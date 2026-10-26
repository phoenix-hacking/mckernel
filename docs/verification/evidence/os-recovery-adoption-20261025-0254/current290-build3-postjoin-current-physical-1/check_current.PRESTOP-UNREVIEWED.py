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
    result['retired_births'] = []
    for pid, expected in [(1224701, 84038706), (1224936, 84046403)]:
        path = Path('/proc') / str(pid) / 'stat'
        try:
            raw = path.read_text()
        except FileNotFoundError:
            result['retired_births'].append({'pid': pid, 'starttime': expected, 'state': 'absent'})
            continue
        birth = int(raw[raw.rfind(')') + 2:].split()[19])
        require(birth != expected, 'recorded build actor still alive')
        result['retired_births'].append({'pid': pid, 'starttime': expected,
                                        'state': 'reused_pid', 'current_starttime': birth})
    require(not lock_rows(), 'permanent mutex remains held')
    result['exclusive_probes'] = []
    for _ in range(2):
        metadata = MUTEX.lstat()
        require(stat.S_ISREG(metadata.st_mode) and (metadata.st_dev, metadata.st_ino) == (27, 4),
                'permanent mutex path changed')
        descriptor = os.open(MUTEX, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
        try:
            actual = os.fstat(descriptor)
            require((actual.st_dev, actual.st_ino) == (27, 4), 'probe identity changed')
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
            rows = lock_rows()
            require(len(rows) == 1 and str(os.getpid()) in rows[0].split(), 'probe kernel row mismatch')
            result['exclusive_probes'].append(rows[0])
        finally:
            os.close(descriptor)
        require(not lock_rows(), 'probe did not retire')
    command = ['/usr/bin/sudo', '-A', '/usr/bin/docker', '--host=unix:///var/run/docker.sock',
               'inspect', '--format', '{{json .State}}', CID]
    completed = subprocess.run(command, capture_output=True, text=True, timeout=30)
    result['docker_observation'] = {'argv': command, 'returncode': completed.returncode,
                                    'stdout': completed.stdout, 'stderr': completed.stderr}
    require(completed.returncode == 0, 'retained container inspection failed')
    state = json.loads(completed.stdout)
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
    result['meminfo'] = Path('/proc/meminfo').read_text()
    result['status'] = 'PASS_BUILD3_POSTJOIN_CURRENT_PHYSICAL_OBSERVATION'
    result['native_execution_authority'] = False
    return result


if __name__ == '__main__':
    print(json.dumps(observe(), indent=2))
