"""Observer lifecycle and delivery with temporary files and fake remote calls."""
import json
import os
from pathlib import Path
import signal
import sys
import tempfile
import time
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import os_goal_guard_protocol as protocol
import os_goal_mailbox as mailbox_module
import os_goal_mailbox_monitor as subject


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


if __name__ == "__main__":
    unittest.main()
