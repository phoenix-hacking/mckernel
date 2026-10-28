"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Pure admission fixtures: no real guard/control/operation executed.
"""
import copy
from datetime import datetime, timezone
import unittest
import json
from pathlib import Path
import guardian_guard as g


class GuardTests(unittest.TestCase):
    def setUp(self):
        self.wall = g.DEADLINE-3600
        chain = {k:dict(pid=v[0],start=v[1],ppid=1311 if k=='watcher' else g.INITIAL['watcher' if k=='worker' else 'worker'][0],state='S') for k,v in g.INITIAL.items()}
        self.procs = {v['pid']:v for v in chain.values()}
        self.procs[1311]=dict(pid=1311,start='596',ppid=1,state='S',comm='systemd')
        guardian = dict(pid=2111552,start='101236067',ppid=2111551,state='S');self.procs[2111552]=dict(guardian,ppid=1311)
        armed=json.loads((Path(__file__).parent/'ARMED-RECEIPT.FIXTURE.json').read_text())
        for name in ('monitor','phone'):
            actor=armed['actors'][name];self.procs[actor['pid']]=dict(actor,ppid=1311)
        self.args = [dict(deadline_epoch=g.DEADLINE,boot_deadline=g.WINDOW_BOOT_CAP,monotonic_deadline=1035706.5689547858,boot_id=g.BOOT_ID,credit_run_id=g.RUN,credit_ceiling=str(g.CEILING)),
          dict(packet_sha256=g.PACKET_SHA,deadline=g.DEADLINE,boot_id=g.BOOT_ID,credit_run_id=g.RUN,original_finite=True,initial_prepaid_guard=True,credit_started=True,boot_deadline=g.BOOT_CAP,finite_watcher_monotonic_deadline=g.MONO_CAP,last_action='WAIT_EXISTING_CREDIT_WATCHER',original=chain,replacement=copy.deepcopy(chain)),
          dict(pid=2111552,birth=guardian,deadline=g.DEADLINE),
          dict(thread_id=g.THREAD,phase='running',goal={'status':'active'},heartbeat_at=datetime.fromtimestamp(self.wall,timezone.utc).isoformat(),worker_pid=2109397,server_pid=2109399,server_start='101211685',credit_budget=dict(id=g.RUN,budget=str(g.CEILING),spent=str(g.SPENT_FLOOR),remaining=str(g.CEILING-g.SPENT_FLOOR)),settings={'billing':dict(mode='prepaid_credits',credit_budget=str(g.CEILING),automatic_credit_purchase=False,api_key_billing=False,account_wide_balance_guard=True)}),
          dict(watcher_pid=2109395),self.procs.get,[self.wall,g.MONO_CAP-3600,g.BOOT_CAP-3600],g.BOOT_ID,armed]

    def test_healthy(self):
        self.assertEqual(g.validate(*self.args),self.args[6])

    def test_negative_bindings(self):
        cases=[(0,'deadline_epoch',g.DEADLINE+1),(0,'monotonic_deadline',1035707),(0,'boot_id','other'),(1,'packet_sha256','0'*64),(1,'credit_run_id','0'*32),(1,'boot_deadline',g.JOURNAL_BOOT_CAP+1),(1,'finite_watcher_monotonic_deadline',g.MONO_CAP+1),(1,'transition_hold','hold'),(1,'stop_intent',True),(1,'last_action','HOLD_THREAD_CHANGED'),(1,'initial_prepaid_guard',False),(2,'deadline',g.DEADLINE+1),(3,'thread_id','other'),(3,'phase','stopped'),(3,'service_hold','hold'),(3,'last_error',{'error':'hold'}),(3,'heartbeat_at','2020-01-01T00:00:00+00:00'),(3,'server_start','other'),(4,'watcher_pid',999)]
        for i,k,v in cases:
            with self.subTest(field=k,value=v):
                args=copy.deepcopy(self.args);args[i][k]=v
                with self.assertRaises(ValueError):g.validate(*args)

    def test_stop_and_uncertain_delivery(self):
        cases = [(key, True) for key in ('checkpoint_requested', 'stop_now', 'paused')]
        cases += [('transport_uncertain', {'at': 'pending'})]
        cases += [(key, {'status': status})
                  for key in ('resume_instruction', 'last_instruction')
                  for status in ('sending', 'delivery_uncertain', 'intent', 'uncertain')]
        cases += [(key, value) for key in ('resume_instruction', 'last_instruction')
                  for value in ('sending', True, [])]
        for key, value in cases:
            with self.subTest(field=key, value=value):
                args = copy.deepcopy(self.args); args[3][key] = value
                with self.assertRaisesRegex(ValueError, 'campaign .*'):
                    g.validate(*args)
        args = copy.deepcopy(self.args)
        args[3].update(checkpoint_requested=False, stop_now=False, paused=False,
                       resume_instruction={'status': 'delivered'}, last_instruction={'status': 'delivered'})
        self.assertEqual(g.validate(*args), args[6])

    def test_negative_credit_and_live_birth(self):
        for k,v in [('id','other'),('budget','57775'),('spent','0'),('remaining','999999')]:
            args=copy.deepcopy(self.args);args[3]['credit_budget'][k]=v
            with self.assertRaises(ValueError):g.validate(*args)
        for pid in [1311,2111552,2111966,1894242,2109395,2109397,2109399]:
            args=copy.deepcopy(self.args);args[5]=lambda p,missing=pid: None if p==missing else self.procs.get(p)
            with self.assertRaises(ValueError):g.validate(*args)
        for index,cap in [(0,g.DEADLINE),(1,g.MONO_CAP),(2,g.BOOT_CAP)]:
            args=copy.deepcopy(self.args);args[6][index]=cap
            with self.assertRaises(ValueError):g.validate(*args)
        args=copy.deepcopy(self.args);args[1]['replacement']['worker']['ppid']=99
        with self.assertRaises(ValueError):g.validate(*args)


if __name__ == '__main__':unittest.main(verbosity=2)
