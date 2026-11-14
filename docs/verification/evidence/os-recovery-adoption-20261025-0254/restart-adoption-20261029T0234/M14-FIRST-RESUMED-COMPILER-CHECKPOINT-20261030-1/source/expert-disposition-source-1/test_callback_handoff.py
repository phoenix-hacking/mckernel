"""Functional OS synthetic regressions. No real fork, signal, pidfd or root operation.
UNRUN: reviewed admission required before execution.
"""
import sys
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

base=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(base/'adapter-readiness-expert-1'))
sys.path.insert(0,str(Path(__file__).resolve().parent))
import deferred_fork as subject
from ownership_latch import CustodyLatch
from pidfd_custody import PidfdCustodyRecord

class ChildExit(BaseException):pass

class FakeSignals:
    SIG_IGN=object();SIG_SETMASK=1;SIG_BLOCK=2
    def __init__(self,pending=()):self.pending=set(pending);self.events=[]
    def sigpending(self):return self.pending.copy()
    def getsignal(self,sig):return 'original'
    def signal(self,sig,handler):self.events.append(('handler',sig,handler))
    def pthread_sigmask(self,how,mask):self.events.append(('mask',how));return set()
    def raise_signal(self,sig):self.events.append(('raise',sig));self.pending.add(sig)

class CallbackCases(unittest.TestCase):
    def setUp(self):
        self.latch=CustodyLatch('ROOT_HELD');self.record=self.latch.reserve_child('validator')
        self.guard=subject.DeferredFork();self.guard.entered=True
    def check_child(self,restore,callback):
        fake=FakeSignals()
        with patch.object(subject,'signal',fake),patch.object(subject.os,'fork',return_value=0),\
             patch.object(self.guard,'_restore',side_effect=restore),\
             patch.object(subject.os,'_exit',side_effect=ChildExit) as exited:
            with self.assertRaises(ChildExit):self.guard.fork_and_pin(self.record,callback)
        exited.assert_called_once_with(127)
        self.assertEqual(self.record.status,'PENDING');self.assertIsNone(self.latch.failure)
    def test_restore_raising_never_enters_callback_or_parent_cleanup(self):
        calls=[]
        def restore(_):raise KeyboardInterrupt('synthetic pending handler')
        self.check_child(restore,lambda:calls.append('called'))
        self.assertEqual(calls,[])
    def test_callback_raise_never_returns_to_parent(self):
        def callback():raise ValueError('synthetic exec failure')
        self.check_child(lambda child:None,callback)
    def test_callback_return_still_exits(self):
        self.check_child(lambda child:None,lambda:None)
    def test_real_restore_orders_handlers_before_unmask(self):
        fake=FakeSignals();self.guard.saved={sig:'original' for sig in subject.STOPS}
        self.guard.original_mask={99}
        def unmask(how,mask):fake.events.append(('mask',how));raise KeyboardInterrupt('pending handler')
        fake.pthread_sigmask=unmask
        with patch.object(subject,'signal',fake),patch.object(subject.os,'fork',return_value=0),\
             patch.object(subject.os,'_exit',side_effect=ChildExit):
            with self.assertRaises(ChildExit):self.guard.fork_and_pin(self.record,lambda:None)
        self.assertEqual([e[0] for e in fake.events],['handler']*len(subject.STOPS)+['mask'])
        self.assertEqual(self.record.status,'PENDING')

class AcquisitionCases(unittest.TestCase):
    def record(self):
        record=PidfdCustodyRecord.__new__(PidfdCustodyRecord)
        record.state='REGISTERED';record.fd=None;record.lock=threading.RLock()
        return record
    def test_stop_captured_after_open_is_retained_before_unmask(self):
        record=self.record();guard=subject.DeferredFork();guard.entered=True
        fake=FakeSignals();events=[]
        def opened(pid,flags):guard._capture(subject.STOPS[0],None);events.append('opened');return 91
        def publish(status,*args):events.append(status)
        def restore(child):
            events.append('restore');self.assertEqual(record.state,'UNKNOWN_RETAINED')
        with patch.object(subject,'signal',fake),patch.object(subject.pidfd_compat,'open_pidfd',side_effect=opened),\
             patch.object(record,'_publish',side_effect=publish),patch.object(guard,'_restore',side_effect=restore),\
             patch.object(subject.os,'close') as closed:
            guard.acquire_and_pin(record,7,'123')
            with self.assertRaises(subject.StopDuringAcquisition):guard.__exit__(None,None,None)
        self.assertEqual(events,['opened','VERIFIED_HELD','UNKNOWN_RETAINED','restore'])
        self.assertEqual(record.fd,91);closed.assert_not_called()
    def test_restore_handler_raise_keeps_preallocated_record(self):
        record=self.record();guard=subject.DeferredFork();guard.entered=True
        fake=FakeSignals()
        with patch.object(subject,'signal',fake),patch.object(subject.pidfd_compat,'open_pidfd',return_value=92),\
             patch.object(record,'_publish'),patch.object(guard,'_restore',side_effect=KeyboardInterrupt),\
             patch.object(subject.os,'close') as closed:
            guard.acquire_and_pin(record,8,'456')
            with self.assertRaises(KeyboardInterrupt):guard.__exit__(None,None,None)
        self.assertEqual((record.state,record.fd),('UNKNOWN_RETAINED',92));closed.assert_not_called()

if __name__=='__main__':unittest.main()
