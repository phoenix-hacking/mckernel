#!/usr/bin/env python3
"""Fail-closed two-phase cleanup for candidate 61bf exact Git duplicates.

The default operation only audits.  Applying a plan requires a fresh identical
audit and revalidates every inode immediately before unlinking it.
"""
import argparse
import hashlib
import json
import os
import stat
import subprocess
import tempfile
from pathlib import Path

CANDIDATE_COMMIT = "61bfbb6cc059f5382b0b19361ff96bf51409620c"
CANDIDATE_ROOT = Path("/home/holden/mckernel-work/retained-exact-candidates/mckernel-exact-candidate-61bfbb6c-scratch-5")
CANDIDATE_IDENTITY = "66306:47622717"


def die(message):
    raise SystemExit("FAIL_CLOSED: " + message)


def git(repo, *args):
    return subprocess.check_output(["git", "-C", str(repo), *args], stderr=subprocess.STDOUT).decode().strip()


def root_guard(root, repo, commit):
    root = Path(root)
    if root != CANDIDATE_ROOT or not root.is_absolute():
        die("wrong candidate root")
    if commit != CANDIDATE_COMMIT:
        die("wrong candidate commit")
    if root.is_symlink() or not root.is_dir():
        die("candidate root is not a directory")
    dev, ino = (int(x) for x in CANDIDATE_IDENTITY.split(":"))
    st = root.stat()
    if (st.st_dev, st.st_ino) != (dev, ino):
        die("candidate root identity differs")
    try:
        if git(repo, "rev-parse", commit + "^{commit}") != commit:
            die("commit unavailable")
        if git(root, "rev-parse", "HEAD") != commit:
            die("candidate HEAD differs")
    except (OSError, subprocess.CalledProcessError):
        die("candidate checkout unavailable")


def evidence_base(root):
    root = Path(root)
    base = root / "docs/verification/evidence"
    for parent in (root / "docs", root / "docs/verification", base):
        if parent.is_symlink() or not parent.is_dir():
            die("evidence ancestor missing or linked")
    rr, rb = root.resolve(strict=True), base.resolve(strict=True)
    if os.path.commonpath((str(rr), str(rb))) != str(rr):
        die("evidence path escapes candidate")
    return base, rb


def audit(root=CANDIDATE_ROOT, repo=Path(__file__).parents[3], commit=CANDIDATE_COMMIT):
    root_guard(root, repo, commit)
    base, resolved = evidence_base(root)
    rows = []
    for path in sorted(base.rglob("*")):
        st = path.lstat()
        if not stat.S_ISREG(st.st_mode) or st.st_nlink != 1:
            continue
        if os.path.commonpath((str(resolved), str(path.resolve(strict=True)))) != str(resolved):
            die("target escapes evidence directory")
        rel = str(path.relative_to(base))
        try:
            blob_id = git(repo, "rev-parse", f"{commit}:docs/verification/evidence/{rel}")
            expected = subprocess.check_output(["git", "-C", str(repo), "cat-file", "blob", blob_id])
        except subprocess.CalledProcessError:
            continue
        data = path.read_bytes()
        digest = hashlib.sha256(data).hexdigest()
        if len(expected) != st.st_size or expected != data or hashlib.sha256(expected).hexdigest() != digest:
            die("file changed or blob mismatch: " + rel)
        rows.append({"path": str(path), "restore_git_path": "docs/verification/evidence/" + rel,
                     "blob": blob_id, "mode": stat.S_IMODE(st.st_mode), "mtime_ns": st.st_mtime_ns,
                     "size": st.st_size, "sha256": digest, "allocated_bytes": st.st_blocks * 512,
                     "dev": st.st_dev, "ino": st.st_ino})
    if not rows:
        die("no exact duplicate evidence targets")
    return {"schema": "mckernel.exact-evidence-cleanup.v1", "status": "AUDIT_PASS",
            "candidate_commit": commit, "candidate_root": str(root),
            "candidate_identity": CANDIDATE_IDENTITY, "targets": rows,
            "recovery": "restore each restore_git_path from blob at candidate_commit"}


def atomic_write(path, obj):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".cleanup-", dir=path.parent)
    os.close(fd)
    try:
        Path(tmp).write_text(json.dumps(obj, sort_keys=True, indent=2) + "\n")
        with open(tmp, "rb") as stream:
            os.fsync(stream.fileno())
        os.replace(tmp, path)
        directory = os.open(path.parent, os.O_DIRECTORY)
        os.fsync(directory)
        os.close(directory)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def apply(plan):
    if plan.get("schema") != "mckernel.exact-evidence-cleanup.v1" or plan.get("status") != "AUDIT_PASS":
        die("invalid audit plan")
    root, commit = Path(plan.get("candidate_root", "")), plan.get("candidate_commit", "")
    repo = Path(__file__).parents[3]
    root_guard(root, repo, commit)
    if plan != audit(root, repo, commit):
        die("audit plan differs from current exact audit")
    _, resolved = evidence_base(root)
    for row in plan["targets"]:
        path = Path(row["path"])
        if os.path.commonpath((str(resolved), str(path.resolve(strict=True)))) != str(resolved):
            die("final target escapes evidence directory")
        st = path.lstat()
        if (not stat.S_ISREG(st.st_mode) or st.st_nlink != 1 or st.st_dev != row["dev"] or
            st.st_ino != row["ino"] or st.st_size != row["size"] or
            stat.S_IMODE(st.st_mode) != row["mode"] or hashlib.sha256(path.read_bytes()).hexdigest() != row["sha256"]):
            die("final target revalidation failed: " + str(path))
        os.unlink(path)
    plan["status"] = "APPLY_PASS"
    plan["removed"] = [row["path"] for row in plan["targets"]]
    plan["removed_allocated_bytes"] = sum(row["allocated_bytes"] for row in plan["targets"])
    return plan


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", required=True)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    result = apply(json.loads(Path(args.plan).read_text())) if args.apply else audit()
    atomic_write(args.plan, result)
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
