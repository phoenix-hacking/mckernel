#!/usr/bin/env python3
"""Build a small, authenticated and reproducible native diagnostic initramfs.

This is intentionally an offline file transformer.  It never mutates the
source tree and refuses to reuse an output directory.
"""
from __future__ import annotations

import argparse
from contextlib import ExitStack
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import tempfile
import types

MCEEXEC_SHA256 = "ee1f660b6c181bb2301bcde8b30c109659f74d52b30407fa6f273d27c02d073b"
MCEEXEC_SIZE = 453352
BASE_ROOT = Path("/home/holden/mckernel-work/scratch/native-ultra-futex-guest-20260909-2026091302/root")
PAYLOAD = Path("/home/holden/mckernel-work/scratch/stability-packet001-compile-20260913-1/startup.argv-empty/payload")
EXPECTED = {
    "modules/ihk.ko": "2443a0b50b2aa1ad8f003558cd30bb0628ae35544925ca67e998a7cbc01545df",
    "modules/ihk-smp-x86_64.ko": "dffec444f0f4e1b90baf018cbcec99b28f300e8d2a3c033bf1a792a6e9450199",
    "modules/mcctrl.ko": "332d7560e02f64844a4d01b837c2d64e65d0f792f3d186bdb8e3e19553efce46",
    "images/mckernel.img": "eb58a8b064212d7fa3ca6949778fd811f985433a54aaf26e7f3e2a0f373a4fd8",
    "bin/mcexec": MCEEXEC_SHA256,
    "bin/native-boot": "4558995",  # full identity is checked by retained-prefix binding below
}
PAYLOAD_SHA256 = "ff227c83b2da598110768e13f5e042b437e049659706b56079cc73f7c818a836"
LOADER = "lib64/ld-linux-x86-64.so.2"
LIBC = "lib64/libc.so.6"
REPLACEMENT_PATHS = frozenset(("images/mckernel.img", "modules/ihk.ko",
                               "modules/ihk-smp-x86_64.ko", "modules/mcctrl.ko"))
MCEEXEC_REPLACEMENT_PATHS = REPLACEMENT_PATHS | frozenset(("bin/mcexec",))

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

def _check_inputs(root, payload, collector, replacements=()):
    inv = _inventory(root)
    by_path = {r["path"]: r for r in inv}
    for rel, digest in EXPECTED.items():
        _fail(rel in by_path and by_path[rel]["type"] == "file", "missing required input: " + rel)
        if rel in replacements:
            continue
        _fail(by_path[rel]["sha256"] == digest or (rel == "bin/native-boot" and by_path[rel]["sha256"].startswith(digest)), "hash mismatch: " + rel)
    for rel in (LOADER, LIBC):
        _fail(rel in by_path and by_path[rel]["type"] == "file", "missing dynamic closure: " + rel)
    for p, label in ((payload, "payload"), (collector, "collector")):
        st = os.lstat(p)
        _fail(stat.S_ISREG(st.st_mode) and not stat.S_ISLNK(st.st_mode), label + " must be regular")
    _fail(_hash(payload) == PAYLOAD_SHA256, "payload hash mismatch")
    return inv

def _open_source(path):
    """Resolve from / with no symlink-following at any component."""
    p = Path(path)
    _fail(p.is_absolute() and str(p) == str(path) and ".." not in p.parts,
          "replacement source must be an absolute normalized path")
    fd = os.open("/", os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    parents = []
    try:
        for component in p.parts[1:-1]:
            st = os.fstat(fd); parents.append((st.st_dev, st.st_ino))
            child = os.open(component, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd); fd = child
        st = os.fstat(fd); parents.append((st.st_dev, st.st_ino))
        result = os.open(p.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=fd)
        return result, parents
    except OSError as exc:
        raise StagerError("unsafe replacement source path: " + str(path)) from exc
    finally:
        os.close(fd)

def _source_stamp(st):
    return (st.st_dev, st.st_ino, st.st_mode, st.st_size, st.st_mtime_ns, st.st_ctime_ns)

def _hash_fd(fd):
    os.lseek(fd, 0, os.SEEK_SET)
    h = hashlib.sha256()
    while True:
        block = os.read(fd, 1024 * 1024)
        if not block: break
        h.update(block)
    os.lseek(fd, 0, os.SEEK_SET)
    return h.hexdigest()

def _authenticate_source(path, stack):
    fd, parents = _open_source(path)
    stack.callback(os.close, fd)
    before = os.fstat(fd)
    _fail(stat.S_ISREG(before.st_mode), "replacement source must be regular")
    digest = _hash_fd(fd)
    _fail(_source_stamp(before) == _source_stamp(os.fstat(fd)), "source changed while hashing")
    return {"path": str(path), "sha256": digest, "size": before.st_size,
            "mode": stat.S_IMODE(before.st_mode), "dev": before.st_dev, "inode": before.st_ino,
            "_fd": fd, "_parents": parents, "_stamp": _source_stamp(before)}

def _recheck_source(descriptor):
    fd, parents = _open_source(descriptor["path"])
    try:
        _fail(parents == descriptor["_parents"] and
              _source_stamp(os.fstat(fd)) == descriptor["_stamp"] and
              _source_stamp(os.fstat(descriptor["_fd"])) == descriptor["_stamp"],
              "replacement source or parent changed: " + descriptor["path"])
    finally:
        os.close(fd)

def _replacement_map(value, stack):
    """Authenticate four kernel artifacts and, optionally, corrected mcexec."""
    keys = set(value) if isinstance(value, dict) else set()
    _fail(isinstance(value, dict) and keys in (set(REPLACEMENT_PATHS),
                                               set(MCEEXEC_REPLACEMENT_PATHS)),
          "replacement map must contain the four kernel artifacts and optional mcexec")
    result = {}; seen_sources = set()
    for rel in sorted(keys):
        item = value[rel]
        _fail(isinstance(item, dict) and set(item) == {"path", "sha256", "size", "mode"},
              "malformed replacement descriptor: " + rel)
        try:
            source = Path(item["path"])
        except (TypeError, ValueError):
            raise StagerError("invalid replacement source: " + rel)
        try:
            expected_size = int(item["size"]); expected_mode = int(item["mode"])
        except (TypeError, ValueError):
            raise StagerError("invalid replacement size/mode: " + rel)
        _fail(isinstance(item["sha256"], str) and len(item["sha256"]) == 64 and all(c in "0123456789abcdef" for c in item["sha256"]),
              "invalid replacement hash: " + rel)
        descriptor = _authenticate_source(item["path"], stack)
        identity = (descriptor["dev"], descriptor["inode"])
        _fail(identity not in seen_sources, "replacement source alias: " + rel)
        seen_sources.add(identity)
        _fail(expected_size >= 0 and expected_mode == descriptor["mode"] and descriptor["size"] == expected_size,
              "replacement source metadata mismatch: " + rel)
        _fail(descriptor["sha256"] == item["sha256"], "replacement source hash mismatch: " + rel)
        if rel == "bin/mcexec":
            _fail(descriptor["sha256"] == MCEEXEC_SHA256 and
                  descriptor["size"] == MCEEXEC_SIZE and descriptor["mode"] == 0o755,
                  "mcexec replacement is not the exact corrected executable")
        _recheck_source(descriptor)
        result[rel] = descriptor
    return result

def _copy_tree(src, dst, replacements=()):
    replacements = set(replacements)
    for row in _inventory(src):
        if row["path"] in replacements:
            continue
        target = dst / row["path"]
        if row["type"] == "dir":
            target.mkdir(parents=True, exist_ok=True)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            with src.joinpath(row["path"]).open("rb") as inp, target.open("xb") as out:
                shutil.copyfileobj(inp, out)
                os.chmod(target, row["mode"])

def _copy_replacement(source, target, descriptor):
    parent = target.parent
    while parent != parent.parent and parent.exists():
        _fail(not parent.is_symlink() and parent.is_dir(), "replacement target parent is unsafe")
        parent = parent.parent
    target.parent.mkdir(parents=True, exist_ok=True)
    _fail(not os.path.lexists(target), "replacement target already exists: " + str(target))
    _recheck_source(descriptor)
    source_fd = os.dup(descriptor["_fd"])
    os.lseek(source_fd, 0, os.SEEK_SET)
    try:
        before = os.fstat(source_fd)
        _fail(stat.S_ISREG(before.st_mode) and before.st_size == descriptor["size"] and
              before.st_dev == descriptor["dev"] and before.st_ino == descriptor["inode"] and
              (before.st_mode & 0o7777) == descriptor["mode"],
              "replacement source changed: " + descriptor["path"])
        h = hashlib.sha256(); total = 0
        fd = os.open(str(target), os.O_WRONLY | os.O_CREAT | os.O_EXCL |
                     getattr(os, "O_NOFOLLOW", 0), descriptor["mode"])
        try:
            while True:
                block = os.read(source_fd, 1024 * 1024)
                if not block: break
                offset = 0
                while offset < len(block):
                    written = os.write(fd, block[offset:])
                    _fail(written > 0, "short replacement write: " + descriptor["path"])
                    offset += written
                h.update(block); total += len(block)
            os.fsync(fd)
        finally:
            os.close(fd)
        after = os.fstat(source_fd)
        _fail(total == descriptor["size"] and h.hexdigest() == descriptor["sha256"] and
              (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns, before.st_ctime_ns) ==
              (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns),
              "replacement source changed while copying: " + descriptor["path"])
        os.chmod(target, descriptor["mode"])
        _recheck_source(descriptor)
    finally:
        # Retain any partial target as failure evidence; exclusive creation
        # prevents a later attempt from overwriting it.
        os.close(source_fd)

def _normalize(root):
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

def _archive_members(path, inventory):
    """Stream and authenticate every newc field and body with bounded reads."""
    expected = {r["path"]: r for r in inventory}
    _fail(len(expected) == len(inventory), "duplicate inventory path")
    seen = set()
    with Path(path).open("rb") as stream:
        def read(n):
            data = stream.read(n)
            _fail(len(data) == n, "truncated archive")
            return data
        def padding():
            _fail(read((-stream.tell()) % 4).strip(b"\0") == b"", "nonzero archive alignment")
        for _ in range(len(inventory) + 1):
            header = read(110)
            _fail(header[:6] == b"070701" and
                  all(c in b"0123456789abcdefABCDEF" for c in header[6:]), "invalid newc header")
            fields = [int(header[i:i + 8], 16) for i in range(6, 110, 8)]
            ino, mode, uid, gid, nlink, mtime, size, devmaj, devmin, rmaj, rmin, namesize, checksum = fields
            _fail(1 < namesize <= 4096 and checksum == 0 and rmaj == rmin == 0,
                  "invalid newc metadata")
            raw = read(namesize)
            _fail(raw[-1:] == b"\0" and b"\0" not in raw[:-1], "invalid archive name")
            try: name = raw[:-1].decode("utf-8", "strict")
            except UnicodeDecodeError as exc: raise StagerError("invalid archive path encoding") from exc
            padding()
            if name == "TRAILER!!!":
                _fail(size == mode == uid == gid == devmaj == devmin == 0 and nlink == 1,
                      "invalid archive trailer")
                _fail(seen == set(expected), "archive members do not match staged inventory")
                tail = stream.read(512)
                _fail(len(tail) <= 511 and not tail.strip(b"\0") and
                      stream.tell() % 512 == 0, "invalid archive trailing padding")
                return sorted(seen)
            _fail(name in expected and name not in seen and not name.startswith("/") and
                  all(part not in ("", ".", "..") for part in name.split("/")),
                  "unexpected or duplicate archive member")
            row = expected[name]; seen.add(name)
            expected_type = stat.S_IFREG if row["type"] == "file" else stat.S_IFDIR
            _fail(mode == expected_type | row["mode"] and uid == gid == 0 and
                  devmaj == devmin == 0 and nlink >= 1,
                  "archive member metadata mismatch: " + name)
            _fail(size == (row["size"] if row["type"] == "file" else 0) and
                  (row["type"] != "file" or nlink == 1), "archive member size/link mismatch: " + name)
            digest = hashlib.sha256(); remaining = size
            while remaining:
                block = read(min(remaining, 1024 * 1024)); digest.update(block); remaining -= len(block)
            _fail(row["type"] != "file" or digest.hexdigest() == row["sha256"],
                  "archive member content mismatch: " + name)
            padding()
    raise StagerError("archive missing trailer")

def _fsync(path):
    fd = os.open(path, os.O_RDONLY | (os.O_DIRECTORY if Path(path).is_dir() else 0))
    try: os.fsync(fd)
    finally: os.close(fd)

def stage(base_root, payload, collector, output, *, cpio="/usr/bin/cpio", gzip="/usr/bin/gzip",
          replacements=None):
    with ExitStack() as sources:
        return _stage(base_root, payload, collector, output, cpio=cpio, gzip=gzip,
                      replacements=replacements, sources=sources)

def _stage(base_root, payload, collector, output, *, cpio, gzip, replacements, sources):
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
    replacements = _replacement_map(replacements, sources) if replacements is not None else {}
    source_inventory = _check_inputs(base_root, payload, collector, replacements)
    for descriptor in replacements.values():
        source_path = os.path.abspath(descriptor["path"])
        output_path = os.path.abspath(str(output))
        _fail(not (os.path.commonpath((output_path, source_path)) in (output_path, source_path)),
              "output aliases replacement source")
    output.mkdir(mode=0o700)
    try:
        tree = output / "root"
        tree.mkdir(mode=0o700)
        _copy_tree(base_root, tree, replacements)
        for rel in sorted(replacements):
            _copy_replacement(Path(replacements[rel]["path"]), tree / rel, replacements[rel])
        (tree / "apps").mkdir(); (tree / "case" / "work").mkdir(parents=True)
        shutil.copyfile(payload, tree / "apps" / "app")
        init_target = tree / "init"
        if init_target.exists():
            _fail(init_target.is_file() and not init_target.is_symlink(), "invalid existing init")
            init_target.unlink()
        _copy_replacement(collector, tree / "init", _authenticate_source(str(collector), sources))
        os.chmod(tree / "init", 0o755); os.utime(tree / "init", (0, 0))
        os.chmod(tree / "apps/app", 0o755); os.utime(tree / "apps/app", (0, 0))
        _normalize(tree)
        reviewed_staged = _inventory(tree)
        staged_by_path = {row["path"]: row for row in reviewed_staged}
        for rel, descriptor in replacements.items():
            row = staged_by_path.get(rel, {})
            _fail(row.get("type") == "file" and all(row.get(key) == descriptor[key]
                  for key in ("sha256", "size", "mode")), "final replacement drift: " + rel)
            _recheck_source(descriptor)
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
        _fail(_inventory(tree) == reviewed_staged, "staged inventory changed during archive")
        members = _archive_members(archive, reviewed_staged)
        # GNU cpio emits descendants for the explicit ``.`` input but does
        # not retain a standalone root member; every inventory path must be
        # present exactly once.
        expected_members = sorted(r["path"] for r in reviewed_staged)
        _fail(sorted(members) == expected_members, "archive members do not match staged inventory")
        manifest = {"schema_version": 1, "kind": "native-diagnostic-initramfs",
                    "base_root": str(base_root), "payload": {"path": str(payload), "sha256": _hash(payload)},
                    "collector": {"path": str(collector), "sha256": _hash(collector)},
                    "source_inventory": source_inventory, "staged_inventory": reviewed_staged,
                    "replacements": {rel: dict({k: v for k, v in replacements[rel].items() if not k.startswith("_")},
                        final_sha256=next(r["sha256"] for r in reviewed_staged if r["path"] == rel),
                        final_size=next(r["size"] for r in reviewed_staged if r["path"] == rel),
                        final_mode=next(r["mode"] for r in reviewed_staged if r["path"] == rel))
                                      for rel in sorted(replacements)},
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
        for descriptor in replacements.values():
            _recheck_source(descriptor)
        return manifest
    except BaseException:
        # Retain the attempt and original error, including partial artifacts.
        # The fresh-output check prevents reuse of this failed attempt name.
        raise

def _named_json(path, value):
    raw = (json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode()
    with path.open("xb") as stream:
        stream.write(raw); stream.flush(); os.fsync(stream.fileno())
    return raw


def _named_ref(path):
    st = os.lstat(path)
    _fail(stat.S_ISREG(st.st_mode) and not stat.S_ISLNK(st.st_mode), "named reference is not regular")
    return {"path": str(path), "size": st.st_size, "sha256": _hash(path), "mode": st.st_mode}


def _named_source(value, stack, cache):
    _fail(type(value) is dict and set(value) == {"path", "size", "sha256", "mode"}, "named source shape")
    _fail(type(value["size"]) is int and value["size"] >= 0 and
          type(value["mode"]) is int and 0 <= value["mode"] <= 0o777, "named source metadata")
    key = value["path"]
    if key not in cache:
        cache[key] = _authenticate_source(key, stack)
    source = cache[key]
    _fail(all(source[k] == value[k] for k in ("path", "size", "sha256", "mode")), "named source drift")
    _recheck_source(source)
    return source


def _named_module(source, name):
    # Only the two exact reviewed offline data transformers are selected by the
    # pinned input file. This is not the privileged native admission loader.
    os.lseek(source["_fd"], 0, os.SEEK_SET)
    raw = b""
    while len(raw) < source["size"]:
        part = os.read(source["_fd"], min(65536, source["size"] - len(raw)))
        _fail(bool(part), "short named module read")
        raw += part
    _fail(hashlib.sha256(raw).hexdigest() == source["sha256"], "named module bytes changed")
    module = types.ModuleType(name); module.__file__ = source["path"]
    exec(compile(raw, source["path"], "exec"), module.__dict__)
    return module


def stage_bound_inputs(inputs_path, inputs_sha256, output):
    """Materialize one reviewed named artifact set; never execute guest code."""
    with ExitStack() as stack:
        descriptor = _authenticate_source(str(_canonical(inputs_path, "bound inputs")), stack)
        _fail(descriptor["sha256"] == inputs_sha256, "bound input digest")
        with os.fdopen(os.dup(descriptor["_fd"]), "rb") as stream:
            def unique(pairs):
                value = {}
                for key, item in pairs:
                    _fail(key not in value, "duplicate bound input key"); value[key] = item
                return value
            doc = json.load(stream, object_pairs_hook=unique,
                            parse_constant=lambda _v: _fail(False, "nonfinite input"))
        keys = {"schema_version", "kind", "case_id", "cohort", "files", "directories",
                "artifact_sources", "artifact_locations", "overlay_source", "diagnostic_source",
                "profile", "payload", "proofs"}
        _fail(type(doc) is dict and set(doc) == keys and type(doc["schema_version"]) is int and
              doc["schema_version"] == 1 and
              doc["kind"] == "named-native-diagnostic-staging-inputs", "bound input shape")
        _fail(type(doc["files"]) is list and bool(doc["files"]) and
              type(doc["directories"]) is dict, "bound file/directory map")
        output = Path(output)
        _fail(output.is_absolute() and str(output) == str(output.parent.resolve() / output.name) and
              output.parent.is_dir() and not os.path.lexists(output), "fresh canonical named output required")
        cache = {}; files = {}; targets = set()
        for row in doc["files"]:
            _fail(type(row) is dict and set(row) == {"target", "source", "role", "proof"}, "bound file row")
            target = row["target"]
            _fail(type(target) is str and not target.startswith("/") and
                  all(part not in ("", ".", "..") for part in target.split("/")) and
                  target not in targets, "invalid or duplicate guest target")
            targets.add(target); files[target] = _named_source(row["source"], stack, cache)
        expected = {"bzImage", "mckernel_image", "mcexec", "payload", "native_boot", "loader", "libc", "collector"}
        _fail(set(doc["artifact_sources"]) == set(doc["artifact_locations"]) == expected, "bound artifact set")
        artifacts = {name: _named_source(value, stack, cache)
                     for name, value in doc["artifact_sources"].items()}
        overlay_source = _named_source(doc["overlay_source"], stack, cache)
        diagnostic_source = _named_source(doc["diagnostic_source"], stack, cache)
        for source in cache.values():
            _fail(os.path.commonpath((str(output), source["path"])) not in (str(output), source["path"]),
                  "named output aliases input")
        overlay = _named_module(overlay_source, "named_offline_overlay")
        diagnostic = _named_module(diagnostic_source, "named_offline_diagnostic")
        output.mkdir(mode=0o700); tree = output / "root"; tree.mkdir(mode=0o700)
        for name, mode in sorted(doc["directories"].items(), key=lambda item: (item[0].count("/"), item[0])):
            _fail(type(name) is str and name not in targets and not name.startswith("/") and
                  all(part not in ("", ".", "..") for part in name.split("/")) and
                  mode in (0o755, 0o1777), "named directory map")
            (tree / name).mkdir(mode=mode, parents=True, exist_ok=True)
            os.chmod(tree / name, mode)
        for target, source in sorted(files.items()):
            _copy_replacement(Path(source["path"]), tree / target, source)
        _normalize(tree)
        inventory = _inventory(tree)
        entries = [(row["path"], (tree / row["path"]).read_bytes() if row["type"] == "file" else b"",
                    (stat.S_IFREG if row["type"] == "file" else stat.S_IFDIR) | row["mode"])
                   for row in inventory]
        raw = overlay._archive(entries); raw += b"\0" * ((-len(raw)) % 512)
        archive = output / "base.cpio"
        with archive.open("xb") as stream: stream.write(raw); stream.flush(); os.fsync(stream.fileno())
        _archive_members(archive, inventory)
        base = output / "base.cpio.gz"; compressed = overlay._gzip(raw)
        with base.open("xb") as stream: stream.write(compressed); stream.flush(); os.fsync(stream.fileno())
        root_base = output / "root-base.json"
        _named_json(root_base, {"schema_version": 1, "cohort": doc["cohort"], "inventory": inventory,
                               "base_cpio_size": len(raw), "base_cpio_sha256": hashlib.sha256(raw).hexdigest()})
        published = {}
        for name, source in artifacts.items():
            relative = doc["artifact_locations"][name]
            _fail(type(relative) is str and not relative.startswith("/") and
                  all(part not in ("", ".", "..") for part in relative.split("/")), "artifact location")
            target = output / relative
            if target.exists():
                _fail(target.is_file() and not target.is_symlink() and
                      target.stat().st_size == source["size"] and _hash(target) == source["sha256"] and
                      stat.S_IMODE(target.stat().st_mode) == source["mode"], "published artifact drift")
            else:
                _copy_replacement(Path(source["path"]), target, source)
            published[name] = _named_ref(target)
        source_copy = output / "source" / "native_diagnostic_overlay.py"
        _copy_replacement(Path(overlay_source["path"]), source_copy, overlay_source)
        derived = output / "derived.cpio.gz"
        payload_member = doc["payload"]["argv"][4].lstrip("/")
        overlay_map = overlay.build_overlay(str(base), published["payload"]["path"], published["collector"]["path"],
            published["mcexec"]["path"], str(derived),
            collector_sha256=published["collector"]["sha256"], mcexec_sha256=published["mcexec"]["sha256"],
            payload_sha256=published["payload"]["sha256"], payload_member=payload_member,
            base_sha256=hashlib.sha256(compressed).hexdigest(), base_size=len(compressed),
            base_cpio_sha256=hashlib.sha256(raw).hexdigest(), base_cpio_size=len(raw))
        overlay_manifest = output / "overlay-manifest.json"; _named_json(overlay_manifest, overlay_map)
        manifest = {"schema_version": 1, "kind": "native-diagnostic-manifest", "case_id": doc["case_id"],
                    "artifacts": {name: published[name] for name in
                        ("bzImage", "mckernel_image", "mcexec", "payload", "native_boot", "loader", "libc")},
                    "modules": [_named_ref(tree / "modules" / name) for name in diagnostic.MODULE_NAMES],
                    "profile": doc["profile"], "payload": doc["payload"],
                    "staging": {"base_initramfs": _named_ref(base), "derived_initramfs": _named_ref(derived),
                                "collector": published["collector"], "overlay_source": _named_ref(source_copy),
                                "overlay_manifest": _named_ref(overlay_manifest)}}
        manifest["artifacts"].update(initramfs=_named_ref(base), root_base=_named_ref(root_base))
        diagnostic._validate_manifest(manifest)
        manifest_path = output / "native-diagnostic-manifest.json"; _named_json(manifest_path, manifest)
        consumed = {item["path"] for item in manifest["artifacts"].values()}
        consumed.update(item["path"] for item in manifest["modules"])
        consumed.update(item["path"] for item in manifest["staging"].values())
        consumed.add(str(manifest_path))
        rows = [{"target": path, "host": path, "content_sha256": _hash(Path(path))}
                for path in sorted(consumed)]
        _named_json(output / "STAGED-REGULAR-SOURCE-ROWS.json", rows)
        for source in cache.values(): _recheck_source(source)
        _recheck_source(descriptor)
        for directory in sorted([output] + [path for path in output.rglob("*") if path.is_dir()],
                                key=lambda path: len(path.parts), reverse=True):
            _fsync(directory)
        result = {"status": "PASS_REAL_NAMED_ARTIFACT_BASE_OVERLAY_AND_MANIFEST_ONLY",
                  "input_sha256": inputs_sha256, "cohort": doc["cohort"],
                  "native_manifest": _named_ref(manifest_path), "staging": manifest["staging"],
                  "strict_collector_ELF_guard_ran_in_real_overlay": True,
                  "native_consumed_regular_files": rows,
                  "materialized_base_files": len(files), "native_or_control_action": False}
        _named_json(output / "RESULT.json", result)
        _fsync(output)
        return result




def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--base-root", type=Path, default=BASE_ROOT); p.add_argument("--payload", type=Path, default=PAYLOAD)
    p.add_argument("--collector", type=Path); p.add_argument("--output", type=Path, required=True)
    p.add_argument("--replacements", type=Path,
                   help="reviewed JSON map for the kernel image, three modules, and optional corrected mcexec")
    p.add_argument("--bound-inputs", type=Path, help="exact reviewed named staging input JSON")
    p.add_argument("--bound-inputs-sha256", help="exact named staging input digest")
    a = p.parse_args(argv)
    if a.bound_inputs is not None:
        if (not a.bound_inputs_sha256 or a.replacements is not None or a.collector is not None or
                a.base_root != BASE_ROOT or a.payload != PAYLOAD):
            p.error("bound inputs require their digest and no legacy input options")
        print(json.dumps(stage_bound_inputs(a.bound_inputs, a.bound_inputs_sha256, a.output), sort_keys=True))
        return
    if a.bound_inputs_sha256 is not None:
        p.error("bound input digest requires bound inputs")
    if a.collector is None:
        p.error("legacy staging requires --collector")
    replacements = json.loads(a.replacements.read_text()) if a.replacements else None
    print(json.dumps(stage(a.base_root, a.payload, a.collector, a.output, replacements=replacements), sort_keys=True))

if __name__ == "__main__": main()
