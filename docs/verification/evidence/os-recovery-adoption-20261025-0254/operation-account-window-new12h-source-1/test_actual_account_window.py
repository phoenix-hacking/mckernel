"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Pure positive/negative policy controls; no workloads or native operations.
"""
import copy
import datetime
import importlib.util
import json
from pathlib import Path
import unittest
from unittest.mock import patch
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('actual_guard',HERE/'actual_account_window.py')
g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g)
class Controls(unittest.TestCase):
 def setUp(self):
  self.state=json.loads((HERE/'ACCOUNT-FIXTURE.json').read_text())
  self.wall=datetime.datetime.fromisoformat(self.state['heartbeat_at']).timestamp()+1
 def test_current_account_canonical_positive_and_no_writes(self):
  before=copy.deepcopy(self.state)
  self.assertEqual(g.check_account_state(self.state,self.wall),g.available_balance(self.state['last_rate_limits']))
  self.assertEqual(before,self.state)
 def test_thread_run_budget_spent_and_remaining(self):
  variants=[('thread_id','historical')]
  for key,value in variants:
   s=copy.deepcopy(self.state);s[key]=value
   with self.assertRaises(ValueError):g.check_account_state(s,self.wall)
  for key,value in [('id','wrong'),('budget','57775'),('spent','22812'),('spent','NaN'),('remaining','99999'),('remaining','0')]:
   with self.subTest(key=key,value=value):
    s=copy.deepcopy(self.state);s['credit_budget'][key]=value
    with self.assertRaises((ValueError,ArithmeticError)):g.check_account_state(s,self.wall)
 def test_all_real_holds_and_stop_predicates(self):
  for key,value in [('service_hold',True),('policy_hold',True),('auth_hold',True),('billing_hold',True),('stop_now',True),('stop_reason','work_window'),('phase','stopped'),('credit_budget_error','unknown')]:
   with self.subTest(key=key):
    s=copy.deepcopy(self.state);s[key]=value
    with self.assertRaises(ValueError):g.check_account_state(s,self.wall)
  s=copy.deepcopy(self.state);s['goal']['status']='paused'
  with self.assertRaises(ValueError):g.check_account_state(s,self.wall)
 def test_canonical_credit_semantics_nullable_controls(self):
  s=copy.deepcopy(self.state);s['last_rate_limits']['spendControlReached']=None
  self.assertGreater(g.check_account_state(s,self.wall),0)
  for key,value in [('balance','0'),('balance','NaN'),('balance',None),('hasCredits',False),('unlimited',True)]:
   with self.subTest(key=key,value=value):
    s=copy.deepcopy(self.state);s['last_rate_limits']['credits'][key]=value
    with self.assertRaises((ValueError,ArithmeticError)):g.check_account_state(s,self.wall)
  s=copy.deepcopy(self.state);s['last_rate_limits']['spendControlReached']=True
  with self.assertRaises(ValueError):g.check_account_state(s,self.wall)
 def test_heartbeat_boundaries(self):
  heart=datetime.datetime.fromisoformat(self.state['heartbeat_at']).timestamp()
  for wall in (heart-1,heart+180,float('nan'),float('inf')):
   with self.assertRaises(ValueError):g.check_account_state(self.state,wall)
 def test_resident_billing_no_new_allowance(self):
  for key,value in [('mode','included_only'),('credit_budget','57775'),('automatic_credit_purchase',True),('api_key_billing',True),('account_wide_balance_guard',False)]:
   with self.subTest(key=key):
    s=copy.deepcopy(self.state);s['settings']['billing'][key]=value
    with self.assertRaises(ValueError):g.check_account_state(s,self.wall)
 def test_exact_window_and_all_three_cutoffs(self):
  window=g.load_window();clocks=[v-1 for v in g.CUTOFFS]
  self.assertEqual(g.check_window(window,clocks,g.BOOT),clocks)
  for i in range(3):
   bad=clocks.copy();bad[i]=g.CUTOFFS[i]
   with self.assertRaises(ValueError):g.check_window(window,bad,g.BOOT)
  with self.assertRaises(ValueError):g.check_window(window,clocks,'differentboot')
  for key in ('deadline_epoch','monotonic_deadline','boot_deadline'):
   bad=copy.deepcopy(window);bad[key]+=1
   with self.assertRaises(ValueError):g.check_window(bad,clocks,g.BOOT)
 def test_malformed_clock_vector(self):
  for clocks in ([],[1,2],[1,2,3,4],[1,float('nan'),3],[1,True,3],[-1,1,1]):
   with self.assertRaises(ValueError):g.check_window(g.load_window(),clocks,g.BOOT)
 def test_pinned_sources_refuse_drift(self):
  actual=Path.read_bytes
  def changed(path):return b'drift' if path==g.CREDITS else actual(path)
  with patch.object(Path,'read_bytes',changed):
   with self.assertRaisesRegex(ValueError,'canonical credit source drift'):g._canonical_functions()
  with patch.object(Path,'read_bytes',return_value=b'drift'):
   with self.assertRaisesRegex(ValueError,'actual window source drift'):g.load_window()
if __name__=='__main__':unittest.main(verbosity=2)
