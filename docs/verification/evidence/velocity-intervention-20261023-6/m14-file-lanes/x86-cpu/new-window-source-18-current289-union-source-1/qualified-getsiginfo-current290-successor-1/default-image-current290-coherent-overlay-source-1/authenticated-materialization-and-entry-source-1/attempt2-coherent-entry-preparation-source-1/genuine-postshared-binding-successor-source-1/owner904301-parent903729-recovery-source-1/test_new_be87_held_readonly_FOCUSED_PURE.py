"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Focused new held-profile immutable/mocked controls. No actual rootquery/flock/signal/unlink.
"""
from pathlib import Path
import ast,copy,hashlib,importlib.util,json,unittest
from unittest import mock
D=Path(__file__).parent;r=json.loads((D/'READY-NEW-BE87-HELD-READONLY.SOURCE.json').read_bytes());raw=Path(r['source']['path']).read_bytes();assert hashlib.sha256(raw).hexdigest()==r['source']['sha256'];spec=importlib.util.spec_from_file_location('actual_newbe87_held_reader_pure',r['source']['path']);a=importlib.util.module_from_spec(spec);spec.loader.exec_module(a)
class ProfileTests(unittest.TestCase):
 def test_real_new_failure_pins_request_relation_and_typed_baseline(self):
  self.assertEqual(len(a.new_failure_inputs()),22);self.assertTrue(a.original_request_relation());self.assertEqual(len(a.accepted_prerequisites()),44)
  for ref in a.r['historical_old_shared_proofs']:a.fixed(ref)
 def test_new58_absent14_publishers_parent_excluded(self):
  self.assertEqual(len(a.m.ABSENT),58);self.assertEqual(len(a.sources),14);self.assertNotIn(903729,a.m.ABSENT);self.assertTrue({898578,904301,903731,903732,903733,903734,903740,904143}<=a.m.ABSENT);self.assertTrue({row['path'] for row in a.r['new_family_publisher_sources']}<=set(a.sources));self.assertEqual(a.r['new_failed_owner']['request_sha256'],'5a20b25385d0df0dd233539e5f745222990526da14447d7c9053ea646dac74a7')
 def test_same_inode_new_hash_exactly_required(self):
  data=(json.dumps(a.r['shared_value'],sort_keys=True)+'\n').encode();self.assertEqual(hashlib.sha256(data).hexdigest(),a.r['shared_identity']['sha256'])
  with mock.patch.object(a.m,'file_identity',return_value=(a.r['shared_identity'],data)),mock.patch.object(a.os.path,'lexists',return_value=False):self.assertEqual(a.shared_phase(True)['original_identity']['inode'],116858)
  old=dict(a.r['shared_identity'],sha256='324ae871e07d57c1453e57473b64bb31f947d073a9a903b1adca1dad1c1aaaed')
  with mock.patch.object(a.m,'file_identity',return_value=(old,data)),mock.patch.object(a.os.path,'lexists',return_value=False),self.assertRaises(a.m.Refusal):a.shared_phase(True)
 def test_affected_path_or_release_phase_refused(self):
  data=(json.dumps(a.r['shared_value'],sort_keys=True)+'\n').encode()
  with mock.patch.object(a.m,'file_identity',return_value=(a.r['shared_identity'],data)),mock.patch.object(a.os.path,'lexists',return_value=True),self.assertRaises(a.m.Refusal):a.shared_phase(True)
  with self.assertRaises(a.m.Refusal):a.shared_phase(False)
 def test_bad_new_owner_join_refused(self):
  original=a.m.read_json
  def read(path,expected=None):
   value=original(path,expected)
   if Path(path).name=='owner.JOIN.json':value=dict(value,returncode=0)
   return value
  with mock.patch.object(a.m,'read_json',side_effect=read),self.assertRaises(a.m.Refusal):a.new_failure_inputs()
 def test_actual_before_effects_source_order_and_no_mutator_entry(self):
  owner=ast.parse(Path(a.r['new_owner_source']['path']).read_bytes());cls=next(n for n in owner.body if isinstance(n,ast.ClassDef) and n.name=='ImageOwner');run=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='run');self.assertEqual(run.body[1].lineno,1487);self.assertEqual(run.body[2].lineno,1489)
  source=ast.parse(Path(r['source']['path']).read_bytes());forbidden={'unlink','archive_and_unlink_one','mark_unlink_attempt','pidfd_open','sole_sigkill','kill','killpg','acquire_root_lock','quarantine_hold'}
  for node in ast.walk(source):
   if isinstance(node,ast.Call):self.assertNotIn(node.func.attr if isinstance(node.func,ast.Attribute) else node.func.id if isinstance(node.func,ast.Name) else None,forbidden)
  self.assertFalse(Path(a.r['archive_directory']).exists());self.assertEqual(a.r['private_root_readonly_capture']['sha256'],'48d0fbc7dd9cf915cc219788015cc00b023abb2edaa1833b2da6fc8477834925')
class BranchTests(unittest.TestCase):
 def run_mocked(self,fail=False,drift=False):
  self.calls=[];self.published=[];baseline=a.accepted_prerequisites()
  def snapshot(label,before):
   self.calls.append((label,before))
   if fail and label=='held2':raise a.m.Refusal('disposable observation failure')
   return {'inputs':{'stable':'different' if drift and label=='held2' else 'same'},'structured_inspect_projection':baseline}
  with mock.patch.object(a,'bind_readonly_release',return_value={}),mock.patch.object(a,'snapshot',side_effect=snapshot),mock.patch.object(a.m,'publish',side_effect=lambda path,raw:self.published.append(json.loads(raw))),mock.patch.object(a.m,'root_readonly',side_effect=AssertionError('no actual query')) as query,mock.patch.object(a.m,'acquire_root_lock',side_effect=AssertionError('no flock')) as lock,mock.patch.object(a.archive_ops,'archive_and_unlink_one',side_effect=AssertionError('no unlink')) as unlink:
   try:return a.execute_readonly(Path('/fixture'),'fixture')
   finally:query.assert_not_called();lock.assert_not_called();unlink.assert_not_called()
 def test_success_exact_held_only_zero_action_branch(self):
  result=self.run_mocked();self.assertEqual(result['status'],'PASS_READONLY_NEW_BE87_SHARED_RETAINED_PARENT903729_HELD');self.assertEqual(self.calls,[('held1',True),('held2',True)]);self.assertEqual(self.published[0]['record_unlinks'],0);self.assertEqual(self.published[0]['flock_operations'],0);self.assertFalse(self.published[0]['old324a_or004f_clearance_for_new_record'])
 def test_failed_second_observation_never_publishes_result(self):
  with self.assertRaises(a.m.Refusal):self.run_mocked(fail=True)
  self.assertEqual(self.published,[])
 def test_input_drift_refuses_result(self):
  with self.assertRaises(a.m.Refusal):self.run_mocked(drift=True)
  self.assertEqual(self.published,[])
if __name__=='__main__':
 suite=unittest.TestSuite([unittest.defaultTestLoader.loadTestsFromTestCase(ProfileTests),unittest.defaultTestLoader.loadTestsFromTestCase(BranchTests)]);result=unittest.TextTestRunner(verbosity=2).run(suite);print(json.dumps({'scope':__doc__,'status':'PASS' if result.wasSuccessful() else 'FAIL','tests':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'new_failure_pins':22,'old134_and18_preserved':True,'old324a_archive_pins':6,'required_absent':58,'publisher_sources':14,'actual_rootquery_flock_signal_unlink':False},sort_keys=True));raise SystemExit(0 if result.wasSuccessful() else 1)
