#!/usr/bin/env python3
"""Independently verify the exact RK-005 v2 configuration artifact.

This review is deliberately bounded and credit-forbidden.  ``--check`` binds
the historical run inputs to Git objects and requires a descendant-or-equal
current repository to retain the same HEAD/index/worktree bytes.
``--verify-artifact`` additionally reopens the exact ZIP, validates its closed
schema, and independently recomputes every configuration delta.  Neither mode
can award a gate, tracker, durable-archive, offline, or production claim.
"""

from __future__ import print_function

import argparse
import hashlib
import io
import json
import os
import re
import stat
import subprocess
import sys
import zipfile
from pathlib import Path, PurePosixPath


REVIEW_DIRECTORY = Path("host-kernel/rocky/evidence")
REVIEW_GLOB = "config-resolution-review-*-v2.json"
SCHEMA_VERSION = 2
HEX_SHA1 = re.compile(r"^[0-9a-f]{40}$")
HEX_SHA256 = re.compile(r"^[0-9a-f]{64}$")
CONFIG_VALUE = re.compile(r"^(CONFIG_[A-Za-z0-9_]+)=(.*)$")
CONFIG_UNSET = re.compile(r"^# (CONFIG_[A-Za-z0-9_]+) is not set$")
CONFIG_ASSIGNMENT_VALUE = re.compile(
    r'^(?:y|m|n|-?[0-9]+|0[xX][0-9A-Fa-f]+|"(?:[^"\\\r\n]|\\.)*")$'
)
SHA256SUM = re.compile(r"^([0-9a-f]{64})  ([A-Za-z0-9][A-Za-z0-9_.-]*)$")
TEMP_SOURCE = re.compile(
    r"^(/tmp/rk005-config-[A-Za-z0-9_-]+)/pass-([12])/"
    r"linux-6\.12\.0-211\.44\.1\.el10_2$"
)
CONTAINER_IMAGE = (
    "rockylinux/rockylinux:10.2@"
    "sha256:e372170ca8630f0f03e9b70fdd0bf4a3ce3426b0de7cdba615f06337389de176"
)
EMPTY_SHA256 = hashlib.sha256(b"").hexdigest()
REVIEW_ID = "rk-005-config-resolution-review-bebf5e08-v2"
REVIEW_SHA256 = "3c417d1ed1b30c7b454d3b55c9ffaf83f2733a28973402c0768107404fa67169"
RUNTIME_HEAD_SHA = "bebf5e081a6c70682d31a06f3719645100a958d0"
RUNTIME_TREE_SHA = "af9b5d69714c6fbfcfe396a39f15cf869ddd5192"
GITHUB_REPOSITORY = "phoenix-hacking/mckernel"
GITHUB_RUN_ID = 32099217603
GITHUB_RUN_ATTEMPT = 1
GITHUB_JOB_ID = 95596363515
ARTIFACT_ID = 9311079167
ARTIFACT_NAME = "rk005-config-resolution-v2-32099217603-1"
ARTIFACT_SIZE = 1718245
ARTIFACT_SHA256 = "4fd479ed3cacc7d7ecbb4d159d63bba588fc782d31c853b8790ad40b195458cb"
ARTIFACT_EXPIRES_AT = "2026-09-17T04:33:07Z"
BASELINE_CONFIG_SHA256 = (
    "5bbdda60ce822ec903c85d3d8ddda1bfc9493216bed86c6c432683aa50dcf50d"
)
CONTROL_CONFIG_SHA256 = (
    "dd7d3cc37c37b94e6a479d172bbaaeb17a6e863f4fa13fa1f5fe19c3548393e4"
)
FRAGMENT_CONFIG_SHA256 = (
    "25dd0fc5647d8addfd650469aad758ca41d7e9599f0d02e34c2025e438114983"
)
RESOLVED_CONFIG_SHA256 = (
    "fc8c835cdd67d50bf71353d956b0c9932ea83a2553a79a951e9254cf72505b7a"
)
CAPTURE_LOG = (
    b"captured deterministic config evidence; RK-005 credit remains forbidden\n"
)

EXPECTED_GATE_CLAIMS = {
    "RK-002": False,
    "RK-003": False,
    "RK-004": False,
    "RK-005": False,
    "RK-006": False,
    "RS-001": False,
}
EXPECTED_CLAIMS = {
    "credit_eligible": False,
    "durable_archive": False,
    "gate_claims": EXPECTED_GATE_CLAIMS,
    "network_isolation_claimed": False,
    "offline_replay_proven": False,
    "production_build_config_bound": False,
    "production_build_proven": False,
    "runtime_identity_claimed": False,
    "tracker_credit": False,
}
EXPECTED_CAVEATS = {
    "archive_bytes_committed": False,
    "artifact_retention_is_durable": False,
    "checkpoint_excludes_self_but_sha256sums_covers_it": True,
    "container_claim_boundary": (
        "The digest-pinned workflow and GitHub job bind the Rocky 10.2 image; "
        "the artifact does not contain a separate in-container OCI manifest attestation."
    ),
    "independent_offline_replay_performed": False,
    "raw_rustavailable_streams_archived": False,
    "top_level_diagnostics_bound_by_zip_sha256": True,
    "top_level_diagnostics_in_internal_manifests": False,
}
EXPECTED_REMAINING_PREREQUISITES = [
    (
        "The RK-003 closure/offline artifact and its exact tool probes still "
        "require independent review and durable archival before RK-005 may "
        "inherit that authority."
    ),
    (
        "Compatibility patches 0006 through 0023 change source/build "
        "compatibility without adding configuration symbols; this phase binds "
        "and applies them but cannot substitute config resolution for their "
        "separate exact compile probes."
    ),
    (
        "A successful config-resolution artifact still requires independent "
        "review and durable archival before any authority lock may be updated."
    ),
    (
        "Both requested resolutions run make LLVM=1 rustavailable against their "
        "final external-build .config, but these hosted config-only invocations "
        "do not prove the offline RK-003 replay, a production compilation, or "
        "RK-005 credit."
    ),
    (
        "A production kernel build has not yet proved that its final .config "
        "byte-matches both independent resolutions."
    ),
    (
        "RK-002, RK-003, RK-004, RK-005, RK-006, RS-001, and tracker credit "
        "remain false."
    ),
]

EXPECTED_INPUTS = [
    {
        "git_blob_sha1": "29eaf29a92880571a5497a3e3f0a3191fe348a9a",
        "path": ".github/workflows/rocky-kernel-config-resolution-v2.yml",
        "sha256": "9ef8d2df9f7f5059c92fb029470b0c5e48991d6221e93d8d7bba307cb1af5e9d",
        "size": 6247,
    },
    {
        "git_blob_sha1": "cdd03ce789a94617250a6627a3b7315b0ca33efc",
        "path": "host-kernel/rocky/config-policy-v2.json",
        "sha256": "9c746399387c7f32148a6a8e8814a19c629f4b905629a1b941c60d99ef3d64b7",
        "size": 10707,
    },
    {
        "git_blob_sha1": "de815156d011d5620b886894a0eaa16dbe2af9ce",
        "path": "host-kernel/rocky/configs/rust-minimal.config",
        "sha256": FRAGMENT_CONFIG_SHA256,
        "size": 46,
    },
    {
        "git_blob_sha1": "92bebb1c9ac686b3a0010c7e3b54b95d9acff14a",
        "path": "host-kernel/rocky/evidence/config-resolution-contract-v2.json",
        "sha256": "c576eea855ed794dcc1dc8f4890d34cfec15022d757d984ce3a1613740ebeefa",
        "size": 23034,
    },
    {
        "git_blob_sha1": "565ec633351b9a12400d504e71c26432dae3173a",
        "path": "host-kernel/rocky/patches/series.json",
        "sha256": "6a1a5e8fb13b6ce6ed35bd8e5487bb67ecf92d2be927799b660f21b5631f68fb",
        "size": 1454,
    },
    {
        "git_blob_sha1": "ca623cfadf7540ecd8c6cff0da763bf63fb710c5",
        "path": "host-kernel/rocky/source-lock.json",
        "sha256": "707ee40466ac0bb0cd0600383bba0b13fc1146e7080034786bf5668a95b27682",
        "size": 18236,
    },
    {
        "git_blob_sha1": "5584b199126e38852f1b80a47e0f93d627d4a6df",
        "path": "host-kernel/rocky/toolchain-lock.json",
        "sha256": "fd3d7a13e1b8b5d103f7e59d22f17c9e4b99cc937637decaa66749acfae6c802",
        "size": 28867,
    },
    {
        "git_blob_sha1": "9fb7784ba97e95c66eeb54f84716571f5aeb9286",
        "path": "scripts/rocky_kernel_config_resolution_v2.py",
        "sha256": "4698526d0c36e38bd5a8258398831e48783d3d280d512253d70703e0a39cfb24",
        "size": 92853,
    },
    {
        "git_blob_sha1": "b61f9ab98225bf05c389304449539259004e4164",
        "path": "scripts/rocky_kernel_platform_lock_v2.py",
        "sha256": "89d35ba1c46ab77db7425b2b4af279af1fffdf4e79657f2a6c318ca4db7f680b",
        "size": 98152,
    },
    {
        "git_blob_sha1": "8beca780433aab9566fb5b262624be495abcbfed",
        "path": "scripts/rocky_kernel_source_lock.py",
        "sha256": "1fc6f6457d5a06d43260b84a8627fa2297c360d3a5c3810012a2198aadf3c262",
        "size": 60008,
    },
]

EXPECTED_PATCHES = [
    {"path": "host-kernel/rocky/patches/0001-x86-rust-set-rustc-abi-x86-softfloat.patch", "sha256": "85069fa5d4e1de8a0d0172480604c74deba0caeafd34268a6735d069599e5113"},
    {"path": "host-kernel/rocky/patches/0002-rust-support-rust-1.91-target-spec.patch", "sha256": "c52bde4ace32fbd908b6c5ed5e4ac1881effd6e9ebd5813e7e083d74a5f34997"},
    {"path": "host-kernel/rocky/patches/0003-kbuild-rust-add-rustc-min-version.patch", "sha256": "4af4b725292a080a9bf69f37308cb4099e957674001f0fc83239f4be29f07ec1"},
    {"path": "host-kernel/rocky/patches/0004-rust-compile-libcore-edition-2024.patch", "sha256": "3ef23cf99a4523a6045a29b70f49ba0080242d7b219db7f0bca58b4f7d73fbb7"},
    {"path": "host-kernel/rocky/patches/0005-rust-clean-unnecessary-transmutes-lint.patch", "sha256": "0ba29993d78fea5db3c0ff8dbf41bf8a6c08b00d9803fc85da7805e698ac8c33"},
    {"path": "host-kernel/rocky/patches/0006-rust-init-allow-dead-code-rust-1.89.patch", "sha256": "315ec61d17c5d3cc97c6123f30bcffa08befcc00c487efaa5e6eda38333d29c5"},
    {"path": "host-kernel/rocky/patches/0007-rust-use-used-compiler-rust-1.89.patch", "sha256": "d9a58b1123e5f5522efb7ad7b7837c406b955c1a1c4a7a38f0d2faa4dd4285fc"},
    {"path": "host-kernel/rocky/patches/0008-rust-enable-arbitrary-self-types-rust-1.92.patch", "sha256": "ab3f6adaed3fcb65669ffc0baccdb3d7a9b7e3df9d0c5889228c775585daacaa"},
    {"path": "host-kernel/rocky/patches/0009-rust-block-drop-removed-merge-flag.patch", "sha256": "076b0b48effba9bed12cb00a4c93318353aa26344f14b0b1bba5508c55a1bcfb"},
    {"path": "host-kernel/rocky/patches/0010-kbuild-disable-default-const-init-unsafe.patch", "sha256": "2781f4eac05a806a58e76a035f2dba45f137a9147512c87cf9f63b1deb40c7e0"},
    {"path": "host-kernel/rocky/patches/0011-mm-ksm-fix-clang-21-uninitialized.patch", "sha256": "2104f602c62bbda355089fb0210647b39d511e77bbdb9857e5c092c004f490a1"},
    {"path": "host-kernel/rocky/patches/0012-netfs-mark-nonstring-lookup-tables.patch", "sha256": "3aeb8de2d5eee43f56268475b8911e6e14eef59e3b8007b4719b8c4ef0a1b691"},
    {"path": "host-kernel/rocky/patches/0013-lib-crypto-mark-binary-vectors-nonstring.patch", "sha256": "329e86bdadf721f366b58582bf893df451a25e1f5cb91715bb789e10c242f021"},
    {"path": "host-kernel/rocky/patches/0014-gcc-15-mark-byte-arrays-nonstring.patch", "sha256": "e98032b0d88ea5dbaffdbdf39a16423fded48dbed41adec29cc232782ba6d24b"},
    {"path": "host-kernel/rocky/patches/0015-gcc-15-demote-unterminated-string-warning.patch", "sha256": "b07d58736bfe7e9ef5f9c3c4ce2807514f2cd01ab1146620fc09eb4f98ac8f29"},
    {"path": "host-kernel/rocky/patches/0016-gcc-15-disable-unterminated-string-warning.patch", "sha256": "ea3a2c85b9dc1c15d3307c3958512b812d56297930d58fc6912adfb2ea3e7284"},
    {"path": "host-kernel/rocky/patches/0017-kbuild-use-cc-disable-warning.patch", "sha256": "890a11c4540d4c003773482c47858a946156e4cf0d2e04d3a9ed8e1a9382fd4b"},
    {"path": "host-kernel/rocky/patches/0018-kbuild-order-unterminated-string-disable.patch", "sha256": "e271fa6f30bb3b39a24ae2f926dfa067577997ecf2076e412b5575a4d785021e"},
    {"path": "host-kernel/rocky/patches/0019-rust-types-add-opaque-try-ffi-init.patch", "sha256": "bc9b84c4c8bf36b7fac02dd3d04e1a170b86ee143b76739a6eed3e564cdebc2b"},
    {"path": "host-kernel/rocky/patches/0020-rust-miscdevice-add-base-abstraction.patch", "sha256": "d377b5bd91d507e383b8673beac42381b9b6c37a47bba7955c768a8f6ddaad25"},
    {"path": "host-kernel/rocky/patches/0021-objtool-recognize-rust-1.92-panic-const.patch", "sha256": "6eb8dd4789a5b01a3f8e00ea45dab9debb7d23bb7a8c4af5b2cfdc181656633a"},
    {"path": "host-kernel/rocky/patches/0022-x86-pvh-annotate-noendbr.patch", "sha256": "2f07f4030312ce1df38ed78615c94bfb99c7e084d27611de96d38bcf47237e48"},
    {"path": "host-kernel/rocky/patches/0023-rust-update-no-alloc-shim-marker-rust-1.92.patch", "sha256": "aeb6af53a40049a009c9973d910e4c8a6286075b88512db051778e5a4595a77b"},
]

EXPECTED_ARCHIVE_PATHS = (
    "capture.exit-code",
    "capture.log",
    "capture/SHA256SUMS",
    "capture/baseline.config",
    "capture/blockers.json",
    "capture/checkpoint.json",
    "capture/commands.json",
    "capture/config-delta.json",
    "capture/control-pass-1.config",
    "capture/control-pass-2.config",
    "capture/dependency-assertions.json",
    "capture/environment.json",
    "capture/fragment.config",
    "capture/resolved-pass-1.config",
    "capture/resolved-pass-2.config",
    "workflow-state",
)
EXPECTED_CHECKSUM_NAMES = (
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
)
EXPECTED_CHECKSUM_DIGESTS = {
    "baseline.config": BASELINE_CONFIG_SHA256,
    "fragment.config": FRAGMENT_CONFIG_SHA256,
    "control-pass-1.config": CONTROL_CONFIG_SHA256,
    "control-pass-2.config": CONTROL_CONFIG_SHA256,
    "resolved-pass-1.config": RESOLVED_CONFIG_SHA256,
    "resolved-pass-2.config": RESOLVED_CONFIG_SHA256,
    "commands.json": "3fd5910f46d4c681aa7c0f59676a62f243be4cfd640c21d773a9d554be662775",
    "environment.json": "6f4c66b5f09f7236504a1044716997ab3e40b310b3db8c66932a246cee9a8a6f",
    "config-delta.json": "2e941435bc403293adb3d37dc0b1e775079e6a115cf664949f338f208e7e17e6",
    "dependency-assertions.json": "537acfbaf702ca42738641890061823fcbf7c41abca756c5e91331e92e49f8a2",
    "blockers.json": "3d515a1700a9cfc25532c3780aecfb1992fcb719d2faeaa44a6ad7c4c5329f02",
    "checkpoint.json": "8f8400043c13f627004de9de523f783f74603b82c793424aa4e6351e373c3baa",
}

EXPECTED_REQUESTED_CHANGES = [
    {"after": "n", "before": "y", "symbol": "CONFIG_MODVERSIONS"},
    {"after": "y", "before": "<absent>", "symbol": "CONFIG_RUST"},
]
EXPECTED_DERIVED_CHANGES = [
    {"after": "<absent>", "before": "y", "symbol": "CONFIG_ASM_MODVERSIONS"}
]
EXPECTED_REQUESTED_GENERATED_CHANGES = [
    {
        "after": '"bindgen 0.72.1"',
        "before": "<absent>",
        "symbol": "CONFIG_BINDGEN_VERSION_TEXT",
    },
    {
        "after": (
            '"rustc 1.92.0 (ded5c06cf 2025-12-08) '
            '(Red Hat 1.92.0-1.el10)"'
        ),
        "before": "<absent>",
        "symbol": "CONFIG_RUSTC_VERSION_TEXT",
    },
]
EXPECTED_REPRESENTATION_CHANGES = [
    {"after": "n", "before": "<absent>", "symbol": "CONFIG_BLK_DEV_RUST_NULL"},
    {"after": "n", "before": "<absent>", "symbol": "CONFIG_DRM_NOVA"},
    {"after": "n", "before": "<absent>", "symbol": "CONFIG_RUST_BUILD_ASSERT_ALLOW"},
    {"after": "n", "before": "<absent>", "symbol": "CONFIG_RUST_DEBUG_ASSERTIONS"},
    {"after": "n", "before": "<absent>", "symbol": "CONFIG_RUST_FW_LOADER_ABSTRACTIONS"},
    {"after": "n", "before": "<absent>", "symbol": "CONFIG_RUST_OVERFLOW_CHECKS"},
    {"after": "n", "before": "<absent>", "symbol": "CONFIG_RUST_PHYLIB_ABSTRACTIONS"},
    {"after": "n", "before": "<absent>", "symbol": "CONFIG_SAMPLES_RUST"},
]
EXPECTED_GENERATED_SYMBOL_RESULTS = {
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
EXPECTED_DEPENDENCIES = {
    "CONFIG_CALL_PADDING": "y",
    "CONFIG_CFI_CLANG": "n",
    "CONFIG_GCC_PLUGIN_RANDSTRUCT": "n",
    "CONFIG_HAVE_RUST": "y",
    "CONFIG_KASAN": "n",
    "CONFIG_KASAN_SW_TAGS": "n",
    "CONFIG_MITIGATION_RETHUNK": "y",
    "CONFIG_MODVERSIONS": "n",
    "CONFIG_PAHOLE_HAS_LANG_EXCLUDE": "y",
    "CONFIG_RANDSTRUCT": "n",
    "CONFIG_RUST_IS_AVAILABLE": "y",
}
EXPECTED_PRESERVATION = {
    "btf_debug": {
        "CONFIG_BPF_SYSCALL": "y",
        "CONFIG_DEBUG_INFO": "y",
        "CONFIG_DEBUG_INFO_BTF": "y",
        "CONFIG_DEBUG_INFO_BTF_MODULES": "y",
        "CONFIG_DEBUG_INFO_DWARF_TOOLCHAIN_DEFAULT": "y",
        "CONFIG_DEBUG_INFO_REDUCED": "n",
        "CONFIG_DEBUG_INFO_SPLIT": "n",
    },
    "module_signing": {
        "CONFIG_CRYPTO_RSA": "y",
        "CONFIG_CRYPTO_SHA512": "y",
        "CONFIG_MODULES": "y",
        "CONFIG_MODULE_ALLOW_BTF_MISMATCH": "n",
        "CONFIG_MODULE_SIG": "y",
        "CONFIG_MODULE_SIG_ALL": "y",
        "CONFIG_MODULE_SIG_FORCE": "n",
        "CONFIG_MODULE_SIG_KEY": '"certs/signing_key.pem"',
        "CONFIG_MODULE_SIG_KEY_TYPE_RSA": "y",
        "CONFIG_MODULE_SIG_SHA512": "y",
    },
    "warning_policy": {"CONFIG_WERROR": "y"},
}
EXPECTED_FIXED_ENVIRONMENT = {
    "ARCH": "x86_64",
    "HOME": "/root",
    "LANG": "C",
    "LC_ALL": "C",
    "PATH": "/usr/sbin:/usr/bin:/sbin:/bin",
    "TZ": "UTC",
}
EXPECTED_ENVIRONMENT_DERIVED = {
    "bindgen_version_text": "bindgen 0.72.1",
    "pahole_version": 131,
    "rustc_llvm_version": 210106,
    "rustc_version": 109200,
    "rustc_version_text": (
        "rustc 1.92.0 (ded5c06cf 2025-12-08) (Red Hat 1.92.0-1.el10)"
    ),
}
EXPECTED_TOOL_PROBES = {
    "bindgen": {"path": "/usr/bin/bindgen", "owner": "bindgen-cli-0:0.72.1-1.el10.x86_64", "sha256": "55880234cb76e4fd13f7401308c61db687301624be48adfd23c3c2cd0797b37c", "stdout_sha256": "c68f981ca03a0733ae2e550a898e2f08d334fd8ece4e9e3b99ea6fa3b8ba21c4", "command": ["bindgen", "--version", "workaround-for-0.69.0"]},
    "clang": {"path": "/usr/bin/clang", "owner": "clang-0:21.1.8-1.el10.x86_64", "sha256": "48271e3fbb759560a54e6f0a13e05a4a0b768eea2ffd6aa2f1e14b8cbb76fb7f", "stdout_sha256": "082de0cf4ec79ce11472d754e6f9508fdc811c2d5c585e90fedcb0ef985b037a", "command": ["clang", "--version"]},
    "lld": {"path": "/usr/bin/ld.lld", "owner": "lld-0:21.1.8-1.el10.x86_64", "sha256": "52029c7d731c74ab72a2eca8126d578547242b3192ba74e27c94c1b51be001f9", "stdout_sha256": "418d72df86baf70c88b9a96a9118e3cdc66be0537a58f66a6879df0479f9a78f", "command": ["ld.lld", "--version"]},
    "llvm": {"path": "/usr/bin/llvm-config", "owner": "llvm-devel-0:21.1.8-1.el10.x86_64", "sha256": "bdf82677530a0997abccadea0d9ce6aa3146d5d542ded5b589a095e4121b3cf0", "stdout_sha256": "2aa7a88c6265f7d12bbbda0d91c617c37977ebba04971007a6ba09f16130f58c", "command": ["llvm-config", "--version"]},
    "pahole": {"path": "/usr/bin/pahole", "owner": "dwarves-0:1.31-1.el10.x86_64", "sha256": "099aa2c9d0f4d22cad3cf65a1dab89bfc11b500f568497a276eec0052b65398b", "stdout_sha256": "d68d5c09201c3f36d4d324c921c79161351a8ea4dc6e25b4d161ff40bae293e2", "command": ["pahole", "--version"]},
    "rustc": {"path": "/usr/bin/rustc", "owner": "rust-0:1.92.0-1.el10.x86_64", "sha256": "38eeb1652fb59753cb7736e354ec1579a543da9a2eb8a68be102a41e88eb5dc6", "stdout_sha256": "a8dc7b68607a44774c48c2a1fab52da313610a1573a160e87c480d386fdedc64", "command": ["rustc", "--version", "--verbose"]},
    "rust_src_core": {"path": "/usr/lib/rustlib/src/rust/library/core/src/lib.rs", "owner": "rust-src-0:1.92.0-1.el10.noarch", "sha256": "38ed9003ea2427f8803317e3e040d69f988d88534468bb28cbf83f27e2b51080", "stdout_sha256": "c1b4ac7ed462cd01c076c33de7d01ddef7f39a4bed73b12b2d769babf57204e9", "command": ["rustc", "--print", "sysroot"]},
}
EXPECTED_RUSTAVAILABLE_STDOUT = (
    "3c1cd8d9e7458db439572d9172e6a6060bd22246f3be9ad1e3b5f7ee7c4f5160",
    "277443f995d6e0d2b61f9ea90fb0ffd3de7b51e788698d18290c476bed2a2562",
)


class ConfigReviewV2Error(RuntimeError):
    """Raised for malformed, retargeted, or overclaiming review evidence."""


def reject_duplicate_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ConfigReviewV2Error("duplicate JSON key: {!r}".format(key))
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
        raise ConfigReviewV2Error("value is not canonical JSON: {}".format(exc))
    return (text + "\n").encode("ascii")


def read_json_bytes(data, label, require_canonical=False):
    try:
        text = data.decode("ascii")
        value = json.loads(text, object_pairs_hook=reject_duplicate_pairs)
    except (UnicodeError, ValueError) as exc:
        raise ConfigReviewV2Error("{} is not valid JSON: {}".format(label, exc))
    if not isinstance(value, dict):
        raise ConfigReviewV2Error("{} must be a JSON object".format(label))
    if require_canonical and data != canonical_json_bytes(value):
        raise ConfigReviewV2Error("{} is not canonical JSON".format(label))
    return value


def exact_keys(value, expected, label):
    if not isinstance(value, dict) or set(value) != set(expected):
        raise ConfigReviewV2Error("{} has unexpected keys".format(label))
    return value


def same_value_and_type(actual, expected):
    if type(actual) is not type(expected):
        return False
    if isinstance(expected, dict):
        return set(actual) == set(expected) and all(
            same_value_and_type(actual[key], expected[key]) for key in expected
        )
    if isinstance(expected, (list, tuple)):
        return len(actual) == len(expected) and all(
            same_value_and_type(left, right)
            for left, right in zip(actual, expected)
        )
    return actual == expected


def require_exact(actual, expected, label):
    if not same_value_and_type(actual, expected):
        raise ConfigReviewV2Error(
            "{} differs: {!r} != {!r}".format(label, actual, expected)
        )


def require_positive_int(value, label):
    if type(value) is not int or value < 1:
        raise ConfigReviewV2Error("{} is not a positive integer".format(label))
    return value


def require_nonnegative_int(value, label):
    if type(value) is not int or value < 0:
        raise ConfigReviewV2Error("{} is not a nonnegative integer".format(label))
    return value


def validate_sha256(value, label):
    if not isinstance(value, str) or HEX_SHA256.fullmatch(value) is None:
        raise ConfigReviewV2Error("{} is not a SHA-256".format(label))


def safe_relative_path(value, label):
    if not isinstance(value, str):
        raise ConfigReviewV2Error("{} is not text".format(label))
    path = PurePosixPath(value)
    if (
        path.is_absolute()
        or not path.parts
        or "\\" in value
        or "\x00" in value
        or "//" in value
        or any(part in ("", ".", "..") for part in value.split("/"))
    ):
        raise ConfigReviewV2Error("{} is unsafe: {!r}".format(label, value))
    return value


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def regular_file(path, label):
    raw = str(path)
    if raw == "" or "\x00" in raw:
        raise ConfigReviewV2Error("{} path is unsafe".format(label))
    components = raw.split(os.sep)
    if os.path.isabs(raw):
        components = components[1:]
    if not components or any(part in ("", ".", "..") for part in components):
        raise ConfigReviewV2Error("{} path is unsafe".format(label))
    requested = Path(os.path.abspath(raw))
    current = Path(requested.anchor)
    parts = requested.parts[1:] if requested.anchor else requested.parts
    try:
        status = current.lstat()
    except OSError as exc:
        raise ConfigReviewV2Error("cannot inspect {}: {}".format(label, exc))
    for index, part in enumerate(parts):
        current = current / part
        try:
            status = current.lstat()
        except OSError as exc:
            raise ConfigReviewV2Error("cannot inspect {}: {}".format(label, exc))
        if stat.S_ISLNK(status.st_mode):
            raise ConfigReviewV2Error("{} traverses a symlink".format(label))
        if index + 1 < len(parts) and not stat.S_ISDIR(status.st_mode):
            raise ConfigReviewV2Error("{} has a non-directory ancestor".format(label))
    if not stat.S_ISREG(status.st_mode):
        raise ConfigReviewV2Error("{} is not a regular file".format(label))
    return requested


def within(root, candidate):
    try:
        common = os.path.commonpath((str(root), str(candidate)))
    except ValueError:
        return False
    return Path(common) == root


def repository_file(repo, relative, label):
    relative = safe_relative_path(relative, label + " path")
    root = repo.resolve()
    requested = root.joinpath(*PurePosixPath(relative).parts)
    try:
        resolved = requested.resolve()
    except OSError as exc:
        raise ConfigReviewV2Error("cannot resolve {}: {}".format(label, exc))
    if not within(root, resolved):
        raise ConfigReviewV2Error("{} escapes the repository".format(label))
    if requested != resolved:
        raise ConfigReviewV2Error("{} traverses a symlink".format(label))
    return regular_file(requested, label)


def run_git(repo, arguments, allow_failure=False):
    try:
        completed = subprocess.run(
            ["git", "-C", str(repo)] + list(arguments),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except OSError as exc:
        raise ConfigReviewV2Error("git failed to execute: {}".format(exc))
    if completed.returncode != 0 and not allow_failure:
        raise ConfigReviewV2Error(
            "git command failed: {}".format(
                completed.stderr.decode("utf-8", errors="replace").strip()
            )
        )
    return completed


def git_tree_record(repo, revision, path, label):
    completed = run_git(repo, ["ls-tree", revision, "--", path])
    rows = completed.stdout.decode("ascii").splitlines()
    if len(rows) != 1:
        raise ConfigReviewV2Error("{} has no unique tree entry".format(label))
    match = re.fullmatch(r"(100644) blob ([0-9a-f]{40})\t(.+)", rows[0])
    if match is None or match.group(3) != path:
        raise ConfigReviewV2Error("{} tree entry is malformed".format(label))
    return match.group(2)


def git_blob_bytes(repo, blob, label):
    completed = run_git(repo, ["cat-file", "blob", blob])
    if not completed.stdout:
        raise ConfigReviewV2Error("{} is unexpectedly empty".format(label))
    return completed.stdout


def validate_input_row(repo, runtime_head, row, current_head, label):
    exact_keys(row, {"git_blob_sha1", "path", "sha256", "size"}, label)
    path = safe_relative_path(row["path"], label + " path")
    validate_sha256(row["sha256"], label + " digest")
    require_positive_int(row["size"], label + " size")
    if not isinstance(row["git_blob_sha1"], str) or HEX_SHA1.fullmatch(
        row["git_blob_sha1"]
    ) is None:
        raise ConfigReviewV2Error("{} has an invalid Git blob".format(label))
    runtime_blob = git_tree_record(repo, runtime_head, path, label + " runtime")
    require_exact(runtime_blob, row["git_blob_sha1"], label + " runtime blob")
    runtime_data = git_blob_bytes(repo, runtime_blob, label + " runtime blob")
    require_exact(len(runtime_data), row["size"], label + " runtime size")
    require_exact(sha256_bytes(runtime_data), row["sha256"], label + " runtime digest")
    current_blob = git_tree_record(repo, current_head, path, label + " current HEAD")
    require_exact(current_blob, runtime_blob, label + " current HEAD blob")
    index = run_git(repo, ["ls-files", "--stage", "--", path])
    rows = index.stdout.decode("ascii").splitlines()
    if len(rows) != 1:
        raise ConfigReviewV2Error("{} has no unique index entry".format(label))
    match = re.fullmatch(r"100644 ([0-9a-f]{40}) 0\t(.+)", rows[0])
    if match is None or match.group(2) != path:
        raise ConfigReviewV2Error("{} index entry is malformed".format(label))
    require_exact(match.group(1), runtime_blob, label + " index blob")
    data = repository_file(repo, path, label + " worktree").read_bytes()
    require_exact(len(data), row["size"], label + " worktree size")
    require_exact(sha256_bytes(data), row["sha256"], label + " worktree digest")


def discover_review(repo, explicit=None):
    repo = repo.resolve()
    if explicit is not None:
        path = explicit if explicit.is_absolute() else repo / explicit
        try:
            relative = path.relative_to(repo).as_posix()
        except ValueError:
            raise ConfigReviewV2Error(
                "explicit review manifest is outside the repository"
            )
        return repository_file(repo, relative, "review manifest")
    candidates = sorted((repo / REVIEW_DIRECTORY).glob(REVIEW_GLOB))
    if len(candidates) != 1:
        raise ConfigReviewV2Error(
            "expected exactly one {} manifest, found {}".format(
                REVIEW_GLOB, len(candidates)
            )
        )
    try:
        relative = candidates[0].relative_to(repo).as_posix()
    except ValueError:
        raise ConfigReviewV2Error("review manifest is outside the repository")
    return repository_file(repo, relative, "review manifest")


def load_review(path):
    data = path.read_bytes()
    require_exact(sha256_bytes(data), REVIEW_SHA256, "review manifest digest")
    return read_json_bytes(data, "review manifest", require_canonical=True)


def validate_config_fact(record, expected, label, pair=False):
    keys = {"byte_identical", "line_count", "paths", "sha256", "size", "symbol_count"} if pair else {"line_count", "path", "sha256", "size", "symbol_count"}
    exact_keys(record, keys, label)
    require_exact(record, expected, label)


def validate_review_object(review):
    exact_keys(
        review,
        {
            "caveats",
            "claims",
            "current_repository_input_policy",
            "remaining_prerequisites",
            "review_id",
            "review_kind",
            "runtime_candidate",
            "schema_version",
            "source_artifact",
            "verified_facts",
            "zip_closure",
        },
        "review",
    )
    require_exact(review["schema_version"], SCHEMA_VERSION, "review schema")
    require_exact(review["review_id"], REVIEW_ID, "review id")
    require_exact(
        review["review_kind"],
        "historical-exact-config-resolution-v2-bounded-pass",
        "review kind",
    )
    exact_keys(review["claims"], set(EXPECTED_CLAIMS), "claims")
    require_exact(review["claims"], EXPECTED_CLAIMS, "claims")
    exact_keys(review["caveats"], set(EXPECTED_CAVEATS), "caveats")
    require_exact(review["caveats"], EXPECTED_CAVEATS, "caveats")
    require_exact(
        review["remaining_prerequisites"],
        EXPECTED_REMAINING_PREREQUISITES,
        "remaining prerequisites",
    )

    policy = exact_keys(
        review["current_repository_input_policy"],
        {
            "bound_input_count",
            "relationship",
            "require_head_index_worktree_equality",
            "runtime_identity_claimed",
        },
        "current input policy",
    )
    require_exact(policy["bound_input_count"], 33, "bound input count")
    require_exact(policy["relationship"], "descendant-or-equal", "relationship")
    require_exact(
        policy["require_head_index_worktree_equality"], True, "input equality"
    )
    require_exact(policy["runtime_identity_claimed"], False, "runtime claim")

    source = exact_keys(
        review["source_artifact"],
        {"artifact", "durable_archive", "expires_at", "github", "retention_days"},
        "source artifact",
    )
    require_exact(source["durable_archive"], False, "durable archive claim")
    require_exact(source["retention_days"], 30, "artifact retention")
    require_exact(source["expires_at"], ARTIFACT_EXPIRES_AT, "artifact expiry")
    artifact = exact_keys(
        source["artifact"],
        {"archive_file_name", "id", "name", "sha256", "size"},
        "artifact",
    )
    require_exact(artifact["archive_file_name"], ARTIFACT_NAME + ".zip", "archive name")
    require_exact(artifact["id"], ARTIFACT_ID, "artifact id")
    require_exact(artifact["name"], ARTIFACT_NAME, "artifact name")
    require_exact(artifact["sha256"], ARTIFACT_SHA256, "artifact digest")
    require_exact(artifact["size"], ARTIFACT_SIZE, "artifact size")
    github = exact_keys(
        source["github"],
        {
            "job_id",
            "repository",
            "run_attempt",
            "run_id",
            "runtime_head_sha",
            "runtime_tree_sha",
        },
        "GitHub identity",
    )
    require_exact(github["job_id"], GITHUB_JOB_ID, "GitHub job id")
    require_exact(github["repository"], GITHUB_REPOSITORY, "GitHub repository")
    require_exact(github["run_attempt"], GITHUB_RUN_ATTEMPT, "GitHub run attempt")
    require_exact(github["run_id"], GITHUB_RUN_ID, "GitHub run id")
    require_exact(github["runtime_head_sha"], RUNTIME_HEAD_SHA, "GitHub head")
    require_exact(github["runtime_tree_sha"], RUNTIME_TREE_SHA, "GitHub tree")

    runtime = exact_keys(
        review["runtime_candidate"],
        {"committed_inputs", "container", "head_sha", "tree_sha"},
        "runtime candidate",
    )
    require_exact(runtime["head_sha"], RUNTIME_HEAD_SHA, "runtime head")
    require_exact(runtime["tree_sha"], RUNTIME_TREE_SHA, "runtime tree")
    exact_keys(
        runtime["container"],
        {
            "image",
            "manifest_digest",
            "runtime_architecture",
            "runtime_os_id",
            "runtime_os_version_id",
        },
        "container",
    )
    require_exact(
        runtime["container"],
        {
            "image": CONTAINER_IMAGE,
            "manifest_digest": CONTAINER_IMAGE.split("@", 1)[1],
            "runtime_architecture": "x86_64",
            "runtime_os_id": "rocky",
            "runtime_os_version_id": "10.2",
        },
        "container",
    )
    require_exact(runtime["committed_inputs"], EXPECTED_INPUTS, "committed inputs")

    facts = exact_keys(
        review["verified_facts"],
        {
            "artifact_state",
            "commands",
            "configurations",
            "delta",
            "dependency_assertions",
            "patch_authority",
            "tool_probes",
        },
        "verified facts",
    )
    state = exact_keys(
        facts["artifact_state"],
        {
            "capture_exit_code",
            "capture_exit_code_sha256",
            "capture_log_sha256",
            "workflow_state",
            "workflow_state_sha256",
        },
        "artifact state",
    )
    require_exact(
        state,
        {
            "capture_exit_code": 0,
            "capture_exit_code_sha256": "9a271f2a916b0b6ee6cecb2426f0b3206ef074578be55d9bc94f6f3fe3ab86aa",
            "capture_log_sha256": "486d5bc92a8b371913d75557b2d18f84e9cf684788681bffb3c0dfaeae00b822",
            "workflow_state": "bootstrap-complete",
            "workflow_state_sha256": "800e9e1be143c4397583a9ec55b59cb110a9db5c77844c77037f3082daf8d182",
        },
        "artifact state",
    )
    configurations = exact_keys(
        facts["configurations"],
        {"baseline", "control", "fragment", "resolved"},
        "configurations",
    )
    validate_config_fact(
        configurations["baseline"],
        {"line_count": 8469, "path": "capture/baseline.config", "sha256": BASELINE_CONFIG_SHA256, "size": 254653, "symbol_count": 8468},
        "baseline configuration",
    )
    validate_config_fact(
        configurations["fragment"],
        {"line_count": 2, "path": "capture/fragment.config", "sha256": FRAGMENT_CONFIG_SHA256, "size": 46, "symbol_count": 2},
        "fragment configuration",
    )
    validate_config_fact(
        configurations["control"],
        {"byte_identical": True, "line_count": 10144, "paths": ["capture/control-pass-1.config", "capture/control-pass-2.config"], "sha256": CONTROL_CONFIG_SHA256, "size": 259858, "symbol_count": 8354},
        "control configuration",
        pair=True,
    )
    validate_config_fact(
        configurations["resolved"],
        {"byte_identical": True, "line_count": 10154, "paths": ["capture/resolved-pass-1.config", "capture/resolved-pass-2.config"], "sha256": RESOLVED_CONFIG_SHA256, "size": 260311, "symbol_count": 8364},
        "resolved configuration",
        pair=True,
    )
    delta = exact_keys(
        facts["delta"],
        {
            "baseline_to_control",
            "control_to_resolved",
            "derived_changes",
            "generated_symbol_results",
            "representation_changes",
            "requested_changes",
            "requested_generated_symbols",
            "unexpected_generated_symbols",
        },
        "delta facts",
    )
    require_exact(delta["baseline_to_control"], {"presence_count": 1149, "semantic_count": 1733, "total_count": 2882}, "baseline delta facts")
    require_exact(delta["control_to_resolved"], {"presence_count": 8, "semantic_count": 5, "total_count": 13}, "resolved delta facts")
    require_exact(delta["requested_changes"], EXPECTED_REQUESTED_CHANGES, "requested changes")
    require_exact(delta["derived_changes"], EXPECTED_DERIVED_CHANGES, "derived changes")
    require_exact(delta["requested_generated_symbols"], EXPECTED_REQUESTED_GENERATED_CHANGES, "generated changes")
    require_exact(delta["representation_changes"], EXPECTED_REPRESENTATION_CHANGES, "representation changes")
    require_exact(delta["generated_symbol_results"], EXPECTED_GENERATED_SYMBOL_RESULTS, "generated results")
    require_exact(delta["unexpected_generated_symbols"], [], "unexpected generated")
    commands = exact_keys(
        facts["commands"],
        {"pass_count", "patch_count", "raw_streams_archived", "rustavailable_pass_count", "schema_version"},
        "command facts",
    )
    require_exact(commands, {"pass_count": 2, "patch_count": 23, "raw_streams_archived": False, "rustavailable_pass_count": 2, "schema_version": 2}, "command facts")
    dependency = exact_keys(
        facts["dependency_assertions"],
        {"dependency_count", "preservation_group_counts", "preserved_symbol_count"},
        "dependency facts",
    )
    require_exact(dependency, {"dependency_count": 11, "preservation_group_counts": {"btf_debug": 7, "module_signing": 10, "warning_policy": 1}, "preserved_symbol_count": 18}, "dependency facts")
    patch_authority = exact_keys(
        facts["patch_authority"], {"count", "patches"}, "patch authority"
    )
    require_exact(patch_authority["count"], 23, "patch count")
    require_exact(patch_authority["patches"], EXPECTED_PATCHES, "patches")
    require_exact(
        policy["bound_input_count"],
        len(EXPECTED_INPUTS) + len(EXPECTED_PATCHES),
        "bound input count",
    )
    probes = exact_keys(
        facts["tool_probes"], set(EXPECTED_TOOL_PROBES), "reviewed probes"
    )
    for name, expected in EXPECTED_TOOL_PROBES.items():
        exact_keys(probes[name], {"owner", "path", "sha256", "stdout_sha256"}, name + " probe")
        require_exact(
            probes[name],
            {"owner": expected["owner"], "path": expected["path"], "sha256": expected["sha256"], "stdout_sha256": expected["stdout_sha256"]},
            name + " probe",
        )

    closure = exact_keys(
        review["zip_closure"],
        {
            "compressed_payload_size",
            "compression_methods",
            "crc_verified",
            "duplicate_paths",
            "entry_count",
            "entry_index_sha256",
            "entry_comments_empty",
            "entry_extra_fields_empty",
            "entry_flag_bits",
            "external_attributes",
            "internal_sha256sums_sha256",
            "path_index_sha256",
            "safe_regular_files_only",
            "uncompressed_size",
            "zip_comment_empty",
        },
        "ZIP closure",
    )
    require_exact(
        closure,
        {
            "compressed_payload_size": 1716007,
            "compression_methods": [0],
            "crc_verified": True,
            "duplicate_paths": False,
            "entry_count": 16,
            "entry_index_sha256": "93c4b7895d835d31d1be5b7f2f90d3768bb24b19b639137ca752aa721fa4a9cc",
            "entry_comments_empty": True,
            "entry_extra_fields_empty": True,
            "entry_flag_bits": [8],
            "external_attributes": [2164260896, 2175008800],
            "internal_sha256sums_sha256": "820ab996e1487ed0632b82c8f19da23076f0b090b7e08d4daaae100e4500484c",
            "path_index_sha256": "5463f5c7a97fe1a4b48be0017b8b5adc158cf2934a13f3faa5c837a4d050a110",
            "safe_regular_files_only": True,
            "uncompressed_size": 1716007,
            "zip_comment_empty": True,
        },
        "ZIP closure",
    )
    return review


def validate_repository(repo, review):
    runtime = review["runtime_candidate"]
    runtime_head = runtime["head_sha"]
    current_head = run_git(repo, ["rev-parse", "HEAD"]).stdout.decode("ascii").strip()
    if HEX_SHA1.fullmatch(current_head) is None:
        raise ConfigReviewV2Error("current HEAD is malformed")
    require_exact(
        run_git(repo, ["cat-file", "-t", runtime_head]).stdout.decode("ascii").strip(),
        "commit",
        "runtime object type",
    )
    require_exact(
        run_git(repo, ["show", "-s", "--format=%T", runtime_head]).stdout.decode("ascii").strip(),
        runtime["tree_sha"],
        "runtime tree",
    )
    ancestor = run_git(
        repo,
        ["merge-base", "--is-ancestor", runtime_head, current_head],
        allow_failure=True,
    )
    if ancestor.returncode != 0:
        raise ConfigReviewV2Error("current HEAD is not a descendant of the reviewed head")
    rows = list(runtime["committed_inputs"])
    for index, patch in enumerate(review["verified_facts"]["patch_authority"]["patches"]):
        row = dict(patch)
        blob = git_tree_record(repo, runtime_head, row["path"], "patch {}".format(index))
        data = git_blob_bytes(repo, blob, "patch {}".format(index))
        row["git_blob_sha1"] = blob
        row["size"] = len(data)
        rows.append(row)
    for index, row in enumerate(rows):
        validate_input_row(
            repo,
            runtime_head,
            row,
            current_head,
            "bound input {}".format(index),
        )
    return current_head


def safe_zip_path(name):
    safe_relative_path(name, "ZIP entry")
    if name.endswith("/"):
        raise ConfigReviewV2Error("ZIP directories are forbidden")
    return name


def zip_entry_records(archive):
    records = []
    names = []
    for info in archive.infolist():
        name = safe_zip_path(info.filename)
        names.append(name)
        mode = info.external_attr >> 16
        if not stat.S_ISREG(mode):
            raise ConfigReviewV2Error("ZIP entry is not a regular file: " + name)
        if info.create_system != 3:
            raise ConfigReviewV2Error("ZIP entry has the wrong creator: " + name)
        if info.extra != b"":
            raise ConfigReviewV2Error("ZIP entry has forbidden extra fields: " + name)
        if info.comment != b"":
            raise ConfigReviewV2Error("ZIP entry has a forbidden comment: " + name)
        if info.flag_bits != 8:
            raise ConfigReviewV2Error("ZIP entry has unexpected flag bits: " + name)
        if info.compress_type != zipfile.ZIP_STORED:
            raise ConfigReviewV2Error("ZIP entry is not stored: " + name)
        if info.external_attr not in (2164260896, 2175008800):
            raise ConfigReviewV2Error("ZIP entry attributes are unreviewed: " + name)
        if info.file_size < 1 or info.compress_size != info.file_size:
            raise ConfigReviewV2Error("ZIP entry size is invalid: " + name)
        if info.flag_bits & 0x1:
            raise ConfigReviewV2Error("encrypted ZIP entries are forbidden")
        try:
            data = archive.read(info)
        except (OSError, RuntimeError, zipfile.BadZipFile) as exc:
            raise ConfigReviewV2Error(
                "cannot read ZIP entry {}: {}".format(name, exc)
            )
        if len(data) != info.file_size:
            raise ConfigReviewV2Error("ZIP entry length differs: " + name)
        records.append(
            {
                "comment_length": len(info.comment),
                "compressed_size": info.compress_size,
                "compression_method": info.compress_type,
                "create_system": info.create_system,
                "crc32": format(info.CRC, "08x"),
                "external_attributes": info.external_attr,
                "extra_length": len(info.extra),
                "flag_bits": info.flag_bits,
                "path": name,
                "sha256": sha256_bytes(data),
                "size": info.file_size,
            }
        )
    if len(names) != len(set(names)):
        raise ConfigReviewV2Error("ZIP contains duplicate paths")
    if not records:
        raise ConfigReviewV2Error("ZIP contains no entries")
    records.sort(key=lambda row: row["path"])
    return records


def parse_sha256sums(data):
    try:
        text = data.decode("ascii")
    except UnicodeError as exc:
        raise ConfigReviewV2Error("SHA256SUMS is not ASCII: {}".format(exc))
    if not text.endswith("\n"):
        raise ConfigReviewV2Error("SHA256SUMS lacks its final newline")
    rows = {}
    for line in text.splitlines():
        match = SHA256SUM.fullmatch(line)
        if match is None:
            raise ConfigReviewV2Error("SHA256SUMS has a malformed row")
        digest, name = match.groups()
        safe_relative_path(name, "checksum path")
        if name in rows:
            raise ConfigReviewV2Error("SHA256SUMS has a duplicate path")
        rows[name] = digest
    require_exact(tuple(rows), EXPECTED_CHECKSUM_NAMES, "checksum paths")
    require_exact(rows, EXPECTED_CHECKSUM_DIGESTS, "checksum digests")
    return rows


def parse_config(data, label):
    try:
        text = data.decode("utf-8")
    except UnicodeError as exc:
        raise ConfigReviewV2Error("{} is not UTF-8: {}".format(label, exc))
    if any(
        (ord(character) < 0x20 and character != "\n")
        or 0x7F <= ord(character) <= 0x9F
        or character in ("\u2028", "\u2029")
        for character in text
    ):
        raise ConfigReviewV2Error(
            "{} contains a forbidden control character".format(label)
        )
    if not text.endswith("\n"):
        raise ConfigReviewV2Error("{} lacks its final newline".format(label))
    values = {}
    for line_number, line in enumerate(text.splitlines(), 1):
        match = CONFIG_VALUE.fullmatch(line)
        if match is not None:
            symbol, value = match.groups()
            if CONFIG_ASSIGNMENT_VALUE.fullmatch(value) is None:
                raise ConfigReviewV2Error(
                    "{}:{} has a malformed assignment".format(label, line_number)
                )
        else:
            match = CONFIG_UNSET.fullmatch(line)
            if match is None:
                if line.startswith("# CONFIG"):
                    raise ConfigReviewV2Error(
                        "{}:{} has a malformed config comment".format(
                            label, line_number
                        )
                    )
                if line == "" or line.startswith("#"):
                    continue
                raise ConfigReviewV2Error(
                    "{}:{} has a malformed row".format(label, line_number)
                )
            symbol, value = match.group(1), "n"
        if symbol in values:
            raise ConfigReviewV2Error(
                "{}:{} duplicates {}".format(label, line_number, symbol)
            )
        values[symbol] = value
    if not values:
        raise ConfigReviewV2Error("{} contains no config symbols".format(label))
    return values


def semantic_config_value(value):
    return "n" if value == "<absent>" else value


def changed_symbols(before, after):
    return [
        {
            "after": after.get(symbol, "<absent>"),
            "before": before.get(symbol, "<absent>"),
            "symbol": symbol,
        }
        for symbol in sorted(set(before) | set(after))
        if before.get(symbol, "<absent>") != after.get(symbol, "<absent>")
    ]


def partition_changes(rows):
    semantic = []
    presence = []
    for row in rows:
        target = semantic if semantic_config_value(row["before"]) != semantic_config_value(row["after"]) else presence
        target.append(row)
    return semantic, presence


def verify_config_record(files, record, label):
    paths = record.get("paths") or [record.get("path")]
    if not paths or any(path not in files for path in paths):
        raise ConfigReviewV2Error("{} paths are incomplete".format(label))
    values = []
    for path in paths:
        data = files[path]
        require_exact(len(data), record["size"], label + " size")
        require_exact(sha256_bytes(data), record["sha256"], label + " digest")
        require_exact(len(data.splitlines()), record["line_count"], label + " lines")
        parsed = parse_config(data, label)
        require_exact(len(parsed), record["symbol_count"], label + " symbols")
        values.append(parsed)
    if len(paths) == 2:
        require_exact(files[paths[0]], files[paths[1]], label + " byte equivalence")
        require_exact(values[0], values[1], label + " map equivalence")
    return values[0]


def verify_environment_document(environment, review, identity):
    exact_keys(
        environment,
        {"container_image", "fixed_environment", "github", "probes", "schema_version"},
        "environment",
    )
    require_exact(environment["container_image"], CONTAINER_IMAGE, "environment image")
    require_exact(environment["fixed_environment"], EXPECTED_FIXED_ENVIRONMENT, "fixed environment")
    require_exact(environment["github"], identity, "environment identity")
    require_exact(environment["schema_version"], 2, "environment schema")
    probes = exact_keys(
        environment["probes"], set(EXPECTED_TOOL_PROBES) | {"derived"}, "environment probes"
    )
    require_exact(probes["derived"], EXPECTED_ENVIRONMENT_DERIVED, "probe derivations")
    reviewed = review["verified_facts"]["tool_probes"]
    owner_format = "%{NAME}-%{EPOCHNUM}:%{VERSION}-%{RELEASE}.%{ARCH}\\n"
    for name, expected in EXPECTED_TOOL_PROBES.items():
        probe = probes[name]
        if name == "rust_src_core":
            exact_keys(probe, {"command", "file_path", "file_sha256", "owner_command", "package_nevra", "stderr_sha256", "stdout_sha256"}, name + " probe")
            path_key = "file_path"
            digest_key = "file_sha256"
        else:
            exact_keys(probe, {"binary_path", "binary_sha256", "command", "owner_command", "package_nevra", "stderr_sha256", "stdout_sha256", "text"}, name + " probe")
            path_key = "binary_path"
            digest_key = "binary_sha256"
            require_exact(sha256_bytes(probe["text"].encode("utf-8")), expected["stdout_sha256"], name + " text")
        require_exact(probe[path_key], expected["path"], name + " path")
        require_exact(probe[digest_key], expected["sha256"], name + " digest")
        require_exact(probe["command"], expected["command"], name + " command")
        require_exact(probe["owner_command"], ["rpm", "-qf", "--qf", owner_format, expected["path"]], name + " owner command")
        require_exact(probe["package_nevra"], expected["owner"], name + " owner")
        require_exact(probe["stderr_sha256"], EMPTY_SHA256, name + " stderr")
        require_exact(probe["stdout_sha256"], expected["stdout_sha256"], name + " stdout")
        require_exact(reviewed[name]["path"], expected["path"], name + " reviewed path")


def verify_commands_document(commands, review):
    exact_keys(commands, {"passes", "patches", "schema_version"}, "commands")
    require_exact(commands["schema_version"], 2, "commands schema")
    require_exact(commands["patches"], EXPECTED_PATCHES, "command patches")
    require_exact(commands["patches"], review["verified_facts"]["patch_authority"]["patches"], "reviewed patches")
    passes = commands["passes"]
    if not isinstance(passes, list) or len(passes) != 2:
        raise ConfigReviewV2Error("commands require exactly two passes")
    roots = []
    fixed_process = {
        "ARCH": "x86_64",
        "FLAVOR": "rhel",
        "HOME": "/root",
        "LANG": "C",
        "LC_ALL": "C",
        "PATH": "/usr/sbin:/usr/bin:/sbin:/bin",
        "RHJOBS": "1",
        "TZ": "UTC",
    }
    for number, row in enumerate(passes, 1):
        exact_keys(row, {"control_olddefconfig", "control_process_configs", "control_process_environment", "fragment_merge", "requested_olddefconfig", "requested_process_configs", "requested_process_environment", "requested_rustavailable", "source_cleanup"}, "command pass {}".format(number))
        cleanup = row["source_cleanup"]
        if not isinstance(cleanup, list) or len(cleanup) != 6:
            raise ConfigReviewV2Error("source cleanup is malformed")
        source = cleanup[2]
        match = TEMP_SOURCE.fullmatch(source) if isinstance(source, str) else None
        if match is None or int(match.group(2)) != number:
            raise ConfigReviewV2Error("command pass root is malformed")
        root = match.group(1)
        roots.append(root)
        control = root + "/pass-{}/control-build".format(number)
        requested = root + "/pass-{}/requested-build".format(number)
        merge = root + "/pass-{}/fragment-merge".format(number)
        require_exact(cleanup, ["make", "-C", source, "ARCH=x86_64", "LLVM=1", "mrproper"], "cleanup command")
        process = [source + "/redhat/configs/process_configs.sh", "-m", "LLVM=1", "6.12.0", "rhel"]
        require_exact(row["control_process_configs"], process, "control process command")
        require_exact(row["requested_process_configs"], process, "requested process command")
        control_env = dict(fixed_process)
        control_env["SPECPACKAGE_NAME"] = "kernel-rk005-control-pass-{}".format(number)
        requested_env = dict(fixed_process)
        requested_env["SPECPACKAGE_NAME"] = "kernel-rk005-requested-pass-{}".format(number)
        require_exact(row["control_process_environment"], control_env, "control process environment")
        require_exact(row["requested_process_environment"], requested_env, "requested process environment")
        require_exact(row["control_olddefconfig"], ["make", "-C", source, "O=" + control, "ARCH=x86_64", "LLVM=1", "olddefconfig"], "control olddefconfig")
        require_exact(row["fragment_merge"], [source + "/scripts/kconfig/merge_config.sh", "-m", "-O", merge, merge + "/.config", "/__w/mckernel/mckernel/host-kernel/rocky/configs/rust-minimal.config"], "fragment merge")
        require_exact(row["requested_olddefconfig"], ["make", "-C", source, "O=" + requested, "ARCH=x86_64", "LLVM=1", "olddefconfig"], "requested olddefconfig")
        rustavailable = exact_keys(row["requested_rustavailable"], {"command", "exit_code", "stderr_sha256", "stdout_sha256", "success_line_count"}, "rustavailable pass {}".format(number))
        require_exact(rustavailable["command"], ["make", "-C", source, "O=" + requested, "ARCH=x86_64", "LLVM=1", "rustavailable"], "rustavailable command")
        require_exact(rustavailable["exit_code"], 0, "rustavailable exit")
        require_exact(rustavailable["stderr_sha256"], EMPTY_SHA256, "rustavailable stderr")
        require_exact(rustavailable["stdout_sha256"], EXPECTED_RUSTAVAILABLE_STDOUT[number - 1], "rustavailable stdout")
        require_exact(rustavailable["success_line_count"], 1, "rustavailable success count")
    require_exact(roots[0], roots[1], "independent pass temporary root")


def verify_artifact(artifact_path, review):
    artifact_path = regular_file(artifact_path, "artifact ZIP")
    artifact_bytes = artifact_path.read_bytes()
    artifact = review["source_artifact"]["artifact"]
    require_exact(len(artifact_bytes), artifact["size"], "artifact size")
    require_exact(sha256_bytes(artifact_bytes), artifact["sha256"], "artifact digest")
    try:
        archive = zipfile.ZipFile(io.BytesIO(artifact_bytes), "r")
    except (OSError, zipfile.BadZipFile) as exc:
        raise ConfigReviewV2Error("artifact is not a readable ZIP: {}".format(exc))
    with archive:
        if archive.comment != b"":
            raise ConfigReviewV2Error("ZIP comments are forbidden")
        records = zip_entry_records(archive)
        paths = tuple(row["path"] for row in records)
        require_exact(paths, EXPECTED_ARCHIVE_PATHS, "artifact paths")
        for row in records:
            expected_attr = 2175008800 if row["path"] in ("capture.exit-code", "capture.log", "workflow-state") else 2164260896
            require_exact(row["external_attributes"], expected_attr, "ZIP attributes " + row["path"])
        closure = review["zip_closure"]
        require_exact(len(records), closure["entry_count"], "ZIP entry count")
        require_exact(sum(row["compressed_size"] for row in records), closure["compressed_payload_size"], "ZIP compressed payload")
        require_exact(sum(row["size"] for row in records), closure["uncompressed_size"], "ZIP uncompressed payload")
        require_exact(sorted(set(row["compression_method"] for row in records)), closure["compression_methods"], "ZIP methods")
        require_exact(sorted(set(row["external_attributes"] for row in records)), closure["external_attributes"], "ZIP attributes")
        require_exact(sorted(set(row["flag_bits"] for row in records)), closure["entry_flag_bits"], "ZIP flags")
        require_exact(sha256_bytes(canonical_json_bytes(records)), closure["entry_index_sha256"], "ZIP entry index")
        require_exact(sha256_bytes(canonical_json_bytes(sorted(paths))), closure["path_index_sha256"], "ZIP path index")
        files = {name: archive.read(name) for name in paths}

    state = review["verified_facts"]["artifact_state"]
    require_exact(files["capture.exit-code"], b"0\n", "capture exit code")
    require_exact(files["capture.log"], CAPTURE_LOG, "capture log")
    require_exact(files["workflow-state"], b"bootstrap-complete\n", "workflow state")
    require_exact(sha256_bytes(files["capture.exit-code"]), state["capture_exit_code_sha256"], "capture exit digest")
    require_exact(sha256_bytes(files["capture.log"]), state["capture_log_sha256"], "capture log digest")
    require_exact(sha256_bytes(files["workflow-state"]), state["workflow_state_sha256"], "workflow state digest")

    sums_data = files["capture/SHA256SUMS"]
    require_exact(sha256_bytes(sums_data), review["zip_closure"]["internal_sha256sums_sha256"], "internal SHA256SUMS")
    sums = parse_sha256sums(sums_data)
    for name, digest in sums.items():
        require_exact(sha256_bytes(files["capture/" + name]), digest, "checksum " + name)

    json_names = ("blockers.json", "checkpoint.json", "commands.json", "config-delta.json", "dependency-assertions.json", "environment.json")
    documents = {
        name: read_json_bytes(files["capture/" + name], name, require_canonical=True)
        for name in json_names
    }
    blockers = exact_keys(documents["blockers.json"], {"gate_claims", "success_blockers"}, "blockers")
    require_exact(blockers["gate_claims"], EXPECTED_GATE_CLAIMS, "blocker gates")
    require_exact(blockers["success_blockers"], EXPECTED_REMAINING_PREREQUISITES, "artifact blockers")
    identity = {
        "head_sha": RUNTIME_HEAD_SHA,
        "repository": GITHUB_REPOSITORY,
        "run_attempt": GITHUB_RUN_ATTEMPT,
        "run_id": GITHUB_RUN_ID,
    }
    checkpoint = exact_keys(documents["checkpoint.json"], {"credit_eligible", "gate_claims", "github", "manifests", "phase", "schema_version", "two_independent_resolutions_identical"}, "checkpoint")
    require_exact(checkpoint["credit_eligible"], False, "checkpoint credit")
    require_exact(checkpoint["gate_claims"], EXPECTED_GATE_CLAIMS, "checkpoint gates")
    require_exact(checkpoint["github"], identity, "checkpoint identity")
    require_exact(checkpoint["phase"], "config-resolution-v2", "checkpoint phase")
    require_exact(checkpoint["schema_version"], 2, "checkpoint schema")
    require_exact(checkpoint["two_independent_resolutions_identical"], True, "checkpoint equivalence")
    manifests = checkpoint["manifests"]
    if not isinstance(manifests, list) or not manifests:
        raise ConfigReviewV2Error("checkpoint manifests must be a nonempty list")
    require_exact(tuple(row.get("path") for row in manifests), EXPECTED_CHECKSUM_NAMES[:-1], "checkpoint manifest paths")
    for index, row in enumerate(manifests):
        exact_keys(row, {"path", "sha256", "size"}, "checkpoint row {}".format(index))
        require_positive_int(row["size"], "checkpoint size")
        require_exact(row["sha256"], sums[row["path"]], "checkpoint digest")
        data = files["capture/" + row["path"]]
        require_exact((sha256_bytes(data), len(data)), (row["sha256"], row["size"]), "checkpoint row")

    verify_environment_document(documents["environment.json"], review, identity)
    verify_commands_document(documents["commands.json"], review)
    configurations = review["verified_facts"]["configurations"]
    baseline = verify_config_record(files, configurations["baseline"], "baseline")
    fragment = verify_config_record(files, configurations["fragment"], "fragment")
    control = verify_config_record(files, configurations["control"], "control")
    resolved = verify_config_record(files, configurations["resolved"], "resolved")
    require_exact(files["capture/fragment.config"], b"CONFIG_RUST=y\n# CONFIG_MODVERSIONS is not set\n", "fragment bytes")
    require_exact(fragment, {"CONFIG_MODVERSIONS": "n", "CONFIG_RUST": "y"}, "fragment map")

    delta = exact_keys(documents["config-delta.json"], {"classification", "derived_changes", "environment_generated_changes", "generated_symbol_results", "representation_changes", "requested_changes", "requested_generated_symbols", "unexpected_generated_symbols"}, "config delta")
    classification = exact_keys(delta["classification"], {"baseline_to_control", "control_to_resolved", "stages"}, "classification")
    require_exact(classification["stages"], ["baseline", "control", "resolved"], "classification stages")
    baseline_rows = changed_symbols(baseline, control)
    control_rows = changed_symbols(control, resolved)
    require_exact(classification["baseline_to_control"], baseline_rows, "baseline classification")
    require_exact(delta["environment_generated_changes"], baseline_rows, "environment changes")
    require_exact(classification["control_to_resolved"], control_rows, "resolved classification")
    baseline_semantic, baseline_presence = partition_changes(baseline_rows)
    control_semantic, control_presence = partition_changes(control_rows)
    facts = review["verified_facts"]["delta"]
    require_exact({"presence_count": len(baseline_presence), "semantic_count": len(baseline_semantic), "total_count": len(baseline_rows)}, facts["baseline_to_control"], "baseline counts")
    require_exact({"presence_count": len(control_presence), "semantic_count": len(control_semantic), "total_count": len(control_rows)}, facts["control_to_resolved"], "resolved counts")
    for key in ("requested_changes", "derived_changes", "requested_generated_symbols", "representation_changes", "generated_symbol_results", "unexpected_generated_symbols"):
        require_exact(delta[key], facts[key], "reviewed " + key)
    classified = sorted(delta["requested_changes"] + delta["derived_changes"] + delta["requested_generated_symbols"] + delta["representation_changes"], key=lambda row: row["symbol"])
    require_exact(classified, control_rows, "complete resolved partition")
    require_exact(delta["representation_changes"], control_presence, "presence partition")
    semantic_classified = sorted(delta["requested_changes"] + delta["derived_changes"] + delta["requested_generated_symbols"], key=lambda row: row["symbol"])
    require_exact(semantic_classified, control_semantic, "semantic partition")
    for symbol, expected in EXPECTED_GENERATED_SYMBOL_RESULTS.items():
        require_exact(semantic_config_value(resolved.get(symbol, "<absent>")), expected, "generated " + symbol)

    assertions = exact_keys(documents["dependency-assertions.json"], {"dependencies", "preservation_groups"}, "assertions")
    require_exact(assertions["dependencies"], EXPECTED_DEPENDENCIES, "dependencies")
    require_exact(assertions["preservation_groups"], EXPECTED_PRESERVATION, "preservation")
    for symbol, expected in EXPECTED_DEPENDENCIES.items():
        require_exact(semantic_config_value(resolved.get(symbol, "<absent>")), expected, "dependency " + symbol)
    for group, values in EXPECTED_PRESERVATION.items():
        for symbol, expected in values.items():
            for stage, config in (("baseline", baseline), ("control", control), ("resolved", resolved)):
                require_exact(semantic_config_value(config.get(symbol, "<absent>")), expected, "{} {} {}".format(group, stage, symbol))
    return {"artifact_sha256": ARTIFACT_SHA256, "resolved_config_sha256": RESOLVED_CONFIG_SHA256}


def parse_args(argv):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--review", type=Path)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--check", action="store_true")
    modes.add_argument("--verify-artifact")
    return parser.parse_args(argv)


def main(argv):
    args = parse_args(argv)
    repo = args.repo.resolve()
    try:
        review_path = discover_review(repo, args.review)
        review = validate_review_object(load_review(review_path))
        current_head = validate_repository(repo, review)
        if args.check:
            print(
                "independent RK-005 v2 review verified at descendant-or-equal {}; "
                "gate, tracker, durable, offline, and production claims remain false".format(current_head)
            )
            return 0
        result = verify_artifact(args.verify_artifact, review)
        print(
            "independent RK-005 v2 artifact verified: zip sha256={} resolved config sha256={}; "
            "all credit claims remain false".format(
                result["artifact_sha256"], result["resolved_config_sha256"]
            )
        )
        return 0
    except (ConfigReviewV2Error, OSError, UnicodeError, ValueError, zipfile.BadZipFile) as exc:
        print("Rocky config-review-v2 error: {}".format(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
