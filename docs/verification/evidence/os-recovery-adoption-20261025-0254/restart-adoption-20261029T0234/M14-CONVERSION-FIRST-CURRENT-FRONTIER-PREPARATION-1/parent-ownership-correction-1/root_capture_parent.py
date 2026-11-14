"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
One direct readonly capture, owned wait4 and atomic no-overwrite join publication.
"""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

HERE = Path(__file__).resolve().parent


def reference(path):
    data = Path(path).read_bytes()
    return dict(path=str(path), bytes=len(data), sha256=hashlib.sha256(data).hexdigest())


def atomic_json(path, value):
    """Publish complete bytes once; an existing destination is never replaced."""
    temporary = path.with_name(path.name + '.tmp')
    with temporary.open('xb') as stream:
        stream.write((json.dumps(value, indent=2, allow_nan=False) + '\n').encode())
        stream.flush()
        os.fsync(stream.fileno())
    # link(2) is atomic and refuses an existing destination, including a symlink.
    # On failure preserve the temporary file for owner reconciliation.
    os.link(temporary, path, follow_symlinks=False)
    descriptor = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    try:
        os.fsync(descriptor)
        temporary.unlink()
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


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
    child_identity = None
    evidence_error = None
    with (output / 'stdout').open('xb') as stdout, (output / 'stderr').open('xb') as stderr:
        child = subprocess.Popen(argv, stdout=stdout, stderr=stderr, start_new_session=True)
        try:
            child_identity = identity(child.pid)
            atomic_json(output / 'STARTED.ACTUAL.json', dict(
                parent=parent, child=child_identity, argv=argv, release=release_ref,
                started_epoch=started_epoch))
        except BaseException as error:
            # No recorded identity is invented, and evidence failure never abandons the child.
            evidence_error = repr(error)
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
    birth = child_identity['birth'] if child_identity is not None else None
    result = dict(scope=__doc__.splitlines()[0], author='/root', parent=parent,
                  child=child_identity, pid=child.pid, birth=birth, starttime=birth, argv=argv,
                  parent_source=reference(Path(__file__).resolve()),
                  returncode=child.returncode, wait4_pid=waited, wait4_status=status,
                  positive_wait4_join=waited == child.pid, positive_direct_wait_join=waited == child.pid,
                  streams_closed=stdout.closed and stderr.closed, process_group_absent=not members and not errors,
                  remaining_group_members=members, group_observation_errors=errors, signals_sent=0,
                  started_epoch=started_epoch, finished_epoch=time.time(),
                  wall_seconds=time.monotonic() - started, user_cpu_seconds=usage.ru_utime,
                  system_cpu_seconds=usage.ru_stime, peak_rss_kib=usage.ru_maxrss,
                  release=release_ref, stdout=reference(output / 'stdout'), stderr=reference(output / 'stderr'),
                  evidence_error=evidence_error, current_free=False)
    destination = output / 'DIRECT-PARENT-JOIN.ACTUAL.json'
    atomic_json(destination, result)
    print(json.dumps(dict(join=reference(destination), returncode=child.returncode,
                          evidence_error=evidence_error)))
    raise SystemExit(child.returncode if evidence_error is None else 1)


if __name__ == '__main__':
    main()
