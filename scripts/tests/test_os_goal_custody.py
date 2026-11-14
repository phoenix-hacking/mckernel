"""Pure functional OS/Rust owner-retention policy; no processes or RPC calls."""

import copy
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import os_goal_custody as custody


def owner_state():
    state = {"worker_pid": 101, "worker_start": "1001", "server_pid": 102,
             "server_start": "1002", "thread_id": "original-root",
             "log_dir": "/candidate/runs/original-invocation", "phase": custody.RETAINED_PHASE,
             "active_turns": {}, "goal": {"status": "paused"},
             "service_hold": {"status": "held"},
             "credit_budget": {"id": "original-credit-run", "spent": "12.5"},
             "native_ownership": {"status": "UNKNOWN", "release": False}}
    state["owner_retention"] = custody.make_retention_record(
        state, watcher_pid=100, watcher_start="1000", reason="user_pause")
    return state


def matches(state, **changes):
    expected = dict(worker_pid=101, worker_start="1001", watcher_pid=100, watcher_start="1000")
    expected.update(changes)
    return custody.retention_matches(state, **expected)


class OwnerRetentionPolicyTests(unittest.TestCase):
    def test_opt_in_retains_the_original_bare_rpc_without_operation_evidence(self):
        original_rpc = object()
        for args in (SimpleNamespace(), SimpleNamespace(retain_owner_on_stop=False)):
            self.assertFalse(custody.retention_required(args, original_rpc))
        enabled = SimpleNamespace(retain_owner_on_stop=True)
        self.assertTrue(custody.retention_required(enabled, original_rpc))
        self.assertTrue(custody.retention_required(SimpleNamespace(continuous=True), original_rpc))
        self.assertFalse(custody.retention_required(enabled, None))
        with self.assertRaises(custody.OwnerCustodyRetained):
            custody.guard_owner_close(custody.retention_required(enabled, original_rpc))
        custody.guard_owner_close(False)

    def test_record_preserves_holds_ledger_and_unknown_ownership(self):
        state = owner_state()
        before = copy.deepcopy(state)
        errors = [custody.retention_error("pause", TimeoutError("pause delivery unknown")),
                  custody.retention_error("pump", BrokenPipeError("original channel unavailable")),
                  custody.retention_error("save", OSError("receipt unavailable"))]
        row = custody.make_retention_record(state, watcher_pid=100, watcher_start="1000",
                                            reason="credit_budget_unknown", errors=errors)
        self.assertEqual(state, before)
        self.assertEqual(row["custody"], "UNKNOWN")
        self.assertFalse(row["release_authorized"])
        self.assertFalse(row["automatic_resume"])
        self.assertFalse(row["controller_dispatch_enabled"])
        self.assertEqual(row["inflight_turn_quiescence"], "unverified")
        self.assertEqual(row["errors"], errors)
        row["errors"][0]["error"] = "different diagnostic"
        self.assertEqual(errors[0]["error"], "pause delivery unknown")

    def test_exact_current_worker_server_watcher_and_invocation_are_required(self):
        state = owner_state()
        self.assertTrue(matches(state))
        for field, value in (("worker_pid", 103), ("worker_start", "changed"),
                             ("server_pid", 104), ("server_start", "2002"),
                             ("thread_id", "different-root"),
                             ("log_dir", "/candidate/runs/different-invocation")):
            with self.subTest(field=field):
                altered = copy.deepcopy(state)
                altered[field] = value
                self.assertFalse(matches(altered))
        for expected in ({"worker_pid": 103}, {"worker_start": "2001"},
                         {"watcher_pid": 99}, {"watcher_start": "2000"}):
            with self.subTest(expected=expected):
                self.assertFalse(matches(state, **expected))

    def test_historical_or_incomplete_receipt_cannot_suppress_supervision(self):
        for field, value in (("schema_version", True), ("phase", "stopped"),
                             ("invocation", "/previous/invocation"),
                             ("watcher_pid", 99), ("watcher_start", "999"),
                             ("release_authorized", True), ("automatic_resume", True),
                             ("controller_dispatch_enabled", True), ("custody", "closed")):
            with self.subTest(field=field):
                state = owner_state()
                state["owner_retention"][field] = value
                self.assertFalse(matches(state))
        for field in ("server_pid", "server_start", "log_dir", "worker_start"):
            with self.subTest(missing=field):
                state = owner_state()
                state[field] = None
                state["owner_retention"] = custody.make_retention_record(
                    state, watcher_pid=100, watcher_start="1000")
                self.assertFalse(matches(state))
        self.assertFalse(matches(None))

    def test_completed_turns_output_and_old_heartbeats_do_not_release_custody(self):
        state = owner_state()
        state.update(active_turns={}, last_turn={"status": "completed"},
                     stdout="all children joined; exit=0", updated_at="2000-01-01T00:00:00Z",
                     capture_progress=[])
        self.assertTrue(matches(state))
        self.assertTrue(custody.retention_required(SimpleNamespace(retain_owner_on_stop=True), object()))


if __name__ == "__main__":
    unittest.main()
