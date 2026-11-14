"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Fake-fork and fake-signal ordering tests; do not run without approved profile.
"""
import signal as real_signal
import sys
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(1,str(Path(__file__).parent.parent/'adapter-readiness-expert-1'))
import deferred_fork as subject
from ownership_latch import CustodyLatch


class FakeSignals:
    SIG_BLOCK=real_signal.SIG_BLOCK
    SIG_SETMASK=real_signal.SIG_SETMASK
    SIG_IGN=real_signal.SIG_IGN
    def __init__(self,record=None,pending=()):
        self.record=record;self.pending=set(pending);self.events=[];self.handlers={}
    def getsignal(self,sig):return 'original-'+str(sig)
    def signal(self,sig,handler):self.events.append(('handler',sig,handler));self.handlers[sig]=handler
    def pthread_sigmask(self,how,mask):
        self.events.append(('mask',how,tuple(mask)));return {999} if how==self.SIG_BLOCK else set()
    def sigpending(self):return set(self.pending)
    def raise_signal(self,sig):
        self.events.append(('replay',sig))
        if self.record is not None and (self.record.pid,self.record.pidfd,self.record.birth)!=(12345,91,'123456'):
            raise AssertionError('stop delivered before complete child record')


class GuardCases(unittest.TestCase):
    def setUp(self):
        self.api=patch.object(subject.pidfd_compat,'require_implementation',return_value=None);self.api.start()
    def tearDown(self):self.api.stop()
    def record(self):return CustodyLatch('ROOT_HELD').reserve_child('owner','lease')

    def test_stop_in_fork_return_gap_is_replayed_after_complete_record(self):
        record=self.record();fake=FakeSignals(record);guard=subject.DeferredFork()
        def fake_fork():
            guard._capture(real_signal.SIGTERM,None)
            return 12345
        with patch.object(subject,'signal',fake),patch.object(subject.os,'fork',side_effect=fake_fork),\
             patch.object(subject.pidfd_compat,'open_pidfd',return_value=91),patch.object(subject.obs,'process',return_value=('123456',1,2)):
            with guard:
                self.assertEqual(guard.fork_and_pin(record),(12345,91,'123456'))
                self.assertFalse(any(event[0]=='replay' for event in fake.events))
        self.assertEqual(record.status,'IDENTIFIED')
        self.assertIn(('replay',real_signal.SIGTERM),fake.events)
        self.assertEqual(fake.events[-1][0:2],('mask',fake.SIG_SETMASK))

    def test_already_pending_stop_cancels_before_fork(self):
        record=self.record();fake=FakeSignals(pending=(real_signal.SIGINT,));guard=subject.DeferredFork()
        with patch.object(subject,'signal',fake),patch.object(subject.os,'fork') as fork:
            with self.assertRaises(subject.StopBeforeFork):
                with guard:guard.fork_and_pin(record)
            fork.assert_not_called()
        self.assertIsNone(record.pid);self.assertEqual(record.status,'UNKNOWN_RETAINED')

    def test_pidfd_failure_keeps_assigned_pid_unknown(self):
        record=self.record();fake=FakeSignals();guard=subject.DeferredFork()
        with patch.object(subject,'signal',fake),patch.object(subject.os,'fork',return_value=12345),\
             patch.object(subject.pidfd_compat,'open_pidfd',side_effect=OSError('fixture')):
            with self.assertRaises(OSError):
                with guard:guard.fork_and_pin(record)
        self.assertEqual(record.pid,12345);self.assertIsNone(record.pidfd)
        self.assertEqual(record.status,'UNKNOWN_RETAINED')

    def test_postopen_verification_error_retains_fd_and_pid(self):
        record=self.record();fake=FakeSignals();guard=subject.DeferredFork()
        error=subject.pidfd_compat.PidfdVerificationError(91,'fixture')
        with patch.object(subject,'signal',fake),patch.object(subject.os,'fork',return_value=12345),\
             patch.object(subject.pidfd_compat,'open_pidfd',side_effect=error):
            with self.assertRaises(subject.pidfd_compat.PidfdVerificationError):
                with guard:guard.fork_and_pin(record)
        self.assertEqual((record.pid,record.pidfd),(12345,91))
        self.assertEqual(record.status,'UNKNOWN_RETAINED')

    def test_child_restores_handlers_and_mask_before_continuation(self):
        record=self.record();fake=FakeSignals();guard=subject.DeferredFork()
        with patch.object(subject,'signal',fake),patch.object(subject.os,'fork',return_value=0):
            guard.__enter__()
            self.assertEqual(guard.fork_and_pin(record),(0,None,None))
            self.assertEqual(fake.events[-1][0:2],('mask',fake.SIG_SETMASK))
            self.assertFalse(guard.entered)

    def test_non_main_thread_cannot_enter(self):
        errors=[]
        def worker():
            try:subject.DeferredFork().__enter__()
            except RuntimeError as exc:errors.append(str(exc))
        thread=threading.Thread(target=worker);thread.start();thread.join()
        self.assertEqual(errors,['fork handoff requires main thread'])


if __name__=='__main__':unittest.main()
