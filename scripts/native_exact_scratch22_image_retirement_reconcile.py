#!/usr/bin/env python3
"""Additive read-only root observation of the interrupted image guard.

This cannot retire a process or container and never writes an original guard
result. A later, independently released cleanup may consume the fresh proof.
"""
import argparse
import importlib.util
import os
from pathlib import Path
import re
import subprocess
import sys

sys.dont_write_bytecode = True

REPO = Path(__file__).resolve().parents[1]
SELF = Path(__file__).resolve()
TEST = REPO / 'scripts/tests/test_native_exact_scratch22_image_retirement_reconcile.py'
ROOT = Path('/home/holden/mckernel-work/scratch')
ORIGINAL_RELEASE = REPO / 'docs/verification/evidence/scratch22-authority3-image-execution-release-20261017.json'
ORIGINAL_QUARANTINE = Path(str(ORIGINAL_RELEASE) + '.root-lock-quarantine.json')
BOOT = '7bfc5687-6c04-4d15-84eb-b92ab9a55dcb'
CONTAINER = '29197a19ae252dcad3fb47c87b97a786dce8e5caa19ddf793e8588ddf6cfc99f'
RECEIPT_SHA = '2c939cb8bb6a85646b0806ed429db3985cfd4b0b31eff0b48abb2b3069e2feae'
IMAGE_SHA = 'fa6685543160fcaa5000b535ec8bd6fc70230465109564c3fb2beecb95bf39ed'
ABSENT = {409807, 411284, 411296, 411308, 411320, 411382, 414643, 414655, 415269}
SCHEMA = 'scratch22-authority3-image.reconciliation'


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


core = load(REPO / 'scripts/native_exact_scratch22_authority1_quarantine_recovery.py', 'image_reconcile_core')
cleanup = load(REPO / 'scripts/native_exact_scratch22_authority3_image_cleanup.py', 'image_reconcile_cleanup')
Refusal = core.Refusal


def files_sha256():
    paths = (SELF, TEST, Path(core.__file__), Path(cleanup.__file__), core.PROC_SOURCE)
    result = {str(path.relative_to(REPO)): core.file_identity(path)[0]['sha256'] for path in paths}
    if result[str(Path(core.__file__).relative_to(REPO))] != '3fdb4dde4dbbd5d07d85d68c02e68d4aee3acca45dce12be3479f3252765abd6':
        raise Refusal('immutable authority1 core differs')
    return result


def read_bound_bytes(row):
    path = Path(row['path'])
    if cleanup.observe_identity(path) != row:
        raise Refusal('frozen input identity differs: ' + row['path'])
    raw = cleanup.read_bounded(path)
    if (core.sha(raw) != row['sha256'] or len(raw) != row['size'] or
            cleanup.observe_identity(path) != row):
        raise Refusal('frozen parsed bytes or identity differ: ' + row['path'])
    return raw


def read_binding(row):
    return cleanup.parse(read_bound_bytes(row))


def bind_release(path, expected, consuming=False, binding=None):
    if binding is None:
        # The accepted core hashes and parses the same bytes from one stable FD.
        release = core.read_json(path, expected)
    else:
        if binding['path'] != str(path) or binding['sha256'] != expected:
            raise Refusal('release binding differs')
        release = read_binding(binding)
    if (release.get('schema') != SCHEMA + '-release.v1' or
            release.get('status') != 'PASS_EXECUTION_RELEASE' or
            type(release.get('execution_count')) is not int or release['execution_count'] != 1 or
            release.get('fetched_source_verified') is not True or
            not re.fullmatch('[0-9a-f]{40}', str(release.get('source_checkpoint', ''))) or
            release.get('files_sha256') != files_sha256() or not release.get('author')):
        raise Refusal('exact independent reconciliation execution release required')
    for key, status in (('source_review', 'PASS_SOURCE'), ('execution_review', 'PASS_EXECUTION_REVIEW')):
        binding = release[key]
        review = core.read_json(Path(binding['path']), binding['sha256'])
        if (review.get('decision') != status or not review.get('reviewer') or
                review['reviewer'] == release['author'] or review.get('implementation_ownership') is not False or
                review.get('files_sha256') != release['files_sha256'] or
                review.get('source_checkpoint') != release['source_checkpoint'] or
                review.get('frozen_inputs_sha256') != core.sha(core.canonical(release['observation']))):
            raise Refusal('independent frozen input/source review differs')
    if not re.fullmatch('[0-9a-f]{32}', str(release.get('nonce', ''))):
        raise Refusal('fresh nonce required')
    output = ROOT / ('scratch22-image-retirement-reconciliation-' + release['nonce'])
    if release.get('output') != str(output) or (not consuming and os.path.lexists(output)):
        raise Refusal('fresh output namespace required')
    # This entry point is root-only; no sudo invocation is embedded in it.
    if not consuming and (os.geteuid() != 0 or os.uname().machine != 'x86_64' or
            os.sched_getaffinity(0) != {0}):
        raise Refusal('root x86_64 CPU0 observation required')
    return release, output


def validate_inputs(obs):
    required = {'request', 'owner_receipt', 'consumed_release', 'original_quarantine',
                'retained_exclusions', 'selected_files', 'candidate_root', 'backup_root',
                'inventories', 'container_inspect', 'original_client_files', 'mount', 'root'}
    if set(obs) != required:
        raise Refusal('complete frozen input set required')
    validate_mount_binding(core.canonical({'filesystems': [obs['mount']]}),
                           cleanup.observe_identity(ROOT), obs)
    request, receipt = read_binding(obs['request']), read_binding(obs['owner_receipt'])
    original, quarantine = read_binding(obs['consumed_release']), read_binding(obs['original_quarantine'])
    if (obs['request']['path'] != str(cleanup.REQUEST) or obs['request']['sha256'] != cleanup.REQUEST_SHA or
            obs['owner_receipt']['path'] != str(cleanup.TERMINAL) or
            obs['owner_receipt']['sha256'] != RECEIPT_SHA or
            obs['consumed_release']['path'] != str(ORIGINAL_RELEASE) or
            obs['consumed_release']['sha256'] != '7e1291db58e0a3e245e3b0904f7c9ac9d2d81e3358c3738d10cbf513a42bdafc' or
            obs['original_quarantine']['sha256'] != '1f150f0076bb9fbdf1a911ac29b6e788016bdf05a73ad6a4b290c3db31d2392a' or
            original.get('nonce') != '591fd260dfd144b584617b2298da1c8d' or
            obs['original_quarantine']['path'] != str(ORIGINAL_QUARANTINE) or
            original.get('schema') != 'scratch22-authority3.image-guard-release.v1' or
            original.get('status') != 'PASS_EXECUTION_RELEASE' or
            original.get('boot_id') != BOOT or original.get('request') !=
            {'path': str(cleanup.REQUEST), 'sha256': cleanup.REQUEST_SHA} or
            original.get('source_sha256', {}).get('scripts/native_exact_scratch22_authority3_image_guard.py') !=
            '8691e8079e39bf209218b264dcd2bc73972ee82b743b4a2ecf2aae1d63ccb6b5' or
            quarantine != {'pid': 409807, 'reason': 'core-entered-without-proven-successful-retirement',
                           'root_lock': [27, 4], 'schema': 'mckernel.tool-image-rebind-root-quarantine.v1',
                           'status': 'QUARANTINED_ROOT_LOCK_HELD'}):
        raise Refusal('original consumed-release/quarantine joins differ')
    if os.path.lexists(cleanup.LEASE):
        raise Refusal('original request lease reappeared')
    if os.path.lexists(Path(original['guard_capture']) / 'guard-result.json'):
        raise Refusal('unexpected original guard result exists')
    validate_original_clients(obs['original_client_files'], original)
    source = cleanup.image_request_binding(request)
    item = obs['container_inspect']
    cleanup.image_owner_receipt_binding(receipt, item, RECEIPT_SHA)
    if (receipt.get('status') != 'PASS' or type(receipt.get('exit_code')) is not int or receipt['exit_code'] != 0 or
            receipt.get('container_id') != CONTAINER or
            receipt.get('container_name') != 'mckernel-image-9f0cc05c13114ed4b4adc24bdab4a22a' or
            receipt.get('owner_nonce') != 'da0a58dae0544695a200641d876fe186'):
        raise Refusal('exact original image owner differs')
    state = item.get('State', {})
    expected = {'Status': 'exited', 'Running': False, 'Paused': False, 'Restarting': False,
                'OOMKilled': False, 'Dead': False, 'Pid': 0, 'ExitCode': 0, 'Error': ''}
    if (any(core.canonical(state.get(k)) != core.canonical(v) for k, v in expected.items()) or
            item.get('Id') != CONTAINER or item.get('Name') != '/' + receipt['container_name'] or
            item.get('Image') != request['image_id'] or
            item.get('Config', {}).get('Labels', {}).get('mckernel.owner') != receipt['owner_nonce']):
        raise Refusal('exact stopped container identity differs')
    command, mounts = cleanup.image_layout(request)
    config, host = item['Config'], item['HostConfig']
    profile = {'CpusetCpus': '2-5', 'NanoCpus': 4000000000, 'Memory': 12884901888,
               'MemorySwap': 12884901888, 'PidsLimit': 512, 'NetworkMode': 'none',
               'IpcMode': 'private', 'ReadonlyRootfs': True, 'Privileged': False,
               'CapDrop': ['ALL'], 'Init': True, 'SecurityOpt': ['no-new-privileges'],
               'Tmpfs': {'/tmp': 'rw,nodev,nosuid,size=256m'},
               'RestartPolicy': {'MaximumRetryCount': 0, 'Name': 'no'}, 'AutoRemove': False}
    if (any(core.canonical(host.get(k)) != core.canonical(v) for k, v in profile.items()) or
            config.get('User') != '1000:1000' or config.get('Entrypoint') != ['/usr/bin/python3'] or
            config.get('Cmd') != command or item.get('Args') != command or
            item.get('Path') != '/usr/bin/python3' or config.get('Image') != request['image_id']):
        raise Refusal('image command/resource profile differs')
    core.inspect_comparison(item)  # Reject malformed/duplicate mount destinations.
    actual = [(m.get('Destination'), m.get('Source'), m.get('Type'), m.get('RW'))
              for m in item['Mounts'] if m.get('Type') == 'bind']
    extra = [m for m in item['Mounts'] if m.get('Type') != 'bind']
    if (sorted(actual) != mounts or (extra and (len(extra) != 1 or extra[0].get('Type') != 'tmpfs' or
            extra[0].get('Destination') != '/tmp' or extra[0].get('RW') is not True))):
        raise Refusal('exact image mounts differ')
    records = obs['retained_exclusions']
    if len(records) != 2 or {r['path'] for r in records} != {str(cleanup.ATTEMPT), str(cleanup.SHARED)}:
        raise Refusal('both original exclusion identities required')
    if {Path(r['path']): r['inode'] for r in records} != {cleanup.ATTEMPT: 107669, cleanup.SHARED: 107668}:
        raise Refusal('original exclusion inodes differ')
    target = dict(container_id=CONTAINER, container_name=receipt['container_name'],
                  owner_nonce=receipt['owner_nonce'], image_id=request['image_id'],
                  owner_pid=409807, owner_starttime='1912441', exit_code=0)
    for row in records:
        cleanup.image_record_binding(Path(row['path']), row, read_binding(row), request, target, BOOT)
    selected = {r['path']: r for r in obs['selected_files']}
    joins = {'driver_path': 'driver_sha256', 'provenance_path': 'provenance_sha256',
             'host_owner_path': 'host_owner_sha256', 'source_manifest': 'source_manifest_sha256',
             'toolchain_manifest': 'toolchain_manifest_sha256'}
    if request.get('gitlink_manifest') is not None:
        joins['gitlink_manifest'] = 'gitlink_manifest_sha256'
    images = [str(cleanup.OUTPUT / p) for p in ('output/build/kernel/mckernel.img', 'evidence/artifacts/mckernel.img')]
    needed = {str(cleanup.EVIDENCE / 'attempt/container.log'), str(cleanup.OUTPUT / 'evidence/receipt.json'),
              *images, *(request[k] for k in joins)}
    if len(selected) != len(obs['selected_files']) or not needed <= set(selected):
        raise Refusal('complete selected published bytes required')
    for row in selected.values():
        if cleanup.observe_identity(Path(row['path'])) != row:
            raise Refusal('selected published bytes/identity differ')
    if (any(selected[request[k]]['sha256'] != request[v] for k, v in joins.items()) or
            any(selected[p]['sha256'] != IMAGE_SHA for p in images)):
        raise Refusal('published image/source hashes differ')
    for key, request_key in (('candidate_root', 'source_identity'), ('backup_root', 'backup_identity')):
        row = obs[key]
        wanted = request[request_key]
        if (cleanup.observe_identity(Path(row['path'])) != row or
                any(core.canonical(wanted.get(k)) != core.canonical(v) for k, v in
                    dict(path=row['path'], dev=row['device'], inode=row['inode'], uid=row['uid'],
                         gid=row['gid'], mode=int(row['mode'], 8), file_type=cleanup.stat.S_IFDIR).items())):
            raise Refusal('source/backup identity differs')
    if ((obs['candidate_root']['device'], obs['candidate_root']['inode']) != (1828, 3946466) or
            (obs['backup_root']['device'], obs['backup_root']['inode']) != (1828, 4608324)):
        raise Refusal('original source/backup nodes differ')
    if obs['candidate_root']['path'] != str(source) or obs['backup_root']['path'] != request['backup_root']:
        raise Refusal('source/backup paths differ')
    if set(obs['inventories']) != {str(cleanup.OUTPUT), str(cleanup.EVIDENCE)}:
        raise Refusal('complete metadata inventories required')
    for path in (cleanup.OUTPUT, cleanup.EVIDENCE):
        if cleanup.metadata_inventory(path) != obs['inventories'][str(path)]:
            raise Refusal('output/evidence metadata drift')
    core.boot_check()
    return receipt


def validate_original_clients(rows, original):
    root = Path(original['guard_capture'])
    if root != ROOT / 'native-image-guard-942c927b-20261017-591fd260dfd144b584617b2298da1c8d':
        raise Refusal('original guard capture namespace differs')
    supplied = {r['path']: r for r in rows}
    commands = sorted(root.glob('command-*'))
    needed = {str(root / 'docker.log'), str(root / 'consumed-release.json')}
    needed.update(str(p / name) for p in commands for name in ('status.json', 'stdout', 'stderr'))
    if len(commands) != 8 or len(supplied) != len(rows) or set(supplied) != needed:
        raise Refusal('complete eight retained client commands/logs required')
    for row in rows:
        if cleanup.observe_identity(Path(row['path'])) != row:
            raise Refusal('retained client bytes/identity differ')
    consumed = read_binding(supplied[str(root / 'consumed-release.json')])
    if consumed != dict(nonce=original['nonce'], release_sha256=
                        '7e1291db58e0a3e245e3b0904f7c9ac9d2d81e3358c3738d10cbf513a42bdafc',
                        request_sha256=cleanup.REQUEST_SHA):
        raise Refusal('original release consumption differs')
    pids = set()
    for path in commands:
        status = read_binding(supplied[str(path / 'status.json')])
        if (type(status.get('pid')) is not int or status['pid'] in pids or
                status.get('state') != 'exited' or type(status.get('exit_code')) is not int or
                status['exit_code'] != 0 or not isinstance(status.get('argv'), list)):
            raise Refusal('retained client exit not proven')
        pids.add(status['pid'])
    if pids != ABSENT - {409807}:
        raise Refusal('original client PID set differs')


def validate_process_report(report, challenge, caller):
    core.BOOT, core.PID, core.START, core.PARENT = BOOT, 409807, '1912441', 0
    core.ABSENT = ABSENT
    core.validate_process_report(report, challenge, caller, False)
    combined = {}
    for snapshot in report['snapshots']:
        for pid, parent, start in snapshot:
            combined.setdefault(pid, set()).add(parent)
    related = set(ABSENT)
    while True:
        expanded = related | {pid for pid, parents in combined.items() if parents & related}
        if expanded == related:
            break
        related = expanded
    if related & set(combined):
        raise Refusal('original owner/client or transitive descendant present')


def validate_containers(raw, receipt):
    target, ids = [], set()
    for line in raw.splitlines():
        row = core.strict(line)
        if (not re.fullmatch('[0-9a-f]{64}', str(row.get('ID', ''))) or row['ID'] in ids or
                row.get('State') not in ('created', 'restarting', 'running', 'removing', 'paused', 'exited', 'dead')):
            raise Refusal('full container census malformed')
        ids.add(row['ID'])
        if row['State'] in ('running', 'restarting', 'removing', 'paused'):
            raise Refusal('active container exists')
        if (row['ID'] == CONTAINER or row.get('Names') == receipt['container_name'] or
                'mckernel.owner=' + receipt['owner_nonce'] in row.get('Labels', '').split(',')):
            target.append(row)
    if (len(target) != 1 or target[0]['ID'] != CONTAINER or
            target[0].get('Names') != receipt['container_name'] or target[0]['State'] != 'exited'):
        raise Refusal('exact stopped container census differs')


def validate_mount_binding(raw, root, obs):
    """Accepted findmnt/full mount record plus stable root-node join."""
    mounts = core.strict(raw).get('filesystems')
    wanted = obs['mount']
    if (not isinstance(mounts, list) or len(mounts) != 1 or mounts[0] != wanted or
            wanted.get('target') != str(ROOT) or wanted.get('uuid') != cleanup.UUID or
            wanted.get('fstype') != 'ext4' or wanted.get('maj:min') != '7:36' or
            not {'rw', 'nodev', 'nosuid'} <= set(wanted.get('options', '').split(',')) or
            obs['root'].get('path') != str(ROOT) or type(root.get('device')) is not int or
            root['device'] != 1828 or obs['root'].get('device') != 1828 or
            any(root.get(key) != obs['root'].get(key) for key in
                ('path', 'device', 'inode', 'mode', 'uid', 'gid'))):
        raise Refusal('fresh scratch mount/root binding differs')


def observe(release, output, release_binding):
    lock = core.acquire_root_lock()  # Existing root-owned 27:4, never created/unlinked.
    try:
        core.require_lock_holder(os.getpid())
        receipt = validate_inputs(release['observation'])
        output.mkdir(mode=0o700)  # Fresh additive captures only.
        captures = {}
        def run(kind, argv):
            try:
                result = subprocess.run(argv, env={'PATH': '/usr/bin:/bin', 'LANG': 'C', 'LC_ALL': 'C'},
                                        stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                        timeout=30, check=False)
                stdout, stderr, code, timed_out = result.stdout, result.stderr, result.returncode, False
            except subprocess.TimeoutExpired as exc:
                stdout, stderr, code, timed_out = exc.stdout or b'', exc.stderr or b'', None, True
            for suffix, raw in (('stdout', stdout), ('stderr', stderr)):
                path = output / (kind + '.' + suffix)
                core.publish(path, raw)
                captures[kind + '.' + suffix] = cleanup.observe_identity(path)
            core.publish(output / (kind + '.command.json'), core.canonical(
                dict(argv=argv, returncode=code, timeout=timed_out)))
            if timed_out or code != 0 or stderr or len(stdout) > core.SMALL_LIMIT:
                raise Refusal('read-only observation command failed: ' + kind)
            return stdout
        def mount_snapshot(label):
            raw = run('mount-' + label, ['/usr/bin/findmnt', '-J', '-T', str(ROOT), '-o',
                                        'TARGET,SOURCE,FSTYPE,OPTIONS,UUID,MAJ:MIN'])
            root = cleanup.observe_identity(ROOT)
            path = output / ('root-' + label + '.json')
            core.publish(path, core.canonical(root))
            captures[path.name] = cleanup.observe_identity(path)
            validate_mount_binding(raw, root, release['observation'])
        mount_snapshot('before')
        caller = [os.getpid(), core.proc_stat(os.getpid())[19]]
        challenge = os.urandom(24).hex()
        raw = run('process', ['/usr/bin/python3', '-I', '-B', '-c', core.process_code(),
                              challenge, str(caller[0]), caller[1]])
        validate_process_report(core.strict(raw), challenge, caller)
        docker = ['/usr/bin/docker', '--host=unix:///var/run/docker.sock']
        raw = run('inspect', docker + ['inspect', '--type', 'container', CONTAINER])
        items = core.strict(raw)
        if (not isinstance(items, list) or len(items) != 1 or core.inspect_comparison(items[0]) !=
                core.inspect_comparison(release['observation']['container_inspect'])):
            raise Refusal('fresh full container inspect differs')
        validate_containers(run('containers', docker + ['ps', '-a', '--no-trunc', '--format', '{{json .}}']), receipt)
        validate_inputs(release['observation'])
        mount_snapshot('after')
        core.require_lock_holder(os.getpid())
        proof = dict(schema=SCHEMA + '-proof.v1', status='PASS_FRESH_RETIREMENT_OBSERVATION',
                     original_guard_retirement_proven=False, cleanup_separately_required=True,
                     nonce=release['nonce'], release=release_binding, observation=release['observation'],
                     boot_id=BOOT, caller=caller, challenge=challenge, captures=captures,
                     root_lock=[27, 4], absent_pids=sorted(ABSENT))
        core.publish(output / 'recovery-proof.json', core.canonical(proof))
        return proof
    finally:
        os.close(lock)


def validate_proof(binding, cleanup_obs):
    """Cleanup consumer: no fallback and no synthetic original retirement."""
    proof = read_binding(binding)
    release_row = proof['release']
    if cleanup.observe_identity(Path(release_row['path'])) != release_row:
        raise Refusal('reconciliation release identity differs')
    release, output = bind_release(Path(release_row['path']), release_row['sha256'], consuming=True,
                                   binding=release_row)
    required = {'schema', 'status', 'original_guard_retirement_proven', 'cleanup_separately_required',
                'nonce', 'release', 'observation', 'boot_id', 'caller', 'challenge', 'captures',
                'root_lock', 'absent_pids'}
    if (set(proof) != required or binding['path'] != str(output / 'recovery-proof.json') or
            binding['uid'] != 0 or binding['gid'] != 0 or
            proof['schema'] != SCHEMA + '-proof.v1' or proof['status'] != 'PASS_FRESH_RETIREMENT_OBSERVATION' or
            proof['original_guard_retirement_proven'] is not False or proof['cleanup_separately_required'] is not True or
            proof['nonce'] != release['nonce'] or proof['observation'] != release['observation'] or
            proof['boot_id'] != BOOT or proof['root_lock'] != [27, 4] or proof['absent_pids'] != sorted(ABSENT)):
        raise Refusal('exact fresh recovery proof differs')
    obs = proof['observation']
    # The future cleanup release must preserve each original join, not merely
    # bind a passing status or a reference to the proof.
    for key in ('request', 'retained_exclusions', 'candidate_root', 'backup_root', 'inventories', 'mount'):
        if obs[key] != cleanup_obs[key]:
            raise Refusal('cleanup/recovery original observation differs: ' + key)
    if any(obs['root'].get(key) != cleanup_obs['root'].get(key) for key in
           ('path', 'device', 'inode', 'mode', 'uid', 'gid')):
        raise Refusal('cleanup/recovery scratch root differs')
    if core.inspect_comparison(obs['container_inspect']) != core.inspect_comparison(cleanup_obs['container_inspect']):
        raise Refusal('cleanup/recovery complete container differs')
    selected = {r['path']: r for r in cleanup_obs['selected_files']}
    for row in [obs['owner_receipt'], obs['consumed_release'], obs['original_quarantine'],
                *obs['selected_files'], *obs['original_client_files']]:
        if selected.get(row['path']) != row:
            raise Refusal('cleanup must preserve every original selected join')
    receipt = validate_inputs(obs)
    captures = proof['captures']
    expected = {kind + '.' + stream for kind in
                ('process', 'inspect', 'containers', 'mount-before', 'mount-after')
                for stream in ('stdout', 'stderr')} | {'root-before.json', 'root-after.json'}
    if set(captures) != expected:
        raise Refusal('complete fresh captures required')
    captured = {}
    for name, row in captures.items():
        if row['path'] != str(output / name) or row['uid'] != 0 or row['gid'] != 0:
            raise Refusal('fresh root capture identity differs')
        captured[name] = read_bound_bytes(row)
        if name.endswith('.stderr') and captured[name]:
            raise Refusal('fresh observation stderr not empty')
    for label in ('before', 'after'):
        validate_mount_binding(captured['mount-' + label + '.stdout'],
                               core.strict(captured['root-' + label + '.json']), obs)
    validate_process_report(core.strict(captured['process.stdout']), proof['challenge'], proof['caller'])
    items = core.strict(captured['inspect.stdout'])
    if (not isinstance(items, list) or len(items) != 1 or
            core.inspect_comparison(items[0]) != core.inspect_comparison(obs['container_inspect'])):
        raise Refusal('fresh inspect capture differs')
    validate_containers(captured['containers.stdout'], receipt)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--release', type=Path, required=True)
    parser.add_argument('--release-sha256', required=True)
    args = parser.parse_args()
    release, output = bind_release(args.release, args.release_sha256)
    observe(release, output, cleanup.observe_identity(args.release))


if __name__ == '__main__':
    main()
