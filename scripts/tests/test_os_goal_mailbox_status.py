"""Large mailbox history and compact status consumers; local temporary files only."""
from contextlib import redirect_stdout
from datetime import datetime, timezone
import hashlib
import io
import json
import os
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import os_goal_guard_protocol as protocol
import os_goal_mailbox_status as subject
import os_goal_service as service
import os_goal_status_feed as feed
import os_goal_status_text as status_text


def history():
    messages = {}
    for index in range(120):
        key = "file:" + hashlib.sha256(str(index).encode("ascii")).hexdigest()
        messages[key] = {
            "source_kind": "file", "source_key": key,
            "source_label": f"inbox.txt revision {index:040x}",
            "source_url": f"https://github.com/owner/repo/blob/{index:040x}/inbox.txt",
            "received_at": f"2026-11-14T00:{index // 60:02d}:{index % 60:02d}Z",
            "delivery_status": ("WAITING", "ACCEPTED", "NOT_QUEUED")[index % 3],
            "request_id": "source-" + f"{index:064x}",
        }
    return {"schema_version": 1, "messages": messages, "last_poll_at": 1000,
            "last_successful_poll_at": 1000, "next_poll_at": 1600, "pending_resumes": [],
            "active_notice_event_id": "active", "notices": {
                "active": {"event_id": "active", "kind": "received", "requested": True,
                           "created_at": "2026-11-14T00:02:00Z", "body": "EXCLUDED_BODY" * 400000,
                           "parts": [{"body": "EXCLUDED_PART"}]}}}


class MailboxStatusTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="mailbox-status-test-")
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name)
        self.path = self.directory / "mailbox-state.json"

    def save(self, state):
        protocol.atomic_json(self.path, state)

    def test_over_four_mib_history_reads_as_compact_accurate_metadata(self):
        state = history()
        self.save(state)
        before = self.path.read_bytes()
        self.assertGreater(len(before), 4 * 1024 * 1024)
        summary = subject.read_mailbox_status(self.path)
        self.assertEqual(summary["message_count"], 120)
        self.assertEqual(len(summary["messages"]), 100)
        self.assertEqual(summary["message_status_counts"]["WAITING"], 40)
        self.assertEqual(summary["message_status_counts"]["ACCEPTED"], 40)
        self.assertEqual(summary["message_status_counts"]["NOT_QUEUED"], 40)
        self.assertEqual(sum(summary["message_status_counts"].values()), 120)
        self.assertEqual(summary["notice_count"], 1)
        self.assertTrue(summary["notice_requested"])
        self.assertEqual(summary["outbox_pending"], 1)
        rendered = json.dumps(summary)
        self.assertLess(len(rendered.encode("utf-8")), 200 * 1024)
        self.assertNotIn("EXCLUDED_BODY", rendered)
        self.assertNotIn("EXCLUDED_PART", rendered)
        self.assertNotIn("body", summary["notices"]["active"])
        self.assertEqual(self.path.read_bytes(), before)
        with self.assertRaisesRegex(ValueError, "bounded"):
            protocol.read_json(self.path)

    def test_recent_receipts_are_chronological_after_sorted_json_roundtrip(self):
        state = json.loads(json.dumps(history(), sort_keys=True))
        expected = sorted(state["messages"], key=lambda key: (
            state["messages"][key]["received_at"], key))[-100:]
        summary = subject.summarize_mailbox_state(state)
        self.assertEqual(list(summary["messages"]), expected)
        self.assertNotEqual(list(state["messages"])[-100:], expected)

    def test_timestamp_offsets_and_equal_timestamp_opaque_keys_sort_stably(self):
        state = {"messages": {
            "file:z": {"received_at": "2026-11-14T01:00:01+01:00", "delivery_status": "WAITING"},
            "file:a": {"received_at": "2026-11-14T00:00:01Z", "delivery_status": "WAITING"},
            "00009": {"received_at": "2026-11-14T00:00:00Z", "delivery_status": "WAITING"},
        }}
        self.assertEqual(list(subject.summarize_mailbox_state(state)["messages"]), ["00009", "file:a", "file:z"])

    def test_only_allowlisted_primitive_metadata_enters_summary(self):
        state = history()
        key = next(reversed(state["messages"]))
        state["messages"][key].update(text="EXCLUDED_MESSAGE", instruction="EXCLUDED_INSTRUCTION",
                                      source_label="label" * 5000, source_url={"text": "EXCLUDED_NESTED"})
        state.update(enqueue_intent={"instruction": "EXCLUDED_INTENT"}, multipart={"parts": "EXCLUDED_HISTORY"},
                     file_inbox={"status": "QUEUED", "text": "EXCLUDED_FILE"},
                     file_reply={"status": "POSTED", "body": "EXCLUDED_REPLY"})
        summary = subject.summarize_mailbox_state(state)
        self.assertLessEqual(len(summary["messages"][key]["source_label"]), 2048)
        self.assertIsNone(summary["messages"][key]["source_url"])
        self.assertNotIn("EXCLUDED_", json.dumps(summary))

    def test_reader_keeps_regular_owned_nofollow_and_stable_read_validation(self):
        self.save({"messages": {}, "notices": {}})
        link = self.directory / "link.json"
        link.symlink_to(self.path)
        with self.assertRaises(OSError):
            subject.read_mailbox_status(link)
        fifo = self.directory / "fifo.json"
        os.mkfifo(fifo)
        with self.assertRaisesRegex(ValueError, "owned regular"):
            subject.read_mailbox_status(fifo)
        owner = os.getuid()
        with patch.object(subject.os, "getuid", return_value=owner + 1):
            with self.assertRaisesRegex(ValueError, "owned regular"):
                subject.read_mailbox_status(self.path)
        real_read = os.read
        changed = False
        def change_after_read(fd, size):
            nonlocal changed
            raw = real_read(fd, size)
            if not changed:
                changed = True
                self.path.write_bytes(b'{"messages":{},"changed":true}')
            return raw
        with patch.object(subject.os, "read", side_effect=change_after_read):
            with self.assertRaisesRegex(ValueError, "changed while reading"):
                subject.read_mailbox_status(self.path)

    def test_reader_accepts_large_history_even_with_short_os_reads(self):
        self.save(history())
        real_read = os.read
        with patch.object(subject.os, "read", side_effect=lambda fd, size: real_read(fd, min(size, 32767))):
            self.assertEqual(subject.read_mailbox_status(self.path)["message_count"], 120)

    def test_renderer_uses_total_counts_and_file_labels_without_comment_ids(self):
        summary = subject.summarize_mailbox_state(history())
        lines = []
        status_text._runtime(lines, {"mailbox": summary}, datetime.now(timezone.utc), None)
        text = "\n".join(lines)
        self.assertIn("Instruction receipts: WAITING=40; ACCEPTED=40; NOT_QUEUED=40", text)
        self.assertIn("Recent instruction receipt metadata: 100 shown of 120 total", text)
        self.assertIn("inbox.txt revision " + f"{119:040x}", text)
        self.assertIn(f"https://github.com/owner/repo/blob/{119:040x}/inbox.txt", text)
        self.assertNotIn("message #None", text)
        self.assertNotIn("EXCLUDED_BODY", text)

    def test_renderer_labels_partial_legacy_counts_as_recent(self):
        runtime = {"mailbox": {"messages": {"file:opaque": {"delivery_status": "WAITING"}}, "message_count": 300}}
        lines = []
        status_text._runtime(lines, runtime, datetime.now(timezone.utc), None)
        self.assertIn("Recent instruction receipts: WAITING=1", "\n".join(lines))

    def test_feed_uses_uncapped_mailbox_reader_and_keeps_other_receipts_bounded(self):
        self.save(history())
        notes = []
        subject_feed = feed.StatusFeed(self.directory, self.directory, publisher=Mock())
        self.assertEqual(subject_feed._snapshot("mailbox-state.json", notes)["message_count"], 120)
        self.assertEqual(notes, [])
        (self.directory / "state.json").write_bytes(self.path.read_bytes())
        self.assertEqual(subject_feed._snapshot("state.json", notes), {})
        self.assertIn("state.json is unavailable: ValueError", notes)

    def test_service_status_returns_compact_file_receipts_for_large_mailbox(self):
        self.save(history())
        protocol.atomic_json(self.directory / "guardian.json", {
            "phase": "MONITORING", "pid": 123, "start": "456"})
        readiness = SimpleNamespace(evaluate_readiness=lambda directory: {"status": "TEST_ONLY"})
        with patch.dict(sys.modules, {"os_goal_readiness": readiness}), \
                patch.object(service, "process_start", return_value="456"), \
                patch.object(service, "lease_free", return_value=False):
            result = service.status(self.directory, self.directory)
        self.assertTrue(result["guardian_live"])
        self.assertEqual(result["mailbox"]["message_count"], 120)
        self.assertEqual(len(result["mailbox"]["messages"]), 100)
        self.assertNotIn("EXCLUDED_BODY", json.dumps(result))

    def test_status_cli_uses_mailbox_summary_instead_of_bounded_receipt_reader(self):
        self.save(history())
        ledger = self.directory / "ledger.json"
        protocol.atomic_json(ledger, {})
        with patch.object(status_text, "render_status_text", return_value="Rendered\n") as render, \
                redirect_stdout(io.StringIO()):
            self.assertEqual(status_text.main(["--runtime-directory", str(self.directory), "--ledger", str(ledger)]), 0)
        mailbox = render.call_args.kwargs["runtime"]["mailbox"]
        self.assertEqual(mailbox["message_count"], 120)
        self.assertEqual(len(mailbox["messages"]), 100)
        self.assertNotIn("EXCLUDED_BODY", json.dumps(mailbox))


if __name__ == "__main__":
    unittest.main()
