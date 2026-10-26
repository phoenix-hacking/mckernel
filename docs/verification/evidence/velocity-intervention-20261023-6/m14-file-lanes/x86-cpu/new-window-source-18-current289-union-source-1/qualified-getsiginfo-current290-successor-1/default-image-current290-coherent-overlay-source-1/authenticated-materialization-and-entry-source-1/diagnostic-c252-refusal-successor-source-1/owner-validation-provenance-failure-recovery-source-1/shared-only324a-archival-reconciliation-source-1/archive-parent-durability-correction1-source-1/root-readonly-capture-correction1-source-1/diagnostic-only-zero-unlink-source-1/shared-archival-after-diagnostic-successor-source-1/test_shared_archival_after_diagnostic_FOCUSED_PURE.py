"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Focused immutable diagnostic prerequisite and fully mocked shared production branch.
No actual shared action, root query/flock/signal or namespace creation.
"""
from pathlib import Path
import ast,copy,hashlib,importlib.util,json,signal,unittest
from unittest import mock
N=Path(__file__).parent;r=json.loads((N/'READY-SHARED-ARCHIVAL-AFTER-ACCEPTED-DIAGNOSTIC.SOURCE.json').read_bytes());raw=Path(r['source']['path']).read_bytes();assert hashlib.sha256(raw).hexdigest()==r['source']['sha256'];spec=importlib.util.spec_from_file_location('actual_shared_after_diag_pure',r['source']['path']);a=importlib.util.module_from_spec(spec);spec.loader.exec_module(a)
refs=a.r['recent_zero_unlink_diagnostic'];values={row['path']:json.loads(Path(row['path']).read_bytes()) for row in refs.values()};baseline=values[refs['result']['path']]['snapshots'][0]['structured_inspect_projection']
class PrerequisiteTests(unittest.TestCase):
 def test_real_accepted_diagnostic_result_join_postreturn(self):self.assertTrue(a.accepted_recent_zero_unlink_diagnostic(baseline));self.assertEqual(len(a.accepted_prerequisites()),44)
 def reject_change(self,key,change):
  data=copy.deepcopy(values);change(data[refs[key]['path']])
  with mock.patch.object(a.m,'read_json',side_effect=lambda path,expected=None:data[str(path)]),self.assertRaises((a.m.Refusal,a.labels.Refusal)):a.accepted_recent_zero_unlink_diagnostic(baseline)
 def test_bad_acceptance_scope_refused(self):self.reject_change('acceptance',lambda x:x.__setitem__('shared_clearance',True))
 def test_nonzero_diagnostic_action_refused(self):self.reject_change('result',lambda x:x.__setitem__('record_unlinks',1))
 def test_diagnostic_input_drift_refused(self):self.reject_change('result',lambda x:x['snapshots'][2]['inputs'].__setitem__('drift',True))
 def test_bad_diagnostic_join_refused(self):self.reject_change('whole_join',lambda x:x.__setitem__('returncode',1))
 def test_bad_postreturn_shared_or_mutex_refused(self):self.reject_change('postreturn',lambda x:x['observations'][0]['shared'].__setitem__('inode',1))
 def test_historical_unknown_not_relabelled(self):self.reject_change('acceptance',lambda x:x.__setitem__('prior889039_observer_cause','AUTH'))
 def test_new50_domain11_sources_and_old_guard_AST_preservation(self):
  self.assertEqual(len(a.m.ABSENT),50);self.assertTrue({889039,895698}<=a.m.ABSENT);self.assertEqual(len(a.sources),11);self.assertTrue(set(row['path'] for row in a.r['new_exact_publisher_sources'])<=set(a.sources));self.assertEqual(a.r['additional_recorded_outer_ids'],[])
  old=ast.parse(Path(r['predecessor_full_shared_source']['path']).read_bytes());new=ast.parse(Path(r['source']['path']).read_bytes());f=lambda t:{n.name:ast.dump(n,include_attributes=False) for n in t.body if isinstance(n,ast.FunctionDef)};of=f(old);nf=f(new)
  for name,value in of.items():
   if name not in ('accepted_prerequisites','bind_release'):self.assertEqual(nf[name],value,name)
  self.assertEqual(a.r['archive_primitives']['sha256'],'5efaeacd6ad7cabb32fad180dbd3c99b7c3f6b63d71c73b048b1fd412b74eb75');self.assertEqual(a.r['private_root_readonly_capture']['sha256'],'48d0fbc7dd9cf915cc219788015cc00b023abb2edaa1833b2da6fc8477834925');self.assertFalse(Path(a.r['archive_directory']).exists())
 def test_missing_recent_diagnostic_release_reference_refused_early(self):
  release={'schema':'mckernel.current290.exact-shared-only324a-reconciliation.release.v1','status':'PASS_EXECUTION_RELEASE','execution_count':1,'unlink_budget':1,'profile_sha256':a.PROFILE_SHA,'shared_identity':a.r['shared_identity'],'process_retirement_acceptance':a.r['process_retirement_acceptance'],'fetched_source_verified':True,'outer_timeout_or_kill_authorized':False,'source_checkpoint':'a'*40,'author':'fixture'}
  with mock.patch.object(a,'runtime_limits'),mock.patch.object(a.m,'read_json',return_value=release),mock.patch.object(a,'accepted_prerequisites',side_effect=AssertionError('must fail before prerequisites')),self.assertRaises(a.m.Refusal):a.bind_release(Path('/fixture'),'fixture')
class Held(BaseException):pass
class ProductionBranchTests(unittest.TestCase):
 def setUp(self):
  self.handlers={n:signal.getsignal(n) for n in a.m.DEFERRED_SIGNALS};self.mask=signal.pthread_sigmask(signal.SIG_BLOCK,set());self.addCleanup(self.restore)
 def restore(self):
  signal.pthread_sigmask(signal.SIG_BLOCK,a.m.DEFERRED_SIGNALS)
  for n,h in self.handlers.items():signal.signal(n,h)
  signal.pthread_sigmask(signal.SIG_SETMASK,self.mask)
 def run_mocked(self,fail=False):
  self.events=[]
  def snapshot(label,before):
   self.events.append(label)
   if fail and label=='after':raise a.m.Refusal('disposable post-proof failure')
   return {'inputs':{'stable':'same'}}
  def archive(path,record,identity,out,safety,publish,mark,parent):safety();mark();self.events.append('unlink-budget-consumed-mock');return {'active_shared_absent':True}
  def hold(fd):self.events.append(('hold',fd));raise Held()
  with mock.patch.object(a,'bind_release',return_value={}),mock.patch.object(a.m,'lock_rows',return_value=[]),mock.patch.object(a.m,'acquire_root_lock',return_value=42),mock.patch.object(a.m,'require_lock_holder'),mock.patch.object(a,'snapshot',side_effect=snapshot),mock.patch.object(a.m,'publish',side_effect=lambda path,raw:self.events.append(path.name)),mock.patch.object(a.archive_ops,'archive_and_unlink_one',side_effect=archive),mock.patch.object(a.m,'quarantine_hold',side_effect=hold),mock.patch.object(a.os,'close',side_effect=lambda fd:self.events.append(('close',fd))):return a.execute(Path('/fixture'),'fixture')
 def test_success_existing_complete_before_unlock(self):
  self.run_mocked();self.assertLess(self.events.index('COMPLETE.json'),self.events.index(('close',42)))
 def test_postproof_uncertainty_retains_original_custody(self):
  with self.assertRaises(Held):self.run_mocked(True)
  self.assertIn(('hold',42),self.events);self.assertNotIn(('close',42),self.events);self.assertEqual(self.events.count('unlink-budget-consumed-mock'),1)
if __name__=='__main__':
 suite=unittest.TestSuite([unittest.defaultTestLoader.loadTestsFromTestCase(PrerequisiteTests),unittest.defaultTestLoader.loadTestsFromTestCase(ProductionBranchTests)]);result=unittest.TextTestRunner(verbosity=2).run(suite);print(json.dumps({'scope':__doc__,'status':'PASS' if result.wasSuccessful() else 'FAIL','tests':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'actual_query_flock_unlink_signal':False,'new_absent_count':50,'publisher_sources':11,'old_mutation_and_custody_branch_unchanged':True},sort_keys=True));raise SystemExit(0 if result.wasSuccessful() else 1)
