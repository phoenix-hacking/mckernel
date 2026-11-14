#!/usr/bin/env python3
"""Fail-closed two-phase cleanup of exact committed duplicate evidence.

This packet is inert unless --apply is supplied.  It only targets single-link
regular files whose bytes equal the pinned Git evidence blobs.  Directories,
links, special files, changed files, and files outside the exact target set
are never removed.
"""
import argparse
import hashlib
import json
import os
import stat
import subprocess
import sys
import tempfile
from pathlib import Path

CANDIDATE_COMMIT = "dce800af8c19d014ef509e102ca4f4b1c473e2ab"
CANDIDATE_ROOT = Path(
    "/home/holden/mckernel-work/retained-exact-candidates/"
    "mckernel-exact-candidate-dce800af-scratch-5"
)
CANDIDATE_IDENTITY = "66306:47736554"


def die(message):
    raise SystemExit("FAIL_CLOSED: " + message)


def git(repo, *args):
    return subprocess.check_output(
        ["git", "-C", str(repo), *args], stderr=subprocess.STDOUT
    ).decode().strip()


def root_guard(root, repo, commit):
    root = Path(root)
    if root != CANDIDATE_ROOT or not root.is_absolute():
        die("wrong candidate root")
    if commit != CANDIDATE_COMMIT:
        die("wrong candidate commit")
    if root.is_symlink() or not root.is_dir():
        die("candidate root is not a directory")
    expected_dev, expected_ino = (int(value) for value in CANDIDATE_IDENTITY.split(":"))
    root_stat = root.stat()
    if (root_stat.st_dev, root_stat.st_ino) != (expected_dev, expected_ino):
        die("candidate root identity differs")
    try:
        git(repo, "cat-file", "-e", commit + "^{commit}")
    except subprocess.CalledProcessError:
        die("commit unavailable")
    try:
        head = git(root, "rev-parse", "HEAD")
    except Exception:
        die("candidate checkout unavailable")
    if head != commit:
        die("candidate HEAD differs")


def blob(repo, commit, rel):
    try:
        return git(repo, "rev-parse", f"{commit}:docs/verification/evidence/{rel}")
    except subprocess.CalledProcessError:
        return None


def evidence_base(root):
    root = Path(root)
    base = root / "docs/verification/evidence"
    for ancestor in (root / "docs", root / "docs/verification", base):
        if ancestor.is_symlink() or not ancestor.is_dir():
            die("evidence ancestor missing or linked")
    resolved_root = root.resolve(strict=True)
    resolved_base = base.resolve(strict=True)
    if os.path.commonpath((str(resolved_root), str(resolved_base))) != str(resolved_root):
        die("evidence path escapes candidate")
    return base, resolved_base


def audit(root=CANDIDATE_ROOT, repo=Path(__file__).parents[3], commit=CANDIDATE_COMMIT):
    root_guard(root, repo, commit)
    base, resolved_base = evidence_base(root)
    rows = []
    for path in sorted(base.rglob("*")):
        st = path.lstat()
        if not stat.S_ISREG(st.st_mode) or st.st_nlink != 1:
            continue
        if os.path.commonpath((str(resolved_base), str(path.resolve(strict=True)))) != str(resolved_base):
            die("target escapes evidence directory")
        rel = str(path.relative_to(base))
        blob_id = blob(repo, commit, rel)
        if not blob_id:
            continue
        data = path.read_bytes()
        expected = subprocess.check_output(
            ["git", "-C", str(repo), "cat-file", "blob", blob_id]
        )
        digest = hashlib.sha256(data).hexdigest()
        if (
            len(expected) != st.st_size
            or hashlib.sha256(expected).hexdigest() != digest
            or expected != data
        ):
            die("file changed or blob mismatch: " + rel)
        rows.append(
            {
                "path": str(path),
                "restore_git_path": "docs/verification/evidence/" + rel,
                "blob": blob_id,
                "mode": stat.S_IMODE(st.st_mode),
                "mtime_ns": st.st_mtime_ns,
                "size": st.st_size,
                "sha256": digest,
                "allocated_bytes": st.st_blocks * 512,
                "dev": st.st_dev,
                "ino": st.st_ino,
            }
        )
    if not rows:
        die("no exact duplicate evidence targets")
    return {
        "schema": "mckernel.exact-evidence-cleanup.v1",
        "status": "AUDIT_PASS",
        "candidate_commit": commit,
        "candidate_root": str(root),
        "candidate_identity": CANDIDATE_IDENTITY,
        "targets": rows,
        "recovery": "restore each restore_git_path from blob at candidate_commit",
    }


def atomic_write(path, obj):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".cleanup-", dir=path.parent)
    os.close(fd)
    try:
        Path(temporary).write_text(json.dumps(obj, sort_keys=True, indent=2) + "\n")
        with open(temporary, "rb") as stream:
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        directory = os.open(path.parent, os.O_DIRECTORY)
        os.fsync(directory)
        os.close(directory)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def apply(plan):
    if plan.get("schema") != "mckernel.exact-evidence-cleanup.v1" or plan.get("status") != "AUDIT_PASS":
        die("invalid audit plan")
    root = Path(plan.get("candidate_root", ""))
    commit = plan.get("candidate_commit", "")
    root_guard(root, Path(__file__).parents[3], commit)
    fresh = audit(root, Path(__file__).parents[3], commit)
    if plan != fresh:
        die("audit plan differs from current exact audit")
    for row in plan["targets"]:
        path = Path(row["path"])
        _, resolved_base = evidence_base(root)
        if os.path.commonpath((str(resolved_base), str(path.resolve(strict=True)))) != str(resolved_base):
            die("final target escapes evidence directory")
        st = path.lstat()
        if (
            not stat.S_ISREG(st.st_mode)
            or st.st_nlink != 1
            or st.st_dev != row["dev"]
            or st.st_ino != row["ino"]
            or st.st_size != row["size"]
            or stat.S_IMODE(st.st_mode) != row["mode"]
            or hashlib.sha256(path.read_bytes()).hexdigest() != row["sha256"]
        ):
            die("final target revalidation failed: " + str(path))
        os.unlink(path)
    plan["status"] = "APPLY_PASS"
    plan["removed"] = [row["path"] for row in plan["targets"]]
    plan["removed_allocated_bytes"] = sum(
        row["allocated_bytes"] for row in plan["targets"]
    )
    return plan


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", required=True)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    if args.apply:
        result = apply(json.loads(Path(args.plan).read_text()))
    else:
        result = audit()
    atomic_write(args.plan, result)
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
