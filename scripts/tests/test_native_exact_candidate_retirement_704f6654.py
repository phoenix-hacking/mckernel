#!/usr/bin/env python3
"""Pure tests only; no roots, Docker, observer, Git, or candidate is touched."""
import hashlib, importlib.util, io, os, stat, struct, subprocess, sys, tempfile, time, unittest
from pathlib import Path
from unittest import mock
ROOT=Path(__file__).parents[2]; PACKET=ROOT/'docs/verification/evidence/native-exact-candidate-retirement-704f6654-1.py'
s=importlib.util.spec_from_file_location('retire_packet',str(PACKET));M=importlib.util.module_from_spec(s);s.loader.exec_module(M)
class T(unittest.TestCase):
 def setUp(self):
  self.old=(M.RELEASE_SHA256,M.HELPER_SHA256,M.OBSERVER_SHA256,M.ARCHIVE_SHA256,M.HELPER_TEST_SHA256,M.OBSERVER_TEST_SHA256,M.INV_SHA,M.CAP_SHA,M.SUCCESS_SHA,M.BUILD_LEASE)
  self.flags={}
  def ioctl(fd,request,arg,mutate=False):
   key=os.fstat(fd if isinstance(fd,int) else fd.fileno()).st_ino
   if request==M.FS_IOC_GETFLAGS:arg[:]=struct.pack('I',self.flags.get(key,0));return 0
   if request==M.FS_IOC_SETFLAGS:self.flags[key]=struct.unpack('I',bytes(arg))[0];return 0
   raise AssertionError('unexpected ioctl')
  self.ioc=mock.patch.object(M.fcntl,'ioctl',side_effect=ioctl);self.ioc.start()
 def tearDown(self):self.ioc.stop();M.RELEASE_SHA256,M.HELPER_SHA256,M.OBSERVER_SHA256,M.ARCHIVE_SHA256,M.HELPER_TEST_SHA256,M.OBSERVER_TEST_SHA256,M.INV_SHA,M.CAP_SHA,M.SUCCESS_SHA,M.BUILD_LEASE=self.old
 def final(self):M.RELEASE_SHA256=M.HELPER_SHA256=M.OBSERVER_SHA256=M.ARCHIVE_SHA256=M.HELPER_TEST_SHA256=M.OBSERVER_TEST_SHA256=M.INV_SHA=M.CAP_SHA=M.SUCCESS_SHA='a'*64
 def test_missing_retention_bindings_are_explicit_draft_sentinels(self):
  self.assertEqual(M.RELEASE_SHA256,'RELEASE_HASH_REQUIRED')
  self.assertTrue(M.INV_SHA.endswith('_REQUIRED'))
  self.assertTrue(M.CAP_SHA.endswith('_REQUIRED'))
  self.assertTrue(M.SUCCESS_SHA.endswith('_REQUIRED'))
  with self.assertRaisesRegex(M.Error,'DRAFT_NOT_RELEASED'): M.draft_guard()
 def test_consumed_failure_inputs_are_exactly_bound(self):
  self.assertEqual(M.FAILURE_RECORD_SHA,'9ce279484127f50d309cdabc50daf36517de8a37c737014056a117dc3ccd89bb')
  self.assertEqual(M.FAILURE_ARCHIVE_SHA,'e09ca937456ede3494c81c611c96d45960f5f633e7874817dd1c54a309568417')
  self.assertEqual(M.FAILURE_CHECKPOINT_SHA,'4dfd1ca41e62a31e95112a5cf907ac32dc9973fb38e452611962e6dadbd3b64c')
 def proc(self,out=b'',err=b'',rc=0):
  p=mock.Mock();p.stdout=io.BytesIO();p.stderr=io.BytesIO();p.communicate.return_value=(out,err);p.returncode=rc;p.poll.return_value=rc;p.wait.return_value=rc;return p
 def anchored(self):
  p=self.proc();p.pid=77;p._mckernel_session=77;p._mckernel_leader_fd=11;p._mckernel_leader_starttime=9;p._mckernel_retired=False;p._mckernel_reader_finished=False;p._mckernel_leader_token=(1,2)
  return p
 def leader(self):return {'pid':77,'pgrp':77,'session':77,'starttime':9}
 def member(self):return {'pid':78,'pgrp':77,'session':77,'starttime':10}
 def row(self,pid):return self.leader() if pid==77 else self.member()
 def lease(self):
  class L:
   def assert_held(self):pass
  return L()
 def output(self,d):
  p=Path(d)/'evidence';p.mkdir(mode=0o700);return M.OutputDir(p)
 def tomb(self,path):
  s=Path(path).parent.stat()
  return {'path':str(path),'immutable':True,'schema':'mckernel.retirement-build-owner-exclusion.v2','parent_uid':s.st_uid,'parent_gid':s.st_gid,'parent_mode':stat.S_IMODE(s.st_mode),'filesystem_device':s.st_dev}
 def test_draft_no_side_effect(self):
  with mock.patch.object(M.os,'geteuid',side_effect=AssertionError),mock.patch.object(M,'gscalar',side_effect=AssertionError):
   with self.assertRaisesRegex(M.Error,'DRAFT_NOT_RELEASED'):M.execute('/x')
 def test_mechanical_single_replacement(self):
  raw=b"RELEASE_SHA256='RELEASE_HASH_REQUIRED'"
  self.assertEqual(M.final_bytes(raw,'a'*64),b"RELEASE_SHA256='"+b'a'*64+b"'")
  with self.assertRaises(M.Error):M.final_bytes(raw+raw,'a'*64)
 def test_exact_git_argv(self):
  self.assertEqual(M.gargv(M.GIT,'rev-parse','HEAD'),['/usr/bin/git','--no-optional-locks','--git-dir=/home/holden/mckernel/.git','--work-tree=/home/holden/mckernel','rev-parse','HEAD'])
  self.assertEqual(M.reader_argv(M.GIT,'cat-file','--batch')[2:8],['-c','core.packedGitWindowSize=32m','-c','core.packedGitLimit=128m','-c','core.deltaBaseCacheLimit=32m'])
  self.assertIn('core.deltaBaseCacheLimit=32m',M.reader_argv(M.GIT,'x'));self.assertNotIn('-C',M.gargv(M.GIT,'x'));self.assertEqual(M.genv()['GIT_ASKPASS'],'/bin/false')
 def test_root_and_release_path_fail_closed(self):
  self.final()
  with mock.patch.object(M.os,'geteuid',return_value=1000):
   with self.assertRaisesRegex(M.Error,'root euid'):M.admit(M.SOURCE/M.RELEASE_PATH)
  with mock.patch.object(M.os,'geteuid',return_value=0):
   with self.assertRaisesRegex(M.Error,'canonical'):M.admit('/tmp/x')
 def test_stream_short_type_size_hash(self):
  class P:
   def __init__(self,b):self.pid=None;self.stdin=io.BytesIO();self.stdout=io.BytesIO(b);self.stderr=io.BytesIO()
   def wait(self):return 0
   def poll(self):return 0
  oid='f2ba8f84ab5c1bce84a7b441cb1959cfc7093b7f';d=hashlib.sha256(b'abc').hexdigest()
  with mock.patch.object(M.subprocess,'Popen',return_value=P((oid+' blob 3\n').encode()+b'abc\n')):M.stream_blob(M.GIT,oid,d,3)
  for raw in ((oid+' tree 3\n').encode()+b'abc\n',(oid+' blob 4\n').encode()+b'abc\n',(oid+' blob 3\n').encode()+b'ab'):
   with mock.patch.object(M.subprocess,'Popen',return_value=P(raw)):
    with self.assertRaises(M.Error):M.stream_blob(M.GIT,oid,d,3)
 def test_stream_stall_and_reader_reap_are_bounded(self):
  class F:
   def fileno(self):return 9
  with mock.patch.object(M.select,'select',return_value=([],[],[])),mock.patch.object(M.time,'monotonic',side_effect=[0,2]):
   with self.assertRaisesRegex(M.Error,'wall timeout'):M.pipe_read(F(),1,1)
  p=mock.Mock();p.wait.side_effect=subprocess.TimeoutExpired(['x'],5)
  with mock.patch.object(M,'retire_process',return_value=(b'',b'')) as retire:
   with self.assertRaises(subprocess.TimeoutExpired):M.finish_reader(p)
  retire.assert_called_once()
 def test_canonical_reader_virtual_limit_covers_retained_pack_mapping(self):
  with mock.patch.object(M.resource,'setrlimit') as setlimit:M.canonical_reader_limits()
  self.assertEqual(setlimit.call_args_list,[mock.call(M.resource.RLIMIT_AS,(2<<30,2<<30)),mock.call(M.resource.RLIMIT_CPU,(900,900))])
  self.assertLess(2<<30,7890604289)
 def test_raw_child_is_retired_if_binding_fails(self):
  class Pipe(io.BytesIO):
   def __init__(self):super().__init__();self.closed_by_packet=False
   def close(self):self.closed_by_packet=True;super().close()
  def child():
   p=mock.Mock();p.pid=321;p.stdin=Pipe();p.stdout=Pipe();p.stderr=Pipe();return p
  for invoke in (
   lambda:p and M.run_bounded(['x']),
   lambda:p and M._reader(M.GIT),
   lambda:p and M.call(['x'],self.output(d),'observer')):
   with tempfile.TemporaryDirectory() as d:
    p=child()
    with mock.patch.object(M.subprocess,'Popen',return_value=p),mock.patch.object(M,'bind_process',side_effect=M.Error('bind failed')),mock.patch.object(M,'retire_process',return_value=(b'',b'')) as retire:
     with self.assertRaises(M.Error):invoke()
    retire.assert_called_once_with(p,mock.ANY)
    self.assertEqual(p._mckernel_session,p.pid);self.assertTrue(p.stdin.closed_by_packet);self.assertTrue(p.stdout.closed_by_packet);self.assertTrue(p.stderr.closed_by_packet)
 def test_stream_finalizes_exited_leader_with_descendants(self):
  p=self.proc();p._mckernel_session=91;p._mckernel_reader_finished=False;p.poll.return_value=0
  oid='0'*40;digest=hashlib.sha256(b'abc').hexdigest()
  with mock.patch.object(M,'_reader',return_value=p),mock.patch.object(M,'stream_blob_process',side_effect=M.Error('record failed')),mock.patch.object(M,'finish_reader',return_value=0) as finish:
   with self.assertRaisesRegex(M.Error,'record failed'):M.stream_blob(M.GIT,oid,digest,3)
  finish.assert_called_once_with(p)
  p=self.proc();p._mckernel_session=92;p._mckernel_reader_finished=False;p.poll.return_value=0
  with mock.patch.object(M,'_reader',return_value=p),mock.patch.object(M,'stream_blob_process',side_effect=M.Error('record failed')),mock.patch.object(M,'finish_reader',return_value=0) as finish:
   with self.assertRaisesRegex(M.Error,'record failed'):M.stream_store(M.GIT,[(oid,digest,3,'a'*64)])
  finish.assert_called_once_with(p)
 def test_stream_reader_keeps_pipes_open_through_term_kill_and_empty_census(self):
  class Pipe(io.BytesIO):
   def __init__(self):super().__init__();self.closed_by_packet=False
   def close(self):self.closed_by_packet=True;super().close()
  p=self.anchored();p.stdin=Pipe();p.stdout=Pipe();p.stderr=Pipe()
  row=self.member();signals=[]
  census=[[row],[row],[row],[row],[self.leader()],[]]
  def sent(fd,sig):signals.append((sig,p.stdout.closed_by_packet))
  with mock.patch.object(M,'_reader',return_value=p),mock.patch.object(M,'stream_blob_process'),mock.patch.object(M,'session_members',side_effect=census),mock.patch.object(M,'pidfd_open',return_value=12),mock.patch.object(M,'pidfd_identity',return_value=77),mock.patch.object(M,'proc_row',side_effect=self.row),mock.patch.object(M,'observe_exit',return_value=0),mock.patch.object(M,'pidfd_send',side_effect=sent),mock.patch.object(M.os,'close'),mock.patch.object(M,'_drain',return_value=(b'',b'')):
   with self.assertRaisesRegex(M.Error,'descendants survived'):M.stream_store(M.GIT,[('0'*40,hashlib.sha256(b'abc').hexdigest(),3,'a'*64)])
  self.assertEqual([x[0] for x in signals],[M.signal.SIGTERM,M.signal.SIGKILL]);self.assertEqual([x[1] for x in signals],[False,False]);self.assertTrue(p._mckernel_retired);self.assertTrue(p.stdout.closed_by_packet)
 def test_repeated_interrupt_after_term_census_kills_then_propagates(self):
  p=self.anchored();row=self.member();signals=[]
  census=[[row],M.Interrupted('second'),[row],[row],[self.leader()],[]]
  with mock.patch.object(M,'session_members',side_effect=census),mock.patch.object(M,'pidfd_open',return_value=12),mock.patch.object(M,'pidfd_identity',return_value=77),mock.patch.object(M,'proc_row',side_effect=self.row),mock.patch.object(M,'observe_exit',return_value=0),mock.patch.object(M,'pidfd_send',side_effect=lambda fd,sig:signals.append(sig)),mock.patch.object(M.os,'close'),mock.patch.object(M,'_drain',return_value=(b'',b'')):
   with self.assertRaises(M.Interrupted):M.retire_process(p,{'stdout_data':bytearray(),'stderr_data':bytearray()})
  self.assertEqual(signals,[M.signal.SIGTERM,M.signal.SIGKILL]);self.assertTrue(p._mckernel_retired)
 def test_run_bounded_preserves_first_interruption_after_cleanup_signal(self):
  p=self.proc();p.pid=321;first=M.Interrupted('first interruption')
  with mock.patch.object(M.subprocess,'Popen',return_value=p),mock.patch.object(M,'bind_process',side_effect=lambda x:x),mock.patch.object(M,'_drain',side_effect=first),mock.patch.object(M,'retire_process',side_effect=M.Interrupted('second interruption')):
   with self.assertRaisesRegex(M.Interrupted,'first interruption'):M.run_bounded(['x'])
 def test_postspawn_permission_and_cleanup_failures_are_preserved(self):
  p=self.proc();p.pid=321
  with mock.patch.object(M.subprocess,'Popen',return_value=p),mock.patch.object(M,'bind_process',side_effect=PermissionError('denied')),mock.patch.object(M,'retire_process',return_value=(b'',b'')) as retire:
   with self.assertRaisesRegex(M.Error,'admission command: denied'):M.run_bounded(['x'])
  retire.assert_called_once_with(p,mock.ANY)
  p=self.proc();p.pid=322
  with mock.patch.object(M.subprocess,'Popen',return_value=p),mock.patch.object(M,'bind_process',side_effect=M.Error('run primary')),mock.patch.object(M,'retire_process',side_effect=M.Error('run cleanup')):
   with self.assertRaisesRegex(M.Error,'primary failure:.*run primary.*cleanup failure:.*run cleanup'):M.run_bounded(['x'])
  with tempfile.TemporaryDirectory() as d:
   p=self.proc();p.pid=323;base=self.output(d)
   try:
    with mock.patch.object(M.subprocess,'Popen',return_value=p),mock.patch.object(M,'bind_process',side_effect=M.Error('call primary')),mock.patch.object(M,'retire_process',side_effect=M.Error('call cleanup')):
     with self.assertRaisesRegex(M.Error,'primary failure:.*call primary.*cleanup failure:.*call cleanup'):M.call(['x'],base,'observer')
    self.assertIn(b'call primary',(base.path/'observer.stderr').read_bytes())
   finally:base.close()
 def test_failed_retirement_does_not_mark_early_and_can_retry(self):
  p=self.anchored();row=self.member()
  with mock.patch.object(M,'pidfd_identity',return_value=77),mock.patch.object(M,'proc_row',side_effect=self.row),mock.patch.object(M,'observe_exit',return_value=0),mock.patch.object(M.os,'close'),mock.patch.object(M,'KILL_TIMEOUT',0):
   with mock.patch.object(M,'session_members',return_value=[row]),mock.patch.object(M,'pidfd_open',side_effect=M.Error('pidfd unavailable')):
    with self.assertRaisesRegex(M.Error,'pidfd unavailable'):M.retire_process(p,{'stdout_data':bytearray(),'stderr_data':bytearray()})
   self.assertFalse(p._mckernel_retired);self.assertIsNone(p._mckernel_leader_fd)
   with mock.patch.object(M,'session_members',side_effect=[[self.leader()],[self.leader()],[]]),mock.patch.object(M,'pidfd_open',return_value=12),mock.patch.object(M,'pidfd_token',return_value=(1,2)),mock.patch.object(M,'unreaped_child',return_value=None),mock.patch.object(M,'pidfd_send'):
    M.retire_process(p,{'stdout_data':bytearray(),'stderr_data':bytearray()})
   self.assertTrue(p._mckernel_retired)
 def test_observer_exact_argv_capture_and_duplicate_json(self):
  self.final()
  with tempfile.TemporaryDirectory() as d:
   b=self.output(d);lease=self.lease();fd=os.open(str(M.OBSERVER),os.O_RDONLY)
   try:
    with mock.patch.object(M.subprocess,'Popen',return_value=self.proc()) as run,mock.patch.object(M,'_drain',return_value=(b'{"x":1}',b'')),mock.patch.object(M,'group_members',return_value=[]):self.assertEqual(M.observer_callback(b,lease,fd)(list(M.QUARANTINES),[[],[]]),{'x':1});self.assertEqual(run.call_args.args[0],['/usr/bin/python3','-E','-s','-B','/proc/self/fd/'+str(fd),'--target',M.QUARANTINES[0],'--target',M.QUARANTINES[1]]);self.assertIn(fd,run.call_args.kwargs['pass_fds'])
    self.assertTrue((b.path/'observer.stdout').exists())
   finally:os.close(fd);b.close()
  with tempfile.TemporaryDirectory() as d:
   b=self.output(d);fd=os.open(str(M.OBSERVER),os.O_RDONLY)
   try:
    with mock.patch.object(M.subprocess,'Popen',return_value=self.proc()),mock.patch.object(M,'_drain',return_value=(b'{"x":1,"x":2}',b'')),mock.patch.object(M,'group_members',return_value=[]):
     with self.assertRaisesRegex(M.Error,'duplicate JSON'):M.observer_callback(b,self.lease(),fd)(list(M.QUARANTINES),[[],[]])
   finally:os.close(fd);b.close()
 def test_callback_failure_durable_and_docker_omission(self):
  self.final()
  with tempfile.TemporaryDirectory() as d:
   b=self.output(d);fd=os.open(str(M.OBSERVER),os.O_RDONLY)
   try:
    with mock.patch.object(M.subprocess,'Popen',return_value=self.proc(rc=3)),mock.patch.object(M,'_drain',return_value=(b'o',b'e')),mock.patch.object(M,'group_members',return_value=[]):
     with self.assertRaisesRegex(M.Error,'observer callback failed'):M.observer_callback(b,self.lease(),fd)(list(M.QUARANTINES),[[],[]])
    self.assertEqual((b.path/'observer.stdout').read_bytes(),b'o')
   finally:os.close(fd);b.close()
  with tempfile.TemporaryDirectory() as d:
   i='a'*64;t={'decd7cf92467e1214cc955d15a00b847587ada37016f206e9a82019cbb72c6b9':{},'8943e49772f840ba5da6571c2e2c6fde60b61157f21f873d832669157ef9bc10':{}}
   rs=[mock.Mock(returncode=0,stdout=(i+'\n').encode(),stderr=b''),mock.Mock(returncode=0,stdout=b'[]',stderr=b'')]
   b=self.output(d)
   try:
    with mock.patch.object(M.subprocess,'Popen',side_effect=[self.proc(rc=x.returncode) for x in rs]) as run,mock.patch.object(M,'_drain',side_effect=[(x.stdout,x.stderr) for x in rs]),mock.patch.object(M,'group_members',return_value=[]):
     with self.assertRaisesRegex(M.Error,'omission/churn'):M.docker_callback(b,{'terminal_containers':t},self.lease())()
    self.assertEqual(run.call_args_list[0].args[0],['/usr/bin/docker','ps','--all','--quiet','--no-trunc']);self.assertEqual(run.call_args_list[1].args[0],['/usr/bin/docker','inspect',i])
   finally:b.close()
 def test_docker_mount_order_is_canonical_but_fields_remain_exact(self):
  mounts=[{'Type':'bind','Source':'/a','Destination':'/x','Mode':'ro','RW':False,'Propagation':'rprivate'},{'Type':'bind','Source':'/b','Destination':'/y','Mode':'rw','RW':True,'Propagation':'rprivate'}]
  left={'Id':'a'*64,'State':{'Status':'exited'},'Mounts':mounts,'Config':{'Image':'x'}}
  right=dict(left,Mounts=list(reversed(mounts)))
  self.assertEqual(M.canonical_docker_row(left),M.canonical_docker_row(right))
  changed=[dict(mounts[0],RW=True),mounts[1]]
  self.assertNotEqual(M.canonical_docker_row(left),M.canonical_docker_row(dict(left,Mounts=changed)))
  with self.assertRaisesRegex(M.Error,'mount record'):M.canonical_docker_row(dict(left,Mounts=[1]))
 def test_timeout_retires_real_process_group_and_keeps_captures(self):
  with tempfile.TemporaryDirectory() as d:
   argv=[sys.executable,'-u','-c','import subprocess,time; subprocess.Popen(["/bin/sleep","30"]); print("partial"); time.sleep(30)']
   b=self.output(d)
   try:
    with mock.patch.object(M,'COMMAND_TIMEOUT',.15):
     with self.assertRaisesRegex(M.Error,'observer callback failed'):M.call(argv,b,'observer')
    self.assertIn(b'partial',(b.path/'observer.stdout').read_bytes());self.assertEqual((b.path/'observer.status').read_text(),'124\n')
   finally:b.close()
 def test_interruption_retires_then_writes_durable_captures(self):
  with tempfile.TemporaryDirectory() as d:
   p=self.proc(b'partial',b'error');p.pid=321
   b=self.output(d)
   try:
    with mock.patch.object(M.subprocess,'Popen',return_value=p),mock.patch.object(M,'bind_process',side_effect=lambda x:x),mock.patch.object(M,'_drain',side_effect=M.Interrupted('stop')),mock.patch.object(M,'retire_process',return_value=(b'partial',b'error')):
     with self.assertRaises(M.Interrupted):M.call(['x'],b,'observer')
    self.assertEqual((b.path/'observer.stdout').read_bytes(),b'partial')
   finally:b.close()
 def test_proc_permission_and_vanish_reconciliation(self):
  with mock.patch.object(M,'raw_starttime',return_value=7),mock.patch.object(Path,'read_bytes',side_effect=PermissionError('x')):
   with self.assertRaisesRegex(M.Error,'cmdline unreadable'):M.proc_cmdline_stable(1)
  with mock.patch.object(M,'raw_starttime',side_effect=[7,FileNotFoundError()]):
   with mock.patch.object(Path,'read_bytes',return_value=b'x\0'):
    with self.assertRaisesRegex(M.Error,'disappeared during census'):M.proc_cmdline_stable(1)
 def test_root_schema_has_no_path_and_carries_size(self):
  self.assertEqual(M.root(25166,9),{'device':26,'inode':25166,'uid':1000,'gid':1000,'mode':0o755,'kind':'directory','size':9})
 def test_stable_read_rejects_fifo_and_oversize_before_read(self):
  with tempfile.TemporaryDirectory() as d:
   fifo=Path(d)/'fifo';os.mkfifo(str(fifo))
   with self.assertRaisesRegex(M.Error,'not durable regular'):M.stable_regular(fifo)
   large=Path(d)/'large';large.write_bytes(b'x')
   with mock.patch.object(M,'MAX_FILE',0):
    with self.assertRaisesRegex(M.Error,'substituted before read'):M.stable_regular(large)
 def test_shared_build_owner_lease_is_exclusive_and_replacement_fails(self):
  with mock.patch.object(sys,'path',[str(ROOT/'scripts')]+sys.path):
   spec=importlib.util.spec_from_file_location('owner',str(ROOT/'scripts/native_rust_exact_build_container_owner.py'));owner=importlib.util.module_from_spec(spec);spec.loader.exec_module(owner)
  with tempfile.TemporaryDirectory() as d:
   lease_path=Path(d)/'build-lease.json';M.BUILD_LEASE=lease_path
   release={'operational_exclusion':str(lease_path),'boot_id':'b','exclusion_tombstone':self.tomb(lease_path)}
   with mock.patch.object(M,'proc_starttime',return_value=7):
    with M.ExclusionLease(release) as held:
     with self.assertRaises(FileExistsError):owner.Lease(lease_path,'build').acquire()
     held.assert_held()
     original=lease_path.stat()
     replacement=Path(d)/'replacement';replacement.write_text('{}')
     os.replace(str(replacement),str(lease_path))
     with self.assertRaisesRegex(M.Error,'replaced'):held.assert_held()
     self.assertEqual(original.st_ino,held.identity.st_ino)
 def test_lease_failures_close_descriptors_and_preserve_tombstone(self):
  with tempfile.TemporaryDirectory() as d:
   path=Path(d)/'lease';M.BUILD_LEASE=path;r={'operational_exclusion':str(path),'boot_id':'b','exclusion_tombstone':self.tomb(path)}
   lease=M.ExclusionLease(r)
   with mock.patch.object(M,'proc_starttime',return_value=7),mock.patch.object(lease,'_make_immutable',side_effect=M.Error('immutable failed')):
    with self.assertRaisesRegex(M.Error,'immutable failed'):lease.__enter__()
   self.assertTrue(path.exists());self.assertIsNone(lease.fd)
  with tempfile.TemporaryDirectory() as d:
   path=Path(d)/'lease';M.BUILD_LEASE=path;r={'operational_exclusion':str(path),'boot_id':'b','exclusion_tombstone':self.tomb(path)}
   with mock.patch.object(M,'proc_starttime',return_value=7):lease=M.ExclusionLease(r);lease.__enter__()
   with mock.patch.object(M.os,'fsync',side_effect=OSError('durability failed')):
    with self.assertRaisesRegex(OSError,'durability failed'):lease.finalize()
   self.assertIsNone(lease.fd)
  with tempfile.TemporaryDirectory() as d:
   path=Path(d)/'lease';M.BUILD_LEASE=path;r={'operational_exclusion':str(path),'boot_id':'b','exclusion_tombstone':self.tomb(path)}
   with mock.patch.object(M,'proc_starttime',return_value=7):lease=M.ExclusionLease(r);lease.__enter__()
   with mock.patch.object(M.os,'fsync',side_effect=OSError('durability failed')):
    with self.assertRaisesRegex(OSError,'durability failed'):lease.__exit__(None,None,None)
   self.assertIsNone(lease.fd)
 def test_status_failure_is_composite_and_sealed_modules_use_checked_bytes(self):
  with tempfile.TemporaryDirectory() as d:
   base=self.output(d);primary=M.Error('primary')
   with mock.patch.object(M,'status',side_effect=OSError('disk full')):
    with self.assertRaisesRegex(M.Error,'status durability failure'):M.fail_status(base,primary)
   sources={'helper':b'X=1\n','archive':b'Y=2\n','observer':b'Z=3\n'}
   h,observer=M.helper(base,sources)
   try:
    self.assertEqual((base.path/'helper.sealed.py').read_bytes(),sources['helper'])
    self.assertEqual(h.X,1);self.assertEqual(os.read(observer,len(sources['observer'])),sources['observer'])
   finally:os.close(observer);base.close()
 def test_live_gate_accepts_held_shared_lease_and_rejects_other_lease(self):
  with tempfile.TemporaryDirectory() as d:
   build=Path(d)/'build';other=Path(d)/'other';fresh=Path(d)/'fresh';fresh.mkdir(0o700);M.BUILD_LEASE=build;out=M.OutputDir(fresh);real_listdir=os.listdir
   r={'boot_id':'boot','launcher_identities':[],'conflict_basenames':list(M.CONFLICT_BASENAMES),'operational_exclusion':str(build),'exclusion_tombstone':self.tomb(build),'heavy_lease_paths':[str(build),str(other)],'output_dir':str(fresh)}
   with mock.patch.object(M,'proc_starttime',return_value=7),mock.patch.object(M,'free_bytes',return_value=1<<50),mock.patch.object(M.os,'sysconf',return_value=1<<30),mock.patch.object(M.os,'listdir',side_effect=lambda p:[] if p=='/proc' else real_listdir(p)),mock.patch.object(Path,'read_text',return_value='boot'):
    with M.ExclusionLease(r) as held:
     M.live_gate(r,held,out)
     other.write_text('active')
     with self.assertRaisesRegex(M.Error,'active heavy lease'):M.live_gate(r,held,out)
   out.close()
 def test_live_gate_rejects_substituted_or_nonempty_output(self):
  with tempfile.TemporaryDirectory() as d:
   build=Path(d)/'build';M.BUILD_LEASE=build;fresh=Path(d)/'fresh';fresh.mkdir(0o700);out=M.OutputDir(fresh);real_listdir=os.listdir
   r={'boot_id':'boot','launcher_identities':[],'conflict_basenames':list(M.CONFLICT_BASENAMES),'operational_exclusion':str(build),'exclusion_tombstone':self.tomb(build),'heavy_lease_paths':[str(build)],'output_dir':str(fresh)}
   patches=(mock.patch.object(M,'proc_starttime',return_value=7),mock.patch.object(M,'free_bytes',return_value=1<<50),mock.patch.object(M.os,'sysconf',return_value=1<<30),mock.patch.object(M.os,'listdir',side_effect=lambda p:[] if p=='/proc' else real_listdir(p)),mock.patch.object(Path,'read_text',return_value='boot'))
   with patches[0],patches[1],patches[2],patches[3],patches[4],M.ExclusionLease(r) as held:
    (fresh/'x').write_text('x')
    with self.assertRaisesRegex(M.Error,'nonempty'):M.live_gate(r,held,out)
   out.close()
   fresh2=Path(d)/'fresh2';fresh2.mkdir(0o700);out2=M.OutputDir(fresh2);replacement=Path(d)/'replacement';replacement.mkdir(0o700);os.replace(str(replacement),str(fresh2))
   with self.assertRaisesRegex(M.Error,'substituted'):out2.assert_fresh()
   out2.close()
 def test_execute_orders_fresh_output_lease_gate_then_helper_setup(self):
  with tempfile.TemporaryDirectory() as d:
   build=Path(d)/'build';output=Path(d)/'output';M.BUILD_LEASE=build
   r={'boot_id':'boot','launcher_identities':[],'conflict_basenames':list(M.CONFLICT_BASENAMES),'operational_exclusion':str(build),'exclusion_tombstone':self.tomb(build),'heavy_lease_paths':[str(build)],'output_dir':str(output),'docker':{}};real_listdir=os.listdir
   events=[];received={}
   class H:
    def remove_root(self,*x):pass
    def retire(self,*x,**kw):events.append('retire');received['args']=x;received['kwargs']=kw;return {'status':'PASS'}
   def make_output(_):output.mkdir(0o700);return M.OutputDir(output)
   observer=os.open('/dev/null',os.O_RDONLY)
   with mock.patch.object(M,'admit',return_value=(r,{'helper':b'','archive':b'','observer':b''})),mock.patch.object(M,'fresh_output',side_effect=make_output),mock.patch.object(M,'helper',side_effect=lambda *x:(events.append('helper') or (H(),observer))),mock.patch.object(M,'proc_starttime',return_value=7),mock.patch.object(M,'free_bytes',return_value=1<<50),mock.patch.object(M.os,'sysconf',return_value=1<<30),mock.patch.object(M.os,'listdir',side_effect=lambda p:[] if p=='/proc' else real_listdir(p)),mock.patch.object(Path,'read_text',return_value='boot'):
    self.assertEqual(M.execute('ignored'),{'status':'PASS'})
    self.assertEqual(events,['helper','retire']);self.assertTrue((output/'packet.status').exists())
    self.assertEqual(received['args'][2:5],M.OUT[:3]);self.assertEqual(received['kwargs']['output_dir_fd']>=0,True);self.assertFalse(any('/proc/self/fd/' in x for x in received['args'][2:5]))
 def test_delete_boundary_checks_before_and_after_and_blocks_lost_lease(self):
  events=[]
  class H:
   def remove_root(self,item,journal):events.append('delete')
  class L:
   def __init__(self,fail=False):self.fail=fail
   def assert_held(self):
    events.append('check')
    if self.fail:raise M.Error('lease replaced')
  h=H();M.bind_delete_boundary(h,L());h.remove_root(None,None)
  self.assertEqual(events,['check','delete','check'])
  events[:]=[];h=H();M.bind_delete_boundary(h,L(True))
  with self.assertRaisesRegex(M.Error,'replaced'):h.remove_root(None,None)
  self.assertEqual(events,['check'])
 def test_packet_schema_rejects_extra_root_member_and_unrelated_seal(self):
  self.final()
  root={'device':26,'inode':25166,'uid':1000,'gid':1000,'mode':0o755,'kind':'directory','size':0};backup=dict(root,inode=35798)
  parent={'device':26,'inode':1,'uid':1000,'gid':1000,'mode':0o755,'kind':'directory','size':0}
  member={'device':26,'inode':2,'uid':1000,'gid':1000,'mode':0o755,'kind':'directory','size':0,'path':'member'}
  def row(path,identity,q,members):return {'path':path,'root':identity,'parent':parent,'members':members,'quarantine_name':q,'quarantine_uid':0,'quarantine_gid':0,'quarantine_mode':0o700}
  entry={'root':'candidate','path':'member','type':'directory','uid':1000,'gid':1000,'mode':0o755,'size':0}
  r={'schema':'mckernel.ordinary-retirement-release.v1','status':'PASS_ONE_SHOT_RETIRE','one_shot':True,'retry':False,'rollback':False,'main_commit':M.MAIN,'ihk_commit':M.IHK,'candidate':M.CANDIDATE,'metadata_backup':M.BACKUP,'inventory_sha256':M.INV_SHA,'capsule_sha256':M.CAP_SHA,'success_sha256':M.SUCCESS_SHA,'source_hashes':{'helper':M.HELPER_SHA256,'observer':M.OBSERVER_SHA256,'archive':M.ARCHIVE_SHA256,'helper_test':M.HELPER_TEST_SHA256,'observer_test':M.OBSERVER_TEST_SHA256},'roots':[row(M.CANDIDATE,root,M.QUARANTINES[0].rsplit('/',1)[1],[member]),row(M.BACKUP,backup,M.QUARANTINES[1].rsplit('/',1)[1],[])],'sealed':{'retention_manifest_sha256':M.INV_SHA,'retention_manifest_pushed_sha256':M.INV_SHA,'retention_manifest_fetched_sha256':M.INV_SHA,'capsule_sha256':M.CAP_SHA,'capsule_pushed_sha256':M.CAP_SHA,'capsule_fetched_sha256':M.CAP_SHA,'retention_manifest_path':str(M.INVENTORY),'capsule_path':str(M.CAPSULE)},'observer':{'observer_sha256':M.OBSERVER_SHA256,'boot_id':'b'},'docker':{'terminal':{'id':'decd7cf92467e1214cc955d15a00b847587ada37016f206e9a82019cbb72c6b9'},'terminal_containers':{}},'boot_id':'b','launcher_identities':[{'pid':1,'starttime':1}],'operational_exclusion':str(M.BUILD_LEASE),'exclusion_tombstone':{'path':str(M.BUILD_LEASE),'immutable':True,'schema':'mckernel.retirement-build-owner-exclusion.v2','parent_uid':1000,'parent_gid':1000,'parent_mode':0o700,'filesystem_device':1},'conflict_basenames':list(M.CONFLICT_BASENAMES),'heavy_lease_paths':[str(M.BUILD_LEASE)],'resource_floors':M.FLOORS,'output_dir':str(M.EVIDENCE_DIR),'evidence_namespace':{'parent':'/dev/shm','name':M.EVIDENCE_DIR.name,'device':1,'uid':0,'gid':0,'mode':0o1777,'sticky':True},'template':{},'finalization':{}}
  inv={'roots':[{'name':'candidate','path':M.CANDIDATE,'identity':{'dev':26,'inode':25166,'uid':1000,'gid':1000,'mode':0o755}},{'name':'metadata-backup','path':M.BACKUP,'identity':{'dev':26,'inode':35798,'uid':1000,'gid':1000,'mode':0o755}}],'entries':[entry]}
  with mock.patch.object(M,'mechanical'),mock.patch.object(M,'canonical_stores'),mock.patch.object(M,'verify_inventory'):
   M.validate_release(r,'f',inv)
   r['roots'][0]['root']['extra']=1
   with self.assertRaisesRegex(M.Error,'root/parent/member'):M.validate_release(r,'f',inv)
   r['roots'][0]['root'].pop('extra');r['sealed']['unrelated']='x'
   with self.assertRaisesRegex(M.Error,'sealed'):M.validate_release(r,'f',inv)
 def test_packet_admitted_roots_reach_real_helper_release_roots(self):
  self.final()
  spec=importlib.util.spec_from_file_location('helper',str(M.HELPER));h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)
  with tempfile.TemporaryDirectory(dir='/dev/shm') as d:
   paths=[Path(d)/'candidate',Path(d)/'backup']
   for p in paths:p.mkdir();p.chmod(0o755)
   rows=[];mroots=[]
   for name,p,q in zip(('candidate','metadata-backup'),paths,('.qc','.qb')):
    inv=h.inventory_root(p);rows.append({'path':str(p),'root':inv['root'],'parent':h.root_identity(p.parent),'members':inv['members'],'quarantine_name':q,'quarantine_uid':0,'quarantine_gid':0,'quarantine_mode':0o700});i=inv['root'];mroots.append({'name':name,'path':str(p),'identity':{'dev':i['device'],'inode':i['inode'],'uid':i['uid'],'gid':i['gid'],'mode':i['mode']}})
   build=Path(d)/'build';old=(M.CANDIDATE,M.BACKUP,M.QUARANTINES,M.BUILD_LEASE);M.CANDIDATE,M.BACKUP,M.QUARANTINES,M.BUILD_LEASE=str(paths[0]),str(paths[1]),(str(Path(d)/'.qc'),str(Path(d)/'.qb')),build
   try:
    release={'schema':'mckernel.ordinary-retirement-release.v1','status':'PASS_ONE_SHOT_RETIRE','one_shot':True,'retry':False,'rollback':False,'main_commit':M.MAIN,'ihk_commit':M.IHK,'candidate':M.CANDIDATE,'metadata_backup':M.BACKUP,'inventory_sha256':M.INV_SHA,'capsule_sha256':M.CAP_SHA,'success_sha256':M.SUCCESS_SHA,'source_hashes':{'helper':M.HELPER_SHA256,'observer':M.OBSERVER_SHA256,'archive':M.ARCHIVE_SHA256,'helper_test':M.HELPER_TEST_SHA256,'observer_test':M.OBSERVER_TEST_SHA256},'roots':rows,'sealed':{'retention_manifest_sha256':M.INV_SHA,'retention_manifest_pushed_sha256':M.INV_SHA,'retention_manifest_fetched_sha256':M.INV_SHA,'capsule_sha256':M.CAP_SHA,'capsule_pushed_sha256':M.CAP_SHA,'capsule_fetched_sha256':M.CAP_SHA,'retention_manifest_path':str(M.INVENTORY),'capsule_path':str(M.CAPSULE)},'observer':{'observer_sha256':M.OBSERVER_SHA256,'boot_id':'b'},'docker':{'terminal':{'id':'decd7cf92467e1214cc955d15a00b847587ada37016f206e9a82019cbb72c6b9'},'terminal_containers':{}},'boot_id':'b','launcher_identities':[{'pid':1,'starttime':1}],'operational_exclusion':str(build),'exclusion_tombstone':self.tomb(build),'conflict_basenames':list(M.CONFLICT_BASENAMES),'heavy_lease_paths':[str(build)],'resource_floors':M.FLOORS,'output_dir':str(M.EVIDENCE_DIR),'template':{},'finalization':{}}
    release['evidence_namespace']={'parent':'/dev/shm','name':M.EVIDENCE_DIR.name,'device':1,'uid':0,'gid':0,'mode':0o1777,'sticky':True}
    inv={'roots':mroots,'entries':[]}
    with mock.patch.object(M,'mechanical'),mock.patch.object(M,'canonical_stores'),mock.patch.object(M,'verify_inventory'):M.validate_release(release,'f',inv)
    with mock.patch.object(h,'manifest_authority',return_value={'roots':mroots,'entries':[]}):self.assertEqual(len(h.release_roots(release,paths)),2)
   finally:M.CANDIDATE,M.BACKUP,M.QUARANTINES,M.BUILD_LEASE=old
 def test_loaded_helper_dirfd_bridge_never_accepts_procfd_output_names(self):
  spec=importlib.util.spec_from_file_location('helper_bridge',str(M.HELPER));h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)
  with tempfile.TemporaryDirectory() as d:
   out=Path(d)/'out';out.mkdir();fd=os.open(str(out),os.O_RDONLY|os.O_DIRECTORY)
   try:
    with mock.patch.object(h,'release_roots',return_value=[]),mock.patch.object(h,'validate_observation'),mock.patch.object(h,'validate_docker_census'):
     self.assertEqual(h.retire([],{'operational_exclusion':'x'},'claim','journal','evidence',lambda *x:{},lambda:{},output_dir_fd=fd)['status'],'PASS')
    self.assertEqual({x.name for x in out.iterdir()},{'claim','journal','evidence'})
    with self.assertRaises(h.RetirementError):h.retire([],{'operational_exclusion':'x'},'/proc/self/fd/9/claim','journal2','evidence2',lambda *x:{},lambda:{},output_dir_fd=fd)
   finally:os.close(fd)
 def test_live_gate_rejects_resource_before_mutation(self):
  r={'boot_id':'x','launcher_identities':[],'process_exclusions':['candidate'],'heavy_lease_paths':[],'output_dir':'/home/holden/mckernel-work/scratch/new'}
  with mock.patch.object(M,'free_bytes',return_value=0),mock.patch.object(M.os,'sysconf',return_value=0):
   with self.assertRaisesRegex(M.Error,'resource floor'):M.live_gate(r,mock.Mock(),mock.Mock())
 def test_fresh_output_and_release_sentinel(self):
  with self.assertRaises(M.Error):M.fresh_output({'output_dir':'/tmp/no'})
  self.assertEqual(M.HELPER_SHA256,'704a3f5f8f2ab259af493b3fbc0dd5bf1d461b8a0d67301d2176052b520df54b')
  self.assertEqual(M.HELPER_SHA256,M.sha(M.HELPER.read_bytes()));self.assertEqual(M.HELPER_TEST_SHA256,M.sha(M.HELPER_TEST.read_bytes()))
  self.assertEqual(M.OBSERVER_SHA256,'3562b1d3d4e9a1e09cb7fa2be30f8e320923d50cf628b7f42314318702653666')
  self.assertEqual(PACKET.read_bytes().count(b"RELEASE_SHA256='RELEASE_HASH_REQUIRED'"),1)
  self.assertNotIn('"/usr/bin/sudo"',PACKET.read_text())
 def test_descriptor_output_substitution_and_immutable_reopen_fail_closed(self):
  with tempfile.TemporaryDirectory() as d:
   out=self.output(d);out.write('observer.stdout',b'exact')
   moved=Path(d)/'moved';out.path.rename(moved);out.path.mkdir(0o700)
   try:
    with self.assertRaisesRegex(M.Error,'output substituted'):out.assert_bound()
   finally:out.close()
  with tempfile.TemporaryDirectory() as d:
   path=Path(d)/'lease';M.BUILD_LEASE=path;r={'operational_exclusion':str(path),'boot_id':'b','exclusion_tombstone':self.tomb(path)}
   with mock.patch.object(M,'proc_starttime',return_value=7):
    lease=M.ExclusionLease(r);lease.__enter__();lease.finalize()
   self.assertTrue(path.exists())
   with self.assertRaises(FileExistsError):os.open(str(path),os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
 def test_pid_reuse_proof_loss_never_signals_a_numeric_group(self):
  p=mock.Mock();p.pid=123;p._mckernel_session=123;p._mckernel_retired=False;p.poll.return_value=None;p.wait.return_value=0
  with mock.patch.object(M.os,'getpgid',side_effect=ProcessLookupError()),mock.patch.object(M.os,'killpg') as kill,mock.patch.object(M,'session_members',return_value=[]):
   with self.assertRaisesRegex(M.Error,'unreaped direct-child identity unavailable'):M.retire_process(p,{'stdout_data':bytearray(),'stderr_data':bytearray()})
  kill.assert_not_called()
 def test_pidfd_failure_fails_closed_without_numeric_group_signal(self):
  p=self.anchored();row=self.member()
  with mock.patch.object(M,'session_members',return_value=[row]),mock.patch.object(M,'pidfd_open',side_effect=M.Error('pidfd unavailable')),mock.patch.object(M.os,'killpg') as kill,mock.patch.object(M,'pidfd_identity',return_value=77),mock.patch.object(M,'proc_row',side_effect=self.row),mock.patch.object(M.os,'close'),mock.patch.object(M,'KILL_TIMEOUT',0):
   with self.assertRaisesRegex(M.Error,'pidfd unavailable'):M.retire_process(p,{'stdout_data':bytearray(),'stderr_data':bytearray()})
  kill.assert_not_called()
 def test_atomic_pass_status_fsync_failure_leaves_no_canonical_pass(self):
  with tempfile.TemporaryDirectory() as d:
   out=self.output(d);real=M.os.fsync;seen=[]
   def fail_dir(fd):
    seen.append(fd)
    if len(seen)>=3:raise OSError('injected dir fsync')
    return real(fd)
   try:
    with mock.patch.object(M.os,'fsync',side_effect=fail_dir):
     with self.assertRaises(OSError):M.status(out,{'status':'PASS'},success=True)
    self.assertFalse(out.exists('packet.status'))
   finally:out.close()
 def test_real_leader_exit_descendant_survival_is_retired_by_pidfd(self):
  if not Path('/proc').is_dir():self.skipTest('Linux proc required')
  p=M.bind_process(subprocess.Popen([sys.executable,'-c','import subprocess; subprocess.Popen(["/bin/sleep","30"])'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True))
  deadline=time.monotonic()+5
  while M.observe_exit(p) is None and time.monotonic()<deadline:time.sleep(.01)
  self.assertEqual(M.observe_exit(p),0);self.assertIsNone(p.returncode)
  M.retire_process(p,{'stdout':p.stdout,'stderr':p.stderr,'stdout_data':bytearray(),'stderr_data':bytearray()})
  self.assertEqual(M.session_members(p._mckernel_session),[])
  p.stdout.close();p.stderr.close()
 def test_fast_start_new_session_exit_is_admitted_and_censused(self):
  p=subprocess.Popen(['/bin/true'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True)
  time.sleep(.05);M.bind_process(p)
  self.assertEqual(M.observe_exit(p),0);self.assertEqual(M.complete_process(p),0)
  self.assertEqual(M.session_members(p._mckernel_session),[])
  p.stdout.close();p.stderr.close()
 def test_reused_sid_rejects_replacement_leader_and_members_without_signals(self):
  for fd_pid in (77,-1):
   p=self.anchored();replacement=dict(self.leader(),starttime=10)
   with mock.patch.object(M,'pidfd_identity',return_value=fd_pid),mock.patch.object(M,'proc_row',return_value=replacement),mock.patch.object(M,'session_members',return_value=[replacement,self.member()]),mock.patch.object(M,'pidfd_send') as send,mock.patch.object(M.os,'killpg') as kill,mock.patch.object(M.os,'close') as close:
    with self.assertRaisesRegex(M.Error,'session incarnation'):M.retire_process(p,{})
   send.assert_not_called();kill.assert_not_called();close.assert_called_once_with(11)
   self.assertFalse(p._mckernel_retired);self.assertIsNone(p._mckernel_leader_fd)
 def test_leader_first_exit_uses_anchor_and_reaps_only_after_descendants(self):
  p=self.anchored();events=[]
  def census(unused):
   events.append('census')
   return [] if 'reap' in events else ([self.leader()] if 'kill' in events else [self.leader(),self.member()])
  def send(fd,sig):events.append('kill' if sig==M.signal.SIGKILL else 'term')
  def reap(**kw):events.append('reap');return 0
  p.wait.side_effect=reap
  with mock.patch.object(M,'pidfd_identity',return_value=77),mock.patch.object(M,'proc_row',side_effect=self.row),mock.patch.object(M,'session_members',side_effect=census),mock.patch.object(M,'observe_exit',return_value=0),mock.patch.object(M,'pidfd_open',return_value=12),mock.patch.object(M,'pidfd_send',side_effect=send),mock.patch.object(M.os,'close') as close:
   M.retire_process(p,{})
  self.assertLess(events.index('kill'),events.index('reap'));self.assertTrue(p._mckernel_retired);close.assert_any_call(11)
  with mock.patch.object(M,'session_members',side_effect=AssertionError('retirement must not repeat')):M.retire_process(p,{})
 def test_bind_primary_cleanup_tree_survives_reader_and_terminal_json(self):
  p=self.proc();p.pid=321
  with mock.patch.object(M.subprocess,'Popen',return_value=p),mock.patch.object(M,'bind_process',side_effect=M.Interrupted('bind interrupted')),mock.patch.object(M,'retire_process',side_effect=M.Error('cleanup uncertain')):
   with self.assertRaises(M.CompositeInterrupted) as raised:M._reader(M.GIT)
  with tempfile.TemporaryDirectory() as d:
   base=self.output(d)
   try:
    M.fail_status(base,raised.exception);record=M.exact_json((base.path/'packet.failure').read_bytes())
    self.assertEqual(record['schema'],'mckernel.packet-failure.v2');self.assertEqual(record['status'],'FAIL')
    self.assertEqual(record['error']['primary']['message'],'bind interrupted');self.assertEqual(record['error']['cleanup']['message'],'cleanup uncertain');self.assertTrue(record['error']['interrupted'])
   finally:base.close()
 def test_blob_primary_wait_interrupt_retires_and_preserves_both(self):
  for invoke in (lambda:M.stream_blob(M.GIT,'0'*40,'a'*64,3),lambda:M.stream_store(M.GIT,[('0'*40,'a'*64,3,'b'*64)])):
   p=self.proc();p._mckernel_reader_finished=False
   p.wait.side_effect=M.Interrupted('wait interrupted')
   def retired(*args):p._mckernel_retired=True;return b'',b''
   with mock.patch.object(M,'_reader',return_value=p),mock.patch.object(M,'stream_blob_process',side_effect=M.Error('blob failed')),mock.patch.object(M,'retire_process',side_effect=retired) as cleanup:
    with self.assertRaises(M.Error) as raised:invoke()
   cleanup.assert_called_once();record=M.error_record(raised.exception)
   self.assertEqual(record['message'],'blob failed')
   self.assertTrue(p.stdout.closed);self.assertTrue(p.stderr.closed)
 def test_wait_census_and_drain_errors_do_not_abort_kill_escalation(self):
  for failure in (RuntimeError('wait defect'),M.Interrupted('wait signal'),KeyboardInterrupt('wait keyboard')):
   p=self.proc();p.wait.side_effect=failure
   with mock.patch.object(M,'retire_process',side_effect=M.Error('retirement uncertainty')) as cleanup:
    with self.assertRaises(M.CompositeError) as raised:M.finish_reader(p)
   cleanup.assert_called_once();self.assertIn(str(failure),str(raised.exception));self.assertIn('retirement uncertainty',str(raised.exception))
  for stage in ('census','drain'):
   p=self.anchored();signals=[]
   rows=[RuntimeError('census defect'),[self.member()],[self.member()],[self.leader()],[]] if stage=='census' else [[self.member()],[self.member()],[self.member()],[self.leader()],[]]
   with mock.patch.object(M,'pidfd_identity',return_value=77),mock.patch.object(M,'proc_row',side_effect=self.row),mock.patch.object(M,'session_members',side_effect=rows),mock.patch.object(M,'observe_exit',return_value=0),mock.patch.object(M,'pidfd_open',return_value=12),mock.patch.object(M,'pidfd_send',side_effect=lambda fd,sig:signals.append(sig)),mock.patch.object(M,'_drain',side_effect=RuntimeError('drain defect') if stage=='drain' else None,return_value=(b'',b'')),mock.patch.object(M.os,'close'):
    with self.assertRaisesRegex(RuntimeError if stage=='census' else M.CompositeError,stage+' defect'):M.retire_process(p,{})
   self.assertIn(M.signal.SIGKILL,signals);self.assertTrue(p._mckernel_retired)
 def test_closed_pipes_and_repeated_interrupts_do_not_block_escalation(self):
  p=self.anchored();p.stdout.close();p.stderr.close();signals=[];attempts=[]
  def send(fd,sig):
   attempts.append(sig)
   if len(attempts) in (1,2,4,5):raise M.Interrupted('repeated signal')
   signals.append(sig)
  with mock.patch.object(M,'pidfd_identity',return_value=77),mock.patch.object(M,'proc_row',side_effect=self.row),mock.patch.object(M,'session_members',side_effect=[[self.member()],[self.member()],[self.member()],[self.leader()],[]]),mock.patch.object(M,'observe_exit',return_value=0),mock.patch.object(M,'pidfd_open',return_value=12),mock.patch.object(M,'pidfd_send',side_effect=send),mock.patch.object(M.os,'close'):
   with self.assertRaises(M.Interrupted):M.retire_process(p,M.process_streams(p))
  self.assertEqual(signals,[M.signal.SIGTERM,M.signal.SIGKILL]);self.assertTrue(p._mckernel_retired);self.assertEqual(len(attempts),6)
 def test_member_esrch_does_not_signal_replacement_and_still_proves_empty(self):
  p=self.anchored()
  with mock.patch.object(M,'pidfd_identity',return_value=77),mock.patch.object(M,'proc_row',side_effect=self.row),mock.patch.object(M,'session_members',side_effect=[[self.member()],[self.leader()],[]]),mock.patch.object(M,'observe_exit',return_value=0),mock.patch.object(M,'pidfd_open',side_effect=FileNotFoundError('member exited')),mock.patch.object(M,'pidfd_send') as send,mock.patch.object(M.os,'close'):
   M.retire_process(p,{})
  send.assert_not_called();self.assertTrue(p._mckernel_retired)
 def test_capture_failure_keeps_primary_and_cleanup_tree(self):
  p=self.proc();p.pid=321
  with mock.patch.object(M.subprocess,'Popen',return_value=p),mock.patch.object(M,'bind_process',side_effect=M.Error('bind failed')),mock.patch.object(M,'retire_process',side_effect=M.Error('cleanup failed')),mock.patch.object(M,'capture',side_effect=OSError('capture failed')):
   with self.assertRaises(M.CompositeError) as raised:M.call(['x'],None,'observer')
  record=M.error_record(raised.exception)
  self.assertEqual(record['primary']['primary']['message'],'bind failed');self.assertEqual(record['primary']['cleanup']['message'],'cleanup failed');self.assertEqual(record['cleanup']['message'],'capture failed')
 def test_actual_packet_signal_handlers_latch_until_retired_then_restore(self):
  p=self.anchored();old={sig:M.signal.getsignal(sig) for sig in (M.signal.SIGINT,M.signal.SIGTERM)};signals=[]
  def send(fd,sig):
   signals.append(sig)
   for unused in range(50):
    for incoming in old:M.signal.getsignal(incoming)(incoming,None)
  with mock.patch.object(M,'pidfd_identity',return_value=77),mock.patch.object(M,'proc_row',side_effect=self.row),mock.patch.object(M,'session_members',side_effect=[[self.member()],[self.member()],[self.member()],[self.leader()],[]]),mock.patch.object(M,'observe_exit',return_value=0),mock.patch.object(M,'pidfd_open',return_value=12),mock.patch.object(M,'pidfd_send',side_effect=send),mock.patch.object(M.os,'close'):
   with self.assertRaises(M.CompositeInterrupted) as raised:M.retire_process(p,{})
  self.assertEqual(signals,[M.signal.SIGTERM,M.signal.SIGKILL]);self.assertTrue(p._mckernel_retired)
  self.assertIn('additional retirement interruptions: 199',str(raised.exception));M.json.dumps(M.error_record(raised.exception))
  self.assertEqual({sig:M.signal.getsignal(sig) for sig in old},old)
 def test_pipe_close_failure_cannot_replace_bind_or_retirement_failures(self):
  p=self.proc();p.pid=321;p.stdout=mock.Mock();p.stdout.close.side_effect=[M.Interrupted('close interrupted'),None]
  p.stderr=mock.Mock();p.stderr.close.side_effect=OSError('close failed')
  with mock.patch.object(M.subprocess,'Popen',return_value=p),mock.patch.object(M,'bind_process',side_effect=M.Error('bind failed')),mock.patch.object(M,'retire_process',side_effect=M.Error('retirement failed')):
   with self.assertRaises(M.CompositeInterrupted) as raised:M.run_bounded(['x'])
  for message in ('bind failed','retirement failed','close interrupted','close failed'):self.assertIn(message,str(raised.exception))
  self.assertEqual(p.stdout.close.call_count,2);p.stderr.close.assert_called_once()
 def test_partial_bind_proc_permission_failure_retires_real_child_itself(self):
  children=[];calls=[];real_popen=M.subprocess.Popen;real_row=M.proc_row
  def spawn(*args,**kwargs):
   child=real_popen(*args,**kwargs);children.append(child);return child
  def row(pid):
   if pid==os.getpid():return real_row(pid)
   calls.append(pid)
   if len(calls)==1:raise PermissionError('one partial bind failure')
   return real_row(pid)
  with mock.patch.object(M.subprocess,'Popen',side_effect=spawn),mock.patch.object(M,'proc_row',side_effect=row):
   with self.assertRaisesRegex(M.Error,'one partial bind failure'):M.run_bounded(['/bin/sleep','30'])
  self.assertEqual(len(children),1);child=children[0]
  self.assertGreater(len(calls),1);self.assertIn(child.returncode,(-M.signal.SIGTERM,-M.signal.SIGKILL))
  self.assertTrue(child._mckernel_retired);self.assertIsNone(child._mckernel_leader_fd)
  self.assertEqual(M.session_members(child.pid),[]);self.assertTrue(child.stdout.closed);self.assertTrue(child.stderr.closed)
 def test_partial_bind_recovery_rejects_pidfd_or_leader_replacement(self):
  for identities,rows in (([88],[]),([77,88],[self.leader(),self.leader()]),([77],[self.leader(),dict(self.leader(),starttime=10)])):
   p=self.anchored();p._mckernel_leader_starttime=None
   with mock.patch.object(M,'pidfd_identity',side_effect=identities),mock.patch.object(M,'proc_row',side_effect=rows):
    with self.assertRaises(M.Error):M.recover_anchor(p)
   self.assertIsNone(p._mckernel_leader_starttime)
 def test_close_anchor_retries_only_same_identity_and_retains_error(self):
  for error in (M.Interrupted('close interrupted'),InterruptedError('close EINTR')):
   p=self.anchored()
   with mock.patch.object(M,'pidfd_identity',side_effect=[77,77]),mock.patch.object(M,'pidfd_token',return_value=(1,2)),mock.patch.object(M,'proc_row',side_effect=self.row),mock.patch.object(M.os,'close',side_effect=[error,None]) as close:
    with self.assertRaises(type(error)):M.close_anchor(p)
   self.assertEqual(close.call_args_list,[mock.call(11),mock.call(11)]);self.assertIsNone(p._mckernel_leader_fd)
 def test_close_anchor_absence_after_error_proves_closed_without_retry(self):
  p=self.anchored()
  with mock.patch.object(M,'pidfd_identity',side_effect=[77,FileNotFoundError('closed')]),mock.patch.object(M.os,'close',side_effect=M.Interrupted('close interrupted')) as close:
   with self.assertRaises(M.Interrupted):M.close_anchor(p)
  close.assert_called_once_with(11);self.assertIsNone(p._mckernel_leader_fd)
 def test_close_anchor_replacement_never_closes_reused_slot(self):
  p=self.anchored()
  with mock.patch.object(M,'pidfd_identity',side_effect=[77,88]),mock.patch.object(M.os,'close',side_effect=M.Interrupted('close interrupted')) as close:
   with self.assertRaisesRegex(M.CompositeInterrupted,'descriptor identity changed'):M.close_anchor(p)
  close.assert_called_once_with(11);self.assertIsNone(p._mckernel_leader_fd)
 def test_close_anchor_reaped_or_replaced_object_refuses_ambiguous_retry(self):
  for identity,token in ((-1,(1,2)),(77,(1,3))):
   p=self.anchored()
   with mock.patch.object(M,'pidfd_identity',return_value=identity),mock.patch.object(M,'pidfd_token',return_value=token),mock.patch.object(M.os,'close',side_effect=M.Interrupted('close interrupted')) as close:
    with self.assertRaisesRegex(M.CompositeInterrupted,'uncertain pidfd close'):M.close_anchor(p)
   close.assert_called_once_with(11);self.assertEqual(p._mckernel_leader_fd,11)
 def test_spawn_preflight_rejects_ignored_sigchld_before_popen(self):
  with mock.patch.object(M.signal,'getsignal',return_value=M.signal.SIG_IGN),mock.patch.object(M.subprocess,'Popen') as popen:
   with self.assertRaisesRegex(M.Error,'default SIGCHLD'):M.run_bounded(['x'])
  popen.assert_not_called()
 def execute_failure_record(self,lease_errors=False,final_errors=False):
  with tempfile.TemporaryDirectory() as d:
   path=Path(d)/'lease';M.BUILD_LEASE=path;base=self.output(d)
   r={'operational_exclusion':str(path),'boot_id':'b','exclusion_tombstone':self.tomb(path),'docker':{}}
   lease=M.ExclusionLease(r);observer=os.open('/dev/null',os.O_RDONLY);armed={};real_fsync=M.os.fsync;real_close=M.os.close;real_signal=M.signal.signal;real_output_close=base.close
   previous={sig:M.signal.getsignal(sig) for sig in (M.signal.SIGINT,M.signal.SIGTERM)}
   class H:
    def remove_root(self,*args):pass
    def retire(self,*args,**kwargs):armed['fd']=lease.fd;raise M.Error('helper primary')
   def fsync(fd):
    if lease_errors and armed.get('fd')==fd and not armed.get('fsync'):
     armed['fsync']=True;raise OSError('lease fsync cleanup')
    return real_fsync(fd)
   def close(fd):
    real_close(fd)
    if lease_errors and armed.get('fd')==fd and not armed.get('close'):
     armed['close']=True;raise OSError('lease close cleanup')
   def restore(sig,handler):
    real_signal(sig,handler)
    if final_errors and armed and handler==previous[sig]:raise M.Interrupted('signal restore cleanup '+str(int(sig)))
   def output_close():
    real_output_close()
    if final_errors:raise OSError('output close cleanup')
   with mock.patch.object(M,'admit',return_value=(r,{})),mock.patch.object(M,'fresh_output',return_value=base),mock.patch.object(M,'ExclusionLease',return_value=lease),mock.patch.object(M,'live_gate'),mock.patch.object(M,'helper',return_value=(H(),observer)),mock.patch.object(M,'proc_starttime',return_value=7),mock.patch.object(M.os,'fsync',side_effect=fsync),mock.patch.object(M.os,'close',side_effect=close),mock.patch.object(M.signal,'signal',side_effect=restore),mock.patch.object(base,'close',side_effect=output_close):
    with self.assertRaises(M.CompositeError) as raised:M.execute('ignored')
   record=M.exact_json((base.path/'packet.failure').read_bytes())
   self.assertFalse((base.path/'packet.status').exists());self.assertEqual(record['error'],M.error_record(raised.exception));self.assertIsNone(base.fd);self.assertIsNone(base.parent_fd);self.assertIsNone(lease.fd)
   self.assertEqual({sig:M.signal.getsignal(sig) for sig in previous},previous)
   return record
 def test_execute_helper_primary_lease_fsync_close_all_in_terminal_json(self):
  record=self.execute_failure_record(lease_errors=True)
  self.assertEqual(record['error']['primary']['message'],'helper primary')
  self.assertEqual(record['error']['cleanup']['primary']['message'],'lease fsync cleanup')
  self.assertEqual(record['error']['cleanup']['cleanup']['message'],'lease close cleanup')
 def test_execute_primary_signal_restore_and_output_close_all_in_terminal_json(self):
  record=self.execute_failure_record(final_errors=True)
  self.assertTrue(record['error']['interrupted']);self.assertEqual(record['error']['cleanup']['message'],'output close cleanup')
  serialized=M.json.dumps(record,sort_keys=True)
  for message in ('helper primary','signal restore cleanup 2','signal restore cleanup 15','output close cleanup'):self.assertIn(message,serialized)
 def spawn_gap_case(self,kind,mode):
  real_spawn=M.subprocess.Popen;real_mask=M.signal.pthread_sigmask;real_streams=M.process_streams;children=[];restore_calls=[];parent=os.getpid()
  old_mask=real_mask(M.signal.SIG_BLOCK,[]);previous=M.signal.getsignal(M.signal.SIGTERM)
  def interrupted(signum,frame):raise M.Interrupted('pending termination')
  def spawn(argv,**kwargs):
   child=real_spawn(['/bin/sleep','30'],**kwargs);children.append(child);return child
  def streams(child):
   self.assertEqual(child._mckernel_session,child.pid);self.assertIsInstance(child._mckernel_leader_starttime,int)
   self.assertTrue({M.signal.SIGTERM,M.signal.SIGINT}.issubset(real_mask(M.signal.SIG_BLOCK,[])))
   if mode=='pending':os.kill(parent,M.signal.SIGTERM);return real_streams(child)
   raise M.Interrupted('stream capture primary')
  def mask(how,values):
   if mode=='restore' and os.getpid()==parent and how==M.signal.SIG_SETMASK:
    restore_calls.append(how)
    if len(restore_calls)<=3:raise OSError('mask restoration cleanup')
   return real_mask(how,values)
  M.signal.signal(M.signal.SIGTERM,interrupted)
  try:
   with tempfile.TemporaryDirectory() as d:
    base=self.output(d)
    try:
     with mock.patch.object(M.subprocess,'Popen',side_effect=spawn),mock.patch.object(M,'process_streams',side_effect=streams),mock.patch.object(M.signal,'pthread_sigmask',side_effect=mask):
      with self.assertRaises(M.Interrupted) as raised:
       if kind=='run':M.run_bounded(['ignored'])
       elif kind=='reader':M._reader(M.GIT)
       else:M.call(['ignored'],base,'observer')
     text=M.json.dumps(M.error_record(raised.exception))
     self.assertIn('pending termination' if mode=='pending' else 'stream capture primary',text)
     if mode=='restore':self.assertIn('mask restoration cleanup',text);self.assertGreaterEqual(len(restore_calls),4)
    finally:base.close()
   self.assertEqual(len(children),1);child=children[0]
   self.assertTrue(child._mckernel_retired);self.assertIn(child.returncode,(-M.signal.SIGTERM,-M.signal.SIGKILL));self.assertIsNone(child._mckernel_leader_fd)
   self.assertEqual(M.session_members(child.pid),[]);self.assertTrue(child.stdout.closed);self.assertTrue(child.stderr.closed)
   if child.stdin is not None:self.assertTrue(child.stdin.closed)
   self.assertEqual(real_mask(M.signal.SIG_BLOCK,[]),old_mask)
  finally:real_mask(M.signal.SIG_SETMASK,old_mask);M.signal.signal(M.signal.SIGTERM,previous)
 def test_each_spawn_stream_capture_gap_retires_real_owned_child(self):
  for kind in ('run','reader','call'):
   with self.subTest(kind=kind):self.spawn_gap_case(kind,'capture')
 def test_each_spawn_pending_signal_retires_real_owned_child(self):
  for kind in ('run','reader','call'):
   with self.subTest(kind=kind):self.spawn_gap_case(kind,'pending')
 def test_each_spawn_mask_restoration_failure_preserves_primary_and_retires(self):
  for kind in ('run','reader','call'):
   with self.subTest(kind=kind):self.spawn_gap_case(kind,'restore')
 def test_spawn_mask_capability_and_wrong_thread_fail_before_popen(self):
  for patch in (mock.patch.object(M.signal,'pthread_sigmask',None),mock.patch.object(M.threading,'current_thread',return_value=object())):
   with patch,mock.patch.object(M.subprocess,'Popen') as popen:
    with self.assertRaisesRegex(M.Error,'single main thread and pthread_sigmask'):M.run_bounded(['ignored'])
   popen.assert_not_called()
 def test_loaded_helper_composite_all_leaves_reach_terminal_failure_json(self):
  with tempfile.TemporaryDirectory() as d:
   base=self.output(d);helper,observer=M.helper(base,{'helper':M.HELPER.read_bytes(),'archive':M.ARCHIVE.read_bytes(),'observer':b'# never executed\n'})
   journal=mock.Mock();journal.write.side_effect=[ValueError('operation primary'),OSError('failure journal error')];journal.close.side_effect=OSError('journal close error')
   try:
    with mock.patch.object(helper,'release_roots',return_value=[]),mock.patch.object(helper,'survivors',return_value={}),mock.patch.object(helper,'Journal',return_value=journal):
     with self.assertRaises(helper.RetirementCompositeError) as raised:helper.retire([],{},'claim-704f6654-1.json','journal-704f6654-1.jsonl','evidence-704f6654-1.json',None,None,output_dir_fd=base.fd)
    error=raised.exception;M.fail_status(base,error);record=M.exact_json((base.path/'packet.failure').read_bytes())
    self.assertEqual(record['error'],helper.failure_record(error));self.assertEqual(record['error']['primary']['primary']['message'],'operation primary');self.assertEqual(record['error']['primary']['cleanup']['message'],'failure journal error');self.assertEqual(record['error']['cleanup']['message'],'journal close error')
    error.primary=error;self.assertIn('FailureTreeCycle',M.json.dumps(M.error_record(error)))
   finally:os.close(observer);base.close()
 def early_owner_case(self,kind,mode):
  real_spawn=M.subprocess.Popen;real_open=M.pidfd_open;real_born=M.born_process;parent=os.getpid();children=[];child_opens=[];raw_owners=[]
  real_owner=M.spawn_owner;original_mask=M.signal.pthread_sigmask(M.signal.SIG_BLOCK,[])
  def owner():
   value=real_owner();raw_owners.append(value);return value
  def spawn(argv,**kwargs):
   child=real_spawn(['/bin/sleep','30'],**kwargs);children.append(child);return child
  def born(child):
   if mode=='born':
    record=raw_owners[0]
    self.assertIs(record['p'],child);self.assertEqual(record['pid'],child.pid);self.assertEqual(record['session'],child.pid)
    self.assertIs(record['streams']['stdout'],child.stdout);self.assertIs(record['streams']['stderr'],child.stderr)
    self.assertTrue({M.signal.SIGINT,M.signal.SIGTERM}.issubset(M.signal.pthread_sigmask(M.signal.SIG_BLOCK,[])))
    raise M.Interrupted('born decoration primary')
   return real_born(child)
  def pidfd(pid):
   if pid!=parent:
    child_opens.append(pid)
    if mode=='permanent' or mode=='transient' and len(child_opens)==1:raise M.Error('child pidfd acquisition '+mode)
   return real_open(pid)
  with tempfile.TemporaryDirectory() as d:
   base=self.output(d)
   try:
    with mock.patch.object(M,'spawn_owner',side_effect=owner),mock.patch.object(M.subprocess,'Popen',side_effect=spawn),mock.patch.object(M,'born_process',side_effect=born),mock.patch.object(M,'pidfd_open',side_effect=pidfd),mock.patch.object(M.os,'killpg') as group_signal:
     with self.assertRaises(M.Error) as raised:
      if kind=='run':M.run_bounded(['ignored'])
      elif kind=='reader':M._reader(M.GIT)
      else:M.call(['ignored'],base,'observer')
    group_signal.assert_not_called();error=M.error_record(raised.exception);text=M.json.dumps(error)
    self.assertIn('born decoration primary' if mode=='born' else 'child pidfd acquisition '+mode,text)
    if mode=='transient':self.assertGreaterEqual(len(child_opens),2)
    if mode=='permanent':
     self.assertEqual(len(child_opens),4);self.assertIn('uncertain pidfd cleanup',text);self.assertIn('pidfd fallback outcome',text)
     def leaves(value):return leaves(value['primary'])+leaves(value['cleanup']) if 'primary' in value else [value.get('message','')]
     outcome=next(message for message in leaves(error) if message.startswith('pidfd fallback outcome: '));evidence=M.json.loads(outcome.split(': ',1)[1])
     self.assertTrue(evidence['retired']);self.assertEqual(evidence['observed_numeric_session_members'],[])
     M.fail_status(base,raised.exception);self.assertEqual(M.exact_json((base.path/'packet.failure').read_bytes())['error'],error)
    self.assertEqual(len(children),1);child=children[0]
    self.assertIn(child.returncode,(-M.signal.SIGTERM,-M.signal.SIGKILL));self.assertTrue(child._mckernel_retired);self.assertIsNone(child._mckernel_leader_fd)
    self.assertEqual(M.session_members(child.pid),[]);self.assertTrue(child.stdout.closed);self.assertTrue(child.stderr.closed)
    if child.stdin is not None:self.assertTrue(child.stdin.closed)
    self.assertEqual(M.signal.pthread_sigmask(M.signal.SIG_BLOCK,[]),original_mask)
   finally:base.close()
 def test_each_born_decoration_failure_consumes_raw_owner_and_reaps_child(self):
  for kind in ('run','reader','call'):
   with self.subTest(kind=kind):self.early_owner_case(kind,'born')
 def test_each_first_child_pidfd_failure_is_reacquired_and_reaped(self):
  for kind in ('run','reader','call'):
   with self.subTest(kind=kind):self.early_owner_case(kind,'transient')
 def test_each_permanent_child_pidfd_failure_records_uncertainty_and_leak_census(self):
  for kind in ('run','reader','call'):
   with self.subTest(kind=kind):self.early_owner_case(kind,'permanent')
 def test_pidfd_self_preflight_fails_before_spawn_and_restores_mask(self):
  previous=M.signal.pthread_sigmask(M.signal.SIG_BLOCK,[])
  with mock.patch.object(M,'pidfd_open',side_effect=M.Error('no pidfd capability')) as opened,mock.patch.object(M.subprocess,'Popen') as spawn:
   with self.assertRaisesRegex(M.Error,'no pidfd capability'):M.run_bounded(['ignored'])
  opened.assert_called_once_with(os.getpid());spawn.assert_not_called();self.assertEqual(M.signal.pthread_sigmask(M.signal.SIG_BLOCK,[]),previous)
 def test_pidfd_self_preflight_identity_failure_closes_probe_without_spawning(self):
  for broken in (mock.patch.object(M,'pidfd_identity',return_value=os.getpid()+1),mock.patch.object(M,'pidfd_identity',side_effect=PermissionError('self fdinfo denied'))):
   before=len(list(Path('/proc/self/fd').iterdir()));mask=M.signal.pthread_sigmask(M.signal.SIG_BLOCK,[])
   with broken,mock.patch.object(M.subprocess,'Popen') as spawn:
    with self.assertRaises(M.Error):M.run_bounded(['ignored'])
   spawn.assert_not_called();self.assertEqual(len(list(Path('/proc/self/fd').iterdir())),before);self.assertEqual(M.signal.pthread_sigmask(M.signal.SIG_BLOCK,[]),mask)
 def test_reacquire_or_numeric_fallback_never_adopts_reaped_replacement(self):
  p=self.anchored();p._mckernel_leader_fd=None
  with mock.patch.object(M.os,'waitid',side_effect=ChildProcessError('already reaped')),mock.patch.object(M,'proc_row',return_value=dict(self.leader(),starttime=10)),mock.patch.object(M,'pidfd_open') as opened,mock.patch.object(M.os,'kill') as sent,mock.patch.object(M,'session_members',return_value=[]):
   with self.assertRaisesRegex(M.Error,'unreaped direct-child identity unavailable'):M.retire_process(p,{})
  opened.assert_not_called();sent.assert_not_called();self.assertFalse(p._mckernel_retired)
 def test_inventory_validates_symlink_and_all_records_before_any_reader_spawn(self):
  common={'classification':'reconstructible','gid':1000,'mode':0o644,'root':'candidate','uid':1000}
  regular=dict(common,type='regular',path='main-file',size=3,sha256=hashlib.sha256(b'abc').hexdigest(),git_oids={'sha1':'0'*40,'sha256':'1'*64})
  link=dict(common,type='symlink',path='ihk/link',size=3,target='abc',git_oids={'sha1':'2'*40,'sha256':'3'*64})
  entries=[dict(regular,path='main-%d'%i) for i in range(7715)]+[dict(link,path='ihk/link-%d'%i) for i in range(1296)]
  with mock.patch.object(M,'stream_store') as streams:M.verify_inventory({'revisions':{'main':M.MAIN,'ihk':M.IHK},'entries':entries})
  self.assertEqual([len(x.args[1]) for x in streams.call_args_list],[7715,1296])
  bad=dict(link,target='\udcff')
  with self.assertRaises(M.Error):M.verify_inventory({'revisions':{'main':M.MAIN,'ihk':M.IHK},'entries':entries[:-1]+[bad]})
  streams.assert_has_calls([])
  capsule=dict(regular,classification='capsule-required',path='capsule-large',size=M.MAX_FILE+1)
  with mock.patch.object(M,'stream_store') as streams:M.verify_inventory({'revisions':{'main':M.MAIN,'ihk':M.IHK},'entries':entries+[capsule]})
  self.assertEqual([len(x.args[1]) for x in streams.call_args_list],[7715,1296])
  with self.assertRaisesRegex(M.Error,'inventory metadata'):
   M.verify_inventory({'revisions':{'main':M.MAIN,'ihk':M.IHK},'entries':entries+[dict(capsule,size=M.MAX_BLOB+1)]})
 def test_inventory_rejects_malformed_digest_oid_and_record_shape_before_spawn(self):
  common={'classification':'reconstructible','gid':1000,'mode':0o644,'root':'candidate','uid':1000,'type':'regular','path':'x','size':3,'sha256':'a'*64,'git_oids':{'sha1':'0'*40,'sha256':'1'*64}}
  for change in (dict(common,sha256='bad'),dict(common,git_oids={'sha1':'bad','sha256':'1'*64}),dict(common,extra=1),dict(common,size=-1)):
   with mock.patch.object(M,'stream_store') as streams:
    with self.assertRaises(M.Error):M.verify_inventory({'revisions':{'main':M.MAIN,'ihk':M.IHK},'entries':[change]})
    streams.assert_not_called()
 def test_stream_blob_requires_requested_git_sha1_and_sha256_objects(self):
  data=b'abc';oid=hashlib.sha1(b'blob 3\0'+data).hexdigest();oid256=hashlib.sha256(b'blob 3\0'+data).hexdigest();digest=hashlib.sha256(data).hexdigest()
  class P:
   def __init__(self,raw):self.stdin=io.BytesIO();self.stdout=io.BytesIO(raw);self.stderr=io.BytesIO()
  M.stream_blob_process(P((oid+' blob 3\n').encode()+data+b'\n'),oid,digest,3,oid256,time.monotonic()+1)
  with self.assertRaisesRegex(M.Error,'blob digest/object id'):
   M.stream_blob_process(P(('0'*40+' blob 3\n').encode()+data+b'\n'),'0'*40,digest,3,oid256,time.monotonic()+1)
 def test_reader_primary_failure_retires_eof_waiting_child_without_natural_wait(self):
  p=subprocess.Popen([sys.executable,'-c','import sys;sys.stdin.read()'],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True)
  try:
   M.bind_process(p);p._mckernel_reader_primary=M.Error('injected record failure');started=time.monotonic()
   with self.assertRaises(M.Error):M.finish_reader(p)
   self.assertLess(time.monotonic()-started,2);self.assertTrue(p._mckernel_retired);self.assertTrue(p.stdin.closed);self.assertTrue(p.stdout.closed);self.assertTrue(p.stderr.closed)
  finally:
   if p.poll() is None:p.kill()
   try:p.wait(timeout=2)
   except subprocess.TimeoutExpired:pass
 def test_reader_primary_stdin_close_and_retirement_failures_are_both_composite(self):
  p=self.anchored();p.stdin=mock.Mock();p.stdin.close.side_effect=OSError('stdin close failed');p.stdout=io.BytesIO();p.stderr=io.BytesIO();p._mckernel_reader_primary=M.Error('record failed')
  with mock.patch.object(M,'cleanup_process',return_value=((b'',b''),M.Error('retirement failed'))):
   with self.assertRaises(M.CompositeError) as raised:M.finish_reader(p)
  tree=M.error_record(raised.exception)
  messages=[]
  def walk(x):
   messages.append(x.get('message',''))
   for key in ('primary','cleanup'):
    if key in x:walk(x[key])
  walk(tree);self.assertIn('record failed',messages);self.assertIn('stdin close failed',messages);self.assertIn('retirement failed',messages);self.assertTrue(p.stdout.closed);self.assertTrue(p.stderr.closed)
 def test_reader_nonzero_exit_retains_both_output_close_failures(self):
  for invoke in (lambda:M.stream_blob(M.GIT,'0'*40,'a'*64,3),lambda:M.stream_store(M.GIT,[('0'*40,'a'*64,3,'b'*64)])):
   p=self.proc();p._mckernel_reader_finished=False;p.stdout=mock.Mock();p.stderr=mock.Mock();p.stdin=mock.Mock()
   p.stdout.close.side_effect=OSError('stdout close failed');p.stderr.close.side_effect=OSError('stderr close failed')
   with mock.patch.object(M,'_reader',return_value=p),mock.patch.object(M,'stream_blob_process'),mock.patch.object(M,'finish_reader',return_value=7):
    with self.assertRaises(M.CompositeError) as raised:invoke()
   text=str(raised.exception);self.assertTrue('canonical reader exit' in text or 'blob reader exit' in text);self.assertIn('stdout close failed',text);self.assertIn('stderr close failed',text)
 def test_reader_embedded_primary_identity_is_not_duplicated(self):
  p=self.proc();p._mckernel_reader_finished=False;primary=M.Error('record identity')
  embedded=M.CompositeError(primary,M.Error('retirement identity'))
  with mock.patch.object(M,'_reader',return_value=p),mock.patch.object(M,'stream_blob_process',side_effect=primary),mock.patch.object(M,'finish_reader',side_effect=embedded):
   with self.assertRaises(M.CompositeError) as raised:M.stream_blob(M.GIT,'0'*40,'a'*64,3)
  record=M.error_record(raised.exception);self.assertEqual(record['primary']['message'],'record identity');self.assertEqual(record['cleanup']['message'],'retirement identity')
if __name__=='__main__':unittest.main()
