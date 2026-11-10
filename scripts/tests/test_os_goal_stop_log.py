"""Offline stop diagnostics using only temporary files and local child writers."""
import copy
import json
import multiprocessing
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import os_goal_stop_log as subject


def concurrent_writer(directory, number):
    subject.write_stop_record(directory, {"log_dir": "/runs/" + str(number)}, event="stop")


class StopLogTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name)
        self.state = {"log_dir": "/runs/current", "worker_pid": 123, "worker_start": "77",
                      "server_pid": 124, "server_start": "78", "thread_id": "root",
                      "goal": {"status": "blocked", "objective": "PRIVATE PROMPT"},
                      "phase": "stopped", "exit_code": 20, "stop_reason": "goal_blocked"}

    def write(self, **kwargs):
        return subject.write_stop_record(self.directory, self.state, event="stop", **kwargs)

    def records(self):
        return [json.loads(line) for line in (self.directory / subject.JOURNAL).read_text().splitlines()]

    def provenance(self, error, **overrides):
        return dict(log_dir=self.state["log_dir"], worker_pid=123, worker_start="77",
                    error=error, **overrides)

    def test_history_survives_invocations_and_latest_matches_final_record(self):
        before = copy.deepcopy(self.state)
        first = self.write()["record"]
        self.assertEqual(self.state, before)
        first_line = (self.directory / subject.JOURNAL).read_bytes()
        self.state["log_dir"] = "/runs/next"
        second = self.write()["record"]
        self.assertTrue((self.directory / subject.JOURNAL).read_bytes().startswith(first_line))
        self.assertEqual(self.records(), [first, second])
        self.assertEqual(json.loads((self.directory / subject.LATEST).read_text()), second)
        self.assertNotEqual(first["record_id"], second["record_id"])
        self.assertTrue(second["recorded_at"].endswith("Z"))
        self.assertEqual(second["invocation"], "next")
        self.assertEqual((self.directory / subject.JOURNAL).stat().st_mode & 0o777, 0o600)

    def test_historical_policy_error_does_not_create_current_policy_stop(self):
        error = {"codexErrorInfo": "cyberPolicy", "message": "old refusal"}
        self.state.update(last_error=error, last_error_provenance={"log_dir": "/runs/old", "error": error})
        record = self.write()["record"]
        self.assertEqual(record["category"], "campaign_blocked")
        self.assertIsNone(record["error"])
        self.assertEqual(record["error_attribution"], "unavailable")
        self.assertEqual(record["retained_diagnostics"][0]["log_dir"], "/runs/old")
        self.assertNotIn("old refusal", json.dumps(record))

    def test_matching_error_and_failure_capture_original_current_diagnostic(self):
        error = {"codexErrorInfo": "cyberPolicy", "message": "current rejection"}
        self.state.update(last_error=error, last_error_provenance=self.provenance(error),
                          last_failure={"log_dir": "/runs/current", "worker_start": "77",
                                        "id": "turn-1", "error": error})
        record = self.write()["record"]
        self.assertEqual(record["category"], "policy_rejection")
        self.assertEqual(record["error"], {"code": "cyberPolicy", "message": "current rejection"})
        self.assertEqual(record["turn_id"], "turn-1")
        self.assertEqual(record["route"], "supported_review")
        self.assertEqual(record["request_scope"], "not_inferred")

    def test_worker_birth_mismatch_or_error_value_mismatch_cannot_promote_error(self):
        error = {"message": "same words"}
        for change in ({"worker_start": "previous"}, {"error": "different"}):
            with self.subTest(change=change):
                provenance = self.provenance(error)
                provenance.update(change)
                self.state.update(last_error=error, last_error_provenance=provenance)
                self.assertIsNone(self.write()["record"]["error"])

    def test_current_failure_can_be_used_when_last_error_is_stale(self):
        self.state.update(last_error="old", last_failure={"log_dir": "/runs/current", "id": "new",
                                                          "error": {"message": "connection reset", "code": "ConnectionError"}})
        record = self.write(reason="server_error")["record"]
        self.assertEqual(record["category"], "technical_failure")
        self.assertEqual(record["error_attribution"], "last_failure")
        self.assertEqual(record["turn_id"], "new")

    def test_explicit_current_errors_do_not_require_saved_provenance(self):
        self.state["active_turns"] = {"root": "active-turn", "child": "other-turn"}
        self.state.update(watcher_pid=122, watcher_start="76")
        record = self.write(reason="launcher_error", error=RuntimeError("broken pipe"))["record"]
        self.assertEqual(record["error_attribution"], "current_event")
        self.assertEqual(record["category"], "technical_failure")
        self.assertEqual(record["error"]["code"], "RuntimeError")
        self.assertEqual(record["turn_id"], "active-turn")
        self.assertEqual(record["identities"]["watcher_pid"], "122")
        self.assertEqual(record["identities"]["watcher_start"], "76")

    def test_message_redaction_bounds_and_no_raw_prompts(self):
        error = {"message": "Bearer abc123 password=hunter2 token=notakey api_key=secret123 "
                            "https://name:password@example.org/ sk-test123 " + "x" * 5000,
                 "request": "PRIVATE REQUEST", "prompt": "PRIVATE PROMPT"}
        record = self.write(error=error)["record"]
        encoded = json.dumps(record)
        for secret in ("abc123", "hunter2", "notakey", "secret123", "name:password", "sk-test123",
                       "PRIVATE REQUEST", "PRIVATE PROMPT"):
            self.assertNotIn(secret, encoded)
        self.assertLessEqual(len(record["error"]["message"]), 1024)

    def test_incomplete_state_is_logged_without_inventing_cause(self):
        self.state = {"last_failure": "malformed", "last_error": {"prompt": "secret"},
                      "last_error_provenance": [], "exit_code": {"bad": "value"}, "goal": [],
                      "active_turns": {}, "thread_id": [], "log_dir": []}
        record = self.write()["record"]
        self.assertEqual(record["category"], "unknown")
        self.assertIsNone(record["exit_code"])
        self.assertIsNone(record["goal_status"])
        self.assertIsNone(record["error"])

    def test_classification_preserves_actual_stop_controls(self):
        for reason, category in (("user_requested", "user_stop"), ("signal_15", "user_stop"),
                                 ("quota_exhausted", "usage_limit"), ("included_usage_unknown", "usage_unknown"),
                                 ("chatgpt_auth_required", "authentication"), ("native_ownership", "binding_or_ownership"),
                                 ("rpc_delivery_uncertain", "delivery_uncertain"), ("work_window", "work_window")):
            with self.subTest(reason=reason):
                self.state["goal"] = {"status": "active"}
                self.assertEqual(self.write(reason=reason)["record"]["category"], category)

    def test_current_permission_and_auth_failures_require_supported_access_before_replay(self):
        for error, category, route in ((PermissionError("permission denied"), "permission_denied", "access_owner"),
                                       ({"code": "403", "message": "forbidden"}, "permission_denied", "access_owner"),
                                       ({"code": "unauthorized", "message": "sign in"}, "authentication", "account_authentication")):
            with self.subTest(category=category, error=error):
                record = self.write(reason="launcher_error", error=error)["record"]
                self.assertEqual(record["category"], category)
                self.assertEqual(record["route"], route)
                self.assertIn("replay", record["remedy"])

    def test_completion_status_and_requested_milestone_reason(self):
        for status in ("complete", "completed"):
            with self.subTest(status=status):
                self.state.update(goal={"status": status}, stop_reason=None)
                self.assertEqual(self.write()["record"]["category"], "goal_completed")
        self.state["goal"] = {"status": "active"}
        self.assertEqual(self.write(reason="requested_milestones_complete")["record"]["category"],
                         "requested_milestones_complete")

    def test_symlink_destinations_and_ancestors_are_rejected_without_outside_writes(self):
        outside = self.directory / "outside"
        outside.mkdir()
        for name in (subject.JOURNAL, subject.LATEST, ".stop-log.lock"):
            with self.subTest(name=name):
                link = self.directory / name
                if link.exists():
                    link.unlink()
                link.symlink_to(outside / "target")
                with self.assertRaises((OSError, ValueError)):
                    self.write()
                self.assertFalse((outside / "target").exists())
                link.unlink()
        linked_directory = self.directory / "link"
        linked_directory.symlink_to(outside, target_is_directory=True)
        with self.assertRaises(OSError):
            subject.write_stop_record(linked_directory, {}, event="stop")
        self.assertFalse((outside / subject.JOURNAL).exists())

    def test_hardlink_and_fifo_are_rejected(self):
        target = self.directory / "target"
        target.write_text("original")
        journal = self.directory / subject.JOURNAL
        journal.hardlink_to(target)
        with self.assertRaises(ValueError):
            self.write()
        self.assertEqual(target.read_text(), "original")
        journal.unlink()
        os.mkfifo(journal)
        with self.assertRaises((OSError, ValueError)):
            self.write()

    def test_concurrent_processes_do_not_interleave_or_lose_records(self):
        context = multiprocessing.get_context("fork")
        children = [context.Process(target=concurrent_writer, args=(str(self.directory), number)) for number in range(8)]
        for child in children:
            child.start()
        for child in children:
            child.join(10)
            self.assertFalse(child.is_alive())
            self.assertEqual(child.exitcode, 0)
        records = self.records()
        self.assertEqual(len(records), 8)
        self.assertEqual({item["invocation"] for item in records}, {str(number) for number in range(8)})
        self.assertEqual(json.loads((self.directory / subject.LATEST).read_text()), records[-1])

    def test_journal_remains_after_latest_refresh_failure(self):
        with patch.object(subject.os, "replace", side_effect=OSError("simulated replace failure")):
            with self.assertRaises(OSError):
                self.write()
        self.assertEqual(len(self.records()), 1)
        self.assertFalse(list(self.directory.glob(".latest-stop-*.tmp")))

    def test_fsyncs_journal_latest_and_directory(self):
        original = subject.os.fsync
        with patch.object(subject.os, "fsync", wraps=original) as synced:
            self.write()
        self.assertEqual(synced.call_count, 4)


if __name__ == "__main__":
    unittest.main()
