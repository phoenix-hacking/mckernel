"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Genuine failed custody plus TEST_ONLY future recovery/cleanup consumer records.
No actual observer/effect leaf, proc, guard, query, cleanup or signal is executed.
"""
from pathlib import Path
import ast,copy,io,json,tempfile,time,unittest
import observe_current64_current118_postjoin as m
D=Path(__file__).resolve().parent

def write(path,value):path.write_text(json.dumps(value,indent=2)+'\n');return m.ref(path)
def fixture(root):
 h=m.validate_retained();builder=m.load(m.PINS['retirement_fixture'],'compatible_shared14_oracle');value,b=builder.build_result_fixture(root)
 value['cleanup_actor']['mutex_fd']=3;value.update(final_safety=dict(mutex=dict(device=27,inode=4,fd=3)),own_fd_closed_only_after_result_on_normal_return=True,original_Docker_actor_gaps=b['actor_gaps'])
 rr=write(root/'TEST_ONLY-CLEANUP-RESULT.json',value);so=root/'TEST_ONLY-CLEANUP.stdout';so.write_text(json.dumps(dict(status='RETIREMENT_COMPLETE_PENDING_PARENT_JOIN_AND_FRESH_CURRENT',result=rr))+'\n');se=root/'TEST_ONLY-CLEANUP.stderr';se.write_text('')
 parent=write(root/'TEST_ONLY-CLEANUP-JOIN.json',dict(TEST_ONLY=True,pid=value['cleanup_actor']['pid'],birth=value['cleanup_actor']['birth'],returncode=0,positive_direct_parent_wait=True,parent_streams_closed=True,stdout=m.ref(so),stderr=m.ref(se)))
 # Reuse the owner's complete raw/positive-wait4 record shape. These generated
 # records are hypothetical recovery clients, explicitly confined to TEMP.
 template=m.checked(value['command_receipts'][0]);receipts=[]
 for i in range(12):
  child=root/('TEST_ONLY-recovery-client-'+str(i));child.mkdir();row=copy.deepcopy(template);argv=['TEST_ONLY_READONLY_RECOVERY_SNAPSHOT',str(i)]
  row.update(TEST_ONLY=True,pid=800100+i,birth=500+i,wait4_pid=800100+i,argv=argv)
  out=child/'stdout';out.write_text('TEST_ONLY');err=child/'stderr';err.write_text('');status=write(child/'status.json',dict(TEST_ONLY=True,state='exited',pid=row['pid'],argv=argv,exit_code=0))
  row['raw']=dict(stdout=m.ref(out),stderr=m.ref(err),**{'status.json':status});receipts.append(write(child/'JOIN-WAIT4.json',row))
 recovery=dict(TEST_ONLY=True,schema='mckernel.current118.failed-idle-helper.retirement-complete.v1',status='COMPLETE_FAILED_HELPER_RETIREMENT_PENDING_PARENT_JOIN',parent_positive_join_required=True,current_free=False,old_readonly_client_status='UNKNOWN',cleanup_required=True,acceptance_credit=False,target=dict(pid=2232651,starttime='103343097',parent=2232650,lock_fd=4),replacement_root_lock=[27,4],after=dict(command_receipts=receipts))
 recoveryref=write(root/'TEST_ONLY-RECOVERY-RESULT.json',recovery)
 targetparent=write(root/'TEST_ONLY-TARGET-PARENT-JOIN.json',dict(TEST_ONLY=True,author='/root',target_pid=2232651,target_birth='103343097',parent_pid=2232650,parent_birth='103343093',positive_direct_parent_wait=True,returncode=-9,streams_closed=True,tool_session=90401,first_readonly_client_status='UNKNOWN'))
 so=root/'TEST_ONLY-RECOVERY.stdout';so.write_text(json.dumps(dict(status=recovery['status'],receipt=recoveryref['path'],receipt_sha256=recoveryref['sha256'],cleanup_required=True))+'\n');se=root/'TEST_ONLY-RECOVERY.stderr';se.write_text('')
 op=dict(TEST_ONLY=True,author='/root',pid=800001,birth=400,parent_pid=800000,parent_birth=399,returncode=0,positive_direct_parent_wait=True,parent_streams_closed=True,start_epoch=m.PINS['limits'][0]-510,finish_epoch=m.PINS['limits'][0]-505,stdout=m.ref(so),stderr=m.ref(se))
 opref=write(root/'TEST_ONLY-RECOVERY-OPERATOR-JOIN.json',op)
 # Actual source identity remains byte-bound; TEMP reviews are not authority.
 source=m.PINS['recovery_parent_validator'];sr=write(root/'TEST_ONLY-RECOVERY-SOURCE-REVIEW.json',dict(TEST_ONLY=True,independent=True,implementation_ownership=False,decision='PASS_TEST_ONLY_SOURCE',files=dict(executor=source)))
 accept=dict(TEST_ONLY=True,independent=True,implementation_ownership=False,decision='PASS_EXACT_CURRENT118_FAILED_HELPER_RETIREMENT',current_free=False,old_readonly_client_status='UNKNOWN',recovery_source=source,recovery_result=recoveryref,target_parent_join=targetparent,operator_parent_join=opref)
 extra=[dict(pid=800001,start=400,role='CURRENT118_actual_recovery_operator',group=None,fd=None),dict(pid=800000,start=399,role='CURRENT118_actual_recovery_operator_parent',group=None,fd=None)]+[dict(pid=800100+i,start=500+i,role='CURRENT118_actual_recovery_recorded_command',group=800100+i,fd=None)for i in range(12)]
 custody=dict(TEST_ONLY=True,schema='mckernel.current118.post-root64-custody.v1',author='/root',decision='BIND_COMPLETE_RECORDED_POST_ROOT64_CUSTODY',runtime_authority=None,base_pending_ledger=m.PINS['pending_ledger'],failed_normal_attempt=m.PINS['failed_normal'],failed_recovery_join=m.PINS['failed_recovery_join'],all_post_base_custody_listed=True,root_attests_no_unlisted_post_base_operation=True,old_readonly_client_status='UNKNOWN',current_free=False,recovery_source=source,recovery_source_review=sr,recovery_result=recoveryref,target_parent_join=targetparent,operator_parent_join=opref,independent_recovery_acceptance=write(root/'TEST_ONLY-RECOVERY-ACCEPTANCE.json',accept),additional_measured_actors=extra,recorded_epoch=m.PINS['limits'][0]-500)
 cr=write(root/'TEST_ONLY-CUSTODY.json',custody);pending=m.checked(m.PINS['pending_ledger']);pending.update(prior_pending_ledger=m.PINS['pending_ledger'],post_Root64_retirement_custody=cr,recorded_epoch=custody['recorded_epoch']+1,declared_boundary='TEST_ONLY supplemented current frontier')
 return dict(facts=h,value=value,retirement=rr,parent=parent,custody=custody,custodyref=cr,pending=pending,binding=dict(custody_supplement=cr))

class Compatibility(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.tmp=tempfile.TemporaryDirectory(prefix='TEST_ONLY-compat-interface-',dir=D);cls.root=Path(cls.tmp.name);cls.f=fixture(cls.root)
 @classmethod
 def tearDownClass(cls):cls.tmp.cleanup()
 def test_genuine_failed_history114_unknown_and_exact12runtime_refs(self):
  h=self.f['facts'];self.assertEqual(len(h['actors']),114);self.assertEqual(h['actors'][-5]['fd'],4);self.assertEqual(h['actors'][-1]['pid'],2247305)
  self.assertFalse(m.checked(m.PINS['failed_normal'])['returncode_claimed']);self.assertEqual(len(m.checked(m.PINS['compatibility_runtime_files'])),12)
 def test_compatible14_result_parent_join_positive_and_old417_rejected(self):
  f=self.f;_,r,a=m.validate_retirement(f['facts'],f['retirement'],f['parent']);self.assertEqual((len(r),len(a)),(14,15))
  old=m.load(m.PINS['source1_observer'],'banked_source1_unchanged')
  oldfacts=old.validate_retained()
  with self.assertRaises(oldfacts['executor'].Refusal):old.validate_retirement(oldfacts,f['retirement'],f['parent'])
 def test_required_future_supplement_and_truthful72_pending_positive(self):
  h=m.validate_retained();m.attach_custody(self.f['binding'],h);self.assertEqual(len(h['actors']),128);self.assertTrue(m.validate_pending_ledger(self.f['pending'],h));m.attach_custody(self.f['binding'],h);self.assertEqual(len(h['actors']),128)
  self.assertEqual(self.f['pending']['consumed_nonces'],m.checked(m.PINS['pending_ledger'])['consumed_nonces'])
 def test_missing_stale_supplement_and_old683_current_alias_rejected(self):
  h=m.validate_retained()
  with self.assertRaises(ValueError):m.validate_pending_ledger(m.checked(m.PINS['pending_ledger']),h)
  m.attach_custody(self.f['binding'],h)
  with self.assertRaises(ValueError):m.validate_pending_ledger(m.checked(m.PINS['pending_ledger']),h)
  q=copy.deepcopy(self.f['pending']);q['consumed_nonces'].append(m.NONCE)
  with self.assertRaises(ValueError):m.validate_pending_ledger(q,h)
 def test_unknown_status_bad_target_join_drop_future_actor_rejected(self):
  for key,value in [('old_readonly_client_status','PASS'),('all_post_base_custody_listed',False),('additional_measured_actors',self.f['custody']['additional_measured_actors'][:-1]),('recorded_epoch',1)]:
   q=copy.deepcopy(self.f['custody']);q[key]=value;r=write(self.root/('TEST_ONLY-bad-custody-'+key+'.json'),q)
   with self.assertRaises(ValueError):m.attach_custody(dict(custody_supplement=r),m.validate_retained())
  q=copy.deepcopy(self.f['custody']);j=m.checked(q['target_parent_join']);j['returncode']=0;q['target_parent_join']=write(self.root/'TEST_ONLY-bad-target-join.json',j)
  with self.assertRaises(ValueError):m.attach_custody(dict(custody_supplement=write(self.root/'TEST_ONLY-bad-target-custody.json',q)),m.validate_retained())
 def test_all_new_failed_and_future_actor_presence_rejected(self):
  h=m.validate_retained();m.attach_custody(self.f['binding'],h);report=dict(snapshots=[[[1,0,'1']],[[1,0,'1']]],groups=[[[1,0,'1',1,1]],[[1,0,'1',1,1]]]);m.validate_absence_reports([report],h['actors'])
  for a in h['actors'][109:]:
   bad=copy.deepcopy(report);bad['snapshots'][0].append([a['pid'],1,str(a['start'])]);bad['groups'][0].append([a['pid'],1,str(a['start']),1,1])
   with self.assertRaises(ValueError):m.validate_absence_reports([bad],h['actors'])
 def test_original_retirement_absence_query_main_and_final_clock_predicates_unchanged(self):
  old=ast.parse(m.auth(m.PINS['source1_observer']).read_bytes());new=ast.parse(Path(m.__file__).read_bytes())
  funcs=lambda tree:{n.name:n for n in tree.body if isinstance(n,ast.FunctionDef)}
  a=funcs(old);b=funcs(new)
  for name in ['validate_retirement','validate_absence_reports','validate_new_commands','main']:
   self.assertEqual(ast.dump(a[name],include_attributes=False),ast.dump(b[name],include_attributes=False),name)
  nested=lambda n:next(x for x in ast.walk(n)if isinstance(x,ast.FunctionDef)and x.name=='before_popen')
  self.assertEqual(ast.dump(nested(a['observe']),include_attributes=False),ast.dump(nested(b['observe']),include_attributes=False))
  self.assertEqual(m.PROFILE,dict(uid=1000,cpus=[0],jobs=1,address_space_bytes=2<<30,maximum_CPU_seconds=60,maximum_wall_seconds=120))
if __name__=='__main__':
 t=time.monotonic();stream=io.StringIO();r=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Compatibility));(D/'PURE-COMPATIBILITY.stdout').write_text(stream.getvalue());print(stream.getvalue(),end='');v=dict(scope=__doc__.splitlines()[0],status='PASS'if r.wasSuccessful()else'FAIL',groups=r.testsRun,errors=len(r.errors),failures=len(r.failures),seconds=time.monotonic()-t,genuine_pre_recovery_rows=114,TEST_ONLY_future_recovery_rows=128,TEST_ONLY_future_with_cleanup_rows=143,consumed_nonces=72,actual_guard_proc_query_cleanup_capture_signal_calls=0,runtime_authority=None);(D/'PURE-COMPATIBILITY.json').write_text(json.dumps(v,indent=2)+'\n');print(json.dumps(v));raise SystemExit(0 if r.wasSuccessful()else 1)
