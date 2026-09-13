#!/usr/bin/env python3
"""Bounded STAF v1 capture. No payload execution or acceptance inference."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import select
import socket
import stat
import struct
import time

MAX_BYTES = 16 * 1024 * 1024
MAX_ENTRIES = 256
MAX_PATH = 1024
MAX_DEPTH = 64
MAX_WIRE = 17 * 1024 * 1024
HEADER = struct.Struct("<8sII16sIIII")
RECORD = struct.Struct("<IIQ")
META = struct.Struct("<8Q")
END = struct.Struct("<4Q")
ACK = struct.Struct("<8s16sIIQQ32s32s")


class ProtocolError(Exception):
    pass


def path_parts(raw, *, absolute=False):
    if not raw or len(raw) > MAX_PATH:
        raise ProtocolError("empty-or-oversized-path")
    if any(c < 32 or c > 126 or c == 92 for c in raw):
        raise ProtocolError("unsafe-path-byte")
    text = raw.decode("ascii")
    if absolute:
        if not text.startswith("/"):
            raise ProtocolError("root-not-absolute")
        text = text[1:]
    elif text.startswith("/"):
        raise ProtocolError("absolute-entry-path")
    parts = text.split("/")
    if any(p in ("", ".", "..") for p in parts):
        raise ProtocolError("unsafe-path-component")
    if not absolute and len(parts) > MAX_DEPTH:
        raise ProtocolError("path-depth-limit")
    return parts


def nonce_bytes(value):
    if len(value) != 32 or any(c not in "0123456789abcdef" for c in value):
        raise ValueError("nonce must contain exactly 32 lowercase hex digits")
    return bytes.fromhex(value)


def canonical(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n").encode("ascii")


def signed64(value):
    return value - (1 << 64) if value & (1 << 63) else value


class Receiver:
    def __init__(self, connection, destination, expected_root, nonce, timeout_seconds=60):
        if not 0 < timeout_seconds <= 120:
            raise ValueError("timeout_seconds must be greater than 0 and at most 120")
        self.expected_root = expected_root.encode("ascii")
        path_parts(self.expected_root, absolute=True)
        self.nonce = nonce_bytes(nonce)
        self.connection = connection
        self.connection.setblocking(False)
        self.started_ns = time.monotonic_ns()
        self.deadline = self.started_ns / 10**9 + timeout_seconds
        self.destination = Path(destination)
        if self.destination.name in ("", ".", ".."):
            raise ValueError("destination must name a fresh capture directory")
        self.parent_fd = -1
        self.root_fd = -1
        self.raw_fd = -1
        self.directory_fds = {}
        try:
            self.parent_fd = os.open(self.destination.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
            # Anchor creation/open to the same parent descriptor, never reuse.
            os.mkdir(self.destination.name, mode=0o700, dir_fd=self.parent_fd)
            self.root_fd = os.open(self.destination.name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
                                   dir_fd=self.parent_fd)
            self.raw_fd = os.open("wire.bin", os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC,
                                  0o600, dir_fd=self.root_fd)
            os.mkdir("files", mode=0o700, dir_fd=self.root_fd)
            self.directory_fds[""] = os.open("files", os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
                                             dir_fd=self.root_fd)
        except BaseException:
            self.close()
            raise
        self.raw_digest = hashlib.sha256()
        self.raw_bytes = 0
        self.received_bytes = 0
        self.content_bytes = 0
        self.file_count = 0
        self.dir_count = 0
        self.entries = []
        self.paths = set()
        self.source = None
        self.header_valid = False
        self.final_digest = None

    def close(self):
        for fd in self.directory_fds.values():
            os.close(fd)
        self.directory_fds.clear()
        if self.raw_fd >= 0:
            os.close(self.raw_fd)
            self.raw_fd = -1
        if self.root_fd >= 0:
            os.close(self.root_fd)
            self.root_fd = -1
        if self.parent_fd >= 0:
            os.close(self.parent_fd)
            self.parent_fd = -1

    def remaining(self):
        left = self.deadline - time.monotonic()
        if left <= 0:
            raise ProtocolError("host-deadline")
        return left

    def write_fd(self, fd, data, written=None):
        view = memoryview(data)
        while view:
            try:
                n = os.write(fd, view)
            except InterruptedError:
                continue
            if n <= 0:
                raise OSError("short-local-write")
            if written is not None:
                written(view[:n])
            view = view[n:]

    def raw_written(self, data):
        self.raw_digest.update(data)
        self.raw_bytes += len(data)

    def read(self, count):
        if count < 0 or self.raw_bytes + count > MAX_WIRE:
            raise ProtocolError("wire-limit")
        chunks = bytearray()
        while len(chunks) < count:
            remaining = self.remaining()
            try:
                data = self.connection.recv(min(32768, count - len(chunks)))
            except (BlockingIOError, InterruptedError):
                select.select([self.connection], [], [], min(remaining, 0.1))
                continue
            if not data:
                raise ProtocolError("premature-eof")
            self.received_bytes += len(data)
            self.write_fd(self.raw_fd, data, self.raw_written)
            chunks += data
        return bytes(chunks)

    def metadata(self, data, expected_kind):
        mode, dev, ino, size, ms, mn, cs, cn = META.unpack(data)
        if mode > 0xffff or stat.S_IFMT(mode) != expected_kind or mn >= 10**9 or cn >= 10**9:
            raise ProtocolError("invalid-object-metadata")
        if self.source is not None and dev != self.source["metadata"]["device"]:
            raise ProtocolError("source-mount-boundary")
        return {"mode": mode, "device": dev, "inode": ino, "size": size,
                "mtime_seconds": signed64(ms), "mtime_nanoseconds": mn,
                "ctime_seconds": signed64(cs), "ctime_nanoseconds": cn}

    def record(self):
        kind, path_length, payload_length = RECORD.unpack(self.read(RECORD.size))
        if path_length > MAX_PATH:
            raise ProtocolError("record-path-limit")
        # Check declared sizes before reading any attacker-selected length.
        if kind in (1, 4):
            if payload_length != META.size:
                raise ProtocolError("directory-payload-size")
        elif kind == 2:
            if not META.size <= payload_length <= META.size + MAX_BYTES - self.content_bytes:
                raise ProtocolError("file-content-limit")
        elif kind == 3:
            if path_length or payload_length != END.size:
                raise ProtocolError("end-shape")
        elif kind == 127:
            if path_length or not 1 <= payload_length <= 256:
                raise ProtocolError("failure-shape")
        else:
            raise ProtocolError("unknown-record-kind")
        return kind, self.read(path_length), payload_length

    def parse(self):
        magic, version, size, nonce, entries, content, paths, reserved = HEADER.unpack(self.read(HEADER.size))
        if (magic, version, size, nonce, entries, content, paths, reserved) != (
                b"STAF0001", 1, HEADER.size, self.nonce, MAX_ENTRIES, MAX_BYTES, MAX_PATH, 0):
            raise ProtocolError("invalid-header-or-nonce")
        self.header_valid = True
        kind, root, length = self.record()
        if kind == 127:
            raise ProtocolError("exporter-failure:" + self.failure_text(length))
        if kind != 4 or root != self.expected_root:
            raise ProtocolError("selected-root-mismatch")
        path_parts(root, absolute=True)
        self.source = {"path": root.decode("ascii"), "metadata": self.metadata(self.read(META.size), stat.S_IFDIR)}
        while True:
            kind, raw_path, length = self.record()
            if kind == 127:
                raise ProtocolError("exporter-failure:" + self.failure_text(length))
            if kind == 3:
                totals = END.unpack(self.read(length))
                if totals != (len(self.entries), self.dir_count, self.file_count, self.content_bytes):
                    raise ProtocolError("final-manifest-count-mismatch")
                # Reject bytes already queued after END. Future bytes cannot be
                # proved absent before the bidirectional ACK; one stream/nonce
                # carries one tree and the exporter sends no bytes until ACK.
                try:
                    extra = self.connection.recv(1, socket.MSG_PEEK)
                except (BlockingIOError, InterruptedError):
                    extra = b""
                if extra:
                    self.read(1)  # Preserve the first offending raw byte.
                    raise ProtocolError("queued-trailing-data")
                return
            if kind not in (1, 2):
                raise ProtocolError("duplicate-root")
            if len(self.entries) >= MAX_ENTRIES:
                raise ProtocolError("entry-limit")
            parts = path_parts(raw_path)
            path = raw_path.decode("ascii")
            parent = "/".join(parts[:-1])
            if path in self.paths or parent not in self.directory_fds:
                raise ProtocolError("duplicate-path-or-missing-parent")
            self.paths.add(path)
            metadata = self.metadata(self.read(META.size), stat.S_IFDIR if kind == 1 else stat.S_IFREG)
            item = {"path": path, "kind": "directory" if kind == 1 else "file", "metadata": metadata,
                    "complete": False, "bytes_stored": 0}
            self.entries.append(item)
            parent_fd = self.directory_fds[parent]
            if kind == 1:
                os.mkdir(parts[-1], mode=0o700, dir_fd=parent_fd)
                self.directory_fds[path] = os.open(parts[-1], os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
                                                  dir_fd=parent_fd)
                item["complete"] = True
                self.dir_count += 1
                continue
            if metadata["size"] != length - META.size:
                raise ProtocolError("file-size-mismatch")
            fd = os.open(parts[-1], os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC,
                         0o600, dir_fd=parent_fd)
            digest = hashlib.sha256()
            def file_written(data):
                digest.update(data)
                item["bytes_stored"] += len(data)
                self.content_bytes += len(data)
            try:
                left = metadata["size"]
                while left:
                    data = self.read(min(left, 32768))
                    self.write_fd(fd, data, file_written)
                    left -= len(data)
                os.fsync(fd)
                item["complete"] = True
                self.file_count += 1
            finally:
                item["sha256"] = digest.hexdigest()
                os.close(fd)

    def failure_text(self, length):
        data = self.read(length)
        if any(c < 32 or c > 126 for c in data):
            raise ProtocolError("unsafe-failure-text")
        return data.decode("ascii")

    def manifest(self, status, error):
        return {"schema_version": 1, "protocol": "STAF0001", "status": status,
                "error": error, "nonce": self.nonce.hex(), "source": self.source,
                "wire_bytes": self.raw_bytes, "wire_sha256": self.raw_digest.hexdigest(),
                "socket_bytes_received": self.received_bytes,
                "received_raw_fully_stored": self.received_bytes == self.raw_bytes,
                "capture_started_monotonic_ns": self.started_ns,
                "parse_finished_monotonic_ns": time.monotonic_ns(),
                "deadline_monotonic_ns": int(self.deadline * 10**9),
                "content_bytes": self.content_bytes, "entry_count": len(self.entries),
                "directories": self.dir_count, "files": self.file_count, "entries": self.entries,
                "limits": {"content_bytes": MAX_BYTES, "entries": MAX_ENTRIES, "path_bytes": MAX_PATH,
                           "depth": MAX_DEPTH, "wire_bytes": MAX_WIRE},
                "application_acceptance": False, "transport_fault_acceptance": False,
                "host_ack_required": True, "whole_tree_atomic_snapshot": False}

    def retain_manifest(self, manifest):
        # fsyncs are intentional: success ACK commits durable host evidence.
        os.fsync(self.raw_fd)
        for fd in self.directory_fds.values():
            os.fsync(fd)
        data = canonical(manifest)
        fd = os.open("manifest.json", os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC,
                     0o600, dir_fd=self.root_fd)
        try:
            # Even after a transport deadline, retain the small failure record.
            view = memoryview(data)
            while view:
                try:
                    count = os.write(fd, view)
                except InterruptedError:
                    continue
                if count <= 0:
                    raise OSError("short-manifest-write")
                view = view[count:]
            os.fsync(fd)
        finally:
            os.close(fd)
        os.fsync(self.root_fd)
        os.fsync(self.parent_fd)  # Persist the fresh capture directory entry.
        self.final_digest = hashlib.sha256(data).digest()

    def send_ack(self, status):
        data = ACK.pack(b"STAA0001", self.nonce, status, 0, self.content_bytes, len(self.entries),
                        self.raw_digest.digest(), self.final_digest)
        # Retain the exact intended ACK before sending it. Delivery status has
        # its own file because manifest.json cannot change after its ACK hash.
        fd = os.open("ack.bin", os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC,
                     0o600, dir_fd=self.root_fd)
        try:
            self.write_fd(fd, data)
            os.fsync(fd)
        finally:
            os.close(fd)
        os.fsync(self.root_fd)
        sent = 0
        error = None
        try:
            while sent < len(data):
                remaining = self.remaining()
                try:
                    count = self.connection.send(data[sent:])
                except (BlockingIOError, InterruptedError):
                    select.select([], [self.connection], [], min(remaining, 0.1))
                    continue
                if count <= 0:
                    raise ProtocolError("ack-channel-closed")
                sent += count
        except (OSError, ProtocolError) as exc:
            error = f"{type(exc).__name__}:{exc}"
        finished_ns = time.monotonic_ns()
        within_deadline = finished_ns < self.deadline * 10**9
        if not within_deadline and error is None:
            error = "ProtocolError:late-host-ack-send"
        result = {"schema_version": 1, "ack_status": status, "bytes_sent": sent,
                  "ack_complete": sent == len(data), "error": error,
                  "finished_monotonic_ns": finished_ns, "within_deadline": within_deadline,
                  "guest_received_ack_verified": False}
        encoded = canonical(result)
        fd = os.open("ack-result.json", os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC,
                     0o600, dir_fd=self.root_fd)
        try:
            # 256-byte local report; a transport timeout cannot suppress it.
            self.write_fd(fd, encoded)
            os.fsync(fd)
        finally:
            os.close(fd)
        os.fsync(self.root_fd)
        return result

    def run(self):
        error = None
        try:
            self.parse()
        except (OSError, ProtocolError, ValueError, struct.error) as exc:
            error = f"{type(exc).__name__}:{exc}"
        manifest = self.manifest("CAPTURE_COMPLETE" if error is None else "FAIL", error)
        self.retain_manifest(manifest)
        ack = None
        if self.header_valid:
            try:
                ack = self.send_ack(0 if error is None else 1)
            except (OSError, ProtocolError) as exc:
                ack = {"ack_complete": False, "error": f"{type(exc).__name__}:{exc}"}
        return {"manifest": manifest, "ack": ack,
                "ok": error is None and ack is not None and ack["ack_complete"] and ack.get("error") is None}


def receive(connection, destination, expected_root, nonce, timeout_seconds=60):
    """Capture one already-connected QEMU port; caller retains socket ownership."""
    receiver = Receiver(connection, destination, expected_root, nonce, timeout_seconds)
    try:
        return receiver.run()
    finally:
        receiver.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--socket", required=True, help="Existing QEMU server=on,wait=off unix socket")
    parser.add_argument("--destination", required=True, help="New host capture directory")
    parser.add_argument("--source-root", required=True, help="Exact selected absolute guest attempt root")
    parser.add_argument("--nonce", required=True)
    parser.add_argument("--timeout", type=float, default=60)
    args = parser.parse_args()
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as connection:
        connection.settimeout(args.timeout)
        connection.connect(args.socket)
        result = receive(connection, args.destination, args.source_root, args.nonce, args.timeout)
    print(json.dumps({"ok": result["ok"], "status": result["manifest"]["status"], "ack": result["ack"]}, sort_keys=True))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
