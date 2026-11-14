"""Observer lifecycle and delivery with temporary files and fake remote calls."""
import json
import hashlib
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import os_goal_guard_protocol as protocol
import os_goal_mailbox as mailbox_module
import os_goal_mailbox_monitor as subject
import os_goal_status_feed as feed_module
import os_goal_progress as progress


class MonitorTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="mailbox-monitor-test-")
        self.addCleanup(temporary.cleanup)
        self.repo = Path(temporary.name)
        self.directory = self.repo / "runtime"
        self.directory.mkdir()
        self.engine = {"thread_id": "manual-root", "supervision_mode": "manual",
                       "supervision_id": "a" * 32, "worker_pid": 1234567,
                       "worker_start": "111", "phase": "running", "goal": {"status": "active"}}
        protocol.atomic_json(self.directory / "state.json", self.engine)
        protocol.atomic_json(self.directory / "watcher.json", {"watcher_pid": 1234568})
        self.mailbox = Mock()
        self.mailbox.poll.return_value = {"status": "POLLED"}
        self.feed = Mock()
        self.feed.tick.return_value = {"status": "PUBLISHED"}
        self.heartbeat = Mock()

    def observer(self, **kwargs):
        observer = subject.MailboxMonitor(self.repo, self.directory,
            mailbox=kwargs.get("mailbox", self.mailbox), feed=self.feed, heartbeat=self.heartbeat)
        self.addCleanup(observer.close)
        return observer

    def test_competing_monitor_cannot_acquire_lifetime_lock_or_replace_receipt(self):
        first = self.observer()
        prior = (self.directory / subject.STATE_FILE).read_bytes()
        with self.assertRaises(BlockingIOError):
            self.observer()
        self.assertEqual((self.directory / subject.STATE_FILE).read_bytes(), prior)
        self.assertFalse(protocol.lease_free(self.directory, subject.LOCK_FILE))
        first.close()
        second = self.observer()
        self.assertNotEqual(first.snapshot["monitor_id"], second.snapshot["monitor_id"])

    def test_stop_and_restart_change_only_observer_receipts_and_never_engine_controls(self):
        before = {name: (self.directory / name).read_bytes() for name in ("state.json", "watcher.json")}
        first = self.observer()
        self.mailbox.poll.side_effect = lambda context: setattr(first, "stopping", True) or {"status": "POLLED"}
        with patch.object(subject.os, "kill", side_effect=AssertionError("No engine signal")):
            self.assertEqual(first.run(interval=0), 0)
        self.assertEqual(protocol.read_json(self.directory / subject.STATE_FILE)["phase"], "STOPPED")
        self.feed.tick.assert_not_called()
        first.close()
        self.mailbox.poll.side_effect = None
        self.observer().tick()
        self.assertEqual({name: (self.directory / name).read_bytes() for name in before}, before)
        self.assertFalse((self.directory / "guardian-intents").exists())
        self.assertFalse((self.directory / "guardian-stop.json").exists())

    def test_manual_owner_receives_without_guardian_even_when_publication_fails(self):
        config = {"repo": "phoenix-hacking/mckernel", "issue_number": 123,
                  "authorized_user_id": 175406809, "authorized_user_login": "phoenix-hacking",
                  "poll_seconds": 600}
        mailbox = mailbox_module.Mailbox(self.repo, self.directory, config)
        comment = {"id": 10, "body": "/mckernel-instruct\nClose the eligible functional caller.",
                   "created_at": "2026-11-14T03:00:00Z", "updated_at": "2026-11-14T03:00:00Z",
                   "user": {"id": 175406809, "login": "phoenix-hacking", "type": "User"}}
        def api(endpoint, **kwargs):
            if endpoint == "graphql":
                return {"data": {"repository": {"pullRequest": {"comments": {
                    "nodes": [comment], "pageInfo": {"endCursor": "comment:10", "hasNextPage": False}}}}}}
            return None
        self.feed.tick.side_effect = RuntimeError("Publication outage")
        observer = self.observer(mailbox=mailbox)
        with patch.object(mailbox_module, "_gh_api", side_effect=api):
            result = observer.tick()
        pending = list((self.directory / "instructions/pending").glob("*.json"))
        self.assertEqual(len(pending), 1)
        self.assertIn("eligible functional caller", json.loads(pending[0].read_text())["text"])
        self.assertIsNone(result["poll_error"])
        self.assertEqual(result["publication_error"]["type"], "RuntimeError")
        self.assertFalse((self.directory / "guardian.json").exists())
        self.assertEqual(protocol.read_json(self.directory / "state.json"), self.engine)
        # A later network failure cannot consume or revoke the durable instruction.
        with patch.object(mailbox_module, "_gh_api", side_effect=RuntimeError("Network outage")), \
                patch.object(mailbox_module.time, "time", return_value=10 ** 10):
            observer.tick()
        self.assertEqual(list((self.directory / "instructions/pending").glob("*.json")), pending)

    def test_stages_are_bounded_and_a_poll_failure_does_not_skip_publication(self):
        observer = self.observer()
        self.mailbox.poll.side_effect = TimeoutError("Poll deadline")
        with patch.object(subject.signal, "setitimer", return_value=(0, 0)) as timer:
            result = observer.tick()
        self.assertEqual(result["poll_error"]["type"], "TimeoutError")
        self.feed.tick.assert_called_once()
        self.assertIsNone(result["publication_error"])
        self.assertIn(((signal.ITIMER_REAL, 50),), [(call.args,) for call in timer.call_args_list])
        self.assertIn(((signal.ITIMER_REAL, 25),), [(call.args,) for call in timer.call_args_list])
        self.assertGreaterEqual(self.heartbeat.call_count, 3)

    def test_stage_deadline_interrupts_a_stalled_synchronous_call(self):
        started = time.monotonic()
        with self.assertRaisesRegex(subject.ObserverDeadline, "deadline"):
            with subject.bounded_stage(.01):
                time.sleep(.2)
        self.assertLess(time.monotonic() - started, .15)

    def test_deadline_escapes_nested_ordinary_transport_and_telemetry_catches(self):
        swallowed = []
        with self.assertRaises(subject.ObserverDeadline):
            with subject.bounded_stage(.01):
                try:
                    try:
                        time.sleep(.2)
                    except OSError:
                        swallowed.append("mailbox transport catch")
                except Exception:
                    swallowed.append("status feed catch")
        self.assertEqual(swallowed, [])

    def test_live_legacy_guardian_prevents_a_second_network_poller(self):
        protocol.atomic_json(self.directory / "guardian.json", {
            "pid": os.getpid(), "start": protocol.process_start(os.getpid())})
        with patch.object(subject, "lease_free", return_value=False), self.assertRaisesRegex(RuntimeError, "legacy guardian"):
            self.observer()
        self.mailbox.poll.assert_not_called()

    def test_held_guardian_lease_with_mismatched_birth_cannot_authorize_another_poller(self):
        protocol.atomic_json(self.directory / "guardian.json", {
            "pid": os.getpid(), "start": str(int(protocol.process_start(os.getpid())) + 1),
            "mailbox_poll_owner": "independent"})
        with patch.object(subject, "lease_free", return_value=False), self.assertRaisesRegex(RuntimeError, "identity"):
            self.observer()
        self.mailbox.poll.assert_not_called()

    def test_stale_malformed_guardian_telemetry_with_no_guardian_lease_does_not_block_queue_poll(self):
        (self.directory / "guardian.json").write_text("{malformed retained telemetry")
        result = self.observer().tick()
        self.mailbox.poll.assert_called_once()
        self.assertIsNone(result["poll_error"])
        self.assertEqual(result["metadata_issues"], ["guardian.json: JSONDecodeError"])


class WorktreeSourceTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="mailbox-source-worktrees-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.primary, self.observer_repo = self.root / "primary", self.root / "observer"
        self.git("init", "-q", str(self.primary))
        self.ledger_path = Path("docs/verification/m14-m15-closure-progress.json")
        (self.primary / self.ledger_path).parent.mkdir(parents=True)
        protocol.atomic_json(self.primary / self.ledger_path, {"source": "observer-pinned"})
        self.git("-C", str(self.primary), "add", ".")
        self.git("-C", str(self.primary), "-c", "user.name=Fixture", "-c",
                 "user.email=fixture@example.invalid", "commit", "-qm", "Pinned observer source")
        self.git("-C", str(self.primary), "worktree", "add", "--quiet", "--detach",
                 str(self.observer_repo), "HEAD")
        protocol.atomic_json(self.primary / self.ledger_path, {"source": "primary-committed"})
        self.git("-C", str(self.primary), "add", ".")
        self.git("-C", str(self.primary), "-c", "user.name=Fixture", "-c",
                 "user.email=fixture@example.invalid", "commit", "-qm", "Current primary source")
        self.primary_head = self.git("-C", str(self.primary), "rev-parse", "HEAD")
        protocol.atomic_json(self.primary / self.ledger_path, {"source": "primary-dirty"})
        self.directory = self.primary / ".git/os-autopilot"
        self.directory.mkdir()
        self.state = {"repo": str(self.primary), "thread_id": "preserved-root",
                      "supervision_mode": "manual", "goal": {"status": "active"}}
        protocol.atomic_json(self.directory / "state.json", self.state)
        self.mailbox = Mock()
        self.mailbox.poll.return_value = {"status": "POLLED"}
        self.publisher = Mock()
        self.publisher.publish.return_value = {"status": "PUBLISHED"}
        self.writer = Mock(side_effect=lambda path, ledger, **kwargs:
                           Path(path).write_text(json.dumps(ledger)) or {})

    @staticmethod
    def git(*arguments):
        return subprocess.run(["git", *arguments], check=True, capture_output=True,
                              text=True, timeout=5).stdout.strip()

    def observer(self, *, mailbox=None):
        observer = subject.MailboxMonitor(self.observer_repo, self.directory,
            mailbox=self.mailbox if mailbox is None else mailbox, heartbeat=Mock())
        self.addCleanup(observer.close)
        return observer

    def publish(self, observer):
        with patch.object(feed_module, "StatusPublisher", return_value=self.publisher), \
                patch.object(feed_module, "write_status_text", self.writer):
            return observer.tick()

    def test_isolated_observer_publishes_saved_primary_dirty_ledger_and_primary_head(self):
        before = (self.directory / "state.json").read_bytes()
        result = self.publish(self.observer())
        self.assertIsNone(result["publication_error"])
        self.assertEqual(result["publication_source"]["repo"], str(self.primary))
        self.assertEqual(result["publication_source"]["mode"], "SAVED_CONTROLLER_WORKTREE")
        self.assertEqual(self.writer.call_args.args[1], {"source": "primary-dirty"})
        self.assertEqual(self.writer.call_args.kwargs["source_commit"], self.primary_head)
        self.assertEqual(json.loads((self.observer_repo / self.ledger_path).read_text()),
                         {"source": "observer-pinned"})
        self.assertEqual((self.directory / "state.json").read_bytes(), before)
        self.publisher.publish.assert_called_once_with(self.directory / "status.txt")

    def test_successful_state_read_cannot_be_attributed_as_an_absent_controller(self):
        # An earlier existence probe can disagree with an atomic state publish.
        # Only the actual read decides whether the cold-start fallback applies.
        with patch.object(Path, "exists", return_value=False):
            result = self.publish(self.observer())
        self.assertEqual(result["publication_source"]["mode"], "SAVED_CONTROLLER_WORKTREE")
        self.assertEqual(self.writer.call_args.args[1], {"source": "primary-dirty"})

    def test_actual_renderer_reads_closure_operation_from_primary_worktree(self):
        canonical = Path(__file__).resolve().parents[2] / self.ledger_path
        ledger = json.loads(canonical.read_text())
        row = next(row for row in ledger["tasks"]
                   if row.get("counted_in_requirement_rollup") is True and row["percent_complete"] < 100)
        target = {"schema_version": 1, "original_check": row["id"], "owner": "existing owner",
                  "next_action": "Complete the matching original condition", "input_bindings": {"source": "a" * 64},
                  "evidence": [], "operation": None}
        now = time.time()
        receipt = {"schema": progress.OPERATION_SCHEMA, "original_check": row["id"],
                   "condition_sha256": progress.condition_sha256(row), "input_bindings": target["input_bindings"],
                   "name": "PRIMARY-WORKTREE-ONLY", "status": "running", "healthy": True,
                   "started_at": progress._utc(now - 1), "observed_at": progress._utc(now),
                   "deadline_at": progress._utc(now + 60)}
        receipt_path = self.primary / "primary-operation.json"
        protocol.atomic_json(receipt_path, receipt)
        target["operation"] = {"name": receipt["name"], "deadline_at": receipt["deadline_at"],
            "receipt": {"path": receipt_path.name, "sha256": hashlib.sha256(receipt_path.read_bytes()).hexdigest()}}
        protocol.atomic_json(self.primary / self.ledger_path, ledger)
        protocol.atomic_json(self.directory / "state.json", dict(self.state, closure_target=target))
        with patch.object(feed_module, "StatusPublisher", return_value=self.publisher):
            result = self.observer().tick()
        self.assertIsNone(result["publication_error"])
        text = (self.directory / "status.txt").read_text()
        self.assertIn("Matching operation: PRIMARY-WORKTREE-ONLY | HEALTHY_BOUNDED_OPERATION", text)
        self.assertIn("Source commit: " + self.primary_head, text)

    def test_foreign_controller_checkout_withholds_publication_and_preserves_authentic_queue(self):
        foreign = self.root / "foreign"
        self.git("init", "-q", str(foreign))
        protocol.atomic_json(self.directory / "state.json", dict(self.state, repo=str(foreign)))
        config = {"repo": "phoenix-hacking/mckernel", "issue_number": 3,
                  "authorized_user_id": 175406809, "authorized_user_login": "phoenix-hacking",
                  "poll_seconds": 600}
        mailbox = mailbox_module.Mailbox(self.observer_repo, self.directory, config)
        comment = {"id": 10, "body": "/mckernel-instruct\nRead the exact reviewed adoption source.",
                   "created_at": "2026-11-14T03:00:00Z", "updated_at": "2026-11-14T03:00:00Z",
                   "user": {"id": 175406809, "login": "phoenix-hacking", "type": "User"}}
        def api(endpoint, **kwargs):
            if endpoint == "graphql":
                return {"data": {"repository": {"pullRequest": {"comments": {
                    "nodes": [comment], "pageInfo": {"endCursor": "comment:10", "hasNextPage": False}}}}}}
            return None
        observer = self.observer(mailbox=mailbox)
        state_before = (self.directory / "state.json").read_bytes()
        with patch.object(mailbox_module, "_gh_api", side_effect=api):
            result = self.publish(observer)
        pending = list((self.directory / "instructions/pending").glob("*.json"))
        self.assertEqual(len(pending), 1)
        queued_before = pending[0].read_bytes()
        self.assertIn(b"reviewed adoption source", queued_before)
        self.assertIsNone(result["poll_error"])
        self.assertEqual(result["last_publication_result"], "ERROR")
        self.assertEqual(result["publication_source"]["mode"], "UNKNOWN")
        self.assertIn("Git common directory", result["publication_error"]["reason"])
        with patch.object(mailbox_module, "_gh_api", side_effect=api):
            self.publish(observer)
        self.assertEqual(pending[0].read_bytes(), queued_before)
        self.assertEqual((self.directory / "state.json").read_bytes(), state_before)
        self.writer.assert_not_called()
        self.publisher.publish.assert_not_called()

    def test_missing_controller_cold_start_uses_explicit_observer_checkout_attribution(self):
        (self.directory / "state.json").unlink()
        result = self.publish(self.observer())
        self.assertIsNone(result["publication_error"])
        self.assertEqual(result["publication_source"]["mode"], "OBSERVER_CHECKOUT_NO_CONTROLLER")
        self.assertFalse(result["publication_source"]["live_source_verified"])
        self.assertEqual(self.writer.call_args.args[1], {"source": "observer-pinned"})
        self.assertIn("OBSERVER_CHECKOUT_NO_CONTROLLER", " ".join(self.writer.call_args.kwargs["notes"]))
        self.assertFalse((self.directory / "state.json").exists())

    def test_existing_unknown_controller_source_does_not_fall_back_to_observer_checkout(self):
        protocol.atomic_json(self.directory / "state.json", {"thread_id": "preserved-root"})
        result = self.publish(self.observer())
        self.assertIsNone(result["poll_error"])
        self.assertIn("checkout is unknown", result["publication_error"]["reason"])
        self.writer.assert_not_called()
        self.publisher.publish.assert_not_called()


if __name__ == "__main__":
    unittest.main()
