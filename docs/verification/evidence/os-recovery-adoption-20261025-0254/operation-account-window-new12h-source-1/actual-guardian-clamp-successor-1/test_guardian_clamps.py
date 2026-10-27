"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Pure guardian receipt/journal/clock controls; no signals or operations.
"""
import copy,importlib.util,json
from pathlib import Path
import unittest
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('v2',HERE/'actual_account_window_v2.py')
g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g)
class GuardianClamps(unittest.TestCase):
 def setUp(self):
  self.receipt=g.load_receipt();self.journal=copy.deepcopy(self.receipt['journal_state'])
  self.observed={'pid':1619833,'start':'92037917','state':'S'}
 def test_exact_parent_guardian_and_minimums(self):
  self.assertEqual(g.validate_guardian(self.journal,self.receipt,self.observed),g.CUTOFFS)
  for i,key in enumerate(('deadline','finite_watcher_monotonic_deadline','boot_deadline')):
   j=copy.deepcopy(self.journal);j[key]-=10
   self.assertEqual(g.validate_guardian(j,self.receipt,self.observed)[i],g.CUTOFFS[i]-10)
 def test_reject_extended_or_malformed_journal_cutoffs(self):
  for key in ('deadline','finite_watcher_monotonic_deadline','boot_deadline'):
   for value in (self.journal[key]+1,0,float('nan'),True):
    with self.subTest(key=key,value=value):
     j=copy.deepcopy(self.journal);j[key]=value
     with self.assertRaises(ValueError):g.validate_guardian(j,self.receipt,self.observed)
 def test_reject_missing_reused_or_zombie_guardian(self):
  for observed in (None,dict(self.observed,start='different'),dict(self.observed,pid=1),dict(self.observed,state='Z')):
   with self.assertRaises(ValueError):g.validate_guardian(self.journal,self.receipt,observed)
 def test_reject_foreign_or_stopping_parent_journal(self):
  for key,value in [('packet_sha256','wrong'),('boot_id','wrong'),('credit_run_id','wrong'),('credit_started',False),('initial_prepaid_guard',False),('replacement_watcher_pid',1),('replacement_watcher_start','wrong'),('transition_hold','held'),('stop_intent',{'reason':'stop'}),('deadline_stop_sent',True),('last_action','DRAIN_USER_STOP')]:
   with self.subTest(key=key):
    j=copy.deepcopy(self.journal);j[key]=value
    with self.assertRaises(ValueError):g.validate_guardian(j,self.receipt,self.observed)
 def test_inherited_earlier_cutoffs_refuse_original_window_tail(self):
  clocks=[v-1 for v in g.CUTOFFS];g.check_window(g.load_window(),clocks,g.BOOT)
  for i in range(3):
   bad=clocks.copy();bad[i]=g.CUTOFFS[i]
   with self.assertRaises(ValueError):g.check_window(g.load_window(),bad,g.BOOT)
  for i in (1,2):
   bad=clocks.copy();bad[i]=(g.CUTOFFS[i]+g.v1.CUTOFFS[i])/2
   g.v1.check_window(g.v1.load_window(),bad,g.BOOT)
   with self.assertRaises(ValueError):g.check_window(g.load_window(),bad,g.BOOT)
 def test_future_tightening_is_applied(self):
  clocks=[v-1 for v in g.CUTOFFS];tightened=list(g.CUTOFFS);tightened[2]-=2
  with self.assertRaises(ValueError):g.check_window(g.load_window(),clocks,g.BOOT,tightened)
 def test_account_policy_is_exact_reviewed_predecessor(self):
  self.assertIs(g.check_account_state,g.v1.check_account_state)
  self.assertIs(g.available_balance,g.v1.available_balance)
if __name__=='__main__':unittest.main(verbosity=2)
