#!/usr/bin/env python3
"""Verify externally signed, non-crediting RK-001 reviewer responses.

This checker proves exact campaign-packet binding, response structure, and an
SSHSIG from a registered reviewer.  Durable archival is a separate required
authority and is never proven by this checker or its temporary Actions report.
The contract shipped by this repository has no registered production reviewer
and cannot award RK-001 or tracker credit.
"""

from __future__ import print_function

import argparse
import base64
import binascii
import datetime
import hashlib
import json
import os
import re
import stat
import subprocess
import sys
import tempfile
import types
from pathlib import Path, PurePosixPath


REPO_ROOT = Path(__file__).resolve().parents[1]
AUTHORITY_PATH = Path(
    "host-kernel/rocky/evidence/rk001-license-review-response-contract-ef58-v1.json"
)
# Frozen only after the campaign authority and response workflow reach final bytes.
AUTHORITY_SHA256 = "c71bbb5432d61106f7c86ec0f05a76e804586c57d2ad189b94e4b010bb4deaec"
SCHEMA_VERSION = 1
CONTRACT_ID = "rk-001-license-review-response-ef58860e-v1"
CAMPAIGN_ID = "rk-001-license-review-campaign-ef58860e-v1"
SOURCE_COMMIT = "ef58860e4806ee16e2c506e4e93c7b6ad8ad8f4b"
SIGNATURE_NAMESPACE = "mckernel-rk001-license-review-response-v1"

MAX_AUTHORITY_BYTES = 2 * 1024 * 1024
MAX_CHECKER_BYTES = 2 * 1024 * 1024
MAX_ROOT_BYTES = 1024 * 1024
MAX_SIGNATURE_BYTES = 64 * 1024
MAX_STREAM_BYTES = 256 * 1024 * 1024
MAX_LINE_BYTES = 2 * 1024 * 1024
MAX_RESPONSE_BYTES = 384 * 1024 * 1024
MAX_SUPPORT_BYTES = 128 * 1024 * 1024
MAX_SUPPORT_MEMBER_BYTES = 32 * 1024 * 1024
MAX_UNIT_RECORDS = 3000
MAX_FINDING_RECORDS = 1024
MAX_ARCHIVE_RECORDS = 8
MAX_ARCHIVE_MEMBER_RECORDS = 200000
MAX_SUPPORT_RECORDS = 4096
MAX_JSON_NESTING = 64
MAX_JSON_NUMBER_TOKEN = 128

HEX_SHA256 = re.compile(r"^[0-9a-f]{64}$")
PACKET_ID_PATTERN = re.compile(r"^[0-9]{4}$")
STABLE_ID_PATTERN = re.compile(r"^[a-z][a-z0-9-]*:[0-9a-f]{64}$")
IDENTITY_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._@+-]{0,127}$")
AUTHORITY_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._:-]{0,127}$")
RFC3339_UTC = re.compile(
    r"^[0-9]{4}-(0[1-9]|1[0-2])-([0-2][0-9]|3[01])T"
    r"([01][0-9]|2[0-3]):[0-5][0-9]:[0-5][0-9]Z$"
)

TOP_LEVEL_MEMBERS = {
    "SHA256SUMS",
    "archive-expansions.jsonl",
    "archive-members.jsonl",
    "content-findings.jsonl",
    "response-root.json",
    "response-root.sig",
    "support-index.jsonl",
    "unit-decisions.jsonl",
}
STREAM_MEMBERS = (
    "content-findings.jsonl",
    "unit-decisions.jsonl",
    "archive-expansions.jsonl",
    "archive-members.jsonl",
    "support-index.jsonl",
)

EXPECTED_CLAIMS = {
    "archive_expansion_complete": False,
    "campaign_complete": False,
    "credit_eligible": False,
    "durable_archive": False,
    "independent_legal_review_complete": False,
    "provenance_review_complete": False,
    "redistribution_approved": False,
    "reviewer_registered": False,
    "tracker_credit": False,
}
EXPECTED_GATE = {
    "credit_eligible": False,
    "gate_id": "RK-001",
    "points_awarded": 0,
    "status": "TODO",
    "tracker_credit": False,
}
EXPECTED_ATTESTATION_FALSE = {
    "content_findings_auto_resolve_paths": False,
    "credit_eligible": False,
    "durable_archive": False,
    "machine_classification_auto_accepted": False,
    "tracker_credit": False,
}

# The response authority intentionally retains the exact ef58860e campaign and
# capture implementation descriptors.  These separately pinned current files
# are compatibility consumers only; they cannot alter the historical campaign,
# response root, claims, gate, or artifact identities.
CURRENT_IMPLEMENTATION_OVERRIDES = {
    "scripts/rocky_kernel_license_review_campaign.py": {
        "path": "scripts/rocky_kernel_license_review_campaign.py",
        "sha256": "02305bcecf42e3b3919535c2104977a1a6e75fece7e5333a916a8ec4c2091f30",
        "size": 82394,
    },
    "scripts/tests/test_rocky_kernel_license_review_campaign.py": {
        "path": "scripts/tests/test_rocky_kernel_license_review_campaign.py",
        "sha256": "1960901c58a33bb39d791db4ddd406ac42c5a62c8eef2879b960c38832bdc192",
        "size": 46015,
    },
    "scripts/rocky_kernel_license_inventory.py": {
        "path": "scripts/rocky_kernel_license_inventory.py",
        "sha256": "e6aa0340364fb033a4a7fce78a1c232103449b1fa1398176ec9eaa4ad8dce4c7",
        "size": 66347,
    },
    "host-kernel/rocky/source-lock.json": {
        "path": "host-kernel/rocky/source-lock.json",
        "sha256": "b70df1e475072dbfa31fdc712900ac59d30eeb139219c7076aacaa19abf0fded",
        "size": 18336,
    },
    "scripts/rocky_kernel_source_lock.py": {
        "path": "scripts/rocky_kernel_source_lock.py",
        "sha256": "d127c497245ba373f68f5d6e6fc934369b368b665365bd1f46d05ff08f8b3718",
        "size": 60175,
    },
}


class ReviewResponseError(RuntimeError):
    """Raised when a response contract, package, or signature fails closed."""


def reject_duplicate_pairs(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ReviewResponseError("duplicate JSON key: {0}".format(key))
        value[key] = item
    return value


def parse_bounded_json_int(token):
    if type(token) is not str or len(token) > MAX_JSON_NUMBER_TOKEN:
        raise ReviewResponseError("JSON integer token exceeds its cap")
    try:
        return int(token, 10)
    except ValueError as error:
        raise ReviewResponseError("JSON integer token is invalid: {0}".format(error))


def reject_json_float(token):
    if type(token) is not str or len(token) > MAX_JSON_NUMBER_TOKEN:
        raise ReviewResponseError("JSON float token exceeds its cap")
    raise ReviewResponseError("JSON floating-point values are forbidden")


def reject_json_constant(token):
    raise ReviewResponseError("nonfinite JSON value is forbidden: {0}".format(token))


def require_bounded_json_nesting(value):
    stack = [(value, 0)]
    while stack:
        current, depth = stack.pop()
        if depth > MAX_JSON_NESTING:
            raise ReviewResponseError("JSON nesting exceeds its cap")
        if isinstance(current, dict):
            stack.extend((item, depth + 1) for item in current.values())
        elif isinstance(current, (list, tuple)):
            stack.extend((item, depth + 1) for item in current)


def canonical_json(value, newline=False):
    require_bounded_json_nesting(value)
    try:
        data = json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("ascii")
    except (RecursionError, TypeError, ValueError) as error:
        raise ReviewResponseError("value is not canonical JSON: {0}".format(error))
    return data + (b"\n" if newline else b"")


def read_json_bytes(data, label, canonical=False):
    try:
        value = json.loads(
            data.decode("ascii"),
            object_pairs_hook=reject_duplicate_pairs,
            parse_constant=reject_json_constant,
            parse_float=reject_json_float,
            parse_int=parse_bounded_json_int,
        )
    except ReviewResponseError:
        raise
    except (RecursionError, UnicodeError, ValueError) as error:
        raise ReviewResponseError("{0} is not valid JSON: {1}".format(label, error))
    require_bounded_json_nesting(value)
    if type(value) is not dict:
        raise ReviewResponseError("{0} must be a JSON object".format(label))
    if canonical and data != canonical_json(value, newline=True):
        raise ReviewResponseError("{0} is not canonical JSON".format(label))
    return value


def exact_keys(value, keys, label):
    if type(value) is not dict or set(value) != set(keys):
        raise ReviewResponseError("{0} fields changed".format(label))
    return value


def require_exact(actual, expected, label):
    if type(actual) is not type(expected):
        raise ReviewResponseError("{0} type changed".format(label))
    if isinstance(expected, dict):
        if set(actual) != set(expected):
            raise ReviewResponseError("{0} fields changed".format(label))
        for key in expected:
            require_exact(actual[key], expected[key], label + "." + str(key))
        return
    if isinstance(expected, list):
        if len(actual) != len(expected):
            raise ReviewResponseError("{0} length changed".format(label))
        for index, values in enumerate(zip(actual, expected)):
            require_exact(values[0], values[1], label + "[{0}]".format(index))
        return
    if actual != expected:
        raise ReviewResponseError(
            "{0} differs: {1!r} != {2!r}".format(label, actual, expected)
        )


def require_bool(value, label):
    if type(value) is not bool:
        raise ReviewResponseError("{0} is not a boolean".format(label))
    return value


def require_nonnegative_int(value, label):
    if type(value) is not int or value < 0:
        raise ReviewResponseError("{0} is not a nonnegative integer".format(label))
    return value


def require_sha256(value, label):
    if type(value) is not str or not HEX_SHA256.fullmatch(value):
        raise ReviewResponseError("{0} is not a lowercase SHA-256".format(label))
    return value


def require_string(value, label, maximum=4096, allow_empty=False):
    if type(value) is not str or (not value and not allow_empty) or len(value) > maximum:
        raise ReviewResponseError("{0} is not a bounded string".format(label))
    if "\x00" in value:
        raise ReviewResponseError("{0} contains NUL".format(label))
    return value


def require_utc_timestamp(value, label):
    value = require_string(value, label, 32)
    if not RFC3339_UTC.fullmatch(value):
        raise ReviewResponseError("{0} is not UTC RFC3339".format(label))
    try:
        datetime.datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError as error:
        raise ReviewResponseError("{0} is not a real UTC time: {1}".format(label, error))
    return value


def safe_relative(value, label):
    require_string(value, label)
    if "\\" in value:
        raise ReviewResponseError("{0} contains a backslash".format(label))
    path = PurePosixPath(value)
    if (
        path.is_absolute()
        or path.as_posix() != value
        or any(part in ("", ".", "..") for part in path.parts)
    ):
        raise ReviewResponseError("{0} is not normalized".format(label))
    return value


def require_sorted_unique_strings(value, label, maximum=4096):
    if type(value) is not list or len(value) > maximum:
        raise ReviewResponseError("{0} is not a bounded list".format(label))
    previous = None
    for item in value:
        require_string(item, label + " item")
        if previous is not None and item <= previous:
            raise ReviewResponseError("{0} is duplicated or unsorted".format(label))
        previous = item
    return value


def _stat_identity(info):
    return (
        info.st_dev,
        info.st_ino,
        info.st_mode,
        info.st_nlink,
        info.st_size,
        info.st_uid,
        info.st_gid,
        getattr(info, "st_mtime_ns", int(info.st_mtime * 1000000000)),
        getattr(info, "st_ctime_ns", int(info.st_ctime * 1000000000)),
    )


def _directory_identity(info):
    return (
        info.st_dev,
        info.st_ino,
        info.st_mode,
        info.st_nlink,
        info.st_uid,
        info.st_gid,
        info.st_size,
        getattr(info, "st_mtime_ns", int(info.st_mtime * 1000000000)),
        getattr(info, "st_ctime_ns", int(info.st_ctime * 1000000000)),
    )


def _safe_component(value, label):
    if type(value) is not str or value in ("", ".", "..") or "/" in value or "\\" in value or "\x00" in value:
        raise ReviewResponseError("{0} is unsafe".format(label))
    return value


def _replay_held_regular(context, label):
    for record in context["directory_chain"]:
        try:
            opened = os.fstat(record["descriptor"])
            namespace = (
                opened
                if record["parent_fd"] is None
                else os.stat(
                    record["name"],
                    dir_fd=record["parent_fd"],
                    follow_symlinks=False,
                )
            )
        except OSError as error:
            raise ReviewResponseError(
                "{0} directory namespace changed: {1}".format(label, error)
            )
        if (
            _directory_identity(opened) != record["identity"]
            or _directory_identity(namespace) != record["identity"]
        ):
            raise ReviewResponseError("{0} directory namespace changed".format(label))
    try:
        opened = os.fstat(context["descriptor"])
        namespace = os.stat(
            context["name"],
            dir_fd=context["parent_fd"],
            follow_symlinks=False,
        )
    except OSError as error:
        raise ReviewResponseError("{0} file namespace changed: {1}".format(label, error))
    if (
        _stat_identity(opened) != context["identity"]
        or _stat_identity(namespace) != context["identity"]
    ):
        raise ReviewResponseError("{0} file namespace changed".format(label))


def _read_held_regular_pass(context, label, size_cap):
    _replay_held_regular(context, label)
    expected_size = context["identity"][4]
    try:
        os.lseek(context["descriptor"], 0, os.SEEK_SET)
        chunks = []
        retained = 0
        while retained < expected_size:
            chunk = os.read(
                context["descriptor"], min(1024 * 1024, expected_size - retained)
            )
            if not chunk:
                raise ReviewResponseError("{0} ended before its bound size".format(label))
            retained += len(chunk)
            if retained > size_cap:
                raise ReviewResponseError("{0} exceeds its size cap".format(label))
            chunks.append(chunk)
            _replay_held_regular(context, label)
        if os.read(context["descriptor"], 1):
            raise ReviewResponseError("{0} grew while read".format(label))
    except ReviewResponseError:
        raise
    except OSError as error:
        raise ReviewResponseError("cannot read {0}: {1}".format(label, error))
    _replay_held_regular(context, label)
    data = b"".join(chunks)
    if len(data) != expected_size:
        raise ReviewResponseError("{0} size changed while read".format(label))
    return data


def read_regular_file_once(path, label, size_cap):
    raw = str(path)
    raw_parts = raw.split(os.sep)
    comparable = raw_parts[1:] if os.path.isabs(raw) else raw_parts
    if (
        not raw
        or "\x00" in raw
        or "\\" in raw
        or any(part in ("", ".", "..") for part in comparable)
    ):
        raise ReviewResponseError("{0} path is unsafe".format(label))
    requested = Path(os.path.abspath(raw))
    if requested.anchor != os.sep or len(requested.parts) < 2:
        raise ReviewResponseError("{0} path is not an absolute file path".format(label))
    directory_flags = (
        os.O_RDONLY
        | getattr(os, "O_DIRECTORY", 0)
        | getattr(os, "O_NOFOLLOW", 0)
        | getattr(os, "O_CLOEXEC", 0)
    )
    file_flags = (
        os.O_RDONLY
        | getattr(os, "O_NOFOLLOW", 0)
        | getattr(os, "O_CLOEXEC", 0)
        | getattr(os, "O_NONBLOCK", 0)
    )
    if hasattr(os, "O_BINARY"):
        file_flags |= os.O_BINARY
    chain = []
    descriptor = None
    try:
        root_fd = os.open(requested.anchor, directory_flags)
        root_info = os.fstat(root_fd)
        if not stat.S_ISDIR(root_info.st_mode):
            raise ReviewResponseError("{0} root is not a directory".format(label))
        chain.append(
            {
                "descriptor": root_fd,
                "identity": _directory_identity(root_info),
                "name": None,
                "parent_fd": None,
            }
        )
        current = root_fd
        for component in requested.parts[1:-1]:
            _safe_component(component, label + " directory component")
            following = None
            try:
                following = os.open(component, directory_flags, dir_fd=current)
                following_info = os.fstat(following)
                namespace = os.stat(component, dir_fd=current, follow_symlinks=False)
            except OSError:
                if following is not None:
                    os.close(following)
                raise
            if (
                not stat.S_ISDIR(following_info.st_mode)
                or _directory_identity(following_info) != _directory_identity(namespace)
            ):
                os.close(following)
                raise ReviewResponseError(
                    "{0} directory component identity changed".format(label)
                )
            chain.append(
                {
                    "descriptor": following,
                    "identity": _directory_identity(following_info),
                    "name": component,
                    "parent_fd": current,
                }
            )
            current = following
        name = _safe_component(requested.parts[-1], label + " filename")
        descriptor = os.open(name, file_flags, dir_fd=current)
        opened = os.fstat(descriptor)
        namespace = os.stat(name, dir_fd=current, follow_symlinks=False)
        if (
            not stat.S_ISREG(opened.st_mode)
            or _stat_identity(opened) != _stat_identity(namespace)
            or opened.st_size > size_cap
        ):
            raise ReviewResponseError("{0} is not the bounded opened regular file".format(label))
        context = {
            "descriptor": descriptor,
            "directory_chain": chain,
            "identity": _stat_identity(opened),
            "name": name,
            "parent_fd": current,
        }
        first = _read_held_regular_pass(context, label, size_cap)
        second = _read_held_regular_pass(context, label, size_cap)
        if first != second:
            raise ReviewResponseError("{0} byte replay differs".format(label))
        _replay_held_regular(context, label)
        return second
    except ReviewResponseError:
        raise
    except OSError as error:
        raise ReviewResponseError("cannot open {0}: {1}".format(label, error))
    finally:
        if descriptor is not None:
            try:
                os.close(descriptor)
            except OSError:
                pass
        for record in reversed(chain):
            try:
                os.close(record["descriptor"])
            except OSError:
                pass


def _read_descriptor(descriptor, label, cap):
    chunks = []
    retained = 0
    while True:
        chunk = os.read(descriptor, min(1024 * 1024, cap - retained + 1))
        if not chunk:
            break
        retained += len(chunk)
        if retained > cap:
            raise ReviewResponseError("{0} exceeds its size cap".format(label))
        chunks.append(chunk)
    return b"".join(chunks)


def _read_bound(repo, record, label, cap=MAX_CHECKER_BYTES):
    exact_keys(record, {"path", "sha256", "size"}, label + " record")
    active_record = CURRENT_IMPLEMENTATION_OVERRIDES.get(record["path"], record)
    require_exact(active_record["path"], record["path"], label + " compatibility path")
    path = Path(repo) / safe_relative(active_record["path"], label + " path")
    data = read_regular_file_once(path, label, cap)
    if (
        len(data)
        != require_nonnegative_int(active_record["size"], label + " size")
        or hashlib.sha256(data).hexdigest() != require_sha256(
            active_record["sha256"], label + " digest"
        )
    ):
        raise ReviewResponseError("{0} bytes differ".format(label))
    return path, data


def _public_key_fingerprint(public_key, expected_type):
    parts = require_string(public_key, "reviewer SSH public key", 16384).split(" ")
    if len(parts) != 2 or parts[0] != expected_type:
        raise ReviewResponseError("reviewer SSH public key format differs")
    try:
        blob = base64.b64decode(parts[1].encode("ascii"), validate=True)
    except (UnicodeError, binascii.Error) as error:
        raise ReviewResponseError("reviewer SSH public key is invalid: {0}".format(error))
    if len(blob) < 16 or len(blob) > 16384:
        raise ReviewResponseError("reviewer SSH public key blob is unbounded")
    if base64.b64encode(blob).decode("ascii") != parts[1]:
        raise ReviewResponseError("reviewer SSH public key is not canonical base64")

    def ssh_string(offset, label):
        if offset + 4 > len(blob):
            raise ReviewResponseError("reviewer SSH public key lacks {0}".format(label))
        length = int.from_bytes(blob[offset : offset + 4], "big")
        start = offset + 4
        end = start + length
        if length > 16384 or end > len(blob):
            raise ReviewResponseError("reviewer SSH public key {0} is invalid".format(label))
        return blob[start:end], end

    wire_type, offset = ssh_string(0, "wire type")
    key_bytes, offset = ssh_string(offset, "key bytes")
    try:
        wire_type_text = wire_type.decode("ascii")
    except UnicodeError as error:
        raise ReviewResponseError("reviewer SSH public key wire type is invalid: {0}".format(error))
    if wire_type_text != expected_type or len(key_bytes) != 32 or offset != len(blob):
        raise ReviewResponseError("reviewer SSH public key wire structure differs")
    digest = base64.b64encode(hashlib.sha256(blob).digest()).decode("ascii").rstrip("=")
    return "SHA256:" + digest


REVIEWER_KEYS = {
    "authority_id",
    "independence_authority_sha256",
    "independent_from_capture",
    "key_type",
    "packet_max",
    "packet_min",
    "reviewer_identity",
    "ssh_fingerprint",
    "ssh_public_key",
    "valid_from",
    "valid_through",
}


def validate_reviewer(record):
    exact_keys(record, REVIEWER_KEYS, "registered reviewer")
    if not AUTHORITY_ID_PATTERN.fullmatch(
        require_string(record["authority_id"], "reviewer authority ID", 128)
    ):
        raise ReviewResponseError("reviewer authority ID is malformed")
    if not IDENTITY_PATTERN.fullmatch(
        require_string(record["reviewer_identity"], "reviewer identity", 128)
    ):
        raise ReviewResponseError("reviewer identity is malformed")
    require_exact(record["key_type"], "ssh-ed25519", "reviewer key type")
    require_exact(
        _public_key_fingerprint(record["ssh_public_key"], record["key_type"]),
        require_string(record["ssh_fingerprint"], "reviewer fingerprint", 128),
        "reviewer SSH fingerprint",
    )
    require_sha256(
        record["independence_authority_sha256"],
        "reviewer independence authority digest",
    )
    require_exact(
        require_bool(record["independent_from_capture"], "reviewer independence"),
        True,
        "reviewer independence",
    )
    for key in ("valid_from", "valid_through"):
        require_utc_timestamp(record[key], "reviewer " + key)
    if record["valid_from"] > record["valid_through"]:
        raise ReviewResponseError("reviewer validity interval is reversed")
    for key in ("packet_min", "packet_max"):
        value = require_string(record[key], "reviewer " + key, 4)
        if not PACKET_ID_PATTERN.fullmatch(value):
            raise ReviewResponseError("reviewer packet scope is malformed")
    if record["packet_min"] > record["packet_max"]:
        raise ReviewResponseError("reviewer packet scope is reversed")
    return record


def _validate_bound_input(record, label, provisional):
    exact_keys(record, {"path", "sha256", "size"}, label)
    safe_relative(record["path"], label + " path")
    if provisional:
        if record["sha256"] is not None or record["size"] is not None:
            raise ReviewResponseError("provisional {0} identity must be null".format(label))
    else:
        require_sha256(record["sha256"], label + " digest")
        require_nonnegative_int(record["size"], label + " size")


def validate_authority(authority):
    exact_keys(
        authority,
        {
            "archive_expansion_policy",
            "campaign_closure",
            "claims",
            "decision_policy",
            "durability_policy",
            "gate",
            "inputs",
            "remaining_blockers",
            "response_contract_id",
            "response_package_policy",
            "reviewer_authority_policy",
            "schema_version",
            "signature_policy",
            "verification_scope",
        },
        "review-response authority",
    )
    require_exact(authority["schema_version"], SCHEMA_VERSION, "schema version")
    require_exact(authority["response_contract_id"], CONTRACT_ID, "contract ID")
    require_exact(authority["claims"], EXPECTED_CLAIMS, "claims")
    require_exact(authority["gate"], EXPECTED_GATE, "gate")
    scope = exact_keys(
        authority["verification_scope"],
        {
            "aggregate_index_supported",
            "campaign_closure_can_be_established",
            "mode",
            "required_campaign_packet_count",
        },
        "verification scope",
    )
    require_exact(scope["mode"], "single-packet-only", "verification mode")
    require_exact(scope["aggregate_index_supported"], False, "aggregate-index support")
    require_exact(
        scope["campaign_closure_can_be_established"],
        False,
        "campaign-closure capability",
    )
    require_exact(scope["required_campaign_packet_count"], 219, "campaign packet count")

    closure = exact_keys(
        authority["campaign_closure"],
        {
            "archive_bindings",
            "binding_status",
            "campaign_id",
            "content_group_count",
            "packet_count",
            "review_unit_count",
            "source_commit",
        },
        "campaign closure",
    )
    status = closure["binding_status"]
    if status not in ("provisional-unfrozen", "frozen"):
        raise ReviewResponseError("campaign binding status is invalid")
    provisional = status == "provisional-unfrozen"
    require_exact(closure["campaign_id"], CAMPAIGN_ID, "campaign ID")
    require_exact(closure["source_commit"], SOURCE_COMMIT, "campaign source commit")
    for key, value in (
        ("packet_count", 219),
        ("review_unit_count", 115265),
        ("content_group_count", 111004),
    ):
        require_exact(closure[key], value, "campaign " + key)
    if type(closure["archive_bindings"]) is not list:
        raise ReviewResponseError("archive bindings must be a list")
    previous_group = None
    for binding in closure["archive_bindings"]:
        validate_archive_binding(binding)
        group_id = binding["container"]["group_id"]
        if previous_group is not None and group_id <= previous_group:
            raise ReviewResponseError("archive bindings are duplicated or unsorted")
        previous_group = group_id
    if provisional and closure["archive_bindings"]:
        raise ReviewResponseError("provisional campaign cannot freeze archive bindings")
    if not provisional and len(closure["archive_bindings"]) != 3:
        raise ReviewResponseError("frozen campaign needs exactly three archive bindings")
    if not provisional and [binding["role"] for binding in closure["archive_bindings"]].count(
        "existing-inventory-closure"
    ) != 1:
        raise ReviewResponseError("frozen campaign needs one existing archive closure")

    inputs = exact_keys(
        authority["inputs"],
        {
            "campaign_authority",
            "campaign_checker",
            "campaign_tests",
            "campaign_workflow",
            "inventory_checker",
            "response_workflow",
            "source_lock",
            "source_lock_validator",
        },
        "authority inputs",
    )
    for key, record in inputs.items():
        _validate_bound_input(record, "input " + key, provisional)

    reviewers = exact_keys(
        authority["reviewer_authority_policy"],
        {
            "independence_registration_required",
            "registered_reviewers",
            "registration_status",
            "self_asserted_identity_forbidden",
        },
        "reviewer authority policy",
    )
    require_exact(
        reviewers["independence_registration_required"], True,
        "reviewer independence registration",
    )
    require_exact(
        reviewers["self_asserted_identity_forbidden"], True,
        "self-asserted reviewer identity policy",
    )
    if reviewers["registration_status"] not in ("required-missing", "registered"):
        raise ReviewResponseError("reviewer registration status is invalid")
    if type(reviewers["registered_reviewers"]) is not list:
        raise ReviewResponseError("registered reviewers must be a list")
    previous = None
    seen_identity = set()
    seen_fingerprint = set()
    for reviewer in reviewers["registered_reviewers"]:
        validate_reviewer(reviewer)
        authority_id = reviewer["authority_id"]
        if previous is not None and authority_id <= previous:
            raise ReviewResponseError("reviewer authorities are duplicated or unsorted")
        if reviewer["reviewer_identity"] in seen_identity:
            raise ReviewResponseError("reviewer identity is registered twice")
        if reviewer["ssh_fingerprint"] in seen_fingerprint:
            raise ReviewResponseError("reviewer key is registered twice")
        previous = authority_id
        seen_identity.add(reviewer["reviewer_identity"])
        seen_fingerprint.add(reviewer["ssh_fingerprint"])
    if reviewers["registration_status"] == "required-missing":
        if reviewers["registered_reviewers"]:
            raise ReviewResponseError("missing reviewer policy contains registrations")
    elif not reviewers["registered_reviewers"]:
        raise ReviewResponseError("registered reviewer policy is empty")

    signature = exact_keys(
        authority["signature_policy"],
        {
            "allowed_key_types",
            "canonical_root",
            "format",
            "namespace",
            "root_member",
            "signature_member",
        },
        "signature policy",
    )
    require_exact(signature["format"], "openssh-sshsig-v1", "signature format")
    require_exact(signature["namespace"], SIGNATURE_NAMESPACE, "signature namespace")
    require_exact(signature["allowed_key_types"], ["ssh-ed25519"], "signature key types")
    require_exact(signature["canonical_root"], "canonical-ascii-json-newline-v1", "canonical root")
    require_exact(signature["root_member"], "response-root.json", "root member")
    require_exact(signature["signature_member"], "response-root.sig", "signature member")

    validate_decision_policy(authority["decision_policy"])
    validate_package_policy(authority["response_package_policy"])
    validate_archive_policy(authority["archive_expansion_policy"], provisional)
    validate_durability_policy(authority["durability_policy"])
    blockers = authority["remaining_blockers"]
    if type(blockers) is not list or not blockers:
        raise ReviewResponseError("remaining blockers must be a nonempty list")
    for blocker in blockers:
        require_string(blocker, "remaining blocker", 1024)
    return authority


def validate_decision_policy(policy):
    exact_keys(
        policy,
        {
            "authorship_statuses",
            "content_finding_auto_resolves_paths",
            "license_statuses",
            "machine_classification_auto_accepted",
            "provenance_statuses",
            "redistribution_statuses",
            "resolution_statuses",
            "unit_evidence_sha256_algorithm",
        },
        "decision policy",
    )
    require_exact(policy["license_statuses"], ["affirmed", "unresolved"], "license statuses")
    require_exact(policy["provenance_statuses"], ["affirmed", "unresolved"], "provenance statuses")
    require_exact(policy["authorship_statuses"], ["affirmed", "unresolved"], "authorship statuses")
    require_exact(
        policy["redistribution_statuses"],
        ["approved", "not-approved", "unresolved"],
        "redistribution statuses",
    )
    require_exact(policy["resolution_statuses"], ["resolved", "unresolved"], "resolution statuses")
    require_exact(policy["content_finding_auto_resolves_paths"], False, "content finding policy")
    require_exact(policy["machine_classification_auto_accepted"], False, "machine classification policy")
    require_exact(
        policy["unit_evidence_sha256_algorithm"],
        "sha256-canonical-complete-campaign-review-unit-json-v1",
        "unit evidence digest policy",
    )


def validate_package_policy(policy):
    exact_keys(
        policy,
        {
            "aggregate_preflight_before_retention",
            "checksum_manifest",
            "descriptor_rooted_reads",
            "hardlinks_allowed",
            "maximum_package_bytes",
            "member_mode",
            "namespace_replay",
            "support_directory",
            "top_level_members",
        },
        "response package policy",
    )
    require_exact(policy["aggregate_preflight_before_retention"], True, "aggregate preflight")
    require_exact(policy["checksum_manifest"], "SHA256SUMS", "checksum manifest")
    require_exact(policy["descriptor_rooted_reads"], True, "descriptor reads")
    require_exact(policy["hardlinks_allowed"], False, "hardlink policy")
    require_exact(policy["maximum_package_bytes"], MAX_RESPONSE_BYTES, "package cap")
    require_exact(policy["member_mode"], "0444", "member mode")
    require_exact(
        policy["namespace_replay"],
        "held-ancestor-root-support-and-named-member-identities-before-during-and-after-retention",
        "namespace replay policy",
    )
    require_exact(policy["support_directory"], "support", "support directory")
    require_exact(policy["top_level_members"], sorted(TOP_LEVEL_MEMBERS), "top-level members")


ARCHIVE_BINDING_KEYS = {
    "attachment_alone_counts_as_reviewed",
    "attachment_alone_credit_eligible",
    "child_inventory",
    "child_review_complete",
    "container",
    "container_review_state",
    "required_next_action",
    "role",
}


def validate_archive_binding(binding):
    exact_keys(binding, ARCHIVE_BINDING_KEYS, "archive binding")
    require_exact(
        binding["attachment_alone_counts_as_reviewed"],
        False,
        "archive attachment review policy",
    )
    require_exact(
        binding["attachment_alone_credit_eligible"],
        False,
        "archive attachment credit policy",
    )
    require_exact(binding["child_review_complete"], False, "archive child review state")
    require_exact(
        binding["container_review_state"],
        "independent-review-required",
        "archive container review state",
    )
    container = exact_keys(
        binding["container"],
        {"group_id", "path", "sha256", "size", "unit_id"},
        "archive container",
    )
    if not STABLE_ID_PATTERN.fullmatch(
        require_string(container["group_id"], "archive group ID", 128)
    ) or not container["group_id"].startswith("exact-content:"):
        raise ReviewResponseError("archive group ID is malformed")
    if not STABLE_ID_PATTERN.fullmatch(
        require_string(container["unit_id"], "archive source unit ID", 128)
    ) or not container["unit_id"].startswith("review-unit:"):
        raise ReviewResponseError("archive source unit ID is malformed")
    safe_relative(container["path"], "archive container path")
    require_sha256(container["sha256"], "archive container digest")
    require_nonnegative_int(container["size"], "archive container size")
    role = binding["role"]
    if role not in (
        "existing-inventory-closure",
        "future-v2-child-inventory-required",
    ):
        raise ReviewResponseError("archive expansion role is invalid")
    child = binding["child_inventory"]
    if role == "existing-inventory-closure":
        require_exact(
            binding["required_next_action"],
            "review-existing-frozen-linux-child-units-and-container-context",
            "existing archive next action",
        )
        exact_keys(
            child,
            {"capture_namespace_closure", "derived_review_closure"},
            "existing archive child inventory",
        )
        capture = exact_keys(
            child["capture_namespace_closure"],
            {
                "complete",
                "item_count",
                "path_set_algorithm",
                "path_set_sha256",
                "source_closure_path_set_sha256",
                "source_manifest_algorithm",
                "source_manifest_sha256",
            },
            "archive capture namespace closure",
        )
        require_exact(capture["complete"], True, "archive capture completeness")
        require_nonnegative_int(capture["item_count"], "archive capture item count")
        require_exact(capture["path_set_algorithm"], "utf8-path-newline", "archive capture path algorithm")
        require_sha256(capture["path_set_sha256"], "archive capture path set")
        require_exact(
            capture["source_closure_path_set_sha256"],
            capture["path_set_sha256"],
            "archive source-closure path set",
        )
        require_exact(
            capture["source_manifest_algorithm"],
            "canonical-json-source-rows",
            "archive source manifest algorithm",
        )
        require_sha256(capture["source_manifest_sha256"], "archive source manifest")
        derived = exact_keys(
            child["derived_review_closure"],
            {
                "content_group_count",
                "content_group_id_stream_algorithm",
                "content_group_id_stream_bytes",
                "content_group_id_stream_sha256",
                "decision_counts",
                "namespace",
                "path_set_algorithm",
                "path_set_sha256",
                "referenced_content_bytes",
                "regular_unit_count",
                "review_state",
                "review_unit_count",
                "review_unit_id_stream_algorithm",
                "review_unit_id_stream_bytes",
                "review_unit_id_stream_sha256",
                "source_identity",
                "symlink_unit_count",
            },
            "archive derived review closure",
        )
        for key in (
            "content_group_count",
            "content_group_id_stream_bytes",
            "referenced_content_bytes",
            "regular_unit_count",
            "review_unit_count",
            "review_unit_id_stream_bytes",
            "symlink_unit_count",
        ):
            require_nonnegative_int(derived[key], "archive derived " + key)
        require_exact(derived["namespace"], "linux", "archive derived namespace")
        require_exact(
            derived["review_state"],
            "independent-review-required",
            "archive derived review state",
        )
        require_exact(
            derived["content_group_id_stream_algorithm"],
            "canonical-json-group-id-rows",
            "archive group stream algorithm",
        )
        require_exact(
            derived["review_unit_id_stream_algorithm"],
            "canonical-json-unit-id-rows",
            "archive unit stream algorithm",
        )
        require_exact(
            derived["path_set_algorithm"],
            "canonical-json-path-rows",
            "archive derived path algorithm",
        )
        for key in (
            "content_group_id_stream_sha256",
            "path_set_sha256",
            "review_unit_id_stream_sha256",
        ):
            require_sha256(derived[key], "archive derived " + key)
        counts = exact_keys(
            derived["decision_counts"],
            {"machine-classified-exact-spdx", "unresolved"},
            "archive derived decision counts",
        )
        for key in counts:
            require_nonnegative_int(counts[key], "archive decision count " + key)
        if sum(counts.values()) != derived["review_unit_count"]:
            raise ReviewResponseError("archive decision counts do not close")
        if derived["regular_unit_count"] + derived["symlink_unit_count"] != derived["review_unit_count"]:
            raise ReviewResponseError("archive entry-type counts do not close")
        require_exact(capture["item_count"], derived["review_unit_count"], "archive capture/review count")
        require_exact(
            derived["source_identity"],
            {"archive_sha256": container["sha256"]},
            "archive derived source identity",
        )
    else:
        require_exact(
            binding["required_next_action"],
            "expand-and-capture-future-v2-child-inventory-before-any-closure-response",
            "future archive next action",
        )
        require_exact(child, None, "future archive child inventory")
    return binding


def validate_archive_policy(policy, provisional):
    exact_keys(
        policy,
        {
            "archive_binding_digest_algorithm",
            "archive_member_stream",
            "archive_response_stream",
            "current_campaign_can_close_successor_archives",
            "raw_container_counts_as_reviewed",
            "streaming_expansion_required",
        },
        "archive expansion policy",
    )
    require_exact(
        policy["archive_binding_digest_algorithm"],
        "sha256-canonical-campaign-archive-binding-json-v1",
        "archive binding digest algorithm",
    )
    require_exact(policy["archive_response_stream"], "archive-expansions.jsonl", "archive response stream")
    require_exact(policy["archive_member_stream"], "archive-members.jsonl", "archive member stream")
    require_exact(policy["raw_container_counts_as_reviewed"], False, "raw container review policy")
    require_exact(policy["streaming_expansion_required"], True, "archive streaming policy")
    require_exact(
        policy["current_campaign_can_close_successor_archives"],
        False,
        "successor archive closure policy",
    )


def validate_durability_policy(policy):
    exact_keys(
        policy,
        {
            "actions_artifact_is_durable",
            "credit_before_durable_registration",
            "durable_authority_registration_status",
            "immutable_object_version_required",
            "outer_archive_digest_required",
        },
        "durability policy",
    )
    require_exact(policy["actions_artifact_is_durable"], False, "Actions durability")
    require_exact(policy["credit_before_durable_registration"], False, "pre-durability credit")
    require_exact(policy["durable_authority_registration_status"], "required-missing", "durable registration")
    require_exact(policy["immutable_object_version_required"], True, "immutable object version")
    require_exact(policy["outer_archive_digest_required"], True, "outer archive digest")


def load_authority(repo=REPO_ROOT, explicit=None):
    path = Path(explicit) if explicit is not None else Path(repo) / AUTHORITY_PATH
    data = read_regular_file_once(path, "review-response authority", MAX_AUTHORITY_BYTES)
    if not isinstance(AUTHORITY_SHA256, str) or not HEX_SHA256.fullmatch(AUTHORITY_SHA256):
        raise ReviewResponseError("review-response authority digest has not been frozen")
    if hashlib.sha256(data).hexdigest() != AUTHORITY_SHA256:
        raise ReviewResponseError("review-response authority digest differs")
    return validate_authority(
        read_json_bytes(data, "review-response authority", canonical=True)
    )


def parse_jsonl(data, label, maximum_records):
    if type(data) is not bytes or len(data) > MAX_STREAM_BYTES:
        raise ReviewResponseError("{0} exceeds its stream cap".format(label))
    if data and not data.endswith(b"\n"):
        raise ReviewResponseError("{0} lacks its final newline".format(label))
    records = []
    for number, line in enumerate(data.splitlines(keepends=True), 1):
        if len(line) > MAX_LINE_BYTES:
            raise ReviewResponseError("{0} line exceeds its cap".format(label))
        if line in (b"", b"\n"):
            raise ReviewResponseError("{0} contains an empty line".format(label))
        records.append(read_json_bytes(line, "{0} line {1}".format(label, number), canonical=True))
        if len(records) > maximum_records:
            raise ReviewResponseError("{0} record count exceeds its cap".format(label))
    return records


def stream_descriptor(path, data, records):
    return {
        "count": len(records),
        "path": path,
        "sha256": hashlib.sha256(data).hexdigest(),
        "size": len(data),
    }


def canonical_stream(records):
    return b"".join(canonical_json(record, newline=True) for record in records)


def stable_id(prefix, payload):
    return prefix + ":" + hashlib.sha256(canonical_json(payload)).hexdigest()


def unit_payload_stream(decisions):
    payloads = []
    for decision in decisions:
        payload = dict(decision)
        if "signed_response_root" not in payload:
            raise ReviewResponseError("unit decision lacks signed response root")
        del payload["signed_response_root"]
        payloads.append(payload)
    return canonical_stream(payloads)


def root_binding(root):
    streams = root["streams"]
    unit = streams["unit_decisions"]
    return {
        "attestations": root["attestations"],
        "campaign_authority_sha256": root["campaign_authority_sha256"],
        "campaign_id": root["campaign_id"],
        "packet_id": root["packet_id"],
        "response_contract_id": root["response_contract_id"],
        "review_completed_at": root["review_completed_at"],
        "reviewer_authority_id": root["reviewer_authority_id"],
        "reviewer_identity": root["reviewer_identity"],
        "reviewer_key_fingerprint": root["reviewer_key_fingerprint"],
        "schema_version": root["schema_version"],
        "streams": {
            "archive_expansions": streams["archive_expansions"],
            "archive_members": streams["archive_members"],
            "content_findings": streams["content_findings"],
            "support_index": streams["support_index"],
            "unit_decision_payload": {
                "count": unit["count"],
                "path": unit["path"],
                "sha256": unit["payload_sha256"],
                "size": unit["payload_size"],
            },
        },
    }


def signed_response_root(root):
    return stable_id("rk001-response-root", root_binding(root))


STREAM_DESCRIPTOR_KEYS = {"count", "path", "sha256", "size"}
UNIT_STREAM_DESCRIPTOR_KEYS = STREAM_DESCRIPTOR_KEYS | {"payload_sha256", "payload_size"}
ROOT_KEYS = {
    "attestations",
    "campaign_authority_sha256",
    "campaign_id",
    "packet_id",
    "response_contract_id",
    "review_completed_at",
    "reviewer_authority_id",
    "reviewer_identity",
    "reviewer_key_fingerprint",
    "schema_version",
    "signed_response_root",
    "streams",
}


def validate_stream_descriptor(value, label, path, unit=False):
    exact_keys(value, UNIT_STREAM_DESCRIPTOR_KEYS if unit else STREAM_DESCRIPTOR_KEYS, label)
    require_exact(value["path"], path, label + " path")
    require_nonnegative_int(value["count"], label + " count")
    require_nonnegative_int(value["size"], label + " size")
    require_sha256(value["sha256"], label + " digest")
    if unit:
        require_nonnegative_int(value["payload_size"], label + " payload size")
        require_sha256(value["payload_sha256"], label + " payload digest")


def validate_root(root, authority):
    exact_keys(root, ROOT_KEYS, "response root")
    require_exact(root["schema_version"], SCHEMA_VERSION, "response root schema")
    require_exact(root["response_contract_id"], CONTRACT_ID, "response root contract")
    require_exact(root["campaign_id"], CAMPAIGN_ID, "response root campaign")
    require_sha256(root["campaign_authority_sha256"], "response root campaign authority")
    packet_id = require_string(root["packet_id"], "response root packet ID", 4)
    if not PACKET_ID_PATTERN.fullmatch(packet_id) or not ("0001" <= packet_id <= "0219"):
        raise ReviewResponseError("response root packet ID is outside the campaign")
    for key in ("reviewer_authority_id", "reviewer_identity"):
        require_string(root[key], "response root " + key, 128)
    require_string(root["reviewer_key_fingerprint"], "response root reviewer fingerprint", 128)
    require_utc_timestamp(root["review_completed_at"], "review completed time")
    streams = exact_keys(
        root["streams"],
        {
            "archive_expansions",
            "archive_members",
            "content_findings",
            "support_index",
            "unit_decisions",
        },
        "response root streams",
    )
    for name, path in (
        ("archive_expansions", "archive-expansions.jsonl"),
        ("archive_members", "archive-members.jsonl"),
        ("content_findings", "content-findings.jsonl"),
        ("support_index", "support-index.jsonl"),
        ("unit_decisions", "unit-decisions.jsonl"),
    ):
        validate_stream_descriptor(streams[name], "response root " + name, path, unit=name == "unit_decisions")
    attestations = exact_keys(
        root["attestations"],
        {
            "all_units_individually_reviewed",
            "archive_expansion_complete",
            "content_findings_auto_resolve_paths",
            "credit_eligible",
            "durable_archive",
            "independent_from_capture",
            "machine_classification_auto_accepted",
            "tracker_credit",
        },
        "response attestations",
    )
    for key, value in attestations.items():
        require_bool(value, "response attestation " + key)
    for key, value in EXPECTED_ATTESTATION_FALSE.items():
        require_exact(attestations[key], value, "response attestation " + key)
    require_exact(
        attestations["independent_from_capture"],
        True,
        "response independent-from-capture attestation",
    )
    require_exact(
        root["signed_response_root"],
        signed_response_root(root),
        "signed response root",
    )
    return root


CONTENT_FINDING_KEYS = {
    "conclusion",
    "content_finding_id",
    "content_group_id",
    "content_sha256",
    "content_size",
    "reviewer_identity",
    "spdx_expression_or_unresolved",
    "support_reference_ids",
}
UNIT_DECISION_KEYS = {
    "authorship_status",
    "content_finding_id",
    "context_group_id",
    "license_status",
    "namespace",
    "origin",
    "path",
    "provenance_status",
    "redistribution_status",
    "resolved_or_unresolved",
    "reviewer_identity",
    "signed_response_root",
    "source_identity",
    "support_reference_ids",
    "unit_evidence_sha256",
    "unit_id",
}
SUPPORT_KEYS = {
    "description",
    "kind",
    "member",
    "reference_id",
    "sha256",
    "size",
}
ARCHIVE_EXPANSION_KEYS = {
    "archive_binding_sha256",
    "archive_group_id",
    "container_path",
    "container_sha256",
    "container_size",
    "expansion_role",
    "expansion_status",
    "member_count",
    "member_stream_sha256",
    "member_stream_size",
    "reviewer_identity",
    "support_reference_ids",
}
ARCHIVE_MEMBER_KEYS = {
    "archive_group_id",
    "entry_type",
    "link_target",
    "path",
    "sha256",
    "size",
    "source_identity",
}


def validate_support(records, files):
    index = {}
    previous = None
    referenced_members = set()
    for record in records:
        exact_keys(record, SUPPORT_KEYS, "support index row")
        reference_id = require_string(record["reference_id"], "support reference ID", 128)
        if not STABLE_ID_PATTERN.fullmatch(reference_id) or not reference_id.startswith("support:"):
            raise ReviewResponseError("support reference ID is malformed")
        if previous is not None and reference_id <= previous:
            raise ReviewResponseError("support index is duplicated or unsorted")
        previous = reference_id
        if record["kind"] not in (
            "archive-expansion",
            "authorship-record",
            "license-text",
            "other",
            "provenance-record",
            "redistribution-analysis",
        ):
            raise ReviewResponseError("support kind is invalid")
        digest = require_sha256(record["sha256"], "support digest")
        require_nonnegative_int(record["size"], "support size")
        member = safe_relative(record["member"], "support member")
        require_exact(member, "support/" + digest, "support member name")
        require_string(record["description"], "support description", 4096)
        payload = dict(record)
        del payload["reference_id"]
        require_exact(reference_id, stable_id("support", payload), "support reference ID")
        if member in referenced_members:
            raise ReviewResponseError("support member is referenced more than once")
        if member not in files:
            raise ReviewResponseError("support member is absent")
        data = files[member]
        if len(data) != record["size"] or hashlib.sha256(data).hexdigest() != digest:
            raise ReviewResponseError("support member bytes differ")
        referenced_members.add(member)
        index[reference_id] = record
    actual_members = {name for name in files if name.startswith("support/")}
    if actual_members != referenced_members:
        raise ReviewResponseError("support member closure differs")
    return index


def _require_support(ids, support, label, affirmative=False):
    require_sorted_unique_strings(ids, label)
    if affirmative and not ids:
        raise ReviewResponseError("{0} is empty for an affirmative decision".format(label))
    for reference_id in ids:
        if reference_id not in support:
            raise ReviewResponseError("{0} references unknown support".format(label))


def validate_findings(records, groups, reviewer_identity, support):
    findings = {}
    previous = None
    expected = {group["group_id"]: group for group in groups}
    for record in records:
        exact_keys(record, CONTENT_FINDING_KEYS, "content finding")
        finding_id = require_string(record["content_finding_id"], "content finding ID", 128)
        if not STABLE_ID_PATTERN.fullmatch(finding_id) or not finding_id.startswith("content-finding:"):
            raise ReviewResponseError("content finding ID is malformed")
        if previous is not None and finding_id <= previous:
            raise ReviewResponseError("content findings are duplicated or unsorted")
        previous = finding_id
        group_id = require_string(record["content_group_id"], "finding group ID", 128)
        if group_id not in expected:
            raise ReviewResponseError("content finding references an unknown group")
        group = expected[group_id]
        require_exact(record["content_sha256"], group["identity"]["sha256"], "finding content digest")
        require_exact(record["content_size"], group["identity"]["size"], "finding content size")
        require_exact(record["reviewer_identity"], reviewer_identity, "finding reviewer")
        if record["conclusion"] not in ("resolved", "unresolved"):
            raise ReviewResponseError("content finding conclusion is invalid")
        expression = record["spdx_expression_or_unresolved"]
        if record["conclusion"] == "resolved":
            require_string(expression, "content finding SPDX expression", 16384)
            if expression == "unresolved":
                raise ReviewResponseError("resolved content finding is unresolved")
        else:
            require_exact(expression, "unresolved", "unresolved content finding")
        _require_support(
            record["support_reference_ids"],
            support,
            "content finding support",
            affirmative=record["conclusion"] == "resolved",
        )
        payload = dict(record)
        del payload["content_finding_id"]
        require_exact(finding_id, stable_id("content-finding", payload), "content finding ID")
        if group_id in findings:
            raise ReviewResponseError("content group has more than one finding")
        findings[group_id] = record
    if set(findings) != set(expected):
        raise ReviewResponseError("content finding/group closure differs")
    return findings


def validate_unit_decisions(records, units, findings, root, support):
    if len(records) != len(units):
        raise ReviewResponseError("unit decision count differs from the packet")
    unresolved = 0
    for index, values in enumerate(zip(records, units)):
        record, unit = values
        exact_keys(record, UNIT_DECISION_KEYS, "unit decision")
        evidence = unit["evidence"]
        for key, expected in (
            ("unit_id", unit["unit_id"]),
            ("path", evidence["path"]),
            ("namespace", evidence["namespace"]),
            ("origin", evidence["origin"]),
            ("source_identity", evidence["source_identity"]),
            ("context_group_id", unit["context_group_id"]),
        ):
            require_exact(record[key], expected, "unit decision {0} row {1}".format(key, index))
        require_exact(
            record["unit_evidence_sha256"],
            hashlib.sha256(canonical_json(unit)).hexdigest(),
            "unit evidence digest",
        )
        require_exact(record["reviewer_identity"], root["reviewer_identity"], "unit reviewer")
        require_exact(record["signed_response_root"], root["signed_response_root"], "unit signed root")
        group_id = unit["exact_content_group_id"]
        finding_id = record["content_finding_id"]
        finding = None
        if group_id is None:
            require_exact(finding_id, None, "symlink content finding")
        else:
            finding = findings.get(group_id)
            if finding is None:
                raise ReviewResponseError("unit content group lacks a finding")
            require_exact(finding_id, finding["content_finding_id"], "unit content finding")
        statuses = {
            "license_status": ("affirmed", "unresolved"),
            "provenance_status": ("affirmed", "unresolved"),
            "authorship_status": ("affirmed", "unresolved"),
            "redistribution_status": ("approved", "not-approved", "unresolved"),
            "resolved_or_unresolved": ("resolved", "unresolved"),
        }
        for key, allowed in statuses.items():
            if record[key] not in allowed:
                raise ReviewResponseError("unit {0} is invalid".format(key))
        affirmative = (
            record["license_status"] == "affirmed"
            and record["provenance_status"] == "affirmed"
            and record["authorship_status"] == "affirmed"
            and record["redistribution_status"] == "approved"
            and record["resolved_or_unresolved"] == "resolved"
            and (finding is None or finding["conclusion"] == "resolved")
        )
        if record["resolved_or_unresolved"] == "resolved" and not affirmative:
            raise ReviewResponseError("unit resolution contradicts its review statuses")
        if record["resolved_or_unresolved"] == "unresolved":
            unresolved += 1
        _require_support(
            record["support_reference_ids"],
            support,
            "unit support",
            affirmative=record["resolved_or_unresolved"] == "resolved",
        )
    require_exact(
        root["attestations"]["all_units_individually_reviewed"],
        len(records) == len(units),
        "all-units-reviewed attestation",
    )
    return unresolved


def validate_archive_members(records, bindings):
    grouped = {group_id: [] for group_id in bindings}
    previous = None
    for record in records:
        exact_keys(record, ARCHIVE_MEMBER_KEYS, "archive member")
        group_id = require_string(record["archive_group_id"], "archive member group", 128)
        if group_id not in bindings:
            raise ReviewResponseError("archive member references an unknown binding")
        binding = bindings[group_id]
        if binding["role"] == "existing-inventory-closure":
            raise ReviewResponseError("existing inventory archive duplicated member rows")
        path = safe_relative(record["path"], "archive member path")
        order = (group_id, path)
        if previous is not None and order <= previous:
            raise ReviewResponseError("archive members are duplicated or unsorted")
        previous = order
        if record["entry_type"] not in ("regular", "symlink", "hardlink"):
            raise ReviewResponseError("archive member type is unsupported")
        require_nonnegative_int(record["size"], "archive member size")
        require_exact(
            record["source_identity"],
            {"archive_sha256": binding["container"]["sha256"]},
            "archive member source identity",
        )
        if record["entry_type"] == "regular":
            require_sha256(record["sha256"], "archive member digest")
            require_exact(record["link_target"], None, "regular archive link target")
        else:
            require_sha256(record["sha256"], "archive link digest")
            target = require_string(record["link_target"], "archive link target", 4096)
            if PurePosixPath(target).is_absolute() or "\x00" in target:
                raise ReviewResponseError("archive link target is unsafe")
        grouped[group_id].append(record)
    return grouped


def validate_archive_expansions(
    records, member_records, authority, reviewer_identity, support, packet_id
):
    bindings = {
        binding["container"]["group_id"]: binding
        for binding in authority["campaign_closure"]["archive_bindings"]
    }
    if packet_id != "0218":
        if records or member_records:
            raise ReviewResponseError("archive expansion records occur outside packet 0218")
        return False
    grouped = validate_archive_members(member_records, bindings)
    if len(records) != len(bindings):
        raise ReviewResponseError("archive expansion count differs from the campaign")
    previous = None
    successor_present = False
    for record in records:
        exact_keys(record, ARCHIVE_EXPANSION_KEYS, "archive expansion")
        group_id = require_string(record["archive_group_id"], "archive expansion group", 128)
        if previous is not None and group_id <= previous:
            raise ReviewResponseError("archive expansions are duplicated or unsorted")
        previous = group_id
        if group_id not in bindings:
            raise ReviewResponseError("archive expansion references an unknown binding")
        binding = bindings[group_id]
        container = binding["container"]
        for key, expected in (
            ("container_path", container["path"]),
            ("container_sha256", container["sha256"]),
            ("container_size", container["size"]),
            ("expansion_role", binding["role"]),
        ):
            require_exact(record[key], expected, "archive expansion " + key)
        require_exact(
            record["archive_binding_sha256"],
            hashlib.sha256(canonical_json(binding)).hexdigest(),
            "archive campaign binding digest",
        )
        require_exact(record["reviewer_identity"], reviewer_identity, "archive expansion reviewer")
        members = grouped[group_id]
        stream = canonical_stream(members)
        require_exact(record["member_count"], len(members), "archive member count")
        require_exact(record["member_stream_size"], len(stream), "archive member stream size")
        require_exact(
            record["member_stream_sha256"],
            hashlib.sha256(stream).hexdigest(),
            "archive member stream digest",
        )
        _require_support(record["support_reference_ids"], support, "archive expansion support", affirmative=True)
        if binding["role"] == "existing-inventory-closure":
            require_exact(record["expansion_status"], "matched-existing-inventory", "existing expansion status")
            if members:
                raise ReviewResponseError("existing inventory archive duplicated member rows")
        else:
            successor_present = True
            require_exact(record["expansion_status"], "future-v2-child-inventory-required", "successor expansion status")
    return not successor_present


def _checksum_manifest(files):
    return b"".join(
        (hashlib.sha256(files[name]).hexdigest() + "  " + name + "\n").encode("ascii")
        for name in sorted(files)
        if name != "SHA256SUMS"
    )


def find_reviewer(authority, root):
    matches = [
        reviewer
        for reviewer in authority["reviewer_authority_policy"]["registered_reviewers"]
        if reviewer["authority_id"] == root["reviewer_authority_id"]
        and reviewer["reviewer_identity"] == root["reviewer_identity"]
    ]
    if len(matches) != 1:
        raise ReviewResponseError("response reviewer is not uniquely registered")
    reviewer = matches[0]
    require_exact(root["reviewer_key_fingerprint"], reviewer["ssh_fingerprint"], "root reviewer fingerprint")
    if not (reviewer["packet_min"] <= root["packet_id"] <= reviewer["packet_max"]):
        raise ReviewResponseError("reviewer is not registered for this packet")
    if not (reviewer["valid_from"] <= root["review_completed_at"] <= reviewer["valid_through"]):
        raise ReviewResponseError("review completion falls outside reviewer validity")
    return reviewer


def _verify_immutable_pass_fd(descriptor, identity, expected, label):
    try:
        before = os.fstat(descriptor)
        if _stat_identity(before) != identity:
            raise ReviewResponseError("{0} immutable descriptor identity changed".format(label))
        passes = []
        for unused in range(2):
            os.lseek(descriptor, 0, os.SEEK_SET)
            data = _read_descriptor(descriptor, label, len(expected))
            if data != expected:
                raise ReviewResponseError("{0} immutable descriptor bytes changed".format(label))
            passes.append(data)
            if _stat_identity(os.fstat(descriptor)) != identity:
                raise ReviewResponseError("{0} immutable descriptor changed while read".format(label))
        if passes[0] != passes[1]:
            raise ReviewResponseError("{0} immutable descriptor replay differs".format(label))
    except ReviewResponseError:
        raise
    except OSError as error:
        raise ReviewResponseError("cannot replay {0}: {1}".format(label, error))


def _immutable_pass_fd(data, label):
    staging = None
    descriptor = None
    try:
        staging = tempfile.TemporaryFile(mode="w+b")
        written = staging.write(data)
        if written != len(data):
            raise ReviewResponseError("{0} immutable copy was short".format(label))
        staging.flush()
        os.fsync(staging.fileno())
        os.fchmod(staging.fileno(), 0o400)
        descriptor = os.open(
            "/proc/self/fd/{0}".format(staging.fileno()),
            os.O_RDONLY | getattr(os, "O_CLOEXEC", 0),
        )
        info = os.fstat(descriptor)
        if (
            not stat.S_ISREG(info.st_mode)
            or stat.S_IMODE(info.st_mode) != 0o400
            or info.st_size != len(data)
        ):
            raise ReviewResponseError("{0} immutable copy identity differs".format(label))
        identity = _stat_identity(info)
        staging.close()
        staging = None
        _verify_immutable_pass_fd(descriptor, identity, data, label)
        return descriptor, identity
    except ReviewResponseError:
        raise
    except OSError as error:
        raise ReviewResponseError("cannot retain {0}: {1}".format(label, error))
    finally:
        if staging is not None:
            staging.close()
        if descriptor is not None and sys.exc_info()[0] is not None:
            try:
                os.close(descriptor)
            except OSError:
                pass


def verify_sshsig(root_bytes, signature_bytes, reviewer, namespace=SIGNATURE_NAMESPACE):
    if not signature_bytes or len(signature_bytes) > MAX_SIGNATURE_BYTES:
        raise ReviewResponseError("response signature is empty or oversized")
    try:
        signature_bytes.decode("ascii")
    except UnicodeError as error:
        raise ReviewResponseError("response signature is not ASCII: {0}".format(error))
    if not signature_bytes.startswith(b"-----BEGIN SSH SIGNATURE-----\n"):
        raise ReviewResponseError("response signature is not an armored SSHSIG")
    allowed_bytes = (
        reviewer["reviewer_identity"] + " " + reviewer["ssh_public_key"] + "\n"
    ).encode("ascii")
    allowed_fd = None
    signature_fd = None
    try:
        allowed_fd, allowed_identity = _immutable_pass_fd(
            allowed_bytes, "allowed-signers copy"
        )
        signature_fd, signature_identity = _immutable_pass_fd(
            signature_bytes, "response-signature copy"
        )
        command = [
            "/usr/bin/ssh-keygen",
            "-Y",
            "verify",
            "-f",
            "/proc/self/fd/{0}".format(allowed_fd),
            "-I",
            reviewer["reviewer_identity"],
            "-n",
            namespace,
            "-s",
            "/proc/self/fd/{0}".format(signature_fd),
        ]
        environment = {
            "HOME": "/nonexistent",
            "LANG": "C",
            "LC_ALL": "C",
            "PATH": "/usr/bin:/bin",
        }
        try:
            process = subprocess.Popen(
                command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=environment,
                pass_fds=(allowed_fd, signature_fd),
            )
        except OSError as error:
            raise ReviewResponseError("cannot execute SSHSIG verifier: {0}".format(error))
        try:
            stdout, stderr = process.communicate(input=root_bytes, timeout=30)
        except subprocess.TimeoutExpired:
            process.kill()
            process.communicate()
            _verify_immutable_pass_fd(
                allowed_fd, allowed_identity, allowed_bytes, "allowed-signers copy"
            )
            _verify_immutable_pass_fd(
                signature_fd, signature_identity, signature_bytes, "response-signature copy"
            )
            raise ReviewResponseError("SSHSIG verification timed out")
        except OSError as error:
            _verify_immutable_pass_fd(
                allowed_fd, allowed_identity, allowed_bytes, "allowed-signers copy"
            )
            _verify_immutable_pass_fd(
                signature_fd, signature_identity, signature_bytes, "response-signature copy"
            )
            raise ReviewResponseError("cannot communicate with SSHSIG verifier: {0}".format(error))
        _verify_immutable_pass_fd(
            allowed_fd, allowed_identity, allowed_bytes, "allowed-signers copy"
        )
        _verify_immutable_pass_fd(
            signature_fd, signature_identity, signature_bytes, "response-signature copy"
        )
        if len(stdout) + len(stderr) > 128 * 1024:
            raise ReviewResponseError("SSHSIG verification output exceeds its cap")
        if process.returncode != 0:
            raise ReviewResponseError("response SSHSIG verification failed")
    finally:
        for descriptor in (signature_fd, allowed_fd):
            if descriptor is not None:
                try:
                    os.close(descriptor)
                except OSError:
                    pass
    return True


def _open_dir(path, label):
    raw = str(path)
    raw_parts = raw.split(os.sep)
    comparable = raw_parts[1:] if os.path.isabs(raw) else raw_parts
    if (
        not raw
        or "\x00" in raw
        or "\\" in raw
        or any(part in ("", ".", "..") for part in comparable)
    ):
        raise ReviewResponseError("{0} path is unsafe".format(label))
    requested = Path(os.path.abspath(raw))
    if requested.anchor != os.sep:
        raise ReviewResponseError("{0} path is not absolute".format(label))
    flags = (
        os.O_RDONLY
        | getattr(os, "O_DIRECTORY", 0)
        | getattr(os, "O_NOFOLLOW", 0)
        | getattr(os, "O_CLOEXEC", 0)
    )
    chain = []
    try:
        current = os.open(requested.anchor, flags)
        root_info = os.fstat(current)
        if not stat.S_ISDIR(root_info.st_mode):
            raise ReviewResponseError("{0} root is not a directory".format(label))
        chain.append(
            {
                "descriptor": current,
                "identity": _directory_identity(root_info),
                "name": None,
                "parent_fd": None,
            }
        )
        for component in requested.parts[1:]:
            _safe_component(component, label + " component")
            following = None
            try:
                following = os.open(component, flags, dir_fd=current)
                info = os.fstat(following)
                namespace = os.stat(component, dir_fd=current, follow_symlinks=False)
            except OSError:
                if following is not None:
                    os.close(following)
                raise
            if (
                not stat.S_ISDIR(info.st_mode)
                or _directory_identity(info) != _directory_identity(namespace)
            ):
                os.close(following)
                raise ReviewResponseError("{0} component identity changed".format(label))
            chain.append(
                {
                    "descriptor": following,
                    "identity": _directory_identity(info),
                    "name": component,
                    "parent_fd": current,
                }
            )
            current = following
    except OSError as error:
        for record in reversed(chain):
            try:
                os.close(record["descriptor"])
            except OSError:
                pass
        raise ReviewResponseError("cannot open {0}: {1}".format(label, error))
    except ReviewResponseError:
        for record in reversed(chain):
            try:
                os.close(record["descriptor"])
            except OSError:
                pass
        raise
    return {
        "chain": chain,
        "expected_names": None,
        "fd": current,
        "identity": chain[-1]["identity"],
        "label": label,
        "name": None,
        "parent": None,
    }


def _open_child_dir(parent, name, label):
    name = _safe_component(name, label + " name")
    _replay_dir(parent)
    flags = (
        os.O_RDONLY
        | getattr(os, "O_DIRECTORY", 0)
        | getattr(os, "O_NOFOLLOW", 0)
        | getattr(os, "O_CLOEXEC", 0)
    )
    descriptor = None
    try:
        descriptor = os.open(name, flags, dir_fd=parent["fd"])
        opened = os.fstat(descriptor)
        namespace = os.stat(name, dir_fd=parent["fd"], follow_symlinks=False)
    except OSError as error:
        if descriptor is not None:
            os.close(descriptor)
        raise ReviewResponseError("cannot open {0}: {1}".format(label, error))
    if (
        not stat.S_ISDIR(opened.st_mode)
        or _directory_identity(opened) != _directory_identity(namespace)
    ):
        os.close(descriptor)
        raise ReviewResponseError("{0} identity changed".format(label))
    context = {
        "chain": None,
        "expected_names": None,
        "fd": descriptor,
        "identity": _directory_identity(opened),
        "label": label,
        "name": name,
        "parent": parent,
    }
    try:
        _replay_dir(context)
    except Exception:
        os.close(descriptor)
        raise
    return context


def _list_dir(context, maximum):
    try:
        names = os.listdir(context["fd"])
    except OSError as error:
        raise ReviewResponseError("cannot list {0}: {1}".format(context["label"], error))
    if len(names) > maximum:
        raise ReviewResponseError("{0} entry count exceeds its cap".format(context["label"]))
    for name in names:
        _safe_component(name, context["label"] + " entry")
    if len(names) != len(set(names)):
        raise ReviewResponseError("{0} names are duplicated".format(context["label"]))
    return sorted(names)


def _replay_dir(context):
    if context["parent"] is None:
        for record in context["chain"]:
            try:
                opened = os.fstat(record["descriptor"])
                namespace = (
                    opened
                    if record["parent_fd"] is None
                    else os.stat(
                        record["name"],
                        dir_fd=record["parent_fd"],
                        follow_symlinks=False,
                    )
                )
            except OSError as error:
                raise ReviewResponseError(
                    "{0} ancestor namespace changed: {1}".format(context["label"], error)
                )
            if (
                _directory_identity(opened) != record["identity"]
                or _directory_identity(namespace) != record["identity"]
            ):
                raise ReviewResponseError("{0} ancestor namespace changed".format(context["label"]))
    else:
        _replay_dir(context["parent"])
        try:
            opened = os.fstat(context["fd"])
            namespace = os.stat(
                context["name"],
                dir_fd=context["parent"]["fd"],
                follow_symlinks=False,
            )
        except OSError as error:
            raise ReviewResponseError(
                "{0} namespace changed: {1}".format(context["label"], error)
            )
        if (
            _directory_identity(opened) != context["identity"]
            or _directory_identity(namespace) != context["identity"]
        ):
            raise ReviewResponseError("{0} namespace changed".format(context["label"]))
    if context["expected_names"] is not None:
        current = _list_dir(context, len(context["expected_names"]))
        if current != context["expected_names"]:
            raise ReviewResponseError("{0} entry namespace changed".format(context["label"]))


def _open_member(directory, name, label):
    name = _safe_component(name, label + " name")
    _replay_dir(directory)
    flags = (
        os.O_RDONLY
        | getattr(os, "O_NOFOLLOW", 0)
        | getattr(os, "O_CLOEXEC", 0)
        | getattr(os, "O_NONBLOCK", 0)
    )
    descriptor = None
    try:
        descriptor = os.open(name, flags, dir_fd=directory["fd"])
        info = os.fstat(descriptor)
        namespace = os.stat(name, dir_fd=directory["fd"], follow_symlinks=False)
    except OSError as error:
        if descriptor is not None:
            os.close(descriptor)
        raise ReviewResponseError("cannot open {0}: {1}".format(label, error))
    if (
        not stat.S_ISREG(info.st_mode)
        or _stat_identity(info) != _stat_identity(namespace)
        or stat.S_IMODE(info.st_mode) != 0o444
        or info.st_nlink != 1
    ):
        os.close(descriptor)
        raise ReviewResponseError("{0} is not an exact read-only regular member".format(label))
    member = {
        "directory": directory,
        "fd": descriptor,
        "identity": _stat_identity(info),
        "label": label,
        "name": name,
        "size": info.st_size,
    }
    _verify_member(member)
    return member


def _verify_member(member):
    _replay_dir(member["directory"])
    try:
        opened = os.fstat(member["fd"])
        namespace = os.stat(
            member["name"],
            dir_fd=member["directory"]["fd"],
            follow_symlinks=False,
        )
    except OSError as error:
        raise ReviewResponseError(
            "{0} namespace changed: {1}".format(member["label"], error)
        )
    if (
        _stat_identity(opened) != member["identity"]
        or _stat_identity(namespace) != member["identity"]
    ):
        raise ReviewResponseError("{0} namespace identity changed".format(member["label"]))


def _read_member(member, cap):
    _verify_member(member)
    expected_size = member["size"]
    try:
        os.lseek(member["fd"], 0, os.SEEK_SET)
        chunks = []
        retained = 0
        while retained < expected_size:
            chunk = os.read(member["fd"], min(1024 * 1024, expected_size - retained))
            if not chunk:
                raise ReviewResponseError(
                    "{0} ended before its bound size".format(member["label"])
                )
            retained += len(chunk)
            if retained > cap:
                raise ReviewResponseError("{0} exceeds its cap".format(member["label"]))
            chunks.append(chunk)
            _verify_member(member)
        if os.read(member["fd"], 1):
            raise ReviewResponseError("{0} grew while read".format(member["label"]))
    except ReviewResponseError:
        raise
    except OSError as error:
        raise ReviewResponseError("cannot read {0}: {1}".format(member["label"], error))
    _verify_member(member)
    data = b"".join(chunks)
    if len(data) != expected_size:
        raise ReviewResponseError("{0} retained-byte size differs".format(member["label"]))
    return data


def _close_dir(context):
    if context is None:
        return
    if context["parent"] is None:
        for record in reversed(context["chain"]):
            try:
                os.close(record["descriptor"])
            except OSError:
                pass
    else:
        try:
            os.close(context["fd"])
        except OSError:
            pass


def read_response_package(directory):
    root = _open_dir(Path(directory), "response package root")
    support = None
    members = {}
    try:
        try:
            names = _list_dir(root, len(TOP_LEVEL_MEMBERS) + 1)
        except OSError as error:
            raise ReviewResponseError("cannot list response package: {0}".format(error))
        root["expected_names"] = names
        top = set(names)
        support_present = "support" in top
        top.discard("support")
        if top != TOP_LEVEL_MEMBERS:
            raise ReviewResponseError("response package top-level closure differs")
        for name in sorted(TOP_LEVEL_MEMBERS):
            members[name] = _open_member(root, name, "response member " + name)
        support_names = []
        if support_present:
            support = _open_child_dir(root, "support", "response support directory")
            support_names = _list_dir(support, MAX_SUPPORT_RECORDS)
            support["expected_names"] = support_names
            for name in support_names:
                if not HEX_SHA256.fullmatch(name):
                    raise ReviewResponseError("support filename is malformed")
                relative = "support/" + name
                members[relative] = _open_member(support, name, "response member " + relative)
        total = sum(member["size"] for member in members.values())
        if total > MAX_RESPONSE_BYTES:
            raise ReviewResponseError("response package aggregate exceeds its cap")
        support_total = sum(member["size"] for name, member in members.items() if name.startswith("support/"))
        if support_total > MAX_SUPPORT_BYTES:
            raise ReviewResponseError("response support aggregate exceeds its cap")
        for name, member in members.items():
            cap = MAX_SUPPORT_MEMBER_BYTES if name.startswith("support/") else (
                MAX_ROOT_BYTES if name == "response-root.json" else
                MAX_SIGNATURE_BYTES if name == "response-root.sig" else
                MAX_STREAM_BYTES
            )
            if member["size"] > cap:
                raise ReviewResponseError("response member exceeds its cap: {0}".format(name))
        _replay_dir(root)
        if support is not None:
            _replay_dir(support)
        files = {}
        retained = 0
        for name in sorted(members):
            _replay_dir(root)
            if support is not None:
                _replay_dir(support)
            member = members[name]
            _verify_member(member)
            cap = MAX_SUPPORT_MEMBER_BYTES if name.startswith("support/") else (
                MAX_ROOT_BYTES if name == "response-root.json" else
                MAX_SIGNATURE_BYTES if name == "response-root.sig" else
                MAX_STREAM_BYTES
            )
            data = _read_member(member, cap)
            retained += len(data)
            if retained > MAX_RESPONSE_BYTES:
                raise ReviewResponseError("response retained bytes exceed their cap")
            _verify_member(member)
            _replay_dir(root)
            if support is not None:
                _replay_dir(support)
            files[name] = data
        if retained != total:
            raise ReviewResponseError("response retained-byte closure differs")
        _replay_dir(root)
        if support is not None:
            _replay_dir(support)
        return files
    finally:
        for member in members.values():
            try:
                os.close(member["fd"])
            except OSError:
                pass
        _close_dir(support)
        _close_dir(root)


def parse_response_files(files):
    if set(name for name in files if not name.startswith("support/")) != TOP_LEVEL_MEMBERS:
        raise ReviewResponseError("response file closure differs")
    expected_manifest = _checksum_manifest(files)
    require_exact(files["SHA256SUMS"], expected_manifest, "response checksum manifest")
    root = read_json_bytes(files["response-root.json"], "response root", canonical=True)
    records = {
        "content_findings": parse_jsonl(files["content-findings.jsonl"], "content findings", MAX_FINDING_RECORDS),
        "unit_decisions": parse_jsonl(files["unit-decisions.jsonl"], "unit decisions", MAX_UNIT_RECORDS),
        "archive_expansions": parse_jsonl(files["archive-expansions.jsonl"], "archive expansions", MAX_ARCHIVE_RECORDS),
        "archive_members": parse_jsonl(files["archive-members.jsonl"], "archive members", MAX_ARCHIVE_MEMBER_RECORDS),
        "support_index": parse_jsonl(files["support-index.jsonl"], "support index", MAX_SUPPORT_RECORDS),
    }
    return root, records


def verify_response_data(authority, groups, units, files, campaign_authority_sha256):
    validate_authority(authority)
    root, records = parse_response_files(files)
    validate_root(root, authority)
    require_exact(root["campaign_authority_sha256"], campaign_authority_sha256, "response campaign authority")
    for name, member in (
        ("content_findings", "content-findings.jsonl"),
        ("unit_decisions", "unit-decisions.jsonl"),
        ("archive_expansions", "archive-expansions.jsonl"),
        ("archive_members", "archive-members.jsonl"),
        ("support_index", "support-index.jsonl"),
    ):
        descriptor = stream_descriptor(member, files[member], records[name])
        expected = root["streams"][name]
        for key in STREAM_DESCRIPTOR_KEYS:
            require_exact(expected[key], descriptor[key], "root stream {0}.{1}".format(name, key))
    payload = unit_payload_stream(records["unit_decisions"])
    unit_descriptor = root["streams"]["unit_decisions"]
    require_exact(unit_descriptor["payload_size"], len(payload), "unit payload stream size")
    require_exact(unit_descriptor["payload_sha256"], hashlib.sha256(payload).hexdigest(), "unit payload stream digest")
    require_exact(root["signed_response_root"], signed_response_root(root), "signed response root replay")
    reviewer = find_reviewer(authority, root)
    support = validate_support(records["support_index"], files)
    findings = validate_findings(records["content_findings"], groups, root["reviewer_identity"], support)
    unresolved = validate_unit_decisions(records["unit_decisions"], units, findings, root, support)
    archive_complete = validate_archive_expansions(
        records["archive_expansions"],
        records["archive_members"],
        authority,
        root["reviewer_identity"],
        support,
        root["packet_id"],
    )
    require_exact(root["attestations"]["archive_expansion_complete"], archive_complete, "archive-complete attestation")
    verify_sshsig(files["response-root.json"], files["response-root.sig"], reviewer)
    return {
        "archive_expansion_complete": archive_complete,
        "campaign_complete": False,
        "credit_eligible": False,
        "durable_archive": False,
        "packet_id": root["packet_id"],
        "points_awarded": 0,
        "reviewed_unit_count": len(records["unit_decisions"]),
        "reviewer_identity": root["reviewer_identity"],
        "reviewer_key_fingerprint": root["reviewer_key_fingerprint"],
        "reviewer_registered": True,
        "signed_response_root": root["signed_response_root"],
        "signature_valid": True,
        "tracker_credit": False,
        "unresolved_unit_count": unresolved,
    }


def load_campaign_checker(repo, authority):
    if authority["campaign_closure"]["binding_status"] != "frozen":
        raise ReviewResponseError("campaign response binding is still provisional")
    checker_path, checker_data = _read_bound(
        repo, authority["inputs"]["campaign_checker"], "frozen campaign checker"
    )
    authority_path, authority_data = _read_bound(
        repo,
        authority["inputs"]["campaign_authority"],
        "frozen campaign authority",
        MAX_AUTHORITY_BYTES,
    )
    for key in (
        "campaign_tests",
        "campaign_workflow",
        "inventory_checker",
        "response_workflow",
        "source_lock",
        "source_lock_validator",
    ):
        _read_bound(repo, authority["inputs"][key], "frozen " + key.replace("_", " "))
    module = types.ModuleType("_rk001_frozen_review_campaign")
    module.__file__ = str(checker_path)
    module.__package__ = None
    try:
        code = compile(checker_data, str(checker_path), "exec", dont_inherit=True)
        exec(code, module.__dict__)
    except (Exception, MemoryError) as error:
        raise ReviewResponseError("cannot execute frozen campaign checker: {0}".format(error))
    require_exact(module.AUTHORITY_SHA256, hashlib.sha256(authority_data).hexdigest(), "campaign authority digest")
    require_exact(module.CAMPAIGN_ID, CAMPAIGN_ID, "campaign checker ID")
    try:
        campaign_authority = module.load_authority(Path(repo).resolve(), authority_path)
    except module.ReviewCampaignError as error:
        raise ReviewResponseError("frozen campaign authority rejected: {0}".format(error))
    closure = authority["campaign_closure"]
    require_exact(
        closure["archive_bindings"],
        campaign_authority["archive_expansion_bindings"],
        "response/campaign archive bindings",
    )
    expected = campaign_authority["expected_result"]
    for key in ("packet_count", "review_unit_count", "content_group_count"):
        require_exact(closure[key], expected[key], "response/campaign " + key)
    return module, campaign_authority


def verify_response(authority, repo, artifact, packet_id, packet_directory, response_directory):
    packet_id = require_string(packet_id, "packet ID", 4)
    if not PACKET_ID_PATTERN.fullmatch(packet_id) or not ("0001" <= packet_id <= "0219"):
        raise ReviewResponseError("packet ID is outside the frozen campaign")
    campaign, campaign_authority = load_campaign_checker(repo, authority)
    try:
        derived = campaign.derive_campaign(Path(repo).resolve(), Path(artifact), campaign_authority)
        campaign.verify_package(campaign_authority, derived, packet_id, packet_directory)
        metadata = campaign.packet_metadata_files(campaign_authority, derived, packet_id)
    except campaign.ReviewCampaignError as error:
        raise ReviewResponseError("frozen campaign packet rejected: {0}".format(error))
    groups = parse_jsonl(metadata["content-groups.jsonl"], "campaign content groups", MAX_FINDING_RECORDS)
    units = parse_jsonl(metadata["review-units.jsonl"], "campaign review units", MAX_UNIT_RECORDS)
    files = read_response_package(response_directory)
    result = verify_response_data(
        authority,
        groups,
        units,
        files,
        authority["inputs"]["campaign_authority"]["sha256"],
    )
    require_exact(result["packet_id"], packet_id, "verified response packet")
    return result


def parser(argv=None):
    value = argparse.ArgumentParser(description=__doc__)
    value.add_argument("--repo", default=REPO_ROOT, type=Path)
    value.add_argument("--authority", type=Path)
    modes = value.add_mutually_exclusive_group(required=True)
    modes.add_argument("--check", action="store_true")
    modes.add_argument("--verify-response", action="store_true")
    value.add_argument("--artifact", type=Path)
    value.add_argument("--packet-id")
    value.add_argument("--packet-dir", type=Path)
    value.add_argument("--response-dir", type=Path)
    return value.parse_args(argv)


def main(argv=None):
    args = parser(argv)
    try:
        repo = args.repo.resolve()
        authority = load_authority(repo, args.authority)
        if args.check:
            if authority["campaign_closure"]["binding_status"] != "frozen":
                raise ReviewResponseError("campaign response binding is still provisional")
            load_campaign_checker(repo, authority)
            print(
                "RK-001 response verifier contract verified: reviewers=0 durable=false "
                "gate=TODO points=0 credit=false"
            )
            return 0
        for value, label in (
            (args.artifact, "--artifact"),
            (args.packet_id, "--packet-id"),
            (args.packet_dir, "--packet-dir"),
            (args.response_dir, "--response-dir"),
        ):
            if value is None:
                raise ReviewResponseError("{0} is required".format(label))
        result = verify_response(
            authority,
            repo,
            args.artifact,
            args.packet_id,
            args.packet_dir,
            args.response_dir,
        )
        print(
            "RK-001 per-packet reviewer response verified: packet={0} root={1} "
            "reviewer={2} fingerprint={3} units={4} unresolved={5} signature=true "
            "aggregate=false campaign_complete=false durable=false gate=TODO points=0 "
            "credit=false".format(
                result["packet_id"],
                result["signed_response_root"],
                result["reviewer_identity"],
                result["reviewer_key_fingerprint"],
                result["reviewed_unit_count"],
                result["unresolved_unit_count"],
            )
        )
        return 0
    except ReviewResponseError as error:
        print("RK-001 review-response error: {0}".format(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
