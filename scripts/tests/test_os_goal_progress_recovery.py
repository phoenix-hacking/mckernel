"""Functional progress-policy recovery with temporary state and fake RPC only.

No live campaign, account, model, service, source payload or native operation.
"""
from copy import deepcopy
import json
from pathlib import Path
import shutil
import time
import unittest

from scripts.tests import test_os_goal_continuous_eligibility as controls
from scripts.tests import test_os_goal_reliability_integration as integration


class CadencePolicyTests(unittest.TestCase):
    def scenario(self):
        fixture = integration.ReliabilityIntegrationTests(methodName="runTest")
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        return fixture

    def overdue(self, fixture):
        campaign = fixture.campaign
        campaign.poll_progress()
        first = campaign.state["progress_review"]["key"]
        now = time.time()
        campaign.state["progress_monitor"]["issued_review_keys"][first] = now - 5200
        campaign.state["progress_review"]["delivered_at"] = now - 5000
        fixture.rpc.started("second-turn")
        fixture.poll_again()
        followup = campaign.state["progress_review"]["key"]
        campaign.state["progress_monitor"]["issued_review_keys"][followup] = now - 2600
        campaign.state["progress_monitor"]["last_semantic_at"] = now - 6000
        campaign.state["progress_review"]["delivered_at"] = now - 2500
        fixture.rpc.started("third-turn")

    def test_default_and_old_args_keep_overdue_same_root_running_without_rpc_or_payload_mutation(self):
        fixture = self.scenario()
        del fixture.fixture.args.stop_on_closure_stall  # A resident pre-upgrade Namespace remains compatible.
        self.overdue(fixture)
        campaign = fixture.campaign
        original_goal = deepcopy(campaign.goal)
        credit = {"id": "retained-finite-run", "budget": "100", "spent": "12"}
        hold = {"owner": "retained-native", "outcome": "UNKNOWN"}
        campaign.state.update(credit_budget=deepcopy(credit), native_hold=deepcopy(hold))
        before = list(fixture.rpc.calls)
        fixture.poll_again()
        fixture.poll_again()
        self.assertIsNone(campaign.stop_reason)
        self.assertFalse(campaign.stop_now)
        self.assertFalse(campaign.checkpoint_requested)
        self.assertEqual(campaign.active, {"test-thread": "third-turn"})
        self.assertEqual(campaign.goal, original_goal)
        self.assertEqual(fixture.rpc.calls, before)
        self.assertEqual(campaign.state["credit_budget"], credit)
        self.assertEqual(campaign.state["native_hold"], hold)
        self.assertEqual(len(campaign.state["progress_snapshot"]["closed_original_checks"]), fixture.closed_count)
        self.assertEqual(campaign.state["progress_snapshot"]["decision_status"], "overdue_advisory")
        self.assertFalse(campaign.state["progress_snapshot"]["stop_required"])
        self.assertEqual(campaign.state["progress_stall_advisory"]["status"], "advisory_only")

    def test_explicit_opt_in_still_latches_and_checkpoints_overdue_campaign(self):
        fixture = self.scenario()
        fixture.fixture.args.stop_on_closure_stall = True
        fixture.fixture.args.continuous = True
        self.overdue(fixture)
        fixture.poll_again()
        campaign = fixture.campaign
        self.assertEqual(campaign.stop_reason, "closure_decision_unresolved")
        self.assertFalse(campaign.state["controller_dispatch_enabled"])
        self.assertTrue(campaign.state["progress_snapshot"]["stop_required"])
        self.assertTrue(campaign.request_checkpoint())
        self.assertTrue(campaign.checkpoint_requested)
        self.assertEqual(campaign.goal["status"], "paused")
        self.assertEqual(campaign.state["thread_id"], "test-thread")
        self.assertFalse(any(method in {"thread/start", "thread/resume", "turn/start"}
                             for method, _ in fixture.rpc.calls))

    def test_parser_requires_explicit_cadence_stop_opt_in(self):
        self.assertFalse(integration.launcher.arguments([]).stop_on_closure_stall)
        self.assertTrue(integration.launcher.arguments(["--stop-on-closure-stall"]).stop_on_closure_stall)

    def test_advisory_policy_does_not_clear_existing_hard_stop_flags(self):
        fixture = self.scenario()
        self.overdue(fixture)
        for reason in ("credit_budget_exhausted", "machine_headroom_exhausted", "signal_15"):
            with self.subTest(reason=reason):
                fixture.campaign.stop_reason = reason
                fixture.campaign.stop_now = True
                fixture.campaign.checkpoint_requested = True
                fixture.campaign.save(stop_reason=reason)
                before = list(fixture.rpc.calls)
                fixture.poll_again()
                self.assertEqual(fixture.campaign.stop_reason, reason)
                self.assertTrue(fixture.campaign.stop_now)
                self.assertTrue(fixture.campaign.checkpoint_requested)
                self.assertEqual(fixture.rpc.calls, before)


class ExplicitProgressRecoveryTests(unittest.TestCase):
    def scenario(self, reason="closure_decision_unresolved"):
        fixture = controls.ContinuousEligibilityTests(methodName="runTest")
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        retention = fixture.retained_paused_owner()
        destination = fixture.directory / integration.progress.LEDGER_PATH
        destination.parent.mkdir(parents=True)
        shutil.copyfile(integration.launcher.REPO / integration.progress.LEDGER_PATH, destination)
        campaign = fixture.campaign
        now = time.time()
        observed = integration.progress.observe_progress(fixture.directory, campaign.state, now=now - 6000)
        first = observed["advisory_key"]
        campaign.state.update(progress_monitor=observed["monitor"],
            progress_review={"key": first, "status": "accepted_by_server", "delivered_at": now - 5900})
        observed = integration.progress.observe_progress(fixture.directory, campaign.state, now=now - 3000)
        followup = observed["advisory_key"]
        campaign.state.update(progress_monitor=observed["monitor"],
            progress_review={"key": followup, "status": "accepted_by_server", "delivered_at": now - 2900})
        observed = integration.progress.observe_progress(fixture.directory, campaign.state, now=now)
        self.assertTrue(observed["snapshot"]["stop_required"])
        campaign.state.update(progress_monitor=observed["monitor"], progress_snapshot=observed["snapshot"],
            progress_advisory={"key": followup, "status": "accepted_by_server"})
        campaign.stop_reason = reason
        campaign.stop_now = False
        campaign.checkpoint_requested = True
        campaign.save(stop_reason=reason)
        campaign.refresh_credit_budget(control_only=True)
        return fixture, retention

    def test_identity_bound_closure_resume_preserves_prior_window_and_rearms_new_reviews(self):
        fixture, retention = self.scenario()
        campaign = fixture.campaign
        campaign.args.stop_on_closure_stall = True  # Even opt-in must receive a new decision window.
        prior_monitor = deepcopy(campaign.state["progress_monitor"])
        prior_review = deepcopy(campaign.state["progress_review"])
        ledger = fixture.ledger()
        reviews = fixture.directory / "progress-reviews"
        reviews.mkdir()
        old_path = reviews / (prior_review["key"] + ".json")
        old_path.write_text(json.dumps(prior_review))
        original_bytes = old_path.read_bytes()
        ident = fixture.queue(source="explicit-user-closure-policy-recovery")
        item = json.loads((fixture.control / "pending" / (ident + ".json")).read_text())
        self.assertEqual(item["control"]["technical_checkpoint"], {
            "stop_reason": "closure_decision_unresolved", "stop_now": False, "checkpoint_requested": True})
        self.assertEqual(item["control"]["expected_owner"], fixture.owner())
        campaign.deliver_instruction(control_only=True)
        self.assertIsNone(campaign.stop_reason)
        self.assertFalse(campaign.stop_now)
        self.assertFalse(campaign.checkpoint_requested)
        self.assertEqual(campaign.goal["status"], "active")
        self.assertEqual(campaign.state["owner_retention"], retention)
        fixture.assert_holds_retained()
        for key in ("id", "budget", "spent", "minimum_balance", "remaining"):
            self.assertEqual(fixture.ledger()[key], ledger[key])
        receipt = campaign.state["last_instruction"]
        rearm = receipt["progress_decision_rearm"]
        self.assertEqual(rearm["prior_monitor"], prior_monitor)
        self.assertEqual(rearm["prior_review"], prior_review)
        self.assertFalse(rearm["canonical_evidence_reset"])
        self.assertFalse(rearm["financial_reset"])
        self.assertEqual(campaign.state["progress_review_epoch"], rearm["epoch"])
        self.assertEqual(campaign.state["progress_monitor"]["issued_review_keys"], {})
        self.assertEqual(campaign.state["progress_monitor"]["accepted_review_times"], {})
        for key in ("accepted_records", "earned_progress_keys", "known_closed_original_checks",
                    "last_semantic_at", "verified_closure_events", "velocity_started_at", "operation_deadlines"):
            self.assertEqual(campaign.state["progress_monitor"][key], prior_monitor[key])
        delivered = json.loads((fixture.control / "delivered" / (ident + ".json")).read_text())
        self.assertEqual(delivered["progress_decision_rearm"], rearm)
        campaign.save(phase="running", controller_dispatch_enabled=True)
        fixture.rpc.started("post-resume-root-turn")
        campaign.poll_progress()
        self.assertIsNone(campaign.stop_reason)
        self.assertFalse(campaign.state["progress_snapshot"]["stop_required"])
        self.assertEqual(campaign.goal["status"], "active")
        self.assertEqual(old_path.read_bytes(), original_bytes)
        self.assertTrue(list(reviews.glob(rearm["epoch"] + "-*.json")))
        self.assertFalse(any(method in {"thread/start", "thread/resume", "turn/start"}
                             for method, _ in fixture.rpc.calls))

    def test_idle_block_resume_requires_the_same_explicit_identity_bound_control(self):
        fixture, retention = self.scenario("blocked_no_ready_work")
        ident = fixture.queue(source="new-ready-work-explicit-idle-recovery")
        fixture.campaign.deliver_instruction(control_only=True)
        self.assertEqual(fixture.campaign.state["last_instruction"]["id"], ident)
        self.assertEqual(fixture.campaign.state["last_instruction"]["status"], "accepted_by_server")
        self.assertIsNone(fixture.campaign.stop_reason)
        self.assertEqual(fixture.campaign.state["owner_retention"], retention)
        fixture.assert_holds_retained()

    def test_older_ordinary_context_does_not_block_explicit_recovery_and_delivers_after_resume(self):
        fixture, retention = self.scenario()
        campaign = fixture.campaign
        ordinary = controls.launcher.queue_instruction(fixture.directory,
            "Current user explicitly authorizes this recovery and the next original proof.",
            source_id="current-user-context-before-recovery-control")
        ordinary_path = fixture.control / "pending" / (ordinary + ".json")
        original = ordinary_path.read_bytes()
        resume = fixture.queue(source="explicit-recovery-after-current-user-context")
        campaign.deliver_instruction(control_only=True)
        self.assertEqual(campaign.state["last_instruction"]["id"], resume)
        self.assertEqual(campaign.state["last_instruction"]["status"], "accepted_by_server")
        self.assertEqual(campaign.goal["status"], "active")
        self.assertEqual(ordinary_path.read_bytes(), original)
        self.assertEqual(campaign.state["owner_retention"], retention)
        fixture.assert_holds_retained()
        campaign.save(phase="running", controller_dispatch_enabled=True)
        fixture.rpc.started("resumed-root-turn")
        campaign.deliver_instruction()
        self.assertFalse(ordinary_path.exists())
        self.assertEqual(campaign.state["last_instruction"]["id"], ordinary)
        self.assertEqual(campaign.state["last_instruction"]["status"], "accepted_by_server")
        self.assertTrue(any(method == "turn/steer" and params["threadId"] == "test-thread"
                            for method, params in fixture.rpc.calls))
        self.assertFalse(any(method in {"thread/start", "thread/resume", "turn/start"}
                             for method, _ in fixture.rpc.calls))
        fixture.assert_holds_retained()

    def test_real_holds_and_user_stops_still_refuse_progress_recovery(self):
        fixture, _ = self.scenario()
        campaign = fixture.campaign
        for field in ("service_hold", "policy_hold", "auth_hold", "billing_hold", "accounting_unknown", "user_pause"):
            with self.subTest(field=field):
                self.assertFalse(controls.launcher.control_context_eligible(dict(campaign.state, **{field: True})))
        for reason in ("signal_15", "user_requested", "work_window", "machine_headroom_exhausted",
                       "credit_budget_unknown", "requested_milestones_complete"):
            with self.subTest(reason=reason):
                self.assertFalse(controls.launcher.control_context_eligible(dict(campaign.state, stop_reason=reason)))
        fixture.assert_holds_retained()

    def test_new_signal_before_activation_preserves_stop_and_old_decision_window(self):
        fixture, retention = self.scenario()
        prior = deepcopy(fixture.campaign.state["progress_monitor"])
        fixture.queue(source="closure-resume-before-new-user-signal")
        fixture.rpc.before["thread/goal/get"] = lambda: fixture.campaign.on_signal(15, None)
        fixture.campaign.deliver_instruction(control_only=True)
        self.assertEqual(fixture.campaign.stop_reason, "signal_15")
        self.assertTrue(fixture.campaign.checkpoint_requested)
        self.assertEqual(fixture.mutations(), [])
        self.assertNotIn("progress_review_epoch", fixture.campaign.state)
        self.assertEqual(fixture.campaign.state["progress_monitor"], prior)
        self.assertEqual(fixture.campaign.state["owner_retention"], retention)
        fixture.assert_holds_retained()

    def test_changed_original_server_identity_refuses_without_acknowledgement(self):
        fixture, _ = self.scenario()
        prior = deepcopy(fixture.campaign.state["progress_monitor"])
        fixture.queue(source="closure-resume-before-owner-identity-change")
        fixture.campaign.state["server_start"] = "another-server-birth"
        fixture.campaign.deliver_instruction(control_only=True)
        self.assertEqual(fixture.mutations(), [])
        self.assertEqual(fixture.campaign.stop_reason, "closure_decision_unresolved")
        self.assertTrue(fixture.campaign.checkpoint_requested)
        self.assertNotIn("progress_review_epoch", fixture.campaign.state)
        self.assertEqual(fixture.campaign.state["progress_monitor"], prior)
        fixture.assert_holds_retained()

    def test_actual_exhaustion_during_recovery_still_stops_before_goal_activation(self):
        fixture, _ = self.scenario()
        prior = deepcopy(fixture.campaign.state["progress_monitor"])
        fixture.queue(source="closure-resume-before-real-fake-credit-exhaustion")
        fixture.rpc.limits["credits"]["balance"] = "850"
        fixture.campaign.deliver_instruction(control_only=True)
        self.assertEqual(fixture.campaign.stop_reason, "credit_budget_exhausted")
        self.assertTrue(fixture.campaign.stop_now)
        self.assertEqual(fixture.mutations(), [])
        self.assertNotIn("progress_review_epoch", fixture.campaign.state)
        self.assertEqual(fixture.campaign.state["progress_monitor"], prior)
        self.assertEqual(fixture.ledger()["remaining"], "0")
        fixture.assert_holds_retained()


if __name__ == "__main__":
    unittest.main()
