#!/usr/bin/env python3
"""Hold the development lock around the unchanged authority3 image owner."""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys

sys.path.insert(0, '/home/holden/mckernel-work/scratch/native-fp-copy-image-preparation-20261018-1/preparation-commands-1/request-schema-correction-1/adapters')
sys.path.insert(0, '/home/holden/mckernel-work/host-preparation/four-callback-affinity-image-preparation-20261019-1/adapters')

import native_rust_exact_mckernel_image_container_owner as image
from native_rust_exact_build_container_owner import CliSignals, Docker, digest, inspect
from native_rust_exact_build_image_rebind_probe import (
    _development_lock, _read_json_snapshot, _write_json, DEFERRED_SIGNALS,
    DEVELOPMENT_LOCK, DEVELOPMENT_LOCK_IDENTITY, quarantine_root_lock,
)

REPO = Path('/home/holden/mckernel')
ROOT = Path('/home/holden/mckernel-work/scratch')
CANDIDATE = '942c927b1ec93cc31284ff498455909d9bb2d0fc'
UUID = '2a5768c8-718d-4914-bdc0-6b32c5a92a52'
SELF = '/home/holden/mckernel-work/host-preparation/four-callback-affinity-image-preparation-20261019-1/heavy-proposal-1/native_exact_scratch22_authority3_image_guard_corrected.py'
TEST = '/home/holden/mckernel-work/host-preparation/four-callback-affinity-image-preparation-20261019-1/heavy-proposal-1/test_packet_joins_corrected.py'
SOURCES = ('/home/holden/mckernel-work/host-preparation/four-callback-affinity-image-preparation-20261019-1/heavy-proposal-1/native_exact_scratch22_authority3_image_guard_corrected.py', '/home/holden/mckernel-work/host-preparation/four-callback-affinity-image-preparation-20261019-1/heavy-proposal-1/test_packet_joins_corrected.py', '/home/holden/mckernel-work/host-preparation/four-callback-affinity-image-preparation-20261019-1/adapters/native_rust_exact_build_container_owner.py', '/home/holden/mckernel-work/host-preparation/four-callback-affinity-image-preparation-20261019-1/adapters/native_rust_exact_build_image_prepare.py', '/home/holden/mckernel-work/host-preparation/four-callback-affinity-image-preparation-20261019-1/adapters/native_rust_exact_build_image_rebind.py', '/home/holden/mckernel-work/host-preparation/four-callback-affinity-image-preparation-20261019-1/adapters/native_rust_exact_build_image_rebind_probe.py', '/home/holden/mckernel-work/host-preparation/four-callback-affinity-image-preparation-20261019-1/adapters/native_rust_exact_build_offline.py', '/home/holden/mckernel-work/host-preparation/four-callback-affinity-image-preparation-20261019-1/adapters/native_rust_exact_disk_build_wrapper.py', '/home/holden/mckernel-work/host-preparation/four-callback-affinity-image-preparation-20261019-1/adapters/native_rust_exact_mckernel_image_container_owner.py', '/home/holden/mckernel-work/host-preparation/four-callback-affinity-image-preparation-20261019-1/adapters/native_rust_exact_mckernel_image_offline.py', '/home/holden/mckernel-work/host-preparation/four-callback-affinity-image-preparation-20261019-1/adapters/native_rust_exact_mckernel_image_request_prepare.py')


def canonical(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n').encode()


def mount_records(value):
    """Docker may reorder Mounts; preserve every complete record and count."""
    if not isinstance(value, list) or any(not isinstance(row, dict) for row in value):
        raise RuntimeError('fresh exact stopped image container has invalid mounts')
    destinations = [row.get('Destination') for row in value]
    if (any(not isinstance(path, str) or not path.startswith('/') for path in destinations) or
            len(set(destinations)) != len(destinations)):
        raise RuntimeError('fresh exact stopped image container has ambiguous mounts')
    return sorted(canonical(row) for row in value)


def bound(pointer):
    if not re.fullmatch('[0-9a-f]{64}', str(pointer.get('sha256', ''))):
        raise RuntimeError('exact external SHA256 required')
    return _read_json_snapshot(pointer['path'], 'bound image guard input', pointer['sha256'])[0]


def require_actual_ordinary(request, request_sha, release, ordinary, acceptance, identity):
    """Bind this actual four-stage sequence, without predecessor correction history."""
    pointer=release['prerequisites']['ordinary']
    expected_request=dict(path=release['request']['path'],sha256=request_sha,bytes=Path(release['request']['path']).stat().st_size)
    if ordinary.get('status')!='PASS_ONE_ORDINARY_PREPARATION_SEQUENCE' or ordinary.get('bindings',{}).get('image-request.json')!=expected_request:
        raise RuntimeError('actual ordinary result/request differs')
    if (ordinary.get('source_identity')!={'device':identity[0],'inode':identity[1]} or
        release.get('live_admission_required',{}).get('source_identity')!=identity):
        raise RuntimeError('actual ordinary source identity differs')
    stages=ordinary.get('stages',[])
    if (len(stages)!=4 or [x.get('stage') for x in stages]!=['materialize','mkdir','prepare','consume']):
        raise RuntimeError('four exact ordered ordinary stages required')
    if (release.get('ordinary_result_acceptance',{}).get('sha256')!='cc5fecb5f0fa67f25fa74accdf7d75f51951847871d2098ce449e450fc44eb94' or
        release.get('ordinary_independent_reviewer')!='/root/two_cpu_end_to_end_review' or
        release.get('author')==release.get('ordinary_independent_reviewer') or
        acceptance.get('schema')!='mckernel.independent-four-callback-affinity-actual-ordinary-acceptance.v1' or
        acceptance.get('decision')!='PASS_ACTUAL_ORDINARY_PREPARATION_AND_REQUEST_CONSUMERS' or
        acceptance.get('ordinary_preparation_acceptance') is not True or
        acceptance.get('implementation_ownership') != {'author':'rust_next_teardown_leaf',
            'reviewer':'two_cpu_end_to_end_review','reviewer_tests_or_target_replays':0,
            'reviewer_writes':'private review reports only'} or
        acceptance.get('actual_inner_result')!=pointer or acceptance.get('request')!=expected_request or
        acceptance.get('source_identity')!=request['source_identity'] or
        acceptance.get('toolchain')!=ordinary['bindings']['image-toolchain.json'] or
        acceptance.get('materialization_receipt')!=ordinary['bindings']['materialization-receipt.json']):
        raise RuntimeError('independent exact actual ordinary acceptance differs')
    accepted_stages=acceptance.get('actual_stage_results',[])
    if len(accepted_stages)!=4:raise RuntimeError('four independently accepted stage records required')
    for stage,accepted in zip(stages,accepted_stages):
        proof=bound(accepted['result'])
        if (accepted.get('actual')!=stage or proof!=stage or
            accepted['result']['bytes']!=Path(accepted['result']['path']).stat().st_size or
            stage.get('exit_code')!=0 or stage.get('direct_child_joined') is not True or
            stage.get('process_identity_captured') is not True or stage.get('observer_error') is not None or stage.get('stderr_bytes')!=0):
            raise RuntimeError('independent direct ordinary stage join differs')
        for key in ('command','process','stdout','stderr'):
            item=accepted[key];path=Path(item['path'])
            if digest(path)!=item['sha256'] or path.stat().st_size!=item['bytes']:
                raise RuntimeError('independently accepted stage capture differs: '+key)
    consumers=acceptance.get('actual_source_and_request_consumers',{})
    cap=consumers.get('capture',{})
    if (consumers.get('driver_source_pass') is not True or consumers.get('owner_request_pass') is not True or
        digest(Path(cap['path']))!=cap['sha256'] or Path(cap['path']).stat().st_size!=cap['bytes']):
        raise RuntimeError('actual source/request consumer capture differs')
    for key in ('all_closed_direct_statuses_and_capture_sizes_match','four_exact_released_stage_argv',
                'request_manifest_toolchain_receipt_and_driver_pins_match','source_identity_matches_actual_request_and_result',
                'full_source_inventory_bytes_types_modes_and_raw_symlink_targets_match','journal_exact_unique_inventory_match'):
        if acceptance.get('findings',{}).get(key) is not True:raise RuntimeError('independent finding missing: '+key)


def authenticate(request_path, request_sha, release_path, release_sha):
    release = bound({'path': str(release_path), 'sha256': release_sha})
    request = bound({'path': str(request_path), 'sha256': request_sha})
    if (os.geteuid() != 1000 or release.get('schema') != 'fp-save-thin.image-guard-release.v1' or
            release.get('status') != 'PASS_EXECUTION_RELEASE' or
            type(release.get('execution_count')) is not int or release['execution_count'] != 1 or
            release.get('request') != {'path': str(request_path), 'sha256': request_sha} or
            request.get('candidate_sha') != CANDIDATE or
            request.get('candidate_identity_scope') != 'base_git_commit_only' or
            request.get('source_derivative_sha256') != '46ef55bc149a7c17cafc7b082e4774561980452e9d89f1d34e2096e7b9a2107e' or
            release.get('source_derivative_sha256') != request.get('source_derivative_sha256') or
            request.get('materialization_sha256') != 'a6c5602304214426c70a73823607ed58f6cc5d475457051b477271bd4d48ffcc' or
            release.get('boot_id') != Path('/proc/sys/kernel/random/boot_id').read_text().strip() or
            release.get('scratch_binding') != {'uuid': UUID, 'device': ROOT.stat().st_dev}):
        raise RuntimeError('fresh exact authority3 image release required')
    review = bound(release['execution_review'])
    payload = {key: value for key, value in release.items() if key != 'execution_review'}
    if (review.get('decision') != 'PASS_EXECUTION' or review.get('implementation_ownership') is not False or
            not review.get('reviewer') or not release.get('author') or review['reviewer'] == release['author'] or
            review.get('reviewed_release_payload_sha256') != hashlib.sha256(canonical(payload)).hexdigest()):
        raise RuntimeError('independent exact release review required')
    if set(release.get('source_sha256', {})) != set(SOURCES):
        raise RuntimeError('exact guard source closure required')
    for name in SOURCES:
        if digest(REPO / name) != release['source_sha256'][name]:
            raise RuntimeError('guard source drift: ' + name)
    for key, status in (('preparation', 'PASS'), ('cleanup', 'PASS_EXECUTED'),
                        ('native_baseline', 'PASS_DIAGNOSTIC_REVALIDATION'), ('ordinary', 'PASS_ONE_ORDINARY_PREPARATION_SEQUENCE')):
        prerequisite = bound(release['prerequisites'][key])
        if prerequisite.get('status') != status:
            raise RuntimeError('unaccepted image prerequisite: ' + key)
        if key == 'preparation' and (prerequisite.get('candidate_sha') != CANDIDATE or
                                    prerequisite.get('image_id') != request['image_id']):
            raise RuntimeError('tool preparation candidate/image differs')
    ordinary=bound(release['prerequisites']['ordinary'])
    acceptance=bound(release['ordinary_result_acceptance'])
    source_stat=os.lstat(request['source_root'])
    identity=[source_stat.st_dev,source_stat.st_ino,source_stat.st_uid,source_stat.st_gid,source_stat.st_mode&4095]
    require_actual_ordinary(request,request_sha,release,ordinary,acceptance,identity)
    mounted = subprocess.run(['/usr/bin/findmnt', '--json', '--output', 'UUID,MAJ:MIN,TARGET',
                              '--target', str(ROOT)], capture_output=True, text=True,
                             timeout=30, check=True)
    rows = json.loads(mounted.stdout)['filesystems']; device = ROOT.stat().st_dev
    if (len(rows) != 1 or rows[0] != {'uuid': UUID, 'maj:min': '%d:%d' %
            (os.major(device), os.minor(device)), 'target': str(ROOT)}):
        raise RuntimeError('live scratch UUID/device differs')
    capture = Path(release['guard_capture'])
    nonce = release.get('nonce', '')
    if (not re.fullmatch('[0-9a-f]{32}', str(nonce)) or capture.parent != ROOT or
            not capture.name.startswith('native-rust-four-callback-affinity-image-guard-') or
            not capture.name.endswith(nonce) or os.path.lexists(capture)):
        raise RuntimeError('fresh nonce-bound guard capture required')
    return request, release


def prove_retired(request, result, docker, capture):
    receipt_path = Path(request['owner_evidence_root']) / image.OWNER_RECEIPT_NAME
    recorded, receipt_sha = _read_json_snapshot(receipt_path, 'actual image owner receipt')
    if (recorded != result or result.get('retired') is not True or
            result.get('terminal_container_retained') is not True or
            result.get('cleanup_separately_required') is not True or
            result.get('client_retirement_unproven', False) or docker.client_retirement_unproven or
            os.path.lexists(request['lease_path'])):
        raise RuntimeError('image owner retirement/publication is unproven')
    shared = result['shared_heavy_operation']
    if shared['path'] != image._SHARED_HEAVY_ENTRY_CONTRACT.SHARED_HEAVY_LOCK_PATH:
        raise RuntimeError('shared image ownership path differs')
    common_path = Path(request['common_exclusion_path'])
    common, common_sha = _read_json_snapshot(common_path, 'retained common record')
    stored, shared_sha = _read_json_snapshot(shared['path'], 'retained shared record')
    meta, shared_meta = common_path.stat(), Path(shared['path']).stat()
    if (stored != shared['record'] or (shared_meta.st_dev, shared_meta.st_ino) !=
            (stored['device'], stored['inode']) or
            (meta.st_dev, meta.st_ino) != (common['dev'], common['inode']) or
            common['request_sha256'] != hashlib.sha256(json.dumps(request, sort_keys=True).encode()).hexdigest() or
            common['pid'] != os.getpid() or common['boot_id'] != Path(
                '/proc/sys/kernel/random/boot_id').read_text().strip() or
            common['starttime'] != image._proc_starttime(os.getpid())):
        raise RuntimeError('retained image ownership records differ')
    name = result['container_name']
    if not re.fullmatch('mckernel-image-[0-9a-f]{32}', str(name)):
        raise RuntimeError('exact image container name missing')
    fresh = inspect(docker, name)
    old = result['terminal_container_info']
    state, config, host = fresh['State'], fresh['Config'], fresh['HostConfig']
    if (not re.fullmatch('[0-9a-f]{64}', str(result.get('container_id', ''))) or
            fresh.get('Id') != result['container_id'] or fresh.get('Id') != old.get('Id') or
            fresh.get('Name') != '/' + result['container_name'] or
            fresh.get('Image') != request['image_id'] or
            config.get('Labels', {}).get('mckernel.owner') != result['owner_nonce'] or
            state.get('Running') is not False or state.get('Pid') != 0 or
            state.get('Status') not in ('exited', 'created') or state.get('OOMKilled') is not False or
            any(fresh.get(key) != old.get(key) for key in ('HostConfig', 'Config')) or
            mount_records(fresh.get('Mounts')) != mount_records(old.get('Mounts')) or
            any(host.get(key) != value for key, value in image.LIMITS.items()) or
            host.get('Privileged') is not False or host.get('ReadonlyRootfs') is not True or
            host.get('CapDrop') != ['ALL'] or host.get('SecurityOpt') != ['no-new-privileges'] or
            host.get('Init') is not True or host.get('IpcMode') != 'private' or
            host.get('PidMode', '') != '' or host.get('Devices') or host.get('DeviceRequests') or
            host.get('Binds') or host.get('CapAdd') or host.get('CgroupParent', '') != '' or
            config.get('User') != '%d:%d' % (os.getuid(), os.getgid()) or
            docker.client_retirement_unproven):
        raise RuntimeError('fresh exact stopped image container is unproven')
    image._check_identity(Path(request['source_root']), request['source_identity'], 'retained source')
    image._check_identity(Path(request['backup_root']), request['backup_identity'], 'retained backup')
    _read_json_snapshot(common_path, 'retained common record after inspection', common_sha)
    _read_json_snapshot(shared['path'], 'retained shared record after inspection', shared_sha)
    if (os.path.lexists(request['lease_path']) or
            (common_path.stat().st_dev, common_path.stat().st_ino) != (meta.st_dev, meta.st_ino) or
            (Path(shared['path']).stat().st_dev, Path(shared['path']).stat().st_ino) !=
            (shared_meta.st_dev, shared_meta.st_ino)):
        raise RuntimeError('ownership identities changed during inspection')
    _write_json(capture / 'inspect-terminal-fresh.json', fresh)
    return {'owner_status': result['status'], 'owner_receipt_sha256': receipt_sha,
            'container_id': fresh['Id'], 'retired': True, 'retained_for_separate_cleanup': True}


def guarded_execute(request_path, request_sha, release_path, release_sha,
                    lock_path=DEVELOPMENT_LOCK, lock_identity=DEVELOPMENT_LOCK_IDENTITY,
                    lock_owner=(0, 0)):
    mask = signal.pthread_sigmask(signal.SIG_BLOCK, DEFERRED_SIGNALS)
    handlers = {number: signal.getsignal(number) for number in DEFERRED_SIGNALS}
    latch = CliSignals()
    fd = None
    entered = core_entered = safe = False
    try:
        latch.__enter__(); entered = True
        for number in DEFERRED_SIGNALS:
            signal.signal(number, latch.receive)
        signal.pthread_sigmask(signal.SIG_SETMASK, mask)
        fd = _development_lock(lock_path, lock_identity, lock_owner)
        latch.check()
        request, release = authenticate(request_path, request_sha, release_path, release_sha)
        capture = Path(release['guard_capture']); capture.mkdir(mode=0o700)
        _write_json(capture / 'consumed-release.json', {'release_sha256': release_sha,
                    'request_sha256': request_sha, 'nonce': release['nonce']})
        docker = Docker(capture / 'docker.log', signals=latch, sudo=True)
        core_entered = True
        result = image.ImageOwner(request, docker=docker, signals=latch).run()
        proof = prove_retired(request, result, docker, capture)
        proof['interrupted_signal'] = latch.requested
        _write_json(capture / 'guard-result.json', proof)
        if _read_json_snapshot(capture / 'guard-result.json', 'published guard proof')[0] != proof:
            raise RuntimeError('guard proof publication differs')
        _development_lock(lock_path, lock_identity, lock_owner, held_fd=fd)
        safe = True
        return proof
    finally:
        if fd is not None:
            if core_entered and not safe:
                quarantine_root_lock(fd, release_path)
            fcntl.flock(fd, fcntl.LOCK_UN); os.close(fd)
        signal.pthread_sigmask(signal.SIG_BLOCK, DEFERRED_SIGNALS)
        if entered:
            latch.__exit__(None, None, None)
        for number, handler in handlers.items():
            signal.signal(number, handler)
        signal.pthread_sigmask(signal.SIG_SETMASK, mask)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('request', 'request-sha256', 'release', 'release-sha256'):
        parser.add_argument('--' + name, required=True)
    args = parser.parse_args(argv)
    proof = guarded_execute(Path(args.request), args.request_sha256,
                            Path(args.release), args.release_sha256)
    print(json.dumps(proof, sort_keys=True))
    return 0 if proof['owner_status'] == 'PASS' and proof['interrupted_signal'] is None else 1


if __name__ == '__main__':
    raise SystemExit(main())
