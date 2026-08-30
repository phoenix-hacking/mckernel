#!/usr/bin/env python3
"""Validate the native Rust ihk module lifecycle and optional built artifact."""

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
        "contract_path": "host-kernel/contracts/ihk-device-registry-foundation-v1.json",
        "destination": "device_registry.rs",
        "kind": "rust_support_module",
        "path": "host-kernel/native-rust/device_registry.rs",
    },
    {
        "contract_path": "host-kernel/contracts/ihk-ioctl-dispatch-foundation-v1.json",
        "destination": "ihk_ioctl.rs",
        "kind": "rust_ioctl_dispatch",
        "path": "host-kernel/native-rust/ihk_ioctl.rs",
    },
    {
        "contract_path": "host-kernel/native-rust/ihk-page-allocator-contract-v1.json",
        "destination": "page_allocator.rs",
        "kind": "rust_support_module",
        "path": "host-kernel/native-rust/page_allocator.rs",
    },
    {
        "contract_path": "host-kernel/native-rust/ihk-page-owner-registry-contract-v1.json",
        "destination": "page_owner_registry.rs",
        "kind": "rust_support_module",
        "path": "host-kernel/native-rust/page_owner_registry.rs",
    },
)
EXPECTED_PROVIDER_LEASE = {
    "attach_symbol": "ihk_smp_provider_attach_v2",
    "callback_abi": 1,
    "callback_payload_reachable": False,
    "compatibility_exports": [
        "ihk_smp_provider_attach_v1",
        "ihk_smp_provider_detach_v1",
    ],
    "credit_eligible": False,
    "detach_symbol": "ihk_smp_provider_detach_v2",
    "device_node_reachable": False,
    "import_namespace": "MCKERNEL_IHK_V1",
    "lifecycle_callbacks": {
        "arguments": "none",
        "exit_before_vacate": True,
        "exit_identity_retained": True,
        "init_before_publish": True,
        "operation_callbacks_reachable": False,
        "raw_data_pointer": False,
        "unpublishing_guard_across_exit": True,
    },
    "open_lease": {
        "acquire_failure": "negative-errno",
        "acquire_symbol": "ihk_smp_provider_open_v1",
        "close_failure": "fail-stop",
        "close_symbol": "ihk_smp_provider_close_v1",
        "credit_eligible": False,
        "device_node_reachable": False,
        "duplicate_close_detectable_while_other_references_exist": False,
        "exactly_once_close_owner": "non-Copy-per-file-wrapper",
        "file_operations_reachable": False,
        "minor": 0,
        "multiple_shared_opens": True,
        "raw_pointer": False,
        "receipt": "positive-i64-provider-generation-token",
        "rocky_runtime_validated": False,
        "rust_layout": False,
        "trusted_noncopy_owner_balance_required": True,
    },
    "registry_static": "IHK_DEVICE_REGISTRY",
    "rocky_runtime_validated": False,
    "scope": "scalar minor-zero module-lifetime provider lease, scalar-only init/exit callbacks, and scalar open-reference receipts; no device registration or provider operation payload",
    "token_version": 1,
}
EXPECTED_PROVIDER_OPEN_FFI_SITE = (
    '#[export_name = "ihk_smp_provider_open_v1"]\n'
    "// SAFETY: This exported C ABI carries only a u32 argument and i64 result;\n"
    "// every expected failure becomes a negative errno and no unwind may cross it.\n"
    'pub extern "C" fn ihk_smp_provider_open_v1(minor: u32) -> i64 {'
)
EXPECTED_PROVIDER_CLOSE_FFI_SITE = (
    '#[export_name = "ihk_smp_provider_close_v1"]\n'
    "// SAFETY: This exported C ABI carries only an i64 receipt; detectable ownership\n"
    "// faults fail stop inside the kernel and no unwind may cross the module boundary.\n"
    'pub extern "C" fn ihk_smp_provider_close_v1(receipt: i64) {'
)
HEX64 = re.compile(r"^[0-9a-f]{64}$")
BOUND_MODINFO_ENVIRONMENT = {
    "LANG": "C",
    "LC_ALL": "C",
    "PATH": "/usr/bin:/bin",
    "TZ": "UTC",
}


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


def _blank_rust_span(masked, text, start, end, preserved=()):
    preserved = set(preserved)
    for offset in range(start, end):
        if offset not in preserved and text[offset] not in "\r\n":
            masked[offset] = " "


def _rust_char_literal_end(text, start):
    cursor = start + 1
    if cursor >= len(text) or text[cursor] in "\r\n'":
        return None
    if text[cursor] == "\\":
        cursor += 1
        if cursor >= len(text) or text[cursor] in "\r\n":
            return None
        if text[cursor] == "u" and cursor + 1 < len(text) and text[cursor + 1] == "{":
            closing = text.find("}", cursor + 2)
            if closing < 0:
                return None
            cursor = closing + 1
        elif text[cursor] == "x":
            cursor += 3
        else:
            cursor += 1
    else:
        cursor += 1
    if cursor < len(text) and text[cursor] == "'":
        return cursor + 1
    return None


def _mask_rust_comments_and_literals(text):
    """Return active Rust syntax with comments/literal contents blanked."""

    masked = list(text)
    cursor = 0
    length = len(text)
    while cursor < length:
        if text.startswith("//", cursor):
            end = text.find("\n", cursor + 2)
            if end < 0:
                end = length
            _blank_rust_span(masked, text, cursor, end)
            cursor = end
            continue
        if text.startswith("/*", cursor):
            depth = 1
            end = cursor + 2
            while end < length and depth:
                if text.startswith("/*", end):
                    depth += 1
                    end += 2
                elif text.startswith("*/", end):
                    depth -= 1
                    end += 2
                else:
                    end += 1
            if depth:
                raise ValidationError("unterminated Rust block comment")
            _blank_rust_span(masked, text, cursor, end)
            cursor = end
            continue

        raw_prefix_length = None
        if cursor == 0 or not (text[cursor - 1].isalnum() or text[cursor - 1] == "_"):
            for prefix in ("br", "cr", "r"):
                if text.startswith(prefix, cursor):
                    probe = cursor + len(prefix)
                    while probe < length and text[probe] == "#":
                        probe += 1
                    if probe < length and text[probe] == '"':
                        raw_prefix_length = len(prefix)
                        break
        if raw_prefix_length is not None:
            quote = cursor + raw_prefix_length
            while quote < length and text[quote] == "#":
                quote += 1
            hashes = text[cursor + raw_prefix_length : quote]
            closing = text.find('"' + hashes, quote + 1)
            if closing < 0:
                raise ValidationError("unterminated Rust raw string literal")
            end = closing + 1 + len(hashes)
            _blank_rust_span(masked, text, quote + 1, closing)
            cursor = end
            continue

        if text[cursor] == '"':
            end = cursor + 1
            while end < length:
                if text[end] == "\\":
                    end += 2
                elif text[end] == '"':
                    end += 1
                    break
                else:
                    end += 1
            else:
                raise ValidationError("unterminated Rust string literal")
            _blank_rust_span(masked, text, cursor, end, (cursor, end - 1))
            cursor = end
            continue

        char_start = cursor
        if (
            text[cursor] == "b"
            and cursor + 1 < length
            and text[cursor + 1] == "'"
            and (cursor == 0 or not (text[cursor - 1].isalnum() or text[cursor - 1] == "_"))
        ):
            char_start = cursor + 1
        if text[char_start] == "'":
            end = _rust_char_literal_end(text, char_start)
            if end is not None:
                _blank_rust_span(masked, text, char_start, end)
                cursor = end
                continue
        cursor += 1
    return "".join(masked)


def _active_fragment_positions(text, code, fragment):
    fragment_code = _mask_rust_comments_and_literals(fragment)
    positions = []
    search_from = 0
    while True:
        position = text.find(fragment, search_from)
        if position < 0:
            return positions
        if code[position : position + len(fragment)] == fragment_code:
            positions.append(position)
        search_from = position + 1


def _require_active_count(text, code, fragment, expected, label):
    actual = len(_active_fragment_positions(text, code, fragment))
    if actual != expected:
        raise ValidationError(
            f"{label} active occurrence count differs for {fragment}: "
            f"expected {expected}, got {actual}"
        )


def _require_active_order(text, code, fragments, label):
    cursor = -1
    for fragment in fragments:
        positions = [
            position
            for position in _active_fragment_positions(text, code, fragment)
            if position > cursor
        ]
        if not positions:
            raise ValidationError(f"{label} lacks ordered fragment: {fragment}")
        cursor = positions[0]


def _active_function_body(text, code, signature, label):
    positions = _active_fragment_positions(text, code, signature)
    if len(positions) != 1:
        raise ValidationError(f"{label} signature is not unique active code")
    opening = code.find("{", positions[0] + len(signature))
    if opening < 0:
        raise ValidationError(f"{label} lacks an opening brace")
    depth = 0
    for position in range(opening, len(code)):
        if code[position] == "{":
            depth += 1
        elif code[position] == "}":
            depth -= 1
            if depth == 0:
                return code[opening + 1 : position]
    raise ValidationError(f"{label} lacks a closing brace")


def _require_order(text, fragments, label):
    cursor = -1
    for fragment in fragments:
        cursor = text.find(fragment, cursor + 1)
        if cursor < 0:
            raise ValidationError(f"{label} lacks ordered fragment: {fragment}")


def _rust_string_constant(text: str, name: str) -> str:
    code = _mask_rust_comments_and_literals(text)
    matches = list(re.finditer(
        rf'^const {re.escape(name)}:\s*&str\s*=\s*"([^"\\]*)";$',
        text,
        re.MULTILINE,
    ))
    matches = [
        match for match in matches
        if code[match.start() : match.end()]
        == _mask_rust_comments_and_literals(match.group(0))
    ]
    if len(matches) != 1:
        raise ValidationError(f"Rust source must define literal {name}: &str")
    return matches[0].group(1)


def _rust_integer_constant(text: str, name: str) -> int:
    code = _mask_rust_comments_and_literals(text)
    matches = list(re.finditer(
        rf"^const {re.escape(name)}:\s*(?:u16|usize)\s*=\s*([0-9]+);$",
        text,
        re.MULTILINE,
    ))
    matches = [
        match for match in matches
        if code[match.start() : match.end()] == match.group(0)
    ]
    if len(matches) != 1:
        raise ValidationError(f"Rust source must define literal integer {name}")
    return int(matches[0].group(1))


def _module_metadata(text: str, field: str) -> str:
    code = _mask_rust_comments_and_literals(text)
    starts = list(re.finditer(r"\bmodule!\s*\{", code))
    if len(starts) != 1:
        raise ValidationError("Rust source lacks a module! entry point")
    opening = code.find("{", starts[0].start())
    depth = 0
    closing = None
    for position in range(opening, len(code)):
        if code[position] == "{":
            depth += 1
        elif code[position] == "}":
            depth -= 1
            if depth == 0:
                closing = position
                break
    if closing is None:
        raise ValidationError("Rust module! entry point lacks a closing brace")
    body = text[opening + 1 : closing]
    body_code = code[opening + 1 : closing]
    matches = list(re.finditer(
        rf'^\s*{re.escape(field)}:\s*"([^"\\]*)",$',
        body,
        re.MULTILINE,
    ))
    matches = [
        match for match in matches
        if body_code[match.start() : match.end()]
        == _mask_rust_comments_and_literals(match.group(0))
    ]
    if len(matches) != 1:
        raise ValidationError(f"module! metadata lacks literal {field}")
    return matches[0].group(1)


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
            "provider_lease",
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
    if contract["provider_lease"] != EXPECTED_PROVIDER_LEASE:
        raise ValidationError("IHK provider-lease contract differs or overclaims readiness")
    if not isinstance(contract["production_source_sha256"], str) or not HEX64.fullmatch(
        contract["production_source_sha256"]
    ):
        raise ValidationError("IHK lifecycle crate-root digest is malformed")
    expected_modules = [
        {
            "destination": "abi/x86_64.rs",
            "path": "host-kernel/native-rust/abi/x86_64.rs",
            "sha256": "89e0f72e821cbef91ad4771f4b4b24515d89035d357dc9c23c935a313b7d12c3",
        },
        {
            "destination": "ikc_queue.rs",
            "path": "host-kernel/native-rust/ikc_queue.rs",
            "sha256": "514f9bce452498e5e9394c450532b040c44fce1ac7a6b5158c76f3d4c7270d40",
        },
        {
            "destination": "device_registry.rs",
            "path": "host-kernel/native-rust/device_registry.rs",
            "sha256": "43c3a4badd09bb70a31c9120d23e3b2b63ffa735412d172e0f0ac3d2edc85af5",
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
    code = _mask_rust_comments_and_literals(text)
    for fragment in (
        '#[path = "abi/x86_64.rs"]\nmod abi;',
        "mod ikc_queue;",
        "mod device_registry;",
        "mod ikc_master;",
        "mod ihk_ioctl;",
        "mod page_allocator;",
        "mod page_owner_registry;",
    ):
        _require_active_count(text, code, fragment, 1, "IHK staged module edge")
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
        _require_active_count(
            text, code, f'*b"{record}"', 1, "IHK version modinfo record"
        )
    if '#[cfg(MODULE)]' not in code or '#[cfg(not(MODULE))]' not in code:
        raise ValidationError("version metadata must cover loadable and built-in forms")

    if "impl kernel::Module for IhkModule" not in code or "impl Drop for IhkModule" not in code:
        raise ValidationError("Rust source lacks paired module init and exit lifecycle")
    if "fn init(_module: &'static ThisModule) -> Result<Self>" not in code or "Ok(Self)" not in code:
        raise ValidationError("ihk init must expose an unconditional dependency-free success path")
    for phase in ("load", "unload"):
        expected = contract["lifecycle_logs"][phase]
        _require_active_count(
            text,
            code,
            f'"{expected}\\n"',
            1,
            f"IHK stable {phase} lifecycle log",
        )

    lease = contract["provider_lease"]
    attach = lease["attach_symbol"]
    detach = lease["detach_symbol"]
    compatibility_attach, compatibility_detach = lease["compatibility_exports"]
    open_lease = lease["open_lease"]
    acquire = open_lease["acquire_symbol"]
    close = open_lease["close_symbol"]
    namespace = lease["import_namespace"]
    registry = lease["registry_static"]
    required_provider_fragments = (
        f"use self::device_registry::{{{registry}, SharePolicy}};",
        f'#[export_name = "{compatibility_attach}"]',
        f'pub extern "C" fn {compatibility_attach}() -> i64 {{',
        f"match {registry}.attach_provider_token()",
        'pr_info!("provider_lease=attach status=live minor=0\\n");',
        f'#[export_name = "__export_symbol_{compatibility_attach}"]',
        f"symbol: {compatibility_attach} as *const () as *const u8,",
        f'#[export_name = "{compatibility_detach}"]',
        f'pub extern "C" fn {compatibility_detach}(token: i64) {{',
        f"{registry}.retire_owned_provider_token(token)",
        '"provider_lease=detach status=vacant minor={} generation={}\\n",',
        f'#[export_name = "__export_symbol_{compatibility_detach}"]',
        f"symbol: {compatibility_detach} as *const () as *const u8,",
        "type IhkSmpProviderInitV2 = extern \"C\" fn() -> i32;",
        "type IhkSmpProviderExitV2 = extern \"C\" fn();",
        "static IHK_SMP_PROVIDER_EXIT_V2: AtomicPtr<()>",
        f'#[export_name = "{attach}"]',
        f'pub extern "C" fn {attach}(',
        f"{registry}.reserve(SharePolicy::Shared)",
        'pr_info!("provider_lease=attach status=live minor=0 callback_abi=1\\n");',
        f'#[export_name = "__export_symbol_{attach}"]',
        f"symbol: {attach} as *const () as *const u8,",
        f'#[export_name = "{detach}"]',
        f'pub extern "C" fn {detach}(',
        f"{registry}.snapshot(handle)",
        '"provider_lease=detach status=vacant minor={} generation={} callback_abi=1\\n",',
        f'#[export_name = "__export_symbol_{detach}"]',
        f"symbol: {detach} as *const () as *const u8,",
        f'#[export_name = "{acquire}"]',
        EXPECTED_PROVIDER_OPEN_FFI_SITE,
        f'pub extern "C" fn {acquire}(minor: u32) -> i64 {{',
        f"match {registry}.acquire_open_token(minor as usize)",
        'pr_info!("provider_open=acquire status=live minor=0\\n");',
        f'#[export_name = "__export_symbol_{acquire}"]',
        f"symbol: {acquire} as *const () as *const u8,",
        f'#[export_name = "{close}"]',
        EXPECTED_PROVIDER_CLOSE_FFI_SITE,
        f'pub extern "C" fn {close}(receipt: i64) {{',
        f"let _ = {registry}.release_owned_open_token(receipt);",
        'pr_info!("provider_open=release status=complete minor=0\\n");',
        f'#[export_name = "__export_symbol_{close}"]',
        f"symbol: {close} as *const () as *const u8,",
        f"match {registry}.active_count() {{",
        'Ok(0) => pr_info!("provider_registry=empty active=0\\n"),',
    )
    for fragment in required_provider_fragments:
        _require_active_count(
            text, code, fragment, 1, "IHK provider-lease exact reviewed boundary"
        )
    attach_body = _active_function_body(
        text, code, f'pub extern "C" fn {attach}(', "IHK v2 attach"
    )
    _require_order(
        attach_body,
        (
            "let init_status = provider_init_status(init());",
            "reservation.abort()",
            "IHK_SMP_PROVIDER_EXIT_V2",
            ".compare_exchange(",
            "reservation.publish()",
            f"{registry}.encode_provider_token(handle)",
        ),
        "IHK v2 init-before-publish and failed-init rollback",
    )
    detach_body = _active_function_body(
        text, code, f'pub extern "C" fn {detach}(', "IHK v2 detach"
    )
    _require_order(
        detach_body,
        (
            "IHK_SMP_PROVIDER_EXIT_V2.load(Ordering::Acquire)",
            ".decode_provider_token(token)",
            ".begin_unregister(handle)",
            f"{registry}.snapshot(handle)",
            "snapshot.provider_references != 0 || snapshot.os_references != 0",
            "exit();",
            "unregister.commit()",
            ".compare_exchange(",
        ),
        "IHK v2 unpublish-exit-vacate ordering",
    )
    acquire_body = _active_function_body(
        text, code, f'pub extern "C" fn {acquire}(', "IHK provider open"
    )
    _require_order(
        acquire_body,
        (
            f"{registry}.acquire_open_token(minor as usize)",
            "Err(error)",
            "return error.errno() as i64;",
        ),
        "IHK provider open acquire-or-negative-errno ordering",
    )
    _require_active_order(
        text,
        code,
        (
            f'pub extern "C" fn {acquire}(',
            f"{registry}.acquire_open_token(minor as usize)",
            'pr_info!("provider_open=acquire status=live minor=0\\n");',
            f'#[export_name = "__export_symbol_{acquire}"]',
        ),
        "IHK provider open acquire-before-success ordering",
    )
    close_body = _active_function_body(
        text, code, f'pub extern "C" fn {close}(', "IHK provider close"
    )
    _require_order(
        close_body,
        (f"{registry}.release_owned_open_token(receipt)",),
        "IHK provider fail-stop close-before-success ordering",
    )
    _require_active_order(
        text,
        code,
        (
            f'pub extern "C" fn {close}(',
            f"{registry}.release_owned_open_token(receipt)",
            'pr_info!("provider_open=release status=complete minor=0\\n");',
            f'#[export_name = "__export_symbol_{close}"]',
        ),
        "IHK provider fail-stop close-before-success ordering",
    )
    for forbidden in (
        "UnsafeCell",
        "MaybeUninit",
        "OpenLease<'",
        "core::mem::forget",
    ):
        if forbidden in code:
            raise ValidationError(
                "IHK provider open boundary must remain a stateless scalar adapter"
            )
    if len(_active_fragment_positions(text, code, 'pub extern "C" fn ')) != 6 or len(
        _active_fragment_positions(text, code, 'extern "C"')
    ) != 8:
        raise ValidationError("IHK provider-lease source has an unreviewed C ABI boundary")
    _require_active_count(
        text, code, '#[link_section = ".export_symbol"]', 7,
        "IHK provider relocation record",
    )
    _require_active_count(
        text, code, f'namespace: *b"{namespace}\\0",', 7,
        "IHK provider import namespace",
    )
    _require_active_count(
        text, code, 'license: *b"GPL\\0",', 7, "IHK provider GPL export"
    )
    if code.count(registry) != 12:
        raise ValidationError("IHK provider registry singleton has unexpected reachability")
    if re.search(
        r"pr_(?:info|err|warn)!\s*\([^;]*\b(?:token|receipt)\b",
        code,
        re.MULTILINE | re.DOTALL,
    ):
        raise ValidationError("IHK provider diagnostics must not disclose opaque tokens")
    registry_check = code.index(f"match {registry}.active_count() {{")
    unload_positions = _active_fragment_positions(
        text, code, f'"{contract["lifecycle_logs"]["unload"]}\\n"'
    )
    if len(unload_positions) != 1:
        raise ValidationError("IHK unload lifecycle diagnostic is not unique active code")
    unload_log = unload_positions[0]
    if registry_check >= unload_log:
        raise ValidationError("IHK provider registry must be checked before unload completion")

    for pattern in (
        r"\bextern\s+crate\b",
        r'extern\s+"C"\s*\{',
        r"\binclude(?:_bytes)?!\s*\(",
        r"\b(?:global_asm|asm)!\s*\(",
        r"\bmodule_param(?:_named)?\s*!?\s*\(",
        r"^\s*params\s*:",
    ):
        if re.search(pattern, code, re.MULTILINE):
            raise ValidationError(f"Rust lifecycle source contains forbidden boundary: {pattern}")
    for match in re.finditer(r"^\s*use\s+([^;]+);", code, re.MULTILINE):
        imported = match.group(1).strip()
        if not imported.startswith(("kernel::", "core::")) and imported != (
            "self::device_registry::{IHK_DEVICE_REGISTRY, SharePolicy}"
        ):
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

    device_contract = values["device_registry.rs"]
    device_item = support[2]
    device_source = device_contract.get("production_source", {})
    device_attachment = device_contract.get("attachment_boundary", {})
    device_evidence = device_contract.get("evidence_policy", {})
    device_readiness = device_contract.get("readiness", {})
    if device_contract.get("gate_id") != "IHK-004-device-registry-foundation":
        raise ValidationError("device registry support contract identity differs")
    if device_contract.get("foundation_status") != (
            "production-crate-owned-allocation-free-device-registry-lifecycle-and-open-receipt-boundary"):
        raise ValidationError("device registry support contract differs from the provider-lease boundary")
    if (device_source.get("path") != device_item["path"] or
            device_source.get("sha256") != device_item["sha256"]):
        raise ValidationError("device registry contract does not bind the staged source")
    if device_attachment != {
            "crate_root_constructs_registry_instance": True,
            "crate_root_path": contract["production_source"],
            "crate_root_sha256": contract["production_source_sha256"],
            "crate_root_size": len(source_text.encode("utf-8")),
            "private_module_edge_validated": True,
            "production_registry_static": contract["provider_lease"]["registry_static"],
            "provider_lease_exports": [
                contract["provider_lease"]["compatibility_exports"][0],
                contract["provider_lease"]["compatibility_exports"][1],
                contract["provider_lease"]["attach_symbol"],
                contract["provider_lease"]["detach_symbol"],
                contract["provider_lease"]["open_lease"]["acquire_symbol"],
                contract["provider_lease"]["open_lease"]["close_symbol"],
            ],
    }:
        raise ValidationError("device registry contract differs from crate-root attachment")
    device_lease = device_contract.get("provider_lease_boundary", {})
    if device_lease.get("attach_symbol") != contract["provider_lease"]["attach_symbol"] or (
        device_lease.get("detach_symbol") != contract["provider_lease"]["detach_symbol"]
    ) or device_lease.get("import_namespace") != contract["provider_lease"]["import_namespace"] or (
        device_lease.get("minor") != 0
        or device_lease.get("callback_abi") != contract["provider_lease"]["callback_abi"]
        or device_lease.get("compatibility_exports") != contract["provider_lease"]["compatibility_exports"]
        or device_lease.get("lifecycle_callbacks") != contract["provider_lease"]["lifecycle_callbacks"]
        or device_lease.get("open_close") != {
            "close_return": "void-or-fail-stop",
            "close_symbol": contract["provider_lease"]["open_lease"]["close_symbol"],
            "concurrent_shared_receipts": contract["provider_lease"]["open_lease"]["multiple_shared_opens"],
            "duplicate_close_detectable_while_other_references_exist": contract["provider_lease"]["open_lease"]["duplicate_close_detectable_while_other_references_exist"],
            "open_return": "positive-generation-token-or-negative-errno",
            "open_symbol": contract["provider_lease"]["open_lease"]["acquire_symbol"],
            "raw_pointer": contract["provider_lease"]["open_lease"]["raw_pointer"],
            "source_validated": True,
            "trusted_noncopy_owner_balance_required": contract["provider_lease"]["open_lease"]["trusted_noncopy_owner_balance_required"],
        }
        or device_lease.get("token", {}).get("version") != contract["provider_lease"]["token_version"]
        or device_lease.get("callback_payload_reachable") is not False
        or device_lease.get("device_node_reachable") is not False
        or device_lease.get("runtime_validated") is not False
        or device_lease.get("credit_eligible") is not False
    ):
        raise ValidationError("device registry provider-lease boundary differs or overclaims readiness")
    if device_evidence != {
            "credit_eligible": False,
            "exact_kbuild_validated": False,
            "legacy_differential_validated": False,
            "linux_adapter_validated": False,
            "rocky_runtime_validated": False,
            "source_and_fixture_validated": True,
    }:
        raise ValidationError("device registry support contract improperly claims evidence or credit")
    if (device_readiness.get("status") != "TODO" or
            device_readiness.get("credit_eligible") is not False or
            not isinstance(device_readiness.get("blockers"), list) or
            len(device_readiness["blockers"]) != 8):
        raise ValidationError("device registry support contract must remain TODO and blocked")

    ioctl_contract = values["ihk_ioctl.rs"]
    ioctl_item = support[3]
    device_ioctl = device_contract.get("ioctl_boundary", {})
    if device_ioctl != {
            "contract_path": ioctl_item["contract_path"],
            "contract_sha256": ioctl_item["contract_sha256"],
            "contract_size": (repo / ioctl_item["contract_path"]).stat().st_size,
            "registration_supported": False,
            "user_copy_reachable": False,
    }:
        raise ValidationError("device registry contract uses a different negative ioctl boundary")
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

    allocator_contract = values["page_allocator.rs"]
    allocator_item = support[4]
    allocator_source = allocator_contract.get("production_source", {})
    allocator_evidence = allocator_contract.get("evidence_policy", {})
    if allocator_contract.get("gate_id") != "IHK-006":
        raise ValidationError("page allocator support contract identity differs")
    if allocator_contract.get("foundation_status") != "private-crate-attached-bitmap-page-allocator":
        raise ValidationError("page allocator support contract overclaims attachment readiness")
    if allocator_source != {
            "path": allocator_item["path"], "sha256": allocator_item["sha256"]}:
        raise ValidationError("page allocator contract does not bind the staged source")
    if allocator_evidence != {
            "built_into_ihk_validated": True,
            "differential_legacy_parity_validated": False,
            "exact_kernel_compile_validated": False,
            "failure_injection_validated": False,
            "gate_credit_eligible": False,
            "rocky_runtime_validated": False,
    }:
        raise ValidationError("page allocator support contract improperly claims evidence or credit")

    owner_contract = values["page_owner_registry.rs"]
    owner_item = support[5]
    owner_source = owner_contract.get("production_source", {})
    owner_dependency = owner_contract.get("allocator_dependency", {})
    owner_evidence = owner_contract.get("evidence_policy", {})
    if owner_contract.get("gate_id") != "IHK-006":
        raise ValidationError("page-owner registry support contract identity differs")
    if owner_contract.get("foundation_status") != "private-crate-attached-raw-page-owner-registry":
        raise ValidationError("page-owner registry support contract overclaims attachment readiness")
    if owner_source != {
            "path": owner_item["path"], "sha256": owner_item["sha256"]}:
        raise ValidationError("page-owner registry contract does not bind the staged source")
    if owner_dependency != {
            "contract_path": allocator_item["contract_path"],
            "contract_sha256": allocator_item["contract_sha256"],
            "source_path": allocator_item["path"],
            "source_sha256": allocator_item["sha256"],
    }:
        raise ValidationError("page-owner registry uses a different allocator contract")
    if owner_evidence != {
            "built_into_ihk_validated": True,
            "exact_kernel_compile_validated": False,
            "failure_injection_validated": False,
            "gate_credit_eligible": False,
            "legacy_adapters_validated": False,
            "rocky_runtime_validated": False,
    }:
        raise ValidationError("page-owner registry support contract improperly claims evidence or credit")

    declarations = (
        '#[allow(dead_code, unreachable_pub)]\n#[path = "abi/x86_64.rs"]\nmod abi;',
        "#[allow(dead_code)]\nmod os_registry;",
        "#[allow(dead_code)]\nmod device_registry;",
        "#[allow(dead_code)]\nmod ihk_ioctl;",
        "#[allow(dead_code)]\nmod page_allocator;",
        "#[allow(dead_code)]\nmod page_owner_registry;",
    )
    for declaration in declarations:
        if source_text.count(declaration) != 1:
            raise ValidationError(f"ihk crate root lacks unique support declaration: {declaration!r}")
    return paths


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
        raise ValidationError("ihk Kconfig entry must be a tristate")
    dependencies = re.findall(r"^\s*depends on\s+(.+)$", block, re.MULTILINE)
    if dependencies:
        raise ValidationError(f"ihk Kconfig entry has module dependencies: {dependencies}")
    if "depends on RUST" not in text or "depends on X86_64" not in text:
        raise ValidationError("native host-module menu must require Rust and x86_64")


def _validate_kbuild(text: str, contract: dict[str, Any]) -> None:
    try:
        validate_native_rust_kbuild(text)
    except KconfigPolicyError as error:
        raise ValidationError(f"shared native Rust Kbuild policy violation: {error}") from error
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
        "provider_lease_validated": True,
        "provider_symbols": [
            "ihk_provider_lifecycle_v1",
            contract["provider_lease"]["compatibility_exports"][0],
            contract["provider_lease"]["compatibility_exports"][1],
            contract["provider_lease"]["attach_symbol"],
            contract["provider_lease"]["detach_symbol"],
            contract["provider_lease"]["open_lease"]["acquire_symbol"],
            contract["provider_lease"]["open_lease"]["close_symbol"],
        ],
        "source_sha256": _sha256(source_path),
        "transitive_module_count": len(module_paths),
        "support_sources": len(support_paths),
        "version": contract["module"]["version"],
    }


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
    module_path: Path, field: str | None = None, modinfo_fd: int | None = None
) -> str:
    executable, pass_fds = _modinfo_execution(modinfo_fd)
    command = ["modinfo"]
    if field is not None:
        command.extend(["-F", field])
    else:
        command.append("-p")
    command.append(str(module_path))
    try:
        result = subprocess.run(
            command,
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
            f"modinfo failed ({result.returncode}): {result.stderr.strip() or result.stdout.strip()}"
        )
    return result.stdout.strip()


def _artifact_modinfo(
    module_path: Path, field: str | None, modinfo_fd: int | None
) -> str:
    # Preserve the historical two-argument seam used by the source-only unit
    # tests while making an explicitly supplied descriptor impossible to drop.
    if modinfo_fd is None:
        return _modinfo(module_path, field)
    return _modinfo(module_path, field, modinfo_fd=modinfo_fd)


def _defined_symbols(module_path: Path) -> set[str]:
    executable = shutil.which("nm")
    if executable is None:
        raise ValidationError("nm is required for built-module provider validation")
    result = subprocess.run(
        [executable, "-a", "--defined-only", str(module_path)],
        check=False,
        capture_output=True,
        env=dict(BOUND_MODINFO_ENVIRONMENT),
        text=True,
    )
    if result.returncode != 0:
        raise ValidationError(
            "nm defined-symbol scan failed "
            f"({result.returncode}): {result.stderr.strip() or result.stdout.strip()}"
        )
    return {line.split()[-1] for line in result.stdout.splitlines() if line.split()}


def _validate_provider_export_symbols(
    defined_symbols: set[str], provider_symbols: set[str]
) -> None:
    missing_provider_symbols = sorted(provider_symbols - defined_symbols)
    if missing_provider_symbols:
        raise ValidationError(
            "built ihk.ko lacks provider definitions: "
            + ", ".join(missing_provider_symbols)
        )

    if "__ksymtab" in defined_symbols:
        raise ValidationError("built ihk.ko contains a non-GPL __ksymtab section")

    expected_ksymtab = {f"__ksymtab_{symbol}" for symbol in provider_symbols}
    expected_kstrtab = {f"__kstrtab_{symbol}" for symbol in provider_symbols}
    expected_kstrtabns = {f"__kstrtabns_{symbol}" for symbol in provider_symbols}
    required_export_symbols = (
        expected_ksymtab
        | expected_kstrtab
        | expected_kstrtabns
        | {"__ksymtab_gpl", "__ksymtab_strings"}
    )
    missing_export_symbols = sorted(required_export_symbols - defined_symbols)
    if missing_export_symbols:
        raise ValidationError(
            "built ihk.ko lacks provider GPL export metadata: "
            + ", ".join(missing_export_symbols)
        )

    actual_ksymtab = {
        symbol
        for symbol in defined_symbols
        if symbol.startswith("__ksymtab_")
        and symbol not in {"__ksymtab_gpl", "__ksymtab_strings"}
    }
    actual_kstrtab = {
        symbol for symbol in defined_symbols if symbol.startswith("__kstrtab_")
    }
    actual_kstrtabns = {
        symbol for symbol in defined_symbols if symbol.startswith("__kstrtabns_")
    }
    unexpected_export_symbols = sorted(
        (actual_ksymtab - expected_ksymtab)
        | (actual_kstrtab - expected_kstrtab)
        | (actual_kstrtabns - expected_kstrtabns)
    )
    if unexpected_export_symbols:
        raise ValidationError(
            "built ihk.ko contains unreviewed export metadata: "
            + ", ".join(unexpected_export_symbols)
        )

    provider_definition_pattern = re.compile(
        r"^ihk(?:_smp)?_provider_[A-Za-z0-9_]+$"
    )
    unexpected_provider_definitions = sorted(
        symbol
        for symbol in defined_symbols - provider_symbols
        if provider_definition_pattern.fullmatch(symbol)
    )
    if unexpected_provider_definitions:
        raise ValidationError(
            "built ihk.ko contains unreviewed provider definitions: "
            + ", ".join(unexpected_provider_definitions)
        )


def validate_module_artifact(
    module_path: Path, summary: dict[str, Any], modinfo_fd: int | None = None
) -> None:
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
        actual = _artifact_modinfo(module_path, field, modinfo_fd)
        if actual != value:
            raise ValidationError(
                f"built module {field} differs: expected {value!r}, got {actual!r}"
            )
    if _artifact_modinfo(module_path, None, modinfo_fd) != "":
        raise ValidationError("built ihk.ko unexpectedly exposes module parameters")
    _validate_provider_export_symbols(
        _defined_symbols(module_path), set(summary["provider_symbols"])
    )
    data = module_path.read_bytes()
    namespace_record = (
        EXPECTED_PROVIDER_LEASE["import_namespace"].encode("ascii") + b"\0"
    )
    if namespace_record not in data:
        raise ValidationError("built ihk.ko lacks the reviewed provider namespace bytes")
    for phase in (
        "lifecycle=load",
        "provider_lease=attach",
        "provider_lease=detach",
        "provider_open=acquire",
        "provider_open=release",
        "provider_registry=empty",
        "lifecycle=unload",
    ):
        if phase.encode("ascii") not in data:
            raise ValidationError(f"built ihk.ko lacks {phase} diagnostic string")


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=ROOT)
    parser.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT)
    parser.add_argument("--module", type=Path, help="also validate a built ihk.ko with modinfo")
    parser.add_argument(
        "--modinfo-fd",
        type=int,
        help="inherited descriptor for the identity-bound kmod executable",
    )
    parser.add_argument("--json", action="store_true", help="emit the passing summary as JSON")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(sys.argv[1:] if argv is None else argv)
    try:
        summary = validate_repository(args.repo, args.contract)
        if args.modinfo_fd is not None and args.module is None:
            raise ValidationError("--modinfo-fd requires --module")
        if args.module is not None:
            validate_module_artifact(args.module, summary, args.modinfo_fd)
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
