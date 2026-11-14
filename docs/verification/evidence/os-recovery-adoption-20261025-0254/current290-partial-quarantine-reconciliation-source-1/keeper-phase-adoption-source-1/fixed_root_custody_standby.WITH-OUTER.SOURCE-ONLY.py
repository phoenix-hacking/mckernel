"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

UNRELEASED source proposal. Exact root PID1060806/start80309560 FD3 duplication
only. No executable main, retirement, signal, unlock, cleanup or fallback.
A separately reviewed keeper/command release is REQUIRED before any invocation.
"""
import ctypes
import hashlib
import os
from pathlib import Path
import select
import types

HERE = Path(__file__).resolve().parent
ADOPTION = HERE.parent / 'partial_quarantine_adoption.py'
ADOPTION_SHA = '57722eab94b8494c2423cf9a161ff43ed2948018fa0ddc8ad59f91cd9d9968aa'
GRANT_SHA = 'a9f54316ae1c5be8338531a692d7fad76f52402dd61727b46fc70f2ea55cf1c2'
PID = 1060806
START = '80309560'
PARENT = 1060803
PARENT_START = '80309553'
PGID = 1060803
OUTER = 1060802
OUTER_START = '80309549'
IDENTITIES = Path('/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/ROOT-CURRENT-QUARANTINE-OUTER-PARENT-ACTOR-IDENTITIES.json')
IDENTITIES_SHA = '1a8409c60d8881566233a1d3b6948faa30f5091009f67810598acd6cd3b070d2'
TARGET_FD = 3
PIDFD_OPEN = 434
PIDFD_GETFD = 438


def adoption():
    raw = ADOPTION.read_bytes()
    if hashlib.sha256(raw).hexdigest() != ADOPTION_SHA:
        raise RuntimeError('unreleased adoption source differs')
    module = types.ModuleType('_partial_quarantine_source')
    module.__file__ = str(ADOPTION)
    exec(compile(raw, str(ADOPTION), 'exec'), module.__dict__)
    return module


def process(p, pid, start, parent=None, pgid=None, expected_uid=0, expected_gid=0):
    raw = Path('/proc/{}/stat'.format(pid)).read_bytes()
    left, sep, right = raw.rpartition(b') ')
    fields = right.split()
    p.need(sep and left.startswith(str(pid).encode() + b' (') and len(fields) >= 50
           and fields[0] not in (b'Z', b'X', b'x', b'T', b't') and fields[19].decode() == start,
           'fixed-root-actor-birth-state')
    if parent is not None:
        p.need(int(fields[1]) == parent, 'fixed-root-parent')
    if pgid is not None:
        p.need(int(fields[2]) == pgid, 'fixed-root-pgid')
    status = Path('/proc/{}/status'.format(pid)).read_text()
    credentials = {line.split(':', 1)[0]: line.split()[1:] for line in status.splitlines()
                   if line.startswith(('Uid:', 'Gid:'))}
    p.need(credentials == {'Uid': [str(expected_uid)] * 4, 'Gid': [str(expected_gid)] * 4}, 'fixed-root-actor-credentials')
    command = Path('/proc/{}/cmdline'.format(pid)).read_bytes()
    p.need(command.endswith(b'\0'), 'fixed-root-actor-command-terminator')
    return dict(pid=pid, starttime=start, parent=int(fields[1]), pgid=int(fields[2]),
                command=command, credentials=credentials)


def actor_binding(p):
    p.need(os.geteuid() == 0 and os.uname().machine == 'x86_64', 'fixed-root-platform-credentials')
    p.need(Path('/proc/sys/kernel/random/boot_id').read_text().strip() == p.BOOT, 'fixed-root-boot')
    grant_raw = p.pinned_bytes(p.PREPARATION / 'ROOT-ACTUAL-NORMAL-RETIREMENT-GRANT.json', GRANT_SHA)
    grant = p.strict(grant_raw)
    argv = grant['argv']
    interpreter = argv.index('/home/holden/anaconda3/bin/python3')
    expected_command = b'\0'.join(word.encode() for word in argv[interpreter:]) + b'\0'
    observed = process(p, PID, START, PARENT, PGID)
    p.need(observed['command'] == expected_command, 'fixed-root-exact-granted-command')
    parent = process(p, PARENT, PARENT_START, parent=OUTER, pgid=PGID)
    outer = process(p, OUTER, OUTER_START, pgid=OUTER, expected_uid=1000, expected_gid=1000)
    retained = p.strict(p.pinned_bytes(IDENTITIES, IDENTITIES_SHA, 9945))
    retained_rows = {row['pid']: row for row in retained['processes']}
    for actor in (observed, parent, outer):
        p.need(hashlib.sha256(actor['command']).hexdigest() == retained_rows[actor['pid']]['cmdline_sha256'],
               'fixed-root-sudo-outer-exact-argv')
    p.pinned_bytes(p.SOURCE, p.SOURCE_SHA, 128910)
    p.pinned_bytes(p.PREPARATION / 'RELEASE.PASS_EXECUTION_RELEASE.json', p.RELEASE_SHA, 241402)
    return observed, parent, outer


def live_pidfd(p, pidfd):
    report = Path('/proc/self/fdinfo/{}'.format(pidfd)).read_text()
    rows = [line.split()[1:] for line in report.splitlines() if line.startswith('Pid:')]
    p.need(rows == [[str(PID)]], 'fixed-root-pidfd-exact-target')
    poller = select.poll()
    poller.register(pidfd, select.POLLIN | select.POLLHUP | select.POLLERR)
    p.need(poller.poll(0) == [], 'fixed-root-pidfd-target-already-exited')


class Standby:
    """Owns the duplicate and pidfd; no close/unlock/retire/serialize interface.

    Future reviewed keeper MUST preserve this object and both FDs on transport,
    observer or evidence errors. It must not exit after printing a descriptor
    number. Successful evidence is not a replacement for the genuinely held FD.
    """
    def __init__(self, fd, pidfd):
        self.fd = fd
        self.pidfd = pidfd
        self.verified = False
        self.error = None
        self.proof = None


def acquire_exact_standby():
    """Unreleased helper definition: no caller or execution wrapper is supplied.

    Caller must already have its independently released keeper/capture protocol.
    Any error after successful getfd RETURNS RETAINED UNVERIFIED HOLD; neither
    descriptor is closed. No old actor may be retired on that result.
    """
    p = adoption()
    before = actor_binding(p)
    root_meta = os.stat(p.ROOT_MUTEX, follow_symlinks=False)
    fields = ('st_dev', 'st_ino', 'st_mode', 'st_uid', 'st_gid', 'st_nlink', 'st_size', 'st_mtime_ns', 'st_ctime_ns')
    metadata = {field: getattr(root_meta, field) for field in fields}
    p.need((root_meta.st_dev, root_meta.st_ino, root_meta.st_uid, root_meta.st_gid,
            root_meta.st_nlink, root_meta.st_size, root_meta.st_mode) == (27, 4, 0, 0, 1, 0, 0o100644),
           'fixed-root-permanent-node')
    libc = ctypes.CDLL(None, use_errno=True)
    libc.syscall.restype = ctypes.c_long
    pidfd = libc.syscall(ctypes.c_long(PIDFD_OPEN), ctypes.c_int(PID), ctypes.c_uint(0))
    if pidfd < 0:
        raise OSError(ctypes.get_errno(), 'fixed-root-pidfd-open-no-fallback')
    try:
        live_pidfd(p, pidfd)
        p.need(actor_binding(p) == before, 'fixed-root-before-getfd-race')
        fd = libc.syscall(ctypes.c_long(PIDFD_GETFD), ctypes.c_int(pidfd), ctypes.c_int(TARGET_FD), ctypes.c_uint(0))
        if fd < 0:
            raise OSError(ctypes.get_errno(), 'fixed-root-pidfd-getfd-no-fallback')
    except BaseException:
        # No duplicate was obtained, no retirement exists, original actor intact.
        os.close(pidfd)
        raise
    hold = Standby(fd, pidfd)
    try:
        live_pidfd(p, pidfd)
        p.need(actor_binding(p) == before, 'fixed-root-after-getfd-race')
        custody = p.verify_description_custody(fd, PID, TARGET_FD, p.ROOT_MUTEX, metadata)
        p.need((custody['device'], custody['inode']) == (27, 4), 'fixed-root-custody-inode')
        live_pidfd(p, pidfd)
        p.need(actor_binding(p) == before, 'fixed-root-final-actor-race')
        hold.proof = dict(scope=p.SCOPE, operation='EXACT_DUPLICATE_ONLY_STANDBY_NO_RETIREMENT',
                          old_actor=p.ROOT_ACTOR, custody=custody,
                          positive_pidfd_target_alive=True, actor_birth_rechecked=True,
                          actual_retirement=False, quarantine_untouched=True,
                          runtime_execution_release=False, requires_live_keeper=True)
        hold.verified = True
    except BaseException as error:
        # Deliberately do not close either descriptor after successful getfd.
        hold.error = type(error).__name__ + ': ' + str(error)
    return hold


if __name__ == '__main__':
    raise SystemExit('SOURCE ONLY: no keeper or independent exact execution release; not runnable')
