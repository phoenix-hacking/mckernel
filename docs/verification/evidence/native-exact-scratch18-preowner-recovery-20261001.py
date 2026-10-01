#!/usr/bin/env python3
"""Fail-closed, source-only retirement of the scratch18 pre-owner failure.

This module deliberately has no privileged or Docker execution path.  A caller
must supply authenticated observations; the command line only validates the
published failure by default.  Recovery archives the two retained ownership
records, never the request, candidate, output, or evidence.
"""
import argparse
import errno
import hashlib
import json
import os
from pathlib import Path
import secrets
import stat
import ctypes
import re

EVIDENCE = Path(__file__).with_name("native-exact-scratch18-build-admission-failure-20261001-1.json")
FAILURE_SHA256 = "40497b42fd0906cfe45af35ee07a9be736948db8cda84d036216e9670663aec7"
# Corrected reviewed observer is not yet released.  This is deliberately a
# valid placeholder; callers must cascade the final 64-hex digest.
WRAPPER_SHA256 = "0" * 64
BOOT_ID_PREFIX = "c733d83b"
DEFAULT_ARCHIVE_DIR = Path("/home/holden/mckernel-work/scratch/native-exact-scratch18-preowner-archives")

class Refusal(ValueError):
    pass

_SEAL = object()
class SealedObservations:
    __slots__ = ("_value", "_seal")
    def __init__(self, value, seal): self._value, self._seal = value, seal

def seal_observations(value):
    """Test/review seam: only a reviewed observer may create this token."""
    if not isinstance(value, dict): raise Refusal("observer-report-shape")
    return SealedObservations(value, _SEAL)

def observe_production(expected_wrapper_sha=WRAPPER_SHA256):
    if not re.fullmatch(r"[0-9a-f]{64}", expected_wrapper_sha):
        raise Refusal("wrapper-hash-format")
    # The corrected procfs/Docker/lease observer is an independently reviewed
    # integration dependency.  Never accept a path, JSON report, or booleans
    # from the command line as a substitute for it.
    raise Refusal("production-observer-not-installed")

def sha(data):
    return hashlib.sha256(data).hexdigest()

def _json(data):
    try:
        return json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise Refusal("invalid-json") from exc

def _regular(path, digest, mode=None, uid=None, gid=None, inode=None, device=None):
    try:
        lst = os.lstat(path)
        fd = os.open(str(path), os.O_RDONLY | os.O_NOFOLLOW)
        try:
            st = os.fstat(fd)
            chunks = []
            while True:
                chunk = os.read(fd, 1024 * 1024)
                if not chunk: break
                chunks.append(chunk)
            data = b"".join(chunks)
        finally:
            os.close(fd)
    except OSError as exc:
        raise Refusal("artifact-unreadable") from exc
    if (not stat.S_ISREG(lst.st_mode) or lst.st_ino != st.st_ino or lst.st_dev != st.st_dev
            or not stat.S_ISREG(st.st_mode) or st.st_nlink != 1 or sha(data) != digest
            or (mode is not None and stat.S_IMODE(st.st_mode) != int(mode, 8))
            or (uid is not None and st.st_uid != uid) or (gid is not None and st.st_gid != gid)
            or (inode is not None and st.st_ino != inode) or (device is not None and st.st_dev != device)):
        raise Refusal("artifact-binding")
    return st

def _fsync_parent(path):
    fd = os.open(str(Path(path).parent), os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try: os.fsync(fd)
    finally: os.close(fd)

def _create_fsync(path, payload):
    fd = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        os.write(fd, payload)
        os.fsync(fd)
    finally: os.close(fd)
    _fsync_parent(path)

def load_failure(path=EVIDENCE):
    raw = Path(path).read_bytes()
    if path == EVIDENCE and sha(raw) != FAILURE_SHA256:
        raise Refusal("failure-evidence-hash")
    return _json(raw)

def validate_observations(failure, observations, wrapper_sha=WRAPPER_SHA256):
    """Validate a complete, authenticated census without changing anything."""
    if not isinstance(observations, SealedObservations) or observations._seal is not _SEAL:
        raise Refusal("unauthenticated-census")
    observations = observations._value
    if not re.fullmatch(r"[0-9a-f]{64}", wrapper_sha): raise Refusal("wrapper-hash-format")
    if observations.get("wrapper_sha256") != wrapper_sha:
        raise Refusal("wrapper-hash")
    for key in ("processes", "docker", "lease", "capacity", "artifacts", "request", "boot"):
        if key not in observations: raise Refusal("incomplete-census-" + key)
    if observations["request"] != failure.get("request"):
        raise Refusal("request-binding")
    if not isinstance(observations["boot"], dict) or not str(observations["boot"].get("boot_id", "")).startswith(BOOT_ID_PREFIX):
        raise Refusal("boot-binding")
    if observations["processes"] not in ([], {"relevant": []}): raise Refusal("relevant-process")
    if observations["docker"].get("new_container") is not False: raise Refusal("new-container")
    if observations["lease"].get("present") is not False: raise Refusal("lease-present")
    if observations["capacity"].get("sufficient") is not True: raise Refusal("capacity")
    expected = failure["postflight"]
    if observations["artifacts"] != expected: raise Refusal("prepared-artifacts-changed")
    owner = failure["owner_identity"]
    if owner.get("current_state") != "absent" or observations.get("owner") != owner:
        raise Refusal("owner-reuse")
    for lock in (failure["retained_locks"]["attempt"], failure["retained_locks"]["shared"]):
        _regular(lock["path"], lock["sha256"], lock["mode"], lock["uid"], lock["gid"], lock["inode"])
    return True

def _rename_noreplace(source, destination):
    """renameat2(RENAME_NOREPLACE), with pinned O_NOFOLLOW parent dirfds."""
    libc = ctypes.CDLL(None, use_errno=True)
    syscall = getattr(libc, "syscall", None)
    if syscall is None: raise Refusal("renameat2-unavailable")
    nr = {"x86_64": 316, "aarch64": 276}.get(os.uname().machine)
    if nr is None: raise Refusal("renameat2-platform")
    sp, dp = Path(source).parent, Path(destination).parent
    sfd = os.open(str(sp), os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    dfd = os.open(str(dp), os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        ctypes.set_errno(0)
        rc = syscall(nr, sfd, os.fsencode(Path(source).name), dfd,
                     os.fsencode(Path(destination).name), 1)
        if rc != 0:
            err = ctypes.get_errno()
            raise OSError(err, os.strerror(err))
    finally:
        os.close(sfd); os.close(dfd)

def _archive_one(source, record, archive_dir, label, fault=None):
    _regular(source, record["sha256"], record["mode"], record["uid"], record["gid"], record["inode"])
    archive_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    name = archive_dir / (Path(source).name + "." + label + "." + secrets.token_hex(8) + ".archive")
    if fault == "collision": raise Refusal("archive-collision")
    try:
        if fault == "collision": raise FileExistsError(errno.EEXIST, "injected collision")
        if fault == "rename": raise OSError(errno.EIO, "injected rename failure")
        _rename_noreplace(source, name)
        _fsync_parent(source)
        _regular(name, record["sha256"], record["mode"], record["uid"], record["gid"], record["inode"])
    except FileExistsError as exc:
        raise Refusal("archive-collision") from exc
    except OSError as exc:
        raise Refusal("archive-rename-failure") from exc
    return str(name)

def recover(failure=None, observations=None, archive_dir=DEFAULT_ARCHIVE_DIR,
            journal_dir=None, execute=False, fault=None):
    failure = load_failure() if failure is None else failure
    if observations is None: observations = observe_production()
    validate_observations(failure, observations)
    if not execute: return {"status": "PASS_VALIDATE_ONLY"}
    archive_dir = Path(archive_dir)
    journal_dir = Path(journal_dir or archive_dir)
    journal_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    journal = journal_dir / ("recovery-" + secrets.token_hex(8) + ".json")
    plans = []
    for label in ("attempt", "shared"):
        rec = failure["retained_locks"][label]
        plans.append({"label": label, "source": rec["path"], "source_inode": rec["inode"],
                      "source_device": rec.get("device"), "source_sha256": rec["sha256"]})
    state = {"schema": "mckernel.native-exact-scratch18-preowner-recovery.v1",
             "status": "STARTED", "failure_sha256": sha(json.dumps(failure, sort_keys=True).encode()),
             "archive_dir": str(archive_dir), "plans": plans, "events": []}
    _create_fsync(journal, json.dumps(state, sort_keys=True, separators=(",", ":")).encode() + b"\n")
    archived = []
    try:
        for label in ("attempt", "shared"):
            rec = failure["retained_locks"][label]
            archived.append(_archive_one(rec["path"], rec, archive_dir, label,
                                         fault=fault if label == "attempt" else None))
            state["events"].append({"archived": label, "path": archived[-1]})
            with open(journal, "ab", opener=lambda p, f: os.open(p, f | os.O_NOFOLLOW)) as jf:
                jf.write((json.dumps(state, sort_keys=True) + "\n").encode()); jf.flush(); os.fsync(jf.fileno())
            _fsync_parent(journal)
        state["status"] = "PASS"
    except Exception as exc:
        state["status"] = "FAIL_CLOSED"
        state["error"] = str(exc)
        _create_fsync(journal.with_name(journal.stem + ".terminal.json"), json.dumps(state, sort_keys=True).encode() + b"\n")
        raise
    _create_fsync(journal.with_name(journal.stem + ".terminal.json"), json.dumps(state, sort_keys=True).encode() + b"\n")
    return {"status": "PASS", "journal": str(journal), "archives": archived}

def replay(path):
    """A terminal journal is evidence, never an authorization to repeat it."""
    raise Refusal("replay-refused")

def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--execute", action="store_true", help="requires injected authenticated observations")
    args = p.parse_args(argv)
    try:
        result = recover(execute=args.execute)
    except Refusal as exc:
        print(json.dumps({"status": "REFUSED", "reason": str(exc)}, sort_keys=True))
        return 1
    print(json.dumps(result, sort_keys=True)); return 0

if __name__ == "__main__": raise SystemExit(main())
