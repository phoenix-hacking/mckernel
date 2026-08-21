#!/usr/bin/env python3
"""Independently re-derive and review non-crediting FP-0006 semantics v3."""

import sys as _fp0006_entry_sys


if __name__ == "__main__" and not hasattr(
    _fp0006_entry_sys, "_mckernel_fp0006_authority_context"
):
    _fp0006_entry_sys.stderr.write(
        "host-module failure-contract review v3 CLI requires the isolated "
        "failure-site authority launcher; refusing direct execution\n"
    )
    raise SystemExit(2)


import argparse
import json
import sys
from collections import Counter
from pathlib import Path

import host_module_failure_contract_review_v2 as review_v2
import host_module_failure_semantics_v3 as semantics
import host_module_failure_sites as sites


SCHEMA_VERSION = 3
PROFILE = "compiler-backed-host-module-failure-contract-review-v3"
ANALYSIS_CLAIM = {
    "credit_eligible": False,
    "executable_acceptance_coverage": False,
    "exhaustive": False,
    "fp_0006_status": "IN_PROGRESS",
    "semantic_error_domains_proven": False,
    "test_mapped": False,
    "tracker_credit": False,
    "reason": (
        "the independent v3 review confirms only immutable input, compiler, "
        "raw-bundle, schema, source-span, object-equality, and CFG bindings; "
        "semantic oracles and executable acceptance evidence remain absent"
    ),
}


class ReviewV3Error(RuntimeError):
    """Raised when a v3 structural review input changes."""


def validate_semantics(capture, expected):
    try:
        semantics.validate_semantics_output_schema(capture)
    except semantics.SemanticsV3Error as exc:
        raise ReviewV3Error("v3 semantics schema is invalid: {0}".format(exc))
    if not semantics.strict_equal(capture, expected):
        raise ReviewV3Error("v3 semantics artifact is not the exact raw-bundle derivation")
    if (
        type(capture["schema_version"]) is not int
        or capture["schema_version"] != semantics.SCHEMA_VERSION
        or capture["profile"] != semantics.PROFILE
        or capture["generator"] != "scripts/host_module_failure_semantics_v3.py"
        or not semantics.strict_equal(capture["analysis_claim"], semantics.ANALYSIS_CLAIM)
        or not semantics.strict_equal(capture["blockers"], list(semantics.BLOCKERS))
    ):
        raise ReviewV3Error("v3 semantics identity or non-crediting claim changed")

    c_records = capture["c_return_contracts"]
    rust_records = capture["rust_mir_sites"]
    if type(c_records) is not list or type(rust_records) is not list:
        raise ReviewV3Error("v3 semantic record lists are missing")
    if len(c_records) != semantics.EXPECTED_C_ROW_COUNT:
        raise ReviewV3Error("v3 C semantic row closure changed")
    if len(rust_records) != semantics.EXPECTED_RUST_SITE_COUNT:
        raise ReviewV3Error("v3 Rust MIR site closure changed")
    if len({item.get("id") for item in c_records}) != len(c_records):
        raise ReviewV3Error("v3 C semantic IDs are duplicated")
    if len({item.get("hfs_id") for item in rust_records}) != len(rust_records):
        raise ReviewV3Error("v3 Rust HFS bindings are duplicated")

    terminal_count = 0
    terminal_ids = set()
    c_functions = set()
    c_sources = set()
    rows_by_module = Counter()
    for record in c_records:
        semantics.require_exact_keys(
            record,
            {
                "compiler_function", "id", "module", "semantic_disposition",
                "source", "terminals", "v1_unresolved_row",
                "v1_unresolved_row_sha256", "value_domain",
            },
            "C return contract",
        )
        if record["v1_unresolved_row_sha256"] != semantics.sha256_bytes(
            semantics.canonical_bytes(record["v1_unresolved_row"])
        ):
            raise ReviewV3Error("C return contract v1 row digest is stale")
        disposition = semantics.require_exact_keys(
            record["semantic_disposition"],
            {"domain_kind", "proof_inputs", "proof_kind", "status"},
            "C semantic disposition",
        )
        if (
            disposition["status"] != "requires_semantic_oracle"
            or disposition["proof_kind"] != "structural_compiler_evidence_only"
            or disposition["domain_kind"] not in (
                "compiler_numeric_interval_observed", "compiler_domain_unbounded"
            )
            or disposition["proof_inputs"] != [
                "gcc-original", "gcc-gimple", "gcc-ssa", "gcc-evrp", "gcc-vrp"
            ]
        ):
            raise ReviewV3Error("C semantic disposition overclaims its evidence")
        value_domain = semantics.require_exact_keys(
            record["value_domain"],
            {"intervals", "negative_numeric_values_are_not_semantic_errno_proof"},
            "C value domain",
        )
        if (
            value_domain["negative_numeric_values_are_not_semantic_errno_proof"]
            is not True
            or type(value_domain["intervals"]) is not list
        ):
            raise ReviewV3Error("C numeric domain is treated as semantic proof")
        for interval in value_domain["intervals"]:
            semantics.require_exact_keys(
                interval, {"high", "low", "ssa_name"}, "C value interval"
            )
            for field in ("high", "low", "ssa_name"):
                semantics.require_string(interval[field], "C value interval " + field)
        terminals = record["terminals"]
        if type(terminals) is not list or len(terminals) not in (1, 2):
            raise ReviewV3Error("C return contract terminal closure changed")
        terminal_count += len(terminals)
        rows_by_module[record["module"]] += 1
        c_sources.add(record["source"])
        c_functions.add((record["source"], record["compiler_function"]["name"]))
        for terminal in terminals:
            semantics.require_exact_keys(
                terminal,
                {
                    "compiler_generic", "compiler_ssa", "hff_id", "hff_sha256",
                    "source_span", "vrp_intervals",
                },
                "C terminal",
            )
            semantics.require_digest(terminal["hff_sha256"], "C terminal HFF digest")
            if terminal["hff_id"] in terminal_ids:
                raise ReviewV3Error("C terminal HFF bindings are duplicated")
            terminal_ids.add(terminal["hff_id"])
            if type(terminal["vrp_intervals"]) is not list:
                raise ReviewV3Error("C terminal VRP interval list is missing")
    if terminal_count != semantics.EXPECTED_C_TERMINAL_COUNT:
        raise ReviewV3Error("C return terminal count changed")
    if dict(sorted(rows_by_module.items())) != semantics.EXPECTED_C_ROWS_BY_MODULE:
        raise ReviewV3Error("C semantic module closure changed")
    if (
        len(c_functions) != semantics.EXPECTED_C_FUNCTION_COUNT
        or len(c_sources) != semantics.EXPECTED_C_SOURCE_COUNT
    ):
        raise ReviewV3Error("C function/source closure changed")

    mapping_counts = Counter()
    for record in rust_records:
        semantics.require_exact_keys(
            record,
            {
                "candidates", "errno", "errno_negative_value", "hfs_id", "id",
                "mapping_status", "semantic_status", "source", "token_span",
            },
            "Rust MIR site",
        )
        if record["semantic_status"] != "requires_semantic_oracle":
            raise ReviewV3Error("Rust MIR site overclaims semantic resolution")
        if type(record["errno_negative_value"]) is not int or record["errno_negative_value"] >= 0:
            raise ReviewV3Error("Rust MIR errno value is not negative")
        candidates = record["candidates"]
        if type(candidates) is not list or not candidates:
            raise ReviewV3Error("Rust MIR site has no structural mapping")
        for candidate in candidates:
            semantics.require_exact_keys(
                candidate,
                {
                    "basic_block", "body_id", "cfg_sha256", "errno_negative_value",
                    "mir_span", "owner", "reachable_from_bb0", "stage",
                },
                "Rust MIR candidate",
            )
            if (
                candidate["reachable_from_bb0"] is not True
                or candidate["errno_negative_value"] != record["errno_negative_value"]
            ):
                raise ReviewV3Error("Rust MIR candidate reachability/value binding differs")
            semantics.require_digest(candidate["cfg_sha256"], "Rust MIR CFG digest")
        mapping_counts[record["mapping_status"]] += 1
    return {
        "c_function_count": len(c_functions),
        "c_return_contract_count": len(c_records),
        "c_source_count": len(c_sources),
        "c_terminal_count": terminal_count,
        "rust_mir_site_count": len(rust_records),
        "rust_mir_site_count_by_mapping_status": dict(sorted(mapping_counts.items())),
    }


def validate_review_output_schema(result):
    """Validate the independent review JSON before it can be serialized."""

    try:
        semantics.validate_type_strict_json(result, "v3 contract review")
        semantics.require_exact_keys(
            result,
            {
                "analysis_claim", "authority_mode", "blockers", "coverage",
                "generator", "inputs", "profile", "schema_version",
                "structural_findings",
            },
            "v3 contract review",
        )
        semantics.require_exact_integer(
            result["schema_version"], SCHEMA_VERSION,
            "v3 contract review schema version",
        )
        semantics.require_enum(
            result["authority_mode"],
            {
                semantics.flows_v2.FRESH_AUTHORITY_MODE,
                semantics.flows_v2.HISTORICAL_AUTHORITY_MODE,
            },
            "v3 contract review authority mode",
        )
        if (
            result["profile"] != PROFILE
            or result["generator"]
            != "scripts/host_module_failure_contract_review_v3.py"
            or not semantics.strict_equal(result["analysis_claim"], ANALYSIS_CLAIM)
            or not semantics.strict_equal(result["blockers"], list(semantics.BLOCKERS))
        ):
            raise semantics.SemanticsV3Error(
                "v3 contract review identity or non-crediting claim changed"
            )
        inputs = semantics.require_exact_keys(
            result["inputs"],
            {"failure_contract_review_v2", "failure_semantics_v3", "raw_bundle"},
            "v3 contract review inputs",
        )
        for name in ("failure_contract_review_v2", "failure_semantics_v3"):
            semantics.validate_artifact_binding(
                inputs[name], "v3 contract review input " + name
            )
        semantics.validate_raw_bundle_record(
            inputs["raw_bundle"], "v3 contract review raw bundle"
        )
        finding_keys = {
            "c_function_count", "c_return_contract_count", "c_source_count",
            "c_terminal_count", "rust_mir_site_count",
            "rust_mir_site_count_by_mapping_status",
        }
        findings = semantics.require_exact_keys(
            result["structural_findings"], finding_keys,
            "v3 contract review structural findings",
        )
        coverage = semantics.require_exact_keys(
            result["coverage"],
            finding_keys
            | {
                "semantic_error_domain_resolved_count", "tracker_credit_count",
                "v2_compiler_active_mapping_count",
            },
            "v3 contract review coverage",
        )
        for mapping, label in (
            (findings, "v3 contract review structural findings"),
            (coverage, "v3 contract review coverage"),
        ):
            for field in sorted(set(mapping) - {"rust_mir_site_count_by_mapping_status"}):
                semantics.require_integer(mapping[field], label + " " + field, minimum=0)
            semantics.require_count_map(
                mapping["rust_mir_site_count_by_mapping_status"],
                label + " Rust mapping status",
            )
    except semantics.SemanticsV3Error as exc:
        raise ReviewV3Error("v3 contract review schema is invalid: {0}".format(exc))
    return result


def build_review(
    repo,
    failure_site_path,
    failure_flow_v1_path,
    failure_flow_v2_path,
    contract_review_v2_path,
    semantics_v3_path,
    raw_bundle_path,
    raw_bundle_sha256_path,
    build_dir=None,
    kernel_dir=None,
    historical_ef58=False,
    repository_authority=None,
):
    repo = Path(repo).resolve()
    if not repo.is_dir():
        raise ReviewV3Error("repository root does not exist")
    try:
        expected_v2_review = review_v2.build_review(
            repo, failure_site_path, failure_flow_v1_path, failure_flow_v2_path,
            build_dir, kernel_dir, historical_ef58, repository_authority,
        )
    except review_v2.ReviewV2Error as exc:
        raise ReviewV3Error("cannot re-derive v2 contract review: {0}".format(exc))
    supplied_v2, supplied_v2_file, _ = semantics.read_json_record(
        contract_review_v2_path, "contract review v2"
    )
    if not semantics.strict_equal(supplied_v2, expected_v2_review):
        raise ReviewV3Error("supplied v2 contract review is not its exact derivation")
    try:
        expected_semantics = semantics.build_capture(
            repo, failure_site_path, failure_flow_v1_path, failure_flow_v2_path,
            raw_bundle_path, raw_bundle_sha256_path, build_dir, kernel_dir,
            historical_ef58, repository_authority,
        )
    except semantics.SemanticsV3Error as exc:
        raise ReviewV3Error("cannot re-derive v3 semantics: {0}".format(exc))
    supplied_semantics, semantics_file, _ = semantics.read_json_record(
        semantics_v3_path, "semantics v3"
    )
    findings = validate_semantics(supplied_semantics, expected_semantics)
    coverage = dict(findings)
    coverage.update(
        {
            "semantic_error_domain_resolved_count": 0,
            "tracker_credit_count": 0,
            "v2_compiler_active_mapping_count": supplied_v2["coverage"][
                "compiler_active_mapped_count"
            ],
        }
    )
    result = {
        "analysis_claim": dict(ANALYSIS_CLAIM),
        "authority_mode": expected_semantics["authority_mode"],
        "blockers": list(semantics.BLOCKERS),
        "coverage": coverage,
        "generator": "scripts/host_module_failure_contract_review_v3.py",
        "inputs": {
            "failure_contract_review_v2": {
                **supplied_v2_file,
                "profile": supplied_v2["profile"],
                "schema_version": supplied_v2["schema_version"],
            },
            "failure_semantics_v3": {
                **semantics_file,
                "profile": supplied_semantics["profile"],
                "schema_version": supplied_semantics["schema_version"],
            },
            "raw_bundle": dict(expected_semantics["raw_bundle"]),
        },
        "profile": PROFILE,
        "schema_version": SCHEMA_VERSION,
        "structural_findings": findings,
    }
    validate_review_output_schema(result)
    if repository_authority is not None:
        try:
            sites.recheck_repository_authority(repo, repository_authority)
        except sites.CaptureError as exc:
            raise ReviewV3Error("fresh authority changed during v3 review: {0}".format(exc))
    return result


def parse_args(argv):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--build-dir", type=Path)
    parser.add_argument("--kernel-dir", type=Path)
    parser.add_argument("--failure-sites", type=Path, required=True)
    parser.add_argument("--failure-flows-v1", type=Path, required=True)
    parser.add_argument("--failure-flows-v2", type=Path, required=True)
    parser.add_argument("--failure-contract-review-v2", type=Path, required=True)
    parser.add_argument("--failure-semantics-v3", type=Path, required=True)
    parser.add_argument("--raw-bundle", type=Path, required=True)
    parser.add_argument("--raw-bundle-sha256", type=Path, required=True)
    parser.add_argument("--historical-ef58", action="store_true")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    if not args.historical_ef58 and (args.build_dir is None or args.kernel_dir is None):
        parser.error("fresh mode requires --build-dir and --kernel-dir")
    return args


def main(argv=None, repository_authority=None):
    args = parse_args(argv or sys.argv[1:])
    try:
        if not args.historical_ef58 and repository_authority is None:
            raise ReviewV3Error("fresh CLI requires isolated repository authority")
        review = build_review(
            args.repo, args.failure_sites, args.failure_flows_v1,
            args.failure_flows_v2, args.failure_contract_review_v2,
            args.failure_semantics_v3, args.raw_bundle,
            args.raw_bundle_sha256, args.build_dir, args.kernel_dir,
            args.historical_ef58, repository_authority,
        )
        semantics.atomic_write(
            args.output,
            (json.dumps(review, allow_nan=False, indent=2, sort_keys=True) + "\n").encode("utf-8"),
        )
    except (ReviewV3Error, semantics.SemanticsV3Error) as exc:
        print("host-module failure-contract review v3 failed: {0}".format(exc), file=sys.stderr)
        return 1
    print(
        "reviewed {0} C return questions and {1} Rust MIR sites; FP-0006 remains IN_PROGRESS".format(
            review["coverage"]["c_return_contract_count"],
            review["coverage"]["rust_mir_site_count"],
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
