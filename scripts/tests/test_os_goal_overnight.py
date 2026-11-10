#!/usr/bin/env python3
"""Detached overnight ownership tests; fake processes, no model/native execution."""
from contextlib import redirect_stdout
import copy
import io
import json
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import start_os_overnight as overnight


class OvernightTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="os-goal-overnight-test-")
        self.addCleanup(self.temp.cleanup)
        self.repo = Path(self.temp.name) / "repo"
        self.repo.mkdir()
        self.directory = self.repo / "os-autopilot"
        self.directory.mkdir()
        self.identities = {
            100: dict(pid=100, start="1000", session=100, ppid=1, state="S"),
            110: dict(pid=110, start="1100", session=100, ppid=100, state="S"),
            120: dict(pid=120, start="1200", session=120, ppid=110, state="S"),
        }
        self.receipt = {
            "schema_version": 1, "attempt_id": "test-attempt", "launched_at": 1,
            "launch_pid": 100, "launch_start": "1000", "launch_session": 100,
            "log_path": str(self.directory / "overnight/test-attempt/overnight.log"),
            "receipt_path": str(self.directory / "overnight/test-attempt/receipt.json"),
            "command": ["systemd-inhibit", "--", "taskset", "-c", "0,6,7",
                        "python3", str(self.repo / "scripts/run_os_goal.py")],
            "status": "STARTING",
        }
        self.watcher = {"watcher_pid": 110, "watcher_start": "1100", "worker_pid": 120,
                        "event": "worker_started", "at": 1}
        self.state = {"worker_pid": 120, "worker_start": "1200", "thread_id": "saved-root",
                      "phase": "running", "goal": {"status": "active"},
                      "active_turns": {"saved-root": "real-turn"}, "heartbeat_at": "now"}
        self.write_state()
        self.identity_patch = patch.object(overnight, "process_identity", side_effect=self.identities.get)
        self.identity_patch.start()
        self.addCleanup(self.identity_patch.stop)
        self.lease_patch = patch.object(overnight, "lease_held", return_value=True)
        self.lease_patch.start()
        self.addCleanup(self.lease_patch.stop)
        self.kill_patch = patch.object(overnight.os, "kill", side_effect=AssertionError("no real signals"))
        self.kill_patch.start()
        self.addCleanup(self.kill_patch.stop)

    def write_state(self):
        (self.directory / "watcher.json").write_text(json.dumps(self.watcher))
        (self.directory / "state.json").write_text(json.dumps(self.state))

    def status(self):
        return overnight.status(self.directory, receipt=self.receipt)

    def test_command_is_continuous_same_root_and_inhibited(self):
        command = overnight.build_command(
            self.repo, python="/fake/python", inhibit="/fake/systemd-inhibit", taskset="/fake/taskset")
        self.assertEqual(command[0], "/fake/systemd-inhibit")
        self.assertIn("/fake/taskset", command)
        self.assertIn("/fake/python", command)
        self.assertIn(str(self.repo / "scripts/run_os_goal.py"), command)
        for flag, value in (("--hours", "0"), ("--max-restarts", "-1"),
                            ("--agent-windows", "off")):
            self.assertEqual(command[command.index(flag) + 1], value)
        self.assertIn("--repair-agent-failures", command)
        self.assertIn("--stop-after-m14-m15", command)
        self.assertEqual(command[command.index("--startup-instruction-file") + 1],
                         str(self.repo / "scripts/m14-m15-overnight-instruction.txt"))
        for flag in ("--fresh-session", "--fresh-on-recovery", "--credit-budget",
                     "--allow-dispatcher-fallback"):
            self.assertNotIn(flag, command)
        self.assertTrue(any("sleep" in arg for arg in command))
        self.assertTrue(any("block" in arg for arg in command))

    def test_popen_receipt_alone_never_claims_active(self):
        (self.directory / "watcher.json").unlink()
        self.assertNotEqual(self.status()["status"], "ACTIVE")
        self.assertNotEqual(self.status()["status"], "WAITING")

    def test_matching_live_watcher_and_worker_report_active(self):
        self.assertEqual(self.status()["status"], "ACTIVE")

    def test_matching_live_blocked_wait_reports_waiting(self):
        self.state.update(phase="waiting_for_input", active_turns={}, goal={"status": "blocked"})
        self.write_state()
        self.assertEqual(self.status()["status"], "WAITING")
        self.assertEqual(self.state["goal"]["status"], "blocked")

    def test_live_processes_without_both_campaign_leases_are_not_active(self):
        for missing in ("watch.lock", "run.lock"):
            with self.subTest(missing=missing), patch.object(
                    overnight, "lease_held", side_effect=lambda directory, name: name != missing):
                self.assertNotIn(self.status()["status"], {"ACTIVE", "WAITING"})

    def test_old_unrelated_or_reused_processes_never_report_active(self):
        mutations = (
            lambda: self.identities[100].update(start="reused"),
            lambda: self.identities[110].update(start="reused"),
            lambda: self.identities[110].update(session=999),
            lambda: self.identities[120].update(start="reused"),
            lambda: self.identities[120].update(ppid=999),
            lambda: self.state.update(worker_pid=999),
            lambda: self.identities.pop(110),
            lambda: self.identities.pop(120),
        )
        original_identities = copy.deepcopy(self.identities)
        original_state = copy.deepcopy(self.state)
        for mutation in mutations:
            self.identities.clear()
            self.identities.update(copy.deepcopy(original_identities))
            self.state = copy.deepcopy(original_state)
            mutation()
            self.write_state()
            with self.subTest(identities=self.identities, state=self.state):
                self.assertNotIn(self.status()["status"], {"ACTIVE", "WAITING"})

    def test_hard_stop_and_exit_are_not_active_work(self):
        for reason in ("server_error", "included_usage_guard", "signal_15", "permission_denied"):
            self.state.update(phase="running", stop_reason=reason, active_turns={})
            self.write_state()
            with self.subTest(reason=reason):
                self.assertNotIn(self.status()["status"], {"ACTIVE", "WAITING"})

    def test_status_is_read_only_and_never_launches_models(self):
        before = {p.name: p.read_bytes() for p in self.directory.glob("*.json")}
        with patch.object(overnight.subprocess, "Popen", side_effect=AssertionError("no launch")), \
                patch.object(overnight.subprocess, "run", side_effect=AssertionError("no command")):
            self.assertEqual(self.status()["status"], "ACTIVE")
        self.assertEqual({p.name: p.read_bytes() for p in self.directory.glob("*.json")}, before)

    def fake_launch(self, *, exit_code=None):
        process = Mock(pid=100)
        process.poll.return_value = exit_code
        process.wait.return_value = exit_code
        return process

    def test_start_detaches_stdio_and_persists_exact_launch_identity(self):
        process = self.fake_launch()
        with patch.object(overnight, "lease_held", return_value=False), \
                patch.object(overnight.shutil, "which", side_effect=lambda name: "/fake/" + name), \
                patch.object(overnight.subprocess, "Popen", return_value=process) as popen, \
                patch.object(overnight.time, "sleep"):
            result = overnight.start(self.repo, self.directory, wait_seconds=0)
        self.assertEqual(popen.call_count, 1)
        kwargs = popen.call_args.kwargs
        self.assertIs(kwargs["start_new_session"], True)
        self.assertEqual(kwargs["stdin"], subprocess.DEVNULL)
        self.assertEqual(kwargs["stderr"], subprocess.STDOUT)
        self.assertIsNotNone(kwargs["stdout"])
        self.assertIsNot(kwargs["stdout"], sys.stdout)
        pointer = json.loads((self.directory / "overnight-latest.json").read_text())
        # A launch acknowledgement must preserve exact birth/session identities.
        receipt = json.loads(Path(pointer.get("receipt_path", self.receipt["receipt_path"])).read_text())
        self.assertEqual(receipt["command"], popen.call_args.args[0])
        self.assertEqual(receipt["launch_pid"], 100)
        self.assertEqual(receipt["launch_start"], "1000")
        self.assertEqual(receipt["launch_session"], 100)
        self.assertTrue(Path(receipt["log_path"]).is_file())
        self.assertIn(result["status"], {"ACTIVE", "STARTING", "WAITING"})

    def test_existing_campaign_lease_prevents_another_spawn(self):
        for held_name in ("watch.lock", "run.lock"):
            with self.subTest(held_name=held_name), \
                    patch.object(overnight, "lease_held", side_effect=lambda directory, name: name == held_name), \
                    patch.object(overnight.subprocess, "Popen") as popen:
                result = overnight.start(self.repo, self.directory, wait_seconds=0)
            self.assertEqual(result["status"], "EXISTING_OWNER")
            popen.assert_not_called()

    def test_inhibitor_and_hard_stop_exits_have_no_outer_retry(self):
        # 1 covers inhibitor/command failure; 20/21/23 cover ordinary BLOCKED,
        # included usage and service stop exits from the existing watcher.
        for exit_code in (1, 20, 21, 23):
            directory = self.directory / ("exit-" + str(exit_code))
            process = self.fake_launch(exit_code=exit_code)
            with self.subTest(exit_code=exit_code), \
                    patch.object(overnight, "lease_held", return_value=False), \
                    patch.object(overnight.shutil, "which", side_effect=lambda name: "/fake/" + name), \
                    patch.object(overnight.subprocess, "Popen", return_value=process) as popen, \
                    patch.object(overnight.time, "sleep"):
                result = overnight.start(self.repo, directory, wait_seconds=0)
            self.assertNotIn(result["status"], {"ACTIVE", "WAITING", "STARTING"})
            self.assertEqual(popen.call_count, 1)
            self.assertTrue(result.get("error") or result.get("reason") or result.get("exit_code") is not None)

    def test_unavailable_sleep_inhibitor_fails_before_spawning(self):
        with patch.object(overnight, "lease_held", return_value=False), \
                patch.object(overnight.shutil, "which", side_effect=lambda name: None if name == "systemd-inhibit" else "/fake/" + name), \
                patch.object(overnight.subprocess, "Popen") as popen:
            try:
                result = overnight.start(self.repo, self.directory, wait_seconds=0)
            except (RuntimeError, FileNotFoundError) as error:
                self.assertIn("inhibit", str(error).lower())
            else:
                self.assertNotIn(result["status"], {"ACTIVE", "WAITING", "STARTING"})
                self.assertIn("inhibit", json.dumps(result).lower())
        popen.assert_not_called()

    def persist_receipt(self):
        receipt_path = Path(self.receipt["receipt_path"])
        receipt_path.parent.mkdir(parents=True, exist_ok=True)
        receipt_path.write_text(json.dumps(self.receipt))
        (self.directory / "overnight-latest.json").write_text(json.dumps(self.receipt))

    def test_live_receipt_prevents_second_detached_start_before_watcher_lease(self):
        process = self.fake_launch()
        with patch.object(overnight, "lease_held", return_value=False), \
                patch.object(overnight.shutil, "which", side_effect=lambda name: "/fake/" + name), \
                patch.object(overnight.subprocess, "Popen", return_value=process) as popen, \
                patch.object(overnight.time, "sleep"):
            first = overnight.start(self.repo, self.directory, wait_seconds=0)
            second = overnight.start(self.repo, self.directory, wait_seconds=0)
        self.assertEqual(first["status"], "STARTING")
        self.assertEqual(second["status"], "EXISTING_OWNER")
        self.assertEqual(popen.call_count, 1)

    def test_unresolved_crash_around_popen_prevents_blind_second_start(self):
        self.receipt.update(launch_pid=None, launch_start=None, launch_session=None)
        self.persist_receipt()
        with patch.object(overnight, "lease_held", return_value=False), \
                patch.object(overnight.subprocess, "Popen") as popen:
            result = overnight.start(self.repo, self.directory, wait_seconds=0)
        self.assertEqual(result["status"], "EXISTING_OWNER")
        popen.assert_not_called()

    def test_simultaneous_start_lease_prevents_spawn(self):
        with patch.object(overnight.fcntl, "flock", side_effect=BlockingIOError), \
                patch.object(overnight.subprocess, "Popen") as popen:
            result = overnight.start(self.repo, self.directory, wait_seconds=0)
        self.assertEqual(result["status"], "EXISTING_OWNER")
        popen.assert_not_called()

    def test_stop_signals_only_current_watcher_using_pidfd(self):
        self.persist_receipt()
        with patch.object(overnight.os, "pidfd_open", return_value=777) as opened, \
                patch.object(overnight.signal, "pidfd_send_signal") as send, \
                patch.object(overnight.os, "close", wraps=overnight.os.close) as closed, \
                patch.object(overnight.os, "kill", side_effect=AssertionError("no pid-based signal")):
            # Close the fake pidfd without touching any actual unrelated descriptor.
            real_close = closed._mock_wraps
            closed.side_effect = lambda fd: None if fd == 777 else real_close(fd)
            result = overnight.stop(self.directory)
        self.assertEqual(result["status"], "STOP_REQUESTED")
        self.assertEqual(opened.call_args.args[0], 110)
        self.assertEqual(send.call_args.args[:2], (777, signal.SIGTERM))
        self.assertEqual(send.call_count, 1)
        self.assertIn(unittest.mock.call(777), closed.call_args_list)

    def test_stop_rejects_stale_and_unrelated_watcher(self):
        self.persist_receipt()
        for change in ({"start": "reused"}, {"session": 999}):
            with self.subTest(change=change):
                self.identities[110].update(change)
                with patch.object(overnight.os, "kill") as kill, \
                        patch.object(overnight.os, "pidfd_open") as opened, \
                        patch.object(overnight.signal, "pidfd_send_signal") as send:
                    result = overnight.stop(self.directory)
                self.assertNotEqual(result["status"], "STOP_REQUESTED")
                kill.assert_not_called()
                opened.assert_not_called()
                send.assert_not_called()
                self.identities[110] = dict(pid=110, start="1100", session=100, ppid=100, state="S")

    def test_stop_detects_identity_change_after_pidfd_open_and_closes_fd(self):
        self.persist_receipt()
        def open_reused(pid, *args):
            self.assertEqual(pid, 110)
            self.identities[110]["start"] = "reused-after-open"
            return 777
        with patch.object(overnight.os, "pidfd_open", side_effect=open_reused), \
                patch.object(overnight.signal, "pidfd_send_signal") as send, \
                patch.object(overnight.os, "close", wraps=overnight.os.close) as closed:
            real_close = closed._mock_wraps
            closed.side_effect = lambda fd: None if fd == 777 else real_close(fd)
            result = overnight.stop(self.directory)
        self.assertNotEqual(result["status"], "STOP_REQUESTED")
        send.assert_not_called()
        self.assertIn(unittest.mock.call(777), closed.call_args_list)

    def test_dry_run_cli_has_no_process_or_model_side_effects(self):
        output = io.StringIO()
        with patch.object(overnight.subprocess, "check_output", return_value=str(self.directory.parent)), \
                patch.object(overnight.subprocess, "Popen", side_effect=AssertionError("no process")), \
                patch.object(overnight.subprocess, "run", side_effect=AssertionError("no command")), \
                patch.object(overnight.shutil, "which", side_effect=lambda name: "/fake/" + name), \
                patch.object(overnight.os, "umask"), redirect_stdout(output):
            code = overnight.main(["dry-run"])
        data = json.loads(output.getvalue())
        self.assertEqual(code, 0)
        self.assertEqual(data["status"], "DRY_RUN")
        self.assertEqual(data["model_calls"], 0)
        self.assertIn("--hours", data["command"])


if __name__ == "__main__":
    unittest.main()
