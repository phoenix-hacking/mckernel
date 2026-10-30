"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Native pidfd APIs or Linux x86_64/64-bit UAPI syscall equivalents. No PID signals.
"""
import ctypes
import errno
import fcntl
import os
import signal
import struct
import sys

# Independently checked against root-owned asm/unistd_64.h and installed 5.15
# generated x86 UAPI headers; exact local header hashes are in the checkpoint.
NR_PIDFD_SEND_SIGNAL=424
NR_PIDFD_OPEN=434


class UnsupportedRuntime(RuntimeError):pass


class PidfdVerificationError(RuntimeError):
    """The new pidfd exists and must remain retained by its caller."""
    def __init__(self,fd,reason):
        super().__init__('new pidfd verification failed; retain descriptor: '+str(reason))
        self.fd=fd


def fallback_supported():
    return (sys.platform=='linux' and os.uname().machine=='x86_64' and
            struct.calcsize('P')==8 and ctypes.sizeof(ctypes.c_long)==8)


def _syscall():
    if not fallback_supported():raise UnsupportedRuntime('pidfd syscall fallback supports only Linux x86_64/64-bit')
    try:fn=ctypes.CDLL(None,use_errno=True).syscall
    except (OSError,AttributeError) as error:raise UnsupportedRuntime('libc syscall unavailable') from error
    fn.argtypes=[ctypes.c_long];fn.restype=ctypes.c_long
    return fn


def _native_open():return getattr(os,'pidfd_open',None)


def _native_signal():return getattr(signal,'pidfd_send_signal',None)


def require_implementation():
    if callable(_native_open()) and callable(_native_signal()):
        return
    _syscall()


def open_pidfd(pid,flags=0):
    if type(pid) is not int or not 0<pid<=0x7fffffff:raise ValueError('positive pid required')
    nonblock=getattr(os,'O_NONBLOCK',0)
    if type(flags) is not int or flags not in (0,nonblock):raise ValueError('unsupported pidfd flags')
    native=_native_open()
    if callable(native):fd=native(pid,flags)
    else:
        fn=_syscall();ctypes.set_errno(0)
        fd=fn(ctypes.c_long(NR_PIDFD_OPEN),ctypes.c_int(pid),ctypes.c_uint(flags))
        if fd==-1:
            error=ctypes.get_errno();raise OSError(error,os.strerror(error))
        fd=int(fd)
    # Failure after creation is returned with the live FD, never silently lost.
    try:
        if type(fd) is not int or fd<0:raise ValueError('invalid new pidfd')
        descriptor=fcntl.fcntl(fd,fcntl.F_GETFD)
        status=fcntl.fcntl(fd,fcntl.F_GETFL)
        if not descriptor&fcntl.FD_CLOEXEC:raise ValueError('pidfd is not close-on-exec')
        if bool(status&nonblock)!=bool(flags&nonblock):raise ValueError('pidfd nonblocking mode differs')
    except BaseException as error:
        raise PidfdVerificationError(fd,error) from error
    return fd


def send_signal(pidfd,sig,flags=0):
    if type(pidfd) is not int or pidfd<0:raise ValueError('pidfd required')
    if not isinstance(sig,int) or isinstance(sig,bool) or not 0<=int(sig)<signal.NSIG:raise ValueError('signal number')
    if type(flags) is not int or flags!=0:raise ValueError('unsupported signal flags')
    native=_native_signal()
    if callable(native):return native(pidfd,int(sig),None,0)
    fn=_syscall();ctypes.set_errno(0)
    result=fn(ctypes.c_long(NR_PIDFD_SEND_SIGNAL),ctypes.c_int(pidfd),ctypes.c_int(int(sig)),
              ctypes.c_void_p(None),ctypes.c_uint(0))
    if result==-1:
        error=ctypes.get_errno();raise OSError(error,os.strerror(error))
    if result!=0:raise OSError(errno.EIO,'unexpected pidfd signal result')
    return None


def waitstatus_exitcode(status):
    """Portable terminal wait conversion; never implies descendant retirement."""
    if type(status) is not int or status<0:raise ValueError('invalid wait status')
    if os.WIFEXITED(status):return os.WEXITSTATUS(status)
    if os.WIFSIGNALED(status):return -os.WTERMSIG(status)
    raise ValueError('wait status is not exited or signalled')
