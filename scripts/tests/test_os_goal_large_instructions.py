"""Large instruction regression tests using temporary files, fake RPC and pipes only."""
import hashlib
import io
import json
import os
from pathlib import Path
import tempfile
import threading
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from scripts.tests.test_os_goal_launcher import FakeRPC, goal, launcher
import os_goal_instruction_limits as limits
import os_goal_instructions as reconciliation


class LargeInstructionTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix="os-large-instructions-")
        self.addCleanup(temp.cleanup)
        self.directory = Path(temp.name)
        (self.directory / "state.json").write_text(json.dumps(
            {"schema_version": 1, "repo": str(self.directory)}))

    def campaign(self, blocked=False):
        args = launcher.arguments(["--hours", "0", "--agent-windows", "off",
                                   "--repair-agent-failures"])
        campaign = launcher.Campaign(args, self.directory, self.directory)
        self.addCleanup(campaign.output.close)
        campaign.state["thread_id"] = "test-thread"
        campaign.controlled = True
        campaign.goal = goal("blocked" if blocked else "active")
        rpc = FakeRPC(args, dict(campaign.goal))
        rpc.on_event = campaign.event
        campaign.rpc = rpc
        if not blocked:
            rpc.started("large-instruction-turn")
        campaign.save()
        return campaign, rpc

    def test_exact_utf8_limit_and_one_byte_over(self):
        for text in ("x" * limits.MAX_INSTRUCTION_BYTES,
                     "😀" * (limits.MAX_INSTRUCTION_BYTES // 4)):
            with self.subTest(kind=text[:1]):
                ident = launcher.queue_instruction(self.directory, text)
                path = self.directory / "instructions/pending" / (ident + ".json")
                self.assertEqual(json.loads(path.read_bytes())["text"], text)
                with self.assertRaisesRegex(ValueError, "262145 UTF-8 bytes.*262144"):
                    launcher.queue_instruction(self.directory, text + "x")

    def test_invalid_text_rejected_without_queue_files(self):
        for text in (None, "", " \n\t", "\ud800"):
            with self.subTest(text=repr(text)), self.assertRaises(ValueError):
                launcher.queue_instruction(self.directory, text)
        self.assertFalse((self.directory / "instructions").exists())

    def test_escape_expansion_source_registry_and_replay_preserve_complete_text(self):
        text = "\0" * limits.MAX_INSTRUCTION_BYTES
        ident = launcher.queue_instruction(self.directory, text, source_id="github:owner/repo:1:2")
        pending = self.directory / "instructions/pending" / (ident + ".json")
        registry = self.directory / "instructions/sources" / (ident[7:] + ".json")
        original = pending.read_bytes(), registry.read_bytes()
        self.assertGreater(len(original[0]), 6 * limits.MAX_INSTRUCTION_BYTES)
        self.assertLess(len(original[1]), limits.MAX_INSTRUCTION_RECORD_BYTES)
        self.assertEqual(json.loads(original[0])["text"], text)
        self.assertEqual(json.loads(original[1])["item"]["text"], text)
        self.assertEqual(launcher.queue_instruction(self.directory, text,
                         source_id="github:owner/repo:1:2"), ident)
        self.assertEqual((pending.read_bytes(), registry.read_bytes()), original)
        with self.assertRaisesRegex(ValueError, "content changed"):
            launcher.queue_instruction(self.directory, "changed", source_id="github:owner/repo:1:2")

    def test_serialized_metadata_budget_is_checked_before_any_queue_write(self):
        with patch.object(launcher, "utc", return_value="x" * limits.MAX_INSTRUCTION_RECORD_BYTES):
            for source in (None, "github:owner/repo:1:3"):
                with self.subTest(source=source), self.assertRaisesRegex(ValueError, "serialized UTF-8 bytes"):
                    launcher.queue_instruction(self.directory, "valid", source_id=source)
        self.assertEqual(list(self.directory.rglob("*.json")), [self.directory / "state.json"])

    def test_registry_envelope_budget_is_checked_before_intent_publication(self):
        source, text, submitted = "github:owner/repo:1:3", "x" * 100, "2026-11-12T04:00:00+00:00"
        item = {"submitted_at": submitted, "text": text,
                "source_id": source, "text_sha256": hashlib.sha256(text.encode()).hexdigest(),
                "id": "source-" + hashlib.sha256(source.encode()).hexdigest()}
        item_size = len((json.dumps(item, indent=2) + "\n").encode())
        with patch.object(limits, "MAX_INSTRUCTION_RECORD_BYTES", item_size + 1), \
                patch.object(launcher, "utc", return_value=submitted):
            with self.assertRaisesRegex(ValueError, "serialized UTF-8 bytes"):
                launcher.queue_instruction(self.directory, text, source_id=source)
        self.assertEqual(list(self.directory.rglob("*.json")), [self.directory / "state.json"])

    def test_full_large_text_reaches_active_and_blocked_controller(self):
        text = "λ\0\n" * 65536
        for blocked in (False, True):
            with self.subTest(blocked=blocked):
                campaign, rpc = self.campaign(blocked)
                ident = launcher.queue_instruction(self.directory, text)
                campaign.deliver_instruction()
                method = "turn/start" if blocked else "turn/steer"
                sent = [params for name, params in rpc.calls if name == method]
                self.assertEqual(len(sent), 1)
                self.assertEqual(sent[0]["input"][0]["text"],
                                 "Live user instruction " + ident + ":\n" + text)
                receipt = self.directory / "instructions/delivered" / (ident + ".json")
                self.assertEqual(json.loads(receipt.read_bytes())["status"], "accepted_by_server")

    def test_large_reconciliation_preserves_original_escaped_bytes(self):
        ident = launcher.queue_instruction(self.directory, "\0" * limits.MAX_INSTRUCTION_BYTES)
        pending = self.directory / "instructions/pending" / (ident + ".json")
        original = pending.read_bytes()
        result = reconciliation.reconcile_instructions(self.directory,
            [{"id": ident, "sha256": hashlib.sha256(original).hexdigest()}],
            hashlib.sha256(b"startup").hexdigest(), execute=True)
        archived = self.directory / "instructions/superseded" / pending.name
        self.assertEqual(archived.read_bytes(), original)
        self.assertEqual(result[0]["status"], "superseded")

    def test_failed_large_controller_send_retains_sending_without_replay(self):
        campaign, rpc = self.campaign()
        text = "x" * limits.MAX_INSTRUCTION_BYTES
        ident = launcher.queue_instruction(self.directory, text)
        failure = launcher.RecoverableFailure("send deadline exhausted")
        with patch.object(rpc, "call", side_effect=failure) as call:
            campaign.deliver_instruction()
            campaign.deliver_instruction()
        self.assertEqual(call.call_count, 1)
        sending = self.directory / "instructions/sending" / (ident + ".json")
        self.assertEqual(json.loads(sending.read_bytes())["text"], text)
        self.assertEqual(campaign.state["last_instruction"]["status"], "delivery_uncertain")
        self.assertTrue(campaign.state["transport_uncertain"])
        self.assertFalse((self.directory / "instructions/delivered" / sending.name).exists())

    def test_startup_reads_exact_unicode_limit_and_preserves_manual_resume_text(self):
        text = "😀" * (limits.MAX_INSTRUCTION_BYTES // 4)
        path = self.directory / "startup.txt"
        path.write_bytes(text.encode("utf-8"))
        self.assertEqual(launcher.read_startup_instruction(path), text)
        campaign, _ = self.campaign()
        self.assertTrue(campaign.manual_resume_instruction(text).endswith(text))
        path.write_bytes(text.encode("utf-8") + b"x")
        with self.assertRaisesRegex(ValueError, "262145 UTF-8 bytes.*262144"):
            launcher.read_startup_instruction(path)

    def test_startup_keeps_regular_utf8_nul_and_nofollow_requirements(self):
        path = self.directory / "startup.txt"
        for raw in (b"\xff", b"valid\0", b" "):
            path.write_bytes(raw)
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                launcher.read_startup_instruction(path)
        link = self.directory / "startup-link.txt"
        link.symlink_to(path)
        with self.assertRaises(OSError):
            launcher.read_startup_instruction(link)

    def test_startup_rejects_file_changed_during_read(self):
        path = self.directory / "startup.txt"
        path.write_text("original")
        real_read = os.read
        def change_after_read(fd, size):
            result = real_read(fd, size)
            path.write_text("changed-length")
            return result
        with patch.object(launcher.os, "read", side_effect=change_after_read):
            with self.assertRaisesRegex(ValueError, "changed during read"):
                launcher.read_startup_instruction(path)


class LargeRPCWriteTests(unittest.TestCase):
    def pipe_rpc(self):
        read_fd, write_fd = os.pipe()
        self.addCleanup(os.close, read_fd)
        stream = os.fdopen(write_fd, "wb", buffering=0)
        self.addCleanup(stream.close)
        os.set_blocking(write_fd, False)
        rpc = launcher.RPC.__new__(launcher.RPC)
        rpc.proc = SimpleNamespace(stdin=stream)
        rpc.events = io.StringIO()
        rpc.next_id, rpc.pending_methods = 0, {}
        rpc.responses, rpc.response_contexts = {}, {}
        return rpc, read_fd, write_fd

    def test_short_writes_deliver_one_complete_large_json_line(self):
        rpc, read_fd, _ = self.pipe_rpc()
        value = {"method": "turn/steer", "params": {"text": "\0" * limits.MAX_INSTRUCTION_BYTES}}
        expected = (json.dumps(value) + "\n").encode()
        received = bytearray()
        def consume():
            while len(received) < len(expected):
                part = os.read(read_fd, min(65536, len(expected) - len(received)))
                if not part:
                    return
                received.extend(part)
        reader = threading.Thread(target=consume, daemon=True)
        reader.start()
        real_write = os.write
        try:
            with patch.object(launcher.os, "write", side_effect=lambda fd, view: real_write(fd, view[:4093])) as writes:
                rpc.send(value, deadline=time.monotonic() + 5)
            reader.join(5)
            self.assertFalse(reader.is_alive())
            self.assertGreater(writes.call_count, 1)
            self.assertEqual(received, expected)
        finally:
            rpc.proc.stdin.close()
            reader.join(1)

    def test_blocked_stdin_obeys_call_deadline_and_marks_mutation(self):
        rpc, _, write_fd = self.pipe_rpc()
        while True:
            try:
                os.write(write_fd, b"x" * 65536)
            except BlockingIOError:
                break
        before = time.monotonic()
        with self.assertRaises(launcher.RecoverableFailure) as caught:
            rpc.call("turn/steer", {"text": "large"}, timeout=0.03)
        self.assertLess(time.monotonic() - before, 1)
        self.assertEqual(caught.exception.rpc_method, "turn/steer")
        self.assertTrue(caught.exception.rpc_mutating)
        self.assertFalse(rpc.pending_methods)
        self.assertIsNone(rpc._call_deadline)

    def test_send_time_consumes_existing_response_deadline(self):
        rpc, _, _ = self.pipe_rpc()
        clock, waits = [10.0], []
        def send(value, *, deadline):
            self.assertEqual(deadline, 11.0)
            clock[0] += 0.8
        def pump(timeout):
            waits.append(timeout)
            clock[0] += timeout
        rpc.send, rpc.pump = send, pump
        with patch.object(launcher.time, "monotonic", side_effect=lambda: clock[0]):
            with self.assertRaises(launcher.RecoverableFailure):
                rpc.call("turn/steer", {}, timeout=1)
        self.assertEqual(len(waits), 1)
        self.assertAlmostEqual(waits[0], 0.2)

    def test_partial_failure_preserves_prefix_and_never_replays(self):
        rpc, read_fd, _ = self.pipe_rpc()
        real_write = os.write
        calls = []
        def fail_after_prefix(fd, view):
            calls.append(len(view))
            if len(calls) == 1:
                return real_write(fd, view[:7])
            raise BrokenPipeError("closed test pipe")
        with patch.object(launcher.os, "write", side_effect=fail_after_prefix):
            with self.assertRaises(BrokenPipeError) as caught:
                rpc.call("turn/steer", {"text": "complete text"}, timeout=1)
        self.assertEqual(os.read(read_fd, 7), b'{"id": ')
        self.assertEqual(len(calls), 2)
        self.assertTrue(caught.exception.rpc_mutating)
        self.assertFalse(rpc.pending_methods)


if __name__ == "__main__":
    unittest.main()
