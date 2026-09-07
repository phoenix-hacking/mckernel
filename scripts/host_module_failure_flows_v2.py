#!/usr/bin/env python3
"""Close bounded C analysis-entry roots without retargeting v1 evidence.

The v1 compiler artifact remains immutable.  This additive v2 artifact binds
its exact bytes, replaces the known empty-root presentation with an explicit
function-summary boundary for every compiler-discovered C function, and gives
continued macro definitions a translation-unit source boundary.  A function
summary boundary is not proof of module/API reachability.  Cross-translation-
unit calls, indirect callbacks, semantic error domains, macro expansions, Rust
MIR, and executable acceptance evidence remain outside this tranche.
"""

import sys as _fp0006_entry_sys


if __name__ == "__main__" and not hasattr(
    _fp0006_entry_sys, "_mckernel_fp0006_authority_context"
):
    _fp0006_entry_sys.stderr.write(
        "host-module failure-flow v2 CLI requires the isolated failure-site "
        "authority launcher; refusing direct execution\n"
    )
    raise SystemExit(2)


import argparse
import hashlib
import json
import os
import re
import stat
import sys
import tempfile
from collections import Counter, defaultdict
from pathlib import Path

import host_module_contracts as contracts
import host_module_failure_contract_gaps as gaps
import host_module_failure_flows as v1_flows
import host_module_failure_sites as sites


SCHEMA_VERSION = 2
PROFILE = "compiler-backed-active-host-module-failure-flows-v2"
MAX_JSON_BYTES = 128 * 1024 * 1024
HEX_DIGEST = re.compile(r"^[0-9a-f]{64}$")
EXPECTED_SEMANTIC_DOMAIN_UNRESOLVED_COUNT = 205
EXPECTED_RUST_MIR_UNRESOLVED_COUNT = 420
EXPECTED_HFS_ARTIFACT = {
    "artifact_bytes": 842417,
    "artifact_sha256": "408f700403de23b705c603d7eff5cd39a2e3c6e2c7fb956cbdccf99c6db4b4b5",
}
EXPECTED_V1_FLOW_ARTIFACT = {
    "artifact_bytes": 4169467,
    "artifact_sha256": "d92f6eeffed29b9690042efd91861b367d18737d47b20344c605d4ed22f0fe9e",
}
HISTORICAL_AUTHORITY_MODE = "historical_ef58860e_archive"
FRESH_AUTHORITY_MODE = "fresh_current_head_replay"
EXPECTED_HFS_PROVENANCE = {
    "compatibility_overlay": {
        "path": "scripts/patches/ihk-linux-compat.patch",
        "sha256": "07b5a777f13fb8fd859bc1d941d9523b41f942b838813f75764a61fad379ecd8",
    },
    "frozen_inventory": {
        "path": "host-kernel/reference/legacy-host-modules-f2eb7352.json",
        "sha256": "8da72c25cb50e1c92ceaceb0e93afa1cc7a72f80e8cd0095eeedb62004bad02d",
    },
    "ihk_commit": "3114d9e7101ad52030eb3effa849a5c108972a1f",
    "repository_commit": "ef58860e4806ee16e2c506e4e93c7b6ad8ad8f4b",
}
HFS_SITE_KEYS = {
    "active_source_sha256",
    "classification",
    "column",
    "end_column",
    "errno",
    "expression",
    "id",
    "identity_sha256",
    "language",
    "line",
    "line_sha256",
    "module",
    "source",
    "source_sha256",
}

ANALYSIS_CLAIM = {
    "credit_eligible": False,
    "exhaustive": False,
    "fp_0006_status": "IN_PROGRESS",
    "module_api_reachability_proven": False,
    "test_mapped": False,
    "tracker_credit": False,
    "reason": (
        "schema v2 closes bounded C function/source analysis-entry roots; it "
        "does not prove module/API reachability, semantic error domains, Rust "
        "MIR, or executable acceptance results"
    ),
}

ANALYSIS_SCOPE = {
    "cross_translation_unit_reachability_proven": False,
    "external_root_definition": (
        "a boundary external to one compiler function summary, or the "
        "translation-unit source boundary for a continued macro definition; "
        "not a module/API entry-point claim"
    ),
    "indirect_callback_reachability_proven": False,
    "module_api_reachability_proven": False,
}

FIXED_BLOCKERS = tuple(v1_flows.FIXED_BLOCKERS)


class FlowV2Error(RuntimeError):
    """Raised when v1 evidence cannot support the bounded v2 derivation."""


def canonical_bytes(value):
    return (
        json.dumps(
            value, allow_nan=False, sort_keys=True, separators=(",", ":")
        )
        + "\n"
    ).encode("utf-8")


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def strict_equal(left, right):
    """Compare decoded JSON recursively without bool/int coercion."""

    if type(left) is not type(right):
        return False
    if isinstance(left, dict):
        return set(left) == set(right) and all(
            strict_equal(left[key], right[key]) for key in left
        )
    if isinstance(left, list):
        return len(left) == len(right) and all(
            strict_equal(left_item, right_item)
            for left_item, right_item in zip(left, right)
        )
    return left == right


def duplicate_rejecting_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise FlowV2Error("duplicate JSON key: {0}".format(key))
        result[key] = value
    return result


def reject_nonfinite_constant(value):
    raise FlowV2Error("non-finite JSON constant is forbidden: {0}".format(value))


def read_bytes_no_symlinks(path, label):
    """Open one regular file through no-follow directory descriptors."""

    path = Path(path)
    if ".." in path.parts:
        raise FlowV2Error("{0} path must not contain '..': {1}".format(label, path))
    absolute = path if path.is_absolute() else Path.cwd() / path
    parts = absolute.parts
    if not parts or parts[0] != "/" or len(parts) < 2:
        raise FlowV2Error("{0} path is invalid: {1}".format(label, path))
    if not hasattr(os, "O_NOFOLLOW") or not hasattr(os, "O_DIRECTORY"):
        raise FlowV2Error("no-follow file traversal is unavailable")

    directory_flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    file_flags = os.O_RDONLY | os.O_NOFOLLOW
    if hasattr(os, "O_CLOEXEC"):
        directory_flags |= os.O_CLOEXEC
        file_flags |= os.O_CLOEXEC

    directory_fd = None
    file_fd = None
    try:
        directory_fd = os.open("/", directory_flags)
        for component in parts[1:-1]:
            try:
                next_fd = os.open(component, directory_flags, dir_fd=directory_fd)
            except OSError as exc:
                raise FlowV2Error(
                    "{0} path contains a symlink or non-directory component: {1}"
                    .format(label, path)
                ) from exc
            os.close(directory_fd)
            directory_fd = next_fd
        try:
            file_fd = os.open(parts[-1], file_flags, dir_fd=directory_fd)
        except OSError as exc:
            raise FlowV2Error(
                "{0} must be a regular non-symlink file: {1}".format(label, path)
            ) from exc
        metadata = os.fstat(file_fd)
        if not stat.S_ISREG(metadata.st_mode):
            raise FlowV2Error("{0} must be a regular file: {1}".format(label, path))
        if metadata.st_size <= 0 or metadata.st_size > MAX_JSON_BYTES:
            raise FlowV2Error("{0} has an invalid size".format(label))
        chunks = []
        remaining = MAX_JSON_BYTES + 1
        while remaining:
            chunk = os.read(file_fd, min(1024 * 1024, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        data = b"".join(chunks)
        if not data or len(data) > MAX_JSON_BYTES:
            raise FlowV2Error("{0} has an invalid size".format(label))
        return data
    finally:
        if file_fd is not None:
            os.close(file_fd)
        if directory_fd is not None:
            os.close(directory_fd)


def read_json_with_bytes(path, label):
    path = Path(path)
    try:
        data = read_bytes_no_symlinks(path, label)
    except FlowV2Error:
        raise
    except OSError as exc:
        raise FlowV2Error("cannot read {0} {1}: {2}".format(label, path, exc))
    try:
        value = json.loads(
            data.decode("utf-8"),
            object_pairs_hook=duplicate_rejecting_object,
            parse_constant=reject_nonfinite_constant,
        )
    except (UnicodeDecodeError, ValueError) as exc:
        if isinstance(exc, FlowV2Error):
            raise
        raise FlowV2Error("cannot parse {0}: {1}".format(label, exc))
    if not isinstance(value, dict):
        raise FlowV2Error("{0} must be a JSON object".format(label))
    return (
        value,
        {"artifact_bytes": len(data), "artifact_sha256": sha256_bytes(data)},
        data,
    )


def read_json(path, label):
    value, record, _ = read_json_with_bytes(path, label)
    return value, record


def function_boundary(module, source, function):
    identity = {
        "function": function,
        "kind": "translation_unit_function_boundary",
        "module": module,
        "source": source,
    }
    digest = sha256_bytes(canonical_bytes(identity))
    return {"id": "HFR-" + digest[:24].upper(), **identity}


def source_boundary(module, source):
    identity = {
        "kind": "translation_unit_source_boundary",
        "module": module,
        "source": source,
    }
    digest = sha256_bytes(canonical_bytes(identity))
    return {"id": "HFR-" + digest[:24].upper(), **identity}


def validate_exact_hfs_authority(hfs, expected_provenance):
    """Validate the complete HFS schema against one replayed provenance record."""

    try:
        gaps.require_exact_keys(hfs, gaps.HFS_TOP_LEVEL_KEYS, "v1 failure-site artifact")
        if (
            not strict_equal(hfs.get("schema_version"), sites.SCHEMA_VERSION)
            or not strict_equal(hfs.get("profile"), sites.PROFILE)
            or not strict_equal(
                hfs.get("generator"), "scripts/host_module_failure_sites.py"
            )
        ):
            raise gaps.GapError("v1 failure-site authority changed")
        gaps.validate_kernel_configuration(hfs.get("kernel_configuration"))
        gaps.require_exact_keys(
            hfs.get("provenance"),
            {"compatibility_overlay", "frozen_inventory", "ihk_commit", "repository_commit"},
            "v1 failure-site provenance",
        )
        if not strict_equal(hfs.get("provenance"), expected_provenance):
            raise gaps.GapError("v1 failure-site replay provenance changed")
        sources = hfs.get("sources")
        if not isinstance(sources, list) or len(sources) != len(sites.EXPECTED_SOURCES):
            raise gaps.GapError("v1 failure-site source closure changed")
        for index, (expected, record) in enumerate(zip(sites.EXPECTED_SOURCES, sources)):
            module, language, source, command_file = expected
            expected_keys = (
                gaps.C_HFS_SOURCE_KEYS
                if language == "c"
                else gaps.RUST_HFS_SOURCE_KEYS
            )
            gaps.require_exact_keys(record, expected_keys, "v1 HFS source {0}".format(index))
            if not strict_equal(
                (
                    record.get("module"), record.get("language"),
                    record.get("source"), record.get("command_file"),
                ),
                (module, language, source, command_file),
            ):
                raise gaps.GapError("v1 HFS source identity changed: {0}".format(source))
            for field, minimum in (
                ("active_target_line_count", 1),
                ("failure_site_count", 0),
                ("post_compile_token_count", 0),
            ):
                gaps.require_count(record.get(field), "{0}.{1}".format(source, field), minimum)
            gaps.require_digest(
                record.get("post_compile_tokens_sha256"),
                "{0}.post_compile_tokens_sha256".format(source),
            )
            argv = record.get("compile_argv")
            preprocess_argv = record.get("preprocess_argv")
            if (
                not isinstance(argv, list)
                or len(argv) < 2
                or any(not isinstance(word, str) or not word or "\0" in word for word in argv)
                or not isinstance(preprocess_argv, list)
                or any(not isinstance(word, str) or not word or "\0" in word for word in preprocess_argv)
            ):
                raise gaps.GapError("v1 HFS compiler argv is malformed: {0}".format(source))
            digest_keys = (
                gaps.C_HFS_DIGEST_KEYS
                if language == "c"
                else gaps.RUST_HFS_DIGEST_KEYS
            )
            digests = gaps.require_exact_keys(
                record.get("digests"), digest_keys, "{0} digests".format(source)
            )
            for field, digest in digests.items():
                gaps.require_digest(digest, "{0}.{1}".format(source, field))
            if language == "c":
                gaps.validate_compiler_record(
                    record.get("preprocessor"), "{0}.preprocessor".format(source)
                )
            else:
                gaps.validate_compiler_record(
                    record.get("recorded_compiler"),
                    "{0}.recorded_compiler".format(source),
                )
                gaps.validate_compiler_record(
                    record.get("simplified_command_compiler"),
                    "{0}.simplified_command_compiler".format(source),
                )
                if (
                    record.get("preprocessing_mode")
                    != "exact Rust source; no C preprocessing"
                    or preprocess_argv != []
                    or record.get("recorded_compile_argv_file")
                    != str(Path(command_file).with_name(Path(command_file).name + ".argv.json"))
                ):
                    raise gaps.GapError("v1 Rust HFS capture claim changed")
        failure_sites = hfs.get("failure_sites")
        if not isinstance(failure_sites, list):
            raise gaps.GapError("v1 failure-site rows are missing")
        for index, site in enumerate(failure_sites):
            gaps.require_exact_keys(site, HFS_SITE_KEYS, "v1 HFS site {0}".format(index))
    except gaps.GapError as exc:
        raise FlowV2Error(str(exc))


def write_private_snapshot(directory, prefix, data):
    """Materialize descriptor-read authority bytes for a replay-only consumer."""

    descriptor, name = tempfile.mkstemp(prefix=prefix, dir=str(directory))
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
    except Exception:
        try:
            os.unlink(name)
        except OSError:
            pass
        raise
    return Path(name)


def validate_input_authority(
    repo,
    build_dir,
    kernel_dir,
    hfs,
    hfs_file,
    hfs_data,
    flow_capture,
    flow_file,
    historical_ef58,
    repository_authority=None,
):
    """Select immutable historical replay or fresh current-HEAD replay."""

    if type(historical_ef58) is not bool:
        raise FlowV2Error("historical authority selector must be a boolean")
    if historical_ef58:
        if not strict_equal(hfs_file, EXPECTED_HFS_ARTIFACT):
            raise FlowV2Error(
                "historical failure-site bytes differ from archived ef58860e HFS"
            )
        if not strict_equal(flow_file, EXPECTED_V1_FLOW_ARTIFACT):
            raise FlowV2Error(
                "historical failure-flow bytes differ from archived ef58860e v1"
            )
        validate_exact_hfs_authority(hfs, EXPECTED_HFS_PROVENANCE)
        return HISTORICAL_AUTHORITY_MODE

    if build_dir is None or kernel_dir is None:
        raise FlowV2Error(
            "fresh authority mode requires both build and kernel directories"
        )
    build_dir = Path(build_dir).resolve()
    kernel_dir = Path(kernel_dir).resolve()
    if not build_dir.is_dir() or not kernel_dir.is_dir():
        raise FlowV2Error("fresh replay build or kernel directory does not exist")
    try:
        authority = repository_authority or sites.capture_repository_authority(repo)
        current_head = authority["main_head"]
        replayed_hfs = sites.build_capture(
            repo,
            build_dir,
            kernel_dir,
            repository_authority=authority,
        )
    except sites.CaptureError as exc:
        raise FlowV2Error("fresh failure-site replay failed: {0}".format(exc))
    replayed_provenance = replayed_hfs.get("provenance", {})
    if not strict_equal(
        replayed_provenance.get("repository_commit"), current_head
    ):
        raise FlowV2Error("fresh failure-site replay is not bound to current HEAD")
    validate_exact_hfs_authority(hfs, replayed_provenance)
    if not strict_equal(hfs, replayed_hfs):
        raise FlowV2Error("fresh failure-site replay differs from supplied HFS")

    try:
        snapshot = write_private_snapshot(
            build_dir, ".host-module-failure-sites-v2-replay.", hfs_data
        )
    except OSError as exc:
        raise FlowV2Error("cannot snapshot failure-site authority: {0}".format(exc))
    try:
        replayed_v1 = v1_flows.build_capture(
            repo, build_dir, kernel_dir, snapshot
        )
    except (v1_flows.FlowError, sites.CaptureError) as exc:
        raise FlowV2Error("fresh failure-flow replay failed: {0}".format(exc))
    finally:
        try:
            snapshot.unlink()
        except OSError:
            pass
    if not strict_equal(flow_capture, replayed_v1):
        raise FlowV2Error("fresh failure-flow replay differs from supplied v1")
    try:
        sites.recheck_repository_authority(repo, authority)
        final_head = sites.git_head(repo)
    except sites.CaptureError as exc:
        raise FlowV2Error("cannot recheck fresh repository authority: {0}".format(exc))
    if not strict_equal(final_head, current_head):
        raise FlowV2Error("repository HEAD changed during fresh authority replay")
    return FRESH_AUTHORITY_MODE


def validate_v1_inputs(hfs, hfs_file, flow_capture, flow_file):
    try:
        hfs_sources = v1_flows.validate_input_shape(hfs)
    except v1_flows.FlowError as exc:
        raise FlowV2Error("v1 failure-site artifact is invalid: {0}".format(exc))
    if hfs.get("generator") != "scripts/host_module_failure_sites.py":
        raise FlowV2Error("v1 failure-site generator changed")
    if set(flow_capture) != gaps.FLOW_TOP_LEVEL_KEYS:
        raise FlowV2Error("v1 failure-flow top-level schema changed")
    if (
        not strict_equal(flow_capture.get("schema_version"), v1_flows.SCHEMA_VERSION)
        or not strict_equal(flow_capture.get("profile"), v1_flows.PROFILE)
        or not strict_equal(
            flow_capture.get("generator"), "scripts/host_module_failure_flows.py"
        )
        or not strict_equal(flow_capture.get("analysis_claim"), v1_flows.ANALYSIS_CLAIM)
        or not strict_equal(flow_capture.get("blockers"), list(v1_flows.FIXED_BLOCKERS))
    ):
        raise FlowV2Error("v1 failure-flow authority or bounded claim changed")
    expected_binding = {
        "artifact_bytes": hfs_file["artifact_bytes"],
        "artifact_sha256": hfs_file["artifact_sha256"],
        "profile": hfs["profile"],
        "repository_commit": hfs.get("provenance", {}).get("repository_commit"),
    }
    if not strict_equal(flow_capture.get("input_failure_sites"), expected_binding):
        raise FlowV2Error("v1 failure-flow artifact does not bind exact HFS bytes")

    source_records = flow_capture.get("sources")
    if not isinstance(source_records, list) or len(source_records) != len(
        sites.EXPECTED_SOURCES
    ):
        raise FlowV2Error("v1 failure-flow source closure changed")
    flow_sources = {}
    functions_by_source = {}
    for expected, record in zip(sites.EXPECTED_SOURCES, source_records):
        module, language, source, _ = expected
        if not isinstance(record, dict) or (
            record.get("module"), record.get("language"), record.get("source")
        ) != (module, language, source):
            raise FlowV2Error("v1 failure-flow source identity changed: {0}".format(source))
        hfs_source = hfs_sources[source]
        if record.get("source_sha256") != hfs_source["digests"][
            "effective_source_sha256"
        ]:
            raise FlowV2Error("v1 source digest differs: {0}".format(source))
        flow_sources[source] = record
        function_map = {}
        if language == "c":
            functions = record.get("functions")
            if not isinstance(functions, list):
                raise FlowV2Error("v1 C function records are missing: {0}".format(source))
            for function in functions:
                if not isinstance(function, dict):
                    raise FlowV2Error("v1 C function record is malformed")
                name = function.get("name")
                if not isinstance(name, str) or not name or name in function_map:
                    raise FlowV2Error("v1 C function identity is ambiguous: {0}".format(source))
                try:
                    gaps.validate_function_range(
                        function.get("statement_range"), "{0}:{1}".format(source, name)
                    )
                except gaps.GapError as exc:
                    raise FlowV2Error(str(exc))
                if not HEX_DIGEST.fullmatch(str(function.get("statement_sha256", ""))):
                    raise FlowV2Error("v1 C statement digest is malformed")
                roots = function.get("reachable_entry_roots")
                if not isinstance(roots, list) or roots != sorted(set(roots)):
                    raise FlowV2Error("v1 C entry roots are malformed")
                function_map[name] = function
            if not strict_equal(record.get("function_count"), len(function_map)):
                raise FlowV2Error("v1 C function count differs: {0}".format(source))
        functions_by_source[source] = function_map

    hfs_by_id = {item["id"]: item for item in hfs["failure_sites"]}
    if len(hfs_by_id) != len(hfs["failure_sites"]):
        raise FlowV2Error("v1 failure-site IDs are duplicated")
    validated_flows = []
    flows_by_id = {}
    mapped_by_site = defaultdict(list)
    for record in flow_capture.get("failure_flows", []):
        source = record.get("source") if isinstance(record, dict) else None
        if source not in flow_sources:
            raise FlowV2Error("v1 failure flow names an unknown source")
        try:
            flow = gaps.validate_flow(
                record, flow_sources[source], functions_by_source[source], hfs_by_id
            )
        except gaps.GapError as exc:
            raise FlowV2Error("v1 failure flow is invalid: {0}".format(exc))
        if flow["id"] in flows_by_id:
            raise FlowV2Error("v1 failure-flow IDs are duplicated")
        flows_by_id[flow["id"]] = flow
        validated_flows.append(flow)
        for site_id in flow["origin"].get("first_stage_site_ids", []):
            mapped_by_site[site_id].append(flow["id"])

    unresolved_by_site = defaultdict(list)
    unresolved_records = []
    for record in flow_capture.get("unresolved_paths", []):
        try:
            unresolved, reason_id = gaps.validate_unresolved(
                record, flow_sources, functions_by_source, hfs_by_id
            )
        except gaps.GapError as exc:
            raise FlowV2Error("v1 unresolved path is invalid: {0}".format(exc))
        unresolved_records.append((unresolved, reason_id))
        for site_id in unresolved.get("first_stage_site_ids", []):
            unresolved_by_site[site_id].append(reason_id)
    try:
        gaps.validate_exact_site_dispositions(
            set(hfs_by_id), mapped_by_site, unresolved_by_site
        )
    except gaps.GapError as exc:
        raise FlowV2Error("v1 HFS disposition closure is invalid: {0}".format(exc))
    expected_flow_order = sorted(
        validated_flows,
        key=lambda item: (
            item["module"], item["source"], item["location"]["line"],
            item["location"]["column"] or 0, item["expression_role"], item["id"],
        ),
    )
    if validated_flows != expected_flow_order:
        raise FlowV2Error("v1 failure flows are not in canonical order")
    unresolved_values = [record for record, _ in unresolved_records]
    if unresolved_values != sorted(
        {canonical_bytes(record): record for record in unresolved_values}.values(),
        key=canonical_bytes,
    ):
        raise FlowV2Error("v1 unresolved paths are duplicated or not canonical")
    by_module = Counter(flow["module"] for flow in validated_flows)
    by_role = Counter(flow["expression_role"] for flow in validated_flows)
    expected_coverage = {
        "by_module": dict(sorted(by_module.items())),
        "by_role": dict(sorted(by_role.items())),
        "c_source_count": sum(
            record["language"] == "c" for record in flow_sources.values()
        ),
        "explicit_failure_site_input_count": len(hfs_by_id),
        "explicit_failure_site_mapped_count": len(
            set(mapped_by_site) | set(unresolved_by_site)
        ),
        "flow_count": len(validated_flows),
        "function_count": sum(len(value) for value in functions_by_source.values()),
        "rust_source_count": sum(
            record["language"] == "rust" for record in flow_sources.values()
        ),
        "source_count": len(flow_sources),
        "unresolved_count": len(unresolved_records),
    }
    if not strict_equal(flow_capture.get("coverage"), expected_coverage):
        raise FlowV2Error("v1 failure-flow coverage summary is stale")
    flows_by_source = Counter(flow["source"] for flow in validated_flows)
    unresolved_by_source = Counter(record["source"] for record, _ in unresolved_records)
    for source, record in flow_sources.items():
        if (
            not strict_equal(record.get("flow_count"), flows_by_source[source])
            or not strict_equal(
                record.get("unresolved_count"), unresolved_by_source[source]
            )
        ):
            raise FlowV2Error("v1 per-source flow totals differ: {0}".format(source))
    unresolved_kind_counts = Counter(
        record["kind"] for record, _ in unresolved_records
    )
    if (
        unresolved_kind_counts["return_value_error_domain_unresolved"]
        != EXPECTED_SEMANTIC_DOMAIN_UNRESOLVED_COUNT
        or unresolved_kind_counts["rust_failure_site_mir_not_captured"]
        != EXPECTED_RUST_MIR_UNRESOLVED_COUNT
    ):
        raise FlowV2Error("v1 semantic-domain or Rust-MIR gap closure changed")
    return {
        "flows": validated_flows,
        "flows_by_id": flows_by_id,
        "flow_sources": flow_sources,
        "functions_by_source": functions_by_source,
        "hfs_by_id": hfs_by_id,
        "hfs_sources": hfs_sources,
        "mapped_by_site": mapped_by_site,
        "unresolved_by_site": unresolved_by_site,
        "unresolved_records": unresolved_records,
    }


def upgrade_flow(flow, root):
    v1_flow_sha256 = sha256_bytes(canonical_bytes(flow))
    identity = {
        "analysis_entry_roots": [root],
        "v1_failure_flow_id": flow["id"],
        "v1_failure_flow_sha256": v1_flow_sha256,
        "v1_identity_sha256": flow["identity_sha256"],
    }
    digest = sha256_bytes(canonical_bytes(identity))
    return {
        "active_compile_profile_sha256": flow["active_compile_profile_sha256"],
        "analysis_entry_roots": [root],
        "expression": flow["expression"],
        "expression_role": flow["expression_role"],
        "function": flow["function"],
        "id": "HF2-" + digest[:24].upper(),
        "identity_sha256": digest,
        "location": flow["location"],
        "module": flow["module"],
        "origin": flow["origin"],
        "source": flow["source"],
        "source_sha256": flow["source_sha256"],
        "v1_failure_flow_id": flow["id"],
        "v1_failure_flow_sha256": v1_flow_sha256,
        "v1_identity_sha256": flow["identity_sha256"],
    }


def macro_disposition(repo, site, reason_id):
    try:
        filtered, provenance = contracts.effective_source_text(
            repo, site["source"], "c"
        )
    except Exception as exc:
        raise FlowV2Error("cannot reconstruct macro source: {0}".format(exc))
    if provenance.get("effective_source_sha256") != site["source_sha256"]:
        raise FlowV2Error("macro source digest differs from HFS evidence")
    try:
        physical = sites.resolve_spliced_c_token(
            filtered, site["line"], site["column"], site["expression"]
        )
    except sites.CaptureError as exc:
        raise FlowV2Error("cannot resolve continued macro spelling: {0}".format(exc))
    if not physical.get("macro_name"):
        raise FlowV2Error("ambiguous C site is not a continued macro definition")
    conservative_key = {
        "column": physical["physical_column"],
        "errno": site["errno"],
        "line": physical["physical_line"],
        "module": site["module"],
        "source": site["source"],
    }
    return {
        "analysis_entry_roots": [source_boundary(site["module"], site["source"])],
        "compiler_logical_location": {
            "column": site["column"],
            "line": site["line"],
        },
        "conservative_physical_identity": conservative_key,
        "errno_ordinal": 1,
        "hfs_id": site["id"],
        "kind": "logical_macro_definition",
        "language": "c",
        "macro_name": physical["macro_name"],
        "physical_spelling": {
            "column": physical["physical_column"],
            "end_column": physical["physical_end_column"],
            "line": physical["physical_line"],
            "source_logical_column": physical["source_logical_column"],
        },
        "v1_unresolved_reason_id": reason_id,
    }


def build_capture(
    repo,
    failure_site_path,
    failure_flow_path,
    build_dir=None,
    kernel_dir=None,
    historical_ef58=False,
    repository_authority=None,
):
    repo = Path(repo).resolve()
    if not repo.is_dir():
        raise FlowV2Error("repository root does not exist")
    hfs, hfs_file, hfs_data = read_json_with_bytes(
        failure_site_path, "v1 failure sites"
    )
    flow_capture, flow_file = read_json(failure_flow_path, "v1 failure flows")
    authority_mode = validate_input_authority(
        repo,
        build_dir,
        kernel_dir,
        hfs,
        hfs_file,
        hfs_data,
        flow_capture,
        flow_file,
        historical_ef58,
        repository_authority,
    )
    index = validate_v1_inputs(hfs, hfs_file, flow_capture, flow_file)

    function_root_records = []
    roots_by_function = {}
    for source_record in flow_capture["sources"]:
        if source_record["language"] != "c":
            continue
        for function in source_record["functions"]:
            root = function_boundary(
                source_record["module"], source_record["source"], function["name"]
            )
            key = (source_record["source"], function["name"])
            roots_by_function[key] = root
            function_root_records.append(
                {
                    "analysis_entry_roots": [root],
                    "function": function["name"],
                    "module": source_record["module"],
                    "source": source_record["source"],
                    "statement_range": function["statement_range"],
                    "statement_sha256": function["statement_sha256"],
                }
            )

    upgraded_flows = []
    upgraded_by_v1 = {}
    for flow in index["flows"]:
        root = roots_by_function.get((flow["source"], flow["function"]))
        if root is None:
            raise FlowV2Error("C failure flow has no function-summary boundary")
        upgraded = upgrade_flow(flow, root)
        upgraded_flows.append(upgraded)
        upgraded_by_v1[flow["id"]] = upgraded

    site_dispositions = []
    for site in hfs["failure_sites"]:
        mapped = index["mapped_by_site"].get(site["id"], [])
        unresolved_ids = index["unresolved_by_site"].get(site["id"], [])
        if site["language"] == "c" and mapped:
            upgraded = [upgraded_by_v1[item] for item in mapped]
            roots = sorted(
                {canonical_bytes(root): root for flow in upgraded for root in flow[
                    "analysis_entry_roots"
                ]}.values(),
                key=canonical_bytes,
            )
            site_dispositions.append(
                {
                    "analysis_entry_roots": roots,
                    "hfs_id": site["id"],
                    "kind": "compiler_function_flow",
                    "language": "c",
                    "v1_failure_flow_ids": sorted(mapped),
                    "v2_failure_flow_ids": sorted(flow["id"] for flow in upgraded),
                }
            )
            continue
        if site["language"] == "c" and len(unresolved_ids) == 1:
            reason_id = unresolved_ids[0]
            reason = next(
                value
                for value, candidate_id in index["unresolved_records"]
                if candidate_id == reason_id
            )
            if reason["kind"] != "active_errno_token_has_no_unique_compiler_function":
                raise FlowV2Error("C site retains a non-macro ambiguous disposition")
            site_dispositions.append(
                macro_disposition(repo, site, reason_id)
            )
            continue
        if site["language"] == "rust" and len(unresolved_ids) == 1:
            reason_id = unresolved_ids[0]
            reason = next(
                value
                for value, candidate_id in index["unresolved_records"]
                if candidate_id == reason_id
            )
            if reason["kind"] != "rust_failure_site_mir_not_captured":
                raise FlowV2Error("Rust site does not retain its MIR blocker")
            site_dispositions.append(
                {
                    "hfs_id": site["id"],
                    "kind": "rust_mir_unresolved",
                    "language": "rust",
                    "v1_unresolved_reason_id": reason_id,
                }
            )
            continue
        raise FlowV2Error("site has no supported v2 disposition: {0}".format(site["id"]))

    site_dispositions.sort(key=lambda item: item["hfs_id"])
    if len(site_dispositions) != len(hfs["failure_sites"]):
        raise FlowV2Error("v2 site disposition closure differs")
    if len({item["hfs_id"] for item in site_dispositions}) != len(site_dispositions):
        raise FlowV2Error("v2 site dispositions are duplicated")
    if any(
        item["language"] == "c" and not item.get("analysis_entry_roots")
        for item in site_dispositions
    ):
        raise FlowV2Error("a C site has no analysis-entry root")

    retained_unresolved = [
        {"id": reason_id, **record}
        for record, reason_id in index["unresolved_records"]
        if record["kind"] in (
            "return_value_error_domain_unresolved",
            "rust_failure_site_mir_not_captured",
            "rust_mir_and_cfg_not_captured",
        )
    ]
    retained_unresolved.sort(key=lambda item: item["id"])
    disposition_counts = Counter(item["kind"] for item in site_dispositions)
    language_counts = Counter(item["language"] for item in site_dispositions)
    unresolved_counts = Counter(item["kind"] for item in retained_unresolved)
    if (
        unresolved_counts["return_value_error_domain_unresolved"]
        != EXPECTED_SEMANTIC_DOMAIN_UNRESOLVED_COUNT
        or unresolved_counts["rust_failure_site_mir_not_captured"]
        != EXPECTED_RUST_MIR_UNRESOLVED_COUNT
        or len(retained_unresolved)
        != EXPECTED_SEMANTIC_DOMAIN_UNRESOLVED_COUNT
        + EXPECTED_RUST_MIR_UNRESOLVED_COUNT
    ):
        raise FlowV2Error("retained semantic-domain or Rust-MIR closure changed")
    coverage = {
        "c_ambiguous_failure_site_count": 0,
        "c_external_root_unresolved_count": 0,
        "c_failure_site_count": language_counts["c"],
        "c_failure_site_resolved_count": disposition_counts[
            "compiler_function_flow"
        ]
        + disposition_counts["logical_macro_definition"],
        "c_function_boundary_root_count": len(function_root_records),
        "c_function_count": len(function_root_records),
        "c_macro_definition_site_count": disposition_counts[
            "logical_macro_definition"
        ],
        "explicit_failure_site_disposition_count": len(site_dispositions),
        "explicit_failure_site_input_count": len(hfs["failure_sites"]),
        "failure_flow_count": len(upgraded_flows),
        "rust_failure_site_count": language_counts["rust"],
        "rust_mir_unresolved_site_count": disposition_counts["rust_mir_unresolved"],
        "semantic_domain_unresolved_count": unresolved_counts[
            "return_value_error_domain_unresolved"
        ],
    }
    return {
        "analysis_claim": dict(ANALYSIS_CLAIM),
        "analysis_scope": dict(ANALYSIS_SCOPE),
        "authority_mode": authority_mode,
        "blockers": list(FIXED_BLOCKERS),
        "coverage": coverage,
        "failure_flows": sorted(upgraded_flows, key=lambda item: item["id"]),
        "function_analysis_roots": sorted(
            function_root_records,
            key=lambda item: (item["module"], item["source"], item["function"]),
        ),
        "generator": "scripts/host_module_failure_flows_v2.py",
        "inputs": {
            "failure_flows_v1": {
                **flow_file,
                "profile": flow_capture["profile"],
                "schema_version": flow_capture["schema_version"],
            },
            "failure_sites_v1": {
                **hfs_file,
                "profile": hfs["profile"],
                "repository_commit": hfs.get("provenance", {}).get(
                    "repository_commit"
                ),
                "schema_version": hfs["schema_version"],
            },
        },
        "profile": PROFILE,
        "schema_version": SCHEMA_VERSION,
        "site_dispositions": site_dispositions,
        "unresolved_paths": retained_unresolved,
    }


def write_capture(path, capture):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = (
        json.dumps(capture, allow_nan=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=path.name + ".", dir=str(path.parent)
    )
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_name, path)
    except Exception:
        try:
            os.unlink(temporary_name)
        except OSError:
            pass
        raise


def parse_args(argv):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--build-dir", type=Path)
    parser.add_argument("--kernel-dir", type=Path)
    parser.add_argument("--failure-sites", type=Path, required=True)
    parser.add_argument("--failure-flows", type=Path, required=True)
    parser.add_argument(
        "--historical-ef58",
        action="store_true",
        help="require exact archived ef58860e HFS and v1 bytes instead of fresh replay",
    )
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args(argv)


def main(argv=None, repository_authority=None):
    args = parse_args(argv or sys.argv[1:])
    try:
        if not args.historical_ef58 and repository_authority is None:
            raise FlowV2Error(
                "fresh CLI requires the isolated repository-authority bootstrap"
            )
        capture = build_capture(
            args.repo,
            args.failure_sites,
            args.failure_flows,
            args.build_dir,
            args.kernel_dir,
            args.historical_ef58,
            repository_authority,
        )
        write_capture(args.output, capture)
    except FlowV2Error as exc:
        print("host-module failure-flow v2 capture failed: {0}".format(exc), file=sys.stderr)
        return 1
    print(
        "captured {0}/{1} C failure-site analysis roots; FP-0006 remains IN_PROGRESS".format(
            capture["coverage"]["c_failure_site_resolved_count"],
            capture["coverage"]["c_failure_site_count"],
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
