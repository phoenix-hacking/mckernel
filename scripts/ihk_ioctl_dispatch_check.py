#!/usr/bin/env python3
"""Fail-closed checker for the IHK-005 scalar ioctl dispatcher foundation.

The contract binds an allocation-free Rust decoder/transaction core to the
frozen IHK ioctl implementation and to the exact Rocky Linux 6.12 Rust API
audit.  The selected kernel exposes ioctl-number and user-access helpers but
does not expose a supported Rust file-operations or character-device
registration surface.  This checker therefore rejects registration, FFI, and
user-copy wiring and keeps the checkpoint TODO and credit-ineligible.
"""

from __future__ import print_function

import argparse
import hashlib
import json
import os
import re
import stat
import subprocess
import sys


IHK_REF = "3114d9e7101ad52030eb3effa849a5c108972a1f"
RUST_PATH = "host-kernel/native-rust/ihk_ioctl.rs"
REGISTRY_PATH = "host-kernel/native-rust/os_registry.rs"
ABI_PATH = "host-kernel/native-rust/abi/x86_64.rs"
CRATE_ROOT_PATH = "host-kernel/native-rust/ihk.rs"
FIXTURE_PATH = "scripts/tests/fixtures/ihk_ioctl_dispatch_compile.rs"
ROCKY_FIXTURE_ROOT = "scripts/tests/fixtures/rust-core-rocky-6.12"
SOURCE_LOCK_PATH = "host-kernel/rocky/source-lock.json"
CONTRACT_PATH = "host-kernel/contracts/ihk-ioctl-dispatch-foundation-v1.json"

LEGACY_SOURCES = (
    ("host_user", "linux/include/ihk/ihk_host_user.h", 5704,
     "2335260024075a08becbe74651162a950aee8bea603e9a451cb8bcae3aa0ef97"),
    ("host_driver", "linux/core/host_driver.c", 69863,
     "be75185f5b1a0aea84b0be995f67405e45964999b6ed28ae60adb3ed1dece722"),
)

ROCKY_RUST_SOURCES = (
    ("crate_exports", "rust/kernel/lib.rs", 4089,
     "730fce907dbd8c48439f63f506d9400ceb707282846f1e325822c77dc99a56f0"),
    ("ioctl_numbers", "rust/kernel/ioctl.rs", 2062,
     "5825ea4fa49271407d85d6be03f03419431732fc6534cd0e6d551aa29dd8f085"),
    ("user_access", "rust/kernel/uaccess.rs", 14314,
     "e0127f615c717909d31042f8f7decef96bbbb72f6987579954cb9036774bdf07"),
)

COMMANDS = {
    "IHK_DEVICE_CREATE_OS": 0x00112900,
    "IHK_DEVICE_DESTROY_OS": 0x00112901,
    "IHK_OS_QUERY_STATUS": 0x00112A03,
    "IHK_OS_STATUS": 0x00112A14,
}

ERRNO_MAP = {
    "Busy": -16,
    "Capacity": -12,
    "Corrupt": -117,
    "InvalidArgument": -22,
    "MissingOs": -2,
    "Overflow": -75,
    "StaleHandle": -116,
}

READINESS_BLOCKERS = (
    "exact Rocky Linux 6.12 has no supported Rust miscdevice, cdev, file_operations, or ioctl callback registration API",
    "the privately attached decoder has no userspace-reachable registration or file-operation adapter",
    "safe UserSlice copy primitives exist, but no supported ioctl callback can supply a userspace argument to them",
    "legacy provider callbacks, kmsg ownership, cdev publication, device-model publication, and teardown are not connected",
    "exact Kbuild, module-load, ioctl, and teardown runtime evidence for this dispatcher is absent",
)

EXPECTED_RUSTC = "rustc 1.92.0 (ded5c06cf 2025-12-08) (Red Hat 1.92.0-1.el10)"


class ContractError(Exception):
    pass


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def _safe_file(root, relative, label):
    if not isinstance(relative, str) or not relative or "\\" in relative:
        raise ContractError("{0} is not a normalized path".format(label))
    parts = relative.split("/")
    if relative.startswith("/") or any(part in ("", ".", "..") for part in parts):
        raise ContractError("{0} escapes its root".format(label))
    root = os.path.realpath(root)
    path = os.path.join(root, *parts)
    resolved = os.path.realpath(path)
    try:
        inside = os.path.commonpath((root, resolved)) == root
    except ValueError:
        inside = False
    if not inside or resolved != path:
        raise ContractError("{0} escapes or traverses a symlink".format(label))
    try:
        info = os.lstat(path)
    except OSError as error:
        raise ContractError("{0} is unavailable: {1}".format(label, error))
    if stat.S_ISLNK(info.st_mode) or not stat.S_ISREG(info.st_mode):
        raise ContractError("{0} must be a regular non-symlink file".format(label))
    return path


def _read(root, relative, label=None):
    path = _safe_file(root, relative, label or relative)
    try:
        with open(path, "rb") as stream:
            return stream.read()
    except (IOError, OSError) as error:
        raise ContractError("cannot read {0}: {1}".format(label or relative, error))


def _text(data, label):
    try:
        return data.decode("utf-8")
    except UnicodeError as error:
        raise ContractError("{0} is not UTF-8: {1}".format(label, error))


def _git_blob(repo_root, path):
    ihk = os.path.join(repo_root, "ihk")
    if not os.path.isdir(ihk):
        raise ContractError("frozen IHK submodule is not initialized")
    process = subprocess.Popen(
        ["git", "show", IHK_REF + ":" + path], cwd=ihk,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    output, error = process.communicate()
    if process.returncode:
        raise ContractError("cannot read frozen IHK blob {0}: {1}".format(
            path, error.decode("utf-8", "replace").strip()))
    return output


def load_legacy_sources(repo_root, overrides=None):
    values = {}
    overrides = overrides or {}
    for source_id, path, size, digest in LEGACY_SOURCES:
        data = overrides.get(source_id)
        if data is None:
            data = _git_blob(repo_root, path)
        if len(data) != size or _sha(data) != digest:
            raise ContractError("frozen legacy source lock mismatch: {0}".format(source_id))
        values[source_id] = data
    return values


def _require(text, pattern, label):
    if not re.search(pattern, text, re.MULTILINE | re.DOTALL):
        raise ContractError("missing locked behavior: {0}".format(label))


def _c_function(text, name):
    match = re.search(r"\b{0}\s*\([^;]*?\)\s*\{{".format(re.escape(name)), text, re.DOTALL)
    if not match:
        raise ContractError("frozen C function is absent: {0}".format(name))
    start = match.end() - 1
    depth = 0
    for index in range(start, len(text)):
        if text[index] == "{":
            depth += 1
        elif text[index] == "}":
            depth -= 1
            if depth == 0:
                return text[start:index + 1]
    raise ContractError("frozen C function is unterminated: {0}".format(name))


def _validate_legacy(sources):
    header = _text(sources["host_user"], "frozen ioctl header")
    host = _text(sources["host_driver"], "frozen host driver")
    for name, value in sorted(COMMANDS.items()):
        _require(
            header,
            r"^#define\s+{0}\s+0x{1:x}$".format(name, value),
            "legacy command {0}".format(name))
    _require(host, r"^#define\s+OS_MAX_MINOR\s+64$", "64-minor legacy capacity")

    device = _c_function(host, "ihk_host_device_ioctl")
    _require(device, r"int ret = -EINVAL;", "unknown device ioctl errno")
    _require(
        device,
        r"case IHK_DEVICE_CREATE_OS:\s*ret = __ihk_device_create_os\(data, arg\);",
        "scalar create dispatch")
    _require(
        device,
        r"case IHK_DEVICE_DESTROY_OS:.*?arg > OS_MAX_MINOR.*?!os_data\[arg\].*?return ret;.*?__ihk_device_destroy_os",
        "scalar destroy lookup and EINVAL")

    create = _c_function(host, "__ihk_device_create_os")
    _require(create, r"for \(i = 0; i < os_max_minor; i\+\+\).*?if \(!os_data\[i\]\)", "first-free create")
    _require(create, r"os_max_minor >= OS_MAX_MINOR.*?return -ENOMEM;", "create capacity errno")
    _require(create, r"os_data\[minor\] = OS_DATA_INVALID;", "exclusive create reservation")
    _require(create, r"__ihk_device_create_os_init\(data, &os, arg\).*?os_data\[minor\] = NULL;", "create argument and rollback")

    create_init = _c_function(host, "__ihk_device_create_os_init")
    _require(create_init, r"data->ops->create_os\(data, data->priv, arg,\s*os, &drv_data\)", "provider argument forwarding")

    destroy = _c_function(host, "__ihk_device_destroy_os")
    _require(destroy, r"atomic_read\(&os->refcount\) > 0.*?ret = -EBUSY;", "busy destroy")
    _require(destroy, r"data->ops->destroy_os.*?if \(ret\).*?ret = -EINVAL;", "provider destroy errno mapping")
    _require(destroy, r"os_data\[os->minor\] = NULL;", "destroy publication")

    status = _c_function(host, "__ihk_os_status")
    _require(status, r"return __ihk_os_query_status\(data\);", "status alias")
    os_ioctl = _c_function(host, "ihk_host_os_ioctl")
    _require(os_ioctl, r"int ret = -EINVAL;", "unknown OS ioctl errno")
    _require(os_ioctl, r"case IHK_OS_QUERY_STATUS:\s*ret = __ihk_os_query_status\(data\);", "query status return")
    _require(os_ioctl, r"case IHK_OS_STATUS:\s*ret = __ihk_os_status\(data\);", "status return")

    for label, body in (
            ("create", create), ("create_init", create_init),
            ("destroy", destroy), ("status", status)):
        if re.search(r"\bcopy_(?:from|to)_user\b", body):
            raise ContractError("legacy {0} subset unexpectedly copies pointed user data".format(label))


def _validate_abi(data):
    text = _text(data, "canonical ABI")
    for name, value in sorted(COMMANDS.items()):
        _require(
            text,
            r"^pub const {0}: u32 = 0x[0-9a-fA-F_]+;$".format(name),
            "canonical ABI constant {0}".format(name))
        match = re.search(
            r"^pub const {0}: u32 = (0x[0-9a-fA-F_]+);$".format(name),
            text, re.MULTILINE)
        if match is None or int(match.group(1).replace("_", ""), 16) != value:
            raise ContractError("canonical ABI value differs: {0}".format(name))


def _validate_rust(data):
    text = _text(data, "IHK ioctl Rust source")
    for pattern, label in (
            (r"\bunsafe\b", "unsafe code"),
            (r"extern\s+\"C\"", "C FFI"),
            (r"\b(?:alloc|std|kernel|bindings)::", "non-core or kernel API dependency"),
            (r"\b(?:Box|Vec|String|Arc|Rc)::", "allocation"),
            (r"\binclude(?:_bytes)?!\s*\(", "textual inclusion"),
            (r"\b(?:global_asm|asm)!\s*\(", "assembly escape hatch"),
            (r"\b(?:misc_register|misc_deregister|cdev_add|cdev_init|register_chrdev|alloc_chrdev_region)\b", "unsupported registration call"),
            (r"\b(?:copy_from_user|copy_to_user|UserSlice)\b", "unreachable user-copy adapter")):
        if re.search(pattern, text):
            raise ContractError("IHK ioctl source contains forbidden {0}".format(label))

    for name in (
            "NATIVE_DEVICE_REGISTRATION_SUPPORTED",
            "NATIVE_FILE_OPERATIONS_SUPPORTED",
            "NATIVE_IOCTL_CALLBACK_SUPPORTED",
            "USER_COPY_REACHABLE_FROM_IOCTL"):
        _require(
            text,
            r"^pub\(crate\) const {0}: bool = false;$".format(name),
            "explicit unsupported marker {0}".format(name))
    for name in COMMANDS:
        _require(text, r"\b{0}\b".format(name), "command import {0}".format(name))
    _require(text, r"argument >= OS_CAPACITY as u64", "fail-closed 0..63 minor range")
    _require(text, r"pub\(crate\) fn prepare_device", "two-phase device dispatcher")
    _require(text, r"commit_after_external_success", "external-success publication boundary")
    _require(text, r"abort_external_failure", "external-failure rollback boundary")
    _require(text, r"DeviceTransactionInner::Destroy.*?-EINVAL", "destroy provider errno mapping")
    _require(text, r"IHK_OS_QUERY_STATUS \| IHK_OS_STATUS", "status command aliases")
    _require(text, r"snapshot\(handle\).*?snapshot.status as i64", "direct status return")
    _require(text, r"map_legacy_destroy_lookup_error", "legacy missing-minor EINVAL bridge")


def _validate_fixture(data):
    text = _text(data, "standalone ioctl fixture")
    for marker in (
            "#![cfg_attr(not(test), no_std)]",
            "../../../host-kernel/native-rust/abi/x86_64.rs",
            "../../../host-kernel/native-rust/os_registry.rs",
            "../../../host-kernel/native-rust/ihk_ioctl.rs",
            "exact_raw_commands_and_scalar_copy_policy",
            "create_failure_rolls_back_and_preserves_provider_errno",
            "create_status_aliases_and_destroy_return_exact_scalars",
            "destroy_lookup_and_unknown_requests_use_legacy_einval",
            "destroy_failures_roll_back_with_exact_stage_errno_mapping",
            "exact_sixty_four_capacity_returns_enomem",
            "leases_exclude_destroy_until_the_open_identity_is_released",
            "stale_open_identity_never_observes_a_recycled_minor",
            "concurrent_create_transactions_publish_unique_minors",
            "deterministic_operation_property_preserves_registry_invariants"):
        if marker not in text:
            raise ContractError("standalone fixture lacks locked marker: {0}".format(marker))


def _validate_attachment(data):
    text = _text(data, "IHK crate root")
    declaration = "#[allow(dead_code)]\nmod ihk_ioctl;"
    if text.count(declaration) != 1:
        raise ContractError("IHK crate root lacks one private ioctl dispatcher attachment")
    if (text.count("mod ikc_queue;") != 1 or
            text.count("mod os_registry;") != 1 or
            text.count("mod ikc_master;") != 1):
        raise ContractError("IHK queue, registry, or master attachment was not preserved")


def _validate_rocky_key_sources(values):
    lib = _text(values["crate_exports"], "Rocky rust/kernel/lib.rs")
    ioctl = _text(values["ioctl_numbers"], "Rocky rust/kernel/ioctl.rs")
    uaccess = _text(values["user_access"], "Rocky rust/kernel/uaccess.rs")
    _require(lib, r"^pub mod ioctl;$", "Rocky ioctl-number module export")
    _require(lib, r"^pub mod uaccess;$", "Rocky user-access module export")
    for module in ("fs", "file", "miscdevice", "miscdev", "cdev"):
        if re.search(r"^pub mod {0};$".format(module), lib, re.MULTILINE):
            raise ContractError("Rocky unexpectedly exports registration module: {0}".format(module))
    for helper in ("_IO", "_IOR", "_IOW", "_IOWR", "_IOC_DIR", "_IOC_TYPE", "_IOC_NR", "_IOC_SIZE"):
        _require(ioctl, r"pub const fn {0}".format(re.escape(helper)), "Rocky ioctl helper {0}".format(helper))
    _require(uaccess, r"pub struct UserSlice", "Rocky safe user slice")
    _require(uaccess, r"bindings::copy_from_user", "Rocky copy-from-user wrapper")
    _require(uaccess, r"bindings::copy_to_user", "Rocky copy-to-user wrapper")


def audit_rocky_source(kernel_source):
    root = os.path.realpath(kernel_source)
    if not os.path.isdir(root) or os.path.islink(kernel_source):
        raise ContractError("Rocky kernel source must be a real directory")
    values = {}
    for source_id, path, size, digest in ROCKY_RUST_SOURCES:
        data = _read(root, path, "Rocky source " + source_id)
        if len(data) != size or _sha(data) != digest:
            raise ContractError("exact Rocky Rust source lock mismatch: {0}".format(source_id))
        values[source_id] = data
    _validate_rocky_key_sources(values)

    rust_root = os.path.join(root, "rust")
    source_count = 0
    forbidden = re.compile(
        r"\b(?:misc_register|misc_deregister|cdev_init|cdev_add|cdev_del|"
        r"register_chrdev|alloc_chrdev_region)\b|\bstruct\s+file_operations\b")
    for directory, subdirectories, files in os.walk(rust_root, followlinks=False):
        for name in subdirectories:
            if os.path.islink(os.path.join(directory, name)):
                raise ContractError("Rocky Rust source tree contains a symlink")
        for name in files:
            path = os.path.join(directory, name)
            if os.path.islink(path):
                raise ContractError("Rocky Rust source tree contains a symlink")
            if not name.endswith(".rs"):
                continue
            source_count += 1
            try:
                with open(path, "r", encoding="utf-8") as stream:
                    text = stream.read()
            except (IOError, OSError, UnicodeError) as error:
                raise ContractError("cannot audit Rocky Rust source: {0}".format(error))
            if forbidden.search(text):
                raise ContractError("Rocky Rust source unexpectedly contains a registration API")
    if source_count < 50:
        raise ContractError("Rocky Rust source audit closure is unexpectedly small")
    return source_count


def derive_contract(repo_root, rust_override=None, abi_override=None,
                    registry_override=None, fixture_override=None,
                    crate_root_override=None, legacy_overrides=None):
    sources = load_legacy_sources(repo_root, legacy_overrides)
    _validate_legacy(sources)
    rust = rust_override if rust_override is not None else _read(repo_root, RUST_PATH)
    abi = abi_override if abi_override is not None else _read(repo_root, ABI_PATH)
    registry = registry_override if registry_override is not None else _read(repo_root, REGISTRY_PATH)
    fixture = fixture_override if fixture_override is not None else _read(repo_root, FIXTURE_PATH)
    crate_root = crate_root_override if crate_root_override is not None else _read(repo_root, CRATE_ROOT_PATH)
    rocky_values = {}
    rocky_fixture_records = []
    for source_id, path, size, digest in ROCKY_RUST_SOURCES:
        fixture_path = ROCKY_FIXTURE_ROOT + "/" + path
        data = _read(repo_root, fixture_path)
        if len(data) != size or _sha(data) != digest:
            raise ContractError("checked-in exact Rocky Rust API fixture drifted: {0}".format(source_id))
        rocky_values[source_id] = data
        rocky_fixture_records.append({"path": fixture_path, "sha256": _sha(data)})
    source_lock = _read(repo_root, SOURCE_LOCK_PATH)

    _validate_abi(abi)
    _validate_rust(rust)
    _validate_fixture(fixture)
    _validate_attachment(crate_root)
    _validate_rocky_key_sources(rocky_values)

    return {
        "behavior": {
            "capacity": 64,
            "commands": COMMANDS,
            "create_return": "minor-number",
            "destroy_missing_minor_errno": -22,
            "destroy_return": 0,
            "errno_map": ERRNO_MAP,
            "minor_policy": "accept-0-through-63; reject-legacy-off-by-one-64",
            "provider_failure_policy": {
                "create": "propagate-external-errno-and-rollback",
                "destroy_shutdown": "propagate-external-errno-and-rollback",
                "destroy_provider": "map-to-EINVAL-and-rollback",
            },
            "status_return": "direct-enum-value-for-both-aliases",
            "user_copy": "none-for-this-scalar-subset",
        },
        "canonical_inputs": {
            "abi": {"path": ABI_PATH, "sha256": _sha(abi)},
            "registry": {"path": REGISTRY_PATH, "sha256": _sha(registry)},
        },
        "fixture": {
            "edition": "2021",
            "minimum_rustc": "1.92.0",
            "no_std_library_mode": True,
            "path": FIXTURE_PATH,
            "sha256": _sha(fixture),
            "test_count": 10,
            "toolchain_identity": EXPECTED_RUSTC,
        },
        "gate_id": "IHK-005-ioctl-dispatch-foundation",
        "implementation": {
            "allocation_free": True,
            "attached_private": True,
            "ffi_free": True,
            "path": RUST_PATH,
            "registration_supported": False,
            "sha256": _sha(rust),
            "size": len(rust),
            "user_copy_reachable": False,
        },
        "legacy_capture": {
            "ihk_ref": IHK_REF,
            "sources": [
                {"id": source_id, "path": path, "sha256": digest, "size": size}
                for source_id, path, size, digest in LEGACY_SOURCES
            ],
        },
        "rocky_rust_api_audit": {
            "available": ["ioctl-number-helpers", "UserSlice-copy-wrappers"],
            "kernel_nvr": "6.12.0-211.44.1.el10_2",
            "outcome": "dispatcher-only-registration-blocked",
            "registration_apis_absent": [
                "miscdevice", "cdev", "file_operations", "ioctl-callback-adapter"
            ],
            "source_lock_path": SOURCE_LOCK_PATH,
            "source_lock_sha256": _sha(source_lock),
            "sources": [
                {"id": source_id, "path": path, "sha256": digest, "size": size}
                for source_id, path, size, digest in ROCKY_RUST_SOURCES
            ],
            "verified_key_source_fixtures": rocky_fixture_records,
        },
        "readiness": {
            "blockers": list(READINESS_BLOCKERS),
            "credit_eligible": False,
            "status": "TODO",
        },
        "schema_version": 1,
    }


def render_contract(value):
    return (json.dumps(value, indent=2, sort_keys=True, separators=(",", ": ")) + "\n").encode("utf-8")


def check(repo_root, rust_override=None, abi_override=None,
          registry_override=None, fixture_override=None,
          crate_root_override=None, legacy_overrides=None,
          contract_override=None, kernel_source=None):
    expected = derive_contract(
        repo_root,
        rust_override=rust_override,
        abi_override=abi_override,
        registry_override=registry_override,
        fixture_override=fixture_override,
        crate_root_override=crate_root_override,
        legacy_overrides=legacy_overrides)
    actual = contract_override if contract_override is not None else _read(repo_root, CONTRACT_PATH)
    if actual != render_contract(expected):
        raise ContractError("checked-in ioctl dispatcher contract differs from deterministic capture")
    if kernel_source is not None:
        audit_rocky_source(kernel_source)
    return expected


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    parser.add_argument("--kernel-source")
    parser.add_argument("--print-contract", action="store_true")
    arguments = parser.parse_args(argv)
    try:
        contract = derive_contract(arguments.repo) if arguments.print_contract else check(
            arguments.repo, kernel_source=arguments.kernel_source)
    except ContractError as error:
        print("IHK ioctl dispatcher contract: FAIL: {0}".format(error), file=sys.stderr)
        return 1
    if arguments.print_contract:
        sys.stdout.write(render_contract(contract).decode("utf-8"))
    else:
        suffix = "; exact Rocky source audited" if arguments.kernel_source else ""
        print("IHK ioctl dispatcher contract: OK (TODO; no credit{0})".format(suffix))
    return 0


if __name__ == "__main__":
    sys.exit(main())
