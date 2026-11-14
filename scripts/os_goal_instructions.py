"""Reconcile explicitly hash-bound stale instructions before launcher activation.

The caller must hold the repository launch lease. This helper never acquires or
changes campaign/watch locks, state, objectives or budgets. Validation is the
default; only an authorized launcher startup may request execute=True.
"""
from __future__ import annotations

from contextlib import ExitStack
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import stat
from uuid import uuid4


_ID = re.compile(r"[0-9]{8}T[0-9]{12}Z-[0-9a-f]{32}\Z")
_SHA = re.compile(r"[0-9a-f]{64}\Z")
_MAX_BYTES = 32768
_MAX_ENTRIES = 256
_MAX_BINDINGS = 32
_DIR_FLAGS = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
_FILE_FLAGS = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK


def _directory(stack, parent, name, create=False):
    if create:
        try:
            os.mkdir(name, 0o700, dir_fd=parent)
            os.fsync(parent)
        except FileExistsError:
            pass
    try:
        fd = os.open(name, _DIR_FLAGS, dir_fd=parent)
    except FileNotFoundError:
        return None
    except OSError as exc:
        raise ValueError("Unsafe instruction directory: " + name) from exc
    stack.callback(os.close, fd)
    return fd


def _base(stack, directory):
    path = Path(directory).absolute()
    if ".." in path.parts:
        raise ValueError("Instruction directory must not contain parent traversal")
    fd = os.open(path.anchor, _DIR_FLAGS)
    stack.callback(os.close, fd)
    for name in path.parts[1:]:
        fd = _directory(stack, fd, name)
        if fd is None:
            raise ValueError("Campaign directory does not exist")
    return fd


def _names(fd):
    if fd is None:
        return []
    names = []
    with os.scandir(fd) as entries:
        for entry in entries:
            names.append(entry.name)
            if len(names) > _MAX_ENTRIES:
                raise ValueError("Instruction directory exceeds bounded entry limit")
    return sorted(names)


def _stat(fd, name):
    if fd is None:
        return None
    try:
        value = os.stat(name, dir_fd=fd, follow_symlinks=False)
    except FileNotFoundError:
        return None
    if not stat.S_ISREG(value.st_mode):
        raise ValueError("Instruction entry must be a regular file: " + name)
    return value


def _read(fd, name):
    before = _stat(fd, name)
    if before is None:
        return None
    if before.st_size > _MAX_BYTES:
        raise ValueError("Instruction entry exceeds bounded byte limit: " + name)
    try:
        stream = os.open(name, _FILE_FLAGS, dir_fd=fd)
    except OSError as exc:
        raise ValueError("Unsafe instruction entry: " + name) from exc
    try:
        opened = os.fstat(stream)
        if not stat.S_ISREG(opened.st_mode) or (opened.st_dev, opened.st_ino) != (before.st_dev, before.st_ino):
            raise ValueError("Instruction entry changed while opening: " + name)
        chunks, size = [], 0
        while size <= _MAX_BYTES:
            chunk = os.read(stream, min(4096, _MAX_BYTES + 1 - size))
            if not chunk:
                break
            chunks.append(chunk)
            size += len(chunk)
        after = os.fstat(stream)
        if size > _MAX_BYTES or (opened.st_size, opened.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
            raise ValueError("Instruction entry changed or exceeds byte limit: " + name)
        return b"".join(chunks)
    finally:
        os.close(stream)


def _receipt(raw, ident, digest):
    try:
        value = json.loads(raw)
        valid = (isinstance(value, dict) and
                 set(value) == {"id", "sha256", "startup_instruction_sha256", "status", "timestamp"} and
                 value.get("id") == ident and
                 value.get("sha256") == digest and value.get("status") == "superseded" and
                 isinstance(value.get("startup_instruction_sha256"), str) and
                 _SHA.fullmatch(value["startup_instruction_sha256"]) and
                 isinstance(value.get("timestamp"), str) and
                 datetime.fromisoformat(value["timestamp"]).tzinfo is not None)
    except (ValueError, TypeError):
        valid = False
    if not valid:
        raise ValueError("Invalid reconciliation receipt: " + ident)
    return value


def _write_receipt(fd, name, value):
    # Publish only a fully fsynced receipt, without replacing historical evidence.
    # A crash can leave an unreferenced temporary file; replay never trusts it.
    temporary = "." + name + "." + uuid4().hex + ".tmp"
    payload = (json.dumps(value, sort_keys=True, indent=2) + "\n").encode()
    stream = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                     0o600, dir_fd=fd)
    try:
        view = memoryview(payload)
        while view:
            written = os.write(stream, view)
            if written <= 0:
                raise OSError("Could not write reconciliation receipt")
            view = view[written:]
        os.fsync(stream)
    finally:
        os.close(stream)
    os.link(temporary, name, src_dir_fd=fd, dst_dir_fd=fd, follow_symlinks=False)
    os.fsync(fd)
    os.unlink(temporary, dir_fd=fd)
    os.fsync(fd)


def reconcile_instructions(directory: Path, bindings: list[dict], startup_instruction_sha256: str,
                           execute: bool = False) -> list[dict]:
    """Validate all queue entries, then optionally archive exact bound bytes.

    Bindings are {id, sha256} pairs for ORIGINAL pending JSON bytes. Delivered
    instructions are only observed by filename and never rewritten or read.
    Existing receipts are immutable, including when a later startup note differs.
    Exceptions block startup; a partially completed move is safely replayable.
    """
    if not isinstance(execute, bool):
        raise ValueError("execute must be a boolean")
    if not isinstance(startup_instruction_sha256, str) or not _SHA.fullmatch(startup_instruction_sha256):
        raise ValueError("A startup instruction SHA-256 is required")
    if not isinstance(bindings, list) or len(bindings) > _MAX_BINDINGS:
        raise ValueError("Expected a bounded list of stale instruction bindings")
    bound = {}
    for item in bindings:
        if (not isinstance(item, dict) or set(item) != {"id", "sha256"} or
                not isinstance(item["id"], str) or not _ID.fullmatch(item["id"]) or
                not isinstance(item["sha256"], str) or not _SHA.fullmatch(item["sha256"]) or
                item["id"] in bound):
            raise ValueError("Invalid or duplicate stale instruction binding")
        bound[item["id"]] = item["sha256"]
    with ExitStack() as stack:
        base = _base(stack, directory)
        control = _directory(stack, base, "instructions")
        dirs = {name: _directory(stack, control, name) if control is not None else None
                for name in ("pending", "sending", "delivered", "superseded", "reconciliation")}
        if _names(dirs["sending"]):
            raise ValueError("Instruction delivery is uncertain; reconcile sending/ before resuming")
        for name in _names(dirs["pending"]):
            if not name.endswith(".json") or name[:-5] not in bound:
                raise ValueError("Unexpected pending instruction requires reconciliation: " + name)
        plans = []
        # Validate the whole queue before any filesystem mutations.
        for ident, digest in sorted(bound.items()):
            name = ident + ".json"
            pending = _read(dirs["pending"], name)
            archived = _read(dirs["superseded"], name)
            delivered = _stat(dirs["delivered"], name)
            raw_receipt = _read(dirs["reconciliation"], name)
            receipt = _receipt(raw_receipt, ident, digest) if raw_receipt is not None else None
            for raw in (pending, archived):
                if raw is not None and hashlib.sha256(raw).hexdigest() != digest:
                    raise ValueError("Original pending instruction hash mismatch: " + ident)
            if delivered is not None and (pending is not None or archived is not None or receipt is not None):
                raise ValueError("Conflicting delivered and pending/superseded instruction: " + ident)
            if receipt is not None and archived is None:
                raise ValueError("Reconciliation receipt has no preserved original: " + ident)
            plans.append((ident, digest, pending, archived, delivered, receipt))
        results = []
        for ident, digest, pending, archived, delivered, receipt in plans:
            name = ident + ".json"
            if pending is not None or archived is not None:
                if execute:
                    if dirs["superseded"] is None:
                        dirs["superseded"] = _directory(stack, control, "superseded", create=True)
                    if dirs["reconciliation"] is None:
                        dirs["reconciliation"] = _directory(stack, control, "reconciliation", create=True)
                    if pending is not None:
                        if os.fstat(dirs["pending"]).st_dev != os.fstat(dirs["superseded"]).st_dev:
                            raise ValueError("Instruction archive must be on the same filesystem")
                        if _read(dirs["pending"], name) != pending:
                            raise ValueError("Pending instruction changed before archival: " + ident)
                        if archived is None:
                            # Link first, durably retain that exact inode, then remove
                            # its queue name. Crashes can leave either or both names.
                            os.link(name, name, src_dir_fd=dirs["pending"],
                                    dst_dir_fd=dirs["superseded"], follow_symlinks=False)
                        if _read(dirs["superseded"], name) != pending:
                            raise ValueError("Archived instruction differs from pending: " + ident)
                    if pending is not None or receipt is None:
                        archive_fd = os.open(name, _FILE_FLAGS, dir_fd=dirs["superseded"])
                        try:
                            os.fsync(archive_fd)
                        finally:
                            os.close(archive_fd)
                        os.fsync(dirs["superseded"])
                    if pending is not None:
                        os.unlink(name, dir_fd=dirs["pending"])
                        os.fsync(dirs["pending"])
                    if receipt is None:
                        receipt = {"id": ident, "sha256": digest,
                                   "startup_instruction_sha256": startup_instruction_sha256,
                                   "status": "superseded", "timestamp": datetime.now(timezone.utc).isoformat()}
                        _write_receipt(dirs["reconciliation"], name, receipt)
                result = dict(receipt) if receipt is not None else {
                    "id": ident, "sha256": digest,
                    "startup_instruction_sha256": startup_instruction_sha256,
                    "status": "would_supersede", "timestamp": None}
                if receipt is not None and receipt["startup_instruction_sha256"] != startup_instruction_sha256:
                    result["requested_startup_instruction_sha256"] = startup_instruction_sha256
                    result["historical_supersession"] = True
                results.append(result)
            else:
                results.append({"id": ident, "sha256": digest,
                                "startup_instruction_sha256": startup_instruction_sha256,
                                "status": "already_delivered" if delivered is not None else "not_present",
                                "timestamp": None})
        return results
