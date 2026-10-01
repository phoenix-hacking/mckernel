#!/usr/bin/env python3
"""Produce a read-only restoration inventory for scratch-13 Git duplicates.

This inventory makes no quiescence or deletion-safety claim. A later cleanup
executor must perform a fresh authoritative census and reject stale plans.
This program never launches external services or mutates the candidate tree.
"""
import argparse, contextlib, hashlib, json, os, stat, subprocess, tempfile
from pathlib import Path

COMMIT = "6fed3a1022db0b4f9828dd42a8bd8f88fc052053"
ROOT = Path("/home/holden/mckernel-work/scratch/mckernel-exact-candidate-6fed3a10-scratch-13")
IDENTITY = "1831:3169097"
REPO = Path("/home/holden/mckernel")
IHK = ROOT / "ihk"
IHK_COMMIT = "3114d9e7101ad52030eb3effa849a5c108972a1f"
IHK_OVERLAY = IHK / "test/ihklib/whitebox/src/driver/mckernel/syscall.c"
IHK_OVERLAY_SHA256 = "7abb77fdc3049a54caebc3344de14c41e779502b4abcb7f301de4a647e15bf77"
SCRATCH = Path("/home/holden/mckernel-work/scratch")
EVIDENCE = ROOT / "docs/verification/evidence"
CONTAINER_ID = "aef5164c5209f62b5f1be6d545f34001779d2ed78008235114890f981635708b"
CONTAINER_NAME = "mckernel-image-bc0df6c9bd6d4234a1ec686df14ec493"
CONTAINER_NONCE = "5630f734cf3249d38945489942d03fad"
EXCLUSION = SCRATCH / "native-exact-candidate-operational-exclusion-exportset-25.json"
EXCLUSION_IDENTITY = "1831:90679"
EXCLUSION_SHA256 = "2eeed65d24ff927cee2421ff49dc3ee0351f682cf96e71517afa375a3f3d7c18"
PROTECTED = (
    ROOT / ".git", ROOT / "ihk",
    SCRATCH / "native-exact-build-evidence-6fed3a10-scratch-13",
    SCRATCH / "native-exact-build-output-6fed3a10-scratch-13",
    SCRATCH / "native-exact-metadata-evidence-6fed3a10-scratch-13",
    SCRATCH / "native-exact-metadata-backup-6fed3a10-scratch-13",
    SCRATCH / "native-exact-build-request-6fed3a10-scratch-13.json",
    SCRATCH / "native-exact-inputs-6fed3a10-scratch-13.json",
    SCRATCH / "native-exact-candidate-preparation-6fed3a10-scratch-13.log",
    SCRATCH / "native-exact-candidate-preparation-6fed3a10-scratch-13-terminal.json",
    SCRATCH / "native-exact-mckernel-image-prepare-inputs-6fed3a10-exportset-25.json",
    SCRATCH / "native-exact-mckernel-image-request-6fed3a10-exportset-25.json",
    SCRATCH / "native-exact-mckernel-image-toolchain-6fed3a10-exportset-25.json",
    SCRATCH / "native-exact-mckernel-image-owner-evidence-6fed3a10-exportset-25",
    SCRATCH / "native-exact-mckernel-image-work-6fed3a10-exportset-25",
    SCRATCH / "native-exact-mckernel-gitlink-inputs-6fed3a10-exportset-25.json",
    SCRATCH / "native-exact-mckernel-gitlink-libdwarf-6fed3a10-exportset-25",
    SCRATCH / "native-exact-mckernel-gitlink-preparation-6fed3a10-exportset-25.log",
    SCRATCH / "native-exact-mckernel-gitlink-preparation-6fed3a10-exportset-25-terminal.json",
    SCRATCH / "native-exact-mckernel-image-preparation-6fed3a10-exportset-25.log",
    SCRATCH / "native-exact-mckernel-image-preparation-6fed3a10-exportset-25-terminal.json",
    SCRATCH / "native-exact-rust-nightly-1.95.0-20260218-1",
    SCRATCH / "native-exact-build-output-4e99a82c-scratch-12",
    EXCLUSION,
)
ANCHORS = (ROOT, EVIDENCE)
NOFOLLOW = os.O_NOFOLLOW | os.O_CLOEXEC

def fail(message):
    raise SystemExit("FAIL_CLOSED: " + message)

def digest(data):
    return hashlib.sha256(data).hexdigest()

def canonical(path):
    p = str(path)
    if not p.startswith("/") or str(Path(p)) != p or any(x in (".", "..") for x in p.split("/")[1:]):
        fail("noncanonical path")
    return p

@contextlib.contextmanager
def directory(path):
    p = canonical(path); fd = os.open("/", os.O_RDONLY | os.O_DIRECTORY | NOFOLLOW)
    try:
        for component in p.split("/")[1:]:
            if component:
                nxt = os.open(component, os.O_RDONLY | os.O_DIRECTORY | NOFOLLOW, dir_fd=fd)
                os.close(fd); fd = nxt
        yield fd
    finally: os.close(fd)

@contextlib.contextmanager
def opened(path, flags=os.O_RDONLY):
    p = Path(canonical(path))
    with directory(str(p.parent)) as parent:
        fd = os.open(p.name, flags | NOFOLLOW, dir_fd=parent)
        try: yield fd
        finally: os.close(fd)

def metadata(s):
    return {"dev":s.st_dev, "ino":s.st_ino, "mode":stat.S_IMODE(s.st_mode),
            "size":s.st_size, "mtime_ns":s.st_mtime_ns, "nlink":s.st_nlink}

def hash_fd(fd):
    os.lseek(fd, 0, os.SEEK_SET); h = hashlib.sha256(); size = 0
    while True:
        b = os.read(fd, 1024 * 1024)
        if not b: return h.hexdigest(), size
        size += len(b); h.update(b)

def read_checked(path, expected=None):
    p = Path(canonical(path))
    with directory(str(p.parent)) as parent:
        parent_before = os.fstat(parent)
        fd = os.open(p.name, os.O_RDONLY | os.O_NONBLOCK | NOFOLLOW, dir_fd=parent)
        try:
            before = os.fstat(fd)
            if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1: fail("file-type-link")
            if expected and any(metadata(before).get(k) != expected.get(k) for k in metadata(before) if k in expected): fail("file-metadata")
            sha, size = hash_fd(fd); after = os.fstat(fd)
            namespace = os.stat(p.name, dir_fd=parent, follow_symlinks=False)
            with directory(str(p.parent)) as reopened_parent:
                parent_after = os.fstat(reopened_parent)
            parent_meta = lambda s: (s.st_dev, s.st_ino, stat.S_IMODE(s.st_mode), s.st_nlink)
            if parent_meta(parent_before) != parent_meta(parent_after) or metadata(before) != metadata(after) or metadata(after) != metadata(namespace): fail("file-changed-during-read")
            if expected and (("sha256" in expected and sha != expected["sha256"]) or ("size" in expected and size != expected["size"])): fail("file-content-race")
            return sha, size, before
        finally: os.close(fd)

def inspect_entry(path):
    p = Path(canonical(path))
    with directory(str(p.parent)) as parent:
        s = os.stat(p.name, dir_fd=parent, follow_symlinks=False)
    return s

def git(*args):
    env = os.environ.copy()
    env.update(GIT_NO_REPLACE_OBJECTS="1", GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull, GIT_OPTIONAL_LOCKS="0")
    return subprocess.check_output(
        ["git", "-c", f"safe.directory={REPO}", "-C", str(REPO), *args],
        stderr=subprocess.STDOUT, env=env).decode().strip()

def git_at(repo, *args):
    env = os.environ.copy()
    env.update(GIT_NO_REPLACE_OBJECTS="1", GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull, GIT_OPTIONAL_LOCKS="0")
    return subprocess.check_output(
        ["git", "-c", f"safe.directory={repo}", "-C", str(repo), *args],
        stderr=subprocess.STDOUT, env=env).decode().strip()

def git_status_at(repo):
    env = os.environ.copy()
    env.update(GIT_NO_REPLACE_OBJECTS="1", GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull, GIT_OPTIONAL_LOCKS="0")
    return subprocess.check_output(
        ["git", "-c", f"safe.directory={repo}", "-C", str(repo), "status", "--porcelain=v1"],
        stderr=subprocess.STDOUT, env=env).decode().rstrip("\n")

def git_blob(path):
    try:
        env = os.environ.copy()
        env.update(GIT_NO_REPLACE_OBJECTS="1", GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull, GIT_OPTIONAL_LOCKS="0")
        return subprocess.check_output(
            ["git", "-c", f"safe.directory={REPO}", "-C", str(REPO),
             "cat-file", "blob", f"{COMMIT}:{path}"], stderr=subprocess.STDOUT, env=env)
    except subprocess.CalledProcessError:
        return None

def guard():
    with directory(str(ROOT)) as fd:
        s = os.fstat(fd)
        if not stat.S_ISDIR(s.st_mode) or f"{s.st_dev}:{s.st_ino}" != IDENTITY: fail("candidate root binding")
    if git("rev-parse", COMMIT + "^{commit}") != COMMIT:
        fail("candidate commit unavailable")
    try:
        head = git("-C", str(ROOT), "rev-parse", "HEAD")
    except subprocess.CalledProcessError:
        fail("candidate checkout unavailable")
    if head != COMMIT:
        fail("candidate HEAD differs")
    with directory(str(IHK)) as fd:
        if not stat.S_ISDIR(os.fstat(fd).st_mode): fail("nested IHK binding")
    try:
        if git_at(IHK, "rev-parse", "HEAD") != IHK_COMMIT: fail("nested IHK HEAD differs")
        dirty = git_status_at(IHK)
    except (OSError, subprocess.CalledProcessError):
        fail("nested IHK checkout unavailable")
    if dirty != " M test/ihklib/whitebox/src/driver/mckernel/syscall.c": fail("nested IHK overlay differs")
    sha, _, _ = read_checked(str(IHK_OVERLAY))
    if sha != IHK_OVERLAY_SHA256: fail("nested IHK overlay bytes differ")
    sha, _, es = read_checked(str(EXCLUSION))
    if f"{es.st_dev}:{es.st_ino}" != EXCLUSION_IDENTITY or sha != EXCLUSION_SHA256:
        fail("operational exclusion binding differs")

def protected_inventory():
    rows = []
    for p in PROTECTED:
        if not p.is_absolute():
            fail("relative protected path")
        x = p.parent
        while x != x.parent:
            try:
                with directory(str(x)) as afd:
                    if not stat.S_ISDIR(os.fstat(afd).st_mode): fail("protected ancestor type: " + str(x))
            except OSError:
                fail("protected ancestor unavailable: " + str(x))
            x = x.parent
        try: s = inspect_entry(p)
        except OSError: fail("protected path missing: " + str(p))
        if stat.S_ISDIR(s.st_mode):
            with directory(str(p)) as fd:
                actual = os.fstat(fd)
                if (actual.st_dev, actual.st_ino, stat.S_IMODE(actual.st_mode)) != (s.st_dev, s.st_ino, stat.S_IMODE(s.st_mode)): fail("protected directory race")
            row = {"path": str(p), "dev": s.st_dev, "ino": s.st_ino, "mode": stat.S_IMODE(s.st_mode), "type": "directory"}
        elif stat.S_ISREG(s.st_mode) and s.st_nlink == 1:
            sha, size, actual = read_checked(str(p), metadata(s))
            row = {"path": str(p), "dev": actual.st_dev, "ino": actual.st_ino, "mode": stat.S_IMODE(actual.st_mode), "type": "file", "size": size, "sha256": sha, "nlink": actual.st_nlink}
        else: fail("protected special or hardlink: " + str(p))
        rows.append(row)
    return rows

def anchor_inventory():
    rows = []
    for p in ANCHORS:
        with directory(str(p)) as fd:
            s = os.fstat(fd)
            if not stat.S_ISDIR(s.st_mode): fail("anchor type")
            rows.append({"path":str(p), "type":"directory", "dev":s.st_dev, "ino":s.st_ino, "mode":stat.S_IMODE(s.st_mode)})
    return rows

def row(p, resolved, expected_meta):
    rel = "docs/verification/evidence/" + str(p.relative_to(EVIDENCE))
    expected = git_blob(rel)
    sha, size, s = read_checked(str(p), expected_meta)
    return {"path": str(p), "restore_git_path": rel,
            "blob": git("rev-parse", f"{COMMIT}:{rel}") if expected is not None else None,
            "mode": stat.S_IMODE(s.st_mode), "mtime_ns": s.st_mtime_ns,
            "size": size, "sha256": sha, "allocated_bytes": s.st_blocks * 512,
            "dev": s.st_dev, "ino": s.st_ino, "nlink": s.st_nlink}

def audit():
    guard(); local_protected = protected_inventory(); local_anchors = anchor_inventory()
    for p in (ROOT / "docs", ROOT / "docs/verification", EVIDENCE):
        try:
            with directory(str(p)) as afd:
                if not stat.S_ISDIR(os.fstat(afd).st_mode): fail("evidence ancestor")
        except OSError: fail("evidence ancestor")
    with directory(str(EVIDENCE)) as evidence_fd:
        if not stat.S_ISDIR(os.fstat(evidence_fd).st_mode): fail("evidence ancestor")
    resolved = str(EVIDENCE)
    if os.path.commonpath((str(ROOT), resolved)) != str(ROOT): fail("evidence escape")
    targets, preserved = [], []
    for p in sorted(EVIDENCE.rglob("*")):
        try: s = inspect_entry(p)
        except OSError: fail("entry disappeared or became inaccessible")
        if stat.S_ISLNK(s.st_mode) or not stat.S_ISREG(s.st_mode) or s.st_nlink != 1: continue
        if os.path.commonpath((resolved, str(p))) != resolved: fail("target escape")
        r = row(p, resolved, metadata(s)); expected = git_blob(r["restore_git_path"])
        (targets if expected is not None and r["sha256"] == digest(expected) and r["size"] == len(expected) else preserved).append(r)
    if not targets: fail("no exact Git duplicates")
    return {"schema": "mckernel.exact-git-source-audit.v1", "status": "AUDIT_PASS",
            "candidate_commit": COMMIT, "candidate_root": str(ROOT), "candidate_identity": IDENTITY,
            "targets": targets, "preserved": preserved, "protected_paths": [str(x) for x in PROTECTED],
            "protected_inventory": local_protected, "anchor_inventory": local_anchors,
            "nested_delta_preserved": True}

def publish(path, obj):
    path = Path(path); payload = (json.dumps(obj, sort_keys=True, indent=2) + "\n").encode()
    if path.exists() or path.is_symlink(): fail("plan collision")
    with tempfile.NamedTemporaryFile(mode="w+b", prefix=".6fed3a10-audit-", dir=path.parent, delete=True) as f:
        off = 0
        while off < len(payload): off += os.write(f.fileno(), payload[off:])
        os.fsync(f.fileno()); st = os.fstat(f.fileno())
        if st.st_nlink != 1 or os.path.lexists(path): fail("plan replacement/collision")
        os.link(f.name, path); d = os.open(path.parent, os.O_DIRECTORY); os.fsync(d); os.close(d)

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--plan", required=True)
    a = ap.parse_args(); publish(a.plan, audit()); print("AUDIT_PASS")

if __name__ == "__main__": raise SystemExit(main())
