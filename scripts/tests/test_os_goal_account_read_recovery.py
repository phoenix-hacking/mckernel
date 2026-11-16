"""Retained account-read transport recovery with fake RPC and temporary ledger.

Functional OS/Rust only; no live account/model/native operation or custody release.
"""
from copy import deepcopy
import json
import signal
import unittest
from unittest.mock import patch

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

    def active_scenario(self):
        fixture, retention = self.scenario()
        fixture.rpc.started("same-root-running-turn")
        fixture.campaign.refresh_credit_budget(control_only=True)
        self.assertEqual(fixture.campaign.stop_reason, "account_read_recovered")
        return fixture, retention

    def queue_active(self, fixture, source="explicit-user-active-primary-resume"):
        return fixtures.launcher.queue_same_owner_resume(fixture.directory,
            "Resume this same Root turn; preserve all held scopes.", source_id=source,
            allow_active_primary=True)

    def repeated_timeout_scenario(self):
        fixture, retention = self.scenario()
        fixture.campaign.refresh_credit_budget(control_only=True)
        self.assertEqual(fixture.campaign.stop_reason, "account_read_recovered")
        self.assertIsNone(fixture.campaign.state["credit_budget_error"])
        # Reproduce the observed resident latch: a second real fake-RPC read
        # fails while the recovered technical stop and paused flags remain.
        fixture.rpc.usage_error = fixtures.launcher.RecoverableFailure(TIMEOUT)
        with self.assertRaises(fixtures.launcher.RecoverableFailure) as caught:
            fixture.rpc.call("account/rateLimits/read", {})
        fixture.campaign.save(credit_budget_error=str(caught.exception),
            last_account_observation=dict(fixture.rpc.last_account_read_completion, status="REJECTED"))
        fixture.rpc.usage_error = None
        return fixture, retention

    def test_second_transport_timeout_recovers_again_without_automatic_resume(self):
        fixture, retention = self.repeated_timeout_scenario()
        campaign = fixture.campaign
        ledger = fixture.ledger()
        generation = campaign.primary_stop_generation
        failed_sequence = campaign.state["last_account_observation"]["sequence"]
        self.assertTrue(fixtures.launcher.account_read_retry_eligible(campaign.state))
        with self.assertRaisesRegex(ValueError, "fresh successful account observation"):
            fixture.queue(source="second-timeout-still-needs-fresh-account")
        campaign.refresh_credit_budget(control_only=True)
        self.assertEqual(campaign.stop_reason, "account_read_recovered")
        self.assertIsNone(campaign.state["credit_budget_error"])
        self.assertGreater(campaign.state["account_read_recovery"]["receive"]["sequence"], failed_sequence)
        self.assertEqual(campaign.state["last_account_control_observation"]["status"], "OBSERVED")
        self.assertTrue(campaign.stop_now and campaign.checkpoint_requested)
        self.assertEqual(campaign.primary_stop_generation, generation)
        self.assertEqual(campaign.goal["status"], "paused")
        self.assertEqual(campaign.state["owner_retention"], retention)
        for key in ("id", "budget", "spent", "minimum_balance", "remaining"):
            self.assertEqual(fixture.ledger()[key], ledger[key])
        self.assertEqual(fixture.mutations(), [])
        fixture.assert_holds_retained()

    def test_repeat_recovery_still_rejects_stale_foreign_and_failed_observations(self):
        for changed in ({"received_utc_ns": 1, "received_mono_ns": 1},
                        {"server_pid": 987654321}, {"response_error": True}):
            with self.subTest(changed=changed):
                fixture, retention = self.repeated_timeout_scenario()
                campaign = fixture.campaign
                ledger = campaign.credit_guard.path.read_bytes()
                prior_recovery = deepcopy(campaign.state["account_read_recovery"])
                context = self.fresh_context(fixture, **changed)
                with self.assertRaises(ValueError):
                    campaign.record_rate_limits(fixture.rpc.limits, read_completion=context)
                self.assertEqual(campaign.stop_reason, "account_read_recovered")
                self.assertEqual(campaign.state["credit_budget_error"], TIMEOUT)
                self.assertEqual(campaign.credit_guard.path.read_bytes(), ledger)
                self.assertEqual(campaign.state["account_read_recovery"], prior_recovery)
                self.assertTrue(campaign.stop_now and campaign.checkpoint_requested)
                self.assertEqual(campaign.goal["status"], "paused")
                self.assertEqual(campaign.state["owner_retention"], retention)
                self.assertEqual(fixture.mutations(), [])

    def test_repeat_timeout_does_not_relax_real_holds_or_malformed_accounting(self):
        fixture, _ = self.repeated_timeout_scenario()
        campaign = fixture.campaign
        ledger = campaign.credit_guard.path.read_bytes()
        for field in ("service_hold", "policy_hold", "auth_hold", "billing_hold", "accounting_unknown", "user_pause"):
            with self.subTest(field=field):
                campaign.save(**{field: True})
                before = list(fixture.rpc.calls)
                self.assertFalse(fixtures.launcher.account_read_retry_eligible(campaign.state))
                campaign.refresh_credit_budget(control_only=True)
                self.assertEqual(fixture.rpc.calls, before)
                self.assertEqual(campaign.state["credit_budget_error"], TIMEOUT)
                self.assertEqual(campaign.credit_guard.path.read_bytes(), ledger)
                campaign.state.pop(field)
                campaign.save()
        for reason in ("credit_budget_exhausted", "chatgpt_auth_changed", "signal_15", "work_window"):
            with self.subTest(reason=reason):
                self.assertFalse(fixtures.launcher.account_read_retry_eligible(dict(campaign.state, stop_reason=reason)))
        fixture.rpc.limits["credits"].pop("balance")
        campaign.refresh_credit_budget(control_only=True)
        self.assertEqual(campaign.stop_reason, "credit_budget_unknown")
        self.assertNotEqual(campaign.state["credit_budget_error"], TIMEOUT)
        self.assertFalse(fixtures.launcher.account_read_retry_eligible(campaign.state))
        self.assertEqual(campaign.credit_guard.path.read_bytes(), ledger)
        self.assertTrue(campaign.stop_now and campaign.checkpoint_requested)
        self.assertEqual(campaign.goal["status"], "paused")
        self.assertEqual(fixture.mutations(), [])
        fixture.assert_holds_retained()

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

    def test_explicit_active_primary_resume_reuses_exact_turn_and_keeps_ordinary_work_pending(self):
        fixture, retention = self.active_scenario()
        with self.assertRaisesRegex(ValueError, "exact idle blocked campaign"):
            fixture.queue(source="default-still-idle-only")
        ordinary = fixtures.launcher.queue_instruction(fixture.directory, "Execute the admitted original prerequisite")
        ordinary_path = fixture.control / "pending" / (ordinary + ".json")
        ordinary_bytes = ordinary_path.read_bytes()
        ident = self.queue_active(fixture)
        self.assertEqual(self.queue_active(fixture), ident)
        item = json.loads((fixture.control / "pending" / (ident + ".json")).read_text())
        self.assertTrue(item["resume_active_primary"])
        self.assertEqual(item["control"]["active_primary_turn_id"], "same-root-running-turn")
        self.assertEqual(item["control"]["expected_owner"], fixture.owner())
        fixture.campaign.deliver_instruction(control_only=True)
        self.assertEqual(fixture.campaign.goal["status"], "active")
        self.assertIsNone(fixture.campaign.stop_reason)
        self.assertFalse(fixture.campaign.stop_now)
        self.assertFalse(fixture.campaign.checkpoint_requested)
        self.assertEqual(fixture.campaign.active, {"test-thread": "same-root-running-turn"})
        self.assertEqual(fixture.rpc.turns["test-thread"]["id"], "same-root-running-turn")
        self.assertEqual(fixture.campaign.state["last_instruction"]["resumed_active_primary_turn_id"], "same-root-running-turn")
        self.assertEqual(ordinary_path.read_bytes(), ordinary_bytes)
        self.assertEqual(fixture.campaign.state["owner_retention"], retention)
        self.assertEqual(fixture.mutations(), [("thread/goal/set", {"threadId": "test-thread", "status": "active"})])
        fixture.assert_holds_retained()

    def test_active_primary_source_cannot_be_reinterpreted_as_idle_resume(self):
        fixture, _ = self.active_scenario()
        self.queue_active(fixture)
        with self.assertRaisesRegex(ValueError, "content changed"):
            fixtures.launcher.queue_same_owner_resume(fixture.directory,
                "Resume this same Root turn; preserve all held scopes.",
                source_id="explicit-user-active-primary-resume")
        self.assertEqual(fixture.mutations(), [])

    def test_active_primary_queue_refuses_any_child_activity(self):
        fixture, _ = self.active_scenario()
        fixture.rpc.started("existing-child-turn", "child")
        with self.assertRaisesRegex(ValueError, "exactly the existing original Root turn"):
            self.queue_active(fixture)
        self.assertEqual(fixture.mutations(), [])
        self.assertEqual(fixture.campaign.active, {"test-thread": "same-root-running-turn", "child": "existing-child-turn"})
        fixture.assert_holds_retained()

    def test_changed_primary_turn_leaves_original_control_unattempted(self):
        fixture, _ = self.active_scenario()
        ident = self.queue_active(fixture)
        path = fixture.control / "pending" / (ident + ".json")
        original = path.read_bytes()
        fixture.rpc.completed()
        fixture.rpc.started("different-root-turn")
        fixture.campaign.deliver_instruction(control_only=True)
        self.assertEqual(path.read_bytes(), original)
        self.assertEqual(fixture.mutations(), [])
        self.assertEqual(fixture.campaign.goal["status"], "paused")
        self.assertEqual(fixture.campaign.active, {"test-thread": "different-root-turn"})

    def test_child_started_during_account_check_refuses_active_primary_activation(self):
        fixture, _ = self.active_scenario()
        self.queue_active(fixture)
        fixture.rpc.after["account/rateLimits/read"] = lambda result: fixture.rpc.started("new-child-turn", "child")
        fixture.campaign.deliver_instruction(control_only=True)
        self.assertEqual(fixture.mutations(), [])
        self.assertEqual(fixture.campaign.state["last_instruction"]["status"], "same_owner_resume_refused")
        self.assertEqual(fixture.campaign.goal["status"], "paused")
        fixture.assert_holds_retained()

    def test_actual_turn_listing_must_confirm_only_the_bound_primary_turn(self):
        for running in (["unexpected-turn"], ["same-root-running-turn", "another-running-turn"]):
            with self.subTest(running=running):
                fixture, _ = self.active_scenario()
                self.queue_active(fixture)
                fixture.rpc.after["thread/turns/list"] = lambda result: result.update(
                    data=[{"id": ident, "status": "inProgress"} for ident in running])
                fixture.campaign.deliver_instruction(control_only=True)
                self.assertEqual(fixture.mutations(), [])
                self.assertEqual(fixture.campaign.state["last_instruction"]["status"], "same_owner_resume_refused")
                self.assertEqual(fixture.campaign.goal["status"], "paused")
                fixture.assert_holds_retained()

    def test_new_signal_and_genuine_account_exhaustion_still_veto_active_primary_resume(self):
        for failure in ("signal", "exhaustion", "service_hold"):
            with self.subTest(failure=failure):
                fixture, _ = self.active_scenario()
                self.queue_active(fixture)
                if failure == "signal":
                    fixture.rpc.before["thread/turns/list"] = lambda: fixture.campaign.on_signal(15, None)
                elif failure == "exhaustion":
                    fixture.rpc.limits["credits"]["balance"] = "850"
                else:
                    fixture.campaign.save(service_hold={"status": "actual hold"})
                fixture.campaign.deliver_instruction(control_only=True)
                self.assertEqual(fixture.mutations(), [])
                self.assertEqual(fixture.campaign.goal["status"], "paused")
                self.assertTrue(fixture.campaign.checkpoint_requested)
                fixture.assert_holds_retained()

    def test_primary_turn_drift_during_activation_compensates_by_pausing_same_goal(self):
        fixture, retention = self.active_scenario()
        self.queue_active(fixture)

        def drift(result):
            fixture.rpc.completed()
            fixture.rpc.started("unexpected-successor-turn")

        fixture.rpc.after["thread/goal/set"] = drift
        fixture.campaign.deliver_instruction(control_only=True)
        self.assertEqual(fixture.campaign.goal["status"], "paused")
        self.assertEqual(fixture.campaign.state["last_instruction"]["status"], "cancelled_after_stop")
        self.assertEqual(fixture.campaign.stop_reason, "account_read_recovered")
        self.assertTrue(fixture.campaign.stop_now)
        self.assertTrue(fixture.campaign.checkpoint_requested)
        self.assertEqual(fixture.campaign.active, {"test-thread": "unexpected-successor-turn"})
        self.assertEqual(fixture.campaign.state["owner_retention"], retention)
        self.assertEqual(fixture.mutations(), [
            ("thread/goal/set", {"threadId": "test-thread", "status": "active"}),
            ("thread/goal/set", {"threadId": "test-thread", "status": "paused"})])
        fixture.assert_holds_retained()

    def test_cli_active_primary_mode_requires_explicit_resume_and_source(self):
        self.assertFalse(fixtures.launcher.arguments([]).resume_active_primary)
        args = fixtures.launcher.arguments(["--resume-same-owner", "Resume the same active Root", "--resume-active-primary",
                                           "--instruction-source-id", "explicit-active-primary-source"])
        self.assertTrue(args.resume_active_primary)
        with patch("sys.stderr"), self.assertRaises(SystemExit):
            fixtures.launcher.arguments(["--resume-active-primary"])


if __name__ == "__main__":
    unittest.main()
