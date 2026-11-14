"""Functional McKernel OS/apps only; no security testing. One direct capture join."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

HERE = Path(__file__).resolve().parent


def reference(path):
    data = path.read_bytes()
    return dict(path=str(path), bytes=len(data), sha256=hashlib.sha256(data).hexdigest())


def identity(pid):
    fields = Path('/proc', str(pid), 'stat').read_text().rsplit(')', 1)[1].split()
    return dict(pid=pid, birth=int(fields[19]), ppid=int(fields[1]),
                pgrp=int(fields[2]), sid=int(fields[3]))


def main():
    release = HERE / 'RELEASE.ACTUAL.json'
    release_ref = reference(release)
    argv = ['/usr/bin/taskset', '-c', '0', '/usr/bin/prlimit',
            '--as=2147483648:2147483648', '--cpu=60:60', '--core=0:0', '--',
            '/home/holden/anaconda3/bin/python3', '-I', '-B',
            str(HERE / 'observe_conversion_frontier.py'),
            '--bindings', str(HERE / 'ROOT-ACTUAL-FRONTIER-OBSERVER-BINDING.json'),
            '--release', str(release), '--release-sha256', release_ref['sha256'],
            '--output', str(HERE / 'actual-frontier-1/OBSERVATION.json')]
    output = HERE / 'actual-frontier-parent-1'
    output.mkdir(mode=0o700)
    parent = identity(os.getpid())
    started_epoch, started = time.time(), time.monotonic()
    with (output / 'stdout').open('xb') as stdout, (output / 'stderr').open('xb') as stderr:
        child = subprocess.Popen(argv, stdout=stdout, stderr=stderr, start_new_session=True)
        child_identity = identity(child.pid)
        (output / 'STARTED.ACTUAL.json').write_text(json.dumps(dict(
            parent=parent, child=child_identity, argv=argv, release=release_ref,
            started_epoch=started_epoch), indent=2) + '\n')
        waited, status, usage = os.wait4(child.pid, 0)
        child.returncode = os.waitstatus_to_exitcode(status)
    members, errors = [], []
    for entry in Path('/proc').iterdir():
        if not entry.name.isdigit():
            continue
        try:
            record = identity(int(entry.name))
            if record['pgrp'] == child.pid:
                members.append(record)
        except FileNotFoundError:
            pass
        except (OSError, ValueError) as error:
            errors.append(dict(path=str(entry), error=repr(error)))
    result = dict(scope='Functional McKernel OS/apps and Rust/assembly migration only; no security testing.',
                  author='/root', parent=parent, child=child_identity, pid=child.pid,
                  birth=child_identity['birth'], starttime=child_identity['birth'], argv=argv,
                  returncode=child.returncode, wait4_pid=waited, wait4_status=status,
                  positive_wait4_join=waited == child.pid, positive_direct_wait_join=waited == child.pid,
                  streams_closed=stdout.closed and stderr.closed, process_group_absent=not members and not errors,
                  remaining_group_members=members, group_observation_errors=errors, signals_sent=0,
                  started_epoch=started_epoch, finished_epoch=time.time(),
                  wall_seconds=time.monotonic() - started, user_cpu_seconds=usage.ru_utime,
                  system_cpu_seconds=usage.ru_stime, peak_rss_kib=usage.ru_maxrss,
                  release=release_ref, stdout=reference(output / 'stdout'), stderr=reference(output / 'stderr'),
                  current_free=False)
    destination = output / 'DIRECT-PARENT-JOIN.ACTUAL.json'
    destination.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(dict(join=reference(destination), returncode=child.returncode)))
    raise SystemExit(child.returncode)


if __name__ == '__main__':
    main()
