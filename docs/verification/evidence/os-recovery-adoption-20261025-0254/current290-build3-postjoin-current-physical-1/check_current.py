"""Functional McKernel OS work only; no security testing.

Observe one joined build, retaining its stopped container and all evidence.
The only lock operation opens and closes a new, nonblocking probe description.
"""
import fcntl
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import time

EVIDENCE = Path(__file__).resolve().parent.parent
ADMISSION = EVIDENCE / 'ROOT-CURRENT290-BUILD-ONLY-ADMISSION-3'
OUTPUT = ADMISSION / 'OUTPUT'
CID = '5487cf9508267dd943b917980bffdfd6adcf3c4ca721112a84beaa3d892614b2'
MUTEX = Path('/run/lock/mckernel-development.lock')


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def read_json(path):
    return json.loads(path.read_text())


def lock_rows():
    rows = Path('/proc/locks').read_text().splitlines()
    return [row for row in rows if any(
        len(part.split(':')) == 3 and part.split(':')[-1] == '4'
        and part.split(':')[:2] == ['00', '1b'] for part in row.split())]


def mutex_metadata(metadata):
    return (stat.S_ISREG(metadata.st_mode) and (metadata.st_dev, metadata.st_ino) == (27, 4)
            and metadata.st_uid == metadata.st_gid == 0 and metadata.st_size == 0
            and metadata.st_nlink == 1 and stat.S_IMODE(metadata.st_mode) == 0o644)


def observe():
    require(os.getuid() == os.geteuid() == 1000, 'ordinary host UID required')
    require(time.time() < 1793100290, 'fixed deadline expired')
    result = {'scope': 'Functional McKernel OS/apps and Rust/assembly migration only; no security testing.',
              'observed_at_epoch': time.time(), 'container_retained': CID}
    for name in ['RUNNER.JOINED.json', 'BUILD-LOCAL-TERMINAL.json']:
        value = read_json(ADMISSION / 'HOLDER' / name)
        require(value['joined'] is True and value['returncode'] == 0, name)
    require(read_json(ADMISSION / 'ROOT-ACTUAL-HOLDER-TOOL35276-RESULT.json')['exit_code'] == 0,
            'actual caller join missing')
    claim = read_json(OUTPUT / 'claim.json')
    grant_path = ADMISSION / 'ROOT-ACTUAL-ONE-BUILD-ONLY-GRANT.json'
    grant_bytes = grant_path.read_bytes()
    require(claim['grant'] == {'path': str(grant_path), 'bytes': len(grant_bytes),
            'sha256': hashlib.sha256(grant_bytes).hexdigest()}, 'actual claim/grant binding')
    require(json.loads(grant_bytes)['nonce'] == 'd115c3b6c48b45c0afb6f247106bf30f', 'consumed actual nonce')
    require((OUTPUT / 'container.cid').read_text().strip() == CID and
            read_json(OUTPUT / 'terminal.json')['container'] == CID, 'actual CID binding')
    result['retired_births'] = []
    for pid, expected in [(1224701, 84038706), (1224936, 84046403)]:
        path = Path('/proc') / str(pid) / 'stat'
        try:
            raw = path.read_text()
        except FileNotFoundError:
            result['retired_births'].append({'pid': pid, 'starttime': expected, 'state': 'absent'})
            continue
        raise RuntimeError('recorded numeric actor PID still present; refuse reuse')
    require(not lock_rows(), 'permanent mutex remains held')
    result['exclusive_probes'] = []
    for _ in range(2):
        metadata = MUTEX.lstat()
        require(mutex_metadata(metadata),
                'permanent mutex path changed')
        descriptor = os.open(MUTEX, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
        try:
            actual = os.fstat(descriptor)
            require(mutex_metadata(actual), 'probe identity changed')
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
            rows = lock_rows()
            require(len(rows) == 1 and str(os.getpid()) in rows[0].split(), 'probe kernel row mismatch')
            require(mutex_metadata(MUTEX.lstat()) and mutex_metadata(os.fstat(descriptor)), 'probe final identity')
            result['exclusive_probes'].append(rows[0])
        finally:
            os.close(descriptor)
        require(not lock_rows() and mutex_metadata(MUTEX.lstat()), 'probe did not retire or path changed')
    command = ['/usr/bin/sudo', '-A', '/usr/bin/docker', '--host=unix:///var/run/docker.sock',
               'inspect', CID]
    completed = subprocess.run(command, capture_output=True, text=True, timeout=30)
    result['docker_observation'] = {'argv': command, 'returncode': completed.returncode,
                                    'stdout': completed.stdout, 'stderr': completed.stderr}
    require(completed.returncode == 0, 'retained container inspection failed')
    inspected = json.loads(completed.stdout)
    require(len(inspected) == 1, 'exact one inspected container')
    container = inspected[0]
    require(container['Id'] == CID and container['Name'] == '/current290-build-only-d115c3b6c48b45c0afb6f247106bf30f'
            and container['Image'] == 'sha256:41778f1f22fd68897c1209e225a9807a197ed47bf0edd17835821bb5986e50b5', 'exact container identity')
    state = container['State']
    require(state['Paused'] is False and state['Restarting'] is False, 'container transitional state')
    require(state == read_json(OUTPUT / 'terminal.json')['state'], 'retained terminal state changed')
    require(state['Running'] is False and state['Pid'] == 0 and state['ExitCode'] == 0
            and not state['OOMKilled'], 'container not successful terminal')
    result['outputs'] = []
    for command_result in read_json(OUTPUT / 'work/evidence/worker-result.json')['commands']:
        artifact = command_result['output']
        path = OUTPUT / artifact['path'].removeprefix('/')
        require(path.stat().st_size == artifact['bytes'] and
                hashlib.sha256(path.read_bytes()).hexdigest() == artifact['sha256'], 'output bytes changed')
        result['outputs'].append(artifact)
    result['capacity'] = {}
    for name in ['/home/holden/mckernel', '/home/holden/mckernel-work/scratch']:
        filesystem = os.statvfs(name)
        result['capacity'][name] = {'available_bytes': filesystem.f_bavail * filesystem.f_frsize,
                                   'device': os.stat(name).st_dev}
    require(result['capacity']['/home/holden/mckernel']['available_bytes'] >= 16 * 2**30, 'HOST floor')
    require(result['capacity']['/home/holden/mckernel-work/scratch']['available_bytes'] >= 12 * 2**30,
            'scratch floor')
    require(os.stat('/home/holden/mckernel-work/scratch').st_dev == 1828, 'scratch mount identity')
    mount = subprocess.run(['/usr/bin/findmnt', '-J', '-T', '/home/holden/mckernel-work/scratch',
                             '-o', 'TARGET,SOURCE,FSTYPE,OPTIONS,UUID,MAJ:MIN'], capture_output=True, text=True, timeout=10)
    result['mount_observation'] = {'returncode': mount.returncode, 'stdout': mount.stdout, 'stderr': mount.stderr}
    expected_mount = read_json(EVIDENCE / 'ROOT-NEW18H-KEEPER-SUCCESSOR-PREPARATION-2/ROOT-ACTUAL-POSTJOIN-CURRENT-PHYSICAL.json')['mount']
    require(mount.returncode == 0 and json.loads(mount.stdout)['filesystems'] == [expected_mount], 'same scratch mount/UUID')
    result['meminfo'] = Path('/proc/meminfo').read_text()
    result['status'] = 'PASS_BUILD3_POSTJOIN_CURRENT_PHYSICAL_OBSERVATION'
    result['native_execution_authority'] = False
    return result


if __name__ == '__main__':
    print(json.dumps(observe(), indent=2))
