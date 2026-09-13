#!/usr/bin/env python3
"""Synthetic connected-socket tests only. Retain every attempt; no QMP/guest."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import socket
import tempfile
import time
import unittest

SPEC = importlib.util.spec_from_file_location(
    "fault_control", Path(__file__).resolve().parents[1] / "application-tests/fault_control.py")
control = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(control)
NONCE = "0123456789abcdef0123456789abcdef"
DIGEST = "a" * 64
MODE = "prepublish-hard"


def request(sequence, phase, *, mode=MODE, tgid=101, tid=102, ticks=12345):
    # Literal reviewed wire layout, independent of the parser regex/formatter.
    return f"STF1 REQ {NONCE} {sequence} {phase} {mode} {tgid} {tid} {ticks}\n".encode()


def failure(sequence, phase, *, mode=MODE, reason="phase-deadline", error=110):
    return f"STF1 FAIL {NONCE} {sequence} {phase} {mode} 101 102 12345 {reason} {error}\n".encode()


def acknowledgement(sequence, phase, mode=MODE):
    return f"STF1 ACK {NONCE} {sequence} {phase} {mode} 101 102 12345 {DIGEST} CONTINUED\n".encode()


class FaultControlTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="stability-fault-control-"))
        print("RETAINED_FAULT_CONTROL_TEST", self.id(), self.root, flush=True)
        self.index = 0
        self.instances = []

    def tearDown(self):
        # Deliberately retain all inputs, raw output and failure reports.
        for item in self.instances:
            instance, host, peer, calls, expected, ack_bytes, directory = item
            (directory / "expected-rx.bin").write_bytes(expected)
            (directory / "peer-ack.bin").write_bytes(ack_bytes)
            (directory / "callback-calls.json").write_text(json.dumps(calls, sort_keys=True) + "\n")
            try:
                instance.close()
            finally:
                host.close()
                peer.close()

    def make(self, callback=None, *, mode=MODE, **limits):
        self.index += 1
        directory = self.root / str(self.index)
        directory.mkdir()
        host, peer = socket.socketpair()
        peer.setblocking(False)
        calls = []
        def captured(row):
            # No acknowledgment can precede callback completion.
            with self.assertRaises(BlockingIOError):
                peer.recv(1, socket.MSG_PEEK)
            calls.append(dict(row))
            return callback(row, peer) if callback else {"sha256": DIGEST, "continued": True}
        instance = control.FaultControl(host, nonce=NONCE, mode=mode,
                                        capture_root=directory / "capture", capture_phase=captured,
                                        **limits)
        item = [instance, host, peer, calls, bytearray(), bytearray(), directory]
        self.instances.append(item)
        return item

    def send(self, item, data):
        # Test frames fit an ordinary local socket buffer; unexpected short
        # send is a test failure, never hidden by an assumed transfer.
        count = item[2].send(data)
        item[4].extend(data[:count])
        self.assertEqual(count, len(data))

    def poll_frame(self, item):
        deadline = time.monotonic() + 1
        while time.monotonic() < deadline:
            event = item[0].poll(0.02)
            if event is not None:
                return event
        self.fail("bounded synthetic frame not observed")

    def read_ack(self, item, expected):
        data = bytearray()
        deadline = time.monotonic() + 0.5
        while len(data) < len(expected) and time.monotonic() < deadline:
            try:
                part = item[2].recv(len(expected) - len(data))
            except BlockingIOError:
                time.sleep(0.001)
                continue
            if not part:
                break
            data.extend(part)
            item[5].extend(part)
        self.assertEqual(bytes(data), expected)

    def no_ack(self, item):
        with self.assertRaises(BlockingIOError):
            item[2].recv(1, socket.MSG_PEEK)

    def phase(self, item, sequence, phase, mode=MODE):
        self.send(item, request(sequence, phase, mode=mode))
        event = self.poll_frame(item)
        self.assertEqual(event["event"], "phase-collected")
        self.read_ack(item, acknowledgement(sequence, phase, mode))

    def test_terminal_phases_then_later_cleanup_failure_remain_pollable(self):
        item = self.make()
        for number, name in enumerate(("PRE_INPUT", "POST_RET", "QUIET"), 1):
            self.phase(item, number, name)
        self.assertTrue(item[0].report()["normal_phases_complete"])
        self.assertIsNone(item[0].poll(0))
        self.send(item, failure(4, "NEW_ADMISSION", reason="new-admission-oracle", error=71))
        self.poll_frame(item)
        self.read_ack(item, acknowledgement(4, "EMERGENCY_CAPTURED"))
        report = item[0].report()
        self.assertTrue(report["emergency_capture_confirmed"])
        self.assertEqual(report["first_failure"]["reason"], "guest-collection-failure")
        self.assertFalse(report["controller_exit_verified"])
        self.assertFalse(report["application_acceptance"])
        self.assertFalse(report["transport_acceptance"])
        self.assertFalse(report["qmp_provenance_verified"])
        self.assertEqual(report["rx_sha256"], hashlib.sha256(item[4]).hexdigest())
        self.assertEqual(report["tx_sha256"], hashlib.sha256(item[5]).hexdigest())

    def test_recoverable_has_two_normal_phases(self):
        mode = "recoverable-backpressure"
        item = self.make(mode=mode)
        self.phase(item, 1, "PRE_INPUT", mode)
        self.phase(item, 2, "POST_RET", mode)
        self.assertTrue(item[0].report()["normal_phases_complete"])
        self.assertEqual(item[0].report()["ack_count"], 2)
        self.send(item, request(3, "QUIET", mode=mode))
        with self.assertRaisesRegex(control.FaultControlError, "normal-phase-order"):
            self.poll_frame(item)
        self.no_ack(item)

    def test_post_input_explicit_emergency_preserves_reason_errno_identity(self):
        item = self.make()
        self.phase(item, 1, "PRE_INPUT")
        self.send(item, failure(2, "OWNER_TERMINAL", reason="owner-phase-incomplete-or-invalid", error=71))
        self.poll_frame(item)
        self.read_ack(item, acknowledgement(2, "EMERGENCY_CAPTURED"))
        captured = item[3][-1]
        self.assertEqual((captured["kind"], captured["phase"], captured["ack_phase"], captured["errno"]),
                         ("FAIL", "OWNER_TERMINAL", "EMERGENCY_CAPTURED", 71))
        self.assertEqual(item[0].report()["identity"], [101, 102, 12345])

    def test_callback_failure_waits_for_guest_failure_and_never_clears_first_failure(self):
        def callback(row, peer):
            if row["phase"] == "POST_RET" and row["kind"] == "REQ":
                raise RuntimeError("synthetic original capture failure")
            return {"sha256": DIGEST, "continued": True, "observations_status": "FAIL" if row["kind"] == "FAIL" else "COLLECTED"}
        item = self.make(callback)
        self.phase(item, 1, "PRE_INPUT")
        self.send(item, request(2, "POST_RET"))
        self.assertEqual(self.poll_frame(item)["event"], "capture-rejected-no-ack")
        self.no_ack(item)
        original = dict(item[0].report()["first_failure"])
        self.assertTrue(item[0].report()["awaiting_guest_failure"])
        self.send(item, failure(3, "POST_RET"))
        self.poll_frame(item)
        self.read_ack(item, acknowledgement(3, "EMERGENCY_CAPTURED"))
        self.assertEqual(item[0].report()["first_failure"], original)
        self.assertTrue(item[0].report()["emergency_capture_confirmed"])
        self.assertEqual(item[0].report()["normal_acks"], 1)

    def test_failed_emergency_callback_sends_no_ack(self):
        item = self.make(lambda row, peer: {"sha256": DIGEST, "continued": row["kind"] != "FAIL"})
        self.phase(item, 1, "PRE_INPUT")
        self.send(item, failure(2, "INPUT", reason="input-write", error=5))
        self.poll_frame(item)
        self.no_ack(item)
        self.assertTrue(item[0].report()["emergency_seen"])
        self.assertFalse(item[0].report()["emergency_capture_confirmed"])

    def test_unconfirmed_or_malformed_callback_returns_never_ack(self):
        values = [None, [], {"sha256": DIGEST, "continued": 1}, {"sha256": DIGEST, "continued": False},
                  {"sha256": "A" * 64, "continued": True}, {"sha256": "a" * 63, "continued": True},
                  {"sha256": DIGEST, "continued": True, "other": float("nan")},
                  {"sha256": DIGEST, "continued": True, "other": "x" * 4097}]
        for value in values:
            with self.subTest(value=repr(value)[:80]):
                item = self.make(lambda row, peer, result=value: result)
                self.send(item, request(1, "PRE_INPUT"))
                self.poll_frame(item)
                self.no_ack(item)
                self.assertEqual(item[0].report()["ack_count"], 0)
                self.assertEqual(item[0].report()["first_failure"]["reason"], "capture-not-confirmed")

    def test_actual_late_callback_return_is_not_acknowledged(self):
        def delayed(row, peer):
            time.sleep(0.06)
            return {"sha256": DIGEST, "continued": True}
        item = self.make(delayed, capture_timeout_seconds=0.02)
        self.send(item, request(1, "PRE_INPUT"))
        self.poll_frame(item)
        self.no_ack(item)
        self.assertEqual(item[0].report()["first_failure"]["error"], "late-capture-callback")

    def test_initial_malformed_nonce_mode_range_and_phase_have_no_callback(self):
        good = request(1, "PRE_INPUT")
        values = [good.replace(b"STF1", b"STF2"), good.replace(NONCE.encode(), b"a" * 32),
                  good.replace(b"prepublish-hard", b"postpublish-notify"), good.replace(b" 1 PRE", b" 01 PRE"),
                  good.replace(b"101 102", b"2147483648 102"), good.replace(b"12345", b"18446744073709551616"),
                  good.replace(b"\n", b"\r\n"), good.replace(b"PRE_INPUT", b"PRE\x00INPUT"),
                  request(2, "PRE_INPUT"), request(1, "POST_RET"), failure(1, "INPUT")]
        for wire in values:
            with self.subTest(wire=wire):
                item = self.make()
                self.send(item, wire)
                with self.assertRaises(control.FaultControlError):
                    self.poll_frame(item)
                self.no_ack(item)
                self.assertEqual(item[3], [])

    def test_changed_owned_identity_stale_sequence_and_wrong_phase(self):
        values = [request(2, "POST_RET", tgid=103), request(2, "POST_RET", tid=103),
                  request(2, "POST_RET", ticks=12346), request(1, "POST_RET"), request(2, "QUIET")]
        for wire in values:
            with self.subTest(wire=wire):
                item = self.make()
                self.phase(item, 1, "PRE_INPUT")
                self.send(item, wire)
                with self.assertRaises(control.FaultControlError):
                    self.poll_frame(item)
                self.no_ack(item)
                self.assertEqual(len(item[3]), 1)

    def test_failure_phase_sequence_and_repeated_emergency_rejected(self):
        for wire in [failure(3, "INPUT"), failure(2, "NEW_ADMISSION"), failure(2, "INPUT", error=4096)]:
            item = self.make()
            self.phase(item, 1, "PRE_INPUT")
            self.send(item, wire)
            with self.assertRaises(control.FaultControlError):
                self.poll_frame(item)
            self.no_ack(item)
        item = self.make()
        self.phase(item, 1, "PRE_INPUT")
        self.send(item, failure(2, "INPUT"))
        self.poll_frame(item)
        self.read_ack(item, acknowledgement(2, "EMERGENCY_CAPTURED"))
        self.send(item, failure(3, "INPUT"))
        with self.assertRaisesRegex(control.FaultControlError, "frame-after-emergency"):
            self.poll_frame(item)
        self.no_ack(item)

    def test_terminal_and_recovery_failure_phases_cannot_be_exchanged(self):
        for mode, phase in [(MODE, "OWNER_RECOVERY"), ("recoverable-backpressure", "OWNER_TERMINAL")]:
            item = self.make(mode=mode)
            self.phase(item, 1, "PRE_INPUT", mode)
            self.send(item, failure(2, phase, mode=mode))
            with self.assertRaisesRegex(control.FaultControlError, "failure-phase-order"):
                self.poll_frame(item)
            self.no_ack(item)
            self.assertEqual(len(item[3]), 1)

    def test_fragmented_request_requires_final_newline_before_callback(self):
        item = self.make()
        wire = request(1, "PRE_INPUT")
        for chunk in [wire[:8], wire[8:-1]]:
            self.send(item, chunk)
            self.assertIsNone(item[0].poll(0.01))
            self.no_ack(item)
            self.assertEqual(item[3], [])
        self.send(item, b"\n")
        self.poll_frame(item)
        self.read_ack(item, acknowledgement(1, "PRE_INPUT"))

    def test_duplicate_queued_frames_fail_before_callback(self):
        item = self.make()
        self.send(item, request(1, "PRE_INPUT") * 2)
        with self.assertRaisesRegex(control.FaultControlError, "pipelined-or-repeated-frame"):
            self.poll_frame(item)
        self.no_ack(item)
        self.assertEqual(item[3], [])

    def test_duplicate_arriving_during_capture_is_retained_without_ack(self):
        item = None
        def callback(row, peer):
            self.send(item, request(1, "PRE_INPUT"))
            return {"sha256": DIGEST, "continued": True}
        item = self.make(callback)
        self.send(item, request(1, "PRE_INPUT"))
        with self.assertRaisesRegex(control.FaultControlError, "unsolicited-frame-before-ack"):
            self.poll_frame(item)
        self.no_ack(item)
        self.assertEqual(item[0].report()["rx_bytes"], len(item[4]))

    def test_overlong_frame_and_actual_total_raw_byte_limit_fail_explicitly(self):
        item = self.make()
        self.send(item, b"x" * 512)
        with self.assertRaisesRegex(control.FaultControlError, "frame-byte-limit"):
            self.poll_frame(item)
        self.no_ack(item)
        item = self.make()
        # Exercise the actual retained-byte sink at its declared hard bound.
        raw = b"x" * 16385
        item[4].extend(raw)
        with self.assertRaisesRegex(control.FaultControlError, "rx-byte-limit"):
            item[0]._retain_rx(raw)
        report = item[0].report()
        self.assertEqual((report["rx_bytes"], report["socket_bytes_received"], report["rx_discarded_bytes"]), (16384, 16385, 1))
        self.assertFalse(report["received_raw_fully_stored"])
        self.assertEqual((item[6] / "capture/rx.bin").read_bytes(), raw[:16384])
        self.assertEqual(report["rx_sha256"], hashlib.sha256(raw[:16384]).hexdigest())

    def test_interrupted_pre_ack_peek_retries_and_rejects_actual_queued_duplicate(self):
        item = None
        def callback(row, peer):
            self.send(item, request(1, "PRE_INPUT"))
            return {"sha256": DIGEST, "continued": True}
        item = self.make(callback)
        class InterruptedPeek:
            interrupted = False
            def __getattr__(self, name):
                return getattr(item[1], name)
            def recv(self, count, flags=0):
                if flags == socket.MSG_PEEK and not self.interrupted:
                    self.interrupted = True
                    raise InterruptedError("synthetic single interrupted peek")
                return item[1].recv(count, flags)
        adapter = InterruptedPeek()
        item[0].connection = adapter
        self.send(item, request(1, "PRE_INPUT"))
        with self.assertRaisesRegex(control.FaultControlError, "unsolicited-frame-before-ack"):
            self.poll_frame(item)
        self.assertTrue(adapter.interrupted)
        self.no_ack(item)
        self.assertEqual(item[0].report()["rx_bytes"], len(item[4]))

    def test_partial_frame_and_missing_frame_use_actual_deadlines(self):
        item = self.make(frame_timeout_seconds=0.02)
        self.send(item, b"STF1 REQ ")
        self.assertIsNone(item[0].poll(0.01))
        time.sleep(0.03)
        with self.assertRaisesRegex(control.FaultControlError, "partial-frame-deadline"):
            item[0].poll(0.01)
        self.no_ack(item)
        item = self.make(timeout_seconds=0.02)
        time.sleep(0.03)
        with self.assertRaisesRegex(control.FaultControlError, "control-deadline"):
            item[0].poll(0.01)
        self.no_ack(item)

    def test_peer_eof_is_failure_and_caller_socket_ownership_is_preserved(self):
        item = self.make()
        item[2].shutdown(socket.SHUT_WR)
        with self.assertRaisesRegex(control.FaultControlError, "unexpected-control-eof"):
            item[0].poll(0.01)
        item[0].close()
        self.assertGreaterEqual(item[1].fileno(), 0)
        report = json.loads((item[6] / "capture/report.json").read_bytes())
        self.assertTrue(report["protocol_failed"])

    def test_half_closed_peer_after_valid_request_receives_no_ack(self):
        item = self.make()
        self.send(item, request(1, "PRE_INPUT"))
        item[2].shutdown(socket.SHUT_WR)
        with self.assertRaisesRegex(control.FaultControlError, "control-eof-before-ack"):
            self.poll_frame(item)
        self.no_ack(item)
        self.assertEqual(len(item[3]), 1)
        self.assertEqual(item[0].report()["ack_count"], 0)

    def test_invalid_limits_and_existing_capture_rejected(self):
        host, peer = socket.socketpair()
        with host, peer:
            for limit in (True, 0, -1, float("nan"), float("inf"), 301):
                with self.assertRaises(ValueError):
                    control.FaultControl(host, nonce=NONCE, mode=MODE, capture_root=self.root / "unused",
                                         capture_phase=lambda row: {}, timeout_seconds=limit)
            with self.assertRaises(FileExistsError):
                control.FaultControl(host, nonce=NONCE, mode=MODE, capture_root=self.root, capture_phase=lambda row: {})


if __name__ == "__main__":
    unittest.main(verbosity=2)
