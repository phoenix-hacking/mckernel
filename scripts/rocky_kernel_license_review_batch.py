#!/usr/bin/env python3
"""Build and verify bounded, non-crediting RK-001 review batch 0001.

This checker derives the batch only from the exact ef58860e inventory and the
digest-locked review-queue checker.  It packages source bytes for human review;
it does not create reviewer decisions, legal conclusions, redistribution
approval, durable evidence, or RK-001 tracker credit.
"""

from __future__ import print_function

import argparse
import collections
import ctypes
import errno
import hashlib
import json
import os
import platform
import shutil
import stat
import subprocess
import sys
import tarfile
import tempfile
import types
from pathlib import Path, PurePosixPath


REPO_ROOT = Path(__file__).resolve().parents[1]
AUTHORITY_PATH = Path(
    "host-kernel/rocky/evidence/"
    "rk001-license-review-batch-ef58-0001-contract-v1.json"
)
AUTHORITY_SHA256 = "e253bfe2ec251cae7f9cd41ebf8df41ad10baa671a755abc89bfc33d19525e9b"
SCHEMA_VERSION = 1
BATCH_ID = "rk-001-license-review-batch-ef58860e-0001-v1"
QUEUE_ID = "rk-001-license-review-queue-ef58860e-v1"
SOURCE_COMMIT = "ef58860e4806ee16e2c506e4e93c7b6ad8ad8f4b"
GROUP_LIMIT = 512

MAX_AUTHORITY_BYTES = 1024 * 1024
MAX_CHECKER_BYTES = 2 * 1024 * 1024
MAX_SOURCE_LOCK_BYTES = 1024 * 1024
MAX_ARTIFACT_BYTES = 8 * 1024 * 1024
MAX_STREAM_BYTES = 16 * 1024 * 1024
MAX_STREAM_RECORDS = 10000
MAX_JSON_NESTING = 64
MAX_JSON_NUMBER_TOKEN = 128
MAX_PACKAGE_FILES = 1024
MAX_CONTENT_BYTES = 16 * 1024 * 1024
MAX_PACKAGE_BYTES = 4 * 1024 * 1024
MAX_TAR_MEMBERS = 200000
MAX_TAR_LOGICAL_BYTES = 8 * 1024 * 1024 * 1024

HEX_SHA256 = __import__("re").compile(r"^[0-9a-f]{64}$")
HEX_SHA1 = __import__("re").compile(r"^[0-9a-f]{40}$")

QUEUE_AUTHORITY = {
    "path": "host-kernel/rocky/evidence/rk001-license-review-queue-ef58-v1.json",
    "queue_id": QUEUE_ID,
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
WORKFLOW = {
    "path": ".github/workflows/rk001-license-review-batch-v1.yml",
    "sha256": "aca51e886f5cacca15596b35ce31c4468c0a60618226d5fd7edbd4ebcbac8d6d",
    "size": 13199,
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
LINUX_ARCHIVE = {
    "name": "linux-6.12.0-211.44.1.el10_2.tar.xz",
    "sha256": "4a174d47b8874a2139efcd1ac1ab2d6b80ae7a0ca62f0ae4596fd20cf62a3533",
    "size": 153374592,
    "top_directory": "linux-6.12.0-211.44.1.el10_2",
}
DIST_GIT = {
    "commit": "e4cad646580f7f3dfec5e3b6b4ea9e89b7572f6c",
    "repository_url": "https://git.rockylinux.org/staging/rpms/kernel.git",
}

EXPECTED_INPUTS = {
    "decision_authority": DECISION_AUTHORITY,
    "decision_checker": DECISION_CHECKER,
    "inventory_artifact": INVENTORY_ARTIFACT,
    "inventory_member": INVENTORY_MEMBER,
    "queue_authority": QUEUE_AUTHORITY,
    "queue_checker": QUEUE_CHECKER,
    "source_lock": SOURCE_LOCK,
    "workflow": WORKFLOW,
}
EXPECTED_CLAIMS = {
    "complete": False,
    "credit_eligible": False,
    "durable_archive": False,
    "independent_legal_review_complete": False,
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
EXPECTED_SELECTION_POLICY = {
    "eligible_basis": "missing-spdx-needs-review",
    "eligible_entry_type": "regular",
    "eligible_group_minimum_path_count": 2,
    "eligible_reasons_policy": "all-group-units-have-one-identical-exact-reason-list",
    "emit_group_order": "group-id-ascending",
    "emit_unit_order": "inventory-path-order",
    "group_limit": GROUP_LIMIT,
    "ranking": ["path-count-descending", "group-id-ascending"],
    "selection_auto_resolves": False,
}
EXPECTED_PACKAGE_POLICY = {
    "checksum_manifest": "SHA256SUMS",
    "content_directory": "content",
    "content_filename": "lowercase-sha256",
    "content_group_stream": "content-groups.jsonl",
    "content_group_stream_schema": "frozen-review-queue-exact-content-group-v1",
    "content_member_count": GROUP_LIMIT,
    "descriptor_rooted_reads": True,
    "member_order": "bytewise-name-ascending",
    "maximum_package_bytes": MAX_PACKAGE_BYTES,
    "namespace_replay": "root-and-member-identities-before-during-and-after-retention",
    "review_unit_stream": "review-units.jsonl",
    "review_unit_stream_schema": "frozen-review-queue-review-unit-v1",
    "summary": "batch-summary.json",
}
EXPECTED_RESULT = {
    "boundary_group_id": "exact-content:c356e20329fcbe1a343e7c7f008dc3232ba56ad802e570d06a9852f2a5ab0d9d",
    "candidate_signal_unit_count": 62,
    "content_group_count": 512,
    "content_group_stream_bytes": 184917,
    "content_group_stream_sha256": "a1a5ed89800a35ca9fbbe59074628ef62e6f90f0a27da38078e2f96596146710",
    "context_group_count": 128,
    "maximum_content_size": 12089,
    "namespace_review_unit_counts": {
        "dist-git": 6,
        "linux": 2084,
        "repository": 0,
        "srpm": 6,
    },
    "review_unit_count": 2096,
    "review_unit_stream_bytes": 2555534,
    "review_unit_stream_sha256": "c6c02b9da1dbda617ff057cbd8e2bb630ded1b35920c3ba2869b186f85cf19c2",
    "selected_path_set_sha256": "8b13ad470f0e56acc6c7cf6e01bc47aebfc4eb1ed8c45b8b9b6df8d39b96e7cd",
    "unique_content_bytes": 81202,
}
EXPECTED_FUTURE_DECISION_SCHEMA = {
    "acceptance": "all-independent-reviewer-fields-affirmative-and-signed-response-root-valid",
    "content_finding_fields": [
        "content_sha256",
        "reviewer_identity",
        "spdx_expression_or_unresolved",
        "support_references",
    ],
    "group_auto_resolves_units": False,
    "implemented_by_this_batch": False,
    "signed_response_root_required": True,
    "unit_decision_fields": [
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
        "signed_response_root",
    ],
}
EXPECTED_REMAINING_BLOCKERS = [
    "This batch is unreviewed review input only; it contains no reviewer decisions, attestations, or signatures.",
    "A content finding never automatically resolves paths that share bytes; every unit requires an independent path/context decision.",
    "The remaining review queue and all 72616 machine-classified inventory units remain outside this bounded batch.",
    "Two embedded source archives remain unexpanded and require a future exhaustive v2 inventory capture.",
    "The temporary Actions artifact is not a durable archive.",
    "The source lock and tracker remain unchanged until all 115265 inventory units are covered, unresolved count is zero, independent review is complete, and durable authority is registered.",
]


class ReviewBatchError(RuntimeError):
    """Raised when a batch authority, input, or package fails closed."""


def reject_duplicate_pairs(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ReviewBatchError("duplicate JSON key: {0}".format(key))
        value[key] = item
    return value


def parse_bounded_json_int(token):
    if type(token) is not str or len(token) > MAX_JSON_NUMBER_TOKEN:
        raise ReviewBatchError("JSON integer token exceeds its cap")
    try:
        return int(token, 10)
    except ValueError as error:
        raise ReviewBatchError("invalid JSON integer: {0}".format(error))


def reject_json_float(token):
    raise ReviewBatchError("JSON floating-point values are forbidden")


def reject_json_constant(token):
    raise ReviewBatchError("nonfinite JSON value is forbidden: {0}".format(token))


def require_bounded_json_nesting(value):
    stack = [(value, 0)]
    while stack:
        current, depth = stack.pop()
        if depth > MAX_JSON_NESTING:
            raise ReviewBatchError("JSON nesting exceeds its cap")
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
        raise ReviewBatchError("value is not canonical JSON: {0}".format(error))
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
    except ReviewBatchError:
        raise
    except (RecursionError, UnicodeError, ValueError) as error:
        raise ReviewBatchError("{0} is not valid JSON: {1}".format(label, error))
    require_bounded_json_nesting(value)
    if type(value) is not dict:
        raise ReviewBatchError("{0} must be a JSON object".format(label))
    if canonical and data != canonical_json(value, newline=True):
        raise ReviewBatchError("{0} is not canonical JSON".format(label))
    return value


def require_exact(actual, expected, label):
    if type(actual) is not type(expected):
        raise ReviewBatchError("{0} type changed".format(label))
    if isinstance(expected, dict):
        if set(actual) != set(expected):
            raise ReviewBatchError("{0} fields changed".format(label))
        for key in expected:
            require_exact(actual[key], expected[key], label + "." + str(key))
        return
    if isinstance(expected, list):
        if len(actual) != len(expected):
            raise ReviewBatchError("{0} length changed".format(label))
        for index, pair in enumerate(zip(actual, expected)):
            require_exact(pair[0], pair[1], label + "[{0}]".format(index))
        return
    if actual != expected:
        raise ReviewBatchError(
            "{0} differs: {1!r} != {2!r}".format(label, actual, expected)
        )


def exact_keys(value, keys, label):
    if type(value) is not dict or set(value) != set(keys):
        raise ReviewBatchError("{0} fields changed".format(label))
    return value


def safe_relative(value, label):
    if type(value) is not str or not value or "\x00" in value or "\\" in value:
        raise ReviewBatchError("{0} is not a safe relative path".format(label))
    path = PurePosixPath(value)
    if (
        path.is_absolute()
        or path.as_posix() != value
        or any(part in ("", ".", "..") for part in path.parts)
    ):
        raise ReviewBatchError("{0} is not normalized".format(label))
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
    return (info.st_dev, info.st_ino, info.st_mode, info.st_uid, info.st_gid)


def read_regular_file_once(path, label, size_cap):
    path = Path(path)
    if os.path.abspath(str(path)) != os.path.realpath(str(path)):
        raise ReviewBatchError("{0} traverses a symlink".format(label))
    try:
        before = os.lstat(str(path))
    except OSError as error:
        raise ReviewBatchError("cannot inspect {0}: {1}".format(label, error))
    if not stat.S_ISREG(before.st_mode) or before.st_size > size_cap:
        raise ReviewBatchError("{0} is not a bounded regular file".format(label))
    flags = os.O_RDONLY
    if hasattr(os, "O_BINARY"):
        flags |= os.O_BINARY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(str(path), flags)
        try:
            opened = os.fstat(descriptor)
            if _stat_identity(opened) != _stat_identity(before):
                raise ReviewBatchError("{0} changed while opened".format(label))
            chunks = []
            total = 0
            while True:
                chunk = os.read(descriptor, 1024 * 1024)
                if not chunk:
                    break
                total += len(chunk)
                if total > size_cap:
                    raise ReviewBatchError("{0} exceeds its size cap".format(label))
                chunks.append(chunk)
            after = os.fstat(descriptor)
        finally:
            os.close(descriptor)
        final = os.lstat(str(path))
    except ReviewBatchError:
        raise
    except OSError as error:
        raise ReviewBatchError("cannot read {0}: {1}".format(label, error))
    data = b"".join(chunks)
    if (
        _stat_identity(opened) != _stat_identity(after)
        or _stat_identity(before) != _stat_identity(final)
        or len(data) != before.st_size
    ):
        raise ReviewBatchError("{0} changed while read".format(label))
    return data


def validate_authority(authority):
    expected = {
        "batch_id": BATCH_ID,
        "claims": EXPECTED_CLAIMS,
        "expected_result": EXPECTED_RESULT,
        "future_decision_schema": EXPECTED_FUTURE_DECISION_SCHEMA,
        "gate": EXPECTED_GATE,
        "inputs": EXPECTED_INPUTS,
        "package_policy": EXPECTED_PACKAGE_POLICY,
        "remaining_blockers": EXPECTED_REMAINING_BLOCKERS,
        "schema_version": SCHEMA_VERSION,
        "selection_policy": EXPECTED_SELECTION_POLICY,
    }
    require_exact(authority, expected, "review-batch authority")
    return authority


def load_authority(repo=REPO_ROOT, explicit=None):
    path = Path(explicit) if explicit is not None else Path(repo) / AUTHORITY_PATH
    data = read_regular_file_once(path, "review-batch authority", MAX_AUTHORITY_BYTES)
    if AUTHORITY_SHA256 is None:
        raise ReviewBatchError("review-batch authority digest has not been frozen")
    if hashlib.sha256(data).hexdigest() != AUTHORITY_SHA256:
        raise ReviewBatchError("review-batch authority digest differs")
    return validate_authority(read_json_bytes(data, "review-batch authority", True))


def _read_bound(repo, record, label, cap):
    path = Path(repo) / safe_relative(record["path"], label + " path")
    data = read_regular_file_once(path, label, cap)
    if len(data) != record["size"] or hashlib.sha256(data).hexdigest() != record["sha256"]:
        raise ReviewBatchError("{0} bytes differ".format(label))
    return path, data


def load_queue_checker(repo, authority):
    inputs = authority["inputs"]
    queue_path, queue_data = _read_bound(
        repo, inputs["queue_checker"], "frozen review-queue checker", MAX_CHECKER_BYTES
    )
    queue_authority_path, _ = _read_bound(
        repo, inputs["queue_authority"], "frozen review-queue authority", MAX_AUTHORITY_BYTES
    )
    _read_bound(
        repo, inputs["decision_checker"], "frozen decision checker", MAX_CHECKER_BYTES
    )
    _read_bound(
        repo, inputs["decision_authority"], "frozen decision authority", MAX_AUTHORITY_BYTES
    )
    _, source_lock_data = _read_bound(
        repo, inputs["source_lock"], "frozen source lock", MAX_SOURCE_LOCK_BYTES
    )
    _read_bound(repo, inputs["workflow"], "frozen review-batch workflow", MAX_CHECKER_BYTES)
    source_lock = read_json_bytes(source_lock_data, "frozen source lock", False)
    require_exact(
        source_lock["source_commit"],
        SOURCE_COMMIT,
        "source-lock repository commit",
    ) if "source_commit" in source_lock else None
    linux = source_lock["embedded_objects"][2]
    require_exact(PurePosixPath(linux["path"]).name, LINUX_ARCHIVE["name"], "Linux archive name")
    require_exact(linux["sha256"], LINUX_ARCHIVE["sha256"], "Linux archive digest")
    require_exact(linux["size"], LINUX_ARCHIVE["size"], "Linux archive size")
    require_exact(source_lock["dist_git"]["commit"], DIST_GIT["commit"], "dist-git commit")
    require_exact(
        source_lock["dist_git"]["repository_url"],
        DIST_GIT["repository_url"],
        "dist-git URL",
    )
    module = types.ModuleType("_rk001_frozen_review_queue")
    module.__file__ = str(queue_path)
    module.__package__ = None
    try:
        code = compile(queue_data, str(queue_path), "exec", dont_inherit=True)
        exec(code, module.__dict__)
    except (Exception, MemoryError) as error:
        raise ReviewBatchError("cannot execute frozen review-queue checker: {0}".format(error))
    require_exact(module.AUTHORITY_SHA256, inputs["queue_authority"]["sha256"], "queue authority digest")
    require_exact(
        str(module.AUTHORITY_PATH).replace("\\", "/"),
        inputs["queue_authority"]["path"],
        "queue authority path",
    )
    try:
        queue_authority = module.load_authority(Path(repo).resolve(), queue_authority_path)
    except module.ReviewQueueError as error:
        raise ReviewBatchError("frozen review-queue authority rejected: {0}".format(error))
    require_exact(queue_authority["queue_id"], QUEUE_ID, "queue ID")
    return module, queue_authority


def derive_queue(repo, artifact_path, authority):
    module, queue_authority = load_queue_checker(repo, authority)
    artifact_data = read_regular_file_once(
        artifact_path, "exact inventory artifact", MAX_ARTIFACT_BYTES
    )
    artifact = authority["inputs"]["inventory_artifact"]
    if len(artifact_data) != artifact["size"] or hashlib.sha256(artifact_data).hexdigest() != artifact["sha256"]:
        raise ReviewBatchError("exact inventory artifact bytes differ")
    try:
        checker, decision_authority, compressed, _ = module.load_exact_inventory(
            Path(repo).resolve(), Path(artifact_path), queue_authority
        )
        if len(compressed) != authority["inputs"]["inventory_member"]["size"]:
            raise ReviewBatchError("inventory member size differs")
        if hashlib.sha256(compressed).hexdigest() != authority["inputs"]["inventory_member"]["sha256"]:
            raise ReviewBatchError("inventory member digest differs")
        result, records = module.analyze_review_queue(
            compressed, checker, decision_authority
        )
        module.require_exact(
            result, queue_authority["expected_result"], "exact review-queue result"
        )
    except module.ReviewQueueError as error:
        raise ReviewBatchError("frozen review queue rejected: {0}".format(error))
    return module, records


def select_batch(module, records):
    group_rows = records["exact-content-groups"]
    group_ids = [record["group_id"] for record in group_rows]
    if len(group_ids) != len(set(group_ids)):
        raise ReviewBatchError("exact-content groups are duplicated")
    unit_ids = [record["unit_id"] for record in records["review-units"]]
    unit_paths = [record["evidence"]["path"] for record in records["review-units"]]
    if len(unit_ids) != len(set(unit_ids)) or len(unit_paths) != len(set(unit_paths)):
        raise ReviewBatchError("review units are duplicated or retargeted")
    units_by_group = collections.defaultdict(list)
    for unit in records["review-units"]:
        group_id = unit["exact_content_group_id"]
        if group_id is not None:
            units_by_group[group_id].append(unit)
    groups = {record["group_id"]: record for record in group_rows}
    eligible = []
    for group_id, units in units_by_group.items():
        group = groups.get(group_id)
        if group is None or group["identity"]["entry_type"] != "regular":
            continue
        if group["path_count"] < EXPECTED_SELECTION_POLICY["eligible_group_minimum_path_count"]:
            continue
        if len(units) != group["path_count"]:
            raise ReviewBatchError("content group/unit closure differs")
        if not all(unit["basis"] == EXPECTED_SELECTION_POLICY["eligible_basis"] for unit in units):
            continue
        reasons = {tuple(unit["evidence"]["unresolved_reasons"]) for unit in units}
        if len(reasons) != 1:
            continue
        eligible.append(group)
    eligible.sort(key=lambda record: (-record["path_count"], record["group_id"]))
    if len(eligible) < GROUP_LIMIT:
        raise ReviewBatchError("eligible review batch is smaller than its frozen limit")
    ranked = eligible[:GROUP_LIMIT]
    selected_ids = {record["group_id"] for record in ranked}
    selected_groups = sorted(ranked, key=lambda record: record["group_id"])
    selected_units = [
        unit
        for unit in records["review-units"]
        if unit["exact_content_group_id"] in selected_ids
    ]
    if [unit["evidence"]["path"] for unit in selected_units] != sorted(
        unit["evidence"]["path"] for unit in selected_units
    ):
        raise ReviewBatchError("selected units are not in inventory path order")
    namespace_counts = collections.Counter(
        unit["evidence"]["namespace"] for unit in selected_units
    )
    group_bytes, group_sha = module.measure_records(selected_groups, "selected group")
    unit_bytes, unit_sha = module.measure_records(selected_units, "selected unit")
    result = {
        "boundary_group_id": ranked[-1]["group_id"],
        "candidate_signal_unit_count": sum(
            unit["candidate_directory_signal_id"] is not None for unit in selected_units
        ),
        "content_group_count": len(selected_groups),
        "content_group_stream_bytes": group_bytes,
        "content_group_stream_sha256": group_sha,
        "context_group_count": len(
            {unit["context_group_id"] for unit in selected_units}
        ),
        "maximum_content_size": max(
            group["identity"]["size"] for group in selected_groups
        ),
        "namespace_review_unit_counts": {
            namespace: namespace_counts[namespace]
            for namespace in ("dist-git", "linux", "repository", "srpm")
        },
        "review_unit_count": len(selected_units),
        "review_unit_stream_bytes": unit_bytes,
        "review_unit_stream_sha256": unit_sha,
        "selected_path_set_sha256": module.path_set_sha256(
            [unit["evidence"]["path"] for unit in selected_units]
        ),
        "unique_content_bytes": sum(
            group["identity"]["size"] for group in selected_groups
        ),
    }
    require_exact(result, EXPECTED_RESULT, "exact review-batch result")
    return result, selected_groups, selected_units


def stream_bytes(module, records):
    return b"".join(module.canonical_json(record, newline=True) for record in records)


def batch_summary(authority, result):
    return {
        "batch_id": authority["batch_id"],
        "claims": authority["claims"],
        "gate": authority["gate"],
        "inputs": authority["inputs"],
        "package_policy": authority["package_policy"],
        "remaining_blockers": authority["remaining_blockers"],
        "result": result,
        "review_state": "independent-review-required",
        "schema_version": SCHEMA_VERSION,
        "selection_policy": authority["selection_policy"],
        "source_commit": SOURCE_COMMIT,
    }


def _open_stable_regular(path, label, expected_size, expected_sha256):
    path = Path(path)
    if os.path.abspath(str(path)) != os.path.realpath(str(path)):
        raise ReviewBatchError("{0} traverses a symlink".format(label))
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(str(path), flags)
    except OSError as error:
        raise ReviewBatchError("cannot open {0}: {1}".format(label, error))
    try:
        opened = os.fstat(descriptor)
        if not stat.S_ISREG(opened.st_mode) or opened.st_size != expected_size:
            raise ReviewBatchError("{0} identity differs".format(label))
        digest = hashlib.sha256()
        while True:
            chunk = os.read(descriptor, 1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
        if digest.hexdigest() != expected_sha256:
            raise ReviewBatchError("{0} digest differs".format(label))
        os.lseek(descriptor, 0, os.SEEK_SET)
        return descriptor, _stat_identity(opened)
    except Exception:
        os.close(descriptor)
        raise


def read_linux_content(archive_path, wanted):
    """Read selected regular members from the exact Linux archive, without extraction."""

    descriptor, identity = _open_stable_regular(
        archive_path,
        "exact Linux archive",
        LINUX_ARCHIVE["size"],
        LINUX_ARCHIVE["sha256"],
    )
    expected_names = {}
    for path, expected in wanted.items():
        safe_relative(path, "selected Linux path")
        if not path.startswith("linux/"):
            raise ReviewBatchError("selected Linux path has the wrong namespace")
        name = LINUX_ARCHIVE["top_directory"] + "/" + path[len("linux/") :]
        expected_names[name] = expected
    found = {}
    seen_names = set()
    total_size = 0
    member_count = 0
    try:
        stream = os.fdopen(os.dup(descriptor), "rb")
        try:
            with tarfile.open(fileobj=stream, mode="r:xz") as archive:
                for member in archive:
                    member_count += 1
                    if member_count > MAX_TAR_MEMBERS:
                        raise ReviewBatchError("Linux archive member count exceeds its cap")
                    raw_name = member.name.rstrip("/")
                    if not raw_name:
                        raise ReviewBatchError("Linux archive member name is empty")
                    name = safe_relative(raw_name, "Linux archive member")
                    if name in seen_names:
                        raise ReviewBatchError("Linux archive contains duplicate members")
                    seen_names.add(name)
                    if type(member.size) is not int or member.size < 0:
                        raise ReviewBatchError("Linux archive member size is malformed")
                    total_size += member.size
                    if total_size > MAX_TAR_LOGICAL_BYTES:
                        raise ReviewBatchError("Linux archive logical size exceeds its cap")
                    expected = expected_names.get(name)
                    if expected is None:
                        continue
                    if not member.isfile() or member.size != expected["size"]:
                        raise ReviewBatchError("selected Linux member identity differs")
                    extracted = archive.extractfile(member)
                    if extracted is None:
                        raise ReviewBatchError("selected Linux member cannot be read")
                    try:
                        data = extracted.read(expected["size"] + 1)
                    finally:
                        extracted.close()
                    if len(data) != expected["size"] or hashlib.sha256(data).hexdigest() != expected["sha256"]:
                        raise ReviewBatchError("selected Linux member bytes differ")
                    found[expected["group_id"]] = data
        finally:
            stream.close()
        if _stat_identity(os.fstat(descriptor)) != identity:
            raise ReviewBatchError("exact Linux archive changed while read")
    except (OSError, EOFError, tarfile.TarError) as error:
        raise ReviewBatchError("Linux archive is invalid: {0}".format(error))
    finally:
        os.close(descriptor)
    if set(found) != {value["group_id"] for value in wanted.values()}:
        raise ReviewBatchError("selected Linux archive member closure differs")
    return found


def _git_environment():
    return {
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
        "PATH": "/usr/bin:/bin",
        "PAGER": "cat",
        "XDG_CONFIG_HOME": "/nonexistent",
    }


def git_blob(repo, oid):
    if type(oid) is not str or not HEX_SHA1.fullmatch(oid):
        raise ReviewBatchError("dist-git blob ID is malformed")
    repo = Path(repo)
    if os.path.abspath(str(repo)) != os.path.realpath(str(repo)) or not repo.is_dir():
        raise ReviewBatchError("dist-git repository path is not canonical")
    command = [
        "/usr/bin/git",
        "--no-pager",
        "-c",
        "advice.graftFileDeprecated=false",
        "-c",
        "core.attributesFile=/dev/null",
        "-c",
        "core.fsmonitor=false",
        "-c",
        "core.hooksPath=/dev/null",
        "-c",
        "credential.helper=",
        "-c",
        "diff.external=",
        "-c",
        "protocol.allow=never",
        "-C",
        str(repo),
        "cat-file",
        "blob",
        oid,
    ]
    try:
        completed = subprocess.run(
            command,
            check=True,
            env=_git_environment(),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except (OSError, subprocess.CalledProcessError) as error:
        message = getattr(error, "stderr", b"").decode("utf-8", errors="replace").strip()
        raise ReviewBatchError("cannot read exact dist-git blob: {0}".format(message))
    return completed.stdout


def materialize_content(groups, units, linux_archive, dist_git):
    units_by_group = collections.defaultdict(list)
    for unit in units:
        units_by_group[unit["exact_content_group_id"]].append(unit)
    linux_wanted = {}
    dist_git_wanted = []
    for group in groups:
        group_id = group["group_id"]
        candidates = units_by_group[group_id]
        linux = [unit for unit in candidates if unit["evidence"]["namespace"] == "linux"]
        expected = {
            "group_id": group_id,
            "sha256": group["identity"]["sha256"],
            "size": group["identity"]["size"],
        }
        if linux:
            linux_wanted[linux[0]["evidence"]["path"]] = expected
            continue
        dist = [unit for unit in candidates if unit["evidence"]["namespace"] == "dist-git"]
        if not dist:
            raise ReviewBatchError("selected content group has no materializable authority")
        expected["oid"] = dist[0]["evidence"]["source_identity"]["git_blob_oid"]
        dist_git_wanted.append(expected)
    blobs = read_linux_content(linux_archive, linux_wanted)
    for expected in dist_git_wanted:
        data = git_blob(dist_git, expected["oid"])
        if len(data) != expected["size"] or hashlib.sha256(data).hexdigest() != expected["sha256"]:
            raise ReviewBatchError("selected dist-git content bytes differ")
        blobs[expected["group_id"]] = data
    if set(blobs) != {group["group_id"] for group in groups}:
        raise ReviewBatchError("materialized content closure differs")
    return blobs


def content_map(groups, blobs):
    values = {}
    for group in groups:
        identity = group["identity"]
        digest = identity["sha256"]
        data = blobs.get(group["group_id"])
        if type(data) is not bytes:
            raise ReviewBatchError("selected content blob is missing")
        if len(data) != identity["size"] or hashlib.sha256(data).hexdigest() != digest:
            raise ReviewBatchError("selected content blob identity differs")
        if digest in values and values[digest] != data:
            raise ReviewBatchError("selected content digest collision")
        values[digest] = data
    if len(values) != GROUP_LIMIT:
        raise ReviewBatchError("selected content digest closure differs")
    return values


def _write_exclusive(path, data, mode=0o444):
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(str(path), flags, 0o600)
    try:
        view = memoryview(data)
        while view:
            written = os.write(descriptor, view)
            if written <= 0:
                raise ReviewBatchError("short output write")
            view = view[written:]
        os.fsync(descriptor)
        os.fchmod(descriptor, mode)
    finally:
        os.close(descriptor)


def _rename_noreplace(parent_fd, source, destination):
    libc = ctypes.CDLL(None, use_errno=True)
    source_bytes = source.encode("utf-8")
    destination_bytes = destination.encode("utf-8")
    if hasattr(libc, "renameat2"):
        result = libc.renameat2(
            parent_fd,
            ctypes.c_char_p(source_bytes),
            parent_fd,
            ctypes.c_char_p(destination_bytes),
            1,
        )
    elif platform.machine() == "x86_64" and hasattr(libc, "syscall"):
        result = libc.syscall(
            316,
            parent_fd,
            ctypes.c_char_p(source_bytes),
            parent_fd,
            ctypes.c_char_p(destination_bytes),
            1,
        )
    else:
        raise ReviewBatchError("atomic no-replace publication is unavailable")
    if result != 0:
        error = ctypes.get_errno()
        raise ReviewBatchError("cannot publish review batch: {0}".format(os.strerror(error)))


def package_files(module, authority, result, groups, units, blobs):
    group_stream = stream_bytes(module, groups)
    unit_stream = stream_bytes(module, units)
    require_exact(len(group_stream), result["content_group_stream_bytes"], "group stream bytes")
    require_exact(hashlib.sha256(group_stream).hexdigest(), result["content_group_stream_sha256"], "group stream digest")
    require_exact(len(unit_stream), result["review_unit_stream_bytes"], "unit stream bytes")
    require_exact(hashlib.sha256(unit_stream).hexdigest(), result["review_unit_stream_sha256"], "unit stream digest")
    values = {
        "batch-summary.json": canonical_json(batch_summary(authority, result), newline=True),
        "content-groups.jsonl": group_stream,
        "review-units.jsonl": unit_stream,
    }
    for digest, data in content_map(groups, blobs).items():
        values["content/" + digest] = data
    return values


def checksum_manifest(files):
    lines = []
    for name in sorted(files):
        safe_relative(name, "package member")
        lines.append("{0}  {1}\n".format(hashlib.sha256(files[name]).hexdigest(), name))
    return "".join(lines).encode("ascii")


def publish_package(output_dir, files):
    output = Path(output_dir)
    if output.name in ("", ".", "..") or "/" in output.name:
        raise ReviewBatchError("output directory name is invalid")
    parent = output.parent.resolve()
    if str(output.parent.absolute()) != str(parent):
        raise ReviewBatchError("output parent path is not canonical")
    parent_fd = os.open(str(parent), os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0))
    parent_identity = _directory_identity(os.fstat(parent_fd))
    stage = None
    try:
        try:
            os.stat(output.name, dir_fd=parent_fd, follow_symlinks=False)
        except FileNotFoundError:
            pass
        else:
            raise ReviewBatchError("output directory already exists")
        stage_path = Path(tempfile.mkdtemp(prefix=".rk001-review-batch-", dir=str(parent)))
        stage = stage_path.name
        os.chmod(str(stage_path), 0o700)
        created_stage_identity = _directory_identity(os.lstat(str(stage_path)))
        if (
            _directory_identity(os.lstat(str(parent))) != parent_identity
            or _directory_identity(os.stat(stage, dir_fd=parent_fd, follow_symlinks=False))
            != created_stage_identity
        ):
            raise ReviewBatchError("output parent or private stage changed")
        content = stage_path / "content"
        content.mkdir(mode=0o700)
        for name in sorted(files):
            path = stage_path / safe_relative(name, "package member")
            if path.parent == content or path.parent == stage_path:
                _write_exclusive(path, files[name])
            else:
                raise ReviewBatchError("package member parent differs")
        manifest = checksum_manifest(files)
        _write_exclusive(stage_path / "SHA256SUMS", manifest)
        os.chmod(str(content), 0o555)
        os.chmod(str(stage_path), 0o555)
        for directory in (content, stage_path):
            descriptor = os.open(str(directory), os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0))
            try:
                os.fsync(descriptor)
            finally:
                os.close(descriptor)
        stage_identity = _directory_identity(
            os.stat(stage, dir_fd=parent_fd, follow_symlinks=False)
        )
        if _directory_identity(os.fstat(parent_fd)) != parent_identity:
            raise ReviewBatchError("output parent changed before publication")
        if (
            _directory_identity(os.lstat(str(parent))) != parent_identity
            or _directory_identity(os.stat(stage, dir_fd=parent_fd, follow_symlinks=False))
            != stage_identity
        ):
            raise ReviewBatchError("output parent or private stage changed before publication")
        _rename_noreplace(parent_fd, stage, output.name)
        published = os.stat(output.name, dir_fd=parent_fd, follow_symlinks=False)
        if _directory_identity(published) != stage_identity:
            raise ReviewBatchError("published review-batch identity differs")
        published_fd = os.open(
            output.name,
            os.O_RDONLY
            | getattr(os, "O_DIRECTORY", 0)
            | getattr(os, "O_NOFOLLOW", 0),
            dir_fd=parent_fd,
        )
        try:
            if _directory_identity(os.fstat(published_fd)) != stage_identity:
                raise ReviewBatchError("published review-batch descriptor differs")
        finally:
            os.close(published_fd)
        stage = None
        os.fsync(parent_fd)
    finally:
        if stage is not None:
            stage_path = parent / stage
            try:
                os.chmod(str(stage_path / "content"), 0o700)
            except OSError:
                pass
            try:
                os.chmod(str(stage_path), 0o700)
            except OSError:
                pass
            shutil.rmtree(str(stage_path), ignore_errors=True)
        os.close(parent_fd)


def parse_jsonl(data, label):
    if len(data) > MAX_STREAM_BYTES:
        raise ReviewBatchError("{0} exceeds its size cap".format(label))
    records = []
    for raw in data.splitlines(True):
        if not raw.endswith(b"\n") or raw == b"\n":
            raise ReviewBatchError("{0} line framing is invalid".format(label))
        records.append(read_json_bytes(raw, label + " row", canonical=True))
        if len(records) > MAX_STREAM_RECORDS:
            raise ReviewBatchError("{0} record count exceeds its cap".format(label))
    if not records or b"".join(canonical_json(record, True) for record in records) != data:
        raise ReviewBatchError("{0} is not a canonical JSONL stream".format(label))
    return records


def _package_preflight(files, authority=None, expected_result=None, group_limit=None):
    """Reject package closure and aggregate-size drift before retaining bytes."""

    total = 0
    for relative in sorted(files):
        size = files[relative]["info"].st_size
        if type(size) is not int or size < 0:
            raise ReviewBatchError("review package member size is malformed")
        total += size
        if total > MAX_PACKAGE_BYTES:
            raise ReviewBatchError("review package aggregate size exceeds its cap")
    if authority is None:
        return total
    result = EXPECTED_RESULT if expected_result is None else expected_result
    limit = GROUP_LIMIT if group_limit is None else group_limit
    require_exact(
        authority["package_policy"]["maximum_package_bytes"],
        MAX_PACKAGE_BYTES,
        "package aggregate-byte cap",
    )
    root_names = {
        "SHA256SUMS",
        "batch-summary.json",
        "content-groups.jsonl",
        "review-units.jsonl",
    }
    content_names = sorted(name for name in files if name.startswith("content/"))
    if set(files) != root_names | set(content_names) or len(content_names) != limit:
        raise ReviewBatchError("review package member closure differs")
    for name in content_names:
        if not HEX_SHA256.fullmatch(name[len("content/") :]):
            raise ReviewBatchError("review package content filename is malformed")
        if files[name]["info"].st_size > result["maximum_content_size"]:
            raise ReviewBatchError("review package content member exceeds its cap")
    if sum(files[name]["info"].st_size for name in content_names) != result[
        "unique_content_bytes"
    ]:
        raise ReviewBatchError("review package content-byte closure differs")
    expected_sizes = {
        "batch-summary.json": len(
            canonical_json(batch_summary(authority, result), newline=True)
        ),
        "content-groups.jsonl": result["content_group_stream_bytes"],
        "review-units.jsonl": result["review_unit_stream_bytes"],
    }
    manifest_names = sorted(name for name in files if name != "SHA256SUMS")
    expected_sizes["SHA256SUMS"] = sum(
        64 + 2 + len(name.encode("ascii")) + 1 for name in manifest_names
    )
    for name, size in expected_sizes.items():
        if files[name]["info"].st_size != size:
            raise ReviewBatchError("review package member size differs: {0}".format(name))
    expected_total = sum(expected_sizes.values()) + result["unique_content_bytes"]
    if total != expected_total:
        raise ReviewBatchError("review package aggregate byte closure differs")
    return total


def _safe_component(value, label):
    if (
        type(value) is not str
        or not value
        or value in (".", "..")
        or "\x00" in value
        or "/" in value
        or "\\" in value
    ):
        raise ReviewBatchError("{0} is not a safe path component".format(label))
    return value


def _open_directory_components(path, label):
    """Open an absolute directory path one no-follow component at a time."""

    absolute = os.path.abspath(str(path))
    if absolute != os.path.realpath(absolute):
        raise ReviewBatchError("{0} traverses a symlink".format(label))
    try:
        expected = os.lstat(absolute)
    except OSError as error:
        raise ReviewBatchError("cannot inspect {0}: {1}".format(label, error))
    if not stat.S_ISDIR(expected.st_mode):
        raise ReviewBatchError("{0} is not a directory".format(label))
    flags = (
        os.O_RDONLY
        | getattr(os, "O_DIRECTORY", 0)
        | getattr(os, "O_NOFOLLOW", 0)
        | getattr(os, "O_CLOEXEC", 0)
    )
    current = None
    chain = []
    try:
        current = os.open(os.path.sep, flags)
        root_info = os.fstat(current)
        chain.append(
            {
                "descriptor": current,
                "identity": _directory_identity(root_info),
                "name": None,
                "parent_fd": None,
            }
        )
        for component in Path(absolute).parts[1:]:
            component = _safe_component(component, label + " component")
            following = os.open(component, flags, dir_fd=current)
            following_info = os.fstat(following)
            following_namespace = os.stat(
                component, dir_fd=current, follow_symlinks=False
            )
            if (
                not stat.S_ISDIR(following_info.st_mode)
                or _directory_identity(following_info)
                != _directory_identity(following_namespace)
            ):
                os.close(following)
                raise ReviewBatchError(
                    "{0} component identity changed".format(label)
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
        opened = os.fstat(current)
        if _directory_identity(opened) != _directory_identity(expected):
            raise ReviewBatchError("{0} changed while opened".format(label))
        return absolute, current, _directory_identity(opened), chain
    except Exception:
        for record in reversed(chain):
            try:
                os.close(record["descriptor"])
            except OSError:
                pass
        raise


def _list_directory_components(descriptor, label):
    try:
        names = os.listdir(descriptor)
    except OSError as error:
        raise ReviewBatchError("cannot list {0}: {1}".format(label, error))
    if len(names) > MAX_PACKAGE_FILES + 1:
        raise ReviewBatchError("{0} entry count exceeds its cap".format(label))
    for name in names:
        _safe_component(name, label + " entry")
    if len(names) != len(set(names)):
        raise ReviewBatchError("{0} entries are duplicated".format(label))
    return sorted(names)


def _open_regular_at(parent_fd, name, relative):
    flags = (
        os.O_RDONLY
        | getattr(os, "O_NOFOLLOW", 0)
        | getattr(os, "O_CLOEXEC", 0)
        | getattr(os, "O_NONBLOCK", 0)
    )
    descriptor = None
    try:
        descriptor = os.open(name, flags, dir_fd=parent_fd)
        info = os.fstat(descriptor)
        namespace = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
    except OSError as error:
        if descriptor is not None:
            try:
                os.close(descriptor)
            except OSError:
                pass
        raise ReviewBatchError(
            "cannot open package member {0}: {1}".format(relative, error)
        )
    if not stat.S_ISREG(info.st_mode) or _stat_identity(info) != _stat_identity(
        namespace
    ):
        os.close(descriptor)
        raise ReviewBatchError(
            "package member is not the exact opened regular file: {0}".format(relative)
        )
    return {
        "descriptor": descriptor,
        "identity": _stat_identity(info),
        "info": info,
        "name": name,
        "parent_fd": parent_fd,
        "relative": relative,
    }


def _verify_package_roots(context):
    for record in context["root_chain"]:
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
            raise ReviewBatchError(
                "package directory component namespace changed: {0}".format(error)
            )
        if (
            _directory_identity(opened) != record["identity"]
            or _directory_identity(namespace) != record["identity"]
        ):
            raise ReviewBatchError("package directory component namespace changed")
    try:
        root_path = os.stat(context["root_path"], follow_symlinks=False)
        root_open = os.fstat(context["root_fd"])
        content_name = os.stat(
            "content", dir_fd=context["root_fd"], follow_symlinks=False
        )
        content_open = os.fstat(context["content_fd"])
    except OSError as error:
        raise ReviewBatchError("package root namespace changed: {0}".format(error))
    if (
        _directory_identity(root_path) != context["root_identity"]
        or _directory_identity(root_open) != context["root_identity"]
        or _directory_identity(content_name) != context["content_identity"]
        or _directory_identity(content_open) != context["content_identity"]
    ):
        raise ReviewBatchError("package root namespace identity changed")


def _verify_package_member(record):
    try:
        opened = os.fstat(record["descriptor"])
        namespace = os.stat(
            record["name"],
            dir_fd=record["parent_fd"],
            follow_symlinks=False,
        )
    except OSError as error:
        raise ReviewBatchError(
            "package member namespace changed: {0}: {1}".format(
                record["relative"], error
            )
        )
    if (
        _stat_identity(opened) != record["identity"]
        or _stat_identity(namespace) != record["identity"]
    ):
        raise ReviewBatchError(
            "package member namespace identity changed: {0}".format(
                record["relative"]
            )
        )


def _replay_package_namespace(context, catalog):
    _verify_package_roots(context)
    if _list_directory_components(context["root_fd"], "package root") != context[
        "root_names"
    ]:
        raise ReviewBatchError("package root entry namespace changed")
    if _list_directory_components(
        context["content_fd"], "package content directory"
    ) != context["content_names"]:
        raise ReviewBatchError("package content entry namespace changed")
    for relative in sorted(catalog):
        _verify_package_member(catalog[relative])


def _read_open_regular_descriptor(record, label, size_cap):
    _verify_package_member(record)
    descriptor = record["descriptor"]
    expected_size = record["info"].st_size
    if expected_size > size_cap:
        raise ReviewBatchError("{0} exceeds its retained-byte cap".format(label))
    try:
        os.lseek(descriptor, 0, os.SEEK_SET)
        chunks = []
        total = 0
        while total < expected_size:
            chunk = os.read(
                descriptor, min(1024 * 1024, expected_size - total)
            )
            if not chunk:
                raise ReviewBatchError("{0} ended before its bound size".format(label))
            total += len(chunk)
            chunks.append(chunk)
    except OSError as error:
        raise ReviewBatchError("cannot read {0}: {1}".format(label, error))
    _verify_package_member(record)
    data = b"".join(chunks)
    if len(data) != expected_size:
        raise ReviewBatchError("{0} size changed while read".format(label))
    return data


def _open_package_catalog(directory):
    root_path, root_fd, root_identity, root_chain = _open_directory_components(
        directory, "review package directory"
    )
    content_fd = None
    catalog = {}
    try:
        root_names = _list_directory_components(root_fd, "package root")
        if "content" not in root_names:
            raise ReviewBatchError("package content directory is missing")
        content_flags = (
            os.O_RDONLY
            | getattr(os, "O_DIRECTORY", 0)
            | getattr(os, "O_NOFOLLOW", 0)
            | getattr(os, "O_CLOEXEC", 0)
        )
        content_fd = os.open("content", content_flags, dir_fd=root_fd)
        content_info = os.fstat(content_fd)
        content_namespace = os.stat(
            "content", dir_fd=root_fd, follow_symlinks=False
        )
        if (
            not stat.S_ISDIR(content_info.st_mode)
            or _directory_identity(content_info)
            != _directory_identity(content_namespace)
        ):
            raise ReviewBatchError("package content directory identity changed")
        content_identity = _directory_identity(content_info)
        content_names = _list_directory_components(
            content_fd, "package content directory"
        )
        for name in root_names:
            if name == "content":
                continue
            if len(catalog) >= MAX_PACKAGE_FILES:
                raise ReviewBatchError("review package file count exceeds its cap")
            record = _open_regular_at(root_fd, name, name)
            catalog[name] = record
        for name in content_names:
            if len(catalog) >= MAX_PACKAGE_FILES:
                raise ReviewBatchError("review package file count exceeds its cap")
            relative = "content/" + name
            catalog[relative] = _open_regular_at(content_fd, name, relative)
        context = {
            "content_fd": content_fd,
            "content_identity": content_identity,
            "content_names": content_names,
            "root_fd": root_fd,
            "root_identity": root_identity,
            "root_chain": root_chain,
            "root_names": root_names,
            "root_path": root_path,
        }
        _replay_package_namespace(context, catalog)
        return context, catalog
    except Exception:
        for record in catalog.values():
            os.close(record["descriptor"])
        if content_fd is not None:
            os.close(content_fd)
        for record in reversed(root_chain):
            try:
                os.close(record["descriptor"])
            except OSError:
                pass
        raise


def _close_package_catalog(context, catalog):
    for record in catalog.values():
        try:
            os.close(record["descriptor"])
        except OSError:
            pass
    try:
        os.close(context["content_fd"])
    except OSError:
        pass
    for record in reversed(context["root_chain"]):
        try:
            os.close(record["descriptor"])
        except OSError:
            pass


def read_package(directory, authority=None, expected_result=None, group_limit=None):
    context, catalog = _open_package_catalog(directory)
    try:
        _package_preflight(catalog, authority, expected_result, group_limit)
        _replay_package_namespace(context, catalog)
        files = {}
        retained = 0
        for relative in sorted(catalog):
            _verify_package_roots(context)
            record = catalog[relative]
            _verify_package_member(record)
            if relative.startswith("content/"):
                member_cap = (
                    (EXPECTED_RESULT if expected_result is None else expected_result)[
                        "maximum_content_size"
                    ]
                    if authority is not None
                    else MAX_CONTENT_BYTES
                )
            else:
                member_cap = MAX_STREAM_BYTES
            remaining = MAX_PACKAGE_BYTES - retained
            if remaining <= 0:
                raise ReviewBatchError(
                    "review package aggregate retention cap is exhausted before the next member"
                )
            data = _read_open_regular_descriptor(
                record,
                "package member " + relative,
                min(member_cap, remaining),
            )
            retained += len(data)
            if retained > MAX_PACKAGE_BYTES:
                raise ReviewBatchError("review package retained bytes exceed their cap")
            _verify_package_roots(context)
            _verify_package_member(record)
            files[relative] = data
        _replay_package_namespace(context, catalog)
        return files
    finally:
        _close_package_catalog(context, catalog)


def verify_package(directory, authority, module):
    files = read_package(directory, authority, EXPECTED_RESULT, GROUP_LIMIT)
    required = {"SHA256SUMS", "batch-summary.json", "content-groups.jsonl", "review-units.jsonl"}
    content_names = {name for name in files if name.startswith("content/")}
    if set(files) != required | content_names or len(content_names) != GROUP_LIMIT:
        raise ReviewBatchError("review package member closure differs")
    expected_manifest = checksum_manifest({name: data for name, data in files.items() if name != "SHA256SUMS"})
    require_exact(files["SHA256SUMS"], expected_manifest, "checksum manifest")
    summary = read_json_bytes(files["batch-summary.json"], "batch summary", True)
    require_exact(summary, batch_summary(authority, EXPECTED_RESULT), "batch summary")
    groups = parse_jsonl(files["content-groups.jsonl"], "content-group stream")
    units = parse_jsonl(files["review-units.jsonl"], "review-unit stream")
    require_exact(len(groups), GROUP_LIMIT, "content-group count")
    require_exact(len(units), EXPECTED_RESULT["review_unit_count"], "review-unit count")
    require_exact(hashlib.sha256(files["content-groups.jsonl"]).hexdigest(), EXPECTED_RESULT["content_group_stream_sha256"], "content-group stream digest")
    require_exact(hashlib.sha256(files["review-units.jsonl"]).hexdigest(), EXPECTED_RESULT["review_unit_stream_sha256"], "review-unit stream digest")
    previous_group = None
    group_index = {}
    for group in groups:
        exact_keys(group, {"group_id", "identity", "path_count", "path_set_sha256", "review_state"}, "selected content group")
        if previous_group is not None and group["group_id"] <= previous_group:
            raise ReviewBatchError("content groups are duplicate or out of order")
        previous_group = group["group_id"]
        require_exact(group["group_id"], module.stable_id("exact-content", group["identity"]), "content group ID")
        require_exact(group["review_state"], "independent-review-required", "content group state")
        group_index[group["group_id"]] = group
    referenced = collections.defaultdict(list)
    previous_path = None
    for unit in units:
        path = safe_relative(unit["evidence"]["path"], "selected unit path")
        if previous_path is not None and path <= previous_path:
            raise ReviewBatchError("review units are duplicate or out of order")
        previous_path = path
        if unit["basis"] != EXPECTED_SELECTION_POLICY["eligible_basis"]:
            raise ReviewBatchError("review unit basis differs")
        require_exact(unit["decision"], "unresolved", "review-unit decision")
        require_exact(unit["review_state"], "independent-review-required", "review-unit state")
        group_id = unit["exact_content_group_id"]
        if group_id not in group_index:
            raise ReviewBatchError("review unit references an unknown content group")
        identity = group_index[group_id]["identity"]
        require_exact(unit["evidence"]["entry_type"], "regular", "review-unit entry type")
        require_exact(unit["evidence"]["sha256"], identity["sha256"], "review-unit content digest")
        require_exact(unit["evidence"]["size"], identity["size"], "review-unit content size")
        referenced[group_id].append(path)
    if set(referenced) != set(group_index):
        raise ReviewBatchError("selected group/unit reference closure differs")
    for group_id, group in group_index.items():
        paths = referenced[group_id]
        require_exact(len(paths), group["path_count"], "selected group path count")
        require_exact(module.path_set_sha256(paths), group["path_set_sha256"], "selected group path set")
        digest = group["identity"]["sha256"]
        member = "content/" + digest
        if member not in files or len(files[member]) != group["identity"]["size"] or hashlib.sha256(files[member]).hexdigest() != digest:
            raise ReviewBatchError("selected content member differs")
    if module.path_set_sha256([unit["evidence"]["path"] for unit in units]) != EXPECTED_RESULT["selected_path_set_sha256"]:
        raise ReviewBatchError("selected path-set digest differs")
    return summary


def parser(argv=None):
    value = argparse.ArgumentParser(description=__doc__)
    value.add_argument("--repo", default=REPO_ROOT, type=Path)
    value.add_argument("--authority", type=Path)
    modes = value.add_mutually_exclusive_group(required=True)
    modes.add_argument("--check", action="store_true")
    modes.add_argument("--build", action="store_true")
    modes.add_argument("--verify-package", type=Path)
    modes.add_argument(
        "--emit",
        choices=("batch-summary", "content-groups", "review-units"),
    )
    value.add_argument("--artifact", type=Path)
    value.add_argument("--linux-archive", type=Path)
    value.add_argument("--dist-git", type=Path)
    value.add_argument("--output-dir", type=Path)
    return value.parse_args(argv)


def main(argv=None):
    args = parser(argv)
    try:
        repo = args.repo.resolve()
        authority = load_authority(repo, args.authority)
        module, _ = load_queue_checker(repo, authority)
        if args.check:
            print(
                "RK-001 review batch contract verified: batch=0001 groups=512 "
                "units=2096 state=independent-review-required gate=TODO points=0 credit=false"
            )
            return 0
        if args.verify_package is not None:
            verify_package(args.verify_package, authority, module)
            print(
                "RK-001 review batch package verified: groups=512 units=2096 "
                "reviewed=false durable=false credit=false"
            )
            return 0
        if args.artifact is None:
            raise ReviewBatchError("--artifact is required for build and emit modes")
        module, records = derive_queue(repo, args.artifact, authority)
        result, groups, units = select_batch(module, records)
        if args.emit:
            if args.emit == "batch-summary":
                sys.stdout.buffer.write(canonical_json(batch_summary(authority, result), True))
            elif args.emit == "content-groups":
                sys.stdout.buffer.write(stream_bytes(module, groups))
            else:
                sys.stdout.buffer.write(stream_bytes(module, units))
            return 0
        if args.output_dir is None or args.linux_archive is None or args.dist_git is None:
            raise ReviewBatchError(
                "--output-dir, --linux-archive, and --dist-git are required for --build"
            )
        blobs = materialize_content(groups, units, args.linux_archive, args.dist_git)
        files = package_files(module, authority, result, groups, units, blobs)
        publish_package(args.output_dir, files)
        verify_package(args.output_dir, authority, module)
        print(
            "RK-001 review batch built: groups=512 units=2096 content_bytes=81202 "
            "reviewed=false durable=false gate=TODO points=0 credit=false"
        )
        return 0
    except ReviewBatchError as error:
        print("RK-001 review-batch error: {0}".format(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
