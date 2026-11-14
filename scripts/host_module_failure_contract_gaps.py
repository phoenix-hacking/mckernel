#!/usr/bin/env python3
"""Bind compiler failure evidence to the legacy behavior contract.

This is deliberately a gap manifest, not an FP-0006 completion oracle.  It
cross-checks the compiler-backed failure-site and bounded failure-flow
artifacts, records the exact differences from the conservative source-derived
behavior contract, and keeps every completion/credit claim false.
"""

import argparse
import hashlib
import json
import os
import re
import sys
import tempfile
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List, Sequence, Set, Tuple

import host_module_contracts as contracts
import host_module_failure_flows as flows
import host_module_failure_sites as sites


SCHEMA_VERSION = 1
PROFILE = "compiler-backed-host-module-failure-contract-gaps-v1"
MAX_JSON_BYTES = 128 * 1024 * 1024
HEX_DIGEST = re.compile(r"^[0-9a-f]{64}$")
FLOW_ID = re.compile(r"^HFF-[0-9A-F]{24}$")
UNRESOLVED_ID = re.compile(r"^HUR-[0-9A-F]{24}$")

ANALYSIS_CLAIM = {
    "credit_eligible": False,
    "executable_acceptance_coverage": False,
    "exhaustive": False,
    "fp_0006_status": "IN_PROGRESS",
    "reason": (
        "this schema reports contract/compiler gaps and bounded flow mappings; "
        "declared acceptance IDs are not executable test results"
    ),
    "test_mapped": False,
}

HFS_TOP_LEVEL_KEYS = {
    "coverage",
    "failure_sites",
    "generator",
    "kernel_configuration",
    "profile",
    "provenance",
    "schema_version",
    "sources",
}
FLOW_TOP_LEVEL_KEYS = {
    "analysis_claim",
    "blockers",
    "coverage",
    "failure_flows",
    "generator",
    "input_failure_sites",
    "profile",
    "schema_version",
    "sources",
    "unresolved_paths",
}
C_HFS_SOURCE_KEYS = {
    "active_target_line_count",
    "command_file",
    "compile_argv",
    "digests",
    "failure_site_count",
    "language",
    "module",
    "post_compile_token_count",
    "post_compile_tokens_sha256",
    "preprocess_argv",
    "preprocessor",
    "source",
}
RUST_HFS_SOURCE_KEYS = {
    "active_target_line_count",
    "command_file",
    "compile_argv",
    "digests",
    "failure_site_count",
    "language",
    "module",
    "post_compile_token_count",
    "post_compile_tokens_sha256",
    "preprocess_argv",
    "preprocessing_mode",
    "recorded_compile_argv_file",
    "recorded_compiler",
    "simplified_command_compiler",
    "source",
}
C_HFS_DIGEST_KEYS = {
    "command_file_sha256",
    "compiler_sha256",
    "config_sha256",
    "effective_source_sha256",
    "preprocessed_sha256",
    "preprocessing_argv_sha256",
    "preprocessor_stderr_sha256",
    "target_preprocessed_sha256",
}
RUST_HFS_DIGEST_KEYS = {
    "command_file_sha256",
    "compiler_sha256",
    "config_sha256",
    "effective_source_sha256",
    "preprocessed_sha256",
    "preprocessing_argv_sha256",
    "recorded_compile_argv_file_sha256",
    "recorded_compile_argv_sha256",
    "target_preprocessed_sha256",
}
COMPILER_KEYS = {
    "bytes",
    "invoked_as",
    "resolved_path",
    "sha256",
    "version_first_line",
    "version_stderr_sha256",
    "version_stdout_sha256",
}
C_FLOW_SOURCE_KEYS = {
    "active_compile_profile",
    "active_compile_profile_sha256",
    "analysis_argv",
    "analysis_status",
    "blockers",
    "flow_count",
    "function_count",
    "functions",
    "language",
    "module",
    "provenance",
    "provenance_sha256",
    "source",
    "source_sha256",
    "unresolved_count",
}
RUST_FLOW_SOURCE_KEYS = {
    "active_compile_profile",
    "active_compile_profile_sha256",
    "analysis_status",
    "blockers",
    "flow_count",
    "function_count",
    "language",
    "module",
    "source",
    "source_sha256",
    "unresolved_count",
}
FLOW_RECORD_KEYS = {
    "active_compile_profile_sha256",
    "expression",
    "expression_role",
    "function",
    "function_range",
    "id",
    "identity_sha256",
    "location",
    "module",
    "origin",
    "provenance_sha256",
    "reachable_entry_roots",
    "source",
    "source_sha256",
}
UNRESOLVED_SCHEMAS = {
    "active_errno_token_has_no_unique_compiler_function": {
        "errno",
        "first_stage_site_ids",
        "kind",
        "line",
        "source",
    },
    "no_compiler_entry_root_reaches_function": {"function", "kind", "source"},
    "return_value_error_domain_unresolved": {
        "function",
        "kind",
        "line",
        "source",
    },
    "rust_failure_site_mir_not_captured": {
        "errno",
        "first_stage_site_ids",
        "kind",
        "line",
        "source",
    },
    "rust_mir_and_cfg_not_captured": {"kind", "source"},
}


class GapError(RuntimeError):
    """Raised when either evidence artifact is malformed or unbound."""


def canonical_bytes(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode(
        "utf-8"
    )


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def pretty(value: object) -> str:
    return json.dumps(value, indent=2, sort_keys=True) + "\n"


def duplicate_rejecting_object(pairs: List[Tuple[str, Any]]) -> Dict[str, Any]:
    result: Dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise GapError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def read_json(path: Path, label: str) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    try:
        data = path.read_bytes()
    except OSError as exc:
        raise GapError(f"cannot read {label} {path}: {exc}") from exc
    if not data or len(data) > MAX_JSON_BYTES:
        raise GapError(f"{label} has an invalid size")
    try:
        value = json.loads(
            data.decode("utf-8"), object_pairs_hook=duplicate_rejecting_object
        )
    except (UnicodeDecodeError, ValueError) as exc:
        if isinstance(exc, GapError):
            raise
        raise GapError(f"cannot parse {label}: {exc}") from exc
    if not isinstance(value, dict):
        raise GapError(f"{label} must be a JSON object")
    return value, {"artifact_bytes": len(data), "artifact_sha256": sha256_bytes(data)}


def require_exact_keys(value: object, expected: Set[str], label: str) -> Dict[str, Any]:
    if not isinstance(value, dict) or set(value) != expected:
        observed = sorted(value) if isinstance(value, dict) else type(value).__name__
        raise GapError(f"{label} schema changed: observed={observed}")
    return value


def require_digest(value: object, label: str) -> str:
    if not isinstance(value, str) or not HEX_DIGEST.fullmatch(value):
        raise GapError(f"{label} is not a SHA-256 digest")
    return value


def require_count(value: object, label: str, minimum: int = 0) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < minimum:
        raise GapError(f"{label} is not an integer >= {minimum}")
    return value


def resolved(path: Path) -> Path:
    try:
        return path.resolve(strict=False)
    except OSError as exc:
        raise GapError(f"cannot resolve {path}: {exc}") from exc


def require_regular_within(path: Path, root: Path, label: str) -> Path:
    if path.is_symlink():
        raise GapError(f"{label} must not be a symlink: {path}")
    candidate = resolved(path)
    base = resolved(root)
    try:
        common = os.path.commonpath((str(candidate), str(base)))
    except ValueError:
        common = ""
    if common != str(base):
        raise GapError(f"{label} escapes {root}: {path}")
    if not candidate.is_file():
        raise GapError(f"{label} is missing or not regular: {path}")
    return candidate


def file_record(path: Path) -> Dict[str, Any]:
    data = path.read_bytes()
    return {"bytes": len(data), "sha256": sha256_bytes(data)}


def validate_compiler_record(value: object, label: str) -> Dict[str, Any]:
    if not isinstance(value, dict) or set(value) not in (
        COMPILER_KEYS,
        COMPILER_KEYS | {"launcher"},
    ):
        raise GapError(f"{label} compiler provenance schema changed")
    require_count(value.get("bytes"), f"{label}.bytes", 1)
    for field in ("invoked_as", "resolved_path", "version_first_line"):
        if not isinstance(value.get(field), str) or not value[field]:
            raise GapError(f"{label}.{field} is missing")
    for field in ("sha256", "version_stderr_sha256", "version_stdout_sha256"):
        require_digest(value.get(field), f"{label}.{field}")
    launcher = value.get("launcher")
    if launcher is not None:
        require_exact_keys(launcher, {"bytes", "resolved_path", "sha256"}, f"{label}.launcher")
        require_count(launcher.get("bytes"), f"{label}.launcher.bytes", 1)
        if not isinstance(launcher.get("resolved_path"), str) or not launcher[
            "resolved_path"
        ]:
            raise GapError(f"{label}.launcher.resolved_path is missing")
        require_digest(launcher.get("sha256"), f"{label}.launcher.sha256")
    return value


def validate_contract(repo: Path) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    contract_path = require_regular_within(
        repo / contracts.CONTRACT_PATH, repo, "behavior contract"
    )
    policy_path = require_regular_within(repo / contracts.POLICY_PATH, repo, "policy")
    inventory_path = require_regular_within(
        repo / contracts.INVENTORY_PATH, repo, "frozen inventory"
    )
    contract, contract_file = read_json(contract_path, "behavior contract")
    policy, _ = read_json(policy_path, "policy")
    inventory, _ = read_json(inventory_path, "frozen inventory")
    try:
        contracts.validate_contract(contract, policy, inventory, repo)
        regenerated = contracts.build_contract(repo, policy, inventory)
        contracts.validate_contract(regenerated, policy, inventory, repo)
    except (contracts.ContractError, contracts.inventory_tool.InventoryError) as exc:
        raise GapError(f"behavior contract validation failed: {exc}") from exc
    if canonical_bytes(contract) != canonical_bytes(regenerated):
        raise GapError("committed behavior contract differs from regeneration")
    contract_file.update(
        {
            "inventory_file_sha256": contract["inventory_file_sha256"],
            "path": str(contracts.CONTRACT_PATH),
            "policy_file_sha256": contract["policy_file_sha256"],
            "profile": contract["inventory_profile"],
            "schema_version": contract["schema_version"],
        }
    )
    return contract, contract_file


def validate_kernel_configuration(value: object) -> Dict[str, Any]:
    config = require_exact_keys(
        value, {"files", "primary_sha256", "sha256"}, "kernel configuration"
    )
    require_digest(config.get("primary_sha256"), "kernel configuration primary")
    require_digest(config.get("sha256"), "kernel configuration aggregate")
    records = config.get("files")
    if not isinstance(records, list) or len(records) < 2:
        raise GapError("kernel configuration file closure is incomplete")
    paths: List[str] = []
    for index, record in enumerate(records):
        require_exact_keys(record, {"bytes", "path", "sha256"}, f"config file {index}")
        require_count(record.get("bytes"), f"config file {index}.bytes", 1)
        if not isinstance(record.get("path"), str) or not record["path"]:
            raise GapError(f"config file {index}.path is missing")
        require_digest(record.get("sha256"), f"config file {index}.sha256")
        paths.append(record["path"])
    if paths != sorted(paths) or len(paths) != len(set(paths)):
        raise GapError("kernel configuration paths are duplicated or unsorted")
    if config["sha256"] != sha256_bytes(canonical_bytes(records)):
        raise GapError("kernel configuration aggregate digest is stale")
    if config["primary_sha256"] not in {record["sha256"] for record in records}:
        raise GapError("kernel primary digest is absent from the configuration closure")
    return config


def source_index(record: Dict[str, Any], roots: Tuple[Tuple[str, Path], ...]) -> int:
    root_map = dict(roots)
    expected = resolved(root_map["$REPO"] / record["source"])
    cwd = root_map["$KERNEL"]
    indexes = []
    for index, word in enumerate(record["compile_argv"]):
        if index == 0 or word.startswith("-"):
            continue
        try:
            candidate = sites.path_from_command(word, cwd)
        except sites.CaptureError:
            continue
        if candidate == expected:
            indexes.append(index)
    if len(indexes) != 1:
        raise GapError(
            f"compiler argv for {record['source']} names the effective source {len(indexes)} times"
        )
    return indexes[0]


def validate_source_records(
    capture: Dict[str, Any], roots: Tuple[Tuple[str, Path], ...]
) -> Dict[str, Dict[str, Any]]:
    config = capture["kernel_configuration"]
    source_site_counts = Counter(site["source"] for site in capture["failure_sites"])
    source_map: Dict[str, Dict[str, Any]] = {}
    for index, (expected, record) in enumerate(
        zip(sites.EXPECTED_SOURCES, capture["sources"])
    ):
        module, language, source_rel, command_rel = expected
        expected_keys = C_HFS_SOURCE_KEYS if language == "c" else RUST_HFS_SOURCE_KEYS
        require_exact_keys(record, expected_keys, f"failure-site source {index}")
        if (
            record.get("module"),
            record.get("language"),
            record.get("source"),
            record.get("command_file"),
        ) != expected:
            raise GapError(f"failure-site source closure changed at {source_rel}")
        require_count(record.get("active_target_line_count"), f"{source_rel} active lines", 1)
        require_count(record.get("failure_site_count"), f"{source_rel} site count")
        require_count(record.get("post_compile_token_count"), f"{source_rel} post token count")
        require_digest(record.get("post_compile_tokens_sha256"), f"{source_rel} post token digest")
        if record["failure_site_count"] != source_site_counts[source_rel]:
            raise GapError(f"failure-site count differs for {source_rel}")
        argv = record.get("compile_argv")
        if (
            not isinstance(argv, list)
            or len(argv) < 2
            or any(not isinstance(word, str) or not word or "\0" in word for word in argv)
        ):
            raise GapError(f"compiler argv is malformed for {source_rel}")
        source_index(record, roots)
        digest_keys = C_HFS_DIGEST_KEYS if language == "c" else RUST_HFS_DIGEST_KEYS
        digests = require_exact_keys(record.get("digests"), digest_keys, f"{source_rel} digests")
        for key, digest in digests.items():
            require_digest(digest, f"{source_rel}.{key}")
        if digests["config_sha256"] != config["sha256"]:
            raise GapError(f"configuration digest differs for {source_rel}")
        if language == "c":
            compiler = validate_compiler_record(record.get("preprocessor"), f"{source_rel} preprocessor")
            if compiler["sha256"] != digests["compiler_sha256"]:
                raise GapError(f"compiler digest differs for {source_rel}")
            if compiler["invoked_as"] != argv[0]:
                raise GapError(f"compiler executable differs from argv for {source_rel}")
            preprocess_argv = record.get("preprocess_argv")
            if not isinstance(preprocess_argv, list):
                raise GapError(f"preprocessor argv is malformed for {source_rel}")
            try:
                expected_preprocess = sites.reconstruct_preprocess_argv(
                    {"compile_argv": argv}, source_index(record, roots)
                )
            except sites.CaptureError as exc:
                raise GapError(f"cannot reconstruct preprocessor argv for {source_rel}: {exc}") from exc
            if preprocess_argv != expected_preprocess:
                raise GapError(f"preprocessor argv differs from compiler argv for {source_rel}")
            if digests["preprocessing_argv_sha256"] != sha256_bytes(
                canonical_bytes(preprocess_argv)
            ):
                raise GapError(f"preprocessor argv digest is stale for {source_rel}")
        else:
            if record.get("preprocess_argv") != [] or record.get("preprocessing_mode") != (
                "exact Rust source; no C preprocessing"
            ):
                raise GapError("Rust preprocessing claim changed")
            recorded = validate_compiler_record(
                record.get("recorded_compiler"), f"{source_rel} recorded compiler"
            )
            simplified = validate_compiler_record(
                record.get("simplified_command_compiler"),
                f"{source_rel} simplified compiler",
            )
            if any(
                item["sha256"] != digests["compiler_sha256"]
                for item in (recorded, simplified)
            ):
                raise GapError("Rust compiler identities differ")
            if recorded["invoked_as"] != argv[0]:
                raise GapError("recorded Rust compiler differs from exact argv")
            if digests["recorded_compile_argv_sha256"] != sha256_bytes(
                canonical_bytes(argv)
            ):
                raise GapError("recorded Rust compiler argv digest is stale")
            if digests["preprocessing_argv_sha256"] != sha256_bytes(canonical_bytes([])):
                raise GapError("Rust empty preprocessing argv digest is stale")
            if digests["preprocessed_sha256"] != digests["effective_source_sha256"]:
                raise GapError("Rust source/preprocessed digests differ")
        source_map[source_rel] = record
    return source_map


def validate_hfs_environment(
    capture: Dict[str, Any],
    repo: Path,
    build_dir: Path,
    kernel_dir: Path,
    roots: Tuple[Tuple[str, Path], ...],
) -> None:
    try:
        actual_config = sites.config_provenance(kernel_dir)
    except sites.CaptureError as exc:
        raise GapError(f"cannot replay kernel configuration: {exc}") from exc
    if canonical_bytes(actual_config) != canonical_bytes(capture["kernel_configuration"]):
        raise GapError("kernel configuration differs from failure-site capture")
    for record in capture["sources"]:
        source_rel = record["source"]
        source_path = require_regular_within(repo / source_rel, repo, "effective source")
        if file_record(source_path)["sha256"] != record["digests"]["effective_source_sha256"]:
            raise GapError(f"effective source differs for {source_rel}")
        command_path = require_regular_within(
            build_dir / record["command_file"], build_dir, "compiler command file"
        )
        try:
            command = sites.parse_kbuild_cmd(command_path)
        except sites.CaptureError as exc:
            raise GapError(f"cannot replay compiler command for {source_rel}: {exc}") from exc
        try:
            sites.verify_command_source(command, source_path, kernel_dir, command_path)
        except sites.CaptureError as exc:
            raise GapError(f"compiler command source differs for {source_rel}: {exc}") from exc
        if command["file"]["sha256"] != record["digests"]["command_file_sha256"]:
            raise GapError(f"compiler command digest differs for {source_rel}")
        for field in ("post_compile_token_count", "post_compile_tokens_sha256"):
            if command[field] != record[field]:
                raise GapError(f"compiler command {field} differs for {source_rel}")
        if record["language"] == "c":
            if command["compile_argv"] != record["compile_argv"]:
                raise GapError(f"compiler argv differs from command file for {source_rel}")
            expected_compiler = record["preprocessor"]
        else:
            argv_path = require_regular_within(
                build_dir / record["recorded_compile_argv_file"],
                build_dir,
                "recorded Rust compiler argv",
            )
            argv_file = file_record(argv_path)
            if argv_file["sha256"] != record["digests"][
                "recorded_compile_argv_file_sha256"
            ]:
                raise GapError("recorded Rust argv file digest differs")
            try:
                recorded_argv = sites.parse_recorded_compile_argv_bytes(
                    argv_path.read_bytes(), str(argv_path)
                )
            except sites.CaptureError as exc:
                raise GapError(f"cannot replay recorded Rust argv: {exc}") from exc
            if recorded_argv != record["compile_argv"]:
                raise GapError("recorded Rust argv differs from failure-site capture")
            try:
                simplified_compiler = sites.compiler_provenance(command["compile_argv"][0])
            except sites.CaptureError as exc:
                raise GapError(f"cannot replay simplified Rust compiler: {exc}") from exc
            if canonical_bytes(simplified_compiler) != canonical_bytes(
                record["simplified_command_compiler"]
            ):
                raise GapError("simplified Rust compiler provenance differs")
            expected_compiler = record["recorded_compiler"]
        try:
            actual_compiler = sites.compiler_provenance(record["compile_argv"][0])
        except sites.CaptureError as exc:
            raise GapError(f"cannot replay compiler provenance for {source_rel}: {exc}") from exc
        if canonical_bytes(actual_compiler) != canonical_bytes(expected_compiler):
            raise GapError(f"compiler provenance differs for {source_rel}")
        source_index(record, roots)


def validate_hfs(
    capture: Dict[str, Any],
    repo: Path,
    build_dir: Path,
    kernel_dir: Path,
    roots: Tuple[Tuple[str, Path], ...],
    replay_environment: bool = True,
) -> Dict[str, Dict[str, Any]]:
    require_exact_keys(capture, HFS_TOP_LEVEL_KEYS, "failure-site artifact")
    if capture.get("schema_version") != sites.SCHEMA_VERSION:
        raise GapError("failure-site schema_version changed")
    if capture.get("profile") != sites.PROFILE:
        raise GapError("failure-site profile changed")
    if capture.get("generator") != "scripts/host_module_failure_sites.py":
        raise GapError("failure-site generator changed")
    try:
        flows.validate_input_shape(capture)
    except flows.FlowError as exc:
        raise GapError(f"failure-site artifact is invalid: {exc}") from exc
    validate_kernel_configuration(capture.get("kernel_configuration"))
    provenance = require_exact_keys(
        capture.get("provenance"),
        {"compatibility_overlay", "frozen_inventory", "ihk_commit", "repository_commit"},
        "failure-site provenance",
    )
    try:
        repository_commit = sites.git_head(repo)
        ihk_commit = sites.git_head(repo / "ihk")
    except sites.CaptureError as exc:
        raise GapError(f"cannot resolve repository provenance: {exc}") from exc
    if provenance.get("repository_commit") != repository_commit:
        raise GapError("failure-site repository commit differs from checkout")
    if provenance.get("ihk_commit") != ihk_commit:
        raise GapError("failure-site IHK commit differs from checkout")
    for field, relative in (
        ("compatibility_overlay", "scripts/patches/ihk-linux-compat.patch"),
        ("frozen_inventory", str(contracts.INVENTORY_PATH)),
    ):
        record = require_exact_keys(provenance.get(field), {"path", "sha256"}, field)
        if record.get("path") != relative:
            raise GapError(f"failure-site {field} path changed")
        evidence_path = require_regular_within(repo / relative, repo, field)
        if file_record(evidence_path)["sha256"] != record.get("sha256"):
            raise GapError(f"failure-site {field} digest differs from checkout")
    source_map = validate_source_records(capture, roots)
    if replay_environment:
        validate_hfs_environment(capture, repo, build_dir, kernel_dir, roots)
    return source_map


def derive_analysis_argv(
    record: Dict[str, Any], roots: Tuple[Tuple[str, Path], ...]
) -> List[str]:
    output = Path("/tmp/mckernel-gap-analysis-output.o")
    try:
        argv = flows.reconstruct_ir_argv(
            record["compile_argv"], source_index(record, roots), output
        )
    except flows.FlowError as exc:
        raise GapError(f"cannot reconstruct analysis argv for {record['source']}: {exc}") from exc
    return flows.normalized_argv(argv, roots, output)


def validate_function_range(value: object, label: str) -> Dict[str, Any]:
    extent = require_exact_keys(
        value,
        {"end_column", "end_line", "kind", "start_column", "start_line"},
        label,
    )
    if extent.get("kind") != "compiler_statement_extent":
        raise GapError(f"{label} kind changed")
    for field in ("end_column", "end_line", "start_column", "start_line"):
        require_count(extent.get(field), f"{label}.{field}", 1)
    if (extent["end_line"], extent["end_column"]) < (
        extent["start_line"],
        extent["start_column"],
    ):
        raise GapError(f"{label} is inverted")
    return extent


def unresolved_identity(record: Dict[str, Any]) -> str:
    return "HUR-" + sha256_bytes(canonical_bytes(record))[:24].upper()


def validate_exact_site_dispositions(
    hfs_ids: Set[str],
    mapped_flow_ids: Dict[str, List[str]],
    unresolved_ids: Dict[str, List[str]],
) -> None:
    observed = set(mapped_flow_ids) | set(unresolved_ids)
    if observed != hfs_ids:
        missing = sorted(hfs_ids - observed)
        unknown = sorted(observed - hfs_ids)
        raise GapError(
            f"HFS/flow mapping closure differs: missing={missing[:3]}, unknown={unknown[:3]}"
        )
    multiply_mapped = sorted(
        site_id
        for site_id in hfs_ids
        if len(mapped_flow_ids.get(site_id, []))
        + len(unresolved_ids.get(site_id, []))
        != 1
    )
    if multiply_mapped:
        raise GapError(f"HFS IDs do not map exactly once: {multiply_mapped[:3]}")


def validate_flow(
    record: object,
    source_record: Dict[str, Any],
    functions: Dict[str, Dict[str, Any]],
    hfs_by_id: Dict[str, Dict[str, Any]],
) -> Dict[str, Any]:
    flow = require_exact_keys(record, FLOW_RECORD_KEYS, "failure-flow record")
    if not isinstance(flow.get("id"), str) or not FLOW_ID.fullmatch(flow["id"]):
        raise GapError("failure-flow ID is malformed")
    for field in (
        "active_compile_profile_sha256",
        "identity_sha256",
        "provenance_sha256",
        "source_sha256",
    ):
        require_digest(flow.get(field), f"{flow['id']}.{field}")
    if flow.get("source") != source_record["source"] or flow.get("module") != source_record[
        "module"
    ]:
        raise GapError(f"failure flow {flow['id']} names the wrong source or module")
    if flow.get("source_sha256") != source_record["source_sha256"]:
        raise GapError(f"failure flow {flow['id']} source digest differs")
    if flow.get("active_compile_profile_sha256") != source_record[
        "active_compile_profile_sha256"
    ]:
        raise GapError(f"failure flow {flow['id']} compiler profile differs")
    if flow.get("provenance_sha256") != source_record.get("provenance_sha256"):
        raise GapError(f"failure flow {flow['id']} IR provenance differs")
    function = functions.get(str(flow.get("function")))
    if function is None:
        raise GapError(f"failure flow {flow['id']} names an unknown function")
    if flow.get("function_range") != function["statement_range"]:
        raise GapError(f"failure flow {flow['id']} function range differs")
    if flow.get("reachable_entry_roots") != function["reachable_entry_roots"]:
        raise GapError(f"failure flow {flow['id']} entry roots differ")
    location = require_exact_keys(flow.get("location"), {"column", "line"}, "flow location")
    require_count(location.get("line"), f"{flow['id']} line", 1)
    require_count(location.get("column"), f"{flow['id']} column", 1)
    extent = validate_function_range(flow.get("function_range"), "flow function range")
    if not extent["start_line"] <= location["line"] <= extent["end_line"]:
        raise GapError(f"failure flow {flow['id']} lies outside its function range")
    if not isinstance(flow.get("expression"), str) or not flow["expression"]:
        raise GapError(f"failure flow {flow['id']} expression is missing")
    if not isinstance(flow.get("expression_role"), str) or not flow["expression_role"]:
        raise GapError(f"failure flow {flow['id']} role is missing")
    if not isinstance(flow.get("origin"), dict):
        raise GapError(f"failure flow {flow['id']} origin is malformed")
    first_stage_ids = flow["origin"].get("first_stage_site_ids", [])
    if not isinstance(first_stage_ids, list) or first_stage_ids != sorted(set(first_stage_ids)):
        raise GapError(f"failure flow {flow['id']} first-stage IDs are malformed")
    for site_id in first_stage_ids:
        site = hfs_by_id.get(site_id)
        if site is None:
            raise GapError(f"failure flow {flow['id']} names unknown HFS ID {site_id}")
        if (
            site["source"] != flow["source"]
            or site["module"] != flow["module"]
            or site["line"] != location["line"]
        ):
            raise GapError(f"failure flow {flow['id']} first-stage location differs")
        origin_errno = flow["origin"].get("errno")
        if origin_errno != site["errno"]:
            raise GapError(f"failure flow {flow['id']} first-stage errno differs")
    identity = {
        "active_compile_profile_sha256": flow["active_compile_profile_sha256"],
        "expression_role": flow["expression_role"],
        "function": flow["function"],
        "function_range": flow["function_range"],
        "location": flow["location"],
        "module": flow["module"],
        "origin": flow["origin"],
        "provenance_sha256": flow["provenance_sha256"],
        "reachable_entry_roots": flow["reachable_entry_roots"],
        "source": flow["source"],
        "source_sha256": flow["source_sha256"],
    }
    digest = sha256_bytes(canonical_bytes(identity))
    if flow["identity_sha256"] != digest or flow["id"] != (
        "HFF-" + digest[:24].upper()
    ):
        raise GapError(f"failure flow {flow['id']} identity is stale")
    return flow


def validate_unresolved(
    value: object,
    source_map: Dict[str, Dict[str, Any]],
    functions_by_source: Dict[str, Dict[str, Dict[str, Any]]],
    hfs_by_id: Dict[str, Dict[str, Any]],
) -> Tuple[Dict[str, Any], str]:
    if not isinstance(value, dict) or value.get("kind") not in UNRESOLVED_SCHEMAS:
        raise GapError("unresolved flow reason has an unknown kind")
    kind = value["kind"]
    record = require_exact_keys(value, UNRESOLVED_SCHEMAS[kind], f"unresolved {kind}")
    source_rel = record.get("source")
    source = source_map.get(str(source_rel))
    if source is None:
        raise GapError(f"unresolved {kind} names an unknown source")
    if "line" in record:
        require_count(record.get("line"), f"unresolved {kind}.line", 1)
    if "errno" in record and record.get("errno") not in flows.LINUX_ERRNO_NAMES:
        raise GapError(f"unresolved {kind} names an unsupported errno")
    if "function" in record and record.get("function") not in functions_by_source.get(
        str(source_rel), {}
    ):
        raise GapError(f"unresolved {kind} names an unknown function")
    first_stage_ids = record.get("first_stage_site_ids", [])
    if not isinstance(first_stage_ids, list) or first_stage_ids != sorted(set(first_stage_ids)):
        raise GapError(f"unresolved {kind} first-stage IDs are malformed")
    if kind == "rust_failure_site_mir_not_captured" and len(first_stage_ids) != 1:
        raise GapError("each Rust MIR gap must bind exactly one HFS ID")
    for site_id in first_stage_ids:
        site = hfs_by_id.get(site_id)
        if site is None:
            raise GapError(f"unresolved {kind} names unknown HFS ID {site_id}")
        if site["source"] != source_rel:
            raise GapError(f"unresolved {kind} HFS source differs")
        if "line" in record and site["line"] != record["line"]:
            raise GapError(f"unresolved {kind} HFS line differs")
        if "errno" in record and site["errno"] != record["errno"]:
            raise GapError(f"unresolved {kind} HFS errno differs")
    reason_id = unresolved_identity(record)
    if not UNRESOLVED_ID.fullmatch(reason_id):
        raise GapError("unresolved reason identity is malformed")
    return record, reason_id


def validate_flow_artifact(
    capture: Dict[str, Any],
    capture_file: Dict[str, Any],
    failure_sites: Dict[str, Any],
    failure_sites_file: Dict[str, Any],
    hfs_source_map: Dict[str, Dict[str, Any]],
    roots: Tuple[Tuple[str, Path], ...],
) -> Dict[str, Any]:
    require_exact_keys(capture, FLOW_TOP_LEVEL_KEYS, "failure-flow artifact")
    if capture.get("schema_version") != flows.SCHEMA_VERSION:
        raise GapError("failure-flow schema_version changed")
    if capture.get("profile") != flows.PROFILE:
        raise GapError("failure-flow profile changed")
    if capture.get("generator") != "scripts/host_module_failure_flows.py":
        raise GapError("failure-flow generator changed")
    if capture.get("analysis_claim") != flows.ANALYSIS_CLAIM:
        raise GapError("failure-flow analysis claim changed or escalated")
    if capture.get("blockers") != list(flows.FIXED_BLOCKERS):
        raise GapError("failure-flow fixed blocker closure changed")
    input_binding = require_exact_keys(
        capture.get("input_failure_sites"),
        {"artifact_bytes", "artifact_sha256", "profile", "repository_commit"},
        "failure-flow input binding",
    )
    if input_binding != {
        "artifact_bytes": failure_sites_file["artifact_bytes"],
        "artifact_sha256": failure_sites_file["artifact_sha256"],
        "profile": failure_sites["profile"],
        "repository_commit": failure_sites["provenance"]["repository_commit"],
    }:
        raise GapError("failure-flow artifact does not bind the exact HFS bytes")
    hfs_by_id = {site["id"]: site for site in failure_sites["failure_sites"]}
    if len(hfs_by_id) != len(failure_sites["failure_sites"]):
        raise GapError("failure-site IDs are duplicated")
    source_map: Dict[str, Dict[str, Any]] = {}
    functions_by_source: Dict[str, Dict[str, Dict[str, Any]]] = {}
    for index, (expected, record) in enumerate(
        zip(sites.EXPECTED_SOURCES, capture.get("sources", []))
    ):
        module, language, source_rel, _ = expected
        expected_keys = C_FLOW_SOURCE_KEYS if language == "c" else RUST_FLOW_SOURCE_KEYS
        require_exact_keys(record, expected_keys, f"failure-flow source {index}")
        if (record.get("module"), record.get("language"), record.get("source")) != (
            module,
            language,
            source_rel,
        ):
            raise GapError(f"failure-flow source closure changed at {source_rel}")
        hfs_source = hfs_source_map[source_rel]
        if record.get("source_sha256") != hfs_source["digests"][
            "effective_source_sha256"
        ]:
            raise GapError(f"failure-flow source digest differs for {source_rel}")
        expected_profile_sha, expected_profile = flows.source_profile(hfs_source, roots)
        if record.get("active_compile_profile") != expected_profile or record.get(
            "active_compile_profile_sha256"
        ) != expected_profile_sha:
            raise GapError(f"failure-flow compiler profile differs for {source_rel}")
        require_count(record.get("flow_count"), f"{source_rel} flow count")
        require_count(record.get("function_count"), f"{source_rel} function count")
        require_count(record.get("unresolved_count"), f"{source_rel} unresolved count")
        blockers = record.get("blockers")
        if not isinstance(blockers, list) or blockers != sorted(set(blockers)):
            raise GapError(f"failure-flow blockers are malformed for {source_rel}")
        if language == "rust":
            if record.get("analysis_status") != "unresolved":
                raise GapError("Rust flow analysis must remain unresolved")
            if blockers != ["rust_mir_and_cfg_not_captured"]:
                raise GapError("Rust flow blocker changed")
            if record["flow_count"] != 0 or record["function_count"] != 0:
                raise GapError("Rust flow artifact claims unsupported MIR/CFG coverage")
            functions_by_source[source_rel] = {}
        else:
            if record.get("analysis_status") != "bounded_compiler_checkpoint":
                raise GapError(f"C flow status changed for {source_rel}")
            provenance = require_exact_keys(
                record.get("provenance"),
                {
                    "analysis_argv_sha256",
                    "cfg_sha256",
                    "cgraph_sha256",
                    "compiler_sha256",
                    "ssa_sha256",
                },
                f"{source_rel} IR provenance",
            )
            for field, digest in provenance.items():
                require_digest(digest, f"{source_rel}.{field}")
            if provenance["compiler_sha256"] != hfs_source["digests"][
                "compiler_sha256"
            ]:
                raise GapError(f"IR compiler digest differs for {source_rel}")
            if record.get("provenance_sha256") != sha256_bytes(
                canonical_bytes(provenance)
            ):
                raise GapError(f"IR provenance digest is stale for {source_rel}")
            analysis_argv = record.get("analysis_argv")
            if analysis_argv != derive_analysis_argv(hfs_source, roots):
                raise GapError(f"analysis argv differs from recorded compiler argv for {source_rel}")
            if provenance["analysis_argv_sha256"] != sha256_bytes(
                canonical_bytes(analysis_argv)
            ):
                raise GapError(f"analysis argv digest is stale for {source_rel}")
            functions = record.get("functions")
            if not isinstance(functions, list):
                raise GapError(f"function records are malformed for {source_rel}")
            function_map: Dict[str, Dict[str, Any]] = {}
            for function in functions:
                require_exact_keys(
                    function,
                    {
                        "name",
                        "reachable_entry_roots",
                        "statement_range",
                        "statement_sha256",
                    },
                    f"{source_rel} function",
                )
                name = function.get("name")
                if not isinstance(name, str) or not name or name in function_map:
                    raise GapError(f"function identity is malformed for {source_rel}")
                validate_function_range(function.get("statement_range"), f"{source_rel}:{name}")
                roots_value = function.get("reachable_entry_roots")
                if not isinstance(roots_value, list) or roots_value != sorted(set(roots_value)):
                    raise GapError(f"function roots are malformed for {source_rel}:{name}")
                require_digest(function.get("statement_sha256"), f"{source_rel}:{name} statements")
                function_map[name] = function
            if record["function_count"] != len(functions):
                raise GapError(f"function count differs for {source_rel}")
            functions_by_source[source_rel] = function_map
        source_map[source_rel] = record
    expected_source_count = len(sites.EXPECTED_SOURCES)
    if len(capture.get("sources", [])) != expected_source_count:
        raise GapError("failure-flow source closure changed")

    all_flows = capture.get("failure_flows")
    if not isinstance(all_flows, list):
        raise GapError("failure-flow records are missing")
    validated_flows: List[Dict[str, Any]] = []
    seen_flow_ids: Set[str] = set()
    mapping_counts: Counter[str] = Counter()
    mapped_flow_ids: Dict[str, List[str]] = defaultdict(list)
    for value in all_flows:
        if not isinstance(value, dict) or value.get("source") not in source_map:
            raise GapError("failure-flow record names an unknown source")
        flow = validate_flow(
            value,
            source_map[value["source"]],
            functions_by_source[value["source"]],
            hfs_by_id,
        )
        if flow["id"] in seen_flow_ids:
            raise GapError(f"duplicate failure-flow ID {flow['id']}")
        seen_flow_ids.add(flow["id"])
        validated_flows.append(flow)
        for site_id in flow["origin"].get("first_stage_site_ids", []):
            mapping_counts[site_id] += 1
            mapped_flow_ids[site_id].append(flow["id"])
    expected_flow_order = sorted(
        validated_flows,
        key=lambda item: (
            item["module"],
            item["source"],
            item["location"]["line"],
            item["location"]["column"] or 0,
            item["expression_role"],
            item["id"],
        ),
    )
    if validated_flows != expected_flow_order:
        raise GapError("failure-flow records are not in canonical order")

    unresolved_values = capture.get("unresolved_paths")
    if not isinstance(unresolved_values, list):
        raise GapError("unresolved failure paths are missing")
    unresolved_records: List[Dict[str, Any]] = []
    unresolved_by_id: Dict[str, Dict[str, Any]] = {}
    unresolved_ids_by_site: Dict[str, List[str]] = defaultdict(list)
    for value in unresolved_values:
        record, reason_id = validate_unresolved(
            value, source_map, functions_by_source, hfs_by_id
        )
        if reason_id in unresolved_by_id:
            raise GapError(f"duplicate unresolved reason ID {reason_id}")
        unresolved_by_id[reason_id] = record
        unresolved_records.append(record)
        for site_id in record.get("first_stage_site_ids", []):
            mapping_counts[site_id] += 1
            unresolved_ids_by_site[site_id].append(reason_id)
    canonical_unresolved = sorted(
        {canonical_bytes(record): record for record in unresolved_records}.values(),
        key=canonical_bytes,
    )
    if unresolved_records != canonical_unresolved:
        raise GapError("unresolved failure paths are duplicated or not canonical")
    validate_exact_site_dispositions(
        set(hfs_by_id), mapped_flow_ids, unresolved_ids_by_site
    )

    by_module = Counter(flow["module"] for flow in validated_flows)
    by_role = Counter(flow["expression_role"] for flow in validated_flows)
    coverage = {
        "by_module": dict(sorted(by_module.items())),
        "by_role": dict(sorted(by_role.items())),
        "c_source_count": sum(1 for item in source_map.values() if item["language"] == "c"),
        "explicit_failure_site_input_count": len(hfs_by_id),
        "explicit_failure_site_mapped_count": len(mapping_counts),
        "flow_count": len(validated_flows),
        "function_count": sum(len(value) for value in functions_by_source.values()),
        "rust_source_count": sum(
            1 for item in source_map.values() if item["language"] == "rust"
        ),
        "source_count": len(source_map),
        "unresolved_count": len(unresolved_records),
    }
    if capture.get("coverage") != coverage:
        raise GapError("failure-flow coverage summary is stale")
    flows_by_source = Counter(flow["source"] for flow in validated_flows)
    unresolved_by_source = Counter(record["source"] for record in unresolved_records)
    for source_rel, record in source_map.items():
        if record["flow_count"] != flows_by_source[source_rel]:
            raise GapError(f"source flow count differs for {source_rel}")
        if record["unresolved_count"] != unresolved_by_source[source_rel]:
            raise GapError(f"source unresolved count differs for {source_rel}")
        expected_blockers = sorted(
            {item["kind"] for item in unresolved_records if item["source"] == source_rel}
        )
        if record["language"] == "rust":
            expected_blockers = ["rust_mir_and_cfg_not_captured"]
        if record["blockers"] != expected_blockers:
            raise GapError(f"source blocker summary differs for {source_rel}")

    capture_file.update(
        {
            "profile": capture["profile"],
            "schema_version": capture["schema_version"],
        }
    )
    return {
        "all_flow_ids": sorted(seen_flow_ids),
        "mapped_flow_ids": {key: sorted(value) for key, value in mapped_flow_ids.items()},
        "unresolved_by_id": unresolved_by_id,
        "unresolved_ids_by_site": {
            key: sorted(value) for key, value in unresolved_ids_by_site.items()
        },
    }


def contract_key(module: str, legacy: Dict[str, Any]) -> Tuple[str, str, int, int, str]:
    try:
        return (
            module,
            str(legacy["source"]),
            int(legacy["line"]),
            int(legacy["column"]),
            str(legacy["errno"]),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise GapError("legacy errno contract identity is malformed") from exc


def site_key(site: Dict[str, Any]) -> Tuple[str, str, int, int, str]:
    return (
        site["module"],
        site["source"],
        site["line"],
        site["column"],
        site["errno"],
    )


def contract_site_record(behavior: Dict[str, Any]) -> Dict[str, Any]:
    legacy = behavior["legacy"]
    return {
        "acceptance_evidence": "declarative_id_only_not_executed_or_verified",
        "behavior_id": behavior["id"],
        "classification": "exact_identity_not_observed_in_compiler_active_capture",
        "column": legacy["column"],
        "declared_acceptance_test_ids": list(behavior["acceptance_test_ids"]),
        "errno": legacy["errno"],
        "line": legacy["line"],
        "module": behavior["module"],
        "source": legacy["source"],
    }


def build_manifest(
    repo: Path,
    contract: Dict[str, Any],
    contract_file: Dict[str, Any],
    hfs: Dict[str, Any],
    hfs_file: Dict[str, Any],
    flow_capture: Dict[str, Any],
    flow_file: Dict[str, Any],
    flow_index: Dict[str, Any],
    roots: Tuple[Tuple[str, Path], ...],
) -> Dict[str, Any]:
    contract_map: Dict[Tuple[str, str, int, int, str], Dict[str, Any]] = {}
    for behavior in contract["behaviors"]:
        if behavior["kind"] != "legacy_errno":
            continue
        key = contract_key(behavior["module"], behavior["legacy"])
        if key in contract_map:
            raise GapError(f"duplicate legacy errno contract identity: {key}")
        contract_map[key] = behavior
    hfs_map = {site_key(site): site for site in hfs["failure_sites"]}
    if len(hfs_map) != len(hfs["failure_sites"]):
        raise GapError("compiler-active failure-site identities are duplicated")

    missing_contract_sites: List[Dict[str, Any]] = []
    site_bindings: List[Dict[str, Any]] = []
    for key, site in sorted(hfs_map.items()):
        behavior = contract_map.get(key)
        if behavior is None:
            contract_mapping = None
            missing_contract_sites.append(
                {
                    "classification": "exact_identity_absent_from_conservative_contract",
                    "column": site["column"],
                    "errno": site["errno"],
                    "hfs_id": site["id"],
                    "line": site["line"],
                    "module": site["module"],
                    "source": site["source"],
                }
            )
        else:
            legacy = behavior["legacy"]
            source_provenance = legacy.get("source_provenance")
            if not isinstance(source_provenance, dict):
                raise GapError(f"contract behavior {behavior['id']} lacks source provenance")
            if (
                source_provenance.get("language") != site["language"]
                or source_provenance.get("effective_source_sha256") != site[
                    "source_sha256"
                ]
                or legacy.get("expression") != site["expression"]
            ):
                raise GapError(f"contract/compiler provenance differs for {site['id']}")
            contract_mapping = {
                "acceptance_evidence": "declarative_id_only_not_executed_or_verified",
                "behavior_id": behavior["id"],
                "declared_acceptance_test_ids": list(
                    behavior["acceptance_test_ids"]
                ),
            }
        mapped = flow_index["mapped_flow_ids"].get(site["id"], [])
        unresolved = flow_index["unresolved_ids_by_site"].get(site["id"], [])
        if bool(mapped) == bool(unresolved):
            raise GapError(f"HFS ID {site['id']} does not have one exclusive flow disposition")
        site_bindings.append(
            {
                "column": site["column"],
                "contract_mapping": contract_mapping,
                "errno": site["errno"],
                "hfs_id": site["id"],
                "line": site["line"],
                "mapped_failure_flow_ids": mapped,
                "module": site["module"],
                "source": site["source"],
                "unresolved_reason_ids": unresolved,
            }
        )

    stale_contract_sites = [
        contract_site_record(contract_map[key])
        for key in sorted(set(contract_map) - set(hfs_map))
    ]
    source_bindings: List[Dict[str, Any]] = []
    flow_sources = {item["source"]: item for item in flow_capture["sources"]}
    for record in hfs["sources"]:
        flow_source = flow_sources[record["source"]]
        normalized_argv = flows.normalized_argv(record["compile_argv"], roots)
        compiler = (
            record["preprocessor"]
            if record["language"] == "c"
            else record["recorded_compiler"]
        )
        source_bindings.append(
            {
                "active_compile_profile_sha256": flow_source[
                    "active_compile_profile_sha256"
                ],
                "command_file": record["command_file"],
                "command_file_sha256": record["digests"]["command_file_sha256"],
                "compile_argv_sha256": sha256_bytes(
                    canonical_bytes(record["compile_argv"])
                ),
                "compiler_provenance_sha256": sha256_bytes(
                    canonical_bytes(compiler)
                ),
                "compiler_sha256": record["digests"]["compiler_sha256"],
                "config_sha256": record["digests"]["config_sha256"],
                "flow_provenance_sha256": flow_source.get("provenance_sha256"),
                "language": record["language"],
                "module": record["module"],
                "normalized_compile_argv_sha256": sha256_bytes(
                    canonical_bytes(normalized_argv)
                ),
                "source": record["source"],
                "source_sha256": record["digests"]["effective_source_sha256"],
            }
        )

    unresolved_reasons = [
        {"id": reason_id, **flow_index["unresolved_by_id"][reason_id]}
        for reason_id in sorted(flow_index["unresolved_by_id"])
    ]
    unresolved_by_kind = Counter(item["kind"] for item in unresolved_reasons)
    mapped_site_count = sum(
        bool(item["mapped_failure_flow_ids"]) for item in site_bindings
    )
    contract_mapped_count = sum(item["contract_mapping"] is not None for item in site_bindings)
    blockers = list(flow_capture["blockers"])
    blockers.append("acceptance_ids_are_declarations_not_executable_results")
    if missing_contract_sites:
        blockers.append("compiler_active_failure_sites_missing_contract_rows")
    if stale_contract_sites:
        blockers.append("conservative_contract_sites_not_compiler_active")
    return {
        "analysis_claim": dict(ANALYSIS_CLAIM),
        "blockers": sorted(set(blockers)),
        "bounded_failure_flow_ids": flow_index["all_flow_ids"],
        "contract_compiler_comparison": {
            "identity_fields": ["module", "source", "line", "column", "errno"],
            "missing_definition": (
                "a compiler-active exact identity has no equal conservative-contract "
                "identity; this does not assert that no semantically related contract row exists"
            ),
            "stale_definition": (
                "a conservative-contract exact identity is absent from this compiler-active "
                "profile; this does not assert dead code across every build profile"
            ),
        },
        "coverage": {
            "bounded_failure_flow_count": len(flow_index["all_flow_ids"]),
            "compiler_active_contract_mapped_count": contract_mapped_count,
            "compiler_active_failure_site_count": len(site_bindings),
            "compiler_active_flow_mapped_count": mapped_site_count,
            "compiler_active_missing_contract_count": len(missing_contract_sites),
            "compiler_active_unresolved_count": len(site_bindings) - mapped_site_count,
            "conservative_contract_failure_site_count": len(contract_map),
            "conservative_stale_contract_count": len(stale_contract_sites),
            "source_count": len(source_bindings),
            "unresolved_path_count": len(unresolved_reasons),
            "unresolved_paths_by_kind": dict(sorted(unresolved_by_kind.items())),
        },
        "generator": "scripts/host_module_failure_contract_gaps.py",
        "inputs": {
            "behavior_contract": contract_file,
            "failure_flows": flow_file,
            "failure_sites": {
                **hfs_file,
                "kernel_configuration_sha256": hfs["kernel_configuration"]["sha256"],
                "profile": hfs["profile"],
                "schema_version": hfs["schema_version"],
            },
            "ihk_commit": hfs["provenance"]["ihk_commit"],
            "repository_commit": hfs["provenance"]["repository_commit"],
        },
        "missing_contract_sites": missing_contract_sites,
        "profile": PROFILE,
        "schema_version": SCHEMA_VERSION,
        "site_bindings": site_bindings,
        "source_provenance": source_bindings,
        "stale_conservative_contract_sites": stale_contract_sites,
        "unresolved_reasons": unresolved_reasons,
    }


def write_manifest(path: Path, manifest: Dict[str, Any], build_dir: Path) -> None:
    path = resolved(path)
    base = resolved(build_dir)
    try:
        common = os.path.commonpath((str(path), str(base)))
    except ValueError:
        common = ""
    if common != str(base):
        raise GapError(f"output escapes build directory: {path}")
    if path.is_symlink():
        raise GapError(f"output must not be a symlink: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    data = pretty(manifest).encode("utf-8")
    descriptor, temporary_name = tempfile.mkstemp(prefix=path.name + ".", dir=str(path.parent))
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_name, str(path))
    except Exception:
        try:
            os.unlink(temporary_name)
        except OSError:
            pass
        raise


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--build-dir", type=Path, required=True)
    parser.add_argument("--kernel-dir", type=Path, required=True)
    parser.add_argument("--failure-sites", type=Path, required=True)
    parser.add_argument("--failure-flows", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args(argv)


def main(argv: Sequence[str]) -> int:
    args = parse_args(argv)
    repo = resolved(args.repo)
    build_dir = resolved(args.build_dir)
    kernel_dir = resolved(args.kernel_dir)
    if not repo.is_dir() or not build_dir.is_dir() or not kernel_dir.is_dir():
        print("host-module failure-contract gap error: repo/build/kernel directory is missing", file=sys.stderr)
        return 2
    try:
        failure_sites_path = require_regular_within(
            args.failure_sites, build_dir, "failure-site artifact"
        )
        failure_flows_path = require_regular_within(
            args.failure_flows, build_dir, "failure-flow artifact"
        )
        contract, contract_file = validate_contract(repo)
        failure_sites, failure_sites_file = read_json(
            failure_sites_path, "failure-site artifact"
        )
        failure_flows, failure_flows_file = read_json(
            failure_flows_path, "failure-flow artifact"
        )
        roots = (("$REPO", repo), ("$BUILD", build_dir), ("$KERNEL", kernel_dir))
        hfs_source_map = validate_hfs(
            failure_sites, repo, build_dir, kernel_dir, roots
        )
        flow_index = validate_flow_artifact(
            failure_flows,
            failure_flows_file,
            failure_sites,
            failure_sites_file,
            hfs_source_map,
            roots,
        )
        manifest = build_manifest(
            repo,
            contract,
            contract_file,
            failure_sites,
            failure_sites_file,
            failure_flows,
            failure_flows_file,
            flow_index,
            roots,
        )
        write_manifest(args.output, manifest, build_dir)
    except (GapError, OSError) as exc:
        print(f"host-module failure-contract gap error: {exc}", file=sys.stderr)
        return 2
    coverage = manifest["coverage"]
    print(
        "captured failure-contract gaps: "
        f"active={coverage['compiler_active_failure_site_count']}, "
        f"missing_contract={coverage['compiler_active_missing_contract_count']}, "
        f"stale_conservative={coverage['conservative_stale_contract_count']}, "
        f"bounded_flows={coverage['bounded_failure_flow_count']}; "
        "FP-0006 remains IN_PROGRESS and credit-ineligible"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
