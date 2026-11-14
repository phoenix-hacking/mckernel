"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
TEST_ONLY hypothetical postretirement records with genuine71/native history and
owner's exact14-receipt oracle. No guard, proc, command, capture, or cleanup calls.
"""
from pathlib import Path
import copy,io,json,tempfile,time,unittest
import observe_current64_current118_postjoin as m
D=Path(__file__).resolve().parent

def write(path,value):path.write_text(json.dumps(value,indent=2)+'\n');return m.ref(path)

def future_fixture(root):
 facts=m.validate_retained();executor=facts['executor'];builder=m.load(m.PINS['retirement_fixture'],'CURRENT118_shared14_TEST_ONLY')
 value,b=builder.build_result_fixture(root)
 value['cleanup_actor']['mutex_fd']=3
 value.update(final_safety=dict(mutex=dict(device=27,inode=4,fd=3)),own_fd_closed_only_after_result_on_normal_return=True,original_Docker_actor_gaps=b['actor_gaps'])
 rr=write(root/'TEST_ONLY-RESULT.json',value)
 stdout=root/'TEST_ONLY-RETIREMENT.stdout';stdout.write_text(json.dumps(dict(status='RETIREMENT_COMPLETE_PENDING_PARENT_JOIN_AND_FRESH_CURRENT',result=rr))+'\n')
 stderr=root/'TEST_ONLY-RETIREMENT.stderr';stderr.write_text('')
 parent=dict(TEST_ONLY=True,pid=value['cleanup_actor']['pid'],birth=value['cleanup_actor']['birth'],returncode=0,positive_direct_parent_wait=True,parent_streams_closed=True,stdout=m.ref(stdout),stderr=m.ref(stderr))
 parentref=write(root/'TEST_ONLY-RETIREMENT-JOIN.json',parent)
 _,retiredreceipts,retired=m.validate_retirement(facts,rr,parentref)
 binding=dict(phase='postjoin_candidate',ledger=m.PINS['pending_ledger'],retirement_result=rr,retirement_parent_join=parentref)
 first=[v-600 for v in m.PINS['limits']];last=[v+10 for v in first]
 history=copy.deepcopy(facts['base_capture']);history.pop('Root62');history.update(TEST_ONLY=True,status=facts['base'].CURRENT_STATUS,Root63=m.PINS['base_ledger'],actual_latest_operation_postjoin_acceptance=facts['prior']['latest_accepted_free_boundary'],observed_clocks=first,last_observed_clocks=last,fixed_cutoffs=m.PINS['limits'])
 history['observer_self']=dict(pid=700001,birth=200,group=700001)
 history['query_clients']=[];history['query_command_receipts']=[];history['complete_process_reports']=[]
 absent={r['pid']for r in facts['actors']+retired}
 inner=history['historical_Root61_reobservation'];inner['group_membership_observation']['rows']=[r for r in inner['group_membership_observation']['rows']if r['pid']not in absent and r['pgrp']not in absent]
 # Real original raw source ABI templates, with explicitly hypothetical process rows.
 original=facts['base'].validate_capture_commands(facts['base_capture'])
 oldreports=facts['base_capture']['complete_process_reports']
 report=executor.authenticated(value['proofs'][-1],True)['process']
 normal=m.load(b['normal'],'CURRENT118_TEST_ONLY_normal');code=executor.process_source(normal,m.checked(b['packet']))
 template=executor.authenticated(value['command_receipts'][0],True)
 new=[];newreports=[];clients=[]
 for index in range(8):
  process=None
  if index in (0,4,7):
   process=copy.deepcopy(oldreports[0]if index<5 else report)
   process.update(caller=[700001,'200'],challenge=('%x'%(index+1))*32)
   process['snapshots']=[[[1,0,'1'],[700001,1,'200']],[[1,0,'1'],[700001,1,'200']]]
   process['groups']=[[[1,0,'1',1,1],[700001,1,'200',700001,700001]],[[1,0,'1',1,1],[700001,1,'200',700001,700001]]]
   argv=copy.deepcopy(original[index]['argv'])if index<5 else['/usr/bin/sudo','-A','/usr/bin/python3','-I','-B','-c',code,'','700001','200']
   argv[7:]=[process['challenge'],'700001','200']
   (history['complete_process_reports']if index<5 else newreports).append(process)
  elif index<5:argv=original[index]['argv']
  else:argv=m.PREFIX+['ps','-aq','--no-trunc','--filter',('id='+m.CID)if index==5 else('name=^/'+m.NAME+'$')]
  row=copy.deepcopy(template);row.update(TEST_ONLY=True,pid=700100+index,birth=300+index,wait4_pid=700100+index,argv=argv,started_epoch=first[0]+index*.1,finished_epoch=first[0]+index*.1+.01)
  child=root/('TEST_ONLY-query-'+str(index));child.mkdir();so=child/'stdout';so.write_text(json.dumps(process)if process is not None else'');se=child/'stderr';se.write_text('')
  row['raw']=dict(stdout=m.ref(so),stderr=m.ref(se),**{'status.json':write(child/'status.json',dict(TEST_ONLY=True,state='exited',pid=row['pid'],exit_code=0,argv=argv))})
  rowref=write(child/'JOIN-WAIT4.json',row);clients.append(dict(pid=row['pid'],birth=row['birth']))
  if index<5:
   history['query_command_receipts'].append(rowref);history['query_clients'].append(clients[-1])
   if process is None:history['BFD_exact_absence_queries'][index-1]['command_receipt']=rowref
  else:new.append(rowref)
 capture=dict(TEST_ONLY=True,status=m.STATUS,Root64=m.PINS['pending_ledger'],current_boundary=m.PINS['pending_ledger'],actual_latest_operation_postjoin_acceptance=None,historical_Root63_reobservation=history,ordinary_CURRENT118_build_nonce=m.NONCE,retired_CURRENT118_CID=m.CID,retirement_result=rr,retirement_parent_join=parentref,all_recorded_actors_absent=facts['actors']+retired,current118_query_command_receipts=new,current118_complete_process_reports=newreports,query_clients=clients,observer_self=dict(pid=700001,birth=200,group=700001),observed_clocks=first,last_observed_clocks=last,fixed_cutoffs=m.PINS['limits'],boot_id=m.BOOT,current_free_candidate=True,independent_acceptance=False,current_physical_clearance_pending=True,artifact_acceptance=False,native_acceptance=False,runtime_authority=None,artifact_rejection=m.PINS['artifact_rejection'],registry_failure=m.PINS['registry_failure'],unknown_births_not_filled=facts['unknown_births'],unmeasured_actor_gaps=b['actor_gaps'],unmeasured_inherited_observer_client_births=True,complete_recursive_capture_scope=m.capture_scope(),fresh_postjoin_PID_FD_lock_absence=True)
 captureref=write(root/'TEST_ONLY-CAPTURE.json',capture)
 captureparent=dict(TEST_ONLY=True,pid=700001,starttime=200,returncode=0,positive_direct_wait_join=True,streams_closed=True,process_group_absent=True,remaining_group_members=[],group_observation_errors=[])
 cpref=write(root/'TEST_ONLY-CAPTURE-JOIN.json',captureparent)
 free=dict(TEST_ONLY=True,independent=True,implementation_ownership=False,decision='PASS_ROOT64_CURRENT118_POSTJOIN_CURRENT_FREE',current_free=True,Root64=m.PINS['pending_ledger'],actual_postjoin_observation=captureref,capture_positive_join=cpref,retirement_result=rr,retirement_parent_join=parentref,producer_nonce=m.NONCE,all_recorded_actors_absent=True,pids_current=0,no_existing_heavy=True,fresh_cleanup_PID_and_own_FD_absent=True,permanent_mutex_rows_absent=True,native_operation_reclassified_as_ordinary=False,artifact_acceptance=False,native_acceptance=False,artifact_rejection=m.PINS['artifact_rejection'],unknown_births_not_filled=facts['unknown_births'],unmeasured_actor_gaps=b['actor_gaps'],complete_recursive_capture_scope=m.capture_scope())
 freeref=write(root/'TEST_ONLY-FREE.json',free)
 ledger=m.checked(m.PINS['pending_ledger']);ledger.update(prior_ledger_retained=m.PINS['pending_ledger'],latest_accepted_free_boundary=freeref,current_physical_clearance_pending=False,recorded_epoch=last[0]+1,status='ROOT65_CURRENT118_POSTJOIN_ACCEPTED')
 ledger['current118_build'].update(normal_retirement_pending=False,current_physical_clearance_pending=False,current_free=freeref,retirement_result=rr,retirement_parent_join=parentref)
 ledgerref=write(root/'TEST_ONLY-ROOT65.json',ledger)
 schema=write(root/'TEST_ONLY-SCHEMA.json',m.observer_schema());sr=write(root/'TEST_ONLY-SCHEMA-REVIEW.json',dict(TEST_ONLY=True,independent=True,decision='PASS_EXACT_OBSERVER_SCHEMA_SOURCE_BINDING',reviewed_observer_schema=schema))
 boundary=write(root/'TEST_ONLY-BOUNDARY.json',dict(TEST_ONLY=True,author='/root',decision='BIND_EXISTING_REVIEWED_CURRENT_BUILD_BOUNDARY',root_attests_exact_current_boundary=True,nonce_ledger=ledgerref,native_custody_clearance=freeref,observer=m.ref(m.__file__),observer_schema=schema,observer_schema_review=sr,independent_current_boundary_review=write(root/'TEST_ONLY-BOUNDARY-REVIEW.json',dict(TEST_ONLY=True))))
 adopted=dict(binding,phase='accepted_current',pending_ledger=m.PINS['pending_ledger'],ledger=ledgerref,latest_free=freeref,current_boundary=boundary)
 return dict(TEST_ONLY=True,facts=facts,binding=binding,adopted=adopted,capture=capture,captureref=captureref,free=free,captureparent=captureparent,captureparentref=cpref,retirement=value,parent=parent,parentref=parentref)

class Current64(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.temp=tempfile.TemporaryDirectory(prefix='TEST_ONLY-current64-',dir=D);cls.root=Path(cls.temp.name);cls.f=future_fixture(cls.root)
 @classmethod
 def tearDownClass(cls):cls.temp.cleanup()
 def test_full_history72_and_124_actor_future_adoption(self):
  f=self.f;m.validate_pending_ledger(m.checked(m.PINS['pending_ledger']),f['facts'])
  self.assertEqual(len(m.validate_capture(f['capture'],f['binding'],f['facts'])),8)
  self.assertEqual(m.validate_current_adoption(f['adopted'],f['facts'])['status'],m.STATUS)
  self.assertEqual(len(f['facts']['actors']),109);self.assertEqual(len(f['capture']['all_recorded_actors_absent']),124)
  self.assertEqual(sum(r['start']is None for r in f['facts']['actors']),3)
 def test_pending_replay_drop_native_history_and_wrong_free_rejected(self):
  p=m.checked(m.PINS['pending_ledger'])
  variants=[]
  q=copy.deepcopy(p);q['consumed_nonces'].append(m.NONCE);variants.append(q)
  q=copy.deepcopy(p);q['consumed_nonces'][-1]='1d3f2239b2884cedbd9e7dbe248ae1aa';variants.append(q)
  q=copy.deepcopy(p);q['consumed_nonces'].pop(0);variants.append(q)
  q=copy.deepcopy(p);q['prior_ledger_retained']=p['latest_accepted_free_boundary'];variants.append(q)
  q=copy.deepcopy(p);q['current118_build']['artifact_acceptance']['accepted_default_remains']='CURRENT118';variants.append(q)
  q=copy.deepcopy(p);q['current_physical_clearance_pending']=False;variants.append(q)
  q=copy.deepcopy(p);q['current_native_operation']['nonce']=m.NONCE;variants.append(q)
  q=copy.deepcopy(p);q['latest_native_once_join']=p['latest_accepted_free_boundary'];variants.append(q)
  for q in variants:
   with self.subTest(case=len(q['consumed_nonces'])):
    with self.assertRaises(ValueError):m.validate_pending_ledger(q,self.f['facts'])
 def test_failed_incomplete_and_wrong_retirement_join_rejected(self):
  f=self.f
  for key,value in [('positive_direct_parent_wait',False),('birth',99),('returncode',1),('parent_streams_closed',False)]:
   q=dict(f['parent']);q[key]=value;r=write(self.root/('TEST_ONLY-badparent-'+key+'.json'),q)
   with self.assertRaises(ValueError):m.validate_retirement(f['facts'],f['binding']['retirement_result'],r)
  q=copy.deepcopy(f['retirement']);q['command_receipts'].pop();r=write(self.root/'TEST_ONLY-incomplete-result.json',q)
  with self.assertRaises(f['facts']['executor'].Refusal):m.validate_retirement(f['facts'],r,f['parentref'])
 def test_every_live_current118_A2_cleanup_actor_and_known_group_rejected(self):
  rows=self.f['capture']['all_recorded_actors_absent'];report=self.f['capture']['current118_complete_process_reports'][0]
  for row in rows:
   q=copy.deepcopy(report);q['snapshots'][0].append([row['pid'],1,str(row['start']or 1)]);q['groups'][0].append([row['pid'],1,str(row['start']or 1),1,1])
   with self.assertRaises(ValueError):m.validate_absence_reports([q],rows)
  for group in sorted({r['group']for r in rows if r['group']is not None}):
   q=copy.deepcopy(report);q['snapshots'][0].append([799999,1,'1']);q['groups'][0].append([799999,1,'1',group,group])
   with self.assertRaises(ValueError):m.validate_absence_reports([q],rows)
 def test_drop_wrong_actor_incomplete_census_age_and_claims_rejected(self):
  f=self.f;variants=[]
  q=copy.deepcopy(f['capture']);q['all_recorded_actors_absent'].pop();variants.append(q)
  q=copy.deepcopy(f['capture']);q['all_recorded_actors_absent'][-1]['start']+=1;variants.append(q)
  q=copy.deepcopy(f['capture']);q['current118_complete_process_reports']=[];variants.append(q)
  q=copy.deepcopy(f['capture']);q['last_observed_clocks'][1]=q['observed_clocks'][1]+120.001;variants.append(q)
  for key in ['native_acceptance','artifact_acceptance','independent_acceptance']:
   q=copy.deepcopy(f['capture']);q[key]=True;variants.append(q)
  q=copy.deepcopy(f['capture']);q['fresh_postjoin_PID_FD_lock_absence']=False;variants.append(q)
  for q in variants:
   with self.assertRaises(ValueError):m.validate_capture(q,f['binding'],f['facts'])
 def test_old_free_and_generic_capture_parent_strictness(self):
  f=self.f
  for key,value in [('actual_postjoin_observation',m.PINS['base_ledger']),('artifact_acceptance',True),('fresh_cleanup_PID_and_own_FD_absent',False)]:
   q=dict(f['free']);q[key]=value
   with self.assertRaises(ValueError):m.validate_acceptance(q,f['capture'],f['captureref'],f['captureparent'],f['captureparentref'],f['binding'],f['facts'])
  for key,value in [('process_group_absent',False),('positive_direct_wait_join',False),('starttime',201),('remaining_group_members',[{'pid':700001}])]:
   q=dict(f['captureparent']);q[key]=value
   with self.assertRaises(ValueError):m.validate_acceptance(f['free'],f['capture'],f['captureref'],q,f['captureparentref'],f['binding'],f['facts'])
 def test_adoption_does_not_rewrite_native_or_add_nonce(self):
  f=self.f;current=m.checked(f['adopted']['ledger'])
  for key,value in [('consumed_nonces',current['consumed_nonces']+[m.NONCE]),('reserved_abandoned_unconsumed_nonces',[]),('current_native_operation',{})]:
   q=copy.deepcopy(current);q[key]=value;b=dict(f['adopted'],ledger=write(self.root/('TEST_ONLY-bad-adopt-'+key+'.json'),q))
   with self.assertRaises(ValueError):m.validate_current_adoption(b,f['facts'])
 def test_new_operation_guard_pure_positive_old_operation_guardian_caps_negative(self):
  g=m.load(m.PINS['shared_guard'],'CURRENT118_pure_operation64')
  successor=json.loads((D/'ROOT64-OPERATION-SUCCESSOR.TEMPLATE.NOT-AUTHORITY.json').read_bytes())
  subjects={'observer':m.ref(m.__file__)}
  successor.update(author='/root',decision='EXPLICIT_OPERATION_WINDOW_SUCCESSOR',subjects=subjects,source_owners=['/root','/root/m14_compose'],minimum_cumulative_spent=str(g.load_predecessor().MIN_SPENT))
  review=dict(schema='mckernel.independent-operation-window-review.v1',decision='PASS_EXPLICIT_OPERATION_WINDOW_SUCCESSOR',independent=True,reviewer='/root/m14_review',operation=m.PINS['operation'],successor=successor)
  self.assertEqual(g.validate_operation(successor,review,m.PINS['operation'],subjects,[0,0,0]),tuple(m.PINS['limits']))
  for field,value in [('operation','current118-build'),('operation_cutoffs',[m.PINS['limits'][0],m.PINS['limits'][1]+1,m.PINS['limits'][2]]),('guardian',dict(source=m.PINS['base_source'],entrypoint='guard')),('predecessor_cutoffs',[0,0,0])]:
   bad=copy.deepcopy(successor);bad[field]=value;badreview=dict(review,successor=bad)
   with self.assertRaises(ValueError):g.validate_operation(bad,badreview,m.PINS['operation'],subjects,[0,0,0])
 def test_guard_identity_and_real_uuid_property(self):
  import uuid,ast
  self.assertRegex(uuid.uuid4().hex,'^[0-9a-f]{32}$')
  raw=Path(m.__file__).read_text();self.assertNotIn('uuid.uuid4().hex()',raw)
  ast.parse(raw)
  guard=m.load(m.PINS['guard'],'CURRENT118_guard_source_only');self.assertEqual(guard.OPERATION,'current118-postjoin-current64')
  self.assertEqual(m.capture_scope()['inherited_readonly_operation'],'bfd-postjoin-current62')
if __name__=='__main__':
 t=time.monotonic();stream=io.StringIO();r=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Current64));(D/'PURE-REGRESSION.stdout').write_text(stream.getvalue());print(stream.getvalue(),end='')
 result=dict(scope=__doc__.splitlines()[0],status='PASS'if r.wasSuccessful()else'FAIL',groups=r.testsRun,errors=len(r.errors),failures=len(r.failures),seconds=time.monotonic()-t,retained_history_rows=109,future_postretirement_rows=124,original_consumed=71,pending_consumed=72,raw_tracked_capture_clients=8,shared_retirement_raw_clients=14,actual_guard_query_cleanup_capture_calls=0,runtime_authority=None,stdout=m.ref(D/'PURE-REGRESSION.stdout'));(D/'PURE-REGRESSION.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result));raise SystemExit(0 if r.wasSuccessful()else 1)
