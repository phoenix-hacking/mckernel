"""Functional-only synthetic successful and UNKNOWN completion fixtures. UNRUN."""
import io
import json
import os
import select
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch
base=Path(__file__).resolve().parent;sys.path.insert(0,str(base/'package'))
import install_completion as subject
import install_issuer
from ownership_latch import CustodyLatch


class MonitorCases(unittest.TestCase):
    def test_positive_timer_wait_and_independent_installer_terminal(self):
        class Poll:
            def register(self,*args):pass
            def unregister(self,*args):pass
            def poll(self,*args):return [(71,select.POLLIN),(72,select.POLLIN)]
        latch=CustodyLatch('KEEPER_HELD')
        with patch.object(install_issuer.select,'poll',return_value=Poll()),\
             patch.object(subject,'remaining',return_value=100),\
             patch.object(install_issuer.os,'waitpid',side_effect=[(50,0),ChildProcessError()]):
            result=install_issuer.monitor_owned(latch,object(),9,50,71,60,72,{},10)
        self.assertEqual(result['timer_direct_wait_status'],0)
        self.assertTrue(result['installer_pidfd_terminal']);self.assertIsNone(result['installer_direct_wait_status'])
    def test_nonzero_timer_never_completes(self):
        class Poll:
            def register(self,*args):pass
            def unregister(self,*args):pass
            def poll(self,*args):return [(71,select.POLLIN),(72,select.POLLIN)]
        latch=CustodyLatch('KEEPER_HELD')
        with patch.object(install_issuer.select,'poll',return_value=Poll()),\
             patch.object(subject,'remaining',return_value=100),\
             patch.object(install_issuer.os,'waitpid',side_effect=[(50,256),ChildProcessError()]):
            with self.assertRaises(install_issuer.IssuerUnknown):
                install_issuer.monitor_owned(latch,object(),9,50,71,60,72,{},10)


class TimeoutReserveCases(unittest.TestCase):
    def test_expired_or_reversed_timer_cannot_release_go(self):
        self.assertEqual(install_issuer.remaining_timeout_budget(10,59000000010),6000000000)
        with self.assertRaises(TimeoutError):install_issuer.remaining_timeout_budget(10,60000000010)
        with self.assertRaises(ValueError):install_issuer.remaining_timeout_budget(10,9)


class WriterJournalCases(unittest.TestCase):
    def test_writer_close_record_required_before_immutable_completion(self):
        ident={'device':1,'inode':2};row={'name':'a.py','sha256':'a'*64}
        events=[{'state':'BEFORE_CREATE','name':'a.py','sha256':'a'*64},
          {'state':'BEFORE_WRITER_CLOSE','name':'a.py','identity':ident},
          {'state':'WRITER_CLOSED','name':'a.py','identity':ident},
          {'state':'BEFORE_IMMUTABLE','name':'a.py','identity':ident},
          {'state':'FILE_HELD','name':'a.py','identity':ident,'sha256':'a'*64}]
        self.assertEqual(subject.verify_writer_sequence(events,row)['identity'],ident)
        with self.assertRaises(ValueError):subject.verify_writer_sequence(events[:2]+events[3:],row)
        changed=[dict(event) for event in events];changed[2]['identity']={'device':1,'inode':99}
        with self.assertRaises(ValueError):subject.verify_writer_sequence(changed,row)


class CensusCases(unittest.TestCase):
    def record(self,pid,parent,group):
        return ('%d (fixture) '%pid+' '.join(['S',str(parent),str(group)]+['0']*17)+'\n').encode()
    def test_empty_private_group_and_no_keeper_descendants(self):
        with tempfile.TemporaryDirectory() as path:
            for pid,parent,group in ((1,0,1),(100,1,10),(300,1,30)):
                directory=Path(path)/str(pid);directory.mkdir();(directory/'stat').write_bytes(self.record(pid,parent,group))
            fd=os.open(path,os.O_RDONLY|os.O_DIRECTORY)
            try:
                with patch.object(subject,'verify_proc_scope'),patch.object(subject,'need_time'):
                    result=subject.census_empty(fd,{},100,200,{})
                self.assertTrue(result['private_group_empty']);self.assertTrue(result['keeper_descendants_empty'])
            finally:os.close(fd)
    def test_adopted_descendant_or_group_member_prevents_completion(self):
        with tempfile.TemporaryDirectory() as path:
            for pid,parent,group in ((1,0,1),(100,1,10),(200,100,200)):
                directory=Path(path)/str(pid);directory.mkdir();(directory/'stat').write_bytes(self.record(pid,parent,group))
            fd=os.open(path,os.O_RDONLY|os.O_DIRECTORY)
            try:
                with patch.object(subject,'verify_proc_scope'),patch.object(subject,'need_time'):
                    with self.assertRaises(ValueError):subject.census_empty(fd,{},100,200,{})
            finally:os.close(fd)


class RetirementCases(unittest.TestCase):
    def authority(self):
        return {'record_type':'ROOT_INSTALL_OPERATION_RETIREMENT_V1','scope':'ROOT_CODE_INSTALL_ONLY',
                'nonce':'a'*64,'native_release':False,'status':'APPROVED_IF_VERIFIED','review_sha256':'b'*64}
    def complete(self):
        return {'status':'INSTALL_ONLY_COMPLETE_PENDING_UID1000_READ','nonce':'a'*64,'native_release':False,'native_currentfree':None,
                'terminals':{'timer_direct_wait_status':0,'installer_pidfd_terminal':True,'installer_direct_wait_status':None},
                'census':{'private_group_empty':True,'keeper_descendants_empty':True},
                'install_proof':{'files':[{}]*23},'captures':[{'writer_closed':True},{'writer_closed':True}]}
    def test_authorized_verified_retirement_closes_exact_owned_fd(self):
        import hashlib
        raw=json.dumps(self.authority()).encode();digest=hashlib.sha256(raw).hexdigest();events=[]
        install=types.SimpleNamespace(MAX_SOURCE=1024,root_file=lambda fd:None,read_stable=lambda fd,limit:raw,
          sha=lambda data:hashlib.sha256(data).hexdigest(),unique=lambda pairs:dict(pairs),hex64=lambda s:type(s) is str and len(s)==64,
          journal=lambda fd,event:events.append(event['state']))
        latch=CustodyLatch('HELD');latch.retain(41);record=latch.reserve_child('timer',41)
        release={'retire_operation_only':True,'owner_release_sha256':digest,'nonce':'a'*64}
        with patch.object(subject,'need_time'),patch('signal.pthread_sigmask',return_value=set()),patch.object(subject.os,'close') as close:
            self.assertTrue(subject.retire_lease_if_authorized(install,latch,record,9,41,8,release,self.complete()))
        close.assert_called_once_with(41);self.assertEqual(events,['BEFORE_OWNED_LEASE_CLOSE','OWNED_LEASE_FD_CLOSED'])
        self.assertNotIn(41,latch.retained);self.assertNotIn(41,record.handles)
    def test_missing_group_proof_cannot_close_owned_fd(self):
        import hashlib
        raw=json.dumps(self.authority()).encode();digest=hashlib.sha256(raw).hexdigest();install=types.SimpleNamespace(MAX_SOURCE=1024,root_file=lambda fd:None,read_stable=lambda fd,limit:raw,sha=lambda data:hashlib.sha256(data).hexdigest(),unique=lambda pairs:dict(pairs),hex64=lambda s:True)
        latch=CustodyLatch('HELD');latch.retain(41);record=latch.reserve_child('timer',41)
        release={'retire_operation_only':True,'owner_release_sha256':digest,'nonce':'a'*64};complete=self.complete();complete['census']['private_group_empty']=False
        with patch.object(subject.os,'close') as close:
            with self.assertRaises(ValueError):subject.retire_lease_if_authorized(install,latch,record,9,41,8,release,complete)
        close.assert_not_called();self.assertIn(41,latch.retained)

if __name__=='__main__':unittest.main()
