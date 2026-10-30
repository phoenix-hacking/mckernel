"""Mocked parent proposal ordering; no real root/FD mutation or signals."""
import contextlib
import importlib.util
import json
import pathlib
import sys
import types
import unittest
from unittest import mock


class EndHeld(Exception):pass


class ReceivedCustody:
    def __init__(self,fd):self.fds=[fd];self.state='OWNED'


def load_parent():
    ipc=types.ModuleType('parent_control')
    ipc.ReceivedCustody=ReceivedCustody
    ipc.canonical=lambda x:(json.dumps(x,sort_keys=True,separators=(',',':'))+'\n').encode()
    ipc.unique=lambda pairs:dict(pairs)
    ipc.remaining=lambda caps:100
    direct=types.ModuleType('direct_completion');direct.verify_parent_retirement_authority=mock.Mock(return_value=True)
    out=types.ModuleType('data_output');out.publish_full=mock.Mock(return_value='c'*64);out.publish_disposition=mock.Mock(return_value='d'*64)
    deferred=types.ModuleType('deferred_fork');deferred.DeferredFork=lambda:contextlib.nullcontext()
    modules={'parent_control':ipc,'direct_completion':direct,'data_output':out,'deferred_fork':deferred,
             'direct_entry':types.ModuleType('direct_entry'),'ownership_latch':types.ModuleType('ownership_latch'),
             'pidfd_compat':types.ModuleType('pidfd_compat')}
    with mock.patch.dict(sys.modules,modules):
        path=pathlib.Path(__file__).with_name('root_parent.proposal.py')
        spec=importlib.util.spec_from_file_location('parent_data_proposal',str(path))
        parent=importlib.util.module_from_spec(spec);spec.loader.exec_module(parent)
    return parent,out,direct


class ParentDataOrder(unittest.TestCase):
    def setUp(self):
        self.parent,self.out,self.direct=load_parent()
        self.owner=ReceivedCustody(99)
        self.latch=types.SimpleNamespace(retained=[self.owner],retain=mock.Mock(),fail=mock.Mock())
        self.result={'proof':{'nonce':'a'*64},'lease_disposition':'HELD'}
        self.admission=json.dumps({'profile_sha256':'b'*64,'retire_operation_only':True}).encode()
        self.caps={'boot_ns':10,'mono_ns':10,'utc_ns':10}

    @contextlib.contextmanager
    def environment(self,fsync_effect=None):
        p=self.parent
        with contextlib.ExitStack() as stack:
            stack.enter_context(mock.patch.object(p,'run',return_value=(self.result,self.latch,99,88)))
            stack.enter_context(mock.patch.object(p,'alarm_deferred',side_effect=contextlib.nullcontext))
            stack.enter_context(mock.patch.object(p,'lease_identity',return_value={'device':1,'inode':2}))
            stack.enter_context(mock.patch.object(p.os,'open',return_value=71))
            stack.enter_context(mock.patch.object(p.os,'write',side_effect=lambda fd,data:len(data)))
            stack.enter_context(mock.patch.object(p.os,'fsync',side_effect=fsync_effect))
            close=stack.enter_context(mock.patch.object(p.os,'close'))
            stack.enter_context(mock.patch.object(p.signal,'setitimer'))
            stack.enter_context(mock.patch.object(p.time,'sleep',side_effect=EndHeld))
            yield close

    def call(self):
        self.parent.serve(self.admission,'x',b'review','y','a'*64,self.caps,[1,2,3,4,5,6])

    def test_failed_full_handoff_never_closes_lease(self):
        self.out.publish_full.side_effect=OSError('short DATA write')
        with self.environment() as close:
            with self.assertRaises(EndHeld):self.call()
        close.assert_not_called()
        self.direct.verify_parent_retirement_authority.assert_not_called()
        self.out.publish_disposition.assert_not_called()
        self.latch.fail.assert_called_once()

    def test_postclose_journal_failure_reports_closed_unknown_without_retry(self):
        with self.environment(fsync_effect=[None,None,OSError('postclose journal fsync')]) as close:
            with self.assertRaises(EndHeld):self.call()
        close.assert_called_once_with(99)
        self.assertEqual(self.owner.state,'VERIFIED_CLOSED')
        self.out.publish_disposition.assert_called_once_with('a'*64,'b'*64,'c'*64,'VERIFIED_CLOSED','UNKNOWN',self.caps)
        self.latch.fail.assert_called_once()

if __name__=='__main__':unittest.main()
