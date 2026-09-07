#!/usr/bin/env python3
"""Validate the fail-closed RK-003 toolchain and RK-005 v2 config lock.

``--check`` validates the immutable platform facts and reports missing primary
evidence.  ``--gate-ready`` is the only gate-credit mode and returns nonzero
until both locks have complete, repository-verifiable evidence.  The checker
never upgrades observed repository metadata into archive or signature proof.
"""

import argparse
import hashlib
import json
import os
import re
import sys
from pathlib import Path, PurePosixPath
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Set, Tuple


TOOLCHAIN_LOCK_PATH = Path("host-kernel/rocky/toolchain-lock.json")
CONFIG_POLICY_V1_PATH = Path("host-kernel/rocky/config-policy.json")
CONFIG_POLICY_PATH = Path("host-kernel/rocky/config-policy-v2.json")
CONFIG_POLICY_V2_PATH = CONFIG_POLICY_PATH
CONFIG_FRAGMENT_PATH = Path("host-kernel/rocky/configs/rust-minimal.config")
SOURCE_LOCK_PATH = Path("host-kernel/rocky/source-lock.json")

MAX_MANIFEST_BYTES = 2 * 1024 * 1024
HEX_SHA256 = re.compile(r"^[0-9a-f]{64}$")
HEX_SHA1 = re.compile(r"^[0-9a-f]{40}$")
KCONFIG_SET = re.compile(r"^(CONFIG_[A-Za-z0-9_]+)=(.*)$")
KCONFIG_UNSET = re.compile(r"^# (CONFIG_[A-Za-z0-9_]+) is not set$")

LOCK_ID_PREFIX = "rocky-10.2-x86_64-kernel-6.12.0-211.44.1.el10_2"
EXPECTED_TARGET = {
    "architecture": "x86_64",
    "distribution": "Rocky Linux",
    "kernel_nvr_base": "kernel-6.12.0-211.44.1.el10_2",
    "release": "10.2",
}
EXPECTED_SOURCE = {
    "dist_git_commit": "e4cad646580f7f3dfec5e3b6b4ea9e89b7572f6c",
    "kernel_source_nevra": "kernel-0:6.12.0-211.44.1.el10_2.src",
    "lock_id": f"{LOCK_ID_PREFIX}-source-v1",
    "path": SOURCE_LOCK_PATH.as_posix(),
    "source_archive_sha256": (
        "4a174d47b8874a2139efcd1ac1ab2d6b80ae7a0ca62f0ae4596fd20cf62a3533"
    ),
    "source_rpm_sha256": (
        "2bfeda65bd9bdd4b86650074c81e061c37822b80317ac0d4f5aacc89c85589cb"
    ),
}
EXPECTED_RELEASE_KEY = {
    "fingerprint": "FC226859C0860BF0DDB95B085B106C736FEDFC85",
    "key_id": "5B106C736FEDFC85",
    "sha256": "be8c4f070b696e64d8ce40e59a95a57e8b5c776f0015c2fd64e14b896622bdb4",
}

# Package checksums came from Rocky 10.2 repository primary metadata.  They are
# immutable observations only; verification flags below must remain false until
# the RPM bytes and rpmkeys evidence are committed and independently checked.
EXPECTED_DIRECT_ARTIFACTS = [
    ("rust", "rustc", "1.92.0", "1.el10", "x86_64", "appstream", "Packages/r/rust-1.92.0-1.el10.x86_64.rpm", 31573199, "ffb092cbb80e6fbffed7ab3a9bfc23c65eb5ee7d22ef80b27f4c9432c9493abb"),
    ("rust-src", "rust-src", "1.92.0", "1.el10", "noarch", "appstream", "Packages/r/rust-src-1.92.0-1.el10.noarch.rpm", 4360888, "c25e7051905b0f77caf324ec6ba9215f9d5fccbeb38bf192e1df05c3eb9683b9"),
    ("rustfmt", "rustfmt", "1.92.0", "1.el10", "x86_64", "appstream", "Packages/r/rustfmt-1.92.0-1.el10.x86_64.rpm", 2073460, "c1de122dfafe9ebafe0bb2b7cc1ee3ffd66b2057ca2441895497b6247361163a"),
    ("clippy", "clippy", "1.92.0", "1.el10", "x86_64", "appstream", "Packages/c/clippy-1.92.0-1.el10.x86_64.rpm", 3785869, "ce0220083c1c429d2a47194c52adb1358a62d650168c3934ed9b23023029ba87"),
    ("cargo", "cargo", "1.92.0", "1.el10", "x86_64", "appstream", "Packages/c/cargo-1.92.0-1.el10.x86_64.rpm", 8421744, "5c462cec175396b46e05bfbd1215dcf13573e1530dc44443ae72b7d5d38df758"),
    ("bindgen-cli", "bindgen", "0.72.1", "1.el10", "x86_64", "crb", "Packages/b/bindgen-cli-0.72.1-1.el10.x86_64.rpm", 2019952, "bda54668cc6c32b272e212777fa00fb57ae0921c5af30ee136e5e3236f37c6d4"),
    ("clang", "clang", "21.1.8", "1.el10", "x86_64", "appstream", "Packages/c/clang-21.1.8-1.el10.x86_64.rpm", 7644624, "c64d0f6daaf7e84c70e147da1fc20eb4b92fc87301d40ce8a7802e8663592138"),
    ("clang-libs", "libclang", "21.1.8", "1.el10", "x86_64", "appstream", "Packages/c/clang-libs-21.1.8-1.el10.x86_64.rpm", 31889783, "7a37c942c580e7eecba79c28a824e61c3cbd317dbec94e649cdce900b03b1953"),
    ("llvm", "llvm", "21.1.8", "1.el10", "x86_64", "appstream", "Packages/l/llvm-21.1.8-1.el10.x86_64.rpm", 25226832, "02d755b89d9863b4837b2f83e0a8244c070b59fde96cf0f1518d210c52bdb12e"),
    ("llvm-libs", "llvm-libs", "21.1.8", "1.el10", "x86_64", "appstream", "Packages/l/llvm-libs-21.1.8-1.el10.x86_64.rpm", 32095351, "a6f0a86b87d8f350defc0aab3e15dec6a17a8fb43eb082eabe535d0ea33a8673"),
    ("lld", "lld", "21.1.8", "1.el10", "x86_64", "appstream", "Packages/l/lld-21.1.8-1.el10.x86_64.rpm", 40091, "f7bf6691d17bbc29513e1a45301ecf001ac663a9af4b55924697f0f76289e907"),
    ("dwarves", "pahole", "1.31", "1.el10", "x86_64", "appstream", "Packages/d/dwarves-1.31-1.el10.x86_64.rpm", 154184, "b3cc43abc989cccce298e5514537eb0abc8c9ebc98799ab7da0590cc7c8bdc27"),
    ("bpftool", "bpftool", "7.7.0", "2.el10", "x86_64", "appstream", "Packages/b/bpftool-7.7.0-2.el10.x86_64.rpm", 335690, "4ffe6aa9dbf1e23cf233b8570c8b41de668be2f3dddf8e806104eb438f53f50c"),
    ("rpm", "rpm", "4.19.1.1", "23.el10", "x86_64", "baseos", "Packages/r/rpm-4.19.1.1-23.el10.x86_64.rpm", 555595, "4006fa906fd9a438a6d3636d2033fa9a106fa024d8076c87e735dc0ccc48fcc6"),
    ("rpm-build", "rpm-build", "4.19.1.1", "23.el10", "x86_64", "appstream", "Packages/r/rpm-build-4.19.1.1-23.el10.x86_64.rpm", 77763, "06b8eee98d6b0190c70eb42ff95315bae6df96dc3748acc38901e31da9bb62b6"),
    ("rpm-sign", "rpm-sign", "4.19.1.1", "23.el10", "x86_64", "baseos", "Packages/r/rpm-sign-4.19.1.1-23.el10.x86_64.rpm", 20597, "aba651ce57ef5448a0662c2907005c21ad317ffc75e487e182c9a1eb234d3379"),
    ("redhat-rpm-config", "rpm-macros", "295", "1.el10.rocky.0.2", "noarch", "appstream", "Packages/r/redhat-rpm-config-295-1.el10.rocky.0.2.noarch.rpm", 79335, "9d43b695c70ed2c5a9d7918cd2b827a63f045f76245d6932e98d08e97ae0bdee"),
    ("kernel-rpm-macros", "kernel-rpm-macros", "205", "27.el10", "noarch", "appstream", "Packages/k/kernel-rpm-macros-205-27.el10.noarch.rpm", 22956, "2c6cc046a2bfa48e7410277d112bcedc1b96fe1f3fd254b840f4dd3f2b4e26fa"),
    ("pesign", "pesign", "116", "6.el10", "x86_64", "appstream", "Packages/p/pesign-116-6.el10.x86_64.rpm", 199229, "962e97b904acd93a776770f8e657726b38a2b2dad54909c99fef8e9ec80de8d6"),
    ("kmod", "kmod", "31", "13.el10", "x86_64", "baseos", "Packages/k/kmod-31-13.el10.x86_64.rpm", 139985, "d6c6c04731a0a010fd63b14a82a1625509356b6e12cbfea982fe498b02c3ef1f"),
]

EXPECTED_CONFIG_CHANGES = {
    "CONFIG_RUST": ("n", "y"),
    "CONFIG_MODVERSIONS": ("y", "n"),
}
EXPECTED_PRESERVE = {
    "CONFIG_BPF_SYSCALL": "y",
    "CONFIG_DEBUG_INFO": "y",
    "CONFIG_DEBUG_INFO_BTF": "y",
    "CONFIG_DEBUG_INFO_BTF_MODULES": "y",
    "CONFIG_DEBUG_INFO_DWARF_TOOLCHAIN_DEFAULT": "y",
    "CONFIG_DEBUG_INFO_REDUCED": "n",
    "CONFIG_DEBUG_INFO_SPLIT": "n",
    "CONFIG_MODULES": "y",
    "CONFIG_MODULE_ALLOW_BTF_MISMATCH": "n",
    "CONFIG_MODULE_SIG": "y",
    "CONFIG_MODULE_SIG_ALL": "y",
    "CONFIG_MODULE_SIG_FORCE": "n",
    "CONFIG_MODULE_SIG_KEY": '"certs/signing_key.pem"',
    "CONFIG_MODULE_SIG_KEY_TYPE_RSA": "y",
    "CONFIG_MODULE_SIG_SHA512": "y",
    "CONFIG_CRYPTO_RSA": "y",
    "CONFIG_CRYPTO_SHA512": "y",
    "CONFIG_CFI_CLANG": "n",
    "CONFIG_GCC_PLUGIN_RANDSTRUCT": "n",
    "CONFIG_KASAN": "n",
    "CONFIG_RANDSTRUCT_NONE": "y",
}
EXPECTED_PRESERVE_V2 = dict(EXPECTED_PRESERVE, CONFIG_WERROR="y")
EXPECTED_PRESERVE_RECORDS_V2 = [
    {"symbol": "CONFIG_BPF_SYSCALL", "value": "y"},
    {"symbol": "CONFIG_DEBUG_INFO", "value": "y"},
    {"symbol": "CONFIG_DEBUG_INFO_BTF", "value": "y"},
    {"symbol": "CONFIG_DEBUG_INFO_BTF_MODULES", "value": "y"},
    {"symbol": "CONFIG_DEBUG_INFO_DWARF_TOOLCHAIN_DEFAULT", "value": "y"},
    {"symbol": "CONFIG_DEBUG_INFO_REDUCED", "value": "n"},
    {"symbol": "CONFIG_DEBUG_INFO_SPLIT", "value": "n"},
    {"symbol": "CONFIG_MODULES", "value": "y"},
    {"symbol": "CONFIG_MODULE_ALLOW_BTF_MISMATCH", "value": "n"},
    {"symbol": "CONFIG_MODULE_SIG", "value": "y"},
    {"symbol": "CONFIG_MODULE_SIG_ALL", "value": "y"},
    {"symbol": "CONFIG_MODULE_SIG_FORCE", "value": "n"},
    {"symbol": "CONFIG_MODULE_SIG_KEY", "value": '"certs/signing_key.pem"'},
    {"symbol": "CONFIG_MODULE_SIG_KEY_TYPE_RSA", "value": "y"},
    {"symbol": "CONFIG_MODULE_SIG_SHA512", "value": "y"},
    {"symbol": "CONFIG_CRYPTO_RSA", "value": "y"},
    {"symbol": "CONFIG_CRYPTO_SHA512", "value": "y"},
    {"symbol": "CONFIG_CFI_CLANG", "value": "n"},
    {"symbol": "CONFIG_GCC_PLUGIN_RANDSTRUCT", "value": "n"},
    {"symbol": "CONFIG_KASAN", "value": "n"},
    {"symbol": "CONFIG_RANDSTRUCT_NONE", "value": "y"},
    {"symbol": "CONFIG_WERROR", "value": "y"},
]
EXPECTED_BASELINE_NORMALIZATION_V2 = (
    "Parse CONFIG_NAME=value and '# CONFIG_NAME is not set' as one unique symbol "
    "map; an absent symbol is not equivalent to an explicit n entry."
)
EXPECTED_MODULE_POLICY_V2 = (
    "R1 and R2 must omit symbol CRC entries, must be built against the exact "
    "selected custom kernel and Module.symvers, and kernel plus module RPMs must be "
    "deployed and rolled back atomically by exact NVR."
)
EXPECTED_GATE_POLICY_V2 = (
    "Credit is forbidden until the fragment is resolved by the exact Rocky RPM "
    "configuration pipeline, baseline-to-control-to-resolved changes are completely "
    "classified, dependency and preservation assertions including CONFIG_WERROR=y "
    "pass, an independent closed v2 artifact review recomputes the evidence, and the "
    "production build emits the locked final config."
)
EXPECTED_CONFIG_EVIDENCE_BLOCKERS_V2 = {
    "build_config": (
        "Capture the final .config from the production RPM build, its SHA-256, "
        "kernel NVR/build ID, and proof that it equals the independently resolved "
        "policy config."
    ),
    "dependency_assertions": (
        "Capture exact-source Kconfig values proving HAVE_RUST, RUST_IS_AVAILABLE, "
        "pahole language exclusion, every other CONFIG_RUST dependency, and every "
        "preservation assertion including CONFIG_WERROR=y."
    ),
    "olddefconfig_delta": (
        "Run the exact Rocky process_configs.sh and make LLVM=1 ARCH=x86_64 "
        "olddefconfig pipeline twice. Enumerate baseline-to-control environment "
        "changes; completely partition control-to-resolved changes as requested, "
        "derived, generated, or explicit-n/absent presence changes; validate every "
        "generated Rust/tool symbol against toolchain evidence; and reject "
        "unclassified drift."
    ),
    "resolution_review": (
        "Consume an independently reviewed, durably archived exact-head v2 config "
        "artifact and recompute all six config byte identities, the command and "
        "environment manifests, all 1733 semantic plus 1149 explicit-n/absent "
        "baseline-to-control rows (2882 total), and the complete control-to-resolved "
        "semantic and presence partition before any RK-005 credit."
    ),
}
EXPECTED_DEPENDENCIES = {
    "CONFIG_HAVE_RUST": "y",
    "CONFIG_RUST_IS_AVAILABLE": "y",
    "CONFIG_MODVERSIONS": "n",
    "CONFIG_GCC_PLUGIN_RANDSTRUCT": "n",
    "CONFIG_RANDSTRUCT": "n",
    "CONFIG_PAHOLE_HAS_LANG_EXCLUDE": "y",
    "CONFIG_CFI_CLANG": "n",
    "CONFIG_CALL_PADDING": "runtime-check-rustc-at-least-1.81.0-if-y",
    "CONFIG_KASAN_SW_TAGS": "n",
    "CONFIG_MITIGATION_RETHUNK": "y",
    "CONFIG_KASAN": "n",
}
EXPECTED_DEPENDENCY_REQUIREMENTS_V2 = [
    {
        "expected": "y",
        "source": "arch/x86/Kconfig selects HAVE_RUST if X86_64",
        "symbol": "CONFIG_HAVE_RUST",
    },
    {
        "expected": "y",
        "source": "init/Kconfig: CONFIG_RUST depends on RUST_IS_AVAILABLE",
        "symbol": "CONFIG_RUST_IS_AVAILABLE",
    },
    {
        "expected": "n",
        "source": "init/Kconfig: CONFIG_RUST depends on !MODVERSIONS",
        "symbol": "CONFIG_MODVERSIONS",
    },
    {
        "expected": "n",
        "source": "init/Kconfig: CONFIG_RUST depends on !GCC_PLUGIN_RANDSTRUCT",
        "symbol": "CONFIG_GCC_PLUGIN_RANDSTRUCT",
    },
    {
        "expected": "n",
        "source": "init/Kconfig: CONFIG_RUST depends on !RANDSTRUCT",
        "symbol": "CONFIG_RANDSTRUCT",
    },
    {
        "expected": "y",
        "source": (
            "init/Kconfig: BTF plus CONFIG_RUST requires "
            "PAHOLE_HAS_LANG_EXCLUDE"
        ),
        "symbol": "CONFIG_PAHOLE_HAS_LANG_EXCLUDE",
    },
    {
        "expected": "n",
        "source": (
            "init/Kconfig CFI Rust dependency is avoided by the selected baseline"
        ),
        "symbol": "CONFIG_CFI_CLANG",
    },
    {
        "expected": "runtime-check-rustc-at-least-1.81.0-if-y",
        "source": (
            "init/Kconfig: CONFIG_RUST depends on !CALL_PADDING || "
            "RUSTC_VERSION >= 108100"
        ),
        "symbol": "CONFIG_CALL_PADDING",
    },
    {
        "expected": "n",
        "source": "init/Kconfig: CONFIG_RUST depends on !KASAN_SW_TAGS",
        "symbol": "CONFIG_KASAN_SW_TAGS",
    },
    {
        "expected": "y",
        "source": (
            "init/Kconfig: when MITIGATION_RETHUNK and KASAN are both enabled, "
            "rustc must be at least 1.83.0; this baseline keeps KASAN=n"
        ),
        "symbol": "CONFIG_MITIGATION_RETHUNK",
    },
    {
        "expected": "n",
        "source": (
            "init/Kconfig: when MITIGATION_RETHUNK and KASAN are both enabled, "
            "rustc must be at least 1.83.0; this baseline keeps KASAN=n"
        ),
        "symbol": "CONFIG_KASAN",
    },
]

EXPECTED_GENERATED_CONFIG_SYMBOLS = [
    "CONFIG_BINDGEN_VERSION_TEXT",
    "CONFIG_PAHOLE_HAS_BTF_TAG",
    "CONFIG_PAHOLE_HAS_LANG_EXCLUDE",
    "CONFIG_PAHOLE_HAS_SPLIT_BTF",
    "CONFIG_PAHOLE_VERSION",
    "CONFIG_RUSTC_LLVM_VERSION",
    "CONFIG_RUSTC_VERSION",
    "CONFIG_RUSTC_VERSION_TEXT",
    "CONFIG_RUST_IS_AVAILABLE",
]
EXPECTED_GENERATED_CONFIG_SYMBOLS_V2 = list(EXPECTED_GENERATED_CONFIG_SYMBOLS)
EXPECTED_GENERATED_CONFIG_SYMBOLS_V2.insert(
    EXPECTED_GENERATED_CONFIG_SYMBOLS_V2.index("CONFIG_RUSTC_LLVM_VERSION"),
    "CONFIG_RUSTC_HAS_UNNECESSARY_TRANSMUTES",
)

EXPECTED_GENERATED_SYMBOL_RULES = {
    "CONFIG_RUSTC_HAS_UNNECESSARY_TRANSMUTES": {
        "expected": "y",
        "minimum_rustc_version": 108800,
        "patch": (
            "host-kernel/rocky/patches/"
            "0005-rust-clean-unnecessary-transmutes-lint.patch"
        ),
    }
}

EXPECTED_GENERATED_CONFIG_VALUES_V2 = {
    "CONFIG_BINDGEN_VERSION_TEXT": '"bindgen 0.72.1"',
    "CONFIG_PAHOLE_HAS_BTF_TAG": "y",
    "CONFIG_PAHOLE_HAS_LANG_EXCLUDE": "y",
    "CONFIG_PAHOLE_HAS_SPLIT_BTF": "y",
    "CONFIG_PAHOLE_VERSION": "131",
    "CONFIG_RUSTC_HAS_UNNECESSARY_TRANSMUTES": "y",
    "CONFIG_RUSTC_LLVM_VERSION": "210106",
    "CONFIG_RUSTC_VERSION": "109200",
    "CONFIG_RUSTC_VERSION_TEXT": (
        '"rustc 1.92.0 (ded5c06cf 2025-12-08) '
        '(Red Hat 1.92.0-1.el10)"'
    ),
    "CONFIG_RUST_IS_AVAILABLE": "y",
}

EXPECTED_RESOLUTION_CLASSIFICATION = {
    "baseline_to_control": "environment-generated",
    "complete_partition_required": True,
    "control_to_resolved": ["requested", "derived", "generated", "presence"],
    "stages": ["baseline", "control", "resolved"],
    "unclassified_changes_forbidden": True,
}

EXPECTED_LLVM_CONFIG_OWNER_POLICY = {
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

EXPECTED_MINIMUM_ROWS = [
    {
        "reason": "scripts/min-tool-version.sh rustc",
        "role": "rustc",
        "version": "1.78.0",
    },
    {
        "reason": "scripts/min-tool-version.sh bindgen",
        "role": "bindgen",
        "version": "0.65.1",
    },
    {
        "reason": "scripts/min-tool-version.sh llvm on x86_64",
        "role": "llvm",
        "version": "13.0.1",
    },
    {
        "reason": (
            "CONFIG_RUST with CONFIG_DEBUG_INFO_BTF requires "
            "PAHOLE_HAS_LANG_EXCLUDE"
        ),
        "role": "pahole",
        "version": "1.24",
    },
]

EXPECTED_PROBES = [
    {"artifact": "rust", "command": ["rustc", "--version", "--verbose"], "expected_version": "1.92.0", "id": "rustc", "minimum_version": "1.78.0"},
    {"artifact": "rust-src", "command": ["rpm", "-qf", "$(rustc --print sysroot)/lib/rustlib/src/rust/library/core/src/lib.rs"], "expected_version": "1.92.0", "id": "rust-src-core", "minimum_version": "1.78.0", "required_file": "$(rustc --print sysroot)/lib/rustlib/src/rust/library/core/src/lib.rs", "required_file_sha256": None},
    {"artifact": "cargo", "command": ["cargo", "--version", "--verbose"], "expected_version": "1.92.0", "id": "cargo", "minimum_version": None},
    {"artifact": "rustfmt", "command": ["rustfmt", "--version"], "expected_version": "1.92.0", "id": "rustfmt", "minimum_version": None},
    {"artifact": "clippy", "command": ["clippy-driver", "--version"], "expected_version": "1.92.0", "id": "clippy", "minimum_version": None},
    {"artifact": "bindgen-cli", "command": ["bindgen", "--version", "workaround-for-0.69.0"], "expected_version": "0.72.1", "id": "bindgen", "minimum_version": "0.65.1"},
    {"artifact": "clang-libs", "command": ["bindgen", "scripts/rust_is_available_bindgen_libclang.h"], "expected_version": None, "id": "libclang-via-bindgen", "minimum_version": None, "required_result": "exit-zero while loading the archived clang-libs libclang; version and loaded-library path/hash are captured separately in probe evidence"},
    {"artifact": "clang", "command": ["clang", "--version"], "expected_version": "21.1.8", "id": "clang", "minimum_version": "13.0.1"},
    {"artifact": "llvm", "command": ["llvm-config", "--version"], "expected_version": "21.1.8", "id": "llvm", "minimum_version": "13.0.1"},
    {"artifact": "lld", "command": ["ld.lld", "--version"], "expected_version": "21.1.8", "id": "lld", "minimum_version": "13.0.1"},
    {"artifact": "dwarves", "command": ["pahole", "--version"], "expected_version": "1.31", "id": "pahole", "minimum_version": "1.24"},
    {"artifact": "bpftool", "command": ["bpftool", "version"], "expected_version": "7.7.0", "id": "bpftool", "minimum_version": None},
    {"artifact": "rpm", "command": ["rpm", "--version"], "expected_version": "4.19.1.1", "id": "rpm", "minimum_version": None},
    {"artifact": "rpm-build", "command": ["rpmbuild", "--version"], "expected_version": "4.19.1.1", "id": "rpmbuild", "minimum_version": None},
    {"artifact": "rpm-sign", "command": ["rpmsign", "--version"], "expected_version": "4.19.1.1", "id": "rpmsign", "minimum_version": None},
]


class PlatformLockError(RuntimeError):
    """Raised when an RK-003 or RK-005 lock is malformed or contradictory."""


def reject_duplicate_object_pairs(
    pairs: List[Tuple[str, Any]],
) -> Dict[str, Any]:
    result: Dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise PlatformLockError(f"duplicate JSON key {key!r}")
        result[key] = value
    return result


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> Tuple[int, str]:
    digest = hashlib.sha256()
    size = 0
    try:
        with path.open("rb") as source:
            for chunk in iter(lambda: source.read(1024 * 1024), b""):
                size += len(chunk)
                digest.update(chunk)
    except OSError as exc:
        raise PlatformLockError(f"cannot read {path}: {exc}") from exc
    return size, digest.hexdigest()


def read_json(path: Path) -> Tuple[Dict[str, Any], bytes]:
    try:
        data = path.read_bytes()
    except OSError as exc:
        raise PlatformLockError(f"cannot read {path}: {exc}") from exc
    if len(data) > MAX_MANIFEST_BYTES:
        raise PlatformLockError(f"manifest is implausibly large: {path}")
    try:
        value = json.loads(data, object_pairs_hook=reject_duplicate_object_pairs)
    except (UnicodeDecodeError, json.JSONDecodeError, PlatformLockError) as exc:
        raise PlatformLockError(f"cannot parse {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise PlatformLockError(f"{path} must contain one JSON object")
    return value, data


def exact_keys(value: object, expected: Iterable[str], label: str) -> Mapping[str, Any]:
    if not isinstance(value, dict):
        raise PlatformLockError(f"{label} must be an object")
    actual = set(value)
    wanted = set(expected)
    if actual != wanted:
        raise PlatformLockError(
            f"{label} fields changed: actual={sorted(actual)}, expected={sorted(wanted)}"
        )
    return value


def require_exact(value: object, expected: object, label: str) -> None:
    if value != expected or type(value) is not type(expected):
        raise PlatformLockError(
            f"{label} changed: actual={value!r}, expected={expected!r}"
        )


def validate_sha256(value: object, label: str) -> str:
    if not isinstance(value, str) or not HEX_SHA256.fullmatch(value):
        raise PlatformLockError(f"{label} must be a lowercase SHA-256")
    return value


def validate_relative_path(value: object, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise PlatformLockError(f"{label} must be a non-empty relative path")
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise PlatformLockError(f"{label} is not a normalized relative path")
    return value


def repository_file(repo: Path, relative: str, label: str) -> Path:
    root = repo.resolve()
    requested = root.joinpath(*PurePosixPath(relative).parts)
    resolved = requested.resolve()
    try:
        common = Path(os.path.commonpath((str(root), str(resolved))))
    except ValueError as exc:
        raise PlatformLockError(f"{label} is on another filesystem") from exc
    if common != root or requested != resolved or requested.is_symlink():
        raise PlatformLockError(f"{label} escapes the repository or traverses a symlink")
    if not requested.is_file():
        raise PlatformLockError(f"{label} is not a regular repository file")
    return requested


def validate_missing_record(
    record: object,
    fields: Iterable[str],
    label: str,
    blockers: List[str],
) -> Mapping[str, Any]:
    item = exact_keys(record, fields, label)
    if item.get("required") is not True:
        raise PlatformLockError(f"{label} must remain required")
    if item.get("status") != "required-missing":
        raise PlatformLockError(
            f"{label} may only become verified with a schema-specific evidence validator"
        )
    blocker = item.get("blocker")
    if not isinstance(blocker, str) or not blocker.strip():
        raise PlatformLockError(f"{label} needs a non-empty blocker")
    blockers.append(f"{label}: {blocker}")
    return item


def validate_evidence_state(
    record: object,
    fields: Iterable[str],
    label: str,
    repo: Optional[Path],
    blockers: List[str],
    path_field: str = "evidence_path",
    digest_field: str = "evidence_sha256",
) -> Tuple[Mapping[str, Any], bool]:
    item = exact_keys(record, fields, label)
    if item.get("required") is not True:
        raise PlatformLockError(f"{label} must remain required")
    status = item.get("status")
    if status == "required-missing":
        blocker = item.get("blocker")
        if not isinstance(blocker, str) or not blocker.strip():
            raise PlatformLockError(f"{label} needs a non-empty blocker")
        blockers.append(f"{label}: {blocker}")
        return item, False
    if status != "verified":
        raise PlatformLockError(f"{label} has invalid status {status!r}")
    if item.get("blocker") is not None:
        raise PlatformLockError(f"verified {label} must clear its blocker")
    path_text = validate_relative_path(
        item.get(path_field), f"{label}.{path_field}"
    )
    expected = validate_sha256(
        item.get(digest_field), f"{label}.{digest_field}"
    )
    if repo is None:
        raise PlatformLockError(f"{label} claims evidence without a repository")
    path = repository_file(repo, path_text, f"{label}.{path_field}")
    size, actual = sha256_file(path)
    if size == 0 or actual != expected:
        raise PlatformLockError(f"{label} evidence file is empty or stale")
    return item, True


def validate_digest_fields(
    item: Mapping[str, Any], fields: Iterable[str], label: str
) -> None:
    for field in fields:
        validate_sha256(item[field], f"{label}.{field}")


def require_null_fields(
    item: Mapping[str, Any], fields: Iterable[str], label: str
) -> None:
    for field in fields:
        if item[field] is not None:
            raise PlatformLockError(f"{label}.{field} must be null while missing")


def validate_source_link(repo: Optional[Path]) -> None:
    if repo is None:
        return
    source, _ = read_json(repository_file(repo, SOURCE_LOCK_PATH.as_posix(), "source lock"))
    require_exact(source.get("lock_id"), EXPECTED_SOURCE["lock_id"], "source lock id")
    require_exact(source.get("target"), {"architecture": "x86_64", "distribution": "Rocky Linux", "release": "10.2"}, "source lock target")
    source_rpm = source.get("source_rpm")
    if not isinstance(source_rpm, dict):
        raise PlatformLockError("source lock source_rpm is missing")
    require_exact(source_rpm.get("nevra"), EXPECTED_SOURCE["kernel_source_nevra"], "source lock NEVRA")
    require_exact(source_rpm.get("sha256"), EXPECTED_SOURCE["source_rpm_sha256"], "source lock SRPM digest")
    dist_git = source.get("dist_git")
    if not isinstance(dist_git, dict):
        raise PlatformLockError("source lock dist_git is missing")
    require_exact(dist_git.get("commit"), EXPECTED_SOURCE["dist_git_commit"], "source lock dist-git commit")
    content = dist_git.get("content")
    if not isinstance(content, list):
        raise PlatformLockError("source lock dist-git content is missing")
    by_path = {
        item.get("path"): item
        for item in content
        if isinstance(item, dict) and isinstance(item.get("path"), str)
    }
    require_exact(
        by_path.get("SPECS/kernel.spec", {}).get("sha256"),
        "081eb3b79dbbd240d484c6b72ecc786abf9997f8040b88120165e9b32273fdfe",
        "source lock kernel.spec digest",
    )
    require_exact(
        by_path.get("SOURCES/kernel-x86_64-rhel.config", {}).get("sha256"),
        "5bbdda60ce822ec903c85d3d8ddda1bfc9493216bed86c6c432683aa50dcf50d",
        "source lock x86_64 config digest",
    )
    embedded = source.get("embedded_objects")
    if not isinstance(embedded, list):
        raise PlatformLockError("source lock embedded_objects is missing")
    archives = {
        item.get("sha256")
        for item in embedded
        if isinstance(item, dict) and item.get("role") == "Rocky-derived Linux source archive"
    }
    require_exact(
        archives,
        {EXPECTED_SOURCE["source_archive_sha256"]},
        "source lock embedded Linux archive",
    )


def validate_rpm_signature_evidence(
    path: Path,
    expected_nevra: str,
    expected_rpm_sha256: str,
    expected_algorithm: str,
) -> None:
    evidence, _ = read_json(path)
    exact_keys(
        evidence,
        {
            "command",
            "result",
            "rpm_sha256",
            "schema_version",
            "signature_algorithm",
            "signer_fingerprint",
            "stderr_sha256",
            "stdout_sha256",
            "subject_nevra",
            "verification_tool",
        },
        "RPM signature evidence",
    )
    require_exact(evidence["schema_version"], 1, "RPM signature evidence schema")
    require_exact(evidence["subject_nevra"], expected_nevra, "RPM signature subject")
    require_exact(evidence["rpm_sha256"], expected_rpm_sha256, "RPM signature artifact")
    require_exact(evidence["signature_algorithm"], expected_algorithm, "RPM signature algorithm")
    require_exact(evidence["signer_fingerprint"], EXPECTED_RELEASE_KEY["fingerprint"], "RPM signature signer")
    require_exact(evidence["result"], "PASS", "RPM signature result")
    if not isinstance(evidence["verification_tool"], str) or not evidence[
        "verification_tool"
    ].strip():
        raise PlatformLockError("RPM signature verification tool is missing")
    if not isinstance(evidence["command"], list) or not evidence["command"]:
        raise PlatformLockError("RPM signature command is missing")
    validate_sha256(evidence["stdout_sha256"], "RPM signature stdout digest")
    validate_sha256(evidence["stderr_sha256"], "RPM signature stderr digest")


def nevra(name: str, version: str, release: str, arch: str) -> str:
    return f"{name}-0:{version}-{release}.{arch}"


def expected_artifact_records() -> List[Dict[str, Any]]:
    records = []
    for name, role, version, release, arch, repository, location, size, digest in EXPECTED_DIRECT_ARTIFACTS:
        records.append(
            {
                "arch": arch,
                "epoch": 0,
                "name": name,
                "nevra": nevra(name, version, release, arch),
                "release": release,
                "repository_id": repository,
                "repository_location": location,
                "role": role,
                "sha256": digest,
                "size": size,
                "version": version,
            }
        )
    return records


def expected_probe_records() -> List[Dict[str, Any]]:
    return [dict(item) for item in EXPECTED_PROBES]


def validate_toolchain_lock(
    lock: Dict[str, Any], repo: Optional[Path] = None
) -> List[str]:
    exact_keys(
        lock,
        {
            "closure",
            "direct_artifacts",
            "gate",
            "kernel_requirements",
            "lock_id",
            "observed_at",
            "probe_evidence",
            "release_key",
            "repositories",
            "required_probes",
            "rpm_build_environment_evidence",
            "rustavailable_evidence",
            "schema_version",
            "source_lock",
            "source_spec_observation",
            "target",
        },
        "toolchain lock",
    )
    require_exact(lock["schema_version"], 1, "toolchain lock.schema_version")
    require_exact(lock["lock_id"], f"{LOCK_ID_PREFIX}-toolchain-v1", "toolchain lock.lock_id")
    require_exact(lock["observed_at"], "2026-08-11", "toolchain lock.observed_at")
    require_exact(lock["target"], EXPECTED_TARGET, "toolchain lock.target")
    require_exact(lock["source_lock"], EXPECTED_SOURCE, "toolchain lock.source_lock")
    require_exact(lock["release_key"], EXPECTED_RELEASE_KEY, "toolchain lock.release_key")
    validate_source_link(repo)

    artifacts = lock["direct_artifacts"]
    if not isinstance(artifacts, list) or len(artifacts) != len(EXPECTED_DIRECT_ARTIFACTS):
        raise PlatformLockError("direct artifact count changed")
    expected_records = expected_artifact_records()
    blockers: List[str] = []
    names: Set[str] = set()
    for index, (actual, expected) in enumerate(zip(artifacts, expected_records)):
        item = exact_keys(actual, {*expected, "verification"}, f"direct_artifacts[{index}]")
        for key, value in expected.items():
            require_exact(item[key], value, f"direct_artifacts[{index}].{key}")
        if item["name"] in names:
            raise PlatformLockError(f"duplicate direct artifact {item['name']}")
        names.add(str(item["name"]))
        verification = exact_keys(
            item["verification"],
            {
                "archive_path",
                "archive_verified",
                "blocker",
                "metadata_observed",
                "signature_algorithm",
                "signature_evidence_path",
                "signature_evidence_sha256",
                "signature_verified",
                "signer_fingerprint",
            },
            f"direct_artifacts[{index}].verification",
        )
        if verification["metadata_observed"] not in {True, False}:
            raise PlatformLockError(
                f"{item['nevra']} metadata_observed must be a boolean"
            )
        archive_verified = verification["archive_verified"] is True
        signature_verified = verification["signature_verified"] is True
        if verification["archive_verified"] not in {True, False} or verification[
            "signature_verified"
        ] not in {True, False}:
            raise PlatformLockError(f"{item['nevra']} verification flags must be booleans")
        if archive_verified != signature_verified:
            raise PlatformLockError(
                f"{item['nevra']} archive and signature verification must advance together"
            )
        if not archive_verified:
            for field in (
                "archive_path",
                "signature_algorithm",
                "signature_evidence_path",
                "signature_evidence_sha256",
                "signer_fingerprint",
            ):
                if verification[field] is not None:
                    raise PlatformLockError(
                        f"{item['nevra']} {field} must be null while unverified"
                    )
            blocker = verification["blocker"]
            if not isinstance(blocker, str) or not blocker.strip():
                raise PlatformLockError(f"{item['nevra']} needs a verification blocker")
            continue
        if verification["blocker"] is not None:
            raise PlatformLockError(
                f"verified {item['nevra']} must clear its blocker"
            )
        if repo is None:
            raise PlatformLockError(
                f"verified {item['nevra']} requires repository-contained evidence"
            )
        archive_path = repository_file(
            repo,
            validate_relative_path(
                verification["archive_path"],
                f"{item['nevra']} archive_path",
            ),
            f"{item['nevra']} archive_path",
        )
        size, digest = sha256_file(archive_path)
        if size != item["size"] or digest != item["sha256"]:
            raise PlatformLockError(
                f"verified {item['nevra']} archive bytes do not match the lock"
            )
        signature_path = repository_file(
            repo,
            validate_relative_path(
                verification["signature_evidence_path"],
                f"{item['nevra']} signature evidence",
            ),
            f"{item['nevra']} signature evidence",
        )
        _, signature_digest = sha256_file(signature_path)
        require_exact(
            signature_digest,
            verification["signature_evidence_sha256"],
            f"{item['nevra']} signature evidence digest",
        )
        if not isinstance(verification["signature_algorithm"], str) or not verification[
            "signature_algorithm"
        ].strip():
            raise PlatformLockError(f"{item['nevra']} signature algorithm is missing")
        require_exact(
            verification["signer_fingerprint"],
            EXPECTED_RELEASE_KEY["fingerprint"],
            f"{item['nevra']} signer fingerprint",
        )
        validate_rpm_signature_evidence(
            signature_path,
            item["nevra"],
            item["sha256"],
            verification["signature_algorithm"],
        )
    if not all(
        item["verification"]["archive_verified"]
        and item["verification"]["signature_verified"]
        for item in artifacts
    ):
        blockers.append(
            "direct_artifacts: all 20 RPM archives and individual header "
            "signatures are unverified"
        )

    repositories = lock["repositories"]
    expected_repo_ids = ["baseos", "appstream", "crb"]
    if not isinstance(repositories, list) or [item.get("id") for item in repositories] != expected_repo_ids:
        raise PlatformLockError("binary repository set/order changed")
    for index, repository in enumerate(repositories):
        item = exact_keys(
            repository,
            {
                "base_url",
                "blocker",
                "id",
                "metadata_observed",
                "primary_metadata_sha256",
                "repomd_sha256",
                "repomd_signature_verified",
                "snapshot_evidence_path",
                "snapshot_evidence_sha256",
            },
            f"repositories[{index}]",
        )
        expected_url = (
            f"https://download.rockylinux.org/pub/rocky/10.2/"
            f"{item['id'].title() if item['id'] != 'baseos' else 'BaseOS'}/x86_64/os/"
        )
        if item["id"] == "appstream":
            expected_url = "https://download.rockylinux.org/pub/rocky/10.2/AppStream/x86_64/os/"
        if item["id"] == "crb":
            expected_url = "https://download.rockylinux.org/pub/rocky/10.2/CRB/x86_64/os/"
        require_exact(item["base_url"], expected_url, f"repositories[{index}].base_url")
        observed = item["metadata_observed"] is True
        signed = item["repomd_signature_verified"] is True
        if item["metadata_observed"] not in {True, False} or item[
            "repomd_signature_verified"
        ] not in {True, False} or observed != signed:
            raise PlatformLockError(
                f"repository.{item['id']} observation and signature states must "
                "advance together"
            )
        if not observed:
            for field in (
                "primary_metadata_sha256",
                "repomd_sha256",
                "snapshot_evidence_path",
                "snapshot_evidence_sha256",
            ):
                if item[field] is not None:
                    raise PlatformLockError(f"repositories[{index}].{field} must be null")
            if not isinstance(item["blocker"], str) or not item["blocker"].strip():
                raise PlatformLockError(f"repositories[{index}] needs a blocker")
            blockers.append(f"repository.{item['id']}: {item['blocker']}")
            continue
        if item["blocker"] is not None:
            raise PlatformLockError(f"verified repository.{item['id']} must clear blocker")
        validate_digest_fields(
            item,
            {"primary_metadata_sha256", "repomd_sha256", "snapshot_evidence_sha256"},
            f"repository.{item['id']}",
        )
        if repo is None:
            raise PlatformLockError("verified repository snapshot needs a repository")
        snapshot_path = repository_file(
            repo,
            validate_relative_path(
                item["snapshot_evidence_path"],
                f"repository.{item['id']}.snapshot_evidence_path",
            ),
            f"repository.{item['id']}.snapshot_evidence_path",
        )
        _, snapshot_digest = sha256_file(snapshot_path)
        require_exact(
            snapshot_digest,
            item["snapshot_evidence_sha256"],
            f"repository.{item['id']} snapshot evidence digest",
        )
        snapshot, _ = read_json(snapshot_path)
        exact_keys(
            snapshot,
            {
                "base_url",
                "files",
                "primary_metadata_sha256",
                "release_key_fingerprint",
                "repomd_sha256",
                "repository_id",
                "schema_version",
                "signature_verified",
                "verification_tool",
            },
            f"repository.{item['id']} snapshot evidence",
        )
        require_exact(snapshot["schema_version"], 1, "snapshot schema")
        require_exact(snapshot["repository_id"], item["id"], "snapshot repository id")
        require_exact(snapshot["base_url"], item["base_url"], "snapshot base URL")
        require_exact(snapshot["repomd_sha256"], item["repomd_sha256"], "snapshot repomd digest")
        require_exact(snapshot["primary_metadata_sha256"], item["primary_metadata_sha256"], "snapshot primary digest")
        require_exact(snapshot["release_key_fingerprint"], EXPECTED_RELEASE_KEY["fingerprint"], "snapshot signer")
        require_exact(snapshot["signature_verified"], True, "snapshot signature result")
        if not isinstance(snapshot["verification_tool"], str) or not snapshot[
            "verification_tool"
        ].strip():
            raise PlatformLockError("snapshot verification tool is missing")
        files = snapshot["files"]
        if not isinstance(files, list) or len(files) < 4:
            raise PlatformLockError("snapshot evidence must retain key, repomd, signature, and primary")
        roles: Set[str] = set()
        role_digests: Dict[str, str] = {}
        for file_index, file_entry in enumerate(files):
            file_item = exact_keys(
                file_entry,
                {"path", "role", "sha256", "size"},
                f"repository.{item['id']}.files[{file_index}]",
            )
            role = file_item["role"]
            if not isinstance(role, str) or role in roles:
                raise PlatformLockError("snapshot evidence file roles must be unique")
            roles.add(role)
            retained_path = repository_file(
                repo,
                validate_relative_path(file_item["path"], "snapshot retained file"),
                "snapshot retained file",
            )
            size, digest = sha256_file(retained_path)
            require_exact(size, file_item["size"], "snapshot retained file size")
            require_exact(digest, file_item["sha256"], "snapshot retained file digest")
            role_digests[role] = digest
        if not {"release-key", "repomd", "repomd-signature", "primary"}.issubset(roles):
            raise PlatformLockError("snapshot evidence retained-file roles are incomplete")
        require_exact(
            role_digests["release-key"],
            EXPECTED_RELEASE_KEY["sha256"],
            "snapshot release-key digest",
        )
        require_exact(
            role_digests["repomd"], item["repomd_sha256"], "snapshot repomd file"
        )
        require_exact(
            role_digests["primary"],
            item["primary_metadata_sha256"],
            "snapshot primary file",
        )

    repository_observations = {
        item["id"]: item["metadata_observed"] for item in repositories
    }
    for artifact in artifacts:
        require_exact(
            artifact["verification"]["metadata_observed"],
            repository_observations[artifact["repository_id"]],
            f"{artifact['nevra']} repository metadata binding",
        )

    closure_fields = {
        "all_archives_verified",
        "all_signatures_verified",
        "blocker",
        "direct_nevras",
        "manifest_path",
        "manifest_sha256",
        "offline_install_verified",
        "package_count",
        "required",
        "resolution_scope",
        "rpm_set_sha256",
        "status",
        "unresolved_dependencies",
    }
    closure, closure_verified = validate_evidence_state(
        lock["closure"],
        closure_fields,
        "closure",
        repo,
        blockers,
        path_field="manifest_path",
        digest_field="manifest_sha256",
    )
    expected_nevras = sorted(record["nevra"] for record in expected_records)
    closure_environment_digest: Optional[str] = None
    require_exact(closure["direct_nevras"], expected_nevras, "closure.direct_nevras")
    require_exact(
        closure["resolution_scope"],
        "The full Rocky-effective kernel.spec BuildRequires set after the reviewed Rocky Rust/LLVM spec change, plus every transitive dependency; closure is not limited to direct_nevras.",
        "closure.resolution_scope",
    )
    if not closure_verified:
        for flag in ("all_archives_verified", "all_signatures_verified", "offline_install_verified"):
            if closure[flag] is not False:
                raise PlatformLockError(f"closure.{flag} must be false while missing")
        for field in (
            "manifest_path",
            "manifest_sha256",
            "package_count",
            "rpm_set_sha256",
            "unresolved_dependencies",
        ):
            if closure[field] is not None:
                raise PlatformLockError(f"closure.{field} must be null while missing")
    else:
        for flag in ("all_archives_verified", "all_signatures_verified", "offline_install_verified"):
            if closure[flag] is not True:
                raise PlatformLockError(f"verified closure requires {flag}=true")
        if not isinstance(closure["package_count"], int) or closure["package_count"] <= len(expected_nevras):
            raise PlatformLockError("full closure must include transitive packages")
        require_exact(closure["unresolved_dependencies"], [], "closure unresolved dependencies")
        validate_sha256(closure["rpm_set_sha256"], "closure.rpm_set_sha256")
        assert repo is not None
        manifest_path = repository_file(
            repo,
            validate_relative_path(closure["manifest_path"], "closure.manifest_path"),
            "closure.manifest_path",
        )
        manifest, _ = read_json(manifest_path)
        exact_keys(
            manifest,
            {"environment_manifest_sha256", "offline_install_result", "package_count", "packages", "requested_direct_nevras", "resolution_scope", "rpm_set_sha256", "schema_version", "source_spec_sha256", "unresolved_dependencies"},
            "closure manifest",
        )
        require_exact(manifest["schema_version"], 1, "closure manifest schema")
        require_exact(manifest["source_spec_sha256"], "081eb3b79dbbd240d484c6b72ecc786abf9997f8040b88120165e9b32273fdfe", "closure source spec")
        require_exact(manifest["requested_direct_nevras"], expected_nevras, "closure requested roots")
        require_exact(manifest["resolution_scope"], closure["resolution_scope"], "closure resolution scope")
        require_exact(manifest["package_count"], closure["package_count"], "closure package count")
        require_exact(manifest["rpm_set_sha256"], closure["rpm_set_sha256"], "closure RPM-set digest")
        require_exact(manifest["unresolved_dependencies"], [], "closure manifest unresolved dependencies")
        require_exact(manifest["offline_install_result"], "PASS", "closure offline install")
        validate_sha256(manifest["environment_manifest_sha256"], "closure environment digest")
        closure_environment_digest = manifest["environment_manifest_sha256"]
        packages = manifest["packages"]
        if not isinstance(packages, list) or len(packages) != closure["package_count"]:
            raise PlatformLockError("closure package manifest count mismatch")
        package_nevras: Set[str] = set()
        canonical_rpm_rows: List[str] = []
        for package_index, package in enumerate(packages):
            package_item = exact_keys(
                package,
                {"archive_path", "arch", "nevra", "sha256", "signature_algorithm", "signature_evidence_path", "signature_evidence_sha256", "signature_verified", "signer_fingerprint", "size"},
                f"closure.packages[{package_index}]",
            )
            package_nevra = package_item["nevra"]
            if not isinstance(package_nevra, str) or package_nevra in package_nevras:
                raise PlatformLockError("closure package NEVRAs must be unique")
            package_nevras.add(package_nevra)
            if package_item["signature_verified"] is not True:
                raise PlatformLockError("closure package signature is unverified")
            require_exact(package_item["signer_fingerprint"], EXPECTED_RELEASE_KEY["fingerprint"], "closure package signer")
            if not isinstance(package_item["signature_algorithm"], str) or not package_item["signature_algorithm"].strip():
                raise PlatformLockError("closure package signature algorithm missing")
            rpm_path = repository_file(repo, validate_relative_path(package_item["archive_path"], "closure archive"), "closure archive")
            rpm_size, rpm_digest = sha256_file(rpm_path)
            require_exact(rpm_size, package_item["size"], "closure RPM size")
            require_exact(rpm_digest, package_item["sha256"], "closure RPM digest")
            signature_path = repository_file(repo, validate_relative_path(package_item["signature_evidence_path"], "closure signature evidence"), "closure signature evidence")
            _, signature_digest = sha256_file(signature_path)
            require_exact(signature_digest, package_item["signature_evidence_sha256"], "closure signature evidence digest")
            validate_rpm_signature_evidence(
                signature_path,
                package_nevra,
                package_item["sha256"],
                package_item["signature_algorithm"],
            )
            canonical_rpm_rows.append(f"{package_nevra}\t{rpm_digest}\n")
        if not set(expected_nevras).issubset(package_nevras):
            raise PlatformLockError("closure omits one or more direct roots")
        require_exact(
            sha256_bytes("".join(sorted(canonical_rpm_rows)).encode()),
            closure["rpm_set_sha256"],
            "closure calculated RPM-set digest",
        )

    probe_evidence, probe_verified = validate_evidence_state(
        lock["probe_evidence"],
        {"blocker", "environment_manifest_sha256", "evidence_path", "evidence_sha256", "required", "results", "status"},
        "probe_evidence",
        repo,
        blockers,
    )
    if not probe_verified:
        require_null_fields(
            probe_evidence,
            {"environment_manifest_sha256", "evidence_path", "evidence_sha256", "results"},
            "probe_evidence",
        )
    else:
        validate_sha256(
            probe_evidence["environment_manifest_sha256"],
            "probe_evidence.environment_manifest_sha256",
        )
        results = probe_evidence["results"]
        if not isinstance(results, list) or len(results) != len(expected_probe_records()):
            raise PlatformLockError("verified probe evidence must cover every required probe")
        expected_by_id = {item["id"]: item for item in expected_probe_records()}
        actual_ids: Set[str] = set()
        for index, result in enumerate(results):
            row = exact_keys(
                result,
                {
                    "binary_path",
                    "binary_sha256",
                    "command",
                    "exit_code",
                    "id",
                    "loaded_library_path",
                    "loaded_library_sha256",
                    "package_nevra",
                    "parsed_version",
                    "required_file_path",
                    "required_file_sha256",
                    "stderr_sha256",
                    "stdout_sha256",
                },
                f"probe_evidence.results[{index}]",
            )
            probe_id = row["id"]
            if probe_id in actual_ids or probe_id not in expected_by_id:
                raise PlatformLockError("verified probe ids are duplicate or unexpected")
            actual_ids.add(str(probe_id))
            expected_probe = expected_by_id[probe_id]
            require_exact(
                row["command"], expected_probe["command"], f"probe {probe_id} command"
            )
            require_exact(row["exit_code"], 0, f"probe {probe_id} exit_code")
            for digest_field in ("binary_sha256", "stdout_sha256", "stderr_sha256"):
                validate_sha256(row[digest_field], f"probe {probe_id}.{digest_field}")
            if not isinstance(row["binary_path"], str) or not row["binary_path"].startswith("/"):
                raise PlatformLockError(f"probe {probe_id} binary_path must be absolute")
            artifact_record = next(
                item for item in expected_records if item["name"] == expected_probe["artifact"]
            )
            expected_probe_owner = artifact_record["nevra"]
            if probe_id == "llvm":
                expected_probe_owner = EXPECTED_LLVM_CONFIG_OWNER_POLICY[
                    "expected_package_nevra"
                ]
                require_exact(
                    row["binary_path"],
                    EXPECTED_LLVM_CONFIG_OWNER_POLICY["binary_path"],
                    "llvm-config binary path",
                )
            require_exact(
                row["package_nevra"],
                expected_probe_owner,
                f"probe {probe_id} package NEVRA",
            )
            if expected_probe["expected_version"] is not None:
                require_exact(
                    row["parsed_version"],
                    expected_probe["expected_version"],
                    f"probe {probe_id} parsed version",
                )
            elif row["parsed_version"] is not None:
                raise PlatformLockError(f"probe {probe_id} parsed_version must be null")
            if probe_id == "rust-src-core":
                for field in ("required_file_path", "required_file_sha256"):
                    if not isinstance(row[field], str) or not row[field]:
                        raise PlatformLockError(f"probe {probe_id}.{field} is missing")
                validate_sha256(
                    row["required_file_sha256"],
                    f"probe {probe_id}.required_file_sha256",
                )
            elif probe_id == "libclang-via-bindgen":
                if not isinstance(row["loaded_library_path"], str) or not row[
                    "loaded_library_path"
                ].startswith("/"):
                    raise PlatformLockError("libclang loaded library path is missing")
                validate_sha256(
                    row["loaded_library_sha256"],
                    "libclang loaded library digest",
                )
            else:
                for field in (
                    "loaded_library_path",
                    "loaded_library_sha256",
                    "required_file_path",
                    "required_file_sha256",
                ):
                    if row[field] is not None:
                        raise PlatformLockError(f"probe {probe_id}.{field} must be null")
    rpm_environment, rpm_environment_verified = validate_evidence_state(
        lock["rpm_build_environment_evidence"],
        {"blocker", "buildroot_oci_digest", "environment_manifest_sha256", "evidence_path", "evidence_sha256", "offline_transaction_verified", "repository_snapshot_manifest_sha256", "required", "rpm_macro_manifest_sha256", "spec_rust_buildrequires_rocky_verified", "status"},
        "rpm_build_environment_evidence",
        repo,
        blockers,
    )
    if not rpm_environment_verified:
        require_null_fields(
            rpm_environment,
            {
                "buildroot_oci_digest",
                "environment_manifest_sha256",
                "evidence_path",
                "evidence_sha256",
                "repository_snapshot_manifest_sha256",
                "rpm_macro_manifest_sha256",
            },
            "rpm_build_environment_evidence",
        )
        for flag in ("offline_transaction_verified", "spec_rust_buildrequires_rocky_verified"):
            if rpm_environment[flag] is not False:
                raise PlatformLockError(
                    f"rpm_build_environment_evidence.{flag} must be false while missing"
                )
    else:
        if not isinstance(rpm_environment["buildroot_oci_digest"], str) or not re.fullmatch(
            r"sha256:[0-9a-f]{64}", rpm_environment["buildroot_oci_digest"]
        ):
            raise PlatformLockError("verified buildroot OCI digest is invalid")
        validate_digest_fields(
            rpm_environment,
            {
                "environment_manifest_sha256",
                "repository_snapshot_manifest_sha256",
                "rpm_macro_manifest_sha256",
            },
            "rpm_build_environment_evidence",
        )
        for flag in ("offline_transaction_verified", "spec_rust_buildrequires_rocky_verified"):
            if rpm_environment[flag] is not True:
                raise PlatformLockError(
                    f"verified rpm environment requires {flag}=true"
                )
        if probe_verified:
            require_exact(
                probe_evidence["environment_manifest_sha256"],
                rpm_environment["environment_manifest_sha256"],
                "probe environment binding",
            )
        if closure_environment_digest is not None:
            require_exact(
                closure_environment_digest,
                rpm_environment["environment_manifest_sha256"],
                "closure environment binding",
            )
    rustavailable, rustavailable_verified = validate_evidence_state(
        lock["rustavailable_evidence"],
        {"blocker", "command", "config_sha256", "environment_manifest_sha256", "evidence_path", "evidence_sha256", "exit_code", "required", "status", "stderr_sha256", "stdout_sha256"},
        "rustavailable_evidence",
        repo,
        blockers,
    )
    require_exact(rustavailable["command"], ["make", "LLVM=1", "rustavailable"], "rustavailable command")
    if not rustavailable_verified:
        require_null_fields(
            rustavailable,
            {
                "config_sha256",
                "environment_manifest_sha256",
                "evidence_path",
                "evidence_sha256",
                "exit_code",
                "stderr_sha256",
                "stdout_sha256",
            },
            "rustavailable_evidence",
        )
    else:
        require_exact(rustavailable["exit_code"], 0, "rustavailable exit_code")
        validate_digest_fields(
            rustavailable,
            {"config_sha256", "environment_manifest_sha256", "stderr_sha256", "stdout_sha256"},
            "rustavailable_evidence",
        )
        require_exact(
            rustavailable["environment_manifest_sha256"],
            rpm_environment["environment_manifest_sha256"],
            "rustavailable environment binding",
        )

    requirements = exact_keys(
        lock["kernel_requirements"],
        {"build_command_prefix", "minimum_source", "minimum_versions"},
        "kernel_requirements",
    )
    require_exact(requirements["build_command_prefix"], ["make", "LLVM=1"], "kernel build prefix")
    require_exact(
        requirements["minimum_source"],
        {"path": "scripts/min-tool-version.sh", "sha256": "24b28bb8c3aaef69c00aac6273bf2b914c7bc452f68f9c4dc671d6670c1a3ffe"},
        "kernel minimum source",
    )
    minimums = requirements["minimum_versions"]
    require_exact(minimums, EXPECTED_MINIMUM_ROWS, "kernel minimum versions")
    for index, minimum in enumerate(minimums):
        exact_keys(
            minimum,
            {"reason", "role", "version"},
            f"kernel minimum versions[{index}]",
        )

    observation = lock["source_spec_observation"]
    expected_observation = {
        "path": "SPECS/kernel.spec",
        "rocky_rust_buildrequires_effective": False,
        "rust_buildrequires_condition": "0%{?fedora}",
        "sha256": "081eb3b79dbbd240d484c6b72ecc786abf9997f8040b88120165e9b32273fdfe",
    }
    require_exact(observation, expected_observation, "source_spec_observation")

    probes = lock["required_probes"]
    require_exact(probes, expected_probe_records(), "required probes")
    if not isinstance(probes, list):
        raise PlatformLockError("required probes must be a list")
    for index, (probe, expected) in enumerate(
        zip(probes, expected_probe_records())
    ):
        exact_keys(probe, expected.keys(), f"required_probes[{index}]")

    gate = exact_keys(lock["gate"], {"credit_eligible", "gate_id", "policy"}, "toolchain gate")
    require_exact(gate["gate_id"], "RK-003", "toolchain gate id")
    if gate["credit_eligible"] is not (not blockers):
        raise PlatformLockError("RK-003 credit_eligible contradicts evidence state")
    if "forbidden" not in str(gate["policy"]).lower():
        raise PlatformLockError("RK-003 gate policy is not fail-closed")
    return blockers


def parse_kconfig(text: str, label: str) -> Dict[str, str]:
    values: Dict[str, str] = {}
    for line_number, raw in enumerate(text.splitlines(), start=1):
        line = raw.strip()
        if not line or (line.startswith("#") and not line.startswith("# CONFIG_")):
            continue
        match = KCONFIG_SET.fullmatch(line)
        value: str
        if match:
            symbol, value = match.groups()
            if value == "n":
                raise PlatformLockError(
                    f"{label}:{line_number}: use '# {symbol} is not set' for n"
                )
        else:
            match = KCONFIG_UNSET.fullmatch(line)
            if not match:
                raise PlatformLockError(f"{label}:{line_number}: malformed Kconfig line")
            symbol, value = match.group(1), "n"
        if symbol in values:
            raise PlatformLockError(f"{label}:{line_number}: duplicate {symbol}")
        values[symbol] = value
    if not values:
        raise PlatformLockError(f"{label} contains no Kconfig symbols")
    return values


def config_delta(
    baseline: Mapping[str, str], resolved: Mapping[str, str]
) -> Dict[str, Tuple[Optional[str], Optional[str]]]:
    return {
        symbol: (baseline.get(symbol), resolved.get(symbol))
        for symbol in sorted(set(baseline) | set(resolved))
        if baseline.get(symbol) != resolved.get(symbol)
    }


def validate_classified_changes(
    rows: Any, label: str, require_nonempty: bool = False
) -> List[Dict[str, str]]:
    if not isinstance(rows, list) or (require_nonempty and not rows):
        raise PlatformLockError(f"{label} must be a non-empty list")
    normalized: List[Dict[str, str]] = []
    seen = set()
    for index, row in enumerate(rows):
        item = exact_keys(row, {"after", "before", "symbol"}, f"{label}[{index}]")
        if not all(isinstance(item[key], str) and item[key] for key in item):
            raise PlatformLockError(f"{label}[{index}] has invalid values")
        if not item["symbol"].startswith("CONFIG_") or item["symbol"] in seen:
            raise PlatformLockError(f"{label}[{index}] has a duplicate or invalid symbol")
        if item["before"] == item["after"]:
            raise PlatformLockError(f"{label}[{index}] does not describe a change")
        seen.add(item["symbol"])
        normalized.append(dict(item))
    ordered = sorted(normalized, key=lambda item: item["symbol"])
    require_exact(normalized, ordered, f"{label} ordering")
    return ordered


def validate_presence_changes(rows: Any, label: str) -> List[Dict[str, str]]:
    normalized = validate_classified_changes(rows, label, require_nonempty=True)
    for index, row in enumerate(normalized):
        if {row["before"], row["after"]} != {"<absent>", "n"}:
            raise PlatformLockError(
                f"{label}[{index}] is not an explicit-n/absent presence change"
            )
    return normalized


def validate_resolved_config(
    baseline: Mapping[str, str], resolved: Mapping[str, str], policy: Mapping[str, Any]
) -> None:
    delta = config_delta(baseline, resolved)
    expected = {symbol: pair for symbol, pair in EXPECTED_CONFIG_CHANGES.items()}
    if delta != expected:
        raise PlatformLockError(
            f"resolved config delta is not exactly allowlisted: actual={delta}, expected={expected}"
        )
    expected_preserve = (
        EXPECTED_PRESERVE_V2
        if policy.get("lock_id") == f"{LOCK_ID_PREFIX}-config-policy-v2"
        else EXPECTED_PRESERVE
    )
    for symbol, value in expected_preserve.items():
        if baseline.get(symbol) != value or resolved.get(symbol) != value:
            raise PlatformLockError(f"preserved symbol {symbol} must remain {value!r}")
    if policy["module_version_policy"].get("no_rocky_kabi_claim") is not True:
        raise PlatformLockError("Rocky kABI must not be claimed")


def validate_config_policy_v1(
    policy: Dict[str, Any], fragment_bytes: bytes, repo: Optional[Path] = None
) -> List[str]:
    exact_keys(
        policy,
        {
            "baseline",
            "delta",
            "dependency_contract",
            "gate",
            "lock_id",
            "module_version_policy",
            "observed_at",
            "preserve",
            "schema_version",
            "source_lock_id",
            "target",
            "toolchain_lock_id",
            "verification_evidence",
        },
        "config policy",
    )
    require_exact(policy["schema_version"], 1, "config policy.schema_version")
    require_exact(policy["lock_id"], f"{LOCK_ID_PREFIX}-config-policy-v1", "config policy.lock_id")
    require_exact(policy["observed_at"], "2026-08-11", "config policy.observed_at")
    require_exact(policy["target"], EXPECTED_TARGET, "config policy.target")
    require_exact(policy["source_lock_id"], EXPECTED_SOURCE["lock_id"], "config policy.source_lock_id")
    require_exact(policy["toolchain_lock_id"], f"{LOCK_ID_PREFIX}-toolchain-v1", "config policy.toolchain_lock_id")
    validate_source_link(repo)

    baseline = exact_keys(
        policy["baseline"],
        {"dist_git_commit", "git_blob", "normalization", "path", "sha256", "symbol_count"},
        "config baseline",
    )
    require_exact(baseline["dist_git_commit"], EXPECTED_SOURCE["dist_git_commit"], "config baseline commit")
    require_exact(baseline["git_blob"], "b390068c4142a5a26e60c9774410ed976e48f004", "config baseline blob")
    require_exact(baseline["path"], "SOURCES/kernel-x86_64-rhel.config", "config baseline path")
    require_exact(baseline["sha256"], "5bbdda60ce822ec903c85d3d8ddda1bfc9493216bed86c6c432683aa50dcf50d", "config baseline sha256")
    require_exact(baseline["symbol_count"], 8468, "config baseline symbol_count")

    delta = exact_keys(
        policy["delta"],
        {"allowed_symbols", "changes", "fragment_path", "fragment_sha256", "unexpected_changes_forbidden"},
        "config delta",
    )
    require_exact(delta["allowed_symbols"], ["CONFIG_MODVERSIONS", "CONFIG_RUST"], "config allowed symbols")
    if delta["unexpected_changes_forbidden"] is not True:
        raise PlatformLockError("unexpected config changes must remain forbidden")
    expected_changes = [
        {"baseline": "n", "reason": "Enable native Rust-for-Linux modules.", "resolved": "y", "symbol": "CONFIG_RUST"},
        {"baseline": "y", "reason": "Linux 6.12 CONFIG_RUST has a hard dependency on !MODVERSIONS.", "resolved": "n", "symbol": "CONFIG_MODVERSIONS"},
    ]
    require_exact(delta["changes"], expected_changes, "config delta changes")
    require_exact(delta["fragment_path"], CONFIG_FRAGMENT_PATH.as_posix(), "config fragment path")
    fragment_digest = sha256_bytes(fragment_bytes)
    require_exact(delta["fragment_sha256"], fragment_digest, "config fragment digest")
    fragment = parse_kconfig(fragment_bytes.decode("utf-8"), "config fragment")
    require_exact(fragment, {symbol: resolved for symbol, (_, resolved) in EXPECTED_CONFIG_CHANGES.items()}, "config fragment")

    preserve = policy["preserve"]
    if not isinstance(preserve, list):
        raise PlatformLockError("preserve must be a list")
    preserve_map: Dict[str, str] = {}
    for index, entry in enumerate(preserve):
        item = exact_keys(entry, {"symbol", "value"}, f"preserve[{index}]")
        symbol = item["symbol"]
        value = item["value"]
        if not isinstance(symbol, str) or not isinstance(value, str) or symbol in preserve_map:
            raise PlatformLockError(f"preserve[{index}] is malformed or duplicate")
        preserve_map[symbol] = value
    require_exact(preserve_map, EXPECTED_PRESERVE, "preserved config symbols")

    dependency = exact_keys(
        policy["dependency_contract"],
        {"init_kconfig_sha256", "kconfig_debug_sha256", "requirements", "rust_is_available_script_sha256"},
        "dependency contract",
    )
    require_exact(dependency["init_kconfig_sha256"], "35cfd4cc4e8850302a072b9d8aef35d827883f6e30f4ff2d428d12eb622fa749", "init Kconfig digest")
    require_exact(dependency["kconfig_debug_sha256"], "5d6e9c71ec42a48908afac2c82a8944340d0b4ebf45e5b1f68bf5eaa70bfb372", "debug Kconfig digest")
    require_exact(dependency["rust_is_available_script_sha256"], "87dac7e23370dd8166e0652dbaadfb89e050a01b5911801fa0a288bde952b9c2", "rust_is_available digest")
    requirements = dependency["requirements"]
    if not isinstance(requirements, list):
        raise PlatformLockError("dependency requirements must be a list")
    dependency_map = {item.get("symbol"): item.get("expected") for item in requirements if isinstance(item, dict)}
    require_exact(dependency_map, EXPECTED_DEPENDENCIES, "dependency requirements")
    for index, item in enumerate(requirements):
        exact_keys(item, {"expected", "source", "symbol"}, f"dependency requirements[{index}]")
        if not isinstance(item["source"], str) or not item["source"].strip():
            raise PlatformLockError(f"dependency requirements[{index}] has no source")

    module_policy = exact_keys(
        policy["module_version_policy"],
        {"atomic_kernel_module_nvr_required", "config_modversions", "exact_nvr_only", "no_rocky_kabi_claim", "policy", "weak_updates_forbidden"},
        "module version policy",
    )
    for flag in ("atomic_kernel_module_nvr_required", "exact_nvr_only", "no_rocky_kabi_claim", "weak_updates_forbidden"):
        if module_policy[flag] is not True:
            raise PlatformLockError(f"module_version_policy.{flag} must remain true")
    require_exact(module_policy["config_modversions"], "n", "module MODVERSIONS policy")
    if "R1 and R2" not in str(module_policy["policy"]):
        raise PlatformLockError("module version policy does not bind R1 to R2")

    evidence = exact_keys(
        policy["verification_evidence"],
        {"build_config", "dependency_assertions", "olddefconfig_delta"},
        "config verification evidence",
    )
    blockers: List[str] = []
    build_config, build_config_verified = validate_evidence_state(
        evidence["build_config"],
        {"blocker", "build_id", "evidence_path", "evidence_sha256", "final_config_sha256", "kernel_nvr", "required", "status"},
        "build_config",
        repo,
        blockers,
    )
    if not build_config_verified:
        require_null_fields(
            build_config,
            {"build_id", "evidence_path", "evidence_sha256", "final_config_sha256", "kernel_nvr"},
            "build_config",
        )
    else:
        validate_sha256(build_config["final_config_sha256"], "build_config.final_config_sha256")
        if not isinstance(build_config["build_id"], str) or not build_config["build_id"]:
            raise PlatformLockError("verified build config needs a build ID")
        if not isinstance(build_config["kernel_nvr"], str) or not build_config[
            "kernel_nvr"
        ].startswith(EXPECTED_TARGET["kernel_nvr_base"]):
            raise PlatformLockError("verified build config has wrong kernel NVR")
    dependency_assertions, dependency_verified = validate_evidence_state(
        evidence["dependency_assertions"],
        {"blocker", "evidence_path", "evidence_sha256", "required", "results", "status"},
        "dependency_assertions",
        repo,
        blockers,
    )
    if not dependency_verified:
        require_null_fields(
            dependency_assertions,
            {"evidence_path", "evidence_sha256", "results"},
            "dependency_assertions",
        )
    else:
        results = dependency_assertions["results"]
        require_exact(results, EXPECTED_DEPENDENCIES, "dependency assertion results")
    olddefconfig_delta, olddefconfig_verified = validate_evidence_state(
        evidence["olddefconfig_delta"],
        {"baseline_config_sha256", "blocker", "changed_symbols", "command_manifest_sha256", "environment_manifest_sha256", "evidence_path", "evidence_sha256", "generated_symbol_allowlist", "generated_symbol_results", "required", "resolved_config_sha256", "second_pass_config_sha256", "status", "unexpected_symbols"},
        "olddefconfig_delta",
        repo,
        blockers,
    )
    require_exact(
        olddefconfig_delta["generated_symbol_allowlist"],
        EXPECTED_GENERATED_CONFIG_SYMBOLS,
        "olddefconfig generated symbol allowlist",
    )
    if not olddefconfig_verified:
        require_null_fields(
            olddefconfig_delta,
            {
                "baseline_config_sha256",
                "changed_symbols",
                "command_manifest_sha256",
                "environment_manifest_sha256",
                "evidence_path",
                "evidence_sha256",
                "generated_symbol_results",
                "resolved_config_sha256",
                "second_pass_config_sha256",
                "unexpected_symbols",
            },
            "olddefconfig_delta",
        )
    else:
        validate_digest_fields(
            olddefconfig_delta,
            {
                "baseline_config_sha256",
                "command_manifest_sha256",
                "environment_manifest_sha256",
                "resolved_config_sha256",
                "second_pass_config_sha256",
            },
            "olddefconfig_delta",
        )
        require_exact(
            olddefconfig_delta["baseline_config_sha256"],
            baseline["sha256"],
            "olddefconfig baseline binding",
        )
        require_exact(
            olddefconfig_delta["resolved_config_sha256"],
            olddefconfig_delta["second_pass_config_sha256"],
            "olddefconfig idempotence",
        )
        require_exact(
            olddefconfig_delta["changed_symbols"],
            [
                {"baseline": "n", "resolved": "y", "symbol": "CONFIG_RUST"},
                {"baseline": "y", "resolved": "n", "symbol": "CONFIG_MODVERSIONS"},
            ],
            "olddefconfig requested changes",
        )
        require_exact(olddefconfig_delta["unexpected_symbols"], [], "olddefconfig unexpected symbols")
        generated_results = olddefconfig_delta["generated_symbol_results"]
        if not isinstance(generated_results, dict) or set(generated_results) != set(
            EXPECTED_GENERATED_CONFIG_SYMBOLS
        ):
            raise PlatformLockError("olddefconfig generated-symbol results are incomplete")
        if generated_results.get("CONFIG_RUST_IS_AVAILABLE") != "y":
            raise PlatformLockError("generated CONFIG_RUST_IS_AVAILABLE must be y")
        for symbol, value in generated_results.items():
            if not isinstance(value, str) or not value:
                raise PlatformLockError(f"generated {symbol} value is missing")
        require_exact(
            build_config["final_config_sha256"],
            olddefconfig_delta["resolved_config_sha256"],
            "production build config binding",
        )

    gate = exact_keys(policy["gate"], {"credit_eligible", "gate_id", "policy"}, "config gate")
    require_exact(gate["gate_id"], "RK-005", "config gate id")
    if gate["credit_eligible"] is not (not blockers):
        raise PlatformLockError("RK-005 credit_eligible contradicts evidence state")
    if "forbidden" not in str(gate["policy"]).lower():
        raise PlatformLockError("RK-005 gate policy is not fail-closed")
    return blockers


def validate_config_policy_v2(
    policy: Dict[str, Any], fragment_bytes: bytes, repo: Optional[Path] = None
) -> List[str]:
    exact_keys(
        policy,
        {
            "baseline",
            "delta",
            "dependency_contract",
            "gate",
            "lock_id",
            "module_version_policy",
            "observed_at",
            "preserve",
            "resolution_classification",
            "schema_version",
            "source_lock_id",
            "target",
            "tool_owner_policy",
            "toolchain_lock_id",
            "verification_evidence",
        },
        "config policy",
    )
    require_exact(policy["schema_version"], 2, "config policy.schema_version")
    require_exact(policy["lock_id"], f"{LOCK_ID_PREFIX}-config-policy-v2", "config policy.lock_id")
    require_exact(policy["observed_at"], "2026-08-17", "config policy.observed_at")
    require_exact(policy["target"], EXPECTED_TARGET, "config policy.target")
    require_exact(policy["source_lock_id"], EXPECTED_SOURCE["lock_id"], "config policy.source_lock_id")
    require_exact(policy["toolchain_lock_id"], f"{LOCK_ID_PREFIX}-toolchain-v1", "config policy.toolchain_lock_id")
    validate_source_link(repo)

    baseline = exact_keys(
        policy["baseline"],
        {"dist_git_commit", "git_blob", "normalization", "path", "sha256", "symbol_count"},
        "config baseline",
    )
    require_exact(baseline["dist_git_commit"], EXPECTED_SOURCE["dist_git_commit"], "config baseline commit")
    require_exact(baseline["git_blob"], "b390068c4142a5a26e60c9774410ed976e48f004", "config baseline blob")
    require_exact(baseline["path"], "SOURCES/kernel-x86_64-rhel.config", "config baseline path")
    require_exact(baseline["sha256"], "5bbdda60ce822ec903c85d3d8ddda1bfc9493216bed86c6c432683aa50dcf50d", "config baseline sha256")
    require_exact(baseline["symbol_count"], 8468, "config baseline symbol_count")
    require_exact(
        baseline["normalization"],
        EXPECTED_BASELINE_NORMALIZATION_V2,
        "config baseline normalization",
    )

    delta = exact_keys(
        policy["delta"],
        {"allowed_symbols", "changes", "fragment_path", "fragment_sha256", "unexpected_changes_forbidden"},
        "config delta",
    )
    require_exact(delta["allowed_symbols"], ["CONFIG_MODVERSIONS", "CONFIG_RUST"], "config allowed symbols")
    if delta["unexpected_changes_forbidden"] is not True:
        raise PlatformLockError("unexpected config changes must remain forbidden")
    expected_changes = [
        {"baseline": "n", "reason": "Enable native Rust-for-Linux modules.", "resolved": "y", "symbol": "CONFIG_RUST"},
        {"baseline": "y", "reason": "Linux 6.12 CONFIG_RUST has a hard dependency on !MODVERSIONS.", "resolved": "n", "symbol": "CONFIG_MODVERSIONS"},
    ]
    require_exact(delta["changes"], expected_changes, "config delta changes")
    require_exact(delta["fragment_path"], CONFIG_FRAGMENT_PATH.as_posix(), "config fragment path")
    fragment_digest = sha256_bytes(fragment_bytes)
    require_exact(delta["fragment_sha256"], fragment_digest, "config fragment digest")
    fragment = parse_kconfig(fragment_bytes.decode("utf-8"), "config fragment")
    require_exact(fragment, {symbol: resolved for symbol, (_, resolved) in EXPECTED_CONFIG_CHANGES.items()}, "config fragment")

    preserve = policy["preserve"]
    if not isinstance(preserve, list):
        raise PlatformLockError("preserve must be a list")
    require_exact(preserve, EXPECTED_PRESERVE_RECORDS_V2, "preserve records")
    preserve_map: Dict[str, str] = {}
    for index, entry in enumerate(preserve):
        item = exact_keys(entry, {"symbol", "value"}, f"preserve[{index}]")
        symbol = item["symbol"]
        value = item["value"]
        if not isinstance(symbol, str) or not isinstance(value, str) or symbol in preserve_map:
            raise PlatformLockError(f"preserve[{index}] is malformed or duplicate")
        preserve_map[symbol] = value
    require_exact(preserve_map, EXPECTED_PRESERVE_V2, "preserved config symbols")

    require_exact(
        policy["resolution_classification"],
        EXPECTED_RESOLUTION_CLASSIFICATION,
        "resolution classification",
    )
    tool_owner_policy = exact_keys(
        policy["tool_owner_policy"], {"llvm_config"}, "tool owner policy"
    )
    require_exact(
        tool_owner_policy["llvm_config"],
        EXPECTED_LLVM_CONFIG_OWNER_POLICY,
        "llvm-config owner policy",
    )

    dependency = exact_keys(
        policy["dependency_contract"],
        {"init_kconfig_sha256", "kconfig_debug_sha256", "requirements", "rust_is_available_script_sha256"},
        "dependency contract",
    )
    require_exact(dependency["init_kconfig_sha256"], "35cfd4cc4e8850302a072b9d8aef35d827883f6e30f4ff2d428d12eb622fa749", "init Kconfig digest")
    require_exact(dependency["kconfig_debug_sha256"], "5d6e9c71ec42a48908afac2c82a8944340d0b4ebf45e5b1f68bf5eaa70bfb372", "debug Kconfig digest")
    require_exact(dependency["rust_is_available_script_sha256"], "87dac7e23370dd8166e0652dbaadfb89e050a01b5911801fa0a288bde952b9c2", "rust_is_available digest")
    require_exact(
        dependency["requirements"],
        EXPECTED_DEPENDENCY_REQUIREMENTS_V2,
        "dependency requirements",
    )

    module_policy = exact_keys(
        policy["module_version_policy"],
        {"atomic_kernel_module_nvr_required", "config_modversions", "exact_nvr_only", "no_rocky_kabi_claim", "policy", "weak_updates_forbidden"},
        "module version policy",
    )
    for flag in ("atomic_kernel_module_nvr_required", "exact_nvr_only", "no_rocky_kabi_claim", "weak_updates_forbidden"):
        if module_policy[flag] is not True:
            raise PlatformLockError(f"module_version_policy.{flag} must remain true")
    require_exact(module_policy["config_modversions"], "n", "module MODVERSIONS policy")
    require_exact(
        module_policy["policy"],
        EXPECTED_MODULE_POLICY_V2,
        "module version policy text",
    )

    evidence = exact_keys(
        policy["verification_evidence"],
        {
            "build_config",
            "dependency_assertions",
            "olddefconfig_delta",
            "resolution_review",
        },
        "config verification evidence",
    )
    blockers: List[str] = []
    build_config, build_config_verified = validate_evidence_state(
        evidence["build_config"],
        {"blocker", "build_id", "evidence_path", "evidence_sha256", "final_config_sha256", "kernel_nvr", "required", "status"},
        "build_config",
        repo,
        blockers,
    )
    if not build_config_verified:
        require_exact(
            build_config["blocker"],
            EXPECTED_CONFIG_EVIDENCE_BLOCKERS_V2["build_config"],
            "build_config blocker",
        )
        require_null_fields(
            build_config,
            {"build_id", "evidence_path", "evidence_sha256", "final_config_sha256", "kernel_nvr"},
            "build_config",
        )
    else:
        validate_sha256(build_config["final_config_sha256"], "build_config.final_config_sha256")
        if not isinstance(build_config["build_id"], str) or not build_config["build_id"]:
            raise PlatformLockError("verified build config needs a build ID")
        if not isinstance(build_config["kernel_nvr"], str) or not build_config[
            "kernel_nvr"
        ].startswith(EXPECTED_TARGET["kernel_nvr_base"]):
            raise PlatformLockError("verified build config has wrong kernel NVR")
    dependency_assertions, dependency_verified = validate_evidence_state(
        evidence["dependency_assertions"],
        {"blocker", "evidence_path", "evidence_sha256", "preservation_results", "required", "results", "status"},
        "dependency_assertions",
        repo,
        blockers,
    )
    if not dependency_verified:
        require_exact(
            dependency_assertions["blocker"],
            EXPECTED_CONFIG_EVIDENCE_BLOCKERS_V2["dependency_assertions"],
            "dependency_assertions blocker",
        )
        require_null_fields(
            dependency_assertions,
            {"evidence_path", "evidence_sha256", "preservation_results", "results"},
            "dependency_assertions",
        )
    else:
        results = dependency_assertions["results"]
        require_exact(results, EXPECTED_DEPENDENCIES, "dependency assertion results")
        require_exact(
            dependency_assertions["preservation_results"],
            EXPECTED_PRESERVE_V2,
            "config preservation results",
        )
    olddefconfig_delta, olddefconfig_verified = validate_evidence_state(
        evidence["olddefconfig_delta"],
        {"baseline_config_sha256", "baseline_to_control_changes", "blocker", "command_manifest_sha256", "control_config_sha256", "control_to_resolved_changes", "derived_changes", "environment_manifest_sha256", "evidence_path", "evidence_sha256", "generated_symbol_allowlist", "generated_symbol_results", "generated_symbol_rules", "representation_changes", "requested_changes", "requested_generated_symbols", "required", "resolved_config_sha256", "second_control_config_sha256", "second_pass_config_sha256", "status", "unexpected_symbols"},
        "olddefconfig_delta",
        repo,
        blockers,
    )
    require_exact(
        olddefconfig_delta["generated_symbol_allowlist"],
        EXPECTED_GENERATED_CONFIG_SYMBOLS_V2,
        "olddefconfig generated symbol allowlist",
    )
    require_exact(
        olddefconfig_delta["generated_symbol_rules"],
        EXPECTED_GENERATED_SYMBOL_RULES,
        "olddefconfig generated symbol rules",
    )
    if not olddefconfig_verified:
        require_exact(
            olddefconfig_delta["blocker"],
            EXPECTED_CONFIG_EVIDENCE_BLOCKERS_V2["olddefconfig_delta"],
            "olddefconfig_delta blocker",
        )
        require_null_fields(
            olddefconfig_delta,
            {
                "baseline_config_sha256",
                "baseline_to_control_changes",
                "command_manifest_sha256",
                "control_config_sha256",
                "control_to_resolved_changes",
                "derived_changes",
                "environment_manifest_sha256",
                "evidence_path",
                "evidence_sha256",
                "generated_symbol_results",
                "representation_changes",
                "requested_changes",
                "requested_generated_symbols",
                "resolved_config_sha256",
                "second_control_config_sha256",
                "second_pass_config_sha256",
                "unexpected_symbols",
            },
            "olddefconfig_delta",
        )
    else:
        validate_digest_fields(
            olddefconfig_delta,
            {
                "baseline_config_sha256",
                "command_manifest_sha256",
                "control_config_sha256",
                "environment_manifest_sha256",
                "resolved_config_sha256",
                "second_control_config_sha256",
                "second_pass_config_sha256",
            },
            "olddefconfig_delta",
        )
        require_exact(
            olddefconfig_delta["baseline_config_sha256"],
            baseline["sha256"],
            "olddefconfig baseline binding",
        )
        require_exact(
            olddefconfig_delta["control_config_sha256"],
            olddefconfig_delta["second_control_config_sha256"],
            "olddefconfig control idempotence",
        )
        require_exact(
            olddefconfig_delta["resolved_config_sha256"],
            olddefconfig_delta["second_pass_config_sha256"],
            "olddefconfig idempotence",
        )
        require_exact(
            olddefconfig_delta["requested_changes"],
            [
                {"after": "n", "before": "y", "symbol": "CONFIG_MODVERSIONS"},
                {
                    "after": "y",
                    "before": "<absent>",
                    "symbol": "CONFIG_RUST",
                },
            ],
            "olddefconfig requested changes",
        )
        require_exact(
            olddefconfig_delta["derived_changes"],
            [
                {
                    "after": "<absent>",
                    "before": "y",
                    "symbol": "CONFIG_ASM_MODVERSIONS",
                }
            ],
            "olddefconfig derived changes",
        )
        baseline_to_control = validate_classified_changes(
            olddefconfig_delta["baseline_to_control_changes"],
            "baseline-to-control changes",
            require_nonempty=True,
        )
        control_to_resolved = validate_classified_changes(
            olddefconfig_delta["control_to_resolved_changes"],
            "control-to-resolved changes",
            require_nonempty=True,
        )
        requested_generated = validate_classified_changes(
            olddefconfig_delta["requested_generated_symbols"],
            "requested generated symbols",
        )
        representation_changes = validate_presence_changes(
            olddefconfig_delta["representation_changes"],
            "control-to-resolved representation changes",
        )
        generated_names = {row["symbol"] for row in requested_generated}
        if not generated_names.issubset(set(EXPECTED_GENERATED_CONFIG_SYMBOLS_V2)):
            raise PlatformLockError(
                "requested generated symbols exceed the generated-symbol policy"
            )
        classified = validate_classified_changes(
            sorted(
                olddefconfig_delta["requested_changes"]
                + olddefconfig_delta["derived_changes"]
                + requested_generated
                + representation_changes,
                key=lambda item: item["symbol"],
            ),
            "classified control-to-resolved changes",
            require_nonempty=True,
        )
        require_exact(
            control_to_resolved,
            classified,
            "complete control-to-resolved classification",
        )
        if not baseline_to_control:
            raise PlatformLockError("baseline-to-control classification is empty")
        require_exact(olddefconfig_delta["unexpected_symbols"], [], "olddefconfig unexpected symbols")
        require_exact(
            olddefconfig_delta["generated_symbol_results"],
            EXPECTED_GENERATED_CONFIG_VALUES_V2,
            "olddefconfig generated-symbol results",
        )
        require_exact(
            build_config["final_config_sha256"],
            olddefconfig_delta["resolved_config_sha256"],
            "production build config binding",
        )

    resolution_review = validate_missing_record(
        evidence["resolution_review"],
        {
            "artifact_path",
            "artifact_sha256",
            "blocker",
            "command_manifest_sha256",
            "environment_manifest_sha256",
            "required",
            "review_manifest_path",
            "review_manifest_sha256",
            "status",
        },
        "resolution_review",
        blockers,
    )
    require_exact(
        resolution_review["blocker"],
        EXPECTED_CONFIG_EVIDENCE_BLOCKERS_V2["resolution_review"],
        "resolution_review blocker",
    )
    require_null_fields(
        resolution_review,
        {
            "artifact_path",
            "artifact_sha256",
            "command_manifest_sha256",
            "environment_manifest_sha256",
            "review_manifest_path",
            "review_manifest_sha256",
        },
        "resolution_review",
    )

    gate = exact_keys(policy["gate"], {"credit_eligible", "gate_id", "policy"}, "config gate")
    require_exact(gate["gate_id"], "RK-005", "config gate id")
    if gate["credit_eligible"] is not (not blockers):
        raise PlatformLockError("RK-005 credit_eligible contradicts evidence state")
    require_exact(gate["policy"], EXPECTED_GATE_POLICY_V2, "RK-005 gate policy")
    return blockers


def validate_config_policy(
    policy: Dict[str, Any], fragment_bytes: bytes, repo: Optional[Path] = None
) -> List[str]:
    lock_id = policy.get("lock_id") if isinstance(policy, dict) else None
    if lock_id == f"{LOCK_ID_PREFIX}-config-policy-v1":
        return validate_config_policy_v1(policy, fragment_bytes, repo)
    if lock_id == f"{LOCK_ID_PREFIX}-config-policy-v2":
        return validate_config_policy_v2(policy, fragment_bytes, repo)
    raise PlatformLockError("config policy version is unsupported")


def load_locks(
    repo: Path,
    toolchain_path: Path = TOOLCHAIN_LOCK_PATH,
    config_path: Path = CONFIG_POLICY_PATH,
    fragment_path: Path = CONFIG_FRAGMENT_PATH,
) -> Tuple[Dict[str, Any], Dict[str, Any], List[str], List[str]]:
    def locked_input(path: Path, label: str) -> Path:
        if path.is_absolute():
            try:
                relative = path.relative_to(repo)
            except ValueError as exc:
                raise PlatformLockError(f"{label} must be within the repository") from exc
        else:
            relative = path
        relative_text = validate_relative_path(relative.as_posix(), label)
        return repository_file(repo, relative_text, label)

    toolchain_file = locked_input(toolchain_path, "toolchain lock input")
    config_file = locked_input(config_path, "config policy input")
    fragment_file = locked_input(fragment_path, "config fragment input")
    toolchain, _ = read_json(toolchain_file)
    config, _ = read_json(config_file)
    try:
        fragment_bytes = fragment_file.read_bytes()
    except OSError as exc:
        raise PlatformLockError(f"cannot read {fragment_file}: {exc}") from exc
    toolchain_blockers = validate_toolchain_lock(toolchain, repo)
    config_blockers = validate_config_policy(config, fragment_bytes, repo)
    if config.get("lock_id") == f"{LOCK_ID_PREFIX}-config-policy-v2":
        owner_policy = config["tool_owner_policy"]["llvm_config"]
        llvm_artifacts = [
            item
            for item in toolchain["direct_artifacts"]
            if item.get("name") == owner_policy["historical_direct_artifact_name"]
        ]
        if len(llvm_artifacts) != 1:
            raise PlatformLockError("historical LLVM artifact identity is ambiguous")
        require_exact(
            llvm_artifacts[0]["nevra"],
            owner_policy["historical_direct_artifact_nevra"],
            "historical LLVM artifact owner binding",
        )
    if config["gate"]["credit_eligible"] and toolchain_blockers:
        raise PlatformLockError("RK-005 cannot be credit-eligible before RK-003")
    rustavailable = toolchain["rustavailable_evidence"]
    olddefconfig = config["verification_evidence"]["olddefconfig_delta"]
    if rustavailable["status"] == "verified" and olddefconfig["status"] == "verified":
        require_exact(
            rustavailable["config_sha256"],
            olddefconfig["resolved_config_sha256"],
            "rustavailable/config-policy config binding",
        )
    return toolchain, config, toolchain_blockers, config_blockers


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--toolchain-lock", type=Path, default=TOOLCHAIN_LOCK_PATH)
    parser.add_argument("--config-policy", type=Path, default=CONFIG_POLICY_PATH)
    parser.add_argument("--config-fragment", type=Path, default=CONFIG_FRAGMENT_PATH)
    parser.add_argument("--baseline-config", type=Path)
    parser.add_argument("--resolved-config", type=Path)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--check", action="store_true")
    modes.add_argument("--gate-ready", action="store_true")
    return parser.parse_args(argv)


def print_blockers(gate: str, blockers: Sequence[str], stream: Any = sys.stdout) -> None:
    print(f"{gate} NOT READY: {len(blockers)} required evidence item(s) incomplete", file=stream)
    for blocker in blockers:
        print(f"- {blocker}", file=stream)


def main(argv: Sequence[str]) -> int:
    args = parse_args(argv)
    repo = args.repo.resolve()
    try:
        toolchain, config, toolchain_blockers, config_blockers = load_locks(
            repo, args.toolchain_lock, args.config_policy, args.config_fragment
        )
        if (args.baseline_config is None) != (args.resolved_config is None):
            raise PlatformLockError(
                "--baseline-config and --resolved-config must be supplied together"
            )
        if args.baseline_config is not None:
            baseline_bytes = args.baseline_config.read_bytes()
            expected_baseline = config["baseline"]
            if sha256_bytes(baseline_bytes) != expected_baseline["sha256"]:
                raise PlatformLockError(
                    "baseline config bytes do not match the locked Rocky config"
                )
            baseline = parse_kconfig(
                baseline_bytes.decode("utf-8"), "baseline config"
            )
            if len(baseline) != expected_baseline["symbol_count"]:
                raise PlatformLockError("baseline config symbol count changed")
            resolved = parse_kconfig(
                args.resolved_config.read_text(encoding="utf-8"), "resolved config"
            )
            validate_resolved_config(baseline, resolved, config)
            print("resolved config delta is exactly allowlisted and preserved")
        if args.check:
            print(
                "Rocky kernel platform locks verified: "
                f"{toolchain['lock_id']} and {config['lock_id']}"
            )
            if toolchain_blockers:
                print_blockers("RK-003", toolchain_blockers)
            if config_blockers:
                print_blockers("RK-005", config_blockers)
            return 0
        blockers = [*toolchain_blockers, *config_blockers]
        if blockers:
            print_blockers("RK-003/RK-005", blockers, sys.stderr)
            return 1
        print("RK-003/RK-005 READY: all required evidence verified")
        return 0
    except (OSError, UnicodeError, PlatformLockError) as exc:
        print(f"Rocky kernel platform-lock error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
