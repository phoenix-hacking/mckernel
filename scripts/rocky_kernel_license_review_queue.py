#!/usr/bin/env python3
"""Verify and derive the non-crediting RK-001 independent-review queue.

The queue is derived only from the exact ef58860e inventory and the frozen
machine-decision checker/authority.  It groups unresolved paths by exact
captured content, source/directory context, and unresolved-reason identities.
Same-directory machine-classified siblings are exposed only as explicitly
non-conclusive candidate signals.  No group or signal resolves a path, makes a
legal conclusion, approves redistribution, or earns RK-001 tracker credit.
"""

from __future__ import print_function

import argparse
import collections
import hashlib
import json
import os
import stat
import sys
import types
from pathlib import Path, PurePosixPath


REPO_ROOT = Path(__file__).resolve().parents[1]
AUTHORITY_PATH = Path(
    "host-kernel/rocky/evidence/rk001-license-review-queue-ef58-v1.json"
)
# Exact canonical authority byte binding.
AUTHORITY_SHA256 = "e284b3700b9ec0a286b07f44505948418b67309015943856ceeb7c2f45c37d37"
SCHEMA_VERSION = 1
MAX_AUTHORITY_BYTES = 1024 * 1024
MAX_CHECKER_BYTES = 1024 * 1024
MAX_REVIEW_UNITS = 100000
MAX_GROUPS = 100000
MAX_STREAM_BYTES = 256 * 1024 * 1024
MAX_JSON_NESTING = 64
MAX_JSON_NUMBER_TOKEN = 128
HEX_SHA256 = __import__("re").compile(r"^[0-9a-f]{64}$")
HEX_SHA1 = __import__("re").compile(r"^[0-9a-f]{40}$")

DECISION_AUTHORITY_RELATIVE = (
    "host-kernel/rocky/evidence/rk001-license-decisions-ef58-v1.json"
)
DECISION_AUTHORITY_SHA256 = (
    "1e9769ffb9d8ccd4b49b0457678b9ed3841c647f6b817a7d66e815f0e6e84299"
)
DECISION_AUTHORITY_SIZE = 10012
DECISION_CHECKER_RELATIVE = "scripts/rocky_kernel_license_decisions.py"
DECISION_CHECKER_SHA256 = (
    "1414c1c16eca768f81de39739bd56ef1283435bf0c163c5e01b02c34e6291112"
)
DECISION_CHECKER_SIZE = 46167
EXPECTED_SOURCE_COMMIT = "ef58860e4806ee16e2c506e4e93c7b6ad8ad8f4b"
EXPECTED_ARTIFACT = {
    "archive_name": "rk001-license-inventory-32192199002-1.zip",
    "sha256": "09333e984e27a45b6af1b2f7d613570f6bf09d3a82f0fa7c6fbf4c9fd7707b18",
    "size": 6734527,
    "source_commit": EXPECTED_SOURCE_COMMIT,
}
EXPECTED_INPUTS = {
    "artifact": EXPECTED_ARTIFACT,
    "decision_authority": {
        "path": DECISION_AUTHORITY_RELATIVE,
        "review_id": "rk-001-license-decisions-ef58860e-v1",
        "sha256": DECISION_AUTHORITY_SHA256,
        "size": DECISION_AUTHORITY_SIZE,
    },
    "decision_checker": {
        "path": DECISION_CHECKER_RELATIVE,
        "sha256": DECISION_CHECKER_SHA256,
        "size": DECISION_CHECKER_SIZE,
    },
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
EXPECTED_POLICY = {
    "candidate_directory_signal": (
        "candidate-only-machine-classified-same-directory-sibling"
    ),
    "candidate_signal_auto_resolves": False,
    "candidate_signal_is_legal_conclusion": False,
    "candidate_signal_is_provenance_review": False,
    "context_identity_fields": [
        "namespace",
        "origin",
        "source_identity",
        "parent_directory",
        "entry_type",
    ],
    "exact_content_identity_fields": ["entry_type", "sha256", "size"],
    "exact_content_scope": "regular-files-only",
    "reason_identity_fields": ["basis", "unresolved_reasons"],
    "review_state": "independent-review-required",
    "schema_version": 1,
    "unit_order": "inventory-path-order",
}
EXPECTED_REMAINING_BLOCKERS = [
    "Every queue unit remains independent-review-required; grouping is not review or resolution.",
    "Directory sibling signals are candidate-only and cannot establish a license, provenance, authorship, or redistribution conclusion.",
    "Two embedded source archives remain unexpanded and unreviewed.",
    "The aggregate source-archive license expression and kernel.spec consumption/redistribution scope require separate review.",
    "The temporary Actions ZIP is not a durable archive.",
    "RK-001 remains TODO with zero points until separately reviewed decisions satisfy the source-lock and tracker authorities.",
]

# Exact canonical stream measurements independently locked by the authority
# digest below.  None of these measurements represent a reviewed decision.
EXPECTED_RESULT = {
    "candidate_directory_signal_cluster_count": 1653,
    "candidate_directory_signal_path_count": 11486,
    "candidate_directory_signal_stream_bytes": 1432770,
    "candidate_directory_signal_stream_sha256": "b8e0f894910480675229cf9003f283ed183e4b8900a336370ceea4c798083088",
    "context_group_count": 2607,
    "context_group_stream_bytes": 1424680,
    "context_group_stream_sha256": "69d77a1705ebb956621e692a42c44d21b8e4d0080dbc20c4940e02d4e2de375a",
    "exact_content_duplicate_group_count": 2214,
    "exact_content_duplicate_path_count": 6161,
    "exact_content_group_count": 38619,
    "exact_content_group_stream_bytes": 13975259,
    "exact_content_group_stream_sha256": "aaa025a2f612e63657eaf77eff549c20d8d04ee945c6a185c6e16a277ae877cf",
    "exact_content_path_count": 42566,
    "independent_review_required_count": 42649,
    "namespace_review_unit_counts": {
        "dist-git": 76,
        "linux": 42470,
        "repository": 33,
        "srpm": 70,
    },
    "reason_cluster_count": 10,
    "reason_cluster_stream_bytes": 3867,
    "reason_cluster_stream_sha256": "2802957f64e22b01547e2dace0b9d9f06586773c604d4ec9c4e5d484f0b03bd3",
    "review_unit_count": 42649,
    "review_unit_stream_bytes": 52561547,
    "review_unit_stream_sha256": "62e4e205952c75a54a61803c4fed7789e77d9faefed89edbf5c234546be98513",
    "symlink_without_content_group_count": 83,
    "unresolved_path_count": 42649,
}

AUTHORITY_KEYS = {
    "claims",
    "expected_result",
    "gate",
    "inputs",
    "queue_id",
    "queue_policy",
    "remaining_blockers",
    "schema_version",
}
RESULT_KEYS = {
    "candidate_directory_signal_cluster_count",
    "candidate_directory_signal_path_count",
    "candidate_directory_signal_stream_bytes",
    "candidate_directory_signal_stream_sha256",
    "context_group_count",
    "context_group_stream_bytes",
    "context_group_stream_sha256",
    "exact_content_duplicate_group_count",
    "exact_content_duplicate_path_count",
    "exact_content_group_count",
    "exact_content_group_stream_bytes",
    "exact_content_group_stream_sha256",
    "exact_content_path_count",
    "independent_review_required_count",
    "namespace_review_unit_counts",
    "reason_cluster_count",
    "reason_cluster_stream_bytes",
    "reason_cluster_stream_sha256",
    "review_unit_count",
    "review_unit_stream_bytes",
    "review_unit_stream_sha256",
    "symlink_without_content_group_count",
    "unresolved_path_count",
}


class ReviewQueueError(RuntimeError):
    """Raised when an input, authority, or derived queue fails closed."""


def reject_duplicate_pairs(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ReviewQueueError("duplicate JSON key: {0}".format(key))
        value[key] = item
    return value


def parse_bounded_json_int(token):
    if type(token) is not str or len(token) > MAX_JSON_NUMBER_TOKEN:
        raise ReviewQueueError("JSON integer token exceeds its cap")
    try:
        return int(token, 10)
    except ValueError as error:
        raise ReviewQueueError("JSON integer token is invalid: {0}".format(error))


def reject_json_float(token):
    if type(token) is not str or len(token) > MAX_JSON_NUMBER_TOKEN:
        raise ReviewQueueError("JSON float token exceeds its cap")
    raise ReviewQueueError("JSON floating-point values are forbidden")


def reject_json_constant(token):
    raise ReviewQueueError("nonfinite JSON value is forbidden: {0}".format(token))


def require_bounded_json_nesting(value):
    stack = [(value, 0)]
    while stack:
        current, depth = stack.pop()
        if depth > MAX_JSON_NESTING:
            raise ReviewQueueError("JSON nesting exceeds its cap")
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
        raise ReviewQueueError("value is not canonical JSON: {0}".format(error))
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
    except ReviewQueueError:
        raise
    except (RecursionError, UnicodeError, ValueError) as error:
        raise ReviewQueueError("{0} is not valid JSON: {1}".format(label, error))
    require_bounded_json_nesting(value)
    if type(value) is not dict:
        raise ReviewQueueError("{0} must be a JSON object".format(label))
    if canonical and data != canonical_json(value, newline=True):
        raise ReviewQueueError("{0} is not canonical JSON".format(label))
    return value


def exact_keys(value, keys, label):
    if type(value) is not dict or set(value) != set(keys):
        raise ReviewQueueError("{0} fields changed".format(label))
    return value


def require_exact(actual, expected, label):
    if type(actual) is not type(expected):
        raise ReviewQueueError("{0} type changed".format(label))
    if isinstance(expected, dict):
        if set(actual) != set(expected):
            raise ReviewQueueError("{0} fields changed".format(label))
        for key in expected:
            require_exact(actual[key], expected[key], label + "." + str(key))
        return
    if isinstance(expected, list):
        if len(actual) != len(expected):
            raise ReviewQueueError("{0} length changed".format(label))
        for index, (left, right) in enumerate(zip(actual, expected)):
            require_exact(left, right, label + "[{0}]".format(index))
        return
    if actual != expected:
        raise ReviewQueueError(
            "{0} differs: {1!r} != {2!r}".format(label, actual, expected)
        )


def require_nonnegative_int(value, label):
    if type(value) is not int or value < 0:
        raise ReviewQueueError("{0} is not a nonnegative integer".format(label))


def require_sha256(value, label):
    if not isinstance(value, str) or not HEX_SHA256.fullmatch(value):
        raise ReviewQueueError("{0} is not a SHA-256".format(label))


def safe_relative(value, label):
    if not isinstance(value, str) or not value or "\x00" in value or "\\" in value:
        raise ReviewQueueError("{0} is not a safe relative path".format(label))
    path = PurePosixPath(value)
    if (
        path.is_absolute()
        or path.as_posix() != value
        or any(part in ("", ".", "..") for part in path.parts)
    ):
        raise ReviewQueueError("{0} is not a normalized relative path".format(label))
    return value


def validate_source_identity(value, namespace, label):
    if type(value) is not dict:
        raise ReviewQueueError("{0} is not an object".format(label))
    keys = set(value)
    if namespace == "linux":
        if keys != {"archive_sha256"}:
            raise ReviewQueueError("{0} fields changed".format(label))
        require_sha256(value["archive_sha256"], label + " archive digest")
    elif namespace == "srpm":
        if keys != {"source_rpm_sha256"}:
            raise ReviewQueueError("{0} fields changed".format(label))
        require_sha256(value["source_rpm_sha256"], label + " SRPM digest")
    elif namespace == "repository":
        if keys != {"git_blob_oid", "git_commit"}:
            raise ReviewQueueError("{0} fields changed".format(label))
        for key in ("git_blob_oid", "git_commit"):
            if type(value[key]) is not str or not HEX_SHA1.fullmatch(value[key]):
                raise ReviewQueueError("{0} {1} is not a Git object ID".format(label, key))
    elif namespace == "dist-git":
        if keys != {"git_blob_oid", "git_mode"}:
            raise ReviewQueueError("{0} fields changed".format(label))
        if type(value["git_blob_oid"]) is not str or not HEX_SHA1.fullmatch(
            value["git_blob_oid"]
        ):
            raise ReviewQueueError("{0} blob is not a Git object ID".format(label))
        if value["git_mode"] not in ("100644", "100755", "120000"):
            raise ReviewQueueError("{0} mode is malformed".format(label))
    else:
        raise ReviewQueueError("{0} namespace is malformed".format(label))
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


def read_regular_file_once(path, label, size_cap):
    path = Path(path)
    if os.path.abspath(str(path)) != os.path.realpath(str(path)):
        raise ReviewQueueError("{0} traverses a symlink".format(label))
    try:
        before = os.lstat(str(path))
    except OSError as error:
        raise ReviewQueueError("cannot inspect {0}: {1}".format(label, error))
    if not stat.S_ISREG(before.st_mode) or before.st_size > size_cap:
        raise ReviewQueueError("{0} is not a bounded regular file".format(label))
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
                raise ReviewQueueError("{0} changed while opened".format(label))
            chunks = []
            total = 0
            while True:
                chunk = os.read(descriptor, 1024 * 1024)
                if not chunk:
                    break
                total += len(chunk)
                if total > size_cap:
                    raise ReviewQueueError("{0} exceeds its size cap".format(label))
                chunks.append(chunk)
            after = os.fstat(descriptor)
        finally:
            os.close(descriptor)
        final = os.lstat(str(path))
    except ReviewQueueError:
        raise
    except OSError as error:
        raise ReviewQueueError("cannot read {0}: {1}".format(label, error))
    data = b"".join(chunks)
    if (
        _stat_identity(opened) != _stat_identity(after)
        or _stat_identity(before) != _stat_identity(final)
        or len(data) != before.st_size
    ):
        raise ReviewQueueError("{0} changed while read".format(label))
    return data


def validate_authority(authority):
    exact_keys(authority, AUTHORITY_KEYS, "review-queue authority")
    require_exact(authority["schema_version"], SCHEMA_VERSION, "schema version")
    require_exact(
        authority["queue_id"],
        "rk-001-license-review-queue-ef58860e-v1",
        "queue ID",
    )
    require_exact(authority["inputs"], EXPECTED_INPUTS, "frozen inputs")
    require_exact(authority["claims"], EXPECTED_CLAIMS, "claims")
    require_exact(authority["gate"], EXPECTED_GATE, "gate")
    require_exact(authority["queue_policy"], EXPECTED_POLICY, "queue policy")
    require_exact(
        authority["remaining_blockers"],
        EXPECTED_REMAINING_BLOCKERS,
        "remaining blockers",
    )
    if EXPECTED_RESULT is None:
        raise ReviewQueueError("expected review-queue result has not been frozen")
    require_exact(authority["expected_result"], EXPECTED_RESULT, "expected result")
    result = exact_keys(authority["expected_result"], RESULT_KEYS, "expected result")
    for key, value in result.items():
        if key.endswith("_sha256"):
            require_sha256(value, "expected " + key)
        elif key == "namespace_review_unit_counts":
            exact_keys(
                value,
                {"dist-git", "linux", "repository", "srpm"},
                "namespace review-unit counts",
            )
            for namespace in value:
                require_nonnegative_int(value[namespace], "namespace count")
        else:
            require_nonnegative_int(value, "expected " + key)
    require_exact(
        result["review_unit_count"],
        result["unresolved_path_count"],
        "review-unit/unresolved total",
    )
    require_exact(
        result["independent_review_required_count"],
        result["unresolved_path_count"],
        "independent-review total",
    )
    require_exact(
        sum(result["namespace_review_unit_counts"].values()),
        result["review_unit_count"],
        "namespace review-unit total",
    )
    require_exact(
        result["exact_content_path_count"]
        + result["symlink_without_content_group_count"],
        result["review_unit_count"],
        "content/symlink partition",
    )
    if result["candidate_directory_signal_path_count"] > result["review_unit_count"]:
        raise ReviewQueueError("candidate signal path count exceeds queue")
    return authority


def load_authority(repo=REPO_ROOT, explicit=None):
    path = Path(explicit) if explicit is not None else Path(repo) / AUTHORITY_PATH
    data = read_regular_file_once(path, "review-queue authority", MAX_AUTHORITY_BYTES)
    if AUTHORITY_SHA256 is None:
        raise ReviewQueueError("review-queue authority digest has not been frozen")
    if hashlib.sha256(data).hexdigest() != AUTHORITY_SHA256:
        raise ReviewQueueError("review-queue authority digest differs")
    return validate_authority(
        read_json_bytes(data, "review-queue authority", canonical=True)
    )


def _load_frozen_checker(repo, authority):
    inputs = authority["inputs"]
    checker_record = inputs["decision_checker"]
    authority_record = inputs["decision_authority"]
    checker_path = Path(repo) / safe_relative(
        checker_record["path"], "decision checker path"
    )
    decision_authority_path = Path(repo) / safe_relative(
        authority_record["path"], "decision authority path"
    )
    checker_data = read_regular_file_once(
        checker_path, "frozen decision checker", MAX_CHECKER_BYTES
    )
    if (
        len(checker_data) != checker_record["size"]
        or hashlib.sha256(checker_data).hexdigest() != checker_record["sha256"]
    ):
        raise ReviewQueueError("frozen decision checker bytes differ")
    decision_authority_data = read_regular_file_once(
        decision_authority_path, "frozen decision authority", MAX_AUTHORITY_BYTES
    )
    if (
        len(decision_authority_data) != authority_record["size"]
        or hashlib.sha256(decision_authority_data).hexdigest()
        != authority_record["sha256"]
    ):
        raise ReviewQueueError("frozen decision authority bytes differ")
    module = types.ModuleType("_rk001_frozen_license_decisions")
    module.__file__ = str(checker_path)
    module.__package__ = None
    try:
        code = compile(checker_data, str(checker_path), "exec", dont_inherit=True)
        exec(code, module.__dict__)
    except (Exception, MemoryError) as error:
        raise ReviewQueueError("cannot execute frozen decision checker: {0}".format(error))
    require_exact(
        str(module.AUTHORITY_PATH).replace("\\", "/"),
        authority_record["path"],
        "decision checker authority path",
    )
    require_exact(
        module.AUTHORITY_SHA256,
        authority_record["sha256"],
        "decision checker authority digest",
    )
    try:
        decision_authority = module.load_authority(
            Path(repo).resolve(), decision_authority_path
        )
    except module.DecisionError as error:
        raise ReviewQueueError("frozen decision authority rejected: {0}".format(error))
    require_exact(
        decision_authority["review_id"],
        authority_record["review_id"],
        "decision authority review ID",
    )
    decision_artifact = decision_authority["artifact"]
    require_exact(
        {
            "archive_name": decision_artifact["archive_name"],
            "sha256": decision_artifact["zip_sha256"],
            "size": decision_artifact["zip_size"],
            "source_commit": decision_artifact["source_commit"],
        },
        inputs["artifact"],
        "decision artifact binding",
    )
    return module, decision_authority


def load_exact_inventory(repo, artifact_path, authority):
    module, decision_authority = _load_frozen_checker(repo, authority)
    try:
        files = module.read_artifact(artifact_path, decision_authority["artifact"])
        module.verify_checksum_manifest(files, decision_authority["artifact"])
        summary = module.validate_summary(
            files["license-inventory-summary.json"], decision_authority
        )
        decision_result = module.analyze_inventory(
            files["license-inventory.jsonl.gz"], summary, decision_authority
        )
        module.require_exact(
            decision_result,
            decision_authority["expected_result"],
            "exact frozen decision result",
        )
    except module.DecisionError as error:
        raise ReviewQueueError("exact inventory foundation rejected: {0}".format(error))
    return (
        module,
        decision_authority,
        files["license-inventory.jsonl.gz"],
        decision_result,
    )


def stable_id(prefix, identity):
    return prefix + ":" + hashlib.sha256(canonical_json(identity)).hexdigest()


def path_set_sha256(paths):
    digest = hashlib.sha256()
    previous = None
    for path in sorted(paths):
        safe_relative(path, "group path")
        if previous is not None and path <= previous:
            raise ReviewQueueError("group paths are duplicate or unsorted")
        previous = path
        digest.update(canonical_json({"path": path}, newline=True))
    return digest.hexdigest()


def parent_directory(path):
    parent = path.rpartition("/")[0]
    return safe_relative(parent, "inventory parent directory")


def add_group(groups, identity, path):
    key = canonical_json(identity)
    record = groups.get(key)
    if record is None:
        if len(groups) >= MAX_GROUPS:
            raise ReviewQueueError("review group count exceeds its cap")
        record = {"identity": identity, "paths": []}
        groups[key] = record
    record["paths"].append(path)
    return stable_id("group", identity)


def make_group_records(groups, prefix):
    records = []
    for grouped in groups.values():
        identity = grouped["identity"]
        paths = grouped["paths"]
        records.append(
            {
                "group_id": stable_id(prefix, identity),
                "identity": identity,
                "path_count": len(paths),
                "path_set_sha256": path_set_sha256(paths),
                "review_state": "independent-review-required",
            }
        )
    records.sort(key=lambda record: record["group_id"])
    if len(records) > MAX_GROUPS:
        raise ReviewQueueError("review group count exceeds its cap")
    return records


def measure_records(records, label):
    digest = hashlib.sha256()
    total = 0
    for record in records:
        line = canonical_json(record, newline=True)
        total += len(line)
        if total > MAX_STREAM_BYTES:
            raise ReviewQueueError("{0} stream exceeds its cap".format(label))
        digest.update(line)
    return total, digest.hexdigest()


def _validate_string_list(values, label, paths=False):
    if (
        type(values) is not list
        or any(type(value) is not str or not value for value in values)
        or values != sorted(set(values))
    ):
        raise ReviewQueueError("{0} is malformed".format(label))
    if paths:
        for value in values:
            safe_relative(value, label)


def validate_record_sets(records):
    """Close every emitted schema and every group-to-unit cross-reference."""

    exact_keys(
        records,
        {
            "candidate-signals",
            "context-groups",
            "exact-content-groups",
            "reason-clusters",
            "review-units",
        },
        "record sets",
    )
    group_specs = (
        (
            "exact-content-groups",
            "exact-content",
            {"entry_type", "sha256", "size"},
        ),
        (
            "context-groups",
            "context",
            {
                "entry_type",
                "namespace",
                "origin",
                "parent_directory",
                "source_identity",
            },
        ),
        (
            "reason-clusters",
            "reason",
            {"basis", "unresolved_reasons"},
        ),
    )
    group_indexes = {}
    for stream_name, prefix, identity_keys in group_specs:
        stream = records[stream_name]
        if type(stream) is not list or len(stream) > MAX_GROUPS:
            raise ReviewQueueError("{0} is not a bounded list".format(stream_name))
        previous = None
        index = {}
        for record in stream:
            exact_keys(
                record,
                {
                    "group_id",
                    "identity",
                    "path_count",
                    "path_set_sha256",
                    "review_state",
                },
                stream_name + " record",
            )
            exact_keys(record["identity"], identity_keys, stream_name + " identity")
            require_exact(
                record["group_id"],
                stable_id(prefix, record["identity"]),
                stream_name + " ID",
            )
            if previous is not None and record["group_id"] <= previous:
                raise ReviewQueueError(stream_name + " IDs are duplicate or unsorted")
            previous = record["group_id"]
            require_nonnegative_int(record["path_count"], stream_name + " path count")
            if record["path_count"] < 1:
                raise ReviewQueueError(stream_name + " contains an empty group")
            require_sha256(record["path_set_sha256"], stream_name + " path digest")
            require_exact(
                record["review_state"],
                "independent-review-required",
                stream_name + " review state",
            )
            identity = record["identity"]
            if prefix == "exact-content":
                require_exact(identity["entry_type"], "regular", "content entry type")
                require_sha256(identity["sha256"], "content digest")
                require_nonnegative_int(identity["size"], "content size")
            elif prefix == "context":
                if identity["entry_type"] not in ("regular", "symlink"):
                    raise ReviewQueueError("context entry type is malformed")
                if identity["namespace"] not in (
                    "dist-git",
                    "linux",
                    "repository",
                    "srpm",
                ):
                    raise ReviewQueueError("context namespace is malformed")
                if type(identity["origin"]) is not str or not identity["origin"]:
                    raise ReviewQueueError("context origin is malformed")
                safe_relative(identity["parent_directory"], "context parent")
                validate_source_identity(
                    identity["source_identity"],
                    identity["namespace"],
                    "context source identity",
                )
            else:
                if type(identity["basis"]) is not str or not identity["basis"]:
                    raise ReviewQueueError("reason basis is malformed")
                _validate_string_list(
                    identity["unresolved_reasons"], "reason unresolved reasons"
                )
                if "independent-review-required" not in identity[
                    "unresolved_reasons"
                ]:
                    raise ReviewQueueError("reason cluster lost independent review")
            index[record["group_id"]] = record
        group_indexes[prefix] = index

    candidate_stream = records["candidate-signals"]
    if type(candidate_stream) is not list or len(candidate_stream) > MAX_GROUPS:
        raise ReviewQueueError("candidate signals are not a bounded list")
    candidate_index = {}
    previous = None
    for record in candidate_stream:
        exact_keys(
            record,
            {
                "auto_resolution",
                "legal_conclusion",
                "provenance_review",
                "signal_id",
                "signal_identity",
                "unresolved_path_count",
                "unresolved_path_set_sha256",
            },
            "candidate signal",
        )
        for key in ("auto_resolution", "legal_conclusion", "provenance_review"):
            require_exact(record[key], False, "candidate signal " + key)
        identity = exact_keys(
            record["signal_identity"],
            {
                "candidate_evidence",
                "evidence_class",
                "namespace",
                "parent_directory",
                "resolved_sibling_path_count",
                "resolved_sibling_path_set_sha256",
            },
            "candidate signal identity",
        )
        require_exact(
            identity["evidence_class"],
            EXPECTED_POLICY["candidate_directory_signal"],
            "candidate evidence class",
        )
        if identity["namespace"] not in (
            "dist-git",
            "linux",
            "repository",
            "srpm",
        ):
            raise ReviewQueueError("candidate namespace is malformed")
        safe_relative(identity["parent_directory"], "candidate parent")
        require_nonnegative_int(
            identity["resolved_sibling_path_count"], "resolved sibling count"
        )
        if identity["resolved_sibling_path_count"] < 1:
            raise ReviewQueueError("candidate signal has no resolved sibling")
        require_sha256(
            identity["resolved_sibling_path_set_sha256"],
            "resolved sibling path digest",
        )
        evidence = identity["candidate_evidence"]
        if type(evidence) is not list or not evidence:
            raise ReviewQueueError("candidate evidence is empty")
        previous_evidence = None
        for candidate in evidence:
            exact_keys(
                candidate,
                {"license_text_paths", "spdx_expression"},
                "candidate evidence",
            )
            _validate_string_list(
                candidate["license_text_paths"],
                "candidate license-text paths",
                paths=True,
            )
            if not candidate["license_text_paths"]:
                raise ReviewQueueError("candidate license-text paths are empty")
            if (
                type(candidate["spdx_expression"]) is not str
                or not candidate["spdx_expression"]
            ):
                raise ReviewQueueError("candidate SPDX expression is malformed")
            encoded = canonical_json(candidate)
            if previous_evidence is not None and encoded <= previous_evidence:
                raise ReviewQueueError("candidate evidence is duplicate or unsorted")
            previous_evidence = encoded
        require_exact(
            record["signal_id"],
            stable_id("candidate-directory", identity),
            "candidate signal ID",
        )
        if previous is not None and record["signal_id"] <= previous:
            raise ReviewQueueError("candidate signal IDs are duplicate or unsorted")
        previous = record["signal_id"]
        require_nonnegative_int(
            record["unresolved_path_count"], "candidate unresolved count"
        )
        if record["unresolved_path_count"] < 1:
            raise ReviewQueueError("candidate signal has no unresolved path")
        require_sha256(
            record["unresolved_path_set_sha256"], "candidate unresolved digest"
        )
        candidate_index[record["signal_id"]] = record

    units = records["review-units"]
    if type(units) is not list or len(units) > MAX_REVIEW_UNITS:
        raise ReviewQueueError("review units are not a bounded list")
    referenced_paths = {
        "exact-content": collections.defaultdict(list),
        "context": collections.defaultdict(list),
        "reason": collections.defaultdict(list),
        "candidate": collections.defaultdict(list),
    }
    seen_paths = set()
    seen_units = set()
    previous_path = None
    for unit in units:
        exact_keys(
            unit,
            {
                "basis",
                "candidate_directory_signal_id",
                "capture_review_status",
                "context_group_id",
                "decision",
                "evidence",
                "exact_content_group_id",
                "reason_cluster_id",
                "review_state",
                "unit_id",
            },
            "review unit",
        )
        require_exact(unit["decision"], "unresolved", "review-unit decision")
        require_exact(
            unit["review_state"],
            "independent-review-required",
            "review-unit state",
        )
        require_exact(
            unit["capture_review_status"],
            "captured-unreviewed",
            "capture review status",
        )
        if type(unit["basis"]) is not str or not unit["basis"]:
            raise ReviewQueueError("review-unit basis is malformed")
        evidence = exact_keys(
            unit["evidence"],
            {
                "authorship_signals",
                "entry_type",
                "license_text_paths",
                "link_target",
                "namespace",
                "origin",
                "parent_directory",
                "path",
                "sha256",
                "size",
                "source_identity",
                "spdx_expression",
                "unresolved_reasons",
            },
            "review-unit evidence",
        )
        path = safe_relative(evidence["path"], "review-unit path")
        if previous_path is not None and path <= previous_path:
            raise ReviewQueueError("review-unit paths are duplicate or unsorted")
        previous_path = path
        seen_paths.add(path)
        if evidence["namespace"] not in (
            "dist-git",
            "linux",
            "repository",
            "srpm",
        ) or path.split("/", 1)[0] != evidence["namespace"]:
            raise ReviewQueueError("review-unit namespace differs")
        require_exact(
            evidence["parent_directory"], parent_directory(path), "unit parent"
        )
        if evidence["entry_type"] not in ("regular", "symlink"):
            raise ReviewQueueError("review-unit entry type is malformed")
        require_sha256(evidence["sha256"], "review-unit digest")
        require_nonnegative_int(evidence["size"], "review-unit size")
        if type(evidence["origin"]) is not str or not evidence["origin"]:
            raise ReviewQueueError("review-unit origin is malformed")
        validate_source_identity(
            evidence["source_identity"],
            evidence["namespace"],
            "review-unit source identity",
        )
        if type(evidence["spdx_expression"]) is not str or not evidence[
            "spdx_expression"
        ]:
            raise ReviewQueueError("review-unit SPDX expression is malformed")
        _validate_string_list(
            evidence["authorship_signals"], "review-unit authorship signals"
        )
        _validate_string_list(
            evidence["license_text_paths"],
            "review-unit license-text paths",
            paths=True,
        )
        _validate_string_list(
            evidence["unresolved_reasons"], "review-unit unresolved reasons"
        )
        if "independent-review-required" not in evidence["unresolved_reasons"]:
            raise ReviewQueueError("review unit lost independent-review blocker")
        if evidence["entry_type"] == "regular":
            require_exact(evidence["link_target"], None, "regular link target")
        elif type(evidence["link_target"]) is not str or not evidence["link_target"]:
            raise ReviewQueueError("symlink target is malformed")
        payload = dict(unit)
        del payload["unit_id"]
        require_exact(
            unit["unit_id"], stable_id("review-unit", payload), "review-unit ID"
        )
        if unit["unit_id"] in seen_units:
            raise ReviewQueueError("review-unit IDs are duplicate")
        seen_units.add(unit["unit_id"])

        content_id = unit["exact_content_group_id"]
        if evidence["entry_type"] == "regular":
            if content_id not in group_indexes["exact-content"]:
                raise ReviewQueueError("review unit has an unknown content group")
            referenced_paths["exact-content"][content_id].append(path)
            require_exact(
                group_indexes["exact-content"][content_id]["identity"],
                {
                    "entry_type": "regular",
                    "sha256": evidence["sha256"],
                    "size": evidence["size"],
                },
                "review-unit content identity",
            )
        else:
            require_exact(content_id, None, "symlink content group")
        context_id = unit["context_group_id"]
        if context_id not in group_indexes["context"]:
            raise ReviewQueueError("review unit has an unknown context group")
        referenced_paths["context"][context_id].append(path)
        require_exact(
            group_indexes["context"][context_id]["identity"],
            {
                "entry_type": evidence["entry_type"],
                "namespace": evidence["namespace"],
                "origin": evidence["origin"],
                "parent_directory": evidence["parent_directory"],
                "source_identity": evidence["source_identity"],
            },
            "review-unit context identity",
        )
        reason_id = unit["reason_cluster_id"]
        if reason_id not in group_indexes["reason"]:
            raise ReviewQueueError("review unit has an unknown reason cluster")
        referenced_paths["reason"][reason_id].append(path)
        require_exact(
            group_indexes["reason"][reason_id]["identity"],
            {
                "basis": unit["basis"],
                "unresolved_reasons": evidence["unresolved_reasons"],
            },
            "review-unit reason identity",
        )
        candidate_id = unit["candidate_directory_signal_id"]
        if candidate_id is not None:
            if candidate_id not in candidate_index:
                raise ReviewQueueError("review unit has an unknown candidate signal")
            referenced_paths["candidate"][candidate_id].append(path)
            identity = candidate_index[candidate_id]["signal_identity"]
            require_exact(
                identity["namespace"], evidence["namespace"], "candidate namespace"
            )
            require_exact(
                identity["parent_directory"],
                evidence["parent_directory"],
                "candidate parent",
            )

    for prefix in ("exact-content", "context", "reason"):
        if set(referenced_paths[prefix]) != set(group_indexes[prefix]):
            raise ReviewQueueError(prefix + " group reference closure differs")
        for group_id, group in group_indexes[prefix].items():
            paths = referenced_paths[prefix][group_id]
            require_exact(len(paths), group["path_count"], prefix + " path count")
            require_exact(
                path_set_sha256(paths),
                group["path_set_sha256"],
                prefix + " path-set digest",
            )
    if set(referenced_paths["candidate"]) != set(candidate_index):
        raise ReviewQueueError("candidate signal reference closure differs")
    for signal_id, signal in candidate_index.items():
        paths = referenced_paths["candidate"][signal_id]
        require_exact(
            len(paths), signal["unresolved_path_count"], "candidate path count"
        )
        require_exact(
            path_set_sha256(paths),
            signal["unresolved_path_set_sha256"],
            "candidate path-set digest",
        )
    if len(seen_paths) != len(units) or len(seen_units) != len(units):
        raise ReviewQueueError("review-unit closure differs")
    return records


def analyze_review_queue(compressed, module, decision_authority):
    known = module.catalog(decision_authority)
    unresolved = []
    resolved_directories = collections.defaultdict(
        lambda: {"evidence": {}, "paths": []}
    )
    previous = None
    try:
        for line in module.bounded_gzip_lines(compressed):
            item = module.read_json_bytes(line, "review-queue inventory row", canonical=True)
            namespace = module.validate_item(item)
            validate_source_identity(
                item["source_identity"], namespace, "inventory source identity"
            )
            if previous is not None and item["path"] <= previous:
                raise ReviewQueueError("inventory paths are duplicate or unsorted")
            previous = item["path"]
            decision = module.classify_item(item, known)
            parent = parent_directory(item["path"])
            if decision["decision"] == module.RESOLVED:
                candidate = {
                    "license_text_paths": list(item["license_text_paths"]),
                    "spdx_expression": item["spdx_expression"],
                }
                resolved = resolved_directories[parent]
                resolved["evidence"][canonical_json(candidate)] = candidate
                resolved["paths"].append(item["path"])
            elif decision["decision"] == module.UNRESOLVED:
                unresolved.append((item, decision, namespace, parent))
                if len(unresolved) > MAX_REVIEW_UNITS:
                    raise ReviewQueueError("review-unit count exceeds its cap")
            else:
                raise ReviewQueueError("frozen checker returned an unknown decision")
    except module.DecisionError as error:
        raise ReviewQueueError("review-queue inventory rejected: {0}".format(error))
    expected_unresolved = decision_authority["expected_result"]["unresolved_count"]
    if len(unresolved) != expected_unresolved:
        raise ReviewQueueError("unresolved path count differs from frozen decisions")

    content_groups = {}
    context_groups = {}
    reason_groups = {}
    content_ids = {}
    context_ids = {}
    reason_ids = {}
    namespace_counts = collections.Counter()
    for item, decision, namespace, parent in unresolved:
        path = item["path"]
        namespace_counts[namespace] += 1
        if item["entry_type"] == "regular":
            content_identity = {
                "entry_type": "regular",
                "sha256": item["sha256"],
                "size": item["size"],
            }
            content_ids[path] = add_group(
                content_groups, content_identity, path
            ).replace("group:", "exact-content:", 1)
        else:
            content_ids[path] = None
        context_identity = {
            "entry_type": item["entry_type"],
            "namespace": namespace,
            "origin": item["origin"],
            "parent_directory": parent,
            "source_identity": item["source_identity"],
        }
        context_ids[path] = add_group(
            context_groups, context_identity, path
        ).replace("group:", "context:", 1)
        reason_identity = {
            "basis": decision["basis"],
            "unresolved_reasons": list(item["unresolved_reasons"]),
        }
        reason_ids[path] = add_group(
            reason_groups, reason_identity, path
        ).replace("group:", "reason:", 1)

    candidate_groups = {}
    candidate_ids = {}
    for item, decision, namespace, parent in unresolved:
        if parent not in resolved_directories:
            candidate_ids[item["path"]] = None
            continue
        resolved = resolved_directories[parent]
        candidate_evidence = [
            resolved["evidence"][key] for key in sorted(resolved["evidence"])
        ]
        resolved_paths = sorted(resolved["paths"])
        identity = {
            "candidate_evidence": candidate_evidence,
            "evidence_class": EXPECTED_POLICY["candidate_directory_signal"],
            "namespace": namespace,
            "parent_directory": parent,
            "resolved_sibling_path_count": len(resolved_paths),
            "resolved_sibling_path_set_sha256": path_set_sha256(resolved_paths),
        }
        key = canonical_json(identity)
        group = candidate_groups.get(key)
        if group is None:
            group = {"identity": identity, "paths": []}
            candidate_groups[key] = group
        group["paths"].append(item["path"])
        candidate_ids[item["path"]] = stable_id("candidate-directory", identity)

    exact_content_records = make_group_records(content_groups, "exact-content")
    context_records = make_group_records(context_groups, "context")
    reason_records = make_group_records(reason_groups, "reason")
    candidate_records = []
    for grouped in candidate_groups.values():
        identity = grouped["identity"]
        paths = grouped["paths"]
        candidate_records.append(
            {
                "auto_resolution": False,
                "legal_conclusion": False,
                "provenance_review": False,
                "signal_id": stable_id("candidate-directory", identity),
                "signal_identity": identity,
                "unresolved_path_count": len(paths),
                "unresolved_path_set_sha256": path_set_sha256(paths),
            }
        )
    candidate_records.sort(key=lambda record: record["signal_id"])

    units = []
    seen_unit_ids = set()
    for item, decision, namespace, parent in unresolved:
        path = item["path"]
        payload = {
            "basis": decision["basis"],
            "candidate_directory_signal_id": candidate_ids[path],
            "capture_review_status": item["review_status"],
            "context_group_id": context_ids[path],
            "decision": "unresolved",
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
            "exact_content_group_id": content_ids[path],
            "reason_cluster_id": reason_ids[path],
            "review_state": "independent-review-required",
        }
        unit_id = stable_id("review-unit", payload)
        if unit_id in seen_unit_ids:
            raise ReviewQueueError("review-unit identities are not unique")
        seen_unit_ids.add(unit_id)
        record = dict(payload)
        record["unit_id"] = unit_id
        units.append(record)
    if [record["evidence"]["path"] for record in units] != sorted(
        record["evidence"]["path"] for record in units
    ):
        raise ReviewQueueError("review units are not in inventory path order")

    content_bytes, content_sha = measure_records(
        exact_content_records, "exact-content group"
    )
    context_bytes, context_sha = measure_records(context_records, "context group")
    reason_bytes, reason_sha = measure_records(reason_records, "reason cluster")
    candidate_bytes, candidate_sha = measure_records(
        candidate_records, "candidate directory signal"
    )
    unit_bytes, unit_sha = measure_records(units, "review unit")
    duplicate_content_groups = [
        record for record in exact_content_records if record["path_count"] > 1
    ]
    result = {
        "candidate_directory_signal_cluster_count": len(candidate_records),
        "candidate_directory_signal_path_count": sum(
            record["unresolved_path_count"] for record in candidate_records
        ),
        "candidate_directory_signal_stream_bytes": candidate_bytes,
        "candidate_directory_signal_stream_sha256": candidate_sha,
        "context_group_count": len(context_records),
        "context_group_stream_bytes": context_bytes,
        "context_group_stream_sha256": context_sha,
        "exact_content_duplicate_group_count": len(duplicate_content_groups),
        "exact_content_duplicate_path_count": sum(
            record["path_count"] for record in duplicate_content_groups
        ),
        "exact_content_group_count": len(exact_content_records),
        "exact_content_group_stream_bytes": content_bytes,
        "exact_content_group_stream_sha256": content_sha,
        "exact_content_path_count": sum(
            record["path_count"] for record in exact_content_records
        ),
        "independent_review_required_count": len(units),
        "namespace_review_unit_counts": {
            namespace: namespace_counts[namespace]
            for namespace in ("dist-git", "linux", "repository", "srpm")
        },
        "reason_cluster_count": len(reason_records),
        "reason_cluster_stream_bytes": reason_bytes,
        "reason_cluster_stream_sha256": reason_sha,
        "review_unit_count": len(units),
        "review_unit_stream_bytes": unit_bytes,
        "review_unit_stream_sha256": unit_sha,
        "symlink_without_content_group_count": sum(
            1 for record in units if record["exact_content_group_id"] is None
        ),
        "unresolved_path_count": len(units),
    }
    records = {
        "candidate-signals": candidate_records,
        "context-groups": context_records,
        "exact-content-groups": exact_content_records,
        "reason-clusters": reason_records,
        "review-units": units,
    }
    validate_record_sets(records)
    return result, records


def parser(argv=None):
    value = argparse.ArgumentParser(description=__doc__)
    value.add_argument("--artifact", required=True, type=Path)
    value.add_argument("--authority", type=Path)
    value.add_argument(
        "--emit",
        choices=(
            "candidate-signals",
            "context-groups",
            "exact-content-groups",
            "reason-clusters",
            "review-units",
        ),
    )
    value.add_argument("--json", action="store_true")
    value.add_argument("--repo", default=REPO_ROOT, type=Path)
    return value.parse_args(argv)


def main(argv=None):
    args = parser(argv)
    try:
        repo = args.repo.resolve()
        authority = load_authority(repo, args.authority)
        module, decision_authority, compressed, decision_result = load_exact_inventory(
            repo, args.artifact, authority
        )
        result, records = analyze_review_queue(
            compressed, module, decision_authority
        )
        require_exact(result, authority["expected_result"], "exact review-queue result")
    except ReviewQueueError as error:
        print("RK-001 license review-queue error: {0}".format(error), file=sys.stderr)
        return 1
    if args.emit:
        for record in records[args.emit]:
            sys.stdout.buffer.write(canonical_json(record, newline=True))
    elif args.json:
        output = {
            "claims": authority["claims"],
            "gate": authority["gate"],
            "queue_id": authority["queue_id"],
            "remaining_blockers": authority["remaining_blockers"],
            "result": result,
        }
        sys.stdout.buffer.write(canonical_json(output, newline=True))
    else:
        print(
            "RK-001 review queue verified: unresolved={0} exact_content_groups={1} "
            "context_groups={2} reason_clusters={3} candidate_signals={4}; "
            "all=independent-review-required gate=TODO points=0 credit=false".format(
                result["unresolved_path_count"],
                result["exact_content_group_count"],
                result["context_group_count"],
                result["reason_cluster_count"],
                result["candidate_directory_signal_cluster_count"],
            )
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
