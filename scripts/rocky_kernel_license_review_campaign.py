#!/usr/bin/env python3
"""Derive, package, and verify the full non-crediting RK-001 review campaign.

The campaign deterministically partitions every item in the exact ef58860e
license inventory.  It preserves review batch 0001, keeps exact-content groups
atomic, and emits only unreviewed inputs for a future independent reviewer.
Machine classification is not legal review, a content finding never resolves a
path automatically, archive containers remain expansion-required, and this
authority cannot award tracker credit.
"""

from __future__ import print_function

import argparse
import collections
import hashlib
import json
import os
import shutil
import stat
import sys
import tempfile
import types
from pathlib import Path, PurePosixPath


REPO_ROOT = Path(__file__).resolve().parents[1]
AUTHORITY_PATH = Path(
    "host-kernel/rocky/evidence/rk001-license-review-campaign-ef58-v1.json"
)
# Filled only after the canonical authority is generated and independently checked.
AUTHORITY_SHA256 = "b5581cb9ad5707af65968a6e01ea69a7c46ebbe2542412c1a4cec0611da77852"
SCHEMA_VERSION = 1
CAMPAIGN_ID = "rk-001-license-review-campaign-ef58860e-v1"
SOURCE_COMMIT = "ef58860e4806ee16e2c506e4e93c7b6ad8ad8f4b"
MACHINE = "machine-classified-exact-spdx"
UNRESOLVED = "unresolved"
REVIEW_STATE = "independent-review-required"

GROUP_LIMIT = 512
UNIT_LIMIT = 2500
MAX_CONTENT_BYTES = 60 * 1024 * 1024
MAX_PACKAGE_BYTES = 64 * 1024 * 1024
MAX_AUTHORITY_BYTES = 1024 * 1024
MAX_CHECKER_BYTES = 2 * 1024 * 1024
MAX_ARTIFACT_BYTES = 8 * 1024 * 1024
MAX_FULL_STREAM_BYTES = 192 * 1024 * 1024
MAX_PACKET_STREAM_BYTES = 16 * 1024 * 1024
MAX_PACKET_RECORDS = 3000
MAX_JSON_NESTING = 64
MAX_JSON_NUMBER_TOKEN = 128

HEX_SHA256 = __import__("re").compile(r"^[0-9a-f]{64}$")
HEX_SHA1 = __import__("re").compile(r"^[0-9a-f]{40}$")
PACKET_ID_PATTERN = __import__("re").compile(r"^[0-9]{4}$")

ARCHIVE_SUFFIXES = (
    ".bz2",
    ".cpio",
    ".gz",
    ".rpm",
    ".src.rpm",
    ".tar",
    ".tar.bz2",
    ".tar.gz",
    ".tar.xz",
    ".tgz",
    ".xz",
    ".zip",
)
SPECIAL_BASIS = "archive-or-rpm-spec-needs-review"

BATCH_AUTHORITY = {
    "batch_id": "rk-001-license-review-batch-ef58860e-0001-v1",
    "path": "host-kernel/rocky/evidence/rk001-license-review-batch-ef58-0001-contract-v1.json",
    "sha256": "e253bfe2ec251cae7f9cd41ebf8df41ad10baa671a755abc89bfc33d19525e9b",
    "size": 4950,
}
BATCH_CHECKER = {
    "path": "scripts/rocky_kernel_license_review_batch.py",
    "sha256": "553a914a12766c3debfb4112cdb26235861f5b70914418b4749ae654d357b06b",
    "size": 63521,
}
BATCH_TESTS = {
    "path": "scripts/tests/test_rocky_kernel_license_review_batch.py",
    "sha256": "60e13fb18184126b9a8c63012b76acf2aa8bac2f098d9ba7df6cb98b53cb0b6d",
    "size": 33623,
}
BATCH_WORKFLOW = {
    "path": ".github/workflows/rk001-license-review-batch-v1.yml",
    "sha256": "aca51e886f5cacca15596b35ce31c4468c0a60618226d5fd7edbd4ebcbac8d6d",
    "size": 13199,
}
CAMPAIGN_WORKFLOW = {
    "path": ".github/workflows/rk001-license-review-campaign-v1.yml",
    "sha256": "95dde8bed1697c792a05f5768ea7dd7ac32d3538f2bf41ce35b8a10d858fa370",
    "size": 24447,
}
QUEUE_AUTHORITY = {
    "path": "host-kernel/rocky/evidence/rk001-license-review-queue-ef58-v1.json",
    "queue_id": "rk-001-license-review-queue-ef58860e-v1",
    "sha256": "e284b3700b9ec0a286b07f44505948418b67309015943856ceeb7c2f45c37d37",
    "size": 3485,
}
QUEUE_CHECKER = {
    "path": "scripts/rocky_kernel_license_review_queue.py",
    "sha256": "13aceef27d471a13dc9ecabde2c905b25b9465ef9b57968e96ce72692a01aa8b",
    "size": 53368,
}
DECISION_AUTHORITY = {
    "path": "host-kernel/rocky/evidence/rk001-license-decisions-ef58-v1.json",
    "review_id": "rk-001-license-decisions-ef58860e-v1",
    "sha256": "1e9769ffb9d8ccd4b49b0457678b9ed3841c647f6b817a7d66e815f0e6e84299",
    "size": 10012,
}
DECISION_CHECKER = {
    "path": "scripts/rocky_kernel_license_decisions.py",
    "sha256": "1414c1c16eca768f81de39739bd56ef1283435bf0c163c5e01b02c34e6291112",
    "size": 46167,
}
SOURCE_LOCK = {
    "path": "host-kernel/rocky/source-lock.json",
    "sha256": "707ee40466ac0bb0cd0600383bba0b13fc1146e7080034786bf5668a95b27682",
    "size": 18236,
}
SOURCE_LOCK_VALIDATOR = {
    "path": "scripts/rocky_kernel_source_lock.py",
    "sha256": "1fc6f6457d5a06d43260b84a8627fa2297c360d3a5c3810012a2198aadf3c262",
    "size": 60008,
}
INVENTORY_ARTIFACT = {
    "archive_name": "rk001-license-inventory-32192199002-1.zip",
    "sha256": "09333e984e27a45b6af1b2f7d613570f6bf09d3a82f0fa7c6fbf4c9fd7707b18",
    "size": 6734527,
    "source_commit": SOURCE_COMMIT,
}
INVENTORY_MEMBER = {
    "name": "license-inventory.jsonl.gz",
    "sha256": "25261775ecaede74cc1482cd733305f0fae7f8003a1a137ea01b40d4c147a41a",
    "size": 6728950,
}

EXPECTED_INPUTS = {
    "batch_authority": BATCH_AUTHORITY,
    "batch_checker": BATCH_CHECKER,
    "batch_tests": BATCH_TESTS,
    "batch_workflow": BATCH_WORKFLOW,
    "campaign_workflow": CAMPAIGN_WORKFLOW,
    "decision_authority": DECISION_AUTHORITY,
    "decision_checker": DECISION_CHECKER,
    "inventory_artifact": INVENTORY_ARTIFACT,
    "inventory_member": INVENTORY_MEMBER,
    "queue_authority": QUEUE_AUTHORITY,
    "queue_checker": QUEUE_CHECKER,
    "source_lock": SOURCE_LOCK,
    "source_lock_validator": SOURCE_LOCK_VALIDATOR,
}
EXPECTED_CLAIMS = {
    "archive_expansion_complete": False,
    "campaign_complete": False,
    "credit_eligible": False,
    "durable_archive": False,
    "independent_legal_review_complete": False,
    "machine_classification_is_legal_review": False,
    "provenance_review_complete": False,
    "redistribution_approved": False,
    "tracker_credit": False,
}
EXPECTED_GATE = {
    "credit_eligible": False,
    "gate_id": "RK-001",
    "points_awarded": 0,
    "status": "TODO",
    "tracker_credit": False,
}
EXPECTED_PARTITION_POLICY = {
    "archive_container_review_state": "expansion-required",
    "archive_suffixes": list(ARCHIVE_SUFFIXES),
    "content_group_atomic": True,
    "content_group_order": "group-id-ascending",
    "group_limit": GROUP_LIMIT,
    "machine_classification_requires_independent_review": True,
    "maximum_content_bytes": MAX_CONTENT_BYTES,
    "maximum_package_bytes": MAX_PACKAGE_BYTES,
    "ordinary_lane": "ordinary-content-and-unit-review",
    "packet_id_order": "four-digit-ascending",
    "preserve_packet_0001": BATCH_AUTHORITY["batch_id"],
    "selection_auto_resolves": False,
    "special_basis": SPECIAL_BASIS,
    "special_lane": "package-scope-and-container-expansion",
    "symlink_lane": "symlink-context-review",
    "unit_limit": UNIT_LIMIT,
    "unit_order": "inventory-path-order",
}
EXPECTED_PACKAGE_POLICY = {
    "checksum_manifest": "SHA256SUMS",
    "content_directory": "content",
    "content_filename": "lowercase-sha256",
    "content_group_stream": "content-groups.jsonl",
    "descriptor_rooted_reads": True,
    "expansion_required_stream": "expansion-required.jsonl",
    "hardlinks_allowed": False,
    "maximum_content_bytes": MAX_CONTENT_BYTES,
    "maximum_package_bytes": MAX_PACKAGE_BYTES,
    "member_mode": "0444",
    "member_order": "bytewise-name-ascending",
    "namespace_replay": "held-root-ancestor-and-member-identities-before-during-and-after-retention",
    "no_partial_retention": True,
    "packet_summary": "packet-summary.json",
    "review_unit_stream": "review-units.jsonl",
}
EXPECTED_RESULT = {
    "content_group_count": 111004,
    "content_group_stream_bytes": 44961974,
    "content_group_stream_sha256": "35f981e50085d19a45d459aa9684f2b95eaad987781eea59bed8e3e5e356e31c",
    "duplicate_content_group_count": 2411,
    "duplicate_content_path_count": 6589,
    "inventory_item_count": 115265,
    "machine_classified_content_bytes": 893753404,
    "machine_classified_content_group_count": 72385,
    "machine_classified_item_count": 72616,
    "materialized_content_bytes": 1524399818,
    "maximum_ordinary_packet_content_bytes": 33893367,
    "maximum_ordinary_packet_unit_count": 602,
    "metadata_only_content_bytes": 153393856,
    "namespace_decision_counts": {
        "dist-git": {MACHINE: 1, UNRESOLVED: 76},
        "linux": {MACHINE: 72557, UNRESOLVED: 42470},
        "repository": {MACHINE: 57, UNRESOLVED: 33},
        "srpm": {MACHINE: 1, UNRESOLVED: 70},
    },
    "ordinary_content_bytes": 1522454817,
    "ordinary_content_group_count": 110480,
    "ordinary_packet_count": 216,
    "ordinary_review_unit_count": 113055,
    "packet_count": 219,
    "packet_manifest_stream_bytes": 156033,
    "packet_manifest_stream_sha256": "b4bf0e5c97d46f1443a70402fe39e624cd0ceab7d710170c425ea7eb940a1c06",
    "preserved_packet_content_bytes": 81202,
    "preserved_packet_content_group_count": 512,
    "preserved_packet_group_stream_bytes": 184917,
    "preserved_packet_group_stream_sha256": "a1a5ed89800a35ca9fbbe59074628ef62e6f90f0a27da38078e2f96596146710",
    "preserved_packet_path_set_sha256": "8b13ad470f0e56acc6c7cf6e01bc47aebfc4eb1ed8c45b8b9b6df8d39b96e7cd",
    "preserved_packet_review_unit_count": 2096,
    "preserved_packet_unit_stream_bytes": 2555534,
    "preserved_packet_unit_stream_sha256": "c6c02b9da1dbda617ff057cbd8e2bb630ded1b35920c3ba2869b186f85cf19c2",
    "referenced_content_bytes": 1677793674,
    "regular_item_count": 115182,
    "review_unit_count": 115265,
    "review_unit_stream_bytes": 143777216,
    "review_unit_stream_sha256": "33ce34f36cd7f75b63d5ee0f54dde9dde6ee18292b39b580fde1722582a0acd9",
    "special_archive_content_bytes": 153393856,
    "special_archive_group_count": 3,
    "special_content_bytes": 155257655,
    "special_content_group_count": 12,
    "special_materialized_content_bytes": 1863799,
    "special_review_unit_count": 31,
    "symlink_item_count": 83,
    "unresolved_content_bytes": 784040270,
    "unresolved_content_group_count": 38619,
    "unresolved_item_count": 42649,
}
EXPECTED_FUTURE_RESPONSE_SCHEMA = {
    "acceptance": (
        "signed-response-structure-may-include-unresolved-decisions; "
        "campaign-closure-requires-every-unit-independent-fields-affirmative"
    ),
    "archive_response_acceptance": "follow-each-frozen-archive-role-and-child-closure-binding",
    "archive_expansion_response_required": True,
    "content_finding_auto_resolves_paths": False,
    "implemented_by_this_campaign": False,
    "machine_classification_auto_accepted": False,
    "signed_response_root_required": True,
    "unexpanded_container_attachment_can_close": False,
    "unit_decision_fields": [
        "unit_id",
        "unit_evidence_sha256",
        "content_finding_id",
        "path",
        "namespace",
        "origin",
        "source_identity",
        "context_group_id",
        "license_status",
        "provenance_status",
        "authorship_status",
        "redistribution_status",
        "resolved_or_unresolved",
        "reviewer_identity",
        "support_reference_ids",
        "signed_response_root",
    ],
}
EXPECTED_REMAINING_BLOCKERS = [
    "All 115265 campaign units remain independent-review-required; partitioning is not review or resolution.",
    "The 72616 machine-classified units record deterministic checker output only and are not legal, provenance, authorship, or redistribution conclusions.",
    "A content finding never automatically resolves paths that share bytes; every path and context needs an independently signed unit decision.",
    "The main Linux archive has an exact 115027-unit frozen child inventory, but those child units and the container context remain independently unreviewed.",
    "The stablelists and kabi-dw archives have no child units in this campaign and require future v2 expansion and inventory before any response can close them.",
    "All three raw archive groups remain metadata-only; attaching raw container bytes alone cannot count as review, closure, or credit.",
    "The temporary Actions artifact is not a durable archive.",
    "The source lock and tracker remain unchanged until every unit and archive expansion is independently reviewed, unresolved count is zero, and durable authority is registered.",
]

SPECIAL_ARCHIVE_GROUP_IDS = [
    "exact-content:50796af2bd673340a5896bb86bd5ab1d8f45aa38eb509d2b52a0bca418fc5cae",
    "exact-content:93935cc150c81723440f7d595a7c63229068982bdff09a7bf838d969ad435541",
    "exact-content:f0c74f97bba883f0da0f371406d0912b9c23a1e42a7bd2c3746c9e69cfd41530",
]

LINUX_CAPTURE_AUTHORITY_RECORD = {
    "complete": True,
    "item_count": 115027,
    "path_set_sha256": "f7495feae099d970ef02bbb1a73a0669b88c83c33dad80d3cc6bfb4184b2b0c2",
    "source_manifest_sha256": "321b8a227f7a9473a94db6fbf747c48727a39b20bd8a24474f68578915ca4e56",
}

LINUX_CAPTURE_NAMESPACE_CLOSURE = {
    "complete": True,
    "item_count": 115027,
    "path_set_algorithm": "utf8-path-newline",
    "path_set_sha256": "f7495feae099d970ef02bbb1a73a0669b88c83c33dad80d3cc6bfb4184b2b0c2",
    "source_closure_path_set_sha256": "f7495feae099d970ef02bbb1a73a0669b88c83c33dad80d3cc6bfb4184b2b0c2",
    "source_manifest_algorithm": "canonical-json-source-rows",
    "source_manifest_sha256": "321b8a227f7a9473a94db6fbf747c48727a39b20bd8a24474f68578915ca4e56",
}

EXPECTED_ARCHIVE_EXPANSION_BINDINGS = [
    {
        "attachment_alone_credit_eligible": False,
        "attachment_alone_counts_as_reviewed": False,
        "child_inventory": {
            "capture_namespace_closure": LINUX_CAPTURE_NAMESPACE_CLOSURE,
            "derived_review_closure": {
                "content_group_count": 110910,
                "content_group_id_stream_algorithm": "canonical-json-group-id-rows",
                "content_group_id_stream_bytes": 10425540,
                "content_group_id_stream_sha256": "fde9cf1678f54eadf2bf1bce93a752edcd7a10b5b5ff834568235b4a61b1948b",
                "decision_counts": {MACHINE: 72557, UNRESOLVED: 42470},
                "namespace": "linux",
                "path_set_algorithm": "canonical-json-path-rows",
                "path_set_sha256": "0baf370a119e991d76822d9bb452273f0eb1ba1d6e49dae5cd8cf5574aa3b273",
                "referenced_content_bytes": 1513073476,
                "regular_unit_count": 114944,
                "review_state": REVIEW_STATE,
                "review_unit_count": 115027,
                "review_unit_id_stream_algorithm": "canonical-json-unit-id-rows",
                "review_unit_id_stream_bytes": 10467457,
                "review_unit_id_stream_sha256": "f24cc1417f7cf1f343bdb9802565398c3d4269263f738b4fff70784930b79180",
                "source_identity": {
                    "archive_sha256": "4a174d47b8874a2139efcd1ac1ab2d6b80ae7a0ca62f0ae4596fd20cf62a3533"
                },
                "symlink_unit_count": 83,
            },
        },
        "child_review_complete": False,
        "container": {
            "group_id": SPECIAL_ARCHIVE_GROUP_IDS[0],
            "path": "srpm/SOURCES/linux-6.12.0-211.44.1.el10_2.tar.xz",
            "sha256": "4a174d47b8874a2139efcd1ac1ab2d6b80ae7a0ca62f0ae4596fd20cf62a3533",
            "size": 153374592,
            "unit_id": "review-unit:47dcbbd652a0b109522e067d4771ee9e125f131f689b0cccb0354ee9f78e956c",
        },
        "container_review_state": REVIEW_STATE,
        "required_next_action": "review-existing-frozen-linux-child-units-and-container-context",
        "role": "existing-inventory-closure",
    },
    {
        "attachment_alone_credit_eligible": False,
        "attachment_alone_counts_as_reviewed": False,
        "child_inventory": None,
        "child_review_complete": False,
        "container": {
            "group_id": SPECIAL_ARCHIVE_GROUP_IDS[1],
            "path": "srpm/SOURCES/kernel-abi-stablelists-6.12.0-211.44.1.el10_2.tar.xz",
            "sha256": "9c753338d255502a040c82be6a39a47b80df15e30fb1d3bc2f13687522c27032",
            "size": 18168,
            "unit_id": "review-unit:66737e57212b2e92f7074e2a37ac75061ed95c07e844dd5a54a0313fcd4bf1db",
        },
        "container_review_state": REVIEW_STATE,
        "required_next_action": "expand-and-capture-future-v2-child-inventory-before-any-closure-response",
        "role": "future-v2-child-inventory-required",
    },
    {
        "attachment_alone_credit_eligible": False,
        "attachment_alone_counts_as_reviewed": False,
        "child_inventory": None,
        "child_review_complete": False,
        "container": {
            "group_id": SPECIAL_ARCHIVE_GROUP_IDS[2],
            "path": "srpm/SOURCES/kernel-kabi-dw-6.12.0-211.44.1.el10_2.tar.xz",
            "sha256": "7547d50e4f0daeb28eba949801d3d09d0c3c6a8946859759a44d00f786791d4e",
            "size": 1096,
            "unit_id": "review-unit:1fd6600d10b6a8b34d75e36cf027374a7c4ffa3599e0a8a516af2f10aace5d11",
        },
        "container_review_state": REVIEW_STATE,
        "required_next_action": "expand-and-capture-future-v2-child-inventory-before-any-closure-response",
        "role": "future-v2-child-inventory-required",
    },
]


class ReviewCampaignError(RuntimeError):
    """Raised when the campaign authority, derivation, or packet fails closed."""


def reject_duplicate_pairs(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ReviewCampaignError("duplicate JSON key: {0}".format(key))
        value[key] = item
    return value


def parse_bounded_json_int(token):
    if type(token) is not str or len(token) > MAX_JSON_NUMBER_TOKEN:
        raise ReviewCampaignError("JSON integer token exceeds its cap")
    try:
        return int(token, 10)
    except ValueError as error:
        raise ReviewCampaignError("JSON integer token is invalid: {0}".format(error))


def reject_json_float(token):
    if type(token) is not str or len(token) > MAX_JSON_NUMBER_TOKEN:
        raise ReviewCampaignError("JSON float token exceeds its cap")
    raise ReviewCampaignError("JSON floating-point values are forbidden")


def reject_json_constant(token):
    raise ReviewCampaignError("nonfinite JSON value is forbidden: {0}".format(token))


def require_bounded_json_nesting(value):
    stack = [(value, 0)]
    while stack:
        current, depth = stack.pop()
        if depth > MAX_JSON_NESTING:
            raise ReviewCampaignError("JSON nesting exceeds its cap")
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
        raise ReviewCampaignError("value is not canonical JSON: {0}".format(error))
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
    except ReviewCampaignError:
        raise
    except (RecursionError, UnicodeError, ValueError) as error:
        raise ReviewCampaignError("{0} is not valid JSON: {1}".format(label, error))
    require_bounded_json_nesting(value)
    if type(value) is not dict:
        raise ReviewCampaignError("{0} must be a JSON object".format(label))
    if canonical and data != canonical_json(value, newline=True):
        raise ReviewCampaignError("{0} is not canonical JSON".format(label))
    return value


def exact_keys(value, keys, label):
    if type(value) is not dict or set(value) != set(keys):
        raise ReviewCampaignError("{0} fields changed".format(label))
    return value


def require_exact(actual, expected, label):
    if type(actual) is not type(expected):
        raise ReviewCampaignError("{0} type changed".format(label))
    if isinstance(expected, dict):
        if set(actual) != set(expected):
            raise ReviewCampaignError("{0} fields changed".format(label))
        for key in expected:
            require_exact(actual[key], expected[key], label + "." + str(key))
        return
    if isinstance(expected, list):
        if len(actual) != len(expected):
            raise ReviewCampaignError("{0} length changed".format(label))
        for index, values in enumerate(zip(actual, expected)):
            require_exact(values[0], values[1], label + "[{0}]".format(index))
        return
    if actual != expected:
        raise ReviewCampaignError(
            "{0} differs: {1!r} != {2!r}".format(label, actual, expected)
        )


def require_nonnegative_int(value, label):
    if type(value) is not int or value < 0:
        raise ReviewCampaignError("{0} is not a nonnegative integer".format(label))


def require_sha256(value, label):
    if type(value) is not str or not HEX_SHA256.fullmatch(value):
        raise ReviewCampaignError("{0} is not a lowercase SHA-256".format(label))


def safe_relative(value, label):
    if type(value) is not str or not value or "\x00" in value or "\\" in value:
        raise ReviewCampaignError("{0} is not a safe relative path".format(label))
    path = PurePosixPath(value)
    if (
        path.is_absolute()
        or path.as_posix() != value
        or any(part in ("", ".", "..") for part in path.parts)
    ):
        raise ReviewCampaignError("{0} is not normalized".format(label))
    return value


def _stat_identity(info):
    return (
        info.st_dev,
        info.st_ino,
        info.st_mode,
        info.st_size,
        getattr(info, "st_mtime_ns", int(info.st_mtime * 1000000000)),
        getattr(info, "st_ctime_ns", int(info.st_ctime * 1000000000)),
    )


def _directory_identity(info):
    return (
        info.st_dev,
        info.st_ino,
        info.st_mode,
        info.st_uid,
        info.st_gid,
        getattr(info, "st_mtime_ns", int(info.st_mtime * 1000000000)),
        getattr(info, "st_ctime_ns", int(info.st_ctime * 1000000000)),
    )


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
            raise ReviewCampaignError(
                "{0} directory namespace changed: {1}".format(label, error)
            )
        if (
            _directory_identity(opened) != record["identity"]
            or _directory_identity(namespace) != record["identity"]
        ):
            raise ReviewCampaignError("{0} directory namespace changed".format(label))
    try:
        opened = os.fstat(context["descriptor"])
        namespace = os.stat(
            context["name"],
            dir_fd=context["parent_fd"],
            follow_symlinks=False,
        )
    except OSError as error:
        raise ReviewCampaignError(
            "{0} file namespace changed: {1}".format(label, error)
        )
    if (
        _stat_identity(opened) != context["identity"]
        or _stat_identity(namespace) != context["identity"]
    ):
        raise ReviewCampaignError("{0} file namespace changed".format(label))


def _read_descriptor_pass(context, label, size_cap):
    _replay_held_regular(context, label)
    expected_size = context["identity"][3]
    try:
        os.lseek(context["descriptor"], 0, os.SEEK_SET)
        chunks = []
        retained = 0
        while retained < expected_size:
            chunk = os.read(
                context["descriptor"], min(1024 * 1024, expected_size - retained)
            )
            if not chunk:
                raise ReviewCampaignError("{0} ended before its bound size".format(label))
            retained += len(chunk)
            if retained > size_cap:
                raise ReviewCampaignError("{0} exceeds its size cap".format(label))
            chunks.append(chunk)
            _replay_held_regular(context, label)
        if os.read(context["descriptor"], 1):
            raise ReviewCampaignError("{0} grew while read".format(label))
    except ReviewCampaignError:
        raise
    except OSError as error:
        raise ReviewCampaignError("cannot read {0}: {1}".format(label, error))
    _replay_held_regular(context, label)
    data = b"".join(chunks)
    if len(data) != expected_size:
        raise ReviewCampaignError("{0} size changed while read".format(label))
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
        raise ReviewCampaignError("{0} path is unsafe".format(label))
    absolute = os.path.abspath(raw)
    requested = Path(absolute)
    if requested.anchor != os.sep or len(requested.parts) < 2:
        raise ReviewCampaignError("{0} path is not an absolute file path".format(label))
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
            raise ReviewCampaignError("{0} root is not a directory".format(label))
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
            if component in ("", ".", "..") or "/" in component or "\\" in component:
                raise ReviewCampaignError("{0} path component is unsafe".format(label))
            following = os.open(component, directory_flags, dir_fd=current)
            following_info = os.fstat(following)
            namespace = os.stat(component, dir_fd=current, follow_symlinks=False)
            if (
                not stat.S_ISDIR(following_info.st_mode)
                or _directory_identity(following_info)
                != _directory_identity(namespace)
            ):
                os.close(following)
                raise ReviewCampaignError(
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
        name = requested.parts[-1]
        if name in ("", ".", "..") or "/" in name or "\\" in name:
            raise ReviewCampaignError("{0} filename is unsafe".format(label))
        descriptor = os.open(name, file_flags, dir_fd=current)
        opened = os.fstat(descriptor)
        namespace = os.stat(name, dir_fd=current, follow_symlinks=False)
    except (OSError, ReviewCampaignError) as error:
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
        if isinstance(error, ReviewCampaignError):
            raise
        raise ReviewCampaignError("cannot open {0}: {1}".format(label, error))
    try:
        if (
            not stat.S_ISREG(opened.st_mode)
            or _stat_identity(opened) != _stat_identity(namespace)
            or opened.st_size > size_cap
        ):
            raise ReviewCampaignError("{0} is not the bounded opened regular file".format(label))
        context = {
            "descriptor": descriptor,
            "directory_chain": chain,
            "identity": _stat_identity(opened),
            "name": name,
            "parent_fd": current,
        }
        first = _read_descriptor_pass(context, label, size_cap)
        second = _read_descriptor_pass(context, label, size_cap)
        if first != second:
            raise ReviewCampaignError("{0} byte replay differs".format(label))
        _replay_held_regular(context, label)
        return second
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


def _read_bound(repo, record, label, cap=MAX_CHECKER_BYTES):
    path = Path(repo) / safe_relative(record["path"], label + " path")
    data = read_regular_file_once(path, label, cap)
    if (
        len(data) != record["size"]
        or hashlib.sha256(data).hexdigest() != record["sha256"]
    ):
        raise ReviewCampaignError("{0} bytes differ".format(label))
    return path, data


PACKET_KEYS = {
    "content_bytes",
    "first_group_id",
    "group_count",
    "group_id_stream_bytes",
    "group_id_stream_sha256",
    "lane",
    "last_group_id",
    "materialized_content_bytes",
    "metadata_only_content_bytes",
    "packet_id",
    "path_set_sha256",
    "unit_count",
    "unit_id_stream_bytes",
    "unit_id_stream_sha256",
}


def validate_packet_manifest(packets):
    if type(packets) is not list or len(packets) != EXPECTED_RESULT["packet_count"]:
        raise ReviewCampaignError("packet manifest count differs")
    previous_last = None
    for index, packet in enumerate(packets, 1):
        exact_keys(packet, PACKET_KEYS, "packet manifest row")
        require_exact(packet["packet_id"], "{0:04d}".format(index), "packet ID")
        for key in (
            "content_bytes",
            "group_count",
            "group_id_stream_bytes",
            "materialized_content_bytes",
            "metadata_only_content_bytes",
            "unit_count",
            "unit_id_stream_bytes",
        ):
            require_nonnegative_int(packet[key], "packet " + key)
        for key in (
            "group_id_stream_sha256",
            "path_set_sha256",
            "unit_id_stream_sha256",
        ):
            require_sha256(packet[key], "packet " + key)
        require_exact(
            packet["materialized_content_bytes"]
            + packet["metadata_only_content_bytes"],
            packet["content_bytes"],
            "packet materialization partition",
        )
        if packet["group_count"] == 0:
            require_exact(packet["first_group_id"], None, "empty packet first group")
            require_exact(packet["last_group_id"], None, "empty packet last group")
        else:
            for key in ("first_group_id", "last_group_id"):
                value = packet[key]
                if type(value) is not str or not value.startswith("exact-content:"):
                    raise ReviewCampaignError("packet group boundary is malformed")
            if packet["first_group_id"] > packet["last_group_id"]:
                raise ReviewCampaignError("packet group boundaries are reversed")
        if index == 1:
            require_exact(packet["lane"], "preserved-review-batch-0001", "packet 0001 lane")
        elif index <= 217:
            require_exact(packet["lane"], EXPECTED_PARTITION_POLICY["ordinary_lane"], "ordinary lane")
            if packet["group_count"] > GROUP_LIMIT or packet["unit_count"] > UNIT_LIMIT:
                raise ReviewCampaignError("ordinary packet count cap exceeded")
            if packet["content_bytes"] > MAX_CONTENT_BYTES:
                raise ReviewCampaignError("ordinary packet content cap exceeded")
            if previous_last is not None and packet["first_group_id"] <= previous_last:
                raise ReviewCampaignError("ordinary packet boundaries overlap or reorder")
            previous_last = packet["last_group_id"]
        elif index == 218:
            require_exact(packet["lane"], EXPECTED_PARTITION_POLICY["special_lane"], "special lane")
        else:
            require_exact(packet["lane"], EXPECTED_PARTITION_POLICY["symlink_lane"], "symlink lane")
    data = stream_bytes(packets)
    require_exact(len(data), EXPECTED_RESULT["packet_manifest_stream_bytes"], "packet manifest bytes")
    require_exact(
        hashlib.sha256(data).hexdigest(),
        EXPECTED_RESULT["packet_manifest_stream_sha256"],
        "packet manifest digest",
    )
    require_exact(
        sum(packet["group_count"] for packet in packets),
        EXPECTED_RESULT["content_group_count"],
        "packet content-group closure",
    )
    require_exact(
        sum(packet["unit_count"] for packet in packets),
        EXPECTED_RESULT["review_unit_count"],
        "packet review-unit closure",
    )
    require_exact(
        sum(packet["content_bytes"] for packet in packets),
        EXPECTED_RESULT["referenced_content_bytes"],
        "packet content-byte closure",
    )
    require_exact(
        sum(packet["materialized_content_bytes"] for packet in packets),
        EXPECTED_RESULT["materialized_content_bytes"],
        "packet materialized-byte closure",
    )
    require_exact(
        sum(packet["metadata_only_content_bytes"] for packet in packets),
        EXPECTED_RESULT["metadata_only_content_bytes"],
        "packet metadata-only-byte closure",
    )
    return packets


def validate_authority(authority):
    exact_keys(
        authority,
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
        "review-campaign authority",
    )
    require_exact(authority["schema_version"], SCHEMA_VERSION, "schema version")
    require_exact(authority["campaign_id"], CAMPAIGN_ID, "campaign ID")
    require_exact(
        authority["archive_expansion_bindings"],
        EXPECTED_ARCHIVE_EXPANSION_BINDINGS,
        "archive expansion bindings",
    )
    require_exact(authority["inputs"], EXPECTED_INPUTS, "frozen inputs")
    require_exact(authority["claims"], EXPECTED_CLAIMS, "claims")
    require_exact(authority["gate"], EXPECTED_GATE, "gate")
    require_exact(authority["partition_policy"], EXPECTED_PARTITION_POLICY, "partition policy")
    require_exact(authority["package_policy"], EXPECTED_PACKAGE_POLICY, "package policy")
    require_exact(authority["expected_result"], EXPECTED_RESULT, "expected result")
    require_exact(
        authority["future_response_schema"],
        EXPECTED_FUTURE_RESPONSE_SCHEMA,
        "future response schema",
    )
    require_exact(
        authority["remaining_blockers"],
        EXPECTED_REMAINING_BLOCKERS,
        "remaining blockers",
    )
    validate_packet_manifest(authority["packets"])
    return authority


def load_authority(repo=REPO_ROOT, explicit=None):
    path = Path(explicit) if explicit is not None else Path(repo) / AUTHORITY_PATH
    data = read_regular_file_once(path, "review-campaign authority", MAX_AUTHORITY_BYTES)
    if not HEX_SHA256.fullmatch(AUTHORITY_SHA256):
        raise ReviewCampaignError("review-campaign authority digest has not been frozen")
    if hashlib.sha256(data).hexdigest() != AUTHORITY_SHA256:
        raise ReviewCampaignError("review-campaign authority digest differs")
    return validate_authority(
        read_json_bytes(data, "review-campaign authority", canonical=True)
    )


def load_batch_checker(repo, authority):
    inputs = authority["inputs"]
    checker_path, checker_data = _read_bound(
        repo, inputs["batch_checker"], "frozen review-batch checker"
    )
    batch_authority_path, _ = _read_bound(
        repo,
        inputs["batch_authority"],
        "frozen review-batch authority",
        MAX_AUTHORITY_BYTES,
    )
    for key, label in (
        ("batch_tests", "frozen review-batch tests"),
        ("batch_workflow", "frozen review-batch workflow"),
        ("campaign_workflow", "frozen review-campaign workflow"),
        ("decision_authority", "frozen decision authority"),
        ("decision_checker", "frozen decision checker"),
        ("queue_authority", "frozen review-queue authority"),
        ("queue_checker", "frozen review-queue checker"),
        ("source_lock", "frozen source lock"),
        ("source_lock_validator", "frozen source-lock validator"),
    ):
        _read_bound(repo, inputs[key], label)
    module = types.ModuleType("_rk001_frozen_review_batch")
    module.__file__ = str(checker_path)
    module.__package__ = None
    try:
        code = compile(checker_data, str(checker_path), "exec", dont_inherit=True)
        exec(code, module.__dict__)
    except (Exception, MemoryError) as error:
        raise ReviewCampaignError("cannot execute frozen review-batch checker: {0}".format(error))
    require_exact(module.AUTHORITY_SHA256, BATCH_AUTHORITY["sha256"], "batch authority digest")
    require_exact(
        str(module.AUTHORITY_PATH).replace("\\", "/"),
        BATCH_AUTHORITY["path"],
        "batch authority path",
    )
    require_exact(module.BATCH_ID, BATCH_AUTHORITY["batch_id"], "batch ID")
    try:
        batch_authority = module.load_authority(Path(repo).resolve(), batch_authority_path)
    except module.ReviewBatchError as error:
        raise ReviewCampaignError("frozen review-batch authority rejected: {0}".format(error))
    return module, batch_authority


def stream_bytes(records):
    return b"".join(canonical_json(record, newline=True) for record in records)


def measure_stream(records, label, cap=MAX_FULL_STREAM_BYTES):
    digest = hashlib.sha256()
    total = 0
    for record in records:
        data = canonical_json(record, newline=True)
        total += len(data)
        if total > cap:
            raise ReviewCampaignError("{0} exceeds its byte cap".format(label))
        digest.update(data)
    return total, digest.hexdigest()


def id_stream(module, key, values):
    records = [{key: value} for value in values]
    data = b"".join(module.canonical_json(record, newline=True) for record in records)
    return len(data), hashlib.sha256(data).hexdigest()


def packet_row(module, group_index, packet_id, lane, group_ids, units, materialized=None, omitted=0):
    group_ids = sorted(group_ids)
    units = sorted(units, key=lambda unit: unit["evidence"]["path"])
    content = sum(group_index[group_id]["identity"]["size"] for group_id in group_ids)
    group_bytes, group_sha = id_stream(module, "group_id", group_ids)
    unit_bytes, unit_sha = id_stream(
        module, "unit_id", [unit["unit_id"] for unit in units]
    )
    return {
        "content_bytes": content,
        "first_group_id": group_ids[0] if group_ids else None,
        "group_count": len(group_ids),
        "group_id_stream_bytes": group_bytes,
        "group_id_stream_sha256": group_sha,
        "lane": lane,
        "last_group_id": group_ids[-1] if group_ids else None,
        "materialized_content_bytes": content if materialized is None else materialized,
        "metadata_only_content_bytes": omitted,
        "packet_id": packet_id,
        "path_set_sha256": module.path_set_sha256(
            [unit["evidence"]["path"] for unit in units]
        ),
        "unit_count": len(units),
        "unit_id_stream_bytes": unit_bytes,
        "unit_id_stream_sha256": unit_sha,
    }


def derive_archive_expansion_bindings(
    module, decision_authority, group_index, units, archive_ids
):
    roles = {
        SPECIAL_ARCHIVE_GROUP_IDS[0]: (
            "existing-inventory-closure",
            "review-existing-frozen-linux-child-units-and-container-context",
        ),
        SPECIAL_ARCHIVE_GROUP_IDS[1]: (
            "future-v2-child-inventory-required",
            "expand-and-capture-future-v2-child-inventory-before-any-closure-response",
        ),
        SPECIAL_ARCHIVE_GROUP_IDS[2]: (
            "future-v2-child-inventory-required",
            "expand-and-capture-future-v2-child-inventory-before-any-closure-response",
        ),
    }
    if sorted(archive_ids) != SPECIAL_ARCHIVE_GROUP_IDS:
        raise ReviewCampaignError("archive expansion group closure differs")
    capture_closure = decision_authority["capture"]["namespace_closures"]["linux"]
    require_exact(
        capture_closure,
        LINUX_CAPTURE_AUTHORITY_RECORD,
        "Linux capture namespace closure",
    )
    units_by_group = collections.defaultdict(list)
    for unit in units:
        if unit["exact_content_group_id"] is not None:
            units_by_group[unit["exact_content_group_id"]].append(unit)
    records = []
    for group_id in SPECIAL_ARCHIVE_GROUP_IDS:
        group = group_index[group_id]
        container_units = units_by_group[group_id]
        if len(container_units) != 1 or group["path_count"] != 1:
            raise ReviewCampaignError("archive container does not have one exact unit")
        unit = container_units[0]
        identity = group["identity"]
        role, action = roles[group_id]
        child_inventory = None
        if role == "existing-inventory-closure":
            child_units = [
                candidate
                for candidate in units
                if candidate["evidence"]["namespace"] == "linux"
            ]
            expected_source_identity = {"archive_sha256": identity["sha256"]}
            if not child_units or any(
                candidate["evidence"]["source_identity"] != expected_source_identity
                for candidate in child_units
            ):
                raise ReviewCampaignError("Linux child inventory source binding differs")
            child_group_ids = sorted(
                {
                    candidate["exact_content_group_id"]
                    for candidate in child_units
                    if candidate["exact_content_group_id"] is not None
                }
            )
            group_bytes, group_sha = id_stream(
                module, "group_id", child_group_ids
            )
            unit_bytes, unit_sha = id_stream(
                module,
                "unit_id",
                [candidate["unit_id"] for candidate in child_units],
            )
            decision_counts = collections.Counter(
                candidate["decision"] for candidate in child_units
            )
            child_inventory = {
                "capture_namespace_closure": {
                    "complete": capture_closure["complete"],
                    "item_count": capture_closure["item_count"],
                    "path_set_algorithm": "utf8-path-newline",
                    "path_set_sha256": capture_closure["path_set_sha256"],
                    "source_closure_path_set_sha256": capture_closure[
                        "path_set_sha256"
                    ],
                    "source_manifest_algorithm": "canonical-json-source-rows",
                    "source_manifest_sha256": capture_closure[
                        "source_manifest_sha256"
                    ],
                },
                "derived_review_closure": {
                    "content_group_count": len(child_group_ids),
                    "content_group_id_stream_algorithm": "canonical-json-group-id-rows",
                    "content_group_id_stream_bytes": group_bytes,
                    "content_group_id_stream_sha256": group_sha,
                    "decision_counts": {
                        MACHINE: decision_counts[MACHINE],
                        UNRESOLVED: decision_counts[UNRESOLVED],
                    },
                    "namespace": "linux",
                    "path_set_algorithm": "canonical-json-path-rows",
                    "path_set_sha256": module.path_set_sha256(
                        [candidate["evidence"]["path"] for candidate in child_units]
                    ),
                    "referenced_content_bytes": sum(
                        group_index[child_group_id]["identity"]["size"]
                        for child_group_id in child_group_ids
                    ),
                    "regular_unit_count": sum(
                        candidate["evidence"]["entry_type"] == "regular"
                        for candidate in child_units
                    ),
                    "review_state": REVIEW_STATE,
                    "review_unit_count": len(child_units),
                    "review_unit_id_stream_algorithm": "canonical-json-unit-id-rows",
                    "review_unit_id_stream_bytes": unit_bytes,
                    "review_unit_id_stream_sha256": unit_sha,
                    "source_identity": expected_source_identity,
                    "symlink_unit_count": sum(
                        candidate["evidence"]["entry_type"] == "symlink"
                        for candidate in child_units
                    ),
                },
            }
        records.append(
            {
                "attachment_alone_credit_eligible": False,
                "attachment_alone_counts_as_reviewed": False,
                "child_inventory": child_inventory,
                "child_review_complete": False,
                "container": {
                    "group_id": group_id,
                    "path": unit["evidence"]["path"],
                    "sha256": identity["sha256"],
                    "size": identity["size"],
                    "unit_id": unit["unit_id"],
                },
                "container_review_state": REVIEW_STATE,
                "required_next_action": action,
                "role": role,
            }
        )
    return records


def derive_campaign(repo, artifact_path, authority):
    batch, batch_authority = load_batch_checker(repo, authority)
    artifact_data = read_regular_file_once(
        artifact_path, "exact inventory artifact", MAX_ARTIFACT_BYTES
    )
    if (
        len(artifact_data) != INVENTORY_ARTIFACT["size"]
        or hashlib.sha256(artifact_data).hexdigest() != INVENTORY_ARTIFACT["sha256"]
    ):
        raise ReviewCampaignError("exact inventory artifact bytes differ")
    try:
        module, queue_authority = batch.load_queue_checker(repo, batch_authority)
        decision, decision_authority, compressed, decision_result = module.load_exact_inventory(
            Path(repo).resolve(), Path(artifact_path), queue_authority
        )
        if (
            len(compressed) != INVENTORY_MEMBER["size"]
            or hashlib.sha256(compressed).hexdigest() != INVENTORY_MEMBER["sha256"]
        ):
            raise ReviewCampaignError("exact inventory member bytes differ")
        queue_result, queue_records = module.analyze_review_queue(
            compressed, decision, decision_authority
        )
        module.require_exact(
            queue_result,
            queue_authority["expected_result"],
            "exact frozen review queue",
        )
    except module.ReviewQueueError as error:
        raise ReviewCampaignError("frozen review queue rejected: {0}".format(error))
    except decision.DecisionError as error:
        raise ReviewCampaignError("frozen decision checker rejected inventory: {0}".format(error))

    candidate_ids = {
        unit["evidence"]["path"]: unit["candidate_directory_signal_id"]
        for unit in queue_records["review-units"]
    }
    unresolved_units = {
        unit["evidence"]["path"]: unit for unit in queue_records["review-units"]
    }
    known = decision.catalog(decision_authority)
    grouped = {}
    units = []
    special_ids = set()
    archive_ids = set()
    namespace_decisions = collections.defaultdict(collections.Counter)
    regular_count = 0
    symlink_count = 0
    previous_path = None
    try:
        for line in decision.bounded_gzip_lines(compressed):
            item = decision.read_json_bytes(line, "campaign inventory row", canonical=True)
            namespace = decision.validate_item(item)
            module.validate_source_identity(
                item["source_identity"], namespace, "campaign source identity"
            )
            path = item["path"]
            if previous_path is not None and path <= previous_path:
                raise ReviewCampaignError("inventory paths are duplicate or unsorted")
            previous_path = path
            classified = decision.classify_item(item, known)
            namespace_decisions[namespace][classified["decision"]] += 1
            parent = module.parent_directory(path)
            context = {
                "entry_type": item["entry_type"],
                "namespace": namespace,
                "origin": item["origin"],
                "parent_directory": parent,
                "source_identity": item["source_identity"],
            }
            reason = {
                "basis": classified["basis"],
                "unresolved_reasons": list(item["unresolved_reasons"]),
            }
            if item["entry_type"] == "regular":
                regular_count += 1
                identity = {
                    "entry_type": "regular",
                    "sha256": item["sha256"],
                    "size": item["size"],
                }
                group_id = module.stable_id("exact-content", identity)
                grouped_record = grouped.get(group_id)
                if grouped_record is None:
                    grouped_record = {
                        "decision": classified["decision"],
                        "identity": identity,
                        "paths": [],
                    }
                    grouped[group_id] = grouped_record
                require_exact(grouped_record["identity"], identity, "content identity")
                require_exact(
                    grouped_record["decision"],
                    classified["decision"],
                    "content-group decision separation",
                )
                grouped_record["paths"].append(path)
                if classified["basis"] == SPECIAL_BASIS:
                    special_ids.add(group_id)
                if path.lower().endswith(ARCHIVE_SUFFIXES):
                    archive_ids.add(group_id)
            else:
                symlink_count += 1
                group_id = None
            payload = {
                "basis": classified["basis"],
                "candidate_directory_signal_id": candidate_ids.get(path),
                "capture_review_status": item["review_status"],
                "context_group_id": module.stable_id("context", context),
                "decision": classified["decision"],
                "evidence": {
                    "authorship_signals": list(item["authorship_signals"]),
                    "entry_type": item["entry_type"],
                    "license_text_paths": list(item["license_text_paths"]),
                    "link_target": item["link_target"],
                    "namespace": namespace,
                    "origin": item["origin"],
                    "parent_directory": parent,
                    "path": path,
                    "sha256": item["sha256"],
                    "size": item["size"],
                    "source_identity": item["source_identity"],
                    "spdx_expression": item["spdx_expression"],
                    "unresolved_reasons": list(item["unresolved_reasons"]),
                },
                "exact_content_group_id": group_id,
                "reason_cluster_id": module.stable_id("reason", reason),
                "review_state": REVIEW_STATE,
            }
            record = dict(payload)
            record["unit_id"] = module.stable_id("review-unit", payload)
            frozen = unresolved_units.get(path)
            if classified["decision"] == UNRESOLVED:
                if frozen is None:
                    raise ReviewCampaignError("unresolved unit is absent from frozen queue")
                module.require_exact(record, frozen, "frozen unresolved unit")
                record = frozen
            elif record["candidate_directory_signal_id"] is not None:
                raise ReviewCampaignError("machine-classified unit gained a candidate signal")
            units.append(record)
    except decision.DecisionError as error:
        raise ReviewCampaignError("campaign inventory derivation rejected: {0}".format(error))

    groups = []
    for group_id, grouped_record in grouped.items():
        paths = grouped_record["paths"]
        groups.append(
            {
                "decision_class": grouped_record["decision"],
                "group_id": group_id,
                "identity": grouped_record["identity"],
                "path_count": len(paths),
                "path_set_sha256": module.path_set_sha256(paths),
                "review_state": REVIEW_STATE,
            }
        )
    groups.sort(key=lambda group: group["group_id"])
    if [unit["evidence"]["path"] for unit in units] != sorted(
        unit["evidence"]["path"] for unit in units
    ):
        raise ReviewCampaignError("campaign units are not in inventory path order")
    if len({unit["unit_id"] for unit in units}) != len(units):
        raise ReviewCampaignError("campaign unit IDs are duplicated")
    if set(unresolved_units) != {
        unit["evidence"]["path"] for unit in units if unit["decision"] == UNRESOLVED
    }:
        raise ReviewCampaignError("frozen unresolved-unit closure differs")

    group_index = {group["group_id"]: group for group in groups}
    units_by_group = collections.defaultdict(list)
    symlink_units = []
    for unit in units:
        group_id = unit["exact_content_group_id"]
        if group_id is None:
            symlink_units.append(unit)
        else:
            if group_id not in group_index:
                raise ReviewCampaignError("unit references an unknown content group")
            units_by_group[group_id].append(unit)
    if set(units_by_group) != set(group_index):
        raise ReviewCampaignError("content-group/unit closure differs")
    for group_id, group in group_index.items():
        paths = [unit["evidence"]["path"] for unit in units_by_group[group_id]]
        require_exact(len(paths), group["path_count"], "content-group path count")
        require_exact(
            module.path_set_sha256(paths), group["path_set_sha256"], "content-group path set"
        )
        for unit in units_by_group[group_id]:
            require_exact(unit["decision"], group["decision_class"], "group decision class")
            require_exact(
                {
                    "entry_type": unit["evidence"]["entry_type"],
                    "sha256": unit["evidence"]["sha256"],
                    "size": unit["evidence"]["size"],
                },
                group["identity"],
                "group/unit content identity",
            )

    try:
        _, batch_groups, batch_units = batch.select_batch(module, queue_records)
    except batch.ReviewBatchError as error:
        raise ReviewCampaignError("preserved review batch rejected: {0}".format(error))
    reserved = {group["group_id"] for group in batch_groups}
    if reserved & special_ids or archive_ids - special_ids:
        raise ReviewCampaignError("preserved/special/archive partition differs")

    packets = []
    packet_groups = {}
    packet_units = {}
    batch_ids = [group["group_id"] for group in batch_groups]
    preserved_units = [
        next(unit for unit in units if unit["evidence"]["path"] == frozen["evidence"]["path"])
        for frozen in batch_units
    ]
    packets.append(
        packet_row(
            module,
            group_index,
            "0001",
            "preserved-review-batch-0001",
            batch_ids,
            preserved_units,
        )
    )
    packet_groups["0001"] = batch_groups
    packet_units["0001"] = batch_units
    remaining = sorted(
        group_id
        for group_id in group_index
        if group_id not in reserved and group_id not in special_ids
    )
    chunks = [remaining[index : index + GROUP_LIMIT] for index in range(0, len(remaining), GROUP_LIMIT)]
    for number, group_ids in enumerate(chunks, 2):
        selected_units = sorted(
            [unit for group_id in group_ids for unit in units_by_group[group_id]],
            key=lambda unit: unit["evidence"]["path"],
        )
        packet_id = "{0:04d}".format(number)
        packets.append(
            packet_row(
                module,
                group_index,
                packet_id,
                EXPECTED_PARTITION_POLICY["ordinary_lane"],
                group_ids,
                selected_units,
            )
        )
        packet_groups[packet_id] = [group_index[group_id] for group_id in group_ids]
        packet_units[packet_id] = selected_units
    special_units = sorted(
        [unit for group_id in special_ids for unit in units_by_group[group_id]],
        key=lambda unit: unit["evidence"]["path"],
    )
    omitted = sum(group_index[group_id]["identity"]["size"] for group_id in archive_ids)
    special_packet_id = "{0:04d}".format(len(packets) + 1)
    packets.append(
        packet_row(
            module,
            group_index,
            special_packet_id,
            EXPECTED_PARTITION_POLICY["special_lane"],
            special_ids,
            special_units,
            materialized=sum(
                group_index[group_id]["identity"]["size"]
                for group_id in special_ids
                if group_id not in archive_ids
            ),
            omitted=omitted,
        )
    )
    packet_groups[special_packet_id] = [group_index[group_id] for group_id in sorted(special_ids)]
    packet_units[special_packet_id] = special_units
    symlink_packet_id = "{0:04d}".format(len(packets) + 1)
    packets.append(
        packet_row(
            module,
            group_index,
            symlink_packet_id,
            EXPECTED_PARTITION_POLICY["symlink_lane"],
            [],
            symlink_units,
            materialized=0,
            omitted=0,
        )
    )
    packet_groups[symlink_packet_id] = []
    packet_units[symlink_packet_id] = symlink_units

    group_bytes, group_sha = measure_stream(groups, "full content-group stream")
    unit_bytes, unit_sha = measure_stream(units, "full review-unit stream")
    manifest_bytes, manifest_sha = measure_stream(packets, "packet manifest stream")
    decision_group_counts = collections.Counter(
        group["decision_class"] for group in groups
    )
    decision_group_bytes = collections.Counter()
    for group in groups:
        decision_group_bytes[group["decision_class"]] += group["identity"]["size"]
    duplicates = [group for group in groups if group["path_count"] > 1]
    ordinary_packets = [
        packet for packet in packets if packet["lane"] == EXPECTED_PARTITION_POLICY["ordinary_lane"]
    ]
    result = {
        "content_group_count": len(groups),
        "content_group_stream_bytes": group_bytes,
        "content_group_stream_sha256": group_sha,
        "duplicate_content_group_count": len(duplicates),
        "duplicate_content_path_count": sum(group["path_count"] for group in duplicates),
        "inventory_item_count": len(units),
        "machine_classified_content_bytes": decision_group_bytes[MACHINE],
        "machine_classified_content_group_count": decision_group_counts[MACHINE],
        "machine_classified_item_count": sum(unit["decision"] == MACHINE for unit in units),
        "materialized_content_bytes": sum(packet["materialized_content_bytes"] for packet in packets),
        "maximum_ordinary_packet_content_bytes": max(packet["content_bytes"] for packet in ordinary_packets),
        "maximum_ordinary_packet_unit_count": max(packet["unit_count"] for packet in ordinary_packets),
        "metadata_only_content_bytes": sum(packet["metadata_only_content_bytes"] for packet in packets),
        "namespace_decision_counts": {
            namespace: {
                MACHINE: namespace_decisions[namespace][MACHINE],
                UNRESOLVED: namespace_decisions[namespace][UNRESOLVED],
            }
            for namespace in ("dist-git", "linux", "repository", "srpm")
        },
        "ordinary_content_bytes": sum(packet["content_bytes"] for packet in ordinary_packets),
        "ordinary_content_group_count": sum(packet["group_count"] for packet in ordinary_packets),
        "ordinary_packet_count": len(ordinary_packets),
        "ordinary_review_unit_count": sum(packet["unit_count"] for packet in ordinary_packets),
        "packet_count": len(packets),
        "packet_manifest_stream_bytes": manifest_bytes,
        "packet_manifest_stream_sha256": manifest_sha,
        "preserved_packet_content_bytes": packets[0]["content_bytes"],
        "preserved_packet_content_group_count": packets[0]["group_count"],
        "preserved_packet_group_stream_bytes": len(stream_bytes(batch_groups)),
        "preserved_packet_group_stream_sha256": hashlib.sha256(stream_bytes(batch_groups)).hexdigest(),
        "preserved_packet_path_set_sha256": packets[0]["path_set_sha256"],
        "preserved_packet_review_unit_count": packets[0]["unit_count"],
        "preserved_packet_unit_stream_bytes": len(stream_bytes(batch_units)),
        "preserved_packet_unit_stream_sha256": hashlib.sha256(stream_bytes(batch_units)).hexdigest(),
        "referenced_content_bytes": sum(packet["content_bytes"] for packet in packets),
        "regular_item_count": regular_count,
        "review_unit_count": len(units),
        "review_unit_stream_bytes": unit_bytes,
        "review_unit_stream_sha256": unit_sha,
        "special_archive_content_bytes": omitted,
        "special_archive_group_count": len(archive_ids),
        "special_content_bytes": packets[-2]["content_bytes"],
        "special_content_group_count": packets[-2]["group_count"],
        "special_materialized_content_bytes": packets[-2]["materialized_content_bytes"],
        "special_review_unit_count": packets[-2]["unit_count"],
        "symlink_item_count": symlink_count,
        "unresolved_content_bytes": decision_group_bytes[UNRESOLVED],
        "unresolved_content_group_count": decision_group_counts[UNRESOLVED],
        "unresolved_item_count": sum(unit["decision"] == UNRESOLVED for unit in units),
    }
    require_exact(result, EXPECTED_RESULT, "exact campaign result")
    require_exact(sorted(archive_ids), SPECIAL_ARCHIVE_GROUP_IDS, "archive group IDs")
    archive_bindings = derive_archive_expansion_bindings(
        module, decision_authority, group_index, units, archive_ids
    )
    require_exact(
        archive_bindings,
        authority["archive_expansion_bindings"],
        "frozen archive expansion bindings",
    )
    require_exact(packets, authority["packets"], "frozen packet manifest")
    validate_packet_manifest(packets)
    return {
        "archive_group_ids": archive_ids,
        "archive_expansion_bindings": archive_bindings,
        "batch": batch,
        "batch_authority": batch_authority,
        "decision": decision,
        "decision_result": decision_result,
        "groups": groups,
        "module": module,
        "packet_groups": packet_groups,
        "packet_units": packet_units,
        "packets": packets,
        "queue_records": queue_records,
        "result": result,
        "units": units,
    }


def packet_summary(authority, packet):
    return {
        "campaign_id": authority["campaign_id"],
        "claims": authority["claims"],
        "gate": authority["gate"],
        "packet": packet,
        "package_policy": authority["package_policy"],
        "partition_policy": authority["partition_policy"],
        "remaining_blockers": authority["remaining_blockers"],
        "review_state": REVIEW_STATE,
        "schema_version": SCHEMA_VERSION,
        "source_commit": SOURCE_COMMIT,
    }


def expansion_records(derived, packet_id):
    if packet_id != "0218":
        return []
    records = derived["archive_expansion_bindings"]
    require_exact(
        [record["container"]["group_id"] for record in records],
        SPECIAL_ARCHIVE_GROUP_IDS,
        "expansion-required group closure",
    )
    return records


def materialized_groups(derived, packet_id):
    return [
        group
        for group in derived["packet_groups"][packet_id]
        if group["group_id"] not in derived["archive_group_ids"]
    ]


def _read_tree_member(root, relative, expected):
    safe_relative(relative, "source-tree member")
    root = Path(root)
    if os.path.abspath(str(root)) != os.path.realpath(str(root)) or not root.is_dir():
        raise ReviewCampaignError("source-tree root is not a canonical directory")
    path = root / relative
    data = read_regular_file_once(
        path, "exact source-tree member", expected["size"]
    )
    if (
        len(data) != expected["size"]
        or hashlib.sha256(data).hexdigest() != expected["sha256"]
    ):
        raise ReviewCampaignError("source-tree member bytes differ")
    return data


def materialize_packet_content(
    derived, packet_id, linux_archive, srpm_root, dist_git, repository_git
):
    batch = derived["batch"]
    groups = materialized_groups(derived, packet_id)
    units_by_group = collections.defaultdict(list)
    for unit in derived["packet_units"][packet_id]:
        if unit["exact_content_group_id"] is not None:
            units_by_group[unit["exact_content_group_id"]].append(unit)
    linux_wanted = {}
    deferred = []
    for group in groups:
        group_id = group["group_id"]
        candidates = sorted(
            units_by_group[group_id], key=lambda unit: unit["evidence"]["path"]
        )
        expected = {
            "group_id": group_id,
            "sha256": group["identity"]["sha256"],
            "size": group["identity"]["size"],
        }
        linux = [unit for unit in candidates if unit["evidence"]["namespace"] == "linux"]
        if linux:
            linux_wanted[linux[0]["evidence"]["path"]] = expected
        else:
            deferred.append((group, candidates, expected))
    blobs = {}
    if linux_wanted:
        if linux_archive is None:
            raise ReviewCampaignError("--linux-archive is required for selected Linux content")
        try:
            blobs.update(batch.read_linux_content(linux_archive, linux_wanted))
        except batch.ReviewBatchError as error:
            raise ReviewCampaignError("exact Linux content rejected: {0}".format(error))
    for group, candidates, expected in deferred:
        choices = []
        for namespace in ("dist-git", "srpm", "repository"):
            choices.extend(
                unit for unit in candidates if unit["evidence"]["namespace"] == namespace
            )
            if choices:
                break
        if not choices:
            raise ReviewCampaignError("content group has no materializable source authority")
        unit = choices[0]
        evidence = unit["evidence"]
        namespace = evidence["namespace"]
        if namespace == "dist-git":
            if dist_git is None:
                raise ReviewCampaignError("--dist-git is required for selected dist-git content")
            oid = evidence["source_identity"]["git_blob_oid"]
            try:
                data = batch.git_blob(dist_git, oid)
            except batch.ReviewBatchError as error:
                raise ReviewCampaignError("exact dist-git blob rejected: {0}".format(error))
        elif namespace == "repository":
            if repository_git is None:
                raise ReviewCampaignError("--repository-git is required for selected repository content")
            identity = evidence["source_identity"]
            require_exact(identity["git_commit"], SOURCE_COMMIT, "repository source commit")
            try:
                data = batch.git_blob(repository_git, identity["git_blob_oid"])
            except batch.ReviewBatchError as error:
                raise ReviewCampaignError("exact repository blob rejected: {0}".format(error))
        else:
            if srpm_root is None:
                raise ReviewCampaignError("--srpm-root is required for selected SRPM content")
            source_digest = evidence["source_identity"]["source_rpm_sha256"]
            require_exact(
                source_digest,
                "2bfeda65bd9bdd4b86650074c81e061c37822b80317ac0d4f5aacc89c85589cb",
                "SRPM source identity",
            )
            data = _read_tree_member(
                srpm_root, evidence["path"][len("srpm/") :], expected
            )
        if (
            len(data) != expected["size"]
            or hashlib.sha256(data).hexdigest() != expected["sha256"]
        ):
            raise ReviewCampaignError("materialized content bytes differ")
        blobs[group["group_id"]] = data
    if set(blobs) != {group["group_id"] for group in groups}:
        raise ReviewCampaignError("materialized content closure differs")
    return blobs


def packet_metadata_files(authority, derived, packet_id):
    packet = derived["packets"][int(packet_id) - 1]
    groups = derived["packet_groups"][packet_id]
    units = derived["packet_units"][packet_id]
    return {
        "content-groups.jsonl": stream_bytes(groups),
        "expansion-required.jsonl": stream_bytes(expansion_records(derived, packet_id)),
        "packet-summary.json": canonical_json(packet_summary(authority, packet), newline=True),
        "review-units.jsonl": stream_bytes(units),
    }


def package_files(authority, derived, packet_id, blobs):
    values = packet_metadata_files(authority, derived, packet_id)
    expected_groups = materialized_groups(derived, packet_id)
    for group in expected_groups:
        data = blobs.get(group["group_id"])
        identity = group["identity"]
        if (
            type(data) is not bytes
            or len(data) != identity["size"]
            or hashlib.sha256(data).hexdigest() != identity["sha256"]
        ):
            raise ReviewCampaignError("packet content blob identity differs")
        name = "content/" + identity["sha256"]
        if name in values and values[name] != data:
            raise ReviewCampaignError("packet content digest collision")
        values[name] = data
    if len([name for name in values if name.startswith("content/")]) != len(expected_groups):
        raise ReviewCampaignError("packet content member closure differs")
    packet = derived["packets"][int(packet_id) - 1]
    if sum(len(data) for name, data in values.items() if name.startswith("content/")) != packet[
        "materialized_content_bytes"
    ]:
        raise ReviewCampaignError("packet materialized-byte closure differs")
    return values


def publish_package(batch, output_dir, files):
    try:
        batch.publish_package(output_dir, files)
    except batch.ReviewBatchError as error:
        raise ReviewCampaignError("cannot publish campaign packet: {0}".format(error))


def _expected_content_members(derived, packet_id):
    values = {}
    for group in materialized_groups(derived, packet_id):
        identity = group["identity"]
        name = "content/" + identity["sha256"]
        if name in values and values[name] != identity["size"]:
            raise ReviewCampaignError("content digest/size collision")
        values[name] = identity["size"]
    return values


def _package_preflight(catalog, metadata, content, packet):
    expected_names = set(metadata) | set(content) | {"SHA256SUMS"}
    if set(catalog) != expected_names:
        raise ReviewCampaignError("packet member closure differs")
    for name, record in catalog.items():
        info = record["info"]
        if not stat.S_ISREG(info.st_mode):
            raise ReviewCampaignError("packet member is not regular")
        if stat.S_IMODE(info.st_mode) != 0o444:
            raise ReviewCampaignError("packet member mode differs")
        if info.st_nlink != 1:
            raise ReviewCampaignError("packet member is hardlinked")
        if name.startswith("content/") and not HEX_SHA256.fullmatch(name[len("content/") :]):
            raise ReviewCampaignError("packet content filename is malformed")
    expected_sizes = {name: len(data) for name, data in metadata.items()}
    expected_sizes.update(content)
    manifest_names = sorted(set(metadata) | set(content))
    expected_sizes["SHA256SUMS"] = sum(
        64 + 2 + len(name.encode("ascii")) + 1 for name in manifest_names
    )
    for name, expected_size in expected_sizes.items():
        if catalog[name]["info"].st_size != expected_size:
            raise ReviewCampaignError("packet member size differs: {0}".format(name))
    total = sum(expected_sizes.values())
    if total > MAX_PACKAGE_BYTES:
        raise ReviewCampaignError("packet aggregate size exceeds its cap")
    if sum(content.values()) != packet["materialized_content_bytes"]:
        raise ReviewCampaignError("packet content preflight closure differs")
    for size in content.values():
        if size > MAX_CONTENT_BYTES:
            raise ReviewCampaignError("packet content member exceeds its cap")
    return total


def read_packet_package(batch, directory, metadata, content, packet):
    try:
        context, catalog = batch._open_package_catalog(directory)
    except batch.ReviewBatchError as error:
        raise ReviewCampaignError("cannot open packet package: {0}".format(error))
    try:
        expected_total = _package_preflight(catalog, metadata, content, packet)
        batch._replay_package_namespace(context, catalog)
        files = {}
        retained = 0
        for relative in sorted(catalog):
            batch._verify_package_roots(context)
            record = catalog[relative]
            batch._verify_package_member(record)
            remaining = MAX_PACKAGE_BYTES - retained
            if remaining <= 0:
                raise ReviewCampaignError(
                    "packet retention cap is exhausted before the next member"
                )
            cap = MAX_CONTENT_BYTES if relative.startswith("content/") else MAX_PACKET_STREAM_BYTES
            data = batch._read_open_regular_descriptor(
                record,
                "campaign packet member " + relative,
                min(cap, remaining),
            )
            retained += len(data)
            if retained > MAX_PACKAGE_BYTES:
                raise ReviewCampaignError("packet retained bytes exceed their cap")
            batch._verify_package_roots(context)
            batch._verify_package_member(record)
            files[relative] = data
        batch._replay_package_namespace(context, catalog)
        if retained != expected_total:
            raise ReviewCampaignError("packet retained-byte closure differs")
        return files
    except batch.ReviewBatchError as error:
        raise ReviewCampaignError("packet namespace or member rejected: {0}".format(error))
    finally:
        batch._close_package_catalog(context, catalog)


def verify_package(authority, derived, packet_id, directory):
    batch = derived["batch"]
    packet = derived["packets"][int(packet_id) - 1]
    metadata = packet_metadata_files(authority, derived, packet_id)
    content = _expected_content_members(derived, packet_id)
    files = read_packet_package(batch, directory, metadata, content, packet)
    expected_names = set(metadata) | set(content) | {"SHA256SUMS"}
    require_exact(set(files), expected_names, "verified packet member closure")
    for name, expected in metadata.items():
        require_exact(files[name], expected, "packet metadata member " + name)
    expected_manifest = batch.checksum_manifest(
        {name: data for name, data in files.items() if name != "SHA256SUMS"}
    )
    require_exact(files["SHA256SUMS"], expected_manifest, "packet checksum manifest")
    for name, expected_size in content.items():
        data = files[name]
        require_exact(len(data), expected_size, "packet content size")
        require_exact(
            hashlib.sha256(data).hexdigest(),
            name[len("content/") :],
            "packet content digest",
        )
    return packet_summary(authority, packet)


def validate_packet_id(value):
    if type(value) is not str or not PACKET_ID_PATTERN.fullmatch(value):
        raise ReviewCampaignError("packet ID must be four decimal digits")
    number = int(value, 10)
    if number < 1 or number > EXPECTED_RESULT["packet_count"]:
        raise ReviewCampaignError("packet ID is outside the frozen campaign")
    return value


def parser(argv=None):
    value = argparse.ArgumentParser(description=__doc__)
    value.add_argument("--repo", default=REPO_ROOT, type=Path)
    value.add_argument("--authority", type=Path)
    modes = value.add_mutually_exclusive_group(required=True)
    modes.add_argument("--check", action="store_true")
    modes.add_argument("--build-packet", action="store_true")
    modes.add_argument("--verify-package", type=Path)
    modes.add_argument(
        "--emit",
        choices=("content-groups", "review-units", "packet-manifest", "packet-summary"),
    )
    value.add_argument("--artifact", type=Path)
    value.add_argument("--packet-id")
    value.add_argument("--linux-archive", type=Path)
    value.add_argument("--srpm-root", type=Path)
    value.add_argument("--dist-git", type=Path)
    value.add_argument("--repository-git", type=Path)
    value.add_argument("--output-dir", type=Path)
    return value.parse_args(argv)


def main(argv=None):
    args = parser(argv)
    try:
        repo = args.repo.resolve()
        authority = load_authority(repo, args.authority)
        if args.check:
            load_batch_checker(repo, authority)
            print(
                "RK-001 review campaign contract verified: packets=219 groups=111004 "
                "units=115265 reviewed=false durable=false gate=TODO points=0 credit=false"
            )
            return 0
        if args.artifact is None:
            raise ReviewCampaignError("--artifact is required for derivation and package modes")
        derived = derive_campaign(repo, args.artifact, authority)
        packet_id = None
        if args.build_packet or args.verify_package is not None or args.emit == "packet-summary":
            packet_id = validate_packet_id(args.packet_id)
        if args.emit:
            if args.emit == "content-groups":
                sys.stdout.buffer.write(stream_bytes(derived["groups"]))
            elif args.emit == "review-units":
                sys.stdout.buffer.write(stream_bytes(derived["units"]))
            elif args.emit == "packet-manifest":
                sys.stdout.buffer.write(stream_bytes(derived["packets"]))
            else:
                packet = derived["packets"][int(packet_id) - 1]
                sys.stdout.buffer.write(canonical_json(packet_summary(authority, packet), newline=True))
            return 0
        if args.verify_package is not None:
            verify_package(authority, derived, packet_id, args.verify_package)
            print(
                "RK-001 campaign packet verified: packet={0} reviewed=false "
                "durable=false gate=TODO points=0 credit=false".format(packet_id)
            )
            return 0
        if args.output_dir is None:
            raise ReviewCampaignError("--output-dir is required for --build-packet")
        blobs = materialize_packet_content(
            derived,
            packet_id,
            args.linux_archive,
            args.srpm_root,
            args.dist_git,
            args.repository_git,
        )
        files = package_files(authority, derived, packet_id, blobs)
        publish_package(derived["batch"], args.output_dir, files)
        verify_package(authority, derived, packet_id, args.output_dir)
        packet = derived["packets"][int(packet_id) - 1]
        print(
            "RK-001 campaign packet built: packet={0} groups={1} units={2} "
            "content_bytes={3} reviewed=false durable=false gate=TODO points=0 credit=false".format(
                packet_id,
                packet["group_count"],
                packet["unit_count"],
                packet["content_bytes"],
            )
        )
        return 0
    except ReviewCampaignError as error:
        print("RK-001 review-campaign error: {0}".format(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
