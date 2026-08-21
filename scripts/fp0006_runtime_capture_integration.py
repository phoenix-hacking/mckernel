#!/usr/bin/env python3
"""Build and review noncrediting FP-0006 lane-capture envelopes.

The GitHub Actions artifact ZIP is transport only.  The evidence object is a
deterministic USTAR envelope whose exact member bytes and metadata are checked
before upload and again on review.  A validated lane or pair does not establish
native-module runtime reachability, current-head legacy provenance, a gate
result, or tracker credit; those decisions still require the missing result
authority named by the contract.
"""

from __future__ import print_function

import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import tempfile
import types
from typing import Any, Dict, List, Optional, Sequence, Tuple
import zipfile


ROOT = Path(__file__).resolve().parent.parent
CONTRACT_PATH = Path(
    "host-kernel/contracts/fp0006-runtime-capture-integration-v1.json"
)
BASE_CHECKER_PATH = Path("scripts/fp0006_ihk_device_negative_dispatch.py")
ENVELOPE_NAME = "fp0006-runtime-capture-v1.tar"
EXPECTED_CONTRACT_SHA256 = "83d36a2b22ea34f43bdea2d276afdb781608d2ee075a85d824b006335b8d304a"
EXPECTED_CONTRACT_SIZE = 8780
EXPECTED_LEGACY_WORKFLOW_SHA256 = "67dd306a2ce36c023dd139d71d3871f32412d43e504cb3bf873bf6e146f9e516"
EXPECTED_NATIVE_WORKFLOW_SHA256 = "e3352df5362e246d09079d82be460d8dc76255b231f9c7fbcac79ae1381a24cf"
EXPECTED_LEGACY_BOOT_ACTIVE_SHA256 = "6a8b2a5a0ae4eb7ed752d5ec18b68edeb2fec5a1ffded5d6359d1685d634bde4"
EXPECTED_LEGACY_FINALIZE_ACTIVE_SHA256 = "8a0529df14c4bd6544a0454e406e888e8e3f67e5dc4491fc80116a8ce872b391"
EXPECTED_NATIVE_CAPTURE_ACTIVE_SHA256 = "bbeeaaf364713206fc439455491adb7cda7b1c9b5fd3f516f76565111c634340"
EXPECTED_ROCKY_PREFLIGHT_BODY_SHA256 = "0d1a606095cbcdf0a85885d8ead440424cb2192bb2a587c06777cffe5071c699"
EXPECTED_ROCKY_CAPTURE_BODY_SHA256 = "1b16c96de56484a8003c5c41b2eb4f62f64ba2ec02ecb5c01b549f7eb1848c7b"
EXPECTED_QEMU_WRAPPER_ACTIVE_SHA256 = "1db4c0dc045cf7a6f5537eefaec4474dec42c832f1bdbb2af618decb8d017954"
EXPECTED_QEMU_RUNNER_ACTIVE_SHA256 = "ba3784281f47607000cc54691af0b1398bba8de7afa3e6f4578e7cf09b1979c8"
HEX40 = re.compile(r"^[0-9a-f]{40}$")
HEX64 = re.compile(r"^[0-9a-f]{64}$")
REPOSITORY_COMPONENT = r"[A-Za-z0-9](?:[A-Za-z0-9_.-]*[A-Za-z0-9])?"
REPOSITORY = re.compile(r"^{0}/{0}$".format(REPOSITORY_COMPONENT))
POSITIVE_DECIMAL = re.compile(r"^[1-9][0-9]*$")
GITHUB_REF = re.compile(r"^refs/[A-Za-z0-9._/-]{1,240}$")
MAX_INPUT_BYTES = 1048576
MAX_PRODUCER_BINARY_BYTES = 8 * MAX_INPUT_BYTES
TAR_BLOCK = 512
TAR_RECORD = 10240
EMPTY_SHA256 = hashlib.sha256(b"").hexdigest()


class CaptureError(RuntimeError):
    """Raised when an integration contract or capture fails closed."""


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical_json(value: Any) -> bytes:
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        + "\n"
    ).encode("ascii")


def _pretty_json(value: Any) -> bytes:
    return (
        json.dumps(value, sort_keys=True, indent=2, ensure_ascii=True) + "\n"
    ).encode("ascii")


def _object_without_duplicates(pairs: List[Tuple[str, Any]]) -> Dict[str, Any]:
    value = {}  # type: Dict[str, Any]
    for key, item in pairs:
        if key in value:
            raise CaptureError("duplicate JSON key: {0}".format(key))
        value[key] = item
    return value


def _load_json(data: bytes, label: str) -> Any:
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as error:
        raise CaptureError("{0} is not UTF-8: {1}".format(label, error))
    try:
        return json.loads(
            text,
            object_pairs_hook=_object_without_duplicates,
            parse_constant=lambda value: (_ for _ in ()).throw(
                CaptureError("non-finite JSON value in {0}: {1}".format(label, value))
            ),
        )
    except CaptureError:
        raise
    except (TypeError, ValueError) as error:
        raise CaptureError("{0} is not valid JSON: {1}".format(label, error))


def _same_json(actual: Any, expected: Any) -> bool:
    if type(actual) is not type(expected):
        return False
    if type(expected) is dict:
        if len(actual) != len(expected):
            return False
        return all(
            type(key) is str
            and key in actual
            and _same_json(actual[key], expected_value)
            for key, expected_value in expected.items()
        )
    if type(expected) is list:
        return len(actual) == len(expected) and all(
            _same_json(left, right) for left, right in zip(actual, expected)
        )
    return bool(actual == expected)


def _require(actual: Any, expected: Any, label: str) -> None:
    if not _same_json(actual, expected):
        raise CaptureError("{0} differs".format(label))


def _require_keys(value: Any, keys: Sequence[str], label: str) -> None:
    if type(value) is not dict or sorted(value) != sorted(keys):
        raise CaptureError("{0} keys differ".format(label))


def _require_int(value: Any, label: str) -> int:
    if type(value) is not int:
        raise CaptureError("{0} is not an exact integer".format(label))
    return value


def _read_regular(path: Path, label: str, maximum: int = MAX_INPUT_BYTES) -> bytes:
    path = Path(path)
    try:
        before = os.lstat(str(path))
    except OSError as error:
        raise CaptureError("cannot inspect {0}: {1}".format(label, error))
    if stat.S_ISLNK(before.st_mode) or not stat.S_ISREG(before.st_mode):
        raise CaptureError("{0} must be a regular non-symlink file".format(label))
    if before.st_size < 0:
        raise CaptureError(
            "{0} size {1} is invalid; maximum is {2}".format(
                label, before.st_size, maximum
            )
        )
    if before.st_size > maximum:
        raise CaptureError(
            "{0} size {1} exceeds maximum {2}".format(
                label, before.st_size, maximum
            )
        )
    try:
        descriptor = os.open(str(path), os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0))
    except OSError as error:
        raise CaptureError("cannot open {0}: {1}".format(label, error))
    opened_identity = None  # type: Optional[Tuple[int, ...]]
    result = b""
    try:
        opened = os.fstat(descriptor)
        if (before.st_dev, before.st_ino) != (opened.st_dev, opened.st_ino):
            raise CaptureError("{0} changed while opening".format(label))
        if not stat.S_ISREG(opened.st_mode) or opened.st_nlink < 1:
            raise CaptureError("{0} opened as a non-regular or unlinked file".format(label))
        if opened.st_size < 0:
            raise CaptureError(
                "{0} opened size {1} is invalid; maximum is {2}".format(
                    label, opened.st_size, maximum
                )
            )
        if opened.st_size > maximum:
            raise CaptureError(
                "{0} opened size {1} exceeds maximum {2}".format(
                    label, opened.st_size, maximum
                )
            )
        chunks = []  # type: List[bytes]
        remaining = opened.st_size
        while remaining:
            chunk = os.read(descriptor, min(remaining, 65536))
            if not chunk:
                raise CaptureError("{0} ended before its retained size".format(label))
            chunks.append(chunk)
            remaining -= len(chunk)
        if os.read(descriptor, 1):
            raise CaptureError("{0} grew beyond its retained size".format(label))
        after = os.fstat(descriptor)
        opened_identity = (
            opened.st_dev, opened.st_ino, opened.st_mode, opened.st_nlink,
            opened.st_uid, opened.st_gid, opened.st_size, opened.st_mtime_ns,
            opened.st_ctime_ns,
        )
        after_identity = (
            after.st_dev, after.st_ino, after.st_mode, after.st_nlink,
            after.st_uid, after.st_gid, after.st_size, after.st_mtime_ns,
            after.st_ctime_ns,
        )
        if opened_identity != after_identity:
            raise CaptureError("{0} changed while reading".format(label))
        result = b"".join(chunks)
    finally:
        os.close(descriptor)
    try:
        replay = os.lstat(str(path))
    except OSError as error:
        raise CaptureError("cannot replay {0} after close: {1}".format(label, error))
    replay_identity = (
        replay.st_dev, replay.st_ino, replay.st_mode, replay.st_nlink,
        replay.st_uid, replay.st_gid, replay.st_size, replay.st_mtime_ns,
        replay.st_ctime_ns,
    )
    if opened_identity != replay_identity:
        raise CaptureError("{0} changed after close".format(label))
    return result


def _read_producer_binary(path: Path, label: str) -> bytes:
    binary = _read_regular(path, label, MAX_PRODUCER_BINARY_BYTES)
    if not binary:
        raise CaptureError("{0} is empty".format(label))
    return binary


def _safe_repo(repo: Path) -> Path:
    repo = Path(repo)
    try:
        metadata = os.lstat(str(repo))
    except OSError as error:
        raise CaptureError("cannot inspect repository root: {0}".format(error))
    if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISDIR(metadata.st_mode):
        raise CaptureError("repository root must be a non-symlink directory")
    return repo


def _git_head(repo: Path) -> str:
    environment = {
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_NO_REPLACE_OBJECTS": "1",
        "GIT_OPTIONAL_LOCKS": "0",
        "GIT_PAGER": "cat",
        "GIT_TERMINAL_PROMPT": "0",
        "HOME": os.devnull,
        "LANG": "C",
        "LC_ALL": "C",
        "PATH": "/usr/bin:/bin",
    }
    completed = subprocess.run(
        [
            "/usr/bin/git", "-c", "safe.directory=" + str(repo.resolve()),
            "-C", str(repo), "rev-parse", "--verify", "HEAD^{commit}",
        ],
        check=False,
        env=environment,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if completed.returncode != 0:
        raise CaptureError("cannot resolve repository HEAD")
    try:
        head = completed.stdout.decode("ascii").strip()
    except UnicodeDecodeError:
        raise CaptureError("repository HEAD is not ASCII")
    if HEX40.fullmatch(head) is None:
        raise CaptureError("repository HEAD is not exact lowercase 40-hex")
    return head


def _load_base_checker(repo: Path) -> Any:
    checker = repo / BASE_CHECKER_PATH
    source = _read_regular(checker, "frozen FP-0006 witness checker")
    module = types.ModuleType("fp0006_frozen_witness_checker")
    module.__file__ = str(checker)
    module.__package__ = ""
    try:
        exec(compile(source, str(checker), "exec", dont_inherit=True), module.__dict__)
    except Exception as error:
        raise CaptureError("cannot initialize frozen witness checker: {0}".format(error))
    return module


def _extract_job(text: str, name: str, label: str) -> str:
    header = "  {0}:\n".format(name)
    if text.count(header) != 1:
        raise CaptureError("{0} must contain exactly one {1} job".format(label, name))
    start = text.index(header)
    following = re.search(r"(?m)^  [A-Za-z0-9_-]+:\n", text[start + len(header):])
    end = len(text) if following is None else start + len(header) + following.start()
    return text[start:end]


def _extract_steps(job: str, label: str) -> Tuple[List[str], Dict[str, str]]:
    matches = list(re.finditer(r"(?m)^      - name: ([^\n]+)\n", job))
    if not matches:
        raise CaptureError("{0} has no named steps".format(label))
    order = []  # type: List[str]
    steps = {}  # type: Dict[str, str]
    for index, match in enumerate(matches):
        name = match.group(1)
        if name in steps:
            raise CaptureError("duplicate step in {0}: {1}".format(label, name))
        end = matches[index + 1].start() if index + 1 < len(matches) else len(job)
        order.append(name)
        steps[name] = job[match.end():end]
    return order, steps


def _active_lines(step: str) -> Tuple[str, ...]:
    return tuple(
        line.strip()
        for line in step.splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    )


def _reject_tolerance(text: str, label: str, allow_if: bool = False) -> None:
    key = r"(?:continue-on-error|\"continue-on-error\"|'continue-on-error')"
    if re.search(r"(?m)^\s*" + key + r"\s*:", text):
        raise CaptureError("{0} tolerates failure".format(label))
    strategy = r"(?:strategy|\"strategy\"|'strategy')"
    if re.search(r"(?m)^\s*" + strategy + r"\s*:", text):
        raise CaptureError("{0} has an unapproved strategy".format(label))
    active = "\n".join(
        line for line in text.splitlines() if not line.lstrip().startswith("#")
    )
    for token in ("|| true", "set +e", "continue-on-error"):
        if token in active:
            raise CaptureError("{0} masks a failure with {1}".format(label, token))
    condition = r"(?:if|\"if\"|'if')"
    if not allow_if and re.search(r"(?m)^\s*" + condition + r"\s*:", text):
        raise CaptureError("{0} is conditionally skipped".format(label))


def _require_job_keys(job: str, expected_if: int, label: str) -> None:
    for key, expected in (
        ("if", expected_if), ("runs-on", 1), ("steps", 1),
        ("continue-on-error", 0), ("strategy", 0),
    ):
        pattern = r"(?m)^    (?:{0}|\"{0}\"|'{0}')\s*:".format(
            re.escape(key)
        )
        if len(re.findall(pattern, job)) != expected:
            raise CaptureError(
                "{0} has an unexpected or duplicate job key: {1}".format(label, key)
            )


def _active_digest(step: str) -> str:
    return _sha256(("\n".join(_active_lines(step)) + "\n").encode("utf-8"))


def _validate_legacy_workflow(text: str, policy: Dict[str, Any]) -> None:
    if _sha256(text.encode("utf-8")) != EXPECTED_LEGACY_WORKFLOW_SHA256:
        raise CaptureError("legacy workflow exact active scope differs")
    job_name = policy["legacy_job"]
    job = _extract_job(text, job_name, "legacy workflow")
    _require_job_keys(job, 1, "legacy capture job")
    trusted = (
        "    if: >-\n"
        "      ${{ github.event_name == 'pull_request' &&\n"
        "          github.event.pull_request.head.repo.full_name == github.repository }}\n"
    )
    if job.count(trusted) != 1 or job.count("    runs-on: ubuntu-24.04\n") != 1:
        raise CaptureError("legacy capture job trust boundary differs")
    preamble = job[:job.index("    steps:\n") + len("    steps:\n")]
    if (
        preamble.count("    if:") != 1
        or preamble.count("    runs-on: ubuntu-24.04\n") != 1
        or preamble.count("    steps:\n") != 1
        or re.search(r"(?m)^    (?:\"if\"|'if'|continue-on-error|strategy):", preamble)
    ):
        raise CaptureError("legacy capture job has an extra job-level condition")
    order, steps = _extract_steps(job, "legacy hosted job")
    boot_name = policy["legacy_boot_step"]
    preflight_name = policy["legacy_preflight_step"]
    finalize_name = policy["legacy_finalize_step"]
    upload_name = policy["legacy_upload_step"]
    containing_upload_name = policy["legacy_containing_upload_step"]
    for name in (
        preflight_name, boot_name, finalize_name, upload_name,
        containing_upload_name,
    ):
        if name not in steps:
            raise CaptureError("legacy workflow lacks required step: {0}".format(name))
    if not (
        order.index(preflight_name) < order.index(boot_name)
        < order.index(finalize_name) < order.index(upload_name)
        < order.index(containing_upload_name)
    ):
        raise CaptureError("legacy capture steps are reordered")
    _reject_tolerance(steps[preflight_name], "legacy authority preflight step")
    _reject_tolerance(steps[boot_name], "legacy boot producer step")
    _reject_tolerance(steps[finalize_name], "legacy clean-host finalizer step")
    preflight_active = _active_lines(steps[preflight_name])
    if preflight_active != (
        "shell: bash", "run: |", "set -euo pipefail",
        'test "$(git rev-parse HEAD)" = "${{ github.event.pull_request.head.sha }}"',
        "python3 scripts/fp0006_runtime_capture_integration.py \\",
        'check-contract --repo "$GITHUB_WORKSPACE"',
    ):
        raise CaptureError("legacy authority preflight commands differ")
    boot_active = _active_lines(steps[boot_name])
    expected_arguments = (
        "--boot-smoke \\",
        "--fp0006-negative-dispatch-capture \\",
        '--fp0006-capture-head "${{ github.event.pull_request.head.sha }}" \\',
        '--fp0006-capture-repository "$GITHUB_REPOSITORY" \\',
        '--fp0006-capture-run-id "$GITHUB_RUN_ID" \\',
        '--fp0006-capture-run-attempt "$GITHUB_RUN_ATTEMPT" \\',
        '--fp0006-capture-event-name "$GITHUB_EVENT_NAME" \\',
        '--fp0006-capture-ref "$GITHUB_REF" \\',
        '--fp0006-capture-github-sha "$GITHUB_SHA" \\',
        '--fp0006-capture-workflow-sha "$GITHUB_WORKFLOW_SHA" \\',
        '--fp0006-capture-base-sha "${{ github.event.pull_request.base.sha }}" \\',
        "--boot-timeout 120 \\",
    )
    positions = []  # type: List[int]
    for line in expected_arguments:
        if boot_active.count(line) != 1:
            raise CaptureError("legacy boot step command boundary differs")
        positions.append(boot_active.index(line))
    if positions != sorted(positions):
        raise CaptureError("legacy boot capture arguments are reordered")
    if _active_digest(steps[boot_name]) != EXPECTED_LEGACY_BOOT_ACTIVE_SHA256:
        raise CaptureError("legacy boot producer active commands differ")
    legacy_launch = "scripts/qemu-rocky-rust-validation.sh \\"
    if (
        boot_active.count(legacy_launch) != 1
        or boot_active.index(legacy_launch) != 4
        or boot_active[-1] != '2>&1 | tee "$HOSTED_BOOT_DIR/run.log"'
    ):
        raise CaptureError("legacy boot launch scope differs")
    boot_depth = 0
    for line in boot_active:
        if (
            re.match(r"^trap(?:\s|$)", line) is not None
            or re.match(r"^(?:exit|return)(?:\s|$)", line) is not None
            or re.match(r"^(?:for|while|until|select|case)(?:\s|$)", line) is not None
            or re.match(r"^[A-Za-z_][A-Za-z0-9_]*\(\)\s*\{$", line) is not None
        ):
            raise CaptureError("legacy boot launch has an overriding control path")
        if re.match(r"^if(?:\s|$)", line) is not None:
            boot_depth += 1
        elif line == "fi":
            boot_depth -= 1
            if boot_depth < 0:
                raise CaptureError("legacy boot launch guards are unbalanced")
        elif line == legacy_launch and boot_depth != 0:
            raise CaptureError("legacy boot launch is conditionally guarded")
    if boot_depth != 0:
        raise CaptureError("legacy boot launch guards are unbalanced")
    if text.count("--fp0006-negative-dispatch-capture") != 1:
        raise CaptureError("legacy capture opt-in escapes its hosted step")

    finalize_active = _active_lines(steps[finalize_name])
    finalize_sequence = (
        "shell: bash", "run: |", "set -euo pipefail",
        'observation="$HOSTED_BOOT_DIR/qemu/guest-evidence/fp0006-legacy-observation"',
        'output="$HOSTED_BOOT_DIR/qemu/guest-evidence/fp0006-legacy-live-ioctl"',
        "python3 scripts/fp0006_runtime_capture_integration.py \\",
        "finalize-legacy-observation \\",
        '--repo "$GITHUB_WORKSPACE" \\',
        '--observation-dir "$observation" \\',
        '--output-dir "$output" \\',
        '--expected-head "${{ github.event.pull_request.head.sha }}" \\',
        '--expected-repository "$GITHUB_REPOSITORY" \\',
        '--expected-run-id "$GITHUB_RUN_ID" \\',
        '--expected-run-attempt "$GITHUB_RUN_ATTEMPT" \\',
        '--expected-event-name "$GITHUB_EVENT_NAME" \\',
        '--expected-ref "$GITHUB_REF" \\',
        '--expected-github-sha "$GITHUB_SHA" \\',
        '--expected-workflow-sha "$GITHUB_WORKFLOW_SHA" \\',
        '--expected-base-sha "${{ github.event.pull_request.base.sha }}"',
    )
    if finalize_active != finalize_sequence:
        raise CaptureError("legacy clean-host finalizer active scope differs")
    if _active_digest(steps[finalize_name]) != EXPECTED_LEGACY_FINALIZE_ACTIVE_SHA256:
        raise CaptureError("legacy clean-host finalizer active commands differ")

    expected_upload = (
        "        if: ${{ always() }}\n"
        "        uses: actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02 # v4.6.2\n"
        "        with:\n"
        "          name: fp0006-legacy-live-ioctl-${{ github.run_id }}-${{ github.run_attempt }}\n"
        "          path: ${{ runner.temp }}/mckernel-hosted-boot-${{ github.run_id }}-${{ github.run_attempt }}/qemu/guest-evidence/fp0006-legacy-live-ioctl/fp0006-runtime-capture-v1.tar\n"
        "          if-no-files-found: error\n"
        "          retention-days: 30\n"
        "          compression-level: 0\n"
        "\n"
    )
    if steps[upload_name] != expected_upload:
        raise CaptureError("legacy dedicated upload scope differs")
    expected_containing_upload = (
        "        if: ${{ always() }}\n"
        "        uses: actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02 # v4.6.2\n"
        "        with:\n"
        "          name: hosted-rocky-boot-${{ github.run_id }}-${{ github.run_attempt }}\n"
        "          path: |\n"
        "            ${{ runner.temp }}/mckernel-hosted-boot-${{ github.run_id }}-${{ github.run_attempt }}/CHECKSUM\n"
        "            ${{ runner.temp }}/mckernel-hosted-boot-${{ github.run_id }}-${{ github.run_attempt }}/host-environment.txt\n"
        "            ${{ runner.temp }}/mckernel-hosted-boot-${{ github.run_id }}-${{ github.run_attempt }}/post-validation.txt\n"
        "            ${{ runner.temp }}/mckernel-hosted-boot-${{ github.run_id }}-${{ github.run_attempt }}/run.log\n"
        "            ${{ runner.temp }}/mckernel-hosted-boot-${{ github.run_id }}-${{ github.run_attempt }}/qemu/serial.log\n"
        "            ${{ runner.temp }}/mckernel-hosted-boot-${{ github.run_id }}-${{ github.run_attempt }}/qemu/debugcon.log\n"
        "            ${{ runner.temp }}/mckernel-hosted-boot-${{ github.run_id }}-${{ github.run_attempt }}/qemu/qemu-started.pid\n"
        "            ${{ runner.temp }}/mckernel-hosted-boot-${{ github.run_id }}-${{ github.run_attempt }}/qemu/qemu-startup.log\n"
        "            ${{ runner.temp }}/mckernel-hosted-boot-${{ github.run_id }}-${{ github.run_attempt }}/qemu/qemu-cpu-model.txt\n"
        "            ${{ runner.temp }}/mckernel-hosted-boot-${{ github.run_id }}-${{ github.run_attempt }}/qemu/qmp-status.jsonl\n"
        "            ${{ runner.temp }}/mckernel-hosted-boot-${{ github.run_id }}-${{ github.run_attempt }}/qemu/guest-command.log\n"
        "            ${{ runner.temp }}/mckernel-hosted-boot-${{ github.run_id }}-${{ github.run_attempt }}/qemu/guest-cleanup.log\n"
        "            ${{ runner.temp }}/mckernel-hosted-boot-${{ github.run_id }}-${{ github.run_attempt }}/qemu/guest-evidence.tar\n"
        "            ${{ runner.temp }}/mckernel-hosted-boot-${{ github.run_id }}-${{ github.run_attempt }}/qemu/guest-evidence.tar.sha256\n"
        "            ${{ runner.temp }}/mckernel-hosted-boot-${{ github.run_id }}-${{ github.run_attempt }}/qemu/guest-evidence/\n"
        "            VALIDATION_PROGRESS.MD\n"
        "          if-no-files-found: warn\n"
        "          retention-days: 90\n"
        "\n"
    )
    if steps[containing_upload_name] != expected_containing_upload:
        raise CaptureError("legacy containing diagnostic upload scope differs")
    protected = _extract_job(text, "boot-smoke", "legacy workflow")
    for token in (
        "fp0006-negative-dispatch-capture",
        "fp0006-runtime-capture-v1.tar",
        "fp0006_runtime_capture_integration.py",
    ):
        if token in protected:
            raise CaptureError("protected boot lane contains FP-0006 capture opt-in")


def _validate_native_workflow(text: str, policy: Dict[str, Any]) -> None:
    if _sha256(text.encode("utf-8")) != EXPECTED_NATIVE_WORKFLOW_SHA256:
        raise CaptureError("native workflow exact active scope differs")
    job_name = policy["native_job"]
    job = _extract_job(text, job_name, "native workflow")
    _require_job_keys(job, 1, "native capture job")
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
        "      image: rockylinux/rockylinux:10.2@sha256:e372170ca8630f0f03e9b70fdd0bf4a3ce3426b0de7cdba615f06337389de176\n"
        "    defaults:\n"
        "      run:\n"
        "        shell: bash\n"
        "\n"
        "    steps:\n"
    )
    first_header = "      - name: {0}\n".format(policy["native_bootstrap_step"])
    if not job.startswith(expected_preamble + first_header):
        raise CaptureError("native capture job scope differs")
    preamble = job[:len(expected_preamble)]
    trusted = (
        "    if: >-\n"
        "      ${{ github.event_name != 'pull_request' ||\n"
        "          github.event.pull_request.head.repo.full_name == github.repository }}\n"
    )
    if job.count(trusted) != 1:
        raise CaptureError("native capture job trust boundary differs")
    order, steps = _extract_steps(job, "native capture job")
    expected_order = [
        policy["native_bootstrap_step"],
        policy["native_checkout_step"],
        policy["native_capture_step"],
        policy["native_upload_step"],
        policy["native_failure_upload_step"],
    ]
    if order != expected_order:
        raise CaptureError("native capture steps are missing, extra, or reordered")
    for name in expected_order[:3]:
        _reject_tolerance(steps[name], "native capture step " + name)
    checkout = steps[policy["native_checkout_step"]]
    expected_checkout = (
        "        uses: actions/checkout@11d5960a326750d5838078e36cf38b85af677262 # v4\n"
        "        with:\n"
        "          ref: ${{ env.EXPECTED_HEAD_SHA }}\n"
        "          fetch-depth: 1\n"
        "          submodules: recursive\n"
        "          persist-credentials: false\n"
        "\n"
    )
    if checkout != expected_checkout:
        raise CaptureError("native capture checkout scope differs")
    bootstrap_active = _active_lines(steps[policy["native_bootstrap_step"]])
    expected_bootstrap = (
        "run: |",
        "set -euo pipefail",
        'fp0006_diagnostics="$RUNNER_TEMP/fp0006-native-rust-first-failure"',
        'mkdir -m 700 "$fp0006_diagnostics"',
        "printf '%s\\n' bootstrap-started capture-envelope-required-missing credit-forbidden \\",
        '> "$fp0006_diagnostics/workflow-state"',
        'test "$(uname -m)" = x86_64',
        ". /etc/os-release",
        'test "$ID" = rocky',
        'test "$VERSION_ID" = 10.2',
        "dnf -y --allowerasing --setopt=install_weak_deps=False install \\",
        "coreutils",
        "dnf -y --setopt=install_weak_deps=False install \\",
        "gcc git-core python3 rust-1.92.0-1.el10",
        "! /usr/bin/rpm -q coreutils-single",
        'test "$(/usr/bin/rpm -qf --qf \'%{NAME}\\n\' /usr/bin/timeout)" = coreutils',
        'test "$(command -v rustc)" = /usr/bin/rustc',
        'test "$(command -v gcc)" = /usr/bin/gcc',
        'test "$(command -v timeout)" = /usr/bin/timeout',
        'test ! -L /usr/bin/rustc',
        'test ! -L /usr/bin/gcc',
        'test ! -L /usr/bin/timeout',
        'test "$(/usr/bin/rpm -qf --qf \'%{NAME}\\n\' /usr/bin/rustc)" = rust',
        'test "$(/usr/bin/rpm -qf --qf \'%{NAME}\\n\' /usr/bin/gcc)" = gcc',
        'test "$(/usr/bin/rpm -q --qf \'%{NAME}-%{EPOCHNUM}:%{VERSION}-%{RELEASE}.%{ARCH}\\n\' rust)" = rust-0:1.92.0-1.el10.x86_64',
        "test \"$(/usr/bin/rustc --version)\" = 'rustc 1.92.0 (ded5c06cf 2025-12-08) (Red Hat 1.92.0-1.el10)'",
        "/usr/bin/rustc -Vv",
        "/usr/bin/gcc --version",
        "dnf clean all",
        "printf '%s\\n' bootstrap-complete capture-envelope-required-missing credit-forbidden \\",
        '> "$fp0006_diagnostics/workflow-state"',
    )
    if bootstrap_active != expected_bootstrap:
        raise CaptureError("native capture bootstrap commands differ")
    capture_active = _active_lines(steps[policy["native_capture_step"]])
    required = (
        "run: |", "set -euo pipefail",
        '[[ "$EXPECTED_HEAD_SHA" =~ ^[0-9a-f]{40}$ ]]',
        'test "$(git -c safe.directory="$GITHUB_WORKSPACE" rev-parse HEAD)" = "$EXPECTED_HEAD_SHA"',
        "python3 scripts/fp0006_runtime_capture_integration.py check-contract \\",
        "/usr/bin/rustc --edition=2021 -D warnings -C linker=/usr/bin/gcc -C strip=symbols \\",
        'producer_bytes="$(/usr/bin/wc -c < "$producer")"',
        'if test "$producer_bytes" -le 0 || test "$producer_bytes" -gt 8388608; then',
        "printf 'FP-0006 native producer binary size observed=%s maximum=8388608\\n' \\",
        "/usr/bin/timeout --signal=TERM --kill-after=5s 30s \\",
        '"$producer" "$stage" > "$producer_output" 2>&1',
        "python3 scripts/fp0006_runtime_capture_integration.py finalize-lane \\",
        '--producer-log "$producer_log" \\',
        '--producer-binary "$producer" \\',
        '--tool-report "$tool_report" \\',
        '--compiler-output "$compiler_output" \\',
        '--github-event-name "$GITHUB_EVENT_NAME" \\',
        '--github-ref "$GITHUB_REF" \\',
        '--github-sha "$GITHUB_SHA" \\',
        '--github-workflow-sha "$GITHUB_WORKFLOW_SHA" \\',
        '--github-base-sha "$base_sha"',
    )
    positions = []
    for line in required:
        if capture_active.count(line) != 1:
            raise CaptureError("native capture producer boundary differs")
        positions.append(capture_active.index(line))
    if positions != sorted(positions):
        raise CaptureError("native capture producer commands are reordered")
    if _active_digest(steps[policy["native_capture_step"]]) != EXPECTED_NATIVE_CAPTURE_ACTIVE_SHA256:
        raise CaptureError("native capture producer active commands differ")
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
    if capture_active.count(timeout_if) != 2:
        raise CaptureError("native compile/capture environment boundaries differ")
    for line in (timeout_line, producer_line, finalizer_line):
        if capture_active.count(line) != 1:
            raise CaptureError("native capture structural command boundary differs")
    timeout_candidates = [
        index for index, line in enumerate(capture_active)
        if line == timeout_if
        and capture_active[index:index + 4] == (
            timeout_if, timeout_line, producer_line, "then",
        )
    ]
    if len(timeout_candidates) != 1:
        raise CaptureError("native producer timeout condition differs")
    timeout_if_position = timeout_candidates[0]
    timeout_position = capture_active.index(timeout_line)
    finalizer_position = capture_active.index(finalizer_line)
    size_candidates = [
        index for index in range(len(capture_active))
        if capture_active[index:index + len(size_window)] == size_window
    ]
    if len(size_candidates) != 1:
        raise CaptureError("native producer size boundary differs")
    if not size_candidates[0] < timeout_position < finalizer_position:
        raise CaptureError("native producer size check is reordered")
    exits = tuple(
        line for line in capture_active
        if re.match(r"^exit(?:\s|$)", line) is not None
    )
    if exits != ('exit "$compile_rc"', "exit 1", "exit 1"):
        raise CaptureError("native capture has an unapproved exit")
    if any(
        re.match(r"^(?:trap|return)(?:\s|$)", line) is not None
        or re.match(r"^(?:for|while|until|select|case)(?:\s|$)", line) is not None
        or re.match(r"^[A-Za-z_][A-Za-z0-9_]*\(\)\s*\{$", line) is not None
        for line in capture_active
    ):
        raise CaptureError("native capture has an overriding control path")
    depth_before = []  # type: List[int]
    capture_depth = 0
    for line in capture_active:
        depth_before.append(capture_depth)
        if re.match(r"^if(?:\s|$)", line) is not None:
            capture_depth += 1
        elif line == "fi":
            capture_depth -= 1
            if capture_depth < 0:
                raise CaptureError("native capture condition scope is unbalanced")
        elif re.match(r"^elif(?:\s|$)", line) is not None:
            raise CaptureError("native capture has an unapproved conditional branch")
    if capture_depth != 0:
        raise CaptureError("native capture condition scope is unbalanced")
    if (
        depth_before[timeout_if_position] != 0
        or depth_before[timeout_position] != 1
        or depth_before[finalizer_position] != 0
    ):
        raise CaptureError("native capture timeout/finalizer reachability differs")
    expected_upload = (
        "        uses: actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02 # v4.6.2\n"
        "        with:\n"
        "          name: fp0006-native-rust-source-fixture-${{ github.run_id }}-${{ github.run_attempt }}\n"
        "          path: ${{ runner.temp }}/fp0006-native-rust-capture/fp0006-runtime-capture-v1.tar\n"
        "          if-no-files-found: error\n"
        "          retention-days: 30\n"
        "          compression-level: 0\n"
        "\n"
    )
    if steps[policy["native_upload_step"]] != expected_upload:
        raise CaptureError("native dedicated upload scope differs")
    expected_failure_upload = (
        "        if: ${{ failure() }}\n"
        "        uses: actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02 # v4.6.2\n"
        "        with:\n"
        "          name: fp0006-native-rust-first-failure-${{ github.run_id }}-${{ github.run_attempt }}\n"
        "          path: ${{ runner.temp }}/fp0006-native-rust-first-failure/workflow-state\n"
        "          if-no-files-found: error\n"
        "          retention-days: 30\n"
        "          compression-level: 0\n"
        "\n"
    )
    if steps[policy["native_failure_upload_step"]] != expected_failure_upload:
        raise CaptureError("native first-failure upload scope differs")
    if "actions/download-artifact@" in job:
        raise CaptureError("native FP-0006 capture attempts an artifact download")
    job_positions = [
        text.index("  exact-build:\n"),
        text.index("  fp0006-native-rust-capture:\n"),
        text.index("  rk006-full-source-build-capture:\n"),
    ]
    if job_positions != sorted(job_positions):
        raise CaptureError("native workflow job order differs")


def _validate_rocky_script(text: str) -> None:
    required = (
        "preflight_fp0006_legacy_negative_dispatch() {",
        "capture_fp0006_legacy_negative_dispatch() {",
        '"$FP0006_PRODUCER_BINARY" /dev/mcd0 "$stage" \\',
        "/usr/bin/tar --format=ustar --sort=name --owner=0 --group=0 \\",
        "f677c7dde6de2160fd9062fa998cb2c4aa14ba9eafdac8b86b592b78776bcd2e",
        "if ! record_live_boot_evidence; then",
        "\tcapture_fp0006_legacy_negative_dispatch\n",
        "preflight_fp0006_legacy_negative_dispatch\nupdate_submodules\n",
    )
    for value in required:
        if text.count(value) != 1:
            raise CaptureError("Rocky validation script boundary differs: {0}".format(value))
    if text.count("--fp0006-negative-dispatch-capture") != 2:
        raise CaptureError("Rocky validation script capture option boundary differs")
    record_position = text.index("if ! record_live_boot_evidence; then")
    capture_position = text.index("\tcapture_fp0006_legacy_negative_dispatch\n")
    boot_only_position = text.index("\tif [ \"$BOOT_ONLY\" -eq 1 ]; then", capture_position)
    if not record_position < capture_position < boot_only_position:
        raise CaptureError("legacy live capture is outside the bounded live-device window")
    preflight_position = text.index("preflight_fp0006_legacy_negative_dispatch\nupdate_submodules\n")
    overlay_sequence = "update_submodules\nrecord_environment\n"
    if text.count(overlay_sequence) != 1:
        raise CaptureError("legacy overlay initialization boundary differs")
    if preflight_position > text.index(overlay_sequence):
        raise CaptureError("legacy authority preflight occurs after overlay initialization")
    capture_body_start = text.index("capture_fp0006_legacy_negative_dispatch() {")
    capture_body_end = text.index("\n}\n\nboot_smoke()", capture_body_start)
    capture_body = text[capture_body_start:capture_body_end + 2]
    preflight_body_start = text.index("preflight_fp0006_legacy_negative_dispatch() {")
    preflight_body_end = text.index(
        "\n}\n\ncapture_fp0006_legacy_negative_dispatch()", preflight_body_start
    )
    preflight_body = text[preflight_body_start:preflight_body_end + 2]
    if _sha256(preflight_body.encode("utf-8")) != EXPECTED_ROCKY_PREFLIGHT_BODY_SHA256:
        raise CaptureError("Rocky validation script preflight body differs")
    if _sha256(capture_body.encode("utf-8")) != EXPECTED_ROCKY_CAPTURE_BODY_SHA256:
        raise CaptureError("Rocky validation script live capture body differs")
    if "finalize-lane" in capture_body or "verify-lane" in capture_body:
        raise CaptureError("legacy guest attempts post-overlay authority review")

    boot_header = "\nboot_smoke() {\n"
    boot_end_marker = "\n}\n\nrun_hostname_smoke()"
    if text.count(boot_header) != 1 or text.count(boot_end_marker) != 1:
        raise CaptureError("Rocky boot-smoke function scope differs")
    boot_body_start = text.index(boot_header) + len(boot_header)
    boot_body_end = text.index(boot_end_marker, boot_body_start)
    boot_active = _active_lines(text[boot_body_start:boot_body_end])
    boot_check_line = 'say "Checking McKernel boot log"'
    record_line = "if ! record_live_boot_evidence; then"
    capture_line = "capture_fp0006_legacy_negative_dispatch"
    boot_only_line = 'if [ "$BOOT_ONLY" -eq 1 ]; then'
    for line in (boot_check_line, record_line, capture_line, boot_only_line):
        if boot_active.count(line) != 1:
            raise CaptureError("Rocky boot-smoke capture boundary differs")
    boot_check_index = boot_active.index(boot_check_line)
    record_index = boot_active.index(record_line)
    capture_index = boot_active.index(capture_line)
    boot_only_index = boot_active.index(boot_only_line)
    expected_live_window = (
        boot_check_line,
        "if ! wait_for_mckernel_boot; then",
        "dump_boot_failure_state",
        "exit 1",
        "fi",
        record_line,
        "dump_boot_failure_state",
        "exit 1",
        "fi",
        capture_line,
        boot_only_line,
    )
    if tuple(boot_active[boot_check_index:boot_only_index + 1]) != expected_live_window:
        raise CaptureError("Rocky live capture window active commands differ")
    if not boot_check_index < record_index < capture_index < boot_only_index:
        raise CaptureError("Rocky live capture window is reordered")
    boot_prefix = boot_active[:capture_index + 1]
    boot_traps = tuple(
        line for line in boot_prefix if re.match(r"^trap(?:\s|$)", line)
    )
    boot_exits = tuple(
        line for line in boot_prefix if re.match(r"^exit(?:\s|$)", line)
    )
    if boot_traps != ("trap boot_cleanup EXIT",) or boot_exits != ("exit 1",) * 6:
        raise CaptureError("Rocky live capture has an overriding trap or exit")
    if any(
        re.match(r"^return(?:\s|$)", line) is not None
        or re.match(r"^(?:for|while|until|select|case)(?:\s|$)", line) is not None
        or re.match(r"^elif(?:\s|$)", line) is not None
        or re.match(r"^[A-Za-z_][A-Za-z0-9_]*\(\)\s*\{$", line) is not None
        for line in boot_prefix
    ):
        raise CaptureError("Rocky live capture has an unapproved control path")
    boot_depth = 0
    boot_depth_before = []  # type: List[int]
    for line in boot_prefix:
        boot_depth_before.append(boot_depth)
        if re.match(r"^if(?:\s|$)", line) is not None:
            boot_depth += 1
        elif line == "fi":
            boot_depth -= 1
            if boot_depth < 0:
                raise CaptureError("Rocky boot-smoke conditions are unbalanced")
    if boot_depth != 0 or boot_depth_before[capture_index] != 0:
        raise CaptureError("Rocky live capture is conditionally unreachable")

    main_marker = "\n}\n\nneed_cmd sudo\n"
    if text.count(main_marker) != 1:
        raise CaptureError("Rocky top-level execution scope differs")
    main_start = text.index(main_marker) + len("\n}\n\n")
    main_active = _active_lines(text[main_start:])
    preflight_line = "preflight_fp0006_legacy_negative_dispatch"
    update_line = "update_submodules"
    if main_active.count(preflight_line) != 1 or main_active.count(update_line) != 1:
        raise CaptureError("Rocky top-level authority calls differ")
    preflight_index = main_active.index(preflight_line)
    update_index = main_active.index(update_line)
    expected_main_prefix = (
        "need_cmd sudo",
        "need_cmd uname",
        "initialize_runtime_evidence",
        'if [ "$INSTALL_DEPS" -eq 1 ]; then',
        "install_deps",
        "fi",
        "ensure_kernel_headers",
        "ensure_libuedev",
        '[ -f "$HOME/.cargo/env" ] && source "$HOME/.cargo/env"',
        'if [ "$INSTALL_RUST" -eq 1 ]; then',
        "ensure_rust",
        "else",
        "need_cmd rustc",
        'export RUSTUP_TOOLCHAIN="$RUST_TOOLCHAIN"',
        "verify_rustc",
        "fi",
        preflight_line,
        update_line,
    )
    if tuple(main_active[:update_index + 1]) != expected_main_prefix:
        raise CaptureError("Rocky clean preflight active scope differs")
    main_depth = 0
    main_depth_before = []  # type: List[int]
    for line in main_active[:update_index + 1]:
        main_depth_before.append(main_depth)
        if re.match(r"^if(?:\s|$)", line) is not None:
            main_depth += 1
        elif line == "fi":
            main_depth -= 1
            if main_depth < 0:
                raise CaptureError("Rocky top-level preflight conditions are unbalanced")
        elif re.match(r"^elif(?:\s|$)", line) is not None:
            raise CaptureError("Rocky top-level preflight has an unapproved branch")
    if (
        main_depth != 0
        or update_index != preflight_index + 1
        or main_depth_before[preflight_index] != 0
        or main_depth_before[update_index] != 0
    ):
        raise CaptureError("Rocky clean preflight is not top-level before overlay setup")
    if any(
        re.match(r"^(?:trap|exit|return)(?:\s|$)", line) is not None
        or re.match(r"^(?:for|while|until|select|case)(?:\s|$)", line) is not None
        or re.match(r"^[A-Za-z_][A-Za-z0-9_]*\(\)\s*\{$", line) is not None
        for line in main_active[:update_index + 1]
    ):
        raise CaptureError("Rocky clean preflight has an overriding control path")


def _validate_qemu_sources(wrapper: str, runner: str) -> None:
    if _active_digest(wrapper) != EXPECTED_QEMU_WRAPPER_ACTIVE_SHA256:
        raise CaptureError("QEMU validation wrapper active body differs")
    if _active_digest(runner) != EXPECTED_QEMU_RUNNER_ACTIVE_SHA256:
        raise CaptureError("QEMU guest runner active body differs")
    wrapper_active = _active_lines(wrapper)
    wrapper_required = (
        'QEMU_RUNNER="$ROOT_DIR/scripts/qemu-mckernel-guest.sh"',
        "printf 'export MCKERNEL_RUNTIME_EVIDENCE_DIR=/tmp/mckernel-validation-evidence; '",
        "printf 'exec ./scripts/rocky-rust-validation.sh '",
        '--guest-evidence-dir /tmp/mckernel-validation-evidence',
        '--stage-dir "$SOURCE_DIR:/tmp/mckernel-hostshare"',
        'exec "$QEMU_RUNNER" "${qemu_args[@]}"',
    )
    positions = []
    for line in wrapper_required:
        if wrapper_active.count(line) != 1:
            raise CaptureError("QEMU validation wrapper boundary differs")
        positions.append(wrapper_active.index(line))
    if positions != sorted(positions):
        raise CaptureError("QEMU validation wrapper boundaries are reordered")
    launch_marker = "qemu_args=("
    if wrapper_active.count(launch_marker) != 1:
        raise CaptureError("QEMU validation wrapper launch scope differs")
    wrapper_launch = wrapper_active[wrapper_active.index(launch_marker):]
    expected_launch_conditions = (
        'if [ -n "$DISK_SIZE" ]; then',
        'if [ -n "$LOG_DIR" ]; then',
        'if [ "$PAUSE_AT_RESET" -eq 1 ]; then',
        'if [ -n "$GDB_PORT" ]; then',
        'if [ "$KEEP_OVERLAY" -eq 1 ]; then',
        'if [ "$KEEP_RUNNING" -eq 1 ]; then',
        'if [ "$DRY_RUN" -eq 1 ]; then',
    )
    launch_conditions = tuple(
        line for line in wrapper_launch if line.startswith("if ")
    )
    if launch_conditions != expected_launch_conditions:
        raise CaptureError("QEMU validation wrapper launch guards differ")
    if wrapper_launch[-1] != 'exec "$QEMU_RUNNER" "${qemu_args[@]}"':
        raise CaptureError("QEMU validation wrapper launch is not the top-level tail")
    if any(
        re.match(r"^(?:exit|return)(?:\s|$)", line) is not None
        or re.match(r"^trap(?:\s|$)", line) is not None
        or re.match(r"^(?:for|while|until|select|case)(?:\s|$)", line) is not None
        or re.match(r"^[A-Za-z_][A-Za-z0-9_]*\(\)\s*\{$", line) is not None
        for line in wrapper_launch
    ):
        raise CaptureError("QEMU validation wrapper launch has an overriding control path")
    conditional_depth = 0
    for line in wrapper_launch:
        if line in expected_launch_conditions:
            conditional_depth += 1
        elif line == "fi":
            conditional_depth -= 1
            if conditional_depth < 0:
                raise CaptureError("QEMU validation wrapper launch guards are unbalanced")
        elif line == 'exec "$QEMU_RUNNER" "${qemu_args[@]}"' and conditional_depth != 0:
            raise CaptureError("QEMU validation wrapper launch is conditionally guarded")
    if conditional_depth != 0:
        raise CaptureError("QEMU validation wrapper launch guards are unbalanced")
    runner_active = _active_lines(runner)
    runner_required = (
        'OVERLAY="$LOG_DIR/guest-overlay.qcow2"',
        'GUEST_EVIDENCE_ARCHIVE="$LOG_DIR/guest-evidence.tar"',
        "if ! tar --no-same-owner --no-same-permissions \\",
        '-C "$GUEST_EVIDENCE_HOST_DIR" -xf "$GUEST_EVIDENCE_ARCHIVE"',
        "cleanup() {",
        'rm -f "$OVERLAY"',
        "trap cleanup EXIT",
        'qemu-img create -f qcow2 -F "$BASE_FORMAT" -b "$IMAGE" "$OVERLAY" >/dev/null',
    )
    positions = []
    for line in runner_required:
        if runner_active.count(line) != 1:
            raise CaptureError("QEMU guest runner boundary differs: {0}".format(line))
        positions.append(runner_active.index(line))
    if positions != sorted(positions):
        raise CaptureError("QEMU guest runner boundaries are reordered")
    trap_lines = tuple(
        line for line in runner_active if re.match(r"^trap(?:\s|$)", line)
    )
    if trap_lines != ("trap cleanup EXIT",):
        raise CaptureError("QEMU guest runner cleanup trap is overridden")
    cleanup_start = runner_active.index("cleanup() {")
    cleanup_trap = runner_active.index("trap cleanup EXIT")
    create_line = (
        'qemu-img create -f qcow2 -F "$BASE_FORMAT" -b "$IMAGE" '
        '"$OVERLAY" >/dev/null'
    )
    create_position = runner_active.index(create_line)
    if not cleanup_start < cleanup_trap < create_position:
        raise CaptureError("QEMU guest runner cleanup/create scope is reordered")
    cleanup_scope = runner_active[cleanup_start:cleanup_trap]
    expected_cleanup_tail = (
        'if [ "$KEEP_RUNNING" -eq 0 ] && [ "$KEEP_OVERLAY" -eq 0 ]; then',
        'rm -f "$OVERLAY"',
        "fi",
        "}",
    )
    if tuple(cleanup_scope[-len(expected_cleanup_tail):]) != expected_cleanup_tail:
        raise CaptureError("QEMU guest runner overlay removal scope differs")
    if any(
        re.match(r"^(?:exit|return)(?:\s|$)", line) is not None
        or re.match(r"^trap(?:\s|$)", line) is not None
        for line in cleanup_scope
    ):
        raise CaptureError("QEMU guest runner cleanup has an overriding control path")
    expected_create_prefix = (
        "trap cleanup EXIT",
        'say "Preparing disposable guest overlay"',
        create_line,
    )
    if tuple(runner_active[cleanup_trap:create_position + 1]) != expected_create_prefix:
        raise CaptureError("QEMU guest runner overlay creation is not top-level reachable")


def _load_contract(repo: Path) -> Tuple[Dict[str, Any], bytes]:
    repo = _safe_repo(repo)
    contract_file = repo / CONTRACT_PATH
    data = _read_regular(contract_file, "FP-0006 capture integration contract")
    if len(data) != EXPECTED_CONTRACT_SIZE or _sha256(data) != EXPECTED_CONTRACT_SHA256:
        raise CaptureError("FP-0006 capture integration contract identity differs")
    contract = _load_json(data, "FP-0006 capture integration contract")
    if data != _pretty_json(contract):
        raise CaptureError("FP-0006 capture integration contract is not canonical pretty JSON")
    _require_keys(
        contract,
        (
            "artifact_policy", "base_witness", "bound_files", "claims",
            "contract_id", "gate", "limitations", "result_authority",
            "schema_version", "surfaces", "vectors", "workflow_policy",
        ),
        "capture integration contract",
    )
    _require(contract["schema_version"], 1, "contract schema")
    _require(
        contract["contract_id"],
        "fp-0006-runtime-capture-integration-v1",
        "contract identity",
    )
    expected_claims = {
            "credit_eligible": False,
            "current_head_legacy_provenance_proven": False,
            "current_head_runtime_reachability_proven": False,
            "exact_legacy_compiler_provenance": False,
            "exact_linker_provenance": False,
            "exact_native_linker_provenance": False,
            "exact_toolchain_proven": False,
            "exact_workflow_run_provenance": False,
        "fp0006_complete": False,
        "full_failure_semantics_covered": False,
        "gate_pass": False,
        "lane_pair_review_complete": False,
        "legacy_runtime_executed": False,
        "native_runtime_executed": False,
        "runtime_reachability_proven": False,
        "tracker_credit": False,
    }
    _require(contract["claims"], expected_claims, "noncrediting claims")
    _require(
        contract["gate"],
        {"gate_id": "FP-0006", "points_awarded": 0, "status": "IN_PROGRESS"},
        "gate boundary",
    )
    _require(
        contract["result_authority"],
        {
            "independent_review_required": True,
            "path": None,
            "status": "required-missing",
        },
        "result authority boundary",
    )
    _require(
        contract["artifact_policy"],
        {
            "canonical_envelope": "deterministic-ustar-v1",
            "dedicated_actions_compression_level": 0,
            "dedicated_actions_retention_days": 30,
            "dedicated_legacy_artifact_name_template": "fp0006-legacy-live-ioctl-${{ github.run_id }}-${{ github.run_attempt }}",
            "dedicated_native_artifact_name_template": "fp0006-native-rust-source-fixture-${{ github.run_id }}-${{ github.run_attempt }}",
            "dedicated_native_first_failure_artifact_name_template": "fp0006-native-rust-first-failure-${{ github.run_id }}-${{ github.run_attempt }}",
            "dedicated_native_first_failure_member": "workflow-state",
            "dedicated_native_first_failure_statuses": [
                "capture-envelope-created-unreviewed",
                "capture-envelope-required-missing",
            ],
            "durable": False,
            "envelope_member_mode": "0444",
            "envelope_members": [
                "authority.json", "compiler.log", "producer-output.log",
                "producer.log", "raw.jsonl", "result.jsonl", "review.json",
                "state-ledger.jsonl", "tool-report.txt", "SHA256SUMS",
            ],
            "envelope_name": ENVELOPE_NAME,
            "hosted_containing_artifact_name_template": "hosted-rocky-boot-${{ github.run_id }}-${{ github.run_attempt }}",
            "hosted_containing_artifact_retention_days": 90,
            "hosted_containing_path": "${{ runner.temp }}/mckernel-hosted-boot-${{ github.run_id }}-${{ github.run_attempt }}/qemu/guest-evidence/",
            "hosted_contains_same_legacy_envelope": True,
            "transport": "actions-zip-is-not-evidence-authority",
        },
        "artifact policy",
    )
    expected_limitations = [
        "The legacy producer executes against the compatibility-overlay live device in a disposable hosted QEMU guest. The overlay digest is an observation and is not current-head legacy provenance.",
        "The native Rust producer is a standalone source fixture and is not a native module runtime or userspace reachability proof.",
        "The Rocky images and native Rust package are pinned, but both legacy and native GCC packages are resolved from mutable repositories and retained only as path, owner, hash, and version observations. Exact legacy compiler, linker, and complete toolchain provenance remain false until observed GCC NEVRAs and repository snapshot locks are committed and independently reviewed.",
        "Workflow event, ref, GitHub SHA, workflow-definition SHA, head, and base identities are retained as observations. Exact workflow-run provenance remains false unless a separate authority proves the executed workflow definition and candidate alignment.",
        "The dedicated fp0006-legacy-live-ioctl-${run_id}-${run_attempt} artifact retains the canonical legacy envelope for 30 days with compression level 0. The pre-existing hosted-rocky-boot-${run_id}-${run-attempt} artifact also contains that same envelope through qemu/guest-evidence/ and retains it for 90 days. Both copies are temporary and non-durable.",
        "A validated lane or pair remains noncrediting until an independent result authority exists and performs its separate review.",
    ]
    _require(contract["limitations"], expected_limitations, "limitations")
    expected_vectors = [
        {
            "argument": 0,
            "expected_normalized_return": -22,
            "expected_state_transition": "none",
            "request": 4294967295,
            "sequence": 0,
            "vector_id": "unknown-device-request-ffffffff-arg0",
        },
        {
            "argument": 63,
            "expected_normalized_return": -22,
            "expected_state_transition": "none",
            "request": 1124609,
            "sequence": 1,
            "vector_id": "destroy-known-empty-minor63",
        },
    ]
    _require(contract["vectors"], expected_vectors, "fixed vectors")

    expected_frozen = {
        "contract": {
            "path": "host-kernel/contracts/fp0006-ihk-device-negative-dispatch-v1.json",
            "sha256": "13baf241704c98b5d087abc85af45201c8f345ed3cdd08ae310febe666e789c8",
            "size": 19668,
        },
        "checker": {
            "path": "scripts/fp0006_ihk_device_negative_dispatch.py",
            "sha256": "9d72d215f2fc618ac05c2f729a57ad865391c105de2e70995b8eb251d81855a7",
            "size": 51559,
        },
        "tests": {
            "path": "scripts/tests/test_fp0006_ihk_device_negative_dispatch.py",
            "sha256": "159a8214431f0a2c7872de2c5ff58195b047da1f8dbbfa3cf265f600ce0b5201",
            "size": 41210,
        },
        "legacy_producer": {
            "path": "scripts/smoke/fp0006-ihk-device-negative-dispatch.c",
            "sha256": "7f500fba27ece9ad52fa52a81d7aa5f57649ad0152e907c17d421e368a279053",
            "size": 7805,
        },
        "native_producer": {
            "path": "scripts/tests/fixtures/ihk_ioctl_fp0006_negative_dispatch.rs",
            "sha256": "905e7cbdfb0655c2ef3fba3425bfa87057f473bb85ef669061d2b3523f2e8209",
            "size": 6177,
        },
    }
    _require(
        contract["base_witness"],
        {
            "contract_id": "fp-0006-ihk-device-negative-dispatch-v1",
            "files": expected_frozen,
        },
        "frozen base witness",
    )
    for binding in expected_frozen.values():
        value = _read_regular(repo / binding["path"], binding["path"])
        if len(value) != binding["size"] or _sha256(value) != binding["sha256"]:
            raise CaptureError("frozen witness identity differs: {0}".format(binding["path"]))

    expected_surfaces = {
        "legacy-live-ioctl": {
            "expected_overlay_host_driver_sha256": "f677c7dde6de2160fd9062fa998cb2c4aa14ba9eafdac8b86b592b78776bcd2e",
            "producer": {
                "path": expected_frozen["legacy_producer"]["path"],
                "runtime_kind": "live-legacy-ioctl-compatibility-overlay-observation",
                "sha256": expected_frozen["legacy_producer"]["sha256"],
                "size": expected_frozen["legacy_producer"]["size"],
            },
        },
        "native-rust-source-fixture": {
            "expected_overlay_host_driver_sha256": None,
            "producer": {
                "path": expected_frozen["native_producer"]["path"],
                "runtime_kind": "standalone-source-fixture-not-module-runtime",
                "sha256": expected_frozen["native_producer"]["sha256"],
                "size": expected_frozen["native_producer"]["size"],
            },
        },
    }
    _require(contract["surfaces"], expected_surfaces, "surface policy")
    expected_workflow_policy = {
        "legacy_boot_step": "Boot disposable Rocky guest and run mcexec",
        "legacy_containing_upload_step": "Upload hosted boot evidence without ephemeral SSH keys",
        "legacy_finalize_step": "Finalize and verify FP-0006 legacy envelope on the clean host",
        "legacy_job": "hosted-boot-smoke",
        "legacy_preflight_step": "Validate FP-0006 capture authority before disposable QEMU",
        "legacy_upload_step": "Upload FP-0006 legacy envelope",
        "native_bootstrap_step": "Install pinned Rust and identify the observed FP-0006 linker",
        "native_capture_step": "Produce and review the FP-0006 native envelope",
        "native_checkout_step": "Check out the exact FP-0006 candidate without credentials",
        "native_failure_upload_step": "Upload FP-0006 first-failure diagnostics",
        "native_job": "fp0006-native-rust-capture",
        "native_upload_step": "Upload FP-0006 native envelope",
    }
    _require(contract["workflow_policy"], expected_workflow_policy, "workflow policy")

    bound_files = contract["bound_files"]
    _require_keys(
        bound_files,
        (
            "legacy_workflow", "native_runtime_validator", "native_workflow",
            "qemu_guest_runner", "qemu_validation_wrapper", "rocky_validation",
        ),
        "integration file bindings",
    )
    loaded = {}  # type: Dict[str, bytes]
    expected_paths = {
        "legacy_workflow": ".github/workflows/rust-x86_64-validation.yml",
        "native_workflow": ".github/workflows/native-rust-host-modules-exact-build.yml",
        "rocky_validation": "scripts/rocky-rust-validation.sh",
        "native_runtime_validator": "scripts/native_rust_runtime_evidence.py",
        "qemu_guest_runner": "scripts/qemu-mckernel-guest.sh",
        "qemu_validation_wrapper": "scripts/qemu-rocky-rust-validation.sh",
    }
    for name, path in expected_paths.items():
        binding = bound_files[name]
        binding_keys = ("path", "sha256", "size")
        if name in ("qemu_guest_runner", "qemu_validation_wrapper"):
            binding_keys = ("active_sha256", "path", "sha256", "size")
        _require_keys(binding, binding_keys, "binding " + name)
        _require(binding["path"], path, "binding path " + name)
        if type(binding["sha256"]) is not str or HEX64.fullmatch(binding["sha256"]) is None:
            raise CaptureError("binding digest is invalid: {0}".format(name))
        _require_int(binding["size"], "binding size " + name)
        data_bound = _read_regular(repo / path, path, 8 * MAX_INPUT_BYTES)
        if len(data_bound) != binding["size"] or _sha256(data_bound) != binding["sha256"]:
            raise CaptureError("integration file identity differs: {0}".format(path))
        loaded[name] = data_bound
    _require(
        bound_files["qemu_validation_wrapper"]["active_sha256"],
        EXPECTED_QEMU_WRAPPER_ACTIVE_SHA256,
        "QEMU validation wrapper active digest",
    )
    _require(
        bound_files["qemu_guest_runner"]["active_sha256"],
        EXPECTED_QEMU_RUNNER_ACTIVE_SHA256,
        "QEMU guest runner active digest",
    )

    try:
        legacy_text = loaded["legacy_workflow"].decode("utf-8")
        native_text = loaded["native_workflow"].decode("utf-8")
        rocky_text = loaded["rocky_validation"].decode("utf-8")
        qemu_wrapper_text = loaded["qemu_validation_wrapper"].decode("utf-8")
        qemu_runner_text = loaded["qemu_guest_runner"].decode("utf-8")
    except UnicodeDecodeError as error:
        raise CaptureError("bound integration source is not UTF-8: {0}".format(error))
    _validate_legacy_workflow(legacy_text, contract["workflow_policy"])
    _validate_native_workflow(native_text, contract["workflow_policy"])
    _validate_rocky_script(rocky_text)
    _validate_qemu_sources(qemu_wrapper_text, qemu_runner_text)

    base = _load_base_checker(repo)
    try:
        summary = base.validate_contract(repo)
    except Exception as error:
        raise CaptureError("frozen base witness validation failed: {0}".format(error))
    _require(summary["contract_id"], contract["base_witness"]["contract_id"], "base contract id")
    _require(summary["contract_sha256"], expected_frozen["contract"]["sha256"], "base contract digest")
    return contract, data


def validate_contract(repo: Path = ROOT) -> Dict[str, Any]:
    contract, data = _load_contract(repo)
    return {
        "claims": contract["claims"],
        "contract_id": contract["contract_id"],
        "contract_sha256": _sha256(data),
        "dedicated_retention_days": contract["artifact_policy"]["dedicated_actions_retention_days"],
        "durable": False,
        "result_authority": contract["result_authority"]["status"],
        "status": "CAPTURE_INTEGRATION_VALIDATED_NONCREDITING",
    }


def _octal(value: int, width: int) -> bytes:
    rendered = ("{0:0" + str(width - 1) + "o}\0").format(value).encode("ascii")
    if len(rendered) != width:
        raise CaptureError("USTAR numeric field exceeds its fixed width")
    return rendered


def _tar_header(name: str, size: int) -> bytes:
    encoded = name.encode("ascii")
    if len(encoded) > 99 or b"/" in encoded or not encoded:
        raise CaptureError("USTAR member name is outside the canonical profile")
    header = bytearray(TAR_BLOCK)
    header[0:len(encoded)] = encoded
    header[100:108] = _octal(0o444, 8)
    header[108:116] = _octal(0, 8)
    header[116:124] = _octal(0, 8)
    header[124:136] = _octal(size, 12)
    header[136:148] = _octal(0, 12)
    header[148:156] = b"        "
    header[156:157] = b"0"
    header[257:263] = b"ustar\0"
    header[263:265] = b"00"
    header[329:337] = _octal(0, 8)
    header[337:345] = _octal(0, 8)
    checksum = sum(header)
    rendered = "{0:06o}\0 ".format(checksum).encode("ascii")
    if len(rendered) != 8:
        raise CaptureError("USTAR checksum exceeds its fixed width")
    header[148:156] = rendered
    return bytes(header)


def _build_tar(members: Sequence[Tuple[str, bytes]]) -> bytes:
    output = bytearray()
    for name, data in members:
        if len(data) > MAX_INPUT_BYTES:
            raise CaptureError("envelope member exceeds its size bound: {0}".format(name))
        output.extend(_tar_header(name, len(data)))
        output.extend(data)
        padding = (-len(data)) % TAR_BLOCK
        if padding:
            output.extend(b"\0" * padding)
    output.extend(b"\0" * (2 * TAR_BLOCK))
    record_padding = (-len(output)) % TAR_RECORD
    if record_padding:
        output.extend(b"\0" * record_padding)
    return bytes(output)


def _parse_octal(field: bytes, label: str) -> int:
    if not field.endswith(b"\0") or any(value not in b"01234567" for value in field[:-1]):
        raise CaptureError("canonical USTAR {0} field differs".format(label))
    try:
        return int(field[:-1].decode("ascii"), 8)
    except ValueError:
        raise CaptureError("canonical USTAR {0} field is invalid".format(label))


def _parse_tar(data: bytes, expected_names: Sequence[str]) -> Dict[str, bytes]:
    if not data or len(data) > 4 * MAX_INPUT_BYTES or len(data) % TAR_RECORD:
        raise CaptureError("envelope length is outside the canonical USTAR profile")
    offset = 0
    members = []  # type: List[Tuple[str, bytes]]
    for expected_name in expected_names:
        if offset + TAR_BLOCK > len(data):
            raise CaptureError("envelope ended before all fixed members")
        header = data[offset:offset + TAR_BLOCK]
        offset += TAR_BLOCK
        if header == b"\0" * TAR_BLOCK:
            raise CaptureError("envelope ended before all fixed members")
        raw_name = header[0:100]
        if b"\0" not in raw_name:
            raise CaptureError("USTAR member name is not terminated")
        name_bytes, tail = raw_name.split(b"\0", 1)
        if any(tail):
            raise CaptureError("USTAR member name padding is nonzero")
        try:
            name = name_bytes.decode("ascii")
        except UnicodeDecodeError:
            raise CaptureError("USTAR member name is not ASCII")
        if name != expected_name:
            raise CaptureError("envelope members are missing, extra, or reordered")
        size = _parse_octal(header[124:136], "size")
        if size > MAX_INPUT_BYTES or offset + size > len(data):
            raise CaptureError("USTAR member size is outside its bound")
        member = data[offset:offset + size]
        offset += size
        padding = (-size) % TAR_BLOCK
        if data[offset:offset + padding] != b"\0" * padding:
            raise CaptureError("USTAR member padding is nonzero")
        offset += padding
        members.append((name, member))
    if data[offset:offset + 2 * TAR_BLOCK] != b"\0" * (2 * TAR_BLOCK):
        raise CaptureError("USTAR end marker differs")
    if any(data[offset + 2 * TAR_BLOCK:]):
        raise CaptureError("USTAR envelope has nonzero trailing data")
    rebuilt = _build_tar(members)
    if data != rebuilt:
        raise CaptureError("USTAR metadata is not the canonical fixed profile")
    return dict(members)


def _artifact_tar_bytes(path: Path) -> bytes:
    path = Path(path)
    try:
        metadata = os.lstat(str(path))
    except OSError as error:
        raise CaptureError("cannot inspect lane artifact: {0}".format(error))
    if stat.S_ISLNK(metadata.st_mode):
        raise CaptureError("lane artifact input must not be a symlink")
    if stat.S_ISDIR(metadata.st_mode):
        names = sorted(os.listdir(str(path)))
        if names != [ENVELOPE_NAME]:
            raise CaptureError("lane artifact directory must contain only the envelope")
        return _read_regular(path / ENVELOPE_NAME, "lane USTAR envelope", 4 * MAX_INPUT_BYTES)
    if not stat.S_ISREG(metadata.st_mode):
        raise CaptureError("lane artifact input must be a directory or transport ZIP")
    data = _read_regular(path, "lane artifact transport ZIP", 8 * MAX_INPUT_BYTES)
    try:
        archive = zipfile.ZipFile(io.BytesIO(data), mode="r")
    except (OSError, zipfile.BadZipFile) as error:
        raise CaptureError("lane artifact transport is not a valid ZIP: {0}".format(error))
    with archive:
        records = archive.infolist()
        if len(records) != 1 or records[0].filename != ENVELOPE_NAME:
            raise CaptureError("transport ZIP must contain only the canonical envelope")
        record = records[0]
        if record.flag_bits & 0x1 or record.file_size > 4 * MAX_INPUT_BYTES:
            raise CaptureError("transport ZIP member is encrypted or oversized")
        mode = (record.external_attr >> 16) & 0o170000
        if mode not in (0, stat.S_IFREG):
            raise CaptureError("transport ZIP envelope is not a regular file")
        try:
            envelope = archive.read(record)
        except (OSError, RuntimeError, zipfile.BadZipFile) as error:
            raise CaptureError("cannot read transport ZIP envelope: {0}".format(error))
        if len(envelope) != record.file_size:
            raise CaptureError("transport ZIP envelope length differs")
        return envelope


def _manifest(members: Sequence[Tuple[str, bytes]]) -> bytes:
    return b"".join(
        ("{0}  {1}\n".format(_sha256(data), name)).encode("ascii")
        for name, data in sorted(members, key=lambda item: item[0])
    )


def _validate_manifest(data: bytes, members: Dict[str, bytes]) -> None:
    expected = _manifest(
        [(name, value) for name, value in members.items() if name != "SHA256SUMS"]
    )
    if data != expected:
        raise CaptureError("internal SHA256SUMS differs")


def _validate_run_metadata(
    head: str, repository: str, run_id: str, run_attempt: str
) -> Tuple[str, str, int, int]:
    if type(head) is not str or HEX40.fullmatch(head) is None:
        raise CaptureError("head must be an exact lowercase 40-hex commit")
    if type(repository) is not str or REPOSITORY.fullmatch(repository) is None:
        raise CaptureError("GitHub repository identity is invalid")
    if type(run_id) is not str or POSITIVE_DECIMAL.fullmatch(run_id) is None:
        raise CaptureError("GitHub run id is not a positive canonical decimal")
    if type(run_attempt) is not str or POSITIVE_DECIMAL.fullmatch(run_attempt) is None:
        raise CaptureError("GitHub run attempt is not a positive canonical decimal")
    return head, repository, int(run_id), int(run_attempt)


def _github_observation(
    head: str, repository: str, run_id: str, run_attempt: str,
    event_name: str, ref: str, github_sha: str, workflow_sha: str,
    base_sha: str,
) -> Dict[str, Any]:
    head, repository, run_id_value, run_attempt_value = _validate_run_metadata(
        head, repository, run_id, run_attempt
    )
    allowed_events = ("pull_request", "push", "workflow_call", "workflow_dispatch")
    if event_name not in allowed_events:
        raise CaptureError("GitHub event name is outside the capture policy")
    if type(ref) is not str or GITHUB_REF.fullmatch(ref) is None or ".." in ref:
        raise CaptureError("GitHub ref is outside the capture policy")
    for value, label in (
        (github_sha, "GitHub SHA"), (workflow_sha, "workflow definition SHA")
    ):
        if type(value) is not str or HEX40.fullmatch(value) is None:
            raise CaptureError("{0} is not exact lowercase 40-hex".format(label))
    if base_sha == "none":
        base = None
    elif type(base_sha) is str and HEX40.fullmatch(base_sha) is not None:
        base = base_sha
    else:
        raise CaptureError("GitHub base SHA is neither none nor exact lowercase 40-hex")
    if event_name == "pull_request":
        if base is None or not ref.startswith("refs/pull/") or not ref.endswith("/merge"):
            raise CaptureError("pull-request run identity is incomplete")
    elif base is not None:
        raise CaptureError("non-pull-request run unexpectedly claims a base SHA")
    return {
        "base_sha": base,
        "event_name": event_name,
        "github_sha": github_sha,
        "head_sha": head,
        "ref": ref,
        "repository": repository,
        "run_attempt": run_attempt_value,
        "run_id": run_id_value,
        "workflow_candidate_aligned": bool(
            github_sha == head and workflow_sha == head
        ),
        "workflow_sha": workflow_sha,
    }


def _write_bytes_exclusive(path: Path, data: bytes, mode: int = 0o444) -> None:
    descriptor = os.open(
        str(path),
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_CLOEXEC", 0),
        0o400,
    )
    try:
        offset = 0
        while offset < len(data):
            written = os.write(descriptor, data[offset:])
            if written <= 0:
                raise CaptureError("cannot write {0}".format(path.name))
            offset += written
        os.fchmod(descriptor, mode)
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _write_envelope(output_dir: Path, envelope: bytes) -> None:
    output_dir = Path(output_dir)
    parent = output_dir.parent
    try:
        parent_metadata = os.lstat(str(parent))
    except OSError as error:
        raise CaptureError("cannot inspect output parent: {0}".format(error))
    if stat.S_ISLNK(parent_metadata.st_mode) or not stat.S_ISDIR(parent_metadata.st_mode):
        raise CaptureError("output parent must be a non-symlink directory")
    if os.path.lexists(str(output_dir)):
        raise CaptureError("output directory already exists")
    try:
        os.mkdir(str(output_dir), 0o700)
        _write_bytes_exclusive(output_dir / ENVELOPE_NAME, envelope)
        directory = os.open(str(output_dir), os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    except Exception:
        try:
            os.unlink(str(output_dir / ENVELOPE_NAME))
        except OSError:
            pass
        try:
            os.rmdir(str(output_dir))
        except OSError:
            pass
        raise


def _candidate_output_dir(output_dir: Path) -> Path:
    output_dir = Path(output_dir)
    candidate = output_dir.parent / ("." + output_dir.name + ".candidate")
    if os.path.lexists(str(output_dir)):
        raise CaptureError("final upload directory already exists")
    if os.path.lexists(str(candidate)):
        raise CaptureError("private candidate directory already exists")
    return candidate


def _discard_candidate(candidate: Path) -> None:
    envelope = Path(candidate) / ENVELOPE_NAME
    try:
        os.unlink(str(envelope))
    except OSError:
        pass
    try:
        os.rmdir(str(candidate))
    except OSError:
        pass


def _publish_candidate(candidate: Path, output_dir: Path) -> None:
    candidate = Path(candidate)
    output_dir = Path(output_dir)
    source = candidate / ENVELOPE_NAME
    destination = output_dir / ENVELOPE_NAME
    if os.path.lexists(str(output_dir)):
        raise CaptureError("final upload directory appeared before publication")
    published = False
    try:
        os.mkdir(str(output_dir), 0o700)
        os.link(str(source), str(destination), follow_symlinks=False)
        published = True
        directory = os.open(str(output_dir), os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
        parent = os.open(
            str(output_dir.parent), os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
        )
        try:
            os.fsync(parent)
        finally:
            os.close(parent)
        os.unlink(str(source))
        os.rmdir(str(candidate))
    except Exception:
        if published:
            try:
                os.unlink(str(destination))
            except OSError:
                pass
        try:
            os.rmdir(str(output_dir))
        except OSError:
            pass
        raise


def _base_review_from_members(
    repo: Path, surface: str, members: Dict[str, bytes]
) -> Dict[str, Any]:
    names = ("raw.jsonl", "result.jsonl", "state-ledger.jsonl")
    with tempfile.TemporaryDirectory(prefix="fp0006-base-capture-") as directory:
        root = Path(directory)
        for name in names:
            _write_bytes_exclusive(root / name, members[name])
        base = _load_base_checker(Path(repo))
        try:
            return base.review_artifact(Path(repo), root, surface)
        except Exception as error:
            raise CaptureError("base capture review failed: {0}".format(error))


def _base_summary(review: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "artifact_content_closure_sha256": review["artifact_content_closure_sha256"],
        "capture_schema_validated": True,
        "raw_sha256": review["raw_sha256"],
        "result_sha256": review["result_sha256"],
        "state_ledger_sha256": review["state_ledger_sha256"],
    }


def _parse_json_lines(data: bytes, label: str) -> List[Dict[str, Any]]:
    if not data or not data.endswith(b"\n"):
        raise CaptureError("{0} is empty or lacks a final newline".format(label))
    records = []
    for index, line in enumerate(data.splitlines(True)):
        value = _load_json(line, "{0} record {1}".format(label, index))
        if type(value) is not dict or line != _canonical_json(value):
            raise CaptureError("{0} record is not canonical JSON".format(label))
        records.append(value)
    return records


def _producer_command(surface: str) -> List[str]:
    prefix = [
        "/usr/bin/env", "-i", "HOME=/nonexistent", "LANG=C", "LC_ALL=C",
        "PATH=/usr/bin:/bin",
    ]
    if surface == "legacy-live-ioctl":
        return prefix + [
            "/usr/bin/timeout", "--signal=TERM", "--kill-after=5s", "30s",
            "<producer-by-sha256>", "/dev/mcd0", "<capture-stage>",
        ]
    if surface == "native-rust-source-fixture":
        return prefix + [
            "/usr/bin/timeout", "--signal=TERM", "--kill-after=5s", "30s",
            "<producer-by-sha256>", "<capture-stage>",
        ]
    raise CaptureError("producer command surface is not recognized")


def _validate_tool_report(data: bytes, surface: str) -> Dict[str, Any]:
    if not data or len(data) > 65536 or b"\0" in data or not data.endswith(b"\n"):
        raise CaptureError("tool observation has an invalid byte boundary")
    try:
        text = data.decode("ascii")
    except UnicodeDecodeError:
        raise CaptureError("tool observation is not ASCII")
    lines = text.splitlines()
    digest_line = re.compile(r"^([0-9a-f]{64})  (/usr/bin/(?:gcc|rustc|timeout))$")
    rpm_version = r"[0-9][0-9A-Za-z.+_~]*"
    rpm_release = r"[0-9][0-9A-Za-z.+_~]*"
    gcc_version_positions = [
        index for index, line in enumerate(lines) if line.startswith("gcc ")
    ]
    timeout_version_positions = [
        index for index, line in enumerate(lines) if line.startswith("timeout ")
    ]
    if surface == "legacy-live-ioctl":
        legacy_gcc_owner = re.compile(
            r"^gcc-0:{0}-{1}\.el8(?:_10)?\.x86_64$".format(
                rpm_version, rpm_release
            )
        )
        legacy_coreutils_owner = re.compile(
            r"^coreutils-0:{0}-{1}\.el8(?:_10)?\.x86_64$".format(
                rpm_version, rpm_release
            )
        )
        if (
            len(lines) < 8 or legacy_gcc_owner.fullmatch(lines[0]) is None
            or legacy_coreutils_owner.fullmatch(lines[1]) is None
        ):
            raise CaptureError("legacy GCC owner observation differs")
        match = digest_line.fullmatch(lines[2])
        timeout_match = digest_line.fullmatch(lines[3])
        if (
            match is None or match.group(2) != "/usr/bin/gcc"
            or timeout_match is None or timeout_match.group(2) != "/usr/bin/timeout"
        ):
            raise CaptureError("legacy GCC digest observation differs")
        if (
            gcc_version_positions != [4] or len(timeout_version_positions) != 1
            or timeout_version_positions[0] <= gcc_version_positions[0]
        ):
            raise CaptureError("legacy GCC version observation differs")
        return {
            "exact_surface_compiler_provenance": False,
            "exact_toolchain_proven": False,
            "gcc_owner": lines[0],
            "gcc_path": "/usr/bin/gcc",
            "gcc_sha256": match.group(1),
            "gcc_version_first_line": lines[4],
            "rust_owner": None,
            "rustc_path": None,
            "rustc_sha256": None,
            "rustc_version_first_line": None,
            "timeout_owner": lines[1],
            "timeout_path": "/usr/bin/timeout",
            "timeout_sha256": timeout_match.group(1),
            "timeout_version_first_line": lines[timeout_version_positions[0]],
        }
    if surface != "native-rust-source-fixture":
        raise CaptureError("tool observation surface is not recognized")
    expected_rust_version = (
        "rustc 1.92.0 (ded5c06cf 2025-12-08) (Red Hat 1.92.0-1.el10)"
    )
    native_el10_release = r"\.el10(?:_[1-9][0-9]?)?\.x86_64"
    native_gcc_owner = re.compile(
        r"^gcc-0:{0}-{1}{2}$".format(
            rpm_version, rpm_release, native_el10_release
        )
    )
    native_coreutils_owner = re.compile(
        r"^coreutils-0:{0}-{1}{2}$".format(
            rpm_version, rpm_release, native_el10_release
        )
    )
    if (
        len(lines) < 16
        or lines[0] != "rust-0:1.92.0-1.el10.x86_64"
        or native_gcc_owner.fullmatch(lines[1]) is None
        or native_coreutils_owner.fullmatch(lines[2]) is None
    ):
        raise CaptureError("native package owner observation differs")
    rust_digest = digest_line.fullmatch(lines[3])
    gcc_digest = digest_line.fullmatch(lines[4])
    timeout_digest = digest_line.fullmatch(lines[5])
    if (
        rust_digest is None or rust_digest.group(2) != "/usr/bin/rustc"
        or gcc_digest is None or gcc_digest.group(2) != "/usr/bin/gcc"
        or timeout_digest is None or timeout_digest.group(2) != "/usr/bin/timeout"
    ):
        raise CaptureError("native tool digest observation differs")
    required_rust_lines = (
        expected_rust_version,
        "binary: rustc",
        "commit-date: 2025-12-08",
        "host: x86_64-unknown-linux-gnu",
        "release: 1.92.0",
    )
    rust_positions = []  # type: List[int]
    for line in required_rust_lines:
        if lines.count(line) != 1:
            raise CaptureError("native rustc verbose observation differs")
        rust_positions.append(lines.index(line))
    if rust_positions != sorted(rust_positions):
        raise CaptureError("native rustc verbose observation is reordered")
    commit_lines = [line for line in lines if line.startswith("commit-hash: ")]
    if (
        len(commit_lines) != 1
        or re.fullmatch(r"commit-hash: ded5c06cf[0-9a-f]{31}", commit_lines[0]) is None
    ):
        raise CaptureError("native rustc commit observation differs")
    if len(gcc_version_positions) != 1 or gcc_version_positions[0] <= rust_positions[-1]:
        raise CaptureError("native GCC version observation differs")
    if (
        len(timeout_version_positions) != 1
        or timeout_version_positions[0] <= gcc_version_positions[0]
    ):
        raise CaptureError("native timeout version observation differs")
    return {
        "exact_surface_compiler_provenance": False,
        "exact_toolchain_proven": False,
        "gcc_owner": lines[1],
        "gcc_path": "/usr/bin/gcc",
        "gcc_sha256": gcc_digest.group(1),
        "gcc_version_first_line": lines[gcc_version_positions[0]],
        "rust_owner": lines[0],
        "rustc_path": "/usr/bin/rustc",
        "rustc_sha256": rust_digest.group(1),
        "rustc_version_first_line": expected_rust_version,
        "timeout_owner": lines[2],
        "timeout_path": "/usr/bin/timeout",
        "timeout_sha256": timeout_digest.group(1),
        "timeout_version_first_line": lines[timeout_version_positions[0]],
    }


def _validate_execution_log(
    data: bytes, surface: str, github: Dict[str, Any], binary_sha256: str,
    tool_report_sha256: str, preflight_sha256: Optional[str] = None,
    overlay_sha256: Optional[str] = None,
) -> Dict[str, Any]:
    records = _parse_json_lines(data, "producer execution log")
    if len(records) != 3:
        raise CaptureError("producer execution log record count differs")
    start, output, finish = records
    expected_start = dict(github)
    expected_start.update({
        "binary_sha256": binary_sha256,
        "event": "producer-start",
        "normalized_command": _producer_command(surface),
        "surface": surface,
        "tool_report_sha256": tool_report_sha256,
    })
    if surface == "legacy-live-ioctl":
        expected_start.update(
            {
                "device": "/dev/mcd0",
                "overlay_host_driver_sha256": overlay_sha256,
                "preflight_sha256": preflight_sha256,
                "timeout_seconds": 30,
            }
        )
    else:
        expected_start["linker"] = "/usr/bin/gcc"
        expected_start["timeout_seconds"] = 30
    _require(start, expected_start, "producer start record")
    _require(
        output,
        {
            "event": "producer-output", "output_bytes": 0,
            "output_sha256": EMPTY_SHA256, "surface": surface,
        },
        "producer output record",
    )
    _require(
        finish,
        {"event": "producer-exit", "status": 0, "surface": surface},
        "producer exit record",
    )
    return {
        "binary_sha256": binary_sha256,
        "log_sha256": _sha256(data),
        "output_bytes": 0,
        "output_sha256": EMPTY_SHA256,
        "overlay_host_driver_sha256": overlay_sha256,
        "preflight_manifest_sha256": preflight_sha256,
        "producer_command": _producer_command(surface),
        "tool_report_sha256": tool_report_sha256,
    }


def _compiler_command(surface: str) -> List[str]:
    if surface == "legacy-live-ioctl":
        return [
            "/usr/bin/env", "-i", "HOME=/nonexistent", "LANG=C", "LC_ALL=C",
            "PATH=/usr/bin:/bin", "/usr/bin/gcc", "-O2", "-std=c11", "-Wall",
            "-Wextra", "-Werror",
            "scripts/smoke/fp0006-ihk-device-negative-dispatch.c", "-o",
            "fp0006-legacy-producer",
        ]
    if surface == "native-rust-source-fixture":
        return [
            "/usr/bin/env", "-i", "HOME=/nonexistent", "LANG=C", "LC_ALL=C",
            "PATH=/usr/bin:/bin", "/usr/bin/rustc", "--edition=2021",
            "-D", "warnings", "-C", "linker=/usr/bin/gcc", "-C",
            "strip=symbols",
            "scripts/tests/fixtures/ihk_ioctl_fp0006_negative_dispatch.rs", "-o",
            "fp0006-native-rust-producer",
        ]
    raise CaptureError("compiler command surface is not recognized")


def _review_object(
    contract: Dict[str, Any], base_review: Dict[str, Any], surface: str,
    github: Dict[str, Any], execution: Dict[str, Any], authority_sha256: str,
    tool_observation: Dict[str, Any],
) -> Dict[str, Any]:
    return {
        "artifact_contract_id": contract["contract_id"],
        "authority_sha256": authority_sha256,
        "base_capture": _base_summary(base_review),
        "base_witness_contract_id": contract["base_witness"]["contract_id"],
        "base_witness_contract_sha256": contract["base_witness"]["files"]["contract"]["sha256"],
        "claims": contract["claims"],
        "dedicated_actions_artifact": {
            "compression_level": 0, "durable": False, "retention_days": 30,
        },
        "execution": execution,
        "github": github,
        "producer": contract["surfaces"][surface]["producer"],
        "result_authority": contract["result_authority"],
        "surface": surface,
        "tool_observation": tool_observation,
        "vectors": contract["vectors"],
    }


def _assemble_envelope(
    contract: Dict[str, Any], authority: bytes, compiler_log: bytes,
    producer_output: bytes, producer_log: bytes, capture: Dict[str, bytes],
    review: Dict[str, Any], tool_report: bytes, output_dir: Path,
) -> None:
    initial = [
        ("authority.json", authority),
        ("compiler.log", compiler_log),
        ("producer-output.log", producer_output),
        ("producer.log", producer_log),
        ("raw.jsonl", capture["raw.jsonl"]),
        ("result.jsonl", capture["result.jsonl"]),
        ("review.json", _canonical_json(review)),
        ("state-ledger.jsonl", capture["state-ledger.jsonl"]),
        ("tool-report.txt", tool_report),
    ]
    members = initial + [("SHA256SUMS", _manifest(initial))]
    envelope = _build_tar(members)
    _parse_tar(envelope, contract["artifact_policy"]["envelope_members"])
    _write_envelope(output_dir, envelope)


def preflight_legacy(
    repo: Path, producer_binary: Path, compiler_report: Path, compiler_output: Path,
    output_manifest: Path, head: str, repository: str, run_id: str,
    run_attempt: str, event_name: str, ref: str, github_sha: str,
    workflow_sha: str, base_sha: str,
) -> Dict[str, Any]:
    contract, contract_bytes = _load_contract(repo)
    github = _github_observation(
        head, repository, run_id, run_attempt, event_name, ref, github_sha,
        workflow_sha, base_sha,
    )
    if github["event_name"] != "pull_request":
        raise CaptureError("legacy live capture is restricted to a pull-request event")
    if _git_head(Path(repo)) != github["head_sha"]:
        raise CaptureError("legacy preflight head differs from repository HEAD")
    binary = _read_producer_binary(producer_binary, "legacy producer binary")
    report = _read_regular(compiler_report, "legacy compiler observation", 65536)
    _validate_tool_report(report, "legacy-live-ioctl")
    compile_log = _read_regular(compiler_output, "legacy compiler output", 65536)
    if compile_log:
        raise CaptureError("successful legacy compiler output must be empty")
    try:
        report_text = report.decode("utf-8")
    except UnicodeDecodeError:
        raise CaptureError("legacy compiler observation is not UTF-8")
    manifest = {
        "claims": contract["claims"],
        "compiler_observation": {
            "bytes": len(report), "sha256": _sha256(report), "text": report_text,
        },
        "compiler_execution": {
            "command": _compiler_command("legacy-live-ioctl"),
            "output_bytes": len(compile_log),
            "output_sha256": _sha256(compile_log),
        },
        "contract_id": contract["contract_id"],
        "contract_sha256": _sha256(contract_bytes),
        "github": github,
        "producer_binary": {"bytes": len(binary), "sha256": _sha256(binary)},
        "producer_source": contract["surfaces"]["legacy-live-ioctl"]["producer"],
        "result_authority": contract["result_authority"],
        "status": "PREFLIGHT_VALIDATED_NONCREDITING",
    }
    data = _canonical_json(manifest)
    output_manifest = Path(output_manifest)
    if os.path.lexists(str(output_manifest)):
        raise CaptureError("legacy preflight manifest already exists")
    _write_bytes_exclusive(output_manifest, data)
    return {
        "claims": contract["claims"], "manifest_sha256": _sha256(data),
        "result_authority": contract["result_authority"]["status"],
        "status": "PREFLIGHT_VALIDATED_NONCREDITING",
    }


def _load_preflight(
    data: bytes, contract: Dict[str, Any], expected_github: Dict[str, Any],
) -> Dict[str, Any]:
    value = _load_json(data, "legacy preflight manifest")
    if data != _canonical_json(value):
        raise CaptureError("legacy preflight manifest is not canonical JSON")
    _require_keys(
        value,
        (
            "claims", "compiler_execution", "compiler_observation", "contract_id",
            "contract_sha256", "github", "producer_binary", "producer_source",
            "result_authority", "status",
        ),
        "legacy preflight manifest",
    )
    _require(value["claims"], contract["claims"], "preflight claims")
    _require(value["contract_id"], contract["contract_id"], "preflight contract")
    _require(value["contract_sha256"], EXPECTED_CONTRACT_SHA256, "preflight contract digest")
    _require(value["producer_source"], contract["surfaces"]["legacy-live-ioctl"]["producer"], "preflight producer")
    _require(value["result_authority"], contract["result_authority"], "preflight result authority")
    _require(value["status"], "PREFLIGHT_VALIDATED_NONCREDITING", "preflight status")
    github = value["github"]
    _require(github, expected_github, "preflight GitHub identity")
    compiler = value["compiler_observation"]
    _require_keys(compiler, ("bytes", "sha256", "text"), "compiler observation")
    if type(compiler["text"]) is not str:
        raise CaptureError("compiler observation text is invalid")
    encoded = compiler["text"].encode("utf-8")
    _require(compiler["bytes"], len(encoded), "compiler observation size")
    _require(compiler["sha256"], _sha256(encoded), "compiler observation digest")
    _validate_tool_report(encoded, "legacy-live-ioctl")
    _require(
        value["compiler_execution"],
        {
            "command": _compiler_command("legacy-live-ioctl"),
            "output_bytes": 0,
            "output_sha256": EMPTY_SHA256,
        },
        "legacy compiler execution",
    )
    binary = value["producer_binary"]
    _require_keys(binary, ("bytes", "sha256"), "preflight producer binary")
    if _require_int(binary["bytes"], "preflight binary size") <= 0:
        raise CaptureError("preflight producer binary is empty")
    if type(binary["sha256"]) is not str or HEX64.fullmatch(binary["sha256"]) is None:
        raise CaptureError("preflight producer binary digest is invalid")
    return value


def finalize_lane(
    repo: Path, capture_dir: Path, producer_output: Path, producer_log: Path,
    producer_binary: Path, tool_report: Path, compiler_output: Path,
    output_dir: Path, surface: str,
    head: str, repository: str, run_id: str, run_attempt: str,
    event_name: str, ref: str, github_sha: str, workflow_sha: str,
    base_sha: str,
) -> Dict[str, Any]:
    contract, _ = _load_contract(repo)
    if surface != "native-rust-source-fixture":
        raise CaptureError("direct lane finalization is limited to the native fixture")
    github = _github_observation(
        head, repository, run_id, run_attempt, event_name, ref, github_sha,
        workflow_sha, base_sha,
    )
    if _git_head(Path(repo)) != github["head_sha"]:
        raise CaptureError("native capture head differs from repository HEAD")
    producer_output_bytes = _read_regular(producer_output, "native producer output", 65536)
    if producer_output_bytes:
        raise CaptureError("successful native producer output must be empty")
    compiler_log = _read_regular(compiler_output, "native compiler output", 65536)
    if compiler_log:
        raise CaptureError("successful native compiler output must be empty")
    binary = _read_producer_binary(producer_binary, "native producer binary")
    tool = _read_regular(tool_report, "native tool observation", 65536)
    tool_observation = _validate_tool_report(tool, surface)
    log = _read_regular(producer_log, "native producer execution log", 65536)
    execution = _validate_execution_log(
        log, surface, github, _sha256(binary), _sha256(tool)
    )
    execution.update(
        {
            "compiler_command": _compiler_command(surface),
            "compiler_log_sha256": _sha256(compiler_log),
            "compiler_output_bytes": len(compiler_log),
        }
    )
    capture = {
        name: _read_regular(Path(capture_dir) / name, "native " + name)
        for name in ("raw.jsonl", "result.jsonl", "state-ledger.jsonl")
    }
    base_review = _base_review_from_members(Path(repo), surface, capture)
    authority = _canonical_json(
        {
            "claims": contract["claims"],
            "compiler_execution": {
                "command": _compiler_command(surface),
                "output_bytes": len(compiler_log),
                "output_sha256": _sha256(compiler_log),
            },
            "contract_id": contract["contract_id"],
            "contract_sha256": EXPECTED_CONTRACT_SHA256,
            "github": github,
            "producer_binary": {"bytes": len(binary), "sha256": _sha256(binary)},
            "producer_source": contract["surfaces"][surface]["producer"],
            "result_authority": contract["result_authority"],
            "status": "NATIVE_TOOL_OBSERVED_NONCREDITING",
            "tool_observation": {
                "bytes": len(tool), "sha256": _sha256(tool),
                "summary": tool_observation,
            },
        }
    )
    review = _review_object(
        contract, base_review, surface, github, execution, _sha256(authority),
        tool_observation,
    )
    candidate = _candidate_output_dir(output_dir)
    try:
        _assemble_envelope(
            contract, authority, compiler_log, producer_output_bytes, log, capture,
            review, tool, candidate,
        )
        result = _review_lane_with_contract(Path(repo), contract, candidate, surface)
        _publish_candidate(candidate, output_dir)
    except Exception:
        _discard_candidate(candidate)
        raise
    result["status"] = "LANE_CAPTURED_UNREVIEWED_NONCREDITING"
    return result


def _load_legacy_observation(path: Path) -> Dict[str, bytes]:
    path = Path(path)
    try:
        metadata = os.lstat(str(path))
    except OSError as error:
        raise CaptureError("cannot inspect legacy observation: {0}".format(error))
    if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISDIR(metadata.st_mode):
        raise CaptureError("legacy observation must be a non-symlink directory")
    expected = [
        "SHA256SUMS", "capture.tar", "compiler.log", "preflight.json",
        "producer-output.log", "producer.log", "tool-report.txt",
    ]
    if sorted(os.listdir(str(path))) != expected:
        raise CaptureError("legacy observation members differ")
    files = {
        name: _read_regular(path / name, "legacy observation " + name, 4 * MAX_INPUT_BYTES)
        for name in expected
    }
    expected_manifest = _manifest(
        [
            (name, files[name]) for name in
            (
                "capture.tar", "compiler.log", "preflight.json",
                "producer-output.log", "producer.log", "tool-report.txt",
            )
        ]
    )
    if files["SHA256SUMS"] != expected_manifest:
        raise CaptureError("legacy observation SHA256SUMS differs")
    return files


def finalize_legacy_observation(
    repo: Path, observation_dir: Path, output_dir: Path, expected_head: str,
    expected_repository: str, expected_run_id: str, expected_run_attempt: str,
    expected_event_name: str, expected_ref: str, expected_github_sha: str,
    expected_workflow_sha: str, expected_base_sha: str,
) -> Dict[str, Any]:
    contract, _ = _load_contract(repo)
    expected_github = _github_observation(
        expected_head, expected_repository, expected_run_id,
        expected_run_attempt, expected_event_name, expected_ref,
        expected_github_sha, expected_workflow_sha, expected_base_sha,
    )
    if expected_github["event_name"] != "pull_request":
        raise CaptureError("legacy live capture is restricted to a pull-request event")
    if _git_head(Path(repo)) != expected_github["head_sha"]:
        raise CaptureError("legacy observation head differs from clean repository HEAD")
    observation = _load_legacy_observation(observation_dir)
    preflight = _load_preflight(
        observation["preflight.json"], contract, expected_github,
    )
    capture = _parse_tar(
        observation["capture.tar"],
        ("raw.jsonl", "result.jsonl", "state-ledger.jsonl"),
    )
    github = preflight["github"]
    if preflight["compiler_observation"]["text"].encode("utf-8") != observation["tool-report.txt"]:
        raise CaptureError("legacy archived compiler observation differs from preflight")
    tool_observation = _validate_tool_report(
        observation["tool-report.txt"], "legacy-live-ioctl"
    )
    execution = _validate_execution_log(
        observation["producer.log"], "legacy-live-ioctl", github,
        preflight["producer_binary"]["sha256"],
        preflight["compiler_observation"]["sha256"],
        _sha256(observation["preflight.json"]),
        contract["surfaces"]["legacy-live-ioctl"]["expected_overlay_host_driver_sha256"],
    )
    if observation["compiler.log"]:
        raise CaptureError("successful legacy compiler output must be empty")
    if observation["producer-output.log"]:
        raise CaptureError("successful legacy producer output must be empty")
    execution.update(
        {
            "compiler_command": _compiler_command("legacy-live-ioctl"),
            "compiler_log_sha256": _sha256(observation["compiler.log"]),
            "compiler_output_bytes": len(observation["compiler.log"]),
        }
    )
    base_review = _base_review_from_members(
        Path(repo), "legacy-live-ioctl", capture
    )
    review = _review_object(
        contract, base_review, "legacy-live-ioctl", github, execution,
        _sha256(observation["preflight.json"]), tool_observation,
    )
    candidate = _candidate_output_dir(output_dir)
    try:
        _assemble_envelope(
            contract, observation["preflight.json"], observation["compiler.log"],
            observation["producer-output.log"], observation["producer.log"], capture,
            review, observation["tool-report.txt"], candidate,
        )
        result = _review_lane_with_contract(
            Path(repo), contract, candidate, "legacy-live-ioctl"
        )
        _publish_candidate(candidate, output_dir)
    except Exception:
        _discard_candidate(candidate)
        raise
    result["status"] = "LANE_CAPTURED_UNREVIEWED_NONCREDITING"
    return result


def _review_lane_with_contract(
    repo: Path, contract: Dict[str, Any], artifact: Path,
    expected_surface: Optional[str] = None,
) -> Dict[str, Any]:
    envelope = _artifact_tar_bytes(artifact)
    files = _parse_tar(envelope, contract["artifact_policy"]["envelope_members"])
    _validate_manifest(files["SHA256SUMS"], files)
    review = _load_json(files["review.json"], "lane review")
    if files["review.json"] != _canonical_json(review):
        raise CaptureError("lane review is not canonical JSON")
    _require_keys(
        review,
        (
            "artifact_contract_id", "authority_sha256", "base_capture", "base_witness_contract_id",
            "base_witness_contract_sha256", "claims", "dedicated_actions_artifact",
            "execution", "github", "producer", "result_authority", "surface",
            "tool_observation", "vectors",
        ),
        "lane review",
    )
    _require(review["artifact_contract_id"], contract["contract_id"], "lane contract id")
    _require(review["base_witness_contract_id"], contract["base_witness"]["contract_id"], "lane base contract")
    _require(review["base_witness_contract_sha256"], contract["base_witness"]["files"]["contract"]["sha256"], "lane base digest")
    _require(review["claims"], contract["claims"], "lane claims")
    _require(review["result_authority"], contract["result_authority"], "lane result authority")
    _require(review["vectors"], contract["vectors"], "lane vectors")
    _require(
        review["authority_sha256"], _sha256(files["authority.json"]),
        "lane authority digest",
    )
    _require(
        review["dedicated_actions_artifact"],
        {"compression_level": 0, "durable": False, "retention_days": 30},
        "lane dedicated artifact policy",
    )
    surface = review["surface"]
    if type(surface) is not str or surface not in contract["surfaces"]:
        raise CaptureError("lane surface is not recognized")
    if expected_surface is not None and surface != expected_surface:
        raise CaptureError("lane surface differs from the requested surface")
    _require(review["producer"], contract["surfaces"][surface]["producer"], "lane producer")
    tool_observation = _validate_tool_report(files["tool-report.txt"], surface)
    _require(review["tool_observation"], tool_observation, "lane tool observation")
    github = review["github"]
    _require_keys(
        github,
        (
            "base_sha", "event_name", "github_sha", "head_sha", "ref",
            "repository", "run_attempt", "run_id",
            "workflow_candidate_aligned", "workflow_sha",
        ),
        "lane GitHub identity",
    )
    replayed_github = _github_observation(
        github["head_sha"], github["repository"], str(github["run_id"]),
        str(github["run_attempt"]), github["event_name"], github["ref"],
        github["github_sha"], github["workflow_sha"],
        "none" if github["base_sha"] is None else github["base_sha"],
    )
    _require(github, replayed_github, "lane GitHub identity")
    capture = {name: files[name] for name in ("raw.jsonl", "result.jsonl", "state-ledger.jsonl")}
    base_review = _base_review_from_members(repo, surface, capture)
    _require(review["base_capture"], _base_summary(base_review), "lane base capture review")
    execution = review["execution"]
    _require_keys(
        execution,
        (
            "binary_sha256", "compiler_command", "compiler_log_sha256",
            "compiler_output_bytes", "log_sha256", "output_bytes", "output_sha256",
            "overlay_host_driver_sha256", "preflight_manifest_sha256",
            "producer_command", "tool_report_sha256",
        ),
        "lane execution binding",
    )
    _require(execution["log_sha256"], _sha256(files["producer.log"]), "execution log digest")
    _require(execution["compiler_command"], _compiler_command(surface), "compiler command")
    _require(execution["producer_command"], _producer_command(surface), "producer command")
    _require(execution["compiler_log_sha256"], _sha256(files["compiler.log"]), "compiler log digest")
    _require(execution["compiler_output_bytes"], len(files["compiler.log"]), "compiler output size")
    if files["compiler.log"]:
        raise CaptureError("successful compiler output member must be empty")
    if files["producer-output.log"]:
        raise CaptureError("successful producer output member must be empty")
    _require(execution["output_sha256"], _sha256(files["producer-output.log"]), "producer output digest")
    _require(execution["output_bytes"], len(files["producer-output.log"]), "producer output size")
    _require(
        execution["tool_report_sha256"], _sha256(files["tool-report.txt"]),
        "execution tool observation digest",
    )
    _validate_execution_log(
        files["producer.log"], surface, github, execution["binary_sha256"],
        execution["tool_report_sha256"], execution["preflight_manifest_sha256"],
        execution["overlay_host_driver_sha256"],
    )
    if surface == "legacy-live-ioctl":
        authority = _load_preflight(
            files["authority.json"], contract, github,
        )
        if authority["compiler_observation"]["text"].encode("utf-8") != files["tool-report.txt"]:
            raise CaptureError("legacy envelope compiler observation differs")
        _require(
            authority["producer_binary"]["sha256"], execution["binary_sha256"],
            "legacy envelope producer binary",
        )
        _require(
            execution["overlay_host_driver_sha256"],
            contract["surfaces"][surface]["expected_overlay_host_driver_sha256"],
            "legacy overlay observation",
        )
        if type(execution["preflight_manifest_sha256"]) is not str or HEX64.fullmatch(execution["preflight_manifest_sha256"]) is None:
            raise CaptureError("legacy preflight digest is invalid")
    else:
        authority = _load_json(files["authority.json"], "native authority")
        if files["authority.json"] != _canonical_json(authority):
            raise CaptureError("native authority is not canonical JSON")
        _require_keys(
            authority,
            (
                "claims", "compiler_execution", "contract_id", "contract_sha256", "github",
                "producer_binary", "producer_source", "result_authority",
                "status", "tool_observation",
            ),
            "native authority",
        )
        _require(authority["claims"], contract["claims"], "native authority claims")
        _require(
            authority["compiler_execution"],
            {
                "command": _compiler_command(surface), "output_bytes": 0,
                "output_sha256": EMPTY_SHA256,
            },
            "native authority compiler execution",
        )
        _require(authority["contract_id"], contract["contract_id"], "native authority contract")
        _require(authority["contract_sha256"], EXPECTED_CONTRACT_SHA256, "native authority contract digest")
        _require(authority["github"], github, "native authority GitHub identity")
        _require(authority["producer_source"], contract["surfaces"][surface]["producer"], "native authority producer")
        _require(authority["result_authority"], contract["result_authority"], "native authority result authority")
        _require(authority["status"], "NATIVE_TOOL_OBSERVED_NONCREDITING", "native authority status")
        binary_authority = authority["producer_binary"]
        _require_keys(binary_authority, ("bytes", "sha256"), "native authority binary")
        if _require_int(binary_authority["bytes"], "native authority binary size") <= 0:
            raise CaptureError("native authority binary is empty")
        _require(binary_authority["sha256"], execution["binary_sha256"], "native authority binary digest")
        _require(
            authority["tool_observation"],
            {
                "bytes": len(files["tool-report.txt"]),
                "sha256": _sha256(files["tool-report.txt"]),
                "summary": tool_observation,
            },
            "native authority tool observation",
        )
        _require(execution["overlay_host_driver_sha256"], None, "native overlay boundary")
        _require(execution["preflight_manifest_sha256"], None, "native preflight boundary")
    return {
        "claims": contract["claims"], "contract_id": contract["contract_id"],
        "envelope_sha256": _sha256(envelope), "github": github,
        "raw_sha256": base_review["raw_sha256"],
        "result_authority": contract["result_authority"]["status"],
        "surface": surface, "vector_count": len(contract["vectors"]),
    }


def review_lane(
    repo: Path, artifact: Path, expected_surface: Optional[str] = None,
    expected_head: Optional[str] = None, expected_repository: Optional[str] = None,
    expected_run_id: Optional[str] = None, expected_run_attempt: Optional[str] = None,
) -> Dict[str, Any]:
    contract, _ = _load_contract(repo)
    result = _review_lane_with_contract(Path(repo), contract, artifact, expected_surface)
    github = result["github"]
    if github["head_sha"] != _git_head(Path(repo)):
        raise CaptureError("lane head differs from repository HEAD")
    if expected_head is not None:
        _require(github["head_sha"], expected_head, "expected lane head")
    if expected_repository is not None:
        _require(github["repository"], expected_repository, "expected lane repository")
    if expected_run_id is not None:
        if not POSITIVE_DECIMAL.fullmatch(expected_run_id):
            raise CaptureError("expected run id is invalid")
        _require(github["run_id"], int(expected_run_id), "expected lane run id")
    if expected_run_attempt is not None:
        if not POSITIVE_DECIMAL.fullmatch(expected_run_attempt):
            raise CaptureError("expected run attempt is invalid")
        _require(github["run_attempt"], int(expected_run_attempt), "expected lane run attempt")
    result["status"] = "LANE_VERIFIED_UNREVIEWED_NONCREDITING"
    return result


def review_pair(
    repo: Path, legacy: Path, native: Path, expected_head: str,
    expected_repository: str,
) -> Dict[str, Any]:
    contract, _ = _load_contract(repo)
    legacy_result = _review_lane_with_contract(
        Path(repo), contract, legacy, "legacy-live-ioctl"
    )
    native_result = _review_lane_with_contract(
        Path(repo), contract, native, "native-rust-source-fixture"
    )
    _require(
        legacy_result["github"]["head_sha"],
        native_result["github"]["head_sha"],
        "legacy/native exact commit",
    )
    _require(
        legacy_result["github"]["repository"],
        native_result["github"]["repository"],
        "legacy/native repository",
    )
    _require(legacy_result["raw_sha256"], native_result["raw_sha256"], "legacy/native raw vectors")
    _require(legacy_result["github"]["head_sha"], _git_head(Path(repo)), "pair repository HEAD")
    _require(legacy_result["github"]["head_sha"], expected_head, "pair expected head")
    _require(
        legacy_result["github"]["repository"], expected_repository,
        "pair expected repository",
    )
    return {
        "artifact_pair_validated": True,
        "claims": contract["claims"],
        "contract_id": contract["contract_id"],
        "head_sha": legacy_result["github"]["head_sha"],
        "legacy": legacy_result,
        "native": native_result,
        "result_authority": contract["result_authority"]["status"],
        "status": "CAPTURED_PAIR_UNREVIEWED_NONCREDITING",
        "vector_count": len(contract["vectors"]),
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command")
    check = commands.add_parser("check-contract")
    check.add_argument("--repo", type=Path, default=ROOT)
    preflight = commands.add_parser("preflight-legacy")
    preflight.add_argument("--repo", type=Path, default=ROOT)
    preflight.add_argument("--producer-binary", type=Path, required=True)
    preflight.add_argument("--compiler-report", type=Path, required=True)
    preflight.add_argument("--compiler-output", type=Path, required=True)
    preflight.add_argument("--output-manifest", type=Path, required=True)
    preflight.add_argument("--head", required=True)
    preflight.add_argument("--github-repository", required=True)
    preflight.add_argument("--github-run-id", required=True)
    preflight.add_argument("--github-run-attempt", required=True)
    preflight.add_argument("--github-event-name", required=True)
    preflight.add_argument("--github-ref", required=True)
    preflight.add_argument("--github-sha", required=True)
    preflight.add_argument("--github-workflow-sha", required=True)
    preflight.add_argument("--github-base-sha", required=True)
    finalize = commands.add_parser("finalize-lane")
    finalize.add_argument("--repo", type=Path, default=ROOT)
    finalize.add_argument("--capture-dir", type=Path, required=True)
    finalize.add_argument("--producer-output", type=Path, required=True)
    finalize.add_argument("--producer-log", type=Path, required=True)
    finalize.add_argument("--producer-binary", type=Path, required=True)
    finalize.add_argument("--tool-report", type=Path, required=True)
    finalize.add_argument("--compiler-output", type=Path, required=True)
    finalize.add_argument("--output-dir", type=Path, required=True)
    finalize.add_argument("--surface", required=True)
    finalize.add_argument("--head", required=True)
    finalize.add_argument("--github-repository", required=True)
    finalize.add_argument("--github-run-id", required=True)
    finalize.add_argument("--github-run-attempt", required=True)
    finalize.add_argument("--github-event-name", required=True)
    finalize.add_argument("--github-ref", required=True)
    finalize.add_argument("--github-sha", required=True)
    finalize.add_argument("--github-workflow-sha", required=True)
    finalize.add_argument("--github-base-sha", required=True)
    legacy = commands.add_parser("finalize-legacy-observation")
    legacy.add_argument("--repo", type=Path, default=ROOT)
    legacy.add_argument("--observation-dir", type=Path, required=True)
    legacy.add_argument("--output-dir", type=Path, required=True)
    legacy.add_argument("--expected-head", required=True)
    legacy.add_argument("--expected-repository", required=True)
    legacy.add_argument("--expected-run-id", required=True)
    legacy.add_argument("--expected-run-attempt", required=True)
    legacy.add_argument("--expected-event-name", required=True)
    legacy.add_argument("--expected-ref", required=True)
    legacy.add_argument("--expected-github-sha", required=True)
    legacy.add_argument("--expected-workflow-sha", required=True)
    legacy.add_argument("--expected-base-sha", required=True)
    verify = commands.add_parser("verify-lane")
    verify.add_argument("--repo", type=Path, default=ROOT)
    verify.add_argument("--artifact", type=Path, required=True)
    verify.add_argument("--surface", required=True)
    verify.add_argument("--expected-head", required=True)
    verify.add_argument("--expected-repository", required=True)
    verify.add_argument("--expected-run-id", required=True)
    verify.add_argument("--expected-run-attempt", required=True)
    pair = commands.add_parser("review-pair")
    pair.add_argument("--repo", type=Path, default=ROOT)
    pair.add_argument("--legacy", type=Path, required=True)
    pair.add_argument("--native", type=Path, required=True)
    pair.add_argument("--expected-head", required=True)
    pair.add_argument("--expected-repository", required=True)
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = _parser()
    arguments = parser.parse_args(argv)
    try:
        if arguments.command == "check-contract":
            result = validate_contract(arguments.repo)
        elif arguments.command == "preflight-legacy":
            result = preflight_legacy(
                arguments.repo, arguments.producer_binary, arguments.compiler_report,
                arguments.compiler_output,
                arguments.output_manifest, arguments.head, arguments.github_repository,
                arguments.github_run_id, arguments.github_run_attempt,
                arguments.github_event_name, arguments.github_ref,
                arguments.github_sha, arguments.github_workflow_sha,
                arguments.github_base_sha,
            )
        elif arguments.command == "finalize-lane":
            result = finalize_lane(
                arguments.repo, arguments.capture_dir, arguments.producer_output,
                arguments.producer_log, arguments.producer_binary, arguments.tool_report,
                arguments.compiler_output, arguments.output_dir, arguments.surface, arguments.head,
                arguments.github_repository, arguments.github_run_id,
                arguments.github_run_attempt,
                arguments.github_event_name, arguments.github_ref,
                arguments.github_sha, arguments.github_workflow_sha,
                arguments.github_base_sha,
            )
        elif arguments.command == "finalize-legacy-observation":
            result = finalize_legacy_observation(
                arguments.repo, arguments.observation_dir, arguments.output_dir,
                arguments.expected_head, arguments.expected_repository,
                arguments.expected_run_id, arguments.expected_run_attempt,
                arguments.expected_event_name, arguments.expected_ref,
                arguments.expected_github_sha, arguments.expected_workflow_sha,
                arguments.expected_base_sha,
            )
        elif arguments.command == "verify-lane":
            result = review_lane(
                arguments.repo, arguments.artifact, arguments.surface,
                arguments.expected_head, arguments.expected_repository,
                arguments.expected_run_id, arguments.expected_run_attempt,
            )
        elif arguments.command == "review-pair":
            result = review_pair(
                arguments.repo, arguments.legacy, arguments.native,
                arguments.expected_head, arguments.expected_repository,
            )
        else:
            parser.error("a command is required")
            return 2
    except CaptureError as error:
        print("fp0006 runtime-capture integration error: {0}".format(error), file=sys.stderr)
        return 1
    print(_canonical_json(result).decode("ascii"), end="")
    return 0


if __name__ == "__main__":
    sys.exit(main())
