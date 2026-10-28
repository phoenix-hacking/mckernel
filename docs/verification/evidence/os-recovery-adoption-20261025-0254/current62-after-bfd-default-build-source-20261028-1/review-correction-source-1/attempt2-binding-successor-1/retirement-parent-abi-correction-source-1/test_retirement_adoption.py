"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Reuse the owner's complete14-command retirement oracle, then test only the new
typed parentjoin/candidate/current adoption layer using hypothetical TEMP records.
"""
from pathlib import Path
import ast
import copy
import io
import json
import tempfile
import types
import unittest
import observe_current62_bfd_postjoin as m

D=Path(__file__).resolve().parent
def write(path,value):
 path.write_text(json.dumps(value,indent=2)+'\n');return m.ref(path)

def future_fixture(root):
 executor=m.load(m.PINS['retirement_executor'],'pure_62_retirement_ADAPTER')
 builder=m.load(m.PINS['positive_retirement_fixture_builder'],'shared14command_ORACLE')
 value,b=builder.build_result_fixture(root)
 # These are the additional actual Actual.finish ABI fields, absent from the
 # owner's narrower pure RESULT fixture. Every record remains TEST_ONLY.
 value['cleanup_actor']['mutex_fd']=3
 value.update(final_safety=dict(mutex=dict(device=27,inode=4,holder=999999,fd=3)),own_fd_closed_only_after_result_on_normal_return=True,original_Docker_actor_gaps=b['actor_gaps'])
 retirement=write(root/'TEST_ONLY-RESULT.json',value)
 stdout=root/'TEST_ONLY-RETIREMENT.stdout';stdout.write_text(json.dumps(dict(status='RETIREMENT_COMPLETE_PENDING_PARENT_JOIN_AND_FRESH_CURRENT',result=retirement))+'\n')
 stderr=root/'TEST_ONLY-RETIREMENT.stderr';stderr.write_text('')
 join=dict(TEST_ONLY=True,pid=999999,birth=100,returncode=0,positive_direct_parent_wait=True,parent_streams_closed=True,stdout=m.ref(stdout),stderr=m.ref(stderr))
 retirement_join=write(root/'TEST_ONLY-RETIREMENT-PARENT-JOIN.json',join)
 _,_,_,actors=m.validate_retirement(executor,retirement,retirement_join)
 facts=m.validate_retained();pending=json.loads((D/'ROOT62-PENDING-LEDGER.TEMPLATE.NOT-AUTHORITY.json').read_bytes())
 pending.update(TEST_ONLY=True,author='/root',complete_within_declared_current_boundary=True,root_attests_no_unlisted_post_boundary_execution_or_custody_operation=True,current_thread='01a183ec-72e5-7400-8f48-b4efb8725520',recorded_epoch=1793218000)
 pendingref=write(root/'TEST_ONLY-Root62.json',pending)
 history=copy.deepcopy(m.checked(m.checked(m.PINS['physical_join'])['physical'])['physical'])
 absent={row['pid']for row in facts['actors']+actors}
 history['group_membership_observation']['rows']=[row for row in history['group_membership_observation']['rows']if row['pid']not in absent and row['pgrp']not in absent]
 queries=[dict(TEST_ONLY=True,argv=argv,returncode=0,stdout='',stderr='')for argv in [m.PREFIX+['ps','-q','--no-trunc'],m.PREFIX+['ps','-aq','--no-trunc','--filter','id='+m.CID],m.PREFIX+['ps','-aq','--no-trunc','--filter','name=^/'+m.NAME+'$']]]
 clocks=[v-600 for v in m.PINS['limits']]
 capture=m.consumer_value(history,pendingref,retirement,retirement_join,facts['actors']+actors,queries,clocks,clocks,m.PINS['limits'])
 capture.update(TEST_ONLY=True,observer_self=dict(pid=700001,birth=200,group=700001),query_clients=[],query_command_receipts=[],complete_process_reports=[],unmeasured_actor_gaps=b['actor_gaps'],unmeasured_inherited_observer_client_births=True,inherited_observer_client_births_are_not_claimed_recorded=True,complete_recursive_capture_scope=m.capture_scope())
 raw_report=executor.authenticated(value['proofs'][-1],True)['process']
 tree=ast.parse(m.auth(b['normal']).read_bytes());literal=next(ast.literal_eval(node.value)for node in tree.body if isinstance(node,ast.Assign)and any(isinstance(t,ast.Name)and t.id=='PROC_CODE'for t in node.targets))
 code=executor.process_source(types.SimpleNamespace(PROC_CODE=literal),m.checked(b['packet']))
 template=executor.authenticated(value['command_receipts'][0],True)
 for index in range(5):
  report=None
  if index in (0,4):
   report=copy.deepcopy(raw_report);report['caller']=[700001,'200'];report['challenge']=('e'if index==0 else'f')*32
   report['snapshots']=[[[1,0,'1'],[700001,1,'200']],[[1,0,'1'],[700001,1,'200']]]
   report['groups']=[[[1,0,'1',1,1],[700001,1,'200',700001,700001]],[[1,0,'1',1,1],[700001,1,'200',700001,700001]]]
   argv=['/usr/bin/sudo','-A','/usr/bin/python3','-I','-B','-c',code,report['challenge'],'700001','200']
   capture['complete_process_reports'].append(report)
  else:argv=queries[index-1]['argv']
  row=copy.deepcopy(template);row.update(TEST_ONLY=True,pid=700100+index,birth=300+index,wait4_pid=700100+index,argv=argv)
  child=root/('TEST_ONLY-query-'+str(index));child.mkdir()
  stdout=child/'stdout';stdout.write_text(json.dumps(report)if report is not None else'')
  stderr=child/'stderr';stderr.write_text('')
  status=write(child/'status.json',dict(TEST_ONLY=True,state='exited',pid=row['pid'],exit_code=0,argv=argv))
  row['raw']=dict(stdout=m.ref(stdout),stderr=m.ref(stderr),**{'status.json':status})
  rr=write(child/'JOIN-WAIT4.json',row);capture['query_command_receipts'].append(rr);capture['query_clients'].append(dict(pid=row['pid'],birth=row['birth']))
  if report is None:queries[index-1]['command_receipt']=rr
 capture['known_numeric_controls_absent']=sorted(set(capture['known_numeric_controls_absent']+[row['pid']for row in capture['query_clients']]))
 captureref=write(root/'TEST_ONLY-CAPTURE.json',capture)
 capture_join=dict(TEST_ONLY=True,pid=700001,starttime=200,returncode=0,positive_direct_wait_join=True,streams_closed=True,process_group_absent=True,remaining_group_members=[],group_observation_errors=[])
 capture_joinref=write(root/'TEST_ONLY-CAPTURE-PARENT-JOIN.json',capture_join)
 free=dict(TEST_ONLY=True,independent=True,implementation_ownership=False,decision='PASS_ROOT62_BFD_POSTJOIN_CURRENT_FREE',current_free=True,Root62=pendingref,actual_postjoin_observation=captureref,capture_positive_join=capture_joinref,retirement_result=retirement,retirement_parent_join=retirement_join,producer_nonce=m.NONCE,native_operation_reclassified_as_ordinary=False,pids_current=0,no_existing_heavy=True,all_recorded_actors_absent=True,unmeasured_producer_Docker_client_births=True,unmeasured_births_are_not_claimed_retired=True,unmeasured_actor_gaps=b['actor_gaps'],runtime_authority=None)
 free.update(unmeasured_inherited_observer_client_births=True,inherited_observer_client_births_are_not_claimed_recorded=True)
 freeref=write(root/'TEST_ONLY-NEW-CURRENT-FREE.json',free)
 current=copy.deepcopy(pending);current.update(prior_ledger_retained=pendingref,latest_accepted_free_boundary=freeref,current_physical_clearance_pending=False,recorded_epoch=1793218100)
 current['bfd_default_build'].update(current_physical_clearance_pending=False,current_free=freeref)
 currentref=write(root/'TEST_ONLY-Root63.json',current)
 schema=m.ref(D/'OBSERVER-SCHEMA.ROOT63-CURRENT.SOURCE-ONLY.json')
 sr=write(root/'TEST_ONLY-SCHEMA-REVIEW.json',dict(TEST_ONLY=True,independent=True,decision='PASS_EXACT_OBSERVER_SCHEMA_SOURCE_BINDING',reviewed_observer_schema=schema))
 boundary=dict(TEST_ONLY=True,author='/root',decision='BIND_EXISTING_REVIEWED_CURRENT_BUILD_BOUNDARY',root_attests_exact_current_boundary=True,nonce_ledger=currentref,native_custody_clearance=freeref,observer=m.ref(m.__file__),independent_current_boundary_review=write(root/'TEST_ONLY-BOUNDARY-REVIEW.json',dict(TEST_ONLY=True)),observer_schema=schema,observer_schema_review=sr)
 boundaryref=write(root/'TEST_ONLY-CURRENT-BOUNDARY.json',boundary)
 binding=dict(ledger=currentref,pending_ledger=pendingref,latest_free=freeref,current_boundary=boundaryref,retirement_result=retirement,retirement_parent_join=retirement_join)
 return dict(executor=executor,facts=facts,binding=binding,capture=capture,captureref=captureref,free=free,capture_join=capture_join,capture_joinref=capture_joinref,pendingref=pendingref,retirement=retirement,retirement_join=retirement_join)

class Adoption(unittest.TestCase):
 def test_exact_shared14_result_plus_real_parentjoin_and_current_adoption(self):
  with tempfile.TemporaryDirectory(prefix='TEST_ONLY-current62-adoption-',dir=D)as directory:
   f=future_fixture(Path(directory))
   self.assertTrue(m.validate_acceptance(f['free'],f['capture'],f['captureref'],f['capture_join'],f['capture_joinref'],f['pendingref'],f['retirement'],f['retirement_join']))
   result=m.validate_current_adoption(f['binding'],f['facts']);self.assertEqual(result['status'],m.STATUS)
   self.assertEqual(len(m.checked(f['binding']['ledger'])['consumed_nonces']),71)
 def test_old_free_missing_join_unknown_birth_and_duplicate_nonce_rejected(self):
  with tempfile.TemporaryDirectory(prefix='TEST_ONLY-current62-negative-',dir=D)as directory:
   root=Path(directory);f=future_fixture(root)
   for field,value in [('positive_direct_wait_join',False),('starttime',199)]:
    bad=dict(f['capture_join']);bad[field]=value
    with self.assertRaises(ValueError):m.validate_acceptance(f['free'],f['capture'],f['captureref'],bad,f['capture_joinref'],f['pendingref'],f['retirement'],f['retirement_join'])
   bad=copy.deepcopy(f['capture']);bad['query_clients'][0]['birth']+=1
   with self.assertRaises(ValueError):m.validate_acceptance(f['free'],bad,f['captureref'],f['capture_join'],f['capture_joinref'],f['pendingref'],f['retirement'],f['retirement_join'])
   bad=dict(f['free']);bad['actual_postjoin_observation']=m.checked(m.PINS['prior_ledger'])['latest_accepted_free_boundary']
   with self.assertRaises(ValueError):m.validate_acceptance(bad,f['capture'],f['captureref'],f['capture_join'],f['capture_joinref'],f['pendingref'],f['retirement'],f['retirement_join'])
   current=m.checked(f['binding']['ledger']);current['consumed_nonces'].append(m.NONCE)
   badbinding=dict(f['binding'],ledger=write(root/'TEST_ONLY-REPLAY-Root63.json',current))
   with self.assertRaises(ValueError):m.validate_current_adoption(badbinding,f['facts'])

if __name__=='__main__':
 stream=io.StringIO();result=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Adoption))
 (D/'PURE-RETIREMENT-ADOPTION.stdout').write_text(stream.getvalue())
 summary=dict(scope=__doc__.splitlines()[0],status='PASS_PURE_RETIREMENT_PARENTJOIN_CURRENT_ADOPTION'if result.wasSuccessful()else'FAIL',tests=result.testsRun,errors=len(result.errors),failures=len(result.failures),shared_retirement_command_oracle=14,actual_guard_query_cleanup_capture_calls=0,actual_ledger_authorship=0,runtime_authority=None,stdout=m.ref(D/'PURE-RETIREMENT-ADOPTION.stdout'))
 (D/'PURE-RETIREMENT-ADOPTION.json').write_text(json.dumps(summary,indent=2)+'\n');print(stream.getvalue(),end='');print(json.dumps(summary,indent=2));raise SystemExit(0 if result.wasSuccessful()else 1)
