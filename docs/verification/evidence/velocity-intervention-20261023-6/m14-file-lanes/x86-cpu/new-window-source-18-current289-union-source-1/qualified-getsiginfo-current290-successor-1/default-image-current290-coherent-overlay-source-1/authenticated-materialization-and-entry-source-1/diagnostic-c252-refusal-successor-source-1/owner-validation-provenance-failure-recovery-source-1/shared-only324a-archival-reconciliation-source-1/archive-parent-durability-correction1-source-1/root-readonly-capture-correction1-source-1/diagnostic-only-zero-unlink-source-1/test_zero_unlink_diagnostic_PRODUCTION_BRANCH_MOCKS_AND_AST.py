"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Diagnostic production-branch mocks and AST no-mutation controls only.
No actual query, root lock, record action, observer snapshot or signal.
"""
from pathlib import Path
import ast,copy,hashlib,importlib.util,json,resource,unittest
from unittest import mock
N=Path(__file__).parent;r=json.loads((N/'READY-SHARED-FENCE-ZERO-UNLINK-DIAGNOSTIC.SOURCE.json').read_bytes())
raw=Path(r['source']['path']).read_bytes();assert hashlib.sha256(raw).hexdigest()==r['source']['sha256'];spec=importlib.util.spec_from_file_location('actual_diagnostic_zero_unlink_entry_pure',r['source']['path']);a=importlib.util.module_from_spec(spec);spec.loader.exec_module(a)
class DiagnosticTests(unittest.TestCase):
 def run_mocked(self,failure=None):
  self.events=[];self.records=[];self.calls=[];self.closed=[]
  def snapshot(label,before):
   self.events.append(label);self.calls.append((label,before))
   if failure==label:raise a.m.Refusal('disposable readonly observation failure')
   inputs={'immutable':'same' if failure!='drift' or label!='archive-safety1' else 'changed'}
   return {'inputs':inputs,'captures':{'fixture':True}}
  def publish(path,raw):
   self.events.append(path.name);self.records.append(json.loads(raw))
   if failure==path.name:raise OSError('disposable diagnostic writer failure')
  with mock.patch.object(a,'bind_diagnostic_release',return_value={'fixture':True}),mock.patch.object(a.m,'lock_rows',return_value=[]),mock.patch.object(a.m,'acquire_root_lock',return_value=42) as acquire,mock.patch.object(a.m,'require_lock_holder'),mock.patch.object(a,'snapshot',side_effect=snapshot),mock.patch.object(a.m,'publish',side_effect=publish),mock.patch.object(a.os,'close',side_effect=lambda fd:self.closed.append(fd)),mock.patch.object(a.archive_ops,'archive_and_unlink_one',side_effect=AssertionError('forbidden archive/unlink entry')) as archive,mock.patch.object(a.m,'sole_sigkill',side_effect=AssertionError('forbidden signal')) as signal,mock.patch.object(a.m,'root_readonly',side_effect=AssertionError('no live query in pure branch test')) as query:
   try:return a.execute_diagnostic(Path('/fixture/release'),'fixturehash')
   finally:archive.assert_not_called();signal.assert_not_called();query.assert_not_called();self.assertEqual(self.closed,[42]);acquire.assert_called_once()
 def test_success_replica_first_safety_context_zero_actions(self):
  result=self.run_mocked();self.assertTrue(result['diagnostic_only']);self.assertEqual(result['record_unlinks'],0);self.assertFalse(result['new_heavy_admission_authorized']);self.assertEqual(self.calls,[('before1',True),('before2',True),('archive-safety1',True)]);self.assertLess(self.events.index('DIAGNOSTIC-PREPARED.json'),self.events.index('archive-safety1'));self.assertEqual(self.records[-1]['record_unlinks'],0);self.assertEqual(self.records[-1]['archive_and_unlink_calls'],0);self.assertEqual(self.records[-1]['attempt_markers'],0);self.assertFalse(self.records[-1]['process_or_shared_reconciliation_authorized'])
 def test_failed_first_safety_observation_releases_only_owned_mutex(self):
  with self.assertRaises(a.m.Refusal):self.run_mocked('archive-safety1')
  self.assertIn('DIAGNOSTIC-PREPARED.json',self.events);self.assertNotIn('DIAGNOSTIC-RESULT.json',self.events)
 def test_failed_initial_observation_no_further_branch(self):
  with self.assertRaises(a.m.Refusal):self.run_mocked('before1')
  self.assertEqual(self.calls,[('before1',True)]);self.assertEqual(self.records,[])
 def test_prepared_writer_failure_no_safety_or_result(self):
  with self.assertRaises(OSError):self.run_mocked('DIAGNOSTIC-PREPARED.json')
  self.assertNotIn(('archive-safety1',True),self.calls)
 def test_input_drift_refused_without_result(self):
  with self.assertRaises(a.m.Refusal):self.run_mocked('drift')
  self.assertNotIn('DIAGNOSTIC-RESULT.json',self.events)
 def test_result_writer_failure_releases_only_owned_mutex(self):
  with self.assertRaises(OSError):self.run_mocked('DIAGNOSTIC-RESULT.json')
  self.assertEqual(len(self.calls),3)
 def test_budget_or_status_cannot_admit_full_shared_entry(self):
  good={'schema':'mckernel.current290.shared-fence-zero-unlink-diagnostic.release.v1','status':'PASS_READONLY_DIAGNOSTIC_EXECUTION_RELEASE','execution_count':1,'unlink_budget':0,'signal_budget':0,'profile_sha256':a.PROFILE_SHA,'shared_identity':a.r['shared_identity'],'process_retirement_acceptance':a.r['process_retirement_acceptance'],'fetched_source_verified':True,'source_checkpoint':'a'*40,'author':'fixture'}
  for key,value in [('unlink_budget',1),('unlink_budget',False),('signal_budget',1),('signal_budget',False),('status','PASS_EXECUTION_RELEASE')]:
   bad=dict(good);bad[key]=value
   with self.subTest(key=key,value=value),mock.patch.object(a.resource,'getrlimit',return_value=(60,60)),mock.patch.object(a.m,'read_json',return_value=bad),mock.patch.object(a,'accepted_prerequisites',side_effect=AssertionError('must refuse before prerequisites')),self.assertRaises(a.m.Refusal):a.bind_diagnostic_release(Path('/fixture'), 'fixture')
 def test_finite_CPU_gate(self):
  with mock.patch.object(a.resource,'getrlimit',return_value=(resource.RLIM_INFINITY,resource.RLIM_INFINITY)),self.assertRaises(a.m.Refusal):a.bind_diagnostic_release(Path('/fixture'),'fixture')
 def test_AST_no_mutation_and_current_predicates_verbatim(self):
  tree=ast.parse(Path(r['source']['path']).read_bytes());forbidden={'archive_and_unlink_one','unlink','mark_unlink_attempt','kill','killpg','pidfd_open','pidfd_send_signal','sole_sigkill','quarantine_hold'}
  for node in ast.walk(tree):
   if isinstance(node,ast.Call):
    name=node.func.attr if isinstance(node.func,ast.Attribute) else node.func.id if isinstance(node.func,ast.Name) else None;self.assertNotIn(name,forbidden)
  self.assertFalse(any(isinstance(n,ast.FunctionDef) and n.name=='execute' for n in tree.body));self.assertEqual(a.r['allowed_record_unlinks'],0);self.assertEqual(a.r['signal_budget'],0);self.assertEqual(len(a.m.ABSENT),48);self.assertEqual(len(a.sources),9)
  old=ast.parse(Path(r['old_full_shared_source_preserved']['path']).read_bytes());funcs=lambda t:{n.name:ast.dump(n,include_attributes=False) for n in t.body if isinstance(n,ast.FunctionDef)};oldf=funcs(old);newf=funcs(tree)
  for name in ('load','proc_bytes_eof','fixed','exact_identity','retained_domain','evidence','process_code','accepted_prerequisites','original_request_relation','shared_phase','retained_inputs','capture','snapshot'):self.assertEqual(oldf[name],newf[name])
  self.assertEqual(a.r['private_root_readonly_capture']['sha256'],'48d0fbc7dd9cf915cc219788015cc00b023abb2edaa1833b2da6fc8477834925');self.assertFalse(Path(a.r['archive_directory']).exists())
if __name__=='__main__':
 result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(DiagnosticTests));print(json.dumps({'scope':__doc__,'status':'PASS' if result.wasSuccessful() else 'FAIL','tests':result.testsRun,'errors':len(result.errors),'failures':len(result.failures),'actual_queries':0,'actual_flock':0,'actual_record_unlinks':0,'actual_signals':0,'production_snapshot_functions_preserved':13,'diagnostic_entry_only':True},sort_keys=True));raise SystemExit(0 if result.wasSuccessful() else 1)
