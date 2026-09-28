"""Recovery classification and supervisor checks without launching processes."""

from contextlib import redirect_stdout
import importlib.util
import io
from pathlib import Path
import signal
import tempfile
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
                       "quota_exhausted", "quota_or_rate_limit", "needs_user_input", "goal_cleared"):
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

    def supervise(self, exits, states, retire=True):
        args = SimpleNamespace(hours=0, max_restarts=2, restart_delay=0,
                               heartbeat_seconds=15, watchdog_seconds=180,
                               stall_seconds=0, grace_seconds=0)
        children = [Mock(pid=100 + index, returncode=code) for index, code in enumerate(exits)]
        for child in children:
            child.poll.return_value = child.returncode
        lease, writes = Mock(), []
        with tempfile.TemporaryDirectory(prefix="os-goal-recovery-test-") as temporary:
            directory = Path(temporary)
            with patch.object(watcher.subprocess, "Popen", side_effect=children) as spawn, \
                    patch.object(watcher, "snapshot", side_effect=states), \
                    patch.object(watcher, "retire_server", return_value=retire) as retire_server, \
                    patch.object(watcher.signal, "signal"), redirect_stdout(io.StringIO()):
                code = watcher.supervise(args, directory, directory, [], lambda path: lease,
                                         lambda path, value: writes.append(dict(value)))
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

    def test_stale_retryable_snapshot_cannot_spawn_another_worker(self):
        code, spawns, records, retired = self.supervise([1], [{
            "thread_id": "saved-thread", "worker_pid": 99, "retryable": True,
            "goal": {"status": "active"}, "stop_reason": "server_error",
            "last_error": {"codexErrorInfo": "serverOverloaded"}}])
        self.assertEqual(code, 1)
        self.assertEqual(len(spawns), 1)
        self.assertFalse(retired)
        self.assertIn("recovery_stopped_worker_snapshot_mismatch", [row["event"] for row in records])


if __name__ == "__main__":
    unittest.main()
