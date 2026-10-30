"""Functional-only synthetic actual-adapter disposition tests. UNRUN.
FD, socket and configured-signal operations are mocked; no root/fork/pidfd.
"""
import signal
import threading
import unittest
from unittest.mock import patch
import adapter
import compositor
import deferred_fork
import pidfd_custody


class FakeSignals:
    SIG_IGN=signal.SIG_IGN;SIG_BLOCK=signal.SIG_BLOCK;SIG_SETMASK=signal.SIG_SETMASK
    def __init__(self):self.pending=set()
    def getsignal(self,sig):return 'old'
    def signal(self,sig,handler):pass
    def pthread_sigmask(self,how,mask):return set()
    def sigpending(self):return self.pending.copy()
    def raise_signal(self,sig):self.pending.add(sig)


class Socket:
    family=1
    def __init__(self,events,fail=False,action=None):self.events=events;self.fail=fail;self.action=action
    def close(self):
        self.events.append('socket-close')
        if self.action:self.action()
        if self.fail:raise OSError('synthetic socket close uncertainty')


class ActualDispositionCases(unittest.TestCase):
    def setUp(self):
        self.events=[];self.signals=FakeSignals()
        self.record=pidfd_custody.PidfdCustodyRecord.__new__(pidfd_custody.PidfdCustodyRecord)
        self.record.state='VERIFIED_HELD';self.record.fd=71;self.record.target_pid=12
        self.record.target_birth='123';self.record.lock=threading.RLock()
        self.duplicate=pidfd_custody.SocketDupRecord.__new__(pidfd_custody.SocketDupRecord)
        self.duplicate.parent=self.record;self.duplicate.fd=72;self.duplicate.historical_fd=72
        self.duplicate.state='ADOPTED';self.duplicate.lock=threading.RLock()
        self.duplicate.socket=Socket(self.events)
        self.owner=compositor.OperationCustody(9,'a'*64);self.owner.record=self.record
        self.owner.duplicate=self.duplicate;self.owner.state='REGISTERED'
        self.session=adapter.CustodySession.__new__(adapter.CustodySession)
        self.session.pidfd_record=self.record;self.session.duplicate=self.duplicate;self.session.owner=self.owner
        self.session.sock=self.duplicate.socket;self.session.closed=False
        self.session.close_state='OPEN';self.session.session_lock=threading.RLock();self.owner.session=self.session
    def invoke(self,close_fn):
        def pid_publish(status,*args):self.events.append('pid-'+status)
        def socket_publish():self.events.append('socket-'+self.duplicate.state)
        with patch.object(deferred_fork,'signal',self.signals),\
             patch.object(deferred_fork.pidfd_compat,'require_implementation'),\
             patch.object(self.record,'_publish',side_effect=pid_publish),\
             patch.object(self.duplicate,'_publish',side_effect=socket_publish),\
             patch.object(deferred_fork.os,'close',side_effect=close_fn):
            return self.session.close(self.owner)
    def test_confirmed_close(self):
        self.invoke(lambda fd:self.events.append(('pidfd-close',fd)))
        self.assertEqual(self.events,['pid-CLOSING','socket-CLOSING','socket-close','socket-VERIFIED_CLOSED',('pidfd-close',71),'pid-VERIFIED_CLOSED'])
        self.assertEqual((self.record.state,self.record.fd),('VERIFIED_CLOSED',None))
        self.assertEqual((self.duplicate.state,self.duplicate.fd),('VERIFIED_CLOSED',None))
        self.assertTrue(self.session.closed)
    def test_pending_before_close_never_calls_close(self):
        self.signals.pending.add(deferred_fork.STOPS[0])
        with self.assertRaises(deferred_fork.StopDuringAcquisition):
            self.invoke(lambda fd:self.fail('must not close'))
        self.assertEqual((self.record.state,self.record.fd),('CLOSURE_UNKNOWN',None))
        self.assertEqual((self.duplicate.state,self.duplicate.fd),('CLOSURE_UNKNOWN',None))
        self.assertNotIn('socket-close',self.events)
        with self.assertRaises(RuntimeError):self.session.close(self.owner)
    def test_pending_after_syscall_never_reuses_numeric_descriptor(self):
        def close(fd):self.events.append(('pidfd-close',fd));self.signals.pending.add(deferred_fork.STOPS[0])
        with self.assertRaises(deferred_fork.StopDuringAcquisition):self.invoke(close)
        self.assertEqual((self.record.state,self.record.fd),('CLOSURE_UNKNOWN',None))
        self.assertEqual((self.duplicate.state,self.duplicate.fd),('CLOSURE_UNKNOWN',None))
        self.assertEqual(self.record.historical_fd,71);self.assertEqual(self.events.count(('pidfd-close',71)),1)
        with self.assertRaises(RuntimeError):self.session.close(self.owner)
    def test_partial_socket_close_does_not_close_pidfd(self):
        self.duplicate.socket=Socket(self.events,True);self.session.sock=self.duplicate.socket
        with self.assertRaises(OSError):self.invoke(lambda fd:self.fail('must not close'))
        self.assertEqual((self.record.state,self.record.fd),('CLOSURE_UNKNOWN',None))
        self.assertEqual((self.duplicate.state,self.duplicate.fd),('CLOSURE_UNKNOWN',None))
    def test_unknown_before_admission_blocks_close(self):
        with patch.object(self.record,'_publish'),patch.object(self.duplicate,'_publish'):
            self.owner.retain_session_unknown(self.session)
        with self.assertRaises(RuntimeError):self.session.close(self.owner)
        self.assertEqual(self.events,[]);self.assertEqual(self.owner.state,'UNKNOWN_RETAINED')
    def test_unknown_concurrent_with_close_waits_for_confirmed_disposition(self):
        attempted=threading.Event();done=threading.Event();threads=[]
        def fail_owner():
            attempted.set();self.owner.retain_session_unknown(self.session);done.set()
        def on_socket_close():
            thread=threading.Thread(target=fail_owner);threads.append(thread);thread.start()
            self.assertTrue(attempted.wait(1));self.assertFalse(done.is_set())
        self.duplicate.socket.action=on_socket_close
        self.invoke(lambda fd:self.events.append(('pidfd-close',fd)))
        threads[0].join(1);self.assertTrue(done.is_set())
        self.assertEqual(self.owner.state,'UNKNOWN_RETAINED')
        self.assertEqual((self.record.state,self.record.fd),('VERIFIED_CLOSED',None))
        self.assertEqual((self.duplicate.state,self.duplicate.fd),('VERIFIED_CLOSED',None))
    def test_revalidate_failure_never_eagerly_disposes(self):
        with patch.object(self.session,'_revalidate',side_effect=ValueError('synthetic')):
            with self.assertRaises(ValueError):self.session.revalidate()
        self.assertEqual((self.record.state,self.record.fd),('VERIFIED_HELD',71))
        self.assertEqual(self.events,[])
    def test_duplicate_adoption_failure_is_unknown_and_never_closed_again(self):
        self.record.state='REGISTERED';self.record.fd=None
        self.duplicate.state='REGISTERED';self.duplicate.fd=None;self.duplicate.socket=None
        self.owner.session=adapter.CustodySession.__new__(adapter.CustodySession)
        with patch.object(deferred_fork,'signal',self.signals),\
             patch.object(deferred_fork.pidfd_compat,'require_implementation'),\
             patch.object(deferred_fork.os,'dup',return_value=75),\
             patch.object(deferred_fork.os,'close') as close,\
             patch.object(deferred_fork.socket,'socket',side_effect=OSError('adoption failed')),\
             patch.object(self.duplicate,'_publish'):
            with self.assertRaises(OSError):self.owner.session.__init__(5,self.record,self.owner)
        self.assertEqual((self.duplicate.state,self.duplicate.fd),('CLOSURE_UNKNOWN',None))
        self.assertEqual(self.duplicate.historical_fd,75);close.assert_not_called()
    def test_constructor_error_after_adoption_never_eagerly_closes(self):
        self.record.state='REGISTERED';self.record.fd=None
        self.duplicate.state='REGISTERED';self.duplicate.fd=None;self.duplicate.socket=None
        self.owner.session=adapter.CustodySession.__new__(adapter.CustodySession)
        wrong=Socket(self.events);wrong.family=-1
        with patch.object(deferred_fork,'signal',self.signals),\
             patch.object(deferred_fork.pidfd_compat,'require_implementation'),\
             patch.object(deferred_fork.os,'dup',return_value=75),\
             patch.object(deferred_fork.socket,'socket',return_value=wrong),\
             patch.object(adapter,'load_wire',return_value=object()),\
             patch.object(self.duplicate,'_publish'):
            with self.assertRaises(ValueError):self.owner.session.__init__(5,self.record,self.owner)
        self.assertEqual(self.duplicate.state,'ADOPTED');self.assertEqual(self.events,[])
        self.assertIs(self.duplicate.socket,wrong)


if __name__=='__main__':unittest.main()
