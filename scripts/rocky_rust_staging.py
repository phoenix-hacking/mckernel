#!/usr/bin/env python3
"""Validate and stage the native Rust-for-Linux host-module build inputs."""

from __future__ import print_function

import argparse
import ctypes
import difflib
import errno
import hashlib
import json
import os
import re
import shutil
import stat
import sys
import tarfile
import tempfile

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


SCHEMA_VERSION = 2
PARENT_SCHEMA_VERSION = 1
PRODUCTION_STAGE_ENABLED = False
EVIDENCE_STAGE_PURPOSE = "compiler-evidence-only"
PROFILE_ID = "rocky-10.2-native-rust-host-modules-v1"
DEFAULT_MANIFEST = "host-kernel/kbuild/stage-manifest.json"
EXPECTED_DESTINATION = {
    "kernel_relative_root": "drivers/misc/mckernel",
    "parent_kbuild_integration": "drivers/misc/Makefile",
    "parent_kconfig_integration": "drivers/misc/Kconfig",
}
EXPECTED_BUILD_CONTRACT = {
    "allowed_project_source_suffixes": [".rs"],
    "build_system": "Linux in-tree Kbuild with Rust-for-Linux",
    "compiler_invocation_owner": "Linux Kbuild",
    "forbidden_project_input_suffixes": [".a", ".c", ".cc", ".cpp", ".o", ".so"],
    "manual_rustc_invocation_forbidden": True,
    "prebuilt_project_objects_forbidden": True,
    "project_c_link_objects": 0,
}
EXPECTED_TARGET = {
    "architecture": "x86_64",
    "config_policy_lock_id": "rocky-10.2-x86_64-kernel-6.12.0-211.44.1.el10_2-config-policy-v1",
    "distribution": "Rocky Linux",
    "kernel_nvr_base": "kernel-6.12.0-211.44.1.el10_2",
    "release": "10.2",
    "resolved_config_sha256": None,
    "resolved_kernel_nvr": None,
    "resolved_toolchain_manifest_sha256": None,
    "source_lock_id": "rocky-10.2-x86_64-kernel-6.12.0-211.44.1.el10_2-source-v1",
    "source_rpm_sha256": "2bfeda65bd9bdd4b86650074c81e061c37822b80317ac0d4f5aacc89c85589cb",
    "toolchain_lock_id": "rocky-10.2-x86_64-kernel-6.12.0-211.44.1.el10_2-toolchain-v1",
}
EXPECTED_INPUTS = (
    {
        "destination": "Kbuild",
        "kind": "kbuild_template",
        "repository_path": "host-kernel/kbuild/Kbuild.in",
        "sha256": "f33c826539ed0807617337ba64a1cb646daf510cc06a44b47243d14e366d67a3",
    },
    {
        "destination": "Kconfig",
        "kind": "kconfig",
        "repository_path": "host-kernel/kbuild/Kconfig",
        "sha256": "48c6ba25186281a3a4fe4690c7520b02d8bbe43965e78d3301d2613477c3874f",
    },
    {
        "destination": "abi/x86_64.rs",
        "kind": "shared_rust_abi",
        "repository_path": "host-kernel/native-rust/abi/x86_64.rs",
        "sha256": "89e0f72e821cbef91ad4771f4b4b24515d89035d357dc9c23c935a313b7d12c3",
    },
    {
        "destination": "ikc_queue.rs",
        "kind": "rust_module",
        "repository_path": "host-kernel/native-rust/ikc_queue.rs",
        "sha256": "514f9bce452498e5e9394c450532b040c44fce1ac7a6b5158c76f3d4c7270d40",
    },
    {
        "destination": "os_registry.rs",
        "kind": "rust_support_module",
        "repository_path": "host-kernel/native-rust/os_registry.rs",
        "sha256": "29464b8ca1038d87cc0d5f760eb22e0cbd7a1a512ae88f4c550574a784d1e49d",
    },
    {
        "destination": "device_registry.rs",
        "kind": "rust_support_module",
        "repository_path": "host-kernel/native-rust/device_registry.rs",
        "sha256": "1e301c29c018f2ad7cc8dba121513b3d4e50707be500c70c631d53c83809dac7",
    },
    {
        "destination": "ikc_master.rs",
        "kind": "rust_module",
        "repository_path": "host-kernel/native-rust/ikc_master.rs",
        "sha256": "f7e8f8bc1cc860a2eb3724457d81bf03b132fa156eac5c5e258a393808e6ca1e",
    },
    {
        "destination": "ihk_ioctl.rs",
        "kind": "rust_ioctl_dispatch",
        "repository_path": "host-kernel/native-rust/ihk_ioctl.rs",
        "sha256": "3d603424705a9b0fb18725bae1d75f1d279b249b866c15f15f98166d013edfbb",
    },
    {
        "destination": "page_allocator.rs",
        "kind": "rust_support_module",
        "repository_path": "host-kernel/native-rust/page_allocator.rs",
        "sha256": "8e2af0cde06cbb70204540b493e8a0a66d5203195ed671235b64bed44d328bc5",
    },
    {
        "destination": "page_owner_registry.rs",
        "kind": "rust_support_module",
        "repository_path": "host-kernel/native-rust/page_owner_registry.rs",
        "sha256": "443d58fa5b2e423f538c6622ef04d8e34338abc43c5e0fd34811d52fc21f4869",
    },
    {
        "destination": "smp_resource.rs",
        "kind": "rust_support_module",
        "repository_path": "host-kernel/native-rust/smp_resource.rs",
        "sha256": "b918ea3186d8f55518c9ceb46d84f6c98633b4ab7b8a81e5d2e0024c0914919b",
    },
)
EXPECTED_PARENT_INTEGRATION_REF = {
    "repository_path": "host-kernel/kbuild/parent-integration-v1.json",
    "sha256": "19b18ece742950b2ef5fc9314579849e763a307982a3a91c99dfaad5917d4b55",
}
EXPECTED_PARENT_SOURCE = {
    "archive_basename": "linux-6.12.0-211.44.1.el10_2.tar.xz",
    "archive_sha256": "4a174d47b8874a2139efcd1ac1ab2d6b80ae7a0ca62f0ae4596fd20cf62a3533",
    "archive_root": "linux-6.12.0-211.44.1.el10_2",
    "source_lock_id": "rocky-10.2-x86_64-kernel-6.12.0-211.44.1.el10_2-source-v1",
    "source_lock_repository_path": "host-kernel/rocky/source-lock.json",
    "source_lock_sha256": "b70df1e475072dbfa31fdc712900ac59d30eeb139219c7076aacaa19abf0fded",
    "source_rpm_sha256": "2bfeda65bd9bdd4b86650074c81e061c37822b80317ac0d4f5aacc89c85589cb",
}
EXPECTED_PARENT_PATCH = {
    "format": "unified-diff",
    "path_strip": 1,
    "repository_path": "host-kernel/kbuild/patches/0001-drivers-misc-add-mckernel-rust-host-modules.patch",
    "sha256": "25b0724a2523c3fd5d6d8b824b72c6e6b19c2b16edebaa6719b53c22d4d5c7d9",
}
EXPECTED_PARENT_FILES = [
    {
        "insertion": {
            "anchor": "obj-y\t\t\t\t+= keba/",
            "line": "obj-$(CONFIG_MCKERNEL_IHK_RUST)\t+= mckernel/",
            "placement": "after",
        },
        "path": "drivers/misc/Makefile",
        "postimage_sha256": "548e7eed491c9287908870a4783be57c15a360f03ecc68a4c4856e7c5c51a74f",
        "preimage_sha256": "3f998f3c28cae01f8cb6e3b283f25175635ff2510ba40ce60235a3c059a9a238",
    },
    {
        "insertion": {
            "anchor": "endmenu",
            "line": 'source "drivers/misc/mckernel/Kconfig"',
            "placement": "before",
        },
        "path": "drivers/misc/Kconfig",
        "postimage_sha256": "ed57d452061fb74e62d5dce3aa3680aec0b70811b87b57a25554dc4dd4c33e4a",
        "preimage_sha256": "679b6c945aebec04f936c184b724f1b0d6daa6d760ec3bb4d6b56db905c19683",
    },
]
EXPECTED_PARENT_ABSENT_PATHS = [
    "drivers/misc/mckernel",
    "drivers/misc/mckernel/Kbuild",
    "drivers/misc/mckernel/Kconfig",
]
PARENT_VERIFICATION_SCOPE = (
    "byte-exact parent preimages, intended insertions, postimages, and patch bytes only; "
    "no build, runtime, or RK-007 credit"
)
MODULE_BLOCKERS = []
READINESS_BLOCKERS = [
    "selected Rocky kernel source, toolchain, and config evidence is not gate-ready",
    "upstream Rust-for-Linux sample has not built through this staging path",
    "production namespace and import metadata has not been proven from built modules",
    "zero-project-C final link manifests have not been captured",
]
EXPECTED_MODULES = (
    {
        "crate": "ihk",
        "normalized_name": "ihk",
        "output": "ihk.ko",
        "kconfig_symbol": "CONFIG_MCKERNEL_IHK_RUST",
        "dependencies": [],
        "production_namespace": "MCKERNEL_IHK_V1",
        "required_import_namespaces": [],
        "source_destination": "ihk.rs",
        "source_repository_path": "host-kernel/native-rust/ihk.rs",
        "source_sha256": "3988cd5a4eca902f945fd2c75dcb157a426d174390212d1e8c5f42aea04b7a9b",
    },
    {
        "crate": "ihk_smp_x86_64",
        "normalized_name": "ihk_smp_x86_64",
        "output": "ihk-smp-x86_64.ko",
        "kconfig_symbol": "CONFIG_MCKERNEL_IHK_SMP_X86_64_RUST",
        "dependencies": ["ihk"],
        "production_namespace": None,
        "required_import_namespaces": ["MCKERNEL_IHK_V1"],
        "source_destination": "ihk_smp_x86_64.rs",
        "source_repository_path": "host-kernel/native-rust/ihk_smp_x86_64.rs",
        "source_sha256": "2442c4511ac9bf5b032c691a0f560e87a22352720c3d07df60b927335149ebb9",
    },
    {
        "crate": "mcctrl",
        "normalized_name": "mcctrl",
        "output": "mcctrl.ko",
        "kconfig_symbol": "CONFIG_MCKERNEL_MCCTRL_RUST",
        "dependencies": ["ihk"],
        "production_namespace": None,
        "required_import_namespaces": ["MCKERNEL_IHK_V1"],
        "source_destination": "mcctrl.rs",
        "source_repository_path": "host-kernel/native-rust/mcctrl.rs",
        "source_sha256": "1a8b85c379d6976d90ba462b9386d1bbd7fce83ca152e46bce391e6cfa6b5389",
    },
)
AUDITED_PROVIDER_EXTERN = (
    'extern "Rust" {\n'
    '    #[link_name = "ihk_provider_lifecycle_v1"]\n'
    "    static IHK_PROVIDER_LIFECYCLE_V1: u8;\n"
    "}"
)
AUDITED_IHK_ATTACH_EXTERN = (
    '#[doc(hidden)]\n'
    '// SAFETY: This C-ABI scalar boundary owns no caller memory.  A positive return\n'
    '// is a versioned opaque token for the single published minor-zero provider;\n'
    '// every failure is a negative errno and leaves no live reservation behind.\n'
    '#[export_name = "ihk_smp_provider_attach_v1"]\n'
    '// SAFETY: This exported C ABI accepts no caller-owned state and returns only\n'
    '// the registry-owned scalar token or a negative errno.\n'
    'pub extern "C" fn ihk_smp_provider_attach_v1() -> i64 {'
)
AUDITED_IHK_DETACH_EXTERN = (
    '#[doc(hidden)]\n'
    '// SAFETY: This C-ABI scalar boundary consumes the exact v1 token owned by the\n'
    '// reviewed namespaced SMP dependent.  The token is an ownership receipt, not\n'
    '// a security boundary against other privileged in-kernel code.  Any malformed,\n'
    '// stale, duplicated, busy, or corrupt state fails stop before unload succeeds.\n'
    '#[export_name = "ihk_smp_provider_detach_v1"]\n'
    '// SAFETY: This exported C ABI accepts only the opaque scalar issued by attach\n'
    '// and cannot return while the owned provider entry remains live.\n'
    'pub extern "C" fn ihk_smp_provider_detach_v1(token: i64) {'
)
AUDITED_SMP_PROVIDER_EXTERN = (
    'extern "C" {\n'
    '    #[link_name = "ihk_provider_lifecycle_v1"]\n'
    '    static IHK_PROVIDER_LIFECYCLE_V1: u8;\n'
    '    #[link_name = "ihk_smp_provider_attach_v1"]\n'
    '    fn ihk_smp_provider_attach_v1() -> i64;\n'
    '    #[link_name = "ihk_smp_provider_detach_v1"]\n'
    '    fn ihk_smp_provider_detach_v1(token: i64);\n'
    '}'
)
EXPECTED_TOP_LEVEL_KEYS = {
    "build_contract",
    "destination",
    "inputs",
    "modules",
    "parent_integration",
    "profile_id",
    "readiness",
    "schema_version",
    "target",
}
HEX64 = re.compile(r"^[0-9a-f]{64}$")


class ValidationError(Exception):
    pass


_RUST_FORBIDDEN_CAPABILITIES = frozenset(
    ("include", "include_bytes", "asm", "global_asm")
)


def _blank_rust_span(masked, text, start, end, preserved=()):
    """Blank a lexical non-code span while retaining offsets and newlines."""

    preserved = set(preserved)
    for offset in range(start, end):
        if offset not in preserved and text[offset] not in "\r\n":
            masked[offset] = " "


def _rust_char_literal_end(text, start):
    """Return the end of a Rust character literal, or None for a lifetime."""

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
    """Return Rust code with comments and literal contents lexically masked."""

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
            closed = False
            while end < length:
                if text[end] == "\\":
                    end += 2
                elif text[end] == '"':
                    end += 1
                    closed = True
                    break
                else:
                    end += 1
            if not closed:
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


def _rust_identifier_start(character):
    return character == "_" or character.isidentifier()


def _rust_identifier_continue(character):
    return character == "_" or ("a" + character).isidentifier()


def _rust_identifiers(text):
    """Yield Rust-like Unicode identifiers without Python ``\b`` ambiguity."""

    cursor = 0
    length = len(text)
    while cursor < length:
        raw = False
        name_start = cursor
        if (
            text.startswith("r#", cursor)
            and cursor + 2 < length
            and _rust_identifier_start(text[cursor + 2])
        ):
            raw = True
            name_start = cursor + 2
        elif not _rust_identifier_start(text[cursor]):
            cursor += 1
            continue
        end = name_start + 1
        while end < length and _rust_identifier_continue(text[end]):
            end += 1
        yield text[name_start:end], cursor, end, raw
        cursor = end


def _validate_bare_audited_extern(masked, start, label):
    line_start = masked.rfind("\n", 0, start) + 1
    if masked[line_start:start].strip():
        raise ValidationError(
            "{0} exact audited extern boundary has an unreviewed modifier".format(label)
        )
    prefix = masked[:start].rstrip()
    if prefix and prefix[-1] not in ";}":
        raise ValidationError(
            "{0} exact audited extern boundary has an unreviewed outer attribute".format(
                label
            )
        )


def _validate_rust_escape_hatches(text, label, allowed_extern_blocks=()):
    """Reject unreviewed Rust source inclusion, assembly, and extern edges."""

    masked = _mask_rust_comments_and_literals(text)
    identifiers = list(_rust_identifiers(masked))
    forbidden = next(
        (name for name, _start, _end, _raw in identifiers
         if name in _RUST_FORBIDDEN_CAPABILITIES),
        None,
    )
    if forbidden is not None:
        raise ValidationError(
            "{0} contains forbidden Rust macro boundary: {1}!".format(
                label, forbidden
            )
        )

    extern_starts = [
        start for name, start, _end, raw in identifiers
        if name == "extern" and not raw
    ]
    allowed_starts = set()
    for exact in allowed_extern_blocks:
        starts = []
        extern_offset = exact.find("extern")
        if extern_offset < 0:
            raise ValidationError(
                "{0} audited extern allowlist item lacks extern".format(label)
            )
        search_from = 0
        while True:
            exact_start = text.find(exact, search_from)
            if exact_start < 0:
                break
            extern_start = exact_start + extern_offset
            if extern_start in extern_starts:
                starts.append((exact_start, extern_start))
            search_from = exact_start + 1
        if len(starts) != 1:
            raise ValidationError(
                "{0} lacks one exact audited extern boundary".format(label)
            )
        exact_start, extern_start = starts[0]
        _validate_bare_audited_extern(masked, exact_start, label)
        allowed_starts.add(extern_start)
    if any(start not in allowed_starts for start in extern_starts):
        raise ValidationError(
            "{0} contains an additional unreviewed extern boundary".format(label)
        )
    return masked


def _object_without_duplicates(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValidationError("duplicate JSON key: {0}".format(key))
        result[key] = value
    return result


def load_json(path):
    try:
        with open(path, "r") as stream:
            return json.load(stream, object_pairs_hook=_object_without_duplicates)
    except (IOError, OSError, ValueError) as error:
        raise ValidationError("cannot load {0}: {1}".format(path, error))


def canonical_json_bytes(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def sha256_bytes(value):
    return hashlib.sha256(value).hexdigest()


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        while True:
            chunk = stream.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def _require_keys(value, expected, label):
    if not isinstance(value, dict):
        raise ValidationError("{0} must be an object".format(label))
    actual = set(value)
    if actual != set(expected):
        raise ValidationError(
            "{0} keys differ: missing={1}, extra={2}".format(
                label, sorted(set(expected) - actual), sorted(actual - set(expected))
            )
        )


def _require_string_list(value, label, allow_empty=True):
    if not isinstance(value, list) or (not allow_empty and not value):
        raise ValidationError("{0} must be a {1}list".format(label, "non-empty " if not allow_empty else ""))
    if any(not isinstance(item, str) or not item.strip() for item in value):
        raise ValidationError("{0} entries must be non-empty strings".format(label))
    if len(value) != len(set(value)):
        raise ValidationError("{0} contains duplicates".format(label))


def _safe_relative_path(value, label):
    if not isinstance(value, str) or not value:
        raise ValidationError("{0} must be a non-empty relative path".format(label))
    if "\\" in value or value.startswith("/") or value != os.path.normpath(value):
        raise ValidationError("{0} is not a normalized POSIX-style relative path".format(label))
    if value == "." or value.startswith("../") or "/../" in value or value.endswith("/.."):
        raise ValidationError("{0} escapes its root".format(label))
    return value


def _repo_regular_file(repo_root, relative, label):
    relative = _safe_relative_path(relative, label)
    repo_real = os.path.realpath(repo_root)
    candidate = os.path.join(repo_real, relative)
    candidate_real = os.path.realpath(candidate)
    try:
        inside = os.path.commonpath([repo_real, candidate_real]) == repo_real
    except ValueError:
        inside = False
    if not inside:
        raise ValidationError("{0} resolves outside the repository".format(label))
    try:
        info = os.lstat(candidate)
    except OSError as error:
        raise ValidationError("{0} is unavailable: {1}".format(label, error))
    if stat.S_ISLNK(info.st_mode) or not stat.S_ISREG(info.st_mode):
        raise ValidationError("{0} must be a regular, non-symlink file".format(label))
    if candidate_real != candidate:
        raise ValidationError("{0} traverses a symlink".format(label))
    return candidate


def _validate_digest(path, expected, label):
    if not isinstance(expected, str) or not HEX64.match(expected):
        raise ValidationError("{0}.sha256 must be lowercase SHA-256".format(label))
    actual = sha256_file(path)
    if actual != expected:
        raise ValidationError("{0} digest mismatch: expected {1}, got {2}".format(label, expected, actual))


def _read_text(path, label):
    try:
        with open(path, "r") as stream:
            return stream.read()
    except (IOError, OSError, UnicodeError) as error:
        raise ValidationError("cannot read {0}: {1}".format(label, error))


def _validate_parent_integration(repo_root, reference):
    if reference != EXPECTED_PARENT_INTEGRATION_REF:
        raise ValidationError("parent_integration differs from the hard-locked parent bundle")
    bundle_path = _repo_regular_file(
        repo_root, reference["repository_path"], "parent_integration.repository_path"
    )
    _validate_digest(bundle_path, reference["sha256"], "parent_integration")
    bundle = load_json(bundle_path)
    _require_keys(
        bundle,
        {
            "checkpoint",
            "credit_eligible",
            "parent_files",
            "patch",
            "profile_id",
            "required_absent_paths",
            "schema_version",
            "selected_source",
            "verification_scope",
        },
        "parent integration bundle",
    )
    if bundle["schema_version"] != PARENT_SCHEMA_VERSION or bundle["profile_id"] != PROFILE_ID:
        raise ValidationError("parent integration bundle identity differs")
    if bundle["checkpoint"] != "integrity_only" or bundle["credit_eligible"] is not False:
        raise ValidationError("parent integration bundle may not claim readiness or credit")
    if bundle["selected_source"] != EXPECTED_PARENT_SOURCE:
        raise ValidationError("parent integration selected source differs from the locked Rocky source")
    selected = bundle["selected_source"]
    source_lock_path = _repo_regular_file(
        repo_root, selected["source_lock_repository_path"], "parent integration source lock"
    )
    _validate_digest(source_lock_path, selected["source_lock_sha256"], "parent integration source lock")
    source_lock = load_json(source_lock_path)
    if source_lock.get("lock_id") != selected["source_lock_id"]:
        raise ValidationError("parent integration source-lock ID differs")
    if source_lock.get("source_rpm", {}).get("sha256") != selected["source_rpm_sha256"]:
        raise ValidationError("parent integration source RPM differs from its source lock")
    archive_objects = [
        item
        for item in source_lock.get("embedded_objects", [])
        if item.get("path") == "SOURCES/" + selected["archive_basename"]
    ]
    if len(archive_objects) != 1 or archive_objects[0].get("sha256") != selected["archive_sha256"]:
        raise ValidationError("parent integration source archive differs from its source lock")
    if bundle["patch"] != EXPECTED_PARENT_PATCH:
        raise ValidationError("parent integration patch identity differs")
    if bundle["parent_files"] != EXPECTED_PARENT_FILES:
        raise ValidationError("parent integration preimages, insertions, or postimages differ")
    if bundle["required_absent_paths"] != EXPECTED_PARENT_ABSENT_PATHS:
        raise ValidationError("parent integration destination absence contract differs")
    if bundle["verification_scope"] != PARENT_VERIFICATION_SCOPE:
        raise ValidationError("parent integration verification scope differs")

    patch_path = _repo_regular_file(
        repo_root, bundle["patch"]["repository_path"], "parent integration patch"
    )
    _validate_digest(patch_path, bundle["patch"]["sha256"], "parent integration patch")
    try:
        with open(patch_path, "rb") as stream:
            patch_bytes = stream.read()
    except (IOError, OSError) as error:
        raise ValidationError("cannot read parent integration patch: {0}".format(error))
    if not patch_bytes.endswith(b"\n") or b"\r" in patch_bytes or b"\0" in patch_bytes:
        raise ValidationError("parent integration patch must be LF-only text ending in a newline")
    return {
        "bundle": bundle,
        "bundle_path": bundle_path,
        "bundle_sha256": reference["sha256"],
        "patch_bytes": patch_bytes,
        "patch_path": patch_path,
    }


def _apply_parent_insertion(preimage, item):
    label = item["path"]
    if sha256_bytes(preimage) != item["preimage_sha256"]:
        raise ValidationError("parent preimage digest mismatch: {0}".format(label))
    if b"\r" in preimage or not preimage.endswith(b"\n"):
        raise ValidationError("parent preimage must be LF-only text ending in a newline: {0}".format(label))
    try:
        text = preimage.decode("utf-8")
    except UnicodeError as error:
        raise ValidationError("parent preimage is not UTF-8 text ({0}): {1}".format(label, error))
    lines = text.splitlines()
    insertion = item["insertion"]
    matches = [index for index, line in enumerate(lines) if line == insertion["anchor"]]
    if len(matches) != 1:
        raise ValidationError(
            "parent insertion anchor must occur exactly once ({0}): got {1}".format(label, len(matches))
        )
    index = matches[0]
    if insertion["placement"] == "after":
        index += 1
    elif insertion["placement"] != "before":
        raise ValidationError("unsupported parent insertion placement: {0}".format(label))
    lines.insert(index, insertion["line"])
    postimage = ("\n".join(lines) + "\n").encode("utf-8")
    if sha256_bytes(postimage) != item["postimage_sha256"]:
        raise ValidationError("parent postimage digest mismatch: {0}".format(label))
    return postimage


def _render_parent_patch(parent_files, preimages, postimages):
    chunks = []
    for item in parent_files:
        path = item["path"]
        chunks.append("diff --git a/{0} b/{0}\n".format(path))
        chunks.extend(
            difflib.unified_diff(
                preimages[path].decode("utf-8").splitlines(True),
                postimages[path].decode("utf-8").splitlines(True),
                fromfile="a/" + path,
                tofile="b/" + path,
                n=3,
            )
        )
    return "".join(chunks).encode("utf-8")


def verify_parent_source_archive(plan, archive_path):
    parent = plan["parent_integration"]
    bundle = parent["bundle"]
    selected = bundle["selected_source"]
    archive_path = os.path.abspath(archive_path)
    try:
        info = os.lstat(archive_path)
    except OSError as error:
        raise ValidationError("selected source archive is unavailable: {0}".format(error))
    if stat.S_ISLNK(info.st_mode) or not stat.S_ISREG(info.st_mode):
        raise ValidationError("selected source archive must be a regular, non-symlink file")
    if os.path.basename(archive_path) != selected["archive_basename"]:
        raise ValidationError("selected source archive basename differs")
    _validate_digest(archive_path, selected["archive_sha256"], "selected source archive")

    try:
        with tarfile.open(archive_path, mode="r:xz") as archive:
            members = archive.getmembers()
            normalized_names = [member.name.rstrip("/") for member in members]
            root = selected["archive_root"]
            for relative in bundle["required_absent_paths"]:
                locked = root + "/" + relative
                if any(name == locked or name.startswith(locked + "/") for name in normalized_names):
                    raise ValidationError("selected source already contains locked destination: {0}".format(relative))

            preimages = {}
            for item in bundle["parent_files"]:
                member_name = root + "/" + item["path"]
                matching = [member for member in members if member.name.rstrip("/") == member_name]
                if len(matching) != 1 or not matching[0].isfile():
                    raise ValidationError(
                        "selected source must contain one regular parent file: {0}".format(item["path"])
                    )
                stream = archive.extractfile(matching[0])
                if stream is None:
                    raise ValidationError("cannot read selected source parent: {0}".format(item["path"]))
                preimages[item["path"]] = stream.read()
    except (IOError, OSError, tarfile.TarError) as error:
        raise ValidationError("cannot inspect selected source archive: {0}".format(error))

    postimages = {}
    for item in bundle["parent_files"]:
        postimages[item["path"]] = _apply_parent_insertion(preimages[item["path"]], item)
    rendered = _render_parent_patch(bundle["parent_files"], preimages, postimages)
    if rendered != parent["patch_bytes"]:
        raise ValidationError("parent integration patch bytes differ from exact intended insertions")
    return {
        "archive_sha256": selected["archive_sha256"],
        "parent_files": [
            {
                "path": item["path"],
                "postimage_sha256": item["postimage_sha256"],
                "preimage_sha256": item["preimage_sha256"],
            }
            for item in bundle["parent_files"]
        ],
        "patch_sha256": bundle["patch"]["sha256"],
    }


def _validate_kbuild(text):
    try:
        return validate_native_rust_kbuild(text)
    except KconfigPolicyError as error:
        raise ValidationError("Kbuild policy violation: {0}".format(error))


def _validate_kconfig(text):
    try:
        return validate_native_rust_kconfig(text)
    except KconfigPolicyError as error:
        raise ValidationError("Kconfig policy violation: {0}".format(error))


def _validate_input(repo_root, item, index):
    label = "inputs[{0}]".format(index)
    _require_keys(item, {"destination", "kind", "repository_path", "sha256"}, label)
    if index >= len(EXPECTED_INPUTS) or item != EXPECTED_INPUTS[index]:
        raise ValidationError("{0} differs from the hard-locked staging input".format(label))
    expected_destination = {
        "kbuild_template": "Kbuild",
        "kconfig": "Kconfig",
        "shared_rust_abi": "abi/x86_64.rs",
        "rust_ioctl_dispatch": "ihk_ioctl.rs",
    }.get(item["kind"])
    if item["kind"] == "rust_module":
        expected_destination = item["destination"]
    elif item["kind"] == "rust_support_module" and item["destination"] in (
        "os_registry.rs",
        "device_registry.rs",
        "page_allocator.rs",
        "page_owner_registry.rs",
        "smp_resource.rs",
    ):
        expected_destination = item["destination"]
    if expected_destination is None:
        raise ValidationError("{0}.kind is not a locked staging input kind".format(label))
    if item["destination"] != expected_destination:
        raise ValidationError("{0}.destination must be {1}".format(label, expected_destination))
    path = _repo_regular_file(repo_root, item["repository_path"], label + ".repository_path")
    _validate_digest(path, item["sha256"], label)
    text = _read_text(path, label)
    if item["kind"] not in ("kbuild_template", "kconfig"):
        _validate_rust_escape_hatches(text, label)
    if item["kind"] == "kbuild_template":
        _validate_kbuild(text)
    elif item["kind"] == "kconfig":
        _validate_kconfig(text)
    elif item["kind"] == "shared_rust_abi":
        required = (
            "pub struct IhkIkcQueueHead",
            "assert_layout!(IhkIkcQueueHead, 64, 8,",
            '#[cfg(not(target_endian = "little"))]',
            '#[cfg(not(target_pointer_width = "64"))]',
        )
        for token in required:
            if text.count(token) != 1:
                raise ValidationError("{0} lacks a unique ABI marker: {1}".format(label, token))
        lowered = text.lower()
        for forbidden in ("unsafe", "module!"):
            if forbidden in lowered:
                raise ValidationError("{0} contains forbidden executable/boundary construct: {1}".format(label, forbidden))
    elif item["destination"] == "ikc_queue.rs":
        required = (
            "use super::abi::IhkIkcQueueHead;",
            "pub(crate) struct SharedQueue",
            "pub(crate) fn try_enqueue",
            "pub(crate) fn try_dequeue",
            "pub(crate) unsafe fn attach",
        )
        for token in required:
            if text.count(token) != 1:
                raise ValidationError("{0} lacks a unique queue marker: {1}".format(label, token))
        lowered = text.lower()
        for forbidden in ("module!",):
            if forbidden in lowered:
                raise ValidationError("{0} contains forbidden executable/boundary construct: {1}".format(label, forbidden))
    elif item["destination"] == "os_registry.rs":
        required = (
            "pub(crate) const OS_CAPACITY: usize = 64;",
            "const MAX_GENERATION: u64 = u64::MAX >> GENERATION_SHIFT;",
            "impl Drop for ReservationGuard<'_>",
            "impl Drop for DestroyGuard<'_>",
            "RegistryError::StaleHandle",
        )
        for token in required:
            if text.count(token) < 1:
                raise ValidationError("{0} lacks registry marker: {1}".format(label, token))
        lowered = text.lower()
        for forbidden in ("unsafe", "module!"):
            if forbidden in lowered:
                raise ValidationError("{0} contains forbidden executable/boundary construct: {1}".format(label, forbidden))
    elif item["destination"] == "device_registry.rs":
        required = (
            "pub(crate) const DEVICE_CAPACITY: usize = 64;",
            "pub(crate) struct DeviceRegistry",
            "pub(crate) fn reserve",
            "pub(crate) fn acquire_open",
            "pub(crate) fn acquire_os",
            "pub(crate) fn begin_unregister",
            "impl Drop for ReservationGuard<'_>",
            "impl Drop for UnregisterGuard<'_>",
            "DeviceRegistryError::RegistryIdentityExhausted",
        )
        for token in required:
            if text.count(token) < 1:
                raise ValidationError("{0} lacks device-registry marker: {1}".format(label, token))
        lowered = text.lower()
        for forbidden in ("unsafe", "module!"):
            if forbidden in lowered:
                raise ValidationError("{0} contains forbidden executable/boundary construct: {1}".format(label, forbidden))
    elif item["destination"] == "ikc_master.rs":
        required = (
            "pub(crate) struct ListenerRegistry",
            "pub(crate) struct ListenerLease",
            "pub(crate) struct MasterRouter",
            "pub(crate) struct ConnectTransaction",
            "pub(crate) struct ChannelLifecycle",
            "use super::abi::",
        )
        for token in required:
            if text.count(token) != 1:
                raise ValidationError("{0} lacks a unique master-registry marker: {1}".format(label, token))
        lowered = text.lower()
        for forbidden in ("unsafe", "module!"):
            if forbidden in lowered:
                raise ValidationError("{0} contains forbidden executable/boundary construct: {1}".format(label, forbidden))
    elif item["destination"] == "page_allocator.rs":
        required = (
            "pub(crate) struct BitmapPageAllocator",
            "pub(crate) struct PageAllocation",
            "pub(crate) struct PageReservation",
            "operation_lock: AtomicBool,",
        )
        for token in required:
            if text.count(token) != 1:
                raise ValidationError("{0} lacks a unique page-allocator marker: {1}".format(label, token))
        lowered = text.lower()
        for forbidden in ("unsafe", "module!"):
            if forbidden in lowered:
                raise ValidationError("{0} contains forbidden executable/boundary construct: {1}".format(label, forbidden))
    elif item["destination"] == "page_owner_registry.rs":
        required = (
            "pub(crate) struct RawPageOwnerRegistry",
            "pub(crate) struct RawPageOwnerSlot",
            "pub(crate) struct RawPageAllocationHandle",
            "static NEXT_REGISTRY_ID: AtomicU64",
        )
        for token in required:
            if text.count(token) != 1:
                raise ValidationError("{0} lacks a unique page-owner marker: {1}".format(label, token))
        lowered = text.lower()
        for forbidden in ("unsafe", "module!"):
            if forbidden in lowered:
                raise ValidationError("{0} contains forbidden executable/boundary construct: {1}".format(label, forbidden))
    elif item["destination"] == "smp_resource.rs":
        required = (
            "pub(crate) const SMP_MAX_CPUS: usize = 512;",
            "pub(crate) struct CpuTransaction",
            "pub(crate) struct MemoryTransaction<",
            "pub(crate) fn begin_external_effects",
            "pub(crate) fn compensated_rollback",
            "CpuState::Quarantined",
            "poisoned: bool",
        )
        for token in required:
            if text.count(token) < 1:
                raise ValidationError("{0} lacks SMP-resource marker: {1}".format(label, token))
        lowered = text.lower()
        for forbidden in ("unsafe", "module!"):
            if forbidden in lowered:
                raise ValidationError("{0} contains forbidden executable/boundary construct: {1}".format(label, forbidden))
    else:
        required = (
            "pub(crate) struct IhkIoctlDispatcher",
            "pub(crate) fn prepare_device",
            "commit_after_external_success",
            "NATIVE_DEVICE_REGISTRATION_SUPPORTED: bool = false",
            "USER_COPY_REACHABLE_FROM_IOCTL: bool = false",
        )
        for token in required:
            if text.count(token) < 1:
                raise ValidationError("{0} lacks ioctl-dispatch marker: {1}".format(label, token))
        lowered = text.lower()
        for forbidden in ("unsafe", "kernel::", "bindings::", "module!"):
            if forbidden in lowered:
                raise ValidationError("{0} contains forbidden executable/boundary construct: {1}".format(label, forbidden))
    return {
        "destination": item["destination"],
        "path": path,
        "sha256": item["sha256"],
    }


def _validate_module(repo_root, module, expected, index):
    label = "modules[{0}]".format(index)
    _require_keys(
        module,
        {
            "blockers",
            "crate",
            "dependencies",
            "kconfig_symbol",
            "normalized_name",
            "output",
            "production_namespace",
            "required_import_namespaces",
            "source",
        },
        label,
    )
    for field in (
        "crate",
        "dependencies",
        "kconfig_symbol",
        "normalized_name",
        "output",
        "production_namespace",
        "required_import_namespaces",
    ):
        if module[field] != expected[field]:
            raise ValidationError("{0}.{1} differs from the locked module contract".format(label, field))
    if module["blockers"] != MODULE_BLOCKERS:
        raise ValidationError("{0}.blockers differs from the locked crate-root checkpoint".format(label))
    _require_keys(module["source"], {"destination", "repository_path", "sha256"}, label + ".source")
    source = module["source"]
    if source["destination"] != expected["source_destination"]:
        raise ValidationError("{0}.source.destination differs from the locked crate root".format(label))
    if source["repository_path"] != expected["source_repository_path"]:
        raise ValidationError("{0}.source.repository_path differs from the locked crate root".format(label))
    if source["sha256"] != expected["source_sha256"]:
        raise ValidationError("{0}.source.sha256 differs from the locked crate root".format(label))
    path = _repo_regular_file(repo_root, source["repository_path"], label + ".source.repository_path")
    if not path.endswith(".rs"):
        raise ValidationError("{0}.source must be a Rust source file".format(label))
    _validate_digest(path, source["sha256"], label + ".source")
    text = _read_text(path, label + ".source")
    allowed_extern_blocks = ()
    if module["crate"] == "ihk":
        allowed_extern_blocks = (
            AUDITED_IHK_ATTACH_EXTERN,
            AUDITED_IHK_DETACH_EXTERN,
        )
    elif module["crate"] == "ihk_smp_x86_64":
        allowed_extern_blocks = (AUDITED_SMP_PROVIDER_EXTERN,)
    elif module["crate"] == "mcctrl":
        allowed_extern_blocks = (AUDITED_PROVIDER_EXTERN,)
    _validate_rust_escape_hatches(
        text, label + ".source", allowed_extern_blocks=allowed_extern_blocks
    )
    if "module!" not in text or "impl kernel::Module" not in text:
        raise ValidationError("{0}.source lacks a native Rust-for-Linux module entry point".format(label))
    if module["crate"] == "ihk":
        for fragment in (
            '#[path = "abi/x86_64.rs"]\nmod abi;',
            "mod ikc_queue;",
            "mod os_registry;",
            "mod device_registry;",
            "mod ikc_master;",
            "mod ihk_ioctl;",
            "mod page_allocator;",
            "mod page_owner_registry;",
        ):
            if text.count(fragment) != 1:
                raise ValidationError(
                    "{0}.source does not bind the staged IHK queue graph: {1}".format(
                        label, fragment
                    )
                )
    elif module["crate"] == "ihk_smp_x86_64":
        fragment = "#[allow(dead_code)]\nmod smp_resource;"
        if text.count(fragment) != 1:
            raise ValidationError(
                "{0}.source does not bind the staged SMP resource policy: {1}".format(
                    label, fragment
                )
            )
    return {
        "destination": source["destination"],
        "path": path,
        "sha256": source["sha256"],
    }, list(module["blockers"])


def validate_manifest(repo_root, manifest_path):
    repo_root = os.path.realpath(repo_root)
    manifest_path = os.path.abspath(manifest_path)
    try:
        original_info = os.lstat(manifest_path)
    except OSError as error:
        raise ValidationError("manifest is unavailable: {0}".format(error))
    if stat.S_ISLNK(original_info.st_mode) or not stat.S_ISREG(original_info.st_mode):
        raise ValidationError("manifest must be a regular, non-symlink file")
    manifest_real = os.path.realpath(manifest_path)
    try:
        inside = os.path.commonpath([repo_root, manifest_real]) == repo_root
    except ValueError:
        inside = False
    if not inside:
        raise ValidationError("manifest resolves outside the repository")
    if manifest_real != manifest_path:
        raise ValidationError("manifest traverses a symlink")
    manifest = load_json(manifest_path)
    _require_keys(manifest, EXPECTED_TOP_LEVEL_KEYS, "manifest")
    if manifest["schema_version"] != SCHEMA_VERSION:
        raise ValidationError("unsupported schema_version")
    if manifest["profile_id"] != PROFILE_ID:
        raise ValidationError("profile_id differs from the selected Rocky profile")
    if manifest["build_contract"] != EXPECTED_BUILD_CONTRACT:
        raise ValidationError("build_contract does not enforce the locked native Rust-only path")
    if manifest["destination"] != EXPECTED_DESTINATION:
        raise ValidationError("destination does not match the locked in-tree staging path")
    if manifest["target"] != EXPECTED_TARGET:
        raise ValidationError("target differs from the locked Rocky identity or overclaims resolved evidence")
    parent_integration = _validate_parent_integration(repo_root, manifest["parent_integration"])

    inputs = manifest["inputs"]
    if not isinstance(inputs, list) or len(inputs) != len(EXPECTED_INPUTS):
        raise ValidationError(
            "inputs must contain exactly Kbuild, Kconfig, the shared x86_64 ABI, "
            "the IHK queue module, OS registry, IKC master module, ioctl dispatcher, "
            "device registry, page allocator, page-owner registry, and SMP resource policy"
        )
    staged_files = [_validate_input(repo_root, item, index) for index, item in enumerate(inputs)]
    destinations = [item["destination"] for item in staged_files]
    if destinations != [
        "Kbuild",
        "Kconfig",
        "abi/x86_64.rs",
        "ikc_queue.rs",
        "os_registry.rs",
        "device_registry.rs",
        "ikc_master.rs",
        "ihk_ioctl.rs",
        "page_allocator.rs",
        "page_owner_registry.rs",
        "smp_resource.rs",
    ]:
        raise ValidationError(
            "inputs must be ordered as Kbuild, Kconfig, abi/x86_64.rs, "
            "ikc_queue.rs, os_registry.rs, device_registry.rs, ikc_master.rs, ihk_ioctl.rs, "
            "page_allocator.rs, page_owner_registry.rs, smp_resource.rs"
        )

    modules = manifest["modules"]
    if not isinstance(modules, list) or len(modules) != len(EXPECTED_MODULES):
        raise ValidationError("modules must contain exactly the three locked modules")
    blockers = []
    for index, expected in enumerate(EXPECTED_MODULES):
        source, module_blockers = _validate_module(repo_root, modules[index], expected, index)
        blockers.extend(module_blockers)
        staged_files.append(source)

    _require_keys(manifest["readiness"], {"blockers", "checkpoint", "credit_eligible"}, "readiness")
    if manifest["readiness"] != {
        "blockers": READINESS_BLOCKERS,
        "checkpoint": "crate_roots_bound",
        "credit_eligible": False,
    }:
        raise ValidationError("readiness must remain the locked crate-roots-bound state")
    blockers.extend(manifest["readiness"]["blockers"])
    if len({item["destination"] for item in staged_files}) != len(staged_files):
        raise ValidationError("staged destinations must be unique")
    if len({item["path"] for item in staged_files}) != len(staged_files):
        raise ValidationError("each staged destination must have a distinct repository input")

    deduplicated = []
    for blocker in blockers:
        if blocker not in deduplicated:
            deduplicated.append(blocker)
    return {
        "blockers": deduplicated,
        "credit_eligible": False,
        "destination": manifest["destination"]["kernel_relative_root"],
        "files": staged_files,
        "manifest": manifest,
        "manifest_path": manifest_path,
        "manifest_sha256": sha256_file(manifest_path),
        "parent_integration": parent_integration,
        "repo_root": repo_root,
    }


def _stage_lock(plan):
    parent = plan["parent_integration"]
    return {
        "files": [
            {"path": item["destination"], "sha256": item["sha256"]}
            for item in sorted(plan["files"], key=lambda value: value["destination"])
        ],
        "manifest_sha256": plan["manifest_sha256"],
        "parent_integration": {
            "bundle_sha256": parent["bundle_sha256"],
            "parent_files": [
                {
                    "path": item["path"],
                    "postimage_sha256": item["postimage_sha256"],
                    "preimage_sha256": item["preimage_sha256"],
                }
                for item in parent["bundle"]["parent_files"]
            ],
            "patch_sha256": parent["bundle"]["patch"]["sha256"],
        },
        "profile_id": PROFILE_ID,
        "schema_version": SCHEMA_VERSION,
        "target": EXPECTED_TARGET,
    }


def _evidence_stage_lock(plan):
    lock = _stage_lock(plan)
    lock.update(
        {
            "credit_eligible": False,
            "production_readiness_blockers": list(READINESS_BLOCKERS),
            "purpose": EVIDENCE_STAGE_PURPOSE,
        }
    )
    return lock


def _kernel_target(kernel_tree, destination):
    kernel_tree = os.path.abspath(kernel_tree)
    try:
        info = os.lstat(kernel_tree)
    except OSError as error:
        raise ValidationError("kernel tree is unavailable: {0}".format(error))
    if stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode):
        raise ValidationError("kernel tree must be a real directory, not a symlink")
    kernel_real = os.path.realpath(kernel_tree)
    target = os.path.join(kernel_real, _safe_relative_path(destination, "destination"))
    parent = os.path.dirname(target)
    parent_real = os.path.realpath(parent)
    if not os.path.isdir(parent) or parent_real != parent:
        raise ValidationError("staging parent must already exist without symlink traversal")
    if os.path.commonpath([kernel_real, parent_real]) != kernel_real:
        raise ValidationError("staging destination escapes the kernel tree")
    return target, parent


def _rename_directory_noreplace(parent, temporary, target):
    parent = os.path.abspath(parent)
    temporary = os.path.abspath(temporary)
    target = os.path.abspath(target)
    if os.path.dirname(temporary) != parent or os.path.dirname(target) != parent:
        raise ValidationError("no-replace rename requires sibling directories")
    old_name = os.path.basename(temporary)
    new_name = os.path.basename(target)
    if old_name in ("", ".", "..") or new_name in ("", ".", ".."):
        raise ValidationError("no-replace rename received an unsafe directory name")

    try:
        libc = ctypes.CDLL(None, use_errno=True)
        renameat2 = libc.renameat2
    except (AttributeError, OSError) as error:
        raise ValidationError("renameat2 is unavailable; refusing a racy staging rename: {0}".format(error))
    renameat2.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
    renameat2.restype = ctypes.c_int
    flags = os.O_RDONLY
    flags |= getattr(os, "O_DIRECTORY", 0)
    flags |= getattr(os, "O_CLOEXEC", 0)
    try:
        parent_fd = os.open(parent, flags)
    except OSError as error:
        raise ValidationError("cannot open staging parent for atomic rename: {0}".format(error))
    try:
        ctypes.set_errno(0)
        result = renameat2(
            parent_fd,
            os.fsencode(old_name),
            parent_fd,
            os.fsencode(new_name),
            1,
        )
        if result != 0:
            number = ctypes.get_errno()
            if number in (errno.EEXIST, errno.ENOTEMPTY):
                raise ValidationError("staging destination appeared concurrently: {0}".format(target))
            if number in (errno.ENOSYS, errno.EINVAL, errno.EOPNOTSUPP):
                raise ValidationError("atomic no-replace rename is unsupported; staging remains unchanged")
            raise ValidationError("atomic no-replace rename failed: {0}".format(os.strerror(number)))
    finally:
        os.close(parent_fd)


def _stage_locked(plan, kernel_tree, lock):
    target, parent = _kernel_target(kernel_tree, plan["destination"])
    if os.path.lexists(target):
        raise ValidationError("staging destination already exists: {0}".format(target))
    temporary = tempfile.mkdtemp(prefix=".mckernel-stage-", dir=parent)
    try:
        os.chmod(temporary, 0o755)
        for item in plan["files"]:
            destination = os.path.join(temporary, item["destination"])
            destination_parent = os.path.dirname(destination)
            if destination_parent != temporary and not os.path.isdir(destination_parent):
                os.makedirs(destination_parent, 0o755)
                os.chmod(destination_parent, 0o755)
            with open(item["path"], "rb") as source, open(destination, "wb") as output:
                shutil.copyfileobj(source, output)
            os.chmod(destination, 0o644)
        lock_path = os.path.join(temporary, "stage-lock.json")
        with open(lock_path, "wb") as stream:
            stream.write(canonical_json_bytes(lock))
        os.chmod(lock_path, 0o644)
        expected = {item["destination"]: item["sha256"] for item in plan["files"]}
        expected["stage-lock.json"] = sha256_bytes(canonical_json_bytes(lock))
        for name, digest in expected.items():
            if sha256_file(os.path.join(temporary, name)) != digest:
                raise ValidationError("staged temporary file digest mismatch: {0}".format(name))
        _rename_directory_noreplace(parent, temporary, target)
        temporary = None
    finally:
        if temporary is not None:
            shutil.rmtree(temporary)
    _verify_locked_stage(plan, kernel_tree, lock)
    return target


def _verify_locked_stage(plan, kernel_tree, lock):
    target, unused_parent = _kernel_target(kernel_tree, plan["destination"])
    del unused_parent
    try:
        info = os.lstat(target)
    except OSError as error:
        raise ValidationError("staged directory is unavailable: {0}".format(error))
    if stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode):
        raise ValidationError("staged destination must be a real directory")
    if stat.S_IMODE(info.st_mode) != 0o755:
        raise ValidationError("staged destination mode must be 0755")
    expected = {item["destination"]: item["sha256"] for item in plan["files"]}
    expected["stage-lock.json"] = sha256_bytes(canonical_json_bytes(lock))
    actual = []
    actual_directories = []
    for root, directories, files in os.walk(target):
        for directory in directories:
            actual_directories.append(os.path.relpath(os.path.join(root, directory), target))
        for name in files:
            actual.append(os.path.relpath(os.path.join(root, name), target))
    expected_directories = set()
    for name in expected:
        parent = os.path.dirname(name)
        while parent:
            expected_directories.add(parent)
            parent = os.path.dirname(parent)
    if set(actual_directories) != expected_directories:
        raise ValidationError("staged directory closure differs")
    for name in expected_directories:
        path = os.path.join(target, name)
        info = os.lstat(path)
        if stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode):
            raise ValidationError("staged directory must be real and non-symlink: {0}".format(name))
        if stat.S_IMODE(info.st_mode) != 0o755:
            raise ValidationError("staged directory mode must be 0755: {0}".format(name))
    if set(actual) != set(expected):
        raise ValidationError(
            "staged file closure differs: missing={0}, extra={1}".format(
                sorted(set(expected) - set(actual)), sorted(set(actual) - set(expected))
            )
        )
    for name, digest in expected.items():
        path = os.path.join(target, name)
        info = os.lstat(path)
        if stat.S_ISLNK(info.st_mode) or not stat.S_ISREG(info.st_mode):
            raise ValidationError("staged file must be regular and non-symlink: {0}".format(name))
        if sha256_file(path) != digest:
            raise ValidationError("staged file digest mismatch: {0}".format(name))
    if load_json(os.path.join(target, "stage-lock.json")) != lock:
        raise ValidationError("stage-lock.json content differs from the deterministic lock")
    return target


def stage(plan, kernel_tree):
    if not PRODUCTION_STAGE_ENABLED:
        raise ValidationError(
            "crate-roots-bound schema v{0} cannot stage production modules without build evidence".format(
                SCHEMA_VERSION
            )
        )
    if plan.get("credit_eligible") is not True or plan["blockers"]:
        raise ValidationError("staging is blocked: {0}".format("; ".join(plan["blockers"])))
    return _stage_locked(plan, kernel_tree, _stage_lock(plan))


def verify_stage(plan, kernel_tree):
    if not PRODUCTION_STAGE_ENABLED:
        raise ValidationError(
            "crate-roots-bound schema v{0} has no verifiable production stage".format(
                SCHEMA_VERSION
            )
        )
    if plan.get("credit_eligible") is not True or plan["blockers"]:
        raise ValidationError("stage verification requires a gate-ready manifest")
    return _verify_locked_stage(plan, kernel_tree, _stage_lock(plan))


def _require_evidence_only_plan(plan):
    if plan.get("credit_eligible") is not False:
        raise ValidationError("compiler-evidence staging may never claim gate credit")
    if plan.get("blockers") != READINESS_BLOCKERS:
        raise ValidationError("compiler-evidence staging requires the exact readiness blockers")


def stage_for_evidence(plan, kernel_tree):
    _require_evidence_only_plan(plan)
    return _stage_locked(plan, kernel_tree, _evidence_stage_lock(plan))


def verify_evidence_stage(plan, kernel_tree):
    _require_evidence_only_plan(plan)
    return _verify_locked_stage(plan, kernel_tree, _evidence_stage_lock(plan))


def _print_blockers(plan, stream):
    for blocker in plan["blockers"]:
        print("BLOCKED: {0}".format(blocker), file=stream)


def parse_args(argv):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    parser.add_argument("--manifest", default=DEFAULT_MANIFEST)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--check", action="store_true")
    action.add_argument("--gate-ready", action="store_true")
    action.add_argument("--verify-parent-source-archive", metavar="SOURCE_TAR_XZ")
    action.add_argument("--stage", metavar="KERNEL_TREE")
    action.add_argument("--verify-stage", metavar="KERNEL_TREE")
    action.add_argument("--stage-for-evidence", metavar="KERNEL_TREE")
    action.add_argument("--verify-evidence-stage", metavar="KERNEL_TREE")
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    repo_root = os.path.realpath(args.repo)
    manifest_path = args.manifest
    if not os.path.isabs(manifest_path):
        manifest_path = os.path.join(repo_root, manifest_path)
    try:
        plan = validate_manifest(repo_root, manifest_path)
        if args.check:
            print("Rocky Rust staging manifest integrity: PASS")
            if plan["blockers"]:
                print("Rocky Rust staging gate: NOT READY ({0} blockers)".format(len(plan["blockers"])))
                _print_blockers(plan, sys.stdout)
            return 0
        if args.gate_ready:
            print("Rocky Rust staging gate: NOT READY", file=sys.stderr)
            _print_blockers(plan, sys.stderr)
            return 1
        if args.verify_parent_source_archive:
            result = verify_parent_source_archive(plan, args.verify_parent_source_archive)
            print(
                "Rocky parent integration source verification: PASS ({0}, patch {1})".format(
                    result["archive_sha256"], result["patch_sha256"]
                )
            )
            print(
                "RK-007 credit: NOT ELIGIBLE (crate-roots-bound schema v{0})".format(
                    SCHEMA_VERSION
                )
            )
            return 0
        if args.stage:
            print("Staged native Rust inputs at {0}".format(stage(plan, args.stage)))
            return 0
        if args.verify_stage:
            print("Verified native Rust stage at {0}".format(verify_stage(plan, args.verify_stage)))
            return 0
        if args.stage_for_evidence:
            print(
                "Staged credit-forbidden compiler evidence inputs at {0}".format(
                    stage_for_evidence(plan, args.stage_for_evidence)
                )
            )
            print("RK-007 credit: NOT ELIGIBLE (compiler evidence only)")
            return 0
        print(
            "Verified credit-forbidden compiler evidence stage at {0}".format(
                verify_evidence_stage(plan, args.verify_evidence_stage)
            )
        )
        print("RK-007 credit: NOT ELIGIBLE (compiler evidence only)")
        return 0
    except (OSError, ValidationError) as error:
        print("Rocky Rust staging validation failed: {0}".format(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
