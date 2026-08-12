#!/usr/bin/env python3
"""Validate the bounded historical dd6 Rocky platform evidence review.

The review is deliberately historical.  The GitHub Actions runtime identity is
the original dd6 candidate; a later repository tree is accepted only through
the exact byte and Git-blob identities recorded by the immutable review.  The
historical Git graph is checked when both commits are available, but is not a
requirement for a shallow or content-equivalent published checkout.  Neither
``--check`` nor ``--verify-artifact`` can award RK-003, RK-005, or tracker
credit.
"""

import argparse
import gzip
import hashlib
import io
import json
import os
import re
import shutil
import stat
import struct
import subprocess
import sys
import tempfile
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path, PurePosixPath


REVIEW_PATH = Path(
    "host-kernel/rocky/evidence/platform-repository-review-dd6-v1.json"
)
PLAN_PATH = Path("host-kernel/rocky/evidence-plan-v1.json")
TOOLCHAIN_LOCK_PATH = Path("host-kernel/rocky/toolchain-lock.json")
SOURCE_LOCK_PATH = Path("host-kernel/rocky/source-lock.json")

REVIEW_ID = "rk-003-rk-005-platform-repository-review-dd6-v1"
RUNTIME_HEAD = "dd6d1954538ca1adbaf335a1dd058aba26c28840"
OBSERVED_HEAD = "9ddbee3bb7fc93ee4514da73ac748ad4c820c068"
PUBLISHED_BASE_HEAD = "8f067ae0dd0ced29e3c1805a3897da832a3ad172"
PUBLISHED_BASE_REVIEW = {
    "path": REVIEW_PATH.as_posix(),
    "size": 8193,
    "sha256": "2640ab33de5ecfeea364007bef6d5aa88cc8289eacd8fe40db474d7a2d8b18e5",
    "git_blob_sha1": "69663e1d5c4eaade855b6e1c67d173c23e3485bd",
}
REPOSITORY = "phoenix-hacking/mckernel"
RUN_ID = 31563271344
RUN_ATTEMPT = 1
JOB_ID = 94009832027
ARTIFACT_ID = 9128527159
ARTIFACT_NAME = "rk003-rk005-platform-evidence-31563271344-1"
ARTIFACT_FILE_NAME = ARTIFACT_NAME + ".zip"
ARTIFACT_SIZE = 193574223
ARTIFACT_SHA256 = (
    "a88e8a35c13dbd5b7a4e6524595d5cec31450f83c136b4cf64030e517d208eef"
)
EXPECTED_REVIEW_SHA256 = (
    "ffd43d9fee68802f6d1875ca52ce9ec200977a69441f751116a96c0061628f2e"
)

RELEASE_KEY_FINGERPRINT = "FC226859C0860BF0DDB95B085B106C736FEDFC85"
RELEASE_KEY_SHA256 = (
    "be8c4f070b696e64d8ce40e59a95a57e8b5c776f0015c2fd64e14b896622bdb4"
)
CONTAINER_MANIFEST = (
    "sha256:e372170ca8630f0f03e9b70fdd0bf4a3ce3426b0de7cdba615f06337389de176"
)
CONTAINER_IMAGE = "rockylinux/rockylinux:10.2@" + CONTAINER_MANIFEST
CONTAINER_TAG_INDEX = (
    "sha256:827d37bc128288ccf160ee318bb3cb92d591164cb217e92f8bc61e3982ae1834"
)

HEX_SHA1 = re.compile(r"^[0-9a-f]{40}$")
HEX_SHA256 = re.compile(r"^[0-9a-f]{64}$")
CHECKSUM_LINE = re.compile(r"^([0-9a-f]{64})  ([^\n]+)$")
RPM_SIGNATURE_LINE = re.compile(
    rb"Header V4 RSA/SHA256 Signature, key ID 6fedfc85: OK"
)
MAX_JSON_BYTES = 2 * 1024 * 1024
MAX_MANIFEST_BYTES = 64 * 1024
MAX_ENTRY_COUNT = 512
MAX_ENTRY_BYTES = 64 * 1024 * 1024
MAX_TOTAL_BYTES = 256 * 1024 * 1024
COMMON_NS = "{http://linux.duke.edu/metadata/common}"
REPO_NS = "{http://linux.duke.edu/metadata/repo}"


EXPECTED_INPUTS = [
    {
        "path": "host-kernel/rocky/evidence-plan-v1.json",
        "git_blob_sha1": "cb7c2ed9ca3217bc9dcad6f7d3bb609708fb340f",
        "sha256": "dbe0788250f363c4f387782511753d9e3dfe8604cb44196e83db64302e876926",
        "size": 19675,
    },
    {
        "path": "host-kernel/rocky/toolchain-lock.json",
        "git_blob_sha1": "5584b199126e38852f1b80a47e0f93d627d4a6df",
        "sha256": "fd3d7a13e1b8b5d103f7e59d22f17c9e4b99cc937637decaa66749acfae6c802",
        "size": 28867,
    },
    {
        "path": "host-kernel/rocky/config-policy.json",
        "git_blob_sha1": "f35f8f4f149a8064c3771c357f434d4043744535",
        "sha256": "94c4715f9c823b3aafcb8399ed7b2cbe25e77308b1c165afc75db70f5afbfd7f",
        "size": 8235,
    },
    {
        "path": "host-kernel/rocky/configs/rust-minimal.config",
        "git_blob_sha1": "de815156d011d5620b886894a0eaa16dbe2af9ce",
        "sha256": "25dd0fc5647d8addfd650469aad758ca41d7e9599f0d02e34c2025e438114983",
        "size": 46,
    },
    {
        "path": "host-kernel/rocky/source-lock.json",
        "git_blob_sha1": "e546a9bc4578e989a96e1ace863b696b08a14e16",
        "sha256": "6b8571b229f31bf68b58749217391d917a2ba2028ac876e8475be1ec5bfef222",
        "size": 9549,
    },
    {
        "path": "host-kernel/rocky/patches/series.json",
        "git_blob_sha1": "565ec633351b9a12400d504e71c26432dae3173a",
        "sha256": "6a1a5e8fb13b6ce6ed35bd8e5487bb67ecf92d2be927799b660f21b5631f68fb",
        "size": 1454,
    },
    {
        "path": "scripts/rocky_kernel_platform_lock.py",
        "git_blob_sha1": "86d62f8cb79bbf80ce376efd1e7f6e84e5a6d916",
        "sha256": "72422ce7c4c4de7993ac3f175eb7901a5f266998d575e057f30220d189607b32",
        "size": 71003,
    },
    {
        "path": "scripts/rocky_kernel_source_lock.py",
        "git_blob_sha1": "d80a3529d5b38fdd7d984e677677a00247edbaa0",
        "sha256": "d58e32ad59f89cee72e201b4cfa4f7301b07f2d8783a8682aee19743836e948f",
        "size": 38173,
    },
    {
        "path": "scripts/rocky_kernel_platform_evidence.py",
        "git_blob_sha1": "1f9dd919e8a6368d67d53ee1957eeb6f8f2acd87",
        "sha256": "db62d408669b3123ca6ed296b8b121cb9247dd536d3253e94cab9148c494762b",
        "size": 95490,
    },
    {
        "path": ".github/workflows/rocky-kernel-platform-evidence.yml",
        "git_blob_sha1": "16924ca4a772aac76b0d9f4eb76e9cae1f99eb0d",
        "sha256": "cc7e2a935369c1f8cea1eb01af26cdbdd08c629232abb05d7489ef68fa056001",
        "size": 5711,
    },
]

CURRENT_INPUT_OVERRIDES = [
    {
        "path": "host-kernel/rocky/source-lock.json",
        "git_blob_sha1": "ad8379320f186646e45a402e5e6fce7b1200f60e",
        "sha256": "16f94def36b3b87ef8bca064bcf4f4ad7251d838fdf1af6cf7bd3413fa6c5531",
        "size": 15666,
    },
    {
        "path": "scripts/rocky_kernel_source_lock.py",
        "git_blob_sha1": "cd5f4b4ad96fa13716ecc26f1bbc84096d7f36ea",
        "sha256": "ffe84874f843126c4d1e680b413aeb279a6116121a1c933e40e2a42411c3ee6e",
        "size": 55617,
    },
]

PUBLISHED_BASE_CHANGED_PATHS = [
    "host-kernel/rocky/source-lock.json",
    "scripts/rocky_kernel_source_lock.py",
]

EXPECTED_CURRENT_REPOSITORY_BINDING = {
    "base_head_sha": OBSERVED_HEAD,
    "binding_kind": "exact-repository-tree-overrides",
    "runtime_committed_input_count": 10,
    "current_override_count": 2,
    "current_overrides": CURRENT_INPUT_OVERRIDES,
    "unchanged_runtime_input_count": 8,
    "all_unoverridden_input_bytes_equal_to_runtime": True,
    "all_unoverridden_input_git_blobs_equal_to_runtime": True,
    "runtime_identity_claimed": False,
}

EXPECTED_PHASE_BLOCKERS = [
    "The full transitive RPM closure has not been resolved or archived.",
    "The archived closure has not been installed into an empty buildroot with dependency repositories disabled and independently reviewed network-isolation evidence.",
    "The required binary, version, libclang, and rust-src probes have not run in that offline buildroot.",
    "The minimal requested config has not been resolved twice by the exact Rocky process_configs.sh and olddefconfig pipeline.",
    "make LLVM=1 rustavailable has not run against the resolved config and exact source.",
    "A production kernel build has not bound its final .config to the independently resolved config.",
    "Successful exact-head artifacts still require independent review before either lock may be updated.",
]

EXPECTED_ZIP_CLOSURE = {
    "entry_count": 166,
    "compressed_size": 193540867,
    "uncompressed_size": 193540867,
    "compression_methods": [0],
    "external_attributes": [2164260896],
    "safe_regular_files_only": True,
    "duplicate_paths": False,
    "crc_verified": True,
    "path_index_format": "canonical-json sorted path array plus newline",
    "path_index_sha256": "21d5519cb2d5297b866e7dd107c3737ab34120103cdee234e2db8a5d1883f3d6",
    "entry_index_format": "canonical-json sorted records of compressed_size, compression_method, crc32, external_attributes, path, sha256, and size plus newline",
    "entry_index_sha256": "c79c0acb091d4d20f28092341ea6dc64b3eed3f080c6b4fb4f329583d986fe6b",
    "checksum_manifests": [
        {
            "path": "bootstrap/SHA256SUMS",
            "sha256": "504edd5a7c8b3ce33c3fea11769920dc2dea03627137e99a286c3ecdd8ee2dd7",
            "size": 10827,
            "covered_entry_count": 98,
        },
        {
            "path": "capture/SHA256SUMS",
            "sha256": "cc175ab98f2c56d89332f84ef5533cd4a7e2823d486197c45b48304bd7999b32",
            "size": 7646,
            "covered_entry_count": 66,
        },
    ],
}

EXPECTED_CLAIMS = {
    "historical_runtime_only": True,
    "current_head_runtime_identity": False,
    "gate_claims": {"RK-003": False, "RK-005": False},
    "tracker_credit": False,
    "credit_eligible": False,
    "closure_complete": False,
    "network_isolation_claimed": False,
}

EXPECTED_CAVEATS = {
    "artifact_retention_is_durable": False,
    "archive_bytes_committed": False,
    "checkpoint_json_alone_anchors_full_archive": False,
    "outer_zip_and_checksum_manifest_pins_required": True,
    "rpm_transcript_hashes_path_independent": False,
    "rpm_transcript_path_sensitivity": "rpmkeys transcript hashes include absolute GitHub Actions temporary paths",
    "container_claim_boundary": "workflow-selected digest and artifact-recorded Rocky 10.2 x86_64 runtime checks; no independent in-container OCI digest attestation",
    "historical_blocker_state_is_current_tracker_state": False,
}


class ReviewError(RuntimeError):
    """Raised when the review or its historical artifact is not exact."""


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def sha256_file(path):
    digest = hashlib.sha256()
    size = 0
    try:
        with path.open("rb") as stream:
            while True:
                chunk = stream.read(1024 * 1024)
                if not chunk:
                    break
                digest.update(chunk)
                size += len(chunk)
    except OSError as exc:
        raise ReviewError("cannot hash {}: {}".format(path, exc))
    return size, digest.hexdigest()


def git_blob_sha1(data):
    prefix = "blob {}\0".format(len(data)).encode("ascii")
    return hashlib.sha1(prefix + data).hexdigest()


def reject_duplicate_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ReviewError("duplicate JSON key: {!r}".format(key))
        result[key] = value
    return result


def strict_json_bytes(data, label, canonical=False):
    if len(data) > MAX_JSON_BYTES:
        raise ReviewError("{} exceeds the JSON size limit".format(label))
    try:
        value = json.loads(
            data.decode("utf-8"), object_pairs_hook=reject_duplicate_pairs
        )
    except (UnicodeDecodeError, ValueError) as exc:
        raise ReviewError("cannot parse {}: {}".format(label, exc))
    if not isinstance(value, dict):
        raise ReviewError("{} must contain one JSON object".format(label))
    if canonical and data != canonical_json_bytes(value):
        raise ReviewError("{} is not canonical JSON".format(label))
    return value


def canonical_json_bytes(value):
    try:
        text = json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        )
    except (TypeError, ValueError) as exc:
        raise ReviewError("value is not canonical JSON: {}".format(exc))
    return (text + "\n").encode("ascii")


def exact_keys(value, expected, label):
    if not isinstance(value, dict):
        raise ReviewError("{} must be an object".format(label))
    actual = set(value)
    wanted = set(expected)
    if actual != wanted:
        raise ReviewError(
            "{} fields changed: actual={}, expected={}".format(
                label, sorted(actual), sorted(wanted)
            )
        )
    return value


def require_exact(actual, expected, label):
    if actual != expected or type(actual) is not type(expected):
        raise ReviewError(
            "{} changed: actual={!r}, expected={!r}".format(label, actual, expected)
        )


def normalized_relative_path(value, label):
    if not isinstance(value, str) or not value or "\\" in value or "\x00" in value:
        raise ReviewError("{} must be a normalized relative path".format(label))
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in ("", ".", "..") for part in path.parts):
        raise ReviewError("{} must be a normalized relative path".format(label))
    if path.as_posix() != value:
        raise ReviewError("{} is not canonically encoded".format(label))
    return path


def within(root, candidate):
    try:
        common = os.path.commonpath((str(root), str(candidate)))
    except ValueError:
        return False
    return Path(common) == root


def repository_file(repo, relative):
    relative_path = normalized_relative_path(relative.as_posix(), "repository path")
    root = repo.resolve()
    requested = root.joinpath(*relative_path.parts)
    try:
        resolved = requested.resolve()
    except OSError as exc:
        raise ReviewError("cannot resolve {}: {}".format(relative, exc))
    if not within(root, resolved):
        raise ReviewError("repository path escapes checkout: {}".format(relative))
    if requested != resolved or requested.is_symlink() or not requested.is_file():
        raise ReviewError(
            "repository input must be a regular file without symlink traversal: {}".format(
                relative
            )
        )
    return requested


def read_repository_json(repo, relative, canonical=False):
    path = repository_file(repo, relative)
    try:
        data = path.read_bytes()
    except OSError as exc:
        raise ReviewError("cannot read {}: {}".format(relative, exc))
    return strict_json_bytes(data, relative.as_posix(), canonical=canonical), data


def validate_review(review, review_bytes):
    if sha256_bytes(review_bytes) != EXPECTED_REVIEW_SHA256:
        raise ReviewError("historical review bytes changed without validator review")
    exact_keys(
        review,
        {
            "schema_version",
            "review_id",
            "review_kind",
            "source_artifact",
            "zip_closure",
            "runtime_candidate",
            "current_head_blob_equivalence_observation",
            "current_repository_input_binding",
            "verified_facts",
            "claims",
            "connector_tree_port",
            "phase_blockers_at_capture",
            "caveats",
        },
        "historical review",
    )
    require_exact(review["schema_version"], 2, "review schema")
    require_exact(review["review_id"], REVIEW_ID, "review ID")
    require_exact(
        review["review_kind"],
        "historical-platform-repository-direct",
        "review kind",
    )
    require_exact(
        review["source_artifact"],
        {
            "github": {
                "repository": REPOSITORY,
                "runtime_head_sha": RUNTIME_HEAD,
                "run_id": RUN_ID,
                "run_attempt": RUN_ATTEMPT,
                "job_id": JOB_ID,
            },
            "artifact": {
                "id": ARTIFACT_ID,
                "name": ARTIFACT_NAME,
                "archive_file_name": ARTIFACT_FILE_NAME,
                "size": ARTIFACT_SIZE,
                "sha256": ARTIFACT_SHA256,
            },
            "retention_days": 30,
            "durable_archive": False,
        },
        "source artifact",
    )
    require_exact(review["zip_closure"], EXPECTED_ZIP_CLOSURE, "ZIP closure")
    runtime = exact_keys(
        review["runtime_candidate"],
        {"head_sha", "committed_inputs", "container"},
        "runtime candidate",
    )
    require_exact(runtime["head_sha"], RUNTIME_HEAD, "runtime head")
    require_exact(runtime["committed_inputs"], EXPECTED_INPUTS, "committed inputs")
    require_exact(
        runtime["container"],
        {
            "image": CONTAINER_IMAGE,
            "manifest_digest": CONTAINER_MANIFEST,
            "tag_index_digest": CONTAINER_TAG_INDEX,
            "platform": "linux/amd64",
            "runtime_architecture": "x86_64",
            "runtime_os_id": "rocky",
            "runtime_os_version_id": "10.2",
            "identity_source": "pinned workflow selection plus artifact record",
            "independent_in_container_oci_attestation": False,
        },
        "container claim",
    )
    require_exact(
        review["current_head_blob_equivalence_observation"],
        {
            "head_sha": OBSERVED_HEAD,
            "observed_against_runtime_head_sha": RUNTIME_HEAD,
            "relationship": "descendant",
            "descendant_commit_count": 15,
            "changed_path_count": 111,
            "bound_input_count": 10,
            "all_bound_input_bytes_equal": True,
            "all_bound_input_git_blobs_equal": True,
            "runtime_identity_claimed": False,
        },
        "current-head blob-equivalence observation",
    )
    require_exact(
        review["current_repository_input_binding"],
        EXPECTED_CURRENT_REPOSITORY_BINDING,
        "current repository input binding",
    )
    require_exact(
        review["connector_tree_port"],
        expected_connector_tree_port(),
        "connector tree port",
    )
    require_exact(
        review["verified_facts"],
        {
            "status": "bounded-pass",
            "phase": "repository-direct",
            "bootstrap": {
                "base_package_count": 138,
                "added_package_count": 47,
                "after_package_count": 185,
                "removed_package_count": 0,
                "overlap_package_count": 0,
                "downloaded_bytes": 20604218,
                "base_package_manifest_sha256": "9c2eddd4bb7c37e992dfcb4b42f2eb3a2728f98f301bdd0f27ddd54b2711d4b8",
                "after_package_manifest_sha256": "ddf0695340682c9b39fa2704f52407664c92e3176ebd61a8c06366a57f344f90",
            },
            "signatures": {
                "release_key_fingerprint": RELEASE_KEY_FINGERPRINT,
                "release_key_sha256": RELEASE_KEY_SHA256,
                "release_key_size": 1688,
                "rpm_archive_instance_count": 67,
                "unique_rpm_count": 65,
                "bootstrap_private_rpmdb_transcript_count": 47,
                "direct_rpm_transcript_count": 20,
                "algorithms": ["RSA/SHA256"],
            },
            "repositories": {
                "repository_count": 3,
                "repository_ids": ["baseos", "appstream", "crb"],
                "repomd_signature_count": 3,
                "signed_primary_rpm_binding_count": 65,
                "direct_archive_count": 20,
            },
            "build_requirements": {
                "rocky_effective_count": 86,
                "reviewed_rocky_rust_count": 3,
                "reviewed_rocky_rust": ["bindgen", "rust", "rust-src"],
                "locked_direct_nevra_count": 20,
                "resolution_root_count": 109,
                "closure_complete": False,
                "reviewed_source_change_applied": False,
                "source_spec_condition": "0%{?fedora}",
            },
        },
        "verified facts",
    )
    require_exact(review["claims"], EXPECTED_CLAIMS, "review claims")
    require_exact(
        review["phase_blockers_at_capture"],
        EXPECTED_PHASE_BLOCKERS,
        "phase blockers",
    )
    require_exact(review["caveats"], EXPECTED_CAVEATS, "review caveats")


def run_command(arguments, cwd=None, env=None):
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
        raise ReviewError("command unavailable: {}: {}".format(arguments[0], exc))
    except subprocess.CalledProcessError as exc:
        raise ReviewError(
            "command failed ({}): {}".format(
                " ".join(arguments),
                exc.stderr.decode("utf-8", errors="replace").strip(),
            )
        )
    return completed.stdout, completed.stderr


def run_git(repo, arguments):
    root = repo.resolve()
    return run_command(
        ["git", "-c", "safe.directory={}".format(root)] + list(arguments),
        cwd=root,
    )


def git_commit_available(repo, commit):
    if not HEX_SHA1.fullmatch(commit):
        raise ReviewError("historical Git commit is malformed")
    root = repo.resolve()
    try:
        completed = subprocess.run(
            [
                "git",
                "-c",
                "safe.directory={}".format(root),
                "-C",
                str(root),
                "cat-file",
                "-e",
                commit + "^{commit}",
            ],
            cwd=str(root),
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except OSError as exc:
        raise ReviewError("command unavailable: git: {}".format(exc))
    return completed.returncode == 0


def current_expected_inputs():
    overrides = {row["path"]: row for row in CURRENT_INPUT_OVERRIDES}
    expected_paths = {row["path"] for row in EXPECTED_INPUTS}
    if len(overrides) != len(CURRENT_INPUT_OVERRIDES):
        raise ReviewError("current input override paths are duplicated")
    if not set(overrides).issubset(expected_paths):
        raise ReviewError("current input override is outside the runtime input set")
    return [overrides.get(row["path"], row) for row in EXPECTED_INPUTS]


def expected_connector_tree_port():
    inputs = current_expected_inputs()
    return {
        "binding_kind": "exact-input-tree-port",
        "published_base_head_sha": PUBLISHED_BASE_HEAD,
        "published_base_review": PUBLISHED_BASE_REVIEW,
        "historical_runtime_head_sha": RUNTIME_HEAD,
        "historical_observation_head_sha": OBSERVED_HEAD,
        "historical_review_preserved_by_exact_base_review_blob": True,
        "historical_observation_fresh_git_reverification_claimed": False,
        "historical_observation_git_object_required_for_tree_port": False,
        "ported_input_count": len(inputs),
        "ported_inputs": inputs,
        "ported_inputs_sha256": sha256_bytes(canonical_json_bytes(inputs)),
        "changed_from_published_base_count": len(PUBLISHED_BASE_CHANGED_PATHS),
        "changed_from_published_base_paths": PUBLISHED_BASE_CHANGED_PATHS,
        "unchanged_from_published_base_count": len(inputs)
        - len(PUBLISHED_BASE_CHANGED_PATHS),
        "runtime_identity_claimed": False,
        "credit_eligible": False,
    }


def validate_repository_inputs(repo):
    for expected in current_expected_inputs():
        relative = Path(expected["path"])
        path = repository_file(repo, relative)
        data = path.read_bytes()
        require_exact(len(data), expected["size"], "{} size".format(relative))
        require_exact(
            sha256_bytes(data), expected["sha256"], "{} SHA-256".format(relative)
        )
        require_exact(
            git_blob_sha1(data),
            expected["git_blob_sha1"],
            "{} Git blob".format(relative),
        )


def validate_connector_parent_vector(parents):
    require_exact(
        parents,
        [PUBLISHED_BASE_HEAD],
        "connector tree-port parent vector",
    )


def validate_connector_input(
    expected, relative, head_bytes, worktree_bytes, tree_entry, index_entry
):
    require_exact(
        tree_entry,
        "100644 blob {}\t{}\0".format(
            expected["git_blob_sha1"], relative
        ).encode("utf-8"),
        "connector HEAD tree entry {}".format(relative),
    )
    require_exact(
        index_entry,
        "100644 {} 0\t{}\n".format(
            expected["git_blob_sha1"], relative
        ).encode("utf-8"),
        "connector index entry {}".format(relative),
    )
    require_exact(
        worktree_bytes,
        head_bytes,
        "connector worktree input {}".format(relative),
    )
    require_exact(len(head_bytes), expected["size"], "HEAD {} size".format(relative))
    require_exact(
        sha256_bytes(head_bytes),
        expected["sha256"],
        "HEAD {} SHA-256".format(relative),
    )
    require_exact(
        git_blob_sha1(head_bytes),
        expected["git_blob_sha1"],
        "HEAD {} Git blob".format(relative),
    )


def validate_git_observation(repo):
    if not (repo / ".git").exists():
        raise ReviewError("connector tree port requires a Git checkout")
    current_stdout, _ = run_git(repo, ["rev-parse", "HEAD"])
    current = current_stdout.decode("ascii").strip()
    if not HEX_SHA1.fullmatch(current):
        raise ReviewError("current Git HEAD is malformed")
    base_stdout, _ = run_git(repo, ["rev-parse", PUBLISHED_BASE_HEAD + "^{commit}"])
    require_exact(
        base_stdout.decode("ascii").strip(),
        PUBLISHED_BASE_HEAD,
        "published connector base commit",
    )
    parents_stdout, _ = run_git(repo, ["show", "-s", "--format=%P", current])
    parents = parents_stdout.decode("ascii").strip().split()
    validate_connector_parent_vector(parents)
    base_review, _ = run_git(
        repo, ["show", "{}:{}".format(PUBLISHED_BASE_HEAD, REVIEW_PATH.as_posix())]
    )
    require_exact(len(base_review), PUBLISHED_BASE_REVIEW["size"], "base review size")
    require_exact(
        sha256_bytes(base_review),
        PUBLISHED_BASE_REVIEW["sha256"],
        "base review SHA-256",
    )
    require_exact(
        git_blob_sha1(base_review),
        PUBLISHED_BASE_REVIEW["git_blob_sha1"],
        "base review Git blob",
    )
    changed = []
    for expected in current_expected_inputs():
        relative = expected["path"]
        base_bytes, _ = run_git(
            repo,
            ["show", "{}:{}".format(PUBLISHED_BASE_HEAD, relative)],
        )
        head_bytes, _ = run_git(repo, ["show", "{}:{}".format(current, relative)])
        tree_entry, _ = run_git(repo, ["ls-tree", "-z", current, "--", relative])
        index_entry, _ = run_git(repo, ["ls-files", "--stage", "--", relative])
        worktree_bytes = repository_file(repo, Path(relative)).read_bytes()
        validate_connector_input(
            expected,
            relative,
            head_bytes,
            worktree_bytes,
            tree_entry,
            index_entry,
        )
        if base_bytes != head_bytes:
            changed.append(relative)
    require_exact(
        changed,
        PUBLISHED_BASE_CHANGED_PATHS,
        "connector tree-port changed paths",
    )
    try:
        observed_type = run_git(repo, ["cat-file", "-t", OBSERVED_HEAD])[0]
    except ReviewError:
        observed_type = b""
    if observed_type.decode("ascii").strip() == "commit":
        run_git(repo, ["merge-base", "--is-ancestor", RUNTIME_HEAD, OBSERVED_HEAD])
        count_stdout, _ = run_git(
            repo,
            ["rev-list", "--count", "{}..{}".format(RUNTIME_HEAD, OBSERVED_HEAD)],
        )
        require_exact(
            count_stdout.decode("ascii").strip(),
            "15",
            "historical observed commit distance",
        )
        paths_stdout, _ = run_git(
            repo,
            ["diff", "--name-only", "{}..{}".format(RUNTIME_HEAD, OBSERVED_HEAD)],
        )
        historical_changed = [
            line for line in paths_stdout.decode("utf-8").splitlines() if line
        ]
        require_exact(
            len(historical_changed),
            111,
            "historical observed changed-path count",
        )
        for expected in EXPECTED_INPUTS:
            runtime_bytes, _ = run_git(
                repo, ["show", "{}:{}".format(RUNTIME_HEAD, expected["path"])]
            )
            observed_bytes, _ = run_git(
                repo, ["show", "{}:{}".format(OBSERVED_HEAD, expected["path"])]
            )
            require_exact(
                observed_bytes,
                runtime_bytes,
                "historical observed input {}".format(expected["path"]),
            )
            require_exact(
                sha256_bytes(runtime_bytes),
                expected["sha256"],
                "historical runtime input {}".format(expected["path"]),
            )
    return True


def check_repository(repo):
    repo = repo.resolve()
    review, review_bytes = read_repository_json(repo, REVIEW_PATH, canonical=True)
    validate_review(review, review_bytes)
    validate_repository_inputs(repo)
    git_checked = validate_git_observation(repo)
    return review, git_checked


def external_regular_file(path):
    if not path.is_absolute() or path.is_symlink() or not path.is_file():
        raise ReviewError("artifact must be an absolute regular file")
    if path.resolve() != path:
        raise ReviewError("artifact path uses symlink traversal")
    return path


def zip_entry_bytes(archive, name, maximum):
    try:
        info = archive.getinfo(name)
    except KeyError:
        raise ReviewError("artifact is missing {}".format(name))
    if info.file_size > maximum:
        raise ReviewError("{} exceeds its review size limit".format(name))
    try:
        data = archive.read(name)
    except (OSError, RuntimeError, zipfile.BadZipFile) as exc:
        raise ReviewError("cannot read {}: {}".format(name, exc))
    if len(data) != info.file_size:
        raise ReviewError("{} changed size while reading".format(name))
    return data


def zip_json(archive, name):
    data = zip_entry_bytes(archive, name, MAX_JSON_BYTES)
    return strict_json_bytes(data, name, canonical=True), data


def validate_zip_infos(archive):
    infos = archive.infolist()
    if not infos or len(infos) > MAX_ENTRY_COUNT:
        raise ReviewError("ZIP entry count is unsafe")
    names = []
    total_compressed = 0
    total_uncompressed = 0
    for info in infos:
        normalized_relative_path(info.filename, "ZIP entry")
        if info.filename.endswith("/"):
            raise ReviewError("ZIP directory entries are forbidden")
        if info.flag_bits & 1:
            raise ReviewError("encrypted ZIP entries are forbidden")
        mode = (info.external_attr >> 16) & 0xFFFF
        if not stat.S_ISREG(mode):
            raise ReviewError("ZIP entry is not a regular file: {}".format(info.filename))
        if info.file_size < 0 or info.file_size > MAX_ENTRY_BYTES:
            raise ReviewError("ZIP entry is too large: {}".format(info.filename))
        if info.compress_size < 0 or info.compress_size > MAX_ENTRY_BYTES:
            raise ReviewError("ZIP compressed entry is too large: {}".format(info.filename))
        names.append(info.filename)
        total_compressed += info.compress_size
        total_uncompressed += info.file_size
    if len(names) != len(set(names)):
        raise ReviewError("ZIP contains duplicate paths")
    if total_uncompressed > MAX_TOTAL_BYTES or total_compressed > MAX_TOTAL_BYTES:
        raise ReviewError("ZIP total size is unsafe")
    return infos, names, total_compressed, total_uncompressed


def hash_zip_entries(archive, infos):
    records = []
    hashes = {}
    for info in sorted(infos, key=lambda row: row.filename):
        digest = hashlib.sha256()
        try:
            with archive.open(info, "r") as stream:
                while True:
                    chunk = stream.read(1024 * 1024)
                    if not chunk:
                        break
                    digest.update(chunk)
        except (OSError, RuntimeError, zipfile.BadZipFile) as exc:
            raise ReviewError("cannot hash ZIP entry {}: {}".format(info.filename, exc))
        value = digest.hexdigest()
        hashes[info.filename] = value
        records.append(
            {
                "compressed_size": info.compress_size,
                "compression_method": info.compress_type,
                "crc32": "{:08x}".format(info.CRC),
                "external_attributes": info.external_attr,
                "path": info.filename,
                "sha256": value,
                "size": info.file_size,
            }
        )
    return records, hashes


def parse_checksum_manifest(data, label):
    try:
        lines = data.decode("ascii").splitlines()
    except UnicodeDecodeError as exc:
        raise ReviewError("{} is not ASCII: {}".format(label, exc))
    if not data.endswith(b"\n") or not lines:
        raise ReviewError("{} must be non-empty and newline terminated".format(label))
    rows = []
    for line in lines:
        match = CHECKSUM_LINE.fullmatch(line)
        if match is None:
            raise ReviewError("{} contains a malformed row".format(label))
        relative = normalized_relative_path(match.group(2), "checksum path")
        rows.append((relative.as_posix(), match.group(1)))
    paths = [row[0] for row in rows]
    if paths != sorted(paths) or len(paths) != len(set(paths)):
        raise ReviewError("{} paths must be sorted and unique".format(label))
    return rows


def validate_checksum_closure(archive, names, hashes):
    covered = set()
    manifest_paths = set()
    for expected in EXPECTED_ZIP_CLOSURE["checksum_manifests"]:
        path = expected["path"]
        manifest_paths.add(path)
        data = zip_entry_bytes(archive, path, MAX_MANIFEST_BYTES)
        require_exact(len(data), expected["size"], "{} size".format(path))
        require_exact(sha256_bytes(data), expected["sha256"], "{} digest".format(path))
        rows = parse_checksum_manifest(data, path)
        require_exact(
            len(rows), expected["covered_entry_count"], "{} row count".format(path)
        )
        prefix = PurePosixPath(path).parent.as_posix() + "/"
        actual = sorted(
            name for name in names if name.startswith(prefix) and name != path
        )
        listed = [prefix + relative for relative, unused in rows]
        require_exact(listed, actual, "{} full closure".format(path))
        for relative, digest in rows:
            full = prefix + relative
            require_exact(hashes[full], digest, "{} entry digest".format(full))
            covered.add(full)
    require_exact(covered | manifest_paths, set(names), "full ZIP checksum closure")


def validate_zip_closure(archive):
    if archive.comment:
        raise ReviewError("ZIP comment is forbidden")
    infos, names, compressed, uncompressed = validate_zip_infos(archive)
    require_exact(len(infos), EXPECTED_ZIP_CLOSURE["entry_count"], "ZIP entry count")
    require_exact(compressed, EXPECTED_ZIP_CLOSURE["compressed_size"], "ZIP compressed bytes")
    require_exact(
        uncompressed, EXPECTED_ZIP_CLOSURE["uncompressed_size"], "ZIP uncompressed bytes"
    )
    require_exact(
        sorted(set(info.compress_type for info in infos)),
        EXPECTED_ZIP_CLOSURE["compression_methods"],
        "ZIP compression methods",
    )
    require_exact(
        sorted(set(info.external_attr for info in infos)),
        EXPECTED_ZIP_CLOSURE["external_attributes"],
        "ZIP external attributes",
    )
    records, hashes = hash_zip_entries(archive, infos)
    path_bytes = canonical_json_bytes(sorted(names))
    require_exact(
        sha256_bytes(path_bytes),
        EXPECTED_ZIP_CLOSURE["path_index_sha256"],
        "ZIP path index",
    )
    require_exact(
        sha256_bytes(canonical_json_bytes(records)),
        EXPECTED_ZIP_CLOSURE["entry_index_sha256"],
        "ZIP entry index",
    )
    validate_checksum_closure(archive, names, hashes)
    return names, hashes


def expected_identity():
    return {
        "head_sha": RUNTIME_HEAD,
        "repository": REPOSITORY,
        "run_attempt": RUN_ATTEMPT,
        "run_id": RUN_ID,
    }


def parse_package_inventory(data, label):
    try:
        rows = data.decode("utf-8").splitlines()
    except UnicodeDecodeError as exc:
        raise ReviewError("{} is not UTF-8: {}".format(label, exc))
    if not data.endswith(b"\n") or not rows:
        raise ReviewError("{} must be non-empty and newline terminated".format(label))
    if rows != sorted(rows) or len(rows) != len(set(rows)):
        raise ReviewError("{} must be sorted and unique".format(label))
    if any(not row or any(ord(character) < 32 for character in row) for row in rows):
        raise ReviewError("{} contains malformed package rows".format(label))
    return rows


def expected_download(repository, location, digest, size):
    return {
        "final_url": repository["base_url"] + location,
        "redirect_count": 0,
        "sha256": digest,
        "size": size,
    }


def validate_rpm_transcript(data, signature, label):
    exact_keys(
        signature,
        {
            "header_signature_algorithm",
            "signer_fingerprint",
            "signer_key_id",
            "status",
            "transcript_sha256",
            "transcript_size",
        },
        label + " signature",
    )
    require_exact(signature["status"], "verified", label + " signature status")
    require_exact(
        signature["header_signature_algorithm"], "RSA/SHA256", label + " algorithm"
    )
    require_exact(
        signature["signer_fingerprint"], RELEASE_KEY_FINGERPRINT, label + " fingerprint"
    )
    require_exact(signature["signer_key_id"], "6FEDFC85", label + " key ID")
    require_exact(len(data), signature["transcript_size"], label + " transcript size")
    require_exact(
        sha256_bytes(data), signature["transcript_sha256"], label + " transcript digest"
    )
    if len(RPM_SIGNATURE_LINE.findall(data)) != 1:
        raise ReviewError("{} lacks one exact RPM signature result".format(label))
    for required in (
        b"Header SHA256 digest: OK",
        b"Header SHA1 digest: OK",
        b"Payload SHA256 digest: OK",
        b"MD5 digest: OK",
    ):
        if required not in data:
            raise ReviewError("{} lacks digest result {}".format(label, required))
    if not data.startswith(b"stdout:\n") or not data.endswith(b"stderr:\n"):
        raise ReviewError("{} transcript framing changed".format(label))


def parse_rpm_header(data, offset, label):
    if offset < 0 or offset + 16 > len(data):
        raise ReviewError("{} has a truncated RPM header".format(label))
    if data[offset : offset + 8] != bytes.fromhex("8eade80100000000"):
        raise ReviewError("{} has an invalid RPM header magic".format(label))
    count, store_size = struct.unpack(">II", data[offset + 8 : offset + 16])
    if count < 1 or count > 4096 or store_size > 16 * 1024 * 1024:
        raise ReviewError("{} has unsafe RPM header bounds".format(label))
    index_end = offset + 16 + count * 16
    end = index_end + store_size
    if index_end > len(data) or end > len(data):
        raise ReviewError("{} has a truncated RPM header store".format(label))
    entries = []
    for index in range(count):
        start = offset + 16 + index * 16
        tag, value_type, position, item_count = struct.unpack(
            ">IIII", data[start : start + 16]
        )
        if position > store_size:
            raise ReviewError("{} has an RPM entry outside its store".format(label))
        entries.append((tag, value_type, position, item_count))
    return end, index_end, store_size, entries


def rpm_signature_payload(data, label):
    if len(data) < 112 or data[:4] != bytes.fromhex("edabeedb"):
        raise ReviewError("{} is not an RPM".format(label))
    signature_end, signature_store, store_size, entries = parse_rpm_header(
        data, 96, label
    )
    signatures = [row for row in entries if row[0] == 268]
    if len(signatures) != 1 or signatures[0][1] != 7:
        raise ReviewError("{} lacks one binary RSA header signature".format(label))
    unused_tag, unused_type, position, count = signatures[0]
    del unused_tag, unused_type
    if count < 1 or count > 8192 or position + count > store_size:
        raise ReviewError("{} has invalid RSA signature bounds".format(label))
    signature = data[signature_store + position : signature_store + position + count]
    main_offset = (signature_end + 7) & ~7
    main_end, unused_store, unused_size, unused_entries = parse_rpm_header(
        data, main_offset, label
    )
    del unused_store, unused_size, unused_entries
    if main_end >= len(data):
        raise ReviewError("{} lacks an RPM payload".format(label))
    return signature, data[main_offset:main_end]


class OpenPGPVerifier(object):
    def __init__(self, key_bytes):
        self._temporary = tempfile.TemporaryDirectory(prefix="mckernel-platform-review-")
        self.root = Path(self._temporary.name)
        self.home = self.root / "gnupg"
        self.home.mkdir(mode=0o700)
        key_path = self.root / "rocky.asc"
        key_path.write_bytes(key_bytes)
        self.keyring = self.root / "rocky.gpg"
        environment = dict(os.environ)
        environment.update({"GNUPGHOME": str(self.home), "LANG": "C", "LC_ALL": "C"})
        run_command(
            [
                "gpg",
                "--batch",
                "--yes",
                "--dearmor",
                "--output",
                str(self.keyring),
                str(key_path),
            ],
            env=environment,
        )
        self.environment = environment

    def close(self):
        self._temporary.cleanup()

    def verify(self, signature, data, label):
        signature_path = self.root / "signature.bin"
        data_path = self.root / "signed-data.bin"
        signature_path.write_bytes(signature)
        data_path.write_bytes(data)
        stdout, unused_stderr = run_command(
            [
                "gpgv",
                "--status-fd=1",
                "--keyring",
                str(self.keyring),
                str(signature_path),
                str(data_path),
            ],
            env=self.environment,
        )
        del unused_stderr
        valid = []
        for line in stdout.decode("utf-8", errors="replace").splitlines():
            if line.startswith("[GNUPG:] VALIDSIG "):
                valid.append(line.split())
        if len(valid) != 1:
            raise ReviewError("{} lacks one VALIDSIG result".format(label))
        fields = valid[0]
        if (
            len(fields) < 12
            or fields[2] != RELEASE_KEY_FINGERPRINT
            or fields[8] != "1"
            or fields[9] != "8"
        ):
            raise ReviewError("{} has the wrong signer or algorithm".format(label))


class HashingReader(object):
    def __init__(self, stream):
        self.stream = stream
        self.digest = hashlib.sha256()
        self.size = 0

    def read(self, size=-1):
        data = self.stream.read(size)
        self.digest.update(data)
        self.size += len(data)
        return data


def expected_rpm_records(plan, toolchain):
    records = {}
    for artifact in list(plan["bootstrap"]["artifacts"]) + list(
        toolchain["direct_artifacts"]
    ):
        compact = {
            key: artifact[key]
            for key in (
                "nevra",
                "repository_id",
                "repository_location",
                "sha256",
                "size",
            )
        }
        prior = records.get(artifact["nevra"])
        if prior is not None and prior != compact:
            raise ReviewError("overlapping RPM identity changed")
        records[artifact["nevra"]] = compact
    require_exact(len(records), 65, "unique reviewed RPM count")
    return records


def validate_repomd_primary(repomd_bytes, repository):
    try:
        root = ET.fromstring(repomd_bytes)
    except ET.ParseError as exc:
        raise ReviewError("cannot parse {} repomd: {}".format(repository["id"], exc))
    primary_rows = [
        row for row in root.findall(REPO_NS + "data") if row.get("type") == "primary"
    ]
    if len(primary_rows) != 1:
        raise ReviewError("{} repomd lacks one primary row".format(repository["id"]))
    row = primary_rows[0]
    expected = repository["primary"]
    checksum = row.find(REPO_NS + "checksum")
    open_checksum = row.find(REPO_NS + "open-checksum")
    location = row.find(REPO_NS + "location")
    size = row.find(REPO_NS + "size")
    open_size = row.find(REPO_NS + "open-size")
    if None in (checksum, open_checksum, location, size, open_size):
        raise ReviewError("{} primary identity is incomplete".format(repository["id"]))
    require_exact(checksum.get("type"), "sha256", "repomd checksum type")
    require_exact(checksum.text, expected["sha256"], "repomd primary digest")
    require_exact(open_checksum.get("type"), "sha256", "repomd open checksum type")
    require_exact(
        open_checksum.text, expected["open_sha256"], "repomd open primary digest"
    )
    require_exact(location.get("href"), expected["href"], "repomd primary path")
    require_exact(int(size.text), expected["size"], "repomd primary size")
    require_exact(int(open_size.text), expected["open_size"], "repomd open size")


def primary_bindings(primary_bytes, repository_id, expected):
    gzip_stream = gzip.GzipFile(fileobj=io.BytesIO(primary_bytes), mode="rb")
    hashing_stream = HashingReader(gzip_stream)
    seen = {}
    try:
        for event, element in ET.iterparse(hashing_stream, events=("end",)):
            del event
            if element.tag != COMMON_NS + "package":
                continue
            name = element.findtext(COMMON_NS + "name")
            arch = element.findtext(COMMON_NS + "arch")
            version = element.find(COMMON_NS + "version")
            if name is None or arch is None or version is None:
                raise ReviewError("primary metadata has an incomplete package row")
            nevra = "{}-{}:{}-{}.{}".format(
                name,
                version.get("epoch"),
                version.get("ver"),
                version.get("rel"),
                arch,
            )
            locked = expected.get(nevra)
            if locked is not None and locked["repository_id"] == repository_id:
                if nevra in seen:
                    raise ReviewError("primary metadata duplicates {}".format(nevra))
                checksum = element.find(COMMON_NS + "checksum")
                location = element.find(COMMON_NS + "location")
                size = element.find(COMMON_NS + "size")
                if checksum is None or location is None or size is None:
                    raise ReviewError("primary metadata row is incomplete for {}".format(nevra))
                require_exact(checksum.get("type"), "sha256", nevra + " checksum type")
                require_exact(checksum.get("pkgid"), "YES", nevra + " pkgid flag")
                require_exact(checksum.text, locked["sha256"], nevra + " digest")
                require_exact(
                    location.get("href"), locked["repository_location"], nevra + " path"
                )
                require_exact(int(size.get("package")), locked["size"], nevra + " size")
                seen[nevra] = True
            element.clear()
        while hashing_stream.read(1024 * 1024):
            pass
    except (ET.ParseError, OSError, EOFError, ValueError) as exc:
        raise ReviewError("cannot parse {} primary metadata: {}".format(repository_id, exc))
    return seen, hashing_stream.size, hashing_stream.digest.hexdigest()


def validate_artifact_semantics(archive, repo, hashes):
    plan, unused_plan_bytes = read_repository_json(repo, PLAN_PATH)
    toolchain, unused_toolchain_bytes = read_repository_json(repo, TOOLCHAIN_LOCK_PATH)
    source, unused_source_bytes = read_repository_json(repo, SOURCE_LOCK_PATH)
    del unused_plan_bytes, unused_toolchain_bytes, unused_source_bytes

    bootstrap, bootstrap_bytes = zip_json(archive, "bootstrap/bootstrap.json")
    bootstrap_input, bootstrap_input_bytes = zip_json(
        archive, "capture/bootstrap-input.json"
    )
    environment, unused_environment_bytes = zip_json(archive, "capture/environment.json")
    checkpoint, unused_checkpoint_bytes = zip_json(archive, "capture/checkpoint.json")
    blockers, unused_blocker_bytes = zip_json(archive, "capture/blockers.json")
    repository_manifest, unused_repository_bytes = zip_json(
        archive, "capture/repository-snapshots.json"
    )
    direct_manifest, unused_direct_bytes = zip_json(archive, "capture/direct-rpms.json")
    build_manifest, unused_build_bytes = zip_json(
        archive, "capture/build-requirements.json"
    )
    del (
        unused_environment_bytes,
        unused_checkpoint_bytes,
        unused_blocker_bytes,
        unused_repository_bytes,
        unused_direct_bytes,
        unused_build_bytes,
    )

    require_exact(bootstrap_bytes, bootstrap_input_bytes, "bootstrap manifest replay")
    identity = expected_identity()
    for label, value in (
        ("bootstrap", bootstrap.get("github")),
        ("bootstrap input", bootstrap_input.get("github")),
        ("environment", environment.get("github")),
        ("checkpoint", checkpoint.get("github")),
    ):
        require_exact(value, identity, label + " runtime identity")
    require_exact(bootstrap["container_image"], CONTAINER_IMAGE, "bootstrap container")
    require_exact(environment["container_image"], CONTAINER_IMAGE, "environment container")
    require_exact(
        environment["container_manifest_digest"],
        CONTAINER_MANIFEST,
        "container manifest",
    )
    require_exact(environment["container_platform"], "linux/amd64", "container platform")
    require_exact(environment["architecture"], "x86_64", "runtime architecture")
    require_exact(
        environment["os_release"], {"id": "rocky", "version_id": "10.2"}, "runtime OS"
    )
    expected_environment_inputs = [
        {"path": row["path"], "sha256": row["sha256"], "size": row["size"]}
        for row in EXPECTED_INPUTS
    ]
    require_exact(
        environment["committed_inputs"],
        expected_environment_inputs,
        "artifact committed inputs",
    )

    before_bytes = zip_entry_bytes(archive, "bootstrap/before-rpms.txt", 64 * 1024)
    after_bytes = zip_entry_bytes(archive, "bootstrap/after-rpms.txt", 64 * 1024)
    before = parse_package_inventory(before_bytes, "bootstrap before inventory")
    after = parse_package_inventory(after_bytes, "bootstrap after inventory")
    added = sorted(row["nevra"] for row in plan["bootstrap"]["artifacts"])
    require_exact(len(before), 138, "base package count")
    require_exact(len(added), 47, "bootstrap addition count")
    if set(before).intersection(added):
        raise ReviewError("bootstrap additions overlap the base package inventory")
    require_exact(after, sorted(before + added), "138+47 package union")
    require_exact(len(after), 185, "post-bootstrap package count")
    require_exact(
        sha256_bytes(before_bytes),
        "9c2eddd4bb7c37e992dfcb4b42f2eb3a2728f98f301bdd0f27ddd54b2711d4b8",
        "base package manifest",
    )
    require_exact(
        sha256_bytes(after_bytes),
        "ddf0695340682c9b39fa2704f52407664c92e3176ebd61a8c06366a57f344f90",
        "after package manifest",
    )
    install = bootstrap["local_rpm_install"]
    require_exact(install["added_nevras"], added, "bootstrap added NEVRAs")
    require_exact(install["removed_nevras"], [], "bootstrap removals")
    require_exact(install["after_package_count"], 185, "bootstrap installed count")
    require_exact(install["status"], "verified", "bootstrap install status")
    require_exact(
        bootstrap["network"],
        {
            "collector_http_downloaded_bytes": 20604218,
            "collector_http_sealed_before_dnf": True,
            "dnf_repository_access": "disabled-cache-only",
            "network_isolation_claimed": False,
            "scope": "The one-way seal covers only urllib requests issued by this collector. GitHub Actions, the runner, and subprocesses are not claimed to be kernel-network-isolated.",
            "subprocess_proxy_defense_enabled": True,
        },
        "bootstrap network claim boundary",
    )

    repositories = {row["id"]: row for row in plan["repositories"]}
    bootstrap_results = bootstrap["artifacts"]
    require_exact(len(bootstrap_results), 47, "bootstrap artifact result count")
    rpm_instances = []
    for locked, result in zip(plan["bootstrap"]["artifacts"], bootstrap_results):
        require_exact(result["nevra"], locked["nevra"], "bootstrap RPM NEVRA")
        filename = PurePosixPath(locked["repository_location"]).name
        archive_path = "bootstrap/rpms/" + filename
        transcript_path = "bootstrap/rpmkeys/" + filename + ".txt"
        require_exact(result["archive_path"], "rpms/" + filename, "bootstrap RPM path")
        require_exact(
            result["download"],
            expected_download(
                repositories[locked["repository_id"]],
                locked["repository_location"],
                locked["sha256"],
                locked["size"],
            ),
            "bootstrap RPM download",
        )
        require_exact(hashes[archive_path], locked["sha256"], "bootstrap RPM bytes")
        transcript = zip_entry_bytes(archive, transcript_path, 64 * 1024)
        validate_rpm_transcript(transcript, result["signature"], locked["nevra"])
        rpm_instances.append((archive_path, locked["nevra"]))

    direct_results = direct_manifest["artifacts"]
    require_exact(direct_manifest["artifact_count"], 20, "direct artifact count")
    require_exact(len(direct_results), 20, "direct artifact result count")
    require_exact(direct_manifest["all_archives_verified"], True, "direct archives")
    require_exact(
        direct_manifest["all_header_signatures_verified"], True, "direct signatures"
    )
    require_exact(
        direct_manifest["scope"],
        "locked direct RPMs only; this is not the transitive closure",
        "direct RPM scope",
    )
    for locked, result in zip(toolchain["direct_artifacts"], direct_results):
        filename = PurePosixPath(locked["repository_location"]).name
        archive_path = "capture/archives/direct-rpms/" + filename
        transcript_path = "capture/transcripts/rpmkeys/" + filename + ".txt"
        for field in ("nevra", "name", "arch", "repository_id"):
            require_exact(result[field], locked[field], "direct RPM " + field)
        require_exact(
            result["archive_path"],
            "archives/direct-rpms/" + filename,
            "direct RPM path",
        )
        require_exact(
            result["download"],
            expected_download(
                repositories[locked["repository_id"]],
                locked["repository_location"],
                locked["sha256"],
                locked["size"],
            ),
            "direct RPM download",
        )
        require_exact(
            result["metadata"],
            {
                "location": locked["repository_location"],
                "sha256": locked["sha256"],
                "size": locked["size"],
            },
            "direct RPM primary metadata",
        )
        require_exact(hashes[archive_path], locked["sha256"], "direct RPM bytes")
        transcript = zip_entry_bytes(archive, transcript_path, 64 * 1024)
        validate_rpm_transcript(transcript, result["signature"], locked["nevra"])
        rpm_instances.append((archive_path, locked["nevra"]))
    require_exact(len(rpm_instances), 67, "RPM signature instance count")

    key_path = "capture/archives/repositories/RPM-GPG-KEY-Rocky-10"
    key_bytes = zip_entry_bytes(archive, key_path, 64 * 1024)
    require_exact(len(key_bytes), 1688, "release-key size")
    require_exact(sha256_bytes(key_bytes), RELEASE_KEY_SHA256, "release-key digest")
    if shutil.which("gpg") is None or shutil.which("gpgv") is None:
        raise ReviewError("--verify-artifact requires gpg and gpgv")
    verifier = OpenPGPVerifier(key_bytes)
    expected_rpms = expected_rpm_records(plan, toolchain)
    primary_seen = set()
    try:
        repository_results = repository_manifest["repositories"]
        require_exact(len(repository_results), 3, "repository result count")
        for locked, result in zip(plan["repositories"], repository_results):
            repository_id = locked["id"]
            require_exact(result["id"], repository_id, "repository identity")
            require_exact(result["base_url"], locked["base_url"], "repository URL")
            root = "capture/archives/repositories/{}/".format(repository_id)
            repomd_path = root + "repomd.xml"
            signature_path = root + "repomd.xml.asc"
            primary_name = PurePosixPath(locked["primary"]["href"]).name
            primary_path = root + primary_name
            repomd_bytes = zip_entry_bytes(archive, repomd_path, MAX_ENTRY_BYTES)
            signature_bytes = zip_entry_bytes(archive, signature_path, MAX_ENTRY_BYTES)
            primary_bytes = zip_entry_bytes(archive, primary_path, MAX_ENTRY_BYTES)
            require_exact(
                hashes[repomd_path], locked["repomd"]["sha256"], "repomd digest"
            )
            require_exact(
                hashes[signature_path],
                locked["signature"]["sha256"],
                "repomd signature digest",
            )
            require_exact(
                hashes[primary_path], locked["primary"]["sha256"], "primary digest"
            )
            verifier.verify(signature_bytes, repomd_bytes, repository_id + " repomd")
            validate_repomd_primary(repomd_bytes, locked)
            matches, open_size, open_digest = primary_bindings(
                primary_bytes, repository_id, expected_rpms
            )
            require_exact(open_size, locked["primary"]["open_size"], "open primary size")
            require_exact(
                open_digest, locked["primary"]["open_sha256"], "open primary digest"
            )
            primary_seen.update(matches)
            transcript_path = "capture/transcripts/repomd/{}.gpgv.txt".format(
                repository_id
            )
            transcript = zip_entry_bytes(archive, transcript_path, 64 * 1024)
            signature_result = result["signature"]
            require_exact(
                len(transcript), signature_result["transcript_size"], "repomd transcript size"
            )
            require_exact(
                sha256_bytes(transcript),
                signature_result["transcript_sha256"],
                "repomd transcript digest",
            )
            require_exact(signature_result["status"], "verified", "repomd status")
            require_exact(
                signature_result["validsig_fingerprint"],
                RELEASE_KEY_FINGERPRINT,
                "repomd signer",
            )
        require_exact(primary_seen, set(expected_rpms), "signed primary RPM bindings")

        for archive_path, nevra in rpm_instances:
            rpm_bytes = zip_entry_bytes(archive, archive_path, MAX_ENTRY_BYTES)
            signature, signed_header = rpm_signature_payload(rpm_bytes, nevra)
            verifier.verify(signature, signed_header, nevra)
    finally:
        verifier.close()

    locked_source = {row["path"]: row for row in source["dist_git"]["content"]}
    for source_path, artifact_path in (
        ("SPECS/kernel.spec", "capture/inputs/kernel.spec"),
        ("SOURCES/kernel-x86_64-rhel.config", "capture/inputs/kernel-x86_64-rhel.config"),
    ):
        locked = locked_source[source_path]
        require_exact(hashes[artifact_path], locked["sha256"], source_path + " digest")
        require_exact(
            archive.getinfo(artifact_path).file_size, locked["size"], source_path + " size"
        )

    spec_transcript = zip_entry_bytes(
        archive, "capture/transcripts/rpmspec-buildrequires.txt", MAX_ENTRY_BYTES
    )
    prefix = (
        b"command: rpmspec -q --buildrequires --target x86_64-linux-gnu "
        b"kernel.spec\nstdout:\n"
    )
    suffix = b"stderr:\n"
    if not spec_transcript.startswith(prefix) or not spec_transcript.endswith(suffix):
        raise ReviewError("rpmspec transcript framing changed")
    spec_stdout = spec_transcript[len(prefix) : -len(suffix)]
    try:
        effective = sorted(
            set(row.strip() for row in spec_stdout.decode("utf-8").splitlines() if row.strip())
        )
    except UnicodeDecodeError as exc:
        raise ReviewError("rpmspec output is not UTF-8: {}".format(exc))
    require_exact(len(effective), 86, "effective BuildRequires count")
    require_exact(
        build_manifest["effective_buildrequires"], effective, "effective BuildRequires"
    )
    require_exact(
        build_manifest["rpmspec_output_sha256"],
        sha256_bytes(spec_stdout),
        "rpmspec output digest",
    )
    reviewed_rust = ["bindgen", "rust", "rust-src"]
    require_exact(
        build_manifest["reviewed_rocky_rust_additions"], reviewed_rust, "reviewed Rust roots"
    )
    require_exact(
        build_manifest["direct_nevras"],
        toolchain["closure"]["direct_nevras"],
        "direct NEVRA roots",
    )
    roots = (
        [{"kind": "rocky-effective-spec", "value": row} for row in effective]
        + [{"kind": "reviewed-rocky-rust", "value": row} for row in reviewed_rust]
        + [
            {"kind": "locked-direct-nevra", "value": row}
            for row in toolchain["closure"]["direct_nevras"]
        ]
    )
    require_exact(len(roots), 109, "resolution root count")
    require_exact(build_manifest["resolution_roots"], roots, "resolution roots")
    require_exact(build_manifest["closure_complete"], False, "closure claim")
    require_exact(
        build_manifest["transitive_resolution_status"],
        "required-missing",
        "transitive resolution status",
    )
    require_exact(
        build_manifest["reviewed_source_change_applied"], False, "source-change claim"
    )
    require_exact(
        build_manifest["network_isolation_claimed"], False, "network-isolation claim"
    )
    require_exact(
        build_manifest["source_spec_condition"], "0%{?fedora}", "source spec condition"
    )

    require_exact(checkpoint["phase"], "repository-direct", "checkpoint phase")
    require_exact(checkpoint["credit_eligible"], False, "checkpoint credit")
    require_exact(
        checkpoint["gate_claims"], {"RK-003": False, "RK-005": False}, "gate claims"
    )
    require_exact(
        checkpoint["successful_capture_requires_review"], True, "review requirement"
    )
    require_exact(
        checkpoint["acquisition"],
        {
            "collector_http_after_seal": False,
            "collector_http_downloaded_bytes": 172692294,
            "collector_http_sealed": True,
            "network_isolation_claimed": False,
            "scope": "The one-way seal covers only urllib requests issued by this collector. GitHub Actions, the runner, and subprocesses are not claimed to be kernel-network-isolated.",
        },
        "capture acquisition claim boundary",
    )
    require_exact(
        blockers["gate_claims"], {"RK-003": False, "RK-005": False}, "blocker gates"
    )
    require_exact(
        blockers["phase_blockers"], EXPECTED_PHASE_BLOCKERS, "artifact phase blockers"
    )
    for manifest in checkpoint["manifests"]:
        path = "capture/" + normalized_relative_path(
            manifest["path"], "checkpoint manifest path"
        ).as_posix()
        require_exact(hashes[path], manifest["sha256"], path + " checkpoint digest")
        require_exact(archive.getinfo(path).file_size, manifest["size"], path + " size")
    return {
        "rpm_signature_instances": len(rpm_instances),
        "signed_primary_bindings": len(primary_seen),
        "effective_buildrequires": len(effective),
        "resolution_roots": len(roots),
    }


def verify_artifact(path, repo):
    path = external_regular_file(path)
    size, digest = sha256_file(path)
    require_exact(size, ARTIFACT_SIZE, "outer artifact size")
    require_exact(digest, ARTIFACT_SHA256, "outer artifact SHA-256")
    try:
        with zipfile.ZipFile(str(path), "r") as archive:
            unused_names, hashes = validate_zip_closure(archive)
            del unused_names
            summary = validate_artifact_semantics(archive, repo, hashes)
    except (OSError, zipfile.BadZipFile) as exc:
        raise ReviewError("cannot verify artifact ZIP: {}".format(exc))
    return summary


def parse_args(argv):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[1])
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--check", action="store_true")
    modes.add_argument("--verify-artifact", type=Path)
    return parser.parse_args(argv)


def main(argv):
    args = parse_args(argv)
    try:
        review, git_checked = check_repository(args.repo)
        if args.check:
            print(
                "historical platform review verified: {} (git_graph_checked={})".format(
                    review["review_id"], str(git_checked).lower()
                )
            )
            print("RK-003/RK-005 and tracker credit remain false")
            return 0
        summary = verify_artifact(args.verify_artifact, args.repo.resolve())
        print(
            "historical artifact verified: head={} run={}/{} artifact={}".format(
                RUNTIME_HEAD, RUN_ID, RUN_ATTEMPT, ARTIFACT_ID
            )
        )
        print(json.dumps(summary, sort_keys=True, separators=(",", ":")))
        print("RK-003/RK-005 and tracker credit remain false")
        return 0
    except ReviewError as exc:
        print("historical platform review error: {}".format(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
