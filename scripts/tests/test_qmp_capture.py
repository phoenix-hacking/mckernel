#!/usr/bin/env python3
"""Real socket protocol tests; no QEMU, application or production acceptance."""
import importlib.util
import itertools
import json
from pathlib import Path
import socket
import threading
import tempfile
import time
import unittest
from unittest.mock import patch

PATH = Path(__file__).resolve().parents[1] / "application-tests/qmp_capture.py"
SPEC = importlib.util.spec_from_file_location("qmp_capture", PATH)
qmp = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(qmp)
EVIDENCE_ROOT = Path(tempfile.mkdtemp(prefix="stability-qmp-tests-"))
EVIDENCE_SEQUENCE = itertools.count(1)
print("QMP_TEST_EVIDENCE " + str(EVIDENCE_ROOT), flush=True)


class Peer:
    def __init__(self, responder, **limits):
        self.client, self.server = socket.socketpair()
        self.server.settimeout(1)
        self.commands, self.errors = [], []
        self.responder = responder
        self.session = qmp.QmpSession(self.client, **limits)
        self.thread = threading.Thread(target=self.serve)
        self.evidence = EVIDENCE_ROOT / str(next(EVIDENCE_SEQUENCE))
        self.evidence.mkdir()

    def serve(self):
        buffer = bytearray()
        try:
            while True:
                raw = self.server.recv(4096)
                if not raw:
                    break
                buffer.extend(raw)
                while b"\n" in buffer:
                    line, _, remainder = buffer.partition(b"\n")
                    buffer = bytearray(remainder)
                    request = json.loads(line)
                    self.commands.append(request["execute"])
                    response = self.responder(request, self)
                    if response is not None:
                        wire = response if type(response) is bytes else (json.dumps(response) + "\n").encode()
                        self.server.sendall(wire)
        except (BrokenPipeError, ConnectionResetError):
            pass
        except BaseException as error:
            self.errors.append(error)
        finally:
            self.server.close()

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, *ignored):
        self.session.close()
        self.thread.join(timeout=2)
        (self.evidence / "record.json").write_text(json.dumps({
            "commands": self.commands, "peer_errors": [repr(error) for error in self.errors],
            "thread_alive_after_join": self.thread.is_alive(),
            "transcript": self.session.transcript, "recovery": self.session.recovery,
            "events": self.session.events, "remaining_buffer_hex": self.session.buffer.hex(),
            "stale_recovery_replies": self.session.stale_recovery_replies,
            "application_acceptance": False}, indent=2) + "\n")
        if self.thread.is_alive():
            raise AssertionError("fake QMP peer did not terminate")
        if self.errors:
            raise AssertionError(repr(self.errors))


def normal(request, peer):
    command = request["execute"]
    if command == "stop":
        peer.paused = True
    if command == "cont":
        peer.paused = False
    result = {}
    if command == "query-status":
        paused = getattr(peer, "paused", False)
        result = {"status": "paused" if paused else "running", "running": not paused}
    return {"return": result, "id": request["id"]}


class QmpTests(unittest.TestCase):
    def test_pause_capture_and_confirm_resume(self):
        with Peer(normal) as peer:
            with peer.session.paused():
                self.assertTrue(peer.paused)
                self.assertEqual(peer.session.execute("capture"), {})
            self.assertTrue(peer.session.recovery[0]["resume_verified"])
        self.assertEqual(peer.commands, ["stop", "query-status", "capture", "cont", "query-status"])

    def test_original_capture_error_survives_successful_resume(self):
        original = ValueError("original physical capture failure")
        with Peer(normal) as peer:
            with self.assertRaises(ValueError) as caught:
                with peer.session.paused():
                    raise original
            self.assertIs(caught.exception, original)
            self.assertTrue(peer.session.recovery[0]["resume_verified"])
            self.assertEqual(peer.session.recovery[0]["original_error"]["message"], str(original))

    def test_rejected_stop_still_attempts_resume(self):
        def respond(request, peer):
            if request["execute"] == "stop":
                return {"error": {"desc": "injected stop rejection"}, "id": request["id"]}
            return normal(request, peer)
        with Peer(respond) as peer:
            with self.assertRaises(qmp.QmpError):
                with peer.session.paused():
                    self.fail("capture body must not run")
            self.assertTrue(peer.session.recovery[0]["resume_verified"])
        self.assertEqual(peer.commands, ["stop", "cont", "query-status"])

    def test_unconfirmed_resume_preserves_both_errors(self):
        def respond(request, peer):
            if request["execute"] == "cont":
                return {"return": {}, "id": request["id"]}
            return normal(request, peer)
        with Peer(respond) as peer:
            with self.assertRaises(qmp.QmpResumeError) as caught:
                with peer.session.paused():
                    raise ValueError("first failure")
            self.assertIsInstance(caught.exception.__cause__, ValueError)
            recovery = peer.session.recovery[0]
            self.assertFalse(recovery["resume_verified"])
            self.assertEqual(recovery["original_error"]["message"], "first failure")
            self.assertIn("resume_error", recovery)

    def test_body_overrun_is_rejected_after_resume(self):
        with Peer(normal) as peer:
            with self.assertRaisesRegex(qmp.QmpError, "capture body exceeded deadline"):
                with peer.session.paused(timeout_seconds=0.1):
                    time.sleep(0.15)
            self.assertTrue(peer.session.recovery[0]["resume_verified"])

    def test_cont_error_still_queries_actual_status(self):
        def respond(request, peer):
            if request["execute"] == "cont":
                return {"error": {"desc": "injected cont rejection"}, "id": request["id"]}
            return normal(request, peer)
        with Peer(respond) as peer:
            with self.assertRaises(qmp.QmpResumeError):
                with peer.session.paused():
                    pass
            self.assertIn("continue_error", peer.session.recovery[0])
            self.assertIn("status_error", peer.session.recovery[0])
        self.assertEqual(peer.commands[-2:], ["cont", "query-status"])

    def test_late_prior_reply_cannot_replace_resume_status(self):
        def respond(request, peer):
            if request["execute"] == "capture":
                time.sleep(0.09)
            return normal(request, peer)
        with Peer(respond, timeout_seconds=0.06) as peer:
            with self.assertRaises(qmp.QmpError):
                with peer.session.paused():
                    peer.session.execute("capture")
            self.assertTrue(peer.session.recovery[0]["resume_verified"])
            self.assertEqual([row["id"] for row in peer.session.stale_recovery_replies], [3])

    def test_malformed_and_wrong_identity_replies_rejected(self):
        for wire in (b'{"return":{},"id":1,"id":1}\n', b'{"return":{},"id":true}\n',
                     b'{"return":{},"id":2}\n', b'{"return":NaN,"id":1}\n',
                     b'{"return":1e999,"id":1}\n'):
            with self.subTest(wire=wire):
                with Peer(lambda request, peer: wire) as peer:
                    with self.assertRaises(qmp.QmpError):
                        peer.session.execute("capture")
                    self.assertTrue(peer.session.transcript)

    def test_event_before_matching_response(self):
        def respond(request, peer):
            return b'{"event":"STOP"}\n' + json.dumps(normal(request, peer)).encode() + b"\n"
        with Peer(respond) as peer:
            self.assertEqual(peer.session.execute("stop"), {})
            self.assertEqual(peer.session.events, [{"event": "STOP"}])

    def test_frame_and_transcript_bounds(self):
        with Peer(lambda request, peer: b"x" * 256, frame_limit=256) as peer:
            with self.assertRaisesRegex(qmp.QmpError, "frame limit"):
                peer.session.execute("capture")
        def respond(request, peer):
            if request["execute"] == "large":
                return {"return": "x" * 180, "id": request["id"]}
            return normal(request, peer)
        with Peer(respond, frame_limit=256, transcript_limit=256) as peer:
            with self.assertRaisesRegex(qmp.QmpError, "ordinary transcript"):
                with peer.session.paused():
                    peer.session.execute("large")
            self.assertTrue(peer.session.recovery[0]["resume_verified"])
            self.assertGreater(peer.session.transcript_bytes, 256)
            self.assertLess(peer.session.transcript_bytes, 2048)

    def test_partial_frame_survives_transcript_cap_during_recovery(self):
        def respond(request, peer):
            if request["execute"] == "large":
                raw = json.dumps({"return": "x" * 180, "id": request["id"]}).encode() + b"\n"
                peer.server.sendall(raw[:120])
                time.sleep(0.02)
                return raw[120:]
            return normal(request, peer)
        with Peer(respond, frame_limit=256, transcript_limit=256) as peer:
            with self.assertRaisesRegex(qmp.QmpError, "ordinary transcript"):
                with peer.session.paused():
                    peer.session.execute("large")
            self.assertTrue(peer.session.recovery[0]["resume_verified"])
            self.assertEqual([row["id"] for row in peer.session.stale_recovery_replies], [3])

    def test_invalid_connect_limits_rejected_before_socket_creation(self):
        with patch.object(qmp.socket, "socket") as factory:
            for timeout in (0, 31, float("inf"), float("nan"), True, "5"):
                with self.subTest(timeout=timeout), self.assertRaises(ValueError):
                    qmp.QmpSession.connect("unused", timeout)
            factory.assert_not_called()

    def test_trickled_frame_cannot_extend_transaction_deadline(self):
        def respond(request, peer):
            peer.server.sendall(b"{")
            for _ in range(20):
                time.sleep(0.02)
                peer.server.sendall(b" ")
            return None
        with Peer(respond, timeout_seconds=0.08) as peer:
            begin = time.monotonic()
            with self.assertRaises(qmp.QmpError):
                peer.session.execute("capture")
            self.assertLess(time.monotonic() - begin, 0.3)


if __name__ == "__main__":
    unittest.main()
