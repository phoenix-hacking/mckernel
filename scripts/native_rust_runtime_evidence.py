#!/usr/bin/env python3
"""Validate and capture credit-forbidden native Rust QEMU runtime evidence."""

from __future__ import print_function

import argparse
import base64
import contextlib
import copy
import datetime
import email.utils
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import stat
import struct
import subprocess
import sys
import types
from typing import Any

EXPECTED_REPOSITORY_SEMANTIC_AUTHORITY_IDENTITIES = {
    "kbuild_link_closure": {
        "git_blob_sha1": "7f0b49c36d183b3201ba29458f8096bc9d9beb30",
        "sha256": "827a19ffb5a86450dcf280de5163c561ebf09da4a25273fef8da97e0d267a293",
        "size": 53921,
    },
    "kconfig_policy": {
        "git_blob_sha1": "b6205a0ffa55fefc580f4742ef8b24b928b3fef4",
        "sha256": "9ad866896a98cfa223978748dec998d8ede51b0a042dfee8776fe77080fd4ba8",
        "size": 7506,
    },
    "kconfig_solver": {
        "git_blob_sha1": "095bd7b985f05c540696bb614df06a66843e64ad",
        "sha256": "fbb89bdb8766dcd446e8d75440c9e6bed1cf0a286107312510daef6626e80ab4",
        "size": 46669,
    },
}
ISOLATED_SELF_DIGEST = (
    "ISOLATED_SELF_DIGEST:42fbfad7d7f523c0722b933a54b1e8ca1c532e2a771a4e547f4c0c46b6cb8eba"
).split(":", 1)[1]

_SEMANTIC_AUTHORITY_FILENAMES = {
    "kbuild_link_closure": "native_rust_kbuild_link_closure.py",
    "kconfig_policy": "native_rust_kconfig_policy.py",
    "kconfig_solver": "native_rust_kconfig_solver.py",
}


def _bootstrap_file_identity(metadata: os.stat_result) -> tuple[Any, ...]:
    return (
        metadata.st_dev,
        metadata.st_ino,
        metadata.st_mode,
        metadata.st_nlink,
        metadata.st_uid,
        metadata.st_gid,
        metadata.st_size,
        getattr(metadata, "st_mtime_ns", int(metadata.st_mtime * 1000000000)),
        getattr(metadata, "st_ctime_ns", int(metadata.st_ctime * 1000000000)),
    )


def _bootstrap_git_blob_sha1(value: bytes) -> str:
    header = "blob {0}\0".format(len(value)).encode("ascii")
    return hashlib.sha1(header + value).hexdigest()


def _bootstrap_worker_authority_fds() -> dict[str, int] | None:
    marker = "--isolated-semantic-worker"
    if marker not in sys.argv[1:]:
        return None
    values = {}
    prefix = "--semantic-authority-fd="
    for argument in sys.argv[1:]:
        if not argument.startswith(prefix):
            continue
        assignment = argument[len(prefix) :]
        key, separator, raw_descriptor = assignment.partition(":")
        if (
            not separator
            or key not in _SEMANTIC_AUTHORITY_FILENAMES
            or key in values
            or any(character < "0" or character > "9" for character in raw_descriptor)
            or raw_descriptor.startswith("0")
        ):
            raise RuntimeError("isolated semantic authority descriptor differs")
        descriptor = int(raw_descriptor, 10)
        if descriptor < 3:
            raise RuntimeError("isolated semantic authority descriptor is unsafe")
        values[key] = descriptor
    if set(values) != set(_SEMANTIC_AUTHORITY_FILENAMES):
        raise RuntimeError("isolated semantic authority descriptor set differs")
    return values


def _read_bootstrap_authority_descriptor(
    descriptor: int, key: str
) -> bytes:
    expected = EXPECTED_REPOSITORY_SEMANTIC_AUTHORITY_IDENTITIES[key]
    before = os.fstat(descriptor)
    if (
        not stat.S_ISREG(before.st_mode)
        or stat.S_IMODE(before.st_mode) != 0o644
        or before.st_size != expected["size"]
    ):
        raise RuntimeError(
            "semantic authority descriptor shape differs: {0}".format(key)
        )
    chunks = []
    offset = 0
    while offset < expected["size"]:
        chunk = os.pread(descriptor, min(65536, expected["size"] - offset), offset)
        if not chunk:
            raise RuntimeError(
                "semantic authority descriptor ended early: {0}".format(key)
            )
        chunks.append(chunk)
        offset += len(chunk)
    if os.pread(descriptor, 1, offset):
        raise RuntimeError(
            "semantic authority descriptor exceeds exact size: {0}".format(key)
        )
    value = b"".join(chunks)
    actual = {
        "git_blob_sha1": _bootstrap_git_blob_sha1(value),
        "sha256": hashlib.sha256(value).hexdigest(),
        "size": len(value),
    }
    if (
        actual != expected
        or _bootstrap_file_identity(os.fstat(descriptor))
        != _bootstrap_file_identity(before)
    ):
        raise RuntimeError(
            "semantic authority descriptor identity differs: {0}".format(key)
        )
    return value


def _read_bootstrap_semantic_authorities() -> dict[str, bytes]:
    worker_fds = _bootstrap_worker_authority_fds()
    if worker_fds is not None:
        return {
            key: _read_bootstrap_authority_descriptor(worker_fds[key], key)
            for key in sorted(worker_fds)
        }
    script_directory = os.path.abspath(os.path.dirname(__file__))
    if not hasattr(os, "O_DIRECTORY") or not hasattr(os, "O_NOFOLLOW"):
        raise RuntimeError("semantic authority bootstrap requires no-follow support")
    directory_before = os.lstat(script_directory)
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    if hasattr(os, "O_CLOEXEC"):
        flags |= os.O_CLOEXEC
    directory_fd = os.open(script_directory, flags)
    try:
        directory_identity = _bootstrap_file_identity(os.fstat(directory_fd))
        if (
            not stat.S_ISDIR(directory_before.st_mode)
            or directory_identity != _bootstrap_file_identity(directory_before)
        ):
            raise RuntimeError("semantic authority directory changed while opening")
        result = {}
        for key in sorted(_SEMANTIC_AUTHORITY_FILENAMES):
            name = _SEMANTIC_AUTHORITY_FILENAMES[key]
            expected = EXPECTED_REPOSITORY_SEMANTIC_AUTHORITY_IDENTITIES[key]
            before = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
            if (
                not stat.S_ISREG(before.st_mode)
                or stat.S_IMODE(before.st_mode) != 0o644
                or before.st_size != expected["size"]
            ):
                raise RuntimeError(
                    "semantic authority file shape differs: {0}".format(name)
                )
            file_flags = os.O_RDONLY | os.O_NOFOLLOW
            if hasattr(os, "O_CLOEXEC"):
                file_flags |= os.O_CLOEXEC
            descriptor = os.open(name, file_flags, dir_fd=directory_fd)
            try:
                opened_identity = _bootstrap_file_identity(os.fstat(descriptor))
                if opened_identity != _bootstrap_file_identity(before):
                    raise RuntimeError(
                        "semantic authority changed while opening: {0}".format(name)
                    )
                chunks = []
                total = 0
                while True:
                    chunk = os.read(descriptor, 65536)
                    if not chunk:
                        break
                    total += len(chunk)
                    if total > expected["size"]:
                        raise RuntimeError(
                            "semantic authority exceeds exact size: {0}".format(name)
                        )
                    chunks.append(chunk)
                value = b"".join(chunks)
                actual = {
                    "git_blob_sha1": _bootstrap_git_blob_sha1(value),
                    "sha256": hashlib.sha256(value).hexdigest(),
                    "size": len(value),
                }
                if (
                    actual != expected
                    or _bootstrap_file_identity(os.fstat(descriptor))
                    != opened_identity
                ):
                    raise RuntimeError(
                        "semantic authority byte identity differs: {0}".format(name)
                    )
                result[key] = value
            finally:
                os.close(descriptor)
        if _bootstrap_file_identity(os.fstat(directory_fd)) != directory_identity:
            raise RuntimeError("semantic authority directory changed during bootstrap")
        return result
    finally:
        os.close(directory_fd)


def _load_verified_project_module(
    package: types.ModuleType,
    module_name: str,
    filename: str,
    source: bytes,
) -> types.ModuleType:
    qualified_name = "scripts.{0}".format(module_name)
    module = types.ModuleType(qualified_name)
    module.__file__ = os.path.join(os.path.abspath(os.path.dirname(__file__)), filename)
    module.__package__ = "scripts"
    module.__loader__ = None
    module.__spec__ = None
    sys.modules[qualified_name] = module
    setattr(package, module_name, module)
    try:
        code = compile(source, module.__file__, "exec")
        exec(code, module.__dict__)
    except BaseException:
        sys.modules.pop(qualified_name, None)
        if getattr(package, module_name, None) is module:
            delattr(package, module_name)
        raise
    return module


_BOOTSTRAP_AUTHORITY_BYTES = _read_bootstrap_semantic_authorities()
_BOOTSTRAP_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _BOOTSTRAP_REPO_ROOT not in sys.path:
    sys.path.insert(0, _BOOTSTRAP_REPO_ROOT)
if "scripts" in sys.modules:
    _scripts_package = sys.modules["scripts"]
else:
    _scripts_package = types.ModuleType("scripts")
    _scripts_package.__package__ = "scripts"
    _scripts_package.__path__ = [os.path.abspath(os.path.dirname(__file__))]
    sys.modules["scripts"] = _scripts_package

_kconfig_policy_module = _load_verified_project_module(
    _scripts_package,
    "native_rust_kconfig_policy",
    _SEMANTIC_AUTHORITY_FILENAMES["kconfig_policy"],
    _BOOTSTRAP_AUTHORITY_BYTES["kconfig_policy"],
)
_link_closure_module = _load_verified_project_module(
    _scripts_package,
    "native_rust_kbuild_link_closure",
    _SEMANTIC_AUTHORITY_FILENAMES["kbuild_link_closure"],
    _BOOTSTRAP_AUTHORITY_BYTES["kbuild_link_closure"],
)
_kconfig_solver_module = _load_verified_project_module(
    _scripts_package,
    "native_rust_kconfig_solver",
    _SEMANTIC_AUTHORITY_FILENAMES["kconfig_solver"],
    _BOOTSTRAP_AUTHORITY_BYTES["kconfig_solver"],
)
del _BOOTSTRAP_AUTHORITY_BYTES

EXPECTED_RAW_RECORD_NAMES = _link_closure_module.EXPECTED_RAW_RECORD_NAMES
LinkClosureError = _link_closure_module.LinkClosureError
check_kbuild_link_closure = _link_closure_module.check_kbuild_link_closure
KconfigPolicyError = _kconfig_policy_module.KconfigPolicyError
validate_native_rust_evidence_fragment = (
    _kconfig_policy_module.validate_native_rust_evidence_fragment
)
SOLVER_CAPTURE_STATUS = _kconfig_solver_module.CAPTURE_STATUS
SOLVER_EXPECTED_CLAIMS = _kconfig_solver_module.EXPECTED_CLAIMS
SOLVER_EXPECTED_COUNTS = _kconfig_solver_module.EXPECTED_COUNTS
SOLVER_EXPECTED_LIMITATIONS = _kconfig_solver_module.EXPECTED_LIMITATIONS
SolverError = _kconfig_solver_module.SolverError
validate_matrix_bytes = _kconfig_solver_module.validate_matrix_bytes


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONTRACT = Path("host-kernel/contracts/native-rust-runtime-evidence-v1.json")
CONTRACT_ID = "mckernel-native-rust-runtime-evidence-v1"
PROTOCOL = "MCKERNEL_NATIVE_RUST_RUNTIME_V1"
HEX40 = re.compile(r"^[0-9a-f]{40}$")
HEX64 = re.compile(r"^[0-9a-f]{64}$")
PROVIDER_LEASE_ATTACH_DIAGNOSTIC = (
    "ihk: provider_lease=attach status=live minor=0 callback_abi=1"
)
PROVIDER_LEASE_DETACH_DIAGNOSTIC_PATTERN = (
    r"ihk: provider_lease=detach status=vacant minor=0 "
    r"generation=([1-9][0-9]*) callback_abi=1"
)
PROVIDER_CALLBACK_ABI = 1
PROVIDER_CALLBACK_INIT_DIAGNOSTIC = (
    "ihk_smp_x86_64: provider_callback=init status=complete callback_abi=1"
)
PROVIDER_CALLBACK_EXIT_DIAGNOSTIC = (
    "ihk_smp_x86_64: provider_callback=exit status=complete callback_abi=1"
)
PROVIDER_REGISTRY_EMPTY_DIAGNOSTIC = "ihk: provider_registry=empty active=0"
PROVIDER_OPEN_ACQUIRE_DIAGNOSTIC = (
    "ihk: provider_open=acquire status=live minor=0"
)
PROVIDER_OPEN_RELEASE_DIAGNOSTIC = (
    "ihk: provider_open=release status=complete minor=0"
)
MCD0_SEQUENTIAL_OPEN_COUNT = 4
MCD0_OVERLAPPING_OPEN_COUNT = 8
MCD0_FIRST_CYCLE_OPEN_COUNT = 15
MCD0_RELOAD_OPEN_COUNT = 3
MCD0_PROVIDER_OPEN_COUNT_PER_TRACE = 18
MCD0_RELOAD_CYCLES = 1
PROVIDER_LEASE_FORBIDDEN_DIAGNOSTICS = (
    "ihk_smp_x86_64: provider_lease=detach-failed",
    "ihk: provider_callback=not-empty",
    "ihk: provider_registry=not-empty",
    "ihk: provider_registry=corrupt",
)
RAW_OPAQUE_TOKEN_FIELD = re.compile(
    r"(?:^|[^A-Za-z0-9_])(?:raw[_-]?|opaque[_-]?)?token\s*=\s*\S+",
    re.IGNORECASE,
)
RAW_PROVIDER_RECEIPT_FIELD = re.compile(
    r"(?:^|[^A-Za-z0-9_])(?:raw[_-]?)?receipt\s*=\s*\S+",
    re.IGNORECASE,
)
PROVIDER_ANCHOR_SYMBOL = "ihk_provider_lifecycle_v1"
PROVIDER_COMPAT_ATTACH_SYMBOL = "ihk_smp_provider_attach_v1"
PROVIDER_COMPAT_DETACH_SYMBOL = "ihk_smp_provider_detach_v1"
PROVIDER_ATTACH_SYMBOL = "ihk_smp_provider_attach_v2"
PROVIDER_DETACH_SYMBOL = "ihk_smp_provider_detach_v2"
PROVIDER_OPEN_SYMBOL = "ihk_smp_provider_open_v1"
PROVIDER_CLOSE_SYMBOL = "ihk_smp_provider_close_v1"
PROVIDER_EXPORT_NAMESPACE = "MCKERNEL_IHK_V1"
PROVIDER_DEFINED_SYMBOLS = (
    PROVIDER_ANCHOR_SYMBOL,
    PROVIDER_COMPAT_ATTACH_SYMBOL,
    PROVIDER_COMPAT_DETACH_SYMBOL,
    PROVIDER_ATTACH_SYMBOL,
    PROVIDER_DETACH_SYMBOL,
    PROVIDER_OPEN_SYMBOL,
    PROVIDER_CLOSE_SYMBOL,
)
PROVIDER_SMP_IMPORT_SYMBOLS = (
    PROVIDER_ANCHOR_SYMBOL,
    PROVIDER_ATTACH_SYMBOL,
    PROVIDER_DETACH_SYMBOL,
    PROVIDER_OPEN_SYMBOL,
    PROVIDER_CLOSE_SYMBOL,
)
# Retain the public helper name for the complete provider definition/export set.
PROVIDER_SYMBOLS = PROVIDER_DEFINED_SYMBOLS
PROVIDER_SYMBOL_PATTERN = re.compile(r"^ihk(?:_smp)?_provider_[A-Za-z0-9_]+$")
EXPECTED_FP0006_NATIVE_JOB_SHA256 = "edb35a6bdf7bd5495e9b5301e15cc2ca674626ea779c79b085f7e1baccb2cde3"
EXPECTED_KERNEL_LOCALVERSION = "-211.44.1.el10_2.mckernel1.x86_64"
EXPECTED_KERNEL_RELEASE = "6.12.0" + EXPECTED_KERNEL_LOCALVERSION
EXPECTED_SOURCE_DATE_EPOCH = 1786434034
EXPECTED_ROCKY_OS_RELEASE_SHA256 = (
    "2ac9f7b21412a20a1b30dba66be466a21abd87e4cddad00841374d7bfae89084"
)
SERIAL_FATAL_PATTERNS = (
    ("BUG", re.compile(r"^(?:\[\s*[0-9.]+\]\s+)?(?:kernel )?BUG(?:[: ])", re.IGNORECASE)),
    ("Oops", re.compile(r"^(?:\[\s*[0-9.]+\]\s+)?Oops(?:[: ])", re.IGNORECASE)),
    (
        "kernel panic",
        re.compile(
            r"^(?:\[\s*[0-9.]+\]\s+)?Kernel panic - not syncing:",
            re.IGNORECASE,
        ),
    ),
    ("call trace", re.compile(r"^(?:\[\s*[0-9.]+\]\s+)?Call Trace:$", re.IGNORECASE)),
    (
        "general protection fault",
        re.compile(
            r"^(?:\[\s*[0-9.]+\]\s+)?(?:general protection fault|GPF:)",
            re.IGNORECASE,
        ),
    ),
    (
        "NULL dereference",
        re.compile(
            r"^(?:\[\s*[0-9.]+\]\s+)?(?:BUG: )?(?:unable to handle kernel )?NULL pointer dereference",
            re.IGNORECASE,
        ),
    ),
    ("KASAN", re.compile(r"^(?:\[\s*[0-9.]+\]\s+)?KASAN:", re.IGNORECASE)),
    ("UBSAN", re.compile(r"^(?:\[\s*[0-9.]+\]\s+)?UBSAN:", re.IGNORECASE)),
    ("use-after-free", re.compile(r"\buse-after-free\b", re.IGNORECASE)),
    ("double-free", re.compile(r"\bdouble[ -]free\b", re.IGNORECASE)),
    (
        "refcount underflow",
        re.compile(r"\brefcount(?:_t)?:.*\bunderflow\b", re.IGNORECASE),
    ),
    (
        "lockup",
        re.compile(r"\b(?:soft lockup|hard LOCKUP)\b", re.IGNORECASE),
    ),
    (
        "hung task",
        re.compile(r"^.*INFO: task .* blocked for more than ", re.IGNORECASE),
    ),
    (
        "kmemleak",
        re.compile(
            r"(?:\bkmemleak:.*\bunreferenced object\b|^unreferenced object 0x)",
            re.IGNORECASE,
        ),
    ),
)
EXPECTED_REPRODUCIBLE_BUILD_ENVIRONMENT_NAMES = (
    "KBUILD_BUILD_HOST",
    "KBUILD_BUILD_TIMESTAMP",
    "KBUILD_BUILD_USER",
    "KBUILD_BUILD_VERSION",
    "SOURCE_DATE_EPOCH",
)
EXPECTED_REPRODUCIBLE_BUILD_ENVIRONMENT = {
    "KBUILD_BUILD_HOST": "rocky-10.2-x86_64",
    "KBUILD_BUILD_TIMESTAMP": "Tue, 11 Aug 2026 07:40:34 +0000",
    "KBUILD_BUILD_USER": "mckernel",
    "KBUILD_BUILD_VERSION": "1",
    "SOURCE_DATE_EPOCH": str(EXPECTED_SOURCE_DATE_EPOCH),
}
EXPECTED_REPRODUCIBLE_BUILD_ENVIRONMENT_SHA256 = hashlib.sha256(
    "".join(
        "{0}={1}\n".format(
            name, EXPECTED_REPRODUCIBLE_BUILD_ENVIRONMENT[name]
        )
        for name in EXPECTED_REPRODUCIBLE_BUILD_ENVIRONMENT_NAMES
    ).encode("ascii")
).hexdigest()
EXPECTED_REPRODUCIBLE_BUILD_ASSERTION_COMMANDS = (
    'test "$KBUILD_BUILD_HOST" = rocky-10.2-x86_64',
    'test "$KBUILD_BUILD_TIMESTAMP" = "Tue, 11 Aug 2026 07:40:34 +0000"',
    'test "$KBUILD_BUILD_USER" = mckernel',
    'test "$KBUILD_BUILD_VERSION" = 1',
    'test "$SOURCE_DATE_EPOCH" = 1786434034',
)
EXPECTED_KBUILD_ENV_COMMAND_PREFIX = [
    "/usr/bin/env",
    "-i",
    "BASH_ENV=",
    "ENV=",
    "GNUMAKEFLAGS=",
    "KBUILD_BUILD_HOST=rocky-10.2-x86_64",
    "KBUILD_BUILD_TIMESTAMP=Tue, 11 Aug 2026 07:40:34 +0000",
    "KBUILD_BUILD_USER=mckernel",
    "KBUILD_BUILD_VERSION=1",
    "LANG=C",
    "LC_ALL=C",
    "LD_LIBRARY_PATH=",
    "LD_PRELOAD=",
    "MAKEFILES=",
    "MAKEFLAGS=",
    "MAKEOVERRIDES=",
    "MFLAGS=",
    "PATH=/usr/bin:/bin",
    "SOURCE_DATE_EPOCH=1786434034",
    "TZ=UTC",
]
EXPECTED_KBUILD_MAKE_IDENTITY_ARGUMENTS = [
    "KBUILD_BUILD_HOST=rocky-10.2-x86_64",
    "KBUILD_BUILD_TIMESTAMP=Tue, 11 Aug 2026 07:40:34 +0000",
    "KBUILD_BUILD_USER=mckernel",
    "KBUILD_BUILD_VERSION=1",
    "SOURCE_DATE_EPOCH=1786434034",
]
BOUND_ROCKY_TOOL_ENVIRONMENT = {
    "LANG": "C",
    "LC_ALL": "C",
    "PATH": "/usr/sbin:/usr/bin:/sbin:/bin",
    "TZ": "UTC",
}
MODINFO_EXECUTABLE = "/usr/sbin/modinfo"
NM_EXECUTABLE = "/usr/bin/nm"
EXPECTED_MODINFO_SHA256 = (
    "7e91f52ed2cd5e2c4f82de4bb07bbaa7179cd5c053b7afcf2fd231056681ed55"
)
EXPECTED_PRECHECK_BUILD_MEMBERS = [
    "build-log.exit-code",
    "build.commands",
    "build.environment",
    "build.exit-code",
    "build.log",
    "build.phase",
    "built-module-artifacts.txt",
    "commit.sha",
    "executed-build-workflow.yml",
    "ihk-smp-x86_64.ko",
    "ihk-smp-x86_64.ko.modinfo",
    "ihk-smp-x86_64.ko.modinfo-section",
    "ihk-smp-x86_64.ko.nm",
    "ihk-smp-x86_64.ko.readelf",
    "ihk.ko",
    "ihk.ko.modinfo",
    "ihk.ko.modinfo-section",
    "ihk.ko.nm",
    "ihk.ko.readelf",
    "kconfig-solver-matrix.json",
    "mcctrl.ko",
    "mcctrl.ko.modinfo",
    "mcctrl.ko.modinfo-section",
    "mcctrl.ko.nm",
    "mcctrl.ko.readelf",
    "module-targets.txt",
    "workflow-provenance.json",
    "workflow-state",
]
MAX_BUILD_EVIDENCE_FILE_SIZE = 1 << 30
MAX_RUNTIME_EVIDENCE_FILE_SIZE = 512 << 20
MAX_RUNTIME_HELPER_FILE_SIZE = 1 << 20
MAX_RUNTIME_TEXT_FILE_SIZE = 64 << 20
MAX_TOOL_EXECUTABLE_FILE_SIZE = 128 << 20
MAX_ISOLATED_SEMANTIC_REQUEST_SIZE = 64 << 20
MAX_ISOLATED_SEMANTIC_RESULT_SIZE = 16 << 20
MAX_KBUILD_RAW_RECORD_SIZE = 2 << 20
MAX_KBUILD_STAGE_LOCK_SIZE = 1 << 20
RUNTIME_HELPER_ELF_SPEC = {
    "native-rust-runtime-mcd0-ioctl-i386": (1, 2, 3),
    "native-rust-runtime-mcd0-ioctl-i386.o": (1, 1, 3),
    "native-rust-runtime-mcd0-ioctl-x86_64": (2, 2, 62),
    "native-rust-runtime-mcd0-ioctl-x86_64.o": (2, 1, 62),
    "native-rust-runtime-poweroff.o": (2, 1, 62),
}
RUNTIME_PROBE_TEXT_TEMPLATE = {
    "native-rust-runtime-mcd0-ioctl-x86_64": (
        bytes.fromhex("b802000000488d3d"),
        bytes.fromhex(
            "be0200000031d20f054885c0783e4989c4b8100000004c89e7"
            "beefbeadde31d20f054883f8ea7513b8030000004c89e70f0548"
            "85c0781c31ffeb1db8030000004c89e70f05bf0b000000eb0cbf"
            "0a000000eb05bf0c000000b83c0000000f05"
        ),
    ),
    "native-rust-runtime-mcd0-ioctl-i386": (
        bytes.fromhex("b805000000bb"),
        bytes.fromhex(
            "b90200000031d2cd8085c0783889c6b83600000089f3b9efbead"
            "de31d2cd8083f8ea7511b80600000089f3cd8085c0781b31dbeb"
            "1cb80600000089f3cd80bb0b000000eb0cbb0a000000eb05bb0c"
            "000000b801000000cd80"
        ),
    ),
}
EXPECTED_RUNTIME_HELPER_SEMANTICS = {
    "allocated_sections": [".text", ".rodata"],
    "device_path_bytes": "/dev/mcd0\0",
    "entry_section": ".text",
    "executable_sections": [".text"],
    "executed_probe_files": [
        "native-rust-runtime-mcd0-ioctl-i386",
        "native-rust-runtime-mcd0-ioctl-x86_64",
    ],
    "instruction_policy": "exact-v1-with-only-device-address-derived-field",
    "object_files_shape_only": True,
    "poweroff_executable_replay": False,
    "program_header_policy": "three-exact-loads-plus-nonexecuting-gnu-stack",
}
CAPTURE_RUNTIME_INPUT_BASENAMES = {
    "serial_log": "serial.log",
    "qemu_log": "qemu.log",
    "qemu_command": "qemu-command.txt",
    "qemu_version": "qemu-version.txt",
    "qemu_exit_code": "qemu.exit-code",
    "environment_log": "environment.txt",
    "initramfs": "initramfs.cpio.gz",
    "initramfs_sha256": "initramfs.sha256",
    "workflow_provenance": "runtime-workflow-provenance.json",
    "executed_caller_workflow": "executed-caller-workflow.yml",
    "executed_runtime_workflow": "executed-runtime-workflow.yml",
}
EXPECTED_EXACT_BUILD_PREPARATION_SHA256 = (
    "254b0a4e4d9afa2c9e49426cd5dce48193d20b55b4a650f4649d05563dd57c80"
)
EXPECTED_EXACT_BUILD_PREFIX_SHA256 = (
    "444b53ca8ec050184e1d1fe478afc58e6e71e33c658e79a094232118ee5ced31"
)
EXPECTED_EXACT_BUILD_STEP_SHA256 = {
    "Refuse the wrong runtime and install exact build tools": "acabf171e87378f911362a812477945a4644fc3e04b4e107e57fff729763b420",
    "Check out the exact candidate without credentials": "4ce648da06a9ff165af51ca0e766fdaedc88353f72508499af8b27d93a4b83bc",
    "Verify source-only contracts without claiming readiness": "480014d26bc2759e11a6609cf5b9b58f3a2d00d603c135193f9ae932d907fecd",
    "Acquire, patch, and credit-forbidden-stage the exact source": "421ce7c6995f804e64121a048ac5ea524d3df23d20318622c6c75c983bf7f000",
    "Resolve the evidence-only module configuration twice": "e15939bc014dd603fed142c3f5226529aadb7eaa37cd64b3dbf3998e11dd4943",
    "Compile the exact kernel and native Rust modules": "17076a9e00d90489b9429cf31b9f6bb4f6c55a28474aa47a3234cb5cae61a82a",
    "Validate built metadata and capture immutable diagnostics": "3af1b3d4105d41a359efbfaa3c0673865e14404c200b451b02a6612a40bdc285",
    "Upload compiler evidence or first-failure diagnostics": "f5c304d408baad23b482154ef91a5738f79a48c1a34b898be1c5e2c55499a3d9",
}
EXPECTED_RK006_CAPTURE_STEP_SHA256 = {
    "Initialize non-durable capture and install exact tools": "a89bfbe988001115dbbe5c71135fa75f9ac0a1fe453c98c423e28795f16071ca",
    "Check out the exact capture candidate without credentials": "c7ec10a3531204c964e98632341afa709ad11f1dc7ce872df916beb03c64ab30",
    "Verify the frozen non-crediting RK-006 capture contract": "3f7555cb83bb7ec65665feabc70e994d0d5a6e3cd14a151374668449ebd80b25",
    "Reacquire and capture the full external 26-patch source replay": "3eb78a45a68861f9a8fea36b4089bd454bb1e273db3f20aae126fdd76d756a4e",
    "Download the same-run exact-build evidence": "4c98e4feff7b7f391d16b8bafff6c3531a7766762c5f66ec5a703e233955316a",
    "Finalize the non-crediting build binding": "3fe1f786cd5e4020a7659a761bd431bf6ed185a15df19b44b5930c02aad6f750",
    "Upload RK-006 capture or first-failure diagnostics": "7ed2ac56ab7dda85cb3ac7b81dd569745fb82103e38e3abc38c527bc0736d7fe",
}
EXPECTED_RUNTIME_INIT_SHA256 = (
    "8abb51802ca0ed3e222f5f2799c3c589f38d35545f4b65693e56fbff44908865"
)
EXPECTED_REPOSITORY_WORKFLOW_IDENTITIES = {
    "build_workflow": {
        "git_blob_sha1": "510644de44b322e2938e05da21669cb35ef343d5",
        "sha256": "c24b1e107a75da00afcb4ebf1945e249c611af8459fdeb90635a561199a33250",
        "size": 90656,
    },
    "runtime_pr_workflow": {
        "git_blob_sha1": "64bb717852d36fc1021e2b61e83aca6415b184d5",
        "sha256": "628e901df2ef4d26978e0280a8ca300d9d58adc57f6c6bde883940706adf2265",
        "size": 754,
    },
    "runtime_workflow": {
        "git_blob_sha1": "3517e4fc182d2e47d713f11806c2b201745fe420",
        "sha256": "bb6ac70461a8bb743de63e38c68240615b60251c119a0c2fc14b6e65f49958e4",
        "size": 35959,
    },
}
EXPECTED_REPOSITORY_HELPER_IDENTITIES = {
    "mcd0_ioctl_i386": {
        "git_blob_sha1": "852f6b986cc325774dce93b550ebd29446ace5e9",
        "sha256": "128b63dba75cdbfc367a69054a95f079818e7c0e4a42071010bad1125e823ad7",
        "size": 936,
    },
    "mcd0_ioctl_x86_64": {
        "git_blob_sha1": "962972031ee0101defcef2d9bc9d01c5bc585b45",
        "sha256": "82f4599faaf083eece40840be62d8da5ceb314123449fdec71e57998e36fdf18",
        "size": 927,
    },
}
BUILD_KERNEL_TARGETS = ["bzImage"]
BUILD_MODULE_TARGETS = [
    "drivers/misc/mckernel/ihk.ko",
    "drivers/misc/mckernel/ihk-smp-x86_64.ko",
    "drivers/misc/mckernel/mcctrl.ko",
]
EXPECTED_RUNTIME_REQUIRED_CONFIG = {
    "disabled": ["CONFIG_MODULE_SIG_FORCE"],
    "enabled": [
        "CONFIG_BINFMT_ELF",
        "CONFIG_BLK_DEV_INITRD",
        "CONFIG_COMPAT",
        "CONFIG_DEVTMPFS",
        "CONFIG_IA32_EMULATION",
        "CONFIG_MISC_DEVICES",
        "CONFIG_MODULES",
        "CONFIG_MODULE_UNLOAD",
        "CONFIG_PRINTK",
        "CONFIG_PROC_FS",
        "CONFIG_RD_GZIP",
        "CONFIG_SERIAL_8250",
        "CONFIG_SERIAL_8250_CONSOLE",
        "CONFIG_SYSFS",
    ],
    "modules": {
        "CONFIG_MCKERNEL_IHK_RUST": "m",
        "CONFIG_MCKERNEL_IHK_SMP_X86_64_RUST": "m",
        "CONFIG_MCKERNEL_MCCTRL_RUST": "m",
    },
}
EXPECTED_LINK_CLAIMS = {
    "complete_external_build_input_closure": False,
    "credit_eligible": False,
    "load_proven": False,
    "production_ready": False,
    "runtime_proven": False,
}


class EvidenceError(RuntimeError):
    """Raised when runtime evidence or its immutable inputs diverge."""


def _object_without_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise EvidenceError("duplicate JSON key: {0}".format(key))
        result[key] = value
    return result


def _load_json(path: Path) -> dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as stream:
            value = json.load(stream, object_pairs_hook=_object_without_duplicates)
    except (OSError, UnicodeError, ValueError) as error:
        raise EvidenceError("cannot load {0}: {1}".format(path, error)) from error
    if not isinstance(value, dict):
        raise EvidenceError("{0} must contain one JSON object".format(path))
    return value


def _canonical_bytes(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode(
        "utf-8"
    )


def _exact_typed_equal(actual: Any, expected: Any) -> bool:
    if type(actual) is not type(expected):
        return False
    if isinstance(expected, dict):
        return (
            set(actual) == set(expected)
            and all(_exact_typed_equal(actual[key], expected[key]) for key in expected)
        )
    if isinstance(expected, list):
        return len(actual) == len(expected) and all(
            _exact_typed_equal(left, right)
            for left, right in zip(actual, expected)
        )
    return actual == expected


def _reproducible_build_environment_text() -> str:
    return "".join(
        "{0}={1}\n".format(name, EXPECTED_REPRODUCIBLE_BUILD_ENVIRONMENT[name])
        for name in EXPECTED_REPRODUCIBLE_BUILD_ENVIRONMENT_NAMES
    )


def _reproducible_build_record_commands(directory_variable: str) -> tuple[str, ...]:
    return (
        "printf '%s\\n' \\",
        '"KBUILD_BUILD_HOST=$KBUILD_BUILD_HOST" \\',
        '"KBUILD_BUILD_TIMESTAMP=$KBUILD_BUILD_TIMESTAMP" \\',
        '"KBUILD_BUILD_USER=$KBUILD_BUILD_USER" \\',
        '"KBUILD_BUILD_VERSION=$KBUILD_BUILD_VERSION" \\',
        '"SOURCE_DATE_EPOCH=$SOURCE_DATE_EPOCH" \\',
        '> "{0}/build.environment"'.format(directory_variable),
    )


def _pretty(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True) + "\n"


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _git_blob_sha1(value: bytes) -> str:
    header = "blob {0}\0".format(len(value)).encode("ascii")
    return hashlib.sha1(header + value).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError as error:
        raise EvidenceError("cannot hash {0}: {1}".format(path, error)) from error
    return digest.hexdigest()


def _active_shell_lines(text: str) -> tuple[str, ...]:
    """Return nonblank shell source with unquoted comments removed."""
    active: list[str] = []
    for raw_line in text.splitlines():
        quote = ""
        escaped = False
        comment_at: int | None = None
        for index, character in enumerate(raw_line):
            if escaped:
                escaped = False
                continue
            if character == "\\" and quote != "'":
                escaped = True
                continue
            if quote:
                if character == quote:
                    quote = ""
                continue
            if character in ("'", '"'):
                quote = character
            elif character == "#":
                comment_at = index
                break
        line = raw_line if comment_at is None else raw_line[:comment_at]
        line = line.strip()
        if line:
            active.append(line)
    return tuple(active)


def _require_keys(value: dict[str, Any], expected: set[str], label: str) -> None:
    if not isinstance(value, dict) or set(value) != expected:
        actual = set(value) if isinstance(value, dict) else set()
        raise EvidenceError(
            "{0} keys differ: missing={1}, extra={2}".format(
                label, sorted(expected - actual), sorted(actual - expected)
            )
        )


def _repo_file(repo: Path, relative: str, label: str) -> Path:
    if not isinstance(relative, str) or not relative or "\\" in relative:
        raise EvidenceError("{0} must be a non-empty POSIX path".format(label))
    item = Path(relative)
    if item.is_absolute() or ".." in item.parts or item.as_posix() != relative:
        raise EvidenceError("{0} escapes the repository".format(label))
    candidate = repo / item
    try:
        candidate.lstat()
    except OSError as error:
        raise EvidenceError("{0} is unavailable: {1}".format(label, error)) from error
    if candidate.is_symlink() or not candidate.is_file():
        raise EvidenceError("{0} must be a regular non-symlink file".format(label))
    try:
        candidate.resolve().relative_to(repo.resolve())
    except ValueError as error:
        raise EvidenceError("{0} resolves outside the repository".format(label)) from error
    return candidate


def _read_text(path: Path, label: str) -> str:
    try:
        with path.open("r", encoding="utf-8", newline="") as stream:
            return stream.read()
    except (OSError, UnicodeError) as error:
        raise EvidenceError("cannot read {0}: {1}".format(label, error)) from error


def _split_named_steps(text: str, expected_names: list[str], label: str) -> dict[str, str]:
    observed = re.findall(r"(?m)^      - name: (.+)$", text)
    if observed != expected_names:
        raise EvidenceError("{0} steps are missing, extra, or reordered".format(label))
    headers = ["      - name: {0}\n".format(name) for name in expected_names]
    positions = [text.index(header) for header in headers]
    result = {}
    for index, (name, position) in enumerate(zip(expected_names, positions)):
        start = position + len(headers[index])
        end = positions[index + 1] if index + 1 < len(positions) else len(text)
        result[name] = text[start:end]
    return result


def _validate_rk006_capture_job_v2(job_text: str) -> None:
    preamble = (
        "  rk006-full-source-build-capture:\n"
        "    name: Bind RK-006 full-source replay to the exact build (credit forbidden)\n"
        "    needs: exact-build\n"
        "    runs-on: ubuntu-24.04\n"
        "    timeout-minutes: 150\n"
        "    container:\n"
        "      image: rockylinux/rockylinux:10.2@sha256:"
        "e372170ca8630f0f03e9b70fdd0bf4a3ce3426b0de7cdba615f06337389de176\n"
        "    defaults:\n"
        "      run:\n"
        "        shell: /usr/bin/bash --noprofile --norc -p -e -o pipefail {0}\n"
        "\n"
        "    steps:\n"
    )
    if not job_text.startswith(preamble):
        raise EvidenceError("RK-006 capture job scope differs")
    expected_names = list(EXPECTED_RK006_CAPTURE_STEP_SHA256)
    steps = _split_named_steps(job_text[len(preamble) :], expected_names, "RK-006 capture")
    for name in expected_names:
        if _sha256_bytes(steps[name].encode("utf-8")) != (
            EXPECTED_RK006_CAPTURE_STEP_SHA256[name]
        ):
            raise EvidenceError("RK-006 capture step scope differs: {0}".format(name))
    if job_text.count("        if: ${{ always() }}\n") != 1:
        raise EvidenceError("RK-006 capture upload condition differs")
    active = "\n".join(_active_shell_lines(job_text))
    for required, expected_count in (
        ("unset GITHUB_ENV GITHUB_PATH", 3),
        (
            "/usr/bin/python3 -E -s scripts/rocky_kernel_rk006_full_source_build_capture.py",
            4,
        ),
        (
            "/usr/bin/env -i LANG=C LC_ALL=C PATH=/usr/bin:/bin PYTHONHASHSEED=0 TZ=UTC",
            6,
        ),
    ):
        if active.count(required) != expected_count:
            raise EvidenceError("RK-006 capture clean execution boundary differs")
    if any(
        fragment in active
        for fragment in ("|| true", "set +e", "trap ", "return ", "exit 0")
    ):
        raise EvidenceError("RK-006 capture may tolerate or bypass evidence failure")


def _validate_rk006_capture_job(job_text: str) -> None:
    return _validate_rk006_capture_job_v2(job_text)
    preamble = (
        "  rk006-full-source-build-capture:\n"
        "    name: Bind RK-006 full-source replay to the exact build (credit forbidden)\n"
        "    needs: exact-build\n"
        "    runs-on: ubuntu-24.04\n"
        "    timeout-minutes: 150\n"
        "    container:\n"
        "      image: rockylinux/rockylinux:10.2@sha256:"
        "e372170ca8630f0f03e9b70fdd0bf4a3ce3426b0de7cdba615f06337389de176\n"
        "    defaults:\n"
        "      run:\n"
        "        shell: /usr/bin/bash --noprofile --norc -p -e -o pipefail {0}\n"
        "\n"
        "    steps:\n"
    )
    if not job_text.startswith(preamble):
        raise EvidenceError("RK-006 capture job scope differs")
    if re.search(
        r'(?m)^    (?:if|"if"|continue-on-error|strategy):', job_text
    ) or any(
        fragment in job_text
        for fragment in (
            "        continue-on-error:",
            "          set +e",
            "|| true",
            "if false",
            "if true",
        )
    ):
        raise EvidenceError("RK-006 capture job may skip or tolerate evidence failure")
    step_names = re.findall(r"(?m)^      - name: (.+)$", job_text)
    expected_steps = [
        "Initialize non-durable capture and install exact tools",
        "Check out the exact capture candidate without credentials",
        "Verify the frozen non-crediting RK-006 capture contract",
        "Reacquire and capture the full external 26-patch source replay",
        "Download the same-run exact-build evidence",
        "Finalize the non-crediting build binding",
        "Upload RK-006 capture or first-failure diagnostics",
    ]
    if step_names != expected_steps:
        raise EvidenceError("RK-006 capture steps are missing, extra, or reordered")
    headers = ["      - name: {0}\n".format(name) for name in expected_steps]
    positions = [job_text.index(header) for header in headers]
    steps: dict[str, str] = {}
    for index, (name, position) in enumerate(zip(expected_steps, positions)):
        start = position + len(headers[index])
        end = positions[index + 1] if index + 1 < len(positions) else len(job_text)
        steps[name] = job_text[start:end]
    expected_step_hashes = {
        expected_steps[0]: "a89bfbe988001115dbbe5c71135fa75f9ac0a1fe453c98c423e28795f16071ca",
        expected_steps[1]: "c7ec10a3531204c964e98632341afa709ad11f1dc7ce872df916beb03c64ab30",
        expected_steps[2]: "bfc1c0d263506674ede307ccd4b9e7f5a3a6b4e551a065f10aadde2a3bf63eb5",
        expected_steps[3]: "8ee6f72f6d7bd9fba30ebc97237b534515d0d6c7fad7328101909d1ed205ae9e",
        expected_steps[4]: "4c98e4feff7b7f391d16b8bafff6c3531a7766762c5f66ec5a703e233955316a",
        expected_steps[5]: "ab8382344b6b288411e8569d6ff60e63432a07a7f3675ff95c0cbf5c92f8afb0",
        expected_steps[6]: "7ed2ac56ab7dda85cb3ac7b81dd569745fb82103e38e3abc38c527bc0736d7fe",
    }
    for name in expected_steps:
        if _sha256_bytes(steps[name].encode("utf-8")) != expected_step_hashes[name]:
            raise EvidenceError("RK-006 capture step scope differs: {0}".format(name))

    expected_checkout = (
        "        uses: actions/checkout@11d5960a326750d5838078e36cf38b85af677262 # v4\n"
        "        with:\n"
        "          ref: ${{ env.EXPECTED_HEAD_SHA }}\n"
        "          fetch-depth: 1\n"
        "          persist-credentials: false\n"
        "          submodules: false\n"
        "\n"
    )
    if steps[expected_steps[1]] != expected_checkout:
        raise EvidenceError("RK-006 capture checkout scope differs")
    expected_download = (
        "        uses: actions/download-artifact@d3f86a106a0bac45b974a628896c90dbdf5c8093 # v4.3.0\n"
        "        with:\n"
        "          name: native-rust-exact-build-${{ github.run_id }}-${{ github.run_attempt }}\n"
        "          path: ${{ runner.temp }}/rk006-build-evidence\n"
        "\n"
    )
    if steps[expected_steps[4]] != expected_download:
        raise EvidenceError("RK-006 capture download scope differs")
    expected_upload = (
        "        if: ${{ always() }}\n"
        "        uses: actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02 # v4.6.2\n"
        "        with:\n"
        "          name: rk006-full-source-build-capture-${{ github.run_id }}-${{ github.run_attempt }}\n"
        "          path: ${{ runner.temp }}/rk006-full-source-build-capture/\n"
        "          if-no-files-found: error\n"
        "          retention-days: 30\n"
        "          compression-level: 0\n"
        "          include-hidden-files: true\n"
    )
    if steps[expected_steps[6]] != expected_upload:
        raise EvidenceError("RK-006 capture upload scope differs")
    if job_text.count("        if: ${{ always() }}\n") != 1:
        raise EvidenceError("RK-006 capture upload condition differs")

    scoped_requirements = {
        expected_steps[0]: [
            "        run: |\n",
            "          set -euo pipefail\n",
            '          capture_dir="$RUNNER_TEMP/rk006-full-source-build-capture"\n',
            '          mkdir -p "$capture_dir"\n',
            "          printf '%s\\n' bootstrap-started > \"$capture_dir/workflow-state\"\n",
            "          test \"$(uname -m)\" = x86_64\n",
            "          test \"$ID\" = rocky\n",
            "          test \"$VERSION_ID\" = 10.2\n",
            "          dnf config-manager --set-enabled crb\n",
            "            hostname kernel-rpm-macros kmod lld llvm llvm-devel make ncurses-devel \\\n",
            "            openssl openssl-devel patch perl python3 python3-devel python3-pyyaml \\\n",
            "            redhat-rpm-config rpm-build rust rust-src rustfmt tar which xz zstd\n",
        ],
        expected_steps[2]: [
            "        run: |\n",
            "          set -euo pipefail\n",
            '          [[ "$EXPECTED_HEAD_SHA" =~ ^[0-9a-f]{40}$ ]]\n',
            "          python3 scripts/rocky_kernel_rk006_full_source_build_capture.py \\\n",
            '            check-contract --repo "$GITHUB_WORKSPACE"\n',
            "            scripts.tests.test_rocky_kernel_rk006_patch_authority \\\n",
            "            scripts.tests.test_rocky_kernel_rk006_full_source_build_capture\n",
        ],
        expected_steps[3]: [
            "        env:\n",
            "          CACHE_ROOT: ${{ runner.temp }}/rk006-source-cache\n",
            "          SOURCE_ASSETS: ${{ runner.temp }}/rk006-source-assets\n",
            "          SOURCE_PARENT: ${{ runner.temp }}/rk006-source\n",
            "        run: |\n",
            "          set -euo pipefail\n",
            '            --repo "$GITHUB_WORKSPACE" --cache-root "$CACHE_ROOT" --acquire\n',
            "          archive=\"$SOURCE_ASSETS/linux-6.12.0-211.44.1.el10_2.tar.xz\"\n",
            "          vendor_patch=\"$SOURCE_ASSETS/1000-debrand-some-messages.patch\"\n",
            "          python3 scripts/rocky_kernel_rk006_full_source_build_capture.py capture \\\n",
            '            --source-archive "$archive" \\\n',
            '            --source-rpm "$srpm" \\\n',
            '            --vendor-patch "$vendor_patch" \\\n',
            '            --output-dir "$RUNNER_TEMP/rk006-full-source-build-capture" \\\n',
            '            --github-head-sha "$EXPECTED_HEAD_SHA" \\\n',
            '            --container-image "$ROCKY_IMAGE"\n',
        ],
        expected_steps[5]: [
            "        run: |\n",
            "          set -euo pipefail\n",
            "            finalize-build \\\n",
            '            --build-evidence-dir "$RUNNER_TEMP/rk006-build-evidence"\n',
            "            verify-capture \\\n",
        ],
    }
    for step_name, fragments in scoped_requirements.items():
        body = steps[step_name]
        active = "".join(
            line for line in body.splitlines(True)
            if not line.lstrip().startswith("#")
        )
        fragment_positions = []
        for fragment in fragments:
            if active.count(fragment) != 1:
                raise EvidenceError(
                    "RK-006 capture step lacks one active boundary: {0}".format(step_name)
                )
            fragment_positions.append(active.index(fragment))
        if fragment_positions != sorted(fragment_positions):
            raise EvidenceError("RK-006 capture step boundaries are reordered: {0}".format(step_name))
    uses = re.findall(r"(?m)^\s*uses:\s*(\S+)", job_text)
    if len(uses) != 3 or any(
        re.fullmatch(r"[^@]+@[0-9a-f]{40}", value) is None for value in uses
    ):
        raise EvidenceError("RK-006 capture actions are not exactly digest pinned")


def _validate_fp0006_native_capture_job(job_text: str) -> None:
    if (
        hashlib.sha256(job_text.encode("utf-8")).hexdigest()
        != EXPECTED_FP0006_NATIVE_JOB_SHA256
    ):
        raise EvidenceError("FP-0006 native capture job exact active scope differs")
    expected_preamble = (
        "  fp0006-native-rust-capture:\n"
        "    name: Capture FP-0006 native Rust fixture (credit forbidden)\n"
        "    needs: exact-build\n"
        "    if: >-\n"
        "      ${{ github.event_name != 'pull_request' ||\n"
        "          github.event.pull_request.head.repo.full_name == github.repository }}\n"
        "    runs-on: ubuntu-24.04\n"
        "    timeout-minutes: 30\n"
        "    container:\n"
        "      image: rockylinux/rockylinux:10.2@sha256:"
        "e372170ca8630f0f03e9b70fdd0bf4a3ce3426b0de7cdba615f06337389de176\n"
        "    defaults:\n"
        "      run:\n"
        "        shell: bash\n"
        "\n"
        "    steps:\n"
    )
    if not job_text.startswith(
        expected_preamble
        + "      - name: Install pinned Rust and identify the observed FP-0006 linker\n"
    ):
        raise EvidenceError("FP-0006 native capture job scope differs")
    trusted = (
        "    if: >-\n"
        "      ${{ github.event_name != 'pull_request' ||\n"
        "          github.event.pull_request.head.repo.full_name == github.repository }}\n"
    )
    if job_text.count(trusted) != 1:
        raise EvidenceError("FP-0006 native capture job trust boundary differs")
    for key, expected in (
        ("if", 1), ("runs-on", 1), ("steps", 1),
        ("continue-on-error", 0), ("strategy", 0),
    ):
        pattern = r"(?m)^    (?:{0}|\"{0}\"|'{0}')\s*:".format(
            re.escape(key)
        )
        if len(re.findall(pattern, job_text)) != expected:
            raise EvidenceError("FP-0006 native capture job keys differ")
    headers = re.findall(r"(?m)^      - name: ([^\n]+)\n", job_text)
    expected_headers = [
        "Install pinned Rust and identify the observed FP-0006 linker",
        "Check out the exact FP-0006 candidate without credentials",
        "Produce and review the FP-0006 native envelope",
        "Upload FP-0006 native envelope",
        "Upload FP-0006 first-failure diagnostics",
    ]
    if headers != expected_headers:
        raise EvidenceError("FP-0006 native capture steps are missing, extra, or reordered")
    starts = [job_text.index("      - name: " + name + "\n") for name in headers]
    steps = {}
    for index, name in enumerate(headers):
        start = starts[index] + len("      - name: " + name + "\n")
        end = starts[index + 1] if index + 1 < len(starts) else len(job_text)
        steps[name] = job_text[start:end]
    for name in headers[:3]:
        if re.search(
            r"(?m)^        (?:if|\"if\"|'if'|continue-on-error|"
            r"\"continue-on-error\"|'continue-on-error')\s*:",
            steps[name],
        ):
            raise EvidenceError("FP-0006 native producer step can skip or tolerate failure")
    checkout = (
        "        uses: actions/checkout@11d5960a326750d5838078e36cf38b85af677262 # v4\n"
        "        with:\n"
        "          ref: ${{ env.EXPECTED_HEAD_SHA }}\n"
        "          fetch-depth: 1\n"
        "          submodules: recursive\n"
        "          persist-credentials: false\n"
        "\n"
    )
    if steps[headers[1]] != checkout:
        raise EvidenceError("FP-0006 native checkout scope differs")
    bootstrap = (
        "        run: |\n"
        "          set -euo pipefail\n"
        "          fp0006_diagnostics=\"$RUNNER_TEMP/fp0006-native-rust-first-failure\"\n"
        "          mkdir -m 700 \"$fp0006_diagnostics\"\n"
        "          printf '%s\\n' bootstrap-started capture-envelope-required-missing credit-forbidden \\\n"
        "            > \"$fp0006_diagnostics/workflow-state\"\n"
        "          test \"$(uname -m)\" = x86_64\n"
        "          . /etc/os-release\n"
        "          test \"$ID\" = rocky\n"
        "          test \"$VERSION_ID\" = 10.2\n"
        "          dnf -y --allowerasing --setopt=install_weak_deps=False install \\\n"
        "            coreutils\n"
        "          dnf -y --setopt=install_weak_deps=False install \\\n"
        "            gcc git-core python3 rust-1.92.0-1.el10\n"
        "          ! /usr/bin/rpm -q coreutils-single\n"
        "          test \"$(/usr/bin/rpm -qf --qf '%{NAME}\\n' /usr/bin/timeout)\" = coreutils\n"
        "          test \"$(command -v rustc)\" = /usr/bin/rustc\n"
        "          test \"$(command -v gcc)\" = /usr/bin/gcc\n"
        "          test \"$(command -v timeout)\" = /usr/bin/timeout\n"
        "          test ! -L /usr/bin/rustc\n"
        "          test ! -L /usr/bin/gcc\n"
        "          test ! -L /usr/bin/timeout\n"
        "          test \"$(/usr/bin/rpm -qf --qf '%{NAME}\\n' /usr/bin/rustc)\" = rust\n"
        "          test \"$(/usr/bin/rpm -qf --qf '%{NAME}\\n' /usr/bin/gcc)\" = gcc\n"
        "          test \"$(/usr/bin/rpm -q --qf '%{NAME}-%{EPOCHNUM}:%{VERSION}-%{RELEASE}.%{ARCH}\\n' rust)\" = rust-0:1.92.0-1.el10.x86_64\n"
        "          test \"$(/usr/bin/rustc --version)\" = 'rustc 1.92.0 (ded5c06cf 2025-12-08) (Red Hat 1.92.0-1.el10)'\n"
        "          /usr/bin/rustc -Vv\n"
        "          /usr/bin/gcc --version\n"
        "          dnf clean all\n"
        "          printf '%s\\n' bootstrap-complete capture-envelope-required-missing credit-forbidden \\\n"
        "            > \"$fp0006_diagnostics/workflow-state\"\n"
        "\n"
    )
    if steps[headers[0]] != bootstrap:
        raise EvidenceError("FP-0006 native bootstrap scope differs")
    upload = (
        "        uses: actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02 # v4.6.2\n"
        "        with:\n"
        "          name: fp0006-native-rust-source-fixture-${{ github.run_id }}-${{ github.run_attempt }}\n"
        "          path: ${{ runner.temp }}/fp0006-native-rust-capture/fp0006-runtime-capture-v1.tar\n"
        "          if-no-files-found: error\n"
        "          retention-days: 30\n"
        "          compression-level: 0\n"
        "\n"
    )
    if steps[headers[3]] != upload:
        raise EvidenceError("FP-0006 native upload scope differs")
    failure_upload = (
        "        if: ${{ failure() }}\n"
        "        uses: actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02 # v4.6.2\n"
        "        with:\n"
        "          name: fp0006-native-rust-first-failure-${{ github.run_id }}-${{ github.run_attempt }}\n"
        "          path: ${{ runner.temp }}/fp0006-native-rust-first-failure/workflow-state\n"
        "          if-no-files-found: error\n"
        "          retention-days: 30\n"
        "          compression-level: 0\n"
    )
    if steps[headers[4]] != failure_upload:
        raise EvidenceError("FP-0006 native first-failure upload scope differs")
    if "actions/download-artifact@" in job_text:
        raise EvidenceError("FP-0006 native capture attempts an artifact download")
    active = "\n".join(
        line for line in job_text.splitlines()
        if not line.lstrip().startswith("#")
    )
    required = [
        'dnf -y --allowerasing --setopt=install_weak_deps=False install \\',
        '            coreutils',
        'dnf -y --setopt=install_weak_deps=False install \\',
        'gcc git-core python3 rust-1.92.0-1.el10',
        '! /usr/bin/rpm -q coreutils-single',
        'test "$(/usr/bin/rpm -qf --qf \'%{NAME}\\n\' /usr/bin/timeout)" = coreutils',
        'test "$(command -v rustc)" = /usr/bin/rustc',
        'test "$(command -v gcc)" = /usr/bin/gcc',
        'test "$(command -v timeout)" = /usr/bin/timeout',
        'test "$(/usr/bin/rpm -q --qf \'%{NAME}-%{EPOCHNUM}:%{VERSION}-%{RELEASE}.%{ARCH}\\n\' rust)" = rust-0:1.92.0-1.el10.x86_64',
        "test \"$(/usr/bin/rustc --version)\" = 'rustc 1.92.0 (ded5c06cf 2025-12-08) (Red Hat 1.92.0-1.el10)'",
        'test "$(git -c safe.directory="$GITHUB_WORKSPACE" rev-parse HEAD)" = "$EXPECTED_HEAD_SHA"',
        "/usr/bin/rustc --edition=2021 -D warnings -C linker=/usr/bin/gcc -C strip=symbols \\",
        'producer_bytes="$(/usr/bin/wc -c < "$producer")"',
        'if test "$producer_bytes" -le 0 || test "$producer_bytes" -gt 8388608; then',
        "printf 'FP-0006 native producer binary size observed=%s maximum=8388608\\n' \\",
        "/usr/bin/timeout --signal=TERM --kill-after=5s 30s \\",
        '"$producer" "$stage" > "$producer_output" 2>&1',
        "python3 scripts/fp0006_runtime_capture_integration.py finalize-lane \\",
    ]
    positions = []
    for fragment in required:
        if active.count(fragment) != 1:
            raise EvidenceError("FP-0006 native capture command boundary differs")
        positions.append(active.index(fragment))
    if positions != sorted(positions):
        raise EvidenceError("FP-0006 native capture commands are reordered")
    capture_lines = tuple(
        line.strip() for line in steps[headers[2]].splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    )
    timeout_if = (
        "if /usr/bin/env -i HOME=/nonexistent LANG=C LC_ALL=C PATH=/usr/bin:/bin \\"
    )
    timeout_line = "/usr/bin/timeout --signal=TERM --kill-after=5s 30s \\"
    producer_line = '"$producer" "$stage" > "$producer_output" 2>&1'
    size_window = (
        'producer_bytes="$(/usr/bin/wc -c < "$producer")"',
        'if test "$producer_bytes" -le 0 || test "$producer_bytes" -gt 8388608; then',
        "printf 'FP-0006 native producer binary size observed=%s maximum=8388608\\n' \\",
        '"$producer_bytes" >&2',
        "exit 1",
        "fi",
    )
    finalizer_line = (
        "python3 scripts/fp0006_runtime_capture_integration.py finalize-lane \\"
    )
    if capture_lines.count(timeout_if) != 2:
        raise EvidenceError("FP-0006 native compile/capture environments differ")
    for line in (timeout_line, producer_line, finalizer_line):
        if capture_lines.count(line) != 1:
            raise EvidenceError("FP-0006 native structural command boundary differs")
    timeout_position = capture_lines.index(timeout_line)
    finalizer_position = capture_lines.index(finalizer_line)
    size_candidates = [
        index for index in range(len(capture_lines))
        if capture_lines[index:index + len(size_window)] == size_window
    ]
    if len(size_candidates) != 1:
        raise EvidenceError("FP-0006 native producer size boundary differs")
    if not size_candidates[0] < timeout_position < finalizer_position:
        raise EvidenceError("FP-0006 native producer size check is reordered")
    timeout_candidates = [
        index for index, line in enumerate(capture_lines)
        if line == timeout_if
        and capture_lines[index:index + 4] == (
            timeout_if, timeout_line, producer_line, "then",
        )
    ]
    if len(timeout_candidates) != 1:
        raise EvidenceError("FP-0006 native producer timeout condition differs")
    timeout_if_position = timeout_candidates[0]
    exits = tuple(
        line for line in capture_lines
        if re.match(r"^exit(?:\s|$)", line) is not None
    )
    if exits != ('exit "$compile_rc"', "exit 1", "exit 1"):
        raise EvidenceError("FP-0006 native capture has an unapproved exit")
    if any(
        re.match(r"^(?:trap|return)(?:\s|$)", line) is not None
        or re.match(r"^(?:for|while|until|select|case)(?:\s|$)", line) is not None
        or re.match(r"^[A-Za-z_][A-Za-z0-9_]*\(\)\s*\{$", line) is not None
        for line in capture_lines
    ):
        raise EvidenceError("FP-0006 native capture has an overriding control path")
    depth_before = []
    capture_depth = 0
    for line in capture_lines:
        depth_before.append(capture_depth)
        if re.match(r"^if(?:\s|$)", line) is not None:
            capture_depth += 1
        elif line == "fi":
            capture_depth -= 1
            if capture_depth < 0:
                raise EvidenceError("FP-0006 native condition scope is unbalanced")
        elif re.match(r"^elif(?:\s|$)", line) is not None:
            raise EvidenceError("FP-0006 native has an unapproved conditional branch")
    if capture_depth != 0:
        raise EvidenceError("FP-0006 native condition scope is unbalanced")
    if (
        depth_before[timeout_if_position] != 0
        or depth_before[timeout_position] != 1
        or depth_before[finalizer_position] != 0
    ):
        raise EvidenceError("FP-0006 native timeout/finalizer reachability differs")
    uses = re.findall(r"(?m)^\s*uses:\s*(\S+)", job_text)
    if len(uses) != 3 or any(
        re.fullmatch(r"[^@]+@[0-9a-f]{40}", value) is None for value in uses
    ):
        raise EvidenceError("FP-0006 native actions are not exactly digest pinned")


def _validate_exact_build_workflow_v2(text: str) -> str:
    native_separator = "\n  fp0006-native-rust-capture:\n"
    capture_separator = "\n  rk006-full-source-build-capture:\n"
    if text.count(native_separator) != 1 or text.count(capture_separator) != 1:
        raise EvidenceError(
            "exact build workflow must contain one FP-0006 job and one trailing RK-006 capture job"
        )
    exact_build_text, native_and_capture = text.split(native_separator, 1)
    if capture_separator not in native_and_capture:
        raise EvidenceError("FP-0006 native job must precede the trailing RK-006 capture job")
    native_tail, capture_tail = native_and_capture.split(capture_separator, 1)
    _validate_fp0006_native_capture_job(
        "  fp0006-native-rust-capture:\n" + native_tail
    )
    _validate_rk006_capture_job(
        "  rk006-full-source-build-capture:\n" + capture_tail
    )

    jobs_marker = "\njobs:\n"
    if exact_build_text.count(jobs_marker) != 1:
        raise EvidenceError("exact build workflow prefix scope differs")
    workflow_prefix = exact_build_text[: exact_build_text.index(jobs_marker) + 1]
    if _sha256_bytes(workflow_prefix.encode("utf-8")) != (
        EXPECTED_EXACT_BUILD_PREFIX_SHA256
    ):
        raise EvidenceError("exact build workflow prefix scope differs")
    expected_env = (
        "\nenv:\n"
        "  ROCKY_IMAGE: rockylinux/rockylinux:10.2@sha256:"
        "e372170ca8630f0f03e9b70fdd0bf4a3ce3426b0de7cdba615f06337389de176\n"
        "  EXPECTED_HEAD_SHA: ${{ inputs.validation_sha || "
        "github.event.pull_request.head.sha || github.sha }}\n"
        "  EXPECTED_KERNEL_RELEASE: "
        + EXPECTED_KERNEL_RELEASE
        + "\n"
        "  KBUILD_BUILD_HOST: rocky-10.2-x86_64\n"
        '  KBUILD_BUILD_TIMESTAMP: "Tue, 11 Aug 2026 07:40:34 +0000"\n'
        "  KBUILD_BUILD_USER: mckernel\n"
        '  KBUILD_BUILD_VERSION: "1"\n'
        "  NATIVE_KERNEL_LOCALVERSION: "
        + EXPECTED_KERNEL_LOCALVERSION
        + "\n"
        '  SOURCE_DATE_EPOCH: "1786434034"\n\n'
    )
    if not workflow_prefix.endswith(expected_env):
        raise EvidenceError("exact build workflow environment mapping differs")

    preamble = (
        "jobs:\n"
        "  exact-build:\n"
        "    name: Compile three native modules (credit forbidden)\n"
        "    runs-on: ubuntu-24.04\n"
        "    timeout-minutes: 330\n"
        "    container:\n"
        "      image: rockylinux/rockylinux:10.2@sha256:"
        "e372170ca8630f0f03e9b70fdd0bf4a3ce3426b0de7cdba615f06337389de176\n"
        "    defaults:\n"
        "      run:\n"
        "        shell: /usr/bin/bash --noprofile --norc -p -e -o pipefail {0}\n"
        "\n"
        "    steps:\n"
    )
    job_text = exact_build_text[exact_build_text.index("jobs:\n") :]
    if not job_text.startswith(preamble):
        raise EvidenceError("exact build workflow job scope differs")
    expected_names = list(EXPECTED_EXACT_BUILD_STEP_SHA256)
    steps = _split_named_steps(job_text[len(preamble) :], expected_names, "exact build")

    module_targets = re.findall(
        r"(?ms)^\s*module_targets=\(\n(?P<body>.*?)^\s*\)\n",
        steps["Compile the exact kernel and native Rust modules"],
    )
    if len(module_targets) != 1 or [
        line.strip() for line in module_targets[0].splitlines() if line.strip()
    ] != BUILD_MODULE_TARGETS:
        raise EvidenceError("exact build workflow module target scope differs")

    active = "\n".join(_active_shell_lines(job_text))
    logical = re.sub(r"\\\n\s*", " ", active)
    make_lines = [line.strip() for line in logical.splitlines() if "/usr/bin/make" in line]
    if len(make_lines) != 6:
        raise EvidenceError("exact build workflow Kbuild release scope differs")
    make_targets = (
        "olddefconfig",
        "olddefconfig",
        "rustavailable",
        "bzImage",
        '"${module_targets[@]}"',
        'kernelrelease)"',
    )
    required_make_arguments = (
        'ARCH=x86_64',
        'LLVM=1',
        'LOCALVERSION="$NATIVE_KERNEL_LOCALVERSION"',
        'KBUILD_BUILD_HOST="$KBUILD_BUILD_HOST"',
        'KBUILD_BUILD_TIMESTAMP="$KBUILD_BUILD_TIMESTAMP"',
        'KBUILD_BUILD_USER="$KBUILD_BUILD_USER"',
        'KBUILD_BUILD_VERSION="$KBUILD_BUILD_VERSION"',
        'SOURCE_DATE_EPOCH="$SOURCE_DATE_EPOCH"',
    )
    for index, (line, target) in enumerate(zip(make_lines, make_targets)):
        if (
            line.count('"${kbuild_environment[@]}" /usr/bin/make') != 1
            or any(line.count(argument) != 1 for argument in required_make_arguments)
            or not line.endswith(target)
            or any(
                token in line
                for token in (
                    " GNUMAKEFLAGS=",
                    " MAKEFILES=",
                    " MAKEFLAGS=",
                    " MAKEOVERRIDES=",
                    " MFLAGS=",
                )
            )
        ):
            raise EvidenceError(
                "exact build workflow command scope differs at Kbuild invocation {0}".format(
                    index + 1
                )
            )
    if any(
        " modules" in line or " M=" in line for line in make_lines
    ):
        raise EvidenceError("exact build workflow invokes a broad module build")

    compile_text = steps["Compile the exact kernel and native Rust modules"]
    compile_positions = [
        compile_text.find("run_phase rustavailable"),
        compile_text.find("run_phase bzImage"),
        compile_text.find("run_phase native-modules"),
    ]
    if (
        any(position < 0 for position in compile_positions)
        or compile_positions != sorted(compile_positions)
    ):
        raise EvidenceError("exact build workflow commands are out of order")

    error_labels = {
        expected_names[0]: "exact build workflow bootstrap scope differs",
        expected_names[1]: "exact build workflow prebuild scope differs",
        expected_names[2]: "exact build workflow prebuild scope differs",
        expected_names[3]: "exact build workflow prebuild scope differs",
        expected_names[4]: "exact build workflow CONFIG_MODULES prerequisite differs",
        expected_names[5]: (
            "exact build workflow compile step command scope or failure capture differs"
        ),
        expected_names[6]: "exact build workflow artifact scope differs",
        expected_names[7]: "exact build workflow upload scope differs",
    }
    for name in expected_names:
        if _sha256_bytes(steps[name].encode("utf-8")) != (
            EXPECTED_EXACT_BUILD_STEP_SHA256[name]
        ):
            raise EvidenceError(error_labels[name])
    if job_text.count("        if: ${{ always() }}\n") != 1:
        raise EvidenceError("exact build workflow upload scope differs")
    return exact_build_text


def _validate_exact_build_workflow(text: str) -> str:
    return _validate_exact_build_workflow_v2(text)
    native_separator = "\n  fp0006-native-rust-capture:\n"
    capture_separator = "\n  rk006-full-source-build-capture:\n"
    if text.count(native_separator) != 1 or text.count(capture_separator) != 1:
        raise EvidenceError(
            "exact build workflow must contain one FP-0006 job and one trailing RK-006 capture job"
        )
    exact_build_text, native_and_capture = text.split(native_separator, 1)
    if capture_separator not in native_and_capture:
        raise EvidenceError("FP-0006 native job must precede the trailing RK-006 capture job")
    native_tail, capture_tail = native_and_capture.split(capture_separator, 1)
    _validate_fp0006_native_capture_job(
        "  fp0006-native-rust-capture:\n" + native_tail
    )
    _validate_rk006_capture_job(
        "  rk006-full-source-build-capture:\n" + capture_tail
    )
    text = exact_build_text
    jobs_marker = "\njobs:\n"
    if text.count(jobs_marker) != 1:
        raise EvidenceError("exact build workflow prefix scope differs")
    workflow_prefix = text[: text.index(jobs_marker) + 1]
    if _sha256_bytes(workflow_prefix.encode("utf-8")) != (
        EXPECTED_EXACT_BUILD_PREFIX_SHA256
    ):
        raise EvidenceError("exact build workflow prefix scope differs")
    expected_env = (
        "\nenv:\n"
        "  ROCKY_IMAGE: rockylinux/rockylinux:10.2@sha256:"
        "e372170ca8630f0f03e9b70fdd0bf4a3ce3426b0de7cdba615f06337389de176\n"
        "  EXPECTED_HEAD_SHA: ${{ inputs.validation_sha || "
        "github.event.pull_request.head.sha || github.sha }}\n"
        "  EXPECTED_KERNEL_RELEASE: "
        + EXPECTED_KERNEL_RELEASE
        + "\n"
        "  KBUILD_BUILD_HOST: rocky-10.2-x86_64\n"
        '  KBUILD_BUILD_TIMESTAMP: "Tue, 11 Aug 2026 07:40:34 +0000"\n'
        "  KBUILD_BUILD_USER: mckernel\n"
        '  KBUILD_BUILD_VERSION: "1"\n'
        "  NATIVE_KERNEL_LOCALVERSION: "
        + EXPECTED_KERNEL_LOCALVERSION
        + "\n"
        '  SOURCE_DATE_EPOCH: "1786434034"\n\n'
    )
    if not workflow_prefix.endswith(expected_env):
        raise EvidenceError("exact build workflow environment mapping differs")
    for name in EXPECTED_REPRODUCIBLE_BUILD_ENVIRONMENT_NAMES:
        if (
            len(re.findall(r"(?m)^\s*{0}:".format(re.escape(name)), text)) != 4
            or text.count(name) != 32
        ):
            raise EvidenceError("exact build reproducible environment scope differs")
    active_workflow = "\n".join(_active_shell_lines(text))
    logical_workflow = re.sub(r"\\\n\s*", " ", active_workflow)
    kbuild_commands = re.findall(
        r'(?<![A-Za-z0-9_])make(?:\s+-s)?\s+-C\s+"\$NATIVE_SOURCE_ROOT"[^\n]*',
        logical_workflow,
    )
    if len(kbuild_commands) != 6 or any(
        command.count('LOCALVERSION="$NATIVE_KERNEL_LOCALVERSION"') != 1
        for command in kbuild_commands
    ):
        raise EvidenceError("exact build workflow Kbuild release scope differs")
    job_preamble = (
        "jobs:\n"
        "  exact-build:\n"
        "    name: Compile three native modules (credit forbidden)\n"
        "    runs-on: ubuntu-24.04\n"
        "    timeout-minutes: 330\n"
        "    container:\n"
        "      image: rockylinux/rockylinux:10.2@sha256:"
        "e372170ca8630f0f03e9b70fdd0bf4a3ce3426b0de7cdba615f06337389de176\n"
        "    defaults:\n"
        "      run:\n"
        "        shell: bash\n"
        "\n"
        "    steps:\n"
    )
    if text.count(job_preamble) != 1:
        raise EvidenceError("exact build workflow job scope differs")

    bootstrap_header = (
        "      - name: Refuse the wrong runtime and install exact build tools\n"
    )
    checkout_header = (
        "      - name: Check out the exact candidate without credentials\n"
    )
    job_start = text.index(job_preamble) + len(job_preamble)
    if (
        text.count(bootstrap_header) != 1
        or text.count(checkout_header) != 1
        or text.index(bootstrap_header) != job_start
    ):
        raise EvidenceError("exact build workflow bootstrap scope differs")
    bootstrap_start = text.index(bootstrap_header) + len(bootstrap_header)
    checkout_start = text.index(checkout_header)
    if checkout_start <= bootstrap_start:
        raise EvidenceError("exact build workflow bootstrap scope differs")
    bootstrap_step = text[bootstrap_start:checkout_start]
    run_marker = "        run: |\n"
    if bootstrap_step.count(run_marker) != 1:
        raise EvidenceError("exact build workflow bootstrap scope differs")
    bootstrap_preamble, bootstrap_body = bootstrap_step.split(run_marker, 1)
    if bootstrap_preamble:
        raise EvidenceError("exact build workflow bootstrap scope differs")
    bootstrap_commands = tuple(
        line.strip()
        for line in bootstrap_body.split("\n")
        if line.strip() and not line.strip().startswith("#")
    )
    openssl_commands = (
        "openssl openssl-devel patch perl python3 python3-devel python3-pyyaml "
        "redhat-rpm-config \\",
        'openssl_path="$(command -v openssl)"',
        'test "$openssl_path" = /usr/bin/openssl',
        'test "$(rpm -qf --qf \'%{NAME}\\n\' "$openssl_path")" = openssl',
        "openssl version",
    )
    openssl_positions = []
    for command in openssl_commands:
        if bootstrap_commands.count(command) != 1:
            raise EvidenceError(
                "exact build workflow lacks the uniquely bound Rocky OpenSSL CLI closure"
            )
        openssl_positions.append(bootstrap_commands.index(command))
    if openssl_positions != sorted(openssl_positions):
        raise EvidenceError("exact build workflow verifies OpenSSL out of order")
    expected_bootstrap_commands = (
        "set -euo pipefail",
        'evidence_dir="$RUNNER_TEMP/native-rust-build-evidence"',
        'mkdir -p "$evidence_dir"',
        'printf \'%s\\n\' "bootstrap-started" > "$evidence_dir/workflow-state"',
        'test "$KBUILD_BUILD_HOST" = rocky-10.2-x86_64',
        'test "$KBUILD_BUILD_TIMESTAMP" = "Tue, 11 Aug 2026 07:40:34 +0000"',
        'test "$KBUILD_BUILD_USER" = mckernel',
        'test "$KBUILD_BUILD_VERSION" = 1',
        'test "$SOURCE_DATE_EPOCH" = 1786434034',
        "printf '%s\\n' \\",
        '"KBUILD_BUILD_HOST=$KBUILD_BUILD_HOST" \\',
        '"KBUILD_BUILD_TIMESTAMP=$KBUILD_BUILD_TIMESTAMP" \\',
        '"KBUILD_BUILD_USER=$KBUILD_BUILD_USER" \\',
        '"KBUILD_BUILD_VERSION=$KBUILD_BUILD_VERSION" \\',
        '"SOURCE_DATE_EPOCH=$SOURCE_DATE_EPOCH" \\',
        '> "$evidence_dir/build.environment"',
        'test "$(uname -m)" = x86_64',
        ". /etc/os-release",
        'test "$ID" = rocky',
        'test "$VERSION_ID" = 10.2',
        "dnf -y --setopt=install_weak_deps=False install dnf-plugins-core",
        "dnf config-manager --set-enabled crb",
        "dnf -y --setopt=install_weak_deps=False install \\",
        "bc binutils bison bindgen-cli bpftool cargo clang cpio diffutils \\",
        "dwarves elfutils-libelf-devel findutils flex gcc git-core gzip \\",
        "hostname kernel-rpm-macros kmod lld llvm make ncurses-devel \\",
        openssl_commands[0],
        "rpm-build rust rust-src rustfmt tar which xz zstd",
        openssl_commands[1],
        openssl_commands[2],
        openssl_commands[3],
        openssl_commands[4],
        "dnf clean all",
        'printf \'%s\\n\' "bootstrap-complete" > "$evidence_dir/workflow-state"',
    )
    if bootstrap_commands != expected_bootstrap_commands:
        raise EvidenceError("exact build workflow bootstrap scope differs")

    resolution_header = "      - name: Resolve the evidence-only module configuration twice\n"
    if text.count(resolution_header) != 1:
        raise EvidenceError("exact build workflow prebuild scope differs")
    resolution_header_start = text.index(resolution_header)
    preparation = text[checkout_start:resolution_header_start]
    if _sha256_bytes(preparation.encode("utf-8")) != (
        EXPECTED_EXACT_BUILD_PREPARATION_SHA256
    ):
        raise EvidenceError("exact build workflow prebuild scope differs")
    active_preparation = "\n".join(_active_shell_lines(preparation))
    if re.search(r"(?<![A-Za-z0-9_])(?:g?make|MAKE)(?![A-Za-z0-9_])", active_preparation):
        raise EvidenceError("exact build workflow prebuild invokes an unbound build tool")

    arrays = re.findall(
        r"(?ms)^\s*module_targets=\(\n(?P<body>.*?)^\s*\)\n", text
    )
    if len(arrays) != 1:
        raise EvidenceError("exact build workflow must declare one module target array")
    targets = [line.strip() for line in arrays[0].splitlines() if line.strip()]
    if targets != BUILD_MODULE_TARGETS:
        raise EvidenceError("exact build workflow module target scope differs")

    required_commands = [
        (
            'run_phase rustavailable make -C "$NATIVE_SOURCE_ROOT" '
            'O="$NATIVE_BUILD_DIR" ARCH=x86_64 LLVM=1 '
            'LOCALVERSION="$NATIVE_KERNEL_LOCALVERSION" rustavailable'
        ),
        (
            'run_phase bzImage make -C "$NATIVE_SOURCE_ROOT" '
            'O="$NATIVE_BUILD_DIR" ARCH=x86_64 LLVM=1 '
            'LOCALVERSION="$NATIVE_KERNEL_LOCALVERSION" -j2 bzImage'
        ),
        (
            'run_phase native-modules make -C "$NATIVE_SOURCE_ROOT" '
            'O="$NATIVE_BUILD_DIR" ARCH=x86_64 LLVM=1 '
            'LOCALVERSION="$NATIVE_KERNEL_LOCALVERSION" '
            '-j2 "${module_targets[@]}"'
        ),
    ]
    resolution_start = text.index(resolution_header) + len(resolution_header)
    next_step = re.search(r"(?m)^      - name: .+$", text[resolution_start:])
    if next_step is None:
        raise EvidenceError("exact build workflow CONFIG_MODULES prerequisite differs")
    resolution_end = resolution_start + next_step.start()
    resolution_step = text[resolution_start:resolution_end]
    if text[resolution_end:].splitlines()[0] != (
        "      - name: Compile the exact kernel and native Rust modules"
    ):
        raise EvidenceError("exact build workflow CONFIG_MODULES prerequisite differs")
    if resolution_step.count(run_marker) != 1:
        raise EvidenceError("exact build workflow CONFIG_MODULES prerequisite differs")
    step_preamble, run_body = resolution_step.split(run_marker, 1)
    if step_preamble != (
        "        env:\n"
        "          BUILD_DIR: ${{ runner.temp }}/native-rust-build\n"
    ):
        raise EvidenceError("exact build workflow CONFIG_MODULES prerequisite differs")
    active_commands = tuple(
        line.strip()
        for line in run_body.split("\n")
        if line.strip() and not line.strip().startswith("#")
    )
    expected_resolution_commands = (
        "set -euo pipefail",
    ) + EXPECTED_REPRODUCIBLE_BUILD_ASSERTION_COMMANDS + (
        'mkdir -p "$BUILD_DIR"',
        'cp "$NATIVE_BASELINE_CONFIG" "$BUILD_DIR/.config"',
        '"$NATIVE_SOURCE_ROOT/scripts/kconfig/merge_config.sh" -m -O "$BUILD_DIR" \\',
        '"$BUILD_DIR/.config" \\',
        '"$GITHUB_WORKSPACE/host-kernel/rocky/configs/rust-minimal.config" \\',
        '"$GITHUB_WORKSPACE/host-kernel/rocky/configs/native-rust-evidence.config"',
        'make -C "$NATIVE_SOURCE_ROOT" O="$BUILD_DIR" ARCH=x86_64 LLVM=1 \\',
        'LOCALVERSION="$NATIVE_KERNEL_LOCALVERSION" olddefconfig',
        'cp "$BUILD_DIR/.config" "$BUILD_DIR/resolved-first.config"',
        'make -C "$NATIVE_SOURCE_ROOT" O="$BUILD_DIR" ARCH=x86_64 LLVM=1 \\',
        'LOCALVERSION="$NATIVE_KERNEL_LOCALVERSION" olddefconfig',
        'cmp "$BUILD_DIR/resolved-first.config" "$BUILD_DIR/.config"',
        'grep -qx \'CONFIG_WERROR=y\' "$BUILD_DIR/.config"',
        'grep -qx \'CONFIG_MODULES=y\' "$BUILD_DIR/.config"',
        "for symbol in \\",
        "CONFIG_MCKERNEL_IHK_RUST \\",
        "CONFIG_MCKERNEL_IHK_SMP_X86_64_RUST \\",
        "CONFIG_MCKERNEL_MCCTRL_RUST; do",
        'grep -qx "$symbol=m" "$BUILD_DIR/.config"',
        "done",
        'EVIDENCE_DIR="$RUNNER_TEMP/native-rust-build-evidence"',
        'MATRIX_DIR="$RUNNER_TEMP/native-rust-kconfig-matrix"',
        'mkdir -p "$EVIDENCE_DIR"',
        'test ! -e "$MATRIX_DIR"',
        "python3 scripts/native_rust_kconfig_solver.py run \\",
        '--source "$NATIVE_SOURCE_ROOT" \\',
        '--seed "$BUILD_DIR/.config" \\',
        '--matrix-dir "$MATRIX_DIR"',
        'cp "$MATRIX_DIR/kconfig-solver-matrix.json" \\',
        '"$EVIDENCE_DIR/kconfig-solver-matrix.json"',
        'chmod 0644 "$EVIDENCE_DIR/kconfig-solver-matrix.json"',
        "python3 scripts/native_rust_kconfig_solver.py check \\",
        '--matrix "$EVIDENCE_DIR/kconfig-solver-matrix.json" \\',
        '--source "$NATIVE_SOURCE_ROOT" \\',
        '--seed "$BUILD_DIR/.config"',
        'printf \'NATIVE_BUILD_DIR=%s\\n\' "$BUILD_DIR" >> "$GITHUB_ENV"',
    )
    if active_commands != expected_resolution_commands:
        raise EvidenceError("exact build workflow CONFIG_MODULES prerequisite differs")

    compile_header = "      - name: Compile the exact kernel and native Rust modules\n"
    if text.count(compile_header) != 1:
        raise EvidenceError("exact build workflow compile step differs")
    compile_start = text.index(compile_header) + len(compile_header)
    next_step = re.search(r"(?m)^      - name: .+$", text[compile_start:])
    if next_step is None:
        raise EvidenceError("exact build workflow compile step differs")
    compile_end = compile_start + next_step.start()
    compile_step = text[compile_start:compile_end]
    metadata_header = "      - name: Validate built metadata and capture immutable diagnostics"
    if text[compile_end:].splitlines()[0] != metadata_header:
        raise EvidenceError("exact build workflow compile step differs")
    if compile_step.count(run_marker) != 1:
        raise EvidenceError("exact build workflow compile step differs")
    compile_preamble, compile_body = compile_step.split(run_marker, 1)
    if compile_preamble:
        raise EvidenceError("exact build workflow compile step differs")
    compile_commands = tuple(
        line.strip()
        for line in compile_body.split("\n")
        if line.strip() and not line.strip().startswith("#")
    )
    normalized_compile = re.sub(r"\\\n\s*", " ", "\n".join(compile_commands))
    collapsed_compile = re.sub(r"\s+", " ", normalized_compile)
    positions: list[int] = []
    for command in required_commands:
        if collapsed_compile.count(command) != 1:
            raise EvidenceError("exact build workflow command scope differs")
        positions.append(collapsed_compile.index(command))
    if positions != sorted(positions):
        raise EvidenceError("exact build workflow commands are out of order")
    for line in normalized_compile.splitlines():
        if 'make -C "$NATIVE_SOURCE_ROOT"' not in line:
            continue
        tokens = line.split()
        if "modules" in tokens or any(token.startswith("M=") for token in tokens):
            raise EvidenceError("exact build workflow invokes a broad module build")
    expected_compile_commands = (
        "set -euo pipefail",
        'evidence_dir="$RUNNER_TEMP/native-rust-build-evidence"',
        'mkdir -p "$evidence_dir"',
    ) + EXPECTED_REPRODUCIBLE_BUILD_ASSERTION_COMMANDS + (
        _reproducible_build_record_commands("$evidence_dir")
    ) + (
        "module_targets=(",
        "drivers/misc/mckernel/ihk.ko",
        "drivers/misc/mckernel/ihk-smp-x86_64.ko",
        "drivers/misc/mckernel/mcctrl.ko",
        ")",
        'printf \'%s\\n\' "${module_targets[@]}" > "$evidence_dir/module-targets.txt"',
        ': > "$evidence_dir/build.commands"',
        'printf \'%s\\n\' not-started > "$evidence_dir/build.phase"',
        "run_phase() {",
        'local phase="$1"',
        "shift",
        'local -a command=("$@")',
        'printf \'%s\\n\' "$phase" > "$evidence_dir/build.phase"',
        'printf \'%q\' "${command[0]}" >> "$evidence_dir/build.commands"',
        'printf \' %q\' "${command[@]:1}" >> "$evidence_dir/build.commands"',
        'printf \'\\n\' >> "$evidence_dir/build.commands"',
        '"${command[@]}"',
        "}",
        "set +e",
        "(",
        "set -e",
        "run_phase rustavailable \\",
        'make -C "$NATIVE_SOURCE_ROOT" O="$NATIVE_BUILD_DIR" \\',
        'ARCH=x86_64 LLVM=1 LOCALVERSION="$NATIVE_KERNEL_LOCALVERSION" \\',
        "rustavailable",
        "run_phase bzImage \\",
        'make -C "$NATIVE_SOURCE_ROOT" O="$NATIVE_BUILD_DIR" \\',
        'ARCH=x86_64 LLVM=1 LOCALVERSION="$NATIVE_KERNEL_LOCALVERSION" \\',
        "-j2 bzImage",
        "run_phase native-modules \\",
        'make -C "$NATIVE_SOURCE_ROOT" O="$NATIVE_BUILD_DIR" \\',
        'ARCH=x86_64 LLVM=1 LOCALVERSION="$NATIVE_KERNEL_LOCALVERSION" \\',
        '-j2 "${module_targets[@]}"',
        'printf \'%s\\n\' complete > "$evidence_dir/build.phase"',
        ') 2>&1 | tee "$evidence_dir/build.log"',
        'pipeline_status=("${PIPESTATUS[@]}")',
        "set -e",
        'producer_status="${pipeline_status[0]}"',
        'tee_status="${pipeline_status[1]}"',
        'printf \'%s\\n\' "$producer_status" > "$evidence_dir/build.exit-code"',
        'printf \'%s\\n\' "$tee_status" > "$evidence_dir/build-log.exit-code"',
        "if (( producer_status != 0 )); then",
        'exit "$producer_status"',
        "fi",
        'exit "$tee_status"',
    )
    if compile_commands != expected_compile_commands:
        raise EvidenceError("exact build workflow failure capture differs")

    metadata_header_line = metadata_header + "\n"
    if text.count(metadata_header_line) != 1:
        raise EvidenceError("exact build workflow artifact scope differs")
    metadata_start = text.index(metadata_header_line) + len(metadata_header_line)
    next_step = re.search(r"(?m)^      - name: .+$", text[metadata_start:])
    if next_step is None:
        raise EvidenceError("exact build workflow artifact scope differs")
    metadata_end = metadata_start + next_step.start()
    metadata_step = text[metadata_start:metadata_end]
    upload_header = "      - name: Upload compiler evidence or first-failure diagnostics"
    if text[metadata_end:].splitlines()[0] != upload_header:
        raise EvidenceError("exact build workflow artifact scope differs")
    if metadata_step.count(run_marker) != 1:
        raise EvidenceError("exact build workflow artifact scope differs")
    metadata_preamble, metadata_body = metadata_step.split(run_marker, 1)
    if metadata_preamble:
        raise EvidenceError("exact build workflow artifact scope differs")
    metadata_commands = tuple(
        line.strip()
        for line in metadata_body.split("\n")
        if line.strip() and not line.strip().startswith("#")
    )
    expected_metadata_commands = (
        "set -euo pipefail",
        'EVIDENCE_DIR="$RUNNER_TEMP/native-rust-build-evidence"',
    ) + EXPECTED_REPRODUCIBLE_BUILD_ASSERTION_COMMANDS + (
        _reproducible_build_record_commands("$EVIDENCE_DIR")
    ) + (
        'module_root="$NATIVE_BUILD_DIR/drivers/misc/mckernel"',
        'ihk="$module_root/ihk.ko"',
        'smp="$module_root/ihk-smp-x86_64.ko"',
        'mcctrl="$module_root/mcctrl.ko"',
        'test -s "$ihk"',
        'test -s "$smp"',
        'test -s "$mcctrl"',
        "(",
        'cd "$NATIVE_BUILD_DIR"',
        "find . -type f -name '*.ko' -printf '%P\\n' | LC_ALL=C sort",
        ') > "$EVIDENCE_DIR/built-module-artifacts.txt"',
        'LC_ALL=C sort "$EVIDENCE_DIR/module-targets.txt" \\',
        '> "$EVIDENCE_DIR/module-targets.sorted"',
        'cmp "$EVIDENCE_DIR/module-targets.sorted" \\',
        '"$EVIDENCE_DIR/built-module-artifacts.txt"',
        'rm "$EVIDENCE_DIR/module-targets.sorted"',
        'git -c safe.directory="$GITHUB_WORKSPACE" rev-parse HEAD \\',
        '> "$EVIDENCE_DIR/commit.sha"',
        'for module in "$ihk" "$smp" "$mcctrl"; do',
        'name="$(basename "$module")"',
        'cp "$module" "$EVIDENCE_DIR/$name"',
        'modinfo "$module" > "$EVIDENCE_DIR/$name.modinfo"',
        'readelf -p .modinfo "$module" > "$EVIDENCE_DIR/$name.modinfo-section"',
        'readelf -SWr "$module" > "$EVIDENCE_DIR/$name.readelf"',
        'nm -A -a "$module" > "$EVIDENCE_DIR/$name.nm"',
        "done",
        "(",
        'cd "$EVIDENCE_DIR"',
        'find . -maxdepth 1 -type f \\',
        "! -name PRECHECK_SHA256SUMS ! -name SHA256SUMS -printf '%P\\0' \\",
        "| sort -z | xargs -0 sha256sum -- > PRECHECK_SHA256SUMS",
        "sha256sum --check --strict PRECHECK_SHA256SUMS",
        ")",
        "for name in ihk.ko ihk-smp-x86_64.ko mcctrl.ko; do",
        'module="$EVIDENCE_DIR/$name"',
        'vermagic="$(modinfo -F vermagic "$module")"',
        'test -n "$vermagic"',
        'test "$(printf \'%s\\n\' "$vermagic" | wc -l)" = 1',
        'test "${vermagic%% *}" = "$EXPECTED_KERNEL_RELEASE"',
        "done",
        'python3 scripts/ihk_native_lifecycle_check.py --repo "$GITHUB_WORKSPACE" --module "$ihk"',
        'python3 scripts/ihk_os_registry_check.py --repo "$GITHUB_WORKSPACE"',
        'test "$(rustc --version | awk \'{print $2}\')" = "1.92.0"',
        'MCKERNEL_RUSTC_1_92="$(command -v rustc)" \\',
        "python3 -m unittest -v scripts.tests.test_ihk_os_registry_check",
        'python3 scripts/ihk_ioctl_dispatch_check.py --repo "$GITHUB_WORKSPACE"',
        'MCKERNEL_RUSTC_1_92="$(command -v rustc)" \\',
        "python3 -m unittest -v scripts.tests.test_ihk_ioctl_dispatch_check",
        'python3 scripts/ihk_smp_native_lifecycle_check.py --repo "$GITHUB_WORKSPACE" --module "$smp"',
        'python3 scripts/mcctrl_native_lifecycle_check.py --repo "$GITHUB_WORKSPACE" --module "$mcctrl"',
        'cp "$NATIVE_BUILD_DIR/.config" "$EVIDENCE_DIR/resolved.config"',
        'cp "$NATIVE_BUILD_DIR/arch/x86/boot/bzImage" "$EVIDENCE_DIR/bzImage"',
        'cp "$NATIVE_SOURCE_ROOT/drivers/misc/mckernel/stage-lock.json" "$EVIDENCE_DIR/stage-lock.json"',
        'kernel_release="$(make -s -C "$NATIVE_SOURCE_ROOT" O="$NATIVE_BUILD_DIR" \\',
        'ARCH=x86_64 LLVM=1 LOCALVERSION="$NATIVE_KERNEL_LOCALVERSION" kernelrelease)"',
        'test "$kernel_release" = "$EXPECTED_KERNEL_RELEASE"',
        'printf \'%s\\n\' "$kernel_release" > "$EVIDENCE_DIR/kernel.release"',
        "cmd_records=(",
        ".ihk-smp-x86_64.ko.cmd",
        ".ihk-smp-x86_64.mod.cmd",
        ".ihk-smp-x86_64.mod.o.cmd",
        ".ihk-smp-x86_64.o.cmd",
        ".ihk.ko.cmd",
        ".ihk.mod.cmd",
        ".ihk.mod.o.cmd",
        ".ihk.o.cmd",
        ".ihk_smp_x86_64.o.cmd",
        ".mcctrl.ko.cmd",
        ".mcctrl.mod.cmd",
        ".mcctrl.mod.o.cmd",
        ".mcctrl.o.cmd",
        ")",
        "mod_records=(ihk-smp-x86_64.mod ihk.mod mcctrl.mod)",
        'for record in "${cmd_records[@]}" "${mod_records[@]}"; do',
        'test -f "$module_root/$record"',
        'test ! -L "$module_root/$record"',
        'cp "$module_root/$record" "$EVIDENCE_DIR/$record"',
        "done",
        "python3 scripts/native_rust_kbuild_link_closure.py \\",
        '--records-dir "$EVIDENCE_DIR" \\',
        '--stage-lock "$EVIDENCE_DIR/stage-lock.json" \\',
        '--output "$EVIDENCE_DIR/kbuild-link-closure.json"',
        "python3 scripts/native_rust_kbuild_link_closure.py \\",
        '--records-dir "$EVIDENCE_DIR" \\',
        '--stage-lock "$EVIDENCE_DIR/stage-lock.json" \\',
        '--check-output "$EVIDENCE_DIR/kbuild-link-closure.json"',
        "(",
        'cd "$EVIDENCE_DIR"',
        "find . -maxdepth 1 -type f ! -name SHA256SUMS -printf '%P\\0' \\",
        "| sort -z | xargs -0 sha256sum -- > SHA256SUMS",
        "sha256sum --check --strict SHA256SUMS",
        ")",
    )
    if metadata_commands != expected_metadata_commands:
        raise EvidenceError("exact build workflow artifact scope differs")

    upload_header_line = upload_header + "\n"
    if text.count(upload_header_line) != 1:
        raise EvidenceError("exact build workflow upload scope differs")
    upload_start = text.index(upload_header_line) + len(upload_header_line)
    expected_upload = (
        "        if: ${{ always() }}\n"
        "        uses: actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02 # v4.6.2\n"
        "        with:\n"
        "          name: native-rust-exact-build-${{ github.run_id }}-${{ github.run_attempt }}\n"
        "          path: ${{ runner.temp }}/native-rust-build-evidence/\n"
        "          if-no-files-found: error\n"
        "          retention-days: 30\n"
        "          compression-level: 0\n"
        "          include-hidden-files: true\n"
    )
    if text[upload_start:] != expected_upload:
        raise EvidenceError("exact build workflow upload scope differs")
    return text


def _regular_evidence_file(path: Path, label: str, nonempty: bool = True) -> Path:
    if path.is_symlink() or not path.is_file():
        raise EvidenceError("{0} must be a regular non-symlink file".format(label))
    if nonempty and not path.stat().st_size:
        raise EvidenceError("{0} is empty".format(label))
    return path


def _regular_evidence_directory(path: Path, label: str) -> Path:
    raw = os.fspath(path)
    if not isinstance(raw, str) or not raw or "\x00" in raw or "\\" in raw:
        raise EvidenceError("{0} path is unsafe".format(label))
    if raw != "/" and raw.endswith("/"):
        raise EvidenceError("{0} path has a trailing separator".format(label))
    components = raw.split("/")
    if raw.startswith("/"):
        components = components[1:]
    if not components or any(item in ("", ".", "..") for item in components):
        raise EvidenceError("{0} path has an unsafe component".format(label))
    requested = Path(os.path.abspath(raw))
    current = Path(requested.anchor)
    try:
        status = current.lstat()
    except OSError as error:
        raise EvidenceError("cannot inspect {0}: {1}".format(label, error)) from error
    for item in requested.parts[1:]:
        current = current / item
        try:
            status = current.lstat()
        except OSError as error:
            raise EvidenceError("cannot inspect {0}: {1}".format(label, error)) from error
        if stat.S_ISLNK(status.st_mode) or not stat.S_ISDIR(status.st_mode):
            raise EvidenceError(
                "{0} must traverse only real directories".format(label)
            )
    return requested


@contextlib.contextmanager
def _bound_evidence_directory(path: Path, label: str):
    requested = _regular_evidence_directory(path, label)
    try:
        before = requested.lstat()
    except OSError as error:
        raise EvidenceError("cannot inspect {0}: {1}".format(label, error)) from error
    if not hasattr(os, "O_DIRECTORY") or not hasattr(os, "O_NOFOLLOW"):
        raise EvidenceError("{0} requires directory no-follow support".format(label))
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    if hasattr(os, "O_CLOEXEC"):
        flags |= os.O_CLOEXEC
    try:
        descriptor = os.open(str(requested), flags)
    except OSError as error:
        raise EvidenceError("cannot open {0}: {1}".format(label, error)) from error
    opened_identity = None
    try:
        opened = os.fstat(descriptor)
        opened_identity = _stat_identity(opened)
        if (
            not stat.S_ISDIR(opened.st_mode)
            or opened_identity != _stat_identity(before)
        ):
            raise EvidenceError("{0} changed while it was opened".format(label))
        try:
            os.set_inheritable(descriptor, False)
        except OSError as error:
            raise EvidenceError(
                "cannot seal {0} descriptor: {1}".format(label, error)
            ) from error
        bound = Path("/proc/self/fd/{0}".format(descriptor))
        if not bound.is_dir():
            raise EvidenceError("{0} lacks a descriptor-bound path".format(label))
        yield bound, descriptor
    finally:
        try:
            final = os.fstat(descriptor)
            if (
                opened_identity is not None
                and _stat_identity(final) != opened_identity
            ):
                raise EvidenceError(
                    "{0} changed while it was validated".format(label)
                )
        finally:
            os.close(descriptor)


@contextlib.contextmanager
def _bound_evidence_file(path: Path, label: str):
    try:
        before = path.lstat()
    except OSError as error:
        raise EvidenceError("cannot inspect {0}: {1}".format(label, error)) from error
    if stat.S_ISLNK(before.st_mode) or not stat.S_ISREG(before.st_mode):
        raise EvidenceError("{0} must be a regular non-symlink file".format(label))
    if stat.S_IMODE(before.st_mode) != 0o644:
        raise EvidenceError("{0} mode must be 0644".format(label))
    flags = os.O_RDONLY
    if hasattr(os, "O_BINARY"):
        flags |= os.O_BINARY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    if hasattr(os, "O_CLOEXEC"):
        flags |= os.O_CLOEXEC
    try:
        descriptor = os.open(str(path), flags)
    except OSError as error:
        raise EvidenceError("cannot open {0}: {1}".format(label, error)) from error
    opened_identity = None
    try:
        opened = os.fstat(descriptor)
        opened_identity = _stat_identity(opened)
        if opened_identity != _stat_identity(before):
            raise EvidenceError("{0} changed while it was opened".format(label))
        os.set_inheritable(descriptor, False)
        bound = Path("/proc/self/fd/{0}".format(descriptor))
        if not bound.is_file():
            raise EvidenceError("{0} lacks a descriptor-bound path".format(label))
        yield bound, descriptor
    finally:
        try:
            final = os.fstat(descriptor)
            if (
                opened_identity is not None
                and _stat_identity(final) != opened_identity
            ):
                raise EvidenceError(
                    "{0} changed while it was validated".format(label)
                )
        finally:
            os.close(descriptor)


def _runtime_file_size_limit(name: str) -> int:
    if name in RUNTIME_HELPER_ELF_SPEC:
        return MAX_RUNTIME_HELPER_FILE_SIZE
    if name == "initramfs.cpio.gz":
        return MAX_RUNTIME_EVIDENCE_FILE_SIZE
    return MAX_RUNTIME_TEXT_FILE_SIZE


@contextlib.contextmanager
def _bound_capture_runtime_inputs(paths: dict[str, Path]):
    if set(paths) != set(CAPTURE_RUNTIME_INPUT_BASENAMES):
        raise EvidenceError("capture runtime input set differs")
    normalized: dict[str, Path] = {}
    parents: set[Path] = set()
    for field, basename in CAPTURE_RUNTIME_INPUT_BASENAMES.items():
        path = paths[field]
        raw = os.fspath(path)
        if (
            not isinstance(raw, str)
            or not raw
            or "\x00" in raw
            or "\\" in raw
            or not path.is_absolute()
            or ".." in path.parts
            or path.name != basename
        ):
            raise EvidenceError(
                "capture runtime input path differs: {0}".format(basename)
            )
        normalized[field] = path
        parents.add(path.parent)
    if len(parents) != 1:
        raise EvidenceError("capture runtime inputs do not share one parent")
    runtime_parent = next(iter(parents))
    if runtime_parent.name != "native-rust-runtime-evidence":
        raise EvidenceError("capture runtime input parent identity differs")
    retained_runtime_fd = None
    leaf_fds: dict[str, int] = {}
    leaf_identities: dict[str, tuple[Any, ...]] = {}
    try:
        with _bound_evidence_directory(
            runtime_parent, "capture runtime input directory"
        ) as bound_runtime:
            _bound_parent, runtime_fd = bound_runtime
            retained_runtime_fd = os.dup(runtime_fd)
            os.set_inheritable(retained_runtime_fd, False)
            inode_owners: dict[tuple[int, int], str] = {}
            names = list(CAPTURE_RUNTIME_INPUT_BASENAMES.values()) + list(
                RUNTIME_HELPER_ELF_SPEC
            )
            flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
            flags |= getattr(os, "O_CLOEXEC", 0)
            for name in names:
                try:
                    before = os.stat(
                        name, dir_fd=runtime_fd, follow_symlinks=False
                    )
                    descriptor = os.open(name, flags, dir_fd=runtime_fd)
                    opened = os.fstat(descriptor)
                except OSError as error:
                    raise EvidenceError(
                        "cannot bind capture runtime input: {0}".format(name)
                    ) from error
                identity = _stat_identity(before)
                if (
                    not stat.S_ISREG(before.st_mode)
                    or stat.S_IMODE(before.st_mode) != 0o644
                    or before.st_size > _runtime_file_size_limit(name)
                    or (before.st_size == 0 and name != "qemu.log")
                    or _stat_identity(opened) != identity
                ):
                    os.close(descriptor)
                    raise EvidenceError(
                        "capture runtime input shape differs: {0}".format(name)
                    )
                inode = (opened.st_dev, opened.st_ino)
                if inode in inode_owners:
                    os.close(descriptor)
                    raise EvidenceError(
                        "capture runtime inputs contain hard-link aliases: {0}, {1}".format(
                            inode_owners[inode], name
                        )
                    )
                if before.st_nlink != 1 or opened.st_nlink != 1:
                    os.close(descriptor)
                    raise EvidenceError(
                        "capture runtime inputs contain hard-link aliases: {0}".format(
                            name
                        )
                    )
                os.set_inheritable(descriptor, False)
                inode_owners[inode] = name
                leaf_fds[name] = descriptor
                leaf_identities[name] = identity

        if retained_runtime_fd is None:
            raise EvidenceError("capture runtime directory descriptor was not retained")

        def recheck() -> None:
            for name in sorted(leaf_fds):
                try:
                    held = os.fstat(leaf_fds[name])
                    current = os.stat(
                        name,
                        dir_fd=retained_runtime_fd,
                        follow_symlinks=False,
                    )
                except OSError as error:
                    raise EvidenceError(
                        "capture runtime input changed: {0}".format(name)
                    ) from error
                if (
                    _stat_identity(held) != leaf_identities[name]
                    or _stat_identity(current) != leaf_identities[name]
                    or held.st_nlink != 1
                    or current.st_nlink != 1
                ):
                    raise EvidenceError(
                        "capture runtime input changed: {0}".format(name)
                    )

        bound_parent = Path(
            "/proc/self/fd/{0}".format(retained_runtime_fd)
        )
        bound_paths = {
            field: Path("/proc/self/fd/{0}".format(leaf_fds[basename]))
            for field, basename in CAPTURE_RUNTIME_INPUT_BASENAMES.items()
        }
        bound_helpers = {
            name: leaf_fds[name]
            for name in RUNTIME_HELPER_ELF_SPEC
        }
        state: dict[str, Any] = {"published_identity": None}
        try:
            yield (
                bound_parent,
                retained_runtime_fd,
                bound_paths,
                runtime_parent,
                bound_helpers,
                recheck,
                state,
            )
            recheck()
        except BaseException:
            if state["published_identity"] is not None:
                _unlink_exact_capture_output(
                    retained_runtime_fd, state["published_identity"]
                )
                state["published_identity"] = None
            raise
    finally:
        for descriptor in leaf_fds.values():
            os.close(descriptor)
        if retained_runtime_fd is not None:
            os.close(retained_runtime_fd)


def _unlink_exact_capture_output(
    runtime_fd: int, expected_identity: tuple[Any, ...]
) -> None:
    try:
        current = os.stat(
            "capture.json", dir_fd=runtime_fd, follow_symlinks=False
        )
        if _stat_identity(current) != expected_identity:
            raise EvidenceError(
                "capture output changed before failure cleanup"
            )
        os.unlink("capture.json", dir_fd=runtime_fd)
        os.fsync(runtime_fd)
    except EvidenceError:
        raise
    except OSError as error:
        raise EvidenceError(
            "cannot clean failed capture output: {0}".format(error)
        ) from error


def _write_capture_output(
    runtime_fd: int,
    output: Path,
    runtime_parent: Path,
    value: dict[str, Any],
    post_publish_check=None,
) -> tuple[Any, ...]:
    if (
        not output.is_absolute()
        or ".." in output.parts
        or output.name != "capture.json"
        or output.parent != runtime_parent
    ):
        raise EvidenceError("capture output must be capture.json in the runtime input parent")
    payload = _pretty(value).encode("utf-8")
    temporary = ".capture.json.tmp.{0}.{1}".format(
        os.getpid(), hashlib.sha256(os.urandom(32)).hexdigest()[:16]
    )
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_CLOEXEC"):
        flags |= os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = None
    linked = False
    completed = False
    identity = None
    try:
        descriptor = os.open(temporary, flags, 0o600, dir_fd=runtime_fd)
        offset = 0
        while offset < len(payload):
            written = os.write(descriptor, payload[offset:])
            if written <= 0:
                raise EvidenceError("capture output write made no progress")
            offset += written
        os.fchmod(descriptor, 0o644)
        os.fsync(descriptor)
        os.link(
            temporary,
            "capture.json",
            src_dir_fd=runtime_fd,
            dst_dir_fd=runtime_fd,
            follow_symlinks=False,
        )
        linked = True
        os.unlink(temporary, dir_fd=runtime_fd)
        identity = _stat_identity(os.fstat(descriptor))
        metadata = os.stat("capture.json", dir_fd=runtime_fd, follow_symlinks=False)
        if (
            _stat_identity(metadata) != identity
            or not stat.S_ISREG(metadata.st_mode)
            or stat.S_IMODE(metadata.st_mode) != 0o644
            or metadata.st_nlink != 1
            or metadata.st_size != len(payload)
        ):
            raise EvidenceError("capture output identity differs after publication")
        verify_flags = os.O_RDONLY
        if hasattr(os, "O_CLOEXEC"):
            verify_flags |= os.O_CLOEXEC
        if hasattr(os, "O_NOFOLLOW"):
            verify_flags |= os.O_NOFOLLOW
        verify_fd = os.open("capture.json", verify_flags, dir_fd=runtime_fd)
        try:
            digest = hashlib.sha256()
            while True:
                chunk = os.read(verify_fd, 65536)
                if not chunk:
                    break
                digest.update(chunk)
            if (
                _stat_identity(os.fstat(verify_fd)) != identity
                or digest.digest() != hashlib.sha256(payload).digest()
            ):
                raise EvidenceError("capture output bytes differ after publication")
        finally:
            os.close(verify_fd)
        os.fsync(runtime_fd)
        if post_publish_check is not None:
            post_publish_check()
        final_fd_identity = _stat_identity(os.fstat(descriptor))
        final_path_identity = _stat_identity(
            os.stat("capture.json", dir_fd=runtime_fd, follow_symlinks=False)
        )
        if final_fd_identity != identity or final_path_identity != identity:
            raise EvidenceError("capture output changed during final input recheck")
        completed = True
    except OSError as error:
        raise EvidenceError("cannot publish capture output: {0}".format(error)) from error
    finally:
        try:
            if linked and not completed:
                cleanup_identity = identity
                if cleanup_identity is None and descriptor is not None:
                    cleanup_identity = _stat_identity(os.fstat(descriptor))
                if cleanup_identity is None:
                    raise EvidenceError(
                        "capture output cleanup identity is unavailable"
                    )
                _unlink_exact_capture_output(runtime_fd, cleanup_identity)
            if not completed:
                try:
                    os.unlink(temporary, dir_fd=runtime_fd)
                except OSError:
                    pass
        finally:
            if descriptor is not None:
                os.close(descriptor)
    if identity is None:
        raise EvidenceError("capture output identity was not established")
    return identity


def _stat_identity(metadata: os.stat_result) -> tuple[Any, ...]:
    return (
        metadata.st_dev,
        metadata.st_ino,
        metadata.st_mode,
        metadata.st_nlink,
        metadata.st_uid,
        metadata.st_gid,
        metadata.st_size,
        getattr(metadata, "st_mtime_ns", int(metadata.st_mtime * 1000000000)),
        getattr(metadata, "st_ctime_ns", int(metadata.st_ctime * 1000000000)),
    )


def _read_bound_descriptor_bytes(
    descriptor: int, maximum_size: int, label: str
) -> tuple[bytes, tuple[Any, ...]]:
    try:
        before = os.fstat(descriptor)
        identity = _stat_identity(before)
        if (
            not stat.S_ISREG(before.st_mode)
            or stat.S_IMODE(before.st_mode) != 0o644
            or before.st_size < 1
            or before.st_size > maximum_size
        ):
            raise EvidenceError("{0} descriptor shape differs".format(label))
        chunks = []
        offset = 0
        while offset < before.st_size:
            chunk = os.pread(
                descriptor, min(65536, before.st_size - offset), offset
            )
            if not chunk:
                raise EvidenceError("{0} descriptor ended early".format(label))
            chunks.append(chunk)
            offset += len(chunk)
        if os.pread(descriptor, 1, offset):
            raise EvidenceError("{0} descriptor grew while reading".format(label))
        if _stat_identity(os.fstat(descriptor)) != identity:
            raise EvidenceError("{0} descriptor changed while reading".format(label))
        return b"".join(chunks), identity
    except OSError as error:
        raise EvidenceError(
            "cannot read {0} descriptor: {1}".format(label, error)
        ) from error


def _semantic_authority_identity(value: bytes) -> dict[str, Any]:
    return {
        "git_blob_sha1": _git_blob_sha1(value),
        "sha256": _sha256_bytes(value),
        "size": len(value),
    }


def _normalized_runtime_checker_sha256(value: bytes) -> str:
    normalized, count = re.subn(
        br"ISOLATED_SELF_DIGEST:[0-9a-f]{64}",
        b"ISOLATED_SELF_DIGEST:" + b"0" * 64,
        value,
    )
    if count != 1:
        raise EvidenceError("isolated runtime checker self-digest marker differs")
    return _sha256_bytes(normalized)


def _decode_canonical_json_bytes(value: bytes, label: str) -> dict[str, Any]:
    try:
        text = value.decode("ascii")
        result = json.loads(
            text,
            object_pairs_hook=_object_without_duplicates,
            parse_constant=lambda item: (_ for _ in ()).throw(
                EvidenceError(
                    "{0} contains non-finite JSON: {1}".format(label, item)
                )
            ),
        )
    except EvidenceError:
        raise
    except (UnicodeError, TypeError, ValueError) as error:
        raise EvidenceError("cannot parse {0}: {1}".format(label, error)) from error
    if type(result) is not dict or _canonical_bytes(result) != value:
        raise EvidenceError("{0} is not one canonical JSON object".format(label))
    return result


def _decode_pretty_canonical_json_bytes(
    value: bytes, label: str
) -> dict[str, Any]:
    try:
        text = value.decode("ascii")
        result = json.loads(
            text,
            object_pairs_hook=_object_without_duplicates,
            parse_constant=lambda item: (_ for _ in ()).throw(
                EvidenceError(
                    "{0} contains non-finite JSON: {1}".format(label, item)
                )
            ),
        )
    except EvidenceError:
        raise
    except (UnicodeError, TypeError, ValueError) as error:
        raise EvidenceError("cannot parse {0}: {1}".format(label, error)) from error
    if type(result) is not dict or _pretty(result).encode("utf-8") != value:
        raise EvidenceError(
            "{0} is not one canonical pretty JSON object".format(label)
        )
    return result


def _run_isolated_semantic_worker(
    action: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    if action not in ("config", "link", "phase2") or type(payload) is not dict:
        raise EvidenceError("isolated semantic worker request differs")
    checker_path = Path(
        os.path.abspath(_run_isolated_semantic_worker.__code__.co_filename)
    )
    authority_directory = checker_path.parent
    with contextlib.ExitStack() as stack:
        _checker_bound, checker_fd = stack.enter_context(
            _bound_evidence_file(checker_path, "isolated runtime checker source")
        )
        checker_bytes, checker_stat_identity = _read_bound_descriptor_bytes(
            checker_fd, 2 << 20, "isolated runtime checker source"
        )
        checker_identity = _semantic_authority_identity(checker_bytes)
        if _normalized_runtime_checker_sha256(checker_bytes) != ISOLATED_SELF_DIGEST:
            raise EvidenceError("isolated runtime checker normalized SHA-256 differs")
        authority_fds = {}
        actual_authorities = {}
        for key in sorted(_SEMANTIC_AUTHORITY_FILENAMES):
            path = authority_directory / _SEMANTIC_AUTHORITY_FILENAMES[key]
            _bound, descriptor = stack.enter_context(
                _bound_evidence_file(
                    path, "isolated semantic authority {0}".format(key)
                )
            )
            source, _identity = _read_bound_descriptor_bytes(
                descriptor,
                EXPECTED_REPOSITORY_SEMANTIC_AUTHORITY_IDENTITIES[key]["size"],
                "isolated semantic authority {0}".format(key),
            )
            actual = _semantic_authority_identity(source)
            if actual != EXPECTED_REPOSITORY_SEMANTIC_AUTHORITY_IDENTITIES[key]:
                raise EvidenceError(
                    "isolated semantic authority byte identity differs: {0}".format(
                        key
                    )
                )
            authority_fds[key] = descriptor
            actual_authorities[key] = actual
        request = {
            "action": action,
            "authorities": actual_authorities,
            "checker": checker_identity,
            "claims": {
                "credit_eligible": False,
                "gate_pass": False,
                "runtime_proven": False,
                "tracker_credit": False,
            },
            "payload": payload,
            "schema_version": 1,
        }
        request_bytes = _canonical_bytes(request)
        if not request_bytes or len(request_bytes) > MAX_ISOLATED_SEMANTIC_REQUEST_SIZE:
            raise EvidenceError("isolated semantic worker request is too large")
        arguments = [
            sys.executable,
            "-I",
            "/proc/self/fd/{0}".format(checker_fd),
            "--isolated-semantic-worker",
            "--checker-fd={0}".format(checker_fd),
        ]
        arguments.extend(
            "--semantic-authority-fd={0}:{1}".format(key, authority_fds[key])
            for key in sorted(authority_fds)
        )
        environment = {
            "LANG": "C",
            "LC_ALL": "C",
            "PATH": "/usr/bin:/bin",
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONHASHSEED": "0",
            "TZ": "UTC",
        }
        try:
            process = subprocess.run(
                arguments,
                input=request_bytes,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
                timeout=60,
                env=environment,
                pass_fds=tuple(sorted([checker_fd] + list(authority_fds.values()))),
            )
        except subprocess.TimeoutExpired as error:
            raise EvidenceError("isolated semantic worker timed out") from error
        if _stat_identity(os.fstat(checker_fd)) != checker_stat_identity:
            raise EvidenceError("isolated runtime checker source changed during worker")
        for key, descriptor in authority_fds.items():
            source, _identity = _read_bound_descriptor_bytes(
                descriptor,
                EXPECTED_REPOSITORY_SEMANTIC_AUTHORITY_IDENTITIES[key]["size"],
                "isolated semantic authority {0}".format(key),
            )
            if _semantic_authority_identity(source) != actual_authorities[key]:
                raise EvidenceError(
                    "isolated semantic authority changed during worker: {0}".format(
                        key
                    )
                )
    if type(process.returncode) is not int or process.returncode != 0:
        diagnostic = process.stderr[:1024].decode("utf-8", "replace").strip()
        raise EvidenceError(
            "isolated semantic worker failed: {0}".format(diagnostic)
        )
    if process.stderr:
        raise EvidenceError("isolated semantic worker emitted unexpected stderr")
    if (
        not process.stdout
        or len(process.stdout) > MAX_ISOLATED_SEMANTIC_RESULT_SIZE
    ):
        raise EvidenceError("isolated semantic worker output size differs")
    result = _decode_canonical_json_bytes(
        process.stdout, "isolated semantic worker result"
    )
    expected_claims = {
        "credit_eligible": False,
        "gate_pass": False,
        "runtime_proven": False,
        "tracker_credit": False,
    }
    if (
        set(result)
        != {
            "action",
            "authorities",
            "checker",
            "claims",
            "payload",
            "request_sha256",
            "schema_version",
        }
        or type(result["schema_version"]) is not int
        or result["schema_version"] != 1
        or result["action"] != action
        or not _exact_typed_equal(result["authorities"], actual_authorities)
        or not _exact_typed_equal(result["checker"], checker_identity)
        or not _exact_typed_equal(result["claims"], expected_claims)
        or result["request_sha256"] != _sha256_bytes(request_bytes)
        or type(result["payload"]) is not dict
    ):
        raise EvidenceError("isolated semantic worker receipt differs")
    return result["payload"]


def _read_regular_evidence_bytes(path: Path, label: str) -> bytes:
    try:
        before = path.lstat()
    except OSError as error:
        raise EvidenceError("cannot inspect {0}: {1}".format(label, error)) from error
    if stat.S_ISLNK(before.st_mode) or not stat.S_ISREG(before.st_mode):
        raise EvidenceError("{0} must be a regular non-symlink file".format(label))
    if stat.S_IMODE(before.st_mode) != 0o644:
        raise EvidenceError("{0} mode must be 0644".format(label))
    flags = os.O_RDONLY
    if hasattr(os, "O_BINARY"):
        flags |= os.O_BINARY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(str(path), flags)
        try:
            opened = os.fstat(descriptor)
            identity = _stat_identity(opened)
            before_identity = _stat_identity(before)
            if identity != before_identity:
                raise EvidenceError("{0} changed while it was opened".format(label))
            chunks: list[bytes] = []
            while True:
                chunk = os.read(descriptor, 1024 * 1024)
                if not chunk:
                    break
                chunks.append(chunk)
            after = os.fstat(descriptor)
            after_identity = _stat_identity(after)
            if after_identity != identity:
                raise EvidenceError("{0} changed while it was read".format(label))
        finally:
            os.close(descriptor)
    except EvidenceError:
        raise
    except OSError as error:
        raise EvidenceError("cannot read {0}: {1}".format(label, error)) from error
    value = b"".join(chunks)
    if len(value) != before.st_size:
        raise EvidenceError("{0} size changed while it was read".format(label))
    try:
        final = path.lstat()
    except OSError as error:
        raise EvidenceError("cannot recheck {0}: {1}".format(label, error)) from error
    final_identity = _stat_identity(final)
    if final_identity != before_identity:
        raise EvidenceError("{0} changed before validation completed".format(label))
    return value


def _validate_runtime_pr_workflow(text: str) -> None:
    expected = (
        "name: Native Rust host modules exact Rocky runtime PR capture\n"
        "\n"
        "on:\n"
        "  pull_request:\n"
        "    branches: [development]\n"
        "    paths:\n"
        "      - .gitmodules\n"
        "      - .github/workflows/native-rust-host-modules-exact-*.yml\n"
        "      - host-kernel/contracts/*.json\n"
        "      - host-kernel/kbuild/**\n"
        "      - host-kernel/native-rust/**\n"
        "      - host-kernel/reference/**\n"
        "      - host-kernel/rocky/**\n"
        "      - ihk\n"
        "      - scripts/**\n"
        "\n"
        "permissions:\n"
        "  contents: read\n"
        "\n"
        "jobs:\n"
        "  exact-runtime:\n"
        "    name: Capture exact lifecycle in QEMU (credit forbidden)\n"
        "    if: >-\n"
        "      ${{ github.event.pull_request.head.repo.full_name == github.repository }}\n"
        "    uses: ./.github/workflows/native-rust-host-modules-exact-runtime.yml\n"
        "    with:\n"
        "      validation_sha: ${{ github.event.pull_request.head.sha }}\n"
    )
    if text != expected:
        raise EvidenceError("runtime PR wrapper trust/exact-head boundary differs")


def _validate_runtime_modinfo_boundary(text: str) -> None:
    verify_header = (
        "      - name: Verify immutable build inputs and native module link contracts\n"
    )
    next_header = "      - name: Assemble a deterministic lifecycle and mcd0 initramfs\n"
    capture_header = "      - name: Create a credit-forbidden technical capture\n"
    upload_header = "      - name: Upload technical capture or first-failure diagnostics\n"
    if any(
        text.count(header) != 1
        for header in (verify_header, next_header, capture_header, upload_header)
    ):
        raise EvidenceError("runtime workflow modinfo step scope differs")
    start = text.index(verify_header) + len(verify_header)
    end = text.index(next_header, start)
    verify_step = text[start:end]
    capture_start = text.index(capture_header) + len(capture_header)
    capture_end = text.index(upload_header, capture_start)
    capture_step = text[capture_start:capture_end]

    binding = (
        "          assert_modinfo_binding() {\n"
        "            test -L \"$modinfo_path\" &&\n"
        "              test \"$(/usr/bin/readlink -- \"$modinfo_path\")\" = ../bin/kmod &&\n"
        "              test ! -L \"$modinfo_target\" &&\n"
        "              test \"$modinfo_path\" -ef \"$modinfo_exec\" &&\n"
        "              test \"$modinfo_target\" -ef \"$modinfo_exec\" &&\n"
        "              test \"$(/usr/bin/sha256sum -- \"$modinfo_exec\")\" = \\\n"
        "              \"$expected_modinfo_sha256  $modinfo_exec\" &&\n"
        "              test \"$(/usr/bin/rpm -q --qf '%{NEVRA}\\n' kmod)\" = \\\n"
        "              \"$expected_modinfo_nevra\" &&\n"
        "              test \"$(/usr/bin/rpm -qf --qf '%{NAME}\\n' \"$modinfo_path\")\" = kmod &&\n"
        "              test \"$(/usr/bin/rpm -qf --qf '%{NAME}\\n' \"$modinfo_target\")\" = kmod\n"
        "          }\n"
    )
    verify_binding = binding + (
        "          run_modinfo() (\n"
        "            assert_modinfo_binding &&\n"
        "              exec -a modinfo \"$modinfo_exec\" \"$@\"\n"
        "          )\n"
    )
    if verify_step.count(verify_binding) != 1 or capture_step.count(binding) != 1:
        raise EvidenceError("runtime workflow modinfo retained-descriptor boundary differs")

    common_ordered = (
        "          expected_modinfo_nevra=kmod-31-13.el10.x86_64\n",
        "          expected_modinfo_sha256=7e91f52ed2cd5e2c4f82de4bb07bbaa7179cd5c053b7afcf2fd231056681ed55\n",
        "          modinfo_path=\"$(command -v modinfo)\"\n",
        "          modinfo_target=/usr/bin/kmod\n",
        "          test \"$modinfo_path\" = /usr/sbin/modinfo\n",
        "          test -x /usr/sbin/modinfo\n",
        "          test -L /usr/sbin/modinfo\n",
        "          test \"$(/usr/bin/readlink -- /usr/sbin/modinfo)\" = ../bin/kmod\n",
        "          test -x \"$modinfo_target\"\n",
        "          test ! -L \"$modinfo_target\"\n",
        "          exec {modinfo_fd}<\"$modinfo_target\"\n",
        "          modinfo_exec=\"/proc/self/fd/$modinfo_fd\"\n",
        "          test -r \"$modinfo_exec\"\n",
    )
    verify_ordered = common_ordered + (
        verify_binding,
        "          test -x /usr/bin/nm\n",
        "          test \"$(run_modinfo -F name \"$BUILD_EVIDENCE/ihk.ko\")\" = ihk\n",
        "          test \"$(run_modinfo -F name \"$BUILD_EVIDENCE/ihk-smp-x86_64.ko\")\" = ihk_smp_x86_64\n",
        "          test \"$(run_modinfo -F name \"$BUILD_EVIDENCE/mcctrl.ko\")\" = mcctrl\n",
        "            /usr/bin/python3 -E -s scripts/ihk_native_lifecycle_check.py \\\n",
        "            /usr/bin/python3 -E -s scripts/ihk_smp_native_lifecycle_check.py \\\n",
        "            /usr/bin/python3 -E -s scripts/mcctrl_native_lifecycle_check.py \\\n",
        "          exec {modinfo_fd}<&-\n",
    )
    positions = []
    for fragment in verify_ordered:
        if verify_step.count(fragment) != 1:
            raise EvidenceError("runtime workflow modinfo binding fragment differs")
        positions.append(verify_step.index(fragment))
    if positions != sorted(positions):
        raise EvidenceError("runtime workflow modinfo validation order differs")
    expected_fd_arguments = (
        '            --repo "$GITHUB_WORKSPACE" --module "$BUILD_EVIDENCE/ihk.ko" \\\n'
        '            --modinfo-fd "$modinfo_fd"\n',
        '            --repo "$GITHUB_WORKSPACE" --module "$BUILD_EVIDENCE/ihk-smp-x86_64.ko" \\\n'
        '            --modinfo-fd "$modinfo_fd"\n',
        '            --repo "$GITHUB_WORKSPACE" --module "$BUILD_EVIDENCE/mcctrl.ko" \\\n'
        '            --modinfo-fd "$modinfo_fd"\n',
    )
    if any(verify_step.count(fragment) != 1 for fragment in expected_fd_arguments):
        raise EvidenceError("runtime workflow lifecycle checker descriptor scope differs")

    binding_calls = [
        match.start()
        for match in re.finditer(r"(?m)^          assert_modinfo_binding$", verify_step)
    ]
    if len(binding_calls) != 5:
        raise EvidenceError("runtime workflow modinfo recheck scope differs")
    first_execution = verify_step.index("          test \"$(run_modinfo -F name")
    ihk_lifecycle = verify_step.index(
        "            /usr/bin/python3 -E -s scripts/ihk_native_lifecycle_check.py"
    )
    smp_lifecycle = verify_step.index(
        "            /usr/bin/python3 -E -s scripts/ihk_smp_native_lifecycle_check.py"
    )
    mcctrl_lifecycle = verify_step.index(
        "            /usr/bin/python3 -E -s scripts/mcctrl_native_lifecycle_check.py"
    )
    close_descriptor = verify_step.index("          exec {modinfo_fd}<&-")
    if not (
        binding_calls[0] < first_execution < binding_calls[1] < ihk_lifecycle
        < binding_calls[2] < smp_lifecycle < binding_calls[3]
        < mcctrl_lifecycle < binding_calls[4] < close_descriptor
    ):
        raise EvidenceError("runtime workflow modinfo recheck order differs")

    capture_ordered = common_ordered + (
        binding,
        "            --capture \\\n",
        "            --check-runtime-evidence \\\n",
        "          exec {modinfo_fd}<&-\n",
    )
    capture_positions = []
    for fragment in capture_ordered:
        if capture_step.count(fragment) != 1:
            raise EvidenceError("runtime workflow capture modinfo binding fragment differs")
        capture_positions.append(capture_step.index(fragment))
    if capture_positions != sorted(capture_positions):
        raise EvidenceError("runtime workflow capture modinfo validation order differs")
    if capture_step.count('            --modinfo-fd "$modinfo_fd" \\\n') != 2:
        raise EvidenceError("runtime workflow evidence checker descriptor scope differs")
    if capture_step.count(
        '            --modinfo-sha256 "$expected_modinfo_sha256" \\\n'
    ) != 2:
        raise EvidenceError("runtime workflow modinfo digest scope differs")
    expected_tool_arguments = (
        '            --modinfo-fd "$modinfo_fd" \\\n'
        '            --modinfo-sha256 "$expected_modinfo_sha256" \\\n'
    )
    if capture_step.count(expected_tool_arguments) != 2:
        raise EvidenceError("runtime workflow modinfo fd/digest binding differs")
    capture_binding_calls = [
        match.start()
        for match in re.finditer(
            r"(?m)^          assert_modinfo_binding$", capture_step
        )
    ]
    capture_call = capture_step.index("            --capture \\\n")
    replay_call = capture_step.index("            --check-runtime-evidence \\\n")
    capture_close = capture_step.index("          exec {modinfo_fd}<&-")
    if not (
        len(capture_binding_calls) == 4
        and capture_binding_calls[0] < capture_call < capture_binding_calls[1]
        < capture_binding_calls[2] < replay_call < capture_binding_calls[3]
        < capture_close
    ):
        raise EvidenceError("runtime workflow capture modinfo recheck order differs")
    for step in (verify_step, capture_step):
        if '          test ! -L /usr/sbin/modinfo\n' in step:
            raise EvidenceError("runtime workflow rejects the exact packaged modinfo alias")
        if re.search(r'(?m)^\s*\"\$modinfo_path\"(?:\s|$)', step):
            raise EvidenceError("runtime workflow executes modinfo through a mutable alias")


def _validate_runtime_nm_boundary(text: str) -> None:
    capture_header = "      - name: Create a credit-forbidden technical capture\n"
    upload_header = "      - name: Upload technical capture or first-failure diagnostics\n"
    if text.count(capture_header) != 1 or text.count(upload_header) != 1:
        raise EvidenceError("runtime workflow nm step scope differs")
    start = text.index(capture_header) + len(capture_header)
    end = text.index(upload_header, start)
    step = text[start:end]
    verify_package = (
        "          verify_nm_package() {\n"
        "            local verification\n"
        "            verification=\"$(/usr/bin/rpm -V binutils)\" || return 1\n"
        "            test -z \"$verification\"\n"
        "          }\n"
    )
    binding = (
        "          assert_nm_binding() {\n"
        "            test ! -L \"$nm_path\" &&\n"
        "              test \"$nm_path\" -ef \"$nm_exec\" &&\n"
        "              test \"$(/usr/bin/sha256sum -- \"$nm_exec\")\" = \\\n"
        "              \"$expected_nm_sha256  $nm_exec\" &&\n"
        "              test \"$(/usr/bin/rpm -q --qf '%{NEVRA}\\n' binutils)\" = \\\n"
        "              \"$expected_nm_nevra\" &&\n"
        "              test \"$(/usr/bin/rpm -qf --qf '%{NAME}\\n' \"$nm_path\")\" = binutils &&\n"
        "              verify_nm_package\n"
        "          }\n"
    )
    ordered = (
        "          expected_nm_nevra=binutils-2.41-63.el10.x86_64\n",
        "          expected_nm_digest_algorithm=\"$(/usr/bin/rpm -q --qf '%{FILEDIGESTALGO}\\n' binutils)\"\n",
        "          test \"$expected_nm_digest_algorithm\" = 8\n",
        "          nm_path=/usr/bin/nm\n",
        "          test -x \"$nm_path\"\n",
        "          test ! -L \"$nm_path\"\n",
        "          test \"$(/usr/bin/rpm -q --qf '%{NEVRA}\\n' binutils)\" = \\\n"
        "            \"$expected_nm_nevra\"\n",
        "          test \"$(/usr/bin/rpm -qf --qf '%{NAME}\\n' \"$nm_path\")\" = binutils\n",
        "          expected_nm_inventory=\"$(\n",
        "            /usr/bin/rpm -q --qf '[%{FILENAMES}\\t%{FILEDIGESTS}\\n]' binutils\n",
        "          )\"\n",
        '          test "${#expected_nm_inventory}" -gt 0\n',
        '          test "${#expected_nm_inventory}" -le 1048576\n',
        "          expected_nm_sha256=\n",
        "          expected_nm_rows=0\n",
        "          while IFS=$'\\t' read -r rpm_filename rpm_digest; do\n",
        "            if test \"$rpm_filename\" = \"$nm_path\"; then\n",
        "              expected_nm_rows=$((expected_nm_rows + 1))\n",
        "              expected_nm_sha256=\"$rpm_digest\"\n",
        "            fi\n",
        '          done <<< "$expected_nm_inventory"\n',
        "          test \"$expected_nm_rows\" -eq 1\n",
        "          [[ \"$expected_nm_sha256\" =~ ^[0-9a-f]{64}$ ]]\n",
        verify_package,
        "          verify_nm_package\n",
        "          exec {nm_fd}<\"$nm_path\"\n",
        "          nm_exec=\"/proc/self/fd/$nm_fd\"\n",
        "          test -r \"$nm_exec\"\n",
        "          test \"$(/usr/bin/sha256sum -- \"$nm_exec\")\" = \\\n"
        "            \"$expected_nm_sha256  $nm_exec\"\n",
        binding,
        '            --nm-fd "$nm_fd" \\\n',
        '            --nm-sha256 "$expected_nm_sha256" \\\n',
        "            --capture \\\n",
        "            --check-runtime-evidence \\\n",
        "          exec {nm_fd}<&-\n",
        "          exec {modinfo_fd}<&-\n",
    )
    positions = []
    for fragment in ordered:
        expected_count = (
            2
            if fragment
            in (
                '            --nm-fd "$nm_fd" \\\n',
                '            --nm-sha256 "$expected_nm_sha256" \\\n',
                "          verify_nm_package\n",
            )
            else 1
        )
        if step.count(fragment) != expected_count:
            raise EvidenceError("runtime workflow nm binding fragment differs")
        positions.append(step.index(fragment))
    if positions != sorted(positions):
        raise EvidenceError("runtime workflow nm validation order differs")
    binding_calls = [
        match.start()
        for match in re.finditer(r"(?m)^          assert_nm_binding$", step)
    ]
    capture_call = step.index("            --capture \\\n")
    replay_call = step.index("            --check-runtime-evidence \\\n")
    close_nm = step.index("          exec {nm_fd}<&-")
    close_modinfo = step.index("          exec {modinfo_fd}<&-")
    if not (
        len(binding_calls) == 4
        and binding_calls[0] < capture_call < binding_calls[1]
        < binding_calls[2] < replay_call < binding_calls[3]
        < close_nm < close_modinfo
    ):
        raise EvidenceError("runtime workflow nm recheck order differs")


def _validate_runtime_workflow_provenance_boundary(text: str) -> None:
    verify_header = (
        "      - name: Verify immutable build inputs and native module link contracts\n"
    )
    assemble_header = "      - name: Assemble a deterministic lifecycle and mcd0 initramfs\n"
    capture_header = "      - name: Create a credit-forbidden technical capture\n"
    upload_header = "      - name: Upload technical capture or first-failure diagnostics\n"
    if any(text.count(item) != 1 for item in (
        verify_header,
        assemble_header,
        capture_header,
        upload_header,
    )):
        raise EvidenceError("runtime workflow provenance step scope differs")
    verify = text[
        text.index(verify_header) + len(verify_header) : text.index(assemble_header)
    ]
    capture = text[
        text.index(capture_header) + len(capture_header) : text.index(upload_header)
    ]
    exact_env = (
        "          CALLER_WORKFLOW_REF: ${{ github.workflow_ref }}\n",
        "          CALLER_WORKFLOW_SHA: ${{ github.workflow_sha }}\n",
        "          DEFINING_WORKFLOW_FILE_PATH: ${{ job.workflow_file_path }}\n",
        "          DEFINING_WORKFLOW_REF: ${{ job.workflow_ref }}\n",
        "          DEFINING_WORKFLOW_REPOSITORY: ${{ job.workflow_repository }}\n",
        "          DEFINING_WORKFLOW_SHA: ${{ job.workflow_sha }}\n",
    )
    for fragment in exact_env:
        if verify.count(fragment) != 1 or capture.count(fragment) != 1:
            raise EvidenceError("runtime workflow provenance context env differs")

    verify_fragments = (
        '          test "$GITHUB_SHA" = "$CALLER_WORKFLOW_SHA"\n',
        '          test "$CALLER_WORKFLOW_SHA" = "$DEFINING_WORKFLOW_SHA"\n',
        "          case \"$GITHUB_EVENT_NAME\" in\n",
        "            pull_request)\n",
        '              [[ "$GITHUB_REF" =~ ^refs/pull/[1-9][0-9]*/merge$ ]]\n',
        "            workflow_dispatch)\n",
        '              test "$EXPECTED_HEAD_SHA" = "$CALLER_WORKFLOW_SHA"\n',
        '          test "$CALLER_WORKFLOW_REF" = \\\n',
        '            "$GITHUB_REPOSITORY/$caller_workflow_path@$GITHUB_REF"\n',
        '          test "$DEFINING_WORKFLOW_REF" = \\\n',
        '            "$GITHUB_REPOSITORY/$runtime_workflow_path@$GITHUB_REF"\n',
        "          workflow_git() {\n",
        '          if ! workflow_git cat-file -e \\\n',
        '            "$DEFINING_WORKFLOW_SHA^{commit}" 2>/dev/null; then\n',
        '            workflow_git fetch --no-tags --depth=1 origin "$GITHUB_REF"\n',
        '            test "$(workflow_git rev-parse FETCH_HEAD)" = "$DEFINING_WORKFLOW_SHA"\n',
        '          candidate_caller_workflow_blob="$(workflow_git rev-parse --verify \\\n',
        '          executed_caller_workflow_blob="$(workflow_git rev-parse --verify \\\n',
        '          candidate_job_workflow_blob="$(workflow_git rev-parse --verify \\\n',
        '          executed_job_workflow_blob="$(workflow_git rev-parse --verify \\\n',
        '          test "$candidate_caller_workflow_blob" = \\\n',
        '            "$executed_caller_workflow_blob"\n',
        '          test "$candidate_job_workflow_blob" = "$executed_job_workflow_blob"\n',
        '          workflow_git cat-file blob "$executed_caller_workflow_blob" \\\n',
        '            > "$RUNTIME_EVIDENCE/executed-caller-workflow.yml"\n',
        '          workflow_git cat-file blob "$executed_job_workflow_blob" \\\n',
        '            > "$RUNTIME_EVIDENCE/executed-runtime-workflow.yml"\n',
        '          /usr/bin/cmp -- "$GITHUB_WORKSPACE/$caller_workflow_path" \\\n',
        '          /usr/bin/cmp -- "$GITHUB_WORKSPACE/$runtime_workflow_path" \\\n',
        '          test "$caller_workflow_size" -le 1048576\n',
        '          test "$job_workflow_size" -le 1048576\n',
        '            "schema": "mckernel-native-rust-runtime-workflow-provenance-v1",\n',
        '          data = (json.dumps(value, indent=2, sort_keys=True) + "\\n").encode("utf-8")\n',
        '          chmod 0644 \\\n',
        '            "$RUNTIME_EVIDENCE/runtime-workflow-provenance.json"\n',
        '          (cd "$BUILD_EVIDENCE" && sha256sum --check --strict SHA256SUMS)\n',
    )
    positions = []
    for fragment in verify_fragments:
        if verify.count(fragment) != 1:
            raise EvidenceError("runtime workflow provenance construction differs")
        positions.append(verify.index(fragment))
    if positions != sorted(positions):
        raise EvidenceError("runtime workflow provenance construction order differs")

    capture_fragments = (
        "          case \"$GITHUB_EVENT_NAME\" in\n",
        '          github_workflow_blob_sha1="$(/usr/bin/git -c \\\n',
        '          job_workflow_blob_sha1="$(/usr/bin/git -c \\\n',
        '          [[ "$github_workflow_blob_sha1" =~ ^[0-9a-f]{40}$ ]]\n',
        '          [[ "$job_workflow_blob_sha1" =~ ^[0-9a-f]{40}$ ]]\n',
    )
    positions = []
    for fragment in capture_fragments:
        if capture.count(fragment) != 1:
            raise EvidenceError("runtime workflow provenance replay differs")
        positions.append(capture.index(fragment))
    if positions != sorted(positions):
        raise EvidenceError("runtime workflow provenance replay order differs")
    cli_fragments = (
        '            --github-event-name "$GITHUB_EVENT_NAME" \\\n',
        '            --github-ref "$GITHUB_REF" \\\n',
        '            --github-sha "$GITHUB_SHA" \\\n',
        '            --github-workflow-ref "$CALLER_WORKFLOW_REF" \\\n',
        '            --github-workflow-sha "$CALLER_WORKFLOW_SHA" \\\n',
        '            --github-workflow-blob-sha1 "$github_workflow_blob_sha1" \\\n',
        '            --job-workflow-ref "$DEFINING_WORKFLOW_REF" \\\n',
        '            --job-workflow-sha "$DEFINING_WORKFLOW_SHA" \\\n',
        '            --job-workflow-repository "$DEFINING_WORKFLOW_REPOSITORY" \\\n',
        '            --job-workflow-file-path "$DEFINING_WORKFLOW_FILE_PATH" \\\n',
        '            --job-workflow-blob-sha1 "$job_workflow_blob_sha1" \\\n',
        "            --workflow-provenance \\\n",
        '              "$RUNTIME_EVIDENCE/runtime-workflow-provenance.json" \\\n',
    )
    for fragment in cli_fragments:
        if capture.count(fragment) != 2:
            raise EvidenceError("runtime workflow provenance checker interface differs")
    if capture.count('            --capture \\\n') != 1 or capture.count(
        '            --check-runtime-evidence \\\n'
    ) != 1:
        raise EvidenceError("runtime workflow provenance capture/replay scope differs")


def validate_contract(repo: Path, contract_relative: Path = DEFAULT_CONTRACT) -> dict[str, Any]:
    repo = repo.resolve()
    contract_path = _repo_file(repo, contract_relative.as_posix(), "runtime contract")
    contract = _load_json(contract_path)
    _require_keys(
        contract,
        {
            "artifact_contract",
            "build_scope",
            "gate",
            "modules",
            "protocol",
            "repository_inputs",
            "repository_helper_identities",
            "repository_semantic_authority_identities",
            "reproducible_build_identity",
            "repository_workflow_identities",
            "runtime",
            "runtime_verifier_scope",
            "schema_version",
            "selected_kernel",
        },
        "contract",
    )
    if type(contract["schema_version"]) is not int or contract["schema_version"] != 1:
        raise EvidenceError("unsupported runtime contract schema")

    expected_build_scope = {
        "builds_full_module_tree": False,
        "credit_eligible": False,
        "kernel_targets": BUILD_KERNEL_TARGETS,
        "module_target_interface": (
            "Linux 6.12 in-tree %.ko single targets in one modpost invocation"
        ),
        "module_targets": BUILD_MODULE_TARGETS,
        "policy": (
            "Build the boot kernel and only the three staged McKernel native Rust modules. "
            "This bounded technical capture neither validates every configured distro module "
            "nor awards RK-002, native-module, migration, or tracker credit."
        ),
        "tracker_credit": False,
    }
    if not _exact_typed_equal(contract["build_scope"], expected_build_scope):
        raise EvidenceError("runtime contract weakens the exact build scope")

    expected_gate = {
        "capture_can_claim_pass": False,
        "credit_eligible": False,
        "gate_ids": ["IHK-001", "SMP-001", "MCC-001"],
        "independent_evidence_review_required": True,
        "policy": (
            "The workflow may create an exact technical capture, but cannot claim PASS or "
            "credit. Exact-run success and a separately committed independent artifact review "
            "are both required before any gate decision."
        ),
    }
    if not _exact_typed_equal(contract["gate"], expected_gate):
        raise EvidenceError("runtime contract weakens the credit/review boundary")

    expected_runtime = {
        "architecture": "x86_64",
        "boot_medium": "deterministic initramfs",
        "container_image": (
            "rockylinux/rockylinux:10.2@sha256:"
            "e372170ca8630f0f03e9b70fdd0bf4a3ce3426b0de7cdba615f06337389de176"
        ),
        "distribution": "Rocky Linux",
        "os_release_sha256": EXPECTED_ROCKY_OS_RELEASE_SHA256,
        "qemu_accelerator": "tcg",
        "required_kernel_config": EXPECTED_RUNTIME_REQUIRED_CONFIG,
        "release": "10.2",
    }
    if not _exact_typed_equal(contract["runtime"], expected_runtime):
        raise EvidenceError("runtime identity differs from exact Rocky 10.2 x86_64 TCG")
    if not _exact_typed_equal(contract["runtime_verifier_scope"], {
        "initramfs_cpio_replay": False,
        "policy": (
            "Offline validation binds the exact helper sources, top-level helper binaries, "
            "initramfs bytes, and checksum record but does not independently rebuild the "
            "helpers or replay cpio membership and embedded module/init/helper bytes. "
            "Build-to-guest correlation therefore depends on the sealed exact workflow and "
            "outer same-run artifact provenance; this residual cannot support gate, runtime, "
            "durability, or credit claims."
        ),
    }):
        raise EvidenceError("runtime verifier limitation scope differs")

    expected_reproducible_identity = {
        "authority": {
            "json_pointer": "/repository_snapshot/primary_metadata/timestamp",
            "kbuild_build_host_basis": (
                "selected Rocky 10.2 x86_64 build platform identity"
            ),
            "kbuild_build_user_basis": "repository project identity mckernel",
            "kbuild_build_version_basis": (
                "fresh exact-build tree canonical first build iteration"
            ),
            "source_date_epoch": EXPECTED_SOURCE_DATE_EPOCH,
            "source_lock_id": (
                "rocky-10.2-x86_64-kernel-6.12.0-211.44.1.el10_2-source-v1"
            ),
        },
        "environment": EXPECTED_REPRODUCIBLE_BUILD_ENVIRONMENT,
        "policy": (
            "The fixed Kbuild identity is derived from the locked source-repository "
            "primary-metadata timestamp and applies to every exact-build phase, including "
            "reusable-workflow builds. This removes run-specific builder and wall-clock "
            "bytes but does not prove cross-run reproducibility, runtime behavior, "
            "durability, or gate credit."
        ),
    }
    if not _exact_typed_equal(
        contract["reproducible_build_identity"], expected_reproducible_identity
    ):
        raise EvidenceError("reproducible build identity differs")

    selected = contract["selected_kernel"]
    if selected != {
        "archive_sha256": "4a174d47b8874a2139efcd1ac1ab2d6b80ae7a0ca62f0ae4596fd20cf62a3533",
        "kernel_release": EXPECTED_KERNEL_RELEASE,
        "localversion": EXPECTED_KERNEL_LOCALVERSION,
        "nvr": "kernel-6.12.0-211.44.1.el10_2",
        "source_lock_id": "rocky-10.2-x86_64-kernel-6.12.0-211.44.1.el10_2-source-v1",
    }:
        raise EvidenceError("selected kernel identity differs")
    source_lock = _load_json(
        _repo_file(repo, contract["repository_inputs"]["source_lock"], "source lock")
    )
    source_timestamp = (
        source_lock.get("repository_snapshot", {})
        .get("primary_metadata", {})
        .get("timestamp")
    )
    authority = contract["reproducible_build_identity"]["authority"]
    if (
        type(source_timestamp) is not int
        or source_timestamp != EXPECTED_SOURCE_DATE_EPOCH
        or authority["source_date_epoch"] != source_timestamp
        or authority["source_lock_id"] != source_lock.get("lock_id")
    ):
        raise EvidenceError("reproducible build timestamp authority diverges")
    canonical_timestamp = email.utils.format_datetime(
        datetime.datetime.fromtimestamp(source_timestamp, datetime.timezone.utc)
    )
    if (
        contract["reproducible_build_identity"]["environment"]
        .get("KBUILD_BUILD_TIMESTAMP")
        != canonical_timestamp
    ):
        raise EvidenceError("reproducible Kbuild timestamp is not authority-derived")
    archives = [
        item
        for item in source_lock.get("embedded_objects", [])
        if item.get("role") == "Rocky-derived Linux source archive"
    ]
    if (
        source_lock.get("lock_id") != selected["source_lock_id"]
        or source_lock.get("source_rpm", {}).get("nvr") != selected["nvr"]
        or len(archives) != 1
        or archives[0].get("sha256") != selected["archive_sha256"]
    ):
        raise EvidenceError("runtime contract and Rocky source lock diverge")

    expected_modules = [
        {
            "defined_provider_symbols": list(PROVIDER_DEFINED_SYMBOLS),
            "depends": [],
            "file": "ihk.ko",
            "gpl_exported_provider_symbols": list(PROVIDER_DEFINED_SYMBOLS),
            "import_namespace": None,
            "name": "ihk",
            "provider_export_namespace": PROVIDER_EXPORT_NAMESPACE,
        },
        {
            "depends": ["ihk"],
            "file": "ihk-smp-x86_64.ko",
            "import_namespace": PROVIDER_EXPORT_NAMESPACE,
            "name": "ihk_smp_x86_64",
            "undefined_provider_symbols": list(PROVIDER_SMP_IMPORT_SYMBOLS),
        },
        {
            "depends": ["ihk"],
            "file": "mcctrl.ko",
            "import_namespace": PROVIDER_EXPORT_NAMESPACE,
            "name": "mcctrl",
            "undefined_provider_symbols": [PROVIDER_ANCHOR_SYMBOL],
        },
    ]
    if not _exact_typed_equal(contract["modules"], expected_modules):
        raise EvidenceError("runtime module graph differs")
    if not _exact_typed_equal(contract["protocol"], {
        "load_order": ["ihk", "ihk_smp_x86_64", "mcctrl"],
        "mcd0": {
            "compat_abi": "i386",
            "compat_ioctl_expected_errno": "EINVAL",
            "credit_eligible": False,
            "device_node_identity_policy": "st_rdev-equals-sysfs-major-minor",
            "device_path": "/dev/mcd0",
            "diagnostic_segments": 2,
            "first_cycle_open_count": MCD0_FIRST_CYCLE_OPEN_COUNT,
            "gate_pass": False,
            "gate_status": "TODO",
            "ioctl_command": "0xdeadbeef",
            "ioctl_return": -22,
            "misc_device_major": 10,
            "misc_device_minor_policy": "dynamic-canonical-decimal",
            "module_owner_unload_expected_diagnostic": (
                "Module ihk_smp_x86_64 is in use"
            ),
            "module_owner_unload_expected_status": 1,
            "native_abi": "x86_64",
            "native_ioctl_expected_errno": "EINVAL",
            "node_removed_after_smp_unload": True,
            "operation_callbacks_reachable": False,
            "os_operations_reachable": False,
            "open_receipt": {
                "duplicate_close_detectable_while_other_references_exist": False,
                "same_generation_token_may_repeat": True,
                "trusted_noncopy_owner_balance_required": True,
            },
            "overlapping_open_count": MCD0_OVERLAPPING_OPEN_COUNT,
            "provider_registry_minor": 0,
            "provider_open_acquire_count_per_trace": (
                MCD0_PROVIDER_OPEN_COUNT_PER_TRACE
            ),
            "provider_open_acquire_diagnostic": PROVIDER_OPEN_ACQUIRE_DIAGNOSTIC,
            "provider_open_release_count_per_trace": (
                MCD0_PROVIDER_OPEN_COUNT_PER_TRACE
            ),
            "provider_open_release_diagnostic": PROVIDER_OPEN_RELEASE_DIAGNOSTIC,
            "reload_cycles": MCD0_RELOAD_CYCLES,
            "reload_open_count": MCD0_RELOAD_OPEN_COUNT,
            "resource_operations_reachable": False,
            "rocky_runtime_validated": False,
            "runtime_behavior_proven": False,
            "sequential_open_count": MCD0_SEQUENTIAL_OPEN_COUNT,
            "sysfs_identity_path": "/sys/class/misc/mcd0/dev",
            "tracker_credit": False,
            "valid_operation_commands": [],
        },
        "provider_lease": {
            "attach_after_ihk_load": True,
            "attach_diagnostic": PROVIDER_LEASE_ATTACH_DIAGNOSTIC,
            "callback_abi": PROVIDER_CALLBACK_ABI,
            "callback_payload_reachable": False,
            "credit_eligible": False,
            "detach_before_smp_unload_completion": True,
            "detach_diagnostic_pattern": (
                "ihk: provider_lease=detach status=vacant minor=0 "
                "generation=[1-9][0-9]* callback_abi=1"
            ),
            "exit_callback_before_detach": True,
            "exit_callback_diagnostic": PROVIDER_CALLBACK_EXIT_DIAGNOSTIC,
            "forbidden_diagnostic_prefixes": list(
                PROVIDER_LEASE_FORBIDDEN_DIAGNOSTICS
            ),
            "gate_status": "TODO",
            "init_callback_before_attach": True,
            "init_callback_diagnostic": PROVIDER_CALLBACK_INIT_DIAGNOSTIC,
            "operation_callbacks_reachable": False,
            "raw_token_logged": False,
            "registry_empty_before_ihk_unload_completion": True,
            "registry_empty_diagnostic": PROVIDER_REGISTRY_EMPTY_DIAGNOSTIC,
            "rocky_runtime_validated": False,
            "runtime_behavior_proven": False,
            "tracker_credit": False,
        },
        "provider_refcount_after_load": 2,
        "provider_refcounts": {
            "after_load": 2,
            "after_mcctrl_unload": 1,
            "after_negative": 2,
            "reload_all_loaded": 2,
            "after_smp_unload": 0,
        },
        "provider_unload_expected_diagnostic": "Module ihk is in use",
        "provider_unload_expected_status": 1,
        "provider_unload_while_referenced_must_fail": True,
        "reload_cycles": MCD0_RELOAD_CYCLES,
        "reload_load_order": ["ihk", "ihk_smp_x86_64", "mcctrl"],
        "reload_unload_order": ["mcctrl", "ihk_smp_x86_64", "ihk"],
        "serial_protocol": PROTOCOL,
        "unload_order": ["mcctrl", "ihk_smp_x86_64", "ihk"],
    }):
        raise EvidenceError("runtime load/refcount/unload protocol differs")

    artifacts = contract["artifact_contract"]
    _require_keys(
        artifacts,
        {
            "build_evidence_files",
            "capture_status",
            "evidence_file_mode",
            "immutable_artifact_digest_required",
            "independent_review_status",
            "runtime_evidence_files",
            "runtime_helper_semantics",
            "size_limits_bytes",
            "tool_digest_authority",
        },
        "artifact_contract",
    )
    if (
        artifacts["capture_status"] != "required-missing"
        or artifacts["evidence_file_mode"] != "0644"
        or artifacts["independent_review_status"] != "required-missing"
        or artifacts["immutable_artifact_digest_required"] is not True
    ):
        raise EvidenceError("repository contract must remain uncaptured and unreviewed")
    if not _exact_typed_equal(artifacts["size_limits_bytes"], {
        "build_evidence_file_max": MAX_BUILD_EVIDENCE_FILE_SIZE,
        "runtime_evidence_file_max": MAX_RUNTIME_EVIDENCE_FILE_SIZE,
        "runtime_helper_file_max": MAX_RUNTIME_HELPER_FILE_SIZE,
        "runtime_text_file_max": MAX_RUNTIME_TEXT_FILE_SIZE,
        "tool_executable_file_max": MAX_TOOL_EXECUTABLE_FILE_SIZE,
    }):
        raise EvidenceError("runtime artifact size limits differ")
    expected_tool_digest_authority = {
        "modinfo": {
            "expected_sha256": EXPECTED_MODINFO_SHA256,
            "package_nevra": "kmod-31-13.el10.x86_64",
            "policy": "fixed-locked-sha256",
        },
        "modules": {
            "policy": "exact-build-SHA256SUMS-record",
        },
        "nm": {
            "file_digest_algorithm": 8,
            "package_nevra": "binutils-2.41-63.el10.x86_64",
            "package_path": NM_EXECUTABLE,
            "policy": "unique-rpm-FILEDIGESTS-row",
        },
    }
    if not _exact_typed_equal(
        artifacts["tool_digest_authority"], expected_tool_digest_authority
    ):
        raise EvidenceError("runtime tool digest authority differs")
    if not _exact_typed_equal(
        artifacts["runtime_helper_semantics"],
        EXPECTED_RUNTIME_HELPER_SEMANTICS,
    ):
        raise EvidenceError("runtime helper executable semantics differ")
    expected_build_evidence = [
        ".ihk-smp-x86_64.ko.cmd",
        ".ihk-smp-x86_64.mod.cmd",
        ".ihk-smp-x86_64.mod.o.cmd",
        ".ihk-smp-x86_64.o.cmd",
        ".ihk.ko.cmd",
        ".ihk.mod.cmd",
        ".ihk.mod.o.cmd",
        ".ihk.o.cmd",
        ".ihk_smp_x86_64.o.cmd",
        ".mcctrl.ko.cmd",
        ".mcctrl.mod.cmd",
        ".mcctrl.mod.o.cmd",
        ".mcctrl.o.cmd",
        "PRECHECK_SHA256SUMS",
        "SHA256SUMS",
        "build-log.exit-code",
        "build.commands",
        "build.environment",
        "build.exit-code",
        "build.log",
        "build.phase",
        "built-module-artifacts.txt",
        "bzImage",
        "commit.sha",
        "executed-build-workflow.yml",
        "ihk-smp-x86_64.ko",
        "ihk-smp-x86_64.ko.modinfo",
        "ihk-smp-x86_64.ko.modinfo-section",
        "ihk-smp-x86_64.ko.nm",
        "ihk-smp-x86_64.ko.readelf",
        "ihk-smp-x86_64.mod",
        "ihk.ko",
        "ihk.ko.modinfo",
        "ihk.ko.modinfo-section",
        "ihk.ko.nm",
        "ihk.ko.readelf",
        "ihk.mod",
        "kbuild-link-closure.json",
        "kconfig-solver-matrix.json",
        "kernel.release",
        "mcctrl.ko",
        "mcctrl.ko.modinfo",
        "mcctrl.ko.modinfo-section",
        "mcctrl.ko.nm",
        "mcctrl.ko.readelf",
        "mcctrl.mod",
        "module-targets.txt",
        "resolved.config",
        "stage-lock.json",
        "workflow-provenance.json",
        "workflow-state",
    ]
    expected_runtime_evidence = [
        "SHA256SUMS",
        "capture.json",
        "environment.txt",
        "executed-caller-workflow.yml",
        "executed-runtime-workflow.yml",
        "initramfs.cpio.gz",
        "initramfs.sha256",
        "native-rust-runtime-mcd0-ioctl-i386",
        "native-rust-runtime-mcd0-ioctl-i386.o",
        "native-rust-runtime-mcd0-ioctl-x86_64",
        "native-rust-runtime-mcd0-ioctl-x86_64.o",
        "native-rust-runtime-poweroff.o",
        "qemu-command.txt",
        "qemu-version.txt",
        "qemu.exit-code",
        "qemu.log",
        "runtime-workflow-provenance.json",
        "serial.log",
        "workflow-state",
    ]
    if (
        artifacts["build_evidence_files"] != expected_build_evidence
        or artifacts["runtime_evidence_files"] != expected_runtime_evidence
    ):
        raise EvidenceError("required immutable artifact file set differs")

    inputs = contract["repository_inputs"]
    _require_keys(
        inputs,
        {
            "build_workflow",
            "config_fragment",
            "init",
            "kbuild_link_closure",
            "kconfig_policy",
            "kconfig_solver",
            "mcd0_ioctl_i386",
            "mcd0_ioctl_x86_64",
            "poweroff",
            "runtime_pr_workflow",
            "runtime_workflow",
            "source_lock",
        },
        "repository_inputs",
    )
    expected_inputs = {
        "build_workflow": ".github/workflows/native-rust-host-modules-exact-build.yml",
        "config_fragment": "host-kernel/rocky/configs/native-rust-evidence.config",
        "init": "scripts/native-rust-runtime-init.sh",
        "kbuild_link_closure": "scripts/native_rust_kbuild_link_closure.py",
        "kconfig_policy": "scripts/native_rust_kconfig_policy.py",
        "kconfig_solver": "scripts/native_rust_kconfig_solver.py",
        "mcd0_ioctl_i386": "scripts/native-rust-runtime-mcd0-ioctl-i386.S",
        "mcd0_ioctl_x86_64": "scripts/native-rust-runtime-mcd0-ioctl-x86_64.S",
        "poweroff": "scripts/native-rust-runtime-poweroff.S",
        "runtime_pr_workflow": ".github/workflows/native-rust-host-modules-exact-runtime-pr.yml",
        "runtime_workflow": ".github/workflows/native-rust-host-modules-exact-runtime.yml",
        "source_lock": "host-kernel/rocky/source-lock.json",
    }
    if inputs != expected_inputs:
        raise EvidenceError("runtime repository input paths differ")
    workflow_identities = contract["repository_workflow_identities"]
    if not _exact_typed_equal(
        workflow_identities, EXPECTED_REPOSITORY_WORKFLOW_IDENTITIES
    ):
        raise EvidenceError("runtime repository workflow identities differ")
    helper_identities = contract["repository_helper_identities"]
    if not _exact_typed_equal(
        helper_identities, EXPECTED_REPOSITORY_HELPER_IDENTITIES
    ):
        raise EvidenceError("runtime repository helper identities differ")
    actual_helper_identities = {}
    for key in sorted(EXPECTED_REPOSITORY_HELPER_IDENTITIES):
        data = _read_regular_evidence_bytes(
            _repo_file(repo, inputs[key], "runtime {0} helper".format(key)),
            "runtime {0} helper".format(key),
        )
        actual_helper_identities[key] = {
            "git_blob_sha1": _git_blob_sha1(data),
            "sha256": _sha256_bytes(data),
            "size": len(data),
        }
    if actual_helper_identities != helper_identities:
        raise EvidenceError("runtime repository helper byte identity differs")
    semantic_authority_identities = contract[
        "repository_semantic_authority_identities"
    ]
    if not _exact_typed_equal(
        semantic_authority_identities,
        EXPECTED_REPOSITORY_SEMANTIC_AUTHORITY_IDENTITIES,
    ):
        raise EvidenceError("runtime semantic authority identities differ")
    actual_semantic_authority_identities = {}
    for key in sorted(EXPECTED_REPOSITORY_SEMANTIC_AUTHORITY_IDENTITIES):
        data = _read_regular_evidence_bytes(
            _repo_file(
                repo,
                inputs[key],
                "runtime semantic authority {0}".format(key),
            ),
            "runtime semantic authority {0}".format(key),
        )
        actual_semantic_authority_identities[key] = (
            _semantic_authority_identity(data)
        )
    if actual_semantic_authority_identities != semantic_authority_identities:
        raise EvidenceError("runtime semantic authority byte identity differs")

    actual_workflow_identities: dict[str, dict[str, Any]] = {}

    def read_bound_workflow(key: str, label: str) -> str:
        path = _repo_file(repo, inputs[key], label)
        data = _read_regular_evidence_bytes(path, label)
        actual_workflow_identities[key] = {
            "git_blob_sha1": _git_blob_sha1(data),
            "sha256": _sha256_bytes(data),
            "size": len(data),
        }
        try:
            return data.decode("utf-8")
        except UnicodeError as error:
            raise EvidenceError("cannot decode {0}: {1}".format(label, error)) from error

    build_workflow = read_bound_workflow("build_workflow", "exact build workflow")
    runtime_workflow = read_bound_workflow("runtime_workflow", "runtime workflow")
    runtime_pr_workflow = read_bound_workflow(
        "runtime_pr_workflow", "runtime PR workflow"
    )
    _validate_runtime_pr_workflow(runtime_pr_workflow)
    _validate_runtime_modinfo_boundary(runtime_workflow)
    _validate_runtime_nm_boundary(runtime_workflow)
    _validate_runtime_workflow_provenance_boundary(runtime_workflow)
    init = _read_text(_repo_file(repo, inputs["init"], "runtime init"), "runtime init")
    poweroff = _read_text(
        _repo_file(repo, inputs["poweroff"], "runtime poweroff"), "runtime poweroff"
    )
    config_bytes = _read_regular_evidence_bytes(
        _repo_file(repo, inputs["config_fragment"], "runtime config fragment"),
        "runtime config fragment",
    )
    try:
        config_receipt = _run_isolated_semantic_worker(
            "config",
            {"config_b64": base64.b64encode(config_bytes).decode("ascii")},
        )
    except EvidenceError as error:
        raise EvidenceError(
            "runtime config fragment policy violation: {0}".format(error)
        ) from error
    if not _exact_typed_equal(config_receipt, {"config_valid": True}):
        raise EvidenceError("runtime config fragment policy receipt differs")
    for fragment in ("workflow_call:", '"$EVIDENCE_DIR/bzImage"'):
        if fragment not in build_workflow:
            raise EvidenceError("exact build workflow is not a reusable boot artifact producer")
    _validate_exact_build_workflow(build_workflow)
    for assignment in (
        "  EXPECTED_KERNEL_RELEASE: {0}\n".format(EXPECTED_KERNEL_RELEASE),
        "  NATIVE_KERNEL_LOCALVERSION: {0}\n".format(EXPECTED_KERNEL_LOCALVERSION),
    ):
        if build_workflow.count(assignment) != 5:
            raise EvidenceError("exact build workflow kernel-release identity differs")
    if build_workflow.count('LOCALVERSION="$NATIVE_KERNEL_LOCALVERSION"') != 6:
        raise EvidenceError("exact build workflow does not bind every Kbuild release")
    for fragment in (
        'test "${vermagic%% *}" = "$EXPECTED_KERNEL_RELEASE"',
        'test "$kernel_release" = "$EXPECTED_KERNEL_RELEASE"',
        'printf \'%s\\n\' "$kernel_release" > "$EVIDENCE_DIR/kernel.release"',
    ):
        if build_workflow.count(fragment) != 1:
            raise EvidenceError("exact build workflow release check differs")

    image = contract["runtime"]["container_image"]
    if runtime_workflow.count(image) < 1:
        raise EvidenceError("runtime workflow does not pin the exact Rocky container digest")
    uses = re.findall(r"^\s*uses:\s*(\S+)", runtime_workflow, re.MULTILINE)
    remote_uses = [item for item in uses if not item.startswith("./")]
    if not remote_uses or any(
        not re.match(r"^[^@]+@[0-9a-f]{40}$", item) for item in remote_uses
    ):
        raise EvidenceError("runtime workflow contains an unpinned action")
    required_workflow = (
        "uses: ./.github/workflows/native-rust-host-modules-exact-build.yml",
        "actions/download-artifact@",
        "dnf -y --allowerasing --setopt=install_weak_deps=False install",
        "copy_executable /usr/bin/stat /bin/stat",
        "-machine q35",
        "-accel tcg",
        "-cpu max",
        "rdinit=/init",
        "native_rust_runtime_evidence.py",
        "if: ${{ always() }}",
        "compression-level: 0",
        "technical-capture-unreviewed",
        "credit=forbidden",
    )
    for fragment in required_workflow:
        if fragment not in runtime_workflow:
            raise EvidenceError("runtime workflow lacks required boundary: {0}".format(fragment))
    if runtime_workflow.count("--allowerasing") != 1:
        raise EvidenceError("runtime workflow coreutils replacement scope differs")
    coreutils_replacement = (
        "          dnf -y --allowerasing --setopt=install_weak_deps=False install \\\n"
        "            coreutils\n"
        "          dnf -y --setopt=install_weak_deps=False install \\\n"
        "            bash binutils cpio findutils gawk git-core gzip kmod \\\n"
        "            qemu-kvm-core python3 sed util-linux which\n"
        "          ! /usr/bin/rpm -q coreutils-single\n"
        "          test \"$(/usr/bin/rpm -qf --qf '%{NAME}\\n' /usr/bin/timeout)\" = coreutils\n"
    )
    if runtime_workflow.count(coreutils_replacement) != 1:
        raise EvidenceError("runtime workflow coreutils replacement transaction differs")
    checkout_step = (
        "      - name: Check out the exact candidate without credentials\n"
        "        uses: actions/checkout@11d5960a326750d5838078e36cf38b85af677262 # v4\n"
        "        with:\n"
        "          ref: ${{ env.EXPECTED_HEAD_SHA }}\n"
        "          fetch-depth: 1\n"
        "          persist-credentials: false\n"
        "          submodules: recursive\n"
    )
    if runtime_workflow.count(checkout_step) != 1:
        raise EvidenceError("runtime workflow checkout scope differs")
    if runtime_workflow.index(coreutils_replacement) > runtime_workflow.index(
        checkout_step
    ):
        raise EvidenceError("runtime workflow Git bootstrap must precede checkout")
    if "permissions:" not in runtime_workflow:
        raise EvidenceError("runtime capture workflow lacks an explicit permission boundary")
    trigger_block = runtime_workflow[: runtime_workflow.index("permissions:")]
    expected_trigger_block = (
        "name: Native Rust host modules exact Rocky runtime\n"
        "\n"
        "on:\n"
        "  workflow_dispatch:\n"
        "    inputs:\n"
        "      validation_sha:\n"
        "        description: Exact 40-hex candidate commit\n"
        "        required: true\n"
        "        type: string\n"
        "  workflow_call:\n"
        "    inputs:\n"
        "      validation_sha:\n"
        "        description: Exact 40-hex candidate commit\n"
        "        required: true\n"
        "        type: string\n"
        "\n"
    )
    if trigger_block != expected_trigger_block:
        raise EvidenceError("runtime capture dispatch/reusable trigger boundary differs")
    if "permissions:\n  contents: read" not in runtime_workflow:
        raise EvidenceError("runtime capture workflow lacks read-only repository permission")
    for symbol in expected_runtime["required_kernel_config"]["enabled"]:
        if symbol not in runtime_workflow:
            raise EvidenceError(
                "runtime workflow does not verify kernel config: {0}".format(symbol)
            )
    if "# CONFIG_MODULE_SIG_FORCE is not set" not in runtime_workflow:
        raise EvidenceError("runtime workflow does not reject forced module signatures")
    for filename in expected_runtime_evidence:
        if filename not in runtime_workflow:
            raise EvidenceError(
                "runtime workflow does not produce required artifact: {0}".format(filename)
            )
    for forbidden in (
        "--privileged",
        "/dev/kvm",
        "contents: write",
        "credit_eligible: true",
        "credit=eligible",
        "final-push.txt",
        "git push",
        "kernel.log",
    ):
        if forbidden in runtime_workflow.lower():
            raise EvidenceError("runtime workflow contains forbidden host/credit boundary")
    if re.search(r"\bpass\b", runtime_workflow, re.IGNORECASE):
        raise EvidenceError("runtime workflow may not claim a gate PASS")
    if actual_workflow_identities != workflow_identities:
        raise EvidenceError("runtime repository workflow byte identity differs")

    load_markers = [
        'emit_state initial-clean',
        'insmod "$IHK" || { fail load-ihk; exit 1; }',
        'insmod "$SMP" || { fail load-ihk-smp-x86-64; exit 1; }',
        'insmod "$MCCTRL" || { fail load-mcctrl; exit 1; }',
        'negative_output="$(rmmod ihk 2>&1)"',
        'rmmod mcctrl || { fail unload-mcctrl; exit 1; }',
        'rmmod ihk_smp_x86_64 || { fail unload-ihk-smp-x86-64; exit 1; }',
        'rmmod ihk || { fail unload-ihk; exit 1; }',
        'emit_state first-cycle-clean',
        'record "RELOAD cycle=1 phase=begin"',
        'insmod "$IHK" || { fail reload-ihk; exit 1; }',
        'insmod "$SMP" || { fail reload-ihk-smp-x86-64; exit 1; }',
        'insmod "$MCCTRL" || { fail reload-mcctrl; exit 1; }',
        'record "MCD0 RELOAD cycle=1 dev=$mcd0_reload_dev open_close=1 '
        'ioctl_x86_64=EINVAL ioctl_i386=EINVAL status=ok"',
        'rmmod mcctrl || { fail unload-reloaded-mcctrl; exit 1; }',
        'rmmod ihk_smp_x86_64 || { fail unload-reloaded-ihk-smp-x86-64; exit 1; }',
        'rmmod ihk || { fail unload-reloaded-ihk; exit 1; }',
        'record "RELOAD cycle=1 status=ok"',
        'emit_state final-clean',
    ]
    positions = [init.find(marker) for marker in load_markers]
    if any(position < 0 for position in positions) or positions != sorted(positions):
        raise EvidenceError("runtime init does not preserve load/negative/reverse-unload order")
    for fragment in (
        "phase=all-loaded references=$references users=$users",
        "phase=after-negative references=$references users=$users",
        "phase=after-mcctrl-unload references=$references users=$users",
        "phase=after-smp-unload references=$references users=$users",
        "phase=reload-all-loaded references=$references users=$users",
        "technical-capture-unreviewed credit=forbidden",
        "NEGATIVE operation=unload-provider-first",
        "MCD0 NODE status=present dev=$mcd0_dev",
        "MCD0 OPEN_CLOSE mode=sequential count=4 status=ok",
        "MCD0 OPEN_CLOSE mode=overlapping count=8 status=ok",
        "MCD0 IOCTL abi=x86_64 expected_errno=EINVAL status=ok",
        "MCD0 IOCTL abi=i386 expected_errno=EINVAL status=ok",
        "MCD0 NEGATIVE operation=unload-smp-with-open-file",
        "MCD0 CLOSE phase=after-module-owner-negative status=ok",
        "MCD0 NODE status=removed",
        "valid_mcd0_dev_identity() {",
        'valid_mcd0_dev_identity "$mcd0_dev"',
        'valid_mcd0_dev_identity "$mcd0_reload_dev"',
        "mcd0_node_matches_identity() {",
        'mcd0_node_matches_identity "$mcd0_dev"',
        'mcd0_node_matches_identity "$mcd0_reload_dev"',
        'expected="$(printf \'a:%x\' "$minor")" || return 1',
        '[ -c /dev/mcd0 ] && [ ! -L /dev/mcd0 ] || return 1',
        'actual="$(/bin/stat -c \'%t:%T\' /dev/mcd0)" || return 1',
        '[ "$actual" = "$expected" ]',
        "RELOAD_LOAD cycle=1 module=ihk status=ok",
        "RELOAD_LOAD cycle=1 module=ihk_smp_x86_64 status=ok",
        "RELOAD_LOAD cycle=1 module=mcctrl status=ok",
        "RELOAD_UNLOAD cycle=1 module=mcctrl status=ok",
        "RELOAD_UNLOAD cycle=1 module=ihk_smp_x86_64 status=ok",
        "RELOAD_UNLOAD cycle=1 module=ihk status=ok",
        "STATE_BEGIN label=$label",
        "DMESG_BEGIN",
        "@EXPECTED_KERNEL_RELEASE@",
    ):
        if fragment not in init:
            raise EvidenceError("runtime init lacks evidence marker: {0}".format(fragment))
    if runtime_workflow.count("copy_executable /usr/bin/stat /bin/stat") != 1:
        raise EvidenceError("runtime workflow stat helper binding differs")
    for fragment in (
        "mcd0_node_matches_identity() {",
        'expected="$(printf \'a:%x\' "$minor")" || return 1',
        '[ -c /dev/mcd0 ] && [ ! -L /dev/mcd0 ] || return 1',
        'actual="$(/bin/stat -c \'%t:%T\' /dev/mcd0)" || return 1',
        '[ "$actual" = "$expected" ]',
        'mcd0_node_matches_identity "$mcd0_dev"',
        'mcd0_node_matches_identity "$mcd0_reload_dev"',
    ):
        if init.count(fragment) != 1:
            raise EvidenceError("runtime init mcd0 node identity binding differs")
    active_init = _active_shell_lines(init)
    for teardown_guard in (
        '[ ! -e /dev/mcd0 ] && [ ! -L /dev/mcd0 ] || {',
        '[ ! -e /sys/class/misc/mcd0 ] && [ ! -L /sys/class/misc/mcd0 ] || {',
    ):
        if active_init.count(teardown_guard) != 2:
            raise EvidenceError("runtime init mcd0 teardown identity differs")
    canonical_pair = "mcctrl,ihk_smp_x86_64,|ihk_smp_x86_64,mcctrl,) ;;"
    if active_init.count(canonical_pair) != 3:
        raise EvidenceError("runtime init provider-user grammar differs")
    if active_init.count(
        '[ "$users" = \'ihk_smp_x86_64,\' ] || '
        "{ fail wrong-users-after-mcctrl; exit 1; }"
    ) != 1:
        raise EvidenceError("runtime init sole-provider-user grammar differs")
    if _sha256_bytes(init.encode("utf-8")) != EXPECTED_RUNTIME_INIT_SHA256:
        raise EvidenceError("runtime init identity differs")
    if re.search(r"\bpass\b", init, re.IGNORECASE) or "credit=eligible" in init:
        raise EvidenceError("runtime init may not claim PASS or credit")
    for value in ("$0xfee1dead", "$0x28121969", "$0x4321fedc"):
        if value not in poweroff:
            raise EvidenceError("poweroff helper lacks exact Linux reboot ABI constant")

    return {
        "contract_id": CONTRACT_ID,
        "contract_path": contract_relative.as_posix(),
        "contract_sha256": _sha256_file(contract_path),
        "gate_ids": contract["gate"]["gate_ids"],
        "runtime": contract["runtime"],
    }


def _strict_ascii_lf_lines(path: Path, label: str) -> list[str]:
    data = _read_regular_evidence_bytes(path, label)
    try:
        text = data.decode("ascii")
    except UnicodeError as error:
        raise EvidenceError("{0} is not strict ASCII".format(label)) from error
    if not text or not text.endswith("\n") or "\r" in text:
        raise EvidenceError("{0} is not canonical LF-terminated text".format(label))
    lines = text[:-1].split("\n")
    if not lines or any(not line for line in lines):
        raise EvidenceError("{0} contains an empty row".format(label))
    return lines


def _parse_sums(directory: Path) -> dict[str, str]:
    sums_path = directory / "SHA256SUMS"
    records: dict[str, str] = {}
    ordered: list[str] = []
    for line in _strict_ascii_lf_lines(sums_path, "build SHA256SUMS"):
        match = re.fullmatch(r"([0-9a-f]{64})  ([A-Za-z0-9._-]+)", line)
        if (
            not match
            or match.group(2) in records
            or match.group(2) in {".", "..", "SHA256SUMS"}
        ):
            raise EvidenceError("malformed or duplicate build SHA256SUMS entry")
        records[match.group(2)] = match.group(1)
        ordered.append(match.group(2))
    if not records:
        raise EvidenceError("build SHA256SUMS is empty")
    if ordered != sorted(ordered):
        raise EvidenceError("build SHA256SUMS paths are not canonical-order sorted")
    for name, digest in records.items():
        path = directory / name
        if path.is_symlink() or not path.is_file() or _sha256_file(path) != digest:
            raise EvidenceError("build evidence digest differs for {0}".format(name))
    return records


def _parse_precheck_sums(
    directory: Path, final_records: dict[str, str], expected: list[str]
) -> dict[str, str]:
    precheck_path = directory / "PRECHECK_SHA256SUMS"
    if precheck_path.is_symlink() or not precheck_path.is_file():
        raise EvidenceError("build evidence lacks regular PRECHECK_SHA256SUMS")
    records: dict[str, str] = {}
    ordered: list[str] = []
    for line in _strict_ascii_lf_lines(
        precheck_path, "build PRECHECK_SHA256SUMS"
    ):
        match = re.fullmatch(r"([0-9a-f]{64})  ([A-Za-z0-9._-]+)", line)
        if (
            not match
            or match.group(2) in records
            or match.group(2) in {".", "..", "PRECHECK_SHA256SUMS", "SHA256SUMS"}
        ):
            raise EvidenceError(
                "malformed or duplicate build PRECHECK_SHA256SUMS entry"
            )
        name = match.group(2)
        records[name] = match.group(1)
        ordered.append(name)
    if ordered != sorted(ordered) or ordered != expected:
        raise EvidenceError("build PRECHECK_SHA256SUMS file set or order differs")
    for name, digest in records.items():
        if final_records.get(name) != digest:
            raise EvidenceError(
                "build precheck/final digest differs for {0}".format(name)
            )
        path = directory / name
        if path.is_symlink() or not path.is_file() or _sha256_file(path) != digest:
            raise EvidenceError(
                "build precheck evidence digest differs for {0}".format(name)
            )
    return records


def _validate_exact_build_artifact_files(
    directory: Path,
    records: dict[str, str],
    expected: list[str],
    max_file_size: int = MAX_BUILD_EVIDENCE_FILE_SIZE,
    per_file_max: dict[str, int] | None = None,
) -> dict[str, tuple[Any, ...]]:
    if (
        type(expected) is not list
        or expected != sorted(expected)
        or len(expected) != len(set(expected))
        or "SHA256SUMS" not in expected
    ):
        raise EvidenceError("build artifact contract file list is not exact and sorted")
    actual: list[str] = []
    identities: dict[str, tuple[Any, ...]] = {}
    inode_owners: dict[tuple[int, int], str] = {}
    try:
        entries = list(os.scandir(directory))
    except OSError as error:
        raise EvidenceError("cannot scan build artifact: {0}".format(error)) from error
    for entry in entries:
        try:
            metadata = entry.stat(follow_symlinks=False)
        except OSError as error:
            raise EvidenceError(
                "cannot inspect build artifact entry: {0}".format(error)
            ) from error
        if (
            entry.name in {"", ".", ".."}
            or "/" in entry.name
            or "\\" in entry.name
            or not stat.S_ISREG(metadata.st_mode)
            or stat.S_IMODE(metadata.st_mode) != 0o644
        ):
            raise EvidenceError(
                "build artifact contains a non-regular, non-0644, or unsafe entry"
            )
        limit = (
            per_file_max.get(entry.name, max_file_size)
            if per_file_max is not None
            else max_file_size
        )
        if (
            type(limit) is not int
            or limit < 1
            or metadata.st_size > limit
        ):
            raise EvidenceError(
                "build artifact file exceeds its exact size limit: {0}".format(
                    entry.name
                )
            )
        inode = (metadata.st_dev, metadata.st_ino)
        if inode in inode_owners:
            raise EvidenceError(
                "build artifact contains hard-link aliases: {0}, {1}".format(
                    inode_owners[inode], entry.name
                )
            )
        inode_owners[inode] = entry.name
        actual.append(entry.name)
        identities[entry.name] = _stat_identity(metadata)
    actual.sort()
    if actual != expected:
        raise EvidenceError(
            "build artifact file set differs: missing={0}, extra={1}".format(
                sorted(set(expected) - set(actual)),
                sorted(set(actual) - set(expected)),
            )
        )
    manifested = sorted(set(records) | {"SHA256SUMS"})
    if manifested != expected:
        raise EvidenceError(
            "build SHA256SUMS file set differs: missing={0}, extra={1}".format(
                sorted(set(expected) - set(manifested)),
                sorted(set(manifested) - set(expected)),
            )
        )
    return identities


def _validate_runtime_helper_artifacts(
    directory: Path,
    records: dict[str, str],
    bound_files: dict[str, int] | None = None,
) -> None:
    for name, expected in sorted(RUNTIME_HELPER_ELF_SPEC.items()):
        elf_class, elf_type, machine = expected
        if bound_files is not None:
            if set(bound_files) != set(RUNTIME_HELPER_ELF_SPEC):
                raise EvidenceError("bound runtime helper file set differs")
            data, _identity = _read_bound_descriptor_bytes(
                bound_files[name],
                MAX_RUNTIME_HELPER_FILE_SIZE,
                "runtime helper artifact {0}".format(name),
            )
        else:
            data = _read_regular_evidence_bytes(
                directory / name, "runtime helper artifact {0}".format(name)
            )
        minimum = 52 if elf_class == 1 else 64
        if (
            len(data) < minimum
            or len(data) > MAX_RUNTIME_HELPER_FILE_SIZE
            or data[:4] != b"\x7fELF"
            or data[4] != elf_class
            or data[5] != 1
            or data[6] != 1
            or int.from_bytes(data[16:18], "little") != elf_type
            or int.from_bytes(data[18:20], "little") != machine
            or int.from_bytes(data[20:24], "little") != 1
            or int.from_bytes(
                data[40:42] if elf_class == 1 else data[52:54], "little"
            )
            != minimum
            or _sha256_bytes(data) != records.get(name)
        ):
            raise EvidenceError(
                "runtime helper ELF identity differs: {0}".format(name)
            )
        if elf_type == 2:
            _validate_runtime_probe_elf(name, data, elf_class, machine)


def _checked_elf_slice(
    data: bytes, offset: int, size: int, label: str
) -> bytes:
    if (
        type(offset) is not int
        or type(size) is not int
        or offset < 0
        or size < 0
        or offset > len(data)
        or size > len(data) - offset
    ):
        raise EvidenceError("runtime helper ELF {0} is out of bounds".format(label))
    return data[offset : offset + size]


def _validate_runtime_probe_elf(
    name: str, data: bytes, elf_class: int, machine: int
) -> None:
    expected_layouts = {
        1: {
            "header": "<16sHHIIIIIHHHHHH",
            "header_size": 52,
            "program": "<IIIIIIII",
            "program_size": 32,
            "section": "<IIIIIIIIII",
            "section_size": 40,
            "text_address": 0x08049000,
            "rodata_address": 0x0804A000,
        },
        2: {
            "header": "<16sHHIQQQIHHHHHH",
            "header_size": 64,
            "program": "<IIQQQQQQ",
            "program_size": 56,
            "section": "<IIQQQQIIQQ",
            "section_size": 64,
            "text_address": 0x401000,
            "rodata_address": 0x402000,
        },
    }
    layout = expected_layouts[elf_class]
    try:
        header = struct.unpack(
            layout["header"],
            _checked_elf_slice(data, 0, layout["header_size"], "header"),
        )
    except (KeyError, struct.error) as error:
        raise EvidenceError(
            "runtime helper executable header differs: {0}".format(name)
        ) from error
    (
        ident,
        elf_type,
        observed_machine,
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
        section_names_index,
    ) = header
    expected_ident = b"\x7fELF" + bytes((elf_class, 1, 1)) + b"\0" * 9
    if (
        ident != expected_ident
        or elf_type != 2
        or observed_machine != machine
        or version != 1
        or flags != 0
        or header_size != layout["header_size"]
        or program_offset != header_size
        or program_entry_size != layout["program_size"]
        or program_count != 4
        or section_entry_size != layout["section_size"]
        or section_count != 4
        or section_names_index != 3
        or section_offset + section_count * section_entry_size != len(data)
    ):
        raise EvidenceError(
            "runtime helper executable ELF boundary differs: {0}".format(name)
        )

    sections = []
    try:
        for index in range(section_count):
            fields = struct.unpack(
                layout["section"],
                _checked_elf_slice(
                    data,
                    section_offset + index * section_entry_size,
                    section_entry_size,
                    "section header",
                ),
            )
            sections.append(fields)
    except struct.error as error:
        raise EvidenceError(
            "runtime helper executable section table differs: {0}".format(name)
        ) from error
    if any(sections[0]):
        raise EvidenceError(
            "runtime helper executable null section differs: {0}".format(name)
        )
    names = _checked_elf_slice(
        data, sections[3][4], sections[3][5], "section-name table"
    )
    if (
        not names.startswith(b"\0")
        or not names.endswith(b"\0")
        or len(names) < 2
        or sorted(names[1:-1].split(b"\0"))
        != [b".rodata", b".shstrtab", b".text"]
    ):
        raise EvidenceError(
            "runtime helper executable section names differ: {0}".format(name)
        )

    def section_name(offset: int) -> bytes:
        if type(offset) is not int or offset < 0 or offset >= len(names):
            raise EvidenceError(
                "runtime helper executable section-name offset differs: {0}".format(
                    name
                )
            )
        end = names.find(b"\0", offset)
        if end < 0:
            raise EvidenceError(
                "runtime helper executable section-name terminator differs: {0}".format(
                    name
                )
            )
        return names[offset:end]

    observed_names = [section_name(item[0]) for item in sections]
    if observed_names != [b"", b".text", b".rodata", b".shstrtab"]:
        raise EvidenceError(
            "runtime helper executable section order differs: {0}".format(name)
        )
    text_section = sections[1]
    rodata_section = sections[2]
    shstr_section = sections[3]
    if (
        text_section[1] != 1
        or text_section[2] != 0x6
        or text_section[3] != layout["text_address"]
        or text_section[4] != 0x1000
        or text_section[6:] != (0, 0, 1, 0)
        or rodata_section[1] != 1
        or rodata_section[2] != 0x2
        or rodata_section[3] != layout["rodata_address"]
        or rodata_section[4] != 0x2000
        or rodata_section[5] != 10
        or rodata_section[6:] != (0, 0, 1, 0)
        or shstr_section[1] != 3
        or shstr_section[2] != 0
        or shstr_section[3] != 0
        or shstr_section[6:] != (0, 0, 1, 0)
        or section_offset
        != (shstr_section[4] + shstr_section[5] + (7 if elf_class == 2 else 3))
        // (8 if elf_class == 2 else 4)
        * (8 if elf_class == 2 else 4)
        or entry != text_section[3]
    ):
        raise EvidenceError(
            "runtime helper executable section semantics differ: {0}".format(name)
        )
    text = _checked_elf_slice(
        data, text_section[4], text_section[5], "text section"
    )
    rodata = _checked_elf_slice(
        data, rodata_section[4], rodata_section[5], "rodata section"
    )
    prefix, suffix = RUNTIME_PROBE_TEXT_TEMPLATE[name]
    if (
        rodata != b"/dev/mcd0\0"
        or len(text) != len(prefix) + 4 + len(suffix)
        or text[: len(prefix)] != prefix
        or text[len(prefix) + 4 :] != suffix
    ):
        raise EvidenceError(
            "runtime helper executable instruction semantics differ: {0}".format(
                name
            )
        )
    address_bytes = text[len(prefix) : len(prefix) + 4]
    if elf_class == 2:
        displacement = struct.unpack("<i", address_bytes)[0]
        target = text_section[3] + len(prefix) + 4 + displacement
    else:
        target = struct.unpack("<I", address_bytes)[0]
    if target != rodata_section[3]:
        raise EvidenceError(
            "runtime helper executable device address differs: {0}".format(name)
        )

    programs = []
    try:
        for index in range(program_count):
            fields = struct.unpack(
                layout["program"],
                _checked_elf_slice(
                    data,
                    program_offset + index * program_entry_size,
                    program_entry_size,
                    "program header",
                ),
            )
            if elf_class == 1:
                kind, offset, virtual, physical, file_size, memory_size, mode, align = fields
            else:
                kind, mode, offset, virtual, physical, file_size, memory_size, align = fields
            programs.append(
                (kind, mode, offset, virtual, physical, file_size, memory_size, align)
            )
    except struct.error as error:
        raise EvidenceError(
            "runtime helper executable program table differs: {0}".format(name)
        ) from error
    base = text_section[3] - text_section[4]
    expected_programs = [
        (1, 4, 0, base, base, header_size + program_count * program_entry_size,
         header_size + program_count * program_entry_size, 0x1000),
        (1, 5, text_section[4], text_section[3], text_section[3],
         text_section[5], text_section[5], 0x1000),
        (1, 4, rodata_section[4], rodata_section[3], rodata_section[3],
         rodata_section[5], rodata_section[5], 0x1000),
        (0x6474E551, 6, 0, 0, 0, 0, 0, 0x10),
    ]
    if programs != expected_programs:
        raise EvidenceError(
            "runtime helper executable load semantics differ: {0}".format(name)
        )


def _read_phase2_bound_file(
    source_dir_fd: int,
    name: str,
    expected_digest: str,
    maximum_size: int,
) -> bytes:
    if (
        not isinstance(name, str)
        or not name
        or "/" in name
        or "\\" in name
        or name in (".", "..")
    ):
        raise EvidenceError("phase-2 snapshot member name is unsafe")
    try:
        before = os.stat(name, dir_fd=source_dir_fd, follow_symlinks=False)
    except OSError as error:
        raise EvidenceError(
            "cannot inspect phase-2 snapshot source: {0}".format(name)
        ) from error
    if (
        not stat.S_ISREG(before.st_mode)
        or stat.S_IMODE(before.st_mode) != 0o644
        or before.st_size < 1
        or before.st_size > maximum_size
    ):
        raise EvidenceError("phase-2 snapshot source shape differs: {0}".format(name))
    read_flags = os.O_RDONLY
    for flag_name in ("O_CLOEXEC", "O_NOFOLLOW"):
        if hasattr(os, flag_name):
            read_flags |= getattr(os, flag_name)
    source_fd = None
    try:
        source_fd = os.open(name, read_flags, dir_fd=source_dir_fd)
        opened = os.fstat(source_fd)
        if _stat_identity(opened) != _stat_identity(before):
            raise EvidenceError("phase-2 snapshot source changed while opening")
        digest = hashlib.sha256()
        chunks = []
        copied = 0
        while True:
            chunk = os.read(source_fd, 65536)
            if not chunk:
                break
            copied += len(chunk)
            if copied > maximum_size:
                raise EvidenceError("phase-2 snapshot source exceeds its size cap")
            digest.update(chunk)
            chunks.append(chunk)
        if (
            copied != before.st_size
            or digest.hexdigest() != expected_digest
            or _stat_identity(os.fstat(source_fd)) != _stat_identity(before)
        ):
            raise EvidenceError("phase-2 snapshot source identity differs")
        return b"".join(chunks)
    except OSError as error:
        raise EvidenceError("cannot read phase-2 bound file: {0}".format(error)) from error
    finally:
        if source_fd is not None:
            os.close(source_fd)


def _link_ascii_lf_text(raw: bytes, label: str, maximum_size: int) -> str:
    if (
        type(raw) is not bytes
        or not raw
        or len(raw) > maximum_size
        or not raw.endswith(b"\n")
        or b"\r" in raw
    ):
        raise LinkClosureError("{0} is not bounded canonical LF text".format(label))
    try:
        text = raw.decode("ascii")
    except UnicodeDecodeError as error:
        raise LinkClosureError("{0} is not ASCII: {1}".format(label, error))
    for character in text:
        codepoint = ord(character)
        if character not in ("\t", "\n") and not 0x20 <= codepoint <= 0x7E:
            raise LinkClosureError(
                "{0} contains forbidden control U+{1:04X}".format(label, codepoint)
            )
    return text


def _parse_link_stage_lock_bytes(raw: bytes) -> tuple[dict[str, Any], dict[str, str]]:
    text = _link_ascii_lf_text(
        raw, "stage lock", _link_closure_module.MAX_STAGE_LOCK_BYTES
    )
    try:
        value = json.loads(
            text,
            object_pairs_hook=_link_closure_module._object_without_duplicates,
        )
    except (TypeError, ValueError) as error:
        raise LinkClosureError("cannot parse stage lock: {0}".format(error))
    if _link_closure_module.canonical_bytes(value) != raw:
        raise LinkClosureError("stage lock must use canonical JSON bytes")
    _link_closure_module._require_keys(
        value,
        (
            "credit_eligible",
            "files",
            "manifest_sha256",
            "parent_integration",
            "production_readiness_blockers",
            "profile_id",
            "purpose",
            "schema_version",
            "target",
        ),
        "stage lock",
    )
    if value["credit_eligible"] is not False or value["purpose"] != "compiler-evidence-only":
        raise LinkClosureError("stage lock must remain compiler-only and credit forbidden")
    if type(value["schema_version"]) is not int or value["schema_version"] != 2:
        raise LinkClosureError("stage lock schema version differs")
    if value["profile_id"] != _link_closure_module.STAGE_PROFILE_ID:
        raise LinkClosureError("stage lock profile_id differs")
    if not isinstance(value["manifest_sha256"], str) or not _link_closure_module.HEX64.match(
        value["manifest_sha256"]
    ):
        raise LinkClosureError("stage lock manifest digest differs")
    blockers = value["production_readiness_blockers"]
    if (
        not isinstance(blockers, list)
        or not blockers
        or any(not isinstance(item, str) or not item for item in blockers)
        or len(blockers) != len(set(blockers))
    ):
        raise LinkClosureError("stage lock readiness blockers must be unique and non-empty")
    parent = value["parent_integration"]
    _link_closure_module._require_keys(
        parent,
        ("bundle_sha256", "parent_files", "patch_sha256"),
        "stage lock parent integration",
    )
    for field in ("bundle_sha256", "patch_sha256"):
        if not isinstance(parent[field], str) or not _link_closure_module.HEX64.match(
            parent[field]
        ):
            raise LinkClosureError("stage lock parent integration digest differs")
    parent_files = parent["parent_files"]
    if not isinstance(parent_files, list) or len(parent_files) != 2:
        raise LinkClosureError("stage lock parent files differ")
    expected_parent_paths = ("drivers/misc/Makefile", "drivers/misc/Kconfig")
    for index, item in enumerate(parent_files):
        _link_closure_module._require_keys(
            item,
            ("path", "postimage_sha256", "preimage_sha256"),
            "stage lock parent files[{0}]".format(index),
        )
        if item["path"] != expected_parent_paths[index]:
            raise LinkClosureError("stage lock parent file path or order differs")
        for field in ("postimage_sha256", "preimage_sha256"):
            if not isinstance(item[field], str) or not _link_closure_module.HEX64.match(
                item[field]
            ):
                raise LinkClosureError("stage lock parent file digest differs")
    if value["target"] != _link_closure_module.EXPECTED_STAGE_TARGET:
        raise LinkClosureError("stage lock target identity or schema differs")
    files = value["files"]
    if not isinstance(files, list):
        raise LinkClosureError("stage lock files must be a list")
    normalized = []
    digests = {}
    for index, item in enumerate(files):
        _link_closure_module._require_keys(
            item, ("path", "sha256"), "stage lock files[{0}]".format(index)
        )
        relative = _link_closure_module._safe_relative_path(
            item["path"], "stage lock files[{0}].path".format(index)
        )
        digest = item["sha256"]
        if not isinstance(digest, str) or not _link_closure_module.HEX64.match(digest):
            raise LinkClosureError("stage lock file digest must be lowercase SHA-256")
        if relative in digests:
            raise LinkClosureError("stage lock contains duplicate paths")
        normalized.append(relative)
        digests[relative] = digest
    if tuple(normalized) != _link_closure_module.EXPECTED_STAGED_FILES:
        raise LinkClosureError("stage lock staged file set or order differs")
    return value, digests


def _validate_kbuild_link_closure_bytes(
    raw: dict[str, bytes], stage_raw: bytes
) -> dict[str, Any]:
    if set(raw) != set(EXPECTED_RAW_RECORD_NAMES):
        raise LinkClosureError("raw record byte set differs")
    texts = {
        name: _link_ascii_lf_text(
            raw[name],
            "raw record {0}".format(name),
            _link_closure_module.MAX_RECORD_BYTES,
        )
        for name in EXPECTED_RAW_RECORD_NAMES
    }
    stage_value, stage_digests = _parse_link_stage_lock_bytes(stage_raw)
    stage_binding = {
        "manifest_sha256": stage_value["manifest_sha256"],
        "profile_id": stage_value["profile_id"],
        "schema_version": stage_value["schema_version"],
        "sha256": _sha256_bytes(stage_raw),
    }
    module_results = []
    all_sources = set()
    source_prefixes = set()
    for module in _link_closure_module.MODULES:
        rust_target = "{0}/{1}".format(
            _link_closure_module.MODULE_ROOT, module["rust_object"]
        )
        rust_name = _link_closure_module._cmd_name(rust_target)
        rust_command = _link_closure_module._parse_saved_command(
            rust_name, rust_target, texts[rust_name]
        )
        sources, source_prefix = _link_closure_module._parse_rust_record(
            rust_name, rust_target, rust_command, texts[rust_name], module
        )
        all_sources.update(sources)
        source_prefixes.add(source_prefix)
        mod_target = "{0}/{1}.mod".format(
            _link_closure_module.MODULE_ROOT, module["name"]
        )
        mod_name = _link_closure_module._cmd_name(mod_target)
        mod_command = _link_closure_module._parse_saved_command(
            mod_name, mod_target, texts[mod_name]
        )
        _link_closure_module._parse_mod_generator(
            mod_name, mod_target, mod_command, module
        )
        response_name = "{0}.mod".format(module["name"])
        expected_response = "{0}/{1}\n".format(
            _link_closure_module.MODULE_ROOT, module["rust_object"]
        ).encode("ascii")
        if raw[response_name] != expected_response:
            raise LinkClosureError(
                "{0} raw object-list response differs".format(response_name)
            )
        generated_target = "{0}/{1}.mod.o".format(
            _link_closure_module.MODULE_ROOT, module["name"]
        )
        generated_name = _link_closure_module._cmd_name(generated_target)
        generated_command = _link_closure_module._parse_saved_command(
            generated_name, generated_target, texts[generated_name]
        )
        _link_closure_module._parse_generated_mod(
            generated_name,
            generated_target,
            generated_command,
            texts[generated_name],
            module,
            source_prefix,
        )
        if module["module_object"] != module["rust_object"]:
            aggregate_target = "{0}/{1}".format(
                _link_closure_module.MODULE_ROOT, module["module_object"]
            )
            aggregate_name = _link_closure_module._cmd_name(aggregate_target)
            aggregate_command = _link_closure_module._parse_saved_command(
                aggregate_name, aggregate_target, texts[aggregate_name]
            )
            _link_closure_module._parse_aggregate(
                aggregate_name, aggregate_target, aggregate_command, module
            )
        final_target = "{0}/{1}.ko".format(
            _link_closure_module.MODULE_ROOT, module["name"]
        )
        final_name = _link_closure_module._cmd_name(final_target)
        final_command = _link_closure_module._parse_saved_command(
            final_name, final_target, texts[final_name]
        )
        final_inputs = _link_closure_module._parse_final_link(
            final_name, final_target, final_command, module
        )
        record_names = (rust_name, mod_name, generated_name, final_name)
        if module["module_object"] != module["rust_object"]:
            record_names += (
                _link_closure_module._cmd_name(
                    "{0}/{1}".format(
                        _link_closure_module.MODULE_ROOT, module["module_object"]
                    )
                ),
            )
        for record_name in record_names:
            references = _link_closure_module._project_references(
                texts[record_name], record_name
            )
            _link_closure_module._validate_reference_surface(
                record_name, references, module
            )
        module_results.append(
            {
                "crate": module["crate"],
                "crate_root": module["crate_root"],
                "final_link_inputs": final_inputs,
                "final_module": final_target,
                "module": module["name"],
                "module_object": "{0}/{1}".format(
                    _link_closure_module.MODULE_ROOT, module["module_object"]
                ),
                "raw_object_list": [
                    "{0}/{1}".format(
                        _link_closure_module.MODULE_ROOT, module["rust_object"]
                    )
                ],
                "rust_object": "{0}/{1}".format(
                    _link_closure_module.MODULE_ROOT, module["rust_object"]
                ),
                "source_dependencies": sources,
            }
        )
    if len(source_prefixes) != 1:
        raise LinkClosureError("Rust crate roots do not share one staged source tree")
    if tuple(sorted(all_sources)) != tuple(
        sorted(_link_closure_module.EXPECTED_STAGED_RUST_SOURCES)
    ):
        raise LinkClosureError("compiler Rust source closure differs")
    raw_records = [
        {
            "name": name,
            "sha256": _sha256_bytes(raw[name]),
            "size": len(raw[name]),
        }
        for name in EXPECTED_RAW_RECORD_NAMES
    ]
    return {
        "claims": {
            "complete_external_build_input_closure": False,
            "credit_eligible": False,
            "load_proven": False,
            "production_ready": False,
            "runtime_proven": False,
        },
        "compilers": {
            "generated_module_source": "clang",
            "linker": "ld.lld",
            "object_postprocessor": "./tools/objtool/objtool",
            "project_source": "rustc",
        },
        "modules": module_results,
        "purpose": "detached compiler and final-link provenance; no runtime or gate credit",
        "raw_record_names": list(EXPECTED_RAW_RECORD_NAMES),
        "raw_records": raw_records,
        "raw_records_sha256": _sha256_bytes(
            _link_closure_module.canonical_bytes(raw_records)
        ),
        "schema_id": _link_closure_module.SCHEMA_ID,
        "source_closure": [
            {"path": path, "stage_sha256": stage_digests[path]}
            for path in _link_closure_module.EXPECTED_STAGED_RUST_SOURCES
        ],
        "source_closure_scope": (
            "staged McKernel Rust project sources named by rustc dependency records; "
            "kernel headers, generated kernel metadata, libraries, and toolchain binaries "
            "remain outside this closure"
        ),
        "stage_lock": stage_binding,
    }


def _validate_link_closure_from_bound_snapshot(
    source_dir_fd: int,
    records: dict[str, str],
    matrix_bytes: bytes | None = None,
) -> dict[str, Any]:
    members = tuple(EXPECTED_RAW_RECORD_NAMES) + (
        "stage-lock.json",
        "kbuild-link-closure.json",
    )
    if any(name not in records for name in members):
        raise EvidenceError("phase-2 snapshot manifest is incomplete")
    try:
        directory_identity = _stat_identity(os.fstat(source_dir_fd))
        relevant = tuple(
            sorted(
                name
                for name in os.listdir(source_dir_fd)
                if name.endswith(".cmd") or name.endswith(".mod")
            )
        )
        if relevant != tuple(EXPECTED_RAW_RECORD_NAMES):
            raise LinkClosureError("raw record set differs in bound build evidence")
        trusted = {
            name: _read_phase2_bound_file(
                source_dir_fd,
                name,
                records[name],
                (
                    MAX_KBUILD_STAGE_LOCK_SIZE
                    if name == "stage-lock.json"
                    else MAX_KBUILD_RAW_RECORD_SIZE
                ),
            )
            for name in members
        }
        raw = {name: trusted[name] for name in EXPECTED_RAW_RECORD_NAMES}
        payload = {
            "raw_b64": {
                name: base64.b64encode(raw[name]).decode("ascii")
                for name in EXPECTED_RAW_RECORD_NAMES
            },
            "stage_lock_b64": base64.b64encode(
                trusted["stage-lock.json"]
            ).decode("ascii"),
        }
        action = "link"
        if matrix_bytes is not None:
            if type(matrix_bytes) is not bytes or not matrix_bytes:
                raise LinkClosureError("bound solver matrix bytes differ")
            payload["matrix_b64"] = base64.b64encode(matrix_bytes).decode("ascii")
            action = "phase2"
        receipt = _run_isolated_semantic_worker(action, payload)
        if (
            type(receipt) is not dict
            or "link" not in receipt
            or (action == "link" and set(receipt) != {"link"})
            or (action == "phase2" and set(receipt) != {"link", "matrix"})
        ):
            raise LinkClosureError("isolated link-closure receipt differs")
        value = receipt["link"]
        if trusted["kbuild-link-closure.json"] != _canonical_bytes(value):
            raise LinkClosureError(
                "link closure output differs from reparsed raw records"
            )
        final_relevant = tuple(
            sorted(
                name
                for name in os.listdir(source_dir_fd)
                if name.endswith(".cmd") or name.endswith(".mod")
            )
        )
        if (
            final_relevant != tuple(EXPECTED_RAW_RECORD_NAMES)
            or _stat_identity(os.fstat(source_dir_fd)) != directory_identity
        ):
            raise LinkClosureError("bound raw record set changed during validation")
        return receipt if matrix_bytes is not None else value
    except LinkClosureError as error:
        raise EvidenceError(
            "Kbuild link closure is invalid: {0}".format(error)
        ) from error


def _validate_phase2_build_evidence(
    directory: Path,
    records: dict[str, str],
    build_dir_fd: int | None = None,
) -> dict[str, Any]:
    matrix_path = directory / "kconfig-solver-matrix.json"
    matrix_bytes = _read_regular_evidence_bytes(
        matrix_path, "Kconfig solver matrix"
    )
    if _sha256_bytes(matrix_bytes) != records["kconfig-solver-matrix.json"]:
        raise EvidenceError("Kconfig solver matrix digest differs from SHA256SUMS")
    link_path = directory / "kbuild-link-closure.json"
    if build_dir_fd is None:
        try:
            matrix = validate_matrix_bytes(matrix_bytes)
        except SolverError as error:
            raise EvidenceError(
                "Kconfig solver matrix is invalid: {0}".format(error)
            ) from error
        try:
            link = check_kbuild_link_closure(
                str(directory),
                str(link_path),
                stage_lock_path=str(directory / "stage-lock.json"),
            )
        except LinkClosureError as error:
            raise EvidenceError(
                "Kbuild link closure is invalid: {0}".format(error)
            ) from error
    else:
        bound_matrix_bytes = _read_phase2_bound_file(
            build_dir_fd,
            "kconfig-solver-matrix.json",
            records["kconfig-solver-matrix.json"],
            16 << 20,
        )
        if bound_matrix_bytes != matrix_bytes:
            raise EvidenceError("bound Kconfig solver matrix bytes differ")
        isolated = _validate_link_closure_from_bound_snapshot(
            build_dir_fd, records, matrix_bytes=bound_matrix_bytes
        )
        if set(isolated) != {"link", "matrix"}:
            raise EvidenceError("isolated phase-2 receipt differs")
        link = isolated["link"]
        matrix = isolated["matrix"]
    link_bytes = _read_regular_evidence_bytes(link_path, "Kbuild link closure")
    if _sha256_bytes(link_bytes) != records["kbuild-link-closure.json"]:
        raise EvidenceError("Kbuild link closure digest differs from SHA256SUMS")

    resolved_bytes = _read_regular_evidence_bytes(
        directory / "resolved.config", "resolved build config"
    )
    seed = matrix["inputs"]["seed_config"]
    if seed != {
        "mode": "0644",
        "path": "seed.config",
        "sha256": records["resolved.config"],
        "size": len(resolved_bytes),
    }:
        raise EvidenceError("Kconfig solver seed does not bind the resolved build config")

    stage_lock = _load_json(directory / "stage-lock.json")
    stage_files = stage_lock.get("files")
    if type(stage_files) is not list:
        raise EvidenceError("stage lock files are malformed")
    kconfig_rows = [
        item
        for item in stage_files
        if type(item) is dict and item.get("path") == "Kconfig"
    ]
    if len(kconfig_rows) != 1 or set(kconfig_rows[0]) != {"path", "sha256"}:
        raise EvidenceError("stage lock must contain one exact Kconfig record")
    staged_kconfig = matrix["inputs"]["staged_kconfig"]
    if (
        staged_kconfig["sha256"] != kconfig_rows[0]["sha256"]
        or link["stage_lock"] is None
        or link["stage_lock"]["sha256"] != records["stage-lock.json"]
        or link["stage_lock"]["manifest_sha256"]
        != stage_lock.get("manifest_sha256")
    ):
        raise EvidenceError("solver, link closure, and stage-lock identities diverge")

    return {
        "kbuild_link_closure": {
            "claims": link["claims"],
            "module_count": len(link["modules"]),
            "raw_record_count": len(link["raw_record_names"]),
            "sha256": records["kbuild-link-closure.json"],
            "stage_lock_sha256": records["stage-lock.json"],
        },
        "kconfig_solver": {
            "claims": matrix["claims"],
            "counts": matrix["counts"],
            "limitations": matrix["limitations"],
            "sha256": records["kconfig-solver-matrix.json"],
            "status": matrix["status"],
        },
    }


def _validate_build_scope_artifacts(
    directory: Path, records: dict[str, str]
) -> dict[str, Any]:
    required = {
        "build.commands",
        "build.environment",
        "build.exit-code",
        "build.log",
        "build-log.exit-code",
        "build.phase",
        "built-module-artifacts.txt",
        "module-targets.txt",
    }
    if not required.issubset(records):
        raise EvidenceError(
            "build scope evidence is incomplete: {0}".format(
                sorted(required - set(records))
            )
        )
    if _read_text(directory / "build.exit-code", "build exit code") != "0\n":
        raise EvidenceError("exact build did not record a successful exit")
    if _read_text(directory / "build-log.exit-code", "build log exit code") != "0\n":
        raise EvidenceError("exact build log capture did not succeed")
    if _read_text(directory / "build.phase", "build phase") != "complete\n":
        raise EvidenceError("exact build did not reach its complete phase")
    _regular_evidence_file(directory / "build.log", "exact build log")
    build_environment = _read_text(
        directory / "build.environment", "reproducible build environment"
    )
    if build_environment != _reproducible_build_environment_text():
        raise EvidenceError("recorded reproducible build environment differs")

    targets = _read_text(directory / "module-targets.txt", "module target scope").splitlines()
    if targets != BUILD_MODULE_TARGETS:
        raise EvidenceError("recorded module target scope differs")
    built = _read_text(
        directory / "built-module-artifacts.txt", "built module artifact scope"
    ).splitlines()
    if built != sorted(BUILD_MODULE_TARGETS):
        raise EvidenceError("built module artifact scope differs")

    command_lines = _read_text(
        directory / "build.commands", "exact build commands"
    ).splitlines()
    if len(command_lines) != 3 or any(not line for line in command_lines):
        raise EvidenceError("exact build command record count differs")
    try:
        commands = [shlex.split(line, posix=True) for line in command_lines]
    except ValueError as error:
        raise EvidenceError("exact build command record is malformed") from error
    make_index = len(EXPECTED_KBUILD_ENV_COMMAND_PREFIX)
    if any(len(command) <= make_index + 7 for command in commands):
        raise EvidenceError("exact build command record is truncated")
    if any(
        command[:make_index] != EXPECTED_KBUILD_ENV_COMMAND_PREFIX
        or command[make_index] != "/usr/bin/make"
        for command in commands
    ):
        raise EvidenceError("exact build command environment boundary differs")

    sources = [command[make_index + 2] for command in commands]
    outputs = [
        command[make_index + 3][2:]
        if command[make_index + 3].startswith("O=")
        else ""
        for command in commands
    ]
    if len(set(sources)) != 1 or len(set(outputs)) != 1:
        raise EvidenceError("exact build commands use inconsistent trees")
    source = Path(sources[0])
    output = Path(outputs[0])
    selected_source = "linux-6.12.0-211.44.1.el10_2"
    if (
        not source.is_absolute()
        or ".." in source.parts
        or source.name != selected_source
        or source.parent.name != "native-rust-source"
        or not output.is_absolute()
        or ".." in output.parts
        or output.name != "native-rust-build"
    ):
        raise EvidenceError("exact build commands use an unexpected source/output identity")

    prefix = EXPECTED_KBUILD_ENV_COMMAND_PREFIX + [
        "/usr/bin/make",
        "-C",
        sources[0],
        "O=" + outputs[0],
        "ARCH=x86_64",
        "LLVM=1",
        "LOCALVERSION=" + EXPECTED_KERNEL_LOCALVERSION,
    ] + EXPECTED_KBUILD_MAKE_IDENTITY_ARGUMENTS
    expected_commands = [
        prefix + ["rustavailable"],
        prefix + ["-j2", "bzImage"],
        prefix + ["-j2"] + BUILD_MODULE_TARGETS,
    ]
    if commands != expected_commands:
        raise EvidenceError("exact build commands exceed the bounded target scope")
    return {
        "build_commands_sha256": records["build.commands"],
        "build_environment_sha256": records["build.environment"],
        "build_log_sha256": records["build.log"],
        "kernel_targets": BUILD_KERNEL_TARGETS,
        "module_targets": BUILD_MODULE_TARGETS,
    }


def _validate_build_workflow_provenance(
    build_dir: Path,
    records: dict[str, str],
    candidate_sha: str,
    runtime_identity: dict[str, Any] | None = None,
) -> None:
    receipt_raw = _read_bounded_regular_path_bytes(
        build_dir / "workflow-provenance.json",
        MAX_RUNTIME_TEXT_FILE_SIZE,
        "exact build workflow provenance",
    )
    workflow_raw = _read_bounded_regular_path_bytes(
        build_dir / "executed-build-workflow.yml",
        MAX_RUNTIME_TEXT_FILE_SIZE,
        "executed build workflow",
    )
    if (
        _sha256_bytes(receipt_raw) != records.get("workflow-provenance.json")
        or _sha256_bytes(workflow_raw)
        != records.get("executed-build-workflow.yml")
    ):
        raise EvidenceError("exact build workflow provenance manifest digest differs")
    receipt = _decode_canonical_json_bytes(
        receipt_raw, "exact build workflow provenance"
    )
    _require_keys(
        receipt,
        {
            "caller",
            "candidate",
            "claims",
            "defining_job",
            "direct_workflow_dispatch",
            "github_run_attempt",
            "github_run_id",
            "schema_version",
            "workflow_file_bytes_equal",
        },
        "exact build workflow provenance",
    )
    if type(receipt["schema_version"]) is not int or receipt["schema_version"] != 1:
        raise EvidenceError("exact build workflow provenance schema differs")
    if receipt["direct_workflow_dispatch"] is not False:
        raise EvidenceError("runtime build provenance unexpectedly claims direct dispatch")
    if receipt["workflow_file_bytes_equal"] is not True:
        raise EvidenceError("exact build workflow byte equality differs")
    expected_claims = {
        "credit_granted": False,
        "gate_passed": False,
        "production_ready": False,
        "release_ready": False,
    }
    if not _exact_typed_equal(receipt["claims"], expected_claims):
        raise EvidenceError("exact build workflow provenance claims differ")
    build_identity = EXPECTED_REPOSITORY_WORKFLOW_IDENTITIES["build_workflow"]
    build_path = ".github/workflows/native-rust-host-modules-exact-build.yml"
    if (
        len(workflow_raw) != build_identity["size"]
        or _sha256_bytes(workflow_raw) != build_identity["sha256"]
        or _git_blob_sha1(workflow_raw) != build_identity["git_blob_sha1"]
    ):
        raise EvidenceError("executed build workflow bytes differ")
    expected_candidate = {
        "sha": candidate_sha,
        "workflow_file_git_blob_sha1": build_identity["git_blob_sha1"],
        "workflow_file_path": build_path,
        "workflow_file_sha256": build_identity["sha256"],
    }
    if not _exact_typed_equal(receipt["candidate"], expected_candidate):
        raise EvidenceError("exact build candidate workflow provenance differs")
    defining = receipt["defining_job"]
    _require_keys(
        defining,
        {
            "evidence_file",
            "workflow_file_git_blob_sha1",
            "workflow_file_path",
            "workflow_file_sha256",
            "workflow_ref",
            "workflow_repository",
            "workflow_sha",
        },
        "exact build defining workflow provenance",
    )
    if (
        defining["evidence_file"] != "executed-build-workflow.yml"
        or defining["workflow_file_git_blob_sha1"]
        != build_identity["git_blob_sha1"]
        or defining["workflow_file_path"] != build_path
        or defining["workflow_file_sha256"] != build_identity["sha256"]
        or type(defining["workflow_sha"]) is not str
        or HEX40.fullmatch(defining["workflow_sha"]) is None
    ):
        raise EvidenceError("exact build defining workflow identity differs")
    caller = receipt["caller"]
    _require_keys(
        caller,
        {"event_name", "ref", "repository", "sha", "workflow_ref", "workflow_sha"},
        "exact build caller provenance",
    )
    if not _is_canonical_positive_decimal(receipt["github_run_id"]) or not (
        _is_canonical_positive_decimal(receipt["github_run_attempt"])
    ):
        raise EvidenceError("exact build provenance run identity differs")
    if runtime_identity is not None:
        _require_keys(
            runtime_identity,
            {
                "candidate_sha",
                "execution_workflow",
                "github_repository",
                "github_run_attempt",
                "github_run_id",
            },
            "runtime identity for build provenance",
        )
        execution = runtime_identity["execution_workflow"]
        expected_caller = {
            "event_name": execution["github_event_name"],
            "ref": execution["github_ref"],
            "repository": runtime_identity["github_repository"],
            "sha": execution["github_sha"],
            "workflow_ref": execution["github_workflow_ref"],
            "workflow_sha": execution["github_workflow_sha"],
        }
        expected_defining = {
            "evidence_file": "executed-build-workflow.yml",
            "workflow_file_git_blob_sha1": build_identity["git_blob_sha1"],
            "workflow_file_path": build_path,
            "workflow_file_sha256": build_identity["sha256"],
            "workflow_ref": "{0}/{1}@{2}".format(
                runtime_identity["github_repository"],
                build_path,
                execution["github_ref"],
            ),
            "workflow_repository": runtime_identity["github_repository"],
            "workflow_sha": execution["job_workflow_sha"],
        }
        if (
            runtime_identity["candidate_sha"] != candidate_sha
            or not _exact_typed_equal(caller, expected_caller)
            or not _exact_typed_equal(defining, expected_defining)
            or receipt["github_run_id"] != runtime_identity["github_run_id"]
            or receipt["github_run_attempt"]
            != runtime_identity["github_run_attempt"]
        ):
            raise EvidenceError("exact build/runtime workflow provenance diverges")


def _canonical_sha256(value: Any, label: str) -> str:
    if type(value) is not str or HEX64.fullmatch(value) is None:
        raise EvidenceError("{0} must be canonical lowercase SHA-256".format(label))
    return value


def _hash_subprocess_descriptor(
    descriptor: int,
    label: str,
    maximum_size: int,
) -> tuple[str, tuple[Any, ...]]:
    try:
        before = os.fstat(descriptor)
        identity = _stat_identity(before)
        if (
            not stat.S_ISREG(before.st_mode)
            or before.st_size < 1
            or before.st_size > maximum_size
        ):
            raise EvidenceError("{0} descriptor shape differs".format(label))
        digest = hashlib.sha256()
        offset = 0
        while offset < before.st_size:
            chunk = os.pread(
                descriptor, min(65536, before.st_size - offset), offset
            )
            if not chunk:
                raise EvidenceError("{0} descriptor ended early".format(label))
            digest.update(chunk)
            offset += len(chunk)
        if os.pread(descriptor, 1, offset):
            raise EvidenceError("{0} descriptor grew while reading".format(label))
        if _stat_identity(os.fstat(descriptor)) != identity:
            raise EvidenceError("{0} descriptor changed while reading".format(label))
        return digest.hexdigest(), identity
    except OSError as error:
        raise EvidenceError(
            "cannot hash {0} descriptor: {1}".format(label, error)
        ) from error


def _tool_execution(
    descriptor: int | None,
    label: str,
    fallback: str,
    expected_sha256: str | None = None,
) -> tuple[str, tuple[int, ...], dict[str, Any] | None]:
    if descriptor is None:
        if expected_sha256 is not None:
            raise EvidenceError(
                "{0} digest requires a retained descriptor".format(label)
            )
        return fallback, (), None
    expected_sha256 = _canonical_sha256(
        expected_sha256, "{0} expected digest".format(label)
    )
    if type(descriptor) is not int or descriptor < 3:
        raise EvidenceError(
            "{0} descriptor must be an open integer fd >= 3".format(label)
        )
    try:
        actual_sha256, identity = _hash_subprocess_descriptor(
            descriptor, label, MAX_TOOL_EXECUTABLE_FILE_SIZE
        )
        descriptor_status = os.fstat(descriptor)
        executable_status = os.stat("/proc/self/fd/{0}".format(descriptor))
    except OSError as error:
        raise EvidenceError(
            "{0} descriptor is unavailable: {1}".format(label, error)
        ) from error
    if (
        not stat.S_ISREG(descriptor_status.st_mode)
        or _stat_identity(descriptor_status) != identity
        or _stat_identity(executable_status) != identity
    ):
        raise EvidenceError(
            "{0} descriptor must identify one regular file".format(label)
        )
    if actual_sha256 != expected_sha256:
        raise EvidenceError("{0} descriptor digest differs".format(label))
    if stat.S_IMODE(descriptor_status.st_mode) & 0o111 == 0:
        raise EvidenceError(
            "{0} descriptor target is not executable".format(label)
        )
    bound = "/proc/self/fd/{0}".format(descriptor)
    return bound, (descriptor,), {
        "descriptor": descriptor,
        "identity": identity,
        "label": label,
        "maximum_size": MAX_TOOL_EXECUTABLE_FILE_SIZE,
        "path": bound,
        "sha256": expected_sha256,
    }


def _modinfo_execution(
    modinfo_fd: int | None,
    modinfo_sha256: str | None = None,
) -> tuple[str, tuple[int, ...], dict[str, Any] | None]:
    if modinfo_fd is not None and modinfo_sha256 != EXPECTED_MODINFO_SHA256:
        raise EvidenceError("modinfo expected digest differs from the Rocky lock")
    return _tool_execution(
        modinfo_fd,
        "modinfo",
        MODINFO_EXECUTABLE,
        expected_sha256=modinfo_sha256,
    )


def _nm_execution(
    nm_fd: int | None,
    nm_sha256: str | None = None,
) -> tuple[str, tuple[int, ...], dict[str, Any] | None]:
    return _tool_execution(
        nm_fd,
        "nm",
        NM_EXECUTABLE,
        expected_sha256=nm_sha256,
    )


def _subprocess_module_execution(
    module: Path,
    module_fd: int | None,
    expected_sha256: str | None = None,
) -> tuple[str, tuple[int, ...], dict[str, Any] | None]:
    if module_fd is None:
        if expected_sha256 is not None:
            raise EvidenceError("module digest requires a retained descriptor")
        return str(module), (), None
    expected_sha256 = _canonical_sha256(
        expected_sha256, "module expected digest"
    )
    if type(module_fd) is not int or module_fd < 3:
        raise EvidenceError("module descriptor must be an open integer fd >= 3")
    bound = "/proc/self/fd/{0}".format(module_fd)
    try:
        actual_sha256, identity = _hash_subprocess_descriptor(
            module_fd, "module", MAX_BUILD_EVIDENCE_FILE_SIZE
        )
        descriptor_status = os.fstat(module_fd)
        bound_status = os.stat(bound)
        module_status = module.stat()
    except OSError as error:
        raise EvidenceError(
            "module descriptor is unavailable: {0}".format(error)
        ) from error
    if (
        not stat.S_ISREG(descriptor_status.st_mode)
        or _stat_identity(descriptor_status) != identity
        or _stat_identity(bound_status) != identity
        or _stat_identity(module_status) != identity
    ):
        raise EvidenceError("module descriptor identity differs from its bound path")
    if actual_sha256 != expected_sha256:
        raise EvidenceError("module descriptor digest differs")
    return bound, (module_fd,), {
        "descriptor": module_fd,
        "identity": identity,
        "label": "module",
        "maximum_size": MAX_BUILD_EVIDENCE_FILE_SIZE,
        "path": str(module),
        "sha256": expected_sha256,
    }


def _recheck_subprocess_bindings(bindings: list[dict[str, Any]]) -> None:
    for binding in bindings:
        try:
            digest, read_identity = _hash_subprocess_descriptor(
                binding["descriptor"],
                binding["label"],
                binding["maximum_size"],
            )
            descriptor_status = os.fstat(binding["descriptor"])
            path_status = os.stat(binding["path"])
        except OSError as error:
            raise EvidenceError(
                "{0} descriptor changed during execution".format(binding["label"])
            ) from error
        if (
            digest != binding["sha256"]
            or read_identity != binding["identity"]
            or _stat_identity(descriptor_status) != binding["identity"]
            or _stat_identity(path_status) != binding["identity"]
        ):
            raise EvidenceError(
                "{0} descriptor changed during execution".format(binding["label"])
            )


def _run_field(
    module: Path,
    field: str,
    modinfo_fd: int | None = None,
    module_fd: int | None = None,
    modinfo_sha256: str | None = None,
    module_sha256: str | None = None,
) -> list[str]:
    executable, pass_fds, tool_binding = _modinfo_execution(
        modinfo_fd, modinfo_sha256
    )
    module_argument, module_fds, module_binding = _subprocess_module_execution(
        module, module_fd, module_sha256
    )
    pass_fds = tuple(sorted(set(pass_fds + module_fds)))
    bindings = [
        binding for binding in (tool_binding, module_binding) if binding is not None
    ]
    try:
        try:
            result = subprocess.run(
                ["modinfo", "-F", field, module_argument],
                check=False,
                env=dict(BOUND_ROCKY_TOOL_ENVIRONMENT),
                executable=executable,
                pass_fds=pass_fds,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
        except OSError as error:
            raise EvidenceError(
                "bound Rocky modinfo is unavailable: {0}".format(error)
            ) from error
        _recheck_subprocess_bindings(bindings)
        if result.returncode != 0:
            raise EvidenceError("modinfo failed for {0}:{1}".format(module.name, field))
        return [line for line in result.stdout.splitlines() if line]
    finally:
        _recheck_subprocess_bindings(bindings)


def _module_vermagic_release(
    module: Path,
    modinfo_fd: int | None = None,
    module_fd: int | None = None,
    modinfo_sha256: str | None = None,
    module_sha256: str | None = None,
) -> str:
    records = _run_field(
        module,
        "vermagic",
        modinfo_fd=modinfo_fd,
        module_fd=module_fd,
        modinfo_sha256=modinfo_sha256,
        module_sha256=module_sha256,
    )
    if len(records) != 1 or not records[0].split():
        raise EvidenceError("{0} vermagic record differs".format(module.name))
    release = records[0].split()[0]
    if release != EXPECTED_KERNEL_RELEASE:
        raise EvidenceError("{0} vermagic release differs".format(module.name))
    return release


def _nm(
    module: Path,
    arguments: list[str],
    nm_fd: int | None = None,
    module_fd: int | None = None,
    nm_sha256: str | None = None,
    module_sha256: str | None = None,
) -> str:
    executable, pass_fds, tool_binding = _nm_execution(nm_fd, nm_sha256)
    module_argument, module_fds, module_binding = _subprocess_module_execution(
        module, module_fd, module_sha256
    )
    pass_fds = tuple(sorted(set(pass_fds + module_fds)))
    bindings = [
        binding for binding in (tool_binding, module_binding) if binding is not None
    ]
    try:
        try:
            result = subprocess.run(
                [NM_EXECUTABLE] + arguments + [module_argument],
                check=False,
                env=dict(BOUND_ROCKY_TOOL_ENVIRONMENT),
                executable=executable,
                pass_fds=pass_fds,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
        except OSError as error:
            raise EvidenceError(
                "bound Rocky nm is unavailable: {0}".format(error)
            ) from error
        _recheck_subprocess_bindings(bindings)
        if result.returncode != 0:
            raise EvidenceError("nm failed for {0}".format(module.name))
        return result.stdout
    finally:
        _recheck_subprocess_bindings(bindings)


def _nm_symbol_records(output: str) -> list[tuple[str, str]]:
    records: list[tuple[str, str]] = []
    for line in output.splitlines():
        fields = line.split()
        if len(fields) >= 2 and re.fullmatch(r"[A-Za-z?]", fields[-2]):
            records.append((fields[-2], fields[-1]))
    return records


def _provider_metadata_symbols(records: list[tuple[str, str]]) -> list[str]:
    result: list[str] = []
    for _kind, name in records:
        for prefix in ("__ksymtab_", "__kstrtab_", "__kstrtabns_"):
            if name.startswith(prefix) and PROVIDER_SYMBOL_PATTERN.fullmatch(
                name[len(prefix) :]
            ):
                result.append(name)
                break
    return result


def _validate_module_symbol_graph(
    module: Path,
    item: dict[str, Any],
    nm_fd: int | None = None,
    module_fd: int | None = None,
    nm_sha256: str | None = None,
    module_sha256: str | None = None,
) -> dict[str, Any]:
    if "defined_provider_symbols" in item:
        expected_definitions = item["defined_provider_symbols"]
        expected_exports = item["gpl_exported_provider_symbols"]
        global_records = _nm_symbol_records(
            _nm(
                module,
                ["-g", "--defined-only"],
                nm_fd=nm_fd,
                module_fd=module_fd,
                nm_sha256=nm_sha256,
                module_sha256=module_sha256,
            )
        )
        global_provider_definitions = [
            name
            for kind, name in global_records
            if kind.isupper()
            and kind != "U"
            and PROVIDER_SYMBOL_PATTERN.fullmatch(name)
        ]
        if sorted(global_provider_definitions) != sorted(expected_definitions):
            raise EvidenceError("ihk provider global definitions differ")

        all_records = _nm_symbol_records(
            _nm(
                module,
                ["-a", "--defined-only"],
                nm_fd=nm_fd,
                module_fd=module_fd,
                nm_sha256=nm_sha256,
                module_sha256=module_sha256,
            )
        )
        all_names = [name for _kind, name in all_records]
        if "__ksymtab" in all_names:
            raise EvidenceError("ihk provider export uses non-GPL __ksymtab")
        expected_metadata = {
            "__{0}_{1}".format(kind, symbol)
            for kind in ("ksymtab", "kstrtab", "kstrtabns")
            for symbol in expected_exports
        }
        actual_metadata = _provider_metadata_symbols(all_records)
        if (
            sorted(actual_metadata) != sorted(expected_metadata)
            or all_names.count("__ksymtab_gpl") != 1
            or all_names.count("__ksymtab_strings") != 1
        ):
            raise EvidenceError("ihk provider GPL export metadata differs")
        namespace = item["provider_export_namespace"]
        if namespace.encode("ascii") + b"\0" not in module.read_bytes():
            raise EvidenceError("ihk provider export namespace bytes are absent")
        return {
            "defined_provider_symbols": list(expected_definitions),
            "gpl_exported_provider_symbols": list(expected_exports),
            "provider_export_namespace": namespace,
        }

    expected_undefined = item["undefined_provider_symbols"]
    undefined_records = _nm_symbol_records(
        _nm(
            module,
            ["-u"],
            nm_fd=nm_fd,
            module_fd=module_fd,
            nm_sha256=nm_sha256,
            module_sha256=module_sha256,
        )
    )
    undefined_provider_symbols = [
        name
        for kind, name in undefined_records
        if kind == "U" and PROVIDER_SYMBOL_PATTERN.fullmatch(name)
    ]
    if sorted(undefined_provider_symbols) != sorted(expected_undefined):
        raise EvidenceError(
            "{0} provider undefined relocation graph differs".format(item["file"])
        )
    return {"undefined_provider_symbols": list(expected_undefined)}


def _validate_resolved_config(path: Path, requirements: dict[str, Any]) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise EvidenceError("resolved kernel config must be a regular file")
    lines = _read_text(path, "resolved kernel config").splitlines()
    for symbol in requirements["enabled"]:
        matches = [
            line
            for line in lines
            if line.startswith(symbol + "=") or line == "# {0} is not set".format(symbol)
        ]
        if matches != ["{0}=y".format(symbol)]:
            raise EvidenceError("runtime kernel lacks required built-in: {0}".format(symbol))
    for symbol in requirements["disabled"]:
        matches = [
            line
            for line in lines
            if line.startswith(symbol + "=") or line == "# {0} is not set".format(symbol)
        ]
        if matches != ["# {0} is not set".format(symbol)]:
            raise EvidenceError("runtime kernel enables forbidden option: {0}".format(symbol))
    modules = requirements["modules"]
    if not isinstance(modules, dict) or modules != {
        "CONFIG_MCKERNEL_IHK_RUST": "m",
        "CONFIG_MCKERNEL_IHK_SMP_X86_64_RUST": "m",
        "CONFIG_MCKERNEL_MCCTRL_RUST": "m",
    }:
        raise EvidenceError("runtime native module config contract differs")
    for symbol, expected in modules.items():
        matches = [
            line
            for line in lines
            if line.startswith(symbol + "=") or line == "# {0} is not set".format(symbol)
        ]
        if matches != ["{0}={1}".format(symbol, expected)]:
            raise EvidenceError(
                "runtime kernel lacks required modular setting: {0}".format(symbol)
            )
    return {
        "disabled": list(requirements["disabled"]),
        "enabled": list(requirements["enabled"]),
        "modules": dict(modules),
    }


def _state_modules(lines: list[str], label: str) -> dict[str, str]:
    begin = "{0} STATE_BEGIN label={1}".format(PROTOCOL, label)
    end = "{0} STATE_END label={1}".format(PROTOCOL, label)
    begin_positions = [index for index, line in enumerate(lines) if line == begin]
    end_positions = [index for index, line in enumerate(lines) if line == end]
    if len(begin_positions) != 1 or len(end_positions) != 1:
        raise EvidenceError("runtime state frame differs: {0}".format(label))
    start = begin_positions[0]
    finish = end_positions[0]
    if start >= finish:
        raise EvidenceError("runtime state frame order differs: {0}".format(label))
    records: dict[str, str] = {}
    for line in lines[start + 1 : finish]:
        prefix = "{0} MODULE ".format(PROTOCOL)
        if not line.startswith(prefix):
            if line.startswith(PROTOCOL):
                raise EvidenceError("nested or malformed runtime state frame")
            continue
        fields = line[len(prefix) :].split(maxsplit=1)
        if len(fields) != 2 or fields[0] in records:
            raise EvidenceError("malformed or duplicate runtime module state")
        records[fields[0]] = fields[1]
    return records


def _provider_users(raw: str, label: str) -> set[str]:
    if raw == "-":
        return set()
    if re.fullmatch(r"(?:[A-Za-z0-9_]+,)+", raw) is None:
        raise EvidenceError("provider user grammar differs for {0}".format(label))
    values = raw[:-1].split(",")
    if len(values) != len(set(values)):
        raise EvidenceError("provider user list contains duplicates for {0}".format(label))
    return set(values)


def _refcount_record(text: str, phase: str) -> tuple[int, set[str]]:
    expression = re.compile(
        r"^"
        + re.escape(PROTOCOL)
        + r" REFCOUNT module=ihk phase="
        + re.escape(phase)
        + r" references=([0-9]+) users=([^\s]+)$",
        re.MULTILINE,
    )
    records = expression.findall(text)
    if len(records) != 1:
        raise EvidenceError("provider refcount record differs for {0}".format(phase))
    references = int(records[0][0])
    users = _provider_users(records[0][1], "refcount {0}".format(phase))
    return references, users


def _state_module_record(
    modules: dict[str, str], module: str, label: str
) -> dict[str, Any]:
    fields = modules.get(module, "").split()
    if (
        len(fields) not in (5, 6)
        or re.fullmatch(r"[1-9][0-9]*", fields[0]) is None
        or re.fullmatch(r"(?:0|[1-9][0-9]*)", fields[1]) is None
        or fields[3] != "Live"
        or re.fullmatch(r"0x[0-9A-Fa-f]+", fields[4]) is None
        or (len(fields) == 6 and re.fullmatch(r"\([A-Z]+\)", fields[5]) is None)
    ):
        raise EvidenceError(
            "{0} /proc/modules state differs for {1}".format(module, label)
        )
    return {
        "size": int(fields[0]),
        "references": int(fields[1]),
        "users_text": fields[2],
        "users": frozenset(
            _provider_users(fields[2], "/proc/modules {0} {1}".format(label, module))
        ),
        "state": fields[3],
        "address": fields[4],
        "taints": None if len(fields) == 5 else fields[5],
    }


def _unique_exact_line(lines: list[str], record: str, label: str) -> int:
    positions = [index for index, line in enumerate(lines) if line == record]
    if len(positions) != 1:
        raise EvidenceError("{0} runtime record differs".format(label))
    return positions[0]


def _unique_prefixed_line(lines: list[str], prefix: str, label: str) -> int:
    positions = [index for index, line in enumerate(lines) if line.startswith(prefix)]
    if len(positions) != 1:
        raise EvidenceError("{0} runtime record differs".format(label))
    return positions[0]


def _unique_kernel_diagnostic(
    lines: list[str], body_pattern: str, label: str
) -> tuple[int, re.Match[str]]:
    expression = re.compile(
        r"^(?:\[\s*[0-9]+(?:\.[0-9]+)?\]\s+)?" + body_pattern + r"$"
    )
    matches = [
        (index, match)
        for index, line in enumerate(lines)
        for match in (expression.fullmatch(line),)
        if match is not None
    ]
    if len(matches) != 1:
        raise EvidenceError("{0} diagnostic is missing or duplicated".format(label))
    return matches[0]


def _kernel_diagnostic_matches(
    lines: list[str], body_pattern: str, label: str, expected_count: int
) -> list[tuple[int, re.Match[str]]]:
    expression = re.compile(
        r"^(?:\[\s*[0-9]+(?:\.[0-9]+)?\]\s+)?" + body_pattern + r"$"
    )
    matches = [
        (index, match)
        for index, line in enumerate(lines)
        for match in (expression.fullmatch(line),)
        if match is not None
    ]
    if len(matches) != expected_count:
        raise EvidenceError(
            "{0} diagnostic count differs: {1} != {2}".format(
                label, len(matches), expected_count
            )
        )
    return matches


def _provider_open_events(lines: list[str]) -> list[tuple[int, str]]:
    prefix = re.compile(r"^(?:\[\s*[0-9]+(?:\.[0-9]+)?\]\s+)?")
    result = []
    for index, line in enumerate(lines):
        body = prefix.sub("", line, count=1)
        if body == PROVIDER_OPEN_ACQUIRE_DIAGNOSTIC:
            result.append((index, "acquire"))
        elif body == PROVIDER_OPEN_RELEASE_DIAGNOSTIC:
            result.append((index, "release"))
    return result


def validate_serial(serial_path: Path, kernel_release: str) -> dict[str, Any]:
    if serial_path.is_symlink() or not serial_path.is_file():
        raise EvidenceError("serial log must be a regular non-symlink file")
    data = serial_path.read_bytes()
    if not data:
        raise EvidenceError("serial log is empty")
    try:
        text = data.decode("utf-8")
    except UnicodeError as error:
        raise EvidenceError("serial log is not strict UTF-8") from error
    text = text.replace("\r\n", "\n")
    if (
        "\r" in text
        or "\0" in text
        or "\x85" in text
        or "\u2028" in text
        or "\u2029" in text
        or any(ord(character) < 32 and character != "\n" for character in text)
        or any(0x7F <= ord(character) <= 0x9F for character in text)
    ):
        raise EvidenceError("serial log contains a noncanonical control character")
    lines = text.split("\n")
    allowed_provider_diagnostic = re.compile(
        r"^(?:\[\s*[0-9]+(?:\.[0-9]+)?\]\s+)?(?:"
        + re.escape(PROVIDER_CALLBACK_INIT_DIAGNOSTIC)
        + r"|"
        + re.escape(PROVIDER_LEASE_ATTACH_DIAGNOSTIC)
        + r"|"
        + re.escape(PROVIDER_CALLBACK_EXIT_DIAGNOSTIC)
        + r"|"
        + PROVIDER_LEASE_DETACH_DIAGNOSTIC_PATTERN
        + r"|"
        + re.escape(PROVIDER_REGISTRY_EMPTY_DIAGNOSTIC)
        + r"|"
        + re.escape(PROVIDER_OPEN_ACQUIRE_DIAGNOSTIC)
        + r"|"
        + re.escape(PROVIDER_OPEN_RELEASE_DIAGNOSTIC)
        + r")$"
    )
    lifecycle_bodies = {
        "ihk load": "ihk: lifecycle=load version=1.7.0rc4 abi=1 parameters=0 dependencies=0",
        "smp load": (
            "ihk_smp_x86_64: lifecycle=load parameters=6 dependency=ihk "
            "import_namespace=MCKERNEL_IHK_V1"
        ),
        "mcctrl load": (
            "mcctrl: lifecycle=load foundation=1 parameters=0 declared_dependencies=1 "
            "ihk_import=source-bound-anchor binfmt=blocked-no-safe-rust-api"
        ),
        "mcctrl unload": (
            "mcctrl: lifecycle=unload foundation=1 parameters=0 declared_dependencies=1 "
            "ihk_import=source-bound-anchor binfmt=blocked-no-safe-rust-api"
        ),
        "smp unload": (
            "ihk_smp_x86_64: lifecycle=unload parameters=6 dependency=ihk "
            "import_namespace=MCKERNEL_IHK_V1"
        ),
        "ihk unload": (
            "ihk: lifecycle=unload version=1.7.0rc4 abi=1 parameters=0 dependencies=0"
        ),
    }
    allowed_lifecycle_diagnostic = re.compile(
        r"^(?:\[\s*[0-9]+(?:\.[0-9]+)?\]\s+)?(?:"
        + "|".join(re.escape(body) for body in lifecycle_bodies.values())
        + r")$"
    )
    for line in lines:
        if (
            "provider_callback" in line
            or "provider_lease" in line
            or "provider_registry" in line
            or "provider_open" in line
        ):
            if any(marker in line for marker in PROVIDER_LEASE_FORBIDDEN_DIAGNOSTICS):
                raise EvidenceError(
                    "provider lease runtime contains a fail-closed diagnostic"
                )
            if (
                RAW_OPAQUE_TOKEN_FIELD.search(line) is not None
                or RAW_PROVIDER_RECEIPT_FIELD.search(line) is not None
            ):
                raise EvidenceError(
                    "provider lease runtime discloses a raw opaque token or receipt"
                )
            if allowed_provider_diagnostic.fullmatch(line) is None:
                raise EvidenceError("provider lease runtime diagnostic grammar differs")
        if any(
            prefix in line
            for prefix in (
                "ihk: lifecycle=",
                "ihk_smp_x86_64: lifecycle=",
                "mcctrl: lifecycle=",
            )
        ) and allowed_lifecycle_diagnostic.fullmatch(line) is None:
            raise EvidenceError("native lifecycle diagnostic grammar differs")
        for label, expression in SERIAL_FATAL_PATTERNS:
            if expression.search(line) is not None:
                raise EvidenceError(
                    "serial log contains fatal diagnostic: {0}".format(label)
                )

    complete = "{0} COMPLETE status=technical-capture-unreviewed credit=forbidden".format(
        PROTOCOL
    )
    if lines.count(complete) != 1 or any(
        line.startswith("{0} INCOMPLETE".format(PROTOCOL)) for line in lines
    ):
        raise EvidenceError("serial protocol is incomplete or duplicated")
    release = "{0} KERNEL_RELEASE actual={1} expected={1}".format(
        PROTOCOL, kernel_release
    )
    if lines.count(release) != 1:
        raise EvidenceError("guest did not boot the exact built kernel release")

    exact_runtime_markers = [
        ("begin", "{0} BEGIN".format(PROTOCOL)),
        ("kernel release", release),
        ("initial state begin", "{0} STATE_BEGIN label=initial-clean".format(PROTOCOL)),
        ("initial state end", "{0} STATE_END label=initial-clean".format(PROTOCOL)),
        ("ihk load", "{0} LOAD module=ihk status=ok".format(PROTOCOL)),
        ("smp load", "{0} LOAD module=ihk_smp_x86_64 status=ok".format(PROTOCOL)),
        ("mcctrl load", "{0} LOAD module=mcctrl status=ok".format(PROTOCOL)),
        ("all-loaded state begin", "{0} STATE_BEGIN label=all-loaded".format(PROTOCOL)),
        ("all-loaded state end", "{0} STATE_END label=all-loaded".format(PROTOCOL)),
        (
            "mcd0 sequential",
            "{0} MCD0 OPEN_CLOSE mode=sequential count=4 status=ok".format(PROTOCOL),
        ),
        (
            "mcd0 overlapping",
            "{0} MCD0 OPEN_CLOSE mode=overlapping count=8 status=ok".format(PROTOCOL),
        ),
        (
            "mcd0 native ioctl",
            "{0} MCD0 IOCTL abi=x86_64 expected_errno=EINVAL status=ok".format(
                PROTOCOL
            ),
        ),
        (
            "mcd0 compat ioctl",
            "{0} MCD0 IOCTL abi=i386 expected_errno=EINVAL status=ok".format(
                PROTOCOL
            ),
        ),
        (
            "mcd0 negative output begin",
            "{0} MCD0 NEGATIVE_OUTPUT_BEGIN".format(PROTOCOL),
        ),
        (
            "mcd0 negative output end",
            "{0} MCD0 NEGATIVE_OUTPUT_END".format(PROTOCOL),
        ),
        (
            "mcd0 close",
            "{0} MCD0 CLOSE phase=after-module-owner-negative status=ok".format(
                PROTOCOL
            ),
        ),
        ("negative output begin", "{0} NEGATIVE_OUTPUT_BEGIN".format(PROTOCOL)),
        ("negative output end", "{0} NEGATIVE_OUTPUT_END".format(PROTOCOL)),
        (
            "after-negative state begin",
            "{0} STATE_BEGIN label=after-negative".format(PROTOCOL),
        ),
        (
            "after-negative state end",
            "{0} STATE_END label=after-negative".format(PROTOCOL),
        ),
        ("mcctrl unload", "{0} UNLOAD module=mcctrl status=ok".format(PROTOCOL)),
        (
            "smp unload",
            "{0} UNLOAD module=ihk_smp_x86_64 status=ok".format(PROTOCOL),
        ),
        ("mcd0 node removed", "{0} MCD0 NODE status=removed".format(PROTOCOL)),
        ("ihk unload", "{0} UNLOAD module=ihk status=ok".format(PROTOCOL)),
        (
            "first-cycle state begin",
            "{0} STATE_BEGIN label=first-cycle-clean".format(PROTOCOL),
        ),
        (
            "first-cycle state end",
            "{0} STATE_END label=first-cycle-clean".format(PROTOCOL),
        ),
        ("reload begin", "{0} RELOAD cycle=1 phase=begin".format(PROTOCOL)),
        (
            "reload ihk",
            "{0} RELOAD_LOAD cycle=1 module=ihk status=ok".format(PROTOCOL),
        ),
        (
            "reload smp",
            "{0} RELOAD_LOAD cycle=1 module=ihk_smp_x86_64 status=ok".format(
                PROTOCOL
            ),
        ),
        (
            "reload mcctrl",
            "{0} RELOAD_LOAD cycle=1 module=mcctrl status=ok".format(PROTOCOL),
        ),
        (
            "reload unload mcctrl",
            "{0} RELOAD_UNLOAD cycle=1 module=mcctrl status=ok".format(PROTOCOL),
        ),
        (
            "reload unload smp",
            "{0} RELOAD_UNLOAD cycle=1 module=ihk_smp_x86_64 status=ok".format(
                PROTOCOL
            ),
        ),
        (
            "reload unload ihk",
            "{0} RELOAD_UNLOAD cycle=1 module=ihk status=ok".format(PROTOCOL),
        ),
        ("reload complete", "{0} RELOAD cycle=1 status=ok".format(PROTOCOL)),
        ("final state begin", "{0} STATE_BEGIN label=final-clean".format(PROTOCOL)),
        ("final state end", "{0} STATE_END label=final-clean".format(PROTOCOL)),
        ("dmesg begin", "{0} DMESG_BEGIN".format(PROTOCOL)),
        ("dmesg end", "{0} DMESG_END".format(PROTOCOL)),
        ("complete", complete),
    ]
    marker_positions = {
        label: _unique_exact_line(lines, marker, label)
        for label, marker in exact_runtime_markers
    }

    prefixed_runtime_markers = [
        (
            "all-loaded refcount",
            "{0} REFCOUNT module=ihk phase=all-loaded references=".format(PROTOCOL),
        ),
        (
            "negative unload",
            "{0} NEGATIVE operation=unload-provider-first status=".format(PROTOCOL),
        ),
        (
            "after-negative refcount",
            "{0} REFCOUNT module=ihk phase=after-negative references=".format(PROTOCOL),
        ),
        (
            "after-mcctrl refcount",
            "{0} REFCOUNT module=ihk phase=after-mcctrl-unload references=".format(
                PROTOCOL
            ),
        ),
        (
            "after-smp refcount",
            "{0} REFCOUNT module=ihk phase=after-smp-unload references=".format(
                PROTOCOL
            ),
        ),
        (
            "reload refcount",
            "{0} REFCOUNT module=ihk phase=reload-all-loaded references=".format(
                PROTOCOL
            ),
        ),
    ]
    marker_positions.update(
        {
            label: _unique_prefixed_line(lines, prefix, label)
            for label, prefix in prefixed_runtime_markers
        }
    )

    def unique_regex_line(expression: re.Pattern[str], label: str):
        matches = [
            (index, match)
            for index, line in enumerate(lines)
            for match in (expression.fullmatch(line),)
            if match is not None
        ]
        if len(matches) != 1:
            raise EvidenceError("{0} runtime record differs".format(label))
        return matches[0]

    mcd0_present_expression = re.compile(
        r"^"
        + re.escape(PROTOCOL)
        + r" MCD0 NODE status=present dev=(10:(?:0|[1-9][0-9]*))$"
    )
    mcd0_present_position, mcd0_present = unique_regex_line(
        mcd0_present_expression,
        "mcd0 node present",
    )
    marker_positions["mcd0 node present"] = mcd0_present_position
    mcd0_negative_expression = re.compile(
        r"^"
        + re.escape(PROTOCOL)
        + r" MCD0 NEGATIVE operation=unload-smp-with-open-file status=(1)$"
    )
    mcd0_negative_position, mcd0_negative = unique_regex_line(
        mcd0_negative_expression,
        "mcd0 module-owner negative",
    )
    marker_positions["mcd0 negative"] = mcd0_negative_position
    mcd0_reload_expression = re.compile(
        r"^"
        + re.escape(PROTOCOL)
        + r" MCD0 RELOAD cycle=1 dev=(10:(?:0|[1-9][0-9]*)) "
        r"open_close=1 ioctl_x86_64=EINVAL ioctl_i386=EINVAL status=ok$"
    )
    mcd0_reload_position, mcd0_reload = unique_regex_line(
        mcd0_reload_expression,
        "mcd0 reload",
    )
    marker_positions["mcd0 reload"] = mcd0_reload_position
    first_minor = int(mcd0_present.group(1).split(":", 1)[1])
    reload_minor = int(mcd0_reload.group(1).split(":", 1)[1])
    if first_minor >= (1 << 20) or reload_minor >= (1 << 20):
        raise EvidenceError("mcd0 dynamic misc minor is out of range")

    provider_negative_expression = re.compile(
        r"^"
        + re.escape(PROTOCOL)
        + r" NEGATIVE operation=unload-provider-first status=(1)$"
    )
    refcount_expression = re.compile(
        r"^"
        + re.escape(PROTOCOL)
        + r" REFCOUNT module=ihk phase="
        r"(?:all-loaded|after-negative|after-mcctrl-unload|after-smp-unload|"
        r"reload-all-loaded) references=(?:0|[1-9][0-9]*) "
        r"users=(?:-|(?:[A-Za-z0-9_]+,)+)$"
    )
    module_expression = re.compile(
        r"^"
        + re.escape(PROTOCOL)
        + r" MODULE (?:ihk|ihk_smp_x86_64|mcctrl) [1-9][0-9]* "
        r"(?:0|[1-9][0-9]*) (?:-|(?:[A-Za-z0-9_]+,)+) Live "
        r"0x[0-9A-Fa-f]+(?: \([A-Z]+\))?$"
    )
    exact_protocol_lines = {marker for _label, marker in exact_runtime_markers}
    dynamic_protocol_expressions = (
        mcd0_present_expression,
        mcd0_negative_expression,
        mcd0_reload_expression,
        provider_negative_expression,
        refcount_expression,
        module_expression,
    )
    for line in lines:
        if PROTOCOL not in line:
            continue
        if not line.startswith(PROTOCOL + " "):
            raise EvidenceError("prefixed or embedded runtime protocol record")
        if line in exact_protocol_lines or any(
            expression.fullmatch(line) is not None
            for expression in dynamic_protocol_expressions
        ):
            continue
        raise EvidenceError("unrecognized runtime protocol record")

    if marker_positions["complete"] != marker_positions["dmesg end"] + 1:
        raise EvidenceError("runtime completion is not adjacent to bounded dmesg")
    state_ranges = [
        (
            marker_positions["{0} state begin".format(label)],
            marker_positions["{0} state end".format(label)],
        )
        for label in ("initial", "all-loaded", "after-negative", "first-cycle", "final")
    ]
    for index, line in enumerate(lines):
        if module_expression.fullmatch(line) is not None and not any(
            start < index < finish for start, finish in state_ranges
        ):
            raise EvidenceError("runtime module record lies outside a state frame")
    ordered_marker_labels = [
        "begin",
        "kernel release",
        "initial state begin",
        "initial state end",
        "ihk load",
        "smp load",
        "mcctrl load",
        "all-loaded state begin",
        "all-loaded state end",
        "all-loaded refcount",
        "mcd0 node present",
        "mcd0 sequential",
        "mcd0 overlapping",
        "mcd0 native ioctl",
        "mcd0 compat ioctl",
        "mcd0 negative",
        "mcd0 negative output begin",
        "mcd0 negative output end",
        "mcd0 close",
        "negative unload",
        "negative output begin",
        "negative output end",
        "after-negative refcount",
        "after-negative state begin",
        "after-negative state end",
        "mcctrl unload",
        "after-mcctrl refcount",
        "smp unload",
        "mcd0 node removed",
        "after-smp refcount",
        "ihk unload",
        "first-cycle state begin",
        "first-cycle state end",
        "reload begin",
        "reload ihk",
        "reload smp",
        "reload mcctrl",
        "reload refcount",
        "mcd0 reload",
        "reload unload mcctrl",
        "reload unload smp",
        "reload unload ihk",
        "reload complete",
        "final state begin",
        "final state end",
        "dmesg begin",
        "dmesg end",
        "complete",
    ]
    positions = [marker_positions[label] for label in ordered_marker_labels]
    if len(set(positions)) != len(positions) or positions != sorted(positions):
        raise EvidenceError("serial runtime markers are missing or out of order")

    if int(mcd0_negative.group(1)) != 1:
        raise EvidenceError("mcd0 module-owner unload negative test did not fail")
    mcd0_output = lines[
        marker_positions["mcd0 negative output begin"] + 1 :
        marker_positions["mcd0 negative output end"]
    ]
    if mcd0_output != ["rmmod: ERROR: Module ihk_smp_x86_64 is in use"]:
        raise EvidenceError("mcd0 module-owner unload lacks the exact in-use diagnostic")

    negative_expression = re.compile(
        r"^"
        + re.escape(PROTOCOL)
        + r" NEGATIVE operation=unload-provider-first status=([0-9]+)$"
    )
    negative_records = [
        match
        for line in lines
        for match in (negative_expression.fullmatch(line),)
        if match is not None
    ]
    if len(negative_records) != 1 or int(negative_records[0].group(1)) != 1:
        raise EvidenceError("provider-first unload negative test did not fail")
    negative_lines = lines[
        marker_positions["negative output begin"] + 1 :
        marker_positions["negative output end"]
    ]
    negative_diagnostic = re.compile(
        r"^rmmod: ERROR: Module ihk is in use by: "
        r"(?:mcctrl ihk_smp_x86_64|ihk_smp_x86_64 mcctrl)$"
    )
    if len(negative_lines) != 1 or negative_diagnostic.fullmatch(
        negative_lines[0]
    ) is None:
        raise EvidenceError("provider-first unload lacks the in-use diagnostic")

    expected_modules = {"ihk", "ihk_smp_x86_64", "mcctrl"}
    initial = _state_modules(lines, "initial-clean")
    all_loaded = _state_modules(lines, "all-loaded")
    after_negative = _state_modules(lines, "after-negative")
    first_cycle = _state_modules(lines, "first-cycle-clean")
    final = _state_modules(lines, "final-clean")
    if initial or first_cycle or final:
        raise EvidenceError("clean runtime state retains a native module")
    if set(all_loaded) != expected_modules or set(after_negative) != expected_modules:
        raise EvidenceError("loaded module state differs before or after the negative test")

    parsed_states = {
        label: {
            module: _state_module_record(records, module, label)
            for module in sorted(expected_modules)
        }
        for label, records in (
            ("all-loaded", all_loaded),
            ("after-negative", after_negative),
        )
    }
    expected_module_dependencies = {
        "ihk": (2, frozenset(("ihk_smp_x86_64", "mcctrl"))),
        "ihk_smp_x86_64": (0, frozenset()),
        "mcctrl": (0, frozenset()),
    }
    for label, records in parsed_states.items():
        for module, expected in expected_module_dependencies.items():
            actual = (records[module]["references"], records[module]["users"])
            if actual != expected:
                raise EvidenceError(
                    "{0} /proc/modules dependencies differ for {1}".format(
                        module, label
                    )
                )
    if parsed_states["all-loaded"] != parsed_states["after-negative"]:
        raise EvidenceError("negative test changed the complete /proc/modules state")

    expected_refcounts = {
        "all-loaded": (2, {"ihk_smp_x86_64", "mcctrl"}),
        "after-negative": (2, {"ihk_smp_x86_64", "mcctrl"}),
        "after-mcctrl-unload": (1, {"ihk_smp_x86_64"}),
        "after-smp-unload": (0, set()),
        "reload-all-loaded": (2, {"ihk_smp_x86_64", "mcctrl"}),
    }
    for phase, expected in expected_refcounts.items():
        actual = _refcount_record(text, phase)
        if actual != expected:
            raise EvidenceError(
                "provider refcount/users differ for {0}: {1}".format(phase, actual)
            )
    for label in ("all-loaded", "after-negative"):
        provider = parsed_states[label]["ihk"]
        if (provider["references"], set(provider["users"])) != expected_refcounts[label]:
            raise EvidenceError("{0} /proc/modules provider state differs".format(label))

    expected_first_open_trace = (
        ["acquire", "release"] * MCD0_SEQUENTIAL_OPEN_COUNT
        + ["acquire"] * MCD0_OVERLAPPING_OPEN_COUNT
        + ["release"] * MCD0_OVERLAPPING_OPEN_COUNT
        + ["acquire", "release"] * 2
        + ["acquire", "release"]
    )
    expected_reload_open_trace = ["acquire", "release"] * MCD0_RELOAD_OPEN_COUNT
    expected_open_trace = expected_first_open_trace + expected_reload_open_trace
    dmesg_start = marker_positions["dmesg begin"]
    dmesg_finish = marker_positions["dmesg end"]
    live_events = _provider_open_events(lines[:dmesg_start])
    dmesg_lines = lines[dmesg_start + 1 : dmesg_finish]
    dmesg_events = _provider_open_events(dmesg_lines)
    if [kind for _position, kind in live_events] != expected_open_trace:
        raise EvidenceError("live provider open/release trace differs")
    if [kind for _position, kind in dmesg_events] != expected_open_trace:
        raise EvidenceError("dmesg provider open/release trace differs")

    def live_events_between(start: int, finish: int) -> list[str]:
        return [kind for position, kind in live_events if start < position < finish]

    live_sections = (
        (
            "sequential",
            marker_positions["mcd0 node present"],
            marker_positions["mcd0 sequential"],
            ["acquire", "release"] * MCD0_SEQUENTIAL_OPEN_COUNT,
        ),
        (
            "overlapping",
            marker_positions["mcd0 sequential"],
            marker_positions["mcd0 overlapping"],
            ["acquire"] * MCD0_OVERLAPPING_OPEN_COUNT
            + ["release"] * MCD0_OVERLAPPING_OPEN_COUNT,
        ),
        (
            "native ioctl",
            marker_positions["mcd0 overlapping"],
            marker_positions["mcd0 native ioctl"],
            ["acquire", "release"],
        ),
        (
            "compat ioctl",
            marker_positions["mcd0 native ioctl"],
            marker_positions["mcd0 compat ioctl"],
            ["acquire", "release"],
        ),
        (
            "held open",
            marker_positions["mcd0 compat ioctl"],
            marker_positions["mcd0 negative"],
            ["acquire"],
        ),
        (
            "held close",
            marker_positions["mcd0 negative output end"],
            marker_positions["mcd0 close"],
            ["release"],
        ),
        (
            "reload",
            marker_positions["reload refcount"],
            marker_positions["mcd0 reload"],
            expected_reload_open_trace,
        ),
    )
    for label, start, finish, expected in live_sections:
        if live_events_between(start, finish) != expected:
            raise EvidenceError("{0} provider open/release trace differs".format(label))

    lifecycle_positions = {
        label: [position for position, _match in _kernel_diagnostic_matches(
            dmesg_lines, re.escape(body), label, 2
        )]
        for label, body in lifecycle_bodies.items()
    }
    provider_positions = {
        "init": [position for position, _match in _kernel_diagnostic_matches(
            dmesg_lines,
            re.escape(PROVIDER_CALLBACK_INIT_DIAGNOSTIC),
            "provider init callback",
            2,
        )],
        "attach": [position for position, _match in _kernel_diagnostic_matches(
            dmesg_lines,
            re.escape(PROVIDER_LEASE_ATTACH_DIAGNOSTIC),
            "provider lease attach",
            2,
        )],
        "exit": [position for position, _match in _kernel_diagnostic_matches(
            dmesg_lines,
            re.escape(PROVIDER_CALLBACK_EXIT_DIAGNOSTIC),
            "provider exit callback",
            2,
        )],
        "detach": [position for position, _match in _kernel_diagnostic_matches(
            dmesg_lines,
            PROVIDER_LEASE_DETACH_DIAGNOSTIC_PATTERN,
            "provider lease detach",
            2,
        )],
        "registry empty": [position for position, _match in _kernel_diagnostic_matches(
            dmesg_lines,
            re.escape(PROVIDER_REGISTRY_EMPTY_DIAGNOSTIC),
            "provider registry empty",
            2,
        )],
    }
    for cycle in range(2):
        cycle_open_positions = [
            position
            for position, _kind in dmesg_events
            if lifecycle_positions["mcctrl load"][cycle]
            < position
            < lifecycle_positions["mcctrl unload"][cycle]
        ]
        expected_cycle_trace = (
            expected_first_open_trace if cycle == 0 else expected_reload_open_trace
        )
        cycle_open_trace = [
            kind
            for position, kind in dmesg_events
            if lifecycle_positions["mcctrl load"][cycle]
            < position
            < lifecycle_positions["mcctrl unload"][cycle]
        ]
        if cycle_open_trace != expected_cycle_trace:
            raise EvidenceError("provider open/release lifecycle cycle differs")
        ordered_cycle = [
            lifecycle_positions["ihk load"][cycle],
            provider_positions["init"][cycle],
            provider_positions["attach"][cycle],
            lifecycle_positions["smp load"][cycle],
            lifecycle_positions["mcctrl load"][cycle],
        ] + cycle_open_positions + [
            lifecycle_positions["mcctrl unload"][cycle],
            provider_positions["exit"][cycle],
            provider_positions["detach"][cycle],
            lifecycle_positions["smp unload"][cycle],
            provider_positions["registry empty"][cycle],
            lifecycle_positions["ihk unload"][cycle],
        ]
        if ordered_cycle != sorted(ordered_cycle) or len(ordered_cycle) != len(
            set(ordered_cycle)
        ):
            raise EvidenceError("provider lease lifecycle diagnostics are out of order")
    if lifecycle_positions["ihk unload"][0] >= lifecycle_positions["ihk load"][1]:
        raise EvidenceError("provider reload lifecycle diagnostics are out of order")

    timestamp_prefix = re.compile(r"^(?:\[\s*[0-9]+(?:\.[0-9]+)?\]\s+)?")
    exact_lifecycle_bodies = set(lifecycle_bodies.values())
    detach_expression = re.compile(r"^" + PROVIDER_LEASE_DETACH_DIAGNOSTIC_PATTERN + r"$")

    def selected_native_trace(segment: list[str]) -> list[str]:
        selected = []
        for line in segment:
            body = timestamp_prefix.sub("", line, count=1)
            if (
                body in exact_lifecycle_bodies
                or body in {
                    PROVIDER_CALLBACK_INIT_DIAGNOSTIC,
                    PROVIDER_LEASE_ATTACH_DIAGNOSTIC,
                    PROVIDER_CALLBACK_EXIT_DIAGNOSTIC,
                    PROVIDER_REGISTRY_EMPTY_DIAGNOSTIC,
                    PROVIDER_OPEN_ACQUIRE_DIAGNOSTIC,
                    PROVIDER_OPEN_RELEASE_DIAGNOSTIC,
                }
                or detach_expression.fullmatch(body) is not None
            ):
                selected.append(body)
        return selected

    if (
        selected_native_trace(lines[: marker_positions["begin"]])
        or selected_native_trace(lines[dmesg_finish + 1 :])
    ):
        raise EvidenceError("native diagnostics lie outside the authorized trace windows")
    if selected_native_trace(
        lines[marker_positions["begin"] + 1 : dmesg_start]
    ) != selected_native_trace(dmesg_lines):
        raise EvidenceError("live and bounded dmesg native diagnostics diverge")

    return {
        "kernel_release": kernel_release,
        "mcd0": {
            "capture_can_claim_pass": False,
            "compat_abi": "i386",
            "compat_unknown_ioctl_errno": -22,
            "credit_eligible": False,
            "device_node_identity_match_observed": True,
            "diagnostic_segments": 2,
            "first_cycle_open_count": MCD0_FIRST_CYCLE_OPEN_COUNT,
            "first_device_major": 10,
            "first_device_minor": first_minor,
            "gate_status": "TODO",
            "module_owner_unload_status": int(mcd0_negative.group(1)),
            "native_abi": "x86_64",
            "native_unknown_ioctl_errno": -22,
            "node_present_observed": True,
            "node_removed_observed": True,
            "operation_callbacks_reachable": False,
            "open_receipt_scope": {
                "duplicate_close_detectable_while_other_references_exist": False,
                "same_generation_token_may_repeat": True,
                "trusted_noncopy_owner_balance_required": True,
            },
            "os_operations_reachable": False,
            "overlapping_open_count": MCD0_OVERLAPPING_OPEN_COUNT,
            "provider_open_acquire_count_per_trace": (
                MCD0_PROVIDER_OPEN_COUNT_PER_TRACE
            ),
            "provider_open_release_count_per_trace": (
                MCD0_PROVIDER_OPEN_COUNT_PER_TRACE
            ),
            "provider_registry_minor": 0,
            "reload_cycles": MCD0_RELOAD_CYCLES,
            "reload_device_major": 10,
            "reload_device_minor": reload_minor,
            "reload_open_count": MCD0_RELOAD_OPEN_COUNT,
            "resource_operations_reachable": False,
            "rocky_runtime_validated": False,
            "runtime_behavior_proven": False,
            "sequential_open_count": MCD0_SEQUENTIAL_OPEN_COUNT,
            "sysfs_identity_path": "/sys/class/misc/mcd0/dev",
            "tracker_credit": False,
            "unknown_ioctl_command": "0xdeadbeef",
            "valid_ioctl_commands": [],
        },
        "negative_unload_status": int(negative_records[0].group(1)),
        "provider_lease": {
            "attach_observed": True,
            "attach_count_per_trace": 2,
            "callback_abi": PROVIDER_CALLBACK_ABI,
            "complete_cycles_observed": 2,
            "detach_observed": True,
            "detach_count_per_trace": 2,
            "exit_callback_observed": True,
            "exit_callback_count_per_trace": 2,
            "init_callback_observed": True,
            "init_callback_count_per_trace": 2,
            "raw_token_logged": False,
            "registry_empty_observed": True,
            "registry_empty_count_per_trace": 2,
        },
        "provider_refcount": 2,
        "provider_users": ["ihk_smp_x86_64", "mcctrl"],
        "serial_sha256": _sha256_file(serial_path),
    }


def _require_sha256_value(value: Any, label: str) -> str:
    if type(value) is not str or HEX64.fullmatch(value) is None:
        raise EvidenceError("{0} must be exact SHA-256 text".format(label))
    return value


def _is_canonical_positive_decimal(value: Any) -> bool:
    return type(value) is str and re.fullmatch(r"[1-9][0-9]*", value) is not None


def _validate_execution_workflow_identity(
    value: dict[str, Any], candidate_sha: str, repository: str
) -> None:
    _require_keys(
        value,
        {
            "github_event_name",
            "github_ref",
            "github_sha",
            "github_workflow_blob_sha1",
            "github_workflow_ref",
            "github_workflow_sha",
            "job_workflow_file_path",
            "job_workflow_blob_sha1",
            "job_workflow_ref",
            "job_workflow_repository",
            "job_workflow_sha",
        },
        "capture execution workflow identity",
    )
    event_name = value["github_event_name"]
    if type(event_name) is not str or event_name not in {
        "pull_request",
        "workflow_dispatch",
    }:
        raise EvidenceError("capture workflow event differs")
    for key in ("github_sha", "github_workflow_sha", "job_workflow_sha"):
        if type(value[key]) is not str or HEX40.fullmatch(value[key]) is None:
            raise EvidenceError("capture execution {0} differs".format(key))
    for key in (
        "github_workflow_blob_sha1",
        "job_workflow_blob_sha1",
    ):
        if type(value[key]) is not str or HEX40.fullmatch(value[key]) is None:
            raise EvidenceError("capture execution {0} differs".format(key))
    github_ref = value["github_ref"]
    if type(github_ref) is not str:
        raise EvidenceError("capture GitHub ref differs")
    if event_name == "pull_request":
        if re.fullmatch(r"refs/pull/[1-9][0-9]*/merge", github_ref) is None:
            raise EvidenceError("capture pull-request ref differs")
        caller_path = ".github/workflows/native-rust-host-modules-exact-runtime-pr.yml"
        caller_identity = EXPECTED_REPOSITORY_WORKFLOW_IDENTITIES[
            "runtime_pr_workflow"
        ]
    else:
        if re.fullmatch(r"refs/(?:heads|tags)/[A-Za-z0-9._/-]+", github_ref) is None:
            raise EvidenceError("capture direct-dispatch ref differs")
        if "//" in github_ref or any(
            component in {"", ".", ".."} for component in github_ref.split("/")
        ):
            raise EvidenceError("capture direct-dispatch ref is not canonical")
        caller_path = ".github/workflows/native-rust-host-modules-exact-runtime.yml"
        caller_identity = EXPECTED_REPOSITORY_WORKFLOW_IDENTITIES[
            "runtime_workflow"
        ]
        if value["github_sha"] != candidate_sha:
            raise EvidenceError("direct-dispatch candidate/execution SHA differs")
    job_path = ".github/workflows/native-rust-host-modules-exact-runtime.yml"
    job_identity = EXPECTED_REPOSITORY_WORKFLOW_IDENTITIES["runtime_workflow"]
    expected_caller_ref = "{0}/{1}@{2}".format(
        repository, caller_path, github_ref
    )
    expected_job_ref = "{0}/{1}@{2}".format(repository, job_path, github_ref)
    if (
        value["github_workflow_ref"] != expected_caller_ref
        or value["job_workflow_ref"] != expected_job_ref
        or value["job_workflow_repository"] != repository
        or value["job_workflow_file_path"] != job_path
    ):
        raise EvidenceError("capture executed workflow ref/path differs")
    if (
        value["github_workflow_sha"] != value["github_sha"]
        or value["job_workflow_sha"] != value["github_sha"]
    ):
        raise EvidenceError("capture caller/called workflow SHA differs")
    if (
        value["github_workflow_blob_sha1"]
        != caller_identity["git_blob_sha1"]
        or value["job_workflow_blob_sha1"] != job_identity["git_blob_sha1"]
    ):
        raise EvidenceError("capture executed workflow blob identity differs")


def _read_bounded_regular_path_bytes(
    path: Path, maximum_size: int, label: str
) -> bytes:
    try:
        before = path.stat()
        identity = _stat_identity(before)
        if (
            not stat.S_ISREG(before.st_mode)
            or stat.S_IMODE(before.st_mode) != 0o644
            or before.st_nlink != 1
            or before.st_size < 1
            or before.st_size > maximum_size
        ):
            raise EvidenceError("{0} shape differs".format(label))
        with path.open("rb") as stream:
            opened = os.fstat(stream.fileno())
            if _stat_identity(opened) != identity:
                raise EvidenceError("{0} changed while opening".format(label))
            chunks = []
            total = 0
            while True:
                chunk = stream.read(65536)
                if not chunk:
                    break
                total += len(chunk)
                if total > maximum_size:
                    raise EvidenceError("{0} exceeds its size bound".format(label))
                chunks.append(chunk)
            if _stat_identity(os.fstat(stream.fileno())) != identity:
                raise EvidenceError("{0} changed while reading".format(label))
        if _stat_identity(path.stat()) != identity:
            raise EvidenceError("{0} changed after reading".format(label))
    except EvidenceError:
        raise
    except OSError as error:
        raise EvidenceError("cannot read {0}: {1}".format(label, error)) from error
    result = b"".join(chunks)
    if len(result) != before.st_size:
        raise EvidenceError("{0} size changed while reading".format(label))
    return result


def _validate_runtime_workflow_provenance(
    provenance_path: Path,
    caller_workflow_path: Path,
    runtime_workflow_path: Path,
    execution: dict[str, Any],
    candidate_sha: str,
    repository: str,
) -> dict[str, str]:
    _validate_execution_workflow_identity(execution, candidate_sha, repository)
    provenance_bytes = _read_bounded_regular_path_bytes(
        provenance_path,
        MAX_RUNTIME_TEXT_FILE_SIZE,
        "runtime workflow provenance",
    )
    caller_bytes = _read_bounded_regular_path_bytes(
        caller_workflow_path,
        MAX_RUNTIME_TEXT_FILE_SIZE,
        "executed caller workflow",
    )
    runtime_bytes = _read_bounded_regular_path_bytes(
        runtime_workflow_path,
        MAX_RUNTIME_TEXT_FILE_SIZE,
        "executed runtime workflow",
    )
    receipt = _decode_pretty_canonical_json_bytes(
        provenance_bytes, "runtime workflow provenance"
    )
    _require_keys(
        receipt,
        {"candidate_sha", "github", "job", "schema", "workflow_blobs"},
        "runtime workflow provenance",
    )
    if (
        receipt["schema"]
        != "mckernel-native-rust-runtime-workflow-provenance-v1"
        or receipt["candidate_sha"] != candidate_sha
    ):
        raise EvidenceError("runtime workflow provenance identity differs")
    expected_github = {
        "event_name": execution["github_event_name"],
        "ref": execution["github_ref"],
        "sha": execution["github_sha"],
        "workflow_ref": execution["github_workflow_ref"],
        "workflow_sha": execution["github_workflow_sha"],
    }
    expected_job = {
        "workflow_file_path": execution["job_workflow_file_path"],
        "workflow_ref": execution["job_workflow_ref"],
        "workflow_repository": execution["job_workflow_repository"],
        "workflow_sha": execution["job_workflow_sha"],
    }
    if not _exact_typed_equal(receipt["github"], expected_github) or not (
        _exact_typed_equal(receipt["job"], expected_job)
    ):
        raise EvidenceError("runtime workflow provenance contexts differ")
    caller_key = (
        "runtime_pr_workflow"
        if execution["github_event_name"] == "pull_request"
        else "runtime_workflow"
    )
    expected_records = {
        "caller": (
            EXPECTED_REPOSITORY_WORKFLOW_IDENTITIES[caller_key],
            (
                ".github/workflows/native-rust-host-modules-exact-runtime-pr.yml"
                if caller_key == "runtime_pr_workflow"
                else ".github/workflows/native-rust-host-modules-exact-runtime.yml"
            ),
            "executed-caller-workflow.yml",
            caller_bytes,
            execution["github_workflow_blob_sha1"],
        ),
        "job": (
            EXPECTED_REPOSITORY_WORKFLOW_IDENTITIES["runtime_workflow"],
            ".github/workflows/native-rust-host-modules-exact-runtime.yml",
            "executed-runtime-workflow.yml",
            runtime_bytes,
            execution["job_workflow_blob_sha1"],
        ),
    }
    blobs = receipt["workflow_blobs"]
    _require_keys(blobs, {"caller", "job"}, "runtime workflow blob receipts")
    for key in ("caller", "job"):
        identity, source_path, evidence_file, data, asserted_blob = expected_records[
            key
        ]
        actual_blob = _git_blob_sha1(data)
        expected = {
            "candidate_git_blob_sha1": identity["git_blob_sha1"],
            "evidence_file": evidence_file,
            "executed_git_blob_sha1": identity["git_blob_sha1"],
            "path": source_path,
            "sha256": identity["sha256"],
            "size": identity["size"],
        }
        if (
            not _exact_typed_equal(blobs[key], expected)
            or actual_blob != identity["git_blob_sha1"]
            or asserted_blob != actual_blob
            or len(data) != identity["size"]
            or _sha256_bytes(data) != identity["sha256"]
        ):
            raise EvidenceError(
                "runtime {0} workflow byte provenance differs".format(key)
            )
    return {
        "executed_caller_workflow_sha256": _sha256_bytes(caller_bytes),
        "executed_runtime_workflow_sha256": _sha256_bytes(runtime_bytes),
        "workflow_provenance_sha256": _sha256_bytes(provenance_bytes),
    }


def _validate_capture_content(value: dict[str, Any]) -> None:
    _require_sha256_value(value["contract_sha256"], "capture contract digest")
    identity = value["identity"]
    _require_keys(
        identity,
        {
            "candidate_sha",
            "execution_workflow",
            "github_repository",
            "github_run_attempt",
            "github_run_id",
        },
        "capture identity",
    )
    if type(identity["candidate_sha"]) is not str or HEX40.fullmatch(
        identity["candidate_sha"]
    ) is None:
        raise EvidenceError("capture candidate SHA differs")
    if type(identity["github_repository"]) is not str or re.fullmatch(
        r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", identity["github_repository"]
    ) is None:
        raise EvidenceError("capture repository identity differs")
    for key in ("github_run_attempt", "github_run_id"):
        item = identity[key]
        if not _is_canonical_positive_decimal(item):
            raise EvidenceError("capture {0} differs".format(key))
    _validate_execution_workflow_identity(
        identity["execution_workflow"],
        identity["candidate_sha"],
        identity["github_repository"],
    )

    build = value["build"]
    _require_keys(
        build,
        {
            "artifact_manifest_sha256",
            "bzimage_sha256",
            "config_runtime_requirements",
            "config_sha256",
            "kbuild_link_closure",
            "kconfig_solver",
            "kernel_release",
            "modules",
            "scope",
        },
        "capture build",
    )
    for key in ("artifact_manifest_sha256", "bzimage_sha256", "config_sha256"):
        _require_sha256_value(build[key], "capture build.{0}".format(key))
    if build["config_runtime_requirements"] != EXPECTED_RUNTIME_REQUIRED_CONFIG:
        raise EvidenceError("capture runtime config requirements differ")
    release = build["kernel_release"]
    if type(release) is not str or release != EXPECTED_KERNEL_RELEASE:
        raise EvidenceError("capture kernel release differs")

    scope = build["scope"]
    _require_keys(
        scope,
        {
            "build_commands_sha256",
            "build_environment_sha256",
            "build_log_sha256",
            "kernel_targets",
            "module_targets",
        },
        "capture build scope",
    )
    _require_sha256_value(scope["build_commands_sha256"], "capture build command digest")
    _require_sha256_value(
        scope["build_environment_sha256"], "capture build environment digest"
    )
    if (
        scope["build_environment_sha256"]
        != EXPECTED_REPRODUCIBLE_BUILD_ENVIRONMENT_SHA256
    ):
        raise EvidenceError("capture build environment digest differs")
    _require_sha256_value(scope["build_log_sha256"], "capture build log digest")
    if scope["kernel_targets"] != BUILD_KERNEL_TARGETS or scope[
        "module_targets"
    ] != BUILD_MODULE_TARGETS:
        raise EvidenceError("capture build target scope differs")

    modules = build["modules"]
    _require_keys(modules, {"ihk", "ihk_smp_x86_64", "mcctrl"}, "capture modules")
    expected_module_facts = {
        "ihk": {
            "defined_provider_symbols": list(PROVIDER_DEFINED_SYMBOLS),
            "depends": [],
            "gpl_exported_provider_symbols": list(PROVIDER_DEFINED_SYMBOLS),
            "import_namespaces": [],
            "provider_export_namespace": PROVIDER_EXPORT_NAMESPACE,
        },
        "ihk_smp_x86_64": {
            "depends": ["ihk"],
            "import_namespaces": [PROVIDER_EXPORT_NAMESPACE],
            "undefined_provider_symbols": list(PROVIDER_SMP_IMPORT_SYMBOLS),
        },
        "mcctrl": {
            "depends": ["ihk"],
            "import_namespaces": [PROVIDER_EXPORT_NAMESPACE],
            "undefined_provider_symbols": [PROVIDER_ANCHOR_SYMBOL],
        },
    }
    for name, expected in expected_module_facts.items():
        record = modules[name]
        _require_keys(record, set(expected) | {"sha256"}, name)
        if any(record[key] != expected_value for key, expected_value in expected.items()):
            raise EvidenceError("capture module metadata differs for {0}".format(name))
        _require_sha256_value(record["sha256"], "capture module digest {0}".format(name))

    solver = build["kconfig_solver"]
    _require_keys(
        solver,
        {"claims", "counts", "limitations", "sha256", "status"},
        "capture Kconfig solver",
    )
    if solver["claims"] != SOLVER_EXPECTED_CLAIMS or any(
        solver["claims"].get(key) is not False for key in SOLVER_EXPECTED_CLAIMS
    ):
        raise EvidenceError("capture Kconfig solver claims must remain false")
    counts = solver["counts"]
    if counts != SOLVER_EXPECTED_COUNTS or type(counts) is not dict:
        raise EvidenceError("capture Kconfig solver counts differ")
    for key in (
        "case_count",
        "matrix_make_invocation_count",
        "negative_make_invocation_count",
        "total_make_invocation_count",
        "two_pass_byte_identical_count",
    ):
        if type(counts.get(key)) is not int:
            raise EvidenceError("capture Kconfig solver count type differs")
    distribution = counts.get("module_result_distribution")
    if type(distribution) is not dict or any(
        type(distribution.get(key)) is not int for key in ("0", "1", "2", "3")
    ):
        raise EvidenceError("capture Kconfig solver distribution type differs")
    if solver["limitations"] != SOLVER_EXPECTED_LIMITATIONS or any(
        type(solver["limitations"].get(key)) is not str
        for key in SOLVER_EXPECTED_LIMITATIONS
    ):
        raise EvidenceError("capture Kconfig solver limitations differ")
    if type(solver["status"]) is not str or solver["status"] != SOLVER_CAPTURE_STATUS:
        raise EvidenceError("capture Kconfig solver status differs")
    _require_sha256_value(solver["sha256"], "capture Kconfig solver digest")

    link = build["kbuild_link_closure"]
    _require_keys(
        link,
        {"claims", "module_count", "raw_record_count", "sha256", "stage_lock_sha256"},
        "capture Kbuild link closure",
    )
    if link["claims"] != EXPECTED_LINK_CLAIMS or any(
        link["claims"].get(key) is not False for key in EXPECTED_LINK_CLAIMS
    ):
        raise EvidenceError("capture Kbuild link claims must remain false")
    if type(link["module_count"]) is not int or link["module_count"] != 3:
        raise EvidenceError("capture Kbuild link module count differs")
    if type(link["raw_record_count"]) is not int or link[
        "raw_record_count"
    ] != len(EXPECTED_RAW_RECORD_NAMES):
        raise EvidenceError("capture Kbuild raw record count differs")
    _require_sha256_value(link["sha256"], "capture Kbuild link digest")
    _require_sha256_value(link["stage_lock_sha256"], "capture stage-lock digest")

    runtime = value["runtime"]
    runtime_digests = {
        "environment_sha256",
        "executed_caller_workflow_sha256",
        "executed_runtime_workflow_sha256",
        "initramfs_sha256",
        "initramfs_sha256_record",
        "qemu_command_sha256",
        "qemu_exit_code_sha256",
        "qemu_log_sha256",
        "qemu_version_sha256",
        "serial_sha256",
        "workflow_provenance_sha256",
    }
    _require_keys(
        runtime,
        runtime_digests
        | {
            "kernel_release",
            "mcd0",
            "negative_unload_status",
            "provider_lease",
            "provider_refcount",
            "provider_users",
        },
        "capture runtime",
    )
    for key in runtime_digests:
        _require_sha256_value(runtime[key], "capture runtime.{0}".format(key))
    if runtime["kernel_release"] != release:
        raise EvidenceError("capture build/runtime kernel releases diverge")
    if type(runtime["negative_unload_status"]) is not int or runtime[
        "negative_unload_status"
    ] != 1:
        raise EvidenceError("capture negative unload status differs")
    expected_provider_lease = {
        "attach_observed": True,
        "attach_count_per_trace": 2,
        "callback_abi": PROVIDER_CALLBACK_ABI,
        "complete_cycles_observed": 2,
        "detach_observed": True,
        "detach_count_per_trace": 2,
        "exit_callback_observed": True,
        "exit_callback_count_per_trace": 2,
        "init_callback_observed": True,
        "init_callback_count_per_trace": 2,
        "raw_token_logged": False,
        "registry_empty_observed": True,
        "registry_empty_count_per_trace": 2,
    }
    if not _exact_typed_equal(runtime["provider_lease"], expected_provider_lease):
        raise EvidenceError("capture provider lease lifecycle differs")
    mcd0 = runtime["mcd0"]
    if type(mcd0) is not dict:
        raise EvidenceError("capture mcd0 runtime summary differs")
    for minor_key in ("first_device_minor", "reload_device_minor"):
        minor = mcd0.get(minor_key)
        if type(minor) is not int or minor < 0 or minor >= (1 << 20):
            raise EvidenceError("capture mcd0 dynamic minor differs")
    expected_mcd0 = {
        "capture_can_claim_pass": False,
        "compat_abi": "i386",
        "compat_unknown_ioctl_errno": -22,
        "credit_eligible": False,
        "device_node_identity_match_observed": True,
        "diagnostic_segments": 2,
        "first_cycle_open_count": MCD0_FIRST_CYCLE_OPEN_COUNT,
        "first_device_major": 10,
        "first_device_minor": mcd0["first_device_minor"],
        "gate_status": "TODO",
        "module_owner_unload_status": 1,
        "native_abi": "x86_64",
        "native_unknown_ioctl_errno": -22,
        "node_present_observed": True,
        "node_removed_observed": True,
        "operation_callbacks_reachable": False,
        "open_receipt_scope": {
            "duplicate_close_detectable_while_other_references_exist": False,
            "same_generation_token_may_repeat": True,
            "trusted_noncopy_owner_balance_required": True,
        },
        "os_operations_reachable": False,
        "overlapping_open_count": MCD0_OVERLAPPING_OPEN_COUNT,
        "provider_open_acquire_count_per_trace": MCD0_PROVIDER_OPEN_COUNT_PER_TRACE,
        "provider_open_release_count_per_trace": MCD0_PROVIDER_OPEN_COUNT_PER_TRACE,
        "provider_registry_minor": 0,
        "reload_cycles": MCD0_RELOAD_CYCLES,
        "reload_device_major": 10,
        "reload_device_minor": mcd0["reload_device_minor"],
        "reload_open_count": MCD0_RELOAD_OPEN_COUNT,
        "resource_operations_reachable": False,
        "rocky_runtime_validated": False,
        "runtime_behavior_proven": False,
        "sequential_open_count": MCD0_SEQUENTIAL_OPEN_COUNT,
        "sysfs_identity_path": "/sys/class/misc/mcd0/dev",
        "tracker_credit": False,
        "unknown_ioctl_command": "0xdeadbeef",
        "valid_ioctl_commands": [],
    }
    if not _exact_typed_equal(mcd0, expected_mcd0):
        raise EvidenceError("capture mcd0 runtime summary differs")
    if type(runtime["provider_refcount"]) is not int or runtime[
        "provider_refcount"
    ] != 2:
        raise EvidenceError("capture provider refcount differs")
    if runtime["provider_users"] != ["ihk_smp_x86_64", "mcctrl"]:
        raise EvidenceError("capture provider users differ")


def validate_capture(value: dict[str, Any]) -> None:
    _require_keys(
        value,
        {
            "build",
            "capture_sha256",
            "contract_id",
            "contract_sha256",
            "identity",
            "readiness",
            "runtime",
            "schema_version",
        },
        "capture",
    )
    if (
        type(value["schema_version"]) is not int
        or value["schema_version"] != 1
        or type(value["contract_id"]) is not str
        or value["contract_id"] != CONTRACT_ID
    ):
        raise EvidenceError("capture identity differs")
    _validate_capture_content(value)
    readiness = value["readiness"]
    if not _exact_typed_equal(readiness, {
        "credit_eligible": False,
        "gate_status": "NOT_READY",
        "independent_reviewed": False,
        "status": "CAPTURED_UNREVIEWED",
        "blockers": [
            "GitHub artifact digest must be retained immutably",
            "independent evidence review must verify and register this exact capture",
        ],
    }):
        raise EvidenceError("capture attempts to bypass independent review or award credit")
    unsigned = copy.deepcopy(value)
    recorded = unsigned.pop("capture_sha256")
    _require_sha256_value(recorded, "capture digest")
    if recorded != _sha256_bytes(_canonical_bytes(unsigned)):
        raise EvidenceError("capture digest is stale")


def _validate_runtime_files(
    contract: dict[str, Any],
    serial_log: Path,
    qemu_log: Path,
    qemu_command: Path,
    qemu_version: Path,
    qemu_exit_code: Path,
    environment_log: Path,
    initramfs: Path,
    initramfs_sha256: Path,
    expected_build_bzimage: Any = None,
    expected_build_bzimage_sha256: Any = None,
    expected_command_build_bzimage: Any = None,
    expected_command_runtime_parent: Any = None,
) -> dict[str, Any]:
    serial_log = _regular_evidence_file(serial_log, "runtime serial log")
    initramfs = _regular_evidence_file(initramfs, "deterministic initramfs")
    runtime = validate_serial(serial_log, EXPECTED_KERNEL_RELEASE)
    paths = {
        "environment_sha256": _regular_evidence_file(
            environment_log, "runtime environment"
        ),
        "qemu_command_sha256": _regular_evidence_file(
            qemu_command, "QEMU command"
        ),
        "qemu_version_sha256": _regular_evidence_file(
            qemu_version, "QEMU version"
        ),
        "qemu_exit_code_sha256": _regular_evidence_file(
            qemu_exit_code, "QEMU exit code"
        ),
    }
    ancillary = {
        name: _sha256_file(path) for name, path in paths.items()
    }
    qemu_log = _regular_evidence_file(qemu_log, "QEMU log", nonempty=False)
    ancillary["qemu_log_sha256"] = _sha256_file(qemu_log)

    environment = _read_text(paths["environment_sha256"], "runtime environment")
    environment_lines = environment.splitlines()
    expected_environment_prefix = [
        "container_image={0}".format(contract["runtime"]["container_image"]),
        "runner_arch=x86_64",
    ]
    if (
        len(environment_lines) < 4
        or environment_lines[:2] != expected_environment_prefix
        or environment_lines[2]
        != "os_release_sha256=" + EXPECTED_ROCKY_OS_RELEASE_SHA256
        or environment_lines[3:] != sorted(environment_lines[3:])
        or len(environment_lines[3:]) != len(set(environment_lines[3:]))
        or any(
            not line or re.fullmatch(r"[A-Za-z0-9_.+~:^()-]+", line) is None
            for line in environment_lines[3:]
        )
        or not any(line.startswith("qemu-kvm-core-") for line in environment_lines[3:])
    ):
        raise EvidenceError("runtime environment identity differs")

    qemu_version_text = _read_text(paths["qemu_version_sha256"], "QEMU version")
    version_lines = qemu_version_text.splitlines()
    if (
        not version_lines
        or re.fullmatch(r"QEMU emulator version [0-9]+\.[0-9]+(?:\.[0-9]+)?(?: .*)?", version_lines[0])
        is None
        or sum(line.startswith("QEMU emulator version ") for line in version_lines)
        != 1
    ):
        raise EvidenceError("QEMU version diagnostic differs")

    qemu_command_text = _read_text(paths["qemu_command_sha256"], "QEMU command")
    if len(qemu_command_text.splitlines()) != 1:
        raise EvidenceError("QEMU command diagnostic must contain exactly one argv record")
    try:
        qemu_argv = shlex.split(qemu_command_text, posix=True)
    except ValueError as error:
        raise EvidenceError("QEMU command diagnostic is malformed") from error
    if len(qemu_argv) != 24:
        raise EvidenceError("QEMU command argv cardinality differs")
    fixed_argv = {
        0: "/usr/libexec/qemu-kvm",
        1: "-machine",
        2: "q35",
        3: "-accel",
        4: "tcg",
        5: "-cpu",
        6: "max",
        7: "-smp",
        8: "2",
        9: "-m",
        10: "2048",
        11: "-kernel",
        13: "-initrd",
        15: "-append",
        16: "console=ttyS0,115200n8 rdinit=/init nokaslr panic=-1",
        17: "-display",
        18: "none",
        19: "-monitor",
        20: "none",
        21: "-serial",
        23: "-no-reboot",
    }
    if any(qemu_argv[index] != value for index, value in fixed_argv.items()):
        raise EvidenceError("QEMU command exact TCG argv differs")

    def exact_runtime_path(value: str, parent_name: str, filename: str) -> Path:
        path = Path(value)
        if (
            not path.is_absolute()
            or ".." in path.parts
            or path.name != filename
            or path.parent.name != parent_name
        ):
            raise EvidenceError("QEMU command evidence path differs: {0}".format(filename))
        return path

    build_argv_path = exact_runtime_path(
        qemu_argv[12], "native-rust-build-evidence", "bzImage"
    )
    initramfs_argv_path = exact_runtime_path(
        qemu_argv[14], "native-rust-runtime-evidence", "initramfs.cpio.gz"
    )
    if not qemu_argv[22].startswith("file:"):
        raise EvidenceError("QEMU command serial boundary differs")
    serial_argv_path = exact_runtime_path(
        qemu_argv[22][len("file:") :],
        "native-rust-runtime-evidence",
        "serial.log",
    )
    if serial_argv_path.parent != initramfs_argv_path.parent:
        raise EvidenceError("QEMU command runtime evidence roots diverge")
    if expected_build_bzimage is not None:
        expected_bzimage = _regular_evidence_file(
            expected_build_bzimage, "expected build bzImage"
        )
        if (
            not isinstance(expected_build_bzimage_sha256, str)
            or HEX64.fullmatch(expected_build_bzimage_sha256) is None
            or _sha256_file(expected_bzimage) != expected_build_bzimage_sha256
        ):
            raise EvidenceError("expected build bzImage digest differs")
    if (
        expected_command_build_bzimage is not None
        or expected_command_runtime_parent is not None
    ):
        if (
            expected_command_build_bzimage is None
            or expected_command_runtime_parent is None
        ):
            raise EvidenceError("expected QEMU command input roots are incomplete")
        command_bzimage = Path(expected_command_build_bzimage)
        command_runtime_parent = Path(expected_command_runtime_parent)
        if (
            build_argv_path != command_bzimage
            or initramfs_argv_path != command_runtime_parent / "initramfs.cpio.gz"
            or serial_argv_path != command_runtime_parent / "serial.log"
        ):
            raise EvidenceError(
                "QEMU command paths differ from captured build/runtime inputs"
            )
    if _read_text(paths["qemu_exit_code_sha256"], "QEMU exit code") != "0\n":
        raise EvidenceError("QEMU did not exit cleanly after guest poweroff")

    initramfs_sha256 = _regular_evidence_file(
        initramfs_sha256, "initramfs digest"
    )
    digest_record = _read_text(initramfs_sha256, "initramfs digest")
    digest_match = re.fullmatch(
        r"([0-9a-f]{64})  initramfs\.cpio\.gz\n", digest_record
    )
    if digest_match is None or digest_match.group(1) != _sha256_file(initramfs):
        raise EvidenceError("initramfs digest record differs")
    ancillary["initramfs_sha256"] = digest_match.group(1)
    ancillary["initramfs_sha256_record"] = _sha256_file(initramfs_sha256)
    runtime.update(ancillary)
    return runtime


def _validate_bound_build_evidence_directory(
    contract: dict[str, Any],
    build_dir: Path,
    candidate_sha: str,
    modinfo_fd: int | None = None,
    nm_fd: int | None = None,
    build_dir_fd: int | None = None,
    modinfo_sha256: str | None = None,
    nm_sha256: str | None = None,
    runtime_identity: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], dict[str, str]]:
    records = _parse_sums(build_dir)
    initial_file_identities = _validate_exact_build_artifact_files(
        build_dir,
        records,
        contract["artifact_contract"]["build_evidence_files"],
    )
    _parse_precheck_sums(build_dir, records, EXPECTED_PRECHECK_BUILD_MEMBERS)
    phase2 = _validate_phase2_build_evidence(
        build_dir, records, build_dir_fd=build_dir_fd
    )
    build_scope = _validate_build_scope_artifacts(build_dir, records)
    commit = _read_text(build_dir / "commit.sha", "build commit").strip()
    if commit != candidate_sha:
        raise EvidenceError("build artifact commit differs from runtime candidate")
    _validate_build_workflow_provenance(
        build_dir, records, candidate_sha, runtime_identity
    )
    kernel_release = _read_text(
        build_dir / "kernel.release", "kernel release"
    ).strip()
    if kernel_release != EXPECTED_KERNEL_RELEASE:
        raise EvidenceError(
            "built kernel release differs from the selected custom release"
        )
    config_state = _validate_resolved_config(
        build_dir / "resolved.config", contract["runtime"]["required_kernel_config"]
    )

    modules: dict[str, Any] = {}
    for item in contract["modules"]:
        with _bound_evidence_file(
            build_dir / item["file"],
            "build module {0}".format(item["file"]),
        ) as bound_module:
            path, module_fd = bound_module
            depends = _run_field(
                path,
                "depends",
                modinfo_fd=modinfo_fd,
                module_fd=module_fd,
                modinfo_sha256=modinfo_sha256,
                module_sha256=records[item["file"]],
            )
            namespaces = _run_field(
                path,
                "import_ns",
                modinfo_fd=modinfo_fd,
                module_fd=module_fd,
                modinfo_sha256=modinfo_sha256,
                module_sha256=records[item["file"]],
            )
            vermagic_release = _module_vermagic_release(
                path,
                modinfo_fd=modinfo_fd,
                module_fd=module_fd,
                modinfo_sha256=modinfo_sha256,
                module_sha256=records[item["file"]],
            )
            if depends != item["depends"]:
                raise EvidenceError(
                    "{0} dependency metadata differs".format(item["file"])
                )
            expected_ns = (
                []
                if item["import_namespace"] is None
                else [item["import_namespace"]]
            )
            if namespaces != expected_ns:
                raise EvidenceError(
                    "{0} import namespace differs".format(item["file"])
                )
            if vermagic_release != kernel_release:
                raise EvidenceError(
                    "{0} vermagic/build release differs".format(item["file"])
                )
            symbol_facts = _validate_module_symbol_graph(
                path,
                item,
                nm_fd=nm_fd,
                module_fd=module_fd,
                nm_sha256=nm_sha256,
                module_sha256=records[item["file"]],
            )
        module_facts = {
            "depends": depends,
            "import_namespaces": namespaces,
            "sha256": records[item["file"]],
        }
        module_facts.update(symbol_facts)
        modules[item["name"]] = module_facts

    build = {
        "artifact_manifest_sha256": _sha256_file(build_dir / "SHA256SUMS"),
        "bzimage_sha256": records["bzImage"],
        "config_sha256": records["resolved.config"],
        "config_runtime_requirements": config_state,
        "kbuild_link_closure": phase2["kbuild_link_closure"],
        "kconfig_solver": phase2["kconfig_solver"],
        "kernel_release": kernel_release,
        "modules": modules,
        "scope": build_scope,
    }
    final_directory = build_dir
    final_records = _parse_sums(final_directory)
    final_file_identities = _validate_exact_build_artifact_files(
        final_directory,
        final_records,
        contract["artifact_contract"]["build_evidence_files"],
    )
    _parse_precheck_sums(
        final_directory, final_records, EXPECTED_PRECHECK_BUILD_MEMBERS
    )
    if (
        final_file_identities != initial_file_identities
        or final_records != records
    ):
        raise EvidenceError("build artifact changed while it was validated")
    return build, records


def _validate_build_evidence_directory(
    contract: dict[str, Any],
    build_dir: Path,
    candidate_sha: str,
    modinfo_fd: int | None = None,
    nm_fd: int | None = None,
    modinfo_sha256: str | None = None,
    nm_sha256: str | None = None,
    runtime_identity: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], dict[str, str]]:
    with _bound_evidence_directory(
        build_dir, "build evidence directory"
    ) as bound_build:
        bound_build_dir, build_dir_fd = bound_build
        return _validate_bound_build_evidence_directory(
            contract,
            bound_build_dir,
            candidate_sha,
            modinfo_fd,
            nm_fd,
            build_dir_fd,
            modinfo_sha256,
            nm_sha256,
            runtime_identity,
        )


def _validate_bound_runtime_evidence_directory(
    repo: Path,
    directory: Path,
    build_dir: Path,
    contract_relative: Path = DEFAULT_CONTRACT,
    modinfo_fd: int | None = None,
    nm_fd: int | None = None,
    build_dir_fd: int | None = None,
    modinfo_sha256: str | None = None,
    nm_sha256: str | None = None,
) -> dict[str, str]:
    summary = validate_contract(repo.resolve(), contract_relative)
    contract = _load_json(repo.resolve() / contract_relative)
    records = _parse_sums(directory)
    expected = contract["artifact_contract"]["runtime_evidence_files"]
    runtime_size_limits = {
        name: MAX_RUNTIME_TEXT_FILE_SIZE for name in expected
    }
    runtime_size_limits["initramfs.cpio.gz"] = MAX_RUNTIME_EVIDENCE_FILE_SIZE
    for name in RUNTIME_HELPER_ELF_SPEC:
        runtime_size_limits[name] = MAX_RUNTIME_HELPER_FILE_SIZE
    initial_file_identities = _validate_exact_build_artifact_files(
        directory,
        records,
        expected,
        max_file_size=MAX_RUNTIME_EVIDENCE_FILE_SIZE,
        per_file_max=runtime_size_limits,
    )
    _validate_runtime_helper_artifacts(directory, records)

    with _bound_evidence_file(
        directory / "capture.json", "runtime capture document"
    ) as bound_capture:
        _capture_path, capture_fd = bound_capture
        capture_bytes, _capture_identity = _read_bound_descriptor_bytes(
            capture_fd,
            MAX_RUNTIME_TEXT_FILE_SIZE,
            "runtime capture document",
        )
        capture_document = _decode_pretty_canonical_json_bytes(
            capture_bytes, "runtime capture document"
        )
    validate_capture(capture_document)
    if capture_document["contract_sha256"] != summary["contract_sha256"]:
        raise EvidenceError("runtime capture contract digest differs")
    replayed_workflow = _validate_runtime_workflow_provenance(
        directory / "runtime-workflow-provenance.json",
        directory / "executed-caller-workflow.yml",
        directory / "executed-runtime-workflow.yml",
        capture_document["identity"]["execution_workflow"],
        capture_document["identity"]["candidate_sha"],
        capture_document["identity"]["github_repository"],
    )
    if any(
        capture_document["runtime"].get(key) != digest
        for key, digest in replayed_workflow.items()
    ):
        raise EvidenceError("runtime capture workflow provenance facts differ")
    replayed_build, _build_records = _validate_bound_build_evidence_directory(
        contract,
        build_dir,
        capture_document["identity"]["candidate_sha"],
        modinfo_fd,
        nm_fd,
        build_dir_fd,
        modinfo_sha256,
        nm_sha256,
        capture_document["identity"],
    )
    if replayed_build != capture_document["build"]:
        raise EvidenceError("runtime capture build evidence facts differ")
    expected_runtime_digests = {
        "environment_sha256": records["environment.txt"],
        "executed_caller_workflow_sha256": records[
            "executed-caller-workflow.yml"
        ],
        "executed_runtime_workflow_sha256": records[
            "executed-runtime-workflow.yml"
        ],
        "initramfs_sha256": records["initramfs.cpio.gz"],
        "initramfs_sha256_record": records["initramfs.sha256"],
        "qemu_command_sha256": records["qemu-command.txt"],
        "qemu_exit_code_sha256": records["qemu.exit-code"],
        "qemu_log_sha256": records["qemu.log"],
        "qemu_version_sha256": records["qemu-version.txt"],
        "serial_sha256": records["serial.log"],
        "workflow_provenance_sha256": records[
            "runtime-workflow-provenance.json"
        ],
    }
    runtime = capture_document["runtime"]
    for name, digest in expected_runtime_digests.items():
        if runtime[name] != digest:
            raise EvidenceError("runtime capture file digest differs: {0}".format(name))
    replayed = _validate_runtime_files(
        contract,
        directory / "serial.log",
        directory / "qemu.log",
        directory / "qemu-command.txt",
        directory / "qemu-version.txt",
        directory / "qemu.exit-code",
        directory / "environment.txt",
        directory / "initramfs.cpio.gz",
        directory / "initramfs.sha256",
        build_dir / "bzImage",
        capture_document["build"]["bzimage_sha256"],
    )
    replayed.update(replayed_workflow)
    if replayed != runtime:
        raise EvidenceError("runtime capture semantic facts differ")
    if _read_text(directory / "workflow-state", "runtime workflow state") != (
        "technical-capture-unreviewed\ncredit=forbidden\n"
    ):
        raise EvidenceError("runtime workflow state differs")
    final_directory = directory
    final_records = _parse_sums(final_directory)
    final_file_identities = _validate_exact_build_artifact_files(
        final_directory,
        final_records,
        expected,
        max_file_size=MAX_RUNTIME_EVIDENCE_FILE_SIZE,
        per_file_max=runtime_size_limits,
    )
    _validate_runtime_helper_artifacts(final_directory, final_records)
    if (
        final_file_identities != initial_file_identities
        or final_records != records
    ):
        raise EvidenceError("runtime evidence changed while it was validated")
    return records


def validate_runtime_evidence_directory(
    repo: Path,
    directory: Path,
    build_dir: Path,
    contract_relative: Path = DEFAULT_CONTRACT,
    modinfo_fd: int | None = None,
    nm_fd: int | None = None,
    modinfo_sha256: str | None = None,
    nm_sha256: str | None = None,
    workflow_provenance: Path | None = None,
) -> dict[str, str]:
    if workflow_provenance is not None and workflow_provenance != (
        directory / "runtime-workflow-provenance.json"
    ):
        raise EvidenceError("runtime workflow provenance path differs")
    with _bound_evidence_directory(
        directory, "runtime evidence directory"
    ) as bound_runtime:
        bound_runtime_directory, _runtime_dir_fd = bound_runtime
        with _bound_evidence_directory(
            build_dir, "build evidence directory"
        ) as bound_build:
            bound_build_directory, build_dir_fd = bound_build
            return _validate_bound_runtime_evidence_directory(
                repo,
                bound_runtime_directory,
                bound_build_directory,
                contract_relative,
                modinfo_fd,
                nm_fd,
                build_dir_fd,
                modinfo_sha256,
                nm_sha256,
            )


def capture(
    repo: Path,
    contract_relative: Path,
    build_dir: Path,
    serial_log: Path,
    qemu_log: Path,
    qemu_command: Path,
    qemu_version: Path,
    qemu_exit_code: Path,
    environment_log: Path,
    initramfs: Path,
    initramfs_sha256: Path,
    candidate_sha: str,
    github_repository: str,
    github_run_id: str,
    github_run_attempt: str,
    github_event_name: str,
    github_ref: str,
    github_sha: str,
    github_workflow_ref: str,
    github_workflow_sha: str,
    github_workflow_blob_sha1: str,
    job_workflow_ref: str,
    job_workflow_sha: str,
    job_workflow_repository: str,
    job_workflow_file_path: str,
    job_workflow_blob_sha1: str,
    workflow_provenance: Path,
    modinfo_fd: int | None = None,
    nm_fd: int | None = None,
    modinfo_sha256: str | None = None,
    nm_sha256: str | None = None,
    output: Path | None = None,
) -> dict[str, Any]:
    summary = validate_contract(repo, contract_relative)
    if not HEX40.fullmatch(candidate_sha):
        raise EvidenceError("candidate SHA must be exact 40-hex")
    if (
        not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", github_repository)
        or not _is_canonical_positive_decimal(github_run_id)
        or not _is_canonical_positive_decimal(github_run_attempt)
    ):
        raise EvidenceError("GitHub run identity is incomplete")
    execution_workflow = {
        "github_event_name": github_event_name,
        "github_ref": github_ref,
        "github_sha": github_sha,
        "github_workflow_blob_sha1": github_workflow_blob_sha1,
        "github_workflow_ref": github_workflow_ref,
        "github_workflow_sha": github_workflow_sha,
        "job_workflow_file_path": job_workflow_file_path,
        "job_workflow_blob_sha1": job_workflow_blob_sha1,
        "job_workflow_ref": job_workflow_ref,
        "job_workflow_repository": job_workflow_repository,
        "job_workflow_sha": job_workflow_sha,
    }
    _validate_execution_workflow_identity(
        execution_workflow, candidate_sha, github_repository
    )
    capture_identity = {
        "candidate_sha": candidate_sha,
        "execution_workflow": execution_workflow,
        "github_repository": github_repository,
        "github_run_attempt": github_run_attempt,
        "github_run_id": github_run_id,
    }
    contract = _load_json(repo / contract_relative)
    if (
        not build_dir.is_absolute()
        or ".." in build_dir.parts
        or build_dir.name != "native-rust-build-evidence"
    ):
        raise EvidenceError("capture build evidence directory identity differs")
    runtime_inputs = {
        "serial_log": serial_log,
        "qemu_log": qemu_log,
        "qemu_command": qemu_command,
        "qemu_version": qemu_version,
        "qemu_exit_code": qemu_exit_code,
        "environment_log": environment_log,
        "initramfs": initramfs,
        "initramfs_sha256": initramfs_sha256,
        "workflow_provenance": workflow_provenance,
        "executed_caller_workflow": (
            workflow_provenance.parent / "executed-caller-workflow.yml"
        ),
        "executed_runtime_workflow": (
            workflow_provenance.parent / "executed-runtime-workflow.yml"
        ),
    }
    with _bound_evidence_directory(
        build_dir, "build evidence directory"
    ) as bound_build:
        bound_build_dir, build_dir_fd = bound_build
        with _bound_capture_runtime_inputs(runtime_inputs) as bound_runtime:
            (
                bound_runtime_dir,
                runtime_dir_fd,
                bound_runtime_inputs,
                runtime_parent,
                bound_runtime_helpers,
                recheck_runtime_inputs,
                capture_state,
            ) = bound_runtime
            build, _build_records = _validate_bound_build_evidence_directory(
                contract,
                bound_build_dir,
                candidate_sha,
                modinfo_fd,
                nm_fd,
                build_dir_fd,
                modinfo_sha256,
                nm_sha256,
                capture_identity,
            )
            helper_records = {
                name: _sha256_bytes(
                    _read_bound_descriptor_bytes(
                        bound_runtime_helpers[name],
                        MAX_RUNTIME_HELPER_FILE_SIZE,
                        "runtime helper artifact {0}".format(name),
                    )[0]
                )
                for name in RUNTIME_HELPER_ELF_SPEC
            }
            _validate_runtime_helper_artifacts(
                bound_runtime_dir,
                helper_records,
                bound_files=bound_runtime_helpers,
            )
            runtime = _validate_runtime_files(
                contract,
                bound_runtime_inputs["serial_log"],
                bound_runtime_inputs["qemu_log"],
                bound_runtime_inputs["qemu_command"],
                bound_runtime_inputs["qemu_version"],
                bound_runtime_inputs["qemu_exit_code"],
                bound_runtime_inputs["environment_log"],
                bound_runtime_inputs["initramfs"],
                bound_runtime_inputs["initramfs_sha256"],
                bound_build_dir / "bzImage",
                build["bzimage_sha256"],
                build_dir / "bzImage",
                runtime_parent,
            )
            runtime.update(
                _validate_runtime_workflow_provenance(
                    bound_runtime_inputs["workflow_provenance"],
                    bound_runtime_inputs["executed_caller_workflow"],
                    bound_runtime_inputs["executed_runtime_workflow"],
                    execution_workflow,
                    candidate_sha,
                    github_repository,
                )
            )
            value = {
                "schema_version": 1,
                "contract_id": CONTRACT_ID,
                "contract_sha256": summary["contract_sha256"],
                "identity": capture_identity,
                "build": build,
                "runtime": runtime,
                "readiness": {
                    "credit_eligible": False,
                    "gate_status": "NOT_READY",
                    "independent_reviewed": False,
                    "status": "CAPTURED_UNREVIEWED",
                    "blockers": [
                        "GitHub artifact digest must be retained immutably",
                        "independent evidence review must verify and register this exact capture",
                    ],
                },
            }
            value["capture_sha256"] = _sha256_bytes(_canonical_bytes(value))
            validate_capture(value)
            recheck_runtime_inputs()
            if output is not None:
                capture_state["published_identity"] = _write_capture_output(
                    runtime_dir_fd,
                    output,
                    runtime_parent,
                    value,
                    post_publish_check=recheck_runtime_inputs,
                )
            recheck_runtime_inputs()
            return value


def _decode_worker_base64(
    value: Any, label: str, maximum_size: int
) -> bytes:
    if (
        type(value) is not str
        or not value
        or any(ord(character) > 0x7F for character in value)
    ):
        raise EvidenceError("isolated {0} encoding differs".format(label))
    try:
        decoded = base64.b64decode(value.encode("ascii"), validate=True)
    except (TypeError, ValueError) as error:
        raise EvidenceError(
            "isolated {0} is not canonical base64".format(label)
        ) from error
    if (
        not decoded
        or len(decoded) > maximum_size
        or base64.b64encode(decoded).decode("ascii") != value
    ):
        raise EvidenceError("isolated {0} byte boundary differs".format(label))
    return decoded


def _worker_checker_fd() -> int:
    values = [
        argument.split("=", 1)[1]
        for argument in sys.argv[1:]
        if argument.startswith("--checker-fd=")
    ]
    if (
        len(values) != 1
        or not values[0].isdigit()
        or values[0].startswith("0")
        or int(values[0], 10) < 3
    ):
        raise EvidenceError("isolated checker descriptor differs")
    return int(values[0], 10)


def _isolated_semantic_worker_main() -> int:
    try:
        request_bytes = sys.stdin.buffer.read(
            MAX_ISOLATED_SEMANTIC_REQUEST_SIZE + 1
        )
        if (
            not request_bytes
            or len(request_bytes) > MAX_ISOLATED_SEMANTIC_REQUEST_SIZE
        ):
            raise EvidenceError("isolated semantic request size differs")
        request = _decode_canonical_json_bytes(
            request_bytes, "isolated semantic request"
        )
        expected_claims = {
            "credit_eligible": False,
            "gate_pass": False,
            "runtime_proven": False,
            "tracker_credit": False,
        }
        if (
            set(request)
            != {
                "action",
                "authorities",
                "checker",
                "claims",
                "payload",
                "schema_version",
            }
            or type(request["schema_version"]) is not int
            or request["schema_version"] != 1
            or request["action"] not in ("config", "link", "phase2")
            or not _exact_typed_equal(
                request["authorities"],
                EXPECTED_REPOSITORY_SEMANTIC_AUTHORITY_IDENTITIES,
            )
            or not _exact_typed_equal(request["claims"], expected_claims)
            or type(request["payload"]) is not dict
        ):
            raise EvidenceError("isolated semantic request schema differs")
        checker_fd = _worker_checker_fd()
        checker_bytes, checker_identity = _read_bound_descriptor_bytes(
            checker_fd, 2 << 20, "isolated runtime checker source"
        )
        if (
            not _exact_typed_equal(
                request["checker"], _semantic_authority_identity(checker_bytes)
            )
            or _normalized_runtime_checker_sha256(checker_bytes)
            != ISOLATED_SELF_DIGEST
            or _stat_identity(os.stat(__file__)) != checker_identity
        ):
            raise EvidenceError("isolated runtime checker execution identity differs")
        if request["action"] == "config":
            if set(request["payload"]) != {"config_b64"}:
                raise EvidenceError("isolated config request keys differ")
            config_bytes = _decode_worker_base64(
                request["payload"]["config_b64"],
                "config fragment",
                1 << 20,
            )
            try:
                config = config_bytes.decode("utf-8")
            except UnicodeError as error:
                raise EvidenceError(
                    "isolated config fragment is not UTF-8"
                ) from error
            validate_native_rust_evidence_fragment(config)
            payload = {"config_valid": True}
        else:
            expected_payload_keys = {"raw_b64", "stage_lock_b64"}
            if request["action"] == "phase2":
                expected_payload_keys.add("matrix_b64")
            if set(request["payload"]) != expected_payload_keys:
                raise EvidenceError("isolated phase-2 request keys differ")
            raw_encoded = request["payload"]["raw_b64"]
            if type(raw_encoded) is not dict or set(raw_encoded) != set(
                EXPECTED_RAW_RECORD_NAMES
            ):
                raise EvidenceError("isolated raw record set differs")
            raw = {
                name: _decode_worker_base64(
                    raw_encoded[name],
                    "raw record {0}".format(name),
                    MAX_KBUILD_RAW_RECORD_SIZE,
                )
                for name in EXPECTED_RAW_RECORD_NAMES
            }
            stage_raw = _decode_worker_base64(
                request["payload"]["stage_lock_b64"],
                "stage lock",
                MAX_KBUILD_STAGE_LOCK_SIZE,
            )
            payload = {
                "link": _validate_kbuild_link_closure_bytes(raw, stage_raw)
            }
            if request["action"] == "phase2":
                matrix_raw = _decode_worker_base64(
                    request["payload"]["matrix_b64"],
                    "Kconfig solver matrix",
                    16 << 20,
                )
                payload["matrix"] = validate_matrix_bytes(matrix_raw)
        result = {
            "action": request["action"],
            "authorities": copy.deepcopy(
                EXPECTED_REPOSITORY_SEMANTIC_AUTHORITY_IDENTITIES
            ),
            "checker": copy.deepcopy(request["checker"]),
            "claims": expected_claims,
            "payload": payload,
            "request_sha256": _sha256_bytes(request_bytes),
            "schema_version": 1,
        }
        output = _canonical_bytes(result)
        if len(output) > MAX_ISOLATED_SEMANTIC_RESULT_SIZE:
            raise EvidenceError("isolated semantic result is too large")
        sys.stdout.buffer.write(output)
        sys.stdout.buffer.flush()
    except (
        EvidenceError,
        KconfigPolicyError,
        LinkClosureError,
        OSError,
        SolverError,
        TypeError,
        ValueError,
    ) as error:
        sys.stderr.write(
            "isolated runtime semantic validation failed: {0}\n".format(error)
        )
        return 1
    return 0


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=ROOT)
    parser.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT)
    actions = parser.add_mutually_exclusive_group(required=True)
    actions.add_argument("--check-contract", action="store_true")
    actions.add_argument("--check-runtime-evidence", action="store_true")
    actions.add_argument("--capture", action="store_true")
    parser.add_argument("--build-evidence-dir", type=Path)
    parser.add_argument("--serial-log", type=Path)
    parser.add_argument("--qemu-log", type=Path)
    parser.add_argument("--qemu-command", type=Path)
    parser.add_argument("--qemu-version", type=Path)
    parser.add_argument("--qemu-exit-code", type=Path)
    parser.add_argument("--environment-log", type=Path)
    parser.add_argument("--initramfs", type=Path)
    parser.add_argument("--initramfs-sha256", type=Path)
    parser.add_argument("--candidate-sha")
    parser.add_argument("--github-repository")
    parser.add_argument("--github-run-id")
    parser.add_argument("--github-run-attempt")
    parser.add_argument("--github-event-name")
    parser.add_argument("--github-ref")
    parser.add_argument("--github-sha")
    parser.add_argument("--github-workflow-ref")
    parser.add_argument("--github-workflow-sha")
    parser.add_argument("--github-workflow-blob-sha1")
    parser.add_argument("--job-workflow-ref")
    parser.add_argument("--job-workflow-sha")
    parser.add_argument("--job-workflow-repository")
    parser.add_argument("--job-workflow-file-path")
    parser.add_argument("--job-workflow-blob-sha1")
    parser.add_argument("--workflow-provenance", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--runtime-evidence-dir", type=Path)
    parser.add_argument(
        "--modinfo-fd",
        type=int,
        help="inherited descriptor for the identity-bound kmod executable",
    )
    parser.add_argument(
        "--modinfo-sha256",
        help="trusted SHA-256 for the inherited kmod executable descriptor",
    )
    parser.add_argument(
        "--nm-fd",
        type=int,
        help="inherited descriptor for the identity-bound nm executable",
    )
    parser.add_argument(
        "--nm-sha256",
        help="RPM FILEDIGESTS SHA-256 for the inherited nm descriptor",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(sys.argv[1:] if argv is None else argv)
    repo = args.repo.resolve()
    try:
        if args.check_contract:
            if any(
                value is not None
                for value in (
                    args.modinfo_fd,
                    args.modinfo_sha256,
                    args.nm_fd,
                    args.nm_sha256,
                )
            ):
                raise EvidenceError(
                    "tool descriptors and digests are only valid for artifact operations"
                )
            summary = validate_contract(repo, args.contract)
            print(
                "native-rust-runtime-evidence: CONTRACT-VERIFIED "
                "runtime={0}/{1} accelerator={2} credit=FORBIDDEN review=REQUIRED".format(
                    summary["runtime"]["distribution"],
                    summary["runtime"]["release"],
                    summary["runtime"]["qemu_accelerator"],
                )
            )
            return 0
        if args.check_runtime_evidence:
            if (
                args.runtime_evidence_dir is None
                or args.build_evidence_dir is None
                or args.modinfo_fd is None
                or args.modinfo_sha256 is None
                or args.nm_fd is None
                or args.nm_sha256 is None
                or args.workflow_provenance is None
            ):
                raise EvidenceError(
                    "runtime evidence check requires --runtime-evidence-dir and "
                    "--build-evidence-dir and both tool fds and digests"
                )
            records = validate_runtime_evidence_directory(
                repo,
                args.runtime_evidence_dir,
                args.build_evidence_dir,
                args.contract,
                args.modinfo_fd,
                args.nm_fd,
                args.modinfo_sha256,
                args.nm_sha256,
                args.workflow_provenance,
            )
            print(
                "native-rust-runtime-evidence: ARTIFACT-VERIFIED "
                "files={0} credit=FORBIDDEN review=REQUIRED".format(
                    len(records) + 1
                )
            )
            return 0
        required = (
            args.build_evidence_dir,
            args.serial_log,
            args.qemu_log,
            args.qemu_command,
            args.qemu_version,
            args.qemu_exit_code,
            args.environment_log,
            args.initramfs,
            args.initramfs_sha256,
            args.candidate_sha,
            args.github_repository,
            args.github_run_id,
            args.github_run_attempt,
            args.github_event_name,
            args.github_ref,
            args.github_sha,
            args.github_workflow_ref,
            args.github_workflow_sha,
            args.github_workflow_blob_sha1,
            args.job_workflow_ref,
            args.job_workflow_sha,
            args.job_workflow_repository,
            args.job_workflow_file_path,
            args.job_workflow_blob_sha1,
            args.workflow_provenance,
            args.modinfo_fd,
            args.modinfo_sha256,
            args.nm_fd,
            args.nm_sha256,
            args.output,
        )
        if any(value is None for value in required):
            raise EvidenceError("capture requires every build/runtime/run-identity argument")
        value = capture(
            repo,
            args.contract,
            args.build_evidence_dir,
            args.serial_log,
            args.qemu_log,
            args.qemu_command,
            args.qemu_version,
            args.qemu_exit_code,
            args.environment_log,
            args.initramfs,
            args.initramfs_sha256,
            args.candidate_sha,
            args.github_repository,
            args.github_run_id,
            args.github_run_attempt,
            args.github_event_name,
            args.github_ref,
            args.github_sha,
            args.github_workflow_ref,
            args.github_workflow_sha,
            args.github_workflow_blob_sha1,
            args.job_workflow_ref,
            args.job_workflow_sha,
            args.job_workflow_repository,
            args.job_workflow_file_path,
            args.job_workflow_blob_sha1,
            args.workflow_provenance,
            args.modinfo_fd,
            args.nm_fd,
            args.modinfo_sha256,
            args.nm_sha256,
            args.output,
        )
        print(
            "native-rust-runtime-evidence: CAPTURED-UNREVIEWED "
            "credit=FORBIDDEN sha256={0}".format(value["capture_sha256"])
        )
        return 0
    except EvidenceError as error:
        print("native-rust-runtime-evidence: FAIL: {0}".format(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    if "--isolated-semantic-worker" in sys.argv[1:]:
        sys.exit(_isolated_semantic_worker_main())
    sys.exit(main())
