"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Offline state/clock/process/API doubles only; no subprocess, signal or model call.
"""
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location('private_run_bridge', Path(__file__).with_name('bridge.py'))
b = importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(b)
NOW = b.DEADLINE-3600


def state(reason=None, phase='running'):
    return dict(thread_id=b.THREAD, phase=phase, goal={'status': 'active'}, stop_reason=reason,
                settings={'billing': {'mode': 'included_only'}},
                last_rate_limits={'primary': {'usedPercent': 30, 'windowDurationMins': 10080},
                                  'credits': {'hasCredits': True, 'unlimited': False, 'balance': '57774.852125'}})


def decide(s=None, journal=None, now=NOW, retired=False, free=False, permit=None, cancelled=False):
    return b.decide(s or state(), journal or {}, now, retired, free, 'exact-state', permit, cancelled)


class BridgeTests(unittest.TestCase):
    def test_live_resident_untouched_even_with_available_credits(self):
        self.assertEqual(decide(), 'WAIT_RESIDENT_UNCHANGED')

    def test_only_local_real_weekly_exhaustion_is_automatic(self):
        s = state('included_usage_guard', 'stopped'); s['goal']['status'] = 'paused'
        s['last_rate_limits']['primary']['usedPercent'] = 100
        self.assertEqual(decide(s, retired=True, free=True), 'START_EXISTING_LAUNCHER_RECOVERY_ONLY')
        for duration, used in [(300, 100), (10080, 99), (10080, float('inf')), (10080, True)]:
            sample = copy.deepcopy(s); sample['last_rate_limits']['primary'].update(windowDurationMins=duration, usedPercent=used)
            self.assertTrue(decide(sample, retired=True, free=True).startswith('HOLD_'))

    def test_ambiguous_quota_credit_auth_unknown_stops_never_retry(self):
        for reason in ['quota_exhausted', 'credit_balance_decreased', 'credit_balance_unknown',
                       'included_usage_unknown', 'credit_budget_exhausted', 'launcher_error', 'turn_failed']:
            s = state(reason, 'stopped'); s['last_rate_limits']['primary']['usedPercent'] = 100
            self.assertTrue(decide(s, retired=True, free=True).startswith('HOLD_'), reason)

    def test_service_hold_wins_even_over_local_guard_or_permit(self):
        s = state('included_usage_guard', 'stopped'); s['last_rate_limits']['primary']['usedPercent'] = 100
        for info in ['cyberPolicy', 'authRequired', 'billingHold', {'quota': 'held'}]:
            sample = copy.deepcopy(s); sample['last_error'] = {'codexErrorInfo': info}
            self.assertTrue(decide(sample, retired=True, free=True).startswith('HOLD_'))

    def test_positive_retirement_and_lease_are_both_required(self):
        s = state('included_usage_guard', 'stopped'); s['last_rate_limits']['primary']['usedPercent'] = 100
        for retired, free in [(False, False), (True, False), (False, True)]:
            self.assertEqual(decide(s, retired=retired, free=free), 'WAIT_POSITIVE_OLD_MODEL_RETIREMENT_AND_LEASES')

    def test_managed_handoff_needs_final_state_hash_current_resume_and_expiry(self):
        s = state('signal_15', 'stopped'); s['goal']['status'] = 'paused'
        self.assertIn('NO_RESUME', decide(s, retired=True, free=True))
        permit = dict(status='PASS_COORDINATED_MODEL_HANDOFF', thread_id=b.THREAD, deadline=b.DEADLINE,
                      stopped_state_sha256='exact-state', explicit_resume_authorized=True,
                      reason='managed_credit_enablement', review_id='root-final-state-review', expires_unix=NOW+60)
        self.assertEqual(decide(s, retired=True, free=True, permit=permit), 'START_EXISTING_LAUNCHER_RECOVERY_ONLY')
        for key, value in [('stopped_state_sha256','old'), ('explicit_resume_authorized',False), ('expires_unix',NOW)]:
            bad = dict(permit); bad[key] = value
            self.assertIn('NO_RESUME', decide(s, retired=True, free=True, permit=bad))

    def test_later_user_cancel_wins_permit_and_credit(self):
        self.assertEqual(decide(cancelled=True), 'DRAIN_USER_STOP')
        self.assertEqual(decide(state('signal_15'), cancelled=True), 'STOP_USER_STOP')

    def test_deadline_original_one_signal_and_already_draining_skip(self):
        self.assertEqual(decide(now=b.DEADLINE), 'DRAIN_DEADLINE')
        self.assertEqual(decide(journal={'deadline_stop_sent':True}, now=b.DEADLINE), 'WAIT_DEADLINE_DRAIN')
        for s in [state('work_window'), state('signal_15'), state('included_usage_guard')]:
            self.assertEqual(decide(s, now=b.DEADLINE), 'WAIT_DEADLINE_DRAIN')

    def test_finite_watcher_expiry_never_receives_second_bridge_signal(self):
        self.assertEqual(decide(journal={'credit_started':True}, now=b.DEADLINE), 'WAIT_FINITE_WATCHER_DRAIN')
        self.assertEqual(decide(journal={'credit_started':True}, now=b.DEADLINE, retired=True), 'STOP_DEADLINE')

    def test_no_model_start_at_deadline_and_no_unknown_outer_restarts(self):
        s = state('included_usage_guard','stopped'); s['last_rate_limits']['primary']['usedPercent'] = 100
        self.assertEqual(decide(s, now=b.DEADLINE, retired=True, free=True), 'STOP_DEADLINE')
        self.assertEqual(decide(journal={'launch_intent':{}}, retired=True, free=True), 'HOLD_UNCERTAIN_LAUNCH_NO_RETRY')
        self.assertEqual(decide(journal={'launch_intent':{'at':NOW}}), 'HOLD_UNCERTAIN_LAUNCH_NO_RETRY')
        self.assertEqual(decide(journal={'credit_started':True}, retired=True), 'STOP_CREDIT_WATCHER_EXIT_NO_RESTART')

    def test_boot_clock_survives_rollback_suspend_and_rearm(self):
        anchor = 10000
        self.assertEqual(b.effective_now(b.DEADLINE-5000, anchor, anchor), b.DEADLINE)
        self.assertEqual(b.effective_now(b.DEADLINE-20, anchor+5, anchor), b.DEADLINE+5)

    def test_exact_process_retirement_no_pid_arithmetic(self):
        chain = {'watcher':{'pid':9,'start':'11'},'worker':{'pid':50,'start':'12'},'server':{'pid':97,'start':'13'}}
        self.assertTrue(b.old_gone(chain, lambda pid: None))
        self.assertTrue(b.old_gone(chain, lambda pid: {'start':'different'}))
        self.assertFalse(b.old_gone(chain, lambda pid: {'start':chain['worker']['start'] if pid==50 else 'different'}))
        with self.assertRaises(PermissionError):
            b.old_gone(chain, lambda pid: (_ for _ in ()).throw(PermissionError('unknown')))

    def test_fresh_triplet_binds_ppids_and_server_birth(self):
        rows={9:dict(pid=9,start='11',ppid=1,state='S'),50:dict(pid=50,start='12',ppid=9,state='S'),
              97:dict(pid=97,start='13',ppid=50,state='S')}
        s=dict(worker_pid=50,server_pid=97,server_start='13')
        self.assertEqual(b.bind(s, {'watcher_pid':9}, rows.get)['worker']['pid'],50)
        rows[97]['ppid']=49
        with self.assertRaises(ValueError): b.bind(s,{'watcher_pid':9},rows.get)

    def test_prepaid_ceiling_and_unknown_balances(self):
        self.assertEqual(b.prepaid_budget(state()), '57774.852125')
        for balance in ['0','NaN','-1']:
            s=state();s['last_rate_limits']['credits']['balance']=balance
            with self.assertRaises((ValueError,ArithmeticError)): b.prepaid_budget(s)
        s=state();s['last_rate_limits']['credits']['balance']='99999'
        self.assertEqual(b.prepaid_budget(s),'57774.852125')

    def test_restart_reuses_original_vetoes_but_rejects_generic_unknown(self):
        yes=lambda *args:True; no=lambda *args:False
        self.assertFalse(b.strict_restart(yes,-9,state()))
        self.assertFalse(b.strict_restart(yes,0,state()))
        self.assertTrue(b.strict_restart(yes,24,dict(state('active_goal_did_not_continue'),retryable=True)))
        self.assertFalse(b.strict_restart(no,24,dict(state('active_goal_did_not_continue'),retryable=True)))

    def test_stable_credit_id_and_no_fresh_session_flags(self):
        cfg={'deadline_utc':'2026-10-25T00:00:00Z','credit_run_id':'a'*32}
        with patch.object(Path,'read_bytes',return_value=b'current instruction'):
            first=b.launcher_argv(cfg,'100',9999); second=b.launcher_argv(cfg,'100',9999)
        self.assertEqual(first,second)
        self.assertEqual(first[first.index('--credit-run-id')+1],'a'*32)
        self.assertNotIn('--fresh-session',first)
        self.assertNotIn('--fresh-on-recovery',first)
        self.assertIn('--boot-deadline',first)

    def test_owned_replacement_watcher_is_polled_reaped_and_never_relaunched(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); campaign=root/'campaign'; campaign.mkdir(); private=root/'private';private.mkdir()
            s=state('included_usage_guard','stopped');s['goal']['status']='paused'
            s['last_rate_limits']['primary']['usedPercent']=100
            raw=json.dumps(s).encode();(campaign/'state.json').write_bytes(raw)
            (private/'CURRENT-INVOCATION.txt').write_text('explicit current recovery-only instruction')
            journal=dict(original={name:{'pid':pid,'start':'old'} for name,pid in [('watcher',9),('worker',50),('server',97)]},
                         boot_id='mockboot',boot_deadline=3700,credit_run_id='a'*32,deadline=b.DEADLINE,last_clock=NOW)
            (private/'journal.json').write_text(json.dumps(journal))
            cfg=dict(deadline_utc='2026-10-25T00:00:00Z',credit_run_id='a'*32)
            alive=[True]
            class Child:
                pid=12345
                polls=0
                def poll(self):
                    self.polls+=1;alive[0]=False;return 0
            child=Child()
            def observed(pid):
                return dict(pid=pid,start='replacement',ppid=1,state='S') if pid==child.pid and alive[0] else None
            sleeps=[0]
            def sleep(unused):
                sleeps[0]+=1
                if sleeps[0]>2:raise AssertionError('replacement child was not reaped')
            with patch.object(b,'HERE',private),patch.object(b,'CAMPAIGN',campaign),\
                 patch.object(b,'birth',side_effect=observed),patch.object(b,'old_gone',return_value=True),\
                 patch.object(b,'leases_free',return_value=True),patch.object(b.time,'time',return_value=NOW),\
                 patch.object(b.time,'clock_gettime',return_value=100),patch.object(b.time,'sleep',side_effect=sleep),\
                 patch.object(Path,'read_text',return_value='mockboot'),\
                 patch.object(b.subprocess,'Popen',return_value=child) as popen,patch.object(b,'stop_worker') as stop:
                self.assertEqual(b.run(cfg),'STOP_CREDIT_WATCHER_EXIT_NO_RESTART')
            self.assertEqual(popen.call_count,1);self.assertEqual(child.polls,1);stop.assert_not_called()
            self.assertEqual((campaign/'state.json').read_bytes(),raw)


if __name__ == '__main__':
    unittest.main(verbosity=2)
