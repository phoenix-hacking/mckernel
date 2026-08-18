#!/usr/bin/env python3
"""Validate the honest native Rust mcctrl lifecycle foundation.

Repository validation is source-contract validation only.  It never grants
MCC-001 credit.  Optional ``--module`` validation additionally requires the
frozen module metadata, including a modpost-derived dependency on ``ihk``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
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
DEFAULT_CONTRACT = Path("host-kernel/native-rust/mcctrl-lifecycle-contract-v1.json")


class ValidationError(Exception):
    """Raised when the mcctrl foundation is incomplete or overclaims support."""


def _object_without_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValidationError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _load_json(path: Path) -> dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as stream:
            value = json.load(stream, object_pairs_hook=_object_without_duplicates)
    except (OSError, UnicodeError, ValueError) as error:
        raise ValidationError(f"cannot load {path}: {error}") from error
    if not isinstance(value, dict):
        raise ValidationError(f"{path} must contain a JSON object")
    return value


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


def _require_keys(value: Any, expected: set[str], label: str) -> None:
    if not isinstance(value, dict):
        raise ValidationError(f"{label} must be an object")
    actual = set(value)
    if actual != expected:
        raise ValidationError(
            f"{label} keys differ: missing={sorted(expected - actual)}, "
            f"extra={sorted(actual - expected)}"
        )


def _require_nonempty_string(value: Any, label: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(f"{label} must be a non-empty string")


def _rust_string_constant(text: str, name: str) -> str:
    match = re.search(
        rf'^const {re.escape(name)}:\s*&str\s*=\s*"([^"\\]*)";$',
        text,
        re.MULTILINE,
    )
    if not match:
        raise ValidationError(f"Rust source must define literal {name}: &str")
    return match.group(1)


def _rust_integer_constant(text: str, name: str) -> int:
    match = re.search(
        rf"^const {re.escape(name)}:\s*(?:u16|usize)\s*=\s*([0-9]+);$",
        text,
        re.MULTILINE,
    )
    if not match:
        raise ValidationError(f"Rust source must define literal integer {name}")
    return int(match.group(1))


def _module_body(text: str) -> str:
    match = re.search(r"module!\s*\{(?P<body>.*?)^\}", text, re.MULTILINE | re.DOTALL)
    if not match:
        raise ValidationError("Rust source lacks a module! entry point")
    return match.group("body")


def _module_literal(body: str, field: str) -> str | None:
    matches = re.findall(
        rf'^\s*{re.escape(field)}:\s*"([^"\\]*)",$', body, re.MULTILINE
    )
    if len(matches) > 1:
        raise ValidationError(f"module! metadata repeats {field}")
    return matches[0] if matches else None


def _validate_contract(contract: dict[str, Any]) -> None:
    _require_keys(
        contract,
        {
            "binfmt",
            "dependencies",
            "foundation_status",
            "foundation_version",
            "gate_credit_eligible",
            "gate_id",
            "ihk_dependency",
            "kbuild",
            "kconfig",
            "legacy_lifecycle",
            "lifecycle_logs",
            "module",
            "parameter_count",
            "production_source",
            "provider_source",
            "reference_inventory",
            "schema_version",
            "selected_kernel",
            "stage_manifest",
        },
        "contract",
    )
    if contract["schema_version"] != 1 or contract["gate_id"] != "MCC-001":
        raise ValidationError("unsupported mcctrl lifecycle contract identity")
    if contract["foundation_version"] != 1:
        raise ValidationError("mcctrl foundation version must be 1")
    if contract["foundation_status"] != "source-bound-dependency":
        raise ValidationError("mcctrl foundation status overclaims implementation")
    if contract["gate_credit_eligible"] is not False:
        raise ValidationError("MCC-001 credit is forbidden by this source-only contract")
    if contract["dependencies"] != ["ihk"]:
        raise ValidationError("frozen mcctrl dependency set must be ['ihk']")
    if contract["parameter_count"] != 0:
        raise ValidationError("frozen mcctrl module-parameter count must be zero")
    if contract["provider_source"] != "host-kernel/native-rust/ihk.rs":
        raise ValidationError("contract points at a different native IHK provider")

    _require_keys(
        contract["module"],
        {"author", "description", "license", "name", "output", "version"},
        "contract.module",
    )
    if contract["module"] != {
        "author": None,
        "description": None,
        "license": "GPL v2",
        "name": "mcctrl",
        "output": "mcctrl.ko",
        "version": None,
    }:
        raise ValidationError("mcctrl module metadata differs from the frozen binary")

    _require_keys(
        contract["ihk_dependency"],
        {"legacy_inter_module_import_count", "native_symbol_import", "required_import_namespace"},
        "contract.ihk_dependency",
    )
    dependency = contract["ihk_dependency"]
    if dependency["legacy_inter_module_import_count"] != 32:
        raise ValidationError("frozen mcctrl IHK import count must be 32")
    if dependency["required_import_namespace"] != "MCKERNEL_IHK_V1":
        raise ValidationError("mcctrl must declare the production IHK namespace")
    _require_keys(
        dependency["native_symbol_import"],
        {
            "built_symbol_reference_validated",
            "provider_symbol",
            "runtime_symbol_reference_proven",
            "scope",
            "source_reference_required",
            "status",
        },
        "native symbol import",
    )
    dependency_scope = (
        "source-bound namespaced lifecycle anchor; built relocation and runtime "
        "unload ordering require exact Rocky 10.2 evidence"
    )
    if dependency["native_symbol_import"] != {
        "built_symbol_reference_validated": False,
        "provider_symbol": "ihk_provider_lifecycle_v1",
        "runtime_symbol_reference_proven": False,
        "scope": dependency_scope,
        "source_reference_required": True,
        "status": "source-bound",
    }:
        raise ValidationError("native IHK symbol import contract differs or overclaims proof")

    _require_keys(
        contract["binfmt"],
        {"legacy_imports", "native_registration_status", "owner_gate_id", "reason"},
        "contract.binfmt",
    )
    binfmt = contract["binfmt"]
    if binfmt["legacy_imports"] != ["__register_binfmt", "unregister_binfmt"]:
        raise ValidationError("frozen binfmt import surface differs")
    if binfmt["native_registration_status"] != "blocked":
        raise ValidationError("native binfmt ownership must remain explicitly blocked")
    if binfmt["owner_gate_id"] != "MCC-013":
        raise ValidationError("binfmt behavior must remain owned by MCC-013")
    _require_nonempty_string(binfmt["reason"], "binfmt blocker reason")

    _require_keys(contract["kconfig"], {"depends_on", "path", "symbol", "type"}, "contract.kconfig")
    if contract["kconfig"] != {
        "depends_on": "MCKERNEL_IHK_RUST",
        "path": "host-kernel/kbuild/Kconfig",
        "symbol": "MCKERNEL_MCCTRL_RUST",
        "type": "tristate",
    }:
        raise ValidationError("mcctrl Kconfig contract differs from production")
    _require_keys(contract["kbuild"], {"config_symbol", "module_object", "path"}, "contract.kbuild")
    if contract["kbuild"] != {
        "config_symbol": "CONFIG_MCKERNEL_MCCTRL_RUST",
        "module_object": "mcctrl.o",
        "path": "host-kernel/kbuild/Kbuild.in",
    }:
        raise ValidationError("mcctrl Kbuild contract differs from production")
    _require_keys(contract["lifecycle_logs"], {"load", "unload"}, "contract.lifecycle_logs")
    _require_keys(
        contract["legacy_lifecycle"],
        {"load_success_log", "unload_success_log"},
        "contract.legacy_lifecycle",
    )
    if contract["legacy_lifecycle"] != {
        "load_success_log": "mcctrl: initialized successfully.",
        "unload_success_log": "mcctrl: unregistered.",
    }:
        raise ValidationError("frozen legacy lifecycle diagnostics differ")

    _require_keys(
        contract["selected_kernel"],
        {"archive_sha256", "release", "reviewed_rust_paths", "source_lock"},
        "contract.selected_kernel",
    )
    selected = contract["selected_kernel"]
    if selected["release"] != "6.12.0-211.44.1.el10_2":
        raise ValidationError("selected kernel release differs")
    expected_archive_sha256 = (
        "4a174d47b8874a2139efcd1ac1ab2d6b80ae7a0ca62f0ae4596fd20cf62a3533"
    )
    if selected["archive_sha256"] != expected_archive_sha256:
        raise ValidationError("selected kernel archive digest differs")
    if selected["reviewed_rust_paths"] != [
        "include/linux/export.h",
        "rust/bindings/bindings_helper.h",
        "rust/exports.c",
        "rust/kernel/lib.rs",
        "rust/macros/module.rs",
        "scripts/mod/modpost.c",
    ]:
        raise ValidationError("selected Rust API review scope differs")


def _validate_rust_source(text: str, contract: dict[str, Any]) -> None:
    module = contract["module"]
    body = _module_body(text)
    if _module_literal(body, "name") != module["name"]:
        raise ValidationError("module! name differs from frozen mcctrl metadata")
    if _module_literal(body, "license") != module["license"]:
        raise ValidationError("module! license differs from frozen mcctrl metadata")
    for field in ("author", "description"):
        if _module_literal(body, field) is not None:
            raise ValidationError(f"module! {field} is absent from the frozen mcctrl metadata")

    if _rust_integer_constant(text, "MCCTRL_FOUNDATION_VERSION") != contract["foundation_version"]:
        raise ValidationError("Rust foundation version differs from contract")
    if _rust_integer_constant(text, "MCCTRL_PARAMETER_COUNT") != contract["parameter_count"]:
        raise ValidationError("Rust parameter count differs from frozen contract")
    declared_dependencies = _rust_integer_constant(
        text, "MCCTRL_DECLARED_DEPENDENCY_COUNT"
    )
    if declared_dependencies != len(contract["dependencies"]):
        raise ValidationError("Rust declared dependency count differs from contract")
    if _rust_string_constant(text, "MCCTRL_IHK_IMPORT_STATUS") != "source-bound-anchor":
        raise ValidationError("Rust source does not identify its source-bound IHK anchor")
    if _rust_string_constant(text, "MCCTRL_BINFMT_STATUS") != "blocked-no-safe-rust-api":
        raise ValidationError("Rust source overclaims binfmt ownership")

    namespace = contract["ihk_dependency"]["required_import_namespace"]
    for record in (f"import_ns={namespace}\\0", f"mcctrl.import_ns={namespace}\\0"):
        if f'*b"{record}"' not in text:
            raise ValidationError(f"Rust source lacks IHK namespace modinfo record: {record}")
    if "#[cfg(MODULE)]" not in text or "#[cfg(not(MODULE))]" not in text:
        raise ValidationError("IHK import metadata must cover loadable and built-in forms")

    provider_symbol = contract["ihk_dependency"]["native_symbol_import"][
        "provider_symbol"
    ]
    provider_import = (
        'extern "Rust" {\n'
        f'    #[link_name = "{provider_symbol}"]\n'
        "    static IHK_PROVIDER_LIFECYCLE_V1: u8;\n"
        "}"
    )
    if provider_import not in text or len(re.findall(r'\bextern\s+"Rust"', text)) != 1:
        raise ValidationError("Rust source lacks the exact audited provider-symbol import")
    if len(re.findall(r'\bextern\s+"', text)) != 1:
        raise ValidationError("Rust source contains an additional unreviewed extern boundary")
    provider_reference = (
        "core::ptr::read_volatile(core::ptr::addr_of!(IHK_PROVIDER_LIFECYCLE_V1))"
    )
    if provider_reference not in text or text.count(provider_reference) != 1:
        raise ValidationError("Rust source lacks the exact provider-anchor relocation")

    if (
        "impl kernel::Module for McctrlModule" not in text
        or "impl Drop for McctrlModule" not in text
    ):
        raise ValidationError("Rust source lacks paired mcctrl init and exit lifecycle")
    if (
        "fn init(_module: &'static ThisModule) -> Result<Self>" not in text
        or "Ok(Self)" not in text
    ):
        raise ValidationError("mcctrl foundation must expose its explicit staging init path")
    for phase in ("load", "unload"):
        expected = contract["lifecycle_logs"][phase]
        if f'"{expected}\\n",' not in text:
            raise ValidationError(f"Rust source lacks stable {phase} lifecycle diagnostic")

    forbidden = (
        r'extern\s+"C"',
        r"\bextern\s+crate\b",
        r"\binclude(?:_bytes)?!\s*\(",
        r"\b(?:global_asm|asm)!\s*\(",
        r"\bmodule_param(?:_named)?\s*!?\s*\(",
        r"^\s*params\s*:",
        r"\b(?:insert_binfmt|register_binfmt|__register_binfmt|unregister_binfmt)\s*\(",
        r"binfmt=registered",
    )
    for pattern in forbidden:
        if re.search(pattern, text, re.MULTILINE):
            raise ValidationError(
                f"Rust foundation contains forbidden boundary or claim: {pattern}"
            )
    if re.search(r'b"(?:mcctrl\.)?depends=', text):
        raise ValidationError(
            "Rust source must let modpost derive depends=ihk from the provider symbol"
        )
    for false_log in contract["legacy_lifecycle"].values():
        if false_log in text:
            raise ValidationError("Rust foundation falsely emits a legacy lifecycle success log")
    if re.search(r'b"(?:mcctrl\.)?version=', text):
        raise ValidationError("frozen mcctrl module has no version metadata")
    for match in re.finditer(r"^\s*use\s+([^;]+);", text, re.MULTILINE):
        imported = match.group(1).strip()
        if not imported.startswith(("kernel::", "core::")):
            raise ValidationError(f"unreviewed Rust dependency in mcctrl source: {imported}")


def _validate_provider_source(text: str, contract: dict[str, Any]) -> None:
    symbol = contract["ihk_dependency"]["native_symbol_import"]["provider_symbol"]
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
            raise ValidationError(
                f"native IHK provider anchor lacks required fragment: {fragment}"
            )
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
    if not re.search(r'^\s*tristate\s+"[^"]+"$', block, re.MULTILINE):
        raise ValidationError("mcctrl Kconfig entry must be a tristate")
    dependencies = re.findall(r"^\s*depends on\s+(.+)$", block, re.MULTILINE)
    if dependencies != [contract["kconfig"]["depends_on"]]:
        raise ValidationError(f"mcctrl Kconfig dependency differs: {dependencies}")
    if "depends on RUST" not in text or "depends on X86_64" not in text:
        raise ValidationError("native host-module menu must require Rust and x86_64")


def _validate_kbuild(text: str, contract: dict[str, Any]) -> None:
    try:
        validate_native_rust_kbuild(text)
    except KconfigPolicyError as error:
        raise ValidationError(f"shared native Rust Kbuild policy violation: {error}") from error
    expected = (
        f"obj-$({contract['kbuild']['config_symbol']}) += "
        f"{contract['kbuild']['module_object']}"
    )
    matches = [line.strip() for line in text.splitlines() if line.strip() == expected]
    if len(matches) != 1:
        raise ValidationError(f"Kbuild must contain exactly one {expected!r} mapping")
    if re.search(r"^\s*mcctrl-(?:y|objs)\s*[:+]?=", text, re.MULTILINE):
        raise ValidationError("mcctrl.ko may not use a composite project-object list")
    forbidden_lines = [
        line.strip()
        for line in text.splitlines()
        if re.search(r"\.(?:c|cc|cpp|a|so)\b", line, re.IGNORECASE)
    ]
    if forbidden_lines:
        raise ValidationError(f"Kbuild contains forbidden project inputs: {forbidden_lines}")


def _validate_stage_manifest(
    manifest: dict[str, Any],
    source_path: Path,
    provider_path: Path,
    contract: dict[str, Any],
) -> None:
    build = manifest.get("build_contract", {})
    if build.get("project_c_link_objects") != 0:
        raise ValidationError("stage manifest does not enforce zero project C objects")
    if build.get("allowed_project_source_suffixes") != [".rs"]:
        raise ValidationError("stage manifest permits non-Rust project sources")
    modules = [item for item in manifest.get("modules", []) if item.get("crate") == "mcctrl"]
    if len(modules) != 1:
        raise ValidationError("stage manifest must contain exactly one mcctrl crate")
    module = modules[0]
    if module.get("dependencies") != contract["dependencies"]:
        raise ValidationError("stage manifest mcctrl dependency set differs")
    if module.get("required_import_namespaces") != [
        contract["ihk_dependency"]["required_import_namespace"]
    ]:
        raise ValidationError("stage manifest mcctrl import namespace differs")
    if module.get("kconfig_symbol") != contract["kbuild"]["config_symbol"]:
        raise ValidationError("stage manifest mcctrl Kconfig symbol differs")
    if module.get("output") != contract["module"]["output"]:
        raise ValidationError("stage manifest mcctrl output differs")
    source = module.get("source", {})
    if source.get("repository_path") != contract["production_source"]:
        raise ValidationError("stage manifest points mcctrl at a different source")
    if source.get("sha256") != _sha256(source_path):
        raise ValidationError("stage manifest mcctrl source digest is stale")
    providers = [
        item for item in manifest.get("modules", []) if item.get("crate") == "ihk"
    ]
    if len(providers) != 1:
        raise ValidationError("stage manifest must contain exactly one native IHK provider")
    provider_source = providers[0].get("source", {})
    if provider_source.get("repository_path") != contract["provider_source"]:
        raise ValidationError("stage manifest points at a different native IHK provider")
    if provider_source.get("sha256") != _sha256(provider_path):
        raise ValidationError("stage manifest native IHK provider source digest is stale")


def _validate_reference_inventory(inventory: dict[str, Any], contract: dict[str, Any]) -> None:
    try:
        source = inventory["source_capture"]["modules"]["mcctrl"]
        binary = inventory["binary_capture"]["modules"]["mcctrl"]
    except (KeyError, TypeError) as error:
        raise ValidationError("reference inventory lacks the mcctrl oracle") from error
    parameters = source.get("source_module_parameters")
    if not isinstance(parameters, list) or len(parameters) != contract["parameter_count"]:
        raise ValidationError("reference inventory mcctrl parameter surface differs")

    values = binary.get("modinfo", {}).get("values", {})
    expected = {
        "depends": contract["dependencies"],
        "license": [contract["module"]["license"]],
        "name": [contract["module"]["name"]],
    }
    for field, wanted in expected.items():
        if values.get(field) != wanted:
            raise ValidationError(f"reference inventory mcctrl {field} metadata differs")
    for field in ("author", "description", "parm", "parmtype", "version"):
        if field in values:
            raise ValidationError(f"reference inventory unexpectedly has mcctrl {field} metadata")

    inter_module = binary.get("inter_module_imports")
    if not isinstance(inter_module, list):
        raise ValidationError("reference inventory lacks mcctrl inter-module imports")
    if len(inter_module) != contract["ihk_dependency"]["legacy_inter_module_import_count"]:
        raise ValidationError("reference inventory mcctrl IHK import count differs")
    if any(item.get("provider") != "ihk" for item in inter_module):
        raise ValidationError("reference inventory mcctrl import provider differs")
    symbols = [item.get("symbol") for item in inter_module]
    invalid_symbols = any(
        not isinstance(symbol, str) or not symbol for symbol in symbols
    )
    if invalid_symbols or len(set(symbols)) != len(symbols):
        raise ValidationError("reference inventory mcctrl IHK symbols are invalid")
    imports = binary.get("imports")
    if not isinstance(imports, list):
        raise ValidationError("reference inventory lacks mcctrl binary imports")
    for symbol in contract["binfmt"]["legacy_imports"]:
        if symbol not in imports:
            raise ValidationError(f"reference inventory lacks legacy binfmt import {symbol}")


def _validate_selected_kernel(source_lock: dict[str, Any], contract: dict[str, Any]) -> None:
    target = source_lock.get("target", {})
    if target != {"architecture": "x86_64", "distribution": "Rocky Linux", "release": "10.2"}:
        raise ValidationError("selected source lock is not Rocky Linux 10.2 x86_64")
    selected = contract["selected_kernel"]
    objects = source_lock.get("embedded_objects", [])
    matching = [
        item
        for item in objects
        if item.get("path") == f"SOURCES/linux-{selected['release']}.tar.xz"
    ]
    if len(matching) != 1 or matching[0].get("sha256") != selected["archive_sha256"]:
        raise ValidationError("source lock does not bind the reviewed Linux archive")


def validate_repository(repo: Path, contract_relative: Path = DEFAULT_CONTRACT) -> dict[str, Any]:
    repo = repo.resolve()
    contract_path = _repo_file(repo, contract_relative.as_posix(), "mcctrl lifecycle contract")
    contract = _load_json(contract_path)
    _validate_contract(contract)
    source_path = _repo_file(repo, contract["production_source"], "production Rust source")
    provider_path = _repo_file(repo, contract["provider_source"], "native IHK provider")
    kconfig_path = _repo_file(repo, contract["kconfig"]["path"], "production Kconfig")
    kbuild_path = _repo_file(repo, contract["kbuild"]["path"], "production Kbuild")
    manifest_path = _repo_file(repo, contract["stage_manifest"], "stage manifest")
    inventory_path = _repo_file(repo, contract["reference_inventory"], "legacy inventory")
    source_lock_path = _repo_file(repo, contract["selected_kernel"]["source_lock"], "source lock")

    _validate_rust_source(_read_text(source_path, "production Rust source"), contract)
    _validate_provider_source(_read_text(provider_path, "native IHK provider"), contract)
    _validate_kconfig(_read_text(kconfig_path, "production Kconfig"), contract)
    _validate_kbuild(_read_text(kbuild_path, "production Kbuild"), contract)
    _validate_stage_manifest(
        _load_json(manifest_path), source_path, provider_path, contract
    )
    _validate_reference_inventory(_load_json(inventory_path), contract)
    _validate_selected_kernel(_load_json(source_lock_path), contract)
    return {
        "binfmt_status": contract["binfmt"]["native_registration_status"],
        "dependencies": len(contract["dependencies"]),
        "foundation_status": contract["foundation_status"],
        "artifact_validated": False,
        "built_symbol_reference_validated": False,
        "gate_credit_eligible": False,
        "gate_id": contract["gate_id"],
        "ihk_symbol_import_status": contract["ihk_dependency"]["native_symbol_import"]["status"],
        "module": contract["module"]["name"],
        "parameters": contract["parameter_count"],
        "provider_symbol": contract["ihk_dependency"]["native_symbol_import"][
            "provider_symbol"
        ],
        "required_import_namespace": contract["ihk_dependency"]["required_import_namespace"],
        "rocky_build_load_validated": False,
        "runtime_symbol_reference_proven": False,
        "source_sha256": _sha256(source_path),
        "source_symbol_reference_present": True,
    }


def _modinfo(module_path: Path, field: str | None = None) -> str:
    executable = shutil.which("modinfo")
    if executable is None:
        raise ValidationError("modinfo is required for built-module validation")
    command = [executable]
    if field is None:
        command.append("-p")
    else:
        command.extend(["-F", field])
    command.append(str(module_path))
    result = subprocess.run(command, check=False, capture_output=True, text=True)
    if result.returncode != 0:
        raise ValidationError(
            f"modinfo failed ({result.returncode}): "
            f"{result.stderr.strip() or result.stdout.strip()}"
        )
    return result.stdout.strip()


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
            f"nm -u failed ({result.returncode}): "
            f"{result.stderr.strip() or result.stdout.strip()}"
        )
    return {line.split()[-1] for line in result.stdout.splitlines() if line.split()}


def validate_module_artifact(module_path: Path, summary: dict[str, Any]) -> None:
    module_path = module_path.resolve()
    if module_path.is_symlink() or not module_path.is_file():
        raise ValidationError("built module must be a regular, non-symlink file")
    expected = {
        "author": "",
        "depends": "ihk",
        "description": "",
        "import_ns": summary["required_import_namespace"],
        "license": "GPL v2",
        "name": summary["module"],
        "version": "",
    }
    for field, wanted in expected.items():
        actual = _modinfo(module_path, field)
        if actual != wanted:
            raise ValidationError(
                f"built mcctrl.ko {field} differs: expected {wanted!r}, got {actual!r}"
            )
    if _modinfo(module_path) != "":
        raise ValidationError("built mcctrl.ko unexpectedly exposes module parameters")
    if summary["provider_symbol"] not in _undefined_symbols(module_path):
        raise ValidationError("built mcctrl.ko lacks the provider anchor relocation")
    data = module_path.read_bytes()
    for marker in (
        b"lifecycle=load",
        b"lifecycle=unload",
        b"ihk_import=",
        b"binfmt=",
        b"blocked-no-safe-rust-api",
    ):
        if marker not in data:
            raise ValidationError(f"built mcctrl.ko lacks diagnostic marker {marker!r}")
    summary["artifact_validated"] = True
    summary["built_symbol_reference_validated"] = True


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=ROOT)
    parser.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT)
    parser.add_argument("--module", type=Path, help="also validate a built mcctrl.ko")
    parser.add_argument(
        "--json", action="store_true", help="emit the source-foundation summary as JSON"
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(sys.argv[1:] if argv is None else argv)
    try:
        summary = validate_repository(args.repo, args.contract)
        if args.module is not None:
            validate_module_artifact(args.module, summary)
            summary["artifact"] = str(args.module.resolve())
    except ValidationError as error:
        print(f"mcctrl-native-lifecycle-check: FAIL: {error}", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(summary, sort_keys=True))
    else:
        level = (
            "ARTIFACT-CONTRACT-VERIFIED"
            if summary["artifact_validated"]
            else "SOURCE-CONTRACT-VERIFIED"
        )
        print(
            f"mcctrl-native-lifecycle-check: {level} "
            f"parameters={summary['parameters']} dependencies={summary['dependencies']} "
            f"ihk_symbol_import={summary['ihk_symbol_import_status']} "
            f"binfmt={summary['binfmt_status']} rocky_build_load=NOT_EVALUATED "
            "runtime_symbol_reference=NOT_PROVEN"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
