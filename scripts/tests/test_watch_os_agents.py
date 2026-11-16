"""Offline functional log-following tests; no security testing or campaign calls."""

import importlib.util
import io
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


spec = importlib.util.spec_from_file_location(
    "agent_viewer", Path(__file__).resolve().parents[1] / "watch_os_agents.py")
viewer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(viewer)


class FollowerTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        (self.root / "runs").mkdir()
        self.state_path = self.root / "state.json"
        self.output = io.StringIO()
        self.follower = viewer.Follower(self.state_path, self.output, lines=2)
        self.addCleanup(self.follower.close)

    def publish(self, name, text, phase="running"):
        log = self.root / "runs" / name
        log.write_text(text)
        self.state_path.write_text(json.dumps({"console_log": str(log), "worker_pid": 123,
                                              "worker_start": "9", "phase": phase,
                                              "goal": {"status": "active"}}))
        return log

    def test_worker_reset_follows_new_log_instead_of_stale_alias(self):
        first = self.publish("first.log", "older\nfirst\nlast\n")
        with patch.object(viewer, "process_alive", return_value=True):
            self.follower.step()
            with first.open("a") as stream:
                stream.write("appended\n")
            self.follower.step()
            self.publish("replacement.log", "replacement-worker\n")
            self.follower.step()
        text = self.output.getvalue()
        self.assertNotIn("older\n", text)
        self.assertEqual(text.count("appended\n"), 1)
        self.assertIn("replacement-worker\n", text)
        self.assertTrue(self.follower.file.name.endswith("replacement.log"))

    def test_rotation_and_truncation_follow_new_bytes(self):
        log = self.publish("current.log", "original\n")
        self.follower.step()
        log.rename(self.root / "runs" / "retained.log")
        log.write_text("rotated\n")
        self.follower.step()
        log.write_text("short\n")
        self.follower.step()
        self.assertIn("original\n", self.output.getvalue())
        self.assertIn("rotated\n", self.output.getvalue())
        self.assertIn("short\n", self.output.getvalue())

    def test_stale_running_and_stopped_are_visible_without_starting_anything(self):
        self.publish("current.log", "data\n")
        with patch.object(viewer, "process_alive", return_value=False):
            self.follower.step()
        state = json.loads(self.state_path.read_text())
        state.update(phase="stopped", stop_reason="credit_budget_unknown", goal={"status": "paused"})
        self.state_path.write_text(json.dumps(state))
        self.follower.step()
        self.assertIn("phase=stale_running_snapshot", self.output.getvalue())
        self.assertIn("phase=stopped goal=paused reason=credit_budget_unknown", self.output.getvalue())

    def test_partial_state_and_external_log_path_wait_without_losing_previous_stream(self):
        log = self.publish("current.log", "retained\n")
        self.follower.step()
        self.state_path.write_text("{")
        self.assertIsNone(self.follower.step())
        self.state_path.write_text(json.dumps({"console_log": str(self.root / "outside.log")}))
        self.assertIsNone(self.follower.step())
        self.assertEqual(log.read_text(), "retained\n")
        self.assertFalse(self.follower.file.closed)

    def test_fresh_state_write_cannot_hide_stale_heartbeat(self):
        self.publish("current.log", "data\n")
        state = json.loads(self.state_path.read_text())
        now = datetime.now(timezone.utc)
        state.update(updated_at=now.isoformat(), heartbeat_at=(now - timedelta(minutes=3)).isoformat())
        self.state_path.write_text(json.dumps(state))
        with patch.object(viewer, "process_alive", return_value=True):
            self.follower.step()
        self.assertIn("phase=heartbeat_stale", self.output.getvalue())

    def test_dead_supervisor_is_visible_even_when_worker_is_live(self):
        self.publish("current.log", "data\n")
        (self.root / "watcher.json").write_text(json.dumps({"event": "worker_started",
            "watcher_pid": 456, "watcher_start": "8"}))
        with patch.object(viewer, "process_alive", side_effect=lambda pid, birth: pid == 123):
            self.follower.step()
        self.assertIn("phase=unmonitored_worker", self.output.getvalue())
        self.assertIn("supervisor=absent", self.output.getvalue())

    def test_roster_distinguishes_running_and_idle_and_reports_changes_once(self):
        self.publish("current.log", "data\n")
        state = json.loads(self.state_path.read_text())
        state.update(thread_id="root", active_turns={"root": "turn"}, agents={
            "root": {"name": "dispatcher", "status": "inProgress"},
            "child": {"name": "/root/dispatch_source", "status": "completed"}})
        self.state_path.write_text(json.dumps(state))
        self.follower.step()
        self.follower.step()
        self.assertEqual(self.output.getvalue().count("1 active turn(s); 2 known"), 1)
        self.assertIn("dispatcher — running", self.output.getvalue())
        self.assertIn("/root/dispatch_source — completed", self.output.getvalue())
        state["active_turns"]["child"] = "child-turn"
        state["agents"]["child"]["status"] = "inProgress"
        self.state_path.write_text(json.dumps(state))
        self.follower.step()
        self.assertIn("2 active turn(s); 2 known", self.output.getvalue())
        self.assertIn("/root/dispatch_source — running", self.output.getvalue())

    def test_retained_in_progress_status_is_not_counted_as_a_live_turn(self):
        self.publish("current.log", "data\n", phase="owner_retained")
        state = json.loads(self.state_path.read_text())
        state.update(active_turns={}, agents={
            "root": {"name": "dispatcher", "status": "inProgress"}})
        self.state_path.write_text(json.dumps(state))
        self.follower.step()
        self.assertIn("0 active turn(s); 1 known", self.output.getvalue())
        self.assertIn("last recorded; no active turn", self.output.getvalue())


if __name__ == "__main__":
    unittest.main()
