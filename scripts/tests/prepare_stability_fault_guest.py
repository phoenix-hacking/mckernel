#!/usr/bin/env python3
"""Prepare an isolated transport-fault root; never starts QEMU or a payload."""
import argparse
from datetime import datetime, timezone
import hashlib
import gzip
import json
import os
from pathlib import Path
import re
import shutil
import stat


def identity(path):
    data = path.read_bytes()
    return dict(path=str(path), size=len(data), sha256=hashlib.sha256(data).hexdigest())


def inventory(root):
    rows = []
    for path in sorted(root.rglob('*')):
        st = path.lstat()
        row = dict(path=str(path.relative_to(root)), mode=stat.S_IMODE(st.st_mode))
        if stat.S_ISREG(st.st_mode):
            row.update(kind='file', size=st.st_size, sha256=identity(path)['sha256'])
        elif stat.S_ISDIR(st.st_mode):
            row.update(kind='directory')
        elif stat.S_ISLNK(st.st_mode):
            row.update(kind='symlink', target=os.readlink(path))
        else:
            raise ValueError('unsupported prepared-root member: ' + str(path))
        rows.append(row)
    return rows


def accepted_cpio_inventory(path):
    """Parse the exact accepted newc archive without extracting or executing it."""
    rows, seen = [], set()
    total = 0
    with gzip.open(path, 'rb') as stream:
        while True:
            header = stream.read(110)
            assert len(header) == 110 and header[:6] == b'070701'
            fields = [int(header[6 + i*8:14 + i*8], 16) for i in range(13)]
            mode, uid, gid, size, name_size = fields[1], fields[2], fields[3], fields[6], fields[11]
            assert uid == gid == fields[12] == 0 and 1 <= name_size <= 4096 and size <= 128*1024**2
            name = stream.read(name_size)
            assert len(name) == name_size and name.endswith(b'\0') and b'\0' not in name[:-1]
            name = name[:-1].decode('utf-8')
            assert stream.read(-(110 + name_size) % 4) == bytes(-(110 + name_size) % 4)
            data = stream.read(size)
            assert len(data) == size and stream.read(-size % 4) == bytes(-size % 4)
            total += 110 + name_size + size
            assert total <= 256*1024**2 and len(seen) < 4096
            if name == 'TRAILER!!!':
                assert size == 0 and not stream.read(1024).strip(b'\0') and not stream.read(1)
                break
            assert name and not name.startswith('/') and all(p not in ('', '.', '..') for p in name.split('/'))
            assert name not in seen
            seen.add(name)
            row = dict(path=name, mode=stat.S_IMODE(mode))
            if stat.S_ISREG(mode):
                assert fields[4] == 1, 'unexpected archive hardlink'
                row.update(kind='file', size=size, sha256=hashlib.sha256(data).hexdigest())
            elif stat.S_ISDIR(mode):
                assert size == 0
                row.update(kind='directory')
            elif stat.S_ISLNK(mode):
                row.update(kind='symlink', target=data.decode('utf-8'))
            else:
                assert stat.S_ISCHR(mode) and size == 0
                assert (name, stat.S_IMODE(mode), fields[9], fields[10]) in (
                    ('dev/console', 0o600, 5, 1), ('dev/null', 0o666, 1, 3))
                continue
            rows.append(row)
    assert {'dev/console', 'dev/null'} <= seen
    return sorted(rows, key=lambda row: row['path'])


def prepare(args):
    # Actual invocation/container provenance remains the coordinator's record.
    assert os.getuid() == 1000 and os.sched_getaffinity(0) == {2, 3, 4, 5}
    assert args.output.is_absolute() and args.module.is_absolute()
    assert re.fullmatch('[0-9a-f]{32}', args.nonce) and int(args.nonce, 16)
    assert args.mode == 'prepublish-hard'  # Release other modes in separate reviewed versions.
    work = Path('/work')
    assert shutil.disk_usage(work).free > 3 * 1024**3
    args.output.mkdir()
    record = dict(status='RUNNING', started_utc=datetime.now(timezone.utc).isoformat(),
                  mode=args.mode, nonce=args.nonce, inputs=[], bindings=[],
                  payload_profile=args.payload_profile,
                  controller_profile=args.controller_profile,
                  guest_execution=False, payload_execution=False, application_acceptance=False,
                  transport_acceptance=False, production_gate_credit=False)

    def save():
        (args.output / 'record.json').write_text(json.dumps(record, indent=2, sort_keys=True) + '\n')

    def load(directory, expected):
        path = directory / 'record.json'
        data = json.loads(path.read_text())
        assert data['status'] == expected, (path, data['status'])
        record['inputs'].append(identity(path))
        return data

    def bind_copy(source, target, rows):
        expected = next(row for row in rows if row['path'] == str(source))
        data = source.read_bytes()
        assert dict(path=str(source), size=len(data), sha256=hashlib.sha256(data).hexdigest()) == expected, source
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        assert identity(target)['sha256'] == expected['sha256']
        record['bindings'].append(dict(original=expected, prepared=identity(target)))

    try:
        shutil.copyfile(__file__, args.output / 'helper.py')
        baseline = work / 'native-ultra-baseline-memory-guest-20260909-stability-service-failure-20260913-1'
        baseline_record = load(baseline, 'PASS')
        module_record = load(args.module, 'PASS_BUILD_ONLY')
        assert module_record['mode'] == args.mode and module_record['shared_production_trees_restored']
        assert module_record['verification_only'] and module_record['owner_parser_tests'] == 19
        utility1 = work / 'stability-guest-collection-build-20260913-1'
        utility2 = work / 'stability-guest-collection-build-20260913-2'
        first = load(utility1, 'FAIL')
        assert first['phase'] == 'artifact-exporter-compile'
        second = load(utility2, 'PASS_BUILD_AND_SYNTHETIC_COLLECTION_TESTS_ONLY')
        assert second['prior_attempt_record'] == identity(utility1 / 'record.json')
        controller, controller_record = utility1, first
        if args.controller_profile == 'owner-phase-v2':
            controller = work / 'stability-owner-terminal-controller-build-20260913-1'
            controller_record = load(controller, 'PASS_BUILD_ONLY')
            assert controller_record['controller_profile'] == args.controller_profile
            assert controller_record['controller_source']['sha256'] == '7b1115f4c744d32bb085f23b515e35bcfab4cf0efa6f2e3cb5827742876511e2'
            for row in controller_record['compiler_dependencies'] + controller_record['compiled_outputs']:
                assert identity(Path(row['path'])) == row
        else:
            assert args.controller_profile == 'owner-phase-v1'
        if args.payload_profile == 'single-thread-v1':
            payload = work / 'stability-transport-infrastructure-20260913-1'
            payload_record = load(payload, 'FAIL')
        else:
            assert args.payload_profile == 'runnable-thread-v1'
            payload = work / 'stability-runnable-thread-payload-build-20260913-1'
            payload_record = load(payload, 'PASS_BUILD_ONLY')
            assert payload_record['payload_profile'] == args.payload_profile
            assert payload_record['payload_source']['sha256'] == 'dbc68dc4e981c0ed3433491747b4dcd7a031548fbd84bddbd8e98361d4681491'
            for row in payload_record['compiler_dependencies'] + payload_record['compiled_outputs']:
                assert identity(Path(row['path'])) == row
        auxiliary = work / 'stability-artifact-channel-module-20260913-1'
        auxiliary_record = load(auxiliary, 'PASS_BUILD_ONLY')
        record['reused_failed_attempt_outputs'] = (
            'Only individually successful compiler outputs are reused; original later failures remain FAIL.')
        root = args.output / 'root'
        before = inventory(baseline / 'root')
        accepted_archive = baseline / 'initramfs.cpio.gz'
        assert identity(accepted_archive) in baseline_record['inputs']
        assert accepted_cpio_inventory(accepted_archive) == before
        record['accepted_baseline_initramfs'] = identity(accepted_archive)
        shutil.copytree(baseline / 'root', root, symlinks=True)
        assert inventory(root) == before
        record['baseline_root_inventory'] = before
        shutil.copyfile(root / 'init', args.output / 'baseline-init.original')
        for name in ('ihk.ko', 'ihk-smp-x86_64.ko', 'mcctrl.ko'):
            bind_copy(args.module / name, root / 'modules' / name, module_record['compiled_modules'])
        bind_copy(auxiliary / 'virtio_console.ko', root / 'modules/virtio_console.ko', auxiliary_record['outputs'])
        for original, target, rows in (
                (controller / 'owner-controller.elf', root / 'bin/fault-controller', controller_record['compiled_outputs']),
                (utility1 / 'after-hello.elf', root / 'bin/fault-after-hello', first['compiled_outputs']),
                (utility2 / 'artifact-exporter.elf', root / 'bin/fault-exporter', second['compiled_outputs']),
                (payload / 'payload.elf', root / 'bin/fault-payload', payload_record['compiled_outputs'])):
            bind_copy(original, target, rows)
            target.chmod(0o755)
        # Exact libraries already selected by the accepted baseline must match
        # every independently captured collection utility dependency.
        for row in first['loader_dependencies'] + second['loader_dependencies'] + payload_record.get('loader_dependencies', []) + controller_record.get('loader_dependencies', []):
            source = Path(row['path'])
            assert identity(source) == row
            target = root / str(source).lstrip('/')
            if target.exists():
                assert identity(target)['sha256'] == row['sha256'], target
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source, target)
            record['bindings'].append(dict(original=row, prepared=identity(target)))
        for row in baseline_record['inputs']:
            if row['path'] in (str(baseline / 'root/bin/native-boot'),
                               str(baseline / 'root/init')) or row['path'].endswith('/bzImage'):
                assert identity(Path(row['path'])) == row
                record['inputs'].append(row)
        # The selected McKernel image and unchanged launcher/HELLO come from
        # the exact accepted root; additionally bind their compiler outputs.
        for relative, parent, key in (
                ('bin/mcexec', work / 'native-application-launcher-20260908-2', 'launcher'),
                ('images/mckernel.img', work / 'mckernel-native-ultra-images-20260909-3', 'image')):
            parent_record = load(parent, 'PASS')
            candidates = []
            if key == 'launcher':
                for selection in parent_record['launchers']:
                    candidates += selection['outputs']
            else:
                candidates = next(r for r in parent_record['images'] if r['kind'] == 'native-rust')['outputs']
            matches = [r for r in candidates if r['sha256'] == identity(root / relative)['sha256']]
            assert matches, relative
            for row in matches:
                assert identity(Path(row['path'])) == row
            record['bindings'].append(dict(prepared=identity(root / relative), compiler_outputs=matches))
        (root / 'stability').mkdir(mode=0o700)
        # The unchanged controller sets this exact working directory before
        # execve for both engines. Keep it explicit in the prepared inventory.
        (root / 'case').mkdir(mode=0o755)
        (root / 'case/work').mkdir(mode=0o755)
        original = (root / 'init').read_text()
        marker = "printf 'NATIVE_APPLICATION_LINUX_REFERENCE begin\\n'"
        assert original.count(marker) == 1
        prefix = original.split(marker, 1)[0]
        start = prefix.index('finish() {')
        stop = prefix.index('trap finish EXIT', start)
        finish = '''finish() {
 local status=$? export_status=0 line
 trap - EXIT
 set +e
 printf 'STABILITY_GUEST_FINISH status=%s\\n' "$status"
 printf '%s\\n' "$status" >/stability/init-status.txt
 /bin/dmesg >/stability/native-dmesg.txt || true
 if [ ! -f /stability/artifact-port.txt ]; then
  printf 'STABILITY_EXPORT_INCOMPLETE port_identity_unverified=1\\n'
  while :; do /usr/bin/coreutils --coreutils-prog=sleep 1; done
 fi
 /bin/fault-exporter /stability /dev/vport0p1 @NONCE@ >/artifact-export.stdout 2>/artifact-export.stderr || export_status=$?
 while IFS= read -r line; do printf '%s\\n' "$line"; done </artifact-export.stderr
 printf 'STABILITY_EXPORT_EXIT status=%s\\n' "$export_status"
 if [ "$export_status" -eq 0 ]; then /poweroff; fi
 printf 'STABILITY_EXPORT_INCOMPLETE awaiting_host_watchdog=1\\n'
 while :; do /usr/bin/coreutils --coreutils-prog=sleep 1; done
}
'''
        prefix = prefix[:start] + finish + prefix[stop:]
        topology = '[ "$online" = 0-3 ] && [ "$nodes" = 0-1 ]'
        assert prefix.count(topology) == 1
        prefix = prefix.replace(topology, '[[ "$online" = 0-3 && "$nodes" = 0-1 ]]')
        # Load the original pinned auxiliary Linux module before native boot.
        anchor = 'insmod /modules/ihk.ko\n'
        assert prefix.count(anchor) == 1
        prefix = prefix.replace(anchor, '''insmod /modules/virtio_console.ko
for port_probe in {1..100}; do
 [ -r /sys/class/virtio-ports/vport0p1/name ] && [ -r /sys/class/virtio-ports/vport0p1/dev ] && [ -c /dev/vport0p1 ] && break
 /usr/bin/coreutils --coreutils-prog=sleep 0.1
done
read -r port_name </sys/class/virtio-ports/vport0p1/name
read -r port_numbers </sys/class/virtio-ports/vport0p1/dev
[[ "$port_name" = stability.artifacts && "$port_numbers" =~ ^([0-9]+):([0-9]+)$ ]]
port_major=${BASH_REMATCH[1]}; port_minor=${BASH_REMATCH[2]}
[ -c /dev/vport0p1 ]
actual_major=$(/bin/stat -c %t /dev/vport0p1); actual_minor=$(/bin/stat -c %T /dev/vport0p1)
[[ "$((16#$actual_major))" -eq "$port_major" && "$((16#$actual_minor))" -eq "$port_minor" ]]
printf 'name=%s device=%s major_hex=%s minor_hex=%s\\n' "$port_name" "$port_numbers" "$actual_major" "$actual_minor" >/stability/artifact-port.txt
''' + anchor)
        init = prefix + '''
# Derive identity from this boot's actual native printk record. The host
# independently joins it to stopped physical boot parameters before PRE_INPUT.
boot_os= boot_generation= boot_count=0
/bin/dmesg >/stability/boot-dmesg.txt
while IFS= read -r line; do
 if [[ "$line" =~ IHK-SMP:\\ boot\\ prepared\\ os=([0-9]+)\\ generation=([0-9]+)\\ params= ]]; then
  boot_os=${BASH_REMATCH[1]}; boot_generation=${BASH_REMATCH[2]}; boot_count=$((boot_count+1))
 fi
done </stability/boot-dmesg.txt
[[ "$boot_count" -eq 1 && "$boot_os" -eq 0 && "$boot_generation" -gt 0 ]]
printf 'STABILITY_BOOT_ID os=%s generation=%s\\n' "$boot_os" "$boot_generation" >/stability/boot-identity.txt
[[ -d /case/work && ! -L /case && ! -L /case/work && -d /proc/self/fd ]]
/bin/fault-controller --linux-reference @NONCE@ /stability/linux /bin/fault-payload >/stability/linux-controller.stdout 2>/stability/linux-controller.stderr
printf 'STABILITY_LINUX_REFERENCE_EXIT status=0\\n'
status=0
/bin/fault-controller --owner-guest @MODE@ @NONCE@ /stability/mckernel /bin/mcexec /bin/fault-payload "$boot_os" "$boot_generation" >/stability/mckernel-controller.stdout 2>/stability/mckernel-controller.stderr || status=$?
printf '%s\\n' "$status" >/stability/controller-status.txt
printf 'STABILITY_CONTROLLER_EXIT status=%s\\n' "$status"
[ "$status" -eq 0 ]
printf 'STABILITY_GUEST_COLLECTION_COMPLETE mode=@MODE@\\n'
'''
        init = init.replace('@NONCE@', args.nonce).replace('@MODE@', args.mode)
        (root / 'init').write_text(init)
        (root / 'init').chmod(0o755)
        assert inventory(baseline / 'root') == before
        record.update(status='PREPARED_NOT_EXECUTED', root=str(root), root_inventory=inventory(root),
                      actual_boot_identity_source='guest dmesg -> unique native boot prepared record; host independently validates',
                      unchanged_production_root_verified=True,
                      init=identity(root / 'init'))
    except BaseException as exc:
        record.update(status='FAIL', error_type=type(exc).__name__, error=str(exc))
        raise
    finally:
        record['finished_utc'] = datetime.now(timezone.utc).isoformat()
        save()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--module', type=Path, required=True)
    parser.add_argument('--mode', choices=['prepublish-hard'], required=True)
    parser.add_argument('--nonce', required=True)
    parser.add_argument('--payload-profile', choices=['single-thread-v1', 'runnable-thread-v1'], default='single-thread-v1')
    parser.add_argument('--controller-profile', choices=['owner-phase-v1', 'owner-phase-v2'], default='owner-phase-v1')
    parser.add_argument('--output', type=Path, required=True)
    prepare(parser.parse_args())
