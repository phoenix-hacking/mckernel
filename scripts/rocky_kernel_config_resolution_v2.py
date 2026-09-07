#!/usr/bin/env python3
"""Capture deterministic, credit-forbidden RK-005 config resolution v2 evidence."""

from __future__ import print_function

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path, PurePosixPath

import rocky_kernel_platform_lock_v2 as platform_lock_v2


CONTRACT_PATH = Path("host-kernel/rocky/evidence/config-resolution-contract-v2.json")
WORKFLOW_PATH = Path(".github/workflows/rocky-kernel-config-resolution-v2.yml")
SOURCE_LOCK_PATH = Path("host-kernel/rocky/source-lock.json")
TOOLCHAIN_LOCK_PATH = Path("host-kernel/rocky/toolchain-lock.json")
CONFIG_POLICY_PATH = Path("host-kernel/rocky/config-policy-v2.json")
CONFIG_FRAGMENT_PATH = Path("host-kernel/rocky/configs/rust-minimal.config")
EXPECTED_CONTRACT_SHA256 = (
    "100510aa9352f07a3f866bcb9fd8ccab6f562391b658a8e20e843b90f31b7d00"
)
EXPECTED_WORKFLOW_SHA256 = (
    "9ef8d2df9f7f5059c92fb029470b0c5e48991d6221e93d8d7bba307cb1af5e9d"
)
CONTAINER_IMAGE = (
    "rockylinux/rockylinux:10.2@"
    "sha256:e372170ca8630f0f03e9b70fdd0bf4a3ce3426b0de7cdba615f06337389de176"
)
PHASE_ID = "config-resolution-v2"
SCHEMA_VERSION = 2
EXPECTED_CLAIM_SCOPE = (
    "RK-005 v2 deterministic configuration-resolution evidence only. This phase "
    "never awards gate or tracker credit, does not prove a production build, and "
    "does not supersede the RK-003 offline-toolchain or RK-006 compatibility-patch "
    "authorities."
)
EXPECTED_AUTHORITY_BINDINGS = {
    "config_policy": {
        "id": (
            "rocky-10.2-x86_64-kernel-6.12.0-211.44.1.el10_2-config-policy-v2"
        ),
        "path": "host-kernel/rocky/config-policy-v2.json",
        "sha256": (
            "9c746399387c7f32148a6a8e8814a19c629f4b905629a1b941c60d99ef3d64b7"
        ),
    },
    "source_lock": {
        "id": "rocky-10.2-x86_64-kernel-6.12.0-211.44.1.el10_2-source-v1",
        "path": "host-kernel/rocky/source-lock.json",
        "sha256": (
            "b70df1e475072dbfa31fdc712900ac59d30eeb139219c7076aacaa19abf0fded"
        ),
    },
    "toolchain_lock": {
        "id": (
            "rocky-10.2-x86_64-kernel-6.12.0-211.44.1.el10_2-toolchain-v1"
        ),
        "path": "host-kernel/rocky/toolchain-lock.json",
        "sha256": (
            "fd3d7a13e1b8b5d103f7e59d22f17c9e4b99cc937637decaa66749acfae6c802"
        ),
    },
}
EXPECTED_GENERATED_CLASSIFICATION = (
    "Resolve an unmodified control and the requested fragment under the same clean "
    "environment. Every locked-baseline-to-control change is enumerated as "
    "environment-generated; every control-to-resolved change is completely "
    "partitioned as requested, derived, generated, or explicit-n/absent presence "
    "drift; and every generated symbol is policy-allowlisted. The two independent "
    "runs and captured tool probes must agree."
)
EXPECTED_GENERATED_POLICY_SYMBOLS = [
    "CONFIG_BINDGEN_VERSION_TEXT",
    "CONFIG_PAHOLE_HAS_BTF_TAG",
    "CONFIG_PAHOLE_HAS_LANG_EXCLUDE",
    "CONFIG_PAHOLE_HAS_SPLIT_BTF",
    "CONFIG_PAHOLE_VERSION",
    "CONFIG_RUSTC_HAS_UNNECESSARY_TRANSMUTES",
    "CONFIG_RUSTC_LLVM_VERSION",
    "CONFIG_RUSTC_VERSION",
    "CONFIG_RUSTC_VERSION_TEXT",
    "CONFIG_RUST_IS_AVAILABLE",
]
EXPECTED_DIRECT_ARTIFACT_NAMES = [
    "rust",
    "rust-src",
    "rustfmt",
    "clippy",
    "cargo",
    "bindgen-cli",
    "clang",
    "clang-libs",
    "llvm",
    "llvm-libs",
    "lld",
    "dwarves",
    "bpftool",
    "rpm",
    "rpm-build",
    "rpm-sign",
    "redhat-rpm-config",
    "kernel-rpm-macros",
    "pesign",
    "kmod",
]
EXPECTED_RESOLUTION_COMPARISON = (
    "The complete resolved config bytes and normalized symbol maps from two "
    "independent clean source/build directories must be identical."
)
EXPECTED_ROCKY_SERIES_BINDING = {
    "path": "host-kernel/rocky/patches/series.json",
    "sha256": "6a1a5e8fb13b6ce6ed35bd8e5487bb67ecf92d2be927799b660f21b5631f68fb",
}
EXPECTED_SOURCE_ASSETS = {
    "baseline": {
        "path": "SOURCES/kernel-x86_64-rhel.config",
        "sha256": (
            "5bbdda60ce822ec903c85d3d8ddda1bfc9493216bed86c6c432683aa50dcf50d"
        ),
        "size": 254653,
    },
    "debrand_patch": {
        "path": "SOURCES/1000-debrand-some-messages.patch",
        "sha256": (
            "080bbc72a543eed6b71daee1b3236b59f3a0f8b3ad20815d962444d3b106b144"
        ),
        "size": 928,
    },
    "linux_archive": {
        "path": "SOURCES/linux-6.12.0-211.44.1.el10_2.tar.xz",
        "root": "linux-6.12.0-211.44.1.el10_2",
        "sha256": (
            "4a174d47b8874a2139efcd1ac1ab2d6b80ae7a0ca62f0ae4596fd20cf62a3533"
        ),
        "size": 153374592,
    },
    "process_configs": {
        "path": "SOURCES/process_configs.sh",
        "sha256": (
            "23501d7f0709000203940749953be512a36c55bd857ba35309224f902ed1e791"
        ),
        "size": 10883,
    },
}
EXPECTED_PRESERVATION_GROUP_SYMBOLS = {
    "btf_debug": (
        "CONFIG_BPF_SYSCALL",
        "CONFIG_DEBUG_INFO",
        "CONFIG_DEBUG_INFO_BTF",
        "CONFIG_DEBUG_INFO_BTF_MODULES",
        "CONFIG_DEBUG_INFO_DWARF_TOOLCHAIN_DEFAULT",
        "CONFIG_DEBUG_INFO_REDUCED",
        "CONFIG_DEBUG_INFO_SPLIT",
    ),
    "module_signing": (
        "CONFIG_CRYPTO_RSA",
        "CONFIG_CRYPTO_SHA512",
        "CONFIG_MODULES",
        "CONFIG_MODULE_ALLOW_BTF_MISMATCH",
        "CONFIG_MODULE_SIG",
        "CONFIG_MODULE_SIG_ALL",
        "CONFIG_MODULE_SIG_FORCE",
        "CONFIG_MODULE_SIG_KEY",
        "CONFIG_MODULE_SIG_KEY_TYPE_RSA",
        "CONFIG_MODULE_SIG_SHA512",
    ),
    "warning_policy": ("CONFIG_WERROR",),
}
EXPECTED_SUCCESS_BLOCKERS = [
    (
        "The RK-003 closure/offline artifact and its exact tool probes still require "
        "independent review and durable archival before RK-005 may inherit that "
        "authority."
    ),
    (
        "Compatibility patches 0006 through 0023 change source/build compatibility "
        "without adding configuration symbols; this phase binds and applies them but "
        "cannot substitute config resolution for their separate exact compile probes."
    ),
    (
        "A successful config-resolution artifact still requires independent review "
        "and durable archival before any authority lock may be updated."
    ),
    (
        "Both requested resolutions run make LLVM=1 rustavailable against their final "
        "external-build .config, but these hosted config-only invocations do not prove "
        "the offline RK-003 replay, a production compilation, or RK-005 credit."
    ),
    (
        "A production kernel build has not yet proved that its final .config "
        "byte-matches both independent resolutions."
    ),
    (
        "RK-002, RK-003, RK-004, RK-005, RK-006, RS-001, and tracker credit remain "
        "false."
    ),
]
HEX_SHA256 = re.compile(r"^[0-9a-f]{64}$")
HEX_SHA1 = re.compile(r"^[0-9a-f]{40}$")
GITHUB_REPOSITORY = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
CONFIG_VALUE = re.compile(r"^(CONFIG_[A-Za-z0-9_]+)=(.*)$")
CONFIG_UNSET = re.compile(r"^# (CONFIG_[A-Za-z0-9_]+) is not set$")
EXPECTED_WORKFLOW_USES = [
    "actions/checkout@11d5960a326750d5838078e36cf38b85af677262",
    "actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02",
]
EXPECTED_COMPATIBILITY_PATCHES = [
    "host-kernel/rocky/patches/0001-x86-rust-set-rustc-abi-x86-softfloat.patch",
    "host-kernel/rocky/patches/0002-rust-support-rust-1.91-target-spec.patch",
    "host-kernel/rocky/patches/0003-kbuild-rust-add-rustc-min-version.patch",
    "host-kernel/rocky/patches/0004-rust-compile-libcore-edition-2024.patch",
    "host-kernel/rocky/patches/0005-rust-clean-unnecessary-transmutes-lint.patch",
    "host-kernel/rocky/patches/0006-rust-init-allow-dead-code-rust-1.89.patch",
    "host-kernel/rocky/patches/0007-rust-use-used-compiler-rust-1.89.patch",
    "host-kernel/rocky/patches/0008-rust-enable-arbitrary-self-types-rust-1.92.patch",
    "host-kernel/rocky/patches/0009-rust-block-drop-removed-merge-flag.patch",
    "host-kernel/rocky/patches/0010-kbuild-disable-default-const-init-unsafe.patch",
    "host-kernel/rocky/patches/0011-mm-ksm-fix-clang-21-uninitialized.patch",
    "host-kernel/rocky/patches/0012-netfs-mark-nonstring-lookup-tables.patch",
    "host-kernel/rocky/patches/0013-lib-crypto-mark-binary-vectors-nonstring.patch",
    "host-kernel/rocky/patches/0014-gcc-15-mark-byte-arrays-nonstring.patch",
    "host-kernel/rocky/patches/0015-gcc-15-demote-unterminated-string-warning.patch",
    "host-kernel/rocky/patches/0016-gcc-15-disable-unterminated-string-warning.patch",
    "host-kernel/rocky/patches/0017-kbuild-use-cc-disable-warning.patch",
    "host-kernel/rocky/patches/0018-kbuild-order-unterminated-string-disable.patch",
    "host-kernel/rocky/patches/0019-rust-types-add-opaque-try-ffi-init.patch",
    "host-kernel/rocky/patches/0020-rust-miscdevice-add-base-abstraction.patch",
    "host-kernel/rocky/patches/0020a-rust-miscdevice-bind-file-operations-to-module.patch",
    "host-kernel/rocky/patches/0021-objtool-recognize-rust-1.92-panic-const.patch",
    "host-kernel/rocky/patches/0022-x86-pvh-annotate-noendbr.patch",
    "host-kernel/rocky/patches/0023-rust-update-no-alloc-shim-marker-rust-1.92.patch",
]
MODULE_OWNER_COMPATIBILITY_PATCH = (
    "host-kernel/rocky/patches/"
    "0020a-rust-miscdevice-bind-file-operations-to-module.patch"
)
MODULE_OWNER_LOCAL_ORIGIN = "McKernel RS-006 miscdevice module-owner compatibility"
MODULE_OWNER_ROCKY_BASE = "linux-6.12.0-211.44.1.el10_2"
MODULE_OWNER_LICENSE = "GPL-2.0"
MODULE_OWNER_INTEGRATION_STATUS = "active-ordered-unbuilt"
EXPECTED_OBJTOOL_NORETURN_FAILURE = {
    "artifact_id": 9160078637,
    "artifact_zip_bytes": 62669,
    "artifact_zip_sha256": (
        "e4c3786f8fed3255fcd4f4c9e9baba340527050bf5be1b044b9c81cdd5a4cfbc"
    ),
    "job_id": 94273299611,
    "objtool_diagnostic_count": 1,
    "repository_commit": "9438ad175b4c1ac7855f6afc119f154639fe18c2",
    "run_id": 31644047766,
    "rustc_version": "1.92.0",
    "symbol_fragment": "_4core9panicking11panic_const23panic_const_",
    "workflow": "Native Rust host modules exact Rocky build",
}
EXPECTED_OBJTOOL_NORETURN_PREIMAGE = {
    "path": "tools/objtool/check.c",
    "sha256": "71b836ba23a062554bc3038e8e8c7f940bfb38d05dec8d063ef87b70901d4f2e",
    "size": 116914,
}
EXPECTED_OBJTOOL_NORETURN_POSTIMAGE = {
    "path": "tools/objtool/check.c",
    "sha256": "2c8d113bcbf65bc0de8ad360f70bc707a0379baa925da01cebf0e95f23ce28e7",
    "size": 116993,
}
LOCAL_COMPATIBILITY_PATCH = EXPECTED_COMPATIBILITY_PATCHES[-2]
LOCAL_COMPATIBILITY_ORIGIN = "McKernel Rocky 10.2 exact-build compatibility"
LOCAL_COMPATIBILITY_ROCKY_BASE = "linux-6.12.0-211.44.1.el10_2"
LOCAL_COMPATIBILITY_LICENSE = "GPL-2.0-only"
LOCAL_COMPATIBILITY_FAILURE_EVIDENCE = {
    "artifact_id": 9145918955,
    "build_exit_code": 2,
    "build_log_bytes": 232963,
    "build_log_sha256": (
        "614f179c466c2721817fbc9b44c1dbaa9e45f4d638ed489e2b31c2c5beb69f6f"
    ),
    "build_phase": "bzImage",
    "diagnostic": (
        "pvh_start_xen+0x64: relocation to !ENDBR: pvh_start_xen+0x0"
    ),
    "failure_boundary": "LD vmlinux.o",
    "job_id": 94144112731,
    "repository_commit": "80a07871b81aa3d05378eb07b3d4cd9d8b922ef0",
    "run_id": 31605746750,
    "workflow": "Native Rust host modules exact Rocky build",
}
ALLOC_SHIM_COMPATIBILITY_PATCH = EXPECTED_COMPATIBILITY_PATCHES[-1]
ALLOC_SHIM_LOCAL_ORIGIN = "McKernel Rocky 10.2 exact-build compatibility"
ALLOC_SHIM_ROCKY_BASE = "linux-6.12.0-211.44.1.el10_2"
ALLOC_SHIM_LICENSE = "GPL-2.0-only"
ALLOC_SHIM_RUST_REFERENCE = {
    "commit": "6f935a044d1ddeb6160494a6320d008d7c311aef",
    "pull_request": 141061,
}
ALLOC_SHIM_LINUX_REFERENCE = {
    "allocator_removal_commit": "392e34b6bc22077ef63abf62387ea3e9f39418c1",
}
ALLOC_SHIM_PREIMAGES = [
    {
        "path": "rust/kernel/alloc/allocator.rs",
        "sha256": "15ce17c9dba35266ff57c1da606f98f2fa4ccb0048fea7d196cce22a4febdc3f",
        "size": 3079,
    },
    {
        "path": "rust/kernel/lib.rs",
        "sha256": "12079556f6e69f48db7fc887227e9243f9fc6837715afb5eaddf57bab8850cdd",
        "size": 4142,
    },
]
ALLOC_SHIM_POSTIMAGES = [
    {
        "path": "rust/kernel/alloc/allocator.rs",
        "sha256": "5eadd2f8bfd94c5f5636d674afdc7fa93de4f49ad09c199ab687235418010e3f",
        "size": 3146,
    },
    {
        "path": "rust/kernel/lib.rs",
        "sha256": "cde3e1e9608006f36c3a44ee11be848d8481c665f75b6d29937c9e9d9f76b0b6",
        "size": 4196,
    },
]
ALLOC_SHIM_FAILURE_EVIDENCE = {
    "artifact_id": 9305826810,
    "artifact_zip_bytes": 235955,
    "artifact_zip_sha256": (
        "c262ff48d96d1f3d8a9dc577b7cbfc52f6186bfc7c95a83c5db2634ca8f8749b"
    ),
    "build_exit_code": 2,
    "build_log_bytes": 234697,
    "build_log_sha256": (
        "beb8153582de991449fed2958746210cd060d4887cad79fe777d8cfe4b3d4b50"
    ),
    "build_phase": "bzImage",
    "diagnostic": (
        "undefined symbol: __rustc::__rust_no_alloc_shim_is_unstable_v2"
    ),
    "failure_boundary": "LD .tmp_vmlinux1",
    "job_id": 95547626904,
    "repository_commit": "6f662225cbb4067800b2a16cbcce81e85924a6bc",
    "run_id": 32082343363,
    "rustc_version": "1.92.0",
    "workflow": "Native Rust host modules exact Rocky build",
}
CAPTURE_ENVIRONMENT = {
    "ARCH": "x86_64",
    "HOME": "/root",
    "LANG": "C",
    "LC_ALL": "C",
    "PATH": "/usr/sbin:/usr/bin:/sbin:/bin",
    "TZ": "UTC",
}
PROBE_COMMANDS = {
    "bindgen": ["bindgen", "--version", "workaround-for-0.69.0"],
    "clang": ["clang", "--version"],
    "lld": ["ld.lld", "--version"],
    "llvm": ["llvm-config", "--version"],
    "pahole": ["pahole", "--version"],
    "rustc": ["rustc", "--version", "--verbose"],
}
RUST_SRC_PROBE_COMMAND = ["rustc", "--print", "sysroot"]
EVIDENCE_NAMES = [
    "baseline.config",
    "fragment.config",
    "control-pass-1.config",
    "control-pass-2.config",
    "resolved-pass-1.config",
    "resolved-pass-2.config",
    "commands.json",
    "environment.json",
    "config-delta.json",
    "dependency-assertions.json",
    "blockers.json",
    "checkpoint.json",
]


class ConfigResolutionError(RuntimeError):
    """Raised when RK-005 evidence cannot be captured exactly."""


def reject_duplicate_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ConfigResolutionError("duplicate JSON key: {!r}".format(key))
        result[key] = value
    return result


def canonical_json_bytes(value):
    try:
        text = json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        )
    except (TypeError, ValueError) as exc:
        raise ConfigResolutionError("value is not canonical JSON: {}".format(exc))
    return (text + "\n").encode("ascii")


def sha256_file(path):
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as stream:
        while True:
            chunk = stream.read(1024 * 1024)
            if not chunk:
                break
            size += len(chunk)
            digest.update(chunk)
    return size, digest.hexdigest()


def require_exact(value, expected, label):
    if value != expected or type(value) is not type(expected):
        raise ConfigResolutionError(
            "{} changed: actual={!r}, expected={!r}".format(label, value, expected)
        )


def exact_keys(value, expected, label):
    if not isinstance(value, dict) or set(value) != set(expected):
        actual = sorted(value) if isinstance(value, dict) else type(value).__name__
        raise ConfigResolutionError(
            "{} fields changed: actual={!r}, expected={!r}".format(
                label, actual, sorted(expected)
            )
        )
    return value


def read_json(path, label):
    if path.is_symlink() or not path.is_file():
        raise ConfigResolutionError("{} must be a regular file".format(label))
    data = path.read_bytes()
    try:
        value = json.loads(
            data.decode("utf-8"), object_pairs_hook=reject_duplicate_pairs
        )
    except (UnicodeDecodeError, ValueError) as exc:
        raise ConfigResolutionError("cannot parse {}: {}".format(label, exc))
    if not isinstance(value, dict):
        raise ConfigResolutionError("{} must contain a JSON object".format(label))
    return value, data


def safe_repo_file(repo, relative, label):
    path = PurePosixPath(str(relative))
    if path.is_absolute() or any(part in ("", ".", "..") for part in path.parts):
        raise ConfigResolutionError("{} path is unsafe".format(label))
    candidate = repo.joinpath(*path.parts)
    root = repo.resolve()
    resolved = candidate.resolve()
    try:
        common = os.path.commonpath((str(root), str(resolved)))
    except ValueError:
        common = ""
    if (
        common != str(root)
        or candidate != resolved
        or candidate.is_symlink()
        or not candidate.is_file()
    ):
        raise ConfigResolutionError("{} must be a confined regular file".format(label))
    return candidate


def regular_file(path, label):
    resolved = path.resolve()
    if path.is_symlink() or not resolved.is_file():
        raise ConfigResolutionError("{} must be a regular file".format(label))
    return resolved


def regular_directory(path, label):
    if path.is_symlink() or not path.is_dir() or path.resolve() != path:
        raise ConfigResolutionError("{} must be a canonical regular directory".format(label))
    return path


def validate_binding(repo, binding, label):
    exact_keys(binding, {"id", "path", "sha256"}, label)
    if not HEX_SHA256.fullmatch(str(binding["sha256"])):
        raise ConfigResolutionError("{} digest is malformed".format(label))
    path = safe_repo_file(repo, binding["path"], label)
    _, digest = sha256_file(path)
    require_exact(digest, binding["sha256"], label + " digest")
    value, _ = read_json(path, label)
    require_exact(value.get("lock_id"), binding["id"], label + " ID")
    return value


def validate_generated_policy_symbols(generated, policy):
    policy_symbols = (
        policy.get("verification_evidence", {})
        .get("olddefconfig_delta", {})
        .get("generated_symbol_allowlist")
    )
    require_exact(
        generated["policy_symbols"],
        EXPECTED_GENERATED_POLICY_SYMBOLS,
        "contract generated-symbol policy",
    )
    require_exact(
        policy_symbols,
        EXPECTED_GENERATED_POLICY_SYMBOLS,
        "config policy generated-symbol policy",
    )


def exact_direct_artifact_map(toolchain):
    rows = toolchain.get("direct_artifacts")
    if not isinstance(rows, list):
        raise ConfigResolutionError("toolchain direct_artifacts must be a list")
    artifacts = {}
    names = []
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            raise ConfigResolutionError(
                "toolchain direct_artifacts[{}] must be an object".format(index)
            )
        name = row.get("name")
        if not isinstance(name, str) or not name or name in artifacts:
            raise ConfigResolutionError(
                "toolchain direct_artifacts[{}] has a malformed or duplicate name".format(
                    index
                )
            )
        names.append(name)
        artifacts[name] = row
    require_exact(names, EXPECTED_DIRECT_ARTIFACT_NAMES, "direct artifact order")
    return artifacts


def validate_platform_authorities(repo, toolchain, policy, fragment_bytes):
    try:
        platform_lock_v2.validate_toolchain_lock(toolchain, repo)
        platform_lock_v2.validate_config_policy(policy, fragment_bytes, repo)
    except platform_lock_v2.PlatformLockError as exc:
        raise ConfigResolutionError(
            "bound platform authority is invalid: {}".format(exc)
        )


def require_patch_header(text, name, expected, label):
    values = re.findall(
        r"(?m)^{}: (.*)$".format(re.escape(name)),
        text,
    )
    require_exact(values, [str(expected)], label)


def validate_compatibility_patch_provenance(row, text, index):
    label = "compatibility patch {}".format(index)
    if row.get("path") == MODULE_OWNER_COMPATIBILITY_PATCH:
        exact_keys(
            row,
            {
                "integration_status",
                "license",
                "local_origin",
                "path",
                "rocky_base",
                "sha256",
            },
            label,
        )
        require_exact(row["local_origin"], MODULE_OWNER_LOCAL_ORIGIN, "module-owner origin")
        require_exact(row["rocky_base"], MODULE_OWNER_ROCKY_BASE, "module-owner Rocky base")
        require_exact(row["license"], MODULE_OWNER_LICENSE, "module-owner license")
        require_exact(
            row["integration_status"],
            MODULE_OWNER_INTEGRATION_STATUS,
            "module-owner integration status",
        )
        for forbidden in ("Upstream-Commit:", "Stable-Commit:"):
            if forbidden in text:
                raise ConfigResolutionError("module-owner patch invents provenance")
        for header in (
            "Status: active ordered Rocky compatibility patch; unbuilt and noncrediting",
            "License: GPL-2.0",
        ):
            require_exact(text.count(header), 1, "module-owner patch header")
        return
    if index == len(EXPECTED_COMPATIBILITY_PATCHES) - 3:
        exact_keys(
            row,
            {
                "observed_failure",
                "path",
                "postimage",
                "preimage",
                "sha256",
            },
            label,
        )
        require_exact(
            row["observed_failure"],
            EXPECTED_OBJTOOL_NORETURN_FAILURE,
            "observed Objtool failure",
        )
        require_exact(row["preimage"], EXPECTED_OBJTOOL_NORETURN_PREIMAGE, "Objtool preimage")
        require_exact(row["postimage"], EXPECTED_OBJTOOL_NORETURN_POSTIMAGE, "Objtool postimage")
        for field, expected in (
            ("Observed-Repository-Commit", "9438ad175b4c1ac7855f6afc119f154639fe18c2"),
            ("Observed-Run-ID", "31644047766"),
            ("Observed-Job-ID", "94273299611"),
            ("Observed-Artifact-ID", "9160078637"),
            ("Observed-Rustc", "1.92.0"),
        ):
            require_exact(
                text.count("{}: {}".format(field, expected)),
                1,
                "observed Objtool patch metadata",
            )
        for forbidden in ("Local-Origin:", "Upstream-Commit:", "Stable-Commit:"):
            if forbidden in text:
                raise ConfigResolutionError(
                    "observed Objtool patch invents provenance"
                )
        return
    if index == len(EXPECTED_COMPATIBILITY_PATCHES) - 2:
        exact_keys(
            row,
            {
                "failure_evidence",
                "license",
                "local_origin",
                "path",
                "rocky_base",
                "sha256",
                "stable_commit",
                "upstream_commit",
            },
            label,
        )
        require_exact(row["path"], LOCAL_COMPATIBILITY_PATCH, "local patch path")
        require_exact(row["upstream_commit"], None, "local upstream commit")
        require_exact(row["stable_commit"], None, "local stable commit")
        require_exact(
            row["local_origin"],
            LOCAL_COMPATIBILITY_ORIGIN,
            "local compatibility origin",
        )
        require_exact(
            row["rocky_base"],
            LOCAL_COMPATIBILITY_ROCKY_BASE,
            "local compatibility Rocky base",
        )
        require_exact(
            row["license"],
            LOCAL_COMPATIBILITY_LICENSE,
            "local compatibility license",
        )
        failure = exact_keys(
            row["failure_evidence"],
            set(LOCAL_COMPATIBILITY_FAILURE_EVIDENCE),
            "local compatibility failure evidence",
        )
        require_exact(
            failure,
            LOCAL_COMPATIBILITY_FAILURE_EVIDENCE,
            "local compatibility failure evidence",
        )
        for forbidden in ("Upstream-Commit", "Stable-Commit"):
            if re.search(r"(?m)^{}: ".format(re.escape(forbidden)), text):
                raise ConfigResolutionError(
                    "local compatibility patch must not claim {}".format(forbidden)
                )
        mail_commits = re.findall(
            r"\AFrom ([0-9a-f]{40}) Mon Sep 17 00:00:00 2001$",
            text,
            re.MULTILINE,
        )
        require_exact(
            mail_commits,
            ["0" * 40],
            "local compatibility patch mail identity",
        )
        require_patch_header(
            text,
            "Local-Origin",
            LOCAL_COMPATIBILITY_ORIGIN,
            "local compatibility origin header",
        )
        require_patch_header(
            text,
            "Rocky-Base",
            row["rocky_base"],
            "local compatibility Rocky base header",
        )
        failure_headers = {
            "Failure-Artifact": failure["artifact_id"],
            "Failure-Commit": failure["repository_commit"],
            "Failure-Exit-Code": failure["build_exit_code"],
            "Failure-Job": failure["job_id"],
            "Failure-Log-Bytes": failure["build_log_bytes"],
            "Failure-Log-SHA256": failure["build_log_sha256"],
            "Failure-Phase": failure["build_phase"],
            "Failure-Run": failure["run_id"],
        }
        for name, value in failure_headers.items():
            require_patch_header(
                text,
                name,
                value,
                "local compatibility {} header".format(name),
            )
        require_patch_header(
            text,
            "License",
            row["license"],
            "local compatibility license header",
        )
        return

    if index == len(EXPECTED_COMPATIBILITY_PATCHES) - 1:
        exact_keys(
            row,
            {
                "failure_evidence",
                "license",
                "linux_reference",
                "local_origin",
                "path",
                "postimages",
                "preimages",
                "rocky_base",
                "rust_reference",
                "sha256",
                "stable_commit",
                "upstream_commit",
            },
            label,
        )
        require_exact(row["path"], ALLOC_SHIM_COMPATIBILITY_PATCH, "allocator patch path")
        require_exact(row["upstream_commit"], None, "allocator upstream commit")
        require_exact(row["stable_commit"], None, "allocator stable commit")
        require_exact(row["local_origin"], ALLOC_SHIM_LOCAL_ORIGIN, "allocator origin")
        require_exact(row["rocky_base"], ALLOC_SHIM_ROCKY_BASE, "allocator Rocky base")
        require_exact(row["license"], ALLOC_SHIM_LICENSE, "allocator license")
        require_exact(
            row["failure_evidence"], ALLOC_SHIM_FAILURE_EVIDENCE, "allocator failure evidence"
        )
        require_exact(row["preimages"], ALLOC_SHIM_PREIMAGES, "allocator preimages")
        require_exact(row["postimages"], ALLOC_SHIM_POSTIMAGES, "allocator postimages")
        require_exact(
            row["rust_reference"], ALLOC_SHIM_RUST_REFERENCE, "allocator Rust reference"
        )
        require_exact(
            row["linux_reference"],
            ALLOC_SHIM_LINUX_REFERENCE,
            "allocator Linux reference",
        )
        for forbidden in ("Upstream-Commit", "Stable-Commit"):
            if re.search(r"(?m)^{}: ".format(re.escape(forbidden)), text):
                raise ConfigResolutionError(
                    "allocator compatibility patch must not claim {}".format(forbidden)
                )
        mail_commits = re.findall(
            r"\AFrom ([0-9a-f]{40}) Mon Sep 17 00:00:00 2001$",
            text,
            re.MULTILINE,
        )
        require_exact(mail_commits, ["0" * 40], "allocator patch mail identity")
        for name, value in (
            ("Observed-Repository-Commit", ALLOC_SHIM_FAILURE_EVIDENCE["repository_commit"]),
            ("Observed-Workflow", ALLOC_SHIM_FAILURE_EVIDENCE["workflow"]),
            ("Observed-Run-ID", ALLOC_SHIM_FAILURE_EVIDENCE["run_id"]),
            ("Observed-Job-ID", ALLOC_SHIM_FAILURE_EVIDENCE["job_id"]),
            ("Observed-Artifact-ID", ALLOC_SHIM_FAILURE_EVIDENCE["artifact_id"]),
            ("Observed-Artifact-Zip-Bytes", ALLOC_SHIM_FAILURE_EVIDENCE["artifact_zip_bytes"]),
            ("Observed-Artifact-Zip-SHA256", ALLOC_SHIM_FAILURE_EVIDENCE["artifact_zip_sha256"]),
            ("Observed-Rustc", ALLOC_SHIM_FAILURE_EVIDENCE["rustc_version"]),
            ("Observed-Failure-Phase", ALLOC_SHIM_FAILURE_EVIDENCE["build_phase"]),
            ("Observed-Build-Log-Bytes", ALLOC_SHIM_FAILURE_EVIDENCE["build_log_bytes"]),
            ("Observed-Build-Log-SHA256", ALLOC_SHIM_FAILURE_EVIDENCE["build_log_sha256"]),
            ("Observed-Diagnostic", ALLOC_SHIM_FAILURE_EVIDENCE["diagnostic"]),
            ("Rust-Reference-PR", ALLOC_SHIM_RUST_REFERENCE["pull_request"]),
            ("Rust-Reference-Commit", ALLOC_SHIM_RUST_REFERENCE["commit"]),
            ("Local-Origin", ALLOC_SHIM_LOCAL_ORIGIN),
            ("Rocky-Base", ALLOC_SHIM_ROCKY_BASE),
            ("License", ALLOC_SHIM_LICENSE),
        ):
            require_patch_header(text, name, value, "allocator {} header".format(name))
        require_exact(
            text.count(ALLOC_SHIM_LINUX_REFERENCE["allocator_removal_commit"]),
            1,
            "allocator Linux reference",
        )
        require_exact(
            text.count(
                "+#![allow(internal_features)]\n+#![feature(rustc_attrs)]"
            ),
            1,
            "allocator internal-feature warning scope",
        )
        return

    if re.search(r"(?m)^Local-Origin: ", text):
        raise ConfigResolutionError(
            "upstream compatibility patch must not claim local origin"
        )
    expected_fields = {"path", "sha256"}
    identity_count = 0
    for field, prefix in (
        ("upstream_commit", "Upstream-Commit: "),
        ("stable_commit", "Stable-Commit: "),
    ):
        identities = re.findall(
            r"(?m)^{}([0-9a-f]{{40}})$".format(re.escape(prefix)), text
        )
        if identities:
            if len(identities) != 1:
                raise ConfigResolutionError(
                    "compatibility patch identity is ambiguous"
                )
            expected_fields.add(field)
            identity_count += 1
            require_exact(row.get(field), identities[0], field)
    if identity_count == 0:
        mail_commits = re.findall(
            r"\AFrom ([0-9a-f]{40}) Mon Sep 17 00:00:00 2001$",
            text,
            re.MULTILINE,
        )
        if len(mail_commits) != 1:
            raise ConfigResolutionError(
                "compatibility patch has no unique commit identity"
            )
        expected_fields.add("upstream_commit")
        require_exact(row.get("upstream_commit"), mail_commits[0], "upstream_commit")
    exact_keys(row, expected_fields, label)


def validate_contract(repo):
    path = safe_repo_file(repo, CONTRACT_PATH.as_posix(), "config contract")
    contract, data = read_json(path, "config contract")
    require_exact(
        hashlib.sha256(data).hexdigest(),
        EXPECTED_CONTRACT_SHA256,
        "config contract digest",
    )
    exact_keys(
        contract,
        {
            "architecture",
            "claim_scope",
            "config_policy",
            "conditional_dependencies",
            "dependency_symbols",
            "derived_delta",
            "gate_claims",
            "generated_environment",
            "outputs",
            "patch_authority",
            "phase_id",
            "preservation_groups",
            "process_configs",
            "requested_delta",
            "resolution_classification",
            "resolution",
            "schema_version",
            "source_assets",
            "source_lock",
            "success_blockers",
            "tool_environment",
            "toolchain_lock",
        },
        "config contract",
    )
    require_exact(contract["schema_version"], SCHEMA_VERSION, "contract schema")
    require_exact(contract["phase_id"], PHASE_ID, "contract phase")
    require_exact(contract["architecture"], "x86_64", "contract architecture")
    require_exact(contract["claim_scope"], EXPECTED_CLAIM_SCOPE, "claim scope")
    require_exact(contract["source_assets"], EXPECTED_SOURCE_ASSETS, "source assets")
    expected_claims = {
        "RK-002": False,
        "RK-003": False,
        "RK-004": False,
        "RK-005": False,
        "RK-006": False,
        "RS-001": False,
    }
    require_exact(contract["gate_claims"], expected_claims, "gate claims")
    for binding_name, expected_binding in EXPECTED_AUTHORITY_BINDINGS.items():
        require_exact(
            contract[binding_name],
            expected_binding,
            "{} binding".format(binding_name.replace("_", " ")),
        )
    source = validate_binding(repo, contract["source_lock"], "source lock")
    toolchain = validate_binding(repo, contract["toolchain_lock"], "toolchain lock")
    policy = validate_binding(repo, contract["config_policy"], "config policy")
    require_exact(source.get("gate", {}).get("credit_eligible"), False, "RK-001 credit")
    require_exact(toolchain.get("gate", {}).get("credit_eligible"), False, "RK-003 credit")
    require_exact(policy.get("gate", {}).get("credit_eligible"), False, "RK-005 credit")
    outputs = contract["outputs"]
    require_exact(outputs, EVIDENCE_NAMES + ["SHA256SUMS"], "contract outputs")

    requested = contract["requested_delta"]
    require_exact(
        requested,
        [
            {"baseline": "n", "resolved": "y", "symbol": "CONFIG_RUST"},
            {
                "baseline": "y",
                "resolved": "n",
                "symbol": "CONFIG_MODVERSIONS",
            },
        ],
        "requested delta",
    )
    require_exact(
        contract["derived_delta"],
        [
            {
                "baseline": "y",
                "depends_on": "CONFIG_MODVERSIONS",
                "reason": (
                    "CONFIG_ASM_MODVERSIONS is visible only when "
                    "CONFIG_MODVERSIONS is enabled."
                ),
                "resolved": "n",
                "symbol": "CONFIG_ASM_MODVERSIONS",
            }
        ],
        "derived delta",
    )
    require_exact(
        contract["conditional_dependencies"],
        {
            "CONFIG_CALL_PADDING": {
                "allowed_values": ["n", "y"],
                "rustc_minimum_if_y": 108100,
            }
        },
        "conditional dependencies",
    )
    policy_requested = [
        {
            "baseline": item["baseline"],
            "resolved": item["resolved"],
            "symbol": item["symbol"],
        }
        for item in policy.get("delta", {}).get("changes", [])
    ]
    require_exact(policy_requested, requested, "policy requested delta")
    fragment = safe_repo_file(
        repo, policy["delta"]["fragment_path"], "config fragment"
    )
    _, fragment_digest = sha256_file(fragment)
    require_exact(
        fragment_digest, policy["delta"]["fragment_sha256"], "fragment digest"
    )
    validate_platform_authorities(repo, toolchain, policy, fragment.read_bytes())

    generated = exact_keys(
        contract["generated_environment"],
        {
            "classification",
            "policy_symbols",
            "symbol_rules",
            "unexpected_symbols_forbidden",
        },
        "generated environment",
    )
    require_exact(
        generated["classification"],
        EXPECTED_GENERATED_CLASSIFICATION,
        "generated classification",
    )
    validate_generated_policy_symbols(generated, policy)
    symbol_rules = exact_keys(
        generated["symbol_rules"],
        {"CONFIG_RUSTC_HAS_UNNECESSARY_TRANSMUTES"},
        "generated symbol rules",
    )
    require_exact(
        symbol_rules["CONFIG_RUSTC_HAS_UNNECESSARY_TRANSMUTES"],
        {
            "expected": "y",
            "minimum_rustc_version": 108800,
            "patch": (
                "host-kernel/rocky/patches/"
                "0005-rust-clean-unnecessary-transmutes-lint.patch"
            ),
        },
        "transmute generated-symbol rule",
    )
    require_exact(
        generated["symbol_rules"],
        policy["verification_evidence"]["olddefconfig_delta"][
            "generated_symbol_rules"
        ],
        "policy generated-symbol rules",
    )
    require_exact(
        generated["unexpected_symbols_forbidden"], True, "unexpected symbol policy"
    )
    classification = {
        "baseline_to_control": "environment-generated",
        "complete_partition_required": True,
        "control_to_resolved": [
            "requested",
            "derived",
            "generated",
            "presence",
        ],
        "stages": ["baseline", "control", "resolved"],
        "unclassified_changes_forbidden": True,
    }
    require_exact(
        contract["resolution_classification"],
        classification,
        "resolution classification",
    )
    require_exact(
        policy.get("resolution_classification"),
        classification,
        "policy resolution classification",
    )
    require_exact(
        contract["preservation_groups"].get("warning_policy"),
        {"CONFIG_WERROR": "y"},
        "warning preservation policy",
    )
    policy_preserve = {}
    for index, row in enumerate(policy.get("preserve", [])):
        item = exact_keys(row, {"symbol", "value"}, "policy preserve {}".format(index))
        if item["symbol"] in policy_preserve:
            raise ConfigResolutionError("policy preservation symbol is duplicated")
        policy_preserve[item["symbol"]] = item["value"]
    require_exact(
        policy_preserve.get("CONFIG_WERROR"), "y", "policy CONFIG_WERROR"
    )
    expected_preservation_groups = {}
    for group, symbols in EXPECTED_PRESERVATION_GROUP_SYMBOLS.items():
        values = {}
        for symbol in symbols:
            if symbol not in policy_preserve:
                raise ConfigResolutionError(
                    "policy preservation symbol is missing: {}".format(symbol)
                )
            values[symbol] = policy_preserve[symbol]
        expected_preservation_groups[group] = values
    require_exact(
        contract["preservation_groups"],
        expected_preservation_groups,
        "preservation groups",
    )

    policy_dependency_rows = (
        policy.get("dependency_contract", {}).get("requirements")
    )
    if not isinstance(policy_dependency_rows, list):
        raise ConfigResolutionError("policy dependency requirements must be a list")
    require_exact(
        policy_dependency_rows,
        platform_lock_v2.EXPECTED_DEPENDENCY_REQUIREMENTS_V2,
        "policy dependency requirements",
    )
    policy_dependencies = {}
    for index, row in enumerate(policy_dependency_rows):
        item = exact_keys(
            row,
            {"expected", "source", "symbol"},
            "policy dependency {}".format(index),
        )
        symbol = item["symbol"]
        expected = item["expected"]
        if (
            not isinstance(symbol, str)
            or not isinstance(expected, str)
            or symbol in policy_dependencies
        ):
            raise ConfigResolutionError(
                "policy dependency {} is malformed or duplicated".format(index)
            )
        policy_dependencies[symbol] = expected
    expected_dependency_symbols = {
        symbol: expected
        for symbol, expected in policy_dependencies.items()
        if symbol not in contract["conditional_dependencies"]
    }
    require_exact(
        contract["dependency_symbols"],
        expected_dependency_symbols,
        "dependency symbols",
    )

    patch_authority = exact_keys(
        contract["patch_authority"],
        {"configuration_effects", "rocky_series", "rust_compatibility"},
        "patch authority",
    )
    configuration_effects = exact_keys(
        patch_authority["configuration_effects"],
        {"generated_symbols", "no_config_symbol_changes"},
        "patch configuration effects",
    )
    require_exact(
        configuration_effects["generated_symbols"],
        {
            "CONFIG_RUSTC_HAS_UNNECESSARY_TRANSMUTES": (
                "host-kernel/rocky/patches/"
                "0005-rust-clean-unnecessary-transmutes-lint.patch"
            )
        },
        "patch-generated symbols",
    )
    require_exact(
        configuration_effects["no_config_symbol_changes"],
        EXPECTED_COMPATIBILITY_PATCHES[:4] + EXPECTED_COMPATIBILITY_PATCHES[5:],
        "patches without config symbols",
    )
    rocky_series = exact_keys(
        patch_authority["rocky_series"], {"path", "sha256"}, "Rocky patch series"
    )
    require_exact(
        rocky_series,
        EXPECTED_ROCKY_SERIES_BINDING,
        "Rocky patch series binding",
    )
    require_exact(
        source.get("patch_series"),
        EXPECTED_ROCKY_SERIES_BINDING,
        "source lock patch series binding",
    )
    series_path = safe_repo_file(repo, rocky_series["path"], "Rocky patch series")
    _, series_digest = sha256_file(series_path)
    require_exact(series_digest, rocky_series["sha256"], "Rocky series digest")
    patches = patch_authority["rust_compatibility"]
    if not isinstance(patches, list) or len(patches) != len(
        EXPECTED_COMPATIBILITY_PATCHES
    ):
        raise ConfigResolutionError(
            "exactly {} compatibility patches are required".format(
                len(EXPECTED_COMPATIBILITY_PATCHES)
            )
        )
    patch_directory = repo / "host-kernel/rocky/patches"
    discovered_patches = sorted(
        path.relative_to(repo).as_posix()
        for path in patch_directory.glob("[0-9]*.patch")
    )
    require_exact(
        discovered_patches,
        EXPECTED_COMPATIBILITY_PATCHES,
        "repository compatibility patch authority",
    )
    require_exact(
        [row.get("path") for row in patches],
        EXPECTED_COMPATIBILITY_PATCHES,
        "compatibility patch order",
    )
    for index, row in enumerate(patches):
        if not isinstance(row, dict):
            raise ConfigResolutionError(
                "compatibility patch {} must be an object".format(index)
            )
        if "path" not in row or "sha256" not in row:
            raise ConfigResolutionError(
                "compatibility patch {} lacks a path or digest".format(index)
            )
        patch = safe_repo_file(repo, row["path"], "compatibility patch")
        _, digest = sha256_file(patch)
        require_exact(digest, row["sha256"], "compatibility patch digest")
        text = patch.read_text(encoding="utf-8")
        validate_compatibility_patch_provenance(row, text, index)
        changed_paths = re.findall(
            r"(?m)^diff --git a/(\S+) b/(\S+)$", text
        )
        if not changed_paths or any(left != right for left, right in changed_paths):
            raise ConfigResolutionError("compatibility patch paths are ambiguous")
        if row["path"] in configuration_effects["no_config_symbol_changes"]:
            if any(
                PurePosixPath(left).name.startswith("Kconfig")
                for left, _ in changed_paths
            ):
                raise ConfigResolutionError(
                    "no-config compatibility patch changes Kconfig"
                )
        else:
            require_exact(
                text.count("config RUSTC_HAS_UNNECESSARY_TRANSMUTES"),
                1,
                "supplemental generated-symbol definition",
            )

    process = exact_keys(
        contract["process_configs"],
        {"command", "environment", "path", "sha256", "source", "working_directory"},
        "process_configs authority",
    )
    require_exact(
        process["sha256"],
        contract["source_assets"]["process_configs"]["sha256"],
        "process_configs asset digest",
    )
    require_exact(
        process["path"],
        "redhat/configs/process_configs.sh",
        "process_configs path",
    )
    require_exact(
        process["source"],
        (
            "Source81 of the exact Rocky kernel SRPM and byte-identical "
            "redhat/configs source copy"
        ),
        "process_configs source",
    )
    require_exact(
        process["command"],
        [
            "SOURCE_ROOT/redhat/configs/process_configs.sh",
            "-m",
            "LLVM=1",
            "6.12.0",
            "rhel",
        ],
        "process_configs command",
    )
    process_environment = dict(CAPTURE_ENVIRONMENT)
    process_environment.update(
        {
            "FLAVOR": "rhel",
            "RHJOBS": "1",
            "SPECPACKAGE_NAME": "kernel-rk005-{control,requested}-pass-N",
        }
    )
    require_exact(
        process["environment"], process_environment, "process_configs environment"
    )
    require_exact(
        process["working_directory"],
        "SOURCE_ROOT/redhat/configs",
        "process_configs working directory",
    )
    resolution = exact_keys(
        contract["resolution"],
        {
            "clean_build_directories",
            "comparison",
            "fragment_merge_command",
            "olddefconfig_command",
            "passes",
            "process_configs_required",
            "rustavailable",
            "source_cleanup_command",
        },
        "resolution commands",
    )
    require_exact(resolution["passes"], 2, "resolution pass count")
    require_exact(
        resolution["clean_build_directories"], True, "clean resolution directories"
    )
    require_exact(
        resolution["process_configs_required"], True, "process_configs requirement"
    )
    require_exact(
        resolution["fragment_merge_command"],
        [
            "SOURCE_ROOT/scripts/kconfig/merge_config.sh",
            "-m",
            "-O",
            "MERGE_DIR",
            "MERGE_DIR/.config",
            "FRAGMENT",
        ],
        "fragment merge command",
    )
    require_exact(
        resolution["olddefconfig_command"],
        [
            "make",
            "-C",
            "SOURCE_ROOT",
            "O=BUILD_DIR",
            "ARCH=x86_64",
            "LLVM=1",
            "olddefconfig",
        ],
        "olddefconfig command",
    )
    require_exact(
        resolution["source_cleanup_command"],
        [
            "make",
            "-C",
            "SOURCE_ROOT",
            "ARCH=x86_64",
            "LLVM=1",
            "mrproper",
        ],
        "source cleanup command",
    )
    require_exact(
        resolution["rustavailable"],
        {
            "command": [
                "make",
                "-C",
                "SOURCE_ROOT",
                "O=REQUESTED_BUILD_DIR",
                "ARCH=x86_64",
                "LLVM=1",
                "rustavailable",
            ],
            "passes": 2,
            "required_stdout_line": "Rust is available!",
            "stderr_must_be_empty": True,
        },
        "rustavailable resolution",
    )
    require_exact(
        resolution["comparison"],
        EXPECTED_RESOLUTION_COMPARISON,
        "resolution comparison",
    )
    require_exact(
        contract["success_blockers"],
        EXPECTED_SUCCESS_BLOCKERS,
        "success blockers",
    )
    tool_environment = exact_keys(
        contract["tool_environment"],
        {
            "expected_binary_owners",
            "expected_file_owners",
            "expected_rustc_llvm_version",
            "expected_versions",
            "fixed_environment",
            "llvm_config_owner_policy",
            "probe_commands",
        },
        "tool environment",
    )
    require_exact(
        tool_environment["fixed_environment"],
        CAPTURE_ENVIRONMENT,
        "fixed capture environment",
    )
    expected_versions = {
        "bindgen": "0.72.1",
        "clang": "21.1.8",
        "lld": "21.1.8",
        "llvm": "21.1.8",
        "pahole": "1.31",
        "rustc": "1.92.0",
    }
    require_exact(
        tool_environment["expected_versions"], expected_versions, "tool versions"
    )
    require_exact(
        tool_environment["expected_rustc_llvm_version"],
        "21.1.6",
        "rustc bundled LLVM version",
    )
    expected_probe_commands = dict(PROBE_COMMANDS)
    expected_probe_commands["rust_src_core"] = RUST_SRC_PROBE_COMMAND
    require_exact(
        tool_environment["probe_commands"],
        expected_probe_commands,
        "tool probe commands",
    )
    artifact_by_name = exact_direct_artifact_map(toolchain)
    expected_owners = {
        "bindgen": artifact_by_name["bindgen-cli"]["nevra"],
        "clang": artifact_by_name["clang"]["nevra"],
        "lld": artifact_by_name["lld"]["nevra"],
        "llvm": "llvm-devel-0:21.1.8-1.el10.x86_64",
        "pahole": artifact_by_name["dwarves"]["nevra"],
        "rustc": artifact_by_name["rust"]["nevra"],
    }
    require_exact(
        tool_environment["expected_binary_owners"], expected_owners, "tool owners"
    )
    require_exact(
        tool_environment["expected_file_owners"],
        {"rust_src_core": artifact_by_name["rust-src"]["nevra"]},
        "tool file owners",
    )
    require_exact(
        artifact_by_name["llvm"]["nevra"],
        "llvm-0:21.1.8-1.el10.x86_64",
        "historical LLVM artifact authority",
    )
    expected_llvm_owner_policy = {
        "binary_path": "/usr/bin/llvm-config",
        "command": ["llvm-config", "--version"],
        "expected_package_nevra": "llvm-devel-0:21.1.8-1.el10.x86_64",
        "historical_direct_artifact_name": "llvm",
        "historical_direct_artifact_nevra": "llvm-0:21.1.8-1.el10.x86_64",
        "scope": (
            "RK-005 binary-owner reconciliation only; this does not amend RK-003, "
            "prove offline closure, or grant gate credit."
        ),
    }
    require_exact(
        tool_environment["llvm_config_owner_policy"],
        expected_llvm_owner_policy,
        "LLVM owner policy",
    )
    require_exact(
        policy.get("tool_owner_policy", {}).get("llvm_config"),
        expected_llvm_owner_policy,
        "config policy LLVM owner",
    )
    return contract


def validate_workflow(repo):
    path = safe_repo_file(repo, WORKFLOW_PATH.as_posix(), "config workflow")
    data = path.read_bytes()
    require_exact(
        hashlib.sha256(data).hexdigest(), EXPECTED_WORKFLOW_SHA256, "workflow digest"
    )
    text = data.decode("utf-8")
    required_counts = {
        "python3 scripts/rocky_kernel_config_resolution_v2.py": 2,
        "python3 scripts/rocky_kernel_platform_lock_v2.py": 1,
        "--phase config-resolution-v2": 1,
        "credit forbidden": 1,
        "compression-level: 0": 1,
        "permissions:\n  contents: read": 1,
        "runs-on: ubuntu-24.04": 1,
        "image: " + CONTAINER_IMAGE: 1,
        "persist-credentials: false": 1,
        "include-hidden-files: true": 1,
    }
    for needle, count in required_counts.items():
        require_exact(text.count(needle), count, "workflow fragment {!r}".format(needle))
    uses = []
    for line in text.splitlines():
        if re.match(r"^\s*uses\s*:", line):
            match = re.fullmatch(r"\s*uses:\s+(\S+)(?:\s+#.*)?", line)
            if match is None:
                raise ConfigResolutionError("workflow action identity is ambiguous")
            uses.append(match.group(1))
    require_exact(uses, EXPECTED_WORKFLOW_USES, "workflow actions")


def validate_identity(head_sha, run_id, run_attempt, repository, container_image):
    if not HEX_SHA1.fullmatch(str(head_sha)):
        raise ConfigResolutionError("GitHub head SHA is malformed")
    if not str(run_id).isdigit() or int(run_id) < 1:
        raise ConfigResolutionError("GitHub run ID is malformed")
    if not str(run_attempt).isdigit() or int(run_attempt) < 1:
        raise ConfigResolutionError("GitHub run attempt is malformed")
    if not GITHUB_REPOSITORY.fullmatch(str(repository)):
        raise ConfigResolutionError("GitHub repository identity is malformed")
    require_exact(container_image, CONTAINER_IMAGE, "container image")
    return {
        "head_sha": head_sha,
        "repository": repository,
        "run_attempt": int(run_attempt),
        "run_id": int(run_id),
    }


def parse_config(path):
    values = {}
    text = regular_file(path, "config").read_text(encoding="utf-8")
    for line in text.splitlines():
        match = CONFIG_VALUE.fullmatch(line)
        if match:
            symbol, value = match.groups()
        else:
            match = CONFIG_UNSET.fullmatch(line)
            if not match:
                continue
            symbol, value = match.group(1), "n"
        if symbol in values:
            raise ConfigResolutionError("duplicate config symbol {}".format(symbol))
        values[symbol] = value
    if not values:
        raise ConfigResolutionError("config contains no symbols")
    return values


def changed_symbols(before, after):
    return [
        {
            "before": before.get(symbol, "<absent>"),
            "after": after.get(symbol, "<absent>"),
            "symbol": symbol,
        }
        for symbol in sorted(set(before) | set(after))
        if before.get(symbol, "<absent>") != after.get(symbol, "<absent>")
    ]


def semantic_config_value(value):
    # Kconfig may omit a disabled bool/tristate when a dependency hides it, or
    # materialize the same value as ``# CONFIG_FOO is not set`` when the
    # dependency becomes visible.  parse_config() represents the latter as
    # ``n``.  A raw unquoted ``n`` is not an integer or string value, so this
    # equivalence is deliberately narrow and does not hide other type drift.
    if value == "<absent>":
        return "n"
    return value


def require_semantic_delta(actual, expected, label):
    require_exact(
        [row["symbol"] for row in actual],
        [row["symbol"] for row in expected],
        label + " symbols",
    )
    for actual_row, expected_row in zip(actual, expected):
        for field in ("before", "after"):
            require_exact(
                semantic_config_value(actual_row[field]),
                semantic_config_value(expected_row[field]),
                "{} {} {}".format(label, actual_row["symbol"], field),
            )


def asserted_config_value(values, symbol, expected, label):
    raw = values.get(symbol, "<absent>")
    actual = semantic_config_value(raw) if expected == "n" else raw
    if actual != expected:
        raise ConfigResolutionError(
            "{} {} differs: {!r} != {!r}".format(
                label, symbol, raw, expected
            )
        )
    return actual


def rpm_file_owner(path):
    command = [
        "rpm",
        "-qf",
        "--qf",
        "%{NAME}-%{EPOCHNUM}:%{VERSION}-%{RELEASE}.%{ARCH}\\n",
        str(path),
    ]
    owner_stdout, owner_stderr = run_command(command, env=CAPTURE_ENVIRONMENT)
    if owner_stderr:
        raise ConfigResolutionError("tool owner query wrote stderr")
    owner_rows = owner_stdout.decode("utf-8").splitlines()
    if len(owner_rows) != 1:
        raise ConfigResolutionError("tool owner query is ambiguous")
    return owner_rows[0], command


def validate_probe_binary_path(probe_id, binary, tool_environment):
    if probe_id == "llvm":
        require_exact(
            binary,
            tool_environment["llvm_config_owner_policy"]["binary_path"],
            "llvm-config binary path",
        )


def probe_environment(contract):
    results = {}
    tool_environment = contract["tool_environment"]
    for probe_id in sorted(PROBE_COMMANDS):
        command = PROBE_COMMANDS[probe_id]
        binary = shutil.which(command[0], path=CAPTURE_ENVIRONMENT["PATH"])
        if binary is None:
            raise ConfigResolutionError("probe binary is missing: {}".format(command[0]))
        validate_probe_binary_path(probe_id, binary, tool_environment)
        completed = run_command(command, env=CAPTURE_ENVIRONMENT)
        owner, owner_command = rpm_file_owner(Path(binary))
        require_exact(
            owner,
            tool_environment["expected_binary_owners"][probe_id],
            "{} binary owner".format(probe_id),
        )
        results[probe_id] = {
            "binary_path": binary,
            "binary_sha256": sha256_file(Path(binary))[1],
            "command": command,
            "owner_command": owner_command,
            "package_nevra": owner,
            "stderr_sha256": hashlib.sha256(completed[1]).hexdigest(),
            "stdout_sha256": hashlib.sha256(completed[0]).hexdigest(),
            "text": (completed[0] + completed[1]).decode("utf-8", errors="strict"),
        }
    rust_sysroot_command = RUST_SRC_PROBE_COMMAND
    sysroot_stdout, sysroot_stderr = run_command(
        rust_sysroot_command, env=CAPTURE_ENVIRONMENT
    )
    if sysroot_stderr:
        raise ConfigResolutionError("rustc sysroot probe wrote stderr")
    sysroot_rows = sysroot_stdout.decode("utf-8").splitlines()
    if len(sysroot_rows) != 1:
        raise ConfigResolutionError("rustc sysroot probe is ambiguous")
    sysroot = Path(sysroot_rows[0])
    if not sysroot.is_absolute() or not sysroot.is_dir() or sysroot.resolve() != sysroot:
        raise ConfigResolutionError("rustc sysroot is not a canonical directory")
    rust_src_core = regular_file(
        sysroot / "lib/rustlib/src/rust/library/core/src/lib.rs",
        "rust-src core",
    )
    if os.path.commonpath((str(sysroot), str(rust_src_core))) != str(sysroot):
        raise ConfigResolutionError("rust-src core escapes the rustc sysroot")
    rust_src_owner, rust_src_owner_command = rpm_file_owner(rust_src_core)
    require_exact(
        rust_src_owner,
        tool_environment["expected_file_owners"]["rust_src_core"],
        "rust-src core owner",
    )
    results["rust_src_core"] = {
        "command": rust_sysroot_command,
        "file_path": str(rust_src_core),
        "file_sha256": sha256_file(rust_src_core)[1],
        "owner_command": rust_src_owner_command,
        "package_nevra": rust_src_owner,
        "stderr_sha256": hashlib.sha256(sysroot_stderr).hexdigest(),
        "stdout_sha256": hashlib.sha256(sysroot_stdout).hexdigest(),
    }
    rust = results["rustc"]["text"]
    rust_match = re.search(r"(?m)^rustc 1\.92\.0(?:\s|$)", rust)
    llvm_match = re.search(r"(?m)^LLVM version:\s*([0-9]+)\.([0-9]+)\.([0-9]+)", rust)
    if rust_match is None or llvm_match is None:
        raise ConfigResolutionError("rustc probe does not prove Rust 1.92.0 and LLVM")
    version_patterns = {
        "bindgen": r"(?m)^bindgen 0\.72\.1(?:\s|$)",
        "clang": r"(?m)clang version 21\.1\.8(?:\s|$)",
        "lld": r"(?m)^LLD 21\.1\.8(?:\s|$)",
        "llvm": r"(?m)^21\.1\.8$",
        "pahole": r"(?m)^v?1\.31$",
        "rustc": r"(?m)^rustc 1\.92\.0(?:\s|$)",
    }
    for probe_id, pattern in sorted(version_patterns.items()):
        if re.search(pattern, results[probe_id]["text"]) is None:
            raise ConfigResolutionError(
                "{} probe does not prove exact version {}".format(
                    probe_id,
                    tool_environment["expected_versions"][probe_id],
                )
            )
    require_exact(
        "{}.{}.{}".format(*llvm_match.groups()),
        tool_environment["expected_rustc_llvm_version"],
        "rustc LLVM version",
    )
    results["derived"] = {
        "bindgen_version_text": first_line(results["bindgen"]["text"]),
        "pahole_version": numeric_version(results["pahole"]["text"], 100),
        "rustc_llvm_version": canonical_version(llvm_match.groups(), 10000),
        "rustc_version": 109200,
        "rustc_version_text": first_line(results["rustc"]["text"]),
    }
    return results


def first_line(text):
    rows = [row.strip() for row in text.splitlines() if row.strip()]
    if not rows:
        raise ConfigResolutionError("tool probe output is empty")
    return rows[0]


def canonical_version(groups, multiplier):
    major, minor, patch = (int(item) for item in groups)
    if multiplier == 10000:
        return major * 10000 + minor * 100 + patch
    return major * 100000 + minor * 100 + patch


def numeric_version(text, multiplier):
    match = re.search(r"(?:v)?([0-9]+)\.([0-9]+)(?:\.([0-9]+))?", text)
    if match is None:
        raise ConfigResolutionError("tool version is not parseable")
    patch = match.group(3) or "0"
    if multiplier == 100:
        return int(match.group(1)) * 100 + int(match.group(2))
    return canonical_version((match.group(1), match.group(2), patch), multiplier)


def expected_generated_values(probes):
    derived = probes["derived"]
    pahole = derived["pahole_version"]
    rustc = derived["rustc_version"]
    return {
        "CONFIG_BINDGEN_VERSION_TEXT": '"{}"'.format(
            derived["bindgen_version_text"]
        ),
        "CONFIG_PAHOLE_HAS_BTF_TAG": "y" if pahole >= 123 else "n",
        "CONFIG_PAHOLE_HAS_LANG_EXCLUDE": "y" if pahole >= 124 else "n",
        "CONFIG_PAHOLE_HAS_SPLIT_BTF": "y" if pahole >= 119 else "n",
        "CONFIG_PAHOLE_VERSION": str(pahole),
        "CONFIG_RUSTC_HAS_UNNECESSARY_TRANSMUTES": (
            "y" if rustc >= 108800 else "n"
        ),
        "CONFIG_RUSTC_LLVM_VERSION": str(derived["rustc_llvm_version"]),
        "CONFIG_RUSTC_VERSION": str(rustc),
        "CONFIG_RUSTC_VERSION_TEXT": '"{}"'.format(
            derived["rustc_version_text"]
        ),
        "CONFIG_RUST_IS_AVAILABLE": "y",
    }


def validate_config_pair(contract, baseline_path, control_paths, resolved_paths, probes):
    baseline = parse_config(baseline_path)
    controls = [parse_config(path) for path in control_paths]
    resolved = [parse_config(path) for path in resolved_paths]
    if regular_file(control_paths[0], "control pass 1").read_bytes() != regular_file(
        control_paths[1], "control pass 2"
    ).read_bytes():
        raise ConfigResolutionError("independent control resolutions differ byte-for-byte")
    if regular_file(resolved_paths[0], "resolved pass 1").read_bytes() != regular_file(
        resolved_paths[1], "resolved pass 2"
    ).read_bytes():
        raise ConfigResolutionError("independent requested resolutions differ byte-for-byte")
    require_exact(controls[0], controls[1], "control symbol maps")
    require_exact(resolved[0], resolved[1], "resolved symbol maps")

    preserved = {}
    for group, values in sorted(contract["preservation_groups"].items()):
        preserved[group] = {}
        for symbol, expected in sorted(values.items()):
            stage_values = {}
            for stage, values_map in (
                ("baseline", baseline),
                ("control", controls[0]),
                ("resolved", resolved[0]),
            ):
                stage_values[stage] = asserted_config_value(
                    values_map, symbol, expected, stage + " preserved"
                )
            if len(set(stage_values.values())) != 1:
                raise ConfigResolutionError(
                    "preserved {} drifted across resolution stages".format(symbol)
                )
            preserved[group][symbol] = stage_values["resolved"]

    environment_delta = changed_symbols(baseline, controls[0])
    requested_delta = changed_symbols(controls[0], resolved[0])
    semantic_requested_delta = [
        row
        for row in requested_delta
        if semantic_config_value(row["before"])
        != semantic_config_value(row["after"])
    ]
    representation_changes = [
        row
        for row in requested_delta
        if semantic_config_value(row["before"])
        == semantic_config_value(row["after"])
    ]
    expected_requested = [
        {"before": row["baseline"], "after": row["resolved"], "symbol": row["symbol"]}
        for row in contract["requested_delta"]
    ]
    expected_requested.sort(key=lambda item: item["symbol"])
    expected_derived = [
        {"before": row["baseline"], "after": row["resolved"], "symbol": row["symbol"]}
        for row in contract["derived_delta"]
    ]
    expected_derived.sort(key=lambda item: item["symbol"])
    requested_symbols = {row["symbol"] for row in expected_requested}
    derived_symbols = {row["symbol"] for row in expected_derived}
    if requested_symbols & derived_symbols:
        raise ConfigResolutionError("requested and derived delta symbols overlap")
    requested_changes = [
        row
        for row in semantic_requested_delta
        if row["symbol"] in requested_symbols
    ]
    derived_changes = [
        row
        for row in semantic_requested_delta
        if row["symbol"] in derived_symbols
    ]
    require_semantic_delta(
        requested_changes, expected_requested, "requested semantic delta"
    )
    require_semantic_delta(
        derived_changes, expected_derived, "derived semantic delta"
    )

    generated_contract = contract["generated_environment"]
    generated_allowed = set(generated_contract["policy_symbols"])
    requested_generated = [
        row
        for row in semantic_requested_delta
        if row["symbol"] not in requested_symbols | derived_symbols
        and row["symbol"] in generated_allowed
    ]
    classified = sorted(
        requested_changes
        + derived_changes
        + requested_generated
        + representation_changes,
        key=lambda item: item["symbol"],
    )
    if classified != requested_delta:
        classified_symbols = {row["symbol"] for row in classified}
        unclassified = sorted(
            row["symbol"]
            for row in requested_delta
            if row["symbol"] not in classified_symbols
        )
        raise ConfigResolutionError(
            "control-to-resolved delta has unclassified symbols: {}".format(
                ", ".join(unclassified)
            )
        )
    expected_generated = expected_generated_values(probes)
    generated_results = {}
    for symbol in sorted(generated_allowed):
        expected = expected_generated[symbol]
        actual = asserted_config_value(
            resolved[0], symbol, expected, "generated tool probe"
        )
        generated_results[symbol] = actual

    assertions = {}
    for symbol, expected in sorted(contract["dependency_symbols"].items()):
        actual = asserted_config_value(
            resolved[0], symbol, expected, "dependency"
        )
        assertions[symbol] = actual
    for symbol, rule in sorted(contract["conditional_dependencies"].items()):
        raw = resolved[0].get(symbol, "<absent>")
        actual = semantic_config_value(raw)
        if actual not in rule["allowed_values"]:
            raise ConfigResolutionError(
                "conditional dependency {} has invalid value {!r}".format(
                    symbol, raw
                )
            )
        if actual == "y" and probes["derived"]["rustc_version"] < rule[
            "rustc_minimum_if_y"
        ]:
            raise ConfigResolutionError(
                "conditional dependency {} requires newer rustc".format(symbol)
            )
        assertions[symbol] = actual
    return {
        "classification": {
            "baseline_to_control": environment_delta,
            "control_to_resolved": requested_delta,
            "stages": contract["resolution_classification"]["stages"],
        },
        "derived_changes": derived_changes,
        "environment_generated_changes": environment_delta,
        "generated_symbol_results": generated_results,
        "representation_changes": representation_changes,
        "requested_changes": requested_changes,
        "requested_generated_symbols": requested_generated,
        "unexpected_generated_symbols": [],
    }, {"dependencies": assertions, "preservation_groups": preserved}


def run_command(arguments, cwd=None, env=None, timeout=600):
    if not arguments or not all(isinstance(item, str) and item for item in arguments):
        raise ConfigResolutionError("command arguments are invalid")
    try:
        completed = subprocess.run(
            list(arguments),
            cwd=str(cwd) if cwd is not None else None,
            env=dict(env) if env is not None else None,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ConfigResolutionError("command failed to execute: {}".format(exc))
    if completed.returncode != 0:
        raise ConfigResolutionError(
            "command failed ({}): {}".format(
                completed.returncode,
                completed.stderr.decode("utf-8", errors="replace")[-2000:],
            )
        )
    return completed.stdout, completed.stderr


def run_rustavailable(command, contract):
    stdout, stderr = run_command(
        command,
        env=CAPTURE_ENVIRONMENT,
        timeout=1800,
    )
    if stderr:
        raise ConfigResolutionError("rustavailable wrote stderr")
    success_line = contract["resolution"]["rustavailable"]["required_stdout_line"]
    stdout_lines = stdout.decode("utf-8", errors="strict").splitlines()
    success_line_count = stdout_lines.count(success_line)
    if success_line_count != 1:
        raise ConfigResolutionError(
            "rustavailable did not emit its unique success line"
        )
    return {
        "command": command,
        "exit_code": 0,
        "stderr_sha256": hashlib.sha256(stderr).hexdigest(),
        "stdout_sha256": hashlib.sha256(stdout).hexdigest(),
        "success_line_count": success_line_count,
    }


def verify_asset(path, record, label):
    path = regular_file(path, label)
    size, digest = sha256_file(path)
    require_exact(size, record["size"], label + " size")
    require_exact(digest, record["sha256"], label + " digest")
    return path


def normalized_tar_member_path(name, root):
    if not isinstance(name, str):
        raise ConfigResolutionError("source archive member name is not text")
    normalized_name = name.rstrip("/")
    parts = normalized_name.split("/")
    if (
        not normalized_name
        or normalized_name.startswith("/")
        or "\\" in normalized_name
        or "\x00" in normalized_name
        or any(part in ("", ".", "..") for part in parts)
        or parts[0] != root
    ):
        raise ConfigResolutionError("source archive member is unsafe: {}".format(name))
    return PurePosixPath(*parts)


def normalized_tar_link_target(member, member_path, root):
    linkname = member.linkname
    if (
        not isinstance(linkname, str)
        or not linkname
        or linkname.startswith("/")
        or "\\" in linkname
        or "\x00" in linkname
        or any(part == "" for part in linkname.split("/"))
    ):
        raise ConfigResolutionError(
            "source archive link target is unsafe: {} -> {}".format(
                member.name, linkname
            )
        )

    # POSIX symlinks are relative to their containing directory. Tar hard-link
    # names are archive member names and are therefore relative to the archive
    # root. Resolve both forms lexically; no filesystem lookup is authoritative.
    if member.issym():
        parts = list(member_path.parent.parts)
    else:
        parts = []
    for part in linkname.split("/"):
        if part == ".":
            continue
        if part == "..":
            if len(parts) <= 1:
                raise ConfigResolutionError(
                    "source archive link target escapes its root: {} -> {}".format(
                        member.name, linkname
                    )
                )
            parts.pop()
            continue
        parts.append(part)
    if not parts or parts[0] != root:
        raise ConfigResolutionError(
            "source archive link target escapes its root: {} -> {}".format(
                member.name, linkname
            )
        )
    return PurePosixPath(*parts)


def safe_tar_member(member, root):
    path = normalized_tar_member_path(member.name, root)
    target = None
    if member.type in (tarfile.REGTYPE, tarfile.AREGTYPE):
        kind = "file"
        if not isinstance(member.size, int) or member.size < 0:
            raise ConfigResolutionError(
                "source archive member has an invalid size: {}".format(member.name)
            )
    elif member.type == tarfile.DIRTYPE:
        kind = "directory"
    elif member.type == tarfile.SYMTYPE:
        kind = "symlink"
        target = normalized_tar_link_target(member, path, root)
    elif member.type == tarfile.LNKTYPE:
        kind = "hardlink"
        target = normalized_tar_link_target(member, path, root)
    else:
        raise ConfigResolutionError(
            "source archive member is unsafe: {}".format(member.name)
        )
    return {"kind": kind, "member": member, "path": path, "target": target}


def validated_tar_members(members, root):
    if (
        not isinstance(root, str)
        or not root
        or "/" in root
        or "\\" in root
        or "\x00" in root
        or root in (".", "..")
    ):
        raise ConfigResolutionError("source archive root name is unsafe")
    records = []
    by_name = {}
    for member in members:
        record = safe_tar_member(member, root)
        name = record["path"].as_posix()
        if name in by_name:
            raise ConfigResolutionError(
                "source archive contains a duplicate member: {}".format(name)
            )
        by_name[name] = record
        records.append(record)

    root_record = by_name.get(root)
    if root_record is None or root_record["kind"] != "directory":
        raise ConfigResolutionError("source archive needs one explicit root directory")

    known_directories = {root}
    for record in records:
        path = record["path"]
        for parent in path.parents:
            parent_name = parent.as_posix()
            if parent_name == ".":
                break
            known_directories.add(parent_name)
        for parent in path.parents:
            parent_name = parent.as_posix()
            if parent_name == ".":
                break
            prior = by_name.get(parent_name)
            if prior is not None and prior["kind"] != "directory":
                raise ConfigResolutionError(
                    "source archive member descends through a non-directory: {}".format(
                        record["member"].name
                    )
                )

    for record in records:
        target = record["target"]
        if target is None:
            continue
        target_name = target.as_posix()
        target_record = by_name.get(target_name)
        if target_record is None and target_name not in known_directories:
            raise ConfigResolutionError(
                "source archive link target is not a member: {} -> {}".format(
                    record["member"].name, record["member"].linkname
                )
            )
        if record["kind"] == "hardlink" and (
            target_record is None or target_record["kind"] != "file"
        ):
            raise ConfigResolutionError(
                "source archive hard-link target is not a regular file: {} -> {}".format(
                    record["member"].name, record["member"].linkname
                )
            )
    return records


def tar_output_path(target, archive_path):
    return target.joinpath(*archive_path.parts)


def extract_validated_tar(stream, records, target):
    directory_paths = set()
    explicit_directories = []
    for record in records:
        for parent in record["path"].parents:
            if parent.as_posix() == ".":
                break
            directory_paths.add(parent)
        if record["kind"] == "directory":
            directory_paths.add(record["path"])
            explicit_directories.append(record)

    for path in sorted(
        directory_paths, key=lambda item: (len(item.parts), item.as_posix())
    ):
        destination = tar_output_path(target, path)
        destination.mkdir(mode=0o700)

    for record in records:
        if record["kind"] != "file":
            continue
        member = record["member"]
        destination = tar_output_path(target, record["path"])
        source = stream.extractfile(member)
        if source is None:
            raise ConfigResolutionError(
                "source archive regular member has no data: {}".format(member.name)
            )
        copied = 0
        with source:
            with destination.open("xb") as output:
                while True:
                    chunk = source.read(1024 * 1024)
                    if not chunk:
                        break
                    copied += len(chunk)
                    if copied > member.size:
                        raise ConfigResolutionError(
                            "source archive member exceeds its declared size: {}".format(
                                member.name
                            )
                        )
                    output.write(chunk)
        if copied != member.size:
            raise ConfigResolutionError(
                "source archive member differs from its declared size: {}".format(
                    member.name
                )
            )
        os.chmod(str(destination), member.mode & 0o777)
        os.utime(str(destination), (member.mtime, member.mtime))

    for record in records:
        member = record["member"]
        destination = tar_output_path(target, record["path"])
        if record["kind"] == "symlink":
            destination.symlink_to(member.linkname)
        elif record["kind"] == "hardlink":
            source = tar_output_path(target, record["target"])
            if source.is_symlink() or not source.is_file():
                raise ConfigResolutionError(
                    "source archive hard-link target was not safely extracted: {}".format(
                        member.name
                    )
                )
            os.link(str(source), str(destination))

    for record in sorted(
        explicit_directories,
        key=lambda item: (-len(item["path"].parts), item["path"].as_posix()),
    ):
        member = record["member"]
        destination = tar_output_path(target, record["path"])
        os.chmod(str(destination), member.mode & 0o777)
        os.utime(str(destination), (member.mtime, member.mtime))


def extract_source(archive, target, root_name):
    target = Path(target)
    if target.is_symlink() or not target.is_dir():
        raise ConfigResolutionError("source extraction target is not a regular directory")
    try:
        next(target.iterdir())
    except StopIteration:
        pass
    else:
        raise ConfigResolutionError("source extraction target is not empty")
    try:
        stream = tarfile.open(str(archive), "r:xz")
    except (OSError, tarfile.TarError) as exc:
        raise ConfigResolutionError("cannot open source archive: {}".format(exc))
    with stream:
        members = stream.getmembers()
        if not members:
            raise ConfigResolutionError("source archive is empty")
        records = validated_tar_members(members, root_name)
        extract_validated_tar(stream, records, target)
    source = target / root_name
    if source.is_symlink() or not (source / "Makefile").is_file():
        raise ConfigResolutionError("source archive root is invalid")
    return source


def apply_patch(source, path, fuzz_zero):
    command = [
        "patch",
        "-d",
        str(source),
        "-p1",
        "--batch",
        "--forward",
    ]
    if fuzz_zero:
        command.append("--fuzz=0")
    command.extend(["--no-backup-if-mismatch", "-i", str(path)])
    run_command(command, timeout=300)


def run_resolution(source, baseline, fragment, pass_number, contract):
    process_source = source / contract["process_configs"]["path"]
    verify_asset(
        process_source,
        {
            "sha256": contract["process_configs"]["sha256"],
            "size": contract["source_assets"]["process_configs"]["size"],
        },
        "source process_configs",
    )
    configs = source / "redhat/configs"
    control_name = "kernel-rk005-control-pass-{}".format(pass_number)
    requested_name = "kernel-rk005-requested-pass-{}".format(pass_number)
    control_input = configs / "{}-6.12.0-x86_64-rhel.config".format(
        control_name
    )
    requested_input = configs / "{}-6.12.0-x86_64-rhel.config".format(
        requested_name
    )
    shutil.copyfile(str(baseline), str(control_input))
    control_environment = dict(CAPTURE_ENVIRONMENT)
    control_environment.update(
        {
            "FLAVOR": "rhel",
            "RHJOBS": "1",
            "SPECPACKAGE_NAME": control_name,
        }
    )
    control_process_command = [
        str(process_source),
        "-m",
        "LLVM=1",
        "6.12.0",
        "rhel",
    ]
    run_command(
        control_process_command,
        cwd=configs,
        env=control_environment,
        timeout=1800,
    )
    control_output = configs / control_input.name
    if not control_output.is_file():
        raise ConfigResolutionError("process_configs did not emit the control config")

    merge_dir = source.parent / "fragment-merge"
    merge_dir.mkdir(mode=0o700)
    shutil.copyfile(str(baseline), str(merge_dir / ".config"))
    merge = source / "scripts/kconfig/merge_config.sh"
    merge_command = [
        str(merge),
        "-m",
        "-O",
        str(merge_dir),
        str(merge_dir / ".config"),
        str(fragment),
    ]
    run_command(
        merge_command,
        cwd=source,
        env=CAPTURE_ENVIRONMENT,
        timeout=300,
    )
    shutil.copyfile(str(merge_dir / ".config"), str(requested_input))
    requested_environment = dict(CAPTURE_ENVIRONMENT)
    requested_environment.update(
        {
            "FLAVOR": "rhel",
            "RHJOBS": "1",
            "SPECPACKAGE_NAME": requested_name,
        }
    )
    requested_process_command = [
        str(process_source),
        "-m",
        "LLVM=1",
        "6.12.0",
        "rhel",
    ]
    run_command(
        requested_process_command,
        cwd=configs,
        env=requested_environment,
        timeout=1800,
    )
    requested_output = configs / requested_input.name
    if not requested_output.is_file():
        raise ConfigResolutionError("process_configs did not emit the requested config")
    control_dir = source.parent / "control-build"
    requested_dir = source.parent / "requested-build"
    control_dir.mkdir(mode=0o700)
    requested_dir.mkdir(mode=0o700)
    shutil.copyfile(str(control_output), str(control_dir / ".config"))
    shutil.copyfile(str(requested_output), str(requested_dir / ".config"))
    source_cleanup = [
        "make",
        "-C",
        str(source),
        "ARCH=x86_64",
        "LLVM=1",
        "mrproper",
    ]
    run_command(source_cleanup, env=CAPTURE_ENVIRONMENT, timeout=1800)
    make_control = [
        "make",
        "-C",
        str(source),
        "O=" + str(control_dir),
        "ARCH=x86_64",
        "LLVM=1",
        "olddefconfig",
    ]
    make_requested = [
        "make",
        "-C",
        str(source),
        "O=" + str(requested_dir),
        "ARCH=x86_64",
        "LLVM=1",
        "olddefconfig",
    ]
    run_command(make_control, env=CAPTURE_ENVIRONMENT, timeout=1800)
    run_command(make_requested, env=CAPTURE_ENVIRONMENT, timeout=1800)
    rustavailable_command = [
        "make",
        "-C",
        str(source),
        "O=" + str(requested_dir),
        "ARCH=x86_64",
        "LLVM=1",
        "rustavailable",
    ]
    rustavailable = run_rustavailable(rustavailable_command, contract)
    return {
        "control": control_dir / ".config",
        "control_process_environment": control_environment,
        "control_process_command": control_process_command,
        "merge_command": merge_command,
        "requested": requested_dir / ".config",
        "requested_process_environment": requested_environment,
        "requested_process_command": requested_process_command,
        "requested_command": make_requested,
        "control_command": make_control,
        "rustavailable": rustavailable,
        "source_cleanup_command": source_cleanup,
    }


def prepare_output(path):
    if not path.is_absolute():
        raise ConfigResolutionError("output directory must be absolute")
    parent = path.parent
    if parent.is_symlink() or not parent.is_dir() or parent.resolve() != parent:
        raise ConfigResolutionError("output parent is unsafe")
    if path.exists() or path.is_symlink():
        raise ConfigResolutionError("output directory already exists")
    path.mkdir(mode=0o700)
    return path


def write_output(root, name, data):
    relative = PurePosixPath(name)
    if relative.is_absolute() or len(relative.parts) != 1:
        raise ConfigResolutionError("output path is unsafe")
    target = root / name
    if target.exists() or target.is_symlink():
        raise ConfigResolutionError("output already exists: {}".format(name))
    mode = "xb"
    with target.open(mode) as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    target.chmod(0o400)


def write_json(root, name, value):
    write_output(root, name, canonical_json_bytes(value))


def write_sha256sums(root):
    rows = []
    for name in EVIDENCE_NAMES:
        path = root / name
        size, digest = sha256_file(path)
        if size < 1:
            raise ConfigResolutionError("evidence output is empty: {}".format(name))
        rows.append("{}  {}".format(digest, name))
    write_output(root, "SHA256SUMS", ("\n".join(rows) + "\n").encode("ascii"))


def build_command_manifest(runs, contract):
    if not isinstance(runs, list) or len(runs) != 2:
        raise ConfigResolutionError("commands manifest requires exactly two runs")
    return {
        "patches": [
            {"path": row["path"], "sha256": row["sha256"]}
            for row in contract["patch_authority"]["rust_compatibility"]
        ],
        "passes": [
            {
                "control_olddefconfig": run["control_command"],
                "control_process_configs": run["control_process_command"],
                "control_process_environment": run[
                    "control_process_environment"
                ],
                "fragment_merge": run["merge_command"],
                "requested_process_configs": run["requested_process_command"],
                "requested_process_environment": run[
                    "requested_process_environment"
                ],
                "requested_olddefconfig": run["requested_command"],
                "requested_rustavailable": run["rustavailable"],
                "source_cleanup": run["source_cleanup_command"],
            }
            for run in runs
        ],
        "schema_version": SCHEMA_VERSION,
    }


def capture(repo, source_assets, output_dir, identity, contract):
    assets = contract["source_assets"]
    archive = verify_asset(
        source_assets / Path(assets["linux_archive"]["path"]).name,
        assets["linux_archive"],
        "Linux archive",
    )
    baseline = verify_asset(
        source_assets / Path(assets["baseline"]["path"]).name,
        assets["baseline"],
        "Rocky baseline config",
    )
    process_asset = verify_asset(
        source_assets / Path(assets["process_configs"]["path"]).name,
        assets["process_configs"],
        "SRPM process_configs",
    )
    debrand = verify_asset(
        source_assets / Path(assets["debrand_patch"]["path"]).name,
        assets["debrand_patch"],
        "Rocky debrand patch",
    )
    fragment = safe_repo_file(repo, CONFIG_FRAGMENT_PATH.as_posix(), "config fragment")
    output = prepare_output(output_dir)
    probes = probe_environment(contract)
    runs = []
    with tempfile.TemporaryDirectory(prefix="rk005-config-") as temporary_name:
        temporary = Path(temporary_name)
        for number in (1, 2):
            run_root = temporary / "pass-{}".format(number)
            run_root.mkdir(mode=0o700)
            source = extract_source(
                archive, run_root, assets["linux_archive"]["root"]
            )
            source_process = source / contract["process_configs"]["path"]
            require_exact(
                source_process.read_bytes(),
                process_asset.read_bytes(),
                "archive/SRPM process_configs bytes",
            )
            apply_patch(source, debrand, False)
            for patch in contract["patch_authority"]["rust_compatibility"]:
                apply_patch(
                    source,
                    safe_repo_file(repo, patch["path"], "compatibility patch"),
                    True,
                )
            runs.append(run_resolution(source, baseline, fragment, number, contract))

        delta, assertions = validate_config_pair(
            contract,
            baseline,
            [runs[0]["control"], runs[1]["control"]],
            [runs[0]["requested"], runs[1]["requested"]],
            probes,
        )
        write_output(output, "baseline.config", baseline.read_bytes())
        write_output(output, "fragment.config", fragment.read_bytes())
        write_output(output, "control-pass-1.config", runs[0]["control"].read_bytes())
        write_output(output, "control-pass-2.config", runs[1]["control"].read_bytes())
        write_output(output, "resolved-pass-1.config", runs[0]["requested"].read_bytes())
        write_output(output, "resolved-pass-2.config", runs[1]["requested"].read_bytes())
        command_manifest = build_command_manifest(runs, contract)
        environment = {
            "container_image": CONTAINER_IMAGE,
            "fixed_environment": CAPTURE_ENVIRONMENT,
            "github": identity,
            "probes": probes,
            "schema_version": SCHEMA_VERSION,
        }
        blockers = {
            "gate_claims": contract["gate_claims"],
            "success_blockers": contract["success_blockers"],
        }
        write_json(output, "commands.json", command_manifest)
        write_json(output, "environment.json", environment)
        write_json(output, "config-delta.json", delta)
        write_json(output, "dependency-assertions.json", assertions)
        write_json(output, "blockers.json", blockers)
        manifests = []
        for name in EVIDENCE_NAMES[:-1]:
            path = output / name
            manifests.append(
                {"path": name, "sha256": sha256_file(path)[1], "size": path.stat().st_size}
            )
        checkpoint = {
            "credit_eligible": False,
            "gate_claims": contract["gate_claims"],
            "github": identity,
            "manifests": manifests,
            "phase": PHASE_ID,
            "schema_version": SCHEMA_VERSION,
            "two_independent_resolutions_identical": True,
        }
        write_json(output, "checkpoint.json", checkpoint)
    write_sha256sums(output)


def parse_args(argv):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[1])
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--check", action="store_true")
    modes.add_argument("--capture", action="store_true")
    parser.add_argument("--phase", choices=[PHASE_ID])
    parser.add_argument("--source-assets", type=Path)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--github-head-sha")
    parser.add_argument("--github-run-id")
    parser.add_argument("--github-run-attempt")
    parser.add_argument("--github-repository")
    parser.add_argument("--container-image")
    return parser.parse_args(argv)


def main(argv):
    args = parse_args(argv)
    repo = args.repo.resolve()
    try:
        contract = validate_contract(repo)
        validate_workflow(repo)
        run_only = (
            args.phase,
            args.source_assets,
            args.output_dir,
            args.github_head_sha,
            args.github_run_id,
            args.github_run_attempt,
            args.github_repository,
            args.container_image,
        )
        if args.check:
            if any(item is not None for item in run_only):
                raise ConfigResolutionError("--check rejects capture-only arguments")
            print("RK-005 config-resolution contract verified; gate credit remains forbidden")
            return 0
        required = {
            "--phase": args.phase,
            "--source-assets": args.source_assets,
            "--output-dir": args.output_dir,
            "--github-head-sha": args.github_head_sha,
            "--github-run-id": args.github_run_id,
            "--github-run-attempt": args.github_run_attempt,
            "--github-repository": args.github_repository,
            "--container-image": args.container_image,
        }
        missing = [key for key, value in required.items() if value is None]
        if missing:
            raise ConfigResolutionError(
                "capture requires {}".format(", ".join(missing))
            )
        require_exact(args.phase, PHASE_ID, "capture phase")
        identity = validate_identity(
            args.github_head_sha,
            args.github_run_id,
            args.github_run_attempt,
            args.github_repository,
            args.container_image,
        )
        capture(
            repo,
            regular_directory(args.source_assets, "source assets"),
            args.output_dir,
            identity,
            contract,
        )
        print("captured deterministic config evidence; RK-005 credit remains forbidden")
        return 0
    except (ConfigResolutionError, OSError, UnicodeError, ValueError) as exc:
        print("Rocky config-resolution error: {}".format(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
