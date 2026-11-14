#!/usr/bin/env python3
"""Actual Python receiver/gate integration only; every attempt stays in TMPDIR."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import socket
import struct
import tempfile
import threading
import time
import traceback
import unittest
from unittest import mock


HERE = Path(__file__).resolve().parent


def imported(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


runner = imported("gate_test_actual_runner", HERE / "run_stability_transport_guest.py")
receiver = imported("gate_test_actual_receiver", HERE / "fixtures/stability-artifact-export/receiver.py")
NONCE = "0123456789abcdef0011223344556677"
SOURCE_ROOT = "/stability"
BINARY = b"\x00\xa5\xff\nSTAF0001\r\x00"


# Independent literal STAF v1 layouts. Do not import parser/gate constants or
# produce wire/expected acknowledgments by calling their formatting code.
def metadata(mode, inode, size=0):
    return struct.pack("<8Q", mode, 31, inode, size, 11, 22, 33, 44)


def frame(kind, path=b"", data=b""):
    return struct.pack("<IIQ", kind, len(path), len(data)) + path + data


def start():
    return (struct.pack("<8sII16sIIII", b"STAF0001", 1, 48, bytes.fromhex(NONCE),
                        256, 16777216, 1024, 0)
            + frame(4, b"/stability", metadata(0o40700, 7)))


def file_frame(path, content, inode):
    return frame(2, path, metadata(0o100640, inode, len(content)) + content)


def end(entries, directories, files, content_bytes):
    return frame(3, data=struct.pack("<4Q", entries, directories, files, content_bytes))


def valid_tree():
    return (start() + frame(1, b"nested", metadata(0o40755, 8))
            + file_frame(b"nested/bytes.bin", BINARY, 9)
            + file_frame(b"empty", b"", 10) + end(3, 1, 2, len(BINARY)))


def expected_ack(wire, manifest_bytes, *, status, entries, content_bytes):
    return struct.pack("<8s16sIIQQ32s32s", b"STAA0001", bytes.fromhex(NONCE),
                       status, 0, content_bytes, entries, hashlib.sha256(wire).digest(),
                       hashlib.sha256(manifest_bytes).digest())


class ExportAckGateTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="stability-export-ack-gate-"))
        print("RETAINED_EXPORT_ACK_GATE_TEST", self.id(), self.root, flush=True)
        self.sessions = []
        self.fsyncs = []
        self.addCleanup(lambda: self.retain("actual-fsync-completions.json", self.fsyncs))
        rows = []
        for path in (Path(__file__).resolve(), HERE / "run_stability_transport_guest.py",
                     HERE / "fixtures/stability-artifact-export/receiver.py"):
            data = path.read_bytes()
            (self.root / ("input-" + path.name)).write_bytes(data)
            rows.append({"path": str(path), "size": len(data),
                         "sha256": hashlib.sha256(data).hexdigest()})
        self.retain("case.json", {"case": self.id(), "inputs": rows,
                    "scope": "synthetic-connected-socket-Python-infrastructure-only",
                    "automatic_deletion": False, "application_acceptance": False,
                    "transport_acceptance": False})

    def retain(self, name, value):
        (self.root / name).write_text(json.dumps(value, sort_keys=True, allow_nan=False) + "\n")

    def session(self):
        host, peer = socket.socketpair()
        peer.settimeout(2)
        item = {"host": host, "peer": peer, "gate": runner.ExportAckGate(host),
                "thread": None, "result": None, "error": None, "ack": bytearray(),
                "finished_ns": None, "capture": self.root / "capture"}
        self.sessions.append(item)
        return item

    def capture(self, wire, *, timeout_seconds=3):
        item = self.session()
        (self.root / "expected-wire.bin").write_bytes(wire)
        self.retain("limits.json", {"receiver_timeout_seconds": timeout_seconds,
                                   "test_worker_join_seconds": 4})

        def collect():
            try:
                item["result"] = receiver.receive(item["gate"], item["capture"],
                                                   SOURCE_ROOT, NONCE, timeout_seconds)
            except BaseException as exc:
                item["error"] = {"type": type(exc).__name__, "message": str(exc),
                                 "traceback": traceback.format_exc()}
            finally:
                item["finished_ns"] = time.monotonic_ns()

        item["thread"] = threading.Thread(target=collect, daemon=True)
        item["thread"].start()
        item["peer"].sendall(wire)
        item["peer"].setblocking(False)
        return item

    def pending(self, item):
        self.assertTrue(item["gate"].pending.wait(2), "actual receiver never reached gated ACK")
        seen = time.monotonic_ns()
        self.assertFalse(item["gate"].allowed.is_set())
        self.assertTrue(item["thread"].is_alive(), item["error"])
        self.assertIsNone(item["result"])
        self.no_ack(item)
        manifest_bytes = (item["capture"] / "manifest.json").read_bytes()
        self.assertTrue(manifest_bytes.endswith(b"\n"))
        self.retain("pending-observation.json", {"observed_monotonic_ns": seen,
                    "manifest_sha256": hashlib.sha256(manifest_bytes).hexdigest(),
                    "wire_sha256": hashlib.sha256((item["capture"] / "wire.bin").read_bytes()).hexdigest(),
                    "peer_ack_bytes_observed": 0, "gate_allowed": False})
        return manifest_bytes, seen

    def no_ack(self, item):
        with self.assertRaises(BlockingIOError):
            item["peer"].recv(1, socket.MSG_PEEK)

    def join(self, item):
        item["thread"].join(4)
        self.assertFalse(item["thread"].is_alive(), "receiver did not finish within test bound")
        self.assertIsNone(item["error"], item["error"])
        self.assertIsNotNone(item["result"])
        return item["result"]

    def read_ack(self, item, expected):
        self.assertEqual(len(expected), 112)
        (self.root / "expected-ack.bin").write_bytes(expected)
        deadline = time.monotonic() + 2
        while len(item["ack"]) < 112 and time.monotonic() < deadline:
            try:
                data = item["peer"].recv(113 - len(item["ack"]))
            except BlockingIOError:
                time.sleep(0.001)
                continue
            if not data:
                break
            item["ack"].extend(data)
        self.assertEqual(bytes(item["ack"]), expected)
        self.no_ack(item)

    def test_actual_receiver_constructor_forwards_socket_interface(self):
        item = self.session()
        self.assertTrue(item["host"].getblocking())
        actual = receiver.Receiver(item["gate"], item["capture"], SOURCE_ROOT, NONCE, 1)
        try:
            self.assertFalse(item["host"].getblocking())
            self.assertEqual(item["gate"].fileno(), item["host"].fileno())
            item["peer"].sendall(b"probe")
            self.assertEqual(item["gate"].recv(1, socket.MSG_PEEK), b"p")
            self.assertEqual(item["gate"].recv(5), b"probe")
            self.assertFalse(item["gate"].pending.is_set())
            self.assertFalse(item["gate"].allowed.is_set())
        finally:
            actual.close()
        # The receiver closes only artifacts, not the supplied connected socket.
        self.assertGreaterEqual(item["host"].fileno(), 0)
        self.assertEqual((item["capture"] / "wire.bin").read_bytes(), b"")

    def test_complete_tree_ack_held_after_fsync_then_released_exactly(self):
        wire = valid_tree()
        fsyncs = self.fsyncs
        real_fsync = os.fsync

        def observe_real_fsync(fd):
            st = os.fstat(fd)
            real_fsync(fd)
            fsyncs.append({"device": st.st_dev, "inode": st.st_ino,
                           "completed_monotonic_ns": time.monotonic_ns()})

        # Observe successful real fsync calls; do not replace their behavior.
        with mock.patch.object(receiver.os, "fsync", side_effect=observe_real_fsync):
            item = self.capture(wire)
            manifest_bytes, pending_ns = self.pending(item)
            manifest = json.loads(manifest_bytes)
            self.assertEqual(manifest["status"], "CAPTURE_COMPLETE")
            self.assertEqual((item["capture"] / "wire.bin").read_bytes(), wire)
            self.assertEqual((item["capture"] / "files/nested/bytes.bin").read_bytes(), BINARY)
            self.assertEqual((item["capture"] / "files/empty").read_bytes(), b"")
            for path in (item["capture"] / "manifest.json", item["capture"] / "wire.bin",
                         item["capture"] / "files/nested/bytes.bin", item["capture"], self.root):
                st = path.stat()
                self.assertTrue(any(row["device"] == st.st_dev and row["inode"] == st.st_ino
                                    and row["completed_monotonic_ns"] <= pending_ns for row in fsyncs), path)
            expected = expected_ack(wire, manifest_bytes, status=0, entries=3, content_bytes=len(BINARY))
            self.assertEqual((item["capture"] / "ack.bin").read_bytes(), expected)
            time.sleep(0.025)
            self.no_ack(item)
            self.assertTrue(item["thread"].is_alive())
            item["gate"].allowed.set()
            self.read_ack(item, expected)
            result = self.join(item)
        self.retain("actual-fsync-completions.json", fsyncs)
        self.assertTrue(result["ok"])
        self.assertEqual(result["ack"]["bytes_sent"], 112)
        self.assertTrue(result["ack"]["ack_complete"])
        self.assertTrue(result["ack"]["within_deadline"])
        self.assertIsNone(result["ack"]["error"])
        self.assertFalse(result["manifest"]["application_acceptance"])
        self.assertFalse(result["manifest"]["transport_fault_acceptance"])

    def test_closed_gate_real_deadline_fails_without_ack_even_if_opened_late(self):
        wire = start() + end(0, 0, 0, 0)
        item = self.capture(wire, timeout_seconds=0.5)
        manifest_bytes, _ = self.pending(item)
        self.assertEqual(json.loads(manifest_bytes)["status"], "CAPTURE_COMPLETE")
        result = self.join(item)
        self.no_ack(item)
        self.assertFalse(result["ok"])
        self.assertFalse(result["ack"]["ack_complete"])
        self.assertEqual(result["ack"]["bytes_sent"], 0)
        self.assertFalse(result["ack"]["within_deadline"])
        self.assertIn("host-deadline", result["ack"]["error"])
        # Opening after the real receive/ACK deadline cannot restart the worker.
        item["gate"].allowed.set()
        time.sleep(0.01)
        self.no_ack(item)
        self.assertEqual(item["ack"], b"")
        self.assertEqual((item["capture"] / "wire.bin").read_bytes(), wire)

    def test_malformed_tree_failure_ack_remains_failure_when_gate_opens(self):
        # Actual retained file count is one; independent END deliberately says two.
        wire = start() + file_frame(b"partial.bin", BINARY, 9) + end(2, 0, 2, len(BINARY))
        item = self.capture(wire)
        manifest_bytes, _ = self.pending(item)
        manifest = json.loads(manifest_bytes)
        self.assertEqual(manifest["status"], "FAIL")
        self.assertIn("final-manifest-count-mismatch", manifest["error"])
        self.assertEqual((item["capture"] / "wire.bin").read_bytes(), wire)
        self.assertEqual((item["capture"] / "files/partial.bin").read_bytes(), BINARY)
        expected = expected_ack(wire, manifest_bytes, status=1, entries=1, content_bytes=len(BINARY))
        self.assertEqual((item["capture"] / "ack.bin").read_bytes(), expected)
        item["gate"].allowed.set()
        self.read_ack(item, expected)
        result = self.join(item)
        self.assertFalse(result["ok"])
        self.assertEqual(result["manifest"]["status"], "FAIL")
        self.assertEqual(result["ack"]["ack_status"], 1)
        self.assertTrue(result["ack"]["ack_complete"])
        self.assertIsNone(result["ack"]["error"])

    def tearDown(self):
        for index, item in enumerate(self.sessions):
            peer = item["peer"]
            peer.setblocking(False)
            # Preserve any unexpected queued bytes too, before bounded shutdown.
            while len(item["ack"]) < 1024:
                try:
                    data = peer.recv(1024 - len(item["ack"]))
                except (BlockingIOError, OSError):
                    break
                if not data:
                    break
                item["ack"].extend(data)
            for channel in (item["host"], peer):
                try:
                    channel.shutdown(socket.SHUT_RDWR)
                except OSError:
                    pass
            if item["thread"] is not None:
                item["thread"].join(4)
            alive = item["thread"] is not None and item["thread"].is_alive()
            (self.root / ("peer-ack-%d.bin" % index)).write_bytes(item["ack"])
            self.retain("result-%d.json" % index, {"result": item["result"], "error": item["error"],
                        "worker_alive_after_bounded_join": alive, "finished_ns": item["finished_ns"],
                        "gate_pending": item["gate"].pending.is_set(),
                        "gate_allowed": item["gate"].allowed.is_set(),
                        "retained_peer_ack_bytes": len(item["ack"])})
            item["host"].close()
            peer.close()
            self.assertFalse(alive, "receiver survived bounded synthetic cleanup")


if __name__ == "__main__":
    unittest.main()
