"""Actual Production Hooks and byte authenticators; only OS boundaries modeled.
Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
"""
from pathlib import Path
import base64,copy,hashlib,importlib.util,json,subprocess,unittest
D=Path(__file__).resolve().parent
def module(name,p):s=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
H=module('hooks',D/'production_hooks.py');B=module('batch',D.parent/'native_diagnostic_batch.py')
RAW=(D/'accepted-owner-export.json').read_bytes();NATIVE=json.loads((D/'accepted-native-capture.json').read_text());OLD='be5b3a70eeb641df92878acfe335735c';PARENT='/home/holden/mckernel-work/scratch/nm05a1/p';EMPTY=H.digest(b'')
def owner_export(case,profile,change=None):
 data=json.loads(RAW);root=str(Path(case['attempt_parent']).with_name(Path(case['attempt_parent']).name+'.owner-'+case['nonce']));data['root']=root;files={r['name']:base64.b64decode(r['base64']) for r in data['files']}
 for k,v in list(files.items()):files[k]=v.replace(OLD.encode(),case['nonce'].encode()).replace(PARENT.encode(),case['attempt_parent'].encode()).replace(B.MANIFEST_SHA.encode(),profile['manifest']['sha256'].encode())
 if change:change(files)
 names=set(files);data['files']=[r for r in data['files'] if r['name'] in names]
 for r in data['files']:
  raw=files[r['name']];r.update(source_path=root+'/'+r['name'],base64=base64.b64encode(raw).decode(),sha256=H.digest(raw));r['identity']['st_size']=len(raw)
 data['total_source_bytes']=sum(len(v) for v in files.values());return H.encoded(data)
def alter(files,name,fn):value=json.loads(files[name]);fn(value);files[name]=H.encoded(value)
class MemoryOS:
 """Virtual FDs/captures/mutex/process calls; production adapter logic stays real."""
 def __init__(self,profile,cases):self.profile=profile;self.cases=cases;self.files={};self.events=[];self.held=False;self.time=100;self.last_identity={};self.metadata={};self.native_timeout=False;self.query_nonempty=False;self.export_change=None;self.native_bad=False;self.fact_bad=False
 def now(self):self.time+=1;return self.time
 def read(self,p,maximum=16<<20):raw=self.files[str(p)];H.need(len(raw)<=maximum,'bounded virtual FD');self.last_identity[str(p)]=self.metadata.get(str(p),{});return raw
 def ref(self,path,obj):raw=H.encoded(obj);self.files[path]=raw;return {'path':path,'sha256':H.digest(raw)}
 def claim(self,p,v):H.need(str(p) not in self.files,'exclusive batch release already consumed');self.files[str(p)]=H.encoded(v);self.events.append('claim')
 def mutex(self):H.need(not self.held,'mutex double-acquire');self.held=True;self.events.append('lock');return 1
 def unlock(self,h):H.need(self.held,'mutex not held');self.held=False;self.events.append('unlock')
 def facts(self):
  self.events.append('facts');return {'canonical_absent':[] if self.fact_bad else H.CANONICAL,'scratch_uuid':H.SCRATCH_UUID,'host_free':100<<30,'scratch_free':30<<30,'memory_available':30<<30,'affinity':[7],'AS':[2<<30,2<<30],'FSIZE':[32<<20,32<<20],'NPROC':[126258,126258]}
 def native(self,ref,op,timeout):
  H.need(not self.held,'mutex must handoff before actual owner');self.events.append('native')
  if self.native_timeout:raise subprocess.TimeoutExpired(op['argv'],timeout)
  value=copy.deepcopy(NATIVE);value['argv']=op['argv'];value['stdout']['path']='/native/stdout';value['stderr']['path']='/native/stderr';self.files['/native/stdout']=self.files['/native/stderr']=b''
  for n in ('stdout','stderr'):self.metadata[value[n]['path']]={k:value[n][k] for k in ('device','inode','uid','gid','nlink','mode','mtime_ns','ctime_ns')}
  if self.native_bad:value['process_group_absent']=False
  return value
 def readonly(self,argv,path,role):
  self.events.append(role)
  if role=='export':
   nonce=argv[argv.index('--nonce')+1];case=next(c for c in self.cases if c['nonce']==nonce);raw=owner_export(case,self.profile,self.export_change)
  else:raw=b'present\n' if self.query_nonempty else b''
  descriptors={}
  for n,b in [('stdout',raw),('stderr',b'')]:p=str(path/n);self.files[p]=b;meta={'device':1,'inode':100+len(self.files),'uid':1000,'gid':1000,'nlink':1,'mode':'0o600','mtime_ns':1,'ctime_ns':1};self.metadata[p]=meta;descriptors[n]=dict(meta,path=p,size=len(b),sha256=H.digest(b))
  return {'returncode':0,'direct_child_joined':True,'closed_streams':True,'group_absent':True,'timed_out':False,'error':None,'retirement_error':None,'remaining_group_members':[],'captures':descriptors}
class Tests(unittest.TestCase):
 def setUp(self):
  self.old=B.validate_profile({'path':str(D.parent/'FIXED-CURRENT-PROFILE.json'),'sha256':H.digest((D.parent/'FIXED-CURRENT-PROFILE.json').read_bytes())});self.profile=copy.deepcopy(self.old)
  # Future data below exist ONLY in virtual OS memory; installed slot remains NULL.
  for i,r in enumerate(self.profile['_manifest']['modules']):r['sha256']=str(i+4)*64
  self.profile['manifest']['sha256']=H.digest(H.encoded(self.profile['_manifest']));self.profile['_sha256']='a'*64
  self.cases=[]
  for i,nonce in enumerate((OLD,'c'*32)):
   parent=PARENT if i==0 else '/modeled/second/p';command=self.profile['command_prefix']+[x for pair in zip(B.FLAGS_ORDER,[parent,nonce,self.profile['owner_sha256'],self.profile['manifest']['path'],self.profile['manifest']['sha256']]) for x in pair];self.cases.append({'nonce':nonce,'attempt_parent':parent,'command':command,'case_id':'modeled-'+str(i),'timeout_seconds':90})
  self.io=MemoryOS(self.profile,self.cases)
 def hooks(self,old=False,null=False):
  profile=self.old if old else self.profile
  t={'modules':[{k:r[k] for k in ('sha256','size')} for r in profile['_manifest']['modules']],'launcher':{k:profile['_manifest']['artifacts']['mcexec'][k] for k in ('sha256','size')}}
  binding={'profile_sha256':profile['_sha256'],'artifact_tuple':t}
  for k in ('sdk_acceptance','launcher_acceptance','first_complete_restoration'):binding[k]=self.io.ref('/proof/'+k,{'profile_sha256':profile['_sha256'],'artifact_tuple_sha256':H.digest(H.encoded(t)),'accepted':True})
  if null:binding=json.loads((D/'FUTURE-PROFILE-SLOT.json').read_text())
  br=self.io.ref('/binding',binding);refs=[]
  for i,c in enumerate(self.cases):refs.append(self.io.ref('/operation/'+str(i),{'argv':c['command'],'nonce':c['nonce'],'profile':profile['resource_profile'],'cpu':7,'stream_cap_bytes':32<<20,'capture_directory':'/capture/'+c['nonce']}))
  release={'status':'PASS_EXECUTION','adapter_sha256':H.digest((D/'production_hooks.py').read_bytes()),'batch_source_sha256':H.digest(Path(B.__file__).read_bytes()),'nonces':[c['nonce'] for c in self.cases],'profile_sha256':profile['_sha256'],'binding_sha256':br['sha256'],'operations':[{'nonce':c['nonce'],'command_sha256':H.digest(json.dumps(c['command'],separators=(',',':')).encode())} for c in self.cases],'operation_refs':refs,'output_root':'/modeled/output','export_source_sha256':H.digest((D/'export_closed_owner.py').read_bytes()),'resources':{'host_required':35<<30,'scratch_required':14<<30,'memory_required':14<<30},'inherited_NPROC':[126258,126258]}
  rr=self.io.ref('/release',release);return H.ProductionHooks(B,profile,self.cases,rr,br,'/modeled/output',io=self.io)
 def test_live_boundary_installs_exact_accepted_stop_handlers(self):
  from unittest import mock
  with mock.patch.object(H.signal,'signal') as install:
   live=H.LiveOS();self.assertEqual({call.args[0] for call in install.call_args_list},live.capture.STOP_SIGNALS);self.assertTrue(all(call.args[1] is live.capture.stop for call in install.call_args_list))
 def test_real_saved_owner_export_and_before_snapshot_authenticate(self):
  c={'nonce':OLD,'attempt_parent':PARENT};v=H.authenticate_owner(RAW,c,self.old,NATIVE);self.assertEqual(v['docker_clients'],30);self.assertEqual(len(v['files']),100);before=H.before_snapshot(v['inner']['observation']['serial']);self.assertEqual(H.digest(before),v['inner']['second_stop_protocol']['snapshot_sha256']['before'])
 def test_actual_hooks_two_serial_operations_with_authenticated_bytes(self):
  h=self.hooks();previous=None
  for c in self.cases:
   a=h.admit(c,previous);e=h.execute(c,a);self.assertTrue(B.evaluate_semantics(self.profile,e)['qualifies_first_restore_reboot']);r=h.retire(c);previous={'receipt':r,'sha256':H.digest(H.encoded(r))};self.assertEqual(r['authenticated_docker_reaps'],30)
  self.assertEqual(h.index,2);self.assertFalse(self.io.held);self.assertEqual(self.io.events.count('native'),2);self.assertEqual(self.io.events.count('claim'),1)
 def test_null_future_slot_cannot_stage_or_execute(self):
  h=self.hooks(null=True)
  with self.assertRaisesRegex(ValueError,'future production profile unbound'):h.admit(self.cases[0],None)
  self.assertEqual(self.io.events,[])
 def test_old20352_cannot_transfer_cycle_or_execute(self):
  h=self.hooks(old=True)
  with self.assertRaisesRegex(ValueError,'old20352'):h.admit(self.cases[0],None)
  self.assertEqual(self.io.events,[])
 def test_batch_release_nonce_order_once_and_output_namespace(self):
  h=self.hooks();r=json.loads(self.io.files['/release']);r['nonces'].reverse();ref=self.io.ref('/bad-release',r)
  with self.assertRaisesRegex(ValueError,'ordered batch release'):H.ProductionHooks(B,self.profile,self.cases,ref,{'path':'/binding','sha256':H.digest(self.io.files['/binding'])},'/modeled/output',io=self.io)
  h.admit(self.cases[0],None);self.io.unlock(h.context['lock']);h.context=None
  again=self.hooks()
  with self.assertRaisesRegex(ValueError,'already consumed'):again.admit(self.cases[0],None)
 def test_fresh_canonical_records_block_before_owner(self):
  h=self.hooks();self.io.fact_bad=True
  with self.assertRaisesRegex(ValueError,'six canonical'):h.admit(self.cases[0],None)
  self.assertNotIn('native',self.io.events);self.assertFalse(self.io.held)
 def test_actual_native_timeout_retains_and_cannot_auto_advance(self):
  h=self.hooks();a=h.admit(self.cases[0],None);self.io.native_timeout=True
  with self.assertRaises(subprocess.TimeoutExpired):h.execute(self.cases[0],a)
  with self.assertRaisesRegex(ValueError,'uncertain owner retained'):h.retire(self.cases[0])
  self.assertEqual(self.io.events.count('native'),1);self.assertNotIn('export',self.io.events);self.assertEqual(h.index,0)
 def test_native_capture_booleans_without_actual_stream_bytes_fail(self):
  io=self.io;ref={'path':'/fake','sha256':'0'*64,'bytes':0};v=copy.deepcopy(NATIVE);v['stdout']=ref;v['stderr']=ref;io.files['/fake']=b''
  with self.assertRaisesRegex(ValueError,'FD hash'):H.authenticate_capture(io,v,True)
 def test_export_digest_and_nonce_are_not_assertions(self):
  data=json.loads(RAW);data['files'][0]['sha256']='0'*64
  with self.assertRaisesRegex(ValueError,'actual exported owner bytes'):H.authenticate_owner(H.encoded(data),{'nonce':OLD,'attempt_parent':PARENT},self.old,NATIVE)
  with self.assertRaisesRegex(ValueError,'exported root'):H.authenticate_owner(RAW,{'nonce':'e'*32,'attempt_parent':PARENT},self.old,NATIVE)
 def test_missing_docker_reap_or_command_is_rejected(self):
  c=self.cases[0]
  for mode in ('missing','unreaped'):
   def change(f):
    if mode=='missing':del f['009-start.json'];del f['009-start.stdout'];del f['009-start.stderr']
    else:alter(f,'009-start.json',lambda x:x['command'].update(reaped=False))
   with self.assertRaisesRegex(ValueError,'Docker'):H.authenticate_owner(owner_export(c,self.profile,change),c,self.profile,NATIVE)
 def test_real_qemu_reap_and_observation_hashes_required(self):
  c=self.cases[0]
  for name,fn in [('inner-result.json',lambda x:x['cleanup'].update(reaped=False)),('capture-bindings.json',lambda x:x['serial.log'].update(sha256='0'*64))]:
   with self.assertRaises(ValueError):H.authenticate_owner(owner_export(c,self.profile,lambda f:alter(f,name,fn)),c,self.profile,NATIVE)
 def test_container_remove_and_empty_three_queries_required(self):
  c=self.cases[0]
  for mode in ('rm','query','lease'):
   def change(f):
    if mode=='rm':alter(f,'027-rm.json',lambda x:x.update(returncode=1,command=dict(x['command'],returncode=1)))
    elif mode=='query':f['030-ps.stdout']=b'not absent\n'
    else:alter(f,'result.json',lambda x:x.update(lease_retained=True))
   with self.assertRaises(ValueError):H.authenticate_owner(owner_export(c,self.profile,change),c,self.profile,NATIVE)
 def test_fresh_external_queries_and_six_records_required_before_next(self):
  h=self.hooks();a=h.admit(self.cases[0],None);h.execute(self.cases[0],a);self.io.query_nonempty=True
  with self.assertRaisesRegex(ValueError,'fresh name'):h.retire(self.cases[0])
  self.assertEqual(h.index,0);self.assertFalse(self.io.held)
 def test_first_iteration_must_semantically_qualify_before_advance(self):
  h=self.hooks();a=h.admit(self.cases[0],None)
  def change(f):
   inner=json.loads(f['inner-result.json']);inner['observation']['serial']=inner['observation']['serial'].replace('68616e646c65643d31','68616e646c65643d30');f['inner-result.json']=H.encoded(inner);f['serial.log']=inner['observation']['serial'].encode();alter(f,'capture-bindings.json',lambda x:x['serial.log'].update(size=len(f['serial.log']),sha256=H.digest(f['serial.log'])))
  self.io.export_change=change
  with self.assertRaises(ValueError):h.execute(self.cases[0],a)
  r=h.retire(self.cases[0]);self.assertFalse(r['lease_retained']);self.assertEqual(h.index,0)
  with self.assertRaisesRegex(ValueError,'serial next'):h.admit(self.cases[1],None)
 def test_exact_admission_deadline_handoff_and_mutex_release(self):
  h=self.hooks();a=h.admit(self.cases[0],None);self.io.time=a['expires_ns']
  with self.assertRaisesRegex(ValueError,'deadline'):h.execute(self.cases[0],a)
  self.assertNotIn('native',self.io.events);self.assertFalse(self.io.held)
if __name__=='__main__':unittest.main(verbosity=2,failfast=True)
