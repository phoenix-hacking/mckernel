"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Pure profile/created-only transaction tests. Docker/admission/custody are effect leaves.
"""
from pathlib import Path
import copy,importlib.util,json,os,struct,subprocess,tempfile,types,unittest
from unittest.mock import patch
D=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('created_only_libelf_candidate',D/'created_only_libelf_adapter.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
B=m.bindings();API=m.interfaces(B);IMAGE=json.loads(m.checked(B['immutable_image_reply']))[0]
CID='b'*64

def request(out):return dict(TEST_ONLY=True,author='/root',operation='CREATED_ONLY_41778_LIBELF_EXPORT',maximum_invocations=1,image=m.IMAGE,source='/usr/lib64/libelf.so.1',nonce='a'*32,name='m15-libelf-extract-'+'a'*32,output_root=str(out),target=str(out/'libelf.so.1'),native_or_build_authority=False)
def container(q):
 h=dict(API['LIMITS'],Privileged=False,ReadonlyRootfs=True,CapDrop=['ALL'],SecurityOpt=['no-new-privileges'],Init=True,PidMode='',IpcMode='private',Devices=[],DeviceRequests=None,Binds=None,CapAdd=None,CgroupParent='',Tmpfs={'/tmp':'rw,nodev,nosuid,size=256m'},RestartPolicy={'Name':'no','MaximumRetryCount':0})
 labels=dict(B['pinned_image_labels']);labels['mckernel.owner']=q['nonce']
 return dict(Id=CID,Name='/'+q['name'],Image=m.IMAGE,Mounts=[],HostConfig=h,Config=dict(User='%d:%d'%(os.getuid(),os.getgid()),Entrypoint=['/usr/bin/sleep'],Cmd=['infinity'],Labels=labels,Env=B['pinned_image_env']),State=dict(Status='created',Running=False,Pid=0,Paused=False,Restarting=False,Dead=False,OOMKilled=False))

class Effects:
 def __init__(self,q):self.q=q;self.info=container(q);self.image=copy.deepcopy(IMAGE);self.calls=[];self.published={};self.retained=[];self.admissions=[];self.client_retirement_unproven=False;self.before_popen=lambda argv:None;self.fail_cp=False;self.bad_created_cid=False;self.start_during_cp=False
 def admit(self,q):self.admissions.append(q['nonce'])
 def publish(self,name,value):self.published[name]=value
 def retain(self,value):self.retained.append(value)
 def exact(self,argv,timeout,check=True):
  assert argv[:4]==m.PREFIX and timeout==30;args=argv[4:];self.calls.append(args)
  if args[:2]==['image','inspect']:out=json.dumps([self.image])
  elif args[0]=='create':
   assert args==API['create_args'](self.q['name'],m.IMAGE,self.q['nonce']);out=(m.FORBIDDEN_CID if self.bad_created_cid else CID)+'\n'
  elif args[:3]==['inspect','--type','container']:assert args[-1]==CID;out=json.dumps([self.info])
  elif args[:2]==['cp','-L']:
   assert args==['cp','-L',CID+':/usr/lib64/libelf.so.1',self.q['target']]
   if self.fail_cp:raise RuntimeError('TEST_ONLY failed cp; preserve created owner')
   raw=struct.pack('<16sHHIQQQIHHHHHH',b'\x7fELF\x02\x01'+b'\0'*10,3,62,1,0,0,0,0,64,56,0,64,0,0);Path(self.q['target']).write_bytes(raw);out=''
   if self.start_during_cp:self.info['State'].update(Status='running',Running=True,Pid=777)
  elif args==['rm','--',CID]:out=CID+'\n'
  elif args[:5]==['ps','--all','--quiet','--no-trunc','--filter']:out=''
  else:raise AssertionError('unexpected command '+repr(args))
  return subprocess.CompletedProcess(argv,0,out,'')
 def run(self):return m.execute_created_only(self.q,commands=self,admit=self.admit,publish=self.publish,retain_uncertainty=self.retain)

class CreatedOnlyTests(unittest.TestCase):
 def test_reviewed_lineage_and_exact_created_only_success(self):
  self.assertEqual(B['reviewed_owner_snapshot']['sha256'],'9634b56f251857141c67b70ce7a0c058470d6ef000a5f041898a91e3a71f6679')
  with tempfile.TemporaryDirectory(prefix='actual-libelf-export-TEST_ONLY_',dir=D) as tmp:
   e=Effects(request(Path(tmp)));r=e.run();self.assertTrue(r['created_only'] and r['container_absent']);self.assertEqual(r['container_starts'],0);self.assertEqual(r['command_count'],8);self.assertFalse(r['SONAME_version_dependency_acceptance']);self.assertFalse(r['file_closure'])
   self.assertEqual([x[0] for x in e.calls],['image','create','inspect','cp','inspect','rm','ps','ps']);self.assertNotIn('start',[x[0] for x in e.calls]);self.assertEqual(len(e.admissions),8);self.assertEqual(e.retained,[])
 def test_wrong_image_or_target_or_invocation_refuses_before_effect(self):
  with tempfile.TemporaryDirectory(prefix='actual-libelf-export-TEST_ONLY_',dir=D) as tmp:
   for change in [dict(image='sha256:'+'0'*64),dict(source='/other'),dict(target=str(Path(tmp)/'other')),dict(maximum_invocations=True)]:
    q=request(Path(tmp));q.update(change);e=Effects(q)
    with self.assertRaises(m.Refusal):e.run()
    self.assertEqual(e.calls,[])
 def test_profile_mismatches_preserve_created_owner_without_cp_or_remove(self):
  with tempfile.TemporaryDirectory(prefix='actual-libelf-export-TEST_ONLY_',dir=D) as tmp:
   for mutate in [lambda x:x['HostConfig'].update(NetworkMode='host'),lambda x:x['HostConfig'].update(MemorySwap=-1),lambda x:x['State'].update(Pid=1),lambda x:x['State'].update(Status='running',Running=True),lambda x:x['Config']['Labels'].update({'mckernel.owner':'c'*32}),lambda x:x['Config'].update(Env=['other=1'])]:
    e=Effects(request(Path(tmp)));mutate(e.info)
    with self.assertRaises(RuntimeError):e.run()
    self.assertEqual([x[0] for x in e.calls],['image','create','inspect']);self.assertTrue(e.retained);self.assertTrue(e.retained[-1]['no_automatic_cleanup_or_retry'])
 def test_cp_failure_retains_exact_owner_and_never_auto_removes(self):
  with tempfile.TemporaryDirectory(prefix='actual-libelf-export-TEST_ONLY_',dir=D) as tmp:
   e=Effects(request(Path(tmp)));e.fail_cp=True
   with self.assertRaises(RuntimeError):e.run()
   self.assertEqual([x[0] for x in e.calls],['image','create','inspect','cp']);self.assertTrue(e.retained[-1]['created_confirmed']);self.assertFalse(e.retained[-1]['removed_confirmed'])
 def test_retired_CID_cannot_be_used_as_new_source(self):
  with tempfile.TemporaryDirectory(prefix='actual-libelf-export-TEST_ONLY_',dir=D) as tmp:
   e=Effects(request(Path(tmp)));e.bad_created_cid=True
   with self.assertRaisesRegex(m.Refusal,'retired2460'):e.run()
   self.assertEqual([x[0] for x in e.calls],['image','create']);self.assertTrue(e.retained)
 def test_after_copy_running_state_refuses_remove_and_retains_all(self):
  with tempfile.TemporaryDirectory(prefix='actual-libelf-export-TEST_ONLY_',dir=D) as tmp:
   e=Effects(request(Path(tmp)));e.start_during_cp=True
   with self.assertRaises(RuntimeError):e.run()
   self.assertEqual([x[0] for x in e.calls],['image','create','inspect','cp','inspect']);self.assertTrue(Path(e.q['target']).is_file());self.assertFalse(e.retained[-1]['removed_confirmed'])
 def test_early_image_or_admission_failure_does_not_claim_create(self):
  with tempfile.TemporaryDirectory(prefix='actual-libelf-export-TEST_ONLY_',dir=D) as tmp:
   e=Effects(request(Path(tmp)));e.image['Id']='sha256:'+'0'*64
   with self.assertRaises(m.Refusal):e.run()
   self.assertFalse(e.retained[-1]['create_attempt_may_have_occurred']);self.assertEqual([x[0] for x in e.calls],['image'])

 def test_root_mediated_copy_ownership_is_recorded_without_rewriting_it(self):
  with tempfile.TemporaryDirectory(prefix='actual-libelf-export-TEST_ONLY_',dir=D) as tmp:
   path=Path(tmp)/'libelf.so.1';path.write_bytes(struct.pack('<16sHHIQQQIHHHHHH',b'\x7fELF\x02\x01'+b'\0'*10,3,62,1,0,0,0,0,64,56,0,64,0,0))
   real=Path.stat
   def modeled_root(pathobj,*args,**kwargs):
    value=real(pathobj,*args,**kwargs)
    if pathobj==path:
     fields=list(value);fields[4]=0;return os.stat_result(fields)
    return value
   with patch.object(Path,'stat',modeled_root):result=m.inspect_library(path)
   self.assertEqual(result['owner']['uid'],0);self.assertFalse(result['SONAME_and_GNU_versions_accepted'])

if __name__=='__main__':unittest.main(verbosity=2)
