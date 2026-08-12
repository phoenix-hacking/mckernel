#!/usr/bin/env python3
"""Capture a bounded, fail-closed first RK-003/RK-005 evidence phase.

The implemented ``repository-direct`` phase binds a run to an exact GitHub
head and digest-pinned Rocky 10.2 x86_64 container, verifies signed repository
snapshots, archives and header-signature checks the twenty direct RPMs already
named by the toolchain lock, and derives Rocky-effective ``kernel.spec`` build
requirements plus the reviewed Rocky Rust additions.  It deliberately stops
before transitive closure resolution, offline installation, probes, config
resolution, ``rustavailable``, or gate credit.  Those blockers are emitted in
every successful evidence bundle.
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
from email.message import Message
from pathlib import Path, PurePosixPath
from typing import Any, BinaryIO, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple


import rocky_kernel_platform_lock as platform_lock


PLAN_PATH = Path("host-kernel/rocky/evidence-plan-v1.json")
TOOLCHAIN_LOCK_PATH = Path("host-kernel/rocky/toolchain-lock.json")
CONFIG_POLICY_PATH = Path("host-kernel/rocky/config-policy.json")
CONFIG_FRAGMENT_PATH = Path("host-kernel/rocky/configs/rust-minimal.config")
SOURCE_LOCK_PATH = Path("host-kernel/rocky/source-lock.json")
PATCH_SERIES_PATH = Path("host-kernel/rocky/patches/series.json")
PLATFORM_VALIDATOR_PATH = Path("scripts/rocky_kernel_platform_lock.py")
SOURCE_VALIDATOR_PATH = Path("scripts/rocky_kernel_source_lock.py")
CAPTURE_SCRIPT_PATH = Path("scripts/rocky_kernel_platform_evidence.py")
WORKFLOW_PATH = Path(".github/workflows/rocky-kernel-platform-evidence.yml")
BASE_RELEASE_KEY_PATH = Path("/etc/pki/rpm-gpg/RPM-GPG-KEY-Rocky-10")

CHECKPOINT_ID = "rk-003-rk-005-platform-evidence-phase-plan-v1"
SCHEMA_VERSION = 1
IMPLEMENTED_PHASE = "repository-direct"
EXPECTED_PLAN_SHA256 = (
    "dbe0788250f363c4f387782511753d9e3dfe8604cb44196e83db64302e876926"
)
EXPECTED_WORKFLOW_SHA256 = (
    "cc7e2a935369c1f8cea1eb01af26cdbdd08c629232abb05d7489ef68fa056001"
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
EXPECTED_TARGET = {
    "architecture": "x86_64",
    "distribution": "Rocky Linux",
    "kernel_nvr_base": "kernel-6.12.0-211.44.1.el10_2",
    "release": "10.2",
}
EXPECTED_REVIEWED_RUST_BUILDREQUIRES = ["bindgen", "rust", "rust-src"]
EXPECTED_REPOSITORY_IDS = ["baseos", "appstream", "crb"]
EXPECTED_ALLOWED_HOSTS = ["download.rockylinux.org", "git.rockylinux.org"]
COLLECTOR_NETWORK_SCOPE = (
    "The one-way seal covers only urllib requests issued by this collector. "
    "GitHub Actions, the runner, and subprocesses are not claimed to be "
    "kernel-network-isolated."
)
EXPECTED_WORKFLOW_USES = [
    "actions/checkout@11d5960a326750d5838078e36cf38b85af677262",
    "actions/checkout@11d5960a326750d5838078e36cf38b85af677262",
    "actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02",
]
EXPECTED_PHASE_IDS = [
    "repository-direct",
    "closure-offline",
    "config-rustavailable",
]

MAX_JSON_BYTES = 2 * 1024 * 1024
MAX_SMALL_DOWNLOAD_BYTES = 32 * 1024 * 1024
MAX_RPM_DOWNLOAD_BYTES = 64 * 1024 * 1024
MAX_TOTAL_DOWNLOAD_BYTES = 512 * 1024 * 1024
MAX_PRIMARY_OPEN_BYTES = 256 * 1024 * 1024
MAX_BUILDREQUIRES = 2048
HEX_SHA256 = re.compile(r"^[0-9a-f]{64}$")
HEX_SHA1 = re.compile(r"^[0-9a-f]{40}$")
GITHUB_REPOSITORY = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
RPM_HEADER_SIGNATURE = re.compile(
    r"Header(?: V[0-9]+)? ([A-Za-z0-9-]+/[A-Za-z0-9-]+) Signature, "
    r"key ID ([0-9A-Fa-f]{8,40}): OK",
    re.IGNORECASE,
)
BOOTSTRAP_NEVRA = re.compile(
    r"^([a-z0-9][a-z0-9+_.-]*)-([0-9]+):([A-Za-z0-9+_.~]+)-"
    r"([A-Za-z0-9+_.~]+)\.(x86_64|noarch)$"
)
COMMON_NS = "http://linux.duke.edu/metadata/common"
REPO_NS = "http://linux.duke.edu/metadata/repo"


class EvidenceError(RuntimeError):
    """Raised when platform evidence cannot be captured without weakening it."""


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


def reject_duplicate_pairs(pairs: Sequence[Tuple[str, Any]]) -> Dict[str, Any]:
    result: Dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise EvidenceError("duplicate JSON key: {!r}".format(key))
        result[key] = value
    return result


def strict_json_bytes(data: bytes, label: str) -> Dict[str, Any]:
    if len(data) > MAX_JSON_BYTES:
        raise EvidenceError("{} exceeds the JSON size limit".format(label))
    try:
        value = json.loads(
            data.decode("utf-8"), object_pairs_hook=reject_duplicate_pairs
        )
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
        raise EvidenceError("value is not canonical-JSON serializable: {}".format(exc)) from exc
    return (text + "\n").encode("ascii")


def exact_keys(value: object, expected: Iterable[str], label: str) -> Mapping[str, Any]:
    if not isinstance(value, dict):
        raise EvidenceError("{} must be an object".format(label))
    actual = set(value)
    wanted = set(expected)
    if actual != wanted:
        raise EvidenceError(
            "{} fields changed: actual={}, expected={}".format(
                label, sorted(actual), sorted(wanted)
            )
        )
    return value


def require_exact(value: object, expected: object, label: str) -> None:
    if value != expected or type(value) is not type(expected):
        raise EvidenceError(
            "{} changed: actual={!r}, expected={!r}".format(label, value, expected)
        )


def validate_sha256(value: object, label: str) -> str:
    if not isinstance(value, str) or not HEX_SHA256.fullmatch(value):
        raise EvidenceError("{} must be a lowercase SHA-256".format(label))
    return value


def normalized_relative_path(value: object, label: str) -> PurePosixPath:
    if not isinstance(value, str) or not value:
        raise EvidenceError("{} must be a non-empty relative path".format(label))
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in ("", ".", "..") for part in path.parts):
        raise EvidenceError("{} is not a normalized relative path".format(label))
    return path


def within(root: Path, candidate: Path) -> bool:
    try:
        common = os.path.commonpath((str(root), str(candidate)))
    except ValueError:
        return False
    return Path(common) == root


def repository_file(repo: Path, relative: Path) -> Path:
    relative_posix = normalized_relative_path(relative.as_posix(), "repository path")
    root = repo.resolve()
    requested = root.joinpath(*relative_posix.parts)
    resolved = requested.resolve()
    if not within(root, resolved):
        raise EvidenceError("repository path escapes checkout: {}".format(relative))
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


def validate_https_url(url: object, allowed_hosts: Sequence[str], label: str) -> str:
    if not isinstance(url, str) or not url:
        raise EvidenceError("{} must be an HTTPS URL".format(label))
    parsed = urllib.parse.urlsplit(url)
    if (
        parsed.scheme != "https"
        or parsed.hostname not in allowed_hosts
        or parsed.username is not None
        or parsed.password is not None
        or parsed.port is not None
        or not parsed.path.startswith("/")
        or parsed.query
        or parsed.fragment
    ):
        raise EvidenceError("{} is outside the locked HTTPS policy".format(label))
    if urllib.parse.urlunsplit(parsed) != url:
        raise EvidenceError("{} is not canonically encoded".format(label))
    return url


def validate_plan(
    plan: Mapping[str, Any],
    plan_bytes: bytes,
    toolchain: Mapping[str, Any],
    config: Mapping[str, Any],
    source: Mapping[str, Any],
) -> None:
    if sha256_bytes(plan_bytes) != EXPECTED_PLAN_SHA256:
        raise EvidenceError("evidence phase-plan bytes changed without validator review")
    exact_keys(
        plan,
        {
            "bootstrap",
            "checkpoint_id",
            "config_policy_lock_id",
            "container",
            "gate_claims",
            "network_policy",
            "phases",
            "release_key",
            "repositories",
            "resolution_policy",
            "schema_version",
            "source_lock_id",
            "target",
            "toolchain_lock_id",
        },
        "phase plan",
    )
    require_exact(plan["schema_version"], SCHEMA_VERSION, "phase-plan schema")
    require_exact(plan["checkpoint_id"], CHECKPOINT_ID, "checkpoint ID")
    require_exact(plan["target"], EXPECTED_TARGET, "phase-plan target")
    require_exact(plan["target"], toolchain["target"], "toolchain target binding")
    require_exact(plan["target"], config["target"], "config target binding")
    require_exact(plan["source_lock_id"], source["lock_id"], "source-lock binding")
    require_exact(
        plan["toolchain_lock_id"], toolchain["lock_id"], "toolchain-lock binding"
    )
    require_exact(
        plan["config_policy_lock_id"], config["lock_id"], "config-policy binding"
    )
    require_exact(plan["gate_claims"], {"RK-003": False, "RK-005": False}, "gate claims")

    bootstrap = exact_keys(
        plan["bootstrap"],
        {
            "artifact_count",
            "artifacts",
            "base_package_count",
            "base_package_manifest_sha256",
            "dnf_repository_network_requested",
            "total_bytes",
        },
        "bootstrap",
    )
    require_exact(bootstrap["artifact_count"], 47, "bootstrap artifact count")
    require_exact(bootstrap["base_package_count"], 138, "base package count")
    require_exact(
        bootstrap["base_package_manifest_sha256"],
        "9c2eddd4bb7c37e992dfcb4b42f2eb3a2728f98f301bdd0f27ddd54b2711d4b8",
        "base package manifest",
    )
    require_exact(
        bootstrap["dnf_repository_network_requested"],
        False,
        "bootstrap DNF repository-network request",
    )
    require_exact(bootstrap["total_bytes"], 20604218, "bootstrap byte count")
    artifacts = bootstrap["artifacts"]
    if not isinstance(artifacts, list) or len(artifacts) != bootstrap["artifact_count"]:
        raise EvidenceError("bootstrap artifact list has the wrong length")
    nevras: List[str] = []
    locations: List[str] = []
    total_bytes = 0
    for index, artifact in enumerate(artifacts):
        row = exact_keys(
            artifact,
            {"nevra", "repository_id", "repository_location", "sha256", "size"},
            "bootstrap artifact {}".format(index),
        )
        nevra = row["nevra"]
        if not isinstance(nevra, str):
            raise EvidenceError("bootstrap artifact NEVRA must be a string")
        match = BOOTSTRAP_NEVRA.fullmatch(nevra)
        if match is None:
            raise EvidenceError("bootstrap artifact NEVRA is malformed: {}".format(nevra))
        name, _, version, release, arch = match.groups()
        if row["repository_id"] not in ("baseos", "appstream"):
            raise EvidenceError("bootstrap artifact uses an unexpected repository")
        location = normalized_relative_path(
            row["repository_location"], "bootstrap artifact location"
        )
        if len(location.parts) != 3 or location.parts[0] != "Packages":
            raise EvidenceError("bootstrap artifact location has an unexpected layout")
        expected_filename = "{}-{}-{}.{}.rpm".format(name, version, release, arch)
        require_exact(location.name, expected_filename, "bootstrap RPM filename")
        validate_sha256(row["sha256"], "bootstrap artifact digest")
        if not isinstance(row["size"], int) or not 1 <= row["size"] <= MAX_RPM_DOWNLOAD_BYTES:
            raise EvidenceError("bootstrap artifact size is unsafe")
        nevras.append(nevra)
        locations.append(location.as_posix())
        total_bytes += row["size"]
    if nevras != sorted(nevras) or len(set(nevras)) != len(nevras):
        raise EvidenceError("bootstrap NEVRAs must be unique and sorted")
    if len(set(locations)) != len(locations):
        raise EvidenceError("bootstrap RPM locations must be unique")
    require_exact(total_bytes, bootstrap["total_bytes"], "bootstrap artifact bytes")
    container = exact_keys(
        plan["container"],
        {"image", "manifest_digest", "platform", "tag_index_digest"},
        "container",
    )
    require_exact(container["image"], CONTAINER_IMAGE, "container image")
    require_exact(
        container["manifest_digest"], CONTAINER_MANIFEST_DIGEST, "container manifest"
    )
    require_exact(container["platform"], CONTAINER_PLATFORM, "container platform")
    require_exact(
        container["tag_index_digest"], CONTAINER_TAG_INDEX_DIGEST, "container index"
    )
    network = exact_keys(
        plan["network_policy"],
        {
            "collector_http_after_acquisition_seal",
            "collector_http_allowed_hosts_before_seal",
            "collector_http_allow_redirects",
            "collector_http_require_content_length",
            "scope",
        },
        "network policy",
    )
    require_exact(
        network["collector_http_allowed_hosts_before_seal"],
        EXPECTED_ALLOWED_HOSTS,
        "collector HTTP allowed hosts",
    )
    require_exact(
        network["collector_http_allow_redirects"], False, "collector redirect policy"
    )
    require_exact(
        network["collector_http_after_acquisition_seal"],
        False,
        "post-seal collector HTTP policy",
    )
    require_exact(
        network["collector_http_require_content_length"],
        True,
        "collector content-length policy",
    )
    require_exact(network["scope"], COLLECTOR_NETWORK_SCOPE, "network scope")

    phases = plan["phases"]
    if not isinstance(phases, list) or [item.get("id") for item in phases if isinstance(item, dict)] != EXPECTED_PHASE_IDS:
        raise EvidenceError("phase order or identities changed")
    for index, phase in enumerate(phases):
        if not isinstance(phase, dict):
            raise EvidenceError("phase {} must be an object".format(index))
        require_exact(
            phase.get("implemented"), index == 0, "phase {} implementation state".format(index)
        )
        scope = phase.get("network_scope")
        if not isinstance(scope, str) or not scope.strip():
            raise EvidenceError("phase {} must state its network scope".format(index))
        if index == 0 and "not claimed to be kernel-network-isolated" not in scope:
            raise EvidenceError("implemented phase overclaims network isolation")
    blockers = phases[0].get("blockers_after_phase")
    if not isinstance(blockers, list) or len(blockers) != 7 or not all(
        isinstance(item, str) and item.strip() for item in blockers
    ):
        raise EvidenceError("implemented phase must retain seven explicit blockers")

    release_key = exact_keys(
        plan["release_key"], {"fingerprint", "sha256", "size", "url"}, "release key"
    )
    require_exact(release_key["fingerprint"], toolchain["release_key"]["fingerprint"], "release-key fingerprint")
    require_exact(release_key["sha256"], toolchain["release_key"]["sha256"], "release-key digest")
    require_exact(release_key["fingerprint"], source["repository_snapshot"]["release_key"]["fingerprint"], "source release-key fingerprint")
    require_exact(release_key["sha256"], source["repository_snapshot"]["release_key"]["sha256"], "source release-key digest")
    if not isinstance(release_key["size"], int) or release_key["size"] < 1:
        raise EvidenceError("release-key size must be positive")
    validate_https_url(release_key["url"], ["download.rockylinux.org"], "release-key URL")

    repositories = plan["repositories"]
    if not isinstance(repositories, list) or len(repositories) != 3:
        raise EvidenceError("phase plan must pin exactly three repositories")
    locked_repositories = {item["id"]: item for item in toolchain["repositories"]}
    if [item.get("id") for item in repositories if isinstance(item, dict)] != EXPECTED_REPOSITORY_IDS:
        raise EvidenceError("repository order or identities changed")
    for item in repositories:
        row = exact_keys(item, {"base_url", "id", "primary", "repomd", "signature"}, "repository")
        repository_id = row["id"]
        require_exact(row["base_url"], locked_repositories[repository_id]["base_url"], "{} base URL".format(repository_id))
        validate_https_url(row["base_url"], ["download.rockylinux.org"], "{} base URL".format(repository_id))
        repomd = exact_keys(row["repomd"], {"revision", "sha256", "size", "url"}, "{} repomd".format(repository_id))
        signature = exact_keys(row["signature"], {"sha256", "size", "url"}, "{} signature".format(repository_id))
        primary = exact_keys(row["primary"], {"href", "open_sha256", "open_size", "sha256", "size"}, "{} primary".format(repository_id))
        for label, record in (("repomd", repomd), ("signature", signature), ("primary", primary)):
            validate_sha256(record["sha256"], "{}.{}.sha256".format(repository_id, label))
            if not isinstance(record["size"], int) or record["size"] < 1:
                raise EvidenceError("{}.{}.size must be positive".format(repository_id, label))
        require_exact(repomd["revision"], "10.2", "{} revision".format(repository_id))
        require_exact(repomd["url"], row["base_url"] + "repodata/repomd.xml", "{} repomd URL".format(repository_id))
        require_exact(signature["url"], repomd["url"] + ".asc", "{} signature URL".format(repository_id))
        primary_path = normalized_relative_path(primary["href"], "{} primary href".format(repository_id))
        require_exact(primary_path.parts[0], "repodata", "{} primary directory".format(repository_id))
        require_exact(row["base_url"] + primary["href"], row["base_url"] + primary_path.as_posix(), "{} primary URL".format(repository_id))
        validate_sha256(primary["open_sha256"], "{}.primary.open_sha256".format(repository_id))
        if not isinstance(primary["open_size"], int) or not 1 <= primary["open_size"] <= MAX_PRIMARY_OPEN_BYTES:
            raise EvidenceError("{}.primary.open_size is unsafe".format(repository_id))

    resolution = exact_keys(
        plan["resolution_policy"],
        {
            "direct_nevras_source",
            "effective_buildrequires_command",
            "reviewed_rocky_rust_buildrequires",
            "rule",
        },
        "resolution policy",
    )
    require_exact(
        resolution["reviewed_rocky_rust_buildrequires"],
        EXPECTED_REVIEWED_RUST_BUILDREQUIRES,
        "reviewed Rocky Rust BuildRequires",
    )
    require_exact(
        resolution["direct_nevras_source"],
        "toolchain-lock.closure.direct_nevras",
        "direct NEVRA source",
    )
    require_exact(
        resolution["effective_buildrequires_command"],
        ["rpmspec", "-q", "--buildrequires", "--target", "x86_64-linux-gnu", "kernel.spec"],
        "rpmspec command",
    )
    if "transitive" not in str(resolution["rule"]).lower():
        raise EvidenceError("resolution policy does not require transitive closure")


def validate_workflow_bytes(workflow: bytes) -> None:
    if sha256_bytes(workflow) != EXPECTED_WORKFLOW_SHA256:
        raise EvidenceError("platform evidence workflow bytes changed without review")
    try:
        text = workflow.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise EvidenceError("platform evidence workflow is not UTF-8") from exc
    uses: List[str] = []
    for line in text.splitlines():
        if re.match(r"^\s*uses\s*:", line):
            match = re.fullmatch(r"\s*uses:\s+(\S+)(?:\s+#.*)?", line)
            if match is None:
                raise EvidenceError("workflow uses entry is ambiguous")
            uses.append(match.group(1))
    require_exact(uses, EXPECTED_WORKFLOW_USES, "workflow actions")
    required_counts = {
        "image: {}".format(CONTAINER_IMAGE): 1,
        "runs-on: ubuntu-24.04": 1,
        "permissions:\n  contents: read": 1,
        "persist-credentials: false": 2,
        "set-safe-directory: false": 1,
        "set-safe-directory: true": 1,
        "            --bootstrap \\\n": 1,
        "--bootstrap-manifest": 1,
        "--phase repository-direct": 1,
        "python3 scripts/rocky_kernel_platform_evidence.py": 3,
        "actions/checkout@11d5960a326750d5838078e36cf38b85af677262": 2,
        "actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02": 1,
    }
    for needle, expected in required_counts.items():
        if text.count(needle) != expected:
            raise EvidenceError(
                "workflow contract fragment has count {}, expected {}: {!r}".format(
                    text.count(needle), expected, needle
                )
            )
    if "RK_PLATFORM_CONTAINER_IMAGE: {}".format(CONTAINER_IMAGE) not in text:
        raise EvidenceError("workflow does not pass its immutable container identity")
    if "compression-level: 0" not in text:
        raise EvidenceError("workflow must not recompress already-compressed archives")


def validate_workflow_contract(repo: Path) -> bytes:
    workflow = repository_file(repo, WORKFLOW_PATH).read_bytes()
    validate_workflow_bytes(workflow)
    return workflow


def validate_source_evidence_file(
    repo: Path, path_value: object, digest_value: object, label: str
) -> None:
    relative = normalized_relative_path(path_value, label + " path")
    expected_digest = validate_sha256(digest_value, label + " digest")
    path = repository_file(repo, Path(relative.as_posix()))
    size, actual_digest = sha256_file(path)
    if size < 1 or actual_digest != expected_digest:
        raise EvidenceError("{} file is absent, empty, or stale".format(label))


def validate_source_evidence_state(
    source: Mapping[str, Any], repo: Path
) -> List[str]:
    evidence_rows = exact_keys(
        source.get("evidence"),
        {
            "acquisition_replay",
            "dist_git_object_replay",
            "repository_metadata_signature_replay",
            "srpm_header_signature",
        },
        "source evidence",
    )
    blockers: List[str] = []
    for name in sorted(evidence_rows):
        fields = {
            "blocker",
            "evidence_path",
            "evidence_sha256",
            "required",
            "status",
        }
        if name == "srpm_header_signature":
            fields.update({"signature_algorithm", "signer_fingerprint"})
        row = exact_keys(evidence_rows[name], fields, "source evidence {}".format(name))
        if row["required"] is not True:
            raise EvidenceError("source evidence row is not required: {}".format(name))
        status = row["status"]
        if status not in ("required-missing", "captured-unverified", "verified"):
            raise EvidenceError("source evidence status is invalid: {}".format(name))
        if status == "required-missing":
            blocker = row["blocker"]
            if not isinstance(blocker, str) or not blocker.strip():
                raise EvidenceError("source evidence blocker is missing: {}".format(name))
            require_exact(row["evidence_path"], None, name + " missing evidence path")
            require_exact(row["evidence_sha256"], None, name + " missing evidence digest")
            if name == "srpm_header_signature":
                require_exact(row["signature_algorithm"], None, "missing signature algorithm")
                require_exact(row["signer_fingerprint"], None, "missing signer fingerprint")
            blockers.append("{}: {}".format(name, blocker))
            continue
        validate_source_evidence_file(
            repo,
            row["evidence_path"],
            row["evidence_sha256"],
            "source evidence {}".format(name),
        )
        if name == "srpm_header_signature":
            algorithm = row["signature_algorithm"]
            if not isinstance(algorithm, str) or not algorithm.strip():
                raise EvidenceError("source SRPM signature algorithm is missing")
            require_exact(
                row["signer_fingerprint"],
                platform_lock.EXPECTED_RELEASE_KEY["fingerprint"],
                "source SRPM signer",
            )
        if status == "verified":
            require_exact(row["blocker"], None, name + " verified blocker")
        else:
            blocker = row["blocker"]
            if not isinstance(blocker, str) or not blocker.strip():
                raise EvidenceError("unverified source evidence needs a blocker: {}".format(name))
            blockers.append("{}: {}".format(name, blocker))

    inventory = exact_keys(
        source.get("licenses", {}).get("inventory"),
        {
            "blocker",
            "complete",
            "inventory_path",
            "inventory_sha256",
            "item_count",
            "required",
            "status",
        },
        "source license inventory",
    )
    if inventory["required"] is not True:
        raise EvidenceError("source license inventory must remain required")
    if inventory["status"] == "required-missing":
        require_exact(inventory["complete"], False, "missing license completeness")
        for key in ("inventory_path", "inventory_sha256", "item_count"):
            require_exact(inventory[key], None, "missing license " + key)
        blocker = inventory["blocker"]
        if not isinstance(blocker, str) or not blocker.strip():
            raise EvidenceError("source license-inventory blocker is missing")
        blockers.append("license_inventory: {}".format(blocker))
    elif inventory["status"] == "verified" and inventory["complete"] is True:
        require_exact(inventory["blocker"], None, "verified license blocker")
        if not isinstance(inventory["item_count"], int) or inventory["item_count"] < 1:
            raise EvidenceError("verified source license inventory needs items")
        validate_source_evidence_file(
            repo,
            inventory["inventory_path"],
            inventory["inventory_sha256"],
            "source license inventory",
        )
    else:
        raise EvidenceError("source license inventory state is invalid")

    gate = exact_keys(
        source.get("gate"), {"credit_eligible", "gate_id", "policy"}, "source gate"
    )
    require_exact(gate["gate_id"], "RK-001", "source gate ID")
    if not isinstance(gate["policy"], str) or "forbidden" not in gate["policy"].lower():
        raise EvidenceError("source gate policy is not fail-closed")
    require_exact(gate["credit_eligible"], not blockers, "source gate credit state")
    return blockers


def load_source_inputs(repo: Path) -> Tuple[Dict[str, Any], List[str]]:
    source, _ = read_repository_json(repo, SOURCE_LOCK_PATH)
    series, series_bytes = read_repository_json(repo, PATCH_SERIES_PATH)
    require_exact(
        source.get("lock_id"),
        platform_lock.EXPECTED_SOURCE["lock_id"],
        "source lock ID",
    )
    require_exact(source.get("target"), {
        "architecture": "x86_64",
        "distribution": "Rocky Linux",
        "release": "10.2",
    }, "source target")
    patch_binding = source.get("patch_series")
    if not isinstance(patch_binding, dict):
        raise EvidenceError("source patch-series binding is missing")
    require_exact(
        patch_binding.get("path"), PATCH_SERIES_PATH.as_posix(), "patch-series path"
    )
    require_exact(
        patch_binding.get("sha256"), sha256_bytes(series_bytes), "patch-series digest"
    )
    require_exact(
        series.get("source_lock_id"), source["lock_id"], "patch-series source binding"
    )
    return source, validate_source_evidence_state(source, repo)


def load_locked_inputs(
    repo: Path,
) -> Tuple[
    Dict[str, Any],
    Dict[str, Any],
    Dict[str, Any],
    Dict[str, Any],
    List[str],
    List[str],
    List[str],
]:
    try:
        toolchain, config, toolchain_blockers, config_blockers = platform_lock.load_locks(repo)
    except platform_lock.PlatformLockError as exc:
        raise EvidenceError("platform-lock validation failed: {}".format(exc)) from exc
    source, source_blockers = load_source_inputs(repo)
    plan, plan_bytes = read_repository_json(repo, PLAN_PATH)
    validate_plan(plan, plan_bytes, toolchain, config, source)
    if toolchain["gate"]["credit_eligible"] is not False:
        raise EvidenceError("capture phase must not start from an RK-003 credit claim")
    if config["gate"]["credit_eligible"] is not False:
        raise EvidenceError("capture phase must not start from an RK-005 credit claim")
    if not toolchain_blockers or not config_blockers:
        raise EvidenceError("capture phase requires explicit RK-003 and RK-005 blockers")
    for repository in toolchain["repositories"]:
        if repository["metadata_observed"] is not False or repository["repomd_sha256"] is not None:
            raise EvidenceError("toolchain lock must not pre-claim repository evidence")
    for artifact in toolchain["direct_artifacts"]:
        verification = artifact["verification"]
        if verification["archive_verified"] is not False or verification["signature_verified"] is not False:
            raise EvidenceError("toolchain lock must not pre-claim direct RPM evidence")
    return (
        plan,
        toolchain,
        config,
        source,
        toolchain_blockers,
        config_blockers,
        source_blockers,
    )


def check_repository(repo: Path) -> Tuple[Dict[str, Any], List[str], List[str]]:
    plan, _, _, _, toolchain_blockers, config_blockers, _ = load_locked_inputs(repo)
    validate_workflow_contract(repo)
    for relative in (
        PLATFORM_VALIDATOR_PATH,
        SOURCE_VALIDATOR_PATH,
        CAPTURE_SCRIPT_PATH,
        CONFIG_FRAGMENT_PATH,
        PATCH_SERIES_PATH,
    ):
        repository_file(repo, relative)
    return plan, toolchain_blockers, config_blockers


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
        raise EvidenceError("runtime container identity differs from the phase plan")
    return {
        "head_sha": head_sha,
        "repository": github_repository,
        "run_attempt": int(run_attempt),
        "run_id": int(run_id),
    }


def run_command(
    arguments: Sequence[str],
    cwd: Optional[Path] = None,
    env: Optional[Mapping[str, str]] = None,
) -> Tuple[bytes, bytes]:
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
    return completed.stdout, completed.stderr


def run_git(repo: Path, arguments: Sequence[str]) -> Tuple[bytes, bytes]:
    canonical_repo = repo.resolve()
    if not canonical_repo.is_dir():
        raise EvidenceError("Git repository path is not a directory")
    return run_command(
        ["git", "-c", "safe.directory={}".format(canonical_repo)]
        + list(arguments),
        cwd=canonical_repo,
    )


def subprocess_network_defense_env(base: Mapping[str, str]) -> Dict[str, str]:
    """Return proxy-loopback defense in depth; this is not network isolation."""
    result = dict(base)
    result.update(
        {
            "ALL_PROXY": "http://127.0.0.1:9",
            "FTP_PROXY": "http://127.0.0.1:9",
            "HTTP_PROXY": "http://127.0.0.1:9",
            "HTTPS_PROXY": "http://127.0.0.1:9",
            "NO_PROXY": "",
            "all_proxy": "http://127.0.0.1:9",
            "ftp_proxy": "http://127.0.0.1:9",
            "http_proxy": "http://127.0.0.1:9",
            "https_proxy": "http://127.0.0.1:9",
            "no_proxy": "",
        }
    )
    return result


def committed_file_identity(repo: Path, head_sha: str, relative: Path) -> Dict[str, Any]:
    path = repository_file(repo, relative)
    filesystem_bytes = path.read_bytes()
    committed_bytes, _ = run_git(
        repo, ["show", "{}:{}".format(head_sha, relative.as_posix())]
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
    values: Dict[str, str] = {}
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


def capture_runtime_environment(transcript_dir: Path) -> Dict[str, Any]:
    required_tools = ("gpg", "gpgv", "python3", "rpm", "rpmkeys", "rpmspec")
    for tool in required_tools:
        if shutil.which(tool) is None:
            raise EvidenceError("required evidence tool is missing: {}".format(tool))
    if platform.machine() != "x86_64" or sys.maxsize <= 2 ** 32:
        raise EvidenceError("runtime is not 64-bit x86_64")
    os_release = parse_os_release(Path("/etc/os-release").read_bytes())
    version_commands = {
        "gpg": ["gpg", "--version"],
        "python": ["python3", "--version"],
        "rpm": ["rpm", "--version"],
        "rpmspec": ["rpmspec", "--version"],
    }
    versions: Dict[str, Dict[str, Any]] = {}
    transcript = bytearray()
    for name in sorted(version_commands):
        stdout, stderr = run_command(version_commands[name])
        combined = stdout + stderr
        if not combined.strip():
            raise EvidenceError("{} version output is empty".format(name))
        transcript.extend(("$ " + " ".join(version_commands[name]) + "\n").encode("ascii"))
        transcript.extend(combined)
        if not combined.endswith(b"\n"):
            transcript.extend(b"\n")
        versions[name] = {
            "command": version_commands[name],
            "output_sha256": sha256_bytes(combined),
            "output_size": len(combined),
        }
    packages_stdout, packages_stderr = run_command(
        ["rpm", "-qa", "--qf", "%{NEVRA}\\n"]
    )
    if packages_stderr:
        raise EvidenceError("rpm package inventory unexpectedly wrote stderr")
    try:
        package_lines = sorted(
            line for line in packages_stdout.decode("utf-8").splitlines() if line
        )
    except UnicodeDecodeError as exc:
        raise EvidenceError("RPM package inventory is not UTF-8") from exc
    package_bytes = ("\n".join(package_lines) + "\n").encode("utf-8")
    write_output_bytes(transcript_dir.parent, PurePosixPath("transcripts/tool-versions.txt"), bytes(transcript))
    write_output_bytes(transcript_dir.parent, PurePosixPath("transcripts/bootstrap-rpms.txt"), package_bytes)
    return {
        "architecture": platform.machine(),
        "bootstrap_package_count": len(package_lines),
        "bootstrap_packages_sha256": sha256_bytes(package_bytes),
        "container_image": CONTAINER_IMAGE,
        "container_manifest_digest": CONTAINER_MANIFEST_DIGEST,
        "container_platform": CONTAINER_PLATFORM,
        "os_release": os_release,
        "tool_versions": versions,
    }


class RejectRedirects(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        del req, fp, msg, headers
        raise EvidenceError("HTTP redirect rejected: {} -> {}".format(code, newurl))


class NetworkSession:
    """One-way state for collector-controlled urllib acquisition only."""

    def __init__(self, allowed_hosts: Sequence[str], opener=None) -> None:
        self.allowed_hosts = tuple(allowed_hosts)
        self.opener = opener or urllib.request.build_opener(RejectRedirects())
        self.sealed = False
        self.downloaded_bytes = 0

    def seal(self) -> None:
        if self.sealed:
            raise EvidenceError("collector HTTP acquisition was already sealed")
        self.sealed = True

    def download_exact(
        self,
        url: str,
        target: Path,
        expected_sha256: str,
        expected_size: int,
        maximum_size: int,
    ) -> Dict[str, Any]:
        if self.sealed:
            raise EvidenceError("collector HTTP attempted after acquisition seal")
        validate_https_url(url, self.allowed_hosts, "download URL")
        validate_sha256(expected_sha256, "download SHA-256")
        if not isinstance(expected_size, int) or not 1 <= expected_size <= maximum_size:
            raise EvidenceError("download size is outside its locked bound")
        if self.downloaded_bytes + expected_size > MAX_TOTAL_DOWNLOAD_BYTES:
            raise EvidenceError("capture exceeds the total download bound")
        if target.exists() or target.is_symlink():
            raise EvidenceError("download target already exists: {}".format(target))
        target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        if target.parent.is_symlink() or not target.parent.is_dir():
            raise EvidenceError("download parent is unsafe: {}".format(target.parent))
        request = urllib.request.Request(
            url,
            headers={
                "Accept-Encoding": "identity",
                "User-Agent": "mckernel-platform-evidence/1",
            },
        )
        digest = hashlib.sha256()
        size = 0
        try:
            with self.opener.open(request, timeout=60) as response:
                if response.geturl() != url:
                    raise EvidenceError("download final URL differs from its lock")
                status = getattr(response, "status", None)
                if status != 200:
                    raise EvidenceError("download returned HTTP {}".format(status))
                headers = response.headers
                lengths = headers.get_all("Content-Length", [])
                if len(lengths) != 1 or lengths[0] != str(expected_size):
                    raise EvidenceError("download Content-Length differs from its lock")
                encodings = headers.get_all("Content-Encoding", [])
                if encodings:
                    raise EvidenceError("encoded HTTP response is forbidden")
                with target.open("xb") as output:
                    while True:
                        chunk = response.read(1024 * 1024)
                        if not chunk:
                            break
                        size += len(chunk)
                        if size > expected_size or size > maximum_size:
                            raise EvidenceError("download exceeded its locked size")
                        digest.update(chunk)
                        output.write(chunk)
                    output.flush()
                    os.fsync(output.fileno())
            if size != expected_size or digest.hexdigest() != expected_sha256:
                raise EvidenceError("download bytes differ from the locked identity")
            target.chmod(0o400)
        except (OSError, urllib.error.URLError, EvidenceError) as exc:
            try:
                target.unlink()
            except FileNotFoundError:
                pass
            if isinstance(exc, EvidenceError):
                raise
            raise EvidenceError("download failed: {}".format(exc)) from exc
        self.downloaded_bytes += size
        return {
            "final_url": url,
            "redirect_count": 0,
            "sha256": expected_sha256,
            "size": size,
        }


def parse_release_key_fingerprints(output: bytes, expected: str) -> Dict[str, Any]:
    try:
        lines = output.decode("utf-8").splitlines()
    except UnicodeDecodeError as exc:
        raise EvidenceError("gpg key listing is not UTF-8") from exc
    fingerprints = [line.split(":")[9] for line in lines if line.startswith("fpr:") and len(line.split(":")) > 9]
    if fingerprints.count(expected) != 1:
        raise EvidenceError("release key fingerprint is missing or ambiguous")
    return {"fingerprint": expected, "fingerprints_seen": fingerprints}


def create_verification_keyrings(key_path: Path, temporary: Path, expected_fingerprint: str) -> Tuple[Path, Path]:
    gpg_home = temporary / "gpg-home"
    gpg_home.mkdir(mode=0o700)
    listing, listing_stderr = run_command(
        [
            "gpg",
            "--batch",
            "--homedir",
            str(gpg_home),
            "--show-keys",
            "--with-colons",
            str(key_path),
        ]
    )
    # A fresh, private GnuPG home reports keybox/trustdb creation on stderr;
    # command success plus the exact parsed primary fingerprint is the
    # security decision, not silence from this diagnostic channel.
    del listing_stderr
    parse_release_key_fingerprints(listing, expected_fingerprint)
    gpg_keyring = temporary / "rocky-10.gpg"
    run_command(
        [
            "gpg",
            "--batch",
            "--homedir",
            str(gpg_home),
            "--yes",
            "--dearmor",
            "--output",
            str(gpg_keyring),
            str(key_path),
        ]
    )
    if not gpg_keyring.is_file() or gpg_keyring.stat().st_size < 1:
        raise EvidenceError("gpg keyring was not created")
    rpm_db = create_private_rpmdb(key_path, temporary / "rpmdb")
    return gpg_keyring, rpm_db


def create_private_rpmdb(key_path: Path, rpm_db: Path) -> Path:
    if rpm_db.exists() or rpm_db.is_symlink():
        raise EvidenceError("private RPM database path already exists")
    rpm_db.mkdir(mode=0o700)
    run_command(["rpm", "--dbpath", str(rpm_db), "--initdb"])
    run_command(["rpmkeys", "--dbpath", str(rpm_db), "--import", str(key_path)])
    return rpm_db


def parse_gpgv_status(status: bytes, expected_fingerprint: str) -> Dict[str, Any]:
    try:
        text = status.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise EvidenceError("gpgv status is not UTF-8") from exc
    if any(marker in text for marker in (" BADSIG ", " ERRSIG ", " NO_PUBKEY ", " EXPKEYSIG ", " REVKEYSIG ")):
        raise EvidenceError("gpgv reported a bad or unusable signature")
    fingerprints = []
    for line in text.splitlines():
        if line.startswith("[GNUPG:] VALIDSIG "):
            fields = line.split()
            if len(fields) < 3:
                raise EvidenceError("malformed gpgv VALIDSIG status")
            fingerprints.append(fields[2])
    if fingerprints != [expected_fingerprint]:
        raise EvidenceError("repomd signature fingerprint differs from its lock")
    return {"status": "verified", "validsig_fingerprint": expected_fingerprint}


def verify_repomd_signature(
    repomd_path: Path,
    signature_path: Path,
    keyring_path: Path,
    expected_fingerprint: str,
) -> Tuple[Dict[str, Any], bytes]:
    stdout, stderr = run_command(
        [
            "gpgv",
            "--status-fd",
            "1",
            "--keyring",
            str(keyring_path),
            str(signature_path),
            str(repomd_path),
        ]
    )
    result = parse_gpgv_status(stdout, expected_fingerprint)
    transcript = b"stdout:\n" + stdout + b"stderr:\n" + stderr
    result["transcript_sha256"] = sha256_bytes(transcript)
    result["transcript_size"] = len(transcript)
    return result, transcript


def parse_repomd(repomd_bytes: bytes, repository: Mapping[str, Any]) -> Dict[str, Any]:
    if b"<!DOCTYPE" in repomd_bytes.upper() or b"<!ENTITY" in repomd_bytes.upper():
        raise EvidenceError("repomd XML declarations are forbidden")
    try:
        root = ET.fromstring(repomd_bytes)
    except ET.ParseError as exc:
        raise EvidenceError("cannot parse repomd XML: {}".format(exc)) from exc
    if root.tag != "{{{}}}repomd".format(REPO_NS):
        raise EvidenceError("repomd root namespace changed")
    revision = root.findtext("{{{}}}revision".format(REPO_NS))
    require_exact(revision, repository["repomd"]["revision"], "repomd revision")
    primary_rows = [
        row
        for row in root.findall("{{{}}}data".format(REPO_NS))
        if row.get("type") == "primary"
    ]
    if len(primary_rows) != 1:
        raise EvidenceError("repomd must contain exactly one primary row")
    row = primary_rows[0]
    checksum = row.find("{{{}}}checksum".format(REPO_NS))
    open_checksum = row.find("{{{}}}open-checksum".format(REPO_NS))
    location = row.find("{{{}}}location".format(REPO_NS))
    if checksum is None or checksum.get("type") != "sha256":
        raise EvidenceError("repomd primary checksum is not SHA-256")
    if open_checksum is None or open_checksum.get("type") != "sha256":
        raise EvidenceError("repomd primary open checksum is not SHA-256")
    if location is None:
        raise EvidenceError("repomd primary location is missing")
    observed = {
        "href": location.get("href"),
        "open_sha256": open_checksum.text,
        "open_size": int(row.findtext("{{{}}}open-size".format(REPO_NS), "-1")),
        "sha256": checksum.text,
        "size": int(row.findtext("{{{}}}size".format(REPO_NS), "-1")),
    }
    require_exact(observed, repository["primary"], "repomd primary identity")
    return {"primary": observed, "revision": revision}


def verify_primary_open_identity(path: Path, expected_sha256: str, expected_size: int) -> Dict[str, Any]:
    digest = hashlib.sha256()
    size = 0
    forbidden_tail = b""
    try:
        with gzip.open(path, "rb") as stream:
            while True:
                chunk = stream.read(1024 * 1024)
                if not chunk:
                    break
                size += len(chunk)
                if size > expected_size or size > MAX_PRIMARY_OPEN_BYTES:
                    raise EvidenceError("primary metadata expands beyond its lock")
                digest.update(chunk)
                scan = (forbidden_tail + chunk).upper()
                if b"<!DOCTYPE" in scan or b"<!ENTITY" in scan:
                    raise EvidenceError("primary metadata XML declarations are forbidden")
                forbidden_tail = scan[-16:]
    except (OSError, EOFError) as exc:
        raise EvidenceError("cannot decompress primary metadata: {}".format(exc)) from exc
    if size != expected_size or digest.hexdigest() != expected_sha256:
        raise EvidenceError("open primary metadata differs from repomd")
    return {"open_sha256": expected_sha256, "open_size": size}


def artifact_metadata_key(item: Mapping[str, Any]) -> Tuple[str, str, str, str, str]:
    return (
        str(item["name"]),
        str(item["arch"]),
        str(item["epoch"]),
        str(item["version"]),
        str(item["release"]),
    )


def expand_bootstrap_artifact(item: Mapping[str, Any]) -> Dict[str, Any]:
    match = BOOTSTRAP_NEVRA.fullmatch(str(item["nevra"]))
    if match is None:
        raise EvidenceError("bootstrap artifact NEVRA is malformed")
    name, epoch, version, release, arch = match.groups()
    return {
        "arch": arch,
        "epoch": int(epoch),
        "name": name,
        "nevra": item["nevra"],
        "release": release,
        "repository_id": item["repository_id"],
        "repository_location": item["repository_location"],
        "sha256": item["sha256"],
        "size": item["size"],
        "version": version,
    }


def parse_primary_artifacts(
    primary_path: Path,
    repository_id: str,
    expected_artifacts: Sequence[Mapping[str, Any]],
) -> Dict[str, Dict[str, Any]]:
    expected = {artifact_metadata_key(item): item for item in expected_artifacts}
    if len(expected) != len(expected_artifacts):
        raise EvidenceError("direct artifact identities are not unique")
    found: Dict[Tuple[str, str, str, str, str], Dict[str, Any]] = {}
    try:
        with gzip.open(primary_path, "rb") as stream:
            iterator = ET.iterparse(stream, events=("end",))
            for _, element in iterator:
                if element.tag != "{{{}}}package".format(COMMON_NS):
                    continue
                name = element.findtext("{{{}}}name".format(COMMON_NS))
                arch = element.findtext("{{{}}}arch".format(COMMON_NS))
                version = element.find("{{{}}}version".format(COMMON_NS))
                if version is None:
                    raise EvidenceError("primary package version is missing")
                key = (
                    str(name),
                    str(arch),
                    str(version.get("epoch")),
                    str(version.get("ver")),
                    str(version.get("rel")),
                )
                if key in expected:
                    if key in found:
                        raise EvidenceError("primary metadata duplicates a direct artifact")
                    checksum = element.find("{{{}}}checksum".format(COMMON_NS))
                    location = element.find("{{{}}}location".format(COMMON_NS))
                    size = element.find("{{{}}}size".format(COMMON_NS))
                    if checksum is None or checksum.get("type") != "sha256" or checksum.get("pkgid") != "YES":
                        raise EvidenceError("direct artifact primary checksum is malformed")
                    if location is None or size is None:
                        raise EvidenceError("direct artifact primary row is incomplete")
                    observed = {
                        "location": location.get("href"),
                        "sha256": checksum.text,
                        "size": int(size.get("package", "-1")),
                    }
                    locked = expected[key]
                    require_exact(observed["location"], locked["repository_location"], "{} primary location".format(locked["nevra"]))
                    require_exact(observed["sha256"], locked["sha256"], "{} primary digest".format(locked["nevra"]))
                    require_exact(observed["size"], locked["size"], "{} primary size".format(locked["nevra"]))
                    found[key] = observed
                element.clear()
            root = iterator.root
    except (OSError, EOFError, ET.ParseError, ValueError) as exc:
        raise EvidenceError("cannot parse primary metadata: {}".format(exc)) from exc
    if root.tag != "{{{}}}metadata".format(COMMON_NS):
        raise EvidenceError("primary metadata root namespace changed")
    if set(found) != set(expected):
        missing = sorted(set(expected) - set(found))
        raise EvidenceError("signed {} primary metadata lacks direct artifacts: {}".format(repository_id, missing))
    return {expected[key]["nevra"]: found[key] for key in sorted(found)}


def parse_rpm_signature(output: bytes, expected_fingerprint: str) -> Dict[str, Any]:
    try:
        text = output.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise EvidenceError("rpmkeys output is not UTF-8") from exc
    upper = text.upper()
    if any(marker in upper for marker in ("NOT OK", "NOKEY", "BAD", "NOTTRUSTED")):
        raise EvidenceError("rpmkeys rejected an RPM signature")
    matches = RPM_HEADER_SIGNATURE.findall(text)
    if len(matches) != 1:
        raise EvidenceError("RPM must have exactly one verified header signature")
    algorithm, key_id = matches[0]
    if len(key_id) < 8 or not expected_fingerprint.upper().endswith(key_id.upper()):
        raise EvidenceError("RPM signer key ID differs from the Rocky release key")
    if "SHA256 DIGEST: OK" not in upper or "PAYLOAD SHA256 DIGEST: OK" not in upper:
        raise EvidenceError("RPM header and payload SHA-256 digests were not both verified")
    return {
        "header_signature_algorithm": algorithm.upper(),
        "signer_fingerprint": expected_fingerprint,
        "signer_key_id": key_id.upper(),
        "status": "verified",
    }


def verify_rpm_signature(
    rpm_path: Path, rpm_db: Path, expected_fingerprint: str
) -> Tuple[Dict[str, Any], bytes]:
    stdout, stderr = run_command(
        ["rpmkeys", "--dbpath", str(rpm_db), "--checksig", "--verbose", str(rpm_path)]
    )
    combined = stdout + stderr
    result = parse_rpm_signature(combined, expected_fingerprint)
    transcript = b"stdout:\n" + stdout + b"stderr:\n" + stderr
    result["transcript_sha256"] = sha256_bytes(transcript)
    result["transcript_size"] = len(transcript)
    return result, transcript


def parse_rpm_inventory_bytes(data: bytes, label: str) -> List[str]:
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise EvidenceError("{} is not UTF-8".format(label)) from exc
    if not text or not text.endswith("\n"):
        raise EvidenceError("{} must be non-empty and newline-terminated".format(label))
    packages = text.splitlines()
    if any(not item or any(ord(character) < 32 for character in item) for item in packages):
        raise EvidenceError("{} contains malformed package rows".format(label))
    if packages != sorted(packages) or len(packages) != len(set(packages)):
        raise EvidenceError("{} must contain sorted unique NEVRAs".format(label))
    return packages


def rpm_inventory() -> Tuple[List[str], bytes]:
    stdout, stderr = run_command(
        [
            "rpm",
            "-qa",
            "--qf",
            "%{NAME}-%{EPOCHNUM}:%{VERSION}-%{RELEASE}.%{ARCH}\\n",
        ]
    )
    if stderr:
        raise EvidenceError("RPM inventory unexpectedly wrote stderr")
    try:
        raw_rows = stdout.decode("utf-8").splitlines()
    except UnicodeDecodeError as exc:
        raise EvidenceError("RPM inventory is not UTF-8") from exc
    if not raw_rows or any(
        not item or any(ord(character) < 32 for character in item)
        for item in raw_rows
    ):
        raise EvidenceError("RPM inventory contains malformed package rows")
    if len(raw_rows) != len(set(raw_rows)):
        raise EvidenceError("RPM inventory contains duplicate NEVRAs")
    packages = sorted(raw_rows)
    data = ("\n".join(packages) + "\n").encode("utf-8")
    return packages, data


def locked_base_release_key(plan: Mapping[str, Any]) -> Tuple[Path, Dict[str, Any]]:
    key_path = external_regular_file(BASE_RELEASE_KEY_PATH, "base-container release key")
    size, digest = sha256_file(key_path)
    require_exact(size, plan["release_key"]["size"], "base release-key size")
    require_exact(digest, plan["release_key"]["sha256"], "base release-key digest")
    return key_path, {
        "fingerprint": plan["release_key"]["fingerprint"],
        "path": BASE_RELEASE_KEY_PATH.as_posix(),
        "private_rpmdb": True,
        "sha256": digest,
        "size": size,
    }


def capture_bootstrap(
    repo: Path,
    output_dir: Path,
    identity: Mapping[str, Any],
    plan: Mapping[str, Any],
) -> None:
    if platform.machine() != "x86_64" or sys.maxsize <= 2 ** 32:
        raise EvidenceError("bootstrap runtime is not 64-bit x86_64")
    parse_os_release(Path("/etc/os-release").read_bytes())
    for tool in ("dnf", "python3", "rpm", "rpmkeys"):
        if shutil.which(tool) is None:
            raise EvidenceError("base container lacks bootstrap tool: {}".format(tool))
    before_packages, before_bytes = rpm_inventory()
    bootstrap = plan["bootstrap"]
    require_exact(len(before_packages), bootstrap["base_package_count"], "base package count")
    require_exact(
        sha256_bytes(before_bytes),
        bootstrap["base_package_manifest_sha256"],
        "base package manifest",
    )
    write_output_bytes(output_dir, PurePosixPath("before-rpms.txt"), before_bytes)
    key_path, key_anchor = locked_base_release_key(plan)

    repositories = {item["id"]: item for item in plan["repositories"]}
    session = NetworkSession(
        plan["network_policy"]["collector_http_allowed_hosts_before_seal"]
    )
    artifact_results: List[Dict[str, Any]] = []
    rpm_paths: List[Path] = []
    with tempfile.TemporaryDirectory(prefix="mckernel-bootstrap-rpmdb-") as temporary_text:
        rpm_db = create_private_rpmdb(key_path, Path(temporary_text) / "rpmdb")
        for artifact in bootstrap["artifacts"]:
            repository = repositories[artifact["repository_id"]]
            filename = PurePosixPath(artifact["repository_location"]).name
            relative = PurePosixPath("rpms") / filename
            rpm_path = output_path(output_dir, relative)
            download = session.download_exact(
                repository["base_url"] + artifact["repository_location"],
                rpm_path,
                artifact["sha256"],
                artifact["size"],
                MAX_RPM_DOWNLOAD_BYTES,
            )
            signature, transcript = verify_rpm_signature(
                rpm_path, rpm_db, plan["release_key"]["fingerprint"]
            )
            transcript_relative = PurePosixPath("rpmkeys") / (filename + ".txt")
            write_output_bytes(output_dir, transcript_relative, transcript)
            artifact_results.append(
                {
                    "archive_path": relative.as_posix(),
                    "download": download,
                    "nevra": artifact["nevra"],
                    "signature": signature,
                }
            )
            rpm_paths.append(rpm_path)
    require_exact(session.downloaded_bytes, bootstrap["total_bytes"], "bootstrap downloads")
    session.seal()

    defended_env = subprocess_network_defense_env(os.environ)
    install_command = [
        "dnf",
        "--noplugins",
        "--cacheonly",
        "--disablerepo=*",
        "--setopt=install_weak_deps=False",
        "--setopt=keepcache=False",
        "-y",
        "install",
    ] + [str(path) for path in rpm_paths]
    install_stdout, install_stderr = run_command(install_command, env=defended_env)
    install_transcript = (
        b"command: dnf --noplugins --cacheonly --disablerepo=* "
        b"--setopt=install_weak_deps=False --setopt=keepcache=False -y "
        b"install <47 digest-verified local RPMs>\nstdout:\n"
        + install_stdout
        + b"stderr:\n"
        + install_stderr
    )
    write_output_bytes(
        output_dir, PurePosixPath("local-rpm-install.txt"), install_transcript
    )
    after_packages, after_bytes = rpm_inventory()
    expected_added = sorted(item["nevra"] for item in bootstrap["artifacts"])
    if set(before_packages).intersection(expected_added):
        raise EvidenceError("bootstrap artifacts overlap the locked base inventory")
    expected_after = sorted(before_packages + expected_added)
    require_exact(after_packages, expected_after, "post-bootstrap package inventory")
    actual_added = sorted(set(after_packages) - set(before_packages))
    removed = sorted(set(before_packages) - set(after_packages))
    require_exact(actual_added, expected_added, "local bootstrap additions")
    require_exact(removed, [], "local bootstrap removals")
    require_exact(
        len(after_packages), len(before_packages) + len(expected_added), "post-bootstrap package count"
    )
    write_output_bytes(output_dir, PurePosixPath("after-rpms.txt"), after_bytes)

    manifest = {
        "artifacts": artifact_results,
        "base_package_count": len(before_packages),
        "base_package_manifest_sha256": sha256_bytes(before_bytes),
        "checkpoint_id": CHECKPOINT_ID,
        "container_image": CONTAINER_IMAGE,
        "github": dict(identity),
        "network": {
            "collector_http_downloaded_bytes": session.downloaded_bytes,
            "collector_http_sealed_before_dnf": session.sealed,
            "dnf_repository_access": "disabled-cache-only",
            "network_isolation_claimed": False,
            "scope": COLLECTOR_NETWORK_SCOPE,
            "subprocess_proxy_defense_enabled": True,
        },
        "local_rpm_install": {
            "added_nevras": actual_added,
            "after_package_count": len(after_packages),
            "after_package_manifest_sha256": sha256_bytes(after_bytes),
            "removed_nevras": removed,
            "status": "verified",
            "transcript_sha256": sha256_bytes(install_transcript),
        },
        "phase_plan_sha256": EXPECTED_PLAN_SHA256,
        "release_key_anchor": key_anchor,
        "schema_version": SCHEMA_VERSION,
    }
    write_output_json(output_dir, PurePosixPath("bootstrap.json"), manifest)
    write_sha256sums(output_dir)
    print_json_blocks(output_dir, ["bootstrap.json"])


def external_regular_file(path: Path, label: str) -> Path:
    if not path.is_absolute() or path.is_symlink() or not path.is_file():
        raise EvidenceError("{} must be an absolute regular file".format(label))
    resolved = path.resolve()
    if resolved != path:
        raise EvidenceError("{} uses symlink traversal".format(label))
    return path


def validate_bootstrap_manifest(
    path: Path,
    identity: Mapping[str, Any],
    plan: Mapping[str, Any],
) -> Tuple[Dict[str, Any], bytes]:
    manifest_path = external_regular_file(path, "bootstrap manifest")
    data = manifest_path.read_bytes()
    manifest = strict_json_bytes(data, "bootstrap manifest")
    if data != canonical_json_bytes(manifest):
        raise EvidenceError("bootstrap manifest is not canonical JSON")
    exact_keys(
        manifest,
        {
            "artifacts",
            "base_package_count",
            "base_package_manifest_sha256",
            "checkpoint_id",
            "container_image",
            "github",
            "network",
            "local_rpm_install",
            "phase_plan_sha256",
            "release_key_anchor",
            "schema_version",
        },
        "bootstrap manifest",
    )
    require_exact(manifest["schema_version"], SCHEMA_VERSION, "bootstrap schema")
    require_exact(manifest["checkpoint_id"], CHECKPOINT_ID, "bootstrap checkpoint")
    require_exact(manifest["container_image"], CONTAINER_IMAGE, "bootstrap container")
    require_exact(manifest["github"], dict(identity), "bootstrap GitHub identity")
    require_exact(manifest["phase_plan_sha256"], EXPECTED_PLAN_SHA256, "bootstrap plan")
    require_exact(
        manifest["base_package_count"], plan["bootstrap"]["base_package_count"], "bootstrap base count"
    )
    require_exact(
        manifest["base_package_manifest_sha256"],
        plan["bootstrap"]["base_package_manifest_sha256"],
        "bootstrap base package digest",
    )
    network = manifest["network"]
    require_exact(
        network,
        {
            "collector_http_downloaded_bytes": plan["bootstrap"]["total_bytes"],
            "collector_http_sealed_before_dnf": True,
            "dnf_repository_access": "disabled-cache-only",
            "network_isolation_claimed": False,
            "scope": COLLECTOR_NETWORK_SCOPE,
            "subprocess_proxy_defense_enabled": True,
        },
        "bootstrap network state",
    )
    expected_nevras = sorted(item["nevra"] for item in plan["bootstrap"]["artifacts"])
    before_path = external_regular_file(
        manifest_path.parent / "before-rpms.txt", "bootstrap base inventory"
    )
    before_bytes = before_path.read_bytes()
    before_packages = parse_rpm_inventory_bytes(before_bytes, "bootstrap base inventory")
    require_exact(
        len(before_packages), plan["bootstrap"]["base_package_count"], "bootstrap base count"
    )
    require_exact(
        sha256_bytes(before_bytes),
        plan["bootstrap"]["base_package_manifest_sha256"],
        "bootstrap base inventory digest",
    )
    if set(before_packages).intersection(expected_nevras):
        raise EvidenceError("bootstrap artifacts overlap the locked base inventory")
    expected_after_packages = sorted(before_packages + expected_nevras)
    expected_after_bytes = ("\n".join(expected_after_packages) + "\n").encode("utf-8")
    install = exact_keys(
        manifest["local_rpm_install"],
        {
            "added_nevras",
            "after_package_count",
            "after_package_manifest_sha256",
            "removed_nevras",
            "status",
            "transcript_sha256",
        },
        "bootstrap install record",
    )
    require_exact(install.get("status"), "verified", "bootstrap install status")
    require_exact(install.get("added_nevras"), expected_nevras, "bootstrap additions")
    require_exact(install.get("removed_nevras"), [], "bootstrap removals")
    require_exact(
        install.get("after_package_count"),
        len(expected_after_packages),
        "bootstrap after package count",
    )
    require_exact(
        install.get("after_package_manifest_sha256"),
        sha256_bytes(expected_after_bytes),
        "bootstrap after package digest",
    )
    validate_sha256(install.get("transcript_sha256"), "bootstrap install transcript")
    after_path = external_regular_file(
        manifest_path.parent / "after-rpms.txt", "bootstrap after inventory"
    )
    require_exact(
        after_path.read_bytes(), expected_after_bytes, "bootstrap after inventory bytes"
    )
    key_path, key_anchor = locked_base_release_key(plan)
    require_exact(manifest["release_key_anchor"], key_anchor, "bootstrap release-key anchor")
    artifacts = manifest["artifacts"]
    if not isinstance(artifacts, list) or len(artifacts) != len(expected_nevras):
        raise EvidenceError("bootstrap artifact results are incomplete")
    if [item.get("nevra") for item in artifacts if isinstance(item, dict)] != expected_nevras:
        raise EvidenceError("bootstrap artifact result order or identity changed")
    repository_urls = {item["id"]: item["base_url"] for item in plan["repositories"]}
    with tempfile.TemporaryDirectory(prefix="mckernel-bootstrap-replay-rpmdb-") as temporary_text:
        rpm_db = create_private_rpmdb(key_path, Path(temporary_text) / "rpmdb")
        for result, locked in zip(artifacts, plan["bootstrap"]["artifacts"]):
            result_row = exact_keys(
                result,
                {"archive_path", "download", "nevra", "signature"},
                "bootstrap artifact result",
            )
            require_exact(result_row["nevra"], locked["nevra"], "bootstrap artifact NEVRA")
            filename = PurePosixPath(locked["repository_location"]).name
            expected_relative = "rpms/{}".format(filename)
            require_exact(result_row["archive_path"], expected_relative, "bootstrap archive path")
            require_exact(
                result_row["download"],
                {
                    "final_url": repository_urls[locked["repository_id"]]
                    + locked["repository_location"],
                    "redirect_count": 0,
                    "sha256": locked["sha256"],
                    "size": locked["size"],
                },
                "bootstrap download record",
            )
            rpm_path = external_regular_file(
                manifest_path.parent / "rpms" / filename, "bootstrap RPM archive"
            )
            size, digest = sha256_file(rpm_path)
            require_exact(size, locked["size"], "bootstrap RPM size")
            require_exact(digest, locked["sha256"], "bootstrap RPM digest")
            verified_signature, _ = verify_rpm_signature(
                rpm_path, rpm_db, plan["release_key"]["fingerprint"]
            )
            require_exact(
                result_row["signature"], verified_signature, "bootstrap RPM signature replay"
            )
    current_packages, current_bytes = rpm_inventory()
    require_exact(
        current_packages, expected_after_packages, "current bootstrap package inventory"
    )
    require_exact(
        current_bytes, expected_after_bytes, "current bootstrap package manifest bytes"
    )
    return manifest, data


def parse_buildrequires(output: bytes, reviewed_additions: Sequence[str]) -> Dict[str, Any]:
    try:
        lines = output.decode("utf-8").splitlines()
    except UnicodeDecodeError as exc:
        raise EvidenceError("rpmspec BuildRequires output is not UTF-8") from exc
    requirements = sorted(set(line.strip() for line in lines if line.strip()))
    if not requirements or len(requirements) > MAX_BUILDREQUIRES:
        raise EvidenceError("rpmspec returned an implausible BuildRequires set")
    for requirement in requirements:
        if any(ord(character) < 32 or ord(character) > 126 for character in requirement):
            raise EvidenceError("BuildRequires contains non-printable text")
        if "%{" in requirement or "%(" in requirement:
            raise EvidenceError("BuildRequires contains an unresolved RPM macro")
    for addition in reviewed_additions:
        pattern = re.compile(r"^{}(?:\s|$)".format(re.escape(addition)))
        if any(pattern.search(requirement) for requirement in requirements):
            raise EvidenceError(
                "Rocky-effective spec unexpectedly contains reviewed addition {}".format(addition)
            )
    return {
        "rocky_effective": requirements,
        "reviewed_rocky_rust_additions": list(reviewed_additions),
    }


def prepare_output_dir(path: Path) -> Path:
    if not path.is_absolute():
        raise EvidenceError("evidence output directory must be absolute")
    parent = path.parent
    if not parent.exists() or parent.is_symlink() or not parent.is_dir():
        raise EvidenceError("evidence output parent is unsafe")
    if parent.resolve() != parent:
        raise EvidenceError("evidence output parent uses symlink traversal")
    if path.exists() or path.is_symlink():
        raise EvidenceError("evidence output directory already exists")
    path.mkdir(mode=0o700)
    if path.resolve() != path:
        raise EvidenceError("evidence output directory resolved unexpectedly")
    return path


def output_path(root: Path, relative: PurePosixPath) -> Path:
    normalized = normalized_relative_path(relative.as_posix(), "output path")
    candidate = root.joinpath(*normalized.parts)
    if not within(root, candidate.resolve(strict=False)):
        raise EvidenceError("output path escapes evidence root")
    current = root
    for part in normalized.parts[:-1]:
        current = current / part
        if current.exists() and (current.is_symlink() or not current.is_dir()):
            raise EvidenceError("output parent is unsafe: {}".format(current))
    return candidate


def write_output_bytes(root: Path, relative: PurePosixPath, data: bytes) -> Path:
    target = output_path(root, relative)
    target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    if target.exists() or target.is_symlink():
        raise EvidenceError("output already exists: {}".format(relative))
    try:
        with target.open("xb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        target.chmod(0o400)
    except OSError as exc:
        try:
            target.unlink()
        except FileNotFoundError:
            pass
        raise EvidenceError("cannot publish output {}: {}".format(relative, exc)) from exc
    return target


def write_output_json(root: Path, relative: PurePosixPath, value: Mapping[str, Any]) -> Path:
    return write_output_bytes(root, relative, canonical_json_bytes(value))


def write_sha256sums(root: Path) -> Path:
    rows: List[str] = []
    for path in sorted(root.rglob("*")):
        if path == root / "SHA256SUMS":
            continue
        if path.is_symlink():
            raise EvidenceError("evidence output contains a symlink")
        if path.is_dir():
            continue
        if not path.is_file():
            raise EvidenceError("evidence output contains a non-regular file")
        relative = path.relative_to(root).as_posix()
        _, digest = sha256_file(path)
        rows.append("{}  {}".format(digest, relative))
    if not rows:
        raise EvidenceError("evidence output is empty")
    return write_output_bytes(root, PurePosixPath("SHA256SUMS"), ("\n".join(rows) + "\n").encode("ascii"))


def print_json_blocks(root: Path, names: Sequence[str]) -> None:
    for name in names:
        path = output_path(root, PurePosixPath(name))
        data = path.read_bytes()
        strict_json_bytes(data, name)
        print(
            "MCKERNEL_PLATFORM_EVIDENCE_JSON_BEGIN {} sha256={}".format(
                name, sha256_bytes(data)
            )
        )
        print(base64.b64encode(data).decode("ascii"))
        print("MCKERNEL_PLATFORM_EVIDENCE_JSON_END {}".format(name))


def source_raw_url(source: Mapping[str, Any], relative: str) -> str:
    commit = source["dist_git"]["commit"]
    normalized = normalized_relative_path(relative, "dist-git path")
    encoded_path = urllib.parse.quote(normalized.as_posix(), safe="/")
    return (
        "https://git.rockylinux.org/staging/rpms/kernel/-/raw/"
        + commit
        + "/"
        + encoded_path
    )


def capture_repository_direct(
    repo: Path,
    output_dir: Path,
    identity: Mapping[str, Any],
    plan: Mapping[str, Any],
    toolchain: Mapping[str, Any],
    config: Mapping[str, Any],
    source: Mapping[str, Any],
    toolchain_blockers: Sequence[str],
    config_blockers: Sequence[str],
    source_blockers: Sequence[str],
    bootstrap_manifest_path: Path,
) -> None:
    bootstrap_manifest, bootstrap_manifest_bytes = validate_bootstrap_manifest(
        bootstrap_manifest_path, identity, plan
    )
    committed_inputs = [
        committed_file_identity(repo, str(identity["head_sha"]), relative)
        for relative in (
            PLAN_PATH,
            TOOLCHAIN_LOCK_PATH,
            CONFIG_POLICY_PATH,
            CONFIG_FRAGMENT_PATH,
            SOURCE_LOCK_PATH,
            PATCH_SERIES_PATH,
            PLATFORM_VALIDATOR_PATH,
            SOURCE_VALIDATOR_PATH,
            CAPTURE_SCRIPT_PATH,
            WORKFLOW_PATH,
        )
    ]
    head_stdout, _ = run_git(repo, ["rev-parse", "HEAD"])
    if head_stdout.decode("ascii").strip() != identity["head_sha"]:
        raise EvidenceError("checkout HEAD differs from the requested GitHub head")

    environment = capture_runtime_environment(output_dir / "transcripts")
    environment["github"] = dict(identity)
    environment["committed_inputs"] = committed_inputs
    environment["bootstrap"] = {
        "after_package_manifest_sha256": bootstrap_manifest["local_rpm_install"][
            "after_package_manifest_sha256"
        ],
        "manifest_sha256": sha256_bytes(bootstrap_manifest_bytes),
        "local_rpm_install_verified": True,
    }
    write_output_bytes(
        output_dir,
        PurePosixPath("bootstrap-input.json"),
        bootstrap_manifest_bytes,
    )

    session = NetworkSession(
        plan["network_policy"]["collector_http_allowed_hosts_before_seal"]
    )
    release_key = plan["release_key"]
    key_path = output_path(output_dir, PurePosixPath("archives/repositories/RPM-GPG-KEY-Rocky-10"))
    key_download = session.download_exact(
        release_key["url"],
        key_path,
        release_key["sha256"],
        release_key["size"],
        MAX_SMALL_DOWNLOAD_BYTES,
    )

    metadata_by_nevra: Dict[str, Dict[str, Any]] = {}
    for artifact in toolchain["direct_artifacts"]:
        metadata_by_nevra[artifact["nevra"]] = dict(artifact)
    for compact in plan["bootstrap"]["artifacts"]:
        artifact = expand_bootstrap_artifact(compact)
        prior = metadata_by_nevra.get(artifact["nevra"])
        if prior is not None:
            for field in (
                "arch",
                "epoch",
                "name",
                "release",
                "repository_id",
                "repository_location",
                "sha256",
                "size",
                "version",
            ):
                require_exact(
                    artifact[field], prior[field], "overlapping RPM {}".format(field)
                )
        else:
            metadata_by_nevra[artifact["nevra"]] = artifact
    direct_by_repository: Dict[str, List[Mapping[str, Any]]] = {
        repository_id: [] for repository_id in EXPECTED_REPOSITORY_IDS
    }
    for artifact in metadata_by_nevra.values():
        direct_by_repository[artifact["repository_id"]].append(artifact)

    repository_results: List[Dict[str, Any]] = []
    metadata_matches: Dict[str, Dict[str, Any]] = {}
    direct_results: List[Dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix="mckernel-platform-evidence-") as temporary_text:
        temporary = Path(temporary_text)
        gpg_keyring, rpm_db = create_verification_keyrings(
            key_path, temporary, release_key["fingerprint"]
        )
        for repository in plan["repositories"]:
            repository_id = repository["id"]
            repository_root = PurePosixPath("archives/repositories") / repository_id
            repomd_path = output_path(output_dir, repository_root / "repomd.xml")
            signature_path = output_path(output_dir, repository_root / "repomd.xml.asc")
            primary_name = PurePosixPath(repository["primary"]["href"]).name
            primary_path = output_path(output_dir, repository_root / primary_name)
            repomd_download = session.download_exact(
                repository["repomd"]["url"],
                repomd_path,
                repository["repomd"]["sha256"],
                repository["repomd"]["size"],
                MAX_SMALL_DOWNLOAD_BYTES,
            )
            signature_download = session.download_exact(
                repository["signature"]["url"],
                signature_path,
                repository["signature"]["sha256"],
                repository["signature"]["size"],
                MAX_SMALL_DOWNLOAD_BYTES,
            )
            primary_download = session.download_exact(
                repository["base_url"] + repository["primary"]["href"],
                primary_path,
                repository["primary"]["sha256"],
                repository["primary"]["size"],
                MAX_SMALL_DOWNLOAD_BYTES,
            )
            repomd_result = parse_repomd(repomd_path.read_bytes(), repository)
            signature_result, signature_transcript = verify_repomd_signature(
                repomd_path,
                signature_path,
                gpg_keyring,
                release_key["fingerprint"],
            )
            transcript_relative = PurePosixPath("transcripts/repomd") / (repository_id + ".gpgv.txt")
            write_output_bytes(output_dir, transcript_relative, signature_transcript)
            primary_open = verify_primary_open_identity(
                primary_path,
                repository["primary"]["open_sha256"],
                repository["primary"]["open_size"],
            )
            matches = parse_primary_artifacts(
                primary_path,
                repository_id,
                direct_by_repository[repository_id],
            )
            metadata_matches.update(matches)
            repository_results.append(
                {
                    "base_url": repository["base_url"],
                    "id": repository_id,
                    "primary_download": primary_download,
                    "primary_open": primary_open,
                    "repomd": repomd_result,
                    "repomd_download": repomd_download,
                    "signature": signature_result,
                    "signature_download": signature_download,
                }
            )

        for artifact in toolchain["direct_artifacts"]:
            filename = PurePosixPath(artifact["repository_location"]).name
            rpm_relative = PurePosixPath("archives/direct-rpms") / filename
            rpm_path = output_path(output_dir, rpm_relative)
            repository = next(
                item for item in plan["repositories"] if item["id"] == artifact["repository_id"]
            )
            download = session.download_exact(
                repository["base_url"] + artifact["repository_location"],
                rpm_path,
                artifact["sha256"],
                artifact["size"],
                MAX_RPM_DOWNLOAD_BYTES,
            )
            signature, signature_transcript = verify_rpm_signature(
                rpm_path, rpm_db, release_key["fingerprint"]
            )
            transcript_relative = PurePosixPath("transcripts/rpmkeys") / (filename + ".txt")
            write_output_bytes(output_dir, transcript_relative, signature_transcript)
            direct_results.append(
                {
                    "arch": artifact["arch"],
                    "archive_path": rpm_relative.as_posix(),
                    "download": download,
                    "metadata": metadata_matches[artifact["nevra"]],
                    "name": artifact["name"],
                    "nevra": artifact["nevra"],
                    "repository_id": artifact["repository_id"],
                    "signature": signature,
                }
            )

        locked_dist_git = {item["path"]: item for item in source["dist_git"]["content"]}
        for dist_path, output_relative in (
            ("SPECS/kernel.spec", PurePosixPath("inputs/kernel.spec")),
            (
                "SOURCES/kernel-x86_64-rhel.config",
                PurePosixPath("inputs/kernel-x86_64-rhel.config"),
            ),
        ):
            locked = locked_dist_git[dist_path]
            session.download_exact(
                source_raw_url(source, dist_path),
                output_path(output_dir, output_relative),
                locked["sha256"],
                locked["size"],
                MAX_SMALL_DOWNLOAD_BYTES,
            )

        session.seal()
        if not session.sealed:
            raise EvidenceError("collector HTTP acquisition did not seal")

        deterministic_env = subprocess_network_defense_env(os.environ)
        deterministic_env.update(
            {
                "HOME": str(temporary / "home"),
                "LANG": "C",
                "LC_ALL": "C",
                "TZ": "UTC",
            }
        )
        (temporary / "home").mkdir(mode=0o700)
        spec_command = plan["resolution_policy"]["effective_buildrequires_command"]
        spec_stdout, spec_stderr = run_command(
            spec_command,
            cwd=output_dir / "inputs",
            env=deterministic_env,
        )
        buildrequires = parse_buildrequires(
            spec_stdout,
            plan["resolution_policy"]["reviewed_rocky_rust_buildrequires"],
        )
        spec_transcript = b"command: " + " ".join(spec_command).encode("ascii") + b"\nstdout:\n" + spec_stdout + b"stderr:\n" + spec_stderr
        write_output_bytes(
            output_dir,
            PurePosixPath("transcripts/rpmspec-buildrequires.txt"),
            spec_transcript,
        )
        showrc_stdout, showrc_stderr = run_command(["rpm", "--showrc"], env=deterministic_env)
        macro_transcript = b"stdout:\n" + showrc_stdout + b"stderr:\n" + showrc_stderr
        write_output_bytes(
            output_dir, PurePosixPath("transcripts/rpm-showrc.txt"), macro_transcript
        )

    repository_manifest = {
        "release_key": {
            "download": key_download,
            "fingerprint": release_key["fingerprint"],
            "path": "archives/repositories/RPM-GPG-KEY-Rocky-10",
        },
        "repositories": repository_results,
        "schema_version": SCHEMA_VERSION,
    }
    direct_manifest = {
        "all_archives_verified": True,
        "all_header_signatures_verified": True,
        "artifact_count": len(direct_results),
        "artifacts": direct_results,
        "scope": "locked direct RPMs only; this is not the transitive closure",
        "schema_version": SCHEMA_VERSION,
    }
    resolution_roots = []
    for requirement in buildrequires["rocky_effective"]:
        resolution_roots.append({"kind": "rocky-effective-spec", "value": requirement})
    for requirement in buildrequires["reviewed_rocky_rust_additions"]:
        resolution_roots.append({"kind": "reviewed-rocky-rust", "value": requirement})
    for nevra in toolchain["closure"]["direct_nevras"]:
        resolution_roots.append({"kind": "locked-direct-nevra", "value": nevra})
    buildrequires_manifest = {
        "closure_complete": False,
        "direct_nevras": toolchain["closure"]["direct_nevras"],
        "effective_buildrequires": buildrequires["rocky_effective"],
        "kernel_spec_sha256": {
            item["path"]: item["sha256"] for item in source["dist_git"]["content"]
        }["SPECS/kernel.spec"],
        "collector_http_sealed_before_derivation": True,
        "network_isolation_claimed": False,
        "resolution_roots": resolution_roots,
        "reviewed_rocky_rust_additions": buildrequires["reviewed_rocky_rust_additions"],
        "reviewed_source_change_applied": False,
        "rpmspec_output_sha256": sha256_bytes(spec_stdout),
        "rpm_showrc_sha256": sha256_bytes(showrc_stdout),
        "schema_version": SCHEMA_VERSION,
        "source_spec_condition": toolchain["source_spec_observation"]["rust_buildrequires_condition"],
        "transitive_resolution_status": "required-missing",
    }
    blocker_manifest = {
        "config_lock_blockers_at_capture": list(config_blockers),
        "gate_claims": {"RK-003": False, "RK-005": False},
        "phase_blockers": plan["phases"][0]["blockers_after_phase"],
        "source_lock_blockers_at_capture": list(source_blockers),
        "source_lock_credit_eligible_at_capture": not source_blockers,
        "toolchain_lock_blockers_at_capture": list(toolchain_blockers),
    }
    write_output_json(output_dir, PurePosixPath("repository-snapshots.json"), repository_manifest)
    write_output_json(output_dir, PurePosixPath("direct-rpms.json"), direct_manifest)
    write_output_json(output_dir, PurePosixPath("build-requirements.json"), buildrequires_manifest)
    write_output_json(output_dir, PurePosixPath("environment.json"), environment)
    write_output_json(output_dir, PurePosixPath("blockers.json"), blocker_manifest)

    manifest_names = [
        "blockers.json",
        "build-requirements.json",
        "direct-rpms.json",
        "environment.json",
        "repository-snapshots.json",
    ]
    manifests = []
    for name in manifest_names:
        path = output_dir / name
        size, digest = sha256_file(path)
        manifests.append({"path": name, "sha256": digest, "size": size})
    checkpoint = {
        "acquisition": {
            "collector_http_after_seal": False,
            "collector_http_downloaded_bytes": session.downloaded_bytes,
            "collector_http_sealed": session.sealed,
            "network_isolation_claimed": False,
            "scope": COLLECTOR_NETWORK_SCOPE,
        },
        "checkpoint_id": CHECKPOINT_ID,
        "credit_eligible": False,
        "gate_claims": {"RK-003": False, "RK-005": False},
        "github": dict(identity),
        "manifests": manifests,
        "phase": IMPLEMENTED_PHASE,
        "schema_version": SCHEMA_VERSION,
        "successful_capture_requires_review": True,
    }
    write_output_json(output_dir, PurePosixPath("checkpoint.json"), checkpoint)
    write_sha256sums(output_dir)
    print_json_blocks(output_dir, ["checkpoint.json"] + manifest_names)


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[1])
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--check", action="store_true")
    modes.add_argument("--bootstrap", action="store_true")
    modes.add_argument("--run", action="store_true")
    parser.add_argument("--phase", choices=[IMPLEMENTED_PHASE])
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--github-head-sha")
    parser.add_argument("--github-run-id")
    parser.add_argument("--github-run-attempt")
    parser.add_argument("--github-repository")
    parser.add_argument("--container-image")
    parser.add_argument("--bootstrap-manifest", type=Path)
    return parser.parse_args(argv)


def main(argv: Sequence[str]) -> int:
    args = parse_args(argv)
    repo = args.repo.resolve()
    try:
        (
            plan,
            toolchain,
            config,
            source,
            toolchain_blockers,
            config_blockers,
            source_blockers,
        ) = load_locked_inputs(repo)
        validate_workflow_contract(repo)
        if args.check:
            run_only = (
                args.phase,
                args.output_dir,
                args.github_head_sha,
                args.github_run_id,
                args.github_run_attempt,
                args.github_repository,
                args.container_image,
                args.bootstrap_manifest,
            )
            if any(value is not None for value in run_only):
                raise EvidenceError("--check does not accept run-only arguments")
            print(
                "Rocky platform evidence phase plan verified: {}".format(
                    plan["checkpoint_id"]
                )
            )
            print(
                "RK-003/RK-005 remain blocked: {} toolchain and {} config evidence items".format(
                    len(toolchain_blockers), len(config_blockers)
                )
            )
            return 0
        shared_required = {
            "--output-dir": args.output_dir,
            "--github-head-sha": args.github_head_sha,
            "--github-run-id": args.github_run_id,
            "--github-run-attempt": args.github_run_attempt,
            "--github-repository": args.github_repository,
            "--container-image": args.container_image,
        }
        missing = [name for name, value in shared_required.items() if value is None]
        if missing:
            raise EvidenceError("capture requires {}".format(", ".join(missing)))
        identity = validate_run_identity(
            args.github_head_sha,
            args.github_run_id,
            args.github_run_attempt,
            args.github_repository,
            args.container_image,
        )
        if args.bootstrap:
            if args.phase is not None or args.bootstrap_manifest is not None:
                raise EvidenceError("--bootstrap rejects phase and bootstrap-manifest arguments")
            output_dir = prepare_output_dir(args.output_dir)
            capture_bootstrap(repo, output_dir, identity, plan)
            print("installed digest-pinned local bootstrap with repositories disabled: {}".format(output_dir))
            return 0
        if args.phase is None or args.bootstrap_manifest is None:
            raise EvidenceError("--run requires --phase and --bootstrap-manifest")
        require_exact(args.phase, IMPLEMENTED_PHASE, "implemented capture phase")
        output_dir = prepare_output_dir(args.output_dir)
        capture_repository_direct(
            repo,
            output_dir,
            identity,
            plan,
            toolchain,
            config,
            source,
            toolchain_blockers,
            config_blockers,
            source_blockers,
            args.bootstrap_manifest,
        )
        print("captured bounded repository-direct evidence: {}".format(output_dir))
        print("RK-003 and RK-005 remain NOT READY pending reviewed later phases")
        return 0
    except (EvidenceError, OSError, UnicodeError, ValueError) as exc:
        print("Rocky platform evidence error: {}".format(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
