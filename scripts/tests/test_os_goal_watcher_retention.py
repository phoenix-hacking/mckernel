"""Offline functional watcher failures: fake clock/processes, no live operations."""

from contextlib import ExitStack, redirect_stdout
import copy
import io
import json
import os
from pathlib import Path
import signal
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import os_goal_custody as custody
import watch_os_goal as watcher


class FakeClock:
    def __init__(self):
        self.now = 100.0
        self.sleeps = 0
        self.step = lambda clock: None

    def sleep(self, seconds):
        self.now += seconds
        self.sleeps += 1
        if self.sleeps > 200:
            raise AssertionError("finite fake scenario did not finish")
        self.step(self)


class FakeWorker:
    pid = 987654

    def __init__(self):
        self.returncode = None
        self.signals = []
        self.terminations = 0
        self.kills = 0

    def poll(self):
        return self.returncode

    def send_signal(self, signum):
        self.signals.append(signum)

    def terminate(self):
        self.terminations += 1

    def kill(self):
        self.kills += 1
        self.returncode = -signal.SIGKILL

    def wait(self, timeout=None):
        if self.returncode is None:
            raise watcher.subprocess.TimeoutExpired("fake-worker", timeout)
        return self.returncode


class WatcherRetentionTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="os-goal-watcher-retention-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.repo = self.root / "repo"
        self.repo.mkdir()
        self.directory = self.root / "campaign"
        self.directory.mkdir()
        self.state_path = self.directory / "state.json"
        self.args = SimpleNamespace(hours=0, grace_seconds=0, heartbeat_seconds=0.25,
                                    watchdog_seconds=0, stall_seconds=0, max_restarts=-1,
                                    restart_delay=0, retain_owner_on_stop=True,
                                    guardian_recovery_proof=None, guardian_run_id=None)
        self.worker = FakeWorker()
        self.clock = FakeClock()
        self.handlers = {}
        self.commands = []
        self.lease = SimpleNamespace(close=Mock())
        self.server_pid = 987655
        self.watcher_pid = os.getpid()
        self.watcher_birth = lambda: "100"
        self.state = {"schema_version": 1, "repo": str(self.repo),
                      "worker_pid": self.worker.pid, "worker_start": "200",
                      "server_pid": self.server_pid, "server_start": "300",
                      "thread_id": "original-root", "phase": "running",
                      "log_dir": str(self.directory / "runs" / "original-invocation"),
                      "active_turns": {}, "goal": {"status": "active"},
                      "agent_event_count": 1, "credit_budget": {"id": "same-run", "spent": "12"},
                      "native_ownership": {"status": "UNKNOWN", "release": False}}
        self.initial_state = None
        self.retire = Mock(return_value=True)
        self.diagnostics = Mock(return_value={"state": {}, "processes": {}, "resources": {}})

    def write_json(self, path, value):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value))

    def retain(self):
        self.state["phase"] = custody.RETAINED_PHASE
        self.state["owner_retention"] = custody.make_retention_record(
            self.state, watcher_pid=self.watcher_pid, watcher_start="100", reason="user_pause")

    def run_watcher(self, *, write_json=None):
        def birth(pid):
            if pid == self.watcher_pid:
                return self.watcher_birth()
            return {self.worker.pid: "200", self.server_pid: "300"}.get(pid)

        def set_handler(signum, handler):
            old = self.handlers.get(signum)
            self.handlers[signum] = handler
            return old

        def launch(command, **kwargs):
            self.commands.append(command)
            self.initial_state = copy.deepcopy(self.state)
            self.write_json(self.state_path, self.state)
            return self.worker

        with ExitStack() as stack:
            stack.enter_context(patch.object(watcher.time, "monotonic", side_effect=lambda: self.clock.now))
            stack.enter_context(patch.object(watcher.time, "time", side_effect=lambda: 1700000000 + self.clock.now))
            stack.enter_context(patch.object(watcher.time, "sleep", side_effect=self.clock.sleep))
            stack.enter_context(patch.object(watcher, "process_start", side_effect=birth))
            stack.enter_context(patch.object(watcher.signal, "signal", side_effect=set_handler))
            stack.enter_context(patch.object(watcher.subprocess, "Popen", side_effect=launch))
            stack.enter_context(patch.object(watcher, "retire_server", self.retire))
            stack.enter_context(patch.object(watcher, "diagnostics", self.diagnostics))
            stack.enter_context(patch.object(watcher, "write_recovery_handoff", return_value=self.directory / "RECOVERY.md"))
            stack.enter_context(redirect_stdout(io.StringIO()))
            return watcher.supervise(self.args, self.repo, self.directory, [],
                                     lambda path: self.lease, write_json or self.write_json)

    def events(self):
        return [json.loads(line) for line in (self.directory / "watcher.jsonl").read_text().splitlines()]

    def assert_original_owner_untouched(self):
        self.assertEqual(self.worker.terminations, 0)
        self.assertEqual(self.worker.kills, 0)
        self.retire.assert_not_called()
        self.assertEqual(len(self.commands), 1)
        saved = json.loads(self.state_path.read_text())
        for key in ("worker_pid", "worker_start", "server_pid", "server_start", "log_dir",
                    "credit_budget", "native_ownership"):
            self.assertEqual(saved[key], self.initial_state[key])

    def test_retained_owner_survives_deadlines_watchdogs_repeated_stops_and_missing_receipt(self):
        self.args.hours = 0.0001
        self.args.watchdog_seconds = 0.1
        self.args.stall_seconds = 0.1
        self.retain()

        def advance(clock):
            if clock.sleeps == 1:
                self.handlers[signal.SIGTERM](signal.SIGTERM, None)
                self.handlers[signal.SIGTERM](signal.SIGTERM, None)
            if clock.sleeps == 2:
                self.state.pop("owner_retention")
                self.state["phase"] = "running"
                self.write_json(self.state_path, self.state)
                clock.now += 1000
            if clock.sleeps == 4:
                self.worker.returncode = -9  # independent controller loss, not watcher action

        self.clock.step = advance
        self.assertEqual(self.run_watcher(), 1)
        self.assert_original_owner_untouched()
        self.assertEqual(self.worker.signals, [])
        self.diagnostics.assert_not_called()
        self.assertIn("--retain-owner-on-stop", self.commands[0])
        events = self.events()
        self.assertEqual(sum(row["event"] == "owner_retained" for row in events), 1)
        lost = next(row for row in events if row["event"] == "owner_controller_lost")
        self.assertEqual(lost["owner_identity"]["server_pid"], self.server_pid)
        self.assertEqual(lost["custody"], "UNKNOWN")
        self.assertTrue(lost["operator_required"])

    def test_unconfirmed_receipt_never_escalates_after_grace_expiry(self):
        self.args.hours = 0.0001

        def advance(clock):
            if clock.sleeps == 5:
                self.handlers[signal.SIGTERM](signal.SIGTERM, None)
            if clock.now >= 120:
                self.worker.returncode = 1

        self.clock.step = advance
        self.assertEqual(self.run_watcher(), 1)
        self.assert_original_owner_untouched()
        self.assertEqual(self.worker.signals, [signal.SIGTERM])
        self.assertTrue(any(row["event"] == "owner_retention_unconfirmed" for row in self.events()))

    def test_unexpected_worker_exit_preserves_known_server_and_never_restarts(self):
        self.clock.step = lambda clock: setattr(self.worker, "returncode", 1)
        self.assertEqual(self.run_watcher(), 1)
        self.assert_original_owner_untouched()
        self.assertEqual(self.worker.signals, [])
        final = self.events()[-1]
        self.assertEqual(final["event"], "watcher_retirement")
        self.assertFalse(final["server_retirement_attempted"])
        self.assertFalse(final["server_retired"])
        self.assertTrue(final["recovery_held"])
        self.assertEqual(final["custody"], "UNKNOWN")

    def test_continuous_alias_forwards_owner_control_without_removing_work_window(self):
        self.args.continuous = True
        self.args.retain_owner_on_stop = False
        self.args.hours = 0.0001
        self.retain()
        self.clock.step = lambda clock: setattr(self.worker, "returncode", 1)
        self.assertEqual(self.run_watcher(), 1)
        for option in ("--same-owner-control", "--retain-owner-on-stop", "--repair-agent-failures"):
            self.assertIn(option, self.commands[0])
        index = self.commands[0].index("--hours")
        self.assertGreater(float(self.commands[0][index + 1]), 0)
        self.assert_original_owner_untouched()

    def test_other_watchers_receipt_does_not_suppress_checkpoint_detection(self):
        self.retain()
        self.state["owner_retention"]["watcher_start"] = "previous-watcher"
        self.args.watchdog_seconds = 0.1

        def advance(clock):
            if clock.sleeps == 3:
                self.worker.returncode = 1

        self.clock.step = advance
        self.assertEqual(self.run_watcher(), 1)
        self.assert_original_owner_untouched()
        self.assertEqual(self.worker.signals, [signal.SIGUSR1])
        self.assertFalse(any(row["event"] == "owner_retained" for row in self.events()))
        self.diagnostics.assert_called_once()

    def assert_drift_keeps_first_owner(self):
        original = copy.deepcopy(self.state)

        def advance(clock):
            if clock.sleeps == 1:
                self.state.update(server_pid=987656, server_start="999",
                                  thread_id="different-root",
                                  log_dir=str(self.directory / "runs" / "different-invocation"))
                self.retain()  # A new well-formed claim cannot replace the first owner.
                self.write_json(self.state_path, self.state)
            if clock.sleeps == 2:
                self.worker.returncode = 1

        self.clock.step = advance
        self.assertEqual(self.run_watcher(), 1)
        events = self.events()
        drift = next(row for row in events if row["event"] == "owner_identity_drift")
        self.assertEqual(drift["owner_identity"]["server_pid"], original["server_pid"])
        self.assertEqual(drift["observed_owner_identity"]["server_pid"], 987656)
        self.assertEqual(drift["custody"], "UNKNOWN")
        final = events[-1]
        self.assertEqual(final["owner_identity"]["log_dir"], original["log_dir"])
        self.assertTrue(final["owner_identity_drift"])
        exited = next(row for row in events if row["event"] == "worker_exited")
        self.assertEqual(exited["thread_id"], original["thread_id"])
        self.assertEqual(self.worker.kills, 0)
        self.assertEqual(self.worker.terminations, 0)
        self.retire.assert_not_called()

    def test_first_owner_identity_stays_pinned_when_saved_state_drifts(self):
        self.assert_drift_keeps_first_owner()
        self.assertFalse(any(row["event"] == "owner_retained" for row in self.events()))

    def test_retained_owner_identity_stays_pinned_when_saved_state_drifts(self):
        self.retain()
        self.assert_drift_keeps_first_owner()
        retained = [row for row in self.events() if row["event"] == "owner_retained"]
        self.assertEqual(len(retained), 1)
        self.assertEqual(retained[0]["owner_retention"]["server_pid"], self.server_pid)

    def test_watchdog_identity_read_does_not_replace_pinned_watcher_birth(self):
        self.args.watchdog_seconds = 0.1

        def advance(clock):
            if clock.sleeps == 1:
                self.watcher_birth = lambda: "999"
            if clock.sleeps == 2:
                self.retain()  # Bound to the original watcher birth, still 100.
                self.write_json(self.state_path, self.state)
            if clock.sleeps == 3:
                self.worker.returncode = 1

        self.clock.step = advance
        self.assertEqual(self.run_watcher(), 1)
        self.assert_original_owner_untouched()
        retained = next(row for row in self.events() if row["event"] == "owner_retained")
        self.assertEqual(retained["watcher_start"], "100")
        self.assertEqual(self.events()[-1]["watcher_start"], "100")

    def test_watcher_exception_finalizer_leaves_live_owner_untouched(self):
        def failed_clock(clock):
            raise RuntimeError("fake watcher failure")

        self.clock.step = failed_clock
        with self.assertRaisesRegex(RuntimeError, "fake watcher failure"):
            self.run_watcher()
        self.assert_original_owner_untouched()
        self.assertIsNone(self.worker.returncode)
        self.assertTrue(self.events()[-1]["operator_required"])

    def test_retention_publication_failure_does_not_fall_into_destructive_cleanup(self):
        self.retain()
        failed = []

        def failing_save(path, value):
            if value.get("event") == "owner_retained" and not failed:
                failed.append(True)
                raise OSError("retention receipt publication unavailable")
            self.write_json(path, value)

        with self.assertRaisesRegex(OSError, "publication unavailable"):
            self.run_watcher(write_json=failing_save)
        self.assert_original_owner_untouched()
        self.assertEqual(self.worker.signals, [])
        self.assertIsNone(self.worker.returncode)

    def test_default_off_keeps_normal_forced_stop_and_server_retirement(self):
        self.args.retain_owner_on_stop = False
        self.args.hours = 0.0001
        self.state["goal"]["status"] = "paused"
        self.assertEqual(self.run_watcher(), 10)
        self.assertEqual(self.worker.terminations, 1)
        self.assertEqual(self.worker.kills, 1)
        self.retire.assert_called_once()
        self.assertNotIn("--retain-owner-on-stop", self.commands[0])


class ExactServerRetirementTests(unittest.TestCase):
    def test_exact_retained_receipt_blocks_retirement_before_pidfd_or_signal(self):
        state = {"worker_pid": 101, "worker_start": "200", "server_pid": 102,
                 "server_start": "300", "thread_id": "original-root",
                 "log_dir": "/candidate/runs/original", "phase": custody.RETAINED_PHASE}
        state["owner_retention"] = custody.make_retention_record(
            state, watcher_pid=os.getpid(), watcher_start="100")
        with patch.object(watcher, "process_start", return_value="100"), \
                patch.object(watcher, "pidfd_open") as open_pidfd, \
                patch.object(watcher, "pidfd_send_signal") as send_signal:
            self.assertFalse(watcher.retire_server(state, 101, worker_start="200"))
            open_pidfd.assert_not_called()
            send_signal.assert_not_called()

    def test_changed_watcher_or_default_caller_birth_cannot_release_unknown_owner(self):
        state = {"worker_pid": 101, "worker_start": "200", "server_pid": 102,
                 "server_start": "300", "thread_id": "original-root",
                 "log_dir": "/candidate/runs/original", "phase": custody.RETAINED_PHASE}
        state["owner_retention"] = custody.make_retention_record(
            state, watcher_pid=100, watcher_start="100")
        for caller in ({}, {"worker_start": "different-birth"}, {"worker_start": "200"}):
            with self.subTest(caller=caller), \
                    patch.object(watcher, "process_start", return_value="different-watcher") as birth, \
                    patch.object(watcher, "pidfd_open") as open_pidfd, \
                    patch.object(watcher, "pidfd_send_signal") as send_signal:
                self.assertFalse(watcher.retire_server(state, 101, **caller))
                birth.assert_not_called()
                open_pidfd.assert_not_called()
                send_signal.assert_not_called()


if __name__ == "__main__":
    unittest.main()
