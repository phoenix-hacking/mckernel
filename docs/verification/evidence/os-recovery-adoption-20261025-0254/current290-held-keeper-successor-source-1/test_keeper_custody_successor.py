"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Private owned file/process fixtures only. No production custody acquisition.
"""
import ctypes
import errno
import fcntl
import json
import os
from pathlib import Path
import select
import tempfile
import unittest
from unittest import mock
import keeper_custody_successor as s

class PrivateCustody(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory(prefix='private-successor-',dir=Path(__file__).parent)
  self.path=Path(self.tmp.name)/'fixture-only.lock';self.path.touch(mode=0o600)
  self.origin=os.getpid();self.fd=os.open(self.path,os.O_RDONLY|os.O_CLOEXEC)
  fcntl.flock(self.fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
  self.copy=os.dup(self.fd);self.meta=s.metadata(os.fstat(self.fd))
  self.pipe_r,self.pipe_w=os.pipe(); ready_r,ready_w=os.pipe()
  self.pid=os.fork()
  if self.pid==0:
   os.close(self.pipe_w);os.close(ready_r);os.close(self.copy)
   os.write(ready_w,b'R');os.close(ready_w)
   select.select([self.pipe_r],[],[],10);os.read(self.pipe_r,1)
   os.close(self.fd);os.close(self.pipe_r);os._exit(0)
  os.close(self.pipe_r);os.close(ready_w)
  self.assertTrue(select.select([ready_r],[],[],5)[0]);self.assertEqual(os.read(ready_r,1),b'R');os.close(ready_r)
  libc=ctypes.CDLL(None,use_errno=True);libc.syscall.restype=ctypes.c_long
  self.pidfd=libc.syscall(ctypes.c_long(434),ctypes.c_int(self.pid),ctypes.c_uint(0));self.joined=False
  if self.pidfd<0:
   os.close(self.pipe_w);self.pipe_w=None;os.waitpid(self.pid,0);self.joined=True
   raise OSError(ctypes.get_errno(),'private-pidfd-open')
 def tearDown(self):
  if self.pipe_w is not None:os.close(self.pipe_w)
  if not self.joined:os.waitpid(self.pid,0)
  for fd in (self.pidfd,self.copy,self.fd):os.close(fd)
  self.tmp.cleanup()
 def check(self,**replace):
  args=dict(fd=self.copy,holder_pid=self.pid,holder_fd=self.fd,path=self.path,expected_metadata=self.meta,lock_origin_pid=self.origin);args.update(replace)
  return s.verify_custody(**args)
 def test_current_holder_distinct_from_original_lock_origin(self):
  proof=self.check();self.assertEqual(proof['holder_pid'],self.pid);self.assertEqual(proof['lock_origin_pid'],self.origin);self.assertFalse(proof['retirement_authority'])
 def test_wrong_lock_origin_refused(self):
  with self.assertRaisesRegex(ValueError,'original-origin'):self.check(lock_origin_pid=self.pid)
 def test_independent_reopen_same_inode_refused(self):
  fd=os.open(self.path,os.O_RDONLY|os.O_CLOEXEC)
  try:
   with self.assertRaisesRegex(ValueError,'same-description'):self.check(fd=fd)
  finally:os.close(fd)
 def test_inheritable_copy_refused(self):
  os.set_inheritable(self.copy,True)
  try:
   with self.assertRaisesRegex(ValueError,'private-readonly-copy'):self.check()
  finally:os.set_inheritable(self.copy,False)
 def test_metadata_mismatch_refused(self):
  bad=dict(self.meta,st_ino=self.meta['st_ino']+1)
  with self.assertRaisesRegex(ValueError,'metadata'):self.check(expected_metadata=bad)
 def test_writable_descriptor_refused(self):
  fd=os.open(self.path,os.O_RDWR|os.O_CLOEXEC)
  try:
   with self.assertRaisesRegex(ValueError,'private-readonly-copy'):self.check(fd=fd)
  finally:os.close(fd)
 def test_closed_production_adapter_refuses_fixture(self):
  with self.assertRaisesRegex(ValueError,'closed-successor-custody-target'):
   s.verify_description_custody(self.copy,self.pid,self.fd,self.path,self.meta)
 def test_postexit_requires_positive_pidfd_then_preserves_original_origin(self):
  with self.assertRaisesRegex(ValueError,'positive-predecessor-pidfd-exit'):
   s.verify_held_after_exit(self.copy,self.pidfd,self.meta,self.path,self.origin)
  os.write(self.pipe_w,b'X');os.close(self.pipe_w);self.pipe_w=None
  poll=select.poll();poll.register(self.pidfd,select.POLLIN);self.assertTrue(poll.poll(5000))
  _,status=os.waitpid(self.pid,0);self.joined=True;self.assertEqual(status,0)
  self.assertTrue(s.verify_held_after_exit(self.copy,self.pidfd,self.meta,self.path,self.origin))
  independent=os.open(self.path,os.O_RDONLY|os.O_CLOEXEC)
  try:
   with self.assertRaises(BlockingIOError):fcntl.flock(independent,fcntl.LOCK_EX|fcntl.LOCK_NB)
  finally:os.close(independent)
 def test_real_pidfd_getfd_private_fixture(self):
  libc=ctypes.CDLL(None,use_errno=True);libc.syscall.restype=ctypes.c_long
  result=libc.syscall(ctypes.c_long(438),ctypes.c_int(self.pidfd),ctypes.c_int(self.fd),ctypes.c_uint(0));error=ctypes.get_errno() if result<0 else 0
  report=dict(scope=s.SCOPE,syscall=438,flags=0,return_value=result,errno=error,production_paths_touched=False,fallback=False)
  if result<0:
   report['status']='BLOCKED_PIDFD_GETFD_'+errno.errorcode.get(error,'UNKNOWN')
   self.assertIn(error,(errno.EPERM,errno.EACCES))
  else:
   try:self.check(fd=result);report['status']='PASS_PRIVATE_PIDFD_GETFD_CURRENT_CUSTODIAN_ORIGIN_SPLIT'
   finally:os.close(result)
  (Path(__file__).parent/'PRIVATE-PIDFD-GETFD-RESULT.json').write_text(json.dumps(report,sort_keys=True,indent=2)+'\n')

class SourceAndRetention(unittest.TestCase):
 def test_predecessor_exact_source_capture_argv_and_grant(self):
  child,sudo,outer=s.authenticate_predecessor()
  self.assertTrue(child.endswith(b'\0'));self.assertTrue(sudo.startswith(b'/usr/bin/sudo\0-A\0'));self.assertIn(b'capture_outer.py\0',outer)
 def test_stopped_and_traced_predecessor_actors_refused(self):
  for state in (b'T',b't'):
   fields=[b'0']*50;fields[0]=state;fields[1]=b'2';fields[2]=b'3';fields[19]=b'4'
   raw=b'1 (private) '+b' '.join(fields)
   with self.subTest(state=state),mock.patch.object(Path,'read_bytes',return_value=raw):
    with self.assertRaisesRegex(ValueError,'exact-live-actor-birth-lineage'):s.process(1,'4',2,3,0,b'fixture')
 def test_frozen_adoption_unchanged_in_private_module(self):
  module=s.adoption();self.assertIs(module.verify_description_custody,s.verify_description_custody)
  self.assertEqual(module.ROOT_ACTOR['pid'],s.LOCK_ORIGIN_PID)
 def test_post_getfd_failure_retains_raw_descriptors(self):
  fake_meta=mock.Mock(st_dev=27,st_ino=4,st_mode=0o100644,st_uid=0,st_gid=0,st_nlink=1,st_size=0,st_mtime_ns=1,st_ctime_ns=2)
  libc=mock.Mock();libc.syscall=mock.Mock(side_effect=[901,902])
  p=mock.Mock(ROOT_MUTEX=Path('/run/lock/mckernel-development.lock'))
  with mock.patch.object(s,'adoption',return_value=p),mock.patch.object(s,'actor_binding',return_value=('bound',)),mock.patch.object(s.os,'stat',return_value=fake_meta),mock.patch.object(s.ctypes,'CDLL',return_value=libc),mock.patch.object(s,'live_pidfd'),mock.patch.object(s,'verify_description_custody',side_effect=ValueError('fixture-observer-failed')),mock.patch.object(s.os,'close') as close:
   hold=s.acquire_exact_standby();self.assertEqual((hold.pidfd,hold.fd),(901,902));self.assertFalse(hold.verified);self.assertIn('fixture-observer-failed',hold.error);close.assert_not_called()
 def test_pre_getfd_failure_closes_only_empty_pidfd(self):
  fake_meta=mock.Mock(st_dev=27,st_ino=4,st_mode=0o100644,st_uid=0,st_gid=0,st_nlink=1,st_size=0,st_mtime_ns=1,st_ctime_ns=2)
  libc=mock.Mock();libc.syscall=mock.Mock(side_effect=[901,-1]);p=mock.Mock(ROOT_MUTEX=Path('/run/lock/mckernel-development.lock'))
  with mock.patch.object(s,'adoption',return_value=p),mock.patch.object(s,'actor_binding',return_value=('bound',)),mock.patch.object(s.os,'stat',return_value=fake_meta),mock.patch.object(s.ctypes,'CDLL',return_value=libc),mock.patch.object(s,'live_pidfd'),mock.patch.object(s.os,'close') as close:
   with self.assertRaises(OSError):s.acquire_exact_standby()
   close.assert_called_once_with(901)

class DepartedOrigin(unittest.TestCase):
 def test_live_successor_holds_same_ofd_after_origin_normal_exit(self):
  import array,socket
  with tempfile.TemporaryDirectory(prefix='departed-origin-',dir=Path(__file__).parent) as tmp:
   path=Path(tmp)/'fixture-only.lock';path.touch(mode=0o600)
   parent_socket,child_socket=socket.socketpair();control_r,control_w=os.pipe()
   origin=os.fork()
   if origin==0:
    parent_socket.close();os.close(control_w)
    fd=os.open(path,os.O_RDONLY|os.O_CLOEXEC);fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
    child_socket.sendmsg([b'F'],[(socket.SOL_SOCKET,socket.SCM_RIGHTS,array.array('i',[fd]))])
    child_socket.close();select.select([control_r],[],[],10);os.read(control_r,1)
    os.close(fd);os.close(control_r);os._exit(0)
   child_socket.close();os.close(control_r);held=None;keeper=None;keeper_control=None
   try:
    self.assertTrue(select.select([parent_socket],[],[],5)[0])
    payload,ancillary,flags,address=parent_socket.recvmsg(1,socket.CMSG_SPACE(array.array('i').itemsize),socket.MSG_CMSG_CLOEXEC)
    self.assertEqual(payload,b'F');self.assertEqual(len(ancillary),1)
    received=array.array('i');received.frombytes(ancillary[0][2]);self.assertEqual(len(received),1);held=received[0]
    os.write(control_w,b'X');os.close(control_w);control_w=None
    self.assertEqual(os.waitpid(origin,0)[1],0);origin=None
    keeper_r,keeper_control=os.pipe();ready_r,ready_w=os.pipe();keeper=os.fork()
    if keeper==0:
     os.close(keeper_control);os.close(ready_r);os.write(ready_w,b'R');os.close(ready_w)
     select.select([keeper_r],[],[],10);os.read(keeper_r,1);os.close(held);os.close(keeper_r);os._exit(0)
    os.close(keeper_r);os.close(ready_w);self.assertTrue(select.select([ready_r],[],[],5)[0]);self.assertEqual(os.read(ready_r,1),b'R');os.close(ready_r)
    origin_rows=s.rows(os.getpid(),held);self.assertEqual(len(origin_rows),1)
    departed_pid=int(origin_rows[0][3]);self.assertNotEqual(departed_pid,keeper)
    self.assertFalse(Path('/proc/%d/stat'%departed_pid).exists())
    proof=s.verify_custody(held,keeper,held,path,s.metadata(os.fstat(held)),departed_pid)
    self.assertEqual(proof['lock_origin_pid'],departed_pid)
   finally:
    parent_socket.close()
    if control_w is not None:os.close(control_w)
    if origin is not None:os.waitpid(origin,0)
    if keeper_control is not None:os.close(keeper_control)
    if keeper is not None:self.assertEqual(os.waitpid(keeper,0)[1],0)
    if held is not None:os.close(held)

class Bridge(unittest.TestCase):
 def packet(self):
  import custody_runtime_bridge as b
  from types import SimpleNamespace
  own=b.ref(Path(b.__file__).resolve());adapter=b.ref(Path(s.__file__).resolve())
  auth=dict(author='/root',decision='GRANT_EXACT_HELD_KEEPER_CUSTODY_SOURCE_COMPOSITION',
   bridge=own,adapter=adapter,custody_adapter=s.ADAPTER,
   target=dict(pid=s.PID,starttime=s.START,parent=s.PARENT,pgid=s.PGID,fd=s.TARGET_FD,boot_id=s.BOOT),
   lock_origin_pid=s.LOCK_ORIGIN_PID,predecessor_launch_sha256=s.PINS['launch'][2],
   source_review=dict(path='/fixture/source-review.json',bytes=1,sha256='fixture'))
  review=dict(decision='PASS_SOURCE_ONLY_NO_EXECUTION_AUTHORITY',reviewer='/fixture/reviewer',bridge=own,adapter=adapter)
  ops=SimpleNamespace(raw_hold=None,packet=dict(successor_custody_adapter=s.ADAPTER,custody_successor_composition=auth),pinned_document=lambda _:review)
  return b,ops,auth,review
 def test_installs_only_closed_custody_hooks(self):
  b,ops,auth,review=self.packet();manifest=b.install_custody_successor(ops,auth)
  self.assertIs(ops.custody_module,s);self.assertTrue(callable(ops.acquire));self.assertFalse(manifest['mutation_authority'])
  with self.assertRaisesRegex(ValueError,'before-copy-once'):b.install_custody_successor(ops,auth)
 def test_rejects_wrong_origin_before_mutation(self):
  b,ops,auth,review=self.packet();auth['lock_origin_pid']=s.PID
  with self.assertRaisesRegex(ValueError,'exact-custody-composition-binding'):b.install_custody_successor(ops,auth)
  self.assertFalse(hasattr(ops,'acquire'));self.assertFalse(hasattr(ops,'custody_module'))
 def test_rejects_self_review_before_mutation(self):
  b,ops,auth,review=self.packet();review['reviewer']='/root'
  with self.assertRaisesRegex(ValueError,'independent-custody-composition-source-review'):b.install_custody_successor(ops,auth)
  self.assertFalse(hasattr(ops,'acquire'))
 def test_unverified_hold_retains_descriptors(self):
  b,ops,auth,review=self.packet();b.install_custody_successor(ops,auth)
  hold=s.Standby(777,778)
  with mock.patch.object(s,'acquire_exact_standby',return_value=hold),mock.patch.object(s.os,'fstat',side_effect=ValueError('fixture-fstat')),mock.patch.object(s.os,'close') as close:
   result=ops.acquire();self.assertIs(ops.raw_hold,hold);self.assertFalse(result.verified);self.assertEqual((result.fd,result.pidfd),(777,778));close.assert_not_called()

if __name__=='__main__':unittest.main(verbosity=2)
