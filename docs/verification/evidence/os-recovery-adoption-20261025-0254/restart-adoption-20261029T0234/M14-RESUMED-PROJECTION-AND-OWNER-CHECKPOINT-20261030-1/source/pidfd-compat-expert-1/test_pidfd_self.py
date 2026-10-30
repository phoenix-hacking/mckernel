"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Proposed unprivileged self-pidfd and signal-zero host check. Do not run without admission.
"""
import fcntl
import os
import pidfd_compat


def main():
    fd=pidfd_compat.open_pidfd(os.getpid(),0)
    try:
        if not fcntl.fcntl(fd,fcntl.F_GETFD)&fcntl.FD_CLOEXEC:raise RuntimeError('CLOEXEC absent')
        if fcntl.fcntl(fd,fcntl.F_GETFL)&os.O_NONBLOCK:raise RuntimeError('unexpected nonblocking flag')
        with open('/proc/self/fdinfo/%d'%fd) as stream:
            rows=dict(line.split(':',1) for line in stream if ':' in line)
        if int(rows['Pid'].strip())!=os.getpid():raise RuntimeError('pidfd identity differs')
        pidfd_compat.send_signal(fd,0)
        print('PASS self pidfd identity, CLOEXEC and pidfd signal 0')
    finally:os.close(fd)


if __name__=='__main__':main()
