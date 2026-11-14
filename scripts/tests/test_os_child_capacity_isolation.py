"""Offline event-method tests. AST-extract Campaign; never import/run launcher."""
import ast
import copy
from decimal import Decimal, InvalidOperation
from pathlib import Path
import time
import math
import unittest
from unittest.mock import Mock
from types import SimpleNamespace

SOURCE = Path(__file__).resolve().parents[1] / 'run_os_goal.py'
tree = ast.parse(SOURCE.read_bytes())
campaign_ast = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'Campaign')
namespace = dict(RPC=object, utc=lambda: 'offline-time', time=time, math=math,
                 Decimal=Decimal, InvalidOperation=InvalidOperation,
                 TERMINAL_CODES={'complete': 0, 'paused': 10, 'blocked': 20,
                                 'usageLimited': 21, 'budgetLimited': 22},
                 LIMIT_ERRORS={'usageLimitExceeded', 'sessionBudgetExceeded'},
                 INCLUDED_USAGE_STOP_PERCENT=97, USER_INPUT_METHOD='item/tool/requestUserInput')
exec(compile(ast.Module(body=[campaign_ast], type_ignores=[]), str(SOURCE), 'exec'), namespace)
Campaign = namespace['Campaign']


class Capacity(unittest.TestCase):
    def setUp(self):
        # Bypass constructor entirely: no real output/files/RPC/environment helpers.
        self.c = c = object.__new__(Campaign)
        c.state = {'thread_id': 'root'}
        c.active = {'root': 'root-turn', 'child': 'child-turn', 'sibling': 'sibling-turn'}
        c.goal = {'status': 'active'}
        c.controlled = True
        c.stopping = c.stop_now = c.checkpoint_requested = False
        c.stop_reason = None
        c.capacity_children = {}
        c.child_capacity_failures = []
        c.log_dir = Path('/offline-never-opened')
        c.state_path = Path('/offline-never-opened/state.json')
        c.output = Mock()
        c.rpc = Mock(side_effect=AssertionError('RPC forbidden'))
        c.save = lambda **fields: c.state.update(copy.deepcopy(fields))
        self.provenance()

    def provenance(self, **changes):
        data = dict(threadId='root', turnId='root-turn', item=dict(
            type='subAgentActivity', kind='interacted', agentThreadId='child',
            agentPath='/root/reviewer'))
        data.update(changes)
        self.c.event(dict(method='item/started', params=data))

    def failure(self, method='error', thread='child', turn='child-turn', code='serverOverloaded', **extra):
        error = dict(codexErrorInfo=code, message='capacity unavailable')
        if method == 'error':
            data = dict(threadId=thread, turnId=turn, error=error, willRetry=False)
        else:
            data = dict(threadId=thread, turn=dict(id=turn, status='failed', error=error))
        data.update(extra)
        self.c.event(dict(method=method, params=data))

    def assert_healthy(self):
        self.assertIsNone(self.c.stop_reason)
        self.assertFalse(self.c.stop_now)
        self.assertEqual(self.c.active['root'], 'root-turn')
        self.assertEqual(self.c.active['sibling'], 'sibling-turn')
        self.assertEqual(self.c.goal['status'], 'active')
        self.assertNotIn('last_error', self.c.state)
        self.assertNotIn('last_failure', self.c.state)
        self.assertEqual(self.c.rpc.mock_calls, [])

    def test_both_orders_duplicates_and_parent_other_child_continue(self):
        for order in [('error', 'turn/completed'), ('turn/completed', 'error')]:
            with self.subTest(order=order):
                self.setUp()
                for method in order + order:
                    self.failure(method)
                self.assert_healthy()
                self.assertNotIn('child', self.c.active)
                self.assertEqual(len(self.c.child_capacity_failures), 1)
                row = self.c.child_capacity_failures[0]
                self.assertEqual(set(row['events']), {'server_error', 'turn_failed'})
                self.assertFalse(row['automatic_retry'])
                self.assertGreater(row['retry_not_before_unix'], time.time() + 50)
                self.c.output.notice.assert_called_once()

    def test_root_unknown_absent_threads_and_unknown_turn_remain_fatal(self):
        for thread, turn in [('root', 'root-turn'), ('unknown', 'x'), (None, None),
                             ('child', 'unobserved-turn')]:
            for method in ('error', 'turn/completed'):
                with self.subTest(thread=thread, method=method):
                    self.setUp()
                    self.failure(method, thread=thread, turn=turn)
                    self.assertTrue(self.c.stop_now)
                    self.assertEqual(self.c.state['last_error']['codexErrorInfo'], 'serverOverloaded')

    def test_policy_unknown_rate_and_quota_errors_still_fatal(self):
        for code in ('cyberPolicy', 'unknown', 'rateLimitExceeded', 'usageLimitExceeded',
                     'sessionBudgetExceeded', None):
            for method in ('error', 'turn/completed'):
                with self.subTest(code=code, method=method):
                    self.setUp()
                    self.failure(method, code=code)
                    self.assertTrue(self.c.stop_now)
                    self.assertEqual(self.c.state['last_error']['codexErrorInfo'], code)
                    if code in ('usageLimitExceeded', 'sessionBudgetExceeded'):
                        self.assertEqual(self.c.stop_reason, 'quota_exhausted')

    def test_unproven_or_wrong_parent_or_turn_fails_closed(self):
        variants = [dict(threadId='sibling'), dict(turnId='stale'),
                    dict(item={'type': 'subAgentActivity', 'kind': 'interacted',
                               'agentThreadId': 'child', 'agentPath': '/root/deeper/child'}),
                    dict(item={'type': 'subAgentActivity', 'kind': 'unknown',
                               'agentThreadId': 'child', 'agentPath': '/root/reviewer'}),
                    dict(item={'type': 'subAgentActivity', 'kind': 'started',
                               'agentThreadId': 'child'})]
        for variant in variants:
            with self.subTest(variant=variant):
                self.setUp()
                self.c.capacity_children.clear()
                self.provenance(**variant)
                self.failure()
                self.assertTrue(self.c.stop_now)

    def test_explicit_stops_and_prior_fatal_fields_remain_intact(self):
        for stop in ('signal_2', 'work_window', 'needs_user_input', 'goal_cleared',
                     'quota_exhausted', 'included_usage_guard', 'credit_balance_decreased',
                     'turn_failed'):
            with self.subTest(stop=stop):
                self.setUp()
                self.c.stop_reason, self.c.stop_now = stop, True
                fatal = {'codexErrorInfo': 'cyberPolicy'}
                old = dict(last_error=fatal, last_failure={'id': 'fatal-turn', 'error': fatal},
                           stop_reason=stop)
                self.c.state.update(copy.deepcopy(old))
                self.failure()
                self.failure('turn/completed')
                self.assertEqual(self.c.stop_reason, stop)
                self.assertTrue(self.c.stop_now)
                for key, value in old.items():
                    self.assertEqual(self.c.state[key], value)

    def test_97_percent_unknown_usage_credit_auth_stops_win_both_orders(self):
        cases = [dict(primary={'usedPercent': 97}), dict(primary={'usedPercent': None}),
                 dict(primary={'usedPercent': 1}, credits={'balance': '0'})]
        for limits in cases:
            for before in (True, False):
                with self.subTest(limits=limits, before=before):
                    self.setUp()
                    self.c.state['last_rate_limits'] = dict(credits={'balance': '1'})
                    if before:
                        self.c.record_rate_limits(limits)
                    self.failure()
                    if not before:
                        self.c.record_rate_limits(limits)
                    self.assertTrue(self.c.stop_now)
        self.setUp()
        self.failure()
        self.c.event(dict(method='account/updated', params={'authMode': 'apiKey'}))
        self.assertEqual(self.c.stop_reason, 'chatgpt_auth_changed')

    def test_server_goal_pause_and_clear_are_never_automatically_reversed(self):
        self.failure()
        self.c.event(dict(method='thread/goal/updated', params=dict(
            threadId='root', goal={'status': 'paused'})))
        self.assertEqual(self.c.goal['status'], 'paused')
        self.failure('turn/completed')
        self.assertEqual(self.c.goal['status'], 'paused')
        self.c.event(dict(method='thread/goal/cleared', params=dict(threadId='root')))
        self.assertEqual(self.c.stop_reason, 'goal_cleared')
        self.assertTrue(self.c.stop_now)
        self.assertEqual(self.c.rpc.mock_calls, [])

    def test_no_parent_health_and_no_existing_hold_fails_closed(self):
        self.c.active.pop('root')
        self.failure()
        self.assertTrue(self.c.stop_now)

    def test_bounded_records_and_provenance(self):
        for n in range(80):
            child = 'child-' + str(n)
            self.provenance(item=dict(type='subAgentActivity', kind='started',
                                     agentThreadId=child, agentPath='/root/c' + str(n)))
        self.assertEqual(len(self.c.capacity_children), 64)
        for n in range(20):
            turn = 'turn-' + str(n)
            self.c.active['child'] = turn
            self.failure(turn=turn)
        self.assertEqual(len(self.c.child_capacity_failures), 16)
        self.assertEqual(self.c.child_capacity_failures[-1]['turn_id'], 'turn-19')
        self.assert_healthy()

    def test_run_keeps_pumping_ready_work_after_child_failure(self):
        c = self.c
        c.args = SimpleNamespace(hours=0, grace_seconds=30, heartbeat_seconds=60)
        c.state['server_pid'] = 123
        c.begin = Mock()
        c.stop = Mock()  # Real shutdown/RPC is deliberately never exercised.
        namespace['os'] = SimpleNamespace(getpid=lambda: 1)
        namespace['restart_advice'] = lambda state: 'offline'
        calls = []

        def pump(timeout):
            calls.append(timeout)
            if len(calls) == 1:
                self.failure()
                self.failure('turn/completed')
                self.assertIsNone(c.stop_reason)
            elif len(calls) == 2:
                self.assertIn('root', c.active)
                self.assertIn('sibling', c.active)
                c.event(dict(method='thread/goal/updated', params=dict(
                    threadId='root', goal={'status': 'complete'})))
            else:
                raise AssertionError('unexpected extra loop iteration')

        c.deliver_instruction = Mock()
        c.rpc.pump.side_effect = pump
        self.assertEqual(c.run(), 0)
        self.assertEqual(len(calls), 2)
        c.rpc.call.assert_not_called()
        c.rpc.close.assert_called_once()

    def test_missing_completion_error_does_not_infer_capacity(self):
        self.failure()
        self.c.event(dict(method='turn/completed', params=dict(threadId='child',
            turn=dict(id='child-turn', status='failed', error=None))))
        self.assertTrue(self.c.stop_now)
        self.assertEqual(self.c.stop_reason, 'turn_failed')

    def test_missing_empty_error_turn_id_stays_fatal_despite_proven_child(self):
        for supplied in ('missing', 'empty'):
            for prior in ('none', 'error', 'turn/completed'):
                with self.subTest(supplied=supplied, prior=prior):
                    self.setUp()
                    if prior != 'none':
                        self.failure(prior)
                    rows_before = copy.deepcopy(self.c.child_capacity_failures)
                    data = dict(threadId='child', willRetry=False, error=dict(
                        codexErrorInfo='serverOverloaded', message='missing event identity'))
                    if supplied == 'empty':
                        data['turnId'] = ''
                    # A repeated unknown-identity event must never inherit a
                    # matching active turn or an earlier exact capacity record.
                    for _ in range(2):
                        self.c.event(dict(method='error', params=data))
                        self.assertTrue(self.c.stop_now)
                        self.assertEqual(self.c.stop_reason, 'server_error')
                        self.assertEqual(self.c.child_capacity_failures, rows_before)
                        self.assertEqual(self.c.state['last_failure']['id'],
                                         None if prior == 'turn/completed' else 'child-turn')
                        self.assertEqual(self.c.state['last_failure']['error']['message'],
                                         'missing event identity')
                    fatal = copy.deepcopy(self.c.state['last_failure'])
                    # A later exact failed completion may be scoped, but must
                    # preserve the fatal unknown-identity event and stop.
                    self.failure('turn/completed')
                    self.assertTrue(self.c.stop_now)
                    self.assertEqual(self.c.stop_reason, 'server_error')
                    self.assertEqual(self.c.state['last_failure'], fatal)
                    self.assertEqual(self.c.rpc.mock_calls, [])


if __name__ == '__main__':
    unittest.main(verbosity=2)
