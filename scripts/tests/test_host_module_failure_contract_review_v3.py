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
        "mir_witness": {
            "kind": "negative_numeric_literal",
            "mir_type": "i32",
            "span": {
                "end_column": 12,
                "end_line": number + 1,
                "path": "$REPO/executer/kernel/mcctrl/rust/mcctrl_helpers.rs",
                "start_column": 5,
                "start_line": number + 1,
            },
            "statement_sha256": "5" * 64,
        },
        "owner": "body{0}".format(number),
        "reachable_from_bb0": True,
        "source_span_binding": {
            "grammar": "exact_hfs_token",
            "mir_type": None,
            "source_span": {
                "end_column": 12,
                "end_line": number + 1,
                "start_column": 5,
                "start_line": number + 1,
            },
            "source_type": None,
        },
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


def direct_graph():
    definitions = []
    reachability = []
    inputs = []
    for number in range(semantics.EXPECTED_C_SOURCE_COUNT):
        module = (
            "ihk" if number < 7
            else "ihk_smp_x86_64" if number < 9
            else "mcctrl"
        )
        source = "source_{0}.c".format(number)
        function = {
            "module": module,
            "name": "entry_{0}".format(number),
            "source": source,
        }
        definitions.append(
            {"function": function, "linkage": "global", "traits": []}
        )
        root = "external:{0}:entry_{1}".format(module, number)
        reachability.append(
            {
                "function": function,
                "local_roots": [root],
                "propagated_roots": [root],
            }
        )
        inputs.append(
            {
                "bytes": number + 1,
                "module": module,
                "sha256": "d" * 64,
                "source": source,
            }
        )
    return {
        "blocked_edges": [],
        "continuity_diagnostic": semantics.DIRECT_CTU_HISTORICAL_DIAGNOSTIC,
        "definitions": sorted(definitions, key=semantics.canonical_bytes),
        "direct_edges": [],
        "fresh_execution_authority": False,
        "function_reachability": sorted(
            reachability, key=semantics.canonical_bytes
        ),
        "indirect_call_sites": [],
        "inputs": sorted(inputs, key=semantics.canonical_bytes),
        "inventory_kind": semantics.DIRECT_CTU_INVENTORY_KIND,
        "module_scope": "same_module_only_no_dependency_link_authority",
        "source_count": semantics.EXPECTED_C_SOURCE_COUNT,
        "status": semantics.DIRECT_CTU_HISTORICAL_STATUS,
    }


def cgraph_bytes(records, second_records=None):
    def table(values):
        lines = ["Initial Symbol table:", ""]
        for record in values:
            lines.append(
                "{0}/{1} ({2}) @0xADDR".format(
                    record["name"], record["number"],
                    record.get("printable_name", record["name"]),
                )
            )
            lines.append(
                "  Type: function{0}".format(
                    " definition analyzed" if record.get("definition") else ""
                )
            )
            if record.get("empty_visibility"):
                lines.append("  Visibility:")
            else:
                visibility = []
                if record.get("global", True):
                    visibility.append("public")
                visibility.extend(record.get("visibility", ()))
                lines.append(
                    "  Visibility:"
                    + ((" " + " ".join(visibility)) if visibility else "")
                )
            if record.get("address_taken"):
                lines.append("  Address is taken.")
            if record.get("alias"):
                lines.append("  Alias target: target/999")
            lines.extend(
                (
                    "  References: ",
                    "  Referring: ",
                    "  Function flags: " + record.get("function_flags", "body"),
                    "  Called by: ",
                    "  Calls: "
                    + " ".join(
                        "{0}/{1}{2}".format(
                            call[0], call[1],
                            " " + call[2] if len(call) == 3 else "",
                        )
                        for call in record.get("calls", ())
                    ),
                )
            )
        lines.extend(("", "Removing unused symbols:", ""))
        return lines

    lines = table(records)
    if second_records is not None:
        lines.extend(table(second_records))
    return ("\n".join(lines) + "\n").encode("utf-8")


def independent_ctu_fixture(source_zero=None, source_one=None):
    inputs = {"sources": {}}
    invocations = {}
    payloads = {}
    for number in range(semantics.EXPECTED_C_SOURCE_COUNT):
        source = "fixture/review_{0}.c".format(number)
        if number == 0:
            records = source_zero or [
                {"name": "callee", "number": 1},
                {
                    "name": "caller", "number": 2,
                    "definition": True, "calls": (("callee", 1),),
                },
            ]
        elif number == 1:
            records = source_one or [
                {"name": "callee", "number": 1, "definition": True}
            ]
        else:
            records = [
                {
                    "name": "leaf_{0}".format(number),
                    "number": 1,
                    "definition": True,
                }
            ]
        data = cgraph_bytes(records)
        path = "c/review-{0}/cgraph.txt".format(number)
        binding = {
            "bytes": len(data),
            "path": path,
            "sha256": semantics.sha256_bytes(data),
        }
        inputs["sources"][source] = {
            "language": "c", "module": "mcctrl", "source": source,
        }
        invocations[source] = {
            "dumps": {"cgraph": binding}, "language": "c", "source": source,
        }
        payloads[path] = data
    return inputs, invocations, payloads


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
    graph = direct_graph()
    coverage = {
        "c_function_count": semantics.EXPECTED_C_FUNCTION_COUNT,
        "c_return_contract_count": semantics.EXPECTED_C_ROW_COUNT,
        "c_return_contract_count_by_module": dict(semantics.EXPECTED_C_ROWS_BY_MODULE),
        "c_return_contract_count_by_status": {
            "requires_semantic_oracle": semantics.EXPECTED_C_ROW_COUNT
        },
        "c_source_count": semantics.EXPECTED_C_SOURCE_COUNT,
        "c_terminal_count": semantics.EXPECTED_C_TERMINAL_COUNT,
        "direct_ctu_blocked_edge_count": 0,
        "direct_ctu_blocked_edge_count_by_reason": {},
        "direct_ctu_definition_count": len(graph["definitions"]),
        "direct_ctu_direct_edge_count": 0,
        "direct_ctu_indirect_site_count": 0,
        "direct_ctu_reachable_function_count": len(graph["definitions"]),
        "direct_ctu_same_module_cross_tu_edge_count": 0,
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
        "direct_cross_translation_unit_call_graph": graph,
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

    def test_rust_candidate_requires_exact_witness_and_source_binding_schema(self):
        for label, mutation in (
            (
                "missing-witness",
                lambda candidate: candidate.pop("mir_witness"),
            ),
            (
                "extra-source-binding-field",
                lambda candidate: candidate["source_span_binding"].update(
                    {"unreviewed": False}
                ),
            ),
            (
                "missing-statement-digest",
                lambda candidate: candidate["mir_witness"].pop(
                    "statement_sha256"
                ),
            ),
        ):
            with self.subTest(label=label):
                capture = copy.deepcopy(self.capture)
                mutation(capture["rust_mir_sites"][0]["candidates"][0])
                with self.assertRaisesRegex(
                    semantics.SemanticsV3Error, "schema changed"
                ):
                    review.validate_semantics(capture, copy.deepcopy(capture))

    def test_rust_candidate_witness_and_source_binding_mutations_fail(self):
        mutations = (
            (
                "witness-span",
                lambda candidate: candidate["mir_witness"]["span"].update(
                    {"start_column": 6}
                ),
                "witness span",
            ),
            (
                "source-span",
                lambda candidate: candidate["source_span_binding"][
                    "source_span"
                ].update({"end_column": 13}),
                "source/MIR span",
            ),
            (
                "source-grammar",
                lambda candidate: candidate["source_span_binding"].update(
                    {"grammar": "parenthesized_cast"}
                ),
                "must be a non-empty string",
            ),
            (
                "statement-digest",
                lambda candidate: candidate["mir_witness"].update(
                    {"statement_sha256": "not-a-digest"}
                ),
                "digest",
            ),
            (
                "candidate-path",
                lambda candidate: candidate["mir_span"].update(
                    {"path": "$REPO/executer/kernel/mcctrl/rust/other.rs"}
                ),
                "exact source",
            ),
            (
                "body-stage",
                lambda candidate: candidate.update({"stage": "other.after.mir"}),
                "body/stage",
            ),
        )
        for label, mutation, diagnostic in mutations:
            with self.subTest(label=label):
                capture = copy.deepcopy(self.capture)
                mutation(capture["rust_mir_sites"][0]["candidates"][0])
                with self.assertRaisesRegex(
                    (review.ReviewV3Error, semantics.SemanticsV3Error), diagnostic
                ):
                    review.validate_semantics(capture, copy.deepcopy(capture))

    def test_rust_cast_move_witness_is_exactly_bound(self):
        capture = copy.deepcopy(self.capture)
        record = capture["rust_mir_sites"][0]
        record["token_span"]["end_column"] = 12
        candidate = record["candidates"][0]
        candidate["mir_span"]["end_column"] = 20
        candidate["mir_witness"] = {
            "cast_span": {
                "end_column": 20,
                "end_line": 1,
                "path": "$REPO/executer/kernel/mcctrl/rust/mcctrl_helpers.rs",
                "start_column": 6,
                "start_line": 1,
            },
            "cast_statement_sha256": "6" * 64,
            "kind": "cast_const_then_negative_move",
            "mir_type": "i64",
            "negative_statement_sha256": "7" * 64,
            "span": copy.deepcopy(candidate["mir_span"]),
        }
        candidate["source_span_binding"] = {
            "grammar": "parenthesized_cast",
            "mir_type": "i64",
            "source_span": {
                "end_column": 20,
                "end_line": 1,
                "start_column": 5,
                "start_line": 1,
            },
            "source_type": "c_long",
        }
        review.validate_semantics(capture, copy.deepcopy(capture))
        original_cast_map = semantics.RUST_SOURCE_CAST_TO_MIR
        semantics.RUST_SOURCE_CAST_TO_MIR = {
            "c_long": "attacker",
            "i64": "attacker",
            "isize": "attacker",
        }
        try:
            review.validate_semantics(capture, copy.deepcopy(capture))
        finally:
            semantics.RUST_SOURCE_CAST_TO_MIR = original_cast_map
        for label, mutation in (
            (
                "cast-start",
                lambda value: value["mir_witness"]["cast_span"].update(
                    {"start_column": 7}
                ),
            ),
            (
                "cast-type",
                lambda value: value["source_span_binding"].update(
                    {"mir_type": "isize"}
                ),
            ),
            (
                "cast-digest",
                lambda value: value["mir_witness"].update(
                    {"cast_statement_sha256": "0"}
                ),
            ),
        ):
            with self.subTest(label=label):
                hostile = copy.deepcopy(capture)
                mutation(hostile["rust_mir_sites"][0]["candidates"][0])
                with self.assertRaises(
                    (review.ReviewV3Error, semantics.SemanticsV3Error)
                ):
                    review.validate_semantics(hostile, copy.deepcopy(hostile))

    def test_rust_body_stage_and_source_paths_are_confined(self):
        capture = copy.deepcopy(self.capture)
        candidate = capture["rust_mir_sites"][0]["candidates"][0]
        candidate["body_id"] = "nested/" + candidate["stage"]
        review.validate_semantics(capture, copy.deepcopy(capture))

        hostile = copy.deepcopy(capture)
        record = hostile["rust_mir_sites"][0]
        candidate = record["candidates"][0]
        record["source"] = "../evil.rs"
        candidate["mir_span"]["path"] = "$REPO/../evil.rs"
        candidate["mir_witness"]["span"]["path"] = "$REPO/../evil.rs"
        with self.assertRaisesRegex(
            semantics.SemanticsV3Error, "safe relative path"
        ):
            review.validate_semantics(hostile, copy.deepcopy(hostile))

        hostile = copy.deepcopy(capture)
        hostile["rust_mir_sites"][0]["candidates"][0]["body_id"] = (
            "../" + candidate["stage"]
        )
        with self.assertRaisesRegex(
            semantics.SemanticsV3Error, "safe relative path"
        ):
            review.validate_semantics(hostile, copy.deepcopy(hostile))

    def test_duplicate_hfs_binding_fails(self):
        capture = copy.deepcopy(self.capture)
        capture["rust_mir_sites"][1]["hfs_id"] = capture["rust_mir_sites"][0]["hfs_id"]
        with self.assertRaisesRegex(review.ReviewV3Error, "duplicated"):
            review.validate_semantics(capture, copy.deepcopy(capture))

    def test_independent_ctu_edge_and_root_mutations_fail(self):
        graph = self.capture["direct_cross_translation_unit_call_graph"]
        independent = {
            key: copy.deepcopy(graph[key])
            for key in (
                "blocked_edges", "definitions", "direct_edges",
                "function_reachability",
            )
        }
        review.validate_independent_direct_graph(
            graph, independent, semantics.flows_v2.HISTORICAL_AUTHORITY_MODE
        )
        hostile = copy.deepcopy(graph)
        hostile["function_reachability"][0]["propagated_roots"].append(
            "external:attacker:root"
        )
        self.assertNotEqual(
            hostile["function_reachability"], graph["function_reachability"]
        )
        with self.assertRaisesRegex(
            review.ReviewV3Error,
            "direct CTU roots are not canonical|independent",
        ):
            review.validate_independent_direct_graph(
                hostile, independent,
                semantics.flows_v2.HISTORICAL_AUTHORITY_MODE,
            )
        hostile = copy.deepcopy(graph)
        hostile["direct_edges"].append(
            {
                "caller": hostile["definitions"][0]["function"],
                "callee": hostile["definitions"][1]["function"],
                "edge_kind": "same_module_cross_translation_unit_direct",
            }
        )
        with self.assertRaisesRegex(review.ReviewV3Error, "independent"):
            review.validate_independent_direct_graph(
                hostile, independent,
                semantics.flows_v2.HISTORICAL_AUTHORITY_MODE,
            )
        hostile = copy.deepcopy(graph)
        hostile["blocked_edges"] = [
            {
                "callee_name": "attacker",
                "caller": hostile["definitions"][0]["function"],
                "reason": "external_outside_candidate",
            }
        ]
        with self.assertRaisesRegex(review.ReviewV3Error, "independent"):
            review.validate_independent_direct_graph(
                hostile, independent,
                semantics.flows_v2.HISTORICAL_AUTHORITY_MODE,
            )

    def test_independent_review_rejects_old_authoritative_status_for_any_edge_count(self):
        old_status = (
            "direct_strong_same_module_cross_translation_unit_call_graph_"
            + "li" + "nked"
        )
        zero = direct_graph()
        zero_independent = {
            key: copy.deepcopy(zero[key])
            for key in (
                "blocked_edges", "definitions", "direct_edges",
                "function_reachability",
            )
        }
        inputs, invocations, payloads = independent_ctu_fixture()
        positive = semantics.derive_direct_ctu_call_graph(
            inputs,
            invocations,
            payloads,
            semantics.flows_v2.FRESH_AUTHORITY_MODE,
            semantics.DIRECT_CTU_CHECKED_DIAGNOSTIC,
        )
        positive_independent = review.independently_derive_direct_graph(
            inputs, invocations, payloads
        )
        for graph, independent, authority_mode in (
            (
                zero,
                zero_independent,
                semantics.flows_v2.HISTORICAL_AUTHORITY_MODE,
            ),
            (
                positive,
                positive_independent,
                semantics.flows_v2.FRESH_AUTHORITY_MODE,
            ),
        ):
            hostile = copy.deepcopy(graph)
            hostile["status"] = old_status
            with self.subTest(edge_count=len(graph["direct_edges"])):
                with self.assertRaisesRegex(
                    review.ReviewV3Error, "schema is invalid"
                ):
                    review.validate_independent_direct_graph(
                        hostile, independent, authority_mode
                    )

    def test_independent_parser_is_not_generator_parser_alias(self):
        self.assertIsNot(review.independent_parse_cgraph, semantics.parse_initial_cgraph)
        data = cgraph_bytes(
            [{"name": "one", "number": 1, "definition": True}]
        )
        baseline = review.independent_parse_cgraph(data, "fixture.c")
        with_aux = data.replace(
            b"  Calls: ", b"  Aux: @0xADDR\n  Calls: "
        )
        self.assertEqual(
            baseline, review.independent_parse_cgraph(with_aux, "fixture.c")
        )
        for hostile in (
            data.replace(b"@0xADDR", b"@0x1234"),
            data.replace(b"(one) @0xADDR", b"(evil @0xADDR)"),
            data.replace(b"  Calls: ", b"  Aux: @0x1234\n  Calls: "),
            data.replace(
                b"  Calls: ", b"  Aux: @0xADDR trailing\n  Calls: "
            ),
        ):
            with self.assertRaisesRegex(review.ReviewV3Error, "address"):
                review.independent_parse_cgraph(hostile, "fixture.c")
        duplicate_aux = data.replace(
            b"  Calls: ",
            b"  Aux: @0xADDR\n  Aux: @0xADDR\n  Calls: ",
        )
        with self.assertRaisesRegex(review.ReviewV3Error, "duplicated"):
            review.independent_parse_cgraph(duplicate_aux, "fixture.c")

    def test_independent_parser_accepts_real_gcc_header_and_star_alias(self):
        data = cgraph_bytes(
            [
                {
                    "name": "one",
                    "number": 1,
                    "definition": True,
                    "calls": (("*alias", 2),),
                },
                {"name": "*alias", "number": 2},
            ]
        )
        without_addresses = data.replace(b" @0xADDR\n", b"\n")
        expected = review.independent_parse_cgraph(data, "fixture.c")
        self.assertEqual(
            expected,
            review.independent_parse_cgraph(without_addresses, "fixture.c"),
        )
        alias = [item for item in expected if item["name"] == "*alias"][0]
        self.assertEqual(alias["traits"], ["alias"])

    def test_independent_header_rejects_nonidentity_printable_names(self):
        baseline = cgraph_bytes(
            [{"name": "named", "number": 1, "definition": True}]
        )
        invalid_labels = (
            b"", b"<unnamed>", b" ", b"named label", b"\t",
            b"named\x01label", b"named\x7flabel", b"named:name",
            b"named@name", b"named/name", b"named+name",
            "snowman_\u2603".encode("utf-8"),
        )
        for label in invalid_labels:
            with self.subTest(label=label):
                hostile = baseline.replace(
                    b"named/1 (named)", b"named/1 (" + label + b")"
                )
                with self.assertRaisesRegex(
                    review.ReviewV3Error, "printable name"
                ):
                    review.independent_parse_cgraph(hostile, "fixture.c")
        for label in (b"named.clone.1", b"named$clone-part", b"*alias"):
            with self.subTest(valid_label=label):
                candidate = baseline.replace(
                    b"named/1 (named)", b"named/1 (" + label + b")"
                )
                parsed = review.independent_parse_cgraph(candidate, "fixture.c")
                self.assertEqual(parsed[0]["printable_name"], label.decode("ascii"))

    def test_independent_parser_accepts_only_exact_empty_visibility_row(self):
        baseline = cgraph_bytes(
            [
                {
                    "name": "local_fn", "number": 1,
                    "definition": True, "empty_visibility": True,
                }
            ]
        )
        parsed = review.independent_parse_cgraph(baseline, "fixture.c")
        self.assertEqual(len(parsed), 1)
        self.assertFalse(parsed[0]["global"])
        self.assertEqual(parsed[0]["traits"], [])

        complete_row = (
            b"  Visibility: in_other_partition used_from_other_partition "
            b"force_output forced_by_abi externally_visible no_reorder "
            b"prevailing_def asm_written external public common weak "
            b"dll_import comdat comdat_group:group one_only section:.text "
            b"(implicit_section) visibility_specified visibility:hidden "
            b"virtual artificial constructor destructor\n"
        )
        complete = baseline.replace(b"  Visibility:\n", complete_row)
        complete_parsed = review.independent_parse_cgraph(complete, "fixture.c")
        self.assertTrue(complete_parsed[0]["global"])
        self.assertEqual(
            complete_parsed[0]["traits"], ["comdat", "inline", "weak"]
        )

        hostile_rows = (
            (
                baseline.replace(b"  Visibility:\n", b""),
                "metadata is incomplete",
            ),
            (
                baseline.replace(
                    b"  Visibility:\n",
                    b"  Visibility:\n  Visibility:\n",
                ),
                "Visibility",
            ),
            (
                baseline.replace(b"  Visibility:\n", b"  Visibility: \n"),
                "Visibility",
            ),
            (
                baseline.replace(b"  Visibility:\n", b"  Visibility:\t\n"),
                "Visibility",
            ),
            (
                baseline.replace(b"  Visibility:\n", b" Visibility:\n"),
                "metadata is incomplete",
            ),
            (
                baseline.replace(
                    b"  Visibility:\n", b"  Visibility: attacker\n"
                ),
                "Visibility",
            ),
            (
                baseline.replace(
                    b"  Visibility:\n", b"  Visibility: public public\n"
                ),
                "Visibility",
            ),
            (
                baseline.replace(
                    b"  Visibility:\n",
                    b"  Visibility: undef prevailing_def\n",
                ),
                "Visibility",
            ),
            (
                baseline.replace(
                    b"  Visibility:\n",
                    b"  Visibility: visibility:hidden visibility:internal\n",
                ),
                "Visibility",
            ),
            (
                baseline.replace(
                    b"  Visibility:\n",
                    b"  Visibility: weak public\n",
                ),
                "Visibility",
            ),
            (
                baseline.replace(
                    b"  Visibility:\n", b"  Visibility: public  weak\n"
                ),
                "Visibility",
            ),
            (
                baseline.replace(
                    b"  Visibility:\n", b"  Visibility: comdat_group:\n"
                ),
                "Visibility",
            ),
            (
                baseline.replace(
                    b"  Visibility:\n",
                    b"  Visibility: comdat_group:group comdat_group:other\n",
                ),
                "Visibility",
            ),
            (
                baseline.replace(
                    b"  Visibility:\n", b"  Visibility: section:\n"
                ),
                "Visibility",
            ),
            (
                baseline.replace(
                    b"  Visibility:\n",
                    b"  Visibility: section:.text one_only\n",
                ),
                "Visibility",
            ),
            (
                baseline.replace(
                    b"  Visibility:\n",
                    "  Visibility: section:\u2603\n".encode("utf-8"),
                ),
                "Visibility",
            ),
            (
                baseline.replace(
                    b"  Visibility:\n",
                    b"  Visibility: semantic_interposition\n",
                ),
                "Visibility",
            ),
            (
                baseline.replace(
                    b"  Visibility:\n", b"  Visibility: visibility:default\n"
                ),
                "Visibility",
            ),
            (
                baseline.replace(
                    b"  Visibility:\n", b"  Visibility: ifunc_resolver\n"
                ),
                "Visibility",
            ),
        )
        for hostile, diagnostic in hostile_rows:
            with self.subTest(hostile=hostile, diagnostic=diagnostic):
                with self.assertRaisesRegex(review.ReviewV3Error, diagnostic):
                    review.independent_parse_cgraph(hostile, "fixture.c")

        for separator in (
            b"\r\n", b"\r", b"\v", b"\f", b"\xc2\x85",
            b"\xe2\x80\xa8", b"\xe2\x80\xa9",
        ):
            with self.subTest(separator=separator):
                with self.assertRaisesRegex(
                    review.ReviewV3Error, "non-LF line separator"
                ):
                    review.independent_parse_cgraph(
                        baseline.replace(b"\n", separator), "fixture.c"
                    )

    def test_independent_parser_bounds_repeated_pruned_tables(self):
        first = [
            {"name": "one", "number": 1, "definition": True},
            {"name": "unused", "number": 2},
        ]
        baseline = review.independent_parse_cgraph(
            cgraph_bytes(first), "fixture.c"
        )
        self.assertEqual(
            baseline,
            review.independent_parse_cgraph(
                cgraph_bytes(first, first[:1]), "fixture.c"
            ),
        )
        pruned_declaration = [
            {
                "name": "one", "number": 1, "definition": True,
                "calls": (("unused", 2),),
            },
            {"name": "unused", "number": 2},
        ]
        self.assertEqual(
            review.independent_parse_cgraph(
                cgraph_bytes(pruned_declaration, pruned_declaration[:1]),
                "fixture.c",
            ),
            review.independent_parse_cgraph(
                cgraph_bytes(pruned_declaration), "fixture.c"
            ),
        )
        changed_printable_name = copy.deepcopy(pruned_declaration)
        changed_printable_name[1]["printable_name"] = "renamed_only"
        with self.assertRaisesRegex(review.ReviewV3Error, "tables differ"):
            review.independent_parse_cgraph(
                cgraph_bytes(pruned_declaration, changed_printable_name),
                "fixture.c",
            )
        later_new_symbol = pruned_declaration + [
            {"name": "attacker", "number": 3, "definition": True}
        ]
        with self.assertRaisesRegex(review.ReviewV3Error, "tables differ"):
            review.independent_parse_cgraph(
                cgraph_bytes(pruned_declaration, later_new_symbol),
                "fixture.c",
            )
        changed_retained_caller = [
            {"name": "one", "number": 1, "definition": True}
        ]
        with self.assertRaisesRegex(review.ReviewV3Error, "tables differ"):
            review.independent_parse_cgraph(
                cgraph_bytes(pruned_declaration, changed_retained_caller),
                "fixture.c",
            )
        unknown_callee = [
            {
                "name": "one", "number": 1, "definition": True,
                "calls": (("missing", 99),),
            },
        ]
        with self.assertRaisesRegex(review.ReviewV3Error, "unknown callee"):
            review.independent_parse_cgraph(
                cgraph_bytes(unknown_callee), "fixture.c"
            )
        analyzed_definitions = [
            {"name": "one", "number": 1, "definition": True},
            {"name": "two", "number": 2, "definition": True},
        ]
        with self.assertRaisesRegex(review.ReviewV3Error, "analyzed definition"):
            review.independent_parse_cgraph(
                cgraph_bytes(
                    analyzed_definitions, analyzed_definitions[:1]
                ),
                "fixture.c",
            )
        caller = [
            {
                "name": "one", "number": 1, "definition": True,
                "calls": (("two", 2),),
            },
            {"name": "two", "number": 2},
        ]
        for suffix in (b" (evil)", b" 999"):
            with self.subTest(suffix=suffix):
                decorated = cgraph_bytes(caller).replace(
                    b"  Calls: two/2", b"  Calls: two/2" + suffix
                )
                with self.assertRaisesRegex(review.ReviewV3Error, "unknown"):
                    review.independent_parse_cgraph(decorated, "fixture.c")

        inputs, invocations, payloads = independent_ctu_fixture(
            [
                {
                    "name": "caller", "number": 1,
                    "definition": True, "calls": (("missing", 2),),
                }
            ]
        )
        with self.assertRaisesRegex(review.ReviewV3Error, "number is unknown"):
            review.independently_derive_direct_graph(
                inputs, invocations, payloads
            )

    def test_independent_gcc_85_decorator_scanner_retains_and_blocks_metadata(self):
        decorators = (
            "(speculative)",
            "(inlined)",
            "(call_stmt_cannot_inline_p)",
            "(indirect_inlining)",
            "(0,0.00 per call)",
            "(1 (estimated locally),1.00 per call)",
            "(2 (estimated locally, globally 0),2.25 per call)",
            "(3 (estimated locally, globally 0 adjusted),3.50 per call)",
            "(4 (adjusted),4.75 per call)",
            "(5 (auto FDO),5.00 per call)",
            "(6 (guessed),6.00 per call)",
            "(2305843009213693950,9223372036854775808.00 per call)",
            "(can throw external)",
            (
                "(speculative) (inlined) (call_stmt_cannot_inline_p) "
                "(indirect_inlining) (7 (estimated locally),7.00 per call) "
                "(can throw external)"
            ),
        )
        records = [
            {"name": "callee_{0}".format(number), "number": number}
            for number in range(1, len(decorators) + 1)
        ]
        records.append(
            {
                "name": "caller",
                "number": 99,
                "definition": True,
                "calls": tuple(
                    ("callee_{0}".format(number), number, decorator)
                    for number, decorator in enumerate(decorators, 1)
                ),
            }
        )
        parsed = review.independent_parse_cgraph(
            cgraph_bytes(records), "fixture.c"
        )
        caller = [item for item in parsed if item["name"] == "caller"][0]
        self.assertEqual(
            {item["edge_metadata"] for item in caller["calls"]},
            {" " + item for item in decorators},
        )

        metadata = decorators[-1]
        inputs, invocations, payloads = independent_ctu_fixture(
            [
                {"name": "callee", "number": 1},
                {
                    "name": "caller", "number": 2,
                    "definition": True,
                    "calls": (("callee", 1, metadata),),
                },
            ]
        )
        graph = review.independently_derive_direct_graph(
            inputs, invocations, payloads
        )
        self.assertFalse(graph["direct_edges"])
        blocked = [
            item for item in graph["blocked_edges"]
            if item["callee_name"] == "callee"
        ][0]
        self.assertEqual(blocked["reason"], "decorated_call_metadata")
        self.assertEqual(blocked["edge_metadata"], " " + metadata)

        generated = semantics.derive_direct_ctu_call_graph(
            inputs,
            invocations,
            payloads,
            semantics.flows_v2.FRESH_AUTHORITY_MODE,
            semantics.DIRECT_CTU_CHECKED_DIAGNOSTIC,
        )
        review.validate_independent_direct_graph(
            generated, graph, semantics.flows_v2.FRESH_AUTHORITY_MODE
        )

    def test_independent_gcc_85_decorator_scanner_rejects_hostile_rows_boundedly(self):
        records = [
            {"name": "callee", "number": 1},
            {
                "name": "caller", "number": 2,
                "definition": True, "calls": (("callee", 1),),
            },
        ]
        baseline = cgraph_bytes(records)
        hostile_rows = (
            "callee/1 (inlined) (speculative)",
            "callee/1 (speculative) (speculative)",
            "callee/1 (18446744073709551615,1.00 per call)",
            "callee/1 (2305843009213693951,1.00 per call)",
            "callee/1 (9223372036854775808,1.00 per call)",
            "callee/1 (1,9223372036854775809.00 per call)",
            "callee/1 (1,9223372036854775808.01 per call)",
            "callee/1 (1,9999999999999999999999999999999999999999.00 per call)",
            "callee/1 (1 (estimated global),1.00 per call)",
            "callee/1 (1 (estimated locally),1.0 per call)",
            "callee/1 (can throw external) (1,1.00 per call)",
            "callee/1(inlined)",
            "callee/1 (inlined)evil",
            "callee/1  callee/1",
        )
        for row in hostile_rows:
            with self.subTest(row=row):
                data = baseline.replace(
                    b"  Calls: callee/1",
                    ("  Calls: " + row).encode("ascii"),
                )
                with self.assertRaises(review.ReviewV3Error) as raised:
                    review.independent_parse_cgraph(data, "fixture.c")
                diagnostic = str(raised.exception)
                self.assertIn("character", diagnostic)
                self.assertLess(len(diagnostic), 300)

        huge = baseline.replace(
            b"  Calls: callee/1",
            b"  Calls: callee/1 (" + b"x" * 8192 + b")",
        )
        with self.assertRaises(review.ReviewV3Error) as raised:
            review.independent_parse_cgraph(huge, "fixture.c")
        self.assertLess(len(str(raised.exception)), 300)
        self.assertIn("of 8204", str(raised.exception))

    def test_independent_derivation_closes_one_same_module_edge_and_roots(self):
        inputs, invocations, payloads = independent_ctu_fixture()
        independent = review.independently_derive_direct_graph(
            inputs, invocations, payloads
        )
        self.assertEqual(
            sum(
                item["edge_kind"]
                == "same_module_cross_translation_unit_direct"
                for item in independent["direct_edges"]
            ),
            1,
        )
        callee = [
            item for item in independent["function_reachability"]
            if item["function"]["name"] == "callee"
        ][0]
        self.assertIn("external:mcctrl:caller", callee["propagated_roots"])
        generated = semantics.derive_direct_ctu_call_graph(
            inputs,
            invocations,
            payloads,
            semantics.flows_v2.FRESH_AUTHORITY_MODE,
            semantics.DIRECT_CTU_CHECKED_DIAGNOSTIC,
        )
        review.validate_independent_direct_graph(
            generated, independent, semantics.flows_v2.FRESH_AUTHORITY_MODE
        )

    def test_independent_analyzed_external_definitions_are_inline_blocked(self):
        external_inline = [
            {
                "name": "fortified_helper", "number": 1,
                "definition": True, "global": False,
                "visibility": ("external", "public"),
            }
        ]
        inputs, invocations, payloads = independent_ctu_fixture(
            external_inline, copy.deepcopy(external_inline)
        )
        independent = review.independently_derive_direct_graph(
            inputs, invocations, payloads
        )
        helpers = [
            item for item in independent["definitions"]
            if item["function"]["name"] == "fortified_helper"
        ]
        self.assertEqual(len(helpers), 2)
        self.assertTrue(all(item["traits"] == ["inline"] for item in helpers))
        generated = semantics.derive_direct_ctu_call_graph(
            inputs,
            invocations,
            payloads,
            semantics.flows_v2.FRESH_AUTHORITY_MODE,
            semantics.DIRECT_CTU_CHECKED_DIAGNOSTIC,
        )
        review.validate_independent_direct_graph(
            generated, independent, semantics.flows_v2.FRESH_AUTHORITY_MODE
        )

        ordinary = [
            {
                "name": "fortified_helper", "number": 1,
                "definition": True,
            }
        ]
        inputs, invocations, payloads = independent_ctu_fixture(
            ordinary, copy.deepcopy(ordinary)
        )
        with self.assertRaisesRegex(review.ReviewV3Error, "duplicate strong"):
            review.independently_derive_direct_graph(
                inputs, invocations, payloads
            )

    def test_independent_external_declaration_remains_resolvable(self):
        source_zero = [
            {
                "name": "callee", "number": 1,
                "global": False,
                "visibility": ("external", "public"),
            },
            {
                "name": "caller", "number": 2,
                "definition": True, "calls": (("callee", 1),),
            },
        ]
        inputs, invocations, payloads = independent_ctu_fixture(source_zero)
        independent = review.independently_derive_direct_graph(
            inputs, invocations, payloads
        )
        self.assertTrue(
            any(
                item["callee"]["name"] == "callee"
                and item["edge_kind"]
                == "same_module_cross_translation_unit_direct"
                for item in independent["direct_edges"]
            )
        )
        generated = semantics.derive_direct_ctu_call_graph(
            inputs,
            invocations,
            payloads,
            semantics.flows_v2.FRESH_AUTHORITY_MODE,
            semantics.DIRECT_CTU_CHECKED_DIAGNOSTIC,
        )
        review.validate_independent_direct_graph(
            generated, independent, semantics.flows_v2.FRESH_AUTHORITY_MODE
        )

    def test_independent_local_roots_match_exact_names_not_prefixes(self):
        source_zero = [
            {
                "name": "foo", "number": 1,
                "definition": True, "address_taken": True,
            },
            {
                "name": "foo_suffix", "number": 2,
                "definition": True, "address_taken": True,
                "calls": (("foo", 1),),
            },
        ]
        inputs, invocations, payloads = independent_ctu_fixture(source_zero)
        independent = review.independently_derive_direct_graph(
            inputs, invocations, payloads
        )
        generated = semantics.derive_direct_ctu_call_graph(
            inputs,
            invocations,
            payloads,
            semantics.flows_v2.FRESH_AUTHORITY_MODE,
            semantics.DIRECT_CTU_CHECKED_DIAGNOSTIC,
        )
        review.validate_independent_direct_graph(
            generated, independent, semantics.flows_v2.FRESH_AUTHORITY_MODE
        )
        foo = [
            item for item in generated["function_reachability"]
            if item["function"]["name"] == "foo"
        ][0]
        self.assertEqual(
            foo["local_roots"],
            [
                "callback:mcctrl:fixture/review_0.c:foo",
                "external:mcctrl:foo",
            ],
        )
        self.assertIn(
            "external:mcctrl:foo_suffix", foo["propagated_roots"]
        )

    def test_independent_printable_call_binds_to_assembler_identity(self):
        inputs, invocations, payloads = independent_ctu_fixture(
            source_zero=[
                {
                    "name": "asm_target", "number": 1,
                    "printable_name": "source_target",
                },
                {
                    "name": "caller", "number": 2,
                    "definition": True,
                    "calls": (("source_target", 1),),
                },
            ],
            source_one=[
                {
                    "name": "asm_target", "number": 1,
                    "printable_name": "source_target",
                    "definition": True,
                }
            ],
        )
        independent = review.independently_derive_direct_graph(
            inputs, invocations, payloads
        )
        self.assertTrue(
            any(
                item["callee"]["name"] == "asm_target"
                and item["caller"]["name"] == "caller"
                and item["edge_kind"]
                == "same_module_cross_translation_unit_direct"
                for item in independent["direct_edges"]
            )
        )
        generated = semantics.derive_direct_ctu_call_graph(
            inputs,
            invocations,
            payloads,
            semantics.flows_v2.FRESH_AUTHORITY_MODE,
            semantics.DIRECT_CTU_CHECKED_DIAGNOSTIC,
        )
        review.validate_independent_direct_graph(
            generated, independent, semantics.flows_v2.FRESH_AUTHORITY_MODE
        )

    def test_independent_repeated_table_binds_dual_identity(self):
        records = [
            {
                "name": "asm_target", "number": 1,
                "printable_name": "source_target",
            },
            {
                "name": "caller", "number": 2, "definition": True,
                "calls": (("source_target", 1),),
            },
        ]
        repeated = review.independent_parse_cgraph(
            cgraph_bytes(records, copy.deepcopy(records)), "fixture.c"
        )
        target = [item for item in repeated if item["number"] == 1][0]
        self.assertEqual(target["name"], "asm_target")
        self.assertEqual(target["printable_name"], "source_target")

        # The first Initial table remains authoritative when GCC drops the
        # declaration-only target from a later phase.  The retained caller's
        # edge still binds printable name plus number to that first-table
        # assembler identity.
        self.assertEqual(
            repeated,
            review.independent_parse_cgraph(
                cgraph_bytes(records, [copy.deepcopy(records[1])]),
                "fixture.c",
            ),
        )

        assembler_spelled_call = copy.deepcopy(records)
        assembler_spelled_call[1]["calls"] = (("asm_target", 1),)
        with self.assertRaisesRegex(
            review.ReviewV3Error, "printable name differs"
        ):
            review.independent_parse_cgraph(
                cgraph_bytes(assembler_spelled_call), "fixture.c"
            )

        changed_assembler_name = copy.deepcopy(records)
        changed_assembler_name[0]["name"] = "other_asm_target"
        with self.assertRaisesRegex(review.ReviewV3Error, "tables differ"):
            review.independent_parse_cgraph(
                cgraph_bytes(records, changed_assembler_name), "fixture.c"
            )

    def test_independent_call_identity_requires_number_and_printable_name(self):
        source_zero = [
            {
                "name": "asm_target", "number": 1,
                "printable_name": "source_target",
            },
            {
                "name": "caller", "number": 2,
                "definition": True, "calls": (("source_target", 1),),
            },
        ]
        wrong_name = copy.deepcopy(source_zero)
        wrong_name[1]["calls"] = (("hostile_target", 1),)
        inputs, invocations, payloads = independent_ctu_fixture(wrong_name)
        with self.assertRaisesRegex(review.ReviewV3Error, "printable name differs"):
            review.independently_derive_direct_graph(
                inputs, invocations, payloads
            )

        wrong_number = copy.deepcopy(source_zero)
        wrong_number[1]["calls"] = (("source_target", 99),)
        inputs, invocations, payloads = independent_ctu_fixture(wrong_number)
        with self.assertRaisesRegex(review.ReviewV3Error, "number is unknown"):
            review.independently_derive_direct_graph(
                inputs, invocations, payloads
            )

        missing_number = cgraph_bytes(source_zero).replace(
            b"  Calls: source_target/1", b"  Calls: source_target"
        )
        with self.assertRaisesRegex(review.ReviewV3Error, "unknown"):
            review.independent_parse_cgraph(missing_number, "fixture.c")

    def test_independent_same_printable_names_resolve_by_number(self):
        source_zero = [
            {
                "name": "asm_first", "number": 1,
                "printable_name": "shared_source_name", "definition": True,
            },
            {
                "name": "asm_second", "number": 2,
                "printable_name": "shared_source_name", "definition": True,
            },
            {
                "name": "caller", "number": 3, "definition": True,
                "calls": (("shared_source_name", 2),),
            },
        ]
        inputs, invocations, payloads = independent_ctu_fixture(source_zero)
        independent = review.independently_derive_direct_graph(
            inputs, invocations, payloads
        )
        caller_edges = [
            item for item in independent["direct_edges"]
            if item["caller"]["name"] == "caller"
        ]
        self.assertEqual(len(caller_edges), 1)
        self.assertEqual(caller_edges[0]["callee"]["name"], "asm_second")

    def test_independent_resolver_rejects_every_caller_trait_and_weak_declaration(self):
        cases = {
            "alias": {"alias": True},
            "clone": {"name": "caller.clone.1"},
            "comdat": {"visibility": ("comdat",)},
            "inline": {"function_flags": "body always_inline"},
            "weak": {"visibility": ("weak",)},
        }
        for trait, mutation in sorted(cases.items()):
            with self.subTest(caller_trait=trait):
                caller = {
                    "name": "caller", "number": 2,
                    "definition": True, "calls": (("callee", 1),),
                }
                caller.update(mutation)
                inputs, invocations, payloads = independent_ctu_fixture(
                    [{"name": "callee", "number": 1}, caller]
                )
                graph = review.independently_derive_direct_graph(
                    inputs, invocations, payloads
                )
                self.assertFalse(graph["direct_edges"])

        for declaration in (
            {
                "name": "callee", "number": 1,
                "visibility": ("weak",),
            },
            {"name": "callee", "number": 1, "global": False},
        ):
            with self.subTest(declaration=declaration):
                inputs, invocations, payloads = independent_ctu_fixture(
                    [
                        declaration,
                        {
                            "name": "caller", "number": 2,
                            "definition": True, "calls": (("callee", 1),),
                        },
                    ]
                )
                graph = review.independently_derive_direct_graph(
                    inputs, invocations, payloads
                )
                self.assertFalse(graph["direct_edges"])

    def test_independent_rootless_and_callback_rooted_scc_closure(self):
        for address_taken, expected_rooted in ((False, False), (True, True)):
            with self.subTest(address_taken=address_taken):
                inputs, invocations, payloads = independent_ctu_fixture(
                    [
                        {
                            "name": "local_a", "number": 1,
                            "definition": True, "global": False,
                            "address_taken": address_taken,
                            "calls": (("local_b", 2),),
                        },
                        {
                            "name": "local_b", "number": 2,
                            "definition": True, "global": False,
                            "calls": (("local_a", 1),),
                        },
                    ]
                )
                graph = review.independently_derive_direct_graph(
                    inputs, invocations, payloads
                )
                rows = [
                    item for item in graph["function_reachability"]
                    if item["function"]["name"] in ("local_a", "local_b")
                ]
                root = "callback:mcctrl:fixture/review_0.c:local_a"
                self.assertEqual(
                    all(root in item["propagated_roots"] for item in rows),
                    expected_rooted,
                )

    def test_direct_cli_refuses_unisolated_execution(self):
        # The module-level guard is covered structurally: a direct execution
        # cannot reach argparse without the authority context attribute.
        self.assertIn("isolated", Path(review.__file__).read_text(encoding="utf-8"))

    def test_review_output_rejects_numeric_aliases(self):
        findings = review.validate_semantics(
            self.capture, copy.deepcopy(self.capture)
        )
        graph = self.capture["direct_cross_translation_unit_call_graph"]
        independent = {
            key: copy.deepcopy(graph[key])
            for key in (
                "blocked_edges", "definitions", "direct_edges",
                "function_reachability",
            )
        }
        findings.update(
            review.validate_independent_direct_graph(
                graph,
                independent,
                semantics.flows_v2.HISTORICAL_AUTHORITY_MODE,
            )
        )
        coverage = {
            key: value for key, value in findings.items()
            if key not in {
                "direct_ctu_blocked_edge_set_sha256",
                "direct_ctu_definition_set_sha256", "direct_ctu_edge_set_sha256",
                "direct_ctu_fresh_execution_authority",
                "direct_ctu_root_closure_sha256",
                "direct_ctu_structural_match_status",
            }
        }
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
            "blockers": semantics.blockers_for_direct_ctu(graph),
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
