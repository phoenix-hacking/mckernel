"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
State/authorization/source fixtures only; real private custody is tested separately.
"""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import types
import unittest
from unittest import mock
import runtime_pipeline as r
import capture_entry as entry

HERE=Path(__file__).resolve().parent
class Runtime(unittest.TestCase):
 def keeper(self):
  k=object.__new__(r.SuccessorKeeper)
  k.state='VERIFIED_STANDBY';k.command_consumed=False;k.retirement_intent_consumed=False;k.signal_call_attempted=False;k.deadline=200
  k.raw_sha='fixture-launch';k.packet={'old_actor':r.base.old.__dict__.get('ROOT_ACTOR','fixture-root')}
  k.custody=types.SimpleNamespace(verify_old_alive=mock.Mock(),verify_held_after_exit=mock.Mock(),pidfd=999)
  k.ops=types.SimpleNamespace(clock_check=mock.Mock(),now=lambda:100,authorize_retirement=mock.Mock(),configure_phase=mock.Mock(return_value={'fixture':True}),publish=mock.Mock(),sole_pidfd_sigkill=mock.Mock(),positive_pidfd_exit=mock.Mock(return_value={'pidfd_exit_ready':True}))
  return k
 def test_retirement_retains_new_custody_and_targets_predecessor_once(self):
  k=self.keeper();self.assertEqual(k.retire({'operation':r.RETIRE}),'PREDECESSOR_EXITED_AWAITING_ACTUAL_JOINS')
  k.ops.sole_pidfd_sigkill.assert_called_once_with(999)
  self.assertTrue(k.retirement_intent_consumed);self.assertTrue(k.signal_call_attempted)
  name,payload=k.ops.publish.call_args_list[0].args
  self.assertEqual(payload['target'],r.PREDECESSOR);self.assertFalse(payload['original_root_retirement_replayed'])
  with self.assertRaisesRegex(ValueError,'once-from-standby'):k.retire({'operation':r.RETIRE})
 def test_signal_error_holds_consumed_operation_without_retry(self):
  k=self.keeper();k.ops.sole_pidfd_sigkill.side_effect=OSError('fixture-pidfd-error')
  self.assertEqual(k.retire({'operation':r.RETIRE}),'HELD_QUARANTINE')
  self.assertTrue(k.command_consumed);self.assertTrue(k.retirement_intent_consumed)
  k.ops.sole_pidfd_sigkill.assert_called_once_with(999)
  with self.assertRaises(ValueError):k.retire({'operation':r.RETIRE})
 def test_configure_failure_has_no_retirement_call(self):
  k=self.keeper();k.ops.configure_phase.side_effect=ValueError('fixture-configure-refusal')
  with self.assertRaisesRegex(ValueError,'configure-refusal'):k.retire({'operation':r.RETIRE})
  k.ops.sole_pidfd_sigkill.assert_not_called();self.assertFalse(k.command_consumed)
 def test_positive_exit_failure_holds_without_adoption(self):
  k=self.keeper();k.ops.positive_pidfd_exit.side_effect=ValueError('fixture-no-positive-exit')
  self.assertEqual(k.retire({'operation':r.RETIRE}),'HELD_QUARANTINE');self.assertTrue(k.signal_call_attempted)
 def test_adoption_requires_new_predecessor_positive_exit_state(self):
  k=self.keeper()
  with self.assertRaisesRegex(ValueError,'positive-predecessor-exit-first'):k.adopt_after_joins({})
 def test_adoption_error_holds_custody(self):
  k=self.keeper();k.state='PREDECESSOR_EXITED_AWAITING_ACTUAL_JOINS'
  k.ops.authorize_join_receipt=mock.Mock(side_effect=ValueError('unknown-join'))
  self.assertEqual(k.adopt_after_joins({}),'HELD_QUARANTINE')
 def test_serve_observer_failure_keeps_raw_hold(self):
  class StopHold(Exception):pass
  k=self.keeper();k.custody=None;k.start=mock.Mock(side_effect=OSError('fixture-observer-error'))
  k.ops.raw_hold=object();k.ops.quarantine_wait=mock.Mock(side_effect=StopHold)
  with self.assertRaises(StopHold):k.serve(lambda:None)
  self.assertEqual(k.state,'HELD_QUARANTINE');k.ops.quarantine_wait.assert_called_once()
 def receipt(self):
  receipt=dict(schema='mckernel.current290.predecessor-keeper-positive-joins.v1',author='/root',operation=r.ADOPT,
    predecessor_custodian=r.PREDECESSOR,keeper={'pid':1,'starttime':'fixture','pgid':1},launch_sha256=r.sha(b'fixture'),
    window_id=r.base.WINDOW_ID,pidfd_exit_ready=True,only_predecessor_keeper_signalled=True,
    original_root_retirement_replayed=False,protected_state_unchanged=True,
    sudo_direct_join=dict(path=str(r.successor.CAPTURE/'OUTER/DIRECT-CHILD-JOIN.json'),bytes=1,sha256='fixture'),outer_tool_join='outer',predecessor_group_zero_members=True,predecessor_wrapper_absent=True)
  docs={'sudo':dict(pid=1193470,starttime='83392595',direct_join=True,wait_status=0,exit_code=0),
    'outer':dict(author='/root',tool_session_id=1416,outer=r.OUTER,status='ACTUAL_TOOL_COMPLETED',actual_tool_result_retained=True,
      join_inferred_from_absence=False,actual_tool_result_refs=[dict(path='/private-fixture/result',bytes=1,sha256='fixture')])}
  ops=types.SimpleNamespace(self_identity=receipt['keeper'],raw_packet=b'fixture',pinned_document=lambda key:docs['sudo' if isinstance(key,dict) else key],p=types.SimpleNamespace(pinned_bytes=mock.Mock()))
  return ops,receipt,docs
 def test_full_positive_joins_bind_actual_sources_then_current_absence(self):
  ops,receipt,docs=self.receipt()
  with mock.patch.object(r,'current_predecessor_absence',return_value=True) as check:self.assertTrue(r.require_predecessor_receipt(ops,receipt));check.assert_called_once()
  ops.p.pinned_bytes.assert_called_once()
 def test_sudo_join_must_be_original_outer_actual_capture_path(self):
  ops,receipt,docs=self.receipt();receipt['sudo_direct_join']['path']='/wrong/private/join.json'
  with self.assertRaisesRegex(ValueError,'exact-predecessor-outer-sudo-join-capture-path'):r.require_predecessor_receipt(ops,receipt)
 def test_no_historical_join_inference_from_current_absence(self):
  ops,receipt,docs=self.receipt();docs['outer']['join_inferred_from_absence']=True
  with mock.patch.object(r,'current_predecessor_absence') as check:
   with self.assertRaisesRegex(ValueError,'actual-tool1416'):r.require_predecessor_receipt(ops,receipt)
   check.assert_not_called()
 def test_wrong_sudo_birth_refused(self):
  ops,receipt,docs=self.receipt();docs['sudo']['starttime']='reused'
  with self.assertRaisesRegex(ValueError,'actual-sudo-direct-wait'):r.require_predecessor_receipt(ops,receipt)
 def test_no_original_root_retirement_replay(self):
  ops,receipt,docs=self.receipt();receipt['original_root_retirement_replayed']=True
  with self.assertRaisesRegex(ValueError,'positive-predecessor-joins'):r.require_predecessor_receipt(ops,receipt)
 def test_original_root_positive_receipt_still_required_at_bootstrap(self):
  ops=object.__new__(r.SuccessorOps);ops.predecessor_receipt=None;ops.engine=types.SimpleNamespace(_CONFIRMED_EXIT_DELTA_MANIFEST={})
  with self.assertRaisesRegex(ValueError,'positive-predecessor-joins-and-confirmed'):ops.bootstrap({},None,{}, {})
 def test_new_operation_names_only_in_capture(self):
  self.assertIn(r.RETIRE,entry.OPERATIONS);self.assertIn(r.ADOPT,entry.OPERATIONS)
  self.assertNotIn('RETIRE_EXACT_OLD_ROOT_PIDFD_ONLY',entry.OPERATIONS)
  self.assertNotIn('ADOPT_AFTER_POSITIVE_RETIREMENT_CURRENT_ABSENCE',entry.OPERATIONS)
 def test_outer_capture_is_byte_identical_to_frozen3d3e(self):
  self.assertEqual(hashlib.sha256((HERE/'capture_outer.py').read_bytes()).hexdigest(),'3d3e46527400d7142a9c98dfa63f665d9973057526dce66b39417ac2e71800c4')
 def test_final_lifecycle_installer_and_retained_history_source_are_pinned(self):
  path=Path(r.LIFECYCLE['path']);self.assertEqual(path.stat().st_size,r.LIFECYCLE['bytes'])
  module=r.load(path,r.LIFECYCLE['sha256'])
  expected=module.expected_authorization(dict(path='/private/source-review',bytes=1,sha256='fixture'))
  self.assertEqual(expected['history_seed'],module.INPUTS['history_seed'])
  self.assertEqual(expected['installer_sha256'],r.LIFECYCLE['sha256'])
  module.authenticated(expected['history_seed'])
 def test_original_borrowed_transaction_four_to_nine_event_private_files(self):
  path=r.FROZEN.parent/'test_runtime_pipeline.py';spec=importlib.util.spec_from_file_location('_original_private_runtime_fixtures',path)
  module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
  module.RuntimeTests('test_borrowed_close_preserves_real_private_keeper_lock_until_final_release').run_borrowed_fixture(True)

if __name__=='__main__':unittest.main(verbosity=2)
