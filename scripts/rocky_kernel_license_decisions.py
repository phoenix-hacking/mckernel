#!/usr/bin/env python3
"""Verify conservative, non-crediting RK-001 license-signal decisions.

This checker consumes one checksum-pinned GitHub Actions artifact.  It parses
every captured inventory row and labels a row only when the capture contains a
syntactically exact SPDX expression whose identifiers are covered by exact,
known Linux license-text records.  The label is a machine evidence decision;
it is not legal advice, a redistribution approval, provenance review, or
RK-001 credit.  Links, archives, RPM spec files, ambiguous expressions, and
items without a complete known-text mapping remain unresolved.
"""

from __future__ import print_function

import argparse
import collections
import gzip
import hashlib
import io
import json
import os
import re
import stat
import sys
import zipfile
import zlib
from pathlib import Path, PurePosixPath


REPO_ROOT = Path(__file__).resolve().parents[1]
AUTHORITY_PATH = Path(
    "host-kernel/rocky/evidence/rk001-license-decisions-ef58-v1.json"
)
# Filled only after the canonical authority and its exact expected result are
# generated.  Keeping the binding here prevents a retargeted manifest from
# silently becoming the decision authority.
AUTHORITY_SHA256 = "1e9769ffb9d8ccd4b49b0457678b9ed3841c647f6b817a7d66e815f0e6e84299"
SCHEMA_VERSION = 1
EXPECTED_ARTIFACT_MEMBERS = (
    "SHA256SUMS",
    "license-inventory-summary.json",
    "license-inventory.jsonl.gz",
)
EXPECTED_SOURCE_COMMIT = "ef58860e4806ee16e2c506e4e93c7b6ad8ad8f4b"
EXPECTED_ARTIFACT = {
    "archive_name": "rk001-license-inventory-32192199002-1.zip",
    "github_run_attempt": "1",
    "github_run_id": "32192199002",
    "members": [
        {
            "name": "SHA256SUMS",
            "sha256": "d099220b27379d66972615d08f92f2d49ccd1d459924f2f1499d4adf2503c299",
            "size": 190,
        },
        {
            "name": "license-inventory-summary.json",
            "sha256": "a8517ed1cff8a242276c49e69c565e7079a30dff50503c0fc8c77f3bfb948793",
            "size": 25185,
        },
        {
            "name": "license-inventory.jsonl.gz",
            "sha256": "25261775ecaede74cc1482cd733305f0fae7f8003a1a137ea01b40d4c147a41a",
            "size": 6728950,
        },
    ],
    "source_commit": EXPECTED_SOURCE_COMMIT,
    "zip_sha256": "09333e984e27a45b6af1b2f7d613570f6bf09d3a82f0fa7c6fbf4c9fd7707b18",
    "zip_size": 6734527,
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
EXPECTED_CAPTURE_BINDING = {
    "container_image": "rockylinux/rockylinux:10.2@sha256:e372170ca8630f0f03e9b70fdd0bf4a3ce3426b0de7cdba615f06337389de176",
    "github_head_sha": EXPECTED_SOURCE_COMMIT,
    "github_repository": "phoenix-hacking/mckernel",
    "github_run_attempt": "1",
    "github_run_id": "32192199002",
}
EXPECTED_REMAINING_BLOCKERS = (
    "Machine SPDX/text classification is not a legal conclusion, redistribution approval, or complete provenance review.",
    "Every row still requires the independent review required by the capture authority before RK-001 can close.",
    "All ambiguous, missing-signal, noncanonical, link, archive, RPM spec, and incomplete text-mapping cases remain unresolved.",
    "Two embedded source archives remain unexpanded and unreviewed.",
    "The aggregate source-archive license expression and kernel.spec consumption/redistribution scope require separate review.",
    "The temporary Actions ZIP is not a durable archive.",
    "RK-001 credit requires a separately reviewed decision authority registered in the source-lock validator; this foundation does not update that authority or the tracker.",
)
EXPECTED_EMBEDDED_OBJECTS = (
    "SOURCES/kernel-abi-stablelists-6.12.0-211.44.1.el10_2.tar.xz",
    "SOURCES/kernel-kabi-dw-6.12.0-211.44.1.el10_2.tar.xz",
)
EXPECTED_CAPTURE_REASON_KEYS = {
    "ambiguous-spdx",
    "license-text-mapping-missing:CC0-1.0",
    "license-text-mapping-missing:CC0-1.0,GPL-1.0-or-later,LGPL-2.0-or-later,Linux-man-pages-copyleft",
    "link-provenance-needs-review",
    "link-target-missing-or-unlicensed",
    "missing-spdx",
    "package-expression-needs-review",
    "patch-authorship-signal-missing",
    "patch-license-signal-missing",
}
ITEM_KEYS = {
    "authorship_signals",
    "entry_type",
    "license_text_paths",
    "link_target",
    "origin",
    "path",
    "review_status",
    "sha256",
    "size",
    "source_identity",
    "spdx_expression",
    "unresolved_reasons",
}
SUMMARY_KEYS = {
    "binding",
    "blockers",
    "complete",
    "credit_eligible",
    "inventory",
    "patch_series_sha256",
    "review_complete",
    "review_counts",
    "schema_version",
    "scope",
    "signal_issue_count",
    "source_lock_sha256",
    "unresolved_count",
    "unresolved_sample",
}
AUTHORITY_KEYS = {
    "artifact",
    "capture",
    "claims",
    "decision_policy",
    "expected_result",
    "gate",
    "known_license_texts",
    "remaining_blockers",
    "review_id",
    "schema_version",
}
RESULT_KEYS = {
    "basis_counts",
    "capture_reason_counts",
    "decision_counts",
    "decision_stream_bytes",
    "decision_stream_sha256",
    "distinct_resolved_spdx_expressions",
    "inventory_item_count",
    "inventory_uncompressed_sha256",
    "known_license_text_count",
    "machine_classified_count",
    "namespace_decision_counts",
    "unresolved_count",
}
RESOLVED = "machine-classified-exact-spdx"
UNRESOLVED = "unresolved"
RESOLVED_BASIS = "exact-spdx-and-known-license-texts"
BASIS_ORDER = (
    RESOLVED_BASIS,
    "ambiguous-spdx-needs-review",
    "archive-or-rpm-spec-needs-review",
    "capture-signal-needs-review",
    "license-evidence-needs-review",
    "missing-spdx-needs-review",
    "noncanonical-spdx-needs-review",
    "nonregular-link-needs-review",
)
HEX_SHA256 = re.compile(r"^[0-9a-f]{64}$")
TOKEN = re.compile(r"[A-Za-z0-9][A-Za-z0-9.+-]*|[()]")
MAX_ARTIFACT_BYTES = 16 * 1024 * 1024
MAX_INVENTORY_COMPRESSED_BYTES = 12 * 1024 * 1024
MAX_INVENTORY_BYTES = 512 * 1024 * 1024
MAX_LINE_BYTES = 1024 * 1024
MAX_ITEMS = 250000
MAX_JSON_NESTING = 64
MAX_SPDX_TOKENS = 2048
MAX_SPDX_NESTING = 64
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


class DecisionError(RuntimeError):
    """Raised whenever the artifact or a decision claim fails closed."""


def reject_duplicate_pairs(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise DecisionError("duplicate JSON key: {0}".format(key))
        value[key] = item
    return value


def require_bounded_json_nesting(value):
    stack = [(value, 0)]
    while stack:
        current, depth = stack.pop()
        if depth > MAX_JSON_NESTING:
            raise DecisionError("JSON nesting exceeds its cap")
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
        raise DecisionError("value is not canonical JSON: {0}".format(error))
    return data + (b"\n" if newline else b"")


def read_json_bytes(data, label, canonical=False):
    try:
        value = json.loads(
            data.decode("ascii"), object_pairs_hook=reject_duplicate_pairs
        )
    except DecisionError:
        raise
    except (RecursionError, UnicodeError, ValueError) as error:
        raise DecisionError("{0} is not valid JSON: {1}".format(label, error))
    require_bounded_json_nesting(value)
    if type(value) is not dict:
        raise DecisionError("{0} must be a JSON object".format(label))
    if canonical and data != canonical_json(value, newline=True):
        raise DecisionError("{0} is not canonical JSON".format(label))
    return value


def exact_keys(value, keys, label):
    if type(value) is not dict or set(value) != set(keys):
        raise DecisionError("{0} fields changed".format(label))
    return value


def require_exact(actual, expected, label):
    if type(actual) is not type(expected):
        raise DecisionError("{0} type changed".format(label))
    if isinstance(expected, dict):
        if set(actual) != set(expected):
            raise DecisionError("{0} fields changed".format(label))
        for key in expected:
            require_exact(actual[key], expected[key], label + "." + str(key))
        return
    if isinstance(expected, list):
        if len(actual) != len(expected):
            raise DecisionError("{0} length changed".format(label))
        for index, (left, right) in enumerate(zip(actual, expected)):
            require_exact(left, right, label + "[{0}]".format(index))
        return
    if actual != expected:
        raise DecisionError(
            "{0} differs: {1!r} != {2!r}".format(label, actual, expected)
        )


def require_nonnegative_int(value, label):
    if type(value) is not int or value < 0:
        raise DecisionError("{0} is not a nonnegative integer".format(label))


def require_sha256(value, label):
    if not isinstance(value, str) or not HEX_SHA256.fullmatch(value):
        raise DecisionError("{0} is not a SHA-256".format(label))


def safe_relative(value, label):
    if not isinstance(value, str) or not value or "\x00" in value or "\\" in value:
        raise DecisionError("{0} is not a safe relative path".format(label))
    path = PurePosixPath(value)
    if (
        path.is_absolute()
        or path.as_posix() != value
        or any(part in ("", ".", "..") for part in path.parts)
    ):
        raise DecisionError("{0} is not a normalized relative path".format(label))
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
        raise DecisionError("{0} traverses a symlink".format(label))
    try:
        before = os.lstat(str(path))
    except OSError as error:
        raise DecisionError("cannot inspect {0}: {1}".format(label, error))
    if not stat.S_ISREG(before.st_mode) or before.st_size > size_cap:
        raise DecisionError("{0} is not a bounded regular file".format(label))
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
                raise DecisionError("{0} changed while opened".format(label))
            chunks = []
            total = 0
            while True:
                chunk = os.read(descriptor, 1024 * 1024)
                if not chunk:
                    break
                total += len(chunk)
                if total > size_cap:
                    raise DecisionError("{0} exceeds its size cap".format(label))
                chunks.append(chunk)
            after = os.fstat(descriptor)
        finally:
            os.close(descriptor)
        final = os.lstat(str(path))
    except DecisionError:
        raise
    except OSError as error:
        raise DecisionError("cannot read {0}: {1}".format(label, error))
    data = b"".join(chunks)
    if (
        _stat_identity(opened) != _stat_identity(after)
        or _stat_identity(before) != _stat_identity(final)
        or len(data) != before.st_size
    ):
        raise DecisionError("{0} changed while read".format(label))
    return data


def false_tree(value, label):
    if isinstance(value, dict):
        for key in value:
            false_tree(value[key], label + "." + key)
        return
    if value is not False:
        raise DecisionError("{0} must remain false".format(label))


def validate_authority(authority):
    exact_keys(authority, AUTHORITY_KEYS, "decision authority")
    if authority["schema_version"] != SCHEMA_VERSION:
        raise DecisionError("decision authority schema changed")
    if authority["review_id"] != "rk-001-license-decisions-ef58860e-v1":
        raise DecisionError("decision authority ID changed")
    require_exact(authority["claims"], EXPECTED_CLAIMS, "claims")
    require_exact(
        authority["gate"],
        {
            "credit_eligible": False,
            "gate_id": "RK-001",
            "points_awarded": 0,
            "status": "TODO",
            "tracker_credit": False,
        },
        "gate",
    )
    policy = exact_keys(
        authority["decision_policy"],
        {
            "archive_suffixes",
            "machine_decision",
            "policy_version",
            "resolved_basis",
            "rpm_spec_suffix",
            "unresolved_decision",
        },
        "decision policy",
    )
    require_exact(policy["policy_version"], 1, "policy version")
    require_exact(policy["machine_decision"], RESOLVED, "machine decision")
    require_exact(policy["unresolved_decision"], UNRESOLVED, "unresolved decision")
    require_exact(policy["resolved_basis"], RESOLVED_BASIS, "resolved basis")
    require_exact(policy["archive_suffixes"], list(ARCHIVE_SUFFIXES), "archive suffixes")
    require_exact(policy["rpm_spec_suffix"], ".spec", "RPM spec suffix")

    artifact = exact_keys(
        authority["artifact"],
        {
            "archive_name",
            "github_run_attempt",
            "github_run_id",
            "members",
            "source_commit",
            "zip_sha256",
            "zip_size",
        },
        "artifact authority",
    )
    require_exact(artifact, EXPECTED_ARTIFACT, "artifact authority")
    require_sha256(artifact["zip_sha256"], "artifact ZIP digest")
    require_nonnegative_int(artifact["zip_size"], "artifact ZIP size")
    if artifact["zip_size"] < 1 or artifact["zip_size"] > MAX_ARTIFACT_BYTES:
        raise DecisionError("artifact ZIP size is outside its cap")
    if type(artifact["members"]) is not list or len(artifact["members"]) != 3:
        raise DecisionError("artifact member authority changed")
    member_names = []
    for record in artifact["members"]:
        exact_keys(record, {"name", "sha256", "size"}, "artifact member")
        member_names.append(safe_relative(record["name"], "artifact member name"))
        require_sha256(record["sha256"], "artifact member digest")
        require_nonnegative_int(record["size"], "artifact member size")
    require_exact(member_names, list(EXPECTED_ARTIFACT_MEMBERS), "artifact member order")

    capture = exact_keys(
        authority["capture"],
        {
            "binding",
            "capture_blockers",
            "inventory_uncompressed_sha256",
            "item_count",
            "namespace_closures",
            "patch_series_sha256",
            "signal_issue_count",
            "source_lock_sha256",
            "unexpanded_embedded_objects",
        },
        "capture authority",
    )
    require_nonnegative_int(capture["item_count"], "capture item count")
    require_nonnegative_int(capture["signal_issue_count"], "capture signal issues")
    require_sha256(
        capture["inventory_uncompressed_sha256"], "uncompressed inventory digest"
    )
    require_sha256(capture["patch_series_sha256"], "patch-series digest")
    require_sha256(capture["source_lock_sha256"], "source-lock digest")
    if (
        type(capture["capture_blockers"]) is not list
        or not capture["capture_blockers"]
        or any(type(value) is not str or not value for value in capture["capture_blockers"])
    ):
        raise DecisionError("capture blockers are missing")
    require_exact(capture["binding"], EXPECTED_CAPTURE_BINDING, "capture binding")
    require_exact(
        authority["remaining_blockers"],
        list(EXPECTED_REMAINING_BLOCKERS),
        "remaining blockers",
    )
    closures = exact_keys(
        capture["namespace_closures"],
        {"dist-git", "linux", "repository", "srpm"},
        "namespace closures",
    )
    namespace_total = 0
    for namespace in ("dist-git", "linux", "repository", "srpm"):
        record = exact_keys(
            closures[namespace],
            {"complete", "item_count", "path_set_sha256", "source_manifest_sha256"},
            "namespace closure " + namespace,
        )
        require_exact(record["complete"], True, "namespace closure complete")
        require_nonnegative_int(record["item_count"], "namespace item count")
        require_sha256(record["path_set_sha256"], "namespace path-set digest")
        require_sha256(record["source_manifest_sha256"], "namespace manifest digest")
        namespace_total += record["item_count"]
    require_exact(namespace_total, capture["item_count"], "namespace item total")
    embedded = capture["unexpanded_embedded_objects"]
    if (
        type(embedded) is not list
        or any(type(value) is not str or not safe_relative(value, "embedded object") for value in embedded)
    ):
        raise DecisionError("unexpanded embedded objects are malformed")
    if embedded != sorted(set(embedded)):
        raise DecisionError("unexpanded embedded objects are malformed")
    require_exact(
        embedded, list(EXPECTED_EMBEDDED_OBJECTS), "unexpanded embedded objects"
    )

    known = authority["known_license_texts"]
    if type(known) is not list or not known:
        raise DecisionError("known license-text authority is empty")
    previous = None
    for record in known:
        exact_keys(
            record,
            {"identifiers", "kind", "path", "sha256", "size"},
            "known license text",
        )
        path = safe_relative(record["path"], "known license-text path")
        if previous is not None and path <= previous:
            raise DecisionError("known license-text paths are duplicate or unsorted")
        previous = path
        if record["kind"] not in ("corroborating", "exception", "license"):
            raise DecisionError("known license-text kind changed")
        identifiers = record["identifiers"]
        if (
            type(identifiers) is not list
            or any(not isinstance(item, str) or not item for item in identifiers)
        ):
            raise DecisionError("known license-text identifiers are malformed")
        if identifiers != sorted(set(identifiers)):
            raise DecisionError("known license-text identifiers are malformed")
        if record["kind"] == "corroborating" and identifiers:
            raise DecisionError("corroborating text cannot assign identifiers")
        if record["kind"] != "corroborating" and not identifiers:
            raise DecisionError("license or exception text needs identifiers")
        require_sha256(record["sha256"], "known license-text digest")
        require_nonnegative_int(record["size"], "known license-text size")
        if record["size"] < 1:
            raise DecisionError("known license-text size is empty")

    result = exact_keys(authority["expected_result"], RESULT_KEYS, "expected result")
    for key in (
        "decision_stream_bytes",
        "distinct_resolved_spdx_expressions",
        "inventory_item_count",
        "known_license_text_count",
        "machine_classified_count",
        "unresolved_count",
    ):
        require_nonnegative_int(result[key], "expected result " + key)
    require_sha256(result["decision_stream_sha256"], "decision-stream digest")
    require_sha256(
        result["inventory_uncompressed_sha256"], "result inventory digest"
    )
    basis_counts = exact_keys(
        result["basis_counts"], set(BASIS_ORDER), "basis count categories"
    )
    decision_counts = exact_keys(
        result["decision_counts"],
        {RESOLVED, UNRESOLVED},
        "decision count categories",
    )
    reason_counts = exact_keys(
        result["capture_reason_counts"],
        EXPECTED_CAPTURE_REASON_KEYS,
        "capture reason counts",
    )
    for key in BASIS_ORDER:
        require_nonnegative_int(basis_counts[key], "basis count " + key)
    for key in (RESOLVED, UNRESOLVED):
        require_nonnegative_int(decision_counts[key], "decision count " + key)
    for key in EXPECTED_CAPTURE_REASON_KEYS:
        require_nonnegative_int(reason_counts[key], "capture reason count " + key)
    namespaces = exact_keys(
        result["namespace_decision_counts"],
        {"dist-git", "linux", "repository", "srpm"},
        "namespace decision counts",
    )
    for namespace in namespaces:
        exact_keys(
            namespaces[namespace], {RESOLVED, UNRESOLVED},
            "namespace decision count " + namespace,
        )
        for decision in (RESOLVED, UNRESOLVED):
            require_nonnegative_int(
                namespaces[namespace][decision],
                "namespace decision count " + namespace + "." + decision,
            )
    require_exact(
        result["machine_classified_count"],
        decision_counts[RESOLVED],
        "machine classified total",
    )
    require_exact(
        result["unresolved_count"],
        decision_counts[UNRESOLVED],
        "unresolved total",
    )
    require_exact(
        sum(basis_counts.values()),
        result["inventory_item_count"],
        "basis total",
    )
    require_exact(
        sum(decision_counts.values()),
        result["inventory_item_count"],
        "decision total",
    )
    require_exact(
        sum(sum(values.values()) for values in namespaces.values()),
        result["inventory_item_count"],
        "namespace decision total",
    )
    return authority


def load_authority(repo=REPO_ROOT, explicit=None):
    path = Path(explicit) if explicit is not None else Path(repo) / AUTHORITY_PATH
    data = read_regular_file_once(path, "decision authority", 1024 * 1024)
    if AUTHORITY_SHA256 is None:
        raise DecisionError("decision authority digest has not been frozen")
    if hashlib.sha256(data).hexdigest() != AUTHORITY_SHA256:
        raise DecisionError("decision authority digest differs")
    authority = read_json_bytes(data, "decision authority", canonical=True)
    return validate_authority(authority)


def member_map(artifact):
    return dict((record["name"], record) for record in artifact["members"])


def read_artifact(path, artifact):
    data = read_regular_file_once(path, "RK-001 artifact ZIP", MAX_ARTIFACT_BYTES)
    if len(data) != artifact["zip_size"]:
        raise DecisionError("artifact ZIP size differs")
    if hashlib.sha256(data).hexdigest() != artifact["zip_sha256"]:
        raise DecisionError("artifact ZIP digest differs")
    try:
        archive = zipfile.ZipFile(io.BytesIO(data), "r")
    except (OSError, zipfile.BadZipFile) as error:
        raise DecisionError("cannot open artifact ZIP: {0}".format(error))
    files = {}
    expected = member_map(artifact)
    with archive:
        if archive.comment:
            raise DecisionError("artifact ZIP comment is not empty")
        infos = archive.infolist()
        names = [info.filename for info in infos]
        if names != list(EXPECTED_ARTIFACT_MEMBERS) or len(names) != len(set(names)):
            raise DecisionError("artifact ZIP member closure or order changed")
        for info in infos:
            safe_relative(info.filename, "artifact ZIP member")
            if info.is_dir() or info.flag_bits & 0x1:
                raise DecisionError("artifact ZIP contains a directory or encrypted member")
            if info.compress_type != zipfile.ZIP_DEFLATED:
                raise DecisionError("artifact ZIP member compression changed")
            if info.extra or info.comment or info.internal_attr != 0:
                raise DecisionError("artifact ZIP member metadata changed")
            mode = info.external_attr >> 16
            if info.create_system != 3 or not stat.S_ISREG(mode) or mode & 0o777 != 0o644:
                raise DecisionError("artifact ZIP member mode changed")
            record = expected[info.filename]
            if info.file_size != record["size"]:
                raise DecisionError("artifact ZIP member size changed: {0}".format(info.filename))
            if info.file_size > MAX_INVENTORY_COMPRESSED_BYTES:
                raise DecisionError("artifact ZIP member exceeds its cap")
            try:
                payload = archive.read(info)
            except (
                NotImplementedError,
                OSError,
                RuntimeError,
                zipfile.BadZipFile,
                zlib.error,
            ) as error:
                raise DecisionError(
                    "cannot read artifact ZIP member {0}: {1}".format(
                        info.filename, error
                    )
                )
            if (
                len(payload) != record["size"]
                or hashlib.sha256(payload).hexdigest() != record["sha256"]
            ):
                raise DecisionError(
                    "artifact ZIP member digest differs: {0}".format(info.filename)
                )
            files[info.filename] = payload
    return files


def verify_checksum_manifest(files, artifact):
    records = member_map(artifact)
    expected = (
        "{0}  license-inventory.jsonl.gz\n"
        "{1}  license-inventory-summary.json\n".format(
            records["license-inventory.jsonl.gz"]["sha256"],
            records["license-inventory-summary.json"]["sha256"],
        )
    ).encode("ascii")
    if files["SHA256SUMS"] != expected:
        raise DecisionError("artifact checksum manifest differs or is stale")


def validate_summary(data, authority):
    summary = read_json_bytes(data, "capture summary", canonical=True)
    exact_keys(summary, SUMMARY_KEYS, "capture summary")
    capture = authority["capture"]
    require_exact(summary["schema_version"], 1, "capture schema")
    for key in ("complete", "credit_eligible", "review_complete"):
        require_exact(summary[key], False, "capture " + key)
    require_exact(summary["binding"], capture["binding"], "capture binding")
    require_exact(summary["blockers"], capture["capture_blockers"], "capture blockers")
    require_exact(
        summary["source_lock_sha256"], capture["source_lock_sha256"], "source lock"
    )
    require_exact(
        summary["patch_series_sha256"],
        capture["patch_series_sha256"],
        "patch series",
    )
    require_exact(summary["signal_issue_count"], capture["signal_issue_count"], "signal issues")
    require_exact(summary["unresolved_count"], capture["item_count"], "capture unresolved")
    require_exact(
        summary["review_counts"],
        {"captured-unreviewed": capture["item_count"]},
        "capture review counts",
    )
    inventory = exact_keys(
        summary["inventory"],
        {
            "compressed_sha256",
            "compressed_size",
            "item_count",
            "path",
            "uncompressed_sha256",
        },
        "capture inventory",
    )
    record = member_map(authority["artifact"])["license-inventory.jsonl.gz"]
    require_exact(inventory["path"], "license-inventory.jsonl.gz", "inventory path")
    require_exact(inventory["item_count"], capture["item_count"], "inventory count")
    require_exact(inventory["compressed_size"], record["size"], "inventory size")
    require_exact(inventory["compressed_sha256"], record["sha256"], "inventory digest")
    require_exact(
        inventory["uncompressed_sha256"],
        capture["inventory_uncompressed_sha256"],
        "uncompressed inventory digest",
    )
    scope = exact_keys(
        summary["scope"],
        {"authority_id", "namespaces", "unexpanded_embedded_objects"},
        "capture scope",
    )
    require_exact(
        scope["authority_id"],
        "rk-001-license-capture-source-closure-v1",
        "capture scope authority",
    )
    require_exact(
        scope["unexpanded_embedded_objects"],
        capture["unexpanded_embedded_objects"],
        "unexpanded embedded objects",
    )
    require_exact(scope["namespaces"], capture["namespace_closures"], "namespace closure")
    sample = summary["unresolved_sample"]
    if type(sample) is not list or len(sample) != 200:
        raise DecisionError("capture unresolved sample is malformed")
    previous = None
    for record in sample:
        exact_keys(record, {"path", "reasons"}, "capture unresolved sample row")
        path = safe_relative(record["path"], "capture unresolved sample path")
        if previous is not None and path <= previous:
            raise DecisionError("capture unresolved sample is duplicate or unsorted")
        previous = path
        reasons = record["reasons"]
        if (
            type(reasons) is not list
            or any(type(reason) is not str or not reason for reason in reasons)
        ):
            raise DecisionError("capture unresolved sample reasons are malformed")
        if reasons != sorted(set(reasons)) or "independent-review-required" not in reasons:
            raise DecisionError("capture unresolved sample reasons are malformed")
    return summary


def validate_item(item):
    exact_keys(item, ITEM_KEYS, "inventory item")
    path = safe_relative(item["path"], "inventory item path")
    namespace = path.split("/", 1)[0]
    if namespace not in ("dist-git", "linux", "repository", "srpm"):
        raise DecisionError("inventory item has an unknown namespace")
    require_sha256(item["sha256"], "inventory item digest")
    require_nonnegative_int(item["size"], "inventory item size")
    if item["entry_type"] not in ("regular", "symlink"):
        raise DecisionError("inventory item type is unsupported")
    if item["entry_type"] == "symlink":
        if not isinstance(item["link_target"], str) or not item["link_target"]:
            raise DecisionError("inventory symlink target is missing")
    elif item["link_target"] is not None:
        raise DecisionError("regular inventory item has a link target")
    if not isinstance(item["origin"], str) or not item["origin"]:
        raise DecisionError("inventory origin is missing")
    if type(item["source_identity"]) is not dict or not item["source_identity"]:
        raise DecisionError("inventory source identity is missing")
    if item["review_status"] != "captured-unreviewed":
        raise DecisionError("capture unexpectedly contains a reviewed item")
    expression = item["spdx_expression"]
    if not isinstance(expression, str) or not expression or len(expression) > 16384:
        raise DecisionError("inventory SPDX expression is malformed")
    for key in ("authorship_signals", "license_text_paths", "unresolved_reasons"):
        values = item[key]
        if (
            type(values) is not list
            or any(not isinstance(value, str) or not value for value in values)
        ):
            raise DecisionError("inventory {0} is malformed".format(key))
        if values != sorted(set(values)):
            raise DecisionError("inventory {0} is malformed".format(key))
    if "independent-review-required" not in item["unresolved_reasons"]:
        raise DecisionError("inventory item lost its independent-review blocker")
    for path_value in item["license_text_paths"]:
        safe_relative(path_value, "inventory license-text path")
    return namespace


class ExpressionParser(object):
    def __init__(self, expression):
        if not isinstance(expression, str):
            raise DecisionError("SPDX expression must be text")
        try:
            expression.encode("ascii")
        except UnicodeError:
            raise DecisionError("SPDX expression must be ASCII")
        if any(
            ord(character) < 0x20 or ord(character) == 0x7f
            for character in expression
        ):
            raise DecisionError("SPDX expression contains a control character")
        self.expression = expression
        self.tokens = []
        previous = 0
        for match in TOKEN.finditer(expression):
            if expression[previous : match.start()] not in ("", " "):
                raise DecisionError("SPDX expression contains invalid syntax")
            self.tokens.append(match.group(0))
            if len(self.tokens) > MAX_SPDX_TOKENS:
                raise DecisionError("SPDX expression has too many tokens")
            previous = match.end()
        if expression[previous:] not in ("", " ") or not self.tokens:
            raise DecisionError("SPDX expression contains invalid syntax")
        self.index = 0
        self.depth = 0
        self.licenses = set()
        self.exceptions = set()

    def peek(self):
        return self.tokens[self.index] if self.index < len(self.tokens) else None

    def take(self):
        value = self.peek()
        self.index += 1
        return value

    def parse_primary(self):
        token = self.peek()
        if token == "(":
            self.take()
            self.depth += 1
            if self.depth > MAX_SPDX_NESTING:
                raise DecisionError("SPDX expression nesting exceeds its cap")
            try:
                self.parse_or()
                if self.take() != ")":
                    raise DecisionError("SPDX expression has unbalanced parentheses")
            finally:
                self.depth -= 1
            return False
        if token is None or token in ("AND", "OR", "WITH", ")"):
            raise DecisionError("SPDX expression is missing an identifier")
        self.take()
        if token == "NOASSERTION":
            raise DecisionError("NOASSERTION is not an exact SPDX decision")
        self.licenses.add(token)
        return True

    def parse_with(self):
        simple = self.parse_primary()
        if self.peek() == "WITH":
            if not simple:
                raise DecisionError("WITH cannot qualify a grouped expression")
            self.take()
            token = self.peek()
            if token is None or token in ("AND", "OR", "WITH", "(", ")"):
                raise DecisionError("WITH is missing an exception identifier")
            self.take()
            self.exceptions.add(token)

    def parse_and(self):
        self.parse_with()
        while self.peek() == "AND":
            self.take()
            self.parse_with()

    def parse_or(self):
        self.parse_and()
        while self.peek() == "OR":
            self.take()
            self.parse_and()

    def parse(self):
        self.parse_or()
        if self.index != len(self.tokens):
            raise DecisionError("SPDX expression has a noncanonical operator or tail")
        return sorted(self.licenses), sorted(self.exceptions)


def parse_spdx_expression(expression):
    return ExpressionParser(expression).parse()


def catalog(authority):
    return dict((record["path"], record) for record in authority["known_license_texts"])


def archive_or_spec(path):
    lowered = path.lower()
    return lowered.endswith(ARCHIVE_SUFFIXES) or lowered.endswith(".spec")


def evidence_covers(item, known, licenses, exceptions):
    paths = item["license_text_paths"]
    if not paths:
        return False
    records = []
    for path in paths:
        record = known.get(path)
        if record is None:
            return False
        records.append(record)
    covered_licenses = set()
    covered_exceptions = set()
    for record in records:
        if record["kind"] == "license":
            covered_licenses.update(record["identifiers"])
        elif record["kind"] == "exception":
            covered_exceptions.update(record["identifiers"])
    if not set(licenses).issubset(covered_licenses):
        return False
    if not set(exceptions).issubset(covered_exceptions):
        return False
    needed = set(licenses) | set(exceptions)
    for record in records:
        if record["kind"] == "corroborating":
            continue
        if not needed.intersection(record["identifiers"]):
            return False
    return True


def classify_item(item, known):
    reasons = item["unresolved_reasons"]
    expression = item["spdx_expression"]
    if item["entry_type"] != "regular":
        decision, basis = UNRESOLVED, "nonregular-link-needs-review"
    elif archive_or_spec(item["path"]):
        decision, basis = UNRESOLVED, "archive-or-rpm-spec-needs-review"
    elif "ambiguous-spdx" in reasons or "malformed-spdx" in reasons:
        decision, basis = UNRESOLVED, "ambiguous-spdx-needs-review"
    elif expression == "NOASSERTION" or "missing-spdx" in reasons:
        decision, basis = UNRESOLVED, "missing-spdx-needs-review"
    else:
        try:
            licenses, exceptions = parse_spdx_expression(expression)
        except DecisionError:
            decision, basis = UNRESOLVED, "noncanonical-spdx-needs-review"
        else:
            extra_reasons = [
                reason for reason in reasons if reason != "independent-review-required"
            ]
            if extra_reasons:
                decision, basis = UNRESOLVED, "capture-signal-needs-review"
            elif not evidence_covers(item, known, licenses, exceptions):
                decision, basis = UNRESOLVED, "license-evidence-needs-review"
            else:
                decision, basis = RESOLVED, RESOLVED_BASIS
    return {
        "basis": basis,
        "decision": decision,
        "license_text_paths": item["license_text_paths"],
        "path": item["path"],
        "sha256": item["sha256"],
        "spdx_expression": expression,
    }


def bounded_gzip_lines(compressed):
    """Yield LF-terminated rows without allowing gzip to allocate a huge line."""

    stream = gzip.GzipFile(fileobj=io.BytesIO(compressed), mode="rb")
    buffer = bytearray()
    expanded = 0
    try:
        with stream:
            while True:
                remaining = MAX_INVENTORY_BYTES - expanded
                request_size = min(64 * 1024, remaining + 1)
                if request_size < 1:
                    raise DecisionError("inventory expansion exceeds its cap")
                chunk = stream.read(request_size)
                if not chunk:
                    break
                expanded += len(chunk)
                if expanded > MAX_INVENTORY_BYTES:
                    raise DecisionError("inventory expansion exceeds its cap")
                buffer.extend(chunk)
                while True:
                    newline = buffer.find(b"\n")
                    if newline < 0:
                        if len(buffer) > MAX_LINE_BYTES:
                            raise DecisionError("inventory line is oversized or unterminated")
                        break
                    line_size = newline + 1
                    if line_size > MAX_LINE_BYTES:
                        raise DecisionError("inventory line is oversized or unterminated")
                    line = bytes(buffer[:line_size])
                    del buffer[:line_size]
                    yield line
            if buffer:
                raise DecisionError("inventory line is oversized or unterminated")
    except DecisionError:
        raise
    except (EOFError, OSError, zlib.error) as error:
        raise DecisionError("cannot decompress inventory: {0}".format(error))


def analyze_inventory(compressed, summary, authority):
    if len(compressed) > MAX_INVENTORY_COMPRESSED_BYTES:
        raise DecisionError("compressed inventory exceeds its cap")
    known = catalog(authority)
    observed_known = {}
    raw_digest = hashlib.sha256()
    decision_digest = hashlib.sha256()
    raw_bytes = 0
    decision_bytes = 0
    count = 0
    previous = None
    basis_counts = collections.Counter()
    decision_counts = collections.Counter()
    reason_counts = collections.Counter()
    namespace_counts = collections.defaultdict(collections.Counter)
    resolved_expressions = set()
    observed_unresolved_sample = []
    try:
        for line in bounded_gzip_lines(compressed):
            raw_bytes += len(line)
            raw_digest.update(line)
            item = read_json_bytes(line, "inventory row", canonical=True)
            namespace = validate_item(item)
            if len(observed_unresolved_sample) < 200:
                observed_unresolved_sample.append(
                    {"path": item["path"], "reasons": item["unresolved_reasons"]}
                )
            if previous is not None and item["path"] <= previous:
                raise DecisionError("inventory paths are duplicate or unsorted")
            previous = item["path"]
            if item["path"] in known:
                observed_known[item["path"]] = {
                    "entry_type": item["entry_type"],
                    "sha256": item["sha256"],
                    "size": item["size"],
                }
            decision = classify_item(item, known)
            decision_line = canonical_json(decision, newline=True)
            decision_digest.update(decision_line)
            decision_bytes += len(decision_line)
            basis_counts[decision["basis"]] += 1
            decision_counts[decision["decision"]] += 1
            namespace_counts[namespace][decision["decision"]] += 1
            if decision["decision"] == RESOLVED:
                resolved_expressions.add(item["spdx_expression"])
            for reason in item["unresolved_reasons"]:
                if reason != "independent-review-required":
                    reason_counts[reason] += 1
            count += 1
            if count > MAX_ITEMS:
                raise DecisionError("inventory item count exceeds its cap")
    except DecisionError:
        raise
    except MemoryError:
        raise DecisionError("inventory decompression exceeded bounded memory")
    except (EOFError, OSError, zlib.error) as error:
        raise DecisionError("cannot decompress inventory: {0}".format(error))

    inventory = summary["inventory"]
    if count != inventory["item_count"] or raw_digest.hexdigest() != inventory[
        "uncompressed_sha256"
    ]:
        raise DecisionError("inventory count or uncompressed digest differs")
    require_exact(
        observed_unresolved_sample,
        summary["unresolved_sample"],
        "capture unresolved sample inventory binding",
    )
    for path, record in known.items():
        expected = {
            "entry_type": "regular",
            "sha256": record["sha256"],
            "size": record["size"],
        }
        if observed_known.get(path) != expected:
            raise DecisionError("known license-text inventory record differs: {0}".format(path))

    normalized_basis = dict((name, basis_counts[name]) for name in BASIS_ORDER)
    normalized_decisions = {
        RESOLVED: decision_counts[RESOLVED],
        UNRESOLVED: decision_counts[UNRESOLVED],
    }
    normalized_namespaces = {}
    for namespace in ("dist-git", "linux", "repository", "srpm"):
        normalized_namespaces[namespace] = {
            RESOLVED: namespace_counts[namespace][RESOLVED],
            UNRESOLVED: namespace_counts[namespace][UNRESOLVED],
        }
    return {
        "basis_counts": normalized_basis,
        "capture_reason_counts": dict(sorted(reason_counts.items())),
        "decision_counts": normalized_decisions,
        "decision_stream_bytes": decision_bytes,
        "decision_stream_sha256": decision_digest.hexdigest(),
        "distinct_resolved_spdx_expressions": len(resolved_expressions),
        "inventory_item_count": count,
        "inventory_uncompressed_sha256": raw_digest.hexdigest(),
        "known_license_text_count": len(known),
        "machine_classified_count": decision_counts[RESOLVED],
        "namespace_decision_counts": normalized_namespaces,
        "unresolved_count": decision_counts[UNRESOLVED],
    }


def review_artifact(path, authority):
    files = read_artifact(path, authority["artifact"])
    verify_checksum_manifest(files, authority["artifact"])
    summary = validate_summary(files["license-inventory-summary.json"], authority)
    result = analyze_inventory(
        files["license-inventory.jsonl.gz"], summary, authority
    )
    require_exact(result, authority["expected_result"], "exact decision result")
    return result


def parser(argv=None):
    value = argparse.ArgumentParser(description=__doc__)
    value.add_argument("--artifact", required=True, type=Path)
    value.add_argument("--authority", type=Path)
    value.add_argument("--repo", default=REPO_ROOT, type=Path)
    value.add_argument("--json", action="store_true")
    return value.parse_args(argv)


def main(argv=None):
    args = parser(argv)
    try:
        authority = load_authority(args.repo.resolve(), args.authority)
        result = review_artifact(args.artifact, authority)
    except DecisionError as error:
        print("RK-001 license decision error: {0}".format(error), file=sys.stderr)
        return 1
    if args.json:
        output = {
            "claims": authority["claims"],
            "gate": authority["gate"],
            "remaining_blockers": authority["remaining_blockers"],
            "result": result,
            "review_id": authority["review_id"],
        }
        sys.stdout.buffer.write(canonical_json(output, newline=True))
    else:
        print(
            "RK-001 license decisions verified: items={0} machine_classified={1} "
            "unresolved={2}; gate=TODO credit=false".format(
                result["inventory_item_count"],
                result["machine_classified_count"],
                result["unresolved_count"],
            )
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
