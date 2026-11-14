"""Recovery classification and supervisor checks without launching processes."""

from contextlib import redirect_stdout
import importlib.util
import io
import hashlib
import json
import os
from pathlib import Path
import signal
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch


SOURCE = Path(__file__).resolve().parents[1] / "watch_os_goal.py"
SPEC = importlib.util.spec_from_file_location("os_goal_recovery_watch", SOURCE)
watcher = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(watcher)


class RecoveryTests(unittest.TestCase):
    def test_recorded_stops_override_every_recovery_path(self):
        for reason in ("work_window", "signal_2", "signal_15", "signal_1",
                       "quota_exhausted", "quota_or_rate_limit", "needs_user_input", "goal_cleared",
                       "budget_exhausted"):
            for code in (10, 20, 23, 24, 1, -9):
                for watchdog in (False, True):
                    with self.subTest(reason=reason, code=code, watchdog=watchdog):
                        state = {"goal": {"status": "paused"}, "stop_reason": reason,
                                 "retryable": True}
                        self.assertFalse(watcher.should_restart(code, state, watchdog=watchdog))

    def test_terminal_goals_and_supervisor_stop_override_transient_errors(self):
        state = {"stop_reason": "server_error",
                 "last_error": {"codexErrorInfo": "serverOverloaded"}}
        for status in ("complete", "usageLimited", "budgetLimited"):
            with self.subTest(status=status):
                self.assertFalse(watcher.should_restart(23, dict(state, goal={"status": status}), watchdog=True))
        for code in (21, 22):
            with self.subTest(code=code):
                self.assertFalse(watcher.should_restart(code, state, watchdog=True))
        self.assertFalse(watcher.should_restart(23, state, watchdog=True, stopped=True))

    def test_unclassified_pauses_and_blockers_do_not_restart(self):
        for status in ("paused", "blocked"):
            for code in (0, 1, 10, 20, 23, -9):
                for watchdog in (False, True):
                    with self.subTest(status=status, code=code, watchdog=watchdog):
                        self.assertFalse(watcher.should_restart(
                            code, {"goal": {"status": status}}, watchdog=watchdog))

    def test_generic_failures_need_structured_transient_evidence(self):
        for reason in ("server_error", "turn_failed"):
            for error in (None, "serverOverloaded", {}, {"message": "serverOverloaded"},
                          {"codexErrorInfo": "deterministicFailure"},
                          {"codexErrorInfo": {"unknown": {}}}):
                for watchdog in (False, True):
                    with self.subTest(reason=reason, error=error, watchdog=watchdog):
                        self.assertFalse(watcher.should_restart(23, {
                            "stop_reason": reason, "last_error": error, "retryable": True,
                            "goal": {"status": "blocked"}}, watchdog=watchdog))

    def test_recognized_transients_and_transport_continuation_still_recover(self):
        for status in ("active", "paused", "blocked"):
            for reason in ("server_error", "turn_failed"):
                for info in ("serverOverloaded", "rateLimitExceeded"):
                    with self.subTest(status=status, reason=reason, info=info):
                        self.assertTrue(watcher.should_restart(23, {
                            "goal": {"status": status}, "stop_reason": reason,
                            "last_error": {"codexErrorInfo": info}}))
            state = {"goal": {"status": status}}
            self.assertTrue(watcher.should_restart(23, dict(state, stop_reason="rate_limit")))
            self.assertTrue(watcher.should_restart(24, dict(state, stop_reason="active_goal_did_not_continue")))
            self.assertTrue(watcher.should_restart(1, dict(state, stop_reason="launcher_error", retryable=True)))
        self.assertTrue(watcher.should_restart(24, {}))
        self.assertFalse(watcher.should_restart(1, {"retryable": False}))

    def test_direct_stop_signals_are_not_crashes(self):
        for signum in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
            with self.subTest(signal=signum):
                self.assertFalse(watcher.should_restart(-signum, {"goal": {"status": "active"}}))
        self.assertTrue(watcher.should_restart(-signal.SIGTERM, {"goal": {"status": "active"}}, watchdog=True))
        self.assertTrue(watcher.should_restart(-signal.SIGKILL, {"goal": {"status": "active"}}))

    def test_usage_auth_and_policy_stops_survive_crash_and_watchdog(self):
        states = [{"stop_reason": reason} for reason in (
            "included_usage_guard", "included_usage_unknown", "credit_balance_decreased",
            "credit_balance_unknown", "chatgpt_auth_required", "chatgpt_auth_changed")]
        states.extend({"stop_reason": "launcher_error", "last_error": {"codexErrorInfo": info}}
                      for info in ("cyberPolicy", "unauthorized", "quotaExceeded",
                                   "insufficientCredits", {"cyberPolicy": {}}))
        for state in states:
            for code in (0, 1, 24, -9):
                with self.subTest(state=state, code=code):
                    self.assertFalse(watcher.should_restart(code, dict(
                        state, retryable=True, goal={"status": "active"}), watchdog=True))

    def test_watchdog_checkpoint_requires_positive_supervisor_classification(self):
        for status in ("active", "paused", "blocked"):
            state = {"stop_reason": "watchdog_recovery", "goal": {"status": status}}
            self.assertTrue(watcher.should_restart(10, state, watchdog=True))
            self.assertFalse(watcher.should_restart(10, state))
            self.assertFalse(watcher.should_restart(10, state, watchdog=True, stopped=True))
            self.assertFalse(watcher.should_restart(21, state, watchdog=True))
            self.assertFalse(watcher.should_restart(10, dict(state,
                last_error={"codexErrorInfo": "cyberPolicy"}), watchdog=True))

    def supervise(self, exits, states, retire=True, fresh=False, argv=None, watchdog=False,
                  max_restarts=2):
        args = SimpleNamespace(hours=0, max_restarts=max_restarts, restart_delay=0,
                               heartbeat_seconds=15, watchdog_seconds=0.5 if watchdog else 180,
                               stall_seconds=0, grace_seconds=0, fresh_on_recovery=fresh)
        children = [Mock(pid=100 + index, returncode=code) for index, code in enumerate(exits)]
        for child in children:
            child.poll.return_value = child.returncode
        if watchdog:
            children[0].poll.side_effect = [None, None, children[0].returncode]
        lease, writes = Mock(), []
        with tempfile.TemporaryDirectory(prefix="os-goal-recovery-test-") as temporary:
            directory = Path(temporary)
            snapshots = iter([states[0], *states] if watchdog else states)
            first_heartbeat = watchdog
            if watchdog:
                (directory / "state.json").write_text(json.dumps(states[0]))
            clock = iter(range(10000))
            monotonic = (lambda: next(clock)) if watchdog else time.monotonic
            original_process_start = watcher.process_start

            def process_start(pid):
                if watchdog and pid == children[0].pid:
                    return "12345"
                return original_process_start(pid)

            def snapshot(path):
                nonlocal first_heartbeat
                state = next(snapshots)
                if not first_heartbeat:
                    path.write_text(json.dumps(state))
                first_heartbeat = False
                return state

            def write_json(path, value):
                if path.name.startswith("fresh-recovery-"):
                    self.assertTrue(retire_server.called)
                    self.assertTrue(retire_server.return_value)
                path.write_text(json.dumps(value))
                writes.append(dict(value))

            with patch.object(watcher.subprocess, "Popen", side_effect=children) as spawn, \
                    patch.object(watcher, "snapshot", side_effect=snapshot), \
                    patch.object(watcher, "retire_server", return_value=retire) as retire_server, \
                    patch.object(watcher, "process_start", side_effect=process_start), \
                    patch.object(watcher.time, "monotonic", side_effect=monotonic), \
                    patch.object(watcher.time, "sleep"), \
                    patch.object(watcher.signal, "signal"), redirect_stdout(io.StringIO()):
                code = watcher.supervise(args, directory, directory, argv or [],
                                         lambda path: lease, write_json)
            lease.close.assert_called_once_with()
        return code, spawn.call_args_list, writes, retire_server.call_args_list

    def test_supervisor_stops_instead_of_spawning_another_blocked_worker(self):
        for status, code in (("paused", 10), ("blocked", 20)):
            with self.subTest(status=status):
                result, spawns, records, _ = self.supervise([code], [{
                    "thread_id": "saved-thread", "worker_pid": 100, "goal": {"status": status}}])
                self.assertEqual(result, code)
                self.assertEqual(len(spawns), 1)
                self.assertNotIn("restarting_saved_session", [row["event"] for row in records])

    def test_code24_resumes_saved_session_after_server_retirement(self):
        states = [{"thread_id": "saved-thread", "worker_pid": 100,
                   "goal": {"status": "paused"}, "cleanup_verified": False,
                   "stop_reason": "active_goal_did_not_continue"},
                  {"thread_id": "saved-thread", "worker_pid": 101,
                   "goal": {"status": "complete"}, "cleanup_verified": False}]
        code, spawns, records, retired = self.supervise([24, 0], states)
        self.assertEqual(code, 0)
        self.assertEqual(len(spawns), 2)
        self.assertNotIn("--recovered", spawns[0].args[0])
        self.assertIn("--recovered", spawns[1].args[0])
        restarts = [row for row in records if row["event"] == "restarting_saved_session"]
        self.assertEqual([row["thread_id"] for row in restarts], ["saved-thread"])
        self.assertEqual([call.args[1] for call in retired], [100, 101])
        self.assertTrue(all(state["cleanup_verified"] is False for state in states))

    def test_unknown_server_ownership_blocks_even_code24_recovery(self):
        code, spawns, records, _ = self.supervise([24], [{
            "thread_id": "saved-thread", "worker_pid": 100, "goal": {"status": "active"}}], retire=False)
        self.assertEqual(code, 1)
        self.assertEqual(len(spawns), 1)
        self.assertIn("recovery_stopped_server_identity_unresolved", [row["event"] for row in records])

    def test_fresh_recovery_preserves_same_prepaid_credit_run(self):
        states = [{"thread_id": "old-thread", "worker_pid": 100,
                   "goal": {"status": "active"}},
                  {"thread_id": "new-thread", "worker_pid": 101,
                   "goal": {"status": "complete"}}]
        ident = "a" * 32
        argv = ["--fresh-on-recovery", "--credit-budget", "100", "--credit-run-id", ident]
        code, spawns, _, _ = self.supervise([-9, 0], states, fresh=True, argv=argv)
        self.assertEqual(code, 0)
        self.assertEqual(len(spawns), 2)
        for call in spawns:
            command = call.args[0]
            self.assertEqual(command[command.index("--credit-budget") + 1], "100")
            self.assertEqual(command[command.index("--credit-run-id") + 1], ident)

    def test_explicit_first_fresh_launch_does_not_repeat_on_saved_recovery(self):
        states = [{"thread_id": "saved-thread", "worker_pid": 100,
                   "goal": {"status": "active"}},
                  {"thread_id": "saved-thread", "worker_pid": 101,
                   "goal": {"status": "complete"}}]
        _, spawns, records, _ = self.supervise([-9, 0], states, argv=["--fresh-session"])
        self.assertIn("--fresh-session", spawns[0].args[0])
        self.assertNotIn("--fresh-session", spawns[1].args[0])
        self.assertNotIn("--fresh-recovery-proof", spawns[1].args[0])
        self.assertIn("restarting_saved_session", [row["event"] for row in records])

    def test_fresh_recovery_receipt_binds_classified_retired_worker_snapshot(self):
        states = [{"thread_id": "old-thread", "worker_pid": 100,
                   "phase": "running", "goal": {"status": "active"}},
                  {"thread_id": "new-thread", "worker_pid": 101,
                   "goal": {"status": "complete"}}]
        code, spawns, records, retired = self.supervise(
            [-9, 0], states, fresh=True, argv=["--fresh-session", "--fresh-on-recovery"])
        self.assertEqual(code, 0)
        self.assertNotIn("--fresh-recovery-proof", spawns[0].args[0])
        self.assertNotIn("--fresh-session", spawns[1].args[0])
        command = spawns[1].args[0]
        proof_path = Path(command[command.index("--fresh-recovery-proof") + 1])
        self.assertTrue(proof_path.name.startswith("fresh-recovery-"))
        proofs = [row for row in records if row.get("schema_version") == 1]
        self.assertEqual(len(proofs), 1)
        proof = proofs[0]
        self.assertEqual(proof["worker_pid"], 100)
        self.assertEqual(proof["thread_id"], "old-thread")
        self.assertEqual(proof["exit_code"], -9)
        self.assertTrue(proof["server_retired"])
        self.assertFalse(proof["stopped"])
        self.assertFalse(proof["watchdog"])
        self.assertEqual(proof["state_sha256"], hashlib.sha256(
            json.dumps(states[0]).encode()).hexdigest())
        self.assertIsNotNone(proof["watcher_start"])
        self.assertEqual([call.args[1] for call in retired], [100, 101])
        self.assertIn("restarting_fresh_session", [row.get("event") for row in records])

    def test_fresh_opt_in_cannot_override_stop_or_unresolved_retirement(self):
        cases = [("signal_15", True), ("included_usage_guard", True),
                 ("chatgpt_auth_required", True), ("credit_balance_unknown", True),
                 ("server_error", True), (None, False)]
        for reason, retire in cases:
            state = {"thread_id": "saved-thread", "worker_pid": 100,
                     "goal": {"status": "active"}, "stop_reason": reason,
                     "last_error": {"codexErrorInfo": "cyberPolicy"} if reason == "server_error" else None}
            with self.subTest(reason=reason, retire=retire):
                _, spawns, records, _ = self.supervise([-9], [state], retire=retire, fresh=True)
                self.assertEqual(len(spawns), 1)
                self.assertFalse(any(row.get("schema_version") == 1 for row in records))

    def test_watchdog_termination_can_authorize_fresh_recovery_after_retirement(self):
        states = [{"thread_id": "hung-thread", "worker_pid": 100,
                   "phase": "running", "goal": {"status": "active"}},
                  {"thread_id": "new-thread", "worker_pid": 101,
                   "goal": {"status": "complete"}}]
        code, spawns, records, _ = self.supervise(
            [-signal.SIGTERM, 0], states, fresh=True, watchdog=True)
        self.assertEqual(code, 0)
        self.assertEqual(len(spawns), 2)
        self.assertIn("heartbeat_stalled", [row.get("event") for row in records])
        proof = next(row for row in records if row.get("server_retired") is True)
        self.assertTrue(proof["watchdog"])
        self.assertTrue(proof["server_retired"])

    def test_responsive_watchdog_checkpoint_recovers_paused_goal(self):
        states = [{"thread_id": "hung-thread", "worker_pid": 100,
                   "phase": "stopped", "goal": {"status": "paused"},
                   "stop_reason": "watchdog_recovery"},
                  {"thread_id": "new-thread", "worker_pid": 101,
                   "goal": {"status": "complete"}}]
        code, spawns, records, _ = self.supervise([10, 0], states, fresh=True, watchdog=True)
        self.assertEqual(code, 0)
        self.assertEqual(len(spawns), 2)
        request = next(row for row in records if row.get("reason") == "heartbeat_stalled"
                       and "watcher_start" in row)
        self.assertEqual(request["worker_start"], "12345")
        proof = next(row for row in records if row.get("server_retired") is True)
        self.assertTrue(proof["watchdog"])

    def test_fresh_recovery_resumes_prepared_bootstrap_without_archiving(self):
        for thread_id in (None, "bootstrapping-thread"):
            states = [{"thread_id": thread_id, "worker_pid": 100,
                       "phase": "starting", "previous_session": {"thread_id": "prior-thread"}},
                      {"thread_id": "new-thread", "worker_pid": 101,
                       "goal": {"status": "complete"}}]
            with self.subTest(thread_id=thread_id):
                _, spawns, records, _ = self.supervise([-9, 0], states, fresh=True)
                self.assertEqual(len(spawns), 2)
                self.assertNotIn("--fresh-recovery-proof", spawns[1].args[0])
                self.assertFalse(any(row.get("server_retired") is True for row in records))
                self.assertIn("restarting_saved_session", [row.get("event") for row in records])

    def test_restart_limit_prevents_fresh_recovery_receipt(self):
        _, spawns, records, _ = self.supervise([-9], [{
            "thread_id": "old-thread", "worker_pid": 100,
            "goal": {"status": "active"}}], fresh=True, max_restarts=0)
        self.assertEqual(len(spawns), 1)
        self.assertFalse(any(row.get("schema_version") == 1 for row in records))
        self.assertIn("restart_limit_reached", [row.get("event") for row in records])

    def test_stale_retryable_snapshot_cannot_spawn_another_worker(self):
        code, spawns, records, retired = self.supervise([1], [{
            "thread_id": "saved-thread", "worker_pid": 99, "retryable": True,
            "goal": {"status": "active"}, "stop_reason": "server_error",
            "last_error": {"codexErrorInfo": "serverOverloaded"}}])
        self.assertEqual(code, 1)
        self.assertEqual(len(spawns), 1)
        self.assertFalse(retired)
        self.assertIn("recovery_stopped_worker_snapshot_mismatch", [row["event"] for row in records])


class WatchdogRequestTests(unittest.TestCase):
    def test_request_requires_current_parent_and_worker_birth_identities(self):
        valid = {"schema_version": 1, "watcher_pid": 41, "watcher_start": "1000",
                 "worker_pid": 42, "worker_start": "1001", "reason": "heartbeat_stalled"}
        variants = [dict(valid, **change) for change in (
            {"watcher_pid": 99}, {"watcher_start": "999"}, {"worker_pid": 99},
            {"worker_start": "999"}, {"reason": "explicit_stop"}, {"schema_version": True})]
        with tempfile.TemporaryDirectory(prefix="watchdog-request-test-") as temporary:
            path = Path(temporary) / "watchdog-request-42-1001.json"
            with patch.object(watcher.os, "getpid", return_value=42), \
                    patch.object(watcher.os, "getppid", return_value=41), \
                    patch.object(watcher, "process_start", side_effect=lambda pid: {41: "1000", 42: "1001"}.get(pid)):
                self.assertFalse(watcher.watchdog_requested(temporary, 42))
                for index, value in enumerate([valid, *variants]):
                    path.write_text(json.dumps(value))
                    with self.subTest(value=value):
                        self.assertEqual(watcher.watchdog_requested(temporary, 42), index == 0)
                self.assertFalse(watcher.watchdog_requested(temporary, 99))
                for raw in ("malformed", "[]", "x" * 4097):
                    path.write_text(raw)
                    self.assertFalse(watcher.watchdog_requested(temporary, 42))
                path.write_text(json.dumps(valid))
                with patch.object(watcher.os, "getuid", return_value=os.getuid() + 1):
                    self.assertFalse(watcher.watchdog_requested(temporary, 42))
                target = Path(temporary) / "original.json"
                path.rename(target)
                path.symlink_to(target)
                self.assertFalse(watcher.watchdog_requested(temporary, 42))
                path.unlink()
                os.mkfifo(path)
                self.assertFalse(watcher.watchdog_requested(temporary, 42))


if __name__ == "__main__":
    unittest.main()
