#!/usr/bin/env python3
"""Pure tests only; no roots, Docker, observer, Git, or candidate is touched."""
import hashlib, importlib.util, io, os, stat, struct, subprocess, sys, tempfile, unittest
from pathlib import Path
from unittest import mock
ROOT=Path(__file__).parents[2]; PACKET=ROOT/'docs/verification/evidence/native-exact-candidate-retirement-67589154-1.py'
s=importlib.util.spec_from_file_location('retire_packet',str(PACKET));M=importlib.util.module_from_spec(s);s.loader.exec_module(M)
class T(unittest.TestCase):
 def setUp(self):
  self.old=(M.RELEASE_SHA256,M.HELPER_SHA256,M.OBSERVER_SHA256,M.ARCHIVE_SHA256,M.HELPER_TEST_SHA256,M.OBSERVER_TEST_SHA256,M.BUILD_LEASE)
  self.flags={}
  def ioctl(fd,request,arg,mutate=False):
   key=os.fstat(fd if isinstance(fd,int) else fd.fileno()).st_ino
   if request==M.FS_IOC_GETFLAGS:arg[:]=struct.pack('I',self.flags.get(key,0));return 0
   if request==M.FS_IOC_SETFLAGS:self.flags[key]=struct.unpack('I',bytes(arg))[0];return 0
   raise AssertionError('unexpected ioctl')
  self.ioc=mock.patch.object(M.fcntl,'ioctl',side_effect=ioctl);self.ioc.start()
 def tearDown(self):self.ioc.stop();M.RELEASE_SHA256,M.HELPER_SHA256,M.OBSERVER_SHA256,M.ARCHIVE_SHA256,M.HELPER_TEST_SHA256,M.OBSERVER_TEST_SHA256,M.BUILD_LEASE=self.old
 def final(self):M.RELEASE_SHA256=M.HELPER_SHA256=M.OBSERVER_SHA256=M.ARCHIVE_SHA256=M.HELPER_TEST_SHA256=M.OBSERVER_TEST_SHA256='a'*64
 def proc(self,out=b'',err=b'',rc=0):
  p=mock.Mock();p.stdout=io.BytesIO();p.stderr=io.BytesIO();p.communicate.return_value=(out,err);p.returncode=rc;p.poll.return_value=rc;return p
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
  p=mock.Mock();p.wait.side_effect=[subprocess.TimeoutExpired(['x'],5),7]
  with mock.patch.object(M,'retire_process',return_value=(b'',b'')) as retire:self.assertEqual(M.finish_reader(p),7);retire.assert_called_once()
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
  self.assertEqual(M.HELPER_SHA256,'7860b315247585f64df2adac7709b1d1405e553d884c08923501b1926a57226b')
  self.assertEqual(M.OBSERVER_SHA256,'3562b1d3d4e9a1e09cb7fa2be30f8e320923d50cf628b7f42314318702653666')
  self.assertIn('RELEASE_HASH_REQUIRED',PACKET.read_text())
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
   M.retire_process(p,{'stdout_data':bytearray(),'stderr_data':bytearray()})
  kill.assert_not_called()
 def test_pidfd_failure_fails_closed_without_numeric_group_signal(self):
  p=mock.Mock();p._mckernel_session=77;p._mckernel_retired=False;p.poll.return_value=None
  row={'pid':77,'pgrp':77,'session':77,'starttime':9}
  with mock.patch.object(M,'session_members',return_value=[row]),mock.patch.object(M,'pidfd_open',side_effect=M.Error('pidfd unavailable')),mock.patch.object(M.os,'killpg') as kill:
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
  self.assertEqual(p.wait(timeout=5),0)
  M.retire_process(p,{'stdout':p.stdout,'stderr':p.stderr,'stdout_data':bytearray(),'stderr_data':bytearray()})
  self.assertEqual(M.session_members(p._mckernel_session),[])
  p.stdout.close();p.stderr.close()
 def test_fast_start_new_session_exit_is_admitted_and_censused(self):
  p=subprocess.Popen(['/bin/true'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True)
  p.wait(timeout=5);M.bind_process(p)
  self.assertEqual(M.session_members(p._mckernel_session),[])
  p.stdout.close();p.stderr.close()
if __name__=='__main__':unittest.main()
