#!/usr/bin/env python3
"""Pure tests only; no roots, Docker, observer, Git, or candidate is touched."""
import hashlib, importlib.util, io, subprocess, tempfile, unittest
from pathlib import Path
from unittest import mock
ROOT=Path(__file__).parents[2]; PACKET=ROOT/'docs/verification/evidence/native-exact-candidate-retirement-67589154-1.py'
s=importlib.util.spec_from_file_location('retire_packet',str(PACKET));M=importlib.util.module_from_spec(s);s.loader.exec_module(M)
class T(unittest.TestCase):
 def setUp(self):self.old=(M.RELEASE_SHA256,M.HELPER_SHA256,M.OBSERVER_SHA256,M.HELPER_TEST_SHA256,M.OBSERVER_TEST_SHA256)
 def tearDown(self):M.RELEASE_SHA256,M.HELPER_SHA256,M.OBSERVER_SHA256,M.HELPER_TEST_SHA256,M.OBSERVER_TEST_SHA256=self.old
 def final(self):M.RELEASE_SHA256=M.HELPER_SHA256=M.OBSERVER_SHA256=M.HELPER_TEST_SHA256=M.OBSERVER_TEST_SHA256='a'*64
 def proc(self,out=b'',err=b'',rc=0):
  p=mock.Mock();p.communicate.return_value=(out,err);p.returncode=rc;return p
 def lease(self):
  class L:
   def assert_held(self):pass
  return L()
 def test_draft_no_side_effect(self):
  with mock.patch.object(M.os,'geteuid',side_effect=AssertionError),mock.patch.object(M,'gscalar',side_effect=AssertionError):
   with self.assertRaisesRegex(M.Error,'DRAFT_NOT_RELEASED'):M.execute('/x')
 def test_mechanical_single_replacement(self):
  raw=b"RELEASE_SHA256='RELEASE_HASH_REQUIRED'"
  self.assertEqual(M.final_bytes(raw,'a'*64),b"RELEASE_SHA256='"+b'a'*64+b"'")
  with self.assertRaises(M.Error):M.final_bytes(raw+raw,'a'*64)
 def test_exact_git_argv(self):
  self.assertEqual(M.gargv(M.GIT,'rev-parse','HEAD')[:4],['/usr/bin/git','--no-optional-locks','--git-dir=/home/holden/mckernel/.git','--work-tree=/home/holden/mckernel'])
  self.assertNotIn('-C',M.gargv(M.GIT,'x'));self.assertEqual(M.genv()['GIT_ASKPASS'],'/bin/false')
 def test_root_and_release_path_fail_closed(self):
  self.final()
  with mock.patch.object(M.os,'geteuid',return_value=1000):
   with self.assertRaisesRegex(M.Error,'root euid'):M.admit(M.SOURCE/M.RELEASE_PATH)
  with mock.patch.object(M.os,'geteuid',return_value=0):
   with self.assertRaisesRegex(M.Error,'canonical'):M.admit('/tmp/x')
 def test_stream_short_type_size_hash(self):
  class P:
   def __init__(self,b):self.stdin=io.BytesIO();self.stdout=io.BytesIO(b);self.stderr=io.BytesIO()
   def wait(self):return 0
   def poll(self):return 0
  oid='0'*40;d=hashlib.sha256(b'abc').hexdigest()
  with mock.patch.object(M.subprocess,'Popen',return_value=P((oid+' blob 3\n').encode()+b'abc\n')):M.stream_blob(M.GIT,oid,d,3)
  for raw in ((oid+' tree 3\n').encode()+b'abc\n',(oid+' blob 4\n').encode()+b'abc\n',(oid+' blob 3\n').encode()+b'ab'):
   with mock.patch.object(M.subprocess,'Popen',return_value=P(raw)):
    with self.assertRaises(M.Error):M.stream_blob(M.GIT,oid,d,3)
 def test_stream_stall_and_reader_reap_are_bounded(self):
  class F:
   def fileno(self):return 9
  with mock.patch.object(M.select,'select',return_value=([],[],[])),mock.patch.object(M.time,'monotonic',side_effect=[0,2]):
   with self.assertRaisesRegex(M.Error,'wall timeout'):M.pipe_read(F(),1,1)
  p=mock.Mock();p.wait.side_effect=[subprocess.TimeoutExpired(['x'],5),subprocess.TimeoutExpired(['x'],5),7]
  self.assertEqual(M.finish_reader(p),7);p.terminate.assert_called_once();p.kill.assert_called_once()
 def test_observer_exact_argv_capture_and_duplicate_json(self):
  self.final()
  with tempfile.TemporaryDirectory() as d:
   b=Path(d)
   lease=self.lease()
   with mock.patch.object(M.subprocess,'Popen',return_value=self.proc(b'{"x":1}')) as run:self.assertEqual(M.observer_callback(b,lease)(list(M.QUARANTINES),[[],[]]),{'x':1});self.assertEqual(run.call_args.args[0],['/usr/bin/python3','-E','-s','-B',str(M.OBSERVER),'--target',M.QUARANTINES[0],'--target',M.QUARANTINES[1]])
   self.assertTrue((b/'observer.stdout').exists())
  with tempfile.TemporaryDirectory() as d:
   with mock.patch.object(M.subprocess,'Popen',return_value=self.proc(b'{"x":1,"x":2}')):
    with self.assertRaisesRegex(M.Error,'duplicate JSON'):M.observer_callback(Path(d),self.lease())(list(M.QUARANTINES),[[],[]])
 def test_callback_failure_durable_and_docker_omission(self):
  self.final()
  with tempfile.TemporaryDirectory() as d:
   b=Path(d)
   with mock.patch.object(M.subprocess,'Popen',return_value=self.proc(b'o',b'e',3)):
    with self.assertRaisesRegex(M.Error,'observer callback failed'):M.observer_callback(b,self.lease())(list(M.QUARANTINES),[[],[]])
   self.assertEqual((b/'observer.stdout').read_bytes(),b'o')
  with tempfile.TemporaryDirectory() as d:
   i='a'*64;t={'decd7cf92467e1214cc955d15a00b847587ada37016f206e9a82019cbb72c6b9':{},'8943e49772f840ba5da6571c2e2c6fde60b61157f21f873d832669157ef9bc10':{}}
   rs=[mock.Mock(returncode=0,stdout=(i+'\n').encode(),stderr=b''),mock.Mock(returncode=0,stdout=b'[]',stderr=b'')]
   with mock.patch.object(M.subprocess,'Popen',side_effect=[self.proc(x.stdout,x.stderr,x.returncode) for x in rs]) as run:
    with self.assertRaisesRegex(M.Error,'omission/churn'):M.docker_callback(Path(d),{'terminal_containers':t},self.lease())()
    self.assertEqual(run.call_args_list[0].args[0],['/usr/bin/docker','ps','--all','--quiet','--no-trunc']);self.assertEqual(run.call_args_list[1].args[0],['/usr/bin/docker','inspect',i])
 def test_timeout_retires_one_process_group_and_keeps_captures(self):
  with tempfile.TemporaryDirectory() as d:
   p=mock.Mock();p.pid=123;p.returncode=-15;p.communicate.side_effect=[subprocess.TimeoutExpired(['x'],180,output=b'before',stderr=b'err'),(b'after',b'closed')]
   with mock.patch.object(M.subprocess,'Popen',return_value=p),mock.patch.object(M.os,'killpg') as kill:
    with self.assertRaisesRegex(M.Error,'observer callback failed'):M.call(['x'],Path(d),'observer')
    kill.assert_called_once_with(123,M.signal.SIGTERM)
   self.assertEqual((Path(d)/'observer.stdout').read_bytes(),b'after')
 def test_second_timeout_kills_and_reaps(self):
  with tempfile.TemporaryDirectory() as d:
   p=mock.Mock();p.pid=321;p.returncode=-9;p.communicate.side_effect=[subprocess.TimeoutExpired(['x'],180),subprocess.TimeoutExpired(['x'],5),(b'out',b'err')]
   with mock.patch.object(M.subprocess,'Popen',return_value=p),mock.patch.object(M.os,'killpg') as kill:
    with self.assertRaises(M.Error):M.call(['x'],Path(d),'observer')
    self.assertEqual(kill.call_args_list,[mock.call(321,M.signal.SIGTERM),mock.call(321,M.signal.SIGKILL)])
 def test_proc_permission_and_vanish_reconciliation(self):
  with mock.patch.object(M,'raw_starttime',return_value=7),mock.patch.object(Path,'read_bytes',side_effect=PermissionError('x')):
   with self.assertRaisesRegex(M.Error,'cmdline unreadable'):M.proc_cmdline_stable(1)
  with mock.patch.object(M,'raw_starttime',side_effect=[7,FileNotFoundError()]):
   with mock.patch.object(Path,'read_bytes',return_value=b'x\0'):
    with self.assertRaisesRegex(M.Error,'disappeared during census'):M.proc_cmdline_stable(1)
 def test_root_schema_has_no_path_and_carries_size(self):
  self.assertEqual(M.root(25166,9),{'device':26,'inode':25166,'uid':1000,'gid':1000,'mode':0o755,'kind':'directory','size':9})
 def test_full_helper_release_roots_accepts_inner_identity_schema(self):
  spec=importlib.util.spec_from_file_location('helper',str(M.HELPER));h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)
  with tempfile.TemporaryDirectory() as d:
   paths=[Path(d)/'candidate',Path(d)/'backup']
   for p in paths:p.mkdir()
   rows=[];mroots=[]
   for name,p,q in zip(('candidate','metadata-backup'),paths,('.qc','.qb')):
    inv=h.inventory_root(p);rows.append({'path':str(p),'root':inv['root'],'parent':h.root_identity(p.parent),'members':inv['members'],'quarantine_name':q,'quarantine_uid':0,'quarantine_gid':0,'quarantine_mode':0o700});i=inv['root'];mroots.append({'name':name,'path':str(p),'identity':{'dev':i['device'],'inode':i['inode'],'uid':i['uid'],'gid':i['gid'],'mode':i['mode']}})
   release={'schema':'mckernel.ordinary-retirement-release.v1','sealed':{k:'a'*64 for k in ('retention_manifest_sha256','retention_manifest_pushed_sha256','retention_manifest_fetched_sha256','capsule_sha256','capsule_pushed_sha256','capsule_fetched_sha256')},'operational_exclusion':'x','roots':rows}
   with mock.patch.object(h,'manifest_authority',return_value={'roots':mroots,'entries':[]}):self.assertEqual(len(h.release_roots(release,paths)),2)
 def test_live_gate_rejects_resource_before_mutation(self):
  r={'boot_id':'x','launcher_identities':[],'process_exclusions':['candidate'],'heavy_lease_paths':[],'output_dir':'/home/holden/mckernel-work/scratch/new'}
  with mock.patch.object(M,'free_bytes',return_value=0),mock.patch.object(M.os,'sysconf',return_value=0):
   with self.assertRaisesRegex(M.Error,'resource floor'):M.live_gate(r)
 def test_fresh_output_and_release_sentinel(self):
  with self.assertRaises(M.Error):M.fresh_output({'output_dir':'/tmp/no'})
  self.assertEqual(M.HELPER_SHA256,'2ba700743d01060b0d35114c3b4380cb9b25865d2d973ca05a3d83df3d38964e')
  self.assertEqual(M.OBSERVER_SHA256,'3562b1d3d4e9a1e09cb7fa2be30f8e320923d50cf628b7f42314318702653666')
  self.assertIn('RELEASE_HASH_REQUIRED',PACKET.read_text())
  self.assertNotIn('"/usr/bin/sudo"',PACKET.read_text())
if __name__=='__main__':unittest.main()
