"""Functional OS only; no security testing. No live query/pidfd/flock/signal/unlink."""
import importlib.util,json,copy,unittest,ast,inspect
from pathlib import Path
from unittest import mock
S=Path(__file__).parent/"retire_exact_parent903729_preserve_be87.PROCESS_ONLY.NOT_RELEASED.py"
def load(name,path):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
a=load('process903',S)
b=load('sequence903',Path('/home/holden/mckernel/scripts/tests/test_native_exact_scratch22_authority1_quarantine_recovery.py'));b.m=a.m
class Focused(unittest.TestCase):
 def test_actual_prerequisite(self):self.assertTrue(a.held_prerequisite())
 def test_changed_shared_or_review_refused(self):
  original=a.m.read_json
  for key,value in [('current_shared_sha256','0'*64),('decision','PASS'),('implementation_ownership',True)]:
   def read(p,sha):
    v=original(p,sha)
    if str(p)==a.r['held_readonly_prerequisite']['path']:v=dict(v);v[key]=value
    return v
   with self.subTest(key=key),mock.patch.object(a.m,'read_json',side_effect=read),self.assertRaises(a.m.Refusal):a.held_prerequisite()
 def test_completed_helper_join_refused(self):
  original=a.m.read_json
  def read(p,sha):
   v=original(p,sha)
   if str(p)==a.r['held_readonly_proofs'][1]['path']:v=dict(v);v['group_absent']=False
   return v
  with mock.patch.object(a.m,'read_json',side_effect=read),self.assertRaises(a.m.Refusal):a.held_prerequisite()
 def test_domains_and_freshnamespace(self):
  self.assertEqual((a.m.PID,a.m.START,a.m.PARENT),(903729,'77387104',903728));self.assertEqual(len(a.m.ABSENT),58);self.assertEqual(len(a.sources),14);self.assertNotIn(903729,a.m.ABSENT);self.assertFalse(a.OUT.exists());self.assertEqual(a.r['shared_identity']['sha256'],'be87556927c1bd55bdf4db6dac6cbb8a035800c0d58727e48187414b2e119fc8')
 def test_execute_unchanged(self):
  primitive=load('original_primitive903',Path(a.r['primitive']['path']))
  self.assertEqual(ast.dump(ast.parse(inspect.getsource(a.m.execute))),ast.dump(ast.parse(inspect.getsource(primitive.execute))))
 def test_after_snapshot_retains_shared_and_never_guards_deadparent(self):
  report={'snapshots':[[],[]]};inputs={'original_shared_binding':{'same':True}}
  with mock.patch.object(a,'retained_inputs',return_value=inputs),mock.patch.object(a,'fixed',side_effect=lambda row:(row,b'')),mock.patch.object(a,'held_parent_identity',side_effect=AssertionError('deadparentguard')),mock.patch.object(a.m,'boot_check'),mock.patch.object(a.m,'require_lock_holder'),mock.patch.object(a.h,'members',return_value=[]),mock.patch.object(a.m,'proc_stat',return_value=[0]*20),mock.patch.object(a.m,'root_readonly',return_value=b'{}'),mock.patch.object(a.m,'strict',return_value=report),mock.patch.object(a.m,'validate_process_report') as validate,mock.patch.object(a,'capture',return_value='mock'),mock.patch.object(a.labels,'validate_ps_identity',return_value={'unparsed_current_Labels_display':{}}),mock.patch.object(a.labels,'project',return_value={}),mock.patch.object(a.labels,'compare'),mock.patch.object(a,'accepted_prerequisites',return_value={}),mock.patch.object(a,'shared_phase',return_value={'same':True}) as shared:
   result=a.snapshot('after',{},a.r,False);shared.assert_called_once_with(True);self.assertFalse(validate.call_args.args[-1]);self.assertEqual(result['base_required_absent'],59)
 def test_finite_cpu_refused_before_release_read(self):
  with mock.patch.object(a.resource,'getrlimit',return_value=(60,60)),mock.patch.object(a.m,'read_json') as read,self.assertRaises(a.m.Refusal):a.bind_release(Path('/unused'),'0'*64)
  read.assert_not_called()
if __name__=='__main__':
 suite=unittest.TestSuite();suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(Focused))
 for name in ('test_prepared_before_sole_signal_and_complete_before_root_unlock','test_pre_signal_failure_never_sends_or_acquires_replacement','test_uncertain_signal_response_consumes_budget_and_never_retries','test_postflight_or_complete_writer_failure_keeps_replacement_lock'):suite.addTest(b.RecoveryTests(name))
 result=unittest.TextTestRunner(verbosity=2).run(suite);raise SystemExit(not result.wasSuccessful())
