#!/usr/bin/env python3
"""Generate and verify the frozen Linux API-needs manifest for host modules.

RS-001 starts from two independently reproducible legacy surfaces:

* undefined symbols in the three frozen ``.ko`` artifacts, excluding imports
  that the frozen IHK provider satisfies; and
* literal ``kallsyms_lookup_name()`` requests in the frozen active x86_64
  source inputs.

This checkpoint deliberately does not turn a Rocky 8.10 observation into a
Rocky 10.2 compatibility claim.  Each need records what the frozen evidence
proves and the export, configuration, and call-context work still required for
the native Rust-for-Linux implementation.
"""

from __future__ import annotations

import argparse
import copy
import difflib
import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable, Sequence

import host_module_inventory as inventory_tool


INVENTORY_PATH = Path("host-kernel/reference/legacy-host-modules-f2eb7352.json")
SOURCE_LOCK_PATH = Path("host-kernel/rocky/source-lock.json")
OUTPUT_PATH = Path("host-kernel/contracts/linux-api-needs-v1.json")

MANIFEST_ID = "mckernel-native-rust-linux-api-needs-v1"
EXPECTED_MODULES = ("ihk", "ihk_smp_x86_64", "mcctrl")
EXPECTED_FILENAMES = {
    "ihk": "ihk.ko",
    "ihk_smp_x86_64": "ihk-smp-x86_64.ko",
    "mcctrl": "mcctrl.ko",
}
FROZEN_SOURCE_CAPTURE_SHA256 = (
    "953351a177f6c0c402befd76061ecefd9aa7161856b66076f64da0bfe2568ce9"
)
LOOKUP_KINDS = ("module_import", "dynamic_kallsyms")

CONTEXT_CLASSES = (
    "process",
    "atomic",
    "irq",
    "nmi",
    "early_boot",
    "module_lifecycle",
)

ABSTRACTION_RULES = (
    (
        "memory_management",
        re.compile(
            r"(?:alloc|free|page|pte|pmd|pgd|vma|vmap|vmalloc|mmap|mm_|"
            r"mem|slab|cache|zone|node|phys|virt|ioremap|unmap|hstate|huge)"
        ),
    ),
    (
        "synchronization",
        re.compile(
            r"(?:lock|mutex|spin|rwsem|semaphore|wait|wake|completion|atomic|"
            r"rcu|barrier|srcu)"
        ),
    ),
    (
        "scheduler_and_task",
        re.compile(
            r"(?:sched|task|thread|pid|cpu|preempt|affinity|current|signal|"
            r"cred|namespace|unshare)"
        ),
    ),
    (
        "interrupt_timer_and_time",
        re.compile(r"(?:irq|ipi|apic|timer|clock|time|jiff|tsc|hpet|delay)"),
    ),
    (
        "device_module_and_sysfs",
        re.compile(
            r"(?:device|driver|module|kobject|kset|class|cdev|sysfs|proc|"
            r"debugfs|uevent|notifier|bus_)"
        ),
    ),
    (
        "filesystem_and_vfs",
        re.compile(
            r"(?:file|inode|dentry|path|mount|umount|read|write|llseek|"
            r"fs_|kern_|vfs_|binfmt|fd_)"
        ),
    ),
    (
        "user_access_and_string",
        re.compile(
            r"(?:user|copy|str|memcpy|memset|bitmap|parse|printf|scnprintf)"
        ),
    ),
    (
        "logging_diagnostics_and_security",
        re.compile(
            r"(?:printk|warn|bug|panic|trace|stack|capable|security|audit|"
            r"random|fortify|check_object)"
        ),
    ),
    (
        "x86_platform",
        re.compile(
            r"(?:x86|real_mode|vector|desc|pgt|pmu|perfmon|uv_|lapic|msr)"
        ),
    ),
)


class ApiNeedsError(RuntimeError):
    """Raised when the API-needs evidence or manifest is incomplete."""


def canonical_bytes(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()


def pretty(value: object) -> str:
    return json.dumps(value, indent=2, sort_keys=True) + "\n"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ApiNeedsError(f"cannot parse {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ApiNeedsError(f"{path} must contain a JSON object")
    return value


def stable_id(kind: str, symbol: str) -> str:
    prefix = "IMPORT" if kind == "module_import" else "KALLSYMS"
    slug = re.sub(r"[^A-Za-z0-9]+", "_", symbol).strip("_").upper()
    suffix = sha256_bytes(f"{kind}\0{symbol}".encode())[:10].upper()
    return f"LAPI-{prefix}-{slug[:48]}-{suffix}"


def acceptance_id(kind: str, symbol: str) -> str:
    return "AT-" + stable_id(kind, symbol).removeprefix("LAPI-")


def abstraction_for(symbol: str) -> dict[str, str]:
    lowered = symbol.lower()
    for family, pattern in ABSTRACTION_RULES:
        if pattern.search(lowered):
            return {
                "family": family,
                "classification_basis": "deterministic symbol-name family; review required",
            }
    return {
        "family": "generic_kernel_runtime",
        "classification_basis": "deterministic fallback; review required",
    }


def require_dict(value: object, description: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ApiNeedsError(f"{description} must be an object")
    return value


def require_list(value: object, description: str) -> list[Any]:
    if not isinstance(value, list):
        raise ApiNeedsError(f"{description} must be a list")
    return value


def validate_inventory(inventory: dict[str, Any]) -> None:
    """Validate every frozen input used by this derivative manifest."""

    if inventory.get("schema_version") != 1:
        raise ApiNeedsError("legacy inventory schema_version must be 1")
    if inventory.get("profile") != inventory_tool.PROFILE:
        raise ApiNeedsError("legacy inventory profile is not the frozen R0 profile")
    if inventory.get("module_order") != list(EXPECTED_MODULES):
        raise ApiNeedsError("legacy inventory module order changed")

    provenance = require_dict(inventory.get("provenance"), "inventory provenance")
    expected_provenance = {
        "parent_commit": inventory_tool.PARENT_REF,
        "ihk_commit": inventory_tool.IHK_REF,
        "workflow_run": inventory_tool.WORKFLOW_RUN,
        "artifact_id": inventory_tool.ARTIFACT_ID,
        "artifact_digest": inventory_tool.ARTIFACT_DIGEST,
        "architecture": "x86_64",
    }
    for key, expected in expected_provenance.items():
        if provenance.get(key) != expected:
            raise ApiNeedsError(f"inventory provenance {key} changed")

    binary = require_dict(inventory.get("binary_capture"), "binary capture")
    try:
        binary_digest = inventory_tool.validate_locked_binary_capture(binary)
    except inventory_tool.InventoryError as exc:
        raise ApiNeedsError(str(exc)) from exc
    if inventory.get("binary_capture_sha256") != binary_digest:
        raise ApiNeedsError("binary_capture_sha256 does not match locked capture")

    source = require_dict(inventory.get("source_capture"), "source capture")
    source_digest = sha256_bytes(inventory_tool.canonical_json(source))
    if inventory.get("source_capture_sha256") != source_digest:
        raise ApiNeedsError("source_capture_sha256 does not match source capture")
    if source_digest != FROZEN_SOURCE_CAPTURE_SHA256:
        raise ApiNeedsError("source capture is not the locked frozen x86_64 input set")

    binary_modules = require_dict(binary.get("modules"), "binary modules")
    source_modules = require_dict(source.get("modules"), "source modules")
    if tuple(binary_modules) != EXPECTED_MODULES or tuple(source_modules) != EXPECTED_MODULES:
        raise ApiNeedsError("inventory must contain exactly the three ordered modules")

    for module in EXPECTED_MODULES:
        binary_entry = require_dict(binary_modules[module], f"binary module {module}")
        if binary_entry.get("filename") != EXPECTED_FILENAMES[module]:
            raise ApiNeedsError(f"unexpected filename for {module}")
        expected_sha = inventory_tool.EXPECTED_MODULE_SHA256[module]
        if binary_entry.get("sha256") != expected_sha:
            raise ApiNeedsError(f"unexpected frozen module digest for {module}")

        imports = require_list(binary_entry.get("imports"), f"{module} imports")
        if imports != sorted(set(imports)) or not all(isinstance(x, str) for x in imports):
            raise ApiNeedsError(f"{module} imports must be unique sorted strings")
        inter = require_list(
            binary_entry.get("inter_module_imports"), f"{module} inter-module imports"
        )
        exported_by_module = {
            provider: {
                row.get("name")
                for row in require_list(
                    binary_modules[provider].get("exports"), f"{provider} exports"
                )
                if isinstance(row, dict) and isinstance(row.get("name"), str)
            }
            for provider in EXPECTED_MODULES
        }
        seen_inter: set[str] = set()
        for edge in inter:
            edge = require_dict(edge, f"{module} inter-module edge")
            if set(edge) != {"provider", "symbol"}:
                raise ApiNeedsError(f"malformed inter-module edge for {module}")
            if edge["provider"] not in EXPECTED_MODULES or edge["provider"] == module:
                raise ApiNeedsError(f"invalid inter-module provider for {module}")
            if edge["symbol"] not in imports or edge["symbol"] in seen_inter:
                raise ApiNeedsError(f"invalid duplicate/inter-module import for {module}")
            if edge["symbol"] not in exported_by_module[edge["provider"]]:
                raise ApiNeedsError(f"inter-module provider does not export symbol for {module}")
            seen_inter.add(edge["symbol"])
        expected_inter = {
            symbol
            for symbol in imports
            if any(
                symbol in exported_by_module[provider]
                for provider in EXPECTED_MODULES
                if provider != module
            )
        }
        if seen_inter != expected_inter:
            raise ApiNeedsError(f"inter-module exclusion set is incomplete for {module}")

        source_entry = require_dict(source_modules[module], f"source module {module}")
        active_inputs = require_list(source_entry.get("active_inputs"), "active inputs")
        active_sources = {
            row.get("source")
            for row in active_inputs
            if isinstance(row, dict) and isinstance(row.get("source"), str)
        }
        lookups = require_list(
            source_entry.get("dynamic_kallsyms_lookups"), f"{module} lookups"
        )
        prior: tuple[str, str, int] | None = None
        for site in lookups:
            site = require_dict(site, f"{module} kallsyms site")
            if set(site) != {"symbol", "source", "line"}:
                raise ApiNeedsError(f"malformed kallsyms site for {module}")
            if not isinstance(site["symbol"], str) or not site["symbol"]:
                raise ApiNeedsError(f"invalid kallsyms symbol for {module}")
            if site["source"] not in active_sources:
                raise ApiNeedsError(f"kallsyms site is outside active inputs for {module}")
            if not isinstance(site["line"], int) or site["line"] < 1:
                raise ApiNeedsError(f"invalid kallsyms line for {module}")
            key = (site["symbol"], site["source"], site["line"])
            if prior is not None and key <= prior:
                raise ApiNeedsError(f"{module} kallsyms sites are not unique and sorted")
            prior = key


def verify_inventory_replay(repo: Path, inventory: dict[str, Any]) -> None:
    """Regenerate the frozen source capture and compare it byte-for-byte."""

    binary = require_dict(inventory.get("binary_capture"), "binary capture")
    try:
        replay = inventory_tool.build_inventory(repo, None, copy.deepcopy(binary))
    except inventory_tool.InventoryError as exc:
        raise ApiNeedsError(f"cannot replay frozen inventory: {exc}") from exc
    if replay != inventory:
        raise ApiNeedsError("frozen inventory replay differs from the checked-in golden")


def validate_source_lock(source_lock: dict[str, Any]) -> None:
    if source_lock.get("schema_version") != 1:
        raise ApiNeedsError("Rocky source lock schema_version must be 1")
    target = require_dict(source_lock.get("target"), "source-lock target")
    if target.get("distribution") != "Rocky Linux" or target.get("release") != "10.2":
        raise ApiNeedsError("API needs must target Rocky Linux 10.2")
    if target.get("architecture") != "x86_64":
        raise ApiNeedsError("API needs must target x86_64")
    srpm = require_dict(source_lock.get("source_rpm"), "source RPM")
    for key in ("nvr", "sha256", "size", "filename"):
        if not srpm.get(key):
            raise ApiNeedsError(f"source RPM {key} is missing")


def linux_import_edges(inventory: dict[str, Any]) -> dict[str, list[str]]:
    modules = inventory["binary_capture"]["modules"]
    edges: dict[str, list[str]] = {}
    for module in EXPECTED_MODULES:
        entry = modules[module]
        inter_symbols = {row["symbol"] for row in entry["inter_module_imports"]}
        edges[module] = sorted(symbol for symbol in entry["imports"] if symbol not in inter_symbols)
    return edges


def dynamic_lookup_sites(
    inventory: dict[str, Any],
) -> dict[str, dict[str, list[dict[str, Any]]]]:
    result: dict[str, dict[str, list[dict[str, Any]]]] = {}
    modules = inventory["source_capture"]["modules"]
    for module in EXPECTED_MODULES:
        by_symbol: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for site in modules[module]["dynamic_kallsyms_lookups"]:
            by_symbol[site["symbol"]].append(
                {"source": site["source"], "line": site["line"]}
            )
        result[module] = {
            symbol: sorted(sites, key=lambda row: (row["source"], row["line"]))
            for symbol, sites in sorted(by_symbol.items())
        }
    return result


def active_input_index(inventory: dict[str, Any]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for details in inventory["source_capture"]["modules"].values():
        for row in details["active_inputs"]:
            result[row["source"]] = row
    return result


def audited_kallsyms_surface(
    repo: Path, inventory: dict[str, Any]
) -> dict[str, Any]:
    """Prove literal coverage and resolve the one bounded computed-name bridge."""

    literal_pattern = re.compile(
        r'\bkallsyms_lookup_name\s*\(\s*(?P<arg>"[^"\\]*(?:\\.[^"\\]*)*"|[A-Za-z_]\w*)\s*\)'
    )
    literal_sites: list[dict[str, Any]] = []
    computed_sites: list[dict[str, Any]] = []
    source_modules = inventory["source_capture"]["modules"]
    for module in EXPECTED_MODULES:
        for entry in source_modules[module]["active_inputs"]:
            if entry["language"] != "c":
                continue
            text = inventory_tool.strip_c_comments(
                inventory_tool.text_blob(repo, entry["source"])
            )
            for match in literal_pattern.finditer(text):
                argument = match.group("arg")
                row = {
                    "module": module,
                    "source": entry["source"],
                    "line": inventory_tool.line_number(text, match.start()),
                }
                if argument.startswith('"'):
                    row["symbol"] = json.loads(argument)
                    literal_sites.append(row)
                else:
                    row["argument"] = argument
                    computed_sites.append(row)

    expected_literals = sorted(
        (
            {
                "module": module,
                "source": site["source"],
                "line": site["line"],
                "symbol": site["symbol"],
            }
            for module in EXPECTED_MODULES
            for site in source_modules[module]["dynamic_kallsyms_lookups"]
        ),
        key=lambda row: (
            EXPECTED_MODULES.index(row["module"]),
            row["symbol"],
            row["source"],
            row["line"],
        ),
    )
    actual_literals = sorted(
        literal_sites,
        key=lambda row: (
            EXPECTED_MODULES.index(row["module"]),
            row["symbol"],
            row["source"],
            row["line"],
        ),
    )
    if actual_literals != expected_literals:
        raise ApiNeedsError("literal kallsyms audit does not match frozen source capture")

    expected_dispatcher = {
        "module": "mcctrl",
        "source": "executer/kernel/mcctrl/driver.c",
        "line": 1217,
        "argument": "name",
    }
    if computed_sites != [expected_dispatcher]:
        raise ApiNeedsError(
            "unresolved or changed non-literal kallsyms call surface: "
            + json.dumps(computed_sites, sort_keys=True)
        )

    rust_path = "executer/kernel/mcctrl/rust/mcctrl_helpers.rs"
    rust_entry = active_input_index(inventory).get(rust_path)
    if not rust_entry or rust_entry.get("language") != "rust":
        raise ApiNeedsError("bounded kallsyms bridge caller is not a frozen Rust input")
    rust_text = inventory_tool.text_blob(repo, rust_path)
    constant_pattern = re.compile(
        r'\bconst\s+([A-Z][A-Z0-9_]*)\s*:\s*&\[u8\]\s*=\s*b"([^"\\]*(?:\\.[^"\\]*)*)"\s*;'
    )
    constants = {
        match.group(1): bytes(match.group(2), "utf-8").decode("unicode_escape")
        for match in constant_pattern.finditer(rust_text)
    }
    bridge_name = "mcctrl_arch_kallsyms_lookup_bridge"
    call_pattern = re.compile(
        rf"\b{bridge_name}\s*\(\s*([A-Z][A-Z0-9_]*)\.as_ptr\s*\(\s*\)"
    )
    forwarded: list[dict[str, Any]] = []
    recognized_offsets: set[int] = set()
    for match in call_pattern.finditer(rust_text):
        constant = match.group(1)
        value = constants.get(constant)
        if value is None or not value.endswith("\0") or "\0" in value[:-1]:
            raise ApiNeedsError(f"kallsyms bridge constant {constant} is not a C string")
        symbol = value[:-1]
        also_literal = any(
            row["module"] == "mcctrl" and row["symbol"] == symbol
            for row in literal_sites
        )
        forwarded.append(
            {
                "module": "mcctrl",
                "symbol": symbol,
                "source": rust_path,
                "line": inventory_tool.line_number(rust_text, match.start()),
                "constant": constant,
                "base_sha256": rust_entry["base_sha256"],
                "effective_input_sha256": rust_entry["effective_input_sha256"],
                "also_present_as_literal_c_lookup": also_literal,
                "dispatcher_source": expected_dispatcher["source"],
                "dispatcher_line": expected_dispatcher["line"],
            }
        )
        recognized_offsets.add(match.start())

    all_bridge_tokens = list(re.finditer(rf"\b{bridge_name}\s*\(", rust_text))
    declarations = [
        match
        for match in all_bridge_tokens
        if re.search(r"\bfn\s+$", rust_text[max(0, match.start() - 12) : match.start()])
    ]
    if len(declarations) != 1 or len(all_bridge_tokens) != len(forwarded) + 1:
        raise ApiNeedsError("not every Rust kallsyms bridge use has a static source name")
    if len(forwarded) != len(recognized_offsets):
        raise ApiNeedsError("duplicate Rust kallsyms bridge call offsets")

    forwarded.sort(key=lambda row: (row["symbol"], row["source"], row["line"]))
    dispatcher_input = active_input_index(inventory).get(expected_dispatcher["source"])
    if not dispatcher_input:
        raise ApiNeedsError("bounded kallsyms dispatcher is not an active input")
    dispatcher = dict(expected_dispatcher)
    dispatcher.update(
        {
            "function": bridge_name,
            "base_sha256": dispatcher_input["base_sha256"],
            "effective_input_sha256": dispatcher_input["effective_input_sha256"],
            "resolved_static_callers": len(forwarded),
            "unresolved_callers": 0,
        }
    )
    return {
        "literal_site_count": len(literal_sites),
        "non_literal_dispatchers": [dispatcher],
        "forwarded_static_names": forwarded,
        "unresolved_computed_names": [],
    }


def input_surface(
    inventory: dict[str, Any], kallsyms_audit: dict[str, Any]
) -> dict[str, Any]:
    imports = linux_import_edges(inventory)
    lookups = dynamic_lookup_sites(inventory)
    return {
        "module_imports": [
            {"module": module, "symbols": imports[module]} for module in EXPECTED_MODULES
        ],
        "dynamic_kallsyms": [
            {
                "module": module,
                "symbols": [
                    {"symbol": symbol, "sites": sites}
                    for symbol, sites in lookups[module].items()
                ],
            }
            for module in EXPECTED_MODULES
        ],
        "kallsyms_non_literal_audit": kallsyms_audit,
    }


def consumer_artifact(
    module: str, inventory: dict[str, Any], imported: bool
) -> dict[str, Any]:
    artifact = inventory["binary_capture"]["modules"][module]
    return {
        "module": module,
        "filename": artifact["filename"],
        "artifact_path": artifact["artifact_path"],
        "module_sha256": artifact["sha256"],
        "evidence": (
            "undefined ELF symbol in frozen module"
            if imported
            else "literal lookup in frozen active source"
        ),
    }


def build_need(
    kind: str,
    symbol: str,
    modules: Iterable[str],
    inventory: dict[str, Any],
    lookup_sites: dict[str, list[dict[str, Any]]] | None = None,
    forwarded_sites: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    module_list = sorted(set(modules), key=EXPECTED_MODULES.index)
    imported = kind == "module_import"
    dynamic_lookup_api = symbol == "kallsyms_lookup_name"
    need: dict[str, Any] = {
        "id": stable_id(kind, symbol),
        "symbol": symbol,
        "lookup_kind": kind,
        "owner": {
            "provider": "Linux kernel core",
            "consuming_modules": module_list,
        },
        "consumers": [
            consumer_artifact(module, inventory, imported) for module in module_list
        ],
        "availability": {
            "legacy_r0": (
                "present as an undefined import in a frozen built module"
                if imported
                else "requested by a literal lookup in frozen active source"
            ),
            "rocky_10_2": "unverified",
            "production_disposition": (
                "forbidden_dynamic_lookup_substrate_must_be_retired"
                if dynamic_lookup_api
                else "blocked_pending_target_probe"
            ),
        },
        "export": {
            "legacy_dependency": (
                "module-visible exported symbol"
                if imported
                else "runtime kallsyms access to a private or non-imported symbol"
            ),
            "rocky_10_2_status": "unverified",
            "native_rust_requirement": (
                "do not bind in production; eliminate every dynamic lookup dependency"
                if dynamic_lookup_api
                else "direct Rust-for-Linux binding or reviewed wrapper"
                if imported
                else "replace lookup with a stable exported API or a reviewed local abstraction"
            ),
        },
        "configuration": {
            "rocky_10_2_requirements": [],
            "status": "requires_selected_config_probe",
        },
        "call_context": {
            "allowed_classes": list(CONTEXT_CLASSES),
            "resolved_classes": [],
            "status": "requires_compiler_backed_call_site_audit",
        },
        "abstraction": abstraction_for(symbol),
        "acceptance": {
            "test_id": acceptance_id(kind, symbol),
            "required_evidence": [
                "selected Rocky 10.2 source/config provider or absence probe",
                "Rust-for-Linux build with no undeclared symbol lookup",
                "call-context and safety justification for every consumer",
            ],
            "status": "planned",
        },
    }
    if imported:
        need["source_provenance"] = {
            "inventory_path": str(INVENTORY_PATH),
            "binary_capture_sha256": inventory["binary_capture_sha256"],
            "artifact_workflow_run": inventory["provenance"]["workflow_run"],
            "artifact_id": inventory["provenance"]["artifact_id"],
            "consumer_edge_count": len(module_list),
        }
    else:
        if lookup_sites is None:
            raise ApiNeedsError(f"dynamic lookup {symbol} has no source sites")
        source_rows = []
        active_by_path: dict[str, dict[str, Any]] = {}
        for module in module_list:
            for row in inventory["source_capture"]["modules"][module]["active_inputs"]:
                active_by_path[row["source"]] = row
        for module in module_list:
            for site in lookup_sites[module]:
                active = active_by_path[site["source"]]
                source_rows.append(
                    {
                        "module": module,
                        "source": site["source"],
                        "line": site["line"],
                        "base_sha256": active["base_sha256"],
                        "effective_input_sha256": active["effective_input_sha256"],
                    }
                )
        need["source_provenance"] = {
            "inventory_path": str(INVENTORY_PATH),
            "source_capture_sha256": inventory["source_capture_sha256"],
            "sites": sorted(
                source_rows,
                key=lambda row: (
                    EXPECTED_MODULES.index(row["module"]),
                    row["source"],
                    row["line"],
                ),
            ),
            "site_count": len(source_rows),
            "forwarded_static_sites": sorted(
                forwarded_sites or [],
                key=lambda row: (row["source"], row["line"], row["constant"]),
            ),
            "forwarded_static_site_count": len(forwarded_sites or []),
        }
    return need


def build_needs(
    inventory: dict[str, Any], kallsyms_audit: dict[str, Any]
) -> list[dict[str, Any]]:
    imports = linux_import_edges(inventory)
    import_consumers: dict[str, list[str]] = defaultdict(list)
    for module in EXPECTED_MODULES:
        for symbol in imports[module]:
            import_consumers[symbol].append(module)

    lookup_map = dynamic_lookup_sites(inventory)
    lookup_consumers: dict[str, dict[str, list[dict[str, Any]]]] = defaultdict(dict)
    for module in EXPECTED_MODULES:
        for symbol, sites in lookup_map[module].items():
            lookup_consumers[symbol][module] = sites
    forwarded_by_symbol: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in kallsyms_audit["forwarded_static_names"]:
        forwarded_by_symbol[row["symbol"]].append(row)
        lookup_consumers.setdefault(row["symbol"], {}).setdefault(row["module"], [])

    overlap = set(import_consumers) & set(lookup_consumers)
    if overlap:
        raise ApiNeedsError(
            "symbols occur in both import and kallsyms surfaces: " + ", ".join(sorted(overlap))
        )

    needs = [
        build_need("module_import", symbol, modules, inventory)
        for symbol, modules in sorted(import_consumers.items())
    ]
    needs.extend(
        build_need(
            "dynamic_kallsyms",
            symbol,
            sites_by_module,
            inventory,
            sites_by_module,
            forwarded_by_symbol.get(symbol, []),
        )
        for symbol, sites_by_module in sorted(lookup_consumers.items())
    )
    return sorted(needs, key=lambda row: (LOOKUP_KINDS.index(row["lookup_kind"]), row["symbol"]))


def coverage_for(
    needs: list[dict[str, Any]], kallsyms_audit: dict[str, Any]
) -> dict[str, Any]:
    by_kind = Counter(row["lookup_kind"] for row in needs)
    owner_edges = Counter()
    unique_by_module = Counter()
    for row in needs:
        for module in row["owner"]["consuming_modules"]:
            unique_by_module[module] += 1
            owner_edges[(module, row["lookup_kind"])] += 1
    dynamic_sites = sum(
        row["source_provenance"].get("site_count", 0)
        for row in needs
        if row["lookup_kind"] == "dynamic_kallsyms"
    )
    import_edges = sum(
        row["source_provenance"].get("consumer_edge_count", 0)
        for row in needs
        if row["lookup_kind"] == "module_import"
    )
    return {
        "need_count": len(needs),
        "by_lookup_kind": {kind: by_kind[kind] for kind in LOOKUP_KINDS},
        "consumer_edges": {
            "module_import": import_edges,
            "dynamic_kallsyms": sum(
                owner_edges[(module, "dynamic_kallsyms")] for module in EXPECTED_MODULES
            ),
        },
        "dynamic_kallsyms_source_sites": dynamic_sites,
        "kallsyms_non_literal_dispatchers": len(
            kallsyms_audit["non_literal_dispatchers"]
        ),
        "kallsyms_forwarded_static_name_sites": len(
            kallsyms_audit["forwarded_static_names"]
        ),
        "kallsyms_unresolved_computed_name_sites": len(
            kallsyms_audit["unresolved_computed_names"]
        ),
        "unique_needs_by_module": {
            module: unique_by_module[module] for module in EXPECTED_MODULES
        },
        "by_module_and_kind": {
            module: {
                kind: owner_edges[(module, kind)] for kind in LOOKUP_KINDS
            }
            for module in EXPECTED_MODULES
        },
    }


def manifest_digest(manifest: dict[str, Any]) -> str:
    unsigned = copy.deepcopy(manifest)
    unsigned.pop("manifest_sha256", None)
    return sha256_bytes(canonical_bytes(unsigned))


def build_manifest(
    inventory: dict[str, Any], source_lock: dict[str, Any], repo: Path | None = None
) -> dict[str, Any]:
    validate_inventory(inventory)
    validate_source_lock(source_lock)
    if repo is None:
        repo = Path(__file__).resolve().parents[1]
    kallsyms_audit = audited_kallsyms_surface(repo.resolve(), inventory)
    needs = build_needs(inventory, kallsyms_audit)
    surface = input_surface(inventory, kallsyms_audit)
    source_rpm = source_lock["source_rpm"]
    manifest: dict[str, Any] = {
        "schema_version": 1,
        "manifest_id": MANIFEST_ID,
        "architecture": "x86_64",
        "generator": "scripts/linux_api_needs.py",
        "scope": {
            "modules": list(EXPECTED_MODULES),
            "included": [
                "unique undefined Linux-kernel imports from the frozen module artifacts",
                "unique literal kallsyms_lookup_name requests from frozen active x86_64 sources",
                "source-proven static names forwarded through the bounded Rust-to-C kallsyms bridge",
            ],
            "excluded": [
                "imports provided by another one of the three project modules",
                "arm64-only and inactive sources",
                "unbounded runtime-computed lookup names (none are accepted by this manifest)",
            ],
        },
        "target": {
            "distribution": "Rocky Linux",
            "release": "10.2",
            "kernel_source_lock": str(SOURCE_LOCK_PATH),
            "kernel_nvr": source_rpm["nvr"],
            "source_rpm_sha256": source_rpm["sha256"],
        },
        "provenance": {
            "legacy_inventory_path": str(INVENTORY_PATH),
            "legacy_profile": inventory["profile"],
            "parent_commit": inventory["provenance"]["parent_commit"],
            "ihk_commit": inventory["provenance"]["ihk_commit"],
            "artifact": {
                "workflow_run": inventory["provenance"]["workflow_run"],
                "artifact_id": inventory["provenance"]["artifact_id"],
                "artifact_digest": inventory["provenance"]["artifact_digest"],
                "binary_capture_sha256": inventory["binary_capture_sha256"],
            },
            "source_capture_sha256": inventory["source_capture_sha256"],
            "input_surface_sha256": sha256_bytes(canonical_bytes(surface)),
            "source_lock_sha256": sha256_bytes(canonical_bytes(source_lock)),
        },
        "classification_policy": {
            "owner": "Linux kernel core for every included need; project-module imports are excluded",
            "availability": "R0 evidence is provenance only; Rocky 10.2 remains unverified until probed",
            "export": "ordinary imports need an exported binding; kallsyms dependencies must be retired",
            "configuration": "derive exact Kconfig requirements from the selected Rocky source/config",
            "call_context": {
                "controlled_vocabulary": list(CONTEXT_CLASSES),
                "policy": "resolve every consumer through a compiler-backed call-site audit",
            },
            "abstraction": "symbol-name families are routing hints, never target-availability claims",
        },
        "needs": needs,
        "kallsyms_exhaustiveness_audit": kallsyms_audit,
        "coverage": coverage_for(needs, kallsyms_audit),
        "readiness": {
            "gate": "RS-001",
            "credit_eligible": False,
            "blockers": [
                "probe every symbol against the selected Rocky 10.2 source, config, and exports",
                "resolve exact Kconfig requirements for every available provider",
                "complete compiler-backed call-site and process/atomic/IRQ/NMI context classification",
                "replace every private kallsyms dependency with a stable exported API or reviewed abstraction",
                "implement and pass the per-need Rust build and behavioral acceptance evidence",
            ],
        },
    }
    manifest["manifest_sha256"] = manifest_digest(manifest)
    return manifest


def validate_need_shape(need: dict[str, Any]) -> None:
    required = {
        "id",
        "symbol",
        "lookup_kind",
        "owner",
        "consumers",
        "availability",
        "export",
        "configuration",
        "call_context",
        "abstraction",
        "acceptance",
        "source_provenance",
    }
    if set(need) != required:
        raise ApiNeedsError(f"need {need.get('id')} has unexpected fields")
    kind = need.get("lookup_kind")
    symbol = need.get("symbol")
    if kind not in LOOKUP_KINDS or not isinstance(symbol, str) or not symbol:
        raise ApiNeedsError("need has invalid lookup kind or symbol")
    if need.get("id") != stable_id(kind, symbol):
        raise ApiNeedsError(f"need id is not stable for {symbol}")
    owner = require_dict(need.get("owner"), f"owner for {symbol}")
    if owner.get("provider") != "Linux kernel core":
        raise ApiNeedsError(f"need owner changed for {symbol}")
    modules = owner.get("consuming_modules")
    if not isinstance(modules, list) or not modules:
        raise ApiNeedsError(f"need has no consumers for {symbol}")
    if modules != sorted(set(modules), key=EXPECTED_MODULES.index):
        raise ApiNeedsError(f"need consumers are invalid for {symbol}")
    consumers = require_list(need.get("consumers"), f"consumers for {symbol}")
    if [row.get("module") for row in consumers if isinstance(row, dict)] != modules:
        raise ApiNeedsError(f"artifact consumers diverge for {symbol}")

    availability = require_dict(need.get("availability"), f"availability for {symbol}")
    if availability.get("rocky_10_2") != "unverified":
        raise ApiNeedsError(f"checkpoint overclaims Rocky availability for {symbol}")
    export = require_dict(need.get("export"), f"export for {symbol}")
    if export.get("rocky_10_2_status") != "unverified":
        raise ApiNeedsError(f"checkpoint overclaims Rocky export status for {symbol}")
    configuration = require_dict(
        need.get("configuration"), f"configuration for {symbol}"
    )
    if configuration.get("status") != "requires_selected_config_probe":
        raise ApiNeedsError(f"checkpoint overclaims configuration closure for {symbol}")
    call_context = require_dict(need.get("call_context"), f"context for {symbol}")
    if call_context.get("status") != "requires_compiler_backed_call_site_audit":
        raise ApiNeedsError(f"checkpoint overclaims call-context closure for {symbol}")
    if call_context.get("allowed_classes") != list(CONTEXT_CLASSES):
        raise ApiNeedsError(f"call-context vocabulary changed for {symbol}")
    abstraction = require_dict(need.get("abstraction"), f"abstraction for {symbol}")
    if abstraction != abstraction_for(symbol):
        raise ApiNeedsError(f"abstraction classification is stale for {symbol}")
    acceptance = require_dict(need.get("acceptance"), f"acceptance for {symbol}")
    if acceptance.get("test_id") != acceptance_id(kind, symbol):
        raise ApiNeedsError(f"acceptance id is not stable for {symbol}")
    if acceptance.get("status") != "planned":
        raise ApiNeedsError(f"checkpoint overclaims acceptance for {symbol}")


def validate_manifest(
    manifest: dict[str, Any],
    inventory: dict[str, Any],
    source_lock: dict[str, Any],
    repo: Path | None = None,
) -> None:
    validate_inventory(inventory)
    validate_source_lock(source_lock)
    if manifest.get("schema_version") != 1 or manifest.get("manifest_id") != MANIFEST_ID:
        raise ApiNeedsError("unexpected API-needs manifest identity")
    if manifest.get("manifest_sha256") != manifest_digest(manifest):
        raise ApiNeedsError("manifest_sha256 does not match manifest content")
    needs = require_list(manifest.get("needs"), "manifest needs")
    prior: tuple[int, str] | None = None
    ids: set[str] = set()
    test_ids: set[str] = set()
    for value in needs:
        need = require_dict(value, "need")
        validate_need_shape(need)
        key = (LOOKUP_KINDS.index(need["lookup_kind"]), need["symbol"])
        if prior is not None and key <= prior:
            raise ApiNeedsError("needs must be unique and sorted")
        prior = key
        if need["id"] in ids or need["acceptance"]["test_id"] in test_ids:
            raise ApiNeedsError("need or acceptance id is duplicated")
        ids.add(need["id"])
        test_ids.add(need["acceptance"]["test_id"])

    expected = build_manifest(inventory, source_lock, repo)
    if manifest != expected:
        raise ApiNeedsError("API-needs manifest does not exactly cover frozen inputs")

    kallsyms_audit = require_dict(
        manifest.get("kallsyms_exhaustiveness_audit"), "kallsyms audit"
    )
    if kallsyms_audit.get("unresolved_computed_names") != []:
        raise ApiNeedsError("computed kallsyms names remain unresolved")
    if manifest.get("coverage") != coverage_for(needs, kallsyms_audit):
        raise ApiNeedsError("coverage counts do not match needs")
    readiness = require_dict(manifest.get("readiness"), "readiness")
    if readiness.get("credit_eligible") is not False or len(readiness.get("blockers", [])) < 5:
        raise ApiNeedsError("RS-001 must remain blocked at this evidence checkpoint")


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--inventory", type=Path, default=INVENTORY_PATH)
    parser.add_argument("--source-lock", type=Path, default=SOURCE_LOCK_PATH)
    parser.add_argument("--output", type=Path, default=OUTPUT_PATH)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--update", action="store_true")
    mode.add_argument("--print", dest="print_manifest", action="store_true")
    return parser.parse_args(argv)


def resolve(repo: Path, path: Path) -> Path:
    return path if path.is_absolute() else repo / path


def main(argv: Sequence[str]) -> int:
    args = parse_args(argv)
    repo = args.repo.resolve()
    inventory_path = resolve(repo, args.inventory)
    source_lock_path = resolve(repo, args.source_lock)
    output_path = resolve(repo, args.output)
    try:
        inventory = read_json(inventory_path)
        source_lock = read_json(source_lock_path)
        verify_inventory_replay(repo, inventory)
        generated = build_manifest(inventory, source_lock, repo)
        validate_manifest(generated, inventory, source_lock, repo)
    except ApiNeedsError as exc:
        print(f"linux API-needs error: {exc}", file=sys.stderr)
        return 2

    rendered = pretty(generated)
    if args.print_manifest:
        sys.stdout.write(rendered)
        return 0
    if args.update:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(rendered, encoding="utf-8")
        print(
            f"updated {output_path}: {generated['coverage']['need_count']} needs, "
            f"manifest_sha256={generated['manifest_sha256']}"
        )
        return 0

    if not output_path.is_file():
        print(f"linux API-needs error: missing golden {output_path}", file=sys.stderr)
        return 2
    try:
        checked_in = read_json(output_path)
        validate_manifest(checked_in, inventory, source_lock, repo)
    except ApiNeedsError as exc:
        print(f"linux API-needs error: {exc}", file=sys.stderr)
        return 2
    checked_rendered = pretty(checked_in)
    if checked_rendered != rendered:
        print("Linux API-needs manifest is stale", file=sys.stderr)
        for index, line in enumerate(
            difflib.unified_diff(
                checked_rendered.splitlines(),
                rendered.splitlines(),
                fromfile=str(output_path),
                tofile=f"{output_path} (regenerated)",
                n=3,
            )
        ):
            if index >= 300:
                print("... diff truncated ...", file=sys.stderr)
                break
            print(line, file=sys.stderr)
        return 1
    coverage = generated["coverage"]
    print(
        "Linux API-needs manifest verified: "
        f"{coverage['by_lookup_kind']['module_import']} imports, "
        f"{coverage['by_lookup_kind']['dynamic_kallsyms']} kallsyms needs, "
        "RS-001 credit remains blocked"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
