#!/usr/bin/env python3
"""Synthetic framing tests only: no C, McKernel, QEMU or guest execution."""
import hashlib
from contextlib import contextmanager
import importlib.util
import json
import os
from pathlib import Path
import socket
import stat
import struct
import tempfile
import threading
import unittest
from unittest import mock

SPEC = importlib.util.spec_from_file_location("artifact_receiver", Path(__file__).with_name("receiver.py"))
receiver = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(receiver)
NONCE = "0123456789abcdef0011223344556677"
ROOT = "/attempt/controller"


# These builders use literal ABI layouts, separate from the parser constants.
def meta(mode, size=0, device=31, inode=7):
    return struct.pack("<8Q", mode, device, inode, size, 11, 22, 33, 44)


def record(kind, path=b"", payload=b""):
    return struct.pack("<IIQ", kind, len(path), len(payload)) + path + payload


def start(root=ROOT, nonce=NONCE):
    return struct.pack("<8sII16sIIII", b"STAF0001", 1, 48, bytes.fromhex(nonce),
                       256, 16777216, 1024, 0) + record(4, root.encode(), meta(stat.S_IFDIR | 0o700))


def finish(entries, directories, files, content):
    return record(3, payload=struct.pack("<4Q", entries, directories, files, content))


def file_record(path, content):
    return record(2, path.encode(), meta(stat.S_IFREG | 0o640, len(content)) + content)


class CaptureTests(unittest.TestCase):
    def evidence_root(self):
        root = Path(tempfile.mkdtemp(prefix="stability-artifact-" + self._testMethodName + "-"))
        (root / "case.json").write_text(json.dumps({"case": self.id(), "evidence_root": str(root),
            "scope": "synthetic-host-parser-only", "automatic_deletion": False}, sort_keys=True) + "\n")
        print("ARTIFACT_SYNTHETIC_EVIDENCE " + str(root), flush=True)
        return root

    @contextmanager
    def retained_directory(self):
        root = self.evidence_root()
        try:
            yield root
        except BaseException as exc:
            (root / "exception.txt").write_text(repr(exc) + "\n")
            raise

    def capture(self, wire, *, fragment=0, expected_root=ROOT, expected_nonce=NONCE,
                peer_eof=True, timeout=2, close_before_ack=False):
        root = self.evidence_root()
        destination = root / "capture"
        (root / "expected-wire.bin").write_bytes(wire)
        (root / "peer-request.json").write_text(json.dumps({"fragment": fragment, "expected_root": expected_root,
            "expected_nonce": expected_nonce, "peer_eof": peer_eof, "timeout": timeout,
            "close_before_ack": close_before_ack}, sort_keys=True) + "\n")
        host, guest = socket.socketpair()
        acknowledgements = bytearray()
        errors = []

        def peer():
            try:
                guest.settimeout(3)
                if fragment:
                    for i in range(0, len(wire), fragment):
                        guest.sendall(wire[i:i + fragment])
                else:
                    guest.sendall(wire)
                if peer_eof:
                    guest.shutdown(socket.SHUT_WR)
                if close_before_ack:
                    return
                while len(acknowledgements) < 112:
                    data = guest.recv(112 - len(acknowledgements))
                    if not data:
                        break
                    acknowledgements.extend(data)
            except (OSError, TimeoutError) as exc:
                errors.append(str(exc))
            finally:
                guest.close()

        thread = threading.Thread(target=peer)
        thread.start()
        try:
            result = receiver.receive(host, destination, expected_root, expected_nonce, timeout)
        except BaseException as exc:
            (root / "exception.txt").write_text(repr(exc) + "\n")
            raise
        finally:
            host.close()
            thread.join(4)
            (root / "received-ack.bin").write_bytes(acknowledgements)
            (root / "peer-errors.json").write_text(json.dumps({"errors": errors, "thread_alive": thread.is_alive()}, sort_keys=True) + "\n")
        (root / "receiver-result.json").write_text(json.dumps(result, sort_keys=True) + "\n")
        self.assertFalse(thread.is_alive(), "bounded synthetic peer cleanup")
        manifest = json.loads((destination / "manifest.json").read_bytes())
        self.assertEqual(manifest, result["manifest"])
        raw = (destination / "wire.bin").read_bytes()
        self.assertEqual(raw, wire[:len(raw)], "all captured bytes are exact original prefix")
        self.assertEqual(hashlib.sha256(raw).hexdigest(), manifest["wire_sha256"])
        self.assertEqual(len(raw), manifest["wire_bytes"])
        self.assertFalse(manifest["application_acceptance"])
        self.assertFalse(manifest["transport_fault_acceptance"])
        if acknowledgements:
            self.assertEqual(len(acknowledgements), 112)
            magic, nonce, status, reserved, content, entries, raw_hash, manifest_hash = struct.unpack(
                "<8s16sIIQQ32s32s", acknowledgements)
            self.assertEqual((magic, nonce, reserved), (b"STAA0001", bytes.fromhex(expected_nonce), 0))
            self.assertEqual(status, 0 if manifest["status"] == "CAPTURE_COMPLETE" else 1)
            self.assertEqual((content, entries), (manifest["content_bytes"], manifest["entry_count"]))
            self.assertEqual(raw_hash, hashlib.sha256(raw).digest())
            self.assertEqual(manifest_hash, hashlib.sha256((destination / "manifest.json").read_bytes()).digest())
        return result, destination, bytes(acknowledgements)

    def rejected(self, wire, reason, **kwargs):
        result, destination, ack = self.capture(wire, **kwargs)
        self.assertFalse(result["ok"])
        self.assertEqual(result["manifest"]["status"], "FAIL")
        self.assertIn(reason, result["manifest"]["error"])
        return destination, ack

    def test_binary_nested_success_fragmented(self):
        data = b"\x00\xff\n\rSTAF0001\x00" * 97
        wire = start() + record(1, b"nested", meta(stat.S_IFDIR | 0o755))
        wire += file_record("nested/raw.bin", data) + file_record("empty", b"") + finish(3, 1, 2, len(data))
        result, destination, ack = self.capture(wire, fragment=7)
        self.assertTrue(result["ok"])
        self.assertEqual(len(ack), 112)
        self.assertEqual((destination / "files/nested/raw.bin").read_bytes(), data)
        self.assertEqual((destination / "files/empty").read_bytes(), b"")
        self.assertEqual((destination / "files/nested/raw.bin").stat().st_mode & 0o777, 0o600)
        self.assertEqual((destination / "files/nested").stat().st_mode & 0o777, 0o700)
        self.assertEqual((destination / "wire.bin").read_bytes(), wire)

    def test_empty_tree_success(self):
        result, _, _ = self.capture(start() + finish(0, 0, 0, 0))
        self.assertTrue(result["ok"])

    def test_wrong_nonce_has_no_ack(self):
        _, ack = self.rejected(start(nonce="a" * 32), "invalid-header-or-nonce")
        self.assertEqual(ack, b"")

    def test_wrong_header_version(self):
        wire = bytearray(start())
        struct.pack_into("<I", wire, 8, 2)
        self.rejected(bytes(wire), "invalid-header-or-nonce")

    def test_wrong_root(self):
        self.rejected(start(root="/attempt/different"), "selected-root-mismatch")

    def test_unsafe_paths(self):
        for path in (b"../escape", b"/absolute", b"a//b", b"./file", b"a\\b", b"nul\x00name",
                     b"trailing/", b"nonascii\xff"):
            with self.subTest(path=path):
                destination, _ = self.rejected(start() + record(2, path, meta(stat.S_IFREG, 0)),
                                               "ProtocolError:")
                self.assertEqual(list((destination / "files").iterdir()), [])

    def test_missing_parent(self):
        self.rejected(start() + file_record("missing/file", b"x"), "missing-parent")

    def test_duplicate_path(self):
        self.rejected(start() + file_record("same", b"x") + file_record("same", b"y"), "duplicate-path")

    def test_symlink_metadata(self):
        self.rejected(start() + record(2, b"link", meta(stat.S_IFLNK, 0)), "invalid-object-metadata")

    def test_cross_filesystem(self):
        self.rejected(start() + record(2, b"other", meta(stat.S_IFREG, 0, device=32)), "mount-boundary")

    def test_declared_file_size_mismatch(self):
        self.rejected(start() + record(2, b"bad", meta(stat.S_IFREG, 4) + b"123"), "file-size-mismatch")

    def test_partial_file_retains_raw_prefix(self):
        wire = start() + struct.pack("<IIQ", 2, 3, 64 + 50000) + b"raw" + meta(stat.S_IFREG, 50000) + b"x" * 40000
        destination, _ = self.rejected(wire, "premature-eof")
        self.assertEqual((destination / "wire.bin").read_bytes(), wire)
        self.assertEqual((destination / "files/raw").read_bytes(), b"x" * 32768)

    def test_oversized_file_declared(self):
        self.rejected(start() + struct.pack("<IIQ", 2, 1, 64 + 16777217), "file-content-limit")

    def test_oversized_path_declared(self):
        self.rejected(start() + struct.pack("<IIQ", 2, 1025, 64), "record-path-limit")

    def test_entry_limit(self):
        wire = start() + b"".join(file_record(str(i), b"") for i in range(257))
        self.rejected(wire, "entry-limit")

    def test_exact_entry_limit_success(self):
        wire = start() + b"".join(file_record(str(i), b"") for i in range(256)) + finish(256, 0, 256, 0)
        result, _, _ = self.capture(wire)
        self.assertTrue(result["ok"])

    def test_aggregate_content_limit(self):
        wire = start() + file_record("full", b"x" * 16777216)
        wire += struct.pack("<IIQ", 2, 1, 65)
        destination, _ = self.rejected(wire, "file-content-limit", timeout=10)
        self.assertEqual((destination / "files/full").stat().st_size, 16777216)

    def test_directory_depth_limit(self):
        wire = start()
        for i in range(1, 66):
            wire += record(1, b"/".join([b"d"] * i), meta(stat.S_IFDIR))
        self.rejected(wire, "path-depth-limit")

    def test_invalid_timestamp(self):
        metadata = struct.pack("<8Q", stat.S_IFREG, 31, 7, 0, 0, 1000000000, 0, 0)
        self.rejected(start() + record(2, b"bad", metadata), "invalid-object-metadata")

    def test_wrong_final_totals(self):
        self.rejected(start() + finish(1, 0, 1, 5), "final-manifest-count-mismatch")

    def test_missing_end(self):
        self.rejected(start() + file_record("file", b"hello"), "premature-eof")

    def test_exporter_reports_failure(self):
        self.rejected(start() + record(127, payload=b"unsafe-entry-type errno=22"), "exporter-failure:unsafe-entry-type")

    def test_duplicate_root(self):
        self.rejected(start() + record(4, ROOT.encode(), meta(stat.S_IFDIR)), "duplicate-root")

    def test_unknown_record(self):
        self.rejected(start() + struct.pack("<IIQ", 17, 0, 0), "unknown-record-kind")

    def test_queued_trailing_byte(self):
        self.rejected(start() + finish(0, 0, 0, 0) + b"x", "queued-trailing-data")

    def test_host_deadline_retains_failure(self):
        result, destination, ack = self.capture(start(), peer_eof=False, timeout=0.05)
        self.assertFalse(result["ok"])
        self.assertIn("host-deadline", result["manifest"]["error"])
        self.assertEqual(ack, b"")
        self.assertFalse(json.loads((destination / "ack-result.json").read_bytes())["ack_complete"])

    def test_peer_closed_before_ack_does_not_authorize_shutdown(self):
        result, destination, ack = self.capture(start() + finish(0, 0, 0, 0), close_before_ack=True)
        self.assertEqual(result["manifest"]["status"], "CAPTURE_COMPLETE")
        self.assertFalse(result["ok"])
        self.assertEqual(ack, b"")
        self.assertFalse(json.loads((destination / "ack-result.json").read_bytes())["ack_complete"])

    def test_local_durability_error_sends_no_ack(self):
        with self.retained_directory() as root:
            destination = Path(root) / "capture"
            host, guest = socket.socketpair()
            wire = start() + finish(0, 0, 0, 0)
            (root / "expected-wire.bin").write_bytes(wire)
            with guest:
                guest.sendall(wire)
                guest.shutdown(socket.SHUT_WR)
                with host, mock.patch.object(receiver.os, "fsync", side_effect=OSError("synthetic-fsync-error")):
                    with self.assertRaisesRegex(OSError, "synthetic-fsync-error"):
                        receiver.receive(host, destination, ROOT, NONCE)
                ack = guest.recv(112)
                (root / "received-ack.bin").write_bytes(ack)
                (root / "peer-errors.json").write_text('{"errors":[]}\n')
                self.assertEqual(ack, b"")
            self.assertFalse((destination / "ack.bin").exists())
            self.assertEqual((destination / "wire.bin").read_bytes(), wire)

    def test_fresh_destination_parent_synced_before_ack(self):
        synced = []
        actual_fsync = receiver.os.fsync
        actual_send_ack = receiver.Receiver.send_ack
        def synced_fsync(fd):
            actual_fsync(fd)
            synced.append(fd)
        def checked_ack(instance, status):
            self.assertIn(instance.parent_fd, synced, "fresh capture parent directory must be durable")
            self.assertIn(instance.root_fd, synced)
            return actual_send_ack(instance, status)
        with mock.patch.object(receiver.os, "fsync", side_effect=synced_fsync), \
                mock.patch.object(receiver.Receiver, "send_ack", checked_ack):
            result, _, _ = self.capture(start() + finish(0, 0, 0, 0))
        self.assertTrue(result["ok"])

    def local_write_fault(self, target):
        with self.retained_directory() as root:
            destination = Path(root) / "capture"
            host, guest = socket.socketpair()
            wire = start() + file_record("data", b"12345678") + finish(1, 0, 1, 8)
            (root / "expected-wire.bin").write_bytes(wire)
            with guest, host:
                guest.sendall(wire)
                guest.shutdown(socket.SHUT_WR)
                instance = receiver.Receiver(host, destination, ROOT, NONCE)
                actual_write = receiver.os.write
                selected_fd = None
                successful_prefix = False
                injected = False
                def write_then_error(fd, data):
                    nonlocal selected_fd, successful_prefix, injected
                    if not injected and selected_fd is None:
                        if target == "raw" and fd == instance.raw_fd:
                            selected_fd = fd
                        elif target == "file" and fd != instance.raw_fd and stat.S_ISREG(os.fstat(fd).st_mode):
                            selected_fd = fd
                    if fd == selected_fd and not injected:
                        if not successful_prefix:
                            successful_prefix = True
                            return actual_write(fd, data[:3])
                        injected = True
                        raise OSError("synthetic-write-after-prefix")
                    return actual_write(fd, data)
                try:
                    with mock.patch.object(receiver.os, "write", side_effect=write_then_error):
                        result = instance.run()
                finally:
                    instance.close()
                    guest.setblocking(False)
                    ack, peer_errors = b"", []
                    try:
                        ack = guest.recv(112)
                    except BlockingIOError as exc:
                        peer_errors.append(str(exc))
                    (root / "received-ack.bin").write_bytes(ack)
                    (root / "peer-errors.json").write_text(json.dumps({"errors": peer_errors}, sort_keys=True) + "\n")
            self.assertTrue(injected)
            self.assertFalse(result["ok"])
            self.assertIn("synthetic-write-after-prefix", result["manifest"]["error"])
            raw = (destination / "wire.bin").read_bytes()
            self.assertEqual(result["manifest"]["wire_bytes"], len(raw))
            self.assertEqual(result["manifest"]["wire_sha256"], hashlib.sha256(raw).hexdigest())
            if target == "raw":
                self.assertEqual(raw, wire[:3])
                self.assertEqual(result["manifest"]["socket_bytes_received"], 48)
                self.assertFalse(result["manifest"]["received_raw_fully_stored"])
            else:
                self.assertEqual((destination / "files/data").read_bytes(), b"123")
                self.assertEqual(result["manifest"]["content_bytes"], 3)
                item = result["manifest"]["entries"][0]
                self.assertEqual(item["bytes_stored"], 3)
                self.assertEqual(item["sha256"], hashlib.sha256(b"123").hexdigest())
                self.assertFalse(item["complete"])
                self.assertTrue(result["manifest"]["received_raw_fully_stored"])

    def test_short_raw_write_then_error_accounts_actual_prefix(self):
        self.local_write_fault("raw")

    def test_short_extracted_file_write_then_error_accounts_actual_prefix(self):
        self.local_write_fault("file")

    def test_existing_destination_rejected(self):
        connection, peer = socket.socketpair()
        with self.retained_directory() as root, connection, peer:
            (root / "expected-wire.bin").write_bytes(b"")
            (root / "received-ack.bin").write_bytes(b"")
            (root / "peer-errors.json").write_text('{"errors":[],"no_stream_started":true}\n')
            # No stream read or path extraction occurs when attempt exists.
            with self.assertRaises(FileExistsError):
                receiver.Receiver(connection, root, ROOT, NONCE)


if __name__ == "__main__":
    unittest.main(verbosity=2)
