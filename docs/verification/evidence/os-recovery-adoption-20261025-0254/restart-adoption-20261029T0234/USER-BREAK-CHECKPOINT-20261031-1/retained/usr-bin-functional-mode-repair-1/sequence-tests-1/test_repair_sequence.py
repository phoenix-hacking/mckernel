"""Functional-only repair sequence tests. UNRUN; all physical calls are mocked."""
import contextlib
import hashlib
import importlib.util
import json
import stat
import types
import unittest
from pathlib import Path
from unittest import mock

HERE=Path(__file__).parent
SOURCE=HERE.parent/'mode_repair.py'
EXPECTED_SHA='2d2dc33884f82deca9ad00b37d8d36e0298b282126110c0158e370ef9818287c'
raw=SOURCE.read_bytes()
if hashlib.sha256(raw).hexdigest()!=EXPECTED_SHA:raise ValueError('frozen repair source differs')
spec=importlib.util.spec_from_file_location('test_actual_mode_repair',str(SOURCE))
repair=importlib.util.module_from_spec(spec);spec.loader.exec_module(repair)


class RepairSequence(unittest.TestCase):
    def setUp(self):
        self.events=[];self.report=[];self.open_calls=[];self.held=[]
        self.capture=types.SimpleNamespace(st_mode=stat.S_IFREG|0o600,st_uid=1000,st_nlink=1,st_dev=8,st_ino=9)
        self.linked=types.SimpleNamespace(st_dev=66306,st_ino=1048578)
        self.mount=b'fixture fixed mount'
        self.root=self.row(0);self.usr=self.row(1);self.before=self.row(2)
        self.after=dict(self.before,mode=0o755,ctime_ns=self.before['ctime_ns']+1)
        self.obs=b'synthetic retained observation';self.review=b'synthetic independent review'
        self.release={'status':'REVIEWED_ONE_SHOT_FUNCTIONAL_MODE_REPAIR','scope':'USR_BIN_0777_TO_0755',
          'nonce':repair.NONCE,'observation_sha256':hashlib.sha256(self.obs).hexdigest(),
          'review_sha256':hashlib.sha256(self.review).hexdigest(),'controls_sha256':'a'*64,'capacity_sha256':'b'*64,
          'issued_boot_ns':1,'expires_boot_ns':2,'expires_mono_ns':3,'utc_cap_ns':4,
          'weekly_observed_utc_ns':5,'weekly_used_percent':95,'service_status':'NO_NEW_REJECTION',
          'mountns_device':1,'mountns_inode':2,'native_release':False,'native_currentfree':None,'reservation_release':False}
        self.rows=[self.root,self.usr,self.before,self.root,self.usr,self.before,
                   self.root,self.usr,self.after,self.after]
        self.records=[{'state':'OWNED','fd':20,'historical_fd':None},
                      {'state':'OWNED','fd':21,'historical_fd':None},
                      {'state':'OWNED','fd':22,'historical_fd':None},
                      {'state':'OWNED','fd':23,'historical_fd':None}]
    def row(self,index):
        path,ino,mode,mtime,ctime=repair.EXPECTED[index]
        return {'path':path,'device':repair.DEV,'inode':ino,'uid':0,'gid':0,'mode':mode,'mtime_ns':mtime,'ctime_ns':ctime}
    def write(self,fd,data):
        item=json.loads(data);self.events.append(('write',item['status']));self.report.append(item);return len(data)
    def fsync(self,fd):self.events.append(('fsync',fd))
    def opened(self,path,dir_fd=None):
        rec=self.records[len(self.open_calls)];self.open_calls.append((path,dir_fd,rec['fd']));return rec
    def run_case(self,fchmod=None,write=None,rows=None):
        observations=iter(self.rows if rows is None else rows)
        def chmod(fd,mode):
            self.events.append(('fchmod',fd,mode))
            if fchmod is not None:fchmod(fd,mode)
        def read(path,limit):return self.obs if str(path)==repair.OBSERVATION else self.review
        with contextlib.ExitStack() as stack:
            stack.enter_context(mock.patch.object(repair,'HELD',self.held))
            stack.enter_context(mock.patch.object(repair,'OBSERVATION_SHA',hashlib.sha256(self.obs).hexdigest()))
            stack.enter_context(mock.patch.object(repair,'root_session'))
            stack.enter_context(mock.patch.object(repair,'controls'))
            stack.enter_context(mock.patch.object(repair,'mount_table',return_value=self.mount))
            stack.enter_context(mock.patch.object(repair,'read_small',side_effect=read))
            stack.enter_context(mock.patch.object(repair,'open_owned',side_effect=self.opened))
            row=stack.enter_context(mock.patch.object(repair,'row',side_effect=lambda fd,path:next(observations)))
            stack.enter_context(mock.patch.object(repair.os,'getuid',return_value=0))
            stack.enter_context(mock.patch.object(repair.os,'geteuid',return_value=0))
            stack.enter_context(mock.patch.object(repair.os,'sched_getaffinity',return_value={6}))
            stack.enter_context(mock.patch.object(repair.os,'fstat',return_value=self.capture))
            stack.enter_context(mock.patch.object(repair.fcntl,'fcntl',return_value=repair.os.O_WRONLY))
            stack.enter_context(mock.patch.object(repair.os,'stat',return_value=self.linked))
            stack.enter_context(mock.patch.object(repair.os,'statvfs',return_value=types.SimpleNamespace(f_flag=0)))
            stack.enter_context(mock.patch.object(repair.signal,'pthread_sigmask',return_value=set()))
            stack.enter_context(mock.patch.object(repair.os,'fchmod',side_effect=chmod))
            stack.enter_context(mock.patch.object(repair.os,'fsync',side_effect=self.fsync))
            stack.enter_context(mock.patch.object(repair.os,'write',side_effect=write or self.write))
            stack.enter_context(mock.patch.object(repair.os,'close',side_effect=lambda fd:self.events.append(('close',fd))))
            repair.guarded_repair(object(),self.release,repair.sha(repair.canon(self.release)),8,9,'/fixture/review')
        return row
    def test_durable_before_single_exact_fchmod_and_separate_readback(self):
        row=self.run_case()
        before=self.events.index(('write','BEFORE_FCHMOD'))
        sync=self.events.index(('fsync',1),before+1)
        chmod=self.events.index(('fchmod',22,0o755))
        self.assertLess(before,sync);self.assertLess(sync,chmod)
        self.assertEqual([e for e in self.events if e[0]=='fchmod'],[('fchmod',22,0o755)])
        self.assertIn(mock.call(23,'/usr/bin'),row.call_args_list)
        self.assertEqual([r['status'] for r in self.report],['BEFORE_FCHMOD','FCHMOD_VERIFIED','MODE_REPAIR_COMPLETE_DESCRIPTORS_CLOSED'])
    def test_failed_precheck_never_calls_fchmod_and_reports_unknown(self):
        rows=[self.root,self.usr,dict(self.before,inode=99)]
        with self.assertRaises(ValueError):self.run_case(rows=rows)
        self.assertFalse(any(e[0]=='fchmod' for e in self.events))
        self.assertEqual(self.report[-1]['status'],'REPAIR_UNKNOWN')
    def test_fchmod_failure_is_one_attempt_and_unknown(self):
        def fail(fd,mode):raise OSError('synthetic failure')
        with self.assertRaises(OSError):self.run_case(fchmod=fail)
        self.assertEqual([e for e in self.events if e[0]=='fchmod'],[('fchmod',22,0o755)])
        self.assertEqual(self.report[-1]['status'],'REPAIR_UNKNOWN')
        self.assertIn('FCHMOD_UNKNOWN',self.report[-1]['states'])
    def test_postmutation_output_failure_never_retries_or_reports_success(self):
        def write(fd,data):
            item=json.loads(data)
            if item['status']=='FCHMOD_VERIFIED':raise OSError('synthetic capture failure')
            return self.write(fd,data)
        with self.assertRaises(OSError):self.run_case(write=write)
        self.assertEqual([e for e in self.events if e[0]=='fchmod'],[('fchmod',22,0o755)])
        self.assertEqual(self.report[-1]['status'],'REPAIR_UNKNOWN')
        self.assertIn('VERIFIED_0755',self.report[-1]['states'])
        self.assertFalse(any(r['status']=='MODE_REPAIR_COMPLETE_DESCRIPTORS_CLOSED' for r in self.report))


if __name__=='__main__':unittest.main()
