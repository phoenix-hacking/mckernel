#!/usr/bin/env python3
"""One released, read-only recheck of the retained authority3 build artifacts.

This does not rerun the build driver or promote the original failed receipt.
The CLI retains the development lock indefinitely if ownership is uncertain.
"""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import shutil
import stat
import subprocess
import uuid

from native_rust_exact_build_container_owner import (
    CliSignals, Docker, Lease, RESOURCE_ARGS, check_profile, digest, inspect, retire,
)
from native_rust_exact_build_image_rebind_probe import (
    _absence, _development_lock, _read_json_snapshot, _write_json,
    DEFERRED_SIGNALS, DEVELOPMENT_LOCK, DEVELOPMENT_LOCK_IDENTITY,
    quarantine_root_lock, validate_image_inspect,
)
from native_rust_exact_mckernel_image_container_owner import _SHARED_HEAVY_ENTRY_CONTRACT

REPO = Path('/home/holden/mckernel')
ROOT = Path('/home/holden/mckernel-work/scratch')
SOURCE = ROOT / 'mckernel-exact-candidate-scratch-22-authority3'
OUTPUT = ROOT / 'mckernel-exact-candidate-scratch-22-authority3-output'
BASELINE = ROOT / 'mckernel-exact-candidate-scratch-22-authority3-evidence/build'
IMAGE = 'sha256:0f8ad280e47d76b23554de4aec411752e1f779f9b2fc7fece6b0b3375dc9775d'
CANDIDATE = '942c927b1ec93cc31284ff498455909d9bb2d0fc'
TREE = '07d05c1bb2ea5f4b6a3817ba55cd32afe56c8d59'
SCRATCH_UUID = '2a5768c8-718d-4914-bdc0-6b32c5a92a52'
FAILED_RECEIPT_SHA256 = '3002334af1776f5e90fe19c33a31e32ff6b431f5946803d2c0969b739e260c96'
FROZEN_FILES = ('.github/workflows/native-rust-host-modules-exact-build.yml',
                'scripts/native_rust_exact_build_offline.py')
ARTIFACTS = ('build/arch/x86/boot/bzImage',
             'build/drivers/misc/mckernel/ihk.ko',
             'build/drivers/misc/mckernel/ihk-smp-x86_64.ko',
             'build/drivers/misc/mckernel/mcctrl.ko')
OWNER = 'scripts/native_exact_scratch22_authority3_artifact_revalidate_owner.py'
TEST = 'scripts/tests/test_native_exact_scratch22_authority3_artifact_revalidate_owner.py'
DRIVER = 'scripts/native_exact_scratch22_authority3_artifact_revalidate.py'
CHECKER = 'scripts/ihk_native_lifecycle_check.py'
SOURCES = (OWNER, TEST, DRIVER, CHECKER,
           'scripts/native_rust_exact_build_container_owner.py',
           'scripts/native_rust_exact_build_image_rebind_probe.py',
           'scripts/native_rust_exact_mckernel_image_container_owner.py')
COMMAND = ['/usr/bin/python3', '-I', '/driver.py',
           '--prior-evidence', '/baseline-evidence', '--capture', '/capture']
SCHEMA = 'scratch22-authority3.artifact-revalidation-release.v1'


def canonical(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':'),
                       allow_nan=False) + '\n').encode()


def profile():
    return {'image': IMAGE, 'cpus': '2-5', 'nano_cpus': 4000000000,
            'memory': 12 * 2**30, 'memory_swap': 12 * 2**30, 'pids': 512,
            'network': 'none', 'read_only_root': True, 'cap_drop': ['ALL'],
            'security_opt': ['no-new-privileges'], 'tmpfs_bytes': 256 * 2**20,
            'user': '%d:%d' % (os.getuid(), os.getgid()), 'command': COMMAND,
            'read_only_inputs': [str(SOURCE), str(OUTPUT), str(BASELINE),
                                 str(REPO / DRIVER), str(REPO / CHECKER)],
            'development_lock': [27, 4]}


def safe_path(path, directory=False):
    path = Path(path)
    if (not path.is_absolute() or '..' in path.parts or
            path != path.resolve(strict=True) or
            any(part.is_symlink() for part in (path, *path.parents)) or
            not (path.is_dir() if directory else path.is_file())):
        raise RuntimeError('unsafe input path: ' + str(path))
    return path


def bound_json(pointer):
    return _read_json_snapshot(pointer['path'], 'bound prerequisite',
                               pointer['sha256'])[0]


def admit_retained_bindings(request, receipt):
    """Join six selected request rows to the immutable failed build evidence."""
    expected_paths = {str(SOURCE / path) for path in FROZEN_FILES}
    expected_paths.update(str(OUTPUT / path) for path in ARTIFACTS)
    bindings = request.get('retained_file_bindings', {})
    if set(bindings) != expected_paths:
        raise RuntimeError('exact six retained file bindings required')
    if request.get('retained_candidate') != {'head': CANDIDATE, 'tree': TREE}:
        raise RuntimeError('exact retained candidate HEAD/tree required')
    if request.get('scratch_binding') != {'uuid': SCRATCH_UUID, 'device': ROOT.stat().st_dev}:
        raise RuntimeError('exact scratch UUID/device binding required')
    provenance_row = receipt['evidence']['build/local-provenance.json']
    provenance = bound_json({'path': str(BASELINE / 'local-provenance.json'),
                             'sha256': provenance_row['sha256']})
    if (provenance.get('candidate_sha') != CANDIDATE or
            provenance.get('driver_sha256') != receipt['request']['driver_path_sha256'] or
            receipt['request']['source_root'] != str(SOURCE) or
            receipt['request']['output_root'] != str(OUTPUT)):
        raise RuntimeError('original compiler provenance differs')
    frozen_hashes = (provenance['workflow_sha256'], provenance['driver_sha256'])
    for relative, expected in zip(FROZEN_FILES, frozen_hashes):
        if bindings[str(SOURCE / relative)].get('sha256') != expected:
            raise RuntimeError('frozen source binding differs from original receipt')
    for relative in ARTIFACTS:
        if bindings[str(OUTPUT / relative)] != receipt['outputs'][relative]:
            raise RuntimeError('artifact binding differs from original receipt')
    for row in bindings.values():
        if (set(row) != {'sha256', 'size'} or type(row['size']) is not int or row['size'] < 0 or
                not re.fullmatch('[0-9a-f]{64}', str(row['sha256']))):
            raise RuntimeError('invalid retained file binding')


def observe_candidate():
    environment = {'PATH': '/usr/bin:/bin', 'LANG': 'C', 'LC_ALL': 'C',
                   'GIT_CONFIG_NOSYSTEM': '1', 'GIT_CONFIG_GLOBAL': '/dev/null',
                   'GIT_NO_REPLACE_OBJECTS': '1', 'GIT_TERMINAL_PROMPT': '0'}
    observed = subprocess.run(['/usr/bin/git', '--no-replace-objects', '-C', str(SOURCE),
                               'rev-parse', '--verify', 'HEAD'], env=environment,
                              capture_output=True, text=True, timeout=30, check=True)
    tree = subprocess.run(['/usr/bin/git', '--no-replace-objects', '-C', str(SOURCE),
                           'rev-parse', '--verify', 'HEAD^{tree}'], env=environment,
                          capture_output=True, text=True, timeout=30, check=True)
    return {'head': observed.stdout.strip(), 'tree': tree.stdout.strip()}


def observe_scratch():
    observed = subprocess.run(['/usr/bin/findmnt', '--json', '--output', 'UUID,MAJ:MIN,TARGET',
                               '--target', str(ROOT)], capture_output=True, text=True,
                              timeout=30, check=True)
    rows = json.loads(observed.stdout)['filesystems']
    device = ROOT.stat().st_dev
    if (len(rows) != 1 or rows[0]['target'] != str(ROOT) or
            rows[0]['maj:min'] != '%d:%d' % (os.major(device), os.minor(device))):
        raise RuntimeError('scratch live mount/device differs')
    return {'uuid': rows[0]['uuid'], 'device': device}


def stable_hash_matches(path, row):
    path = safe_path(path)
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC)
    fields = ('st_dev', 'st_ino', 'st_mode', 'st_nlink', 'st_size', 'st_mtime_ns', 'st_ctime_ns')
    identity = lambda meta: tuple(getattr(meta, field) for field in fields)
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or before.st_size != row['size']:
            raise RuntimeError('retained file size/type differs: ' + str(path))
        checksum = hashlib.sha256()
        size = 0
        while True:
            block = os.read(fd, 1024 * 1024)
            if not block:
                break
            checksum.update(block)
            size += len(block)
        if (identity(before) != identity(os.fstat(fd)) or
                identity(before) != identity(os.stat(path, follow_symlinks=False)) or
                size != before.st_size or checksum.hexdigest() != row['sha256']):
            raise RuntimeError('retained file hash/identity differs: ' + str(path))
    finally:
        os.close(fd)


def verify_retained_bindings(request):
    if observe_scratch() != request['scratch_binding']:
        raise RuntimeError('scratch UUID/device changed')
    if observe_candidate() != request['retained_candidate']:
        raise RuntimeError('retained candidate HEAD/tree changed')
    for path, row in request['retained_file_bindings'].items():
        stable_hash_matches(Path(path), row)


def authenticate_request(path, checksum):
    if not re.fullmatch('[0-9a-f]{64}', str(checksum or '')):
        raise RuntimeError('exact external request SHA256 required')
    request, observed = _read_json_snapshot(path, 'one-shot release', checksum)
    if (request.get('schema') != SCHEMA or
            request.get('status') != 'PASS_EXECUTION_RELEASE' or
            type(request.get('execution_count')) is not int or request['execution_count'] != 1 or
            request.get('candidate_sha') != CANDIDATE or
            request.get('profile') != profile() or
            request.get('strict_fresh_build_pass') is not False or
            request.get('runtime_or_acceptance_credit') is not False):
        raise RuntimeError('exact diagnostic execution release required')
    review = bound_json(request['execution_review'])
    payload = {key: value for key, value in request.items() if key != 'execution_review'}
    if (review.get('decision') != 'PASS_EXECUTION' or
            review.get('implementation_ownership') is not False or
            not request.get('author') or not review.get('reviewer') or
            request['author'] == review['reviewer'] or
            review.get('reviewed_request_payload_sha256') != hashlib.sha256(canonical(payload)).hexdigest()):
        raise RuntimeError('independent exact request review required')
    if set(request.get('source_sha256', {})) != set(SOURCES):
        raise RuntimeError('small exact source closure required')
    for relative in SOURCES:
        if digest(safe_path(REPO / relative)) != request['source_sha256'][relative]:
            raise RuntimeError('released source drift: ' + relative)
    cleanup = bound_json(request['accepted_cleanup'])
    if (cleanup.get('schema') != 'scratch22-authority3.cleanup-result.v1' or
            cleanup.get('status') != 'PASS_EXECUTED' or
            cleanup.get('terminal') is not True or cleanup.get('container_absent') is not True):
        raise RuntimeError('accepted authority3 cleanup required')
    if request['baseline_receipt']['sha256'] != FAILED_RECEIPT_SHA256:
        raise RuntimeError('exact original failed owner receipt required')
    baseline_receipt = bound_json(request['baseline_receipt'])
    if (Path(request['baseline_receipt']['path']) != BASELINE.parent / 'receipt.json' or
            baseline_receipt.get('candidate_sha') != CANDIDATE or
            baseline_receipt.get('status') != 'FAIL'):
        raise RuntimeError('retained original failed receipt required')
    admit_retained_bindings(request, baseline_receipt)
    for directory in (SOURCE, OUTPUT, BASELINE):
        safe_path(directory, directory=True)
    capture = Path(request['capture'])
    if (capture.parent != ROOT or not capture.name.startswith('native-artifact-revalidate-authority3-') or
            os.path.lexists(capture) or os.path.lexists(lease_path(capture)) or
            capture.name.endswith(('.json', '.py'))):
        raise RuntimeError('fresh exact capture and lease required')
    safe_path(ROOT, directory=True)
    # Bind live input roots to fresh release identities without corpus hashing.
    if set(request.get('input_identities', {})) != {str(p) for p in (SOURCE, OUTPUT, BASELINE)}:
        raise RuntimeError('exact input root identities required')
    for directory in (SOURCE, OUTPUT, BASELINE):
        meta = directory.stat()
        if request['input_identities'][str(directory)] != [meta.st_dev, meta.st_ino]:
            raise RuntimeError('input root identity drift')
    boot = Path('/proc/sys/kernel/random/boot_id').read_text().strip()
    if request.get('boot_id') != boot:
        raise RuntimeError('release boot identity differs')
    for stale in (ROOT / 'native-exact-build-lease-scratch-22-authority3.json',
                  ROOT / 'native-exact-candidate-operational-exclusion-scratch18.json',
                  Path(_SHARED_HEAVY_ENTRY_CONTRACT.SHARED_HEAVY_LOCK_PATH)):
        if os.path.lexists(stale):
            raise RuntimeError('prior or active ownership remains: ' + str(stale))
    return request, observed


def lease_path(capture):
    return capture.parent / ('.' + capture.name + '.lease.json')


def check_capacity():
    if shutil.disk_usage(REPO).free < 17 * 2**30 or shutil.disk_usage(ROOT).free < 13 * 2**30:
        raise RuntimeError('16/12 GiB floors plus 1 GiB capture headroom required')
    memory = dict(line.split(':', 1) for line in Path('/proc/meminfo').read_text().splitlines())
    if int(memory['MemAvailable'].split()[0]) * 1024 < 16 * 2**30:
        raise RuntimeError('16 GiB available RAM required')


def mounts(capture):
    return [(SOURCE, '/src', False), (OUTPUT, '/out', False),
            (BASELINE, '/baseline-evidence', False),
            (REPO / DRIVER, '/driver.py', False),
            (REPO / CHECKER, '/src/scripts/ihk_native_lifecycle_check.py', False),
            (capture / 'payload', '/capture', True)]


def create_args(name, nonce, capture):
    args = ['create', '--name', name, '--label', 'mckernel.owner=' + nonce,
            '--init', '--network=none', '--ipc=private', *RESOURCE_ARGS,
            '--user', '%d:%d' % (os.getuid(), os.getgid()), '--read-only',
            '--cap-drop=ALL', '--security-opt=no-new-privileges',
            '--tmpfs', '/tmp:rw,nodev,nosuid,size=256m']
    for source, target, writable in mounts(capture):
        args += ['--mount', 'type=bind,src=%s,dst=%s%s' %
                 (source, target, '' if writable else ',readonly')]
    return args + ['--entrypoint', '/usr/bin/sleep', IMAGE, 'infinity']


def validate_container(info, nonce, capture):
    check_profile(info, IMAGE, nonce, network='none', readonly=True)
    expected = {(str(source), target, writable) for source, target, writable in mounts(capture)}
    actual = info.get('Mounts', [])
    if (len(actual) != len(expected) or any(row.get('Type') != 'bind' or
            row.get('Propagation') not in ('rprivate', '') for row in actual) or
            {(row.get('Source'), row.get('Destination'), row.get('RW')) for row in actual} != expected):
        raise RuntimeError('exact read-only input/fresh capture mount profile differs')
    host, config = info.get('HostConfig', {}), info.get('Config', {})
    if (host.get('Tmpfs') != {'/tmp': 'rw,nodev,nosuid,size=256m'} or
            host.get('RestartPolicy') != {'Name': 'no', 'MaximumRetryCount': 0} or
            config.get('User') != '%d:%d' % (os.getuid(), os.getgid()) or
            config.get('Entrypoint') != ['/usr/bin/sleep'] or config.get('Cmd') != ['infinity']):
        raise RuntimeError('effective command/user/tmp/restart profile differs')


def execute(request, checksum, request_path, signals, runner=None):
    """Called only inside the guarded CLI; fake transports are test-only."""
    capture = Path(request['capture'])
    shared, record = _SHARED_HEAVY_ENTRY_CONTRACT.acquire_heavy_operation(
        {'kind': 'authority3-artifact-revalidation', 'request': str(request_path),
         'request_sha256': checksum, 'capture': str(capture)}, 'build')
    name = 'mckernel-authority3-revalidate-' + uuid.uuid4().hex
    lease = Lease(lease_path(capture), name)
    docker = None
    attempted = created = retired = absent = released = False
    result = {'status': 'FAIL', 'strict_fresh_build_pass': False,
              'runtime_or_acceptance_credit': False, 'request_sha256': checksum,
              'container_name': name, 'lease_path': str(lease.path),
              'shared_path': str(shared), 'ownership_released': False}
    try:
        capture.mkdir(mode=0o700)
        (capture / 'payload').mkdir(mode=0o700)
        # Durable one-shot consumption survives even a clean diagnostic failure.
        _write_json(Path(str(request_path) + '.consumed.json'),
                    {'request_sha256': checksum, 'capture': str(capture), 'container_name': name})
        lease.acquire()
        verify_retained_bindings(request)
        _write_json(capture / 'retained-inputs-before-create.json', {'verified': True})
        docker = runner or Docker(capture / 'docker.log', signals=signals, sudo=True)
        image = json.loads(docker.call(['image', 'inspect', IMAGE]).stdout)
        validate_image_inspect(image, IMAGE)
        attempted = True
        docker.call(create_args(name, lease.nonce, capture))
        created = True
        before = inspect(docker, name)
        validate_container(before, lease.nonce, capture)
        _write_json(capture / 'inspect-before-start.json', before)
        docker.call(['start', name])
        command = docker.call(['exec', name, *COMMAND], timeout=1800, check=False)
        result['payload_exit_code'] = command.returncode
        payload, _ = _read_json_snapshot(capture / 'payload/result.json', 'fresh payload result')
        if (command.returncode == 0 and payload.get('status') == 'PASS_DIAGNOSTIC_FINAL_CHECKS' and
                payload.get('strict_fresh_build_pass') is False and
                payload.get('runtime_or_acceptance_credit') is False):
            result['status'] = 'PASS_DIAGNOSTIC_REVALIDATION'
        else:
            result['error'] = 'diagnostic payload failed unchanged final checks'
    except BaseException as exc:
        result.update(status='FAIL', error=str(exc))
    finally:
        signals.cleaning = True
        try:
            # A lost create response is never converted to a clean retirement.
            if attempted and not created:
                raise RuntimeError('Docker create ownership is uncertain')
            if docker is not None and docker.client_retirement_unproven:
                raise RuntimeError('Docker client retirement is uncertain')
            if created:
                terminal = retire(docker, name, lease.nonce)
                retired = True
                _write_json(capture / 'inspect-terminal.json', terminal)
                try:
                    verify_retained_bindings(request)
                    _write_json(capture / 'retained-inputs-after-retirement.json', {'verified': True})
                except BaseException as exc:
                    result.update(status='FAIL', retained_input_error=str(exc))
                docker.call(['rm', name])
                _write_json(capture / 'container-absence.json', _absence(docker, name))
                absent = True
                if docker.client_retirement_unproven:
                    raise RuntimeError('Docker retirement client is uncertain')
            # Before create, no container was attempted; this is a clean refusal.
            lease.release()
            cleanup_proof = {'status': 'PASS', 'retired': True,
                             'cleanup_separately_required': False,
                             'terminal_container_info': None,
                             'terminal_container_info_current': True}
            released = _SHARED_HEAVY_ENTRY_CONTRACT._release_exclusion(shared, record, cleanup_proof)
            if not released or os.path.lexists(shared) or os.path.lexists(lease.path):
                raise RuntimeError('shared or lease release is unproven')
            _write_json(capture / 'ownership-release.json', {'released': True,
                        'container_attempted': attempted, 'container_absent': absent})
            result['ownership_released'] = True
        except BaseException as exc:
            result.update(status='FAIL', cleanup_error=str(exc))
        result.update(retired=retired, container_absent=absent,
                      shared_released=released,
                      client_retirement_unproven=bool(docker and docker.client_retirement_unproven))
        if signals.requested is not None:
            result.update(status='FAIL', interrupted_signal=signals.requested)
        if capture.is_dir():
            _write_json(capture / 'owner-result.json', result)
    return result


def guarded_execute(request_path, checksum, lock_path=DEVELOPMENT_LOCK,
                    lock_identity=DEVELOPMENT_LOCK_IDENTITY, lock_owner=(0, 0)):
    previous_mask = signal.pthread_sigmask(signal.SIG_BLOCK, DEFERRED_SIGNALS)
    handlers = {number: signal.getsignal(number) for number in DEFERRED_SIGNALS}
    signals = CliSignals()
    lockfd = None
    entered = core_entered = safe = False
    try:
        signals.__enter__()
        entered = True
        for number in DEFERRED_SIGNALS:
            signal.signal(number, signals.receive)
        signal.pthread_sigmask(signal.SIG_SETMASK, previous_mask)
        lockfd = _development_lock(lock_path, lock_identity, lock_owner)
        signals.check()
        request, observed = authenticate_request(request_path, checksum)
        if os.path.lexists(str(request_path) + '.consumed.json'):
            raise RuntimeError('one-shot request already consumed')
        check_capacity()
        core_entered = True
        result = execute(request, observed, request_path, signals)
        capture = Path(request['capture'])
        recorded, _ = _read_json_snapshot(capture / 'owner-result.json', 'actual owner result')
        release, _ = _read_json_snapshot(capture / 'ownership-release.json', 'actual release proof')
        if (recorded != result or result.get('ownership_released') is not True or
                release.get('released') is not True or
                result.get('client_retirement_unproven') is not False or
                os.path.lexists(result['lease_path']) or os.path.lexists(result['shared_path'])):
            raise RuntimeError('root guard cannot prove ownership release')
        if release.get('container_attempted') is True:
            absence, _ = _read_json_snapshot(capture / 'container-absence.json', 'absence proof')
            name = result['container_name']
            if (absence != {'container_name': name, 'absent': True, 'inspect_exit_code': 1,
                            'stderr': 'Error: No such object: %s\n' % name} or
                    result.get('retired') is not True or result.get('container_absent') is not True):
                raise RuntimeError('root guard cannot prove container retirement')
        _development_lock(lock_path, lock_identity, lock_owner, held_fd=lockfd)
        safe = True
        return result
    finally:
        if lockfd is not None:
            if core_entered and not safe:
                quarantine_root_lock(lockfd, request_path)
            fcntl.flock(lockfd, fcntl.LOCK_UN)
            os.close(lockfd)
        signal.pthread_sigmask(signal.SIG_BLOCK, DEFERRED_SIGNALS)
        if entered:
            signals.__exit__(None, None, None)
        for number, handler in handlers.items():
            signal.signal(number, handler)
        signal.pthread_sigmask(signal.SIG_SETMASK, previous_mask)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--request', required=True)
    parser.add_argument('--expected-request-sha256', required=True)
    args = parser.parse_args(argv)
    result = guarded_execute(Path(args.request), args.expected_request_sha256)
    print(json.dumps(result, sort_keys=True))
    return 0 if result['status'] == 'PASS_DIAGNOSTIC_REVALIDATION' else 1


if __name__ == '__main__':
    raise SystemExit(main())
