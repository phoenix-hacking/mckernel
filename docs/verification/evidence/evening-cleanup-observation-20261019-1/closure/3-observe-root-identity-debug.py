#!/usr/bin/python3
"""Dedicated finite ROOT_OBSERVE producer, no effect-mode option.
Reuses reviewed regular capture/limited child/direct-wait pattern; adds owned
session retirement proof required for complete root proc/Docker census timeout.
No deletion/trim/container mutation/build/guest authority.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import resource
import signal
import stat
import subprocess
import sys
import time
import types

BASE = Path('/home/holden/mckernel-work/host-preparation/duplicate-archive-cleanup-execution-preparation-20261018-1')
SOURCE = BASE / 'exact120.py'
CAP = 33554432


def fixed_small(path):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or before.st_size > 4 << 20:
            raise RuntimeError('source/release shape')
        raw = os.read(fd, (4 << 20) + 1)
        after = os.fstat(fd)
        fields = ('st_dev', 'st_ino', 'st_size', 'st_mtime_ns', 'st_ctime_ns')
        if len(raw) != before.st_size or any(getattr(before, k) != getattr(after, k) for k in fields):
            raise RuntimeError('source/release raced')
        if any(getattr(before, k) != getattr(os.lstat(path), k) for k in fields):
            raise RuntimeError('source/release name raced')
        return raw
    finally:
        os.close(fd)


def group_census(pgid, starttime):
    # Any transient/inaccessible process leaves retirement uncertain, never PASS.
    before = sorted(p.name for p in Path('/proc').iterdir() if p.name.isdigit())
    members = []
    for name in before:
        raw = Path('/proc', name, 'stat').read_bytes()
        fields = raw.rpartition(b') ')[2].split()
        if len(fields) < 20:
            raise RuntimeError('retirement proc stat shape')
        if int(fields[2]) == pgid:
            if int(fields[3]) != pgid or int(fields[19]) < starttime or (int(name) == pgid and int(fields[19]) != starttime):
                raise RuntimeError('owned group/session identity drift')
            members.append([int(name), int(fields[19]), fields[0].decode()])
        again = Path('/proc', name, 'stat').read_bytes().rpartition(b') ')[2].split()
        if len(again) < 20 or again[19] != fields[19]:
            raise RuntimeError('retirement PID identity raced')
    after = sorted(p.name for p in Path('/proc').iterdir() if p.name.isdigit())
    if before != after:
        raise RuntimeError('retirement process set raced')
    return members


def bounds():
    os.sched_setaffinity(0, {6})
    os.nice(19)
    resource.setrlimit(resource.RLIMIT_AS, (4294967296, 4294967296))
    resource.setrlimit(resource.RLIMIT_CPU, (60, 60))
    resource.setrlimit(resource.RLIMIT_FSIZE, (CAP, CAP))
    resource.setrlimit(resource.RLIMIT_NOFILE, (4096, 4096))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))


def main():
    p = argparse.ArgumentParser(allow_abbrev=False)
    p.add_argument('--release', required=True)
    p.add_argument('--release-sha256', required=True)
    a = p.parse_args()
    if os.getuid() != 0 or os.geteuid() != 0:
        raise RuntimeError('root required')
    release_raw = fixed_small(a.release)
    if hashlib.sha256(release_raw).hexdigest() != a.release_sha256:
        raise RuntimeError('release pin')
    release = json.loads(release_raw)
    source_raw = fixed_small(SOURCE)
    source_sha = hashlib.sha256(source_raw).hexdigest()
    own_sha = hashlib.sha256(fixed_small(Path(__file__).resolve())).hexdigest()
    if (release['status'] != 'OBSERVATION_RELEASE' or release['source_sha256'] != source_sha or
            release['observation_wrapper_sha256'] != own_sha):
        raise RuntimeError('observation source/release gate')
    # Execute already pinned source definitions in memory, without import writes.
    contract = types.ModuleType('exact120_observation_contract')
    contract.__file__ = str(SOURCE)
    exec(compile(source_raw, str(SOURCE), 'exec'), contract.__dict__)
    directory, ancestry = contract.safe_directory(BASE)
    opened = []
    report = {'status': 'STARTING', 'argv': ['/usr/bin/python3', '-I', str(SOURCE), '--mode', 'observe', '--release', a.release],
              'source_sha256': source_sha, 'wrapper_sha256': own_sha, 'release_sha256': a.release_sha256,
              'boot_id': Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
              'limits': {'affinity': '6', 'jobs': 1, 'as_bytes': 4294967296, 'cpu_seconds': 60, 'wall_seconds': 90,
                         'term_grace_seconds': 5, 'kill_wait_seconds': 5, 'fsize_bytes_each': CAP, 'nofile': 4096},
              'direct_joined': False, 'whole_group_retired': False, 'interpreter': sys.executable, 'version': sys.version}
    child = None
    began = time.monotonic()
    try:
        for name in ('actual-observation-5.stdout', 'actual-observation-5.stderr', 'actual-observation-5.supervisor.jsonl'):
            fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=directory)
            opened.append(fd)
        os.fsync(directory)
        out, err, journal = opened
        def emit(event):
            raw = (json.dumps(event, sort_keys=True) + '\n').encode()
            while raw:
                n = os.write(journal, raw)
                if n <= 0:
                    raise RuntimeError('journal short write')
                raw = raw[n:]
            os.fsync(journal)
        report['capture_initial_metadata'] = [contract.meta(os.fstat(fd)) for fd in (out, err)]
        emit(report)
        try:
            child = subprocess.Popen(report['argv'], stdin=subprocess.DEVNULL, stdout=out, stderr=err,
                                     close_fds=True, start_new_session=True, preexec_fn=bounds,
                                     env=contract.ENV)
            report['pid'] = child.pid
            fields = Path('/proc', str(child.pid), 'stat').read_bytes().rpartition(b') ')[2].split()
            if len(fields) < 20 or int(fields[2]) != child.pid or int(fields[3]) != child.pid:
                raise RuntimeError('new child process-group/session identity')
            report['starttime'] = int(fields[19]); report['pgid'] = child.pid
            emit(dict(report, status='LAUNCHED'))
            try:
                report['returncode'] = child.wait(timeout=90)
            except subprocess.TimeoutExpired:
                report['timed_out'] = True
                os.killpg(child.pid, signal.SIGTERM)
                try:
                    report['returncode'] = child.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    os.killpg(child.pid, signal.SIGKILL)
                    report['returncode'] = child.wait(timeout=5)
            report['direct_joined'] = True
            members = group_census(child.pid, report['starttime'])
            if members and report.get('timed_out'):
                # Direct parent may obey TERM while an owned CLI remains. Kill
                # only the still-identity-bound original session group.
                os.killpg(child.pid, signal.SIGKILL)
                deadline = time.monotonic() + 5
                while members and time.monotonic() < deadline:
                    time.sleep(0.05)
                    members = group_census(child.pid, report['starttime'])
            report['remaining_group'] = members
            report['whole_group_retired'] = not members
            if members:
                raise RuntimeError('owned group remains; retirement uncertain, retain identities')
            checkfd = os.open(contract.LOCK, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
            try:
                import fcntl
                if (os.fstat(checkfd).st_dev, os.fstat(checkfd).st_ino) != contract.LOCK_ID:
                    raise RuntimeError('persistent mutex identity drift')
                fcntl.flock(checkfd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                report['mutex_identity_preserved_and_available'] = True
            finally:
                os.close(checkfd)
            report['status'] = 'OBSERVATION_JOINED' if report['returncode'] == 0 and not report.get('timed_out') else 'OBSERVATION_FAILED_RETIRED'
        except BaseException as exc:
            report['error'] = repr(exc)
            report['status'] = 'STOP_UNCERTAIN'
            # Never leave the direct child unjoined merely because admission or
            # evidence code failed. Only this new owned read-only group is signaled.
            if child is not None and child.poll() is None:
                try:
                    os.killpg(child.pid, signal.SIGTERM)
                    try:
                        child.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        os.killpg(child.pid, signal.SIGKILL)
                        child.wait(timeout=5)
                    report['direct_joined'] = True
                except BaseException as retire_error:
                    report['retirement_error'] = repr(retire_error)
            # Uncertainty remains even if error cleanup joined; no fabricated PASS.
        for fd in (out, err):
            os.fsync(fd)
        report['elapsed_seconds'] = time.monotonic() - began
        report['capture_metadata'] = [contract.meta(os.fstat(fd)) for fd in (out, err)]
        report['capture_sha256'] = []
        for index, name in enumerate(('actual-observation-5.stdout', 'actual-observation-5.stderr')):
            readfd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
            try:
                if contract.meta(os.fstat(readfd)) != report['capture_metadata'][index] or os.fstat(readfd).st_size > CAP:
                    raise RuntimeError('capture identity/size drift')
                sha = hashlib.sha256()
                while True:
                    block = os.read(readfd, 1 << 20)
                    if not block:
                        break
                    sha.update(block)
                if contract.meta(os.fstat(readfd)) != report['capture_metadata'][index]:
                    raise RuntimeError('capture read drift')
                report['capture_sha256'].append(sha.hexdigest())
            finally:
                os.close(readfd)
        emit(report)
        print(json.dumps({'status': report['status'], 'direct_joined': report['direct_joined'], 'whole_group_retired': report['whole_group_retired']}))
        if report['status'] != 'OBSERVATION_JOINED':
            raise SystemExit(1)
    finally:
        for fd in opened:
            os.close(fd)
        os.close(directory)


if __name__ == '__main__':
    main()
