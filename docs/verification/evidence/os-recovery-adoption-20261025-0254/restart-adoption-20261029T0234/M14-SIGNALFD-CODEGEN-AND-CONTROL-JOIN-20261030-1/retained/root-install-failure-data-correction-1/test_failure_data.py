"""Mocked functional failure-DATA tests; no root, signal, fork or cleanup."""
import contextlib
import importlib.util
import json
import pathlib
import stat
import sys
import types
import unittest
from unittest import mock


class EndHold(Exception):pass


def load_parent():
    ipc=types.ModuleType('parent_control')
    ipc.canonical=lambda x:(json.dumps(x,sort_keys=True,separators=(',',':'))+'\n').encode()
    ipc.remaining=lambda caps:100
    deferred=types.ModuleType('deferred_fork');deferred.DeferredFork=lambda:contextlib.nullcontext()
    names=('direct_entry','direct_completion','ownership_latch','pidfd_compat','caller_data_output')
    modules={name:types.ModuleType(name) for name in names};modules.update(parent_control=ipc,deferred_fork=deferred)
    with mock.patch.dict(sys.modules,modules):
        path=pathlib.Path(__file__).with_name('root_parent.proposal.py')
        spec=importlib.util.spec_from_file_location('failure_parent_fixture',str(path))
        parent=importlib.util.module_from_spec(spec);spec.loader.exec_module(parent)
    return parent


class FailureData(unittest.TestCase):
    def setUp(self):
        self.p=load_parent()
        self.st=types.SimpleNamespace(st_mode=stat.S_IFREG|0o600,st_nlink=1)
        self.root={'pid':111,'birth':'42'};self.keeper={'pid':112,'birth':'43'}

    @contextlib.contextmanager
    def sink(self,writer=None):
        p=self.p
        with contextlib.ExitStack() as stack:
            stack.enter_context(mock.patch.object(p.os,'fstat',return_value=self.st))
            stack.enter_context(mock.patch.object(p.fcntl,'fcntl',return_value=p.os.O_WRONLY))
            out=stack.enter_context(mock.patch.object(p.os,'write',side_effect=writer or (lambda fd,raw:len(raw))))
            fsync=stack.enter_context(mock.patch.object(p.os,'fsync'))
            yield out,fsync

    def test_exact_fixed_message_and_observed_identity(self):
        with self.sink() as (out,fsync):
            self.assertTrue(self.p._failure_note('keeper','child_entry',ValueError('actual admitted root owner and nonce required'),self.root,self.keeper))
        fd,raw=out.call_args.args;obj=json.loads(raw)
        self.assertEqual(fd,2);self.assertLessEqual(len(raw),4096)
        self.assertEqual(obj['error_class'],'ValueError')
        self.assertEqual(obj['error_message'],'actual admitted root owner and nonce required')
        self.assertEqual(obj['message_policy'],'exact_fixed')
        self.assertEqual(obj['root_parent'],self.root);self.assertEqual(obj['keeper'],self.keeper)
        self.assertEqual(obj['outcome'],'UNKNOWN');self.assertIsNone(obj['native_currentfree'])
        self.assertIs(obj['native_release'],False);fsync.assert_called_once_with(2)

    def test_arbitrary_exception_text_is_not_disclosed(self):
        secret='REQUEST_CONTENTS_MUST_NOT_APPEAR'
        with self.sink() as (out,fsync):
            self.assertTrue(self.p._failure_note('root_parent','lease_handoff',ValueError(secret),self.root,self.keeper))
        raw=out.call_args.args[1];self.assertNotIn(secret.encode(),raw)
        self.assertEqual(json.loads(raw)['message_policy'],'redacted')

    def test_short_write_is_single_attempt_and_not_flushed(self):
        with self.sink(writer=lambda fd,raw:len(raw)-1) as (out,fsync):
            self.assertFalse(self.p._failure_note('root_parent','go_handoff',ValueError('GO shape'),self.root,self.keeper))
        out.assert_called_once();fsync.assert_not_called()

    def test_serve_emits_failure_before_unknown_hold(self):
        p=self.p;events=[]
        result={'proof':{},'stdout_capture':{'device':1,'inode':2},
                'root_parent':self.root,'terminal_evidence':{'keeper':{'pid':112,'birth':'43'}}}
        latch=types.SimpleNamespace(retained=[],retain=mock.Mock(),fail=mock.Mock())
        def write(fd,raw):
            if fd==2:events.append(('failure',json.loads(raw)))
            return len(raw)
        def sleep(_):events.append(('hold',None));raise EndHold()
        with contextlib.ExitStack() as stack:
            stack.enter_context(mock.patch.object(p,'run',return_value=(result,latch,99,88)))
            stack.enter_context(mock.patch.object(p,'alarm_deferred',side_effect=contextlib.nullcontext))
            stack.enter_context(mock.patch.object(p,'lease_identity',return_value={'device':1,'inode':2}))
            stack.enter_context(mock.patch.object(p,'ensure_capture',side_effect=p.Unknown('capture before full')))
            stack.enter_context(mock.patch.object(p,'process',return_value={'pid':111,'birth':'42'}))
            stack.enter_context(mock.patch.object(p.os,'getpid',return_value=111))
            stack.enter_context(mock.patch.object(p.os,'open',return_value=71))
            stack.enter_context(mock.patch.object(p.os,'fstat',return_value=self.st))
            stack.enter_context(mock.patch.object(p.fcntl,'fcntl',return_value=p.os.O_WRONLY))
            stack.enter_context(mock.patch.object(p.os,'write',side_effect=write))
            stack.enter_context(mock.patch.object(p.os,'fsync'))
            stack.enter_context(mock.patch.object(p.signal,'setitimer'))
            stack.enter_context(mock.patch.object(p.time,'sleep',side_effect=sleep))
            with self.assertRaises(EndHold):
                p.serve(b'{"profile_sha256":"x"}',b'',b'',b'','a'*64,{},[])
        self.assertEqual([event[0] for event in events],['failure','hold'])
        self.assertEqual(events[0][1]['stage'],'full_handoff')
        self.assertEqual(events[0][1]['error_class'],'Unknown')
        self.assertEqual(events[0][1]['error_message'],'capture before full')
        self.assertEqual(events[0][1]['keeper'],self.keeper)
        latch.fail.assert_called_once()

if __name__=='__main__':unittest.main()
