#!/usr/bin/env python3
"""Prepare ONLY mode2's isolated acknowledged-publication guest root.

Derived from the retained original fault stager; no compiler or process launch.
The prepared root remains blocked on a separate compiled-stack readiness review.
This helper never grants guest release, transport credit or application acceptance.
"""
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

ORIGINAL_STAGER_SHA256 = '0b45f00a6ed72b8b55b25f27261650e14b32e43e398ee2005ffeb5a16ac78d82'
MODULE_RECORD_SHA256 = '3bded4f7bfc206b4e64b03a58243d0e3a7783a5a493dd4095be5916a07e7ed48'
PREPARATION_RECORD_SHA256 = 'e7e2e6b8caa8e7c4deaffcbfd87f7d53bbb9b04b19dd7c574e9ace670520c0b2'
CONTROLLER_RECORD_SHA256 = '561090585ba7316ad7b03716e5e430586fc13180bad0f0fe448a133ea1f4546c'
CONTROLLER_SOURCES = {
    'controller.c': 'b8360dc502d53ee537e462815657d85510488a1820c10501c38cb49150b52d3c',
    'phase_client.h': '929f9fd03793f6006056219bc6d75451ed9c2e6a856a938997bbf8663b8a6e6d',
}


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
    assert args.mode == 'postpublish-notify', 'mode3 requires separate eight-HELLO composition'
    assert args.controller_profile == 'owner-published-hold-v1' and args.payload_profile == 'runnable-thread-v1'
    work = Path('/work')
    assert args.output.parent == work and args.output == args.output.resolve(), 'fresh canonical direct child of /work required'
    assert shutil.disk_usage(work).free > 3 * 1024**3
    args.output.mkdir()
    record = dict(status='RUNNING', started_utc=datetime.now(timezone.utc).isoformat(),
                  mode=args.mode, nonce=args.nonce, inputs=[], bindings=[],
                  payload_profile=args.payload_profile,
                  controller_profile=args.controller_profile,
                  controller_protocol='STF2', phase_ioctl_version=2, phase_ioctl_command='0xc100f502',
                  guest_execution=False, payload_execution=False, application_acceptance=False,
                  transport_acceptance=False, production_gate_credit=False,
                  guest_release_ready=False, compiled_stack_readiness=dict(status='PENDING_ACTUAL_REVIEW'),
                  verified_read_only_inputs=[])
    observed_inputs = {}

    def save():
        (args.output / 'record.json').write_text(json.dumps(record, indent=2, sort_keys=True) + '\n')

    def verify(row):
        path = Path(row['path'])
        assert path.is_absolute()
        data = path.read_bytes()
        assert dict(path=str(path), size=len(data), sha256=hashlib.sha256(data).hexdigest()) == row, path
        if path in observed_inputs:
            assert observed_inputs[path] == row, path
        else:
            observed_inputs[path] = row
            record['verified_read_only_inputs'].append(row)
        return data

    def load(directory, expected, expected_sha256=None):
        path = directory / 'record.json'
        raw = path.read_bytes()
        row = dict(path=str(path), size=len(raw), sha256=hashlib.sha256(raw).hexdigest())
        if expected_sha256 is not None:
            assert row['sha256'] == expected_sha256, path
        data = json.loads(raw)
        assert data['status'] == expected, (path, data['status'])
        target = args.output / 'input-records' / str(path).lstrip('/')
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
        assert verify(row) == raw
        record['inputs'].append(row)
        return data

    def completed(command):
        collected = command['collection']
        assert collected['status'] == 'COMPLETED' and collected['raw_wait_status'] == 0 and collected['cleanup_complete']
        for stream in collected['streams'].values():
            assert stream['eof'] and not stream['truncated'] and stream['discarded_observed_bytes'] == 0
            assert stream['bytes_observed'] == stream['bytes_retained'] == stream['artifact']['size']
            verify(stream['artifact'])

    def bind_copy(source, target, rows):
        matches = [row for row in rows if row['path'] == str(source)]
        assert len(matches) == 1, source
        expected = matches[0]
        data = verify(expected)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        assert identity(target)['sha256'] == expected['sha256']
        record['bindings'].append(dict(original=expected, prepared=identity(target)))

    try:
        shutil.copyfile(__file__, args.output / 'helper.py')
        original_stager = Path(__file__).parent / 'fixtures/stability-published-guest-v1/prepare_stability_fault_guest.py.original'
        original = original_stager.read_bytes()
        assert hashlib.sha256(original).hexdigest() == ORIGINAL_STAGER_SHA256
        (args.output / 'prepare_stability_fault_guest.py.original').write_bytes(original)
        record['derived_original_stager'] = identity(original_stager)
        baseline = work / 'native-ultra-baseline-memory-guest-20260909-stability-service-failure-20260913-1'
        baseline_record = load(baseline, 'PASS')
        assert args.module == work / 'stability-published-hold-module-20260913-postpublish-notify-1'
        module_record = load(args.module, 'PASS_BUILD_ONLY', MODULE_RECORD_SHA256)
        assert module_record['mode'] == args.mode and module_record['shared_production_trees_restored']
        assert module_record['verification_only']
        assert module_record['phase_wiring'] == 'PRIVATE_VERSION2_ACKNOWLEDGED_PUBLISHED_HOLD'
        assert module_record['actual_stack_frames_verified'] is False
        preparation_path = Path(module_record['preparation_record']['path'])
        assert preparation_path == work / 'stability-published-source-20260913-postpublish-notify-2/record.json'
        verify(module_record['preparation_record'])
        preparation = load(preparation_path.parent, 'PREPARED_PUBLISHED_HOLD_NO_BUILD_NO_EXECUTION', PREPARATION_RECORD_SHA256)
        assert verify(module_record['preparation_record']) == (args.module / 'preparation-record.json').read_bytes()
        assert preparation['mode'] == args.mode and preparation['phase_wiring'] == module_record['phase_wiring']
        assert preparation['shared_production_trees_restored'] and preparation['verification_only']
        assert module_record['prepared_source_before_format'] == preparation['complete_published_source']
        assert inventory(args.module / 'combined-source') == preparation['complete_published_source']
        assert module_record['held_stage_record'] == preparation['held_stage_record']
        held_path = Path(module_record['held_stage_record']['path'])
        verify(module_record['held_stage_record'])
        held = load(held_path.parent, 'PREPARED_NOT_COMPILED_NOT_EXECUTED')
        assert held['mode'] == args.mode and held['version'] == 2 and held['command'] == '0xc100f502'
        assert verify(module_record['held_stage_record']) == (args.module / 'held-stage-record.json').read_bytes()
        assert module_record['published_fixture_inputs'] == preparation['published_fixture_inputs']
        for row in preparation['fixture_inputs'] + preparation['published_fixture_inputs']:
            verify(row)
        compiler_inputs = {row['path']: row for row in module_record['compiler_inputs']}
        compiler_bindings = module_record['retained_compiler_bindings']
        assert len(compiler_inputs) == len(module_record['compiler_inputs']) == len(compiler_bindings) == 63
        assert {row['historical_compile_path'] for row in compiler_bindings} == set(compiler_inputs)
        for binding in compiler_bindings:
            retained = binding['retained']
            verify(retained)
            original = compiler_inputs[binding['historical_compile_path']]
            assert (retained['size'], retained['sha256']) == (original['size'], original['sha256'])
        for command in module_record['commands']:
            completed(command)
        for row in module_record['compiled_modules']:
            verify(row)
        record['module_compiler_bindings'] = compiler_bindings
        record['compiled_stack_readiness'] = dict(
            status='PENDING_ACTUAL_REVIEW', module_record=identity(args.module / 'record.json'),
            compiled_modules=module_record['compiled_modules'], actual_stack_frames_verified=False,
            required='Separate independently reviewed actual compiled frame/chain readiness bound to these module bytes; runner must join before guest release.')
        if 'reused_owner_parser_tests' in module_record:
            reuse = module_record['reused_owner_parser_tests']
            assert reuse == preparation['reused_owner_parser_tests']
            assert reuse['passed_cases'] == 19 and reuse['rerun'] is False
            prior_path = Path(reuse['record']['path'])
            assert prior_path.is_relative_to(work) and prior_path.name == 'record.json'
            assert identity(prior_path) == reuse['record']
            prior = load(prior_path.parent, 'PASS_BUILD_ONLY')
            assert prior['owner_parser_tests'] == 19
            checks = [row for row in prior['commands'] if row['label'] == 'owner-parser-tests']
            assert len(checks) == 1
            completed(checks[0])
            for relative in ('scripts/tests/test_owner_observations.py', 'scripts/application-tests/owner_observations.py'):
                rows = []
                # The new build has published_fixture_inputs, not the original
                # observer/parser fixtures. They belong to its exact preparation.
                for proof in (prior, preparation):
                    matches = [row for row in proof['fixture_inputs'] if row['path'].endswith('/source/' + relative)]
                    assert len(matches) == 1
                    verify(matches[0])
                    rows.append(matches[0])
                assert (rows[0]['size'], rows[0]['sha256']) == (rows[1]['size'], rows[1]['sha256'])
            record['reused_owner_parser_validation'] = dict(reference=identity(prior_path),
                preparation_record=identity(preparation_path), passed_cases=19, rerun=False)
        else:
            raise AssertionError('exact original19 owner-parser reuse proof required')
        utility1 = work / 'stability-guest-collection-build-20260913-1'
        utility2 = work / 'stability-guest-collection-build-20260913-2'
        first = load(utility1, 'FAIL')
        assert first['phase'] == 'artifact-exporter-compile'
        second = load(utility2, 'PASS_BUILD_AND_SYNTHETIC_COLLECTION_TESTS_ONLY')
        assert second['prior_attempt_record'] == identity(utility1 / 'record.json')
        controller = work / 'stability-published-client-tests-20260913-1'
        controller_record = load(controller, 'PASS_PUBLISHED_CONTROLLER_BUILD_AND_CLIENT_METADATA_ONLY', CONTROLLER_RECORD_SHA256)
        assert controller_record['passed_cases'] == 81 and controller_record['guest_execution'] is False
        for name, expected_hash in CONTROLLER_SOURCES.items():
            pairs = [row for row in controller_record['inputs'] if row['retained']['path'] == str(controller / name)]
            assert len(pairs) == 1
            pair = pairs[0]
            assert pair['original']['sha256'] == pair['retained']['sha256'] == expected_hash
            assert pair['original']['size'] == pair['retained']['size']
            verify(pair['retained'])
            compiled = [row for row in controller_record['compiler_dependencies'] if row['original']['path'] == str(controller / name)]
            assert len(compiled) == 1 and compiled[0]['original'] == pair['retained']
        for pair in controller_record['compiler_dependencies']:
            verify(pair['retained'])
            assert (pair['retained']['size'], pair['retained']['sha256']) == (pair['original']['size'], pair['original']['sha256'])
        for row in controller_record['compiled_outputs']:
            verify(row)
        for command in controller_record['commands']:
            completed(command)
        record['controller_compiler_bindings'] = controller_record['compiler_dependencies']
        record['controller_source_bindings'] = [row for row in controller_record['inputs']
            if row['retained']['path'] in [str(controller / name) for name in CONTROLLER_SOURCES]]
        payload = work / 'stability-runnable-thread-payload-build-20260913-1'
        payload_record = load(payload, 'PASS_BUILD_ONLY')
        assert payload_record['payload_profile'] == args.payload_profile
        assert payload_record['payload_source']['sha256'] == 'dbc68dc4e981c0ed3433491747b4dcd7a031548fbd84bddbd8e98361d4681491'
        for row in payload_record['compiler_dependencies'] + payload_record['compiled_outputs']:
            verify(row)
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
                (controller / 'controller.elf', root / 'bin/fault-controller', controller_record['compiled_outputs']),
                (utility1 / 'after-hello.elf', root / 'bin/fault-after-hello', first['compiled_outputs']),
                (utility2 / 'artifact-exporter.elf', root / 'bin/fault-exporter', second['compiled_outputs']),
                (payload / 'payload.elf', root / 'bin/fault-payload', payload_record['compiled_outputs'])):
            bind_copy(original, target, rows)
            target.chmod(0o755)
        # Exact libraries already selected by the accepted baseline must match
        # every independently captured collection utility dependency.
        for row in first['loader_dependencies'] + second['loader_dependencies'] + payload_record.get('loader_dependencies', []) + controller_record.get('loader_dependencies', []):
            source = Path(row['path'])
            data = verify(row)
            target = root / str(source).lstrip('/')
            if target.exists():
                assert target.read_bytes() == data, target
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(data)
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
        for path, row in list(observed_inputs.items()):
            assert identity(path) == row, 'bound input changed during preparation: ' + str(path)
        assert original_stager.read_bytes() == (args.output / 'prepare_stability_fault_guest.py.original').read_bytes()
        assert Path(__file__).read_bytes() == (args.output / 'helper.py').read_bytes()
        record.update(status='PREPARED_REQUIRES_COMPILED_STACK_REVIEW', root=str(root), root_inventory=inventory(root),
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
    parser.add_argument('--mode', choices=['postpublish-notify'], required=True)
    parser.add_argument('--nonce', required=True)
    parser.add_argument('--payload-profile', choices=['runnable-thread-v1'], default='runnable-thread-v1')
    parser.add_argument('--controller-profile', choices=['owner-published-hold-v1'], default='owner-published-hold-v1')
    parser.add_argument('--output', type=Path, required=True)
    prepare(parser.parse_args())
