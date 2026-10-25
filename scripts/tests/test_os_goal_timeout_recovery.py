"""Offline functional OS supervision tests; no actual workers or signals."""
import importlib.util
import hashlib
import json
import io
import os
import sys
from contextlib import redirect_stdout
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

spec = importlib.util.spec_from_file_location('watch_candidate', (Path(__file__).resolve().parents[1] / 'watch_os_goal.py'))
watcher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(watcher)


def state(status='active', **changes):
    result = {'thread_id': 'same-thread', 'worker_pid': 101, 'goal': {'status': status},
              'stop_reason': 'credit_budget_unknown',
              'credit_budget_error': 'App-server request timed out: account/rateLimits/read'}
    result.update(changes)
    return result


class CreditWatcher(unittest.TestCase):
    def test_only_exact_timeout_exit_class_restarts(self):
        self.assertTrue(watcher.credit_poll_timeout(state()))
        self.assertFalse(watcher.should_restart(21, state()))
        for error in ['unknown', '401 Unauthorized', 'billing unavailable',
                      'App-server request timed out: account/read']:
            self.assertFalse(watcher.should_restart(21, state(credit_budget_error=error)))
        self.assertFalse(watcher.should_restart(23, state()))
        self.assertFalse(watcher.should_restart(21, state(thread_id=None)))

    def test_real_unknown_exhaustion_auth_policy_and_holds_stay_stopped(self):
        for reason in ['credit_budget_exhausted', 'included_usage_unknown', 'chatgpt_auth_changed',
                       'policy_hold', 'quota_exhausted', 'signal_2', 'work_window']:
            self.assertFalse(watcher.should_restart(21, state(stop_reason=reason), watchdog=True))
        for flag in ['service_hold', 'policy_hold', 'auth_hold', 'billing_hold']:
            self.assertFalse(watcher.should_restart(21, state(**{flag: True})))
        for info in ['usageLimitExceeded', 'sessionBudgetExceeded', 'authentication', 'billing']:
            self.assertFalse(watcher.should_restart(21, state(last_error={'codexErrorInfo': info})))

    def test_user_pause_and_terminal_states_never_promoted(self):
        for status in ['paused', 'blocked', 'complete', 'usageLimited', 'budgetLimited']:
            self.assertFalse(watcher.should_restart(21, state(status), watchdog=True))
        self.assertFalse(watcher.should_restart(21, state(), stopped=True))

    def supervise(self, retire, owned=False, startup_retry=False):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            first = Mock(pid=101, returncode=21); first.poll.return_value = 21
            second = Mock(pid=102, returncode=0); second.poll.return_value = 0
            third = Mock(pid=103, returncode=0); third.poll.return_value = 0
            args = SimpleNamespace(hours=.1, max_restarts=2, fresh_on_recovery=True,
                                   restart_delay=0, heartbeat_seconds=10)
            terminal = state('complete', worker_pid=102, stop_reason=None)
            initial = state()
            if owned:
                goal = {'status': 'paused', 'updatedAt': 2, 'objective': 'same-objective'}
                initial.update(goal=goal, worker_start='700')
                initial['credit_timeout_shutdown_pause'] = {
                    'schema_version': 1, 'worker_pid': 101, 'worker_start': '700',
                    'thread_id': 'same-thread', 'stop_reason': initial['stop_reason'],
                    'credit_budget_error': initial['credit_budget_error'],
                    'pause_method': 'thread/goal/set', 'pause_confirmed': True,
                    'goal_before': dict(goal, status='active', updatedAt=1), 'goal_after': goal,
                    'goal_after_sha256': hashlib.sha256(json.dumps(
                        goal, sort_keys=True, separators=(',', ':')).encode()).hexdigest()}
            states = [initial, terminal]
            children = [first, second]
            if startup_retry:
                second.returncode = 21; second.poll.return_value = 21
                pending = state('paused', worker_pid=102, worker_start='700', goal=goal)
                pending['credit_timeout_startup'] = {'schema_version': 1, 'worker_pid': 102,
                    'worker_start': '700', 'watcher_pid': os.getpid(), 'watcher_start': '700',
                    'thread_id': 'same-thread', 'before_inference': True, 'account_validated': True,
                    'phase_at_failure': 'starting', 'expected_goal_sha256':
                    initial['credit_timeout_shutdown_pause']['goal_after_sha256']}
                terminal['worker_pid'] = 103
                states = [initial, pending, terminal]; children.append(third)
            published = []
            clock = iter(range(100, 1000))
            with patch.object(watcher.subprocess, 'Popen', side_effect=children) as spawn, \
                    patch.object(watcher, 'snapshot', side_effect=states), \
                    patch.object(watcher, 'retire_server', return_value=retire) as retirement, \
                    patch.object(watcher, 'process_start', return_value='700'), \
                    patch.object(watcher.time, 'monotonic', side_effect=lambda: next(clock)), \
                    patch.object(watcher.signal, 'signal'), redirect_stdout(io.StringIO()):
                code = watcher.supervise(args, directory, directory,
                                         ['--fresh-session', '--credit-budget', '100',
                                          '--credit-run-id', 'a' * 32], lambda _: Mock(),
                                         lambda path, value: published.append(value))
            return code, spawn.call_args_list, retirement.call_count, published

    def test_same_thread_route_no_fresh_proof_budget_unchanged_cutoff_tightens(self):
        code, calls, retired, published = self.supervise(True, owned=True)
        self.assertEqual((code, len(calls), retired), (0, 2, 2))
        first, second = [c.args[0] for c in calls]
        self.assertIn('--recovered', second)
        self.assertNotIn('--fresh-session', second)
        self.assertNotIn('--fresh-recovery-proof', second)
        self.assertIn('--credit-timeout-goal-sha256', second)
        self.assertEqual(second[second.index('--credit-run-id') + 1], 'a' * 32)
        self.assertEqual(second[second.index('--credit-budget') + 1], '100')
        self.assertLess(float(second[second.index('--hours') + 1]),
                        float(first[first.index('--hours') + 1]))
        started = [r for r in published if r['event'] == 'worker_started'][-1]
        self.assertEqual(started['worker_pid'], 102)
        self.assertTrue(started['credit_timeout_recovery']['approved'])
        self.assertEqual(started['credit_timeout_recovery']['worker_pid'], 101)
        self.assertEqual(started['credit_timeout_recovery']['thread_id'], 'same-thread')

    def test_no_restart_without_positive_server_retirement(self):
        code, calls, retired, _ = self.supervise(False)
        self.assertEqual((code, len(calls), retired), (1, 1, 1))

    def test_startup_timeout_retries_only_under_same_live_watcher_origin(self):
        code, calls, retired, published = self.supervise(True, owned=True, startup_retry=True)
        self.assertEqual((code, len(calls), retired), (0, 3, 3))
        for call in calls[1:]:
            self.assertNotIn('--fresh-recovery-proof', call.args[0])
            self.assertIn('--credit-timeout-goal-sha256', call.args[0])
        lineage = [r['credit_timeout_recovery'] for r in published if r['event'] == 'worker_started'][1:]
        self.assertEqual(lineage[0], lineage[1])


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
launchspec = importlib.util.spec_from_file_location('launch_candidate', (Path(__file__).resolve().parents[1] / 'run_os_goal.py'))
launcher = importlib.util.module_from_spec(launchspec)
launchspec.loader.exec_module(launcher)


class PauseReceipt(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(); self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        args = launcher.arguments(['--hours', '0', '--agent-windows', 'off'])
        self.c = launcher.Campaign(args, self.root, self.root)
        self.addCleanup(self.c.output.close)
        self.c.controlled, self.c.stopping, self.c.stop_now = True, True, True
        self.c.stop_reason = 'credit_budget_unknown'
        self.c.state.update(state(), worker_pid=os.getpid(), worker_start='700')
        self.before = {'status': 'active', 'updatedAt': 1, 'objective': launcher.OBJECTIVE}
        self.after = dict(self.before, status='paused', updatedAt=2)
        self.c.rpc = Mock()

    def pause(self, before=None, after=None):
        self.c.rpc.call.side_effect = [{'goal': self.before if before is None else before},
                                       {'goal': self.after if after is None else after}]
        self.c.pause()

    def test_actual_owned_pause_receipt_and_fingerprint_changes_veto(self):
        self.pause()
        self.assertTrue(watcher.timeout_pause_owned(self.c.state))
        self.assertTrue(watcher.should_restart(21, self.c.state))
        for field, value in [('worker_start', '701'), ('thread_id', 'other')]:
            changed = dict(self.c.state, **{field: value})
            self.assertFalse(watcher.timeout_pause_owned(changed))
        changed = dict(self.c.state, goal=dict(self.after, updatedAt=3))
        self.assertFalse(watcher.timeout_pause_owned(changed))

    def test_preexisting_userpause_block_checkpoint_or_signal_has_no_receipt(self):
        self.pause(before=dict(self.before, status='paused'))
        self.assertNotIn('credit_timeout_shutdown_pause', self.c.state)
        self.c.checkpoint_requested = True
        self.pause()
        self.assertNotIn('credit_timeout_shutdown_pause', self.c.state)
        self.c.checkpoint_requested = False
        def call(method, params):
            if method == 'thread/goal/get': return {'goal': self.before}
            self.c.on_signal(2, None)
            return {'goal': self.after}
        self.c.rpc.call.side_effect = call
        self.c.pause()
        self.assertNotIn('credit_timeout_shutdown_pause', self.c.state)

    def test_uncertain_pause_later_goal_event_and_new_instance_clear_authority(self):
        self.c.rpc.call.side_effect = [{'goal': self.before}, RuntimeError('timeout')]
        with self.assertRaises(RuntimeError): self.c.pause()
        self.assertNotIn('credit_timeout_shutdown_pause', self.c.state)
        self.pause()
        self.c.event({'method': 'thread/goal/updated',
                      'params': {'threadId': 'same-thread', 'goal': self.after}})
        self.assertNotIn('credit_timeout_shutdown_pause', self.c.state)
        self.pause()
        args = launcher.arguments(['--hours', '0', '--agent-windows', 'off'])
        new = launcher.Campaign(args, self.root, self.root)
        self.addCleanup(new.output.close)
        self.assertNotIn('credit_timeout_shutdown_pause', new.state)

    def test_startup_changed_goal_vetoes_before_thread_resume(self):
        spec = importlib.util.spec_from_file_location(
            'existing_fakes', str(Path(__file__).with_name('test_os_goal_launcher.py')))
        old = importlib.util.module_from_spec(spec); spec.loader.exec_module(old)
        expected = hashlib.sha256(json.dumps(
            self.after, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
        self.c.args = launcher.arguments(['--hours', '0', '--agent-windows', 'off',
                                          '--worker', '--recovered',
                                          '--credit-timeout-goal-sha256', expected])
        rpc = old.FakeRPC(self.c.args, live_goal=dict(self.after, updatedAt=3))
        self.c.rpc_factory = rpc.factory
        self.c.controlled, self.c.stopping, self.c.stop_now = False, False, False
        self.c.stop_reason = None
        with patch.object(launcher, 'check_resources'), patch.object(launcher, 'preflight', return_value={}):
            self.c.begin()
        self.assertEqual(self.c.stop_reason, 'startup_goal_stopped')
        self.assertFalse(any(name in {'thread/resume', 'thread/start', 'turn/start'}
                             for name, _ in rpc.calls))

    def test_startup_marker_is_not_approval_without_matching_watcher_origin(self):
        self.pause()
        origin = dict(self.c.state['credit_timeout_shutdown_pause'], approved=True,
                      watcher_pid=os.getppid(), watcher_start='800')
        self.c.state.pop('credit_timeout_shutdown_pause')
        self.c.controlled, self.c.stopping, self.c.stop_now = False, False, False
        self.c.stop_reason = None
        self.c.args.credit_timeout_goal_sha256 = origin['goal_after_sha256']
        self.c.state.update(phase='starting', auth_mode='chatgpt')
        self.c.credit_guard = launcher.CreditBudget(self.root, 'a' * 32, '100', launcher.atomic_json)
        self.c.rpc.call.side_effect = launcher.RecoverableFailure(
            'App-server request timed out: account/rateLimits/read')
        with patch('watch_os_goal.process_start', return_value='800'):
            self.c.refresh_credit_budget()
        self.c.state['stop_reason'] = self.c.stop_reason
        self.assertIn('credit_timeout_startup', self.c.state)
        self.assertFalse(watcher.should_restart(21, self.c.state))
        self.c.state['_credit_timeout_origin'] = origin
        self.assertTrue(watcher.should_restart(21, self.c.state))
        self.c.state['_credit_timeout_origin'] = dict(origin, watcher_start='different')
        self.assertFalse(watcher.should_restart(21, self.c.state))


if __name__ == '__main__':
    unittest.main()
