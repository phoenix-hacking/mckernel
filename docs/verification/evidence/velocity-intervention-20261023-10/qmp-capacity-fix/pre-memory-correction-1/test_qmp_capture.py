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




class LongCapacityTests(unittest.TestCase):
    """Functional capacity fixtures only: fake sockets and small in-memory caps."""
    @classmethod
    def setUpClass(cls):
        import sys
        root = PATH.parent
        def load(name, filename):
            spec = importlib.util.spec_from_file_location(name, root / filename)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            return module
        with patch.dict(sys.modules, {'qmp_capture': qmp}):
            cls.backend = load('capacity_backend', 'native_diagnostic_backend.py')
        cls.transport = load('capacity_transport', 'long_transport.py')
        cls.diagnostic = load('capacity_diagnostic', 'native_diagnostic.py')

    def backend_for(self, session):
        backend = object.__new__(self.backend.QmpBackend)
        backend.session = session
        backend.negotiated = True
        return backend

    def test_short_defaults_unchanged_and_no_encoded_work(self):
        session = qmp.QmpSession(None)
        self.assertEqual(session.transcript_limit, 8 * 2**20)
        self.assertIsNone(session.transcript_capture_limit)
        self.assertIsNone(session.transcript_record_limit)
        with patch.object(qmp.json, 'dumps', side_effect=AssertionError('short encoded accounting')):
            session._retain('received', b'x')
        self.assertEqual(session.transcript[0]['raw_hex'], '78')

    def test_old_raw_exact_boundary_and_offending_byte_retained(self):
        session = qmp.QmpSession(None, frame_limit=256, transcript_limit=256)
        session._retain('received', b'x' * 256)
        with self.assertRaisesRegex(qmp.QmpError, 'ordinary transcript budget'):
            session._retain('received', b'y')
        self.assertEqual(session.transcript_bytes, 257)
        self.assertEqual(session.transcript[-1]['raw_hex'], '79')

    def test_encoded_exact_boundary_and_one_over_record_retained(self):
        row = {'direction': 'received', 'monotonic': 1.0, 'raw_hex': '78'}
        bound = len(json.dumps([row] * 10, sort_keys=True, allow_nan=False).encode())
        session = qmp.QmpSession(None, frame_limit=256, transcript_limit=256,
                                 transcript_capture_limit=bound)
        with patch.object(qmp.time, 'monotonic', return_value=1.0):
            for unused in range(10):
                session._retain('received', b'x')
            self.assertEqual(session.transcript_serialized_bytes, bound)
            with self.assertRaisesRegex(qmp.QmpError, 'ordinary encoded'):
                session._retain('received', b'x')
        self.assertEqual(len(session.transcript), 11)
        serialized = self.diagnostic._qmp_transcript_bytes(session.transcript,
                      {'qmp_bytes': session.transcript_serialized_bytes})
        self.assertEqual(len(serialized), session.transcript_serialized_bytes)
        with self.assertRaisesRegex(self.diagnostic.DiagnosticError, 'QMP transcript capture limit'):
            self.diagnostic._qmp_transcript_bytes(session.transcript, {'qmp_bytes': len(serialized)-1})
        self.assertEqual(json.loads(serialized), session.transcript)

    def test_tiny_fragment_row_limit_and_terminal_record_reserve(self):
        session = qmp.QmpSession(None, frame_limit=256, transcript_limit=2**20,
                                 transcript_capture_limit=2 * 2**20, transcript_record_limit=3)
        for unused in range(3):
            session._retain('received', b'x')
        with self.assertRaisesRegex(qmp.QmpError, 'ordinary transcript record'):
            session._retain('received', b'x')
        self.assertEqual(len(session.transcript), 4)
        session.recovering = True
        for unused in range(4095):
            session._retain('received', b'x')
        self.assertEqual(len(session.transcript), 4099)
        with self.assertRaisesRegex(qmp.QmpError, 'recovery record limit'):
            session._retain('received', b'x')
        self.assertEqual(len(session.transcript), 4099)

    def test_raw_hard_reserve_cannot_be_widened_by_recovery(self):
        session = qmp.QmpSession(None, frame_limit=256, transcript_limit=256)
        session.recovering = True
        with self.assertRaisesRegex(qmp.QmpError, 'transcript limit exceeded'):
            session._retain('received', b'x' * (2 * 2**20 + 257))
        self.assertEqual(session.transcript, [])

    def test_encoded_hard_reserve_and_invalid_limits(self):
        session = qmp.QmpSession(None, frame_limit=256, transcript_limit=256,
                                 transcript_capture_limit=512)
        session.recovering = True
        # Scale only the reserve constant to exercise the exact hard bound
        # without a multi-megabyte record fixture.
        with patch.object(qmp, 'RECOVERY_CAPTURE_BYTES', 64):
            with self.assertRaisesRegex(qmp.QmpError, 'encoded transcript recovery'):
                session._retain('received', b'x' * 300)
        self.assertEqual(session.transcript, [])
        for kwargs in ({'transcript_record_limit': True}, {'transcript_record_limit': 1048577},
                       {'transcript_capture_limit': True}, {'transcript_capture_limit': 129 * 2**20}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                qmp.QmpSession(None, **kwargs)

    def test_terminal_quit_after_ordinary_raw_exhaustion_consumes_reserved_control(self):
        def respond(request, peer):
            if request['execute'] == 'large':
                return {'return': 'x' * 180, 'id': request['id']}
            return normal(request, peer)
        with Peer(respond, frame_limit=256, transcript_limit=256) as peer:
            peer.session._retain('received', b'x' * 50)
            with self.assertRaisesRegex(qmp.QmpError, 'ordinary transcript budget'):
                peer.session.execute('large')
            original_rows = len(peer.session.transcript)
            self.backend_for(peer.session).terminate(timeout=1)
            self.assertFalse(peer.session.recovering)
            self.assertGreater(len(peer.session.transcript), original_rows)
            self.assertEqual([r['id'] for r in peer.session.stale_recovery_replies], [1])
        self.assertEqual(peer.commands, ['large', 'quit'])

    def test_terminal_quit_after_encoded_exhaustion_and_state_restore_on_error(self):
        with Peer(normal, frame_limit=256, transcript_limit=256,
                  transcript_capture_limit=512) as peer:
            with self.assertRaisesRegex(qmp.QmpError, 'ordinary encoded'):
                while True:
                    peer.session._retain('received', b'x')
            backend = self.backend_for(peer.session)
            backend.terminate(timeout=1)
            self.assertFalse(peer.session.recovering)
            with patch.object(backend, '_execute', side_effect=qmp.QmpError('terminal rejected')):
                with self.assertRaisesRegex(qmp.QmpError, 'terminal rejected'):
                    backend.terminate(timeout=1)
            self.assertFalse(peer.session.recovering)
        self.assertEqual(peer.commands, ['quit'])

    def test_long_factory_profile_propagation_and_profile_drift_rejection(self):
        profile = self.transport.TRANSPORT
        with patch.object(self.backend, 'QmpBackend') as factory:
            self.backend.qmp_factory('/not-opened', long_profile=profile)(timeout=1)
            self.assertEqual(factory.call_args.kwargs['transcript_limit'], 32 * 2**20)
            self.assertEqual(factory.call_args.kwargs['transcript_capture_limit'], 128 * 2**20)
            self.assertEqual(factory.call_args.kwargs['transcript_record_limit'], 1048576)
            factory.reset_mock()
            self.backend.qmp_factory('/not-opened')(timeout=1)
            self.assertNotIn('transcript_limit', factory.call_args.kwargs)
        altered = dict(profile, qmp_bytes=profile['qmp_bytes']+1)
        with self.assertRaisesRegex(ValueError, 'exact explicit long QMP profile'):
            self.backend.qmp_factory('/not-opened', long_profile=altered)

    def test_full_7800_second_unchanged_cadence_fits_all_finite_caps(self):
        profile = self.transport.TRANSPORT
        polls = int(profile['inner_seconds'] / 0.05) + 64
        # Budget each normal query/status pair at192raw bytes, plus1MiB
        # greeting/startup allowance; metadata at96bytes for each of2rows.
        raw = polls * 192 + 2**20
        encoded = 2 * raw + polls * 2 * 96 + 2
        self.assertLess(raw, profile['qmp_raw_bytes'])
        self.assertLess(encoded, profile['qmp_ordinary_capture_bytes'])
        self.assertLess(polls * 2, profile['qmp_record_limit'])
        self.assertGreater(profile['qmp_record_limit'], polls * 2 * 3)
        self.assertEqual(profile['qmp_recovery_bytes'], qmp.RECOVERY_BYTES)
        self.assertEqual(profile['qmp_recovery_capture_bytes'], qmp.RECOVERY_CAPTURE_BYTES)
        self.assertEqual(profile['qmp_recovery_records'], qmp.RECOVERY_RECORDS)
        self.assertEqual(profile['qmp_bytes'], profile['qmp_ordinary_capture_bytes'] + profile['qmp_recovery_capture_bytes'])
        total = profile['serial_bytes'] + profile['qmp_bytes'] + 3 * profile['other_stream_bytes'] + profile['metadata_bytes']
        self.assertLess(total, profile['shared_capture_bytes'])
        self.assertEqual(profile['logical_growth_bytes'], 4224 * 2**20)
        self.assertEqual(profile['file_bytes'], 384 * 2**20)
        self.assertEqual(profile['producer']['work_ns'], 3600 * 10**9)
        self.assertEqual(profile['producer']['wall_ns'], 7200 * 10**9)
        sample = {'execute': 'query-status', 'id': polls}
        request = (json.dumps(sample, separators=(',', ':')) + '\n').encode()
        response = (json.dumps({'return': {'status': 'running', 'running': True, 'singlestep': False}, 'id': polls})+'\r\n').encode()
        self.assertLessEqual(len(request) + len(response), 192)

    def test_exact_interpreter_row_memory_model(self):
        import sys
        row = json.loads(json.dumps({'direction': 'received', 'monotonic': time.monotonic(), 'raw_hex': '78'}))
        # Include dict, distinct decoded keys, values, list reference; exclude
        # hex payload characters, separately bounded by2*34MiB for allrows.
        overhead = (sys.getsizeof(row) + sum(sys.getsizeof(k) for k in row) +
                    sum(sys.getsizeof(v) for v in row.values()) - len(row['raw_hex']) + 8)
        self.assertLessEqual(overhead, 512)
        encoded_overhead = len(json.dumps(row, sort_keys=True).encode()) - len(row['raw_hex'])
        self.assertLessEqual(encoded_overhead, 96)


if __name__ == '__main__':
    unittest.main()
