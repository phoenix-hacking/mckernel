"""Functional OS custody fixture only; no security testing.

Uses one owned child and a newly created private flock file. Never references or
opens the production mutex/actor. A denied pidfd_getfd is retained as BLOCKED,
with no fallback and no root probe. Child exits normally via the private pipe.
"""
import ctypes
import errno
import fcntl
import json
import os
from pathlib import Path
import select
import signal
import tempfile
import time

HERE = Path(__file__).resolve().parent
SCOPE = 'Functional McKernel OS/apps and Rust/assembly migration only; no security testing.'
PR_SET_PTRACER = 0x59616D61
PR_SET_PTRACER_ANY = ctypes.c_ulong(-1).value
SYS_PIDFD_GETFD_X86_64 = 438


def main():
    result = dict(scope=SCOPE, operation='owned-private-file-crossprocess-pidfd_getfd-fixture',
                  root_probe=False, production_paths_touched=False, fallback=False,
                  fixture_normal_exit=False, runtime_authority=False)
    if os.uname().machine != 'x86_64':
        return dict(result, status='BLOCKED_UNSUPPORTED_FIXTURE_ARCH')
    with tempfile.TemporaryDirectory(prefix='crossprocess-custody-fixture-', dir=HERE) as tmp:
        path = Path(tmp) / 'fixture-only.lock'
        path.touch(mode=0o600)
        ready_r, ready_w = os.pipe()
        control_r, control_w = os.pipe()
        pid = os.fork()
        if pid == 0:
            os.close(ready_r)
            os.close(control_w)
            libc = ctypes.CDLL(None, use_errno=True)
            libc.prctl.argtypes = [ctypes.c_int, ctypes.c_ulong, ctypes.c_ulong, ctypes.c_ulong, ctypes.c_ulong]
            libc.prctl.restype = ctypes.c_int
            rc = libc.prctl(PR_SET_PTRACER, PR_SET_PTRACER_ANY, 0, 0, 0)
            error = ctypes.get_errno() if rc else 0
            fd = os.open(path, os.O_RDONLY | os.O_CLOEXEC)
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            os.write(ready_w, (json.dumps(dict(pid=os.getpid(), fd=fd, prctl_return=rc, prctl_errno=error)) + '\n').encode())
            os.close(ready_w)
            # EOF or one-byte request causes only normal owned-child exit.
            select.select([control_r], [], [], 15)
            os.read(control_r, 1)
            os.close(fd)
            os.close(control_r)
            os._exit(0)
        os.close(ready_w)
        os.close(control_r)
        pidfd = duplicate = independent = None
        child_joined = False
        try:
            if not select.select([ready_r], [], [], 5)[0]:
                raise RuntimeError('fixture child readiness deadline')
            ready = json.loads(os.read(ready_r, 4096))
            result['child_ready'] = ready
            if ready['pid'] != pid or ready['prctl_return'] != 0:
                return dict(result, status='BLOCKED_FIXTURE_PTRACER_SETUP')
            pidfd = os.pidfd_open(pid, 0)
            result['pidfd_open_succeeded'] = True
            libc = ctypes.CDLL(None, use_errno=True)
            libc.syscall.restype = ctypes.c_long
            ctypes.set_errno(0)
            returned = libc.syscall(ctypes.c_long(SYS_PIDFD_GETFD_X86_64), ctypes.c_int(pidfd), ctypes.c_int(ready['fd']), ctypes.c_uint(0))
            error = ctypes.get_errno()
            result['pidfd_getfd'] = dict(syscall=438, flags=0, return_value=returned,
                                         errno=error if returned < 0 else 0,
                                         errno_name=errno.errorcode.get(error) if returned < 0 else None)
            if returned < 0:
                result['status'] = 'BLOCKED_PIDFD_GETFD_DENIED' if error in (errno.EPERM, errno.EACCES) else 'BLOCKED_PIDFD_GETFD_ERROR'
                return result
            duplicate = returned
            result['duplicate_cloexec'] = not os.get_inheritable(duplicate)
            before = os.fstat(duplicate)
            result['private_inode'] = [before.st_dev, before.st_ino]
            wanted = ['FLOCK', 'ADVISORY', 'WRITE', str(pid),
                      '{:02x}:{:02x}:{}'.format(os.major(before.st_dev), os.minor(before.st_dev), before.st_ino), '0', 'EOF']
            def rows(actor, fd):
                return [line.split()[2:] for line in Path('/proc/{}/fdinfo/{}'.format(actor, fd)).read_text().splitlines() if line.startswith('lock:')]
            if rows(os.getpid(), duplicate) != [wanted] or rows(pid, ready['fd']) != [wanted]:
                raise RuntimeError('fixture same-description lock proof differs')
            result['genuine_custody_before_child_exit'] = True
            independent = os.open(path, os.O_RDONLY | os.O_CLOEXEC)
            try:
                fcntl.flock(independent, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                result['independent_acquire_before_exit_blocked'] = True
            else:
                raise RuntimeError('fixture lock unexpectedly free before child exit')
            os.write(control_w, b'x')
            os.close(control_w)
            control_w = None
            poll = select.poll()
            poll.register(pidfd, select.POLLIN)
            events = poll.poll(5000)
            if not any(fd == pidfd and mask & select.POLLIN for fd, mask in events):
                raise RuntimeError('fixture positive pidfd exit deadline')
            _, status = os.waitpid(pid, 0)
            child_joined = True
            result['positive_pidfd_exit'] = True
            result['normal_child_wait_status'] = status
            result['fixture_normal_exit'] = os.waitstatus_to_exitcode(status) == 0
            try:
                fcntl.flock(independent, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                result['custody_continues_after_child_exit'] = True
            else:
                raise RuntimeError('fixture custody gap after child exit')
            result['post_exit_fdinfo_lock_rows'] = rows(os.getpid(), duplicate)
            os.close(duplicate)
            duplicate = None
            fcntl.flock(independent, fcntl.LOCK_EX | fcntl.LOCK_NB)
            result['free_only_after_custodian_close'] = True
            result['status'] = 'PASS_REAL_PRIVATE_CROSSPROCESS_CUSTODY'
            return result
        finally:
            if control_w is not None:
                os.close(control_w)
            os.close(ready_r)
            if not child_joined:
                # Child receives EOF and exits normally. No kill/signal fallback.
                _, status = os.waitpid(pid, 0)
                result['normal_child_wait_status'] = status
                result['fixture_normal_exit'] = os.waitstatus_to_exitcode(status) == 0
            for fd in (independent, duplicate, pidfd):
                if fd is not None:
                    os.close(fd)


if __name__ == '__main__':
    started = time.monotonic()
    outcome = main()
    outcome['elapsed_seconds'] = time.monotonic() - started
    print(json.dumps(outcome, sort_keys=True, indent=2))
