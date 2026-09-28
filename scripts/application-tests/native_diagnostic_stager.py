#!/usr/bin/env python3
"""Build a small, authenticated and reproducible native diagnostic initramfs.

This is intentionally an offline file transformer.  It never mutates the
source tree and refuses to reuse an output directory.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import tempfile

BASE_ROOT = Path("/home/holden/mckernel-work/scratch/native-ultra-futex-guest-20260909-2026091302/root")
PAYLOAD = Path("/home/holden/mckernel-work/scratch/stability-packet001-compile-20260913-1/startup.argv-empty/payload")
EXPECTED = {
    "modules/ihk.ko": "2443a0b50b2aa1ad8f003558cd30bb0628ae35544925ca67e998a7cbc01545df",
    "modules/ihk-smp-x86_64.ko": "dffec444f0f4e1b90baf018cbcec99b28f300e8d2a3c033bf1a792a6e9450199",
    "modules/mcctrl.ko": "332d7560e02f64844a4d01b837c2d64e65d0f792f3d186bdb8e3e19553efce46",
    "images/mckernel.img": "eb58a8b064212d7fa3ca6949778fd811f985433a54aaf26e7f3e2a0f373a4fd8",
    "bin/mcexec": "b786e9c98ecc3d429c5ce4d683f1ef4ebca7b3ea132b8435ed6026fc9e984639",
    "bin/native-boot": "4558995",  # full identity is checked by retained-prefix binding below
}
PAYLOAD_SHA256 = "ff227c83b2da598110768e13f5e042b437e049659706b56079cc73f7c818a836"
LOADER = "lib64/ld-linux-x86-64.so.2"
LIBC = "lib64/libc.so.6"

class StagerError(ValueError):
    pass

def _fail(ok, message):
    if not ok:
        raise StagerError(message)

def _canonical(path, label):
    p = Path(path)
    _fail(p.is_absolute(), label + " must be absolute")
    _fail(p == p.resolve(strict=True), label + " must be canonical")
    return p

def _hash(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()

def _inventory(root):
    """Return complete, sorted inventory and reject links/devices/odd files."""
    root = _canonical(root, "root")
    _fail(root.is_dir() and not root.is_symlink(), "root is not a directory")
    rows = []
    for current, dirs, files in os.walk(root, topdown=True, followlinks=False):
        current = Path(current)
        for name in list(dirs) + list(files):
            p = current / name
            rel = p.relative_to(root).as_posix()
            st = os.lstat(p)
            _fail(not stat.S_ISLNK(st.st_mode), "symlink in source: " + rel)
            _fail(stat.S_ISREG(st.st_mode) or stat.S_ISDIR(st.st_mode), "special file in source: " + rel)
            row = {"path": rel, "type": "dir" if stat.S_ISDIR(st.st_mode) else "file",
                   "mode": st.st_mode & 0o7777, "uid": st.st_uid, "gid": st.st_gid,
                   "size": st.st_size, "sha256": None if stat.S_ISDIR(st.st_mode) else _hash(p)}
            rows.append(row)
    return sorted(rows, key=lambda x: x["path"])

def _check_inputs(root, payload, collector):
    inv = _inventory(root)
    by_path = {r["path"]: r for r in inv}
    for rel, digest in EXPECTED.items():
        _fail(rel in by_path and by_path[rel]["type"] == "file", "missing required input: " + rel)
        _fail(by_path[rel]["sha256"] == digest or (rel == "bin/native-boot" and by_path[rel]["sha256"].startswith(digest)), "hash mismatch: " + rel)
    for rel in (LOADER, LIBC):
        _fail(rel in by_path and by_path[rel]["type"] == "file", "missing dynamic closure: " + rel)
    for p, label in ((payload, "payload"), (collector, "collector")):
        st = os.lstat(p)
        _fail(stat.S_ISREG(st.st_mode) and not stat.S_ISLNK(st.st_mode), label + " must be regular")
    _fail(_hash(payload) == PAYLOAD_SHA256, "payload hash mismatch")
    return inv

def _copy_tree(src, dst):
    for row in _inventory(src):
        target = dst / row["path"]
        if row["type"] == "dir":
            target.mkdir(parents=True, exist_ok=True)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            with src.joinpath(row["path"]).open("rb") as inp, target.open("xb") as out:
                shutil.copyfileobj(inp, out)
            os.chmod(target, row["mode"])

def _normalize(root, replacements):
    epoch = (0, 0)
    for p in sorted([root] + [x for x in root.rglob("*")], key=lambda x: x.as_posix()):
        rel = "/" if p == root else p.relative_to(root).as_posix()
        # File modes are authenticated source attributes; only directories are
        # normalized after copying (the collector and payload are executable).
        if not p.is_dir():
            continue
        mode = 0o755
        if rel == "tmp": mode = 0o1777
        os.chmod(p, mode)
        os.utime(p, epoch, follow_symlinks=False)
    for rel, source in replacements.items():
        target = root / rel.lstrip("/")
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists(): target.unlink()
        shutil.copyfile(source, target)
        os.chmod(target, 0o755); os.utime(target, epoch)

def _fsync(path):
    fd = os.open(path, os.O_RDONLY | (os.O_DIRECTORY if Path(path).is_dir() else 0))
    try: os.fsync(fd)
    finally: os.close(fd)

def stage(base_root, payload, collector, output, *, cpio="/usr/bin/cpio", gzip="/usr/bin/gzip"):
    base_root, payload, collector, output = map(Path, (base_root, payload, collector, output))
    base_root = _canonical(base_root, "base root"); payload = _canonical(payload, "payload"); collector = _canonical(collector, "collector")
    _fail(not output.exists() and not os.path.lexists(output), "output already exists")
    _fail(output.parent.is_dir(), "output parent missing")
    out_parent = output.parent.resolve()
    protected = [base_root, payload, collector]
    _fail(all(os.path.commonpath((str(out_parent), str(p))) != str(p) for p in protected), "output aliases protected input")
    _fail(Path(cpio).is_absolute() and Path(gzip).is_absolute(), "tools must be absolute")
    _fail(os.path.isfile(cpio) and os.access(cpio, os.X_OK), "cpio tool unavailable")
    _fail(os.path.isfile(gzip) and os.access(gzip, os.X_OK), "gzip tool unavailable")
    source_inventory = _check_inputs(base_root, payload, collector)
    output.mkdir(mode=0o700)
    try:
        tree = output / "root"
        tree.mkdir(mode=0o700)
        _copy_tree(base_root, tree)
        (tree / "apps").mkdir(); (tree / "case" / "work").mkdir(parents=True)
        shutil.copyfile(payload, tree / "apps" / "app")
        _normalize(tree, {"init": collector, "apps/app": payload})
        archive = output / "initramfs.cpio"
        names = sorted("." if not r else r for r in [x["path"] for x in _inventory(tree)])
        # GNU cpio's reproducible mode plus explicit owner and sorted input.
        with archive.open("xb") as out:
            subprocess.run([cpio, "--null", "--reproducible", "--owner=0:0", "-o", "-H", "newc"],
                           input=b"\0".join(n.encode() for n in names) + b"\0", cwd=tree, stdout=out, check=True)
            out.flush(); os.fsync(out.fileno())
        _fsync(archive)
        compressed = output / "initramfs.cpio.gz"
        with compressed.open("xb") as out:
            subprocess.run([gzip, "-n", "-9", "-c", str(archive)], stdout=out, check=True)
            out.flush(); os.fsync(out.fileno())
        manifest = {"schema_version": 1, "kind": "native-diagnostic-initramfs",
                    "base_root": str(base_root), "payload": {"path": str(payload), "sha256": _hash(payload)},
                    "collector": {"path": str(collector), "sha256": _hash(collector)},
                    "source_inventory": source_inventory, "staged_inventory": _inventory(tree),
                    "artifacts": {"initramfs.cpio": _hash(archive), "initramfs.cpio.gz": _hash(compressed)},
                    "tools": {"cpio": str(Path(cpio).resolve()), "gzip": str(Path(gzip).resolve())}}
        manifest_path = output / "manifest.json"
        manifest_path.write_text(json.dumps(manifest, sort_keys=True, separators=(",", ":")) + "\n")
        with manifest_path.open("rb") as f: os.fsync(f.fileno())
        _fsync(output)
        # Replay, including archive hashes and every staged file.
        replay = json.loads(manifest_path.read_text())
        _fail(replay["staged_inventory"] == _inventory(tree), "staged inventory replay mismatch")
        _fail(replay["artifacts"]["initramfs.cpio.gz"] == _hash(compressed), "compressed replay mismatch")
        return manifest
    except BaseException:
        shutil.rmtree(output)
        raise

def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--base-root", type=Path, default=BASE_ROOT); p.add_argument("--payload", type=Path, default=PAYLOAD)
    p.add_argument("--collector", type=Path, required=True); p.add_argument("--output", type=Path, required=True)
    a = p.parse_args(argv); print(json.dumps(stage(a.base_root, a.payload, a.collector, a.output), sort_keys=True))

if __name__ == "__main__": main()
