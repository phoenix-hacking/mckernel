#!/usr/bin/env python3
"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
SDK13 compile/link driver proposal; requires independently admitted container owner.
"""
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import time

PROFILE = Path('/work/sdk13-profile.json')
PROFILE_SHA256 = '3e6d2491c509790cea3f2de035e2171858d5efbcb9cc0dca8cc3aaea15007926'
EVIDENCE = Path('/work/sdk13-driver-evidence')
CWD = '/work/output/build/kernel'
STAGES = ('Rust object plus depinfo', 'GCC14 generic C object plus depfile',
          'GCC14 architecture C object plus depfile', 'GNU ld 2.41 raw eleven-input image')
PER_STAGE_TIMEOUT = 600


def read_profile():
    fd = os.open(PROFILE, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1 or before.st_size > 1024 * 1024:
            raise ValueError('profile must be bounded regular single-link file')
        data = b''
        while len(data) <= 1024 * 1024:
            chunk = os.read(fd, 65536)
            if not chunk:
                break
            data += chunk
        after = os.fstat(fd)
        if len(data) != before.st_size or (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns, before.st_ctime_ns) != (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns):
            raise ValueError('profile changed during read')
        if hashlib.sha256(data).hexdigest() != PROFILE_SHA256:
            raise ValueError('profile hash mismatch')
        value = json.loads(data)
        commands = value['commands']
        if len(commands) != 4 or tuple(x['stage'] for x in commands) != STAGES:
            raise ValueError('wrong command stages')
        if any(x['cwd'] != CWD or not isinstance(x['argv'], list) or not x['argv'] or
               not all(isinstance(a, str) and '\0' not in a for a in x['argv']) for x in commands):
            raise ValueError('wrong command schema')
        return commands
    finally:
        os.close(fd)


def write_new(path, value):
    raw = (json.dumps(value, sort_keys=True, allow_nan=False) + '\n').encode()
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC, 0o600)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())


def main():
    commands = read_profile()
    EVIDENCE.mkdir(mode=0o700)
    write_new(EVIDENCE / 'intent.json', {'profile_sha256': PROFILE_SHA256, 'stages': STAGES,
                                        'per_stage_timeout': PER_STAGE_TIMEOUT})
    for i, command in enumerate(commands, 1):
        stamp = time.time()
        write_new(EVIDENCE / ('stage-%d-intent.json' % i), {'argv': command['argv'], 'cwd': CWD,
                                                            'start_utc': stamp})
        child = None
        status = {'stage': command['stage'], 'returncode': None, 'timed_out': False,
                  'direct_wait_completed': False, 'descendant_closure': 'UNKNOWN'}
        try:
            with (EVIDENCE / ('stage-%d.stdout' % i)).open('xb') as out, \
                 (EVIDENCE / ('stage-%d.stderr' % i)).open('xb') as err:
                child = subprocess.Popen(command['argv'], cwd=CWD, stdin=subprocess.DEVNULL,
                                         stdout=out, stderr=err, start_new_session=True)
                status['child_pid'] = child.pid
                try:
                    status['returncode'] = child.wait(timeout=PER_STAGE_TIMEOUT)
                    status['direct_wait_completed'] = True
                except subprocess.TimeoutExpired:
                    status['timed_out'] = True
                    # Popen owns this unreaped direct child. Killing it does not prove
                    # any descendants or container have retired; owner must retain UNKNOWN.
                    child.terminate()
                    try:
                        status['returncode'] = child.wait(timeout=5)
                        status['direct_wait_completed'] = True
                    except subprocess.TimeoutExpired:
                        child.kill()
                        status['returncode'] = child.wait(timeout=5)
                        status['direct_wait_completed'] = True
                out.flush(); os.fsync(out.fileno()); err.flush(); os.fsync(err.fileno())
        except BaseException as exc:
            status['error'] = type(exc).__name__ + ': ' + str(exc)
        status['finish_utc'] = time.time()
        write_new(EVIDENCE / ('stage-%d-result.json' % i), status)
        if status.get('error') or status['timed_out'] or not status['direct_wait_completed'] or status['returncode'] != 0:
            write_new(EVIDENCE / 'result.json', {'status': 'FAIL_OR_UNKNOWN', 'last_stage': i,
                                                  'container_retirement': 'OWNER_REQUIRED'})
            return 1
    write_new(EVIDENCE / 'result.json', {'status': 'COMMANDS_EXITED_ZERO',
                                          'artifact_validation': 'NOT_PERFORMED',
                                          'container_retirement': 'OWNER_REQUIRED'})
    return 0


if __name__ == '__main__':
    sys.exit(main())
