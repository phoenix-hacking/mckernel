#!/usr/bin/env python3
"""Validate the bounded, noncrediting FP-0006 OS-status alias witness.

The two producers remain evidence inputs.  This reviewer validates exact
repository authority and capture schemas, but the durable independent result
authority is deliberately required-missing, so no runtime, gate, tracker, or
completion claim can be created here.
"""

from __future__ import print_function

import argparse
import base64
import copy
import errno
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
from typing import Any, Dict, List, Optional, Sequence, Tuple


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONTRACT = Path(
    "host-kernel/contracts/fp0006-ihk-os-status-alias-v1.json"
)
CONTRACT_ID = "fp-0006-ihk-os-status-alias-v1"
LEGACY_SURFACE = "legacy-live-ioctl"
NATIVE_SURFACE = "native-rust-source-fixture"
SURFACE_ALIASES = {
    "legacy": LEGACY_SURFACE,
    "native": NATIVE_SURFACE,
}
HEX64 = re.compile(r"^[0-9a-f]{64}$")

# SELF_DIGEST:1d8d58d150d435337309df417c9372d925f20f865b58c416f8985ef5bdab4147
SELF_SOURCE_MAXIMUM = 1024 * 1024
SECURITY_SOURCE_SHA256 = "d03f035089f343a3e4767054631bd3ff381195e207b6bb0cde4b2f266690a30b"
SECURITY_SOURCE_SIZE = 51627


class WitnessError(RuntimeError):
    """Fail-closed bootstrap error used before exact helpers are loaded."""

# The exact dependency is loaded only after the CLI proves isolated mode and
# verifies this source.  Authoritative review is never available through an
# importing process, so parent monkeypatches cannot cross the execution
# boundary.
_read_rooted_file = None
_read_capture_members = None
_file_identity = None


def _exact_json_equal(actual: Any, expected: Any) -> bool:
    if type(actual) is not type(expected):
        return False
    if type(expected) is dict:
        if len(actual) != len(expected):
            return False
        for key, expected_value in expected.items():
            if type(key) is not str or key not in actual:
                return False
            if not _exact_json_equal(actual[key], expected_value):
                return False
        return True
    if type(expected) is list:
        if len(actual) != len(expected):
            return False
        return all(
            _exact_json_equal(actual_item, expected_item)
            for actual_item, expected_item in zip(actual, expected)
        )
    return bool(actual == expected)


def _require_exact_json(actual: Any, expected: Any, label: str) -> None:
    if not _exact_json_equal(actual, expected):
        raise WitnessError("{0} differs".format(label))


def _duplicate_rejecting_object(pairs: List[Tuple[str, Any]]) -> Dict[str, Any]:
    value = {}  # type: Dict[str, Any]
    for key, item in pairs:
        if key in value:
            raise WitnessError("duplicate JSON key: {0}".format(key))
        value[key] = item
    return value


def _reject_constant(value: str) -> None:
    raise WitnessError("non-finite JSON number is forbidden: {0}".format(value))


def _validate_strict_json(value: Any, label: str) -> None:
    if value is None or type(value) in (bool, int, str):
        return
    if type(value) is list:
        for item in value:
            _validate_strict_json(item, label)
        return
    if type(value) is dict:
        for key, item in value.items():
            if type(key) is not str:
                raise WitnessError("{0} has a non-string key".format(label))
            _validate_strict_json(item, label)
        return
    raise WitnessError("{0} has a non-strict JSON value".format(label))


def _load_json_bytes(data: bytes, label: str) -> Dict[str, Any]:
    try:
        value = json.loads(
            data.decode("utf-8"),
            object_pairs_hook=_duplicate_rejecting_object,
            parse_constant=_reject_constant,
        )
    except WitnessError:
        raise
    except (UnicodeError, ValueError) as error:
        raise WitnessError("cannot parse {0}: {1}".format(label, error))
    if type(value) is not dict:
        raise WitnessError("{0} must contain one JSON object".format(label))
    _validate_strict_json(value, label)
    return value


def _canonical_json(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode(
        "utf-8"
    )


def _pretty_json(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _bootstrap_identity(metadata: os.stat_result) -> Tuple[int, ...]:
    return (
        metadata.st_dev,
        metadata.st_ino,
        metadata.st_mode,
        metadata.st_nlink,
        metadata.st_uid,
        metadata.st_gid,
        metadata.st_rdev,
        metadata.st_size,
        getattr(metadata, "st_mtime_ns", int(metadata.st_mtime * 1000000000)),
        getattr(metadata, "st_ctime_ns", int(metadata.st_ctime * 1000000000)),
        getattr(metadata, "st_blksize", 0),
        getattr(metadata, "st_blocks", 0),
    )


def _open_absolute_no_follow(path: str, label: str) -> Tuple[int, os.stat_result]:
    if type(path) is not str or not path or "\0" in path:
        raise WitnessError("{0} path differs".format(label))
    absolute = os.path.abspath(path)
    parts = Path(absolute).parts
    if not parts or parts[0] != "/":
        raise WitnessError("{0} path is not absolute".format(label))
    no_follow = getattr(os, "O_NOFOLLOW", 0)
    directory_only = getattr(os, "O_DIRECTORY", 0)
    if not no_follow or not directory_only:
        raise WitnessError("isolated CLI no-follow traversal is unavailable")
    directory_flags = (
        os.O_RDONLY
        | getattr(os, "O_CLOEXEC", 0)
        | no_follow
        | directory_only
    )
    leaf_flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | no_follow
    directory = os.open("/", directory_flags)
    leaf = -1
    try:
        for component in parts[1:-1]:
            next_directory = os.open(component, directory_flags, dir_fd=directory)
            os.close(directory)
            directory = next_directory
        leaf = os.open(parts[-1], leaf_flags, dir_fd=directory)
        metadata = os.fstat(leaf)
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1:
            raise WitnessError("{0} must be one regular unlinked authority".format(label))
        return leaf, metadata
    except Exception:
        if leaf >= 0:
            os.close(leaf)
        raise
    finally:
        os.close(directory)


def _read_retained_exact(
    descriptor: int, metadata: os.stat_result, maximum: int, label: str
) -> bytes:
    if type(maximum) is not int or maximum < 1:
        raise WitnessError("{0} maximum differs".format(label))
    if metadata.st_size < 1 or metadata.st_size > maximum:
        raise WitnessError("{0} size exceeds its bound".format(label))
    os.lseek(descriptor, 0, os.SEEK_SET)
    chunks = []  # type: List[bytes]
    remaining = metadata.st_size
    while remaining:
        chunk = os.read(descriptor, min(65536, remaining))
        if not chunk:
            raise WitnessError("{0} ended before its retained size".format(label))
        chunks.append(chunk)
        remaining -= len(chunk)
    if os.read(descriptor, 1):
        raise WitnessError("{0} grew beyond its retained size".format(label))
    after = os.fstat(descriptor)
    if _bootstrap_identity(after) != _bootstrap_identity(metadata):
        raise WitnessError("{0} changed while being read".format(label))
    return b"".join(chunks)


def _open_verified_cli_source() -> Dict[str, Any]:
    if sys.flags.isolated != 1:
        raise WitnessError("authoritative review requires python3 -I")
    if type(sys.argv[0]) is not str or not sys.argv[0]:
        raise WitnessError("isolated CLI source path differs")
    path = os.path.abspath(sys.argv[0])
    descriptor, metadata = _open_absolute_no_follow(path, "isolated CLI source")
    try:
        data = _read_retained_exact(
            descriptor, metadata, SELF_SOURCE_MAXIMUM, "isolated CLI source"
        )
        pattern = br"SELF_" + br"DIGEST:[0-9a-f]{64}"
        markers = re.findall(pattern, data)
        normalized, count = re.subn(
            pattern, b"SELF_" + b"DIGEST:" + b"0" * 64, data
        )
        expected = markers[0].split(b":", 1)[1].decode("ascii") if markers else ""
        if count != 1 or _sha256(normalized) != expected:
            raise WitnessError("isolated CLI source identity differs")
        return {
            "data": data,
            "descriptor": descriptor,
            "identity": _bootstrap_identity(metadata),
            "path": path,
        }
    except Exception:
        os.close(descriptor)
        raise


def _verify_cli_source_final(source: Dict[str, Any]) -> None:
    descriptor = source["descriptor"]
    expected = source["identity"]
    if _bootstrap_identity(os.fstat(descriptor)) != expected:
        raise WitnessError("isolated CLI retained source changed before output")
    current, metadata = _open_absolute_no_follow(
        source["path"], "isolated CLI final source"
    )
    try:
        if _bootstrap_identity(metadata) != expected:
            raise WitnessError("isolated CLI source path changed before output")
    finally:
        os.close(current)


def _load_exact_security_primitives(source_path: str) -> None:
    global WitnessError, _directory_identity, _file_identity
    global _read_capture_members, _read_rooted_file
    security_path = str(Path(source_path).parent / "fp0006_ihk_device_negative_dispatch.py")
    descriptor, metadata = _open_absolute_no_follow(
        security_path, "isolated security primitives"
    )
    try:
        data = _read_retained_exact(
            descriptor, metadata, SECURITY_SOURCE_SIZE,
            "isolated security primitives",
        )
    finally:
        os.close(descriptor)
    if len(data) != SECURITY_SOURCE_SIZE or _sha256(data) != SECURITY_SOURCE_SHA256:
        raise WitnessError("isolated security primitive identity differs")
    namespace = {
        "__builtins__": __builtins__,
        "__file__": security_path,
        "__name__": "_fp0006_exact_security_primitives",
        "__package__": None,
    }
    code = compile(data, security_path, "exec", dont_inherit=True)
    exec(code, namespace, namespace)
    required = (
        "WitnessError",
        "_directory_identity",
        "_file_identity",
        "_read_capture_members",
        "_read_rooted_file",
    )
    if any(name not in namespace for name in required):
        raise WitnessError("isolated security primitive exports differ")
    WitnessError = namespace["WitnessError"]
    _directory_identity = namespace["_directory_identity"]
    _file_identity = namespace["_file_identity"]
    _read_capture_members = namespace["_read_capture_members"]
    _read_rooted_file = namespace["_read_rooted_file"]


def _require_keys(value: Any, expected: Sequence[str], label: str) -> None:
    if type(value) is not dict:
        raise WitnessError("{0} must be an object".format(label))
    _require_exact_json(sorted(value.keys()), sorted(expected), label + " keys")


def _require_int(value: Any, label: str) -> int:
    if type(value) is not int:
        raise WitnessError("{0} must be an exact integer".format(label))
    return value


def _bind_closed_file_bytes(
    snapshots: List[Dict[str, Any]], data: bytes, label: str
) -> None:
    if not snapshots or type(data) is not bytes:
        raise WitnessError("{0} aggregate snapshot is unavailable".format(label))
    snapshot = snapshots[-1]
    leaf = snapshot.get("leaf")
    if type(leaf) is not dict or Path(leaf.get("path")) != Path(snapshot["target"]):
        raise WitnessError("{0} aggregate leaf binding differs".format(label))
    snapshot["expected_bytes"] = data


def _bind_closed_capture_bytes(
    snapshots: List[Dict[str, Any]], files: Dict[str, bytes]
) -> None:
    if not snapshots or type(files) is not dict:
        raise WitnessError("capture aggregate snapshot is unavailable")
    snapshot = snapshots[-1]
    members = snapshot.get("members")
    if type(members) is not list or sorted(files.keys()) != members:
        raise WitnessError("capture aggregate member binding differs")
    for name in members:
        if type(files[name]) is not bytes:
            raise WitnessError("capture aggregate bytes differ: " + name)
    snapshot["expected_bytes"] = dict(files)


def _aggregate_read_exact(
    path: Path, expected_identity: List[int], expected_bytes: bytes, label: str
) -> None:
    """Replay one closed leaf without using the owned os.close path."""

    try:
        named_before = os.lstat(str(path))
        if stat.S_ISLNK(named_before.st_mode) or not stat.S_ISREG(named_before.st_mode):
            raise WitnessError("{0} aggregate leaf changed type".format(label))
        _require_exact_json(
            _file_identity(named_before), expected_identity,
            label + " aggregate named identity",
        )
        if named_before.st_nlink != 1:
            raise WitnessError("{0} aggregate leaf is multiply linked".format(label))
        with path.open("rb", buffering=0) as source:
            retained = os.fstat(source.fileno())
            _require_exact_json(
                _file_identity(retained), expected_identity,
                label + " aggregate descriptor identity",
            )
            first = source.read(len(expected_bytes) + 1)
            source.seek(0)
            second = source.read(len(expected_bytes) + 1)
            _require_exact_json(first, expected_bytes, label + " aggregate bytes")
            _require_exact_json(second, expected_bytes,
                                label + " aggregate byte replay")
            _require_exact_json(
                _file_identity(os.fstat(source.fileno())), expected_identity,
                label + " aggregate retained identity",
            )
        named_after = os.lstat(str(path))
        _require_exact_json(
            _file_identity(named_after), expected_identity,
            label + " aggregate post-read identity",
        )
    except WitnessError:
        raise
    except (OSError, TypeError, ValueError) as error:
        raise WitnessError("cannot aggregate-replay {0}: {1}".format(label, error))


def _private_exec_helper_bytes() -> bytes:
    """Return the exact isolated verifier source sealed into a memfd."""

    return b'''from __future__ import print_function
import base64
import errno
import fcntl
import json
import os
import stat
import sys

MAX_EXPECTATION = 8 * 1024 * 1024
MAX_FILE_BYTES = 4 * 1024 * 1024
MAX_TOTAL_BYTES = 8 * 1024 * 1024
MAX_DIRECTORIES = 128
MAX_FILES = 32
MAX_NAMESPACES = 8
MAX_FD = 4095
DIRECTORY_IDENTITY_LENGTH = 5
FILE_IDENTITY_LENGTH = 12
PROTOCOL = "fp0006-private-exec-seal-v1"
F_GET_SEALS = 1034
REQUIRED_SEALS = 15

def file_identity(info):
    return [
        info.st_dev, info.st_ino, info.st_mode, info.st_nlink,
        info.st_uid, info.st_gid, info.st_rdev, info.st_size,
        info.st_mtime_ns, info.st_ctime_ns,
        getattr(info, "st_blksize", 0), getattr(info, "st_blocks", 0),
    ]

def directory_identity(info):
    return [
        info.st_dev, info.st_ino, info.st_mode, info.st_uid, info.st_gid,
    ]

def object_without_duplicates(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError("duplicate key")
        value[key] = item
    return value

def strict(value):
    if value is None or type(value) in (bool, int, str):
        return
    if type(value) is list:
        for item in value:
            strict(item)
        return
    if type(value) is dict:
        for key, item in value.items():
            if type(key) is not str:
                raise ValueError("non-string key")
            strict(item)
        return
    raise ValueError("non-strict JSON")

def exact_keys(value, keys):
    if type(value) is not dict or sorted(value.keys()) != sorted(keys):
        raise ValueError("keys differ")

def exact_int(value):
    if type(value) is not int:
        raise ValueError("integer differs")
    return value

def argument_fd(text):
    if type(text) is not str or not text.isdigit() or str(int(text)) != text:
        raise ValueError("fd argument differs")
    value = int(text)
    if value < 3 or value > MAX_FD:
        raise ValueError("fd argument outside cap")
    return value

def read_bounded(descriptor, cap):
    info = os.fstat(descriptor)
    if info.st_size < 0 or info.st_size > cap:
        raise ValueError("sealed input size differs")
    os.lseek(descriptor, 0, os.SEEK_SET)
    chunks = []
    remaining = info.st_size
    while remaining:
        chunk = os.read(descriptor, min(remaining, 65536))
        if not chunk:
            raise ValueError("sealed input ended early")
        chunks.append(chunk)
        remaining -= len(chunk)
    if os.read(descriptor, 1):
        raise ValueError("sealed input grew")
    return b"".join(chunks)

def read_exact_file(descriptor, size):
    if size < 0 or size > MAX_FILE_BYTES:
        raise ValueError("file size outside cap")
    os.lseek(descriptor, 0, os.SEEK_SET)
    chunks = []
    remaining = size
    while remaining:
        chunk = os.read(descriptor, min(remaining, 65536))
        if not chunk:
            raise ValueError("file ended early")
        chunks.append(chunk)
        remaining -= len(chunk)
    if os.read(descriptor, 1):
        raise ValueError("file grew")
    return b"".join(chunks)

def validate_identity(value, length):
    if type(value) is not list or len(value) != length:
        raise ValueError("identity shape differs")
    for item in value:
        exact_int(item)
    return value

def validate_fd_set(expected):
    names = os.listdir("/proc/self/fd")
    if len(names) != len(expected) + 4:
        raise ValueError("inherited fd namespace exceeds cap")
    actual = []
    standard = []
    transient = []
    seen = set()
    for name in names:
        if type(name) is not str or not name.isdigit() or str(int(name)) != name:
            raise ValueError("inherited fd namespace differs")
        descriptor = int(name)
        if descriptor in seen:
            raise ValueError("inherited fd namespace duplicates")
        seen.add(descriptor)
        if descriptor <= 2:
            standard.append(descriptor)
            continue
        if descriptor > MAX_FD:
            raise ValueError("inherited fd exceeds cap")
        try:
            fcntl.fcntl(descriptor, fcntl.F_GETFD)
        except OSError as error:
            if error.errno != errno.EBADF:
                raise
            transient.append(descriptor)
        else:
            actual.append(descriptor)
    if sorted(standard) != [0, 1, 2]:
        raise ValueError("standard fd set differs")
    if len(transient) != 1:
        raise ValueError("inherited fd namespace transient differs")
    if sorted(actual) != sorted(expected):
        raise ValueError("inherited fd set differs")
    for descriptor in actual:
        flags = fcntl.fcntl(descriptor, fcntl.F_GETFL)
        if flags & os.O_ACCMODE != os.O_RDONLY:
            raise ValueError("inherited source fd is not read-only")

def main():
    if len(sys.argv) != 4:
        return 40
    helper_fd = argument_fd(sys.argv[1])
    expectation_fd = argument_fd(sys.argv[2])
    start_fd = argument_fd(sys.argv[3])
    for descriptor in (helper_fd, expectation_fd, start_fd):
        if fcntl.fcntl(descriptor, fcntl.F_GETFL) & os.O_ACCMODE != os.O_RDONLY:
            return 42
    if fcntl.fcntl(helper_fd, F_GET_SEALS) != REQUIRED_SEALS:
        return 42
    os.close(helper_fd)
    start = os.read(start_fd, 2)
    if start != b"G" or os.read(start_fd, 1) != b"":
        return 41
    os.close(start_fd)
    if fcntl.fcntl(expectation_fd, F_GET_SEALS) != REQUIRED_SEALS:
        return 42
    raw = read_bounded(expectation_fd, MAX_EXPECTATION)
    os.close(expectation_fd)
    value = json.loads(
        raw.decode("utf-8"), object_pairs_hook=object_without_duplicates,
        parse_constant=lambda item: (_ for _ in ()).throw(ValueError(item)),
    )
    strict(value)
    exact_keys(value, ("directories", "files", "namespaces", "protocol"))
    if value["protocol"] != PROTOCOL:
        return 43
    directories = value["directories"]
    files = value["files"]
    namespaces = value["namespaces"]
    if (
        type(directories) is not list or len(directories) > MAX_DIRECTORIES or
        type(files) is not list or len(files) > MAX_FILES or
        type(namespaces) is not list or len(namespaces) > MAX_NAMESPACES
    ):
        return 44
    expected_fds = set()
    for row in directories:
        exact_keys(row, ("fd", "identity"))
        descriptor = exact_int(row["fd"])
        if descriptor < 3 or descriptor > MAX_FD or descriptor in expected_fds:
            raise ValueError("directory fd differs")
        expected_fds.add(descriptor)
        validate_identity(row["identity"], DIRECTORY_IDENTITY_LENGTH)
    total_bytes = 0
    for row in files:
        exact_keys(row, ("bytes", "fd", "identity"))
        descriptor = exact_int(row["fd"])
        if descriptor < 3 or descriptor > MAX_FD or descriptor in expected_fds:
            raise ValueError("file fd differs")
        expected_fds.add(descriptor)
        validate_identity(row["identity"], FILE_IDENTITY_LENGTH)
        if type(row["bytes"]) is not str:
            raise ValueError("file bytes encoding differs")
        decoded = base64.b64decode(row["bytes"].encode("ascii"), validate=True)
        if len(decoded) > MAX_FILE_BYTES:
            raise ValueError("file bytes exceed cap")
        total_bytes += len(decoded)
        if total_bytes > MAX_TOTAL_BYTES:
            raise ValueError("total file bytes exceed cap")
        row["decoded"] = decoded
    for row in namespaces:
        exact_keys(row, ("fd", "members"))
        descriptor = exact_int(row["fd"])
        if descriptor not in expected_fds or type(row["members"]) is not list:
            raise ValueError("namespace fd differs")
        if len(row["members"]) > 16:
            raise ValueError("namespace member cap differs")
        for member in row["members"]:
            if type(member) is not str or not member or "/" in member or "\\\\" in member:
                raise ValueError("namespace member differs")
    validate_fd_set(expected_fds)

    observed_namespaces = []
    expected_namespaces = []
    observed_directories = []
    expected_directories = []
    observed_files = []
    expected_files = []
    for row in namespaces:
        observed_namespaces.append(sorted(os.listdir(row["fd"])))
        expected_namespaces.append(row["members"])
    for row in directories:
        observed_directories.append(directory_identity(os.fstat(row["fd"])))
        expected_directories.append(row["identity"])
    for row in files:
        before = file_identity(os.fstat(row["fd"]))
        first = read_exact_file(row["fd"], len(row["decoded"]))
        second = read_exact_file(row["fd"], len(row["decoded"]))
        after = file_identity(os.fstat(row["fd"]))
        observed_files.append((before, first, second, after))
        expected_files.append(
            (row["identity"], row["decoded"], row["decoded"], row["identity"])
        )
    matched = (
        observed_namespaces == expected_namespaces and
        observed_directories == expected_directories and
        observed_files == expected_files
    )
    return 0 if matched else 45

try:
    status = main()
except BaseException:
    status = 46
os._exit(status)
'''


def _owned_fd_identity(
    descriptor: int, label: str, identity_length: int = 12,
) -> Optional[List[int]]:
    if type(descriptor) is not int or descriptor < 0:
        raise WitnessError("{0} descriptor differs".format(label))
    try:
        metadata = os.fstat(descriptor)
        if identity_length == 5:
            return _directory_identity(metadata)
        if identity_length == 12:
            return _file_identity(metadata)
        raise WitnessError("{0} identity length differs".format(label))
    except OSError as error:
        if error.errno == errno.EBADF:
            return None
        raise WitnessError(
            "cannot identify {0} descriptor: {1}".format(label, error)
        )


def _owned_fd_state(
    descriptor: int, expected_identity: Sequence[int], label: str,
) -> str:
    if type(expected_identity) is not list or any(
        type(item) is not int for item in expected_identity
    ):
        raise WitnessError("{0} retained identity differs".format(label))
    if len(expected_identity) not in (5, 12):
        raise WitnessError("{0} retained identity length differs".format(label))
    actual = _owned_fd_identity(descriptor, label, len(expected_identity))
    if actual is None:
        return "closed"
    if not _exact_json_equal(actual, expected_identity):
        return "reused"
    return "owned"


def _close_owned_fd_once(
    descriptor: int, expected_identity: List[int], label: str,
) -> Tuple[bool, Optional[BaseException]]:
    state = _owned_fd_state(descriptor, expected_identity, label)
    if state == "closed":
        return True, WitnessError(
            "{0} descriptor closed before owned close".format(label)
        )
    if state == "reused":
        return True, WitnessError(
            "{0} descriptor identity changed before owned close".format(label)
        )
    try:
        os.close(descriptor)
    except BaseException as error:
        # A failed close does not preserve ownership of the descriptor number.
        # On Linux the kernel may already have released the open file before
        # reporting a late error, and another thread or callback may reuse the
        # same number immediately.  Even reopening the same inode is not proof
        # that the new open-file description is ours.  Retire this ownership
        # token after the single close attempt and never probe or close the
        # number again; an uncertain leak is safer than closing an unrelated
        # replacement descriptor.
        return True, error
    return True, None


def _cleanup_owned_fd(
    descriptor: int, expected_identity: List[int], label: str,
) -> Tuple[bool, Optional[BaseException]]:
    # Ownership is deliberately one-shot.  Retrying a descriptor number after
    # close() reports an error can target a replacement open-file description.
    return _close_owned_fd_once(descriptor, expected_identity, label)


def _create_sealed_read_fd(data: bytes, label: str) -> int:
    if type(data) is not bytes or not data:
        raise WitnessError("{0} sealed bytes differ".format(label))
    creator = getattr(os, "memfd_create", None)
    allow_sealing = getattr(os, "MFD_ALLOW_SEALING", 2)
    close_on_exec = getattr(os, "MFD_CLOEXEC", 1)
    add_seals = getattr(fcntl, "F_ADD_SEALS", 1033)
    get_seals = getattr(fcntl, "F_GET_SEALS", 1034)
    required_seals = 15
    writable = -1
    readable = -1
    writable_identity = None  # type: Optional[List[int]]
    readable_identity = None  # type: Optional[List[int]]
    success = False
    try:
        if creator is not None:
            writable = creator("fp0006-" + label, allow_sealing | close_on_exec)
        else:
            if not hasattr(os, "uname") or os.uname().machine != "x86_64":
                raise WitnessError("sealed memfd support is required")
            try:
                import ctypes

                libc = ctypes.CDLL(None, use_errno=True)
                libc.syscall.restype = ctypes.c_long
                result = libc.syscall(
                    ctypes.c_long(319),
                    ctypes.c_char_p(("fp0006-" + label).encode("ascii")),
                    ctypes.c_uint(allow_sealing | close_on_exec),
                )
                if result < 0:
                    error_number = ctypes.get_errno()
                    raise OSError(error_number, os.strerror(error_number))
                writable = int(result)
            except (ImportError, AttributeError) as error:
                raise WitnessError(
                    "sealed memfd support is required: {0}".format(error)
                )
        writable_identity = _owned_fd_identity(
            writable, label + " writable memfd"
        )
        if writable_identity is None:
            raise WitnessError("{0} writable memfd is unavailable".format(label))
        offset = 0
        while offset < len(data):
            written = os.write(writable, data[offset:])
            if written <= 0:
                raise WitnessError("{0} sealed write failed".format(label))
            offset += written
            writable_identity = _owned_fd_identity(
                writable, label + " writable memfd"
            )
            if writable_identity is None:
                raise WitnessError(
                    "{0} writable memfd disappeared".format(label)
                )
        if os.fsync(writable) is not None:
            raise WitnessError("{0} sealed sync differs".format(label))
        fcntl.fcntl(writable, add_seals, required_seals)
        if fcntl.fcntl(writable, get_seals) != required_seals:
            raise WitnessError("{0} seals differ".format(label))
        writable_identity = _owned_fd_identity(
            writable, label + " sealed writable memfd"
        )
        if writable_identity is None:
            raise WitnessError("{0} sealed memfd disappeared".format(label))
        readable = os.open(
            "/proc/self/fd/{0}".format(writable),
            os.O_RDONLY | getattr(os, "O_CLOEXEC", 0),
        )
        readable_identity = _owned_fd_identity(
            readable, label + " readable memfd"
        )
        if readable_identity is None:
            raise WitnessError("{0} readable memfd disappeared".format(label))
        closed, close_error = _close_owned_fd_once(
            writable, writable_identity, label + " writable memfd"
        )
        if closed:
            writable = -1
        if close_error is not None:
            raise WitnessError(
                "cannot close {0} writable memfd: {1}".format(label, close_error)
            )
        success = True
        return readable
    except WitnessError:
        raise
    except (OSError, TypeError, ValueError) as error:
        raise WitnessError("cannot seal {0}: {1}".format(label, error))
    finally:
        cleanup_error = None  # type: Optional[BaseException]
        if writable >= 0:
            if writable_identity is None:
                raise WitnessError(
                    "{0} writable cleanup identity is unavailable".format(label)
                )
            closed, error = _cleanup_owned_fd(
                writable, writable_identity,
                label + " writable memfd cleanup",
            )
            if closed:
                writable = -1
            if error is not None:
                cleanup_error = error
        if readable >= 0 and not success:
            if readable_identity is None:
                raise WitnessError(
                    "{0} readable cleanup identity is unavailable".format(label)
                )
            closed, error = _cleanup_owned_fd(
                readable, readable_identity,
                label + " readable memfd cleanup",
            )
            if closed:
                readable = -1
            if error is not None and cleanup_error is None:
                cleanup_error = error
        if cleanup_error is not None:
            raise WitnessError(
                "cannot clean up {0} sealed descriptors: {1}".format(
                    label, cleanup_error
                )
            )


def _raw_close_fd(descriptor: int, label: str) -> None:
    """Close a private control fd without invoking a patched os.close hook."""

    if type(descriptor) is not int or descriptor < 0:
        raise WitnessError("{0} raw-close descriptor differs".format(label))
    if not hasattr(os, "uname") or os.uname().machine != "x86_64":
        raise WitnessError("x86_64 raw-close support is required")
    try:
        import ctypes

        libc = ctypes.CDLL(None, use_errno=True)
        libc.syscall.restype = ctypes.c_long
        result = libc.syscall(ctypes.c_long(3), ctypes.c_int(descriptor))
        if result != 0:
            error_number = ctypes.get_errno()
            raise OSError(error_number, os.strerror(error_number))
    except (ImportError, AttributeError, OSError, TypeError, ValueError) as error:
        raise WitnessError("cannot raw-close {0}: {1}".format(label, error))


def _raw_close_owned_fd_once(
    descriptor: int, expected_identity: List[int], label: str,
) -> Tuple[bool, Optional[BaseException]]:
    state = _owned_fd_state(descriptor, expected_identity, label)
    if state == "closed":
        return True, WitnessError(
            "{0} descriptor closed before raw close".format(label)
        )
    if state == "reused":
        return True, WitnessError(
            "{0} descriptor identity changed before raw close".format(label)
        )
    try:
        _raw_close_fd(descriptor, label)
    except BaseException as error:
        # A raw close attempt consumes this ownership token even when the
        # syscall reports an error.  Linux may already have released the open
        # file description before returning a late error such as EINTR, and
        # the descriptor number may immediately name either the same inode
        # through a new open-file description or an unrelated inode.  Never
        # probe or retry the number after the attempt: doing so could make the
        # caller's cleanup close that replacement descriptor.
        return True, error
    return True, None


def _run_exec_seal(
    directory_records: List[Dict[str, Any]],
    file_records: List[Dict[str, Any]],
    namespace_records: List[Dict[str, Any]],
) -> None:
    helper = _private_exec_helper_bytes()
    expected_helper_sha256 = "3e40970cc1b006a39ee0436a6cab47f413d49009d40530bb5fe5c0e704738e2c"
    expected_helper_size = 9171
    if len(helper) != expected_helper_size or _sha256(helper) != expected_helper_sha256:
        raise WitnessError("private exec helper identity differs")

    expectation = {
        "directories": [
            {"fd": row["descriptor"], "identity": list(row["identity"])}
            for row in directory_records
        ],
        "files": [
            {
                "bytes": base64.b64encode(row["bytes"]).decode("ascii"),
                "fd": row["descriptor"],
                "identity": list(row["identity"]),
            }
            for row in file_records
        ],
        "namespaces": [
            {"fd": row["descriptor"], "members": list(row["members"])}
            for row in namespace_records
        ],
        "protocol": "fp0006-private-exec-seal-v1",
    }
    expectation_bytes = _canonical_json(expectation)
    if len(expectation_bytes) > 8 * 1024 * 1024:
        raise WitnessError("private exec expectation exceeds its cap")

    def kill_and_reap(candidate: subprocess.Popen) -> None:
        try:
            candidate.kill()
        except (OSError, subprocess.SubprocessError):
            pass
        except (AttributeError, TypeError, ValueError) as error:
            raise WitnessError(
                "private exec verifier kill failed: {0}".format(error)
            )
        try:
            reaped_status = candidate.wait()
        except (OSError, subprocess.SubprocessError, AttributeError, TypeError) as error:
            raise WitnessError(
                "private exec verifier reap failed: {0}".format(error)
            )
        if type(reaped_status) is not int:
            raise WitnessError("private exec verifier reap status differs")

    helper_fd = -1
    expectation_fd = -1
    start_read = -1
    start_write = -1
    helper_identity = None  # type: Optional[List[int]]
    expectation_identity = None  # type: Optional[List[int]]
    start_read_identity = None  # type: Optional[List[int]]
    start_write_identity = None  # type: Optional[List[int]]
    process = None  # type: Optional[subprocess.Popen]
    try:
        helper_fd = _create_sealed_read_fd(helper, "exec-helper")
        helper_identity = _owned_fd_identity(helper_fd, "private exec helper")
        if helper_identity is None:
            raise WitnessError("private exec helper disappeared")
        expectation_fd = _create_sealed_read_fd(expectation_bytes, "expectation")
        expectation_identity = _owned_fd_identity(
            expectation_fd, "private exec expectation"
        )
        if expectation_identity is None:
            raise WitnessError("private exec expectation disappeared")
        start_read, start_write = os.pipe()
        start_read_identity = _owned_fd_identity(
            start_read, "private exec start reader"
        )
        start_write_identity = _owned_fd_identity(
            start_write, "private exec start writer"
        )
        if start_read_identity is None or start_write_identity is None:
            raise WitnessError("private exec start pipe disappeared")
        source_fds = [row["descriptor"] for row in directory_records + file_records]
        pass_fds = sorted(set(source_fds + [helper_fd, expectation_fd, start_read]))
        if (
            len(pass_fds) > 192
            or any(type(item) is not int or item < 3 or item > 4095 for item in pass_fds)
        ):
            raise WitnessError("private exec inherited fd set exceeds its cap")
        command = [
            "/proc/self/exe", "-I", "-S", "-B",
            "/proc/self/fd/{0}".format(helper_fd),
            str(helper_fd), str(expectation_fd), str(start_read),
        ]
        process = subprocess.Popen(
            command,
            executable="/proc/self/exe",
            close_fds=True,
            pass_fds=tuple(pass_fds),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            env={
                "LC_ALL": "C.UTF-8",
                "PATH": "",
                "PYTHONDONTWRITEBYTECODE": "1",
            },
        )

        closed, close_error = _close_owned_fd_once(
            start_read, start_read_identity, "private exec start reader"
        )
        if closed:
            start_read = -1
        if close_error is not None:
            raise WitnessError(
                "private exec start-reader close failed: {0}".format(close_error)
            )
        closed, close_error = _close_owned_fd_once(
            helper_fd, helper_identity, "private exec helper"
        )
        if closed:
            helper_fd = -1
        if close_error is not None:
            raise WitnessError(
                "private exec helper close failed: {0}".format(close_error)
            )
        closed, close_error = _close_owned_fd_once(
            expectation_fd, expectation_identity, "private exec expectation"
        )
        if closed:
            expectation_fd = -1
        if close_error is not None:
            raise WitnessError(
                "private exec expectation close failed: {0}".format(close_error)
            )
        close_error = None  # type: Optional[BaseException]
        for record in file_records:
            descriptor = record["descriptor"]
            closed, error = _close_owned_fd_once(
                descriptor, record["owned_identity"],
                record["label"] + " source",
            )
            if closed:
                record["descriptor"] = -1
            if error is not None and close_error is None:
                close_error = error
        for record in reversed(directory_records):
            descriptor = record["descriptor"]
            closed, error = _close_owned_fd_once(
                descriptor, record["owned_identity"],
                "private exec source directory " + record["path"],
            )
            if closed:
                record["descriptor"] = -1
            if error is not None and close_error is None:
                close_error = error
        if close_error is not None:
            raise WitnessError(
                "private exec parent close failed: {0}".format(close_error)
            )
        if os.write(start_write, b"G") != 1:
            raise WitnessError("private exec start protocol write differs")
        # The helper requires EOF after the one-byte token.  A raw syscall
        # closes this private control writer only after every callback-capable
        # parent close has completed, so EOF is the start barrier rather than
        # a race with an os.close wrapper.
        closed, close_error = _raw_close_owned_fd_once(
            start_write, start_write_identity, "private exec start writer"
        )
        if closed:
            start_write = -1
        if close_error is not None:
            raise WitnessError(str(close_error))
        try:
            status = process.wait(timeout=10.0)
        except subprocess.TimeoutExpired:
            kill_and_reap(process)
            process = None
            raise WitnessError("private exec verifier timed out")
        process = None
        if type(status) is not int or status != 0:
            raise WitnessError(
                "private exec verifier protocol failed with status {0}".format(status)
            )
    except WitnessError:
        raise
    except (OSError, TypeError, ValueError, subprocess.SubprocessError) as error:
        raise WitnessError("private exec verifier failed: {0}".format(error))
    finally:
        cleanup_error = None  # type: Optional[WitnessError]
        if process is not None:
            try:
                kill_and_reap(process)
            except WitnessError as error:
                cleanup_error = error
        if start_write >= 0:
            if start_write_identity is None:
                raise WitnessError(
                    "private exec cleanup writer identity is unavailable"
                )
            closed, error = _cleanup_owned_fd(
                start_write, start_write_identity,
                "private exec cleanup writer",
            )
            if closed:
                start_write = -1
            if error is not None and cleanup_error is None:
                cleanup_error = error
        control_descriptors = (
            ("start_read", start_read, start_read_identity,
             "private exec start-reader cleanup"),
            ("expectation_fd", expectation_fd, expectation_identity,
             "private exec expectation cleanup"),
            ("helper_fd", helper_fd, helper_identity,
             "private exec helper cleanup"),
        )
        for name, descriptor, identity, label in control_descriptors:
            if descriptor < 0:
                continue
            if identity is None:
                if cleanup_error is None:
                    cleanup_error = WitnessError(
                        "{0} identity is unavailable".format(label)
                    )
                continue
            closed, error = _cleanup_owned_fd(descriptor, identity, label)
            if closed:
                if name == "start_read":
                    start_read = -1
                elif name == "expectation_fd":
                    expectation_fd = -1
                else:
                    helper_fd = -1
            if error is not None and cleanup_error is None:
                cleanup_error = error
        for record in file_records:
            descriptor = record.get("descriptor", -1)
            if descriptor < 0:
                continue
            closed, error = _cleanup_owned_fd(
                descriptor, record["owned_identity"],
                record["label"] + " source cleanup",
            )
            if closed:
                record["descriptor"] = -1
            if error is not None and cleanup_error is None:
                cleanup_error = error
        for record in reversed(directory_records):
            descriptor = record.get("descriptor", -1)
            if descriptor < 0:
                continue
            closed, error = _cleanup_owned_fd(
                descriptor, record["owned_identity"],
                "private exec source directory cleanup " + record["path"],
            )
            if closed:
                record["descriptor"] = -1
            if error is not None and cleanup_error is None:
                cleanup_error = error
        if cleanup_error is not None:
            raise cleanup_error


def _retained_private_seal(
    directories: Dict[str, List[int]],
    authority_files: Sequence[Tuple[Path, List[int], bytes, str]],
    capture_files: Sequence[Tuple[Path, List[int], bytes, str]],
    capture_namespaces: Sequence[Tuple[Path, List[str]]],
) -> None:
    """Seal every root after parent-side path/listing/close callbacks.

    A fresh isolated interpreter executes exact sealed helper bytes and sees
    only the bounded expectation memfd, a one-byte start protocol, and the
    retained read descriptors.  Parent close callbacks complete before the
    helper starts its decisive descriptor-only observations.
    """

    no_follow = getattr(os, "O_NOFOLLOW", 0)
    directory_only = getattr(os, "O_DIRECTORY", 0)
    if not no_follow or not directory_only:
        raise WitnessError("private aggregate O_NOFOLLOW/openat support is required")
    directory_flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | no_follow | directory_only
    leaf_flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | no_follow
    directory_records = []  # type: List[Dict[str, Any]]
    directory_by_path = {}  # type: Dict[str, Dict[str, Any]]
    file_records = []  # type: List[Dict[str, Any]]
    namespace_records = []  # type: List[Dict[str, Any]]
    opened = True
    try:
        ordered_directories = sorted(
            directories.keys(), key=lambda item: (len(Path(item).parts), item)
        )
        for key in ordered_directories:
            path = Path(key)
            if not path.is_absolute():
                raise WitnessError("private aggregate directory is not absolute")
            if key == path.anchor:
                named = os.lstat(key)
                descriptor = os.open(key, directory_flags)
            else:
                parent_key = str(path.parent)
                if parent_key not in directory_by_path:
                    raise WitnessError("private aggregate parent is unavailable: " + key)
                parent = directory_by_path[parent_key]["descriptor"]
                named = os.stat(path.name, dir_fd=parent, follow_symlinks=False)
                descriptor = os.open(path.name, directory_flags, dir_fd=parent)
            retained = os.fstat(descriptor)
            record = {
                "descriptor": descriptor,
                "identity": list(directories[key]),
                "owned_identity": _directory_identity(retained),
                "path": key,
            }
            directory_records.append(record)
            if stat.S_ISLNK(named.st_mode) or not stat.S_ISDIR(named.st_mode):
                raise WitnessError("private aggregate directory changed type: " + key)
            _require_exact_json(
                _directory_identity(named), directories[key],
                "private aggregate named directory " + key,
            )
            _require_exact_json(
                _directory_identity(retained), directories[key],
                "private aggregate retained directory " + key,
            )
            directory_by_path[key] = record

        all_files = list(authority_files) + list(capture_files)
        seen_files = {}  # type: Dict[str, Tuple[List[int], bytes]]
        for path, identity, data, label in all_files:
            key = str(path)
            if key in seen_files:
                _require_exact_json(
                    seen_files[key], (identity, data),
                    "private aggregate duplicate leaf " + key,
                )
                continue
            parent_key = str(path.parent)
            if parent_key not in directory_by_path:
                raise WitnessError("private aggregate leaf parent is unavailable: " + key)
            parent = directory_by_path[parent_key]["descriptor"]
            named = os.stat(path.name, dir_fd=parent, follow_symlinks=False)
            if stat.S_ISLNK(named.st_mode) or not stat.S_ISREG(named.st_mode):
                raise WitnessError("{0} private aggregate type differs".format(label))
            descriptor = os.open(path.name, leaf_flags, dir_fd=parent)
            retained = os.fstat(descriptor)
            record = {
                "bytes": data,
                "descriptor": descriptor,
                "identity": list(identity),
                "label": label,
                "owned_identity": _file_identity(retained),
                "path": key,
            }
            file_records.append(record)
            if retained.st_nlink != 1:
                raise WitnessError("{0} private aggregate hardlink differs".format(label))
            _require_exact_json(
                _file_identity(named), identity,
                label + " private aggregate named identity",
            )
            _require_exact_json(
                _file_identity(retained), identity,
                label + " private aggregate retained identity",
            )
            seen_files[key] = (identity, data)

        for root, members in capture_namespaces:
            key = str(root)
            if key not in directory_by_path:
                raise WitnessError("private capture namespace root is unavailable")
            descriptor = directory_by_path[key]["descriptor"]
            _require_exact_json(
                sorted(os.listdir(descriptor)), list(members),
                "private aggregate capture namespace " + key,
            )
            namespace_records.append(
                {"descriptor": descriptor, "members": list(members), "path": key}
            )

        _run_exec_seal(directory_records, file_records, namespace_records)
        opened = False
    except WitnessError:
        raise
    except (OSError, TypeError, ValueError) as error:
        raise WitnessError("private aggregate seal failed: {0}".format(error))
    finally:
        if opened:
            cleanup_error = None  # type: Optional[BaseException]
            for record in file_records:
                descriptor = record.get("descriptor", -1)
                if descriptor >= 0:
                    closed, error = _cleanup_owned_fd(
                        descriptor, record["owned_identity"],
                        record["label"] + " retained cleanup",
                    )
                    if closed:
                        record["descriptor"] = -1
                    if error is not None and cleanup_error is None:
                        cleanup_error = error
            for record in reversed(directory_records):
                descriptor = record.get("descriptor", -1)
                if descriptor >= 0:
                    closed, error = _cleanup_owned_fd(
                        descriptor, record["owned_identity"],
                        "private aggregate directory cleanup " + record["path"],
                    )
                    if closed:
                        record["descriptor"] = -1
                    if error is not None and cleanup_error is None:
                        cleanup_error = error
            if cleanup_error is not None:
                raise WitnessError(
                    "private aggregate descriptor cleanup failed: {0}".format(
                        cleanup_error
                    )
                )


def _aggregate_post_close_sweep(
    authority_snapshots: Sequence[Dict[str, Any]],
    capture_snapshots: Sequence[Dict[str, Any]],
) -> None:
    """Perform one aggregate sweep after every retained descriptor is closed.

    All capture namespace listings run before any leaf is finalized.  The
    authority leaves are then byte-replayed before capture leaves, so a
    capture-listing mutation of authority and an authority-replay mutation of
    capture are both observed.  No owned os.close or namespace listing occurs
    after leaf finalization begins; a final identity pass also detects changes
    caused by the short-lived byte readers' teardown.
    """

    authority_files = []  # type: List[Tuple[Path, List[int], bytes, str]]
    capture_files = []  # type: List[Tuple[Path, List[int], bytes, str]]
    directories = {}  # type: Dict[str, List[int]]
    capture_namespaces = []  # type: List[Tuple[Path, List[str]]]

    for snapshot in authority_snapshots:
        if type(snapshot) is not dict or type(snapshot.get("directories")) is not list:
            raise WitnessError("authority aggregate snapshot shape differs")
        for directory in snapshot["directories"]:
            path = Path(directory["path"])
            key = str(path)
            identity = list(directory["identity"])
            if key in directories:
                _require_exact_json(directories[key], identity,
                                    "aggregate directory identity " + key)
            else:
                directories[key] = identity
        leaf = snapshot.get("leaf")
        expected_bytes = snapshot.get("expected_bytes")
        if type(leaf) is not dict or type(expected_bytes) is not bytes:
            raise WitnessError("authority aggregate leaf bytes are unavailable")
        authority_files.append(
            (Path(leaf["path"]), list(leaf["identity"]), expected_bytes,
             str(snapshot["label"]))
        )

    for snapshot in capture_snapshots:
        if type(snapshot) is not dict or type(snapshot.get("directories")) is not list:
            raise WitnessError("capture aggregate snapshot shape differs")
        for directory in snapshot["directories"]:
            path = Path(directory["path"])
            key = str(path)
            identity = list(directory["identity"])
            if key in directories:
                _require_exact_json(directories[key], identity,
                                    "aggregate directory identity " + key)
            else:
                directories[key] = identity
        root = Path(snapshot["root"])
        members = list(snapshot["members"])
        expected_bytes_by_name = snapshot.get("expected_bytes")
        identities = snapshot.get("identities")
        if type(expected_bytes_by_name) is not dict or type(identities) is not dict:
            raise WitnessError("capture aggregate byte authority is unavailable")
        capture_namespaces.append((root, members))
        for name in members:
            capture_files.append(
                (
                    root / name,
                    list(identities[name]),
                    expected_bytes_by_name[name],
                    "capture member " + name,
                )
            )

    # Namespace operations are intentionally completed before any leaf is
    # finalized.  Exact listings bind the accepted member set at each
    # checkpoint; stable directory identity binds the same path components.
    try:
        for root, members in capture_namespaces:
            _require_exact_json(
                sorted(os.listdir(str(root))), members,
                "aggregate capture namespace " + str(root),
            )
    except WitnessError:
        raise
    except (OSError, TypeError, ValueError) as error:
        raise WitnessError("aggregate namespace replay failed: {0}".format(error))

    for path, identity, data, label in authority_files:
        _aggregate_read_exact(path, identity, data, label)
    for path, identity, data, label in capture_files:
        _aggregate_read_exact(path, identity, data, label)

    # This pass has no owned-descriptor teardown or namespace listing after an
    # earlier root is checked.  Stable directory identity rejects component
    # replacement; full leaf identity binds content metadata after all reads.
    try:
        for key in sorted(directories):
            metadata = os.lstat(key)
            if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISDIR(metadata.st_mode):
                raise WitnessError("aggregate directory changed type: " + key)
            _require_exact_json(
                _directory_identity(metadata), directories[key],
                "aggregate final directory " + key,
            )
        for path, identity, _, label in authority_files + capture_files:
            metadata = os.lstat(str(path))
            if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISREG(metadata.st_mode):
                raise WitnessError("{0} aggregate final type differs".format(label))
            _require_exact_json(
                _file_identity(metadata), identity,
                label + " aggregate final identity",
            )
    except WitnessError:
        raise
    except (OSError, TypeError, ValueError) as error:
        raise WitnessError("aggregate final identity sweep failed: {0}".format(error))

    _retained_private_seal(
        directories, authority_files, capture_files, capture_namespaces
    )


def _select_exact_rows(actual: Any, expected: Any, label: str) -> None:
    if type(actual) is not list or type(expected) is not list:
        raise WitnessError("{0} rows must be lists".format(label))
    indexed = {}  # type: Dict[str, Dict[str, Any]]
    for row in actual:
        if type(row) is not dict or type(row.get("id")) is not str:
            raise WitnessError("{0} has an invalid identity".format(label))
        if row["id"] in indexed:
            raise WitnessError("{0} has a duplicate identity".format(label))
        indexed[row["id"]] = row
    seen = []  # type: List[str]
    for row in expected:
        if type(row) is not dict or type(row.get("id")) is not str:
            raise WitnessError("{0} authority has an invalid row".format(label))
        row_id = row["id"]
        if row_id in seen or row_id not in indexed:
            raise WitnessError("{0} authority row is duplicate or absent".format(label))
        seen.append(row_id)
        _require_exact_json(indexed[row_id], row, label + " row " + row_id)


def _expected_claims() -> Dict[str, bool]:
    return {
        "credit_eligible": False,
        "current_head_provenance_proven": False,
        "current_head_runtime_reachability_proven": False,
        "durable_evidence": False,
        "failure_semantics_covered": False,
        "fp0006_complete": False,
        "gate_pass": False,
        "independent_review_complete": False,
        "legacy_runtime_executed": False,
        "native_module_runtime_executed": False,
        "native_runtime_executed": False,
        "runtime_reachability_proven": False,
        "tracker_credit": False,
    }


def _expected_vectors() -> List[Dict[str, Any]]:
    definitions = (
        (
            "AT-IHK-IOCTL-C5F3D68589",
            0,
            "BHV-IHK-IOCTL-IHK_OS_QUERY_STATUS-C5F3D68589",
            1124867,
            "IHK_OS_QUERY_STATUS",
            "query-status-arg0",
        ),
        (
            "AT-IHK-IOCTL-C5F3D68589",
            18446744073709551615,
            "BHV-IHK-IOCTL-IHK_OS_QUERY_STATUS-C5F3D68589",
            1124867,
            "IHK_OS_QUERY_STATUS",
            "query-status-arg-u64-max",
        ),
        (
            "AT-IHK-IOCTL-242ED0E83C",
            0,
            "BHV-IHK-IOCTL-IHK_OS_STATUS-242ED0E83C",
            1124884,
            "IHK_OS_STATUS",
            "status-alias-arg0",
        ),
        (
            "AT-IHK-IOCTL-242ED0E83C",
            18446744073709551615,
            "BHV-IHK-IOCTL-IHK_OS_STATUS-242ED0E83C",
            1124884,
            "IHK_OS_STATUS",
            "status-alias-arg-u64-max",
        ),
    )
    vectors = []  # type: List[Dict[str, Any]]
    for sequence, definition in enumerate(definitions):
        acceptance, argument, behavior, request, request_name, vector_id = definition
        vectors.append(
            {
                "acceptance_test_id": acceptance,
                "argument": argument,
                "behavior_id": behavior,
                "expected_errno": 0,
                "expected_interface_return": 5,
                "expected_normalized_return": 5,
                "expected_status_after": 5,
                "expected_status_before": 5,
                "request": request,
                "request_name": request_name,
                "sequence": sequence,
                "vector_id": vector_id,
            }
        )
    return vectors


def _verify_legacy_authority(
    contract: Dict[str, Any], inputs: Dict[str, bytes]
) -> None:
    expected = contract["legacy_behavior_authority"]
    actual = _load_json_bytes(
        inputs["legacy_behavior_contract"], "legacy behavior contract"
    )
    authority = expected["authority"]
    _require_exact_json(actual.get("schema_version"), authority["schema_version"],
                        "legacy schema")
    _require_exact_json(actual.get("generator"), authority["generator"],
                        "legacy generator")
    _require_exact_json(
        actual.get("inventory_file_sha256"),
        expected["inputs"]["inventory"]["sha256"],
        "legacy inventory binding",
    )
    _require_exact_json(
        actual.get("policy_file_sha256"),
        expected["inputs"]["policy"]["sha256"],
        "legacy policy binding",
    )
    _require_exact_json(actual.get("policy_id"),
                        expected["inputs"]["policy"]["policy_id"],
                        "legacy policy identity")
    _require_exact_json(actual.get("provenance"), expected["provenance"],
                        "legacy provenance")
    _select_exact_rows(actual.get("acceptance_tests"), expected["acceptance_tests"],
                       "legacy acceptance")
    _select_exact_rows(actual.get("behaviors"), expected["behaviors"],
                       "legacy behavior")


def _verify_current_semantics(inputs: Dict[str, bytes]) -> None:
    abi = _load_json_bytes(inputs["abi_contract"], "shared ABI contract")
    _require_exact_json(
        {
            "IHK_OS_QUERY_STATUS": abi["constant_bindings"]["host_user"].get(
                "IHK_OS_QUERY_STATUS"
            ),
            "IHK_OS_STATUS": abi["constant_bindings"]["host_user"].get(
                "IHK_OS_STATUS"
            ),
            "IHK_OS_STATUS_RUNNING": abi["constant_bindings"]["status"].get(
                "IHK_OS_STATUS_RUNNING"
            ),
        },
        {
            "IHK_OS_QUERY_STATUS": 1124867,
            "IHK_OS_STATUS": 1124884,
            "IHK_OS_STATUS_RUNNING": 5,
        },
        "shared ABI status constants",
    )

    ioctl_foundation = _load_json_bytes(
        inputs["ioctl_foundation"], "ioctl foundation"
    )
    _require_exact_json(
        {
            "IHK_OS_QUERY_STATUS": ioctl_foundation["behavior"]["commands"].get(
                "IHK_OS_QUERY_STATUS"
            ),
            "IHK_OS_STATUS": ioctl_foundation["behavior"]["commands"].get(
                "IHK_OS_STATUS"
            ),
        },
        {"IHK_OS_QUERY_STATUS": 1124867, "IHK_OS_STATUS": 1124884},
        "ioctl foundation aliases",
    )
    _require_exact_json(ioctl_foundation["behavior"].get("status_return"),
                        "direct-enum-value-for-both-aliases",
                        "ioctl status return policy")
    _require_exact_json(ioctl_foundation["behavior"].get("user_copy"),
                        "none-for-this-scalar-subset", "ioctl user-copy policy")
    _require_exact_json(ioctl_foundation["implementation"].get("registration_supported"),
                        False, "ioctl registration boundary")
    _require_exact_json(ioctl_foundation["readiness"].get("credit_eligible"),
                        False, "ioctl credit boundary")

    registry_foundation = _load_json_bytes(
        inputs["os_registry_foundation"], "OS registry foundation"
    )
    _require_exact_json(
        registry_foundation["canonical_abi"]["status_values"].get(
            "IHK_OS_STATUS_RUNNING"
        ),
        5,
        "registry RUNNING value",
    )
    _require_exact_json(registry_foundation["readiness"].get("credit_eligible"),
                        False, "registry credit boundary")

    abi_source = inputs["abi_source"].decode("utf-8")
    dispatcher = inputs["rust_dispatcher"].decode("utf-8")
    registry = inputs["registry_source"].decode("utf-8")
    required_source_fragments = (
        (abi_source, "pub const IHK_OS_QUERY_STATUS: u32 = 0x0011_2a03;",
         "ABI QUERY_STATUS declaration"),
        (abi_source, "pub const IHK_OS_STATUS: u32 = 0x0011_2a14;",
         "ABI STATUS declaration"),
        (abi_source, "pub const IHK_OS_STATUS_RUNNING: i32 = 5;",
         "ABI RUNNING declaration"),
        (dispatcher, "IHK_OS_QUERY_STATUS | IHK_OS_STATUS => Ok(OsIoctl::QueryStatus)",
         "dispatcher alias decode"),
        (dispatcher, "_argument: u64", "dispatcher ignored argument"),
        (dispatcher, ".snapshot(handle)", "dispatcher snapshot source"),
        (dispatcher, ".map(|snapshot| snapshot.status as i64)",
         "dispatcher direct status result"),
        (registry, "Running = 5", "registry RUNNING representation"),
        (registry, "pub(crate) fn transition(", "registry transition API"),
        (registry, "pub(crate) fn snapshot(", "registry snapshot API"),
    )
    for text, fragment, label in required_source_fragments:
        if text.count(fragment) != 1:
            raise WitnessError("{0} is not uniquely present".format(label))


def _load_authority(
    repo: Path, contract_path: Path = DEFAULT_CONTRACT
) -> Tuple[Dict[str, Any], bytes, Dict[str, Dict[str, Any]], List[Dict[str, Any]]]:
    expected_relative = "host-kernel/contracts/fp0006-ihk-os-status-alias-v1.json"
    expected_contract_sha256 = "369084c6af4184c20b40cce189dcca92f01711da82398a976d128f794d32c679"
    expected_contract_size = 10968
    if Path(contract_path).as_posix() != expected_relative:
        raise WitnessError("status-alias contract path differs from fixed authority")
    repo = Path(repo)
    snapshots = []  # type: List[Dict[str, Any]]
    contract_bytes = _read_rooted_file(
        repo,
        expected_relative,
        "FP-0006 status-alias contract",
        expected_contract_size,
        snapshots=snapshots,
    )
    if contract_bytes is None:
        raise WitnessError("status-alias contract is unavailable")
    _bind_closed_file_bytes(
        snapshots, contract_bytes, "FP-0006 status-alias contract"
    )
    _require_exact_json(len(contract_bytes), expected_contract_size, "contract size")
    _require_exact_json(_sha256(contract_bytes), expected_contract_sha256,
                        "contract digest")
    contract = _load_json_bytes(contract_bytes, "FP-0006 status-alias contract")
    if contract_bytes != _pretty_json(contract):
        raise WitnessError("status-alias contract is not canonical pretty JSON")
    _require_keys(
        contract,
        (
            "abi_authority", "artifact_contract", "claims", "contract_id",
            "frozen_inputs", "gate", "legacy_behavior_authority", "limitations",
            "native_semantics", "producers", "schema_version", "schemas", "vectors",
        ),
        "status-alias contract",
    )
    _require_exact_json(contract["schema_version"], 1, "contract schema version")
    _require_exact_json(
        contract["contract_id"], "fp-0006-ihk-os-status-alias-v1",
        "contract identity",
    )
    _require_exact_json(contract["claims"], _expected_claims(), "noncrediting claims")
    _require_exact_json(
        contract["gate"],
        {"gate_id": "FP-0006", "points_awarded": 0, "status": "IN_PROGRESS"},
        "gate boundary",
    )
    _require_exact_json(
        contract["artifact_contract"]["result_authority"],
        {
            "durable_artifact_required": True,
            "independent_review_required": True,
            "path": None,
            "status": "required-missing",
        },
        "result authority boundary",
    )
    _require_exact_json(
        contract["abi_authority"],
        {
            "requests": {"IHK_OS_QUERY_STATUS": 1124867, "IHK_OS_STATUS": 1124884},
            "running_name": "RUNNING",
            "running_status": 5,
            "word_bits": 64,
        },
        "ABI authority",
    )
    _require_exact_json(contract["vectors"], _expected_vectors(), "vector authority")
    _require_exact_json(
        contract["schemas"],
        {
            "raw": {
                "exact_keys": ["argument", "request", "sequence", "vector_id"],
                "record_count": 4,
            },
            "result": {
                "exact_keys": [
                    "errno", "interface_return", "normalized_return", "sequence",
                    "surface", "vector_id",
                ],
                "record_count": 4,
            },
            "state_ledger": {
                "exact_keys": [
                    "minor", "phase", "sequence", "status", "status_name",
                    "surface", "vector_id",
                ],
                "record_count": 8,
            },
        },
        "capture schemas",
    )

    inputs = {}  # type: Dict[str, bytes]
    summaries = {}  # type: Dict[str, Dict[str, Any]]
    frozen_inputs = contract["frozen_inputs"]
    if type(frozen_inputs) is not dict:
        raise WitnessError("frozen inputs must be an object")
    for input_id in sorted(frozen_inputs):
        binding = frozen_inputs[input_id]
        _require_keys(binding, ("path", "sha256", "size"),
                      "frozen input " + input_id)
        size = _require_int(binding["size"], "frozen input size " + input_id)
        if type(binding["path"]) is not str or type(binding["sha256"]) is not str:
            raise WitnessError("frozen input binding types differ: " + input_id)
        data = _read_rooted_file(
            repo, binding["path"], "frozen input " + input_id, size,
            snapshots=snapshots,
        )
        if data is None:
            raise WitnessError("frozen input is unavailable: " + input_id)
        _bind_closed_file_bytes(snapshots, data, "frozen input " + input_id)
        _require_exact_json(len(data), size, "frozen input size " + input_id)
        _require_exact_json(_sha256(data), binding["sha256"],
                            "frozen input digest " + input_id)
        inputs[input_id] = data
        summaries[input_id] = {
            "path": binding["path"], "sha256": _sha256(data), "size": len(data)
        }

    for producer_id in ("legacy", "native"):
        binding = contract["producers"][producer_id]
        _require_keys(binding, ("path", "sha256", "size", "surface"),
                      producer_id + " producer")
        size = _require_int(binding["size"], producer_id + " producer size")
        data = _read_rooted_file(
            repo, binding["path"], producer_id + " producer", size,
            snapshots=snapshots,
        )
        if data is None:
            raise WitnessError(producer_id + " producer is unavailable")
        _bind_closed_file_bytes(snapshots, data, producer_id + " producer")
        _require_exact_json(len(data), size, producer_id + " producer size")
        _require_exact_json(_sha256(data), binding["sha256"],
                            producer_id + " producer digest")
        summaries[producer_id + "_producer"] = {
            "path": binding["path"], "sha256": _sha256(data), "size": len(data)
        }

    _verify_legacy_authority(contract, inputs)
    _verify_current_semantics(inputs)
    return contract, contract_bytes, summaries, snapshots


def _validate_contract_internal(
    repo: Path = ROOT, contract_path: Path = DEFAULT_CONTRACT
) -> Dict[str, Any]:
    contract, contract_bytes, inputs, snapshots = _load_authority(repo, contract_path)
    _aggregate_post_close_sweep(snapshots, ())
    return {
        "claims": copy.deepcopy(contract["claims"]),
        "contract_id": contract["contract_id"],
        "contract_sha256": _sha256(contract_bytes),
        "frozen_inputs": inputs,
        "result_authority": contract["artifact_contract"]["result_authority"]["status"],
        "vector_count": len(contract["vectors"]),
    }


def _load_json_lines(data: bytes, label: str) -> List[Dict[str, Any]]:
    if not data.endswith(b"\n") or data.startswith(b"\xef\xbb\xbf"):
        raise WitnessError("{0} must be UTF-8 JSON lines ending in LF".format(label))
    lines = data.splitlines(True)
    if not lines or any(line == b"\n" or not line.endswith(b"\n") for line in lines):
        raise WitnessError("{0} has a blank or unterminated record".format(label))
    records = []  # type: List[Dict[str, Any]]
    for index, line in enumerate(lines):
        record = _load_json_bytes(line, "{0} record {1}".format(label, index))
        if line != _canonical_json(record):
            raise WitnessError("{0} record {1} is not canonical".format(label, index))
        records.append(record)
    return records


def _expected_raw(authority: Dict[str, Any]) -> List[Dict[str, Any]]:
    return [
        {
            "argument": vector["argument"],
            "request": vector["request"],
            "sequence": vector["sequence"],
            "vector_id": vector["vector_id"],
        }
        for vector in authority["vectors"]
    ]


def _validate_raw(data: bytes, authority: Dict[str, Any]) -> List[Dict[str, Any]]:
    records = _load_json_lines(data, "raw stream")
    schema = authority["schemas"]["raw"]
    _require_exact_json(len(records), schema["record_count"], "raw record count")
    _require_exact_json(records, _expected_raw(authority), "raw vector order")
    for record in records:
        _require_keys(record, schema["exact_keys"], "raw record")
        for key in ("argument", "request", "sequence"):
            _require_int(record[key], "raw " + key)
        if type(record["vector_id"]) is not str:
            raise WitnessError("raw vector_id must be exact text")
    return records


def _validate_results(
    data: bytes, surface: str, authority: Dict[str, Any]
) -> List[Dict[str, Any]]:
    records = _load_json_lines(data, "result stream")
    schema = authority["schemas"]["result"]
    expected = []  # type: List[Dict[str, Any]]
    for vector in authority["vectors"]:
        expected.append(
            {
                "errno": vector["expected_errno"],
                "interface_return": vector["expected_interface_return"],
                "normalized_return": vector["expected_normalized_return"],
                "sequence": vector["sequence"],
                "surface": surface,
                "vector_id": vector["vector_id"],
            }
        )
    _require_exact_json(len(records), schema["record_count"], "result record count")
    _require_exact_json(records, expected, "result vector order and values")
    for record in records:
        _require_keys(record, schema["exact_keys"], "result record")
        for key in ("errno", "interface_return", "normalized_return", "sequence"):
            _require_int(record[key], "result " + key)
    return records


def _validate_ledger(
    data: bytes, surface: str, authority: Dict[str, Any]
) -> List[Dict[str, Any]]:
    records = _load_json_lines(data, "state ledger")
    schema = authority["schemas"]["state_ledger"]
    expected = []  # type: List[Dict[str, Any]]
    for vector in authority["vectors"]:
        for phase in ("before", "after"):
            expected.append(
                {
                    "minor": 0,
                    "phase": phase,
                    "sequence": vector["sequence"],
                    "status": vector[
                        "expected_status_before" if phase == "before"
                        else "expected_status_after"
                    ],
                    "status_name": "RUNNING",
                    "surface": surface,
                    "vector_id": vector["vector_id"],
                }
            )
    _require_exact_json(len(records), schema["record_count"], "state-ledger count")
    _require_exact_json(records, expected, "state-ledger order and values")
    for record in records:
        _require_keys(record, schema["exact_keys"], "state-ledger record")
        for key in ("minor", "sequence", "status"):
            _require_int(record[key], "state-ledger " + key)
    for index in range(0, len(records), 2):
        before = dict(records[index])
        after = dict(records[index + 1])
        before.pop("phase")
        after.pop("phase")
        if not _exact_json_equal(before, after):
            raise WitnessError("status vector changed the pre/post state ledger")
    return records


def _review_surface_with_authority(
    authority: Dict[str, Any], path: Path, surface: str,
    snapshots: List[Dict[str, Any]],
) -> Tuple[Dict[str, Any], List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
    artifact = authority["artifact_contract"]
    if surface not in (artifact["legacy_surface"], artifact["native_surface"]):
        raise WitnessError("capture surface is not recognized")
    mode = artifact["directory_member_mode"]
    if type(mode) is not str or re.fullmatch(r"0[0-7]{3}", mode) is None:
        raise WitnessError("capture member mode authority is invalid")
    maximum = _require_int(artifact["maximum_member_bytes"], "maximum member bytes")
    members = tuple(artifact["capture_members"])
    files = _read_capture_members(
        Path(path), members, int(mode, 8), maximum, snapshots=snapshots
    )
    _bind_closed_capture_bytes(snapshots, files)
    raw = _validate_raw(files["raw.jsonl"], authority)
    results = _validate_results(files["result.jsonl"], surface, authority)
    ledger = _validate_ledger(files["state-ledger.jsonl"], surface, authority)
    rows = [
        {"name": name, "sha256": _sha256(files[name]), "size": len(files[name])}
        for name in members
    ]
    closure = _sha256(_canonical_json(rows))
    if HEX64.fullmatch(closure) is None:
        raise WitnessError("capture closure digest is invalid")
    summary = {
        "artifact_content_closure_sha256": closure,
        "capture_schema_validated": True,
        "claims": copy.deepcopy(authority["claims"]),
        "contract_id": authority["contract_id"],
        "files": rows,
        "result_authority": artifact["result_authority"]["status"],
        "status": "CAPTURED_UNREVIEWED_NONCREDITING",
        "surface": surface,
        "validated_result_count": len(results),
        "validated_state_record_count": len(ledger),
        "vector_count": len(raw),
    }
    return summary, raw, results, ledger


def _review_surface_internal(
    repo: Path, path: Path, surface: str,
    contract_path: Path = DEFAULT_CONTRACT,
) -> Dict[str, Any]:
    if type(surface) is not str:
        raise WitnessError("surface must be exactly legacy or native")
    if surface == "legacy":
        exact_surface = "legacy-live-ioctl"
    elif surface == "native":
        exact_surface = "native-rust-source-fixture"
    else:
        raise WitnessError("surface must be exactly legacy or native")
    authority, _, _, authority_snapshots = _load_authority(repo, contract_path)
    capture_snapshots = []  # type: List[Dict[str, Any]]
    summary, _, _, _ = _review_surface_with_authority(
        authority, Path(path), exact_surface, capture_snapshots
    )
    _aggregate_post_close_sweep(authority_snapshots, capture_snapshots)
    return summary


def _without_surface(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    normalized = []  # type: List[Dict[str, Any]]
    for record in records:
        item = dict(record)
        item.pop("surface")
        normalized.append(item)
    return normalized


def _review_pair_internal(
    repo: Path, legacy_path: Path, native_path: Path,
    contract_path: Path = DEFAULT_CONTRACT,
) -> Dict[str, Any]:
    authority, _, _, authority_snapshots = _load_authority(repo, contract_path)
    capture_snapshots = []  # type: List[Dict[str, Any]]
    legacy, legacy_raw, legacy_results, legacy_ledger = _review_surface_with_authority(
        authority, Path(legacy_path), "legacy-live-ioctl", capture_snapshots
    )
    native, native_raw, native_results, native_ledger = _review_surface_with_authority(
        authority, Path(native_path), "native-rust-source-fixture", capture_snapshots
    )
    _require_exact_json(legacy_raw, native_raw, "legacy/native raw vectors")
    _require_exact_json(_without_surface(legacy_results),
                        _without_surface(native_results),
                        "legacy/native result semantics")
    _require_exact_json(_without_surface(legacy_ledger),
                        _without_surface(native_ledger),
                        "legacy/native state semantics")
    _aggregate_post_close_sweep(authority_snapshots, capture_snapshots)
    return {
        "artifact_pair_validated": True,
        "claims": copy.deepcopy(authority["claims"]),
        "contract_id": authority["contract_id"],
        "legacy": legacy,
        "native": native,
        "result_authority": authority["artifact_contract"]["result_authority"]["status"],
        "status": "CAPTURED_UNREVIEWED_NONCREDITING",
        "vector_count": len(authority["vectors"]),
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command")
    contract = subparsers.add_parser("check-contract")
    contract.add_argument("--repo", type=Path, default=ROOT)
    surface = subparsers.add_parser("review-surface")
    surface.add_argument("--repo", type=Path, default=ROOT)
    surface.add_argument("--surface", choices=("legacy", "native"), required=True)
    surface.add_argument("--artifact", type=Path, required=True)
    pair = subparsers.add_parser("review-pair")
    pair.add_argument("--repo", type=Path, default=ROOT)
    pair.add_argument("--legacy", type=Path, required=True)
    pair.add_argument("--native", type=Path, required=True)
    return parser


def _require_cli_noncrediting_result(command: str, result: Dict[str, Any]) -> None:
    expected_claims = {
        "credit_eligible": False,
        "current_head_provenance_proven": False,
        "current_head_runtime_reachability_proven": False,
        "durable_evidence": False,
        "failure_semantics_covered": False,
        "fp0006_complete": False,
        "gate_pass": False,
        "independent_review_complete": False,
        "legacy_runtime_executed": False,
        "native_module_runtime_executed": False,
        "native_runtime_executed": False,
        "runtime_reachability_proven": False,
        "tracker_credit": False,
    }
    if type(result) is not dict:
        raise WitnessError("isolated CLI result is not an object")
    claims = result.get("claims")
    if not _exact_json_equal(claims, expected_claims):
        raise WitnessError("isolated CLI claims are not exact false authority")
    if result.get("contract_id") != "fp-0006-ihk-os-status-alias-v1":
        raise WitnessError("isolated CLI contract identity differs")
    if result.get("result_authority") != "required-missing":
        raise WitnessError("isolated CLI result authority overclaims")
    if command == "check-contract":
        if result.get("status") != "CONTRACT_VALIDATED_NONCREDITING":
            raise WitnessError("isolated contract status differs")
    elif command == "review-surface":
        if (
            result.get("status") != "CAPTURED_UNREVIEWED_NONCREDITING"
            or result.get("capture_schema_validated") is not True
        ):
            raise WitnessError("isolated surface status differs")
    elif command == "review-pair":
        if (
            result.get("status") != "CAPTURED_UNREVIEWED_NONCREDITING"
            or result.get("artifact_pair_validated") is not True
        ):
            raise WitnessError("isolated pair status differs")
        for name in ("legacy", "native"):
            nested = result.get(name)
            if type(nested) is not dict or not _exact_json_equal(
                nested.get("claims"), expected_claims
            ):
                raise WitnessError("isolated pair nested claims differ")
    else:
        raise WitnessError("isolated CLI command differs")


def _verify_direct_process_invocation() -> None:
    if sys.flags.isolated != 1:
        raise WitnessError("authoritative review requires python3 -I")
    current_main = sys.modules.get("__main__")
    if (
        current_main is None
        or getattr(current_main, "__dict__", None) is not globals()
        or __spec__ is not None
        or __package__ not in (None, "")
    ):
        raise WitnessError("authoritative review requires direct script execution")
    try:
        with open("/proc/self/cmdline", "rb", buffering=0) as source:
            raw = source.read(16385)
    except (OSError, TypeError, ValueError) as error:
        raise WitnessError("cannot bind isolated process command: {0}".format(error))
    if not raw or len(raw) > 16384 or not raw.endswith(b"\0"):
        raise WitnessError("isolated process command is outside its bound")
    fields = raw[:-1].split(b"\0")
    expected = [os.fsencode(item) for item in sys.argv]
    if (
        len(fields) < 3
        or fields[1] != b"-I"
        or fields[2:] != expected
        or any(item in (b"-c", b"-m") for item in fields[1:3])
    ):
        raise WitnessError("isolated process command does not name the direct CLI")


def _cli_entry() -> int:
    source = None  # type: Optional[Dict[str, Any]]
    try:
        _verify_direct_process_invocation()
        source = _open_verified_cli_source()
        _load_exact_security_primitives(source["path"])
        parser = _build_parser()
        arguments = parser.parse_args(sys.argv[1:])
        if arguments.command == "check-contract":
            result = _validate_contract_internal(arguments.repo)
            result["status"] = "CONTRACT_VALIDATED_NONCREDITING"
        elif arguments.command == "review-surface":
            result = _review_surface_internal(
                arguments.repo, arguments.artifact, arguments.surface
            )
        elif arguments.command == "review-pair":
            result = _review_pair_internal(
                arguments.repo, arguments.legacy, arguments.native
            )
        else:
            parser.error("a command is required")
            return 2
        _require_cli_noncrediting_result(arguments.command, result)
        output = _canonical_json(result)
        if not output or len(output) > 1024 * 1024:
            raise WitnessError("isolated CLI output exceeds its bound")
        _verify_cli_source_final(source)
    except (WitnessError, OSError, TypeError, ValueError) as error:
        print("fp0006 status-alias witness error: {0}".format(error), file=sys.stderr)
        return 1
    finally:
        if source is not None and source.get("descriptor", -1) >= 0:
            os.close(source["descriptor"])
            source["descriptor"] = -1
    sys.stdout.write(output.decode("utf-8"))
    return 0


if __name__ == "__main__":
    sys.exit(_cli_entry())
else:
    # Importing callers receive constants and pure formatting helpers only.
    # No callable validation, review, envelope, or executable entry authority
    # remains available for __name__/global/code/default/class rebinding.
    for _private_authority_name in (
        "_cli_entry",
        "_load_authority",
        "_require_cli_noncrediting_result",
        "_review_pair_internal",
        "_review_surface_internal",
        "_review_surface_with_authority",
        "_validate_contract_internal",
        "_verify_direct_process_invocation",
    ):
        globals().pop(_private_authority_name, None)
    del _private_authority_name
