"""Functional source-only parent handoff mocks. UNRUN; no real root/FD effects."""
import contextlib
import importlib.util
import json
import signal
import stat
import sys
import threading
import types
import unittest
from pathlib import Path
from unittest import mock

HERE=Path(__file__).parent


def load_parent():
    modules={name:types.ModuleType(name) for name in ('deferred_fork','direct_entry','direct_completion','ownership_latch','parent_control','pidfd_compat','caller_data_output')}
    class Guard:
        def __enter__(self):return self
        def __exit__(self,*args):return False
    class ReceivedCustody:
        def __init__(self):self.state='RECEIVED_RETAINED';self.fds=[55]
    modules['deferred_fork'].DeferredFork=Guard
    modules['parent_control'].ReceivedCustody=ReceivedCustody
    modules['parent_control'].remaining=lambda _:1000000000
    modules['parent_control'].canonical=lambda value:(json.dumps(value,sort_keys=True,separators=(',',':'))+'\n').encode()
    modules['direct_completion'].verify_parent_retirement_authority=lambda *_:True
    modules['caller_data_output'].publish_full=lambda *_:'f'*64
    modules['caller_data_output'].publish_disposition=lambda *_:None
    with mock.patch.dict(sys.modules,modules):
        spec=importlib.util.spec_from_file_location('test_parent4',HERE/'root_parent.py')
        parent=importlib.util.module_from_spec(spec);spec.loader.exec_module(parent)
    return parent


class Handoff(unittest.TestCase):
    def setUp(self):
        self.p=load_parent();self.owner=self.p.ipc.ReceivedCustody()
        self.latch=mock.Mock();self.latch.lock=threading.RLock();self.latch.retained=[self.owner]
        self.result={'proof':{'synthetic':True},'stdout_capture':{'device':8,'inode':9}}
        self.admission=json.dumps({'profile_sha256':'d'*64}).encode()
        self.order=[]
    def execute(self,full,close,disposition,fsync=None):
        with contextlib.ExitStack() as stack:
            stack.enter_context(mock.patch.object(self.p,'run',return_value=(self.result,self.latch,55,56)))
            stack.enter_context(mock.patch.object(self.p,'alarm_deferred',side_effect=contextlib.nullcontext))
            stack.enter_context(mock.patch.object(self.p,'lease_identity',return_value={'device':3,'inode':4}))
            stack.enter_context(mock.patch.object(self.p,'ensure_capture',return_value={'device':8,'inode':9}))
            stack.enter_context(mock.patch.object(self.p.caller_data_output,'publish_full',side_effect=full))
            stack.enter_context(mock.patch.object(self.p.caller_data_output,'publish_disposition',side_effect=disposition))
            stack.enter_context(mock.patch.object(self.p.os,'open',return_value=57))
            stack.enter_context(mock.patch.object(self.p.os,'write',side_effect=lambda fd,data:len(data)))
            stack.enter_context(mock.patch.object(self.p.os,'fsync',side_effect=fsync))
            stack.enter_context(mock.patch.object(self.p.os,'close',side_effect=close))
            stack.enter_context(mock.patch.object(self.p.signal,'setitimer'))
            stack.enter_context(mock.patch.object(self.p.time,'sleep',side_effect=SystemExit('synthetic retained'))) 
            return self.p.serve(self.admission,'a',b'review','b','a'*64,{},[])
    def test_full_before_single_close_then_final(self):
        def full(*args):self.order.append('full');return 'f'*64
        def close(fd):self.order.append(('close',fd))
        def final(*args):self.order.append(('final',args[3],args[4]))
        result=self.execute(full,close,final)
        self.assertEqual(self.order,['full',('close',55),('final','VERIFIED_CLOSED','COMPLETE')])
        self.assertEqual(result['lease_disposition'],'VERIFIED_CLOSED');self.assertEqual(self.owner.fds,[None])
    def test_full_failure_never_closes(self):
        def full(*args):raise OSError('short full')
        with self.assertRaises(SystemExit):self.execute(full,lambda fd:self.order.append(fd),lambda *args:None)
        self.assertEqual(self.order,[]);self.assertEqual(self.owner.fds,[55]);self.latch.fail.assert_called_once()
    def test_uncertain_close_never_retried_and_unknown_reported(self):
        def close(fd):self.order.append(fd);raise InterruptedError('ambiguous close')
        def final(*args):self.order.append((args[3],args[4]))
        with self.assertRaises(SystemExit):self.execute(lambda *_:'f'*64,close,final)
        self.assertEqual(self.order,[55,('CLOSURE_UNKNOWN','UNKNOWN')]);self.assertEqual(self.owner.fds,[None])
    def test_postclose_journal_failure_reports_known_closed_unknown(self):
        def close(fd):self.order.append(('close',fd))
        def final(*args):self.order.append(('final',args[3],args[4]))
        calls=[]
        def fsync(fd):
            calls.append(fd)
            if len(calls)==3:raise OSError('postclose journal failed')
        with self.assertRaises(SystemExit):self.execute(lambda *_:'f'*64,close,final,fsync)
        self.assertEqual(self.order,[('close',55),('final','VERIFIED_CLOSED','UNKNOWN')])
        self.assertEqual(self.owner.state,'VERIFIED_CLOSED')
    def test_final_failure_does_not_retry_or_reclose(self):
        def close(fd):self.order.append(('close',fd))
        def final(*args):self.order.append('final');raise OSError('partial final')
        with self.assertRaises(SystemExit):self.execute(lambda *_:'f'*64,close,final)
        self.assertEqual(self.order,[('close',55),'final']);self.assertEqual(self.owner.state,'VERIFIED_CLOSED')


class EarlyCapture(unittest.TestCase):
    def setUp(self):
        spec=importlib.util.spec_from_file_location('test_parent4_bootstrap',HERE/'BOOTSTRAP.py')
        self.bootstrap=importlib.util.module_from_spec(spec);spec.loader.exec_module(self.bootstrap)
    def reject(self,mode,device,inode):
        actual=types.SimpleNamespace(st_mode=mode,st_uid=1000,st_nlink=1,st_dev=device,st_ino=inode)
        with contextlib.ExitStack() as stack:
            stack.enter_context(mock.patch.object(self.bootstrap.sys,'argv',['boot','a'*64,'/review','b'*64,'8','9']))
            stack.enter_context(mock.patch.object(self.bootstrap.os,'getuid',return_value=0))
            stack.enter_context(mock.patch.object(self.bootstrap.os,'geteuid',return_value=0))
            stack.enter_context(mock.patch.object(self.bootstrap.os,'fstat',return_value=actual))
            stack.enter_context(mock.patch.object(self.bootstrap.fcntl,'fcntl',return_value=self.bootstrap.os.O_WRONLY))
            read=stack.enter_context(mock.patch.object(self.bootstrap,'read_fd'))
            with self.assertRaises(ValueError):self.bootstrap.main()
            read.assert_not_called()
    def test_pipe_is_rejected_before_any_input_or_fork(self):
        self.reject(stat.S_IFIFO|0o600,8,9)
    def test_wrong_capture_inode_rejected_before_any_input_or_fork(self):
        self.reject(stat.S_IFREG|0o600,8,10)


if __name__=='__main__':unittest.main()
