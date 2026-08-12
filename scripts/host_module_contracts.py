#!/usr/bin/env python3
"""Lock the native-Rust module policy and generate the legacy behavior map.

The policy manifest is the machine-readable authority for FP-0001 and
FP-0002.  The generated behavior contract is the executable FP-0006 map from
every frozen externally visible legacy surface and discovered errno token to
one native Rust replacement and at least one acceptance-test identifier.
"""

from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable, Sequence

import host_module_failure_sites as failure_site_tool
import host_module_inventory as inventory_tool


POLICY_PATH = Path("host-kernel/contracts/native-rust-host-modules-policy-v1.json")
INVENTORY_PATH = Path("host-kernel/reference/legacy-host-modules-f2eb7352.json")
CONTRACT_PATH = Path("host-kernel/contracts/legacy-behavior-contract-f2eb7352.json")

EXPECTED_MODULES = {
    "ihk": {
        "filename": "ihk.ko",
        "normalized_name": "ihk",
        "dependencies": [],
        "gate": "IHK-013",
    },
    "ihk_smp_x86_64": {
        "filename": "ihk-smp-x86_64.ko",
        "normalized_name": "ihk_smp_x86_64",
        "dependencies": ["ihk"],
        "gate": "SMP-015",
    },
    "mcctrl": {
        "filename": "mcctrl.ko",
        "normalized_name": "mcctrl",
        "dependencies": ["ihk"],
        "gate": "MCC-019",
    },
}

DEVICE_OPERATIONS = {
    "/dev/mcd{device_minor}": [
        "open",
        "read",
        "write",
        "mmap",
        "unlocked_ioctl",
        "release",
    ],
    "/dev/mcos{os_minor}": [
        "open",
        "write",
        "unlocked_ioctl",
        "release",
    ],
}

KIND_COMPONENT = {
    "module_identity": "module",
    "module_lifecycle": "module",
    "module_dependency": "module",
    "module_parameter": "params",
    "exported_symbol": "exports",
    "device_node": "device",
    "device_operation": "device",
    "ioctl": "device::ioctl",
    "aux_handler": "device::aux",
    "procfs": "procfs",
    "sysfs": "sysfs",
    "ikc_master_message": "ikc::master",
    "ikc_scd_message": "ikc::scd",
    "ikc_constant": "ikc::queue",
    "ikc_layout": "ikc::layout",
    "legacy_errno": "error",
    "forwarded_errno": "error",
}

KIND_HARNESS = {
    "module_identity": "module-metadata-golden",
    "module_lifecycle": "module-lifecycle-differential",
    "module_dependency": "module-dependency-golden",
    "module_parameter": "module-parameter-differential",
    "exported_symbol": "symbol-and-caller-differential",
    "device_node": "device-node-differential",
    "device_operation": "file-operation-differential",
    "ioctl": "ioctl-differential",
    "aux_handler": "aux-handler-differential",
    "procfs": "procfs-differential",
    "sysfs": "sysfs-differential",
    "ikc_master_message": "ikc-protocol-differential",
    "ikc_scd_message": "ikc-protocol-differential",
    "ikc_constant": "ikc-constant-golden",
    "ikc_layout": "layout-and-runtime-differential",
    "legacy_errno": "fault-and-errno-differential",
    "forwarded_errno": "provider-error-propagation-differential",
}

# Keep source-derived contract rows and compiler-backed evidence on one lexical
# definition.  In particular, Rust expresses many failures as
# ``-(EINVAL as c_long)``; the old direct-token-only matcher silently missed
# those sites.  ``mask_non_code`` below also ensures comments and literals
# cannot manufacture contract coverage.
ERRNO_PATTERN = failure_site_tool.ERRNO_PATTERN
PATCH_PATH = "scripts/patches/ihk-linux-compat.patch"
IHK_SYMBOL_NAMESPACE = "MCKERNEL_IHK_V1"


class ContractError(RuntimeError):
    """Raised when a policy or behavior contract is incomplete or stale."""


def canonical_bytes(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()


def pretty(value: object) -> str:
    return json.dumps(value, indent=2, sort_keys=True) + "\n"


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def slug(value: str, limit: int = 44) -> str:
    normalized = re.sub(r"[^A-Za-z0-9]+", "_", value).strip("_").upper()
    return (normalized or "VALUE")[:limit]


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ContractError(f"cannot parse {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ContractError(f"{path} must contain a JSON object")
    return value


def validate_policy(policy: dict[str, Any]) -> None:
    if policy.get("schema_version") != 1:
        raise ContractError("policy schema_version must be 1")
    if policy.get("policy_id") != "native-rust-host-modules-v1":
        raise ContractError("unexpected policy_id")
    if policy.get("architecture") != "x86_64":
        raise ContractError("only x86_64 may be in the scored policy")

    host = policy.get("host_platform")
    if not isinstance(host, dict):
        raise ContractError("host_platform is missing")
    expected_host = {
        "distribution_core": "Rocky Linux",
        "kernel_source_policy": "version-pinned Rocky-derived custom build",
        "config_rust_required": True,
        "kernel_core_conversion_target": False,
        "rocky_kabi_support_claimed": False,
    }
    for key, expected in expected_host.items():
        if host.get(key) != expected:
            raise ContractError(f"host_platform.{key} must be {expected!r}")

    scope = policy.get("conversion_scope")
    if not isinstance(scope, dict):
        raise ContractError("conversion_scope is missing")
    if scope.get("required_implementation_language") != "Rust-for-Linux":
        raise ContractError("production modules must use Rust-for-Linux")
    modules = scope.get("included_modules")
    if not isinstance(modules, list):
        raise ContractError("included_modules must be a list")
    actual: dict[str, dict[str, Any]] = {}
    for entry in modules:
        if not isinstance(entry, dict) or not isinstance(entry.get("crate"), str):
            raise ContractError("every included module needs a crate")
        crate = entry["crate"]
        if crate in actual:
            raise ContractError(f"duplicate included module {crate}")
        actual[crate] = entry
    if set(actual) != set(EXPECTED_MODULES):
        raise ContractError(
            f"conversion scope is {sorted(actual)}, expected {sorted(EXPECTED_MODULES)}"
        )
    for crate, expected in EXPECTED_MODULES.items():
        entry = actual[crate]
        for field in ("filename", "normalized_name"):
            if entry.get(field) != expected[field]:
                raise ContractError(f"{crate}.{field} does not match the locked target")
        if entry.get("permitted_project_module_dependencies") != expected["dependencies"]:
            raise ContractError(f"{crate} dependency set is not locked")

    completion = policy.get("completion_definition")
    if not isinstance(completion, dict):
        raise ContractError("completion_definition is missing")
    for key in (
        "production_link_graph_project_c_objects",
        "production_module_project_c_dispatch_targets",
        "production_module_project_c_implementation_bodies",
    ):
        if completion.get(key) != 0:
            raise ContractError(f"{key} must remain zero")
    if completion.get("assembly_is_not_rust") is not True:
        raise ContractError("assembly must remain separately classified")

    forbidden = policy.get("forbidden_production_inputs")
    if not isinstance(forbidden, list) or len(forbidden) < 8:
        raise ContractError("forbidden production input policy is incomplete")
    joined = "\n".join(str(item).lower() for item in forbidden)
    for required in ("c implementation", "c fallback", "c companion", "archive", "prebuilt"):
        if required not in joined:
            raise ContractError(f"forbidden policy does not cover {required}")

    boundaries = policy.get("permitted_non_rust_boundaries")
    if not isinstance(boundaries, list) or len(boundaries) != 4:
        raise ContractError("exactly four non-Rust boundary classes are allowed")
    boundary_text = "\n".join(json.dumps(item, sort_keys=True) for item in boundaries)
    for required in ("Linux kernel core", "public C UAPI", "Kbuild", "x86"):
        if required not in boundary_text:
            raise ContractError(f"allowed boundary {required!r} is missing")

    isolation = policy.get("reference_isolation")
    if not isinstance(isolation, dict):
        raise ContractError("reference isolation policy is missing")
    if isolation.get("reference_profile") != inventory_tool.PROFILE:
        raise ContractError("reference profile is not the frozen inventory profile")
    forbidden_locations = isolation.get("forbidden_locations")
    if not isinstance(forbidden_locations, list) or len(forbidden_locations) < 5:
        raise ContractError("reference isolation locations are incomplete")

    invalidation = policy.get("evidence_invalidation_rules")
    if not isinstance(invalidation, list) or len(invalidation) < 6:
        raise ContractError("evidence invalidation rules are incomplete")
    for index, rule in enumerate(invalidation):
        if not isinstance(rule, dict) or set(rule) != {"change", "invalidates", "reason"}:
            raise ContractError(f"evidence invalidation rule {index} is malformed")

    dependencies = policy.get("dependency_rules")
    if not isinstance(dependencies, dict):
        raise ContractError("dependency rules are missing")
    if dependencies.get("load_order") != ["ihk", "ihk_smp_x86_64", "mcctrl"]:
        raise ContractError("module load order changed")
    if dependencies.get("unload_order") != ["mcctrl", "ihk_smp_x86_64", "ihk"]:
        raise ContractError("module unload order changed")
    for flag in (
        "no_undeclared_runtime_symbol_lookup",
        "no_project_c_companion_module",
        "no_prebuilt_project_object",
        "symbol_namespaces_required",
    ):
        if dependencies.get(flag) is not True:
            raise ContractError(f"dependency rule {flag} must be true")

    oracles = policy.get("module_oracles")
    if not isinstance(oracles, dict):
        raise ContractError("module oracle policy is missing")
    profiles = oracles.get("profiles")
    if not isinstance(profiles, dict) or set(profiles) != {"R0", "R1", "R2"}:
        raise ContractError("module oracle profiles must be exactly R0, R1, and R2")
    expected_bindings = {
        "R0": {
            "source_commit",
            "ihk_commit",
            "kernel_nvr",
            "kernel_build_id",
            "kernel_config_sha256",
            "toolchain_manifest_sha256",
            "artifact_sha256",
        },
        "R1": {
            "source_commit",
            "ihk_commit",
            "kernel_nvr",
            "kernel_build_id",
            "kernel_config_sha256",
            "toolchain_manifest_sha256",
            "artifact_sha256",
        },
        "R2": {
            "source_commit",
            "kernel_nvr",
            "kernel_build_id",
            "kernel_config_sha256",
            "toolchain_manifest_sha256",
            "artifact_sha256",
        },
    }
    for profile, required in expected_bindings.items():
        entry = profiles.get(profile)
        if not isinstance(entry, dict):
            raise ContractError(f"module oracle profile {profile} is malformed")
        if set(entry.get("required_bindings", [])) != required:
            raise ContractError(f"module oracle profile {profile} bindings changed")
    required_comparison_fields = {
        "kernel_nvr",
        "kernel_build_id",
        "kernel_config_sha256",
        "toolchain_manifest_sha256",
        "vermagic",
        "signing_policy",
        "dependency_names",
        "symbol_signatures",
    }
    if set(oracles.get("comparison_identity_fields", [])) != required_comparison_fields:
        raise ContractError("R1/R2 comparison identity fields changed")
    comparison = str(oracles.get("production_comparison", ""))
    if "R1 and R2" not in comparison or "R0" not in comparison:
        raise ContractError("module oracle production comparison is incomplete")

    symbol_contract = policy.get("module_symbol_contract")
    if not isinstance(symbol_contract, dict):
        raise ContractError("module symbol contract is missing")
    if symbol_contract.get("production_namespaces") != {
        "ihk": IHK_SYMBOL_NAMESPACE
    }:
        raise ContractError("production symbol namespaces changed")
    if symbol_contract.get("required_imports") != {
        "ihk_smp_x86_64": [IHK_SYMBOL_NAMESPACE],
        "mcctrl": [IHK_SYMBOL_NAMESPACE],
    }:
        raise ContractError("production namespace imports changed")
    if "intentional production-only" not in str(
        symbol_contract.get("r0_namespace_policy", "")
    ):
        raise ContractError("R0 namespace delta is not explicit")
    modversions = symbol_contract.get("modversions")
    if not isinstance(modversions, dict) or set(modversions) != {
        "config_source",
        "disabled",
        "enabled",
        "r0_crc_policy",
    }:
        raise ContractError("conditional MODVERSIONS policy is incomplete")
    if "R1/R2" not in str(modversions["enabled"]):
        raise ContractError("enabled MODVERSIONS policy does not bind R1 to R2")
    if "omit symbol CRC" not in str(modversions["disabled"]):
        raise ContractError("disabled MODVERSIONS policy does not reject CRCs")
    if modversions["r0_crc_policy"] != "informational provenance only":
        raise ContractError("R0 CRCs must remain informational")


def apply_unified_diff_to_text(
    text: str, patch_text: str, source_path: str
) -> tuple[str, bool]:
    """Apply one file's unified diff while preserving deterministic provenance."""

    relative = source_path.removeprefix("ihk/")
    lines = patch_text.splitlines(keepends=True)
    start: int | None = None
    end = len(lines)
    for index, line in enumerate(lines):
        match = re.match(r"^diff --git a/(\S+) b/(\S+)\s*$", line)
        if not match:
            continue
        if start is not None:
            end = index
            break
        if source_path.startswith("ihk/") and match.group(1) == relative:
            start = index
    if start is None:
        return text, False

    original = text.splitlines(keepends=True)
    output: list[str] = []
    cursor = 0
    index = start
    while index < end:
        header = re.match(
            r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@",
            lines[index],
        )
        if not header:
            index += 1
            continue
        old_start = int(header.group(1)) - 1
        old_count = int(header.group(2) or "1")
        if old_start < cursor:
            raise ContractError(f"overlapping patch hunks for {source_path}")
        output.extend(original[cursor:old_start])
        cursor = old_start
        consumed = 0
        index += 1
        while index < end and not lines[index].startswith("@@ "):
            line = lines[index]
            if line.startswith("diff --git "):
                break
            if line.startswith("\\ No newline at end of file"):
                index += 1
                continue
            if not line or line[0] not in " +-":
                raise ContractError(
                    f"malformed unified diff line for {source_path}: {line!r}"
                )
            marker, value = line[0], line[1:]
            if marker in " -":
                if cursor >= len(original) or original[cursor] != value:
                    raise ContractError(
                        f"compatibility overlay context mismatch for {source_path} "
                        f"at source line {cursor + 1}"
                    )
                cursor += 1
                consumed += 1
            if marker in " +":
                output.append(value)
            index += 1
        if consumed != old_count:
            raise ContractError(
                f"compatibility overlay hunk count mismatch for {source_path}: "
                f"consumed {consumed}, expected {old_count}"
            )
    output.extend(original[cursor:])
    return "".join(output), True


def effective_source_text(
    repo: Path, path: str, language: str = "c"
) -> tuple[str, dict[str, Any]]:
    base = inventory_tool.source_blob(repo, path).decode("utf-8", errors="replace")
    patch = inventory_tool.source_blob(repo, PATCH_PATH)
    if language == "c":
        effective, applied = apply_unified_diff_to_text(
            base, patch.decode("utf-8", errors="strict"), path
        )
        filtered = inventory_tool.filter_simple_cpp(
            inventory_tool.strip_c_comments(effective), inventory_tool.CPP_DEFINES
        )
        filter_mode = "compatibility overlay plus conservative named-guard CPP"
        cpp_defines: list[str] = sorted(inventory_tool.CPP_DEFINES)
        unknown_policy: str | None = "retain both branches conservatively"
    elif language == "rust":
        effective, applied = base, False
        filtered = inventory_tool.strip_c_comments(effective)
        filter_mode = "Rust source with comments removed; no cfg attributes in frozen input"
        cpp_defines = []
        unknown_policy = None
    else:
        raise ContractError(f"unsupported failure-site source language {language}: {path}")
    return filtered, {
        "base_sha256": sha256(base.encode()),
        "compatibility_overlay_applied": applied,
        "compatibility_overlay_sha256": sha256(patch) if applied else None,
        "cpp_defines": cpp_defines,
        "cpp_unknown_condition_policy": unknown_policy,
        "effective_source_sha256": sha256(effective.encode()),
        "effective_filtered_sha256": sha256(filtered.encode()),
        "filter_mode": filter_mode,
        "language": language,
    }


def source_errno_surface(repo: Path, legacy: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    result: dict[str, list[dict[str, Any]]] = {}
    source_modules = legacy["source_capture"]["modules"]
    for module in EXPECTED_MODULES:
        occurrences: list[dict[str, Any]] = []
        for entry in source_modules[module]["active_inputs"]:
            path = str(entry["source"])
            language = str(entry.get("language"))
            if language not in {"c", "rust"}:
                continue
            filtered, provenance = effective_source_text(repo, path, language)
            try:
                masked = failure_site_tool.mask_non_code(filtered, language)
            except failure_site_tool.CaptureError as exc:
                raise ContractError(
                    f"cannot lexically mask failure-site source {path}: {exc}"
                ) from exc
            for match in ERRNO_PATTERN.finditer(masked):
                line = filtered.count("\n", 0, match.start()) + 1
                line_start = filtered.rfind("\n", 0, match.start()) + 1
                line_end = filtered.find("\n", match.end())
                if line_end < 0:
                    line_end = len(filtered)
                statement = " ".join(filtered[line_start:line_end].strip().split())
                expression = filtered[match.start() : match.end()]
                occurrences.append(
                    {
                        "classification": "explicit_negative_errno_token",
                        "column": match.start() - line_start + 1,
                        "errno": match.group(1),
                        "expression": expression,
                        "expression_sha256": sha256(expression.encode()),
                        "line": line,
                        "source": path,
                        "source_provenance": provenance,
                        "statement": statement,
                        "syntax": (
                            "parenthesized_or_cast"
                            if re.match(r"-\s*\(", expression)
                            else "direct"
                        ),
                    }
                )
        occurrences.sort(
            key=lambda item: (
                str(item["source"]),
                int(item["line"]),
                int(item["column"]),
                str(item["errno"]),
            )
        )
        for occurrence in occurrences:
            occurrence["site_id"] = (
                f"{module}:{occurrence['source']}:{occurrence['line']}:"
                f"{occurrence['column']}:{occurrence['errno']}"
            )
        result[module] = occurrences
    return result


def failure_site_key(entry: dict[str, Any]) -> tuple[str, str, int, int, str]:
    """Return the cross-oracle identity shared with compiler-backed capture."""

    try:
        return (
            str(entry["module"]),
            str(entry["source"]),
            int(entry["line"]),
            int(entry["column"]),
            str(entry["errno"]),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise ContractError(f"malformed compiler failure-site identity: {entry!r}") from exc


def validate_compiler_failure_capture(
    contract: dict[str, Any], capture: dict[str, Any]
) -> dict[str, int]:
    """Prove every compiler-active negative errno site has a contract row.

    The source contract is deliberately conservative when a preprocessor guard
    cannot be resolved from the frozen inventory.  Therefore compiler-active
    rows must be a subset, not necessarily an exact set, of source-derived rows.
    The comparison still fails closed for an unknown, duplicated, or
    provenance-mismatched compiler row.
    """

    if capture.get("schema_version") != failure_site_tool.SCHEMA_VERSION:
        raise ContractError("compiler failure capture schema_version changed")
    if capture.get("profile") != failure_site_tool.PROFILE:
        raise ContractError("compiler failure capture profile changed")
    provenance = capture.get("provenance")
    if not isinstance(provenance, dict):
        raise ContractError("compiler failure capture provenance is missing")
    frozen = provenance.get("frozen_inventory")
    if not isinstance(frozen, dict) or frozen.get("sha256") != contract.get(
        "inventory_file_sha256"
    ):
        raise ContractError("compiler failure capture inventory digest is stale")
    sites = capture.get("failure_sites")
    if not isinstance(sites, list) or not sites:
        raise ContractError("compiler failure capture has no active sites")

    mapped: dict[tuple[str, str, int, int, str], dict[str, Any]] = {}
    for behavior in contract.get("behaviors", []):
        if not isinstance(behavior, dict) or behavior.get("kind") != "legacy_errno":
            continue
        legacy = behavior.get("legacy")
        if not isinstance(legacy, dict):
            raise ContractError("legacy errno behavior has malformed source identity")
        keyed = dict(legacy)
        keyed["module"] = behavior.get("module")
        key = failure_site_key(keyed)
        if key in mapped:
            raise ContractError(f"duplicate mapped compiler failure-site key {key}")
        mapped[key] = legacy

    active: set[tuple[str, str, int, int, str]] = set()
    by_module: Counter[str] = Counter()
    for index, site in enumerate(sites):
        if not isinstance(site, dict):
            raise ContractError(f"compiler failure site {index} is malformed")
        required_site_fields = {
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
        if set(site) != required_site_fields:
            raise ContractError(
                f"compiler failure site {index} does not match its locked schema"
            )
        if site.get("classification") != "explicit_negative_errno_token":
            raise ContractError(
                f"compiler failure site {index} has unknown classification"
            )
        key = failure_site_key(site)
        if key in active:
            raise ContractError(f"duplicate compiler failure-site key {key}")
        active.add(key)
        by_module[key[0]] += 1
        if key not in mapped:
            raise ContractError(
                "compiler-active failure site has no Rust/test mapping: "
                f"{key[0]}:{key[1]}:{key[2]}:{key[3]}:{key[4]}"
            )
        identity = {
            "column": site["column"],
            "errno": site["errno"],
            "language": site["language"],
            "line": site["line"],
            "module": site["module"],
            "source": site["source"],
            "source_sha256": site["source_sha256"],
        }
        identity_sha256 = failure_site_tool.sha256_bytes(
            failure_site_tool.canonical_bytes(identity)
        )
        if site["identity_sha256"] != identity_sha256 or site["id"] != (
            "HFS-" + identity_sha256[:24].upper()
        ):
            raise ContractError(f"compiler failure site {index} identity is stale")
        mapped_site = mapped[key]
        source_provenance = mapped_site.get("source_provenance")
        if not isinstance(source_provenance, dict):
            raise ContractError(f"mapped failure site {key} lacks source provenance")
        if source_provenance.get("language") != site["language"]:
            raise ContractError(f"compiler failure site {index} language changed")
        if source_provenance.get("effective_source_sha256") != site[
            "source_sha256"
        ]:
            raise ContractError(
                f"compiler failure site {index} does not use the frozen effective source"
            )
        if mapped_site.get("expression") != site["expression"]:
            raise ContractError(f"compiler failure site {index} expression changed")

    if set(by_module) != set(EXPECTED_MODULES):
        raise ContractError(
            "compiler failure capture does not cover all production modules"
        )
    coverage = capture.get("coverage")
    if not isinstance(coverage, dict):
        raise ContractError("compiler failure capture coverage is missing")
    if coverage.get("failure_site_count") != len(active):
        raise ContractError("compiler failure capture total is stale")
    if coverage.get("by_module") != dict(sorted(by_module.items())):
        raise ContractError("compiler failure capture module totals are stale")
    return dict(sorted(by_module.items()))


def parameter_default(repo: Path, parameter: dict[str, Any]) -> dict[str, Any]:
    path = str(parameter["source"])
    filtered, provenance = effective_source_text(repo, path)
    name = re.escape(str(parameter["name"]))
    declaration = re.compile(
        rf"\b(?:static\s+)?(?P<ctype>unsigned\s+(?:int|long)|int|long|bool)\s+"
        rf"{name}\s*=\s*(?P<value>[^;]+);"
    )
    matches = list(declaration.finditer(filtered))
    if len(matches) != 1:
        raise ContractError(
            f"expected one initialized declaration for module parameter "
            f"{parameter['name']} in {path}, found {len(matches)}"
        )
    match = matches[0]
    expression = match.group("value").strip()
    try:
        value = inventory_tool.parse_c_integer(expression)
    except inventory_tool.InventoryError as exc:
        raise ContractError(
            f"cannot evaluate default for module parameter {parameter['name']}: {exc}"
        ) from exc
    return {
        "c_type": " ".join(match.group("ctype").split()),
        "expression": expression,
        "line": filtered.count("\n", 0, match.start()) + 1,
        "source_provenance": provenance,
        "value": value,
    }


def flatten_procfs(procfs: dict[str, Any]) -> Iterable[tuple[str, dict[str, Any], str]]:
    for key in ("dynamic_directories", "dynamic_symlinks"):
        for index, entry in enumerate(procfs.get(key, [])):
            if isinstance(entry, dict):
                name = str(entry.get("path_format") or entry.get("name") or f"{key}-{index}")
            else:
                name = str(entry)
            yield name, entry, f"procfs.{key}[{index}]"
    tables = procfs.get("tables", {})
    if isinstance(tables, dict):
        for table_name, entries in sorted(tables.items()):
            if not isinstance(entries, list):
                continue
            for index, entry in enumerate(entries):
                if not isinstance(entry, dict):
                    continue
                name = str(entry.get("name") or entry.get("path") or f"{table_name}-{index}")
                value = dict(entry)
                value["table"] = table_name
                yield name, value, f"procfs.tables.{table_name}[{index}]"


def build_contract(repo: Path, policy: dict[str, Any], legacy: dict[str, Any]) -> dict[str, Any]:
    validate_policy(policy)
    if legacy.get("profile") != inventory_tool.PROFILE:
        raise ContractError("legacy inventory profile changed")
    if legacy.get("module_order") != ["ihk", "ihk_smp_x86_64", "mcctrl"]:
        raise ContractError("legacy module order changed")

    behaviors: list[dict[str, Any]] = []
    tests: list[dict[str, Any]] = []
    seen_keys: set[str] = set()

    def add(
        module: str,
        kind: str,
        name: str,
        legacy_value: object,
        oracle_path: str,
        assertions: Sequence[str],
    ) -> None:
        if module not in EXPECTED_MODULES:
            raise ContractError(f"unknown behavior module {module}")
        if kind not in KIND_COMPONENT:
            raise ContractError(f"unknown behavior kind {kind}")
        key = f"{module}|{kind}|{name}|{oracle_path}"
        if key in seen_keys:
            raise ContractError(f"duplicate behavior key {key}")
        seen_keys.add(key)
        suffix = sha256(key.encode())[:10].upper()
        behavior_id = f"BHV-{slug(module, 20)}-{slug(kind, 24)}-{slug(name)}-{suffix}"
        test_id = f"AT-{slug(module, 20)}-{slug(kind, 24)}-{suffix}"
        component = KIND_COMPONENT[kind]
        replacement = f"crate::{component}::{slug(name).lower()}_{suffix.lower()}"
        behavior = {
            "acceptance_test_ids": [test_id],
            "id": behavior_id,
            "kind": kind,
            "legacy": legacy_value,
            "module": module,
            "oracle_path": oracle_path,
            "rust_replacement": {
                "crate": module,
                "native_path": replacement,
                "project_c_dispatch_permitted": False,
            },
        }
        test = {
            "assertions": list(assertions),
            "behavior_ids": [behavior_id],
            "gate_targets": [EXPECTED_MODULES[module]["gate"], "INT-004"],
            "harness": KIND_HARNESS[kind],
            "id": test_id,
            "module": module,
        }
        behaviors.append(behavior)
        tests.append(test)

    binary_modules = legacy["binary_capture"]["modules"]
    source_modules = legacy["source_capture"]["modules"]
    for module, expected in EXPECTED_MODULES.items():
        details = binary_modules[module]
        modinfo = details["modinfo"]["values"]
        identity = {
            "production_contract": {
                "filename": expected["filename"],
                "license": modinfo.get("license", []),
                "normalized_name": expected["normalized_name"],
                "vermagic_policy": (
                    "R1 legacy-C and R2 native-Rust artifacts must have identical "
                    "vermagic for the selected custom Rocky kernel NVR; the R0 Rocky "
                    "8.10 vermagic is provenance only and must not be copied"
                ),
            },
            "r0_reference": {
                "filename": expected["filename"],
                "license": modinfo.get("license", []),
                "normalized_name": expected["normalized_name"],
                "vermagic": modinfo.get("vermagic", []),
            },
        }
        add(
            module,
            "module_identity",
            expected["normalized_name"],
            identity,
            f"binary_capture.modules.{module}.modinfo",
            [
                "filename, normalized name, and compatible license match the frozen interface",
                "R1 and R2 vermagic match the selected custom Rocky kernel exactly without requiring R0 vermagic equality",
                "no unexpected module taint",
            ],
        )
        for action in ("load", "unload"):
            add(
                module,
                "module_lifecycle",
                action,
                {"action": action},
                f"policy.dependency_rules.{action}_order",
                ["same success or busy result as the reference", "no warning, leak, callback, or registration remains"],
            )
        for provider in expected["dependencies"]:
            add(
                module,
                "module_dependency",
                provider,
                {
                    "consumer": module,
                    "provider": provider,
                    "required_symbol_namespace": IHK_SYMBOL_NAMESPACE,
                },
                f"policy.conversion_scope.included_modules.{module}.dependencies",
                [
                    "dependency and required provider namespace are declared and versioned",
                    "load and unload ordering is enforced",
                ],
            )
        for index, parameter in enumerate(source_modules[module]["source_module_parameters"]):
            parameter_contract = dict(parameter)
            parameter_contract["default"] = parameter_default(repo, parameter)
            add(
                module,
                "module_parameter",
                str(parameter["name"]),
                parameter_contract,
                f"source_capture.modules.{module}.source_module_parameters[{index}]",
                ["name, type, permissions, default, and invalid-input behavior match", "parameter lifetime survives load and unload cycles"],
            )
        source_exports = {
            str(entry["name"]): entry
            for entry in source_modules[module]["source_export_macros"]
        }
        for index, exported in enumerate(details["exports"]):
            name = str(exported["name"])
            source_export = source_exports.get(name)
            if source_export is None:
                raise ContractError(f"missing source export provenance for {module}:{name}")
            export_contract = {
                "production_contract": {
                    "export_class": source_export["class"],
                    "name": name,
                    "namespace": IHK_SYMBOL_NAMESPACE,
                    "namespace_policy": (
                        "an intentional production-only namespace delta; R0 has no "
                        "namespace and consumers must import the new namespace"
                    ),
                    "symbol_version_policy": (
                        "when the selected kernel enables CONFIG_MODVERSIONS, R1 and R2 "
                        "CRCs must match each other; when disabled, both must omit CRCs; "
                        "the R0 CRC is provenance only"
                    ),
                },
                "r0_reference": dict(exported),
                "source_declaration": source_export,
            }
            add(
                module,
                "exported_symbol",
                name,
                export_contract,
                f"binary_capture.modules.{module}.exports[{index}]",
                [
                    "symbol name, signature, export class, and consumer relationship match",
                    "the declared production namespace is imported by every R2 consumer as an intentional delta from unnamespaced R0",
                    "symbol CRCs match R1 only when CONFIG_MODVERSIONS is enabled and are absent from both R1 and R2 otherwise",
                    "all frozen consumers rebuilt for R1 and R2 link and execute identically",
                ],
            )

    for index, node in enumerate(legacy["device_nodes"]):
        path_template = str(node["path_template"])
        add(
            "ihk",
            "device_node",
            path_template,
            node,
            f"device_nodes[{index}]",
            ["major/minor allocation and node naming match", "all nodes are removed on unload and failed initialization"],
        )
        for operation in DEVICE_OPERATIONS[path_template]:
            add(
                "ihk",
                "device_operation",
                f"{path_template}:{operation}",
                {"path_template": path_template, "operation": operation},
                f"device_nodes[{index}].operations.{operation}",
                ["return value, errno, output bytes, and side effects match", "invalid, concurrent, interrupted, and teardown cases leave no residual state"],
            )

    ioctl_groups = legacy["ioctls"]
    dispatch_sets = {
        "ihk_device_constants": set(ioctl_groups["ihk_device_dispatch_cases"]),
        "ihk_os_constants": set(ioctl_groups["ihk_os_dispatch_cases"]),
        "mcctrl_operation_constants": set(ioctl_groups["mcctrl_control_switch_cases"]),
    }
    for group in ("ihk_device_constants", "ihk_os_constants", "mcctrl_operation_constants"):
        module = "mcctrl" if group.startswith("mcctrl") else "ihk"
        for index, entry in enumerate(ioctl_groups[group]):
            value = dict(entry)
            value["legacy_dispatch_case_present"] = entry["name"] in dispatch_sets[group]
            add(
                module,
                "ioctl",
                str(entry["name"]),
                value,
                f"ioctls.{group}[{index}]",
                ["numeric command and compat command match", "valid and invalid argument return, errno, copied data, and state transition match"],
            )
    for index, entry in enumerate(ioctl_groups["mcctrl_registered_aux_handlers"]):
        if isinstance(entry, dict):
            name = str(entry.get("name") or entry.get("request") or index)
        else:
            name = str(entry)
        add(
            "mcctrl",
            "aux_handler",
            name,
            entry,
            f"ioctls.mcctrl_registered_aux_handlers[{index}]",
            ["handler registration and request number match", "success, failure, and unregister behavior match"],
        )

    add(
        "mcctrl",
        "procfs",
        "root",
        {
            "root_name_format": legacy["procfs"]["root_name_format"],
            "root_path_template": legacy["procfs"]["root_path_template"],
        },
        "procfs.root_path_template",
        ["root name, path, ownership, and creation behavior match", "failed setup and unload remove the complete hierarchy"],
    )
    for name, entry, path in flatten_procfs(legacy["procfs"]):
        add(
            "mcctrl",
            "procfs",
            name,
            entry,
            path,
            ["path, type, mode, content, partial-read, seek, and errno behavior match", "concurrent process exit and module unload are lifetime-safe"],
        )
    add(
        "mcctrl",
        "sysfs",
        "root",
        {
            "anchor": legacy["sysfs"]["anchor"],
            "root_component": legacy["sysfs"]["root_component"],
        },
        "sysfs.root_component",
        ["root anchor, kobject ownership, and setup behavior match", "failed setup and unload remove the complete hierarchy"],
    )
    for index, entry in enumerate(legacy["sysfs"]["entries"]):
        name = f"{entry.get('operation')}:{entry.get('path_format')}"
        add(
            "mcctrl",
            "sysfs",
            name,
            entry,
            f"sysfs.entries[{index}]",
            ["operation, path, mode, show/store bytes, and errno match", "concurrent removal and module unload are lifetime-safe"],
        )

    ikc = legacy["ikc"]
    for index, entry in enumerate(ikc["master_messages"]):
        add(
            "ihk",
            "ikc_master_message",
            str(entry["name"]),
            entry,
            f"ikc.master_messages[{index}]",
            ["message value and field interpretation match", "connect, reply, disconnect, malformed, duplicate, and teardown behavior match"],
        )
    for index, entry in enumerate(ikc["scd_messages"]):
        add(
            "mcctrl",
            "ikc_scd_message",
            str(entry["name"]),
            entry,
            f"ikc.scd_messages[{index}]",
            ["message value, packet fields, reply, errno, and side effects match", "unknown, malformed, duplicate, interrupted, and teardown behavior match"],
        )
    for group in ("channel_flags", "queue_options"):
        for index, entry in enumerate(ikc[group]):
            add(
                "ihk",
                "ikc_constant",
                str(entry["name"]),
                entry,
                f"ikc.{group}[{index}]",
                ["numeric value and state-machine interpretation match", "invalid combinations are rejected without side effects"],
            )
    add(
        "ihk",
        "ikc_constant",
        str(ikc["max_port"]["name"]),
        ikc["max_port"],
        "ikc.max_port",
        ["numeric limit and boundary behavior match", "out-of-range ports are rejected without allocation"],
    )
    add(
        "ihk",
        "ikc_layout",
        "queue_head",
        ikc["queue_head"],
        "ikc.queue_head",
        ["size, alignment, field offsets, and endian interpretation match", "ring wrap, saturation, ordering, and corruption handling match"],
    )
    add(
        "mcctrl",
        "ikc_layout",
        "scd_packet",
        ikc["scd_packet"],
        "ikc.scd_packet",
        ["128-byte packet size and all shared field offsets match", "packet boundary and malformed-length handling match"],
    )

    errno_surface = source_errno_surface(repo, legacy)
    for module in EXPECTED_MODULES:
        for entry in errno_surface[module]:
            stable_oracle_key = sha256(str(entry["site_id"]).encode())[:24]
            add(
                module,
                "legacy_errno",
                str(entry["site_id"]),
                entry,
                f"source_errno_surface.{module}.by_site_id.{stable_oracle_key}",
                [
                    "the same explicit failure site returns the exact negative errno",
                    "the mapped Rust fault test proves the intended site fired",
                    "output and ownership state match after the failure",
                ],
            )
        add(
            module,
            "forwarded_errno",
            "provider_errno",
            {"contract": "preserve negative Linux/provider errno unless the frozen wrapper explicitly translates it"},
            f"source_errno_surface.{module}.forwarded_provider_result",
            ["injected provider failures preserve the frozen return translation", "no partial registration, allocation, mapping, or callback ownership remains"],
        )

    behaviors.sort(key=lambda item: item["id"])
    tests.sort(key=lambda item: item["id"])
    coverage = {
        "behavior_count": len(behaviors),
        "by_kind": dict(sorted(Counter(item["kind"] for item in behaviors).items())),
        "by_module": dict(sorted(Counter(item["module"] for item in behaviors).items())),
        "errno_by_module": {
            module: sorted({entry["errno"] for entry in errno_surface[module]})
            for module in EXPECTED_MODULES
        },
        "errno_sites_by_module": {
            module: len(errno_surface[module])
            for module in EXPECTED_MODULES
        },
        "errno_syntax_by_module": {
            module: dict(
                sorted(Counter(entry["syntax"] for entry in errno_surface[module]).items())
            )
            for module in EXPECTED_MODULES
        },
        "test_count": len(tests),
    }
    return {
        "acceptance_tests": tests,
        "behaviors": behaviors,
        "coverage": coverage,
        "generator": "scripts/host_module_contracts.py",
        "inventory_file_sha256": sha256((repo / INVENTORY_PATH).read_bytes()),
        "inventory_profile": legacy["profile"],
        "policy_file_sha256": sha256((repo / POLICY_PATH).read_bytes()),
        "policy_id": policy["policy_id"],
        "comparison_profiles": {
            "R0": "frozen Rocky 8.10 binary and runtime provenance oracle",
            "R1": "legacy C modules rebuilt for the selected custom Rocky kernel",
            "R2": "native Rust modules built for the exact same custom Rocky kernel",
            "identity_rule": "R1 and R2 are compared directly; R0 kernel-specific metadata is never copied into R2",
        },
        "failure_mapping": {
            "classification": "explicit_negative_errno_token",
            "compiler_capture_match_key": [
                "module",
                "source",
                "line",
                "column",
                "errno",
            ],
            "compiler_capture_profile": failure_site_tool.PROFILE,
            "compiler_capture_subset_policy": (
                "every compiler-active site must map to exactly one conservative "
                "source-derived behavior row"
            ),
            "lexical_masking": "comments, strings, byte strings, raw strings, and character literals excluded",
            "rust_casted_errno_syntax_included": True,
        },
        "provenance": {
            "parent_commit": legacy["provenance"]["parent_commit"],
            "ihk_commit": legacy["provenance"]["ihk_commit"],
            "reference_workflow_run": legacy["provenance"]["workflow_run"],
            "reference_artifact_id": legacy["provenance"]["artifact_id"],
        },
        "schema_version": 2,
    }


def validate_contract(contract: dict[str, Any], policy: dict[str, Any], legacy: dict[str, Any], repo: Path) -> None:
    validate_policy(policy)
    if contract.get("schema_version") != 2:
        raise ContractError("contract schema_version must be 2")
    if contract.get("policy_id") != policy.get("policy_id"):
        raise ContractError("contract policy_id is stale")
    if contract.get("policy_file_sha256") != sha256((repo / POLICY_PATH).read_bytes()):
        raise ContractError("contract policy digest is stale")
    if contract.get("inventory_file_sha256") != sha256((repo / INVENTORY_PATH).read_bytes()):
        raise ContractError("contract inventory digest is stale")
    profiles = contract.get("comparison_profiles")
    if not isinstance(profiles, dict) or set(profiles) != {"R0", "R1", "R2", "identity_rule"}:
        raise ContractError("R0/R1/R2 comparison profiles are missing")
    if "R1 and R2" not in str(profiles["identity_rule"]):
        raise ContractError("module identity must compare R1 directly with R2")
    failure_mapping = contract.get("failure_mapping")
    expected_failure_mapping = {
        "classification": "explicit_negative_errno_token",
        "compiler_capture_match_key": [
            "module",
            "source",
            "line",
            "column",
            "errno",
        ],
        "compiler_capture_profile": failure_site_tool.PROFILE,
        "compiler_capture_subset_policy": (
            "every compiler-active site must map to exactly one conservative "
            "source-derived behavior row"
        ),
        "lexical_masking": "comments, strings, byte strings, raw strings, and character literals excluded",
        "rust_casted_errno_syntax_included": True,
    }
    if failure_mapping != expected_failure_mapping:
        raise ContractError("failure mapping scanner contract is missing or stale")

    behaviors = contract.get("behaviors")
    tests = contract.get("acceptance_tests")
    if not isinstance(behaviors, list) or not behaviors:
        raise ContractError("contract has no behaviors")
    if not isinstance(tests, list) or not tests:
        raise ContractError("contract has no acceptance tests")
    behavior_by_id: dict[str, dict[str, Any]] = {}
    test_by_id: dict[str, dict[str, Any]] = {}
    native_paths: set[str] = set()
    for behavior in behaviors:
        if not isinstance(behavior, dict) or not isinstance(behavior.get("id"), str):
            raise ContractError("malformed behavior entry")
        behavior_id = behavior["id"]
        if behavior_id in behavior_by_id:
            raise ContractError(f"duplicate behavior id {behavior_id}")
        behavior_by_id[behavior_id] = behavior
        replacement = behavior.get("rust_replacement")
        if not isinstance(replacement, dict):
            raise ContractError(f"{behavior_id} has no Rust replacement")
        if replacement.get("crate") != behavior.get("module"):
            raise ContractError(f"{behavior_id} replacement crate mismatch")
        native_path = replacement.get("native_path")
        if not isinstance(native_path, str) or not native_path.startswith("crate::"):
            raise ContractError(f"{behavior_id} replacement is not a native Rust path")
        if native_path in native_paths:
            raise ContractError(f"duplicate native Rust replacement path {native_path}")
        native_paths.add(native_path)
        if replacement.get("project_c_dispatch_permitted") is not False:
            raise ContractError(f"{behavior_id} permits project C dispatch")
        test_ids = behavior.get("acceptance_test_ids")
        if not isinstance(test_ids, list) or not test_ids:
            raise ContractError(f"{behavior_id} has no acceptance test id")
        legacy_value = behavior.get("legacy")
        kind = behavior.get("kind")
        if kind in {
            "module_identity",
            "exported_symbol",
            "module_parameter",
            "legacy_errno",
        } and not isinstance(legacy_value, dict):
            raise ContractError(f"{behavior_id} has malformed legacy contract")
        if kind == "module_identity":
            assert isinstance(legacy_value, dict)
            production = legacy_value.get("production_contract")
            r0 = legacy_value.get("r0_reference")
            if not isinstance(production, dict) or not isinstance(r0, dict):
                raise ContractError(f"{behavior_id} does not separate R0 identity from production")
            if "vermagic" in production or "R1" not in str(production.get("vermagic_policy")):
                raise ContractError(f"{behavior_id} incorrectly freezes R0 vermagic")
            if not r0.get("vermagic"):
                raise ContractError(f"{behavior_id} lacks R0 vermagic provenance")
        elif kind == "exported_symbol":
            assert isinstance(legacy_value, dict)
            production = legacy_value.get("production_contract")
            r0 = legacy_value.get("r0_reference")
            if not isinstance(production, dict) or not isinstance(r0, dict):
                raise ContractError(f"{behavior_id} does not separate R0 export metadata")
            expected_namespace = IHK_SYMBOL_NAMESPACE
            if production.get("namespace") != expected_namespace:
                raise ContractError(f"{behavior_id} has wrong production namespace")
            version_policy = str(production.get("symbol_version_policy"))
            if "R1 and R2" not in version_policy or "R0 CRC is provenance only" not in version_policy:
                raise ContractError(f"{behavior_id} has invalid symbol version policy")
        elif kind == "module_parameter":
            assert isinstance(legacy_value, dict)
            default = legacy_value.get("default")
            if not isinstance(default, dict) or not isinstance(default.get("value"), int):
                raise ContractError(f"{behavior_id} lacks an evaluated source default")
            if not isinstance(default.get("source_provenance"), dict):
                raise ContractError(f"{behavior_id} lacks default provenance")
        elif kind == "legacy_errno":
            assert isinstance(legacy_value, dict)
            required = {
                "classification",
                "column",
                "errno",
                "expression",
                "expression_sha256",
                "line",
                "site_id",
                "source",
                "source_provenance",
                "statement",
                "syntax",
            }
            if set(legacy_value) != required:
                raise ContractError(f"{behavior_id} has malformed failure-site mapping")
            if legacy_value["classification"] != "explicit_negative_errno_token":
                raise ContractError(f"{behavior_id} has unknown failure classification")
            expression = legacy_value["expression"]
            if not isinstance(expression, str) or legacy_value[
                "expression_sha256"
            ] != sha256(expression.encode()):
                raise ContractError(f"{behavior_id} has stale failure expression digest")
            if legacy_value["syntax"] not in {"direct", "parenthesized_or_cast"}:
                raise ContractError(f"{behavior_id} has unknown failure syntax")
            expected_oracle_key = sha256(str(legacy_value["site_id"]).encode())[:24]
            if behavior.get("oracle_path") != (
                f"source_errno_surface.{behavior.get('module')}.by_site_id."
                f"{expected_oracle_key}"
            ):
                raise ContractError(f"{behavior_id} has an unstable failure oracle path")

    for test in tests:
        if not isinstance(test, dict) or not isinstance(test.get("id"), str):
            raise ContractError("malformed acceptance test")
        test_id = test["id"]
        if test_id in test_by_id:
            raise ContractError(f"duplicate acceptance test id {test_id}")
        test_by_id[test_id] = test
        if not test.get("assertions") or not test.get("behavior_ids"):
            raise ContractError(f"{test_id} lacks assertions or behavior links")

    referenced_tests: set[str] = set()
    for behavior_id, behavior in behavior_by_id.items():
        for test_id in behavior["acceptance_test_ids"]:
            referenced_tests.add(test_id)
            test = test_by_id.get(test_id)
            if test is None:
                raise ContractError(f"{behavior_id} references missing test {test_id}")
            if behavior_id not in test["behavior_ids"]:
                raise ContractError(f"{test_id} does not link back to {behavior_id}")
    if referenced_tests != set(test_by_id):
        extra = sorted(set(test_by_id) - referenced_tests)
        raise ContractError(f"unreferenced acceptance tests: {extra[:5]}")

    modules = Counter(item["module"] for item in behaviors)
    if set(modules) != set(EXPECTED_MODULES):
        raise ContractError("not every production module has mapped behaviors")
    if any(modules[module] < 10 for module in EXPECTED_MODULES):
        raise ContractError(f"implausibly small behavior map: {dict(modules)}")

    mapped_errno_sites: dict[str, set[str]] = defaultdict(set)
    for behavior in behaviors:
        if behavior["kind"] == "legacy_errno":
            mapped_errno_sites[behavior["module"]].add(str(behavior["legacy"]["site_id"]))
    expected_errno = source_errno_surface(repo, legacy)
    for module, entries in expected_errno.items():
        expected = {str(entry["site_id"]) for entry in entries}
        if mapped_errno_sites[module] != expected:
            raise ContractError(
                f"errno site coverage mismatch for {module}: "
                f"mapped={len(mapped_errno_sites[module])}, expected={len(expected)}"
            )

    coverage = contract.get("coverage")
    if not isinstance(coverage, dict):
        raise ContractError("coverage summary is missing")
    if coverage.get("behavior_count") != len(behaviors) or coverage.get("test_count") != len(tests):
        raise ContractError("coverage totals are stale")
    if coverage.get("by_kind") != dict(sorted(Counter(item["kind"] for item in behaviors).items())):
        raise ContractError("coverage by_kind is stale")
    if coverage.get("by_module") != dict(sorted(modules.items())):
        raise ContractError("coverage by_module is stale")
    expected_errno_classes = {
        module: sorted({entry["errno"] for entry in entries})
        for module, entries in expected_errno.items()
    }
    expected_errno_sites = {
        module: len(entries) for module, entries in expected_errno.items()
    }
    expected_errno_syntax = {
        module: dict(sorted(Counter(entry["syntax"] for entry in entries).items()))
        for module, entries in expected_errno.items()
    }
    if coverage.get("errno_by_module") != expected_errno_classes:
        raise ContractError("coverage errno_by_module is stale")
    if coverage.get("errno_sites_by_module") != expected_errno_sites:
        raise ContractError("coverage errno_sites_by_module is stale")
    if coverage.get("errno_syntax_by_module") != expected_errno_syntax:
        raise ContractError("coverage errno_syntax_by_module is stale")


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--policy", type=Path, default=POLICY_PATH)
    parser.add_argument("--inventory", type=Path, default=INVENTORY_PATH)
    parser.add_argument("--contract", type=Path, default=CONTRACT_PATH)
    parser.add_argument(
        "--failure-capture",
        type=Path,
        help="optional compiler-backed active failure-site capture to cross-check",
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--update", action="store_true")
    mode.add_argument("--print", dest="print_contract", action="store_true")
    return parser.parse_args(argv)


def main(argv: Sequence[str]) -> int:
    args = parse_args(argv)
    repo = args.repo.resolve()
    policy_path = args.policy if args.policy.is_absolute() else repo / args.policy
    inventory_path = args.inventory if args.inventory.is_absolute() else repo / args.inventory
    contract_path = args.contract if args.contract.is_absolute() else repo / args.contract
    try:
        policy = read_json(policy_path)
        legacy = read_json(inventory_path)
        generated = build_contract(repo, policy, legacy)
        validate_contract(generated, policy, legacy, repo)
        compiler_failure_coverage = None
        if args.failure_capture is not None:
            failure_capture_path = (
                args.failure_capture
                if args.failure_capture.is_absolute()
                else repo / args.failure_capture
            )
            compiler_failure_coverage = validate_compiler_failure_capture(
                generated, read_json(failure_capture_path)
            )
        rendered = pretty(generated)
    except ContractError as exc:
        print(f"host-module contract error: {exc}", file=sys.stderr)
        return 2

    if args.print_contract:
        sys.stdout.write(rendered)
        return 0
    if args.update:
        contract_path.parent.mkdir(parents=True, exist_ok=True)
        contract_path.write_text(rendered, encoding="utf-8")
        print(
            f"updated {contract_path}: {generated['coverage']['behavior_count']} behaviors, "
            f"{generated['coverage']['test_count']} acceptance tests"
        )
        return 0
    try:
        existing = read_json(contract_path)
        validate_contract(existing, policy, legacy, repo)
    except ContractError as exc:
        print(f"host-module contract error: {exc}", file=sys.stderr)
        return 2
    existing_rendered = pretty(existing)
    if existing_rendered != rendered:
        print("host-module behavior contract is stale", file=sys.stderr)
        for index, line in enumerate(
            difflib.unified_diff(
                existing_rendered.splitlines(),
                rendered.splitlines(),
                fromfile=str(contract_path),
                tofile=f"{contract_path} (regenerated)",
                n=3,
            )
        ):
            if index >= 300:
                print("... diff truncated ...", file=sys.stderr)
                break
            print(line, file=sys.stderr)
        return 1
    compiler_suffix = (
        ""
        if compiler_failure_coverage is None
        else f", compiler_active_failure_sites={sum(compiler_failure_coverage.values())}"
    )
    print(
        f"host-module policy and behavior contract verified: "
        f"{generated['coverage']['behavior_count']} behaviors, "
        f"{generated['coverage']['test_count']} acceptance tests, "
        f"policy_sha256={generated['policy_file_sha256']}{compiler_suffix}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
