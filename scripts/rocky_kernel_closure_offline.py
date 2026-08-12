#!/usr/bin/env python3
"""Capture fail-closed RK-003 transitive closure and offline replay evidence.

This is phase two of the Rocky platform evidence plan.  It consumes the
reviewed repository-direct bundle, uses DNF only to acquire a candidate
transaction, binds every selected RPM to the already captured signed primary
metadata, verifies every RPM with the private Rocky-key RPM database, and then
replays the complete transaction into a second empty installroot with every
repository disabled.  Successful capture is deliberately credit-forbidden.
"""

import argparse
import ast
import bz2
import gzip
import hashlib
import json
import lzma
import os
import re
import shlex
import shutil
import stat
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path, PurePosixPath
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

import rocky_kernel_platform_evidence as phase_one


CONTRACT_PATH = Path(
    "host-kernel/rocky/evidence/closure-offline-contract-v1.json"
)
EXPECTED_CONTRACT_SHA256 = (
    "2fe1230ef9cd7901a3c660f3dfd26b2dadfb31b161ef047fedfda20d9936c013"
)
WORKFLOW_PATH = Path(".github/workflows/rocky-kernel-closure-offline.yml")
EXPECTED_WORKFLOW_SHA256 = (
    "1ae78c257ab7682aa8dbd817970c9f0384b47fe2b2880cdc523138a121967ce1"
)
EXPECTED_WORKFLOW_USES = [
    "actions/checkout@11d5960a326750d5838078e36cf38b85af677262",
    "actions/checkout@11d5960a326750d5838078e36cf38b85af677262",
    "actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02",
]
SCHEMA_VERSION = 1
PHASE_ID = "closure-offline"
RPM_NEVRA_QUERY = "%{NAME}-%{EPOCHNUM}:%{VERSION}-%{RELEASE}.%{ARCH}\\n"
MAX_PRIMARY_PACKAGES = 100000
MAX_CAPTURED_RPMS = 4096
MAX_CAPTURED_BYTES = 8 * 1024 * 1024 * 1024
MAX_REPOMD_OBJECTS = 64
MAX_METADATA_OBJECT_BYTES = 512 * 1024 * 1024
MAX_METADATA_OPEN_BYTES = 1024 * 1024 * 1024
HEX_SHA256 = re.compile(r"^[0-9a-f]{64}$")
LOCKED_LLVM_PROBE_OWNER_NEVRA = "llvm-0:21.1.8-1.el10.x86_64"
LLVM_CONFIG_OWNER_NEVRA = "llvm-devel-0:21.1.8-1.el10.x86_64"
LLVM_OWNER_AUTHORITY_BLOCKER = (
    "The current RK-003 toolchain authority maps the llvm-config probe to "
    "llvm-0:21.1.8-1.el10.x86_64, but the captured binary is owned by "
    "llvm-devel-0:21.1.8-1.el10.x86_64; this mapping must be reconciled before "
    "credit or review ingestion."
)
LIBCLANG_PROBE_BYTES = (
    b"/* SPDX-License-Identifier: GPL-2.0 */\n"
    b'#pragma message("clang version " __clang_version__)\n'
)
# Exact two-line helper used by the locked kernel probe command.  It is copied
# into the ephemeral installroot only; this does not attest the source tree.
LIBCLANG_PROBE_SHA256 = "bf71d14ea244116ab8c6d61c593d37be3c9c346e13d0569a10acdfec63739e21"
PROBE_RESULT_FIELDS = {
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
}
DIRECT_MANIFEST_NAMES = [
    "blockers.json",
    "build-requirements.json",
    "direct-rpms.json",
    "environment.json",
    "repository-snapshots.json",
]
PYTHON36_ENTRYPOINT_PATHS = [
    "scripts/rocky_kernel_closure_offline.py",
    "scripts/rocky_kernel_platform_evidence.py",
]


class ClosureError(RuntimeError):
    pass


def exact_keys(value: object, expected: Iterable[str], label: str) -> Mapping[str, Any]:
    if not isinstance(value, dict) or set(value) != set(expected):
        actual = sorted(value) if isinstance(value, dict) else type(value).__name__
        raise ClosureError(
            "{} fields changed: actual={!r}, expected={!r}".format(
                label, actual, sorted(expected)
            )
        )
    return value


def require_exact(value: object, expected: object, label: str) -> None:
    if value != expected or type(value) is not type(expected):
        raise ClosureError(
            "{} changed: actual={!r}, expected={!r}".format(label, value, expected)
        )


def open_regular_read(path: Path, label: str) -> int:
    """Open one regular file without following any component symlinks."""
    if not hasattr(os, "O_DIRECTORY") or not hasattr(os, "O_NOFOLLOW"):
        raise ClosureError("no-follow file opening is unavailable")
    absolute = Path(os.path.abspath(str(path)))
    parts = absolute.parts
    if not parts or parts[0] != os.path.sep or len(parts) < 2:
        raise ClosureError("{} path is invalid".format(label))
    directory_fd = -1
    file_fd = -1
    try:
        directory_fd = os.open(
            os.path.sep, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
        )
        for component in parts[1:-1]:
            next_fd = os.open(
                component,
                os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                dir_fd=directory_fd,
            )
            os.close(directory_fd)
            directory_fd = next_fd
        file_fd = os.open(
            parts[-1],
            os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK,
            dir_fd=directory_fd,
        )
        if not stat.S_ISREG(os.fstat(file_fd).st_mode):
            raise ClosureError("{} must be a regular file".format(label))
        result = file_fd
        file_fd = -1
        return result
    except OSError as exc:
        raise ClosureError("cannot safely open {}: {}".format(label, exc)) from exc
    finally:
        if directory_fd >= 0:
            os.close(directory_fd)
        if file_fd >= 0:
            os.close(file_fd)


def open_regular_create(path: Path, label: str) -> int:
    """Create one regular file without following any component symlinks."""
    if not hasattr(os, "O_DIRECTORY") or not hasattr(os, "O_NOFOLLOW"):
        raise ClosureError("no-follow file creation is unavailable")
    absolute = Path(os.path.abspath(str(path)))
    parts = absolute.parts
    if not parts or parts[0] != os.path.sep or len(parts) < 2:
        raise ClosureError("{} path is invalid".format(label))
    directory_fd = -1
    file_fd = -1
    try:
        directory_fd = os.open(
            os.path.sep, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
        )
        for component in parts[1:-1]:
            next_fd = os.open(
                component,
                os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                dir_fd=directory_fd,
            )
            os.close(directory_fd)
            directory_fd = next_fd
        file_fd = os.open(
            parts[-1],
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
            0o600,
            dir_fd=directory_fd,
        )
        if not stat.S_ISREG(os.fstat(file_fd).st_mode):
            raise ClosureError("{} must be a regular file".format(label))
        result = file_fd
        file_fd = -1
        return result
    except OSError as exc:
        raise ClosureError("cannot safely create {}: {}".format(label, exc)) from exc
    finally:
        if directory_fd >= 0:
            os.close(directory_fd)
        if file_fd >= 0:
            os.close(file_fd)


def regular_identity(value: os.stat_result) -> Tuple[int, int, int, int, int]:
    return (
        value.st_dev,
        value.st_ino,
        value.st_size,
        value.st_mtime_ns,
        value.st_ctime_ns,
    )


def read_regular_bytes(path: Path, label: str) -> bytes:
    descriptor = open_regular_read(path, label)
    try:
        with os.fdopen(descriptor, "rb") as stream:
            descriptor = -1
            before = regular_identity(os.fstat(stream.fileno()))
            data = stream.read()
            after = regular_identity(os.fstat(stream.fileno()))
            if before != after or len(data) != after[2]:
                raise ClosureError("{} changed while it was read".format(label))
            return data
    finally:
        if descriptor >= 0:
            os.close(descriptor)


def sha256_file(path: Path) -> Tuple[int, str]:
    digest = hashlib.sha256()
    size = 0
    descriptor = open_regular_read(path, "hash input")
    try:
        with os.fdopen(descriptor, "rb") as stream:
            descriptor = -1
            before = regular_identity(os.fstat(stream.fileno()))
            while True:
                chunk = stream.read(1024 * 1024)
                if not chunk:
                    break
                size += len(chunk)
                digest.update(chunk)
            after = regular_identity(os.fstat(stream.fileno()))
            if before != after or size != after[2]:
                raise ClosureError("hash input changed while it was read")
    finally:
        if descriptor >= 0:
            os.close(descriptor)
    return size, digest.hexdigest()


def read_json(path: Path, label: str) -> Tuple[Dict[str, Any], bytes]:
    data = read_regular_bytes(path, label)
    try:
        value = json.loads(
            data.decode("utf-8"), object_pairs_hook=phase_one.reject_duplicate_pairs
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ClosureError("cannot parse {}: {}".format(label, exc)) from exc
    if not isinstance(value, dict):
        raise ClosureError("{} must be a JSON object".format(label))
    return value, data


def safe_repo_file(repo: Path, relative: str) -> Path:
    try:
        return phase_one.repository_file(repo, Path(relative))
    except phase_one.EvidenceError as exc:
        raise ClosureError(str(exc)) from exc


def runtime_os_release_bytes() -> bytes:
    requested = Path("/etc/os-release")
    try:
        resolved = requested.resolve(strict=True)
    except OSError as exc:
        raise ClosureError("cannot resolve runtime os-release: {}".format(exc)) from exc
    allowed = {requested, Path("/usr/lib/os-release")}
    if resolved not in allowed:
        raise ClosureError("runtime os-release resolves outside its standard locations")
    return read_regular_bytes(resolved, "runtime os-release")


def parse_python36_source(source: str, label: str) -> None:
    """Reject syntax and annotation forms that cannot import on Python 3.6."""
    try:
        try:
            ast.parse(source, filename=label, feature_version=(3, 6))
        except TypeError:
            try:
                ast.parse(source, filename=label, feature_version=6)
            except TypeError:
                ast.parse(source, filename=label)
    except SyntaxError as exc:
        raise ClosureError("{} is not Python 3.6 parseable: {}".format(label, exc)) from exc
    forbidden = (
        (r"from\s+__future__\s+import\s+annotations", "postponed annotations"),
        (r"\b(?:list|dict|set|tuple)\s*\[[^\]]", "built-in generic annotation"),
        (
            r"(?:->|:)\s*[A-Za-z_][A-Za-z0-9_.\[\], ]*\s\|\s(?:None|[A-Za-z_])",
            "PEP 604 union annotation",
        ),
    )
    for pattern, description in forbidden:
        if re.search(pattern, source):
            raise ClosureError("{} uses a Python 3.6-incompatible {}".format(label, description))


def local_python_imports(source: str) -> List[str]:
    tree = ast.parse(source)
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            names.add(node.module.split(".")[0])
    return sorted(names)


def python36_runtime_paths(repo: Path) -> List[str]:
    pending = list(PYTHON36_ENTRYPOINT_PATHS)
    observed: List[str] = []
    while pending:
        relative = pending.pop(0)
        if relative in observed:
            continue
        path = safe_repo_file(repo, relative)
        try:
            source = read_regular_bytes(path, relative).decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ClosureError("{} is not UTF-8".format(relative)) from exc
        parse_python36_source(source, relative)
        observed.append(relative)
        for module in local_python_imports(source):
            candidate = "scripts/{}.py".format(module)
            candidate_path = repo / candidate
            if candidate not in observed and candidate not in pending and candidate_path.exists():
                pending.append(candidate)
    return observed


def validate_python36_runtime(repo: Path) -> None:
    runtime_paths = python36_runtime_paths(repo)
    if len(runtime_paths) < len(PYTHON36_ENTRYPOINT_PATHS):
        raise ClosureError("Python 3.6 runtime import closure is incomplete")


def validate_contract(repo: Path) -> Dict[str, Any]:
    contract_path = safe_repo_file(repo, CONTRACT_PATH.as_posix())
    contract, contract_bytes = read_json(contract_path, "closure contract")
    require_exact(
        hashlib.sha256(contract_bytes).hexdigest(),
        EXPECTED_CONTRACT_SHA256,
        "closure contract digest",
    )
    exact_keys(
        contract,
        {
            "claim_scope",
            "direct_phase",
            "gate_claims",
            "network_contract",
            "outputs",
            "phase_id",
            "required_probe_ids",
            "schema_version",
            "success_blockers",
            "toolchain_lock",
        },
        "closure contract",
    )
    require_exact(contract["schema_version"], SCHEMA_VERSION, "contract schema")
    require_exact(contract["phase_id"], PHASE_ID, "contract phase")
    expected_claims = {
        "RK-002": False,
        "RK-003": False,
        "RK-004": False,
        "RK-005": False,
        "RK-006": False,
        "RS-001": False,
    }
    require_exact(contract["gate_claims"], expected_claims, "gate claims")
    if not isinstance(contract["claim_scope"], str) or "never awards" not in contract[
        "claim_scope"
    ]:
        raise ClosureError("contract claim scope is not fail-closed")
    direct = exact_keys(
        contract["direct_phase"],
        {
            "artifact_id",
            "artifact_name",
            "historical_build_requirements_sha256",
            "historical_checkpoint_sha256",
            "effective_buildrequires_count",
            "github_repository",
            "head_sha",
            "outer_zip_sha256",
            "resolution_root_count",
            "resolution_inputs_sha256",
            "reviewed_rocky_rust_count",
            "run_attempt",
            "run_id",
        },
        "direct phase",
    )
    for field in (
        "historical_build_requirements_sha256",
        "historical_checkpoint_sha256",
        "outer_zip_sha256",
        "resolution_inputs_sha256",
    ):
        if not isinstance(direct[field], str) or not HEX_SHA256.fullmatch(direct[field]):
            raise ClosureError("direct phase {} is not a SHA-256".format(field))
    if not re.fullmatch(r"[0-9a-f]{40}", str(direct["head_sha"])):
        raise ClosureError("direct phase head SHA is malformed")
    require_exact(direct["resolution_root_count"], 109, "resolution root count")
    require_exact(direct["effective_buildrequires_count"], 86, "BuildRequires count")
    require_exact(direct["reviewed_rocky_rust_count"], 3, "Rust addition count")

    lock = exact_keys(contract["toolchain_lock"], {"id", "path", "sha256"}, "toolchain binding")
    lock_path = safe_repo_file(repo, str(lock["path"]))
    _, digest = sha256_file(lock_path)
    require_exact(digest, lock["sha256"], "toolchain lock digest")
    toolchain, _ = read_json(lock_path, "toolchain lock")
    require_exact(toolchain.get("lock_id"), lock["id"], "toolchain lock ID")
    require_exact(toolchain.get("gate", {}).get("credit_eligible"), False, "RK-003 credit")
    probe_ids = [item.get("id") for item in toolchain.get("required_probes", [])]
    require_exact(contract["required_probe_ids"], probe_ids, "required probe IDs")
    require_exact(
        contract["outputs"],
        [
            "closure.json",
            "offline-replay.json",
            "probes.json",
            "rpm-macros.json",
            "environment.json",
            "blockers.json",
            "checkpoint.json",
            "SHA256SUMS",
        ],
        "contract outputs",
    )
    blockers = contract["success_blockers"]
    if not isinstance(blockers, list) or len(blockers) != 9 or not all(
        isinstance(item, str) and item.strip() for item in blockers
    ):
        raise ClosureError("successful capture must retain nine blockers")
    if "marks closure-offline unimplemented" not in blockers[-2]:
        raise ClosureError("phase-plan reconciliation blocker is missing")
    require_exact(
        blockers[-1], LLVM_OWNER_AUTHORITY_BLOCKER, "LLVM owner authority blocker"
    )
    network = exact_keys(
        contract["network_contract"],
        {"acquisition", "offline_replay", "scope"},
        "network contract",
    )
    if "configured network sources" not in str(network["acquisition"]):
        raise ClosureError("acquisition network boundary is overstated")
    if "not kernel-level network isolation" not in str(network["scope"]):
        raise ClosureError("network claim boundary is missing")
    return contract


def expected_direct_bundle_paths(
    plan: Mapping[str, Any], toolchain: Mapping[str, Any]
) -> List[str]:
    paths = {
        "archives/repositories/RPM-GPG-KEY-Rocky-10",
        "blockers.json",
        "bootstrap-input.json",
        "build-requirements.json",
        "checkpoint.json",
        "direct-rpms.json",
        "environment.json",
        "inputs/kernel-x86_64-rhel.config",
        "inputs/kernel.spec",
        "repository-snapshots.json",
        "transcripts/bootstrap-rpms.txt",
        "transcripts/rpm-showrc.txt",
        "transcripts/rpmspec-buildrequires.txt",
        "transcripts/tool-versions.txt",
    }
    for repository in plan["repositories"]:
        repository_id = repository["id"]
        primary_name = PurePosixPath(repository["primary"]["href"]).name
        paths.update(
            {
                "archives/repositories/{}/repomd.xml".format(repository_id),
                "archives/repositories/{}/repomd.xml.asc".format(repository_id),
                "archives/repositories/{}/{}".format(repository_id, primary_name),
                "transcripts/repomd/{}.gpgv.txt".format(repository_id),
            }
        )
    for artifact in toolchain["direct_artifacts"]:
        filename = PurePosixPath(artifact["repository_location"]).name
        paths.add("archives/direct-rpms/{}".format(filename))
        paths.add("transcripts/rpmkeys/{}.txt".format(filename))
    return sorted(paths)


def verify_sha256sums(
    root: Path,
    expected_files: Optional[Sequence[str]] = None,
    label: str = "bundle",
) -> None:
    manifest = root / "SHA256SUMS"
    data = read_regular_bytes(manifest, label + " SHA256SUMS")
    if not data or not data.endswith(b"\n"):
        raise ClosureError("{} SHA256SUMS is malformed".format(label))
    listed: List[str] = []
    for line in data.decode("ascii").splitlines():
        match = re.fullmatch(r"([0-9a-f]{64})  ([^\0\r\n]+)", line)
        if match is None:
            raise ClosureError("{} SHA256SUMS has a malformed row".format(label))
        relative = phase_one.normalized_relative_path(match.group(2), "checksum path")
        path = root.joinpath(*relative.parts)
        resolved = path.resolve()
        if (
            path.is_symlink()
            or path != resolved
            or os.path.commonpath((str(root), str(resolved))) != str(root)
            or not path.is_file()
        ):
            raise ClosureError("checksummed {} input is not a regular file".format(label))
        _, digest = sha256_file(path)
        require_exact(digest, match.group(1), "direct input checksum")
        listed.append(relative.as_posix())
    actual: List[str] = []
    for path in root.rglob("*"):
        if path.is_symlink() or (not path.is_file() and not path.is_dir()):
            raise ClosureError("{} contains a symlink or special file".format(label))
        if path.is_file() and path != manifest:
            actual.append(path.relative_to(root).as_posix())
    actual.sort()
    require_exact(listed, sorted(listed), "checksum path order")
    require_exact(listed, actual, label + " checksum closure")
    if expected_files is not None:
        require_exact(actual, sorted(expected_files), label + " exact file set")


def validate_download_record(
    value: object, expected_url: str, expected_sha256: str, expected_size: int, label: str
) -> None:
    row = exact_keys(
        value, {"final_url", "redirect_count", "sha256", "size"}, label
    )
    require_exact(row["final_url"], expected_url, label + " final URL")
    require_exact(row["redirect_count"], 0, label + " redirects")
    require_exact(row["sha256"], expected_sha256, label + " digest")
    require_exact(row["size"], expected_size, label + " size")


def validate_direct_checkpoint(
    root: Path,
    direct: Mapping[str, Any],
    expected_identity: Optional[Mapping[str, Any]],
) -> Tuple[Dict[str, Any], bytes]:
    checkpoint, checkpoint_bytes = read_json(root / "checkpoint.json", "direct checkpoint")
    exact_keys(
        checkpoint,
        {
            "acquisition",
            "checkpoint_id",
            "credit_eligible",
            "gate_claims",
            "github",
            "manifests",
            "phase",
            "schema_version",
            "successful_capture_requires_review",
        },
        "direct checkpoint",
    )
    acquisition = exact_keys(
        checkpoint["acquisition"],
        {
            "collector_http_after_seal",
            "collector_http_downloaded_bytes",
            "collector_http_sealed",
            "network_isolation_claimed",
            "scope",
        },
        "direct acquisition",
    )
    require_exact(acquisition["collector_http_after_seal"], False, "direct post-seal HTTP")
    require_exact(acquisition["collector_http_sealed"], True, "direct acquisition seal")
    require_exact(acquisition["network_isolation_claimed"], False, "direct network claim")
    if not isinstance(acquisition["collector_http_downloaded_bytes"], int) or acquisition[
        "collector_http_downloaded_bytes"
    ] < 1:
        raise ClosureError("direct acquisition byte count is invalid")
    require_exact(checkpoint["checkpoint_id"], phase_one.CHECKPOINT_ID, "direct checkpoint ID")
    require_exact(checkpoint["phase"], "repository-direct", "direct phase ID")
    require_exact(checkpoint["schema_version"], SCHEMA_VERSION, "direct checkpoint schema")
    require_exact(checkpoint["credit_eligible"], False, "direct phase credit")
    require_exact(checkpoint["gate_claims"], {"RK-003": False, "RK-005": False}, "direct gate claims")
    require_exact(
        checkpoint["successful_capture_requires_review"], True, "direct review requirement"
    )
    github = exact_keys(
        checkpoint["github"], {"head_sha", "repository", "run_attempt", "run_id"}, "direct GitHub identity"
    )
    if expected_identity is None:
        require_exact(github["head_sha"], direct["head_sha"], "direct head SHA")
        require_exact(github["repository"], direct["github_repository"], "direct repository")
        require_exact(github["run_id"], direct["run_id"], "direct run ID")
        require_exact(github["run_attempt"], direct["run_attempt"], "direct run attempt")
        require_exact(
            hashlib.sha256(checkpoint_bytes).hexdigest(),
            direct["historical_checkpoint_sha256"],
            "historical direct checkpoint digest",
        )
    else:
        require_exact(dict(github), dict(expected_identity), "current direct/capture identity")
    manifests = checkpoint["manifests"]
    if not isinstance(manifests, list) or len(manifests) != len(DIRECT_MANIFEST_NAMES):
        raise ClosureError("direct checkpoint manifest coverage changed")
    observed_names = []
    for index, item in enumerate(manifests):
        row = exact_keys(item, {"path", "sha256", "size"}, "direct manifest {}".format(index))
        relative = phase_one.normalized_relative_path(row["path"], "direct manifest path")
        if relative.parts != (relative.name,):
            raise ClosureError("direct checkpoint manifest must be top-level")
        path = root / relative.name
        size, digest = sha256_file(path)
        require_exact(size, row["size"], relative.name + " size")
        require_exact(digest, row["sha256"], relative.name + " digest")
        observed_names.append(relative.name)
    require_exact(observed_names, DIRECT_MANIFEST_NAMES, "direct manifest order")
    return checkpoint, checkpoint_bytes


def validate_direct_bundle_manifests(
    root: Path, plan: Mapping[str, Any], toolchain: Mapping[str, Any]
) -> None:
    repositories, _ = read_json(root / "repository-snapshots.json", "repository snapshots")
    exact_keys(repositories, {"release_key", "repositories", "schema_version"}, "repository snapshots")
    require_exact(repositories["schema_version"], SCHEMA_VERSION, "repository snapshot schema")
    release_key = exact_keys(
        repositories["release_key"], {"download", "fingerprint", "path"}, "snapshot release key"
    )
    require_exact(release_key["fingerprint"], plan["release_key"]["fingerprint"], "release-key fingerprint")
    require_exact(release_key["path"], "archives/repositories/RPM-GPG-KEY-Rocky-10", "release-key path")
    validate_download_record(
        release_key["download"],
        plan["release_key"]["url"],
        plan["release_key"]["sha256"],
        plan["release_key"]["size"],
        "release-key download",
    )
    repository_rows = repositories["repositories"]
    if not isinstance(repository_rows, list) or len(repository_rows) != len(plan["repositories"]):
        raise ClosureError("repository snapshot count changed")
    for locked, item in zip(plan["repositories"], repository_rows):
        row = exact_keys(
            item,
            {
                "base_url",
                "id",
                "primary_download",
                "primary_open",
                "repomd",
                "repomd_download",
                "signature",
                "signature_download",
            },
            "repository snapshot",
        )
        require_exact(row["id"], locked["id"], "repository ID")
        require_exact(row["base_url"], locked["base_url"], "repository base URL")
        validate_download_record(
            row["repomd_download"],
            locked["repomd"]["url"],
            locked["repomd"]["sha256"],
            locked["repomd"]["size"],
            locked["id"] + " repomd download",
        )
        validate_download_record(
            row["signature_download"],
            locked["signature"]["url"],
            locked["signature"]["sha256"],
            locked["signature"]["size"],
            locked["id"] + " signature download",
        )
        validate_download_record(
            row["primary_download"],
            locked["base_url"] + locked["primary"]["href"],
            locked["primary"]["sha256"],
            locked["primary"]["size"],
            locked["id"] + " primary download",
        )
        primary_open = exact_keys(row["primary_open"], {"open_sha256", "open_size"}, "primary open identity")
        require_exact(primary_open, {"open_sha256": locked["primary"]["open_sha256"], "open_size": locked["primary"]["open_size"]}, "primary open identity")
        repomd = exact_keys(row["repomd"], {"primary", "revision"}, "repomd result")
        require_exact(repomd["primary"], locked["primary"], "repomd primary identity")
        require_exact(repomd["revision"], locked["repomd"]["revision"], "repomd revision")
        signature = exact_keys(
            row["signature"],
            {"status", "transcript_sha256", "transcript_size", "validsig_fingerprint"},
            "repomd signature",
        )
        require_exact(signature["status"], "verified", "repomd signature status")
        require_exact(signature["validsig_fingerprint"], plan["release_key"]["fingerprint"], "repomd signer")

    direct, _ = read_json(root / "direct-rpms.json", "direct RPM manifest")
    exact_keys(
        direct,
        {"all_archives_verified", "all_header_signatures_verified", "artifact_count", "artifacts", "scope", "schema_version"},
        "direct RPM manifest",
    )
    require_exact(direct["all_archives_verified"], True, "direct archive verification")
    require_exact(direct["all_header_signatures_verified"], True, "direct signature verification")
    require_exact(direct["schema_version"], SCHEMA_VERSION, "direct RPM schema")
    require_exact(direct["artifact_count"], len(toolchain["direct_artifacts"]), "direct RPM count")
    artifacts = direct["artifacts"]
    if not isinstance(artifacts, list) or len(artifacts) != len(toolchain["direct_artifacts"]):
        raise ClosureError("direct RPM artifact coverage changed")
    for locked, item in zip(toolchain["direct_artifacts"], artifacts):
        row = exact_keys(
            item,
            {"arch", "archive_path", "download", "metadata", "name", "nevra", "repository_id", "signature"},
            "direct RPM artifact",
        )
        for field in ("arch", "name", "nevra", "repository_id"):
            require_exact(row[field], locked[field], "direct RPM " + field)
        filename = PurePosixPath(locked["repository_location"]).name
        require_exact(row["archive_path"], "archives/direct-rpms/{}".format(filename), "direct RPM path")
        repository = next(value for value in plan["repositories"] if value["id"] == locked["repository_id"])
        validate_download_record(
            row["download"],
            repository["base_url"] + locked["repository_location"],
            locked["sha256"],
            locked["size"],
            locked["nevra"] + " download",
        )
        metadata = exact_keys(row["metadata"], {"location", "sha256", "size"}, "direct RPM metadata")
        require_exact(metadata, {"location": locked["repository_location"], "sha256": locked["sha256"], "size": locked["size"]}, "direct RPM metadata")
        signature = exact_keys(
            row["signature"],
            {"header_signature_algorithm", "signer_fingerprint", "signer_key_id", "status", "transcript_sha256", "transcript_size"},
            "direct RPM signature",
        )
        require_exact(signature["status"], "verified", "direct RPM signature status")
        require_exact(signature["signer_fingerprint"], plan["release_key"]["fingerprint"], "direct RPM signer")

    environment, _ = read_json(root / "environment.json", "direct environment")
    exact_keys(
        environment,
        {"architecture", "bootstrap", "bootstrap_package_count", "bootstrap_packages_sha256", "committed_inputs", "container_image", "container_manifest_digest", "container_platform", "github", "os_release", "tool_versions"},
        "direct environment",
    )
    require_exact(environment["architecture"], "x86_64", "direct environment architecture")
    require_exact(environment["container_image"], phase_one.CONTAINER_IMAGE, "direct container image")
    require_exact(
        environment["container_manifest_digest"],
        plan["container"]["manifest_digest"],
        "direct container manifest",
    )
    require_exact(environment["container_platform"], plan["container"]["platform"], "direct container platform")
    github = exact_keys(
        environment["github"], {"head_sha", "repository", "run_attempt", "run_id"}, "direct environment GitHub identity"
    )
    checkpoint, _ = read_json(root / "checkpoint.json", "direct checkpoint")
    require_exact(dict(github), checkpoint["github"], "direct environment/checkpoint identity")
    require_exact(environment["os_release"], {"id": "rocky", "version_id": "10.2"}, "direct environment OS")
    bootstrap = exact_keys(
        environment["bootstrap"],
        {"after_package_manifest_sha256", "local_rpm_install_verified", "manifest_sha256"},
        "direct bootstrap environment",
    )
    require_exact(bootstrap["local_rpm_install_verified"], True, "direct bootstrap install")
    for field in ("after_package_manifest_sha256", "manifest_sha256"):
        if not isinstance(bootstrap[field], str) or not HEX_SHA256.fullmatch(bootstrap[field]):
            raise ClosureError("direct bootstrap {} is not a SHA-256".format(field))
    if not isinstance(environment["bootstrap_package_count"], int) or environment[
        "bootstrap_package_count"
    ] < 1:
        raise ClosureError("direct bootstrap package count is invalid")
    if not isinstance(environment["bootstrap_packages_sha256"], str) or not HEX_SHA256.fullmatch(
        environment["bootstrap_packages_sha256"]
    ):
        raise ClosureError("direct bootstrap inventory digest is malformed")
    expected_input_paths = [
        value.as_posix()
        for value in (
            phase_one.PLAN_PATH,
            phase_one.TOOLCHAIN_LOCK_PATH,
            phase_one.CONFIG_POLICY_PATH,
            phase_one.CONFIG_FRAGMENT_PATH,
            phase_one.SOURCE_LOCK_PATH,
            phase_one.PATCH_SERIES_PATH,
            phase_one.PLATFORM_VALIDATOR_PATH,
            phase_one.SOURCE_VALIDATOR_PATH,
            phase_one.CAPTURE_SCRIPT_PATH,
            phase_one.WORKFLOW_PATH,
        )
    ]
    committed = environment["committed_inputs"]
    if not isinstance(committed, list) or len(committed) != len(expected_input_paths):
        raise ClosureError("direct committed-input coverage changed")
    for index, (expected_path, item) in enumerate(zip(expected_input_paths, committed)):
        row = exact_keys(item, {"path", "sha256", "size"}, "direct committed input {}".format(index))
        require_exact(row["path"], expected_path, "direct committed-input path")
        if not isinstance(row["sha256"], str) or not HEX_SHA256.fullmatch(row["sha256"]):
            raise ClosureError("direct committed-input digest is malformed")
        if not isinstance(row["size"], int) or row["size"] < 1:
            raise ClosureError("direct committed-input size is invalid")
    tool_versions = exact_keys(
        environment["tool_versions"], {"gpg", "python", "rpm", "rpmspec"}, "direct tool versions"
    )
    expected_commands = {
        "gpg": ["gpg", "--version"],
        "python": ["python3", "--version"],
        "rpm": ["rpm", "--version"],
        "rpmspec": ["rpmspec", "--version"],
    }
    for name, command in expected_commands.items():
        row = exact_keys(
            tool_versions[name], {"command", "output_sha256", "output_size"}, "direct {} version".format(name)
        )
        require_exact(row["command"], command, "direct {} command".format(name))
        if not isinstance(row["output_sha256"], str) or not HEX_SHA256.fullmatch(row["output_sha256"]):
            raise ClosureError("direct tool version digest is malformed")
        if not isinstance(row["output_size"], int) or row["output_size"] < 1:
            raise ClosureError("direct tool version output is empty")
    blockers, _ = read_json(root / "blockers.json", "direct blockers")
    exact_keys(
        blockers,
        {"config_lock_blockers_at_capture", "gate_claims", "phase_blockers", "source_lock_blockers_at_capture", "source_lock_credit_eligible_at_capture", "toolchain_lock_blockers_at_capture"},
        "direct blockers",
    )
    require_exact(blockers["gate_claims"], {"RK-003": False, "RK-005": False}, "direct blocker gate claims")
    for field in (
        "config_lock_blockers_at_capture",
        "phase_blockers",
        "toolchain_lock_blockers_at_capture",
    ):
        values = blockers[field]
        if not isinstance(values, list) or not values or not all(
            isinstance(value, str) and value.strip() for value in values
        ):
            raise ClosureError("direct blocker list is empty or malformed: {}".format(field))
    source_blockers = blockers["source_lock_blockers_at_capture"]
    if not isinstance(source_blockers, list) or not all(
        isinstance(value, str) and value.strip() for value in source_blockers
    ):
        raise ClosureError("direct source-lock blocker list is malformed")
    require_exact(
        blockers["source_lock_credit_eligible_at_capture"],
        not source_blockers,
        "direct source-lock credit",
    )


def validate_direct_root(
    root: Path,
    contract: Mapping[str, Any],
    expected_identity: Optional[Mapping[str, Any]] = None,
    expected_files: Optional[Sequence[str]] = None,
    plan: Optional[Mapping[str, Any]] = None,
    toolchain: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    requested_root = root
    if requested_root.is_symlink() or not requested_root.is_dir():
        raise ClosureError("direct phase root must be a regular directory")
    root = requested_root.resolve()
    verify_sha256sums(root, expected_files, "direct bundle")
    direct = contract["direct_phase"]
    validate_direct_checkpoint(root, direct, expected_identity)
    build, build_bytes = read_json(root / "build-requirements.json", "BuildRequires")
    exact_keys(
        build,
        {
            "closure_complete",
            "collector_http_sealed_before_derivation",
            "direct_nevras",
            "effective_buildrequires",
            "kernel_spec_sha256",
            "network_isolation_claimed",
            "resolution_roots",
            "reviewed_rocky_rust_additions",
            "reviewed_source_change_applied",
            "rpmspec_output_sha256",
            "rpm_showrc_sha256",
            "schema_version",
            "source_spec_condition",
            "transitive_resolution_status",
        },
        "BuildRequires",
    )
    resolution_inputs = {
        key: build.get(key)
        for key in (
            "direct_nevras",
            "effective_buildrequires",
            "kernel_spec_sha256",
            "resolution_roots",
            "reviewed_rocky_rust_additions",
        )
    }
    semantic_digest = hashlib.sha256(
        phase_one.canonical_json_bytes(resolution_inputs)
    ).hexdigest()
    require_exact(
        semantic_digest,
        direct["resolution_inputs_sha256"],
        "resolution input digest",
    )
    if expected_identity is None:
        require_exact(
            hashlib.sha256(build_bytes).hexdigest(),
            direct["historical_build_requirements_sha256"],
            "historical BuildRequires digest",
        )
    require_exact(len(build.get("resolution_roots", [])), direct["resolution_root_count"], "resolution roots")
    require_exact(len(build.get("effective_buildrequires", [])), direct["effective_buildrequires_count"], "effective BuildRequires")
    require_exact(len(build.get("reviewed_rocky_rust_additions", [])), direct["reviewed_rocky_rust_count"], "reviewed Rust roots")
    require_exact(build.get("closure_complete"), False, "direct closure state")
    require_exact(build["collector_http_sealed_before_derivation"], True, "direct derivation seal")
    require_exact(build["network_isolation_claimed"], False, "direct network claim")
    require_exact(build["reviewed_source_change_applied"], False, "reviewed source change state")
    require_exact(build["schema_version"], SCHEMA_VERSION, "BuildRequires schema")
    require_exact(build["transitive_resolution_status"], "required-missing", "direct closure status")
    if plan is not None and toolchain is not None:
        require_exact(build["direct_nevras"], toolchain["closure"]["direct_nevras"], "direct NEVRA order")
        require_exact(
            build["reviewed_rocky_rust_additions"],
            plan["resolution_policy"]["reviewed_rocky_rust_buildrequires"],
            "reviewed Rust additions",
        )
        roots = build["resolution_roots"]
        if not isinstance(roots, list):
            raise ClosureError("resolution roots must be a list")
        for index, item in enumerate(roots):
            exact_keys(item, {"kind", "value"}, "resolution root {}".format(index))
        expected_roots = []
        expected_roots.extend(
            {"kind": "rocky-effective-spec", "value": item}
            for item in build["effective_buildrequires"]
        )
        expected_roots.extend(
            {"kind": "reviewed-rocky-rust", "value": item}
            for item in build["reviewed_rocky_rust_additions"]
        )
        expected_roots.extend(
            {"kind": "locked-direct-nevra", "value": item}
            for item in build["direct_nevras"]
        )
        require_exact(roots, expected_roots, "resolution-root construction")
        for field in ("kernel_spec_sha256", "rpmspec_output_sha256", "rpm_showrc_sha256"):
            if not isinstance(build[field], str) or not HEX_SHA256.fullmatch(build[field]):
                raise ClosureError("BuildRequires {} is not a SHA-256".format(field))
        require_exact(
            build["source_spec_condition"],
            toolchain["source_spec_observation"]["rust_buildrequires_condition"],
            "source spec condition",
        )
        validate_direct_bundle_manifests(root, plan, toolchain)
    return build


def primary_index(primary_path: Path, repository_id: str) -> Dict[str, Dict[str, Any]]:
    index: Dict[str, Dict[str, Any]] = {}
    count = 0
    try:
        stream = gzip.open(str(primary_path), "rb")
        context = ET.iterparse(stream, events=("end",))
        for _, element in context:
            if element.tag != "{" + phase_one.COMMON_NS + "}package":
                continue
            count += 1
            if count > MAX_PRIMARY_PACKAGES:
                raise ClosureError("primary metadata package bound exceeded")
            name = element.findtext("{" + phase_one.COMMON_NS + "}name")
            arch = element.findtext("{" + phase_one.COMMON_NS + "}arch")
            version = element.find("{" + phase_one.COMMON_NS + "}version")
            checksum = element.find("{" + phase_one.COMMON_NS + "}checksum")
            location = element.find("{" + phase_one.COMMON_NS + "}location")
            size = element.find("{" + phase_one.COMMON_NS + "}size")
            if None in (version, checksum, location, size) or not name or not arch:
                raise ClosureError("primary metadata package is incomplete")
            if checksum.get("type") != "sha256" or checksum.get("pkgid") != "YES":
                raise ClosureError("primary package checksum is not a SHA-256 pkgid")
            epoch = version.get("epoch") or "0"
            ver = version.get("ver")
            rel = version.get("rel")
            href = location.get("href")
            package_size = size.get("package")
            if not ver or not rel or not href or not package_size or not package_size.isdigit():
                raise ClosureError("primary metadata identity is malformed")
            normalized_href = phase_one.normalized_relative_path(
                href, "primary package location"
            )
            if normalized_href.parts[0] != "Packages" or normalized_href.suffix != ".rpm":
                raise ClosureError("primary package location has an unsafe layout")
            nevra = "{}-{}:{}-{}.{}".format(name, epoch, ver, rel, arch)
            row = {
                "arch": arch,
                "nevra": nevra,
                "repository_id": repository_id,
                "repository_location": normalized_href.as_posix(),
                "sha256": (checksum.text or "").strip(),
                "size": int(package_size),
            }
            if not HEX_SHA256.fullmatch(row["sha256"]):
                raise ClosureError("primary package digest is malformed")
            previous = index.get(nevra)
            if previous is not None and previous != row:
                raise ClosureError("primary metadata has ambiguous NEVRA {}".format(nevra))
            index[nevra] = row
            element.clear()
    except (OSError, EOFError, ET.ParseError) as exc:
        raise ClosureError("cannot parse primary metadata: {}".format(exc)) from exc
    finally:
        try:
            stream.close()
        except (NameError, OSError):
            pass
    if not index:
        raise ClosureError("primary metadata contains no packages")
    return index


def load_primary_indexes(
    snapshot_roots: Mapping[str, Path], plan: Mapping[str, Any]
) -> Dict[str, Dict[str, Any]]:
    combined: Dict[str, Dict[str, Any]] = {}
    for repository in plan["repositories"]:
        repository_id = repository["id"]
        href = PurePosixPath(repository["primary"]["href"])
        path = snapshot_roots[repository_id].joinpath(*href.parts)
        size, digest = sha256_file(path)
        require_exact(size, repository["primary"]["size"], "primary compressed size")
        require_exact(digest, repository["primary"]["sha256"], "primary compressed digest")
        phase_one.verify_primary_open_identity(
            path,
            repository["primary"]["open_sha256"],
            repository["primary"]["open_size"],
        )
        for nevra, row in primary_index(path, repository_id).items():
            previous = combined.get(nevra)
            if previous is not None and previous != row:
                raise ClosureError("repository snapshots disagree for {}".format(nevra))
            combined[nevra] = row
    return combined


def repomd_data_rows(
    repomd_path: Path, repository: Mapping[str, Any]
) -> List[Dict[str, Any]]:
    data = read_regular_bytes(repomd_path, "signed repomd")
    try:
        phase_one.parse_repomd(data, repository)
    except phase_one.EvidenceError as exc:
        raise ClosureError(str(exc)) from exc
    if b"<!DOCTYPE" in data.upper() or b"<!ENTITY" in data.upper():
        raise ClosureError("repomd XML declarations are forbidden")
    try:
        root = ET.fromstring(data)
    except ET.ParseError as exc:
        raise ClosureError("cannot parse repomd data rows: {}".format(exc)) from exc
    namespace = "{" + phase_one.REPO_NS + "}"
    rows: List[Dict[str, Any]] = []
    seen_types = set()
    seen_locations = set()
    for element in root.findall(namespace + "data"):
        data_type = element.get("type")
        checksum = element.find(namespace + "checksum")
        open_checksum = element.find(namespace + "open-checksum")
        location = element.find(namespace + "location")
        size_text = element.findtext(namespace + "size")
        open_size_text = element.findtext(namespace + "open-size")
        if (
            not data_type
            or checksum is None
            or checksum.get("type") != "sha256"
            or location is None
            or not size_text
            or not size_text.isdigit()
        ):
            raise ClosureError("repomd data row is incomplete")
        if data_type in seen_types:
            raise ClosureError("repomd data type is duplicated: {}".format(data_type))
        relative = phase_one.normalized_relative_path(
            location.get("href"), "repomd data location"
        )
        if relative.parts[0] != "repodata" or relative.as_posix() in seen_locations:
            raise ClosureError("repomd data location is duplicated or unsafe")
        digest = (checksum.text or "").strip()
        if not HEX_SHA256.fullmatch(digest):
            raise ClosureError("repomd data digest is malformed")
        size = int(size_text)
        if not 1 <= size <= MAX_METADATA_OBJECT_BYTES:
            raise ClosureError("repomd data compressed size exceeds its bound")
        if (open_checksum is None) != (open_size_text is None):
            raise ClosureError("repomd open identity is incomplete")
        open_digest = None
        open_size = None
        if open_checksum is not None:
            if open_checksum.get("type") != "sha256" or not open_size_text or not open_size_text.isdigit():
                raise ClosureError("repomd open identity is malformed")
            open_digest = (open_checksum.text or "").strip()
            open_size = int(open_size_text)
            if not HEX_SHA256.fullmatch(open_digest) or not 1 <= open_size <= MAX_METADATA_OPEN_BYTES:
                raise ClosureError("repomd open identity exceeds its bound")
        rows.append(
            {
                "href": relative.as_posix(),
                "open_sha256": open_digest,
                "open_size": open_size,
                "sha256": digest,
                "size": size,
                "type": data_type,
            }
        )
        seen_types.add(data_type)
        seen_locations.add(relative.as_posix())
    if not rows or len(rows) > MAX_REPOMD_OBJECTS:
        raise ClosureError("repomd data row count is empty or exceeds its bound")
    primary = [row for row in rows if row["type"] == "primary"]
    if len(primary) != 1:
        raise ClosureError("repomd must contain exactly one primary object")
    require_exact(primary[0]["href"], repository["primary"]["href"], "primary metadata href")
    require_exact(primary[0]["sha256"], repository["primary"]["sha256"], "primary metadata digest")
    require_exact(primary[0]["size"], repository["primary"]["size"], "primary metadata size")
    require_exact(primary[0]["open_sha256"], repository["primary"]["open_sha256"], "primary open digest")
    require_exact(primary[0]["open_size"], repository["primary"]["open_size"], "primary open size")
    return rows


def verify_metadata_open_identity(path: Path, row: Mapping[str, Any]) -> bool:
    expected_digest = row["open_sha256"]
    expected_size = row["open_size"]
    if expected_digest is None:
        return False
    suffix = PurePosixPath(row["href"]).suffix
    if suffix == ".gz":
        stream = gzip.open(str(path), "rb")
    elif suffix == ".bz2":
        stream = bz2.open(str(path), "rb")
    elif suffix == ".xz":
        stream = lzma.open(str(path), "rb")
    elif suffix == ".zck" and shutil.which("unzck") is None:
        # repomd signs the compressed object identity independently.  The
        # minimal pinned container need not carry the optional zchunk CLI, so
        # retain the exact object but do not overclaim its open identity.
        return False
    elif suffix in (".zst", ".zck"):
        arguments = (
            ["zstd", "--decompress", "--stdout", str(path)]
            if suffix == ".zst"
            else ["unzck", "--stdout", str(path)]
        )
        try:
            process = subprocess.Popen(
                arguments, stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
        except OSError as exc:
            raise ClosureError("metadata decompressor is unavailable: {}".format(exc)) from exc
        if process.stdout is None or process.stderr is None:
            process.kill()
            raise ClosureError("metadata decompressor pipes are unavailable")
        digest = hashlib.sha256()
        size = 0
        while True:
            chunk = process.stdout.read(1024 * 1024)
            if not chunk:
                break
            size += len(chunk)
            if size > expected_size or size > MAX_METADATA_OPEN_BYTES:
                process.kill()
                process.wait()
                raise ClosureError("metadata expands beyond its signed bound")
            digest.update(chunk)
        stderr = process.stderr.read()
        return_code = process.wait()
        if return_code != 0:
            raise ClosureError("metadata decompressor failed: {}".format(stderr.decode("utf-8", errors="replace").strip()))
        if stderr:
            raise ClosureError("metadata decompressor wrote stderr")
        require_exact(size, expected_size, "metadata open size")
        require_exact(digest.hexdigest(), expected_digest, "metadata open digest")
        return True
    else:
        size, digest = sha256_file(path)
        require_exact(size, expected_size, "uncompressed metadata size")
        require_exact(digest, expected_digest, "uncompressed metadata digest")
        return True
    digest = hashlib.sha256()
    size = 0
    try:
        with stream:
            while True:
                chunk = stream.read(1024 * 1024)
                if not chunk:
                    break
                size += len(chunk)
                if size > expected_size or size > MAX_METADATA_OPEN_BYTES:
                    raise ClosureError("metadata expands beyond its signed bound")
                digest.update(chunk)
    except (OSError, EOFError, lzma.LZMAError) as exc:
        raise ClosureError("cannot decompress signed metadata: {}".format(exc)) from exc
    require_exact(size, expected_size, "metadata open size")
    require_exact(digest.hexdigest(), expected_digest, "metadata open digest")
    return True


def materialize_snapshot_repositories(
    direct_root: Path,
    output_root: Path,
    plan: Mapping[str, Any],
    gpg_keyring: Path,
) -> Tuple[Dict[str, Path], List[Dict[str, Any]]]:
    session = phase_one.NetworkSession(
        plan["network_policy"]["collector_http_allowed_hosts_before_seal"]
    )
    roots: Dict[str, Path] = {}
    manifests: List[Dict[str, Any]] = []
    for repository in plan["repositories"]:
        repository_id = repository["id"]
        source_root = direct_root / "archives" / "repositories" / repository_id
        relative_root = PurePosixPath("archives/snapshot-repositories") / repository_id
        snapshot_root = output_root.joinpath(*relative_root.parts)
        roots[repository_id] = snapshot_root
        repomd_relative = relative_root / "repodata/repomd.xml"
        signature_relative = relative_root / "repodata/repomd.xml.asc"
        repomd_path = copy_archive(source_root / "repomd.xml", output_root, repomd_relative)
        signature_path = copy_archive(
            source_root / "repomd.xml.asc", output_root, signature_relative
        )
        size, digest = sha256_file(repomd_path)
        require_exact(size, repository["repomd"]["size"], repository_id + " repomd size")
        require_exact(digest, repository["repomd"]["sha256"], repository_id + " repomd digest")
        signature, transcript = phase_one.verify_repomd_signature(
            repomd_path,
            signature_path,
            gpg_keyring,
            plan["release_key"]["fingerprint"],
        )
        phase_one.write_output_bytes(
            output_root,
            PurePosixPath("transcripts/snapshot-repomd") / (repository_id + ".gpgv.txt"),
            transcript,
        )
        metadata_rows = []
        for row in repomd_data_rows(repomd_path, repository):
            href = PurePosixPath(row["href"])
            target_relative = relative_root / href
            if row["type"] == "primary":
                source = source_root / href.name
                target = copy_archive(source, output_root, target_relative)
                download = {
                    "final_url": repository["base_url"] + href.as_posix(),
                    "redirect_count": 0,
                    "sha256": row["sha256"],
                    "size": row["size"],
                    "source": "verified repository-direct archive",
                }
            else:
                target = phase_one.output_path(output_root, target_relative)
                download = session.download_exact(
                    repository["base_url"] + href.as_posix(),
                    target,
                    row["sha256"],
                    row["size"],
                    MAX_METADATA_OBJECT_BYTES,
                )
                download["source"] = "bounded no-redirect HTTPS acquisition"
            size, digest = sha256_file(target)
            require_exact(size, row["size"], "signed metadata size")
            require_exact(digest, row["sha256"], "signed metadata digest")
            observed = dict(row)
            observed["archive_path"] = target_relative.as_posix()
            observed["download"] = download
            observed["open_identity_verified"] = verify_metadata_open_identity(target, row)
            observed["signed_compressed_identity_verified"] = True
            metadata_rows.append(observed)
        manifests.append(
            {
                "base_url": repository["base_url"],
                "id": repository_id,
                "local_repository_path": relative_root.as_posix(),
                "metadata": metadata_rows,
                "repomd_sha256": repository["repomd"]["sha256"],
                "repomd_signature": signature,
            }
        )
    session.seal()
    if not session.sealed:
        raise ClosureError("metadata acquisition did not seal")
    return roots, manifests


def dnf_base_arguments(installroot: Path, cache_root: str) -> List[str]:
    return [
        "dnf",
        "--noplugins",
        "-y",
        "--config=/dev/null",
        "--installroot",
        str(installroot),
        "--releasever=10.2",
        "--setopt=module_platform_id=platform:el10",
        "--setopt=reposdir=/dev/null",
        "--setopt=install_weak_deps=False",
        "--setopt=keepcache=True",
        "--setopt=cachedir={}".format(cache_root),
        "--setopt=metadata_expire=never",
        "--setopt=strict=True",
        "--setopt=best=True",
        "--setopt=skip_if_unavailable=False",
        "--setopt=gpgcheck=False",
        "--setopt=repo_gpgcheck=False",
        "--disablerepo=*",
    ]


def dnf_repository_id(repository: Mapping[str, Any]) -> str:
    repository_id = repository["id"]
    if not isinstance(repository_id, str) or not re.fullmatch(
        r"[a-z0-9][a-z0-9_-]*", repository_id
    ):
        raise ClosureError("locked DNF repository ID is unsafe")
    return "rk003-snapshot-" + repository_id


def online_command(
    installroot: Path,
    repositories: Sequence[Mapping[str, Any]],
    snapshot_roots: Mapping[str, Path],
    roots: Sequence[str],
) -> List[str]:
    arguments = dnf_base_arguments(installroot, "/var/cache/dnf")
    for repository in repositories:
        snapshot_root = snapshot_roots[repository["id"]]
        command_repository_id = dnf_repository_id(repository)
        if not snapshot_root.is_absolute() or snapshot_root.is_symlink() or not snapshot_root.is_dir():
            raise ClosureError("snapshot repository root is unsafe")
        local_url = "file://" + snapshot_root.as_posix()
        arguments.append(
            "--repofrompath={},{}".format(command_repository_id, local_url)
        )
        arguments.append(
            "--setopt={}.baseurl={},{}".format(
                command_repository_id, local_url, repository["base_url"]
            )
        )
        arguments.append(
            "--setopt={}.skip_if_unavailable=False".format(command_repository_id)
        )
        arguments.append("--enablerepo={}".format(command_repository_id))
    arguments.extend(["install", "--downloadonly", "--"])
    arguments.extend(roots)
    return arguments


def snapshot_solve_command(
    installroot: Path,
    repositories: Sequence[Mapping[str, Any]],
    snapshot_roots: Mapping[str, Path],
    roots: Sequence[str],
) -> List[str]:
    arguments = dnf_base_arguments(installroot, "/var/cache/dnf")
    for repository in repositories:
        snapshot_root = snapshot_roots[repository["id"]]
        command_repository_id = dnf_repository_id(repository)
        if not snapshot_root.is_absolute() or snapshot_root.is_symlink() or not snapshot_root.is_dir():
            raise ClosureError("snapshot repository root is unsafe")
        local_url = "file://" + snapshot_root.as_posix()
        arguments.append(
            "--repofrompath={},{}".format(command_repository_id, local_url)
        )
        arguments.append(
            "--setopt={}.skip_if_unavailable=False".format(command_repository_id)
        )
        arguments.append("--enablerepo={}".format(command_repository_id))
    arguments.extend(["install", "--"])
    arguments.extend(roots)
    return arguments


def offline_command(
    installroot: Path, rpm_paths: Sequence[Path]
) -> List[str]:
    arguments = dnf_base_arguments(installroot, "/var/cache/dnf")
    arguments.extend(["--cacheonly", "install", "--"])
    arguments.extend(str(path) for path in rpm_paths)
    return arguments


def run_command(
    arguments: Sequence[str], env: Optional[Mapping[str, str]] = None
) -> Tuple[bytes, bytes]:
    try:
        completed = subprocess.run(
            list(arguments),
            check=True,
            env=dict(env) if env is not None else None,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except OSError as exc:
        raise ClosureError("command unavailable: {}: {}".format(arguments[0], exc)) from exc
    except subprocess.CalledProcessError as exc:
        raise ClosureError(
            "command failed ({}): {}".format(
                " ".join(arguments), exc.stderr.decode("utf-8", errors="replace").strip()
            )
        ) from exc
    return completed.stdout, completed.stderr


def command_transcript(
    arguments: Sequence[str], stdout: bytes, stderr: bytes
) -> bytes:
    command = " ".join(shlex.quote(item) for item in arguments).encode("utf-8")
    return b"command: " + command + b"\nstdout:\n" + stdout + b"stderr:\n" + stderr


def verify_expected_version(
    probe_id: str, expected: Optional[str], output: bytes, owner_nevra: str
) -> None:
    if expected is None:
        return
    try:
        text = output.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ClosureError("{} version output is not UTF-8".format(probe_id)) from exc
    version = re.escape(expected)
    owner_version = re.compile(r"-[0-9]+:{}-".format(version))
    if owner_version.search(owner_nevra) is None:
        raise ClosureError(
            "{} binary owner does not identify exact version {}".format(
                probe_id, expected
            )
        )

    # rustfmt and clippy report their upstream component versions rather than the
    # Rust RPM version carried by expected_version.  Their exact RPM version is
    # still enforced above; the command output must identify the expected tool.
    component_prefixes = {"clippy": "clippy ", "rustfmt": "rustfmt "}
    component_prefix = component_prefixes.get(probe_id)
    if component_prefix is not None:
        if not text.startswith(component_prefix):
            raise ClosureError("{} output does not identify the tool".format(probe_id))
        return

    output_version = re.compile(r"(?<![0-9.]){}(?![A-Za-z0-9.])".format(version))
    if output_version.search(text) is None:
        raise ClosureError(
            "{} output does not identify exact version {}".format(probe_id, expected)
        )


def expected_probe_owner(probe_id: str, locked_owner_nevra: str) -> str:
    if probe_id != "llvm":
        return locked_owner_nevra
    require_exact(
        locked_owner_nevra,
        LOCKED_LLVM_PROBE_OWNER_NEVRA,
        "current LLVM probe authority mapping",
    )
    return LLVM_CONFIG_OWNER_NEVRA


def loaded_libclang_path(stderr: bytes) -> str:
    try:
        stderr_text = stderr.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ClosureError("dynamic-loader evidence is not UTF-8") from exc
    matches = []
    for line in stderr_text.splitlines():
        match = re.search(r"calling init:\s+(/\S*libclang\.so\S*)\s*$", line)
        if match is not None:
            matches.append(match.group(1))
    if len(matches) != 1:
        raise ClosureError("dynamic-loader evidence does not identify one libclang")
    return matches[0]


def stable_environment(base: Mapping[str, str]) -> Dict[str, str]:
    result = dict(base)
    result.update({"LANG": "C", "LC_ALL": "C", "TZ": "UTC"})
    return result


def acquisition_environment(base: Mapping[str, str]) -> Dict[str, str]:
    result = stable_environment(base)
    for key in (
        "ALL_PROXY",
        "FTP_PROXY",
        "HTTP_PROXY",
        "HTTPS_PROXY",
        "NO_PROXY",
        "all_proxy",
        "ftp_proxy",
        "http_proxy",
        "https_proxy",
        "no_proxy",
    ):
        result.pop(key, None)
    return result


def private_environment(base: Mapping[str, str]) -> Dict[str, str]:
    return stable_environment(phase_one.subprocess_network_defense_env(base))


def rpm_nevra(path: Path) -> str:
    stdout, stderr = run_command(["rpm", "-qp", "--qf", RPM_NEVRA_QUERY, str(path)])
    if stderr:
        raise ClosureError("RPM identity query wrote stderr")
    try:
        rows = stdout.decode("utf-8").splitlines()
    except UnicodeDecodeError as exc:
        raise ClosureError("RPM identity is not UTF-8") from exc
    if len(rows) != 1 or not rows[0]:
        raise ClosureError("RPM identity query is ambiguous")
    return rows[0]


def installed_nevras(root: Path) -> List[str]:
    stdout, stderr = run_command(
        ["rpm", "--root", str(root), "-qa", "--qf", RPM_NEVRA_QUERY]
    )
    if stderr:
        raise ClosureError("installroot inventory wrote stderr")
    rows = sorted(row for row in stdout.decode("utf-8").splitlines() if row)
    if not rows or len(rows) != len(set(rows)):
        raise ClosureError("installroot inventory is empty or ambiguous")
    return rows


def verify_transitive_inventory(
    installed: Sequence[str], direct_nevras: Sequence[str]
) -> None:
    if len(installed) != len(set(installed)):
        raise ClosureError("installed closure contains duplicate NEVRAs")
    if len(direct_nevras) != len(set(direct_nevras)):
        raise ClosureError("locked direct NEVRAs contain duplicates")
    missing = sorted(set(direct_nevras) - set(installed))
    if missing:
        raise ClosureError("installed closure omits locked direct NEVRAs: {}".format(missing))
    if len(installed) <= len(direct_nevras):
        raise ClosureError("installed closure contains no transitive packages")


def verify_cached_repomd(
    cache_root: Path, repositories: Sequence[Mapping[str, Any]]
) -> None:
    if cache_root.is_symlink() or not cache_root.is_dir():
        raise ClosureError("DNF cache root is unsafe")
    candidates = []
    for path in cache_root.rglob("repomd.xml"):
        resolved = path.resolve()
        if (
            path.is_symlink()
            or path != resolved
            or os.path.commonpath((str(cache_root.resolve()), str(resolved)))
            != str(cache_root.resolve())
            or not path.is_file()
        ):
            raise ClosureError("DNF cached repomd path is unsafe")
        candidates.append(path)
    if len(candidates) != len(repositories):
        raise ClosureError("DNF did not cache exactly one repomd per snapshot")
    expected = sorted(repository["repomd"]["sha256"] for repository in repositories)
    observed = sorted(sha256_file(path)[1] for path in candidates)
    require_exact(observed, expected, "DNF cached exact repomd identities")


def repository_for_metadata(
    metadata: Mapping[str, Any], repositories: Sequence[Mapping[str, Any]]
) -> Mapping[str, Any]:
    matches = [
        repository
        for repository in repositories
        if repository["id"] == metadata["repository_id"]
    ]
    if len(matches) != 1:
        raise ClosureError("closure RPM repository identity is ambiguous")
    return matches[0]


def copy_archive(source: Path, output_root: Path, relative: PurePosixPath) -> Path:
    target = phase_one.output_path(output_root, relative)
    target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    if target.exists() or target.is_symlink():
        raise ClosureError("archive output already exists")
    input_descriptor = open_regular_read(source, "archive source")
    output_descriptor = -1
    created = False
    output_identity = None
    try:
        output_descriptor = open_regular_create(target, "archive output")
        created = True
        if not stat.S_ISREG(os.fstat(output_descriptor).st_mode):
            raise ClosureError("archive output is not a regular file")
        output_identity = regular_identity(os.fstat(output_descriptor))[:2]
        with os.fdopen(input_descriptor, "rb") as input_stream, os.fdopen(
            output_descriptor, "wb"
        ) as output_stream:
            input_descriptor = -1
            output_descriptor = -1
            input_identity = regular_identity(os.fstat(input_stream.fileno()))
            shutil.copyfileobj(input_stream, output_stream, 1024 * 1024)
            if regular_identity(os.fstat(input_stream.fileno())) != input_identity:
                raise ClosureError("archive source changed while it was copied")
            if output_stream.tell() != input_identity[2]:
                raise ClosureError("archive copy size differs from its source")
            output_stream.flush()
            os.fsync(output_stream.fileno())
            os.fchmod(output_stream.fileno(), 0o400)
    except OSError as exc:
        raise ClosureError("cannot safely archive {}: {}".format(relative, exc)) from exc
    finally:
        if input_descriptor >= 0:
            os.close(input_descriptor)
        if output_descriptor >= 0:
            os.close(output_descriptor)
        if created:
            try:
                final_status = os.lstat(str(target))
            except OSError as exc:
                raise ClosureError("archive output disappeared during publication") from exc
            if (
                not stat.S_ISREG(final_status.st_mode)
                or (final_status.st_dev, final_status.st_ino) != output_identity
            ):
                raise ClosureError("archive output changed during publication")
    return target


def chroot_regular_file(root: Path, path: str, label: str) -> Path:
    requested = PurePosixPath(path)
    if not requested.is_absolute() or any(
        part in ("", ".", "..") for part in requested.parts[1:]
    ):
        raise ClosureError("{} path is unsafe".format(label))
    stdout, stderr = run_command(
        ["chroot", str(root), "/usr/bin/readlink", "-f", "--", requested.as_posix()]
    )
    if stderr:
        raise ClosureError("{} path resolution wrote stderr".format(label))
    rows = stdout.decode("utf-8").splitlines()
    if len(rows) != 1:
        raise ClosureError("{} path resolution is ambiguous".format(label))
    canonical = PurePosixPath(rows[0])
    if not canonical.is_absolute() or any(
        part in ("", ".", "..") for part in canonical.parts[1:]
    ):
        raise ClosureError("{} canonical path is unsafe".format(label))
    host_path = root.joinpath(*canonical.parts[1:])
    resolved_root = root.resolve()
    resolved_host = host_path.resolve()
    if (
        host_path.is_symlink()
        or os.path.commonpath((str(resolved_root), str(resolved_host)))
        != str(resolved_root)
        or not host_path.is_file()
    ):
        raise ClosureError("{} is not a confined regular file".format(label))
    return host_path


def resolve_binary(root: Path, command: str) -> Tuple[str, str]:
    shell = "command -v -- {}".format(shlex.quote(command))
    stdout, _ = run_command(["chroot", str(root), "/bin/sh", "-c", shell])
    rows = stdout.decode("utf-8").splitlines()
    if len(rows) != 1 or not rows[0].startswith("/"):
        raise ClosureError("probe binary resolution is ambiguous: {}".format(command))
    binary = PurePosixPath(rows[0])
    if any(part in ("", ".", "..") for part in binary.parts[1:]):
        raise ClosureError("probe binary path is unsafe")
    resolved = chroot_regular_file(root, binary.as_posix(), "probe binary")
    _, digest = sha256_file(resolved)
    return binary.as_posix(), digest


def installed_file_owner_capture(root: Path, path: str) -> Tuple[str, bytes, bytes]:
    stdout, stderr = run_command(
        ["rpm", "--root", str(root), "-qf", "--qf", RPM_NEVRA_QUERY, path]
    )
    if stderr:
        raise ClosureError("installed file ownership query wrote stderr")
    rows = stdout.decode("utf-8").splitlines()
    if len(rows) != 1 or not rows[0]:
        raise ClosureError("installed file ownership is ambiguous")
    return rows[0], stdout, stderr


def installed_file_owner(root: Path, path: str) -> str:
    owner, _, _ = installed_file_owner_capture(root, path)
    return owner


def chroot_probe(
    root: Path, command: Sequence[str], extra_env: Optional[Mapping[str, str]] = None
) -> Tuple[bytes, bytes]:
    env_pairs = [
        "HOME=/root",
        "LANG=C",
        "LC_ALL=C",
        "PATH=/usr/sbin:/usr/bin:/sbin:/bin",
        "TZ=UTC",
        "HTTP_PROXY=http://127.0.0.1:9",
        "HTTPS_PROXY=http://127.0.0.1:9",
        "ALL_PROXY=http://127.0.0.1:9",
        "NO_PROXY=",
    ]
    if extra_env:
        env_pairs.extend("{}={}".format(key, value) for key, value in sorted(extra_env.items()))
    return run_command(
        ["chroot", str(root), "/usr/bin/env", "-i"] + env_pairs + list(command)
    )


def capture_probes(
    root: Path, toolchain: Mapping[str, Any], output_root: Path
) -> Dict[str, Any]:
    results: List[Dict[str, Any]] = []
    artifact_by_name = {
        item["name"]: item for item in toolchain["direct_artifacts"]
    }
    if len(artifact_by_name) != len(toolchain["direct_artifacts"]):
        raise ClosureError("toolchain direct artifact names are ambiguous")
    probe_by_id = {item["id"]: item for item in toolchain["required_probes"]}
    if len(probe_by_id) != len(toolchain["required_probes"]):
        raise ClosureError("toolchain probe ids are ambiguous")
    special = {"rust-src-core", "libclang-via-bindgen"}
    for probe in toolchain["required_probes"]:
        probe_id = probe["id"]
        if probe_id in special:
            continue
        command = list(probe["command"])
        binary_path, binary_sha256 = resolve_binary(root, command[0])
        stdout, stderr = chroot_probe(root, command)
        combined = stdout + stderr
        expected = probe.get("expected_version")
        owner_nevra = installed_file_owner(root, binary_path)
        expected_owner = expected_probe_owner(
            probe_id, artifact_by_name[probe["artifact"]]["nevra"]
        )
        require_exact(owner_nevra, expected_owner, "{} binary owner".format(probe_id))
        verify_expected_version(probe_id, expected, combined, owner_nevra)
        transcript = command_transcript(command, stdout, stderr)
        relative = PurePosixPath("transcripts/probes") / (probe_id + ".txt")
        phase_one.write_output_bytes(output_root, relative, transcript)
        results.append(
            {
                "binary_path": binary_path,
                "binary_sha256": binary_sha256,
                "command": command,
                "exit_code": 0,
                "id": probe_id,
                "loaded_library_path": None,
                "loaded_library_sha256": None,
                "package_nevra": owner_nevra,
                "parsed_version": expected,
                "required_file_path": None,
                "required_file_sha256": None,
                "stderr_sha256": hashlib.sha256(stderr).hexdigest(),
                "stdout_sha256": hashlib.sha256(stdout).hexdigest(),
            }
        )

    rpm_path, rpm_digest = resolve_binary(root, "rpm")
    sysroot_stdout, sysroot_stderr = chroot_probe(root, ["rustc", "--print", "sysroot"])
    if sysroot_stderr:
        raise ClosureError("rustc sysroot probe wrote stderr")
    sysroot_rows = sysroot_stdout.decode("utf-8").splitlines()
    if len(sysroot_rows) != 1 or not sysroot_rows[0].startswith("/"):
        raise ClosureError("rustc sysroot is ambiguous")
    core_path = PurePosixPath(sysroot_rows[0]) / "lib/rustlib/src/rust/library/core/src/lib.rs"
    host_core = chroot_regular_file(root, core_path.as_posix(), "rust-src core file")
    _, core_digest = sha256_file(host_core)
    owner, rust_src_stdout, rust_src_stderr = installed_file_owner_capture(
        root, core_path.as_posix()
    )
    require_exact(
        owner,
        artifact_by_name["rust-src"]["nevra"],
        "rust-src core file owner",
    )
    rust_src_command = list(probe_by_id["rust-src-core"]["command"])
    phase_one.write_output_bytes(
        output_root,
        PurePosixPath("transcripts/probes/rust-src-core.txt"),
        command_transcript(
            ["rustc", "--print", "sysroot"], sysroot_stdout, sysroot_stderr
        )
        + command_transcript(rust_src_command, rust_src_stdout, rust_src_stderr),
    )
    results.append(
        {
            "binary_path": rpm_path,
            "binary_sha256": rpm_digest,
            "command": rust_src_command,
            "exit_code": 0,
            "id": "rust-src-core",
            "loaded_library_path": None,
            "loaded_library_sha256": None,
            "package_nevra": owner,
            "parsed_version": probe_by_id["rust-src-core"]["expected_version"],
            "required_file_path": core_path.as_posix(),
            "required_file_sha256": core_digest,
            "stderr_sha256": hashlib.sha256(rust_src_stderr).hexdigest(),
            "stdout_sha256": hashlib.sha256(rust_src_stdout).hexdigest(),
        }
    )

    bindgen_path, bindgen_digest = resolve_binary(root, "bindgen")
    files_stdout, files_stderr = run_command(
        [
            "rpm",
            "--root",
            str(root),
            "-ql",
            artifact_by_name["clang-libs"]["nevra"],
        ]
    )
    if files_stderr:
        raise ClosureError("clang-libs file query wrote stderr")
    candidates: List[Tuple[int, str, Path]] = []
    for row in files_stdout.decode("utf-8").splitlines():
        if "/libclang.so" not in row or not row.startswith("/"):
            continue
        resolved = chroot_regular_file(root, row, "libclang candidate")
        candidates.append((resolved.stat().st_size, row, resolved))
    if not candidates:
        raise ClosureError("clang-libs contains no libclang shared library")
    _, libclang_candidate, _ = sorted(candidates, reverse=True)[0]
    fixture_dir = root / "scripts"
    if fixture_dir.exists() or fixture_dir.is_symlink():
        raise ClosureError("libclang probe fixture directory already exists")
    fixture_dir.mkdir(mode=0o755)
    header = fixture_dir / "rust_is_available_bindgen_libclang.h"
    with header.open("xb") as stream:
        stream.write(LIBCLANG_PROBE_BYTES)
        stream.flush()
        os.fsync(stream.fileno())
    header.chmod(0o400)
    require_exact(
        hashlib.sha256(LIBCLANG_PROBE_BYTES).hexdigest(),
        LIBCLANG_PROBE_SHA256,
        "libclang probe fixture digest",
    )
    libclang_command = list(probe_by_id["libclang-via-bindgen"]["command"])
    stdout, stderr = chroot_probe(
        root,
        libclang_command,
        {
            "LD_DEBUG": "libs",
            "LIBCLANG_PATH": str(PurePosixPath(libclang_candidate).parent),
        },
    )
    libclang_path = loaded_libclang_path(stderr)
    libclang_host = chroot_regular_file(root, libclang_path, "loaded libclang")
    libclang_path = "/" + libclang_host.relative_to(root).as_posix()
    _, libclang_digest = sha256_file(libclang_host)
    transcript = command_transcript(libclang_command, stdout, stderr)
    phase_one.write_output_bytes(
        output_root,
        PurePosixPath("transcripts/probes/libclang-via-bindgen.txt"),
        transcript,
    )
    libclang_owner = installed_file_owner(root, libclang_path)
    require_exact(
        libclang_owner,
        artifact_by_name["clang-libs"]["nevra"],
        "libclang owner",
    )
    results.append(
        {
            "binary_path": bindgen_path,
            "binary_sha256": bindgen_digest,
            "command": libclang_command,
            "exit_code": 0,
            "id": "libclang-via-bindgen",
            "loaded_library_path": libclang_path,
            "loaded_library_sha256": libclang_digest,
            "package_nevra": libclang_owner,
            "parsed_version": None,
            "required_file_path": None,
            "required_file_sha256": None,
            "stderr_sha256": hashlib.sha256(stderr).hexdigest(),
            "stdout_sha256": hashlib.sha256(stdout).hexdigest(),
        }
    )
    order = [item["id"] for item in toolchain["required_probes"]]
    results.sort(key=lambda item: order.index(item["id"]))
    require_exact([item["id"] for item in results], order, "probe result coverage")
    for index, result in enumerate(results):
        exact_keys(result, PROBE_RESULT_FIELDS, "probe result {}".format(index))
    return {
        "all_required_probes_verified": True,
        "fixture_path": "/scripts/rust_is_available_bindgen_libclang.h",
        "fixture_sha256": LIBCLANG_PROBE_SHA256,
        "fixture_size": len(LIBCLANG_PROBE_BYTES),
        "network_isolation_claimed": False,
        "results": results,
        "schema_version": SCHEMA_VERSION,
    }


def prepare_empty_directory(path: Path, label: str) -> Path:
    if path.exists() or path.is_symlink():
        raise ClosureError("{} already exists".format(label))
    path.mkdir(mode=0o700, parents=True)
    if any(path.iterdir()):
        raise ClosureError("{} did not start empty".format(label))
    return path


def prepare_chroot_devices(root: Path) -> None:
    device_dir = root / "dev"
    if device_dir.is_symlink() or (device_dir.exists() and not device_dir.is_dir()):
        raise ClosureError("offline installroot /dev is not a regular directory")
    device_dir.mkdir(mode=0o755, parents=True, exist_ok=True)
    null = device_dir / "null"
    if null.is_symlink():
        raise ClosureError("offline installroot /dev/null is a symlink")
    if not null.exists():
        try:
            os.mknod(str(null), stat.S_IFCHR | 0o666, os.makedev(1, 3))
        except OSError as exc:
            raise ClosureError("cannot create isolated chroot /dev/null: {}".format(exc)) from exc
    if not stat.S_ISCHR(null.stat().st_mode) or null.stat().st_rdev != os.makedev(1, 3):
        raise ClosureError("isolated chroot /dev/null has the wrong device identity")


def validate_capture_manifest_schemas(
    closure: Mapping[str, Any],
    offline: Mapping[str, Any],
    probes: Mapping[str, Any],
    macros: Mapping[str, Any],
    environment: Mapping[str, Any],
    blockers: Mapping[str, Any],
) -> None:
    exact_keys(
        closure,
        {
            "all_archives_verified",
            "all_repomd_data_materialized",
            "all_signatures_verified",
            "configured_network_sources",
            "environment_manifest_sha256",
            "exact_snapshot_root_solve_verified",
            "historical_direct_phase_checkpoint_sha256",
            "network_isolation_claimed",
            "package_bytes",
            "package_count",
            "packages",
            "resolution_inputs_sha256",
            "resolution_root_count",
            "resolution_roots",
            "rpm_set_sha256",
            "schema_version",
            "snapshot_repositories",
            "unresolved_dependencies",
        },
        "closure output",
    )
    for index, item in enumerate(closure["packages"]):
        row = exact_keys(
            item,
            {
                "arch",
                "archive_path",
                "nevra",
                "repository_id",
                "repository_location",
                "sha256",
                "signature",
                "signature_transcript_path",
                "size",
            },
            "closure package {}".format(index),
        )
        exact_keys(
            row["signature"],
            {
                "header_signature_algorithm",
                "signer_fingerprint",
                "signer_key_id",
                "status",
                "transcript_sha256",
                "transcript_size",
            },
            "closure package signature",
        )
    for repository in closure["snapshot_repositories"]:
        snapshot = exact_keys(
            repository,
            {
                "base_url",
                "id",
                "local_repository_path",
                "metadata",
                "repomd_sha256",
                "repomd_signature",
            },
            "snapshot repository output",
        )
        exact_keys(
            snapshot["repomd_signature"],
            {"status", "transcript_sha256", "transcript_size", "validsig_fingerprint"},
            "snapshot repomd signature output",
        )
        for item in snapshot["metadata"]:
            metadata = exact_keys(
                item,
                {
                    "archive_path",
                    "download",
                    "href",
                    "open_identity_verified",
                    "open_sha256",
                    "open_size",
                    "sha256",
                    "signed_compressed_identity_verified",
                    "size",
                    "type",
                },
                "snapshot metadata output",
            )
            exact_keys(
                metadata["download"],
                {"final_url", "redirect_count", "sha256", "size", "source"},
                "snapshot metadata download output",
            )
    replay = exact_keys(
        offline,
        {
            "all_repositories_disabled",
            "command",
            "empty_installroot_verified",
            "enabled_repository_count",
            "environment_manifest_sha256",
            "installed_package_count",
            "installed_rpm_set_sha256",
            "network_isolation_claimed",
            "network_scope",
            "proxy_loopback_defense",
            "schema_version",
            "snapshot_solve",
            "transaction_exit_code",
            "transaction_output_sha256",
        },
        "offline replay output",
    )
    exact_keys(
        replay["snapshot_solve"],
        {
            "command",
            "empty_installroot_verified",
            "installed_package_count",
            "installed_rpm_set_sha256",
            "local_file_repositories_only",
            "transaction_exit_code",
            "transaction_output_sha256",
        },
        "snapshot solve output",
    )
    exact_keys(
        probes,
        {
            "all_required_probes_verified",
            "environment_manifest_sha256",
            "fixture_path",
            "fixture_sha256",
            "fixture_size",
            "network_isolation_claimed",
            "results",
            "schema_version",
        },
        "probe output",
    )
    for index, result in enumerate(probes["results"]):
        exact_keys(result, PROBE_RESULT_FIELDS, "probe output {}".format(index))
    exact_keys(macros, {"command", "output_sha256", "output_size", "schema_version"}, "RPM macro output")
    exact_keys(
        environment,
        {
            "architecture",
            "container_image",
            "container_manifest_digest",
            "container_platform",
            "direct_input",
            "github",
            "offline_installroot_package_count",
            "offline_os_release",
            "offline_rpm_set_sha256",
            "runtime_os_release",
            "schema_version",
            "snapshot_solve_package_count",
        },
        "closure environment output",
    )
    exact_keys(
        blockers,
        {
            "config_lock_blockers_at_capture",
            "gate_claims",
            "phase_success_blockers",
            "toolchain_lock_blockers_at_capture",
        },
        "closure blocker output",
    )


def validate_capture_checkpoint(checkpoint: Mapping[str, Any]) -> None:
    row = exact_keys(
        checkpoint,
        {
            "credit_eligible",
            "direct_phase_head_sha",
            "gate_claims",
            "github",
            "manifests",
            "phase",
            "schema_version",
            "successful_capture_requires_independent_review",
        },
        "closure checkpoint",
    )
    require_exact(row["credit_eligible"], False, "closure checkpoint credit")
    require_exact(row["phase"], PHASE_ID, "closure checkpoint phase")
    require_exact(row["schema_version"], SCHEMA_VERSION, "closure checkpoint schema")
    require_exact(
        row["successful_capture_requires_independent_review"],
        True,
        "closure checkpoint review requirement",
    )
    if not re.fullmatch(r"[0-9a-f]{40}", str(row["direct_phase_head_sha"])):
        raise ClosureError("closure checkpoint direct-phase SHA is malformed")
    claims = row["gate_claims"]
    if not isinstance(claims, dict) or not claims or any(
        type(value) is not bool or value for value in claims.values()
    ):
        raise ClosureError("closure checkpoint contains a gate-credit claim")
    exact_keys(
        row["github"],
        {"head_sha", "repository", "run_attempt", "run_id"},
        "closure checkpoint GitHub identity",
    )
    expected_names = [
        "blockers.json",
        "closure.json",
        "environment.json",
        "offline-replay.json",
        "probes.json",
        "rpm-macros.json",
    ]
    manifests = row["manifests"]
    if not isinstance(manifests, list) or len(manifests) != len(expected_names):
        raise ClosureError("closure checkpoint manifest coverage changed")
    observed_names = []
    for index, item in enumerate(manifests):
        manifest = exact_keys(
            item, {"path", "sha256", "size"}, "closure manifest {}".format(index)
        )
        relative = phase_one.normalized_relative_path(
            manifest["path"], "closure manifest path"
        )
        if relative.parts != (relative.name,):
            raise ClosureError("closure checkpoint manifest must be top-level")
        if not isinstance(manifest["sha256"], str) or not HEX_SHA256.fullmatch(
            manifest["sha256"]
        ):
            raise ClosureError("closure checkpoint manifest digest is malformed")
        if not isinstance(manifest["size"], int) or manifest["size"] < 1:
            raise ClosureError("closure checkpoint manifest size is invalid")
        observed_names.append(relative.as_posix())
    require_exact(observed_names, expected_names, "closure checkpoint manifest order")


def expected_capture_bundle_paths(
    closure: Mapping[str, Any], probes: Mapping[str, Any]
) -> List[str]:
    paths = {
        "blockers.json",
        "checkpoint.json",
        "closure.json",
        "environment.json",
        "offline-replay.json",
        "probes.json",
        "rpm-macros.json",
        "transcripts/dnf-exact-snapshot.txt",
        "transcripts/dnf-offline.txt",
        "transcripts/dnf-online.txt",
        "transcripts/rpm-showrc-offline.txt",
    }
    for repository in closure["snapshot_repositories"]:
        repository_id = repository["id"]
        local_root = phase_one.normalized_relative_path(
            repository["local_repository_path"], "snapshot output path"
        )
        paths.add((local_root / "repodata/repomd.xml").as_posix())
        paths.add((local_root / "repodata/repomd.xml.asc").as_posix())
        paths.add("transcripts/snapshot-repomd/{}.gpgv.txt".format(repository_id))
        for metadata in repository["metadata"]:
            paths.add(
                phase_one.normalized_relative_path(
                    metadata["archive_path"], "metadata archive path"
                ).as_posix()
            )
    for package in closure["packages"]:
        paths.add(
            phase_one.normalized_relative_path(
                package["archive_path"], "RPM archive path"
            ).as_posix()
        )
        paths.add(
            phase_one.normalized_relative_path(
                package["signature_transcript_path"], "RPM transcript path"
            ).as_posix()
        )
    for probe in probes["results"]:
        probe_id = probe["id"]
        if not isinstance(probe_id, str) or not re.fullmatch(r"[a-z0-9-]+", probe_id):
            raise ClosureError("probe transcript identity is unsafe")
        paths.add("transcripts/probes/{}.txt".format(probe_id))
    return sorted(paths)


def capture(
    repo: Path,
    direct_root: Path,
    output_dir: Path,
    identity: Mapping[str, Any],
) -> None:
    if os.uname().machine != "x86_64":
        raise ClosureError("capture runtime is not x86_64")
    runtime_os_release = phase_one.parse_os_release(runtime_os_release_bytes())
    contract = validate_contract(repo)
    (
        plan,
        toolchain,
        _,
        _,
        toolchain_blockers,
        config_blockers,
        _,
    ) = phase_one.load_locked_inputs(repo)
    expected_direct_files = expected_direct_bundle_paths(plan, toolchain)
    build = validate_direct_root(
        direct_root,
        contract,
        identity,
        expected_direct_files,
        plan,
        toolchain,
    )
    phase_one.validate_bootstrap_manifest(
        direct_root / "bootstrap-input.json", identity, plan
    )
    direct_input = {}
    for name in ["SHA256SUMS", "checkpoint.json"] + DIRECT_MANIFEST_NAMES:
        size, digest = sha256_file(direct_root / name)
        direct_input[name] = {"sha256": digest, "size": size}
    direct_input["exact_file_count"] = len(expected_direct_files)
    direct_input["github"] = dict(identity)
    direct_nevras = toolchain["closure"]["direct_nevras"]
    require_exact(
        sorted(build["direct_nevras"]),
        sorted(direct_nevras),
        "direct NEVRA inputs",
    )
    roots = [item["value"] for item in build["resolution_roots"]]
    if len(roots) != len(set((item["kind"], item["value"]) for item in build["resolution_roots"])):
        raise ClosureError("resolution roots contain duplicates")
    output_root = phase_one.prepare_output_dir(output_dir)
    with tempfile.TemporaryDirectory(prefix="mckernel-rk003-closure-") as temporary_name:
        temporary = Path(temporary_name)
        release_key_path = (
            direct_root / "archives/repositories/RPM-GPG-KEY-Rocky-10"
        )
        release_key_size, release_key_digest = sha256_file(release_key_path)
        require_exact(
            release_key_size, plan["release_key"]["size"], "release key size"
        )
        require_exact(
            release_key_digest,
            plan["release_key"]["sha256"],
            "release key digest",
        )
        verification_root = prepare_empty_directory(
            temporary / "verification", "signature verification root"
        )
        gpg_keyring, rpm_db = phase_one.create_verification_keyrings(
            release_key_path, verification_root, plan["release_key"]["fingerprint"]
        )
        snapshot_roots, snapshot_manifests = materialize_snapshot_repositories(
            direct_root,
            output_root,
            plan,
            gpg_keyring,
        )
        primary = load_primary_indexes(snapshot_roots, plan)

        online_root = prepare_empty_directory(temporary / "online-root", "online installroot")
        online = online_command(
            online_root, plan["repositories"], snapshot_roots, roots
        )
        online_stdout, online_stderr = run_command(
            online, acquisition_environment(os.environ)
        )
        phase_one.write_output_bytes(
            output_root,
            PurePosixPath("transcripts/dnf-online.txt"),
            command_transcript(online, online_stdout, online_stderr),
        )
        cache_dir = online_root / "var/cache/dnf"
        if cache_dir.is_symlink() or not cache_dir.is_dir():
            raise ClosureError("DNF did not retain its cache inside the online installroot")
        verify_cached_repomd(cache_dir, plan["repositories"])
        cached = sorted(cache_dir.rglob("*.rpm"))
        if not cached or len(cached) > MAX_CAPTURED_RPMS:
            raise ClosureError("captured RPM count is empty or exceeds its bound")
        captured_bytes = 0
        for cached_path in cached:
            resolved_cached = cached_path.resolve()
            if (
                cached_path.is_symlink()
                or cached_path != resolved_cached
                or os.path.commonpath((str(cache_dir.resolve()), str(resolved_cached)))
                != str(cache_dir.resolve())
                or not cached_path.is_file()
            ):
                raise ClosureError("DNF cache contains an unsafe RPM path")
            captured_bytes += cached_path.stat().st_size
            if captured_bytes > MAX_CAPTURED_BYTES:
                raise ClosureError("captured RPM bytes exceed the artifact bound")
        rows: List[Dict[str, Any]] = []
        paths_by_nevra: Dict[str, Path] = {}
        for source_path in cached:
            nevra = rpm_nevra(source_path)
            if nevra in paths_by_nevra:
                previous_size, previous_digest = sha256_file(paths_by_nevra[nevra])
                size, digest = sha256_file(source_path)
                if (size, digest) != (previous_size, previous_digest):
                    raise ClosureError("duplicate cached NEVRA has different bytes")
                continue
            metadata = primary.get(nevra)
            if metadata is None:
                raise ClosureError("closure RPM is absent from signed primary: {}".format(nevra))
            size, digest = sha256_file(source_path)
            require_exact(size, metadata["size"], "closure RPM size")
            require_exact(digest, metadata["sha256"], "closure RPM digest")
            repository = repository_for_metadata(metadata, plan["repositories"])
            filename = PurePosixPath(metadata["repository_location"]).name
            archive_relative = (
                PurePosixPath("archives/snapshot-repositories")
                / repository["id"]
                / PurePosixPath(metadata["repository_location"])
            )
            archive_path = copy_archive(source_path, output_root, archive_relative)
            signature, transcript = phase_one.verify_rpm_signature(
                archive_path, rpm_db, plan["release_key"]["fingerprint"]
            )
            transcript_relative = (
                PurePosixPath("transcripts/rpmkeys")
                / repository["id"]
                / (filename + ".txt")
            )
            phase_one.write_output_bytes(output_root, transcript_relative, transcript)
            row = dict(metadata)
            row.update(
                {
                    "archive_path": archive_relative.as_posix(),
                    "signature": signature,
                    "signature_transcript_path": transcript_relative.as_posix(),
                }
            )
            rows.append(row)
            paths_by_nevra[nevra] = archive_path
        rows.sort(key=lambda item: item["nevra"])
        transaction_nevras = [item["nevra"] for item in rows]
        verify_transitive_inventory(transaction_nevras, direct_nevras)
        shutil.rmtree(str(online_root))
        if online_root.exists() or online_root.is_symlink():
            raise ClosureError("online installroot cleanup failed before exact snapshot solve")

        snapshot_solve_root = prepare_empty_directory(
            temporary / "snapshot-solve-root", "exact snapshot solve installroot"
        )
        snapshot_solve = snapshot_solve_command(
            snapshot_solve_root, plan["repositories"], snapshot_roots, roots
        )
        if any("https://" in item or "http://" in item for item in snapshot_solve):
            raise ClosureError("exact snapshot solve command contains a network URL")
        snapshot_stdout, snapshot_stderr = run_command(
            snapshot_solve, private_environment(os.environ)
        )
        snapshot_transcript = command_transcript(
            snapshot_solve, snapshot_stdout, snapshot_stderr
        )
        phase_one.write_output_bytes(
            output_root,
            PurePosixPath("transcripts/dnf-exact-snapshot.txt"),
            snapshot_transcript,
        )
        snapshot_inventory = installed_nevras(snapshot_solve_root)
        require_exact(
            snapshot_inventory,
            transaction_nevras,
            "exact snapshot root solve inventory",
        )
        shutil.rmtree(str(snapshot_solve_root))
        if snapshot_solve_root.exists() or snapshot_solve_root.is_symlink():
            raise ClosureError("exact snapshot solve cleanup failed before offline replay")

        offline_root = prepare_empty_directory(temporary / "offline-root", "offline installroot")
        rpm_paths = [paths_by_nevra[item["nevra"]] for item in rows]
        offline = offline_command(offline_root, rpm_paths)
        if any("repofrompath" in item or item.startswith("--enablerepo") for item in offline):
            raise ClosureError("offline command contains a repository enablement")
        if offline.count("--disablerepo=*") != 1:
            raise ClosureError("offline command does not disable every repository")
        offline_stdout, offline_stderr = run_command(offline, private_environment(os.environ))
        offline_transcript = command_transcript(
            offline, offline_stdout, offline_stderr
        )
        phase_one.write_output_bytes(
            output_root, PurePosixPath("transcripts/dnf-offline.txt"), offline_transcript
        )
        offline_inventory = installed_nevras(offline_root)
        require_exact(offline_inventory, transaction_nevras, "offline installed closure")
        offline_os_release_path = chroot_regular_file(
            offline_root, "/etc/os-release", "offline os-release"
        )
        offline_os_release = phase_one.parse_os_release(
            read_regular_bytes(offline_os_release_path, "offline os-release")
        )

        prepare_chroot_devices(offline_root)
        probes = capture_probes(offline_root, toolchain, output_root)
        macro_stdout, macro_stderr = chroot_probe(offline_root, ["rpm", "--showrc"])
        macro_transcript = command_transcript(
            ["rpm", "--showrc"], macro_stdout, macro_stderr
        )
        phase_one.write_output_bytes(
            output_root, PurePosixPath("transcripts/rpm-showrc-offline.txt"), macro_transcript
        )
        rpm_set_bytes = "".join(
            "{}\t{}\n".format(item["nevra"], item["sha256"]) for item in rows
        ).encode("utf-8")
        closure = {
            "all_archives_verified": True,
            "all_repomd_data_materialized": True,
            "all_signatures_verified": True,
            "configured_network_sources": [
                repository["base_url"] for repository in plan["repositories"]
            ],
            "exact_snapshot_root_solve_verified": True,
            "historical_direct_phase_checkpoint_sha256": contract["direct_phase"]["historical_checkpoint_sha256"],
            "network_isolation_claimed": False,
            "package_count": len(rows),
            "package_bytes": sum(item["size"] for item in rows),
            "packages": rows,
            "resolution_root_count": len(roots),
            "resolution_roots": list(build["resolution_roots"]),
            "resolution_inputs_sha256": contract["direct_phase"]["resolution_inputs_sha256"],
            "rpm_set_sha256": hashlib.sha256(rpm_set_bytes).hexdigest(),
            "schema_version": SCHEMA_VERSION,
            "snapshot_repositories": snapshot_manifests,
            "unresolved_dependencies": [],
        }
        offline_manifest = {
            "all_repositories_disabled": True,
            "command": offline,
            "empty_installroot_verified": True,
            "enabled_repository_count": 0,
            "installed_package_count": len(offline_inventory),
            "installed_rpm_set_sha256": hashlib.sha256(rpm_set_bytes).hexdigest(),
            "network_isolation_claimed": False,
            "network_scope": contract["network_contract"]["scope"],
            "proxy_loopback_defense": True,
            "snapshot_solve": {
                "command": snapshot_solve,
                "empty_installroot_verified": True,
                "installed_package_count": len(snapshot_inventory),
                "installed_rpm_set_sha256": hashlib.sha256(rpm_set_bytes).hexdigest(),
                "local_file_repositories_only": True,
                "transaction_exit_code": 0,
                "transaction_output_sha256": hashlib.sha256(snapshot_transcript).hexdigest(),
            },
            "schema_version": SCHEMA_VERSION,
            "transaction_exit_code": 0,
            "transaction_output_sha256": hashlib.sha256(offline_transcript).hexdigest(),
        }
        environment = {
            "architecture": os.uname().machine,
            "container_image": phase_one.CONTAINER_IMAGE,
            "container_manifest_digest": plan["container"]["manifest_digest"],
            "container_platform": plan["container"]["platform"],
            "direct_input": direct_input,
            "github": dict(identity),
            "offline_installroot_package_count": len(offline_inventory),
            "offline_os_release": offline_os_release,
            "offline_rpm_set_sha256": hashlib.sha256(rpm_set_bytes).hexdigest(),
            "runtime_os_release": runtime_os_release,
            "schema_version": SCHEMA_VERSION,
            "snapshot_solve_package_count": len(snapshot_inventory),
        }
        probes["environment_manifest_sha256"] = hashlib.sha256(
            phase_one.canonical_json_bytes(environment)
        ).hexdigest()
        closure["environment_manifest_sha256"] = probes[
            "environment_manifest_sha256"
        ]
        offline_manifest["environment_manifest_sha256"] = probes[
            "environment_manifest_sha256"
        ]
        macro_manifest = {
            "command": ["rpm", "--showrc"],
            "output_sha256": hashlib.sha256(macro_transcript).hexdigest(),
            "output_size": len(macro_transcript),
            "schema_version": SCHEMA_VERSION,
        }
        blockers = {
            "config_lock_blockers_at_capture": list(config_blockers),
            "gate_claims": dict(contract["gate_claims"]),
            "phase_success_blockers": list(contract["success_blockers"]),
            "toolchain_lock_blockers_at_capture": list(toolchain_blockers),
        }
        validate_capture_manifest_schemas(
            closure,
            offline_manifest,
            probes,
            macro_manifest,
            environment,
            blockers,
        )
        for name, value in (
            ("closure.json", closure),
            ("offline-replay.json", offline_manifest),
            ("probes.json", probes),
            ("rpm-macros.json", macro_manifest),
            ("environment.json", environment),
            ("blockers.json", blockers),
        ):
            phase_one.write_output_json(output_root, PurePosixPath(name), value)
        manifests = []
        for name in (
            "blockers.json",
            "closure.json",
            "environment.json",
            "offline-replay.json",
            "probes.json",
            "rpm-macros.json",
        ):
            size, digest = sha256_file(output_root / name)
            manifests.append({"path": name, "sha256": digest, "size": size})
        checkpoint = {
            "credit_eligible": False,
            "direct_phase_head_sha": contract["direct_phase"]["head_sha"],
            "gate_claims": dict(contract["gate_claims"]),
            "github": dict(identity),
            "manifests": manifests,
            "phase": PHASE_ID,
            "schema_version": SCHEMA_VERSION,
            "successful_capture_requires_independent_review": True,
        }
        validate_capture_checkpoint(checkpoint)
        phase_one.write_output_json(output_root, PurePosixPath("checkpoint.json"), checkpoint)
        phase_one.write_sha256sums(output_root)
        verify_sha256sums(
            output_root,
            expected_capture_bundle_paths(closure, probes),
            "capture bundle",
        )


def validate_workflow(repo: Path) -> None:
    workflow_path = safe_repo_file(repo, WORKFLOW_PATH.as_posix())
    workflow_bytes = read_regular_bytes(workflow_path, "closure workflow")
    require_exact(
        hashlib.sha256(workflow_bytes).hexdigest(),
        EXPECTED_WORKFLOW_SHA256,
        "closure workflow digest",
    )
    text = workflow_bytes.decode("utf-8")
    required = {
        "python3 scripts/rocky_kernel_closure_offline.py": 2,
        "PYTHONDONTWRITEBYTECODE=1 python3 -m unittest -v": 1,
        "--phase closure-offline": 1,
        "--direct-root \"$EVIDENCE_ROOT/repository-direct\"": 1,
        "--output-dir \"$EVIDENCE_ROOT/closure-offline\"": 1,
        "--disablerepo=*": 0,
        "compression-level: 0": 1,
        "- .github/workflows/rocky-kernel-platform-evidence.yml": 2,
        "- host-kernel/rocky/**": 2,
        "- scripts/rocky_kernel_platform_evidence.py": 2,
        "- scripts/rocky_kernel_platform_lock.py": 2,
        "- scripts/rocky_kernel_source_lock.py": 2,
        "- scripts/tests/test_rocky_kernel_closure_offline.py": 2,
    }
    for needle, expected in required.items():
        if text.count(needle) != expected:
            raise ClosureError(
                "workflow fragment count differs for {!r}: {} != {}".format(
                    needle, text.count(needle), expected
                )
            )
    if "credit forbidden" not in text.lower():
        raise ClosureError("workflow omits its credit-forbidden scope")
    uses: List[str] = []
    for line in text.splitlines():
        if re.match(r"^\s*uses\s*:", line):
            match = re.fullmatch(r"\s*uses:\s+(\S+)(?:\s+#.*)?", line)
            if match is None:
                raise ClosureError("workflow action identity is ambiguous")
            uses.append(match.group(1))
    require_exact(uses, EXPECTED_WORKFLOW_USES, "closure workflow actions")
    immutable_counts = {
        "image: " + phase_one.CONTAINER_IMAGE: 1,
        "runs-on: ubuntu-24.04": 1,
        "permissions:\n  contents: read": 1,
        "persist-credentials: false": 2,
        "set-safe-directory: false": 1,
        "set-safe-directory: true": 1,
        "actions/checkout@11d5960a326750d5838078e36cf38b85af677262": 2,
        "actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02": 1,
    }
    for needle, expected in immutable_counts.items():
        require_exact(text.count(needle), expected, "workflow immutable fragment")


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[1])
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--check", action="store_true")
    modes.add_argument("--capture", action="store_true")
    parser.add_argument("--phase", choices=[PHASE_ID])
    parser.add_argument("--direct-root", type=Path)
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
        validate_python36_runtime(repo)
        contract = validate_contract(repo)
        validate_workflow(repo)
        if args.check:
            run_only = (
                args.phase,
                args.direct_root,
                args.output_dir,
                args.github_head_sha,
                args.github_run_id,
                args.github_run_attempt,
                args.github_repository,
                args.container_image,
            )
            if any(item is not None for item in run_only):
                raise ClosureError("--check rejects capture-only arguments")
            print("RK-003 closure/offline contract verified; gate credit remains forbidden")
            return 0
        required = {
            "--phase": args.phase,
            "--direct-root": args.direct_root,
            "--output-dir": args.output_dir,
            "--github-head-sha": args.github_head_sha,
            "--github-run-id": args.github_run_id,
            "--github-run-attempt": args.github_run_attempt,
            "--github-repository": args.github_repository,
            "--container-image": args.container_image,
        }
        missing = [name for name, value in required.items() if value is None]
        if missing:
            raise ClosureError("capture requires {}".format(", ".join(missing)))
        require_exact(args.phase, PHASE_ID, "capture phase")
        identity = phase_one.validate_run_identity(
            args.github_head_sha,
            args.github_run_id,
            args.github_run_attempt,
            args.github_repository,
            args.container_image,
        )
        capture(repo, args.direct_root, args.output_dir, identity)
        print("captured closure/offline evidence; RK-003 and dependent gates remain uncredited")
        return 0
    except (ClosureError, phase_one.EvidenceError, OSError, UnicodeError, ValueError) as exc:
        print("Rocky closure/offline evidence error: {}".format(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
