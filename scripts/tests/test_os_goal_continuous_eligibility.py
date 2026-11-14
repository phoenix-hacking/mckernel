#!/usr/bin/env python3
"""Offline functional harness control: FakeRPC and temporary state only.

No inference, service connection, payload, real campaign edit or hold release.
"""

import copy
import json
import os
from pathlib import Path
from types import SimpleNamespace
import tempfile
import time
import unittest
from unittest.mock import patch

from scripts.tests.test_os_goal_launcher import FakeRPC, goal, launcher
from os_goal_custody import make_retention_record
from os_goal_guard_protocol import process_start


class ObservedRPC(FakeRPC):
    """Attribute fake receive events to this offline test's existing process."""

    def __init__(self, args, live_goal):
        super().__init__(args, live_goal)
        self.proc = SimpleNamespace(pid=os.getpid())
        self.last_account_read_completion = None
        self.last_account_notification = None
        self.sequence = 0
        self.before = {}
        self.after = {}
        self.usage_error = None
        self.limits = {"primary": {"usedPercent": 99, "windowDurationMins": 10080},
                       "credits": {"hasCredits": True, "unlimited": False, "balance": "1000"}}

    def context(self, limits, *, source="read", response_error=False):
        self.sequence += 1
        return {"schema_version": 1, "source": source,
                "method": "account/rateLimits/read" if source == "read" else "account/rateLimits/updated",
                "request_id": self.sequence if source == "read" else None,
                "received_utc_ns": time.time_ns(), "received_mono_ns": time.monotonic_ns(),
                "sequence": self.sequence, "server_pid": self.proc.pid,
                "rate_limits_sha256": launcher._account_value_sha256(limits),
                "response_error": response_error}

    def call(self, method, params, **kwargs):
        before = self.before.pop(method, None)
        if before is not None:
            before()
        if method == "account/rateLimits/read" and self.usage_error is not None:
            self.calls.append((method, params))
            self.last_account_read_completion = self.context(None, response_error=True)
            raise self.usage_error
        result = super().call(method, params, **kwargs)
        if method == "account/rateLimits/read":
            self.last_account_read_completion = self.context(result["rateLimits"])
        after = self.after.pop(method, None)
        if after is not None:
            after(result)
        return result


class ContinuousEligibilityTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="os-goal-eligibility-")
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name)
        self.args = launcher.arguments(["--hours", "0", "--agent-windows", "off",
            "--same-owner-control", "--credit-budget", "100", "--credit-run-id", "a" * 32])
        self.campaign = launcher.Campaign(self.args, self.directory, self.directory)
        self.addCleanup(self.campaign.output.close)
        self.rpc = ObservedRPC(self.args, goal("blocked"))
        self.rpc.on_event = self.campaign.event
        self.campaign.rpc = self.rpc
        self.campaign.controlled = True
        self.campaign.goal = copy.deepcopy(self.rpc.goal)
        self.holds = {"source_hold": {"scope": "original-source", "outcome": "UNKNOWN"},
                      "native_hold": {"owner": "original-native", "bytes": 12 * 1024 ** 3},
                      "resource_hold": {"owner": "original-host", "bytes": 2415919104, "jobs": 2},
                      "logical_lease": {"owner": "original-runtime", "outcome": "UNKNOWN"}}
        self.campaign.save(thread_id="test-thread", phase="waiting_for_input", auth_mode="chatgpt",
            goal=self.campaign.goal, worker_pid=os.getpid(), worker_start=process_start(os.getpid()),
            server_pid=os.getpid(), server_start=process_start(os.getpid()), **copy.deepcopy(self.holds))
        self.campaign.refresh_credit_budget()
        self.control = self.directory / "instructions"

    def queue(self, source="explicit-user-source-1", text="Resume this same blocked owner; retain all holds."):
        return launcher.queue_same_owner_resume(self.directory, text, source_id=source)

    def ledger(self):
        return json.loads(self.campaign.credit_guard.path.read_text())

    def owner(self):
        return launcher._account_control_owner(self.campaign.state, self.directory, self.directory)

    def observed(self, **overrides):
        state = dict(self.campaign.state, **overrides)
        return launcher.observed_account_control(state, self.ledger(), self.owner(),
                                                 time.time_ns(), time.monotonic_ns())

    def mutations(self):
        return [(method, params) for method, params in self.rpc.calls
                if method not in {"account/read", "account/rateLimits/read", "thread/goal/get", "thread/turns/list"}]

    def assert_holds_retained(self):
        for key, value in self.holds.items():
            self.assertEqual(self.campaign.state[key], value)
        self.assertEqual(self.ledger()["id"], "a" * 32)
        self.assertEqual(self.ledger()["budget"], "100")

    def retained_paused_owner(self):
        """Prepare a technically paused owner, without any explicit user stop."""
        self.args.continuous = True
        self.args.retain_owner_on_stop = True
        self.rpc.goal = goal("paused")
        self.campaign.goal = copy.deepcopy(self.rpc.goal)
        self.campaign.save(phase="owner_retained", goal=self.campaign.goal,
                           continuous=True, stop_reason=None, user_paused=False)
        retention = make_retention_record(self.campaign.state, watcher_pid=os.getppid(),
            watcher_start=process_start(os.getppid()), reason="watchdog_recovery")
        self.campaign.save(owner_retention=retention)
        # Exercise the real observation producer for this phase. Rewriting an
        # old execution receipt or pretending the goal is active is forbidden.
        self.campaign.refresh_credit_budget()
        return copy.deepcopy(retention)

    def technical_checkpoint(self):
        retention = self.retained_paused_owner()
        self.campaign.stop_reason = "watchdog_recovery"
        self.campaign.stop_now = True
        self.campaign.checkpoint_requested = True
        self.campaign.save(stop_reason=self.campaign.stop_reason)
        self.campaign.refresh_credit_budget(control_only=True)
        return retention, {"stop_reason": "watchdog_recovery", "stop_now": True,
                           "checkpoint_requested": True}

    def test_blocked_fresh_control_observation_is_not_execution_accepted(self):
        observed = self.observed()
        self.assertEqual(observed["status"], "OBSERVED")
        self.assertEqual(observed["context"], "same_owner_control")
        self.assertIs(observed["execution_authorized"], False)
        self.assertEqual(self.campaign.state["last_account_observation"]["status"], "PENDING")
        with self.assertRaises(ValueError):
            launcher.accepted_account_observation(self.campaign.state, self.ledger(), self.owner(),
                                                  time.time_ns(), time.monotonic_ns())
        self.assertEqual(self.mutations(), [])
        self.assert_holds_retained()

    def test_new_opt_in_does_not_change_the_active_execution_receipt_contract(self):
        self.campaign.goal = goal()
        self.rpc.goal = goal()
        self.campaign.save(phase="running", goal=self.campaign.goal)
        self.campaign.refresh_credit_budget()
        accepted = launcher.accepted_account_observation(self.campaign.state, self.ledger(), self.owner(),
                                                          time.time_ns(), time.monotonic_ns())
        self.assertEqual(accepted["status"], "ACCEPTED")
        self.assertEqual(self.observed()["status"], "OBSERVED")
        self.assert_holds_retained()

    def test_old_producer_contract_stays_pending_without_opt_in(self):
        self.args.same_owner_control = False
        self.campaign.state.pop("last_account_control_observation")
        self.campaign.state.pop("same_owner_control_capability")
        self.campaign.refresh_credit_budget()
        self.assertEqual(self.campaign.state["last_account_observation"]["status"], "PENDING")
        self.assertNotIn("last_account_control_observation", self.campaign.state)
        self.assertEqual(self.mutations(), [])

    def test_controller_capability_absence_refuses_without_queueing_user_text(self):
        self.campaign.state.pop("same_owner_control_capability")
        launcher.atomic_json(self.campaign.state_path, self.campaign.state)
        with self.assertRaisesRegex(ValueError, "does not advertise.*capability"):
            self.queue()
        self.assertEqual(list((self.control / "pending").glob("*.json")), [])
        self.assertEqual(self.mutations(), [])

    def test_legacy_registration_guard_refuses_the_control_envelope_before_steer(self):
        ident = self.queue()
        item = json.loads((self.control / "pending" / (ident + ".json")).read_text())
        # This is the unchanged legacy envelope validator, not the new control
        # handler. A downgraded controller cannot interpret resume as plain text.
        with self.assertRaisesRegex(ValueError, "capture registration refused"):
            self.campaign.register_instruction_capture_progress(item, {})
        self.assertEqual(self.mutations(), [])

    def test_typed_resume_only_changes_goal_context_and_retains_original_holds(self):
        ident = self.queue()
        original_ledger = self.ledger()
        self.campaign.deliver_instruction()
        self.assertEqual(self.mutations(), [("thread/goal/set", {"threadId": "test-thread", "status": "active"})])
        self.assertEqual(self.campaign.goal["status"], "active")
        receipt = json.loads((self.control / "delivered" / (ident + ".json")).read_text())
        self.assertEqual(receipt["status"], "accepted_by_server")
        self.assertIs(receipt["execution_admission"], False)
        self.assertIs(receipt["hold_release"], False)
        self.assertEqual(self.ledger(), original_ledger)
        self.assertEqual(self.campaign.state["last_account_observation"]["status"], "PENDING")
        self.assert_holds_retained()

    def test_source_dedup_preserves_original_binding_after_successful_activation(self):
        ident = self.queue()
        source = self.control / "sources" / (ident[len("source-"):] + ".json")
        original_source = source.read_bytes()
        self.campaign.deliver_instruction()
        receipt = self.control / "delivered" / (ident + ".json")
        original_receipt = receipt.read_bytes()
        self.assertEqual(self.queue(), ident)
        self.assertEqual(source.read_bytes(), original_source)
        self.assertEqual(receipt.read_bytes(), original_receipt)
        self.assertEqual(list((self.control / "pending").glob("*.json")), [])
        with self.assertRaisesRegex(ValueError, "content changed"):
            self.queue(text="Different authorization under the same source")
        with self.assertRaisesRegex(ValueError, "content changed"):
            launcher.queue_instruction(self.directory, "Resume this same blocked owner; retain all holds.",
                                       source_id="explicit-user-source-1")
        self.assertEqual(len(self.mutations()), 1)

    def test_large_typed_control_registry_uses_unlimited_instruction_reader_and_deduplicates(self):
        text = 'Resume this SAME owner while preserving every hold.\n' + 'x' * (4 * 1024 * 1024 + 1)
        ident = self.queue(source='large-explicit-control-source', text=text)
        registry = self.control / 'sources' / (ident[len('source-'):] + '.json')
        original = registry.read_bytes()
        self.assertGreater(len(original), 4 * 1024 * 1024)
        self.assertEqual(launcher._read_private_json(registry)['item']['text'], text)
        self.campaign.deliver_instruction()
        self.assertEqual(self.campaign.state['last_instruction']['status'], 'accepted_by_server')
        self.assertEqual(self.mutations(), [('thread/goal/set', {'threadId': 'test-thread', 'status': 'active'})])
        self.assertEqual(self.queue(source='large-explicit-control-source', text=text), ident)
        self.assertEqual(registry.read_bytes(), original)
        self.assertEqual(list((self.control / 'pending').glob('*.json')), [])
        self.assert_holds_retained()

    def test_crash_after_source_intent_recovers_original_binding_without_repinning(self):
        write_json = launcher.atomic_json

        def fail_pending(path, value):
            if Path(path).parent.name == "pending":
                raise OSError("offline simulated queue interruption")
            return write_json(path, value)

        with patch.object(launcher, "atomic_json", side_effect=fail_pending):
            with self.assertRaises(OSError):
                self.queue()
        registry = next((self.control / "sources").glob("*.json"))
        original = json.loads(registry.read_text())["item"]
        self.campaign.goal = dict(self.campaign.goal, updatedAt=999)
        self.campaign.save(goal=self.campaign.goal)
        ident = self.queue()
        published = json.loads((self.control / "pending" / (ident + ".json")).read_text())
        self.assertEqual(published, original)
        self.assertNotEqual(published["control"]["goal_sha256"], launcher._account_value_sha256(self.campaign.goal))
        self.assertEqual(self.mutations(), [])

    def test_ordinary_instruction_never_activates_a_blocked_goal(self):
        self.args.repair_agent_failures = True
        launcher.queue_instruction(self.directory, "Review the corrected source; preserve the blocked goal.",
                                   source_id="ordinary-user-source")
        self.campaign.deliver_instruction()
        self.assertEqual([method for method, _ in self.mutations()], ["turn/start"])
        self.assertEqual(self.campaign.goal["status"], "blocked")
        self.assert_holds_retained()

    def test_disabled_control_consumer_never_falls_back_to_plain_instruction_delivery(self):
        ident = self.queue()
        self.args.same_owner_control = False
        self.args.repair_agent_failures = True
        self.campaign.deliver_instruction()
        self.assertEqual(self.mutations(), [])
        self.assertTrue((self.control / "refused" / (ident + ".json")).exists())
        self.assertEqual(self.campaign.goal["status"], "blocked")

    def test_real_service_hold_blocks_resume_without_releasing_scoped_holds(self):
        self.queue()
        self.campaign.save(service_hold={"reason": "original unresolved service hold"})
        self.campaign.deliver_instruction()
        self.assertEqual(self.mutations(), [])
        self.assertEqual(self.campaign.state["last_instruction"]["status"], "same_owner_resume_refused")
        self.assertEqual(self.campaign.state["service_hold"], {"reason": "original unresolved service hold"})
        self.assert_holds_retained()

    def test_current_or_unattributed_account_errors_block_control_without_stop_reason(self):
        errors = ({"codexErrorInfo": "cyberPolicy"}, {"code": "auth_required"},
                  {"codexErrorInfo": "usageLimitExceeded"}, {"code": "quota_exceeded"},
                  {"error_code": "permission_denied"}, {"message": "not authenticated"},
                  {"message": "permission denied"})
        for index, error in enumerate(errors):
            for current_provenance in (False, True):
                with self.subTest(error=error, current_provenance=current_provenance):
                    provenance = ({"error": error, "log_dir": str(self.campaign.log_dir)}
                                  if current_provenance else None)
                    self.campaign.save(last_error=error, last_error_provenance=provenance,
                                       stop_reason=None)
                    self.assertIsNone(self.campaign.stop_reason)
                    self.assertIsNone(self.campaign.state["stop_reason"])
                    with self.assertRaises(ValueError):
                        self.observed()
                    with self.assertRaises(ValueError):
                        self.queue(source="denied-error-{}-{}".format(index, current_provenance))
                    self.assert_holds_retained()
        self.assertEqual(self.mutations(), [])

    def test_account_error_arriving_after_queue_blocks_consumer_without_stop_reason(self):
        self.queue()
        error = {"codexErrorInfo": "cyberPolicy", "message": "original service notice"}
        self.campaign.save(last_error=error, last_error_provenance={
            "error": error, "log_dir": str(self.campaign.log_dir)}, stop_reason=None)
        self.campaign.deliver_instruction()
        self.assertEqual(self.mutations(), [])
        self.assertEqual(self.campaign.goal["status"], "blocked")
        self.assertEqual(self.campaign.state["last_instruction"]["status"], "same_owner_resume_refused")
        self.assertEqual(self.campaign.state["last_error"], error)
        self.assert_holds_retained()

    def test_current_non_account_failure_does_not_globalize_scoped_holds(self):
        self.campaign.save(last_error={"message": "bounded functional compile failure"},
                           last_error_provenance=None, stop_reason=None)
        # Control projects only the account/service/uncertainty rules from the
        # existing recovery guard. Source/native/resource holds remain scoped.
        self.assertEqual(self.observed()["status"], "OBSERVED")
        self.queue()
        self.campaign.deliver_instruction()
        self.assertEqual(self.mutations(), [("thread/goal/set", {"threadId": "test-thread", "status": "active"})])
        self.assert_holds_retained()

    def test_authentication_change_stops_control_before_activation(self):
        self.queue()
        self.rpc.account_type = "apiKey"
        self.campaign.deliver_instruction()
        self.assertEqual(self.campaign.stop_reason, "chatgpt_auth_changed")
        self.assertTrue(self.campaign.stop_now)
        self.assertEqual(self.mutations(), [])
        self.assert_holds_retained()

    def test_unknown_or_exhausted_accounting_blocks_resume(self):
        self.queue()
        self.rpc.limits["credits"]["balance"] = "850"
        self.campaign.deliver_instruction()
        self.assertEqual(self.campaign.stop_reason, "credit_budget_exhausted")
        self.assertTrue(self.campaign.stop_now)
        self.assertEqual(self.mutations(), [])
        self.assertEqual(self.ledger()["remaining"], "0")
        self.assert_holds_retained()

    def test_unknown_account_balance_blocks_resume(self):
        self.queue()
        self.rpc.limits["credits"].pop("balance")
        self.campaign.deliver_instruction()
        self.assertEqual(self.campaign.stop_reason, "credit_budget_unknown")
        self.assertTrue(self.campaign.stop_now)
        self.assertEqual(self.mutations(), [])
        self.assert_holds_retained()

    def test_freshest_read_error_cannot_fall_back_to_older_control_observation(self):
        old = self.observed()
        self.rpc.usage_error = RuntimeError("account/rateLimits/read: account denied")
        self.campaign.refresh_credit_budget()
        self.assertGreater(self.campaign.state["last_account_observation"]["sequence"], old["sequence"])
        self.assertEqual(self.campaign.state["last_account_observation"]["status"], "REJECTED")
        with self.assertRaises(ValueError):
            self.observed()
        self.assertEqual(self.mutations(), [])

    def test_control_evidence_requires_both_fresh_clocks_and_original_owner(self):
        observed = self.observed()
        for utc_delta, mono_delta in ((26, 0), (0, 26), (-1, 0), (0, -1)):
            with self.subTest(utc_delta=utc_delta, mono_delta=mono_delta), self.assertRaises(ValueError):
                launcher.observed_account_control(self.campaign.state, self.ledger(), self.owner(),
                    observed["received_utc_ns"] + utc_delta * 1000000000,
                    observed["received_mono_ns"] + mono_delta * 1000000000)
        changed = dict(self.owner(), log_dir="different-owner")
        with self.assertRaises(ValueError):
            launcher.observed_account_control(self.campaign.state, self.ledger(), changed,
                                             time.time_ns(), time.monotonic_ns())

    def test_goal_or_stop_generation_change_refuses_the_old_command(self):
        self.queue()
        self.campaign.primary_stop_generation += 1
        self.campaign.save()
        self.campaign.deliver_instruction()
        self.assertEqual(self.mutations(), [])
        self.assertEqual(self.campaign.state["last_instruction"]["status"], "same_owner_resume_refused")
        self.assert_holds_retained()

    def test_exact_live_goal_change_refuses_the_original_command(self):
        self.queue()
        self.rpc.goal = dict(self.rpc.goal, updatedAt=999)
        self.campaign.deliver_instruction()
        self.assertEqual(self.mutations(), [])
        self.assertEqual(self.campaign.state["last_instruction"]["status"], "same_owner_resume_refused")
        self.assert_holds_retained()

    def test_live_objective_change_refuses_the_original_command(self):
        self.queue()
        self.rpc.goal = dict(self.rpc.goal, objective="A different objective")
        self.campaign.deliver_instruction()
        self.assertEqual(self.mutations(), [])
        self.assertEqual(self.campaign.state["last_instruction"]["status"], "same_owner_resume_refused")
        self.assert_holds_retained()

    def test_original_process_birth_change_refuses_before_any_control_read(self):
        self.queue()
        self.campaign.save(server_start="99999999999999")
        before = list(self.rpc.calls)
        self.campaign.deliver_instruction()
        self.assertEqual(self.rpc.calls, before)
        self.assertEqual(self.campaign.state["last_instruction"]["status"], "same_owner_resume_refused")
        self.assert_holds_retained()

    def test_active_turn_discovered_on_same_server_blocks_resume(self):
        self.queue()
        self.rpc.turns["test-thread"] = {"id": "original-active-turn", "status": "inProgress"}
        self.campaign.deliver_instruction()
        self.assertEqual(self.mutations(), [])
        self.assertEqual(self.campaign.state["last_instruction"]["status"], "same_owner_resume_refused")
        self.assert_holds_retained()

    def test_pause_arriving_during_final_read_beats_activation(self):
        self.queue()
        self.rpc.before["thread/goal/get"] = lambda: self.rpc.status("paused")
        self.campaign.deliver_instruction()
        self.assertEqual(self.mutations(), [])
        self.assertEqual(self.campaign.goal["status"], "paused")
        self.assert_holds_retained()

    def test_signal_arriving_during_final_read_beats_activation(self):
        self.queue()
        self.rpc.before["thread/goal/get"] = lambda: self.campaign.on_signal(15, None)
        self.campaign.deliver_instruction()
        self.assertEqual(self.mutations(), [])
        self.assertEqual(self.campaign.stop_reason, "signal_15")
        self.assert_holds_retained()

    def test_pause_inside_activation_is_compensated_on_the_same_rpc(self):
        self.queue()

        def pause_before_accepted_activation_response(result):
            self.rpc.status("paused")
            # The observed newer pause races the already issued activation. The
            # server ends active, while the controller retains the pause event.
            self.rpc.goal["status"] = "active"

        self.rpc.after["thread/goal/set"] = pause_before_accepted_activation_response
        self.campaign.deliver_instruction()
        self.assertEqual([params["status"] for method, params in self.mutations()
                          if method == "thread/goal/set"], ["active", "paused"])
        self.assertEqual(self.campaign.goal["status"], "paused")
        self.assertEqual(self.campaign.state["last_instruction"]["status"], "cancelled_after_stop")
        self.assert_holds_retained()

    def test_ambiguous_activation_retains_intent_and_never_replays(self):
        ident = self.queue()

        def lost_reply(result):
            raise TimeoutError("offline accepted activation with lost reply")

        self.rpc.after["thread/goal/set"] = lost_reply
        self.campaign.deliver_instruction()
        sending = self.control / "sending" / (ident + ".json")
        intent = self.control / "sending" / (ident + ".control-intent.json")
        self.assertTrue(sending.exists())
        self.assertTrue(intent.exists())
        original, original_intent = sending.read_bytes(), intent.read_bytes()
        self.assertEqual(self.campaign.state["last_instruction"]["status"], "delivery_uncertain")
        self.assertEqual(self.campaign.state["transport_uncertain"]["method"], "thread/goal/set")
        before = list(self.rpc.calls)
        # Reconciliation is still required even if the memory-only stop latches
        # disappear. The original durable sending claim excludes replay.
        self.campaign.stop_reason, self.campaign.stop_now = None, False
        self.assertIn("test-thread", self.campaign.active)
        self.campaign.deliver_instruction()
        self.assertEqual(self.rpc.calls, before)
        self.assertEqual(sending.read_bytes(), original)
        self.assertEqual(intent.read_bytes(), original_intent)
        self.assertEqual(self.queue(), ident)
        self.assert_holds_retained()

    def test_compensation_failure_remains_uncertain_with_all_charges_retained(self):
        self.queue()

        def stop_inside_activation(result):
            self.campaign.on_signal(15, None)
            self.rpc.before["thread/goal/get"] = lambda: (_ for _ in ()).throw(TimeoutError("offline pause read failed"))

        self.rpc.after["thread/goal/set"] = stop_inside_activation
        self.campaign.deliver_instruction()
        self.assertEqual(self.campaign.stop_reason, "signal_15")
        self.assertEqual(self.campaign.state["last_instruction"]["status"], "delivery_uncertain")
        self.assertTrue(self.campaign.state["transport_uncertain"])
        self.assertTrue(list((self.control / "sending").glob("*.control-intent.json")))
        self.assert_holds_retained()

    def test_compensating_pause_returning_active_retains_uncertainty_and_original_intent(self):
        ident = self.queue()

        def refuse_compensating_pause(result):
            self.rpc.goal["status"] = "active"
            result["goal"]["status"] = "active"

        def stop_inside_activation(result):
            self.campaign.on_signal(15, None)
            self.rpc.after["thread/goal/set"] = refuse_compensating_pause

        self.rpc.after["thread/goal/set"] = stop_inside_activation
        self.campaign.deliver_instruction()
        self.assertEqual([params["status"] for method, params in self.mutations()
                          if method == "thread/goal/set"], ["active", "paused"])
        self.assertEqual(self.campaign.goal["status"], "active")
        self.assertEqual(self.campaign.stop_reason, "signal_15")
        self.assertEqual(self.campaign.state["last_instruction"]["status"], "delivery_uncertain")
        self.assertTrue(self.campaign.stop_now)
        self.assertTrue(self.campaign.state["transport_uncertain"])
        self.assertTrue((self.control / "sending" / (ident + ".json")).exists())
        self.assertTrue((self.control / "sending" / (ident + ".control-intent.json")).exists())
        self.assertFalse((self.control / "delivered" / (ident + ".json")).exists())
        self.assert_holds_retained()

    def test_explicit_continuous_resume_from_paused_retained_owner_preserves_custody(self):
        retention = self.retained_paused_owner()
        original_rpc = self.campaign.rpc
        original_owner = self.owner()
        original_ledger = self.ledger()
        self.assertEqual(self.observed()["status"], "OBSERVED")
        self.assertEqual(self.campaign.state["last_account_observation"]["status"], "PENDING")
        ident = self.queue(source="explicit-paused-retained-resume",
                           text="Resume this same technically paused retained Root; all execution and custody holds remain.")
        self.campaign.deliver_instruction()
        self.assertIs(self.campaign.rpc, original_rpc)
        self.assertEqual(self.owner(), original_owner)
        self.assertEqual(self.ledger(), original_ledger)
        self.assertEqual(self.campaign.state["owner_retention"], retention)
        self.assertEqual(self.mutations(), [("thread/goal/set", {"threadId": "test-thread", "status": "active"})])
        self.assertEqual(self.campaign.state["last_instruction"]["status"], "accepted_by_server")
        self.assertTrue((self.control / "delivered" / (ident + ".json")).exists())
        self.assertEqual(self.campaign.state["last_account_observation"]["status"], "PENDING")
        self.assert_holds_retained()

    def test_paused_retained_owner_is_not_an_automatic_or_plain_instruction_resume(self):
        retention = self.retained_paused_owner()
        launcher.queue_instruction(self.directory, "Review new original M14/M15 source evidence.",
                                   source_id="ordinary-paused-retained-instruction")
        self.campaign.deliver_instruction()
        self.assertEqual(self.mutations(), [])
        self.assertEqual(self.campaign.goal["status"], "paused")
        self.assertEqual(self.campaign.state["owner_retention"], retention)
        self.assert_holds_retained()

    def test_paused_retained_resume_requires_continuous_mode_and_its_current_capability(self):
        self.retained_paused_owner()
        self.args.continuous = False
        self.campaign.save(continuous=False)
        with self.assertRaises(ValueError):
            self.queue(source="noncontinuous-paused-resume")
        self.assertEqual(self.mutations(), [])
        self.assertEqual(self.campaign.goal["status"], "paused")
        self.assert_holds_retained()

    def test_user_pause_marker_wins_over_explicit_paused_retained_control(self):
        retention = self.retained_paused_owner()
        self.campaign.save(user_paused=True)
        with self.assertRaises(ValueError):
            self.queue(source="paused-owner-user-pause-still-authoritative")
        self.assertEqual(self.mutations(), [])
        self.assertIs(self.campaign.state["user_paused"], True)
        self.assertEqual(self.campaign.goal["status"], "paused")
        self.assertEqual(self.campaign.state["owner_retention"], retention)
        self.assert_holds_retained()

    def test_hard_account_stop_wins_over_explicit_paused_retained_control(self):
        retention = self.retained_paused_owner()
        self.campaign.save(stop_reason="credit_budget_unknown",
                           credit_budget_error="original finite accounting unresolved")
        with self.assertRaises(ValueError):
            self.queue(source="paused-owner-account-hold-still-authoritative")
        self.assertEqual(self.mutations(), [])
        self.assertEqual(self.campaign.goal["status"], "paused")
        self.assertEqual(self.campaign.state["stop_reason"], "credit_budget_unknown")
        self.assertEqual(self.campaign.state["owner_retention"], retention)
        self.assert_holds_retained()

    def test_new_user_pause_after_queue_prevents_paused_retained_activation(self):
        retention = self.retained_paused_owner()
        self.queue(source="paused-retained-queued-before-user-pause")
        self.campaign.save(user_paused=True)
        self.campaign.deliver_instruction()
        self.assertEqual(self.mutations(), [])
        self.assertIs(self.campaign.state["user_paused"], True)
        self.assertEqual(self.campaign.goal["status"], "paused")
        self.assertEqual(self.campaign.state["owner_retention"], retention)
        self.assert_holds_retained()

    def test_paused_retained_control_rejects_a_different_saved_custody_owner(self):
        self.retained_paused_owner()
        row = dict(self.campaign.state["owner_retention"], server_start="99999999999999")
        self.campaign.save(owner_retention=row)
        with self.assertRaises(ValueError):
            self.queue(source="paused-retained-wrong-original-owner")
        self.assertEqual(self.mutations(), [])
        self.assertEqual(self.campaign.goal["status"], "paused")
        self.assertEqual(self.campaign.state["owner_retention"], row)
        self.assert_holds_retained()

    def test_bound_technical_checkpoint_reads_fresh_account_before_exact_acknowledgement(self):
        retention, flags = self.technical_checkpoint()
        self.assertEqual(self.observed()["status"], "OBSERVED")
        self.assertEqual(self.campaign.state["last_account_observation"]["status"], "REJECTED")
        ident = self.queue(source="explicit-exact-technical-checkpoint-resume")
        item = json.loads((self.control / "pending" / (ident + ".json")).read_text())
        self.assertEqual(item["control"]["technical_checkpoint"], flags)
        observed_flags = []

        def read_with_original_flags():
            observed_flags.append({"stop_reason": self.campaign.stop_reason,
                "stop_now": self.campaign.stop_now,
                "checkpoint_requested": self.campaign.checkpoint_requested})

        self.rpc.before["account/rateLimits/read"] = read_with_original_flags
        self.campaign.deliver_instruction(control_only=True)
        self.assertEqual(observed_flags, [flags])
        self.assertIsNone(self.campaign.stop_reason)
        self.assertFalse(self.campaign.stop_now)
        self.assertFalse(self.campaign.checkpoint_requested)
        receipt = self.campaign.state["last_instruction"]
        self.assertEqual(receipt["status"], "accepted_by_server")
        self.assertEqual(receipt["acknowledged_checkpoint"], flags)
        self.assertEqual(self.campaign.state["acknowledged_technical_checkpoint"]["checkpoint"], flags)
        self.assertEqual(self.campaign.state["owner_retention"], retention)
        self.assertEqual(self.mutations(), [("thread/goal/set", {"threadId": "test-thread", "status": "active"})])
        self.assert_holds_retained()

    def test_changed_bound_technical_flag_refuses_without_clearing_checkpoint(self):
        retention, flags = self.technical_checkpoint()
        self.queue(source="technical-resume-before-flag-change")
        self.campaign.stop_now = False
        self.campaign.save()
        self.campaign.deliver_instruction(control_only=True)
        self.assertEqual(self.mutations(), [])
        self.assertEqual(self.campaign.stop_reason, flags["stop_reason"])
        self.assertTrue(self.campaign.checkpoint_requested)
        self.assertEqual(self.campaign.state["last_instruction"]["status"], "same_owner_resume_refused")
        self.assertEqual(self.campaign.state["owner_retention"], retention)
        self.assert_holds_retained()

    def test_new_signal_beats_previously_bound_technical_checkpoint(self):
        retention, flags = self.technical_checkpoint()
        self.queue(source="technical-resume-before-current-user-stop")
        self.rpc.before["thread/goal/get"] = lambda: self.campaign.on_signal(15, None)
        self.campaign.deliver_instruction(control_only=True)
        self.assertEqual(self.mutations(), [])
        self.assertEqual(self.campaign.stop_reason, "signal_15")
        self.assertTrue(self.campaign.checkpoint_requested)
        self.assertNotIn("acknowledged_technical_checkpoint", self.campaign.state)
        self.assertEqual(self.campaign.state["owner_retention"], retention)
        self.assert_holds_retained()

    def test_technical_control_cannot_extend_window_or_clear_user_account_unknown_holds(self):
        self.retained_paused_owner()
        for reason in ("signal_15", "user_requested", "work_window", "requested_milestones_complete",
                       "credit_budget_unknown", "chatgpt_auth_changed", "owner_pause_unknown"):
            with self.subTest(reason=reason):
                self.assertFalse(launcher.control_context_eligible(dict(self.campaign.state,
                    stop_reason=reason, stop_now=True, checkpoint_requested=True)))
        for field in ("auth_unknown", "credit_budget_unknown", "included_usage_unknown",
                      "accounting_unknown", "user_pause", "user_paused", "service_hold"):
            for value in (True, None, {}, 0, "UNKNOWN"):
                with self.subTest(field=field, value=value):
                    self.assertFalse(launcher.control_context_eligible(dict(self.campaign.state,
                        **{field: value})))
        self.assertTrue(launcher.control_context_eligible(self.campaign.state))
        self.assert_holds_retained()

    def test_real_exhaustion_during_technical_account_read_never_acknowledges_checkpoint(self):
        retention, flags = self.technical_checkpoint()
        self.queue(source="technical-resume-before-genuine-credit-exhaustion")
        self.rpc.limits["credits"]["balance"] = "850"
        self.campaign.deliver_instruction(control_only=True)
        self.assertEqual(self.mutations(), [])
        self.assertEqual(self.campaign.stop_reason, "credit_budget_exhausted")
        self.assertTrue(self.campaign.stop_now)
        self.assertTrue(self.campaign.checkpoint_requested)
        self.assertNotIn("acknowledged_technical_checkpoint", self.campaign.state)
        self.assertEqual(self.ledger()["remaining"], "0")
        self.assertEqual(self.campaign.state["owner_retention"], retention)
        self.assert_holds_retained()

    def test_cli_requires_an_explicit_source_and_does_not_enable_control_implicitly(self):
        self.assertFalse(launcher.arguments([]).same_owner_control)
        parsed = launcher.arguments(["--resume-same-owner", "Resume original owner", "--instruction-source-id", "user-command-1"])
        self.assertEqual(parsed.resume_same_owner, "Resume original owner")
        self.assertFalse(parsed.same_owner_control)
        with patch("sys.stderr"), self.assertRaises(SystemExit):
            launcher.arguments(["--resume-same-owner", "Resume original owner"])


if __name__ == "__main__":
    unittest.main()
