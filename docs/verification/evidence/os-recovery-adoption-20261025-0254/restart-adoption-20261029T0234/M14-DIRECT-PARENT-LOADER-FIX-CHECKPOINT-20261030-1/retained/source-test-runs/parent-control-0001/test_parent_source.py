"""Functional-only synthetic tests; UNRUN. No actual fork, pidfd or signals."""
import array
import contextlib
import importlib.util
import socket
import struct
import sys
import types
import unittest
from pathlib import Path
from unittest import mock

HERE=Path(__file__).parent


def load_protocol():
    module=types.ModuleType('deferred_fork')
    class Guard:
        def __enter__(self):return self
        def __exit__(self,*args):return False
    module.DeferredFork=Guard
    with mock.patch.dict(sys.modules,{'deferred_fork':module}):
        spec=importlib.util.spec_from_file_location('private_parent_control',HERE/'parent_control.py')
        result=importlib.util.module_from_spec(spec);spec.loader.exec_module(result)
    return result


class TestProtocol(unittest.TestCase):
    def setUp(self):self.mod=load_protocol()
    def mock_receive(self,raw,anc,flags=0,pid=123):
        sock=mock.Mock();sock.recvmsg.return_value=(raw,anc,flags,None)
        held=[]
        with mock.patch.object(self.mod,'wait'):
            return self.mod.receive(sock,{},held,pid),held
    def test_rights_and_kernel_credentials_retained(self):
        raw=self.mod.canonical({'nonce':'a','seq':1});fds=array.array('i',[41])
        anc=[(socket.SOL_SOCKET,socket.SCM_RIGHTS,fds.tobytes()),(socket.SOL_SOCKET,socket.SCM_CREDENTIALS,struct.pack('3i',123,0,0))]
        (message,received),held=self.mock_receive(raw,anc)
        self.assertEqual(message,{'nonce':'a','seq':1});self.assertEqual(received,[41]);self.assertEqual(held[0].fds,[41])
    def test_bad_peer_retains_received_fds(self):
        raw=self.mod.canonical({'nonce':'a'});fds=array.array('i',[42]);held=[]
        anc=[(socket.SOL_SOCKET,socket.SCM_RIGHTS,fds.tobytes()),(socket.SOL_SOCKET,socket.SCM_CREDENTIALS,struct.pack('3i',999,0,0))]
        sock=mock.Mock();sock.recvmsg.return_value=(raw,anc,0,None)
        with mock.patch.object(self.mod,'wait'),self.assertRaises(ValueError):self.mod.receive(sock,{},held,123)
        self.assertEqual(held[0].fds,[42])
    def test_truncated_ancillary_retained(self):
        raw=self.mod.canonical({'nonce':'a'});fds=array.array('i',[43]);held=[]
        anc=[(socket.SOL_SOCKET,socket.SCM_RIGHTS,fds.tobytes()),(socket.SOL_SOCKET,socket.SCM_CREDENTIALS,struct.pack('3i',123,0,0))]
        sock=mock.Mock();sock.recvmsg.return_value=(raw,anc,socket.MSG_CTRUNC,None)
        with mock.patch.object(self.mod,'wait'),self.assertRaises(ValueError):self.mod.receive(sock,{},held,123)
        self.assertEqual(held[0].fds,[43])
    def test_noncanonical_frame_fails(self):
        held=[];sock=mock.Mock();sock.recvmsg.return_value=(b'{ "x": 1 }\n',[(socket.SOL_SOCKET,socket.SCM_CREDENTIALS,struct.pack('3i',123,0,0))],0,None)
        with mock.patch.object(self.mod,'wait'),self.assertRaises(ValueError):self.mod.receive(sock,{},held,123)
    def test_stop_at_receive_restore_preserves_owned_record(self):
        held=[];sock=mock.Mock();fds=array.array('i',[44])
        sock.recvmsg.return_value=(self.mod.canonical({'seq':1}),[(socket.SOL_SOCKET,socket.SCM_RIGHTS,fds.tobytes()),(socket.SOL_SOCKET,socket.SCM_CREDENTIALS,struct.pack('3i',123,0,0))],0,None)
        class StopGuard:
            def __enter__(self):return self
            def __exit__(self,*args):raise InterruptedError('deferred stop')
        with mock.patch.object(self.mod,'wait'),mock.patch.object(self.mod.deferred_fork,'DeferredFork',StopGuard),self.assertRaises(InterruptedError):self.mod.receive(sock,{},held,123)
        self.assertEqual(held[0].fds,[44])


def load_parent():
    protocol=load_protocol()
    modules={name:types.ModuleType(name) for name in ('deferred_fork','direct_entry','direct_completion','ownership_latch','pidfd_compat')}
    modules['parent_control']=protocol
    class Guard:
        def __enter__(self):return self
        def __exit__(self,*args):return False
    modules['deferred_fork'].DeferredFork=Guard
    modules['direct_completion'].verify_parent_retirement_authority=lambda *_:True
    with mock.patch.dict(sys.modules,modules):
        spec=importlib.util.spec_from_file_location('private_root_parent',HERE/'root_parent.py')
        result=importlib.util.module_from_spec(spec);spec.loader.exec_module(result)
    return result


class TestRetirement(unittest.TestCase):
    def setUp(self):
        self.mod=load_parent();self.latch=mock.Mock();self.events=[]
        self.owner=self.mod.ipc.ReceivedCustody();self.owner.fds=[55];self.latch.retained=[self.owner]
        self.result={'status':'INSTALL_ONLY_COMPLETE_PENDING_UID1000_READ','proof':{'source':'actual-fixture'}}
    def run_serve(self,close):
        with mock.patch.object(self.mod,'run',return_value=(self.result,self.latch,55,56)), \
             mock.patch.object(self.mod,'lease_identity',return_value={'device':3,'inode':4}), \
             mock.patch.object(self.mod.ipc,'remaining',return_value=1000000), \
             mock.patch.object(self.mod.os,'open',return_value=57), \
             mock.patch.object(self.mod.os,'write',side_effect=lambda fd,data:len(data)), \
             mock.patch.object(self.mod.os,'fsync'),mock.patch.object(self.mod.os,'close',side_effect=close), \
             mock.patch.object(self.mod,'alarm_deferred',side_effect=contextlib.nullcontext),mock.patch.object(self.mod.signal,'setitimer'), \
             mock.patch.object(self.mod.time,'sleep',side_effect=SystemExit('held for fixture')):
            return self.mod.serve(b'a','x',b'b','y','f'*64,{},[])
    def test_confirmed_close_only_once(self):
        output=self.run_serve(lambda fd:self.events.append(fd))
        self.assertEqual(self.events,[55]);self.assertEqual(output['lease_disposition'],'VERIFIED_CLOSED');self.assertEqual(self.owner.fds,[None]);self.assertEqual(self.owner.state,'VERIFIED_CLOSED')
    def test_uncertain_close_is_never_retried(self):
        def uncertain(fd):self.events.append(fd);raise InterruptedError('close uncertain')
        with self.assertRaises(SystemExit):self.run_serve(uncertain)
        self.assertEqual(self.events,[55]);self.latch.fail.assert_called_once();self.assertEqual(self.owner.fds,[None]);self.assertEqual(self.owner.state,'CLOSURE_UNKNOWN')


if __name__=='__main__':unittest.main()
