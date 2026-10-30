"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Fail-closed Python runtime binding; no fallback, fork, pidfd syscall or signal.
"""
import fcntl
import hashlib
import os
import signal
import stat
import struct
import sys
import threading
import time
import pidfd_compat


class UnsupportedRuntime(RuntimeError):pass


def require_capabilities():
    pidfd_compat.require_implementation()
    required=((signal,'pthread_sigmask'),
              (signal,'sigpending'),(signal,'raise_signal'),(threading,'main_thread'),
              (time,'clock_gettime'),(time,'clock_gettime_ns'))
    missing=[module.__name__+'.'+name for module,name in required if not callable(getattr(module,name,None))]
    if not hasattr(time,'CLOCK_BOOTTIME'):missing.append('time.CLOCK_BOOTTIME')
    if missing:raise UnsupportedRuntime('required runtime APIs unavailable: '+', '.join(missing))


def verify_current(path,expected_sha256):
    """Bind this actual process to one reviewed root-owned immutable executable.

    Expected path/hash come from an authenticated root operation manifest. No
    result here is an account, workload, ownership, or execution admission.
    """
    require_capabilities()
    if (type(path) is not str or not path.startswith('/') or '//' in path or
        any(part in ('','.','..') for part in path.split('/')[1:]) or
        type(expected_sha256) is not str or len(expected_sha256)!=64 or
        any(c not in '0123456789abcdef' for c in expected_sha256)):
        raise UnsupportedRuntime('invalid explicit runtime binding')
    fd=os.open('/',os.O_RDONLY|os.O_DIRECTORY|os.O_CLOEXEC)
    try:
        parts=path.split('/')[1:]
        for index,part in enumerate(parts):
            parent=os.fstat(fd)
            if parent.st_uid!=0 or not stat.S_ISDIR(parent.st_mode) or stat.S_IMODE(parent.st_mode)&0o022:
                raise UnsupportedRuntime('runtime ancestry is not root controlled')
            flags=os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC
            if index<len(parts)-1:flags|=os.O_DIRECTORY
            child=os.open(part,flags,dir_fd=fd);os.close(fd);fd=child
        st=os.fstat(fd)
        if (st.st_uid!=0 or not stat.S_ISREG(st.st_mode) or st.st_nlink!=1 or
            stat.S_IMODE(st.st_mode)&0o022 or st.st_size>128*1024*1024):
            raise UnsupportedRuntime('runtime executable ownership or type')
        b=bytearray(4);fcntl.ioctl(fd,0x80086601,b,True)
        if not struct.unpack('I',b)[0]&0x10:raise UnsupportedRuntime('runtime executable is not immutable')
        h=hashlib.sha256()
        while True:
            data=os.read(fd,1024*1024)
            if not data:break
            h.update(data)
        after=os.fstat(fd)
        before=(st.st_dev,st.st_ino,st.st_size,st.st_mtime_ns,st.st_ctime_ns)
        if before!=(after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns,after.st_ctime_ns) or h.hexdigest()!=expected_sha256:
            raise UnsupportedRuntime('runtime bytes or identity changed')
        actual=os.stat('/proc/self/exe')
        if (actual.st_dev,actual.st_ino)!=(st.st_dev,st.st_ino) or sys.executable!=path:
            raise UnsupportedRuntime('actual process runtime differs')
        return {'path':path,'sha256':expected_sha256,'device':st.st_dev,'inode':st.st_ino,'version':sys.version_info[:3]}
    finally:os.close(fd)
