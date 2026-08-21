#!/usr/bin/env python3
"""Capture fail-closed RK-003 transitive closure and offline replay evidence.

This is phase two of the Rocky platform evidence plan.  It consumes an exact
externally digest-bound repository-snapshot-capture-v2 tar, derives the current
resolution roots from the immutable locked kernel.spec, and uses DNF only to
acquire a candidate transaction from three bounded Rocky binary sources.  It
binds every selected RPM to the verified signed primary metadata, verifies each
RPM with the private Rocky-key RPM database, and replays the complete
transaction into a second empty installroot with every repository disabled.
Successful capture is deliberately credit-forbidden.
"""

import argparse
import ast
import bz2
import ctypes
import errno
import gzip
import hashlib
import json
import lzma
import os
import re
import secrets
import shlex
import shutil
import stat
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path, PurePosixPath
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

import rocky_kernel_platform_evidence as phase_one
import rocky_repository_snapshot_capture as snapshot_v2


LEGACY_CONTRACT_PATH = Path(
    "host-kernel/rocky/evidence/closure-offline-contract-v1.json"
)
LEGACY_EXPECTED_CONTRACT_SHA256 = (
    "2fe1230ef9cd7901a3c660f3dfd26b2dadfb31b161ef047fedfda20d9936c013"
)
CONTRACT_PATH = Path(
    "host-kernel/rocky/evidence/closure-offline-contract-v2.json"
)
EXPECTED_CONTRACT_SHA256 = (
    "bf785fab1321b9edbe86fea7c37111854d94bae513c7e16c946ef0ac06052e00"
)
WORKFLOW_PATH = Path(".github/workflows/rocky-kernel-closure-offline.yml")
EXPECTED_WORKFLOW_SHA256 = (
    "2861a04b97a89b9f23ea3e6ee7e2378f1d9962330451ddb0c3e87e025a7c5e2e"
)
EXPECTED_WORKFLOW_USES = [
    "actions/checkout@11d5960a326750d5838078e36cf38b85af677262",
    "actions/checkout@11d5960a326750d5838078e36cf38b85af677262",
    "actions/download-artifact@d3f86a106a0bac45b974a628896c90dbdf5c8093",
    "actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02",
]
SCHEMA_VERSION = 1
V2_SCHEMA_VERSION = 2
PHASE_ID = "closure-offline"
RPM_NEVRA_QUERY = "%{NAME}-%{EPOCHNUM}:%{VERSION}-%{RELEASE}.%{ARCH}\\n"
MAX_PRIMARY_PACKAGES = 100000
MAX_CAPTURED_RPMS = 4096
MAX_CAPTURED_BYTES = 8 * 1024 * 1024 * 1024
MAX_REPOMD_OBJECTS = 64
MAX_METADATA_OBJECT_BYTES = 512 * 1024 * 1024
MAX_METADATA_OPEN_BYTES = 1024 * 1024 * 1024
MAX_V2_SHA256SUMS_BYTES = 32 * 1024 * 1024
HEX_SHA256 = re.compile(r"^[0-9a-f]{64}$")
LOCKED_LLVM_PROBE_OWNER_NEVRA = "llvm-0:21.1.8-1.el10.x86_64"
LLVM_CONFIG_OWNER_NEVRA = "llvm-devel-0:21.1.8-1.el10.x86_64"
LLVM_OWNER_AUTHORITY_BLOCKER = (
    "The current RK-003 toolchain authority maps the llvm-config probe to "
    "llvm-0:21.1.8-1.el10.x86_64, but the captured binary is owned by "
    "llvm-devel-0:21.1.8-1.el10.x86_64; this mapping must be reconciled before "
    "credit or review ingestion."
)
METADATA_RECONCILIATION_FALSE_CLAIMS = {
    "closure_artifact_captured": False,
    "closure_artifact_durable": False,
    "closure_artifact_independently_reviewed": False,
    "credit_eligible": False,
    "gate_rk_003": False,
    "runtime_evidence_captured": False,
    "tracker_credit": False,
}
METADATA_RECONCILIATION_SCOPE = (
    "Local closure-v2 implementation-status and llvm-config owner "
    "reconciliation only; the historical v1 plan and toolchain lock remain "
    "unchanged, and no runtime, review, durability, gate, or tracker claim is "
    "made."
)
PHASE_PLAN_RECONCILIATION_SCOPE = (
    "The exact historical v1 plan remains byte-stable and records the phase as "
    "unimplemented; closure-v2 now has a local contract, checker, workflow, and "
    "tests, but no runtime capture is claimed."
)
LLVM_CONFIG_OWNER_SCOPE = (
    "RK-003 probe-owner metadata only; this does not prove that llvm-devel was "
    "captured in a complete closure, reviewed, durably archived, or eligible "
    "for gate or tracker credit."
)
V2_SUCCESS_BLOCKERS = [
    "The snapshot-backed closure/offline artifact still requires independent "
    "review and durable archival before it may be bound into the toolchain lock.",
    "Kernel-level network isolation was not proved; repository-disabled "
    "file-only replay and proxy-loopback defense are narrower evidence.",
    "The repository-snapshot-capture-v2 artifact is a runtime input and is not "
    "accepted or durable merely because this bridge verifies it.",
    "The minimal requested config has not been resolved twice by the exact Rocky "
    "process_configs.sh and olddefconfig pipeline.",
    "make LLVM=1 rustavailable has not run in the reviewed offline buildroot "
    "against the exact source and resolved config.",
    "A production kernel build has not bound its final .config to the "
    "independently resolved config.",
    "The RK-006 compatibility patch series remains independently governed and "
    "receives no credit from this evidence.",
]
LIBCLANG_PROBE_BYTES = (
    b"/* SPDX-License-Identifier: GPL-2.0 */\n"
    b'#pragma message("clang version " __clang_version__)\n'
)
# Exact two-line helper used by the locked kernel probe command.  It is copied
# into the ephemeral installroot only; this does not attest the source tree.
LIBCLANG_PROBE_SHA256 = "bf71d14ea244116ab8c6d61c593d37be3c9c346e13d0569a10acdfec63739e21"
PROBE_RESULT_FIELDS = {
    "binary_path",
    "binary_sha256",
    "command",
    "exit_code",
    "id",
    "loaded_library_path",
    "loaded_library_sha256",
    "package_nevra",
    "parsed_version",
    "required_file_path",
    "required_file_sha256",
    "stderr_sha256",
    "stdout_sha256",
}
DIRECT_MANIFEST_NAMES = [
    "blockers.json",
    "build-requirements.json",
    "direct-rpms.json",
    "environment.json",
    "repository-snapshots.json",
]
PYTHON36_ENTRYPOINT_PATHS = [
    "scripts/rocky_kernel_closure_offline.py",
    "scripts/rocky_kernel_platform_evidence.py",
]


class ClosureError(RuntimeError):
    pass


def exact_keys(value: object, expected: Iterable[str], label: str) -> Mapping[str, Any]:
    if not isinstance(value, dict) or set(value) != set(expected):
        actual = sorted(value) if isinstance(value, dict) else type(value).__name__
        raise ClosureError(
            "{} fields changed: actual={!r}, expected={!r}".format(
                label, actual, sorted(expected)
            )
        )
    return value


def require_exact(value: object, expected: object, label: str) -> None:
    if value != expected or type(value) is not type(expected):
        raise ClosureError(
            "{} changed: actual={!r}, expected={!r}".format(label, value, expected)
        )


def open_regular_read(path: Path, label: str) -> int:
    """Open one regular file without following any component symlinks."""
    if not hasattr(os, "O_DIRECTORY") or not hasattr(os, "O_NOFOLLOW"):
        raise ClosureError("no-follow file opening is unavailable")
    absolute = Path(os.path.abspath(str(path)))
    parts = absolute.parts
    if not parts or parts[0] != os.path.sep or len(parts) < 2:
        raise ClosureError("{} path is invalid".format(label))
    directory_fd = -1
    file_fd = -1
    try:
        directory_fd = os.open(
            os.path.sep, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
        )
        for component in parts[1:-1]:
            next_fd = os.open(
                component,
                os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                dir_fd=directory_fd,
            )
            os.close(directory_fd)
            directory_fd = next_fd
        file_fd = os.open(
            parts[-1],
            os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK,
            dir_fd=directory_fd,
        )
        if not stat.S_ISREG(os.fstat(file_fd).st_mode):
            raise ClosureError("{} must be a regular file".format(label))
        result = file_fd
        file_fd = -1
        return result
    except OSError as exc:
        raise ClosureError("cannot safely open {}: {}".format(label, exc)) from exc
    finally:
        if directory_fd >= 0:
            os.close(directory_fd)
        if file_fd >= 0:
            os.close(file_fd)


def open_regular_create(path: Path, label: str) -> int:
    """Create one regular file without following any component symlinks."""
    if not hasattr(os, "O_DIRECTORY") or not hasattr(os, "O_NOFOLLOW"):
        raise ClosureError("no-follow file creation is unavailable")
    absolute = Path(os.path.abspath(str(path)))
    parts = absolute.parts
    if not parts or parts[0] != os.path.sep or len(parts) < 2:
        raise ClosureError("{} path is invalid".format(label))
    directory_fd = -1
    file_fd = -1
    try:
        directory_fd = os.open(
            os.path.sep, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
        )
        for component in parts[1:-1]:
            next_fd = os.open(
                component,
                os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                dir_fd=directory_fd,
            )
            os.close(directory_fd)
            directory_fd = next_fd
        file_fd = os.open(
            parts[-1],
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
            0o600,
            dir_fd=directory_fd,
        )
        if not stat.S_ISREG(os.fstat(file_fd).st_mode):
            raise ClosureError("{} must be a regular file".format(label))
        result = file_fd
        file_fd = -1
        return result
    except OSError as exc:
        raise ClosureError("cannot safely create {}: {}".format(label, exc)) from exc
    finally:
        if directory_fd >= 0:
            os.close(directory_fd)
        if file_fd >= 0:
            os.close(file_fd)


def open_regular_create_read_write(path: Path, label: str) -> int:
    """Create one descriptor-bound regular file for write-then-verify use."""
    if not hasattr(os, "O_DIRECTORY") or not hasattr(os, "O_NOFOLLOW"):
        raise ClosureError("no-follow file creation is unavailable")
    absolute = Path(os.path.abspath(str(path)))
    parts = absolute.parts
    if not parts or parts[0] != os.path.sep or len(parts) < 2:
        raise ClosureError("{} path is invalid".format(label))
    directory_fd = -1
    file_fd = -1
    try:
        directory_fd = os.open(
            os.path.sep, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
        )
        for component in parts[1:-1]:
            next_fd = os.open(
                component,
                os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                dir_fd=directory_fd,
            )
            os.close(directory_fd)
            directory_fd = next_fd
        file_fd = os.open(
            parts[-1],
            os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
            0o600,
            dir_fd=directory_fd,
        )
        metadata = os.fstat(file_fd)
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1:
            raise ClosureError("{} must be one regular file".format(label))
        result = file_fd
        file_fd = -1
        return result
    except OSError as exc:
        raise ClosureError("cannot safely create {}: {}".format(label, exc)) from exc
    finally:
        if directory_fd >= 0:
            os.close(directory_fd)
        if file_fd >= 0:
            os.close(file_fd)


def regular_identity(value: os.stat_result) -> Tuple[int, int, int, int, int]:
    return (
        value.st_dev,
        value.st_ino,
        value.st_size,
        value.st_mtime_ns,
        value.st_ctime_ns,
    )


def read_regular_bytes(path: Path, label: str) -> bytes:
    descriptor = open_regular_read(path, label)
    try:
        with os.fdopen(descriptor, "rb") as stream:
            descriptor = -1
            before = regular_identity(os.fstat(stream.fileno()))
            data = stream.read()
            after = regular_identity(os.fstat(stream.fileno()))
            if before != after or len(data) != after[2]:
                raise ClosureError("{} changed while it was read".format(label))
            return data
    finally:
        if descriptor >= 0:
            os.close(descriptor)


def sha256_file(path: Path) -> Tuple[int, str]:
    digest = hashlib.sha256()
    size = 0
    descriptor = open_regular_read(path, "hash input")
    try:
        with os.fdopen(descriptor, "rb") as stream:
            descriptor = -1
            before = regular_identity(os.fstat(stream.fileno()))
            while True:
                chunk = stream.read(1024 * 1024)
                if not chunk:
                    break
                size += len(chunk)
                digest.update(chunk)
            after = regular_identity(os.fstat(stream.fileno()))
            if before != after or size != after[2]:
                raise ClosureError("hash input changed while it was read")
    finally:
        if descriptor >= 0:
            os.close(descriptor)
    return size, digest.hexdigest()


def v2_absolute_path(path: Path, label: str) -> Path:
    try:
        result = Path(os.path.abspath(str(path)))
    except (OSError, TypeError, ValueError) as exc:
        raise ClosureError("{} is not a usable path: {}".format(label, exc)) from exc
    if not result.is_absolute() or len(result.parts) < 2:
        raise ClosureError("{} is not a usable absolute path".format(label))
    if any(part in ("", ".", "..") for part in result.parts[1:]):
        raise ClosureError("{} contains an unsafe component".format(label))
    return result


def v2_directory_identity(metadata: os.stat_result) -> Tuple[int, int, int, int, int]:
    if not stat.S_ISDIR(metadata.st_mode):
        raise ClosureError("secure output identity is not a directory")
    return (
        metadata.st_dev,
        metadata.st_ino,
        metadata.st_mode,
        metadata.st_uid,
        metadata.st_gid,
    )


def v2_regular_identity(
    metadata: os.stat_result,
) -> Tuple[int, int, int, int, int, int, int, int, int]:
    return (
        metadata.st_dev,
        metadata.st_ino,
        metadata.st_mode,
        metadata.st_nlink,
        metadata.st_uid,
        metadata.st_gid,
        metadata.st_size,
        metadata.st_mtime_ns,
        metadata.st_ctime_ns,
    )


def v2_open_directory(path: Path, label: str) -> int:
    if not hasattr(os, "O_DIRECTORY") or not hasattr(os, "O_NOFOLLOW"):
        raise ClosureError("secure v2 output directory opening is unavailable")
    requested = v2_absolute_path(path, label)
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    descriptor = -1
    try:
        descriptor = os.open(os.path.sep, flags)
        for component in requested.parts[1:]:
            child = os.open(component, flags, dir_fd=descriptor)
            os.close(descriptor)
            descriptor = child
        result = descriptor
        descriptor = -1
        return result
    except OSError as exc:
        raise ClosureError("cannot safely open {}: {}".format(label, exc)) from exc
    finally:
        if descriptor >= 0:
            os.close(descriptor)


def v2_require_stable_directory(
    path: Path,
    descriptor: int,
    expected: Tuple[int, int, int, int, int],
    label: str,
) -> None:
    require_exact(
        v2_directory_identity(os.fstat(descriptor)),
        expected,
        label + " descriptor identity",
    )
    reopened = v2_open_directory(path, label + " path")
    try:
        require_exact(
            v2_directory_identity(os.fstat(reopened)),
            expected,
            label + " path identity",
        )
    finally:
        os.close(reopened)


def v2_write_all(descriptor: int, data: bytes, label: str) -> None:
    offset = 0
    try:
        while offset < len(data):
            written = os.write(descriptor, data[offset:])
            if written <= 0:
                raise ClosureError("{} write made no progress".format(label))
            offset += written
    except OSError as exc:
        raise ClosureError("cannot write {}: {}".format(label, exc)) from exc


def v2_rename_noreplace(
    source_directory: int,
    source_name: str,
    destination_directory: int,
    destination_name: str,
) -> None:
    try:
        renameat2 = ctypes.CDLL(None, use_errno=True).renameat2
    except AttributeError as exc:
        raise ClosureError(
            "atomic no-replace v2 output publication is unavailable"
        ) from exc
    renameat2.argtypes = (
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_uint,
    )
    renameat2.restype = ctypes.c_int
    result = renameat2(
        source_directory,
        os.fsencode(source_name),
        destination_directory,
        os.fsencode(destination_name),
        1,
    )
    if result != 0:
        error = ctypes.get_errno()
        if error in (errno.EEXIST, errno.ENOTEMPTY):
            raise ClosureError("v2 output leaf appeared before publication")
        raise ClosureError(
            "cannot atomically publish v2 output: {}".format(os.strerror(error))
        )


def v2_remove_directory_contents(descriptor: int) -> None:
    """Remove one held directory tree without following any pathname component."""
    try:
        names = sorted(os.listdir(descriptor))
    except OSError as exc:
        raise ClosureError("cannot enumerate secure output cleanup: {}".format(exc)) from exc
    for name in names:
        if not isinstance(name, str) or name in ("", ".", "..") or "/" in name:
            raise ClosureError("secure output cleanup found an unsafe name")
        try:
            metadata = os.stat(name, dir_fd=descriptor, follow_symlinks=False)
            if stat.S_ISDIR(metadata.st_mode):
                child = os.open(
                    name,
                    os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                    dir_fd=descriptor,
                )
                try:
                    v2_remove_directory_contents(child)
                    os.fsync(child)
                finally:
                    os.close(child)
                os.rmdir(name, dir_fd=descriptor)
            else:
                os.unlink(name, dir_fd=descriptor)
        except OSError as exc:
            raise ClosureError(
                "cannot clean secure output entry {}: {}".format(name, exc)
            ) from exc


def v2_remove_named_directory_if_identity(
    parent_descriptor: int,
    name: str,
    expected: Tuple[int, int, int, int, int],
) -> None:
    try:
        metadata = os.stat(name, dir_fd=parent_descriptor, follow_symlinks=False)
    except FileNotFoundError:
        return
    except OSError as exc:
        raise ClosureError("cannot inspect secure output cleanup leaf: {}".format(exc)) from exc
    if not stat.S_ISDIR(metadata.st_mode):
        return
    if v2_directory_identity(metadata) != expected:
        return
    try:
        os.rmdir(name, dir_fd=parent_descriptor)
    except OSError as exc:
        raise ClosureError("cannot remove secure output directory: {}".format(exc)) from exc


def v2_copy_regular_between_directories(
    source_directory: int, destination_directory: int, name: str
) -> Tuple[int, int, int, int, int, int, int, int, int]:
    source_descriptor = -1
    destination_descriptor = -1
    try:
        source_descriptor = os.open(
            name,
            os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK,
            dir_fd=source_directory,
        )
        before = v2_regular_identity(os.fstat(source_descriptor))
        if (
            not stat.S_ISREG(before[2])
            or before[3] != 1
            or before[4] != os.geteuid()
            or stat.S_IMODE(before[2]) != 0o400
        ):
            raise ClosureError("v2 publication source file identity is unsafe")
        destination_descriptor = os.open(
            name,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
            0o600,
            dir_fd=destination_directory,
        )
        copied = 0
        while True:
            chunk = os.read(source_descriptor, 1024 * 1024)
            if not chunk:
                break
            copied += len(chunk)
            v2_write_all(destination_descriptor, chunk, "v2 publication file")
        os.fchmod(destination_descriptor, 0o400)
        os.fsync(destination_descriptor)
        after = v2_regular_identity(os.fstat(source_descriptor))
        published = os.fstat(destination_descriptor)
        if (
            before != after
            or copied != before[6]
            or not stat.S_ISREG(published.st_mode)
            or published.st_nlink != 1
            or published.st_size != copied
            or stat.S_IMODE(published.st_mode) != 0o400
        ):
            raise ClosureError("v2 publication source changed while copied")
        destination_identity = v2_regular_identity(published)
    except ClosureError:
        raise
    except OSError as exc:
        raise ClosureError("cannot copy v2 publication file: {}".format(exc)) from exc
    finally:
        if source_descriptor >= 0:
            os.close(source_descriptor)
        if destination_descriptor >= 0:
            os.close(destination_descriptor)
    return destination_identity


def v2_copy_output_tree(
    source_directory: int,
    destination_directory: int,
    prefix: PurePosixPath = PurePosixPath(),
) -> Dict[str, Tuple[str, Tuple[int, ...]]]:
    copied_namespace: Dict[str, Tuple[str, Tuple[int, ...]]] = {}
    try:
        before_names = sorted(os.listdir(source_directory))
    except OSError as exc:
        raise ClosureError("cannot enumerate v2 publication source: {}".format(exc)) from exc
    for name in before_names:
        if not isinstance(name, str) or name in ("", ".", "..") or "/" in name:
            raise ClosureError("v2 publication source contains an unsafe name")
        try:
            metadata = os.stat(name, dir_fd=source_directory, follow_symlinks=False)
        except OSError as exc:
            raise ClosureError(
                "cannot inspect v2 publication source {}: {}".format(name, exc)
            ) from exc
        if stat.S_ISREG(metadata.st_mode):
            identity = v2_copy_regular_between_directories(
                source_directory, destination_directory, name
            )
            copied_namespace[(prefix / name).as_posix()] = ("file", identity)
            continue
        if not stat.S_ISDIR(metadata.st_mode):
            raise ClosureError("v2 publication source contains a symlink or special file")
        if (
            metadata.st_uid != os.geteuid()
            or stat.S_IMODE(metadata.st_mode) != 0o700
        ):
            raise ClosureError("v2 publication source directory identity is unsafe")
        source_child = -1
        destination_child = -1
        try:
            source_child = os.open(
                name,
                os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                dir_fd=source_directory,
            )
            os.mkdir(name, 0o700, dir_fd=destination_directory)
            destination_child = os.open(
                name,
                os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                dir_fd=destination_directory,
            )
            copied_namespace[(prefix / name).as_posix()] = (
                "directory",
                v2_directory_identity(os.fstat(destination_child)),
            )
            source_identity = v2_directory_identity(os.fstat(source_child))
            copied_namespace.update(
                v2_copy_output_tree(
                    source_child, destination_child, prefix / name
                )
            )
            require_exact(
                v2_directory_identity(os.fstat(source_child)),
                source_identity,
                "v2 publication source directory identity",
            )
            os.fsync(destination_child)
        except OSError as exc:
            raise ClosureError(
                "cannot copy v2 publication directory {}: {}".format(name, exc)
            ) from exc
        finally:
            if source_child >= 0:
                os.close(source_child)
            if destination_child >= 0:
                os.close(destination_child)
    try:
        after_names = sorted(os.listdir(source_directory))
    except OSError as exc:
        raise ClosureError("cannot re-enumerate v2 publication source: {}".format(exc)) from exc
    require_exact(after_names, before_names, "v2 publication source closure")
    return copied_namespace


def v2_hash_regular_at(
    directory_descriptor: int, name: str, label: str
) -> Tuple[Tuple[int, int, int, int, int, int, int, int, int], int, str]:
    descriptor = -1
    try:
        descriptor = os.open(
            name,
            os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK,
            dir_fd=directory_descriptor,
        )
        before = v2_regular_identity(os.fstat(descriptor))
        if not stat.S_ISREG(before[2]) or before[3] != 1:
            raise ClosureError("{} is not one regular file".format(label))
        digest = hashlib.sha256()
        size = 0
        while True:
            chunk = os.read(descriptor, 1024 * 1024)
            if not chunk:
                break
            size += len(chunk)
            digest.update(chunk)
        after = v2_regular_identity(os.fstat(descriptor))
        if before != after or size != before[6]:
            raise ClosureError("{} changed while hashed".format(label))
        return before, size, digest.hexdigest()
    except ClosureError:
        raise
    except OSError as exc:
        raise ClosureError("cannot hash {}: {}".format(label, exc)) from exc
    finally:
        if descriptor >= 0:
            os.close(descriptor)


def v2_open_relative_parent_at(
    root_descriptor: int, relative: PurePosixPath, label: str
) -> Tuple[int, str]:
    try:
        normalized = phase_one.normalized_relative_path(relative.as_posix(), label)
    except phase_one.EvidenceError as exc:
        raise ClosureError("{} is unsafe: {}".format(label, exc)) from exc
    descriptor = os.dup(root_descriptor)
    try:
        for component in normalized.parts[:-1]:
            child = os.open(
                component,
                os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                dir_fd=descriptor,
            )
            os.close(descriptor)
            descriptor = child
        result = descriptor
        descriptor = -1
        return result, normalized.name
    except OSError as exc:
        raise ClosureError("cannot open {} parent: {}".format(label, exc)) from exc
    finally:
        if descriptor >= 0:
            os.close(descriptor)


def v2_hash_regular_relative(
    root_descriptor: int, relative: PurePosixPath, label: str
) -> Tuple[Tuple[int, int, int, int, int, int, int, int, int], int, str]:
    parent_descriptor, name = v2_open_relative_parent_at(
        root_descriptor, relative, label
    )
    try:
        return v2_hash_regular_at(parent_descriptor, name, label)
    finally:
        os.close(parent_descriptor)


def v2_read_regular_relative(
    root_descriptor: int,
    relative: PurePosixPath,
    label: str,
    maximum_bytes: int,
) -> Tuple[bytes, Tuple[int, int, int, int, int, int, int, int, int]]:
    parent_descriptor, name = v2_open_relative_parent_at(
        root_descriptor, relative, label
    )
    descriptor = -1
    try:
        descriptor = os.open(
            name,
            os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK,
            dir_fd=parent_descriptor,
        )
        before = v2_regular_identity(os.fstat(descriptor))
        if (
            not stat.S_ISREG(before[2])
            or before[3] != 1
            or before[6] < 1
            or before[6] > maximum_bytes
        ):
            raise ClosureError("{} identity or size is unsafe".format(label))
        chunks = []
        size = 0
        while size < before[6]:
            chunk = os.read(descriptor, min(1024 * 1024, before[6] - size))
            if not chunk:
                raise ClosureError("{} is truncated".format(label))
            size += len(chunk)
            chunks.append(chunk)
        if os.read(descriptor, 1):
            raise ClosureError("{} grew while read".format(label))
        after = v2_regular_identity(os.fstat(descriptor))
        if before != after or size != before[6]:
            raise ClosureError("{} changed while read".format(label))
        return b"".join(chunks), before
    except ClosureError:
        raise
    except OSError as exc:
        raise ClosureError("cannot read {}: {}".format(label, exc)) from exc
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        os.close(parent_descriptor)


def v2_output_namespace(
    root_descriptor: int,
) -> Dict[str, Tuple[str, Tuple[int, ...]]]:
    result: Dict[str, Tuple[str, Tuple[int, ...]]] = {}

    def visit(directory_descriptor: int, prefix: PurePosixPath) -> None:
        try:
            before_names = sorted(os.listdir(directory_descriptor))
        except OSError as exc:
            raise ClosureError("cannot enumerate v2 output namespace: {}".format(exc)) from exc
        for name in before_names:
            if not isinstance(name, str) or name in ("", ".", "..") or "/" in name:
                raise ClosureError("v2 output namespace contains an unsafe name")
            relative = prefix / name
            try:
                metadata = os.stat(
                    name, dir_fd=directory_descriptor, follow_symlinks=False
                )
            except OSError as exc:
                raise ClosureError(
                    "cannot inspect v2 output namespace {}: {}".format(
                        relative, exc
                    )
                ) from exc
            if stat.S_ISREG(metadata.st_mode):
                if (
                    metadata.st_nlink != 1
                    or metadata.st_uid != os.geteuid()
                    or stat.S_IMODE(metadata.st_mode) != 0o400
                ):
                    raise ClosureError("v2 output file identity is unsafe")
                result[relative.as_posix()] = (
                    "file",
                    v2_regular_identity(metadata),
                )
                continue
            if not stat.S_ISDIR(metadata.st_mode):
                raise ClosureError("v2 output contains a symlink or special file")
            if (
                metadata.st_uid != os.geteuid()
                or stat.S_IMODE(metadata.st_mode) != 0o700
            ):
                raise ClosureError("v2 output directory identity is unsafe")
            result[relative.as_posix()] = (
                "directory",
                v2_directory_identity(metadata),
            )
            child = -1
            try:
                child = os.open(
                    name,
                    os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                    dir_fd=directory_descriptor,
                )
                visit(child, relative)
            except OSError as exc:
                raise ClosureError(
                    "cannot open v2 output directory {}: {}".format(relative, exc)
                ) from exc
            finally:
                if child >= 0:
                    os.close(child)
        try:
            after_names = sorted(os.listdir(directory_descriptor))
        except OSError as exc:
            raise ClosureError("cannot replay v2 output namespace: {}".format(exc)) from exc
        require_exact(after_names, before_names, "v2 output namespace replay")

    visit(root_descriptor, PurePosixPath())
    return result


def v2_verify_checksum_directory(
    root_descriptor: int,
    expected_manifest_bytes: Optional[bytes] = None,
    expected_files: Optional[Sequence[str]] = None,
) -> Tuple[
    bytes,
    Dict[str, Tuple[str, Tuple[int, ...]]],
    Dict[str, Tuple[int, str]],
]:
    manifest_bytes, _ = v2_read_regular_relative(
        root_descriptor,
        PurePosixPath("SHA256SUMS"),
        "v2 output SHA256SUMS",
        MAX_V2_SHA256SUMS_BYTES,
    )
    if expected_manifest_bytes is not None:
        require_exact(
            manifest_bytes,
            expected_manifest_bytes,
            "v2 output exact SHA256SUMS bytes",
        )
    if not manifest_bytes.endswith(b"\n"):
        raise ClosureError("v2 output SHA256SUMS is malformed")
    try:
        lines = manifest_bytes.decode("ascii").splitlines()
    except UnicodeDecodeError as exc:
        raise ClosureError("v2 output SHA256SUMS is not ASCII") from exc
    listed = []
    declared = {}
    for line in lines:
        match = re.fullmatch(r"([0-9a-f]{64})  ([^\0\r\n]+)", line)
        if match is None:
            raise ClosureError("v2 output SHA256SUMS row is malformed")
        try:
            relative = phase_one.normalized_relative_path(
                match.group(2), "v2 checksum path"
            )
        except phase_one.EvidenceError as exc:
            raise ClosureError("v2 output checksum path is unsafe: {}".format(exc)) from exc
        name = relative.as_posix()
        if name == "SHA256SUMS" or name in declared:
            raise ClosureError("v2 output checksum path is duplicated or recursive")
        declared[name] = match.group(1)
        listed.append(name)
    if not listed:
        raise ClosureError("v2 output SHA256SUMS is empty")
    require_exact(listed, sorted(listed), "v2 output checksum order")
    before_namespace = v2_output_namespace(root_descriptor)
    actual_files = sorted(
        name
        for name, item in before_namespace.items()
        if item[0] == "file" and name != "SHA256SUMS"
    )
    require_exact(listed, actual_files, "v2 output checksum closure")
    if expected_files is not None:
        require_exact(
            actual_files,
            sorted(expected_files),
            "v2 output exact file set",
        )
    verified = {}
    for name in listed:
        _, size, digest = v2_hash_regular_relative(
            root_descriptor, PurePosixPath(name), "v2 checksummed output"
        )
        require_exact(digest, declared[name], "v2 output checksum")
        verified[name] = (size, digest)
    after_namespace = v2_output_namespace(root_descriptor)
    require_exact(
        after_namespace,
        before_namespace,
        "v2 output namespace after checksum verification",
    )
    return manifest_bytes, after_namespace, verified


def v2_require_output_namespace(
    root_descriptor: int,
    expected: Mapping[str, Tuple[str, Tuple[int, ...]]],
    label: str,
) -> None:
    require_exact(v2_output_namespace(root_descriptor), expected, label)


def v2_compare_output_trees(source_directory: int, destination_directory: int) -> None:
    try:
        source_names = sorted(os.listdir(source_directory))
        destination_names = sorted(os.listdir(destination_directory))
    except OSError as exc:
        raise ClosureError("cannot enumerate copied v2 output: {}".format(exc)) from exc
    require_exact(destination_names, source_names, "copied v2 output closure")
    for name in source_names:
        source_metadata = os.stat(
            name, dir_fd=source_directory, follow_symlinks=False
        )
        destination_metadata = os.stat(
            name, dir_fd=destination_directory, follow_symlinks=False
        )
        if stat.S_ISREG(source_metadata.st_mode):
            if not stat.S_ISREG(destination_metadata.st_mode):
                raise ClosureError("copied v2 output file type changed")
            source_identity, source_size, source_digest = v2_hash_regular_at(
                source_directory, name, "staged v2 output"
            )
            destination_identity, destination_size, destination_digest = (
                v2_hash_regular_at(
                    destination_directory, name, "copied v2 output"
                )
            )
            if (
                source_size != destination_size
                or source_digest != destination_digest
                or stat.S_IMODE(source_identity[2]) != 0o400
                or stat.S_IMODE(destination_identity[2]) != 0o400
            ):
                raise ClosureError("copied v2 output file bytes or mode changed")
            continue
        if not stat.S_ISDIR(source_metadata.st_mode) or not stat.S_ISDIR(
            destination_metadata.st_mode
        ):
            raise ClosureError("copied v2 output contains a symlink or special file")
        source_child = os.open(
            name,
            os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
            dir_fd=source_directory,
        )
        destination_child = os.open(
            name,
            os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
            dir_fd=destination_directory,
        )
        try:
            v2_compare_output_trees(source_child, destination_child)
        finally:
            os.close(source_child)
            os.close(destination_child)


class V2OutputTransaction:
    """Descriptor-bound, no-replace output transaction for closure-v2 only."""

    def __init__(self, output_dir: Path) -> None:
        self.output_dir = v2_absolute_path(output_dir, "v2 output directory")
        self.output_parent_descriptor = -1
        self.stage_parent_descriptor = -1
        self.stage_descriptor = -1
        self.output_parent_identity = None  # type: Optional[Tuple[int, int, int, int, int]]
        self.stage_identity = None  # type: Optional[Tuple[int, int, int, int, int]]
        self.stage_name = ""
        self.stage_root = Path("/tmp")
        self.checksum_manifest_bytes = None  # type: Optional[bytes]
        self.checksum_expected_files = None  # type: Optional[Tuple[str, ...]]
        self.checksum_stage_namespace = None  # type: Optional[Dict[str, Tuple[str, Tuple[int, ...]]]]
        self.published = False
        self.closed = False
        try:
            self.output_parent_descriptor = v2_open_directory(
                self.output_dir.parent, "v2 output parent"
            )
            self.output_parent_identity = v2_directory_identity(
                os.fstat(self.output_parent_descriptor)
            )
            self.require_output_parent("v2 output parent at transaction start")
            self.require_output_leaf_absent()
            self.stage_parent_descriptor = v2_open_directory(
                Path("/tmp"), "v2 trusted stage parent"
            )
            self.require_output_parent("v2 output parent before trusted stage create")
            for _ in range(32):
                candidate = ".mckernel-rk003-closure.{}.{}".format(
                    os.getpid(), secrets.token_hex(12)
                )
                try:
                    os.mkdir(candidate, 0o700, dir_fd=self.stage_parent_descriptor)
                except FileExistsError:
                    continue
                self.stage_name = candidate
                break
            if not self.stage_name:
                raise ClosureError("cannot allocate a private v2 output stage")
            self.stage_descriptor = os.open(
                self.stage_name,
                os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                dir_fd=self.stage_parent_descriptor,
            )
            metadata = os.fstat(self.stage_descriptor)
            if (
                metadata.st_uid != os.geteuid()
                or stat.S_IMODE(metadata.st_mode) != 0o700
            ):
                raise ClosureError("private v2 output stage identity is unsafe")
            self.stage_identity = v2_directory_identity(metadata)
            self.stage_root = Path("/tmp") / self.stage_name
            self.require_stage("private v2 output stage")
        except Exception:
            self.close(suppress_errors=True)
            raise

    def __enter__(self):
        return self

    def __exit__(self, exception_type, exception, traceback):
        self.close(suppress_errors=exception_type is not None)
        return False

    def require_active(self) -> None:
        if self.closed or self.stage_descriptor < 0:
            raise ClosureError("v2 output transaction is closed")

    def invalidate_checksum_authority(self) -> None:
        self.checksum_manifest_bytes = None
        self.checksum_expected_files = None
        self.checksum_stage_namespace = None

    def require_output_parent(self, label: str) -> None:
        if self.output_parent_identity is None or self.output_parent_descriptor < 0:
            raise ClosureError("v2 output parent is unavailable")
        v2_require_stable_directory(
            self.output_dir.parent,
            self.output_parent_descriptor,
            self.output_parent_identity,
            label,
        )

    def require_stage(self, label: str) -> None:
        self.require_active()
        if self.stage_identity is None or self.stage_parent_descriptor < 0:
            raise ClosureError("private v2 output stage is unavailable")
        require_exact(
            v2_directory_identity(os.fstat(self.stage_descriptor)),
            self.stage_identity,
            label + " descriptor identity",
        )
        reopened = os.open(
            self.stage_name,
            os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
            dir_fd=self.stage_parent_descriptor,
        )
        try:
            require_exact(
                v2_directory_identity(os.fstat(reopened)),
                self.stage_identity,
                label + " held-parent identity",
            )
        finally:
            os.close(reopened)

    def require_output_leaf_absent(self) -> None:
        try:
            metadata = os.stat(
                self.output_dir.name,
                dir_fd=self.output_parent_descriptor,
                follow_symlinks=False,
            )
        except FileNotFoundError:
            return
        except OSError as exc:
            raise ClosureError("cannot inspect v2 output leaf: {}".format(exc)) from exc
        if stat.S_ISLNK(metadata.st_mode):
            raise ClosureError("v2 output leaf must not be a symlink")
        if stat.S_ISDIR(metadata.st_mode):
            raise ClosureError("v2 output leaf already exists as a directory")
        if stat.S_ISREG(metadata.st_mode):
            raise ClosureError("v2 output leaf already exists as a regular file")
        raise ClosureError("v2 output leaf already exists as a special file")

    def normalized(self, relative: PurePosixPath) -> PurePosixPath:
        return phase_one.normalized_relative_path(
            relative.as_posix(), "v2 output path"
        )

    def open_relative_parent(
        self, relative: PurePosixPath, create: bool
    ) -> Tuple[int, str]:
        normalized = self.normalized(relative)
        self.require_stage("v2 output stage before relative open")
        descriptor = os.dup(self.stage_descriptor)
        try:
            for component in normalized.parts[:-1]:
                if create:
                    try:
                        os.mkdir(component, 0o700, dir_fd=descriptor)
                    except FileExistsError:
                        pass
                child = os.open(
                    component,
                    os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                    dir_fd=descriptor,
                )
                metadata = os.fstat(child)
                if (
                    metadata.st_uid != os.geteuid()
                    or stat.S_IMODE(metadata.st_mode) != 0o700
                ):
                    os.close(child)
                    raise ClosureError("v2 output parent identity is unsafe")
                os.close(descriptor)
                descriptor = child
            result = descriptor
            descriptor = -1
            return result, normalized.name
        except ClosureError:
            raise
        except OSError as exc:
            raise ClosureError("cannot safely open v2 output parent: {}".format(exc)) from exc
        finally:
            if descriptor >= 0:
                os.close(descriptor)

    def path(self, relative: PurePosixPath) -> Path:
        normalized = self.normalized(relative)
        self.require_stage("v2 output stage before path use")
        return self.stage_root.joinpath(*normalized.parts)

    def directory_path(self, relative: PurePosixPath) -> Path:
        normalized = self.normalized(relative)
        parent_descriptor, name = self.open_relative_parent(normalized, False)
        child = -1
        try:
            child = os.open(
                name,
                os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                dir_fd=parent_descriptor,
            )
            metadata = os.fstat(child)
            if (
                metadata.st_uid != os.geteuid()
                or stat.S_IMODE(metadata.st_mode) != 0o700
            ):
                raise ClosureError("v2 output directory identity is unsafe")
        except OSError as exc:
            raise ClosureError("cannot safely open v2 output directory: {}".format(exc)) from exc
        finally:
            if child >= 0:
                os.close(child)
            os.close(parent_descriptor)
        return self.path(normalized)

    def write_bytes(self, relative: PurePosixPath, data: bytes) -> Path:
        if not isinstance(data, bytes):
            raise ClosureError("v2 output data must be bytes")
        self.invalidate_checksum_authority()
        self.require_output_parent("v2 output parent before staged output write")
        parent_descriptor, name = self.open_relative_parent(relative, True)
        descriptor = -1
        created = False
        try:
            descriptor = os.open(
                name,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                0o600,
                dir_fd=parent_descriptor,
            )
            created = True
            metadata = os.fstat(descriptor)
            if (
                not stat.S_ISREG(metadata.st_mode)
                or metadata.st_nlink != 1
                or metadata.st_uid != os.geteuid()
            ):
                raise ClosureError("new v2 output file identity is unsafe")
            v2_write_all(descriptor, data, "v2 staged output")
            os.fchmod(descriptor, 0o400)
            os.fsync(descriptor)
            final = os.fstat(descriptor)
            if final.st_size != len(data) or stat.S_IMODE(final.st_mode) != 0o400:
                raise ClosureError("v2 staged output file is incomplete")
            os.fsync(parent_descriptor)
        except ClosureError:
            raise
        except OSError as exc:
            raise ClosureError("cannot write v2 staged output: {}".format(exc)) from exc
        finally:
            if descriptor >= 0:
                os.close(descriptor)
            if created and sys.exc_info()[0] is not None:
                try:
                    os.unlink(name, dir_fd=parent_descriptor)
                except OSError:
                    pass
            os.close(parent_descriptor)
        self.require_output_parent("v2 output parent after staged output write")
        return self.path(relative)

    def copy_file(
        self,
        source: Path,
        relative: PurePosixPath,
        maximum_bytes: Optional[int] = None,
    ) -> Path:
        self.invalidate_checksum_authority()
        self.require_output_parent("v2 output parent before staged output copy")
        source_descriptor = open_regular_read(source, "v2 output copy source")
        try:
            parent_descriptor, name = self.open_relative_parent(relative, True)
        except Exception:
            os.close(source_descriptor)
            raise
        destination_descriptor = -1
        created = False
        try:
            before = v2_regular_identity(os.fstat(source_descriptor))
            if maximum_bytes is not None:
                if type(maximum_bytes) is not int or maximum_bytes < 1:
                    raise ClosureError("v2 output copy byte bound is invalid")
                if before[6] < 1 or before[6] > maximum_bytes:
                    raise ClosureError("v2 output copy source exceeds its byte bound")
            destination_descriptor = os.open(
                name,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                0o600,
                dir_fd=parent_descriptor,
            )
            created = True
            copied = 0
            while copied < before[6]:
                chunk = os.read(
                    source_descriptor, min(1024 * 1024, before[6] - copied)
                )
                if not chunk:
                    raise ClosureError("v2 output copy source is truncated")
                copied += len(chunk)
                v2_write_all(destination_descriptor, chunk, "v2 staged output copy")
            if os.read(source_descriptor, 1):
                raise ClosureError("v2 output copy source grew while copied")
            after = v2_regular_identity(os.fstat(source_descriptor))
            if before != after or copied != before[6]:
                raise ClosureError("v2 output copy source changed while copied")
            os.fchmod(destination_descriptor, 0o400)
            os.fsync(destination_descriptor)
            destination = os.fstat(destination_descriptor)
            if (
                not stat.S_ISREG(destination.st_mode)
                or destination.st_nlink != 1
                or destination.st_size != copied
                or stat.S_IMODE(destination.st_mode) != 0o400
            ):
                raise ClosureError("v2 staged output copy is incomplete")
            os.fsync(parent_descriptor)
        except ClosureError:
            raise
        except OSError as exc:
            raise ClosureError("cannot copy v2 staged output: {}".format(exc)) from exc
        finally:
            os.close(source_descriptor)
            if destination_descriptor >= 0:
                os.close(destination_descriptor)
            if created and sys.exc_info()[0] is not None:
                try:
                    os.unlink(name, dir_fd=parent_descriptor)
                except OSError:
                    pass
            os.close(parent_descriptor)
        self.require_output_parent("v2 output parent after staged output copy")
        return self.path(relative)

    def read_bytes(self, relative: PurePosixPath) -> bytes:
        parent_descriptor, name = self.open_relative_parent(relative, False)
        descriptor = -1
        try:
            descriptor = os.open(
                name,
                os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK,
                dir_fd=parent_descriptor,
            )
            before = v2_regular_identity(os.fstat(descriptor))
            if not stat.S_ISREG(before[2]):
                raise ClosureError("v2 output input is not a regular file")
            chunks = []
            size = 0
            while True:
                chunk = os.read(descriptor, 1024 * 1024)
                if not chunk:
                    break
                size += len(chunk)
                chunks.append(chunk)
            after = v2_regular_identity(os.fstat(descriptor))
            if before != after or size != before[6]:
                raise ClosureError("v2 output input changed while read")
            return b"".join(chunks)
        except ClosureError:
            raise
        except OSError as exc:
            raise ClosureError("cannot read v2 staged output: {}".format(exc)) from exc
        finally:
            if descriptor >= 0:
                os.close(descriptor)
            os.close(parent_descriptor)

    def hash_file(self, relative: PurePosixPath) -> Tuple[int, str]:
        parent_descriptor, name = self.open_relative_parent(relative, False)
        try:
            _, size, digest = v2_hash_regular_at(
                parent_descriptor, name, "v2 staged output"
            )
            return size, digest
        finally:
            os.close(parent_descriptor)

    def list_files(self) -> List[str]:
        result: List[str] = []

        def visit(directory_descriptor: int, prefix: PurePosixPath) -> None:
            before_names = sorted(os.listdir(directory_descriptor))
            for name in before_names:
                if name in ("", ".", "..") or "/" in name:
                    raise ClosureError("v2 staged output contains an unsafe name")
                metadata = os.stat(
                    name, dir_fd=directory_descriptor, follow_symlinks=False
                )
                relative = prefix / name
                if stat.S_ISREG(metadata.st_mode):
                    if metadata.st_nlink != 1 or metadata.st_uid != os.geteuid():
                        raise ClosureError("v2 staged output file identity is unsafe")
                    result.append(relative.as_posix())
                elif stat.S_ISDIR(metadata.st_mode):
                    child = os.open(
                        name,
                        os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                        dir_fd=directory_descriptor,
                    )
                    try:
                        visit(child, relative)
                    finally:
                        os.close(child)
                else:
                    raise ClosureError(
                        "v2 staged output contains a symlink or special file"
                    )
            require_exact(
                sorted(os.listdir(directory_descriptor)),
                before_names,
                "v2 staged output directory closure",
            )

        self.require_stage("v2 output stage before enumeration")
        visit(self.stage_descriptor, PurePosixPath())
        result.sort()
        return result

    def write_json(self, relative: PurePosixPath, value: Mapping[str, Any]) -> Path:
        return self.write_bytes(relative, phase_one.canonical_json_bytes(value))

    def write_sha256sums(self) -> Path:
        files = self.list_files()
        if not files or "SHA256SUMS" in files:
            raise ClosureError("v2 staged output checksum state is invalid")
        rows = []
        for name in files:
            _, digest = self.hash_file(PurePosixPath(name))
            rows.append("{}  {}".format(digest, name))
        return self.write_bytes(
            PurePosixPath("SHA256SUMS"), ("\n".join(rows) + "\n").encode("ascii")
        )

    def verify_sha256sums(self, expected_files: Sequence[str]) -> None:
        manifest, namespace, _ = v2_verify_checksum_directory(
            self.stage_descriptor,
            expected_files=expected_files,
        )
        self.checksum_manifest_bytes = manifest
        self.checksum_expected_files = tuple(sorted(expected_files))
        self.checksum_stage_namespace = namespace

    def publish(self) -> None:
        self.require_active()
        if self.published:
            raise ClosureError("v2 output transaction is already published")
        if (
            self.checksum_manifest_bytes is None
            or self.checksum_expected_files is None
            or self.checksum_stage_namespace is None
        ):
            raise ClosureError(
                "v2 output must pass exact checksum verification before publication"
            )
        self.require_stage("v2 output stage before publication")
        _, stage_namespace, _ = v2_verify_checksum_directory(
            self.stage_descriptor,
            self.checksum_manifest_bytes,
            self.checksum_expected_files,
        )
        require_exact(
            stage_namespace,
            self.checksum_stage_namespace,
            "verified v2 stage identity before publication",
        )
        self.require_output_parent("v2 output parent before publication directory create")
        self.require_output_leaf_absent()
        hidden_name = ".{}.publish.{}.{}".format(
            self.output_dir.name, os.getpid(), secrets.token_hex(12)
        )
        hidden_descriptor = -1
        final_descriptor = -1
        hidden_identity = None  # type: Optional[Tuple[int, int, int, int, int]]
        renamed = False
        committed = False
        try:
            os.mkdir(hidden_name, 0o700, dir_fd=self.output_parent_descriptor)
            hidden_descriptor = os.open(
                hidden_name,
                os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                dir_fd=self.output_parent_descriptor,
            )
            hidden_identity = v2_directory_identity(os.fstat(hidden_descriptor))
            self.require_output_parent("v2 output parent before publication copy")
            hidden_copy_namespace = v2_copy_output_tree(
                self.stage_descriptor, hidden_descriptor
            )
            v2_compare_output_trees(self.stage_descriptor, hidden_descriptor)
            _, stage_after_copy, _ = v2_verify_checksum_directory(
                self.stage_descriptor,
                self.checksum_manifest_bytes,
                self.checksum_expected_files,
            )
            require_exact(
                stage_after_copy,
                self.checksum_stage_namespace,
                "verified v2 stage identity after publication copy",
            )
            _, hidden_namespace, _ = v2_verify_checksum_directory(
                hidden_descriptor,
                self.checksum_manifest_bytes,
                self.checksum_expected_files,
            )
            require_exact(
                hidden_namespace,
                hidden_copy_namespace,
                "verified hidden v2 output preserved copy identities",
            )
            os.fsync(hidden_descriptor)
            self.require_output_parent("v2 output parent before publication rename")
            _, hidden_before_rename, _ = v2_verify_checksum_directory(
                hidden_descriptor,
                self.checksum_manifest_bytes,
                self.checksum_expected_files,
            )
            require_exact(
                hidden_before_rename,
                hidden_namespace,
                "verified hidden v2 output identity before rename",
            )
            v2_rename_noreplace(
                self.output_parent_descriptor,
                hidden_name,
                self.output_parent_descriptor,
                self.output_dir.name,
            )
            renamed = True
            final_descriptor = os.open(
                self.output_dir.name,
                os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                dir_fd=self.output_parent_descriptor,
            )
            require_exact(
                v2_directory_identity(os.fstat(final_descriptor)),
                hidden_identity,
                "published v2 output directory identity",
            )
            _, final_namespace, _ = v2_verify_checksum_directory(
                final_descriptor,
                self.checksum_manifest_bytes,
                self.checksum_expected_files,
            )
            require_exact(
                final_namespace,
                hidden_namespace,
                "published v2 output preserved hidden identities",
            )
            _, final_stage_namespace, _ = v2_verify_checksum_directory(
                self.stage_descriptor,
                self.checksum_manifest_bytes,
                self.checksum_expected_files,
            )
            require_exact(
                final_stage_namespace,
                self.checksum_stage_namespace,
                "verified v2 stage identity after publication",
            )
            os.fsync(self.output_parent_descriptor)
            self.require_output_parent("v2 output parent after publication")
            _, final_replay_namespace, _ = v2_verify_checksum_directory(
                final_descriptor,
                self.checksum_manifest_bytes,
                self.checksum_expected_files,
            )
            require_exact(
                final_replay_namespace,
                final_namespace,
                "published v2 output final verification replay",
            )
            v2_require_output_namespace(
                self.stage_descriptor,
                self.checksum_stage_namespace,
                "verified v2 stage final identity replay",
            )
            v2_require_output_namespace(
                final_descriptor,
                final_replay_namespace,
                "published v2 output final namespace replay",
            )
            committed = True
            self.published = True
        except ClosureError:
            raise
        except OSError as exc:
            raise ClosureError("v2 output publication failed: {}".format(exc)) from exc
        finally:
            cleanup_descriptor = (
                final_descriptor
                if final_descriptor >= 0
                else hidden_descriptor
            )
            if not committed and cleanup_descriptor >= 0:
                try:
                    v2_remove_directory_contents(cleanup_descriptor)
                    os.fsync(cleanup_descriptor)
                except ClosureError:
                    pass
            if final_descriptor >= 0:
                os.close(final_descriptor)
            if hidden_descriptor >= 0:
                os.close(hidden_descriptor)
            if not committed:
                cleanup_name = self.output_dir.name if renamed else hidden_name
                try:
                    if hidden_identity is not None:
                        v2_remove_named_directory_if_identity(
                            self.output_parent_descriptor,
                            cleanup_name,
                            hidden_identity,
                        )
                except ClosureError:
                    pass

    def close(self, suppress_errors: bool = False) -> None:
        if self.closed:
            return
        error = None  # type: Optional[Exception]
        if self.stage_descriptor >= 0:
            try:
                v2_remove_directory_contents(self.stage_descriptor)
                os.fsync(self.stage_descriptor)
            except Exception as exc:
                error = exc
            finally:
                os.close(self.stage_descriptor)
                self.stage_descriptor = -1
        if self.stage_parent_descriptor >= 0 and self.stage_name:
            try:
                if self.stage_identity is not None:
                    v2_remove_named_directory_if_identity(
                        self.stage_parent_descriptor,
                        self.stage_name,
                        self.stage_identity,
                    )
                os.fsync(self.stage_parent_descriptor)
            except Exception as exc:
                if error is None:
                    error = exc
        if self.stage_parent_descriptor >= 0:
            os.close(self.stage_parent_descriptor)
            self.stage_parent_descriptor = -1
        if self.output_parent_descriptor >= 0:
            os.close(self.output_parent_descriptor)
            self.output_parent_descriptor = -1
        self.closed = True
        if error is not None and not suppress_errors:
            if isinstance(error, ClosureError):
                raise error
            raise ClosureError("cannot clean private v2 output stage: {}".format(error))


def read_json(path: Path, label: str) -> Tuple[Dict[str, Any], bytes]:
    data = read_regular_bytes(path, label)
    try:
        value = json.loads(
            data.decode("utf-8"), object_pairs_hook=phase_one.reject_duplicate_pairs
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ClosureError("cannot parse {}: {}".format(label, exc)) from exc
    if not isinstance(value, dict):
        raise ClosureError("{} must be a JSON object".format(label))
    return value, data


def safe_repo_file(repo: Path, relative: str) -> Path:
    try:
        return phase_one.repository_file(repo, Path(relative))
    except phase_one.EvidenceError as exc:
        raise ClosureError(str(exc)) from exc


def runtime_os_release_bytes() -> bytes:
    requested = Path("/etc/os-release")
    try:
        resolved = requested.resolve(strict=True)
    except OSError as exc:
        raise ClosureError("cannot resolve runtime os-release: {}".format(exc)) from exc
    allowed = {requested, Path("/usr/lib/os-release")}
    if resolved not in allowed:
        raise ClosureError("runtime os-release resolves outside its standard locations")
    return read_regular_bytes(resolved, "runtime os-release")


def parse_python36_source(source: str, label: str) -> None:
    """Reject syntax and annotation forms that cannot import on Python 3.6."""
    try:
        try:
            ast.parse(source, filename=label, feature_version=(3, 6))
        except TypeError:
            try:
                ast.parse(source, filename=label, feature_version=6)
            except TypeError:
                ast.parse(source, filename=label)
    except SyntaxError as exc:
        raise ClosureError("{} is not Python 3.6 parseable: {}".format(label, exc)) from exc
    forbidden = (
        (r"from\s+__future__\s+import\s+annotations", "postponed annotations"),
        (r"\b(?:list|dict|set|tuple)\s*\[[^\]]", "built-in generic annotation"),
        (
            r"(?:->|:)\s*[A-Za-z_][A-Za-z0-9_.\[\], ]*\s\|\s(?:None|[A-Za-z_])",
            "PEP 604 union annotation",
        ),
    )
    for pattern, description in forbidden:
        if re.search(pattern, source):
            raise ClosureError("{} uses a Python 3.6-incompatible {}".format(label, description))


def local_python_imports(source: str) -> List[str]:
    tree = ast.parse(source)
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            names.add(node.module.split(".")[0])
    return sorted(names)


def python36_runtime_paths(repo: Path) -> List[str]:
    pending = list(PYTHON36_ENTRYPOINT_PATHS)
    observed: List[str] = []
    while pending:
        relative = pending.pop(0)
        if relative in observed:
            continue
        path = safe_repo_file(repo, relative)
        try:
            source = read_regular_bytes(path, relative).decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ClosureError("{} is not UTF-8".format(relative)) from exc
        parse_python36_source(source, relative)
        observed.append(relative)
        for module in local_python_imports(source):
            candidate = "scripts/{}.py".format(module)
            candidate_path = repo / candidate
            if candidate not in observed and candidate not in pending and candidate_path.exists():
                pending.append(candidate)
    return observed


def validate_python36_runtime(repo: Path) -> None:
    runtime_paths = python36_runtime_paths(repo)
    if len(runtime_paths) < len(PYTHON36_ENTRYPOINT_PATHS):
        raise ClosureError("Python 3.6 runtime import closure is incomplete")


def validate_legacy_contract(repo: Path) -> Dict[str, Any]:
    contract_path = safe_repo_file(repo, LEGACY_CONTRACT_PATH.as_posix())
    contract, contract_bytes = read_json(contract_path, "legacy closure contract")
    require_exact(
        hashlib.sha256(contract_bytes).hexdigest(),
        LEGACY_EXPECTED_CONTRACT_SHA256,
        "legacy closure contract digest",
    )
    exact_keys(
        contract,
        {
            "claim_scope",
            "direct_phase",
            "gate_claims",
            "network_contract",
            "outputs",
            "phase_id",
            "required_probe_ids",
            "schema_version",
            "success_blockers",
            "toolchain_lock",
        },
        "closure contract",
    )
    require_exact(contract["schema_version"], SCHEMA_VERSION, "contract schema")
    require_exact(contract["phase_id"], PHASE_ID, "contract phase")
    expected_claims = {
        "RK-002": False,
        "RK-003": False,
        "RK-004": False,
        "RK-005": False,
        "RK-006": False,
        "RS-001": False,
    }
    require_exact(contract["gate_claims"], expected_claims, "gate claims")
    if not isinstance(contract["claim_scope"], str) or "never awards" not in contract[
        "claim_scope"
    ]:
        raise ClosureError("contract claim scope is not fail-closed")
    direct = exact_keys(
        contract["direct_phase"],
        {
            "artifact_id",
            "artifact_name",
            "historical_build_requirements_sha256",
            "historical_checkpoint_sha256",
            "effective_buildrequires_count",
            "github_repository",
            "head_sha",
            "outer_zip_sha256",
            "resolution_root_count",
            "resolution_inputs_sha256",
            "reviewed_rocky_rust_count",
            "run_attempt",
            "run_id",
        },
        "direct phase",
    )
    for field in (
        "historical_build_requirements_sha256",
        "historical_checkpoint_sha256",
        "outer_zip_sha256",
        "resolution_inputs_sha256",
    ):
        if not isinstance(direct[field], str) or not HEX_SHA256.fullmatch(direct[field]):
            raise ClosureError("direct phase {} is not a SHA-256".format(field))
    if not re.fullmatch(r"[0-9a-f]{40}", str(direct["head_sha"])):
        raise ClosureError("direct phase head SHA is malformed")
    require_exact(direct["resolution_root_count"], 109, "resolution root count")
    require_exact(direct["effective_buildrequires_count"], 86, "BuildRequires count")
    require_exact(direct["reviewed_rocky_rust_count"], 3, "Rust addition count")

    lock = exact_keys(contract["toolchain_lock"], {"id", "path", "sha256"}, "toolchain binding")
    lock_path = safe_repo_file(repo, str(lock["path"]))
    _, digest = sha256_file(lock_path)
    require_exact(digest, lock["sha256"], "toolchain lock digest")
    toolchain, _ = read_json(lock_path, "toolchain lock")
    require_exact(toolchain.get("lock_id"), lock["id"], "toolchain lock ID")
    require_exact(toolchain.get("gate", {}).get("credit_eligible"), False, "RK-003 credit")
    probe_ids = [item.get("id") for item in toolchain.get("required_probes", [])]
    require_exact(contract["required_probe_ids"], probe_ids, "required probe IDs")
    require_exact(
        contract["outputs"],
        [
            "closure.json",
            "offline-replay.json",
            "probes.json",
            "rpm-macros.json",
            "environment.json",
            "blockers.json",
            "checkpoint.json",
            "SHA256SUMS",
        ],
        "contract outputs",
    )
    blockers = contract["success_blockers"]
    if not isinstance(blockers, list) or len(blockers) != 9 or not all(
        isinstance(item, str) and item.strip() for item in blockers
    ):
        raise ClosureError("successful capture must retain nine blockers")
    if "marks closure-offline unimplemented" not in blockers[-2]:
        raise ClosureError("phase-plan reconciliation blocker is missing")
    require_exact(
        blockers[-1], LLVM_OWNER_AUTHORITY_BLOCKER, "LLVM owner authority blocker"
    )
    network = exact_keys(
        contract["network_contract"],
        {"acquisition", "offline_replay", "scope"},
        "network contract",
    )
    if "configured network sources" not in str(network["acquisition"]):
        raise ClosureError("acquisition network boundary is overstated")
    if "not kernel-level network isolation" not in str(network["scope"]):
        raise ClosureError("network claim boundary is missing")
    return contract


def validate_metadata_reconciliation(
    repo: Path, value: object, toolchain: Mapping[str, Any]
) -> Mapping[str, Any]:
    """Validate the local-only status and probe-owner overlay."""
    reconciliation = exact_keys(
        value,
        {"claims", "llvm_config_owner", "phase_plan", "scope"},
        "metadata reconciliation",
    )
    claims = exact_keys(
        reconciliation["claims"],
        METADATA_RECONCILIATION_FALSE_CLAIMS,
        "metadata reconciliation claims",
    )
    for claim in sorted(METADATA_RECONCILIATION_FALSE_CLAIMS):
        require_exact(claims[claim], False, "metadata reconciliation claim " + claim)
    require_exact(
        reconciliation["scope"],
        METADATA_RECONCILIATION_SCOPE,
        "metadata reconciliation scope",
    )

    phase = exact_keys(
        reconciliation["phase_plan"],
        {
            "historical_implemented",
            "implementation_available",
            "path",
            "phase_id",
            "sha256",
            "scope",
        },
        "phase-plan reconciliation",
    )
    require_exact(
        phase["path"], phase_one.PLAN_PATH.as_posix(), "historical phase-plan path"
    )
    phase_plan_path = safe_repo_file(repo, str(phase["path"]))
    phase_plan_size, phase_plan_digest = sha256_file(phase_plan_path)
    if phase_plan_size < 1:
        raise ClosureError("historical phase plan is empty")
    require_exact(
        phase_plan_digest, phase_one.EXPECTED_PLAN_SHA256, "historical phase-plan digest"
    )
    require_exact(
        phase["sha256"], phase_plan_digest, "phase-plan reconciliation digest"
    )
    require_exact(phase["phase_id"], PHASE_ID, "phase-plan reconciliation phase")
    require_exact(
        phase["historical_implemented"],
        False,
        "historical closure implementation state",
    )
    require_exact(
        phase["implementation_available"],
        True,
        "closure-v2 implementation availability",
    )
    require_exact(
        phase["scope"],
        PHASE_PLAN_RECONCILIATION_SCOPE,
        "phase-plan reconciliation scope",
    )
    phase_plan, _ = read_json(phase_plan_path, "historical phase plan")
    phases = phase_plan.get("phases")
    if not isinstance(phases, list):
        raise ClosureError("historical phase plan phases are missing")
    historical_rows = [
        row for row in phases if isinstance(row, dict) and row.get("id") == PHASE_ID
    ]
    if len(historical_rows) != 1:
        raise ClosureError("historical closure phase is ambiguous")
    require_exact(
        historical_rows[0].get("implemented"),
        phase["historical_implemented"],
        "historical closure phase implementation state",
    )

    owner = exact_keys(
        reconciliation["llvm_config_owner"],
        {
            "binary_path",
            "command",
            "expected_package_nevra",
            "historical_direct_artifact_name",
            "historical_direct_artifact_nevra",
            "probe_id",
            "scope",
        },
        "llvm-config owner reconciliation",
    )
    require_exact(owner["probe_id"], "llvm", "llvm-config probe ID")
    require_exact(
        owner["binary_path"], "/usr/bin/llvm-config", "llvm-config binary path"
    )
    require_exact(
        owner["command"], ["llvm-config", "--version"], "llvm-config command"
    )
    require_exact(
        owner["historical_direct_artifact_name"],
        "llvm",
        "historical LLVM artifact name",
    )
    require_exact(
        owner["historical_direct_artifact_nevra"],
        LOCKED_LLVM_PROBE_OWNER_NEVRA,
        "historical LLVM artifact NEVRA",
    )
    require_exact(
        owner["expected_package_nevra"],
        LLVM_CONFIG_OWNER_NEVRA,
        "llvm-config expected owner",
    )
    require_exact(
        owner["scope"],
        LLVM_CONFIG_OWNER_SCOPE,
        "llvm-config owner reconciliation scope",
    )

    probes = toolchain.get("required_probes")
    artifacts = toolchain.get("direct_artifacts")
    if not isinstance(probes, list) or not isinstance(artifacts, list):
        raise ClosureError("historical LLVM authority is missing")
    probe_rows = [
        row
        for row in probes
        if isinstance(row, dict) and row.get("id") == owner["probe_id"]
    ]
    artifact_rows = [
        row
        for row in artifacts
        if isinstance(row, dict)
        and row.get("name") == owner["historical_direct_artifact_name"]
    ]
    if len(probe_rows) != 1 or len(artifact_rows) != 1:
        raise ClosureError("historical LLVM probe authority is ambiguous")
    require_exact(
        probe_rows[0].get("artifact"),
        owner["historical_direct_artifact_name"],
        "historical LLVM probe artifact",
    )
    require_exact(
        probe_rows[0].get("command"), owner["command"], "historical LLVM probe command"
    )
    require_exact(
        artifact_rows[0].get("nevra"),
        owner["historical_direct_artifact_nevra"],
        "historical LLVM probe artifact NEVRA",
    )
    if owner["expected_package_nevra"] == owner["historical_direct_artifact_nevra"]:
        raise ClosureError("llvm-config owner reconciliation did not change the owner")
    return reconciliation


def validate_v2_success_blockers(value: object) -> List[str]:
    """Validate the exact ordered, fail-closed closure-v2 blocker authority."""
    if type(value) is not list:
        raise ClosureError("v2 success blockers must be an exact list")
    require_exact(
        len(value), len(V2_SUCCESS_BLOCKERS), "v2 success blocker count"
    )
    for index, expected in enumerate(V2_SUCCESS_BLOCKERS):
        require_exact(
            value[index], expected, "v2 success blocker {}".format(index)
        )
    return value


def validate_contract(repo: Path) -> Dict[str, Any]:
    """Validate the snapshot-backed v2 capture contract without awarding credit."""
    contract_path = safe_repo_file(repo, CONTRACT_PATH.as_posix())
    contract, contract_bytes = read_json(contract_path, "closure v2 contract")
    require_exact(
        hashlib.sha256(contract_bytes).hexdigest(),
        EXPECTED_CONTRACT_SHA256,
        "closure v2 contract digest",
    )
    exact_keys(
        contract,
        {
            "claim_scope",
            "gate_claims",
            "historical_review_anchor",
            "metadata_reconciliation",
            "network_contract",
            "outputs",
            "phase_id",
            "required_probe_ids",
            "resolution_authority",
            "schema_version",
            "snapshot_authority",
            "success_blockers",
            "toolchain_lock",
        },
        "closure v2 contract",
    )
    require_exact(contract["schema_version"], V2_SCHEMA_VERSION, "v2 contract schema")
    require_exact(contract["phase_id"], PHASE_ID, "v2 contract phase")
    expected_claims = {
        "RK-002": False,
        "RK-003": False,
        "RK-004": False,
        "RK-005": False,
        "RK-006": False,
        "RS-001": False,
    }
    validate_false_gate_claims(
        contract["gate_claims"], expected_claims, "v2 gate claims"
    )
    if not isinstance(contract["claim_scope"], str) or "never awards" not in contract[
        "claim_scope"
    ]:
        raise ClosureError("v2 contract claim scope is not fail-closed")

    historical = exact_keys(
        contract["historical_review_anchor"],
        {
            "closure_contract_path",
            "closure_contract_sha256",
            "repository_direct_artifact_sha256",
            "repository_direct_head_sha",
            "scope",
        },
        "historical review anchor",
    )
    require_exact(
        historical["closure_contract_path"],
        LEGACY_CONTRACT_PATH.as_posix(),
        "legacy contract path",
    )
    legacy_size, legacy_digest = sha256_file(
        safe_repo_file(repo, LEGACY_CONTRACT_PATH.as_posix())
    )
    if legacy_size < 1:
        raise ClosureError("legacy closure contract is empty")
    require_exact(
        legacy_digest,
        LEGACY_EXPECTED_CONTRACT_SHA256,
        "legacy closure contract binding",
    )
    require_exact(
        historical["closure_contract_sha256"],
        legacy_digest,
        "historical closure contract digest",
    )
    for field in ("repository_direct_artifact_sha256", "closure_contract_sha256"):
        if not isinstance(historical[field], str) or not HEX_SHA256.fullmatch(
            historical[field]
        ):
            raise ClosureError("historical {} is not a SHA-256".format(field))
    if not re.fullmatch(r"[0-9a-f]{40}", str(historical["repository_direct_head_sha"])):
        raise ClosureError("historical repository-direct head is malformed")
    if "Historical provenance only" not in str(historical["scope"]):
        raise ClosureError("historical review scope is ambiguous")

    snapshot = exact_keys(
        contract["snapshot_authority"],
        {
            "artifact_digest_source",
            "binary_repository_ids",
            "capture_id",
            "claims_must_remain_false",
            "current_source_commit_required",
            "git_authority",
            "release_key",
            "repositories",
            "required_repository_inputs",
            "schema_version",
            "source_repository_id",
            "workflow_ref_prefix",
        },
        "snapshot authority",
    )
    require_exact(snapshot["schema_version"], 2, "snapshot authority schema")
    require_exact(snapshot["capture_id"], snapshot_v2.CAPTURE_ID, "snapshot capture ID")
    require_exact(snapshot["claims_must_remain_false"], True, "snapshot claim policy")
    require_exact(
        snapshot["current_source_commit_required"], True, "snapshot source policy"
    )
    require_exact(
        snapshot["git_authority"],
        snapshot_v2.GIT_AUTHORITY_POLICY,
        "snapshot Git authority policy",
    )
    require_exact(
        snapshot["workflow_ref_prefix"],
        snapshot_v2.WORKFLOW_REF_PREFIX,
        "snapshot workflow-ref prefix",
    )
    if "workflow-dispatch input" not in str(snapshot["artifact_digest_source"]):
        raise ClosureError("snapshot artifact digest source is not external")
    expected_repositories = [
        {"id": item[0], "kind": item[1], "base_url": item[2]}
        for item in snapshot_v2.REPOSITORIES
    ]
    require_exact(snapshot["repositories"], expected_repositories, "snapshot repositories")
    require_exact(
        snapshot["binary_repository_ids"],
        ["baseos", "appstream", "crb"],
        "snapshot binary repositories",
    )
    require_exact(
        snapshot["source_repository_id"], "source-baseos", "snapshot source repository"
    )
    require_exact(
        snapshot["release_key"],
        {
            "fingerprint": snapshot_v2.RELEASE_FINGERPRINT,
            "sha256": snapshot_v2.RELEASE_KEY_SHA256,
            "size": snapshot_v2.RELEASE_KEY_SIZE,
        },
        "snapshot release key",
    )
    required_inputs = snapshot["required_repository_inputs"]
    expected_input_roles = ["workflow", "contract", "checker", "tests"]
    if not isinstance(required_inputs, list) or len(required_inputs) != len(
        expected_input_roles
    ):
        raise ClosureError("snapshot input authority coverage changed")
    for index, role in enumerate(expected_input_roles):
        row = exact_keys(
            required_inputs[index],
            {"path", "role", "sha256", "size"},
            "snapshot input authority {}".format(index),
        )
        require_exact(row["role"], role, "snapshot input authority role")
        require_exact(
            row["path"], snapshot_v2.REQUIRED_INPUTS[role], "snapshot input authority path"
        )
        if not isinstance(row["sha256"], str) or not HEX_SHA256.fullmatch(row["sha256"]):
            raise ClosureError("snapshot input authority digest is malformed")
        if type(row["size"]) is not int or row["size"] < 1:
            raise ClosureError("snapshot input authority size is invalid")
        observed_size, observed_digest = sha256_file(safe_repo_file(repo, row["path"]))
        require_exact(observed_size, row["size"], "snapshot input authority size")
        require_exact(observed_digest, row["sha256"], "snapshot input authority digest")

    resolution = exact_keys(
        contract["resolution_authority"],
        {
            "direct_nevra_count",
            "direct_nevras_sha256",
            "effective_buildrequires_count",
            "kernel_spec",
            "resolution_inputs_sha256",
            "resolution_root_count",
            "reviewed_rocky_rust_additions",
            "reviewed_rocky_rust_count",
            "rpmspec_command",
        },
        "resolution authority",
    )
    for field in ("direct_nevras_sha256", "resolution_inputs_sha256"):
        if not isinstance(resolution[field], str) or not HEX_SHA256.fullmatch(
            resolution[field]
        ):
            raise ClosureError("resolution {} is not a SHA-256".format(field))
    require_exact(resolution["direct_nevra_count"], 20, "direct NEVRA count")
    require_exact(
        resolution["effective_buildrequires_count"], 86, "effective BuildRequires count"
    )
    require_exact(resolution["resolution_root_count"], 109, "resolution root count")
    require_exact(resolution["reviewed_rocky_rust_count"], 3, "reviewed Rust count")
    require_exact(
        resolution["reviewed_rocky_rust_additions"],
        ["bindgen", "rust", "rust-src"],
        "reviewed Rust additions",
    )
    require_exact(
        resolution["rpmspec_command"],
        ["rpmspec", "-q", "--buildrequires", "--target", "x86_64-linux-gnu", "kernel.spec"],
        "rpmspec command",
    )
    spec = exact_keys(
        resolution["kernel_spec"],
        {"dist_git_commit", "path", "sha256", "size"},
        "kernel spec authority",
    )
    if not re.fullmatch(r"[0-9a-f]{40}", str(spec["dist_git_commit"])):
        raise ClosureError("kernel spec dist-git commit is malformed")
    require_exact(spec["path"], "SPECS/kernel.spec", "kernel spec path")
    if not isinstance(spec["sha256"], str) or not HEX_SHA256.fullmatch(spec["sha256"]):
        raise ClosureError("kernel spec digest is malformed")
    if type(spec["size"]) is not int or spec["size"] < 1:
        raise ClosureError("kernel spec size is invalid")

    require_exact(
        contract["outputs"],
        [
            "closure.json",
            "offline-replay.json",
            "probes.json",
            "rpm-macros.json",
            "environment.json",
            "resolution-input.json",
            "snapshot-input.json",
            "blockers.json",
            "checkpoint.json",
            "SHA256SUMS",
        ],
        "v2 contract outputs",
    )
    network = exact_keys(
        contract["network_contract"],
        {"metadata", "rpm_acquisition", "scope", "source_input"},
        "v2 network contract",
    )
    if "verified canonical" not in str(network["metadata"]):
        raise ClosureError("snapshot metadata boundary is missing")
    if "three exact" not in str(network["rpm_acquisition"]):
        raise ClosureError("RPM acquisition boundary is missing")
    if "not kernel-level network isolation" not in str(network["scope"]):
        raise ClosureError("network claim boundary is missing")
    if "no redirects" not in str(network["source_input"]):
        raise ClosureError("source-input redirect boundary is missing")

    lock = exact_keys(
        contract["toolchain_lock"], {"id", "path", "sha256"}, "toolchain binding"
    )
    lock_path = safe_repo_file(repo, str(lock["path"]))
    _, lock_digest = sha256_file(lock_path)
    require_exact(lock_digest, lock["sha256"], "toolchain lock digest")
    toolchain, _ = read_json(lock_path, "toolchain lock")
    require_exact(toolchain.get("lock_id"), lock["id"], "toolchain lock ID")
    require_exact(toolchain.get("gate", {}).get("credit_eligible"), False, "RK-003 credit")
    probe_ids = [item.get("id") for item in toolchain.get("required_probes", [])]
    require_exact(contract["required_probe_ids"], probe_ids, "required probe IDs")
    direct_nevras = toolchain.get("closure", {}).get("direct_nevras")
    if not isinstance(direct_nevras, list):
        raise ClosureError("toolchain direct NEVRA list is missing")
    require_exact(len(direct_nevras), resolution["direct_nevra_count"], "direct NEVRA count")
    require_exact(
        hashlib.sha256(phase_one.canonical_json_bytes(direct_nevras)).hexdigest(),
        resolution["direct_nevras_sha256"],
        "direct NEVRA digest",
    )
    validate_metadata_reconciliation(
        repo, contract["metadata_reconciliation"], toolchain
    )
    validate_v2_success_blockers(contract["success_blockers"])
    return contract


def expected_direct_bundle_paths(
    plan: Mapping[str, Any], toolchain: Mapping[str, Any]
) -> List[str]:
    paths = {
        "archives/repositories/RPM-GPG-KEY-Rocky-10",
        "blockers.json",
        "bootstrap-input.json",
        "build-requirements.json",
        "checkpoint.json",
        "direct-rpms.json",
        "environment.json",
        "inputs/kernel-x86_64-rhel.config",
        "inputs/kernel.spec",
        "repository-snapshots.json",
        "transcripts/bootstrap-rpms.txt",
        "transcripts/rpm-showrc.txt",
        "transcripts/rpmspec-buildrequires.txt",
        "transcripts/tool-versions.txt",
    }
    for repository in plan["repositories"]:
        repository_id = repository["id"]
        primary_name = PurePosixPath(repository["primary"]["href"]).name
        paths.update(
            {
                "archives/repositories/{}/repomd.xml".format(repository_id),
                "archives/repositories/{}/repomd.xml.asc".format(repository_id),
                "archives/repositories/{}/{}".format(repository_id, primary_name),
                "transcripts/repomd/{}.gpgv.txt".format(repository_id),
            }
        )
    for artifact in toolchain["direct_artifacts"]:
        filename = PurePosixPath(artifact["repository_location"]).name
        paths.add("archives/direct-rpms/{}".format(filename))
        paths.add("transcripts/rpmkeys/{}.txt".format(filename))
    return sorted(paths)


def verify_sha256sums(
    root: Path,
    expected_files: Optional[Sequence[str]] = None,
    label: str = "bundle",
) -> None:
    manifest = root / "SHA256SUMS"
    data = read_regular_bytes(manifest, label + " SHA256SUMS")
    if not data or not data.endswith(b"\n"):
        raise ClosureError("{} SHA256SUMS is malformed".format(label))
    listed: List[str] = []
    for line in data.decode("ascii").splitlines():
        match = re.fullmatch(r"([0-9a-f]{64})  ([^\0\r\n]+)", line)
        if match is None:
            raise ClosureError("{} SHA256SUMS has a malformed row".format(label))
        relative = phase_one.normalized_relative_path(match.group(2), "checksum path")
        path = root.joinpath(*relative.parts)
        resolved = path.resolve()
        if (
            path.is_symlink()
            or path != resolved
            or os.path.commonpath((str(root), str(resolved))) != str(root)
            or not path.is_file()
        ):
            raise ClosureError("checksummed {} input is not a regular file".format(label))
        _, digest = sha256_file(path)
        require_exact(digest, match.group(1), "direct input checksum")
        listed.append(relative.as_posix())
    actual: List[str] = []
    for path in root.rglob("*"):
        if path.is_symlink() or (not path.is_file() and not path.is_dir()):
            raise ClosureError("{} contains a symlink or special file".format(label))
        if path.is_file() and path != manifest:
            actual.append(path.relative_to(root).as_posix())
    actual.sort()
    require_exact(listed, sorted(listed), "checksum path order")
    require_exact(listed, actual, label + " checksum closure")
    if expected_files is not None:
        require_exact(actual, sorted(expected_files), label + " exact file set")


def validate_download_record(
    value: object, expected_url: str, expected_sha256: str, expected_size: int, label: str
) -> None:
    row = exact_keys(
        value, {"final_url", "redirect_count", "sha256", "size"}, label
    )
    require_exact(row["final_url"], expected_url, label + " final URL")
    require_exact(row["redirect_count"], 0, label + " redirects")
    require_exact(row["sha256"], expected_sha256, label + " digest")
    require_exact(row["size"], expected_size, label + " size")


def validate_direct_checkpoint(
    root: Path,
    direct: Mapping[str, Any],
    expected_identity: Optional[Mapping[str, Any]],
) -> Tuple[Dict[str, Any], bytes]:
    checkpoint, checkpoint_bytes = read_json(root / "checkpoint.json", "direct checkpoint")
    exact_keys(
        checkpoint,
        {
            "acquisition",
            "checkpoint_id",
            "credit_eligible",
            "gate_claims",
            "github",
            "manifests",
            "phase",
            "schema_version",
            "successful_capture_requires_review",
        },
        "direct checkpoint",
    )
    acquisition = exact_keys(
        checkpoint["acquisition"],
        {
            "collector_http_after_seal",
            "collector_http_downloaded_bytes",
            "collector_http_sealed",
            "network_isolation_claimed",
            "scope",
        },
        "direct acquisition",
    )
    require_exact(acquisition["collector_http_after_seal"], False, "direct post-seal HTTP")
    require_exact(acquisition["collector_http_sealed"], True, "direct acquisition seal")
    require_exact(acquisition["network_isolation_claimed"], False, "direct network claim")
    if not isinstance(acquisition["collector_http_downloaded_bytes"], int) or acquisition[
        "collector_http_downloaded_bytes"
    ] < 1:
        raise ClosureError("direct acquisition byte count is invalid")
    require_exact(checkpoint["checkpoint_id"], phase_one.CHECKPOINT_ID, "direct checkpoint ID")
    require_exact(checkpoint["phase"], "repository-direct", "direct phase ID")
    require_exact(checkpoint["schema_version"], SCHEMA_VERSION, "direct checkpoint schema")
    require_exact(checkpoint["credit_eligible"], False, "direct phase credit")
    require_exact(checkpoint["gate_claims"], {"RK-003": False, "RK-005": False}, "direct gate claims")
    require_exact(
        checkpoint["successful_capture_requires_review"], True, "direct review requirement"
    )
    github = exact_keys(
        checkpoint["github"], {"head_sha", "repository", "run_attempt", "run_id"}, "direct GitHub identity"
    )
    if expected_identity is None:
        require_exact(github["head_sha"], direct["head_sha"], "direct head SHA")
        require_exact(github["repository"], direct["github_repository"], "direct repository")
        require_exact(github["run_id"], direct["run_id"], "direct run ID")
        require_exact(github["run_attempt"], direct["run_attempt"], "direct run attempt")
        require_exact(
            hashlib.sha256(checkpoint_bytes).hexdigest(),
            direct["historical_checkpoint_sha256"],
            "historical direct checkpoint digest",
        )
    else:
        require_exact(dict(github), dict(expected_identity), "current direct/capture identity")
    manifests = checkpoint["manifests"]
    if not isinstance(manifests, list) or len(manifests) != len(DIRECT_MANIFEST_NAMES):
        raise ClosureError("direct checkpoint manifest coverage changed")
    observed_names = []
    for index, item in enumerate(manifests):
        row = exact_keys(item, {"path", "sha256", "size"}, "direct manifest {}".format(index))
        relative = phase_one.normalized_relative_path(row["path"], "direct manifest path")
        if relative.parts != (relative.name,):
            raise ClosureError("direct checkpoint manifest must be top-level")
        path = root / relative.name
        size, digest = sha256_file(path)
        require_exact(size, row["size"], relative.name + " size")
        require_exact(digest, row["sha256"], relative.name + " digest")
        observed_names.append(relative.name)
    require_exact(observed_names, DIRECT_MANIFEST_NAMES, "direct manifest order")
    return checkpoint, checkpoint_bytes


def validate_direct_bundle_manifests(
    root: Path, plan: Mapping[str, Any], toolchain: Mapping[str, Any]
) -> None:
    repositories, _ = read_json(root / "repository-snapshots.json", "repository snapshots")
    exact_keys(repositories, {"release_key", "repositories", "schema_version"}, "repository snapshots")
    require_exact(repositories["schema_version"], SCHEMA_VERSION, "repository snapshot schema")
    release_key = exact_keys(
        repositories["release_key"], {"download", "fingerprint", "path"}, "snapshot release key"
    )
    require_exact(release_key["fingerprint"], plan["release_key"]["fingerprint"], "release-key fingerprint")
    require_exact(release_key["path"], "archives/repositories/RPM-GPG-KEY-Rocky-10", "release-key path")
    validate_download_record(
        release_key["download"],
        plan["release_key"]["url"],
        plan["release_key"]["sha256"],
        plan["release_key"]["size"],
        "release-key download",
    )
    repository_rows = repositories["repositories"]
    if not isinstance(repository_rows, list) or len(repository_rows) != len(plan["repositories"]):
        raise ClosureError("repository snapshot count changed")
    for locked, item in zip(plan["repositories"], repository_rows):
        row = exact_keys(
            item,
            {
                "base_url",
                "id",
                "primary_download",
                "primary_open",
                "repomd",
                "repomd_download",
                "signature",
                "signature_download",
            },
            "repository snapshot",
        )
        require_exact(row["id"], locked["id"], "repository ID")
        require_exact(row["base_url"], locked["base_url"], "repository base URL")
        validate_download_record(
            row["repomd_download"],
            locked["repomd"]["url"],
            locked["repomd"]["sha256"],
            locked["repomd"]["size"],
            locked["id"] + " repomd download",
        )
        validate_download_record(
            row["signature_download"],
            locked["signature"]["url"],
            locked["signature"]["sha256"],
            locked["signature"]["size"],
            locked["id"] + " signature download",
        )
        validate_download_record(
            row["primary_download"],
            locked["base_url"] + locked["primary"]["href"],
            locked["primary"]["sha256"],
            locked["primary"]["size"],
            locked["id"] + " primary download",
        )
        primary_open = exact_keys(row["primary_open"], {"open_sha256", "open_size"}, "primary open identity")
        require_exact(primary_open, {"open_sha256": locked["primary"]["open_sha256"], "open_size": locked["primary"]["open_size"]}, "primary open identity")
        repomd = exact_keys(row["repomd"], {"primary", "revision"}, "repomd result")
        require_exact(repomd["primary"], locked["primary"], "repomd primary identity")
        require_exact(repomd["revision"], locked["repomd"]["revision"], "repomd revision")
        signature = exact_keys(
            row["signature"],
            {"status", "transcript_sha256", "transcript_size", "validsig_fingerprint"},
            "repomd signature",
        )
        require_exact(signature["status"], "verified", "repomd signature status")
        require_exact(signature["validsig_fingerprint"], plan["release_key"]["fingerprint"], "repomd signer")

    direct, _ = read_json(root / "direct-rpms.json", "direct RPM manifest")
    exact_keys(
        direct,
        {"all_archives_verified", "all_header_signatures_verified", "artifact_count", "artifacts", "scope", "schema_version"},
        "direct RPM manifest",
    )
    require_exact(direct["all_archives_verified"], True, "direct archive verification")
    require_exact(direct["all_header_signatures_verified"], True, "direct signature verification")
    require_exact(direct["schema_version"], SCHEMA_VERSION, "direct RPM schema")
    require_exact(direct["artifact_count"], len(toolchain["direct_artifacts"]), "direct RPM count")
    artifacts = direct["artifacts"]
    if not isinstance(artifacts, list) or len(artifacts) != len(toolchain["direct_artifacts"]):
        raise ClosureError("direct RPM artifact coverage changed")
    for locked, item in zip(toolchain["direct_artifacts"], artifacts):
        row = exact_keys(
            item,
            {"arch", "archive_path", "download", "metadata", "name", "nevra", "repository_id", "signature"},
            "direct RPM artifact",
        )
        for field in ("arch", "name", "nevra", "repository_id"):
            require_exact(row[field], locked[field], "direct RPM " + field)
        filename = PurePosixPath(locked["repository_location"]).name
        require_exact(row["archive_path"], "archives/direct-rpms/{}".format(filename), "direct RPM path")
        repository = next(value for value in plan["repositories"] if value["id"] == locked["repository_id"])
        validate_download_record(
            row["download"],
            repository["base_url"] + locked["repository_location"],
            locked["sha256"],
            locked["size"],
            locked["nevra"] + " download",
        )
        metadata = exact_keys(row["metadata"], {"location", "sha256", "size"}, "direct RPM metadata")
        require_exact(metadata, {"location": locked["repository_location"], "sha256": locked["sha256"], "size": locked["size"]}, "direct RPM metadata")
        signature = exact_keys(
            row["signature"],
            {"header_signature_algorithm", "signer_fingerprint", "signer_key_id", "status", "transcript_sha256", "transcript_size"},
            "direct RPM signature",
        )
        require_exact(signature["status"], "verified", "direct RPM signature status")
        require_exact(signature["signer_fingerprint"], plan["release_key"]["fingerprint"], "direct RPM signer")

    environment, _ = read_json(root / "environment.json", "direct environment")
    exact_keys(
        environment,
        {"architecture", "bootstrap", "bootstrap_package_count", "bootstrap_packages_sha256", "committed_inputs", "container_image", "container_manifest_digest", "container_platform", "github", "os_release", "tool_versions"},
        "direct environment",
    )
    require_exact(environment["architecture"], "x86_64", "direct environment architecture")
    require_exact(environment["container_image"], phase_one.CONTAINER_IMAGE, "direct container image")
    require_exact(
        environment["container_manifest_digest"],
        plan["container"]["manifest_digest"],
        "direct container manifest",
    )
    require_exact(environment["container_platform"], plan["container"]["platform"], "direct container platform")
    github = exact_keys(
        environment["github"], {"head_sha", "repository", "run_attempt", "run_id"}, "direct environment GitHub identity"
    )
    checkpoint, _ = read_json(root / "checkpoint.json", "direct checkpoint")
    require_exact(dict(github), checkpoint["github"], "direct environment/checkpoint identity")
    require_exact(environment["os_release"], {"id": "rocky", "version_id": "10.2"}, "direct environment OS")
    bootstrap = exact_keys(
        environment["bootstrap"],
        {"after_package_manifest_sha256", "local_rpm_install_verified", "manifest_sha256"},
        "direct bootstrap environment",
    )
    require_exact(bootstrap["local_rpm_install_verified"], True, "direct bootstrap install")
    for field in ("after_package_manifest_sha256", "manifest_sha256"):
        if not isinstance(bootstrap[field], str) or not HEX_SHA256.fullmatch(bootstrap[field]):
            raise ClosureError("direct bootstrap {} is not a SHA-256".format(field))
    if not isinstance(environment["bootstrap_package_count"], int) or environment[
        "bootstrap_package_count"
    ] < 1:
        raise ClosureError("direct bootstrap package count is invalid")
    if not isinstance(environment["bootstrap_packages_sha256"], str) or not HEX_SHA256.fullmatch(
        environment["bootstrap_packages_sha256"]
    ):
        raise ClosureError("direct bootstrap inventory digest is malformed")
    expected_input_paths = [
        value.as_posix()
        for value in (
            phase_one.PLAN_PATH,
            phase_one.TOOLCHAIN_LOCK_PATH,
            phase_one.CONFIG_POLICY_PATH,
            phase_one.CONFIG_FRAGMENT_PATH,
            phase_one.SOURCE_LOCK_PATH,
            phase_one.PATCH_SERIES_PATH,
            phase_one.PLATFORM_VALIDATOR_PATH,
            phase_one.SOURCE_VALIDATOR_PATH,
            phase_one.CAPTURE_SCRIPT_PATH,
            phase_one.WORKFLOW_PATH,
        )
    ]
    committed = environment["committed_inputs"]
    if not isinstance(committed, list) or len(committed) != len(expected_input_paths):
        raise ClosureError("direct committed-input coverage changed")
    for index, (expected_path, item) in enumerate(zip(expected_input_paths, committed)):
        row = exact_keys(item, {"path", "sha256", "size"}, "direct committed input {}".format(index))
        require_exact(row["path"], expected_path, "direct committed-input path")
        if not isinstance(row["sha256"], str) or not HEX_SHA256.fullmatch(row["sha256"]):
            raise ClosureError("direct committed-input digest is malformed")
        if not isinstance(row["size"], int) or row["size"] < 1:
            raise ClosureError("direct committed-input size is invalid")
    tool_versions = exact_keys(
        environment["tool_versions"], {"gpg", "python", "rpm", "rpmspec"}, "direct tool versions"
    )
    expected_commands = {
        "gpg": ["gpg", "--version"],
        "python": ["python3", "--version"],
        "rpm": ["rpm", "--version"],
        "rpmspec": ["rpmspec", "--version"],
    }
    for name, command in expected_commands.items():
        row = exact_keys(
            tool_versions[name], {"command", "output_sha256", "output_size"}, "direct {} version".format(name)
        )
        require_exact(row["command"], command, "direct {} command".format(name))
        if not isinstance(row["output_sha256"], str) or not HEX_SHA256.fullmatch(row["output_sha256"]):
            raise ClosureError("direct tool version digest is malformed")
        if not isinstance(row["output_size"], int) or row["output_size"] < 1:
            raise ClosureError("direct tool version output is empty")
    blockers, _ = read_json(root / "blockers.json", "direct blockers")
    exact_keys(
        blockers,
        {"config_lock_blockers_at_capture", "gate_claims", "phase_blockers", "source_lock_blockers_at_capture", "source_lock_credit_eligible_at_capture", "toolchain_lock_blockers_at_capture"},
        "direct blockers",
    )
    require_exact(blockers["gate_claims"], {"RK-003": False, "RK-005": False}, "direct blocker gate claims")
    for field in (
        "config_lock_blockers_at_capture",
        "phase_blockers",
        "toolchain_lock_blockers_at_capture",
    ):
        values = blockers[field]
        if not isinstance(values, list) or not values or not all(
            isinstance(value, str) and value.strip() for value in values
        ):
            raise ClosureError("direct blocker list is empty or malformed: {}".format(field))
    source_blockers = blockers["source_lock_blockers_at_capture"]
    if not isinstance(source_blockers, list) or not all(
        isinstance(value, str) and value.strip() for value in source_blockers
    ):
        raise ClosureError("direct source-lock blocker list is malformed")
    require_exact(
        blockers["source_lock_credit_eligible_at_capture"],
        not source_blockers,
        "direct source-lock credit",
    )


def validate_direct_root(
    root: Path,
    contract: Mapping[str, Any],
    expected_identity: Optional[Mapping[str, Any]] = None,
    expected_files: Optional[Sequence[str]] = None,
    plan: Optional[Mapping[str, Any]] = None,
    toolchain: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    requested_root = root
    if requested_root.is_symlink() or not requested_root.is_dir():
        raise ClosureError("direct phase root must be a regular directory")
    root = requested_root.resolve()
    verify_sha256sums(root, expected_files, "direct bundle")
    direct = contract["direct_phase"]
    validate_direct_checkpoint(root, direct, expected_identity)
    build, build_bytes = read_json(root / "build-requirements.json", "BuildRequires")
    exact_keys(
        build,
        {
            "closure_complete",
            "collector_http_sealed_before_derivation",
            "direct_nevras",
            "effective_buildrequires",
            "kernel_spec_sha256",
            "network_isolation_claimed",
            "resolution_roots",
            "reviewed_rocky_rust_additions",
            "reviewed_source_change_applied",
            "rpmspec_output_sha256",
            "rpm_showrc_sha256",
            "schema_version",
            "source_spec_condition",
            "transitive_resolution_status",
        },
        "BuildRequires",
    )
    resolution_inputs = {
        key: build.get(key)
        for key in (
            "direct_nevras",
            "effective_buildrequires",
            "kernel_spec_sha256",
            "resolution_roots",
            "reviewed_rocky_rust_additions",
        )
    }
    semantic_digest = hashlib.sha256(
        phase_one.canonical_json_bytes(resolution_inputs)
    ).hexdigest()
    require_exact(
        semantic_digest,
        direct["resolution_inputs_sha256"],
        "resolution input digest",
    )
    if expected_identity is None:
        require_exact(
            hashlib.sha256(build_bytes).hexdigest(),
            direct["historical_build_requirements_sha256"],
            "historical BuildRequires digest",
        )
    require_exact(len(build.get("resolution_roots", [])), direct["resolution_root_count"], "resolution roots")
    require_exact(len(build.get("effective_buildrequires", [])), direct["effective_buildrequires_count"], "effective BuildRequires")
    require_exact(len(build.get("reviewed_rocky_rust_additions", [])), direct["reviewed_rocky_rust_count"], "reviewed Rust roots")
    require_exact(build.get("closure_complete"), False, "direct closure state")
    require_exact(build["collector_http_sealed_before_derivation"], True, "direct derivation seal")
    require_exact(build["network_isolation_claimed"], False, "direct network claim")
    require_exact(build["reviewed_source_change_applied"], False, "reviewed source change state")
    require_exact(build["schema_version"], SCHEMA_VERSION, "BuildRequires schema")
    require_exact(build["transitive_resolution_status"], "required-missing", "direct closure status")
    if plan is not None and toolchain is not None:
        require_exact(build["direct_nevras"], toolchain["closure"]["direct_nevras"], "direct NEVRA order")
        require_exact(
            build["reviewed_rocky_rust_additions"],
            plan["resolution_policy"]["reviewed_rocky_rust_buildrequires"],
            "reviewed Rust additions",
        )
        roots = build["resolution_roots"]
        if not isinstance(roots, list):
            raise ClosureError("resolution roots must be a list")
        for index, item in enumerate(roots):
            exact_keys(item, {"kind", "value"}, "resolution root {}".format(index))
        expected_roots = []
        expected_roots.extend(
            {"kind": "rocky-effective-spec", "value": item}
            for item in build["effective_buildrequires"]
        )
        expected_roots.extend(
            {"kind": "reviewed-rocky-rust", "value": item}
            for item in build["reviewed_rocky_rust_additions"]
        )
        expected_roots.extend(
            {"kind": "locked-direct-nevra", "value": item}
            for item in build["direct_nevras"]
        )
        require_exact(roots, expected_roots, "resolution-root construction")
        for field in ("kernel_spec_sha256", "rpmspec_output_sha256", "rpm_showrc_sha256"):
            if not isinstance(build[field], str) or not HEX_SHA256.fullmatch(build[field]):
                raise ClosureError("BuildRequires {} is not a SHA-256".format(field))
        require_exact(
            build["source_spec_condition"],
            toolchain["source_spec_observation"]["rust_buildrequires_condition"],
            "source spec condition",
        )
        validate_direct_bundle_manifests(root, plan, toolchain)
    return build


def primary_index(primary_path: Path, repository_id: str) -> Dict[str, Dict[str, Any]]:
    index: Dict[str, Dict[str, Any]] = {}
    count = 0
    try:
        stream = gzip.open(str(primary_path), "rb")
        context = ET.iterparse(stream, events=("end",))
        for _, element in context:
            if element.tag != "{" + phase_one.COMMON_NS + "}package":
                continue
            count += 1
            if count > MAX_PRIMARY_PACKAGES:
                raise ClosureError("primary metadata package bound exceeded")
            name = element.findtext("{" + phase_one.COMMON_NS + "}name")
            arch = element.findtext("{" + phase_one.COMMON_NS + "}arch")
            version = element.find("{" + phase_one.COMMON_NS + "}version")
            checksum = element.find("{" + phase_one.COMMON_NS + "}checksum")
            location = element.find("{" + phase_one.COMMON_NS + "}location")
            size = element.find("{" + phase_one.COMMON_NS + "}size")
            if None in (version, checksum, location, size) or not name or not arch:
                raise ClosureError("primary metadata package is incomplete")
            if checksum.get("type") != "sha256" or checksum.get("pkgid") != "YES":
                raise ClosureError("primary package checksum is not a SHA-256 pkgid")
            epoch = version.get("epoch") or "0"
            ver = version.get("ver")
            rel = version.get("rel")
            href = location.get("href")
            package_size = size.get("package")
            if not ver or not rel or not href or not package_size or not package_size.isdigit():
                raise ClosureError("primary metadata identity is malformed")
            normalized_href = phase_one.normalized_relative_path(
                href, "primary package location"
            )
            if normalized_href.parts[0] != "Packages" or normalized_href.suffix != ".rpm":
                raise ClosureError("primary package location has an unsafe layout")
            nevra = "{}-{}:{}-{}.{}".format(name, epoch, ver, rel, arch)
            row = {
                "arch": arch,
                "nevra": nevra,
                "repository_id": repository_id,
                "repository_location": normalized_href.as_posix(),
                "sha256": (checksum.text or "").strip(),
                "size": int(package_size),
            }
            if not HEX_SHA256.fullmatch(row["sha256"]):
                raise ClosureError("primary package digest is malformed")
            previous = index.get(nevra)
            if previous is not None and previous != row:
                raise ClosureError("primary metadata has ambiguous NEVRA {}".format(nevra))
            index[nevra] = row
            element.clear()
    except (OSError, EOFError, ET.ParseError) as exc:
        raise ClosureError("cannot parse primary metadata: {}".format(exc)) from exc
    finally:
        try:
            stream.close()
        except (NameError, OSError):
            pass
    if not index:
        raise ClosureError("primary metadata contains no packages")
    return index


def load_primary_indexes(
    snapshot_roots: Mapping[str, Path], plan: Mapping[str, Any]
) -> Dict[str, Dict[str, Any]]:
    combined: Dict[str, Dict[str, Any]] = {}
    for repository in plan["repositories"]:
        repository_id = repository["id"]
        href = PurePosixPath(repository["primary"]["href"])
        path = snapshot_roots[repository_id].joinpath(*href.parts)
        size, digest = sha256_file(path)
        require_exact(size, repository["primary"]["size"], "primary compressed size")
        require_exact(digest, repository["primary"]["sha256"], "primary compressed digest")
        phase_one.verify_primary_open_identity(
            path,
            repository["primary"]["open_sha256"],
            repository["primary"]["open_size"],
        )
        for nevra, row in primary_index(path, repository_id).items():
            previous = combined.get(nevra)
            if previous is not None and previous != row:
                raise ClosureError("repository snapshots disagree for {}".format(nevra))
            combined[nevra] = row
    return combined


def repomd_data_rows(
    repomd_path: Path, repository: Mapping[str, Any]
) -> List[Dict[str, Any]]:
    data = read_regular_bytes(repomd_path, "signed repomd")
    try:
        phase_one.parse_repomd(data, repository)
    except phase_one.EvidenceError as exc:
        raise ClosureError(str(exc)) from exc
    if b"<!DOCTYPE" in data.upper() or b"<!ENTITY" in data.upper():
        raise ClosureError("repomd XML declarations are forbidden")
    try:
        root = ET.fromstring(data)
    except ET.ParseError as exc:
        raise ClosureError("cannot parse repomd data rows: {}".format(exc)) from exc
    namespace = "{" + phase_one.REPO_NS + "}"
    rows: List[Dict[str, Any]] = []
    seen_types = set()
    seen_locations = set()
    for element in root.findall(namespace + "data"):
        data_type = element.get("type")
        checksum = element.find(namespace + "checksum")
        open_checksum = element.find(namespace + "open-checksum")
        location = element.find(namespace + "location")
        size_text = element.findtext(namespace + "size")
        open_size_text = element.findtext(namespace + "open-size")
        if (
            not data_type
            or checksum is None
            or checksum.get("type") != "sha256"
            or location is None
            or not size_text
            or not size_text.isdigit()
        ):
            raise ClosureError("repomd data row is incomplete")
        if data_type in seen_types:
            raise ClosureError("repomd data type is duplicated: {}".format(data_type))
        relative = phase_one.normalized_relative_path(
            location.get("href"), "repomd data location"
        )
        if relative.parts[0] != "repodata" or relative.as_posix() in seen_locations:
            raise ClosureError("repomd data location is duplicated or unsafe")
        digest = (checksum.text or "").strip()
        if not HEX_SHA256.fullmatch(digest):
            raise ClosureError("repomd data digest is malformed")
        size = int(size_text)
        if not 1 <= size <= MAX_METADATA_OBJECT_BYTES:
            raise ClosureError("repomd data compressed size exceeds its bound")
        if (open_checksum is None) != (open_size_text is None):
            raise ClosureError("repomd open identity is incomplete")
        open_digest = None
        open_size = None
        if open_checksum is not None:
            if open_checksum.get("type") != "sha256" or not open_size_text or not open_size_text.isdigit():
                raise ClosureError("repomd open identity is malformed")
            open_digest = (open_checksum.text or "").strip()
            open_size = int(open_size_text)
            if not HEX_SHA256.fullmatch(open_digest) or not 1 <= open_size <= MAX_METADATA_OPEN_BYTES:
                raise ClosureError("repomd open identity exceeds its bound")
        rows.append(
            {
                "href": relative.as_posix(),
                "open_sha256": open_digest,
                "open_size": open_size,
                "sha256": digest,
                "size": size,
                "type": data_type,
            }
        )
        seen_types.add(data_type)
        seen_locations.add(relative.as_posix())
    if not rows or len(rows) > MAX_REPOMD_OBJECTS:
        raise ClosureError("repomd data row count is empty or exceeds its bound")
    primary = [row for row in rows if row["type"] == "primary"]
    if len(primary) != 1:
        raise ClosureError("repomd must contain exactly one primary object")
    require_exact(primary[0]["href"], repository["primary"]["href"], "primary metadata href")
    require_exact(primary[0]["sha256"], repository["primary"]["sha256"], "primary metadata digest")
    require_exact(primary[0]["size"], repository["primary"]["size"], "primary metadata size")
    require_exact(primary[0]["open_sha256"], repository["primary"]["open_sha256"], "primary open digest")
    require_exact(primary[0]["open_size"], repository["primary"]["open_size"], "primary open size")
    return rows


def verify_metadata_open_identity(path: Path, row: Mapping[str, Any]) -> bool:
    expected_digest = row["open_sha256"]
    expected_size = row["open_size"]
    if expected_digest is None:
        return False
    suffix = PurePosixPath(row["href"]).suffix
    if suffix == ".gz":
        stream = gzip.open(str(path), "rb")
    elif suffix == ".bz2":
        stream = bz2.open(str(path), "rb")
    elif suffix == ".xz":
        stream = lzma.open(str(path), "rb")
    elif suffix == ".zck" and shutil.which("unzck") is None:
        # repomd signs the compressed object identity independently.  The
        # minimal pinned container need not carry the optional zchunk CLI, so
        # retain the exact object but do not overclaim its open identity.
        return False
    elif suffix in (".zst", ".zck"):
        arguments = (
            ["zstd", "--decompress", "--stdout", str(path)]
            if suffix == ".zst"
            else ["unzck", "--stdout", str(path)]
        )
        try:
            process = subprocess.Popen(
                arguments, stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
        except OSError as exc:
            raise ClosureError("metadata decompressor is unavailable: {}".format(exc)) from exc
        if process.stdout is None or process.stderr is None:
            process.kill()
            raise ClosureError("metadata decompressor pipes are unavailable")
        digest = hashlib.sha256()
        size = 0
        while True:
            chunk = process.stdout.read(1024 * 1024)
            if not chunk:
                break
            size += len(chunk)
            if size > expected_size or size > MAX_METADATA_OPEN_BYTES:
                process.kill()
                process.wait()
                raise ClosureError("metadata expands beyond its signed bound")
            digest.update(chunk)
        stderr = process.stderr.read()
        return_code = process.wait()
        if return_code != 0:
            raise ClosureError("metadata decompressor failed: {}".format(stderr.decode("utf-8", errors="replace").strip()))
        if stderr:
            raise ClosureError("metadata decompressor wrote stderr")
        require_exact(size, expected_size, "metadata open size")
        require_exact(digest.hexdigest(), expected_digest, "metadata open digest")
        return True
    else:
        size, digest = sha256_file(path)
        require_exact(size, expected_size, "uncompressed metadata size")
        require_exact(digest, expected_digest, "uncompressed metadata digest")
        return True
    digest = hashlib.sha256()
    size = 0
    try:
        with stream:
            while True:
                chunk = stream.read(1024 * 1024)
                if not chunk:
                    break
                size += len(chunk)
                if size > expected_size or size > MAX_METADATA_OPEN_BYTES:
                    raise ClosureError("metadata expands beyond its signed bound")
                digest.update(chunk)
    except (OSError, EOFError, lzma.LZMAError) as exc:
        raise ClosureError("cannot decompress signed metadata: {}".format(exc)) from exc
    require_exact(size, expected_size, "metadata open size")
    require_exact(digest.hexdigest(), expected_digest, "metadata open digest")
    return True


def materialize_snapshot_repositories(
    direct_root: Path,
    output_root: Path,
    plan: Mapping[str, Any],
    gpg_keyring: Path,
) -> Tuple[Dict[str, Path], List[Dict[str, Any]]]:
    session = phase_one.NetworkSession(
        plan["network_policy"]["collector_http_allowed_hosts_before_seal"]
    )
    roots: Dict[str, Path] = {}
    manifests: List[Dict[str, Any]] = []
    for repository in plan["repositories"]:
        repository_id = repository["id"]
        source_root = direct_root / "archives" / "repositories" / repository_id
        relative_root = PurePosixPath("archives/snapshot-repositories") / repository_id
        snapshot_root = output_root.joinpath(*relative_root.parts)
        roots[repository_id] = snapshot_root
        repomd_relative = relative_root / "repodata/repomd.xml"
        signature_relative = relative_root / "repodata/repomd.xml.asc"
        repomd_path = copy_archive(source_root / "repomd.xml", output_root, repomd_relative)
        signature_path = copy_archive(
            source_root / "repomd.xml.asc", output_root, signature_relative
        )
        size, digest = sha256_file(repomd_path)
        require_exact(size, repository["repomd"]["size"], repository_id + " repomd size")
        require_exact(digest, repository["repomd"]["sha256"], repository_id + " repomd digest")
        signature, transcript = phase_one.verify_repomd_signature(
            repomd_path,
            signature_path,
            gpg_keyring,
            plan["release_key"]["fingerprint"],
        )
        phase_one.write_output_bytes(
            output_root,
            PurePosixPath("transcripts/snapshot-repomd") / (repository_id + ".gpgv.txt"),
            transcript,
        )
        metadata_rows = []
        for row in repomd_data_rows(repomd_path, repository):
            href = PurePosixPath(row["href"])
            target_relative = relative_root / href
            if row["type"] == "primary":
                source = source_root / href.name
                target = copy_archive(source, output_root, target_relative)
                download = {
                    "final_url": repository["base_url"] + href.as_posix(),
                    "redirect_count": 0,
                    "sha256": row["sha256"],
                    "size": row["size"],
                    "source": "verified repository-direct archive",
                }
            else:
                target = phase_one.output_path(output_root, target_relative)
                download = session.download_exact(
                    repository["base_url"] + href.as_posix(),
                    target,
                    row["sha256"],
                    row["size"],
                    MAX_METADATA_OBJECT_BYTES,
                )
                download["source"] = "bounded no-redirect HTTPS acquisition"
            size, digest = sha256_file(target)
            require_exact(size, row["size"], "signed metadata size")
            require_exact(digest, row["sha256"], "signed metadata digest")
            observed = dict(row)
            observed["archive_path"] = target_relative.as_posix()
            observed["download"] = download
            observed["open_identity_verified"] = verify_metadata_open_identity(target, row)
            observed["signed_compressed_identity_verified"] = True
            metadata_rows.append(observed)
        manifests.append(
            {
                "base_url": repository["base_url"],
                "id": repository_id,
                "local_repository_path": relative_root.as_posix(),
                "metadata": metadata_rows,
                "repomd_sha256": repository["repomd"]["sha256"],
                "repomd_signature": signature,
            }
        )
    session.seal()
    if not session.sealed:
        raise ClosureError("metadata acquisition did not seal")
    return roots, manifests


def dnf_base_arguments(installroot: Path, cache_root: str) -> List[str]:
    return [
        "dnf",
        "--noplugins",
        "-y",
        "--config=/dev/null",
        "--installroot",
        str(installroot),
        "--releasever=10.2",
        "--setopt=module_platform_id=platform:el10",
        "--setopt=reposdir=/dev/null",
        "--setopt=install_weak_deps=False",
        "--setopt=keepcache=True",
        "--setopt=cachedir={}".format(cache_root),
        "--setopt=metadata_expire=never",
        "--setopt=strict=True",
        "--setopt=best=True",
        "--setopt=skip_if_unavailable=False",
        "--setopt=gpgcheck=False",
        "--setopt=repo_gpgcheck=False",
        "--disablerepo=*",
    ]


def dnf_repository_id(repository: Mapping[str, Any]) -> str:
    repository_id = repository["id"]
    if not isinstance(repository_id, str) or not re.fullmatch(
        r"[a-z0-9][a-z0-9_-]*", repository_id
    ):
        raise ClosureError("locked DNF repository ID is unsafe")
    return "rk003-snapshot-" + repository_id


def online_command(
    installroot: Path,
    repositories: Sequence[Mapping[str, Any]],
    snapshot_roots: Mapping[str, Path],
    roots: Sequence[str],
) -> List[str]:
    arguments = dnf_base_arguments(installroot, "/var/cache/dnf")
    for repository in repositories:
        snapshot_root = snapshot_roots[repository["id"]]
        command_repository_id = dnf_repository_id(repository)
        if not snapshot_root.is_absolute() or snapshot_root.is_symlink() or not snapshot_root.is_dir():
            raise ClosureError("snapshot repository root is unsafe")
        local_url = "file://" + snapshot_root.as_posix()
        arguments.append(
            "--repofrompath={},{}".format(command_repository_id, local_url)
        )
        arguments.append(
            "--setopt={}.baseurl={},{}".format(
                command_repository_id, local_url, repository["base_url"]
            )
        )
        arguments.append(
            "--setopt={}.skip_if_unavailable=False".format(command_repository_id)
        )
        arguments.append("--enablerepo={}".format(command_repository_id))
    arguments.extend(["install", "--downloadonly", "--"])
    arguments.extend(roots)
    return arguments


def snapshot_solve_command(
    installroot: Path,
    repositories: Sequence[Mapping[str, Any]],
    snapshot_roots: Mapping[str, Path],
    roots: Sequence[str],
) -> List[str]:
    arguments = dnf_base_arguments(installroot, "/var/cache/dnf")
    for repository in repositories:
        snapshot_root = snapshot_roots[repository["id"]]
        command_repository_id = dnf_repository_id(repository)
        if not snapshot_root.is_absolute() or snapshot_root.is_symlink() or not snapshot_root.is_dir():
            raise ClosureError("snapshot repository root is unsafe")
        local_url = "file://" + snapshot_root.as_posix()
        arguments.append(
            "--repofrompath={},{}".format(command_repository_id, local_url)
        )
        arguments.append(
            "--setopt={}.skip_if_unavailable=False".format(command_repository_id)
        )
        arguments.append("--enablerepo={}".format(command_repository_id))
    arguments.extend(["install", "--"])
    arguments.extend(roots)
    return arguments


def offline_command(
    installroot: Path, rpm_paths: Sequence[Path]
) -> List[str]:
    arguments = dnf_base_arguments(installroot, "/var/cache/dnf")
    arguments.extend(["--cacheonly", "install", "--"])
    arguments.extend(str(path) for path in rpm_paths)
    return arguments


def run_command(
    arguments: Sequence[str], env: Optional[Mapping[str, str]] = None
) -> Tuple[bytes, bytes]:
    try:
        completed = subprocess.run(
            list(arguments),
            check=True,
            env=dict(env) if env is not None else None,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except OSError as exc:
        raise ClosureError("command unavailable: {}: {}".format(arguments[0], exc)) from exc
    except subprocess.CalledProcessError as exc:
        raise ClosureError(
            "command failed ({}): {}".format(
                " ".join(arguments), exc.stderr.decode("utf-8", errors="replace").strip()
            )
        ) from exc
    return completed.stdout, completed.stderr


def command_transcript(
    arguments: Sequence[str], stdout: bytes, stderr: bytes
) -> bytes:
    command = " ".join(shlex.quote(item) for item in arguments).encode("utf-8")
    return b"command: " + command + b"\nstdout:\n" + stdout + b"stderr:\n" + stderr


def verify_expected_version(
    probe_id: str, expected: Optional[str], output: bytes, owner_nevra: str
) -> None:
    if expected is None:
        return
    try:
        text = output.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ClosureError("{} version output is not UTF-8".format(probe_id)) from exc
    version = re.escape(expected)
    owner_version = re.compile(r"-[0-9]+:{}-".format(version))
    if owner_version.search(owner_nevra) is None:
        raise ClosureError(
            "{} binary owner does not identify exact version {}".format(
                probe_id, expected
            )
        )

    # rustfmt and clippy report their upstream component versions rather than the
    # Rust RPM version carried by expected_version.  Their exact RPM version is
    # still enforced above; the command output must identify the expected tool.
    component_prefixes = {"clippy": "clippy ", "rustfmt": "rustfmt "}
    component_prefix = component_prefixes.get(probe_id)
    if component_prefix is not None:
        if not text.startswith(component_prefix):
            raise ClosureError("{} output does not identify the tool".format(probe_id))
        return

    output_version = re.compile(r"(?<![0-9.]){}(?![A-Za-z0-9.])".format(version))
    if output_version.search(text) is None:
        raise ClosureError(
            "{} output does not identify exact version {}".format(probe_id, expected)
        )


def expected_probe_owner(
    probe_id: str,
    locked_owner_nevra: str,
    llvm_config_owner: Mapping[str, Any],
) -> str:
    if probe_id != llvm_config_owner["probe_id"]:
        return locked_owner_nevra
    require_exact(
        locked_owner_nevra,
        llvm_config_owner["historical_direct_artifact_nevra"],
        "historical LLVM probe authority mapping",
    )
    return llvm_config_owner["expected_package_nevra"]


def validate_probe_binary_path(
    probe_id: str, binary_path: str, llvm_config_owner: Mapping[str, Any]
) -> None:
    """Bind the reconciled llvm-config owner to the binary actually executed."""
    if probe_id == llvm_config_owner["probe_id"]:
        require_exact(
            binary_path,
            llvm_config_owner["binary_path"],
            "llvm-config resolved binary path",
        )


def loaded_libclang_path(stderr: bytes) -> str:
    try:
        stderr_text = stderr.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ClosureError("dynamic-loader evidence is not UTF-8") from exc
    matches = []
    for line in stderr_text.splitlines():
        match = re.search(r"calling init:\s+(/\S*libclang\.so\S*)\s*$", line)
        if match is not None:
            matches.append(match.group(1))
    if len(matches) != 1:
        raise ClosureError("dynamic-loader evidence does not identify one libclang")
    return matches[0]


def stable_environment(base: Mapping[str, str]) -> Dict[str, str]:
    result = dict(base)
    result.update({"LANG": "C", "LC_ALL": "C", "TZ": "UTC"})
    return result


def acquisition_environment(base: Mapping[str, str]) -> Dict[str, str]:
    result = stable_environment(base)
    for key in (
        "ALL_PROXY",
        "FTP_PROXY",
        "HTTP_PROXY",
        "HTTPS_PROXY",
        "NO_PROXY",
        "all_proxy",
        "ftp_proxy",
        "http_proxy",
        "https_proxy",
        "no_proxy",
    ):
        result.pop(key, None)
    return result


def private_environment(base: Mapping[str, str]) -> Dict[str, str]:
    return stable_environment(phase_one.subprocess_network_defense_env(base))


def rpm_nevra(path: Path) -> str:
    stdout, stderr = run_command(["rpm", "-qp", "--qf", RPM_NEVRA_QUERY, str(path)])
    if stderr:
        raise ClosureError("RPM identity query wrote stderr")
    try:
        rows = stdout.decode("utf-8").splitlines()
    except UnicodeDecodeError as exc:
        raise ClosureError("RPM identity is not UTF-8") from exc
    if len(rows) != 1 or not rows[0]:
        raise ClosureError("RPM identity query is ambiguous")
    return rows[0]


def installed_nevras(root: Path) -> List[str]:
    stdout, stderr = run_command(
        ["rpm", "--root", str(root), "-qa", "--qf", RPM_NEVRA_QUERY]
    )
    if stderr:
        raise ClosureError("installroot inventory wrote stderr")
    rows = sorted(row for row in stdout.decode("utf-8").splitlines() if row)
    if not rows or len(rows) != len(set(rows)):
        raise ClosureError("installroot inventory is empty or ambiguous")
    return rows


def verify_transitive_inventory(
    installed: Sequence[str], direct_nevras: Sequence[str]
) -> None:
    if len(installed) != len(set(installed)):
        raise ClosureError("installed closure contains duplicate NEVRAs")
    if len(direct_nevras) != len(set(direct_nevras)):
        raise ClosureError("locked direct NEVRAs contain duplicates")
    missing = sorted(set(direct_nevras) - set(installed))
    if missing:
        raise ClosureError("installed closure omits locked direct NEVRAs: {}".format(missing))
    if len(installed) <= len(direct_nevras):
        raise ClosureError("installed closure contains no transitive packages")


def verify_cached_repomd(
    cache_root: Path, repositories: Sequence[Mapping[str, Any]]
) -> None:
    if cache_root.is_symlink() or not cache_root.is_dir():
        raise ClosureError("DNF cache root is unsafe")
    candidates = []
    for path in cache_root.rglob("repomd.xml"):
        resolved = path.resolve()
        if (
            path.is_symlink()
            or path != resolved
            or os.path.commonpath((str(cache_root.resolve()), str(resolved)))
            != str(cache_root.resolve())
            or not path.is_file()
        ):
            raise ClosureError("DNF cached repomd path is unsafe")
        candidates.append(path)
    if len(candidates) != len(repositories):
        raise ClosureError("DNF did not cache exactly one repomd per snapshot")
    expected = sorted(repository["repomd"]["sha256"] for repository in repositories)
    observed = sorted(sha256_file(path)[1] for path in candidates)
    require_exact(observed, expected, "DNF cached exact repomd identities")


def repository_for_metadata(
    metadata: Mapping[str, Any], repositories: Sequence[Mapping[str, Any]]
) -> Mapping[str, Any]:
    matches = [
        repository
        for repository in repositories
        if repository["id"] == metadata["repository_id"]
    ]
    if len(matches) != 1:
        raise ClosureError("closure RPM repository identity is ambiguous")
    return matches[0]


def copy_archive(
    source: Path,
    output_root: Path,
    relative: PurePosixPath,
    maximum_bytes: Optional[int] = None,
) -> Path:
    target = phase_one.output_path(output_root, relative)
    target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    if target.exists() or target.is_symlink():
        raise ClosureError("archive output already exists")
    input_descriptor = open_regular_read(source, "archive source")
    output_descriptor = -1
    created = False
    output_identity = None
    try:
        output_descriptor = open_regular_create(target, "archive output")
        created = True
        if not stat.S_ISREG(os.fstat(output_descriptor).st_mode):
            raise ClosureError("archive output is not a regular file")
        output_identity = regular_identity(os.fstat(output_descriptor))[:2]
        with os.fdopen(input_descriptor, "rb") as input_stream, os.fdopen(
            output_descriptor, "wb"
        ) as output_stream:
            input_descriptor = -1
            output_descriptor = -1
            input_identity = regular_identity(os.fstat(input_stream.fileno()))
            if maximum_bytes is not None:
                if type(maximum_bytes) is not int or maximum_bytes < 1:
                    raise ClosureError("archive byte bound is invalid")
                if input_identity[2] < 1 or input_identity[2] > maximum_bytes:
                    raise ClosureError("archive source exceeds its byte bound")
                remaining = input_identity[2]
                while remaining:
                    chunk = input_stream.read(min(1024 * 1024, remaining))
                    if not chunk:
                        raise ClosureError("archive source is truncated")
                    output_stream.write(chunk)
                    remaining -= len(chunk)
                if input_stream.read(1):
                    raise ClosureError("archive source grew while it was copied")
            else:
                shutil.copyfileobj(input_stream, output_stream, 1024 * 1024)
            if regular_identity(os.fstat(input_stream.fileno())) != input_identity:
                raise ClosureError("archive source changed while it was copied")
            if output_stream.tell() != input_identity[2]:
                raise ClosureError("archive copy size differs from its source")
            output_stream.flush()
            os.fsync(output_stream.fileno())
            os.fchmod(output_stream.fileno(), 0o400)
    except OSError as exc:
        raise ClosureError("cannot safely archive {}: {}".format(relative, exc)) from exc
    finally:
        if input_descriptor >= 0:
            os.close(input_descriptor)
        if output_descriptor >= 0:
            os.close(output_descriptor)
        if created:
            try:
                final_status = os.lstat(str(target))
            except OSError as exc:
                raise ClosureError("archive output disappeared during publication") from exc
            if (
                not stat.S_ISREG(final_status.st_mode)
                or (final_status.st_dev, final_status.st_ino) != output_identity
            ):
                raise ClosureError("archive output changed during publication")
    return target


def hash_snapshot_descriptor(
    descriptor: int,
    expected_identity: Tuple[int, int, int, int, int, int, int, int, int],
    label: str,
) -> Tuple[int, str]:
    """Hash the one held snapshot inode and reject any identity mutation."""
    duplicate = -1
    try:
        require_exact(
            v2_regular_identity(os.fstat(descriptor)),
            expected_identity,
            label + " identity before hash",
        )
        duplicate = os.dup(descriptor)
        os.lseek(duplicate, 0, os.SEEK_SET)
        digest = hashlib.sha256()
        size = 0
        while True:
            chunk = os.read(duplicate, 1024 * 1024)
            if not chunk:
                break
            size += len(chunk)
            digest.update(chunk)
        require_exact(
            v2_regular_identity(os.fstat(descriptor)),
            expected_identity,
            label + " identity after hash",
        )
        require_exact(size, expected_identity[6], label + " size")
        return size, digest.hexdigest()
    except ClosureError:
        raise
    except OSError as exc:
        raise ClosureError("cannot hash {}: {}".format(label, exc)) from exc
    finally:
        if duplicate >= 0:
            os.close(duplicate)


def copy_snapshot_archive_held(
    source: Path,
    stage_root: Path,
    maximum_bytes: int,
) -> Tuple[
    Path,
    int,
    Tuple[int, int, int, int, int, int, int, int, int],
    int,
    str,
]:
    """Copy the external tar once and retain its exact inode for all consumers."""
    if type(maximum_bytes) is not int or maximum_bytes < 1:
        raise ClosureError("snapshot artifact byte bound is invalid")
    target = stage_root / "snapshot.tar"
    input_descriptor = open_regular_read(source, "snapshot artifact source")
    output_descriptor = -1
    created = False
    try:
        output_descriptor = open_regular_create_read_write(
            target, "held snapshot artifact"
        )
        created = True
        input_identity = v2_regular_identity(os.fstat(input_descriptor))
        if input_identity[6] < 1 or input_identity[6] > maximum_bytes:
            raise ClosureError("snapshot artifact source exceeds its byte bound")
        digest = hashlib.sha256()
        copied = 0
        while copied < input_identity[6]:
            chunk = os.read(
                input_descriptor,
                min(1024 * 1024, input_identity[6] - copied),
            )
            if not chunk:
                raise ClosureError("snapshot artifact source is truncated")
            copied += len(chunk)
            digest.update(chunk)
            v2_write_all(output_descriptor, chunk, "held snapshot artifact")
        if os.read(input_descriptor, 1):
            raise ClosureError("snapshot artifact source grew while copied")
        require_exact(
            v2_regular_identity(os.fstat(input_descriptor)),
            input_identity,
            "snapshot artifact source identity",
        )
        os.fchmod(output_descriptor, 0o400)
        os.fsync(output_descriptor)
        output_identity = v2_regular_identity(os.fstat(output_descriptor))
        if (
            not stat.S_ISREG(output_identity[2])
            or output_identity[3] != 1
            or output_identity[4] != os.geteuid()
            or stat.S_IMODE(output_identity[2]) != 0o400
            or output_identity[6] != copied
        ):
            raise ClosureError("held snapshot artifact identity is unsafe")
        held_size, held_digest = hash_snapshot_descriptor(
            output_descriptor, output_identity, "held snapshot artifact"
        )
        require_exact(held_size, copied, "held snapshot artifact copied size")
        require_exact(
            held_digest,
            digest.hexdigest(),
            "held snapshot artifact copied digest",
        )
        result = output_descriptor
        output_descriptor = -1
        return target, result, output_identity, copied, held_digest
    except ClosureError:
        raise
    except OSError as exc:
        raise ClosureError("cannot stage held snapshot artifact: {}".format(exc)) from exc
    finally:
        os.close(input_descriptor)
        if output_descriptor >= 0:
            os.close(output_descriptor)
        if created and sys.exc_info()[0] is not None:
            try:
                target.unlink()
            except OSError:
                pass


def verify_and_extract_snapshot_descriptor(
    repo: Path,
    descriptor: int,
    expected_identity: Tuple[int, int, int, int, int, int, int, int, int],
    expected_size: int,
    expected_digest: str,
    snapshot_contract: Mapping[str, Any],
    input_records: Sequence[Mapping[str, Any]],
    execution_identity: Mapping[str, Any],
    tree: Path,
) -> Dict[str, Any]:
    """Verify and extract the externally bound snapshot from one held inode."""
    try:
        snapshot_v2.validate_contract(snapshot_contract)
        snapshot_v2.validate_input_records(input_records)
        validated_execution = snapshot_v2.validate_execution_identity(
            execution_identity.get("source_commit")
            if isinstance(execution_identity, dict)
            else None,
            execution_identity.get("workflow_ref")
            if isinstance(execution_identity, dict)
            else None,
        )
        snapshot_v2.require_repository_head(
            repo, validated_execution["source_commit"], input_records
        )
        before_size, before_digest = hash_snapshot_descriptor(
            descriptor, expected_identity, "snapshot artifact before verification"
        )
        require_exact(before_size, expected_size, "snapshot artifact verified size")
        require_exact(
            before_digest,
            expected_digest,
            "snapshot artifact verified digest",
        )
        limits = snapshot_contract["limits"]
        duplicate = os.dup(descriptor)
        try:
            os.lseek(duplicate, 0, os.SEEK_SET)
            with os.fdopen(duplicate, "rb") as artifact_stream:
                duplicate = -1
                snapshot_v2.extract_canonical_tar_stream(
                    artifact_stream, tree, limits
                )
                artifact_stream.seek(0)
                stream_digest = hashlib.sha256()
                stream_size = 0
                while True:
                    chunk = artifact_stream.read(1024 * 1024)
                    if not chunk:
                        break
                    stream_size += len(chunk)
                    stream_digest.update(chunk)
                require_exact(
                    v2_regular_identity(os.fstat(artifact_stream.fileno())),
                    expected_identity,
                    "snapshot artifact stream identity",
                )
        finally:
            if duplicate >= 0:
                os.close(duplicate)
        require_exact(stream_size, expected_size, "snapshot artifact stream size")
        require_exact(
            stream_digest.hexdigest(),
            expected_digest,
            "snapshot artifact stream digest",
        )
        manifest_path = tree / "capture-manifest.json"
        manifest_data = read_regular_bytes(manifest_path, "snapshot manifest")
        manifest = snapshot_v2.strict_json_bytes(
            manifest_data, "capture-manifest.json"
        )
        expected_manifest = snapshot_v2.build_capture_manifest(
            tree,
            repo,
            snapshot_contract,
            input_records,
            validated_execution,
        )
        snapshot_v2.require_exact(
            manifest, expected_manifest, "snapshot capture manifest"
        )
        rebuilt_tar = tree.parent / "snapshot-rebuilt.tar"
        snapshot_v2.create_deterministic_tar(tree, rebuilt_tar, limits)
        rebuilt_size, rebuilt_digest = snapshot_v2.sha256_file(rebuilt_tar)
        snapshot_v2.require_exact(
            rebuilt_size, expected_size, "snapshot canonical rebuilt size"
        )
        snapshot_v2.require_exact(
            rebuilt_digest, expected_digest, "snapshot canonical rebuilt digest"
        )
        final_size, final_digest = hash_snapshot_descriptor(
            descriptor, expected_identity, "snapshot artifact after verification"
        )
        require_exact(final_size, expected_size, "snapshot artifact final size")
        require_exact(final_digest, expected_digest, "snapshot artifact final digest")
        return manifest
    except snapshot_v2.SnapshotError as exc:
        raise ClosureError("snapshot artifact verification failed: {}".format(exc)) from exc


def chroot_regular_file(root: Path, path: str, label: str) -> Path:
    requested = PurePosixPath(path)
    if not requested.is_absolute() or any(
        part in ("", ".", "..") for part in requested.parts[1:]
    ):
        raise ClosureError("{} path is unsafe".format(label))
    stdout, stderr = run_command(
        ["chroot", str(root), "/usr/bin/readlink", "-f", "--", requested.as_posix()]
    )
    if stderr:
        raise ClosureError("{} path resolution wrote stderr".format(label))
    rows = stdout.decode("utf-8").splitlines()
    if len(rows) != 1:
        raise ClosureError("{} path resolution is ambiguous".format(label))
    canonical = PurePosixPath(rows[0])
    if not canonical.is_absolute() or any(
        part in ("", ".", "..") for part in canonical.parts[1:]
    ):
        raise ClosureError("{} canonical path is unsafe".format(label))
    host_path = root.joinpath(*canonical.parts[1:])
    resolved_root = root.resolve()
    resolved_host = host_path.resolve()
    if (
        host_path.is_symlink()
        or os.path.commonpath((str(resolved_root), str(resolved_host)))
        != str(resolved_root)
        or not host_path.is_file()
    ):
        raise ClosureError("{} is not a confined regular file".format(label))
    return host_path


def resolve_binary(root: Path, command: str) -> Tuple[str, str]:
    shell = "command -v -- {}".format(shlex.quote(command))
    stdout, _ = run_command(["chroot", str(root), "/bin/sh", "-c", shell])
    rows = stdout.decode("utf-8").splitlines()
    if len(rows) != 1 or not rows[0].startswith("/"):
        raise ClosureError("probe binary resolution is ambiguous: {}".format(command))
    binary = PurePosixPath(rows[0])
    if any(part in ("", ".", "..") for part in binary.parts[1:]):
        raise ClosureError("probe binary path is unsafe")
    resolved = chroot_regular_file(root, binary.as_posix(), "probe binary")
    _, digest = sha256_file(resolved)
    return binary.as_posix(), digest


def installed_file_owner_capture(root: Path, path: str) -> Tuple[str, bytes, bytes]:
    stdout, stderr = run_command(
        ["rpm", "--root", str(root), "-qf", "--qf", RPM_NEVRA_QUERY, path]
    )
    if stderr:
        raise ClosureError("installed file ownership query wrote stderr")
    rows = stdout.decode("utf-8").splitlines()
    if len(rows) != 1 or not rows[0]:
        raise ClosureError("installed file ownership is ambiguous")
    return rows[0], stdout, stderr


def installed_file_owner(root: Path, path: str) -> str:
    owner, _, _ = installed_file_owner_capture(root, path)
    return owner


def chroot_probe(
    root: Path, command: Sequence[str], extra_env: Optional[Mapping[str, str]] = None
) -> Tuple[bytes, bytes]:
    env_pairs = [
        "HOME=/root",
        "LANG=C",
        "LC_ALL=C",
        "PATH=/usr/sbin:/usr/bin:/sbin:/bin",
        "TZ=UTC",
        "HTTP_PROXY=http://127.0.0.1:9",
        "HTTPS_PROXY=http://127.0.0.1:9",
        "ALL_PROXY=http://127.0.0.1:9",
        "NO_PROXY=",
    ]
    if extra_env:
        env_pairs.extend("{}={}".format(key, value) for key, value in sorted(extra_env.items()))
    return run_command(
        ["chroot", str(root), "/usr/bin/env", "-i"] + env_pairs + list(command)
    )


def capture_probes(
    root: Path,
    toolchain: Mapping[str, Any],
    llvm_config_owner: Mapping[str, Any],
    output: V2OutputTransaction,
) -> Dict[str, Any]:
    results: List[Dict[str, Any]] = []
    artifact_by_name = {
        item["name"]: item for item in toolchain["direct_artifacts"]
    }
    if len(artifact_by_name) != len(toolchain["direct_artifacts"]):
        raise ClosureError("toolchain direct artifact names are ambiguous")
    probe_by_id = {item["id"]: item for item in toolchain["required_probes"]}
    if len(probe_by_id) != len(toolchain["required_probes"]):
        raise ClosureError("toolchain probe ids are ambiguous")
    special = {"rust-src-core", "libclang-via-bindgen"}
    for probe in toolchain["required_probes"]:
        probe_id = probe["id"]
        if probe_id in special:
            continue
        command = list(probe["command"])
        binary_path, binary_sha256 = resolve_binary(root, command[0])
        validate_probe_binary_path(probe_id, binary_path, llvm_config_owner)
        stdout, stderr = chroot_probe(root, command)
        combined = stdout + stderr
        expected = probe.get("expected_version")
        owner_nevra = installed_file_owner(root, binary_path)
        expected_owner = expected_probe_owner(
            probe_id,
            artifact_by_name[probe["artifact"]]["nevra"],
            llvm_config_owner,
        )
        require_exact(owner_nevra, expected_owner, "{} binary owner".format(probe_id))
        verify_expected_version(probe_id, expected, combined, owner_nevra)
        transcript = command_transcript(command, stdout, stderr)
        relative = PurePosixPath("transcripts/probes") / (probe_id + ".txt")
        output.write_bytes(relative, transcript)
        results.append(
            {
                "binary_path": binary_path,
                "binary_sha256": binary_sha256,
                "command": command,
                "exit_code": 0,
                "id": probe_id,
                "loaded_library_path": None,
                "loaded_library_sha256": None,
                "package_nevra": owner_nevra,
                "parsed_version": expected,
                "required_file_path": None,
                "required_file_sha256": None,
                "stderr_sha256": hashlib.sha256(stderr).hexdigest(),
                "stdout_sha256": hashlib.sha256(stdout).hexdigest(),
            }
        )

    rpm_path, rpm_digest = resolve_binary(root, "rpm")
    sysroot_stdout, sysroot_stderr = chroot_probe(root, ["rustc", "--print", "sysroot"])
    if sysroot_stderr:
        raise ClosureError("rustc sysroot probe wrote stderr")
    sysroot_rows = sysroot_stdout.decode("utf-8").splitlines()
    if len(sysroot_rows) != 1 or not sysroot_rows[0].startswith("/"):
        raise ClosureError("rustc sysroot is ambiguous")
    core_path = PurePosixPath(sysroot_rows[0]) / "lib/rustlib/src/rust/library/core/src/lib.rs"
    host_core = chroot_regular_file(root, core_path.as_posix(), "rust-src core file")
    _, core_digest = sha256_file(host_core)
    owner, rust_src_stdout, rust_src_stderr = installed_file_owner_capture(
        root, core_path.as_posix()
    )
    require_exact(
        owner,
        artifact_by_name["rust-src"]["nevra"],
        "rust-src core file owner",
    )
    rust_src_command = list(probe_by_id["rust-src-core"]["command"])
    output.write_bytes(
        PurePosixPath("transcripts/probes/rust-src-core.txt"),
        command_transcript(
            ["rustc", "--print", "sysroot"], sysroot_stdout, sysroot_stderr
        )
        + command_transcript(rust_src_command, rust_src_stdout, rust_src_stderr),
    )
    results.append(
        {
            "binary_path": rpm_path,
            "binary_sha256": rpm_digest,
            "command": rust_src_command,
            "exit_code": 0,
            "id": "rust-src-core",
            "loaded_library_path": None,
            "loaded_library_sha256": None,
            "package_nevra": owner,
            "parsed_version": probe_by_id["rust-src-core"]["expected_version"],
            "required_file_path": core_path.as_posix(),
            "required_file_sha256": core_digest,
            "stderr_sha256": hashlib.sha256(rust_src_stderr).hexdigest(),
            "stdout_sha256": hashlib.sha256(rust_src_stdout).hexdigest(),
        }
    )

    bindgen_path, bindgen_digest = resolve_binary(root, "bindgen")
    files_stdout, files_stderr = run_command(
        [
            "rpm",
            "--root",
            str(root),
            "-ql",
            artifact_by_name["clang-libs"]["nevra"],
        ]
    )
    if files_stderr:
        raise ClosureError("clang-libs file query wrote stderr")
    candidates: List[Tuple[int, str, Path]] = []
    for row in files_stdout.decode("utf-8").splitlines():
        if "/libclang.so" not in row or not row.startswith("/"):
            continue
        resolved = chroot_regular_file(root, row, "libclang candidate")
        candidates.append((resolved.stat().st_size, row, resolved))
    if not candidates:
        raise ClosureError("clang-libs contains no libclang shared library")
    _, libclang_candidate, _ = sorted(candidates, reverse=True)[0]
    fixture_dir = root / "scripts"
    if fixture_dir.exists() or fixture_dir.is_symlink():
        raise ClosureError("libclang probe fixture directory already exists")
    fixture_dir.mkdir(mode=0o755)
    header = fixture_dir / "rust_is_available_bindgen_libclang.h"
    with header.open("xb") as stream:
        stream.write(LIBCLANG_PROBE_BYTES)
        stream.flush()
        os.fsync(stream.fileno())
    header.chmod(0o400)
    require_exact(
        hashlib.sha256(LIBCLANG_PROBE_BYTES).hexdigest(),
        LIBCLANG_PROBE_SHA256,
        "libclang probe fixture digest",
    )
    libclang_command = list(probe_by_id["libclang-via-bindgen"]["command"])
    stdout, stderr = chroot_probe(
        root,
        libclang_command,
        {
            "LD_DEBUG": "libs",
            "LIBCLANG_PATH": str(PurePosixPath(libclang_candidate).parent),
        },
    )
    libclang_path = loaded_libclang_path(stderr)
    libclang_host = chroot_regular_file(root, libclang_path, "loaded libclang")
    libclang_path = "/" + libclang_host.relative_to(root).as_posix()
    _, libclang_digest = sha256_file(libclang_host)
    transcript = command_transcript(libclang_command, stdout, stderr)
    output.write_bytes(
        PurePosixPath("transcripts/probes/libclang-via-bindgen.txt"),
        transcript,
    )
    libclang_owner = installed_file_owner(root, libclang_path)
    require_exact(
        libclang_owner,
        artifact_by_name["clang-libs"]["nevra"],
        "libclang owner",
    )
    results.append(
        {
            "binary_path": bindgen_path,
            "binary_sha256": bindgen_digest,
            "command": libclang_command,
            "exit_code": 0,
            "id": "libclang-via-bindgen",
            "loaded_library_path": libclang_path,
            "loaded_library_sha256": libclang_digest,
            "package_nevra": libclang_owner,
            "parsed_version": None,
            "required_file_path": None,
            "required_file_sha256": None,
            "stderr_sha256": hashlib.sha256(stderr).hexdigest(),
            "stdout_sha256": hashlib.sha256(stdout).hexdigest(),
        }
    )
    order = [item["id"] for item in toolchain["required_probes"]]
    results.sort(key=lambda item: order.index(item["id"]))
    require_exact([item["id"] for item in results], order, "probe result coverage")
    for index, result in enumerate(results):
        exact_keys(result, PROBE_RESULT_FIELDS, "probe result {}".format(index))
    return {
        "all_required_probes_verified": True,
        "fixture_path": "/scripts/rust_is_available_bindgen_libclang.h",
        "fixture_sha256": LIBCLANG_PROBE_SHA256,
        "fixture_size": len(LIBCLANG_PROBE_BYTES),
        "network_isolation_claimed": False,
        "results": results,
        "schema_version": SCHEMA_VERSION,
    }


def prepare_empty_directory(path: Path, label: str) -> Path:
    if path.exists() or path.is_symlink():
        raise ClosureError("{} already exists".format(label))
    path.mkdir(mode=0o700, parents=True)
    if any(path.iterdir()):
        raise ClosureError("{} did not start empty".format(label))
    return path


def prepare_chroot_devices(root: Path) -> None:
    device_dir = root / "dev"
    if device_dir.is_symlink() or (device_dir.exists() and not device_dir.is_dir()):
        raise ClosureError("offline installroot /dev is not a regular directory")
    device_dir.mkdir(mode=0o755, parents=True, exist_ok=True)
    null = device_dir / "null"
    if null.is_symlink():
        raise ClosureError("offline installroot /dev/null is a symlink")
    if not null.exists():
        try:
            os.mknod(str(null), stat.S_IFCHR | 0o666, os.makedev(1, 3))
        except OSError as exc:
            raise ClosureError("cannot create isolated chroot /dev/null: {}".format(exc)) from exc
    if not stat.S_ISCHR(null.stat().st_mode) or null.stat().st_rdev != os.makedev(1, 3):
        raise ClosureError("isolated chroot /dev/null has the wrong device identity")


def validate_snapshot_runtime_identity(
    expected_sha256: str,
    source_commit: str,
    workflow_ref: str,
    source_run_id: str,
    source_run_attempt: str,
    capture_identity: Mapping[str, Any],
) -> Dict[str, Any]:
    if not isinstance(expected_sha256, str) or not HEX_SHA256.fullmatch(expected_sha256):
        raise ClosureError("snapshot artifact digest must be a lowercase SHA-256")
    if not isinstance(source_commit, str) or not re.fullmatch(
        r"[0-9a-f]{40}", source_commit
    ):
        raise ClosureError("snapshot source commit must be exact lowercase 40-hex")
    require_exact(
        source_commit,
        capture_identity["head_sha"],
        "snapshot source/current capture commit",
    )
    require_exact(
        capture_identity["repository"],
        snapshot_v2.WORKFLOW_REPOSITORY,
        "snapshot/current capture repository",
    )
    try:
        execution_identity = snapshot_v2.validate_execution_identity(
            source_commit, workflow_ref
        )
    except snapshot_v2.SnapshotError as exc:
        raise ClosureError("snapshot execution identity is invalid: {}".format(exc)) from exc
    for label, value in (
        ("snapshot source run ID", source_run_id),
        ("snapshot source run attempt", source_run_attempt),
    ):
        if (
            not isinstance(value, str)
            or not re.fullmatch(r"[1-9][0-9]{0,18}", value)
            or int(value) > 9223372036854775807
        ):
            raise ClosureError("{} must be a bounded positive integer".format(label))
    return {
        "artifact_sha256": expected_sha256,
        "execution_identity": execution_identity,
        "repository": capture_identity["repository"],
        "run_attempt": int(source_run_attempt),
        "run_id": int(source_run_id),
    }


def validate_snapshot_manifest_bridge(
    manifest: Mapping[str, Any],
    contract: Mapping[str, Any],
    runtime: Mapping[str, Any],
) -> None:
    authority = contract["snapshot_authority"]
    require_exact(manifest.get("schema_version"), 2, "snapshot manifest schema")
    require_exact(
        manifest.get("capture_id"), authority["capture_id"], "snapshot manifest capture ID"
    )
    require_exact(
        manifest.get("execution_identity"),
        runtime["execution_identity"],
        "snapshot manifest execution identity",
    )
    require_exact(manifest.get("claims"), snapshot_v2.FALSE_CLAIMS, "snapshot claims")
    if any(value is not False for value in manifest["claims"].values()):
        raise ClosureError("snapshot manifest contains a credit claim")
    require_exact(
        manifest.get("target"), snapshot_v2.TARGET, "snapshot manifest target"
    )
    release_key = exact_keys(
        manifest.get("release_key"),
        {"fingerprint", "path", "sha256", "size"},
        "snapshot manifest release key",
    )
    require_exact(
        {key: release_key[key] for key in ("fingerprint", "sha256", "size")},
        authority["release_key"],
        "snapshot manifest release-key authority",
    )
    require_exact(
        release_key["path"],
        "release-key/RPM-GPG-KEY-Rocky-10",
        "snapshot release-key path",
    )
    repositories = manifest.get("repositories")
    if not isinstance(repositories, list) or len(repositories) != len(
        authority["repositories"]
    ):
        raise ClosureError("snapshot manifest repository coverage changed")
    actual = []
    for item in repositories:
        if not isinstance(item, dict):
            raise ClosureError("snapshot manifest repository row is malformed")
        actual.append(
            {
                "base_url": item.get("base_url"),
                "id": item.get("id"),
                "kind": item.get("kind"),
            }
        )
    require_exact(actual, authority["repositories"], "snapshot repository authority")
    input_authority = {
        item["role"]: item for item in authority["required_repository_inputs"]
    }
    repository_inputs = manifest.get("repository_inputs")
    if not isinstance(repository_inputs, list) or len(repository_inputs) != len(
        input_authority
    ):
        raise ClosureError("snapshot manifest input coverage changed")
    observed_roles = []
    for item in repository_inputs:
        row = exact_keys(
            item,
            {"path", "role", "sha256", "size"},
            "snapshot manifest repository input",
        )
        role = row["role"]
        if role not in input_authority or role in observed_roles:
            raise ClosureError("snapshot manifest repository input role is ambiguous")
        expected = input_authority[role]
        require_exact(row["path"], expected["path"], "snapshot manifest input path")
        require_exact(row["sha256"], expected["sha256"], "snapshot manifest input digest")
        require_exact(row["size"], expected["size"], "snapshot manifest input size")
        observed_roles.append(role)
    require_exact(
        sorted(observed_roles), sorted(input_authority), "snapshot manifest input roles"
    )
    snapshot_identity = manifest.get("snapshot_identity")
    if not isinstance(snapshot_identity, str) or not HEX_SHA256.fullmatch(snapshot_identity):
        raise ClosureError("snapshot identity is malformed")


def validate_snapshot_checker_binding(
    repo: Path, contract: Mapping[str, Any]
) -> None:
    """Require the imported frozen verifier to originate from its bound source."""
    authority = contract["snapshot_authority"]
    rows = [
        item
        for item in authority["required_repository_inputs"]
        if item["role"] == "checker"
    ]
    if len(rows) != 1:
        raise ClosureError("snapshot checker authority is ambiguous")
    row = rows[0]
    expected_path = safe_repo_file(repo, row["path"])
    origin_value = getattr(snapshot_v2, "__file__", None)
    if not isinstance(origin_value, str) or not origin_value:
        raise ClosureError("snapshot checker import origin is missing")
    try:
        origin = Path(origin_value).resolve(strict=True)
        expected_origin = expected_path.resolve(strict=True)
    except OSError as exc:
        raise ClosureError("cannot resolve snapshot checker import origin") from exc
    require_exact(origin, expected_origin, "snapshot checker import origin")
    size, digest = sha256_file(expected_path)
    require_exact(size, row["size"], "snapshot checker source size")
    require_exact(digest, row["sha256"], "snapshot checker source digest")


def stage_verify_and_extract_snapshot(
    repo: Path,
    artifact: Path,
    runtime: Mapping[str, Any],
    contract: Mapping[str, Any],
    temporary: Path,
) -> Tuple[Path, Dict[str, Any], Dict[str, Any]]:
    validate_snapshot_checker_binding(repo, contract)
    snapshot_contract, input_records = snapshot_v2.check_repository_inputs(repo)
    stage_root = temporary / "snapshot-input"
    stage_root.mkdir(mode=0o700)
    staged_descriptor = -1
    try:
        (
            staged,
            staged_descriptor,
            staged_identity,
            artifact_size,
            artifact_digest,
        ) = copy_snapshot_archive_held(
            artifact,
            stage_root,
            snapshot_contract["limits"]["max_snapshot_tar_bytes"],
        )
        require_exact(
            artifact_digest,
            runtime["artifact_sha256"],
            "snapshot artifact digest before verification",
        )
        tree = temporary / "snapshot-tree"
        tree.mkdir(mode=0o700)
        manifest = verify_and_extract_snapshot_descriptor(
            repo,
            staged_descriptor,
            staged_identity,
            artifact_size,
            artifact_digest,
            snapshot_contract,
            input_records,
            runtime["execution_identity"],
            tree,
        )
        final_size, final_digest = hash_snapshot_descriptor(
            staged_descriptor,
            staged_identity,
            "snapshot artifact final replay",
        )
        require_exact(final_size, artifact_size, "staged snapshot size")
        require_exact(final_digest, artifact_digest, "staged snapshot digest")
        try:
            named_status = os.lstat(str(staged))
        except OSError as exc:
            raise ClosureError("held snapshot artifact path disappeared") from exc
        require_exact(
            v2_regular_identity(named_status),
            staged_identity,
            "held snapshot artifact path identity",
        )
    finally:
        if staged_descriptor >= 0:
            os.close(staged_descriptor)
    validate_snapshot_manifest_bridge(manifest, contract, runtime)
    input_manifest = {
        "artifact": {
            "name": "rocky-repository-snapshot-v2-{}-{}".format(
                runtime["run_id"], runtime["run_attempt"]
            ),
            "repository": runtime["repository"],
            "sha256": artifact_digest,
            "size": artifact_size,
        },
        "capture_id": manifest["capture_id"],
        "claims": dict(snapshot_v2.FALSE_CLAIMS),
        "execution_identity": dict(manifest["execution_identity"]),
        "repository_inputs": list(manifest["repository_inputs"]),
        "repository_ids": [item["id"] for item in manifest["repositories"]],
        "run_attempt": runtime["run_attempt"],
        "run_id": runtime["run_id"],
        "schema_version": V2_SCHEMA_VERSION,
        "snapshot_identity": manifest["snapshot_identity"],
    }
    return tree, manifest, input_manifest


def snapshot_payload_index(manifest: Mapping[str, Any]) -> Dict[str, Mapping[str, Any]]:
    records = manifest.get("payload_files")
    if not isinstance(records, list) or not records:
        raise ClosureError("snapshot payload file records are missing")
    result: Dict[str, Mapping[str, Any]] = {}
    for item in records:
        row = exact_keys(item, {"path", "sha256", "size"}, "snapshot payload file")
        relative = phase_one.normalized_relative_path(row["path"], "snapshot payload path")
        key = relative.as_posix()
        if key in result:
            raise ClosureError("snapshot payload path is duplicated")
        if not isinstance(row["sha256"], str) or not HEX_SHA256.fullmatch(row["sha256"]):
            raise ClosureError("snapshot payload digest is malformed")
        if type(row["size"]) is not int or row["size"] < 0:
            raise ClosureError("snapshot payload size is invalid")
        result[key] = row
    return result


def copy_snapshot_payload(
    tree: Path,
    payload: Mapping[str, Mapping[str, Any]],
    source_relative: str,
    output: V2OutputTransaction,
    output_relative: PurePosixPath,
) -> Path:
    if source_relative not in payload:
        raise ClosureError("snapshot payload omits {}".format(source_relative))
    record = payload[source_relative]
    source_path = tree.joinpath(
        *phase_one.normalized_relative_path(
            source_relative, "snapshot payload source"
        ).parts
    )
    target = output.copy_file(source_path, output_relative)
    size, digest = output.hash_file(output_relative)
    require_exact(size, record["size"], "copied snapshot payload size")
    require_exact(digest, record["sha256"], "copied snapshot payload digest")
    return target


def materialize_snapshot_v2_repositories(
    tree: Path,
    manifest: Mapping[str, Any],
    output: V2OutputTransaction,
    contract: Mapping[str, Any],
) -> Tuple[Dict[str, Path], List[Dict[str, Any]], List[Dict[str, Any]], Path]:
    payload = snapshot_payload_index(manifest)
    release_key_path = copy_snapshot_payload(
        tree,
        payload,
        "release-key/RPM-GPG-KEY-Rocky-10",
        output,
        PurePosixPath("archives/snapshot-repositories/RPM-GPG-KEY-Rocky-10"),
    )
    authority = contract["snapshot_authority"]
    by_id = {item["id"]: item for item in manifest["repositories"]}
    if len(by_id) != len(manifest["repositories"]):
        raise ClosureError("snapshot repository IDs are duplicated")
    roots: Dict[str, Path] = {}
    output_rows: List[Dict[str, Any]] = []
    dnf_rows: List[Dict[str, Any]] = []
    for repository_id in authority["binary_repository_ids"]:
        repository = by_id[repository_id]
        relative_root = PurePosixPath("archives/snapshot-repositories") / repository_id
        fixed = [
            "repositories/{}/repodata/repomd.xml".format(repository_id),
            "repositories/{}/repodata/repomd.xml.asc".format(repository_id),
            "repositories/{}/repodata/signature.json".format(repository_id),
        ]
        for source_relative in fixed:
            copy_snapshot_payload(
                tree,
                payload,
                source_relative,
                output,
                relative_root
                / phase_one.normalized_relative_path(
                    source_relative.split("/{}/".format(repository_id), 1)[1],
                    "snapshot fixed repository path",
                ),
            )
        metadata_rows = []
        objects = repository.get("objects")
        if not isinstance(objects, list) or not objects:
            raise ClosureError("snapshot repository metadata objects are missing")
        for item in objects:
            row = exact_keys(
                item,
                {
                    "compressed_sha256",
                    "compressed_size",
                    "compression",
                    "href",
                    "open_checksum_declared",
                    "open_sha256",
                    "open_size",
                    "type",
                    "verified_open_sha256",
                    "verified_open_size",
                },
                "snapshot metadata object",
            )
            href = phase_one.normalized_relative_path(row["href"], "snapshot metadata href")
            source_relative = "repositories/{}/{}".format(
                repository_id, href.as_posix()
            )
            target = copy_snapshot_payload(
                tree, payload, source_relative, output, relative_root / href
            )
            size, digest = output.hash_file(relative_root / href)
            require_exact(size, row["compressed_size"], "snapshot metadata size")
            require_exact(digest, row["compressed_sha256"], "snapshot metadata digest")
            metadata_rows.append(
                {
                    "archive_path": (relative_root / href).as_posix(),
                    "compression": row["compression"],
                    "href": href.as_posix(),
                    "open_checksum_declared": row["open_checksum_declared"],
                    "open_sha256": row["open_sha256"],
                    "open_size": row["open_size"],
                    "sha256": digest,
                    "signed_compressed_identity_verified": True,
                    "size": size,
                    "source_snapshot_path": source_relative,
                    "type": row["type"],
                    "verified_open_sha256": row["verified_open_sha256"],
                    "verified_open_size": row["verified_open_size"],
                }
            )
        roots[repository_id] = output.directory_path(relative_root)
        output_rows.append(
            {
                "base_url": repository["base_url"],
                "id": repository_id,
                "kind": repository["kind"],
                "local_repository_path": relative_root.as_posix(),
                "metadata": metadata_rows,
                "repomd": dict(repository["repomd"]),
                "signature": dict(repository["signature"]),
            }
        )
        dnf_rows.append(
            {
                "base_url": repository["base_url"],
                "id": repository_id,
                "repomd": dict(repository["repomd"]),
            }
        )
    return roots, output_rows, dnf_rows, release_key_path


def load_primary_indexes_v2(
    snapshot_roots: Mapping[str, Path],
    repositories: Sequence[Mapping[str, Any]],
) -> Dict[str, Dict[str, Any]]:
    index: Dict[str, Dict[str, Any]] = {}
    for repository in repositories:
        primary_rows = [
            item for item in repository["metadata"] if item["type"] == "primary"
        ]
        if len(primary_rows) != 1:
            raise ClosureError("snapshot repository must contain exactly one primary object")
        primary_path = snapshot_roots[repository["id"]].joinpath(
            *phase_one.normalized_relative_path(
                primary_rows[0]["href"], "snapshot primary href"
            ).parts
        )
        current = primary_index(primary_path, repository["id"])
        for nevra, metadata in current.items():
            if nevra in index and index[nevra] != metadata:
                raise ClosureError("repository snapshots disagree for {}".format(nevra))
            index[nevra] = metadata
    return index


def validate_locked_primary_membership(
    primary: Mapping[str, Mapping[str, Any]],
    toolchain: Mapping[str, Any],
) -> None:
    for artifact in toolchain["direct_artifacts"]:
        nevra = artifact["nevra"]
        if nevra not in primary:
            raise ClosureError("locked direct RPM is absent from signed snapshot: {}".format(nevra))
        observed = primary[nevra]
        for field in ("arch", "repository_id", "repository_location", "sha256", "size"):
            require_exact(observed[field], artifact[field], "locked direct RPM " + field)


def validate_source_primary_membership(
    tree: Path,
    manifest: Mapping[str, Any],
    source: Mapping[str, Any],
    contract: Mapping[str, Any],
) -> Dict[str, Any]:
    source_id = contract["snapshot_authority"]["source_repository_id"]
    rows = [item for item in manifest["repositories"] if item["id"] == source_id]
    if len(rows) != 1:
        raise ClosureError("snapshot source repository is ambiguous")
    primary_object = [item for item in rows[0]["objects"] if item["type"] == "primary"]
    if len(primary_object) != 1:
        raise ClosureError("snapshot source repository primary object is ambiguous")
    path = tree / "repositories" / source_id / Path(
        *phase_one.normalized_relative_path(
            primary_object[0]["href"], "source primary href"
        ).parts
    )
    primary_size, primary_digest = sha256_file(path)
    require_exact(
        primary_size,
        primary_object[0]["compressed_size"],
        "source primary compressed size",
    )
    require_exact(
        primary_digest,
        primary_object[0]["compressed_sha256"],
        "source primary compressed digest",
    )
    index = primary_index(path, source_id)
    locked = source["source_rpm"]
    nevra = locked["nevra"]
    if nevra not in index:
        raise ClosureError("locked source RPM is absent from signed source snapshot")
    observed = index[nevra]
    require_exact(observed["arch"], locked["arch"], "source RPM architecture")
    require_exact(
        observed["repository_location"],
        locked["repository_location"],
        "source RPM location",
    )
    require_exact(observed["sha256"], locked["sha256"], "source RPM digest")
    require_exact(observed["size"], locked["size"], "source RPM size")
    return {
        "primary": {
            "href": primary_object[0]["href"],
            "sha256": primary_object[0]["compressed_sha256"],
            "size": primary_object[0]["compressed_size"],
        },
        "repository_id": source_id,
        "source_rpm": dict(observed),
        "verified": True,
    }


def build_resolution_semantics(
    authority: Mapping[str, Any],
    direct_nevras: Sequence[str],
    parsed: Mapping[str, Any],
    kernel_spec_sha256: str,
) -> Tuple[Dict[str, Any], str]:
    exact_keys(
        parsed,
        {"reviewed_rocky_rust_additions", "rocky_effective"},
        "parsed BuildRequires",
    )
    if not isinstance(direct_nevras, list):
        direct_nevras = list(direct_nevras)
    direct = list(direct_nevras)
    if not all(isinstance(item, str) and item for item in direct):
        raise ClosureError("direct NEVRAs are malformed")
    if len(direct) != len(set(direct)):
        raise ClosureError("direct NEVRAs contain duplicates")
    require_exact(len(direct), authority["direct_nevra_count"], "direct NEVRA count")
    require_exact(
        hashlib.sha256(phase_one.canonical_json_bytes(direct)).hexdigest(),
        authority["direct_nevras_sha256"],
        "direct NEVRA digest",
    )
    effective = parsed["rocky_effective"]
    reviewed = parsed["reviewed_rocky_rust_additions"]
    if not isinstance(effective, list) or not all(
        isinstance(item, str) and item for item in effective
    ):
        raise ClosureError("effective BuildRequires are malformed")
    if len(effective) != len(set(effective)) or effective != sorted(effective):
        raise ClosureError("effective BuildRequires are not sorted and unique")
    require_exact(
        len(effective),
        authority["effective_buildrequires_count"],
        "effective BuildRequires count",
    )
    require_exact(
        reviewed,
        authority["reviewed_rocky_rust_additions"],
        "reviewed Rust additions",
    )
    if not isinstance(kernel_spec_sha256, str) or not HEX_SHA256.fullmatch(
        kernel_spec_sha256
    ):
        raise ClosureError("resolution kernel spec digest is malformed")
    require_exact(
        kernel_spec_sha256,
        authority["kernel_spec"]["sha256"],
        "resolution kernel spec digest",
    )
    roots = []
    roots.extend(
        {"kind": "rocky-effective-spec", "value": item} for item in effective
    )
    roots.extend(
        {"kind": "reviewed-rocky-rust", "value": item} for item in reviewed
    )
    roots.extend({"kind": "locked-direct-nevra", "value": item} for item in direct)
    require_exact(len(roots), authority["resolution_root_count"], "resolution root count")
    if len({(item["kind"], item["value"]) for item in roots}) != len(roots):
        raise ClosureError("resolution roots contain duplicates")
    semantic = {
        "direct_nevras": direct,
        "effective_buildrequires": list(effective),
        "kernel_spec_sha256": kernel_spec_sha256,
        "resolution_roots": roots,
        "reviewed_rocky_rust_additions": list(reviewed),
    }
    semantic_digest = hashlib.sha256(
        phase_one.canonical_json_bytes(semantic)
    ).hexdigest()
    require_exact(
        semantic_digest,
        authority["resolution_inputs_sha256"],
        "resolution input semantic digest",
    )
    return semantic, semantic_digest


def derive_resolution_input(
    output: V2OutputTransaction,
    work_root: Path,
    contract: Mapping[str, Any],
    toolchain: Mapping[str, Any],
    source: Mapping[str, Any],
) -> Dict[str, Any]:
    authority = contract["resolution_authority"]
    locked_specs = [
        item
        for item in source["dist_git"]["content"]
        if item["path"] == "SPECS/kernel.spec"
    ]
    if len(locked_specs) != 1:
        raise ClosureError("source lock kernel.spec authority is ambiguous")
    locked_spec = locked_specs[0]
    require_exact(
        source["dist_git"]["commit"],
        authority["kernel_spec"]["dist_git_commit"],
        "resolution dist-git commit",
    )
    require_exact(locked_spec, {
        "path": authority["kernel_spec"]["path"],
        "sha256": authority["kernel_spec"]["sha256"],
        "size": authority["kernel_spec"]["size"],
    }, "resolution kernel spec authority")
    spec_relative = PurePosixPath("inputs/kernel.spec")
    download_root = prepare_empty_directory(
        work_root / "resolution-input", "resolution input work directory"
    )
    spec_path = download_root / "kernel.spec"
    session = phase_one.NetworkSession(["git.rockylinux.org"])
    download = session.download_exact(
        phase_one.source_raw_url(source, locked_spec["path"]),
        spec_path,
        locked_spec["sha256"],
        locked_spec["size"],
        4 * 1024 * 1024,
    )
    session.seal()
    if not session.sealed:
        raise ClosureError("kernel spec acquisition did not seal")
    output.copy_file(spec_path, spec_relative)
    deterministic_env = phase_one.subprocess_network_defense_env(os.environ)
    deterministic_env.update({"LANG": "C", "LC_ALL": "C", "TZ": "UTC"})
    command = authority["rpmspec_command"]
    stdout, stderr = phase_one.run_command(
        command, cwd=spec_path.parent, env=deterministic_env
    )
    parsed = phase_one.parse_buildrequires(
        stdout, authority["reviewed_rocky_rust_additions"]
    )
    spec_transcript = (
        b"command: "
        + " ".join(command).encode("ascii")
        + b"\nstdout:\n"
        + stdout
        + b"stderr:\n"
        + stderr
    )
    output.write_bytes(
        PurePosixPath("transcripts/rpmspec-buildrequires.txt"), spec_transcript
    )
    showrc_stdout, showrc_stderr = phase_one.run_command(
        ["rpm", "--showrc"], env=deterministic_env
    )
    output.write_bytes(
        PurePosixPath("transcripts/rpm-showrc-resolution.txt"),
        b"stdout:\n" + showrc_stdout + b"stderr:\n" + showrc_stderr,
    )
    semantic, semantic_digest = build_resolution_semantics(
        authority,
        toolchain["closure"]["direct_nevras"],
        parsed,
        locked_spec["sha256"],
    )
    return {
        "collector_http_sealed_before_derivation": True,
        "direct_nevras": semantic["direct_nevras"],
        "effective_buildrequires": semantic["effective_buildrequires"],
        "kernel_spec": {
            "archive_path": spec_relative.as_posix(),
            "download": download,
            "sha256": locked_spec["sha256"],
            "size": locked_spec["size"],
        },
        "resolution_inputs_sha256": semantic_digest,
        "resolution_roots": semantic["resolution_roots"],
        "reviewed_rocky_rust_additions": semantic[
            "reviewed_rocky_rust_additions"
        ],
        "rpmspec_output_sha256": hashlib.sha256(stdout).hexdigest(),
        "rpm_showrc_sha256": hashlib.sha256(showrc_stdout).hexdigest(),
        "schema_version": V2_SCHEMA_VERSION,
        "source_spec_condition": toolchain["source_spec_observation"][
            "rust_buildrequires_condition"
        ],
    }


def validate_false_gate_claims(
    claims: object, expected: Mapping[str, Any], label: str
) -> None:
    require_exact(claims, expected, label)
    if not isinstance(claims, dict) or not claims or any(
        type(value) is not bool or value for value in claims.values()
    ):
        raise ClosureError("{} contains a credit claim".format(label))


def validate_snapshot_input_v2(
    value: Mapping[str, Any], contract: Mapping[str, Any]
) -> None:
    row = exact_keys(
        value,
        {
            "artifact",
            "bootstrap_checkpoint_id",
            "bootstrap_manifest",
            "capture_id",
            "claims",
            "credit_eligible",
            "execution_identity",
            "gate_claims",
            "repository_ids",
            "repository_inputs",
            "run_attempt",
            "run_id",
            "schema_version",
            "snapshot_identity",
        },
        "snapshot input v2",
    )
    authority = contract["snapshot_authority"]
    require_exact(row["schema_version"], V2_SCHEMA_VERSION, "snapshot input schema")
    require_exact(row["credit_eligible"], False, "snapshot input credit")
    validate_false_gate_claims(row["gate_claims"], contract["gate_claims"], "snapshot input gates")
    require_exact(row["claims"], snapshot_v2.FALSE_CLAIMS, "snapshot input claims")
    if any(type(value) is not bool or value for value in row["claims"].values()):
        raise ClosureError("snapshot input contains a snapshot credit claim")
    require_exact(row["capture_id"], authority["capture_id"], "snapshot input capture ID")
    execution = exact_keys(
        row["execution_identity"],
        {"source_commit", "workflow_ref"},
        "snapshot input execution identity",
    )
    try:
        validated_execution = snapshot_v2.validate_execution_identity(
            execution["source_commit"], execution["workflow_ref"]
        )
    except snapshot_v2.SnapshotError as exc:
        raise ClosureError("snapshot input execution identity is invalid: {}".format(exc)) from exc
    require_exact(execution, validated_execution, "snapshot input execution identity")
    artifact = exact_keys(
        row["artifact"],
        {"name", "repository", "sha256", "size"},
        "snapshot input artifact",
    )
    if type(row["run_id"]) is not int or not 1 <= row["run_id"] <= 9223372036854775807:
        raise ClosureError("snapshot input run ID is invalid")
    if (
        type(row["run_attempt"]) is not int
        or not 1 <= row["run_attempt"] <= 9223372036854775807
    ):
        raise ClosureError("snapshot input run attempt is invalid")
    require_exact(
        artifact["name"],
        "rocky-repository-snapshot-v2-{}-{}".format(
            row["run_id"], row["run_attempt"]
        ),
        "snapshot input artifact name",
    )
    require_exact(
        artifact["repository"],
        snapshot_v2.WORKFLOW_REPOSITORY,
        "snapshot input artifact repository",
    )
    if not isinstance(artifact["sha256"], str) or not HEX_SHA256.fullmatch(
        artifact["sha256"]
    ):
        raise ClosureError("snapshot input artifact digest is malformed")
    if (
        type(artifact["size"]) is not int
        or artifact["size"] < 1
        or artifact["size"] > snapshot_v2.TAR_LIMITS["max_snapshot_tar_bytes"]
    ):
        raise ClosureError("snapshot input artifact size is invalid")
    if not isinstance(row["snapshot_identity"], str) or not HEX_SHA256.fullmatch(
        row["snapshot_identity"]
    ):
        raise ClosureError("snapshot input snapshot identity is malformed")
    require_exact(
        row["repository_ids"],
        [item["id"] for item in authority["repositories"]],
        "snapshot input repository IDs",
    )
    input_authority = {
        item["role"]: item for item in authority["required_repository_inputs"]
    }
    records = row["repository_inputs"]
    if not isinstance(records, list) or len(records) != len(input_authority):
        raise ClosureError("snapshot input repository-input coverage changed")
    observed_roles = []
    for index, item in enumerate(records):
        record = exact_keys(
            item,
            {"path", "role", "sha256", "size"},
            "snapshot input repository record {}".format(index),
        )
        role = record["role"]
        if role not in input_authority or role in observed_roles:
            raise ClosureError("snapshot input repository role is ambiguous")
        require_exact(record["path"], input_authority[role]["path"], "snapshot input path")
        require_exact(
            record["sha256"], input_authority[role]["sha256"], "snapshot input digest"
        )
        require_exact(
            record["size"], input_authority[role]["size"], "snapshot input size"
        )
        observed_roles.append(role)
    require_exact(sorted(observed_roles), sorted(input_authority), "snapshot input roles")
    bootstrap = exact_keys(
        row["bootstrap_manifest"],
        {"sha256", "size"},
        "snapshot input bootstrap manifest",
    )
    if not isinstance(bootstrap["sha256"], str) or not HEX_SHA256.fullmatch(
        bootstrap["sha256"]
    ):
        raise ClosureError("snapshot input bootstrap digest is malformed")
    if type(bootstrap["size"]) is not int or bootstrap["size"] < 1:
        raise ClosureError("snapshot input bootstrap size is invalid")
    require_exact(
        row["bootstrap_checkpoint_id"],
        phase_one.CHECKPOINT_ID,
        "snapshot input bootstrap checkpoint",
    )


def validate_resolution_input_v2(
    value: Mapping[str, Any], contract: Mapping[str, Any]
) -> None:
    row = exact_keys(
        value,
        {
            "collector_http_sealed_before_derivation",
            "credit_eligible",
            "direct_nevras",
            "effective_buildrequires",
            "gate_claims",
            "kernel_spec",
            "resolution_inputs_sha256",
            "resolution_roots",
            "reviewed_rocky_rust_additions",
            "rpm_showrc_sha256",
            "rpmspec_output_sha256",
            "schema_version",
            "source_snapshot_membership",
            "source_spec_condition",
        },
        "resolution input v2",
    )
    require_exact(row["schema_version"], V2_SCHEMA_VERSION, "resolution input schema")
    require_exact(row["credit_eligible"], False, "resolution input credit")
    validate_false_gate_claims(
        row["gate_claims"], contract["gate_claims"], "resolution input gates"
    )
    require_exact(
        row["collector_http_sealed_before_derivation"],
        True,
        "resolution collector seal",
    )
    authority = contract["resolution_authority"]
    kernel_spec = exact_keys(
        row["kernel_spec"],
        {"archive_path", "download", "sha256", "size"},
        "resolution kernel spec",
    )
    require_exact(kernel_spec["archive_path"], "inputs/kernel.spec", "kernel spec archive path")
    require_exact(kernel_spec["sha256"], authority["kernel_spec"]["sha256"], "kernel spec digest")
    require_exact(kernel_spec["size"], authority["kernel_spec"]["size"], "kernel spec size")
    download = exact_keys(
        kernel_spec["download"],
        {"final_url", "redirect_count", "sha256", "size"},
        "resolution kernel spec download",
    )
    require_exact(download["redirect_count"], 0, "kernel spec redirects")
    require_exact(download["sha256"], kernel_spec["sha256"], "downloaded kernel spec digest")
    require_exact(download["size"], kernel_spec["size"], "downloaded kernel spec size")
    required_url_suffix = "/{}/{}".format(
        authority["kernel_spec"]["dist_git_commit"],
        authority["kernel_spec"]["path"],
    )
    if (
        not isinstance(download["final_url"], str)
        or not download["final_url"].startswith("https://git.rockylinux.org/")
        or not download["final_url"].endswith(required_url_suffix)
    ):
        raise ClosureError("kernel spec URL is not the immutable authority")
    semantic, semantic_digest = build_resolution_semantics(
        authority,
        row["direct_nevras"],
        {
            "rocky_effective": row["effective_buildrequires"],
            "reviewed_rocky_rust_additions": row[
                "reviewed_rocky_rust_additions"
            ],
        },
        kernel_spec["sha256"],
    )
    require_exact(row["resolution_roots"], semantic["resolution_roots"], "resolution roots")
    require_exact(row["resolution_inputs_sha256"], semantic_digest, "resolution semantic digest")
    for field in ("rpmspec_output_sha256", "rpm_showrc_sha256"):
        if not isinstance(row[field], str) or not HEX_SHA256.fullmatch(row[field]):
            raise ClosureError("resolution {} is malformed".format(field))
    if not isinstance(row["source_spec_condition"], str) or not row["source_spec_condition"]:
        raise ClosureError("resolution source-spec condition is malformed")
    membership = exact_keys(
        row["source_snapshot_membership"],
        {"primary", "repository_id", "source_rpm", "verified"},
        "source snapshot membership",
    )
    require_exact(membership["verified"], True, "source snapshot membership")
    require_exact(
        membership["repository_id"],
        contract["snapshot_authority"]["source_repository_id"],
        "source snapshot repository",
    )
    primary = exact_keys(
        membership["primary"], {"href", "sha256", "size"}, "source snapshot primary"
    )
    primary_href = phase_one.normalized_relative_path(
        primary["href"], "source snapshot primary href"
    )
    if primary_href.parts[0] != "repodata":
        raise ClosureError("source snapshot primary path is outside repodata")
    if not isinstance(primary["sha256"], str) or not HEX_SHA256.fullmatch(primary["sha256"]):
        raise ClosureError("source snapshot primary digest is malformed")
    if type(primary["size"]) is not int or primary["size"] < 1:
        raise ClosureError("source snapshot primary size is invalid")
    source_rpm = exact_keys(
        membership["source_rpm"],
        {"arch", "nevra", "repository_id", "repository_location", "sha256", "size"},
        "source snapshot RPM",
    )
    require_exact(source_rpm["repository_id"], membership["repository_id"], "source RPM repository")
    require_exact(source_rpm["arch"], "src", "source RPM architecture")
    source_location = phase_one.normalized_relative_path(
        source_rpm["repository_location"], "source RPM location"
    )
    if source_location.parts[0] != "Packages" or source_location.suffix != ".rpm":
        raise ClosureError("source RPM location has an unsafe layout")
    if not isinstance(source_rpm["nevra"], str) or not source_rpm["nevra"]:
        raise ClosureError("source RPM NEVRA is malformed")
    if not isinstance(source_rpm["sha256"], str) or not HEX_SHA256.fullmatch(source_rpm["sha256"]):
        raise ClosureError("source RPM digest is malformed")
    if type(source_rpm["size"]) is not int or source_rpm["size"] < 1:
        raise ClosureError("source RPM size is invalid")


def validate_capture_manifest_schemas(
    closure: Mapping[str, Any],
    offline: Mapping[str, Any],
    probes: Mapping[str, Any],
    macros: Mapping[str, Any],
    environment: Mapping[str, Any],
    blockers: Mapping[str, Any],
) -> None:
    exact_keys(
        closure,
        {
            "all_archives_verified",
            "all_repomd_data_materialized",
            "all_signatures_verified",
            "configured_network_sources",
            "environment_manifest_sha256",
            "exact_snapshot_root_solve_verified",
            "historical_direct_phase_checkpoint_sha256",
            "network_isolation_claimed",
            "package_bytes",
            "package_count",
            "packages",
            "resolution_inputs_sha256",
            "resolution_root_count",
            "resolution_roots",
            "rpm_set_sha256",
            "schema_version",
            "snapshot_repositories",
            "unresolved_dependencies",
        },
        "closure output",
    )
    for index, item in enumerate(closure["packages"]):
        row = exact_keys(
            item,
            {
                "arch",
                "archive_path",
                "nevra",
                "repository_id",
                "repository_location",
                "sha256",
                "signature",
                "signature_transcript_path",
                "size",
            },
            "closure package {}".format(index),
        )
        exact_keys(
            row["signature"],
            {
                "header_signature_algorithm",
                "signer_fingerprint",
                "signer_key_id",
                "status",
                "transcript_sha256",
                "transcript_size",
            },
            "closure package signature",
        )
    for repository in closure["snapshot_repositories"]:
        snapshot = exact_keys(
            repository,
            {
                "base_url",
                "id",
                "local_repository_path",
                "metadata",
                "repomd_sha256",
                "repomd_signature",
            },
            "snapshot repository output",
        )
        exact_keys(
            snapshot["repomd_signature"],
            {"status", "transcript_sha256", "transcript_size", "validsig_fingerprint"},
            "snapshot repomd signature output",
        )
        for item in snapshot["metadata"]:
            metadata = exact_keys(
                item,
                {
                    "archive_path",
                    "download",
                    "href",
                    "open_identity_verified",
                    "open_sha256",
                    "open_size",
                    "sha256",
                    "signed_compressed_identity_verified",
                    "size",
                    "type",
                },
                "snapshot metadata output",
            )
            exact_keys(
                metadata["download"],
                {"final_url", "redirect_count", "sha256", "size", "source"},
                "snapshot metadata download output",
            )
    replay = exact_keys(
        offline,
        {
            "all_repositories_disabled",
            "command",
            "empty_installroot_verified",
            "enabled_repository_count",
            "environment_manifest_sha256",
            "installed_package_count",
            "installed_rpm_set_sha256",
            "network_isolation_claimed",
            "network_scope",
            "proxy_loopback_defense",
            "schema_version",
            "snapshot_solve",
            "transaction_exit_code",
            "transaction_output_sha256",
        },
        "offline replay output",
    )
    snapshot_solve_output = exact_keys(
        replay["snapshot_solve"],
        {
            "command",
            "empty_installroot_verified",
            "installed_package_count",
            "installed_rpm_set_sha256",
            "local_file_repositories_only",
            "transaction_exit_code",
            "transaction_output_sha256",
        },
        "snapshot solve output",
    )
    exact_keys(
        probes,
        {
            "all_required_probes_verified",
            "environment_manifest_sha256",
            "fixture_path",
            "fixture_sha256",
            "fixture_size",
            "network_isolation_claimed",
            "results",
            "schema_version",
        },
        "probe output",
    )
    for index, result in enumerate(probes["results"]):
        exact_keys(result, PROBE_RESULT_FIELDS, "probe output {}".format(index))
    exact_keys(macros, {"command", "output_sha256", "output_size", "schema_version"}, "RPM macro output")
    exact_keys(
        environment,
        {
            "architecture",
            "container_image",
            "container_manifest_digest",
            "container_platform",
            "direct_input",
            "github",
            "offline_installroot_package_count",
            "offline_os_release",
            "offline_rpm_set_sha256",
            "runtime_os_release",
            "schema_version",
            "snapshot_solve_package_count",
        },
        "closure environment output",
    )
    exact_keys(
        blockers,
        {
            "config_lock_blockers_at_capture",
            "gate_claims",
            "phase_success_blockers",
            "toolchain_lock_blockers_at_capture",
        },
        "closure blocker output",
    )


def validate_capture_manifest_schemas_v2(
    closure: Mapping[str, Any],
    offline: Mapping[str, Any],
    probes: Mapping[str, Any],
    macros: Mapping[str, Any],
    environment: Mapping[str, Any],
    blockers: Mapping[str, Any],
) -> None:
    exact_keys(
        closure,
        {
            "all_archives_verified",
            "all_binary_repomd_data_materialized",
            "all_signatures_verified",
            "configured_network_sources",
            "credit_eligible",
            "environment_manifest_sha256",
            "exact_snapshot_root_solve_verified",
            "gate_claims",
            "network_isolation_claimed",
            "package_bytes",
            "package_count",
            "packages",
            "resolution_inputs_sha256",
            "resolution_root_count",
            "resolution_roots",
            "rpm_set_sha256",
            "schema_version",
            "snapshot_input",
            "snapshot_repositories",
            "unresolved_dependencies",
        },
        "closure v2 output",
    )
    require_exact(closure["schema_version"], V2_SCHEMA_VERSION, "closure v2 schema")
    require_exact(closure["credit_eligible"], False, "closure v2 credit")
    for field in (
        "all_archives_verified",
        "all_binary_repomd_data_materialized",
        "all_signatures_verified",
        "exact_snapshot_root_solve_verified",
    ):
        require_exact(closure[field], True, "closure v2 " + field)
    require_exact(
        closure["network_isolation_claimed"], False, "closure v2 network claim"
    )
    closure_claims = closure["gate_claims"]
    if not isinstance(closure_claims, dict) or not closure_claims or any(
        type(value) is not bool or value for value in closure_claims.values()
    ):
        raise ClosureError("closure v2 contains a gate-credit claim")
    if not isinstance(closure["packages"], list):
        raise ClosureError("closure packages are malformed")
    require_exact(closure["package_count"], len(closure["packages"]), "closure package count")
    require_exact(
        closure["resolution_root_count"],
        len(closure["resolution_roots"]),
        "closure resolution-root count",
    )
    require_exact(closure["unresolved_dependencies"], [], "closure unresolved dependencies")
    snapshot_binding = exact_keys(
        closure["snapshot_input"],
        {"artifact_sha256", "capture_id", "snapshot_identity", "source_commit"},
        "closure snapshot binding",
    )
    require_exact(
        snapshot_binding["capture_id"], snapshot_v2.CAPTURE_ID, "closure snapshot capture ID"
    )
    for field in ("artifact_sha256", "snapshot_identity"):
        if not isinstance(snapshot_binding[field], str) or not HEX_SHA256.fullmatch(
            snapshot_binding[field]
        ):
            raise ClosureError("closure snapshot {} is malformed".format(field))
    if not isinstance(snapshot_binding["source_commit"], str) or not re.fullmatch(
        r"[0-9a-f]{40}", snapshot_binding["source_commit"]
    ):
        raise ClosureError("closure snapshot source commit is malformed")
    for index, item in enumerate(closure["packages"]):
        row = exact_keys(
            item,
            {
                "arch",
                "archive_path",
                "nevra",
                "repository_id",
                "repository_location",
                "sha256",
                "signature",
                "signature_transcript_path",
                "size",
            },
            "closure v2 package {}".format(index),
        )
        exact_keys(
            row["signature"],
            {
                "header_signature_algorithm",
                "signer_fingerprint",
                "signer_key_id",
                "status",
                "transcript_sha256",
                "transcript_size",
            },
            "closure v2 package signature",
        )
    require_exact(
        closure["package_bytes"],
        sum(item["size"] for item in closure["packages"]),
        "closure package bytes",
    )
    for repository in closure["snapshot_repositories"]:
        snapshot = exact_keys(
            repository,
            {
                "base_url",
                "id",
                "kind",
                "local_repository_path",
                "metadata",
                "repomd",
                "signature",
            },
            "snapshot v2 repository output",
        )
        exact_keys(
            snapshot["repomd"], {"revision", "sha256", "size"}, "snapshot v2 repomd"
        )
        exact_keys(
            snapshot["signature"],
            {
                "hash_algorithm_id",
                "primary_fingerprint",
                "public_key_algorithm_id",
                "sha256",
                "signature_fingerprint",
                "signature_timestamp",
                "size",
                "status",
            },
            "snapshot v2 signature",
        )
        for item in snapshot["metadata"]:
            exact_keys(
                item,
                {
                    "archive_path",
                    "compression",
                    "href",
                    "open_checksum_declared",
                    "open_sha256",
                    "open_size",
                    "sha256",
                    "signed_compressed_identity_verified",
                    "size",
                    "source_snapshot_path",
                    "type",
                    "verified_open_sha256",
                    "verified_open_size",
                },
                "snapshot v2 metadata output",
            )
    replay = exact_keys(
        offline,
        {
            "all_repositories_disabled",
            "command",
            "credit_eligible",
            "empty_installroot_verified",
            "enabled_repository_count",
            "environment_manifest_sha256",
            "gate_claims",
            "installed_package_count",
            "installed_rpm_set_sha256",
            "network_isolation_claimed",
            "network_scope",
            "proxy_loopback_defense",
            "schema_version",
            "snapshot_solve",
            "transaction_exit_code",
            "transaction_output_sha256",
        },
        "offline v2 replay output",
    )
    require_exact(replay["schema_version"], V2_SCHEMA_VERSION, "offline v2 schema")
    require_exact(replay["credit_eligible"], False, "offline v2 credit")
    require_exact(replay["all_repositories_disabled"], True, "offline repository policy")
    require_exact(replay["empty_installroot_verified"], True, "offline empty root")
    require_exact(replay["enabled_repository_count"], 0, "offline repository count")
    require_exact(replay["network_isolation_claimed"], False, "offline network claim")
    require_exact(replay["proxy_loopback_defense"], True, "offline proxy defense")
    require_exact(replay["transaction_exit_code"], 0, "offline transaction status")
    validate_false_gate_claims(
        replay["gate_claims"], closure_claims, "offline v2 gate claims"
    )
    require_exact(
        replay["installed_rpm_set_sha256"],
        closure["rpm_set_sha256"],
        "offline/closure RPM set",
    )
    require_exact(
        replay["installed_package_count"],
        closure["package_count"],
        "offline/closure package count",
    )
    require_exact(
        replay["environment_manifest_sha256"],
        closure["environment_manifest_sha256"],
        "offline/closure environment",
    )
    snapshot_solve_output = exact_keys(
        replay["snapshot_solve"],
        {
            "command",
            "empty_installroot_verified",
            "installed_package_count",
            "installed_rpm_set_sha256",
            "local_file_repositories_only",
            "transaction_exit_code",
            "transaction_output_sha256",
        },
        "snapshot v2 solve output",
    )
    require_exact(
        snapshot_solve_output["installed_package_count"],
        closure["package_count"],
        "snapshot/closure package count",
    )
    require_exact(
        snapshot_solve_output["installed_rpm_set_sha256"],
        closure["rpm_set_sha256"],
        "snapshot/closure RPM set",
    )
    require_exact(
        snapshot_solve_output["empty_installroot_verified"],
        True,
        "snapshot empty root",
    )
    require_exact(
        snapshot_solve_output["local_file_repositories_only"],
        True,
        "snapshot local-repository policy",
    )
    require_exact(
        snapshot_solve_output["transaction_exit_code"],
        0,
        "snapshot transaction status",
    )
    exact_keys(
        probes,
        {
            "all_required_probes_verified",
            "credit_eligible",
            "environment_manifest_sha256",
            "fixture_path",
            "fixture_sha256",
            "fixture_size",
            "gate_claims",
            "network_isolation_claimed",
            "results",
            "schema_version",
        },
        "probe output",
    )
    require_exact(probes["schema_version"], V2_SCHEMA_VERSION, "probe v2 schema")
    require_exact(probes["credit_eligible"], False, "probe v2 credit")
    require_exact(
        probes["all_required_probes_verified"], True, "probe v2 verification"
    )
    require_exact(probes["network_isolation_claimed"], False, "probe network claim")
    validate_false_gate_claims(
        probes["gate_claims"], closure_claims, "probe v2 gate claims"
    )
    require_exact(
        probes["environment_manifest_sha256"],
        closure["environment_manifest_sha256"],
        "probe/closure environment",
    )
    for index, result in enumerate(probes["results"]):
        exact_keys(result, PROBE_RESULT_FIELDS, "probe output {}".format(index))
    exact_keys(
        macros,
        {
            "command",
            "credit_eligible",
            "gate_claims",
            "output_sha256",
            "output_size",
            "schema_version",
        },
        "RPM macro v2 output",
    )
    require_exact(macros["schema_version"], V2_SCHEMA_VERSION, "RPM macro v2 schema")
    require_exact(macros["credit_eligible"], False, "RPM macro v2 credit")
    validate_false_gate_claims(
        macros["gate_claims"], closure_claims, "RPM macro v2 gate claims"
    )
    exact_keys(
        environment,
        {
            "architecture",
            "container_image",
            "container_manifest_digest",
            "container_platform",
            "credit_eligible",
            "gate_claims",
            "github",
            "offline_installroot_package_count",
            "offline_os_release",
            "offline_rpm_set_sha256",
            "resolution_inputs_sha256",
            "runtime_os_release",
            "schema_version",
            "snapshot_tar_sha256",
            "snapshot_solve_package_count",
        },
        "closure v2 environment output",
    )
    require_exact(environment["schema_version"], V2_SCHEMA_VERSION, "environment v2 schema")
    require_exact(environment["credit_eligible"], False, "environment v2 credit")
    validate_false_gate_claims(
        environment["gate_claims"], closure_claims, "environment v2 gate claims"
    )
    require_exact(
        environment["offline_rpm_set_sha256"],
        closure["rpm_set_sha256"],
        "environment/closure RPM set",
    )
    require_exact(
        environment["resolution_inputs_sha256"],
        closure["resolution_inputs_sha256"],
        "environment/closure resolution inputs",
    )
    require_exact(
        environment["snapshot_tar_sha256"],
        snapshot_binding["artifact_sha256"],
        "environment/closure snapshot tar",
    )
    require_exact(
        environment["offline_installroot_package_count"],
        closure["package_count"],
        "environment offline package count",
    )
    require_exact(
        environment["snapshot_solve_package_count"],
        closure["package_count"],
        "environment snapshot package count",
    )
    exact_keys(
        blockers,
        {
            "config_lock_blockers_at_capture",
            "credit_eligible",
            "gate_claims",
            "phase_success_blockers",
            "schema_version",
            "toolchain_lock_blockers_at_capture",
        },
        "closure blocker output",
    )
    require_exact(blockers["schema_version"], V2_SCHEMA_VERSION, "blocker v2 schema")
    require_exact(blockers["credit_eligible"], False, "blocker v2 credit")
    validate_false_gate_claims(
        blockers["gate_claims"], closure_claims, "blocker v2 gate claims"
    )


def validate_capture_checkpoint(checkpoint: Mapping[str, Any]) -> None:
    row = exact_keys(
        checkpoint,
        {
            "credit_eligible",
            "direct_phase_head_sha",
            "gate_claims",
            "github",
            "manifests",
            "phase",
            "schema_version",
            "successful_capture_requires_independent_review",
        },
        "closure checkpoint",
    )
    require_exact(row["credit_eligible"], False, "closure checkpoint credit")
    require_exact(row["phase"], PHASE_ID, "closure checkpoint phase")
    require_exact(row["schema_version"], SCHEMA_VERSION, "closure checkpoint schema")
    require_exact(
        row["successful_capture_requires_independent_review"],
        True,
        "closure checkpoint review requirement",
    )
    if not re.fullmatch(r"[0-9a-f]{40}", str(row["direct_phase_head_sha"])):
        raise ClosureError("closure checkpoint direct-phase SHA is malformed")
    claims = row["gate_claims"]
    if not isinstance(claims, dict) or not claims or any(
        type(value) is not bool or value for value in claims.values()
    ):
        raise ClosureError("closure checkpoint contains a gate-credit claim")
    exact_keys(
        row["github"],
        {"head_sha", "repository", "run_attempt", "run_id"},
        "closure checkpoint GitHub identity",
    )
    expected_names = [
        "blockers.json",
        "closure.json",
        "environment.json",
        "offline-replay.json",
        "probes.json",
        "rpm-macros.json",
    ]
    manifests = row["manifests"]
    if not isinstance(manifests, list) or len(manifests) != len(expected_names):
        raise ClosureError("closure checkpoint manifest coverage changed")
    observed_names = []
    for index, item in enumerate(manifests):
        manifest = exact_keys(
            item, {"path", "sha256", "size"}, "closure manifest {}".format(index)
        )
        relative = phase_one.normalized_relative_path(
            manifest["path"], "closure manifest path"
        )
        if relative.parts != (relative.name,):
            raise ClosureError("closure checkpoint manifest must be top-level")
        if not isinstance(manifest["sha256"], str) or not HEX_SHA256.fullmatch(
            manifest["sha256"]
        ):
            raise ClosureError("closure checkpoint manifest digest is malformed")
        if not isinstance(manifest["size"], int) or manifest["size"] < 1:
            raise ClosureError("closure checkpoint manifest size is invalid")
        observed_names.append(relative.as_posix())
    require_exact(observed_names, expected_names, "closure checkpoint manifest order")


def validate_capture_checkpoint_v2(checkpoint: Mapping[str, Any]) -> None:
    row = exact_keys(
        checkpoint,
        {
            "claims",
            "credit_eligible",
            "gate_claims",
            "github",
            "manifests",
            "phase",
            "schema_version",
            "snapshot_identity",
            "snapshot_source_commit",
            "snapshot_tar_sha256",
            "successful_capture_requires_independent_review",
        },
        "closure v2 checkpoint",
    )
    require_exact(row["credit_eligible"], False, "closure v2 checkpoint credit")
    require_exact(row["claims"], snapshot_v2.FALSE_CLAIMS, "closure v2 checkpoint claims")
    if any(type(value) is not bool or value for value in row["claims"].values()):
        raise ClosureError("closure v2 checkpoint contains an acceptance claim")
    require_exact(row["phase"], PHASE_ID, "closure v2 checkpoint phase")
    require_exact(row["schema_version"], V2_SCHEMA_VERSION, "closure v2 checkpoint schema")
    require_exact(
        row["successful_capture_requires_independent_review"],
        True,
        "closure v2 checkpoint review requirement",
    )
    if not isinstance(row["gate_claims"], dict) or not row["gate_claims"] or any(
        type(value) is not bool or value for value in row["gate_claims"].values()
    ):
        raise ClosureError("closure v2 checkpoint contains a gate-credit claim")
    github = exact_keys(
        row["github"],
        {"head_sha", "repository", "run_attempt", "run_id"},
        "closure v2 checkpoint GitHub identity",
    )
    require_exact(
        row["snapshot_source_commit"],
        github["head_sha"],
        "snapshot/current checkpoint commit",
    )
    for field in ("snapshot_identity", "snapshot_tar_sha256"):
        if not isinstance(row[field], str) or not HEX_SHA256.fullmatch(row[field]):
            raise ClosureError("closure v2 checkpoint {} is malformed".format(field))
    expected_names = [
        "blockers.json",
        "closure.json",
        "environment.json",
        "offline-replay.json",
        "probes.json",
        "resolution-input.json",
        "rpm-macros.json",
        "snapshot-input.json",
    ]
    manifests = row["manifests"]
    if not isinstance(manifests, list) or len(manifests) != len(expected_names):
        raise ClosureError("closure v2 checkpoint manifest coverage changed")
    observed_names = []
    for index, item in enumerate(manifests):
        manifest = exact_keys(
            item, {"path", "sha256", "size"}, "closure v2 manifest {}".format(index)
        )
        relative = phase_one.normalized_relative_path(
            manifest["path"], "closure v2 manifest path"
        )
        if relative.parts != (relative.name,):
            raise ClosureError("closure v2 checkpoint manifest must be top-level")
        if not isinstance(manifest["sha256"], str) or not HEX_SHA256.fullmatch(
            manifest["sha256"]
        ):
            raise ClosureError("closure v2 checkpoint manifest digest is malformed")
        if type(manifest["size"]) is not int or manifest["size"] < 1:
            raise ClosureError("closure v2 checkpoint manifest size is invalid")
        observed_names.append(relative.as_posix())
    require_exact(observed_names, expected_names, "closure v2 checkpoint manifest order")


def expected_capture_bundle_paths(
    closure: Mapping[str, Any], probes: Mapping[str, Any]
) -> List[str]:
    paths = {
        "blockers.json",
        "checkpoint.json",
        "closure.json",
        "environment.json",
        "offline-replay.json",
        "probes.json",
        "rpm-macros.json",
        "transcripts/dnf-exact-snapshot.txt",
        "transcripts/dnf-offline.txt",
        "transcripts/dnf-online.txt",
        "transcripts/rpm-showrc-offline.txt",
    }
    for repository in closure["snapshot_repositories"]:
        repository_id = repository["id"]
        local_root = phase_one.normalized_relative_path(
            repository["local_repository_path"], "snapshot output path"
        )
        paths.add((local_root / "repodata/repomd.xml").as_posix())
        paths.add((local_root / "repodata/repomd.xml.asc").as_posix())
        paths.add("transcripts/snapshot-repomd/{}.gpgv.txt".format(repository_id))
        for metadata in repository["metadata"]:
            paths.add(
                phase_one.normalized_relative_path(
                    metadata["archive_path"], "metadata archive path"
                ).as_posix()
            )
    for package in closure["packages"]:
        paths.add(
            phase_one.normalized_relative_path(
                package["archive_path"], "RPM archive path"
            ).as_posix()
        )
        paths.add(
            phase_one.normalized_relative_path(
                package["signature_transcript_path"], "RPM transcript path"
            ).as_posix()
        )
    for probe in probes["results"]:
        probe_id = probe["id"]
        if not isinstance(probe_id, str) or not re.fullmatch(r"[a-z0-9-]+", probe_id):
            raise ClosureError("probe transcript identity is unsafe")
        paths.add("transcripts/probes/{}.txt".format(probe_id))
    return sorted(paths)


def expected_capture_bundle_paths_v2(
    closure: Mapping[str, Any], probes: Mapping[str, Any]
) -> List[str]:
    paths = {
        "archives/snapshot-repositories/RPM-GPG-KEY-Rocky-10",
        "blockers.json",
        "checkpoint.json",
        "closure.json",
        "environment.json",
        "inputs/kernel.spec",
        "offline-replay.json",
        "probes.json",
        "resolution-input.json",
        "rpm-macros.json",
        "snapshot-input.json",
        "transcripts/dnf-exact-snapshot.txt",
        "transcripts/dnf-offline.txt",
        "transcripts/dnf-online.txt",
        "transcripts/rpm-showrc-offline.txt",
        "transcripts/rpm-showrc-resolution.txt",
        "transcripts/rpmspec-buildrequires.txt",
    }
    for repository in closure["snapshot_repositories"]:
        repository_id = repository["id"]
        local_root = phase_one.normalized_relative_path(
            repository["local_repository_path"], "snapshot v2 output path"
        )
        paths.add((local_root / "repodata/repomd.xml").as_posix())
        paths.add((local_root / "repodata/repomd.xml.asc").as_posix())
        paths.add((local_root / "repodata/signature.json").as_posix())
        for metadata in repository["metadata"]:
            paths.add(
                phase_one.normalized_relative_path(
                    metadata["archive_path"], "metadata v2 archive path"
                ).as_posix()
            )
    for package in closure["packages"]:
        paths.add(
            phase_one.normalized_relative_path(
                package["archive_path"], "RPM archive path"
            ).as_posix()
        )
        paths.add(
            phase_one.normalized_relative_path(
                package["signature_transcript_path"], "RPM transcript path"
            ).as_posix()
        )
    for probe in probes["results"]:
        probe_id = probe["id"]
        if not isinstance(probe_id, str) or not re.fullmatch(r"[a-z0-9-]+", probe_id):
            raise ClosureError("probe transcript identity is unsafe")
        paths.add("transcripts/probes/{}.txt".format(probe_id))
    return sorted(paths)


def capture(
    repo: Path,
    snapshot_artifact: Path,
    snapshot_sha256: str,
    snapshot_source_commit: str,
    snapshot_workflow_ref: str,
    snapshot_run_id: str,
    snapshot_run_attempt: str,
    bootstrap_manifest: Path,
    output_dir: Path,
    identity: Mapping[str, Any],
) -> None:
    if os.uname().machine != "x86_64":
        raise ClosureError("capture runtime is not x86_64")
    runtime_os_release = phase_one.parse_os_release(runtime_os_release_bytes())
    contract = validate_contract(repo)
    (
        plan,
        toolchain,
        _,
        source,
        toolchain_blockers,
        config_blockers,
        _,
    ) = phase_one.load_locked_inputs(repo)
    runtime = validate_snapshot_runtime_identity(
        snapshot_sha256,
        snapshot_source_commit,
        snapshot_workflow_ref,
        snapshot_run_id,
        snapshot_run_attempt,
        identity,
    )
    bootstrap, bootstrap_bytes = phase_one.validate_bootstrap_manifest(
        bootstrap_manifest, identity, plan
    )
    with V2OutputTransaction(output_dir) as output, tempfile.TemporaryDirectory(
        prefix="mckernel-rk003-closure-"
    ) as temporary_name:
        temporary = Path(temporary_name)
        snapshot_tree, snapshot_manifest, snapshot_input = stage_verify_and_extract_snapshot(
            repo, snapshot_artifact, runtime, contract, temporary
        )
        source_snapshot_membership = validate_source_primary_membership(
            snapshot_tree, snapshot_manifest, source, contract
        )
        (
            snapshot_roots,
            snapshot_manifests,
            dnf_repositories,
            release_key_path,
        ) = materialize_snapshot_v2_repositories(
            snapshot_tree, snapshot_manifest, output, contract
        )
        release_key_size, release_key_digest = output.hash_file(
            PurePosixPath(
                "archives/snapshot-repositories/RPM-GPG-KEY-Rocky-10"
            )
        )
        require_exact(
            release_key_size, plan["release_key"]["size"], "release key size"
        )
        require_exact(
            release_key_digest,
            plan["release_key"]["sha256"],
            "release key digest",
        )
        verification_root = prepare_empty_directory(
            temporary / "verification", "signature verification root"
        )
        _, rpm_db = phase_one.create_verification_keyrings(
            release_key_path, verification_root, plan["release_key"]["fingerprint"]
        )
        primary = load_primary_indexes_v2(snapshot_roots, snapshot_manifests)
        validate_locked_primary_membership(primary, toolchain)
        resolution_input = derive_resolution_input(
            output,
            temporary,
            contract,
            toolchain,
            source,
        )
        resolution_input["credit_eligible"] = False
        resolution_input["gate_claims"] = dict(contract["gate_claims"])
        resolution_input["source_snapshot_membership"] = source_snapshot_membership
        roots = [item["value"] for item in resolution_input["resolution_roots"]]
        direct_nevras = toolchain["closure"]["direct_nevras"]
        snapshot_input["bootstrap_manifest"] = {
            "sha256": hashlib.sha256(bootstrap_bytes).hexdigest(),
            "size": len(bootstrap_bytes),
        }
        snapshot_input["bootstrap_checkpoint_id"] = bootstrap["checkpoint_id"]
        snapshot_input["credit_eligible"] = False
        snapshot_input["gate_claims"] = dict(contract["gate_claims"])
        validate_snapshot_input_v2(snapshot_input, contract)
        validate_resolution_input_v2(resolution_input, contract)

        online_root = prepare_empty_directory(temporary / "online-root", "online installroot")
        online = online_command(
            online_root, dnf_repositories, snapshot_roots, roots
        )
        online_stdout, online_stderr = run_command(
            online, acquisition_environment(os.environ)
        )
        output.write_bytes(
            PurePosixPath("transcripts/dnf-online.txt"),
            command_transcript(online, online_stdout, online_stderr),
        )
        cache_dir = online_root / "var/cache/dnf"
        if cache_dir.is_symlink() or not cache_dir.is_dir():
            raise ClosureError("DNF did not retain its cache inside the online installroot")
        verify_cached_repomd(cache_dir, dnf_repositories)
        cached = sorted(cache_dir.rglob("*.rpm"))
        if not cached or len(cached) > MAX_CAPTURED_RPMS:
            raise ClosureError("captured RPM count is empty or exceeds its bound")
        captured_bytes = 0
        for cached_path in cached:
            resolved_cached = cached_path.resolve()
            if (
                cached_path.is_symlink()
                or cached_path != resolved_cached
                or os.path.commonpath((str(cache_dir.resolve()), str(resolved_cached)))
                != str(cache_dir.resolve())
                or not cached_path.is_file()
            ):
                raise ClosureError("DNF cache contains an unsafe RPM path")
            captured_bytes += cached_path.stat().st_size
            if captured_bytes > MAX_CAPTURED_BYTES:
                raise ClosureError("captured RPM bytes exceed the artifact bound")
        rows: List[Dict[str, Any]] = []
        paths_by_nevra: Dict[str, Path] = {}
        for source_path in cached:
            nevra = rpm_nevra(source_path)
            if nevra in paths_by_nevra:
                previous_size, previous_digest = sha256_file(paths_by_nevra[nevra])
                size, digest = sha256_file(source_path)
                if (size, digest) != (previous_size, previous_digest):
                    raise ClosureError("duplicate cached NEVRA has different bytes")
                continue
            metadata = primary.get(nevra)
            if metadata is None:
                raise ClosureError("closure RPM is absent from signed primary: {}".format(nevra))
            size, digest = sha256_file(source_path)
            require_exact(size, metadata["size"], "closure RPM size")
            require_exact(digest, metadata["sha256"], "closure RPM digest")
            repository = repository_for_metadata(metadata, dnf_repositories)
            filename = PurePosixPath(metadata["repository_location"]).name
            archive_relative = (
                PurePosixPath("archives/snapshot-repositories")
                / repository["id"]
                / PurePosixPath(metadata["repository_location"])
            )
            archive_path = output.copy_file(source_path, archive_relative)
            signature, transcript = phase_one.verify_rpm_signature(
                source_path, rpm_db, plan["release_key"]["fingerprint"]
            )
            transcript_relative = (
                PurePosixPath("transcripts/rpmkeys")
                / repository["id"]
                / (filename + ".txt")
            )
            output.write_bytes(transcript_relative, transcript)
            row = dict(metadata)
            row.update(
                {
                    "archive_path": archive_relative.as_posix(),
                    "signature": signature,
                    "signature_transcript_path": transcript_relative.as_posix(),
                }
            )
            rows.append(row)
            paths_by_nevra[nevra] = archive_path
        rows.sort(key=lambda item: item["nevra"])
        transaction_nevras = [item["nevra"] for item in rows]
        verify_transitive_inventory(transaction_nevras, direct_nevras)
        shutil.rmtree(str(online_root))
        if online_root.exists() or online_root.is_symlink():
            raise ClosureError("online installroot cleanup failed before exact snapshot solve")

        snapshot_solve_root = prepare_empty_directory(
            temporary / "snapshot-solve-root", "exact snapshot solve installroot"
        )
        snapshot_solve = snapshot_solve_command(
            snapshot_solve_root, dnf_repositories, snapshot_roots, roots
        )
        if any("https://" in item or "http://" in item for item in snapshot_solve):
            raise ClosureError("exact snapshot solve command contains a network URL")
        snapshot_stdout, snapshot_stderr = run_command(
            snapshot_solve, private_environment(os.environ)
        )
        snapshot_transcript = command_transcript(
            snapshot_solve, snapshot_stdout, snapshot_stderr
        )
        output.write_bytes(
            PurePosixPath("transcripts/dnf-exact-snapshot.txt"),
            snapshot_transcript,
        )
        snapshot_inventory = installed_nevras(snapshot_solve_root)
        require_exact(
            snapshot_inventory,
            transaction_nevras,
            "exact snapshot root solve inventory",
        )
        shutil.rmtree(str(snapshot_solve_root))
        if snapshot_solve_root.exists() or snapshot_solve_root.is_symlink():
            raise ClosureError("exact snapshot solve cleanup failed before offline replay")

        offline_root = prepare_empty_directory(temporary / "offline-root", "offline installroot")
        rpm_paths = [paths_by_nevra[item["nevra"]] for item in rows]
        offline = offline_command(offline_root, rpm_paths)
        if any("repofrompath" in item or item.startswith("--enablerepo") for item in offline):
            raise ClosureError("offline command contains a repository enablement")
        if offline.count("--disablerepo=*") != 1:
            raise ClosureError("offline command does not disable every repository")
        offline_stdout, offline_stderr = run_command(offline, private_environment(os.environ))
        offline_transcript = command_transcript(
            offline, offline_stdout, offline_stderr
        )
        output.write_bytes(
            PurePosixPath("transcripts/dnf-offline.txt"), offline_transcript
        )
        offline_inventory = installed_nevras(offline_root)
        require_exact(offline_inventory, transaction_nevras, "offline installed closure")
        offline_os_release_path = chroot_regular_file(
            offline_root, "/etc/os-release", "offline os-release"
        )
        offline_os_release = phase_one.parse_os_release(
            read_regular_bytes(offline_os_release_path, "offline os-release")
        )

        prepare_chroot_devices(offline_root)
        probes = capture_probes(
            offline_root,
            toolchain,
            contract["metadata_reconciliation"]["llvm_config_owner"],
            output,
        )
        probes["credit_eligible"] = False
        probes["gate_claims"] = dict(contract["gate_claims"])
        probes["schema_version"] = V2_SCHEMA_VERSION
        macro_stdout, macro_stderr = chroot_probe(offline_root, ["rpm", "--showrc"])
        macro_transcript = command_transcript(
            ["rpm", "--showrc"], macro_stdout, macro_stderr
        )
        output.write_bytes(
            PurePosixPath("transcripts/rpm-showrc-offline.txt"), macro_transcript
        )
        rpm_set_bytes = "".join(
            "{}\t{}\n".format(item["nevra"], item["sha256"]) for item in rows
        ).encode("utf-8")
        closure = {
            "all_archives_verified": True,
            "all_binary_repomd_data_materialized": True,
            "all_signatures_verified": True,
            "configured_network_sources": [
                repository["base_url"] for repository in dnf_repositories
            ],
            "credit_eligible": False,
            "exact_snapshot_root_solve_verified": True,
            "gate_claims": dict(contract["gate_claims"]),
            "network_isolation_claimed": False,
            "package_count": len(rows),
            "package_bytes": sum(item["size"] for item in rows),
            "packages": rows,
            "resolution_root_count": len(roots),
            "resolution_roots": list(resolution_input["resolution_roots"]),
            "resolution_inputs_sha256": resolution_input[
                "resolution_inputs_sha256"
            ],
            "rpm_set_sha256": hashlib.sha256(rpm_set_bytes).hexdigest(),
            "schema_version": V2_SCHEMA_VERSION,
            "snapshot_input": {
                "artifact_sha256": snapshot_input["artifact"]["sha256"],
                "capture_id": snapshot_input["capture_id"],
                "snapshot_identity": snapshot_input["snapshot_identity"],
                "source_commit": snapshot_input["execution_identity"][
                    "source_commit"
                ],
            },
            "snapshot_repositories": snapshot_manifests,
            "unresolved_dependencies": [],
        }
        offline_manifest = {
            "all_repositories_disabled": True,
            "command": offline,
            "credit_eligible": False,
            "empty_installroot_verified": True,
            "enabled_repository_count": 0,
            "gate_claims": dict(contract["gate_claims"]),
            "installed_package_count": len(offline_inventory),
            "installed_rpm_set_sha256": hashlib.sha256(rpm_set_bytes).hexdigest(),
            "network_isolation_claimed": False,
            "network_scope": contract["network_contract"]["scope"],
            "proxy_loopback_defense": True,
            "snapshot_solve": {
                "command": snapshot_solve,
                "empty_installroot_verified": True,
                "installed_package_count": len(snapshot_inventory),
                "installed_rpm_set_sha256": hashlib.sha256(rpm_set_bytes).hexdigest(),
                "local_file_repositories_only": True,
                "transaction_exit_code": 0,
                "transaction_output_sha256": hashlib.sha256(snapshot_transcript).hexdigest(),
            },
            "schema_version": V2_SCHEMA_VERSION,
            "transaction_exit_code": 0,
            "transaction_output_sha256": hashlib.sha256(offline_transcript).hexdigest(),
        }
        environment = {
            "architecture": os.uname().machine,
            "container_image": phase_one.CONTAINER_IMAGE,
            "container_manifest_digest": plan["container"]["manifest_digest"],
            "container_platform": plan["container"]["platform"],
            "credit_eligible": False,
            "gate_claims": dict(contract["gate_claims"]),
            "github": dict(identity),
            "offline_installroot_package_count": len(offline_inventory),
            "offline_os_release": offline_os_release,
            "offline_rpm_set_sha256": hashlib.sha256(rpm_set_bytes).hexdigest(),
            "resolution_inputs_sha256": resolution_input[
                "resolution_inputs_sha256"
            ],
            "runtime_os_release": runtime_os_release,
            "schema_version": V2_SCHEMA_VERSION,
            "snapshot_tar_sha256": snapshot_input["artifact"]["sha256"],
            "snapshot_solve_package_count": len(snapshot_inventory),
        }
        probes["environment_manifest_sha256"] = hashlib.sha256(
            phase_one.canonical_json_bytes(environment)
        ).hexdigest()
        closure["environment_manifest_sha256"] = probes[
            "environment_manifest_sha256"
        ]
        offline_manifest["environment_manifest_sha256"] = probes[
            "environment_manifest_sha256"
        ]
        macro_manifest = {
            "command": ["rpm", "--showrc"],
            "credit_eligible": False,
            "gate_claims": dict(contract["gate_claims"]),
            "output_sha256": hashlib.sha256(macro_transcript).hexdigest(),
            "output_size": len(macro_transcript),
            "schema_version": V2_SCHEMA_VERSION,
        }
        blockers = {
            "config_lock_blockers_at_capture": list(config_blockers),
            "credit_eligible": False,
            "gate_claims": dict(contract["gate_claims"]),
            "phase_success_blockers": list(contract["success_blockers"]),
            "schema_version": V2_SCHEMA_VERSION,
            "toolchain_lock_blockers_at_capture": list(toolchain_blockers),
        }
        validate_capture_manifest_schemas_v2(
            closure,
            offline_manifest,
            probes,
            macro_manifest,
            environment,
            blockers,
        )
        for name, value in (
            ("closure.json", closure),
            ("offline-replay.json", offline_manifest),
            ("probes.json", probes),
            ("rpm-macros.json", macro_manifest),
            ("environment.json", environment),
            ("resolution-input.json", resolution_input),
            ("snapshot-input.json", snapshot_input),
            ("blockers.json", blockers),
        ):
            output.write_json(PurePosixPath(name), value)
        manifests = []
        for name in (
            "blockers.json",
            "closure.json",
            "environment.json",
            "offline-replay.json",
            "probes.json",
            "resolution-input.json",
            "rpm-macros.json",
            "snapshot-input.json",
        ):
            size, digest = output.hash_file(PurePosixPath(name))
            manifests.append({"path": name, "sha256": digest, "size": size})
        checkpoint = {
            "claims": dict(snapshot_v2.FALSE_CLAIMS),
            "credit_eligible": False,
            "gate_claims": dict(contract["gate_claims"]),
            "github": dict(identity),
            "manifests": manifests,
            "phase": PHASE_ID,
            "schema_version": V2_SCHEMA_VERSION,
            "snapshot_identity": snapshot_input["snapshot_identity"],
            "snapshot_source_commit": snapshot_input["execution_identity"][
                "source_commit"
            ],
            "snapshot_tar_sha256": snapshot_input["artifact"]["sha256"],
            "successful_capture_requires_independent_review": True,
        }
        validate_capture_checkpoint_v2(checkpoint)
        output.write_json(PurePosixPath("checkpoint.json"), checkpoint)
        output.write_sha256sums()
        output.verify_sha256sums(expected_capture_bundle_paths_v2(closure, probes))
        output.publish()


def validate_workflow(repo: Path) -> None:
    workflow_path = safe_repo_file(repo, WORKFLOW_PATH.as_posix())
    workflow_bytes = read_regular_bytes(workflow_path, "closure workflow")
    require_exact(
        hashlib.sha256(workflow_bytes).hexdigest(),
        EXPECTED_WORKFLOW_SHA256,
        "closure workflow digest",
    )
    text = workflow_bytes.decode("utf-8")
    required = {
        "python3 scripts/rocky_kernel_closure_offline.py": 2,
        "python3 scripts/rocky_repository_snapshot_capture.py": 1,
        "--source-commit \"$EXPECTED_HEAD_SHA\"": 1,
        "--workflow-ref \"$SNAPSHOT_WORKFLOW_REF\"": 1,
        "PYTHONDONTWRITEBYTECODE=1 python3 -m unittest -v": 1,
        "--phase closure-offline": 1,
        "--bootstrap-manifest \"$EVIDENCE_ROOT/bootstrap/bootstrap.json\"": 1,
        "--snapshot-artifact \"$SNAPSHOT_DOWNLOAD/payload/snapshot.tar\"": 1,
        "--snapshot-sha256 \"$SNAPSHOT_TAR_SHA256\"": 1,
        "--snapshot-source-commit \"$EXPECTED_HEAD_SHA\"": 1,
        "--snapshot-workflow-ref \"$SNAPSHOT_WORKFLOW_REF\"": 1,
        "--snapshot-run-id \"$SNAPSHOT_RUN_ID\"": 1,
        "--snapshot-run-attempt \"$SNAPSHOT_RUN_ATTEMPT\"": 1,
        "--output-dir \"$EVIDENCE_ROOT/closure-offline\"": 1,
        "test \"$GITHUB_WORKFLOW_SHA\" = \"$EXPECTED_HEAD_SHA\"": 1,
        "--disablerepo=*": 0,
        "--direct-root": 0,
        "--phase repository-direct": 0,
        "compression-level: 0": 1,
        "- .github/workflows/rocky-kernel-platform-evidence.yml": 2,
        "- .github/workflows/rocky-repository-snapshot-capture-v2.yml": 2,
        "- host-kernel/rocky/**": 2,
        "- scripts/rocky_kernel_platform_evidence.py": 2,
        "- scripts/rocky_kernel_platform_lock.py": 2,
        "- scripts/rocky_kernel_source_lock.py": 2,
        "- scripts/rocky_repository_snapshot_capture.py": 2,
        "- scripts/tests/test_rocky_kernel_closure_offline.py": 2,
        "- scripts/tests/test_rocky_repository_snapshot_capture.py": 2,
        "run-id: ${{ inputs.snapshot_run_id }}": 1,
        "name: rocky-repository-snapshot-v2-${{ inputs.snapshot_run_id }}-${{ inputs.snapshot_run_attempt }}": 1,
        "repository: ${{ github.repository }}": 1,
        "github-token: ${{ github.token }}": 1,
        "cmp \"$EVIDENCE_ROOT/expected-snapshot.tar.sha256\" \"$snapshot_self_digest\"": 1,
        "test \"$artifact_size\" -le {}".format(
            snapshot_v2.TAR_LIMITS["max_snapshot_tar_bytes"]
        ): 1,
        "path: ${{ runner.temp }}/rk003-closure-offline-evidence/closure-offline/": 1,
    }
    for needle, expected in required.items():
        if text.count(needle) != expected:
            raise ClosureError(
                "workflow fragment count differs for {!r}: {} != {}".format(
                    needle, text.count(needle), expected
                )
            )
    if "credit forbidden" not in text.lower():
        raise ClosureError("workflow omits its credit-forbidden scope")
    if "latest" in text.lower():
        raise ClosureError("workflow may not select a mutable latest artifact")
    before_checkout = text.find("Reject mutable or ambiguous dispatch identities")
    first_checkout = text.find(EXPECTED_WORKFLOW_USES[0])
    download = text.find(EXPECTED_WORKFLOW_USES[2])
    digest_binding = text.find("Bind the downloaded snapshot to the external digest")
    capture_step = text.find("Capture complete closure from the verified snapshot")
    if not (
        0 <= before_checkout < first_checkout < download < digest_binding < capture_step
    ):
        raise ClosureError("workflow snapshot identity ordering changed")
    dispatch_only_steps = (
        "Reject mutable or ambiguous dispatch identities",
        "Require an empty snapshot artifact landing directory",
        "Download the exact cross-run snapshot artifact",
        "Bind the downloaded snapshot to the external digest",
        "Capture complete closure from the verified snapshot and replay offline",
    )
    dispatch_guard = "if: ${{ github.event_name == 'workflow_dispatch' }}"
    for step_name in dispatch_only_steps:
        offset = text.find("- name: " + step_name)
        if offset < 0 or text.find(dispatch_guard, offset, offset + 300) < 0:
            raise ClosureError("workflow dispatch guard is missing for " + step_name)
    upload_offset = text.find("- name: Upload closure, replay, and probe evidence")
    upload_guard = "if: ${{ always() && github.event_name == 'workflow_dispatch' }}"
    if upload_offset < 0 or text.find(upload_guard, upload_offset, upload_offset + 300) < 0:
        raise ClosureError("workflow upload is not dispatch-only")
    uses: List[str] = []
    for line in text.splitlines():
        if re.match(r"^\s*uses\s*:", line):
            match = re.fullmatch(r"\s*uses:\s+(\S+)(?:\s+#.*)?", line)
            if match is None:
                raise ClosureError("workflow action identity is ambiguous")
            uses.append(match.group(1))
    require_exact(uses, EXPECTED_WORKFLOW_USES, "closure workflow actions")
    immutable_counts = {
        "image: " + phase_one.CONTAINER_IMAGE: 1,
        "runs-on: ubuntu-24.04": 1,
        "permissions:\n  actions: read\n  contents: read": 1,
        "persist-credentials: false": 2,
        "set-safe-directory: false": 1,
        "set-safe-directory: true": 1,
        "actions/checkout@11d5960a326750d5838078e36cf38b85af677262": 2,
        "actions/download-artifact@d3f86a106a0bac45b974a628896c90dbdf5c8093": 1,
        "actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02": 1,
        "required: true": 5,
        "type: string": 5,
        "retention-days: 30": 1,
        "if-no-files-found: error": 1,
    }
    for needle, expected in immutable_counts.items():
        require_exact(text.count(needle), expected, "workflow immutable fragment")


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[1])
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--check", action="store_true")
    modes.add_argument("--capture", action="store_true")
    parser.add_argument("--phase", choices=[PHASE_ID])
    parser.add_argument("--bootstrap-manifest", type=Path)
    parser.add_argument("--snapshot-artifact", type=Path)
    parser.add_argument("--snapshot-sha256")
    parser.add_argument("--snapshot-source-commit")
    parser.add_argument("--snapshot-workflow-ref")
    parser.add_argument("--snapshot-run-id")
    parser.add_argument("--snapshot-run-attempt")
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--github-head-sha")
    parser.add_argument("--github-run-id")
    parser.add_argument("--github-run-attempt")
    parser.add_argument("--github-repository")
    parser.add_argument("--container-image")
    return parser.parse_args(argv)


def main(argv: Sequence[str]) -> int:
    args = parse_args(argv)
    repo = args.repo.resolve()
    try:
        validate_python36_runtime(repo)
        contract = validate_contract(repo)
        validate_workflow(repo)
        if args.check:
            run_only = (
                args.phase,
                args.bootstrap_manifest,
                args.snapshot_artifact,
                args.snapshot_sha256,
                args.snapshot_source_commit,
                args.snapshot_workflow_ref,
                args.snapshot_run_id,
                args.snapshot_run_attempt,
                args.output_dir,
                args.github_head_sha,
                args.github_run_id,
                args.github_run_attempt,
                args.github_repository,
                args.container_image,
            )
            if any(item is not None for item in run_only):
                raise ClosureError("--check rejects capture-only arguments")
            print("RK-003 closure/offline contract verified; gate credit remains forbidden")
            return 0
        required = {
            "--phase": args.phase,
            "--bootstrap-manifest": args.bootstrap_manifest,
            "--snapshot-artifact": args.snapshot_artifact,
            "--snapshot-sha256": args.snapshot_sha256,
            "--snapshot-source-commit": args.snapshot_source_commit,
            "--snapshot-workflow-ref": args.snapshot_workflow_ref,
            "--snapshot-run-id": args.snapshot_run_id,
            "--snapshot-run-attempt": args.snapshot_run_attempt,
            "--output-dir": args.output_dir,
            "--github-head-sha": args.github_head_sha,
            "--github-run-id": args.github_run_id,
            "--github-run-attempt": args.github_run_attempt,
            "--github-repository": args.github_repository,
            "--container-image": args.container_image,
        }
        missing = [name for name, value in required.items() if value is None]
        if missing:
            raise ClosureError("capture requires {}".format(", ".join(missing)))
        require_exact(args.phase, PHASE_ID, "capture phase")
        identity = phase_one.validate_run_identity(
            args.github_head_sha,
            args.github_run_id,
            args.github_run_attempt,
            args.github_repository,
            args.container_image,
        )
        capture(
            repo,
            args.snapshot_artifact,
            args.snapshot_sha256,
            args.snapshot_source_commit,
            args.snapshot_workflow_ref,
            args.snapshot_run_id,
            args.snapshot_run_attempt,
            args.bootstrap_manifest,
            args.output_dir,
            identity,
        )
        print("captured closure/offline evidence; RK-003 and dependent gates remain uncredited")
        return 0
    except (
        ClosureError,
        phase_one.EvidenceError,
        snapshot_v2.SnapshotError,
        OSError,
        UnicodeError,
        ValueError,
    ) as exc:
        print("Rocky closure/offline evidence error: {}".format(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
