#!/usr/bin/env python3
"""Validate the native Rust ihk module lifecycle and optional built artifact."""

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


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONTRACT = Path("host-kernel/native-rust/ihk-lifecycle-contract-v1.json")
EXPECTED_SUPPORT_SOURCES = (
    {
        "contract_path": "host-kernel/contracts/x86_64-shared-abi-v1.json",
        "destination": "abi/x86_64.rs",
        "kind": "shared_rust_abi",
        "path": "host-kernel/native-rust/abi/x86_64.rs",
    },
    {
        "contract_path": "host-kernel/contracts/ihk-os-registry-foundation-v1.json",
        "destination": "os_registry.rs",
        "kind": "rust_support_module",
        "path": "host-kernel/native-rust/os_registry.rs",
    },
    {
        "contract_path": "host-kernel/contracts/ihk-ioctl-dispatch-foundation-v1.json",
        "destination": "ihk_ioctl.rs",
        "kind": "rust_ioctl_dispatch",
        "path": "host-kernel/native-rust/ihk_ioctl.rs",
    },
)
HEX64 = re.compile(r"^[0-9a-f]{64}$")


class ValidationError(Exception):
    """Raised when the lifecycle contract is incomplete or inconsistent."""


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


def _repo_file(repo: Path, relative: str, label: str) -> Path:
    if not isinstance(relative, str) or not relative or "\\" in relative:
        raise ValidationError(f"{label} must be a non-empty POSIX path")
    candidate_relative = Path(relative)
    if candidate_relative.is_absolute() or ".." in candidate_relative.parts:
        raise ValidationError(f"{label} escapes the repository: {relative}")
    candidate = repo / candidate_relative
    try:
        info = candidate.lstat()
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


def _require_keys(value: dict[str, Any], expected: set[str], label: str) -> None:
    actual = set(value)
    if actual != expected:
        raise ValidationError(
            f"{label} keys differ: missing={sorted(expected - actual)}, "
            f"extra={sorted(actual - expected)}"
        )


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


def _module_metadata(text: str, field: str) -> str:
    block = re.search(r"module!\s*\{(?P<body>.*?)^\}", text, re.MULTILINE | re.DOTALL)
    if not block:
        raise ValidationError("Rust source lacks a module! entry point")
    match = re.search(
        rf'^\s*{re.escape(field)}:\s*"([^"\\]*)",$',
        block.group("body"),
        re.MULTILINE,
    )
    if not match:
        raise ValidationError(f"module! metadata lacks literal {field}")
    return match.group(1)


def _validate_contract(contract: dict[str, Any]) -> None:
    _require_keys(
        contract,
        {
            "abi_version",
            "crate_modules",
            "dependencies",
            "gate_id",
            "kbuild",
            "kconfig",
            "lifecycle_logs",
            "module",
            "parameter_count",
            "production_source",
            "production_source_sha256",
            "reference_inventory",
            "schema_version",
            "stage_manifest",
            "support_sources",
        },
        "contract",
    )
    if contract["schema_version"] != 1 or contract["gate_id"] != "IHK-001":
        raise ValidationError("unsupported lifecycle contract identity")
    if contract["abi_version"] != 1:
        raise ValidationError("IHK lifecycle ABI version must be 1")
    if contract["dependencies"] != []:
        raise ValidationError("ihk core must have no module dependencies")
    if contract["parameter_count"] != 0:
        raise ValidationError("ihk core must match the legacy zero-parameter surface")
    if contract["production_source"] != "host-kernel/native-rust/ihk.rs":
        raise ValidationError("IHK lifecycle contract redirects the crate root")
    if not isinstance(contract["production_source_sha256"], str) or not HEX64.fullmatch(
        contract["production_source_sha256"]
    ):
        raise ValidationError("IHK lifecycle crate-root digest is malformed")
    expected_modules = [
        {
            "destination": "abi/x86_64.rs",
            "path": "host-kernel/native-rust/abi/x86_64.rs",
            "sha256": "b5980e5b621914a120a0e6b72241477c48aee85615ae4cc76077f3874e35f860",
        },
        {
            "destination": "ikc_queue.rs",
            "path": "host-kernel/native-rust/ikc_queue.rs",
            "sha256": "514f9bce452498e5e9394c450532b040c44fce1ac7a6b5158c76f3d4c7270d40",
        },
        {
            "destination": "ikc_master.rs",
            "path": "host-kernel/native-rust/ikc_master.rs",
            "sha256": "f7e8f8bc1cc860a2eb3724457d81bf03b132fa156eac5c5e258a393808e6ca1e",
        },
    ]
    if contract["crate_modules"] != expected_modules:
        raise ValidationError("IHK lifecycle transitive Rust module graph differs")
    _require_keys(
        contract["module"],
        {"author", "description", "license", "name", "output", "version"},
        "contract.module",
    )
    if contract["module"]["name"] != "ihk" or contract["module"]["output"] != "ihk.ko":
        raise ValidationError("contract must describe the ihk.ko module")
    _require_keys(
        contract["kconfig"], {"path", "symbol", "type"}, "contract.kconfig"
    )
    if contract["kconfig"]["symbol"] != "MCKERNEL_IHK_RUST":
        raise ValidationError("contract Kconfig symbol differs from the production symbol")
    if contract["kconfig"]["type"] != "tristate":
        raise ValidationError("ihk production Kconfig entry must be a tristate")
    _require_keys(
        contract["kbuild"],
        {"config_symbol", "module_object", "path"},
        "contract.kbuild",
    )
    if contract["kbuild"]["config_symbol"] != "CONFIG_MCKERNEL_IHK_RUST":
        raise ValidationError("contract Kbuild symbol differs from the production symbol")
    if contract["kbuild"]["module_object"] != "ihk.o":
        raise ValidationError("contract Kbuild object must be ihk.o")
    _require_keys(contract["lifecycle_logs"], {"load", "unload"}, "contract.lifecycle_logs")


def _validate_rust_source(text: str, contract: dict[str, Any]) -> None:
    for fragment in (
        '#[path = "abi/x86_64.rs"]\nmod abi;',
        "mod ikc_queue;",
        "mod ikc_master;",
        "mod ihk_ioctl;",
    ):
        if text.count(fragment) != 1:
            raise ValidationError(
                f"IHK crate root lacks the exact staged module edge: {fragment}"
            )
    module = contract["module"]
    expected_metadata = {
        "name": module["name"],
        "author": module["author"],
        "description": module["description"],
        "license": module["license"],
    }
    for field, expected in expected_metadata.items():
        actual = _module_metadata(text, field)
        if actual != expected:
            raise ValidationError(
                f"module! {field} differs: expected {expected!r}, got {actual!r}"
            )

    if _rust_string_constant(text, "IHK_VERSION") != module["version"]:
        raise ValidationError("Rust lifecycle version differs from contract")
    if _rust_integer_constant(text, "IHK_ABI_VERSION") != contract["abi_version"]:
        raise ValidationError("Rust lifecycle ABI version differs from contract")
    if _rust_integer_constant(text, "IHK_PARAMETER_COUNT") != contract["parameter_count"]:
        raise ValidationError("Rust parameter count differs from the legacy contract")
    if _rust_integer_constant(text, "IHK_DEPENDENCY_COUNT") != len(contract["dependencies"]):
        raise ValidationError("Rust dependency count differs from the contract")

    version = module["version"]
    for record in (f'version={version}\\0', f'ihk.version={version}\\0'):
        if f'*b"{record}"' not in text:
            raise ValidationError(f"Rust source lacks version modinfo record: {record}")
    if '#[cfg(MODULE)]' not in text or '#[cfg(not(MODULE))]' not in text:
        raise ValidationError("version metadata must cover loadable and built-in forms")

    if "impl kernel::Module for IhkModule" not in text or "impl Drop for IhkModule" not in text:
        raise ValidationError("Rust source lacks paired module init and exit lifecycle")
    if "fn init(_module: &'static ThisModule) -> Result<Self>" not in text or "Ok(Self)" not in text:
        raise ValidationError("ihk init must expose an unconditional dependency-free success path")
    for phase in ("load", "unload"):
        expected = contract["lifecycle_logs"][phase]
        if f'"{expected}\\n"' not in text:
            raise ValidationError(f"Rust source lacks stable {phase} lifecycle log")

    for pattern in (
        r'extern\s+"C"',
        r"\bextern\s+crate\b",
        r"\binclude(?:_bytes)?!\s*\(",
        r"\b(?:global_asm|asm)!\s*\(",
        r"\bmodule_param(?:_named)?\s*!?\s*\(",
        r"^\s*params\s*:",
    ):
        if re.search(pattern, text, re.MULTILINE):
            raise ValidationError(f"Rust lifecycle source contains forbidden boundary: {pattern}")
    for match in re.finditer(r"^\s*use\s+([^;]+);", text, re.MULTILINE):
        imported = match.group(1).strip()
        if not imported.startswith(("kernel::", "core::")):
            raise ValidationError(f"unreviewed Rust dependency in lifecycle source: {imported}")


def _validate_support_sources(
    repo: Path, contract: dict[str, Any], source_text: str
) -> dict[str, Path]:
    support = contract["support_sources"]
    if not isinstance(support, list) or len(support) != len(EXPECTED_SUPPORT_SOURCES):
        raise ValidationError("lifecycle contract must bind the exact IHK Rust support closure")
    paths: dict[str, Path] = {}
    values: dict[str, dict[str, Any]] = {}
    for index, (item, expected) in enumerate(zip(support, EXPECTED_SUPPORT_SOURCES)):
        _require_keys(
            item,
            {"contract_path", "contract_sha256", "destination", "kind", "path", "sha256"},
            f"support_sources[{index}]",
        )
        for field, value in expected.items():
            if item[field] != value:
                raise ValidationError(f"support_sources[{index}].{field} differs from the locked closure")
        for field in ("contract_sha256", "sha256"):
            if not isinstance(item[field], str) or not HEX64.fullmatch(item[field]):
                raise ValidationError(f"support_sources[{index}].{field} is not lowercase SHA-256")
        path = _repo_file(repo, item["path"], f"support_sources[{index}].path")
        contract_path = _repo_file(
            repo, item["contract_path"], f"support_sources[{index}].contract_path"
        )
        if _sha256(path) != item["sha256"] or _sha256(contract_path) != item["contract_sha256"]:
            raise ValidationError(f"support_sources[{index}] digest is stale")
        paths[item["destination"]] = path
        values[item["destination"]] = _load_json(contract_path)

    abi_contract = values["abi/x86_64.rs"]
    capture = abi_contract.get("capture", {})
    abi_item = support[0]
    if capture.get("rust_path") != abi_item["path"] or capture.get("rust_sha256") != abi_item["sha256"]:
        raise ValidationError("shared ABI contract does not bind the staged ABI source")
    if abi_contract.get("readiness", {}).get("credit_eligible") is not False:
        raise ValidationError("shared ABI support contract improperly claims credit")

    registry_contract = values["os_registry.rs"]
    registry_item = support[1]
    implementation = registry_contract.get("implementation", {})
    canonical_abi = registry_contract.get("canonical_abi", {})
    readiness = registry_contract.get("readiness", {})
    if registry_contract.get("gate_id") != "IHK-005-foundation":
        raise ValidationError("OS registry support contract identity differs")
    if implementation.get("path") != registry_item["path"] or implementation.get("sha256") != registry_item["sha256"]:
        raise ValidationError("OS registry contract does not bind the staged source")
    if canonical_abi.get("path") != abi_item["path"] or canonical_abi.get("sha256") != abi_item["sha256"]:
        raise ValidationError("OS registry contract uses a different canonical ABI")
    if readiness.get("status") != "TODO" or readiness.get("credit_eligible") is not False:
        raise ValidationError("OS registry support contract must remain TODO and credit-ineligible")

    ioctl_contract = values["ihk_ioctl.rs"]
    ioctl_item = support[2]
    ioctl_implementation = ioctl_contract.get("implementation", {})
    ioctl_inputs = ioctl_contract.get("canonical_inputs", {})
    ioctl_readiness = ioctl_contract.get("readiness", {})
    if ioctl_contract.get("gate_id") != "IHK-005-ioctl-dispatch-foundation":
        raise ValidationError("ioctl dispatcher support contract identity differs")
    if (ioctl_implementation.get("path") != ioctl_item["path"] or
            ioctl_implementation.get("sha256") != ioctl_item["sha256"]):
        raise ValidationError("ioctl dispatcher contract does not bind the staged source")
    if ioctl_implementation.get("registration_supported") is not False:
        raise ValidationError("ioctl dispatcher contract overclaims device registration")
    if ioctl_implementation.get("user_copy_reachable") is not False:
        raise ValidationError("ioctl dispatcher contract overclaims reachable user copy")
    if ioctl_inputs.get("abi") != {
            "path": abi_item["path"], "sha256": abi_item["sha256"]}:
        raise ValidationError("ioctl dispatcher contract uses a different canonical ABI")
    if ioctl_inputs.get("registry") != {
            "path": registry_item["path"], "sha256": registry_item["sha256"]}:
        raise ValidationError("ioctl dispatcher contract uses a different OS registry")
    if ioctl_readiness.get("status") != "TODO" or ioctl_readiness.get("credit_eligible") is not False:
        raise ValidationError("ioctl dispatcher support contract must remain TODO and credit-ineligible")

    declarations = (
        '#[allow(dead_code, unreachable_pub)]\n#[path = "abi/x86_64.rs"]\nmod abi;',
        "#[allow(dead_code)]\nmod os_registry;",
        "#[allow(dead_code)]\nmod ihk_ioctl;",
    )
    for declaration in declarations:
        if source_text.count(declaration) != 1:
            raise ValidationError(f"ihk crate root lacks unique support declaration: {declaration!r}")
    return paths


def _validate_kconfig(text: str, contract: dict[str, Any]) -> None:
    symbol = contract["kconfig"]["symbol"]
    matches = list(re.finditer(rf"^config {re.escape(symbol)}$", text, re.MULTILINE))
    if len(matches) != 1:
        raise ValidationError(f"Kconfig must define {symbol} exactly once")
    tail = text[matches[0].end() :]
    block = re.split(r"^config |^endmenu$", tail, maxsplit=1, flags=re.MULTILINE)[0]
    if not re.search(r'^\s*tristate\s+"[^"]+"$', block, re.MULTILINE):
        raise ValidationError("ihk Kconfig entry must be a tristate")
    dependencies = re.findall(r"^\s*depends on\s+(.+)$", block, re.MULTILINE)
    if dependencies:
        raise ValidationError(f"ihk Kconfig entry has module dependencies: {dependencies}")
    if "depends on RUST" not in text or "depends on X86_64" not in text:
        raise ValidationError("native host-module menu must require Rust and x86_64")


def _validate_kbuild(text: str, contract: dict[str, Any]) -> None:
    symbol = contract["kbuild"]["config_symbol"]
    module_object = contract["kbuild"]["module_object"]
    expected = f"obj-$({symbol}) += {module_object}"
    lines = [line.strip() for line in text.splitlines() if line.strip() == expected]
    if len(lines) != 1:
        raise ValidationError(f"Kbuild must contain exactly one {expected!r} mapping")
    if re.search(r"^\s*ihk-(?:y|objs)\s*[:+]?=", text, re.MULTILINE):
        raise ValidationError("ihk.ko may not use a composite project-object list")
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
    module_paths: dict[str, Path],
    support_paths: dict[str, Path],
    contract: dict[str, Any],
) -> None:
    build = manifest.get("build_contract", {})
    if build.get("project_c_link_objects") != 0:
        raise ValidationError("stage manifest does not enforce zero project C objects")
    if build.get("allowed_project_source_suffixes") != [".rs"]:
        raise ValidationError("stage manifest permits non-Rust project sources")
    modules = [item for item in manifest.get("modules", []) if item.get("crate") == "ihk"]
    if len(modules) != 1:
        raise ValidationError("stage manifest must contain exactly one ihk crate")
    module = modules[0]
    if module.get("dependencies") != contract["dependencies"]:
        raise ValidationError("stage manifest ihk dependency set differs from contract")
    if module.get("output") != contract["module"]["output"]:
        raise ValidationError("stage manifest ihk output differs from contract")
    source = module.get("source", {})
    if source.get("repository_path") != contract["production_source"]:
        raise ValidationError("stage manifest points ihk at a different production source")
    if source.get("sha256") != _sha256(source_path):
        raise ValidationError("stage manifest ihk source digest is stale")
    inputs = manifest.get("inputs", [])
    by_destination = {
        item.get("destination"): item for item in inputs if isinstance(item, dict)
    }
    for expected in contract["crate_modules"]:
        item = by_destination.get(expected["destination"])
        if item is None:
            raise ValidationError(
                f"stage manifest omits IHK module {expected['destination']}"
            )
        if item.get("repository_path") != expected["path"]:
            raise ValidationError(
                f"stage manifest redirects IHK module {expected['destination']}"
            )
        if item.get("sha256") != _sha256(module_paths[expected["destination"]]):
            raise ValidationError(
                f"stage manifest IHK module digest is stale: {expected['destination']}"
            )
    for support in contract["support_sources"]:
        staged = by_destination.get(support["destination"])
        expected = {
            "destination": support["destination"],
            "kind": support["kind"],
            "repository_path": support["path"],
            "sha256": support["sha256"],
        }
        if staged != expected:
            raise ValidationError(
                f"stage manifest support input differs: {support['destination']}"
            )
        if _sha256(support_paths[support["destination"]]) != support["sha256"]:
            raise ValidationError(f"staged support digest is stale: {support['destination']}")


def _validate_reference_inventory(inventory: dict[str, Any], contract: dict[str, Any]) -> None:
    try:
        parameters = inventory["source_capture"]["modules"]["ihk"]["source_module_parameters"]
    except (KeyError, TypeError) as error:
        raise ValidationError("reference inventory lacks the ihk parameter oracle") from error
    if not isinstance(parameters, list):
        raise ValidationError("reference inventory ihk parameter oracle must be a list")
    if len(parameters) != contract["parameter_count"]:
        raise ValidationError(
            "reference inventory parameter count differs from lifecycle contract: "
            f"expected {contract['parameter_count']}, got {len(parameters)}"
        )


def validate_repository(repo: Path, contract_relative: Path = DEFAULT_CONTRACT) -> dict[str, Any]:
    repo = repo.resolve()
    contract_path = _repo_file(repo, contract_relative.as_posix(), "lifecycle contract")
    contract = _load_json(contract_path)
    _validate_contract(contract)

    source_path = _repo_file(repo, contract["production_source"], "production Rust source")
    module_paths = {
        item["destination"]: _repo_file(repo, item["path"], item["destination"])
        for item in contract["crate_modules"]
    }
    kconfig_path = _repo_file(repo, contract["kconfig"]["path"], "production Kconfig")
    kbuild_path = _repo_file(repo, contract["kbuild"]["path"], "production Kbuild")
    manifest_path = _repo_file(repo, contract["stage_manifest"], "stage manifest")
    inventory_path = _repo_file(
        repo, contract["reference_inventory"], "legacy reference inventory"
    )

    source_text = _read_text(source_path, "production Rust source")
    _validate_rust_source(source_text, contract)
    if _sha256(source_path) != contract["production_source_sha256"]:
        raise ValidationError("IHK lifecycle crate-root digest is stale")
    for item in contract["crate_modules"]:
        if _sha256(module_paths[item["destination"]]) != item["sha256"]:
            raise ValidationError(
                f"IHK lifecycle module digest is stale: {item['destination']}"
            )
    support_paths = _validate_support_sources(repo, contract, source_text)
    _validate_kconfig(_read_text(kconfig_path, "production Kconfig"), contract)
    _validate_kbuild(_read_text(kbuild_path, "production Kbuild"), contract)
    _validate_stage_manifest(
        _load_json(manifest_path), source_path, module_paths, support_paths, contract
    )
    _validate_reference_inventory(_load_json(inventory_path), contract)
    return {
        "abi_version": contract["abi_version"],
        "dependencies": len(contract["dependencies"]),
        "gate_id": contract["gate_id"],
        "module": contract["module"]["name"],
        "parameters": contract["parameter_count"],
        "source_sha256": _sha256(source_path),
        "transitive_module_count": len(module_paths),
        "support_sources": len(support_paths),
        "version": contract["module"]["version"],
    }


def _modinfo(module_path: Path, field: str | None = None) -> str:
    executable = shutil.which("modinfo")
    if executable is None:
        raise ValidationError("modinfo is required for built-module validation")
    command = [executable]
    if field is not None:
        command.extend(["-F", field])
    else:
        command.append("-p")
    command.append(str(module_path))
    result = subprocess.run(command, check=False, capture_output=True, text=True)
    if result.returncode != 0:
        raise ValidationError(
            f"modinfo failed ({result.returncode}): {result.stderr.strip() or result.stdout.strip()}"
        )
    return result.stdout.strip()


def validate_module_artifact(module_path: Path, summary: dict[str, Any]) -> None:
    module_path = module_path.resolve()
    if module_path.is_symlink() or not module_path.is_file():
        raise ValidationError("built module must be a regular, non-symlink file")
    expected = {
        "name": summary["module"],
        "version": summary["version"],
        "license": "GPL v2",
        "depends": "",
    }
    for field, value in expected.items():
        actual = _modinfo(module_path, field)
        if actual != value:
            raise ValidationError(
                f"built module {field} differs: expected {value!r}, got {actual!r}"
            )
    if _modinfo(module_path) != "":
        raise ValidationError("built ihk.ko unexpectedly exposes module parameters")
    data = module_path.read_bytes()
    for phase in ("lifecycle=load", "lifecycle=unload"):
        if phase.encode("ascii") not in data:
            raise ValidationError(f"built ihk.ko lacks {phase} diagnostic string")


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=ROOT)
    parser.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT)
    parser.add_argument("--module", type=Path, help="also validate a built ihk.ko with modinfo")
    parser.add_argument("--json", action="store_true", help="emit the passing summary as JSON")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(sys.argv[1:] if argv is None else argv)
    try:
        summary = validate_repository(args.repo, args.contract)
        if args.module is not None:
            validate_module_artifact(args.module, summary)
            summary["artifact"] = str(args.module.resolve())
    except ValidationError as error:
        print(f"ihk-native-lifecycle-check: FAIL: {error}", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(summary, sort_keys=True))
    else:
        artifact = " artifact=validated" if args.module is not None else " artifact=not-supplied"
        print(
            "ihk-native-lifecycle-check: PASS "
            f"module={summary['module']} version={summary['version']} "
            f"parameters={summary['parameters']} dependencies={summary['dependencies']}"
            f"{artifact}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
