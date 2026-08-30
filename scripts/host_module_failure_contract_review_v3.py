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
from collections import defaultdict
import json
import re
import sys
from collections import Counter
from pathlib import Path
import tempfile

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
REVIEW_CGRAPH_HEADER = re.compile(
    r"^(?P<name>\*?[A-Za-z_][A-Za-z0-9_$.-]*)/(?P<number>[0-9]+) "
    r"\((?P<label>[^()]*)\)(?P<address> @0xADDR)?$"
)
REVIEW_CGRAPH_PRINTABLE_NAME = re.compile(
    r"^\*?[A-Za-z_][A-Za-z0-9_$.-]*$"
)
REVIEW_CGRAPH_AUX = re.compile(r"^  Aux: @0xADDR$")
REVIEW_NON_LF_SEPARATORS = ("\r", "\v", "\f", "\x85", "\u2028", "\u2029")
REVIEW_VISIBILITY_VALUE = re.compile(r"^[!-~]+$")
REVIEW_VISIBILITY_TOKEN_RANKS = {
    "in_other_partition": 0,
    "used_from_other_partition": 1,
    "force_output": 2,
    "forced_by_abi": 3,
    "externally_visible": 4,
    "no_reorder": 5,
    "undef": 6,
    "prevailing_def": 6,
    "prevailing_def_ironly": 6,
    "preempted_reg": 6,
    "preempted_ir": 6,
    "resolved_ir": 6,
    "resolved_exec": 6,
    "resolved_dyn": 6,
    "prevailing_def_ironly_exp": 6,
    "asm_written": 7,
    "external": 8,
    "public": 9,
    "common": 10,
    "weak": 11,
    "dll_import": 12,
    "comdat": 13,
    "one_only": 15,
    "(implicit_section)": 17,
    "visibility_specified": 18,
    "visibility:protected": 19,
    "visibility:hidden": 19,
    "visibility:internal": 19,
    "virtual": 20,
    "artificial": 21,
    "constructor": 22,
    "destructor": 23,
}
REVIEW_CGRAPH_EDGE = re.compile(
    r"(?P<name>\*?[A-Za-z_][A-Za-z0-9_$.-]*)/(?P<number>[0-9]+)"
    r"(?P<edge_metadata>"
    r"(?: \(speculative\))?"
    r"(?: \(inlined\))?"
    r"(?: \(call_stmt_cannot_inline_p\))?"
    r"(?: \(indirect_inlining\))?"
    r"(?: \((?P<profile_count>0|[1-9][0-9]{0,18})"
    r"(?: \((?:estimated locally(?:, globally 0(?: adjusted)?)?|"
    r"adjusted|auto FDO|guessed)\))?,"
    r"(?P<profile_frequency>0|[1-9][0-9]{0,308})\."
    r"(?P<profile_frequency_fraction>[0-9]{2}) per call\))?"
    r"(?: \(can throw external\))?"
    r")(?= |$)"
)
REVIEW_CGRAPH_PROFILE_MAX_COUNT = 2305843009213693950
REVIEW_CGRAPH_PROFILE_MAX_FREQUENCY_INTEGER = 9223372036854775808
REVIEW_CLONE_MARKERS = (
    ".clone.", ".constprop.", ".isra.", ".part.", ".cold",
)


class ReviewV3Error(RuntimeError):
    """Raised when a v3 structural review input changes."""


def _review_traits(record):
    lines = [line.lower() for line in record["details"]]
    visibility = set(record["visibility"])
    type_text = record["type"].lower()
    traits = set()
    if (
        record["name"].startswith("*")
        or "alias" in type_text
        or any(line.startswith("alias target:") for line in lines)
    ):
        traits.add("alias")
    if any(marker in record["name"] for marker in REVIEW_CLONE_MARKERS) or any(
        line.startswith("clone of") for line in lines
    ):
        traits.add("clone")
    if "comdat" in visibility or "one_only" in visibility or "comdat" in type_text:
        traits.add("comdat")
    if any(
        line.startswith("function flags:")
        and any("inline" in token for token in line.split()[2:])
        for line in lines
    ):
        traits.add("inline")
    if (
        type_text.startswith("function definition analyzed")
        and "external" in visibility
    ):
        traits.add("inline")
    if "weak" in visibility or "weakref" in visibility or "weak" in type_text:
        traits.add("weak")
    return sorted(traits)


def _review_calls_failure(payload, cursor):
    """Report one independently bounded Calls-row scanner diagnostic."""

    excerpt = payload[cursor:cursor + 80]
    if cursor + len(excerpt) < len(payload):
        excerpt += "..."
    raise ReviewV3Error(
        "independent cgraph Calls syntax is unknown at character {0} of "
        "{1}; token {2}".format(cursor, len(payload), repr(excerpt))
    )


def _review_scan_calls(payload):
    """Independently scan complete GCC 8.5 call-edge records."""

    if payload == "":
        return []
    if payload[:1] != " ":
        _review_calls_failure(payload, 0)
    cursor = 1
    calls = []
    while cursor < len(payload):
        edge = REVIEW_CGRAPH_EDGE.match(payload, cursor)
        if edge is None or edge.start() != cursor:
            _review_calls_failure(payload, cursor)
        if (
            edge.group("profile_count") is not None
            and (
                int(edge.group("profile_count")) > REVIEW_CGRAPH_PROFILE_MAX_COUNT
                or int(edge.group("profile_frequency"))
                > REVIEW_CGRAPH_PROFILE_MAX_FREQUENCY_INTEGER
                or (
                    int(edge.group("profile_frequency"))
                    == REVIEW_CGRAPH_PROFILE_MAX_FREQUENCY_INTEGER
                    and edge.group("profile_frequency_fraction") != "00"
                )
            )
        ):
            _review_calls_failure(payload, cursor)
        metadata = edge.group("edge_metadata")
        call = {
            "name": edge.group("name"),
            "number": int(edge.group("number")),
        }
        if metadata:
            call["edge_metadata"] = metadata
        calls.append(call)
        cursor = edge.end()
        if cursor == len(payload):
            break
        if payload[cursor] != " " or cursor + 1 >= len(payload):
            _review_calls_failure(payload, cursor)
        cursor += 1
    return calls


def _review_visibility_row(line):
    """Independently parse GCC's exact, possibly token-empty visibility row."""

    if line == "  Visibility:":
        return []
    marker = "  Visibility: "
    if line[:len(marker)] != marker:
        raise ReviewV3Error("independent cgraph Visibility syntax is malformed")
    payload = line[len(marker):]
    pieces = payload.split(" ")
    if not payload or any(piece == "" for piece in pieces):
        raise ReviewV3Error("independent cgraph Visibility syntax is malformed")
    previous = -1
    for piece in pieces:
        rank = REVIEW_VISIBILITY_TOKEN_RANKS.get(piece)
        if piece.startswith("comdat_group:"):
            suffix = piece.partition(":")[2]
            rank = 14 if REVIEW_VISIBILITY_VALUE.fullmatch(suffix) else None
        elif piece.startswith("section:"):
            suffix = piece.partition(":")[2]
            rank = 16 if REVIEW_VISIBILITY_VALUE.fullmatch(suffix) else None
        if rank is None:
            raise ReviewV3Error(
                "independent cgraph Visibility contains an unknown token"
            )
        if rank <= previous:
            raise ReviewV3Error(
                "independent cgraph Visibility is duplicated or out of order"
            )
        previous = rank
    return pieces


def _review_initial_section(lines, source):
    records = []
    current = None
    for line in lines:
        match = REVIEW_CGRAPH_HEADER.match(line)
        if match:
            if (
                REVIEW_CGRAPH_PRINTABLE_NAME.fullmatch(match.group("label"))
                is None
            ):
                raise ReviewV3Error(
                    "independent cgraph symbol has no printable name"
                )
            current = {
                "address_taken": False,
                "calls": [],
                "details": [],
                "label": match.group("label"),
                "name": match.group("name"),
                "number": int(match.group("number")),
                "saw_aux": False,
                "saw_calls": False,
                "saw_visibility": False,
                "type": None,
                "visibility": [],
            }
            records.append(current)
            continue
        if current is None:
            if line.strip():
                raise ReviewV3Error("independent cgraph has pre-symbol content")
            continue
        stripped = line.strip()
        if not stripped:
            continue
        current["details"].append(stripped)
        if stripped.startswith("Type:"):
            if current["type"] is not None:
                raise ReviewV3Error("independent cgraph Type row is duplicated")
            current["type"] = stripped.split(":", 1)[1].strip()
        elif line.startswith("  Visibility:"):
            if current["saw_visibility"]:
                raise ReviewV3Error("independent cgraph Visibility row is duplicated")
            current["saw_visibility"] = True
            current["visibility"] = _review_visibility_row(line)
        elif stripped == "Address is taken.":
            current["address_taken"] = True
        elif stripped == "Aux: @0xADDR":
            if current["saw_aux"]:
                raise ReviewV3Error("independent cgraph Aux row is duplicated")
            current["saw_aux"] = True
        elif stripped.startswith("Calls:"):
            if current["saw_calls"]:
                raise ReviewV3Error("independent cgraph Calls row is duplicated")
            current["saw_calls"] = True
            payload = stripped.split(":", 1)[1]
            current["calls"] = _review_scan_calls(payload)
    numbers = [item["number"] for item in records]
    if not records or len(numbers) != len(set(numbers)):
        raise ReviewV3Error("independent cgraph symbol closure differs")
    result = []
    for record in records:
        if record["type"] is None:
            raise ReviewV3Error("independent cgraph symbol omits Type")
        if not record["type"].startswith("function"):
            continue
        if not record["saw_visibility"] or not record["saw_calls"]:
            raise ReviewV3Error("independent cgraph function metadata is incomplete")
        result.append(
            {
                "address_taken": record["address_taken"],
                "calls": sorted(record["calls"], key=semantics.canonical_bytes),
                "definition": record["type"].startswith("function definition analyzed"),
                "global": "public" in set(record["visibility"]),
                "name": record["name"],
                "number": record["number"],
                "printable_name": record["label"],
                "source": source,
                "traits": _review_traits(record),
            }
        )
    if not any(item["definition"] for item in result):
        raise ReviewV3Error("independent cgraph has no definitions")
    return sorted(result, key=semantics.canonical_bytes)


def independent_parse_cgraph(data, source):
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ReviewV3Error("independent cgraph is not UTF-8: {0}".format(exc))
    if any(separator in text for separator in REVIEW_NON_LF_SEPARATORS):
        raise ReviewV3Error("independent cgraph contains a non-LF line separator")
    lines = text.splitlines()
    for line in lines:
        header = REVIEW_CGRAPH_HEADER.fullmatch(line)
        address_record = (
            (header is not None and header.group("address") is not None)
            or REVIEW_CGRAPH_AUX.fullmatch(line) is not None
        )
        if "@0x" in line and (line.count("@0x") != 1 or not address_record):
            raise ReviewV3Error(
                "independent normalized cgraph retains a raw or misplaced allocator address"
            )
        if "0xADDR" in line and (
            line.count("0xADDR") != 1
            or not address_record
        ):
            raise ReviewV3Error(
                "independent cgraph address placeholder escaped a record"
            )
    starts = [index for index, line in enumerate(lines) if line == "Initial Symbol table:"]
    if not starts:
        raise ReviewV3Error("independent cgraph omits Initial Symbol table")
    terminators = {
        "Final Symbol table:", "Initial Symbol table:",
        "Optimized Symbol table:", "Reclaimed Symbol table:",
    }
    tables = []
    for start in starts:
        end = len(lines)
        for index in range(start + 1, len(lines)):
            if (
                lines[index] in terminators
                or lines[index].startswith("Removing unused symbols:")
            ):
                end = index
                break
        tables.append(_review_initial_section(lines[start + 1:end], source))
    first = tables[0]
    first_by_number = {record["number"]: record for record in first}
    # A GCC call row spells the callee's printable source name, while the
    # numbered symbol record retains the assembler identity used by the CTU
    # resolver.  Bind both halves against the authoritative first table: the
    # number selects exactly one record and the call spelling must match that
    # record's printable name.  This also permits distinct assembler symbols
    # to share a printable name without making the resolution ambiguous.
    for caller in first:
        for call in caller["calls"]:
            target = first_by_number.get(call["number"])
            if target is None:
                raise ReviewV3Error(
                    "independent initial cgraph call symbol number is unknown "
                    "(unknown callee)"
                )
            if target["printable_name"] != call["name"]:
                raise ReviewV3Error(
                    "independent initial cgraph call printable name differs"
                )
    first_definitions = {
        number for number, record in first_by_number.items()
        if record["definition"]
    }
    for table in tables[1:]:
        table_by_number = {record["number"]: record for record in table}
        if not set(table_by_number).issubset(first_by_number):
            raise ReviewV3Error("independent repeated cgraph tables differ")
        if not first_definitions.issubset(table_by_number):
            raise ReviewV3Error(
                "independent repeated cgraph pruned an analyzed definition"
            )
        if any(
            not semantics.strict_equal(record, first_by_number[number])
            for number, record in table_by_number.items()
        ):
            raise ReviewV3Error("independent repeated cgraph tables differ")
        # GCC 8.5 may omit declaration-only callees from a later IPA phase.
        # Calls resolve in the authoritative first table, and every analyzed
        # definition remains mandatory in each later table above.
    return first


def _review_identity(key):
    return {"module": key[0], "name": key[2], "source": key[1]}


def _review_blocked_reason(records):
    traits = sorted(
        set(trait for record in records for trait in record["traits"])
        & semantics.CGRAPH_BLOCKED_TRAITS
    )
    if traits:
        return traits[0] + "_target"
    if any(not record["global"] for record in records):
        return "static_name_collision"
    return "unresolved_candidate_target"


def independently_derive_direct_graph(inputs, invocations, payloads):
    """Re-derive the bounded structural CTU inventory without authority claims."""

    sources = sorted(
        source for source, record in inputs["sources"].items()
        if record["language"] == "c"
    )
    if len(sources) != semantics.EXPECTED_C_SOURCE_COUNT:
        raise ReviewV3Error("independent direct C source closure changed")
    by_source = {}
    for source in sources:
        invocation = invocations.get(source)
        binding = invocation.get("dumps", {}).get("cgraph") if invocation else None
        if binding is None:
            raise ReviewV3Error("independent C invocation omits cgraph")
        data = semantics.validate_file_binding(
            binding, payloads, "independent C cgraph"
        )
        by_source[source] = independent_parse_cgraph(data, source)

    definitions = []
    records = {}
    all_by_module_name = defaultdict(list)
    strong_by_module_name = defaultdict(list)
    for source in sources:
        module = inputs["sources"][source]["module"]
        for record in by_source[source]:
            if not record["definition"]:
                continue
            key = (module, source, record["name"])
            if key in records:
                raise ReviewV3Error(
                    "independent graph found a duplicate translation-unit definition"
                )
            records[key] = record
            all_by_module_name[(module, record["name"])].append((key, record))
            if record["global"] and not record["traits"]:
                strong_by_module_name[(module, record["name"])].append((key, record))
            definitions.append(
                {
                    "function": _review_identity(key),
                    "linkage": "global" if record["global"] else "source_local",
                    "traits": list(record["traits"]),
                }
            )
    for key, candidates in strong_by_module_name.items():
        if len(candidates) > 1:
            raise ReviewV3Error(
                "independent graph found duplicate strong definition {0}".format(key)
            )

    edges = []
    blocked_edges = []
    graph_edges = set()
    for source in sources:
        module = inputs["sources"][source]["module"]
        numbered = {item["number"]: item for item in by_source[source]}
        for caller in by_source[source]:
            if not caller["definition"]:
                continue
            caller_key = (module, source, caller["name"])
            for call in caller["calls"]:
                declared = numbered.get(call["number"])
                if declared is None:
                    raise ReviewV3Error(
                        "independent direct call symbol number is unknown"
                    )
                if declared["printable_name"] != call["name"]:
                    raise ReviewV3Error(
                        "independent direct call printable name differs"
                    )
                target_key = None
                edge_kind = None
                reason = None
                if caller["traits"]:
                    reason = caller["traits"][0] + "_caller"
                elif "edge_metadata" in call:
                    reason = "decorated_call_metadata"
                elif declared["definition"]:
                    if declared["traits"]:
                        reason = _review_blocked_reason([declared])
                    else:
                        target_key = (module, source, declared["name"])
                        edge_kind = "same_translation_unit_direct"
                elif declared["traits"] or not declared["global"]:
                    if declared["traits"]:
                        reason = declared["traits"][0] + "_declaration"
                    else:
                        reason = "source_local_declaration"
                else:
                    all_candidates = all_by_module_name.get(
                        (module, declared["name"]), []
                    )
                    strong = strong_by_module_name.get(
                        (module, declared["name"]), []
                    )
                    if len(all_candidates) == 1 and len(strong) == 1:
                        target_key = strong[0][0]
                        if target_key[1] == source:
                            raise ReviewV3Error(
                                "independent external target resolves in its TU"
                            )
                        edge_kind = "same_module_cross_translation_unit_direct"
                    else:
                        other_modules = [
                            item
                            for (candidate_module, candidate_name), values
                            in all_by_module_name.items()
                            if candidate_name == declared["name"]
                            and candidate_module != module
                            for item in values
                        ]
                        if all_candidates:
                            reason = _review_blocked_reason(
                                [item[1] for item in all_candidates]
                            )
                        elif other_modules:
                            reason = "cross_module_reference"
                        else:
                            reason = "external_outside_candidate"
                if target_key is None:
                    if reason is None:
                        raise ReviewV3Error(
                            "independent blocked edge has no structural reason"
                        )
                    blocked = {
                        "callee_name": declared["name"],
                        "caller": _review_identity(caller_key),
                        "reason": reason,
                    }
                    if "edge_metadata" in call:
                        blocked["edge_metadata"] = call["edge_metadata"]
                    blocked_edges.append(blocked)
                    continue
                if target_key not in records or records[target_key]["traits"]:
                    raise ReviewV3Error("independent graph traverses blocked target")
                graph_edges.add((caller_key, target_key))
                edges.append(
                    {
                        "callee": _review_identity(target_key),
                        "caller": _review_identity(caller_key),
                        "edge_kind": edge_kind,
                    }
                )

    roots = {}
    local_roots = {}
    for key, record in records.items():
        local = []
        if record["global"] and not record["traits"]:
            local.append("external:{0}:{1}".format(key[0], key[2]))
        if record["address_taken"]:
            local.append("callback:{0}:{1}:{2}".format(key[0], key[1], key[2]))
        local_roots[key] = sorted(local)
        roots[key] = set(local)
    changed = True
    while changed:
        changed = False
        for caller, callee in sorted(graph_edges):
            before = len(roots[callee])
            roots[callee].update(roots[caller])
            if len(roots[callee]) != before:
                changed = True
    reachability = [
        {
            "function": _review_identity(key),
            "local_roots": local_roots[key],
            "propagated_roots": sorted(roots[key]),
        }
        for key in sorted(records)
    ]
    return {
        "blocked_edges": sorted(
            {
                semantics.canonical_bytes(item): item
                for item in blocked_edges
            }.values(),
            key=semantics.canonical_bytes,
        ),
        "definitions": sorted(definitions, key=semantics.canonical_bytes),
        "direct_edges": sorted(
            {semantics.canonical_bytes(item): item for item in edges}.values(),
            key=semantics.canonical_bytes,
        ),
        "function_reachability": sorted(
            reachability, key=semantics.canonical_bytes
        ),
    }


def validate_independent_direct_graph(
    supplied_graph, independent, authority_mode
):
    try:
        semantics.validate_direct_ctu_graph_schema(
            supplied_graph, authority_mode
        )
    except semantics.SemanticsV3Error as exc:
        raise ReviewV3Error(
            "supplied direct CTU inventory schema is invalid: {0}".format(exc)
        )
    observed = {
        key: supplied_graph[key]
        for key in (
            "blocked_edges", "definitions", "direct_edges",
            "function_reachability",
        )
    }
    if not semantics.strict_equal(observed, independent):
        raise ReviewV3Error(
            "independent direct CTU definitions, edges, blockers, or roots differ"
        )
    return {
        "direct_ctu_blocked_edge_count": len(independent["blocked_edges"]),
        "direct_ctu_blocked_edge_set_sha256": semantics.sha256_bytes(
            semantics.canonical_bytes(independent["blocked_edges"])
        ),
        "direct_ctu_definition_count": len(independent["definitions"]),
        "direct_ctu_definition_set_sha256": semantics.sha256_bytes(
            semantics.canonical_bytes(independent["definitions"])
        ),
        "direct_ctu_direct_edge_count": len(independent["direct_edges"]),
        "direct_ctu_edge_set_sha256": semantics.sha256_bytes(
            semantics.canonical_bytes(independent["direct_edges"])
        ),
        "direct_ctu_reachable_function_count": sum(
            bool(item["propagated_roots"])
            for item in independent["function_reachability"]
        ),
        "direct_ctu_root_closure_sha256": semantics.sha256_bytes(
            semantics.canonical_bytes(independent["function_reachability"])
        ),
        "direct_ctu_same_module_cross_tu_edge_count": sum(
            item["edge_kind"] == "same_module_cross_translation_unit_direct"
            for item in independent["direct_edges"]
        ),
        "direct_ctu_fresh_execution_authority": False,
        "direct_ctu_structural_match_status": (
            "nonauthoritative_structural_inventory_matches"
        ),
    }


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
        or not semantics.strict_equal(
            capture["blockers"],
            semantics.blockers_for_direct_ctu(
                capture["direct_cross_translation_unit_call_graph"]
            ),
        )
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
            "direct_ctu_blocked_edge_count",
            "direct_ctu_blocked_edge_set_sha256",
            "direct_ctu_definition_count", "direct_ctu_definition_set_sha256",
            "direct_ctu_direct_edge_count", "direct_ctu_edge_set_sha256",
            "direct_ctu_fresh_execution_authority",
            "direct_ctu_reachable_function_count",
            "direct_ctu_root_closure_sha256",
            "direct_ctu_same_module_cross_tu_edge_count",
            "direct_ctu_structural_match_status",
        }
        findings = semantics.require_exact_keys(
            result["structural_findings"], finding_keys,
            "v3 contract review structural findings",
        )
        coverage = semantics.require_exact_keys(
            result["coverage"],
            {
                "c_function_count", "c_return_contract_count", "c_source_count",
                "c_terminal_count", "rust_mir_site_count",
                "rust_mir_site_count_by_mapping_status",
                "direct_ctu_blocked_edge_count", "direct_ctu_definition_count",
                "direct_ctu_direct_edge_count",
                "direct_ctu_reachable_function_count",
                "direct_ctu_same_module_cross_tu_edge_count",
                "semantic_error_domain_resolved_count", "tracker_credit_count",
                "v2_compiler_active_mapping_count",
            },
            "v3 contract review coverage",
        )
        integer_findings = finding_keys - {
            "direct_ctu_blocked_edge_set_sha256",
            "direct_ctu_definition_set_sha256", "direct_ctu_edge_set_sha256",
            "direct_ctu_fresh_execution_authority",
            "direct_ctu_root_closure_sha256",
            "direct_ctu_structural_match_status",
            "rust_mir_site_count_by_mapping_status",
        }
        for field in sorted(integer_findings):
            semantics.require_integer(
                findings[field], "v3 contract review finding " + field, minimum=0
            )
        for field in (
            "direct_ctu_blocked_edge_set_sha256",
            "direct_ctu_definition_set_sha256", "direct_ctu_edge_set_sha256",
            "direct_ctu_root_closure_sha256",
        ):
            semantics.require_digest(findings[field], "v3 contract review " + field)
        if (
            type(findings["direct_ctu_fresh_execution_authority"]) is not bool
            or findings["direct_ctu_fresh_execution_authority"] is not False
            or findings["direct_ctu_structural_match_status"]
            != "nonauthoritative_structural_inventory_matches"
        ):
            raise semantics.SemanticsV3Error(
                "v3 contract review CTU inventory overclaims authority"
            )
        if not semantics.strict_equal(result["blockers"], list(semantics.BLOCKERS)):
            raise semantics.SemanticsV3Error(
                "v3 contract review direct CTU blocker boundary changed"
            )
        for mapping, label in ((findings, "findings"), (coverage, "coverage")):
            semantics.require_count_map(
                mapping["rust_mir_site_count_by_mapping_status"],
                label + " Rust mapping status",
            )
        for field in sorted(
            set(coverage) - {"rust_mir_site_count_by_mapping_status"}
        ):
            semantics.require_integer(
                coverage[field], "v3 contract review coverage " + field, minimum=0
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
    reviewer_receipt = None
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
        inputs = semantics.load_inputs(
            repo,
            failure_site_path,
            failure_flow_v1_path,
            failure_flow_v2_path,
            build_dir,
            kernel_dir,
            historical_ef58,
            repository_authority,
        )
        supplied_manifest, supplied_payloads, supplied_raw_record = (
            semantics.read_raw_bundle(raw_bundle_path, raw_bundle_sha256_path)
        )
        supplied_invocations = semantics.validate_raw_manifest(
            supplied_manifest, supplied_payloads, inputs
        )
        independent_comparison = None
        if inputs["authority_mode"] == semantics.flows_v2.FRESH_AUTHORITY_MODE:
            with tempfile.TemporaryDirectory(
                prefix="host-module-semantics-v3-review-recapture."
            ) as temporary:
                temporary_root = Path(temporary)
                reviewer_bundle = temporary_root / Path(raw_bundle_path).name
                reviewer_sidecar = temporary_root / Path(raw_bundle_sha256_path).name
                reviewer_receipt = semantics.capture_raw_bundle(
                    inputs,
                    repo,
                    build_dir,
                    kernel_dir,
                    reviewer_bundle,
                    reviewer_sidecar,
                )
                reviewer_manifest, reviewer_payloads, reviewer_raw_record = (
                    semantics.read_raw_bundle(reviewer_bundle, reviewer_sidecar)
                )
                semantics.validate_raw_manifest(
                    reviewer_manifest, reviewer_payloads, inputs
                )
                independent_comparison = (
                    semantics.compare_independent_fresh_captures(
                        supplied_manifest,
                        supplied_payloads,
                        supplied_raw_record,
                        reviewer_receipt,
                        reviewer_manifest,
                        reviewer_payloads,
                        reviewer_raw_record,
                    )
                )
                expected_semantics = semantics.build_capture(
                    repo,
                    failure_site_path,
                    failure_flow_v1_path,
                    failure_flow_v2_path,
                    raw_bundle_path,
                    raw_bundle_sha256_path,
                    build_dir,
                    kernel_dir,
                    historical_ef58,
                    repository_authority,
                    independent_fresh_comparison=independent_comparison,
                )
                independent_graph = independently_derive_direct_graph(
                    inputs, supplied_invocations, supplied_payloads
                )
                independent_comparison.replay(
                    supplied_manifest, supplied_raw_record
                )
                reviewer_receipt.replay()
        else:
            expected_semantics = semantics.build_capture(
                repo,
                failure_site_path,
                failure_flow_v1_path,
                failure_flow_v2_path,
                raw_bundle_path,
                raw_bundle_sha256_path,
                build_dir,
                kernel_dir,
                historical_ef58,
                repository_authority,
            )
            independent_graph = independently_derive_direct_graph(
                inputs, supplied_invocations, supplied_payloads
            )
    except semantics.SemanticsV3Error as exc:
        raise ReviewV3Error("cannot re-derive v3 semantics: {0}".format(exc))
    finally:
        if reviewer_receipt is not None:
            reviewer_receipt.close()
    supplied_semantics, semantics_file, _ = semantics.read_json_record(
        semantics_v3_path, "semantics v3"
    )
    findings = validate_semantics(supplied_semantics, expected_semantics)
    findings.update(
        validate_independent_direct_graph(
            supplied_semantics["direct_cross_translation_unit_call_graph"],
            independent_graph,
            expected_semantics["authority_mode"],
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
            "v2_compiler_active_mapping_count": supplied_v2["coverage"][
                "compiler_active_mapped_count"
            ],
        }
    )
    result = {
        "analysis_claim": dict(ANALYSIS_CLAIM),
        "authority_mode": expected_semantics["authority_mode"],
        "blockers": list(supplied_semantics["blockers"]),
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
    output_target = None
    output_authority = None
    try:
        if not args.historical_ef58 and repository_authority is None:
            raise ReviewV3Error("fresh CLI requires isolated repository authority")
        output_target = semantics.prepare_empty_output_target(
            args.output, "contract review v3 output"
        )
        review = build_review(
            args.repo, args.failure_sites, args.failure_flows_v1,
            args.failure_flows_v2, args.failure_contract_review_v2,
            args.failure_semantics_v3, args.raw_bundle,
            args.raw_bundle_sha256, args.build_dir, args.kernel_dir,
            args.historical_ef58, repository_authority,
        )
        output_authority = output_target.create(
            (
                json.dumps(
                    review, allow_nan=False, indent=2, sort_keys=True
                )
                + "\n"
            ).encode("utf-8")
        )
        output_authority.replay()
    except (ReviewV3Error, semantics.SemanticsV3Error) as exc:
        print("host-module failure-contract review v3 failed: {0}".format(exc), file=sys.stderr)
        return 1
    finally:
        if output_authority is not None:
            output_authority.close()
        if output_target is not None:
            output_target.close()
    print(
        "reviewed {0} C return questions and {1} Rust MIR sites; FP-0006 remains IN_PROGRESS".format(
            review["coverage"]["c_return_contract_count"],
            review["coverage"]["rust_mir_site_count"],
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
