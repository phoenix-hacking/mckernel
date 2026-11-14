"""Instruction capacity regressions: temporary files, fake RPC and anonymous pipes."""
import hashlib
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import threading
import time
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import run_os_goal as launcher


# The decoded text exceeds both the previous 256 KiB proposal and 2 MiB records.
# JSON escaping also expands this message substantially without changing its text.
LARGE_TEXT = "λ🙂\0\n" * 262145


class InstructionQueueTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix="os-goal-unlimited-queue-")
        self.addCleanup(temp.cleanup)
        self.directory = Path(temp.name)
        self.initial = {"schema_version": 1, "thread_id": "saved-root",
                        "goal": {"status": "blocked"}, "retained_hold": "unchanged"}
        launcher.atomic_json(self.directory / "state.json", self.initial)

    def campaign(self, *, blocked=False):
        # Construct only the existing queue consumer; no server or resource work.
        campaign = launcher.Campaign.__new__(launcher.Campaign)
        campaign.directory = self.directory
        campaign.args = SimpleNamespace(repair_agent_failures=True)
        campaign.state = dict(self.initial)
        campaign.controlled = True
        campaign.checkpoint_requested = campaign.stop_now = False
        campaign.stop_reason = None
        campaign.goal = {"status": "blocked" if blocked else "active"}
        campaign.active = {} if blocked else {"saved-root": "current-turn"}
        campaign.notices = []
        campaign.output = SimpleNamespace(notice=campaign.notices.append)
        campaign.save = lambda **fields: campaign.state.update(fields)
        campaign.rpc = SimpleNamespace(call=Mock(return_value={
            "turn": {"id": "new-instruction-turn", "status": "inProgress"}}))
        return campaign

    def pending(self, ident):
        return self.directory / "instructions/pending" / (ident + ".json")

    def test_complete_ascii_and_utf8_messages_exceed_previous_payload_caps(self):
        for text in ("x" * 8193, "λ🙂" * 50000, LARGE_TEXT):
            with self.subTest(utf8_bytes=len(text.encode("utf-8"))):
                ident = launcher.queue_instruction(self.directory, text)
                self.assertEqual(launcher._read_private_json(self.pending(ident))["text"], text)
        self.assertGreater(len(LARGE_TEXT.encode("utf-8")), 2 * 1024 * 1024)
        self.assertEqual(json.loads((self.directory / "state.json").read_bytes()), self.initial)

    def test_invalid_or_empty_text_still_refused_before_queue_creation(self):
        for text in (None, 123, "", " \t\n", "\ud800"):
            with self.subTest(text=repr(text)), self.assertRaises(ValueError):
                launcher.queue_instruction(self.directory, text)
        self.assertFalse((self.directory / "instructions").exists())

    def test_large_source_bound_message_is_idempotent_before_and_after_delivery(self):
        source_id = "github:owner/repo:1:123"
        ident = launcher.queue_instruction(self.directory, LARGE_TEXT, source_id=source_id)
        pending = self.pending(ident)
        registry = self.directory / "instructions/sources" / (ident[7:] + ".json")
        before = pending.read_bytes(), registry.read_bytes()
        self.assertGreater(len(before[0]), 2 * 1024 * 1024)
        item = launcher._read_private_json(pending)
        self.assertEqual(item["source_id"], source_id)
        self.assertEqual(item["text_sha256"], hashlib.sha256(LARGE_TEXT.encode("utf-8")).hexdigest())
        self.assertEqual(launcher._read_private_json(registry)["item"], item)
        self.assertEqual(launcher.queue_instruction(self.directory, LARGE_TEXT, source_id=source_id), ident)
        self.assertEqual((pending.read_bytes(), registry.read_bytes()), before)
        campaign = self.campaign()
        campaign.deliver_instruction()
        self.assertEqual(launcher.queue_instruction(self.directory, LARGE_TEXT, source_id=source_id), ident)
        campaign.deliver_instruction()
        self.assertEqual(campaign.rpc.call.call_count, 1)
        self.assertFalse(pending.exists())
        self.assertEqual(registry.read_bytes(), before[1])
        with self.assertRaisesRegex(ValueError, "content changed"):
            launcher.queue_instruction(self.directory, LARGE_TEXT + "changed", source_id=source_id)

    def test_large_enqueue_intent_recovers_without_duplicate_source_messages(self):
        source_id = "github:owner/repo:1:124"
        atomic_json = launcher.atomic_json
        def fail_pending(path, value):
            if path.parent.name == "pending":
                raise OSError("simulated storage interruption")
            atomic_json(path, value)
        with patch.object(launcher, "atomic_json", side_effect=fail_pending):
            with self.assertRaisesRegex(OSError, "storage interruption"):
                launcher.queue_instruction(self.directory, LARGE_TEXT, source_id=source_id)
        ident = launcher.queue_instruction(self.directory, LARGE_TEXT, source_id=source_id)
        self.assertEqual(launcher._read_private_json(self.pending(ident))["text"], LARGE_TEXT)
        self.assertEqual(len(list(self.pending(ident).parent.glob("*.json"))), 1)
        self.assertEqual(launcher.queue_instruction(self.directory, LARGE_TEXT, source_id=source_id), ident)

    def test_full_large_message_reaches_active_and_blocked_coordinator_once(self):
        for blocked in (False, True):
            with self.subTest(blocked=blocked):
                campaign = self.campaign(blocked=blocked)
                original_goal = dict(campaign.goal)
                ident = launcher.queue_instruction(self.directory, LARGE_TEXT)
                campaign.deliver_instruction()
                campaign.deliver_instruction()
                campaign.rpc.call.assert_called_once()
                method, params = campaign.rpc.call.call_args.args
                self.assertEqual(method, "turn/start" if blocked else "turn/steer")
                self.assertEqual(params["threadId"], "saved-root")
                self.assertEqual(params["input"], [{"type": "text", "text":
                    "Live user instruction " + ident + ":\n" + LARGE_TEXT}])
                if not blocked:
                    self.assertEqual(params["expectedTurnId"], "current-turn")
                receipt = self.directory / "instructions/delivered" / (ident + ".json")
                self.assertEqual(launcher._read_private_json(receipt)["status"], "accepted_by_server")
                self.assertEqual(campaign.goal, original_goal)
                self.assertEqual(campaign.state["retained_hold"], "unchanged")
                self.assertFalse(self.pending(ident).exists())
                self.assertFalse((self.directory / "instructions/sending" / receipt.name).exists())

    def test_large_failed_mutation_retains_sending_and_is_never_replayed(self):
        campaign = self.campaign()
        ident = launcher.queue_instruction(self.directory, LARGE_TEXT)
        campaign.rpc.call.side_effect = launcher.RecoverableFailure("send deadline exhausted")
        campaign.deliver_instruction()
        campaign.deliver_instruction()
        campaign.rpc.call.assert_called_once()
        sending = self.directory / "instructions/sending" / (ident + ".json")
        self.assertEqual(launcher._read_private_json(sending)["text"], LARGE_TEXT)
        self.assertEqual(campaign.state["last_instruction"]["status"], "delivery_uncertain")
        self.assertEqual(campaign.state["transport_uncertain"]["method"], "turn/steer")
        self.assertTrue(campaign.stop_now)
        self.assertEqual(campaign.goal, {"status": "active"})

    def test_existing_stop_and_checkpoint_gates_retain_large_pending_bytes(self):
        campaign = self.campaign()
        ident = launcher.queue_instruction(self.directory, LARGE_TEXT)
        before = self.pending(ident).read_bytes()
        for gate in ("stop_reason", "checkpoint_requested", "controlled"):
            with self.subTest(gate=gate):
                old = getattr(campaign, gate)
                setattr(campaign, gate, "retained_hold" if gate == "stop_reason" else gate == "checkpoint_requested")
                campaign.deliver_instruction()
                setattr(campaign, gate, old)
                self.assertEqual(self.pending(ident).read_bytes(), before)
                campaign.rpc.call.assert_not_called()

    def test_source_id_validation_remains_separate_from_message_size(self):
        for source_id in ("", 123, "s" * 513):
            with self.subTest(source_id=repr(source_id)), self.assertRaisesRegex(ValueError, "source ID"):
                launcher.queue_instruction(self.directory, LARGE_TEXT, source_id=source_id)
        self.assertFalse(list((self.directory / "instructions/pending").glob("*.json")))


class InstructionReaderTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix="os-goal-unlimited-read-")
        self.addCleanup(temp.cleanup)
        self.directory = Path(temp.name)
        self.path = self.directory / "instruction.json"

    def test_large_private_json_handles_short_reads_without_truncation(self):
        launcher.atomic_json(self.path, {"text": LARGE_TEXT})
        real_read = os.read
        with patch.object(launcher.os, "read", side_effect=lambda fd, size: real_read(fd, min(size, 32767))):
            self.assertEqual(launcher._read_private_json(self.path), {"text": LARGE_TEXT})

    def test_private_json_requires_regular_owned_single_link_object(self):
        launcher.atomic_json(self.path, {"text": "valid"})
        link = self.directory / "link.json"
        link.symlink_to(self.path)
        with self.assertRaises(OSError):
            launcher._read_private_json(link)
        fifo = self.directory / "fifo.json"
        os.mkfifo(fifo)
        with self.assertRaisesRegex(ValueError, "regular file"):
            launcher._read_private_json(fifo)
        owner = os.getuid()
        with patch.object(launcher.os, "getuid", return_value=owner + 1):
            with self.assertRaisesRegex(ValueError, "owner-controlled"):
                launcher._read_private_json(self.path)
        hardlink = self.directory / "hardlink.json"
        os.link(self.path, hardlink)
        with self.assertRaisesRegex(ValueError, "single-link"):
            launcher._read_private_json(self.path)
        hardlink.unlink()
        self.path.write_text("[]", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "object"):
            launcher._read_private_json(self.path)
        self.path.write_bytes('{"text":"unsupported encoding"}'.encode("utf-16"))
        with self.assertRaises(UnicodeDecodeError):
            launcher._read_private_json(self.path)

    def test_startup_reads_complete_large_utf8_and_keeps_manual_resume_text(self):
        text = "λ🙂\n" * 400000
        self.assertGreater(len(text.encode("utf-8")), 2 * 1024 * 1024)
        self.path.write_bytes(text.encode("utf-8"))
        self.assertEqual(launcher.read_startup_instruction(self.path), text)
        campaign = launcher.Campaign.__new__(launcher.Campaign)
        campaign.state = {}
        campaign.prior_policy_failure = None
        campaign.log_dir = self.directory / "current-invocation"
        self.assertTrue(campaign.manual_resume_instruction(text).endswith(text))

    def test_startup_keeps_regular_utf8_nonempty_nul_and_nofollow_validation(self):
        for raw in (b"\xff", b"valid\0", b" \t\n"):
            self.path.write_bytes(raw)
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                launcher.read_startup_instruction(self.path)
        link = self.directory / "startup-link"
        link.symlink_to(self.path)
        with self.assertRaises(OSError):
            launcher.read_startup_instruction(link)
        fifo = self.directory / "startup-fifo"
        os.mkfifo(fifo)
        with self.assertRaisesRegex(ValueError, "regular file"):
            launcher.read_startup_instruction(fifo)

    def test_changed_startup_and_private_json_are_refused(self):
        for reader in (launcher.read_startup_instruction, launcher._read_private_json):
            self.path.write_text('{"text":"original"}', encoding="utf-8")
            real_read = os.read
            changed = False
            def change_after_read(fd, size):
                nonlocal changed
                raw = real_read(fd, size)
                if not changed:
                    changed = True
                    self.path.write_text('{"text":"changed length"}', encoding="utf-8")
                return raw
            with self.subTest(reader=reader.__name__), patch.object(launcher.os, "read", side_effect=change_after_read):
                with self.assertRaisesRegex(ValueError, "changed during read"):
                    reader(self.path)


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
        value = {"method": "turn/steer", "params": {"text": LARGE_TEXT}}
        expected = (json.dumps(value) + "\n").encode("utf-8")
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

    def test_partial_send_timeout_keeps_mutating_hold_and_disables_the_channel(self):
        rpc, read_fd, _ = self.pipe_rpc()
        real_write = os.write
        with patch.object(launcher.os, "write", side_effect=lambda fd, view: real_write(fd, view[:7])) as writes:
            with patch.object(launcher.time, "monotonic", side_effect=[0.0, 0.0, 2.0]):
                with self.assertRaises(launcher.RecoverableFailure) as caught:
                    rpc.call("turn/steer", {"text": LARGE_TEXT}, timeout=1)
            self.assertEqual(str(caught.exception), "App-server request timed out: turn/steer")
            self.assertEqual(os.read(read_fd, 7), b'{"id": ')
            # Retain the original uncertain request; append no subsequent line.
            with self.assertRaises(launcher.RecoverableFailure) as repeated:
                rpc.call("thread/goal/get", {}, timeout=1)
            self.assertIs(repeated.exception, caught.exception)
            self.assertEqual(writes.call_count, 1)
        campaign = launcher.Campaign.__new__(launcher.Campaign)
        campaign.state = {"thread_id": "saved-root", "worker_start": "retained-owner"}
        record = campaign.transport_error_record(caught.exception)
        self.assertEqual(record["class"], "rpc_timeout")
        self.assertEqual(record["method"], "turn/steer")
        self.assertTrue(record["mutating"])
        self.assertTrue(record["channel_unusable"])
        campaign.state["transport_failure"] = record
        campaign.controlled, campaign.stopping = True, False
        campaign.rpc = SimpleNamespace(call=Mock())
        campaign.save = lambda **fields: campaign.state.update(fields)
        campaign.stop()
        campaign.rpc.call.assert_not_called()
        self.assertFalse(campaign.state["cleanup_verified"])
        self.assertFalse(rpc.pending_methods)

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

    def test_large_response_frame_is_decoded_without_an_application_byte_cap(self):
        rpc = launcher.RPC.__new__(launcher.RPC)
        text = "x" * (32 * 1024 * 1024 + 1)
        rpc.buffer = (json.dumps({"id": 1, "result": {"text": text}}) + "\n").encode("utf-8")
        rpc.pump_stderr = lambda: None
        rpc.pending_methods, rpc.responses, rpc.response_contexts = {}, {}, {}
        rpc.account_receive_sequence = 0
        rpc.pump()
        self.assertEqual(rpc.responses[1]["result"]["text"], text)
        self.assertEqual(rpc.buffer, b"")


if __name__ == "__main__":
    unittest.main()
