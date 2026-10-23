"""Actual adapted control flow and unchanged strict semantic consumers; effects modeled only.
Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
"""
from pathlib import Path
import copy, hashlib, importlib.util, json, subprocess, tempfile, unittest
D=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('batch',D/'native_diagnostic_batch.py');batch=importlib.util.module_from_spec(spec);spec.loader.exec_module(batch)
def sha(raw):return hashlib.sha256(raw).hexdigest()
def ref(path):return {'path':str(path),'sha256':sha(path.read_bytes())}
def canonical(obj):return json.dumps(obj,sort_keys=True,separators=(',',':')).encode()
OBS=json.loads((D/'accepted-observation.json').read_text());BEFORE=(D/'accepted-first-prefix.kmsg').read_bytes()
class Hooks:
 def __init__(self,profile,change=None):self.profile=profile;self.change=change;self.events=[];self.tick=100;self.admissions={}
 def clock(self):self.tick+=1;return self.tick
 def identity(self,c):return {'nonce':c['nonce'],'profile_sha256':self.profile['_sha256'],'command_sha256':sha(json.dumps(c['command'],separators=(',',':')).encode())}
 def admit(self,c,previous):
  self.events.append(('admit',c['case_id']));r=self.identity(c);r.update({k:True for k in batch.PARENT_CHECKS});r.update(observed_ns=self.clock(),expires_ns=self.tick+10000,previous_retirement_sha256=None if previous is None else previous['sha256'],expected_epochs=[[0,1,1],[0,2,2]],resource_profile_sha256=sha(canonical(self.profile['resource_profile'])),permanent_mutex_identity=[27,4]);self.admissions[c['nonce']]=r
  if self.change:self.change('admit',c,r)
  return r
 def execute(self,c,a):
  self.events.append(('execute',c['case_id']));r=self.identity(c);r.update(returncode=0,owner_status='PROTOCOL_PASS',admission_sha256=sha(canonical(a)),observation=copy.deepcopy(OBS),kernel_before=BEFORE)
  if self.change:self.change('execute',c,r)
  return r
 def retire(self,c):
  self.events.append(('retire',c['case_id']));r=self.identity(c);r.update({k:True for k in batch.RETIRE_CHECKS});r.update(lease_retained=False,retired_ns=self.clock(),permanent_mutex_identity=[27,4])
  if self.change:self.change('retire',c,r)
  return r
class Tests(unittest.TestCase):
 def setUp(self):
  self.work=Path(tempfile.mkdtemp(prefix='modeled-',dir=str(D)));self.profile_ref=ref(D/'FIXED-CURRENT-PROFILE.json');self.profile=batch.validate_profile(self.profile_ref)
 def make(self,n=2):
  cases=[]
  for i in range(n):
   parent=self.work/('parent%d'%i);parent.mkdir(mode=0o700);nonce=('%032x'%(i+1));cid='modeled-%d'%i
   command=self.profile['command_prefix']+[item for pair in zip(batch.FLAGS_ORDER,[str(parent),nonce,self.profile['owner_sha256'],self.profile['manifest']['path'],batch.MANIFEST_SHA]) for item in pair]
   release={'status':'PASS_EXECUTION','case_id':cid,'command':command,'command_sha256':sha(json.dumps(command,separators=(',',':')).encode()),'profile_sha256':self.profile['_sha256'],'manifest_sha256':batch.MANIFEST_SHA,'nonce':nonce,'attempt_parent':str(parent),'expected_epochs':[[0,1,1],[0,2,2]],'fixture_only':True}
   p=self.work/('release%d.json'%i);p.write_text(json.dumps(release));cases.append({'case_id':cid,'command':command,'timeout_seconds':90,'release':ref(p),'output_name':'case-%d.json'%i,'nonce':nonce,'attempt_parent':str(parent)})
  obj={'schema_version':2,'kind':'p05-fixed-profile-serial-batch','profile':self.profile_ref,'cases':cases};p=self.work/'spec.json';p.write_text(json.dumps(obj));return p,obj
 def run_model(self,change=None,n=2):
  p,obj=self.make(n);hooks=Hooks(self.profile,change);result=batch.run_batch(str(p),str(self.work/'out'),hooks=hooks,now_ns=hooks.clock);return result,hooks,obj
 def first_record(self):return json.loads((self.work/'out/case-0.json').read_text())
 def test_actual_protocol_and_first_restoration_are_distinct(self):
  h=Hooks(self.profile);p,obj=self.make(1);c=obj['cases'][0];a=h.admit(c,None);e=h.execute(c,a);r=batch.evaluate_semantics(self.profile,e);self.assertTrue(r['qualifies_first_restore_reboot']);self.assertFalse(r['original_protocol']['complete_restoration_verified']);self.assertFalse(r['original_protocol']['quota_credit']);self.assertFalse(r['automatic_quota_credit'])
 def test_two_iterations_are_serial_and_retirement_chained(self):
  r,h,_=self.run_model();self.assertFalse(r['stopped_on_failure']);self.assertEqual(r['qualified_observations'],2);self.assertEqual(h.events,[('admit','modeled-0'),('execute','modeled-0'),('retire','modeled-0'),('admit','modeled-1'),('execute','modeled-1'),('retire','modeled-1')]);self.assertEqual(r['prior_cycle_credit_transferred'],0);self.assertFalse(r['automatic_native_acceptance'])
 def test_one_to_thirtytwo_count_boundary(self):
  p,obj=self.make(32);self.assertEqual(len(batch.validate_spec(obj)[1]),32)
  for cases in ([],obj['cases']+[obj['cases'][0]]):
   bad=copy.deepcopy(obj);bad['cases']=cases
   with self.assertRaises(batch.BatchError):batch.validate_spec(bad)
 def test_duplicate_nonce_parent_release_output_and_command_refused(self):
  p,obj=self.make(2)
  for field in ('nonce','attempt_parent','release','output_name','command'):
   bad=copy.deepcopy(obj);bad['cases'][1][field]=bad['cases'][0][field]
   with self.assertRaises(batch.BatchError):batch.validate_spec(bad)
 def test_argv_profile_widening_refused(self):
  p,obj=self.make();obj['cases'][0]['command'][4]='--fsize=67108864'
  with self.assertRaises(batch.BatchError):batch.validate_spec(obj)
 def test_no_runtime_backend_installed(self):
  p,_=self.make()
  with self.assertRaises(batch.BatchError):batch.run_batch(str(p),str(self.work/'out'))
  self.assertFalse((self.work/'out').exists())
 def test_future_v3_and_old_cycle_quota_rejected(self):
  for field,value in [('future_v3_artifacts',{'modules':'future'}),('prior_cycle_credit',1),('expected_epochs',[[0,9,9],[0,2,2]])]:
   data=json.loads((D/'FIXED-CURRENT-PROFILE.json').read_text());data[field]=value;p=self.work/(field+'.json');p.write_text(json.dumps(data))
   with self.assertRaises(batch.BatchError):batch.validate_profile(ref(p))
 def test_stale_admission_stops_without_execution(self):
  r,h,_=self.run_model(lambda phase,c,x:x.update(expires_ns=x['observed_ns']) if phase=='admit' else None);self.assertTrue(r['stopped_on_failure']);self.assertEqual(h.events,[('admit','modeled-0')])
 def test_missing_aggregate_or_resource_admission_stops(self):
  r,h,_=self.run_model(lambda phase,c,x:x.update(aggregate_admitted=False) if phase=='admit' else None);self.assertTrue(r['stopped_on_failure']);self.assertEqual(len(h.events),1)
 def test_foreign_execution_receipt_stops_and_retires(self):
  r,h,_=self.run_model(lambda phase,c,x:x.update(nonce='f'*32) if phase=='execute' else None);self.assertTrue(r['stopped_on_failure']);self.assertEqual(h.events[-1],('retire','modeled-0'));self.assertEqual(len(h.events),3)
 def test_execute_admission_binding_required(self):
  r,h,_=self.run_model(lambda phase,c,x:x.update(admission_sha256='0'*64) if phase=='execute' else None);self.assertTrue(r['stopped_on_failure']);self.assertEqual(r['qualified_observations'],0)
 def test_transport_zero_does_not_override_oracle(self):
  def change(phase,c,x):
   if phase=='execute':x['observation']['serial']=x['observation']['serial'].replace('68616e646c65643d31','68616e646c65643d30')
  r,h,_=self.run_model(change);self.assertTrue(r['stopped_on_failure']);self.assertEqual(r['qualified_observations'],0);self.assertEqual(h.events[-1],('retire','modeled-0'))
 def test_protocol_pass_without_first_prefix_is_not_qualified(self):
  r,h,_=self.run_model(lambda phase,c,x:x.update(kernel_before=b'') if phase=='execute' else None);self.assertTrue(r['stopped_on_failure']);self.assertEqual(self.first_record()['semantics']['protocol_status'],'PROTOCOL_PASS');self.assertFalse(self.first_record()['semantics']['qualifies_first_restore_reboot'])
 def test_expected_epoch_never_derived_from_observed_rows(self):
  def change(phase,c,x):
   if phase!='execute':return
   x['kernel_before']=x['kernel_before'].replace(b'epoch=1 ',b'epoch=9 ');lines=x['observation']['serial'].splitlines(keepends=True);buffers={}
   for name in ('before','after'):
    rows=[json.loads(line[len('ND_REBOOT_CHUNK '):]) for line in lines if line.startswith('ND_REBOOT_CHUNK ') and json.loads(line[len('ND_REBOOT_CHUNK '):])['name']==name];buffers[name]=b''.join(bytes.fromhex(r['hex']) for r in rows).replace(b'epoch=1 ',b'epoch=9 ')
   for i,line in enumerate(lines):
    if line.startswith('ND_REBOOT_CHUNK '):
     row=json.loads(line[len('ND_REBOOT_CHUNK '):]);name=row['name']
     if name in buffers:row['hex']=buffers[name][row['offset']:row['offset']+len(bytes.fromhex(row['hex']))].hex();lines[i]='ND_REBOOT_CHUNK '+json.dumps(row,separators=(',',':'))+'\r\n'
   x['observation']['serial']=''.join(lines)
  r,h,_=self.run_model(change);self.assertTrue(r['stopped_on_failure']);record=self.first_record();self.assertEqual(record['semantics']['protocol_status'],'PROTOCOL_PASS');self.assertIn('exact owner/epoch',record['semantics']['qualification_error'])
 def test_failed_owner_transport_stops_even_if_retirement_succeeds(self):
  r,h,_=self.run_model(lambda phase,c,x:x.update(returncode=1) if phase=='execute' else None);self.assertTrue(r['stopped_on_failure']);self.assertEqual(len(h.events),3)
 def test_uncertain_owner_retirement_never_advances(self):
  r,h,_=self.run_model(lambda phase,c,x:x.update(group_absent=False) if phase=='retire' else None);self.assertTrue(r['stopped_on_failure']);self.assertTrue(self.first_record()['uncertain']);self.assertEqual(r['qualified_observations'],0);self.assertEqual(len(h.events),3)
 def test_missing_canonical_exclusions_stops(self):
  r,h,_=self.run_model(lambda phase,c,x:x.update(canonical_exclusions_absent=False) if phase=='retire' else None);self.assertTrue(r['stopped_on_failure']);self.assertEqual(len(h.events),3)
 def test_lease_retention_is_not_retirement(self):
  r,h,_=self.run_model(lambda phase,c,x:x.update(lease_retained=True) if phase=='retire' else None);self.assertTrue(r['stopped_on_failure']);self.assertEqual(r['qualified_observations'],0)
 def test_retirement_must_follow_this_admission(self):
  r,h,_=self.run_model(lambda phase,c,x:x.update(retired_ns=1) if phase=='retire' else None);self.assertTrue(r['stopped_on_failure']);self.assertTrue(self.first_record()['uncertain'])
 def test_second_admission_requires_exact_previous_retirement(self):
  r,h,_=self.run_model(lambda phase,c,x:x.update(previous_retirement_sha256='0'*64) if phase=='admit' and c['case_id']=='modeled-1' else None);self.assertTrue(r['stopped_on_failure']);self.assertEqual(r['qualified_observations'],1);self.assertEqual(h.events[-1],('admit','modeled-1'))
 def test_timeout_uncertainty_has_no_retry_or_signal(self):
  def change(phase,c,x):
   if phase=='execute':raise subprocess.TimeoutExpired(c['command'],1)
   if phase=='retire':x['group_absent']=False
  r,h,_=self.run_model(change);self.assertTrue(r['stopped_on_failure']);self.assertTrue(self.first_record()['uncertain']);self.assertEqual(h.events,[('admit','modeled-0'),('execute','modeled-0'),('retire','modeled-0')])
 def test_source_manifest_and_release_drift_stop(self):
  p,obj=self.make();second=Path(obj['cases'][1]['release']['path'])
  def change(phase,c,x):
   if phase=='execute':second.write_text(second.read_text()+' ')
  h=Hooks(self.profile,change);r=batch.run_batch(str(p),str(self.work/'out'),hooks=h,now_ns=h.clock);self.assertTrue(r['stopped_on_failure']);self.assertEqual(len(h.events),3);self.assertIn('digest drift',self.first_record()['error'])
if __name__=='__main__':unittest.main(verbosity=2,failfast=True)
