#!/usr/bin/env python3
"""Validate the empty RK-001 reviewer registry and lint external candidates.

The checked-in v1 authority deliberately contains no appointments.  Candidate
lint proves structure, an appointing-authority SSHSIG over independence
evidence, and reviewer proof of key possession.  It is read-only and never
turns a candidate into a production registration or tracker credit.
Authorization lookup accepts only a repository root and reparses the exact
fixed-digest production authority on every call; lint results are never inputs.
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
from pathlib import Path, PurePosixPath


REPO_ROOT = Path(__file__).resolve().parents[1]
AUTHORITY_PATH = Path(
    "host-kernel/rocky/evidence/rk001-license-reviewer-registry-ef58-v1.json"
)
AUTHORITY_SHA256 = "29a3779ba42e869d31b22872fee04d391b10a941598234df968393c96c0146b8"
AUTHORITY_SIZE = 2589
CAMPAIGN_PATH = "host-kernel/rocky/evidence/rk001-license-review-campaign-ef58-v1.json"
CAMPAIGN_SHA256 = "b5581cb9ad5707af65968a6e01ea69a7c46ebbe2542412c1a4cec0611da77852"
CAMPAIGN_SIZE = 168050
CAMPAIGN_ID = "rk-001-license-review-campaign-ef58860e-v1"
SOURCE_COMMIT = "ef58860e4806ee16e2c506e4e93c7b6ad8ad8f4b"
REGISTRY_ID = "rk-001-license-reviewer-registry-ef58860e-v1"
REGISTRY_VERSION = 1
REVOCATION_EPOCH = 1
SCHEMA_VERSION = 1
PACKET_MIN = "0001"
PACKET_MAX = "0219"
PACKET_COUNT = 219
REVIEW_UNIT_COUNT = 115265
CONTENT_GROUP_COUNT = 111004
POSSESSION_NAMESPACE = "mckernel-rk001-license-reviewer-possession-v1"
INDEPENDENCE_NAMESPACE = "mckernel-rk001-license-reviewer-independence-v1"
SSHSIG_FORMAT = "openssh-sshsig-v1"
PAYLOAD_ALGORITHM = "canonical-ascii-json-newline-v1"
APPOINTMENT_ID_ALGORITHM = (
    "appointment:sha256-canonical-appointment-identity-json-v1"
)

MAX_AUTHORITY_BYTES = 64 * 1024
MAX_CAMPAIGN_BYTES = 2 * 1024 * 1024
MAX_CANDIDATE_BYTES = 256 * 1024
MAX_EVIDENCE_BYTES = 256 * 1024
MAX_SIGNATURE_BYTES = 64 * 1024
MAX_JSON_NESTING = 32
MAX_JSON_NUMBER_TOKEN = 128
MAX_CAPTURE_IDENTITIES = 128
SSHSIG_TIMEOUT_SECONDS = 15

HEX_SHA256 = re.compile(r"^[0-9a-f]{64}$")
PACKET_ID_PATTERN = re.compile(r"^[0-9]{4}$")
STABLE_ID_PATTERN = re.compile(r"^[a-z][a-z0-9-]*:[0-9a-f]{64}$")
IDENTITY_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._@+-]{0,127}$")
AUTHORITY_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._:-]{0,127}$")
ORGANIZATION_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 .,&()/_+-]{1,127}$")
RFC3339_UTC = re.compile(
    r"^[0-9]{4}-(0[1-9]|1[0-2])-([0-2][0-9]|3[01])T"
    r"([01][0-9]|2[0-3]):[0-5][0-9]:[0-5][0-9]Z$"
)

EXPECTED_CLAIMS = {
    "appointment_active": False,
    "credit_eligible": False,
    "durable_archive": False,
    "durable_registry": False,
    "gate_complete": False,
    "independence_appointment_registered": False,
    "proof_of_key_possession_registered": False,
    "reviewer_registered": False,
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
EXPECTED_DURABILITY = {
    "candidate_file_is_durable_registration": False,
    "durable_registration_present": False,
    "repository_registry_is_durable_authority": False,
    "status": "required-missing",
    "workflow_artifact_is_durable_registration": False,
}
EXPECTED_APPOINTMENT_POLICY = {
    "allowed_key_types": ["ssh-ed25519"],
    "appointment_id_algorithm": APPOINTMENT_ID_ALGORITHM,
    "appointment_statuses": ["active", "revoked"],
    "candidate_lint_registers": False,
    "independence_evidence_namespace": INDEPENDENCE_NAMESPACE,
    "independence_evidence_required": True,
    "packet_max": PACKET_MAX,
    "packet_min": PACKET_MIN,
    "proof_namespace": POSSESSION_NAMESPACE,
    "proof_of_key_possession_required": True,
    "production_appointment_record_fields": [
        "appointment",
        "independence_evidence",
    ],
    "production_evidence_embedded": True,
    "production_record_schema": "embedded-appointment-and-independence-evidence-v1",
    "self_appointment_forbidden": True,
}
EXPECTED_CAMPAIGN_BINDING = {
    "campaign_authority": {
        "path": CAMPAIGN_PATH,
        "sha256": CAMPAIGN_SHA256,
        "size": CAMPAIGN_SIZE,
    },
    "campaign_id": CAMPAIGN_ID,
    "content_group_count": CONTENT_GROUP_COUNT,
    "packet_count": PACKET_COUNT,
    "review_unit_count": REVIEW_UNIT_COUNT,
    "source_commit": SOURCE_COMMIT,
}
EXPECTED_BLOCKERS = [
    "No production reviewer appointment is registered; the production appointments array is intentionally empty.",
    "Candidate lint validates an external proposal but never edits or registers it in this authority.",
    "A future production appointment record must embed its appointment and separately signed independence evidence so authorization can revalidate both SSHSIG proofs.",
    "No immutable durable reviewer-registration authority is present.",
    "No signed packet response or aggregate 219-packet response index is established by this registry.",
    "This registry cannot modify the source lock or tracker and cannot award RK-001 credit.",
]


class ReviewerRegistryError(RuntimeError):
    """Raised when registry or candidate validation fails closed."""


def reject_duplicate_pairs(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ReviewerRegistryError("duplicate JSON key: {0}".format(key))
        value[key] = item
    return value


def parse_bounded_json_int(token):
    if type(token) is not str or len(token) > MAX_JSON_NUMBER_TOKEN:
        raise ReviewerRegistryError("JSON integer token exceeds its cap")
    try:
        return int(token, 10)
    except ValueError as error:
        raise ReviewerRegistryError("JSON integer token is invalid: {0}".format(error))


def reject_json_float(token):
    if type(token) is not str or len(token) > MAX_JSON_NUMBER_TOKEN:
        raise ReviewerRegistryError("JSON float token exceeds its cap")
    raise ReviewerRegistryError("JSON floating-point values are forbidden")


def reject_json_constant(token):
    raise ReviewerRegistryError("nonfinite JSON value is forbidden: {0}".format(token))


def require_bounded_json_nesting(value):
    stack = [(value, 0)]
    while stack:
        current, depth = stack.pop()
        if depth > MAX_JSON_NESTING:
            raise ReviewerRegistryError("JSON nesting exceeds its cap")
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
        raise ReviewerRegistryError("value is not canonical JSON: {0}".format(error))
    return data + (b"\n" if newline else b"")


def read_json_bytes(data, label, canonical=False):
    try:
        text = data.decode("ascii")
        value = json.loads(
            text,
            object_pairs_hook=reject_duplicate_pairs,
            parse_constant=reject_json_constant,
            parse_float=reject_json_float,
            parse_int=parse_bounded_json_int,
        )
    except ReviewerRegistryError:
        raise
    except (RecursionError, UnicodeError, ValueError) as error:
        raise ReviewerRegistryError(
            "{0} is not valid JSON: {1}".format(label, error)
        )
    require_bounded_json_nesting(value)
    if type(value) is not dict:
        raise ReviewerRegistryError("{0} must be a JSON object".format(label))
    if canonical and data != canonical_json(value, newline=True):
        raise ReviewerRegistryError("{0} is not canonical JSON".format(label))
    return value


def exact_keys(value, keys, label):
    if type(value) is not dict or set(value) != set(keys):
        raise ReviewerRegistryError("{0} fields changed".format(label))
    return value


def require_exact(actual, expected, label):
    if type(actual) is not type(expected):
        raise ReviewerRegistryError("{0} type changed".format(label))
    if isinstance(expected, dict):
        if set(actual) != set(expected):
            raise ReviewerRegistryError("{0} fields changed".format(label))
        for key in expected:
            require_exact(actual[key], expected[key], label + "." + str(key))
        return actual
    if isinstance(expected, list):
        if len(actual) != len(expected):
            raise ReviewerRegistryError("{0} length changed".format(label))
        for index, pair in enumerate(zip(actual, expected)):
            require_exact(pair[0], pair[1], label + "[{0}]".format(index))
        return actual
    if actual != expected:
        raise ReviewerRegistryError(
            "{0} differs: {1!r} != {2!r}".format(label, actual, expected)
        )
    return actual


def require_bool(value, label):
    if type(value) is not bool:
        raise ReviewerRegistryError("{0} is not a boolean".format(label))
    return value


def require_nonnegative_int(value, label):
    if type(value) is not int or value < 0:
        raise ReviewerRegistryError("{0} is not a nonnegative integer".format(label))
    return value


def require_sha256(value, label):
    if type(value) is not str or not HEX_SHA256.fullmatch(value):
        raise ReviewerRegistryError("{0} is not a lowercase SHA-256".format(label))
    return value


def require_ssh_fingerprint(value, label):
    value = require_ascii_text(value, label, 128)
    if not value.startswith("SHA256:"):
        raise ReviewerRegistryError("{0} has the wrong algorithm".format(label))
    encoded = value[len("SHA256:") :]
    if len(encoded) != 43 or not re.fullmatch(r"[A-Za-z0-9+/]{43}", encoded):
        raise ReviewerRegistryError("{0} is malformed".format(label))
    try:
        digest = base64.b64decode((encoded + "=").encode("ascii"), validate=True)
    except (UnicodeError, binascii.Error) as error:
        raise ReviewerRegistryError("{0} is invalid: {1}".format(label, error))
    if len(digest) != 32:
        raise ReviewerRegistryError("{0} has the wrong digest length".format(label))
    canonical = base64.b64encode(digest).decode("ascii").rstrip("=")
    if canonical != encoded:
        raise ReviewerRegistryError("{0} is not canonical base64".format(label))
    return value


def require_ascii_text(value, label, maximum=4096, minimum=1):
    if type(value) is not str or len(value) < minimum or len(value) > maximum:
        raise ReviewerRegistryError("{0} is not a bounded string".format(label))
    if value != value.strip():
        raise ReviewerRegistryError("{0} has surrounding whitespace".format(label))
    if any(ord(character) < 32 or ord(character) > 126 for character in value):
        raise ReviewerRegistryError("{0} is not printable ASCII".format(label))
    return value


def require_identity(value, label):
    value = require_ascii_text(value, label, 128)
    if not IDENTITY_PATTERN.fullmatch(value):
        raise ReviewerRegistryError("{0} is malformed".format(label))
    return value


def require_authority_id(value, label):
    value = require_ascii_text(value, label, 128)
    if not AUTHORITY_ID_PATTERN.fullmatch(value):
        raise ReviewerRegistryError("{0} is malformed".format(label))
    return value


def require_organization(value, label):
    value = require_ascii_text(value, label, 128, 2)
    if not ORGANIZATION_PATTERN.fullmatch(value):
        raise ReviewerRegistryError("{0} is malformed".format(label))
    return value


def parse_utc_timestamp(value, label):
    value = require_ascii_text(value, label, 32)
    if not RFC3339_UTC.fullmatch(value):
        raise ReviewerRegistryError("{0} is not UTC RFC3339".format(label))
    try:
        parsed = datetime.datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError as error:
        raise ReviewerRegistryError(
            "{0} is not a real UTC time: {1}".format(label, error)
        )
    return parsed


def require_packet_id(value, label):
    if type(value) is not str or not PACKET_ID_PATTERN.fullmatch(value):
        raise ReviewerRegistryError("{0} is not a four-digit packet ID".format(label))
    if value < PACKET_MIN or value > PACKET_MAX:
        raise ReviewerRegistryError("{0} is outside the campaign".format(label))
    return value


def stable_id(prefix, payload):
    if type(prefix) is not str or not re.fullmatch(r"[a-z][a-z0-9-]*", prefix):
        raise ReviewerRegistryError("stable ID prefix is malformed")
    return prefix + ":" + hashlib.sha256(canonical_json(payload)).hexdigest()


def safe_relative(value, label):
    value = require_ascii_text(value, label, 4096)
    if "\\" in value:
        raise ReviewerRegistryError("{0} contains a backslash".format(label))
    candidate = PurePosixPath(value)
    if candidate.is_absolute() or not candidate.parts:
        raise ReviewerRegistryError("{0} is not relative".format(label))
    if any(part in ("", ".", "..") for part in candidate.parts):
        raise ReviewerRegistryError("{0} contains an unsafe component".format(label))
    if str(candidate) != value:
        raise ReviewerRegistryError("{0} is not normalized".format(label))
    return candidate


def _safe_flags(directory=False):
    flags = os.O_RDONLY
    flags |= getattr(os, "O_CLOEXEC", 0)
    flags |= getattr(os, "O_NOFOLLOW", 0)
    if directory:
        flags |= getattr(os, "O_DIRECTORY", 0)
    else:
        flags |= getattr(os, "O_NONBLOCK", 0)
    return flags


def _directory_identity(metadata):
    return (
        metadata.st_dev,
        metadata.st_ino,
        metadata.st_mode,
        metadata.st_nlink,
        metadata.st_uid,
        metadata.st_gid,
        metadata.st_size,
        getattr(metadata, "st_mtime_ns", int(metadata.st_mtime * 1000000000)),
        getattr(metadata, "st_ctime_ns", int(metadata.st_ctime * 1000000000)),
    )


def _file_identity(metadata):
    return (
        metadata.st_dev,
        metadata.st_ino,
        metadata.st_mode,
        metadata.st_nlink,
        metadata.st_size,
        metadata.st_uid,
        metadata.st_gid,
        getattr(metadata, "st_mtime_ns", int(metadata.st_mtime * 1000000000)),
        getattr(metadata, "st_ctime_ns", int(metadata.st_ctime * 1000000000)),
    )


def _validate_namespace_directory(metadata, label, final=False):
    if not stat.S_ISDIR(metadata.st_mode):
        raise ReviewerRegistryError("{0} is not a directory".format(label))
    if metadata.st_uid not in (0, os.geteuid()):
        raise ReviewerRegistryError("{0} has an untrusted owner".format(label))
    if final and metadata.st_mode & (stat.S_IWGRP | stat.S_IWOTH):
        raise ReviewerRegistryError("{0} is group/world writable".format(label))
    return _directory_identity(metadata)


def _open_root_namespace(root, label):
    """Open each absolute namespace component and retain the final descriptor."""
    root = Path(os.path.abspath(str(root)))
    components = root.parts[1:]
    descriptors = []
    records = []
    try:
        current = os.open(os.sep, _safe_flags(directory=True))
        descriptors.append(current)
        root_metadata = os.fstat(current)
        records.append(
            (os.sep, _validate_namespace_directory(root_metadata, label + " ancestor /"))
        )
        for index, component in enumerate(components):
            next_descriptor = os.open(
                component,
                _safe_flags(directory=True),
                dir_fd=current,
            )
            descriptors.append(next_descriptor)
            current = next_descriptor
            metadata = os.fstat(current)
            records.append(
                (
                    component,
                    _validate_namespace_directory(
                        metadata,
                        label + " namespace " + component,
                        final=index == len(components) - 1,
                    ),
                )
            )
        if not components:
            _validate_namespace_directory(root_metadata, label, final=True)
        final_descriptor = descriptors[-1]
        for descriptor in descriptors[:-1]:
            os.close(descriptor)
        return root, final_descriptor, tuple(records)
    except ReviewerRegistryError:
        for descriptor in reversed(descriptors):
            try:
                os.close(descriptor)
            except OSError:
                pass
        raise
    except OSError as error:
        for descriptor in reversed(descriptors):
            try:
                os.close(descriptor)
            except OSError:
                pass
        raise ReviewerRegistryError("cannot open {0}: {1}".format(label, error))


def _replay_root_namespace(root, expected_records, label):
    replay_descriptor = None
    try:
        replay_root, replay_descriptor, actual_records = _open_root_namespace(root, label)
        if replay_root != root or actual_records != expected_records:
            raise ReviewerRegistryError("{0} namespace changed while being read".format(label))
    finally:
        if replay_descriptor is not None:
            try:
                os.close(replay_descriptor)
            except OSError:
                pass


def validate_root_directory(root, label):
    descriptor = None
    try:
        root, descriptor, records = _open_root_namespace(root, label)
        _replay_root_namespace(root, records, label)
        return root
    finally:
        if descriptor is not None:
            try:
                os.close(descriptor)
            except OSError:
                pass


def _read_descriptor(descriptor, label, cap):
    chunks = []
    retained = 0
    while True:
        try:
            chunk = os.read(descriptor, min(1024 * 1024, cap - retained + 1))
        except InterruptedError:
            continue
        if not chunk:
            break
        retained += len(chunk)
        if retained > cap:
            raise ReviewerRegistryError("{0} exceeds its size cap".format(label))
        chunks.append(chunk)
    return b"".join(chunks)


def _replay_held_relative(context, label):
    root_descriptor = context["root_descriptor"]
    root_identity = context["namespace_records"][-1][1]
    try:
        if _directory_identity(os.fstat(root_descriptor)) != root_identity:
            raise ReviewerRegistryError("{0} root descriptor changed".format(label))
        for record in context["relative_directories"]:
            opened = os.fstat(record["descriptor"])
            namespace = os.stat(
                record["name"],
                dir_fd=record["parent_descriptor"],
                follow_symlinks=False,
            )
            if (
                _directory_identity(opened) != record["identity"]
                or _directory_identity(namespace) != record["identity"]
            ):
                raise ReviewerRegistryError(
                    "{0} parent namespace changed".format(label)
                )
        opened = os.fstat(context["file_descriptor"])
        namespace = os.stat(
            context["file_name"],
            dir_fd=context["file_parent_descriptor"],
            follow_symlinks=False,
        )
    except ReviewerRegistryError:
        raise
    except OSError as error:
        raise ReviewerRegistryError(
            "{0} namespace replay failed: {1}".format(label, error)
        )
    if (
        _file_identity(opened) != context["file_identity"]
        or _file_identity(namespace) != context["file_identity"]
    ):
        raise ReviewerRegistryError("{0} file namespace changed".format(label))
    _validate_namespace_directory(os.fstat(root_descriptor), label + " root", final=True)
    _replay_root_namespace(
        context["root"], context["namespace_records"], label + " root"
    )


def _read_held_relative_pass(context, label, cap):
    _replay_held_relative(context, label)
    expected_size = context["file_identity"][4]
    try:
        os.lseek(context["file_descriptor"], 0, os.SEEK_SET)
        chunks = []
        retained = 0
        while retained < expected_size:
            chunk = os.read(
                context["file_descriptor"], min(1024 * 1024, expected_size - retained)
            )
            if not chunk:
                raise ReviewerRegistryError(
                    "{0} ended before its bound size".format(label)
                )
            retained += len(chunk)
            if retained > cap:
                raise ReviewerRegistryError("{0} exceeds its size cap".format(label))
            chunks.append(chunk)
            _replay_held_relative(context, label)
        if os.read(context["file_descriptor"], 1):
            raise ReviewerRegistryError("{0} grew while read".format(label))
    except ReviewerRegistryError:
        raise
    except OSError as error:
        raise ReviewerRegistryError("cannot read {0}: {1}".format(label, error))
    _replay_held_relative(context, label)
    data = b"".join(chunks)
    if len(data) != expected_size:
        raise ReviewerRegistryError("{0} size changed while read".format(label))
    return data


def read_secure_relative(root, relative, label, cap):
    relative = safe_relative(str(relative), label + " path")
    root_descriptor = None
    namespace_records = None
    relative_directories = []
    file_descriptor = None
    try:
        root, root_descriptor, namespace_records = _open_root_namespace(
            root, label + " root"
        )
        current = root_descriptor
        for component in relative.parts[:-1]:
            next_descriptor = os.open(
                component,
                _safe_flags(directory=True),
                dir_fd=current,
            )
            try:
                directory_metadata = os.fstat(next_descriptor)
                directory_namespace = os.stat(
                    component, dir_fd=current, follow_symlinks=False
                )
                _validate_namespace_directory(
                    directory_metadata, label + " parent " + component, final=True
                )
                if _directory_identity(directory_metadata) != _directory_identity(
                    directory_namespace
                ):
                    raise ReviewerRegistryError(
                        "{0} parent identity changed".format(label)
                    )
            except Exception:
                os.close(next_descriptor)
                raise
            relative_directories.append(
                {
                    "descriptor": next_descriptor,
                    "identity": _directory_identity(directory_metadata),
                    "name": component,
                    "parent_descriptor": current,
                }
            )
            current = next_descriptor
        file_descriptor = os.open(
            relative.parts[-1],
            _safe_flags(directory=False),
            dir_fd=current,
        )
        first = os.fstat(file_descriptor)
        namespace_first = os.stat(
            relative.parts[-1], dir_fd=current, follow_symlinks=False
        )
        if not stat.S_ISREG(first.st_mode):
            raise ReviewerRegistryError("{0} is not a regular file".format(label))
        if _file_identity(first) != _file_identity(namespace_first):
            raise ReviewerRegistryError("{0} opened identity changed".format(label))
        if first.st_nlink != 1:
            raise ReviewerRegistryError("{0} has multiple hard links".format(label))
        if first.st_uid not in (0, os.geteuid()):
            raise ReviewerRegistryError("{0} has an untrusted owner".format(label))
        if first.st_mode & (stat.S_IWGRP | stat.S_IWOTH):
            raise ReviewerRegistryError("{0} is group/world writable".format(label))
        if first.st_size > cap:
            raise ReviewerRegistryError("{0} exceeds its size cap".format(label))
        context = {
            "file_descriptor": file_descriptor,
            "file_identity": _file_identity(first),
            "file_name": relative.parts[-1],
            "file_parent_descriptor": current,
            "namespace_records": namespace_records,
            "relative_directories": relative_directories,
            "root": root,
            "root_descriptor": root_descriptor,
        }
        first_data = _read_held_relative_pass(context, label, cap)
        second_data = _read_held_relative_pass(context, label, cap)
        if first_data != second_data:
            raise ReviewerRegistryError("{0} byte replay differs".format(label))
        _replay_held_relative(context, label)
        return second_data
    except ReviewerRegistryError:
        raise
    except OSError as error:
        raise ReviewerRegistryError("cannot open {0}: {1}".format(label, error))
    finally:
        if file_descriptor is not None:
            try:
                os.close(file_descriptor)
            except OSError:
                pass
        for record in reversed(relative_directories):
            try:
                os.close(record["descriptor"])
            except OSError:
                pass
        if root_descriptor is not None:
            try:
                os.close(root_descriptor)
            except OSError:
                pass


def read_external_file(path, label, cap):
    path = Path(os.path.abspath(str(path)))
    if path.name in ("", ".", ".."):
        raise ReviewerRegistryError("{0} path is invalid".format(label))
    root = path.parent
    return read_secure_relative(root, path.name, label, cap), root


def _public_key_fingerprint(public_key, expected_type):
    public_key = require_ascii_text(public_key, "SSH public key", 16384)
    parts = public_key.split(" ")
    if len(parts) != 2 or parts[0] != expected_type:
        raise ReviewerRegistryError("SSH public key format differs")
    try:
        blob = base64.b64decode(parts[1].encode("ascii"), validate=True)
    except (UnicodeError, binascii.Error) as error:
        raise ReviewerRegistryError("SSH public key is invalid: {0}".format(error))
    if len(blob) < 16 or len(blob) > 16384:
        raise ReviewerRegistryError("SSH public key blob is unbounded")
    if base64.b64encode(blob).decode("ascii") != parts[1]:
        raise ReviewerRegistryError("SSH public key is not canonical base64")

    def ssh_string(offset, label):
        if offset + 4 > len(blob):
            raise ReviewerRegistryError("SSH public key lacks {0}".format(label))
        length = int.from_bytes(blob[offset : offset + 4], "big")
        start = offset + 4
        end = start + length
        if length > 16384 or end > len(blob):
            raise ReviewerRegistryError("SSH public key {0} is invalid".format(label))
        return blob[start:end], end

    wire_type, offset = ssh_string(0, "wire type")
    key_bytes, offset = ssh_string(offset, "key bytes")
    try:
        wire_type_text = wire_type.decode("ascii")
    except UnicodeError as error:
        raise ReviewerRegistryError(
            "SSH public key wire type is invalid: {0}".format(error)
        )
    if wire_type_text != expected_type or len(key_bytes) != 32 or offset != len(blob):
        raise ReviewerRegistryError("SSH public key wire structure differs")
    digest = base64.b64encode(hashlib.sha256(blob).digest()).decode("ascii")
    return "SHA256:" + digest.rstrip("=")


def validate_key_record(record, label, identity_key):
    exact_keys(
        record,
        {
            identity_key,
            "key_type",
            "ssh_fingerprint",
            "ssh_public_key",
        },
        label,
    )
    identity = require_identity(record[identity_key], label + " identity")
    require_exact(record["key_type"], "ssh-ed25519", label + " key type")
    fingerprint = _public_key_fingerprint(
        record["ssh_public_key"], record["key_type"]
    )
    require_exact(
        record["ssh_fingerprint"], fingerprint, label + " SSH fingerprint"
    )
    return identity


def appointment_identity_payload(appointment):
    return {
        "appointing_authority": appointment["appointing_authority"],
        "campaign_binding": appointment["campaign_binding"],
        "reviewer": appointment["reviewer"],
        "scope": appointment["scope"],
        "validity": appointment["validity"],
    }


def appointment_signing_payload(appointment):
    payload = appointment_identity_payload(appointment)
    payload["appointment_id"] = appointment["appointment_id"]
    payload["independence_evidence"] = appointment["independence_evidence"]
    payload["status"] = appointment["status"]
    return payload


def evidence_identity_payload(evidence):
    return {
        key: evidence[key]
        for key in evidence
        if key not in ("authority_proof", "evidence_id")
    }


def evidence_signing_payload(evidence):
    return {key: evidence[key] for key in evidence if key != "authority_proof"}


def _validate_signature_shape(record, payload, namespace, label):
    exact_keys(
        record,
        {"format", "namespace", "payload_algorithm", "payload_sha256", "signature"},
        label,
    )
    require_exact(record["format"], SSHSIG_FORMAT, label + " format")
    require_exact(record["namespace"], namespace, label + " namespace")
    require_exact(
        record["payload_algorithm"], PAYLOAD_ALGORITHM, label + " payload algorithm"
    )
    payload_bytes = canonical_json(payload, newline=True)
    require_exact(
        record["payload_sha256"],
        hashlib.sha256(payload_bytes).hexdigest(),
        label + " payload digest",
    )
    signature = record["signature"]
    if type(signature) is not str or not signature:
        raise ReviewerRegistryError("{0} signature is missing".format(label))
    try:
        signature_bytes = signature.encode("ascii")
    except UnicodeError as error:
        raise ReviewerRegistryError(
            "{0} signature is not ASCII: {1}".format(label, error)
        )
    if len(signature_bytes) > MAX_SIGNATURE_BYTES:
        raise ReviewerRegistryError("{0} signature exceeds its cap".format(label))
    if b"\r" in signature_bytes or b"\x00" in signature_bytes:
        raise ReviewerRegistryError("{0} signature has forbidden bytes".format(label))
    if not signature_bytes.startswith(b"-----BEGIN SSH SIGNATURE-----\n"):
        raise ReviewerRegistryError("{0} signature is not an SSHSIG".format(label))
    if not signature_bytes.endswith(b"-----END SSH SIGNATURE-----\n"):
        raise ReviewerRegistryError("{0} signature is truncated".format(label))
    return payload_bytes, signature_bytes


def _validate_ssh_keygen():
    path = "/usr/bin/ssh-keygen"
    try:
        metadata = os.lstat(path)
    except OSError as error:
        raise ReviewerRegistryError("cannot inspect SSHSIG verifier: {0}".format(error))
    if (
        not stat.S_ISREG(metadata.st_mode)
        or stat.S_ISLNK(metadata.st_mode)
        or metadata.st_nlink != 1
        or metadata.st_uid != 0
        or metadata.st_mode & (stat.S_IWGRP | stat.S_IWOTH)
        or not metadata.st_mode & stat.S_IXUSR
    ):
        raise ReviewerRegistryError("SSHSIG verifier metadata is unsafe")
    return path


def _verify_immutable_pass_fd(descriptor, identity, expected, path, label):
    try:
        for _unused in range(2):
            opened = os.fstat(descriptor)
            namespace = os.stat(str(path), follow_symlinks=False)
            if (
                _file_identity(opened) != identity
                or _file_identity(namespace) != identity
                or not stat.S_ISREG(opened.st_mode)
                or stat.S_IMODE(opened.st_mode) != 0o400
                or opened.st_nlink != 1
                or opened.st_uid not in (0, os.geteuid())
            ):
                raise ReviewerRegistryError(
                    "{0} immutable identity changed".format(label)
                )
            os.lseek(descriptor, 0, os.SEEK_SET)
            actual = _read_descriptor(descriptor, label, len(expected))
            if actual != expected:
                raise ReviewerRegistryError(
                    "{0} immutable bytes changed".format(label)
                )
            if _file_identity(os.fstat(descriptor)) != identity:
                raise ReviewerRegistryError(
                    "{0} immutable descriptor changed while read".format(label)
                )
    except ReviewerRegistryError:
        raise
    except OSError as error:
        raise ReviewerRegistryError("cannot replay {0}: {1}".format(label, error))


def _immutable_pass_fd(data, directory, prefix, label):
    staging_descriptor = None
    descriptor = None
    path = None
    try:
        staging_descriptor, raw_path = tempfile.mkstemp(prefix=prefix, dir=str(directory))
        path = Path(raw_path)
        retained = 0
        while retained < len(data):
            written = os.write(staging_descriptor, data[retained:])
            if written <= 0:
                raise ReviewerRegistryError(
                    "{0} immutable copy was short".format(label)
                )
            retained += written
        os.fsync(staging_descriptor)
        os.fchmod(staging_descriptor, 0o400)
        descriptor = os.open(
            "/proc/self/fd/{0}".format(staging_descriptor),
            os.O_RDONLY | getattr(os, "O_CLOEXEC", 0),
        )
        os.close(staging_descriptor)
        staging_descriptor = None
        info = os.fstat(descriptor)
        namespace = os.stat(str(path), follow_symlinks=False)
        if (
            not stat.S_ISREG(info.st_mode)
            or _file_identity(info) != _file_identity(namespace)
            or stat.S_IMODE(info.st_mode) != 0o400
            or info.st_nlink != 1
            or info.st_size != len(data)
            or info.st_uid not in (0, os.geteuid())
        ):
            raise ReviewerRegistryError(
                "{0} immutable copy identity differs".format(label)
            )
        identity = _file_identity(info)
        _verify_immutable_pass_fd(descriptor, identity, data, path, label)
        return descriptor, identity, path
    except ReviewerRegistryError:
        raise
    except OSError as error:
        raise ReviewerRegistryError("cannot retain {0}: {1}".format(label, error))
    finally:
        if staging_descriptor is not None:
            try:
                os.close(staging_descriptor)
            except OSError:
                pass
        if descriptor is not None and sys.exc_info()[0] is not None:
            try:
                os.close(descriptor)
            except OSError:
                pass


def verify_sshsig(public_key, identity, signature_bytes, payload, namespace):
    identity = require_identity(identity, "SSHSIG principal")
    public_key = require_ascii_text(public_key, "SSHSIG public key", 16384)
    namespace = require_ascii_text(namespace, "SSHSIG namespace", 128)
    executable = _validate_ssh_keygen()
    allowed_bytes = (identity + " " + public_key + "\n").encode("ascii")
    with tempfile.TemporaryDirectory(prefix="mckernel-rk001-registry-") as temporary:
        os.chmod(temporary, 0o700)
        allowed_descriptor = None
        signature_descriptor = None
        process = None
        try:
            allowed_descriptor, allowed_identity, allowed_path = _immutable_pass_fd(
                allowed_bytes, temporary, "allowed-signers-", "allowed-signers copy"
            )
            signature_descriptor, signature_identity, signature_path = _immutable_pass_fd(
                signature_bytes, temporary, "signature-", "signature copy"
            )
            process = subprocess.Popen(
                [
                    executable,
                    "-Y",
                    "verify",
                    "-f",
                    "/proc/self/fd/{0}".format(allowed_descriptor),
                    "-I",
                    identity,
                    "-n",
                    namespace,
                    "-s",
                    "/proc/self/fd/{0}".format(signature_descriptor),
                ],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env={
                    "HOME": "/nonexistent",
                    "LANG": "C",
                    "LC_ALL": "C",
                    "PATH": "/usr/bin:/bin",
                },
                pass_fds=(allowed_descriptor, signature_descriptor),
            )
            _verify_immutable_pass_fd(
                allowed_descriptor,
                allowed_identity,
                allowed_bytes,
                allowed_path,
                "allowed-signers copy",
            )
            _verify_immutable_pass_fd(
                signature_descriptor,
                signature_identity,
                signature_bytes,
                signature_path,
                "signature copy",
            )
            stdout, stderr = process.communicate(
                input=payload, timeout=SSHSIG_TIMEOUT_SECONDS
            )
        except subprocess.TimeoutExpired:
            process.kill()
            process.communicate()
            raise ReviewerRegistryError("SSHSIG verification timed out")
        except ReviewerRegistryError:
            if process is not None:
                if process.poll() is None:
                    process.kill()
                process.communicate()
            raise
        except OSError as error:
            if process is not None:
                if process.poll() is None:
                    process.kill()
                process.communicate()
            raise ReviewerRegistryError(
                "cannot execute SSHSIG verifier: {0}".format(error)
            )
        finally:
            try:
                if allowed_descriptor is not None:
                    _verify_immutable_pass_fd(
                        allowed_descriptor,
                        allowed_identity,
                        allowed_bytes,
                        allowed_path,
                        "allowed-signers copy",
                    )
                if signature_descriptor is not None:
                    _verify_immutable_pass_fd(
                        signature_descriptor,
                        signature_identity,
                        signature_bytes,
                        signature_path,
                        "signature copy",
                    )
            finally:
                for descriptor in (signature_descriptor, allowed_descriptor):
                    if descriptor is not None:
                        try:
                            os.close(descriptor)
                        except OSError:
                            pass
        if len(stdout) + len(stderr) > 1024 * 1024:
            raise ReviewerRegistryError("SSHSIG verifier output exceeds its cap")
        if process.returncode != 0:
            raise ReviewerRegistryError("SSHSIG verification failed")


def validate_authority(authority):
    exact_keys(
        authority,
        {
            "appointment_policy",
            "appointments",
            "campaign_binding",
            "claims",
            "durability",
            "gate",
            "registration_status",
            "registry_id",
            "registry_version",
            "remaining_blockers",
            "revocation_epoch",
            "schema_version",
        },
        "reviewer registry authority",
    )
    require_exact(authority["schema_version"], SCHEMA_VERSION, "schema version")
    require_exact(authority["registry_id"], REGISTRY_ID, "registry ID")
    require_exact(authority["registry_version"], REGISTRY_VERSION, "registry version")
    require_exact(
        authority["revocation_epoch"], REVOCATION_EPOCH, "registry revocation epoch"
    )
    require_exact(
        authority["registration_status"], "required-missing", "registration status"
    )
    require_exact(authority["appointments"], [], "production appointments")
    require_exact(
        authority["appointment_policy"],
        EXPECTED_APPOINTMENT_POLICY,
        "appointment policy",
    )
    require_exact(
        authority["campaign_binding"],
        EXPECTED_CAMPAIGN_BINDING,
        "campaign binding",
    )
    require_exact(authority["claims"], EXPECTED_CLAIMS, "registry claims")
    require_exact(authority["durability"], EXPECTED_DURABILITY, "durability")
    require_exact(authority["gate"], EXPECTED_GATE, "gate")
    require_exact(
        authority["remaining_blockers"], EXPECTED_BLOCKERS, "remaining blockers"
    )
    return authority


def validate_campaign(campaign):
    exact_keys(
        campaign,
        {
            "archive_expansion_bindings",
            "campaign_id",
            "claims",
            "expected_result",
            "future_response_schema",
            "gate",
            "inputs",
            "package_policy",
            "packets",
            "partition_policy",
            "remaining_blockers",
            "schema_version",
        },
        "campaign authority",
    )
    require_exact(campaign["schema_version"], 1, "campaign schema")
    require_exact(campaign["campaign_id"], CAMPAIGN_ID, "campaign ID")
    expected = campaign["expected_result"]
    if type(expected) is not dict:
        raise ReviewerRegistryError("campaign expected result is not an object")
    require_exact(expected.get("packet_count"), PACKET_COUNT, "campaign packet count")
    require_exact(
        expected.get("review_unit_count"), REVIEW_UNIT_COUNT, "campaign review units"
    )
    require_exact(
        expected.get("content_group_count"),
        CONTENT_GROUP_COUNT,
        "campaign content groups",
    )
    if type(campaign["packets"]) is not list or len(campaign["packets"]) != PACKET_COUNT:
        raise ReviewerRegistryError("campaign packet records changed")
    inventory = campaign.get("inputs", {}).get("inventory_artifact", {})
    require_exact(inventory.get("source_commit"), SOURCE_COMMIT, "campaign source commit")
    require_exact(campaign["claims"].get("campaign_complete"), False, "campaign completion")
    require_exact(campaign["claims"].get("credit_eligible"), False, "campaign credit")
    require_exact(campaign["claims"].get("durable_archive"), False, "campaign durability")
    require_exact(campaign["claims"].get("tracker_credit"), False, "campaign tracker credit")
    require_exact(campaign["gate"], {
        "credit_eligible": False,
        "gate_id": "RK-001",
        "points_awarded": 0,
        "status": "TODO",
        "tracker_credit": False,
    }, "campaign gate")
    return campaign


def _validate_campaign_binding(record):
    require_exact(
        record,
        {
            "campaign_authority_sha256": CAMPAIGN_SHA256,
            "campaign_id": CAMPAIGN_ID,
            "source_commit": SOURCE_COMMIT,
        },
        "candidate campaign binding",
    )


def _validate_reviewer(record):
    exact_keys(
        record,
        {
            "key_type",
            "organization",
            "reviewer_identity",
            "role",
            "ssh_fingerprint",
            "ssh_public_key",
        },
        "candidate reviewer",
    )
    identity = require_identity(record["reviewer_identity"], "reviewer identity")
    organization = require_organization(record["organization"], "reviewer organization")
    require_exact(record["role"], "independent-license-reviewer", "reviewer role")
    require_exact(record["key_type"], "ssh-ed25519", "reviewer key type")
    fingerprint = _public_key_fingerprint(record["ssh_public_key"], record["key_type"])
    require_ssh_fingerprint(record["ssh_fingerprint"], "reviewer fingerprint")
    require_exact(record["ssh_fingerprint"], fingerprint, "reviewer fingerprint")
    return identity, organization


def _validate_appointing_authority(record):
    exact_keys(
        record,
        {
            "authority_id",
            "issued_at",
            "issuer_identity",
            "issuer_organization",
            "key_type",
            "ssh_fingerprint",
            "ssh_public_key",
        },
        "appointing authority",
    )
    require_authority_id(record["authority_id"], "appointing authority ID")
    identity = require_identity(record["issuer_identity"], "appointing issuer identity")
    organization = require_organization(
        record["issuer_organization"], "appointing issuer organization"
    )
    parse_utc_timestamp(record["issued_at"], "appointment issue time")
    require_exact(record["key_type"], "ssh-ed25519", "appointing authority key type")
    fingerprint = _public_key_fingerprint(record["ssh_public_key"], record["key_type"])
    require_ssh_fingerprint(
        record["ssh_fingerprint"], "appointing authority fingerprint"
    )
    require_exact(
        record["ssh_fingerprint"], fingerprint, "appointing authority fingerprint"
    )
    return identity, organization


def _validate_scope(scope):
    exact_keys(scope, {"packet_max", "packet_min"}, "appointment scope")
    lower = require_packet_id(scope["packet_min"], "appointment packet minimum")
    upper = require_packet_id(scope["packet_max"], "appointment packet maximum")
    if lower > upper:
        raise ReviewerRegistryError("appointment packet scope is reversed")


def _validate_validity(validity, issued_at):
    exact_keys(validity, {"valid_from", "valid_through"}, "appointment validity")
    issued = parse_utc_timestamp(issued_at, "appointment issue time")
    lower = parse_utc_timestamp(validity["valid_from"], "appointment valid_from")
    upper = parse_utc_timestamp(validity["valid_through"], "appointment valid_through")
    if issued > lower:
        raise ReviewerRegistryError("appointment starts before it was issued")
    if lower > upper:
        raise ReviewerRegistryError("appointment validity interval is reversed")
    if upper - lower > datetime.timedelta(days=366):
        raise ReviewerRegistryError("appointment validity exceeds one year")


def _validate_evidence_binding(binding):
    exact_keys(binding, {"path", "sha256", "size"}, "independence evidence binding")
    safe_relative(binding["path"], "independence evidence path")
    require_sha256(binding["sha256"], "independence evidence digest")
    size = require_nonnegative_int(binding["size"], "independence evidence size")
    if size == 0 or size > MAX_EVIDENCE_BYTES:
        raise ReviewerRegistryError("independence evidence size is outside its cap")


def validate_appointment_structure(appointment):
    exact_keys(
        appointment,
        {
            "appointment_id",
            "appointing_authority",
            "campaign_binding",
            "independence_evidence",
            "proof_of_key_possession",
            "reviewer",
            "scope",
            "status",
            "validity",
        },
        "appointment candidate",
    )
    _validate_campaign_binding(appointment["campaign_binding"])
    reviewer_identity, reviewer_organization = _validate_reviewer(
        appointment["reviewer"]
    )
    issuer_identity, issuer_organization = _validate_appointing_authority(
        appointment["appointing_authority"]
    )
    if reviewer_identity == issuer_identity:
        raise ReviewerRegistryError("reviewer cannot appoint itself")
    if reviewer_organization == issuer_organization:
        raise ReviewerRegistryError("reviewer and appointing authority share an organization")
    if (
        appointment["reviewer"]["ssh_public_key"]
        == appointment["appointing_authority"]["ssh_public_key"]
        or appointment["reviewer"]["ssh_fingerprint"]
        == appointment["appointing_authority"]["ssh_fingerprint"]
    ):
        raise ReviewerRegistryError(
            "reviewer and appointing authority must use different SSH keys"
        )
    if appointment["status"] not in ("active", "revoked"):
        raise ReviewerRegistryError("appointment status is invalid")
    _validate_scope(appointment["scope"])
    _validate_validity(
        appointment["validity"], appointment["appointing_authority"]["issued_at"]
    )
    _validate_evidence_binding(appointment["independence_evidence"])
    expected_id = stable_id("appointment", appointment_identity_payload(appointment))
    if not STABLE_ID_PATTERN.fullmatch(
        require_ascii_text(appointment["appointment_id"], "appointment ID", 80)
    ):
        raise ReviewerRegistryError("appointment ID is malformed")
    require_exact(appointment["appointment_id"], expected_id, "appointment ID")
    _validate_signature_shape(
        appointment["proof_of_key_possession"],
        appointment_signing_payload(appointment),
        POSSESSION_NAMESPACE,
        "proof of key possession",
    )
    return appointment


def validate_independence_evidence(evidence, appointment):
    exact_keys(
        evidence,
        {
            "appointment_id",
            "appointment_status",
            "authority_proof",
            "campaign_id",
            "capture_operator_identities",
            "capture_organization",
            "conflict_check",
            "evidence_basis",
            "evidence_id",
            "independent_from_campaign_generation",
            "independent_from_capture",
            "independent_from_source_capture",
            "issued_at",
            "issuer_identity",
            "issuer_organization",
            "reviewer_identity",
            "reviewer_organization",
            "schema_version",
            "source_commit",
            "statement",
        },
        "independence evidence",
    )
    require_exact(evidence["schema_version"], SCHEMA_VERSION, "evidence schema")
    require_exact(evidence["campaign_id"], CAMPAIGN_ID, "evidence campaign ID")
    require_exact(evidence["source_commit"], SOURCE_COMMIT, "evidence source commit")
    require_exact(
        evidence["appointment_id"], appointment["appointment_id"], "evidence appointment"
    )
    require_exact(
        evidence["appointment_status"], appointment["status"], "evidence appointment status"
    )
    reviewer = appointment["reviewer"]
    authority = appointment["appointing_authority"]
    for key in ("reviewer_identity", "organization"):
        evidence_key = "reviewer_organization" if key == "organization" else key
        require_exact(
            evidence[evidence_key], reviewer[key], "evidence " + evidence_key
        )
    require_exact(
        evidence["issuer_identity"], authority["issuer_identity"], "evidence issuer"
    )
    require_exact(
        evidence["issuer_organization"],
        authority["issuer_organization"],
        "evidence issuer organization",
    )
    require_exact(evidence["issued_at"], authority["issued_at"], "evidence issue time")
    capture_organization = require_organization(
        evidence["capture_organization"], "capture organization"
    )
    if capture_organization == reviewer["organization"]:
        raise ReviewerRegistryError("reviewer organization performed source capture")
    identities = evidence["capture_operator_identities"]
    if type(identities) is not list or not identities or len(identities) > MAX_CAPTURE_IDENTITIES:
        raise ReviewerRegistryError("capture operator identities are unbounded")
    normalized = [require_identity(item, "capture operator identity") for item in identities]
    if normalized != sorted(set(normalized)):
        raise ReviewerRegistryError("capture operator identities are duplicated or unsorted")
    if reviewer["reviewer_identity"] in normalized:
        raise ReviewerRegistryError("reviewer performed source capture")
    require_exact(
        evidence["conflict_check"], "completed-no-conflict", "evidence conflict check"
    )
    require_exact(
        evidence["evidence_basis"],
        "organizational-separation-and-conflict-check-v1",
        "evidence basis",
    )
    for key in (
        "independent_from_campaign_generation",
        "independent_from_capture",
        "independent_from_source_capture",
    ):
        require_exact(require_bool(evidence[key], "evidence " + key), True, "evidence " + key)
    require_exact(
        require_ascii_text(evidence["statement"], "independence statement", 512, 32),
        "The appointed reviewer is organizationally and operationally independent from source capture and campaign generation.",
        "independence statement",
    )
    evidence_id = require_ascii_text(evidence["evidence_id"], "evidence ID", 96)
    if not STABLE_ID_PATTERN.fullmatch(evidence_id):
        raise ReviewerRegistryError("evidence ID is malformed")
    require_exact(
        evidence_id,
        stable_id("independence-evidence", evidence_identity_payload(evidence)),
        "evidence ID",
    )
    payload, signature = _validate_signature_shape(
        evidence["authority_proof"],
        evidence_signing_payload(evidence),
        INDEPENDENCE_NAMESPACE,
        "independence authority proof",
    )
    verify_sshsig(
        authority["ssh_public_key"],
        authority["issuer_identity"],
        signature,
        payload,
        INDEPENDENCE_NAMESPACE,
    )
    return evidence


def _validate_candidate_material(candidate, evidence_bytes):
    if type(evidence_bytes) is not bytes:
        raise ReviewerRegistryError("independence evidence must be raw bytes")
    validate_appointment_structure(candidate)
    binding = candidate["independence_evidence"]
    if len(evidence_bytes) != binding["size"]:
        raise ReviewerRegistryError("independence evidence size differs")
    if hashlib.sha256(evidence_bytes).hexdigest() != binding["sha256"]:
        raise ReviewerRegistryError("independence evidence digest differs")
    evidence = read_json_bytes(
        evidence_bytes, "independence evidence", canonical=True
    )
    validate_independence_evidence(evidence, candidate)
    payload, signature = _validate_signature_shape(
        candidate["proof_of_key_possession"],
        appointment_signing_payload(candidate),
        POSSESSION_NAMESPACE,
        "proof of key possession",
    )
    verify_sshsig(
        candidate["reviewer"]["ssh_public_key"],
        candidate["reviewer"]["reviewer_identity"],
        signature,
        payload,
        POSSESSION_NAMESPACE,
    )
    return evidence


def validate_candidate(candidate, evidence_bytes):
    """Return informational copies after freshly verifying both SSHSIG proofs."""
    candidate_bytes = canonical_json(candidate, newline=True)
    candidate_copy = read_json_bytes(
        candidate_bytes, "appointment candidate snapshot", canonical=True
    )
    evidence = _validate_candidate_material(candidate_copy, evidence_bytes)
    evidence_copy = read_json_bytes(
        canonical_json(evidence, newline=True),
        "independence evidence snapshot",
        canonical=True,
    )
    return candidate_copy, evidence_copy


def load_and_validate_candidate(candidate_path):
    candidate_bytes, candidate_root = read_external_file(
        candidate_path, "appointment candidate", MAX_CANDIDATE_BYTES
    )
    candidate = read_json_bytes(
        candidate_bytes, "appointment candidate", canonical=True
    )
    validate_appointment_structure(candidate)
    evidence_bytes = read_secure_relative(
        candidate_root,
        candidate["independence_evidence"]["path"],
        "independence evidence",
        MAX_EVIDENCE_BYTES,
    )
    return validate_candidate(candidate, evidence_bytes)


def _validate_lookup_query(reviewer_identity, ssh_fingerprint, packet_id, at_time):
    reviewer_identity = require_identity(reviewer_identity, "reviewer identity lookup")
    ssh_fingerprint = require_ssh_fingerprint(
        ssh_fingerprint, "reviewer fingerprint lookup"
    )
    packet_id = require_packet_id(packet_id, "packet lookup")
    parse_utc_timestamp(at_time, "appointment lookup time")
    return reviewer_identity, ssh_fingerprint, packet_id, at_time


def _appointment_matches(record, reviewer_identity, ssh_fingerprint, packet_id, at_time):
    reviewer = record["reviewer"]
    scope = record["scope"]
    validity = record["validity"]
    return (
        reviewer["reviewer_identity"] == reviewer_identity
        and reviewer["ssh_fingerprint"] == ssh_fingerprint
        and scope["packet_min"] <= packet_id <= scope["packet_max"]
        and validity["valid_from"] <= at_time <= validity["valid_through"]
    )


def preview_candidate_activity(
    candidate,
    evidence_bytes,
    reviewer_identity,
    ssh_fingerprint,
    packet_id,
    at_time,
):
    """Freshly lint raw candidate material for a non-authorizing activity preview."""
    record, _evidence = validate_candidate(candidate, evidence_bytes)
    reviewer_identity, ssh_fingerprint, packet_id, at_time = _validate_lookup_query(
        reviewer_identity, ssh_fingerprint, packet_id, at_time
    )
    if record["status"] == "revoked":
        return False
    if record["status"] != "active":
        raise ReviewerRegistryError("candidate status is invalid")
    return _appointment_matches(
        record, reviewer_identity, ssh_fingerprint, packet_id, at_time
    )


def validate_embedded_production_record(record):
    """Revalidate a future embedded record; this alone grants no authority."""
    exact_keys(
        record,
        {"appointment", "independence_evidence"},
        "embedded production appointment record",
    )
    evidence_bytes = canonical_json(record["independence_evidence"], newline=True)
    return validate_candidate(record["appointment"], evidence_bytes)


def find_active_appointment(
    repo, reviewer_identity, ssh_fingerprint, packet_id, at_time
):
    """Authorize solely from a fresh read of the exact frozen production bytes."""
    authority, _campaign = check_repository(repo)
    reviewer_identity, ssh_fingerprint, packet_id, at_time = _validate_lookup_query(
        reviewer_identity, ssh_fingerprint, packet_id, at_time
    )
    matches = []
    appointment_ids = set()
    for record in authority["appointments"]:
        appointment, evidence = validate_embedded_production_record(record)
        appointment_id = appointment["appointment_id"]
        if appointment_id in appointment_ids:
            raise ReviewerRegistryError(
                "production registry repeats an appointment identity"
            )
        appointment_ids.add(appointment_id)
        if appointment["status"] == "revoked":
            continue
        if appointment["status"] != "active":
            raise ReviewerRegistryError("production appointment status is invalid")
        if _appointment_matches(
            appointment, reviewer_identity, ssh_fingerprint, packet_id, at_time
        ):
            matches.append(
                {
                    "appointment": appointment,
                    "independence_evidence": evidence,
                }
            )
    if len(matches) > 1:
        raise ReviewerRegistryError("multiple active appointments match")
    return matches[0] if matches else None


def check_repository(repo):
    repo = validate_root_directory(repo, "repository")
    authority_bytes = read_secure_relative(
        repo, AUTHORITY_PATH.as_posix(), "reviewer registry authority", MAX_AUTHORITY_BYTES
    )
    if len(authority_bytes) != AUTHORITY_SIZE:
        raise ReviewerRegistryError("reviewer registry authority size differs")
    if hashlib.sha256(authority_bytes).hexdigest() != AUTHORITY_SHA256:
        raise ReviewerRegistryError("reviewer registry authority digest differs")
    authority = read_json_bytes(
        authority_bytes, "reviewer registry authority", canonical=True
    )
    validate_authority(authority)
    binding = authority["campaign_binding"]["campaign_authority"]
    campaign_bytes = read_secure_relative(
        repo, binding["path"], "campaign authority", MAX_CAMPAIGN_BYTES
    )
    if len(campaign_bytes) != binding["size"]:
        raise ReviewerRegistryError("campaign authority size differs")
    if hashlib.sha256(campaign_bytes).hexdigest() != binding["sha256"]:
        raise ReviewerRegistryError("campaign authority digest differs")
    campaign = read_json_bytes(campaign_bytes, "campaign authority", canonical=True)
    validate_campaign(campaign)
    return authority, campaign


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Validate the non-crediting RK-001 reviewer registry"
    )
    parser.add_argument("--repo", default=str(REPO_ROOT), help="repository root")
    actions = parser.add_mutually_exclusive_group(required=True)
    actions.add_argument("--check", action="store_true", help="validate production authority")
    actions.add_argument(
        "--candidate-lint",
        metavar="PATH",
        help="lint one external candidate without registering it",
    )
    arguments = parser.parse_args(argv)
    try:
        authority, campaign = check_repository(arguments.repo)
        if arguments.candidate_lint:
            candidate, evidence = load_and_validate_candidate(
                arguments.candidate_lint
            )
            print(
                "RK-001 REVIEWER CANDIDATE VALID (NOT REGISTERED): "
                "appointment={0} evidence={1} packets={2}-{3}".format(
                    candidate["appointment_id"],
                    evidence["evidence_id"],
                    candidate["scope"]["packet_min"],
                    candidate["scope"]["packet_max"],
                )
            )
        else:
            print(
                "RK-001 REVIEWER REGISTRY PASS: campaign={0} packets={1} "
                "appointments=0 registration=required-missing gate=TODO credit=0".format(
                    campaign["campaign_id"], len(campaign["packets"])
                )
            )
        if authority["claims"]["tracker_credit"]:
            raise ReviewerRegistryError("unreachable tracker-credit claim")
        return 0
    except ReviewerRegistryError as error:
        print("RK-001 REVIEWER REGISTRY FAIL: {0}".format(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
