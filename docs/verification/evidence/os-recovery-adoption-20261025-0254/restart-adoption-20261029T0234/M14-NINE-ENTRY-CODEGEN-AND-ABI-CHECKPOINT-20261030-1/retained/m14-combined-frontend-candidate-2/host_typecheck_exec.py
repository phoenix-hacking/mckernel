#!/usr/bin/python3
"""HOST-only stage then same-PID exec; actual admission and outside owner required.

Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
No fork/Popen occurs in this Python source. The coordinator owns the process,
source exclusion, stdout/stderr, lease and post-exec descendant observations.
"""
import ctypes
import hashlib
import types
import json
import math
import os
import resource
import signal
import stat
import subprocess
import time
import host_gate_typecheck as host_gate
from pathlib import Path

HERE = Path(__file__).absolute().parent
PROFILE = HERE / 'PROFILE.SOURCE-ONLY.json'
PROFILE_SHA = '2598a333f90b1a53dcc429c1e7bd258267239ac07db414b8e36e481fd0acf4e3'
PRODUCER = Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261026-1/WEEKLY-ONLY-20261029-1/DISPATCHER-SOL-MAX-20261030-1/attempt-0002/m14-perf-host-light-runner-source-1/perf_two_phase_owner.py')
PRODUCER_SHA = '2c7745023574066a5bb63590ace7f6a53d1f4dc85059274598a2bbece9455b68'
MAX_INPUT = 8 << 20
MAX_TOTAL = 128 << 20
NOFOLLOW = os.O_NOFOLLOW | os.O_CLOEXEC


def require(ok, what):
    if not ok:
        raise RuntimeError(what)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def safe_open_abs(path, flags=os.O_RDONLY):
    """Reject symlinks in every path component and return an owned descriptor."""
    p = Path(path)
    require(p.is_absolute() and all(x not in ('', '.', '..') for x in p.parts[1:]), 'bad absolute path')
    fd = os.open('/', os.O_RDONLY | os.O_DIRECTORY | NOFOLLOW)
    try:
        for part in p.parts[1:-1]:
            nxt = os.open(part, os.O_RDONLY | os.O_DIRECTORY | NOFOLLOW, dir_fd=fd)
            os.close(fd); fd = nxt
        out = os.open(p.parts[-1], flags | NOFOLLOW | os.O_NONBLOCK, dir_fd=fd)
    finally:
        os.close(fd)
    return out


def stable(fd):
    s = os.fstat(fd)
    return (s.st_dev, s.st_ino, s.st_mode, s.st_size, s.st_mtime_ns, s.st_ctime_ns)


def read_fd(fd, size):
    require(0 <= size <= MAX_INPUT, 'source size bound')
    before = stable(fd)
    require(stat.S_ISREG(before[2]) and before[3] == size, 'source type/size')
    os.lseek(fd, 0, os.SEEK_SET)
    chunks, remaining = [], size
    while remaining:
        data = os.read(fd, min(remaining, 65536))
        require(bool(data), 'short read')
        chunks.append(data); remaining -= len(data)
    require(not os.read(fd, 1) and stable(fd) == before, 'source changed during read')
    return b''.join(chunks), before


def mkdir_chain(rootfd, parts):
    fd = os.dup(rootfd)
    try:
        for part in parts:
            require(part not in ('', '.', '..') and '/' not in part, 'bad component')
            try: os.mkdir(part, 0o700, dir_fd=fd)
            except FileExistsError: pass
            nxt = os.open(part, os.O_RDONLY | os.O_DIRECTORY | NOFOLLOW, dir_fd=fd)
            os.close(fd); fd = nxt
        return fd
    except BaseException:
        os.close(fd); raise


def create_file(dirfd, name, data):
    fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | NOFOLLOW, 0o600, dir_fd=dirfd)
    try:
        view = memoryview(data)
        while view:
            n = os.write(fd, view); require(n > 0, 'short write'); view = view[n:]
        os.fsync(fd)
    finally: os.close(fd)


def verify_row_fd(fd, row):
    data, ident = read_fd(fd, row['expected_bytes'])
    require(digest(data) == row['expected_sha256'], 'source hash mismatch: ' + row['relative_path'])
    return data, ident


def stage(profile, parentfd):
    """Exclusive work-1; hold each exact source fd and verify the staged bytes twice."""
    os.mkdir('work-1', 0o700, dir_fd=parentfd)
    work = os.open('work-1', os.O_RDONLY | os.O_DIRECTORY | NOFOLLOW, dir_fd=parentfd)
    held, seen, total = [], set(), 0
    try:
        for name in ('src', 'out', 'home', 'tmp'):
            os.mkdir(name, 0o700, dir_fd=work)
        src = os.open('src', os.O_RDONLY | os.O_DIRECTORY | NOFOLLOW, dir_fd=work)
        try:
            rows = profile['source_files']; require(len(rows) == 172, 'source row count')
            for row in rows:
                rel = row['relative_path']; parts = rel.split('/')
                require(not rel.startswith('/') and all(x not in ('', '.', '..') for x in parts), 'bad source name')
                require(rel not in seen, 'duplicate source name'); seen.add(rel)
                total += row['expected_bytes']; require(total <= MAX_TOTAL, 'source total bound')
                inp = safe_open_abs(row['input_path'])
                try:
                    data, ident = verify_row_fd(inp, row)
                    sub = mkdir_chain(src, parts[:-1])
                    try: create_file(sub, parts[-1], data)
                    finally: os.close(sub)
                    held.append((row, inp, ident)); inp = -1
                finally:
                    if inp >= 0: os.close(inp)
        finally: os.close(src)
        readback(profile, held)
        return work, held
    except BaseException:
        try: write_record(work, 'UNKNOWN.json', {'state':'UNKNOWN', 'phase':'staging', 'lease_release':False})
        except BaseException: pass
        for _, fd, _ in held: os.close(fd)
        os.close(work)
        raise


def readback(profile, held):
    """Reopen names without links; match both held and path identity and staged bytes."""
    root = Path(profile['work_root_proposal']) / 'src'
    evidence = []
    for row, fd, identity in held:
        _, now = verify_row_fd(fd, row); require(now == identity, 'held source identity changed')
        again = safe_open_abs(row['input_path'])
        try:
            _, same = verify_row_fd(again, row); require(same == identity, 'source path identity changed')
        finally: os.close(again)
        copied = safe_open_abs(root / row['relative_path'])
        try:
            _, staged = verify_row_fd(copied, row)
        finally: os.close(copied)
        evidence.append({'relative_path':row['relative_path'], 'input_stat':list(identity), 'staged_stat':list(staged), 'sha256':row['expected_sha256']})
    return evidence


def write_record(work, name, value):
    out = os.open('out', os.O_RDONLY | os.O_DIRECTORY | NOFOLLOW, dir_fd=work)
    try: create_file(out, name, (json.dumps(value, sort_keys=True, indent=2)+'\n').encode())
    finally: os.close(out)



def emit(event, **values):
    print(json.dumps({'event':event, **values},sort_keys=True),flush=True)


def main():
    grant, caps=host_gate.check()
    host_gate.consume(grant)
    identity=host_gate.birth(os.getpid())
    parentfd=safe_open_abs(HERE,os.O_RDONLY|os.O_DIRECTORY)
    work=None;held=[]
    try:
        intent={'nonce':grant['nonce'],'profile':PROFILE_SHA,'owner':identity,'state':'STAGING_INTENT'}
        create_file(parentfd,'DIRECT-STAGING-INTENT.json',(json.dumps(intent,sort_keys=True)+'\n').encode())
        os.fsync(parentfd);emit('STAGING_INTENT',**intent)
        raw=PROFILE.read_bytes();require(digest(raw)==PROFILE_SHA,'profile changed')
        profile=json.loads(raw);require(len(profile['executable_argv'])==208,'argv count')
        work,held=stage(profile,parentfd)
        readback_data=readback(profile,held)
        write_record(work,'staged-readback.json',readback_data)
        require(host_gate.birth(os.getpid())['start']==identity['start'],'owner birth changed')
        host_gate.check() # all three caps have >=195s remaining before exec
        argv=['/usr/bin/taskset','-c','6','/usr/bin/prlimit','--as=4294967296','--cpu=150','--nofile=256','--fsize=67108864','--core=0','--','/usr/bin/timeout','--signal=TERM','--kill-after=5s','180s','/usr/bin/time','-v','-o',str(HERE/'work-1/out/time.txt')]+profile['executable_argv']
        dispatch={'state':'EXEC_INTENT','owner':identity,'argv':argv,'cwd':profile['cwd'],'env':profile['environment_env_i'],'lease_release':False,'source_fd_lifetime':'retained through second readback; CLOEXEC after exec; coordinator exclusion continues'}
        write_record(work,'exec-intent.json',dispatch)
        emit('EXEC_INTENT',owner=identity,output=str(HERE/'work-1/out'),lease_release=False)
        os.chdir(profile['cwd'])
        os.execve(argv[0],argv,profile['environment_env_i'])
    except BaseException as exc:
        if work is not None:
            try: write_record(work,'UNKNOWN.json',{'state':'UNKNOWN','phase':'before_or_during_exec','exception':type(exc).__name__,'owner':identity,'lease_release':False})
            except BaseException: pass
        emit('UNKNOWN',owner=identity,error=type(exc).__name__,lease_release=False)
        raise
    finally:
        for _,fd,_ in held: os.close(fd)
        if work is not None:os.close(work)
        os.close(parentfd)


if __name__=='__main__':main()
