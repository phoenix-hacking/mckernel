#!/usr/bin/env python3
"""Reviewed owner for one isolated current-source McKernel image build.

This module is an admission/transport boundary around the offline image
driver.  It does not relocate sources, install software, or perform a guest
operation.  A root-released invocation creates exactly one private compile-only, read-only-root
container on CPU6/1CPU/4GiB under its separate HOST lease; tests inject a fake Docker
transport and never contact Docker.
"""
from __future__ import annotations

import argparse
import base64
import errno
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


REQUEST_SCHEMA = "mckernel.native-exact-mckernel-image-container-request.v1"
RECEIPT_SCHEMA = "mckernel.native-exact-mckernel-image-container-receipt.v1"
OWNER_RECEIPT_NAME = "owner-receipt.json"
EXPECTED_DRIVER_SHA256 = '7d30085edda4d1272f923b19e8632e9ab8b259874623974c2da53dbe4c3c5be0'
EXPECTED_PROVENANCE_SHA256 = '453dd998e4ef1e2ed21b0818771d97197d77f98c90ca8c6c67cc8ab019063044'
EXPECTED_HOST_OWNER_SHA256 = '8aeb5f85d0fe3d8722cf88b5dccb47ba22c2c97283f8812a77f9e29cf895146c'
EXPECTED_HEAVY_ENTRY_CONTRACT_SHA256 = "c252ee341eb61752704f8b818503c0a5dc97400845494707ca3110f5f23df6d1"
# The image owner advances with the image-candidate namespace.  Keep consumed
# exclusions explicit: accepting one of these would allow a request to race a
# retired build candidate.  Tests may replace COMMON_EXCLUSION with a private
# fixture, so the rejection list remains separate from the active value.
COMMON_EXCLUSION = '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-4/dual-container/reuse/compile-only-candidate/operation-1/compile-lease.json'
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
    "Memory": 4 * 2**30, "MemorySwap": 4 * 2**30,
    "PidsLimit": 128, "NetworkMode": "none",
}
RESOURCE_ARGS = ("--cpus=1", "--cpuset-cpus=6", "--memory=4g",
                 "--memory-swap=4g", "--pids-limit=128")
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


_HOST_OWNER_PATH = Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261026-1/WEEKLY-ONLY-20261029-1/DISPATCHER-SOL-MAX-20261030-1/sdk21-nonheld13-owner-source-1/sdk13_compile_host_helper.v7.py')
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

def _validate_request(request):
    _validate_compile_domain(request)
    _fail(isinstance(request, dict) and request.get("schema") == REQUEST_SCHEMA,
          "request schema")
    _fail(isinstance(request.get("native_fork_owned_transaction", False), bool),
          "owned native fork opt-in must be Boolean")
    candidate = request.get("candidate_sha")
    ihk = request.get("ihk_sha")
    _fail(isinstance(candidate, str) and re.fullmatch(r"[0-9a-f]{40}", candidate),
          "candidate identity")
    _fail(isinstance(ihk, str) and re.fullmatch(r"[0-9a-f]{40}", ihk), "IHK identity")
    _fail(isinstance(request.get("image_id"), str) and
          re.fullmatch(r"sha256:[0-9a-f]{64}", request["image_id"]), "image identity")
    _fail(1 <= request.get("jobs", 0) <= 4 and isinstance(request.get("jobs"), int),
          "jobs exceed reviewed bound")
    _fail(1 <= request.get("timeout", 0) <= MAX_TIMEOUT and isinstance(request.get("timeout"), int),
          "timeout exceeds reviewed bound")
    _fail(request.get("launcher_aggregate_memory_gib") == LAUNCHER_AGGREGATE_GIB,
          "launcher aggregate must be exactly 16.2158 GiB")
    memory_effect = request.get("memory_backed_bytes")
    _fail(isinstance(memory_effect, int) and not isinstance(memory_effect, bool) and memory_effect == 0,
          "memory-backed source bytes are not zero")
    aggregate = request.get("aggregate_memory_required")
    _fail(aggregate == LIMITS["Memory"] and aggregate + memory_effect <= LAUNCHER_AGGREGATE_BYTES,
          "aggregate memory admission failed")
    disk_admission = request.get("disk_admission")
    _fail(isinstance(disk_admission, dict), "disk admission manifest missing")
    _fail(disk_admission.get("host_free_floor") == 16 * 2**30 and
          disk_admission.get("scratch_free_floor") == 12 * 2**30,
          "disk admission floors differ")
    host_measure = _canonical(disk_admission.get("host_root", ""), "host measurement root", directory=True)
    scratch_measure = _canonical(disk_admission.get("scratch_root", ""), "scratch measurement root", directory=True)
    _fail(shutil.disk_usage(host_measure).free >= 16 * 2**30, "host disk floor failed")
    _fail(shutil.disk_usage(scratch_measure).free >= 12 * 2**30, "scratch disk floor failed")
    _fail(isinstance(disk_admission.get("host_device"), int) and
          os.stat(host_measure).st_dev == disk_admission["host_device"], "host device changed")
    _fail(isinstance(disk_admission.get("scratch_device"), int) and
          os.stat(scratch_measure).st_dev == disk_admission["scratch_device"], "scratch device changed")
    allocation_roots = request.get("memory_allocation_roots")
    _fail(isinstance(allocation_roots, list) and allocation_roots,
          "memory allocation roots missing")
    allocation_paths = [_canonical(item, "memory allocation root", directory=True)
                        for item in allocation_roots]
    source = _canonical(request.get("source_root", ""), "source root", directory=True)
    _fail(source in allocation_paths and len(set(allocation_paths)) == len(allocation_paths),
          "memory allocation roots do not bind source")
    owner_evidence = _canonical(request.get("owner_evidence_root", ""),
                                "owner evidence root", directory=True)
    _no_symlink_parents(owner_evidence, "owner evidence root")
    _fail(not any(owner_evidence.iterdir()), "owner evidence root must be fresh")
    work_root = _canonical(request.get("work_root", ""), "dedicated work root", directory=True)
    _fail(stat.S_IMODE(work_root.stat().st_mode) == 0o700,
          "dedicated work root must be mode 0700")
    attempt = _confined_path(request.get("attempt_root", ""), "attempt root")
    _fail(not attempt.exists() and attempt.parent == owner_evidence,
          "attempt root must be private and absent")
    receipt_path = _confined_path(owner_evidence / OWNER_RECEIPT_NAME, "owner receipt")
    _fail(not receipt_path.exists() and not receipt_path.is_symlink(),
          "owner receipt must be fresh")
    output = _confined_path(request.get("output_root", ""), "output root")
    evidence = _confined_path(request.get("evidence_root", ""), "evidence root")
    for path, label in ((output, "output root"), (evidence, "evidence root")):
        _fail(not path.exists() and not path.is_symlink(), label + " must be fresh")
        _fail(path.parent.exists() and path.parent.is_dir(), label + " parent missing")
    _fail(not any(work_root.iterdir()), "dedicated work root must be empty")
    _fail(output.parent == work_root and evidence.parent == work_root,
          "output/evidence must be direct children of dedicated work root")
    manifest = _regular(request.get("source_manifest", ""), "source manifest")
    toolchain = _regular(request.get("toolchain_manifest", ""), "toolchain manifest")
    driver = _regular(request.get("driver_path", ""), "offline driver")
    provenance = _regular(request.get("provenance_path", ""), "offline provenance")
    host_owner = _regular(request.get("host_owner_path", ""), "host owner")
    _fail(request.get("driver_sha256") == EXPECTED_DRIVER_SHA256, "offline driver release hash")
    _fail(_sha256(driver) == EXPECTED_DRIVER_SHA256, "offline driver bytes differ")
    _fail(isinstance(request.get("provenance_sha256"), str) and
          re.fullmatch(r"[0-9a-f]{64}", request["provenance_sha256"]),
          "offline provenance hash binding")
    _fail(_sha256(provenance) == request["provenance_sha256"],
          "offline provenance bytes differ")
    _fail(request["provenance_sha256"] == EXPECTED_PROVENANCE_SHA256,
          "offline provenance release hash")
    _fail(isinstance(request.get("host_owner_sha256"), str) and
          re.fullmatch(r"[0-9a-f]{64}", request["host_owner_sha256"]),
          "host owner hash binding")
    _fail(_sha256(host_owner) == request["host_owner_sha256"],
          "host owner bytes differ")
    _fail(request["host_owner_sha256"] == EXPECTED_HOST_OWNER_SHA256,
          "host owner release hash")
    for path, label, key in ((manifest, "source manifest", "source_manifest_sha256"),
                             (toolchain, "toolchain manifest", "toolchain_manifest_sha256")):
        _fail(isinstance(request.get(key), str) and re.fullmatch(r"[0-9a-f]{64}", request[key]),
              label + " hash binding")
        _fail(_sha256(path) == request[key], label + " hash drift")
    source_doc = _load_json(manifest, "source manifest")
    _fail(source_doc.get("candidate_sha") == candidate and source_doc.get("ihk_sha") == ihk,
          "source manifest identity differs")
    _fail(source_doc.get("schema") in ("mckernel.native-exact-mckernel-image-inputs.v1",
                                        "mckernel.native-exact-build-inputs.v1",
                                        "mckernel.native-fp-save-thin-inputs.v1",
                                        "mckernel.rust-fpu-sched-cutover-thin-inputs.v1",
                                        "mckernel.m14-combined-production-thin-inputs.v1"),
          "source manifest schema")
    if source_doc.get('schema') in ('mckernel.native-fp-save-thin-inputs.v1',
                                     'mckernel.rust-fpu-sched-cutover-thin-inputs.v1',
                                     'mckernel.m14-combined-production-thin-inputs.v1'):
        _fail(request.get('source_derivative_sha256') == source_doc.get('source_derivative_sha256') and
              request.get('materialization_sha256') == source_doc.get('materialization_sha256') and
              request.get('candidate_identity_scope') == 'base_git_commit_only',
              'explicit derivative request identity differs')
    else:
        _fail(request.get('source_derivative_sha256') is None and
              request.get('materialization_sha256') is None and
              request.get('candidate_identity_scope') is None,
              'thin identity fields on original full-tree request')
    _fail(isinstance(request.get("source_identity"), dict), "source identity missing")
    _check_identity(source, request["source_identity"], "source root")
    disk = request.get("disk_identity")
    _fail(isinstance(disk, dict) and disk.get("path") == str(source), "disk identity binding")
    _check_identity(source, disk, "disk candidate")
    toolchain_doc = _load_json(toolchain, "toolchain manifest")
    toolchain_schema = toolchain_doc.get("schema")
    _fail(toolchain_schema in ("mckernel.native-exact-mckernel-image-toolchain.v1",
                               "mckernel.native-exact-mckernel-image-toolchain.v2"),
          "toolchain manifest schema")
    if toolchain_schema.endswith(".v2"):
        mounts_by_target = _v2_mount_roots(request, toolchain_doc)
        roots = list(mounts_by_target.values())
        image_tools, mounted_tools = _validate_v2_image_tools(request, toolchain_doc)
        host_git = _v2_host_git(request)
        tools = {**image_tools, **mounted_tools}
    else:
        mounts_by_target = None
        host_git = None
        roots = _toolchain_roots(request)
        tools = toolchain_doc.get("tools")
        _fail(isinstance(tools, dict) and all(name in tools for name in REQUIRED_TOOLS),
              "toolchain tools incomplete")
    git_descriptor = host_git if toolchain_schema.endswith(".v2") else tools["git"]
    _admit_request_gitlink(request, source_doc, source, manifest, candidate, ihk,
                           allocation_paths, git_descriptor)
    if toolchain_schema.endswith(".v2"):
        kernel_root = mounts_by_target["/out"]
        kernel_root, kernel_dir = _validate_kernel_binding(toolchain_doc, kernel_root)
        # v2's kernel is deliberately not a second bind: it is part of the
        # read-only host_root -> /out translation.
    else:
        _fail(isinstance(toolchain_doc.get("kernel_dir"), str), "kernel directory binding")
        kernel_root = None
        kernel_dir = _canonical(toolchain_doc["kernel_dir"], "kernel directory", directory=True)
    for name in REQUIRED_TOOLS:
        descriptor = tools[name]
        _fail(isinstance(descriptor, dict) and isinstance(descriptor.get("path"), str) and
              isinstance(descriptor.get("sha256"), str) and
              re.fullmatch(r"[0-9a-f]{64}", descriptor["sha256"]) and
              isinstance(descriptor.get("version"), str) and descriptor["version"],
              "toolchain tool identity incomplete: " + name)
        if toolchain_schema.endswith(".v2") and name in mounted_tools:
            tool_path = _v2_host_path(descriptor["path"], mounts_by_target, "tool " + name)
            _fail(_sha256(tool_path) == descriptor["sha256"], "tool hash drift: " + name)
        elif not (toolchain_schema.endswith(".v2") and name in image_tools):
            tool_path = _regular(descriptor["path"], "tool " + name)
            _fail(_sha256(tool_path) == descriptor["sha256"], "tool hash drift: " + name)
    if toolchain_schema.endswith(".v2"):
        _fail(toolchain_doc.get("kernel_dir") in (None, "/out/build"),
              "container kernel directory binding")
    else:
        _fail(isinstance(toolchain_doc.get("kernel_inventory"), dict) and
              _tree_inventory(kernel_dir) == toolchain_doc["kernel_inventory"],
              "kernel inventory differs")
    if not toolchain_schema.endswith(".v2"):
        _fail(toolchain_doc.get("toolchain_roots") == request.get("toolchain_roots"),
              "toolchain root manifest differs")
        _fail(toolchain_doc.get("path_dirs") == request.get("path_dirs"),
              "PATH manifest differs")
    _fail(isinstance(toolchain_doc.get("linux_probe"), dict) and
          toolchain_doc["linux_probe"].get("kernel_dir") ==
          ("/out/build" if toolchain_schema.endswith(".v2") else str(kernel_dir)),
          "Linux probe manifest differs")
    _fail(isinstance(toolchain_doc.get("environment"), dict) and not toolchain_doc["environment"],
          "toolchain environment is not sealed")
    _fail(isinstance(tools.get("rustc"), dict), "toolchain Rust identity")
    rust_version = tools["rustc"].get("version", "")
    _fail(rust_version == EXPECTED_V2_RUSTC_VERSION,
          "toolchain Rust version is not the supported exact nightly")
    source_tools = dict(tools)
    if toolchain_schema.endswith(".v2"):
        # Authentication of the source checkout is a host operation.  Do not
        # read image /usr paths here: the container's receipt is their only
        # host-side authority.  Git alone is needed by source admission.
        source_tools = {"git": host_git}
    _validate_authenticated_source(source, source_doc, candidate, ihk, source_tools, provenance)
    backup_raw = request.get("backup_root", request.get("source_backup_root"))
    backup = _canonical(backup_raw, "source backup", directory=True)
    _check_identity(backup, request.get("backup_identity"), "source backup")
    _fail(isinstance(request.get("backup_inventory"), dict) and request["backup_inventory"],
          "source backup inventory missing")
    _fail(_tree_inventory(backup) == request["backup_inventory"],
          "source backup inventory differs")
    path_dirs = toolchain_doc.get("path_dirs") if toolchain_schema.endswith(".v2") else request.get("path_dirs")
    _fail(isinstance(path_dirs, list) and path_dirs, "path_dirs manifest missing")
    image_path_dirs = ({str(Path(row["path"]).parent) for row in image_tools.values()}
                       if toolchain_schema.endswith(".v2") else set())
    for row in path_dirs:
        _fail(isinstance(row, str), "path_dirs row")
        if toolchain_schema.endswith(".v2"):
            if row.startswith(("/out/", "/nightly/")):
                path = _v2_host_path(row, mounts_by_target, "path_dirs entry", directory=True)
                _fail(path.is_dir(), "PATH directory escapes toolchain roots")
            else:
                _fail(row in image_path_dirs, "image PATH directory differs")
        else:
            path = _canonical(row, "path_dirs entry", directory=True)
            _fail(path.is_dir() and any(path == other or other in path.parents for other in roots),
                  "PATH directory escapes toolchain roots")
    nightly = request.get("nightly")
    _fail(isinstance(nightly, dict) and isinstance(nightly.get("rustc_version"), str) and
          nightly["rustc_version"] == EXPECTED_V2_RUSTC_VERSION and
          nightly["rustc_version"] == rust_version, "nightly manifest")
    expected_mounts = {"source": "/src", "manifest": "/inputs.json",
                                 "toolchain": "/toolchain.json", "driver": "/driver.py",
                                 "provenance": "/native_rust_exact_build_offline.py",
                                 "work": "/work"}
    if request.get("gitlink_manifest") is not None:
        expected_mounts.update({"gitlink_manifest": "/libdwarf-inputs.json",
                                "gitlink": "/src/executer/user/lib/libdwarf/libdwarf"})
    _fail(request.get("mounts") == expected_mounts, "mount manifest differs")
    common = request.get("common_exclusion_path")
    _fail(common == COMMON_EXCLUSION and common not in RETIRED_COMMON_EXCLUSIONS,
          "common exclusion path differs or is retired")
    lease = _regular(request.get("lease_path", ""), "lease path") if Path(request.get("lease_path", "")).exists() else Path(request.get("lease_path", ""))
    _no_symlink_parents(lease, "lease path")
    disjoint_paths = (source, manifest, toolchain, driver, provenance, host_owner,
                      owner_evidence, work_root, *roots, backup)
    gitlink_root = None
    if request.get("gitlink_manifest") is not None:
        gitlink_root = _canonical(request.get("gitlink_root", ""), "libdwarf checkout", directory=True)
        _disjoint((source, gitlink_root))
        disjoint_paths += (gitlink_root, _regular(request["gitlink_manifest"], "gitlink manifest"))
    if not toolchain_schema.endswith(".v2"):
        disjoint_paths += (kernel_dir,)
    _disjoint(disjoint_paths)
    _fail(work_root != owner_evidence and work_root not in owner_evidence.parents and
          owner_evidence not in work_root.parents, "work/evidence roots overlap")
    try:
        authenticated_host = _load_reviewed_host_owner(
            host_owner, request["host_owner_sha256"], provenance,
            request["provenance_sha256"])
    except (OSError, RuntimeError, SyntaxError) as exc:
        raise OwnerError("authenticated host owner import failed: " + str(exc)) from exc
    try:
        measurement = authenticated_host.measure(
            host_measure, scratch_measure, 16 * 2**30, 12 * 2**30,
            source_root=source, output_root=work_root,
            memory_allocation_roots=allocation_paths)
    except (OSError, RuntimeError, ValueError) as exc:
        raise OwnerError("resource/allocation measurement failed: " + str(exc)) from exc
    _fail(measurement.get("memory_allocation_memory_backed_bytes") == memory_effect,
          "measured memory-backed allocation differs")
    _fail(measurement.get("aggregate_memory_required") == aggregate,
          "measured aggregate memory differs")
    return {"source": source, "manifest": manifest, "toolchain": toolchain,
            "driver": driver, "provenance": provenance, "output": output, "evidence": evidence,
            "owner_evidence": owner_evidence, "attempt": attempt,
            "work": work_root, "backup": backup, "measurement": measurement,
            "host_owner": authenticated_host,
            "host_owner_path": host_owner, "roots": roots, "kernel": kernel_dir,
            "kernel_root": kernel_root, "toolchain_schema": toolchain_schema,
            "mounts_by_target": mounts_by_target, "host_git": host_git,
            "allocation_roots": allocation_paths,
            "gitlink_root": gitlink_root,
            "gitlink_manifest": _regular(request["gitlink_manifest"], "gitlink manifest")
            if request.get("gitlink_manifest") is not None else None,
            "path_dirs": [_v2_host_path(row, mounts_by_target, "PATH directory", directory=True)
                          if row.startswith(("/out/", "/nightly/")) else Path(row)
                          for row in path_dirs] if toolchain_schema.endswith(".v2") else
            [_canonical(row, "PATH directory", directory=True) for row in path_dirs],
            "lease": lease}




def _check_profile(info, image, nonce, mounts=None, command=None, user=None,
                   host_owner=None):
    (host_owner or _HOST_OWNER).check_profile(info, image, nonce)
    _fail(info.get("Config", {}).get("Labels", {}).get("mckernel.operation") == COMPILE_PROFILE["operation"], "compile operation label mismatch")
    config = info.get("Config", {})
    if command is not None:
        _fail(config.get("Entrypoint") == ["/usr/bin/python3"] and config.get("Cmd") == command,
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
    evidence = _safe_directory(evidence, "driver evidence root")
    output = _safe_directory(output, "driver output root")
    _fail(result.get("status") == "PASS", "driver receipt is not PASS")
    _fail(result.get("native_fork_owned_transaction", False) is
          request.get("native_fork_owned_transaction", False), "owned fork opt-in receipt differs")
    _fail(result.get("candidate_sha") == request["candidate_sha"] and
          result.get("ihk_sha") == request["ihk_sha"], "driver receipt identity differs")
    _fail(result.get("source_manifest_sha256") == request["source_manifest_sha256"] and
          result.get("toolchain_manifest_sha256") == request["toolchain_manifest_sha256"],
          "driver receipt provenance differs")
    if request.get("gitlink_manifest") is not None:
        _fail(result.get("gitlink_manifest_sha256") == request["gitlink_manifest_sha256"],
              "driver gitlink provenance differs")
    if request.get('source_derivative_sha256') is not None:
        _fail(result.get('source_derivative_sha256') == request['source_derivative_sha256'] and
              result.get('materialization_sha256') == request['materialization_sha256'] and
              result.get('candidate_identity_scope') == 'base_git_commit_only',
              'driver explicit derivative identity differs')
    panic_proof=result.get('production_rust_core_panic_reference_proof')
    _fail(isinstance(panic_proof,dict) and panic_proof.get('status')=='PASS_PRODUCTION_RUST_NO_TARGETED_CORE_PANIC_REFS'
          and panic_proof.get('forbidden')==[] and panic_proof.get('clone_thread_undefined')==1,
          'actual production Rust core-panic reference proof missing')
    _fail(panic_proof['object']['sha256']==result['artifacts']['mckernel_rust.o']['sha256'],
          'actual final Rust object/core-panic proof differs')
    inventory = result.get("inventory")
    _fail(isinstance(inventory, dict), "driver evidence inventory missing")
    observed_inventory = {}
    for item in sorted(evidence.rglob("*")):
        st = item.lstat()
        _fail(not stat.S_ISLNK(st.st_mode), "driver evidence contains symlink")
        _fail(stat.S_ISREG(st.st_mode) or stat.S_ISDIR(st.st_mode),
              "driver evidence contains special file")
        if item.is_file() and item.relative_to(evidence) != Path("receipt.json"):
            relative = item.relative_to(evidence)
            _fail(not relative.is_absolute() and ".." not in relative.parts,
                  "driver evidence inventory path escapes root")
            observed_inventory[str(relative)] = {
                "size": item.stat().st_size, "sha256": _sha256(item)}
    for relative, metadata in inventory.items():
        relative_path = Path(relative)
        _fail(not relative_path.is_absolute() and ".." not in relative_path.parts and
              str(relative_path) == relative, "driver evidence inventory path is not canonical")
        path = _safe_regular(evidence / relative_path, "driver evidence member")
        _fail(isinstance(metadata, dict) and metadata.get("size") == path.stat().st_size and
              metadata.get("sha256") == _sha256(path), "driver evidence inventory drift")
    _fail(set(observed_inventory) == set(inventory),
          "driver evidence inventory is incomplete or has unexpected members")
    expected = {"mckernel.img", "mckernel.img.map", "CMakeCache.txt", "compile_commands.json",
                "mckernel_rust.o", "build.make"}
    if request.get("native_fork_owned_transaction", False):
        expected.update({"mcexec", "mcexec_helpers.o", "mcexec-rust-build.make"})
    copied = result.get("evidence_artifacts")
    _fail(isinstance(copied, dict) and set(copied) >= expected,
          "driver artifact inventory incomplete")
    for name in expected:
        relative = name
        path = evidence / "artifacts" / relative
        row = copied[name]
        _safe_regular(path, "driver evidence artifact")
        _fail(
              str(row.get("path", "")).replace("\\", "/").endswith("/artifacts/" + relative),
              "driver artifact path differs: " + name)
        _fail(row.get("size") == path.stat().st_size and row.get("sha256") == _sha256(path),
              "driver artifact hash differs: " + name)
        _fail(row.get("path") == "/work/evidence/artifacts/" + name,
              "driver artifact path is not canonical: " + name)
    artifacts = result.get("artifacts")
    _fail(isinstance(artifacts, dict) and set(artifacts) >= expected,
          "driver output artifact inventory incomplete")
    output_paths = {"mckernel.img": output / "build/kernel/mckernel.img",
                    "mckernel.img.map": output / "build/kernel/mckernel.img.map",
                    "CMakeCache.txt": output / "build/CMakeCache.txt",
                    "compile_commands.json": output / "build/compile_commands.json",
                    "mckernel_rust.o": output / "build/kernel/rust/mckernel_rust.o",
                    "build.make": output / "build/kernel/CMakeFiles/mckernel_rust_obj.dir/build.make"}
    if request.get("native_fork_owned_transaction", False):
        output_paths.update({
            "mcexec": output / "build/executer/user/mcexec",
            "mcexec_helpers.o": output / "build/executer/user/rust/mcexec_helpers.o",
            "mcexec-rust-build.make": output / "build/executer/user/CMakeFiles/mcexec_rust_helpers.dir/build.make",
        })
    for name, path in output_paths.items():
        row = artifacts[name]
        output_rel = path.relative_to(output)
        _fail(row.get("path") == "/work/output/" + output_rel.as_posix(),
              "driver output artifact path is not canonical: " + name)
        _safe_regular(path, "driver output artifact")
        _fail(row.get("size") == path.stat().st_size and
              row.get("sha256") == _sha256(path), "driver output hash differs: " + name)


def _revalidate_inputs(bound, request):
    _check_identity(bound["source"], request["source_identity"], "source root")
    _check_identity(bound["backup"], request["backup_identity"], "source backup")
    _fail(_tree_inventory(bound["backup"]) == request["backup_inventory"],
          "source backup inventory changed")
    _fail(_sha256(bound["manifest"]) == request["source_manifest_sha256"],
          "source manifest changed")
    _fail(_sha256(bound["toolchain"]) == request["toolchain_manifest_sha256"],
          "toolchain manifest changed")
    if bound.get("gitlink_manifest") is not None:
        _fail(_sha256(bound["gitlink_manifest"]) == request["gitlink_manifest_sha256"],
              "gitlink manifest changed")
    _fail(_sha256(bound["driver"]) == EXPECTED_DRIVER_SHA256 and
          _sha256(bound["provenance"]) == EXPECTED_PROVENANCE_SHA256,
          "authenticated helper bytes changed")
    _fail(_sha256(bound["host_owner_path"]) == request["host_owner_sha256"],
          "authenticated host owner changed")
    source_doc = _load_json(bound["manifest"], "source manifest")
    toolchain_doc = _load_json(bound["toolchain"], "toolchain manifest")
    if bound.get("toolchain_schema", "").endswith(".v2"):
        _v2_mount_roots(request, toolchain_doc)
        host_root, host_kernel = _validate_kernel_binding(toolchain_doc, bound["kernel_root"])
        _fail(host_root == bound["kernel_root"] and host_kernel == bound["kernel"],
              "kernel binding changed")
        _validate_v2_image_tools(request, toolchain_doc)
    if bound.get("toolchain_schema", "").endswith(".v2"):
        _validate_v2_image_tools(request, toolchain_doc)
        source_tools = {"git": _v2_host_git(request)}
    else:
        source_tools = toolchain_doc["tools"]
    rust_descriptor = (toolchain_doc.get("mounted_tools", {}).get("rustc", {})
                       if bound.get("toolchain_schema", "").endswith(".v2")
                       else toolchain_doc.get("tools", {}).get("rustc", {}))
    rust_version = rust_descriptor.get("version", "")
    _fail(rust_version == EXPECTED_V2_RUSTC_VERSION and
          request.get("nightly", {}).get("rustc_version") == rust_version,
          "toolchain Rust version drifted")
    _validate_authenticated_source(bound["source"], source_doc, request["candidate_sha"],
                                   request["ihk_sha"], source_tools, bound["provenance"])
    if bound.get("gitlink_manifest") is not None:
        _validate_gitlink_manifest(_load_json(bound["gitlink_manifest"], "gitlink manifest"),
                                   bound["gitlink_manifest"], bound["gitlink_root"],
                                   bound["manifest"], request["candidate_sha"],
                                   request["ihk_sha"], source_tools["git"])


COMPILE_PROFILE = {'activation': 'COMPILE_LINK_ONLY_NO_GUEST_OR_KERNEL_ACTIVATION', 'admission_max_age_ns': 120000000000, 'container_name': 'mckernel-m14-compile-95f3c1f79ec040ddbb7065ff9f5ca536', 'driver_sha256': '7d30085edda4d1272f923b19e8632e9ab8b259874623974c2da53dbe4c3c5be0', 'host_helper_sha256': '8ffc9a09e2f2e9e9c9cc09af559d707bf6c4b989fc4f9d3ad51fe88a8e5b6083', 'image_id': 'sha256:41778f1f22fd68897c1209e225a9807a197ed47bf0edd17835821bb5986e50b5', 'jobs': 1, 'lease_path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-4/dual-container/reuse/compile-only-candidate/operation-1/compile-lease.json', 'limits': {'CpusetCpus': '6', 'Memory': 4294967296, 'MemorySwap': 4294967296, 'NanoCpus': 1000000000, 'NetworkMode': 'none', 'PidsLimit': 128}, 'materialization_sha256': '3c0c7e48058afda716d622056cc555b027d27177d5019499cab992f74899dc7f', 'minimum_MemAvailable': 25769803776, 'namespace': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-4/dual-container/reuse/compile-only-candidate/operation-1', 'operation': 'M14_CANDIDATE14_HOST_COMPILE_LINK_ONLY_V1', 'owner_nonce': '95f3c1f79ec040ddbb7065ff9f5ca536', 'provenance_sha256': '453dd998e4ef1e2ed21b0818771d97197d77f98c90ca8c6c67cc8ab019063044', 'reserved_native_profile': {'CpusetCpus': '2-5', 'Memory': 12884901888, 'MemorySwap': 12884901888, 'NanoCpus': 4000000000, 'NetworkMode': 'none', 'PidsLimit': 512}, 'schema': 'mckernel.m14-candidate14-compile-link-profile.v1', 'sole_rw_mount_target': '/work', 'source_derivative_sha256': 'caa690b06ff078828ecab2ae9d70adfd98072073be2acae7955efd8a48bce3ba', 'source_manifest_sha256': 'bf3096e00f9f176c308604332ac276abc30c2576b2c7c3052c837ccf7e640b47', 'source_root': '/home/holden/mckernel-work/host-preparation/compute-idle-rust-cutover-20261023-1/production-combined-14/default-image-preparation-1/source-materialization-attempt-1/materialized-source', 'toolchain_manifest_sha256': 'a68e02b3b66b8bfbae96bf742dc8702b6e81dd97b92189b87437c3d08fccdf72'}
COMPILE_PROFILE_PATH = Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-4/dual-container/reuse/compile-only-candidate/COMPILE-PROFILE.json')
COMPILE_PROFILE_SHA256 = '9b78e4ec49f163a333a3fd7e9cf0dc6b05dbdc097a0b785c20cf741aaa6e23fa'
PRIVATE_ROOT = Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-4/dual-container/reuse/compile-only-candidate')


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
    _fail(request.get("native_fork_owned_transaction") is True,
          "candidate14 build configuration selection changed")
    for key in ("source_root", "source_manifest_sha256", "source_derivative_sha256",
                "materialization_sha256", "driver_sha256", "provenance_sha256",
                "toolchain_manifest_sha256", "image_id"):
        _fail(request.get(key) == COMPILE_PROFILE[key], "fixed candidate14 input differs: " + key)
    root = Path(COMPILE_PROFILE["namespace"])
    expected = {"work_root": root / "owner-work", "output_root": root / "owner-work/output",
                "evidence_root": root / "owner-work/evidence", "owner_evidence_root": root / "owner-evidence",
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
    _fail(release.get("status") == "RELEASED_FOR_ONE_COMPILE_ONLY_CANDIDATE14" and
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
    _fail(facts.get("schema") == "mckernel.m14-candidate14-dual-container-admission.v1" and
          facts.get("operation") == COMPILE_PROFILE["operation"] and
          facts.get("request_core_sha256") == _request_core_hash(request) and
          facts.get("profile_sha256") == COMPILE_PROFILE_SHA256,
          "root live admission bindings differ")
    _fail(facts.get("cpu6_consumer_joined") is True and facts.get("P12_sole_native_heavy") is True,
          "CPU6/native lane prerequisites missing")
    _fail(facts.get("compile_limits") == LIMITS and
          facts.get("P12_limits") == COMPILE_PROFILE["reserved_native_profile"],
          "concurrent resource reservation differs")
    _fail(facts.get("capacity_verdict") == "PASS_DUAL_CONTAINER_COMPILE_CPU6_4G" and
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
        self.record = {"schema": "mckernel.m14-candidate14-compile-lease.v1", "operation": COMPILE_PROFILE["operation"],
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

    def release_accepted(self, acceptance, unlink_gate=None):
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
                _fail(callable(unlink_gate), 'SDK13 lease unlink gate missing')
                unlink_boundary=unlink_gate()
                os.unlink(self.path.name, dir_fd=parent_fd)
                os.fsync(parent_fd)
                return unlink_boundary
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
    mounts = [(bound["source"], "/src", True), (bound["manifest"], "/inputs.json", True),
              (bound["gitlink_manifest"], "/libdwarf-inputs.json", True),
              (bound["gitlink_root"], "/src/executer/user/lib/libdwarf/libdwarf", True),
              (bound["toolchain"], "/toolchain.json", True), (bound["driver"], "/driver.py", True),
              (bound["provenance"], "/native_rust_exact_build_offline.py", True),
              (bound["work"], "/work", False)]
    _fail(bound["toolchain_schema"].endswith(".v2") and bound["gitlink_root"] is not None,
          "fixed candidate14 v2/gitlink closure required")
    mounts += [(root, target, True) for target, root in bound["mounts_by_target"].items()]
    _fail([(str(src), target) for src, target, ro in mounts if not ro] ==
          [(str(Path(COMPILE_PROFILE["namespace"]) / "owner-work"), "/work")], "sole HOST RW compile mount differs")
    _fail(len({target for _, target, _ in mounts}) == len(mounts), "duplicate compile mount target")
    return mounts


def _compile_command(bound, request):
    return ["/driver.py", "--source-root", "/src", "--candidate-sha", request["candidate_sha"],
            "--ihk-sha", request["ihk_sha"], "--manifest", "/inputs.json", "--toolchain", "/toolchain.json",
            "--output", "/work/output", "--evidence", "/work/evidence", "--jobs", "1",
            "--timeout", str(request["timeout"]), "--gitlink-manifest", "/libdwarf-inputs.json",
            "--native-fork-owned-transaction"]


def _compile_create_args(bound, request):
    mounts = _compile_mounts(bound)
    command = _compile_command(bound, request)
    args = ["create", "--name", COMPILE_PROFILE["container_name"], "--label", "mckernel.owner=" + COMPILE_PROFILE["owner_nonce"],
            "--label", "mckernel.operation=" + COMPILE_PROFILE["operation"], "--init", "--network=none", "--ipc=private",
            *RESOURCE_ARGS, "--user", "1000:1000", "--cap-drop=ALL", "--security-opt=no-new-privileges", "--read-only",
            "--tmpfs", "/tmp:rw,nodev,nosuid,size=256m"]
    for source, target, readonly in mounts:
        args += ["--mount", "type=bind,src=" + str(source) + ",dst=" + target + (",readonly" if readonly else "")]
    args += ["--entrypoint", "/usr/bin/python3", request["image_id"], *command]
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
        receipt = {"schema": "mckernel.m14-candidate14-compile-owner-receipt.v1", "status": "FAIL",
                   "scope": "Functional McKernel OS/apps and Rust/assembly migration only; no security testing.",
                   "operation": COMPILE_PROFILE["operation"], "profile_sha256": COMPILE_PROFILE_SHA256,
                   "request_core_sha256": _request_core_hash(r), "candidate_sha": r["candidate_sha"], "ihk_sha": r["ihk_sha"],
                   "container_name": COMPILE_PROFILE["container_name"], "owner_nonce": COMPILE_PROFILE["owner_nonce"],
                   "container_id": None, "retired": False, "container_absence_confirmed": False,
                   "all_docker_clients_joined": False, "cleanup_separately_required": True,
                   "lease_retained_for_root_acceptance": True, "compile_lease": lease.record,
                   "source_derivative_sha256": r["source_derivative_sha256"], "materialization_sha256": r["materialization_sha256"],
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
            _fail(receipt["exit_code"] == 0, "offline candidate14 image driver failed")
            build_receipt = _load_json(_safe_regular(bound["evidence"] / "receipt.json", "driver receipt"), "driver receipt")
            _validate_driver_result(bound["evidence"], bound["output"], build_receipt, r)
            _revalidate_inputs(bound, r)
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


# SDK13 successor admission source.  The candidate14 lifecycle remains above
# byte-for-byte for review and reuse; no SDK13 launch is enabled until its
# profile/driver/mount and output validation are wired and independently reviewed.
SDK13_PROFILE_SHA = "e6a8462b10b409e86a7192d34328de33307cccd5c8e53d75b6312c85042c1ec3"
SDK13_RETIREMENT_SHA = "bc2df78168d34ef7c6b720766a03391668775d8e0847bb1130ff404e7958248d"
SDK13_RETIREMENT_ACCEPTANCE_SHA = "69216fdba1acbe6a1cde3aa996534ed863deb57a5fd0bf64a05242d68bc9b894"
SDK13_V3_REVIEW_SHA = "d37004eb0835315d3458fcbd4b5f8a677fad0fef2d71905556bb48b24f2d2bbd"
SDK13_REQUIRED_FACTS = ("native_known_and_unknown_custody", "native_reserved_resources",
    "v2_unknown_reserved_resources", "pure_outstanding_reserved_resources",
    "daemon_socket_identity_and_continuity", "daemon_native_rw_separation",
    "cpu6_positive_retirement_and_exclusive_grant", "root_controller_service_weekly_clocks",
    "sdk_image_and_toolchain_identity", "sdk_source_config_header_object_closure",
    "readonly_mounts_and_rw_output_nonintersection", "fresh_output_and_owner_ancestry",
    "aggregate_cpu_memory_disk_headroom", "nonce_uniqueness",
    "independent_successor_source_execution_review")

def _validate_sdk13_facts(facts, now_boot_ns, boot_id):
    _fail(isinstance(facts, dict), "SDK13 root admission missing")
    _fail(facts.get("status") == "SDK13_COMPILE_ONLY_ADMISSION" and
          facts.get("profile_sha256") == SDK13_PROFILE_SHA, "SDK13 admission identity mismatch")
    _fail(facts.get("retirement_result_sha256") == SDK13_RETIREMENT_SHA and
          facts.get("retirement_acceptance_sha256") == SDK13_RETIREMENT_ACCEPTANCE_SHA and
          facts.get("v3_observation_review_sha256") == SDK13_V3_REVIEW_SHA, "SDK13 retirement evidence mismatch")
    _fail(facts.get("boot_id") == boot_id and type(facts.get("observed_boottime_ns")) is int and
          0 <= now_boot_ns - facts["observed_boottime_ns"] <= 120000000000, "SDK13 facts expired or wrong boot")
    _fail(facts.get("unknown_custody_retained") is True and
          facts.get("historical_no_unlisted") is None and facts.get("current_free") is None,
          "SDK13 unknowns cannot be erased or asserted")
    for name in SDK13_REQUIRED_FACTS:
        fact = facts.get("facts", {}).get(name) if isinstance(facts.get("facts"), dict) else None
        _fail(isinstance(fact, dict) and fact.get("verdict") == "PASS" and
              isinstance(fact.get("evidence_sha256"), str) and
              re.fullmatch(r"[0-9a-f]{64}", fact["evidence_sha256"]) is not None,
              "SDK13 required reviewed fact missing: " + name)
    limits = facts.get("reservations")
    _fail(isinstance(limits, dict) and limits.get("native_memory_bytes") == 12 * 2**30 and
          limits.get("native_cpus") == "2-5" and limits.get("native_memory_swap_bytes") == 12 * 2**30 and
          limits.get("native_pids") == 512 and limits.get("v2_unknown_memory_bytes") == 2 * 2**30 and
          limits.get("v2_unknown_cpu") == "7" and limits.get("pure_memory_bytes") == 2**29 and limits.get("pure_cpu") == "0" and
          limits.get("compile_memory_bytes") == 4 * 2**30 and limits.get("compile_memory_swap_bytes") == 4 * 2**30 and
          limits.get("compile_pids") == 128 and limits.get("compile_cpu") == "6" and
          limits.get("daemon_parent_memory_bytes") == 2**29 and
          limits.get("daemon_reader_memory_bytes") == 2**29 and
          limits.get("daemon_reader_cpu") == "7" and limits.get("daemon_reader_compiler_concurrent") is False and
          limits.get("mutex") == "27:4" and limits.get("scratch") == "21",
          "SDK13 fixed reservations differ")
    _fail(type(facts.get("aggregate_memory_bytes")) is int and
          (12 + 2 + 4 + 1) * 2**30 + 2**29 <= facts["aggregate_memory_bytes"] <= int(Decimal("22.3811") * 2**30) and
          type(facts.get("aggregate_cpu_shares")) is int and facts["aggregate_cpu_shares"] == 7 and
          type(facts.get("MemAvailable")) is int and facts["MemAvailable"] >= 24 * 2**30 and
          type(facts.get("host_free_bytes")) is int and facts["host_free_bytes"] >= 16 * 2**30 and
          type(facts.get("scratch_free_bytes")) is int and facts["scratch_free_bytes"] >= 12 * 2**30,
          "SDK13 aggregate capacity insufficient or unknown")
    return facts

# SDK13 owner branch: the reviewed candidate14 owner and lifecycle functions are
# retained above. Root must bind exact current facts and review these adaptations.
SDK13_DIR = Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261026-1/WEEKLY-ONLY-20261029-1/DISPATCHER-SOL-MAX-20261030-1/sdk21-nonheld13-owner-source-1')
SDK13_PROFILE_PATH = SDK13_DIR.parent / 'sdk21-nonheld13-data32-compile-preparation-1/SDK21-COMPILE.SOURCE-ONLY.json'
SDK13_REQUEST_PATH = SDK13_DIR.parent / 'sdk21-nonheld13-input-validation-source-1/SDK13-DATA32-ADMISSION.SOURCE-ONLY.json'
SDK13_DRIVER = SDK13_DIR / 'sdk13_four_command_driver.v4.py'
SDK13_DRIVER_SHA = '4e02868edc4928fc1f4050832de9656d35a9a3b589c0b8293f46a6f790e3a26a'
SDK13_VALIDATOR = SDK13_DIR.parent / 'sdk21-nonheld13-input-validation-source-1/sdk13_data32_input_validation.py'
SDK13_VALIDATOR_SHA = 'a9912953c35ce94a92713d93c39d28a40e788f334de548aadbda656e8dba0587'
SDK13_IMAGE = 'sha256:41778f1f22fd68897c1209e225a9807a197ed47bf0edd17835821bb5986e50b5'
SDK13_OPERATION = 'M14_SDK13_DATA32_RETIRED_ROOT70_COMPILE_ONLY_V1'
SDK13_RELEASE = SDK13_DIR / 'ROOT-SDK13-DATA32-RELEASE.ACTUAL.json'
SDK13_ACCEPTANCE = SDK13_DIR / 'ROOT-SDK13-DATA32-PHYSICAL-ACCEPTANCE.ACTUAL.json'
SDK13_WORK = Path('/home/holden/mckernel-work/scratch/sdk21-nonheld13-data32-compile-only-20261030-1')
SDK13_CONTROL = SDK13_DIR.parent / 'ACTUAL-CONTROLS-ARMED.json'
SDK13_CAPACITY = SDK13_DIR.parent / 'ACTUAL-CAPACITY-FALLBACK-ARMED.json'
SDK13_UTC = 1793774133
SDK13_BOOT = 1571569.6959267766
SDK13_MONO = 1556231.5688797957
SDK13_BOOT_ID = '7bfc5687-6c04-4d15-84eb-b92ab9a55dcb'
SDK13_CLEAN_ENV = {'PATH':'/usr/bin:/bin','HOME':'/nonexistent','LANG':'C','LC_ALL':'C',
                   'TMPDIR':'/tmp','HOSTNAME':'mckernel-sdk13'}



def _sdk13_root_file_mode(uid,gid,mode,euid):
    return uid==0 and ((gid==1000 and mode==0o640) or (mode==0o600 and euid==0))

def _sdk13_no_access_acl(fd):
    try:os.getxattr(fd,'system.posix_acl_access')
    except OSError as exc:
        if exc.errno in (errno.ENODATA,errno.ENOTSUP):return
        raise
    raise OwnerError('SDK13 root document extended access ACL not allowed')

def _sdk13_read(path, maximum, expected_sha=None, root=False):
    path=Path(path)
    if root:
        _fail(path.is_absolute() and SDK13_DIR in path.parents,
              'SDK13 root document must be in the new private SDK namespace')
    _no_symlink_parents(path,'SDK13 bound input')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
    try:
        st = os.fstat(fd)
        _fail(stat.S_ISREG(st.st_mode) and st.st_nlink == 1 and st.st_size <= maximum,
              'SDK13 bounded single-link regular file required: ' + str(path))
        if root:
            _fail(_sdk13_root_file_mode(st.st_uid,st.st_gid,stat.S_IMODE(st.st_mode),os.geteuid()),
                  'SDK13 root document UID/GID/mode differs')
            _sdk13_no_access_acl(fd)
        chunks=[]; total=0
        while True:
            block=os.read(fd,65536)
            if not block: break
            total+=len(block); _fail(total<=maximum, 'SDK13 file grew')
            chunks.append(block)
        end=os.fstat(fd); named=os.lstat(path)
        keys=('st_dev','st_ino','st_uid','st_gid','st_mode','st_nlink','st_size','st_mtime_ns','st_ctime_ns')
        _fail(total==st.st_size and all(getattr(st,k)==getattr(end,k)==getattr(named,k) for k in keys),
              'SDK13 file identity changed: ' + str(path))
        data=b''.join(chunks); digest=hashlib.sha256(data).hexdigest()
        if expected_sha is not None: _fail(digest==expected_sha, 'SDK13 hash mismatch: ' + str(path))
        return data, (st.st_dev,st.st_ino,st.st_mode,st.st_uid,st.st_gid,st.st_nlink,st.st_size,st.st_mtime_ns,st.st_ctime_ns,digest)
    finally: os.close(fd)


def _sdk13_module():
    raw,_=_sdk13_read(SDK13_VALIDATOR,2**20,SDK13_VALIDATOR_SHA)
    module=types.ModuleType('_sdk13_authenticated_input_validator')
    module.__file__=str(SDK13_VALIDATOR)
    exec(compile(raw,str(SDK13_VALIDATOR),'exec'),module.__dict__)
    _fail(callable(getattr(module,'validate',None)) and callable(getattr(module,'revalidate',None)),
          'SDK13 validator API missing')
    return module


def _sdk13_root(ref, path):
    _fail(isinstance(ref,dict) and set(ref)=={'path','sha256'} and ref['path']==str(path) and
          isinstance(ref['sha256'],str) and re.fullmatch(r'[0-9a-f]{64}',ref['sha256']),
          'SDK13 sealed reference missing')
    _no_symlink_parents(path,'SDK13 sealed document')
    raw,ident=_sdk13_read(path,2**20,ref['sha256'],root=True)
    value=json.loads(raw); _fail(isinstance(value,dict),'SDK13 sealed object expected')
    return value,ident


def _sdk13_ref(ref):
    _fail(isinstance(ref,dict) and set(ref)=={'path','sha256'} and
          isinstance(ref['path'],str) and Path(ref['path']).is_absolute(), 'SDK13 evidence reference invalid')
    return _sdk13_root(ref,Path(ref['path']))



def _sdk13_capture_fresh(now,observed,expiry):
    return (type(observed) in (int,float) and type(expiry) in (int,float) and
            0<=now-observed<=30 and now<expiry<=SDK13_UTC)

def _sdk13_authorize(request):
    release,identity=_sdk13_root(request.get('compile_only_release'),SDK13_RELEASE)
    _fail(release.get('status')=='RELEASED_ONE_SDK13_COMPILE_ONLY' and
          release.get('operation')==SDK13_OPERATION and release.get('profile_sha256')==SDK13_PROFILE_SHA and
          release.get('driver_sha256')==SDK13_DRIVER_SHA and release.get('validator_sha256')==SDK13_VALIDATOR_SHA and
          release.get('source_map_sha256')==request.get('source_map_sha256') and
          release.get('container_env')==SDK13_CLEAN_ENV and
          release.get('owner_sha256')==_sha256(Path(__file__)) and
          release.get('request_core_sha256')==_request_core_hash(request), 'SDK13 release bindings differ')
    policy=_sdk13_containment_policy(release,request)
    facts=release.get('admission'); boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
    _validate_sdk13_facts(facts,_boottime_ns(),boot)
    _fail(boot==SDK13_BOOT_ID and facts.get('service_status')=='NO_NEW_REJECTION' and
          facts.get('paid_fallback') is False and type(facts.get('weekly_used_percent')) in (int,float) and
          0<=facts['weekly_used_percent']<100, 'SDK13 service or weekly allowance not established')
    now=time.time(); bt=time.clock_gettime(time.CLOCK_BOOTTIME); mono=time.monotonic()
    _fail(_sdk13_capture_fresh(now,facts.get('weekly_observed_utc'),facts.get('expiry_utc')) and
          now<SDK13_UTC and bt<SDK13_BOOT and mono<SDK13_MONO and
          now<policy['until_utc'] and bt<policy['until_boot'] and mono<policy['until_mono'],
          'SDK13 usage, time ceiling or containment authority expired')
    controls=[]
    for path,key in ((SDK13_CONTROL,'controls_sha256'),(SDK13_CAPACITY,'capacity_sha256')):
        data,record=_sdk13_read(path,2**20,facts.get(key));
        _fail(isinstance(facts.get(key),str),'SDK13 control hash missing')
        doc=json.loads(data)
        _fail(doc.get('caps')=={'boot_deadline':SDK13_BOOT,'boot_id':SDK13_BOOT_ID,'deadline':SDK13_UTC,
                                'monotonic_deadline':SDK13_MONO},'SDK13 actual control caps mismatch')
        controls.append(record)
    evidence=[]; refs=release.get('evidence_refs')
    _fail(isinstance(refs,dict) and set(refs)==set(SDK13_REQUIRED_FACTS), 'SDK13 fact evidence incomplete')
    for name in SDK13_REQUIRED_FACTS:
        ref=refs[name]; _fail(ref.get('sha256')==facts['facts'][name]['evidence_sha256'], 'SDK13 fact hash differs')
        _,record=_sdk13_ref(ref); evidence.append((name,record))
    daemon=facts.get('daemon')
    _fail(isinstance(daemon,dict) and daemon.get('pid')==2036 and daemon.get('starttime')==1513 and
          release.get('daemon_read_contract')==SDK13_DAEMON_CONTRACT,
          'SDK13 fixed daemon read contract or sealed identity differs')
    _fail(_mem_available()>=24*2**30,'SDK13 actual memory below floor')
    for path,key,floor in ((Path('/home/holden/mckernel'),'host_required_bytes',16*2**30),
                           (Path('/home/holden/mckernel-work/scratch'),'scratch_required_bytes',12*2**30)):
        st=os.statvfs(path); free=st.f_bavail*st.f_frsize; need=facts.get(key)
        _fail(type(need) is int and need>=floor and free>=need,'SDK13 actual disk below admitted bound')
    return {'release':identity,'controls':controls,'evidence':evidence,'daemon':daemon}


SDK13_DAEMON_PARENT = SDK13_DIR / 'sdk13_daemon_metadata_parent.v6.py'
SDK13_DAEMON_PARENT_SHA = 'df90959f8996eeca19f5075e55a0d5b3ec96da42004c77957929712b963ba492'
SDK13_DAEMON_READER = SDK13_DIR / 'sdk13_daemon_metadata_reader.v4.py'
SDK13_DAEMON_READER_SHA = 'ef5eadb127f024275e10cbe2d4c8b2f2a8cf1a3fe301a20cd7d23a627df1d9f8'
SDK13_CAPTURE_SOURCE = SDK13_DIR / 'sdk13_owned_capture.v5.py'
SDK13_CAPTURE_SHA = '8f8774534d8c97436abc26dcbb45581ecb1debf025c9385dd3da95e482a34310'
SDK13_CENSUS_SHA = '96d17547bfc71454d54e95a705138cc9b26faa1e2cafc34105c9ed8d5a68f4d1'
SDK13_PYTHON = '/home/holden/anaconda3/bin/python3.9'
SDK13_PYTHON_SHA = '8f122d7bdf820e716491d2be6c3b9f2b85f5fa46b34811e29432fa7cd8fd41fb'
SDK13_DAEMON_PHASES = ('prelease','pre-create','pre-start')
SDK13_DAEMON_ARGV = ['/usr/bin/sudo','-A','/usr/bin/taskset','-c','7','/usr/bin/prlimit',
    '--as=536870912:536870912','--cpu=10:10','--fsize=8388608:8388608',
    '--nofile=128:128','--core=0:0','--',SDK13_PYTHON,'-I','-B',str(SDK13_DAEMON_PARENT)]
SDK13_DAEMON_CONTRACT = {'parent_sha256':SDK13_DAEMON_PARENT_SHA,'reader_sha256':SDK13_DAEMON_READER_SHA,
    'capture_sha256':SDK13_CAPTURE_SHA,'census_sha256':SDK13_CENSUS_SHA,'python_sha256':SDK13_PYTHON_SHA,
    'daemon_pid':2036,'daemon_birth':1513,'boot_id':SDK13_BOOT_ID,'socket':'/var/run/docker.sock',
    'affinity':'7','AS_each':536870912,'CPU_each':10,'wall_seconds':15,'outer_kill_grace_seconds':5,
    'reserved_parent_plus_reader_bytes':1073741824,'max_invocations':3,'phases':list(SDK13_DAEMON_PHASES),
    'compiler_concurrent':False,'argv_prefix':SDK13_DAEMON_ARGV,'argv_suffix':'stable sealed release/control identity JSON'}


def _sdk13_capture_library():
    import ast
    raw,_=_sdk13_read(SDK13_CAPTURE_SOURCE,2**20,SDK13_CAPTURE_SHA)
    funcs={'need','write','hashed','stop','cpu_used','members','process_start','terminal_unreaped','wait_terminal','owned_capture'}
    assignments={'FIELDS','stopping','CENSUS_SOURCE','CENSUS_SHA','_CENSUS','STOP_SIGNALS'}
    nodes=[]
    for node in ast.parse(raw,str(SDK13_CAPTURE_SOURCE)).body:
        if (isinstance(node,(ast.Import,ast.ImportFrom)) or
            isinstance(node,ast.FunctionDef) and node.name in funcs or
            isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id in assignments for t in node.targets)):
            nodes.append(node)
    scope={'__file__':str(SDK13_CAPTURE_SOURCE)}
    exec(compile(ast.Module(body=nodes,type_ignores=[]),str(SDK13_CAPTURE_SOURCE),'exec'),scope)
    _fail(callable(scope.get('owned_capture')) and scope.get('CENSUS_SHA')==SDK13_CENSUS_SHA,
          'SDK13 daemon capture source mismatch')
    return scope


def _sdk13_check_daemon_capture(join,doc,expected):
    _fail(isinstance(join,dict) and join.get('returncode')==0 and join.get('direct_child_joined') is True and
          join.get('group_absent') is True and join.get('closed_streams') is True and
          not join.get('error') and not join.get('retirement_error') and not join.get('timed_out'),
          'SDK13 sudo daemon capture or join unknown')
    _fail(isinstance(doc,dict) and doc.get('status')=='PASS_EXACT_DAEMON_METADATA' and
          doc.get('reader_direct_joined') is True and doc.get('reader_group_absent') is True and
          doc.get('reader_streams_closed') is True and doc.get('reader_wait4_status')==0 and not doc.get('error'),
          'SDK13 root daemon reader custody unknown')
    stdout=doc.get('reader_stdout');stderr=doc.get('reader_stderr')
    _fail(isinstance(stdout,dict) and stdout.get('complete') is True and not stdout.get('error') and
          isinstance(stderr,dict) and stderr.get('complete') is True and not stderr.get('error') and
          stderr.get('bytes')==0 and stderr.get('base64')=='' and
          stderr.get('sha256')==hashlib.sha256(b'').hexdigest(), 'SDK13 reader diagnostics incomplete or nonempty')
    try: raw=base64.b64decode(stdout.get('base64',''),validate=True)
    except (ValueError,TypeError) as exc:raise OwnerError('SDK13 reader stdout encoding differs') from exc
    _fail(len(raw)==stdout.get('bytes') and hashlib.sha256(raw).hexdigest()==stdout.get('sha256') and
          json.loads(raw)==doc.get('sample'), 'SDK13 retained reader stdout differs')
    outer=join.get('effect_boundary');inner=doc.get('pre_reader_gate')
    _fail(isinstance(outer,dict) and isinstance(inner,dict) and
          outer.get('weekly_observed_utc')==inner.get('weekly_observed_utc') and
          outer.get('expiry_utc')==inner.get('expiry_utc') and
          type(outer.get('boot')) in (int,float) and type(inner.get('boot')) in (int,float) and
          type(outer.get('mono')) in (int,float) and type(inner.get('mono')) in (int,float) and
          inner['boot']>=outer['boot'] and inner['mono']>=outer['mono'],
          'SDK13 outer/reader effect boundary evidence differs')
    parent=doc.get('parent');reader=doc.get('reader');sample=doc.get('sample')
    _fail(isinstance(parent,dict) and isinstance(reader,dict) and isinstance(sample,dict) and
          type(parent.get('pid')) is int and parent['pid']>0 and type(parent.get('birth')) is int and parent['birth']>0 and
          parent.get('ppid')==join.get('pid') and parent.get('pgid')==join.get('pid') and parent.get('sid')==join.get('pid') and
          reader.get('ppid')==parent['pid'] and reader.get('pgid')==reader.get('pid') and reader.get('sid')==reader.get('pid') and
          doc.get('reader_wait4_pid')==reader.get('pid') and sample.get('reader')==reader,
          'SDK13 root caller or reader identity mismatch')
    _fail(sample.get('status')=='OBSERVED_EXACT_DAEMON_READONLY' and sample.get('boot_id')==SDK13_BOOT_ID and
          sample.get('daemon_birth_before')==sample.get('daemon_birth_after')==1513 and
          sample.get('daemon')==expected, 'SDK13 fixed daemon identity differs')
    return sample['daemon']


def _sdk13_capture_daemon(phase,evidence_root,expected,request,authority,signals):
    _fail(phase in SDK13_DAEMON_PHASES,'SDK13 unknown daemon capture phase')
    _sdk13_read(SDK13_DAEMON_PARENT,2**20,SDK13_DAEMON_PARENT_SHA)
    _sdk13_read(SDK13_DAEMON_READER,2**20,SDK13_DAEMON_READER_SHA)
    _fail(_sha256(Path(SDK13_PYTHON))==SDK13_PYTHON_SHA,'SDK13 daemon Python changed')
    capture=_sdk13_capture_library();path=Path(evidence_root)/('daemon-'+phase);os.mkdir(path,0o700)
    def limits():
        import resource
        for key,value in ((resource.RLIMIT_AS,536870912),(resource.RLIMIT_CPU,10),
                          (resource.RLIMIT_FSIZE,8388608),(resource.RLIMIT_NOFILE,128),(resource.RLIMIT_CORE,0)):
            resource.setrlimit(key,(value,value))
    _fail(_sdk13_authorize(request)==authority,'SDK13 authority changed immediately before daemon capture')
    token=json.dumps({'release':list(authority['release']),
                      'controls':[list(x) for x in authority['controls']]},sort_keys=True,separators=(',',':'))
    argv=SDK13_DAEMON_ARGV+[token]
    join=capture['owned_capture']({'argv':argv},path,15,limits,
            effect_gate=lambda:_sdk13_effect_gate(request,authority,signals,'daemon-'+phase))
    raw,_=_sdk13_read(path/'stdout',16384);doc=json.loads(raw)
    observed=_sdk13_check_daemon_capture(join,doc,expected)
    _exclusive_json(path/'sdk13-daemon-verdict.json',{'status':'PASS_EXACT_DAEMON_CAPTURE',
                    'phase':phase,'daemon':observed,'parent':doc['parent'],'reader':doc['reader'],
                    'outer_join':join,'current_free':False})
    return observed


def _sdk13_set_profile(request,bound):
    global COMPILE_PROFILE, COMPILE_PROFILE_SHA256
    _fail(request.get('compile_operation')==SDK13_OPERATION and request.get('jobs')==1 and
          type(request.get('timeout')) is int and
          1<=request['timeout']<=2500, 'SDK13 operation or timeout invalid')
    nonce=request.get('owner_nonce')
    _fail(isinstance(nonce,str) and re.fullmatch(r'[0-9a-f]{32}',nonce) and nonce not in
          ('4709c9fae2c743a7acd662e93a663358','5732bbe86da94491884b8b18a020f2ea',
           '95f3c1f79ec040ddbb7065ff9f5ca536'),'SDK13 fresh nonce required')
    _fail(Path(bound['work'])==SDK13_WORK and Path(bound['lease'])==SDK13_DIR/'sdk13-data32-owner-evidence-1/compile-lease.json' and
          Path(bound['owner_evidence'])==SDK13_DIR/'sdk13-data32-owner-evidence-1' and
          Path(bound['attempt'])==SDK13_DIR/'sdk13-data32-owner-evidence-1/attempt' and
          request.get('lease_path')==str(bound['lease']), 'SDK13 private domain differs')
    COMPILE_PROFILE_SHA256=SDK13_PROFILE_SHA
    COMPILE_PROFILE={'operation':SDK13_OPERATION,'container_name':'mckernel-sdk13-'+nonce,
                     'owner_nonce':nonce,'image_id':SDK13_IMAGE,'lease_path':str(bound['lease']),'limits':LIMITS}


def _sdk13_mounts(bound):
    mounts=[(str(SDK13_WORK),'/work',False)]
    mounts.extend((str(a),str(b),bool(c)) for a,b,c in bound['readonly_mounts'])
    mounts.extend([(str(SDK13_PROFILE_PATH),'/work/sdk13-profile.json',True),
                   (str(SDK13_DRIVER),'/work/sdk13-driver.py',True),
                   (str(bound['source_map_path']),'/work/sdk13-source-map.json',True)])
    _fail(all(ro for _,_,ro in mounts[1:]) and len({p[1] for p in mounts})==len(mounts),
          'SDK13 mount set not exclusive or duplicate targets')
    return mounts



def _sdk13_manifest(bound,request):
    rows=[]
    for source,target,readonly in _sdk13_mounts(bound):
        _no_symlink_parents(Path(source),'SDK13 mount source')
        st=os.lstat(source)
        _fail(not stat.S_ISLNK(st.st_mode) and (stat.S_ISDIR(st.st_mode) or stat.S_ISREG(st.st_mode)),
              'SDK13 mounted source type differs')
        rows.append({'target':target,'readonly':readonly,'device':st.st_dev,'inode':st.st_ino,'mode':st.st_mode})
    doc={'schema':'mckernel.sdk13.effective-mounts.v1','profile_sha256':SDK13_PROFILE_SHA,
         'source_map_sha256':request['source_map_sha256'],'driver_sha256':SDK13_DRIVER_SHA,'mounts':rows}
    path=Path(bound['attempt'])/'effective-mounts.json';_exclusive_json(path,doc)
    raw,identity=_sdk13_read(path,8*2**20);return {'path':str(path),'sha256':hashlib.sha256(raw).hexdigest(),
                                                'identity':identity,'mounts':rows}


def _sdk13_revalidate_manifest(bound,manifest):
    _,identity=_sdk13_read(Path(manifest['path']),8*2**20,manifest['sha256'])
    _fail(identity==manifest['identity'],'SDK13 effective mount manifest identity changed')
    _fail(len(_sdk13_mounts(bound))==len(manifest['mounts']),'SDK13 mount manifest count changed')
    for (source,target,readonly),row in zip(_sdk13_mounts(bound),manifest['mounts']):
        st=os.lstat(source)
        _fail((target,readonly,st.st_dev,st.st_ino,st.st_mode)==
              (row['target'],row['readonly'],row['device'],row['inode'],row['mode']),
              'SDK13 mounted source changed before launch')


def _sdk13_create_args(bound,request,manifest):
    mounts=_sdk13_mounts(bound)+[(manifest['path'],'/work/sdk13-effective-mounts.json',True)]
    mi=manifest['identity']; command=['/work/sdk13-driver.py',request['source_map_sha256'],
        manifest['sha256'],str(mi[0]),str(mi[1]),str(mi[2]),SDK13_DRIVER_SHA]
    args=['create','--name',COMPILE_PROFILE['container_name'],
          '--label','mckernel.owner='+COMPILE_PROFILE['owner_nonce'],
          '--label','mckernel.operation='+SDK13_OPERATION,'--init','--network=none','--ipc=private',
          *RESOURCE_ARGS,'--user','1000:1000','--cap-drop=ALL','--security-opt=no-new-privileges',
          '--read-only','--hostname','mckernel-sdk13','--tmpfs','/tmp:rw,nodev,nosuid,size=256m']
    for key,value in SDK13_CLEAN_ENV.items():args+=['--env',key+'='+value]
    for source,target,readonly in mounts:
        args+=['--mount','type=bind,src='+source+',dst='+target+(',readonly' if readonly else '')]
    args+=['--entrypoint','/usr/bin/python3',SDK13_IMAGE,*command]
    return args,mounts,command



# Emit only selected fields and fixed-value environment markers; never capture
# the image's raw Config.Env. Exact-own-CID checks remain the retained checks.
SDK13_HOST_KEYS=('NanoCpus','CpusetCpus','Memory','MemorySwap','PidsLimit','NetworkMode',
                 'Privileged','ReadonlyRootfs','CapDrop','SecurityOpt','Init','PidMode',
                 'IpcMode','Devices','DeviceRequests','Binds','CapAdd','CgroupParent','Tmpfs')
SDK13_STATE_KEYS=('Running','Status','Pid','Paused','Restarting','Dead')
SDK13_FIELD_EXPR=(['.Id','.Name','.Image']+['.State.'+k for k in SDK13_STATE_KEYS]+
                  ['.HostConfig.'+k for k in SDK13_HOST_KEYS]+
                  ['.Mounts','.Config.Entrypoint','.Config.Cmd','.Config.User',
                   '(index .Config.Labels "mckernel.owner")',
                   '(index .Config.Labels "mckernel.operation")'])
SDK13_ENV_MARKERS=('P','H','L','C','T','N')
SDK13_ENV_TEMPLATE='{{range .Config.Env}}'+''.join(
    ('{{if ' if i==0 else '{{else if ')+'eq . '+json.dumps(k+'='+v)+'}}'+SDK13_ENV_MARKERS[i]
    for i,(k,v) in enumerate(SDK13_CLEAN_ENV.items()))+'{{else}}X{{end}}{{end}}'
SDK13_INSPECT_TEMPLATE='\n'.join('{{json '+e+'}}' for e in SDK13_FIELD_EXPR)+'\n'+SDK13_ENV_TEMPLATE


def _sdk13_own_inspect(docker,cid=None):
    target=cid or COMPILE_PROFILE['container_name']
    result=docker.call(['inspect','--format',SDK13_INSPECT_TEMPLATE,target])
    lines=result.stdout.splitlines()
    _fail(len(lines)==len(SDK13_FIELD_EXPR)+1,'SDK13 redacted inspect shape differs')
    environment_matches=sorted(lines[-1])==sorted(SDK13_ENV_MARKERS)
    fields=[json.loads(line) for line in lines[:-1]]
    off=0; ident,name,image=fields[:3];off=3
    state=dict(zip(SDK13_STATE_KEYS,fields[off:off+len(SDK13_STATE_KEYS)]));off+=len(SDK13_STATE_KEYS)
    host=dict(zip(SDK13_HOST_KEYS,fields[off:off+len(SDK13_HOST_KEYS)]));off+=len(SDK13_HOST_KEYS)
    mounts,entrypoint,cmd,user,owner_label,operation_label=fields[off:]
    info={'Id':ident,'Name':name,'Image':image,'State':state,'HostConfig':host,'Mounts':mounts,
          'sdk13_environment_matches':environment_matches,
          'Config':{'Entrypoint':entrypoint,'Cmd':cmd,'User':user,
                    'Labels':{'mckernel.owner':owner_label,'mckernel.operation':operation_label}}}
    _assert_owned_container(info,cid)
    return info


# The retained exact-CID cleanup resolves this function dynamically.
_own_inspect=_sdk13_own_inspect


def _sdk13_prepare_work(bound,request,validator):
    work=Path(bound['work']);os.mkdir(work,0o700)
    st=os.lstat(work)
    created=tuple(getattr(st,k) for k in ('st_dev','st_ino','st_mode','st_uid','st_gid','st_nlink','st_size','st_mtime_ns','st_ctime_ns'))
    validator.bind_work(bound,request,created)
    data,_=_sdk13_read(SDK13_PROFILE_PATH,2**20,SDK13_PROFILE_SHA); profile=json.loads(data)
    def host_path(raw):
        path=Path(raw); _fail(path.is_absolute() and '..' not in path.parts and path!=Path('/work'), 'SDK13 mount target invalid')
        return work/path.relative_to('/work')
    for name in profile['private_work']['precreation_requirements']['required_output_directories']:
        host_path(name).mkdir(parents=True,exist_ok=True)
    for _,target,readonly in _sdk13_mounts(bound)[1:]+[(str(bound['attempt'])+'/effective-mounts.json','/work/sdk13-effective-mounts.json',True)]:
        if target.startswith('/work/'):
            _fail(readonly,'SDK13 unexpected writable nested mount')
            placeholder=host_path(target);placeholder.parent.mkdir(parents=True,exist_ok=True)
            fd=os.open(placeholder,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW|os.O_CLOEXEC,0o600)
            os.close(fd)
    return created

def _sdk13_driver_result(bound,request,manifest):
    evidence=Path(bound['work'])/'sdk13-driver-evidence'
    proof=_load_json(_safe_regular(evidence/'precompiler-view.json','SDK13 mounted view proof'),'SDK13 mounted view proof')
    _fail(proof.get('status')=='PASS_EFFECTIVE_MOUNTS_SOURCE_ENV' and
          proof.get('profile_sha256')==SDK13_PROFILE_SHA and proof.get('driver_sha256')==SDK13_DRIVER_SHA and
          proof.get('source_map_sha256')==request['source_map_sha256'] and
          proof.get('mount_manifest_sha256')==manifest['sha256'], 'SDK13 precompiler mounted view mismatch')
    result=_load_json(_safe_regular(evidence/'result.json','SDK13 driver result'),'SDK13 driver result')
    _fail(result.get('status')=='COMMANDS_EXITED_ZERO' and result.get('artifact_validation')=='NOT_PERFORMED',
          'SDK13 driver did not report four zero exits')
    for i in range(1,5):
        intent=_load_json(_safe_regular(evidence/('stage-%d-intent.json'%i),'SDK13 intent'),'SDK13 intent')
        row=_load_json(_safe_regular(evidence/('stage-%d-result.json'%i),'SDK13 stage'),'SDK13 stage')
        _fail(intent.get('argv')==bound['commands'][i-1]['argv'] and
              intent.get('cwd')==bound['commands'][i-1]['cwd'] and
              row.get('stage')==bound['commands'][i-1]['stage'] and
              row.get('returncode')==0 and row.get('direct_wait_completed') is True and
              row.get('timed_out') is False and not row.get('error'),'SDK13 stage or command differs')
        for suffix in ('stdout','stderr'):
            _safe_regular(evidence/('stage-%d.%s'%(i,suffix)),'SDK13 stage capture')
    outputs=[]
    depfiles=['/work/output/build/kernel/rust/mckernel_rust.d',
              '/work/output/build/kernel/CMakeFiles/mckernel.img.dir/syscall.c.o.d',
              '/work/output/build/kernel/CMakeFiles/mckernel.img.dir/__/arch/x86_64/kernel/syscall.c.o.d',
              '/work/output/build/kernel/CMakeFiles/mckernel.img.dir/link.d',
              '/work/output/build/kernel/mckernel.img.map']
    for raw in bound['outputs']+depfiles:
        host=Path(bound['work']) / Path(raw).relative_to('/work')
        path=_safe_regular(host,'SDK13 actual output')
        _fail(path.stat().st_size>0,'SDK13 output empty')
        outputs.append({'path':str(path),'bytes':path.stat().st_size,'sha256':_sha256(path)})
    return outputs


SDK13_EFFECT_STOP_SIGNALS={signal.SIGTERM,signal.SIGINT,signal.SIGALRM}


def _sdk13_evaluate_effect(expected_release,actual_release,expected_controls,actual_controls,
                           facts,utc,boot,mono,boot_id,stopped):
    _fail(expected_release==actual_release and expected_controls==actual_controls,
          'SDK13 release/control identity changed before effect')
    _fail(not stopped,'SDK13 stop before effect')
    _fail(isinstance(facts,dict) and facts.get('service_status')=='NO_NEW_REJECTION' and
          facts.get('paid_fallback') is False and type(facts.get('weekly_used_percent')) in (int,float) and
          0<=facts['weekly_used_percent']<100 and
          _sdk13_capture_fresh(utc,facts.get('weekly_observed_utc'),facts.get('expiry_utc')) and
          utc<SDK13_UTC and boot<SDK13_BOOT and mono<SDK13_MONO and boot_id==SDK13_BOOT_ID,
          'SDK13 usage or clock expired before effect')
    return {'utc':utc,'boot':boot,'mono':mono,'weekly_observed_utc':facts['weekly_observed_utc'],
            'expiry_utc':facts['expiry_utc']}


def _sdk13_effect_gate(request,authority,signals,phase):
    _fail(signals is not None,'SDK13 stop observer missing')
    current,release_id=_sdk13_root(request.get('compile_only_release'),SDK13_RELEASE)
    facts=current.get('admission');controls=[]
    for path,key in ((SDK13_CONTROL,'controls_sha256'),(SDK13_CAPACITY,'capacity_sha256')):
        _fail(isinstance(facts,dict) and isinstance(facts.get(key),str),'SDK13 current control binding missing')
        raw,ident=_sdk13_read(path,2**20,facts[key]);doc=json.loads(raw)
        _fail(doc.get('caps')=={'boot_deadline':SDK13_BOOT,'boot_id':SDK13_BOOT_ID,'deadline':SDK13_UTC,
                                'monotonic_deadline':SDK13_MONO},'SDK13 current control caps changed')
        controls.append(ident)
    boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
    utc=time.time();boot=time.clock_gettime(time.CLOCK_BOOTTIME);mono=time.monotonic()
    stopped=signals.requested is not None or bool(signal.sigpending() & SDK13_EFFECT_STOP_SIGNALS)
    result=_sdk13_evaluate_effect(authority['release'],release_id,authority['controls'],controls,
                                  facts,utc,boot,mono,boot_id,stopped)
    result['phase']=phase
    return result


def _sdk13_retirement_effect_gate(request,acceptance_identity,retirement_authority,signals,phase):
    _fail(signals is not None,'SDK13 retirement stop observer missing')
    current,actual=_sdk13_root(request.get('physical_acceptance'),SDK13_ACCEPTANCE)
    controls=[]
    for path,key in ((SDK13_CONTROL,'controls_sha256'),(SDK13_CAPACITY,'capacity_sha256')):
        _fail(isinstance(current.get(key),str),'SDK13 retirement control binding missing')
        raw,ident=_sdk13_read(path,2**20,current[key]);doc=json.loads(raw)
        _fail(doc.get('caps')=={'boot_deadline':SDK13_BOOT,'boot_id':SDK13_BOOT_ID,'deadline':SDK13_UTC,
                                'monotonic_deadline':SDK13_MONO},'SDK13 retirement control caps changed')
        controls.append(ident)
    _fail(current.get('release_action_authorized') is True,'SDK13 retirement action not released')
    boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
    utc=time.time();boot=time.clock_gettime(time.CLOCK_BOOTTIME);mono=time.monotonic()
    stopped=signals.requested is not None or bool(signal.sigpending() & SDK13_EFFECT_STOP_SIGNALS)
    result=_sdk13_evaluate_effect(acceptance_identity,actual,retirement_authority[0],controls,
                                  current,utc,boot,mono,boot_id,stopped)
    result['phase']='retirement-'+phase
    return result


# Cleanup authority is sealed with the one SDK release but has a strictly
# limited purpose: stop only the exact CID created by this owner. It does not
# authorize create, start, removal, global clearance or lease release.
SDK13_CONTAINMENT_ACTIONS=('inspect','stop','kill','wait')


def _sdk13_containment_policy(release,request):
    policy=release.get('containment_policy')
    _fail(isinstance(policy,dict) and set(policy)=={'status','operation','profile_sha256','owner_sha256',
          'request_core_sha256','owner_nonce','allowed_actions','max_calls','max_wall_seconds',
          'until_utc','until_boot','until_mono'},'SDK13 sealed containment policy missing')
    _fail(policy['status']=='EXACT_CREATED_CID_CONTAINMENT_ONLY' and policy['operation']==SDK13_OPERATION and
          policy['profile_sha256']==SDK13_PROFILE_SHA and policy['owner_sha256']==_sha256(Path(__file__)) and
          policy['request_core_sha256']==_request_core_hash(request) and policy['owner_nonce']==request.get('owner_nonce') and
          policy['allowed_actions']==list(SDK13_CONTAINMENT_ACTIONS) and policy['max_calls']==8 and
          policy['max_wall_seconds']==90 and all(type(policy[k]) in (int,float) and 0<policy[k]<10**12
          for k in ('until_utc','until_boot','until_mono')),'SDK13 containment scope or bounds differ')
    return policy


def _sdk13_containment_args(args,cid,attested):
    _fail(isinstance(args,tuple) and re.fullmatch(r'[0-9a-f]{64}',cid or ''),'SDK13 containment CID unavailable')
    allowed=(('inspect','--format',SDK13_INSPECT_TEMPLATE,cid),('stop','--time','15',cid),('kill',cid),('wait',cid))
    _fail(args in allowed,'SDK13 containment action or CID differs')
    _fail(args[0]=='inspect' or attested,'SDK13 containment CID not yet authenticated')
    return args[0]


class SDK13Containment:
    def __init__(self,request,authority,lease,cid):
        _fail(isinstance(cid,str) and re.fullmatch(r'[0-9a-f]{64}',cid),'SDK13 created CID unknown')
        self.request=request;self.authority=authority;self.lease=lease;self.cid=cid
        self.started=time.monotonic();self.calls=0;self.attested=False
    def gate(self,args):
        action=_sdk13_containment_args(args,self.cid,self.attested)
        release,identity=_sdk13_root(self.request.get('compile_only_release'),SDK13_RELEASE)
        _fail(identity==self.authority['release'],'SDK13 containment root release changed')
        policy=_sdk13_containment_policy(release,self.request)
        raw=self.lease.load_owned()
        _fail(self.lease.record.get('pid')==os.getpid() and
              self.lease.record.get('starttime')==_proc_starttime(os.getpid()) and
              self.lease.record.get('request_core_sha256')==_request_core_hash(self.request),
              'SDK13 containment owner or lease changed')
        now=time.time();boot=time.clock_gettime(time.CLOCK_BOOTTIME);mono=time.monotonic()
        _fail(self.calls<policy['max_calls'] and now<policy['until_utc'] and boot<policy['until_boot'] and
              mono<policy['until_mono'] and mono-self.started<policy['max_wall_seconds'],
              'SDK13 containment authority expired')
        # One absolute client deadline includes the 5-second retirement reserve;
        # neither spawn/setup nor a later wait may reset it.
        deadline=min(mono+30.0,self.started+policy['max_wall_seconds'],policy['until_mono'],
                     mono+(policy['until_utc']-now),mono+(policy['until_boot']-boot))
        _fail(deadline-mono>5.0,'SDK13 containment lacks client retirement window')
        self.calls+=1
        return {'phase':'containment-'+action,'cid':self.cid,'call':self.calls,'utc':now,'boot':boot,'mono':mono,
                'absolute_deadline_mono':deadline,'retirement_reserve_seconds':5.0,
                'lease_sha256':hashlib.sha256(raw).hexdigest(),'limited_retirement_only':True}
    def confirm(self,info):
        _assert_owned_container(info,self.cid);self.attested=True


def _sdk13_contain_created(request,authority,lease,cid,attempt,signals):
    state=SDK13Containment(request,authority,lease,cid)
    client=_HOST_OWNER.Docker(Path(attempt)/'containment-docker.log',signals,sudo=True,effect_gate=state.gate)
    info=_sdk13_own_inspect(client,cid);state.confirm(info)
    if info.get('State',{}).get('Running') or info.get('State',{}).get('Status') in ('paused','restarting'):
        client.call(['stop','--time','15',cid],timeout=30,check=False)
        info=_sdk13_own_inspect(client,cid);state.confirm(info)
        if info.get('State',{}).get('Running'):
            client.call(['kill',cid],timeout=30)
        client.call(['wait',cid],timeout=30)
        info=_sdk13_own_inspect(client,cid);state.confirm(info)
    _fail(info.get('State',{}).get('Running') is False and info['State'].get('Pid')==0 and
          info['State'].get('Status') in ('exited','created','dead') and
          not client.client_retirement_unproven,'SDK13 exact CID containment remains unknown')
    return {'status':'EXACT_CID_STOPPED_NOT_RETIRED','container_id':cid,'terminal_state':info['State'],
            'containment_calls':state.calls,'lease_retained':True,'current_free':False,
            'physical_retirement_accepted':False}


class SDK13ImageOwner:
    def __init__(self,request,validator,signals):
        self.request=request;self.validator=validator;self.signals=signals
    def run(self):
        r=self.request
        _fail('physical_acceptance' not in r,'SDK13 launch request must not contain future physical acceptance')
        _fail(os.getuid()==os.geteuid()==os.getgid()==os.getegid()==1000,'SDK13 ordinary owner required')
        authority=_sdk13_authorize(r)
        bound=self.validator.validate(r,profile_path=SDK13_PROFILE_PATH,request_path=SDK13_REQUEST_PATH,
                                      source_map_path=Path(r['source_map_path']))
        _sdk13_set_profile(r,bound)
        _sdk13_read(SDK13_DRIVER,2**20,SDK13_DRIVER_SHA)
        self.validator.revalidate(bound,r)
        _fail(_sdk13_authorize(r)==authority,'SDK13 authority identity drift before lease')
        os.mkdir(Path(bound['owner_evidence']),0o700)
        _fsync_dir(Path(bound['owner_evidence']).parent)
        try:
            _sdk13_capture_daemon('prelease',bound['owner_evidence'],authority['daemon'],r,authority,self.signals)
            _fail(_sdk13_authorize(r)==authority,'SDK13 authority changed after prelease daemon read')
        except BaseException as exc:
            _exclusive_json(Path(bound['owner_evidence'])/'prelease-daemon-error.json',
                            {'status':'UNKNOWN_PRELEASE_DAEMON_CAPTURE','error':type(exc).__name__+': '+str(exc),
                             'native_guest_or_heavy_release':False})
            raise
        lease=CompileLease(r)
        try: lease.acquire()
        except BaseException as exc:
            _exclusive_json(Path(bound['owner_evidence'])/'prelease-error.json',
                            {'status':'UNKNOWN_PRECREATE_LEASE_ACQUISITION',
                             'error':type(exc).__name__+': '+str(exc),'native_guest_or_heavy_release':False})
            raise
        receipt={'scope':'Functional McKernel OS/apps and Rust/assembly migration only; no security testing.',
                 'operation':SDK13_OPERATION,'profile_sha256':SDK13_PROFILE_SHA,
                 'owner_sha256':_sha256(Path(__file__)),'driver_sha256':SDK13_DRIVER_SHA,
                 'validator_sha256':SDK13_VALIDATOR_SHA,'container_name':COMPILE_PROFILE['container_name'],
                 'owner_nonce':COMPILE_PROFILE['owner_nonce'],'status':'FAIL','container_id':None,'retired':False,
                 'container_absence_confirmed':False,'all_docker_clients_joined':False,
                 'lease_retained_for_root_acceptance':True,'native_guest_or_heavy_release':False,
                 'compile_lease':lease.record,'request_core_sha256':_request_core_hash(r)}
        attempted=False;client=None
        try:
            receipt['work_created_identity']=_sdk13_prepare_work(bound,r,self.validator)
            Path(bound['attempt']).mkdir(mode=0o700); _fsync_dir(Path(bound['owner_evidence']))
            client=_HOST_OWNER.Docker(Path(bound['attempt'])/'docker.log',self.signals,sudo=True,
                    effect_gate=lambda args:_sdk13_effect_gate(r,authority,self.signals,'docker-'+args[0]))
            image_rows=client.call(['image','inspect','--format','{{json .Id}}\n{{json .Architecture}}',SDK13_IMAGE],timeout=30).stdout.splitlines()
            _fail(len(image_rows)==2 and json.loads(image_rows[0])==SDK13_IMAGE and
                  json.loads(image_rows[1])=='amd64','SDK13 image identity differs')
            manifest=_sdk13_manifest(bound,r)
            receipt['mount_manifest_sha256']=manifest['sha256']
            self.validator.revalidate(bound,r)
            _sdk13_revalidate_manifest(bound,manifest)
            _fail(_sdk13_authorize(r)==authority,'SDK13 authority changed before create')
            _sdk13_capture_daemon('pre-create',bound['owner_evidence'],authority['daemon'],r,authority,self.signals)
            _fail(_sdk13_authorize(r)==authority,'SDK13 authority changed after pre-create daemon read')
            args,mounts,command=_sdk13_create_args(bound,r,manifest)
            _fail(not client.client_retirement_unproven,'SDK13 precreate client retirement unknown')
            attempted=True;created=client.call(args);cid=created.stdout.strip()
            _fail(re.fullmatch(r'[0-9a-f]{64}',cid or ''),'SDK13 create CID missing')
            receipt['container_id']=cid;info=_own_inspect(client,cid)
            _check_profile(info,SDK13_IMAGE,COMPILE_PROFILE['owner_nonce'],mounts=mounts,
                           command=command,user='1000:1000',host_owner=_HOST_OWNER)
            _fail(info.get('sdk13_environment_matches') is True,'SDK13 container environment differs')
            self.validator.revalidate(bound,r)
            _sdk13_revalidate_manifest(bound,manifest)
            _fail(_sdk13_authorize(r)==authority,'SDK13 authority changed before start')
            _sdk13_capture_daemon('pre-start',bound['owner_evidence'],authority['daemon'],r,authority,self.signals)
            _fail(_sdk13_authorize(r)==authority,'SDK13 authority changed after pre-start daemon read')
            _fail(not client.client_retirement_unproven,'SDK13 prestart client retirement unknown')
            client.call(['start',cid]);waited=client.call(['wait',cid],timeout=r['timeout'])
            receipt['exit_code']=int(waited.stdout.strip());_fail(receipt['exit_code']==0,'SDK13 driver failed')
            receipt['outputs']=_sdk13_driver_result(bound,r,manifest)
            self.validator.revalidate(bound,r);receipt['status']='PASS'
        except BaseException as exc:
            receipt['error']=type(exc).__name__+': '+str(exc)
        finally:
            if self.signals:self.signals.cleaning=True
            if attempted and client is not None:
                cid=receipt.get('container_id')
                if cid is None:
                    receipt.update(status='FAIL',cleanup_error='UNKNOWN: create produced no authenticated CID; no containment attempted')
                else:
                    try:receipt.update(_cleanup_owned_compile(client,Path(bound['attempt']),cid))
                    except BaseException as exc:
                        receipt.update(status='FAIL',cleanup_error=type(exc).__name__+': '+str(exc))
                        try:
                            receipt['bounded_containment']=_sdk13_contain_created(r,authority,lease,cid,
                                                                                 Path(bound['attempt']),self.signals)
                        except BaseException as containment_error:
                            receipt['containment_error']=type(containment_error).__name__+': '+str(containment_error)
            else:receipt['no_container_create_attempted']=True
            try:self.validator.revalidate(bound,r)
            except BaseException as exc:receipt.update(status='FAIL',input_revalidation_error=type(exc).__name__+': '+str(exc))
            if self.signals and self.signals.requested is not None:receipt.update(status='FAIL',interrupted_signal=self.signals.requested)
            receipt['finished_at']=time.time()
            _exclusive_json(Path(bound['owner_evidence'])/OWNER_RECEIPT_NAME,receipt)
        return receipt



def _sdk13_retirement_controls(acceptance):
    # A separate, fresh root operation release is required for HOST lease retirement.
    _fail(acceptance.get('release_action_authorized') is True and
          acceptance.get('service_status')=='NO_NEW_REJECTION' and acceptance.get('paid_fallback') is False and
          type(acceptance.get('weekly_used_percent')) in (int,float) and
          0<=acceptance['weekly_used_percent']<100, 'SDK13 retirement service or billing unknown')
    now=time.time(); bt=time.clock_gettime(time.CLOCK_BOOTTIME); mono=time.monotonic()
    _fail(type(acceptance.get('weekly_observed_utc')) in (int,float) and
          0<=now-acceptance['weekly_observed_utc']<=30 and
          type(acceptance.get('expiry_utc')) in (int,float) and now<acceptance['expiry_utc']<=SDK13_UTC and
          now<SDK13_UTC and bt<SDK13_BOOT and mono<SDK13_MONO and
          Path('/proc/sys/kernel/random/boot_id').read_text().strip()==SDK13_BOOT_ID,
          'SDK13 retirement usage or time expired')
    rows=[]
    for path,key in ((SDK13_CONTROL,'controls_sha256'),(SDK13_CAPACITY,'capacity_sha256')):
        digest=acceptance.get(key);_fail(isinstance(digest,str),'SDK13 retirement controls missing')
        raw,identity=_sdk13_read(path,2**20,digest);doc=json.loads(raw)
        _fail(doc.get('caps')=={'boot_deadline':SDK13_BOOT,'boot_id':SDK13_BOOT_ID,'deadline':SDK13_UTC,
                                'monotonic_deadline':SDK13_MONO},'SDK13 retirement control caps mismatch')
        rows.append(identity)
    ref=acceptance.get('daemon_retirement_evidence')
    proof,identity=_sdk13_ref(ref)
    _fail(proof.get('status')=='PASS_SEPARATE_FRESH_DAEMON_RETIREMENT_CAPTURE' and
          type(proof.get('observed_utc')) in (int,float) and 0<=now-proof['observed_utc']<=30,
          'SDK13 separate retirement daemon evidence missing or expired')
    daemon=_sdk13_check_daemon_capture(proof.get('outer_join'),proof.get('parent_record'),acceptance.get('daemon'))
    before=int(_proc_starttime(daemon['pid']));sock=os.stat('/var/run/docker.sock');after=int(_proc_starttime(daemon['pid']))
    _fail(before==after==daemon['starttime'] and stat.S_ISSOCK(sock.st_mode) and
          (sock.st_dev,sock.st_ino)==(daemon['socket_device'],daemon['socket_inode']),
          'SDK13 retirement daemon/socket continuity differs')
    return rows,(identity,daemon)

def _sdk13_release_accepted_lease(request,validator,signals):
    _fail(os.getuid()==os.geteuid()==os.getgid()==os.getegid()==1000,'SDK13 ordinary release owner required')
    core_request={k:v for k,v in request.items() if k!='physical_acceptance'}
    # The initial validator correctly requires a fresh, absent work/evidence
    # namespace; it cannot be reused after the operation has produced evidence.
    # Physical acceptance binds the exact already-existing receipt and lease.
    bound={'work':SDK13_WORK,'owner_evidence':SDK13_DIR/'sdk13-data32-owner-evidence-1',
           'attempt':SDK13_DIR/'sdk13-data32-owner-evidence-1/attempt',
           'lease':SDK13_DIR/'sdk13-data32-owner-evidence-1/compile-lease.json'}
    _fail(core_request.get('work_root')==str(bound['work']) and
          core_request.get('owner_evidence_root')==str(bound['owner_evidence']) and
          core_request.get('attempt_root')==str(bound['attempt']),
          'SDK13 existing release paths differ')
    _sdk13_set_profile(core_request,bound)
    acceptance,acceptance_identity=_sdk13_root(request.get('physical_acceptance'),SDK13_ACCEPTANCE)
    _fail(acceptance.get('status')=='ACCEPTED_COMPILE_ONLY_PHYSICAL_RETIREMENT' and
          acceptance.get('operation')==SDK13_OPERATION and acceptance.get('profile_sha256')==SDK13_PROFILE_SHA and
          acceptance.get('owner_sha256')==_sha256(Path(__file__)) and
          acceptance.get('request_core_sha256')==_request_core_hash(core_request) and
          acceptance.get('owner_and_controller_joined') is True and
          acceptance.get('all_owned_client_identities_retired') is True,
          'SDK13 physical acceptance missing or differs')
    receipt_path=_safe_regular(Path(bound['owner_evidence'])/OWNER_RECEIPT_NAME,'SDK13 owner receipt')
    _fail(acceptance.get('owner_receipt_sha256')==_sha256(receipt_path),'SDK13 receipt changed')
    receipt=_load_json(receipt_path,'SDK13 owner receipt')
    _fail(receipt.get('retired') is True and receipt.get('container_absence_confirmed') is True and
          receipt.get('all_docker_clients_joined') is True and receipt.get('operation')==SDK13_OPERATION and
          receipt.get('request_core_sha256')==_request_core_hash(core_request),'SDK13 physical retirement missing')
    retirement_authority=_sdk13_retirement_controls(acceptance)
    cid=receipt.get('container_id');client=_HOST_OWNER.Docker(Path(bound['attempt'])/'lease-release-docker.log',signals,sudo=True,
        effect_gate=lambda args:_sdk13_retirement_effect_gate(request,acceptance_identity,retirement_authority,signals,args[0]))
    absence=_own_absence(client,cid)
    _fail(not client.client_retirement_unproven,'SDK13 lease release client retirement unknown')
    _fail(_sdk13_retirement_controls(acceptance)==retirement_authority,
          'SDK13 retirement authority or daemon changed')
    lease=CompileLease(core_request);stored=_load_json(lease.path,'SDK13 compile lease')
    for key in ('schema','operation','request_core_sha256','profile_sha256','container_name','owner_nonce'):
        _fail(stored.get(key)==lease.record[key],'SDK13 accepted lease binding differs')
    lease.record=stored; lease.load_owned()
    _exclusive_json(Path(bound['attempt'])/'accepted-lease-release-intent.json',
                    {'operation':SDK13_OPERATION,'acceptance':acceptance,'fresh_own_absence':absence,
                     'lease_sha256':hashlib.sha256(lease.load_owned()).hexdigest()})
    unlink_boundary=lease.release_accepted(acceptance,unlink_gate=lambda:
        _sdk13_retirement_effect_gate(request,acceptance_identity,retirement_authority,signals,'lease-unlink'))
    result={'unlink_boundary':unlink_boundary,'status':'PASS_SDK13_COMPILE_ONLY_LEASE_RELEASED','container_id':cid,
            'fresh_own_absence':absence,'native_guest_or_heavy_release':False}
    _exclusive_json(Path(bound['attempt'])/'accepted-lease-release-result.json',result)
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description="Functional McKernel OS/apps and Rust/assembly migration only; no security testing. SDK13 compile owner.")
    parser.add_argument("action", choices=("run", "release-accepted-lease"))
    parser.add_argument("request", type=Path)
    args = parser.parse_args(argv)
    request = json.loads(args.request.read_text())
    validator = _sdk13_module()
    if args.action == "release-accepted-lease":
        with Signals() as signals:
            result = _sdk13_release_accepted_lease(request,validator,signals)
        print(json.dumps(result,sort_keys=True))
        return 0
    with Signals() as signals:
        result=SDK13ImageOwner(request,validator,signals).run()
    print(json.dumps(result,sort_keys=True))
    return 0 if result.get('status')=='PASS' and result.get('retired') is True else 1


if __name__ == "__main__":
    raise SystemExit(main())
