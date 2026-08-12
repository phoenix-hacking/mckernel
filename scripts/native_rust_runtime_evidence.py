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
import shutil
import subprocess
import sys
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONTRACT = Path("host-kernel/contracts/native-rust-runtime-evidence-v1.json")
CONTRACT_ID = "mckernel-native-rust-runtime-evidence-v1"
PROTOCOL = "MCKERNEL_NATIVE_RUST_RUNTIME_V1"
HEX40 = re.compile(r"^[0-9a-f]{40}$")
HEX64 = re.compile(r"^[0-9a-f]{64}$")


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


def _regular_evidence_file(path: Path, label: str, nonempty: bool = True) -> Path:
    if path.is_symlink() or not path.is_file():
        raise EvidenceError("{0} must be a regular non-symlink file".format(label))
    resolved = path.resolve()
    if nonempty and not resolved.stat().st_size:
        raise EvidenceError("{0} is empty".format(label))
    return resolved


def validate_contract(repo: Path, contract_relative: Path = DEFAULT_CONTRACT) -> dict[str, Any]:
    repo = repo.resolve()
    contract_path = _repo_file(repo, contract_relative.as_posix(), "runtime contract")
    contract = _load_json(contract_path)
    _require_keys(
        contract,
        {
            "artifact_contract",
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
        "required_kernel_config": {
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
        },
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
        "SHA256SUMS",
        "bzImage",
        "commit.sha",
        "ihk-smp-x86_64.ko",
        "ihk-smp-x86_64.ko.modinfo",
        "ihk-smp-x86_64.ko.nm",
        "ihk.ko",
        "ihk.ko.modinfo",
        "ihk.ko.nm",
        "kernel.release",
        "mcctrl.ko",
        "mcctrl.ko.modinfo",
        "mcctrl.ko.nm",
        "resolved.config",
        "stage-lock.json",
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
        "poweroff": "scripts/native-rust-runtime-poweroff.S",
        "runtime_workflow": ".github/workflows/native-rust-host-modules-exact-runtime.yml",
        "source_lock": "host-kernel/rocky/source-lock.json",
    }
    if inputs != expected_inputs:
        raise EvidenceError("runtime repository input paths differ")
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
    for symbol in (
        "CONFIG_MCKERNEL_IHK_RUST=m",
        "CONFIG_MCKERNEL_IHK_SMP_X86_64_RUST=m",
        "CONFIG_MCKERNEL_MCCTRL_RUST=m",
    ):
        if config.count(symbol) != 1:
            raise EvidenceError("runtime config lacks exact modular selection: {0}".format(symbol))
    for fragment in ("workflow_call:", "-j2 bzImage modules", '"$EVIDENCE_DIR/bzImage"'):
        if fragment not in build_workflow:
            raise EvidenceError("exact build workflow is not a reusable boot artifact producer")

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


def _validate_resolved_config(path: Path, requirements: dict[str, list[str]]) -> dict[str, Any]:
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
    return {
        "disabled": list(requirements["disabled"]),
        "enabled": list(requirements["enabled"]),
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
    if value["schema_version"] != 1 or value["contract_id"] != CONTRACT_ID:
        raise EvidenceError("capture identity differs")
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
    build_dir = build_dir.resolve()
    records = _parse_sums(build_dir)
    contract = _load_json(repo / contract_relative)
    required = set(contract["artifact_contract"]["build_evidence_files"])
    available = set(records) | {"SHA256SUMS"}
    if not required.issubset(available):
        raise EvidenceError(
            "build artifact lacks required files: {0}".format(sorted(required - available))
        )
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
            "kernel_release": kernel_release,
            "modules": modules,
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
