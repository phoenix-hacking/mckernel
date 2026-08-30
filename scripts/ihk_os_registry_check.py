#!/usr/bin/env python3
"""Fail-closed contract checker for the unattached IHK-005 OS registry.

The checker binds the Rust foundation to exact frozen IHK Git blobs, the
canonical x86_64 status capture, its standalone Rust fixture, and a deterministic
checked-in JSON record.  It deliberately does not claim that the source is
attached, built by Kbuild, or runtime validated.
"""

from __future__ import print_function

import argparse
import ast
import hashlib
import json
import os
import re
import subprocess
import sys


IHK_REF = "3114d9e7101ad52030eb3effa849a5c108972a1f"
RUST_PATH = "host-kernel/native-rust/os_registry.rs"
ABI_PATH = "host-kernel/native-rust/abi/x86_64.rs"
FIXTURE_PATH = "scripts/tests/fixtures/ihk_os_registry_compile.rs"
CONTRACT_PATH = "host-kernel/contracts/ihk-os-registry-foundation-v1.json"

SOURCE_LOCKS = (
    ("host_driver", "linux/core/host_driver.c", 69863,
     "be75185f5b1a0aea84b0be995f67405e45964999b6ed28ae60adb3ed1dece722"),
    ("status", "linux/include/ihk/status.h", 995,
     "fef81cf170da96d41500a572c22e44c272f7110eff815cf43944de0e429d81e7"),
    ("smp_header", "linux/driver/smp/smp-driver.h", 5246,
     "2ae46800be142144f207af794961584efab244b6148a557849843e805e81fdd4"),
    ("smp_driver", "linux/driver/smp/smp-driver.c", 138442,
     "90fefdcb66ecd49cff6d43d2f5b8c13ce28010be2bde8043400cb2baebfa2544"),
    ("smp_status", "linux/driver/smp/arch/x86_64/smp-arch-driver.c", 52592,
     "6ec820741ce6e77e4f60ce4c6b6577ed215a42ecf1a7e30207390ed6d0cbb745"),
)

STATUS_NAMES = (
    "IHK_OS_STATUS_NOT_BOOTED",
    "IHK_OS_STATUS_LOADING",
    "IHK_OS_STATUS_BOOTING",
    "IHK_OS_STATUS_BOOTED",
    "IHK_OS_STATUS_READY",
    "IHK_OS_STATUS_RUNNING",
    "IHK_OS_STATUS_FREEZING",
    "IHK_OS_STATUS_FROZEN",
    "IHK_OS_STATUS_SHUTDOWN",
    "IHK_OS_STATUS_FAILED",
    "IHK_OS_STATUS_HUNGUP",
)

STATUS_VARIANTS = (
    "NotBooted", "Loading", "Booting", "Booted", "Ready", "Running",
    "Freezing", "Frozen", "Shutdown", "Failed", "Hungup",
)

TRANSITION_MASKS = (6, 257, 1848, 1840, 2016, 1984, 1952, 1888, 1, 257, 769)

ERRNO_MAP = {
    "Busy": -16,
    "Capacity": -12,
    "Corrupt": -117,
    "GenerationExhausted": -75,
    "InvalidMinor": -22,
    "InvalidTransition": -22,
    "NotFound": -2,
    "ReferenceOverflow": -75,
    "StaleHandle": -116,
}

READINESS_BLOCKERS = (
    "the registry is privately attached to ihk.rs, but create/destroy entry points are not wired",
    "exact Rocky Linux 6.12 Kbuild and module-load evidence for this source is absent",
    "legacy create/destroy callbacks, cdev publication, kmsg ownership, and device teardown are not connected",
    "the transition graph and errno bridge require independent review against runtime provider behavior",
)


class ContractError(Exception):
    pass


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def _read(repo_root, relative):
    if not isinstance(relative, str) or not relative or "\\" in relative:
        raise ContractError("invalid repository path: {0!r}".format(relative))
    parts = relative.split("/")
    if relative.startswith("/") or ".." in parts or "." in parts:
        raise ContractError("repository path escapes root: {0}".format(relative))
    root = os.path.realpath(repo_root)
    path = os.path.join(root, *parts)
    if os.path.islink(path) or not os.path.isfile(path):
        raise ContractError("repository input is not a regular file: {0}".format(relative))
    if os.path.commonpath((root, os.path.realpath(path))) != root:
        raise ContractError("repository input resolves outside root: {0}".format(relative))
    try:
        with open(path, "rb") as stream:
            return stream.read()
    except (OSError, IOError) as error:
        raise ContractError("cannot read {0}: {1}".format(relative, error))


def _git_blob(repo_root, ref, path):
    ihk = os.path.join(repo_root, "ihk")
    if not os.path.isdir(ihk):
        raise ContractError("frozen IHK submodule is not initialized")
    process = subprocess.Popen(
        ["git", "show", ref + ":" + path], cwd=ihk,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    output, error = process.communicate()
    if process.returncode:
        raise ContractError("cannot read frozen IHK blob {0}:{1}: {2}".format(
            ref, path, error.decode("utf-8", "replace").strip()))
    return output


def load_legacy_sources(repo_root, overrides=None):
    result = {}
    overrides = overrides or {}
    for source_id, path, size, digest in SOURCE_LOCKS:
        data = overrides.get(source_id)
        if data is None:
            data = _git_blob(repo_root, IHK_REF, path)
        if len(data) != size or _sha(data) != digest:
            raise ContractError("frozen legacy source lock mismatch: {0}".format(source_id))
        result[source_id] = data
    return result


def _text(data, label):
    try:
        return data.decode("utf-8")
    except UnicodeError as error:
        raise ContractError("{0} is not UTF-8: {1}".format(label, error))


def _without_comments(value):
    return re.sub(r"/\*.*?\*/|//[^\n]*", "", value, flags=re.DOTALL)


def _require_pattern(text, pattern, label):
    if not re.search(pattern, text, re.MULTILINE | re.DOTALL):
        raise ContractError("missing locked behavior: {0}".format(label))


def _status_values(text):
    clean = _without_comments(text)
    match = re.search(r"enum\s+ihk_os_status\s*\{(.*?)\}\s*;", clean, re.DOTALL)
    if not match:
        raise ContractError("frozen status enum is absent")
    values = {}
    current = -1
    for raw in match.group(1).split(","):
        item = raw.strip()
        if not item:
            continue
        parts = item.split("=", 1)
        name = parts[0].strip()
        current = int(parts[1].strip(), 0) if len(parts) == 2 else current + 1
        values[name] = current
    expected = dict((name, index) for index, name in enumerate(STATUS_NAMES + ("IHK_OS_STATUS_COUNT",)))
    if values != expected:
        raise ContractError("frozen status values differ from the canonical 0..11 sequence")
    return dict((name, values[name]) for name in STATUS_NAMES)


def _validate_legacy(sources):
    host = _text(sources["host_driver"], "host_driver")
    status = _text(sources["status"], "status")
    smp_header = _text(sources["smp_header"], "smp_header")
    smp_driver = _text(sources["smp_driver"], "smp_driver")
    smp_status = _text(sources["smp_status"], "smp_status")
    values = _status_values(status)

    for pattern, label in (
        (r"^#define\s+OS_MAX_MINOR\s+64$", "64-entry legacy OS table"),
        (r"^#define\s+OS_DATA_INVALID\s+\(\(void \*\)-1\)$", "in-progress sentinel"),
        (r"os_data\[OS_MAX_MINOR\]", "fixed OS slot array"),
        (r"for \(i = 0; i < os_max_minor; i\+\+\).*?if \(!os_data\[i\]\).*?break;", "first-free scan"),
        (r"if \(os_max_minor >= OS_MAX_MINOR\).*?return -ENOMEM;", "capacity errno"),
        (r"os_data\[minor\] = OS_DATA_INVALID;", "exclusive create reservation"),
        (r"__ihk_device_create_os_init.*?os_data\[minor\] = NULL;.*?return ret;", "create rollback"),
        (r"atomic_read\(&os->refcount\) > 0.*?ret = -EBUSY;", "busy destroy"),
        (r"os_data\[os->minor\] = NULL;", "destroy release"),
    ):
        _require_pattern(host, pattern, label)

    internal = {
        "BUILTIN_OS_STATUS_INITIAL": 0,
        "BUILTIN_OS_STATUS_LOADING": 1,
        "BUILTIN_OS_STATUS_BOOTING": 3,
        "BUILTIN_OS_STATUS_SHUTDOWN": 4,
        "BUILTIN_OS_STATUS_HUNGUP": 5,
    }
    for name, value in internal.items():
        _require_pattern(
            smp_header,
            r"^#define\s+{0}\s+{1}(?:\s|$)".format(name, value),
            "SMP internal status {0}".format(name))

    for name in STATUS_NAMES:
        _require_pattern(smp_status, r"\b{0}\b".format(name),
                         "SMP observable status {0}".format(name))
    _require_pattern(smp_status, r"switch \(status\).*?case BUILTIN_OS_STATUS_INITIAL:.*?IHK_OS_STATUS_NOT_BOOTED", "SMP initial mapping")
    _require_pattern(smp_status, r"os->param->status == 1.*?IHK_OS_STATUS_BOOTED.*?os->param->status == 2.*?IHK_OS_STATUS_READY.*?os->param->status == 3.*?IHK_OS_STATUS_RUNNING", "SMP boot progress mapping")
    _require_pattern(smp_status, r"IHK_OS_MONITOR_KERNEL_FREEZING.*?IHK_OS_STATUS_FREEZING", "freeze monitor mapping")
    _require_pattern(smp_status, r"IHK_OS_MONITOR_KERNEL_FROZEN.*?IHK_OS_STATUS_FROZEN", "frozen monitor mapping")
    _require_pattern(smp_driver, r"static int smp_ihk_os_boot.*?set_os_status\(os, BUILTIN_OS_STATUS_BOOTING\).*?revert_os_status:.*?set_os_status\(os, BUILTIN_OS_STATUS_INITIAL\)", "boot publication and rollback")
    _require_pattern(smp_driver, r"static int smp_ihk_os_load_file.*?os->status = BUILTIN_OS_STATUS_LOADING;.*?set_os_status\(os, BUILTIN_OS_STATUS_INITIAL\)", "load transition and rollback")
    _require_pattern(smp_driver, r"static int smp_ihk_os_shutdown.*?set_os_status\(os, BUILTIN_OS_STATUS_SHUTDOWN\).*?set_os_status\(os, BUILTIN_OS_STATUS_INITIAL\)", "shutdown transition and completion")
    _require_pattern(smp_driver, r"smp_ihk_os_notify_hungup.*?set_os_status\(os, BUILTIN_OS_STATUS_HUNGUP\)", "hungup transition")
    return values


def _numeric(node):
    if isinstance(node, ast.Expression):
        return _numeric(node.body)
    if hasattr(ast, "Constant") and isinstance(node, ast.Constant):
        if isinstance(node.value, int):
            return node.value
    if sys.version_info < (3, 8) and isinstance(node, ast.Num):
        return node.n
    if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.LShift, ast.BitOr)):
        left = _numeric(node.left)
        right = _numeric(node.right)
        return left << right if isinstance(node.op, ast.LShift) else left | right
    raise ContractError("unsupported transition-mask expression")


def _transition_masks(rust):
    match = re.search(
        r"const ALLOWED_TRANSITIONS:\s*\[u16;\s*11\]\s*=\s*\[(.*?)\];",
        rust, re.DOTALL)
    if not match:
        raise ContractError("Rust source lacks an explicit 11-state transition matrix")
    body = _without_comments(match.group(1))
    expressions = [item.strip() for item in body.split(",") if item.strip()]
    try:
        masks = tuple(_numeric(ast.parse(item, mode="eval")) for item in expressions)
    except (SyntaxError, ValueError, TypeError) as error:
        raise ContractError("cannot parse transition matrix: {0}".format(error))
    if masks != TRANSITION_MASKS:
        raise ContractError("Rust transition matrix differs from the reviewed foundation")
    return masks


def _validate_abi(abi, expected_statuses):
    text = _text(abi, "canonical ABI")
    for name, value in sorted(expected_statuses.items()):
        pattern = r"^pub const {0}: i32 = {1};$".format(name, value)
        _require_pattern(text, pattern, "canonical ABI {0}".format(name))


def _validate_rust(data, expected_statuses):
    rust = _text(data, "OS registry Rust source")
    forbidden = (
        (r"\bunsafe\b", "unsafe code"),
        (r"extern\s+\"C\"", "C FFI"),
        (r"\b(?:alloc|std|kernel)::", "non-core dependency"),
        (r"\b(?:Box|Vec|String|Arc|Rc)::", "allocation"),
        (r"\binclude(?:_bytes)?!\s*\(", "textual source inclusion"),
        (r"\b(?:global_asm|asm)!\s*\(", "assembly escape hatch"),
    )
    for pattern, label in forbidden:
        if re.search(pattern, rust):
            raise ContractError("OS registry contains forbidden {0}".format(label))

    _require_pattern(rust, r"^pub\(crate\) const OS_CAPACITY: usize = 64;$", "exact 64-slot capacity")
    _require_pattern(rust, r"slots:\s*\[Slot; OS_CAPACITY\]", "allocation-free slot array")
    _require_pattern(rust, r"word:\s*AtomicU64", "atomic slot word")
    _require_pattern(rust, r"^const GENERATION_SHIFT: u32 = 23;$", "generation field")
    _require_pattern(rust, r"^const MAX_GENERATION: u64 = u64::MAX >> GENERATION_SHIFT;$", "non-wrapping generation ceiling")
    _require_pattern(rust, r"PHASE_RETIRED", "permanent generation retirement")
    _require_pattern(rust, r"old_generation == MAX_GENERATION", "generation exhaustion check")
    _require_pattern(rust, r"impl Drop for ReservationGuard", "create rollback guard")
    _require_pattern(rust, r"impl Drop for DestroyGuard", "destroy rollback guard")
    _require_pattern(rust, r"references\(current\) != 0.*?RegistryError::Busy", "busy-reference destroy exclusion")
    _require_pattern(rust, r"generation\(current\) != handle.generation.*?RegistryError::StaleHandle", "stale-handle rejection")
    if rust.count("compare_exchange(") < 8:
        raise ContractError("registry lacks complete atomic publication/exclusion surfaces")

    for index, name in enumerate(STATUS_NAMES):
        variant = STATUS_VARIANTS[index]
        _require_pattern(rust, r"\b{0}\b".format(name), "canonical status import {0}".format(name))
        _require_pattern(rust, r"{0}\s*=\s*{1},".format(variant, index), "Rust status discriminant {0}".format(variant))
        _require_pattern(rust, r"OsStatus::{0} as usize.*?{1} as usize".format(variant, name), "status ABI assertion {0}".format(name))
        if expected_statuses[name] != index:
            raise ContractError("legacy status value differs from Rust discriminant")
    _require_pattern(
        rust,
        r"ALLOWED_TRANSITIONS\.len\(\).*?IHK_OS_STATUS_COUNT as usize",
        "canonical status-count assertion")
    return _transition_masks(rust)


def _validate_fixture(data):
    fixture = _text(data, "OS registry fixture")
    for marker in (
        "#![cfg_attr(not(test), no_std)]",
        "../../../host-kernel/native-rust/abi/x86_64.rs",
        "../../../host-kernel/native-rust/os_registry.rs",
        "exact_capacity_first_fit_and_generation_reuse",
        "reservation_and_destroy_guards_rollback",
        "references_exclude_destroy_and_release_on_drop",
        "reference_counter_overflow_fails_closed",
        "explicit_state_graph_accepts_only_reviewed_edges",
        "concurrent_reservations_are_exclusive_and_complete",
        "concurrent_churn_never_revives_an_old_handle",
        "errno_mapping_is_stable_and_minor_bounds_fail_closed",
    ):
        if marker not in fixture:
            raise ContractError("standalone fixture lacks locked marker: {0}".format(marker))


def derive_contract(repo_root, rust_override=None, abi_override=None,
                    fixture_override=None, legacy_overrides=None):
    sources = load_legacy_sources(repo_root, legacy_overrides)
    statuses = _validate_legacy(sources)
    rust = rust_override if rust_override is not None else _read(repo_root, RUST_PATH)
    abi = abi_override if abi_override is not None else _read(repo_root, ABI_PATH)
    fixture = fixture_override if fixture_override is not None else _read(repo_root, FIXTURE_PATH)
    _validate_abi(abi, statuses)
    transitions = _validate_rust(rust, statuses)
    _validate_fixture(fixture)

    return {
        "behavior": {
            "capacity_errno": -12,
            "create_reservation": "exclusive-first-free-with-rollback",
            "destroy_policy": "exclusive-and-reference-free-with-rollback",
            "errno_map": ERRNO_MAP,
            "generation_policy": "41-bit-monotonic-per-minor-retire-before-wrap",
            "status_transition_masks": list(transitions),
        },
        "canonical_abi": {
            "path": ABI_PATH,
            "sha256": _sha(abi),
            "status_values": statuses,
        },
        "fixture": {
            "edition": "2021",
            "minimum_rustc": "1.92.0",
            "no_std_library_mode": True,
            "path": FIXTURE_PATH,
            "sha256": _sha(fixture),
            "test_count": 8,
        },
        "gate_id": "IHK-005-foundation",
        "implementation": {
            "allocation_free": True,
            "capacity": 64,
            "ffi_free": True,
            "generation_bits": 41,
            "path": RUST_PATH,
            "sha256": _sha(rust),
            "size": len(rust),
            "slot_atomic_bits": 64,
        },
        "legacy_capture": {
            "ihk_ref": IHK_REF,
            "sources": [
                {
                    "id": source_id,
                    "path": path,
                    "sha256": digest,
                    "size": size,
                }
                for source_id, path, size, digest in SOURCE_LOCKS
            ],
        },
        "readiness": {
            "blockers": list(READINESS_BLOCKERS),
            "credit_eligible": False,
            "status": "TODO",
        },
        "schema_version": 1,
    }


def render_contract(contract):
    return (json.dumps(contract, indent=2, sort_keys=True, separators=(",", ": ")) + "\n").encode("utf-8")


def check(repo_root, rust_override=None, abi_override=None,
          fixture_override=None, legacy_overrides=None, contract_override=None):
    expected = derive_contract(
        repo_root,
        rust_override=rust_override,
        abi_override=abi_override,
        fixture_override=fixture_override,
        legacy_overrides=legacy_overrides)
    actual = contract_override if contract_override is not None else _read(repo_root, CONTRACT_PATH)
    if actual != render_contract(expected):
        raise ContractError("checked-in OS registry contract differs from deterministic capture")
    return expected


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    parser.add_argument("--print-contract", action="store_true")
    arguments = parser.parse_args(argv)
    try:
        contract = derive_contract(arguments.repo) if arguments.print_contract else check(arguments.repo)
    except ContractError as error:
        print("IHK OS registry contract: FAIL: {0}".format(error), file=sys.stderr)
        return 1
    if arguments.print_contract:
        sys.stdout.write(render_contract(contract).decode("utf-8"))
    else:
        print("IHK OS registry contract: OK (TODO; no credit)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
