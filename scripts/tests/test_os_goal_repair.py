#!/usr/bin/env python3
"""Offline same-Root diagnostic bounds; no launcher, model or native operations."""
import copy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import os_goal_repair as repair
import os_goal_resources as resources


class BlockedRepairTests(unittest.TestCase):
    def setUp(self):
        self.goal = {"status": "blocked", "objective": "Finish original M14 then M15",
                     "threadId": "root", "reason": "ordinary test failed"}
        self.state = {"thread_id": "root", "active_turns": {}, "log_dir": "current",
                      "worker_pid": 42, "worker_start": "123", "stop_reason": None}

    def test_review_context_is_read_only_and_same_root(self):
        before = copy.deepcopy((self.goal, self.state))
        key = repair.blocked_repair_key(self.goal, self.state)
        self.assertEqual(len(key), 64)
        prompt = repair.blocked_repair_instruction(self.goal, self.state)
        self.assertIn(key, prompt)
        self.assertIn("saved goal remains BLOCKED", prompt)
        self.assertIn("does not prove an ordinary software defect", prompt)
        self.assertIn("No forced goal/set active", prompt)
        self.assertEqual((self.goal, self.state), before)

    def test_heartbeat_turn_and_accounting_changes_do_not_create_new_review(self):
        key = repair.blocked_repair_key(self.goal, self.state)
        self.state.update(updated_at="new", heartbeat_at="later", worker_pid=99,
                          log_dir="next", last_turn={"id": "diagnostic-finished"})
        self.goal.update(updatedAt=123, tokensUsed=4500, elapsedSeconds=10,
                         timeUsedSeconds=25, time_used_seconds=26)
        self.assertEqual(repair.blocked_repair_key(self.goal, self.state), key)
        self.goal["reason"] = "new affirmative source input"
        self.assertNotEqual(repair.blocked_repair_key(self.goal, self.state), key)

    def test_no_review_for_other_thread_or_goal_state(self):
        for change in ({"status": "paused"}, {"status": "complete"},
                       {"status": "active"}, {"threadId": "other"},
                       {"objective": ""}, {"objective": 42}):
            with self.subTest(change=change):
                self.assertIsNone(repair.blocked_repair_key(dict(self.goal, **change), self.state))

    def test_active_or_unknown_work_and_requests_block_diagnosis(self):
        for active in (None, [], "", {"root": "turn"}, {"child": "turn"}):
            with self.subTest(active=active):
                self.assertIsNone(repair.blocked_repair_key(
                    self.goal, dict(self.state, active_turns=active)))
        for key, value in (("pending_request", {"method": "permission"}),
                           ("stop_now", True), ("checkpoint_requested", True),
                           ("transport_uncertain", {"method": "turn/start"}),
                           ("credit_budget_error", "unknown balance")):
            with self.subTest(key=key):
                self.assertIsNone(repair.blocked_repair_key(self.goal, dict(self.state, **{key: value})))

    def test_stops_and_all_binding_hold_types_remain_authoritative(self):
        for reason in ("turn_failed", "server_error", "work_window", "signal_15",
                       "quota_exhausted", "chatgpt_auth_required", "needs_user_input",
                       "permission_denied", "native_owner_unknown", "made_up", ""):
            with self.subTest(reason=reason):
                self.assertIsNone(repair.blocked_repair_instruction(
                    self.goal, dict(self.state, stop_reason=reason)))
        for field in repair._HOLDS:
            with self.subTest(field=field):
                self.assertIsNone(repair.blocked_repair_key(self.goal, dict(self.state, **{field: True})))

    def test_error_strings_and_untyped_retryable_claims_never_grant_repair(self):
        for error in ("compile failed", "cyberPolicy", "unknown", {},
                      {"codexErrorInfo": "cyberPolicy"},
                      {"codexErrorInfo": "serverOverloaded"}):
            state = dict(self.state, last_error=error, retryable=True)
            with self.subTest(error=error):
                self.assertIsNone(repair.blocked_repair_key(self.goal, state))
                state["last_error_provenance"] = dict(
                    error=error, log_dir="current", worker_pid=42, worker_start="123")
                self.assertIsNone(repair.blocked_repair_key(self.goal, state))

    def test_only_identity_bound_historical_error_is_separated(self):
        error = {"codexErrorInfo": "cyberPolicy"}
        state = dict(self.state, last_error=error)
        state["last_error_provenance"] = dict(error=error, log_dir="old")
        self.assertIsNotNone(repair.blocked_repair_key(self.goal, state))
        state["last_error_provenance"]["error"] = "different"
        self.assertIsNone(repair.blocked_repair_key(self.goal, state))
        state["last_error_provenance"] = dict(error=error, log_dir="current", worker_pid=41)
        self.assertIsNotNone(repair.blocked_repair_key(self.goal, state))
        state["stop_reason"] = "server_error"
        self.assertIsNone(repair.blocked_repair_key(self.goal, state))

    def test_uncertain_or_unrecognized_instruction_delivery_holds(self):
        for field in ("last_instruction", "resume_instruction"):
            for receipt in ("bad", {}, {"status": "intent"}, {"status": "sending"},
                            {"status": "delivery_uncertain"}, {"status": "invented"}):
                with self.subTest(field=field, receipt=receipt):
                    self.assertIsNone(repair.blocked_repair_key(
                        self.goal, dict(self.state, **{field: receipt})))
            self.assertIsNotNone(repair.blocked_repair_key(
                self.goal, dict(self.state, **{field: {"status": "accepted_by_server"}})))

    def test_malformed_or_oversized_context_never_produces_prompt(self):
        for value in (None, [], "blocked"):
            self.assertIsNone(repair.blocked_repair_key(value, self.state))
            self.assertIsNone(repair.blocked_repair_key(self.goal, value))
        for value in (float("nan"), object(), "x" * 65537):
            self.assertIsNone(repair.blocked_repair_key(dict(self.goal, reason=value), self.state))
        recursive = dict(self.goal)
        recursive["reason"] = recursive
        self.assertIsNone(repair.blocked_repair_key(recursive, self.state))

    def test_instruction_contains_actual_repair_and_hold_boundaries(self):
        prompt = repair.repair_instruction()
        for fragment in ("actual failed command/check", "CAMPAIGN.md", "followup_task",
                         "separate independent owner", "meaningful relevant input",
                         "one bounded correction", "independent ready eligible M14/M15",
                         "Sol/MAX", "Reuse completed HIGH evidence",
                         "source-fetch transport", "cyberPolicy", "permission-rejected",
                         "UNKNOWN outcomes", "without an arbitrary time cap", "included usage limit",
                         "may assign another repair owner", "not a terminal stop",
                         "normal BLOCKED", "do not busy-loop"):
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, prompt)
        self.assertNotIn("schema_version", prompt)
        self.assertNotIn("Sol/HIGH-or-higher", prompt)

    def isolated_state(self):
        """Harness-registered proof permits only a distinct read-only source task."""
        state = copy.deepcopy(self.state)
        state.update(source_hold=True, resource_hold=True,
                     account_hold=False, auth_hold=False, budget_unknown=False,
                     retained_charges=[
                         {"owner": "original-publisher", "planning_bytes": 2 * 1024 ** 3,
                          "jobs": 1, "state": "UNKNOWN"},
                         {"owner": "unjoined-actor", "planning_bytes": 256 * 1024 ** 2,
                          "jobs": 1, "state": "UNKNOWN"}])
        state["repair_context"] = {
            "schema_version": 1, "thread_id": "root", "account_gate_clear": True,
            "source_overhead_accounted": True,
            "blocker": {"scope": "task", "task_id": "held-native-publication",
                        "hold_fields": ["source_hold", "resource_hold"],
                        "parked": True, "turn_status": "failed",
                        "runtime_resources_retained": True},
            "task": {"task_id": "M15-independent-source", "kind": "source",
                     "isolated_from_blocker": True, "requires_execution": False},
            "registered_inputs": [
                {"id": "source-handoff", "kind": "source", "sha256": "a" * 64,
                 "status": "registered", "current": True, "thread_id": "root"},
                {"id": "scope-receipt", "kind": "receipt", "sha256": "b" * 64,
                 "status": "registered", "current": True, "thread_id": "root"}]}
        return state

    def test_parked_terminal_task_frees_logical_slot_without_freeing_225_gib_jobs2(self):
        state = self.isolated_state()
        before = copy.deepcopy(state)
        self.assertTrue(repair.blocked_task_slot_available(state["repair_context"]["blocker"]))
        self.assertIsNotNone(repair.blocked_repair_key(self.goal, state))
        self.assertIn("Registered isolated read-only task M15-independent-source",
                      repair.blocked_repair_instruction(self.goal, state))
        self.assertEqual(sum(row["planning_bytes"] for row in state["retained_charges"]),
                         2 * 1024 ** 3 + 256 * 1024 ** 2)
        self.assertEqual(sum(row["jobs"] for row in state["retained_charges"]), 2)
        self.assertEqual(state, before)

    def test_available_logical_slot_is_not_permission_for_an_incompatible_payload(self):
        state = self.isolated_state()
        now = 100_000_000_000
        snapshot = {
            "observed_utc_ns": now, "observed_mono_ns": now,
            "cpu_affinity": [0, 6, 7], "MemAvailable_bytes": 26 * 1024 ** 3,
            "host_free_bytes": 17 * 1024 ** 3, "scratch_free_bytes": 13 * 1024 ** 3,
            "retained_charges_complete": True, "retained_charges": state["retained_charges"],
            "controller_worker_overhead_bytes": 128 * 1024 ** 2,
            "all_controller_worker_overhead_measured": True, "exclusive_scope_compatible": True}
        request = {"CPU": [7], "planning_bytes": 2 * 1024 ** 3, "jobs": 1,
                   "host_floor_bytes": 17 * 1024 ** 3, "scratch_floor_bytes": 13 * 1024 ** 3,
                   "max_age_ns": 25_000_000_000}
        self.assertTrue(repair.blocked_task_slot_available(state["repair_context"]["blocker"]))
        self.assertIsNotNone(repair.blocked_repair_key(self.goal, state))
        with self.assertRaisesRegex(RuntimeError, "Retained charges"):
            resources.check_payload_admission(snapshot, request, now_utc_ns=now, now_mono_ns=now)
        state["account_hold"] = True
        self.assertIsNone(repair.blocked_repair_key(self.goal, state))

    def test_logical_slot_is_not_free_before_terminal_parking_and_resource_quarantine(self):
        for field, value in (("turn_status", "inProgress"), ("turn_status", "unknown"),
                             ("parked", False), ("runtime_resources_retained", False)):
            state = self.isolated_state()
            state["repair_context"]["blocker"][field] = value
            self.assertFalse(repair.blocked_task_slot_available(state["repair_context"]["blocker"]))
            self.assertIsNone(repair.blocked_repair_key(self.goal, state))
        state = self.isolated_state()
        state["active_turns"] = {"blocked-child": "not-yet-closed-by-original-owner"}
        self.assertIsNone(repair.blocked_repair_key(self.goal, state))

    def test_positive_isolation_and_current_account_overhead_gates_are_required(self):
        for field in ("account_gate_clear", "source_overhead_accounted"):
            for value in (False, None, "true", 1):
                state = self.isolated_state()
                state["repair_context"][field] = value
                self.assertIsNone(repair.blocked_repair_key(self.goal, state))
        for change in ({"isolated_from_blocker": False}, {"requires_execution": True},
                       {"kind": "native"}, {"task_id": "held-native-publication"}):
            state = self.isolated_state()
            state["repair_context"]["task"].update(change)
            self.assertIsNone(repair.blocked_repair_key(self.goal, state))
        state = self.isolated_state()
        state["repair_context"]["blocker"]["hold_fields"] = ["source_hold"]
        self.assertIsNone(repair.blocked_repair_key(self.goal, state))
        state["repair_context"]["blocker"]["scope"] = "global"
        self.assertIsNone(repair.blocked_repair_key(self.goal, state))

    def test_global_stops_override_valid_lane_isolation(self):
        for field in repair._GLOBAL_HOLDS:
            for value in (True, None, {}, "UNKNOWN", 0):
                state = self.isolated_state()
                state[field] = value
                self.assertIsNone(repair.blocked_repair_key(self.goal, state), field)
        for field, value in (("stop_now", True), ("checkpoint_requested", True),
                             ("credit_budget_error", "unknown budget"),
                             ("transport_uncertain", {"method": "turn/start"})):
            state = self.isolated_state()
            state[field] = value
            self.assertIsNone(repair.blocked_repair_key(self.goal, state))
        state = self.isolated_state()
        state["last_error"] = {"codexErrorInfo": "unknown"}
        self.assertIsNone(repair.blocked_repair_key(self.goal, state))
        state = self.isolated_state()
        self.assertIsNone(repair.blocked_repair_key(dict(self.goal, status="paused"), state))

    def test_only_registered_current_revision_changes_rearm_a_diagnostic(self):
        state = self.isolated_state()
        original = repair.blocked_repair_key(self.goal, state)
        state.update(heartbeat_at="later", tokens_used=999, worker_pid=999)
        state["repair_context"]["registered_inputs"].reverse()
        for row in state["repair_context"]["registered_inputs"]:
            row["heartbeat_at"] = "new"
        self.assertEqual(repair.blocked_repair_key(self.goal, state), original)
        state["repair_context"]["registered_inputs"][0]["sha256"] = "c" * 64
        self.assertNotEqual(repair.blocked_repair_key(self.goal, state), original)
        for field, value in (("current", False), ("status", "unregistered"),
                             ("thread_id", "another-root"), ("sha256", "not-a-digest")):
            state = self.isolated_state()
            state["repair_context"]["registered_inputs"][0][field] = value
            self.assertIsNone(repair.blocked_repair_key(self.goal, state))

    def test_uncertain_delivery_still_prevents_isolated_resubmission(self):
        state = self.isolated_state()
        state["last_instruction"] = {"status": "delivery_uncertain"}
        self.assertIsNone(repair.blocked_repair_key(self.goal, state))
        state = self.isolated_state()
        state["resume_instruction"] = {"status": "sending"}
        self.assertIsNone(repair.blocked_repair_key(self.goal, state))

    def test_scope_aware_stop_can_route_only_the_isolated_read_only_task(self):
        state = self.isolated_state()
        state["stop_reason"] = "source_hold"
        self.assertIsNotNone(repair.blocked_repair_key(self.goal, state))
        state["stop_reason"] = "permission_denied"
        self.assertIsNone(repair.blocked_repair_key(self.goal, state))


if __name__ == "__main__":
    unittest.main()
