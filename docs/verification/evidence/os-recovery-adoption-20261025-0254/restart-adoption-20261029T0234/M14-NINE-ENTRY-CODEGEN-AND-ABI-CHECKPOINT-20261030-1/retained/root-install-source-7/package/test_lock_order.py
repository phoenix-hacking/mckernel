"""Functional-only synthetic actual-adapter lock ordering tests. UNRUN.
No real fork, configured signals, pidfd syscall, or privileged operation.
"""
import os
import socket
import struct
import threading
import unittest
from unittest.mock import patch
import adapter
import compositor
import pidfd_custody


def setup_owner():
    record=pidfd_custody.PidfdCustodyRecord.__new__(pidfd_custody.PidfdCustodyRecord)
    record.state='REGISTERED';record.fd=None;record.lock=threading.RLock()
    dup=pidfd_custody.SocketDupRecord.__new__(pidfd_custody.SocketDupRecord)
    dup.state='REGISTERED';dup.fd=None;dup.historical_fd=None;dup.socket=None;dup.lock=threading.RLock()
    owner=compositor.OperationCustody(9,'a'*64);owner.record=record;owner.duplicate=dup;owner.state='REGISTERED'
    session=adapter.CustodySession.__new__(adapter.CustodySession);owner.session=session
    return owner,session,record,dup


class ConstructorCases(unittest.TestCase):
    def test_reentrant_unknown_on_pidfd_guard_restore_blocks_authentication(self):
        owner,session,record,dup=setup_owner()
        class Sock:
            family=socket.AF_UNIX
            def getsockopt(self,level,opt,*args):
                return socket.SOCK_STREAM if opt==socket.SO_TYPE else struct.pack('3i',os.getppid(),0,0)
        sock=Sock();guards=[]
        class Guard:
            def __enter__(self):guards.append(self);return self
            def duplicate_and_adopt(self,record_arg,fd):
                dup.state='ADOPTED';dup.fd=73;dup.historical_fd=73;dup.socket=sock;return sock
            def acquire_and_pin(self,record_arg,pid,birth):
                record.state='VERIFIED_HELD';record.fd=74;record.target_pid=pid;record.target_birth=birth
                return 74
            def __exit__(self,kind,value,tb):
                if len(guards)==2:owner.retain_session_unknown(session)
        with patch.object(adapter.deferred_fork,'DeferredFork',Guard),\
             patch.object(adapter,'load_wire',return_value=object()),\
             patch.object(adapter,'proc_identity',return_value=(1,'123')),\
             patch.object(adapter,'trusted_file') as trusted,\
             patch.object(record,'_publish'),patch.object(dup,'_publish'):
            with self.assertRaisesRegex(ValueError,'no longer live'):session.__init__(9,record,owner)
        trusted.assert_not_called()
        self.assertEqual(owner.state,'UNKNOWN_RETAINED')
        self.assertEqual(record.state,'UNKNOWN_RETAINED')
        self.assertEqual((dup.state,dup.fd),('CLOSURE_UNKNOWN',None))
        self.assertFalse(hasattr(session,'data'))


class RevalidationCases(unittest.TestCase):
    def setUp(self):
        self.owner,self.session,self.record,self.dup=setup_owner()
        self.record.state='VERIFIED_HELD';self.record.fd=74;self.record.target_pid=5;self.record.target_birth='123'
        self.dup.state='ADOPTED';self.dup.fd=73;self.dup.historical_fd=73
        self.session.pidfd_record=self.record;self.session.duplicate=self.dup;self.session.owner=self.owner
        self.session.session_lock=threading.RLock();self.session.close_state='OPEN';self.session.closed=False
    def test_cross_thread_unknown_waits_for_owner_locked_revalidation(self):
        entered=threading.Event();proceed=threading.Event();attempted=threading.Event();failed=threading.Event();values=[]
        def revalidate_body():entered.set();self.assertTrue(proceed.wait(2));return 'verified-data'
        def reader():values.append(self.session.revalidate())
        def fail_owner():attempted.set();self.owner.retain_session_unknown(self.session);failed.set()
        with patch.object(self.session,'_revalidate',side_effect=revalidate_body),\
             patch.object(self.record,'_publish'),patch.object(self.dup,'_publish'):
            reader_thread=threading.Thread(target=reader);reader_thread.start();self.assertTrue(entered.wait(2))
            fail_thread=threading.Thread(target=fail_owner);fail_thread.start();self.assertTrue(attempted.wait(2))
            self.assertFalse(failed.is_set());proceed.set();reader_thread.join(2);fail_thread.join(2)
            self.assertFalse(reader_thread.is_alive());self.assertFalse(fail_thread.is_alive())
            self.assertEqual(values,['verified-data']);self.assertTrue(failed.is_set())
            with self.assertRaisesRegex(ValueError,'no longer live'):self.session.revalidate()
        self.assertEqual(self.owner.state,'UNKNOWN_RETAINED')
    def test_reentrant_unknown_during_revalidation_prevents_data_return(self):
        def body():self.owner.retain_session_unknown(self.session);return 'must-not-escape'
        with patch.object(self.session,'_revalidate',side_effect=body),\
             patch.object(self.record,'_publish'),patch.object(self.dup,'_publish'):
            with self.assertRaisesRegex(ValueError,'no longer live'):self.session.revalidate()
        self.assertEqual(self.owner.state,'UNKNOWN_RETAINED')


if __name__=='__main__':unittest.main()
