#!/usr/bin/env python3
"""Validate and capture credit-forbidden native Rust QEMU runtime evidence."""

from __future__ import print_function

import argparse
import copy
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


def _pretty(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True) + "\n"


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError as error:
        raise EvidenceError("cannot hash {0}: {1}".format(path, error)) from error
    return digest.hexdigest()


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
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        raise EvidenceError("cannot read {0}: {1}".format(label, error)) from error


def _validate_rk006_capture_job(job_text: str) -> None:
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
        "        shell: bash\n"
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
        "Reacquire and capture the full external 25-patch source replay",
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


def _validate_exact_build_workflow(text: str) -> str:
    capture_separator = "\n  rk006-full-source-build-capture:\n"
    if text.count(capture_separator) != 1:
        raise EvidenceError("exact build workflow must contain one trailing RK-006 capture job")
    exact_build_text, capture_tail = text.split(capture_separator, 1)
    _validate_rk006_capture_job(
        "  rk006-full-source-build-capture:\n" + capture_tail
    )
    text = exact_build_text
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
            'O="$NATIVE_BUILD_DIR" ARCH=x86_64 LLVM=1 rustavailable'
        ),
        (
            'run_phase bzImage make -C "$NATIVE_SOURCE_ROOT" '
            'O="$NATIVE_BUILD_DIR" ARCH=x86_64 LLVM=1 -j2 bzImage'
        ),
        (
            'run_phase native-modules make -C "$NATIVE_SOURCE_ROOT" '
            'O="$NATIVE_BUILD_DIR" ARCH=x86_64 LLVM=1 -j2 "${module_targets[@]}"'
        ),
    ]
    resolution_header = "      - name: Resolve the evidence-only module configuration twice\n"
    if text.count(resolution_header) != 1:
        raise EvidenceError("exact build workflow CONFIG_MODULES prerequisite differs")
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
        'mkdir -p "$BUILD_DIR"',
        'cp "$NATIVE_BASELINE_CONFIG" "$BUILD_DIR/.config"',
        '"$NATIVE_SOURCE_ROOT/scripts/kconfig/merge_config.sh" -m -O "$BUILD_DIR" \\',
        '"$BUILD_DIR/.config" \\',
        '"$GITHUB_WORKSPACE/host-kernel/rocky/configs/rust-minimal.config" \\',
        '"$GITHUB_WORKSPACE/host-kernel/rocky/configs/native-rust-evidence.config"',
        'make -C "$NATIVE_SOURCE_ROOT" O="$BUILD_DIR" ARCH=x86_64 LLVM=1 olddefconfig',
        'cp "$BUILD_DIR/.config" "$BUILD_DIR/resolved-first.config"',
        'make -C "$NATIVE_SOURCE_ROOT" O="$BUILD_DIR" ARCH=x86_64 LLVM=1 olddefconfig',
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
        "set -uo pipefail",
        'evidence_dir="$RUNNER_TEMP/native-rust-build-evidence"',
        'mkdir -p "$evidence_dir"',
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
        "ARCH=x86_64 LLVM=1 rustavailable",
        "run_phase bzImage \\",
        'make -C "$NATIVE_SOURCE_ROOT" O="$NATIVE_BUILD_DIR" \\',
        "ARCH=x86_64 LLVM=1 -j2 bzImage",
        "run_phase native-modules \\",
        'make -C "$NATIVE_SOURCE_ROOT" O="$NATIVE_BUILD_DIR" \\',
        'ARCH=x86_64 LLVM=1 -j2 "${module_targets[@]}"',
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
        'make -s -C "$NATIVE_SOURCE_ROOT" O="$NATIVE_BUILD_DIR" ARCH=x86_64 LLVM=1 \\',
        'kernelrelease > "$EVIDENCE_DIR/kernel.release"',
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
            "runtime",
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
        "qemu_accelerator": "tcg",
        "required_kernel_config": EXPECTED_RUNTIME_REQUIRED_CONFIG,
        "release": "10.2",
    }
    if contract["runtime"] != expected_runtime:
        raise EvidenceError("runtime identity differs from exact Rocky 10.2 x86_64 TCG")

    selected = contract["selected_kernel"]
    if selected != {
        "archive_sha256": "4a174d47b8874a2139efcd1ac1ab2d6b80ae7a0ca62f0ae4596fd20cf62a3533",
        "nvr": "kernel-6.12.0-211.44.1.el10_2",
        "source_lock_id": "rocky-10.2-x86_64-kernel-6.12.0-211.44.1.el10_2-source-v1",
    }:
        raise EvidenceError("selected kernel identity differs")
    source_lock = _load_json(
        _repo_file(repo, contract["repository_inputs"]["source_lock"], "source lock")
    )
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
        "qemu-command.txt",
        "qemu.exit-code",
        "qemu.log",
        "qemu-version.txt",
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
        "runtime_workflow": ".github/workflows/native-rust-host-modules-exact-runtime.yml",
        "source_lock": "host-kernel/rocky/source-lock.json",
    }
    if inputs != expected_inputs:
        raise EvidenceError("runtime repository input paths differ")
    _repo_file(repo, inputs["kbuild_link_closure"], "Kbuild link-closure checker")
    _repo_file(repo, inputs["kconfig_solver"], "Kconfig solver")
    build_workflow = _read_text(
        _repo_file(repo, inputs["build_workflow"], "exact build workflow"),
        "exact build workflow",
    )
    runtime_workflow = _read_text(
        _repo_file(repo, inputs["runtime_workflow"], "runtime workflow"),
        "runtime workflow",
    )
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
    if "permissions:" not in runtime_workflow:
        raise EvidenceError("runtime capture workflow lacks an explicit permission boundary")
    trigger_block = runtime_workflow[: runtime_workflow.index("permissions:")]
    trigger_events = re.findall(r"(?m)^  ([a-z_]+):", trigger_block)
    if trigger_events != ["workflow_dispatch"]:
        raise EvidenceError("runtime capture workflow must remain manual-only")
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
    for line in _read_text(sums_path, "build SHA256SUMS").splitlines():
        match = re.fullmatch(r"([0-9a-f]{64})  ([A-Za-z0-9._-]+)", line)
        if (
            not match
            or match.group(2) in records
            or match.group(2) in {".", "..", "SHA256SUMS"}
        ):
            raise EvidenceError("malformed or duplicate build SHA256SUMS entry")
        records[match.group(2)] = match.group(1)
    if not records:
        raise EvidenceError("build SHA256SUMS is empty")
    for name, digest in records.items():
        path = directory / name
        if path.is_symlink() or not path.is_file() or _sha256_file(path) != digest:
            raise EvidenceError("build evidence digest differs for {0}".format(name))
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
    if any(len(command) < 7 for command in commands):
        raise EvidenceError("exact build command record is truncated")

    sources = [command[2] for command in commands]
    outputs = [command[3][2:] if command[3].startswith("O=") else "" for command in commands]
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

    prefix = ["make", "-C", sources[0], "O=" + outputs[0], "ARCH=x86_64", "LLVM=1"]
    expected_commands = [
        prefix + ["rustavailable"],
        prefix + ["-j2", "bzImage"],
        prefix + ["-j2"] + BUILD_MODULE_TARGETS,
    ]
    if commands != expected_commands:
        raise EvidenceError("exact build commands exceed the bounded target scope")
    return {
        "build_commands_sha256": records["build.commands"],
        "build_log_sha256": records["build.log"],
        "kernel_targets": BUILD_KERNEL_TARGETS,
        "module_targets": BUILD_MODULE_TARGETS,
    }


def _run_field(module: Path, field: str) -> list[str]:
    executable = shutil.which("modinfo")
    if executable is None:
        raise EvidenceError("modinfo is required to capture runtime evidence")
    result = subprocess.run(
        [executable, "-F", field, str(module)],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if result.returncode != 0:
        raise EvidenceError("modinfo failed for {0}:{1}".format(module.name, field))
    return [line for line in result.stdout.splitlines() if line]


def _nm(module: Path, arguments: list[str]) -> str:
    executable = shutil.which("nm")
    if executable is None:
        raise EvidenceError("nm is required to capture runtime evidence")
    result = subprocess.run(
        [executable] + arguments + [str(module)],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
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
    users = {item for item in records[0][1].strip(",").split(",") if item != "-"}
    return references, users


def _state_provider_record(modules: dict[str, str], label: str) -> tuple[int, set[str]]:
    fields = modules.get("ihk", "").split()
    if len(fields) < 4 or not fields[1].isdigit():
        raise EvidenceError("provider /proc/modules state differs for {0}".format(label))
    references = int(fields[1])
    users = {item for item in fields[2].strip(",").split(",") if item != "-"}
    return references, users


def validate_serial(serial_path: Path, kernel_release: str) -> dict[str, Any]:
    if serial_path.is_symlink() or not serial_path.is_file():
        raise EvidenceError("serial log must be a regular non-symlink file")
    data = serial_path.read_bytes()
    if not data:
        raise EvidenceError("serial log is empty")
    text = data.decode("utf-8", errors="replace").replace("\r\n", "\n")
    complete = "{0} COMPLETE status=technical-capture-unreviewed credit=forbidden".format(
        PROTOCOL
    )
    if text.count(complete) != 1 or "{0} INCOMPLETE".format(PROTOCOL) in text:
        raise EvidenceError("serial protocol is incomplete or duplicated")
    release = "{0} KERNEL_RELEASE actual={1} expected={1}".format(PROTOCOL, kernel_release)
    if text.count(release) != 1:
        raise EvidenceError("guest did not boot the exact built kernel release")

    runtime_markers = [
        "{0} BEGIN".format(PROTOCOL),
        "{0} STATE_BEGIN label=initial-clean".format(PROTOCOL),
        "{0} LOAD module=ihk status=ok".format(PROTOCOL),
        "{0} LOAD module=ihk_smp_x86_64 status=ok".format(PROTOCOL),
        "{0} LOAD module=mcctrl status=ok".format(PROTOCOL),
        "{0} STATE_BEGIN label=all-loaded".format(PROTOCOL),
        "{0} REFCOUNT module=ihk phase=all-loaded references=2 ".format(PROTOCOL),
        "{0} NEGATIVE operation=unload-provider-first status=".format(PROTOCOL),
        "{0} REFCOUNT module=ihk phase=after-negative references=2 ".format(PROTOCOL),
        "{0} STATE_BEGIN label=after-negative".format(PROTOCOL),
        "{0} UNLOAD module=mcctrl status=ok".format(PROTOCOL),
        "{0} REFCOUNT module=ihk phase=after-mcctrl-unload references=1 ".format(
            PROTOCOL
        ),
        "{0} UNLOAD module=ihk_smp_x86_64 status=ok".format(PROTOCOL),
        "{0} REFCOUNT module=ihk phase=after-smp-unload references=0 ".format(PROTOCOL),
        "{0} UNLOAD module=ihk status=ok".format(PROTOCOL),
        "{0} STATE_BEGIN label=final-clean".format(PROTOCOL),
        "{0} DMESG_BEGIN".format(PROTOCOL),
        "{0} DMESG_END".format(PROTOCOL),
        complete,
    ]
    positions = [text.find(marker) for marker in runtime_markers]
    if any(position < 0 for position in positions) or positions != sorted(positions):
        raise EvidenceError("serial runtime markers are missing or out of order")
    negative = re.search(
        re.escape(PROTOCOL) + r" NEGATIVE operation=unload-provider-first status=([0-9]+)",
        text,
    )
    if negative is None or int(negative.group(1)) != 1:
        raise EvidenceError("provider-first unload negative test did not fail")
    negative_begin = "{0} NEGATIVE_OUTPUT_BEGIN".format(PROTOCOL)
    negative_end = "{0} NEGATIVE_OUTPUT_END".format(PROTOCOL)
    if text.splitlines().count(negative_begin) != 1 or text.splitlines().count(
        negative_end
    ) != 1:
        raise EvidenceError("provider-first unload diagnostic frame differs")
    negative_start = text.index(negative_begin) + len(negative_begin)
    negative_finish = text.index(negative_end, negative_start)
    if "Module ihk is in use" not in text[negative_start:negative_finish]:
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
    if _state_provider_record(all_loaded, "all-loaded") != expected_refcounts["all-loaded"]:
        raise EvidenceError("all-loaded /proc/modules provider state differs")
    if _state_provider_record(after_negative, "after-negative") != expected_refcounts[
        "after-negative"
    ]:
        raise EvidenceError("negative test changed /proc/modules provider state")

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
    lifecycle_positions = [text.find(marker) for marker in lifecycle]
    if any(position < 0 for position in lifecycle_positions) or lifecycle_positions != sorted(
        lifecycle_positions
    ):
        raise EvidenceError("lifecycle diagnostics are missing or out of order")
    return {
        "kernel_release": kernel_release,
        "negative_unload_status": int(negative.group(1)),
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
    if type(release) is not str or re.fullmatch(
        r"6\.12\.0-211\.44\.1\.el10_2(?:[.A-Za-z0-9_+-]*)", release
    ) is None:
        raise EvidenceError("capture kernel release differs")

    scope = build["scope"]
    _require_keys(
        scope,
        {"build_commands_sha256", "build_log_sha256", "kernel_targets", "module_targets"},
        "capture build scope",
    )
    _require_sha256_value(scope["build_commands_sha256"], "capture build command digest")
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
    build_dir = _regular_evidence_directory(build_dir, "build evidence directory")
    initial_directory_identity = _stat_identity(build_dir.lstat())
    records = _parse_sums(build_dir)
    contract = _load_json(repo / contract_relative)
    initial_file_identities = _validate_exact_build_artifact_files(
        build_dir,
        records,
        contract["artifact_contract"]["build_evidence_files"],
    )
    phase2 = _validate_phase2_build_evidence(build_dir, records)
    build_scope = _validate_build_scope_artifacts(build_dir, records)
    commit = _read_text(build_dir / "commit.sha", "build commit").strip()
    if commit != candidate_sha:
        raise EvidenceError("build artifact commit differs from runtime candidate")
    kernel_release = _read_text(build_dir / "kernel.release", "kernel release").strip()
    if not re.fullmatch(r"6\.12\.0-211\.44\.1\.el10_2(?:[.A-Za-z0-9_+-]*)", kernel_release):
        raise EvidenceError("built kernel release is outside the selected NVR")
    config_state = _validate_resolved_config(
        build_dir / "resolved.config", contract["runtime"]["required_kernel_config"]
    )

    modules: dict[str, Any] = {}
    for item in contract["modules"]:
        path = build_dir / item["file"]
        depends = _run_field(path, "depends")
        namespaces = _run_field(path, "import_ns")
        if depends != item["depends"]:
            raise EvidenceError("{0} dependency metadata differs".format(item["file"]))
        expected_ns = [] if item["import_namespace"] is None else [item["import_namespace"]]
        if namespaces != expected_ns:
            raise EvidenceError("{0} import namespace differs".format(item["file"]))
        if "provider_symbol_definition" in item:
            defined = _nm(path, ["-g", "--defined-only"])
            symbol = item["provider_symbol_definition"]
            if not re.search(r"\b[A-Z]\s+{0}$".format(re.escape(symbol)), defined, re.MULTILINE):
                raise EvidenceError("provider anchor definition is absent")
        else:
            undefined = _nm(path, ["-u"])
            symbol = item["undefined_provider_symbol"]
            if not re.search(r"\bU\s+{0}$".format(re.escape(symbol)), undefined, re.MULTILINE):
                raise EvidenceError("consumer provider-anchor relocation is absent")
        modules[item["name"]] = {
            "depends": depends,
            "import_namespaces": namespaces,
            "sha256": records[item["file"]],
        }

    runtime = validate_serial(serial_log, kernel_release)
    ancillary: dict[str, str] = {}
    for label, path in (
        ("environment_sha256", environment_log),
        ("qemu_command_sha256", qemu_command),
        ("qemu_version_sha256", qemu_version),
        ("qemu_exit_code_sha256", qemu_exit_code),
    ):
        resolved = _regular_evidence_file(path, label)
        ancillary[label] = _sha256_file(resolved)
    qemu_log = _regular_evidence_file(qemu_log, "QEMU log", nonempty=False)
    ancillary["qemu_log_sha256"] = _sha256_file(qemu_log)

    environment = _read_text(environment_log.resolve(), "runtime environment")
    if (
        "container_image={0}".format(contract["runtime"]["container_image"]) not in environment
        or "runner_arch=x86_64" not in environment
        or "qemu-kvm-core-" not in environment
    ):
        raise EvidenceError("runtime environment identity differs")
    qemu_version_text = _read_text(qemu_version.resolve(), "QEMU version")
    if not re.search(r"(?m)^QEMU emulator version [0-9]+\.", qemu_version_text):
        raise EvidenceError("QEMU version diagnostic differs")
    qemu_command_text = _read_text(qemu_command.resolve(), "QEMU command")
    if len(qemu_command_text.splitlines()) != 1:
        raise EvidenceError("QEMU command diagnostic must contain exactly one argv record")
    for fragment in (
        "/usr/libexec/qemu-kvm",
        "-machine q35",
        "-accel tcg",
        "-cpu max",
        "-smp 2",
        "-m 2048",
        "-kernel ",
        "bzImage",
        "-initrd ",
        "initramfs.cpio.gz",
        "rdinit=/init",
        "-serial ",
        "serial.log",
        "-no-reboot",
    ):
        if fragment not in qemu_command_text:
            raise EvidenceError("QEMU command lacks exact TCG boot boundary: {0}".format(fragment))
    if "/dev/kvm" in qemu_command_text or "-accel kvm" in qemu_command_text:
        raise EvidenceError("QEMU command crosses the TCG-only boundary")
    if _read_text(qemu_exit_code.resolve(), "QEMU exit code").strip() != "0":
        raise EvidenceError("QEMU did not exit cleanly after guest poweroff")

    initramfs = _regular_evidence_file(initramfs, "deterministic initramfs")
    initramfs_sha256 = _regular_evidence_file(initramfs_sha256, "initramfs digest")
    digest_record = _read_text(initramfs_sha256, "initramfs digest").strip()
    digest_match = re.fullmatch(r"([0-9a-f]{64})  initramfs\.cpio\.gz", digest_record)
    if digest_match is None or digest_match.group(1) != _sha256_file(initramfs):
        raise EvidenceError("initramfs digest record differs")
    ancillary["initramfs_sha256"] = digest_match.group(1)
    ancillary["initramfs_sha256_record"] = _sha256_file(initramfs_sha256)
    runtime.update(ancillary)
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
        "build": {
            "artifact_manifest_sha256": _sha256_file(build_dir / "SHA256SUMS"),
            "bzimage_sha256": records["bzImage"],
            "config_sha256": records["resolved.config"],
            "config_runtime_requirements": config_state,
            "kbuild_link_closure": phase2["kbuild_link_closure"],
            "kconfig_solver": phase2["kconfig_solver"],
            "kernel_release": kernel_release,
            "modules": modules,
            "scope": build_scope,
        },
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
    final_directory = _regular_evidence_directory(
        build_dir, "build evidence directory"
    )
    final_records = _parse_sums(final_directory)
    final_file_identities = _validate_exact_build_artifact_files(
        build_dir,
        final_records,
        contract["artifact_contract"]["build_evidence_files"],
    )
    if (
        _stat_identity(final_directory.lstat()) != initial_directory_identity
        or final_file_identities != initial_file_identities
        or final_records != records
    ):
        raise EvidenceError("build artifact changed before capture completed")
    value["capture_sha256"] = _sha256_bytes(_canonical_bytes(value))
    validate_capture(value)
    return value


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=ROOT)
    parser.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT)
    actions = parser.add_mutually_exclusive_group(required=True)
    actions.add_argument("--check-contract", action="store_true")
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
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(sys.argv[1:] if argv is None else argv)
    repo = args.repo.resolve()
    try:
        if args.check_contract:
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
