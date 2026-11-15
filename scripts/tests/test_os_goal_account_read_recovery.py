"""Retained account-read transport recovery with fake RPC and temporary ledger.

Functional OS/Rust only; no live account/model/native operation or custody release.
"""
from copy import deepcopy
import json
import signal
import unittest

from scripts.tests import test_os_goal_continuous_eligibility as fixtures


TIMEOUT = "App-server request timed out: account/rateLimits/read"


class RetainedAccountReadRecoveryTests(unittest.TestCase):
    def scenario(self):
        fixture = fixtures.ContinuousEligibilityTests(methodName="runTest")
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        retention = fixture.retained_paused_owner()
        campaign = fixture.campaign
        campaign.stop_reason = "credit_budget_unknown"
        campaign.stop_now = True
        campaign.checkpoint_requested = True
        campaign.save(stop_reason=campaign.stop_reason, credit_budget_error=TIMEOUT)
        return fixture, retention

    def fresh_context(self, fixture, **changes):
        context = fixture.rpc.context(fixture.rpc.limits)
        context.update(changes)
        fixture.rpc.last_account_read_completion = context
        return context

    def test_transport_context_allows_only_reads_until_fresh_data_and_idle_explicit_resume(self):
        fixture, retention = self.scenario()
        campaign = fixture.campaign
        before_ledger = fixture.ledger()
        self.assertTrue(fixtures.launcher.control_context_eligible(campaign.state))
        with self.assertRaisesRegex(ValueError, "fresh successful account observation"):
            fixture.queue(source="before-real-account-refresh")
        ordinary = fixtures.launcher.queue_instruction(fixture.directory, "Continue the admitted prerequisite")
        path = fixture.control / "pending" / (ordinary + ".json")
        original = path.read_bytes()
        campaign.deliver_instruction(control_only=True)
        self.assertEqual(path.read_bytes(), original)
        self.assertEqual(fixture.mutations(), [])
        fixture.rpc.started("existing-draining-root-turn")
        campaign.refresh_credit_budget(control_only=True)
        self.assertEqual(campaign.stop_reason, "account_read_recovered")
        self.assertTrue(campaign.stop_now)
        self.assertTrue(campaign.checkpoint_requested)
        self.assertEqual(campaign.goal["status"], "paused")
        self.assertEqual(campaign.state["owner_retention"], retention)
        self.assertIsNone(campaign.state["credit_budget_error"])
        self.assertEqual(campaign.state["last_account_control_observation"]["status"], "OBSERVED")
        self.assertEqual(campaign.state["account_read_recovery"]["prior_error"], TIMEOUT)
        self.assertFalse(campaign.state["account_read_recovery"]["execution_admission"])
        self.assertFalse(campaign.state["account_read_recovery"]["hold_release"])
        for key in ("id", "budget", "spent", "minimum_balance", "remaining"):
            self.assertEqual(fixture.ledger()[key], before_ledger[key])
        with self.assertRaisesRegex(ValueError, "exact idle blocked campaign"):
            fixture.queue(source="still-active-original-root")
        fixture.rpc.completed()
        ident = fixture.queue(source="explicit-user-resume-after-real-account-refresh")
        item = json.loads((fixture.control / "pending" / (ident + ".json")).read_text())
        self.assertEqual(item["control"]["technical_checkpoint"], {
            "stop_reason": "account_read_recovered", "stop_now": True, "checkpoint_requested": True})
        campaign.deliver_instruction(control_only=True)
        self.assertIsNone(campaign.stop_reason)
        self.assertFalse(campaign.stop_now)
        self.assertFalse(campaign.checkpoint_requested)
        self.assertEqual(campaign.goal["status"], "active")
        self.assertEqual(fixture.mutations(), [("thread/goal/set", {"threadId": "test-thread", "status": "active"})])
        fixture.assert_holds_retained()

    def test_genuinely_new_same_server_notification_recovers_without_model_or_goal_mutation(self):
        fixture, retention = self.scenario()
        fixture.rpc.last_account_notification = fixture.rpc.context(fixture.rpc.limits, source="notification")
        fixture.rpc.last_account_notification.pop("response_error")  # Actual RPC notification shape.
        fixture.rpc.emit("account/rateLimits/updated", {"rateLimits": deepcopy(fixture.rpc.limits)})
        self.assertEqual(fixture.campaign.stop_reason, "account_read_recovered")
        self.assertTrue(fixture.campaign.stop_now)
        self.assertTrue(fixture.campaign.checkpoint_requested)
        self.assertEqual(fixture.campaign.goal["status"], "paused")
        self.assertEqual(fixture.campaign.state["last_account_control_observation"]["status"], "OBSERVED")
        self.assertEqual(fixture.campaign.state["owner_retention"], retention)
        self.assertEqual(fixture.mutations(), [])
        fixture.assert_holds_retained()

    def test_cached_read_completion_cannot_be_relabelled_fresh(self):
        fixture, _ = self.scenario()
        original = fixture.campaign.credit_guard.path.read_bytes()
        with self.assertRaisesRegex(ValueError, "new fresh successful receive"):
            fixture.campaign.record_rate_limits(fixture.rpc.limits,
                read_completion=fixture.rpc.last_account_read_completion)
        self.assertEqual(fixture.campaign.stop_reason, "credit_budget_unknown")
        self.assertEqual(fixture.campaign.state["credit_budget_error"], TIMEOUT)
        self.assertEqual(fixture.campaign.credit_guard.path.read_bytes(), original)
        self.assertNotIn("account_read_recovery", fixture.campaign.state)

    def test_stale_or_foreign_or_failed_receive_cannot_recover_or_change_ledger(self):
        for change in ({"received_utc_ns": 1, "received_mono_ns": 1},
                       {"server_pid": 987654321}, {"response_error": True}):
            with self.subTest(change=change):
                fixture, _ = self.scenario()
                original = fixture.campaign.credit_guard.path.read_bytes()
                context = self.fresh_context(fixture, **change)
                with self.assertRaises(ValueError):
                    fixture.campaign.record_rate_limits(fixture.rpc.limits, read_completion=context)
                self.assertEqual(fixture.campaign.stop_reason, "credit_budget_unknown")
                self.assertEqual(fixture.campaign.state["credit_budget_error"], TIMEOUT)
                self.assertEqual(fixture.campaign.credit_guard.path.read_bytes(), original)
                self.assertNotIn("account_read_recovery", fixture.campaign.state)

    def test_unknown_accounting_auth_errors_and_real_holds_do_not_enable_read_retry(self):
        fixture, _ = self.scenario()
        for error in ("missing balance", "original finite accounting unresolved", "account/rateLimits/read: auth denied"):
            with self.subTest(error=error):
                state = dict(fixture.campaign.state, credit_budget_error=error)
                self.assertFalse(fixtures.launcher.account_read_retry_eligible(state))
                self.assertFalse(fixtures.launcher.control_context_eligible(state))
        for field in ("service_hold", "policy_hold", "auth_hold", "billing_hold", "permission_hold",
                      "account_hold", "accounting_unknown", "credit_budget_unknown", "user_pause"):
            with self.subTest(field=field):
                self.assertFalse(fixtures.launcher.account_read_retry_eligible(dict(fixture.campaign.state, **{field: True})))
        for reason in ("credit_budget_exhausted", "chatgpt_auth_changed", "signal_15", "work_window"):
            with self.subTest(reason=reason):
                self.assertFalse(fixtures.launcher.account_read_retry_eligible(dict(fixture.campaign.state, stop_reason=reason)))

    def test_real_hold_prevents_refresh_and_notification_does_not_clear_it(self):
        fixture, retention = self.scenario()
        fixture.campaign.save(service_hold={"reason": "actual service hold"})
        before = list(fixture.rpc.calls)
        ledger = fixture.campaign.credit_guard.path.read_bytes()
        fixture.campaign.refresh_credit_budget(control_only=True)
        self.assertEqual(fixture.rpc.calls, before)
        fixture.rpc.last_account_notification = fixture.rpc.context(fixture.rpc.limits, source="notification")
        fixture.rpc.emit("account/rateLimits/updated", {"rateLimits": fixture.rpc.limits})
        self.assertEqual(fixture.campaign.stop_reason, "credit_budget_unknown")
        self.assertEqual(fixture.campaign.state["credit_budget_error"], TIMEOUT)
        self.assertEqual(fixture.campaign.credit_guard.path.read_bytes(), ledger)
        self.assertEqual(fixture.campaign.state["owner_retention"], retention)
        self.assertEqual(fixture.campaign.state["service_hold"], {"reason": "actual service hold"})
        self.assertEqual(fixture.mutations(), [])

    def test_fresh_data_with_missing_balance_is_a_real_unknown_not_transport_recovery(self):
        fixture, _ = self.scenario()
        ledger = fixture.campaign.credit_guard.path.read_bytes()
        fixture.rpc.limits["credits"].pop("balance")
        fixture.campaign.refresh_credit_budget(control_only=True)
        self.assertEqual(fixture.campaign.stop_reason, "credit_budget_unknown")
        self.assertNotEqual(fixture.campaign.state["credit_budget_error"], TIMEOUT)
        self.assertFalse(fixtures.launcher.account_read_retry_eligible(fixture.campaign.state))
        self.assertEqual(fixture.campaign.credit_guard.path.read_bytes(), ledger)
        self.assertNotIn("account_read_recovery", fixture.campaign.state)
        self.assertEqual(fixture.mutations(), [])

    def test_genuine_fresh_exhaustion_stays_exhausted_and_cumulative(self):
        fixture, retention = self.scenario()
        fixture.rpc.limits["credits"]["balance"] = "850"
        fixture.campaign.refresh_credit_budget(control_only=True)
        self.assertEqual(fixture.campaign.stop_reason, "credit_budget_exhausted")
        self.assertTrue(fixture.campaign.stop_now)
        self.assertTrue(fixture.campaign.checkpoint_requested)
        self.assertEqual(fixture.ledger()["remaining"], "0")
        self.assertEqual(fixture.ledger()["spent"], "150")
        self.assertEqual(fixture.campaign.state["owner_retention"], retention)
        self.assertNotIn("account_read_recovery", fixture.campaign.state)
        self.assertEqual(fixture.mutations(), [])
        fixture.assert_holds_retained()

    def test_changed_ledger_ceiling_refuses_before_accounting(self):
        fixture, _ = self.scenario()
        original = fixture.campaign.credit_guard.path.read_bytes()
        fixture.campaign.state["credit_budget"]["budget"] = "101"
        context = self.fresh_context(fixture)
        with self.assertRaisesRegex(ValueError, "original owner/finite ledger differs"):
            fixture.campaign.record_rate_limits(fixture.rpc.limits, read_completion=context)
        self.assertEqual(fixture.campaign.credit_guard.path.read_bytes(), original)
        self.assertEqual(fixture.campaign.stop_reason, "credit_budget_unknown")
        self.assertNotIn("account_read_recovery", fixture.campaign.state)

    def test_new_signal_during_read_wins_without_recovery_or_activation(self):
        fixture, retention = self.scenario()
        fixture.rpc.after["account/rateLimits/read"] = lambda result: fixture.campaign.on_signal(int(signal.SIGTERM), None)
        fixture.campaign.refresh_credit_budget(control_only=True)
        self.assertEqual(fixture.campaign.stop_reason, "signal_15")
        self.assertTrue(fixture.campaign.checkpoint_requested)
        self.assertNotIn("account_read_recovery", fixture.campaign.state)
        self.assertEqual(fixture.campaign.state["owner_retention"], retention)
        self.assertEqual(fixture.mutations(), [])
        fixture.assert_holds_retained()


if __name__ == "__main__":
    unittest.main()
