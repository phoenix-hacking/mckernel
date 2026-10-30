"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Main-thread configured-stop deferral around a pre-registered child handoff.
"""
import os
import signal
import threading
import graph_observations as obs
import pidfd_compat
from ownership_latch import ChildRecord
from pidfd_custody import PidfdCustodyRecord,PublicationUnknown

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
        self.acquired=False;self.entered=False;self.forked=False;self.fd_record=None

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
        try:self._restore(False)
        except BaseException as error:
            if self.fd_record is not None and self.fd_record.state=='VERIFIED_HELD':
                try:self.fd_record.retain_unknown(self.fd_record.fd,self.fd_record.target_pid,self.fd_record.target_birth)
                except BaseException as publication:failure=publication
            if failure is None:failure=error
        if failure is not None:raise failure
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
