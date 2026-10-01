import os,tempfile,unittest,json,hashlib
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

if __name__=='__main__': unittest.main()
