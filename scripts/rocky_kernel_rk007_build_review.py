#!/usr/bin/env python3
"""Verify one bounded, non-crediting RK-007 exact-build artifact review.

The review is historical and exact-runtime-head.  Descendant repository ports
must enumerate exact changed current inputs without retargeting the reviewed
bytes.  The review closes the captured Kbuild module-link surface of one
GitHub Actions artifact; it does not prove durable retention, a production
build, module loading, hardware coverage, runtime behavior, or RK-007/tracker
credit.
"""

from __future__ import print_function

import argparse
import hashlib
import io
import json
import os
import re
import shlex
import stat
import struct
import subprocess
import sys
import zipfile
from pathlib import Path, PurePosixPath


REVIEW_DIRECTORY = Path("host-kernel/rocky/evidence")
REVIEW_GLOB = "rk007-native-build-review-*-v1.json"
SCHEMA_VERSION = 1
REVIEW_ID = "rk-007-native-rust-exact-build-review-bc60eed5-v1"
REVIEW_SHA256 = "f01713c701698d2b3651423c74fa0811db00d7ce34d6641e42238532f829e015"
EXPECTED_HISTORICAL_PROJECTION_SHA256 = (
    "ead3785b11e5ec04840978e09c972050fb9ee5ea6d946e5f0efba2c58a11f61d"
)
RUNTIME_HEAD_SHA = "bc60eed563527ad72761e0ad8209a9b5f9242fb3"
RUNTIME_TREE_SHA = "9f26e59299544d4aeee0503c10c13e0915885b4a"
GITHUB_REPOSITORY = "phoenix-hacking/mckernel"
GITHUB_RUN_ID = 32102757520
GITHUB_RUN_ATTEMPT = 1
GITHUB_JOB_ID = 95606332586
ARTIFACT_ID = 9312566500
ARTIFACT_NAME = "native-rust-exact-build-32102757520-1"
ARTIFACT_SIZE = 22458133
ARTIFACT_SHA256 = "72de35e144c18413980eb9f404aa6971c29826c86621fee18cc132ae6f23f346"
ARTIFACT_EXPIRES_AT = "2026-09-17T05:46:12Z"
HEX_SHA1 = re.compile(r"^[0-9a-f]{40}$")
HEX_SHA256 = re.compile(r"^[0-9a-f]{64}$")
SUM_LINE = re.compile(r"^([0-9a-f]{64})  ([A-Za-z0-9.][A-Za-z0-9_.-]*)$")
CONFIG_SET = re.compile(r"^(CONFIG_[A-Za-z0-9_]+)=(.*)$")
CONFIG_UNSET = re.compile(r"^# (CONFIG_[A-Za-z0-9_]+) is not set$")
SOURCE_ROOT = "/__w/_temp/native-rust-source/linux-6.12.0-211.44.1.el10_2"
MODULE_ROOT = "drivers/misc/mckernel"
CONTAINER_IMAGE = (
    "rockylinux/rockylinux:10.2@sha256:"
    "e372170ca8630f0f03e9b70fdd0bf4a3ce3426b0de7cdba615f06337389de176"
)

EXPECTED_GATE_CLAIMS = {
    "RK-002": False,
    "RK-003": False,
    "RK-004": False,
    "RK-005": False,
    "RK-006": False,
    "RK-007": False,
    "RS-001": False,
}
EXPECTED_CLAIMS = {
    "broad_hardware_compatibility": False,
    "complete_external_build_cmd_closure": False,
    "credit_eligible": False,
    "durable_archive": False,
    "exact_toolchain_binary_identity_proven": False,
    "gate_claims": EXPECTED_GATE_CLAIMS,
    "module_loadability_proven": False,
    "production_build_proven": False,
    "resolved_config_authority_proven": False,
    "runtime_behavior_proven": False,
    "source_patch_authority_proven": False,
    "tracker_credit": False,
}
EXPECTED_CAVEATS = {
    "archive_bytes_committed": False,
    "artifact_retention_is_durable": False,
    "captured_cmd_scope": (
        "all thirteen top-level drivers/misc/mckernel .cmd records uploaded by "
        "the exact workflow; the complete external build tree was not archived"
    ),
    "command_oracle_reuse": (
        "the exact raw-command and immutable token-vector oracles are artifact-specific; "
        "future artifacts require a new independent review and must not be accepted by "
        "automatic digest refresh"
    ),
    "generated_mod_c_is_project_c": False,
    "elf_parser_scope": (
        "exact ELF64 little-endian x86-64 ET_REL shape; direct module bytes are "
        "authoritative and uploaded modinfo, nm, and readelf text is diagnostic corroboration"
    ),
    "raw_compiler_binaries_archived": False,
    "runtime_or_load_lifecycle_captured": False,
    "source_patch_and_toolchain_authorities_inherited": False,
    "unarchived_command_inputs": (
        "response files, dep-info, generated .mod.c, aggregate response lists, "
        ".module-common.o, and linked object bytes were not archived"
    ),
}
EXPECTED_REMAINING_PREREQUISITES = [
    (
        "Durably archive the exact artifact ZIP before its GitHub Actions copy "
        "expires at 2026-09-17T05:46:12Z."
    ),
    (
        "Independently close the selected source, compatibility-patch, resolved "
        "configuration, and exact toolchain authorities; this artifact review "
        "does not inherit their gate credit."
    ),
    (
        "Capture and review a complete external-build command/input closure if "
        "authority beyond the thirteen uploaded top-level module .cmd records is required."
    ),
    (
        "Run the exact modules through reviewed load, dependency, namespace, "
        "device, unload, and failure-path lifecycle evidence before any runtime claim."
    ),
    (
        "Any RK-007 or tracker credit requires a separate authority update; this "
        "bounded historical review cannot award it."
    ),
]
EXPECTED_REVIEW_KEYS = {
    "caveats", "claims", "current_repository_input_policy", "inner_closure",
    "remaining_prerequisites", "review_id", "review_kind", "runtime_candidate",
    "schema_version", "source_artifact", "verified_facts", "zip_closure",
}

EXPECTED_MODULE_TARGETS = [
    "drivers/misc/mckernel/ihk.ko",
    "drivers/misc/mckernel/ihk-smp-x86_64.ko",
    "drivers/misc/mckernel/mcctrl.ko",
]
EXPECTED_BUILT_MODULES = sorted(EXPECTED_MODULE_TARGETS)
EXPECTED_CONFIG = {
    "CONFIG_MODULES": "y",
    "CONFIG_MCKERNEL_IHK_RUST": "m",
    "CONFIG_MCKERNEL_IHK_SMP_X86_64_RUST": "m",
    "CONFIG_MCKERNEL_MCCTRL_RUST": "m",
    "CONFIG_RUST": "y",
    "CONFIG_WERROR": "y",
}
EXPECTED_STAGE_FILES = [
    {"path": "Kbuild", "sha256": "f33c826539ed0807617337ba64a1cb646daf510cc06a44b47243d14e366d67a3"},
    {"path": "Kconfig", "sha256": "69f14cc7d347d6da3d6cbe0199e35fab72e40f6af3683df1c337efd449721296"},
    {"path": "abi/x86_64.rs", "sha256": "b5980e5b621914a120a0e6b72241477c48aee85615ae4cc76077f3874e35f860"},
    {"path": "ihk.rs", "sha256": "53e2b003573804df8d11f34a8290108ac5a0fc15bb559f2f980c38a3316b4a55"},
    {"path": "ihk_ioctl.rs", "sha256": "3d603424705a9b0fb18725bae1d75f1d279b249b866c15f15f98166d013edfbb"},
    {"path": "ihk_smp_x86_64.rs", "sha256": "f5beb6dae65e486772af5198aa60f77d4e1b86d37b5ee8ae50eb4b34f9b0d74f"},
    {"path": "ikc_master.rs", "sha256": "f7e8f8bc1cc860a2eb3724457d81bf03b132fa156eac5c5e258a393808e6ca1e"},
    {"path": "ikc_queue.rs", "sha256": "514f9bce452498e5e9394c450532b040c44fce1ac7a6b5158c76f3d4c7270d40"},
    {"path": "mcctrl.rs", "sha256": "1a8b85c379d6976d90ba462b9386d1bbd7fce83ca152e46bce391e6cfa6b5389"},
    {"path": "os_registry.rs", "sha256": "29464b8ca1038d87cc0d5f760eb22e0cbd7a1a512ae88f4c550574a784d1e49d"},
    {"path": "page_allocator.rs", "sha256": "8e2af0cde06cbb70204540b493e8a0a66d5203195ed671235b64bed44d328bc5"},
    {"path": "page_owner_registry.rs", "sha256": "443d58fa5b2e423f538c6622ef04d8e34338abc43c5e0fd34811d52fc21f4869"},
]
STAGE_REPOSITORY_PATHS = {
    "Kbuild": "host-kernel/kbuild/Kbuild.in",
    "Kconfig": "host-kernel/kbuild/Kconfig",
    "abi/x86_64.rs": "host-kernel/native-rust/abi/x86_64.rs",
    "ihk.rs": "host-kernel/native-rust/ihk.rs",
    "ihk_ioctl.rs": "host-kernel/native-rust/ihk_ioctl.rs",
    "ihk_smp_x86_64.rs": "host-kernel/native-rust/ihk_smp_x86_64.rs",
    "ikc_master.rs": "host-kernel/native-rust/ikc_master.rs",
    "ikc_queue.rs": "host-kernel/native-rust/ikc_queue.rs",
    "mcctrl.rs": "host-kernel/native-rust/mcctrl.rs",
    "os_registry.rs": "host-kernel/native-rust/os_registry.rs",
    "page_allocator.rs": "host-kernel/native-rust/page_allocator.rs",
    "page_owner_registry.rs": "host-kernel/native-rust/page_owner_registry.rs",
}

EXPECTED_COMMITTED_INPUTS = [
    {"git_blob_sha1": "b35eb64a336adcfc048bb73ff1bb8a7f0e044ab9", "mode": "100644", "path": ".github/workflows/native-rust-host-modules-exact-build.yml", "sha256": "6566255ce3288d31e5a25047a3fe602171d80f868186f1a956b776592491cddf", "size": 26831},
    {"git_blob_sha1": "36553a626cb67f0dd54df3713aa9931c904a6b49", "mode": "100644", "path": "host-kernel/kbuild/Kbuild.in", "sha256": "f33c826539ed0807617337ba64a1cb646daf510cc06a44b47243d14e366d67a3", "size": 371},
    {"git_blob_sha1": "3a7f9ca21d2921eb8b5a1e3caa0ca5e5a8116956", "mode": "100644", "path": "host-kernel/kbuild/Kconfig", "sha256": "69f14cc7d347d6da3d6cbe0199e35fab72e40f6af3683df1c337efd449721296", "size": 823},
    {"git_blob_sha1": "8add3295a066294f788b5971f23be98b55407c33", "mode": "100644", "path": "host-kernel/kbuild/stage-manifest.json", "sha256": "7c2e2574b5fd1fc921b5e323b472680183d8bb2f7d9d39bdc3ef87208f434689", "size": 5743},
    {"git_blob_sha1": "ae02ad57d96b7cb46b165f0097116d1d04fb5cd4", "mode": "100644", "path": "host-kernel/native-rust/abi/x86_64.rs", "sha256": "b5980e5b621914a120a0e6b72241477c48aee85615ae4cc76077f3874e35f860", "size": 18796},
    {"git_blob_sha1": "9bccef539ec17fb91a2920cb0ca81486adcd2b33", "mode": "100644", "path": "host-kernel/native-rust/ihk.rs", "sha256": "53e2b003573804df8d11f34a8290108ac5a0fc15bb559f2f980c38a3316b4a55", "size": 3818},
    {"git_blob_sha1": "200f4840bfa71521bbbac628d080c0d5f66df0a2", "mode": "100644", "path": "host-kernel/native-rust/ihk_ioctl.rs", "sha256": "3d603424705a9b0fb18725bae1d75f1d279b249b866c15f15f98166d013edfbb", "size": 9977},
    {"git_blob_sha1": "fc3d63b0396fb09470b14b48c016bb246f93b493", "mode": "100644", "path": "host-kernel/native-rust/ihk_smp_x86_64.rs", "sha256": "f5beb6dae65e486772af5198aa60f77d4e1b86d37b5ee8ae50eb4b34f9b0d74f", "size": 10271},
    {"git_blob_sha1": "73ce30401de5980e747c4a9197fcb73b571b5ef7", "mode": "100644", "path": "host-kernel/native-rust/ikc_master.rs", "sha256": "f7e8f8bc1cc860a2eb3724457d81bf03b132fa156eac5c5e258a393808e6ca1e", "size": 26419},
    {"git_blob_sha1": "ce3e82e5b571f11ef5bfcde7394146e618db3fc6", "mode": "100644", "path": "host-kernel/native-rust/ikc_queue.rs", "sha256": "514f9bce452498e5e9394c450532b040c44fce1ac7a6b5158c76f3d4c7270d40", "size": 17662},
    {"git_blob_sha1": "47b8baf1aac67f4578ffcb6fc8c45a4ca7d8cac7", "mode": "100644", "path": "host-kernel/native-rust/mcctrl.rs", "sha256": "1a8b85c379d6976d90ba462b9386d1bbd7fce83ca152e46bce391e6cfa6b5389", "size": 3017},
    {"git_blob_sha1": "4cc0d58b65b2717b5bc9b020aaa5a68c0598b420", "mode": "100644", "path": "host-kernel/native-rust/os_registry.rs", "sha256": "29464b8ca1038d87cc0d5f760eb22e0cbd7a1a512ae88f4c550574a784d1e49d", "size": 17706},
    {"git_blob_sha1": "d18dc2ad253d63492984ab707480dafd01c41034", "mode": "100644", "path": "host-kernel/native-rust/page_allocator.rs", "sha256": "8e2af0cde06cbb70204540b493e8a0a66d5203195ed671235b64bed44d328bc5", "size": 21301},
    {"git_blob_sha1": "6513b579a64b4e0ccb9f42984a69fe0479adcd91", "mode": "100644", "path": "host-kernel/native-rust/page_owner_registry.rs", "sha256": "443d58fa5b2e423f538c6622ef04d8e34338abc43c5e0fd34811d52fc21f4869", "size": 13085},
    {"git_blob_sha1": "e2027dd013bca3e6174319585f748036aa435829", "mode": "100644", "path": "host-kernel/rocky/configs/native-rust-evidence.config", "sha256": "d415bee7fff27207bb27dcf7e57506723ceabd4b483b66c4f800d03263843af4", "size": 268},
    {"git_blob_sha1": "de815156d011d5620b886894a0eaa16dbe2af9ce", "mode": "100644", "path": "host-kernel/rocky/configs/rust-minimal.config", "sha256": "25dd0fc5647d8addfd650469aad758ca41d7e9599f0d02e34c2025e438114983", "size": 46},
    {"git_blob_sha1": "b4986af5b20b8b4e6d8193f31f338734f25e7297", "mode": "100644", "path": "scripts/rocky_rust_staging.py", "sha256": "59281bfb65924b6ffc563cbad4024849645d5dfab67533fc23b37d0b4895b68b", "size": 51590},
]

# This historical review always re-verifies the exact bc60 input objects above.
# Descendant commits may change a bound input only through an independently
# reviewed, exact old-to-new record in this closed list.  These records describe
# only the current descendant; every historical runtime record above stays fixed.
EXPECTED_CURRENT_OVERRIDES = [
    {
        "current_git_blob_sha1": "9a99536e3d09cb7a26aa9830236d89512de09633",
        "current_sha256": "e5f4dcebea346e516c86788de11aa203677a283a86df36acce5603fd540e4cdd",
        "current_size": 46889,
        "mode": "100644",
        "path": ".github/workflows/native-rust-host-modules-exact-build.yml",
        "runtime_git_blob_sha1": "b35eb64a336adcfc048bb73ff1bb8a7f0e044ab9",
        "runtime_sha256": "6566255ce3288d31e5a25047a3fe602171d80f868186f1a956b776592491cddf",
        "runtime_size": 26831,
    },
    {
        "current_git_blob_sha1": "f64e4f539b831815266c7f04413f1cd640aa7abe",
        "current_sha256": "48c6ba25186281a3a4fe4690c7520b02d8bbe43965e78d3301d2613477c3874f",
        "current_size": 848,
        "mode": "100644",
        "path": "host-kernel/kbuild/Kconfig",
        "runtime_git_blob_sha1": "3a7f9ca21d2921eb8b5a1e3caa0ca5e5a8116956",
        "runtime_sha256": "69f14cc7d347d6da3d6cbe0199e35fab72e40f6af3683df1c337efd449721296",
        "runtime_size": 823,
    },
    {
        "current_git_blob_sha1": "a17f033fed694044a34e37f9f361ba75e37f6e7c",
        "current_sha256": "e41b6df1dcd0d8007b23a0795de596e5c775e84f10fe02cf08edd5d199cd4b7a",
        "current_size": 5743,
        "mode": "100644",
        "path": "host-kernel/kbuild/stage-manifest.json",
        "runtime_git_blob_sha1": "8add3295a066294f788b5971f23be98b55407c33",
        "runtime_sha256": "7c2e2574b5fd1fc921b5e323b472680183d8bb2f7d9d39bdc3ef87208f434689",
        "runtime_size": 5743,
    },
    {
        "current_git_blob_sha1": "21483d8c8efbf58d1c6a1c3c99c083646be2f401",
        "current_sha256": "a8a71bc16bb84ab7394ef38879d445b849e823ec5944569d9a815c4398947ca3",
        "current_size": 285,
        "mode": "100644",
        "path": "host-kernel/rocky/configs/native-rust-evidence.config",
        "runtime_git_blob_sha1": "e2027dd013bca3e6174319585f748036aa435829",
        "runtime_sha256": "d415bee7fff27207bb27dcf7e57506723ceabd4b483b66c4f800d03263843af4",
        "runtime_size": 268,
    },
    {
        "current_git_blob_sha1": "529e790c2037caf334517983afd489e16f9882cf",
        "current_sha256": "47d5c0005ae7e8217b723b2c5f1a1f321f90e7aa4d26000aa44ffbf25e426656",
        "current_size": 49797,
        "mode": "100644",
        "path": "scripts/rocky_rust_staging.py",
        "runtime_git_blob_sha1": "b4986af5b20b8b4e6d8193f31f338734f25e7297",
        "runtime_sha256": "59281bfb65924b6ffc563cbad4024849645d5dfab67533fc23b37d0b4895b68b",
        "runtime_size": 51590,
    },
]

EXPECTED_ZIP_PATHS = tuple(sorted([
    ".ihk-smp-x86_64.ko.cmd", ".ihk-smp-x86_64.mod.cmd",
    ".ihk-smp-x86_64.mod.o.cmd", ".ihk-smp-x86_64.o.cmd",
    ".ihk.ko.cmd", ".ihk.mod.cmd", ".ihk.mod.o.cmd", ".ihk.o.cmd",
    ".ihk_smp_x86_64.o.cmd", ".mcctrl.ko.cmd", ".mcctrl.mod.cmd",
    ".mcctrl.mod.o.cmd", ".mcctrl.o.cmd", "PRECHECK_SHA256SUMS",
    "SHA256SUMS", "build-log.exit-code", "build.commands", "build.exit-code",
    "build.log", "build.phase", "built-module-artifacts.txt", "bzImage",
    "commit.sha", "ihk-smp-x86_64.ko", "ihk-smp-x86_64.ko.modinfo",
    "ihk-smp-x86_64.ko.modinfo-section", "ihk-smp-x86_64.ko.nm",
    "ihk-smp-x86_64.ko.readelf", "ihk.ko", "ihk.ko.modinfo",
    "ihk.ko.modinfo-section", "ihk.ko.nm", "ihk.ko.readelf",
    "kernel.release", "mcctrl.ko", "mcctrl.ko.modinfo",
    "mcctrl.ko.modinfo-section", "mcctrl.ko.nm", "mcctrl.ko.readelf",
    "module-targets.txt", "resolved.config", "stage-lock.json", "workflow-state",
]))
EXPECTED_PRECHECK_NAMES = tuple(sorted([
    "build-log.exit-code", "build.commands", "build.exit-code", "build.log",
    "build.phase", "built-module-artifacts.txt", "commit.sha",
    "ihk-smp-x86_64.ko", "ihk-smp-x86_64.ko.modinfo",
    "ihk-smp-x86_64.ko.modinfo-section", "ihk-smp-x86_64.ko.nm",
    "ihk-smp-x86_64.ko.readelf", "ihk.ko", "ihk.ko.modinfo",
    "ihk.ko.modinfo-section", "ihk.ko.nm", "ihk.ko.readelf", "mcctrl.ko",
    "mcctrl.ko.modinfo", "mcctrl.ko.modinfo-section", "mcctrl.ko.nm",
    "mcctrl.ko.readelf", "module-targets.txt", "workflow-state",
]))

EXPECTED_CMD_RECORDS = [
    {"inputs": ["drivers/misc/mckernel/ihk-smp-x86_64.o", "drivers/misc/mckernel/ihk-smp-x86_64.mod.o", ".module-common.o"], "kind": "final-link", "path": ".ihk-smp-x86_64.ko.cmd", "project_sources": [], "sha256": "2e608ceeeab99a11ff07135f014be4b0e87209cb864165fc41fdfeb6c0b87cd7", "target": "drivers/misc/mckernel/ihk-smp-x86_64.ko", "token_sha256": "834f7830582161bb6e085122199c86a4ce9a093333b0616d0ba9118f69a860bd", "tool": "ld.lld"},
    {"inputs": ["drivers/misc/mckernel/ihk_smp_x86_64.o"], "kind": "object-list", "path": ".ihk-smp-x86_64.mod.cmd", "project_sources": [], "sha256": "3a122749c2a69a7884c316d37e8e9474e7fc923a5edd3a863d520740bcb37bdf", "target": "drivers/misc/mckernel/ihk-smp-x86_64.mod", "token_sha256": "3cb5e23627fc72c80852298424f243210fe9b2ba32651ae75d8c63f625d157b3", "tool": "printf+awk"},
    {"inputs": ["drivers/misc/mckernel/ihk-smp-x86_64.mod.c"], "kind": "generated-mod-c-compile", "path": ".ihk-smp-x86_64.mod.o.cmd", "project_sources": [], "sha256": "e70cd4e3a09463aaff50590d90b81470d7ba7fafa05e75c9bc53aec895975d47", "target": "drivers/misc/mckernel/ihk-smp-x86_64.mod.o", "token_sha256": "799f45c76be810d5d9e5f2c45c75b57092158b67a2338248f0989d5eb3fc2b9c", "tool": "clang"},
    {"inputs": ["@drivers/misc/mckernel/ihk-smp-x86_64.mod"], "kind": "aggregate-link", "path": ".ihk-smp-x86_64.o.cmd", "project_sources": [], "sha256": "569329bc0644b43570f3e47eb8373374cbe9fa849f7d57c73fbc5e88ee801a6a", "target": "drivers/misc/mckernel/ihk-smp-x86_64.o", "token_sha256": "7b74bbf4474c02a1157465efa5c1ec3275deb8b80e1ab231d853eebe072b3b24", "tool": "ld.lld"},
    {"inputs": ["drivers/misc/mckernel/ihk.o", "drivers/misc/mckernel/ihk.mod.o", ".module-common.o"], "kind": "final-link", "path": ".ihk.ko.cmd", "project_sources": [], "sha256": "6739f4d1e9141d321835a6a607d735113def24054abf2d3b1ab5fed8843e23db", "target": "drivers/misc/mckernel/ihk.ko", "token_sha256": "c0e2cff79a1550244360c5b306874ad96e3f3c8452f6516a1bd3d293bf66736b", "tool": "ld.lld"},
    {"inputs": ["drivers/misc/mckernel/ihk.o"], "kind": "object-list", "path": ".ihk.mod.cmd", "project_sources": [], "sha256": "fa945babda5e444d0b5f783a79c166e2129003f439a761d608122106dcb4e93f", "target": "drivers/misc/mckernel/ihk.mod", "token_sha256": "f4ed8670467b3bbe0f580e598067f1509245b820af7eaf33d259ea85a7311d5a", "tool": "printf+awk"},
    {"inputs": ["drivers/misc/mckernel/ihk.mod.c"], "kind": "generated-mod-c-compile", "path": ".ihk.mod.o.cmd", "project_sources": [], "sha256": "445e9537ff3a49d197cf476fbc4a8cfef70c9148c1c78b10d763adc469f3ba58", "target": "drivers/misc/mckernel/ihk.mod.o", "token_sha256": "578869942a28d8231d43d9a3a82cdb4b851cea100fc04da53fad1cc4e0483b4a", "tool": "clang"},
    {"crate": "ihk", "inputs": [], "kind": "rust-compile", "path": ".ihk.o.cmd", "project_sources": ["abi/x86_64.rs", "ihk.rs", "ihk_ioctl.rs", "ikc_master.rs", "ikc_queue.rs", "os_registry.rs", "page_allocator.rs", "page_owner_registry.rs"], "root_source": "ihk.rs", "sha256": "9ee29b41b526d89d7aa0031779c2685d16f3b43c39cafa9676c02f38046309bd", "target": "drivers/misc/mckernel/ihk.o", "token_sha256": "ee0591dd23138244cc0b612a55e48aedbc78e14741c31bf59304f23c131be447", "tool": "rustc"},
    {"crate": "ihk_smp_x86_64", "inputs": [], "kind": "rust-compile", "path": ".ihk_smp_x86_64.o.cmd", "project_sources": ["ihk_smp_x86_64.rs"], "root_source": "ihk_smp_x86_64.rs", "sha256": "7cb42c947cd455b8018502afe5c9917515cb990c93752d21d0f87ccd4f5e94c3", "target": "drivers/misc/mckernel/ihk_smp_x86_64.o", "token_sha256": "7f108463faf039bfa79067a81b89a28ab62fad1fe7d1cee19fd10b1af1f07a20", "tool": "rustc"},
    {"inputs": ["drivers/misc/mckernel/mcctrl.o", "drivers/misc/mckernel/mcctrl.mod.o", ".module-common.o"], "kind": "final-link", "path": ".mcctrl.ko.cmd", "project_sources": [], "sha256": "dce809d695b2e46a132460f3719f5f1d1e1952b284a6f275290e1b04dcf9e9a4", "target": "drivers/misc/mckernel/mcctrl.ko", "token_sha256": "7822b1febd4e16ffe940041089a690632c591f70ae24048bc8a6b823ec533101", "tool": "ld.lld"},
    {"inputs": ["drivers/misc/mckernel/mcctrl.o"], "kind": "object-list", "path": ".mcctrl.mod.cmd", "project_sources": [], "sha256": "19eb040ff31e457fb875124258997b3be67b5e299312158b9f57d13c6221f1e5", "target": "drivers/misc/mckernel/mcctrl.mod", "token_sha256": "3a5b7728fb2224f9cf12ed899c4c106d919cd137d732abe47cce0644318d751c", "tool": "printf+awk"},
    {"inputs": ["drivers/misc/mckernel/mcctrl.mod.c"], "kind": "generated-mod-c-compile", "path": ".mcctrl.mod.o.cmd", "project_sources": [], "sha256": "2d72b6ecea643d5a4de556b435a43ab17941cea09e5dc0131d2f17cbb0de9242", "target": "drivers/misc/mckernel/mcctrl.mod.o", "token_sha256": "b2a310c7f9bda5405684b7956d06e40cf04e764b0488e5429f74d40b541b2834", "tool": "clang"},
    {"crate": "mcctrl", "inputs": [], "kind": "rust-compile", "path": ".mcctrl.o.cmd", "project_sources": ["mcctrl.rs"], "root_source": "mcctrl.rs", "sha256": "eb4dfd772f14a3e3ab8c2c014d123aaed3ca5b656cd781d70fef705fad1f5fd5", "target": "drivers/misc/mckernel/mcctrl.o", "token_sha256": "b9a25ab3b8319813228545ccdfa0fecbc41024030c29d659088ba3f71b3fc07a", "tool": "rustc"},
]

# This is a deliberately separate exact-shape semantic oracle.  Updating a
# manifest-derived command digest must not silently update the reviewed token
# vector; a future artifact requires an explicit review of this mapping.
EXACT_CMD_TOKEN_VECTOR_SHA256 = {
    ".ihk-smp-x86_64.ko.cmd": "834f7830582161bb6e085122199c86a4ce9a093333b0616d0ba9118f69a860bd",
    ".ihk-smp-x86_64.mod.cmd": "3cb5e23627fc72c80852298424f243210fe9b2ba32651ae75d8c63f625d157b3",
    ".ihk-smp-x86_64.mod.o.cmd": "799f45c76be810d5d9e5f2c45c75b57092158b67a2338248f0989d5eb3fc2b9c",
    ".ihk-smp-x86_64.o.cmd": "7b74bbf4474c02a1157465efa5c1ec3275deb8b80e1ab231d853eebe072b3b24",
    ".ihk.ko.cmd": "c0e2cff79a1550244360c5b306874ad96e3f3c8452f6516a1bd3d293bf66736b",
    ".ihk.mod.cmd": "f4ed8670467b3bbe0f580e598067f1509245b820af7eaf33d259ea85a7311d5a",
    ".ihk.mod.o.cmd": "578869942a28d8231d43d9a3a82cdb4b851cea100fc04da53fad1cc4e0483b4a",
    ".ihk.o.cmd": "ee0591dd23138244cc0b612a55e48aedbc78e14741c31bf59304f23c131be447",
    ".ihk_smp_x86_64.o.cmd": "7f108463faf039bfa79067a81b89a28ab62fad1fe7d1cee19fd10b1af1f07a20",
    ".mcctrl.ko.cmd": "7822b1febd4e16ffe940041089a690632c591f70ae24048bc8a6b823ec533101",
    ".mcctrl.mod.cmd": "3a5b7728fb2224f9cf12ed899c4c106d919cd137d732abe47cce0644318d751c",
    ".mcctrl.mod.o.cmd": "b2a310c7f9bda5405684b7956d06e40cf04e764b0488e5429f74d40b541b2834",
    ".mcctrl.o.cmd": "b9a25ab3b8319813228545ccdfa0fecbc41024030c29d659088ba3f71b3fc07a",
}

EXPECTED_CMD_STRUCTURE_SHA256 = {
    ".ihk-smp-x86_64.ko.cmd": "c5dbccb53388d8196945a89b3822fb489419c85638bc5a54fe4910423e03fa90",
    ".ihk-smp-x86_64.mod.cmd": "eb6784c3a6ba2ba5a1521aef21ebd592002dc199119a96ecf31cf85f9a2c7647",
    ".ihk-smp-x86_64.mod.o.cmd": "ed36bcaf09ab6191e939e0a35d40966282831815ef63adac41d4fc51b1c29e2c",
    ".ihk-smp-x86_64.o.cmd": "0f30d74080e228b476f460fbfadeeed9afbcca5a3d2e587c980a1324817a7346",
    ".ihk.ko.cmd": "9201991de24abef2481fe9333df3136e1f91a5eafa5ba29669b191cff0b275d9",
    ".ihk.mod.cmd": "53400849363ce9b6fff27b4a7b146e97c3f00d9ff4c7ffaf05147454949e831a",
    ".ihk.mod.o.cmd": "caa553d2c67d00a51f3e61f3a133b93ff2bf0c1cdef1a48ccd092b3ac6d8b38a",
    ".ihk.o.cmd": "7849c868bf948375d470290b62a4d06f81d982d20874c605bb437cb9861670ab",
    ".ihk_smp_x86_64.o.cmd": "e22878d73908bd67e41251e684a5a4198fedd8f193ed4425c5df8c6242b23358",
    ".mcctrl.ko.cmd": "f0c6c12e3f6556896188ee3ef40db517decfb491154faab810f818fc9c64046c",
    ".mcctrl.mod.cmd": "25ff995169641a64074ad81af8e8435325e3f47be462449a29ffa7f6ac8a7ebf",
    ".mcctrl.mod.o.cmd": "13ccd98b8bbab8db130e19ac0d56bce94039af04ee759d32f2e08c560233e625",
    ".mcctrl.o.cmd": "ad8bc0ed7f322c752634e79466da7cf073feac3d261ce83145ad74342059fd41",
}
EXPECTED_CMD_LINE_SHA256 = {
    ".ihk-smp-x86_64.ko.cmd": ("a323bbd36a6d64f28e20850b23e5a1f17f69b0d5726c9b1fee93c576a56c81e0", "37517e5f3dc66819f61f5a7bb8ace1921282415f10551d2defa5c3eb0985b570"),
    ".ihk-smp-x86_64.mod.cmd": ("5e8c60a27cce54352b3241b60cf5db268ff1e6951f9aae7d5e9463be4c2b9db2", "37517e5f3dc66819f61f5a7bb8ace1921282415f10551d2defa5c3eb0985b570"),
    ".ihk-smp-x86_64.mod.o.cmd": ("73a203036ba0adcbdd4b6e469d5a99029d1fae96daaa55f5635e037275884f89", "7b3f1bf58bbcfa969828c03307c7c8660638cacd81a0b1f7e0781d9a6fee22da"),
    ".ihk-smp-x86_64.o.cmd": ("476f0081115e371d508ecd6215bac86aa5d66fc8ab56950e302d48c03ac57334", "1cbccb7ceb5d6f41b4473a2035a3bde8534152d1c90414c15a2ca55ec2212147"),
    ".ihk.ko.cmd": ("2d344af4fccac5c5743ff6ddbb84d7e0a3e80655becc14dc77500fb1a41edde3", "37517e5f3dc66819f61f5a7bb8ace1921282415f10551d2defa5c3eb0985b570"),
    ".ihk.mod.cmd": ("aa4c3d40af1a807d0eca8424c4876d23d6f8275493c76612af170b251d5febda", "37517e5f3dc66819f61f5a7bb8ace1921282415f10551d2defa5c3eb0985b570"),
    ".ihk.mod.o.cmd": ("f13808049073671e789c7344a7e9e5b385c9c608391c9946ad7fc01959a9df6e", "ab3a0331b7424a2305f9bf18082f157846f53a87d610705dba01fc5bf241cc00"),
    ".ihk.o.cmd": ("37f7ae7035f2d42e818b587db965504d5b137f9933b5bd440dcceebf76ca81d5", "485814be653b79a80c08a0b8d6429e2f81b066fa2c7cb4d06cd5dc805e406d44"),
    ".ihk_smp_x86_64.o.cmd": ("d6da30ad7f7ee15e0c42ca8b93bfb54c9e731f5d26d100d03f66345053d842bc", "2f87f424474a8ee09cced21241f9166b011f0380060e67b2c8806428bff8cd13"),
    ".mcctrl.ko.cmd": ("80a243bdc6985157733647b52d5a87668beba87ec0e0fe1f7209490d92c3ce35", "37517e5f3dc66819f61f5a7bb8ace1921282415f10551d2defa5c3eb0985b570"),
    ".mcctrl.mod.cmd": ("f4e4296a5a8992785b1d6d6f877becc6a5ff400f094eb51ffa7687dc064d62d9", "37517e5f3dc66819f61f5a7bb8ace1921282415f10551d2defa5c3eb0985b570"),
    ".mcctrl.mod.o.cmd": ("0ebfd2476ae454ff33d9b2f506869fd852f423fe31effaecf6471efcd6a90cc1", "372c477d4011bdc2958fa92b92666398dd6af6fce67a7c7f8ba289b65fd017ec"),
    ".mcctrl.o.cmd": ("652ea1191569f54f1bad4599e538eec22403d0b520073ca5d6993709a1bde439", "3730eded92a0c389669f49e813e92d0668a85bac2463d58736e2bdd916f7e236"),
}
for expected_cmd_record in EXPECTED_CMD_RECORDS:
    expected_cmd_record["structure_sha256"] = EXPECTED_CMD_STRUCTURE_SHA256[
        expected_cmd_record["path"]
    ]
    expected_cmd_record["savedcmd_line_sha256"] = EXPECTED_CMD_LINE_SHA256[
        expected_cmd_record["path"]
    ][0]
    expected_cmd_record["trailing_lines_sha256"] = EXPECTED_CMD_LINE_SHA256[
        expected_cmd_record["path"]
    ][1]
del expected_cmd_record

EXPECTED_MODULE_FACTS = [
    {"binary": "ihk.ko", "binary_sha256": "ba8201909f30b7a8c1763d98e1a8e4398ff3167293cfc3d4be12050ffbc2609b", "binary_size": 688480, "crate": "ihk", "depends": [], "elf_class": "ELF64", "elf_machine": "EM_X86_64", "elf_type": "ET_REL", "import_namespaces": [], "kconfig_symbol": "CONFIG_MCKERNEL_IHK_RUST", "license": "GPL v2", "modinfo_record_count": 11, "name": "ihk", "parameters": [], "production_namespace": "MCKERNEL_IHK_V1", "provider_relocation_count": 4, "provider_relocation_sections": [".rela.debug_info", ".rela__ksymtab_gpl"], "provider_symbol": "defined-exported"},
    {"binary": "ihk-smp-x86_64.ko", "binary_sha256": "26fe011de606930d6c5d0d076403c66c0ca95b592a2b937330a5b7acd5706934", "binary_size": 645024, "crate": "ihk_smp_x86_64", "depends": ["ihk"], "elf_class": "ELF64", "elf_machine": "EM_X86_64", "elf_type": "ET_REL", "import_namespaces": ["MCKERNEL_IHK_V1"], "kconfig_symbol": "CONFIG_MCKERNEL_IHK_SMP_X86_64_RUST", "license": "Dual BSD/GPL", "modinfo_record_count": 21, "name": "ihk_smp_x86_64", "parameters": [{"description": "IHK reserved memory in MBs", "name": "ihk_mem", "type": "ulong"}, {"description": "IHK reserved CPU cores", "name": "ihk_cores", "type": "uint"}, {"description": "IHK IKC IPI to be scanned from this IRQ vector", "name": "ihk_start_irq", "type": "uint"}, {"description": "IHK reserved physical memory start address", "name": "ihk_phys_start", "type": "ulong"}, {"description": "IHK trampoline page physical address", "name": "ihk_trampoline", "type": "ulong"}, {"description": "Target CPU of IHK IKC IRQ", "name": "ihk_ikc_irq_core", "type": "uint"}], "production_namespace": None, "provider_relocation_count": 2, "provider_relocation_sections": [".rela.text", ".rela.init.text"], "provider_symbol": "undefined-import"},
    {"binary": "mcctrl.ko", "binary_sha256": "2995c20318ecd2f329b0125937a13e0fca855fec3d470b138f0527244effa5f5", "binary_size": 637392, "crate": "mcctrl", "depends": ["ihk"], "elf_class": "ELF64", "elf_machine": "EM_X86_64", "elf_type": "ET_REL", "import_namespaces": ["MCKERNEL_IHK_V1"], "kconfig_symbol": "CONFIG_MCKERNEL_MCCTRL_RUST", "license": "GPL v2", "modinfo_record_count": 9, "name": "mcctrl", "parameters": [], "production_namespace": None, "provider_relocation_count": 2, "provider_relocation_sections": [".rela.text", ".rela.init.text"], "provider_symbol": "undefined-import"},
]

EXPECTED_DIRECT_MODINFO = {
    "ihk.ko": [
        "version=1.7.0rc4", "author=McKernel Rust port",
        "description=Native Rust IHK host core", "license=GPL v2", "name=ihk",
        "intree=Y", "depends=", "srcversion=A966ACFF0E56DC23D4F9D8B",
        "rhelversion=10.2", "vermagic=6.12.0 SMP preempt mod_unload ", "retpoline=Y",
    ],
    "ihk-smp-x86_64.ko": [
        "parm=ihk_mem:IHK reserved memory in MBs", "parmtype=ihk_mem:ulong",
        "import_ns=MCKERNEL_IHK_V1", "parm=ihk_cores:IHK reserved CPU cores",
        "parmtype=ihk_cores:uint",
        "parm=ihk_start_irq:IHK IKC IPI to be scanned from this IRQ vector",
        "parmtype=ihk_start_irq:uint",
        "parm=ihk_phys_start:IHK reserved physical memory start address",
        "parmtype=ihk_phys_start:ulong",
        "parm=ihk_trampoline:IHK trampoline page physical address",
        "parmtype=ihk_trampoline:ulong",
        "parm=ihk_ikc_irq_core:Target CPU of IHK IKC IRQ",
        "parmtype=ihk_ikc_irq_core:uint", "license=Dual BSD/GPL",
        "name=ihk_smp_x86_64", "intree=Y", "depends=ihk",
        "srcversion=CC9191281B7CBAD878935B9", "rhelversion=10.2",
        "vermagic=6.12.0 SMP preempt mod_unload ", "retpoline=Y",
    ],
    "mcctrl.ko": [
        "import_ns=MCKERNEL_IHK_V1", "license=GPL v2", "name=mcctrl", "intree=Y",
        "depends=ihk", "srcversion=213563A224DD7050D6CCC1F", "rhelversion=10.2",
        "vermagic=6.12.0 SMP preempt mod_unload ", "retpoline=Y",
    ],
}

EXPECTED_ELF_SECTION_SHAPES = {
    "ihk.ko": {
        ".text": {"alignment": 16, "entry_size": 0, "flags": 6, "size": 1896, "type": 1},
        ".init.text": {"alignment": 16, "entry_size": 0, "flags": 6, "size": 342, "type": 1},
        ".modinfo": {"alignment": 1, "entry_size": 0, "flags": 2, "size": 227, "type": 1},
        ".rodata": {"alignment": 8, "entry_size": 0, "flags": 50, "size": 586, "type": 1},
        "__ksymtab_gpl": {"alignment": 4, "entry_size": 0, "flags": 2, "size": 12, "type": 1},
        "__ksymtab_strings": {"alignment": 1, "entry_size": 1, "flags": 50, "size": 42, "type": 1},
        ".rela__ksymtab_gpl": {"alignment": 8, "entry_size": 24, "flags": 64, "size": 72, "type": 4},
    },
    "ihk-smp-x86_64.ko": {
        ".text": {"alignment": 16, "entry_size": 0, "flags": 6, "size": 584, "type": 1},
        ".init.text": {"alignment": 16, "entry_size": 0, "flags": 6, "size": 309, "type": 1},
        ".modinfo": {"alignment": 1, "entry_size": 0, "flags": 2, "size": 670, "type": 1},
        ".rodata": {"alignment": 8, "entry_size": 0, "flags": 50, "size": 384, "type": 1},
        "__param": {"alignment": 8, "entry_size": 0, "flags": 2, "size": 240, "type": 1},
        ".rela__param": {"alignment": 8, "entry_size": 24, "flags": 64, "size": 576, "type": 4},
    },
    "mcctrl.ko": {
        ".text": {"alignment": 16, "entry_size": 0, "flags": 6, "size": 704, "type": 1},
        ".init.text": {"alignment": 16, "entry_size": 0, "flags": 6, "size": 391, "type": 1},
        ".modinfo": {"alignment": 1, "entry_size": 0, "flags": 2, "size": 178, "type": 1},
    },
}

EXPECTED_ELF_SYMTAB_INFO = {
    "ihk.ko": 66,
    "ihk-smp-x86_64.ko": 52,
    "mcctrl.ko": 51,
}

EXPECTED_ELF_STRUCTURE_SHA256 = {
    "ihk.ko": "27b83b008f0b562c77fe4edbccf23ba3040aba37cc7427dadc7d6bf218ef0eb0",
    "ihk-smp-x86_64.ko": "b5812968769adae4f446fc80e418ac3a540f0cb294ce093e5e2cb38c76c3156f",
    "mcctrl.ko": "06d6d68bf181fb91cf5c403fc499faa76b91cbb930bc667cc7740f59793710b9",
}

EXPECTED_THIS_MODULE = {
    "ihk.ko": {
        "name": "ihk", "section_index": 44,
        "section_sha256": "7a957f569e10a775b948a693b4e79231981ea4861415e0abf0bc415dcf1f3c0e",
        "symbol_index": 106,
    },
    "ihk-smp-x86_64.ko": {
        "name": "ihk_smp_x86_64", "section_index": 43,
        "section_sha256": "9e89faaa64f25bb1c474f84939dbcc2d7514c14282963c4e5c75248f583044c9",
        "symbol_index": 79,
    },
    "mcctrl.ko": {
        "name": "mcctrl", "section_index": 41,
        "section_sha256": "be608114c87535eddac6f82d153707fcf166ee6bde263aaf4ce541891653f512",
        "symbol_index": 71,
    },
}

EXPECTED_SMP_PARAMETER_LAYOUT = [
    {"name": "ihk_mem", "name_offset": 86, "ops": "param_ops_ulong", "ops_index": 80, "storage": "_RNvCs5Iw3aBAMJ7i_14ihk_smp_x86_647IHK_MEM", "storage_index": 81, "storage_size": 8, "storage_value": 32, "type": "ulong"},
    {"name": "ihk_cores", "name_offset": 15, "ops": "param_ops_uint", "ops_index": 85, "storage": "_RNvCs5Iw3aBAMJ7i_14ihk_smp_x86_649IHK_CORES", "storage_index": 86, "storage_size": 4, "storage_value": 40, "type": "uint"},
    {"name": "ihk_start_irq", "name_offset": 55, "ops": "param_ops_uint", "ops_index": 85, "storage": "_RNvCs5Iw3aBAMJ7i_14ihk_smp_x86_6413IHK_START_IRQ", "storage_index": 77, "storage_size": 4, "storage_value": 0, "type": "uint"},
    {"name": "ihk_phys_start", "name_offset": 25, "ops": "param_ops_ulong", "ops_index": 80, "storage": "_RNvCs5Iw3aBAMJ7i_14ihk_smp_x86_6414IHK_PHYS_START", "storage_index": 82, "storage_size": 8, "storage_value": 8, "type": "ulong"},
    {"name": "ihk_trampoline", "name_offset": 0, "ops": "param_ops_ulong", "ops_index": 80, "storage": "_RNvCs5Iw3aBAMJ7i_14ihk_smp_x86_6414IHK_TRAMPOLINE", "storage_index": 83, "storage_size": 8, "storage_value": 16, "type": "ulong"},
    {"name": "ihk_ikc_irq_core", "name_offset": 69, "ops": "param_ops_uint", "ops_index": 85, "storage": "_RNvCs5Iw3aBAMJ7i_14ihk_smp_x86_6416IHK_IKC_IRQ_CORE", "storage_index": 87, "storage_size": 4, "storage_value": 24, "type": "uint"},
]

EXPECTED_MODULE_NOTES = {
    "ihk.ko": {
        "build_id": "1bc8df16d28cf1d55eb653fbcadb097f256a40e0",
        "build_id_index": 54,
        "build_id_sha256": "0d2afb84f4f41eb36a17066cebaaad0926396bc8f09339a8234ab4d3bfc6c6ec",
        "linux_index": 53,
        "property_index": 55,
    },
    "ihk-smp-x86_64.ko": {
        "build_id": "8cfeae7e8aa9821c14a8b8b616d1c8b7ac3ec02f",
        "build_id_index": 53,
        "build_id_sha256": "e1bff8bc2b929b82243dd1d441258449d8d136da0f15b8b255cec82a83959e20",
        "linux_index": 52,
        "property_index": 54,
    },
    "mcctrl.ko": {
        "build_id": "33c45f858a650f09239d648f4b5da64320f21b68",
        "build_id_index": 51,
        "build_id_sha256": "99324206be3c7b80292651aacedfbdf33eaf9cf4e9531ceaa8e0d033a39cd597",
        "linux_index": 50,
        "property_index": 52,
    },
}

LINUX_NOTE_SHA256 = "e3ddbe0735c86b1ff2161cd10da98ac9a27462d5d0794d2ce7fd14635edd07b5"
GNU_PROPERTY_NOTE_SHA256 = "5037a9afed5475133c29907c72d05abaed2f741d404c85bf5e944ffded789bac"

X86_64_RELOCATION_WIDTHS = {
    1: 8,   # R_X86_64_64
    2: 4,   # R_X86_64_PC32
    4: 4,   # R_X86_64_PLT32
    10: 4,  # R_X86_64_32
    11: 4,  # R_X86_64_32S
}

EXPECTED_RELOCATION_SECTION_SYMBOLS = {
    "ihk.ko": [
        {
            "binding": 0, "index": 64, "name": "", "name_offset": 0, "other": 0,
            "section": "__ksymtab_strings", "size": 0, "type": 3, "value": 0,
        },
    ],
    "ihk-smp-x86_64.ko": [],
    "mcctrl.ko": [],
}

EXPECTED_PROVIDER_RELOCATIONS = {
    "ihk.ko": [
        {"addend": 0, "offset": 1466, "relocation_section": ".rela.debug_info", "symbol": "ihk_provider_lifecycle_v1", "symbol_index": 90, "symbol_section": ".rodata", "target_section": ".debug_info", "type": 1},
        {"addend": 0, "offset": 0, "relocation_section": ".rela__ksymtab_gpl", "symbol": "ihk_provider_lifecycle_v1", "symbol_index": 90, "symbol_section": ".rodata", "target_section": "__ksymtab_gpl", "type": 2},
        {"addend": 0, "offset": 4, "relocation_section": ".rela__ksymtab_gpl", "symbol": "", "symbol_index": 64, "symbol_section": "__ksymtab_strings", "target_section": "__ksymtab_gpl", "type": 2},
        {"addend": 26, "offset": 8, "relocation_section": ".rela__ksymtab_gpl", "symbol": "", "symbol_index": 64, "symbol_section": "__ksymtab_strings", "target_section": "__ksymtab_gpl", "type": 2},
    ],
    "ihk-smp-x86_64.ko": [
        {"addend": -4, "offset": 251, "relocation_section": ".rela.text", "symbol": "ihk_provider_lifecycle_v1", "symbol_index": 58, "symbol_section": "", "target_section": ".text", "type": 2},
        {"addend": -4, "offset": 28, "relocation_section": ".rela.init.text", "symbol": "ihk_provider_lifecycle_v1", "symbol_index": 58, "symbol_section": "", "target_section": ".init.text", "type": 2},
    ],
    "mcctrl.ko": [
        {"addend": -4, "offset": 30, "relocation_section": ".rela.text", "symbol": "ihk_provider_lifecycle_v1", "symbol_index": 51, "symbol_section": "", "target_section": ".text", "type": 2},
        {"addend": -4, "offset": 31, "relocation_section": ".rela.init.text", "symbol": "ihk_provider_lifecycle_v1", "symbol_index": 51, "symbol_section": "", "target_section": ".init.text", "type": 2},
    ],
}

EXPECTED_PROVIDER_OBJECT = {
    "binary": "ihk.ko",
    "content_hex": "01",
    "section": ".rodata",
    "size": 1,
    "symbol": "ihk_provider_lifecycle_v1",
    "value": 560,
}


class BuildReviewError(RuntimeError):
    """Raised when review, repository, or artifact bytes fail closed."""


def reject_duplicate_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise BuildReviewError("duplicate JSON key: {!r}".format(key))
        result[key] = value
    return result


def canonical_json_bytes(value):
    try:
        text = json.dumps(
            value, allow_nan=False, ensure_ascii=True, separators=(",", ":"), sort_keys=True
        )
    except (TypeError, ValueError) as exc:
        raise BuildReviewError("value is not canonical JSON: {}".format(exc))
    return (text + "\n").encode("ascii")


def read_json_bytes(data, label, require_canonical=False):
    try:
        value = json.loads(data.decode("ascii"), object_pairs_hook=reject_duplicate_pairs)
    except (UnicodeError, ValueError) as exc:
        raise BuildReviewError("{} is not valid JSON: {}".format(label, exc))
    if type(value) is not dict:
        raise BuildReviewError("{} must be a JSON object".format(label))
    if require_canonical and data != canonical_json_bytes(value):
        raise BuildReviewError("{} is not canonical JSON".format(label))
    return value


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def exact_keys(value, expected, label):
    if type(value) is not dict or set(value) != set(expected):
        raise BuildReviewError("{} has unexpected keys".format(label))
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
            same_value_and_type(left, right) for left, right in zip(actual, expected)
        )
    return actual == expected


def require_exact(actual, expected, label):
    if not same_value_and_type(actual, expected):
        raise BuildReviewError("{} differs: {!r} != {!r}".format(label, actual, expected))


def require_positive_int(value, label):
    if type(value) is not int or value < 1:
        raise BuildReviewError("{} is not a positive integer".format(label))


def safe_relative_path(value, label):
    if not isinstance(value, str):
        raise BuildReviewError("{} is not text".format(label))
    path = PurePosixPath(value)
    if (
        path.is_absolute()
        or not path.parts
        or "\\" in value
        or "\x00" in value
        or "//" in value
        or any(part in ("", ".", "..") for part in value.split("/"))
    ):
        raise BuildReviewError("{} is unsafe: {!r}".format(label, value))
    return value


def regular_file(path, label):
    raw = str(path)
    raw_parts = raw.split(os.sep)
    comparable_parts = raw_parts[1:] if os.path.isabs(raw) else raw_parts
    if (
        not raw
        or "\x00" in raw
        or "\\" in raw
        or any(part in ("", ".", "..") for part in comparable_parts)
    ):
        raise BuildReviewError("{} path is unsafe".format(label))
    requested = Path(os.path.abspath(raw))
    current = Path(requested.anchor)
    parts = requested.parts[1:] if requested.anchor else requested.parts
    try:
        status = current.lstat()
    except OSError as exc:
        raise BuildReviewError("cannot inspect {}: {}".format(label, exc))
    for index, part in enumerate(parts):
        if part in ("", ".", ".."):
            raise BuildReviewError("{} path is unsafe".format(label))
        current = current / part
        try:
            status = current.lstat()
        except OSError as exc:
            raise BuildReviewError("cannot inspect {}: {}".format(label, exc))
        if stat.S_ISLNK(status.st_mode):
            raise BuildReviewError("{} traverses a symlink".format(label))
        if index + 1 < len(parts) and not stat.S_ISDIR(status.st_mode):
            raise BuildReviewError("{} has a non-directory ancestor".format(label))
    if not stat.S_ISREG(status.st_mode):
        raise BuildReviewError("{} is not a regular file".format(label))
    return requested


def read_regular_file_once(path, label, expected_mode=None):
    requested = regular_file(path, label)
    initial = requested.lstat()
    if expected_mode is not None and stat.S_IMODE(initial.st_mode) != expected_mode:
        raise BuildReviewError(
            "{} mode is not {:04o}".format(label, expected_mode)
        )
    directory_flags = os.O_RDONLY
    if hasattr(os, "O_DIRECTORY"):
        directory_flags |= os.O_DIRECTORY
    if hasattr(os, "O_NOFOLLOW"):
        directory_flags |= os.O_NOFOLLOW
    file_flags = os.O_RDONLY
    if hasattr(os, "O_BINARY"):
        file_flags |= os.O_BINARY
    if hasattr(os, "O_NOFOLLOW"):
        file_flags |= os.O_NOFOLLOW
    directory_descriptor = None
    try:
        directory_descriptor = os.open(requested.anchor, directory_flags)
        for part in requested.parts[1:-1]:
            child = os.open(part, directory_flags, dir_fd=directory_descriptor)
            os.close(directory_descriptor)
            directory_descriptor = child
        descriptor = os.open(requested.parts[-1], file_flags, dir_fd=directory_descriptor)
    except OSError as exc:
        raise BuildReviewError("cannot open {}: {}".format(label, exc))
    finally:
        if directory_descriptor is not None:
            os.close(directory_descriptor)
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode):
            raise BuildReviewError("{} changed away from a regular file".format(label))
        if expected_mode is not None and stat.S_IMODE(before.st_mode) != expected_mode:
            raise BuildReviewError(
                "{} mode is not {:04o}".format(label, expected_mode)
            )
        chunks = []
        while True:
            chunk = os.read(descriptor, 1024 * 1024)
            if not chunk:
                break
            chunks.append(chunk)
        after = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    identity_before = (
        before.st_dev, before.st_ino, before.st_mode, before.st_size, before.st_mtime_ns
    )
    identity_after = (
        after.st_dev, after.st_ino, after.st_mode, after.st_size, after.st_mtime_ns
    )
    identity_initial = (
        initial.st_dev, initial.st_ino, initial.st_mode, initial.st_size, initial.st_mtime_ns
    )
    data = b"".join(chunks)
    if identity_initial != identity_before or identity_before != identity_after or len(data) != after.st_size:
        raise BuildReviewError("{} changed while it was read".format(label))
    return data


def repository_file(repo, relative, label):
    relative = safe_relative_path(relative, label + " path")
    root = repo.resolve()
    requested = root.joinpath(*PurePosixPath(relative).parts)
    resolved = requested.resolve()
    try:
        common = os.path.commonpath((str(root), str(resolved)))
    except ValueError:
        common = ""
    if Path(common) != root:
        raise BuildReviewError("{} escapes the repository".format(label))
    if requested != resolved:
        raise BuildReviewError("{} traverses a symlink".format(label))
    return regular_file(requested, label)


def run_git(repo, arguments, allow_failure=False):
    environment = dict(
        (name, value) for name, value in os.environ.items()
        if not name.startswith("GIT_")
    )
    environment["GIT_NO_REPLACE_OBJECTS"] = "1"
    environment["GIT_GRAFT_FILE"] = os.devnull
    environment["GIT_CONFIG_GLOBAL"] = os.devnull
    environment["GIT_CONFIG_NOSYSTEM"] = "1"
    environment["LC_ALL"] = "C"
    try:
        completed = subprocess.run(
            ["git", "--no-replace-objects", "-C", str(repo)] + list(arguments),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=environment,
        )
    except OSError as exc:
        raise BuildReviewError("git failed to execute: {}".format(exc))
    if completed.returncode != 0 and not allow_failure:
        raise BuildReviewError(
            "git command failed: {}".format(
                completed.stderr.decode("utf-8", errors="replace").strip()
            )
        )
    return completed


def discover_review(repo, explicit=None):
    repo = repo.resolve()
    if explicit is not None:
        path = explicit if explicit.is_absolute() else repo / explicit
        try:
            relative = path.relative_to(repo).as_posix()
        except ValueError:
            raise BuildReviewError("explicit review manifest is outside the repository")
        return repository_file(repo, relative, "review manifest")
    candidates = sorted((repo / REVIEW_DIRECTORY).glob(REVIEW_GLOB))
    if len(candidates) != 1:
        raise BuildReviewError(
            "expected exactly one {} manifest, found {}".format(REVIEW_GLOB, len(candidates))
        )
    relative = candidates[0].relative_to(repo).as_posix()
    return repository_file(repo, relative, "review manifest")


def load_review(path):
    data = read_regular_file_once(path, "review manifest")
    require_exact(sha256_bytes(data), REVIEW_SHA256, "review manifest digest")
    review = read_json_bytes(data, "review manifest", require_canonical=True)
    validate_historical_projection(review)
    return review


def validate_historical_projection(review):
    """Lock every historical fact while excluding only the current-port policy."""
    exact_keys(review, EXPECTED_REVIEW_KEYS, "review")
    historical_projection = dict(review)
    del historical_projection["current_repository_input_policy"]
    require_exact(
        sha256_bytes(canonical_json_bytes(historical_projection)),
        EXPECTED_HISTORICAL_PROJECTION_SHA256,
        "historical review projection digest",
    )


def validate_current_repository_input_policy(review):
    """Validate the closed old-to-new records for the current descendant."""
    policy = exact_keys(
        review["current_repository_input_policy"],
        {
            "bound_input_count", "current_override_count", "current_overrides",
            "historical_runtime_inputs_immutable", "relationship",
            "require_head_index_worktree_equality", "runtime_identity_claimed",
        },
        "current repository input policy",
    )
    require_exact(policy["bound_input_count"], len(EXPECTED_COMMITTED_INPUTS), "input count")
    require_exact(
        policy["current_override_count"],
        len(EXPECTED_CURRENT_OVERRIDES),
        "current override count",
    )
    require_exact(
        policy["current_overrides"],
        EXPECTED_CURRENT_OVERRIDES,
        "current overrides",
    )
    require_exact(
        policy["historical_runtime_inputs_immutable"],
        True,
        "historical runtime input policy",
    )
    require_exact(policy["relationship"], "descendant-or-equal", "relationship")
    require_exact(policy["require_head_index_worktree_equality"], True, "input equality")
    require_exact(policy["runtime_identity_claimed"], False, "runtime identity claim")

    committed_by_path = {row["path"]: row for row in EXPECTED_COMMITTED_INPUTS}
    if len(committed_by_path) != len(EXPECTED_COMMITTED_INPUTS):
        raise BuildReviewError("committed input paths are not unique")
    override_paths = set()
    for index, row in enumerate(policy["current_overrides"]):
        label = "current override {}".format(index)
        exact_keys(
            row,
            {
                "current_git_blob_sha1", "current_sha256", "current_size", "mode",
                "path", "runtime_git_blob_sha1", "runtime_sha256", "runtime_size",
            },
            label,
        )
        path = safe_relative_path(row["path"], label + " path")
        if path in override_paths:
            raise BuildReviewError("current override paths are not unique")
        override_paths.add(path)
        if path not in committed_by_path:
            raise BuildReviewError("{} is not a reviewed runtime input".format(label))
        runtime_row = committed_by_path[path]
        require_exact(row["mode"], runtime_row["mode"], label + " mode")
        require_exact(
            row["runtime_git_blob_sha1"],
            runtime_row["git_blob_sha1"],
            label + " runtime blob",
        )
        require_exact(
            row["runtime_sha256"], runtime_row["sha256"], label + " runtime digest"
        )
        require_exact(
            row["runtime_size"], runtime_row["size"], label + " runtime size"
        )
        if (
            not isinstance(row["current_git_blob_sha1"], str)
            or HEX_SHA1.fullmatch(row["current_git_blob_sha1"]) is None
        ):
            raise BuildReviewError("{} current blob is invalid".format(label))
        if (
            not isinstance(row["current_sha256"], str)
            or HEX_SHA256.fullmatch(row["current_sha256"]) is None
        ):
            raise BuildReviewError("{} current digest is invalid".format(label))
        if type(row["current_size"]) is not int or row["current_size"] < 0:
            raise BuildReviewError("{} current size is invalid".format(label))
        if (
            row["current_git_blob_sha1"] == row["runtime_git_blob_sha1"]
            and row["current_sha256"] == row["runtime_sha256"]
            and row["current_size"] == row["runtime_size"]
        ):
            raise BuildReviewError("{} does not describe a changed input".format(label))


def validate_review_object(review):
    exact_keys(review, EXPECTED_REVIEW_KEYS, "review")
    require_exact(review["schema_version"], SCHEMA_VERSION, "schema version")
    require_exact(review["review_id"], REVIEW_ID, "review id")
    require_exact(
        review["review_kind"],
        "historical-exact-native-rust-build-bounded-pass",
        "review kind",
    )
    require_exact(review["claims"], EXPECTED_CLAIMS, "bounded claims")
    require_exact(review["caveats"], EXPECTED_CAVEATS, "caveats")
    require_exact(
        review["remaining_prerequisites"],
        EXPECTED_REMAINING_PREREQUISITES,
        "remaining prerequisites",
    )

    source = exact_keys(
        review["source_artifact"],
        {"artifact", "durable_archive", "expires_at", "github", "retention_days"},
        "source artifact",
    )
    require_exact(source["durable_archive"], False, "durable archive")
    require_exact(source["retention_days"], 30, "retention")
    require_exact(source["expires_at"], ARTIFACT_EXPIRES_AT, "expiry")
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
        {"job_id", "repository", "run_attempt", "run_id", "runtime_head_sha", "runtime_tree_sha"},
        "GitHub identity",
    )
    require_exact(github["job_id"], GITHUB_JOB_ID, "job id")
    require_exact(github["repository"], GITHUB_REPOSITORY, "repository")
    require_exact(github["run_attempt"], GITHUB_RUN_ATTEMPT, "run attempt")
    require_exact(github["run_id"], GITHUB_RUN_ID, "run id")
    require_exact(github["runtime_head_sha"], RUNTIME_HEAD_SHA, "GitHub head")
    require_exact(github["runtime_tree_sha"], RUNTIME_TREE_SHA, "GitHub tree")

    runtime = exact_keys(
        review["runtime_candidate"],
        {"committed_inputs", "container", "head_sha", "tree_sha"},
        "runtime candidate",
    )
    require_exact(runtime["head_sha"], RUNTIME_HEAD_SHA, "runtime head")
    require_exact(runtime["tree_sha"], RUNTIME_TREE_SHA, "runtime tree")
    require_exact(runtime["committed_inputs"], EXPECTED_COMMITTED_INPUTS, "committed inputs")
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

    facts = exact_keys(
        review["verified_facts"],
        {
            "artifact_state", "build_commands", "cmd_records", "configuration",
            "module_outputs", "output_set", "stage_lock",
        },
        "verified facts",
    )
    require_exact(
        facts["artifact_state"],
        {
            "build_exit_code": 0,
            "build_log_exit_code": 0,
            "build_phase": "complete",
            "kernel_release": "6.12.0",
            "workflow_state": "bootstrap-complete",
        },
        "artifact state",
    )
    commands = exact_keys(
        facts["build_commands"], {"commands", "count", "ordered"}, "build commands"
    )
    require_exact(commands["count"], 3, "build command count")
    require_exact(commands["ordered"], True, "build command ordering")
    require_exact(
        commands["commands"],
        [
            "make -C {} O=/__w/_temp/native-rust-build ARCH=x86_64 LLVM=1 rustavailable".format(SOURCE_ROOT),
            "make -C {} O=/__w/_temp/native-rust-build ARCH=x86_64 LLVM=1 -j2 bzImage".format(SOURCE_ROOT),
            "make -C {} O=/__w/_temp/native-rust-build ARCH=x86_64 LLVM=1 -j2 {}".format(SOURCE_ROOT, " ".join(EXPECTED_MODULE_TARGETS)),
        ],
        "build commands",
    )
    require_exact(facts["cmd_records"], EXPECTED_CMD_RECORDS, "command records")
    require_exact(
        facts["configuration"],
        {"required_symbols": EXPECTED_CONFIG, "resolved_path": "resolved.config", "stable_resolution_claimed": False},
        "configuration",
    )
    require_exact(facts["module_outputs"], EXPECTED_MODULE_FACTS, "module outputs")
    require_exact(
        facts["output_set"],
        {
            "built_modules": EXPECTED_BUILT_MODULES,
            "bzimage_present": True,
            "module_count": 3,
            "module_targets": EXPECTED_MODULE_TARGETS,
        },
        "output set",
    )
    require_exact(
        facts["stage_lock"],
        {
            "credit_eligible": False,
            "file_count": len(EXPECTED_STAGE_FILES),
            "files": EXPECTED_STAGE_FILES,
            "manifest_sha256": "7c2e2574b5fd1fc921b5e323b472680183d8bb2f7d9d39bdc3ef87208f434689",
            "profile_id": "rocky-10.2-native-rust-host-modules-v1",
            "purpose": "compiler-evidence-only",
        },
        "stage lock",
    )

    inner = exact_keys(
        review["inner_closure"],
        {"final_manifest_sha256", "final_records", "precheck_manifest_sha256", "precheck_records"},
        "inner closure",
    )
    if type(inner["final_records"]) is not list or type(inner["precheck_records"]) is not list:
        raise BuildReviewError("inner closure records must be lists")
    require_positive_int(len(inner["final_records"]), "final record count")
    require_positive_int(len(inner["precheck_records"]), "precheck record count")
    require_exact(len(inner["final_records"]), len(EXPECTED_ZIP_PATHS) - 1, "final record count")
    require_exact(len(inner["precheck_records"]), len(EXPECTED_PRECHECK_NAMES), "precheck record count")
    for label, rows, expected_names in (
        ("final", inner["final_records"], sorted(set(EXPECTED_ZIP_PATHS) - {"SHA256SUMS"})),
        ("precheck", inner["precheck_records"], list(EXPECTED_PRECHECK_NAMES)),
    ):
        for index, row in enumerate(rows):
            exact_keys(row, {"path", "sha256", "size"}, "{} record {}".format(label, index))
            safe_relative_path(row["path"], label + " path")
            if not isinstance(row["sha256"], str) or HEX_SHA256.fullmatch(row["sha256"]) is None:
                raise BuildReviewError("{} record digest is invalid".format(label))
            if type(row["size"]) is not int or row["size"] < 0:
                raise BuildReviewError("{} record size is invalid".format(label))
        require_exact([row["path"] for row in rows], expected_names, label + " paths")
    for key in ("final_manifest_sha256", "precheck_manifest_sha256"):
        if not isinstance(inner[key], str) or HEX_SHA256.fullmatch(inner[key]) is None:
            raise BuildReviewError("{} is invalid".format(key))

    closure = exact_keys(
        review["zip_closure"],
        {
            "archive_comment_empty", "compressed_payload_size", "crc_verified",
            "duplicate_paths", "entry_count", "entry_index_sha256", "paths",
            "regular_mode", "stored_payload_size", "unsafe_paths",
        },
        "ZIP closure",
    )
    require_exact(closure["archive_comment_empty"], True, "ZIP comment")
    require_exact(closure["crc_verified"], True, "ZIP CRC")
    require_exact(closure["duplicate_paths"], [], "ZIP duplicate paths")
    require_exact(closure["entry_count"], len(EXPECTED_ZIP_PATHS), "ZIP entry count")
    require_exact(closure["paths"], list(EXPECTED_ZIP_PATHS), "ZIP paths")
    require_exact(closure["regular_mode"], "100644", "ZIP mode")
    require_exact(closure["unsafe_paths"], [], "ZIP unsafe paths")
    require_positive_int(closure["compressed_payload_size"], "compressed payload size")
    require_exact(
        closure["compressed_payload_size"], closure["stored_payload_size"], "stored payload size"
    )
    if not isinstance(closure["entry_index_sha256"], str) or HEX_SHA256.fullmatch(
        closure["entry_index_sha256"]
    ) is None:
        raise BuildReviewError("ZIP entry index digest is invalid")
    validate_current_repository_input_policy(review)
    return review


def git_tree_record(repo, revision, path, label):
    completed = run_git(repo, ["ls-tree", revision, "--", path])
    rows = completed.stdout.decode("ascii").splitlines()
    if len(rows) != 1:
        raise BuildReviewError("{} has no unique tree entry".format(label))
    match = re.fullmatch(r"(100644) blob ([0-9a-f]{40})\t(.+)", rows[0])
    if match is None or match.group(3) != path:
        raise BuildReviewError("{} tree entry is malformed".format(label))
    return match.group(1), match.group(2)


def current_input_record(runtime_row, overrides_by_path):
    """Return the exact current record without mutating historical identity."""
    override = overrides_by_path.get(runtime_row["path"])
    if override is None:
        return {
            "git_blob_sha1": runtime_row["git_blob_sha1"],
            "mode": runtime_row["mode"],
            "path": runtime_row["path"],
            "sha256": runtime_row["sha256"],
            "size": runtime_row["size"],
        }
    require_exact(
        override["path"],
        runtime_row["path"],
        "{} override path".format(runtime_row["path"]),
    )
    require_exact(
        override["runtime_git_blob_sha1"],
        runtime_row["git_blob_sha1"],
        "{} override runtime blob".format(runtime_row["path"]),
    )
    require_exact(
        override["runtime_sha256"],
        runtime_row["sha256"],
        "{} override runtime digest".format(runtime_row["path"]),
    )
    require_exact(
        override["runtime_size"],
        runtime_row["size"],
        "{} override runtime size".format(runtime_row["path"]),
    )
    require_exact(
        override["mode"],
        runtime_row["mode"],
        "{} override mode".format(runtime_row["path"]),
    )
    return {
        "git_blob_sha1": override["current_git_blob_sha1"],
        "mode": override["mode"],
        "path": override["path"],
        "sha256": override["current_sha256"],
        "size": override["current_size"],
    }


def validate_repository(repo, review):
    repo = repo.resolve()
    runtime_type = run_git(repo, ["cat-file", "-t", RUNTIME_HEAD_SHA]).stdout.strip()
    require_exact(runtime_type, b"commit", "runtime Git object type")
    runtime_tree = run_git(repo, ["show", "-s", "--format=%T", RUNTIME_HEAD_SHA]).stdout.decode("ascii").strip()
    require_exact(runtime_tree, RUNTIME_TREE_SHA, "runtime tree")
    current_head = run_git(repo, ["rev-parse", "HEAD"]).stdout.decode("ascii").strip()
    if HEX_SHA1.fullmatch(current_head) is None:
        raise BuildReviewError("current HEAD is invalid")
    current_type = run_git(repo, ["cat-file", "-t", current_head]).stdout.strip()
    require_exact(current_type, b"commit", "current HEAD Git object type")
    ancestry = run_git(repo, ["merge-base", "--is-ancestor", RUNTIME_HEAD_SHA, current_head], allow_failure=True)
    if ancestry.returncode != 0:
        raise BuildReviewError("current HEAD is not a descendant of the reviewed runtime head")
    committed_inputs = review["runtime_candidate"]["committed_inputs"]
    overrides = review["current_repository_input_policy"]["current_overrides"]
    overrides_by_path = {row["path"]: row for row in overrides}
    if len(overrides_by_path) != len(overrides):
        raise BuildReviewError("current override paths are not unique")
    committed_paths = {row["path"] for row in committed_inputs}
    if set(overrides_by_path) - committed_paths:
        raise BuildReviewError("current override names an unreviewed runtime input")
    for index, row in enumerate(committed_inputs):
        label = "committed input {}".format(index)
        path = safe_relative_path(row["path"], label + " path")
        runtime_mode, runtime_blob = git_tree_record(repo, RUNTIME_HEAD_SHA, path, label + " runtime")
        require_exact(runtime_mode, row["mode"], label + " runtime mode")
        require_exact(runtime_blob, row["git_blob_sha1"], label + " runtime blob")
        data = run_git(repo, ["cat-file", "blob", runtime_blob]).stdout
        require_exact(len(data), row["size"], label + " runtime size")
        require_exact(sha256_bytes(data), row["sha256"], label + " runtime digest")
        current_expected = current_input_record(row, overrides_by_path)
        current_mode, current_blob = git_tree_record(repo, current_head, path, label + " current")
        require_exact(
            (current_mode, current_blob),
            (current_expected["mode"], current_expected["git_blob_sha1"]),
            label + " current blob",
        )
        current_data = run_git(repo, ["cat-file", "blob", current_blob]).stdout
        require_exact(
            len(current_data), current_expected["size"], label + " current size"
        )
        require_exact(
            sha256_bytes(current_data),
            current_expected["sha256"],
            label + " current digest",
        )
        index_rows = run_git(repo, ["ls-files", "--stage", "--", path]).stdout.decode("ascii").splitlines()
        if len(index_rows) != 1:
            raise BuildReviewError("{} has no unique index entry".format(label))
        match = re.fullmatch(r"(100644) ([0-9a-f]{40}) 0\t(.+)", index_rows[0])
        if match is None or match.group(3) != path:
            raise BuildReviewError("{} index entry is malformed".format(label))
        require_exact(
            (match.group(1), match.group(2)),
            (current_expected["mode"], current_expected["git_blob_sha1"]),
            label + " index",
        )
        worktree = read_regular_file_once(
            repository_file(repo, path, label + " worktree"),
            label + " worktree",
            expected_mode=0o644,
        )
        require_exact(
            len(worktree), current_expected["size"], label + " worktree size"
        )
        require_exact(
            sha256_bytes(worktree),
            current_expected["sha256"],
            label + " worktree digest",
        )

    end_head = run_git(repo, ["rev-parse", "HEAD"]).stdout.decode("ascii").strip()
    require_exact(end_head, current_head, "current HEAD at repository snapshot end")
    for index, row in enumerate(committed_inputs):
        label = "committed input {} snapshot end".format(index)
        path = safe_relative_path(row["path"], label + " path")
        current_expected = current_input_record(row, overrides_by_path)
        runtime_mode, runtime_blob = git_tree_record(
            repo, RUNTIME_HEAD_SHA, path, label + " runtime"
        )
        require_exact(
            (runtime_mode, runtime_blob),
            (row["mode"], row["git_blob_sha1"]),
            label + " runtime blob",
        )
        runtime_data = run_git(repo, ["cat-file", "blob", runtime_blob]).stdout
        require_exact(len(runtime_data), row["size"], label + " runtime size")
        require_exact(
            sha256_bytes(runtime_data), row["sha256"], label + " runtime digest"
        )
        end_mode, end_blob = git_tree_record(repo, end_head, path, label + " current")
        require_exact(
            (end_mode, end_blob),
            (current_expected["mode"], current_expected["git_blob_sha1"]),
            label + " current blob",
        )
        current_data = run_git(repo, ["cat-file", "blob", end_blob]).stdout
        require_exact(
            len(current_data), current_expected["size"], label + " current size"
        )
        require_exact(
            sha256_bytes(current_data),
            current_expected["sha256"],
            label + " current digest",
        )
        index_rows = run_git(
            repo, ["ls-files", "--stage", "--", path]
        ).stdout.decode("ascii").splitlines()
        if len(index_rows) != 1:
            raise BuildReviewError("{} has no unique index entry".format(label))
        match = re.fullmatch(r"(100644) ([0-9a-f]{40}) 0\t(.+)", index_rows[0])
        if match is None or match.group(3) != path:
            raise BuildReviewError("{} index entry is malformed".format(label))
        require_exact(
            (match.group(1), match.group(2)),
            (current_expected["mode"], current_expected["git_blob_sha1"]),
            label + " index",
        )
        worktree = read_regular_file_once(
            repository_file(repo, path, label + " worktree"),
            label + " worktree",
            expected_mode=0o644,
        )
        require_exact(
            len(worktree), current_expected["size"], label + " worktree size"
        )
        require_exact(
            sha256_bytes(worktree),
            current_expected["sha256"],
            label + " worktree digest",
        )
    final_head = run_git(repo, ["rev-parse", "HEAD"]).stdout.decode("ascii").strip()
    require_exact(final_head, current_head, "current HEAD after repository snapshot")
    return current_head


def parse_sum_manifest(data, label):
    try:
        text = data.decode("ascii")
    except UnicodeError as exc:
        raise BuildReviewError("{} is not ASCII: {}".format(label, exc))
    if not text.endswith("\n") or "\r" in text or "\x00" in text:
        raise BuildReviewError("{} is not canonical LF text".format(label))
    rows = []
    seen = set()
    for line in text.splitlines():
        match = SUM_LINE.fullmatch(line)
        if match is None:
            raise BuildReviewError("{} contains a malformed row".format(label))
        name = safe_relative_path(match.group(2), label + " member")
        if name in seen:
            raise BuildReviewError("{} contains duplicate paths".format(label))
        seen.add(name)
        rows.append((name, match.group(1)))
    if [name for name, unused in rows] != sorted(seen):
        raise BuildReviewError("{} paths are not sorted".format(label))
    return rows


def parse_config(data):
    try:
        text = data.decode("utf-8")
    except UnicodeError as exc:
        raise BuildReviewError("resolved config is not UTF-8: {}".format(exc))
    if not text.endswith("\n") or "\r" in text or "\x00" in text:
        raise BuildReviewError("resolved config is not canonical LF text")
    values = {}
    for line in text.splitlines():
        match = CONFIG_SET.fullmatch(line) or CONFIG_UNSET.fullmatch(line)
        if match is None:
            continue
        symbol = match.group(1)
        value = match.group(2) if line.startswith("CONFIG_") else "n"
        if symbol in values:
            raise BuildReviewError("resolved config repeats {}".format(symbol))
        values[symbol] = value
    return values


def parse_modinfo(data, label):
    try:
        text = data.decode("utf-8")
    except UnicodeError as exc:
        raise BuildReviewError("{} is not UTF-8: {}".format(label, exc))
    if not text.endswith("\n") or "\r" in text or "\x00" in text:
        raise BuildReviewError("{} is not canonical text".format(label))
    values = {}
    for line in text.splitlines():
        if not line.strip():
            continue
        match = re.fullmatch(r"([a-z0-9_]+):\s*(.*)", line)
        if match is None:
            raise BuildReviewError("{} contains a malformed line".format(label))
        values.setdefault(match.group(1), []).append(match.group(2))
    return values


def elf_string(table, offset, label):
    if type(offset) is not int or offset < 0 or offset >= len(table):
        raise BuildReviewError("{} string offset is outside its table".format(label))
    end = table.find(b"\0", offset)
    if end < 0:
        raise BuildReviewError("{} string is not NUL terminated".format(label))
    try:
        return table[offset:end].decode("ascii")
    except UnicodeError as exc:
        raise BuildReviewError("{} string is not ASCII: {}".format(label, exc))


def parse_elf_notes(data, label):
    records = []
    position = 0
    while position < len(data):
        if position + 12 > len(data):
            raise BuildReviewError("{} note header is truncated".format(label))
        name_size, description_size, note_type = struct.unpack_from("<III", data, position)
        position += 12
        if name_size < 1:
            raise BuildReviewError("{} note has an empty name".format(label))
        name_end = position + name_size
        padded_name_end = (name_end + 3) & ~3
        description_end = padded_name_end + description_size
        padded_description_end = (description_end + 3) & ~3
        if padded_description_end > len(data):
            raise BuildReviewError("{} note payload is truncated".format(label))
        raw_name = data[position:name_end]
        if not raw_name.endswith(b"\0") or b"\0" in raw_name[:-1]:
            raise BuildReviewError("{} note name is not canonical".format(label))
        try:
            note_name = raw_name[:-1].decode("ascii")
        except UnicodeError as exc:
            raise BuildReviewError("{} note name is not ASCII: {}".format(label, exc))
        if any(data[name_end:padded_name_end]) or any(data[description_end:padded_description_end]):
            raise BuildReviewError("{} note padding is not zero".format(label))
        description = data[padded_name_end:description_end]
        records.append({
            "description_hex": description.hex(),
            "description_size": description_size,
            "name": note_name,
            "name_size": name_size,
            "type": note_type,
        })
        position = padded_description_end
    if not records:
        raise BuildReviewError("{} has no note records".format(label))
    return records


def parse_elf_module(data, label):
    if len(data) < 64 or data[:4] != b"\x7fELF":
        raise BuildReviewError("{} is not an ELF file".format(label))
    ident = data[:16]
    if ident[4] != 2 or ident[5] != 1 or ident[6] != 1 or ident[7:] != b"\0" * 9:
        raise BuildReviewError("{} is not little-endian ELF64 version 1".format(label))
    try:
        header = struct.unpack_from("<HHIQQQIHHHHHH", data, 16)
    except struct.error as exc:
        raise BuildReviewError("{} ELF header is truncated: {}".format(label, exc))
    (
        elf_type,
        machine,
        version,
        entry,
        program_offset,
        section_offset,
        flags,
        header_size,
        program_entry_size,
        program_count,
        section_entry_size,
        section_count,
        section_name_index,
    ) = header
    if elf_type != 1 or machine != 62 or version != 1:
        raise BuildReviewError("{} is not an x86-64 ET_REL module".format(label))
    if any((entry, program_offset, flags, program_entry_size, program_count)):
        raise BuildReviewError("{} ELF relocatable header fields differ".format(label))
    if header_size != 64 or section_entry_size != 64:
        raise BuildReviewError("{} ELF header sizes differ".format(label))
    if section_count < 1 or section_count > 4096 or section_name_index >= section_count:
        raise BuildReviewError("{} ELF section count/index differs".format(label))
    table_size = section_entry_size * section_count
    if section_offset < header_size or section_offset + table_size > len(data):
        raise BuildReviewError("{} ELF section table is outside the file".format(label))
    rows = []
    for index in range(section_count):
        try:
            raw = struct.unpack_from(
                "<IIQQQQIIQQ", data, section_offset + index * section_entry_size
            )
        except struct.error as exc:
            raise BuildReviewError("{} section {} is truncated: {}".format(label, index, exc))
        row = {
            "name_offset": raw[0],
            "type": raw[1],
            "flags": raw[2],
            "address": raw[3],
            "offset": raw[4],
            "size": raw[5],
            "link": raw[6],
            "info": raw[7],
            "alignment": raw[8],
            "entry_size": raw[9],
        }
        if row["type"] != 8 and row["offset"] + row["size"] > len(data):
            raise BuildReviewError("{} section {} is outside the file".format(label, index))
        if row["address"] != 0:
            raise BuildReviewError("{} ET_REL section {} has a nonzero address".format(label, index))
        alignment = row["alignment"]
        if alignment and alignment & (alignment - 1):
            raise BuildReviewError("{} section {} alignment is not a power of two".format(label, index))
        if alignment > 1 and row["offset"] % alignment:
            raise BuildReviewError("{} section {} offset is misaligned".format(label, index))
        rows.append(row)
    name_row = rows[section_name_index]
    if name_row["type"] != 3:
        raise BuildReviewError("{} section-name table has the wrong type".format(label))
    name_table = data[name_row["offset"]:name_row["offset"] + name_row["size"]]
    sections = {}
    for index, row in enumerate(rows):
        name = elf_string(name_table, row["name_offset"], "{} section {}".format(label, index))
        row["index"] = index
        row["name"] = name
        if name and name in sections:
            raise BuildReviewError("{} repeats ELF section {}".format(label, name))
        if name:
            sections[name] = row
    require_exact(
        rows[0],
        {
            "address": 0, "alignment": 0, "entry_size": 0, "flags": 0,
            "index": 0, "info": 0, "link": 0, "name": "", "name_offset": 0,
            "offset": 0, "size": 0, "type": 0,
        },
        label + " canonical null section header",
    )
    for required in (".modinfo", ".symtab", ".strtab"):
        if required not in sections:
            raise BuildReviewError("{} lacks ELF section {}".format(label, required))

    modinfo_row = sections[".modinfo"]
    if modinfo_row["type"] != 1:
        raise BuildReviewError("{} .modinfo has the wrong section type".format(label))
    modinfo_data = data[
        modinfo_row["offset"]:modinfo_row["offset"] + modinfo_row["size"]
    ]
    if not modinfo_data or not modinfo_data.endswith(b"\0"):
        raise BuildReviewError("{} .modinfo is not NUL terminated".format(label))
    modinfo = {}
    modinfo_records = []
    record_offset = 0
    modinfo_entries = []
    for index, raw_record in enumerate(modinfo_data[:-1].split(b"\0")):
        if not raw_record or b"=" not in raw_record:
            raise BuildReviewError("{} .modinfo record {} is malformed".format(label, index))
        try:
            record = raw_record.decode("utf-8")
        except UnicodeError as exc:
            raise BuildReviewError("{} .modinfo is not UTF-8: {}".format(label, exc))
        key, value = record.split("=", 1)
        if re.fullmatch(r"[a-z0-9_]+", key) is None:
            raise BuildReviewError("{} .modinfo key is malformed".format(label))
        modinfo.setdefault(key, []).append(value)
        modinfo_records.append(record)
        modinfo_entries.append((record_offset, record))
        record_offset += len(raw_record) + 1

    symtab = sections[".symtab"]
    if symtab["type"] != 2 or symtab["entry_size"] != 24 or symtab["size"] % 24:
        raise BuildReviewError("{} symbol table shape differs".format(label))
    if symtab["link"] >= len(rows):
        raise BuildReviewError("{} symbol string-table link is invalid".format(label))
    strtab_row = rows[symtab["link"]]
    if strtab_row["type"] != 3 or strtab_row["name"] != ".strtab":
        raise BuildReviewError("{} symbol string table differs".format(label))
    strings = data[strtab_row["offset"]:strtab_row["offset"] + strtab_row["size"]]
    symbols = {}
    symbols_by_index = []
    for index in range(symtab["size"] // symtab["entry_size"]):
        try:
            raw = struct.unpack_from(
                "<IBBHQQ", data, symtab["offset"] + index * symtab["entry_size"]
            )
        except struct.error as exc:
            raise BuildReviewError("{} symbol {} is truncated: {}".format(label, index, exc))
        name = elf_string(strings, raw[0], "{} symbol {}".format(label, index))
        record = {
            "binding": raw[1] >> 4,
            "index": index,
            "name_offset": raw[0],
            "other": raw[2],
            "type": raw[1] & 0x0f,
            "section_index": raw[3],
            "value": raw[4],
            "size": raw[5],
        }
        if record["other"] != 0:
            raise BuildReviewError("{} symbol {} has noncanonical st_other".format(label, index))
        if record["binding"] not in (0, 1) or record["type"] not in (0, 1, 2, 3, 4):
            raise BuildReviewError("{} symbol {} class differs".format(label, index))
        if record["section_index"] == 0xffff:
            raise BuildReviewError(
                "{} symbol {} uses unsupported SHN_XINDEX".format(label, index)
            )
        if not (
            record["section_index"] < len(rows)
            or record["section_index"] == 0xfff1
        ):
            raise BuildReviewError("{} symbol {} section index differs".format(label, index))
        symbols.setdefault(name, []).append(record)
        symbols_by_index.append((name, record))
    if not symbols_by_index:
        raise BuildReviewError("{} symbol table is empty".format(label))
    require_exact(
        symbols_by_index[0],
        (
            "",
            {
                "binding": 0, "index": 0, "name_offset": 0, "other": 0,
                "section_index": 0, "size": 0, "type": 0, "value": 0,
            },
        ),
        label + " canonical null symbol",
    )
    if symtab["info"] < 1 or symtab["info"] > len(symbols_by_index):
        raise BuildReviewError("{} symbol-table local boundary is invalid".format(label))
    if any(
        symbol["binding"] != 0
        for _, symbol in symbols_by_index[:symtab["info"]]
    ) or any(
        symbol["binding"] == 0
        for _, symbol in symbols_by_index[symtab["info"]:]
    ):
        raise BuildReviewError("{} symbol-table local/global partition differs".format(label))

    relocations = {}
    all_relocation_sections = []
    for row in rows:
        if row["type"] != 4:
            continue
        if row["info"] >= len(rows):
            raise BuildReviewError("{} relocation target section is invalid".format(label))
        target_row = rows[row["info"]]
        if (
            row["entry_size"] != 24
            or row["size"] % 24
            or row["link"] != symtab["index"]
        ):
            raise BuildReviewError("{} relocation section shape differs".format(label))
        records = []
        all_records = []
        for index in range(row["size"] // row["entry_size"]):
            try:
                offset, info, addend = struct.unpack_from(
                    "<QQq", data, row["offset"] + index * row["entry_size"]
                )
            except struct.error as exc:
                raise BuildReviewError(
                    "{} relocation {} is truncated: {}".format(label, index, exc)
                )
            symbol_index = info >> 32
            if symbol_index >= len(symbols_by_index):
                raise BuildReviewError("{} relocation symbol index is invalid".format(label))
            relocation_type = info & 0xffffffff
            if relocation_type not in X86_64_RELOCATION_WIDTHS:
                raise BuildReviewError("{} relocation type is unsupported".format(label))
            if offset + X86_64_RELOCATION_WIDTHS[relocation_type] > target_row["size"]:
                raise BuildReviewError(
                    "{} relocation {} write exceeds its target".format(label, index)
                )
            symbol_name, symbol = symbols_by_index[symbol_index]
            symbol_section = None
            if symbol["section_index"] < len(rows):
                symbol_section = rows[symbol["section_index"]]["name"]
            full_record = {
                "addend": addend,
                "index": index,
                "offset": offset,
                "symbol": symbol_name,
                "symbol_index": symbol_index,
                "symbol_section": symbol_section,
                "type": relocation_type,
            }
            all_records.append(full_record)
            if (
                symbol_name == "ihk_provider_lifecycle_v1"
                or target_row["name"] == "__ksymtab_gpl"
            ):
                records.append(full_record)
        all_relocation_sections.append({
            "index": row["index"],
            "name": row["name"],
            "records": all_records,
            "target_section": target_row["name"],
            "target_section_index": target_row["index"],
        })
        if records:
            relocations[row["name"]] = {
                "flags": row["flags"],
                "records": records,
                "section_index": row["index"],
                "target_section": target_row["name"],
                "target_section_index": target_row["index"],
            }

    namespace_data = b""
    if "__ksymtab_strings" in sections:
        namespace_row = sections["__ksymtab_strings"]
        if namespace_row["type"] != 1:
            raise BuildReviewError("{} export string section has the wrong type".format(label))
        namespace_data = data[
            namespace_row["offset"]:namespace_row["offset"] + namespace_row["size"]
        ]
    structure = {
        "header": {
            "flags": flags,
            "header_size": header_size,
            "machine": machine,
            "program_count": program_count,
            "program_entry_size": program_entry_size,
            "program_offset": program_offset,
            "section_count": section_count,
            "section_entry_size": section_entry_size,
            "section_name_index": section_name_index,
            "section_offset": section_offset,
            "type": elf_type,
            "version": version,
        },
        "relocations": all_relocation_sections,
        "sections": rows,
        "symbols": [dict(record, name=name) for name, record in symbols_by_index],
    }
    return {
        "elf_class": "ELF64",
        "elf_machine": "EM_X86_64",
        "elf_type": "ET_REL",
        "modinfo": modinfo,
        "modinfo_entries": modinfo_entries,
        "modinfo_records": modinfo_records,
        "namespace_data": namespace_data,
        "relocations": relocations,
        "sections": sections,
        "symbols": symbols,
        "symbols_by_index": symbols_by_index,
        "all_relocations": all_relocation_sections,
        "structure_sha256": sha256_bytes(canonical_json_bytes(structure)),
    }


def parse_saved_command(path, data):
    if any((byte < 0x20 and byte != 0x0a) or byte == 0x7f for byte in data):
        raise BuildReviewError("{} contains non-LF control bytes".format(path))
    try:
        text = data.decode("ascii")
    except UnicodeError as exc:
        raise BuildReviewError("{} is not strict ASCII: {}".format(path, exc))
    if not text.endswith("\n") or "\r" in text or "\x00" in text:
        raise BuildReviewError("{} is not canonical text".format(path))
    lines = text[:-1].split("\n")
    if not lines:
        raise BuildReviewError("{} lacks command text".format(path))
    first = lines[0]
    match = re.fullmatch(r"savedcmd_(.+) := (.+)", first)
    if match is None:
        raise BuildReviewError("{} lacks one saved command".format(path))
    if text.count("savedcmd_") != 1:
        raise BuildReviewError("{} has multiple saved commands".format(path))
    return match.group(1), match.group(2), text


def reject_raw_shell_grammar(fragment, label):
    """Reject active shell grammar while permitting inert quoted text."""
    single_quoted = False
    double_quoted = False
    for character in fragment:
        if character == "\\" and not single_quoted:
            raise BuildReviewError("{} has raw shell expansion/control".format(label))
        if character == "'" and not double_quoted:
            single_quoted = not single_quoted
            continue
        if character == '"' and not single_quoted:
            double_quoted = not double_quoted
            continue
        if single_quoted:
            continue
        if double_quoted:
            if character in ("$", "`"):
                raise BuildReviewError("{} has raw shell expansion/control".format(label))
            continue
        if character in "$`;&|<>*?[]{}~#!()":
            raise BuildReviewError("{} has raw shell expansion/control".format(label))
    if single_quoted or double_quoted:
        raise BuildReviewError("{} has unmatched shell quoting".format(label))


def summarize_cmd(path, data):
    expected = next((row for row in EXPECTED_CMD_RECORDS if row["path"] == path), None)
    if expected is None:
        raise BuildReviewError("unexpected command record {}".format(path))
    target, command, text = parse_saved_command(path, data)
    if "$(shell" in text or "`" in text:
        raise BuildReviewError("{} contains forbidden shell evaluation".format(path))
    require_exact(target, expected["target"], path + " target")
    try:
        tokens = shlex.split(command, posix=True)
    except ValueError as exc:
        raise BuildReviewError("{} command tokenization failed: {}".format(path, exc))
    kind = expected["kind"]
    if kind == "rust-compile":
        expected_separator_count = 0 if expected["crate"] == "ihk_smp_x86_64" else 1
        if expected_separator_count:
            raw_boundary = "  ; ./tools/objtool/objtool "
            if command.count(";") != 1 or command.count(raw_boundary) != 1:
                raise BuildReviewError("{} Rust shell pipeline differs".format(path))
            compiler_command, objtool_command = command.split(raw_boundary, 1)
            reject_raw_shell_grammar(compiler_command, path + " Rust compiler command")
            reject_raw_shell_grammar(objtool_command, path + " Rust objtool command")
        else:
            if ";" in command:
                raise BuildReviewError("{} Rust shell pipeline differs".format(path))
            compiler_command = command
            reject_raw_shell_grammar(compiler_command, path + " Rust compiler command")
        if tokens.count(";") != expected_separator_count:
            raise BuildReviewError("{} Rust shell pipeline differs".format(path))
        if expected_separator_count:
            separator = tokens.index(";")
            compiler_tokens = tokens[:separator]
            objtool_tokens = tokens[separator + 1:]
        else:
            compiler_tokens = tokens
            objtool_tokens = []
        if (
            any(token in ("&&", "||", "|", ">", ">>", "<", "<<", "&") for token in compiler_tokens)
            or any("$(" in token or "${" in token or "`" in token for token in compiler_tokens)
        ):
            raise BuildReviewError("{} Rust compiler command contains shell control".format(path))
        if len(compiler_tokens) < 3 or compiler_tokens[1] != "rustc":
            raise BuildReviewError("{} Rust compiler position differs".format(path))
        if compiler_tokens.count("rustc") != 1 or compiler_tokens.count("-Dwarnings") != 1:
            raise BuildReviewError("{} is not one warning-fatal Rust compile".format(path))
        if compiler_tokens.count("--emit=obj={}".format(target)) != 1:
            raise BuildReviewError("{} object output differs".format(path))
        if compiler_tokens.count("--crate-name") != 1:
            raise BuildReviewError("{} crate-name option differs".format(path))
        crate_index = compiler_tokens.index("--crate-name")
        if crate_index + 1 >= len(compiler_tokens):
            raise BuildReviewError("{} crate-name value is missing".format(path))
        require_exact(compiler_tokens[crate_index + 1], expected["crate"], path + " crate name")
        root = SOURCE_ROOT + "/" + MODULE_ROOT + "/" + expected["root_source"]
        primary_sources = [
            token for token in compiler_tokens
            if token.startswith(SOURCE_ROOT + "/" + MODULE_ROOT + "/")
            and token.endswith(".rs")
        ]
        require_exact(primary_sources, [root], path + " primary Rust source")
        require_exact(compiler_tokens[-1], root, path + " final Rust source token")
        source_assignment = "source_{} := {}".format(target, root)
        require_exact(text[:-1].split("\n").count(source_assignment), 1, path + " source assignment")
        modfile = MODULE_ROOT + "/" + (
            "ihk-smp-x86_64" if expected["crate"] == "ihk_smp_x86_64" else expected["crate"]
        )
        require_exact(compiler_tokens[0], "RUST_MODFILE=" + modfile, path + " RUST_MODFILE")
        require_exact(
            [token for token in compiler_tokens if token.startswith("@")],
            ["@./include/generated/rustc_cfg"],
            path + " Rust response inputs",
        )
        extern_values = []
        for index, token in enumerate(compiler_tokens):
            if token == "--extern":
                if index + 1 >= len(compiler_tokens):
                    raise BuildReviewError("{} Rust extern input is missing".format(path))
                extern_values.append(compiler_tokens[index + 1])
            elif token.startswith("--extern="):
                raise BuildReviewError("{} Rust extern inputs differ".format(path))
        require_exact(
            extern_values,
            ["force:alloc", "kernel"],
            path + " exact Rust extern inputs",
        )
        expected_objtool = []
        if expected_separator_count:
            expected_objtool = [
                "./tools/objtool/objtool", "--hacks=jump_label", "--hacks=noinstr",
                "--hacks=skylake", "--ibt", "--mcount", "--mnop", "--orc",
                "--retpoline", "--rethunk", "--sls", "--static-call", "--uaccess",
                "--prefix=16", "--werror", "--link", "--module", target,
            ]
        require_exact(
            objtool_tokens,
            expected_objtool,
            path + " exact Rust objtool pipeline",
        )
        sources = sorted(set(re.findall(
            re.escape(SOURCE_ROOT + "/" + MODULE_ROOT + "/") + r"([A-Za-z0-9_./-]+\.rs)",
            text,
        )))
        require_exact(sources, expected["project_sources"], path + " project sources")
        allowed_object_tokens = {"--emit=obj=" + target}
        forbidden = [
            token for token in compiler_tokens
            if token.lower().endswith(
                (".a", ".bc", ".c", ".cc", ".cpp", ".ko", ".lo", ".o", ".obj", ".rlib", ".rmeta", ".so")
            )
            and token not in allowed_object_tokens
        ]
        if forbidden:
            raise BuildReviewError("{} consumes a forbidden project input: {}".format(path, forbidden))
    elif kind == "generated-mod-c-compile":
        reject_raw_shell_grammar(command, path + " generated-mod command")
        if (
            any(token in (";", "&&", "||", "|", ">", ">>", "<", "<<", "&") for token in tokens)
            or any(token.startswith("@") or "$(" in token or "${" in token or "`" in token for token in tokens)
        ):
            raise BuildReviewError("{} generated-mod command contains shell control".format(path))
        if not tokens or tokens[0] != "clang" or tokens.count("clang") != 1:
            raise BuildReviewError("{} is not one generated-mod C compile".format(path))
        if tokens.count("-DMODULE") != 1 or tokens.count("-o") != 1:
            raise BuildReviewError("{} generated-mod compile differs".format(path))
        forced_includes = []
        for index, token in enumerate(tokens):
            if token == "-include":
                if index + 1 >= len(tokens):
                    raise BuildReviewError("{} generated include is missing".format(path))
                forced_includes.append(tokens[index + 1])
            elif token.startswith("-include"):
                raise BuildReviewError("{} generated include inputs differ".format(path))
        require_exact(
            forced_includes,
            [
                SOURCE_ROOT + "/include/linux/compiler-version.h",
                SOURCE_ROOT + "/include/linux/kconfig.h",
                SOURCE_ROOT + "/include/linux/compiler_types.h",
            ],
            path + " exact generated include inputs",
        )
        output_index = tokens.index("-o")
        if output_index + 1 >= len(tokens):
            raise BuildReviewError("{} generated output is missing".format(path))
        require_exact(tokens[output_index + 1], target, path + " generated output")
        suffix_inputs = [
            token for token in tokens
            if token.lower().endswith((".a", ".c", ".cc", ".cpp", ".o", ".so"))
        ]
        require_exact(suffix_inputs, [target, expected["inputs"][0]], path + " generated compile inputs")
        require_exact(tokens[-1], expected["inputs"][0], path + " generated source")
        source_assignment = "source_{} := {}".format(target, expected["inputs"][0])
        require_exact(text[:-1].split("\n").count(source_assignment), 1, path + " generated source assignment")
    elif kind == "object-list":
        pipe_boundary = " | awk "
        redirect_boundary = " > "
        if (
            command.count("|") != 1
            or command.count(">") != 1
            or command.count(pipe_boundary) != 1
        ):
            raise BuildReviewError("{} object-list shell grammar differs".format(path))
        printf_command, awk_command = command.split(pipe_boundary, 1)
        if awk_command.count(redirect_boundary) != 1:
            raise BuildReviewError("{} object-list shell grammar differs".format(path))
        awk_program, redirect_target = awk_command.split(redirect_boundary, 1)
        reject_raw_shell_grammar(printf_command, path + " object-list printf command")
        reject_raw_shell_grammar(awk_program, path + " object-list awk program")
        reject_raw_shell_grammar(redirect_target, path + " object-list redirect target")
        require_exact(redirect_target, target, path + " object-list raw redirect target")
        object_name = expected["inputs"][0][len(MODULE_ROOT) + 1:]
        require_exact(
            tokens,
            [
                "printf", "%s\\n", object_name, "|", "awk",
                '!x[$$0]++ { print("drivers/misc/mckernel/"$$0) }', ">", target,
            ],
            path + " exact object-list tokens",
        )
    elif kind == "aggregate-link":
        raw_boundary = "  ; ./tools/objtool/objtool "
        if command.count(";") != 1 or command.count(raw_boundary) != 1:
            raise BuildReviewError("{} aggregate-link shell grammar differs".format(path))
        linker_command, objtool_command = command.split(raw_boundary, 1)
        reject_raw_shell_grammar(linker_command, path + " aggregate linker command")
        reject_raw_shell_grammar(objtool_command, path + " aggregate objtool command")
        require_exact(
            tokens,
            [
                "ld.lld", "-m", "elf_x86_64", "-z", "noexecstack", "-r", "-o", target,
                expected["inputs"][0], ";", "./tools/objtool/objtool", "--hacks=jump_label",
                "--hacks=noinstr", "--hacks=skylake", "--ibt", "--mcount", "--mnop", "--orc",
                "--retpoline", "--rethunk", "--sls", "--static-call", "--uaccess", "--prefix=16",
                "--werror", "--link", "--module", target,
            ],
            path + " exact aggregate-link tokens",
        )
    elif kind == "final-link":
        require_exact(
            tokens,
            [
                "ld.lld", "-r", "-m", "elf_x86_64", "-z", "noexecstack",
                "--build-id=sha1", "-T", "scripts/module.lds", "-o", target,
            ] + expected["inputs"],
            path + " exact final-link tokens",
        )
    else:
        raise BuildReviewError("{} has an unsupported command kind".format(path))
    command_lines = text[:-1].split("\n")
    exact_token_sha256 = sha256_bytes(canonical_json_bytes(tokens))
    raw_line_sha256 = sha256_bytes(command_lines[0].encode("ascii"))
    trailing_lines_sha256 = sha256_bytes(canonical_json_bytes(command_lines[1:]))
    structure_sha256 = sha256_bytes(canonical_json_bytes(command_lines))
    require_exact(
        exact_token_sha256,
        EXACT_CMD_TOKEN_VECTOR_SHA256[path],
        path + " immutable exact command token vector",
    )
    require_exact(
        raw_line_sha256,
        EXPECTED_CMD_LINE_SHA256[path][0],
        path + " immutable exact raw saved-command line",
    )
    require_exact(
        trailing_lines_sha256,
        EXPECTED_CMD_LINE_SHA256[path][1],
        path + " immutable exact trailing-line grammar",
    )
    require_exact(
        structure_sha256,
        EXPECTED_CMD_STRUCTURE_SHA256[path],
        path + " immutable exact full command structure",
    )
    require_exact(
        raw_line_sha256,
        expected["savedcmd_line_sha256"],
        path + " exact raw saved-command line digest",
    )
    require_exact(
        trailing_lines_sha256,
        expected["trailing_lines_sha256"],
        path + " exact trailing-line grammar digest",
    )
    require_exact(
        structure_sha256,
        expected["structure_sha256"],
        path + " exact full command structure digest",
    )
    require_exact(
        exact_token_sha256,
        expected["token_sha256"],
        path + " exact command token digest",
    )
    require_exact(sha256_bytes(data), expected["sha256"], path + " exact command digest")
    return expected


def verify_stage_lock(data, review):
    stage = read_json_bytes(data, "stage lock", require_canonical=True)
    exact_keys(
        stage,
        {
            "credit_eligible", "files", "manifest_sha256", "parent_integration",
            "production_readiness_blockers", "profile_id", "purpose", "schema_version", "target",
        },
        "stage lock",
    )
    require_exact(stage["schema_version"], 2, "stage schema")
    require_exact(stage["credit_eligible"], False, "stage credit")
    require_exact(stage["purpose"], "compiler-evidence-only", "stage purpose")
    require_exact(stage["profile_id"], "rocky-10.2-native-rust-host-modules-v1", "stage profile")
    require_exact(stage["files"], EXPECTED_STAGE_FILES, "staged files")
    require_exact(
        stage["manifest_sha256"],
        review["verified_facts"]["stage_lock"]["manifest_sha256"],
        "stage manifest digest",
    )
    if any(PurePosixPath(row["path"]).suffix in (".a", ".c", ".cc", ".cpp", ".o", ".so") for row in stage["files"]):
        raise BuildReviewError("stage lock contains C or prebuilt project inputs")
    parent = exact_keys(
        stage["parent_integration"], {"bundle_sha256", "parent_files", "patch_sha256"}, "parent integration"
    )
    require_exact(parent["bundle_sha256"], "c806e6cda3be3e6f4b92cef35a0d5369738bae5b87e32ed4f486489d3435db2f", "parent bundle")
    require_exact(parent["patch_sha256"], "25b0724a2523c3fd5d6d8b824b72c6e6b19c2b16edebaa6719b53c22d4d5c7d9", "parent patch")
    require_exact(len(parent["parent_files"]), 2, "parent files")
    if type(stage["production_readiness_blockers"]) is not list or not stage["production_readiness_blockers"]:
        raise BuildReviewError("stage lock must retain production blockers")
    target = exact_keys(
        stage["target"],
        {
            "architecture", "config_policy_lock_id", "distribution", "kernel_nvr_base",
            "release", "resolved_config_sha256", "resolved_kernel_nvr",
            "resolved_toolchain_manifest_sha256", "source_lock_id", "source_rpm_sha256",
            "toolchain_lock_id",
        },
        "stage target",
    )
    require_exact(target["architecture"], "x86_64", "stage architecture")
    require_exact(target["release"], "10.2", "stage release")
    require_exact(target["resolved_config_sha256"], None, "unresolved config authority")
    require_exact(target["resolved_kernel_nvr"], None, "unresolved kernel authority")
    require_exact(target["resolved_toolchain_manifest_sha256"], None, "unresolved toolchain authority")
    return stage


def verify_parameter_layout(name, binary, parsed, fact):
    parameter_sections = ("__param", ".rela__param")
    if not fact["parameters"]:
        require_exact(
            [section for section in parameter_sections if section in parsed["sections"]],
            [],
            name + " unexpected loader parameters",
        )
        return
    require_exact(name, "ihk-smp-x86_64.ko", name + " parameter-bearing module")
    require_exact(
        [(row["name"], row["type"]) for row in fact["parameters"]],
        [(row["name"], row["type"]) for row in EXPECTED_SMP_PARAMETER_LAYOUT],
        name + " loader parameter fact order",
    )
    parameter_section = parsed["sections"]["__param"]
    relocation_section = parsed["sections"][".rela__param"]
    rodata_section = parsed["sections"][".rodata"]
    parameter_data = binary[
        parameter_section["offset"]:parameter_section["offset"] + parameter_section["size"]
    ]
    relocation_data = binary[
        relocation_section["offset"]:relocation_section["offset"] + relocation_section["size"]
    ]
    rodata = binary[rodata_section["offset"]:rodata_section["offset"] + rodata_section["size"]]
    require_exact(
        sha256_bytes(parameter_data),
        "ca544288f9a8aa4e09b0d14b7b574c785d9436ae77d0fe8f769a57af0d78f5b9",
        name + " immutable __param content",
    )
    require_exact(
        sha256_bytes(relocation_data),
        "7fa257beda28a6985ea933f885e379eaa8d783efab6720d124c1c4328c3e68e1",
        name + " immutable .rela__param content",
    )
    require_exact(
        sha256_bytes(rodata),
        "a93a1c6f6b9077e1642c300a7f29c0d642e2dafa59c6337f2bb393a93667bccb",
        name + " immutable parameter-name rodata content",
    )
    relocation_rows = [
        row for row in parsed["all_relocations"] if row["name"] == ".rela__param"
    ]
    require_exact(len(relocation_rows), 1, name + " parameter relocation section count")
    records = relocation_rows[0]["records"]
    require_exact(len(records), 24, name + " exact parameter relocation count")
    bss_index = parsed["sections"][".bss"]["index"]
    for index, expected in enumerate(EXPECTED_SMP_PARAMETER_LAYOUT):
        base = index * 40
        require_exact(
            {
                "flags": parameter_data[base + 27],
                "level": struct.unpack_from("<b", parameter_data, base + 26)[0],
                "padding": parameter_data[base + 28:base + 32],
                "permission": struct.unpack_from("<H", parameter_data, base + 24)[0],
            },
            {"flags": 0, "level": -1, "padding": b"\0" * 4, "permission": 0o644},
            name + " parameter {} permissions".format(index),
        )
        name_relocation, module_relocation, ops_relocation, storage_relocation = records[
            index * 4:index * 4 + 4
        ]
        require_exact(
            name_relocation,
            {
                "addend": expected["name_offset"], "index": index * 4,
                "offset": base, "symbol": "", "symbol_index": 48,
                "symbol_section": ".rodata", "type": 1,
            },
            name + " parameter {} name relocation".format(index),
        )
        require_exact(
            elf_string(rodata, expected["name_offset"], name + " parameter name"),
            expected["name"],
            name + " parameter {} loader name".format(index),
        )
        require_exact(
            module_relocation,
            {
                "addend": 0, "index": index * 4 + 1, "offset": base + 8,
                "symbol": "__this_module", "symbol_index": 79,
                "symbol_section": ".gnu.linkonce.this_module", "type": 1,
            },
            name + " parameter {} module relocation".format(index),
        )
        require_exact(
            ops_relocation,
            {
                "addend": 0, "index": index * 4 + 2, "offset": base + 16,
                "symbol": expected["ops"], "symbol_index": expected["ops_index"],
                "symbol_section": "", "type": 1,
            },
            name + " parameter {} ops relocation".format(index),
        )
        ops_symbols = parsed["symbols"].get(expected["ops"], [])
        require_exact(len(ops_symbols), 1, name + " parameter ops symbol count")
        ops_symbol = ops_symbols[0]
        require_exact(
            {
                key: ops_symbol[key]
                for key in ("binding", "index", "other", "section_index", "size", "type", "value")
            },
            {
                "binding": 1, "index": expected["ops_index"], "other": 0,
                "section_index": 0, "size": 0, "type": 0, "value": 0,
            },
            name + " parameter {} ops symbol".format(index),
        )
        require_exact(
            storage_relocation,
            {
                "addend": 0, "index": index * 4 + 3, "offset": base + 32,
                "symbol": expected["storage"], "symbol_index": expected["storage_index"],
                "symbol_section": ".bss", "type": 1,
            },
            name + " parameter {} storage relocation".format(index),
        )
        storage_symbols = parsed["symbols"].get(expected["storage"], [])
        require_exact(len(storage_symbols), 1, name + " parameter storage symbol count")
        storage_symbol = storage_symbols[0]
        require_exact(
            {
                key: storage_symbol[key]
                for key in ("binding", "index", "other", "section_index", "size", "type", "value")
            },
            {
                "binding": 1, "index": expected["storage_index"], "other": 0,
                "section_index": bss_index, "size": expected["storage_size"],
                "type": 1, "value": expected["storage_value"],
            },
            name + " parameter {} storage symbol".format(index),
        )


def verify_module_notes(name, binary, parsed):
    expected = EXPECTED_MODULE_NOTES[name]
    note_names = (".note.Linux", ".note.gnu.build-id", ".note.gnu.property")
    require_exact(
        sorted(row["name"] for row in parsed["sections"].values() if row["type"] == 7),
        sorted(note_names),
        name + " exact NOTE section set",
    )
    specifications = (
        (
            ".note.Linux", 4, 48, expected["linux_index"], LINUX_NOTE_SHA256,
            [
                {"description_hex": "00", "description_size": 1, "name": "Linux", "name_size": 6, "type": 256},
                {"description_hex": "00000000", "description_size": 4, "name": "Linux", "name_size": 6, "type": 257},
            ],
        ),
        (
            ".note.gnu.build-id", 4, 36, expected["build_id_index"],
            expected["build_id_sha256"],
            [{
                "description_hex": expected["build_id"], "description_size": 20,
                "name": "GNU", "name_size": 4, "type": 3,
            }],
        ),
        (
            ".note.gnu.property", 8, 32, expected["property_index"],
            GNU_PROPERTY_NOTE_SHA256,
            [{
                "description_hex": "020000c0040000000100000000000000",
                "description_size": 16, "name": "GNU", "name_size": 4, "type": 5,
            }],
        ),
    )
    for section_name, alignment, size, section_index, digest, expected_records in specifications:
        section = parsed["sections"].get(section_name)
        if section is None:
            raise BuildReviewError("{} lacks {}".format(name, section_name))
        require_exact(
            {
                key: section[key]
                for key in ("alignment", "entry_size", "flags", "index", "info", "link", "size", "type")
            },
            {
                "alignment": alignment, "entry_size": 0, "flags": 2,
                "index": section_index, "info": 0, "link": 0, "size": size, "type": 7,
            },
            name + " " + section_name + " exact shape",
        )
        note_data = binary[section["offset"]:section["offset"] + section["size"]]
        require_exact(
            parse_elf_notes(note_data, name + " " + section_name),
            expected_records,
            name + " " + section_name + " exact records",
        )
        require_exact(
            sha256_bytes(note_data), digest, name + " " + section_name + " immutable content"
        )


def verify_modules(files):
    for fact in EXPECTED_MODULE_FACTS:
        name = fact["binary"]
        binary = files[name]
        require_exact(len(binary), fact["binary_size"], name + " binary size")
        parsed = parse_elf_module(binary, name)
        require_exact(parsed["elf_class"], fact["elf_class"], name + " ELF class")
        require_exact(parsed["elf_machine"], fact["elf_machine"], name + " ELF machine")
        require_exact(parsed["elf_type"], fact["elf_type"], name + " ELF type")
        for section_name, expected_shape in EXPECTED_ELF_SECTION_SHAPES[name].items():
            if section_name not in parsed["sections"]:
                raise BuildReviewError("{} lacks exact section {}".format(name, section_name))
            section_row = parsed["sections"][section_name]
            actual_shape = {
                key: section_row[key]
                for key in ("alignment", "entry_size", "flags", "size", "type")
            }
            require_exact(actual_shape, expected_shape, name + " " + section_name + " shape")
            if section_name in (".modinfo", "__ksymtab_gpl", "__ksymtab_strings"):
                if not section_row["flags"] & 0x2:
                    raise BuildReviewError("{} {} is not SHF_ALLOC".format(name, section_name))
        require_exact(
            parsed["sections"][".symtab"]["info"],
            EXPECTED_ELF_SYMTAB_INFO[name],
            name + " exact symbol-table local boundary",
        )
        verify_module_notes(name, binary, parsed)

        direct = parsed["modinfo"]
        require_exact(
            parsed["modinfo_records"],
            EXPECTED_DIRECT_MODINFO[name],
            name + " exact direct modinfo records",
        )
        require_exact(
            len(parsed["modinfo_records"]),
            fact["modinfo_record_count"],
            name + " direct modinfo record count",
        )
        require_exact(direct.get("name"), [fact["name"]], name + " direct module name")
        require_exact(direct.get("license"), [fact["license"]], name + " direct license")
        require_exact(
            direct.get("depends"),
            [",".join(fact["depends"])],
            name + " direct dependency order",
        )
        require_exact(
            direct.get("import_ns", []),
            fact["import_namespaces"],
            name + " direct import namespace",
        )
        require_exact(direct.get("intree"), ["Y"], name + " direct in-tree marker")
        require_exact(direct.get("rhelversion"), ["10.2"], name + " direct RHEL marker")
        require_exact(
            direct.get("vermagic"),
            ["6.12.0 SMP preempt mod_unload "],
            name + " direct vermagic",
        )
        require_exact(direct.get("retpoline"), ["Y"], name + " direct retpoline marker")
        require_exact(
            direct.get("parm", []),
            [row["name"] + ":" + row["description"] for row in fact["parameters"]],
            name + " exact direct module parameters",
        )
        require_exact(
            direct.get("parmtype", []),
            [row["name"] + ":" + row["type"] for row in fact["parameters"]],
            name + " exact direct module parameter types",
        )
        verify_parameter_layout(name, binary, parsed, fact)

        this_expected = EXPECTED_THIS_MODULE[name]
        this_section = parsed["sections"].get(".gnu.linkonce.this_module")
        if this_section is None:
            raise BuildReviewError("{} lacks .gnu.linkonce.this_module".format(name))
        require_exact(
            {
                key: this_section[key]
                for key in ("alignment", "entry_size", "flags", "index", "info", "link", "size", "type")
            },
            {
                "alignment": 64, "entry_size": 0, "flags": 3,
                "index": this_expected["section_index"], "info": 0, "link": 0,
                "size": 1408, "type": 1,
            },
            name + " exact this_module section shape",
        )
        this_symbols = parsed["symbols"].get("__this_module", [])
        require_exact(len(this_symbols), 1, name + " __this_module symbol count")
        this_symbol = this_symbols[0]
        require_exact(
            {
                "binding": this_symbol["binding"],
                "index": this_symbol["index"],
                "other": this_symbol["other"],
                "section_index": this_symbol["section_index"],
                "size": this_symbol["size"],
                "type": this_symbol["type"],
                "value": this_symbol["value"],
            },
            {
                "binding": 1, "index": this_expected["symbol_index"], "other": 0,
                "section_index": this_expected["section_index"], "size": 1408,
                "type": 1, "value": 0,
            },
            name + " exact __this_module symbol",
        )
        this_data = binary[
            this_section["offset"]:this_section["offset"] + this_section["size"]
        ]
        this_name_field = this_data[24:80]
        expected_name_field = (
            this_expected["name"].encode("ascii") + b"\0"
        ).ljust(56, b"\0")
        require_exact(this_name_field, expected_name_field, name + " inline this_module name field")
        require_exact(
            this_expected["name"], fact["name"], name + " this_module/module fact name"
        )
        require_exact(
            direct.get("name"), [this_expected["name"]], name + " this_module/modinfo name"
        )
        require_exact(
            sha256_bytes(this_data),
            this_expected["section_sha256"],
            name + " immutable this_module section content",
        )

        values = parse_modinfo(files[name + ".modinfo"], name + " modinfo")
        expected_sidecar_keys = (set(direct) - {"parm", "parmtype"}) | {"filename"}
        if fact["parameters"]:
            expected_sidecar_keys.add("parm")
        require_exact(set(values), expected_sidecar_keys, name + " sidecar field closure")
        require_exact(
            values.get("filename"),
            ["/__w/_temp/native-rust-build/{}/{}".format(MODULE_ROOT, name)],
            name + " sidecar filename",
        )
        compared_keys = (
            "author", "depends", "description", "import_ns", "intree", "license",
            "name", "retpoline", "rhelversion", "srcversion", "vermagic", "version",
        )
        for key in compared_keys:
            require_exact(values.get(key, []), direct.get(key, []), name + " sidecar " + key)
        require_exact(
            values.get("parm", []),
            [
                "{}:{} ({})".format(row["name"], row["description"], row["type"])
                for row in reversed(fact["parameters"])
            ],
            name + " exact sidecar module parameters",
        )

        section_lines = ["", "String dump of section '.modinfo':"]
        section_lines.extend(
            "  [{:6x}]  {}".format(offset, record)
            for offset, record in parsed["modinfo_entries"]
        )
        section_lines.append("")
        require_exact(
            files[name + ".modinfo-section"],
            ("\n".join(section_lines) + "\n").encode("utf-8"),
            name + " direct modinfo section sidecar",
        )

        symbol_name = "ihk_provider_lifecycle_v1"
        symbols = parsed["symbols"]
        symbol_rows = symbols.get(symbol_name, [])
        actual_provider_relocations = []
        for relocation_name, relocation in parsed["relocations"].items():
            if name == "ihk.ko" and relocation_name == ".rela__ksymtab_gpl":
                selected = relocation["records"]
            else:
                selected = [
                    record for record in relocation["records"]
                    if record["symbol"] == symbol_name
                ]
            for record in selected:
                actual_provider_relocations.append({
                    "addend": record["addend"],
                    "offset": record["offset"],
                    "relocation_section": relocation_name,
                    "symbol": record["symbol"],
                    "symbol_index": record["symbol_index"],
                    "symbol_section": record["symbol_section"],
                    "target_section": relocation["target_section"],
                    "type": record["type"],
                })
                require_exact(
                    relocation["flags"], 0x40, name + " " + relocation_name + " flags"
                )
                target = parsed["sections"][relocation["target_section"]]
                if target["flags"] & 0x2 and target["type"] != 1:
                    raise BuildReviewError(
                        "{} {} alloc relocation target is not PROGBITS".format(
                            name, relocation_name
                        )
                    )
                if target["name"] in (".text", ".init.text") and target["flags"] != 0x6:
                    raise BuildReviewError(
                        "{} {} relocation code target is not alloc+exec".format(
                            name, relocation_name
                        )
                    )
                relocation_width = {1: 8, 2: 4}.get(record["type"], 1)
                if record["offset"] + relocation_width > target["size"]:
                    raise BuildReviewError(
                        "{} {} relocation write exceeds its target".format(
                            name, relocation_name
                        )
                    )
        require_exact(
            actual_provider_relocations,
            EXPECTED_PROVIDER_RELOCATIONS[name],
            name + " direct provider relocation closure",
        )
        require_exact(
            len(actual_provider_relocations),
            fact["provider_relocation_count"],
            name + " provider relocation count",
        )
        relocation_sections = []
        for record in actual_provider_relocations:
            if record["relocation_section"] not in relocation_sections:
                relocation_sections.append(record["relocation_section"])
        require_exact(
            relocation_sections,
            fact["provider_relocation_sections"],
            name + " provider relocation sections",
        )
        actual_section_symbols = []
        for expected_symbol in EXPECTED_RELOCATION_SECTION_SYMBOLS[name]:
            symbol_index = expected_symbol["index"]
            if symbol_index >= len(parsed["symbols_by_index"]):
                raise BuildReviewError("{} relocation section symbol is missing".format(name))
            symbol_name_at_index, symbol = parsed["symbols_by_index"][symbol_index]
            symbol_section = None
            if symbol["section_index"] < 0xff00:
                matching_sections = [
                    row["name"] for row in parsed["sections"].values()
                    if row["index"] == symbol["section_index"]
                ]
                symbol_section = matching_sections[0] if len(matching_sections) == 1 else None
            actual_section_symbols.append({
                "binding": symbol["binding"],
                "index": symbol["index"],
                "name": symbol_name_at_index,
                "name_offset": symbol["name_offset"],
                "other": symbol["other"],
                "section": symbol_section,
                "size": symbol["size"],
                "type": symbol["type"],
                "value": symbol["value"],
            })
        require_exact(
            actual_section_symbols,
            EXPECTED_RELOCATION_SECTION_SYMBOLS[name],
            name + " relocation section-symbol shape",
        )
        nm = files[name + ".nm"].decode("utf-8")
        if fact["provider_symbol"] == "defined-exported":
            require_exact(len(symbol_rows), 1, name + " direct provider symbol count")
            provider = symbol_rows[0]
            require_exact(name, EXPECTED_PROVIDER_OBJECT["binary"], "provider object binary")
            provider_section = parsed["sections"].get(EXPECTED_PROVIDER_OBJECT["section"])
            if provider_section is None:
                raise BuildReviewError("{} lacks the direct provider object section".format(name))
            require_exact(provider["binding"], 1, name + " direct provider binding")
            require_exact(provider["other"], 0, name + " direct provider visibility")
            require_exact(provider["type"], 1, name + " direct provider type")
            require_exact(provider["section_index"], provider_section["index"], name + " direct provider section")
            require_exact(
                provider["value"], EXPECTED_PROVIDER_OBJECT["value"],
                name + " direct provider value",
            )
            require_exact(
                provider["size"], EXPECTED_PROVIDER_OBJECT["size"],
                name + " direct provider size",
            )
            if (
                not provider_section["flags"] & 0x2
                or provider["value"] + provider["size"] > provider_section["size"]
            ):
                raise BuildReviewError("{} direct provider definition is out of range".format(name))
            provider_start = provider_section["offset"] + provider["value"]
            provider_content = binary[provider_start:provider_start + provider["size"]]
            require_exact(
                provider_content,
                bytes.fromhex(EXPECTED_PROVIDER_OBJECT["content_hex"]),
                name + " direct provider object content",
            )
            if "__ksymtab_strings" not in parsed["sections"] or "__ksymtab_gpl" not in parsed["sections"]:
                raise BuildReviewError("{} lacks direct GPL export sections".format(name))
            string_index = parsed["sections"]["__ksymtab_strings"]["index"]
            export_index = parsed["sections"]["__ksymtab_gpl"]["index"]
            for export_name, expected_index, expected_value in (
                ("__kstrtab_" + symbol_name, string_index, 0),
                ("__kstrtabns_" + symbol_name, string_index, 26),
                ("__ksymtab_" + symbol_name, export_index, 0),
            ):
                export_rows = symbols.get(export_name, [])
                require_exact(len(export_rows), 1, name + " direct " + export_name + " count")
                export = export_rows[0]
                require_exact(export["binding"], 0, name + " direct " + export_name + " binding")
                require_exact(export["other"], 0, name + " direct " + export_name + " visibility")
                require_exact(export["type"], 0, name + " direct " + export_name + " type")
                require_exact(
                    export["section_index"], expected_index, name + " direct " + export_name + " section"
                )
                require_exact(export["value"], expected_value, name + " direct " + export_name + " value")
                require_exact(export["size"], 0, name + " direct " + export_name + " size")
            require_exact(
                parsed["namespace_data"],
                b"ihk_provider_lifecycle_v1\0MCKERNEL_IHK_V1\0",
                name + " direct export namespace bytes",
            )
            for marker in (
                " __kstrtab_ihk_provider_lifecycle_v1\n",
                " __kstrtabns_ihk_provider_lifecycle_v1\n",
                " __ksymtab_ihk_provider_lifecycle_v1\n",
                " R ihk_provider_lifecycle_v1\n",
            ):
                if nm.count(marker) != 1:
                    raise BuildReviewError("{} provider export differs".format(name))
        else:
            require_exact(len(symbol_rows), 1, name + " direct provider import count")
            require_exact(symbol_rows[0]["binding"], 1, name + " direct provider import binding")
            require_exact(symbol_rows[0]["other"], 0, name + " direct provider import visibility")
            require_exact(symbol_rows[0]["type"], 0, name + " direct provider import type")
            require_exact(symbol_rows[0]["section_index"], 0, name + " direct provider import section")
            require_exact(symbol_rows[0]["value"], 0, name + " direct provider import value")
            require_exact(symbol_rows[0]["size"], 0, name + " direct provider import size")
            for prefix in ("__kstrtab_", "__kstrtabns_", "__ksymtab_"):
                require_exact(symbols.get(prefix + symbol_name, []), [], name + " unexpected direct export")
            require_exact(parsed["namespace_data"], b"", name + " unexpected export namespace")
            if nm.count(" U ihk_provider_lifecycle_v1\n") != 1:
                raise BuildReviewError("{} provider import differs".format(name))
        readelf = files[name + ".readelf"].decode("utf-8")
        for marker in ("Section Headers:", ".text", ".modinfo", "Relocation section"):
            if marker not in readelf:
                raise BuildReviewError("{} readelf output lacks {}".format(name, marker))
        require_exact(
            parsed["structure_sha256"],
            EXPECTED_ELF_STRUCTURE_SHA256[name],
            name + " immutable exact ELF structure",
        )
        require_exact(sha256_bytes(binary), fact["binary_sha256"], name + " binary digest")


def verify_artifact_bytes(data, review, require_outer_identity=True):
    validate_review_object(review)
    if require_outer_identity:
        require_exact(len(data), ARTIFACT_SIZE, "artifact size")
        require_exact(sha256_bytes(data), ARTIFACT_SHA256, "artifact digest")
    try:
        archive = zipfile.ZipFile(io.BytesIO(data), "r")
    except (OSError, zipfile.BadZipFile) as exc:
        raise BuildReviewError("artifact is not a valid ZIP: {}".format(exc))
    with archive:
        if archive.comment:
            raise BuildReviewError("ZIP archive comment is not empty")
        infos = archive.infolist()
        names = [info.filename for info in infos]
        if len(names) != len(set(names)):
            raise BuildReviewError("ZIP contains duplicate paths")
        for name in names:
            safe_relative_path(name, "ZIP member")
        require_exact(sorted(names), list(EXPECTED_ZIP_PATHS), "ZIP path closure")
        files = {}
        index = []
        for info in infos:
            mode = (info.external_attr >> 16) & 0o177777
            if info.create_system != 3 or mode != (stat.S_IFREG | 0o644):
                raise BuildReviewError("ZIP member is not Unix mode 100644: {}".format(info.filename))
            if info.compress_type != zipfile.ZIP_STORED or info.compress_size != info.file_size:
                raise BuildReviewError("ZIP member is not stored verbatim: {}".format(info.filename))
            if info.flag_bits & 0x1 or info.extra or info.comment:
                raise BuildReviewError("ZIP member has forbidden metadata: {}".format(info.filename))
            try:
                payload = archive.read(info)
            except (OSError, RuntimeError, zipfile.BadZipFile) as exc:
                raise BuildReviewError("cannot verify ZIP member {}: {}".format(info.filename, exc))
            if len(payload) != info.file_size:
                raise BuildReviewError("ZIP member size differs: {}".format(info.filename))
            files[info.filename] = payload
            index.append({
                "compressed_size": info.compress_size,
                "crc32": "{:08x}".format(info.CRC),
                "mode": "100644",
                "path": info.filename,
                "size": info.file_size,
            })
        index.sort(key=lambda row: row["path"])
        closure = review["zip_closure"]
        require_exact(sum(row["size"] for row in index), closure["stored_payload_size"], "ZIP payload size")
        require_exact(sha256_bytes(canonical_json_bytes(index)), closure["entry_index_sha256"], "ZIP entry index")

    final_rows = parse_sum_manifest(files["SHA256SUMS"], "SHA256SUMS")
    precheck_rows = parse_sum_manifest(files["PRECHECK_SHA256SUMS"], "PRECHECK_SHA256SUMS")
    require_exact([name for name, unused in final_rows], sorted(set(EXPECTED_ZIP_PATHS) - {"SHA256SUMS"}), "final checksum paths")
    require_exact([name for name, unused in precheck_rows], list(EXPECTED_PRECHECK_NAMES), "precheck checksum paths")
    for label, rows in (("final", final_rows), ("precheck", precheck_rows)):
        records = []
        for name, digest in rows:
            require_exact(sha256_bytes(files[name]), digest, label + " checksum " + name)
            records.append({"path": name, "sha256": digest, "size": len(files[name])})
        require_exact(records, review["inner_closure"][label + "_records"], label + " records")
        require_exact(sha256_bytes(files["SHA256SUMS" if label == "final" else "PRECHECK_SHA256SUMS"]), review["inner_closure"][label + "_manifest_sha256"], label + " manifest digest")

    exact_text = {
        "build.exit-code": b"0\n",
        "build-log.exit-code": b"0\n",
        "build.phase": b"complete\n",
        "commit.sha": (RUNTIME_HEAD_SHA + "\n").encode("ascii"),
        "kernel.release": b"6.12.0\n",
        "workflow-state": b"bootstrap-complete\n",
    }
    for name, expected in exact_text.items():
        require_exact(files[name], expected, name)
    commands = files["build.commands"].decode("utf-8").splitlines()
    require_exact(commands, review["verified_facts"]["build_commands"]["commands"], "build command order")
    require_exact(files["module-targets.txt"].decode("ascii").splitlines(), EXPECTED_MODULE_TARGETS, "module target order")
    require_exact(files["built-module-artifacts.txt"].decode("ascii").splitlines(), EXPECTED_BUILT_MODULES, "built module set")
    values = parse_config(files["resolved.config"])
    for symbol, expected in EXPECTED_CONFIG.items():
        require_exact(values.get(symbol), expected, "resolved " + symbol)
    verify_stage_lock(files["stage-lock.json"], review)

    cmd_paths = sorted(name for name in files if name.startswith(".") and name.endswith(".cmd"))
    require_exact(cmd_paths, [row["path"] for row in EXPECTED_CMD_RECORDS], "captured command paths")
    summaries = [summarize_cmd(name, files[name]) for name in cmd_paths]
    require_exact(summaries, EXPECTED_CMD_RECORDS, "captured command summaries")
    project_sources = sorted(set(
        source for row in summaries for source in row["project_sources"]
    ))
    require_exact(project_sources, sorted(
        row["path"] for row in EXPECTED_STAGE_FILES if row["path"].endswith(".rs")
    ), "compiled Rust source closure")
    verify_modules(files)

    if not files["bzImage"].startswith(b"MZ") or files["bzImage"][0x202:0x206] != b"HdrS":
        raise BuildReviewError("bzImage lacks x86 boot header markers")
    log = files["build.log"].decode("utf-8")
    markers = [
        "Rust is available!",
        "RUSTC [M] drivers/misc/mckernel/ihk.o",
        "RUSTC [M] drivers/misc/mckernel/ihk_smp_x86_64.o",
        "RUSTC [M] drivers/misc/mckernel/mcctrl.o",
        "LD [M]  drivers/misc/mckernel/ihk.ko",
        "LD [M]  drivers/misc/mckernel/ihk-smp-x86_64.ko",
        "LD [M]  drivers/misc/mckernel/mcctrl.ko",
    ]
    for marker in markers:
        if log.count(marker) != 1:
            raise BuildReviewError("build log marker differs: {}".format(marker))
    return {
        "artifact_sha256": sha256_bytes(data),
        "cmd_record_count": len(cmd_paths),
        "module_count": len(EXPECTED_MODULE_FACTS),
        "zip_entry_count": len(EXPECTED_ZIP_PATHS),
    }


def verify_artifact(path, review):
    return verify_artifact_bytes(read_regular_file_once(path, "artifact ZIP"), review)


def build_parser():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path("."))
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--verify-artifact")
    parser.add_argument("--check", action="store_true")
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        path = discover_review(args.repo, args.manifest)
        review = validate_review_object(load_review(path))
        current_head = validate_repository(args.repo, review)
        result = None
        if args.verify_artifact is not None:
            result = verify_artifact(args.verify_artifact, review)
        output = {
            "artifact_verified": result is not None,
            "claims": review["claims"],
            "current_head": current_head,
            "review_id": REVIEW_ID,
        }
        if result is not None:
            output["verified"] = result
        print(json.dumps(output, sort_keys=True, separators=(",", ":")))
        return 0
    except (BuildReviewError, OSError, UnicodeError, zipfile.BadZipFile) as exc:
        print("rk-007 build review failed: {}".format(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
