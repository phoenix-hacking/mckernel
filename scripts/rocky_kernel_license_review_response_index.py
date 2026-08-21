#!/usr/bin/env python3
"""Build and verify a non-crediting RK-001 aggregate response index.

The index is a deterministic census of exactly the 219 frozen campaign
packets.  Every production entry is reconstructed from one descriptor-rooted
response-package snapshot and accepted by the exact frozen response-v1
verifier, including its reviewer-registration and SSHSIG checks.  Even a
structurally complete index is not campaign closure: successor-v2 archive
inventories and immutable durable authority remain missing, and every gate,
tracker, and credit claim stays false.
"""

from __future__ import print_function

import argparse
import ctypes
import datetime
import hashlib
import hmac
import json
import os
import re
import stat
import sys
import types
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
AUTHORITY_PATH = Path(
    "host-kernel/rocky/evidence/"
    "rk001-license-review-response-index-contract-ef58-v1.json"
)
AUTHORITY_SHA256 = "202c5038d73c5d58ab06dbc6babdd9e3710d3250d77dc714cce043b46bfa82cc"

SCHEMA_VERSION = 1
CONTRACT_ID = "rk-001-license-review-response-index-ef58860e-v1"
RESPONSE_CONTRACT_ID = "rk-001-license-review-response-ef58860e-v1"
CAMPAIGN_ID = "rk-001-license-review-campaign-ef58860e-v1"
SOURCE_COMMIT = "ef58860e4806ee16e2c506e4e93c7b6ad8ad8f4b"
PACKET_COUNT = 219
REVIEW_UNIT_COUNT = 115265
CONTENT_GROUP_COUNT = 111004

MAX_AUTHORITY_BYTES = 2 * 1024 * 1024
MAX_INDEX_BYTES = 4 * 1024 * 1024
MAX_JSON_NESTING = 64
MAX_JSON_NUMBER_TOKEN = 128
MAX_STRING_BYTES = 4096

HEX_SHA256 = re.compile(r"^[0-9a-f]{64}$")
PACKET_ID_PATTERN = re.compile(r"^[0-9]{4}$")
SIGNED_ROOT_PATTERN = re.compile(r"^rk001-response-root:[0-9a-f]{64}$")
IDENTITY_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._@+-]{0,127}$")
AUTHORITY_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._:-]{0,127}$")
FINGERPRINT_PATTERN = re.compile(r"^SHA256:[A-Za-z0-9+/]{43}$")
RFC3339_UTC = re.compile(
    r"^[0-9]{4}-(0[1-9]|1[0-2])-([0-2][0-9]|3[01])T"
    r"([01][0-9]|2[0-3]):[0-5][0-9]:[0-5][0-9]Z$"
)

EXPECTED_PACKET_IDS = tuple("{0:04d}".format(value) for value in range(1, 220))
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
EXPECTED_INPUTS = {
    "campaign_authority",
    "campaign_checker",
    "campaign_tests",
    "campaign_workflow",
    "response_authority",
    "response_checker",
    "response_tests",
    "response_workflow",
}
EXPECTED_INPUT_DESCRIPTORS = {
    "campaign_authority": {
        "path": "host-kernel/rocky/evidence/rk001-license-review-campaign-ef58-v1.json",
        "sha256": "b5581cb9ad5707af65968a6e01ea69a7c46ebbe2542412c1a4cec0611da77852",
        "size": 168050,
    },
    "campaign_checker": {
        "path": "scripts/rocky_kernel_license_review_campaign.py",
        "sha256": "f5117c8af8fbf65f159cb06a69379b88f342bacccfb2aad2c5a44fe9559e3a63",
        "size": 81188,
    },
    "campaign_tests": {
        "path": "scripts/tests/test_rocky_kernel_license_review_campaign.py",
        "sha256": "9ea1b4254987141b6b78bcff4539c423ca913a328a401af511b293ba412666b5",
        "size": 45546,
    },
    "campaign_workflow": {
        "path": ".github/workflows/rk001-license-review-campaign-v1.yml",
        "sha256": "95dde8bed1697c792a05f5768ea7dd7ac32d3538f2bf41ce35b8a10d858fa370",
        "size": 24447,
    },
    "response_authority": {
        "path": "host-kernel/rocky/evidence/rk001-license-review-response-contract-ef58-v1.json",
        "sha256": "c71bbb5432d61106f7c86ec0f05a76e804586c57d2ad189b94e4b010bb4deaec",
        "size": 8381,
    },
    "response_checker": {
        "path": "scripts/rocky_kernel_license_review_response.py",
        "sha256": "ae27f84572bf74ef1d2ec22efd99e5aac6d117d4ef5b1fb8d7f38da823200b5c",
        "size": 93401,
    },
    "response_tests": {
        "path": "scripts/tests/test_rocky_kernel_license_review_response.py",
        "sha256": "115a623db997de726efc00e5163ead6136f2b51baf14ebf5286b41ef13c68d28",
        "size": 38087,
    },
    "response_workflow": {
        "path": ".github/workflows/rk001-license-review-response-v1.yml",
        "sha256": "1a3116d1a512bfc34e252ee83785aa0d06b6e493febf7303ea47c4a27592b791",
        "size": 15388,
    },
}
# Historical response-index inputs stay exact.  Current verifier/test bytes
# are an independently pinned compatibility layer and do not modify the
# response census, the ef58860e artifact facts, or any false claim.
CURRENT_IMPLEMENTATION_OVERRIDES = {
    EXPECTED_INPUT_DESCRIPTORS["campaign_checker"]["path"]: {
        "path": EXPECTED_INPUT_DESCRIPTORS["campaign_checker"]["path"],
        "sha256": "02305bcecf42e3b3919535c2104977a1a6e75fece7e5333a916a8ec4c2091f30",
        "size": 82394,
    },
    EXPECTED_INPUT_DESCRIPTORS["campaign_tests"]["path"]: {
        "path": EXPECTED_INPUT_DESCRIPTORS["campaign_tests"]["path"],
        "sha256": "1960901c58a33bb39d791db4ddd406ac42c5a62c8eef2879b960c38832bdc192",
        "size": 46015,
    },
    EXPECTED_INPUT_DESCRIPTORS["response_checker"]["path"]: {
        "path": EXPECTED_INPUT_DESCRIPTORS["response_checker"]["path"],
        "sha256": "c86eb2dbd8e8b1afcc7556d26c1d37eda886ed6660ae940e42d3b1c5e16279de",
        "size": 95089,
    },
}
EXPECTED_BLOCKERS = [
    "No production reviewer identity, independence appointment, or SSH public key is registered in the frozen response-v1 authority.",
    "No external signed reviewer response exists for any of the 219 campaign packets.",
    "Packet 0218 cannot close the stablelists archive until a successor v2 child inventory is frozen and reviewed.",
    "Packet 0218 cannot close the kabi-dw archive until a successor v2 child inventory is frozen and reviewed.",
    "No immutable durable response archive authority or object version is registered.",
    "A structurally complete 219-entry index is only a deterministic response census; it does not establish legal, provenance, redistribution, archive, gate, tracker, or credit completion.",
    "This checker cannot modify the source lock or tracker and cannot award RK-001 credit.",
]
EXPECTED_COVERAGE_POLICY = {
    "all_packet_responses_is_structural_only": True,
    "content_group_count": CONTENT_GROUP_COUNT,
    "packet_count": PACKET_COUNT,
    "packet_id_max": "0219",
    "packet_id_min": "0001",
    "packet_id_order": "four-digit-ascending-contiguous",
    "packet_unit_count_stream_sha256":
        "3f50a8e9cad00d8d7d8b88bdebea332e3051fbd086bf56e30720ac6fed17d365",
    "packet_unit_count_stream_size": 8321,
    "review_unit_count": REVIEW_UNIT_COUNT,
    "serialized_index_claims_live_verification": False,
    "structural_entry_census_is_live_verification": False,
    "zero_unresolved_does_not_establish_campaign_completion": True,
}
EXPECTED_ARCHIVE_POLICY = {
    "kabi_dw_successor_v2_inventory_status": "required-missing",
    "packet_0218_existing_inventory_may_be_structurally_attested": True,
    "packet_0218_successor_v2_archive_blockers_required": True,
    "raw_container_counts_as_reviewed": False,
    "stablelists_successor_v2_inventory_status": "required-missing",
}
EXPECTED_DURABILITY_POLICY = {
    "actions_artifact_is_durable": False,
    "credit_before_durable_registration": False,
    "durable_authority_registration_status": "required-missing",
    "immutable_object_version_required": True,
    "index_file_is_durable_archive": False,
    "outer_archive_digest_required": True,
}
EXPECTED_IDENTITY_POLICY = {
    "authority_identity_key_tuple": [
        "reviewer_authority_id",
        "reviewer_identity",
        "reviewer_key_fingerprint",
    ],
    "duplicate_signed_response_root_forbidden": True,
    "every_response_requires_existing_verifier_registration": True,
    "mixed_registered_reviewers_allowed": True,
    "self_asserted_identity_forbidden": True,
}
EXPECTED_TIME_POLICY = {
    "aggregate_time_bounds_are_derived": True,
    "clock_time_is_not_inserted_by_builder": True,
    "completion_time_must_pass_existing_reviewer_validity_check": True,
    "format": "rfc3339-utc-whole-seconds",
    "packet_completion_times_need_not_be_monotonic": True,
}
EXPECTED_SCOPE = {
    "aggregate_index_supported": True,
    "campaign_closure_can_be_established": False,
    "mode": "complete-structural-response-index-only",
    "required_campaign_packet_count": PACKET_COUNT,
}
EXPECTED_INDEX_FORMAT = {
    "atomic_publication": "linux-renameat2-noreplace-retained-fd-v1",
    "canonical_json": "canonical-ascii-json-newline-v1",
    "entry_order": "packet-id-ascending",
    "entry_stream_algorithm": "sha256-canonical-index-entry-jsonl-v1",
    "index_member": "rk001-license-review-response-index.json",
    "maximum_index_bytes": MAX_INDEX_BYTES,
    "published_mode": "0444",
    "package_digest_algorithm":
        "sha256-canonical-member-path-size-digest-jsonl-v1",
    "path_layout": {
        "packet_directory": "PACKETS_ROOT/NNNN",
        "response_directory": "RESPONSES_ROOT/NNNN",
    },
    "response_directory_closure": "exact-packet-ids-0001-through-0219",
    "schema_version": SCHEMA_VERSION,
    "signature_verification": "existing-frozen-response-v1-verifier-required",
    "snapshot_policy":
        "descriptor-rooted-package-snapshot-before-index-retention",
}

ENTRY_KEYS = {
    "archive_expansion_complete",
    "durable_archive",
    "packet_id",
    "response_package_sha256",
    "review_completed_at",
    "reviewed_unit_count",
    "reviewer_authority_id",
    "reviewer_identity",
    "reviewer_key_fingerprint",
    "reviewer_registered",
    "signature_valid",
    "signed_response_root",
    "unresolved_unit_count",
}
REVIEWER_KEYS = {
    "first_packet_id",
    "last_packet_id",
    "packet_count",
    "reviewer_authority_id",
    "reviewer_identity",
    "reviewer_key_fingerprint",
}
INDEX_KEYS = {
    "all_packet_responses_verified",
    "campaign_authority_sha256",
    "campaign_id",
    "claims",
    "durability_registration_status",
    "entries",
    "entry_stream_sha256",
    "entry_stream_size",
    "gate",
    "latest_review_completed_at",
    "earliest_review_completed_at",
    "packet_count",
    "response_authority_sha256",
    "response_index_contract_id",
    "reviewed_unit_count",
    "reviewer_count",
    "reviewer_set_sha256",
    "reviewer_set_size",
    "reviewers",
    "schema_version",
    "source_commit",
    "structural_response_coverage_complete",
    "successor_v2_archive_blockers_present",
    "unresolved_unit_count",
}


class ResponseIndexError(RuntimeError):
    """Raised when an index authority, package census, or index fails closed."""


def _new_live_verification_boundary():
    """Create a closure-held issuer with no module-visible mint or token."""
    secret = os.urandom(32)

    class SealedLiveVerifiedPacket(object):
        __slots__ = ("__entry_bytes", "__seal")

        def __new__(cls, *_arguments, **_keywords):
            raise ResponseIndexError("live packet construction is private")

        def __init_subclass__(cls, **_keywords):
            raise TypeError("live verified packets cannot be subclassed")

        def __setattr__(self, _name, _value):
            raise ResponseIndexError("live verified packets are immutable")

    def seal_bytes(payload):
        return hmac.new(
            secret,
            b"rk001-live-verified-packet-v1\x00" + payload,
            hashlib.sha256,
        ).digest()

    def mint(entry):
        payload = canonical_json(entry, newline=True)
        packet = object.__new__(SealedLiveVerifiedPacket)
        object.__setattr__(
            packet,
            "_SealedLiveVerifiedPacket__entry_bytes",
            payload,
        )
        object.__setattr__(
            packet,
            "_SealedLiveVerifiedPacket__seal",
            seal_bytes(payload),
        )
        return packet

    def decode(packet):
        if type(packet) is not SealedLiveVerifiedPacket:
            raise ResponseIndexError("live packet provenance is missing")
        try:
            payload = object.__getattribute__(
                packet, "_SealedLiveVerifiedPacket__entry_bytes"
            )
            actual_seal = object.__getattribute__(
                packet, "_SealedLiveVerifiedPacket__seal"
            )
        except (AttributeError, TypeError) as error:
            raise ResponseIndexError(
                "live packet provenance is malformed: {0}".format(error)
            )
        if type(payload) is not bytes or type(actual_seal) is not bytes:
            raise ResponseIndexError("live packet provenance types changed")
        expected_seal = seal_bytes(payload)
        if not hmac.compare_digest(actual_seal, expected_seal):
            raise ResponseIndexError("live packet provenance seal differs")
        return read_json_bytes(payload, "live verified packet", canonical=True)

    def bind(load_implementation, verify_implementation):
        trusted_stacks = []

        def load(repo, authority):
            stack = load_implementation(repo, authority)
            response, response_authority, campaign, campaign_authority = stack
            trusted_stacks.append(
                (
                    response,
                    response_authority,
                    campaign,
                    campaign_authority,
                    response.parse_jsonl,
                    response.read_response_package,
                    response.verify_response_data,
                    response.read_json_bytes,
                    campaign.verify_package,
                    campaign.packet_metadata_files,
                )
            )
            return stack

        def verify(
            response,
            response_authority,
            campaign,
            campaign_authority,
            derived_campaign,
            packet_id,
            packet_directory,
            response_directory,
        ):
            trusted = None
            for candidate in trusted_stacks:
                if (
                    candidate[0] is response
                    and candidate[1] is response_authority
                    and candidate[2] is campaign
                    and candidate[3] is campaign_authority
                ):
                    trusted = candidate
                    break
            if trusted is None:
                raise ResponseIndexError(
                    "packet verification did not use a frozen loaded stack"
                )
            current_functions = (
                response.parse_jsonl,
                response.read_response_package,
                response.verify_response_data,
                response.read_json_bytes,
                campaign.verify_package,
                campaign.packet_metadata_files,
            )
            for current, retained in zip(current_functions, trusted[4:]):
                if current is not retained:
                    raise ResponseIndexError(
                        "frozen packet verifier function identity changed"
                    )
            for value, key, label in (
                (response_authority, "response_authority", "response authority"),
                (campaign_authority, "campaign_authority", "campaign authority"),
            ):
                payload = canonical_json(value, newline=True)
                bound = EXPECTED_INPUT_DESCRIPTORS[key]
                require_exact(len(payload), bound["size"], label + " size")
                require_exact(
                    hashlib.sha256(payload).hexdigest(),
                    bound["sha256"],
                    label + " digest",
                )
            entry = verify_implementation(
                response,
                response_authority,
                campaign,
                campaign_authority,
                derived_campaign,
                packet_id,
                packet_directory,
                response_directory,
            )
            return mint(entry)

        return load, verify, decode

    return SealedLiveVerifiedPacket, bind


LiveVerifiedPacket, _bind_live_verification_boundary = (
    _new_live_verification_boundary()
)
del _new_live_verification_boundary


def reject_duplicate_pairs(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ResponseIndexError("duplicate JSON key: {0}".format(key))
        value[key] = item
    return value


def parse_bounded_json_int(token):
    if type(token) is not str or len(token) > MAX_JSON_NUMBER_TOKEN:
        raise ResponseIndexError("JSON integer token exceeds its cap")
    try:
        return int(token, 10)
    except ValueError as error:
        raise ResponseIndexError("JSON integer token is invalid: {0}".format(error))


def reject_json_float(token):
    if type(token) is not str or len(token) > MAX_JSON_NUMBER_TOKEN:
        raise ResponseIndexError("JSON float token exceeds its cap")
    raise ResponseIndexError("JSON floating-point values are forbidden")


def reject_json_constant(token):
    raise ResponseIndexError("nonfinite JSON value is forbidden: {0}".format(token))


def require_bounded_json_nesting(value):
    stack = [(value, 0)]
    while stack:
        current, depth = stack.pop()
        if depth > MAX_JSON_NESTING:
            raise ResponseIndexError("JSON nesting exceeds its cap")
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
        raise ResponseIndexError("value is not canonical JSON: {0}".format(error))
    return data + (b"\n" if newline else b"")


def canonical_stream(records):
    return b"".join(canonical_json(record, newline=True) for record in records)


def read_json_bytes(data, label, canonical=False):
    if len(data) > MAX_INDEX_BYTES:
        raise ResponseIndexError("{0} exceeds its byte cap".format(label))
    try:
        value = json.loads(
            data.decode("ascii"),
            object_pairs_hook=reject_duplicate_pairs,
            parse_constant=reject_json_constant,
            parse_float=reject_json_float,
            parse_int=parse_bounded_json_int,
        )
    except ResponseIndexError:
        raise
    except (RecursionError, UnicodeError, ValueError) as error:
        raise ResponseIndexError("{0} is not valid JSON: {1}".format(label, error))
    require_bounded_json_nesting(value)
    if type(value) is not dict:
        raise ResponseIndexError("{0} must be a JSON object".format(label))
    if canonical and data != canonical_json(value, newline=True):
        raise ResponseIndexError("{0} is not canonical JSON".format(label))
    return value


def exact_keys(value, keys, label):
    if type(value) is not dict or set(value) != set(keys):
        raise ResponseIndexError("{0} fields changed".format(label))
    return value


def require_exact(actual, expected, label):
    if type(actual) is not type(expected):
        raise ResponseIndexError("{0} type changed".format(label))
    if isinstance(expected, dict):
        if set(actual) != set(expected):
            raise ResponseIndexError("{0} fields changed".format(label))
        for key in expected:
            require_exact(actual[key], expected[key], label + "." + str(key))
        return
    if isinstance(expected, list):
        if len(actual) != len(expected):
            raise ResponseIndexError("{0} length changed".format(label))
        for index, pair in enumerate(zip(actual, expected)):
            require_exact(pair[0], pair[1], label + "[{0}]".format(index))
        return
    if actual != expected:
        raise ResponseIndexError(
            "{0} differs: {1!r} != {2!r}".format(label, actual, expected)
        )


def require_bool(value, label):
    if type(value) is not bool:
        raise ResponseIndexError("{0} is not a boolean".format(label))
    return value


def require_nonnegative_int(value, label):
    if type(value) is not int or value < 0:
        raise ResponseIndexError("{0} is not a nonnegative integer".format(label))
    return value


def require_string(value, label, maximum=MAX_STRING_BYTES):
    if type(value) is not str or not value or len(value) > maximum:
        raise ResponseIndexError("{0} is not a bounded string".format(label))
    return value


def require_sha256(value, label):
    if type(value) is not str or not HEX_SHA256.fullmatch(value):
        raise ResponseIndexError("{0} is not a lowercase SHA-256".format(label))
    return value


def require_utc_timestamp(value, label):
    value = require_string(value, label, 20)
    if not RFC3339_UTC.fullmatch(value):
        raise ResponseIndexError("{0} is not an RFC3339 UTC timestamp".format(label))
    try:
        datetime.datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError as error:
        raise ResponseIndexError("{0} is not a real timestamp: {1}".format(label, error))
    return value


def safe_relative(value, label):
    value = require_string(value, label, 512)
    path = Path(value)
    if (
        path.is_absolute()
        or "\\" in value
        or "\x00" in value
        or any(part in ("", ".", "..") for part in path.parts)
    ):
        raise ResponseIndexError("{0} is unsafe".format(label))
    return path


def _file_identity(info):
    return (
        info.st_dev,
        info.st_ino,
        info.st_mode,
        info.st_nlink,
        info.st_uid,
        info.st_gid,
        info.st_size,
        info.st_mtime_ns,
        info.st_ctime_ns,
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
        info.st_mtime_ns,
        info.st_ctime_ns,
    )


def _read_regular(path, cap, label):
    raw = str(path)
    if not raw or "\x00" in raw or "\\" in raw:
        raise ResponseIndexError("{0} path is unsafe".format(label))
    requested = Path(os.path.abspath(raw))
    if requested.anchor != os.sep or not requested.name:
        raise ResponseIndexError("{0} path is unsafe".format(label))
    directory_flags = (
        os.O_RDONLY
        | getattr(os, "O_DIRECTORY", 0)
        | getattr(os, "O_NOFOLLOW", 0)
        | getattr(os, "O_CLOEXEC", 0)
    )
    file_flags = (
        os.O_RDONLY
        | getattr(os, "O_NONBLOCK", 0)
        | getattr(os, "O_NOFOLLOW", 0)
        | getattr(os, "O_CLOEXEC", 0)
    )
    chain = []
    descriptor = None
    try:
        current = os.open(requested.anchor, directory_flags)
        root_info = os.fstat(current)
        if not stat.S_ISDIR(root_info.st_mode):
            raise ResponseIndexError("{0} filesystem root is not a directory".format(label))
        chain.append(
            {
                "descriptor": current,
                "identity": _directory_identity(root_info),
                "name": None,
                "parent_fd": None,
            }
        )
        for component in requested.parts[1:-1]:
            if component in ("", ".", "..") or os.sep in component:
                raise ResponseIndexError("{0} path component is unsafe".format(label))
            following = None
            try:
                following = os.open(component, directory_flags, dir_fd=current)
                opened = os.fstat(following)
                namespace = os.stat(
                    component, dir_fd=current, follow_symlinks=False
                )
                if (
                    not stat.S_ISDIR(opened.st_mode)
                    or _directory_identity(opened) != _directory_identity(namespace)
                ):
                    raise ResponseIndexError(
                        "{0} path component identity differs".format(label)
                    )
            except Exception:
                if following is not None:
                    try:
                        os.close(following)
                    except OSError:
                        pass
                raise
            chain.append(
                {
                    "descriptor": following,
                    "identity": _directory_identity(opened),
                    "name": component,
                    "parent_fd": current,
                }
            )
            current = following
        descriptor = os.open(requested.name, file_flags, dir_fd=current)
        before = os.fstat(descriptor)
        namespace = os.stat(requested.name, dir_fd=current, follow_symlinks=False)
        if (
            not stat.S_ISREG(before.st_mode)
            or before.st_nlink != 1
            or _file_identity(before) != _file_identity(namespace)
        ):
            raise ResponseIndexError("{0} is not one immutable regular file".format(label))
        if before.st_size > cap:
            raise ResponseIndexError("{0} exceeds its byte cap".format(label))
        chunks = []
        retained = 0
        while True:
            block = os.read(descriptor, min(1024 * 1024, cap + 1 - retained))
            if not block:
                break
            retained += len(block)
            if retained > cap:
                raise ResponseIndexError("{0} exceeds its byte cap".format(label))
            chunks.append(block)
        after = os.fstat(descriptor)
        namespace_after = os.stat(
            requested.name, dir_fd=current, follow_symlinks=False
        )
        if (
            _file_identity(before) != _file_identity(after)
            or _file_identity(before) != _file_identity(namespace_after)
            or retained != before.st_size
        ):
            raise ResponseIndexError("{0} changed while being read".format(label))
        for record in chain:
            opened = os.fstat(record["descriptor"])
            current_namespace = (
                opened
                if record["parent_fd"] is None
                else os.stat(
                    record["name"],
                    dir_fd=record["parent_fd"],
                    follow_symlinks=False,
                )
            )
            if (
                _directory_identity(opened) != record["identity"]
                or _directory_identity(current_namespace) != record["identity"]
            ):
                raise ResponseIndexError("{0} path changed while being read".format(label))
        return b"".join(chunks)
    except OSError as error:
        raise ResponseIndexError("cannot read {0}: {1}".format(label, error))
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


def _validate_bound(record, label):
    exact_keys(record, {"path", "sha256", "size"}, label)
    safe_relative(record["path"], label + " path")
    require_sha256(record["sha256"], label + " digest")
    require_nonnegative_int(record["size"], label + " size")


def validate_authority(authority):
    exact_keys(
        authority,
        {
            "archive_policy",
            "claims",
            "coverage_policy",
            "durability_policy",
            "gate",
            "identity_policy",
            "index_format",
            "inputs",
            "remaining_blockers",
            "response_index_contract_id",
            "schema_version",
            "source_commit",
            "time_policy",
            "verification_scope",
        },
        "response-index authority",
    )
    require_exact(authority["schema_version"], SCHEMA_VERSION, "schema version")
    require_exact(authority["response_index_contract_id"], CONTRACT_ID, "contract ID")
    require_exact(authority["source_commit"], SOURCE_COMMIT, "source commit")
    require_exact(authority["claims"], EXPECTED_CLAIMS, "authority claims")
    require_exact(authority["gate"], EXPECTED_GATE, "authority gate")
    require_exact(authority["coverage_policy"], EXPECTED_COVERAGE_POLICY, "coverage policy")
    require_exact(authority["archive_policy"], EXPECTED_ARCHIVE_POLICY, "archive policy")
    require_exact(authority["durability_policy"], EXPECTED_DURABILITY_POLICY, "durability policy")
    require_exact(authority["identity_policy"], EXPECTED_IDENTITY_POLICY, "identity policy")
    require_exact(authority["time_policy"], EXPECTED_TIME_POLICY, "time policy")
    require_exact(authority["verification_scope"], EXPECTED_SCOPE, "verification scope")
    require_exact(authority["index_format"], EXPECTED_INDEX_FORMAT, "index format")
    inputs = exact_keys(authority["inputs"], EXPECTED_INPUTS, "authority inputs")
    require_exact(inputs, EXPECTED_INPUT_DESCRIPTORS, "authority input descriptors")
    for key, record in inputs.items():
        _validate_bound(record, "input " + key)
    require_exact(
        authority["remaining_blockers"], EXPECTED_BLOCKERS, "remaining blockers"
    )
    return authority


def load_authority(repo=REPO_ROOT, explicit=None):
    repo = Path(repo).resolve()
    path = Path(explicit) if explicit is not None else repo / AUTHORITY_PATH
    data = _read_regular(path, MAX_AUTHORITY_BYTES, "response-index authority")
    require_exact(hashlib.sha256(data).hexdigest(), AUTHORITY_SHA256, "authority digest")
    authority = read_json_bytes(data, "response-index authority")
    validate_authority(authority)
    return authority


def _read_bound(repo, record, label, cap=MAX_AUTHORITY_BYTES):
    _validate_bound(record, label)
    active_record = CURRENT_IMPLEMENTATION_OVERRIDES.get(record["path"], record)
    require_exact(active_record["path"], record["path"], label + " compatibility path")
    path = Path(repo).resolve() / safe_relative(
        active_record["path"], label + " path"
    )
    data = _read_regular(path, cap, label)
    require_exact(len(data), active_record["size"], label + " size")
    require_exact(
        hashlib.sha256(data).hexdigest(),
        active_record["sha256"],
        label + " digest",
    )
    return path, data


def _load_frozen_stack_implementation(repo, authority):
    """Load the exact response/campaign v1 verifier stack bound by authority."""
    repo = Path(repo).resolve()
    validate_authority(authority)
    bound = {}
    for key, record in authority["inputs"].items():
        bound[key] = _read_bound(repo, record, "frozen " + key.replace("_", " "))
    response_path, response_data = bound["response_checker"]
    response = types.ModuleType("_rk001_frozen_review_response_for_index")
    response.__file__ = str(response_path)
    response.__package__ = None
    try:
        code = compile(response_data, str(response_path), "exec", dont_inherit=True)
        exec(code, response.__dict__)
    except (Exception, MemoryError) as error:
        raise ResponseIndexError("cannot execute frozen response checker: {0}".format(error))
    require_exact(
        response.AUTHORITY_SHA256,
        authority["inputs"]["response_authority"]["sha256"],
        "response checker authority digest",
    )
    try:
        response_authority = response.load_authority(
            repo, bound["response_authority"][0]
        )
        campaign, campaign_authority = response.load_campaign_checker(
            repo, response_authority
        )
    except response.ReviewResponseError as error:
        raise ResponseIndexError("frozen response stack rejected: {0}".format(error))
    require_exact(response.CONTRACT_ID, RESPONSE_CONTRACT_ID, "response contract ID")
    require_exact(response.CAMPAIGN_ID, CAMPAIGN_ID, "response campaign ID")
    require_exact(
        hashlib.sha256(bound["campaign_authority"][1]).hexdigest(),
        authority["inputs"]["campaign_authority"]["sha256"],
        "campaign authority digest",
    )
    require_exact(
        hashlib.sha256(bound["campaign_checker"][1]).hexdigest(),
        CURRENT_IMPLEMENTATION_OVERRIDES.get(
            authority["inputs"]["campaign_checker"]["path"],
            authority["inputs"]["campaign_checker"],
        )["sha256"],
        "campaign checker digest",
    )
    validate_campaign(authority, campaign_authority)
    return response, response_authority, campaign, campaign_authority


def packet_unit_records(campaign_authority):
    packets = campaign_authority.get("packets")
    if type(packets) is not list or len(packets) != PACKET_COUNT:
        raise ResponseIndexError("campaign packet table is incomplete")
    records = []
    for expected_id, packet in zip(EXPECTED_PACKET_IDS, packets):
        if type(packet) is not dict:
            raise ResponseIndexError("campaign packet is not an object")
        require_exact(packet.get("packet_id"), expected_id, "campaign packet ID")
        unit_count = require_nonnegative_int(
            packet.get("unit_count"), "campaign packet unit count"
        )
        records.append({"packet_id": expected_id, "unit_count": unit_count})
    return records


def validate_campaign(authority, campaign_authority):
    validate_authority(authority)
    campaign_bytes = canonical_json(campaign_authority, newline=True)
    campaign_bound = authority["inputs"]["campaign_authority"]
    require_exact(
        len(campaign_bytes), campaign_bound["size"], "campaign authority size"
    )
    require_exact(
        hashlib.sha256(campaign_bytes).hexdigest(),
        campaign_bound["sha256"],
        "campaign authority digest",
    )
    records = packet_unit_records(campaign_authority)
    stream = canonical_stream(records)
    coverage = authority["coverage_policy"]
    require_exact(len(stream), coverage["packet_unit_count_stream_size"], "packet-unit stream size")
    require_exact(
        hashlib.sha256(stream).hexdigest(),
        coverage["packet_unit_count_stream_sha256"],
        "packet-unit stream digest",
    )
    require_exact(
        sum(record["unit_count"] for record in records),
        REVIEW_UNIT_COUNT,
        "campaign review-unit total",
    )
    expected = campaign_authority.get("expected_result")
    if type(expected) is not dict:
        raise ResponseIndexError("campaign expected result is absent")
    for key, value in (
        ("packet_count", PACKET_COUNT),
        ("review_unit_count", REVIEW_UNIT_COUNT),
        ("content_group_count", CONTENT_GROUP_COUNT),
    ):
        require_exact(expected.get(key), value, "campaign expected " + key)
    return records


def response_package_digest(files):
    if type(files) is not dict or not files:
        raise ResponseIndexError("response package snapshot is empty")
    records = []
    previous = None
    for name in sorted(files):
        if type(name) is not str or not name or name.startswith("/") or "\\" in name:
            raise ResponseIndexError("response member path is unsafe")
        if any(part in ("", ".", "..") for part in name.split("/")):
            raise ResponseIndexError("response member path is unsafe")
        if previous is not None and name <= previous:
            raise ResponseIndexError("response member paths are duplicated or unsorted")
        data = files[name]
        if type(data) is not bytes:
            raise ResponseIndexError("response member snapshot is not bytes")
        records.append(
            {
                "path": name,
                "sha256": hashlib.sha256(data).hexdigest(),
                "size": len(data),
            }
        )
        previous = name
    return hashlib.sha256(canonical_stream(records)).hexdigest()


def _verify_packet_snapshot_implementation(
    response,
    response_authority,
    campaign,
    campaign_authority,
    derived_campaign,
    packet_id,
    packet_directory,
    response_directory,
):
    """Verify one packet and response from one retained package snapshot."""
    if packet_id not in EXPECTED_PACKET_IDS:
        raise ResponseIndexError("packet ID is outside the frozen campaign")
    try:
        campaign.verify_package(
            campaign_authority, derived_campaign, packet_id, packet_directory
        )
        metadata = campaign.packet_metadata_files(
            campaign_authority, derived_campaign, packet_id
        )
        groups = response.parse_jsonl(
            metadata["content-groups.jsonl"],
            "campaign content groups",
            response.MAX_FINDING_RECORDS,
        )
        units = response.parse_jsonl(
            metadata["review-units.jsonl"],
            "campaign review units",
            response.MAX_UNIT_RECORDS,
        )
        files = response.read_response_package(response_directory)
        result = response.verify_response_data(
            response_authority,
            groups,
            units,
            files,
            response_authority["inputs"]["campaign_authority"]["sha256"],
        )
        root = response.read_json_bytes(
            files["response-root.json"], "response root", canonical=True
        )
    except (
        response.ReviewResponseError,
        campaign.ReviewCampaignError,
        KeyError,
    ) as error:
        raise ResponseIndexError(
            "packet {0} response rejected: {1}".format(packet_id, error)
        )
    require_exact(result["packet_id"], packet_id, "verified packet ID")
    entry = {
        "archive_expansion_complete": result["archive_expansion_complete"],
        "durable_archive": result["durable_archive"],
        "packet_id": packet_id,
        "response_package_sha256": response_package_digest(files),
        "review_completed_at": root["review_completed_at"],
        "reviewed_unit_count": result["reviewed_unit_count"],
        "reviewer_authority_id": root["reviewer_authority_id"],
        "reviewer_identity": result["reviewer_identity"],
        "reviewer_key_fingerprint": result["reviewer_key_fingerprint"],
        "reviewer_registered": result["reviewer_registered"],
        "signature_valid": result["signature_valid"],
        "signed_response_root": result["signed_response_root"],
        "unresolved_unit_count": result["unresolved_unit_count"],
    }
    return entry


(
    load_frozen_stack,
    verify_packet_snapshot,
    _decode_live_verified_packet,
) = _bind_live_verification_boundary(
    _load_frozen_stack_implementation,
    _verify_packet_snapshot_implementation,
)
del _bind_live_verification_boundary


def validate_entry(entry, expected_packet_id, expected_unit_count):
    exact_keys(entry, ENTRY_KEYS, "response index entry")
    require_exact(entry["packet_id"], expected_packet_id, "entry packet ID")
    require_exact(
        require_nonnegative_int(entry["reviewed_unit_count"], "entry reviewed units"),
        expected_unit_count,
        "entry reviewed units",
    )
    unresolved = require_nonnegative_int(
        entry["unresolved_unit_count"], "entry unresolved units"
    )
    if unresolved > expected_unit_count:
        raise ResponseIndexError("entry unresolved units exceed reviewed units")
    require_sha256(entry["response_package_sha256"], "entry package digest")
    if not SIGNED_ROOT_PATTERN.fullmatch(
        require_string(entry["signed_response_root"], "entry signed root", 128)
    ):
        raise ResponseIndexError("entry signed root is malformed")
    authority_id = require_string(
        entry["reviewer_authority_id"], "entry reviewer authority", 128
    )
    identity = require_string(entry["reviewer_identity"], "entry reviewer identity", 128)
    fingerprint = require_string(
        entry["reviewer_key_fingerprint"], "entry reviewer fingerprint", 128
    )
    if not AUTHORITY_ID_PATTERN.fullmatch(authority_id):
        raise ResponseIndexError("entry reviewer authority is malformed")
    if not IDENTITY_PATTERN.fullmatch(identity):
        raise ResponseIndexError("entry reviewer identity is malformed")
    if not FINGERPRINT_PATTERN.fullmatch(fingerprint):
        raise ResponseIndexError("entry reviewer fingerprint is malformed")
    require_utc_timestamp(entry["review_completed_at"], "entry completion time")
    require_exact(
        require_bool(entry["signature_valid"], "entry signature status"),
        True,
        "entry signature status",
    )
    require_exact(
        require_bool(entry["reviewer_registered"], "entry reviewer registration"),
        True,
        "entry reviewer registration",
    )
    require_exact(
        require_bool(entry["durable_archive"], "entry durability"),
        False,
        "entry durability",
    )
    require_exact(
        require_bool(entry["archive_expansion_complete"], "entry archive status"),
        False,
        "entry archive status",
    )
    return entry


def reviewer_records(entries):
    groups = {}
    authority_map = {}
    identity_map = {}
    fingerprint_map = {}
    for entry in entries:
        key = (
            entry["reviewer_authority_id"],
            entry["reviewer_identity"],
            entry["reviewer_key_fingerprint"],
        )
        for value, mapping, label in (
            (key[0], authority_map, "reviewer authority"),
            (key[1], identity_map, "reviewer identity"),
            (key[2], fingerprint_map, "reviewer fingerprint"),
        ):
            if value in mapping and mapping[value] != key:
                raise ResponseIndexError("{0} maps to conflicting identities".format(label))
            mapping[value] = key
        groups.setdefault(key, []).append(entry["packet_id"])
    records = []
    for key in sorted(groups):
        packets = groups[key]
        records.append(
            {
                "first_packet_id": min(packets),
                "last_packet_id": max(packets),
                "packet_count": len(packets),
                "reviewer_authority_id": key[0],
                "reviewer_identity": key[1],
                "reviewer_key_fingerprint": key[2],
            }
        )
    return records


def build_index_data(authority, campaign_authority, packet_entries):
    """Build a structural census which deliberately makes no live claim."""
    validate_authority(authority)
    packet_counts = validate_campaign(authority, campaign_authority)
    if type(packet_entries) not in (list, tuple):
        raise ResponseIndexError("packet entries must be an ordered sequence")
    if len(packet_entries) != PACKET_COUNT:
        raise ResponseIndexError("packet entry count differs from the campaign")
    entries = []
    roots = set()
    package_digests = set()
    for expected, candidate in zip(packet_counts, packet_entries):
        if type(candidate) is not dict:
            raise ResponseIndexError("verified packet result is not an object")
        entry = dict(candidate)
        validate_entry(entry, expected["packet_id"], expected["unit_count"])
        if entry["signed_response_root"] in roots:
            raise ResponseIndexError("signed response root is duplicated")
        if entry["response_package_sha256"] in package_digests:
            raise ResponseIndexError("response package digest is duplicated")
        roots.add(entry["signed_response_root"])
        package_digests.add(entry["response_package_sha256"])
        entries.append(entry)
    entry_stream = canonical_stream(entries)
    reviewers = reviewer_records(entries)
    reviewer_stream = canonical_stream(reviewers)
    completed = [entry["review_completed_at"] for entry in entries]
    index = {
        "all_packet_responses_verified": False,
        "campaign_authority_sha256": authority["inputs"]["campaign_authority"]["sha256"],
        "campaign_id": CAMPAIGN_ID,
        "claims": dict(EXPECTED_CLAIMS),
        "durability_registration_status": "required-missing",
        "earliest_review_completed_at": min(completed),
        "entries": entries,
        "entry_stream_sha256": hashlib.sha256(entry_stream).hexdigest(),
        "entry_stream_size": len(entry_stream),
        "gate": dict(EXPECTED_GATE),
        "latest_review_completed_at": max(completed),
        "packet_count": len(entries),
        "response_authority_sha256": authority["inputs"]["response_authority"]["sha256"],
        "response_index_contract_id": CONTRACT_ID,
        "reviewed_unit_count": sum(entry["reviewed_unit_count"] for entry in entries),
        "reviewer_count": len(reviewers),
        "reviewer_set_sha256": hashlib.sha256(reviewer_stream).hexdigest(),
        "reviewer_set_size": len(reviewer_stream),
        "reviewers": reviewers,
        "schema_version": SCHEMA_VERSION,
        "source_commit": SOURCE_COMMIT,
        "structural_response_coverage_complete": False,
        "successor_v2_archive_blockers_present": True,
        "unresolved_unit_count": sum(entry["unresolved_unit_count"] for entry in entries),
    }
    require_exact(index["reviewed_unit_count"], REVIEW_UNIT_COUNT, "index reviewed-unit total")
    return index


def validate_structural_index_data(authority, campaign_authority, index):
    """Validate only serialized structure; never emit a verification claim."""
    validate_authority(authority)
    exact_keys(index, INDEX_KEYS, "response index")
    entries = index.get("entries")
    if type(entries) is not list:
        raise ResponseIndexError("response index entries must be a list")
    rebuilt = build_index_data(authority, campaign_authority, entries)
    require_exact(index, rebuilt, "response index replay")
    return {
        "all_packet_responses_verified": False,
        "campaign_complete": False,
        "credit_eligible": False,
        "durable_archive": False,
        "packet_count": PACKET_COUNT,
        "points_awarded": 0,
        "reviewed_unit_count": REVIEW_UNIT_COUNT,
        "reviewer_count": index["reviewer_count"],
        "structural_response_coverage_complete": False,
        "tracker_credit": False,
        "unresolved_unit_count": index["unresolved_unit_count"],
    }


def _live_packet_entries(verified_packets):
    if type(verified_packets) not in (list, tuple):
        raise ResponseIndexError("live verified packets must be an ordered sequence")
    if len(verified_packets) != PACKET_COUNT:
        raise ResponseIndexError("live verified packet count differs from the campaign")
    entries = []
    for verified in verified_packets:
        if type(verified) is not LiveVerifiedPacket:
            raise ResponseIndexError("live packet provenance is missing")
        entries.append(_decode_live_verified_packet(verified))
    return entries


def _collected_packet_entries(collected_packets):
    entries = []
    for packet in collected_packets:
        if type(packet) is LiveVerifiedPacket:
            entries.append(_decode_live_verified_packet(packet))
        elif type(packet) is dict:
            entries.append(dict(packet))
        else:
            raise ResponseIndexError(
                "packet verifier result is neither sealed nor structural"
            )
    return entries


def verify_index_data(authority, campaign_authority, index, verified_packets=None):
    """Match one structural index to 219 live frozen-verifier results."""
    validate_structural_index_data(authority, campaign_authority, index)
    if verified_packets is None:
        raise ResponseIndexError("live verified packets are required")
    live_entries = _live_packet_entries(verified_packets)
    live = build_index_data(authority, campaign_authority, live_entries)
    require_exact(index, live, "response index/live package binding")
    return {
        "all_packet_responses_verified": True,
        "campaign_complete": False,
        "credit_eligible": False,
        "durable_archive": False,
        "packet_count": PACKET_COUNT,
        "points_awarded": 0,
        "reviewed_unit_count": REVIEW_UNIT_COUNT,
        "reviewer_count": index["reviewer_count"],
        "structural_response_coverage_complete": True,
        "tracker_credit": False,
        "unresolved_unit_count": index["unresolved_unit_count"],
    }


def index_bytes(authority, campaign_authority, index):
    validate_structural_index_data(authority, campaign_authority, index)
    data = canonical_json(index, newline=True)
    if len(data) > MAX_INDEX_BYTES:
        raise ResponseIndexError("response index exceeds its byte cap")
    return data


def parse_index_bytes(authority, campaign_authority, data):
    validate_authority(authority)
    index = read_json_bytes(data, "response index", canonical=True)
    validate_structural_index_data(authority, campaign_authority, index)
    return index


def _directory_child_identities(response, path, label):
    context = None
    try:
        context = response._open_dir(Path(path), label)
        names = response._list_dir(context, PACKET_COUNT + 1)
        context["expected_names"] = names
        if names != list(EXPECTED_PACKET_IDS):
            raise ResponseIndexError(
                "{0} closure is not exact packet IDs 0001..0219".format(label)
            )
        identities = {}
        for name in names:
            info = os.stat(name, dir_fd=context["fd"], follow_symlinks=False)
            if not stat.S_ISDIR(info.st_mode):
                raise ResponseIndexError("{0}/{1} is not a directory".format(label, name))
            identities[name] = (
                info.st_dev,
                info.st_ino,
                info.st_mode,
                info.st_nlink,
                info.st_uid,
                info.st_gid,
                info.st_mtime_ns,
                info.st_ctime_ns,
            )
        response._replay_dir(context)
        return context, identities
    except Exception as error:
        if context is not None:
            response._close_dir(context)
        if isinstance(error, ResponseIndexError):
            raise
        raise ResponseIndexError("cannot snapshot {0}: {1}".format(label, error))


def _verify_child_identity(response, context, identities, name, label):
    try:
        response._replay_dir(context)
        info = os.stat(name, dir_fd=context["fd"], follow_symlinks=False)
    except (OSError, response.ReviewResponseError) as error:
        raise ResponseIndexError("cannot replay {0}: {1}".format(label, error))
    current = (
        info.st_dev,
        info.st_ino,
        info.st_mode,
        info.st_nlink,
        info.st_uid,
        info.st_gid,
        info.st_mtime_ns,
        info.st_ctime_ns,
    )
    if current != identities[name]:
        raise ResponseIndexError("{0}/{1} identity changed".format(label, name))


def collect_verified_packets(response, packet_root, response_root, verifier):
    """Collect exactly 219 verified results with root-namespace replay.

    Relative roots are resolved once against the entry working directory.
    Later working-directory changes can therefore never retarget either tree;
    strict retained-ancestor replay may instead reject the collection if any
    recorded namespace identity changes while verification is in progress.

    ``verifier`` is injectable for bounded structural-build tests, whose plain
    dictionary results can only reach the always-false serialized census.
    Production passes the closure around :func:`verify_packet_snapshot`; only
    that frozen-stack closure can emit the sealed handles required for a live
    verification result.
    """
    starting_directory = os.getcwd()

    def absolute_from_start(value, label):
        raw = str(value)
        if not raw or "\x00" in raw or "\\" in raw:
            raise ResponseIndexError("{0} path is unsafe".format(label))
        absolute = raw if os.path.isabs(raw) else os.path.join(starting_directory, raw)
        return Path(os.path.normpath(absolute))

    packet_root = absolute_from_start(packet_root, "campaign packet root")
    response_root = absolute_from_start(response_root, "review response root")
    packet_context = None
    response_context = None
    try:
        packet_context, packet_ids = _directory_child_identities(
            response, packet_root, "campaign packet root"
        )
        response_context, response_ids = _directory_child_identities(
            response, response_root, "review response root"
        )
        results = []
        for packet_id in EXPECTED_PACKET_IDS:
            _verify_child_identity(
                response, packet_context, packet_ids, packet_id, "campaign packet root"
            )
            _verify_child_identity(
                response, response_context, response_ids, packet_id, "review response root"
            )
            result = verifier(
                packet_id,
                packet_root / packet_id,
                response_root / packet_id,
            )
            if type(result) is not LiveVerifiedPacket and type(result) is not dict:
                raise ResponseIndexError(
                    "packet verifier did not emit a sealed or structural result"
                )
            _verify_child_identity(
                response, packet_context, packet_ids, packet_id, "campaign packet root"
            )
            _verify_child_identity(
                response, response_context, response_ids, packet_id, "review response root"
            )
            results.append(result)
        response._replay_dir(packet_context)
        response._replay_dir(response_context)
        return results
    except ResponseIndexError:
        raise
    except response.ReviewResponseError as error:
        raise ResponseIndexError("response root replay failed: {0}".format(error))
    finally:
        if packet_context is not None:
            response._close_dir(packet_context)
        if response_context is not None:
            response._close_dir(response_context)


def build_index(
    authority,
    campaign_authority,
    response,
    packet_root,
    response_root,
    verifier,
):
    validate_authority(authority)
    validate_campaign(authority, campaign_authority)
    verified = collect_verified_packets(
        response, packet_root, response_root, verifier
    )
    return build_index_data(
        authority, campaign_authority, _collected_packet_entries(verified)
    )


def verify_index(
    authority,
    campaign_authority,
    response,
    packet_root,
    response_root,
    verifier,
    data,
):
    index = parse_index_bytes(authority, campaign_authority, data)
    verified = collect_verified_packets(
        response, packet_root, response_root, verifier
    )
    return verify_index_data(
        authority, campaign_authority, index, verified_packets=verified
    )


def _stable_directory_identity(info):
    return (
        info.st_dev,
        info.st_ino,
        stat.S_IFMT(info.st_mode),
        stat.S_IMODE(info.st_mode),
        info.st_nlink,
        info.st_uid,
        info.st_gid,
    )


def _parent_chain_snapshot(context, label):
    records = []
    for record in context["chain"]:
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
        opened_identity = _stable_directory_identity(opened)
        if opened_identity != _stable_directory_identity(namespace):
            raise ResponseIndexError("{0} namespace identity differs".format(label))
        if not stat.S_ISDIR(opened.st_mode):
            raise ResponseIndexError("{0} component is not a directory".format(label))
        records.append(opened_identity)
    final = os.fstat(context["fd"])
    if final.st_uid not in (0, os.geteuid()):
        raise ResponseIndexError("{0} has an untrusted owner".format(label))
    if final.st_mode & (stat.S_IWGRP | stat.S_IWOTH):
        raise ResponseIndexError("{0} is group/world writable".format(label))
    return tuple(records)


def _replay_parent_chain(context, expected, label):
    actual = _parent_chain_snapshot(context, label)
    if actual != expected:
        raise ResponseIndexError("{0} changed during publication".format(label))


def _read_retained_fd(descriptor, cap, label):
    try:
        os.lseek(descriptor, 0, os.SEEK_SET)
    except OSError as error:
        raise ResponseIndexError("cannot rewind {0}: {1}".format(label, error))
    chunks = []
    retained = 0
    while True:
        block = os.read(descriptor, min(1024 * 1024, cap + 1 - retained))
        if not block:
            break
        retained += len(block)
        if retained > cap:
            raise ResponseIndexError("{0} exceeds its byte cap".format(label))
        chunks.append(block)
    return b"".join(chunks)


def _validate_output_snapshot(descriptor, parent_fd, name, data, mode, label):
    first = os.fstat(descriptor)
    namespace_first = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
    retained = _read_retained_fd(descriptor, MAX_INDEX_BYTES, label)
    second = os.fstat(descriptor)
    namespace_second = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
    final = os.fstat(descriptor)
    for info in (first, namespace_first, second, namespace_second, final):
        if (
            not stat.S_ISREG(info.st_mode)
            or info.st_nlink != 1
            or stat.S_IMODE(info.st_mode) != mode
            or info.st_size != len(data)
        ):
            raise ResponseIndexError("{0} identity differs".format(label))
    expected_identity = _file_identity(first)
    for info in (namespace_first, second, namespace_second, final):
        if _file_identity(info) != expected_identity:
            raise ResponseIndexError("{0} changed during retained replay".format(label))
    expected_inode = (first.st_dev, first.st_ino)
    for info in (namespace_first, second, namespace_second, final):
        if (info.st_dev, info.st_ino) != expected_inode:
            raise ResponseIndexError("{0} namespace changed".format(label))
    if retained != data or hashlib.sha256(retained).digest() != hashlib.sha256(data).digest():
        raise ResponseIndexError("{0} retained bytes differ".format(label))
    return expected_inode


def _rename_noreplace(parent_fd, old_name, new_name):
    try:
        libc = ctypes.CDLL(None, use_errno=True)
        renameat2 = libc.renameat2
    except (AttributeError, OSError) as error:
        raise ResponseIndexError(
            "Linux renameat2(RENAME_NOREPLACE) is unavailable: {0}".format(error)
        )
    renameat2.argtypes = (
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_uint,
    )
    renameat2.restype = ctypes.c_int
    result = renameat2(
        parent_fd,
        old_name.encode("ascii"),
        parent_fd,
        new_name.encode("ascii"),
        1,
    )
    if result != 0:
        number = ctypes.get_errno()
        raise OSError(number, os.strerror(number), new_name)


def _unlink_owned_name(parent_fd, name, descriptor):
    if not name:
        return False
    try:
        namespace = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
        opened = os.fstat(descriptor)
    except FileNotFoundError:
        return False
    if (namespace.st_dev, namespace.st_ino) != (opened.st_dev, opened.st_ino):
        return False
    os.unlink(name, dir_fd=parent_fd)
    return True


def _new_stage_name(parent_fd):
    flags = (
        os.O_RDWR
        | os.O_CREAT
        | os.O_EXCL
        | getattr(os, "O_NONBLOCK", 0)
        | getattr(os, "O_NOFOLLOW", 0)
        | getattr(os, "O_CLOEXEC", 0)
    )
    for _attempt in range(32):
        name = ".rk001-index-stage-{0}-{1}".format(
            os.getpid(), os.urandom(16).hex()
        )
        try:
            return name, os.open(name, flags, 0o600, dir_fd=parent_fd)
        except FileExistsError:
            continue
    raise ResponseIndexError("cannot allocate a unique private index stage")


def _write_new_file(response, path, data):
    path = Path(path)
    if type(data) is not bytes or len(data) > MAX_INDEX_BYTES:
        raise ResponseIndexError("index output bytes are invalid")
    if (
        path.name in ("", ".", "..")
        or os.sep in path.name
        or "\\" in path.name
        or "\x00" in path.name
    ):
        raise ResponseIndexError("output filename is unsafe")
    try:
        encoded_name = path.name.encode("ascii")
    except UnicodeEncodeError:
        raise ResponseIndexError("output filename is not ASCII")
    if len(encoded_name) > 255:
        raise ResponseIndexError("output filename exceeds its byte cap")
    context = None
    descriptor = None
    retained_descriptor = None
    stage_name = None
    published = False
    try:
        parent = Path(os.path.abspath(str(path.parent)))
        context = response._open_dir(parent, "index output parent")
        parent_snapshot = _parent_chain_snapshot(context, "index output parent")
        try:
            os.stat(path.name, dir_fd=context["fd"], follow_symlinks=False)
        except FileNotFoundError:
            pass
        else:
            raise ResponseIndexError("index output already exists")
        stage_name, descriptor = _new_stage_name(context["fd"])
        offset = 0
        while offset < len(data):
            written = os.write(descriptor, data[offset:])
            if written <= 0:
                raise ResponseIndexError("index stage write made no progress")
            offset += written
        os.fsync(descriptor)
        _validate_output_snapshot(
            descriptor, context["fd"], stage_name, data, 0o600, "index stage"
        )
        os.fchmod(descriptor, 0o444)
        os.fsync(descriptor)
        _validate_output_snapshot(
            descriptor, context["fd"], stage_name, data, 0o444, "sealed index stage"
        )
        read_flags = (
            os.O_RDONLY
            | getattr(os, "O_NONBLOCK", 0)
            | getattr(os, "O_NOFOLLOW", 0)
            | getattr(os, "O_CLOEXEC", 0)
        )
        retained_descriptor = os.open(
            stage_name, read_flags, dir_fd=context["fd"]
        )
        _validate_output_snapshot(
            retained_descriptor,
            context["fd"],
            stage_name,
            data,
            0o444,
            "retained read-only index stage",
        )
        os.close(descriptor)
        descriptor = retained_descriptor
        retained_descriptor = None
        _replay_parent_chain(context, parent_snapshot, "index output parent")
        os.fsync(context["fd"])
        _rename_noreplace(context["fd"], stage_name, path.name)
        published = True
        stage_name = None
        os.fsync(context["fd"])
        _replay_parent_chain(context, parent_snapshot, "index output parent")
        _validate_output_snapshot(
            descriptor, context["fd"], path.name, data, 0o444, "published index"
        )
        _replay_parent_chain(context, parent_snapshot, "index output parent")
        _validate_output_snapshot(
            descriptor, context["fd"], path.name, data, 0o444, "published index"
        )
        _replay_parent_chain(context, parent_snapshot, "index output parent")
    except Exception as error:
        if context is not None and descriptor is not None:
            target = path.name if published else stage_name
            try:
                if _unlink_owned_name(context["fd"], target, descriptor):
                    os.fsync(context["fd"])
            except OSError as cleanup_error:
                raise ResponseIndexError(
                    "index publication failed ({0}); cleanup failed ({1})".format(
                        error, cleanup_error
                    )
                )
        raise ResponseIndexError("cannot create index output: {0}".format(error))
    finally:
        if retained_descriptor is not None:
            try:
                os.close(retained_descriptor)
            except OSError:
                pass
        if descriptor is not None:
            try:
                os.close(descriptor)
            except OSError:
                pass
        if context is not None:
            response._close_dir(context)


def parser(argv=None):
    value = argparse.ArgumentParser(description=__doc__)
    value.add_argument("--repo", default=REPO_ROOT, type=Path)
    value.add_argument("--authority", type=Path)
    modes = value.add_mutually_exclusive_group(required=True)
    modes.add_argument("--check", action="store_true")
    modes.add_argument("--build-index", action="store_true")
    modes.add_argument("--verify-index", action="store_true")
    value.add_argument("--artifact", type=Path)
    value.add_argument("--packets-root", type=Path)
    value.add_argument("--responses-root", type=Path)
    value.add_argument("--index", type=Path)
    value.add_argument("--output", type=Path)
    return value.parse_args(argv)


def main(argv=None):
    args = parser(argv)
    try:
        repo = args.repo.resolve()
        authority = load_authority(repo, args.authority)
        response, response_authority, campaign, campaign_authority = load_frozen_stack(
            repo, authority
        )
        if args.check:
            print(
                "RK-001 response-index contract verified: packets=219 units=115265 "
                "reviewers=0 durable=false campaign_complete=false gate=TODO "
                "points=0 credit=false"
            )
            return 0
        for candidate, label in (
            (args.artifact, "--artifact"),
            (args.packets_root, "--packets-root"),
            (args.responses_root, "--responses-root"),
        ):
            if candidate is None:
                raise ResponseIndexError("{0} is required".format(label))
        try:
            derived = campaign.derive_campaign(repo, args.artifact, campaign_authority)
        except campaign.ReviewCampaignError as error:
            raise ResponseIndexError("frozen campaign artifact rejected: {0}".format(error))

        def production_verifier(packet_id, packet_directory, response_directory):
            return verify_packet_snapshot(
                response,
                response_authority,
                campaign,
                campaign_authority,
                derived,
                packet_id,
                packet_directory,
                response_directory,
            )

        if args.build_index:
            if args.output is None:
                raise ResponseIndexError("--output is required")
            index = build_index(
                authority,
                campaign_authority,
                response,
                args.packets_root,
                args.responses_root,
                production_verifier,
            )
            data = index_bytes(authority, campaign_authority, index)
            _write_new_file(response, args.output, data)
            print(
                "RK-001 structural response index built: packets=219 units=115265 "
                "unresolved={0} reviewers={1} campaign_complete=false durable=false "
                "gate=TODO points=0 credit=false".format(
                    index["unresolved_unit_count"], index["reviewer_count"]
                )
            )
            return 0
        if args.index is None:
            raise ResponseIndexError("--index is required")
        data = _read_regular(args.index, MAX_INDEX_BYTES, "response index")
        result = verify_index(
            authority,
            campaign_authority,
            response,
            args.packets_root,
            args.responses_root,
            production_verifier,
            data,
        )
        print(
            "RK-001 structural response index verified: packets={0} units={1} "
            "unresolved={2} reviewers={3} campaign_complete=false durable=false "
            "gate=TODO points=0 credit=false".format(
                result["packet_count"],
                result["reviewed_unit_count"],
                result["unresolved_unit_count"],
                result["reviewer_count"],
            )
        )
        return 0
    except ResponseIndexError as error:
        print("RK-001 response-index error: {0}".format(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
