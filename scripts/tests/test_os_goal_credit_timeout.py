"""Functional OS launcher accounting only; no inference or production state access."""
import importlib.util
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch
from test_os_goal_transport import usage_error

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
SOURCE = (Path(__file__).resolve().parents[1] / 'run_os_goal.py')
spec = importlib.util.spec_from_file_location('credit_timeout_candidate', SOURCE)
launcher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(launcher)


def limits(balance='1000'):
    return {'primary': {'usedPercent': 46}, 'credits': {
        'hasCredits': True, 'unlimited': False, 'balance': balance}}


class CreditTimeout(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        args = launcher.arguments(['--hours', '0', '--agent-windows', 'off',
                                   '--credit-budget', '100', '--credit-run-id', 'a' * 32])
        self.c = launcher.Campaign(args, self.root, self.root)
        self.addCleanup(self.c.output.close)
        self.c.rpc = Mock()
        self.c.rpc.last_account_read_completion = None
        self.c.rpc.last_account_notification = None

    def notification(self, value=None, now=100):
        with patch.object(launcher.time, 'monotonic', return_value=now):
            self.c.event({'method': 'account/rateLimits/updated',
                          'params': {'rateLimits': limits() if value is None else value}})

    def refresh(self, now=110, error=None):
        self.c.rpc.call.side_effect = error or launcher.RecoverableFailure(
            'App-server request timed out: account/rateLimits/read')
        with patch.object(launcher.time, 'monotonic', return_value=now), patch.object(launcher.time, 'sleep'):
            self.c.refresh_credit_budget()

    def test_notification_during_rpc_timeout_preserves_guard_and_spending(self):
        self.c.record_rate_limits(limits())
        def call(*args, **kwargs):
            self.notification(limits('950'))
            raise launcher.RecoverableFailure(
                'App-server request timed out: account/rateLimits/read')
        self.c.rpc.call.side_effect = call
        with patch.object(launcher.time, 'monotonic', return_value=110):
            self.c.refresh_credit_budget()
        self.assertIsNone(self.c.stop_reason)
        self.assertFalse(self.c.stop_now)
        saved = json.loads(self.c.credit_guard.path.read_text())
        self.assertEqual((saved['id'], saved['spent'], saved['remaining']), ('a' * 32, '50', '50'))
        self.assertEqual(self.c.state['last_usage_read_notification_fallback']['age_seconds'], 10)

    def test_missing_or_stale_or_monotonic_rollback_stops(self):
        for observed in [None, (self.c.rpc, 94), (self.c.rpc, 111)]:
            with self.subTest(observed=observed):
                self.c.last_credit_notification = observed
                self.c.stop_reason, self.c.stop_now = None, False
                self.refresh()
                self.assertEqual(self.c.stop_reason, 'credit_budget_unknown')

    def test_successful_poll_or_saved_state_is_not_notification_freshness(self):
        self.c.record_rate_limits(limits())
        self.assertIsNone(self.c.last_credit_notification)
        self.c.state['last_credit_notification'] = 110
        self.refresh()
        self.assertEqual(self.c.stop_reason, 'credit_budget_unknown')

    def test_new_rpc_cannot_reuse_previous_server_notification(self):
        self.notification()
        self.c.rpc = Mock()
        self.refresh()
        self.assertEqual(self.c.stop_reason, 'credit_budget_unknown')

    def test_invalid_notification_and_persistence_error_cannot_grant_freshness(self):
        self.notification()
        self.notification({'primary': {'usedPercent': 'unknown'}})
        self.assertIsNone(self.c.last_credit_notification)
        self.assertEqual(self.c.stop_reason, 'included_usage_unknown')
        self.c.stop_reason, self.c.stop_now = None, False
        with patch.object(self.c.credit_guard, 'observe', side_effect=OSError('write failed')):
            self.notification()
        self.refresh()
        self.assertEqual(self.c.stop_reason, 'credit_budget_unknown')
        self.assertIsNone(self.c.last_credit_notification)

    def test_exhaustion_and_explicit_holds_win(self):
        for reason in ['policy_hold', 'chatgpt_auth_changed', 'quota_exhausted', 'signal_2']:
            self.c.stop_reason, self.c.stop_now = None, False
            self.notification()
            def call(*args, **kwargs):
                self.c.stop_reason, self.c.stop_now = reason, True
                raise launcher.RecoverableFailure(
                    'App-server request timed out: account/rateLimits/read')
            self.c.rpc.call.side_effect = call
            with patch.object(launcher.time, 'monotonic', return_value=110):
                self.c.refresh_credit_budget()
            self.assertEqual(self.c.stop_reason, reason)
        self.c.stop_reason, self.c.stop_now = None, False
        self.notification()
        self.notification(limits('900'))
        self.refresh()
        self.assertEqual(self.c.stop_reason, 'credit_budget_exhausted')

    def test_non_timeout_transport_auth_billing_and_guard_errors_are_not_hidden(self):
        for error in [RuntimeError('401 Unauthorized'), RuntimeError('billing hold'),
                      ValueError('corrupt guard'), TimeoutError('account unavailable')]:
            with self.subTest(error=error):
                self.c.stop_reason, self.c.stop_now = None, False
                self.notification()
                self.refresh(error=error)
                self.assertEqual(self.c.stop_reason, 'credit_budget_unknown')

    def test_next_poll_fails_after_notification_age_bound(self):
        self.notification()
        self.refresh(now=115)
        self.assertIsNone(self.c.stop_reason)
        self.refresh(now=115.001)
        self.assertEqual(self.c.stop_reason, 'credit_budget_unknown')

    def test_502_retries_only_read_then_validates_persistent_guard(self):
        self.c.record_rate_limits(limits())
        self.c.rpc.call.side_effect = [RuntimeError(usage_error()), {'rateLimits': limits('950')}]
        with patch.object(launcher.time, 'sleep') as sleep:
            self.c.refresh_credit_budget()
        sleep.assert_called_once_with(1)
        self.assertEqual(self.c.rpc.call.call_count, 2)
        self.assertIsNone(self.c.stop_reason)
        saved = json.loads(self.c.credit_guard.path.read_text())
        self.assertEqual((saved['spent'], saved['remaining'], saved['id']), ('50', '50', 'a' * 32))
        for call in self.c.rpc.call.call_args_list:
            self.assertEqual(call.args, ('account/rateLimits/read', {}))

    def test_gateway_failure_fresh_notification_and_stale_data_paths(self):
        for error in [RuntimeError(usage_error(500)), RuntimeError(usage_error(502)),
                      RuntimeError(usage_error(503)), RuntimeError(usage_error(504)),
                      BrokenPipeError('peer closed'), ConnectionResetError('peer reset')]:
            with self.subTest(error=error):
                self.c.stop_reason, self.c.stop_now = None, False
                self.notification()
                self.refresh(error=error)
                self.assertIsNone(self.c.stop_reason)
        self.c.last_credit_notification = (self.c.rpc, 90)
        self.refresh(error=RuntimeError(usage_error()))
        self.assertEqual(self.c.stop_reason, 'credit_budget_unknown')

    def test_true_guard_write_failure_during_rpc_is_not_normalized_or_overwritten(self):
        def call(*args, **kwargs):
            with patch.object(self.c.credit_guard, 'observe', side_effect=BrokenPipeError('guard write failed')):
                self.notification()
            raise RuntimeError(usage_error())
        self.c.rpc.call.side_effect = call
        self.c.refresh_credit_budget()
        self.assertEqual(self.c.state['credit_budget_error'], 'guard write failed')
        self.assertNotIn('last_usage_read_notification_fallback', self.c.state)
        self.assertNotIn('last_usage_transport_error', self.c.state)

    def test_gateway_owns_pause_and_startup_receipts_with_same_legacy_keys(self):
        before = {'threadId': 'saved', 'status': 'active', 'updatedAt': 1, 'objective': launcher.OBJECTIVE}
        after = dict(before, status='paused', updatedAt=2)
        self.c.state.update(thread_id='saved', worker_pid=os.getpid(), worker_start='123',
                            credit_budget_error=usage_error())
        self.c.controlled, self.c.stopping, self.c.stop_now = True, True, True
        self.c.stop_reason = 'credit_budget_unknown'
        self.c.rpc.call.side_effect = [{'goal': before}, {'goal': after}]
        self.c.pause()
        receipt = self.c.state['credit_timeout_shutdown_pause']
        self.assertEqual(receipt['credit_budget_error'], usage_error())
        self.assertEqual(receipt['goal_after'], after)
        self.c.controlled, self.c.stopping, self.c.stop_now = False, False, False
        self.c.stop_reason = None
        self.c.args.credit_timeout_goal_sha256 = receipt['goal_after_sha256']
        self.c.state.update(phase='starting', auth_mode='chatgpt')
        self.refresh(error=RuntimeError(usage_error()))
        self.assertTrue(self.c.state['credit_timeout_startup']['before_inference'])
        self.assertEqual(self.c.state['credit_timeout_startup']['expected_goal_sha256'], receipt['goal_after_sha256'])

    def test_generic_recovery_usage_failure_emits_only_read_only_startup_marker(self):
        self.c.args.recovery_require_active = True
        self.c.state.update(thread_id='saved', worker_pid=os.getpid(), worker_start='123',
                            phase='starting', auth_mode='chatgpt', goal={'status': 'active'})
        self.refresh(error=RuntimeError(usage_error()))
        marker = self.c.state['transport_startup']
        self.assertTrue(marker['before_inference'])
        self.assertTrue(marker['require_active'])
        self.assertEqual((marker['class'], marker['method']), ('http_502', 'account/rateLimits/read'))
        self.assertEqual(self.c.stop_reason, 'credit_budget_unknown')


if __name__ == '__main__':
    unittest.main()
