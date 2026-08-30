#!/usr/bin/env python3
"""Validate and capture credit-forbidden native Rust QEMU runtime evidence."""

from __future__ import print_function

import argparse
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
import subprocess
import sys
from typing import Any

if __package__:
    from .native_rust_kbuild_link_closure import (
        EXPECTED_RAW_RECORD_NAMES,
        LinkClosureError,
        check_kbuild_link_closure,
    )
    from .native_rust_kconfig_policy import (
        KconfigPolicyError,
        validate_native_rust_evidence_fragment,
    )
    from .native_rust_kconfig_solver import (
        CAPTURE_STATUS as SOLVER_CAPTURE_STATUS,
        EXPECTED_CLAIMS as SOLVER_EXPECTED_CLAIMS,
        EXPECTED_COUNTS as SOLVER_EXPECTED_COUNTS,
        EXPECTED_LIMITATIONS as SOLVER_EXPECTED_LIMITATIONS,
        SolverError,
        validate_matrix_bytes,
    )
else:
    from native_rust_kbuild_link_closure import (
        EXPECTED_RAW_RECORD_NAMES,
        LinkClosureError,
        check_kbuild_link_closure,
    )
    from native_rust_kconfig_policy import (
        KconfigPolicyError,
        validate_native_rust_evidence_fragment,
    )
    from native_rust_kconfig_solver import (
        CAPTURE_STATUS as SOLVER_CAPTURE_STATUS,
        EXPECTED_CLAIMS as SOLVER_EXPECTED_CLAIMS,
        EXPECTED_COUNTS as SOLVER_EXPECTED_COUNTS,
        EXPECTED_LIMITATIONS as SOLVER_EXPECTED_LIMITATIONS,
        SolverError,
        validate_matrix_bytes,
    )


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONTRACT = Path("host-kernel/contracts/native-rust-runtime-evidence-v1.json")
CONTRACT_ID = "mckernel-native-rust-runtime-evidence-v1"
PROTOCOL = "MCKERNEL_NATIVE_RUST_RUNTIME_V1"
HEX40 = re.compile(r"^[0-9a-f]{40}$")
HEX64 = re.compile(r"^[0-9a-f]{64}$")
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
EXPECTED_PRECHECK_BUILD_MEMBERS = [
    "build-log.exit-code",
    "build.commands",
    "build.environment",
    "build.exit-code",
    "build.log",
    "build.phase",
    "built-module-artifacts.txt",
    "commit.sha",
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
    "workflow-state",
]
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
    "Validate built metadata and capture immutable diagnostics": "0e21676488597055046c958c45379f7bbebcfa5c2a1f1ba97daf30eb2dd18fd2",
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
    "d2a952a91a4c53f555ceb8c96edd6d2bce2375f3c77b09374d51daf38524412b"
)
EXPECTED_REPOSITORY_WORKFLOW_IDENTITIES = {
    "build_workflow": {
        "git_blob_sha1": "00491ca68573cec33b79b84be257e220b27c3cf4",
        "sha256": "a9b85eac8389b2b3c93f1f45955a0624609e55013da54cb609be7b8765687307",
        "size": 71916,
    },
    "runtime_pr_workflow": {
        "git_blob_sha1": "64bb717852d36fc1021e2b61e83aca6415b184d5",
        "sha256": "628e901df2ef4d26978e0280a8ca300d9d58adc57f6c6bde883940706adf2265",
        "size": 754,
    },
    "runtime_workflow": {
        "git_blob_sha1": "0b4685b5142e8162a4cb84fd4fae8b6e57465b5c",
        "sha256": "22ee9651e907bbc45b9f6b02b63981beb61d8e38c23976272535b0608218d150",
        "size": 19359,
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
    resolved = path.resolve()
    if nonempty and not resolved.stat().st_size:
        raise EvidenceError("{0} is empty".format(label))
    return resolved


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


def _stat_identity(metadata: os.stat_result) -> tuple[Any, ...]:
    return (
        metadata.st_dev,
        metadata.st_ino,
        metadata.st_mode,
        metadata.st_size,
        getattr(metadata, "st_mtime_ns", int(metadata.st_mtime * 1000000000)),
        getattr(metadata, "st_ctime_ns", int(metadata.st_ctime * 1000000000)),
    )


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
    next_header = "      - name: Assemble a deterministic lifecycle-only initramfs\n"
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
            "reproducible_build_identity",
            "repository_workflow_identities",
            "runtime",
            "runtime_verifier_scope",
            "schema_version",
            "selected_kernel",
        },
        "contract",
    )
    if contract["schema_version"] != 1:
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
    if contract["build_scope"] != expected_build_scope:
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
    if contract["gate"] != expected_gate:
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
    if contract["runtime"] != expected_runtime:
        raise EvidenceError("runtime identity differs from exact Rocky 10.2 x86_64 TCG")
    if contract["runtime_verifier_scope"] != {
        "initramfs_cpio_replay": False,
        "policy": (
            "Offline validation binds the exact initramfs bytes and checksum record but "
            "does not independently replay cpio membership or the embedded module, init, "
            "and poweroff bytes. Build-to-guest correlation therefore depends on the "
            "sealed exact workflow and outer same-run artifact provenance; this residual "
            "cannot support gate, runtime, durability, or credit claims."
        ),
    }:
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
    if contract["reproducible_build_identity"] != expected_reproducible_identity:
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
            "depends": [],
            "file": "ihk.ko",
            "import_namespace": None,
            "name": "ihk",
            "provider_symbol_definition": "ihk_provider_lifecycle_v1",
        },
        {
            "depends": ["ihk"],
            "file": "ihk-smp-x86_64.ko",
            "import_namespace": "MCKERNEL_IHK_V1",
            "name": "ihk_smp_x86_64",
            "undefined_provider_symbol": "ihk_provider_lifecycle_v1",
        },
        {
            "depends": ["ihk"],
            "file": "mcctrl.ko",
            "import_namespace": "MCKERNEL_IHK_V1",
            "name": "mcctrl",
            "undefined_provider_symbol": "ihk_provider_lifecycle_v1",
        },
    ]
    if contract["modules"] != expected_modules:
        raise EvidenceError("runtime module graph differs")
    if contract["protocol"] != {
        "load_order": ["ihk", "ihk_smp_x86_64", "mcctrl"],
        "provider_refcount_after_load": 2,
        "provider_refcounts": {
            "after_load": 2,
            "after_mcctrl_unload": 1,
            "after_negative": 2,
            "after_smp_unload": 0,
        },
        "provider_unload_expected_diagnostic": "Module ihk is in use",
        "provider_unload_expected_status": 1,
        "provider_unload_while_referenced_must_fail": True,
        "serial_protocol": PROTOCOL,
        "unload_order": ["mcctrl", "ihk_smp_x86_64", "ihk"],
    }:
        raise EvidenceError("runtime load/refcount/unload protocol differs")

    artifacts = contract["artifact_contract"]
    _require_keys(
        artifacts,
        {
            "build_evidence_files",
            "capture_status",
            "immutable_artifact_digest_required",
            "independent_review_status",
            "runtime_evidence_files",
        },
        "artifact_contract",
    )
    if (
        artifacts["capture_status"] != "required-missing"
        or artifacts["independent_review_status"] != "required-missing"
        or artifacts["immutable_artifact_digest_required"] is not True
    ):
        raise EvidenceError("repository contract must remain uncaptured and unreviewed")
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
        "workflow-state",
    ]
    expected_runtime_evidence = [
        "SHA256SUMS",
        "capture.json",
        "environment.txt",
        "initramfs.cpio.gz",
        "initramfs.sha256",
        "native-rust-runtime-poweroff.o",
        "qemu-command.txt",
        "qemu-version.txt",
        "qemu.exit-code",
        "qemu.log",
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
            "kconfig_solver",
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
        "kconfig_solver": "scripts/native_rust_kconfig_solver.py",
        "poweroff": "scripts/native-rust-runtime-poweroff.S",
        "runtime_pr_workflow": ".github/workflows/native-rust-host-modules-exact-runtime-pr.yml",
        "runtime_workflow": ".github/workflows/native-rust-host-modules-exact-runtime.yml",
        "source_lock": "host-kernel/rocky/source-lock.json",
    }
    if inputs != expected_inputs:
        raise EvidenceError("runtime repository input paths differ")
    workflow_identities = contract["repository_workflow_identities"]
    if workflow_identities != EXPECTED_REPOSITORY_WORKFLOW_IDENTITIES:
        raise EvidenceError("runtime repository workflow identities differ")
    _repo_file(repo, inputs["kbuild_link_closure"], "Kbuild link-closure checker")
    _repo_file(repo, inputs["kconfig_solver"], "Kconfig solver")

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
    init = _read_text(_repo_file(repo, inputs["init"], "runtime init"), "runtime init")
    poweroff = _read_text(
        _repo_file(repo, inputs["poweroff"], "runtime poweroff"), "runtime poweroff"
    )
    config = _read_text(
        _repo_file(repo, inputs["config_fragment"], "runtime config fragment"),
        "runtime config fragment",
    )
    try:
        validate_native_rust_evidence_fragment(config)
    except KconfigPolicyError as error:
        raise EvidenceError(
            "runtime config fragment policy violation: {0}".format(error)
        ) from error
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
        "technical-capture-unreviewed credit=forbidden",
        "NEGATIVE operation=unload-provider-first",
        "STATE_BEGIN label=$label",
        "DMESG_BEGIN",
        "@EXPECTED_KERNEL_RELEASE@",
    ):
        if fragment not in init:
            raise EvidenceError("runtime init lacks evidence marker: {0}".format(fragment))
    active_init = _active_shell_lines(init)
    canonical_pair = "mcctrl,ihk_smp_x86_64,|ihk_smp_x86_64,mcctrl,) ;;"
    if active_init.count(canonical_pair) != 2:
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


def _parse_sums(directory: Path) -> dict[str, str]:
    sums_path = directory / "SHA256SUMS"
    if sums_path.is_symlink() or not sums_path.is_file():
        raise EvidenceError("build evidence lacks regular SHA256SUMS")
    records: dict[str, str] = {}
    ordered: list[str] = []
    for line in _read_text(sums_path, "build SHA256SUMS").splitlines():
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
    for line in _read_text(
        precheck_path, "build PRECHECK_SHA256SUMS"
    ).splitlines():
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
    directory: Path, records: dict[str, str], expected: list[str]
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


def _validate_phase2_build_evidence(
    directory: Path, records: dict[str, str]
) -> dict[str, Any]:
    matrix_path = directory / "kconfig-solver-matrix.json"
    matrix_bytes = _read_regular_evidence_bytes(
        matrix_path, "Kconfig solver matrix"
    )
    if _sha256_bytes(matrix_bytes) != records["kconfig-solver-matrix.json"]:
        raise EvidenceError("Kconfig solver matrix digest differs from SHA256SUMS")
    try:
        matrix = validate_matrix_bytes(matrix_bytes)
    except SolverError as error:
        raise EvidenceError("Kconfig solver matrix is invalid: {0}".format(error)) from error

    link_path = directory / "kbuild-link-closure.json"
    try:
        link = check_kbuild_link_closure(
            str(directory), str(link_path), stage_lock_path=str(directory / "stage-lock.json")
        )
    except LinkClosureError as error:
        raise EvidenceError("Kbuild link closure is invalid: {0}".format(error)) from error
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


def _modinfo_execution(modinfo_fd: int | None) -> tuple[str, tuple[int, ...]]:
    if modinfo_fd is None:
        return MODINFO_EXECUTABLE, ()
    if type(modinfo_fd) is not int or modinfo_fd < 3:
        raise EvidenceError("modinfo descriptor must be an open integer fd >= 3")
    try:
        descriptor_status = os.fstat(modinfo_fd)
        executable_status = os.stat("/proc/self/fd/{0}".format(modinfo_fd))
    except OSError as error:
        raise EvidenceError("modinfo descriptor is unavailable: {0}".format(error)) from error
    if (
        not stat.S_ISREG(descriptor_status.st_mode)
        or descriptor_status.st_dev != executable_status.st_dev
        or descriptor_status.st_ino != executable_status.st_ino
    ):
        raise EvidenceError("modinfo descriptor must identify one regular file")
    if stat.S_IMODE(descriptor_status.st_mode) & 0o111 == 0:
        raise EvidenceError("modinfo descriptor target is not executable")
    return "/proc/self/fd/{0}".format(modinfo_fd), (modinfo_fd,)


def _run_field(
    module: Path, field: str, modinfo_fd: int | None = None
) -> list[str]:
    executable, pass_fds = _modinfo_execution(modinfo_fd)
    try:
        result = subprocess.run(
            ["modinfo", "-F", field, str(module)],
            check=False,
            env=dict(BOUND_ROCKY_TOOL_ENVIRONMENT),
            executable=executable,
            pass_fds=pass_fds,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
    except OSError as error:
        raise EvidenceError("bound Rocky modinfo is unavailable: {0}".format(error)) from error
    if result.returncode != 0:
        raise EvidenceError("modinfo failed for {0}:{1}".format(module.name, field))
    return [line for line in result.stdout.splitlines() if line]


def _module_vermagic_release(
    module: Path, modinfo_fd: int | None = None
) -> str:
    if modinfo_fd is None:
        records = _run_field(module, "vermagic")
    else:
        records = _run_field(module, "vermagic", modinfo_fd=modinfo_fd)
    if len(records) != 1 or not records[0].split():
        raise EvidenceError("{0} vermagic record differs".format(module.name))
    release = records[0].split()[0]
    if release != EXPECTED_KERNEL_RELEASE:
        raise EvidenceError("{0} vermagic release differs".format(module.name))
    return release


def _nm(module: Path, arguments: list[str]) -> str:
    try:
        result = subprocess.run(
            [NM_EXECUTABLE] + arguments + [str(module)],
            check=False,
            env=dict(BOUND_ROCKY_TOOL_ENVIRONMENT),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
    except OSError as error:
        raise EvidenceError("bound Rocky nm is unavailable: {0}".format(error)) from error
    if result.returncode != 0:
        raise EvidenceError("nm failed for {0}".format(module.name))
    return result.stdout


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


def _state_modules(text: str, label: str) -> dict[str, str]:
    begin = "{0} STATE_BEGIN label={1}".format(PROTOCOL, label)
    end = "{0} STATE_END label={1}".format(PROTOCOL, label)
    if text.splitlines().count(begin) != 1 or text.splitlines().count(end) != 1:
        raise EvidenceError("runtime state frame differs: {0}".format(label))
    start = text.index(begin) + len(begin)
    finish = text.index(end, start)
    records: dict[str, str] = {}
    for line in text[start:finish].splitlines():
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


def validate_serial(serial_path: Path, kernel_release: str) -> dict[str, Any]:
    if serial_path.is_symlink() or not serial_path.is_file():
        raise EvidenceError("serial log must be a regular non-symlink file")
    data = serial_path.read_bytes()
    if not data:
        raise EvidenceError("serial log is empty")
    text = data.decode("utf-8", errors="replace").replace("\r\n", "\n")
    lines = text.splitlines()
    for line in lines:
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
    release = "{0} KERNEL_RELEASE actual={1} expected={1}".format(PROTOCOL, kernel_release)
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
        ("negative output begin", "{0} NEGATIVE_OUTPUT_BEGIN".format(PROTOCOL)),
        ("negative output end", "{0} NEGATIVE_OUTPUT_END".format(PROTOCOL)),
        ("after-negative state begin", "{0} STATE_BEGIN label=after-negative".format(PROTOCOL)),
        ("after-negative state end", "{0} STATE_END label=after-negative".format(PROTOCOL)),
        ("mcctrl unload", "{0} UNLOAD module=mcctrl status=ok".format(PROTOCOL)),
        ("smp unload", "{0} UNLOAD module=ihk_smp_x86_64 status=ok".format(PROTOCOL)),
        ("ihk unload", "{0} UNLOAD module=ihk status=ok".format(PROTOCOL)),
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
            "{0} REFCOUNT module=ihk phase=after-smp-unload references=".format(PROTOCOL),
        ),
    ]
    marker_positions.update(
        {
            label: _unique_prefixed_line(lines, prefix, label)
            for label, prefix in prefixed_runtime_markers
        }
    )
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
        "negative unload",
        "negative output begin",
        "negative output end",
        "after-negative refcount",
        "after-negative state begin",
        "after-negative state end",
        "mcctrl unload",
        "after-mcctrl refcount",
        "smp unload",
        "after-smp refcount",
        "ihk unload",
        "final state begin",
        "final state end",
        "dmesg begin",
        "dmesg end",
        "complete",
    ]
    positions = [marker_positions[label] for label in ordered_marker_labels]
    if len(set(positions)) != len(positions) or positions != sorted(positions):
        raise EvidenceError("serial runtime markers are missing or out of order")
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
    negative_begin = "{0} NEGATIVE_OUTPUT_BEGIN".format(PROTOCOL)
    negative_end = "{0} NEGATIVE_OUTPUT_END".format(PROTOCOL)
    negative_start = _unique_exact_line(lines, negative_begin, "negative output begin")
    negative_finish = _unique_exact_line(lines, negative_end, "negative output end")
    negative_lines = lines[negative_start + 1 : negative_finish]
    negative_diagnostic = re.compile(
        r"^rmmod: ERROR: Module ihk is in use by: "
        r"(?:mcctrl ihk_smp_x86_64|ihk_smp_x86_64 mcctrl)$"
    )
    if len(negative_lines) != 1 or negative_diagnostic.fullmatch(
        negative_lines[0]
    ) is None:
        raise EvidenceError("provider-first unload lacks the in-use diagnostic")
    expected_modules = {"ihk", "ihk_smp_x86_64", "mcctrl"}
    initial = _state_modules(text, "initial-clean")
    all_loaded = _state_modules(text, "all-loaded")
    after_negative = _state_modules(text, "after-negative")
    final = _state_modules(text, "final-clean")
    if initial or final:
        raise EvidenceError("initial or final runtime state retains a native module")
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
            raise EvidenceError(
                "{0} /proc/modules provider state differs".format(label)
            )

    lifecycle = [
        "ihk: lifecycle=load version=1.7.0rc4 abi=1 parameters=0 dependencies=0",
        (
            "ihk_smp_x86_64: lifecycle=load parameters=6 dependency=ihk "
            "import_namespace=MCKERNEL_IHK_V1"
        ),
        (
            "mcctrl: lifecycle=load foundation=1 parameters=0 declared_dependencies=1 "
            "ihk_import=source-bound-anchor binfmt=blocked-no-safe-rust-api"
        ),
        (
            "mcctrl: lifecycle=unload foundation=1 parameters=0 declared_dependencies=1 "
            "ihk_import=source-bound-anchor binfmt=blocked-no-safe-rust-api"
        ),
        (
            "ihk_smp_x86_64: lifecycle=unload parameters=6 dependency=ihk "
            "import_namespace=MCKERNEL_IHK_V1"
        ),
        "ihk: lifecycle=unload version=1.7.0rc4 abi=1 parameters=0 dependencies=0",
    ]
    dmesg_lines = lines[
        marker_positions["dmesg begin"] + 1 : marker_positions["dmesg end"]
    ]
    lifecycle_positions = []
    for marker in lifecycle:
        expression = re.compile(
            r"^(?:\[\s*[0-9]+(?:\.[0-9]+)?\]\s+)?"
            + re.escape(marker)
            + r"$"
        )
        matches = [
            index
            for index, line in enumerate(dmesg_lines)
            if expression.fullmatch(line) is not None
        ]
        if len(matches) != 1:
            raise EvidenceError("lifecycle diagnostics are missing or duplicated")
        lifecycle_positions.append(matches[0])
    if lifecycle_positions != sorted(lifecycle_positions):
        raise EvidenceError("lifecycle diagnostics are missing or out of order")
    return {
        "kernel_release": kernel_release,
        "negative_unload_status": int(negative_records[0].group(1)),
        "provider_refcount": 2,
        "provider_users": ["ihk_smp_x86_64", "mcctrl"],
        "serial_sha256": _sha256_file(serial_path),
    }


def _require_sha256_value(value: Any, label: str) -> str:
    if type(value) is not str or HEX64.fullmatch(value) is None:
        raise EvidenceError("{0} must be exact SHA-256 text".format(label))
    return value


def _validate_capture_content(value: dict[str, Any]) -> None:
    _require_sha256_value(value["contract_sha256"], "capture contract digest")
    identity = value["identity"]
    _require_keys(
        identity,
        {"candidate_sha", "github_repository", "github_run_attempt", "github_run_id"},
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
        if type(item) is not str or not item.isdigit() or int(item) < 1:
            raise EvidenceError("capture {0} differs".format(key))

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
        "ihk": {"depends": [], "import_namespaces": []},
        "ihk_smp_x86_64": {
            "depends": ["ihk"],
            "import_namespaces": ["MCKERNEL_IHK_V1"],
        },
        "mcctrl": {
            "depends": ["ihk"],
            "import_namespaces": ["MCKERNEL_IHK_V1"],
        },
    }
    for name, expected in expected_module_facts.items():
        record = modules[name]
        _require_keys(record, {"depends", "import_namespaces", "sha256"}, name)
        if record["depends"] != expected["depends"] or record[
            "import_namespaces"
        ] != expected["import_namespaces"]:
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
        "initramfs_sha256",
        "initramfs_sha256_record",
        "qemu_command_sha256",
        "qemu_exit_code_sha256",
        "qemu_log_sha256",
        "qemu_version_sha256",
        "serial_sha256",
    }
    _require_keys(
        runtime,
        runtime_digests
        | {"kernel_release", "negative_unload_status", "provider_refcount", "provider_users"},
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
    if readiness != {
        "credit_eligible": False,
        "gate_status": "NOT_READY",
        "independent_reviewed": False,
        "status": "CAPTURED_UNREVIEWED",
        "blockers": [
            "GitHub artifact digest must be retained immutably",
            "independent evidence review must verify and register this exact capture",
        ],
    }:
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
            build_argv_path != expected_bzimage
            or initramfs_argv_path != initramfs
            or serial_argv_path != serial_log
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


def _validate_build_evidence_directory(
    contract: dict[str, Any],
    build_dir: Path,
    candidate_sha: str,
    modinfo_fd: int | None = None,
) -> tuple[dict[str, Any], dict[str, str]]:
    build_dir = _regular_evidence_directory(build_dir, "build evidence directory")
    initial_directory_identity = _stat_identity(build_dir.lstat())
    records = _parse_sums(build_dir)
    initial_file_identities = _validate_exact_build_artifact_files(
        build_dir,
        records,
        contract["artifact_contract"]["build_evidence_files"],
    )
    _parse_precheck_sums(build_dir, records, EXPECTED_PRECHECK_BUILD_MEMBERS)
    phase2 = _validate_phase2_build_evidence(build_dir, records)
    build_scope = _validate_build_scope_artifacts(build_dir, records)
    commit = _read_text(build_dir / "commit.sha", "build commit").strip()
    if commit != candidate_sha:
        raise EvidenceError("build artifact commit differs from runtime candidate")
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
        path = build_dir / item["file"]
        if modinfo_fd is None:
            depends = _run_field(path, "depends")
            namespaces = _run_field(path, "import_ns")
            vermagic_release = _module_vermagic_release(path)
        else:
            depends = _run_field(path, "depends", modinfo_fd=modinfo_fd)
            namespaces = _run_field(path, "import_ns", modinfo_fd=modinfo_fd)
            vermagic_release = _module_vermagic_release(path, modinfo_fd=modinfo_fd)
        if depends != item["depends"]:
            raise EvidenceError(
                "{0} dependency metadata differs".format(item["file"])
            )
        expected_ns = (
            [] if item["import_namespace"] is None else [item["import_namespace"]]
        )
        if namespaces != expected_ns:
            raise EvidenceError(
                "{0} import namespace differs".format(item["file"])
            )
        if vermagic_release != kernel_release:
            raise EvidenceError(
                "{0} vermagic/build release differs".format(item["file"])
            )
        if "provider_symbol_definition" in item:
            symbols = _nm(path, ["-g", "--defined-only"])
            symbol = item["provider_symbol_definition"]
            expression = r"\b[A-Z]\s+{0}$".format(re.escape(symbol))
            diagnostic = "provider anchor definition is absent"
        else:
            symbols = _nm(path, ["-u"])
            symbol = item["undefined_provider_symbol"]
            expression = r"\bU\s+{0}$".format(re.escape(symbol))
            diagnostic = "consumer provider-anchor relocation is absent"
        if not re.search(expression, symbols, re.MULTILINE):
            raise EvidenceError(diagnostic)
        modules[item["name"]] = {
            "depends": depends,
            "import_namespaces": namespaces,
            "sha256": records[item["file"]],
        }

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
    final_directory = _regular_evidence_directory(
        build_dir, "build evidence directory"
    )
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
        _stat_identity(final_directory.lstat()) != initial_directory_identity
        or final_file_identities != initial_file_identities
        or final_records != records
    ):
        raise EvidenceError("build artifact changed while it was validated")
    return build, records


def validate_runtime_evidence_directory(
    repo: Path,
    directory: Path,
    build_dir: Path,
    contract_relative: Path = DEFAULT_CONTRACT,
    modinfo_fd: int | None = None,
) -> dict[str, str]:
    summary = validate_contract(repo.resolve(), contract_relative)
    contract = _load_json(repo.resolve() / contract_relative)
    directory = _regular_evidence_directory(directory, "runtime evidence directory")
    initial_directory_identity = _stat_identity(directory.lstat())
    records = _parse_sums(directory)
    expected = contract["artifact_contract"]["runtime_evidence_files"]
    initial_file_identities = _validate_exact_build_artifact_files(
        directory, records, expected
    )

    capture_document = _load_json(directory / "capture.json")
    validate_capture(capture_document)
    if capture_document["contract_sha256"] != summary["contract_sha256"]:
        raise EvidenceError("runtime capture contract digest differs")
    replayed_build, _build_records = _validate_build_evidence_directory(
        contract,
        build_dir,
        capture_document["identity"]["candidate_sha"],
        modinfo_fd,
    )
    if replayed_build != capture_document["build"]:
        raise EvidenceError("runtime capture build evidence facts differ")
    expected_runtime_digests = {
        "environment_sha256": records["environment.txt"],
        "initramfs_sha256": records["initramfs.cpio.gz"],
        "initramfs_sha256_record": records["initramfs.sha256"],
        "qemu_command_sha256": records["qemu-command.txt"],
        "qemu_exit_code_sha256": records["qemu.exit-code"],
        "qemu_log_sha256": records["qemu.log"],
        "qemu_version_sha256": records["qemu-version.txt"],
        "serial_sha256": records["serial.log"],
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
    )
    if replayed != runtime:
        raise EvidenceError("runtime capture semantic facts differ")
    if _read_text(directory / "workflow-state", "runtime workflow state") != (
        "technical-capture-unreviewed\ncredit=forbidden\n"
    ):
        raise EvidenceError("runtime workflow state differs")
    final_directory = _regular_evidence_directory(
        directory, "runtime evidence directory"
    )
    final_records = _parse_sums(final_directory)
    final_file_identities = _validate_exact_build_artifact_files(
        final_directory, final_records, expected
    )
    if (
        _stat_identity(final_directory.lstat()) != initial_directory_identity
        or final_file_identities != initial_file_identities
        or final_records != records
    ):
        raise EvidenceError("runtime evidence changed while it was validated")
    return records


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
    modinfo_fd: int | None = None,
) -> dict[str, Any]:
    summary = validate_contract(repo, contract_relative)
    if not HEX40.fullmatch(candidate_sha):
        raise EvidenceError("candidate SHA must be exact 40-hex")
    if (
        not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", github_repository)
        or not github_run_id.isdigit()
        or int(github_run_id) < 1
        or not github_run_attempt.isdigit()
        or int(github_run_attempt) < 1
    ):
        raise EvidenceError("GitHub run identity is incomplete")
    contract = _load_json(repo / contract_relative)
    bound_build_dir = _regular_evidence_directory(
        build_dir, "build evidence directory"
    )
    build, _build_records = _validate_build_evidence_directory(
        contract, bound_build_dir, candidate_sha, modinfo_fd
    )

    runtime = _validate_runtime_files(
        contract,
        serial_log,
        qemu_log,
        qemu_command,
        qemu_version,
        qemu_exit_code,
        environment_log,
        initramfs,
        initramfs_sha256,
        bound_build_dir / "bzImage",
    )
    value = {
        "schema_version": 1,
        "contract_id": CONTRACT_ID,
        "contract_sha256": summary["contract_sha256"],
        "identity": {
            "candidate_sha": candidate_sha,
            "github_repository": github_repository,
            "github_run_attempt": github_run_attempt,
            "github_run_id": github_run_id,
        },
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
    return value


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
    parser.add_argument("--output", type=Path)
    parser.add_argument("--runtime-evidence-dir", type=Path)
    parser.add_argument(
        "--modinfo-fd",
        type=int,
        help="inherited descriptor for the identity-bound kmod executable",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(sys.argv[1:] if argv is None else argv)
    repo = args.repo.resolve()
    try:
        if args.check_contract:
            if args.modinfo_fd is not None:
                raise EvidenceError("--modinfo-fd is only valid for artifact operations")
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
            ):
                raise EvidenceError(
                    "runtime evidence check requires --runtime-evidence-dir and "
                    "--build-evidence-dir and --modinfo-fd"
                )
            records = validate_runtime_evidence_directory(
                repo,
                args.runtime_evidence_dir,
                args.build_evidence_dir,
                args.contract,
                args.modinfo_fd,
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
            args.modinfo_fd,
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
            args.modinfo_fd,
        )
        if args.output.exists() or args.output.is_symlink():
            raise EvidenceError("capture output already exists or is a symlink")
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(_pretty(value), encoding="utf-8")
        print(
            "native-rust-runtime-evidence: CAPTURED-UNREVIEWED "
            "credit=FORBIDDEN sha256={0}".format(value["capture_sha256"])
        )
        return 0
    except EvidenceError as error:
        print("native-rust-runtime-evidence: FAIL: {0}".format(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
