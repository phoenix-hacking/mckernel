"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
One exact read-only observation with enforced CPU0 and positive child ownership.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import resource
import subprocess
import time

HELPER = Path(__file__).resolve().parent.parent / 'observe_current60_postjoin.py'
HELPER_SHA256 = 'de9f6a1b76faded7a31227d13fe30cab33867ba769eb0a0b7234ea564946f048'
PYTHON = '/home/holden/anaconda3/bin/python3'


def write_once(path, value):
    with Path(path).open('x') as stream:
        json.dump(value, stream, indent=2)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())


def child_limits():
    os.sched_setaffinity(0, {0})
    resource.setrlimit(resource.RLIMIT_AS, (2 << 30, 2 << 30))
    resource.setrlimit(resource.RLIMIT_CPU, (60, 60))


def group_members(group):
    members, errors = [], []
    for path in Path('/proc').iterdir():
        if not path.name.isdecimal():
            continue
        try:
            fields = (path / 'stat').read_text().rsplit(')', 1)[1].split()
            if int(fields[2]) == group:
                members.append(int(path.name))
        except (FileNotFoundError, ProcessLookupError):
            pass
        except OSError as error:
            errors.append(str(error))
    return members, errors


def capture(argv, prefix, timeout):
    """Retain ownership on timeout; never signal, retry, or infer a positive join."""
    prefix = Path(prefix)
    write_once(str(prefix) + '.ONCE-CLAIM.json', dict(argv=argv, CPU=[0]))
    started = time.time()
    monotonic = time.monotonic()
    with Path(str(prefix) + '.stdout').open('xb') as stdout, Path(str(prefix) + '.stderr').open('xb') as stderr:
        child = subprocess.Popen(argv, stdout=stdout, stderr=stderr,
                                 start_new_session=True, preexec_fn=child_limits,
                                 close_fds=True)
        fields = (Path('/proc') / str(child.pid) / 'stat').read_text().rsplit(')', 1)[1].split()
        identity = dict(pid=child.pid, birth=fields[19], argv=argv,
                        actual_affinity=sorted(os.sched_getaffinity(child.pid)),
                        started_epoch=started)
        write_once(str(prefix) + '.STARTED.json', identity)
        assert identity['actual_affinity'] == [0], 'exact CPU0 before observation'
        while True:
            joined, status, usage = os.wait4(child.pid, os.WNOHANG)
            if joined:
                break
            if time.monotonic() - monotonic >= timeout:
                write_once(str(prefix) + '.TIMEOUT-OWNERSHIP-RETAINED.json', identity)
                raise TimeoutError('observation timeout; retain exact live child ownership')
            time.sleep(.01)
        child.returncode = os.waitstatus_to_exitcode(status)
    members, errors = group_members(child.pid)
    result = dict(identity, returncode=child.returncode,
                  positive_direct_wait4_join=True, streams_closed=True,
                  process_group_absent=not members and not errors,
                  remaining_group_members=members, group_observation_errors=errors,
                  wall_seconds=time.monotonic() - monotonic,
                  CPU_seconds=usage.ru_utime + usage.ru_stime,
                  maximum_RSS_KiB=usage.ru_maxrss)
    write_once(str(prefix) + '.RESULT.json', result)
    assert result['process_group_absent'], 'complete group absence after positive join'
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument('--command-json', required=True, type=Path)
    parser.add_argument('--command-sha256', required=True)
    args = parser.parse_args()
    raw = args.command_json.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == args.command_sha256
    command = json.loads(raw)  # This subject is explicitly declared JSON.
    assert os.getuid() == os.geteuid() == 1000
    assert hashlib.sha256(HELPER.read_bytes()).hexdigest() == HELPER_SHA256
    argv = command['argv']
    assert len(argv) == 10 and argv[:4] == [PYTHON, '-I', '-B', str(HELPER)]
    assert argv[4] == '--release' and argv[6] == '--release-sha256' and argv[8] == '--output'
    release_raw = Path(argv[5]).read_bytes()
    assert hashlib.sha256(release_raw).hexdigest() == argv[7]
    release = json.loads(release_raw)
    assert release['author'] == '/root' and release['maximum_invocations'] == 1
    assert release['output'] == argv[9] and not Path(argv[9]).exists()
    assert command['CPU'] == [0] and command['maximum_invocations'] == 1
    assert command['timeout_seconds'] == 120
    result = capture(argv, command['record_prefix'], command['timeout_seconds'])
    print(json.dumps(result))
    return result['returncode']


if __name__ == '__main__':
    raise SystemExit(main())
