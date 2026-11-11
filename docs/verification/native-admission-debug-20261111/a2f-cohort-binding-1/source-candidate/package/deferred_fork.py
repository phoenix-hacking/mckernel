"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Main-thread configured-stop deferral around a pre-registered child handoff.
"""
import os
import signal
import socket
import threading
import graph_observations as obs
import pidfd_compat
from ownership_latch import ChildRecord
from pidfd_custody import PidfdCustodyRecord,SocketDupRecord,PublicationUnknown

STOPS=(signal.SIGINT,signal.SIGTERM,signal.SIGHUP,signal.SIGQUIT)
_LOCK=threading.Lock()


class StopBeforeFork(RuntimeError):pass
class StopDuringAcquisition(RuntimeError):pass


class DeferredFork:
    """Defer configured Python stop handlers until PID/pidfd/birth are retained.

    This does not defend against arbitrary async exceptions injected by other
    threads, native code or uncatchable signals. Trusted runtime must route all
    campaign forks through this main-thread guard and retain the watchdog lease.
    """
    def __init__(self):
        self.saved={};self.captured=[];self.original_mask=None
        self.acquired=False;self.entered=False;self.forked=False;self.fd_record=None;self.close_record=None;self.socket_record=None

    def _capture(self,signum,frame):
        self.captured.append(signum)

    def __enter__(self):
        if threading.current_thread() is not threading.main_thread():
            raise RuntimeError('fork handoff requires main thread')
        pidfd_compat.require_implementation()
        if not _LOCK.acquire(False):raise RuntimeError('another fork handoff active')
        self.acquired=True
        try:
            # Install non-raising deferrers before masking. Any old handler that
            # runs during installation runs before the code can fork.
            for sig in STOPS:
                self.saved[sig]=signal.getsignal(sig)
                signal.signal(sig,self._capture)
            self.original_mask=signal.pthread_sigmask(signal.SIG_BLOCK,STOPS)
            self.entered=True
            return self
        except BaseException:
            self._restore(False)
            raise

    def _restore(self,child):
        error=None;queued=set()
        try:
            if self.original_mask is not None and not child:
                # Queue before unmasking; standard-signal coalescing is retained.
                for sig in set(self.captured):
                    if self.saved.get(sig) != signal.SIG_IGN:
                        try:signal.raise_signal(sig);queued.add(sig)
                        except BaseException as exc:
                            if error is None:error=exc
            for sig,handler in self.saved.items():
                try:signal.signal(sig,handler)
                except BaseException as exc:
                    if error is None:error=exc
            if self.original_mask is not None and not child:
                for sig in set(self.captured)-queued:
                    if self.saved.get(sig) != signal.SIG_IGN:
                        try:signal.raise_signal(sig)
                        except BaseException as exc:
                            if error is None:error=exc
            if self.original_mask is not None and not child and self.fd_record is not None:
                try:
                    if self.fd_record.state=='VERIFIED_HELD' and (self.captured or set(signal.sigpending()).intersection(STOPS)):
                        self.fd_record.retain_unknown(self.fd_record.fd,self.fd_record.target_pid,self.fd_record.target_birth)
                except BaseException as exc:
                    if error is None:error=exc
            if self.original_mask is not None and not child and self.close_record is not None:
                try:
                    if self.close_record.state in ('CLOSING','VERIFIED_CLOSED') and (self.captured or set(signal.sigpending()).intersection(STOPS)):
                        self.close_record.closure_unknown()
                except BaseException as exc:
                    if error is None:error=exc
            if self.original_mask is not None and not child and self.socket_record is not None:
                try:
                    if self.socket_record.state in ('DUPLICATED','ADOPTED','CLOSING','VERIFIED_CLOSED') and (self.captured or set(signal.sigpending()).intersection(STOPS)):
                        self.socket_record.closure_unknown()
                except BaseException as exc:
                    if error is None:error=exc
            if self.original_mask is not None:
                try:signal.pthread_sigmask(signal.SIG_SETMASK,self.original_mask)
                except BaseException as exc:
                    if error is None:error=exc
        finally:
            self.entered=False
            if self.acquired:
                self.acquired=False;_LOCK.release()
        if error is not None:raise error

    def __exit__(self,kind,value,traceback):
        failure=None
        try:
            if self.fd_record is not None and self.fd_record.state=='VERIFIED_HELD':
                if kind is not None or self.captured or set(signal.sigpending()).intersection(STOPS):
                    self.fd_record.retain_unknown(self.fd_record.fd,self.fd_record.target_pid,self.fd_record.target_birth)
        except BaseException as error:failure=error
        try:
            if self.close_record is not None and self.close_record.state in ('CLOSING','VERIFIED_CLOSED'):
                if kind is not None or self.captured or set(signal.sigpending()).intersection(STOPS):
                    self.close_record.closure_unknown()
        except BaseException as error:failure=error
        try:
            if self.socket_record is not None and self.socket_record.state in ('DUPLICATED','ADOPTED','CLOSING','VERIFIED_CLOSED'):
                if kind is not None or self.captured or set(signal.sigpending()).intersection(STOPS):
                    self.socket_record.closure_unknown()
        except BaseException as error:failure=error
        try:self._restore(False)
        except BaseException as error:
            if self.socket_record is not None and self.socket_record.state in ('DUPLICATED','ADOPTED','CLOSING','VERIFIED_CLOSED'):
                try:self.socket_record.closure_unknown()
                except BaseException as publication:failure=publication
            if self.close_record is not None and self.close_record.state in ('CLOSING','VERIFIED_CLOSED'):
                try:self.close_record.closure_unknown()
                except BaseException as publication:failure=publication
            if self.fd_record is not None and self.fd_record.state=='VERIFIED_HELD':
                try:self.fd_record.retain_unknown(self.fd_record.fd,self.fd_record.target_pid,self.fd_record.target_birth)
                except BaseException as publication:failure=publication
            if failure is None:failure=error
        if failure is not None:raise failure
        if kind is None and self.socket_record is not None and self.socket_record.state=='CLOSURE_UNKNOWN':
            raise StopDuringAcquisition('uncertain socket disposition')
        if kind is None and self.close_record is not None and self.close_record.state=='CLOSURE_UNKNOWN':
            raise StopDuringAcquisition('uncertain session close')
        if kind is None and self.fd_record is not None and self.fd_record.state=='UNKNOWN_RETAINED':
            raise StopDuringAcquisition('configured stop during pidfd acquisition')
        return False

    def acquire_and_pin(self,record,pid,birth):
        if not self.entered or self.forked or type(record) is not PidfdCustodyRecord:
            raise RuntimeError('guard and pre-registered pidfd record required')
        if record.state!='REGISTERED':raise RuntimeError('pidfd record already used')
        if self.captured or set(signal.sigpending()).intersection(STOPS):
            raise StopBeforeFork('configured stop pending before pidfd acquisition')
        self.forked=True
        try:fd=pidfd_compat.open_pidfd(pid,0)
        except pidfd_compat.PidfdVerificationError as error:
            self.fd_record=record
            try:record.retain_unknown(error.fd,pid,birth)
            except PublicationUnknown as publication:
                publication.pidfd_error=error
                raise
            error.custody_record=record
            raise
        self.fd_record=record
        record.retain_verified(fd,pid,birth)
        return fd

    def duplicate_and_adopt(self,record,source_fd):
        if not self.entered or self.forked or type(record) is not SocketDupRecord or record.state!='REGISTERED':
            raise RuntimeError('pre-owned socket duplicate record required')
        self.forked=True;self.socket_record=record
        try:
            if self.captured or set(signal.sigpending()).intersection(STOPS):
                record.closure_unknown();raise StopDuringAcquisition('stop before duplicate')
            fd=os.dup(source_fd)
            record.assigned(fd)
            sock=socket.socket(fileno=fd)
            record.adopted(sock)
            return sock
        except BaseException:
            if record.state!='CLOSURE_UNKNOWN':record.closure_unknown()
            raise

    def close_session(self,record,socket_record):
        if not self.entered or self.forked or type(record) is not PidfdCustodyRecord or type(socket_record) is not SocketDupRecord:
            raise RuntimeError('guard and owned records required')
        if record.state!='VERIFIED_HELD':raise RuntimeError('pidfd unavailable for close')
        if socket_record.state!='ADOPTED':raise RuntimeError('socket unavailable for close')
        self.forked=True;self.close_record=record;self.socket_record=socket_record
        try:
            if self.captured or set(signal.sigpending()).intersection(STOPS):
                record.closure_unknown();socket_record.closure_unknown()
                raise StopDuringAcquisition('stop before session close')
            with record.lock:
                with socket_record.lock:
                    record.begin_close();socket_record.begin_close()
                    socket_record.socket.close();socket_record.closed_after_syscall()
                    os.close(record.fd);record.closed_after_syscall()
        except BaseException:
            if record.state in ('VERIFIED_HELD','CLOSING','VERIFIED_CLOSED'):
                record.closure_unknown()
            if socket_record.state in ('ADOPTED','CLOSING'):
                socket_record.closure_unknown()
            raise

    def fork_and_pin(self,record,child_callback):
        if not self.entered or self.forked or type(record) is not ChildRecord or not callable(child_callback):
            raise RuntimeError('guard and pre-registered child record required')
        pending=set(signal.sigpending()).intersection(STOPS)
        if pending or self.captured:
            record.unknown('configured stop pending before fork')
            raise StopBeforeFork('configured stop pending before fork')
        self.forked=True
        try:
            pid=os.fork()
        except BaseException as error:
            record.unknown(error)
            raise
        if pid==0:
            # Stops remain masked while entering this child-only finally region.
            # No restored handler or exec error may return into the parent path.
            try:
                self._restore(True)
                child_callback()
            finally:
                os._exit(127)
            raise RuntimeError('child os._exit unexpectedly returned')
        try:
            record.assigned(pid)  # first Python-level parent action
            try:pidfd=pidfd_compat.open_pidfd(pid,0)
            except pidfd_compat.PidfdVerificationError as error:
                record.pin_pidfd(error.fd)
                raise
            record.pin_pidfd(pidfd)
            birth=obs.process(pid)[0]
            record.identified(birth,pidfd)
            return pid,pidfd,birth
        except BaseException as error:
            record.unknown(error)
            raise
