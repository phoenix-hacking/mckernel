#!/usr/bin/env python3
"""Capture the two still-missing RK-001 embedded-archive child inventories.

This is an additive, non-crediting v2 scaffold.  It binds the exact frozen
stablelists and kabi-dw containers, inventories tar.xz members sequentially,
and emits deterministic machine capture.  It never treats capture as legal
review, durable archival, campaign closure, or RK-001 credit.
"""

from __future__ import print_function

import argparse
import copy
import gzip
import hashlib
import json
import os
import posixpath
import re
import shutil
import stat
import sys
import tarfile
import tempfile
import unicodedata
import zlib
from pathlib import Path, PurePosixPath


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = Path(
    "host-kernel/rocky/evidence/"
    "rk001-license-child-inventory-contract-ef58-v2.json"
)
SCHEMA_VERSION = 2
CONTRACT_ID = "rk-001-license-child-inventory-ef58860e-v2"
SOURCE_COMMIT = "ef58860e4806ee16e2c506e4e93c7b6ad8ad8f4b"
EXPECTED_CONTAINER_IMAGE = (
    "rockylinux/rockylinux:10.2@sha256:"
    "e372170ca8630f0f03e9b70fdd0bf4a3ce3426b0de7cdba615f06337389de176"
)
EXPECTED_REPOSITORY = "phoenix-hacking/mckernel"

MAX_CONTRACT_BYTES = 128 * 1024
MAX_BOUND_INPUT_BYTES = 4 * 1024 * 1024
MAX_SUMMARY_BYTES = 2 * 1024 * 1024
MAX_CHECKSUM_BYTES = 64 * 1024
MAX_JSON_NUMBER_TOKEN = 128
READ_BLOCK = 1024 * 1024
PREFIX_BYTES = 128 * 1024
MAX_TAR_END_PADDING_BYTES = 1024 * 1024

MEMBER_PATH_SET_ALGORITHM = "uint64be-length-prefixed-utf8-paths-v1"
EXPECTED_GZIP_HEADER = b"\x1f\x8b\x08\x00\x00\x00\x00\x00\x02\xff"
NESTED_ARCHIVE_FORMATS = (
    "7zip",
    "ar",
    "bzip2",
    "cpio",
    "gzip",
    "rpm",
    "tar",
    "xz",
    "zip",
    "zstd",
)

HEX_SHA256 = re.compile(r"^[0-9a-f]{64}$")
HEX_SHA1 = re.compile(r"^[0-9a-f]{40}$")
DIGITS = re.compile(r"^[1-9][0-9]{0,19}$")
STABLE_ID = re.compile(r"^[a-z][a-z0-9-]*:[0-9a-f]{64}$")
EXPECTED_INPUTS = {
    "campaign_authority": {
        "path": "host-kernel/rocky/evidence/rk001-license-review-campaign-ef58-v1.json",
        "sha256": "b5581cb9ad5707af65968a6e01ea69a7c46ebbe2542412c1a4cec0611da77852",
        "size": 168050,
    },
    "child_inventory_v2_workflow": {
        "path": ".github/workflows/rk001-license-child-inventory-v2.yml",
        "sha256": "b6f363c9c58f1eca8120b3b900bb4beacc7f01298b71562158fc19710d83482b",
        "size": 12335,
    },
    "license_inventory_v1_checker": {
        "path": "scripts/rocky_kernel_license_inventory.py",
        "sha256": "d6103ca6d2d0bd6c5f0a40994839f1c60a0584283e624252a10aa58f0111ee9d",
        "size": 61125,
    },
    "source_lock": {
        "path": "host-kernel/rocky/source-lock.json",
        "sha256": "707ee40466ac0bb0cd0600383bba0b13fc1146e7080034786bf5668a95b27682",
        "size": 18236,
    },
    "source_lock_validator": {
        "path": "scripts/rocky_kernel_source_lock.py",
        "sha256": "1fc6f6457d5a06d43260b84a8627fa2297c360d3a5c3810012a2198aadf3c262",
        "size": 60008,
    },
}
EXPECTED_SOURCE_RPM = {
    "cache_relative_path": (
        "rocky/10.2/x86_64/source-rpms/sha256/2b/"
        "2bfeda65bd9bdd4b86650074c81e061c37822b80317ac0d4f5aacc89c85589cb/"
        "kernel-6.12.0-211.44.1.el10_2.src.rpm"
    ),
    "filename": "kernel-6.12.0-211.44.1.el10_2.src.rpm",
    "sha256": "2bfeda65bd9bdd4b86650074c81e061c37822b80317ac0d4f5aacc89c85589cb",
    "size": 159328372,
    "url": (
        "https://download.rockylinux.org/pub/rocky/10.2/BaseOS/source/tree/"
        "Packages/k/kernel-6.12.0-211.44.1.el10_2.src.rpm"
    ),
}
EXPECTED_CONTAINERS = [
    {
        "group_id": "exact-content:93935cc150c81723440f7d595a7c63229068982bdff09a7bf838d969ad435541",
        "namespace": "stablelists",
        "output_member": "stablelists-archive-members.jsonl.gz",
        "path": "srpm/SOURCES/kernel-abi-stablelists-6.12.0-211.44.1.el10_2.tar.xz",
        "role": "kernel ABI stable-list source object",
        "sha256": "9c753338d255502a040c82be6a39a47b80df15e30fb1d3bc2f13687522c27032",
        "size": 18168,
        "source_lock_path": "SOURCES/kernel-abi-stablelists-6.12.0-211.44.1.el10_2.tar.xz",
        "unit_id": "review-unit:66737e57212b2e92f7074e2a37ac75061ed95c07e844dd5a54a0313fcd4bf1db",
    },
    {
        "group_id": "exact-content:f0c74f97bba883f0da0f371406d0912b9c23a1e42a7bd2c3746c9e69cfd41530",
        "namespace": "kabi-dw",
        "output_member": "kabi-dw-archive-members.jsonl.gz",
        "path": "srpm/SOURCES/kernel-kabi-dw-6.12.0-211.44.1.el10_2.tar.xz",
        "role": "kernel ABI DWARF source object",
        "sha256": "7547d50e4f0daeb28eba949801d3d09d0c3c6a8946859759a44d00f786791d4e",
        "size": 1096,
        "source_lock_path": "SOURCES/kernel-kabi-dw-6.12.0-211.44.1.el10_2.tar.xz",
        "unit_id": "review-unit:1fd6600d10b6a8b34d75e36cf027374a7c4ffa3599e0a8a516af2f10aace5d11",
    },
]
EXPECTED_CLAIMS = {
    "archive_expansion_complete": False,
    "campaign_complete": False,
    "child_inventory_registered": False,
    "child_review_complete": False,
    "credit_eligible": False,
    "durable_archive": False,
    "gate_complete": False,
    "independent_legal_review_complete": False,
    "provenance_review_complete": False,
    "redistribution_approved": False,
    "tracker_credit": False,
}
EXPECTED_GATE = {
    "credit_eligible": False,
    "gate_complete": False,
    "gate_id": "RK-001",
    "points_awarded": 0,
    "status": "TODO",
    "tracker_credit": False,
}
EXPECTED_REMAINING_BLOCKERS = [
    (
        "The exact stablelists and kabi-dw archive bytes are absent locally; no child "
        "counts or child closure digests are frozen in this contract."
    ),
    (
        "A successful capture remains machine-generated and captured-unreviewed; it is "
        "not independent legal, provenance, authorship, or redistribution review."
    ),
    (
        "Any nested archive member remains a transitive expansion blocker; this v2 "
        "scaffold does not silently claim recursive archive closure."
    ),
    (
        "The temporary Actions artifact is not a durable archive and requires a "
        "separately reviewed immutable result authority."
    ),
    (
        "The frozen v1 campaign and response authorities cannot close these successor "
        "archives and remain unchanged."
    ),
    (
        "RK-001, tracker credit, source-lock mutation, and every completion claim remain "
        "false."
    ),
]
EXPECTED_CAPTURE_POLICY = {
    "archive_format": "tar+xz",
    "authority_read_policy": "descriptor-rooted-nofollow-ancestor-replay-v1",
    "container_open_policy": "descriptor-rooted-nofollow-ancestor-replay-v1",
    "container_identity_policy": "retained-fd-full-stat-and-stream-sha256-v1",
    "directory_entries_are_review_units": False,
    "hardlinks_followed": False,
    "link_identity_algorithm": "sha256-and-size-of-utf8-canonical-target-v1",
    "maximum_archive_members": 250000,
    "maximum_archive_uncompressed_bytes": 536870912,
    "maximum_jsonl_uncompressed_bytes": 268435456,
    "maximum_member_bytes": 67108864,
    "maximum_path_bytes": 4096,
    "member_order": "canonical-path-ascending",
    "member_path_set_algorithm": MEMBER_PATH_SET_ALGORITHM,
    "nested_archive_detection": "content-magic-prefix-v1",
    "nested_archive_members_complete_expansion": False,
    "path_control_policy": "reject-unicode-control-and-format",
    "sequential_reader": "python-tarfile-r-pipe-xz",
    "symlinks_followed": False,
    "tar_end_padding_policy": "zero-only",
    "unsupported_special_entries": "reject",
}
EXPECTED_ARTIFACT_POLICY = {
    "checksum_manifest": "SHA256SUMS",
    "directory_mode": "0555",
    "gzip_body_policy": "canonical-recompress-byte-exact-v1",
    "gzip_compresslevel": 9,
    "gzip_filename": "",
    "gzip_header_hex": EXPECTED_GZIP_HEADER.hex(),
    "gzip_mtime": 0,
    "member_mode": "0444",
    "member_set_policy": "exact-initial-and-final-dirfd-list-v1",
    "output_members": [
        "SHA256SUMS",
        "child-inventory-summary.json",
        "kabi-dw-archive-members.jsonl.gz",
        "stablelists-archive-members.jsonl.gz",
    ],
    "summary_member": "child-inventory-summary.json",
    "temporary_actions_retention_days": 30,
    "verification_snapshot_policy": "single-retained-dirfd-and-member-fd-replay-v1",
}
EXPECTED_WORKFLOW_STEPS = [
    "Reject mutable dispatch and runtime identity",
    "Install bounded source and archive tools",
    "Check out the exact candidate without persisted credentials",
    "Freeze and verify the additive authority privately",
    "Acquire and extract the exact locked source RPM",
    "Capture twice, compare, and verify without review claims",
    "Upload temporary machine capture without tracker credit",
]
EXPECTED_IDENTITY_STEP_COMMANDS = (
    "set -euo pipefail",
    '[[ "$EXPECTED_HEAD_SHA" =~ ^[0-9a-f]{40}$ ]]',
    '[[ "$GITHUB_SHA" == "$EXPECTED_HEAD_SHA" ]]',
    '[[ "$GITHUB_WORKFLOW_SHA" == "$EXPECTED_HEAD_SHA" ]]',
    'case "$GITHUB_WORKFLOW_REF" in',
    '  "$GITHUB_REPOSITORY/.github/workflows/rk001-license-child-inventory-v2.yml@refs/heads/"*|\\',
    '  "$GITHUB_REPOSITORY/.github/workflows/rk001-license-child-inventory-v2.yml@refs/tags/"*) ;;',
    "  *) echo 'unexpected child-inventory workflow ref' >&2; exit 1 ;;",
    "esac",
    '[[ "$(uname -m)" == x86_64 ]]',
    ". /etc/os-release",
    '[[ "$ID" == rocky ]]',
    '[[ "$VERSION_ID" == 10.2 ]]',
)


class ChildInventoryError(RuntimeError):
    """Raised when a contract, container, or capture fails closed."""


def reject_duplicate_pairs(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ChildInventoryError("duplicate JSON key: {0}".format(key))
        value[key] = item
    return value


def reject_float(token):
    raise ChildInventoryError("floating-point JSON values are forbidden: {0}".format(token))


def reject_constant(token):
    raise ChildInventoryError("nonfinite JSON values are forbidden: {0}".format(token))


def parse_bounded_int(token):
    if type(token) is not str or len(token) > MAX_JSON_NUMBER_TOKEN:
        raise ChildInventoryError("JSON integer token exceeds its cap")
    try:
        return int(token, 10)
    except ValueError as error:
        raise ChildInventoryError("JSON integer token is invalid: {0}".format(error))


def canonical_json(value, newline=False):
    data = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("ascii")
    return data + (b"\n" if newline else b"")


def read_json_bytes(data, label, canonical=False):
    if type(data) is not bytes:
        raise ChildInventoryError("{0} is not bytes".format(label))
    try:
        value = json.loads(
            data.decode("utf-8"),
            object_pairs_hook=reject_duplicate_pairs,
            parse_int=parse_bounded_int,
            parse_float=reject_float,
            parse_constant=reject_constant,
        )
    except ChildInventoryError:
        raise
    except (UnicodeError, ValueError) as error:
        raise ChildInventoryError("cannot parse {0}: {1}".format(label, error))
    if type(value) is not dict:
        raise ChildInventoryError("{0} must contain one JSON object".format(label))
    if canonical and data != canonical_json(value, newline=True):
        raise ChildInventoryError("{0} is not canonical JSON".format(label))
    return value


def exact_keys(value, keys, label):
    if type(value) is not dict or set(value) != set(keys):
        raise ChildInventoryError("{0} keys differ".format(label))
    return value


def require_exact(actual, expected, label):
    if type(actual) is not type(expected):
        raise ChildInventoryError("{0} differs".format(label))
    if type(expected) is dict:
        if set(actual) != set(expected):
            raise ChildInventoryError("{0} differs".format(label))
        for key in expected:
            require_exact(actual[key], expected[key], label + "." + str(key))
    elif type(expected) in (list, tuple):
        if len(actual) != len(expected):
            raise ChildInventoryError("{0} differs".format(label))
        for index, values in enumerate(zip(actual, expected)):
            require_exact(values[0], values[1], label + "[{0}]".format(index))
    elif actual != expected:
        raise ChildInventoryError("{0} differs".format(label))
    return actual


def require_int(value, label, minimum=0):
    if type(value) is not int or value < minimum:
        raise ChildInventoryError("{0} is not a bounded integer".format(label))
    return value


def require_string(value, label, maximum=4096):
    if type(value) is not str or not value:
        raise ChildInventoryError("{0} is not a bounded string".format(label))
    try:
        encoded = value.encode("utf-8")
    except UnicodeError as error:
        raise ChildInventoryError("{0} is not valid UTF-8: {1}".format(label, error))
    if len(encoded) > maximum:
        raise ChildInventoryError("{0} is not a bounded string".format(label))
    if any(unicodedata.category(character) in ("Cc", "Cf", "Cs") for character in value):
        raise ChildInventoryError("{0} contains a control or format character".format(label))
    return value


def require_sha256(value, label):
    if type(value) is not str or not HEX_SHA256.fullmatch(value):
        raise ChildInventoryError("{0} is not a lowercase SHA-256".format(label))
    return value


def safe_relative(value, label, maximum=4096):
    value = require_string(value, label, maximum)
    if "\\" in value:
        raise ChildInventoryError("{0} contains a backslash".format(label))
    path = PurePosixPath(value)
    if (
        path.is_absolute()
        or path.as_posix() != value
        or any(part in ("", ".", "..") for part in path.parts)
    ):
        raise ChildInventoryError("{0} is not a normalized relative path".format(label))
    return path.as_posix()


def _bounded_file_identity(metadata):
    return (
        metadata.st_dev,
        metadata.st_ino,
        stat.S_IFMT(metadata.st_mode),
        stat.S_IMODE(metadata.st_mode),
        metadata.st_nlink,
        metadata.st_uid,
        metadata.st_gid,
        metadata.st_size,
        metadata.st_mtime_ns,
        metadata.st_ctime_ns,
    )


def _directory_identity(metadata):
    return (
        metadata.st_dev,
        metadata.st_ino,
        stat.S_IFMT(metadata.st_mode),
        stat.S_IMODE(metadata.st_mode),
        metadata.st_nlink,
        metadata.st_uid,
        metadata.st_gid,
    )


def _open_descriptor_rooted_leaf(path, label):
    path = Path(os.path.abspath(str(path)))
    parts = path.parts
    if len(parts) < 2 or parts[0] != os.path.sep:
        raise ChildInventoryError("{0} path is not absolute".format(label))
    nofollow = getattr(os, "O_NOFOLLOW", None)
    directory_flag = getattr(os, "O_DIRECTORY", None)
    if nofollow is None or directory_flag is None:
        raise ChildInventoryError(
            "descriptor-rooted O_NOFOLLOW/O_DIRECTORY is unavailable for {0}".format(
                label
            )
        )
    directory_flags = (
        os.O_RDONLY
        | nofollow
        | directory_flag
        | getattr(os, "O_CLOEXEC", 0)
        | getattr(os, "O_NONBLOCK", 0)
    )
    leaf_flags = (
        os.O_RDONLY
        | nofollow
        | getattr(os, "O_CLOEXEC", 0)
        | getattr(os, "O_NONBLOCK", 0)
    )
    directories = []
    leaf_descriptor = None
    try:
        root_descriptor = os.open(os.path.sep, directory_flags)
        root_metadata = os.fstat(root_descriptor)
        if not stat.S_ISDIR(root_metadata.st_mode):
            raise ChildInventoryError("filesystem root is not a directory")
        directories.append(
            {
                "descriptor": root_descriptor,
                "identity": _directory_identity(root_metadata),
                "name": None,
                "parent_descriptor": None,
            }
        )
        for component in parts[1:-1]:
            parent_descriptor = directories[-1]["descriptor"]
            descriptor = None
            try:
                descriptor = os.open(
                    component, directory_flags, dir_fd=parent_descriptor
                )
                metadata = os.fstat(descriptor)
                named = os.stat(
                    component, dir_fd=parent_descriptor, follow_symlinks=False
                )
                identity = _directory_identity(metadata)
                if (
                    not stat.S_ISDIR(metadata.st_mode)
                    or stat.S_ISLNK(named.st_mode)
                    or _directory_identity(named) != identity
                ):
                    raise ChildInventoryError(
                        "{0} ancestor is not a retained named directory".format(
                            label
                        )
                    )
                directories.append(
                    {
                        "descriptor": descriptor,
                        "identity": identity,
                        "name": component,
                        "parent_descriptor": parent_descriptor,
                    }
                )
                descriptor = None
            finally:
                if descriptor is not None:
                    os.close(descriptor)
        leaf_name = parts[-1]
        leaf_descriptor = os.open(
            leaf_name, leaf_flags, dir_fd=directories[-1]["descriptor"]
        )
        leaf_metadata = os.fstat(leaf_descriptor)
        leaf_identity = _bounded_file_identity(leaf_metadata)
        return (
            path,
            leaf_descriptor,
            leaf_name,
            leaf_metadata,
            leaf_identity,
            tuple(directories),
        )
    except Exception:
        if leaf_descriptor is not None:
            os.close(leaf_descriptor)
        for record in reversed(directories):
            os.close(record["descriptor"])
        raise


def _open_descriptor_rooted_directory(path, label):
    path = Path(os.path.abspath(str(path)))
    parts = path.parts
    if not parts or parts[0] != os.path.sep:
        raise ChildInventoryError("{0} path is not absolute".format(label))
    nofollow = getattr(os, "O_NOFOLLOW", None)
    directory_flag = getattr(os, "O_DIRECTORY", None)
    if nofollow is None or directory_flag is None:
        raise ChildInventoryError(
            "descriptor-rooted O_NOFOLLOW/O_DIRECTORY is unavailable for {0}".format(
                label
            )
        )
    flags = (
        os.O_RDONLY
        | nofollow
        | directory_flag
        | getattr(os, "O_CLOEXEC", 0)
        | getattr(os, "O_NONBLOCK", 0)
    )
    directories = []
    try:
        root_descriptor = os.open(os.path.sep, flags)
        root_metadata = os.fstat(root_descriptor)
        if not stat.S_ISDIR(root_metadata.st_mode):
            raise ChildInventoryError("filesystem root is not a directory")
        directories.append(
            {
                "descriptor": root_descriptor,
                "identity": _directory_identity(root_metadata),
                "name": None,
                "parent_descriptor": None,
            }
        )
        for component in parts[1:]:
            parent_descriptor = directories[-1]["descriptor"]
            descriptor = None
            try:
                descriptor = os.open(component, flags, dir_fd=parent_descriptor)
                metadata = os.fstat(descriptor)
                named = os.stat(
                    component, dir_fd=parent_descriptor, follow_symlinks=False
                )
                identity = _directory_identity(metadata)
                if (
                    not stat.S_ISDIR(metadata.st_mode)
                    or stat.S_ISLNK(named.st_mode)
                    or _directory_identity(named) != identity
                ):
                    raise ChildInventoryError(
                        "{0} component is not a retained named directory".format(
                            label
                        )
                    )
                directories.append(
                    {
                        "descriptor": descriptor,
                        "identity": identity,
                        "name": component,
                        "parent_descriptor": parent_descriptor,
                    }
                )
                descriptor = None
            finally:
                if descriptor is not None:
                    os.close(descriptor)
        return path, tuple(directories), os.fstat(directories[-1]["descriptor"])
    except Exception:
        for record in reversed(directories):
            os.close(record["descriptor"])
        raise


def _replay_descriptor_rooted_directories(directories, label):
    try:
        for record in directories:
            retained = os.fstat(record["descriptor"])
            if (
                not stat.S_ISDIR(retained.st_mode)
                or _directory_identity(retained) != record["identity"]
            ):
                raise ChildInventoryError(
                    "{0} retained directory identity changed".format(label)
                )
            if record["name"] is not None:
                named = os.stat(
                    record["name"],
                    dir_fd=record["parent_descriptor"],
                    follow_symlinks=False,
                )
                if (
                    stat.S_ISLNK(named.st_mode)
                    or _directory_identity(named) != record["identity"]
                ):
                    raise ChildInventoryError(
                        "{0} named directory identity changed".format(label)
                    )
    except ChildInventoryError:
        raise
    except OSError as error:
        raise ChildInventoryError(
            "cannot replay descriptor-rooted {0}: {1}".format(label, error)
        )


def _replay_descriptor_rooted_leaf(
    leaf_descriptor, leaf_name, leaf_identity, directories, label
):
    try:
        _replay_descriptor_rooted_directories(directories, label)
        retained_leaf = os.fstat(leaf_descriptor)
        named_leaf = os.stat(
            leaf_name,
            dir_fd=directories[-1]["descriptor"],
            follow_symlinks=False,
        )
    except ChildInventoryError:
        raise
    except OSError as error:
        raise ChildInventoryError(
            "cannot replay descriptor-rooted {0}: {1}".format(label, error)
        )
    if (
        not stat.S_ISREG(retained_leaf.st_mode)
        or not stat.S_ISREG(named_leaf.st_mode)
        or _bounded_file_identity(retained_leaf) != leaf_identity
        or _bounded_file_identity(named_leaf) != leaf_identity
    ):
        raise ChildInventoryError("{0} named leaf identity changed".format(label))


def _close_descriptor_rooted_leaf(leaf_descriptor, directories):
    os.close(leaf_descriptor)
    for record in reversed(directories):
        os.close(record["descriptor"])


def _close_descriptor_rooted_directory(directories):
    for record in reversed(directories):
        os.close(record["descriptor"])


def _bounded_file(path, label, cap):
    try:
        (
            _path,
            descriptor,
            leaf_name,
            metadata,
            identity,
            directories,
        ) = _open_descriptor_rooted_leaf(path, label)
    except ChildInventoryError:
        raise
    except OSError as error:
        raise ChildInventoryError(
            "cannot open descriptor-rooted {0}: {1}".format(label, error)
        )
    try:
        if (
            not stat.S_ISREG(metadata.st_mode)
            or metadata.st_nlink != 1
            or metadata.st_size < 1
            or metadata.st_size > cap
        ):
            raise ChildInventoryError(
                "{0} is not a bounded single-link regular file".format(label)
            )

        def replay_identity():
            _replay_descriptor_rooted_leaf(
                descriptor, leaf_name, identity, directories, label
            )

        replay_identity()
        chunks = []
        retained_size = 0
        try:
            os.lseek(descriptor, 0, os.SEEK_SET)
            while retained_size < metadata.st_size:
                block = os.read(
                    descriptor, min(READ_BLOCK, metadata.st_size - retained_size)
                )
                if not block:
                    break
                chunks.append(block)
                retained_size += len(block)
                replay_identity()
            if retained_size != metadata.st_size or os.read(descriptor, 1):
                raise ChildInventoryError("{0} size changed while read".format(label))
            data = b"".join(chunks)

            os.lseek(descriptor, 0, os.SEEK_SET)
            replay_offset = 0
            while replay_offset < len(data):
                block = os.read(
                    descriptor, min(READ_BLOCK, len(data) - replay_offset)
                )
                if not block or block != data[replay_offset : replay_offset + len(block)]:
                    raise ChildInventoryError("{0} bytes changed on replay".format(label))
                replay_offset += len(block)
                replay_identity()
            if replay_offset != len(data) or os.read(descriptor, 1):
                raise ChildInventoryError("{0} bytes changed on replay".format(label))
        except OSError as error:
            raise ChildInventoryError("cannot read {0}: {1}".format(label, error))
        replay_identity()
        return data
    finally:
        _close_descriptor_rooted_leaf(descriptor, directories)


def repository_file(repo, relative, label):
    relative = safe_relative(relative, label + " path")
    root = Path(repo).resolve()
    requested = root.joinpath(*PurePosixPath(relative).parts)
    try:
        resolved = requested.resolve(strict=True)
    except (OSError, RuntimeError) as error:
        raise ChildInventoryError("cannot resolve {0}: {1}".format(label, error))
    if resolved != requested or os.path.commonpath((str(root), str(resolved))) != str(root):
        raise ChildInventoryError("{0} escapes or traverses a symlink".format(label))
    return requested


def file_record(path):
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as stream:
        while True:
            block = stream.read(READ_BLOCK)
            if not block:
                break
            size += len(block)
            digest.update(block)
    return {"sha256": digest.hexdigest(), "size": size}


def validate_capture_binding(binding):
    exact_keys(
        binding,
        {
            "container_image",
            "github_head_sha",
            "github_repository",
            "github_run_attempt",
            "github_run_id",
        },
        "capture binding",
    )
    require_exact(binding["container_image"], EXPECTED_CONTAINER_IMAGE, "capture image")
    if type(binding["github_head_sha"]) is not str or not HEX_SHA1.fullmatch(
        binding["github_head_sha"]
    ):
        raise ChildInventoryError("capture head is not a commit SHA")
    require_exact(binding["github_repository"], EXPECTED_REPOSITORY, "capture repository")
    for key in ("github_run_attempt", "github_run_id"):
        if type(binding[key]) is not str or not DIGITS.fullmatch(binding[key]):
            raise ChildInventoryError("capture {0} is malformed".format(key))
    return binding


def validate_capture_policy(policy):
    require_exact(policy, EXPECTED_CAPTURE_POLICY, "capture policy")
    return policy


def validate_contract_schema(authority):
    exact_keys(
        authority,
        {
            "artifact_policy",
            "capture_policy",
            "claims",
            "containers",
            "contract_id",
            "expected_result",
            "gate",
            "inputs",
            "remaining_blockers",
            "runtime",
            "schema_version",
            "source_commit",
            "source_rpm",
        },
        "child inventory contract",
    )
    require_exact(authority["schema_version"], SCHEMA_VERSION, "schema version")
    require_exact(authority["contract_id"], CONTRACT_ID, "contract identity")
    require_exact(authority["source_commit"], SOURCE_COMMIT, "source commit")
    require_exact(authority["claims"], EXPECTED_CLAIMS, "false claims")
    require_exact(authority["gate"], EXPECTED_GATE, "gate state")
    require_exact(
        authority["remaining_blockers"],
        EXPECTED_REMAINING_BLOCKERS,
        "remaining blockers",
    )

    exact_keys(
        authority["runtime"],
        {"architecture", "container_image", "distribution_id", "distribution_version"},
        "runtime policy",
    )
    require_exact(authority["runtime"]["architecture"], "x86_64", "runtime architecture")
    require_exact(authority["runtime"]["container_image"], EXPECTED_CONTAINER_IMAGE, "runtime image")
    require_exact(authority["runtime"]["distribution_id"], "rocky", "runtime distribution")
    require_exact(authority["runtime"]["distribution_version"], "10.2", "runtime version")

    require_exact(authority["inputs"], EXPECTED_INPUTS, "frozen input bindings")
    require_exact(authority["source_rpm"], EXPECTED_SOURCE_RPM, "source RPM binding")
    require_exact(authority["containers"], EXPECTED_CONTAINERS, "container bindings")
    expected = exact_keys(
        authority["expected_result"],
        {
            "capture_artifact_status",
            "kabi_dw_child_count",
            "result_authority_status",
            "stablelists_child_count",
        },
        "expected result",
    )
    require_exact(expected["capture_artifact_status"], "required-missing", "capture status")
    require_exact(expected["result_authority_status"], "required-missing", "result authority")
    require_exact(expected["stablelists_child_count"], None, "stablelists child count")
    require_exact(expected["kabi_dw_child_count"], None, "kabi-dw child count")

    validate_capture_policy(authority["capture_policy"])
    require_exact(authority["artifact_policy"], EXPECTED_ARTIFACT_POLICY, "artifact policy")
    return authority


def _load_bound(repo, record, label):
    path = repository_file(repo, record["path"], label)
    data = _bounded_file(path, label, MAX_BOUND_INPUT_BYTES)
    if len(data) != record["size"] or hashlib.sha256(data).hexdigest() != record["sha256"]:
        raise ChildInventoryError("{0} bytes differ".format(label))
    return path, data


def _workflow_step_blocks(workflow_text):
    lines = workflow_text.splitlines()
    starts = []
    for index, line in enumerate(lines):
        match = re.fullmatch(r"      - name: ([^\r\n]+)", line)
        if match is not None:
            starts.append((index, match.group(1)))
    require_exact(
        [item[1] for item in starts], EXPECTED_WORKFLOW_STEPS, "workflow step order"
    )
    blocks = {}
    for position, values in enumerate(starts):
        start, name = values
        end = starts[position + 1][0] if position + 1 < len(starts) else len(lines)
        while end > start and lines[end - 1] == "":
            end -= 1
        blocks[name] = lines[start:end]
    return blocks


def _workflow_run_commands(block, label):
    run_indexes = [index for index, line in enumerate(block) if line == "        run: |"]
    if len(run_indexes) != 1:
        raise ChildInventoryError("{0} must contain one literal run block".format(label))
    run_index = run_indexes[0]
    commands = []
    for line in block[run_index + 1 :]:
        if not line.startswith("          "):
            raise ChildInventoryError("{0} has a non-command after run".format(label))
        command = line[10:]
        if not command or command.lstrip().startswith("#"):
            raise ChildInventoryError("{0} has a blank or comment command".format(label))
        commands.append(command)
    return tuple(commands)


def _validate_workflow_semantics(workflow_text):
    if type(workflow_text) is not str:
        raise ChildInventoryError("workflow text is not a string")
    if (
        not workflow_text.endswith("\n")
        or "\r" in workflow_text
        or "\x00" in workflow_text
        or "\t" in workflow_text
    ):
        raise ChildInventoryError("workflow text framing differs")
    if workflow_text.count("\nsteps:\n"):
        raise ChildInventoryError("workflow steps indentation differs")
    if workflow_text.count("    steps:\n") != 1:
        raise ChildInventoryError("workflow must contain one active steps mapping")
    blocks = _workflow_step_blocks(workflow_text)
    identity_name = EXPECTED_WORKFLOW_STEPS[0]
    identity_block = blocks[identity_name]
    require_exact(
        identity_block[:2],
        ["      - name: " + identity_name, "        run: |"],
        "identity step mapping",
    )
    require_exact(
        _workflow_run_commands(identity_block, "identity step"),
        EXPECTED_IDENTITY_STEP_COMMANDS,
        "identity step active commands",
    )
    active_head_guard = '[[ "$GITHUB_SHA" == "$EXPECTED_HEAD_SHA" ]]'
    active_workflow_guard = '[[ "$GITHUB_WORKFLOW_SHA" == "$EXPECTED_HEAD_SHA" ]]'
    all_commands = []
    for name in EXPECTED_WORKFLOW_STEPS:
        block = blocks[name]
        if "        run: |" in block:
            all_commands.extend(_workflow_run_commands(block, name))
    require_exact(all_commands.count(active_head_guard), 1, "active head guard count")
    require_exact(
        all_commands.count(active_workflow_guard), 1, "active workflow guard count"
    )
    return workflow_text


def validate_workflow_bytes(workflow_bytes):
    if type(workflow_bytes) is not bytes:
        raise ChildInventoryError("workflow is not bytes")
    record = EXPECTED_INPUTS["child_inventory_v2_workflow"]
    if (
        len(workflow_bytes) != record["size"]
        or hashlib.sha256(workflow_bytes).hexdigest() != record["sha256"]
    ):
        raise ChildInventoryError("child inventory workflow bytes differ")
    try:
        workflow_text = workflow_bytes.decode("utf-8")
    except UnicodeError as error:
        raise ChildInventoryError("cannot decode child inventory workflow: {0}".format(error))
    return _validate_workflow_semantics(workflow_text)


def check_repository(repo):
    repo = Path(repo).resolve()
    contract_path = repository_file(repo, CONTRACT_PATH.as_posix(), "child inventory contract")
    contract_bytes = _bounded_file(contract_path, "child inventory contract", MAX_CONTRACT_BYTES)
    authority = read_json_bytes(contract_bytes, "child inventory contract", canonical=True)
    validate_contract_schema(authority)
    loaded = {}
    for key in sorted(EXPECTED_INPUTS):
        _path, data = _load_bound(repo, EXPECTED_INPUTS[key], key.replace("_", " "))
        loaded[key] = data

    source_lock = read_json_bytes(loaded["source_lock"], "source lock")
    source_rpm = source_lock.get("source_rpm")
    if type(source_rpm) is not dict:
        raise ChildInventoryError("source-lock source RPM is missing")
    for key in ("filename", "sha256", "size", "url"):
        require_exact(
            source_rpm.get(key), EXPECTED_SOURCE_RPM[key], "source-lock source RPM " + key
        )
    require_exact(
        source_lock.get("acquisition", {}).get("cache_relative_path"),
        EXPECTED_SOURCE_RPM["cache_relative_path"],
        "source-lock cache path",
    )
    embedded = {item.get("path"): item for item in source_lock.get("embedded_objects", [])}
    for container in EXPECTED_CONTAINERS:
        require_exact(
            embedded.get(container["source_lock_path"]),
            {
                "path": container["source_lock_path"],
                "role": container["role"],
                "sha256": container["sha256"],
                "size": container["size"],
            },
            "source-lock embedded object " + container["namespace"],
        )

    campaign = read_json_bytes(
        loaded["campaign_authority"], "campaign authority", canonical=True
    )
    bindings = campaign.get("archive_expansion_bindings")
    if type(bindings) is not list:
        raise ChildInventoryError("campaign archive bindings are missing")
    by_group = {
        binding.get("container", {}).get("group_id"): binding for binding in bindings
    }
    for container in EXPECTED_CONTAINERS:
        binding = by_group.get(container["group_id"])
        if type(binding) is not dict:
            raise ChildInventoryError("campaign child container is missing")
        require_exact(binding.get("role"), "future-v2-child-inventory-required", "campaign role")
        require_exact(binding.get("child_inventory"), None, "campaign child inventory")
        require_exact(
            binding.get("required_next_action"),
            "expand-and-capture-future-v2-child-inventory-before-any-closure-response",
            "campaign next action",
        )
        require_exact(
            binding.get("container"),
            {
                "group_id": container["group_id"],
                "path": container["path"],
                "sha256": container["sha256"],
                "size": container["size"],
                "unit_id": container["unit_id"],
            },
            "campaign container " + container["namespace"],
        )

    validate_workflow_bytes(loaded["child_inventory_v2_workflow"])
    return authority, contract_bytes


def _file_identity(info):
    return (
        info.st_dev,
        info.st_ino,
        stat.S_IFMT(info.st_mode),
        stat.S_IMODE(info.st_mode),
        info.st_nlink,
        info.st_uid,
        info.st_gid,
        info.st_size,
        info.st_mtime_ns,
        info.st_ctime_ns,
    )


def _replay_archive(descriptor, leaf_name, identity, directories, label):
    _replay_descriptor_rooted_leaf(
        descriptor, leaf_name, identity, directories, label
    )
    try:
        opened = os.fstat(descriptor)
    except OSError as error:
        raise ChildInventoryError("cannot replay {0}: {1}".format(label, error))
    if (
        _file_identity(opened) != identity
        or not stat.S_ISREG(opened.st_mode)
        or opened.st_nlink != 1
        or opened.st_mode & (stat.S_IWGRP | stat.S_IWOTH)
    ):
        raise ChildInventoryError("{0} identity changed or is unsafe".format(label))


def _open_archive(path, container):
    label = container["namespace"] + " archive"
    try:
        (
            held_path,
            descriptor,
            leaf_name,
            metadata,
            bounded_identity,
            directories,
        ) = _open_descriptor_rooted_leaf(path, label)
    except ChildInventoryError:
        raise
    except OSError as error:
        raise ChildInventoryError(
            "cannot open descriptor-rooted {0}: {1}".format(label, error)
        )
    identity = _file_identity(metadata)
    try:
        require_exact(identity, bounded_identity, label + " retained identity")
        _replay_archive(descriptor, leaf_name, identity, directories, label)
        if metadata.st_size != container["size"]:
            raise ChildInventoryError("{0} size differs".format(label))
        return descriptor, held_path, leaf_name, identity, directories
    except Exception:
        _close_descriptor_rooted_leaf(descriptor, directories)
        raise


def _hash_descriptor(descriptor, leaf_name, identity, directories, label):
    digest = hashlib.sha256()
    size = 0
    _replay_archive(descriptor, leaf_name, identity, directories, label)
    try:
        os.lseek(descriptor, 0, os.SEEK_SET)
        while True:
            block = os.read(descriptor, READ_BLOCK)
            if not block:
                break
            size += len(block)
            digest.update(block)
            _replay_archive(descriptor, leaf_name, identity, directories, label)
    except OSError as error:
        raise ChildInventoryError("cannot hash {0}: {1}".format(label, error))
    _replay_archive(descriptor, leaf_name, identity, directories, label)
    return size, digest.hexdigest()


class _DigestingReader(object):
    def __init__(self, stream):
        self._stream = stream
        self._digest = hashlib.sha256()
        self._size = 0

    def read(self, size=-1):
        data = self._stream.read(size)
        if type(data) is not bytes:
            raise ChildInventoryError("archive descriptor returned non-byte data")
        self._digest.update(data)
        self._size += len(data)
        return data

    def metrics(self):
        return self._size, self._digest.hexdigest()


def _normalized_member_name(member, maximum):
    raw = member.name
    if type(raw) is not str or not raw or "\x00" in raw or "\\" in raw:
        raise ChildInventoryError("archive member name is unsafe")
    if member.isdir():
        raw = raw.rstrip("/")
    if not raw:
        raise ChildInventoryError("archive member name is empty")
    return safe_relative(raw, "archive member", maximum)


def _resolved_link(member_path, raw_target, hardlink, maximum):
    raw_target = require_string(raw_target, "archive link target", maximum)
    if "\\" in raw_target or PurePosixPath(raw_target).is_absolute():
        raise ChildInventoryError("archive link target is unsafe")
    base = "" if hardlink else posixpath.dirname(member_path)
    resolved = posixpath.normpath(posixpath.join(base, raw_target))
    if resolved in ("", ".", "..") or resolved.startswith("../"):
        raise ChildInventoryError("archive link target escapes")
    return safe_relative(resolved, "resolved archive link", maximum)


def _hash_member(stream, declared_size, policy, label):
    digest = hashlib.sha256()
    retained = 0
    prefix = bytearray()
    while retained < declared_size:
        block = stream.read(min(READ_BLOCK, declared_size - retained))
        if not block:
            raise ChildInventoryError("{0} ended before its declared size".format(label))
        if type(block) is not bytes:
            raise ChildInventoryError("{0} returned non-byte data".format(label))
        retained += len(block)
        digest.update(block)
        if len(prefix) < PREFIX_BYTES:
            prefix.extend(block[: PREFIX_BYTES - len(prefix)])
    if stream.read(1):
        raise ChildInventoryError("{0} exceeds its declared size".format(label))
    return retained, digest.hexdigest(), bytes(prefix)


def _nested_archive_format(prefix):
    if type(prefix) is not bytes:
        raise ChildInventoryError("archive member prefix is not bytes")
    if prefix.startswith(b"\x37\x7a\xbc\xaf\x27\x1c"):
        return "7zip"
    if prefix.startswith(b"!<arch>\n"):
        return "ar"
    if prefix.startswith(b"BZh"):
        return "bzip2"
    if prefix.startswith((b"070701", b"070702", b"070707", b"\x71\xc7", b"\xc7\x71")):
        return "cpio"
    if prefix.startswith(b"\x1f\x8b\x08"):
        return "gzip"
    if prefix.startswith(b"\xed\xab\xee\xdb"):
        return "rpm"
    if len(prefix) >= 263 and prefix[257:262] == b"ustar":
        return "tar"
    if prefix.startswith(b"\xfd7zXZ\x00"):
        return "xz"
    if prefix.startswith((b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08")):
        return "zip"
    if prefix.startswith(b"\x28\xb5\x2f\xfd"):
        return "zstd"
    return None


def _record_stream_metrics(records):
    digest = hashlib.sha256()
    size = 0
    for record in records:
        line = canonical_json(record, newline=True)
        digest.update(line)
        size += len(line)
    return size, digest.hexdigest()


def _path_set_sha256(records):
    digest = hashlib.sha256()
    for record in records:
        encoded = record["path"].encode("utf-8")
        if len(encoded) >= 1 << 64:
            raise ChildInventoryError("archive member path cannot be length framed")
        digest.update(len(encoded).to_bytes(8, byteorder="big"))
        digest.update(encoded)
    return digest.hexdigest()


def _validate_link_closure(records):
    by_path = {record["path"]: record for record in records}
    for record in records:
        if record["entry_type"] not in ("symlink", "hardlink"):
            continue
        target = record["link_target"]
        if target not in by_path:
            raise ChildInventoryError("archive link target is absent: {0}".format(target))
        seen = {record["path"]}
        current = target
        while True:
            if current in seen:
                raise ChildInventoryError("archive link cycle is present")
            seen.add(current)
            target_record = by_path[current]
            if target_record["entry_type"] not in ("hardlink", "symlink"):
                break
            current = target_record["link_target"]
        if record["entry_type"] == "hardlink" and target_record["entry_type"] != "regular":
            raise ChildInventoryError("archive hardlink does not resolve to a regular file")


def _derive_capture(container, records, regular_bytes):
    counts = {name: 0 for name in ("directory", "hardlink", "regular", "symlink")}
    nested = 0
    for record in records:
        counts[record["entry_type"]] += 1
        if record["entry_type"] == "regular" and record["nested_archive_format"] is not None:
            nested += 1
    stream_size, stream_sha = _record_stream_metrics(records)
    return {
        "child_review_complete": False,
        "directory_count": counts["directory"],
        "hardlink_count": counts["hardlink"],
        "member_count": len(records),
        "member_path_set_algorithm": MEMBER_PATH_SET_ALGORITHM,
        "member_path_set_sha256": _path_set_sha256(records),
        "member_stream_algorithm": "canonical-ascii-json-lines-v2",
        "member_stream_sha256": stream_sha,
        "member_stream_size": stream_size,
        "nested_archive_member_count": nested,
        "regular_content_bytes": regular_bytes,
        "regular_count": counts["regular"],
        "review_state": "captured-unreviewed",
        "review_unit_count": counts["regular"] + counts["symlink"] + counts["hardlink"],
        "source_identity": {"archive_sha256": container["sha256"]},
        "symlink_count": counts["symlink"],
        "transitive_archive_expansion_complete": False,
    }


def inventory_tar_xz(path, container, capture_policy):
    """Sequentially inventory one exact tar.xz without extracting it."""
    exact_keys(container, set(EXPECTED_CONTAINERS[0]), "container binding")
    policy = validate_capture_policy(capture_policy)
    descriptor, _held_path, leaf_name, identity, directories = _open_archive(
        path, container
    )
    label = container["namespace"] + " archive"
    records = []
    seen = set()
    regular_bytes = 0
    try:
        size, digest = _hash_descriptor(
            descriptor, leaf_name, identity, directories, label
        )
        if size != container["size"] or digest != container["sha256"]:
            raise ChildInventoryError("{0} bytes differ from the contract".format(label))
        duplicate = os.dup(descriptor)
        try:
            os.lseek(duplicate, 0, os.SEEK_SET)
            with os.fdopen(duplicate, "rb", buffering=0) as raw:
                duplicate = None
                streamed_descriptor = _DigestingReader(raw)
                with tarfile.open(fileobj=streamed_descriptor, mode="r|xz") as archive:
                    for member in archive:
                        if len(records) >= policy["maximum_archive_members"]:
                            raise ChildInventoryError("archive member count exceeds its cap")
                        relative = _normalized_member_name(
                            member, policy["maximum_path_bytes"]
                        )
                        canonical_path = container["namespace"] + "/" + relative
                        if canonical_path in seen:
                            raise ChildInventoryError("archive contains a duplicate member path")
                        seen.add(canonical_path)
                        source_identity = {"archive_sha256": container["sha256"]}
                        if member.isdir():
                            if member.size != 0:
                                raise ChildInventoryError(
                                    "archive directory carries hidden payload bytes"
                                )
                            record = {
                                "archive_group_id": container["group_id"],
                                "entry_type": "directory",
                                "link_target": None,
                                "nested_archive_format": None,
                                "path": canonical_path,
                                "sha256": hashlib.sha256(b"").hexdigest(),
                                "size": 0,
                                "source_identity": source_identity,
                            }
                        elif member.isreg():
                            if (
                                type(member.size) is not int
                                or member.size < 0
                                or member.size > policy["maximum_member_bytes"]
                            ):
                                raise ChildInventoryError("archive member size exceeds its cap")
                            extracted = archive.extractfile(member)
                            if extracted is None:
                                raise ChildInventoryError("cannot read regular archive member")
                            member_size, member_sha, prefix = _hash_member(
                                extracted, member.size, policy, canonical_path
                            )
                            regular_bytes += member_size
                            if regular_bytes > policy["maximum_archive_uncompressed_bytes"]:
                                raise ChildInventoryError("archive expansion exceeds its cap")
                            record = {
                                "archive_group_id": container["group_id"],
                                "entry_type": "regular",
                                "link_target": None,
                                "nested_archive_format": _nested_archive_format(prefix),
                                "path": canonical_path,
                                "sha256": member_sha,
                                "size": member_size,
                                "source_identity": source_identity,
                            }
                        elif member.issym() or member.islnk():
                            if member.size != 0:
                                raise ChildInventoryError(
                                    "archive link carries hidden payload bytes"
                                )
                            resolved = _resolved_link(
                                relative,
                                member.linkname,
                                member.islnk(),
                                policy["maximum_path_bytes"],
                            )
                            canonical_target = container["namespace"] + "/" + resolved
                            target_bytes = canonical_target.encode("utf-8")
                            record = {
                                "archive_group_id": container["group_id"],
                                "entry_type": "hardlink" if member.islnk() else "symlink",
                                "link_target": canonical_target,
                                "nested_archive_format": None,
                                "path": canonical_path,
                                "sha256": hashlib.sha256(target_bytes).hexdigest(),
                                "size": len(target_bytes),
                                "source_identity": source_identity,
                            }
                        else:
                            raise ChildInventoryError(
                                "archive contains an unsupported special member"
                            )
                        records.append(record)
                        _replay_archive(
                            descriptor, leaf_name, identity, directories, label
                        )
                    trailing_size = 0
                    while True:
                        trailing = archive.fileobj.read(READ_BLOCK)
                        if not trailing:
                            break
                        if type(trailing) is not bytes or trailing.strip(b"\x00"):
                            raise ChildInventoryError(
                                "archive carries nonzero bytes after its tar end marker"
                            )
                        trailing_size += len(trailing)
                        if trailing_size > MAX_TAR_END_PADDING_BYTES:
                            raise ChildInventoryError(
                                "archive tar end padding exceeds its cap"
                            )
                        _replay_archive(
                            descriptor, leaf_name, identity, directories, label
                        )
                    decompressor = archive.fileobj.cmp
                    if not decompressor.eof or decompressor.unused_data:
                        raise ChildInventoryError(
                            "archive XZ stream has a missing end or trailing bytes"
                        )
                streamed_size, streamed_digest = streamed_descriptor.metrics()
                if streamed_size != size or streamed_digest != digest:
                    raise ChildInventoryError(
                        "archive descriptor bytes differ during member streaming"
                    )
        except (OSError, tarfile.TarError, EOFError) as error:
            raise ChildInventoryError("cannot stream {0}: {1}".format(label, error))
        finally:
            if duplicate is not None:
                os.close(duplicate)
        if not records:
            raise ChildInventoryError("archive child inventory is empty")
        records.sort(key=lambda record: record["path"])
        if len({record["path"] for record in records}) != len(records):
            raise ChildInventoryError("archive child paths are duplicated")
        _validate_link_closure(records)
        size_after, digest_after = _hash_descriptor(
            descriptor, leaf_name, identity, directories, label
        )
        if size_after != size or digest_after != digest:
            raise ChildInventoryError("archive bytes changed across inventory")
        capture = _derive_capture(container, records, regular_bytes)
        if capture["member_stream_size"] > policy["maximum_jsonl_uncompressed_bytes"]:
            raise ChildInventoryError("archive member stream exceeds its cap")
        return {"capture": capture, "container": copy.deepcopy(container), "records": records}
    finally:
        _close_descriptor_rooted_leaf(descriptor, directories)


MEMBER_KEYS = {
    "archive_group_id",
    "entry_type",
    "link_target",
    "nested_archive_format",
    "path",
    "sha256",
    "size",
    "source_identity",
}


def validate_member_record(record, container):
    exact_keys(record, MEMBER_KEYS, "archive member record")
    require_exact(record["archive_group_id"], container["group_id"], "archive group")
    entry_type = record["entry_type"]
    if entry_type not in ("directory", "hardlink", "regular", "symlink"):
        raise ChildInventoryError("archive member type is invalid")
    path = safe_relative(
        record["path"],
        "archive member path",
        EXPECTED_CAPTURE_POLICY["maximum_path_bytes"]
        + len(container["namespace"].encode("utf-8"))
        + 1,
    )
    if not path.startswith(container["namespace"] + "/"):
        raise ChildInventoryError("archive member namespace differs")
    require_sha256(record["sha256"], "archive member digest")
    require_int(record["size"], "archive member size")
    require_exact(
        record["source_identity"],
        {"archive_sha256": container["sha256"]},
        "archive member source identity",
    )
    if entry_type in ("directory", "regular"):
        require_exact(record["link_target"], None, "non-link target")
    else:
        target = safe_relative(
            record["link_target"],
            "archive link target",
            EXPECTED_CAPTURE_POLICY["maximum_path_bytes"]
            + len(container["namespace"].encode("utf-8"))
            + 1,
        )
        if not target.startswith(container["namespace"] + "/"):
            raise ChildInventoryError("archive link target namespace differs")
    if entry_type == "directory":
        require_exact(record["nested_archive_format"], None, "directory archive format")
        require_exact(record["size"], 0, "directory size")
        require_exact(record["sha256"], hashlib.sha256(b"").hexdigest(), "directory digest")
    elif entry_type == "regular":
        if record["size"] > EXPECTED_CAPTURE_POLICY["maximum_member_bytes"]:
            raise ChildInventoryError("regular archive member size exceeds its cap")
        nested_format = record["nested_archive_format"]
        if nested_format is not None and nested_format not in NESTED_ARCHIVE_FORMATS:
            raise ChildInventoryError("regular archive member format is invalid")
    else:
        require_exact(record["nested_archive_format"], None, "link archive format")
        target_bytes = record["link_target"].encode("utf-8")
        require_exact(record["size"], len(target_bytes), "link target size")
        require_exact(
            record["sha256"], hashlib.sha256(target_bytes).hexdigest(), "link target digest"
        )
    return record


def validate_record_collection(records, container):
    if type(records) is not list or not records:
        raise ChildInventoryError("archive member record collection is empty or malformed")
    if len(records) > EXPECTED_CAPTURE_POLICY["maximum_archive_members"]:
        raise ChildInventoryError("archive member count exceeds its cap")
    regular_bytes = 0
    previous = None
    for record in records:
        validate_member_record(record, container)
        if previous is not None and record["path"] <= previous:
            raise ChildInventoryError("archive member rows are duplicated or unsorted")
        previous = record["path"]
        if record["entry_type"] == "regular":
            regular_bytes += record["size"]
            if regular_bytes > EXPECTED_CAPTURE_POLICY["maximum_archive_uncompressed_bytes"]:
                raise ChildInventoryError("archive expansion exceeds its cap")
    stream_size, _stream_digest = _record_stream_metrics(records)
    if stream_size > EXPECTED_CAPTURE_POLICY["maximum_jsonl_uncompressed_bytes"]:
        raise ChildInventoryError("archive member stream exceeds its cap")
    _validate_link_closure(records)
    return regular_bytes


def _write_gzip_records(path, records):
    with path.open("xb") as raw:
        with gzip.GzipFile(
            filename="",
            mode="wb",
            fileobj=raw,
            compresslevel=EXPECTED_ARTIFACT_POLICY["gzip_compresslevel"],
            mtime=EXPECTED_ARTIFACT_POLICY["gzip_mtime"],
        ) as compressed:
            for record in records:
                compressed.write(canonical_json(record, newline=True))


class _ExactByteSink(object):
    def __init__(self, expected):
        self._expected = expected
        self._offset = 0

    def write(self, data):
        if type(data) is not bytes:
            raise ChildInventoryError("canonical gzip writer returned non-byte data")
        end = self._offset + len(data)
        if end > len(self._expected) or self._expected[self._offset : end] != data:
            raise ChildInventoryError("gzip body is not the canonical recompression")
        self._offset = end
        return len(data)

    def flush(self):
        return None

    def require_complete(self):
        if self._offset != len(self._expected):
            raise ChildInventoryError("gzip stream has bytes beyond canonical recompression")


def _require_canonical_gzip_recompression(expected, records):
    sink = _ExactByteSink(expected)
    with gzip.GzipFile(
        filename="",
        mode="wb",
        fileobj=sink,
        compresslevel=EXPECTED_ARTIFACT_POLICY["gzip_compresslevel"],
        mtime=EXPECTED_ARTIFACT_POLICY["gzip_mtime"],
    ) as compressed:
        for record in records:
            compressed.write(canonical_json(record, newline=True))
    sink.require_complete()


def _decompress_canonical_gzip(data, cap):
    if type(data) is not bytes or len(data) < 18:
        raise ChildInventoryError("archive member stream is not a bounded gzip member")
    require_exact(data[:10], EXPECTED_GZIP_HEADER, "gzip header")
    decoder = zlib.decompressobj(16 + zlib.MAX_WBITS)
    try:
        uncompressed = decoder.decompress(data, cap + 1)
        if len(uncompressed) > cap or decoder.unconsumed_tail:
            raise ChildInventoryError("archive member stream exceeds its cap")
        remaining = cap + 1 - len(uncompressed)
        if remaining > 0:
            uncompressed += decoder.flush(remaining)
    except zlib.error as error:
        raise ChildInventoryError(
            "cannot decompress archive member stream: {0}".format(error)
        )
    if len(uncompressed) > cap:
        raise ChildInventoryError("archive member stream exceeds its cap")
    if not decoder.eof or decoder.unused_data or decoder.unconsumed_tail:
        raise ChildInventoryError(
            "archive member stream has a missing end or trailing gzip member"
        )
    return uncompressed


def _write_bytes(path, data):
    with path.open("xb") as stream:
        stream.write(data)


def _capture_summary(authority, contract_bytes, results, binding, stream_records):
    containers = []
    for result in results:
        member = result["container"]["output_member"]
        record = stream_records[member]
        containers.append(
            {
                "capture": copy.deepcopy(result["capture"]),
                "container": copy.deepcopy(result["container"]),
                "stream": {
                    "compressed_sha256": record["sha256"],
                    "compressed_size": record["size"],
                    "member": member,
                    "uncompressed_sha256": result["capture"]["member_stream_sha256"],
                    "uncompressed_size": result["capture"]["member_stream_size"],
                },
            }
        )
    return {
        "artifact_status": "temporary-unreviewed-capture",
        "binding": copy.deepcopy(binding),
        "blockers": copy.deepcopy(authority["remaining_blockers"]),
        "claims": copy.deepcopy(EXPECTED_CLAIMS),
        "containers": containers,
        "contract": {
            "contract_id": CONTRACT_ID,
            "path": CONTRACT_PATH.as_posix(),
            "sha256": hashlib.sha256(contract_bytes).hexdigest(),
            "size": len(contract_bytes),
        },
        "gate": copy.deepcopy(EXPECTED_GATE),
        "result_authority_status": "required-missing",
        "schema_version": SCHEMA_VERSION,
        "source_commit": SOURCE_COMMIT,
    }


def write_capture(output_dir, authority, contract_bytes, results, binding):
    validate_contract_schema(authority)
    validate_capture_binding(binding)
    if [result["container"] for result in results] != authority["containers"]:
        raise ChildInventoryError("capture result container closure differs")
    output_dir = Path(output_dir).absolute()
    if output_dir.exists() or output_dir.is_symlink():
        raise ChildInventoryError("capture output already exists")
    parent = output_dir.parent
    if not parent.is_dir() or parent.is_symlink():
        raise ChildInventoryError("capture output parent is unsafe")
    temporary = Path(tempfile.mkdtemp(prefix=".rk001-child-v2-", dir=str(parent)))
    published = False
    try:
        stream_records = {}
        for result in results:
            container = result["container"]
            records = result["records"]
            regular_bytes = validate_record_collection(records, container)
            require_exact(
                _derive_capture(
                    container,
                    records,
                    regular_bytes,
                ),
                result["capture"],
                "derived capture closure",
            )
            member_path = temporary / container["output_member"]
            _write_gzip_records(member_path, records)
            stream_records[container["output_member"]] = file_record(member_path)

        summary = _capture_summary(
            authority, contract_bytes, results, binding, stream_records
        )
        summary_path = temporary / "child-inventory-summary.json"
        _write_bytes(summary_path, canonical_json(summary, newline=True))
        checksummed = sorted(
            ["child-inventory-summary.json"]
            + [container["output_member"] for container in authority["containers"]]
        )
        checksum_bytes = b"".join(
            (
                file_record(temporary / name)["sha256"] + "  " + name + "\n"
            ).encode("ascii")
            for name in checksummed
        )
        _write_bytes(temporary / "SHA256SUMS", checksum_bytes)
        for path in temporary.iterdir():
            os.chmod(str(path), 0o444)
        os.chmod(str(temporary), 0o555)
        os.rename(str(temporary), str(output_dir))
        published = True
    finally:
        if not published and temporary.exists():
            shutil.rmtree(str(temporary))
    return verify_capture(output_dir, authority, contract_bytes)


def _capture_member_cap(name, authority):
    safe_relative(name, "capture member")
    if name == "SHA256SUMS":
        return MAX_CHECKSUM_BYTES
    if name == "child-inventory-summary.json":
        return MAX_SUMMARY_BYTES
    if name in {
        container["output_member"] for container in authority["containers"]
    }:
        return authority["capture_policy"]["maximum_jsonl_uncompressed_bytes"]
    raise ChildInventoryError("capture member is not frozen by the authority")


def _capture_directory_names(descriptor, label):
    try:
        names = os.listdir(descriptor)
    except OSError as error:
        raise ChildInventoryError("cannot list {0}: {1}".format(label, error))
    if type(names) is not list or any(type(name) is not str for name in names):
        raise ChildInventoryError("{0} returned non-text member names".format(label))
    return sorted(names)


def _replay_capture_member(snapshot, record):
    label = "capture member " + record["name"]
    try:
        _replay_descriptor_rooted_directories(snapshot["directories"], label)
        retained = os.fstat(record["descriptor"])
        named = os.stat(
            record["name"],
            dir_fd=snapshot["directory_descriptor"],
            follow_symlinks=False,
        )
    except ChildInventoryError:
        raise
    except OSError as error:
        raise ChildInventoryError("cannot replay {0}: {1}".format(label, error))
    if (
        not stat.S_ISREG(retained.st_mode)
        or not stat.S_ISREG(named.st_mode)
        or _bounded_file_identity(retained) != record["identity"]
        or _bounded_file_identity(named) != record["identity"]
    ):
        raise ChildInventoryError("{0} identity changed".format(label))


def _read_capture_snapshot_member(snapshot, record, cap):
    label = "capture member " + record["name"]
    if record["size"] < 1 or record["size"] > cap:
        raise ChildInventoryError("{0} exceeds its exact bound".format(label))
    _replay_capture_member(snapshot, record)
    data = bytearray()
    try:
        os.lseek(record["descriptor"], 0, os.SEEK_SET)
        while len(data) < record["size"]:
            block = os.read(
                record["descriptor"],
                min(READ_BLOCK, record["size"] - len(data)),
            )
            if not block:
                break
            data.extend(block)
            _replay_capture_member(snapshot, record)
        if len(data) != record["size"] or os.read(record["descriptor"], 1):
            raise ChildInventoryError("{0} size changed while read".format(label))
        frozen = bytes(data)

        os.lseek(record["descriptor"], 0, os.SEEK_SET)
        offset = 0
        while offset < len(frozen):
            block = os.read(
                record["descriptor"], min(READ_BLOCK, len(frozen) - offset)
            )
            if not block or block != frozen[offset : offset + len(block)]:
                raise ChildInventoryError("{0} bytes changed on replay".format(label))
            offset += len(block)
            _replay_capture_member(snapshot, record)
        if offset != len(frozen) or os.read(record["descriptor"], 1):
            raise ChildInventoryError("{0} bytes changed on replay".format(label))
    except ChildInventoryError:
        raise
    except OSError as error:
        raise ChildInventoryError("cannot read {0}: {1}".format(label, error))
    _replay_capture_member(snapshot, record)
    return frozen


def _close_capture_snapshot(snapshot):
    for record in reversed(list(snapshot["members"].values())):
        os.close(record["descriptor"])
    _close_descriptor_rooted_directory(snapshot["directories"])


def _open_capture_snapshot(directory, authority):
    label = "capture directory"
    try:
        _path, directories, metadata = _open_descriptor_rooted_directory(
            directory, label
        )
    except ChildInventoryError:
        raise
    except OSError as error:
        raise ChildInventoryError(
            "cannot open descriptor-rooted {0}: {1}".format(label, error)
        )
    snapshot = {
        "bytes": {},
        "directories": directories,
        "directory_descriptor": directories[-1]["descriptor"],
        "directory_identity": _bounded_file_identity(metadata),
        "members": {},
        "names": None,
    }
    try:
        if (
            not stat.S_ISDIR(metadata.st_mode)
            or stat.S_IMODE(metadata.st_mode)
            != int(authority["artifact_policy"]["directory_mode"], 8)
        ):
            raise ChildInventoryError("capture directory mode or type differs")
        names = _capture_directory_names(snapshot["directory_descriptor"], label)
        require_exact(
            names, authority["artifact_policy"]["output_members"], "capture members"
        )
        snapshot["names"] = names

        nofollow = getattr(os, "O_NOFOLLOW", None)
        if nofollow is None:
            raise ChildInventoryError(
                "descriptor-rooted O_NOFOLLOW is unavailable for capture members"
            )
        flags = (
            os.O_RDONLY
            | nofollow
            | getattr(os, "O_CLOEXEC", 0)
            | getattr(os, "O_NONBLOCK", 0)
        )
        expected_mode = int(authority["artifact_policy"]["member_mode"], 8)
        for name in names:
            _capture_member_cap(name, authority)
            member_descriptor = None
            try:
                member_descriptor = os.open(
                    name, flags, dir_fd=snapshot["directory_descriptor"]
                )
                member_metadata = os.fstat(member_descriptor)
                named_metadata = os.stat(
                    name,
                    dir_fd=snapshot["directory_descriptor"],
                    follow_symlinks=False,
                )
                identity = _bounded_file_identity(member_metadata)
                if (
                    not stat.S_ISREG(member_metadata.st_mode)
                    or not stat.S_ISREG(named_metadata.st_mode)
                    or member_metadata.st_nlink != 1
                    or stat.S_IMODE(member_metadata.st_mode) != expected_mode
                    or _bounded_file_identity(named_metadata) != identity
                ):
                    raise ChildInventoryError(
                        "capture member {0} type, mode, link count, or identity differs".format(
                            name
                        )
                    )
                snapshot["members"][name] = {
                    "descriptor": member_descriptor,
                    "identity": identity,
                    "name": name,
                    "size": member_metadata.st_size,
                }
                member_descriptor = None
            finally:
                if member_descriptor is not None:
                    os.close(member_descriptor)

        for name in names:
            snapshot["bytes"][name] = _read_capture_snapshot_member(
                snapshot,
                snapshot["members"][name],
                _capture_member_cap(name, authority),
            )
        return snapshot
    except ChildInventoryError:
        _close_capture_snapshot(snapshot)
        raise
    except OSError as error:
        _close_capture_snapshot(snapshot)
        raise ChildInventoryError(
            "cannot snapshot capture directory: {0}".format(error)
        )
    except Exception:
        _close_capture_snapshot(snapshot)
        raise


def _replay_capture_snapshot(snapshot, authority):
    names = _capture_directory_names(
        snapshot["directory_descriptor"], "capture directory replay"
    )
    require_exact(
        names, authority["artifact_policy"]["output_members"], "capture member replay"
    )
    for name in snapshot["names"]:
        _replay_capture_member(snapshot, snapshot["members"][name])
    _replay_descriptor_rooted_directories(
        snapshot["directories"], "capture directory replay"
    )
    try:
        retained = os.fstat(snapshot["directory_descriptor"])
        final_record = snapshot["directories"][-1]
        if final_record["name"] is None:
            named = retained
        else:
            named = os.stat(
                final_record["name"],
                dir_fd=final_record["parent_descriptor"],
                follow_symlinks=False,
            )
    except OSError as error:
        raise ChildInventoryError(
            "cannot replay capture directory identity: {0}".format(error)
        )
    if (
        not stat.S_ISDIR(retained.st_mode)
        or not stat.S_ISDIR(named.st_mode)
        or _bounded_file_identity(retained) != snapshot["directory_identity"]
        or _bounded_file_identity(named) != snapshot["directory_identity"]
    ):
        raise ChildInventoryError("capture directory identity changed")


def _parse_jsonl(data, container, cap):
    if len(data) > cap or not data or not data.endswith(b"\n"):
        raise ChildInventoryError("archive member stream is empty, truncated, or oversized")
    records = []
    previous = None
    for line in data.splitlines(keepends=True):
        record = read_json_bytes(line, "archive member row", canonical=True)
        validate_member_record(record, container)
        if previous is not None and record["path"] <= previous:
            raise ChildInventoryError("archive member rows are duplicated or unsorted")
        previous = record["path"]
        records.append(record)
    return records


def _verify_capture_snapshot(snapshot, authority, contract_bytes):
    actual_names = snapshot["names"]
    member_bytes = snapshot["bytes"]
    checksum_bytes = member_bytes["SHA256SUMS"]
    summary_bytes = member_bytes["child-inventory-summary.json"]
    expected_checksums = b"".join(
        (
            hashlib.sha256(member_bytes[name]).hexdigest() + "  " + name + "\n"
        ).encode("ascii")
        for name in sorted(actual_names)
        if name != "SHA256SUMS"
    )
    require_exact(checksum_bytes, expected_checksums, "capture checksums")
    summary = read_json_bytes(summary_bytes, "child inventory summary", canonical=True)
    exact_keys(
        summary,
        {
            "artifact_status",
            "binding",
            "blockers",
            "claims",
            "containers",
            "contract",
            "gate",
            "result_authority_status",
            "schema_version",
            "source_commit",
        },
        "child inventory summary",
    )
    require_exact(summary["schema_version"], SCHEMA_VERSION, "summary schema")
    require_exact(summary["artifact_status"], "temporary-unreviewed-capture", "artifact status")
    validate_capture_binding(summary["binding"])
    require_exact(summary["claims"], EXPECTED_CLAIMS, "summary claims")
    require_exact(summary["gate"], EXPECTED_GATE, "summary gate")
    require_exact(summary["blockers"], authority["remaining_blockers"], "summary blockers")
    require_exact(summary["result_authority_status"], "required-missing", "result authority")
    require_exact(summary["source_commit"], SOURCE_COMMIT, "summary source commit")
    require_exact(
        summary["contract"],
        {
            "contract_id": CONTRACT_ID,
            "path": CONTRACT_PATH.as_posix(),
            "sha256": hashlib.sha256(contract_bytes).hexdigest(),
            "size": len(contract_bytes),
        },
        "summary contract binding",
    )
    if type(summary["containers"]) is not list or len(summary["containers"]) != 2:
        raise ChildInventoryError("summary container closure differs")
    for expected_container, row in zip(authority["containers"], summary["containers"]):
        exact_keys(row, {"capture", "container", "stream"}, "summary container row")
        require_exact(row["container"], expected_container, "summary container")
        stream = exact_keys(
            row["stream"],
            {
                "compressed_sha256",
                "compressed_size",
                "member",
                "uncompressed_sha256",
                "uncompressed_size",
            },
            "summary stream",
        )
        require_exact(stream["member"], expected_container["output_member"], "stream member")
        compressed = member_bytes[stream["member"]]
        require_exact(len(compressed), stream["compressed_size"], "compressed size")
        require_exact(
            hashlib.sha256(compressed).hexdigest(), stream["compressed_sha256"], "compressed digest"
        )
        uncompressed = _decompress_canonical_gzip(
            compressed,
            authority["capture_policy"]["maximum_jsonl_uncompressed_bytes"],
        )
        require_exact(len(uncompressed), stream["uncompressed_size"], "uncompressed size")
        require_exact(
            hashlib.sha256(uncompressed).hexdigest(),
            stream["uncompressed_sha256"],
            "uncompressed digest",
        )
        records = _parse_jsonl(
            uncompressed,
            expected_container,
            authority["capture_policy"]["maximum_jsonl_uncompressed_bytes"],
        )
        regular_bytes = validate_record_collection(records, expected_container)
        _require_canonical_gzip_recompression(compressed, records)
        derived = _derive_capture(
            expected_container,
            records,
            regular_bytes,
        )
        require_exact(derived, row["capture"], "summary capture closure")
    _replay_capture_snapshot(snapshot, authority)
    return summary


def verify_capture(directory, authority, contract_bytes):
    validate_contract_schema(authority)
    snapshot = _open_capture_snapshot(directory, authority)
    try:
        return _verify_capture_snapshot(snapshot, authority, contract_bytes)
    finally:
        _close_capture_snapshot(snapshot)


def capture(repo, args):
    authority, contract_bytes = check_repository(repo)
    paths = {
        "stablelists": Path(args.stablelists_archive),
        "kabi-dw": Path(args.kabi_dw_archive),
    }
    results = [
        inventory_tar_xz(paths[container["namespace"]], container, authority["capture_policy"])
        for container in authority["containers"]
    ]
    binding = {
        "container_image": args.container_image,
        "github_head_sha": args.github_head_sha,
        "github_repository": args.github_repository,
        "github_run_attempt": args.github_run_attempt,
        "github_run_id": args.github_run_id,
    }
    summary = write_capture(
        Path(args.output_dir), authority, contract_bytes, results, binding
    )
    print(
        "RK-001 child inventory v2 captured (NOT REVIEWED, NO CREDIT): "
        "stablelists={0} kabi-dw={1} result-authority=required-missing".format(
            summary["containers"][0]["capture"]["review_unit_count"],
            summary["containers"][1]["capture"]["review_unit_count"],
        )
    )


def parse_args(argv):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=ROOT)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--check", action="store_true")
    modes.add_argument("--capture", action="store_true")
    modes.add_argument("--verify-capture", type=Path)
    parser.add_argument("--stablelists-archive", type=Path)
    parser.add_argument("--kabi-dw-archive", type=Path)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--github-head-sha")
    parser.add_argument("--github-run-id")
    parser.add_argument("--github-run-attempt")
    parser.add_argument("--github-repository")
    parser.add_argument("--container-image")
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    try:
        if args.check:
            authority, _contract_bytes = check_repository(args.repo)
            print(
                "RK-001 child inventory v2 contract PASS: containers={0} "
                "counts=required-missing gate=TODO credit=0".format(
                    len(authority["containers"])
                )
            )
        elif args.verify_capture is not None:
            authority, contract_bytes = check_repository(args.repo)
            summary = verify_capture(args.verify_capture, authority, contract_bytes)
            print(
                "RK-001 child inventory v2 capture verified (NOT REVIEWED, NO CREDIT): "
                "members={0} result-authority={1}".format(
                    sum(row["capture"]["member_count"] for row in summary["containers"]),
                    summary["result_authority_status"],
                )
            )
        else:
            required = {
                "--container-image": args.container_image,
                "--github-head-sha": args.github_head_sha,
                "--github-repository": args.github_repository,
                "--github-run-attempt": args.github_run_attempt,
                "--github-run-id": args.github_run_id,
                "--kabi-dw-archive": args.kabi_dw_archive,
                "--output-dir": args.output_dir,
                "--stablelists-archive": args.stablelists_archive,
            }
            missing = sorted(name for name, value in required.items() if value is None)
            if missing:
                raise ChildInventoryError(
                    "capture arguments are missing: {0}".format(", ".join(missing))
                )
            capture(args.repo, args)
        return 0
    except ChildInventoryError as error:
        print("RK-001 child inventory v2 ERROR: {0}".format(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
