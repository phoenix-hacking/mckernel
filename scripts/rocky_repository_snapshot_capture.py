#!/usr/bin/env python3
"""Capture a bounded, signed Rocky repository-metadata snapshot.

This is a capture and drift-diagnostics checkpoint, not an acceptance gate.
The versioned contract hard-codes every credit and gate claim to ``false``.
The captured tar contains the exact release key, repomd.xml, detached
signature, and every metadata object referenced by each verified repomd.xml.
"""

import argparse
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
import shutil
import stat
import subprocess
import sys
import tarfile
import tempfile
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path, PurePosixPath


CONTRACT_PATH = Path(
    "host-kernel/rocky/evidence/repository-snapshot-capture-contract-v2.json"
)
CHECKER_PATH = Path("scripts/rocky_repository_snapshot_capture.py")
TEST_PATH = Path("scripts/tests/test_rocky_repository_snapshot_capture.py")
WORKFLOW_PATH = Path(".github/workflows/rocky-repository-snapshot-capture-v2.yml")
CAPTURE_ID = "rocky-10.2-x86_64-repository-metadata-capture-v2"
RELEASE_FINGERPRINT = "FC226859C0860BF0DDB95B085B106C736FEDFC85"
RELEASE_KEY_SHA256 = (
    "be8c4f070b696e64d8ce40e59a95a57e8b5c776f0015c2fd64e14b896622bdb4"
)
RELEASE_KEY_SIZE = 1688
RELEASE_KEY_URL = "https://download.rockylinux.org/pub/rocky/RPM-GPG-KEY-Rocky-10"
REPOSITORIES = [
    (
        "source-baseos",
        "source",
        "https://download.rockylinux.org/pub/rocky/10.2/BaseOS/source/tree/",
    ),
    (
        "baseos",
        "binary",
        "https://download.rockylinux.org/pub/rocky/10.2/BaseOS/x86_64/os/",
    ),
    (
        "appstream",
        "binary",
        "https://download.rockylinux.org/pub/rocky/10.2/AppStream/x86_64/os/",
    ),
    (
        "crb",
        "binary",
        "https://download.rockylinux.org/pub/rocky/10.2/CRB/x86_64/os/",
    ),
]
REQUIRED_INPUTS = {
    "checker": CHECKER_PATH.as_posix(),
    "contract": CONTRACT_PATH.as_posix(),
    "tests": TEST_PATH.as_posix(),
    "workflow": WORKFLOW_PATH.as_posix(),
}
FALSE_CLAIMS = {
    "accepted_checkpoint": False,
    "credit_eligible": False,
    "durable_archive": False,
    "gate_rk_001": False,
    "gate_rk_003": False,
    "gate_rk_005": False,
    "old_checkpoint_replaced": False,
    "repository_metadata_closure_accepted": False,
    "routine_ci_replay_ready": False,
    "rpm_closure_complete": False,
    "tracker_credit": False,
}
TARGET = {
    "architecture": "x86_64",
    "distribution": "Rocky Linux",
    "release": "10.2",
}

MAX_JSON_BYTES = 2 * 1024 * 1024
MAX_JSON_NESTING = 64
MAX_JSON_INTEGER_DIGITS = 20
SHA256 = re.compile(r"^[0-9a-f]{64}$")
SOURCE_COMMIT = re.compile(r"^[0-9a-f]{40}$")
REPO_ID = re.compile(r"^[a-z][a-z0-9-]{0,31}$")
REPOMD_NS = "http://linux.duke.edu/metadata/repo"
WORKFLOW_REPOSITORY = "phoenix-hacking/mckernel"
WORKFLOW_REF_PREFIX = (
    WORKFLOW_REPOSITORY + "/" + WORKFLOW_PATH.as_posix() + "@"
)
EXECUTION_IDENTITY_POLICY = {
    "source_commit": "required exact lowercase 40-hex checked-out Git commit",
    "workflow_ref_prefix": WORKFLOW_REF_PREFIX,
}
GIT_AUTHORITY_EXECUTABLE = "/usr/bin/git"
GIT_AUTHORITY_ENVIRONMENT = {
    "GIT_ATTR_NOSYSTEM": "1",
    "GIT_CONFIG_GLOBAL": os.devnull,
    "GIT_CONFIG_NOSYSTEM": "1",
    "GIT_GRAFT_FILE": os.devnull,
    "GIT_NO_REPLACE_OBJECTS": "1",
    "GIT_OPTIONAL_LOCKS": "0",
    "GIT_PAGER": "cat",
    "GIT_TERMINAL_PROMPT": "0",
    "HOME": "/nonexistent",
    "LANG": "C",
    "LC_ALL": "C",
    "PAGER": "cat",
    "PATH": "/usr/bin:/bin",
    "XDG_CONFIG_HOME": "/nonexistent",
}
GIT_AUTHORITY_CONFIG = [
    "advice.graftFileDeprecated=false",
    "core.attributesFile=/dev/null",
    "core.fsmonitor=false",
    "core.hooksPath=/dev/null",
    "core.pager=cat",
    "core.sshCommand=/usr/bin/false",
    "credential.helper=",
    "diff.external=",
    "fetch.recurseSubmodules=false",
    "interactive.diffFilter=",
    "protocol.allow=never",
    "submodule.recurse=false",
]
GIT_AUTHORITY_POLICY = {
    "config_overrides": GIT_AUTHORITY_CONFIG,
    "environment": GIT_AUTHORITY_ENVIRONMENT,
    "executable": GIT_AUTHORITY_EXECUTABLE,
    "inherit_environment": False,
}
TAR_LIMITS = {
    "max_snapshot_tar_bytes": 4328521728,
    "max_tar_member_bytes": 536870912,
    "max_tar_members": 300,
    "max_tar_payload_bytes": 4311744512,
}
LIMITS = {
    "download_timeout_seconds": 90,
    "max_key_bytes": 65536,
    "max_metadata_object_bytes": 536870912,
    "max_metadata_open_bytes": 4294967296,
    "max_open_bytes_total": 8589934592,
    "max_repository_objects": 64,
    "max_repomd_bytes": 8388608,
    "max_signature_bytes": 1048576,
    "max_snapshot_tar_bytes": 4328521728,
    "max_tar_member_bytes": 536870912,
    "max_tar_members": 300,
    "max_tar_payload_bytes": 4311744512,
    "max_total_download_bytes": 4294967296,
    "redirect_limit": 5,
}
NETWORK_POLICY = {
    "allowed_hosts": ["download.rockylinux.org"],
    "policy": (
        "HTTPS only; reject credentials, ports, query strings, fragments, "
        "cross-policy redirects, content encodings, path traversal, and objects "
        "not named by a verified repomd.xml"
    ),
}
ARTIFACT_POLICY = {
    "deterministic_payload": "snapshot.tar",
    "deterministic_payload_digest": "snapshot.tar.sha256",
    "format": (
        "ustar with sorted regular-file entries, uid/gid/mtime zero, empty "
        "owner/group names, and mode 0644"
    ),
    "retention_days": 30,
}
DIAGNOSTIC_BASELINES = [
    {
        "id": "source-baseos",
        "primary_sha256": (
            "1cc64f6d0e798011d1862c2284189742f6383c6fc27c84de207c739148e50209"
        ),
        "primary_size": 186048,
        "repomd_sha256": (
            "9085b7c0ce3d9ebda8cba25d3daafd13062ce7cd4a10c0036265af80449adea0"
        ),
        "signature_sha256": (
            "40e16e3d39ddc9ed7fff85201704b0805a37d732291193e6a3143a731001641e"
        ),
    },
    {
        "id": "baseos",
        "primary_sha256": (
            "6e0f444d03d0d2c15a55aecd84287914435f2573016532280d124549d9fa256d"
        ),
        "primary_size": 17598546,
        "repomd_sha256": (
            "266aec928c5111a4e5b002a3b491261b454351341ea4e9e6d22b9a596dc26c0d"
        ),
        "signature_sha256": (
            "34c9870178d2a7f194d03c35624af961fb0212e3f48292a7047ddac2b206b9fa"
        ),
    },
    {
        "id": "appstream",
        "primary_sha256": (
            "ceacd5afd9e68516c25846fc41f2c5668a4b5c2cd092b792529f74b716e91edf"
        ),
        "primary_size": 1799777,
        "repomd_sha256": (
            "067e62bd6a9c1b2c68935083cc5f0d7cdad3e8d30a2643a6d0f887a47536bd7c"
        ),
        "signature_sha256": (
            "a113f22ef47ecb6a3012ed32e15081f682652ac2d2ec84b526c6c010a7031267"
        ),
    },
    {
        "id": "crb",
        "primary_sha256": (
            "288c787cbb9142c054daef1c9fcceddae986e3d4a2853427ee7124e94d6c1b6a"
        ),
        "primary_size": 449395,
        "repomd_sha256": (
            "1ea3907a2adf3e162e09339628d52133e5c976cfa5e795779ca555cbd534e95f"
        ),
        "signature_sha256": (
            "78fe1199974c88e3891064dd7d15716c13d94227be82f6a070394c888231a530"
        ),
    },
]


def expected_contract():
    return {
        "artifact": ARTIFACT_POLICY,
        "capture_id": CAPTURE_ID,
        "claims": FALSE_CLAIMS,
        "diagnostic_baselines": DIAGNOSTIC_BASELINES,
        "execution_identity": EXECUTION_IDENTITY_POLICY,
        "git_authority": GIT_AUTHORITY_POLICY,
        "limits": LIMITS,
        "network": NETWORK_POLICY,
        "release_key": {
            "fingerprint": RELEASE_FINGERPRINT,
            "sha256": RELEASE_KEY_SHA256,
            "size": RELEASE_KEY_SIZE,
            "url": RELEASE_KEY_URL,
        },
        "repositories": [
            {"id": row[0], "kind": row[1], "base_url": row[2]}
            for row in REPOSITORIES
        ],
        "required_repository_inputs": REQUIRED_INPUTS,
        "schema_version": 2,
        "target": TARGET,
    }


class SnapshotError(RuntimeError):
    """A fail-closed snapshot capture or verification error."""


def canonical_json_bytes(value):
    try:
        text = json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        )
    except (MemoryError, OverflowError, RecursionError, TypeError, ValueError) as exc:
        raise SnapshotError("value is not canonical-JSON serializable: {}".format(exc))
    return (text + "\n").encode("ascii")


def reject_duplicate_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise SnapshotError("duplicate JSON key: {!r}".format(key))
        result[key] = value
    return result


def reject_json_constant(value):
    raise SnapshotError("non-finite JSON constant is forbidden: {}".format(value))


def parse_json_integer(value):
    digits = value[1:] if value.startswith("-") else value
    if len(digits) > MAX_JSON_INTEGER_DIGITS:
        raise SnapshotError("JSON integer exceeds the digit limit")
    return int(value)


def reject_json_float(value):
    raise SnapshotError("JSON floating-point values are forbidden: {}".format(value))


def require_bounded_json_nesting(value, label):
    stack = [(value, 1)]
    while stack:
        current, depth = stack.pop()
        if depth > MAX_JSON_NESTING:
            raise SnapshotError("{} exceeds the JSON nesting limit".format(label))
        if isinstance(current, dict):
            stack.extend((item, depth + 1) for item in current.values())
        elif isinstance(current, list):
            stack.extend((item, depth + 1) for item in current)


def strict_json_bytes(data, label):
    if len(data) > MAX_JSON_BYTES:
        raise SnapshotError("{} exceeds the JSON size limit".format(label))
    try:
        value = json.loads(
            data.decode("utf-8"),
            object_pairs_hook=reject_duplicate_pairs,
            parse_constant=reject_json_constant,
            parse_float=reject_json_float,
            parse_int=parse_json_integer,
        )
    except (
        MemoryError,
        RecursionError,
        SnapshotError,
        UnicodeDecodeError,
        ValueError,
    ) as exc:
        raise SnapshotError("cannot parse {}: {}".format(label, exc))
    if not isinstance(value, dict):
        raise SnapshotError("{} must contain one JSON object".format(label))
    require_bounded_json_nesting(value, label)
    return value


def exact_keys(value, expected, label):
    if not isinstance(value, dict):
        raise SnapshotError("{} must be an object".format(label))
    actual = set(value)
    wanted = set(expected)
    if actual != wanted:
        raise SnapshotError(
            "{} fields changed: actual={}, expected={}".format(
                label, sorted(actual), sorted(wanted)
            )
        )
    return value


def require_exact(actual, expected, label):
    """Compare recursively without Python's bool/int/float equality aliases."""
    if type(actual) is not type(expected):
        raise SnapshotError(
            "{} type changed: actual={}, expected={}".format(
                label, type(actual).__name__, type(expected).__name__
            )
        )
    if isinstance(expected, dict):
        if set(actual) != set(expected):
            raise SnapshotError(
                "{} fields changed: actual={}, expected={}".format(
                    label, sorted(actual), sorted(expected)
                )
            )
        for key in sorted(expected):
            require_exact(actual[key], expected[key], "{}.{}".format(label, key))
        return
    if isinstance(expected, list):
        if len(actual) != len(expected):
            raise SnapshotError(
                "{} length changed: actual={}, expected={}".format(
                    label, len(actual), len(expected)
                )
            )
        for index, expected_item in enumerate(expected):
            require_exact(
                actual[index], expected_item, "{}[{}]".format(label, index)
            )
        return
    if isinstance(expected, tuple):
        if len(actual) != len(expected):
            raise SnapshotError(
                "{} length changed: actual={}, expected={}".format(
                    label, len(actual), len(expected)
                )
            )
        for index, expected_item in enumerate(expected):
            require_exact(
                actual[index], expected_item, "{}[{}]".format(label, index)
            )
        return
    if actual != expected:
        raise SnapshotError(
            "{} changed: actual={!r}, expected={!r}".format(label, actual, expected)
        )


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def regular_identity(metadata):
    return (
        metadata.st_dev,
        metadata.st_ino,
        metadata.st_mode,
        metadata.st_nlink,
        metadata.st_size,
        metadata.st_mtime_ns,
        metadata.st_ctime_ns,
    )


def absolute_path(path, label):
    try:
        result = Path(os.path.abspath(str(path)))
    except (OSError, TypeError, ValueError) as exc:
        raise SnapshotError("{} is not a usable path: {}".format(label, exc))
    if not result.is_absolute() or len(result.parts) < 2:
        raise SnapshotError("{} did not normalize to a usable absolute path".format(label))
    return result


def open_directory_fd(path, label, create=False):
    if not hasattr(os, "O_DIRECTORY") or not hasattr(os, "O_NOFOLLOW"):
        raise SnapshotError("no-follow directory opening is unavailable")
    requested = absolute_path(path, label)
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    descriptor = -1
    try:
        descriptor = os.open(os.path.sep, flags)
        for component in requested.parts[1:]:
            if component in ("", ".", ".."):
                raise SnapshotError("{} path contains an unsafe component".format(label))
            try:
                child = os.open(component, flags, dir_fd=descriptor)
            except FileNotFoundError:
                if not create:
                    raise
                try:
                    os.mkdir(component, 0o700, dir_fd=descriptor)
                except FileExistsError:
                    pass
                child = os.open(component, flags, dir_fd=descriptor)
            os.close(descriptor)
            descriptor = child
        result = descriptor
        descriptor = -1
        return result
    except SnapshotError:
        raise
    except OSError as exc:
        raise SnapshotError("cannot safely open {}: {}".format(label, exc))
    finally:
        if descriptor >= 0:
            os.close(descriptor)


def make_directories_nofollow(path, label):
    descriptor = open_directory_fd(path, label, create=True)
    os.close(descriptor)


def open_regular_read(path, label):
    if not hasattr(os, "O_DIRECTORY") or not hasattr(os, "O_NOFOLLOW"):
        raise SnapshotError("no-follow file opening is unavailable")
    requested = absolute_path(path, label)
    parent_descriptor = open_directory_fd(requested.parent, label + " parent")
    flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK
    if hasattr(os, "O_BINARY"):
        flags |= os.O_BINARY
    descriptor = -1
    try:
        descriptor = os.open(requested.name, flags, dir_fd=parent_descriptor)
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode):
            raise SnapshotError("{} must be a regular file".format(label))
        result = descriptor
        descriptor = -1
        return result
    except SnapshotError:
        raise
    except OSError as exc:
        raise SnapshotError("cannot safely open {}: {}".format(label, exc))
    finally:
        os.close(parent_descriptor)
        if descriptor >= 0:
            os.close(descriptor)


def open_regular_create(path, label):
    if not hasattr(os, "O_DIRECTORY") or not hasattr(os, "O_NOFOLLOW"):
        raise SnapshotError("no-follow file creation is unavailable")
    requested = absolute_path(path, label)
    make_directories_nofollow(requested.parent, label + " parent")
    parent_descriptor = open_directory_fd(requested.parent, label + " parent")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW
    if hasattr(os, "O_BINARY"):
        flags |= os.O_BINARY
    descriptor = -1
    try:
        descriptor = os.open(
            requested.name, flags, 0o600, dir_fd=parent_descriptor
        )
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode):
            raise SnapshotError("{} must be a regular file".format(label))
        result = descriptor
        descriptor = -1
        return result
    except SnapshotError:
        raise
    except OSError as exc:
        raise SnapshotError("cannot safely create {}: {}".format(label, exc))
    finally:
        os.close(parent_descriptor)
        if descriptor >= 0:
            os.close(descriptor)


def read_regular_bytes(path, label, maximum=None, expected_mode=None):
    descriptor = open_regular_read(path, label)
    chunks = []
    size = 0
    try:
        before = regular_identity(os.fstat(descriptor))
        if (
            expected_mode is not None
            and stat.S_IMODE(before[2]) != expected_mode
        ):
            raise SnapshotError(
                "{} permission mode changed: actual={:04o}, expected={:04o}".format(
                    label, stat.S_IMODE(before[2]), expected_mode
                )
            )
        if maximum is not None and before[4] > maximum:
            raise SnapshotError("{} exceeds its byte limit".format(label))
        while True:
            chunk = os.read(descriptor, 1024 * 1024)
            if not chunk:
                break
            size += len(chunk)
            if maximum is not None and size > maximum:
                raise SnapshotError("{} exceeds its byte limit".format(label))
            chunks.append(chunk)
        after = regular_identity(os.fstat(descriptor))
    except OSError as exc:
        raise SnapshotError("cannot read {}: {}".format(label, exc))
    finally:
        os.close(descriptor)
    if before != after or size != after[4]:
        raise SnapshotError("{} changed while it was read".format(label))
    return b"".join(chunks)


def write_all(descriptor, data, label):
    offset = 0
    try:
        while offset < len(data):
            written = os.write(descriptor, data[offset:])
            if written <= 0:
                raise SnapshotError("cannot write {} completely".format(label))
            offset += written
    except OSError as exc:
        raise SnapshotError("cannot write {}: {}".format(label, exc))


def write_regular_exclusive(path, data, label, mode=0o600):
    descriptor = open_regular_create(path, label)
    try:
        write_all(descriptor, data, label)
        os.fchmod(descriptor, mode)
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_size != len(data):
            raise SnapshotError("{} changed while it was written".format(label))
    finally:
        os.close(descriptor)


def sha256_file(path):
    digest = hashlib.sha256()
    size = 0
    descriptor = open_regular_read(path, "hash input")
    try:
        before = regular_identity(os.fstat(descriptor))
        with os.fdopen(descriptor, "rb") as source:
            descriptor = -1
            while True:
                chunk = source.read(1024 * 1024)
                if not chunk:
                    break
                size += len(chunk)
                digest.update(chunk)
            after = regular_identity(os.fstat(source.fileno()))
    except OSError as exc:
        raise SnapshotError("cannot hash {}: {}".format(path, exc))
    finally:
        if descriptor >= 0:
            os.close(descriptor)
    if before != after or size != after[4]:
        raise SnapshotError("hash input changed while it was read")
    return size, digest.hexdigest()


def normalized_relative_path(value, label):
    if not isinstance(value, str) or not value or "\\" in value or "%" in value:
        raise SnapshotError("{} must be a plain normalized relative path".format(label))
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in ("", ".", "..") for part in path.parts):
        raise SnapshotError("{} is not a normalized relative path".format(label))
    if path.as_posix() != value:
        raise SnapshotError("{} is not canonically spelled".format(label))
    return path


def within(root, candidate):
    try:
        return Path(os.path.commonpath((str(root), str(candidate)))) == root
    except ValueError:
        return False


def lexical_absolute_path(path, label):
    try:
        result = Path(os.path.abspath(str(path)))
    except (OSError, TypeError, ValueError) as exc:
        raise SnapshotError("{} is not a usable path: {}".format(label, exc))
    if not result.is_absolute():
        raise SnapshotError("{} did not normalize to an absolute path".format(label))
    return result


def require_real_directory_path(path, label):
    """Require an existing directory path with no symlink component."""
    current = Path(path.parts[0])
    for part in path.parts[1:]:
        current = current / part
        try:
            metadata = os.lstat(str(current))
        except OSError as exc:
            raise SnapshotError(
                "{} contains a missing or unreadable directory {}: {}".format(
                    label, current, exc
                )
            )
        if stat.S_ISLNK(metadata.st_mode):
            raise SnapshotError("{} contains a symlink component: {}".format(label, current))
        if not stat.S_ISDIR(metadata.st_mode):
            raise SnapshotError(
                "{} contains a non-directory component: {}".format(label, current)
            )


def lstat_optional(path, label):
    try:
        return os.lstat(str(path))
    except FileNotFoundError:
        return None
    except OSError as exc:
        raise SnapshotError("cannot inspect {} {}: {}".format(label, path, exc))


def path_contains(parent, child):
    try:
        return Path(os.path.commonpath((str(parent), str(child)))) == parent
    except ValueError:
        return False


def directory_identity(metadata):
    if not stat.S_ISDIR(metadata.st_mode):
        raise SnapshotError("stable path does not identify a directory")
    return (
        metadata.st_dev,
        metadata.st_ino,
        metadata.st_mode,
        metadata.st_uid,
        metadata.st_gid,
    )


def require_stable_directory_path(path, descriptor, expected, label):
    require_exact(
        directory_identity(os.fstat(descriptor)), expected, label + " descriptor"
    )
    reopened = open_directory_fd(path, label + " path")
    try:
        require_exact(
            directory_identity(os.fstat(reopened)), expected, label + " path"
        )
    finally:
        os.close(reopened)


def validate_capture_destinations(output_dir, diagnostics_dir):
    output_dir = lexical_absolute_path(output_dir, "capture output directory")
    diagnostics_dir = (
        lexical_absolute_path(diagnostics_dir, "capture diagnostics directory")
        if diagnostics_dir is not None
        else None
    )
    if diagnostics_dir is not None and (
        path_contains(output_dir, diagnostics_dir)
        or path_contains(diagnostics_dir, output_dir)
    ):
        raise SnapshotError(
            "capture output and diagnostics directories must not overlap"
        )

    require_real_directory_path(
        output_dir.parent, "capture output directory parent path"
    )
    parent_descriptor = open_directory_fd(
        output_dir.parent, "capture output directory parent"
    )
    try:
        parent_identity = directory_identity(os.fstat(parent_descriptor))
        try:
            output_metadata = os.stat(
                output_dir.name,
                dir_fd=parent_descriptor,
                follow_symlinks=False,
            )
        except FileNotFoundError:
            pass
        except OSError as exc:
            raise SnapshotError(
                "cannot inspect capture output directory: {}".format(exc)
            )
        else:
            if stat.S_ISLNK(output_metadata.st_mode):
                raise SnapshotError(
                    "capture output directory must not be a symlink"
                )
            raise SnapshotError("capture output directory must not already exist")

        if diagnostics_dir is not None:
            require_real_directory_path(
                diagnostics_dir.parent, "capture diagnostics directory parent path"
            )
            diagnostics_metadata = lstat_optional(
                diagnostics_dir, "capture diagnostics directory"
            )
            if diagnostics_metadata is not None:
                if stat.S_ISLNK(diagnostics_metadata.st_mode):
                    raise SnapshotError(
                        "capture diagnostics directory must not be a symlink"
                    )
                if not stat.S_ISDIR(diagnostics_metadata.st_mode):
                    raise SnapshotError(
                        "capture diagnostics destination must be a directory"
                    )
        require_stable_directory_path(
            output_dir.parent,
            parent_descriptor,
            parent_identity,
            "capture output parent",
        )
        result = (
            output_dir,
            diagnostics_dir,
            parent_descriptor,
            parent_identity,
        )
        parent_descriptor = -1
        return result
    finally:
        if parent_descriptor >= 0:
            os.close(parent_descriptor)


def validate_artifact_path(artifact, maximum_bytes):
    artifact = absolute_path(artifact, "snapshot artifact")
    descriptor = open_regular_read(artifact, "snapshot artifact")
    try:
        metadata = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    if metadata.st_size < 1 or metadata.st_size > maximum_bytes:
        raise SnapshotError("snapshot artifact size is outside its byte limit")
    return artifact


def regular_repository_file(repo, relative):
    relative = normalized_relative_path(relative.as_posix(), "repository path")
    root = repo.resolve()
    requested = root.joinpath(*relative.parts)
    resolved = requested.resolve()
    if not within(root, resolved):
        raise SnapshotError("repository path escapes checkout: {}".format(relative))
    if requested != resolved or requested.is_symlink() or not requested.is_file():
        raise SnapshotError(
            "repository input must be a regular file without symlink traversal: {}".format(
                relative
            )
        )
    return requested


def load_contract(repo):
    path = regular_repository_file(repo, CONTRACT_PATH)
    data = read_regular_bytes(
        path, "capture contract", maximum=MAX_JSON_BYTES
    )
    contract = strict_json_bytes(data, CONTRACT_PATH.as_posix())
    validate_contract(contract)
    return contract, data


def validate_contract(contract):
    exact_keys(
        contract,
        {
            "artifact",
            "capture_id",
            "claims",
            "diagnostic_baselines",
            "execution_identity",
            "git_authority",
            "limits",
            "network",
            "release_key",
            "repositories",
            "required_repository_inputs",
            "schema_version",
            "target",
        },
        "capture contract",
    )
    require_exact(contract["schema_version"], 2, "contract schema_version")
    require_exact(contract["capture_id"], CAPTURE_ID, "contract capture_id")
    require_exact(contract["claims"], FALSE_CLAIMS, "contract claims")
    require_exact(contract["target"], TARGET, "contract target")
    require_exact(
        contract["execution_identity"],
        EXECUTION_IDENTITY_POLICY,
        "contract execution identity policy",
    )
    require_exact(
        contract["git_authority"],
        GIT_AUTHORITY_POLICY,
        "contract Git authority policy",
    )
    require_exact(
        contract["required_repository_inputs"],
        REQUIRED_INPUTS,
        "contract repository inputs",
    )
    release_key = exact_keys(
        contract["release_key"],
        {"fingerprint", "sha256", "size", "url"},
        "release_key",
    )
    require_exact(release_key["fingerprint"], RELEASE_FINGERPRINT, "key fingerprint")
    require_exact(release_key["sha256"], RELEASE_KEY_SHA256, "key sha256")
    require_exact(release_key["size"], RELEASE_KEY_SIZE, "key size")
    require_exact(release_key["url"], RELEASE_KEY_URL, "key URL")

    actual_repositories = []
    if not isinstance(contract["repositories"], list):
        raise SnapshotError("contract repositories must be an array")
    for index, row in enumerate(contract["repositories"]):
        row = exact_keys(row, {"base_url", "id", "kind"}, "repository row")
        if not isinstance(row["id"], str) or not REPO_ID.fullmatch(row["id"]):
            raise SnapshotError("repository id is invalid at index {}".format(index))
        actual_repositories.append((row["id"], row["kind"], row["base_url"]))
    require_exact(actual_repositories, REPOSITORIES, "repository set and order")

    claims = contract["claims"]
    if any(value is not False for value in claims.values()):
        raise SnapshotError("every capture claim must remain false")

    network = exact_keys(
        contract["network"], {"allowed_hosts", "policy"}, "network policy"
    )
    require_exact(network["allowed_hosts"], ["download.rockylinux.org"], "allowed hosts")
    if not isinstance(network["policy"], str) or "HTTPS only" not in network["policy"]:
        raise SnapshotError("network policy must explicitly require HTTPS")

    limits = exact_keys(
        contract["limits"],
        {
            "download_timeout_seconds",
            "max_key_bytes",
            "max_metadata_object_bytes",
            "max_metadata_open_bytes",
            "max_open_bytes_total",
            "max_repository_objects",
            "max_repomd_bytes",
            "max_signature_bytes",
            "max_snapshot_tar_bytes",
            "max_tar_member_bytes",
            "max_tar_members",
            "max_tar_payload_bytes",
            "max_total_download_bytes",
            "redirect_limit",
        },
        "limits",
    )
    for name, value in limits.items():
        if type(value) is not int or value <= 0:
            raise SnapshotError("limit {} must be a positive integer".format(name))
    require_exact(
        {name: limits[name] for name in TAR_LIMITS},
        TAR_LIMITS,
        "snapshot tar limits",
    )
    if limits["redirect_limit"] > 10 or limits["max_repository_objects"] > 256:
        raise SnapshotError("capture redirect/object limits are not bounded tightly enough")
    if limits["max_metadata_object_bytes"] > limits["max_total_download_bytes"]:
        raise SnapshotError("per-object byte limit exceeds the total download limit")
    if limits["max_metadata_open_bytes"] > limits["max_open_bytes_total"]:
        raise SnapshotError("per-object open-byte limit exceeds the total open-byte limit")
    if limits["max_tar_member_bytes"] < limits["max_metadata_object_bytes"]:
        raise SnapshotError("tar member byte limit is smaller than a metadata object")
    if limits["max_tar_payload_bytes"] < limits["max_total_download_bytes"]:
        raise SnapshotError("tar payload byte limit is smaller than captured downloads")
    if limits["max_snapshot_tar_bytes"] < limits["max_tar_payload_bytes"]:
        raise SnapshotError("snapshot tar byte limit is smaller than its payload limit")
    if limits["max_tar_members"] > 1024:
        raise SnapshotError("snapshot tar member limit is not bounded tightly enough")

    artifact = exact_keys(
        contract["artifact"],
        {
            "deterministic_payload",
            "deterministic_payload_digest",
            "format",
            "retention_days",
        },
        "artifact policy",
    )
    require_exact(artifact["deterministic_payload"], "snapshot.tar", "payload name")
    require_exact(
        artifact["deterministic_payload_digest"],
        "snapshot.tar.sha256",
        "payload digest name",
    )
    require_exact(
        artifact["format"],
        "ustar with sorted regular-file entries, uid/gid/mtime zero, empty owner/group names, and mode 0644",
        "artifact format",
    )
    require_exact(artifact["retention_days"], 30, "artifact retention")

    baselines = contract["diagnostic_baselines"]
    if not isinstance(baselines, list) or len(baselines) != len(REPOSITORIES):
        raise SnapshotError("diagnostic baselines must cover every repository exactly once")
    ids = []
    for row in baselines:
        row = exact_keys(
            row,
            {
                "id",
                "primary_sha256",
                "primary_size",
                "repomd_sha256",
                "signature_sha256",
            },
            "diagnostic baseline",
        )
        ids.append(row["id"])
        for field in ("primary_sha256", "repomd_sha256", "signature_sha256"):
            if not isinstance(row[field], str) or not SHA256.fullmatch(row[field]):
                raise SnapshotError("baseline {} must be a SHA-256".format(field))
        if type(row["primary_size"]) is not int or row["primary_size"] <= 0:
            raise SnapshotError("baseline primary_size must be positive")
    require_exact(ids, [row[0] for row in REPOSITORIES], "baseline repository order")
    require_exact(contract, expected_contract(), "capture contract")


def validate_execution_identity(source_commit, workflow_ref):
    if not isinstance(source_commit, str) or not SOURCE_COMMIT.fullmatch(source_commit):
        raise SnapshotError("source commit must be an exact lowercase 40-hex Git commit")
    if (
        not isinstance(workflow_ref, str)
        or len(workflow_ref) > 512
        or not workflow_ref.startswith(WORKFLOW_REF_PREFIX)
        or any(ord(character) < 0x21 or ord(character) > 0x7E for character in workflow_ref)
    ):
        raise SnapshotError("workflow ref is outside the exact workflow identity policy")
    git_ref = workflow_ref[len(WORKFLOW_REF_PREFIX) :]
    if not git_ref.startswith(("refs/heads/", "refs/tags/")):
        raise SnapshotError("workflow ref must identify one branch or tag")
    ref_name = git_ref.split("/", 2)[-1]
    ref_parts = ref_name.split("/")
    if (
        not ref_name
        or any(not part for part in ref_parts)
        or any(part.startswith(".") for part in ref_parts)
        or any(part.endswith((".", ".lock")) for part in ref_parts)
        or ".." in ref_name
        or "@{" in ref_name
        or any(character in " ~^:?*[\\" for character in ref_name)
        or ref_name == "@"
    ):
        raise SnapshotError("workflow ref has an unsafe Git ref spelling")
    return {"source_commit": source_commit, "workflow_ref": workflow_ref}


def single_git_nul_record(data, label):
    if not isinstance(data, bytes) or not data.endswith(b"\0"):
        raise SnapshotError("{} is not one NUL-terminated Git record".format(label))
    rows = data[:-1].split(b"\0")
    if len(rows) != 1 or not rows[0]:
        raise SnapshotError("{} is not unique".format(label))
    return rows[0]


def git_authority_environment():
    """Return the exact environment allowed at the Git authority boundary."""
    return dict(GIT_AUTHORITY_ENVIRONMENT)


def git_authority_command(repo, arguments):
    """Build one absolute, configuration-bounded read-only Git command."""
    command = [GIT_AUTHORITY_EXECUTABLE, "--no-pager"]
    for value in GIT_AUTHORITY_CONFIG:
        command.extend(["-c", value])
    command.extend(
        [
            "-c",
            "safe.directory={}".format(repo),
            "-C",
            str(repo),
        ]
    )
    command.extend(arguments)
    return command


def repository_tree_entry(repo, source_commit, path, environment):
    stdout, _ = run_checked(
        git_authority_command(
            repo,
            [
                "ls-tree",
                "-z",
                "--full-tree",
                source_commit,
                "--",
                path,
            ],
        ),
        "source-commit tree entry {}".format(path),
        environment,
    )
    row = single_git_nul_record(
        stdout, "source-commit tree entry {}".format(path)
    )
    try:
        metadata, actual_path = row.split(b"\t", 1)
        mode, object_type, object_id = metadata.split(b" ")
        expected_path = path.encode("utf-8", "strict")
    except (UnicodeError, ValueError) as exc:
        raise SnapshotError(
            "source-commit tree entry {} is malformed: {}".format(path, exc)
        )
    if (
        actual_path != expected_path
        or mode not in (b"100644", b"100755")
        or object_type != b"blob"
        or re.fullmatch(br"(?:[0-9a-f]{40}|[0-9a-f]{64})", object_id) is None
    ):
        raise SnapshotError(
            "source-commit tree entry {} is not one regular blob".format(path)
        )
    return mode, object_id


def require_repository_index_entry(repo, path, tree_entry, environment):
    stdout, _ = run_checked(
        git_authority_command(
            repo,
            [
                "ls-files",
                "--stage",
                "-z",
                "--",
                path,
            ],
        ),
        "repository index entry {}".format(path),
        environment,
    )
    row = single_git_nul_record(stdout, "repository index entry {}".format(path))
    try:
        metadata, actual_path = row.split(b"\t", 1)
        mode, object_id, stage = metadata.split(b" ")
        expected_path = path.encode("utf-8", "strict")
    except (UnicodeError, ValueError) as exc:
        raise SnapshotError(
            "repository index entry {} is malformed: {}".format(path, exc)
        )
    if actual_path != expected_path or stage != b"0":
        raise SnapshotError(
            "repository index entry {} is not one exact stage-0 path".format(path)
        )
    require_exact((mode, object_id), tree_entry, "repository index mode/blob {}".format(path))


def verify_repository_input_at_head(repo, source_commit, record, environment):
    tree_entry = repository_tree_entry(
        repo, source_commit, record["path"], environment
    )
    require_repository_index_entry(
        repo, record["path"], tree_entry, environment
    )
    object_spec = "{}:{}".format(source_commit, record["path"])
    object_type, _ = run_checked(
        git_authority_command(
            repo,
            [
                "cat-file",
                "-t",
                object_spec,
            ],
        ),
        "source-commit repository input type {}".format(record["path"]),
        environment,
    )
    require_exact(
        object_type.decode("ascii", "strict").strip(),
        "blob",
        "source-commit repository input type {}".format(record["path"]),
    )
    object_size, _ = run_checked(
        git_authority_command(
            repo,
            [
                "cat-file",
                "-s",
                object_spec,
            ],
        ),
        "source-commit repository input size {}".format(record["path"]),
        environment,
    )
    size_text = object_size.decode("ascii", "strict").strip()
    if not re.fullmatch(r"[0-9]{1,20}", size_text):
        raise SnapshotError("source-commit repository input size is invalid")
    require_exact(
        int(size_text),
        record["size"],
        "source-commit repository input size {}".format(record["path"]),
    )
    blob, _ = run_checked(
        git_authority_command(
            repo,
            [
                "show",
                object_spec,
            ],
        ),
        "source-commit repository input {}".format(record["path"]),
        environment,
    )
    if len(blob) != record["size"] or sha256_bytes(blob) != record["sha256"]:
        raise SnapshotError(
            "repository input differs from source commit: {}".format(
                record["path"]
            )
        )
    worktree_path = regular_repository_file(repo, Path(record["path"]))
    worktree_data = read_regular_bytes(
        worktree_path,
        "checked-out repository input {}".format(record["path"]),
        maximum=MAX_JSON_BYTES,
        expected_mode=(0o644 if tree_entry[0] == b"100644" else 0o755),
    )
    if (
        len(worktree_data) != record["size"]
        or sha256_bytes(worktree_data) != record["sha256"]
    ):
        raise SnapshotError(
            "checked-out repository input differs from source commit: {}".format(
                record["path"]
            )
        )


def require_repository_head(repo, source_commit, input_records):
    environment = git_authority_environment()
    stdout, _ = run_checked(
        git_authority_command(
            repo,
            [
                "rev-parse",
                "--verify",
                "HEAD^{commit}",
            ],
        ),
        "source commit inspection",
        environment,
    )
    actual = stdout.decode("ascii", "strict").strip()
    require_exact(actual, source_commit, "checked-out source commit")
    for record in input_records:
        verify_repository_input_at_head(
            repo, source_commit, record, environment
        )
    for record in input_records:
        verify_repository_input_at_head(
            repo, source_commit, record, environment
        )
    final_head, _ = run_checked(
        git_authority_command(
            repo,
            [
                "rev-parse",
                "--verify",
                "HEAD^{commit}",
            ],
        ),
        "final source commit inspection",
        environment,
    )
    require_exact(
        final_head.decode("ascii", "strict").strip(),
        source_commit,
        "final checked-out source commit",
    )


def check_repository_inputs(repo):
    contract, data = load_contract(repo)
    records = []
    for role in sorted(REQUIRED_INPUTS):
        relative = Path(REQUIRED_INPUTS[role])
        path = regular_repository_file(repo, relative)
        contents = read_regular_bytes(
            path,
            "repository input {}".format(relative.as_posix()),
            maximum=MAX_JSON_BYTES,
        )
        records.append(
            {
                "path": relative.as_posix(),
                "role": role,
                "sha256": sha256_bytes(contents),
                "size": len(contents),
            }
        )
    if sha256_bytes(data) != records[1]["sha256"]:
        raise SnapshotError("internal contract input digest mismatch")
    validate_input_records(records)
    return contract, records


def validate_input_records(input_records):
    if not isinstance(input_records, list):
        raise SnapshotError("repository input records must be an array")
    roles = sorted(REQUIRED_INPUTS)
    if len(input_records) != len(roles):
        raise SnapshotError("repository input records must cover every required input")
    for index, role in enumerate(roles):
        record = exact_keys(
            input_records[index],
            {"path", "role", "sha256", "size"},
            "repository input record",
        )
        require_exact(record["role"], role, "repository input role")
        require_exact(
            record["path"], REQUIRED_INPUTS[role], "repository input path"
        )
        if not isinstance(record["sha256"], str) or not SHA256.fullmatch(
            record["sha256"]
        ):
            raise SnapshotError("repository input digest must be a lowercase SHA-256")
        if (
            type(record["size"]) is not int
            or record["size"] <= 0
            or record["size"] > MAX_JSON_BYTES
        ):
            raise SnapshotError("repository input size is outside its byte limit")


def validate_https_url(url, allowed_hosts, label, required_prefix=None):
    if (
        not isinstance(url, str)
        or not url
        or any(ord(character) < 0x21 or ord(character) > 0x7E for character in url)
    ):
        raise SnapshotError("{} must be a non-empty HTTPS URL".format(label))
    parsed = urllib.parse.urlsplit(url)
    if (
        parsed.scheme != "https"
        or parsed.hostname not in allowed_hosts
        or parsed.netloc != parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.port is not None
        or not parsed.path.startswith("/")
        or "%" in parsed.path
        or "\\" in parsed.path
        or "//" in parsed.path
        or any(part in (".", "..") for part in parsed.path.split("/"))
        or parsed.query
        or parsed.fragment
        or urllib.parse.urlunsplit(parsed) != url
    ):
        raise SnapshotError("{} is outside the locked HTTPS policy".format(label))
    if required_prefix is not None and not url.startswith(required_prefix):
        raise SnapshotError("{} escaped its repository base URL".format(label))
    return url


class BoundedRedirectHandler(urllib.request.HTTPRedirectHandler):
    def __init__(self, allowed_hosts, redirect_limit, required_prefix=None):
        urllib.request.HTTPRedirectHandler.__init__(self)
        self.allowed_hosts = allowed_hosts
        self.redirect_limit = redirect_limit
        self.required_prefix = required_prefix
        self.redirect_count = 0

    def redirect_request(self, request, fp, code, msg, headers, newurl):
        self.redirect_count += 1
        if self.redirect_count > self.redirect_limit:
            raise SnapshotError("download exceeded the redirect limit")
        validate_https_url(
            newurl,
            self.allowed_hosts,
            "redirect URL",
            required_prefix=self.required_prefix,
        )
        return urllib.request.HTTPRedirectHandler.redirect_request(
            self, request, fp, code, msg, headers, newurl
        )


def download_to_path(url, destination, maximum, contract, required_prefix=None):
    allowed_hosts = contract["network"]["allowed_hosts"]
    validate_https_url(url, allowed_hosts, "download URL", required_prefix)
    handler = BoundedRedirectHandler(
        allowed_hosts,
        contract["limits"]["redirect_limit"],
        required_prefix=required_prefix,
    )
    opener = urllib.request.build_opener(handler)
    request = urllib.request.Request(
        url,
        headers={
            "Accept-Encoding": "identity",
            "User-Agent": "mckernel-rocky-snapshot-capture-v2",
        },
    )
    try:
        response = opener.open(
            request, timeout=contract["limits"]["download_timeout_seconds"]
        )
    except (OSError, urllib.error.URLError, SnapshotError) as exc:
        raise SnapshotError("download failed for {}: {}".format(url, exc))
    try:
        status = response.getcode()
        if status != 200:
            raise SnapshotError("download returned HTTP {} for {}".format(status, url))
        final_url = response.geturl()
        validate_https_url(
            final_url, allowed_hosts, "final download URL", required_prefix
        )
        encoding = response.headers.get("Content-Encoding")
        if encoding not in (None, "", "identity"):
            raise SnapshotError("download used a forbidden content encoding")
        content_length = response.headers.get("Content-Length")
        if content_length is not None:
            if not re.fullmatch(r"[0-9]{1,20}", content_length):
                raise SnapshotError("download Content-Length is not a bounded integer")
            announced = int(content_length)
            if announced < 0 or announced > maximum:
                raise SnapshotError("download Content-Length exceeds its byte limit")
        digest = hashlib.sha256()
        size = 0
        descriptor = open_regular_create(destination, "download destination")
        try:
            with os.fdopen(descriptor, "wb") as output:
                descriptor = -1
                while True:
                    chunk = response.read(1024 * 1024)
                    if not chunk:
                        break
                    size += len(chunk)
                    if size > maximum:
                        raise SnapshotError("download exceeded its byte limit")
                    digest.update(chunk)
                    output.write(chunk)
        except OSError as exc:
            raise SnapshotError("cannot write download {}: {}".format(destination, exc))
        finally:
            if descriptor >= 0:
                os.close(descriptor)
        if content_length is not None and size != announced:
            raise SnapshotError("download length differs from Content-Length")
        return {
            "final_url": final_url,
            "redirect_count": handler.redirect_count,
            "sha256": digest.hexdigest(),
            "size": size,
            "url": url,
        }
    finally:
        response.close()


def run_checked(command, label, environment=None):
    try:
        completed = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            env=environment,
        )
    except OSError as exc:
        raise SnapshotError("cannot run {}: {}".format(label, exc))
    if completed.returncode != 0:
        stderr = completed.stderr.decode("utf-8", "replace").strip()
        raise SnapshotError(
            "{} failed with status {}: {}".format(
                label, completed.returncode, stderr[-800:]
            )
        )
    return completed.stdout, completed.stderr


def verify_key_fingerprint_bytes(key_data, expected_fingerprint):
    with tempfile.TemporaryDirectory(prefix="mck-rocky-snapshot-key.") as home_text:
        home = Path(home_text)
        os.chmod(str(home), 0o700)
        key_path = home / "release-key.asc"
        write_regular_exclusive(key_path, key_data, "private release-key copy")
        environment = os.environ.copy()
        environment.update({"GNUPGHOME": str(home), "LC_ALL": "C"})
        stdout, _ = run_checked(
            [
                "gpg",
                "--batch",
                "--no-options",
                "--homedir",
                str(home),
                "--with-colons",
                "--show-keys",
                str(key_path),
            ],
            "release-key fingerprint inspection",
            environment,
        )
    primary_fingerprints = []
    waiting_for_primary = False
    for raw_line in stdout.decode("utf-8", "replace").splitlines():
        fields = raw_line.split(":")
        if fields[0] == "pub":
            waiting_for_primary = True
        elif fields[0] == "fpr" and waiting_for_primary:
            primary_fingerprints.append(fields[9].upper())
            waiting_for_primary = False
    if primary_fingerprints != [expected_fingerprint]:
        raise SnapshotError(
            "release key primary fingerprints changed: {}".format(primary_fingerprints)
        )
    return expected_fingerprint


def verify_key_fingerprint(key_path, expected_fingerprint):
    key_data = read_regular_bytes(
        key_path, "release key", maximum=LIMITS["max_key_bytes"]
    )
    return verify_key_fingerprint_bytes(key_data, expected_fingerprint)


def verify_detached_signature_bytes(
    key_data, signature_data, signed_data, fingerprint
):
    with tempfile.TemporaryDirectory(prefix="mck-rocky-snapshot-gpg.") as home_text:
        home = Path(home_text)
        os.chmod(str(home), 0o700)
        environment = os.environ.copy()
        environment.update({"GNUPGHOME": str(home), "LC_ALL": "C"})
        key_path = home / "release-key.asc"
        signature_path = home / "repomd.xml.asc"
        signed_path = home / "repomd.xml"
        write_regular_exclusive(key_path, key_data, "private release-key copy")
        write_regular_exclusive(
            signature_path, signature_data, "private signature copy"
        )
        write_regular_exclusive(signed_path, signed_data, "private signed-data copy")
        keyring = home / "release-key.gpg"
        run_checked(
            [
                "gpg",
                "--batch",
                "--no-options",
                "--no-autostart",
                "--homedir",
                str(home),
                "--dearmor",
                "--output",
                str(keyring),
                str(key_path),
            ],
            "release-key dearmor",
            environment,
        )
        stdout, _ = run_checked(
            [
                "gpgv",
                "--status-fd",
                "1",
                "--keyring",
                str(keyring),
                str(signature_path),
                str(signed_path),
            ],
            "repomd detached-signature verification",
            environment,
        )
    valid = []
    for line in stdout.decode("utf-8", "replace").splitlines():
        if line.startswith("[GNUPG:] VALIDSIG "):
            fields = line.split()
            if len(fields) != 12 or fields[0:2] != ["[GNUPG:]", "VALIDSIG"]:
                raise SnapshotError("gpgv emitted a malformed VALIDSIG status")
            valid.append(
                {
                    "hash_algorithm_id": int(fields[9]),
                    "primary_fingerprint": fields[-1].upper(),
                    "public_key_algorithm_id": int(fields[8]),
                    "signature_fingerprint": fields[2].upper(),
                    "signature_timestamp": int(fields[4]),
                    "status": "verified",
                }
            )
    if len(valid) != 1 or valid[0]["primary_fingerprint"] != fingerprint:
        raise SnapshotError("repomd signature is not bound to the pinned primary key")
    if (
        valid[0]["public_key_algorithm_id"] != 1
        or valid[0]["hash_algorithm_id"] != 8
    ):
        raise SnapshotError("repomd signature must use RSA with SHA-256")
    return valid[0]


def verify_detached_signature(key_path, signature_path, signed_path, fingerprint):
    key_data = read_regular_bytes(
        key_path, "release key", maximum=LIMITS["max_key_bytes"]
    )
    signature_data = read_regular_bytes(
        signature_path,
        "repomd detached signature",
        maximum=LIMITS["max_signature_bytes"],
    )
    signed_data = read_regular_bytes(
        signed_path, "signed repomd.xml", maximum=LIMITS["max_repomd_bytes"]
    )
    return verify_detached_signature_bytes(
        key_data, signature_data, signed_data, fingerprint
    )


def integer_text(element, label, required=True):
    if element is None:
        if required:
            raise SnapshotError("repomd entry is missing {}".format(label))
        return None
    text = element.text
    if (
        element.attrib
        or len(element)
        or not isinstance(text, str)
        or not re.fullmatch(r"[0-9]{1,20}", text)
    ):
        raise SnapshotError(
            "repomd {} is not a bounded nonnegative integer".format(label)
        )
    return int(text)


def checksum_element(element, label, required=True):
    if element is None:
        if required:
            raise SnapshotError("repomd entry is missing {}".format(label))
        return None
    if element.attrib != {"type": "sha256"} or len(element):
        raise SnapshotError("repomd {} must use SHA-256 only".format(label))
    value = element.text
    if not isinstance(value, str) or not SHA256.fullmatch(value):
        raise SnapshotError("repomd {} is not a lowercase SHA-256".format(label))
    return value


def strict_utf8_xml_text(data, label):
    if type(data) is not bytes:
        raise SnapshotError("{} must be supplied as exact bytes".format(label))
    if data.startswith((b"\xef\xbb\xbf", b"\xff\xfe", b"\xfe\xff", b"\x00\x00\xfe\xff")):
        raise SnapshotError("{} must not contain a byte-order mark".format(label))
    try:
        text = data.decode("utf-8", "strict")
    except UnicodeDecodeError as exc:
        raise SnapshotError("{} is not strict UTF-8: {}".format(label, exc))
    if "\x00" in text or text.startswith("\ufeff"):
        raise SnapshotError("{} is not canonical UTF-8 XML".format(label))
    declaration = re.match(r"\A<\?xml(?P<body>[ \t\r\n].*?)\?>", text, re.DOTALL)
    if declaration is not None:
        encodings = re.findall(
            r"(?:^|[ \t\r\n])encoding[ \t\r\n]*=[ \t\r\n]*(['\"])([^'\"]+)\1",
            declaration.group("body"),
            re.IGNORECASE,
        )
        if len(encodings) > 1 or (
            encodings and encodings[0][1].upper() != "UTF-8"
        ):
            raise SnapshotError("{} must declare UTF-8 only".format(label))
    if re.search(
        r"<![ \t\r\n]*(?:DOCTYPE|ENTITY)\b", text, re.IGNORECASE
    ):
        raise SnapshotError("{} DTDs and entity declarations are forbidden".format(label))
    return text


def parse_repomd(data, maximum_objects):
    text = strict_utf8_xml_text(data, "repomd.xml")
    try:
        root = ET.fromstring(text)
    except ET.ParseError as exc:
        raise SnapshotError("cannot parse repomd.xml: {}".format(exc))
    if root.tag != "{{{}}}repomd".format(REPOMD_NS):
        raise SnapshotError("repomd.xml has an unexpected root element")
    if root.attrib:
        raise SnapshotError("repomd.xml root attributes changed")
    namespace = {"repo": REPOMD_NS}
    allowed_root_children = {"revision", "tags", "data"}
    root_child_counts = {}
    for child in root:
        prefix = "{{{}}}".format(REPOMD_NS)
        if not child.tag.startswith(prefix):
            raise SnapshotError("repomd.xml contains a foreign-namespace child")
        name = child.tag[len(prefix) :]
        if name not in allowed_root_children:
            raise SnapshotError("repomd.xml contains an unexpected child")
        root_child_counts[name] = root_child_counts.get(name, 0) + 1
    if root_child_counts.get("revision") != 1 or root_child_counts.get("tags", 0) > 1:
        raise SnapshotError("repomd.xml revision/tags multiplicity changed")
    revision = root.find("repo:revision", namespace)
    if revision is None or revision.text != "10.2" or revision.attrib:
        raise SnapshotError("repomd revision must be exactly 10.2")
    elements = root.findall("repo:data", namespace)
    if not elements or len(elements) > maximum_objects:
        raise SnapshotError("repomd metadata-object count is outside the contract")
    rows = []
    seen_types = set()
    seen_hrefs = set()
    for element in elements:
        if set(element.attrib) != {"type"}:
            raise SnapshotError("repomd data entry attributes changed")
        data_type = element.attrib["type"]
        if not re.fullmatch(r"[a-z0-9_+-]+", data_type) or data_type in seen_types:
            raise SnapshotError("repomd data type is invalid or duplicated")
        seen_types.add(data_type)
        allowed_children = {
            "checksum",
            "database_version",
            "location",
            "open-checksum",
            "open-size",
            "size",
            "timestamp",
        }
        child_counts = {}
        prefix = "{{{}}}".format(REPOMD_NS)
        for child in element:
            if not child.tag.startswith(prefix):
                raise SnapshotError("repomd data contains a foreign-namespace child")
            child_name = child.tag[len(prefix) :]
            if child_name not in allowed_children:
                raise SnapshotError("repomd data contains an unexpected child")
            child_counts[child_name] = child_counts.get(child_name, 0) + 1
        for child_name in ("checksum", "location", "size", "timestamp"):
            if child_counts.get(child_name) != 1:
                raise SnapshotError(
                    "repomd data {} multiplicity changed".format(child_name)
                )
        for child_name in ("database_version", "open-checksum", "open-size"):
            if child_counts.get(child_name, 0) > 1:
                raise SnapshotError(
                    "repomd data {} multiplicity changed".format(child_name)
                )
        location = element.find("repo:location", namespace)
        if (
            location is None
            or set(location.attrib) != {"href"}
            or len(location)
            or (location.text is not None and location.text.strip())
        ):
            raise SnapshotError("repomd location must contain only href")
        href = normalized_relative_path(location.attrib["href"], "repomd href").as_posix()
        if not href.startswith("repodata/") or href in seen_hrefs:
            raise SnapshotError("repomd href is outside repodata or duplicated")
        seen_hrefs.add(href)
        compressed_sha256 = checksum_element(
            element.find("repo:checksum", namespace), "checksum"
        )
        compressed_size = integer_text(element.find("repo:size", namespace), "size")
        integer_text(element.find("repo:timestamp", namespace), "timestamp")
        integer_text(
            element.find("repo:database_version", namespace),
            "database_version",
            required=False,
        )
        open_checksum_element = element.find("repo:open-checksum", namespace)
        open_size_element = element.find("repo:open-size", namespace)
        if (open_checksum_element is None) != (open_size_element is None):
            raise SnapshotError("repomd open checksum and size must appear together")
        open_sha256 = checksum_element(
            open_checksum_element, "open-checksum", required=False
        )
        open_size = integer_text(open_size_element, "open-size", required=False)
        compression = compression_for_href(href)
        if compression != "none" and (open_sha256 is None or open_size is None):
            raise SnapshotError("compressed repomd objects require open hash and size")
        rows.append(
            {
                "compressed_sha256": compressed_sha256,
                "compressed_size": compressed_size,
                "compression": compression,
                "href": href,
                "open_sha256": open_sha256,
                "open_size": open_size,
                "type": data_type,
            }
        )
    if "primary" not in seen_types:
        raise SnapshotError("repomd does not name primary metadata")
    return {"objects": rows, "revision": "10.2"}


def compression_for_href(href):
    if href.endswith(".gz"):
        return "gzip"
    if href.endswith(".bz2"):
        return "bzip2"
    if href.endswith(".xz"):
        return "xz"
    if href.endswith((".xml", ".sqlite")):
        return "none"
    raise SnapshotError("unsupported or ambiguous metadata compression: {}".format(href))


def open_metadata_stream(source, compression):
    if compression == "gzip":
        return gzip.GzipFile(fileobj=source, mode="rb")
    if compression == "bzip2":
        return bz2.BZ2File(source, "rb")
    if compression == "xz":
        return lzma.LZMAFile(source, "rb")
    if compression == "none":
        return source
    raise SnapshotError("unknown metadata compression: {}".format(compression))


def verify_metadata_object(path, row, per_open_limit, total_open_counter):
    descriptor = open_regular_read(path, "metadata object")
    try:
        before = regular_identity(os.fstat(descriptor))
        with os.fdopen(descriptor, "rb") as source:
            descriptor = -1
            compressed_digest = hashlib.sha256()
            compressed_size = 0
            while True:
                chunk = source.read(1024 * 1024)
                if not chunk:
                    break
                compressed_size += len(chunk)
                compressed_digest.update(chunk)
            if (
                compressed_size != row["compressed_size"]
                or compressed_digest.hexdigest() != row["compressed_sha256"]
            ):
                raise SnapshotError(
                    "metadata object compressed bytes differ from repomd.xml"
                )
            source.seek(0)
            stream = open_metadata_stream(source, row["compression"])
            open_digest = hashlib.sha256()
            open_size = 0
            try:
                while True:
                    chunk = stream.read(1024 * 1024)
                    if not chunk:
                        break
                    open_size += len(chunk)
                    total_open_counter[0] += len(chunk)
                    if open_size > per_open_limit:
                        raise SnapshotError(
                            "opened metadata object exceeds its byte limit"
                        )
                    if total_open_counter[0] > total_open_counter[1]:
                        raise SnapshotError(
                            "opened metadata exceeds the total byte limit"
                        )
                    open_digest.update(chunk)
            finally:
                if stream is not source:
                    stream.close()
            after = regular_identity(os.fstat(source.fileno()))
    except SnapshotError:
        raise
    except (OSError, EOFError, ValueError, lzma.LZMAError) as exc:
        raise SnapshotError("cannot decompress metadata object: {}".format(exc))
    finally:
        if descriptor >= 0:
            os.close(descriptor)
    if before != after or compressed_size != after[4]:
        raise SnapshotError("metadata object changed while it was verified")
    opened_sha256 = open_digest.hexdigest()
    if row["open_size"] is not None:
        if open_size != row["open_size"] or opened_sha256 != row["open_sha256"]:
            raise SnapshotError("metadata object open bytes differ from repomd.xml")
        declared = True
    else:
        if row["compression"] != "none":
            raise SnapshotError("compressed metadata lacks an open-byte binding")
        declared = False
    result = dict(row)
    result.update(
        {
            "open_checksum_declared": declared,
            "verified_open_sha256": opened_sha256,
            "verified_open_size": open_size,
        }
    )
    return result


def safe_write_json(path, value):
    data = canonical_json_bytes(value)
    requested = absolute_path(path, "JSON output")
    make_directories_nofollow(requested.parent, "JSON output parent")
    parent_descriptor = open_directory_fd(
        requested.parent, "JSON output parent"
    )
    temporary_name = ".{}.tmp.{}.{}".format(
        requested.name, os.getpid(), secrets.token_hex(8)
    )
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW
    descriptor = -1
    try:
        descriptor = os.open(
            temporary_name, flags, 0o600, dir_fd=parent_descriptor
        )
        write_all(descriptor, data, "JSON output")
        os.fchmod(descriptor, 0o600)
        os.close(descriptor)
        descriptor = -1
        os.replace(
            temporary_name,
            requested.name,
            src_dir_fd=parent_descriptor,
            dst_dir_fd=parent_descriptor,
        )
    except OSError as exc:
        raise SnapshotError("cannot write {}: {}".format(path, exc))
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        try:
            os.unlink(temporary_name, dir_fd=parent_descriptor)
        except FileNotFoundError:
            pass
        except OSError:
            pass
        os.close(parent_descriptor)


def diagnostics_claims():
    return {
        "accepted_checkpoint": False,
        "credit_eligible": False,
        "durable_archive": False,
        "tracker_credit": False,
    }


def write_capture_diagnostics(diagnostics_dir, state, error=None):
    if diagnostics_dir is None:
        return
    make_directories_nofollow(diagnostics_dir, "capture diagnostics directory")
    value = {
        "capture_id": CAPTURE_ID,
        "claims": diagnostics_claims(),
        "error": error,
        "observations": state,
        "schema_version": 1,
        "status": "failed" if error is not None else "bounded-capture-complete",
    }
    safe_write_json(diagnostics_dir / "drift-report.json", value)


def repository_archive_path(repository_id, href):
    href_path = normalized_relative_path(href, "repository object href")
    return Path("repositories") / repository_id / Path(*href_path.parts)


def build_repository_record(
    tree, repository, contract, total_open_counter, key_data
):
    repository_id = repository["id"]
    root = tree / "repositories" / repository_id
    repomd_path = root / "repodata" / "repomd.xml"
    signature_path = root / "repodata" / "repomd.xml.asc"
    repomd_data = read_regular_bytes(
        repomd_path,
        "captured repomd.xml",
        maximum=contract["limits"]["max_repomd_bytes"],
    )
    signature_data = read_regular_bytes(
        signature_path,
        "captured repomd signature",
        maximum=contract["limits"]["max_signature_bytes"],
    )
    repomd_size = len(repomd_data)
    repomd_sha256 = sha256_bytes(repomd_data)
    signature_size = len(signature_data)
    signature_sha256 = sha256_bytes(signature_data)
    parsed = parse_repomd(repomd_data, contract["limits"]["max_repository_objects"])
    signature = verify_detached_signature_bytes(
        key_data, signature_data, repomd_data, RELEASE_FINGERPRINT
    )
    objects = []
    for row in parsed["objects"]:
        path = tree / repository_archive_path(repository_id, row["href"])
        objects.append(
            verify_metadata_object(
                path,
                row,
                contract["limits"]["max_metadata_open_bytes"],
                total_open_counter,
            )
        )
    signature_record_path = root / "repodata" / "signature.json"
    signature_record = strict_json_bytes(
        read_regular_bytes(
            signature_record_path,
            "captured signature record",
            maximum=MAX_JSON_BYTES,
        ),
        signature_record_path.as_posix(),
    )
    require_exact(signature_record, signature, "captured signature record")
    primary = [row for row in objects if row["type"] == "primary"][0]
    return {
        "base_url": repository["base_url"],
        "id": repository_id,
        "kind": repository["kind"],
        "metadata_object_count": len(objects),
        "objects": objects,
        "primary": {
            "href": primary["href"],
            "sha256": primary["compressed_sha256"],
            "size": primary["compressed_size"],
        },
        "repomd": {
            "revision": parsed["revision"],
            "sha256": repomd_sha256,
            "size": repomd_size,
        },
        "signature": dict(
            signature,
            sha256=signature_sha256,
            size=signature_size,
        ),
    }


def expected_payload_paths(input_records, repositories):
    paths = {
        "inputs/{}".format(record["path"]) for record in input_records
    }
    paths.add("release-key/RPM-GPG-KEY-Rocky-10")
    for repository in repositories:
        root = "repositories/{}/".format(repository["id"])
        paths.update(
            {
                root + "repodata/repomd.xml",
                root + "repodata/repomd.xml.asc",
                root + "repodata/signature.json",
            }
        )
        paths.update(root + row["href"] for row in repository["objects"])
    return sorted(paths)


def payload_file_records(tree, expected_paths):
    records = []
    for path in sorted(tree.rglob("*")):
        if path.is_symlink():
            raise SnapshotError("snapshot tree contains a symlink payload entry")
        if path.is_dir():
            continue
        if not path.is_file():
            raise SnapshotError("snapshot tree contains a non-regular payload entry")
        relative = path.relative_to(tree).as_posix()
        if relative == "capture-manifest.json":
            continue
        normalized_relative_path(relative, "payload path")
        size, digest = sha256_file(path)
        records.append({"path": relative, "sha256": digest, "size": size})
    actual_paths = [record["path"] for record in records]
    require_exact(actual_paths, expected_paths, "snapshot payload path closure")
    return records


def build_capture_manifest(tree, repo, contract, input_records, execution_identity):
    execution_identity = validate_execution_identity(
        execution_identity.get("source_commit")
        if isinstance(execution_identity, dict)
        else None,
        execution_identity.get("workflow_ref")
        if isinstance(execution_identity, dict)
        else None,
    )
    contract_copy = tree / "inputs" / CONTRACT_PATH
    copied_contract = read_regular_bytes(
        contract_copy, "archived contract input", maximum=MAX_JSON_BYTES
    )
    _, repository_contract_data = load_contract(repo)
    if copied_contract != repository_contract_data:
        raise SnapshotError("archived contract differs from the repository input")
    for record in input_records:
        archived = tree / "inputs" / Path(record["path"])
        archived_data = read_regular_bytes(
            archived,
            "archived repository input {}".format(record["path"]),
            maximum=MAX_JSON_BYTES,
        )
        if (
            len(archived_data) != record["size"]
            or sha256_bytes(archived_data) != record["sha256"]
        ):
            raise SnapshotError("archived repository input differs: {}".format(record["path"]))

    key_path = tree / "release-key" / "RPM-GPG-KEY-Rocky-10"
    key_data = read_regular_bytes(
        key_path,
        "archived release key",
        maximum=contract["limits"]["max_key_bytes"],
    )
    key_size = len(key_data)
    key_sha256 = sha256_bytes(key_data)
    require_exact(key_size, contract["release_key"]["size"], "release key size")
    require_exact(key_sha256, contract["release_key"]["sha256"], "release key SHA-256")
    fingerprint = verify_key_fingerprint_bytes(
        key_data, contract["release_key"]["fingerprint"]
    )

    total_open_counter = [0, contract["limits"]["max_open_bytes_total"]]
    repositories = []
    for repository in contract["repositories"]:
        repositories.append(
            build_repository_record(
                tree, repository, contract, total_open_counter, key_data
            )
        )
    identity_rows = []
    for row in repositories:
        identity_rows.append(
            {
                "id": row["id"],
                "object_bindings": [
                    {
                        "href": item["href"],
                        "sha256": item["compressed_sha256"],
                        "size": item["compressed_size"],
                    }
                    for item in row["objects"]
                ],
                "repomd_sha256": row["repomd"]["sha256"],
                "signature_sha256": row["signature"]["sha256"],
            }
        )
    snapshot_identity = sha256_bytes(canonical_json_bytes(identity_rows))
    expected_paths = expected_payload_paths(input_records, repositories)
    return {
        "capture_id": CAPTURE_ID,
        "capture_results": {
            "all_declared_open_checksums_verified": True,
            "all_repomd_objects_archived": True,
            "all_repomd_signatures_verified": True,
            "release_key_verified": True,
        },
        "claims": FALSE_CLAIMS,
        "execution_identity": execution_identity,
        "payload_files": payload_file_records(tree, expected_paths),
        "release_key": {
            "fingerprint": fingerprint,
            "path": "release-key/RPM-GPG-KEY-Rocky-10",
            "sha256": key_sha256,
            "size": key_size,
        },
        "repositories": repositories,
        "repository_inputs": input_records,
        "schema_version": 2,
        "snapshot_identity": snapshot_identity,
        "target": TARGET,
    }


def drift_rows(contract, repository_records):
    baselines = {row["id"]: row for row in contract["diagnostic_baselines"]}
    result = []
    for current in repository_records:
        baseline = baselines[current["id"]]
        current_values = {
            "primary_sha256": current["primary"]["sha256"],
            "primary_size": current["primary"]["size"],
            "repomd_sha256": current["repomd"]["sha256"],
            "signature_sha256": current["signature"]["sha256"],
        }
        expected_values = {key: baseline[key] for key in sorted(current_values)}
        changed_fields = [
            key for key in sorted(current_values) if current_values[key] != expected_values[key]
        ]
        result.append(
            {
                "baseline": expected_values,
                "changed_fields": changed_fields,
                "current": current_values,
                "drift_observed": bool(changed_fields),
                "id": current["id"],
            }
        )
    return result


def copy_repository_inputs(repo, tree, input_records):
    for record in input_records:
        source = regular_repository_file(repo, Path(record["path"]))
        destination = tree / "inputs" / Path(record["path"])
        data = read_regular_bytes(
            source,
            "repository input {}".format(record["path"]),
            maximum=MAX_JSON_BYTES,
        )
        if len(data) != record["size"] or sha256_bytes(data) != record["sha256"]:
            raise SnapshotError(
                "repository input changed before capture: {}".format(record["path"])
            )
        write_regular_exclusive(
            destination,
            data,
            "archived repository input {}".format(record["path"]),
        )


def create_deterministic_tar(tree, destination, limits=None):
    names = []
    for path in sorted(tree.rglob("*")):
        if path.is_symlink():
            raise SnapshotError("snapshot tree contains a symlink")
        if path.is_dir():
            continue
        descriptor = open_regular_read(path, "snapshot tar source")
        os.close(descriptor)
        names.append(path.relative_to(tree).as_posix())
    names.sort()
    total_size = 0
    if limits is not None and len(names) > limits["max_tar_members"]:
        raise SnapshotError("snapshot tar member count exceeds its limit")
    output_descriptor = open_regular_create(destination, "snapshot tar output")
    try:
        with os.fdopen(output_descriptor, "wb") as output:
            output_descriptor = -1
            with tarfile.open(
                fileobj=output, mode="w", format=tarfile.USTAR_FORMAT
            ) as archive:
                for name in names:
                    path = tree / Path(name)
                    source_descriptor = open_regular_read(
                        path, "snapshot tar source {}".format(name)
                    )
                    try:
                        before = regular_identity(os.fstat(source_descriptor))
                        size = before[4]
                        total_size += size
                        if (
                            limits is not None
                            and size > limits["max_tar_member_bytes"]
                        ):
                            raise SnapshotError(
                                "snapshot tar member exceeds its byte limit"
                            )
                        if (
                            limits is not None
                            and total_size > limits["max_tar_payload_bytes"]
                        ):
                            raise SnapshotError(
                                "snapshot tar payload exceeds its byte limit"
                            )
                        info = tarfile.TarInfo(name=name)
                        info.size = size
                        info.mode = 0o644
                        info.uid = 0
                        info.gid = 0
                        info.mtime = 0
                        info.uname = ""
                        info.gname = ""
                        with os.fdopen(source_descriptor, "rb") as source:
                            source_descriptor = -1
                            archive.addfile(info, source)
                            after = regular_identity(os.fstat(source.fileno()))
                        if before != after:
                            raise SnapshotError(
                                "snapshot tar source changed while it was read"
                            )
                    finally:
                        if source_descriptor >= 0:
                            os.close(source_descriptor)
    finally:
        if output_descriptor >= 0:
            os.close(output_descriptor)
    if limits is not None:
        artifact_size, _ = sha256_file(destination)
        if artifact_size > limits["max_snapshot_tar_bytes"]:
            raise SnapshotError("snapshot tar byte stream exceeds its limit")


def independent_stage_directory():
    return tempfile.TemporaryDirectory(
        prefix="mck-rocky-snapshot-stage.", dir="/tmp"
    )


def require_private_stage_directory(path):
    try:
        metadata = os.lstat(str(path))
    except OSError as exc:
        raise SnapshotError("cannot inspect independent capture stage: {}".format(exc))
    if (
        not stat.S_ISDIR(metadata.st_mode)
        or stat.S_ISLNK(metadata.st_mode)
        or stat.S_IMODE(metadata.st_mode) != 0o700
        or metadata.st_uid != os.geteuid()
    ):
        raise SnapshotError("independent capture stage identity is unsafe")


def rename_noreplace(
    source_directory, source_name, destination_directory, destination_name
):
    try:
        renameat2 = ctypes.CDLL(None, use_errno=True).renameat2
    except AttributeError:
        raise SnapshotError("atomic no-replace directory publication is unavailable")
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
        if error == errno.EEXIST:
            raise SnapshotError("capture output leaf appeared before publication")
        raise SnapshotError(
            "cannot atomically publish capture output: {}".format(
                os.strerror(error)
            )
        )


def copy_regular_file_between_directories(
    source_directory, destination_directory, name
):
    flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK
    if hasattr(os, "O_BINARY"):
        flags |= os.O_BINARY
    source_descriptor = -1
    destination_descriptor = -1
    try:
        source_descriptor = os.open(name, flags, dir_fd=source_directory)
        before = regular_identity(os.fstat(source_descriptor))
        if not stat.S_ISREG(before[2]):
            raise SnapshotError("capture publication source must be a regular file")
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
            write_all(destination_descriptor, chunk, "capture publication file")
        os.fchmod(destination_descriptor, 0o600)
        os.fsync(destination_descriptor)
        after = regular_identity(os.fstat(source_descriptor))
        published = os.fstat(destination_descriptor)
        if before != after or copied != before[4] or published.st_size != copied:
            raise SnapshotError("capture publication source changed while copied")
    except OSError as exc:
        raise SnapshotError("cannot copy capture publication file: {}".format(exc))
    finally:
        if source_descriptor >= 0:
            os.close(source_descriptor)
        if destination_descriptor >= 0:
            os.close(destination_descriptor)


def publish_capture_files(
    artifact,
    checksum,
    output_dir,
    output_parent_descriptor,
    output_parent_identity,
):
    artifact = absolute_path(artifact, "snapshot publication artifact")
    checksum = absolute_path(checksum, "snapshot publication checksum")
    if (
        artifact.name != "snapshot.tar"
        or checksum.name != "snapshot.tar.sha256"
        or artifact.parent != checksum.parent
    ):
        raise SnapshotError(
            "snapshot artifact and checksum must share one exact source parent"
        )
    source_parent_descriptor = open_directory_fd(
        artifact.parent, "snapshot publication source parent"
    )
    hidden_name = ".{}.publish.{}.{}".format(
        output_dir.name, os.getpid(), secrets.token_hex(8)
    )
    hidden_descriptor = -1
    published = False
    try:
        source_names = sorted(os.listdir(source_parent_descriptor))
        require_exact(
            source_names,
            ["snapshot.tar", "snapshot.tar.sha256"],
            "snapshot publication source closure",
        )
        require_stable_directory_path(
            output_dir.parent,
            output_parent_descriptor,
            output_parent_identity,
            "capture output parent before publication",
        )
        try:
            os.mkdir(hidden_name, 0o700, dir_fd=output_parent_descriptor)
            hidden_descriptor = os.open(
                hidden_name,
                os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                dir_fd=output_parent_descriptor,
            )
        except OSError as exc:
            raise SnapshotError(
                "cannot create private capture publication directory: {}".format(exc)
            )
        for name in ("snapshot.tar", "snapshot.tar.sha256"):
            copy_regular_file_between_directories(
                source_parent_descriptor, hidden_descriptor, name
            )
        os.fsync(hidden_descriptor)
        require_stable_directory_path(
            output_dir.parent,
            output_parent_descriptor,
            output_parent_identity,
            "capture output parent at publication",
        )
        hidden_identity = directory_identity(os.fstat(hidden_descriptor))
        rename_noreplace(
            output_parent_descriptor,
            hidden_name,
            output_parent_descriptor,
            output_dir.name,
        )
        published = True
        final_descriptor = os.open(
            output_dir.name,
            os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
            dir_fd=output_parent_descriptor,
        )
        try:
            require_exact(
                directory_identity(os.fstat(final_descriptor)),
                hidden_identity,
                "published capture directory identity",
            )
        finally:
            os.close(final_descriptor)
        os.fsync(output_parent_descriptor)
        require_stable_directory_path(
            output_dir.parent,
            output_parent_descriptor,
            output_parent_identity,
            "capture output parent after publication",
        )
    except OSError as exc:
        raise SnapshotError("capture publication failed: {}".format(exc))
    finally:
        os.close(source_parent_descriptor)
        if hidden_descriptor >= 0:
            if not published:
                for name in ("snapshot.tar", "snapshot.tar.sha256"):
                    try:
                        os.unlink(name, dir_fd=hidden_descriptor)
                    except FileNotFoundError:
                        pass
                try:
                    os.fsync(hidden_descriptor)
                except OSError:
                    pass
            os.close(hidden_descriptor)
        if not published:
            try:
                os.rmdir(hidden_name, dir_fd=output_parent_descriptor)
            except FileNotFoundError:
                pass
            except OSError:
                pass


def remaining_download_limit(contract, total_downloaded, object_limit):
    remaining = contract["limits"]["max_total_download_bytes"] - total_downloaded
    if remaining <= 0:
        raise SnapshotError("capture exhausted its total download byte limit")
    return min(object_limit, remaining)


def capture_snapshot(
    repo, output_dir, diagnostics_dir, contract, input_records, execution_identity
):
    validate_contract(contract)
    validate_input_records(input_records)
    execution_identity = validate_execution_identity(
        execution_identity.get("source_commit")
        if isinstance(execution_identity, dict)
        else None,
        execution_identity.get("workflow_ref")
        if isinstance(execution_identity, dict)
        else None,
    )
    require_repository_head(
        repo, execution_identity["source_commit"], input_records
    )
    (
        output_dir,
        diagnostics_dir,
        output_parent_descriptor,
        output_parent_identity,
    ) = validate_capture_destinations(output_dir, diagnostics_dir)
    state = []
    total_downloaded = 0
    try:
        with independent_stage_directory() as stage_text:
            stage = Path(stage_text)
            require_private_stage_directory(stage)
            require_stable_directory_path(
                output_dir.parent,
                output_parent_descriptor,
                output_parent_identity,
                "capture output parent before staging",
            )
            tree = stage / "tree"
            tree.mkdir(mode=0o700)
            copy_repository_inputs(repo, tree, input_records)

            key_path = tree / "release-key" / "RPM-GPG-KEY-Rocky-10"
            key_download = download_to_path(
                contract["release_key"]["url"],
                key_path,
                remaining_download_limit(
                    contract,
                    total_downloaded,
                    contract["limits"]["max_key_bytes"],
                ),
                contract,
            )
            total_downloaded += key_download["size"]
            require_exact(
                key_download["size"],
                contract["release_key"]["size"],
                "downloaded key size",
            )
            require_exact(
                key_download["sha256"],
                contract["release_key"]["sha256"],
                "downloaded key digest",
            )
            key_data = read_regular_bytes(
                key_path,
                "downloaded release key",
                maximum=contract["limits"]["max_key_bytes"],
            )
            verify_key_fingerprint_bytes(
                key_data, contract["release_key"]["fingerprint"]
            )

            total_open_counter = [0, contract["limits"]["max_open_bytes_total"]]
            for repository in contract["repositories"]:
                repository_id = repository["id"]
                base_url = repository["base_url"]
                root = tree / "repositories" / repository_id / "repodata"
                repomd_path = root / "repomd.xml"
                signature_path = root / "repomd.xml.asc"
                repomd_download = download_to_path(
                    base_url + "repodata/repomd.xml",
                    repomd_path,
                    remaining_download_limit(
                        contract,
                        total_downloaded,
                        contract["limits"]["max_repomd_bytes"],
                    ),
                    contract,
                    required_prefix=base_url,
                )
                total_downloaded += repomd_download["size"]
                signature_download = download_to_path(
                    base_url + "repodata/repomd.xml.asc",
                    signature_path,
                    remaining_download_limit(
                        contract,
                        total_downloaded,
                        contract["limits"]["max_signature_bytes"],
                    ),
                    contract,
                    required_prefix=base_url,
                )
                total_downloaded += signature_download["size"]
                repomd_data = read_regular_bytes(
                    repomd_path,
                    "downloaded repomd.xml",
                    maximum=contract["limits"]["max_repomd_bytes"],
                )
                signature_data = read_regular_bytes(
                    signature_path,
                    "downloaded repomd signature",
                    maximum=contract["limits"]["max_signature_bytes"],
                )
                signature = verify_detached_signature_bytes(
                    key_data,
                    signature_data,
                    repomd_data,
                    RELEASE_FINGERPRINT,
                )
                safe_write_json(root / "signature.json", signature)
                parsed = parse_repomd(
                    repomd_data, contract["limits"]["max_repository_objects"]
                )
                objects = []
                for row in parsed["objects"]:
                    object_path = tree / repository_archive_path(repository_id, row["href"])
                    download = download_to_path(
                        urllib.parse.urljoin(base_url, row["href"]),
                        object_path,
                        remaining_download_limit(
                            contract,
                            total_downloaded,
                            contract["limits"]["max_metadata_object_bytes"],
                        ),
                        contract,
                        required_prefix=base_url,
                    )
                    total_downloaded += download["size"]
                    verified = verify_metadata_object(
                        object_path,
                        row,
                        contract["limits"]["max_metadata_open_bytes"],
                        total_open_counter,
                    )
                    objects.append(verified)
                primary = [row for row in objects if row["type"] == "primary"][0]
                state.append(
                    {
                        "id": repository_id,
                        "metadata_object_count": len(objects),
                        "primary_sha256": primary["compressed_sha256"],
                        "primary_size": primary["compressed_size"],
                        "repomd_sha256": repomd_download["sha256"],
                        "signature_sha256": signature_download["sha256"],
                        "status": "verified",
                    }
                )
                write_capture_diagnostics(diagnostics_dir, state)

            manifest = build_capture_manifest(
                tree, repo, contract, input_records, execution_identity
            )
            safe_write_json(tree / "capture-manifest.json", manifest)
            rebuilt = build_capture_manifest(
                tree, repo, contract, input_records, execution_identity
            )
            require_exact(rebuilt, manifest, "self-verified capture manifest")

            payload = stage / "payload"
            payload.mkdir(mode=0o700)
            tar_path = payload / "snapshot.tar"
            create_deterministic_tar(tree, tar_path, contract["limits"])
            tar_size, tar_digest = sha256_file(tar_path)
            write_regular_exclusive(
                payload / "snapshot.tar.sha256",
                "{}  snapshot.tar\n".format(tar_digest).encode("ascii"),
                "snapshot tar digest",
            )
            publish_capture_files(
                tar_path,
                payload / "snapshot.tar.sha256",
                output_dir,
                output_parent_descriptor,
                output_parent_identity,
            )
            if (
                diagnostics_dir is not None
                and diagnostics_dir.parent == output_dir.parent
            ):
                require_stable_directory_path(
                    output_dir.parent,
                    output_parent_descriptor,
                    output_parent_identity,
                    "capture diagnostics parent after publication",
                )
            write_capture_diagnostics(
                diagnostics_dir,
                {
                    "drift": drift_rows(contract, manifest["repositories"]),
                    "execution_identity": execution_identity,
                    "snapshot_identity": manifest["snapshot_identity"],
                    "snapshot_tar_sha256": tar_digest,
                    "snapshot_tar_size": tar_size,
                },
            )
            return manifest
    except Exception as exc:
        error = str(exc) if isinstance(exc, SnapshotError) else "unexpected capture failure"
        try:
            if (
                diagnostics_dir is not None
                and diagnostics_dir.parent == output_dir.parent
            ):
                require_stable_directory_path(
                    output_dir.parent,
                    output_parent_descriptor,
                    output_parent_identity,
                    "capture diagnostics parent after failure",
                )
            write_capture_diagnostics(diagnostics_dir, state, error=error)
        except Exception:
            pass
        if isinstance(exc, SnapshotError):
            raise
        raise
    finally:
        os.close(output_parent_descriptor)


def extract_canonical_tar_stream(source_stream, destination, limits):
    try:
        archive = tarfile.open(fileobj=source_stream, mode="r:")
    except (OSError, tarfile.TarError) as exc:
        raise SnapshotError("cannot open snapshot tar: {}".format(exc))
    with archive:
        members = []
        while True:
            try:
                member = archive.next()
            except (OSError, tarfile.TarError) as exc:
                raise SnapshotError("cannot enumerate snapshot tar: {}".format(exc))
            if member is None:
                break
            members.append(member)
            if len(members) > limits["max_tar_members"]:
                raise SnapshotError("snapshot tar member count exceeds its limit")
        names = [member.name for member in members]
        if not names or names != sorted(names) or len(names) != len(set(names)):
            raise SnapshotError("snapshot tar paths are empty, unsorted, or duplicated")
        total_size = 0
        for member in members:
            path = normalized_relative_path(member.name, "snapshot tar path")
            if not member.isfile():
                raise SnapshotError("snapshot tar may contain regular files only")
            if member.size < 0 or member.size > limits["max_tar_member_bytes"]:
                raise SnapshotError("snapshot tar member exceeds its byte limit")
            total_size += member.size
            if total_size > limits["max_tar_payload_bytes"]:
                raise SnapshotError("snapshot tar payload exceeds its byte limit")
            if (
                member.mode != 0o644
                or member.uid != 0
                or member.gid != 0
                or member.mtime != 0
                or member.uname != ""
                or member.gname != ""
            ):
                raise SnapshotError("snapshot tar metadata is not canonical")
            target = destination.joinpath(*path.parts)
            make_directories_nofollow(target.parent, "snapshot extraction parent")
            member_source = archive.extractfile(member)
            if member_source is None:
                raise SnapshotError("cannot read snapshot tar member")
            output_descriptor = open_regular_create(
                target, "snapshot extracted member"
            )
            try:
                with member_source, os.fdopen(output_descriptor, "wb") as output:
                    output_descriptor = -1
                    shutil.copyfileobj(member_source, output, length=1024 * 1024)
                    output.flush()
                    os.fsync(output.fileno())
                    metadata = os.fstat(output.fileno())
                    if metadata.st_size != member.size:
                        raise SnapshotError(
                            "snapshot tar member length is truncated"
                        )
                    os.fchmod(output.fileno(), 0o600)
            finally:
                if output_descriptor >= 0:
                    os.close(output_descriptor)


def extract_canonical_tar(artifact, destination, limits):
    artifact = absolute_path(artifact, "snapshot artifact")
    descriptor = open_regular_read(artifact, "snapshot artifact")
    try:
        before = regular_identity(os.fstat(descriptor))
        if before[4] < 1 or before[4] > limits["max_snapshot_tar_bytes"]:
            raise SnapshotError("snapshot artifact size is outside its byte limit")
        with os.fdopen(descriptor, "rb") as source:
            descriptor = -1
            extract_canonical_tar_stream(source, destination, limits)
            after = regular_identity(os.fstat(source.fileno()))
    finally:
        if descriptor >= 0:
            os.close(descriptor)
    if before != after:
        raise SnapshotError("snapshot artifact changed while it was read")


def verify_artifact(repo, artifact, contract, input_records, execution_identity):
    validate_contract(contract)
    validate_input_records(input_records)
    execution_identity = validate_execution_identity(
        execution_identity.get("source_commit")
        if isinstance(execution_identity, dict)
        else None,
        execution_identity.get("workflow_ref")
        if isinstance(execution_identity, dict)
        else None,
    )
    require_repository_head(
        repo, execution_identity["source_commit"], input_records
    )
    limits = contract["limits"]
    artifact = absolute_path(artifact, "snapshot artifact")
    artifact_descriptor = open_regular_read(artifact, "snapshot artifact")
    with tempfile.TemporaryDirectory(prefix="mck-rocky-snapshot-verify.") as temp_text:
        tree = Path(temp_text) / "tree"
        tree.mkdir(mode=0o700)
        original_digest = hashlib.sha256()
        original_size = 0
        try:
            before = regular_identity(os.fstat(artifact_descriptor))
            if before[4] < 1 or before[4] > limits["max_snapshot_tar_bytes"]:
                raise SnapshotError("snapshot artifact size is outside its byte limit")
            with os.fdopen(artifact_descriptor, "rb") as artifact_stream:
                artifact_descriptor = -1
                extract_canonical_tar_stream(artifact_stream, tree, limits)
                artifact_stream.seek(0)
                while True:
                    chunk = artifact_stream.read(1024 * 1024)
                    if not chunk:
                        break
                    original_size += len(chunk)
                    original_digest.update(chunk)
                after = regular_identity(os.fstat(artifact_stream.fileno()))
        finally:
            if artifact_descriptor >= 0:
                os.close(artifact_descriptor)
        if before != after or original_size != after[4]:
            raise SnapshotError("snapshot artifact changed while it was verified")
        manifest_path = tree / "capture-manifest.json"
        manifest_data = read_regular_bytes(
            manifest_path, "snapshot manifest", maximum=MAX_JSON_BYTES
        )
        manifest = strict_json_bytes(manifest_data, "capture-manifest.json")
        expected = build_capture_manifest(
            tree, repo, contract, input_records, execution_identity
        )
        require_exact(manifest, expected, "snapshot capture manifest")
        rebuilt_tar = Path(temp_text) / "rebuilt.tar"
        create_deterministic_tar(tree, rebuilt_tar, limits)
        rebuilt_size, rebuilt_digest = sha256_file(rebuilt_tar)
        if (
            original_size != rebuilt_size
            or original_digest.hexdigest() != rebuilt_digest
        ):
            raise SnapshotError("snapshot tar byte stream is not deterministic/canonical")
        return manifest


def parse_args(argv):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--capture", action="store_true")
    mode.add_argument("--verify-artifact", type=Path)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--diagnostics-dir", type=Path)
    parser.add_argument("--source-commit")
    parser.add_argument("--workflow-ref")
    args = parser.parse_args(argv)
    if args.capture and args.output_dir is None:
        parser.error("--capture requires --output-dir")
    if not args.capture and (args.output_dir is not None or args.diagnostics_dir is not None):
        parser.error("output/diagnostics directories are valid only with --capture")
    identity_values = (args.source_commit, args.workflow_ref)
    if args.check and ((args.source_commit is None) != (args.workflow_ref is None)):
        parser.error("--check execution identity must be supplied as one complete pair")
    if not args.check and any(value is None for value in identity_values):
        parser.error("capture and verify require --source-commit and --workflow-ref")
    return args


def main(argv=None):
    args = parse_args(argv)
    try:
        repo = args.repo.resolve()
        contract, input_records = check_repository_inputs(repo)
        execution_identity = None
        if not args.check or args.source_commit is not None:
            execution_identity = validate_execution_identity(
                args.source_commit, args.workflow_ref
            )
        if args.check:
            if execution_identity is not None:
                require_repository_head(
                    repo, execution_identity["source_commit"], input_records
                )
            print(
                json.dumps(
                    {
                        "capture_id": CAPTURE_ID,
                        "claims": FALSE_CLAIMS,
                        "repository_count": len(REPOSITORIES),
                        "status": (
                            "contract-and-checkout-valid-no-credit"
                            if execution_identity is not None
                            else "contract-valid-no-credit"
                        ),
                    },
                    sort_keys=True,
                )
            )
        elif args.capture:
            manifest = capture_snapshot(
                repo,
                args.output_dir,
                args.diagnostics_dir,
                contract,
                input_records,
                execution_identity,
            )
            print(
                json.dumps(
                    {
                        "claims": FALSE_CLAIMS,
                        "execution_identity": execution_identity,
                        "snapshot_identity": manifest["snapshot_identity"],
                        "status": "bounded-capture-complete",
                    },
                    sort_keys=True,
                )
            )
        else:
            manifest = verify_artifact(
                repo,
                args.verify_artifact,
                contract,
                input_records,
                execution_identity,
            )
            print(
                json.dumps(
                    {
                        "claims": FALSE_CLAIMS,
                        "execution_identity": execution_identity,
                        "snapshot_identity": manifest["snapshot_identity"],
                        "status": "artifact-verified-no-credit",
                    },
                    sort_keys=True,
                )
            )
    except SnapshotError as exc:
        print("error: {}".format(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
