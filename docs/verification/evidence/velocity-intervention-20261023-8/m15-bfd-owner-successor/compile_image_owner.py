#!/usr/bin/env python3
"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

Fixed private BFD qualification specialization of the reviewed compile-only owner.
A root-released invocation creates exactly one private compile-only, read-only-root
container on CPU6/1CPU/2GiB under its separate HOST lease; tests inject a fake Docker
transport and never contact Docker.
"""
from __future__ import annotations

import argparse
from decimal import Decimal
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import signal
import stat
import subprocess
import sys
import time
import types
import uuid


REQUEST_SCHEMA = "mckernel.m15-bfd-compile-request.v1"
SCOPE = 'Functional McKernel OS/apps and Rust/assembly migration only; no security testing.'
RECEIPT_SCHEMA = "mckernel.native-exact-mckernel-image-container-receipt.v1"
OWNER_RECEIPT_NAME = "owner-receipt.json"
EXPECTED_DRIVER_SHA256 = '7d30085edda4d1272f923b19e8632e9ab8b259874623974c2da53dbe4c3c5be0'
EXPECTED_PROVENANCE_SHA256 = '453dd998e4ef1e2ed21b0818771d97197d77f98c90ca8c6c67cc8ab019063044'
EXPECTED_HOST_OWNER_SHA256 = '76ff839a839a2f55cd7d537d22221cb1b053390e2b6052b8be2b5d8b20990e63'
EXPECTED_HEAVY_ENTRY_CONTRACT_SHA256 = "c252ee341eb61752704f8b818503c0a5dc97400845494707ca3110f5f23df6d1"
# The image owner advances with the image-candidate namespace.  Keep consumed
# exclusions explicit: accepting one of these would allow a request to race a
# retired build candidate.  Tests may replace COMMON_EXCLUSION with a private
# fixture, so the rejection list remains separate from the active value.
COMMON_EXCLUSION = '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-8/m15-bfd-owner-successor/operation-1/compile-lease.json'
RETIRED_COMMON_EXCLUSIONS = frozenset(
    "/home/holden/mckernel-work/scratch/native-exact-candidate-operational-exclusion-" + suffix + ".json"
    for suffix in (
        "76ae20b5", "76ae20b5-2", "97fb67a7-3", "closurefix-4",
        "runtimeclosure-5", "offlinecwd-5", "offlinecwd-6", "memorymap-7",
        "memorymap-relocated-8", "mappingbinding-9", "lifecyclebinding-10",
        "objtoolbinding-11", "runtimeblob-12", "selfdigest-13", "exportset-16",
        "exportset-17", "exportset-18", "exportset-19", "exportset-20",
        "exportset-21", "exportset-22", "exportset-23", "exportset-24",
        "exportset-25", "exportset-26", "scratch15-exportset-27", "scratch16", "scratch17-image-1",
    )
)
RETIRED_COMMON_EXCLUSIONS = RETIRED_COMMON_EXCLUSIONS | frozenset(('/home/holden/mckernel-work/host-preparation/four-callback-affinity-image-preparation-20261019-1/affinity-full-syscall-include-correction-1/fresh-full-attempt-1/common-exclusion.json',))

RETIRED_COMMON_EXCLUSIONS = RETIRED_COMMON_EXCLUSIONS | frozenset(('/home/holden/mckernel-work/host-preparation/p-m06-matched-guest-build-binding-20261022-1/full-image-attempt-1/common-exclusion.json',))

RETIRED_COMMON_EXCLUSIONS = RETIRED_COMMON_EXCLUSIONS | frozenset(('/home/holden/mckernel-work/host-preparation/compute-idle-rust-cutover-20261023-1/production-combined-2/pinned-full-image-attempt-1/common-exclusion.json',))

RETIRED_COMMON_EXCLUSIONS = RETIRED_COMMON_EXCLUSIONS | frozenset(('/home/holden/mckernel-work/host-preparation/compute-idle-rust-cutover-20261023-1/production-combined-2/correction1/pinned-full-image-attempt-1/common-exclusion.json',))

RETIRED_COMMON_EXCLUSIONS = RETIRED_COMMON_EXCLUSIONS | frozenset(('/home/holden/mckernel-work/host-preparation/compute-idle-rust-cutover-20261023-1/production-combined-4/default-image-successor-1/pinned-full-image-attempt-1/common-exclusion.json',))

RETIRED_COMMON_EXCLUSIONS = RETIRED_COMMON_EXCLUSIONS | frozenset(('/home/holden/mckernel-work/host-preparation/compute-idle-rust-cutover-20261023-1/production-combined-5/default-image-successor-1/pinned-full-image-attempt-1/common-exclusion.json',))

RETIRED_COMMON_EXCLUSIONS = RETIRED_COMMON_EXCLUSIONS | frozenset(('/home/holden/mckernel-work/host-preparation/compute-idle-rust-cutover-20261023-1/production-combined-5/actual-owner-consumer-correction-1/next-build-preparation-1/pinned-full-image-attempt-2/common-exclusion.json',))

RETIRED_COMMON_EXCLUSIONS = RETIRED_COMMON_EXCLUSIONS | frozenset(('/home/holden/mckernel-work/host-preparation/compute-idle-rust-cutover-20261023-1/production-combined-6/default-image-preparation-1/next-build-preparation-1/pinned-full-image-attempt-1/common-exclusion.json',))

RETIRED_COMMON_EXCLUSIONS = RETIRED_COMMON_EXCLUSIONS | frozenset(('/home/holden/mckernel-work/host-preparation/compute-idle-rust-cutover-20261023-1/production-combined-7/default-image-preparation-1/next-build-preparation-1/pinned-full-image-attempt-1/common-exclusion.json',))

RETIRED_COMMON_EXCLUSIONS = RETIRED_COMMON_EXCLUSIONS | frozenset(('/home/holden/mckernel-work/host-preparation/compute-idle-rust-cutover-20261023-1/production-combined-8/default-image-preparation-1/next-build-preparation-1/pinned-full-image-attempt-1/common-exclusion.json',))

RETIRED_COMMON_EXCLUSIONS = RETIRED_COMMON_EXCLUSIONS | frozenset(('/home/holden/mckernel-work/host-preparation/compute-idle-rust-cutover-20261023-1/production-combined-9/default-image-preparation-1/next-build-preparation-1/pinned-full-image-attempt-1/common-exclusion.json',))

RETIRED_COMMON_EXCLUSIONS = RETIRED_COMMON_EXCLUSIONS | frozenset(('/home/holden/mckernel-work/host-preparation/compute-idle-rust-cutover-20261023-1/production-combined-10/default-image-preparation-1/next-build-preparation-1/pinned-full-image-attempt-1/common-exclusion.json',))

RETIRED_COMMON_EXCLUSIONS = RETIRED_COMMON_EXCLUSIONS | frozenset(('/home/holden/mckernel-work/host-preparation/compute-idle-rust-cutover-20261023-1/production-combined-11/default-image-preparation-1/next-build-preparation-1/pinned-full-image-attempt-1/common-exclusion.json',))

RETIRED_COMMON_EXCLUSIONS = RETIRED_COMMON_EXCLUSIONS | frozenset(('/home/holden/mckernel-work/host-preparation/compute-idle-rust-cutover-20261023-1/production-combined-12/default-image-preparation-1/next-build-preparation-1/pinned-full-image-attempt-1/common-exclusion.json',))

RETIRED_COMMON_EXCLUSIONS = RETIRED_COMMON_EXCLUSIONS | frozenset(('/home/holden/mckernel-work/host-preparation/compute-idle-rust-cutover-20261023-1/production-combined-13/default-image-preparation-1/next-build-preparation-1/pinned-full-image-attempt-1/common-exclusion.json',))

LIMITS = {
    "NanoCpus": 1_000_000_000, "CpusetCpus": "6",
    "Memory": 2 * 2**30, "MemorySwap": 2 * 2**30,
    "PidsLimit": 128, "NetworkMode": "none",
}
RESOURCE_ARGS = ("--cpus=1", "--cpuset-cpus=6", "--memory=2g",
                 "--memory-swap=2g", "--pids-limit=128")
MAX_TIMEOUT = 19_800
LAUNCHER_AGGREGATE_GIB = "16.2158"
LAUNCHER_AGGREGATE_BYTES = int(Decimal(LAUNCHER_AGGREGATE_GIB) * 2**30)
REQUIRED_TOOLS = ("cmake", "cc", "clang", "ld.lld", "rustc", "nm", "readelf", "make", "ld",
                  "objcopy", "ar", "ranlib", "git", "dd")
REQUIRED_LIBRARIES = ("libnuma", "libbfd", "libiberty", "libudev")
LIBRARY_SPECS = {
    "libnuma": {"development_package": "numactl-devel",
                "linker": {"path": "/usr/lib64/libnuma.so", "owner": "numactl-libs"},
                "headers": {"/usr/include/numa.h": "numactl-devel"}},
    "libbfd": {"development_package": "binutils-devel",
               "linker": {"path": "/usr/lib64/libbfd.so", "owner": "binutils-devel"},
               "headers": {"/usr/include/bfd.h": "binutils-devel"}},
    "libiberty": {"development_package": "binutils-devel",
                  "linker": {"path": "/usr/lib64/libiberty.a", "owner": "binutils-devel"},
                  "headers": {"/usr/include/libiberty.h": "binutils-devel"}},
    "libudev": {"development_package": "systemd-devel",
                "linker": {"path": "/usr/lib64/libudev.so", "owner": "systemd-libs"},
                "headers": {"/usr/include/libudev.h": "systemd-devel"}},
}
# This is duplicated deliberately: the image preparer is authenticated
# independently and the downstream owner must not import an unbound producer
# module merely to learn the base-image identity.
PREPARER_BASE_IMAGE = (
    "rockylinux/rockylinux:10.2@sha256:"
    "e372170ca8630f0f03e9b70fdd0bf4a3ce3426b0de7cdba615f06337389de176"
)
PINNED_CMAKE_RPM = "cmake-0:3.31.8-1.el10.x86_64"
PINNED_RUST_RPM = "rust-0:1.92.0-1.el10.x86_64"
EXPECTED_V2_RUSTC_VERSION = "rustc 1.95.0-nightly (c04308580 2026-02-18)"
_PREPARATION_EVIDENCE = (
    "image-inspect.json", "inspect-before-start.json", "tool-observation.json",
    "inspect-terminal.json", "offline-inspect-before-start.json",
    "offline-tool-observation.json", "offline-inspect-terminal.json",
)
SUDO_DOCKER_PREFIX = ("/usr/bin/sudo", "-A", "/usr/bin/docker",
                      "--host=unix:///var/run/docker.sock")
RETIRED_COMMON_EXCLUSIONS = RETIRED_COMMON_EXCLUSIONS | frozenset(('/home/holden/mckernel-work/scratch/native-fp-copy-image-preparation-20261018-1/preparation-commands-1/common-exclusion-084cffb0413a4275bfdd66e3fd6c3368.json',))




def _load_reviewed_host_owner(path, host_sha256=None, provenance_path=None,
                              provenance_sha256=None):
    """Load reviewed owner/provenance from authenticated source bytes only."""
    path = Path(path)
    provenance_path = (path.with_name("native_rust_exact_build_offline.py")
                       if provenance_path is None else Path(provenance_path))
    def source_bytes(candidate, expected, label):
        if not (candidate.is_absolute() and candidate.is_file() and not candidate.is_symlink()):
            raise RuntimeError(label + " is not a regular source file")
        current = Path(candidate.anchor)
        for component in candidate.parts[1:]:
            current /= component
            if current.is_symlink():
                raise RuntimeError(label + " has symlink parent")
        before = os.lstat(candidate)
        data = candidate.read_bytes()
        after = os.lstat(candidate)
        if (before.st_dev, before.st_ino, before.st_size, before.st_mode) != \
                (after.st_dev, after.st_ino, after.st_size, after.st_mode):
            raise RuntimeError(label + " identity changed during import")
        observed = hashlib.sha256(data).hexdigest()
        if expected is not None:
            if observed != expected:
                raise RuntimeError(label + " hash mismatch")
        return data
    host_bytes = source_bytes(path, host_sha256, "host owner")
    provenance_bytes = source_bytes(provenance_path, provenance_sha256, "host provenance")
    package_name = "_mckernel_reviewed_exact_owner_%d" % os.getpid()
    package = types.ModuleType(package_name)
    package.__path__ = [str(path.parent)]
    package.__package__ = package_name
    sys.modules[package_name] = package
    provenance_name = package_name + ".native_rust_exact_build_offline"
    host_name = package_name + ".native_rust_exact_build_container_owner"
    provenance = types.ModuleType(provenance_name)
    provenance.__package__ = package_name
    provenance.__file__ = str(provenance_path)
    host = types.ModuleType(host_name)
    host.__package__ = package_name
    host.__file__ = str(path)
    sys.modules[provenance_name] = provenance
    sys.modules[host_name] = host
    try:
        exec(compile(provenance_bytes, str(provenance_path), "exec"), provenance.__dict__)
        exec(compile(host_bytes, str(path), "exec"), host.__dict__)
        return host
    finally:
        sys.modules.pop(host_name, None)
        sys.modules.pop(provenance_name, None)
        sys.modules.pop(package_name, None)


_HOST_OWNER_PATH = Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-8/m15-bfd-owner-successor/compile_host_helper.py')
_HOST_OWNER = _load_reviewed_host_owner(
    _HOST_OWNER_PATH, EXPECTED_HOST_OWNER_SHA256,
    Path('/home/holden/mckernel-work/host-preparation/compute-idle-rust-cutover-20261023-1/production-combined-14/default-image-preparation-1/native_rust_exact_build_offline.py'),
    EXPECTED_PROVENANCE_SHA256)


class OwnerError(RuntimeError):
    pass





def _gitlink_rows(raw, tree=False):
    _fail(isinstance(raw, bytes) and (not raw or raw.endswith(b"\0")),
          "malformed libdwarf Git rows")
    rows = {}
    for item in raw.split(b"\0")[:-1]:
        metadata, separator, raw_path = item.partition(b"\t")
        _fail(separator and raw_path, "malformed libdwarf Git row")
        try:
            relative = raw_path.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise OwnerError("non-UTF-8 libdwarf path") from exc
        _fail(relative and not Path(relative).is_absolute() and "\\" not in relative and
              "\0" not in relative and all(part not in ("", ".", "..")
              for part in relative.split("/")), "libdwarf Git path escapes checkout")
        fields = metadata.split()
        if tree:
            _fail(len(fields) == 3 and fields[1] == b"blob", "unsupported libdwarf tree entry")
            mode, blob = fields[0], fields[2]
        else:
            _fail(len(fields) == 3 and fields[2] == b"0", "unsupported libdwarf index entry")
            mode, blob = fields[0], fields[1]
        _fail(mode in (b"100644", b"100755") and re.fullmatch(b"[0-9a-f]{40}", blob),
              "unsupported libdwarf mode or blob")
        _fail(relative not in rows, "duplicate libdwarf Git path")
        rows[relative] = {"mode": mode.decode(), "blob": blob.decode()}
    return rows


def _validate_gitlink_manifest(document, manifest_path, checkout, base_manifest,
                               candidate, ihk, git_tool=None):
    """Authenticate the supplemental self-contained libdwarf closure."""
    _fail(isinstance(document, dict) and
          document.get("schema") == "mckernel.native-exact-mckernel-gitlink-inputs.v1",
          "gitlink manifest schema")
    _fail(document.get("candidate_sha") == candidate and document.get("ihk_sha") == ihk,
          "gitlink manifest identity differs")
    base = _regular(base_manifest, "base source manifest")
    _fail(document.get("base_manifest_sha256") == _sha256(base),
          "gitlink base manifest hash differs")
    rows = document.get("consumed_gitlinks")
    _fail(isinstance(rows, dict) and set(rows) == {"executer/user/lib/libdwarf/libdwarf"},
          "consumed gitlink set differs")
    checkout = _canonical(checkout, "libdwarf checkout", directory=True)
    row = rows["executer/user/lib/libdwarf/libdwarf"]
    _fail(isinstance(row, dict) and row.get("path") == "executer/user/lib/libdwarf/libdwarf",
          "libdwarf gitlink path differs")
    _fail(((_load_json(base, "base source manifest").get("gitlinks") or {}).get(row["path"]) ==
           row.get("commit") and re.fullmatch(r"[0-9a-f]{40}", str(row.get("commit", ""))) and
           re.fullmatch(r"[0-9a-f]{40}", str(row.get("tree", "")))),
          "base manifest gitlink differs")
    git = _git_factory(git_tool or {"path": "/usr/bin/git"})
    # The source tree itself is the authenticated closure; no worktree state,
    # alternate object database, replacement refs, or nested repository is
    # accepted.  Use the reviewed helper's exact inventory shape when present.
    _fail(git(checkout, "rev-parse", "HEAD").decode().strip() == row.get("commit"),
          "libdwarf HEAD differs from manifest")
    _fail(git(checkout, "rev-parse", "HEAD^{tree}").decode().strip() == row.get("tree"),
          "libdwarf tree differs from manifest")
    _fail(not git(checkout, "status", "--porcelain=v1", "--ignored=matching",
                  "--untracked-files=all").decode(), "libdwarf checkout is dirty")
    index_rows = _gitlink_rows(git(checkout, "ls-files", "--stage", "-z"))
    tree_rows = _gitlink_rows(git(checkout, "ls-tree", "-r", "--full-tree", "-z", "HEAD"),
                              tree=True)
    _fail(index_rows == tree_rows, "libdwarf index differs from HEAD tree")
    _fail(set(index_rows) == set(row.get("files", {})), "libdwarf tracked file set differs")
    observed = {}
    for raw, expected in row.get("files", {}).items():
        path = checkout / raw
        _fail(path.resolve(strict=False) == path and path.is_file() and not path.is_symlink(),
              "libdwarf tracked path differs: " + raw)
        info = os.lstat(path)
        mode = format(stat.S_IFMT(info.st_mode) | stat.S_IMODE(info.st_mode), "06o")
        _fail(mode in ("100644", "100755"),
              "libdwarf tracked mode differs: " + raw)
        observed[raw] = {"mode": mode,
                         "blob": git(checkout, "hash-object", "--no-filters", "--", raw).decode().strip(),
                         "sha256": _sha256(path)}
        _fail({"mode": mode, "blob": observed[raw]["blob"]} == tree_rows[raw],
              "libdwarf worktree differs from HEAD tree")
    _fail(observed == row.get("files"), "libdwarf tracked inventory differs")
    git_meta = _canonical(checkout / ".git", "libdwarf Git metadata", directory=True)
    git_dir = git(checkout, "rev-parse", "--absolute-git-dir").decode().strip()
    common_raw = git(checkout, "rev-parse", "--git-common-dir").decode().strip()
    common = Path(common_raw)
    if not common.is_absolute():
        common = (checkout / common).resolve()
    _fail(Path(git_dir) == git_meta and common == git_meta,
          "libdwarf uses external Git metadata")
    _fail(not (git_meta / "objects/info/alternates").exists() and
          not (git_meta / "shallow").exists() and
          git(checkout, "rev-parse", "--is-shallow-repository").decode().strip() == "false" and
          not git(checkout, "for-each-ref", "--format=%(refname)", "refs/replace").decode().strip(),
          "libdwarf uses external or replacement Git objects")
    metadata = {}
    for item in sorted(git_meta.rglob("*")):
        relative = item.relative_to(git_meta).as_posix()
        _fail(relative and not Path(relative).is_absolute() and ".." not in Path(relative).parts,
              "libdwarf Git metadata path differs")
        info = item.lstat()
        _fail(not stat.S_ISLNK(info.st_mode), "libdwarf Git metadata contains symlink")
        _fail(stat.S_ISREG(info.st_mode) or stat.S_ISDIR(info.st_mode),
              "libdwarf Git metadata contains special file")
        if stat.S_ISREG(info.st_mode):
            metadata[relative] = {"mode": format(stat.S_IMODE(info.st_mode), "04o"),
                                  "size": info.st_size, "sha256": _sha256(item)}
    _fail(metadata == row.get("git_metadata"), "libdwarf Git metadata differs")
    return checkout


def _fail(condition, message):
    if not condition:
        raise OwnerError(message)


def _sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _fsync_dir(path):
    fd = os.open(Path(path), os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _atomic_json(path, value):
    path = Path(path)
    temporary = path.with_name(path.name + ".tmp-" + uuid.uuid4().hex)
    with temporary.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, sort_keys=True, indent=2)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)
    _fsync_dir(path.parent)


def _exclusive_json(path, value):
    """Publish one receipt without following links or overwriting evidence."""
    path = Path(path)
    _no_symlink_parents(path, "receipt path")
    payload = (json.dumps(value, sort_keys=True, indent=2) + "\n").encode()
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    fd = os.open(path, flags, 0o600)
    try:
        offset = 0
        while offset < len(payload):
            written = os.write(fd, payload[offset:])
            _fail(written > 0, "receipt short write")
            offset += written
        os.fsync(fd)
    finally:
        os.close(fd)
    _fsync_dir(path.parent)


def _exclusive_text(path, text):
    path = Path(path)
    _no_symlink_parents(path, "evidence path")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    fd = os.open(path, flags, 0o600)
    try:
        payload = text.encode("utf-8", "replace")
        offset = 0
        while offset < len(payload):
            written = os.write(fd, payload[offset:])
            _fail(written > 0, "evidence short write")
            offset += written
        os.fsync(fd)
    finally:
        os.close(fd)
    _fsync_dir(path.parent)


def _canonical(path, label, directory=False):
    path = Path(path)
    _fail(path.is_absolute() and not path.is_symlink() and path.exists(), label + " missing")
    resolved = path.resolve(strict=True)
    _fail(resolved == path, label + " is not canonical")
    if directory:
        _fail(resolved.is_dir(), label + " must be a directory")
    return resolved


def _regular(path, label):
    path = _canonical(path, label)
    _fail(stat.S_ISREG(path.lstat().st_mode), label + " must be regular")
    return path


def _safe_regular(path, label):
    """Validate a regular file without following a leaf or ancestor link."""
    path = Path(path)
    _no_symlink_parents(path, label)
    try:
        info = os.lstat(path)
    except OSError as exc:
        raise OwnerError(label + " missing") from exc
    _fail(stat.S_ISREG(info.st_mode), label + " must be a regular file")
    return path


def _safe_directory(path, label):
    """Validate a directory and every path component without following links."""
    path = Path(path)
    _no_symlink_parents(path, label)
    try:
        info = os.lstat(path)
    except OSError as exc:
        raise OwnerError(label + " missing") from exc
    _fail(stat.S_ISDIR(info.st_mode), label + " must be a directory")
    return path


def _no_symlink_parents(path, label):
    path = Path(path)
    _fail(path.is_absolute(), label + " must be absolute")
    current = Path(path.anchor)
    for component in path.parts[1:]:
        current /= component
        _fail(not current.is_symlink(), label + " has symlink parent")


def _confined_path(path, label):
    """Require an absolute path whose leaf and every ancestor are real."""
    path = Path(path)
    _no_symlink_parents(path, label)
    _fail(path.is_absolute(), label + " must be absolute")
    current = Path(path.anchor)
    for component in path.parts[1:]:
        current /= component
        if current == path:
            continue
        _fail(current.exists() and current.is_dir(), label + " has non-directory ancestor")
    if path.exists():
        _fail(path.resolve(strict=True) == path, label + " is not canonical")
    return path


def _disjoint(paths):
    roots = [Path(path).resolve(strict=False) for path in paths]
    for index, left in enumerate(roots):
        for right in roots[index + 1:]:
            _fail(left != right and left not in right.parents and right not in left.parents,
                  "bound roots overlap")


def _load_json(path, label):
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise OwnerError("malformed " + label) from exc
    _fail(isinstance(value, dict), label + " must be an object")
    return value


def _identity(path):
    info = os.lstat(path)
    return {"path": str(Path(path).resolve(strict=True)), "dev": info.st_dev,
            "inode": info.st_ino, "uid": info.st_uid, "gid": info.st_gid,
            "mode": stat.S_IMODE(info.st_mode), "file_type": stat.S_IFMT(info.st_mode)}


def _tree_inventory(root):
    root = Path(root)
    observed = {}
    for item in sorted(root.rglob("*")):
        st = item.lstat()
        _fail(not stat.S_ISLNK(st.st_mode), "inventory contains symlink")
        _fail(stat.S_ISREG(st.st_mode) or stat.S_ISDIR(st.st_mode),
              "inventory contains special file")
        row = {"mode": stat.S_IMODE(st.st_mode),
               "type": "directory" if stat.S_ISDIR(st.st_mode) else "file"}
        if stat.S_ISREG(st.st_mode):
            row.update(size=st.st_size, sha256=_sha256(item))
        observed[str(item.relative_to(root))] = row
    return observed


def _closure_inventory(root, host_root=None, container_root=None):
    """Inventory a translated build closure, retaining symlink spelling.

    ``Path.rglob`` follows enough link metadata to make a closure admission
    race-prone.  Walk with lstat instead, and validate every link's lexical
    target and resolved target against the host root.  The container target is
    recorded separately because an absolute host link must be translated to
    its ``/out`` spelling without changing bytes on disk.
    """
    root = Path(root)
    host_root = root if host_root is None else Path(host_root)
    container_root = Path("/out") if container_root is None else Path(container_root)
    _fail(root == host_root or root in host_root.parents,
          "closure root is outside host root")
    result = {}
    active = set()
    seen_objects = {}

    def translated(path):
        resolved = path.resolve(strict=True)
        _fail(resolved == host_root or host_root in resolved.parents,
              "closure symlink escapes host root")
        return container_root / resolved.relative_to(host_root)

    def visit(directory):
        info = os.lstat(directory)
        marker = (info.st_dev, info.st_ino)
        _fail(marker not in active, "closure directory cycle")
        active.add(marker)
        try:
            entries = sorted(os.scandir(directory), key=lambda item: item.name)
            for entry in entries:
                item = Path(entry.path)
                relative = str(item.relative_to(host_root))
                st = os.lstat(item)
                mode = st.st_mode
                if stat.S_ISLNK(mode):
                    raw = os.readlink(item)
                    _fail(raw != "", "closure symlink has empty target")
                    # The on-disk spelling is container-facing.  Translate an
                    # absolute /out edge solely for host admission, retaining
                    # its original bytes in ``target`` below.
                    raw_path = Path(raw)
                    if raw_path.is_absolute() and (raw_path == container_root or
                                                   container_root in raw_path.parents):
                        target = host_root / raw_path.relative_to(container_root)
                    else:
                        target = raw_path if raw_path.is_absolute() else item.parent / raw_path
                    _fail(not target.is_symlink(), "closure symlink alias/cycle")
                    target = target.resolve(strict=True)
                    _fail(target == host_root or host_root in target.parents,
                          "closure symlink escapes host root")
                    target_stat = os.lstat(target)
                    _fail(stat.S_ISREG(target_stat.st_mode) or stat.S_ISDIR(target_stat.st_mode),
                          "closure symlink targets special file")
                    # A link to another link is an alias chain, not a stable
                    # closure edge; reject it so the translated graph is
                    # deterministic and cannot hide a cycle.
                    row = {"mode": stat.S_IMODE(mode), "type": "symlink",
                           "target": raw, "resolved": str(target.relative_to(host_root)),
                           "container_target": str(container_root / target.relative_to(host_root))}
                    result[relative] = row
                elif stat.S_ISDIR(mode):
                    result[relative] = {"mode": stat.S_IMODE(mode), "type": "directory"}
                    visit(item)
                elif stat.S_ISREG(mode):
                    object_key = (st.st_dev, st.st_ino)
                    _fail(object_key not in seen_objects,
                          "closure contains aliased regular files")
                    seen_objects[object_key] = item
                    result[relative] = {"mode": stat.S_IMODE(mode), "type": "file",
                                        "size": st.st_size, "sha256": _sha256(item)}
                else:
                    raise OwnerError("closure contains special file")
        finally:
            active.remove(marker)

    visit(root)
    return result


def _validate_kernel_binding(toolchain_doc, host_root):
    binding = toolchain_doc.get("kernel_binding")
    _fail(isinstance(binding, dict) and
          set(binding) == {"container_root", "container_kernel_dir", "closure_inventory"},
          "kernel binding schema differs")
    host_root = _canonical(host_root, "kernel host root", directory=True)
    host_kernel = _canonical(host_root / "build", "kernel host directory", directory=True)
    _fail(host_kernel == host_root / "build", "kernel host directory must be host_root/build")
    _fail(binding["container_root"] == "/out" and
          binding["container_kernel_dir"] == "/out/build",
          "kernel container translation differs")
    inventory = binding["closure_inventory"]
    _fail(isinstance(inventory, dict) and inventory,
          "kernel closure inventory missing")
    observed = _closure_inventory(host_root, host_root, Path("/out"))
    _fail(observed == inventory, "kernel closure inventory differs")
    return host_root, host_kernel


def _validate_v2_image_tools(request, toolchain_doc):
    """Authenticate the immutable image tool closure without mounting it."""
    receipt = _regular(request.get("image_receipt", ""), "image receipt")
    expected = request.get("image_receipt_sha256")
    _fail(isinstance(expected, str) and re.fullmatch(r"[0-9a-f]{64}", expected),
          "image receipt hash binding")
    _fail(_sha256(receipt) == expected, "image receipt hash drift")
    document = _load_json(receipt, "image receipt")
    _fail(document.get("status") == "PASS" and document.get("image_id") == request["image_id"] and
          document.get("candidate_sha") == request.get("candidate_sha") and
          document.get("retired") is True and
          document.get("base_image") == PREPARER_BASE_IMAGE,
          "image receipt identity differs")
    _fail(document.get("source_free") is True and document.get("runtime_network") == "none",
          "image receipt is not source-free and offline")
    lock_sha = document.get("toolchain_lock_sha256")
    _fail(isinstance(lock_sha, str) and re.fullmatch(r"[0-9a-f]{64}", lock_sha),
          "image receipt toolchain lock hash")
    requested_lock_sha = request.get("toolchain_lock_sha256")
    _fail(isinstance(requested_lock_sha, str) and
          re.fullmatch(r"[0-9a-f]{64}", requested_lock_sha) and
          requested_lock_sha == lock_sha, "image receipt toolchain lock differs")
    packages = document.get("packages")
    _fail(isinstance(packages, dict) and packages and
          all(isinstance(name, str) and name and isinstance(value, str) and value
              for name, value in packages.items()),
          "image receipt packages missing")
    image_tools = toolchain_doc.get("image_tools")
    mounted_tools = toolchain_doc.get("mounted_tools")
    _fail(isinstance(image_tools, dict) and isinstance(mounted_tools, dict),
          "v2 image/mounted tool partitions missing")
    _fail(set(image_tools) | set(mounted_tools) == set(REQUIRED_TOOLS) and
          not set(image_tools) & set(mounted_tools), "v2 tool partition overlaps")
    _fail("rustc" in mounted_tools and "rustc" not in image_tools,
          "nightly rustc must be mounted")
    receipt_tools = document.get("tools")
    _fail(isinstance(receipt_tools, dict) and receipt_tools,
          "image receipt tools missing")
    _fail(packages.get("cmake") == PINNED_CMAKE_RPM and
          packages.get("rust") == PINNED_RUST_RPM,
          "image receipt pinned CMake/Rust identity differs")
    evidence = document.get("evidence")
    _fail(isinstance(evidence, dict) and evidence, "image receipt evidence missing")
    evidence_root = receipt.parent
    for name in _PREPARATION_EVIDENCE:
        row = evidence.get(name)
        _fail(isinstance(row, dict) and
              isinstance(row.get("sha256"), str) and
              re.fullmatch(r"[0-9a-f]{64}", row["sha256"]) and
              isinstance(row.get("size"), int) and row["size"] >= 0,
              "image receipt evidence entry missing: " + name)
        path = _safe_regular(evidence_root / name, "image receipt evidence")
        _fail(path.stat().st_size == row["size"] and _sha256(path) == row["sha256"],
              "image receipt evidence hash drift: " + name)
    _fail(evidence["tool-observation.json"]["sha256"] ==
          evidence["offline-tool-observation.json"]["sha256"],
          "image receipt preparation/offline observations differ")
    for name, descriptor in image_tools.items():
        _fail(isinstance(descriptor, dict) and isinstance(descriptor.get("path"), str) and
              isinstance(descriptor.get("target"), str) and
              descriptor["path"].startswith("/usr/") and descriptor["target"].startswith("/usr/"),
              "image tool descriptor incomplete: " + name)
        _fail(re.fullmatch(r"[0-9a-f]{64}", str(descriptor.get("sha256", ""))),
              "image tool hash missing: " + name)
        _fail(isinstance(receipt_tools, dict) and receipt_tools.get(name) == descriptor and
              isinstance(descriptor.get("rpm_nevra"), str) and
              isinstance(descriptor.get("executable_version"), str),
              "image receipt tool differs: " + name)
        # Only tools consumed from the immutable image need package-owner
        # authentication.  The producer may retain observations for
        # base-provided tools (for example rpm) that are not part of this
        # owner contract's image_tools partition.
        rpm = descriptor["rpm_nevra"]
        package_match = re.fullmatch(r"(.+)-\d+:[^-]+-.+\.[^.]+", rpm)
        _fail(package_match is not None, "image receipt tool RPM identity malformed")
        _fail(packages.get(package_match.group(1)) == rpm,
              "image receipt package/tool identity differs")
    _validate_library_closure(document, toolchain_doc.get("libraries"), receipt.parent)
    return image_tools, mounted_tools


def _validate_library_closure(document, expected, evidence_root=None):
    """Bind CMake's immutable image library closure to both probe phases."""
    libraries = document.get("libraries")
    _fail(isinstance(libraries, dict) and set(libraries) == set(REQUIRED_LIBRARIES),
          "image receipt libraries incomplete")
    _fail(expected == libraries, "toolchain library closure differs from image receipt")
    packages = document.get("packages")
    _fail(isinstance(packages, dict), "image receipt packages missing")
    evidence = document.get("evidence")
    _fail(isinstance(evidence, dict), "image receipt evidence missing")
    for name in REQUIRED_LIBRARIES:
        row = libraries[name]
        spec = LIBRARY_SPECS[name]
        _fail(isinstance(row, dict) and row.get("development_package") == spec["development_package"] and
              row["development_package"] in packages, "library development package missing: " + name)
        linker = row.get("linker")
        headers = row.get("headers")
        _fail(isinstance(linker, dict) and isinstance(headers, dict) and headers,
              "library artifacts incomplete: " + name)
        _fail(isinstance(headers, dict) and set(headers) == set(spec["headers"]),
              "library header set differs: " + name)
        expected = [("linker", linker, spec["linker"]["path"], spec["linker"]["owner"])]
        expected += [("header", headers[path], path, expected_owner)
                     for path, expected_owner in spec["headers"].items()]
        for label, artifact, expected_path, expected_owner in expected:
            _fail(isinstance(artifact, dict) and isinstance(artifact.get("path"), str) and
                  artifact["path"].startswith("/usr/") and
                  isinstance(artifact.get("target"), str) and artifact["target"].startswith("/usr/") and
                  isinstance(artifact.get("owner"), str) and artifact["owner"] and
                  isinstance(artifact.get("rpm_nevra"), str) and
                  re.fullmatch(r"[0-9a-f]{64}", str(artifact.get("sha256", ""))),
                  "library " + label + " identity incomplete: " + name)
            _fail(artifact["path"] == expected_path and artifact["owner"] == expected_owner,
                  "library " + label + " role differs: " + name)
            package_match = re.fullmatch(r"(.+)-\d+:[^-]+-.+\.[^.]+", artifact["rpm_nevra"])
            _fail(package_match is not None and artifact["owner"] == package_match.group(1) and
                  packages.get(package_match.group(1)) == artifact["rpm_nevra"],
                  "library RPM identity differs: " + name)
    if evidence_root is not None:
        for filename in ("tool-observation.json", "offline-tool-observation.json"):
            observed = _load_json(_safe_regular(Path(evidence_root) / filename,
                                                "image receipt library evidence"),
                                  "image receipt library evidence")
            _fail(observed.get("libraries") == libraries,
                  "preparation/offline library observation differs")
    return libraries


def _v2_host_git(request):
    """Bind the host-side Git used before the offline container starts.

    Image tools are authenticated by the preparation receipt and may only be
    observed inside the image.  Source admission happens on the host, so it
    needs a separate, explicitly hash-bound Git executable; borrowing the
    image descriptor would silently compare host ``/usr`` with image bytes.
    """
    descriptor = request.get("host_git")
    _fail(isinstance(descriptor, dict) and set(descriptor) == {"path", "sha256"},
          "v2 host Git binding")
    path = _regular(descriptor.get("path", ""), "v2 host Git")
    expected = descriptor.get("sha256")
    _fail(isinstance(expected, str) and re.fullmatch(r"[0-9a-f]{64}", expected),
          "v2 host Git hash")
    _fail(_sha256(path) == expected, "v2 host Git hash drift")
    return {"path": str(path), "sha256": expected}


def _check_identity(path, expected, label, directory=True):
    actual = _identity(path)
    _fail(isinstance(expected, dict), label + " identity missing")
    for key in ("path", "dev", "inode", "uid", "gid", "mode", "file_type"):
        _fail(expected.get(key) == actual[key], label + " identity changed: " + key)
    if directory:
        _fail(actual["file_type"] == stat.S_IFDIR, label + " is not a directory")
    return actual


def _toolchain_roots(request):
    rows = request.get("toolchain_roots")
    _fail(isinstance(rows, list) and rows, "toolchain_roots are required")
    seen = []
    for row in rows:
        _fail(isinstance(row, dict) and set(row) == {"path", "inventory"}, "toolchain root row")
        path = _canonical(row.get("path", ""), "toolchain root", directory=True)
        inventory = row.get("inventory")
        _fail(isinstance(inventory, dict) and inventory, "toolchain root inventory")
        observed = {}
        for item in path.rglob("*"):
            relative = str(item.relative_to(path))
            st = item.lstat()
            _fail(not stat.S_ISLNK(st.st_mode), "toolchain root contains symlink")
            _fail(stat.S_ISREG(st.st_mode) or stat.S_ISDIR(st.st_mode),
                  "toolchain root contains special file")
            row_data = {"mode": stat.S_IMODE(st.st_mode),
                        "type": "directory" if stat.S_ISDIR(st.st_mode) else "file"}
            if stat.S_ISREG(st.st_mode):
                row_data.update(size=st.st_size, sha256=_sha256(item))
            observed[relative] = row_data
        _fail(observed == inventory, "toolchain root inventory differs")
        for other in seen:
            _fail(path != other and path not in other.parents and other not in path.parents,
                  "toolchain roots overlap")
        seen.append(path)
    return seen


def _v2_mount_roots(request, toolchain_doc):
    """Bind host closures to their container spelling without leaking it into v2.

    The v2 toolchain document is consumed verbatim inside the image and hence
    contains only ``/out``/``/nightly`` paths.  The owner-only request supplies
    the separate host mapping and is checked against the same inventories.
    """
    document_rows = toolchain_doc.get("toolchain_roots")
    request_rows = request.get("toolchain_roots")
    _fail(isinstance(document_rows, list) and isinstance(request_rows, list) and
          document_rows and len(document_rows) == len(request_rows),
          "v2 toolchain roots missing")
    document = {}
    for row in document_rows:
        _fail(isinstance(row, dict) and set(row) == {"path", "inventory"} and
              row["path"] in ("/out", "/nightly") and isinstance(row["inventory"], dict),
              "v2 container root row")
        _fail(row["path"] not in document, "duplicate v2 container root")
        document[row["path"]] = row["inventory"]
    mounted = {}
    for row in request_rows:
        _fail(isinstance(row, dict) and set(row) == {"host_path", "container_path", "inventory"},
              "v2 host root row")
        target = row["container_path"]
        _fail(target in document and target not in mounted and row["inventory"] == document[target],
              "v2 host/container root binding differs")
        host = _canonical(row["host_path"], "v2 host toolchain root", directory=True)
        observed = _closure_inventory(host, host, Path(target))
        _fail(observed == row["inventory"], "v2 toolchain root inventory differs")
        mounted[target] = host
    _fail(set(mounted) == set(document) and set(mounted) == {"/out", "/nightly"},
          "v2 mounted roots incomplete")
    return mounted


def _v2_host_path(raw, mounts, label, directory=False):
    _fail(isinstance(raw, str) and raw.startswith("/"), label + " must be absolute")
    path = Path(raw)
    choices = [(Path(target), root) for target, root in mounts.items()
               if path == Path(target) or Path(target) in path.parents]
    _fail(len(choices) == 1, label + " is outside v2 mounted roots")
    target, root = choices[0]
    candidate = root / path.relative_to(target)
    candidate = _canonical(candidate, label, directory=directory)
    if directory:
        _fail(candidate.is_dir(), label + " must be a directory")
    else:
        _fail(stat.S_ISREG(candidate.lstat().st_mode), label + " must be regular")
    return candidate


def _authenticated_provenance(path):
    module_name = "_mckernel_exact_owner_provenance_%d" % os.getpid()
    module = importlib.util.module_from_spec(importlib.util.spec_from_loader(module_name, loader=None))
    try:
        exec(compile(Path(path).read_bytes(), str(path), "exec"), module.__dict__)
    except BaseException as exc:
        raise OwnerError("authenticated provenance import failed") from exc
    return module


def _git_factory(tool):
    tool_path = tool["path"]
    def git(root, *args):
        command = [tool_path, "-c", "safe.directory=" + str(root),
                   "-c", "core.fsmonitor=", "-c", "core.hooksPath=/dev/null",
                   "-C", str(root), *args]
        env = {"PATH": str(Path(tool_path).parent), "GIT_OPTIONAL_LOCKS": "0",
               "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": "/dev/null",
               "GIT_NO_REPLACE_OBJECTS": "1", "GIT_TERMINAL_PROMPT": "0",
               "LANG": "C", "LC_ALL": "C"}
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                env=env, timeout=30, check=False)
        _fail(result.returncode == 0 and not result.stderr,
              "authenticated Git command failed")
        return result.stdout
    return git


def _validate_authenticated_source(source, manifest, candidate, ihk, tools, provenance_path):
    provenance = _authenticated_provenance(provenance_path)
    if manifest.get('schema') == provenance.THIN_SCHEMA:
        provenance.validate_thin_source(source, manifest, candidate, ihk)
        return
    git = _git_factory(tools["git"])
    try:
        _fail(git(source, "rev-parse", "HEAD").decode().strip() == candidate,
              "source HEAD differs from candidate")
        ihk_root = _canonical(source / "ihk", "IHK checkout", directory=True)
        _fail(git(ihk_root, "rev-parse", "HEAD").decode().strip() == ihk,
              "IHK HEAD differs from manifest")
        production = ihk == provenance.REVIEWED_IHK_HEAD
        if production:
            provenance.verify_ihk_overlay(source, git, applied=True)
        files, links = provenance.source_inventory(source, git, allow_ihk_overlay=production)
    except BaseException as exc:
        if isinstance(exc, OwnerError):
            raise
        raise OwnerError("authenticated source admission failed: " + str(exc)) from exc
    _fail(manifest.get("repository_files") == files, "source inventory differs")
    _fail(manifest.get("gitlinks") == links, "source gitlink inventory differs")


def _proc_starttime(pid):
    """Capture the process identity needed by the image common exclusion."""
    return Path("/proc").joinpath(str(pid), "stat").read_text().rsplit(")", 1)[1].split()[19]


def _admit_request_gitlink(request, source_doc, source, manifest, candidate, ihk,
                           allocation_paths, git_descriptor):
    if source_doc.get('schema') in ('mckernel.native-fp-save-thin-inputs.v1',
                                     'mckernel.rust-fpu-sched-cutover-thin-inputs.v1',
                                     'mckernel.m14-combined-production-thin-inputs.v1'):
        _fail(request.get('gitlink_manifest') is not None and
              request.get('gitlink_root') is not None,
              'thin source requires supplemental libdwarf manifest and root')
    gitlink_manifest = request.get("gitlink_manifest")
    if gitlink_manifest is not None:
        gitlink_manifest = _regular(gitlink_manifest, "gitlink manifest")
        _fail(isinstance(request.get("gitlink_manifest_sha256"), str) and
              re.fullmatch(r"[0-9a-f]{64}", request["gitlink_manifest_sha256"]) and
              _sha256(gitlink_manifest) == request["gitlink_manifest_sha256"],
              "gitlink manifest hash drift")
        gitlink_root = _canonical(request.get("gitlink_root", ""), "libdwarf checkout", directory=True)
        _disjoint((source, gitlink_root))
        _fail(gitlink_root in allocation_paths, "memory allocation roots do not bind libdwarf")
        _validate_gitlink_manifest(_load_json(gitlink_manifest, "gitlink manifest"),
                                   gitlink_manifest, gitlink_root, manifest, candidate, ihk,
                                   git_descriptor)



def preflight_request_crossrefs(request):
    """Read-only deterministic join checks; live admission remains unchanged."""
    _fail(isinstance(request, dict) and request.get('schema') ==
          'mckernel.native-exact-mckernel-image-container-request.v1',
          'image request schema')
    documents = {}
    for key in ('source_manifest', 'gitlink_manifest', 'driver_path'):
        hash_key = 'driver_sha256' if key == 'driver_path' else key + '_sha256'
        path = _regular(request.get(key, ''), key)
        checksum = request.get(hash_key)
        _fail(isinstance(checksum, str) and re.fullmatch(r'[0-9a-f]{64}', checksum)
              and _sha256(path) == checksum, key + ' deterministic hash differs')
        if key != 'driver_path':
            documents[key] = _load_json(path, key)
    _fail(request['driver_sha256'] == EXPECTED_DRIVER_SHA256,
          'offline driver release hash')
    source = documents['source_manifest']
    supplement = documents['gitlink_manifest']
    _fail(isinstance(source, dict) and isinstance(supplement, dict),
          'source/supplement document shape')
    _fail(supplement.get('schema') == 'mckernel.native-exact-mckernel-gitlink-inputs.v1',
          'gitlink manifest schema')
    _fail(supplement.get('base_manifest_sha256') == request['source_manifest_sha256'],
          'gitlink base manifest hash differs')
    _fail(supplement.get('candidate_sha') == request.get('candidate_sha') and
          supplement.get('ihk_sha') == request.get('ihk_sha'),
          'gitlink manifest identity differs')
    rows = supplement.get('consumed_gitlinks')
    key = 'executer/user/lib/libdwarf/libdwarf'
    _fail(isinstance(rows, dict) and set(rows) == {key} and isinstance(rows[key], dict),
          'consumed gitlink set differs')
    row = rows[key]
    _fail(row.get('path') == key and (source.get('gitlinks') or {}).get(key) == row.get('commit')
          and re.fullmatch(r'[0-9a-f]{40}', str(row.get('commit', '')))
          and re.fullmatch(r'[0-9a-f]{40}', str(row.get('tree', ''))),
          'base manifest gitlink differs')
    return {'status': 'PASS_DETERMINISTIC_REQUEST_CROSSREFS_ONLY',
            'source_manifest_sha256': request['source_manifest_sha256'],
            'gitlink_manifest_sha256': request['gitlink_manifest_sha256'],
            'driver_sha256': request['driver_sha256']}


RETIRED_COMMON_EXCLUSIONS = RETIRED_COMMON_EXCLUSIONS | frozenset(('/home/holden/mckernel-work/host-preparation/phase5-opt-in-image-lock-binding-20261020-1/full-image-attempt-1/common-exclusion.json',))

RETIRED_COMMON_EXCLUSIONS = RETIRED_COMMON_EXCLUSIONS | frozenset(('/home/holden/mckernel-work/host-preparation/phase5-opt-in-image-lock-binding-20261020-1/gitlink-nine-copy-observer-correction-1/full-image-attempt-1/common-exclusion.json',))

RETIRED_COMMON_EXCLUSIONS = RETIRED_COMMON_EXCLUSIONS | frozenset(('/home/holden/mckernel-work/host-preparation/numa-insert-clear-image-successor-preparation-20261021-1/production-preflight-correction-preparation-1/full-image-attempt-2/common-exclusion.json',))

def _bfd_inventory(root, selected=None):
    """Fixed consumed closure; Git metadata and Python caches are not inputs."""
    root = Path(root)
    rows = {}
    def walk(path):
        relative = path.relative_to(root).as_posix()
        info = path.lstat()
        row = {"mode": stat.S_IMODE(info.st_mode)}
        if stat.S_ISLNK(info.st_mode):
            target = path.resolve(strict=True)
            _fail(root in target.parents, "BFD source link escapes read-only source")
            _fail(target.is_file() or target.is_dir(), "BFD special link unsupported")
            row.update(type="symlink", target=os.readlink(path),
                       resolved=target.relative_to(root).as_posix(), target_type="directory" if target.is_dir() else "file")
            if target.is_file():
                row["sha256"] = _sha256(target)
        elif stat.S_ISDIR(info.st_mode):
            row["type"] = "directory"
            for child in sorted(path.iterdir()):
                if child.name not in (".git", "__pycache__"):
                    walk(child)
        else:
            _fail(stat.S_ISREG(info.st_mode), "BFD input contains special file")
            row.update(type="file", size=info.st_size, sha256=_sha256(path))
        if relative != ".":
            rows[relative] = row
    if selected is None:
        walk(root)
    else:
        for relative in selected:
            walk(root / relative)
    for row in rows.values():
        if row["type"] == "symlink" and row["target_type"] == "directory":
            _fail(row["resolved"] in rows and rows[row["resolved"]]["type"] == "directory",
                  "BFD directory link target is outside inventoried closure")
    return rows


def _retained_toolchain_request():
    path = _regular(COMPILE_PROFILE["retained_request"], "retained toolchain request")
    _fail(_sha256(path) == COMPILE_PROFILE["retained_request_sha256"], "retained toolchain request changed")
    retained = _load_json(path, "retained toolchain request")
    _fail(retained["image_id"] == COMPILE_PROFILE["image_id"], "retained image changed")
    return retained


def _validate_request(request):
    _validate_compile_domain(request)
    _fail(request.get("schema") == REQUEST_SCHEMA, "BFD request schema")
    _fail(type(request.get("timeout")) is int and 1 <= request["timeout"] <= MAX_TIMEOUT,
          "BFD timeout exceeds retained bound")
    source = _canonical(request["source_root"], "BFD original source", directory=True)
    candidate = _canonical(request["candidate_root"], "BFD proposal", directory=True)
    work = _canonical(request["work_root"], "BFD HOST work", directory=True)
    owner_evidence = _canonical(request["owner_evidence_root"], "BFD owner evidence", directory=True)
    for path in (source, candidate, work, owner_evidence):
        _no_symlink_parents(path, "BFD input/output root")
    _fail(stat.S_IMODE(work.stat().st_mode) == 0o700 and not any(work.iterdir()),
          "BFD HOST work must be private and empty")
    _fail(not any(owner_evidence.iterdir()), "BFD owner evidence must be fresh")
    attempt = _confined_path(request["attempt_root"], "BFD attempt")
    output = _confined_path(request["output_root"], "BFD qualification output")
    for path in (attempt, output, owner_evidence / OWNER_RECEIPT_NAME):
        _fail(not path.exists() and not path.is_symlink(), "BFD output/receipt already exists")
    _disjoint((source, candidate, work, owner_evidence))
    retained = _retained_toolchain_request()
    toolchain = _regular(retained["toolchain_manifest"], "retained SDK toolchain")
    _fail(_sha256(toolchain) == COMPILE_PROFILE["toolchain_manifest_sha256"], "retained SDK manifest changed")
    toolchain_doc = _load_json(toolchain, "retained SDK toolchain")
    mounts = _v2_mount_roots(retained, toolchain_doc)
    _validate_v2_image_tools(retained, toolchain_doc)
    _disjoint((source, candidate, work, owner_evidence, *mounts.values()))
    roots = [source, candidate, *mounts.values()]
    _fail(request.get("memory_allocation_roots") == [str(p) for p in roots], "BFD allocation roots differ")
    _fail(request.get("memory_backed_bytes") == 0, "BFD inputs must be disk-backed")
    disk = request.get("disk_admission")
    _fail(isinstance(disk, dict) and disk.get("host_free_floor") == 16 * 2**30 and
          disk.get("scratch_free_floor") == 12 * 2**30, "BFD disk floors differ")
    for key in ("host", "scratch"):
        measured = _canonical(disk.get(key + "_root", ""), key + " measurement root", directory=True)
        _fail(measured.stat().st_dev == disk.get(key + "_device"), key + " measurement device changed")
    bound = {"source": source, "candidate": candidate, "work": work,
             "output": output, "evidence": output, "owner_evidence": owner_evidence,
             "attempt": attempt, "host_owner": _HOST_OWNER, "host_owner_path": _HOST_OWNER_PATH,
             "allocation_roots": roots, "mounts_by_target": mounts}
    _revalidate_inputs(bound, request)
    bound["measurement"] = _HOST_OWNER.measure(disk["host_root"], disk["scratch_root"],
        16 * 2**30, 12 * 2**30, source_root=source, output_root=work, memory_allocation_roots=roots)
    _fail(bound["measurement"]["memory_allocation_memory_backed_bytes"] == 0 and
          bound["measurement"]["aggregate_memory_required"] == LIMITS["Memory"], "BFD allocation measurement changed")
    return bound


def _check_profile(info, image, nonce, mounts=None, command=None, user=None,
                   host_owner=None):
    (host_owner or _HOST_OWNER).check_profile(info, image, nonce)
    _fail(info.get("Config", {}).get("Labels", {}).get("mckernel.operation") == COMPILE_PROFILE["operation"], "compile operation label mismatch")
    config = info.get("Config", {})
    if command is not None:
        _fail(config.get("Entrypoint") == ["/usr/bin/env"] and config.get("Cmd") == command,
              "effective driver command mismatch")
    if user is not None:
        _fail(config.get("User") == user, "effective container user mismatch")
    if mounts is not None:
        expected = {(str(source), target, not readonly) for source, target, readonly in mounts}
        actual = {(row.get("Source"), row.get("Destination"), row.get("RW"))
                  for row in info.get("Mounts", []) if row.get("Type") == "bind"}
        _fail(actual == expected, "effective bind mounts mismatch")
        _fail(all(row.get("Type") in ("bind", "tmpfs") for row in info.get("Mounts", [])),
              "unexpected effective mount type")
        tmpfs_mounts = [row for row in info.get("Mounts", []) if row.get("Type") == "tmpfs"]
        _fail(not tmpfs_mounts or (len(tmpfs_mounts) == 1 and
              tmpfs_mounts[0].get("Destination") == "/tmp" and
              tmpfs_mounts[0].get("RW") is True), "unexpected effective tmpfs mount")
    tmpfs = config_host = info.get("HostConfig", {}).get("Tmpfs")
    _fail(tmpfs == {"/tmp": "rw,nodev,nosuid,size=256m"},
          "effective tmpfs profile mismatch")


# The accepted host owner supplies the reviewed lease, signal, Docker transport,
# inspection, and retirement semantics.  Image-specific admission remains local.
Lease = _HOST_OWNER.Lease
Docker = _HOST_OWNER.Docker
Signals = _HOST_OWNER.CliSignals
_inspect = _HOST_OWNER.inspect
_retire = _HOST_OWNER.retire


def _validate_driver_result(evidence, output, result, request):
    output = _safe_directory(output, "BFD qualification output")
    _fail(evidence == output, "BFD evidence/output contract differs")
    _fail(result.get("status") == "PASS_PINNED_ABI_AND_SELECTED_USER_TOOL_ARTIFACTS" and
          result.get("scope") == SCOPE and result.get("native_acceptance") is False and
          result.get("M15_file_closure") is False, "BFD qualifier result contract differs")
    pins = _load_json(Path(COMPILE_PROFILE["candidate_root"]) / "PINNED-ABI.json", "BFD pins")
    _fail(result.get("pins") == pins and isinstance(result.get("layout"), str) and result["layout"], "BFD pin/layout result differs")
    _fail(not (output / "FAILURE.json").exists(), "BFD failure evidence present")
    comparisons = result.get("comparisons")
    _fail(isinstance(comparisons, list) and len(comparisons) == 8, "BFD comparison set incomplete")
    cases = {"mcinspect": [["--help"], [], ["--kernel=/work/qualification-1/absent.img", "--ps"],
                           ["--kernel=/work/qualification-1/stripped.o", "--ps"]],
             "eclair": [["-h"], ["-k", "/work/qualification-1/absent.img", "-d", "/work/qualification-1/absent.dump"],
                        ["-k", "/work/qualification-1/stripped.o", "-d", "/work/qualification-1/absent.dump"],
                        ["-k", "/work/qualification-1/fixture.o", "-d", "/work/qualification-1/absent.dump"]]}
    expected = [(tool, args) for tool in ("mcinspect", "eclair") for args in cases[tool]]
    _fail([(row.get("tool"), row.get("args")) for row in comparisons] == expected and
          all(row.get("matched") is True and type(row.get("rc")) is int for row in comparisons), "BFD behavior comparisons differ")
    for tool in ("mcinspect", "eclair"):
        for i in range(4):
            for stream in ("stdout", "stderr"):
                original = _safe_regular(output / f"{tool}-{i}-original.{stream}", "BFD baseline stream")
                rust = _safe_regular(output / f"{tool}-{i}-rust.{stream}", "BFD Rust stream")
                _fail(original.read_bytes() == rust.read_bytes(), "BFD retained behavior streams differ")
    commands = json.loads(_safe_regular(output / "commands.json", "BFD command capture").read_text())
    names = ["witness-build", "witness-run", "witness-preprocessed", "rust-build", "mcinspect-original-compile",
             "eclair-original-compile", "equivalence-link", "fixture-compile", "fixture-strip", "equivalence-run",
             "rust-symbols", "selected-configure", "selected-build", "mcinspect-baseline-compile", "mcinspect-baseline-link",
             "mcinspect-dynamic", "mcinspect-symbols", "eclair-baseline-compile", "eclair-baseline-link", "eclair-dynamic", "eclair-symbols"]
    _fail(isinstance(commands, list) and [row.get("log") for row in commands] == names and
          all(type(row.get("rc")) is int and row["rc"] == 0 for row in commands), "BFD command capture incomplete/failing")
    for name in names:
        for stream in ("stdout", "stderr"):
            _safe_regular(output / (name + "." + stream), "BFD command stream")
    symbols = (output / "rust-symbols.stdout").read_text()
    names = re.findall(r"\bT\s+((?:mcinspect|eclair)_bfd_(?:get_symtab_upper_bound|canonicalize_symtab)_bridge)\b", symbols)
    expected_symbols = {tool + "_bfd_" + function + "_bridge" for tool in ("mcinspect", "eclair")
                        for function in ("get_symtab_upper_bound", "canonicalize_symtab")}
    _fail(len(names) == 4 and set(names) == expected_symbols and not re.search(r"\bU\s+(?:mcinspect|eclair)_bfd_", symbols),
          "BFD four-definition/no-old-wrapper result differs")
    for relative in ("bfd_accessors.o", "bfd_layout.rs", "equivalence", "layout-witness", "fixture.o", "stripped.o",
                     "selected-tools/executer/user/mcinspect", "selected-tools/executer/user/eclair",
                     "selected-tools/executer/user/CMakeFiles/mcinspect.dir/link.txt",
                     "selected-tools/executer/user/CMakeFiles/eclair.dir/link.txt"):
        _fail(_safe_regular(output / relative, "BFD qualification artifact").stat().st_size > 0, "BFD artifact empty")


def _revalidate_inputs(bound, request):
    _validate_compile_domain(request)
    _check_identity(bound["source"], COMPILE_PROFILE["source_identity"], "BFD source root")
    _check_identity(bound["candidate"], COMPILE_PROFILE["candidate_identity"], "BFD proposal root")
    manifest = _regular(COMPILE_PROFILE["input_manifest"], "BFD fixed inputs")
    _fail(_sha256(manifest) == COMPILE_PROFILE["input_manifest_sha256"], "BFD fixed input manifest changed")
    inputs = _load_json(manifest, "BFD fixed inputs")
    _fail(_bfd_inventory(bound["candidate"]) == inputs["candidate"], "BFD candidate closure changed")
    _fail(_bfd_inventory(bound["source"], inputs["source_roots"]) == inputs["source"], "BFD consumed source closure changed")
    binding = _load_json(bound["candidate"] / "SOURCE-BINDING.json", "BFD original source binding")
    for relative, digest in binding["sources"].items():
        _fail(_sha256(bound["source"] / relative) == digest, "BFD selected original source changed: " + relative)
    _fail(_sha256(_HOST_OWNER_PATH) == EXPECTED_HOST_OWNER_SHA256, "BFD host helper changed")
    retained = _retained_toolchain_request()
    toolchain = _regular(retained["toolchain_manifest"], "retained SDK toolchain")
    _fail(_sha256(toolchain) == COMPILE_PROFILE["toolchain_manifest_sha256"], "retained SDK manifest changed")
    toolchain_doc = _load_json(toolchain, "retained SDK toolchain")
    _fail(_v2_mount_roots(retained, toolchain_doc) == bound["mounts_by_target"], "retained SDK mounts changed")
    _validate_v2_image_tools(retained, toolchain_doc)


COMPILE_PROFILE = {'activation': 'COMPILE_LINK_ONLY_NO_GUEST_OR_KERNEL_ACTIVATION', 'admission_max_age_ns': 120000000000, 'image_id': 'sha256:41778f1f22fd68897c1209e225a9807a197ed47bf0edd17835821bb5986e50b5', 'jobs': 1, 'minimum_MemAvailable': 25769803776, 'reserved_native_profile': {'CpusetCpus': '2-5', 'Memory': 12884901888, 'MemorySwap': 12884901888, 'NanoCpus': 4000000000, 'NetworkMode': 'none', 'PidsLimit': 512}, 'sole_rw_mount_target': '/work', 'toolchain_manifest_sha256': 'a68e02b3b66b8bfbae96bf742dc8702b6e81dd97b92189b87437c3d08fccdf72', 'schema': 'mckernel.m15-bfd-compile-link-profile.v1', 'scope': 'Functional McKernel OS/apps and Rust/assembly migration only; no security testing.', 'operation': 'M15_BFD_PINNED_SELECTED_USER_TOOLS_COMPILE_ONLY_V1', 'namespace': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-8/m15-bfd-owner-successor/operation-1', 'lease_path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-8/m15-bfd-owner-successor/operation-1/compile-lease.json', 'owner_nonce': 'bf69b996f71f4cb1bb0a50d7aa43aaa8', 'container_name': 'mckernel-m15-bfd-compile-bf69b996f71f4cb1bb0a50d7aa43aaa8', 'host_helper_sha256': '76ff839a839a2f55cd7d537d22221cb1b053390e2b6052b8be2b5d8b20990e63', 'limits': {'CpusetCpus': '6', 'Memory': 2147483648, 'MemorySwap': 2147483648, 'NanoCpus': 1000000000, 'NetworkMode': 'none', 'PidsLimit': 128}, 'candidate_root': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-8/m15-bfd', 'source_root': '/home/holden/mckernel', 'source_identity': {'path': '/home/holden/mckernel', 'dev': 66306, 'inode': 47459795, 'uid': 1000, 'gid': 1000, 'mode': 509, 'file_type': 16384}, 'candidate_identity': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-8/m15-bfd', 'dev': 66306, 'inode': 56125093, 'uid': 1000, 'gid': 1000, 'mode': 509, 'file_type': 16384}, 'input_manifest': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-8/m15-bfd-owner-successor/BFD-INPUTS.json', 'input_manifest_sha256': 'aed4fd1dc6d49e83320714e683ea4adb360614efc9633fe93b3e96254d587bc8', 'retained_request': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-4/dual-container/reuse/compile-only-candidate/compile-request.PREPARED.json', 'retained_request_sha256': '92bcb96713c498bf2397bb24c3473a2ffbeb61f45dfa423a6ae8b99f4a4ffe4f', 'command': ['/usr/bin/env', '-i', 'PATH=/nightly/bin:/usr/bin:/bin', 'LANG=C', 'LC_ALL=C', '/usr/bin/python3', '/candidate/orchestration/qualify.py', '--repo', '/src', '--output', '/work/qualification-1']}
COMPILE_PROFILE_PATH = Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-8/m15-bfd-owner-successor/COMPILE-PROFILE.json')
COMPILE_PROFILE_SHA256 = 'e25bec3d2864245092c4202e6ce05c20e00ea8914e8a932eacd19f7a3f3e159a'
PRIVATE_ROOT = Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-8/m15-bfd-owner-successor')


def _canonical_hash(document):
    return hashlib.sha256(json.dumps(document, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def _request_core_hash(request):
    return _canonical_hash({k: v for k, v in request.items() if k != "compile_only_release"})


def _validate_compile_domain(request):
    """One fixed HOST compile domain; never a native-owner exemption switch."""
    _fail(isinstance(request, dict), "compile request must be an object")
    _fail(request.get("compile_operation") == COMPILE_PROFILE["operation"], "compile domain mismatch")
    _fail(request.get("compile_profile_sha256") == COMPILE_PROFILE_SHA256 and
          _sha256(COMPILE_PROFILE_PATH) == COMPILE_PROFILE_SHA256, "compile profile changed")
    _fail(_load_json(COMPILE_PROFILE_PATH, "compile profile") == COMPILE_PROFILE, "compile profile bytes differ")
    _fail(LIMITS == COMPILE_PROFILE["limits"] and _HOST_OWNER.LIMITS == LIMITS,
          "private compile owner/helper limits differ")
    _fail(request.get("jobs") == 1 and request.get("aggregate_memory_required") == LIMITS["Memory"],
          "compile jobs/aggregate profile mismatch")
    for key in ("source_root", "candidate_root", "input_manifest_sha256", "toolchain_manifest_sha256", "image_id"):
        _fail(request.get(key) == COMPILE_PROFILE[key], "fixed BFD input differs: " + key)
    _fail(request.get("exact_command") == COMPILE_PROFILE["command"], "fixed BFD command differs")
    root = Path(COMPILE_PROFILE["namespace"])
    expected = {"work_root": root / "owner-work", "output_root": root / "owner-work/qualification-1",
                "evidence_root": root / "owner-work/qualification-1", "owner_evidence_root": root / "owner-evidence",
                "attempt_root": root / "owner-evidence/attempt", "lease_path": root / "compile-lease.json",
                "common_exclusion_path": root / "compile-lease.json",
                "host_owner_path": _HOST_OWNER_PATH}
    _fail(root.parent == PRIVATE_ROOT, "compile namespace escapes private candidate")
    for key, path in expected.items():
        _fail(request.get(key) == str(path), "compile HOST path differs: " + key)
        _no_symlink_parents(path, "compile HOST path")
    _fail(request.get("host_owner_sha256") == EXPECTED_HOST_OWNER_SHA256 == COMPILE_PROFILE["host_helper_sha256"],
          "private compile helper binding differs")
    _fail(root.stat().st_dev == PRIVATE_ROOT.stat().st_dev and
          Path(request["work_root"]).stat().st_dev == PRIVATE_ROOT.stat().st_dev,
          "compile outputs must stay on the private HOST filesystem")
    return expected


def _read_root_document(ref, exact_path, label):
    _fail(isinstance(ref, dict) and set(ref) == {"path", "sha256"} and
          ref.get("path") == str(exact_path) and re.fullmatch(r"[0-9a-f]{64}", ref.get("sha256", "")),
          label + " reference missing or differs")
    _no_symlink_parents(exact_path, label)
    before = os.lstat(exact_path)
    _fail(stat.S_ISREG(before.st_mode) and before.st_uid == 0 and before.st_nlink == 1 and
          not stat.S_IMODE(before.st_mode) & 0o022 and before.st_size <= 2**20,
          label + " must be a sealed root-owned regular file")
    raw = exact_path.read_bytes()
    after = os.lstat(exact_path)
    _fail((before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns, before.st_ctime_ns) ==
          (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns), label + " changed during read")
    _fail(hashlib.sha256(raw).hexdigest() == ref["sha256"], label + " hash mismatch")
    document = json.loads(raw)
    _fail(isinstance(document, dict), label + " must be an object")
    return document


def _boottime_ns():
    return time.clock_gettime_ns(time.CLOCK_BOOTTIME)


def _mem_available():
    return int(next(row.split()[1] for row in Path("/proc/meminfo").read_text().splitlines()
                    if row.startswith("MemAvailable:"))) * 1024


def _validate_launch_admission(request):
    """Fail closed until root binds actual live P12 facts and source review."""
    _validate_compile_domain(request)
    release = _read_root_document(request.get("compile_only_release"), PRIVATE_ROOT / "ROOT-RELEASE.json", "compile release")
    _fail(release.get("status") == "RELEASED_FOR_ONE_COMPILE_ONLY_M15_BFD" and
          release.get("operation") == COMPILE_PROFILE["operation"] and
          release.get("request_core_sha256") == _request_core_hash(request) and
          release.get("profile_sha256") == COMPILE_PROFILE_SHA256 and
          release.get("owner_sha256") == _sha256(Path(__file__)) and
          release.get("host_helper_sha256") == EXPECTED_HOST_OWNER_SHA256,
          "root compile release bindings differ")
    _fail(isinstance(release.get("independent_source_review_sha256"), str) and
          re.fullmatch(r"[0-9a-f]{64}", release["independent_source_review_sha256"]),
          "independent source review binding missing")
    facts = _read_root_document(release.get("root_admission"), PRIVATE_ROOT / "ROOT-ADMISSION.json", "root live admission")
    _fail(facts.get("schema") == "mckernel.m15-bfd-dual-container-admission.v1" and
          facts.get("operation") == COMPILE_PROFILE["operation"] and
          facts.get("request_core_sha256") == _request_core_hash(request) and
          facts.get("profile_sha256") == COMPILE_PROFILE_SHA256,
          "root live admission bindings differ")
    _fail(facts.get("cpu6_consumer_joined") is True and facts.get("P12_sole_native_heavy") is True,
          "CPU6/native lane prerequisites missing")
    _fail(facts.get("compile_limits") == LIMITS and
          facts.get("P12_limits") == COMPILE_PROFILE["reserved_native_profile"],
          "concurrent resource reservation differs")
    _fail(facts.get("capacity_verdict") == "PASS_DUAL_CONTAINER_COMPILE_CPU6_2G" and
          facts.get("controller_allowance_reviewed") is True and
          facts.get("native_cgroups_unchanged") is True, "concurrent capacity/controller agreement missing")
    for available, required in (("HOST_available", "HOST_required"), ("scratch_available", "scratch_required")):
        _fail(type(facts.get(available)) is int and type(facts.get(required)) is int and
              facts[required] >= (16 if available == "HOST_available" else 12) * 2**30 and
              facts[available] >= facts[required], "concurrent disk capacity admission differs")
    p12 = facts.get("P12")
    _fail(isinstance(p12, dict) and set(p12) == {"id", "name", "owner_label_key", "owner_label_value", "config_sha256", "host_config_sha256"},
          "root P12 identity binding missing")
    _fail(re.fullmatch(r"[0-9a-f]{64}", p12.get("id", "")) and
          isinstance(p12.get("name"), str) and p12["name"].startswith("/") and
          p12["name"] != "/" + COMPILE_PROFILE["container_name"] and
          isinstance(p12.get("owner_label_key"), str) and p12["owner_label_key"] and
          isinstance(p12.get("owner_label_value"), str) and p12["owner_label_value"] and
          all(re.fullmatch(r"[0-9a-f]{64}", p12.get(k, "")) for k in ("config_sha256", "host_config_sha256")),
          "root P12 identity malformed")
    roots = facts.get("P12_rw_roots")
    _fail(isinstance(roots, list) and roots, "root P12 RW domains missing")
    own = Path(request["work_root"])
    for raw in roots:
        _fail(isinstance(raw, str) and Path(raw).is_absolute() and raw == os.path.abspath(raw),
              "P12 RW domain malformed")
        other = Path(raw)
        _fail(own != other and own not in other.parents and other not in own.parents,
              "compile/P12 output domains overlap")
    _fresh_compile_resources(facts)
    return {"release": release, "facts": facts}


def _fresh_compile_resources(facts):
    age = _boottime_ns() - facts.get("observed_boottime_ns", -10**30)
    _fail(facts.get("boot_id") == Path("/proc/sys/kernel/random/boot_id").read_text().strip() and
          type(facts.get("observed_boottime_ns")) is int and
          0 <= age <= COMPILE_PROFILE["admission_max_age_ns"], "root live admission expired or wrong boot")
    _fail(type(facts.get("MemAvailable")) is int and
          facts["MemAvailable"] >= COMPILE_PROFILE["minimum_MemAvailable"], "root memory admission below 24GiB")
    observed = _mem_available()
    _fail(observed >= COMPILE_PROFILE["minimum_MemAvailable"], "fresh MemAvailable below 24GiB")
    return {"MemAvailable": observed, "root_admission_age_ns": age, "observed_boottime_ns": _boottime_ns()}


def _check_live_p12(docker, facts):
    expected = facts["P12"]
    rows = json.loads(docker.call(["inspect", expected["id"]]).stdout)
    _fail(isinstance(rows, list) and len(rows) == 1, "P12 inspect identity ambiguous")
    info = rows[0]
    _fail(info.get("Id") == expected["id"] and info.get("Name") == expected["name"] and
          info.get("State", {}).get("Running") is True and
          info.get("Config", {}).get("Labels", {}).get(expected["owner_label_key"]) == expected["owner_label_value"],
          "P12 identity/state changed")
    _fail(_canonical_hash(info.get("Config")) == expected["config_sha256"] and
          _canonical_hash(info.get("HostConfig")) == expected["host_config_sha256"], "P12 effective config changed")
    _fail(all(info.get("HostConfig", {}).get(k) == v for k, v in COMPILE_PROFILE["reserved_native_profile"].items()),
          "P12 effective resource reservation changed")
    return {"id": info["Id"], "name": info["Name"], "config_sha256": expected["config_sha256"],
            "host_config_sha256": expected["host_config_sha256"], "running": True}


class CompileLease:
    """One exclusively owned HOST record; no native/global record access."""
    def __init__(self, request):
        self.path = Path(request["lease_path"])
        _fail(str(self.path) == COMPILE_PROFILE["lease_path"], "compile lease domain mismatch")
        self.record = {"schema": "mckernel.m15-bfd-compile-lease.v1", "operation": COMPILE_PROFILE["operation"],
                       "pid": os.getpid(), "starttime": _proc_starttime(os.getpid()),
                       "boot_id": Path("/proc/sys/kernel/random/boot_id").read_text().strip(),
                       "request_core_sha256": _request_core_hash(request), "profile_sha256": COMPILE_PROFILE_SHA256,
                       "container_name": COMPILE_PROFILE["container_name"], "owner_nonce": COMPILE_PROFILE["owner_nonce"]}

    def acquire(self):
        _no_symlink_parents(self.path, "compile lease")
        fd = os.open(self.path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0), 0o600)
        try:
            meta = os.fstat(fd)
            self.record.update(device=meta.st_dev, inode=meta.st_ino)
            raw = (json.dumps(self.record, sort_keys=True) + "\n").encode()
            offset = 0
            while offset < len(raw):
                written = os.write(fd, raw[offset:])
                _fail(written > 0, "compile lease short write")
                offset += written
            os.fsync(fd)
        finally:
            os.close(fd)
        _fsync_dir(self.path.parent)

    def load_owned(self):
        _no_symlink_parents(self.path, "compile lease")
        fd = os.open(self.path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
        try:
            meta = os.fstat(fd)
            raw = os.read(fd, 1 << 20)
            current = json.loads(raw)
            _fail(current == self.record and meta.st_dev == self.record["device"] and
                  meta.st_ino == self.record["inode"] and meta.st_size == len(raw), "compile lease ownership changed")
            return raw
        finally:
            os.close(fd)

    def release_accepted(self, acceptance):
        _fail(acceptance.get("status") == "ACCEPTED_COMPILE_ONLY_PHYSICAL_RETIREMENT" and
              acceptance.get("operation") == self.record["operation"] and
              acceptance.get("request_core_sha256") == self.record["request_core_sha256"] and
              acceptance.get("lease_sha256") == hashlib.sha256(self.load_owned()).hexdigest(),
              "compile lease physical acceptance differs")
        parent_fd = os.open(self.path.parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0))
        try:
            fd = os.open(self.path.name, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0), dir_fd=parent_fd)
            try:
                meta = os.fstat(fd)
                raw = os.read(fd, 1 << 20)
                _fail(json.loads(raw) == self.record and meta.st_dev == self.record["device"] and
                      meta.st_ino == self.record["inode"] and meta.st_size == len(raw), "compile lease changed at release")
                os.unlink(self.path.name, dir_fd=parent_fd)
                os.fsync(parent_fd)
            finally:
                os.close(fd)
        finally:
            os.close(parent_fd)


def _assert_owned_container(info, cid=None):
    _fail(isinstance(info, dict) and re.fullmatch(r"[0-9a-f]{64}", info.get("Id", "")) and
          info.get("Name") == "/" + COMPILE_PROFILE["container_name"] and
          (cid is None or info["Id"] == cid) and info.get("Image") == COMPILE_PROFILE["image_id"] and
          info.get("Config", {}).get("Labels", {}).get("mckernel.owner") == COMPILE_PROFILE["owner_nonce"] and
          info.get("Config", {}).get("Labels", {}).get("mckernel.operation") == COMPILE_PROFILE["operation"],
          "refusing lifecycle operation outside exact compiler ownership")
    _fail(all(info.get("HostConfig", {}).get(k) == v for k, v in LIMITS.items()),
          "owned compiler resource profile changed")
    return info["Id"]


def _own_inspect(docker, cid=None):
    target = cid or COMPILE_PROFILE["container_name"]
    rows = json.loads(docker.call(["inspect", target]).stdout)
    _fail(isinstance(rows, list) and len(rows) == 1, "owned compiler inspect ambiguous")
    _assert_owned_container(rows[0], cid)
    return rows[0]


def _own_absence(docker, cid):
    _fail(re.fullmatch(r"[0-9a-f]{64}", cid or ""), "owned compiler ID missing for absence")
    rows = []
    filters = ("id=" + cid, "name=^/" + COMPILE_PROFILE["container_name"] + "$",
               "label=mckernel.owner=" + COMPILE_PROFILE["owner_nonce"])
    for value in filters:
        result = docker.call(["ps", "--all", "--no-trunc", "--filter", value, "--format", "{{.ID}}"])
        _fail(result.returncode == 0 and not result.stdout.strip() and not result.stderr.strip(),
              "compiler container absence unproven")
        rows.append({"filter": value, "returncode": result.returncode, "stdout": result.stdout, "stderr": result.stderr})
    return rows


def _cleanup_owned_compile(docker, attempt, cid=None):
    """Only captured compiler CID; P12 is never a lifecycle target."""
    info = _own_inspect(docker, cid)
    cid = info["Id"]
    if info.get("State", {}).get("Running") or info.get("State", {}).get("Status") in ("paused", "restarting"):
        docker.call(["stop", "--time", "15", cid], timeout=30, check=False)
        info = _own_inspect(docker, cid)
        if info.get("State", {}).get("Running"):
            docker.call(["kill", cid], timeout=30)
        docker.call(["wait", cid], timeout=30)
        info = _own_inspect(docker, cid)
    _fail(info.get("State", {}).get("Running") is False and info["State"].get("Pid") == 0 and
          info["State"].get("Status") in ("exited", "created", "dead"), "owned compiler retirement unproven")
    logs = docker.call(["logs", cid])
    _exclusive_text(attempt / "container.log", logs.stdout + logs.stderr)
    _exclusive_json(attempt / "terminal-before-removal.json", info)
    _fail(not getattr(docker, "client_retirement_unproven", False), "compiler Docker client retirement unproven")
    # Reinspect the immutable CID directly before removal; never remove by a reused name.
    _own_inspect(docker, cid)
    docker.call(["rm", cid])
    absence = _own_absence(docker, cid)
    _fail(not getattr(docker, "client_retirement_unproven", False), "compiler cleanup client retirement unproven")
    return {"retired": True, "container_id": cid, "container_absence_confirmed": True,
            "all_docker_clients_joined": True, "terminal_before_removal": info, "absence": absence,
            "cleanup_separately_required": False, "terminal_container_info": None,
            "terminal_container_info_current": True, "lease_retained_for_root_acceptance": True}


def _compile_mounts(bound):
    mounts = [(bound["source"], "/src", True), (bound["candidate"], "/candidate", True),
              (bound["work"], "/work", False)]
    _fail(set(bound["mounts_by_target"]) == {"/out", "/nightly"}, "retained pinned/nightly mounts required")
    mounts += [(path, target, True) for target, path in sorted(bound["mounts_by_target"].items())]
    _fail([(str(path), target) for path, target, ro in mounts if not ro] ==
          [(str(Path(COMPILE_PROFILE["namespace"]) / "owner-work"), "/work")], "sole HOST RW BFD mount differs")
    return mounts


def _compile_command(bound, request):
    return list(COMPILE_PROFILE["command"][1:])


def _compile_create_args(bound, request):
    mounts = _compile_mounts(bound)
    command = _compile_command(bound, request)
    args = ["create", "--name", COMPILE_PROFILE["container_name"], "--label", "mckernel.owner=" + COMPILE_PROFILE["owner_nonce"],
            "--label", "mckernel.operation=" + COMPILE_PROFILE["operation"], "--init", "--network=none", "--ipc=private",
            *RESOURCE_ARGS, "--user", "1000:1000", "--cap-drop=ALL", "--security-opt=no-new-privileges", "--read-only",
            "--tmpfs", "/tmp:rw,nodev,nosuid,size=256m"]
    for source, target, readonly in mounts:
        args += ["--mount", "type=bind,src=" + str(source) + ",dst=" + target + (",readonly" if readonly else "")]
    args += ["--entrypoint", "/usr/bin/env", request["image_id"], *command]
    return args, mounts, command


def release_accepted_compile_lease(request, docker=None):
    """Separate root-approved physical retirement; never a build/native release."""
    _validate_compile_domain(request)
    _fail(os.getuid() == os.geteuid() == os.getgid() == os.getegid() == 1000, "ordinary holden release controller required")
    acceptance_path = PRIVATE_ROOT / "ROOT-PHYSICAL-ACCEPTANCE.json"
    # Root publishes the exact acceptance hash in a separate root-owned reference.
    ref_path = PRIVATE_ROOT / "ROOT-PHYSICAL-ACCEPTANCE-REF.json"
    _no_symlink_parents(ref_path, "physical acceptance reference")
    meta = os.lstat(ref_path)
    _fail(stat.S_ISREG(meta.st_mode) and meta.st_uid == 0 and meta.st_nlink == 1 and
          not stat.S_IMODE(meta.st_mode) & 0o022 and meta.st_size <= 4096, "root physical acceptance reference required")
    acceptance = _read_root_document(json.loads(ref_path.read_text()), acceptance_path, "root compile physical acceptance")
    _fail(acceptance.get("status") == "ACCEPTED_COMPILE_ONLY_PHYSICAL_RETIREMENT" and
          acceptance.get("operation") == COMPILE_PROFILE["operation"] and
          acceptance.get("request_core_sha256") == _request_core_hash(request) and
          acceptance.get("owner_sha256") == _sha256(Path(__file__)) and
          acceptance.get("profile_sha256") == COMPILE_PROFILE_SHA256 and
          acceptance.get("owner_and_controller_joined") is True and
          acceptance.get("all_owned_client_identities_retired") is True,
          "root physical acceptance bindings differ")
    receipt_path = Path(request["owner_evidence_root"]) / OWNER_RECEIPT_NAME
    _fail(acceptance.get("owner_receipt_sha256") == _sha256(receipt_path), "accepted compile receipt changed")
    receipt = _load_json(receipt_path, "compile receipt")
    _fail(receipt.get("retired") is True and receipt.get("container_absence_confirmed") is True and
          receipt.get("all_docker_clients_joined") is True and receipt.get("operation") == COMPILE_PROFILE["operation"] and
          receipt.get("request_core_sha256") == _request_core_hash(request), "compile receipt has no physical retirement")
    cid = receipt.get("container_id")
    attempt = Path(request["attempt_root"])
    client = docker or _HOST_OWNER.Docker(attempt / "lease-release-docker.log", sudo=True)
    absence = _own_absence(client, cid)
    _fail(not getattr(client, "client_retirement_unproven", False), "lease-release Docker clients unproven")
    lease = CompileLease(request)
    stored = _load_json(lease.path, "compile lease")
    for key in ("schema", "operation", "request_core_sha256", "profile_sha256", "container_name", "owner_nonce"):
        _fail(stored.get(key) == lease.record[key], "accepted compile lease binding differs")
    lease.record = stored
    lease.load_owned()
    _exclusive_json(attempt / "accepted-lease-release-intent.json", {
        "operation": COMPILE_PROFILE["operation"], "acceptance": acceptance, "fresh_own_absence": absence,
        "lease_record": stored, "lease_sha256": hashlib.sha256(lease.load_owned()).hexdigest()})
    lease.release_accepted(acceptance)
    result = {"status": "PASS_COMPILE_ONLY_LEASE_RELEASED", "operation": COMPILE_PROFILE["operation"],
              "lease_record": stored, "container_id": cid, "fresh_own_absence": absence,
              "native_guest_or_heavy_release": False}
    _exclusive_json(attempt / "accepted-lease-release-result.json", result)
    return result


class ImageOwner:
    def __init__(self, request, docker=None, signals=None):
        self.request = dict(request); self.docker = docker; self.signals = signals

    def validate(self):
        self.bound = _validate_request(self.request)
        _fail(os.geteuid() != 0, "owner must be unprivileged")
        return self.bound

    def run(self):
        r = self.request
        _fail(os.getuid() == os.geteuid() == os.getgid() == os.getegid() == 1000,
              "ordinary holden compile owner required")
        # NULL release rejects before full validation, lease or Docker construction.
        authority = _validate_launch_admission(r)
        bound = self.validate()
        _revalidate_inputs(bound, r)
        authority = _validate_launch_admission(r)
        lease = CompileLease(r)
        lease.acquire()
        receipt = {"schema": "mckernel.m15-bfd-compile-owner-receipt.v1", "status": "FAIL",
                   "scope": "Functional McKernel OS/apps and Rust/assembly migration only; no security testing.",
                   "operation": COMPILE_PROFILE["operation"], "profile_sha256": COMPILE_PROFILE_SHA256,
                   "request_core_sha256": _request_core_hash(r), "input_manifest_sha256": r["input_manifest_sha256"],
                   "container_name": COMPILE_PROFILE["container_name"], "owner_nonce": COMPILE_PROFILE["owner_nonce"],
                   "container_id": None, "retired": False, "container_absence_confirmed": False,
                   "all_docker_clients_joined": False, "cleanup_separately_required": True,
                   "lease_retained_for_root_acceptance": True, "compile_lease": lease.record,
                   "candidate_root": r["candidate_root"], "source_root": r["source_root"],
                   "native_guest_or_heavy_release": False, "root_release": r["compile_only_release"],
                   "P12_pre_create": None, "P12_pre_start": None}
        attempted = False
        client = None
        try:
            bound["attempt"].mkdir(mode=0o700)
            _fsync_dir(bound["owner_evidence"])
            client = self.docker or bound["host_owner"].Docker(bound["attempt"] / "docker.log", self.signals, sudo=True)
            image = json.loads(client.call(["image", "inspect", r["image_id"]]).stdout)
            _fail(isinstance(image, list) and len(image) == 1 and image[0].get("Id") == r["image_id"] and
                  image[0].get("Architecture") == "amd64", "compile image identity mismatch")
            authority = _validate_launch_admission(r)
            receipt["P12_pre_create"] = _check_live_p12(client, authority["facts"])
            args, mounts, command = _compile_create_args(bound, r)
            _fail(not getattr(client, "client_retirement_unproven", False), "pre-create Docker clients unproven")
            attempted = True
            created = client.call(args)
            cid = created.stdout.strip()
            _fail(re.fullmatch(r"[0-9a-f]{64}", cid or ""), "compiler create did not return exact CID")
            receipt["container_id"] = cid
            info = _own_inspect(client, cid)
            _check_profile(info, r["image_id"], COMPILE_PROFILE["owner_nonce"], mounts=mounts,
                           command=command, user="1000:1000", host_owner=bound["host_owner"])
            # Rebind actual capacity, accepted facts and P12 identity after container creation.
            authority = _validate_launch_admission(r)
            latest = bound["host_owner"].measure(r["disk_admission"]["host_root"], r["disk_admission"]["scratch_root"],
                16 * 2**30, 12 * 2**30, source_root=bound["source"], output_root=bound["work"],
                memory_allocation_roots=bound["allocation_roots"])
            _fail(latest.get("memory_allocation_memory_backed_bytes") == r["memory_backed_bytes"] and
                  latest.get("aggregate_memory_required") == r["aggregate_memory_required"],
                  "pre-start compile allocation changed")
            receipt["pre_start_measurement"] = latest
            receipt["P12_pre_start"] = _check_live_p12(client, authority["facts"])
            receipt["fresh_concurrent_resources"] = _fresh_compile_resources(authority["facts"])
            _fail(not getattr(client, "client_retirement_unproven", False), "pre-start Docker clients unproven")
            client.call(["start", cid])
            waited = client.call(["wait", cid], timeout=r["timeout"])
            receipt["exit_code"] = int(waited.stdout.strip())
            _fail(receipt["exit_code"] == 0, "BFD qualifier failed; failure evidence retained")
            build_receipt = _load_json(_safe_regular(bound["evidence"] / "RESULT.json", "BFD qualifier result"), "driver receipt")
            _validate_driver_result(bound["evidence"], bound["output"], build_receipt, r)
            _revalidate_inputs(bound, r)
            receipt["qualification_result_sha256"] = _sha256(bound["output"] / "RESULT.json")
            receipt["qualification_inventory"] = _closure_inventory(bound["output"], bound["output"], Path("/work/qualification-1"))
            receipt["status"] = "PASS"
        except BaseException as exc:
            receipt["error"] = str(exc)
        finally:
            if self.signals:
                self.signals.cleaning = True
            if attempted and client is not None:
                try:
                    receipt.update(_cleanup_owned_compile(client, bound["attempt"], receipt.get("container_id")))
                except BaseException as exc:
                    receipt["status"] = "FAIL"
                    receipt["cleanup_error"] = str(exc)
            else:
                # No create was attempted. Keep the lease for root reconciliation;
                # do not invent Docker/physical retirement that was never observed.
                receipt["no_container_create_attempted"] = True
            try:
                _revalidate_inputs(bound, r)
            except BaseException as exc:
                receipt["status"] = "FAIL"
                receipt["input_revalidation_error"] = str(exc)
            if self.signals and self.signals.requested is not None:
                receipt["status"] = "FAIL"
                receipt["interrupted_signal"] = self.signals.requested
            receipt.update(driver_evidence_root=str(bound["evidence"]), output_root=str(bound["output"]),
                           owner_evidence_root=str(bound["owner_evidence"]), attempt_root=str(bound["attempt"]),
                           compile_lease_path=str(lease.path), finished_at=time.time())
            # A compiler result never releases ownership or claims P12/native clearance.
            _exclusive_json(bound["owner_evidence"] / OWNER_RECEIPT_NAME, receipt)
        return receipt


def main(argv=None):
    parser = argparse.ArgumentParser(description="Functional McKernel OS/apps and Rust/assembly migration only; no security testing. Fixed M15 BFD compile-only owner.")
    parser.add_argument("action", choices=("run", "release-accepted-lease"))
    parser.add_argument("request", type=Path)
    args = parser.parse_args(argv)
    request = json.loads(args.request.read_text())
    if args.action == "release-accepted-lease":
        result = release_accepted_compile_lease(request)
        print(json.dumps(result, sort_keys=True))
        return 0
    with Signals() as signals:
        result = ImageOwner(request, signals=signals).run()
    print(json.dumps(result, sort_keys=True))
    return 0 if result.get("status") == "PASS" and result.get("retired") is True else 1




if __name__ == "__main__":
    raise SystemExit(main())
