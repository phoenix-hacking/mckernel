#!/usr/bin/env python3
"""Fail-closed preparation packet for the consumed exact-build candidate.

This packet is intentionally a preparation/plan artifact.  It does not delete,
copy, mount, launch, or build anything.  A separately reviewed operator may
call ``prepare_archive`` after the guards below have been independently
released; source relocation remains a later, distinct operation.
"""

from __future__ import annotations

import hashlib
import json
import os
import pathlib
import stat
import tarfile
import io
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

SCRATCH = pathlib.Path("/home/holden/mckernel-work/scratch")
CANDIDATE = SCRATCH / "mckernel-exact-candidate-8b5056f8-scratch-6"
OUTPUT = SCRATCH / "native-exact-build-output-8b5056f8-scratch-6"
EVIDENCE = SCRATCH / "native-exact-build-evidence-8b5056f8-scratch-6"
FAILURE = pathlib.Path("/home/holden/mckernel/docs/verification/evidence/native-exact-build-8b5056f8-scratch6-runtime-workflow-failure-20260930.json")
ARCHIVE = SCRATCH / "native-exact-build-failure-8b5056f8-scratch-6-20260930.tar"
REQUEST = SCRATCH / "native-exact-build-request-8b5056f8-scratch-6.json"
MANIFEST = SCRATCH / "native-exact-inputs-8b5056f8-scratch-6.json"
PREP_TERMINAL = SCRATCH / "native-exact-candidate-preparation-8b5056f8-scratch-6-terminal.json"
EXCLUSION = SCRATCH / "native-exact-candidate-operational-exclusion-objtoolbinding-11.json"
DEST_PARENT = pathlib.Path("/home/holden/mckernel-work/retained-exact-candidates")
DESTINATION = DEST_PARENT / "mckernel-exact-candidate-8b5056f8-scratch-6"

CANDIDATE_COMMIT = "8b5056f836ecd3e6916625696750c4dfadbaaf9f"
CANDIDATE_IDENTITY = "1831:5111816"
OUTPUT_IDENTITY = "1831:6553623"
EVIDENCE_IDENTITY = "1831:6553638"
CONTAINER_ID = "92b2f3fed0376933f6d703ecfe5245da5a3f19be63aa9712d4713792b5c245e9"
CONTAINER_EXIT = 1
CONTAINER_PID = 0
CONTAINER_OOM = False
REQUEST_SHA = "f234ca2cb443f0014f626bbbf1e72991dd1c6a51598c5b675f895354847300d4"
MANIFEST_SHA = "c1ad79ea8b0bba63e41b9a1e34d43b32e008ee97dec357ad6a3295b972bdd719"
PREP_TERMINAL_SHA = "dd243ae0f14025bccafeab21654478780f102ddc64668770820d79b5a0379b95"
EXCLUSION_SHA = "4f3f3ec96b1366cdbac384ff70d54f0576f99308a33ad7986dc804ca5f8511ee"
EXCLUSION_IDENTITY = "1831:57597"
FAILURE_SHA = "9e3e757596190f2d023a0fe372cdefff86d20df2af488a84c25593194979cd08"
FAILURE_COMMIT = "ec4768c91f1719647cdf806dbd1a192da119b990"
OWNER_RECEIPT_SHA = "fba8703bf4c8bc79e53b6fe7b7b4d20ea4b47e2406de0bd05deedeb7984a4107"
BUILD_RECEIPT_SHA = "ffa7765a9cc0d0820cde690efa0896c15411d134e2ff48374b38ee085de80889"
DRIVER_LOG_SHA = "6023ceed80de89933221fd9b2725addea3f7a3e040b54d72c020fe7259bacdf5"
SOURCE_DEVICE = 1831
DESTINATION_DEVICE = 66306
INPUT_DEVICES = {OUTPUT: 1831, EVIDENCE: 1831, REQUEST: 1831, MANIFEST: 1831,
                 PREP_TERMINAL: 1831, EXCLUSION: 1831, FAILURE: 66306}
HOST_FREE_FLOOR = 16 * 1024**3
EMERGENCY_RESERVE = 512 * 1024**2

# OUTPUT and EVIDENCE are deliberately trees.  CANDIDATE is never listed here.
ARCHIVE_INPUTS = (OUTPUT, EVIDENCE, REQUEST, MANIFEST, PREP_TERMINAL, EXCLUSION, FAILURE)
REFERENCED_EVIDENCE = {
    EVIDENCE / "receipt.json": OWNER_RECEIPT_SHA,
    EVIDENCE / "build/receipt.json": BUILD_RECEIPT_SHA,
    EVIDENCE / "build/driver.log": DRIVER_LOG_SHA,
}


@dataclass(frozen=True)
class Entry:
    path: str
    kind: str
    mode: int
    size: int
    sha256: Optional[str]
    target: Optional[str]
    hardlink_to: Optional[str]


def digest(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open("rb", buffering=0) as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def inventory(root: pathlib.Path) -> List[Entry]:
    """Return a deterministic, lstat-based inventory while rejecting escapes."""
    root = pathlib.Path(root)
    if not root.is_dir() or root.is_symlink():
        raise ValueError("root-not-directory")
    rows: List[Entry] = []
    seen: Dict[Tuple[int, int], List[str]] = {}
    for path in sorted((root, *root.rglob("*")), key=lambda p: str(p)):
        info = path.lstat()
        rel = "." if path == root else str(path.relative_to(root))
        kind = stat.filemode(info.st_mode)[0]
        target = None
        sha = None
        hardlink = None
        if stat.S_ISLNK(info.st_mode):
            target = os.readlink(path)
            resolved = (path.parent / target).resolve(strict=False)
            if os.path.commonpath((str(root), str(resolved))) != str(root):
                raise ValueError("unsafe-symlink")
        elif stat.S_ISREG(info.st_mode):
            if info.st_nlink != 1:
                raise ValueError("external-hardlink")
            sha = digest(path)
            key = (info.st_dev, info.st_ino)
            seen.setdefault(key, []).append(rel)
        elif not stat.S_ISDIR(info.st_mode):
            raise ValueError("special-file")
        rows.append(Entry(rel, kind, stat.S_IMODE(info.st_mode), info.st_size, sha, target, hardlink))
    anchors = {name: min(paths) for paths in seen.values() if len(paths) > 1 for name in paths}
    rows = [Entry(row.path, row.kind, row.mode, row.size, row.sha256, row.target,
                  anchors.get(row.path) if row.path in anchors and row.path != anchors[row.path] else row.hardlink_to)
            for row in rows]
    return rows


def _require_regular(path: pathlib.Path) -> None:
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_dev != SOURCE_DEVICE:
        raise RuntimeError(f"input-identity:{path}")


def _validate_input(path: pathlib.Path) -> None:
    """Validate a file or complete directory tree without following escapes."""
    expected_device = INPUT_DEVICES.get(path, SOURCE_DEVICE)
    info = path.lstat()
    if info.st_dev != expected_device:
        raise RuntimeError(f"input-device:{path}")
    parent = path.parent
    while True:
        parent_info = parent.lstat()
        if stat.S_ISLNK(parent_info.st_mode):
            raise RuntimeError(f"input-ancestor-symlink:{parent}")
        if parent == parent.parent:
            break
        parent = parent.parent
    if stat.S_ISREG(info.st_mode):
        if info.st_nlink != 1:
            raise RuntimeError(f"external-hardlink:{path}")
        return
    if stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode):
        raise RuntimeError(f"input-kind:{path}")
    for child in sorted(path.rglob("*"), key=str):
        child_info = child.lstat()
        if child_info.st_dev != expected_device:
            raise RuntimeError(f"input-device:{child}")
        if stat.S_ISLNK(child_info.st_mode) or not (stat.S_ISREG(child_info.st_mode) or stat.S_ISDIR(child_info.st_mode)):
            raise RuntimeError(f"input-kind:{child}")
        if stat.S_ISREG(child_info.st_mode) and child_info.st_nlink != 1:
            raise RuntimeError(f"external-hardlink:{child}")


def _input_record(path: pathlib.Path) -> dict:
    _validate_input(path)
    if path.is_dir():
        rows = inventory(path)
        return {"path": str(path), "kind": "directory", "entries": [row.__dict__ for row in rows]}
    return {"path": str(path), "kind": "file", "sha256": digest(path), "size": path.stat().st_size}


def audit_inputs(snapshot: Optional[dict] = None) -> dict:
    """Audit only the seven retained failure inputs; never inspect source C."""
    if snapshot is None:
        snapshot = _expected_members()
    # The snapshot is the sole source used for the archive and manifest.  A
    # second live inventory is only a guard against mutation during auditing.
    if snapshot != _expected_members():
        raise RuntimeError("audited-snapshot-changed")
    for path in ARCHIVE_INPUTS:
        _validate_input(path)
    if f"{OUTPUT.stat().st_dev}:{OUTPUT.stat().st_ino}" != OUTPUT_IDENTITY or f"{EVIDENCE.stat().st_dev}:{EVIDENCE.stat().st_ino}" != EVIDENCE_IDENTITY:
        raise RuntimeError("live-tree-identity-mismatch")
    if f"{EXCLUSION.stat().st_dev}:{EXCLUSION.stat().st_ino}" != EXCLUSION_IDENTITY:
        raise RuntimeError("live-exclusion-identity-mismatch")
    for path, expected in REFERENCED_EVIDENCE.items():
        _validate_input(path)
        if digest(path) != expected:
            raise RuntimeError(f"referenced-evidence-hash-mismatch:{path}")
    failure = json.loads(FAILURE.read_text())
    if digest(REQUEST) != REQUEST_SHA or digest(MANIFEST) != MANIFEST_SHA or digest(PREP_TERMINAL) != PREP_TERMINAL_SHA or digest(EXCLUSION) != EXCLUSION_SHA or digest(FAILURE) != FAILURE_SHA:
        raise RuntimeError("retained-input-hash-mismatch")
    execution = failure.get("execution", {})
    if failure.get("candidate_sha") != CANDIDATE_COMMIT or execution.get("exit_code") != CONTAINER_EXIT or execution.get("terminal_pid") != CONTAINER_PID or execution.get("oom_killed") != CONTAINER_OOM or execution.get("container_id") != CONTAINER_ID:
        raise RuntimeError("failure-identity-mismatch")
    retained = failure.get("retained_evidence", {})
    if retained.get("output_identity") != OUTPUT_IDENTITY or retained.get("evidence_identity") != EVIDENCE_IDENTITY or retained.get("operational_exclusion_identity") != EXCLUSION_IDENTITY or retained.get("operational_exclusion_sha256") != EXCLUSION_SHA:
        raise RuntimeError("retained-evidence-identity-mismatch")
    if execution.get("exit_code") != CONTAINER_EXIT:
        raise RuntimeError("failure-exit-mismatch")
    return {
        "schema": "mckernel.native-exact-candidate-retention-relocation.v1",
        "status": "AUDIT_ONLY",
        "candidate_root": str(CANDIDATE),
        "candidate_commit": CANDIDATE_COMMIT,
        "candidate_identity": CANDIDATE_IDENTITY,
        "output_identity": OUTPUT_IDENTITY,
        "evidence_identity": EVIDENCE_IDENTITY,
        "container_id": CONTAINER_ID,
        "container_exit": CONTAINER_EXIT,
        "container_pid": CONTAINER_PID,
        "container_oom": CONTAINER_OOM,
        "failure_record_commit": FAILURE_COMMIT,
        "inputs": {name: row.__dict__ for name, row in sorted(snapshot.items())},
        "source_excluded": True,
        "destination": str(DESTINATION),
        "source_device": SOURCE_DEVICE,
        "destination_device": DESTINATION_DEVICE,
        "host_free_floor": HOST_FREE_FLOOR,
        "emergency_reserve": EMERGENCY_RESERVE,
    }


def _add_no_replace(tar: tarfile.TarFile, path: pathlib.Path, arcname: str) -> None:
    _validate_input(path)
    tar.add(path, arcname=arcname, recursive=path.is_dir())


def _expected_members() -> dict:
    expected = {}
    for path in ARCHIVE_INPUTS:
        _validate_input(path)
        if path.is_dir():
            for row in inventory(path):
                expected[f"{path.name}/{row.path}" if row.path != "." else path.name] = row
        else:
            info = path.stat()
            expected[path.name] = Entry(path.name, "-", stat.S_IMODE(info.st_mode), info.st_size, digest(path), None, None)
    return expected


def _verify_archive(path: pathlib.Path, expected: dict, identity: tuple[int, int]) -> None:
    info = path.lstat()
    if (info.st_dev, info.st_ino) != identity:
        raise RuntimeError("archive-temp-replaced")
    with tarfile.open(path, "r") as archive:
        members = archive.getmembers()
        actual = {member.name: member for member in members if member.name != "retention-manifest.json"}
        if set(actual) != set(expected):
            raise RuntimeError("archive-member-set-mismatch")
        for name, row in expected.items():
            member = actual[name]
            expected_type = {"d": tarfile.DIRTYPE, "-": tarfile.REGTYPE}[row.kind]
            if member.type != expected_type or member.mode != row.mode or (row.kind == "-" and member.size != row.size):
                raise RuntimeError(f"archive-member-metadata-mismatch:{name}")
            if row.kind == "-":
                stream = archive.extractfile(member)
                if stream is None or hashlib.sha256(stream.read()).hexdigest() != row.sha256:
                    raise RuntimeError(f"archive-member-hash-mismatch:{name}")
    info = path.lstat()
    if (info.st_dev, info.st_ino) != identity:
        raise RuntimeError("archive-temp-replaced")


def prepare_archive(destination: pathlib.Path = ARCHIVE) -> dict:
    """Create an explicit failure archive; source candidate is never an input.

    The caller must opt in with ``RETENTION_PREPARE_RELEASE=1``.  This gate is
    deliberately independent of any later relocation release.
    """
    if os.environ.get("RETENTION_PREPARE_RELEASE") != "1":
        raise RuntimeError("PREPARATION_RELEASE_REQUIRED")
    expected = _expected_members()
    audit = audit_inputs(expected)
    destination = pathlib.Path(destination)
    if destination.exists() or destination.is_symlink():
        raise FileExistsError("archive-exists")
    destination.parent.mkdir(mode=0o700, parents=False, exist_ok=True)
    metadata = (json.dumps(audit, sort_keys=True) + "\n").encode()
    temp = destination.with_name(destination.name + f".tmp-{os.getpid()}")
    if destination.exists() or destination.is_symlink():
        raise FileExistsError("archive-exists")
    if os.stat(destination.parent).st_dev != os.stat(temp.parent).st_dev:
        raise RuntimeError("archive-parent-device-mismatch")
    temp_identity = None
    try:
        fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        stat_result = os.fstat(fd)
        temp_identity = (stat_result.st_dev, stat_result.st_ino)
    except FileExistsError:
        raise FileExistsError("archive-temp-exists")
    try:
        with os.fdopen(fd, "wb", closefd=True) as stream:
            with tarfile.open(fileobj=stream, mode="w", dereference=False) as archive:
                for path in ARCHIVE_INPUTS:
                    _add_no_replace(archive, path, path.name)
                info = tarfile.TarInfo("retention-manifest.json")
                info.mode = 0o600
                info.size = len(metadata)
                archive.addfile(info, io.BytesIO(metadata))
            stream.flush()
            os.fsync(stream.fileno())
        _verify_archive(temp, expected, temp_identity)
        if (os.stat(temp).st_dev, os.stat(temp).st_ino) != temp_identity:
            raise RuntimeError("archive-temp-replaced")
        temp_fd = os.open(temp, os.O_RDONLY | os.O_NOFOLLOW)
        os.close(temp_fd)
        os.link(temp, destination)
        if (os.stat(temp).st_dev, os.stat(temp).st_ino) != temp_identity:
            raise RuntimeError("archive-temp-replaced")
        os.unlink(temp)
        dfd = os.open(destination.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            os.fsync(dfd)
        finally:
            os.close(dfd)
    except Exception:
        if temp_identity is not None and (temp.exists() or temp.is_symlink()):
            current = temp.lstat()
            if (current.st_dev, current.st_ino) == temp_identity:
                temp.unlink()
        raise
    return {"archive": str(destination), "sha256": digest(destination), "source_excluded": True}


def relocation_plan() -> dict:
    """Return the later plan; this function has no filesystem side effects."""
    return {
        "schema": "mckernel.native-exact-candidate-relocation-plan.v1",
        "status": "NOT_EXECUTED",
        "source": str(CANDIDATE),
        "destination": str(DESTINATION),
        "source_commit": CANDIDATE_COMMIT,
        "source_identity": CANDIDATE_IDENTITY,
        "cross_filesystem": True,
        "no_replace": True,
        "verify_before_delete": True,
        "preserve_source_until_verified": True,
        "normalize_only_directory_st_size": True,
        "preserve_hashes_symlinks_hardlinks": True,
        "fsync_destination": True,
        "guards": [
            "process-reference-census", "docker/container-identity", "lease",
            "mount-and-ancestor-identity", "destination-absence",
            "source-device-identity", "host-capacity-floor", "operational-exclusion",
        ],
        "host_free_floor": HOST_FREE_FLOOR,
        "emergency_reserve": EMERGENCY_RESERVE,
        "destructive_action": "separate reviewed packet only",
    }


def main() -> int:
    print(json.dumps({"audit": audit_inputs() if os.environ.get("RETENTION_AUDIT") == "1" else "AUDIT_NOT_REQUESTED", "relocation": relocation_plan()}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
