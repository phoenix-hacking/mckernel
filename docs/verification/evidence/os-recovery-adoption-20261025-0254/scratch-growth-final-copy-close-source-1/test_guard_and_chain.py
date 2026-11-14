"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Pure snapshot and retained JSON tests; no process/FD/signal/root/runtime action.
"""
import copy
import datetime
import json
from pathlib import Path
import unittest
import recover_growth_custody as r

class AccountGuard(unittest.TestCase):
    wall=1793057000.0
    def state(self):
        return dict(phase='running',stop_reason=None,thread_id='01a170fb-57c3-7ab3-862d-8005bef92a63',
                    heartbeat_at=datetime.datetime.fromtimestamp(self.wall-5,datetime.timezone.utc).isoformat(),
                    credit_budget=dict(id='7f4af94a83b14cc08f97401f5891d965',budget='57774.852125',remaining='100'),
                    credit_budget_error=None,last_rate_limits=dict(spendControlReached=None,
                    credits=dict(hasCredits=True,unlimited=False,balance='123.4')))
    def test_null_normal_and_false_use_pinned_canonical_function(self):
        for flag in (None,False):
            s=self.state();s['last_rate_limits']['spendControlReached']=flag
            self.assertEqual(r.check_account_state(s,self.wall),r.Decimal('123.4'))
    def test_true_or_truthy_spending_stop_refused(self):
        for flag in (True,1,'service-stop'):
            s=self.state();s['last_rate_limits']['spendControlReached']=flag
            with self.subTest(flag=flag),self.assertRaises(ValueError):r.check_account_state(s,self.wall)
    def test_unknown_exhausted_unlimited_or_nonfinite_credits_refused(self):
        bad=[None,{},dict(hasCredits=False,unlimited=False,balance='1'),
             dict(hasCredits=True,unlimited=True,balance='1'),
             dict(hasCredits=True,unlimited=False,balance='0'),
             dict(hasCredits=True,unlimited=False,balance='NaN'),
             dict(hasCredits=True,unlimited=False,balance='Infinity')]
        for credits in bad:
            s=self.state();s['last_rate_limits']['credits']=credits
            with self.subTest(credits=credits),self.assertRaises(ValueError):r.check_account_state(s,self.wall)
    def test_heartbeat_goal_phase_budget_and_real_holds_refused(self):
        variants=[('phase','paused'),('phase','blocked'),('stop_reason','service_policy'),
                  ('stop_reason','authentication'),('stop_reason','billing'),('stop_reason','user_stop'),
                  ('stop_now',True),('credit_budget_error','Account spending control has been reached'),
                  ('thread_id','other'),
                  ('heartbeat_at',datetime.datetime.fromtimestamp(self.wall-180,datetime.timezone.utc).isoformat()),
                  ('heartbeat_at',datetime.datetime.fromtimestamp(self.wall+1,datetime.timezone.utc).isoformat())]
        for key,value in variants:
            s=self.state();s[key]=value
            with self.subTest(key=key,value=value),self.assertRaises(ValueError):r.check_account_state(s,self.wall)
        for key,value in [('id','other'),('budget','57775'),('remaining','0'),('remaining','NaN')]:
            s=self.state();s['credit_budget'][key]=value
            with self.subTest(key=key,value=value),self.assertRaises(ValueError):r.check_account_state(s,self.wall)

class PredecessorChain(unittest.TestCase):
    def fixture(self):
        here=Path(r.__file__).parent
        pins=json.loads((here/'ACTUAL-TARGET-PINS.json').read_text())
        raw=here.parent/'ROOT-SCRATCH-GROWTH-SDK7-ADMISSION-1/CLOSE-REFUSAL-RAW'
        docs=[json.loads((raw/name).read_text()) for name in ('RAWREADY.json','QUARANTINE.json','PIDFD-EXIT.json','OLD-ACTUAL-JOINS.json','COPY-PACKET.json')]
        return [pins,*docs,docs[-1]['qualified_postconditions']]
    def test_exact_new_holder_and_retired_origin_are_distinct(self):
        f=self.fixture();self.assertTrue(r.predecessor_chain(*f))
        self.assertEqual(r.TARGET,dict(pid=1289073,birth=85353159,parent=1289070,pgid=1289064,fd=4,origin=1281419))
        self.assertEqual(r.CALLER_BIRTH,85353151);self.assertEqual(r.TOOL_CELL_ID,'44584')
        self.assertNotEqual(r.PID,r.ORIGIN)
    def test_wrong_new_holder_origin_or_old_retirement_refused(self):
        cases=[(1,['data','successor','pid'],1281419),
               (1,['data','successor','birth'],85353160),
               (1,['data','successor','fd'],5),
               (1,['data','lock_origin_pid'],1289073),
               (2,['data','phase'],'READY'),
               (2,['data','closed'],True),
               (2,['data','error'],"ValueError('service policy')"),
               (3,['data','old_target'],r.TARGET),
               (3,['data','positive_pidfd_exit'],False),
               (4,['tool_positive_join'],False),
               (5,['sources','recover_growth_custody.py','sha256'],'0'*64)]
        for index,path,value in cases:
            f=copy.deepcopy(self.fixture());target=f[index]
            for key in path[:-1]:target=target[key]
            target[path[-1]]=value
            with self.subTest(path=path),self.assertRaises(ValueError):r.predecessor_chain(*f)

if __name__=='__main__':unittest.main(verbosity=2)
