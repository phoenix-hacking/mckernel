import copy
import unittest
from pathlib import Path

import host_module_failure_contract_review_v3 as review
import host_module_failure_semantics_v3 as semantics


def c_record(number, module):
    function_number = number % semantics.EXPECTED_C_FUNCTION_COUNT
    row = {
        "function": "function_{0}".format(function_number),
        "kind": "return_value_error_domain_unresolved",
        "line": number + 1,
        "source": "source_{0}.c".format(
            function_number % semantics.EXPECTED_C_SOURCE_COUNT
        ),
    }
    row_sha = semantics.sha256_bytes(semantics.canonical_bytes(row))
    terminal = {
        "compiler_generic": {
            "matching_line_count": 1,
            "matching_lines_sha256": "1" * 64,
            "sample": ["return value;"],
        },
        "compiler_ssa": {
            "expression": "return _1;",
            "location": {"column": 1, "line": number + 1},
            "origins": [],
        },
        "hff_id": "HFF-{0:024d}".format(number),
        "hff_sha256": "2" * 64,
        "source_span": {"column": 1, "line": number + 1},
        "vrp_intervals": [],
    }
    return {
        "compiler_function": {
            "name": row["function"],
            "return_type": "long",
            "signature": "long function(void)",
            "ssa_statement_range": {
                "end_column": 1,
                "end_line": number + 1,
                "kind": "compiler_statement_extent",
                "start_column": 1,
                "start_line": number + 1,
            },
        },
        "id": "HFC3-{0:024d}".format(number),
        "module": module,
        "semantic_disposition": {
            "domain_kind": "compiler_domain_unbounded",
            "proof_inputs": ["gcc-original", "gcc-gimple", "gcc-ssa", "gcc-evrp", "gcc-vrp"],
            "proof_kind": "structural_compiler_evidence_only",
            "status": "requires_semantic_oracle",
        },
        "source": row["source"],
        "terminals": [terminal],
        "v1_unresolved_row": row,
        "v1_unresolved_row_sha256": row_sha,
        "value_domain": {
            "intervals": [],
            "negative_numeric_values_are_not_semantic_errno_proof": True,
        },
    }


def rust_record(number):
    candidate = {
        "basic_block": 0,
        "body_id": "crate.body{0}.built.after.mir".format(number),
        "cfg_sha256": "3" * 64,
        "errno_negative_value": -22,
        "mir_span": {
            "end_column": 12,
            "end_line": number + 1,
            "path": "$REPO/executer/kernel/mcctrl/rust/mcctrl_helpers.rs",
            "start_column": 5,
            "start_line": number + 1,
        },
        "owner": "body{0}".format(number),
        "reachable_from_bb0": True,
        "stage": "crate.body{0}.built.after.mir".format(number),
    }
    return {
        "candidates": [candidate],
        "errno": "EINVAL",
        "errno_negative_value": -22,
        "hfs_id": "HFS-{0:024d}".format(number),
        "id": "HFR3-{0:024d}".format(number),
        "mapping_status": "unique_structural_mapping_semantics_unresolved",
        "semantic_status": "requires_semantic_oracle",
        "source": "executer/kernel/mcctrl/rust/mcctrl_helpers.rs",
        "token_span": {
            "column": 5,
            "end_column": 12,
            "line": number + 1,
            "source_sha256": semantics.EXPECTED_RUST["source_sha256"],
        },
    }


def semantics_capture():
    modules = (
        ["ihk"] * semantics.EXPECTED_C_ROWS_BY_MODULE["ihk"]
        + ["ihk_smp_x86_64"] * semantics.EXPECTED_C_ROWS_BY_MODULE["ihk_smp_x86_64"]
        + ["mcctrl"] * semantics.EXPECTED_C_ROWS_BY_MODULE["mcctrl"]
    )
    c_records = [c_record(number, module) for number, module in enumerate(modules)]
    # Three immutable rows have two HFF terminals (205 rows -> 208 terminals).
    for number in range(3):
        duplicate = copy.deepcopy(c_records[number]["terminals"][0])
        duplicate["hff_id"] += "-B"
        duplicate["hff_sha256"] = "4" * 64
        c_records[number]["terminals"].append(duplicate)
    rust_records = [rust_record(number) for number in range(semantics.EXPECTED_RUST_SITE_COUNT)]
    coverage = {
        "c_function_count": semantics.EXPECTED_C_FUNCTION_COUNT,
        "c_return_contract_count": semantics.EXPECTED_C_ROW_COUNT,
        "c_return_contract_count_by_module": dict(semantics.EXPECTED_C_ROWS_BY_MODULE),
        "c_return_contract_count_by_status": {
            "requires_semantic_oracle": semantics.EXPECTED_C_ROW_COUNT
        },
        "c_source_count": semantics.EXPECTED_C_SOURCE_COUNT,
        "c_terminal_count": semantics.EXPECTED_C_TERMINAL_COUNT,
        "rust_mir_body_count": semantics.EXPECTED_RUST_SITE_COUNT,
        "rust_mir_site_count": semantics.EXPECTED_RUST_SITE_COUNT,
        "rust_mir_site_count_by_mapping_status": {
            "unique_structural_mapping_semantics_unresolved": semantics.EXPECTED_RUST_SITE_COUNT
        },
        "semantic_error_domain_resolved_count": 0,
        "tracker_credit_count": 0,
    }
    return {
        "analysis_claim": dict(semantics.ANALYSIS_CLAIM),
        "authority_mode": semantics.flows_v2.HISTORICAL_AUTHORITY_MODE,
        "blockers": list(semantics.BLOCKERS),
        "c_return_contracts": c_records,
        "compiler_invocations": [],
        "coverage": coverage,
        "generator": "scripts/host_module_failure_semantics_v3.py",
        "inputs": {
            "failure_flows_v1": {
                "artifact_bytes": 1,
                "artifact_sha256": "8" * 64,
                "profile": "failure-flow-v1",
                "schema_version": 1,
            },
            "failure_flows_v2": {
                "artifact_bytes": 2,
                "artifact_sha256": "9" * 64,
                "profile": "failure-flow-v2",
                "schema_version": 2,
            },
            "failure_sites_v1": {
                "artifact_bytes": 3,
                "artifact_sha256": "a" * 64,
                "profile": "failure-sites-v1",
                "schema_version": 1,
            },
        },
        "profile": semantics.PROFILE,
        "raw_bundle": {
            "artifact_bytes": 1,
            "artifact_sha256": "5" * 64,
            "manifest_sha256": "6" * 64,
            "sha256_sidecar_bytes": 1,
            "sha256_sidecar_sha256": "7" * 64,
        },
        "rust_mir_sites": rust_records,
        "schema_version": semantics.SCHEMA_VERSION,
        "toolchains": {},
    }


class ReviewV3Tests(unittest.TestCase):
    def setUp(self):
        self.capture = semantics_capture()

    def test_exact_synthetic_semantics_is_structurally_accepted(self):
        findings = review.validate_semantics(self.capture, copy.deepcopy(self.capture))
        self.assertEqual(findings["c_return_contract_count"], 205)
        self.assertEqual(findings["c_function_count"], 166)
        self.assertEqual(findings["c_source_count"], 15)
        self.assertEqual(findings["c_terminal_count"], 208)
        self.assertEqual(findings["rust_mir_site_count"], 420)
        self.assertFalse(review.ANALYSIS_CLAIM["tracker_credit"])

    def test_any_artifact_mutation_fails_exact_derivation(self):
        supplied = copy.deepcopy(self.capture)
        supplied["coverage"]["tracker_credit_count"] = 1
        with self.assertRaisesRegex(review.ReviewV3Error, "exact"):
            review.validate_semantics(supplied, self.capture)

    def test_semantics_numeric_bool_float_aliases_fail_even_if_expected_matches(self):
        mutations = (
            (("schema_version",), True),
            (("schema_version",), 3.0),
            (("coverage", "c_return_contract_count"), True),
            (("coverage", "c_return_contract_count_by_module", "ihk"), 33.0),
            (("inputs", "failure_sites_v1", "artifact_bytes"), True),
            (("raw_bundle", "sha256_sidecar_bytes"), 1.0),
            (("c_return_contracts", 0, "v1_unresolved_row", "line"), True),
            (("rust_mir_sites", 0, "candidates", 0, "basic_block"), False),
        )
        for path, value in mutations:
            with self.subTest(path=path, value=value):
                capture = copy.deepcopy(self.capture)
                target = capture
                for component in path[:-1]:
                    target = target[component]
                target[path[-1]] = value
                with self.assertRaisesRegex(
                    review.ReviewV3Error, "schema is invalid"
                ):
                    review.validate_semantics(capture, copy.deepcopy(capture))

    def test_semantics_boolean_fields_reject_integer_aliases(self):
        capture = copy.deepcopy(self.capture)
        capture["rust_mir_sites"][0]["candidates"][0][
            "reachable_from_bb0"
        ] = 1
        with self.assertRaisesRegex(review.ReviewV3Error, "schema is invalid"):
            review.validate_semantics(capture, copy.deepcopy(capture))

    def test_c_semantic_overclaim_fails(self):
        capture = copy.deepcopy(self.capture)
        capture["c_return_contracts"][0]["semantic_disposition"]["status"] = "proven_error"
        with self.assertRaisesRegex(review.ReviewV3Error, "overclaims"):
            review.validate_semantics(capture, copy.deepcopy(capture))

    def test_c_row_digest_mutation_fails(self):
        capture = copy.deepcopy(self.capture)
        capture["c_return_contracts"][0]["v1_unresolved_row"]["line"] += 1
        with self.assertRaisesRegex(review.ReviewV3Error, "digest"):
            review.validate_semantics(capture, copy.deepcopy(capture))

    def test_c_numeric_domain_cannot_be_promoted_to_semantic_proof(self):
        capture = copy.deepcopy(self.capture)
        capture["c_return_contracts"][0]["value_domain"][
            "negative_numeric_values_are_not_semantic_errno_proof"
        ] = False
        with self.assertRaisesRegex(review.ReviewV3Error, "semantic proof"):
            review.validate_semantics(capture, copy.deepcopy(capture))

    def test_rust_semantic_overclaim_fails(self):
        capture = copy.deepcopy(self.capture)
        capture["rust_mir_sites"][0]["semantic_status"] = "proven_error"
        with self.assertRaisesRegex(review.ReviewV3Error, "schema is invalid"):
            review.validate_semantics(capture, copy.deepcopy(capture))

    def test_rust_cfg_reachability_and_errno_mutations_fail(self):
        capture = copy.deepcopy(self.capture)
        capture["rust_mir_sites"][0]["candidates"][0]["reachable_from_bb0"] = False
        with self.assertRaisesRegex(review.ReviewV3Error, "reachability"):
            review.validate_semantics(capture, copy.deepcopy(capture))
        capture = copy.deepcopy(self.capture)
        capture["rust_mir_sites"][0]["candidates"][0]["errno_negative_value"] = -14
        with self.assertRaisesRegex(review.ReviewV3Error, "binding"):
            review.validate_semantics(capture, copy.deepcopy(capture))

    def test_duplicate_hfs_binding_fails(self):
        capture = copy.deepcopy(self.capture)
        capture["rust_mir_sites"][1]["hfs_id"] = capture["rust_mir_sites"][0]["hfs_id"]
        with self.assertRaisesRegex(review.ReviewV3Error, "duplicated"):
            review.validate_semantics(capture, copy.deepcopy(capture))

    def test_direct_cli_refuses_unisolated_execution(self):
        # The module-level guard is covered structurally: a direct execution
        # cannot reach argparse without the authority context attribute.
        self.assertIn("isolated", Path(review.__file__).read_text(encoding="utf-8"))

    def test_review_output_rejects_numeric_aliases(self):
        findings = review.validate_semantics(
            self.capture, copy.deepcopy(self.capture)
        )
        coverage = dict(findings)
        coverage.update(
            {
                "semantic_error_domain_resolved_count": 0,
                "tracker_credit_count": 0,
                "v2_compiler_active_mapping_count": 0,
            }
        )
        result = {
            "analysis_claim": dict(review.ANALYSIS_CLAIM),
            "authority_mode": semantics.flows_v2.HISTORICAL_AUTHORITY_MODE,
            "blockers": list(semantics.BLOCKERS),
            "coverage": coverage,
            "generator": "scripts/host_module_failure_contract_review_v3.py",
            "inputs": {
                "failure_contract_review_v2": {
                    "artifact_bytes": 1,
                    "artifact_sha256": "b" * 64,
                    "profile": "failure-contract-review-v2",
                    "schema_version": 2,
                },
                "failure_semantics_v3": {
                    "artifact_bytes": 2,
                    "artifact_sha256": "c" * 64,
                    "profile": semantics.PROFILE,
                    "schema_version": semantics.SCHEMA_VERSION,
                },
                "raw_bundle": dict(self.capture["raw_bundle"]),
            },
            "profile": review.PROFILE,
            "schema_version": review.SCHEMA_VERSION,
            "structural_findings": findings,
        }
        review.validate_review_output_schema(result)
        mutations = (
            (("schema_version",), True),
            (("coverage", "tracker_credit_count"), 0.0),
            (("coverage", "rust_mir_site_count_by_mapping_status",
              "unique_structural_mapping_semantics_unresolved"), True),
            (("inputs", "failure_semantics_v3", "schema_version"), 3.0),
            (("inputs", "raw_bundle", "artifact_bytes"), False),
        )
        for path, value in mutations:
            with self.subTest(path=path, value=value):
                mutated = copy.deepcopy(result)
                target = mutated
                for component in path[:-1]:
                    target = target[component]
                target[path[-1]] = value
                with self.assertRaisesRegex(
                    review.ReviewV3Error, "schema is invalid"
                ):
                    review.validate_review_output_schema(mutated)


if __name__ == "__main__":
    unittest.main()
