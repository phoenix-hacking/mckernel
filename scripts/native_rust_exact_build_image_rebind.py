#!/usr/bin/env python3
"""Bind an already-proven offline tool image to a new candidate.

This is deliberately a data-only admission boundary.  It authenticates the
old receipt and every retained observation, then emits a fresh, no-replace
rebind request.  A later owner is responsible for the fresh offline probe,
container retirement, and the final PASS receipt; this module never starts
Docker and cannot turn an old observation into execution evidence.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import uuid

SHA = re.compile(r"^[0-9a-f]{64}$")
GIT_SHA = re.compile(r"^[0-9a-f]{40}$")
IMAGE = re.compile(r"^sha256:[0-9a-f]{64}$")
PROFILE = {"cpus": 4, "memory_gib": 12, "pids": 512,
           "swap": "none", "network": "none", "mounts": "none",
           "privileged": False}


class RebindError(RuntimeError):
    pass


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def _regular(path, label):
    path = Path(path)
    if not path.is_absolute() or not path.is_file() or path.is_symlink():
        raise RebindError(label + " is not a regular absolute file")
    if any(part.is_symlink() for part in (path, *path.parents)):
        raise RebindError(label + " has symlink parent")
    return path


def _fresh(path, label):
    path = Path(path)
    if not path.is_absolute() or path.exists() or path.is_symlink():
        raise RebindError(label + " must be a fresh absolute path")
    if not path.parent.is_dir() or any(part.is_symlink() for part in (path.parent, *path.parent.parents)):
        raise RebindError(label + " parent is unsafe")
    return path


def _open_directory(path, label):
    """Open an absolute directory through a no-symlink descriptor chain."""
    path = Path(path)
    if not path.is_absolute() or ".." in path.parts:
        raise RebindError(label + " is not canonical")
    fd = os.open("/", os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        for part in path.parts[1:]:
            next_fd = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                              dir_fd=fd)
            os.close(fd)
            fd = next_fd
        return fd
    except BaseException:
        os.close(fd)
        raise


def _publish_request(output_path, payload):
    """Publish one request relative to a pinned parent descriptor."""
    output_path = Path(output_path)
    parent_fd = _open_directory(output_path.parent, "rebind request parent")
    stage_fd = file_fd = None
    stage_name = ".image-rebind-" + uuid.uuid4().hex
    try:
        try:
            os.stat(output_path.name, dir_fd=parent_fd, follow_symlinks=False)
        except FileNotFoundError:
            pass
        else:
            raise RebindError("rebind request already exists")
        os.mkdir(stage_name, 0o700, dir_fd=parent_fd)
        stage_fd = os.open(stage_name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                           dir_fd=parent_fd)
        file_fd = os.open("request.json", os.O_WRONLY | os.O_CREAT | os.O_EXCL |
                          os.O_NOFOLLOW, 0o600, dir_fd=stage_fd)
        view = memoryview(payload)
        while view:
            count = os.write(file_fd, view)
            if count <= 0:
                raise RebindError("request publication made no progress")
            view = view[count:]
        os.fsync(file_fd)
        os.close(file_fd)
        file_fd = None
        os.link("request.json", output_path.name, src_dir_fd=stage_fd,
                dst_dir_fd=parent_fd, follow_symlinks=False)
        os.fsync(parent_fd)
    except FileExistsError as exc:
        raise RebindError("rebind request already exists") from exc
    finally:
        if file_fd is not None:
            os.close(file_fd)
        if stage_fd is not None:
            try:
                os.unlink("request.json", dir_fd=stage_fd)
            except FileNotFoundError:
                pass
            os.close(stage_fd)
        try:
            os.rmdir(stage_name, dir_fd=parent_fd)
        except FileNotFoundError:
            pass
        os.close(parent_fd)


def _fresh_child(path, root, label):
    path, root = Path(path), Path(root)
    if (not path.is_absolute() or path.exists() or path.is_symlink() or
            not root.is_absolute() or path.parent != root):
        raise RebindError(label + " must be a fresh child of target evidence root")
    if any(part.is_symlink() for part in root.parents):
        raise RebindError(label + " parent is unsafe")
    return path


def _canonical(value, label):
    if not isinstance(value, str) or not value:
        raise RebindError(label + " missing")
    return value


def _load(path, label):
    try:
        return json.loads(_regular(path, label).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise RebindError(label + " unreadable") from exc


def _load_hashed(path, label):
    """Read and hash one immutable receipt snapshot, avoiding TOCTOU parsing."""
    path = _regular(path, label)
    try:
        payload = path.read_bytes()
        return json.loads(payload.decode("utf-8")), hashlib.sha256(payload).hexdigest()
    except (OSError, UnicodeError, ValueError) as exc:
        raise RebindError(label + " unreadable") from exc


def validate_receipt(receipt_path, evidence_root, *, source_candidate_sha,
                     source_receipt_sha256, image_id,
                     toolchain_lock_sha256):
    receipt_path = _regular(receipt_path, "receipt")
    receipt, receipt_digest = _load_hashed(receipt_path, "receipt")
    if not SHA.fullmatch(source_receipt_sha256) or receipt_digest != source_receipt_sha256:
        raise RebindError("source receipt digest differs")
    evidence_root = Path(evidence_root)
    if not evidence_root.is_absolute() or not evidence_root.is_dir():
        raise RebindError("evidence root missing")
    if not IMAGE.fullmatch(image_id) or not GIT_SHA.fullmatch(source_candidate_sha):
        raise RebindError("candidate or image identity malformed")
    if not SHA.fullmatch(toolchain_lock_sha256):
        raise RebindError("toolchain lock malformed")
    required = {"status": "PASS", "source_free": True, "runtime_network": "none",
                "retired": True, "candidate_sha": source_candidate_sha,
                "image_id": image_id, "toolchain_lock_sha256": toolchain_lock_sha256}
    for key, expected in required.items():
        if receipt.get(key) != expected:
            raise RebindError("receipt " + key + " differs")
    if not isinstance(receipt.get("tools"), dict) or not isinstance(receipt.get("libraries"), dict):
        raise RebindError("receipt tool/library data missing")
    evidence = receipt.get("evidence")
    if not isinstance(evidence, dict) or not evidence:
        raise RebindError("receipt evidence missing")
    for name, row in evidence.items():
        relative = Path(name) if isinstance(name, str) else Path(".")
        if (not isinstance(name, str) or not name or relative.is_absolute() or
                name != relative.as_posix() or relative == Path(".") or
                any(part in ("", ".", "..") for part in relative.parts) or
                not isinstance(row, dict) or not SHA.fullmatch(str(row.get("sha256", "")))):
            raise RebindError("evidence descriptor malformed")
        path = _regular(evidence_root / relative, "evidence " + name)
        if digest(path) != row["sha256"] or path.stat().st_size != row.get("size"):
            raise RebindError("evidence drift: " + name)
    return receipt


def rebind(*, receipt_path, evidence_root, source_candidate_sha, target_candidate_sha,
           source_receipt_sha256, image_id, toolchain_lock_sha256, output_path,
           target_receipt_path=None, target_evidence_root=None, image_probe=None):
    """Create a fresh candidate-bound request; ``image_probe`` is deferred."""
    if not GIT_SHA.fullmatch(target_candidate_sha):
        raise RebindError("target candidate identity malformed")
    if target_receipt_path is None or target_evidence_root is None:
        raise RebindError("target receipt and evidence paths required")
    target_evidence_root = _fresh(target_evidence_root, "target evidence root")
    target_receipt_path = _fresh_child(target_receipt_path, target_evidence_root,
                                       "target receipt")
    receipt = validate_receipt(receipt_path, evidence_root,
                               source_candidate_sha=source_candidate_sha,
                               source_receipt_sha256=source_receipt_sha256,
                               image_id=image_id,
                               toolchain_lock_sha256=toolchain_lock_sha256)
    if image_probe is not None:
        raise RebindError("execution probe is deferred to the reviewed owner")
    output_path = _fresh(output_path, "rebind request")
    if (output_path == target_evidence_root or
            target_evidence_root in output_path.parents or
            output_path in target_evidence_root.parents):
        raise RebindError("request and target evidence destinations overlap")
    request = {
        "schema": "mckernel.native-exact-build-image-rebind.v1",
        "status": "READY_FOR_REVIEWED_EXECUTION",
        "source_candidate_sha": source_candidate_sha,
        "target_candidate_sha": target_candidate_sha,
        "image_id": image_id,
        "source_receipt": str(Path(receipt_path)), "source_receipt_sha256": source_receipt_sha256,
        "source_evidence_root": str(Path(evidence_root)), "source_evidence": receipt["evidence"],
        "target_receipt": str(target_receipt_path),
        "target_evidence_root": str(target_evidence_root),
        "toolchain_lock_sha256": toolchain_lock_sha256, "profile": PROFILE,
        "probe": {"network": "none", "mounts": "none", "read_only": True,
                   "unprivileged": True, "fresh_container": True,
                   "compare_with_source_observation": True,
                   "target_receipt_must_be_pass": True,
                   "target_receipt_candidate_sha": target_candidate_sha,
                   "target_receipt_evidence_root": str(target_evidence_root),
                   "owned_cleanup_required": True,
                   "retire_before_lease_release": True},
        "execution_claim": False,
    }
    payload = (json.dumps(request, sort_keys=True, indent=2) + "\n").encode()
    _publish_request(output_path, payload)
    return request


def main(argv=None):
    p = argparse.ArgumentParser()
    for name in ("receipt_path", "evidence_root", "source_candidate_sha", "target_candidate_sha", "source_receipt_sha256", "image_id", "toolchain_lock_sha256", "output_path", "target_receipt_path", "target_evidence_root"):
        p.add_argument("--" + name.replace("_", "-"), required=True)
    args = p.parse_args(argv)
    try:
        rebind(**vars(args))
    except RebindError as exc:
        p.error(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
