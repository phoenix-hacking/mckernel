#!/usr/bin/env python3
"""Capture fail-closed, run-bound RK-001 source provenance evidence.

This checkpoint verifies the four replay/signature classes already named by
``host-kernel/rocky/source-lock.json``.  It intentionally does not update that
lock or claim RK-001 credit: the path-by-path license inventory remains a hard
blocker and captured CI output still needs review before it can be committed.
"""

import argparse
import base64
import gzip
import hashlib
import json
import os
import platform
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path, PurePosixPath
from typing import Any, BinaryIO, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple


import rocky_kernel_source_lock as source_lock


SOURCE_LOCK_PATH = Path("host-kernel/rocky/source-lock.json")
PATCH_SERIES_PATH = Path("host-kernel/rocky/patches/series.json")
SOURCE_LOCK_VALIDATOR_PATH = Path("scripts/rocky_kernel_source_lock.py")
CAPTURE_SCRIPT_PATH = Path("scripts/rocky_kernel_source_evidence.py")
WORKFLOW_PATH = Path(".github/workflows/rocky-kernel-source-evidence.yml")
WORKFLOW_TRIGGER_PATHS = (
    ".github/workflows/rocky-kernel-source-evidence.yml",
    "host-kernel/rocky/source-lock.json",
    "host-kernel/rocky/patches/**",
    "host-kernel/rocky/patches/series.json",
    "host-kernel/kbuild/stage-manifest.json",
    "host-kernel/native-rust/ihk.rs",
    "host-kernel/native-rust/ihk-page-allocator-contract-v1.json",
    "host-kernel/native-rust/ihk-page-owner-registry-contract-v1.json",
    "host-kernel/native-rust/page_allocator.rs",
    "host-kernel/native-rust/page_owner_registry.rs",
    "scripts/ihk_page_allocator_check.py",
    "scripts/ihk_page_owner_registry_check.py",
    "scripts/tests/fixtures/ihk_page_allocator_compile.rs",
    "scripts/tests/fixtures/ihk_page_allocator_lifetime_compile_fail.rs",
    "scripts/tests/fixtures/ihk_page_allocator_must_use_compile_fail.rs",
    "scripts/tests/fixtures/ihk_page_owner_registry_compile.rs",
    "scripts/tests/fixtures/ihk_page_owner_registry_lifetime_compile_fail.rs",
    "scripts/tests/fixtures/ihk_page_owner_registry_sync_compile_fail.rs",
    "scripts/tests/test_ihk_page_allocator_check.py",
    "scripts/tests/test_ihk_page_owner_registry_check.py",
    "scripts/rocky_kernel_source_evidence.py",
    "scripts/rocky_kernel_license_inventory.py",
    "scripts/rocky_kernel_source_lock.py",
)

CONTAINER_IMAGE = (
    "rockylinux/rockylinux:10.2@"
    "sha256:e372170ca8630f0f03e9b70fdd0bf4a3ce3426b0de7cdba615f06337389de176"
)
CONTAINER_MANIFEST_DIGEST = (
    "sha256:e372170ca8630f0f03e9b70fdd0bf4a3ce3426b0de7cdba615f06337389de176"
)
CONTAINER_TAG_INDEX_DIGEST = (
    "sha256:827d37bc128288ccf160ee318bb3cb92d591164cb217e92f8bc61e3982ae1834"
)
CONTAINER_PLATFORM = "linux/amd64"
CHECKPOINT_ID = "rk-001-source-evidence-capture-v1"
SCHEMA_VERSION = 1

MAX_JSON_BYTES = 1024 * 1024
MAX_SMALL_DOWNLOAD_BYTES = 8 * 1024 * 1024
HEX_SHA256 = re.compile(r"^[0-9a-f]{64}$")
HEX_SHA1 = re.compile(r"^[0-9a-f]{40}$")
GITHUB_REPOSITORY = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
RPM_HEADER_SIGNATURE_LEGACY = re.compile(
    r"Header(?: V[0-9]+)? ([A-Za-z0-9-]+)/(SHA[0-9-]+) Signature, "
    r"key ID ([0-9A-Fa-f]{8,40}): OK",
    re.IGNORECASE,
)
RPM_HEADER_SIGNATURE_OPENPGP = re.compile(
    r"^\s*Header\s+OpenPGP\s+V[0-9]+\s+"
    r"([A-Za-z0-9-]+)/(SHA[0-9-]+),\s+key\s+"
    r"(fingerprint|ID)\s+([0-9A-Fa-f]{8,40})\s+signature:\s+OK\s*$",
    re.IGNORECASE | re.MULTILINE,
)


class EvidenceError(RuntimeError):
    """Raised when evidence cannot be captured without weakening the lock."""


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> Tuple[int, str]:
    digest = hashlib.sha256()
    size = 0
    try:
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                size += len(chunk)
                digest.update(chunk)
    except OSError as exc:
        raise EvidenceError("cannot hash {}: {}".format(path, exc)) from exc
    return size, digest.hexdigest()


def _reject_duplicate_pairs(pairs: Sequence[Tuple[str, Any]]) -> Dict[str, Any]:
    result = {}  # type: Dict[str, Any]
    for key, value in pairs:
        if key in result:
            raise EvidenceError("duplicate JSON key: {!r}".format(key))
        result[key] = value
    return result


def strict_json_bytes(data: bytes, label: str) -> Dict[str, Any]:
    if len(data) > MAX_JSON_BYTES:
        raise EvidenceError("{} exceeds the JSON size limit".format(label))
    try:
        value = json.loads(data.decode("utf-8"), object_pairs_hook=_reject_duplicate_pairs)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise EvidenceError("cannot parse {}: {}".format(label, exc)) from exc
    if not isinstance(value, dict):
        raise EvidenceError("{} must contain one JSON object".format(label))
    return value


def canonical_json_bytes(value: Mapping[str, Any]) -> bytes:
    try:
        text = json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        )
    except (TypeError, ValueError) as exc:
        raise EvidenceError("evidence is not canonical-JSON serializable: {}".format(exc))
    return (text + "\n").encode("ascii")


def within(root: Path, candidate: Path) -> bool:
    try:
        common = os.path.commonpath((str(root), str(candidate)))
    except ValueError:
        return False
    return Path(common) == root


def repository_file(repo: Path, relative: Path) -> Path:
    if relative.is_absolute() or any(part in ("", ".", "..") for part in relative.parts):
        raise EvidenceError("repository path is not normalized: {}".format(relative))
    root = repo.resolve()
    requested = root.joinpath(*relative.parts)
    resolved = requested.resolve()
    if not within(root, resolved):
        raise EvidenceError("repository path escapes the checkout: {}".format(relative))
    if requested != resolved or requested.is_symlink() or not requested.is_file():
        raise EvidenceError(
            "repository input must be a regular file without symlink traversal: {}".format(
                relative
            )
        )
    return requested


def read_repository_json(repo: Path, relative: Path) -> Tuple[Dict[str, Any], bytes]:
    path = repository_file(repo, relative)
    try:
        data = path.read_bytes()
    except OSError as exc:
        raise EvidenceError("cannot read {}: {}".format(relative, exc)) from exc
    return strict_json_bytes(data, relative.as_posix()), data


def run_command(
    arguments: Sequence[str],
    cwd: Optional[Path] = None,
    env: Optional[Mapping[str, str]] = None,
) -> bytes:
    if not arguments or not all(isinstance(item, str) and item for item in arguments):
        raise EvidenceError("invalid command arguments")
    try:
        completed = subprocess.run(
            list(arguments),
            cwd=str(cwd) if cwd is not None else None,
            env=dict(env) if env is not None else None,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except OSError as exc:
        raise EvidenceError("command is unavailable: {}: {}".format(arguments[0], exc)) from exc
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr.decode("utf-8", errors="replace").strip()
        raise EvidenceError(
            "command failed ({}): {}".format(" ".join(arguments), stderr)
        ) from exc
    return completed.stdout


def load_locked_inputs(
    repo: Path,
) -> Tuple[Dict[str, Any], Dict[str, Any], bytes, bytes, List[str]]:
    lock, lock_bytes = read_repository_json(repo, SOURCE_LOCK_PATH)
    series, series_bytes = read_repository_json(repo, PATCH_SERIES_PATH)
    try:
        blockers = source_lock.validate_loaded_manifests(
            lock, series, series_bytes, repo.resolve()
        )
    except source_lock.SourceLockError as exc:
        raise EvidenceError("source-lock validation failed: {}".format(exc)) from exc
    if lock.get("gate", {}).get("credit_eligible") is not False:
        raise EvidenceError("capture checkpoint must not start from an RK-001 credit claim")
    inventory = lock.get("licenses", {}).get("inventory", {})
    if inventory.get("complete") is not False or inventory.get("status") != "required-missing":
        raise EvidenceError("capture checkpoint requires the license inventory blocker")
    if not any(item.startswith("license_inventory:") for item in blockers):
        raise EvidenceError("RK-001 license-inventory blocker unexpectedly disappeared")
    return lock, series, lock_bytes, series_bytes, blockers


def workflow_scalar(raw: str) -> str:
    """Return one plain workflow scalar without letting comments attest it."""
    value = raw.strip()
    quote = None  # type: Optional[str]
    escaped = False
    for index, character in enumerate(value):
        if quote == '"':
            if escaped:
                escaped = False
            elif character == "\\":
                escaped = True
            elif character == quote:
                quote = None
        elif quote == "'":
            if character == quote:
                quote = None
        elif character in ("'", '"'):
            quote = character
        elif character == "#" and (index == 0 or value[index - 1].isspace()):
            return value[:index].rstrip()
    if quote is not None:
        raise EvidenceError("workflow scalar contains an unterminated quote")
    return value


def workflow_mapping_matches(
    lines: Sequence[str], indent: int, key: str
) -> List[Tuple[int, str]]:
    pattern = re.compile(
        r"^" + (" " * indent) + re.escape(key) + r":(?:[ \t]*(.*))?$"
    )
    matches = []
    for index, line in enumerate(lines):
        match = pattern.fullmatch(line)
        if match is not None:
            matches.append((index, workflow_scalar(match.group(1) or "")))
    return matches


def require_workflow_mapping(
    lines: Sequence[str], indent: int, key: str, expected: str, label: str
) -> int:
    matches = workflow_mapping_matches(lines, indent, key)
    if len(matches) != 1 or matches[0][1] != expected:
        raise EvidenceError(
            "{} must map {} exactly once to {!r}".format(label, key, expected)
        )
    return matches[0][0]


def require_workflow_key_set(
    lines: Sequence[str], indent: int, expected: Iterable[str], label: str
) -> None:
    pattern = re.compile(
        r"^" + (" " * indent) + r"([A-Za-z0-9_-]+):(?:[ \t]*(.*))?$"
    )
    keys = []
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        leading = len(line) - len(line.lstrip(" "))
        if leading != indent:
            continue
        match = pattern.fullmatch(line)
        if match is None:
            raise EvidenceError("{} contains malformed mapping syntax".format(label))
        workflow_scalar(match.group(2) or "")
        keys.append(match.group(1))
    if len(set(keys)) != len(keys) or set(keys) != set(expected):
        raise EvidenceError("{} mapping keys changed or are duplicated".format(label))


def workflow_mapping_block(
    lines: Sequence[str], indent: int, key: str, expected: str, label: str
) -> List[str]:
    start = require_workflow_mapping(lines, indent, key, expected, label) + 1
    end = len(lines)
    for index in range(start, len(lines)):
        line = lines[index]
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        leading = len(line) - len(line.lstrip(" "))
        if leading <= indent:
            end = index
            break
    return list(lines[start:end])


def require_workflow_empty_block(lines: Sequence[str], label: str) -> None:
    if any(line.strip() and not line.strip().startswith("#") for line in lines):
        raise EvidenceError("{} must remain empty".format(label))


def require_workflow_sequence(
    lines: Sequence[str], indent: int, key: str, expected: Iterable[str], label: str
) -> None:
    block = workflow_mapping_block(lines, indent, key, "", label)
    item = re.compile(r"^" + (" " * (indent + 2)) + r"-[ \t]+(.+)$")
    values = []
    for line in block:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        leading = len(line) - len(line.lstrip(" "))
        if leading != indent + 2:
            raise EvidenceError("{} contains invalid sequence indentation".format(label))
        match = item.fullmatch(line)
        if match is None:
            raise EvidenceError("{} contains a malformed sequence item".format(label))
        value = workflow_scalar(match.group(1))
        if not value:
            raise EvidenceError("{} contains an empty sequence item".format(label))
        values.append(value)
    if len(set(values)) != len(values) or set(values) != set(expected):
        raise EvidenceError("{} sequence set changed or is duplicated".format(label))


def validate_workflow_triggers(lines: Sequence[str]) -> None:
    triggers = workflow_mapping_block(lines, 0, "on", "", "workflow triggers")
    require_workflow_key_set(
        triggers,
        2,
        {"workflow_dispatch", "push", "pull_request"},
        "workflow triggers",
    )
    dispatch = workflow_mapping_block(
        triggers, 2, "workflow_dispatch", "", "workflow dispatch trigger"
    )
    require_workflow_empty_block(dispatch, "workflow dispatch trigger")
    for trigger, branch in (
        ("push", "[codex/rocky-rust-validation]"),
        ("pull_request", "[development]"),
    ):
        block = workflow_mapping_block(
            triggers, 2, trigger, "", "{} trigger".format(trigger)
        )
        require_workflow_key_set(
            block, 4, {"branches", "paths"}, "{} trigger".format(trigger)
        )
        require_workflow_mapping(
            block, 4, "branches", branch, "{} trigger".format(trigger)
        )
        require_workflow_sequence(
            block,
            4,
            "paths",
            WORKFLOW_TRIGGER_PATHS,
            "{} trigger paths".format(trigger),
        )


def workflow_jobs(lines: Sequence[str]) -> Dict[str, List[str]]:
    job_lines = workflow_mapping_block(lines, 0, "jobs", "", "workflow jobs")
    header = re.compile(r"^  ([A-Za-z0-9_-]+):(?:[ \t]*(.*))?$")
    starts = []  # type: List[Tuple[int, str]]
    for index, line in enumerate(job_lines):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        leading = len(line) - len(line.lstrip(" "))
        if leading != 2:
            continue
        match = header.fullmatch(line)
        if match is None or workflow_scalar(match.group(2) or ""):
            raise EvidenceError("workflow contains a malformed job declaration")
        starts.append((index, match.group(1)))
    if len({name for _, name in starts}) != len(starts):
        raise EvidenceError("workflow contains duplicate job declarations")
    jobs = {}  # type: Dict[str, List[str]]
    for offset, (start, name) in enumerate(starts):
        end = starts[offset + 1][0] if offset + 1 < len(starts) else len(job_lines)
        jobs[name] = list(job_lines[start + 1 : end])
    return jobs


def workflow_steps(job: Sequence[str], label: str) -> Dict[str, List[str]]:
    step_lines = workflow_mapping_block(job, 4, "steps", "", label + " steps")
    header = re.compile(r"^      - name:(?:[ \t]*(.*))?$")
    starts = []  # type: List[Tuple[int, str]]
    for index, line in enumerate(step_lines):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        leading = len(line) - len(line.lstrip(" "))
        if leading != 6:
            continue
        match = header.fullmatch(line)
        if match is None:
            raise EvidenceError("{} contains an unnamed or malformed step".format(label))
        name = workflow_scalar(match.group(1) or "")
        if not name:
            raise EvidenceError("{} contains an empty step name".format(label))
        starts.append((index, name))
    if len({name for _, name in starts}) != len(starts):
        raise EvidenceError("{} contains duplicate step names".format(label))
    steps = {}  # type: Dict[str, List[str]]
    for offset, (start, name) in enumerate(starts):
        end = starts[offset + 1][0] if offset + 1 < len(starts) else len(step_lines)
        steps[name] = list(step_lines[start + 1 : end])
    return steps


def workflow_run_script(step: Sequence[str], label: str) -> str:
    block = workflow_mapping_block(step, 8, "run", "|", label + " run block")
    script = []
    for line in block:
        if not line:
            script.append("")
        elif line.startswith("          "):
            script.append(line[10:])
        elif line.strip().startswith("#"):
            script.append("")
        else:
            raise EvidenceError("{} run block has invalid indentation".format(label))
    return "\n".join(script)


def workflow_shell_commands(script: str, label: str) -> List[List[str]]:
    commands = []  # type: List[List[str]]
    continued = ""
    for raw in script.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("#"):
            if continued:
                raise EvidenceError(
                    "{} places a comment inside a continued command".format(label)
                )
            continue
        if line.endswith("\\"):
            fragment = line[:-1].rstrip()
            if not fragment:
                raise EvidenceError("{} contains an empty continuation".format(label))
            continued += fragment + " "
            continue
        continued += line
        try:
            tokens = shlex.split(continued, comments=True, posix=True)
        except ValueError as exc:
            raise EvidenceError("{} contains malformed shell: {}".format(label, exc)) from exc
        if tokens:
            commands.append(tokens)
        continued = ""
    if continued:
        raise EvidenceError("{} ends inside a continued command".format(label))
    return commands


def validate_workflow_job_runtime(job: Sequence[str], label: str) -> None:
    require_workflow_key_set(
        job,
        4,
        {"name", "runs-on", "timeout-minutes", "container", "defaults", "steps"},
        label,
    )
    require_workflow_mapping(job, 4, "runs-on", "ubuntu-24.04", label)
    require_workflow_mapping(job, 4, "timeout-minutes", "90", label)
    container = workflow_mapping_block(job, 4, "container", "", label + " container")
    require_workflow_key_set(container, 6, {"image"}, label + " container")
    require_workflow_mapping(container, 6, "image", CONTAINER_IMAGE, label + " container")
    defaults = workflow_mapping_block(job, 4, "defaults", "", label + " defaults")
    require_workflow_key_set(defaults, 6, {"run"}, label + " defaults")
    run_defaults = workflow_mapping_block(defaults, 6, "run", "", label + " defaults")
    require_workflow_key_set(run_defaults, 8, {"shell"}, label + " defaults")
    require_workflow_mapping(run_defaults, 8, "shell", "bash", label + " defaults")


def validate_checkout_step(step: Sequence[str], label: str) -> None:
    require_workflow_key_set(step, 8, {"uses", "with"}, label)
    require_workflow_mapping(
        step,
        8,
        "uses",
        "actions/checkout@11d5960a326750d5838078e36cf38b85af677262",
        label,
    )
    values = workflow_mapping_block(step, 8, "with", "", label + " inputs")
    require_workflow_key_set(
        values,
        10,
        {"ref", "fetch-depth", "persist-credentials", "submodules"},
        label + " inputs",
    )
    require_workflow_mapping(values, 10, "ref", "${{ env.EXPECTED_HEAD_SHA }}", label)
    require_workflow_mapping(values, 10, "fetch-depth", "1", label)
    require_workflow_mapping(values, 10, "persist-credentials", "false", label)
    require_workflow_mapping(values, 10, "submodules", "recursive", label)


def validate_upload_step(
    step: Sequence[str], label: str, artifact_name: str, artifact_path: str
) -> None:
    require_workflow_key_set(step, 8, {"uses", "with"}, label)
    require_workflow_mapping(
        step,
        8,
        "uses",
        "actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02",
        label,
    )
    values = workflow_mapping_block(step, 8, "with", "", label + " inputs")
    require_workflow_key_set(
        values,
        10,
        {"name", "path", "if-no-files-found", "retention-days"},
        label + " inputs",
    )
    require_workflow_mapping(values, 10, "name", artifact_name, label)
    require_workflow_mapping(values, 10, "path", artifact_path, label)
    require_workflow_mapping(values, 10, "if-no-files-found", "error", label)
    require_workflow_mapping(values, 10, "retention-days", "30", label)


def validate_step_environment(
    step: Sequence[str], expected: Mapping[str, str], label: str
) -> None:
    values = workflow_mapping_block(step, 8, "env", "", label + " environment")
    require_workflow_key_set(values, 10, set(expected), label + " environment")
    for key, value in expected.items():
        require_workflow_mapping(values, 10, key, value, label + " environment")


def validate_workflow_contract(repo: Path) -> bytes:
    workflow = repository_file(repo, WORKFLOW_PATH).read_bytes()
    try:
        text = workflow.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise EvidenceError("evidence workflow is not UTF-8") from exc
    lines = text.splitlines()
    require_workflow_key_set(
        lines,
        0,
        {"name", "on", "permissions", "env", "jobs"},
        "workflow top level",
    )
    require_workflow_mapping(
        lines,
        0,
        "name",
        "Rocky 10.2 kernel source evidence",
        "workflow top level",
    )
    validate_workflow_triggers(lines)
    permissions = workflow_mapping_block(
        lines, 0, "permissions", "", "workflow permissions"
    )
    require_workflow_key_set(permissions, 2, {"contents"}, "workflow permissions")
    require_workflow_mapping(permissions, 2, "contents", "read", "workflow permissions")
    environment = workflow_mapping_block(lines, 0, "env", "", "workflow environment")
    require_workflow_key_set(
        environment,
        2,
        {"RK001_CONTAINER_IMAGE", "EXPECTED_HEAD_SHA"},
        "workflow environment",
    )
    require_workflow_mapping(
        environment, 2, "RK001_CONTAINER_IMAGE", CONTAINER_IMAGE, "workflow environment"
    )
    require_workflow_mapping(
        environment,
        2,
        "EXPECTED_HEAD_SHA",
        "${{ github.event.pull_request.head.sha || github.sha }}",
        "workflow environment",
    )
    jobs = workflow_jobs(lines)
    if set(jobs) != {"capture", "license-inventory"}:
        raise EvidenceError("workflow must contain only distinct source and license jobs")
    capture_job = jobs["capture"]
    license_job = jobs["license-inventory"]
    validate_workflow_job_runtime(capture_job, "source capture job")
    validate_workflow_job_runtime(license_job, "license inventory job")

    for forbidden in ("needs", "if", "continue-on-error"):
        if workflow_mapping_matches(license_job, 4, forbidden):
            raise EvidenceError(
                "license inventory job cannot declare {}".format(forbidden)
            )

    capture_steps = workflow_steps(capture_job, "source capture job")
    expected_capture_steps = {
        "Install required verification tools",
        "Check out the exact candidate commit",
        "Verify capture contract without claiming gate credit",
        "Capture exact RK-001 replay evidence",
        "Upload canonical source evidence",
    }
    if set(capture_steps) != expected_capture_steps:
        raise EvidenceError("source capture job step set changed")
    for step_name in (
        "Install required verification tools",
        "Verify capture contract without claiming gate credit",
    ):
        require_workflow_key_set(capture_steps[step_name], 8, {"run"}, step_name)
    require_workflow_key_set(
        capture_steps["Capture exact RK-001 replay evidence"],
        8,
        {"env", "run"},
        "source evidence capture step",
    )
    validate_step_environment(
        capture_steps["Capture exact RK-001 replay evidence"],
        {"EVIDENCE_DIR": "${{ runner.temp }}/rk001-source-evidence"},
        "source evidence capture step",
    )
    validate_checkout_step(
        capture_steps["Check out the exact candidate commit"], "source checkout step"
    )
    validate_upload_step(
        capture_steps["Upload canonical source evidence"],
        "source upload step",
        "rk001-source-evidence-${{ github.run_id }}-${{ github.run_attempt }}",
        "${{ runner.temp }}/rk001-source-evidence/",
    )
    source_capture_commands = workflow_shell_commands(
        workflow_run_script(
            capture_steps["Capture exact RK-001 replay evidence"],
            "source evidence capture step",
        ),
        "source evidence capture step",
    )
    expected_source_capture_commands = [
        ["set", "-euo", "pipefail"],
        [
            "python3",
            "scripts/rocky_kernel_source_evidence.py",
            "--repo",
            "$GITHUB_WORKSPACE",
            "--run",
            "--output-dir",
            "$EVIDENCE_DIR",
            "--github-head-sha",
            "$EXPECTED_HEAD_SHA",
            "--github-run-id",
            "$GITHUB_RUN_ID",
            "--github-run-attempt",
            "$GITHUB_RUN_ATTEMPT",
            "--github-repository",
            "$GITHUB_REPOSITORY",
            "--container-image",
            "$RK001_CONTAINER_IMAGE",
        ],
        ["("],
        ["cd", "$EVIDENCE_DIR"],
        ["sha256sum", "--check", "--strict", "SHA256SUMS"],
        [")"],
    ]
    if source_capture_commands != expected_source_capture_commands:
        raise EvidenceError("source capture commands or run bindings changed")

    license_steps = workflow_steps(license_job, "license inventory job")
    expected_license_steps = {
        "Install exact license-capture tools",
        "Check out the exact candidate commit for license capture",
        "Verify source and license contracts without claiming gate credit",
        "Capture exhaustive source and license inventory",
        "Upload exhaustive license inventory capture",
    }
    if set(license_steps) != expected_license_steps:
        raise EvidenceError("license inventory job step set changed")
    for step_name in (
        "Install exact license-capture tools",
        "Verify source and license contracts without claiming gate credit",
    ):
        require_workflow_key_set(license_steps[step_name], 8, {"run"}, step_name)
    require_workflow_key_set(
        license_steps["Capture exhaustive source and license inventory"],
        8,
        {"env", "run"},
        "license capture step",
    )
    validate_step_environment(
        license_steps["Capture exhaustive source and license inventory"],
        {
            "LICENSE_CACHE_ROOT": "${{ runner.temp }}/rk001-license-cache",
            "LICENSE_EVIDENCE_DIR": "${{ runner.temp }}/rk001-license-inventory",
        },
        "license capture step",
    )
    for step_name, step in license_steps.items():
        for forbidden in ("if", "continue-on-error"):
            if workflow_mapping_matches(step, 8, forbidden):
                raise EvidenceError(
                    "license step {!r} cannot declare {}".format(step_name, forbidden)
                )
    validate_checkout_step(
        license_steps["Check out the exact candidate commit for license capture"],
        "license checkout step",
    )
    validate_upload_step(
        license_steps["Upload exhaustive license inventory capture"],
        "license upload step",
        "rk001-license-inventory-${{ github.run_id }}-${{ github.run_attempt }}",
        "${{ runner.temp }}/rk001-license-inventory/",
    )

    install_commands = workflow_shell_commands(
        workflow_run_script(
            license_steps["Install exact license-capture tools"],
            "license tool install step",
        ),
        "license tool install step",
    )
    expected_install_commands = [
        ["set", "-euo", "pipefail"],
        ["test", "$(uname -m)", "=", "x86_64"],
        [".", "/etc/os-release"],
        ["test", "$ID", "=", "rocky"],
        ["test", "$VERSION_ID", "=", "10.2"],
        [
            "dnf",
            "-y",
            "--setopt=install_weak_deps=False",
            "install",
            "cpio",
            "git-core",
            "gnupg2",
            "gzip",
            "python3",
            "rpm",
            "xz",
        ],
        ["dnf", "clean", "all"],
        [
            "for",
            "tool",
            "in",
            "cpio",
            "git",
            "gpg",
            "gpgv",
            "gzip",
            "python3",
            "rpm",
            "rpm2cpio",
            "rpmkeys",
            "sha256sum",
            "xz;",
            "do",
        ],
        ["command", "-v", "$tool", ">/dev/null"],
        ["done"],
    ]
    if install_commands != expected_install_commands:
        raise EvidenceError("license tool installation or runtime checks changed")

    verify_commands = workflow_shell_commands(
        workflow_run_script(
            license_steps["Verify source and license contracts without claiming gate credit"],
            "license contract step",
        ),
        "license contract step",
    )
    expected_verify_commands = [
        ["set", "-euo", "pipefail"],
        [
            "test",
            "$(git -c safe.directory=$GITHUB_WORKSPACE rev-parse HEAD)",
            "=",
            "$EXPECTED_HEAD_SHA",
        ],
        ["test", "$GITHUB_REPOSITORY", "=", "phoenix-hacking/mckernel"],
        [
            "python3",
            "scripts/rocky_kernel_source_evidence.py",
            "--repo",
            "$GITHUB_WORKSPACE",
            "--check",
        ],
        [
            "python3",
            "scripts/rocky_kernel_license_inventory.py",
            "--repo",
            "$GITHUB_WORKSPACE",
            "--check",
        ],
    ]
    if verify_commands != expected_verify_commands:
        raise EvidenceError("license contract step commands changed or became conditional")

    capture_commands = workflow_shell_commands(
        workflow_run_script(
            license_steps["Capture exhaustive source and license inventory"],
            "license capture step",
        ),
        "license capture step",
    )
    expected_capture_commands = [
        ["set", "-euo", "pipefail"],
        [
            "python3",
            "scripts/rocky_kernel_license_inventory.py",
            "--repo",
            "$GITHUB_WORKSPACE",
            "--capture",
            "--cache-root",
            "$LICENSE_CACHE_ROOT",
            "--output-dir",
            "$LICENSE_EVIDENCE_DIR",
            "--github-head-sha",
            "$EXPECTED_HEAD_SHA",
            "--github-run-id",
            "$GITHUB_RUN_ID",
            "--github-run-attempt",
            "$GITHUB_RUN_ATTEMPT",
            "--github-repository",
            "$GITHUB_REPOSITORY",
            "--container-image",
            "$RK001_CONTAINER_IMAGE",
        ],
        [
            "python3",
            "scripts/rocky_kernel_license_inventory.py",
            "--repo",
            "$GITHUB_WORKSPACE",
            "--verify-capture",
            "$LICENSE_EVIDENCE_DIR",
        ],
        ["("],
        ["cd", "$LICENSE_EVIDENCE_DIR"],
        ["sha256sum", "--check", "--strict", "SHA256SUMS"],
        [")"],
    ]
    if capture_commands != expected_capture_commands:
        raise EvidenceError("license capture commands or run bindings changed")
    return workflow


def check_repository(repo: Path) -> Tuple[Dict[str, Any], Dict[str, Any], List[str]]:
    lock, series, _, _, blockers = load_locked_inputs(repo)
    validate_workflow_contract(repo)
    repository_file(repo, SOURCE_LOCK_VALIDATOR_PATH)
    repository_file(repo, CAPTURE_SCRIPT_PATH)
    return lock, series, blockers


def validate_run_identity(
    head_sha: str,
    run_id: str,
    run_attempt: str,
    github_repository: str,
    container_image: str,
) -> Dict[str, Any]:
    if not HEX_SHA1.fullmatch(head_sha):
        raise EvidenceError("GitHub head SHA must be exactly 40 lowercase hex characters")
    if not run_id.isdigit() or int(run_id) < 1:
        raise EvidenceError("GitHub run ID must be a positive decimal integer")
    if not run_attempt.isdigit() or int(run_attempt) < 1:
        raise EvidenceError("GitHub run attempt must be a positive decimal integer")
    if not GITHUB_REPOSITORY.fullmatch(github_repository):
        raise EvidenceError("GitHub repository must have an owner/name identity")
    if container_image != CONTAINER_IMAGE:
        raise EvidenceError("runtime container identity differs from the workflow lock")
    return {
        "head_sha": head_sha,
        "repository": github_repository,
        "run_attempt": int(run_attempt),
        "run_id": int(run_id),
    }


def committed_file_identity(repo: Path, head_sha: str, relative: Path) -> Dict[str, Any]:
    path = repository_file(repo, relative)
    filesystem_bytes = path.read_bytes()
    committed_bytes = run_command(
        [
            "git",
            "-c",
            "safe.directory={}".format(repo.resolve()),
            "show",
            "{}:{}".format(head_sha, relative.as_posix()),
        ],
        cwd=repo,
    )
    if filesystem_bytes != committed_bytes:
        raise EvidenceError("checkout bytes differ from {}:{}".format(head_sha, relative))
    return {
        "path": relative.as_posix(),
        "sha256": sha256_bytes(filesystem_bytes),
        "size": len(filesystem_bytes),
    }


def parse_os_release(data: bytes) -> Dict[str, str]:
    try:
        lines = data.decode("utf-8").splitlines()
    except UnicodeDecodeError as exc:
        raise EvidenceError("/etc/os-release is not UTF-8") from exc
    values = {}  # type: Dict[str, str]
    for line in lines:
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            raise EvidenceError("malformed /etc/os-release line")
        key, raw = line.split("=", 1)
        if key in values:
            raise EvidenceError("duplicate /etc/os-release field: {}".format(key))
        try:
            parsed = shlex.split(raw, posix=True)
        except ValueError as exc:
            raise EvidenceError("malformed /etc/os-release value") from exc
        if len(parsed) != 1:
            raise EvidenceError("ambiguous /etc/os-release value")
        values[key] = parsed[0]
    if values.get("ID") != "rocky" or values.get("VERSION_ID") != "10.2":
        raise EvidenceError("runtime is not Rocky Linux 10.2")
    return {"id": values["ID"], "version_id": values["VERSION_ID"]}


def capture_runtime_environment() -> Dict[str, Any]:
    required_tools = ("git", "gpg", "gpgv", "gzip", "python3", "rpm", "rpmkeys")
    for tool in required_tools:
        if shutil.which(tool) is None:
            raise EvidenceError("required evidence tool is missing: {}".format(tool))
    machine = platform.machine()
    if machine != "x86_64" or sys.maxsize <= 2 ** 32:
        raise EvidenceError("runtime is not a 64-bit x86_64 environment")
    os_release = parse_os_release(Path("/etc/os-release").read_bytes())
    version_commands = {
        "git": ["git", "--version"],
        "gpg": ["gpg", "--version"],
        "gpgv": ["gpgv", "--version"],
        "gzip": ["gzip", "--version"],
        "python": ["python3", "--version"],
        "rpm": ["rpm", "--version"],
        "rpmkeys": ["rpmkeys", "--version"],
    }
    versions = {}
    for name in sorted(version_commands):
        output = run_command(version_commands[name]).decode("utf-8", errors="strict")
        first_line = output.splitlines()[0].strip() if output.splitlines() else ""
        if not first_line:
            raise EvidenceError("{} did not report a version".format(name))
        versions[name] = first_line
    packages_raw = run_command(
        [
            "rpm",
            "-q",
            "--qf",
            "%{NAME}-%{EPOCHNUM}:%{VERSION}-%{RELEASE}.%{ARCH}\\n",
            "coreutils-single",
            "git-core",
            "gnupg2",
            "gzip",
            "python3",
            "rpm",
        ]
    ).decode("utf-8", errors="strict")
    packages = sorted(item for item in packages_raw.splitlines() if item)
    if len(packages) != 6 or len(set(packages)) != 6:
        raise EvidenceError("runtime package identity capture is incomplete")
    return {
        "architecture": machine,
        "os_release": os_release,
        "packages": packages,
        "platform": CONTAINER_PLATFORM,
        "tool_versions": versions,
    }


def build_binding(
    repo: Path,
    github: Mapping[str, Any],
    container_image: str,
) -> Dict[str, Any]:
    actual_head = run_command(
        [
            "git",
            "-c",
            "safe.directory={}".format(repo.resolve()),
            "rev-parse",
            "HEAD",
        ],
        cwd=repo,
    ).decode().strip()
    if actual_head != github["head_sha"]:
        raise EvidenceError("checked-out commit differs from the GitHub head SHA")
    inputs = {}
    for name, relative in (
        ("capture_script", CAPTURE_SCRIPT_PATH),
        ("patch_series", PATCH_SERIES_PATH),
        ("source_lock", SOURCE_LOCK_PATH),
        ("source_lock_validator", SOURCE_LOCK_VALIDATOR_PATH),
        ("workflow", WORKFLOW_PATH),
    ):
        inputs[name] = committed_file_identity(repo, actual_head, relative)
    return {
        "checkpoint_id": CHECKPOINT_ID,
        "container": {
            "image": container_image,
            "manifest_digest": CONTAINER_MANIFEST_DIGEST,
            "platform": CONTAINER_PLATFORM,
            "tag_index_digest_observed_at_authoring": CONTAINER_TAG_INDEX_DIGEST,
        },
        "github": dict(github),
        "inputs": inputs,
        "schema_version": SCHEMA_VERSION,
    }


class RejectRedirects(urllib.request.HTTPRedirectHandler):
    """Reject every redirect; evidence URLs must resolve exactly as locked."""

    def redirect_request(
        self,
        request: urllib.request.Request,
        file_pointer: BinaryIO,
        code: int,
        message: str,
        headers: Mapping[str, str],
        new_url: str,
    ) -> None:
        del request, file_pointer, message, headers
        raise EvidenceError(
            "download redirect rejected: status={} target={!r}".format(code, new_url)
        )


def validate_locked_https_url(url: Any, expected_host: str, label: str) -> str:
    if not isinstance(url, str):
        raise EvidenceError("{} must be a URL".format(label))
    parsed = urllib.parse.urlsplit(url)
    if (
        parsed.scheme != "https"
        or parsed.hostname != expected_host
        or parsed.username is not None
        or parsed.password is not None
        or parsed.port is not None
        or parsed.query
        or parsed.fragment
        or not parsed.path.startswith("/")
    ):
        raise EvidenceError("{} has host or URL drift: {!r}".format(label, url))
    return url


def download_exact(
    url: str,
    target: Path,
    expected_sha256: str,
    expected_size: Optional[int],
    maximum_size: int,
    opener: Optional[Any] = None,
) -> Dict[str, Any]:
    validate_locked_https_url(url, "download.rockylinux.org", "download URL")
    if not HEX_SHA256.fullmatch(expected_sha256):
        raise EvidenceError("download SHA-256 identity is malformed")
    if expected_size is not None and (not isinstance(expected_size, int) or expected_size < 1):
        raise EvidenceError("download byte identity is malformed")
    if maximum_size < 1 or (expected_size is not None and expected_size > maximum_size):
        raise EvidenceError("download size cap is smaller than the locked artifact")
    if target.exists() or target.is_symlink():
        raise EvidenceError("refusing to overwrite download target: {}".format(target))
    target.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(
        url,
        headers={
            "Accept-Encoding": "identity",
            "User-Agent": "mckernel-rk-001-source-evidence/1",
        },
        method="GET",
    )
    http = opener if opener is not None else urllib.request.build_opener(RejectRedirects())
    temporary = None  # type: Optional[str]
    digest = hashlib.sha256()
    size = 0
    status = None
    content_length = None
    try:
        try:
            response_context = http.open(request, timeout=120.0)
        except EvidenceError:
            raise
        except (OSError, urllib.error.URLError) as exc:
            raise EvidenceError("download failed without verified bytes: {}".format(exc)) from exc
        with response_context as response:
            status = getattr(response, "status", None)
            if status != 200:
                raise EvidenceError("download returned HTTP status {!r}".format(status))
            if response.geturl() != url:
                raise EvidenceError("download final URL drifted from its lock")
            encodings = response.headers.get_all("Content-Encoding") or []
            if encodings and encodings != ["identity"]:
                raise EvidenceError("download used an unexpected content encoding")
            lengths = response.headers.get_all("Content-Length") or []
            if len(lengths) != 1 or not lengths[0].isdigit():
                raise EvidenceError(
                    "download needs one unambiguous Content-Length: "
                    "url={!r} locked_size={!r} declared_content_lengths={!r}".format(
                        url, expected_size, lengths
                    )
                )
            content_length = int(lengths[0])
            if content_length < 1 or content_length > maximum_size:
                raise EvidenceError("download Content-Length exceeds its evidence cap")
            if expected_size is not None and content_length != expected_size:
                raise EvidenceError(
                    "download Content-Length differs from its lock: "
                    "url={!r} locked_size={} declared_size={}".format(
                        url, expected_size, content_length
                    )
                )
            with tempfile.NamedTemporaryFile(
                mode="wb",
                prefix=".{}-".format(target.name),
                dir=str(target.parent),
                delete=False,
            ) as output:
                temporary = output.name
                while True:
                    chunk = response.read(1024 * 1024)
                    if not chunk:
                        break
                    if not isinstance(chunk, bytes):
                        raise EvidenceError("download stream returned non-byte data")
                    size += len(chunk)
                    if size > content_length or size > maximum_size:
                        raise EvidenceError("download exceeded its declared size")
                    digest.update(chunk)
                    output.write(chunk)
                output.flush()
                os.fsync(output.fileno())
        actual_sha256 = digest.hexdigest()
        if (
            size != content_length
            or (expected_size is not None and size != expected_size)
            or actual_sha256 != expected_sha256
        ):
            raise EvidenceError(
                "download identity differs from its lock: "
                "url={!r} locked_size={!r} declared_size={} actual_size={} "
                "locked_sha256={} actual_sha256={}".format(
                    url,
                    expected_size,
                    content_length,
                    size,
                    expected_sha256,
                    actual_sha256,
                )
            )
        if temporary is None:
            raise EvidenceError("download did not create a staged artifact")
        os.chmod(temporary, 0o400)
        os.replace(temporary, target)
        temporary = None
    finally:
        if temporary is not None:
            try:
                os.unlink(temporary)
            except FileNotFoundError:
                pass
    return {
        "content_length": content_length,
        "final_url": url,
        "http_status": status,
        "redirect_count": 0,
        "sha256": digest.hexdigest(),
        "size": size,
        "url": url,
    }


def _xml_children(element: ET.Element, local_name: str) -> List[ET.Element]:
    return [child for child in list(element) if child.tag.rsplit("}", 1)[-1] == local_name]


def _one_xml_child(element: ET.Element, local_name: str, label: str) -> ET.Element:
    children = _xml_children(element, local_name)
    if len(children) != 1:
        raise EvidenceError("{} needs exactly one {} element".format(label, local_name))
    return children[0]


def verify_repomd_primary(repomd_bytes: bytes, lock: Mapping[str, Any]) -> Dict[str, Any]:
    if b"<!DOCTYPE" in repomd_bytes or b"<!ENTITY" in repomd_bytes:
        raise EvidenceError("repomd.xml contains a forbidden declaration")
    try:
        root = ET.fromstring(repomd_bytes)
    except ET.ParseError as exc:
        raise EvidenceError("repomd.xml is malformed: {}".format(exc)) from exc
    if root.tag.rsplit("}", 1)[-1] != "repomd":
        raise EvidenceError("repository metadata root is not repomd")
    revision = _one_xml_child(root, "revision", "repomd.xml")
    expected_repository = lock["repository_snapshot"]
    if (revision.text or "").strip() != expected_repository["repomd"]["revision"]:
        raise EvidenceError("repomd revision differs from the source lock")
    primary_rows = [
        child
        for child in _xml_children(root, "data")
        if child.attrib.get("type") == "primary"
    ]
    if len(primary_rows) != 1:
        raise EvidenceError("repomd.xml needs exactly one primary metadata row")
    primary = primary_rows[0]
    expected = expected_repository["primary_metadata"]
    checksum = _one_xml_child(primary, "checksum", "primary metadata")
    open_checksum = _one_xml_child(primary, "open-checksum", "primary metadata")
    location = _one_xml_child(primary, "location", "primary metadata")
    size = _one_xml_child(primary, "size", "primary metadata")
    open_size = _one_xml_child(primary, "open-size", "primary metadata")
    timestamp = _one_xml_child(primary, "timestamp", "primary metadata")
    if checksum.attrib != {"type": "sha256"} or (checksum.text or "").strip() != expected["sha256"]:
        raise EvidenceError("primary compressed checksum differs from the lock")
    if open_checksum.attrib != {"type": "sha256"} or (open_checksum.text or "").strip() != expected["open_sha256"]:
        raise EvidenceError("primary open checksum differs from the lock")
    if location.attrib != {"href": expected["href"]}:
        raise EvidenceError("primary metadata location differs from the lock")
    numeric = {
        "open_size": (open_size.text or "").strip(),
        "size": (size.text or "").strip(),
        "timestamp": (timestamp.text or "").strip(),
    }
    for name, text in numeric.items():
        expected_key = "open_size" if name == "open_size" else name
        if not text.isdigit() or int(text) != expected[expected_key]:
            raise EvidenceError("primary {} differs from the lock".format(name))
    href_path = PurePosixPath(expected["href"])
    if href_path.is_absolute() or any(part in ("", ".", "..") for part in href_path.parts):
        raise EvidenceError("primary metadata href is not normalized")
    return {
        "href": expected["href"],
        "open_sha256": expected["open_sha256"],
        "open_size": expected["open_size"],
        "sha256": expected["sha256"],
        "size": expected["size"],
        "timestamp": expected["timestamp"],
    }


def verify_open_primary(path: Path, expected: Mapping[str, Any]) -> Dict[str, Any]:
    compressed_size, compressed_sha = sha256_file(path)
    if compressed_size != expected["size"] or compressed_sha != expected["sha256"]:
        raise EvidenceError("compressed primary metadata differs from the lock")
    try:
        opened = gzip.decompress(path.read_bytes())
    except (OSError, EOFError) as exc:
        raise EvidenceError("primary metadata cannot be decompressed") from exc
    if len(opened) != expected["open_size"]:
        raise EvidenceError("open primary metadata size differs from the lock")
    opened_sha = sha256_bytes(opened)
    if opened_sha != expected["open_sha256"]:
        raise EvidenceError("open primary metadata SHA-256 differs from the lock")
    return {"open_sha256": opened_sha, "open_size": len(opened)}


def parse_primary_key_fingerprint(colon_output: bytes) -> str:
    try:
        rows = [line.split(":") for line in colon_output.decode("utf-8").splitlines()]
    except UnicodeDecodeError as exc:
        raise EvidenceError("gpg key identity output is not UTF-8") from exc
    fingerprints = []
    expect_primary = False
    for row in rows:
        kind = row[0] if row else ""
        if kind == "pub":
            if expect_primary:
                raise EvidenceError("gpg key output omitted a primary fingerprint")
            expect_primary = True
        elif kind == "fpr" and expect_primary:
            if len(row) <= 9 or not re.fullmatch(r"[0-9A-F]{40}", row[9]):
                raise EvidenceError("gpg key fingerprint is malformed")
            fingerprints.append(row[9])
            expect_primary = False
    if expect_primary or len(fingerprints) != 1:
        raise EvidenceError("release-key file must contain exactly one primary key")
    return fingerprints[0]


def parse_gpg_validsig(status_output: bytes, expected_fingerprint: str, expected_created: int) -> Dict[str, Any]:
    try:
        lines = status_output.decode("utf-8").splitlines()
    except UnicodeDecodeError as exc:
        raise EvidenceError("gpg status output is not UTF-8") from exc
    forbidden = ("BADSIG", "ERRSIG", "NO_PUBKEY", "EXPSIG", "EXPKEYSIG", "REVKEYSIG")
    statuses = []
    for line in lines:
        if not line.startswith("[GNUPG:] "):
            continue
        fields = line[len("[GNUPG:] ") :].split()
        if fields:
            statuses.append(fields)
    if any(row[0] in forbidden for row in statuses):
        raise EvidenceError("gpg reported a forbidden signature status")
    valid = [row for row in statuses if row[0] == "VALIDSIG"]
    good = [row for row in statuses if row[0] == "GOODSIG"]
    if len(valid) != 1 or len(good) != 1 or len(valid[0]) < 11:
        raise EvidenceError("gpg did not report exactly one good valid signature")
    row = valid[0]
    signature_fingerprint = row[1]
    primary_fingerprint = row[10]
    if signature_fingerprint != expected_fingerprint and primary_fingerprint != expected_fingerprint:
        raise EvidenceError("repomd signature does not chain to the pinned Rocky key")
    if not row[3].isdigit() or int(row[3]) != expected_created:
        raise EvidenceError("repomd signature creation timestamp differs from the lock")
    if not row[7].isdigit() or not row[8].isdigit():
        raise EvidenceError("repomd signature algorithms are malformed")
    return {
        "created_unix": int(row[3]),
        "hash_algorithm_id": int(row[8]),
        "primary_fingerprint": primary_fingerprint,
        "public_key_algorithm_id": int(row[7]),
        "signature_fingerprint": signature_fingerprint,
        "status": "verified",
    }


def verify_repomd_signature(
    key_path: Path,
    signature_path: Path,
    repomd_path: Path,
    lock: Mapping[str, Any],
    work: Path,
) -> Dict[str, Any]:
    expected = lock["repository_snapshot"]
    expected_fingerprint = expected["release_key"]["fingerprint"]
    home = work / "gnupg"
    home.mkdir(mode=0o700)
    colon_output = run_command(
        [
            "gpg",
            "--batch",
            "--homedir",
            str(home),
            "--with-colons",
            "--show-keys",
            "--fingerprint",
            str(key_path),
        ]
    )
    actual_fingerprint = parse_primary_key_fingerprint(colon_output)
    if actual_fingerprint != expected_fingerprint:
        raise EvidenceError("release key fingerprint differs from the lock")
    keyring = work / "rocky-10-release-key.gpg"
    run_command(
        [
            "gpg",
            "--batch",
            "--yes",
            "--dearmor",
            "--output",
            str(keyring),
            str(key_path),
        ]
    )
    status = run_command(
        [
            "gpgv",
            "--status-fd=1",
            "--keyring",
            str(keyring),
            str(signature_path),
            str(repomd_path),
        ]
    )
    verified = parse_gpg_validsig(
        status,
        expected_fingerprint,
        expected["repomd"]["signature"]["created_unix"],
    )
    verified["release_key_fingerprint"] = actual_fingerprint
    return verified


def parse_rpm_header_signature(output: bytes, expected_fingerprint: str) -> Dict[str, Any]:
    try:
        text = output.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise EvidenceError("rpmkeys output is not UTF-8") from exc
    upper = text.upper()
    if any(
        token in upper
        for token in ("NOT OK", "NOKEY", "NOTFOUND", "NOTTRUSTED", "SIGNATURE: BAD")
    ):
        raise EvidenceError("rpmkeys did not establish a trusted signature")
    matches = []
    for public_key_algorithm, hash_algorithm, key_id in RPM_HEADER_SIGNATURE_LEGACY.findall(text):
        matches.append((public_key_algorithm, hash_algorithm, "key-id", key_id))
    for (
        public_key_algorithm,
        hash_algorithm,
        identity_type,
        key_identity,
    ) in RPM_HEADER_SIGNATURE_OPENPGP.findall(text):
        matches.append(
            (
                public_key_algorithm,
                hash_algorithm,
                "fingerprint" if identity_type.lower() == "fingerprint" else "key-id",
                key_identity,
            )
        )
    if len(matches) != 1:
        raise EvidenceError("rpmkeys did not report exactly one header signature")
    public_key_algorithm, hash_algorithm, identity_type, key_identity = matches[0]
    normalized_key_identity = key_identity.upper()
    if not expected_fingerprint.endswith(normalized_key_identity):
        raise EvidenceError("SRPM header signer does not match the pinned Rocky key")
    return {
        "hash_algorithm": hash_algorithm.upper(),
        "public_key_algorithm": public_key_algorithm.upper(),
        "signature_algorithm": "{}/{}".format(
            public_key_algorithm.upper(), hash_algorithm.upper()
        ),
        "signature_key_identity": normalized_key_identity,
        "signature_key_identity_type": identity_type,
        "signer_fingerprint": expected_fingerprint,
        "status": "verified",
        "verification_output_sha256": sha256_bytes(output),
    }


def verify_srpm_header_signature(
    srpm_path: Path,
    key_path: Path,
    expected_fingerprint: str,
    work: Path,
) -> Dict[str, Any]:
    rpmdb = work / "rpmdb"
    rpmdb.mkdir(mode=0o700)
    run_command(["rpm", "--dbpath", str(rpmdb), "--initdb"])
    run_command(["rpmkeys", "--dbpath", str(rpmdb), "--import", str(key_path)])
    imported = run_command(
        [
            "rpm",
            "--dbpath",
            str(rpmdb),
            "-q",
            "--qf",
            "%{NAME}-%{VERSION}-%{RELEASE}\\n",
            "gpg-pubkey",
        ]
    ).decode("utf-8", errors="strict").splitlines()
    if len(imported) != 1 or not imported[0].startswith("gpg-pubkey-"):
        raise EvidenceError("isolated RPM database does not contain exactly one release key")
    output = run_command(
        ["rpmkeys", "--dbpath", str(rpmdb), "--checksig", "--verbose", str(srpm_path)]
    )
    result = parse_rpm_header_signature(output, expected_fingerprint)
    result["isolated_rpm_key_record"] = imported[0]
    return result


def git_environment(work: Path) -> Dict[str, str]:
    home = work / "git-home"
    home.mkdir(mode=0o700)
    env = dict(os.environ)
    env.update(
        {
            "GIT_ASKPASS": "/bin/false",
            "GIT_CONFIG_GLOBAL": "/dev/null",
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_TERMINAL_PROMPT": "0",
            "HOME": str(home),
            "LC_ALL": "C",
        }
    )
    return env


def inspect_dist_git(
    dist_git: Path,
    lock: Mapping[str, Any],
    series: Mapping[str, Any],
    env: Optional[Mapping[str, str]] = None,
) -> Dict[str, Any]:
    identity = lock["dist_git"]
    try:
        source_lock.verify_dist_git(dist_git, lock, series)
    except source_lock.SourceLockError as exc:
        raise EvidenceError("dist-git object verification failed: {}".format(exc)) from exc
    command_env = env if env is not None else os.environ

    def git(arguments: Sequence[str]) -> bytes:
        return run_command(["git"] + list(arguments), cwd=dist_git, env=command_env)

    if git(["cat-file", "-t", identity["tag"]]).decode().strip() != "tag":
        raise EvidenceError("locked dist-git ref is not an annotated tag")
    tag_bytes = git(["cat-file", "-p", identity["tag"]])
    rows = []
    for item in list(identity["content"]) + list(series["patches"]):
        path = item["path"]
        oid = git(["rev-parse", "{}:{}".format(identity["commit"], path)]).decode().strip()
        if not HEX_SHA1.fullmatch(oid):
            raise EvidenceError("dist-git blob OID is malformed: {}".format(path))
        if git(["cat-file", "-t", oid]).decode().strip() != "blob":
            raise EvidenceError("locked dist-git object is not a blob: {}".format(path))
        rows.append(
            {
                "git_blob_oid": oid,
                "path": path,
                "sha256": item["sha256"],
                "size": item["size"],
            }
        )
    return {
        "blobs": rows,
        "commit": identity["commit"],
        "commit_parent": identity["commit_parent"],
        "http_redirects_allowed": False,
        "repository_url": identity["repository_url"],
        "tag": identity["tag"],
        "tag_annotation_sha256": sha256_bytes(tag_bytes),
        "tag_object": identity["tag_object"],
        "tag_peel": identity["commit"],
    }


def fetch_and_verify_dist_git(
    work: Path, lock: Mapping[str, Any], series: Mapping[str, Any]
) -> Dict[str, Any]:
    identity = lock["dist_git"]
    url = validate_locked_https_url(
        identity["repository_url"], "git.rockylinux.org", "dist-git repository URL"
    )
    dist_git = work / "dist-git"
    dist_git.mkdir(mode=0o700)
    env = git_environment(work)
    run_command(["git", "init", "--quiet"], cwd=dist_git, env=env)
    refspec = "+refs/tags/{0}:refs/tags/{0}".format(identity["tag"])
    run_command(
        [
            "git",
            "-c",
            "credential.helper=",
            "-c",
            "http.followRedirects=false",
            "-c",
            "http.sslVerify=true",
            "-c",
            "protocol.version=2",
            "fetch",
            "--quiet",
            "--no-tags",
            "--depth=2",
            "--force",
            url,
            refspec,
        ],
        cwd=dist_git,
        env=env,
    )
    return inspect_dist_git(dist_git, lock, series, env)


def bound_record(binding: Mapping[str, Any], evidence_class: str, result: Mapping[str, Any]) -> Dict[str, Any]:
    return {
        "binding": dict(binding),
        "evidence_class": evidence_class,
        "result": dict(result),
        "schema_version": SCHEMA_VERSION,
    }


def write_evidence_file(directory: Path, name: str, value: Mapping[str, Any]) -> None:
    if not re.fullmatch(r"[a-z0-9-]+\.json", name):
        raise EvidenceError("invalid evidence filename")
    path = directory / name
    if path.exists() or path.is_symlink():
        raise EvidenceError("duplicate evidence output: {}".format(name))
    data = canonical_json_bytes(value)
    path.write_bytes(data)
    os.chmod(str(path), 0o444)


def finalize_evidence(directory: Path) -> List[str]:
    json_files = sorted(directory.glob("*.json"), key=lambda item: item.name)
    if not json_files:
        raise EvidenceError("no evidence JSON files were produced")
    lines = []
    for path in json_files:
        if path.is_symlink() or not path.is_file():
            raise EvidenceError("evidence output is not a regular file")
        _, digest = sha256_file(path)
        lines.append("{}  {}".format(digest, path.name))
    checksum_path = directory / "SHA256SUMS"
    checksum_path.write_text("\n".join(lines) + "\n", encoding="ascii")
    os.chmod(str(checksum_path), 0o444)
    return [path.name for path in json_files] + [checksum_path.name]


def print_reconstructable_evidence(directory: Path, names: Sequence[str]) -> None:
    for name in names:
        path = directory / name
        data = path.read_bytes()
        encoded = base64.b64encode(data).decode("ascii")
        print("RK001_EVIDENCE_BEGIN {} {} {}".format(name, len(data), sha256_bytes(data)))
        print(encoded)
        print("RK001_EVIDENCE_END {}".format(name))


def capture(
    repo: Path,
    output_dir: Path,
    github: Mapping[str, Any],
    container_image: str,
) -> None:
    lock, series, _, _, starting_blockers = load_locked_inputs(repo)
    validate_workflow_contract(repo)
    runtime = capture_runtime_environment()
    binding = build_binding(repo, github, container_image)

    if output_dir.exists() or output_dir.is_symlink():
        raise EvidenceError("output directory already exists; stale evidence is forbidden")
    if not output_dir.is_absolute() or output_dir.name in ("", ".", ".."):
        raise EvidenceError("output directory must be an absolute normalized path")
    requested_parent = output_dir.parent
    parent = requested_parent.resolve()
    if requested_parent != parent:
        raise EvidenceError("output path has symlink or non-canonical traversal")
    if not requested_parent.is_dir() or requested_parent.is_symlink():
        raise EvidenceError("output parent must be an existing non-symlink directory")

    stage = Path(tempfile.mkdtemp(prefix=".rk001-evidence-", dir=str(parent)))
    try:
        with tempfile.TemporaryDirectory(prefix="rk001-source-work-") as work_name:
            work = Path(work_name)
            source = lock["source_rpm"]
            repository = lock["repository_snapshot"]
            srpm_path = work / source["filename"]
            srpm_download = download_exact(
                source["url"],
                srpm_path,
                source["sha256"],
                source["size"],
                source["size"],
            )

            key_path = work / "RPM-GPG-KEY-Rocky-10"
            repomd_path = work / "repomd.xml"
            signature_path = work / "repomd.xml.asc"
            primary_path = work / "primary.xml.gz"
            key_download = download_exact(
                repository["release_key"]["url"],
                key_path,
                repository["release_key"]["sha256"],
                None,
                MAX_SMALL_DOWNLOAD_BYTES,
            )
            repomd_download = download_exact(
                repository["repomd"]["url"],
                repomd_path,
                repository["repomd"]["sha256"],
                None,
                MAX_SMALL_DOWNLOAD_BYTES,
            )
            signature_download = download_exact(
                repository["repomd"]["signature"]["url"],
                signature_path,
                repository["repomd"]["signature"]["sha256"],
                None,
                MAX_SMALL_DOWNLOAD_BYTES,
            )
            primary_identity = verify_repomd_primary(repomd_path.read_bytes(), lock)
            primary_url = repository["base_url"] + primary_identity["href"]
            primary_download = download_exact(
                primary_url,
                primary_path,
                primary_identity["sha256"],
                primary_identity["size"],
                primary_identity["size"],
            )
            open_primary = verify_open_primary(primary_path, primary_identity)
            repomd_signature = verify_repomd_signature(
                key_path, signature_path, repomd_path, lock, work
            )
            srpm_signature = verify_srpm_header_signature(
                srpm_path,
                key_path,
                repository["release_key"]["fingerprint"],
                work,
            )
            dist_git = fetch_and_verify_dist_git(work, lock, series)

            context = {
                "binding": binding,
                "runtime": runtime,
                "schema_version": SCHEMA_VERSION,
            }
            acquisition = {
                "artifact": {
                    "arch": source["arch"],
                    "filename": source["filename"],
                    "nevra": source["nevra"],
                },
                "download": srpm_download,
            }
            metadata = {
                "downloads": {
                    "primary": primary_download,
                    "release_key": key_download,
                    "repomd": repomd_download,
                    "repomd_signature": signature_download,
                },
                "primary": dict(primary_identity, **open_primary),
                "repomd_signature": repomd_signature,
            }
            summary = {
                "binding": binding,
                "captured_evidence_classes": [
                    "acquisition_replay",
                    "dist_git_object_replay",
                    "repository_metadata_signature_replay",
                    "srpm_header_signature",
                ],
                "credit_eligible": False,
                "remaining_blockers": [
                    "captured CI evidence is not credited until reviewed and committed",
                    "complete path-by-path license and provenance inventory is still missing",
                ],
                "rk_001_ready": False,
                "schema_version": SCHEMA_VERSION,
                "starting_source_lock_blockers": starting_blockers,
            }

            write_evidence_file(stage, "capture-context.json", context)
            write_evidence_file(
                stage,
                "acquisition-replay.json",
                bound_record(binding, "acquisition_replay", acquisition),
            )
            write_evidence_file(
                stage,
                "repository-metadata-signature-replay.json",
                bound_record(
                    binding, "repository_metadata_signature_replay", metadata
                ),
            )
            write_evidence_file(
                stage,
                "srpm-header-signature.json",
                bound_record(binding, "srpm_header_signature", srpm_signature),
            )
            write_evidence_file(
                stage,
                "dist-git-object-replay.json",
                bound_record(binding, "dist_git_object_replay", dist_git),
            )
            write_evidence_file(stage, "capture-summary.json", summary)

        names = finalize_evidence(stage)
        os.replace(str(stage), str(output_dir))
        print_reconstructable_evidence(output_dir, names)
        print("RK-001 remains NOT READY: capture completed without gate credit")
    finally:
        if stage.exists():
            shutil.rmtree(str(stage))


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[1])
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--check", action="store_true")
    modes.add_argument("--run", action="store_true")
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--github-head-sha")
    parser.add_argument("--github-run-id")
    parser.add_argument("--github-run-attempt")
    parser.add_argument("--github-repository")
    parser.add_argument("--container-image")
    return parser.parse_args(argv)


def main(argv: Sequence[str]) -> int:
    args = parse_args(argv)
    repo = args.repo.resolve()
    try:
        _, _, blockers = check_repository(repo)
        if args.check:
            print(
                "RK-001 evidence capture contract verified; gate remains blocked by {} item(s)".format(
                    len(blockers)
                )
            )
            return 0
        required = {
            "--container-image": args.container_image,
            "--github-head-sha": args.github_head_sha,
            "--github-repository": args.github_repository,
            "--github-run-attempt": args.github_run_attempt,
            "--github-run-id": args.github_run_id,
            "--output-dir": args.output_dir,
        }
        missing = sorted(name for name, value in required.items() if value is None)
        if missing:
            raise EvidenceError("--run requires {}".format(", ".join(missing)))
        github = validate_run_identity(
            args.github_head_sha,
            args.github_run_id,
            args.github_run_attempt,
            args.github_repository,
            args.container_image,
        )
        capture(repo, args.output_dir, github, args.container_image)
        return 0
    except EvidenceError as exc:
        print("RK-001 evidence capture error: {}".format(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
