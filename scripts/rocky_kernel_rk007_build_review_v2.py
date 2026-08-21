#!/usr/bin/env python3
"""Verify one exact-head, bounded, non-crediting RK-007 v2 build review.

The v2 review is deliberately separate from the historical bc60 v1 review.
It binds a fresh exact-head Actions artifact, reparses the transported Kconfig
solver matrix, regenerates the Kbuild link closure from all thirteen ``.cmd``
and three ``.mod`` records, and verifies the three direct module binaries.
None of those checks prove durable retention, toolchain identity, production
readiness, loading, runtime behavior, gate credit, or tracker credit.
"""

from __future__ import print_function

import argparse
import hashlib
import importlib.util
import io
import json
import os
import re
import stat
import struct
import subprocess
import sys
import tempfile
import types
import zipfile
from pathlib import Path, PurePosixPath


SCRIPT_DIRECTORY = os.path.dirname(os.path.realpath(__file__))
REPO_ROOT = os.path.dirname(SCRIPT_DIRECTORY)


class BuildReviewV2Error(RuntimeError):
    """Raised when the v2 review, repository, or artifact fails closed."""


REUSED_MODULE_BINDINGS = {
    "native_rust_kbuild_link_closure.py": (
        53824, "0d01fdbd437fe0d12b804784907c2208e40d3b45206297f4dd90de05411101f8"
    ),
    "native_rust_kconfig_policy.py": (
        7506, "9ad866896a98cfa223978748dec998d8ede51b0a042dfee8776fe77080fd4ba8"
    ),
    "native_rust_kconfig_solver.py": (
        46054, "7a708375beb168f95ce6f6c76b96d47e70176a7f1654645aa99ca1275c9d7984"
    ),
    "rocky_kernel_rk007_build_review.py": (
        136681, "6741d0963c670c2febc97cc527e833f5fcf16e6e878c5831a76e9b67bd62a581"
    ),
}


def _stat_identity(info):
    return (
        info.st_dev, info.st_ino, info.st_mode, info.st_size,
        getattr(info, "st_mtime_ns", int(info.st_mtime * 1000000000)),
        getattr(info, "st_ctime_ns", int(info.st_ctime * 1000000000)),
    )


def _load_exact_module(module_name, file_name):
    path = os.path.join(SCRIPT_DIRECTORY, file_name)
    if os.path.abspath(path) != os.path.realpath(path):
        raise BuildReviewV2Error("reused module path traverses a symlink: {0}".format(file_name))
    try:
        info = os.lstat(path)
    except OSError as error:
        raise BuildReviewV2Error("cannot inspect reused module {0}: {1}".format(file_name, error))
    if not stat.S_ISREG(info.st_mode):
        raise BuildReviewV2Error("reused module is not a regular file: {0}".format(file_name))
    flags = os.O_RDONLY
    if hasattr(os, "O_BINARY"):
        flags |= os.O_BINARY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(path, flags)
        try:
            opened = os.fstat(descriptor)
            if not stat.S_ISREG(opened.st_mode) or _stat_identity(opened) != _stat_identity(info):
                raise BuildReviewV2Error("reused module changed while opened: {0}".format(file_name))
            chunks = []
            while True:
                chunk = os.read(descriptor, 1024 * 1024)
                if not chunk:
                    break
                chunks.append(chunk)
            after = os.fstat(descriptor)
        finally:
            os.close(descriptor)
    except BuildReviewV2Error:
        raise
    except OSError as error:
        raise BuildReviewV2Error("cannot read reused module {0}: {1}".format(file_name, error))
    data = b"".join(chunks)
    try:
        final = os.lstat(path)
    except OSError as error:
        raise BuildReviewV2Error("cannot restat reused module {0}: {1}".format(file_name, error))
    if (
        _stat_identity(after) != _stat_identity(opened)
        or _stat_identity(final) != _stat_identity(info) or len(data) != info.st_size
    ):
        raise BuildReviewV2Error("reused module changed while read: {0}".format(file_name))
    expected_size, expected_sha256 = REUSED_MODULE_BINDINGS[file_name]
    if len(data) != expected_size or hashlib.sha256(data).hexdigest() != expected_sha256:
        raise BuildReviewV2Error("reused module bytes differ: {0}".format(file_name))
    specification = importlib.util.spec_from_loader(module_name, loader=None, origin=path)
    if specification is None or os.path.realpath(specification.origin) != os.path.realpath(path):
        raise BuildReviewV2Error("cannot bind reused-module origin: {0}".format(file_name))
    module = types.ModuleType(module_name)
    module.__file__ = path
    module.__loader__ = None
    module.__package__ = module_name.rpartition(".")[0]
    module.__spec__ = specification
    sys.modules[module_name] = module
    try:
        code = compile(data, path, "exec", dont_inherit=True)
        exec(code, module.__dict__)
    except Exception:
        sys.modules.pop(module_name, None)
        raise
    if os.path.realpath(module.__file__) != os.path.realpath(path):
        raise BuildReviewV2Error("loaded reused-module origin differs: {0}".format(file_name))
    return module


# Load every reused checker from an exact repository path.  The solver's own
# ``from scripts import native_rust_kconfig_policy`` is executed under a
# temporary exact synthetic package, so a foreign regular ``scripts`` package
# on PYTHONPATH cannot win over this repository's PEP-420 namespace.
kconfig_policy = _load_exact_module(
    "_mckernel_rk007_v2_kconfig_policy", "native_rust_kconfig_policy.py"
)
_missing_module = object()
_saved_scripts = sys.modules.get("scripts", _missing_module)
_saved_policy = sys.modules.get("scripts.native_rust_kconfig_policy", _missing_module)
_exact_scripts = types.ModuleType("scripts")
_exact_scripts.__path__ = [SCRIPT_DIRECTORY]
_exact_scripts.__package__ = "scripts"
_exact_scripts.native_rust_kconfig_policy = kconfig_policy
sys.modules["scripts"] = _exact_scripts
sys.modules["scripts.native_rust_kconfig_policy"] = kconfig_policy
try:
    kconfig_solver = _load_exact_module(
        "_mckernel_rk007_v2_kconfig_solver", "native_rust_kconfig_solver.py"
    )
finally:
    if _saved_scripts is _missing_module:
        sys.modules.pop("scripts", None)
    else:
        sys.modules["scripts"] = _saved_scripts
    if _saved_policy is _missing_module:
        sys.modules.pop("scripts.native_rust_kconfig_policy", None)
    else:
        sys.modules["scripts.native_rust_kconfig_policy"] = _saved_policy
link_closure = _load_exact_module(
    "_mckernel_rk007_v2_link_closure", "native_rust_kbuild_link_closure.py"
)
v1_review = _load_exact_module(
    "_mckernel_rk007_v2_historical_review", "rocky_kernel_rk007_build_review.py"
)
REUSED_MODULE_ORIGINS = {
    "kconfig_policy": os.path.realpath(kconfig_policy.__file__),
    "kconfig_solver": os.path.realpath(kconfig_solver.__file__),
    "link_closure": os.path.realpath(link_closure.__file__),
    "v1_review": os.path.realpath(v1_review.__file__),
}


REVIEW_DIRECTORY = Path("host-kernel/rocky/evidence")
REVIEW_GLOB = "rk007-native-build-review-*-v2.json"
SCHEMA_VERSION = 2
REVIEW_ID = "rk-007-native-rust-exact-build-review-ef58860e-v2"
# Filled after the exact ef58860e artifact was downloaded and reviewed.
REVIEW_SHA256 = "d751296653c555b56213593cf3a004200d036d934ff508042797300402d45359"
RUNTIME_HEAD_SHA = "ef58860e4806ee16e2c506e4e93c7b6ad8ad8f4b"
RUNTIME_TREE_SHA = "ae853aa5a48ad85698709a50074cd86d91d02761"
GITHUB_REPOSITORY = "phoenix-hacking/mckernel"
GITHUB_RUN_ID = 32192199024
GITHUB_RUN_ATTEMPT = 1
GITHUB_JOB_ID = 95888740940
ARTIFACT_ID = 9345473288
ARTIFACT_NAME = "native-rust-exact-build-32192199024-1"
ARTIFACT_SIZE = 22510502
ARTIFACT_SHA256 = "d0d63f49311f308b6e1f59e505cf0afc9bde95876ad8955b3ca49bd084a1c84e"
ARTIFACT_EXPIRES_AT = "2026-09-17T22:54:22Z"
CONTAINER_IMAGE = (
    "rockylinux/rockylinux:10.2@sha256:"
    "e372170ca8630f0f03e9b70fdd0bf4a3ce3426b0de7cdba615f06337389de176"
)
HEX_SHA1 = re.compile(r"^[0-9a-f]{40}$")
HEX_SHA256 = re.compile(r"^[0-9a-f]{64}$")
SUM_LINE = re.compile(r"^([0-9a-f]{64})  ([A-Za-z0-9.][A-Za-z0-9_.-]*)$")

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
    "complete_external_build_input_closure": False,
    "configuration_authority_proven": False,
    "credit_eligible": False,
    "durable_archive": False,
    "exact_toolchain_binary_identity_proven": False,
    "gate_claims": EXPECTED_GATE_CLAIMS,
    "independent_kconfig_replay_proven": False,
    "module_loadability_proven": False,
    "production_build_proven": False,
    "runtime_behavior_proven": False,
    "source_patch_authority_proven": False,
    "tracker_credit": False,
}
EXPECTED_CAVEATS = {
    "archive_bytes_committed": False,
    "artifact_retention_is_durable": False,
    "compiler_binaries_archived": False,
    "kbuild_scope": (
        "all thirteen transported top-level .cmd records and all three .mod "
        "object-list records; generated objects, response inputs, headers, libraries, "
        "and toolchain binaries remain outside the transported closure"
    ),
    "kconfig_scope": (
        "the canonical report schema, 54-case oracle, one RUST=n negative, and "
        "reported two-pass identities are reviewed; per-case .config bytes were not "
        "transported and make was not independently replayed"
    ),
    "module_oracle_reuse": (
        "the historical v1 ELF parser and immutable module-structure oracle are reused "
        "only to inspect the fresh v2 module bytes; the historical artifact identity "
        "and review authority are not retargeted"
    ),
    "runtime_or_load_lifecycle_captured": False,
    "source_patch_config_and_toolchain_authorities_inherited": False,
}
EXPECTED_REMAINING_PREREQUISITES = [
    (
        "Durably archive the exact artifact ZIP before its temporary GitHub Actions "
        "retention expires."
    ),
    (
        "Independently replay the Kconfig matrix with retained per-case configuration "
        "bytes before treating its runner-reported digests as replay authority."
    ),
    (
        "Close the selected source, compatibility-patch, resolved-configuration, and "
        "exact toolchain authorities; this bounded artifact review cannot inherit them."
    ),
    (
        "Capture any external build inputs required beyond the thirteen .cmd and three "
        ".mod records before claiming complete build-input closure."
    ),
    (
        "Run the exact modules through reviewed load, dependency, namespace, device, "
        "unload, and failure-path lifecycle evidence before any runtime claim."
    ),
    (
        "Any RK-007 or tracker credit requires a separate authority update; this review "
        "is structurally unable to award it."
    ),
]

EXPECTED_INPUTS = [
    {"git_blob_sha1":"3780ba2239d4b365f5d8bb92e6fbaa505b287c30","mode":"100644","path":".github/workflows/native-rust-host-modules-exact-build.yml","sha256":"5af1cf1ac85d5c62663cb12d2ad7b0aa472d1e87865be3be2d5ea099e4d2854b","size":30870},
    {"git_blob_sha1":"36553a626cb67f0dd54df3713aa9931c904a6b49","mode":"100644","path":"host-kernel/kbuild/Kbuild.in","sha256":"f33c826539ed0807617337ba64a1cb646daf510cc06a44b47243d14e366d67a3","size":371},
    {"git_blob_sha1":"f64e4f539b831815266c7f04413f1cd640aa7abe","mode":"100644","path":"host-kernel/kbuild/Kconfig","sha256":"48c6ba25186281a3a4fe4690c7520b02d8bbe43965e78d3301d2613477c3874f","size":848},
    {"git_blob_sha1":"a17f033fed694044a34e37f9f361ba75e37f6e7c","mode":"100644","path":"host-kernel/kbuild/stage-manifest.json","sha256":"e41b6df1dcd0d8007b23a0795de596e5c775e84f10fe02cf08edd5d199cd4b7a","size":5743},
    {"git_blob_sha1":"ae02ad57d96b7cb46b165f0097116d1d04fb5cd4","mode":"100644","path":"host-kernel/native-rust/abi/x86_64.rs","sha256":"b5980e5b621914a120a0e6b72241477c48aee85615ae4cc76077f3874e35f860","size":18796},
    {"git_blob_sha1":"9bccef539ec17fb91a2920cb0ca81486adcd2b33","mode":"100644","path":"host-kernel/native-rust/ihk.rs","sha256":"53e2b003573804df8d11f34a8290108ac5a0fc15bb559f2f980c38a3316b4a55","size":3818},
    {"git_blob_sha1":"200f4840bfa71521bbbac628d080c0d5f66df0a2","mode":"100644","path":"host-kernel/native-rust/ihk_ioctl.rs","sha256":"3d603424705a9b0fb18725bae1d75f1d279b249b866c15f15f98166d013edfbb","size":9977},
    {"git_blob_sha1":"fc3d63b0396fb09470b14b48c016bb246f93b493","mode":"100644","path":"host-kernel/native-rust/ihk_smp_x86_64.rs","sha256":"f5beb6dae65e486772af5198aa60f77d4e1b86d37b5ee8ae50eb4b34f9b0d74f","size":10271},
    {"git_blob_sha1":"73ce30401de5980e747c4a9197fcb73b571b5ef7","mode":"100644","path":"host-kernel/native-rust/ikc_master.rs","sha256":"f7e8f8bc1cc860a2eb3724457d81bf03b132fa156eac5c5e258a393808e6ca1e","size":26419},
    {"git_blob_sha1":"ce3e82e5b571f11ef5bfcde7394146e618db3fc6","mode":"100644","path":"host-kernel/native-rust/ikc_queue.rs","sha256":"514f9bce452498e5e9394c450532b040c44fce1ac7a6b5158c76f3d4c7270d40","size":17662},
    {"git_blob_sha1":"47b8baf1aac67f4578ffcb6fc8c45a4ca7d8cac7","mode":"100644","path":"host-kernel/native-rust/mcctrl.rs","sha256":"1a8b85c379d6976d90ba462b9386d1bbd7fce83ca152e46bce391e6cfa6b5389","size":3017},
    {"git_blob_sha1":"4cc0d58b65b2717b5bc9b020aaa5a68c0598b420","mode":"100644","path":"host-kernel/native-rust/os_registry.rs","sha256":"29464b8ca1038d87cc0d5f760eb22e0cbd7a1a512ae88f4c550574a784d1e49d","size":17706},
    {"git_blob_sha1":"d18dc2ad253d63492984ab707480dafd01c41034","mode":"100644","path":"host-kernel/native-rust/page_allocator.rs","sha256":"8e2af0cde06cbb70204540b493e8a0a66d5203195ed671235b64bed44d328bc5","size":21301},
    {"git_blob_sha1":"6513b579a64b4e0ccb9f42984a69fe0479adcd91","mode":"100644","path":"host-kernel/native-rust/page_owner_registry.rs","sha256":"443d58fa5b2e423f538c6622ef04d8e34338abc43c5e0fd34811d52fc21f4869","size":13085},
    {"git_blob_sha1":"21483d8c8efbf58d1c6a1c3c99c083646be2f401","mode":"100644","path":"host-kernel/rocky/configs/native-rust-evidence.config","sha256":"a8a71bc16bb84ab7394ef38879d445b849e823ec5944569d9a815c4398947ca3","size":285},
    {"git_blob_sha1":"de815156d011d5620b886894a0eaa16dbe2af9ce","mode":"100644","path":"host-kernel/rocky/configs/rust-minimal.config","sha256":"25dd0fc5647d8addfd650469aad758ca41d7e9599f0d02e34c2025e438114983","size":46},
    {"git_blob_sha1":"529e790c2037caf334517983afd489e16f9882cf","mode":"100644","path":"scripts/rocky_rust_staging.py","sha256":"47d5c0005ae7e8217b723b2c5f1a1f321f90e7aa4d26000aa44ffbf25e426656","size":49797},
    {"git_blob_sha1":"8b571f2c122ae8a6102e8ed83129f584701feea2","mode":"100644","path":"scripts/native_rust_kbuild_link_closure.py","sha256":"0d01fdbd437fe0d12b804784907c2208e40d3b45206297f4dd90de05411101f8","size":53824},
    {"git_blob_sha1":"b6205a0ffa55fefc580f4742ef8b24b928b3fef4","mode":"100644","path":"scripts/native_rust_kconfig_policy.py","sha256":"9ad866896a98cfa223978748dec998d8ede51b0a042dfee8776fe77080fd4ba8","size":7506},
    {"git_blob_sha1":"8211d19c56c56368718fe1420937fd5187530773","mode":"100644","path":"scripts/native_rust_kconfig_solver.py","sha256":"7a708375beb168f95ce6f6c76b96d47e70176a7f1654645aa99ca1275c9d7984","size":46054},
    {"git_blob_sha1":"4842e2e3f58a842de707565bd50a6f710eba4c55","mode":"100644","path":"scripts/rocky_kernel_rk007_build_review.py","sha256":"6741d0963c670c2febc97cc527e833f5fcf16e6e878c5831a76e9b67bd62a581","size":136681},
]
EXPECTED_INPUT_BY_PATH = dict((row["path"], row) for row in EXPECTED_INPUTS)
EXPECTED_HISTORICAL_ORACLE_SOURCE = EXPECTED_INPUT_BY_PATH[
    "scripts/rocky_kernel_rk007_build_review.py"
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
EXPECTED_STAGE_FILE_ORDER = (
    "Kbuild", "Kconfig", "abi/x86_64.rs", "ihk.rs", "ihk_ioctl.rs",
    "ihk_smp_x86_64.rs", "ikc_master.rs", "ikc_queue.rs", "mcctrl.rs",
    "os_registry.rs", "page_allocator.rs", "page_owner_registry.rs",
)
EXPECTED_STAGE_FILE_RECORDS = [
    {
        "path": path,
        "sha256": EXPECTED_INPUT_BY_PATH[STAGE_REPOSITORY_PATHS[path]]["sha256"],
    }
    for path in EXPECTED_STAGE_FILE_ORDER
]

EXPECTED_ZIP_PATHS = tuple(sorted((
    ".ihk-smp-x86_64.ko.cmd", ".ihk-smp-x86_64.mod.cmd",
    ".ihk-smp-x86_64.mod.o.cmd", ".ihk-smp-x86_64.o.cmd",
    ".ihk.ko.cmd", ".ihk.mod.cmd", ".ihk.mod.o.cmd", ".ihk.o.cmd",
    ".ihk_smp_x86_64.o.cmd", ".mcctrl.ko.cmd", ".mcctrl.mod.cmd",
    ".mcctrl.mod.o.cmd", ".mcctrl.o.cmd", "PRECHECK_SHA256SUMS",
    "SHA256SUMS", "build-log.exit-code", "build.commands", "build.exit-code",
    "build.log", "build.phase", "built-module-artifacts.txt", "bzImage",
    "commit.sha", "ihk-smp-x86_64.ko", "ihk-smp-x86_64.ko.modinfo",
    "ihk-smp-x86_64.ko.modinfo-section", "ihk-smp-x86_64.ko.nm",
    "ihk-smp-x86_64.ko.readelf", "ihk-smp-x86_64.mod", "ihk.ko",
    "ihk.ko.modinfo", "ihk.ko.modinfo-section", "ihk.ko.nm", "ihk.ko.readelf",
    "ihk.mod", "kbuild-link-closure.json", "kconfig-solver-matrix.json",
    "kernel.release", "mcctrl.ko", "mcctrl.ko.modinfo",
    "mcctrl.ko.modinfo-section", "mcctrl.ko.nm", "mcctrl.ko.readelf",
    "mcctrl.mod", "module-targets.txt", "resolved.config", "stage-lock.json",
    "workflow-state",
)))
EXPECTED_PRECHECK_NAMES = tuple(sorted((
    "build-log.exit-code", "build.commands", "build.exit-code", "build.log",
    "build.phase", "built-module-artifacts.txt", "commit.sha",
    "ihk-smp-x86_64.ko", "ihk-smp-x86_64.ko.modinfo",
    "ihk-smp-x86_64.ko.modinfo-section", "ihk-smp-x86_64.ko.nm",
    "ihk-smp-x86_64.ko.readelf", "ihk.ko", "ihk.ko.modinfo",
    "ihk.ko.modinfo-section", "ihk.ko.nm", "ihk.ko.readelf",
    "kconfig-solver-matrix.json", "mcctrl.ko", "mcctrl.ko.modinfo",
    "mcctrl.ko.modinfo-section", "mcctrl.ko.nm", "mcctrl.ko.readelf",
    "module-targets.txt", "workflow-state",
)))
EXPECTED_CMD_NAMES = tuple(link_closure.EXPECTED_CMD_NAMES)
EXPECTED_MOD_NAMES = tuple(link_closure.EXPECTED_MOD_NAMES)
EXPECTED_RAW_NAMES = tuple(link_closure.EXPECTED_RAW_RECORD_NAMES)
EXPECTED_MODULE_RECORDS = [
    {"path": "ihk-smp-x86_64.ko", "sha256": "26fe011de606930d6c5d0d076403c66c0ca95b592a2b937330a5b7acd5706934", "size": 645024},
    {"path": "ihk.ko", "sha256": "ba8201909f30b7a8c1763d98e1a8e4398ff3167293cfc3d4be12050ffbc2609b", "size": 688480},
    {"path": "mcctrl.ko", "sha256": "2995c20318ecd2f329b0125937a13e0fca855fec3d470b138f0527244effa5f5", "size": 637392},
]
EXPECTED_MODULE_TARGETS_BYTES = (
    b"drivers/misc/mckernel/ihk.ko\n"
    b"drivers/misc/mckernel/ihk-smp-x86_64.ko\n"
    b"drivers/misc/mckernel/mcctrl.ko\n"
)
EXPECTED_BUILT_MODULES_BYTES = (
    b"drivers/misc/mckernel/ihk-smp-x86_64.ko\n"
    b"drivers/misc/mckernel/ihk.ko\n"
    b"drivers/misc/mckernel/mcctrl.ko\n"
)
EXPECTED_BUILD_COMMANDS_BYTES = (
    b"make -C /__w/_temp/native-rust-source/linux-6.12.0-211.44.1.el10_2 "
    b"O=/__w/_temp/native-rust-build ARCH=x86_64 LLVM=1 rustavailable\n"
    b"make -C /__w/_temp/native-rust-source/linux-6.12.0-211.44.1.el10_2 "
    b"O=/__w/_temp/native-rust-build ARCH=x86_64 LLVM=1 -j2 bzImage\n"
    b"make -C /__w/_temp/native-rust-source/linux-6.12.0-211.44.1.el10_2 "
    b"O=/__w/_temp/native-rust-build ARCH=x86_64 LLVM=1 -j2 "
    b"drivers/misc/mckernel/ihk.ko "
    b"drivers/misc/mckernel/ihk-smp-x86_64.ko "
    b"drivers/misc/mckernel/mcctrl.ko\n"
)
EXPECTED_BUILD_COMMAND_FACT = {
    "count": 3, "ordered": True,
    "sha256": "67677b22b171714068c1c9eedb5f5612812a9f018f717578c63e6e9ae609dfa4",
    "size": 482,
}


def canonical_json_bytes(value):
    try:
        text = json.dumps(
            value, allow_nan=False, ensure_ascii=True, separators=(",", ":"),
            sort_keys=True,
        )
    except (TypeError, ValueError) as error:
        raise BuildReviewV2Error("value is not canonical JSON: {0}".format(error))
    return (text + "\n").encode("ascii")


def reject_duplicate_pairs(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise BuildReviewV2Error("duplicate JSON key: {0!r}".format(key))
        value[key] = item
    return value


def read_json_bytes(data, label, require_canonical=False):
    try:
        value = json.loads(data.decode("ascii"), object_pairs_hook=reject_duplicate_pairs)
    except BuildReviewV2Error:
        raise
    except (UnicodeError, ValueError) as error:
        raise BuildReviewV2Error("{0} is not valid JSON: {1}".format(label, error))
    if type(value) is not dict:
        raise BuildReviewV2Error("{0} must be a JSON object".format(label))
    if require_canonical and data != canonical_json_bytes(value):
        raise BuildReviewV2Error("{0} is not canonical JSON".format(label))
    return value


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def exact_keys(value, expected, label):
    if type(value) is not dict or set(value) != set(expected):
        raise BuildReviewV2Error("{0} has unexpected keys".format(label))
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
        raise BuildReviewV2Error(
            "{0} differs: {1!r} != {2!r}".format(label, actual, expected)
        )


def require_positive_int(value, label):
    if type(value) is not int or value < 1:
        raise BuildReviewV2Error("{0} is not a positive integer".format(label))


def safe_relative_path(value, label):
    if not isinstance(value, str):
        raise BuildReviewV2Error("{0} is not text".format(label))
    path = PurePosixPath(value)
    if (
        path.is_absolute() or not path.parts or "\\" in value or "\x00" in value
        or "//" in value or any(part in ("", ".", "..") for part in value.split("/"))
    ):
        raise BuildReviewV2Error("{0} is unsafe: {1!r}".format(label, value))
    return value


def discover_review(repo, explicit=None):
    repo = Path(repo).resolve()
    if explicit is not None:
        path = explicit if explicit.is_absolute() else repo / explicit
        try:
            relative = path.relative_to(repo).as_posix()
        except ValueError:
            raise BuildReviewV2Error("review manifest is outside the repository")
        return v1_review.repository_file(repo, relative, "v2 review manifest")
    candidates = sorted((repo / REVIEW_DIRECTORY).glob(REVIEW_GLOB))
    if len(candidates) != 1:
        raise BuildReviewV2Error(
            "expected one {0} manifest, found {1}".format(REVIEW_GLOB, len(candidates))
        )
    return v1_review.repository_file(
        repo, candidates[0].relative_to(repo).as_posix(), "v2 review manifest"
    )


def load_review(path):
    data = v1_review.read_regular_file_once(path, "v2 review manifest", expected_mode=0o644)
    require_exact(sha256_bytes(data), REVIEW_SHA256, "review manifest digest")
    return read_json_bytes(data, "v2 review manifest", require_canonical=True)


def _false_tree(value, label):
    if isinstance(value, dict):
        for key in value:
            _false_tree(value[key], label + "." + key)
        return
    if value is not False:
        raise BuildReviewV2Error("{0} must remain false".format(label))


def validate_review_object(review):
    exact_keys(
        review,
        {
            "artifact_closure", "caveats", "claims", "remaining_prerequisites",
            "review_id", "review_kind", "runtime_candidate", "schema_version",
            "source_artifact", "verified_facts",
        },
        "review",
    )
    require_exact(review["schema_version"], SCHEMA_VERSION, "schema version")
    require_exact(review["review_id"], REVIEW_ID, "review id")
    require_exact(
        review["review_kind"],
        "exact-head-native-rust-build-bounded-non-crediting-review",
        "review kind",
    )
    require_exact(review["claims"], EXPECTED_CLAIMS, "bounded claims")
    _false_tree(review["claims"], "claims")
    require_exact(review["caveats"], EXPECTED_CAVEATS, "caveats")
    require_exact(
        review["remaining_prerequisites"], EXPECTED_REMAINING_PREREQUISITES,
        "remaining prerequisites",
    )

    source = exact_keys(
        review["source_artifact"],
        {"artifact", "durable_archive", "expires_at", "github", "retention_days"},
        "source artifact",
    )
    require_exact(source["durable_archive"], False, "durable archive")
    require_exact(source["retention_days"], 30, "retention days")
    require_exact(source["expires_at"], ARTIFACT_EXPIRES_AT, "artifact expiry")
    github = exact_keys(
        source["github"],
        {"job_id", "repository", "run_attempt", "run_id", "runtime_head_sha", "runtime_tree_sha"},
        "GitHub source",
    )
    require_exact(
        github,
        {
            "job_id": GITHUB_JOB_ID, "repository": GITHUB_REPOSITORY,
            "run_attempt": GITHUB_RUN_ATTEMPT, "run_id": GITHUB_RUN_ID,
            "runtime_head_sha": RUNTIME_HEAD_SHA, "runtime_tree_sha": RUNTIME_TREE_SHA,
        },
        "GitHub source",
    )
    artifact = exact_keys(
        source["artifact"], {"archive_file_name", "id", "name", "sha256", "size"},
        "artifact",
    )
    require_exact(
        artifact,
        {
            "archive_file_name": ARTIFACT_NAME + ".zip", "id": ARTIFACT_ID,
            "name": ARTIFACT_NAME, "sha256": ARTIFACT_SHA256, "size": ARTIFACT_SIZE,
        },
        "artifact identity",
    )
    for value, label in (
        (github["run_id"], "run id"), (github["run_attempt"], "run attempt"),
        (github["job_id"], "job id"), (artifact["id"], "artifact id"),
        (artifact["size"], "artifact size"),
    ):
        require_positive_int(value, label)

    runtime = exact_keys(
        review["runtime_candidate"], {"committed_inputs", "container", "head_sha", "tree_sha"},
        "runtime candidate",
    )
    require_exact(runtime["head_sha"], RUNTIME_HEAD_SHA, "runtime head")
    require_exact(runtime["tree_sha"], RUNTIME_TREE_SHA, "runtime tree")
    require_exact(runtime["committed_inputs"], EXPECTED_INPUTS, "committed inputs")
    require_exact(
        runtime["container"],
        {
            "image": CONTAINER_IMAGE,
            "manifest_digest": CONTAINER_IMAGE.rsplit("@sha256:", 1)[1],
            "runtime_architecture": "x86_64", "runtime_os_id": "rocky",
            "runtime_os_version_id": "10.2",
        },
        "runtime container",
    )

    closure = exact_keys(
        review["artifact_closure"],
        {
            "compressed_payload_size", "entry_count", "entry_index_sha256",
            "entry_flag_bits",
            "final_checksum_record_count", "final_checksum_sha256", "paths",
            "precheck_checksum_record_count", "precheck_checksum_sha256",
            "stored_payload_size",
        },
        "artifact closure",
    )
    require_exact(closure["entry_count"], len(EXPECTED_ZIP_PATHS), "ZIP entry count")
    require_exact(closure["entry_flag_bits"], 0x8, "ZIP data-descriptor flag")
    require_exact(closure["paths"], list(EXPECTED_ZIP_PATHS), "ZIP path closure")
    for key in ("compressed_payload_size", "stored_payload_size"):
        require_positive_int(closure[key], "artifact closure " + key)
    require_exact(
        closure["compressed_payload_size"], closure["stored_payload_size"],
        "stored ZIP payload",
    )
    require_exact(
        closure["final_checksum_record_count"], len(EXPECTED_ZIP_PATHS) - 1,
        "final checksum row count",
    )
    require_exact(
        closure["precheck_checksum_record_count"], len(EXPECTED_PRECHECK_NAMES),
        "precheck checksum row count",
    )
    for key in (
        "entry_index_sha256", "final_checksum_sha256", "precheck_checksum_sha256",
    ):
        value = closure[key]
        if type(value) is not str or HEX_SHA256.fullmatch(value) is None:
            raise BuildReviewV2Error("artifact closure {0} is invalid".format(key))

    facts = exact_keys(
        review["verified_facts"],
        {
            "artifact_state", "build_commands", "historical_oracle_source",
            "kbuild_link_closure", "kconfig_solver_matrix", "modules",
            "resolved_configuration",
        },
        "verified facts",
    )
    require_exact(
        facts["historical_oracle_source"], EXPECTED_HISTORICAL_ORACLE_SOURCE,
        "historical module-oracle source",
    )
    require_exact(
        facts["build_commands"], EXPECTED_BUILD_COMMAND_FACT, "build command fact"
    )
    state = exact_keys(
        facts["artifact_state"],
        {"build_exit_code", "build_log_exit_code", "build_phase", "kernel_release", "workflow_state"},
        "artifact state",
    )
    require_exact(
        state,
        {"build_exit_code": 0, "build_log_exit_code": 0, "build_phase": "complete", "kernel_release": "6.12.0", "workflow_state": "bootstrap-complete"},
        "artifact state",
    )
    config = exact_keys(
        facts["resolved_configuration"],
        {"required_symbols", "stable_resolution_claimed"}, "resolved configuration",
    )
    require_exact(
        config["required_symbols"],
        {
            "CONFIG_MCKERNEL_IHK_RUST": "m",
            "CONFIG_MCKERNEL_IHK_SMP_X86_64_RUST": "m",
            "CONFIG_MCKERNEL_MCCTRL_RUST": "m", "CONFIG_MODULES": "y",
            "CONFIG_RUST": "y", "CONFIG_WERROR": "y",
        },
        "required configuration",
    )
    require_exact(config["stable_resolution_claimed"], False, "config authority claim")

    solver = exact_keys(
        facts["kconfig_solver_matrix"],
        {
            "case_count", "independent_replay_proven", "make_invocation_count",
            "path", "per_case_config_bytes_retained", "schema_version", "sha256",
            "size", "status", "two_pass_byte_identical_count",
        },
        "solver fact",
    )
    require_exact(solver["path"], "kconfig-solver-matrix.json", "solver path")
    require_exact(solver["schema_version"], 1, "solver schema")
    require_exact(solver["status"], "captured-unreviewed", "solver status")
    require_exact(solver["case_count"], 54, "solver cases")
    require_exact(solver["make_invocation_count"], 110, "solver make count")
    require_exact(solver["two_pass_byte_identical_count"], 54, "solver identity count")
    require_exact(solver["independent_replay_proven"], False, "solver replay claim")
    require_exact(solver["per_case_config_bytes_retained"], False, "solver byte retention")
    _validate_digest_fact(solver, "solver fact")

    link = exact_keys(
        facts["kbuild_link_closure"],
        {
            "cmd_record_count", "mod_record_count", "path", "raw_record_count",
            "raw_records", "raw_records_sha256", "schema_id", "sha256", "size",
        },
        "link fact",
    )
    require_exact(link["path"], "kbuild-link-closure.json", "link report path")
    require_exact(link["schema_id"], link_closure.SCHEMA_ID, "link schema")
    require_exact(link["cmd_record_count"], 13, "command record count")
    require_exact(link["mod_record_count"], 3, "mod record count")
    require_exact(link["raw_record_count"], 16, "raw record count")
    require_exact(
        [row["name"] for row in link["raw_records"]], list(EXPECTED_RAW_NAMES),
        "raw record names",
    )
    for index, record in enumerate(link["raw_records"]):
        label = "raw record {0}".format(index)
        exact_keys(record, {"name", "sha256", "size"}, label)
        safe_relative_path(record["name"], label + " name")
        _validate_digest_fact(record, label)
    require_exact(
        sha256_bytes(link_closure.canonical_bytes(link["raw_records"])),
        link["raw_records_sha256"], "raw record projection digest",
    )
    _validate_digest_fact(link, "link fact")

    require_exact(facts["modules"], EXPECTED_MODULE_RECORDS, "module records")
    for index, record in enumerate(facts["modules"]):
        _validate_digest_fact(record, "module {0}".format(index))
    return review


def _validate_digest_fact(record, label):
    digest = record.get("sha256")
    size = record.get("size")
    if type(digest) is not str or HEX_SHA256.fullmatch(digest) is None:
        raise BuildReviewV2Error("{0} digest is invalid".format(label))
    require_positive_int(size, label + " size")


def _git(repo, arguments, allow_failure=False):
    completed = v1_review.run_git(repo, arguments, allow_failure=allow_failure)
    if completed.returncode != 0 and not allow_failure:
        raise BuildReviewV2Error("git command failed")
    return completed


def _git_text(repo, arguments, label):
    raw = _git(repo, arguments).stdout
    try:
        return raw.decode("ascii").strip()
    except UnicodeError as error:
        raise BuildReviewV2Error("{0} is not ASCII: {1}".format(label, error))


def _tree_record(repo, revision, path, label):
    safe_relative_path(path, label + " path")
    raw = _git(repo, ["ls-tree", "-z", revision, "--", path]).stdout
    if not raw.endswith(b"\0") or raw.count(b"\0") != 1:
        raise BuildReviewV2Error("{0} is absent or ambiguous".format(label))
    try:
        metadata, actual_path = raw[:-1].split(b"\t", 1)
        mode, kind, object_id = metadata.decode("ascii").split(" ")
        actual_path = actual_path.decode("utf-8")
    except (UnicodeError, ValueError) as error:
        raise BuildReviewV2Error("{0} tree row is malformed: {1}".format(label, error))
    if actual_path != path or kind != "blob" or mode != "100644" or HEX_SHA1.fullmatch(object_id) is None:
        raise BuildReviewV2Error("{0} tree row differs".format(label))
    data = _git(repo, ["cat-file", "blob", object_id]).stdout
    return {
        "git_blob_sha1": object_id, "mode": mode, "path": path,
        "sha256": sha256_bytes(data), "size": len(data),
    }


def _index_record(repo, path, label):
    raw = _git(repo, ["ls-files", "--stage", "-z", "--", path]).stdout
    if not raw.endswith(b"\0") or raw.count(b"\0") != 1:
        raise BuildReviewV2Error("{0} index row is absent or ambiguous".format(label))
    try:
        metadata, actual_path = raw[:-1].split(b"\t", 1)
        mode, object_id, stage_number = metadata.decode("ascii").split(" ")
        actual_path = actual_path.decode("utf-8")
    except (UnicodeError, ValueError) as error:
        raise BuildReviewV2Error("{0} index row is malformed: {1}".format(label, error))
    if actual_path != path or mode != "100644" or stage_number != "0" or HEX_SHA1.fullmatch(object_id) is None:
        raise BuildReviewV2Error("{0} index row differs".format(label))
    return object_id


def validate_repository(repo, review):
    review = validate_review_object(review)
    repo = Path(repo).resolve()
    runtime = review["runtime_candidate"]
    require_exact(_git_text(repo, ["cat-file", "-t", RUNTIME_HEAD_SHA], "runtime type"), "commit", "runtime object type")
    require_exact(_git_text(repo, ["rev-parse", RUNTIME_HEAD_SHA + "^{tree}"], "runtime tree"), RUNTIME_TREE_SHA, "runtime tree")
    require_exact(_git_text(repo, ["cat-file", "-t", "HEAD"], "HEAD type"), "commit", "current HEAD object type")
    current = _git_text(repo, ["rev-parse", "HEAD"], "current HEAD")
    if HEX_SHA1.fullmatch(current) is None:
        raise BuildReviewV2Error("current HEAD is invalid")
    ancestry = _git(repo, ["merge-base", "--is-ancestor", RUNTIME_HEAD_SHA, current], allow_failure=True)
    if ancestry.returncode != 0:
        raise BuildReviewV2Error("current HEAD is not a descendant of the reviewed runtime")

    snapshots = []
    for index, expected in enumerate(runtime["committed_inputs"]):
        label = "committed input {0}".format(index)
        require_exact(_tree_record(repo, RUNTIME_HEAD_SHA, expected["path"], label + " runtime"), expected, label + " runtime")
        require_exact(_tree_record(repo, current, expected["path"], label + " current"), expected, label + " current")
        require_exact(_index_record(repo, expected["path"], label), expected["git_blob_sha1"], label + " index blob")
        path = v1_review.repository_file(repo, expected["path"], label + " worktree")
        data = v1_review.read_regular_file_once(path, label + " worktree", expected_mode=0o644)
        require_exact(len(data), expected["size"], label + " worktree size")
        require_exact(sha256_bytes(data), expected["sha256"], label + " worktree digest")
        snapshots.append((path, data, expected))

    require_exact(_git_text(repo, ["rev-parse", "HEAD"], "final current HEAD"), current, "repository HEAD snapshot")
    for index, snapshot in enumerate(snapshots):
        path, data, expected = snapshot
        label = "committed input {0}".format(index)
        require_exact(_index_record(repo, expected["path"], label + " final"), expected["git_blob_sha1"], label + " final index")
        require_exact(v1_review.read_regular_file_once(path, label + " final", expected_mode=0o644), data, label + " worktree snapshot")
    return current


def parse_sum_manifest(data, label):
    try:
        text = data.decode("ascii")
    except UnicodeError as error:
        raise BuildReviewV2Error("{0} is not ASCII: {1}".format(label, error))
    if not text.endswith("\n") or "\r" in text or "\x00" in text:
        raise BuildReviewV2Error("{0} is not canonical LF text".format(label))
    rows = []
    seen = set()
    for line in text.splitlines():
        match = SUM_LINE.fullmatch(line)
        if match is None:
            raise BuildReviewV2Error("{0} contains a malformed row".format(label))
        name = safe_relative_path(match.group(2), label + " path")
        if name in seen:
            raise BuildReviewV2Error("{0} contains duplicate paths".format(label))
        seen.add(name)
        rows.append((name, match.group(1)))
    if [row[0] for row in rows] != sorted(seen):
        raise BuildReviewV2Error("{0} paths are not sorted".format(label))
    return rows


def read_zip_members(data, expected_paths=EXPECTED_ZIP_PATHS, expected_flag_bits=0x8):
    try:
        archive = zipfile.ZipFile(io.BytesIO(data), "r")
    except (OSError, zipfile.BadZipFile) as error:
        raise BuildReviewV2Error("artifact is not a valid ZIP: {0}".format(error))
    with archive:
        if archive.comment:
            raise BuildReviewV2Error("ZIP archive comment is not empty")
        infos = archive.infolist()
        names = [info.filename for info in infos]
        if len(names) != len(set(names)):
            raise BuildReviewV2Error("ZIP contains duplicate paths")
        for name in names:
            safe_relative_path(name, "ZIP member")
        require_exact(sorted(names), list(expected_paths), "ZIP path closure")
        offsets = [info.header_offset for info in infos]
        if not offsets or offsets[0] != 0 or offsets != sorted(set(offsets)):
            raise BuildReviewV2Error("ZIP local-header offsets are not a closed sequence")
        if sum(info.file_size for info in infos) > 64 * 1024 * 1024:
            raise BuildReviewV2Error("ZIP declared payload is too large")
        central_start = archive.start_dir
        central_offset = central_start
        central_rows = []
        for info in infos:
            if central_offset + 46 > len(data):
                raise BuildReviewV2Error("ZIP central header is truncated")
            try:
                central = struct.unpack_from("<4s6H3I5H2I", data, central_offset)
            except struct.error as error:
                raise BuildReviewV2Error("ZIP central header is malformed: {0}".format(error))
            (
                central_signature, made_by, needed, central_flags, central_method,
                central_time, central_date, central_crc, central_compressed_size,
                central_file_size, central_name_length, central_extra_length,
                central_comment_length, disk_start, central_internal_attr,
                central_external_attr, local_header_offset,
            ) = central
            if central_signature != b"PK\x01\x02":
                raise BuildReviewV2Error("ZIP central-header signature differs")
            central_name_start = central_offset + 46
            central_name_end = central_name_start + central_name_length
            central_end = (
                central_name_end + central_extra_length + central_comment_length
            )
            try:
                expected_name = info.filename.encode("ascii")
            except UnicodeError as error:
                raise BuildReviewV2Error("ZIP central name is not ASCII: {0}".format(error))
            if (
                central_end > len(data)
                or data[central_name_start:central_name_end] != expected_name
                or central_extra_length != 0
                or central_comment_length != 0
            ):
                raise BuildReviewV2Error("ZIP central name/metadata differs: {0}".format(info.filename))
            if (
                central_flags != info.flag_bits
                or central_method != info.compress_type
                or central_crc != info.CRC
                or central_compressed_size != info.compress_size
                or central_file_size != info.file_size
                or local_header_offset != info.header_offset
            ):
                raise BuildReviewV2Error("ZIP central record differs: {0}".format(info.filename))
            if (
                disk_start != 0 or central_internal_attr != info.internal_attr
                or central_external_attr != info.external_attr
            ):
                raise BuildReviewV2Error("ZIP central attributes differ: {0}".format(info.filename))
            central_rows.append({
                "date": central_date, "external_attr": central_external_attr,
                "flags": central_flags, "internal_attr": central_internal_attr,
                "made_by": made_by, "method": central_method, "needed": needed,
                "time": central_time,
            })
            central_offset = central_end
        if central_offset + 22 != len(data):
            raise BuildReviewV2Error("ZIP has trailing bytes or a noncanonical EOCD")
        try:
            eocd = struct.unpack_from("<4s4H2IH", data, central_offset)
        except struct.error as error:
            raise BuildReviewV2Error("ZIP EOCD is malformed: {0}".format(error))
        (
            eocd_signature, disk_number, central_disk, disk_entries, total_entries,
            central_size, central_directory_offset, eocd_comment_length,
        ) = eocd
        if (
            eocd_signature != b"PK\x05\x06" or disk_number != 0 or central_disk != 0
            or disk_entries != len(infos) or total_entries != len(infos)
            or central_size != central_offset - central_start
            or central_directory_offset != central_start or eocd_comment_length != 0
        ):
            raise BuildReviewV2Error("ZIP EOCD differs from the closed single-disk shape")
        files = {}
        index = []
        for position, info in enumerate(infos):
            central = central_rows[position]
            mode = (info.external_attr >> 16) & 0o177777
            if info.create_system != 3 or mode != (stat.S_IFREG | 0o644):
                raise BuildReviewV2Error("ZIP member is not Unix mode 100644: {0}".format(info.filename))
            if (
                info.internal_attr != 0 or info.extract_version != 20
                or central["needed"] != 20
            ):
                raise BuildReviewV2Error("ZIP member internal/extract metadata differs: {0}".format(info.filename))
            if expected_flag_bits == 0x8 and (
                info.external_attr != 0x81A40020 or info.create_version != 45
                or central["made_by"] != 0x032D
            ):
                raise BuildReviewV2Error("ZIP GitHub external/create metadata differs: {0}".format(info.filename))
            if info.compress_type != zipfile.ZIP_STORED or info.compress_size != info.file_size:
                raise BuildReviewV2Error("ZIP member is not stored verbatim: {0}".format(info.filename))
            if info.flag_bits != expected_flag_bits or info.extra or info.comment:
                raise BuildReviewV2Error("ZIP member has forbidden metadata: {0}".format(info.filename))
            if info.header_offset + 30 > len(data):
                raise BuildReviewV2Error("ZIP local header is truncated: {0}".format(info.filename))
            try:
                local = struct.unpack_from("<4s5H3I2H", data, info.header_offset)
            except struct.error as error:
                raise BuildReviewV2Error(
                    "ZIP local header is malformed for {0}: {1}".format(
                        info.filename, error
                    )
                )
            (
                signature, local_version, local_flags, local_method,
                local_time, local_date, local_crc, local_compressed_size,
                local_file_size, name_length, extra_length,
            ) = local
            if signature != b"PK\x03\x04":
                raise BuildReviewV2Error("ZIP local-header signature differs: {0}".format(info.filename))
            if local_flags != info.flag_bits or local_flags != expected_flag_bits:
                raise BuildReviewV2Error("ZIP local/central flag bits differ: {0}".format(info.filename))
            if local_method != info.compress_type:
                raise BuildReviewV2Error("ZIP local/central method differs: {0}".format(info.filename))
            if (
                local_version != central["needed"]
                or local_time != central["time"] or local_date != central["date"]
            ):
                raise BuildReviewV2Error("ZIP local/central version or timestamp differs: {0}".format(info.filename))
            name_start = info.header_offset + 30
            name_end = name_start + name_length
            extra_end = name_end + extra_length
            try:
                expected_name = info.filename.encode("ascii")
            except UnicodeError as error:
                raise BuildReviewV2Error("ZIP local name is not ASCII: {0}".format(error))
            if data[name_start:name_end] != expected_name or extra_length != 0 or extra_end > len(data):
                raise BuildReviewV2Error("ZIP local name/extra differs: {0}".format(info.filename))
            payload_end = extra_end + info.compress_size
            if payload_end > len(data):
                raise BuildReviewV2Error("ZIP local payload is truncated: {0}".format(info.filename))
            if expected_flag_bits == 0x8:
                if (local_crc, local_compressed_size, local_file_size) != (0, 0, 0):
                    raise BuildReviewV2Error("ZIP descriptor local fields are nonzero: {0}".format(info.filename))
                descriptor_end = payload_end + 16
                if descriptor_end > len(data):
                    raise BuildReviewV2Error("ZIP data descriptor is truncated: {0}".format(info.filename))
                descriptor = struct.unpack_from("<4sIII", data, payload_end)
                if descriptor != (
                    b"PK\x07\x08", info.CRC, info.compress_size, info.file_size
                ):
                    raise BuildReviewV2Error("ZIP data descriptor differs: {0}".format(info.filename))
                local_end = descriptor_end
            elif expected_flag_bits == 0:
                if (local_crc, local_compressed_size, local_file_size) != (
                    info.CRC, info.compress_size, info.file_size
                ):
                    raise BuildReviewV2Error("ZIP local size/CRC fields differ: {0}".format(info.filename))
                local_end = payload_end
            else:
                raise BuildReviewV2Error("ZIP flag policy is unsupported")
            expected_next = (
                infos[position + 1].header_offset
                if position + 1 < len(infos) else archive.start_dir
            )
            if local_end != expected_next:
                raise BuildReviewV2Error("ZIP local record sequence has a gap: {0}".format(info.filename))
            try:
                payload = archive.read(info)
            except (OSError, RuntimeError, zipfile.BadZipFile) as error:
                raise BuildReviewV2Error("cannot read ZIP member {0}: {1}".format(info.filename, error))
            if len(payload) != info.file_size:
                raise BuildReviewV2Error("ZIP member size differs: {0}".format(info.filename))
            files[info.filename] = payload
            index.append({
                "compressed_size": info.compress_size, "crc32": "{0:08x}".format(info.CRC),
                "create_version": info.create_version,
                "data_descriptor": expected_flag_bits == 0x8,
                "dos_date": central["date"], "dos_time": central["time"],
                "external_attr": "{0:08x}".format(info.external_attr),
                "extract_version": info.extract_version,
                "flag_bits": info.flag_bits, "local_flag_bits": local_flags,
                "internal_attr": info.internal_attr,
                "mode": "100644",
                "path": info.filename, "size": info.file_size,
            })
        index.sort(key=lambda row: row["path"])
    return files, index


def verify_inner_checksums(files, review):
    closure = review["artifact_closure"]
    rows = parse_sum_manifest(files["SHA256SUMS"], "SHA256SUMS")
    require_exact([row[0] for row in rows], sorted(set(EXPECTED_ZIP_PATHS) - {"SHA256SUMS"}), "final checksum paths")
    require_exact(len(rows), closure["final_checksum_record_count"], "final checksum count")
    require_exact(sha256_bytes(files["SHA256SUMS"]), closure["final_checksum_sha256"], "final checksum manifest digest")
    for name, expected in rows:
        require_exact(sha256_bytes(files[name]), expected, "final checksum " + name)
    # PRECHECK is itself covered above, but its pre-validation member set and
    # bytes are also closed explicitly.
    precheck_rows = parse_sum_manifest(
        files["PRECHECK_SHA256SUMS"], "PRECHECK_SHA256SUMS"
    )
    require_exact(
        [row[0] for row in precheck_rows], list(EXPECTED_PRECHECK_NAMES),
        "precheck checksum paths",
    )
    require_exact(
        len(precheck_rows), closure["precheck_checksum_record_count"],
        "precheck checksum count",
    )
    require_exact(
        sha256_bytes(files["PRECHECK_SHA256SUMS"]),
        closure["precheck_checksum_sha256"], "precheck checksum manifest digest",
    )
    for name, expected in precheck_rows:
        if name not in files:
            raise BuildReviewV2Error("PRECHECK names an absent member: {0}".format(name))
        require_exact(sha256_bytes(files[name]), expected, "precheck checksum " + name)


def verify_solver_report(data, fact, resolved_config):
    if not isinstance(resolved_config, bytes):
        raise BuildReviewV2Error("solver resolved configuration bytes are required")
    _validate_digest_fact(fact, "solver fact")
    require_exact(len(data), fact["size"], "solver report size")
    require_exact(sha256_bytes(data), fact["sha256"], "solver report digest")
    try:
        document = kconfig_solver.validate_matrix_bytes(data)
    except kconfig_solver.SolverError as error:
        raise BuildReviewV2Error("solver report: {0}".format(error))
    require_exact(document["status"], "captured-unreviewed", "solver report status")
    require_exact(document["claims"]["independent_replay_proven"], False, "solver replay claim")
    require_exact(document["claims"]["per_case_config_bytes_retained"], False, "solver bytes claim")
    staged = EXPECTED_INPUT_BY_PATH["host-kernel/kbuild/Kconfig"]
    require_exact(
        document["inputs"]["staged_kconfig"]["sha256"], staged["sha256"],
        "solver staged Kconfig digest",
    )
    require_exact(
        document["inputs"]["staged_kconfig"]["size"], staged["size"],
        "solver staged Kconfig size",
    )
    require_exact(
        document["inputs"]["seed_config"]["sha256"],
        sha256_bytes(resolved_config), "solver seed config digest",
    )
    require_exact(
        document["inputs"]["seed_config"]["size"], len(resolved_config),
        "solver seed config size",
    )
    return document


def _write_temp_file(directory, name, data):
    safe_relative_path(name, "temporary member")
    path = os.path.join(directory, name)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(path, flags, 0o600)
    try:
        view = memoryview(data)
        offset = 0
        while offset < len(view):
            written = os.write(descriptor, view[offset:])
            if written <= 0:
                raise BuildReviewV2Error("short write for temporary member")
            offset += written
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    os.chmod(path, 0o644)
    return path


def verify_stage_lock_binding(data):
    stage = read_json_bytes(data, "stage lock", require_canonical=True)
    exact_keys(
        stage,
        {
            "credit_eligible", "files", "manifest_sha256", "parent_integration",
            "production_readiness_blockers", "profile_id", "purpose",
            "schema_version", "target",
        },
        "stage lock",
    )
    require_exact(stage["credit_eligible"], False, "stage lock credit claim")
    require_exact(stage["purpose"], "compiler-evidence-only", "stage lock purpose")
    require_exact(stage["schema_version"], 2, "stage lock schema")
    require_exact(
        stage["profile_id"], link_closure.STAGE_PROFILE_ID, "stage lock profile"
    )
    require_exact(
        stage["manifest_sha256"],
        EXPECTED_INPUT_BY_PATH["host-kernel/kbuild/stage-manifest.json"]["sha256"],
        "stage lock manifest binding",
    )
    require_exact(
        stage["files"], EXPECTED_STAGE_FILE_RECORDS,
        "stage lock exact repository file bindings",
    )
    return stage


def verify_link_report(files, fact):
    _validate_digest_fact(fact, "link fact")
    report = files["kbuild-link-closure.json"]
    require_exact(len(report), fact["size"], "link report size")
    require_exact(sha256_bytes(report), fact["sha256"], "link report digest")
    verify_stage_lock_binding(files["stage-lock.json"])
    with tempfile.TemporaryDirectory(prefix="rk007-v2-link-") as directory:
        for name in EXPECTED_RAW_NAMES:
            _write_temp_file(directory, name, files[name])
        stage_path = _write_temp_file(directory, "stage-lock.json", files["stage-lock.json"])
        report_path = _write_temp_file(directory, "kbuild-link-closure.json", report)
        try:
            value = link_closure.check_kbuild_link_closure(
                directory, report_path, stage_lock_path=stage_path
            )
        except link_closure.LinkClosureError as error:
            raise BuildReviewV2Error("link closure: {0}".format(error))
    require_exact(value["raw_record_names"], list(EXPECTED_RAW_NAMES), "reparsed raw record names")
    require_exact(value["raw_records"], fact["raw_records"], "reparsed raw records")
    require_exact(value["raw_records_sha256"], fact["raw_records_sha256"], "reparsed raw record digest")
    require_exact(
        value["stage_lock"]["manifest_sha256"],
        EXPECTED_INPUT_BY_PATH["host-kernel/kbuild/stage-manifest.json"]["sha256"],
        "link stage manifest binding",
    )
    expected_sources = [
        {
            "path": path,
            "stage_sha256": EXPECTED_INPUT_BY_PATH[repository_path]["sha256"],
        }
        for path, repository_path in (
            (item, STAGE_REPOSITORY_PATHS[item])
            for item in EXPECTED_STAGE_FILE_ORDER
        )
        if path.endswith(".rs")
    ]
    require_exact(value["source_closure"], expected_sources, "link source/repository binding")
    for claim, result in value["claims"].items():
        require_exact(result, False, "link report claim " + claim)
    return value


def verify_modules(files, facts):
    require_exact(facts, EXPECTED_MODULE_RECORDS, "module facts")
    for fact in facts:
        data = files[fact["path"]]
        require_exact(len(data), fact["size"], fact["path"] + " size")
        require_exact(sha256_bytes(data), fact["sha256"], fact["path"] + " digest")
    try:
        v1_review.verify_modules(files)
    except v1_review.BuildReviewError as error:
        raise BuildReviewV2Error("module structural oracle: {0}".format(error))


def verify_exact_output_texts(files):
    exact = {
        "build.exit-code": b"0\n", "build-log.exit-code": b"0\n",
        "build.commands": EXPECTED_BUILD_COMMANDS_BYTES,
        "build.phase": b"complete\n",
        "built-module-artifacts.txt": EXPECTED_BUILT_MODULES_BYTES,
        "commit.sha": (RUNTIME_HEAD_SHA + "\n").encode("ascii"),
        "kernel.release": b"6.12.0\n",
        "module-targets.txt": EXPECTED_MODULE_TARGETS_BYTES,
        "workflow-state": b"bootstrap-complete\n",
    }
    for name, expected in exact.items():
        if name not in files:
            raise BuildReviewV2Error("exact output is absent: {0}".format(name))
        require_exact(files[name], expected, name)


def verify_build_outputs(files):
    verify_exact_output_texts(files)
    if not files["bzImage"].startswith(b"MZ") or files["bzImage"][0x202:0x206] != b"HdrS":
        raise BuildReviewV2Error("bzImage lacks exact x86 boot header markers")
    try:
        log = files["build.log"].decode("utf-8")
    except UnicodeError as error:
        raise BuildReviewV2Error("build log is not UTF-8: {0}".format(error))
    markers = (
        "Rust is available!",
        "RUSTC [M] drivers/misc/mckernel/ihk.o",
        "RUSTC [M] drivers/misc/mckernel/ihk_smp_x86_64.o",
        "RUSTC [M] drivers/misc/mckernel/mcctrl.o",
        "LD [M]  drivers/misc/mckernel/ihk.ko",
        "LD [M]  drivers/misc/mckernel/ihk-smp-x86_64.ko",
        "LD [M]  drivers/misc/mckernel/mcctrl.ko",
    )
    for marker in markers:
        if log.count(marker) != 1:
            raise BuildReviewV2Error("build log marker differs: {0}".format(marker))


def verify_artifact_bytes(data, review):
    validate_review_object(review)
    require_exact(len(data), ARTIFACT_SIZE, "artifact size")
    require_exact(sha256_bytes(data), ARTIFACT_SHA256, "artifact digest")
    files, index = read_zip_members(
        data, expected_flag_bits=review["artifact_closure"]["entry_flag_bits"]
    )
    closure = review["artifact_closure"]
    require_exact(sum(row["size"] for row in index), closure["stored_payload_size"], "ZIP payload size")
    require_exact(sum(row["compressed_size"] for row in index), closure["compressed_payload_size"], "ZIP compressed size")
    require_exact(sha256_bytes(canonical_json_bytes(index)), closure["entry_index_sha256"], "ZIP entry index")
    verify_inner_checksums(files, review)

    verify_build_outputs(files)
    config = v1_review.parse_config(files["resolved.config"])
    for symbol, expected in review["verified_facts"]["resolved_configuration"]["required_symbols"].items():
        require_exact(config.get(symbol), expected, "resolved " + symbol)
    verify_solver_report(
        files["kconfig-solver-matrix.json"],
        review["verified_facts"]["kconfig_solver_matrix"],
        resolved_config=files["resolved.config"],
    )
    verify_link_report(files, review["verified_facts"]["kbuild_link_closure"])
    verify_modules(files, review["verified_facts"]["modules"])
    return {
        "artifact_sha256": sha256_bytes(data), "cmd_record_count": len(EXPECTED_CMD_NAMES),
        "kconfig_case_count": 54, "mod_record_count": len(EXPECTED_MOD_NAMES),
        "module_count": len(EXPECTED_MODULE_RECORDS), "zip_entry_count": len(EXPECTED_ZIP_PATHS),
    }


def verify_artifact(path, review):
    data = v1_review.read_regular_file_once(path, "v2 artifact ZIP", expected_mode=0o644)
    return verify_artifact_bytes(data, review)


def build_parser():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path("."))
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--verify-artifact", type=Path)
    parser.add_argument("--check", action="store_true")
    return parser


def main(argv=None):
    arguments = build_parser().parse_args(argv)
    try:
        review = validate_review_object(load_review(discover_review(arguments.repo, arguments.manifest)))
        current = validate_repository(arguments.repo, review)
        verified = None
        if arguments.verify_artifact is not None:
            verified = verify_artifact(arguments.verify_artifact, review)
        output = {
            "artifact_verified": verified is not None, "claims": review["claims"],
            "current_head": current, "review_id": REVIEW_ID,
        }
        if verified is not None:
            output["verified"] = verified
        print(json.dumps(output, sort_keys=True, separators=(",", ":")))
        return 0
    except (
        BuildReviewV2Error, OSError, UnicodeError, ValueError,
        v1_review.BuildReviewError, zipfile.BadZipFile,
    ) as error:
        print("rk-007 v2 build review failed: {0}".format(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
