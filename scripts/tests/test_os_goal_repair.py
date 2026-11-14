#!/usr/bin/env python3
"""Offline same-Root diagnostic bounds; no launcher, model or native operations."""
import copy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import os_goal_repair as repair


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
                         "source-fetch transport", "cyberPolicy", "permission-rejected",
                         "UNKNOWN outcomes", "without an arbitrary time cap", "included usage limit",
                         "may assign another repair owner", "not a terminal stop",
                         "normal BLOCKED", "do not busy-loop"):
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, prompt)
        self.assertNotIn("schema_version", prompt)


if __name__ == "__main__":
    unittest.main()
