"""Functional-only synthetic tests; UNRUN. No actual fork, pidfd or signals."""
import array
import ast
import fcntl
import threading
import contextlib
import importlib.util
import hashlib
import json
import socket
import struct
import sys
import types
import unittest
from pathlib import Path
from unittest import mock

HERE=Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261026-1/WEEKLY-ONLY-20261029-1/DISPATCHER-MAX-PREFERRED-20261030-1/root-install-parent-successor-2')


def load_protocol():
    module=types.ModuleType('deferred_fork')
    class Guard:
        def __enter__(self):return self
        def __exit__(self,*args):return False
    module.DeferredFork=Guard
    with mock.patch.dict(sys.modules,{'deferred_fork':module}):
        spec=importlib.util.spec_from_file_location('private_parent_control',HERE.parent/'root-install-parent-successor-1'/'parent_control.py')
        result=importlib.util.module_from_spec(spec);spec.loader.exec_module(result)
    return result


class TestProfile(unittest.TestCase):
    def test_exact_argument_positions_and_pinned_source(self):
        profile=json.loads((HERE/'PROFILE.SOURCE-ONLY.json').read_text());argv=profile['argv']
        literal=(HERE/'BOOTSTRAP.py').read_text()
        self.assertEqual(len(argv),20);self.assertEqual(argv[4],'6');self.assertEqual(argv[15],'-c')
        self.assertEqual(argv[16],literal)
        self.assertEqual(hashlib.sha256(literal.encode()).hexdigest(),profile['bootsource_sha256'])
        self.assertEqual(argv[17:],['<FRESH_ADMISSION_SHA256>','<REVIEWED_SOURCE_REVIEW_PATH>','<REVIEWED_SOURCE_REVIEW_SHA256>'])
        self.assertNotIn('/usr/bin/timeout',argv)


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
    class FakePidfdVerificationError(Exception):pass
    modules['pidfd_compat'].PidfdVerificationError=FakePidfdVerificationError
    class FakeChildRecord:pass
    modules['ownership_latch'].ChildRecord=FakeChildRecord
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
    def test_exact_frame_rejects_bool_and_float_aliases(self):
        for value in (True,1.0):
            with self.assertRaises(ValueError):self.mod.exact({'seq':value},{'seq':1})
    def test_confirmed_close_only_once(self):
        output=self.run_serve(lambda fd:self.events.append(fd))
        self.assertEqual(self.events,[55]);self.assertEqual(output['lease_disposition'],'VERIFIED_CLOSED');self.assertEqual(self.owner.fds,[None]);self.assertEqual(self.owner.state,'VERIFIED_CLOSED')
    def test_uncertain_close_is_never_retried(self):
        def uncertain(fd):self.events.append(fd);raise InterruptedError('close uncertain')
        with self.assertRaises(SystemExit):self.run_serve(uncertain)
        self.assertEqual(self.events,[55]);self.latch.fail.assert_called_once();self.assertEqual(self.owner.fds,[None]);self.assertEqual(self.owner.state,'CLOSURE_UNKNOWN')


class TestRecovery(unittest.TestCase):
    def setUp(self):
        self.mod=load_parent();self.latch=mock.Mock();self.latch.lock=threading.RLock()
        self.record=self.mod.ownership_latch.ChildRecord()
        self.record.latch=self.latch;self.record.pid=321;self.record.pidfd=58
        self.record.birth=None;self.record.status='UNKNOWN_RETAINED';self.latch.children={'keeper':self.record}
        self.row={'pid':321,'parent':777,'pgrp':777,'birth':'12345'}
    def check(self,error):
        with mock.patch.object(self.mod,'process',return_value=self.row), \
             mock.patch.object(self.mod.os,'getpid',return_value=777), \
             mock.patch.object(self.mod.os,'readlink',return_value='anon_inode:[pidfd]'), \
             mock.patch.object(self.mod.fcntl,'fcntl',side_effect=[fcntl.FD_CLOEXEC,0]), \
             mock.patch.object(self.mod,'pidfd_pid',return_value=321):
            return self.mod.retained_keeper_target(self.latch,self.record,error,None,None)
    def test_recorded_pidfd_birth_read_failure_can_be_reverified(self):
        self.assertEqual(self.check(ValueError('birth read failed')),(321,58))
        self.assertEqual(self.record.status,'UNKNOWN_RETAINED')
        self.assertEqual(self.record.failure_observation,self.row)
    def test_pidfd_verification_error_never_signalled(self):
        self.assertEqual(self.check(self.mod.pidfd_compat.PidfdVerificationError()),(None,None))
        self.assertFalse(hasattr(self.record,'failure_observation'))
    def test_pidfd_wrong_identity_never_signalled(self):
        with mock.patch.object(self.mod,'process',return_value=self.row), \
             mock.patch.object(self.mod.os,'getpid',return_value=777), \
             mock.patch.object(self.mod.os,'readlink',return_value='anon_inode:[pidfd]'), \
             mock.patch.object(self.mod.fcntl,'fcntl',side_effect=[fcntl.FD_CLOEXEC,0]), \
             mock.patch.object(self.mod,'pidfd_pid',return_value=322):
            self.assertEqual(self.mod.retained_keeper_target(self.latch,self.record,ValueError(),None,None),(None,None))
    def test_fork_error_actual_failure_path_stops_recorded_handle(self):
        self.latch.retained=[]
        self.latch.reserve_child.return_value=self.record
        self.mod.ownership_latch.CustodyLatch=lambda _:self.latch
        class Guard:
            def __enter__(self):return self
            def __exit__(self,*args):return False
            def fork_and_pin(self,record,callback):raise ValueError('birth read failed')
        sock1=mock.Mock();sock2=mock.Mock();stops=[]
        self.mod.direct_completion.set_subreaper=lambda:None
        with contextlib.ExitStack() as fixture_stack:
            fixture_stack.enter_context(mock.patch.object(self.mod.os,'getuid',return_value=0))
            fixture_stack.enter_context(mock.patch.object(self.mod.os,'geteuid',return_value=0))
            fixture_stack.enter_context(mock.patch.object(self.mod.threading,'active_count',return_value=1))
            fixture_stack.enter_context(mock.patch.object(self.mod.signal,'getitimer',return_value=(0.0,0.0)))
            fixture_stack.enter_context(mock.patch.object(self.mod.signal,'pthread_sigmask',return_value=set()))
            fixture_stack.enter_context(mock.patch.object(self.mod.signal,'signal'))
            fixture_stack.enter_context(mock.patch.object(self.mod.signal,'setitimer'))
            fixture_stack.enter_context(mock.patch.object(self.mod.os,'getpid',return_value=777))
            fixture_stack.enter_context(mock.patch.object(self.mod.os,'readlink',return_value='anon_inode:[pidfd]'))
            fixture_stack.enter_context(mock.patch.object(self.mod.fcntl,'fcntl',side_effect=[fcntl.FD_CLOEXEC,0]))
            fixture_stack.enter_context(mock.patch.object(self.mod,'pidfd_pid',return_value=321))
            fixture_stack.enter_context(mock.patch.object(self.mod,'process',side_effect=[{'pid':777,'parent':1,'pgrp':777,'birth':'9'},self.row,self.row]))
            fixture_stack.enter_context(mock.patch.object(self.mod.socket,'socketpair',return_value=(sock1,sock2)))
            fixture_stack.enter_context(mock.patch.object(self.mod,'alarm_deferred',side_effect=contextlib.nullcontext))
            fixture_stack.enter_context(mock.patch.object(self.mod.deferred_fork,'DeferredFork',Guard))
            fixture_stack.enter_context(mock.patch.object(self.mod.ipc,'remaining',return_value=100000000000))
            fixture_stack.enter_context(mock.patch.object(self.mod.time,'clock_gettime_ns',side_effect=[100,200,6000000200]))
            fixture_stack.enter_context(mock.patch.object(self.mod.time,'monotonic_ns',return_value=100))
            fixture_stack.enter_context(mock.patch.object(self.mod.time,'time_ns',return_value=100))
            fixture_stack.enter_context(mock.patch.object(self.mod,'stop_owned',side_effect=lambda fds,sig:stops.append((list(fds),sig))))
            waited = fixture_stack.enter_context(mock.patch.object(self.mod,'wait_known'))
            fixture_stack.enter_context(mock.patch.object(self.mod.time,'sleep',side_effect=SystemExit('held for fixture')))
            with self.assertRaises(SystemExit):
                self.mod.run(b'a',hashlib.sha256(b'a').hexdigest(),b'b',hashlib.sha256(b'b').hexdigest(),
                             'a'*64,{'boot_ns':100000000000,'mono_ns':100000000000,'utc_ns':100000000000},[1+v for v in range(1,7)])
        self.assertEqual(stops,[( [None,58],self.mod.signal.SIGTERM),([None,58],self.mod.signal.SIGKILL)])
        waited.assert_called_once_with(321,58)


class TestBootstrapBytes(unittest.TestCase):
    def test_actual_final_serialization_expression(self):
        tree=ast.parse((HERE/'BOOTSTRAP.py').read_text())
        main=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='main')
        assignments=[n for n in main.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='raw' for t in n.targets)]
        self.assertEqual(len(assignments),1)
        actual=eval(compile(ast.Expression(assignments[0].value),str(HERE/'BOOTSTRAP.py'),'eval'),{'json':json,'result':{'z':False,'a':7}})
        self.assertEqual(actual,b'{"a":7,"z":false}\n')
        self.assertNotIn(b'\\n',actual)


if __name__=='__main__':unittest.main()
