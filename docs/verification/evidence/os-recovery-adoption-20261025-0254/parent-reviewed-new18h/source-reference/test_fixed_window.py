"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Pure fixed-window/manual-handoff fixtures; no RPC, launch, queue, signal or ledger.
"""
from pathlib import Path
import copy,datetime,importlib.util,unittest
P=Path(__file__).parent
s=importlib.util.spec_from_file_location('window_metadata_only',P/'finalize_window.py');f=importlib.util.module_from_spec(s);s.loader.exec_module(f)
class FixedWindowTests(unittest.TestCase):
 def window(self):
  return dict(window_id='fixture',boot_id='fixtureboot',start_epoch=1800000000.,start_boot=900000.,start_monotonic=880000.,deadline_epoch=1800064800.,boot_deadline=964800.,monotonic_deadline=944800.,deadline_utc=f.utc(1800064800.),max_agents=10,build_jobs=7)
 def test_each_clock_must_be_exactly_eighteen_hours(self):
  w=self.window();self.assertEqual(f.validate_window(w),w)
  for key in ['deadline_epoch','boot_deadline','monotonic_deadline']:
   bad=dict(w);bad[key]+=1
   with self.assertRaises(ValueError):f.validate_window(bad)
 def test_recovery_does_not_start_a_new_eighteen_hours(self):
  w=self.window();self.assertEqual(f.remaining(w,w['start_epoch'],w['start_boot'],w['start_monotonic']),64800)
  self.assertEqual(f.remaining(w,w['start_epoch']+3600,w['start_boot']+3600,w['start_monotonic']+3600),61200)
  self.assertEqual(f.remaining(w,w['deadline_epoch'],w['boot_deadline'],w['monotonic_deadline']),0)
 def test_rollback_and_suspend_cannot_extend_fixed_window(self):
  w=self.window();self.assertEqual(f.remaining(w,w['start_epoch']-3600,w['start_boot']+7200,w['start_monotonic']+3600),57600)
  self.assertEqual(f.remaining(w,w['deadline_epoch']+1,w['start_boot'],w['start_monotonic']),-1)
 def test_new_rendering_replaces_superseded_cutoff_in_both_controls(self):
  w=self.window()
  for name in ['controller/bridge.TEMPLATE.py','twenty-minute-steering/steer_every_twenty_minutes.TEMPLATE.py']:
   text=f.render((P/name).read_text(),w)
   self.assertIn("DEADLINE = float('1800064800.0')",text)
   self.assertNotIn('1792994400',text)
   self.assertNotIn('__WINDOW_DEADLINE_',text)
  self.assertIn('controller/armed-controller/journal.json',f.render((P/'twenty-minute-steering/steer_every_twenty_minutes.TEMPLATE.py').read_text(),w))
 def test_manual_handoff_allows_accepted_history_but_never_uncertain(self):
  state=dict(phase='stopped',goal=dict(status='paused'),active_turns={},stop_reason='signal_2',resume_instruction=dict(status='accepted_by_server'))
  self.assertTrue(f.manual_stop_eligible(state))
  self.assertTrue(f.manual_stop_eligible(dict(state,stop_reason='work_window')))
  for status in ['sending','delivery_uncertain','unknown']:
   self.assertFalse(f.manual_stop_eligible(dict(state,resume_instruction=dict(status=status))))
  for reason in ['signal_15','credit_budget_unknown','auth_required']:
   self.assertFalse(f.manual_stop_eligible(dict(state,stop_reason=reason)))
if __name__=='__main__':unittest.main()
