"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Mocked child-restoration tests; no real fork or signal. Do not run without admission.
"""
import signal
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

base=Path(__file__).parent.parent
sys.path.append(str(base/'pidfd-compat-expert-1'))
sys.path.append(str(base/'adapter-readiness-expert-1'))
import deferred_fork as subject
from ownership_latch import CustodyLatch


class ChildExit(BaseException):pass


class FakeSignals:
    SIG_IGN=signal.SIG_IGN
    SIG_SETMASK=signal.SIG_SETMASK
    def __init__(self):self.events=[]
    def sigpending(self):return set()
    def signal(self,sig,handler):self.events.append(('handler',sig,handler))
    def pthread_sigmask(self,how,mask):
        self.events.append(('mask',how,tuple(mask)))
        raise KeyboardInterrupt('pending child handler')


class ChildRestorationCases(unittest.TestCase):
    def setUp(self):
        self.latch=CustodyLatch('ROOT_HELD');self.record=self.latch.reserve_child('validator')
        self.guard=subject.DeferredFork();self.guard.entered=True

    def test_child_restoration_error_exits_without_parent_cleanup(self):
        with patch.object(subject.signal,'sigpending',return_value=set()),\
             patch.object(subject.os,'fork',return_value=0),\
             patch.object(self.guard,'_restore',side_effect=RuntimeError('restore failed')),\
             patch.object(subject.os,'_exit',side_effect=ChildExit) as exit_call:
            with self.assertRaises(ChildExit):self.guard.fork_and_pin(self.record)
        exit_call.assert_called_once_with(127)
        self.assertEqual(self.record.status,'PENDING');self.assertIsNone(self.latch.failure)

    def test_pending_handler_raise_occurs_after_handler_restore_then_child_exit(self):
        fake=FakeSignals();self.guard.saved={sig:'original' for sig in subject.STOPS}
        self.guard.original_mask={99};self.guard.acquired=False
        with patch.object(subject,'signal',fake),patch.object(subject.os,'fork',return_value=0),\
             patch.object(subject.os,'_exit',side_effect=ChildExit) as exit_call:
            with self.assertRaises(ChildExit):self.guard.fork_and_pin(self.record)
        exit_call.assert_called_once_with(127)
        self.assertEqual([event[0] for event in fake.events],['handler']*len(subject.STOPS)+['mask'])
        self.assertEqual(self.record.status,'PENDING');self.assertIsNone(self.latch.failure)


if __name__=='__main__':unittest.main()
