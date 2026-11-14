#!/usr/bin/env python3
"""Reviewed owner for one isolated current-source McKernel image build.

This module is an admission/transport boundary around the offline image
driver.  It does not relocate sources, install software, or perform a guest
operation.  A real invocation creates exactly one private, read-only-root
container under the reviewed 4 CPU/12 GiB lease; tests inject a fake Docker
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


REQUEST_SCHEMA = "mckernel.native-exact-mckernel-image-container-request.v1"
RECEIPT_SCHEMA = "mckernel.native-exact-mckernel-image-container-receipt.v1"
OWNER_RECEIPT_NAME = "owner-receipt.json"
EXPECTED_DRIVER_SHA256 = '961393ed21085c446320c56d033c519b1a8af6d2d019a3ebcf41f7bb7651cc1d'
EXPECTED_RETAINED_COPY_BINDING_SHA256 = 'e9e23e3777db038aaf57112fe65bd6ebc878c6f5e70d20e0bb75a83c758f3d6a'
EXPECTED_PROVENANCE_SHA256 = '7b0b064b1b23d93e962da50043b3d864c844aab160e1f3220d40f898376ee272'
EXPECTED_HOST_OWNER_SHA256 = "96d17547bfc71454d54e95a705138cc9b26faa1e2cafc34105c9ed8d5a68f4d1"
EXPECTED_HEAVY_ENTRY_CONTRACT_SHA256 = "c252ee341eb61752704f8b818503c0a5dc97400845494707ca3110f5f23df6d1"
# The image owner advances with the image-candidate namespace.  Keep consumed
# exclusions explicit: accepting one of these would allow a request to race a
# retired build candidate.  Tests may replace COMMON_EXCLUSION with a private
# fixture, so the rejection list remains separate from the active value.
COMMON_EXCLUSION = '/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-18-current289-union-source-1/qualified-getsiginfo-current290-successor-1/default-image-current290-coherent-overlay-source-1/authenticated-materialization-and-entry-source-1/image-receipt-identity-successor-source-1/actual-current290-default-image-attempt-3/common-exclusion.json'
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

RETIRED_COMMON_EXCLUSIONS = RETIRED_COMMON_EXCLUSIONS | frozenset(('/home/holden/mckernel-work/host-preparation/compute-idle-rust-cutover-20261023-1/production-combined-14/default-image-preparation-1/next-build-preparation-1/pinned-full-image-attempt-1/common-exclusion.json',))

RETIRED_COMMON_EXCLUSIONS = RETIRED_COMMON_EXCLUSIONS | frozenset(('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-10/m14-union2-default-image-preparation-1/normal-heavy-build-preparation-1/provenance-authority-correction-1/pinned-full-image-attempt-1/common-exclusion.json',))

LIMITS = {
    "NanoCpus": 4_000_000_000, "CpusetCpus": "2-5",
    "Memory": 12 * 2**30, "MemorySwap": 12 * 2**30,
    "PidsLimit": 512, "NetworkMode": "none",
}
RETIRED_COMMON_EXCLUSIONS = RETIRED_COMMON_EXCLUSIONS | frozenset(('/home/holden/mckernel-work/host-preparation/compute-idle-rust-cutover-20261023-1/production-combined-15/default-image-preparation-1/next-build-preparation-1/pinned-full-image-attempt-1/common-exclusion.json',))

RESOURCE_ARGS = ("--cpus=4", "--cpuset-cpus=2-5", "--memory=12g",
                 "--memory-swap=12g", "--pids-limit=512")
MAX_TIMEOUT = 19_800
LAUNCHER_AGGREGATE_GIB = "22.0485"
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


def _load_heavy_entry_contract(path=None, expected_sha256=None):
    """Execute the authenticated regular-file bytes of the shared contract.

    Importlib is deliberately avoided: a loader may consult a cache or follow
    a changed path after authentication.  The path and identity are checked
    both before and after the single byte read, then those exact bytes are
    compiled and executed.
    """
    path = (Path('/home/holden/mckernel-work/host-preparation/four-callback-affinity-image-preparation-20261019-1/adapters/native_rust_exact_disk_build_wrapper.py')
            if path is None else Path(path))
    expected_sha256 = (EXPECTED_HEAVY_ENTRY_CONTRACT_SHA256
                       if expected_sha256 is None else expected_sha256)
    if not (path.is_absolute() and path.is_file() and not path.is_symlink()):
        raise OwnerError("shared heavy-entry contract is not a regular source file")
    current = Path(path.anchor)
    for component in path.parts[1:]:
        current /= component
        if current.is_symlink():
            raise OwnerError("shared heavy-entry contract has symlink parent")
    before = os.lstat(path)
    data = path.read_bytes()
    after = os.lstat(path)
    identity = lambda row: (row.st_dev, row.st_ino, row.st_size, row.st_mode)
    if identity(before) != identity(after):
        raise OwnerError("shared heavy-entry contract identity changed during import")
    if hashlib.sha256(data).hexdigest() != expected_sha256:
        raise OwnerError("shared heavy-entry contract hash mismatch")
    module = types.ModuleType("_mckernel_exact_heavy_entry_contract")
    module.__file__ = str(path)
    module.__package__ = ""
    exec(compile(data, str(path), "exec"), module.__dict__)
    return module


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


_HOST_OWNER_PATH = Path('/home/holden/mckernel-work/host-preparation/four-callback-affinity-image-preparation-20261019-1/adapters/native_rust_exact_build_container_owner.py')
_HOST_OWNER = _load_reviewed_host_owner(
    _HOST_OWNER_PATH, EXPECTED_HOST_OWNER_SHA256,
    Path('/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-18-current289-union-source-1/qualified-getsiginfo-current290-successor-1/default-image-current290-coherent-overlay-source-1/authenticated-materialization-and-entry-source-1/native_rust_exact_build_offline.CURRENT290-IHK3114.SOURCE-ONLY.py'), EXPECTED_PROVENANCE_SHA256)


RETIRED_COMMON_EXCLUSIONS = RETIRED_COMMON_EXCLUSIONS | frozenset(('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261024-2/m14-f02-contract-source-1/retained-validation-queue-source-1/retained-validation-attempt-1/common-exclusion.json',))

class OwnerError(RuntimeError):
    pass


_SHARED_HEAVY_ENTRY_CONTRACT = _load_heavy_entry_contract()


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
    # A source-free tool image retains its own preparation candidate identity.
    # The current source candidate is independently authenticated by _validate_request.
    image_candidate = request.get("image_receipt_candidate_sha")
    _fail(isinstance(image_candidate, str) and
          re.fullmatch(r"[0-9a-f]{40}", image_candidate),
          "image receipt candidate identity binding")
    _fail(document.get("status") == "PASS" and document.get("image_id") == request["image_id"] and
          document.get("candidate_sha") == image_candidate and
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
          "launcher aggregate must be exactly 22.0485 GiB")
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


class CommonExclusion:
    def __init__(self, path, request):
        self.path = Path(path); self.request = request; self.record = None

    def acquire(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.record = {"schema": "mckernel.native-exact-operational-exclusion.v1",
                       "pid": os.getpid(), "starttime": _proc_starttime(os.getpid()),
                       "boot_id": Path("/proc/sys/kernel/random/boot_id").read_text().strip(),
                       "request_sha256": hashlib.sha256(json.dumps(self.request, sort_keys=True).encode()).hexdigest()}
        try:
            fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError as exc:
            raise OwnerError("common exclusion exists; reconciliation required") from exc
        identity = os.fstat(fd)
        self.record.update({"dev": identity.st_dev, "inode": identity.st_ino})
        payload = (json.dumps(self.record, sort_keys=True) + "\n").encode()
        offset = 0
        try:
            while offset < len(payload):
                written = os.write(fd, payload[offset:])
                _fail(isinstance(written, int) and written > 0, "common exclusion short write")
                offset += written
            os.fsync(fd)
        finally:
            os.close(fd)
        _fsync_dir(self.path.parent)


def _check_profile(info, image, nonce, mounts=None, command=None, user=None,
                   host_owner=None):
    (host_owner or _HOST_OWNER).check_profile(info, image, nonce)
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


class ImageOwner:
    def __init__(self, request, docker=None, signals=None):
        self.request = dict(request); self.docker = docker; self.signals = signals

    def validate(self):
        self.bound = _validate_request(self.request)
        _fail(os.geteuid() != 0, "owner must be unprivileged")
        return self.bound

    def run(self):
        r = self.request
        # Shared admission must precede validation because validation performs
        # authenticated host measurement.  If anything after this acquisition
        # fails, the token is intentionally retained for recovery/review.
        shared_lock, shared_record = _SHARED_HEAVY_ENTRY_CONTRACT.acquire_heavy_operation(
            r, "image")
        bound = self.validate()
        evidence = bound["evidence"]
        _revalidate_inputs(bound, r)
        host_owner = bound["host_owner"]
        name = "mckernel-image-" + uuid.uuid4().hex
        nonce = uuid.uuid4().hex
        common = CommonExclusion(r["common_exclusion_path"], r)
        common.acquire()
        # No output/evidence mutation occurs until the shared heavy-build
        # exclusion is durably owned.  A stale common lock therefore fails
        # before creating a misleading fresh output namespace.
        # The driver must see absent output/evidence directories.  Only their
        # already-existing parent is mounted; the driver creates the fresh
        # child roots inside that parent.
        bound["attempt"].mkdir(mode=0o700)
        _fsync_dir(bound["owner_evidence"])
        _fsync_dir(evidence.parent); _fsync_dir(bound["output"].parent)
        lease = host_owner.Lease(bound["lease"], name); lease.acquire()
        docker = self.docker or host_owner.Docker(bound["attempt"] / "docker.log", self.signals, sudo=True)
        receipt = {"schema": RECEIPT_SCHEMA, "status": "FAIL", "candidate_sha": r["candidate_sha"],
                   "ihk_sha": r["ihk_sha"], "container_name": name, "owner_nonce": nonce,
                   "cleanup_separately_required": True, "terminal_container_retained": False,
                   "terminal_container_info": None, "terminal_container_info_current": False,
                   "shared_heavy_operation": {"kind": "image", "path": str(shared_lock),
                                              "record": shared_record}}
        if r.get('source_derivative_sha256') is not None:
            receipt.update(candidate_identity_scope='base_git_commit_only',
                           source_derivative_sha256=r['source_derivative_sha256'],
                           materialization_sha256=r['materialization_sha256'])
        attempted = False
        try:
            image = json.loads(docker.call(["image", "inspect", r["image_id"]]).stdout)[0]
            _fail(image.get("Id") == r["image_id"] and image.get("Architecture") == "amd64",
                  "container image identity mismatch")
            mounts = [(bound["source"], "/src", True), (bound["manifest"], "/inputs.json", True),
                      (bound["toolchain"], "/toolchain.json", True), (bound["driver"], "/driver.py", True),
                      (bound["provenance"], "/native_rust_exact_build_offline.py", True),
                      (bound["output"].parent, "/work", False)]
            if bound.get("gitlink_manifest") is not None:
                mounts.insert(2, (bound["gitlink_manifest"], "/libdwarf-inputs.json", True))
                mounts.insert(3, (bound["gitlink_root"], "/src/executer/user/lib/libdwarf/libdwarf", True))
            # v2 translates the complete host build output to /out.  It is a
            # single read-only mount: never mount /build separately or copy
            # and rewrite closure bytes.
            if bound["toolchain_schema"].endswith(".v2"):
                mount_roots = [(root, target) for target, root in bound["mounts_by_target"].items()]
            else:
                mount_roots = [(root, str(root)) for root in bound["roots"] + [bound["kernel"]]]
            for root, target in mount_roots:
                row = (root, target, True)
                if row not in mounts: mounts.append(row)
            rw_mounts = [(source, target) for source, target, readonly in mounts if not readonly]
            _fail(rw_mounts == [(bound["work"], "/work")],
                  "dedicated work root is not sole RW mount")
            args = ["create", "--name", name, "--label", "mckernel.owner=" + nonce, "--init",
                    "--network=none", "--ipc=private", *RESOURCE_ARGS, "--user", "%d:%d" % (os.getuid(), os.getgid()),
                    "--cap-drop=ALL", "--security-opt=no-new-privileges", "--read-only",
                    "--tmpfs", "/tmp:rw,nodev,nosuid,size=256m"]
            for source, target, readonly in mounts:
                args += ["--mount", "type=bind,src=" + str(source) + ",dst=" + target +
                         (",readonly" if readonly else "")]
            command = ["/driver.py", "--source-root", "/src",
                       "--candidate-sha", r["candidate_sha"], "--ihk-sha", r["ihk_sha"],
                       "--manifest", "/inputs.json", "--toolchain", "/toolchain.json",
                       "--output", "/work/" + bound["output"].name,
                       "--evidence", "/work/" + evidence.name, "--jobs", str(r["jobs"]),
                       "--timeout", str(r["timeout"])]
            if bound.get("gitlink_manifest") is not None:
                command += ["--gitlink-manifest", "/libdwarf-inputs.json"]
            if r.get("native_fork_owned_transaction", False):
                command += ["--native-fork-owned-transaction"]
            args += ["--entrypoint", "/usr/bin/python3", r["image_id"], *command]
            attempted = True
            created = docker.call(args); receipt["container_id"] = created.stdout.strip()
            info = host_owner.inspect(docker, name)
            _check_profile(info, r["image_id"], nonce, mounts=mounts, command=command,
                           user="%d:%d" % (os.getuid(), os.getgid()), host_owner=host_owner)
            # The admission measurement is only a lower bound.  Rebind the
            # lease to a fresh host/scratch measurement immediately before
            # Docker start so a concurrent allocation cannot slip between
            # validation and execution.
            latest = host_owner.measure(
                r["disk_admission"]["host_root"],
                r["disk_admission"]["scratch_root"],
                16 * 2**30, 12 * 2**30, source_root=bound["source"],
                output_root=bound["work"], memory_allocation_roots=bound["allocation_roots"])
            _fail(latest.get("memory_allocation_memory_backed_bytes") ==
                  r["memory_backed_bytes"], "pre-start memory allocation changed")
            _fail(latest.get("aggregate_memory_required") ==
                  r["aggregate_memory_required"], "pre-start aggregate memory changed")
            receipt["pre_start_measurement"] = latest
            docker.call(["start", name]); waited = docker.call(["wait", name], timeout=r["timeout"])
            receipt["exit_code"] = int(waited.stdout.strip())
            _fail(receipt["exit_code"] == 0, "offline image driver failed")
            receipt_path = _safe_regular(evidence / "receipt.json", "driver receipt")
            build_receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            _validate_driver_result(evidence, bound["output"], build_receipt, r)
            _revalidate_inputs(bound, r)
            receipt["status"] = "PASS"
        except BaseException as exc:
            receipt["error"] = str(exc)
        finally:
            if self.signals: self.signals.cleaning = True
            if attempted:
                try:
                    receipt["terminal_container_info"] = host_owner.retire(docker, name, nonce)
                    receipt["terminal_container_retained"] = True
                    receipt["retired"] = True
                except BaseException as exc:
                    receipt["status"] = "FAIL"; receipt["retirement_error"] = str(exc); receipt["retired"] = False
                try:
                    logs = docker.call(["logs", name], check=False)
                    _fail(logs.returncode == 0, "Docker logs command failed")
                    _exclusive_text(bound["attempt"] / "container.log", logs.stdout + logs.stderr)
                except BaseException as exc:
                    receipt["status"] = "FAIL"; receipt["capture_error"] = str(exc)
                if getattr(docker, "client_retirement_unproven", False):
                    receipt["status"] = "FAIL"; receipt["retired"] = False
                    receipt["client_retirement_unproven"] = True
            else:
                receipt["retired"] = True
                receipt["cleanup_separately_required"] = False
                receipt["terminal_container_info_current"] = True
            try:
                _revalidate_inputs(bound, r)
            except BaseException as exc:
                receipt["status"] = "FAIL"
                receipt["input_revalidation_error"] = str(exc)
            if self.signals and self.signals.requested is not None:
                receipt["status"] = "FAIL"
                receipt["interrupted_signal"] = self.signals.requested
            receipt["driver_evidence_root"] = str(evidence)
            receipt["owner_evidence_root"] = str(bound["owner_evidence"])
            receipt["attempt_root"] = str(bound["attempt"])
            receipt["common_exclusion_path"] = r["common_exclusion_path"]
            receipt["finished_at"] = time.time()
            _exclusive_json(bound["owner_evidence"] / OWNER_RECEIPT_NAME, receipt)
            if receipt.get("retired"):
                lease.release()
            # The shared contract releases only after a positive PASS,
            # terminal retirement, and sealed evidence.  Any uncertain
            # container, observer, or evidence state deliberately retains it
            # for explicit reconciliation.
            _SHARED_HEAVY_ENTRY_CONTRACT._release_exclusion(
                shared_lock, shared_record, receipt)
        return receipt


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("request", type=Path)
    args = parser.parse_args(argv)
    with Signals() as signals:
        result = ImageOwner(json.loads(args.request.read_text()), signals=signals).run()
    print(json.dumps(result, sort_keys=True))
    return 0 if result.get("status") == "PASS" else 1





_REUSE_FIXED = json.loads('{"archive": {"bytes": 8509594, "path": "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/current290-default-link-failure-retention-1/CURRENT290-DEFAULT-FINAL-LINK-FAILURE-FULL-BUILD-AND-OWNER.tar.gz", "sha256": "eba7d942852d3fd938aaa79fea62da1412db00da06013a1a2933e3eca2627ea5"}, "base_manifest": {"bytes": 35830378, "path": "/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-18-current289-union-source-1/qualified-getsiginfo-current290-successor-1/default-image-current290-coherent-overlay-source-1/authenticated-materialization-and-entry-source-1/source-inputs.CURRENT290-QUALIFIED-IHK3114.json", "sha256": "3a0653623cc1cdb7ebb0e217274ded31ea8fea5068140af4884c273b493b5018"}, "base_materialization_receipt": {"bytes": 17922, "path": "/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-18-current289-union-source-1/qualified-getsiginfo-current290-successor-1/default-image-current290-coherent-overlay-source-1/authenticated-materialization-and-entry-source-1/ACTUAL-CURRENT290-SOURCE-MATERIALIZATION-AND-EXACT-SIX-READBACK.NOT-BUILD-ACCEPTANCE.json", "sha256": "e2699ae5da9b37f541aa6c27f50b8a2cdfb8a038cde44770309de617591594f9"}, "base_source_root": "/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-18-current289-union-source-1/qualified-getsiginfo-current290-successor-1/default-image-current290-coherent-overlay-source-1/authenticated-materialization-and-entry-source-1/source-materialization-current290-ihk3114-attempt-1/materialized-source", "candidate_sha": "eb3ce544eb1f479a56933a5c7fa8300ab6dfe533", "commands": {"Rust_actual_default_command": "cd /work/output/build/kernel && /usr/bin/cmake -E env MAKEFLAGS= MCKERNEL_RUST_VERSION=1.8.0 MCKERNEL_RUST_BUILDID=3114d9e MCKERNEL_X86_ENABLE_SSE=1 MCKERNEL_CPU_C_FILE=/src/arch/x86_64/kernel/cpu.c /nightly/bin/rustc --crate-name mckernel_rust --crate-type lib --edition=2021 -C panic=abort -C opt-level=2 -C debuginfo=2 -C code-model=large -C relocation-model=static -C no-redzone=yes -C force-frame-pointers=yes -C overflow-checks=off -C force-unwind-tables=no -C no-vectorize-loops -C no-vectorize-slp -C target-feature=-sse,-sse2,-sse3,-ssse3,-sse4.1,-sse4.2,-avx,-avx2,-fma --cfg f03_io_diagnostic_callbacks_candidate --cfg f03_mincore_candidate --cfg f03_move_pages_candidate --cfg f03_sched_bridges_candidate --cfg f03_signal_process_bridges_candidate --cfg f03_dispatch_context_candidate --cfg f03_leaf_callbacks_candidate --cfg native_linux_irq_work_v6_12 --cfg f03_syscall_entry_candidate --cfg f03_futex_atomic_candidate --cfg f03_futex_no_uaccess_candidate --cfg process_global_storage_candidate --cfg f03_syscall_table_candidate --cfg f03_ptrace_entry_candidate --cfg f03_syscall_table_clone3 --cfg enable_profile --cfg enable_perf --cfg enable_rusage --emit=obj=/work/output/build/kernel/rust/mckernel_rust.o /src/kernel/rust/lib.rs", "Rust_actual_default_makefile": {"bytes": 9297, "path": "/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-18-current289-union-source-1/qualified-getsiginfo-current290-successor-1/default-image-current290-coherent-overlay-source-1/authenticated-materialization-and-entry-source-1/image-receipt-identity-successor-source-1/actual-current290-default-image-attempt-3/owner-work/output/build/kernel/CMakeFiles/mckernel_rust_obj.dir/build.make", "sha256": "51a872a778d2b3e914918fab0de573392a645f58509c25b64bcb3c1cb56fe8d5"}, "Rust_codegen_units_1_must_not_be_added": true, "Rust_flags_must_remain_exact": true, "Rust_input_view": "Actual default77rootmodules/79Rustfiles plus3existingexternalfiles+unchangedCPU-Cenv input;2Rustpostimages only; not Source27/31 test bodies/cfgs/ABI appendices.", "additional_required_proof": "Fresh actualdefault-object LOCAL metadata proof for the4Source30loggerattributes, because Source30CGU1 fixture cannot qualify this defaultCGU-absence profile.", "container_cwd": "/work/output/build/kernel", "link_actual_default": {"bytes": 759, "path": "/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-18-current289-union-source-1/qualified-getsiginfo-current290-successor-1/default-image-current290-coherent-overlay-source-1/authenticated-materialization-and-entry-source-1/image-receipt-identity-successor-source-1/actual-current290-default-image-attempt-3/owner-work/output/build/kernel/CMakeFiles/mckernel.img.dir/link.txt", "sha256": "d9d50ed84770a8bff5af2371e19245200d99d61fe3cda28e880bd88e6669e428"}, "link_argv": ["/usr/bin/ld", "-e", "arch_start", "-T", "/work/output/build/kernel/config/smp-x86.lds", "--build-id", "-Map=/work/output/build/kernel/mckernel.img.map", "--dependency-file=CMakeFiles/mckernel.img.dir/link.d", "CMakeFiles/mckernel.img.dir/mem.c.o", "CMakeFiles/mckernel.img.dir/syscall.c.o", "CMakeFiles/mckernel.img.dir/process.c.o", "CMakeFiles/mckernel.img.dir/rust/abi_checks.c.o", "CMakeFiles/mckernel.img.dir/__/arch/x86_64/kernel/context.S.o", "CMakeFiles/mckernel.img.dir/__/arch/x86_64/kernel/cpu.c.o", "CMakeFiles/mckernel.img.dir/__/arch/x86_64/kernel/interrupt.S.o", "CMakeFiles/mckernel.img.dir/__/arch/x86_64/kernel/memory.c.o", "CMakeFiles/mckernel.img.dir/__/arch/x86_64/kernel/syscall.c.o", "CMakeFiles/mckernel.img.dir/__/arch/x86_64/kernel/trampoline.S.o", "rust/mckernel_rust.o", "-o", "mckernel.img"], "link_order_exact": ["CMakeFiles/mckernel.img.dir/mem.c.o", "CMakeFiles/mckernel.img.dir/syscall.c.o", "CMakeFiles/mckernel.img.dir/process.c.o", "CMakeFiles/mckernel.img.dir/rust/abi_checks.c.o", "CMakeFiles/mckernel.img.dir/__/arch/x86_64/kernel/context.S.o", "CMakeFiles/mckernel.img.dir/__/arch/x86_64/kernel/cpu.c.o", "CMakeFiles/mckernel.img.dir/__/arch/x86_64/kernel/interrupt.S.o", "CMakeFiles/mckernel.img.dir/__/arch/x86_64/kernel/memory.c.o", "CMakeFiles/mckernel.img.dir/__/arch/x86_64/kernel/syscall.c.o", "CMakeFiles/mckernel.img.dir/__/arch/x86_64/kernel/trampoline.S.o", "rust/mckernel_rust.o"], "new_objects": ["kernel/rust/mckernel_rust.o", "kernel/CMakeFiles/mckernel.img.dir/process.c.o"], "new_owner_execution_argv": null, "no_other_C_ASM_compile": true, "no_unchanged_SDK_or_MODULES_END_probe_compile": true, "post_link_existing_validators": ["_validate_modules_end_probe on retained exact driver.ko and current exact consumers", "_validate_production_rust_panic_refs on actual full new Rust object", "_validate_image including rawld/link.d/ELF/required native symbols/compile database", "_revalidate_inputs/source/toolchain/seed/overlay hashes and sourceview after compilation"], "process_command_authority": "Actual current290 CMake compile_commands plus exactly the CMake56e3 APPEND property, independently evaluated with real LANGUAGES NONE probes. A reuse receipt must label this explicit oneflag command derivation, never fresh full configure.", "process_command_expected_argv": ["/usr/bin/cc", "-DIHK_IKC_USE_LINUX_WORK_IRQ", "-DIHK_OS_MANYCORE", "-DKERNEL_RAM_VADDR=0xfffffffffe800000", "-DMAP_KERNEL_START=0xfffffffffe800000UL", "-DMCKERNEL_NATIVE_CLONE3", "-DMCKERNEL_NATIVE_CLONE_TID", "-DMCKERNEL_NATIVE_FAULT_FIXUP", "-DMCKERNEL_NATIVE_FUTEX", "-DMCKERNEL_NATIVE_SIGNAL_STACK", "-DMCKERNEL_RUST_ATOMIC_HELPERS", "-DMCKERNEL_RUST_BITOPS", "-DMCKERNEL_RUST_LIST_HELPERS", "-DMCKERNEL_RUST_LOCK_HELPERS", "-DMCKERNEL_RUST_MCS_RWLOCK_HELPERS", "-DMCKERNEL_RUST_MC_RWLOCK_HELPERS", "-DMCKERNEL_RUST_PTE_HELPERS", "-DMCKERNEL_RUST_REFCOUNT_HELPERS", "-DMCKERNEL_RUST_SPINLOCK_HELPERS", "-DPROFILE_ENABLE", "-D__KERNEL__", "-DMCKERNEL_RUST_PROCESS_GLOBAL_STORAGE", "-DMCKERNEL_RUST_PROCESS_HELPERS", "-I/work/output/build/kernel/include", "-I/src/kernel/include", "-I/work/output/build/kernel", "-I/work/output/build", "-I/src/ihk/cokernel/smp/x86_64/include", "-I/src/ihk/cokernel/smp/x86_64", "-I/src/ihk/ikc/include", "-I/src/ihk/linux/include", "-I/src/lib/include", "-I/src/arch/x86_64/kernel/include", "-g", "-Wall", "-Wextra", "-Wno-unused-parameter", "-Wno-sign-compare", "-Wno-unused-function", "-Wno-implicit-fallthrough", "-Wno-stringop-truncation", "-ffreestanding", "-O2", "-nostdinc", "-isystem", "/usr/lib/gcc/x86_64-redhat-linux/14/include", "-fno-omit-frame-pointer", "-mcmodel=large", "-mno-red-zone", "-mno-sse", "-o", "CMakeFiles/mckernel.img.dir/process.c.o", "-c", "/src/kernel/process.c"], "process_command_selected_original": {"command": "/usr/bin/cc -DIHK_IKC_USE_LINUX_WORK_IRQ -DIHK_OS_MANYCORE -DKERNEL_RAM_VADDR=0xfffffffffe800000 -DMAP_KERNEL_START=0xfffffffffe800000UL -DMCKERNEL_NATIVE_CLONE3 -DMCKERNEL_NATIVE_CLONE_TID -DMCKERNEL_NATIVE_FAULT_FIXUP -DMCKERNEL_NATIVE_FUTEX -DMCKERNEL_NATIVE_SIGNAL_STACK -DMCKERNEL_RUST_ATOMIC_HELPERS -DMCKERNEL_RUST_BITOPS -DMCKERNEL_RUST_LIST_HELPERS -DMCKERNEL_RUST_LOCK_HELPERS -DMCKERNEL_RUST_MCS_RWLOCK_HELPERS -DMCKERNEL_RUST_MC_RWLOCK_HELPERS -DMCKERNEL_RUST_PTE_HELPERS -DMCKERNEL_RUST_REFCOUNT_HELPERS -DMCKERNEL_RUST_SPINLOCK_HELPERS -DPROFILE_ENABLE -D__KERNEL__ -DMCKERNEL_RUST_PROCESS_HELPERS -I/work/output/build/kernel/include -I/src/kernel/include -I/work/output/build/kernel -I/work/output/build -I/src/ihk/cokernel/smp/x86_64/include -I/src/ihk/cokernel/smp/x86_64 -I/src/ihk/ikc/include -I/src/ihk/linux/include -I/src/lib/include -I/src/arch/x86_64/kernel/include -g -Wall -Wextra -Wno-unused-parameter -Wno-sign-compare -Wno-unused-function -Wno-implicit-fallthrough -Wno-stringop-truncation -ffreestanding -O2 -nostdinc -isystem /usr/lib/gcc/x86_64-redhat-linux/14/include -fno-omit-frame-pointer -mcmodel=large -mno-red-zone -mno-sse -o CMakeFiles/mckernel.img.dir/process.c.o -c /src/kernel/process.c", "directory": "/work/output/build/kernel", "file": "/src/kernel/process.c", "output": "kernel/CMakeFiles/mckernel.img.dir/process.c.o"}, "process_only_delta": "-DMCKERNEL_RUST_PROCESS_GLOBAL_STORAGE exactlyonce; all other compiler/include/options/source/output tokens identical", "scope": "Functional McKernel OS/apps and Rust/assembly migration only; no security testing.", "status": "SOURCE_ONLY_RECIPE_REQUIRES_MINIMAL_DRIVER_OWNER_EXTENSION_AND_FRESH_RELEASE"}, "configuration": [{"build_relative": "CMakeCache.txt", "retained_archive_member": "docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-18-current289-union-source-1/qualified-getsiginfo-current290-successor-1/default-image-current290-coherent-overlay-source-1/authenticated-materialization-and-entry-source-1/image-receipt-identity-successor-source-1/actual-current290-default-image-attempt-3/owner-work/output/build/CMakeCache.txt", "source": {"bytes": 26772, "path": "/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-18-current289-union-source-1/qualified-getsiginfo-current290-successor-1/default-image-current290-coherent-overlay-source-1/authenticated-materialization-and-entry-source-1/image-receipt-identity-successor-source-1/actual-current290-default-image-attempt-3/owner-work/output/build/CMakeCache.txt", "sha256": "0a76d32d26170bc88370a013dd189af7cd04a342222be2f2f0c03723dee74019"}}, {"build_relative": "compile_commands.json", "retained_archive_member": "docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-18-current289-union-source-1/qualified-getsiginfo-current290-successor-1/default-image-current290-coherent-overlay-source-1/authenticated-materialization-and-entry-source-1/image-receipt-identity-successor-source-1/actual-current290-default-image-attempt-3/owner-work/output/build/compile_commands.json", "source": {"bytes": 74750, "path": "/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-18-current289-union-source-1/qualified-getsiginfo-current290-successor-1/default-image-current290-coherent-overlay-source-1/authenticated-materialization-and-entry-source-1/image-receipt-identity-successor-source-1/actual-current290-default-image-attempt-3/owner-work/output/build/compile_commands.json", "sha256": "8355a2fa83310991bd21d3ddea7106d1e40134f2f90b4f0c5d4eb2e218869139"}}, {"build_relative": "kernel/CMakeFiles/mckernel.img.dir/build.make", "retained_archive_member": "docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-18-current289-union-source-1/qualified-getsiginfo-current290-successor-1/default-image-current290-coherent-overlay-source-1/authenticated-materialization-and-entry-source-1/image-receipt-identity-successor-source-1/actual-current290-default-image-attempt-3/owner-work/output/build/kernel/CMakeFiles/mckernel.img.dir/build.make", "source": {"bytes": 30122, "path": "/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-18-current289-union-source-1/qualified-getsiginfo-current290-successor-1/default-image-current290-coherent-overlay-source-1/authenticated-materialization-and-entry-source-1/image-receipt-identity-successor-source-1/actual-current290-default-image-attempt-3/owner-work/output/build/kernel/CMakeFiles/mckernel.img.dir/build.make", "sha256": "d038ece565cc965f11288eac31da307e56bd3c9ec40e9470f89d0756e1decb2f"}}, {"build_relative": "kernel/CMakeFiles/mckernel.img.dir/flags.make", "retained_archive_member": "docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-18-current289-union-source-1/qualified-getsiginfo-current290-successor-1/default-image-current290-coherent-overlay-source-1/authenticated-materialization-and-entry-source-1/image-receipt-identity-successor-source-1/actual-current290-default-image-attempt-3/owner-work/output/build/kernel/CMakeFiles/mckernel.img.dir/flags.make", "source": {"bytes": 3993, "path": "/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-18-current289-union-source-1/qualified-getsiginfo-current290-successor-1/default-image-current290-coherent-overlay-source-1/authenticated-materialization-and-entry-source-1/image-receipt-identity-successor-source-1/actual-current290-default-image-attempt-3/owner-work/output/build/kernel/CMakeFiles/mckernel.img.dir/flags.make", "sha256": "eb3f8f83cf8fffd7599118c70881f7203bee5e4a68894069212287ea54444b24"}}, {"build_relative": "kernel/CMakeFiles/mckernel.img.dir/link.txt", "retained_archive_member": "docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-18-current289-union-source-1/qualified-getsiginfo-current290-successor-1/default-image-current290-coherent-overlay-source-1/authenticated-materialization-and-entry-source-1/image-receipt-identity-successor-source-1/actual-current290-default-image-attempt-3/owner-work/output/build/kernel/CMakeFiles/mckernel.img.dir/link.txt", "source": {"bytes": 759, "path": "/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-18-current289-union-source-1/qualified-getsiginfo-current290-successor-1/default-image-current290-coherent-overlay-source-1/authenticated-materialization-and-entry-source-1/image-receipt-identity-successor-source-1/actual-current290-default-image-attempt-3/owner-work/output/build/kernel/CMakeFiles/mckernel.img.dir/link.txt", "sha256": "d9d50ed84770a8bff5af2371e19245200d99d61fe3cda28e880bd88e6669e428"}}, {"build_relative": "kernel/CMakeFiles/mckernel_rust_obj.dir/build.make", "retained_archive_member": "docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-18-current289-union-source-1/qualified-getsiginfo-current290-successor-1/default-image-current290-coherent-overlay-source-1/authenticated-materialization-and-entry-source-1/image-receipt-identity-successor-source-1/actual-current290-default-image-attempt-3/owner-work/output/build/kernel/CMakeFiles/mckernel_rust_obj.dir/build.make", "source": {"bytes": 9297, "path": "/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-18-current289-union-source-1/qualified-getsiginfo-current290-successor-1/default-image-current290-coherent-overlay-source-1/authenticated-materialization-and-entry-source-1/image-receipt-identity-successor-source-1/actual-current290-default-image-attempt-3/owner-work/output/build/kernel/CMakeFiles/mckernel_rust_obj.dir/build.make", "sha256": "51a872a778d2b3e914918fab0de573392a645f58509c25b64bcb3c1cb56fe8d5"}}, {"build_relative": "kernel/config/smp-x86.lds", "retained_archive_member": "docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-18-current289-union-source-1/qualified-getsiginfo-current290-successor-1/default-image-current290-coherent-overlay-source-1/authenticated-materialization-and-entry-source-1/image-receipt-identity-successor-source-1/actual-current290-default-image-attempt-3/owner-work/output/build/kernel/config/smp-x86.lds", "source": {"bytes": 915, "path": "/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-18-current289-union-source-1/qualified-getsiginfo-current290-successor-1/default-image-current290-coherent-overlay-source-1/authenticated-materialization-and-entry-source-1/image-receipt-identity-successor-source-1/actual-current290-default-image-attempt-3/owner-work/output/build/kernel/config/smp-x86.lds", "sha256": "b95d62a32abad215818adbde3597fad0607d4d14dddc7fc9adea09d9cd133bbd"}}, {"build_relative": "kernel/include/swapfmt.h", "retained_archive_member": "docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-18-current289-union-source-1/qualified-getsiginfo-current290-successor-1/default-image-current290-coherent-overlay-source-1/authenticated-materialization-and-entry-source-1/image-receipt-identity-successor-source-1/actual-current290-default-image-attempt-3/owner-work/output/build/kernel/include/swapfmt.h", "source": {"bytes": 878, "path": "/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-18-current289-union-source-1/qualified-getsiginfo-current290-successor-1/default-image-current290-coherent-overlay-source-1/authenticated-materialization-and-entry-source-1/image-receipt-identity-successor-source-1/actual-current290-default-image-attempt-3/owner-work/output/build/kernel/include/swapfmt.h", "sha256": "e14e0134c80c2a4bfcda779285b57d46e01a70702eb608fb6b378ff763d90183"}}, {"build_relative": "tmp.resolve_MODULES_END/driver.ko", "retained_archive_member": "docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-18-current289-union-source-1/qualified-getsiginfo-current290-successor-1/default-image-current290-coherent-overlay-source-1/authenticated-materialization-and-entry-source-1/image-receipt-identity-successor-source-1/actual-current290-default-image-attempt-3/owner-work/output/build/tmp.resolve_MODULES_END/driver.ko", "source": {"bytes": 151688, "path": "/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-18-current289-union-source-1/qualified-getsiginfo-current290-successor-1/default-image-current290-coherent-overlay-source-1/authenticated-materialization-and-entry-source-1/image-receipt-identity-successor-source-1/actual-current290-default-image-attempt-3/owner-work/output/build/tmp.resolve_MODULES_END/driver.ko", "sha256": "0c5c6d38362e859db21c28cba14101e8bc62119d4b33f5e38820294196444ff6"}}, {"build_relative": "config.h", "retained_archive_member": "docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-18-current289-union-source-1/qualified-getsiginfo-current290-successor-1/default-image-current290-coherent-overlay-source-1/authenticated-materialization-and-entry-source-1/image-receipt-identity-successor-source-1/actual-current290-default-image-attempt-3/owner-work/output/build/config.h", "source": {"bytes": 1055, "path": "/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-18-current289-union-source-1/qualified-getsiginfo-current290-successor-1/default-image-current290-coherent-overlay-source-1/authenticated-materialization-and-entry-source-1/image-receipt-identity-successor-source-1/actual-current290-default-image-attempt-3/owner-work/output/build/config.h", "sha256": "da78d6a8c94b274adad3159b1cc373b00e5de7fea6cc2ae7955a700078db6b2f"}}], "configuration_mode": "REUSED_CONFIGURATION_DERIVED_CURRENT_DEFAULT_COMMANDS", "fresh_full_configure": false, "fresh_materialization": false, "future_nonce": null, "future_pid": null, "ihk_sha": "3114d9e7101ad52030eb3effa849a5c108972a1f", "members": {"bytes": 829416, "path": "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/current290-default-link-failure-retention-1/MEMBERS.json", "sha256": "f2b65f3ae91ac069f302e6e10c30e07e42957010507372c1dcf483832a71a03a"}, "objects": [{"action": "reuse exact object; no C/ASM compile", "build_relative": "kernel/CMakeFiles/mckernel.img.dir/mem.c.o", "link_token": "CMakeFiles/mckernel.img.dir/mem.c.o", "replace": false, "retained_archive_member": "docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-18-current289-union-source-1/qualified-getsiginfo-current290-successor-1/default-image-current290-coherent-overlay-source-1/authenticated-materialization-and-entry-source-1/image-receipt-identity-successor-source-1/actual-current290-default-image-attempt-3/owner-work/output/build/kernel/CMakeFiles/mckernel.img.dir/mem.c.o", "source": {"bytes": 2848, "path": "/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-18-current289-union-source-1/qualified-getsiginfo-current290-successor-1/default-image-current290-coherent-overlay-source-1/authenticated-materialization-and-entry-source-1/image-receipt-identity-successor-source-1/actual-current290-default-image-attempt-3/owner-work/output/build/kernel/CMakeFiles/mckernel.img.dir/mem.c.o", "sha256": "4b595744494abba0493d75a1475e48b3745e1a668f5575543e81797b994e4f7c"}}, {"action": "reuse exact object; no C/ASM compile", "build_relative": "kernel/CMakeFiles/mckernel.img.dir/syscall.c.o", "link_token": "CMakeFiles/mckernel.img.dir/syscall.c.o", "replace": false, "retained_archive_member": "docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-18-current289-union-source-1/qualified-getsiginfo-current290-successor-1/default-image-current290-coherent-overlay-source-1/authenticated-materialization-and-entry-source-1/image-receipt-identity-successor-source-1/actual-current290-default-image-attempt-3/owner-work/output/build/kernel/CMakeFiles/mckernel.img.dir/syscall.c.o", "source": {"bytes": 397416, "path": "/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-18-current289-union-source-1/qualified-getsiginfo-current290-successor-1/default-image-current290-coherent-overlay-source-1/authenticated-materialization-and-entry-source-1/image-receipt-identity-successor-source-1/actual-current290-default-image-attempt-3/owner-work/output/build/kernel/CMakeFiles/mckernel.img.dir/syscall.c.o", "sha256": "4ae43c42620a929f13f6dc83d628e01bc0186bc33c1c988121bfc2a1299931d4"}}, {"action": "new selected compilation", "build_relative": "kernel/CMakeFiles/mckernel.img.dir/process.c.o", "link_token": "CMakeFiles/mckernel.img.dir/process.c.o", "replace": true, "retained_archive_member": "docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-18-current289-union-source-1/qualified-getsiginfo-current290-successor-1/default-image-current290-coherent-overlay-source-1/authenticated-materialization-and-entry-source-1/image-receipt-identity-successor-source-1/actual-current290-default-image-attempt-3/owner-work/output/build/kernel/CMakeFiles/mckernel.img.dir/process.c.o", "source": {"bytes": 76536, "path": "/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-18-current289-union-source-1/qualified-getsiginfo-current290-successor-1/default-image-current290-coherent-overlay-source-1/authenticated-materialization-and-entry-source-1/image-receipt-identity-successor-source-1/actual-current290-default-image-attempt-3/owner-work/output/build/kernel/CMakeFiles/mckernel.img.dir/process.c.o", "sha256": "385b8d205d119ade76af5e36bae0a6fd893f8ca7518f45d635979a55c61d4678"}}, {"action": "reuse exact object; no C/ASM compile", "build_relative": "kernel/CMakeFiles/mckernel.img.dir/rust/abi_checks.c.o", "link_token": "CMakeFiles/mckernel.img.dir/rust/abi_checks.c.o", "replace": false, "retained_archive_member": "docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-18-current289-union-source-1/qualified-getsiginfo-current290-successor-1/default-image-current290-coherent-overlay-source-1/authenticated-materialization-and-entry-source-1/image-receipt-identity-successor-source-1/actual-current290-default-image-attempt-3/owner-work/output/build/kernel/CMakeFiles/mckernel.img.dir/rust/abi_checks.c.o", "source": {"bytes": 2880, "path": "/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-18-current289-union-source-1/qualified-getsiginfo-current290-successor-1/default-image-current290-coherent-overlay-source-1/authenticated-materialization-and-entry-source-1/image-receipt-identity-successor-source-1/actual-current290-default-image-attempt-3/owner-work/output/build/kernel/CMakeFiles/mckernel.img.dir/rust/abi_checks.c.o", "sha256": "e139686acfa04f6d7576da5656693d13c4235e5beefb7f8ae3c9f7ccf03ea9b0"}}, {"action": "reuse exact object; no C/ASM compile", "build_relative": "kernel/CMakeFiles/mckernel.img.dir/__/arch/x86_64/kernel/context.S.o", "link_token": "CMakeFiles/mckernel.img.dir/__/arch/x86_64/kernel/context.S.o", "replace": false, "retained_archive_member": "docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-18-current289-union-source-1/qualified-getsiginfo-current290-successor-1/default-image-current290-coherent-overlay-source-1/authenticated-materialization-and-entry-source-1/image-receipt-identity-successor-source-1/actual-current290-default-image-attempt-3/owner-work/output/build/kernel/CMakeFiles/mckernel.img.dir/__/arch/x86_64/kernel/context.S.o", "source": {"bytes": 2344, "path": "/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-18-current289-union-source-1/qualified-getsiginfo-current290-successor-1/default-image-current290-coherent-overlay-source-1/authenticated-materialization-and-entry-source-1/image-receipt-identity-successor-source-1/actual-current290-default-image-attempt-3/owner-work/output/build/kernel/CMakeFiles/mckernel.img.dir/__/arch/x86_64/kernel/context.S.o", "sha256": "dce0972b3291f970d49a5fa6d64f25c587423aafa63efc8b47bcfdbdfb679c7a"}}, {"action": "reuse exact object; no C/ASM compile", "build_relative": "kernel/CMakeFiles/mckernel.img.dir/__/arch/x86_64/kernel/cpu.c.o", "link_token": "CMakeFiles/mckernel.img.dir/__/arch/x86_64/kernel/cpu.c.o", "replace": false, "retained_archive_member": "docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-18-current289-union-source-1/qualified-getsiginfo-current290-successor-1/default-image-current290-coherent-overlay-source-1/authenticated-materialization-and-entry-source-1/image-receipt-identity-successor-source-1/actual-current290-default-image-attempt-3/owner-work/output/build/kernel/CMakeFiles/mckernel.img.dir/__/arch/x86_64/kernel/cpu.c.o", "source": {"bytes": 2872, "path": "/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-18-current289-union-source-1/qualified-getsiginfo-current290-successor-1/default-image-current290-coherent-overlay-source-1/authenticated-materialization-and-entry-source-1/image-receipt-identity-successor-source-1/actual-current290-default-image-attempt-3/owner-work/output/build/kernel/CMakeFiles/mckernel.img.dir/__/arch/x86_64/kernel/cpu.c.o", "sha256": "3bed7de9807b6d8e70e87722a11b3d103119203822b9e022ebd0ecbc570bbce1"}}, {"action": "reuse exact object; no C/ASM compile", "build_relative": "kernel/CMakeFiles/mckernel.img.dir/__/arch/x86_64/kernel/interrupt.S.o", "link_token": "CMakeFiles/mckernel.img.dir/__/arch/x86_64/kernel/interrupt.S.o", "replace": false, "retained_archive_member": "docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-18-current289-union-source-1/qualified-getsiginfo-current290-successor-1/default-image-current290-coherent-overlay-source-1/authenticated-materialization-and-entry-source-1/image-receipt-identity-successor-source-1/actual-current290-default-image-attempt-3/owner-work/output/build/kernel/CMakeFiles/mckernel.img.dir/__/arch/x86_64/kernel/interrupt.S.o", "source": {"bytes": 16056, "path": "/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-18-current289-union-source-1/qualified-getsiginfo-current290-successor-1/default-image-current290-coherent-overlay-source-1/authenticated-materialization-and-entry-source-1/image-receipt-identity-successor-source-1/actual-current290-default-image-attempt-3/owner-work/output/build/kernel/CMakeFiles/mckernel.img.dir/__/arch/x86_64/kernel/interrupt.S.o", "sha256": "66bcbec1fc5086cac18a8009f0e1b36ecaba7bf11f38cadd5de9f03e3873ee44"}}, {"action": "reuse exact object; no C/ASM compile", "build_relative": "kernel/CMakeFiles/mckernel.img.dir/__/arch/x86_64/kernel/memory.c.o", "link_token": "CMakeFiles/mckernel.img.dir/__/arch/x86_64/kernel/memory.c.o", "replace": false, "retained_archive_member": "docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-18-current289-union-source-1/qualified-getsiginfo-current290-successor-1/default-image-current290-coherent-overlay-source-1/authenticated-materialization-and-entry-source-1/image-receipt-identity-successor-source-1/actual-current290-default-image-attempt-3/owner-work/output/build/kernel/CMakeFiles/mckernel.img.dir/__/arch/x86_64/kernel/memory.c.o", "source": {"bytes": 2888, "path": "/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-18-current289-union-source-1/qualified-getsiginfo-current290-successor-1/default-image-current290-coherent-overlay-source-1/authenticated-materialization-and-entry-source-1/image-receipt-identity-successor-source-1/actual-current290-default-image-attempt-3/owner-work/output/build/kernel/CMakeFiles/mckernel.img.dir/__/arch/x86_64/kernel/memory.c.o", "sha256": "d3207c7a7844086196676c82d66e6aa4f1233e37b167460e23ba089ec71aca85"}}, {"action": "reuse exact object; no C/ASM compile", "build_relative": "kernel/CMakeFiles/mckernel.img.dir/__/arch/x86_64/kernel/syscall.c.o", "link_token": "CMakeFiles/mckernel.img.dir/__/arch/x86_64/kernel/syscall.c.o", "replace": false, "retained_archive_member": "docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-18-current289-union-source-1/qualified-getsiginfo-current290-successor-1/default-image-current290-coherent-overlay-source-1/authenticated-materialization-and-entry-source-1/image-receipt-identity-successor-source-1/actual-current290-default-image-attempt-3/owner-work/output/build/kernel/CMakeFiles/mckernel.img.dir/__/arch/x86_64/kernel/syscall.c.o", "source": {"bytes": 135464, "path": "/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-18-current289-union-source-1/qualified-getsiginfo-current290-successor-1/default-image-current290-coherent-overlay-source-1/authenticated-materialization-and-entry-source-1/image-receipt-identity-successor-source-1/actual-current290-default-image-attempt-3/owner-work/output/build/kernel/CMakeFiles/mckernel.img.dir/__/arch/x86_64/kernel/syscall.c.o", "sha256": "cea862c3d32ab3dfbc8e39d1da50b6fe324bb0ffcb88476915605ea639b832ed"}}, {"action": "reuse exact object; no C/ASM compile", "build_relative": "kernel/CMakeFiles/mckernel.img.dir/__/arch/x86_64/kernel/trampoline.S.o", "link_token": "CMakeFiles/mckernel.img.dir/__/arch/x86_64/kernel/trampoline.S.o", "replace": false, "retained_archive_member": "docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-18-current289-union-source-1/qualified-getsiginfo-current290-successor-1/default-image-current290-coherent-overlay-source-1/authenticated-materialization-and-entry-source-1/image-receipt-identity-successor-source-1/actual-current290-default-image-attempt-3/owner-work/output/build/kernel/CMakeFiles/mckernel.img.dir/__/arch/x86_64/kernel/trampoline.S.o", "source": {"bytes": 5568, "path": "/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-18-current289-union-source-1/qualified-getsiginfo-current290-successor-1/default-image-current290-coherent-overlay-source-1/authenticated-materialization-and-entry-source-1/image-receipt-identity-successor-source-1/actual-current290-default-image-attempt-3/owner-work/output/build/kernel/CMakeFiles/mckernel.img.dir/__/arch/x86_64/kernel/trampoline.S.o", "sha256": "ebd728290101289164a887deb52dc7977d896e9627a2cb1323fd649db89055c5"}}, {"action": "new selected compilation", "build_relative": "kernel/rust/mckernel_rust.o", "link_token": "rust/mckernel_rust.o", "replace": true, "retained_archive_member": "docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-18-current289-union-source-1/qualified-getsiginfo-current290-successor-1/default-image-current290-coherent-overlay-source-1/authenticated-materialization-and-entry-source-1/image-receipt-identity-successor-source-1/actual-current290-default-image-attempt-3/owner-work/output/build/kernel/rust/mckernel_rust.o", "source": {"bytes": 18045008, "path": "/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-18-current289-union-source-1/qualified-getsiginfo-current290-successor-1/default-image-current290-coherent-overlay-source-1/authenticated-materialization-and-entry-source-1/image-receipt-identity-successor-source-1/actual-current290-default-image-attempt-3/owner-work/output/build/kernel/rust/mckernel_rust.o", "sha256": "5b70e620fbdc5467757f430c8a45328364abfdcca7dfeb91ec9aa4693d7e6506"}}], "postimages": [{"base": {"bytes": 26500, "path": "/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-18-current289-union-source-1/qualified-getsiginfo-current290-successor-1/default-image-current290-coherent-overlay-source-1/authenticated-materialization-and-entry-source-1/source-materialization-current290-ihk3114-attempt-1/materialized-source/kernel/CMakeLists.txt", "sha256": "f54e9093abf7850e3c14afef4932b7ad9e67b92a395cf8e031b8e5366e170b7b"}, "base_mode": 384, "container_destination": "/src/kernel/CMakeLists.txt", "postimage": {"bytes": 26715, "path": "/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-18-current289-union-source-1/qualified-getsiginfo-current290-successor-1/default-image-current290-coherent-overlay-source-1/authenticated-materialization-and-entry-source-1/attempt3-coherent-entry-preparation-source-1/genuine-newbe87-physical-binding-preparation-source-1/actual7553-namespace6294-final-source-1/memory-floor-correction1-source-1/query-packet-pin-correction1-source-1/default290-link-data-selector-correction1-source-1/kernel/CMakeLists.txt", "sha256": "f29336679e462746822d5ce9efe1a74491fbea1f0cbb46d56cfdc48ae082b3cc"}, "postimage_mode": 384, "readonly": true, "relative": "kernel/CMakeLists.txt"}, {"base": {"bytes": 2094, "path": "/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-18-current289-union-source-1/qualified-getsiginfo-current290-successor-1/default-image-current290-coherent-overlay-source-1/authenticated-materialization-and-entry-source-1/source-materialization-current290-ihk3114-attempt-1/materialized-source/kernel/rust/lib.rs", "sha256": "ad7b9f9e66d56f4d6df1d20366ec4697c2448a5930081a944c3b7e78088790ae"}, "base_mode": 384, "container_destination": "/src/kernel/rust/lib.rs", "postimage": {"bytes": 2115, "path": "/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/kernel-syscall/default290-corrected-real-crate-source-1/candidate/kernel/rust/lib.rs", "sha256": "a05908f81b3ecd37d22fa75585525b8a4c8cf8cc9c52be57ea9a86e2ec580680"}, "postimage_mode": 384, "readonly": true, "relative": "kernel/rust/lib.rs"}, {"base": {"bytes": 1227766, "path": "/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-18-current289-union-source-1/qualified-getsiginfo-current290-successor-1/default-image-current290-coherent-overlay-source-1/authenticated-materialization-and-entry-source-1/source-materialization-current290-ihk3114-attempt-1/materialized-source/kernel/rust/syscall_policy.rs", "sha256": "e7d533e6d27d216edfb091f51cbd7705ccde1410ed5d0b2f7efbc8fef4526308"}, "base_mode": 384, "container_destination": "/src/kernel/rust/syscall_policy.rs", "postimage": {"bytes": 1228858, "path": "/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/kernel-syscall/default290-corrected-real-crate-source-1/candidate/kernel/rust/syscall_policy.rs", "sha256": "fefec3eb05be2f714dfeca34310901a566557f82ee08de9b9ad0ef0344f74d62"}, "postimage_mode": 384, "readonly": true, "relative": "kernel/rust/syscall_policy.rs"}], "retention_receipt": {"bytes": 10866, "path": "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/current290-default-link-failure-retention-1/SOURCE-RETENTION.json", "sha256": "67489c39965ef088b497a553cb6ec99044cfd442bc1de96fe7e5be4b944a8137"}, "runtime_authority": null, "schema": "mckernel.current290.readonly-three-postimage-nine-object-reuse.v1", "seed_root": "/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-18-current289-union-source-1/qualified-getsiginfo-current290-successor-1/default-image-current290-coherent-overlay-source-1/authenticated-materialization-and-entry-source-1/image-receipt-identity-successor-source-1/actual-current290-default-image-attempt-3/owner-work/output/build"}')
_REUSE_INPUT_SHA256 = 'c9af4c64ac2b414caf7d78b9a1b467edbf17d0252554d2b4a402a49bfd75a4b8'
_REUSE_INPUT_BYTES = 41994
_REUSE_IDENTITY_BASELINE = {}

def _reuse_require(condition, message):
    if not condition:
        raise RuntimeError('readonly reuse: ' + message)

def _reuse_file(path, expected):
    path = Path(path)
    _reuse_require(not path.is_symlink() and path.is_file(), 'regular input missing: ' + str(path))
    for parent in path.parents:
        _reuse_require(not parent.is_symlink(), 'symlink input parent')
    before = path.stat()
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        opened = os.fstat(stream.fileno())
        _reuse_require((opened.st_dev, opened.st_ino) == (before.st_dev, before.st_ino), 'input identity changed at open')
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
        after_fd = os.fstat(stream.fileno())
    after = path.stat()
    identity = lambda item: (item.st_dev, item.st_ino, item.st_size, item.st_mtime_ns, item.st_ctime_ns, item.st_mode)
    _reuse_require(identity(before) == identity(opened) == identity(after_fd) == identity(after), 'input changed while hashing')
    _reuse_require(after.st_size == expected['bytes'] and digest.hexdigest() == expected['sha256'], 'input bytes/hash differs: ' + str(path))
    baseline = _REUSE_IDENTITY_BASELINE.setdefault(str(path), identity(after))
    _reuse_require(identity(after) == baseline, 'input inode/metadata changed since first authentication')
    return dict(path=str(path), sha256=digest.hexdigest(), bytes=after.st_size, dev=after.st_dev, inode=after.st_ino)

def _reuse_layout(fixed):
    _reuse_require(fixed == _REUSE_FIXED, 'frozen input data differs')
    _reuse_require(len(fixed['postimages']) == 3 and {row['relative'] for row in fixed['postimages']} == {'kernel/CMakeLists.txt', 'kernel/rust/lib.rs', 'kernel/rust/syscall_policy.rs'}, 'three allowed postimages')
    objects = fixed['objects']
    _reuse_require(len(objects) == 11 and len({row['build_relative'] for row in objects}) == 11, '11 unique ordered objects required')
    _reuse_require(sum(not row['replace'] for row in objects) == 9, 'nine reused objects required')
    _reuse_require({row['build_relative'] for row in objects if row['replace']} == {'kernel/CMakeFiles/mckernel.img.dir/process.c.o', 'kernel/rust/mckernel_rust.o'}, 'two replacement objects differ')
    for row in objects + fixed['configuration']:
        path = Path(row['build_relative'])
        _reuse_require(not path.is_absolute() and '..' not in path.parts, 'seed destination escapes')
        _reuse_require(Path(row['source']['path']) == Path(fixed['seed_root']) / path, 'seed original path differs')
    return fixed

def _reuse_authenticate(input_path, *, container=False):
    _reuse_file(input_path, dict(sha256=_REUSE_INPUT_SHA256, bytes=_REUSE_INPUT_BYTES))
    fixed = _reuse_layout(json.loads(Path(input_path).read_text()))
    seed = Path('/seed-build') if container else Path(fixed['seed_root'])
    aliases = {'archive': '/seed-archive.tar.gz', 'members': '/seed-members.json', 'retention_receipt': '/seed-retention.json'}
    proofs = {}
    for key, alias in aliases.items():
        proofs[key] = _reuse_file(alias if container else fixed[key]['path'], fixed[key])
    member_doc = json.loads(Path(aliases['members'] if container else fixed['members']['path']).read_text())
    rows = {row['member']: row for row in member_doc['members']}
    _reuse_require(len(rows) == len(member_doc['members']), 'duplicate retained archive member')
    for row in fixed['objects'] + fixed['configuration']:
        retained = rows.get(row['retained_archive_member'])
        _reuse_require(retained is not None and retained['kind'] == 'regular' and retained['source'] == row['source'], 'seed/archive member binding differs')
        _reuse_file(seed / row['build_relative'], row['source'])
    for row in fixed['postimages']:
        path = Path('/src') / row['relative'] if container else row['postimage']['path']
        _reuse_file(path, row['postimage'])
        _reuse_require(row['readonly'] is True and row['container_destination'] == '/src/' + row['relative'], 'postimage is not exact readonly destination')
    return proofs

def _reuse_mounts(input_path):
    fixed = _REUSE_FIXED
    mounts = [(Path(fixed['base_source_root']), '/base-src', True),
              (Path(fixed['seed_root']), '/seed-build', True),
              (Path(input_path), '/reuse-inputs.json', True)]
    for key, target in (('archive', '/seed-archive.tar.gz'), ('members', '/seed-members.json'), ('retention_receipt', '/seed-retention.json')):
        mounts.append((Path(fixed[key]['path']), target, True))
    mounts.extend((Path(row['postimage']['path']), row['container_destination'], True) for row in fixed['postimages'])
    return mounts

def _reuse_preflight_request_crossrefs(request):
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
    _fail(request['driver_sha256'] == _REUSE_DRIVER_SHA256,
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
def _reuse_validate_request_base(request):
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
          "launcher aggregate must be exactly 22.0485 GiB")
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
    _fail(request.get("driver_sha256") == _REUSE_DRIVER_SHA256, "offline driver release hash")
    _fail(_sha256(driver) == _REUSE_DRIVER_SHA256, "offline driver bytes differ")
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
def _reuse_revalidate_inputs_base(bound, request):
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
    _fail(_sha256(bound["driver"]) == _REUSE_DRIVER_SHA256 and
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

_REUSE_FRESH_PREFLIGHT = preflight_request_crossrefs
_REUSE_FRESH_VALIDATE_REQUEST = _validate_request
_REUSE_FRESH_REVALIDATE = _revalidate_inputs
_REUSE_FRESH_VALIDATE_RESULT = _validate_driver_result
_REUSE_FRESH_IMAGE_OWNER = ImageOwner
_REUSE_DRIVER_SHA256 = '9d0b4e92891a2251bd099eb3dde04471e23dc76c7fb043f2781a45d64f7e376b'
_REUSE_HOST_INPUT_PATH = '/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-18-current289-union-source-1/qualified-getsiginfo-current290-successor-1/default-image-current290-coherent-overlay-source-1/authenticated-materialization-and-entry-source-1/attempt3-coherent-entry-preparation-source-1/genuine-newbe87-physical-binding-preparation-source-1/actual7553-namespace6294-final-source-1/memory-floor-correction1-source-1/query-packet-pin-correction1-source-1/default290-link-data-selector-correction1-source-1/minimal-selected-default-readonly-overlay-and-seed-plan-1/implementation-source-1/FROZEN-READONLY-THREE-POSTIMAGE-NINE-OBJECT-INPUTS.json'

def preflight_request_crossrefs(request):
    if 'readonly_reuse_inputs' not in request:
        return _REUSE_FRESH_PREFLIGHT(request)
    _reuse_authenticate(request['readonly_reuse_inputs'])
    return _reuse_preflight_request_crossrefs(request)

def _validate_request(request):
    if 'readonly_reuse_inputs' not in request:
        return _REUSE_FRESH_VALIDATE_REQUEST(request)
    _reuse_require(request['readonly_reuse_inputs'] == _REUSE_HOST_INPUT_PATH, 'descriptor host path differs')
    _reuse_authenticate(request['readonly_reuse_inputs'])
    _reuse_require(request.get('gitlink_manifest') == '/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-18-current289-union-source-1/qualified-getsiginfo-current290-successor-1/default-image-current290-coherent-overlay-source-1/authenticated-materialization-and-entry-source-1/gitlink-inputs.CURRENT290-IHK3114.SOURCE-ONLY.json' and request.get('gitlink_manifest_sha256') == 'e0c1abf3e0a16c9ff4a328d66f54fa126be0955d9ef54158ae520f7aa5d64c05' and request.get('gitlink_root') == '/home/holden/mckernel-work/scratch/native-exact-mckernel-gitlink-libdwarf-942c927b-scratch22-authority3-image1-20261017', 'exact consumed gitlink mount binding differs')
    _reuse_require(request['source_root'] == _REUSE_FIXED['base_source_root'], 'original source root differs')
    _reuse_require(request['source_manifest_sha256'] == _REUSE_FIXED['base_manifest']['sha256'], 'base manifest differs')
    _reuse_require(request.get('native_fork_owned_transaction', False) is False, 'reuse image-only mode required')
    bound = _reuse_validate_request_base(request)
    _reuse_require(bound['output'].name == 'output' and bound['evidence'].name == 'evidence', 'reuse fresh output aliases differ')
    _reuse_require(str(bound['source']) == _REUSE_FIXED['base_source_root'], 'validated base source differs')
    for readonly_source, _, _ in _reuse_mounts(request['readonly_reuse_inputs']):
        for writable in (bound['work'], bound['owner_evidence']):
            _reuse_require(writable != readonly_source and writable not in readonly_source.parents and readonly_source not in writable.parents, 'reuse readonly input overlaps mutable namespace')
    return bound

def _revalidate_inputs(bound, request):
    if 'readonly_reuse_inputs' not in request:
        return _REUSE_FRESH_REVALIDATE(bound, request)
    _reuse_revalidate_inputs_base(bound, request)
    if 'readonly_reuse_inputs' in request:
        _reuse_authenticate(request['readonly_reuse_inputs'])
        _reuse_require(_sha256(bound['driver']) == _REUSE_DRIVER_SHA256, 'reuse driver changed')

def _validate_driver_result(evidence, output, result, request):
    _REUSE_FRESH_VALIDATE_RESULT(evidence, output, result, request)
    if 'readonly_reuse_inputs' not in request:
        return
    proof = result.get('readonly_reuse')
    _reuse_require(isinstance(proof, dict), 'reuse result missing typed mode')
    _reuse_require(proof.get('schema') == _REUSE_FIXED['schema'] and proof.get('inputs_sha256') == _REUSE_INPUT_SHA256, 'reuse result input binding differs')
    _reuse_require(proof.get('configuration_mode') == _REUSE_FIXED['configuration_mode'] and proof.get('fresh_full_configure') is False, 'reuse configuration truth differs')
    _reuse_require((proof.get('reused_object_count'), proof.get('replaced_object_count'), proof.get('link_input_count')) == (9, 2, 11), 'reuse object counts differ')
    _reuse_require(proof.get('postimages') == _REUSE_FIXED['postimages'], 'reuse postimages differ')
    ownership = proof.get('fresh_object_ownership')
    _reuse_require(isinstance(ownership, dict) and ownership.get('status') == 'PASS_ACTUAL_DEFAULT_WHOLE_RUST_HANDLER_NO_PANIC_AND_FOUR_LOCAL_LOGGERS' and ownership.get('mandatory_fresh_compiled_object_gate') is True, 'mandatory fresh compiled Rust ownership proof missing')
    _reuse_require(ownership.get('new_Rust_object') == result['artifacts']['mckernel_rust.o'], 'fresh Rust ownership proof object identity differs')
    _reuse_require(ownership.get('whole_undefined_set_exact_except_removed_panics') is True and len(ownership.get('removed_original_panic_imports', [])) == 2, 'fresh Rust panic/import closure differs')
    _reuse_require(set(ownership.get('logger_proof', {})) == {'F06_PROCESS_VM_IOV_LOCAL_DEBUG', 'F06_PROCESS_VM_IOV_REMOTE_DEBUG', 'F06_PROCESS_VM_FOUND_DEBUG', 'F06_PROCESS_VM_COPY_DEBUG'}, 'four strict logger proofs missing')
    for marker, logger in ownership['logger_proof'].items():
        record = logger.get('record', {})
        symbol = record.get('symbol', {})
        _reuse_require(symbol.get('bind') == 0 and symbol.get('size') == 32 and record.get('filename') == '/src/kernel/rust/syscall_policy.rs' and record.get('function') == 'arch_process_vm_rw_log_bridge' and len(record.get('relocations', [])) == 2 and logger.get('callback_consumer_relocations'), 'fresh strict logger receipt differs')
    _reuse_require(json.loads((Path(evidence) / 'fresh-compiled-rust-ownership-proof.json').read_text()) == ownership, 'fresh Rust proof evidence differs')

    objects = proof.get('objects')
    _reuse_require(isinstance(objects, list) and len(objects) == 11, 'reuse result object list differs')
    for selected, actual in zip(_REUSE_FIXED['objects'], objects):
        _reuse_require(actual.get('build_relative') == selected['build_relative'] and actual.get('reused') is (not selected['replace']), 'reuse result object role/order differs')
        path = Path(output) / 'build' / selected['build_relative']
        artifact = actual.get('artifact')
        _reuse_require(isinstance(artifact, dict) and artifact.get('path') == '/work/output/build/' + selected['build_relative'], 'reuse result object path differs')
        _safe_regular(path, 'reuse result object')
        _reuse_require(artifact.get('size') == path.stat().st_size and artifact.get('sha256') == _sha256(path), 'reuse result final artifact differs')
        if not selected['replace']:
            _reuse_file(path, selected['source'])
    _reuse_require([row['phase'] for row in result['commands'] if row['phase'] in ('configure', 'build', 'recompile-full-Rust', 'recompile-process', 'raw-ld-11-inputs')] == ['recompile-full-Rust', 'recompile-process', 'raw-ld-11-inputs'], 'reuse executable phase set/order differs')

class ImageOwner(_REUSE_FRESH_IMAGE_OWNER):
    def run(self):
        if 'readonly_reuse_inputs' not in self.request:
            return super().run()
        return self._reuse_run()

    def _reuse_run(self):
        r = self.request
        # Shared admission must precede validation because validation performs
        # authenticated host measurement.  If anything after this acquisition
        # fails, the token is intentionally retained for recovery/review.
        shared_lock, shared_record = _SHARED_HEAVY_ENTRY_CONTRACT.acquire_heavy_operation(
            r, "image")
        bound = self.validate()
        evidence = bound["evidence"]
        _revalidate_inputs(bound, r)
        host_owner = bound["host_owner"]
        name = "mckernel-image-" + uuid.uuid4().hex
        nonce = uuid.uuid4().hex
        common = CommonExclusion(r["common_exclusion_path"], r)
        common.acquire()
        # No output/evidence mutation occurs until the shared heavy-build
        # exclusion is durably owned.  A stale common lock therefore fails
        # before creating a misleading fresh output namespace.
        # The driver must see absent output/evidence directories.  Only their
        # already-existing parent is mounted; the driver creates the fresh
        # child roots inside that parent.
        bound["attempt"].mkdir(mode=0o700)
        _fsync_dir(bound["owner_evidence"])
        _fsync_dir(evidence.parent); _fsync_dir(bound["output"].parent)
        lease = host_owner.Lease(bound["lease"], name); lease.acquire()
        docker = self.docker or host_owner.Docker(bound["attempt"] / "docker.log", self.signals, sudo=True)
        receipt = {"schema": RECEIPT_SCHEMA, "status": "FAIL", "candidate_sha": r["candidate_sha"],
                   "ihk_sha": r["ihk_sha"], "container_name": name, "owner_nonce": nonce,
                   "cleanup_separately_required": True, "terminal_container_retained": False,
                   "terminal_container_info": None, "terminal_container_info_current": False,
                   "shared_heavy_operation": {"kind": "image", "path": str(shared_lock),
                                              "record": shared_record}}
        if r.get('source_derivative_sha256') is not None:
            receipt.update(candidate_identity_scope='base_git_commit_only',
                           source_derivative_sha256=r['source_derivative_sha256'],
                           materialization_sha256=r['materialization_sha256'])
        attempted = False
        try:
            image = json.loads(docker.call(["image", "inspect", r["image_id"]]).stdout)[0]
            _fail(image.get("Id") == r["image_id"] and image.get("Architecture") == "amd64",
                  "container image identity mismatch")
            mounts = [(bound["source"], "/src", True), (bound["manifest"], "/inputs.json", True),
                      (bound["toolchain"], "/toolchain.json", True), (bound["driver"], "/driver.py", True),
                      (bound["provenance"], "/native_rust_exact_build_offline.py", True),
                      (bound["output"].parent, "/work", False)]
            mounts.extend(_reuse_mounts(r["readonly_reuse_inputs"]))
            if bound.get("gitlink_manifest") is not None:
                mounts.insert(2, (bound["gitlink_manifest"], "/libdwarf-inputs.json", True))
                mounts.insert(3, (bound["gitlink_root"], "/src/executer/user/lib/libdwarf/libdwarf", True))
            # v2 translates the complete host build output to /out.  It is a
            # single read-only mount: never mount /build separately or copy
            # and rewrite closure bytes.
            if bound["toolchain_schema"].endswith(".v2"):
                mount_roots = [(root, target) for target, root in bound["mounts_by_target"].items()]
            else:
                mount_roots = [(root, str(root)) for root in bound["roots"] + [bound["kernel"]]]
            for root, target in mount_roots:
                row = (root, target, True)
                if row not in mounts: mounts.append(row)
            rw_mounts = [(source, target) for source, target, readonly in mounts if not readonly]
            _fail(rw_mounts == [(bound["work"], "/work")],
                  "dedicated work root is not sole RW mount")
            args = ["create", "--name", name, "--label", "mckernel.owner=" + nonce, "--init",
                    "--network=none", "--ipc=private", *RESOURCE_ARGS, "--user", "%d:%d" % (os.getuid(), os.getgid()),
                    "--cap-drop=ALL", "--security-opt=no-new-privileges", "--read-only",
                    "--tmpfs", "/tmp:rw,nodev,nosuid,size=256m"]
            for source, target, readonly in mounts:
                args += ["--mount", "type=bind,src=" + str(source) + ",dst=" + target +
                         (",readonly" if readonly else "")]
            command = ["/driver.py", "--source-root", "/src",
                       "--candidate-sha", r["candidate_sha"], "--ihk-sha", r["ihk_sha"],
                       "--manifest", "/inputs.json", "--toolchain", "/toolchain.json",
                       "--output", "/work/" + bound["output"].name,
                       "--evidence", "/work/" + evidence.name, "--jobs", str(r["jobs"]),
                       "--timeout", str(r["timeout"])]
            if bound.get("gitlink_manifest") is not None:
                command += ["--gitlink-manifest", "/libdwarf-inputs.json"]
            if r.get("native_fork_owned_transaction", False):
                command += ["--native-fork-owned-transaction"]
            command += ["--readonly-reuse-inputs", "/reuse-inputs.json"]
            args += ["--entrypoint", "/usr/bin/python3", r["image_id"], *command]
            attempted = True
            created = docker.call(args); receipt["container_id"] = created.stdout.strip()
            info = host_owner.inspect(docker, name)
            _check_profile(info, r["image_id"], nonce, mounts=mounts, command=command,
                           user="%d:%d" % (os.getuid(), os.getgid()), host_owner=host_owner)
            # The admission measurement is only a lower bound.  Rebind the
            # lease to a fresh host/scratch measurement immediately before
            # Docker start so a concurrent allocation cannot slip between
            # validation and execution.
            latest = host_owner.measure(
                r["disk_admission"]["host_root"],
                r["disk_admission"]["scratch_root"],
                16 * 2**30, 12 * 2**30, source_root=bound["source"],
                output_root=bound["work"], memory_allocation_roots=bound["allocation_roots"])
            _fail(latest.get("memory_allocation_memory_backed_bytes") ==
                  r["memory_backed_bytes"], "pre-start memory allocation changed")
            _fail(latest.get("aggregate_memory_required") ==
                  r["aggregate_memory_required"], "pre-start aggregate memory changed")
            receipt["pre_start_measurement"] = latest
            docker.call(["start", name]); waited = docker.call(["wait", name], timeout=r["timeout"])
            receipt["exit_code"] = int(waited.stdout.strip())
            _fail(receipt["exit_code"] == 0, "offline image driver failed")
            receipt_path = _safe_regular(evidence / "receipt.json", "driver receipt")
            build_receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            _validate_driver_result(evidence, bound["output"], build_receipt, r)
            _revalidate_inputs(bound, r)
            receipt["status"] = "PASS"
        except BaseException as exc:
            receipt["error"] = str(exc)
        finally:
            if self.signals: self.signals.cleaning = True
            if attempted:
                try:
                    receipt["terminal_container_info"] = host_owner.retire(docker, name, nonce)
                    receipt["terminal_container_retained"] = True
                    receipt["retired"] = True
                except BaseException as exc:
                    receipt["status"] = "FAIL"; receipt["retirement_error"] = str(exc); receipt["retired"] = False
                try:
                    logs = docker.call(["logs", name], check=False)
                    _fail(logs.returncode == 0, "Docker logs command failed")
                    _exclusive_text(bound["attempt"] / "container.log", logs.stdout + logs.stderr)
                except BaseException as exc:
                    receipt["status"] = "FAIL"; receipt["capture_error"] = str(exc)
                if getattr(docker, "client_retirement_unproven", False):
                    receipt["status"] = "FAIL"; receipt["retired"] = False
                    receipt["client_retirement_unproven"] = True
            else:
                receipt["retired"] = True
                receipt["cleanup_separately_required"] = False
                receipt["terminal_container_info_current"] = True
            try:
                _revalidate_inputs(bound, r)
            except BaseException as exc:
                receipt["status"] = "FAIL"
                receipt["input_revalidation_error"] = str(exc)
            if self.signals and self.signals.requested is not None:
                receipt["status"] = "FAIL"
                receipt["interrupted_signal"] = self.signals.requested
            receipt["driver_evidence_root"] = str(evidence)
            receipt["owner_evidence_root"] = str(bound["owner_evidence"])
            receipt["attempt_root"] = str(bound["attempt"])
            receipt["common_exclusion_path"] = r["common_exclusion_path"]
            receipt["finished_at"] = time.time()
            _exclusive_json(bound["owner_evidence"] / OWNER_RECEIPT_NAME, receipt)
            if receipt.get("retired"):
                lease.release()
            # The shared contract releases only after a positive PASS,
            # terminal retirement, and sealed evidence.  Any uncertain
            # container, observer, or evidence state deliberately retains it
            # for explicit reconciliation.
            _SHARED_HEAVY_ENTRY_CONTRACT._release_exclusion(
                shared_lock, shared_record, receipt)
        return receipt

if __name__ == "__main__":
    raise SystemExit(main())
