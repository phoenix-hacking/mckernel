"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Genuine retained history plus clearly hypothetical postretirement test facts only.
No observe/guard/query/process/capture/export/native/compiler call is permitted.
"""
from pathlib import Path
import copy
import io
import json
import tempfile
import unittest
import observe_current62_bfd_postjoin as m

D=Path(__file__).resolve().parent

class Current62(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.facts=m.validate_retained()
  cls.pending=json.loads((D/'ROOT62-PENDING-LEDGER.TEMPLATE.NOT-AUTHORITY.json').read_bytes())
  cls.pending.update(TEST_ONLY=True,author='/root',complete_within_declared_current_boundary=True,root_attests_no_unlisted_post_boundary_execution_or_custody_operation=True,current_thread='01a183ec-72e5-7400-8f48-b4efb8725520',recorded_epoch=1793218000)
  source=m.checked(m.PINS['physical_join'])['physical'];cls.history=copy.deepcopy(m.checked(source)['physical'])
  absent={row['pid']for row in cls.facts['actors']}
  cls.history['group_membership_observation']['rows']=[row for row in cls.history['group_membership_observation']['rows']if row['pid']not in absent and row['pgrp']not in absent]
  cls.history['TEST_ONLY_future_postretirement_effects']=True
  cls.queries=[dict(argv=argv,returncode=0,stdout='',stderr='',TEST_ONLY=True)for argv in [m.PREFIX+['ps','-q','--no-trunc'],m.PREFIX+['ps','-aq','--no-trunc','--filter','id='+m.CID],m.PREFIX+['ps','-aq','--no-trunc','--filter','name=^/'+m.NAME+'$']]]
  cls.clocks=[value-600 for value in m.PINS['limits']]
 def test_genuine_producer_joins_and_history_multiset(self):
  self.assertTrue(m.validate_pending_ledger(m.checked(m.PINS['actual_pending_root62']),self.facts))
  self.assertEqual(len(self.facts['prior']['consumed_nonces']),70)
  self.assertEqual(len(self.facts['prior_actors']),61)
  self.assertEqual(len({(r['pid'],r['start'])for r in self.facts['prior_actors']}),56)
  self.assertEqual(self.facts['actors'][:61],self.facts['prior_actors'])
  self.assertEqual([(r['pid'],r['start'])for r in self.facts['actors'][61:]],[(2124365,101427979),(2124454,101432667),(2123297,101423116),(2123451,101426466),(2124389,101429895),(2145640,101816056),(2153594,101972261),(2153595,101972338),(2153599,101972387),(2153607,101972458),(2153616,101972497)])
 def test_pending71_and_candidate_never_self_accepts(self):
  self.assertTrue(m.validate_pending_ledger(self.pending,self.facts))
  self.assertTrue(m.validate_fresh_physical(self.history,self.facts['actors'],self.queries,self.clocks,self.clocks,m.PINS['limits']))
  result=m.consumer_value(self.history,dict(TEST_ONLY=True),dict(TEST_ONLY=True),dict(TEST_ONLY=True),self.facts['actors'],self.queries,self.clocks,self.clocks,m.PINS['limits'])
  self.assertIsNone(result['actual_latest_operation_postjoin_acceptance']);self.assertTrue(result['current_physical_clearance_pending'])
  self.assertEqual(result['historical_Root61_reobservation'],self.history)
  self.assertTrue(result['unmeasured_producer_Docker_client_births']);self.assertNotIn('Root61',result)
  self.assertTrue({row['pid']for row in self.facts['actors']}<=set(result['known_numeric_controls_absent']))
 def test_nonce_replay_and_history_relabel_rejected(self):
  for mutate in [lambda x:x['consumed_nonces'].append(m.NONCE),lambda x:x['current_native_operation'].__setitem__('nonce',m.NONCE),lambda x:x.__setitem__('current_physical_clearance_pending',False),lambda x:x['ordinary_operations_since_prior_heavy_boundary'].pop()]:
   bad=copy.deepcopy(self.pending);mutate(bad)
   with self.assertRaises(ValueError):m.validate_pending_ledger(bad,self.facts)
 def test_missing_tool_join_wrong_birth_and_old_thread_rejected(self):
  for mutate in [lambda x:x['bfd_default_build'].__setitem__('actual_holder_tool_join_receipt',None),lambda x:x['bfd_default_build']['failed_retirement_attempts'].pop(),lambda x:x.__setitem__('prior_pending_ledger',m.PINS['original_pending_root62']),lambda x:x['bfd_default_build'].__setitem__('nonce','0'*32),lambda x:x.__setitem__('current_thread','01a18111-26a7-7ef2-bbd6-e33d1c8dc803'),lambda x:x.__setitem__('recorded_epoch',1793166745)]:
   bad=copy.deepcopy(self.pending);mutate(bad)
   with self.assertRaises(ValueError):m.validate_pending_ledger(bad,self.facts)
 def test_surviving_actor_group_or_incomplete_census_rejected(self):
  for mutate in [lambda x:x['group_membership_observation']['rows'].append(dict(pid=700001,pgrp=2124454)),lambda x:x['group_membership_observation']['errors'].append(dict(TEST_ONLY=True)),lambda x:x.__setitem__('pids_current',1)]:
   bad=copy.deepcopy(self.history);mutate(bad)
   with self.assertRaises(ValueError):m.validate_fresh_physical(bad,self.facts['actors'],self.queries,self.clocks,self.clocks,m.PINS['limits'])
 def test_wrong_CID_nonempty_reply_and_wider_clock_rejected(self):
  for index,update in [(1,dict(argv=m.PREFIX+['ps','-aq','--no-trunc','--filter','id='+'0'*64])),(2,dict(stdout=m.CID+'\n'))]:
   bad=copy.deepcopy(self.queries);bad[index].update(update)
   with self.assertRaises(ValueError):m.validate_fresh_physical(self.history,self.facts['actors'],bad,self.clocks,self.clocks,m.PINS['limits'])
  bad=list(m.PINS['limits']);bad[1]+=1
  with self.assertRaises(ValueError):m.validate_fresh_physical(self.history,self.facts['actors'],self.queries,self.clocks,self.clocks,bad)
 def test_parent_join_must_be_separate_complete_and_exact(self):
  actor=dict(pid=700002,birth=123456)
  join=dict(TEST_ONLY=True,pid=700002,starttime=123456,returncode=0,positive_direct_wait_join=True,streams_closed=True,process_group_absent=True,remaining_group_members=[],group_observation_errors=[])
  m.validate_parent_join(join,actor)
  for field,value in [('returncode',1),('positive_direct_wait_join',False),('starttime',123455),('process_group_absent',False)]:
   bad=dict(join);bad[field]=value
   with self.assertRaises(ValueError):m.validate_parent_join(bad,actor)

if __name__=='__main__':
 stream=io.StringIO();result=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Current62))
 (D/'PURE-CURRENT62.stdout').write_text(stream.getvalue())
 value=dict(scope=__doc__.splitlines()[0],status='PASS_PURE_TYPED_CURRENT62_ONLY'if result.wasSuccessful()else'FAIL',tests=result.testsRun,errors=len(result.errors),failures=len(result.failures),genuine_prior_actor_rows=61,genuine_prior_unique_pairs=56,new_recorded_BFD_and_failure_actor_rows=11,future_pending_nonce_count=71,actual_guards=0,actual_queries=0,actual_captures=0,actual_cleanup=0,compiler_native_export_calls=0,runtime_authority=None,stdout=m.ref(D/'PURE-CURRENT62.stdout'))
 (D/'PURE-CURRENT62.json').write_text(json.dumps(value,indent=2)+'\n');print(stream.getvalue(),end='');print(json.dumps(value,indent=2));raise SystemExit(0 if result.wasSuccessful()else 1)
