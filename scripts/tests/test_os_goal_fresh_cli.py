"""Offline fresh-session CLI boundaries; no server or inference."""
import contextlib
import io
import json
from pathlib import Path
import signal
import sys
import tempfile
import unittest
from unittest import mock

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))
import run_os_goal as launcher
import os_goal_sessions as sessions


class FreshCLITests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.repo = Path(self.temp.name)
        self.directory = self.repo / '.git/os-autopilot'
        self.directory.mkdir(parents=True)
        self.state_path = self.directory / 'state.json'
        self.original = json.dumps({
            'schema_version': 1, 'repo': str(self.repo), 'thread_id': 'old-thread',
            'phase': 'stopped', 'goal': {'status': 'paused', 'objective': launcher.OBJECTIVE},
            'worker_pid': 2147483646, 'server_pid': 2147483647,
            'active_turns': {},
        }).encode()
        self.state_path.write_bytes(self.original)

    def main(self, argv):
        with mock.patch.object(launcher, 'REPO', self.repo), \
                mock.patch.object(launcher.subprocess, 'check_output', return_value='.git\n'), \
                mock.patch.object(launcher.shutil, 'which', return_value='/bin/codex'), \
                contextlib.redirect_stdout(io.StringIO()):
            return launcher.main(argv)

    def test_explicit_fresh_worker_archives_before_campaign_under_existing_lease(self):
        sentinel = self.repo / 'compiled-image'
        sentinel.write_bytes(b'retained image')

        def campaign(args, repo, directory):
            state = json.loads(self.state_path.read_bytes())
            self.assertIsNone(state['thread_id'])
            self.assertEqual(Path(state['previous_session']['state_path']).read_bytes(), self.original)
            with (directory / 'run.lock').open('rb') as stream:
                with self.assertRaises(BlockingIOError):
                    launcher.fcntl.flock(stream, launcher.fcntl.LOCK_EX | launcher.fcntl.LOCK_NB)
            return mock.Mock(run=mock.Mock(return_value=0))

        with mock.patch.object(launcher, 'Campaign', side_effect=campaign), \
                mock.patch.object(launcher.signal, 'signal'):
            self.assertEqual(self.main(['--worker', '--fresh-session']), 0)
        self.assertEqual(sentinel.read_bytes(), b'retained image')

    def test_fresh_dry_run_never_archives_or_starts_a_session(self):
        with mock.patch.object(sessions, 'prepare_fresh_session') as prepare, \
                mock.patch.object(launcher, 'server_argv', return_value=['codex', 'app-server']), \
                mock.patch.object(launcher, 'launch_resources', return_value={}), \
                mock.patch.object(launcher, 'policy_hashes', return_value={}), \
                mock.patch.object(launcher, 'window_capability', return_value={}):
            self.assertEqual(self.main(['--dry-run', '--fresh-session']), 0)
        prepare.assert_not_called()
        self.assertEqual(self.state_path.read_bytes(), self.original)

    def test_fresh_settings_check_never_archives_or_starts_inference(self):
        with mock.patch.object(sessions, 'prepare_fresh_session') as prepare, \
                mock.patch.object(launcher, 'server_argv', return_value=['codex', 'app-server']), \
                mock.patch.object(launcher, 'RPC') as rpc, \
                mock.patch.object(launcher, 'preflight', return_value={'model': 'gpt-6.1-sol'}):
            self.assertEqual(self.main(['--check', '--fresh-session']), 0)
        prepare.assert_not_called()
        rpc.return_value.close.assert_called_once()
        self.assertEqual(self.state_path.read_bytes(), self.original)

    def test_recovery_receipt_requires_supervised_recovered_mode(self):
        for options in ([], ['--worker'], ['--worker', '--recovered']):
            with self.subTest(options=options), contextlib.redirect_stderr(io.StringIO()), \
                    self.assertRaises(SystemExit):
                launcher.arguments([*options, '--fresh-recovery-proof', '/tmp/proof.json'])
        args = launcher.arguments(['--worker', '--recovered', '--fresh-on-recovery',
                                   '--fresh-recovery-proof', '/tmp/proof.json'])
        self.assertEqual(args.fresh_recovery_proof, Path('/tmp/proof.json'))


class MetadataRPC:
    def __init__(self, args, old):
        self.args, self.old = args, dict(old)
        self.new = None
        self.calls = []
        self.fail_read = False
        self.fail_create = False
        self.old_turn_active = False
        self.settled_tokens_used = None

    def factory(self, *args):
        return self

    def call(self, method, params, **kwargs):
        self.calls.append((method, dict(params)))
        if method == 'account/read':
            return {'account': {'type': 'chatgpt'}}
        if method == 'account/rateLimits/read':
            return {'rateLimits': {'primary': {'usedPercent': 1}, 'credits': {'balance': '0'}}}
        if method == 'thread/goal/get':
            if self.fail_read:
                raise RuntimeError('metadata read failed')
            goal = self.old if params['threadId'] == 'old-thread' else self.new
            return {'goal': dict(goal) if goal else None}
        if method == 'thread/turns/list':
            if self.settled_tokens_used is not None:
                self.old['tokensUsed'] = self.settled_tokens_used
            return {'data': [{'status': 'inProgress'}] if self.old_turn_active else [], 'nextCursor': None}
        if method in {'thread/start', 'thread/resume'}:
            return {'thread': {'id': 'new-thread'}, 'model': self.args.model,
                    'reasoningEffort': self.args.effort, 'approvalPolicy': 'never',
                    'sandbox': {'type': 'dangerFullAccess'}}
        if method == 'thread/goal/set':
            if params['threadId'] == 'old-thread':
                self.old.update(status=params['status'])
                return {'goal': dict(self.old)}
            if self.fail_create:
                raise RuntimeError('goal creation transport failed')
            self.new = self.new or {'objective': params['objective'], 'tokensUsed': 0, 'tokenBudget': None}
            self.new.update({key: value for key, value in params.items() if key != 'threadId'})
            return {'goal': dict(self.new)}
        raise AssertionError('Unexpected RPC: ' + method)


class FreshGoalBootstrapTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name)
        self.args = launcher.arguments(['--hours', '0', '--agent-windows', 'off', '--quiet', '--fresh-session'])
        self.old = {'objective': launcher.OBJECTIVE, 'status': 'blocked', 'tokenBudget': 1000, 'tokensUsed': 300}
        self.path = self.directory / 'state.json'
        launcher.atomic_json(self.path, {'schema_version': 1, 'repo': str(self.directory),
            'thread_id': 'old-thread', 'phase': 'stopped', 'worker_pid': 2147483646,
            'server_pid': None, 'goal': self.old, 'stop_reason': 'turn_failed'})
        sessions.prepare_fresh_session(self.directory, self.directory, launcher.atomic_json,
                                       expected_objective=launcher.OBJECTIVE)
        self.rpc = MetadataRPC(self.args, self.old)

    def campaign(self):
        campaign = launcher.Campaign(self.args, self.directory, self.directory, self.rpc.factory)
        self.addCleanup(campaign.output.close)
        return campaign

    def begin(self, campaign):
        with mock.patch.object(launcher, 'preflight', return_value={}), \
                mock.patch.object(launcher, 'check_resources'), \
                mock.patch.object(launcher, 'launch_resources', return_value={}), \
                mock.patch.object(launcher, 'server_argv', return_value=[]), \
                mock.patch.object(launcher, 'resource_instructions', return_value=''), \
                mock.patch.object(launcher, 'policy_hashes', return_value={}), \
                contextlib.redirect_stdout(io.StringIO()):
            campaign.begin()

    def test_blocked_predecessor_is_read_without_resume_or_change_and_remaining_budget_carried(self):
        campaign = self.campaign()
        self.begin(campaign)
        self.assertEqual(self.rpc.old, self.old)
        self.assertFalse(any(method == 'thread/resume' for method, _ in self.rpc.calls))
        changes = [params for method, params in self.rpc.calls if method == 'thread/goal/set']
        self.assertEqual(changes, [{'threadId': 'new-thread', 'status': 'active',
                                   'objective': launcher.OBJECTIVE, 'tokenBudget': 700}])
        self.assertEqual(campaign.state['fresh_token_budget'], 700)
        self.assertEqual(self.rpc.calls[2], ('thread/goal/get', {'threadId': 'old-thread'}))

    def test_active_predecessor_pauses_before_new_thread_start(self):
        self.rpc.old['status'] = 'active'
        self.begin(self.campaign())
        pause = self.rpc.calls.index(('thread/goal/set', {'threadId': 'old-thread', 'status': 'paused'}))
        start = next(index for index, (method, _) in enumerate(self.rpc.calls) if method == 'thread/start')
        self.assertLess(pause, start)
        self.assertEqual(self.rpc.old['status'], 'paused')

    def test_predecessor_active_turn_refuses_new_thread_after_pausing_goal(self):
        self.rpc.old['status'] = 'active'
        self.rpc.old_turn_active = True
        with self.assertRaisesRegex(RuntimeError, 'still has an active turn'):
            self.begin(self.campaign())
        self.assertEqual(self.rpc.old['status'], 'paused')
        self.assertFalse(any(method == 'thread/start' for method, _ in self.rpc.calls))

    def test_blocked_predecessor_active_turn_is_preserved_and_refuses_new_thread(self):
        self.rpc.old_turn_active = True
        with self.assertRaisesRegex(RuntimeError, 'still has an active turn'):
            self.begin(self.campaign())
        self.assertEqual(self.rpc.old, self.old)
        self.assertFalse(any(method in {'thread/start', 'thread/goal/set'} for method, _ in self.rpc.calls))

    def test_final_old_turn_usage_is_settled_before_new_budget_is_computed(self):
        self.rpc.old['status'] = 'active'
        self.rpc.settled_tokens_used = 450
        self.begin(self.campaign())
        self.assertEqual(self.rpc.new['tokenBudget'], 550)
        listed = next(index for index, (method, _) in enumerate(self.rpc.calls) if method == 'thread/turns/list')
        refreshed = next(index for index, (method, params) in enumerate(self.rpc.calls)
                         if index > listed and method == 'thread/goal/get' and params['threadId'] == 'old-thread')
        start = next(index for index, (method, _) in enumerate(self.rpc.calls) if method == 'thread/start')
        self.assertLess(listed, refreshed)
        self.assertLess(refreshed, start)

    def test_terminal_predecessor_never_starts_new_thread_or_changes_old_goal(self):
        for status in ('complete', 'usageLimited', 'budgetLimited'):
            with self.subTest(status=status):
                self.rpc.calls.clear()
                self.rpc.old['status'] = status
                campaign = self.campaign()
                self.begin(campaign)
                self.assertEqual(campaign.goal['status'], status)
                self.assertFalse(any(method in {'thread/start', 'thread/resume', 'thread/goal/set'}
                                     for method, _ in self.rpc.calls))

    def test_missing_failed_or_foreign_predecessor_goal_fails_before_thread_start(self):
        for scenario in ('read_error', 'missing', 'foreign'):
            with self.subTest(scenario=scenario):
                self.rpc.calls.clear()
                self.rpc.fail_read = scenario == 'read_error'
                self.rpc.old = {} if scenario == 'missing' else dict(self.old)
                if scenario == 'foreign':
                    self.rpc.old['objective'] = 'Different objective'
                with self.assertRaises(RuntimeError):
                    self.begin(self.campaign())
                self.assertFalse(any(method in {'thread/start', 'thread/resume', 'thread/goal/set'}
                                     for method, _ in self.rpc.calls))

    def test_requested_budget_can_only_reduce_carried_allowance(self):
        self.args.token_budget = 400
        self.begin(self.campaign())
        self.assertEqual(self.rpc.new['tokenBudget'], 400)

    def test_crash_after_new_thread_creation_reuses_durable_allowance(self):
        self.args.token_budget = 1000
        self.rpc.fail_create = True
        with self.assertRaisesRegex(RuntimeError, 'transport failed'):
            self.begin(self.campaign())
        self.assertEqual(json.loads(self.path.read_bytes())['fresh_token_budget'], 700)
        self.rpc.fail_create = False
        self.rpc.calls.clear()
        self.args.recovered = True
        self.begin(self.campaign())
        self.assertEqual(self.rpc.new['tokenBudget'], 700)
        self.assertFalse(any(method == 'thread/start' for method, _ in self.rpc.calls))

    def test_recovery_does_not_reapply_original_cli_budget_to_existing_goal(self):
        self.args.token_budget = 1000
        self.begin(self.campaign())
        self.rpc.new['tokensUsed'] = 100
        self.rpc.calls.clear()
        self.args.recovered = True
        self.begin(self.campaign())
        self.assertEqual(self.rpc.new['tokenBudget'], 700)
        self.assertFalse(any('tokenBudget' in params for _, params in self.rpc.calls))

    def test_exhausted_allowance_does_not_create_a_new_conversation(self):
        self.rpc.old['tokensUsed'] = 1000
        campaign = self.campaign()
        self.begin(campaign)
        self.assertTrue(campaign.stop_now)
        self.assertEqual(campaign.stop_reason, 'budget_exhausted')
        self.assertFalse(any(method == 'thread/start' for method, _ in self.rpc.calls))

    def test_watchdog_requires_valid_request_and_preserves_existing_stops(self):
        campaign = self.campaign()
        with mock.patch('watch_os_goal.watchdog_requested', return_value=True):
            campaign.on_watchdog(signal.SIGUSR1, None)
            self.assertEqual(campaign.stop_reason, 'watchdog_recovery')
            for reason in ('signal_15', 'included_usage_guard', 'turn_failed'):
                campaign.stop_reason = reason
                campaign.on_watchdog(signal.SIGUSR1, None)
                self.assertEqual(campaign.stop_reason, reason)
        with mock.patch('watch_os_goal.watchdog_requested', return_value=False):
            campaign.on_watchdog(signal.SIGUSR1, None)
        self.assertEqual(campaign.stop_reason, 'signal_' + str(signal.SIGUSR1))


if __name__ == '__main__':
    unittest.main()
