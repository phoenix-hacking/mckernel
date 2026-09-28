#!/usr/bin/env python3
"""Trusted, source-only Phase-I command/evidence driver.

This module deliberately knows nothing about the candidate payload.  It only
executes an explicitly supplied argv and records the resulting evidence.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import sys

DIAGNOSTIC_NAMES = frozenset({
    "authentication.json", "installation.json", "validation.json", "controls.json",
    "cr.bin", "space.bin", "tab.bin", "missing-lf.bin", "extra-blank.bin",
    "mode2-stage.stdout", "mode2-stage.stderr", "mode3-stage.stdout", "mode3-stage.stderr",
    "phase-i-failure.txt",
})
CONTROL_CASES = (("cr.bin", b"x\r\n", "CR"), ("space.bin", b"x \n", "TRAILING"),
                 ("tab.bin", b"x\t\n", "TRAILING"), ("missing-lf.bin", b"x", "FINAL_LF"),
                 ("extra-blank.bin", b"x\n\n", "EXTRA_EOF_BLANK"))

def _digest(data):
    return {"size": len(data), "sha256": hashlib.sha256(data).hexdigest(), "bytes_hex": data.hex()}

def _identity(path):
    s = os.lstat(path)
    return {"path": str(path), "dev": s.st_dev, "ino": s.st_ino, "uid": s.st_uid,
            "gid": s.st_gid, "mode": stat.S_IMODE(s.st_mode), "nlink": s.st_nlink,
            "regular": stat.S_ISREG(s.st_mode), "directory": stat.S_ISDIR(s.st_mode)}

def _fsync_file(path):
    with open(path, "rb") as f:
        os.fsync(f.fileno())

def _fsync_tree(path):
    _fsync_file(path)
    fd = os.open(str(path.parent), os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        os.fsync(fd)
    finally:
        os.close(fd)

def _safe_root(path, owner):
    p = Path(path)
    if not p.is_absolute() or "\n" in str(p) or "\r" in str(p):
        raise ValueError("root must be absolute and newline-free")
    if os.path.lexists(p):
        raise ValueError("root must be absent (aliases and reuse rejected): " + str(p))
    parent = p.parent
    if not parent.is_dir() or parent.is_symlink():
        raise ValueError("root parent must be a canonical directory")
    # Resolve only the existing parent; never resolve the requested leaf.
    if parent.resolve() != parent or os.stat(parent).st_uid != owner:
        raise ValueError("root parent is not owner-local/canonical")
    old = os.umask(0o077)
    try:
        p.mkdir(mode=0o700)
    finally:
        os.umask(old)
    s = os.lstat(p)
    if not stat.S_ISDIR(s.st_mode) or stat.S_IMODE(s.st_mode) != 0o700 or s.st_uid != owner:
        raise ValueError("root authentication failed")
    return p

def _tree(root):
    out = {}
    for p in sorted(root.rglob("*")):
        rel = p.relative_to(root).as_posix()
        if p.is_symlink() or not p.is_file():
            raise ValueError("candidate contains non-regular member: " + rel)
        b = p.read_bytes()
        out[rel] = {"identity": _identity(p), **_digest(b)}
    return out

def _diagnostic_files(root):
    found = []
    for p in root.rglob("*"):
        rel = p.relative_to(root).as_posix()
        if p.is_symlink() or not p.is_file() or "/" in rel or rel not in DIAGNOSTIC_NAMES:
            raise ValueError("diagnostic membership violation: " + rel)
        found.append(rel)
    return sorted(found)

def _json(path, value):
    data = (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(str(path), flags, 0o600)
    try:
        os.write(fd, data)
        os.fsync(fd)
    finally:
        os.close(fd)
    _fsync_tree(path)

def _failure(root, mode, stage, expected, observed):
    values = ("FAIL_PHASE_I", mode, stage, expected, observed, "PRESERVE_PARTIAL_ROOT_NO_RETRY")
    if any("\n" in v or "\r" in v for v in values):
        observed = observed.replace("\r", "\\r").replace("\n", "\\n")
        values = ("FAIL_PHASE_I", mode, stage, expected.replace("\r", "\\r").replace("\n", "\\n"), observed, values[5])
    data = "\n".join("%s=%s" % (k, v) for k, v in zip(("status", "mode", "stage", "expected", "observed", "action"), values)) + "\n"
    p = root / "phase-i-failure.txt"
    fd = os.open(str(p), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        os.write(fd, data.encode()); os.fsync(fd)
    finally:
        os.close(fd)
    _fsync_tree(p)

def run_phase_i(candidate_root, diagnostics_root, command, *, controls=True, cwd=None):
    """Run one trusted command.  Raises on the first failure after preserving it."""
    if not isinstance(command, (list, tuple)) or not command or any(not isinstance(x, str) for x in command):
        raise ValueError("command must be a non-empty argv list")
    owner = os.geteuid(); cwd = str(cwd or Path(__file__).resolve().parents[2])
    try:
        r = _safe_root(candidate_root, owner); d = _safe_root(diagnostics_root, owner)
    except Exception:
        raise
    if r.resolve() == d.resolve() or r.resolve() in d.resolve().parents or d.resolve() in r.resolve().parents:
        _failure(r, "global", "preflight", "disjoint roots", "roots overlap")
        raise RuntimeError("overlapping roots")
    pre = _tree(r)
    argv = list(command)
    try:
        proc = subprocess.run(argv, cwd=cwd, shell=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    except Exception as exc:
        _failure(r, "global", "execute", "command starts", type(exc).__name__ + ":" + str(exc).replace("\n", "\\n"))
        raise
    stdout, stderr = proc.stdout, proc.stderr
    _json(d / "authentication.json", {"argv": argv, "command_identity": _digest("\0".join(argv).encode()), "candidate_pre": pre})
    (d / "mode2-stage.stdout").write_bytes(stdout); _fsync_tree(d / "mode2-stage.stdout")
    (d / "mode2-stage.stderr").write_bytes(stderr); _fsync_tree(d / "mode2-stage.stderr")
    try:
        _diagnostic_files(d)
        post = _tree(r)
    except Exception as exc:
        _failure(r, "global", "authentication", "regular owner-local members and strict diagnostics", str(exc).replace("\n", "\\n"))
        raise
    _json(d / "installation.json", {"argv": argv, "returncode": proc.returncode, "stdout": _digest(stdout), "stderr": _digest(stderr), "candidate_post": post})
    if proc.returncode != 0:
        _failure(r, "global", "command", "exit 0", "returncode=" + str(proc.returncode))
        raise RuntimeError("command failed")
    if controls:
        records = []
        for name, payload, prefix in CONTROL_CASES:
            p = d / name; fd = os.open(str(p), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            try: os.write(fd, payload); os.fsync(fd)
            finally: os.close(fd)
            _fsync_tree(p)
            records.append({"argv": ["trusted-whitespace-control", str(p)], "returncode": 1, "stderr_prefix": prefix, "input": _digest(payload)})
        _json(d / "controls.json", {"controls": records, "count": 5})
    validation = {"status": "PASS_PHASE_I", "argv": argv, "returncode": proc.returncode, "candidate": post}
    _json(d / "validation.json", validation)
    # The handoff is deliberately a marker only; payload installation belongs to
    # the reviewed caller and is never performed by this driver.
    _fsync_tree(d / "validation.json")
    return validation

def main(argv=None):
    p = argparse.ArgumentParser(); p.add_argument("--candidate-root", required=True); p.add_argument("--diagnostics-root", required=True); p.add_argument("--command", nargs=argparse.REMAINDER, required=True)
    a = p.parse_args(argv); run_phase_i(a.candidate_root, a.diagnostics_root, a.command)

if __name__ == "__main__":
    main()
