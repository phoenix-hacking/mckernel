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

sys.path.insert(0, '/home/holden/mckernel-work/host-preparation/phase5-opt-in-image-lock-binding-20261020-1/runtime-binding-correction-1')
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
SELF = '/home/holden/mckernel-work/host-preparation/phase5-opt-in-image-lock-binding-20261020-1/runtime-binding-correction-1/image-execution-preparation-1/native_exact_current_optin_image_guard.py'
TEST = '/home/holden/mckernel-work/host-preparation/four-callback-affinity-image-preparation-20261019-1/affinity-full-syscall-include-correction-1/fresh-full-attempt-1/heavy-proposal-1/test_fresh_full_metadata_joins.py'
SOURCES = ('/home/holden/mckernel-work/host-preparation/phase5-opt-in-image-lock-binding-20261020-1/runtime-binding-correction-1/image-execution-preparation-1/native_exact_current_optin_image_guard.py', '/home/holden/mckernel-work/host-preparation/four-callback-affinity-image-preparation-20261019-1/affinity-full-syscall-include-correction-1/fresh-full-attempt-1/heavy-proposal-1/test_fresh_full_metadata_joins.py', '/home/holden/mckernel-work/host-preparation/four-callback-affinity-image-preparation-20261019-1/adapters/native_rust_exact_build_container_owner.py', '/home/holden/mckernel-work/host-preparation/four-callback-affinity-image-preparation-20261019-1/adapters/native_rust_exact_build_image_prepare.py', '/home/holden/mckernel-work/host-preparation/four-callback-affinity-image-preparation-20261019-1/adapters/native_rust_exact_build_image_rebind.py', '/home/holden/mckernel-work/host-preparation/four-callback-affinity-image-preparation-20261019-1/adapters/native_rust_exact_build_image_rebind_probe.py', '/home/holden/mckernel-work/host-preparation/phase5-opt-in-image-lock-binding-20261020-1/runtime-binding-correction-1/native_rust_exact_build_offline.py', '/home/holden/mckernel-work/host-preparation/four-callback-affinity-image-preparation-20261019-1/adapters/native_rust_exact_disk_build_wrapper.py', '/home/holden/mckernel-work/host-preparation/phase5-opt-in-image-lock-binding-20261020-1/runtime-binding-correction-1/native_rust_exact_mckernel_image_container_owner.py', '/home/holden/mckernel-work/host-preparation/phase5-opt-in-image-lock-binding-20261020-1/producer/native_rust_exact_mckernel_image_offline.py', '/home/holden/mckernel-work/host-preparation/four-callback-affinity-image-preparation-20261019-1/adapters/native_rust_exact_mckernel_image_request_prepare.py')


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
    """Exact current6959 materialization and separately reviewed runtime binding."""
    source_ref = {'path': '/home/holden/mckernel-work/host-preparation/phase5-opt-in-production-link-image-independent-review-20261020-1/ACTUAL-6959-SOURCE-MATERIALIZATION-AND-IDENTITY-BINDING-REVIEW.json', 'sha256': 'e9aafd94f1c3957453d9fd3a7b2329832fe62baea2a0f781fb02b78ac4badb1c', 'bytes': 6934}
    runtime_ref = {'path': '/home/holden/mckernel-work/host-preparation/phase5-opt-in-production-link-image-independent-review-20261020-1/FULL-RUNTIME-ADAPTER-OWNER-REQUEST-BINDING-REVIEW.json', 'sha256': '45fcabf1f8b146adf4541a6773ca58674a0f697e84bcf07a8a42571e87778c42', 'bytes': 5664}
    basis_ref = {'path': '/home/holden/mckernel-work/host-preparation/phase5-opt-in-image-lock-binding-20261020-1/runtime-binding-correction-1/image-request-SOURCE-BOUND-PROPOSAL.json', 'sha256': 'd04fac3295bfd7968f9c1d9a06c8c06648fac96e33b5e11c73c0ce299a864638', 'bytes': 26524702}
    if release.get('source_materialization_acceptance') != source_ref or release.get('runtime_binding_acceptance') != runtime_ref or release.get('bound_request_basis') != basis_ref:
        raise RuntimeError('exact current source/runtime request authority required')
    source = bound(source_ref)
    runtime = bound(runtime_ref)
    if source.get('status') != 'PASS_ACTUAL_6959_SOURCE_MATERIALIZATION_AND_SOURCE_IDENTITY_BINDING_ONLY' or runtime.get('status') != 'PASS_EXACT_FULL_RUNTIME_ADAPTER_OWNER_AND_REQUEST_BINDINGS_ONLY':
        raise RuntimeError('current independent source/runtime review status differs')
    if release.get('ordinary_result_acceptance') != source_ref or release.get('prerequisites', {}).get('ordinary') != source['actual_evidence'][0]:
        raise RuntimeError('exact independently reviewed current ordinary whole required')
    if runtime.get('reviewed_request_proposal') != basis_ref:
        raise RuntimeError('reviewed runtime request basis differs')
    receipt = source['source_receipt']
    if receipt.get('source_derivative_sha256') != request.get('source_derivative_sha256') or receipt.get('materialization_sha256') != request.get('materialization_sha256'):
        raise RuntimeError('reviewed source derivation/materialization differs')
    if source.get('source_identity') != request.get('source_identity') or [request['source_identity'][k] for k in ('dev','inode','uid','gid','mode')] != identity:
        raise RuntimeError('actual current source identity differs')
    basis = bound(basis_ref)
    # Only genuinely live device/backup identities may differ from the reviewed
    # source-bound request. No source/compiler/owner/namespace field is mutable.
    expected = dict(basis)
    expected['backup_identity'] = request.get('backup_identity')
    expected['disk_admission'] = dict(basis['disk_admission'])
    for key in ('host_device','scratch_device'):
        expected['disk_admission'][key] = request['disk_admission'].get(key)
    if request != expected:
        raise RuntimeError('current request changed outside exact late identity fields')
    if ordinary.get('status') != 'PASS' or len(ordinary.get('records',[])) != 2:
        raise RuntimeError('actual current two-command whole result missing')
    for row in ordinary['records']:
        if row.get('returncode') != 0 or row.get('direct_child_joined') is not True or row.get('group_absent') is not True or row.get('closed_streams') is not True or row.get('error') is not None or row.get('retirement_error') is not None:
            raise RuntimeError('current source directjoin/retirement differs')
        for stream in row['captures'].values():
            raw=Path(stream['path']).read_bytes()
            if len(raw)!=stream['size'] or hashlib.sha256(raw).hexdigest()!=stream['sha256']:
                raise RuntimeError('current source closed capture drift')


def authenticate(request_path, request_sha, release_path, release_sha):
    release = bound({'path': str(release_path), 'sha256': release_sha})
    request = bound({'path': str(request_path), 'sha256': request_sha})
    if (os.geteuid() != 1000 or release.get('schema') != 'fp-save-thin.image-guard-release.v1' or
            release.get('status') != 'PASS_EXECUTION_RELEASE' or
            type(release.get('execution_count')) is not int or release['execution_count'] != 1 or
            release.get('request') != {'path': str(request_path), 'sha256': request_sha} or
            request.get('candidate_sha') != CANDIDATE or
            request.get('candidate_identity_scope') != 'base_git_commit_only' or
            request.get('source_derivative_sha256') != '547be54d6726f8a577fcd56110b89491288faa677e22a84cc7f8e24e6b893867' or
            release.get('source_derivative_sha256') != request.get('source_derivative_sha256') or
            request.get('materialization_sha256') != 'c3dc8e79397b00afc3cf95b5debf20977a608a4a0f98befc7e5472a57bbe859a' or
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
                        ('native_baseline', 'PASS_DIAGNOSTIC_REVALIDATION'), ('ordinary', None)):
        prerequisite = bound(release['prerequisites'][key])
        if key!='ordinary' and prerequisite.get('status') != status:
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
            not capture.name.startswith('native-rust-phase5-current-optin-image-guard-') or
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
