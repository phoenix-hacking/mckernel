"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Main-thread configured-stop deferral around a pre-registered child handoff.
"""
import os
import signal
import threading
import graph_observations as obs
import pidfd_compat
from ownership_latch import ChildRecord

STOPS=(signal.SIGINT,signal.SIGTERM,signal.SIGHUP,signal.SIGQUIT)
_LOCK=threading.Lock()


class StopBeforeFork(RuntimeError):pass


class DeferredFork:
    """Defer configured Python stop handlers until PID/pidfd/birth are retained.

    This does not defend against arbitrary async exceptions injected by other
    threads, native code or uncatchable signals. Trusted runtime must route all
    campaign forks through this main-thread guard and retain the watchdog lease.
    """
    def __init__(self):
        self.saved={};self.captured=[];self.original_mask=None
        self.acquired=False;self.entered=False;self.forked=False

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
        self._restore(False)
        return False

    def fork_and_pin(self,record):
        if not self.entered or self.forked or type(record) is not ChildRecord:
            raise RuntimeError('guard and pre-registered child record required')
        pending=set(signal.sigpending()).intersection(STOPS)
        if pending or self.captured:
            record.unknown('configured stop pending before fork')
            raise StopBeforeFork('configured stop pending before fork')
        self.forked=True
        try:
            pid=os.fork()
            if pid==0:
                # Child never replays parent-captured stops. Restore original
                # disposition and thread mask before any child exec path.
                self._restore(True)
                return 0,None,None
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
