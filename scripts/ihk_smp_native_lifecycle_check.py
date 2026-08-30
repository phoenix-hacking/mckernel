#!/usr/bin/env python3
"""Fail-closed validation for the native Rust ihk-smp lifecycle foundation."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import sys
import tempfile
from typing import Any

if __package__:
    from .native_rust_kconfig_policy import (
        KconfigPolicyError,
        validate_native_rust_kbuild,
        validate_native_rust_kconfig,
    )
else:
    from native_rust_kconfig_policy import (
        KconfigPolicyError,
        validate_native_rust_kbuild,
        validate_native_rust_kconfig,
    )


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONTRACT = Path(
    "host-kernel/native-rust/ihk-smp-lifecycle-contract-v1.json"
)
BOUND_MODINFO_ENVIRONMENT = {
    "LANG": "C",
    "LC_ALL": "C",
    "PATH": "/usr/bin:/bin",
    "TZ": "UTC",
}


class ValidationError(Exception):
    """Raised when the SMP lifecycle contract is incomplete or inconsistent."""


def _object_without_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise ValidationError(f"duplicate JSON key: {key}")
        value[key] = item
    return value


def _load_json(path: Path) -> dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as stream:
            value = json.load(stream, object_pairs_hook=_object_without_duplicates)
    except (OSError, UnicodeError, ValueError) as error:
        raise ValidationError(f"cannot load {path}: {error}") from error
    if not isinstance(value, dict):
        raise ValidationError(f"{path} must contain a JSON object")
    return value


def _require_keys(value: dict[str, Any], expected: set[str], label: str) -> None:
    actual = set(value)
    if actual != expected:
        raise ValidationError(
            f"{label} keys differ: missing={sorted(expected - actual)}, "
            f"extra={sorted(actual - expected)}"
        )


def _repo_file(repo: Path, relative: str, label: str) -> Path:
    if not isinstance(relative, str) or not relative or "\\" in relative:
        raise ValidationError(f"{label} must be a non-empty POSIX path")
    relative_path = Path(relative)
    if relative_path.is_absolute() or ".." in relative_path.parts:
        raise ValidationError(f"{label} escapes the repository: {relative}")
    candidate = repo / relative_path
    try:
        candidate.lstat()
    except OSError as error:
        raise ValidationError(f"{label} is unavailable: {error}") from error
    if candidate.is_symlink() or not candidate.is_file():
        raise ValidationError(f"{label} must be a regular, non-symlink file")
    try:
        candidate.resolve().relative_to(repo.resolve())
    except ValueError as error:
        raise ValidationError(f"{label} resolves outside the repository") from error
    return candidate


def _read_text(path: Path, label: str) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        raise ValidationError(f"cannot read {label}: {error}") from error


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _module_block(text: str) -> dict[str, str]:
    match = re.search(r"module!\s*\{(?P<body>.*?)^\}", text, re.MULTILINE | re.DOTALL)
    if not match:
        raise ValidationError("Rust source lacks a module! entry point")
    fields = re.findall(
        r'^\s*([a-z_]+):\s*(?:"([^"\\]*)"|([A-Za-z_][A-Za-z0-9_]*)),$',
        match.group("body"),
        re.MULTILINE,
    )
    result = {name: string_value or identifier for name, string_value, identifier in fields}
    if len(result) != len(fields):
        raise ValidationError("module! metadata has duplicate or unparsable fields")
    return result


def _literal_string_constant(text: str, name: str) -> str:
    match = re.search(
        rf'^const {re.escape(name)}:\s*&str\s*=\s*"([^"\\]*)";$',
        text,
        re.MULTILINE,
    )
    if not match:
        raise ValidationError(f"Rust source must define literal {name}: &str")
    return match.group(1)


def _literal_usize_constant(text: str, name: str) -> int:
    match = re.search(
        rf"^const {re.escape(name)}:\s*usize\s*=\s*([0-9]+);$",
        text,
        re.MULTILINE,
    )
    if not match:
        raise ValidationError(f"Rust source must define literal {name}: usize")
    return int(match.group(1))


PARAMETER_PATTERN = re.compile(
    r"""
    ^numeric_parameter!\(\s*
    name:\s*(?P<name>[a-z][a-z0-9_]*),\s*
    storage:\s*(?P<storage>[A-Z][A-Z0-9_]*),\s*
    descriptor:\s*(?P<descriptor>[A-Z][A-Z0-9_]*),\s*
    rust_type:\s*(?P<rust_type>core::ffi::c_(?:uint|ulong)),\s*
    ops:\s*(?P<ops>param_ops_(?:uint|ulong)),\s*
    default:\s*(?P<default>[0-9]+),\s*
    permission:\s*(?P<permission>0o[0-7]+),\s*
    loadable_name_bytes:\s*b"(?P<loadable_name_bytes>[a-z][a-z0-9_]*\\0)",\s*
    builtin_name_bytes:\s*b"(?P<builtin_name_bytes>[a-z][a-z0-9_.]*\\0)",\s*
    \);$
    """,
    re.MULTILINE | re.VERBOSE,
)


MODINFO_PATTERN = re.compile(
    r"""
    ^modinfo_pair!\(\s*
    (?P<loadable_name>[A-Z][A-Z0-9_]*),\s*
    (?P<builtin_name>[A-Z][A-Z0-9_]*),\s*
    b"(?P<loadable>[^"\\]*(?:\\.[^"\\]*)*)",\s*
    b"(?P<builtin>[^"\\]*(?:\\.[^"\\]*)*)"\s*
    \);$
    """,
    re.MULTILINE | re.VERBOSE,
)


def _validate_contract(contract: dict[str, Any]) -> None:
    _require_keys(
        contract,
        {
            "artifact_policy",
            "dependency_contract",
            "gate_id",
            "kbuild",
            "kconfig",
            "legacy_source_commit",
            "lifecycle_logs",
            "module",
            "parameters",
            "production_source",
            "provider_source",
            "reference_inventory",
            "schema_version",
            "stage_manifest",
        },
        "contract",
    )
    if contract["schema_version"] != 1 or contract["gate_id"] != "SMP-001":
        raise ValidationError("unsupported SMP lifecycle contract identity")
    if contract["legacy_source_commit"] != "3114d9e7101ad52030eb3effa849a5c108972a1f":
        raise ValidationError("legacy source commit differs from the frozen oracle")
    if contract["production_source"] != "host-kernel/native-rust/ihk_smp_x86_64.rs":
        raise ValidationError("contract points at a different production crate")
    if contract["provider_source"] != "host-kernel/native-rust/ihk.rs":
        raise ValidationError("contract points at a different native IHK provider")

    _require_keys(
        contract["artifact_policy"],
        {"environment_generated_metadata", "rocky_10_2_build_and_load_required_for_gate"},
        "contract.artifact_policy",
    )
    if contract["artifact_policy"] != {
        "environment_generated_metadata": ["rhelversion", "srcversion", "vermagic"],
        "rocky_10_2_build_and_load_required_for_gate": True,
    }:
        raise ValidationError("artifact policy weakens the Rocky 10.2 gate")

    _require_keys(
        contract["dependency_contract"],
        {
            "built_symbol_reference_validated",
            "dependencies",
            "import_namespaces",
            "provider_symbol",
            "scope",
            "source_symbol_reference_required",
        },
        "contract.dependency_contract",
    )
    dependency = contract["dependency_contract"]
    if dependency != {
        "built_symbol_reference_validated": False,
        "dependencies": ["ihk"],
        "import_namespaces": ["MCKERNEL_IHK_V1"],
        "provider_symbol": "ihk_provider_lifecycle_v1",
        "scope": "source-bound namespaced symbol dependency; built relocation and runtime ordering require Rocky evidence",
        "source_symbol_reference_required": True,
    }:
        raise ValidationError("provider dependency/import contract differs or overclaims runtime proof")

    _require_keys(
        contract["module"],
        {"forbidden_static_metadata", "license", "name", "output"},
        "contract.module",
    )
    if contract["module"] != {
        "forbidden_static_metadata": ["author", "description", "version"],
        "license": "Dual BSD/GPL",
        "name": "ihk_smp_x86_64",
        "output": "ihk-smp-x86_64.ko",
    }:
        raise ValidationError("module identity/metadata differs from the frozen legacy module")

    _require_keys(contract["lifecycle_logs"], {"load", "unload"}, "contract.lifecycle_logs")
    for phase in ("load", "unload"):
        expected = f"lifecycle={phase} parameters={{}} dependency={{}} import_namespace={{}}"
        if contract["lifecycle_logs"][phase] != expected:
            raise ValidationError(f"{phase} lifecycle diagnostic is not the stable contract string")

    _require_keys(
        contract["kconfig"], {"path", "provider_symbol", "symbol", "type"}, "contract.kconfig"
    )
    if contract["kconfig"] != {
        "path": "host-kernel/kbuild/Kconfig",
        "provider_symbol": "MCKERNEL_IHK_RUST",
        "symbol": "MCKERNEL_IHK_SMP_X86_64_RUST",
        "type": "tristate",
    }:
        raise ValidationError("Kconfig contract differs from the native SMP target")
    _require_keys(
        contract["kbuild"],
        {"composite_object", "config_symbol", "module_object", "path"},
        "contract.kbuild",
    )
    if contract["kbuild"] != {
        "composite_object": "ihk-smp-x86_64-y := ihk_smp_x86_64.o",
        "config_symbol": "CONFIG_MCKERNEL_IHK_SMP_X86_64_RUST",
        "module_object": "ihk-smp-x86_64.o",
        "path": "host-kernel/kbuild/Kbuild.in",
    }:
        raise ValidationError("Kbuild contract differs from ihk-smp-x86_64.ko")

    parameters = contract["parameters"]
    if not isinstance(parameters, list) or len(parameters) != 6:
        raise ValidationError("contract must contain exactly six SMP parameters")
    expected_names = {
        "ihk_cores",
        "ihk_ikc_irq_core",
        "ihk_mem",
        "ihk_phys_start",
        "ihk_start_irq",
        "ihk_trampoline",
    }
    actual_names: set[str] = set()
    for index, parameter in enumerate(parameters):
        if not isinstance(parameter, dict):
            raise ValidationError(f"contract.parameters[{index}] must be an object")
        _require_keys(
            parameter,
            {
                "default",
                "description",
                "legacy_source",
                "name",
                "ops",
                "permission",
                "rust_type",
                "type",
            },
            f"contract.parameters[{index}]",
        )
        name = parameter["name"]
        if not isinstance(name, str) or name in actual_names:
            raise ValidationError("parameter names must be unique strings")
        actual_names.add(name)
        if parameter["default"] != 0 or parameter["permission"] != "0644":
            raise ValidationError(f"{name} must retain default 0 and permission 0644")
        type_contracts = {
            "uint": ("core::ffi::c_uint", "param_ops_uint"),
            "ulong": ("core::ffi::c_ulong", "param_ops_ulong"),
        }
        expected_type = type_contracts.get(parameter["type"])
        if expected_type is None or (parameter["rust_type"], parameter["ops"]) != expected_type:
            raise ValidationError(f"{name} has an inconsistent numeric type/ops contract")
    if actual_names != expected_names:
        raise ValidationError("SMP parameter names differ from the frozen six-name surface")


def _expected_modinfo(contract: dict[str, Any]) -> tuple[set[str], set[str]]:
    module_name = contract["module"]["name"]
    loadable = {"import_ns=MCKERNEL_IHK_V1\\0"}
    for parameter in contract["parameters"]:
        loadable.add(f"parm={parameter['name']}:{parameter['description']}\\0")
        loadable.add(f"parmtype={parameter['name']}:{parameter['type']}\\0")
    builtin = {f"{module_name}.{record}" for record in loadable}
    return loadable, builtin


def _validate_rust_source(text: str, contract: dict[str, Any]) -> None:
    metadata = _module_block(text)
    expected_metadata = {
        "type": "IhkSmpModule",
        "name": contract["module"]["name"],
        "license": contract["module"]["license"],
    }
    if metadata != expected_metadata:
        raise ValidationError(
            f"module! metadata differs from exact legacy-compatible fields: {metadata}"
        )

    parameters = {item["name"]: item for item in contract["parameters"]}
    if _literal_usize_constant(text, "IHK_SMP_PARAMETER_COUNT") != len(parameters):
        raise ValidationError("Rust parameter count differs from the six-parameter contract")
    if _literal_string_constant(text, "IHK_SMP_DEPENDENCY") != "ihk":
        raise ValidationError("Rust provider dependency constant differs")
    if _literal_string_constant(text, "IHK_SMP_IMPORT_NAMESPACE") != "MCKERNEL_IHK_V1":
        raise ValidationError("Rust provider import namespace constant differs")
    provider_symbol = contract["dependency_contract"]["provider_symbol"]
    provider_import = (
        'extern "Rust" {\n'
        f'    #[link_name = "{provider_symbol}"]\n'
        "    static IHK_PROVIDER_LIFECYCLE_V1: u8;\n"
        "}"
    )
    if provider_import not in text or len(re.findall(r'\bextern\s+"Rust"', text)) != 1:
        raise ValidationError("Rust source lacks the exact audited provider-symbol import")
    if len(re.findall(r"\bextern\s+\"", text)) != 1:
        raise ValidationError("Rust source contains an additional unreviewed extern boundary")

    required_abi_fragments = (
        '#[link_section = "__param"]',
        "struct KernelParameter",
        "union KernelParameterValue",
        "unsafe impl Sync for KernelParameter {}",
        "core::mem::size_of::<kernel::bindings::kernel_param>()",
        "core::mem::align_of::<kernel::bindings::kernel_param>()",
        "module: THIS_MODULE.as_ptr()",
        "core::ptr::addr_of!(kernel::bindings::$ops)",
        "core::ptr::addr_of_mut!($storage)",
        "core::ptr::read_volatile(core::ptr::addr_of!(IHK_PROVIDER_LIFECYCLE_V1))",
        "level: -1",
        "flags: 0",
    )
    for fragment in required_abi_fragments:
        if fragment not in text:
            raise ValidationError(f"Rust parameter ABI lacks required fragment: {fragment}")

    parameter_name_selection = """name: {
                #[cfg(MODULE)]
                const PARAMETER_NAME: &[u8] = $loadable_name_bytes;
                #[cfg(not(MODULE))]
                const PARAMETER_NAME: &[u8] = $builtin_name_bytes;
                PARAMETER_NAME.as_ptr() as *const core::ffi::c_char
            },"""
    if text.count(parameter_name_selection) != 1:
        raise ValidationError(
            "Rust parameter ABI must select Linux loadable/built-in descriptor names by MODULE"
        )

    matches = list(PARAMETER_PATTERN.finditer(text))
    invocation_count = len(re.findall(r"^numeric_parameter!\(", text, re.MULTILINE))
    if len(matches) != 6 or invocation_count != len(matches):
        raise ValidationError("Rust source must contain exactly six fully literal parameter descriptors")
    actual_parameters: dict[str, dict[str, str]] = {}
    for match in matches:
        item = match.groupdict()
        name = item["name"]
        if name in actual_parameters:
            raise ValidationError(f"duplicate Rust parameter descriptor: {name}")
        expected = parameters.get(name)
        if expected is None:
            raise ValidationError(f"unexpected Rust parameter descriptor: {name}")
        expected_storage = name.upper()
        expected_descriptor = "PARAM_" + expected_storage
        actual = {
            "storage": item["storage"],
            "descriptor": item["descriptor"],
            "rust_type": item["rust_type"],
            "ops": item["ops"],
            "default": item["default"],
            "permission": item["permission"],
            "loadable_name_bytes": item["loadable_name_bytes"],
            "builtin_name_bytes": item["builtin_name_bytes"],
        }
        wanted = {
            "storage": expected_storage,
            "descriptor": expected_descriptor,
            "rust_type": expected["rust_type"],
            "ops": expected["ops"],
            "default": str(expected["default"]),
            "permission": "0o" + expected["permission"].lstrip("0"),
            "loadable_name_bytes": name + "\\0",
            "builtin_name_bytes": contract["module"]["name"] + "." + name + "\\0",
        }
        if actual != wanted:
            raise ValidationError(f"Rust descriptor for {name} differs: expected {wanted}, got {actual}")
        actual_parameters[name] = actual
    if set(actual_parameters) != set(parameters):
        raise ValidationError("Rust parameter descriptor set is incomplete")

    pairs = list(MODINFO_PATTERN.finditer(text))
    expected_loadable, expected_builtin = _expected_modinfo(contract)
    loadable = [match.group("loadable") for match in pairs]
    builtin = [match.group("builtin") for match in pairs]
    if (
        len(pairs) != len(expected_loadable)
        or len(set(loadable)) != len(loadable)
        or set(loadable) != expected_loadable
    ):
        raise ValidationError("loadable Rust modinfo records differ from the exact SMP contract")
    if len(set(builtin)) != len(builtin) or set(builtin) != expected_builtin:
        raise ValidationError("built-in Rust modinfo records differ from the exact SMP contract")
    if re.search(r'b"(?:ihk_smp_x86_64\.)?depends=', text):
        raise ValidationError("Rust source must let modpost derive depends=ihk from the provider symbol")

    if "impl kernel::Module for IhkSmpModule" not in text or "impl Drop for IhkSmpModule" not in text:
        raise ValidationError("Rust source lacks paired module init/drop lifecycle")
    if "fn init(_module: &'static ThisModule) -> Result<Self>" not in text or "Ok(Self)" not in text:
        raise ValidationError("Rust SMP lifecycle lacks an unconditional initialization path")
    for phase in ("load", "unload"):
        expected = contract["lifecycle_logs"][phase]
        if f'"{expected}\\n"' not in text:
            raise ValidationError(f"Rust source lacks stable {phase} lifecycle diagnostic")
    for constant in (
        "IHK_SMP_PARAMETER_COUNT",
        "IHK_SMP_DEPENDENCY",
        "IHK_SMP_IMPORT_NAMESPACE",
    ):
        if text.count(constant) < 3:
            raise ValidationError(f"lifecycle diagnostics do not consume {constant}")

    lowered = text.lower()
    for forbidden in ('extern "c"', "include_bytes!", "include!", "global_asm!", "asm!("):
        if forbidden in lowered:
            raise ValidationError(f"Rust lifecycle contains forbidden boundary: {forbidden}")
    for match in re.finditer(r"^\s*use\s+([^;]+);", text, re.MULTILINE):
        imported = match.group(1).strip()
        if not imported.startswith(("kernel::", "core::")):
            raise ValidationError(f"unreviewed Rust dependency: {imported}")


def _validate_provider_source(text: str, contract: dict[str, Any]) -> None:
    symbol = contract["dependency_contract"]["provider_symbol"]
    export_record_layout = """pub struct IhkExportSymbolRecord {
    license: [u8; 4],
    namespace: [u8; 16],
    padding: [u8; 4],
    symbol: *const u8,
}"""
    if text.count(export_record_layout) != 1:
        raise ValidationError(
            "native IHK provider anchor lacks the exact x86_64 .export_symbol record layout"
        )
    required = (
        '#[repr(C, align(8))]',
        "pub struct IhkExportSymbolRecord",
        "unsafe impl Sync for IhkExportSymbolRecord {}",
        "const _: [(); 32] = [(); core::mem::size_of::<IhkExportSymbolRecord>()];",
        "const _: [(); 8] = [(); core::mem::align_of::<IhkExportSymbolRecord>()];",
        f'#[export_name = "{symbol}"]',
        f'#[export_name = "__export_symbol_{symbol}"]',
        '#[link_section = ".export_symbol"]',
        'license: *b"GPL\\0"',
        'namespace: *b"MCKERNEL_IHK_V1\\0"',
        "symbol: core::ptr::addr_of!(IHK_PROVIDER_LIFECYCLE_V1)",
    )
    for fragment in required:
        if fragment not in text:
            raise ValidationError(f"native IHK provider anchor lacks required fragment: {fragment}")
    if text.count(f'#[export_name = "{symbol}"]') != 1:
        raise ValidationError("native IHK provider anchor symbol is not unique")
    if text.count(f'#[export_name = "__export_symbol_{symbol}"]') != 1:
        raise ValidationError("native IHK provider export record is not unique")
    lowered = text.lower()
    for forbidden in ('extern "c"', "include_bytes!", "include!", "global_asm!", "asm!("):
        if forbidden in lowered:
            raise ValidationError(f"native IHK provider contains forbidden boundary: {forbidden}")


def _validate_kconfig(text: str, contract: dict[str, Any]) -> None:
    try:
        validate_native_rust_kconfig(text)
    except KconfigPolicyError as error:
        raise ValidationError(f"shared native Rust Kconfig policy violation: {error}") from error
    symbol = contract["kconfig"]["symbol"]
    matches = list(re.finditer(rf"^config {re.escape(symbol)}$", text, re.MULTILINE))
    if len(matches) != 1:
        raise ValidationError(f"Kconfig must define {symbol} exactly once")
    tail = text[matches[0].end() :]
    block = re.split(r"^config |^endmenu$", tail, maxsplit=1, flags=re.MULTILINE)[0]
    if not re.search(r'^\s*tristate\s+"[^"\n]+"$', block, re.MULTILINE):
        raise ValidationError("SMP Kconfig entry must remain a tristate")
    dependencies = re.findall(r"^\s*depends on\s+(.+)$", block, re.MULTILINE)
    if dependencies != [contract["kconfig"]["provider_symbol"]]:
        raise ValidationError("SMP Kconfig provider dependency differs")
    if re.search(r"^\s*(?:select|imply|default|def_bool|def_tristate)\b", block, re.MULTILINE):
        raise ValidationError("SMP Kconfig entry may not hide a provider/configuration edge")


def _validate_kbuild(text: str, contract: dict[str, Any]) -> None:
    try:
        validate_native_rust_kbuild(text)
    except KconfigPolicyError as error:
        raise ValidationError(f"shared native Rust Kbuild policy violation: {error}") from error
    mapping = (
        f"obj-$({contract['kbuild']['config_symbol']}) += "
        f"{contract['kbuild']['module_object']}"
    )
    substantive = [line.strip() for line in text.splitlines() if line.strip()]
    if substantive.count(mapping) != 1:
        raise ValidationError("Kbuild lacks the exact ihk-smp-x86_64.ko mapping")
    if substantive.count(contract["kbuild"]["composite_object"]) != 1:
        raise ValidationError("Kbuild lacks the exact Rust crate composite mapping")
    for line in substantive:
        if contract["kbuild"]["config_symbol"] in line and line != mapping:
            raise ValidationError("Kbuild contains an alternate SMP production mapping")
    if re.search(r"\.(?:c|cc|cpp|a|so)\b", text, re.IGNORECASE):
        raise ValidationError("Kbuild contains a forbidden project implementation input")


def _validate_stage_manifest(
    manifest: dict[str, Any], source_path: Path, provider_path: Path, contract: dict[str, Any]
) -> None:
    build = manifest.get("build_contract", {})
    if build.get("project_c_link_objects") != 0:
        raise ValidationError("stage manifest does not enforce zero project C objects")
    if build.get("allowed_project_source_suffixes") != [".rs"]:
        raise ValidationError("stage manifest permits non-Rust project sources")
    modules = [
        item for item in manifest.get("modules", []) if item.get("crate") == "ihk_smp_x86_64"
    ]
    if len(modules) != 1:
        raise ValidationError("stage manifest must contain exactly one SMP crate")
    module = modules[0]
    dependency = contract["dependency_contract"]
    if module.get("dependencies") != dependency["dependencies"]:
        raise ValidationError("stage manifest SMP provider dependency differs")
    if module.get("required_import_namespaces") != dependency["import_namespaces"]:
        raise ValidationError("stage manifest SMP import namespace differs")
    if module.get("output") != contract["module"]["output"]:
        raise ValidationError("stage manifest SMP output differs")
    source = module.get("source", {})
    if source.get("repository_path") != contract["production_source"]:
        raise ValidationError("stage manifest points SMP at a different production source")
    if source.get("destination") != "ihk_smp_x86_64.rs":
        raise ValidationError("stage manifest SMP destination differs")
    if source.get("sha256") != _sha256(source_path):
        raise ValidationError("stage manifest SMP source digest is stale")
    providers = [item for item in manifest.get("modules", []) if item.get("crate") == "ihk"]
    if len(providers) != 1:
        raise ValidationError("stage manifest must contain exactly one native IHK provider")
    provider_source = providers[0].get("source", {})
    if provider_source.get("repository_path") != contract["provider_source"]:
        raise ValidationError("stage manifest points at a different native IHK provider")
    if provider_source.get("sha256") != _sha256(provider_path):
        raise ValidationError("stage manifest native IHK provider source digest is stale")


def _validate_reference_inventory(
    inventory: dict[str, Any], contract: dict[str, Any], repo: Path
) -> None:
    provenance = inventory.get("provenance", {})
    if provenance.get("ihk_commit") != contract["legacy_source_commit"]:
        raise ValidationError("reference inventory is not bound to the frozen IHK commit")
    try:
        source_parameters = inventory["source_capture"]["modules"]["ihk_smp_x86_64"][
            "source_module_parameters"
        ]
        binary_values = inventory["binary_capture"]["modules"]["ihk_smp_x86_64"][
            "modinfo"
        ]["values"]
    except (KeyError, TypeError) as error:
        raise ValidationError("reference inventory lacks the SMP metadata oracle") from error

    expected = {item["name"]: item for item in contract["parameters"]}
    source: dict[str, dict[str, Any]] = {}
    for item in source_parameters:
        if not isinstance(item, dict) or not isinstance(item.get("name"), str):
            raise ValidationError("reference source parameter entry is malformed")
        name = item["name"]
        if name in source:
            raise ValidationError(f"reference source has duplicate parameter {name}")
        source[name] = item
    if set(source) != set(expected):
        raise ValidationError("reference inventory parameter names differ from the contract")
    for name, parameter in expected.items():
        item = source[name]
        oracle = {
            "description": item.get("description"),
            "permissions_expression": item.get("permissions_expression"),
            "source": item.get("source"),
            "type": item.get("type"),
        }
        wanted = {
            "description": parameter["description"],
            "permissions_expression": parameter["permission"],
            "source": parameter["legacy_source"],
            "type": parameter["type"],
        }
        if oracle != wanted:
            raise ValidationError(f"reference source oracle differs for {name}")

    if binary_values.get("name") != [contract["module"]["name"]]:
        raise ValidationError("legacy binary module name differs")
    if binary_values.get("license") != [contract["module"]["license"]]:
        raise ValidationError("legacy binary license differs")
    if binary_values.get("depends") != contract["dependency_contract"]["dependencies"]:
        raise ValidationError("legacy binary provider dependency differs")
    for forbidden in contract["module"]["forbidden_static_metadata"]:
        if forbidden in binary_values:
            raise ValidationError(f"legacy binary unexpectedly carries {forbidden} metadata")
    parm = {value.split(":", 1)[0]: value.split(":", 1)[1] for value in binary_values.get("parm", [])}
    parmtype = {
        value.split(":", 1)[0]: value.split(":", 1)[1]
        for value in binary_values.get("parmtype", [])
    }
    if parm != {name: item["description"] for name, item in expected.items()}:
        raise ValidationError("legacy binary parameter descriptions differ")
    if parmtype != {name: item["type"] for name, item in expected.items()}:
        raise ValidationError("legacy binary parameter types differ")

    source_texts: dict[str, str] = {}
    for parameter in contract["parameters"]:
        relative = parameter["legacy_source"]
        if relative not in source_texts:
            source_texts[relative] = _read_text(
                _repo_file(repo, relative, f"legacy parameter source {relative}"),
                f"legacy parameter source {relative}",
            )
        text = source_texts[relative]
        c_type = "unsigned int" if parameter["type"] == "uint" else "unsigned long"
        patterns = (
            rf"\bstatic\s+{re.escape(c_type)}\s+{re.escape(parameter['name'])}\s*=\s*0\s*;",
            rf"\bmodule_param\(\s*{re.escape(parameter['name'])}\s*,\s*{parameter['type']}\s*,\s*{parameter['permission']}\s*\)\s*;",
            rf'\bMODULE_PARM_DESC\(\s*{re.escape(parameter["name"])}\s*,\s*"{re.escape(parameter["description"])}"\s*\)\s*;',
        )
        for pattern in patterns:
            if len(re.findall(pattern, text)) != 1:
                raise ValidationError(
                    f"frozen source does not prove {parameter['name']} type/default/permission/description"
                )


def validate_repository(
    repo: Path, contract_relative: Path = DEFAULT_CONTRACT
) -> dict[str, Any]:
    repo = repo.resolve()
    contract_path = _repo_file(repo, contract_relative.as_posix(), "SMP lifecycle contract")
    contract = _load_json(contract_path)
    _validate_contract(contract)
    source_path = _repo_file(repo, contract["production_source"], "production SMP Rust source")
    _validate_rust_source(_read_text(source_path, "production SMP Rust source"), contract)
    provider_path = _repo_file(repo, contract["provider_source"], "native IHK provider source")
    _validate_provider_source(_read_text(provider_path, "native IHK provider source"), contract)
    _validate_kconfig(
        _read_text(_repo_file(repo, contract["kconfig"]["path"], "production Kconfig"), "Kconfig"),
        contract,
    )
    _validate_kbuild(
        _read_text(_repo_file(repo, contract["kbuild"]["path"], "production Kbuild"), "Kbuild"),
        contract,
    )
    _validate_stage_manifest(
        _load_json(_repo_file(repo, contract["stage_manifest"], "stage manifest")),
        source_path,
        provider_path,
        contract,
    )
    _validate_reference_inventory(
        _load_json(_repo_file(repo, contract["reference_inventory"], "legacy inventory")),
        contract,
        repo,
    )
    return {
        "artifact_validated": False,
        "built_symbol_reference_validated": False,
        "dependencies": contract["dependency_contract"]["dependencies"],
        "gate_id": contract["gate_id"],
        "import_namespaces": contract["dependency_contract"]["import_namespaces"],
        "module": contract["module"]["name"],
        "output": contract["module"]["output"],
        "parameters": len(contract["parameters"]),
        "rocky_build_load_validated": False,
        "source_symbol_reference_present": True,
        "runtime_symbol_reference_proven": False,
        "source_sha256": _sha256(source_path),
    }


def _raw_modinfo_records(module_path: Path) -> list[str]:
    executable = shutil.which("objcopy")
    if executable is None:
        raise ValidationError("objcopy is required for raw built-module validation")
    source_sha256 = _sha256(module_path)
    with tempfile.TemporaryDirectory(prefix="mckernel-smp-modinfo-") as temporary:
        temporary_path = Path(temporary)
        dump_path = temporary_path / "modinfo.bin"
        output_path = temporary_path / "module.copy"
        result = subprocess.run(
            [
                executable,
                "--dump-section",
                f".modinfo={dump_path}",
                str(module_path),
                str(output_path),
            ],
            check=False,
            capture_output=True,
        )
        if result.returncode != 0:
            error = result.stderr.decode("utf-8", errors="replace").strip()
            raise ValidationError(
                f"objcopy raw .modinfo extraction failed ({result.returncode}): {error}"
            )
        try:
            data = dump_path.read_bytes()
        except OSError as error:
            raise ValidationError(
                f"objcopy did not produce raw .modinfo bytes: {error}"
            ) from error
    if _sha256(module_path) != source_sha256:
        raise ValidationError("objcopy modified the built SMP module during validation")
    if not data:
        raise ValidationError("built SMP module has an empty raw .modinfo section")
    if not data.endswith(b"\0"):
        raise ValidationError("built SMP module raw .modinfo is not NUL terminated")
    # Linked kernel modules may contain zero padding between input `.modinfo`
    # contributions.  Preserve every non-empty record exactly while treating
    # only those all-zero spans as linker padding.
    encoded_records = [record for record in data.split(b"\0") if record]
    if not encoded_records:
        raise ValidationError("built SMP module raw .modinfo has no records")
    records: list[str] = []
    for encoded in encoded_records:
        try:
            record = encoded.decode("ascii")
        except UnicodeDecodeError as error:
            raise ValidationError(
                "built SMP module raw .modinfo is not exact ASCII"
            ) from error
        key, separator, _value = record.partition("=")
        if not separator or not key:
            raise ValidationError(
                f"built SMP module raw .modinfo record is malformed: {record!r}"
            )
        records.append(record)
    return records


def _modinfo_execution(modinfo_fd: int | None) -> tuple[str, tuple[int, ...]]:
    if modinfo_fd is None:
        executable = shutil.which("modinfo")
        if executable is None:
            raise ValidationError("modinfo is required for built-module validation")
        return executable, ()
    if type(modinfo_fd) is not int or modinfo_fd < 3:
        raise ValidationError("modinfo descriptor must be an open integer fd >= 3")
    try:
        descriptor_status = os.fstat(modinfo_fd)
        executable_status = os.stat(f"/proc/self/fd/{modinfo_fd}")
    except OSError as error:
        raise ValidationError(f"modinfo descriptor is unavailable: {error}") from error
    if (
        not stat.S_ISREG(descriptor_status.st_mode)
        or descriptor_status.st_dev != executable_status.st_dev
        or descriptor_status.st_ino != executable_status.st_ino
    ):
        raise ValidationError("modinfo descriptor must identify one regular file")
    if stat.S_IMODE(descriptor_status.st_mode) & 0o111 == 0:
        raise ValidationError("modinfo descriptor target is not executable")
    return f"/proc/self/fd/{modinfo_fd}", (modinfo_fd,)


def _modinfo(
    module_path: Path, field: str, modinfo_fd: int | None = None
) -> list[str]:
    executable, pass_fds = _modinfo_execution(modinfo_fd)
    try:
        result = subprocess.run(
            ["modinfo", "-F", field, str(module_path)],
            check=False,
            capture_output=True,
            env=dict(BOUND_MODINFO_ENVIRONMENT),
            executable=executable,
            pass_fds=pass_fds,
            text=True,
        )
    except OSError as error:
        raise ValidationError(f"bound modinfo execution failed: {error}") from error
    if result.returncode != 0:
        raise ValidationError(
            f"modinfo -F {field} failed ({result.returncode}): "
            f"{result.stderr.strip() or result.stdout.strip()}"
        )
    return [line for line in result.stdout.splitlines() if line]


def _artifact_modinfo(
    module_path: Path, field: str, modinfo_fd: int | None
) -> list[str]:
    if modinfo_fd is None:
        return _modinfo(module_path, field)
    return _modinfo(module_path, field, modinfo_fd=modinfo_fd)


def _named_parameter_values(values: list[str], label: str) -> dict[str, str]:
    parsed: dict[str, str] = {}
    for value in values:
        name, separator, detail = value.partition(":")
        if not separator or not name or not detail:
            raise ValidationError(f"built SMP module {label} is malformed: {value!r}")
        if name in parsed:
            raise ValidationError(
                f"built SMP module {label} repeats parameter {name}"
            )
        parsed[name] = detail
    return parsed


def _undefined_symbols(module_path: Path) -> set[str]:
    executable = shutil.which("nm")
    if executable is None:
        raise ValidationError("nm is required for built-module dependency validation")
    result = subprocess.run(
        [executable, "-u", str(module_path)],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise ValidationError(
            f"nm -u failed ({result.returncode}): {result.stderr.strip() or result.stdout.strip()}"
        )
    return {line.split()[-1] for line in result.stdout.splitlines() if line.split()}


def validate_module_artifact(
    module_path: Path,
    summary: dict[str, Any],
    contract: dict[str, Any],
    modinfo_fd: int | None = None,
) -> None:
    module_path = module_path.resolve()
    if module_path.is_symlink() or not module_path.is_file():
        raise ValidationError("built SMP module must be a regular, non-symlink file")
    scalar_fields = {
        "name": [contract["module"]["name"]],
        "license": [contract["module"]["license"]],
        "depends": contract["dependency_contract"]["dependencies"],
        "import_ns": contract["dependency_contract"]["import_namespaces"],
    }
    for field, expected in scalar_fields.items():
        actual = _artifact_modinfo(module_path, field, modinfo_fd)
        if actual != expected:
            raise ValidationError(
                f"built SMP module {field} differs: expected {expected}, got {actual}"
            )
    for field in contract["module"]["forbidden_static_metadata"]:
        if _artifact_modinfo(module_path, field, modinfo_fd):
            raise ValidationError(f"built SMP module unexpectedly carries {field} metadata")
    parameters = {item["name"]: item for item in contract["parameters"]}
    raw_records = _raw_modinfo_records(module_path)
    raw_parm = sorted(
        record for record in raw_records if record.startswith("parm=")
    )
    expected_raw_parm = sorted(
        f'parm={name}:{item["description"]}'
        for name, item in parameters.items()
    )
    if raw_parm != expected_raw_parm:
        raise ValidationError(
            "built SMP module raw parameter descriptions differ: "
            f"expected {expected_raw_parm}, got {raw_parm}"
        )
    raw_parmtype = sorted(
        record for record in raw_records if record.startswith("parmtype=")
    )
    expected_raw_parmtype = sorted(
        f'parmtype={name}:{item["type"]}'
        for name, item in parameters.items()
    )
    if raw_parmtype != expected_raw_parmtype:
        raise ValidationError(
            "built SMP module raw parameter types differ: "
            f"expected {expected_raw_parmtype}, got {raw_parmtype}"
        )
    parm_values = _artifact_modinfo(module_path, "parm", modinfo_fd)
    type_values = _artifact_modinfo(module_path, "parmtype", modinfo_fd)
    parm = _named_parameter_values(parm_values, "rendered parameter description")
    parmtype = _named_parameter_values(type_values, "rendered parameter type")
    # kmod deliberately renders `modinfo -F parm` by joining each raw
    # `parm=name:description` record with its `parmtype=name:type` peer.  The
    # resulting public representation is `name:description (type)`; asking for
    # `parmtype` still returns the raw `name:type` record.
    expected_parm = {
        name: f'{item["description"]} ({item["type"]})'
        for name, item in parameters.items()
    }
    if parm != expected_parm:
        raise ValidationError(
            "built SMP module parameter descriptions differ: "
            f"expected {expected_parm}, got {parm}"
        )
    expected_parmtype = {name: item["type"] for name, item in parameters.items()}
    if parmtype != expected_parmtype:
        raise ValidationError(
            "built SMP module parameter types differ: "
            f"expected {expected_parmtype}, got {parmtype}"
        )
    provider_symbol = contract["dependency_contract"]["provider_symbol"]
    if provider_symbol not in _undefined_symbols(module_path):
        raise ValidationError("built SMP module lacks the provider anchor relocation")
    data = module_path.read_bytes()
    for phase in ("load", "unload"):
        prefix = f"lifecycle={phase} parameters=".encode("ascii")
        if prefix not in data:
            raise ValidationError(f"built SMP module lacks {phase} diagnostic string")
    summary["artifact_validated"] = True
    summary["built_symbol_reference_validated"] = True


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=ROOT)
    parser.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT)
    parser.add_argument(
        "--module", type=Path, help="also validate built ihk-smp-x86_64.ko metadata"
    )
    parser.add_argument(
        "--modinfo-fd",
        type=int,
        help="inherited descriptor for the identity-bound kmod executable",
    )
    parser.add_argument("--json", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(sys.argv[1:] if argv is None else argv)
    try:
        repo = args.repo.resolve()
        contract_path = _repo_file(repo, args.contract.as_posix(), "SMP lifecycle contract")
        contract = _load_json(contract_path)
        summary = validate_repository(repo, args.contract)
        if args.modinfo_fd is not None and args.module is None:
            raise ValidationError("--modinfo-fd requires --module")
        if args.module is not None:
            validate_module_artifact(args.module, summary, contract, args.modinfo_fd)
    except ValidationError as error:
        print(f"ihk-smp-native-lifecycle-check: FAIL: {error}", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(summary, sort_keys=True))
    else:
        level = "ARTIFACT-CONTRACT-VERIFIED" if summary["artifact_validated"] else "SOURCE-CONTRACT-VERIFIED"
        print(
            "ihk-smp-native-lifecycle-check: "
            f"{level} module={summary['module']} parameters={summary['parameters']} "
            "rocky_build_load=NOT_EVALUATED runtime_symbol_reference=NOT_PROVEN"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
