#!/usr/bin/env python3
"""Review bounded FP-0006 C-flow closure without awarding gate credit.

This review binds the immutable source-derived behavior contract, exact
compiler failure sites, and the additive v2 flow artifact.  It accepts exact
contract identities, explicit logical-to-physical aliases for continued macro
definitions, and deterministic selected-profile supplements.  Acceptance IDs
remain declarations, Rust MIR and semantic domains remain unresolved, and
FP-0006 therefore remains IN_PROGRESS.
"""

import sys as _fp0006_entry_sys


if __name__ == "__main__" and not hasattr(
    _fp0006_entry_sys, "_mckernel_fp0006_authority_context"
):
    _fp0006_entry_sys.stderr.write(
        "host-module failure-contract review v2 CLI requires the isolated "
        "failure-site authority launcher; refusing direct execution\n"
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
from collections import Counter
from pathlib import Path

import host_module_contracts as contracts
import host_module_failure_flows_v2 as flows_v2
import host_module_failure_sites as sites


SCHEMA_VERSION = 2
PROFILE = "compiler-backed-host-module-failure-contract-review-v2"
MAX_JSON_BYTES = 128 * 1024 * 1024
HEX_DIGEST = re.compile(r"^[0-9a-f]{64}$")
EXPECTED_SELECTED_PROFILE_SUPPLEMENTS = {
    "HFS-DC5B12F30906A4362FB28DBF",
    "HFS-D9B12133A20AA15053FA4715",
}
EXPECTED_ALTERNATE_PROFILE_CONTRACT_IDENTITIES = frozenset(
    {
        ("mcctrl", "executer/kernel/mcctrl/control.c", 695, 10, "EFAULT"),
        ("mcctrl", "executer/kernel/mcctrl/control.c", 713, 10, "EFAULT"),
        ("mcctrl", "executer/kernel/mcctrl/control.c", 718, 10, "EFAULT"),
        ("mcctrl", "executer/kernel/mcctrl/control.c", 723, 10, "EFAULT"),
        ("mcctrl", "executer/kernel/mcctrl/control.c", 728, 9, "EINVAL"),
        ("mcctrl", "executer/kernel/mcctrl/control.c", 2884, 10, "EFAULT"),
        ("mcctrl", "executer/kernel/mcctrl/control.c", 2897, 10, "EFAULT"),
        ("mcctrl", "executer/kernel/mcctrl/control.c", 2945, 10, "EINVAL"),
        ("mcctrl", "executer/kernel/mcctrl/control.c", 2949, 10, "EFAULT"),
        ("mcctrl", "executer/kernel/mcctrl/control.c", 2957, 10, "EINVAL"),
        ("mcctrl", "executer/kernel/mcctrl/control.c", 2964, 11, "EINVAL"),
        ("mcctrl", "executer/kernel/mcctrl/control.c", 2972, 11, "EINVAL"),
        ("mcctrl", "executer/kernel/mcctrl/control.c", 2989, 12, "EFAULT"),
        ("mcctrl", "executer/kernel/mcctrl/control.c", 4247, 8, "EFAULT"),
        ("mcctrl", "executer/kernel/mcctrl/control.c", 4258, 8, "EFAULT"),
        ("mcctrl", "executer/kernel/mcctrl/control.c", 4263, 8, "EFAULT"),
    }
)
EXPECTED_VERSION_GUARD_CONTRACT_IDENTITIES = frozenset(
    {
        (
            "ihk_smp_x86_64",
            "ihk/linux/driver/smp/arch/x86_64/smp-arch-driver.c",
            182,
            10,
            "EFAULT",
        ),
    }
)
EXPECTED_MACRO_ALIAS_CONTRACT_IDENTITIES = frozenset(
    {
        ("mcctrl", "executer/kernel/mcctrl/futex.c", 79, 15, "EFAULT"),
        ("mcctrl", "executer/kernel/mcctrl/futex.c", 101, 28, "EFAULT"),
    }
)
EXPECTED_STALE_CONTRACT_IDENTITIES = (
    EXPECTED_ALTERNATE_PROFILE_CONTRACT_IDENTITIES
    | EXPECTED_VERSION_GUARD_CONTRACT_IDENTITIES
    | EXPECTED_MACRO_ALIAS_CONTRACT_IDENTITIES
)

ANALYSIS_CLAIM = {
    "credit_eligible": False,
    "executable_acceptance_coverage": False,
    "exhaustive": False,
    "fp_0006_status": "IN_PROGRESS",
    "test_mapped": False,
    "tracker_credit": False,
    "reason": (
        "all compiler-active sites have bounded declarative mappings, but Rust "
        "MIR, semantic error domains, macro-expansion dataflow, module/API "
        "reachability, and executable acceptance results remain unresolved"
    ),
}


class ReviewV2Error(RuntimeError):
    """Raised when a v2 review input or claim changes."""


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
            raise ReviewV2Error("duplicate JSON key: {0}".format(key))
        result[key] = value
    return result


def reject_nonfinite_constant(value):
    raise ReviewV2Error("non-finite JSON constant is forbidden: {0}".format(value))


def read_bytes_no_symlinks(path, label, root=None):
    """Open one regular file through no-follow directory descriptors."""

    path = Path(path)
    if ".." in path.parts:
        raise ReviewV2Error("{0} path must not contain '..': {1}".format(label, path))
    absolute = path if path.is_absolute() else Path.cwd() / path
    if root is not None:
        root = Path(root)
        if ".." in root.parts:
            raise ReviewV2Error("{0} containment root is invalid".format(label))
        absolute_root = root if root.is_absolute() else Path.cwd() / root
        try:
            common = os.path.commonpath((str(absolute), str(absolute_root)))
        except ValueError:
            common = ""
        if common != str(absolute_root):
            raise ReviewV2Error("{0} escapes its authority root: {1}".format(label, path))
    parts = absolute.parts
    if not parts or parts[0] != "/" or len(parts) < 2:
        raise ReviewV2Error("{0} path is invalid: {1}".format(label, path))
    if not hasattr(os, "O_NOFOLLOW") or not hasattr(os, "O_DIRECTORY"):
        raise ReviewV2Error("no-follow file traversal is unavailable")

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
                raise ReviewV2Error(
                    "{0} path contains a symlink or non-directory component: {1}"
                    .format(label, path)
                ) from exc
            os.close(directory_fd)
            directory_fd = next_fd
        try:
            file_fd = os.open(parts[-1], file_flags, dir_fd=directory_fd)
        except OSError as exc:
            raise ReviewV2Error(
                "{0} must be a regular non-symlink file: {1}".format(label, path)
            ) from exc
        metadata = os.fstat(file_fd)
        if not stat.S_ISREG(metadata.st_mode):
            raise ReviewV2Error("{0} must be a regular file: {1}".format(label, path))
        if metadata.st_size <= 0 or metadata.st_size > MAX_JSON_BYTES:
            raise ReviewV2Error("{0} has an invalid size".format(label))
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
            raise ReviewV2Error("{0} has an invalid size".format(label))
        return data
    finally:
        if file_fd is not None:
            os.close(file_fd)
        if directory_fd is not None:
            os.close(directory_fd)


def read_json_with_bytes(path, label, root=None):
    path = Path(path)
    try:
        data = read_bytes_no_symlinks(path, label, root=root)
    except ReviewV2Error:
        raise
    except OSError as exc:
        raise ReviewV2Error("cannot read {0} {1}: {2}".format(label, path, exc))
    try:
        value = json.loads(
            data.decode("utf-8"),
            object_pairs_hook=duplicate_rejecting_object,
            parse_constant=reject_nonfinite_constant,
        )
    except (UnicodeDecodeError, ValueError) as exc:
        if isinstance(exc, ReviewV2Error):
            raise
        raise ReviewV2Error("cannot parse {0}: {1}".format(label, exc))
    if not isinstance(value, dict):
        raise ReviewV2Error("{0} must be a JSON object".format(label))
    return (
        value,
        {"artifact_bytes": len(data), "artifact_sha256": sha256_bytes(data)},
        data,
    )


def read_json(path, label, root=None):
    value, record, _ = read_json_with_bytes(path, label, root=root)
    return value, record


def require_exact_keys(value, expected, label):
    if not isinstance(value, dict) or set(value) != set(expected):
        raise ReviewV2Error("{0} schema changed".format(label))
    return value


def validate_root(root, label):
    if not isinstance(root, dict):
        raise ReviewV2Error("{0} root is malformed".format(label))
    kind = root.get("kind")
    expected = (
        {"function", "id", "kind", "module", "source"}
        if kind == "translation_unit_function_boundary"
        else {"id", "kind", "module", "source"}
        if kind == "translation_unit_source_boundary"
        else None
    )
    if expected is None or set(root) != expected:
        raise ReviewV2Error("{0} root kind or schema changed".format(label))
    identity = {key: root[key] for key in sorted(set(root) - {"id"})}
    digest = sha256_bytes(canonical_bytes(identity))
    if root["id"] != "HFR-" + digest[:24].upper():
        raise ReviewV2Error("{0} root identity is stale".format(label))
    return root


def validate_v2_capture(capture, capture_file, hfs, hfs_file, expected_capture):
    expected_top = {
        "analysis_claim",
        "analysis_scope",
        "authority_mode",
        "blockers",
        "coverage",
        "failure_flows",
        "function_analysis_roots",
        "generator",
        "inputs",
        "profile",
        "schema_version",
        "site_dispositions",
        "unresolved_paths",
    }
    require_exact_keys(capture, expected_top, "v2 failure-flow artifact")
    if not strict_equal(capture, expected_capture):
        raise ReviewV2Error(
            "v2 failure-flow artifact is not the exact derivation of supplied v1 bytes"
        )
    if (
        not strict_equal(capture.get("schema_version"), flows_v2.SCHEMA_VERSION)
        or not strict_equal(capture.get("profile"), flows_v2.PROFILE)
        or not strict_equal(
            capture.get("generator"), "scripts/host_module_failure_flows_v2.py"
        )
        or not strict_equal(capture.get("analysis_claim"), flows_v2.ANALYSIS_CLAIM)
        or not strict_equal(capture.get("analysis_scope"), flows_v2.ANALYSIS_SCOPE)
        or not strict_equal(capture.get("blockers"), list(flows_v2.FIXED_BLOCKERS))
        or capture.get("authority_mode") not in (
            flows_v2.HISTORICAL_AUTHORITY_MODE,
            flows_v2.FRESH_AUTHORITY_MODE,
        )
    ):
        raise ReviewV2Error("v2 failure-flow authority or bounded claim changed")
    inputs = require_exact_keys(
        capture.get("inputs"), {"failure_flows_v1", "failure_sites_v1"}, "v2 inputs"
    )
    expected_hfs_binding = {
        "artifact_bytes": hfs_file["artifact_bytes"],
        "artifact_sha256": hfs_file["artifact_sha256"],
        "profile": hfs["profile"],
        "repository_commit": hfs.get("provenance", {}).get("repository_commit"),
        "schema_version": hfs["schema_version"],
    }
    if not strict_equal(inputs["failure_sites_v1"], expected_hfs_binding):
        raise ReviewV2Error("v2 flow artifact does not bind exact HFS bytes")
    v1_binding = require_exact_keys(
        inputs["failure_flows_v1"],
        {"artifact_bytes", "artifact_sha256", "profile", "schema_version"},
        "v1 failure-flow binding",
    )
    expected_v1_binding = expected_capture["inputs"]["failure_flows_v1"]
    if not strict_equal(v1_binding, expected_v1_binding):
        raise ReviewV2Error("v2 flow artifact does not bind exact supplied v1 bytes")
    if (
        not HEX_DIGEST.fullmatch(str(v1_binding.get("artifact_sha256", "")))
        or not strict_equal(v1_binding.get("profile"), flows_v2.v1_flows.PROFILE)
        or not strict_equal(
            v1_binding.get("schema_version"), flows_v2.v1_flows.SCHEMA_VERSION
        )
    ):
        raise ReviewV2Error("v1 failure-flow binding is malformed")

    hfs_by_id = {item["id"]: item for item in hfs["failure_sites"]}
    if len(hfs_by_id) != len(hfs["failure_sites"]):
        raise ReviewV2Error("HFS IDs are duplicated")
    function_roots = capture.get("function_analysis_roots")
    if not isinstance(function_roots, list):
        raise ReviewV2Error("v2 function roots are missing")
    root_by_function = {}
    for record in function_roots:
        require_exact_keys(
            record,
            {
                "analysis_entry_roots",
                "function",
                "module",
                "source",
                "statement_range",
                "statement_sha256",
            },
            "v2 function root",
        )
        key = (record["source"], record["function"])
        if key in root_by_function:
            raise ReviewV2Error("v2 function roots are duplicated")
        roots = record["analysis_entry_roots"]
        if not isinstance(roots, list) or len(roots) != 1:
            raise ReviewV2Error("v2 function root closure is not singular")
        root = validate_root(roots[0], "function")
        if (
            root.get("kind") != "translation_unit_function_boundary"
            or root.get("function") != record["function"]
            or root.get("module") != record["module"]
            or root.get("source") != record["source"]
        ):
            raise ReviewV2Error("v2 function root binding differs")
        if not HEX_DIGEST.fullmatch(str(record.get("statement_sha256", ""))):
            raise ReviewV2Error("v2 function statement digest is malformed")
        root_by_function[key] = root

    v2_flows = capture.get("failure_flows")
    if not isinstance(v2_flows, list):
        raise ReviewV2Error("v2 failure flows are missing")
    flows_by_id = {}
    for flow in v2_flows:
        require_exact_keys(
            flow,
            {
                "active_compile_profile_sha256",
                "analysis_entry_roots",
                "expression",
                "expression_role",
                "function",
                "id",
                "identity_sha256",
                "location",
                "module",
                "origin",
                "source",
                "source_sha256",
                "v1_failure_flow_id",
                "v1_failure_flow_sha256",
                "v1_identity_sha256",
            },
            "v2 failure flow",
        )
        if flow["id"] in flows_by_id:
            raise ReviewV2Error("v2 failure-flow IDs are duplicated")
        root = root_by_function.get((flow["source"], flow["function"]))
        if root is None or flow["analysis_entry_roots"] != [root]:
            raise ReviewV2Error("v2 failure flow has no exact function root")
        identity = {
            "analysis_entry_roots": [root],
            "v1_failure_flow_id": flow["v1_failure_flow_id"],
            "v1_failure_flow_sha256": flow["v1_failure_flow_sha256"],
            "v1_identity_sha256": flow["v1_identity_sha256"],
        }
        digest = sha256_bytes(canonical_bytes(identity))
        if flow["identity_sha256"] != digest or flow["id"] != (
            "HF2-" + digest[:24].upper()
        ):
            raise ReviewV2Error("v2 failure-flow identity is stale")
        flows_by_id[flow["id"]] = flow

    dispositions = capture.get("site_dispositions")
    if not isinstance(dispositions, list):
        raise ReviewV2Error("v2 site dispositions are missing")
    disposition_by_id = {}
    for disposition in dispositions:
        if not isinstance(disposition, dict):
            raise ReviewV2Error("v2 site disposition is malformed")
        site_id = disposition.get("hfs_id")
        site = hfs_by_id.get(site_id)
        if site is None or site_id in disposition_by_id:
            raise ReviewV2Error("v2 site disposition identity is unknown or duplicated")
        if disposition.get("language") != site["language"]:
            raise ReviewV2Error("v2 site disposition language differs")
        kind = disposition.get("kind")
        if kind == "compiler_function_flow":
            require_exact_keys(
                disposition,
                {
                    "analysis_entry_roots",
                    "hfs_id",
                    "kind",
                    "language",
                    "v1_failure_flow_ids",
                    "v2_failure_flow_ids",
                },
                "C flow disposition",
            )
            ids = disposition["v2_failure_flow_ids"]
            if not isinstance(ids, list) or not ids or any(item not in flows_by_id for item in ids):
                raise ReviewV2Error("C flow disposition names unknown v2 flows")
            expected_v1_ids = sorted(flows_by_id[item]["v1_failure_flow_id"] for item in ids)
            if disposition["v1_failure_flow_ids"] != expected_v1_ids:
                raise ReviewV2Error("C flow disposition v1/v2 binding differs")
            if any(
                site_id not in flows_by_id[item]["origin"].get(
                    "first_stage_site_ids", []
                )
                for item in ids
            ):
                raise ReviewV2Error("C flow disposition does not bind its HFS ID")
            if not disposition["analysis_entry_roots"]:
                raise ReviewV2Error("C flow disposition has no analysis-entry root")
            for root in disposition["analysis_entry_roots"]:
                validate_root(root, "C flow disposition")
            expected_roots = sorted(
                {
                    canonical_bytes(root): root
                    for item in ids
                    for root in flows_by_id[item]["analysis_entry_roots"]
                }.values(),
                key=canonical_bytes,
            )
            if disposition["analysis_entry_roots"] != expected_roots:
                raise ReviewV2Error("C flow disposition root union differs")
        elif kind == "logical_macro_definition":
            require_exact_keys(
                disposition,
                {
                    "analysis_entry_roots",
                    "compiler_logical_location",
                    "conservative_physical_identity",
                    "errno_ordinal",
                    "hfs_id",
                    "kind",
                    "language",
                    "macro_name",
                    "physical_spelling",
                    "v1_unresolved_reason_id",
                },
                "macro disposition",
            )
            if len(disposition["analysis_entry_roots"]) != 1:
                raise ReviewV2Error("macro disposition root closure differs")
            root = validate_root(disposition["analysis_entry_roots"][0], "macro")
            if (
                root["kind"] != "translation_unit_source_boundary"
                or root["module"] != site["module"]
                or root["source"] != site["source"]
            ):
                raise ReviewV2Error("macro disposition uses the wrong root kind")
            if disposition["compiler_logical_location"] != {
                "column": site["column"], "line": site["line"]
            }:
                raise ReviewV2Error("macro compiler-logical identity differs")
            if (
                disposition["errno_ordinal"] != 1
                or not isinstance(disposition["macro_name"], str)
                or not disposition["macro_name"]
            ):
                raise ReviewV2Error("macro spelling classification is malformed")
            physical = disposition["conservative_physical_identity"]
            require_exact_keys(
                physical, {"column", "errno", "line", "module", "source"},
                "macro physical identity",
            )
            if (
                physical["module"] != site["module"]
                or physical["source"] != site["source"]
                or physical["errno"] != site["errno"]
            ):
                raise ReviewV2Error("macro physical identity differs from HFS")
            spelling = require_exact_keys(
                disposition["physical_spelling"],
                {"column", "end_column", "line", "source_logical_column"},
                "macro physical spelling",
            )
            if (
                spelling["line"] != physical["line"]
                or spelling["column"] != physical["column"]
                or spelling["end_column"] <= spelling["column"]
            ):
                raise ReviewV2Error("macro physical spelling differs")
        elif kind == "rust_mir_unresolved":
            require_exact_keys(
                disposition,
                {"hfs_id", "kind", "language", "v1_unresolved_reason_id"},
                "Rust disposition",
            )
        else:
            raise ReviewV2Error("v2 site disposition kind changed")
        disposition_by_id[site_id] = disposition
    if set(disposition_by_id) != set(hfs_by_id):
        raise ReviewV2Error("v2 site disposition closure differs")

    unresolved = capture.get("unresolved_paths")
    if not isinstance(unresolved, list):
        raise ReviewV2Error("v2 retained unresolved paths are missing")
    unresolved_counts = Counter()
    unresolved_ids = set()
    unresolved_by_id = {}
    for record in unresolved:
        if not isinstance(record, dict) or not isinstance(record.get("id"), str):
            raise ReviewV2Error("v2 unresolved path is malformed")
        if record["id"] in unresolved_ids:
            raise ReviewV2Error("v2 unresolved path IDs are duplicated")
        unresolved_ids.add(record["id"])
        unresolved_by_id[record["id"]] = record
        unresolved_counts[record.get("kind")] += 1
    for site_id, disposition in disposition_by_id.items():
        if disposition["kind"] != "rust_mir_unresolved":
            continue
        reason = unresolved_by_id.get(disposition["v1_unresolved_reason_id"])
        if (
            reason is None
            or reason.get("kind") != "rust_failure_site_mir_not_captured"
            or reason.get("first_stage_site_ids") != [site_id]
        ):
            raise ReviewV2Error("Rust disposition does not retain its exact MIR gap")
    disposition_counts = Counter(item["kind"] for item in dispositions)
    language_counts = Counter(item["language"] for item in dispositions)
    coverage = {
        "c_ambiguous_failure_site_count": 0,
        "c_external_root_unresolved_count": 0,
        "c_failure_site_count": language_counts["c"],
        "c_failure_site_resolved_count": disposition_counts[
            "compiler_function_flow"
        ]
        + disposition_counts["logical_macro_definition"],
        "c_function_boundary_root_count": len(function_roots),
        "c_function_count": len(function_roots),
        "c_macro_definition_site_count": disposition_counts[
            "logical_macro_definition"
        ],
        "explicit_failure_site_disposition_count": len(dispositions),
        "explicit_failure_site_input_count": len(hfs_by_id),
        "failure_flow_count": len(v2_flows),
        "rust_failure_site_count": language_counts["rust"],
        "rust_mir_unresolved_site_count": disposition_counts["rust_mir_unresolved"],
        "semantic_domain_unresolved_count": unresolved_counts[
            "return_value_error_domain_unresolved"
        ],
    }
    if not strict_equal(capture.get("coverage"), coverage):
        raise ReviewV2Error("v2 failure-flow coverage is stale")
    capture_file.update({"profile": capture["profile"], "schema_version": capture["schema_version"]})
    return disposition_by_id


def contract_identity(module, legacy):
    return (
        module,
        str(legacy["source"]),
        int(legacy["line"]),
        int(legacy["column"]),
        str(legacy["errno"]),
    )


def site_identity(site):
    return (
        site["module"],
        site["source"],
        site["line"],
        site["column"],
        site["errno"],
    )


def contract_mapping(behavior, classification):
    return {
        "acceptance_evidence": "declarative_id_only_not_executed_or_verified",
        "behavior_id": behavior["id"],
        "classification": classification,
        "declared_acceptance_test_ids": list(behavior["acceptance_test_ids"]),
        "rust_replacement": dict(behavior["rust_replacement"]),
    }


def classify_stale_contract_row(behavior, alias_hfs_ids):
    legacy = behavior["legacy"]
    identity = {
        "column": legacy["column"],
        "errno": legacy["errno"],
        "line": legacy["line"],
        "module": behavior["module"],
        "source": legacy["source"],
    }
    identity_tuple = (
        identity["module"],
        identity["source"],
        identity["line"],
        identity["column"],
        identity["errno"],
    )
    base = {
        "active_alias_hfs_ids": sorted(alias_hfs_ids),
        "behavior_id": behavior["id"],
        "contract_identity": identity,
        "declared_acceptance_test_ids": list(behavior["acceptance_test_ids"]),
    }
    if alias_hfs_ids:
        if identity_tuple not in EXPECTED_MACRO_ALIAS_CONTRACT_IDENTITIES:
            raise ReviewV2Error("retargeted macro-alias contract row")
        return {
            **base,
            "classification": "physical_spelling_alias_of_active_logical_macro_site",
            "profile_reason": (
                "C phase-2 backslash-newline splicing reports the active compiler "
                "identity on the macro definition's first logical line"
            ),
        }
    if identity_tuple in EXPECTED_MACRO_ALIAS_CONTRACT_IDENTITIES:
        raise ReviewV2Error("expected macro-alias contract row has no active HFS alias")
    if identity_tuple in EXPECTED_ALTERNATE_PROFILE_CONTRACT_IDENTITIES:
        return {
            **base,
            "classification": "alternate_profile_branch",
            "profile_reason": (
                "the selected MCCTRL_RUST_HELPERS and non-CONFIG_MIC profile uses "
                "the opposite preprocessor branch"
            ),
        }
    if identity_tuple in EXPECTED_VERSION_GUARD_CONTRACT_IDENTITIES:
        return {
            **base,
            "classification": "version_guard_inactive",
            "profile_reason": (
                "the selected Rocky kernel version excludes the older guarded branch"
            ),
        }
    raise ReviewV2Error(
        "conservative-only contract row has no reviewed multi-profile classification"
    )


def validate_contract(repo):
    try:
        policy, policy_file = read_json(
            repo / contracts.POLICY_PATH, "policy", root=repo
        )
        legacy, inventory_file = read_json(
            repo / contracts.INVENTORY_PATH, "frozen inventory", root=repo
        )
        contract_path = repo / contracts.CONTRACT_PATH
        contract, contract_file = read_json(
            contract_path, "behavior contract", root=repo
        )
        contracts.validate_contract(
            contract,
            policy,
            legacy,
            repo,
            policy_file_sha256=policy_file["artifact_sha256"],
            inventory_file_sha256=inventory_file["artifact_sha256"],
        )
    except (OSError, contracts.ContractError, ReviewV2Error) as exc:
        raise ReviewV2Error("behavior contract is invalid: {0}".format(exc))
    return contract, contract_file


def build_review(
    repo,
    failure_site_path,
    failure_flow_v1_path,
    failure_flow_v2_path,
    build_dir=None,
    kernel_dir=None,
    historical_ef58=False,
    repository_authority=None,
):
    repo = Path(repo).resolve()
    if not repo.is_dir():
        raise ReviewV2Error("repository root does not exist")
    if not historical_ef58:
        if repository_authority is None:
            try:
                repository_authority = sites.capture_repository_authority(repo)
            except sites.CaptureError as exc:
                raise ReviewV2Error(
                    "cannot snapshot fresh repository authority: {0}".format(exc)
                )
    elif repository_authority is not None:
        raise ReviewV2Error("historical review cannot consume fresh authority")
    hfs, hfs_file, hfs_data = read_json_with_bytes(
        failure_site_path, "failure sites"
    )
    _, _, v1_data = read_json_with_bytes(
        failure_flow_v1_path, "v1 failure flows"
    )
    try:
        with tempfile.TemporaryDirectory(
            prefix="host-module-failure-review-v2."
        ) as temporary:
            snapshot_root = Path(temporary)
            hfs_snapshot = flows_v2.write_private_snapshot(
                snapshot_root, "failure-sites.", hfs_data
            )
            v1_snapshot = flows_v2.write_private_snapshot(
                snapshot_root, "failure-flows-v1.", v1_data
            )
            expected_capture = flows_v2.build_capture(
                repo,
                hfs_snapshot,
                v1_snapshot,
                build_dir,
                kernel_dir,
                historical_ef58,
                repository_authority,
            )
    except (OSError, flows_v2.FlowV2Error) as exc:
        raise ReviewV2Error(
            "cannot derive v2 authority from supplied v1 bytes: {0}".format(exc)
        )
    flow_capture, flow_file = read_json(failure_flow_v2_path, "v2 failure flows")
    dispositions = validate_v2_capture(
        flow_capture, flow_file, hfs, hfs_file, expected_capture
    )
    contract, contract_file = validate_contract(repo)

    contract_map = {}
    for behavior in contract["behaviors"]:
        if behavior["kind"] != "legacy_errno":
            continue
        key = contract_identity(behavior["module"], behavior["legacy"])
        if key in contract_map:
            raise ReviewV2Error("legacy errno contract identities are duplicated")
        contract_map[key] = behavior

    active_mappings = []
    alias_hfs_by_contract_key = {}
    mapping_counts = Counter()
    for site in hfs["failure_sites"]:
        key = site_identity(site)
        disposition = dispositions[site["id"]]
        behavior = contract_map.get(key)
        alias_identity = None
        if behavior is not None:
            mapping = contract_mapping(behavior, "exact_conservative_contract_identity")
            match_kind = "exact_identity"
        elif disposition["kind"] == "logical_macro_definition":
            physical = disposition["conservative_physical_identity"]
            alias_identity = (
                physical["module"], physical["source"], physical["line"],
                physical["column"], physical["errno"],
            )
            behavior = contract_map.get(alias_identity)
            if behavior is None:
                raise ReviewV2Error("macro physical spelling has no contract row")
            mapping = contract_mapping(
                behavior, "compiler_logical_macro_alias"
            )
            alias_hfs_by_contract_key.setdefault(alias_identity, []).append(site["id"])
            match_kind = "compiler_logical_macro_alias"
        else:
            try:
                mapping = contracts.compiler_profile_failure_mapping(site)
            except contracts.ContractError as exc:
                raise ReviewV2Error("cannot supplement compiler-profile row: {0}".format(exc))
            match_kind = "selected_compiler_profile_supplement"
        mapping_counts[match_kind] += 1
        active_mappings.append(
            {
                "compiler_site": {
                    "column": site["column"],
                    "errno": site["errno"],
                    "hfs_id": site["id"],
                    "line": site["line"],
                    "module": site["module"],
                    "source": site["source"],
                },
                "contract_match_kind": match_kind,
                "contract_physical_alias_identity": (
                    {
                        "column": alias_identity[3],
                        "errno": alias_identity[4],
                        "line": alias_identity[2],
                        "module": alias_identity[0],
                        "source": alias_identity[1],
                    }
                    if alias_identity is not None
                    else None
                ),
                "disposition_kind": disposition["kind"],
                "mapping": mapping,
            }
        )

    active_mappings.sort(key=lambda item: item["compiler_site"]["hfs_id"])
    if len(active_mappings) != len(hfs["failure_sites"]):
        raise ReviewV2Error("compiler-active mapping closure differs")
    observed_supplements = {
        item["compiler_site"]["hfs_id"]
        for item in active_mappings
        if item["contract_match_kind"]
        == "selected_compiler_profile_supplement"
    }
    if observed_supplements != EXPECTED_SELECTED_PROFILE_SUPPLEMENTS:
        raise ReviewV2Error("selected compiler-profile supplement closure changed")
    stale_keys = sorted(set(contract_map) - set(site_identity(site) for site in hfs["failure_sites"]))
    if set(stale_keys) != set(EXPECTED_STALE_CONTRACT_IDENTITIES):
        raise ReviewV2Error("conservative-only contract identity closure changed")
    stale_rows = [
        classify_stale_contract_row(
            contract_map[key], alias_hfs_by_contract_key.get(key, [])
        )
        for key in stale_keys
    ]
    stale_counts = Counter(item["classification"] for item in stale_rows)
    blockers = sorted(
        set(flow_capture["blockers"])
        | {
            "acceptance_ids_are_declarations_not_executable_results",
            "selected_profile_supplements_are_not_frozen_contract_rows",
        }
    )
    coverage = {
        "c_ambiguous_failure_site_count": flow_capture["coverage"][
            "c_ambiguous_failure_site_count"
        ],
        "c_external_root_unresolved_count": flow_capture["coverage"][
            "c_external_root_unresolved_count"
        ],
        "compiler_active_exact_contract_count": mapping_counts["exact_identity"],
        "compiler_active_failure_site_count": len(hfs["failure_sites"]),
        "compiler_active_macro_alias_count": mapping_counts[
            "compiler_logical_macro_alias"
        ],
        "compiler_active_mapped_count": len(active_mappings),
        "compiler_active_missing_count": 0,
        "compiler_active_selected_profile_supplement_count": mapping_counts[
            "selected_compiler_profile_supplement"
        ],
        "conservative_contract_failure_site_count": len(contract_map),
        "reviewed_contract_failure_site_count": len(contract_map)
        + mapping_counts["selected_compiler_profile_supplement"],
        "rust_mir_unresolved_site_count": flow_capture["coverage"][
            "rust_mir_unresolved_site_count"
        ],
        "semantic_domain_unresolved_count": flow_capture["coverage"][
            "semantic_domain_unresolved_count"
        ],
        "stale_conservative_contract_count": len(stale_rows),
        "stale_conservative_contract_count_by_classification": dict(
            sorted(stale_counts.items())
        ),
    }
    review = {
        "active_site_mappings": active_mappings,
        "analysis_claim": dict(ANALYSIS_CLAIM),
        "authority_mode": expected_capture["authority_mode"],
        "blockers": blockers,
        "c_flow_analysis_scope": dict(flow_capture["analysis_scope"]),
        "coverage": coverage,
        "generator": "scripts/host_module_failure_contract_review_v2.py",
        "inputs": {
            "behavior_contract": contract_file,
            "failure_flows_v1": dict(
                expected_capture["inputs"]["failure_flows_v1"]
            ),
            "failure_flows_v2": flow_file,
            "failure_sites": {
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
        "stale_conservative_contract_sites": stale_rows,
    }
    if repository_authority is not None:
        try:
            sites.recheck_repository_authority(repo, repository_authority)
        except sites.CaptureError as exc:
            raise ReviewV2Error(
                "fresh repository authority changed during review: {0}".format(exc)
            )
    return review


def write_review(path, review):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = (
        json.dumps(review, allow_nan=False, indent=2, sort_keys=True) + "\n"
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
    parser.add_argument("--failure-flows-v1", type=Path, required=True)
    parser.add_argument("--failure-flows-v2", type=Path, required=True)
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
            raise ReviewV2Error(
                "fresh CLI requires the isolated repository-authority bootstrap"
            )
        review = build_review(
            args.repo, args.failure_sites, args.failure_flows_v1,
            args.failure_flows_v2, args.build_dir, args.kernel_dir,
            args.historical_ef58,
            repository_authority,
        )
        write_review(args.output, review)
    except ReviewV2Error as exc:
        print("host-module failure-contract v2 review failed: {0}".format(exc), file=sys.stderr)
        return 1
    print(
        "reviewed {0}/{1} compiler-active mappings with {2} exact-profile stale classifications; FP-0006 remains IN_PROGRESS".format(
            review["coverage"]["compiler_active_mapped_count"],
            review["coverage"]["compiler_active_failure_site_count"],
            review["coverage"]["stale_conservative_contract_count"],
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
