import os,tempfile,unittest,json,hashlib,fcntl,signal,select
from unittest import mock
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import native_rust_exact_build_image_rebind_probe as p

class T(unittest.TestCase):
 def _auth(self,root):
  target=root/'target'; target.mkdir()
  (root/'source').mkdir()
  req={'target_evidence_root':str(root/'out'),'target_receipt':str(root/'out'/'image-receipt.json'),'target_candidate_sha':'b'*40,'source_candidate_sha':'a'*40,'image_id':'sha256:'+'a'*64,'source_receipt':'/source','source_receipt_sha256':'c'*64,'source_evidence_root':str(root/'source'),'toolchain_lock_sha256':'d'*64}
  rec={'candidate_sha':'a'*40,'evidence':{},'packages':{},'tools':{},'libraries':{}}
  return req,rec,{}
 def _docker(self, probe):
  class D:
   client_retirement_unproven=False
   def __init__(s,*a,**k): s.calls=[]
   def call(s,a,**k):
    s.calls.append(a)
    class R:
     returncode=1; stdout=''; stderr=''
    if a[:2]==['image','inspect']: R.returncode=0; R.stdout=json.dumps([{'Id':'sha256:'+'a'*64,'Architecture':'amd64','Os':'linux'}])
    if a and a[0]=='exec': R.returncode=0; R.stdout=json.dumps(probe)
    if a and a[0]=='inspect' and len(a)>1: R.returncode=1; R.stdout='[]\n'; R.stderr='Error: No such object: %s\n'%a[1]
    return R()
  return D
 def _patch_common(self,root,probe,release=True):
  req,rec,sp=self._auth(root); rec['evidence']={};
  lease=mock.Mock(); lease.nonce='n'; lease.acquire=mock.Mock(); lease.release=mock.Mock()
  shared=mock.Mock(); shared.acquire_heavy_operation=mock.Mock(return_value=(root/'lock',{})); shared._release_exclusion=mock.Mock(return_value=release)
  return req,rec,sp,lease,shared
 def test_execute_success_fields(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d); req,rec,sp,lease,shared=self._patch_common(root,{})
   with mock.patch.object(p,'authenticate_request',return_value=(req,'r',rec,sp)),mock.patch.object(p,'Lease',return_value=lease),mock.patch.object(p,'Docker',self._docker({})),mock.patch.object(p,'_SHARED_HEAVY_ENTRY_CONTRACT',shared),mock.patch.object(p,'inspect',return_value={'HostConfig':{},'Config':{}}),mock.patch.object(p,'check_profile'),mock.patch.object(p,'validate_container'),mock.patch.object(p,'validate_probe'),mock.patch.object(p,'retire',return_value={}):
    final,result=p.execute(request_path='/r',expected_request_sha256='e'*64)
   self.assertEqual(result['status'],'PASS',result); self.assertFalse(result['cleanup_separately_required']); self.assertEqual(final.name,'image-receipt.json')
 def test_probe_mismatch_fails(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d); req,rec,sp,lease,shared=self._patch_common(root,{'x':1})
   with mock.patch.object(p,'authenticate_request',return_value=(req,'r',rec,sp)),mock.patch.object(p,'Lease',return_value=lease),mock.patch.object(p,'Docker',self._docker({'x':2})),mock.patch.object(p,'_SHARED_HEAVY_ENTRY_CONTRACT',shared),mock.patch.object(p,'inspect',return_value={'HostConfig':{},'Config':{}}),mock.patch.object(p,'check_profile'),mock.patch.object(p,'validate_container'),mock.patch.object(p,'validate_probe'),mock.patch.object(p,'retire',return_value={}):
    _,result=p.execute(request_path='/r',expected_request_sha256='e'*64)
   self.assertEqual(result['status'],'FAIL'); self.assertTrue(result['cleanup_separately_required'])
 def test_release_false_fails(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d); req,rec,sp,lease,shared=self._patch_common(root,{} ,False)
   with mock.patch.object(p,'authenticate_request',return_value=(req,'r',rec,sp)),mock.patch.object(p,'Lease',return_value=lease),mock.patch.object(p,'Docker',self._docker({})),mock.patch.object(p,'_SHARED_HEAVY_ENTRY_CONTRACT',shared),mock.patch.object(p,'inspect',return_value={'HostConfig':{},'Config':{}}),mock.patch.object(p,'check_profile'),mock.patch.object(p,'validate_container'),mock.patch.object(p,'validate_probe'),mock.patch.object(p,'retire',return_value={}):
    _,result=p.execute(request_path='/r',expected_request_sha256='e'*64)
   self.assertEqual(result['status'],'FAIL')
 def test_daemon_constructor_failure_is_refused(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d); req,rec,sp,lease,shared=self._patch_common(root,{})
   with mock.patch.object(p,'authenticate_request',return_value=(req,'r',rec,sp)),mock.patch.object(p,'Lease',side_effect=RuntimeError('daemon unreachable')),mock.patch.object(p,'_SHARED_HEAVY_ENTRY_CONTRACT',shared):
    _,result=p.execute(request_path='/r',expected_request_sha256='e'*64)
   self.assertEqual(result['status'],'FAIL')
   shared._release_exclusion.assert_not_called()
   self.assertTrue(result['cleanup_separately_required'])
 def test_ambiguous_create_reconciles_and_retains_ownership(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d); req,rec,sp,lease,shared=self._patch_common(root,{})
   Base=self._docker({})
   class D(Base):
    def call(s,a,**k):
     if a and a[0]=='create': raise RuntimeError('client lost create response')
     return super().call(a,**k)
   retired=mock.Mock(return_value={'State':{'Status':'created','Running':False,'Pid':0}})
   with mock.patch.object(p,'authenticate_request',return_value=(req,'r',rec,sp)),mock.patch.object(p,'Lease',return_value=lease),mock.patch.object(p,'Docker',D),mock.patch.object(p,'_SHARED_HEAVY_ENTRY_CONTRACT',shared),mock.patch.object(p,'validate_probe'),mock.patch.object(p,'retire',retired):
    _,result=p.execute(request_path='/r',expected_request_sha256='e'*64)
   self.assertEqual(result['status'],'FAIL')
   retired.assert_called_once()
   lease.release.assert_not_called()
   shared._release_exclusion.assert_not_called()
   self.assertTrue(result['container_name'].startswith('mckernel-tool-rebind-'))
   self.assertTrue(result['cleanup_separately_required'])
 def test_pending_signal_is_not_success(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d); req,rec,sp,lease,shared=self._patch_common(root,{})
   class S:
    requested=15; cleaning=False
    def check(self): raise RuntimeError('owner interrupted by signal 15')
   sig=S()
   with mock.patch.object(p,'authenticate_request',return_value=(req,'r',rec,sp)),mock.patch.object(p,'Lease',return_value=lease),mock.patch.object(p,'Docker',self._docker({})),mock.patch.object(p,'_SHARED_HEAVY_ENTRY_CONTRACT',shared),mock.patch.object(p,'inspect',return_value={'HostConfig':{},'Config':{}}),mock.patch.object(p,'check_profile'),mock.patch.object(p,'validate_container'),mock.patch.object(p,'validate_probe'),mock.patch.object(p,'retire',return_value={}):
    _,result=p.execute(request_path='/r',expected_request_sha256='e'*64,signals=sig)
   self.assertEqual(result['status'],'FAIL')
   lease.release.assert_not_called()
   shared._release_exclusion.assert_not_called()
 def test_cpu(self): self.assertIn('--cpuset-cpus=2-5',p.create_args('n','i','x'))
 def test_cpus(self): self.assertIn('--cpus=4',p.create_args('n','i','x'))
 def test_mem(self): self.assertIn('--memory=12g',p.create_args('n','i','x'))
 def test_swap(self): self.assertIn('--memory-swap=12g',p.create_args('n','i','x'))
 def test_net(self): self.assertIn('--network=none',p.create_args('n','i','x'))
 def test_ipc(self): self.assertIn('--ipc=private',p.create_args('n','i','x'))
 def test_ro(self): self.assertIn('--read-only',p.create_args('n','i','x'))
 def test_caps(self): self.assertIn('--cap-drop=ALL',p.create_args('n','i','x'))
 def test_pid(self): self.assertIn('--pids-limit=512',p.create_args('n','i','x'))
 def test_dupes(self):
  with tempfile.TemporaryDirectory() as d:
   f=Path(d)/'x'; f.write_text('{"a":1,"a":2}')
   with self.assertRaises(p.RebindProbeError): p._read_json_snapshot(f,'x')
 def test_image_id(self):
  with self.assertRaises(p.RebindProbeError): p.validate_image_inspect([{'Id':'sha256:'+'b'*64,'Architecture':'amd64','Os':'linux'}],'sha256:'+'a'*64)
 def test_arch(self):
  with self.assertRaises(p.RebindProbeError): p.validate_image_inspect([{'Id':'sha256:'+'a'*64,'Architecture':'arm64','Os':'linux'}],'sha256:'+'a'*64)
 def test_rows(self):
  with self.assertRaises(p.RebindProbeError): p.validate_image_inspect([],'sha256:'+'a'*64)
 def test_daemon_error_is_not_absence(self):
  docker=mock.Mock()
  docker.call.return_value=type('R',(),{'returncode':1,'stdout':'','stderr':'Cannot connect to the Docker daemon\n'})()
  with self.assertRaises(p.RebindProbeError): p._absence(docker,'owned')
 def test_mount(self):
  i={'HostConfig':{'NetworkMode':'none','ReadonlyRootfs':True,'Binds':['bad'],'Tmpfs':{'/tmp':'rw,nodev,nosuid,size=256m'},'RestartPolicy':{'Name':'no','MaximumRetryCount':0}},'Config':{'User':'%d:%d'%(os.getuid(),os.getgid()),'Entrypoint':['/usr/bin/sleep'],'Cmd':['infinity']}}
  with self.assertRaises(Exception): p.validate_container(i,'x','n')
 def test_network(self):
  i={'HostConfig':{'NetworkMode':'bridge','ReadonlyRootfs':True,'Tmpfs':{'/tmp':'rw,nodev,nosuid,size=256m'},'RestartPolicy':{'Name':'no','MaximumRetryCount':0}},'Config':{'User':'%d:%d'%(os.getuid(),os.getgid()),'Entrypoint':['/usr/bin/sleep'],'Cmd':['infinity']}}
  with self.assertRaises(Exception): p.validate_container(i,'x','n')
 def test_user(self):
  i={'HostConfig':{'NetworkMode':'none','ReadonlyRootfs':True,'Tmpfs':{'/tmp':'rw,nodev,nosuid,size=256m'},'RestartPolicy':{'Name':'no','MaximumRetryCount':0}},'Config':{'User':'0:0','Entrypoint':['/usr/bin/sleep'],'Cmd':['infinity']}}
  with self.assertRaises(Exception): p.validate_container(i,'x','n')
 def test_traversal(self):
  with tempfile.TemporaryDirectory() as d:
   with self.assertRaises(p.RebindProbeError): p._copy_closure(d,Path(d)/'o',{'../x':{'sha256':'0'*64,'size':0}})
 def test_noreplace(self):
  with tempfile.TemporaryDirectory() as d:
   f=Path(d)/'x'; f.write_bytes(b'a')
   with self.assertRaises(FileExistsError): p._write_new(f,b'b')
 def test_probe_binding(self): self.assertEqual(p._expected_probe({'target_candidate_sha':'a'*40,'target_evidence_root':'/x'})['target_receipt_candidate_sha'],'a'*40)

class RootGuardTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
  self.root=Path(self.temp.name); self.lock=self.root/'development.lock'; self.lock.touch(mode=0o644); self.lock.chmod(0o644)
  self.binding=(self.lock.stat().st_dev,self.lock.stat().st_ino)
  self.target=self.root/'target'; self.shared=self.root/'shared.lock'
  self.request=self.root/'request.json'
  self.req={'target_evidence_root':str(self.target),'target_receipt':str(self.target/'image-receipt.json'),
            'target_candidate_sha':'b'*40,'image_id':'sha256:'+'a'*64}
  p._write_json(self.request,self.req); self.checksum=hashlib.sha256(self.request.read_bytes()).hexdigest()
  patch=mock.patch.object(p,'_SHARED_HEAVY_ENTRY_CONTRACT',type('Contract',(),{'SHARED_HEAVY_LOCK_PATH':str(self.shared)})())
  patch.start(); self.addCleanup(patch.stop)
 def call(self):
  return p.guarded_execute(request_path=self.request,expected_request_sha256=self.checksum,
                           lock_path=self.lock,lock_identity=self.binding,lock_owner=(os.getuid(),os.getgid()))
 def assert_locked(self):
  fd=os.open(self.lock,os.O_RDONLY)
  try:
   with self.assertRaises(BlockingIOError): fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
  finally: os.close(fd)
 def success(self,**kwargs):
  self.assert_locked()
  self.target.mkdir(); name='mckernel-tool-rebind-disposable'
  lease=self.root/('.'+self.target.name+'.lease.json')
  lease.write_text('owned'); self.shared.write_text('owned')
  p._write_json(self.target/'rebind-container-absence.json',{'container_name':name,'absent':True,
                'inspect_exit_code':1,'stderr':'Error: No such object: %s\n'%name})
  p._write_json(self.target/'rebind-shared-release.json',{'released':True})
  self.assert_locked()  # Ownership proof still incomplete while these names exist.
  lease.unlink(); self.shared.unlink()
  result={'status':'PASS','retired':True,'cleanup_separately_required':False,
          'terminal_container_info':None,'terminal_container_info_current':True,
          'client_retirement_unproven':False,'lease_path':str(lease),'container_name':name,
          'shared_heavy_operation':{'path':str(self.shared)},
          'candidate_sha':self.req['target_candidate_sha'],'image_id':self.req['image_id'],
          'evidence':p.inventory(self.target)}
  receipt=self.target/'image-receipt.json'; p._write_json(receipt,result)
  self.assert_locked()
  return receipt,result
 def test_success_unlocks_only_after_actual_receipt_and_ownership_proofs(self):
  old_mask=signal.pthread_sigmask(signal.SIG_BLOCK,set())
  old_handlers={s:signal.getsignal(s) for s in p.DEFERRED_SIGNALS}
  real=p._prove_guarded_success
  def proof(*args): self.assert_locked(); return real(*args)
  with mock.patch.object(p,'execute',side_effect=self.success),mock.patch.object(p,'_prove_guarded_success',side_effect=proof):
   receipt,result=self.call()
  self.assertEqual(result['status'],'PASS'); self.assertTrue(receipt.is_file())
  fd=os.open(self.lock,os.O_RDONLY)
  try: fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
  finally: os.close(fd)
  self.assertEqual(signal.pthread_sigmask(signal.SIG_BLOCK,set()),old_mask)
  self.assertEqual({s:signal.getsignal(s) for s in p.DEFERRED_SIGNALS},old_handlers)
 def test_busy_or_wrong_inode_stops_before_execute(self):
  fd=os.open(self.lock,os.O_RDONLY)
  try:
   fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
   with mock.patch.object(p,'execute') as core:
    with self.assertRaises(BlockingIOError): self.call()
    core.assert_not_called()
  finally: os.close(fd)
  with mock.patch.object(p,'execute') as core:
   with self.assertRaisesRegex(p.RebindProbeError,'lock identity'):
    p.guarded_execute(request_path=self.request,expected_request_sha256=self.checksum,
                       lock_path=self.lock,lock_identity=(self.binding[0],self.binding[1]+1),lock_owner=(os.getuid(),os.getgid()))
   core.assert_not_called()
 def test_symlink_lock_or_ancestor_is_refused(self):
  alias=self.root/'alias'; alias.symlink_to(self.lock)
  with self.assertRaises(OSError): p._development_lock(alias,self.binding,(os.getuid(),os.getgid()))
  ancestor=self.root/'alias-dir'; ancestor.symlink_to(self.root,target_is_directory=True)
  with self.assertRaises(OSError): p._development_lock(ancestor/self.lock.name,self.binding,(os.getuid(),os.getgid()))
 def test_unproven_terminal_or_receipt_error_keeps_lock_during_quarantine(self):
  class Held(BaseException): pass
  for failure in ('core-exception','shared-left','receipt-lost','client-uncertain'):
   with self.subTest(failure=failure):
    case=RootGuardTests(); case.setUp()
    held_fds=[]; handlers={s:signal.getsignal(s) for s in p.DEFERRED_SIGNALS}
    old_mask=signal.pthread_sigmask(signal.SIG_BLOCK,set())
    try:
     def core(**kwargs):
      if failure=='core-exception': raise RuntimeError('disposable core exception')
      receipt,result=case.success(**kwargs)
      if failure=='shared-left': case.shared.write_text('uncertain shared owner')
      if failure=='receipt-lost': receipt.unlink()
      if failure=='client-uncertain': result['client_retirement_unproven']=True
      return receipt,result
     def hold(): case.assert_locked(); raise Held()
     real_quarantine=p.quarantine_root_lock
     def quarantine(fd,path): held_fds.append(fd); return real_quarantine(fd,path)
     with mock.patch.object(p,'execute',side_effect=core),mock.patch.object(p,'quarantine_wait',side_effect=hold),mock.patch.object(p,'quarantine_root_lock',side_effect=quarantine):
      with self.assertRaises(Held): case.call()
     case.assert_locked()
    finally:
     for fd in held_fds: os.close(fd)  # Dispose only the deliberately intercepted test hold.
     signal.pthread_sigmask(signal.SIG_BLOCK,p.DEFERRED_SIGNALS)
     for number,handler in handlers.items(): signal.signal(number,handler)
     signal.pthread_sigmask(signal.SIG_SETMASK,old_mask)
     case.doCleanups()
 def test_actual_children_keep_all_four_handlers_and_lock_across_quarantine(self):
  for number in p.DEFERRED_SIGNALS:
   with self.subTest(signal=number):
    case=RootGuardTests(); case.setUp(); readfd,writefd=os.pipe(); continue_read,continue_write=os.pipe()
    pid=None; reaped=False
    try:
     pid=os.fork()
     if pid==0:
      try:
       os.close(readfd); os.close(continue_write)
       real_wait=p.quarantine_wait
       def owner(**kwargs):
        case.assert_locked(); os.write(writefd,b'O')
        if os.read(continue_read,1)!=b'C': raise RuntimeError('missing test continuation')
        kwargs['signals'].check()
        raise RuntimeError('signal latch did not reject')
       def held(): os.write(writefd,b'H'); real_wait()
       def writer(*args,**kwargs): raise BrokenPipeError('disposable quarantine writer failure')
       p.execute=owner; p.quarantine_wait=held; p._write_json=writer
       case.call(); os._exit(91)
      except BaseException:
       os.write(writefd,b'E'); os._exit(92)
     os.close(writefd); writefd=None; os.close(continue_read); continue_read=None
     self.assertTrue(select.select([readfd],[],[],5)[0]); self.assertEqual(os.read(readfd,1),b'O')
     os.kill(pid,number); os.write(continue_write,b'C')
     self.assertTrue(select.select([readfd],[],[],5)[0]); self.assertEqual(os.read(readfd,1),b'H')
     case.assert_locked()
     os.kill(pid,number)  # Handler remains active during uncertain quarantine too.
     self.assertFalse(select.select([readfd],[],[],0.03)[0])
     waited,status=os.waitpid(pid,os.WNOHANG); reaped=waited==pid
     self.assertEqual(waited,0,'quarantine child exited: '+str(status))
    finally:
     if pid is not None and not reaped:
      try: os.kill(pid,signal.SIGKILL)
      except ProcessLookupError: pass
      os.waitpid(pid,0)
     for fd in (readfd,writefd,continue_read,continue_write):
      if fd is not None: os.close(fd)
     case.doCleanups()
 def test_main_routes_only_through_guard(self):
  with mock.patch.object(p,'guarded_execute',return_value=(Path('/receipt'),{'status':'PASS'})) as guarded,mock.patch('builtins.print'):
   self.assertEqual(p.main(['--request','/request','--expected-request-sha256','e'*64]),0)
  guarded.assert_called_once_with(request_path='/request',expected_request_sha256='e'*64)

if __name__=='__main__': unittest.main()
