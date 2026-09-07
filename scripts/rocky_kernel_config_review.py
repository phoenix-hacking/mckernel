#!/usr/bin/env python3
"""Validate a bounded independent review of RK-005 config evidence.

The review is historical evidence only.  Neither ``--check`` nor
``--verify-artifact`` can award a gate or tracker credit.  The checker binds
the reviewed workflow head and every configuration input to Git objects, and
also requires the current HEAD, index, and worktree to retain those exact input
bytes.  That current-input equivalence is not a claim that the current HEAD ran
the historical workflow.
"""

from __future__ import print_function

import argparse
import hashlib
import json
import os
import re
import stat
import subprocess
import sys
import zipfile
from pathlib import Path, PurePosixPath


REVIEW_DIRECTORY = Path("host-kernel/rocky/evidence")
REVIEW_GLOB = "config-resolution-review-*-v1.json"
SCHEMA_VERSION = 1
HEX_SHA1 = re.compile(r"^[0-9a-f]{40}$")
HEX_SHA256 = re.compile(r"^[0-9a-f]{64}$")
CONFIG_VALUE = re.compile(r"^(CONFIG_[A-Za-z0-9_]+)=(.*)$")
CONFIG_UNSET = re.compile(r"^# (CONFIG_[A-Za-z0-9_]+) is not set$")
SHA256SUM = re.compile(r"^([0-9a-f]{64})  ([A-Za-z0-9][A-Za-z0-9_.-]*)$")
CONTAINER_IMAGE = (
    "rockylinux/rockylinux:10.2@"
    "sha256:e372170ca8630f0f03e9b70fdd0bf4a3ce3426b0de7cdba615f06337389de176"
)
EMPTY_SHA256 = hashlib.sha256(b"").hexdigest()
REVIEW_ID = "rk-005-config-resolution-review-378d12cd-v1"
REVIEW_SHA256 = "abfd0fa4d54a764290a030d1d2c83ef3ce06e7f8d422ee997af0711c6d83f409"
RUNTIME_HEAD_SHA = "378d12cd7faf6aa320acd50d2f6fb5e555200e17"
RUNTIME_TREE_SHA = "35e6aa63fcb4a6ea66fed45b683ad63f84a7e450"
GITHUB_REPOSITORY = "phoenix-hacking/mckernel"
GITHUB_RUN_ID = 32090075305
GITHUB_RUN_ATTEMPT = 1
GITHUB_JOB_ID = 95570363996
ARTIFACT_ID = 9308096471
ARTIFACT_NAME = "rk005-config-resolution-32090075305-1"
ARTIFACT_SIZE = 1424826
ARTIFACT_SHA256 = "44295264fdb63fb7e77eb75787f45c6a634cbe5cddae29f42e7af365c54067a6"
ARTIFACT_EXPIRES_AT = "2026-09-17T02:01:30Z"
BASELINE_CONFIG_SHA256 = (
    "5bbdda60ce822ec903c85d3d8ddda1bfc9493216bed86c6c432683aa50dcf50d"
)
CONTROL_CONFIG_SHA256 = (
    "dd7d3cc37c37b94e6a479d172bbaaeb17a6e863f4fa13fa1f5fe19c3548393e4"
)
FRAGMENT_CONFIG_SHA256 = (
    "25dd0fc5647d8addfd650469aad758ca41d7e9599f0d02e34c2025e438114983"
)
RESOLVED_CONFIG_SHA256 = (
    "fc8c835cdd67d50bf71353d956b0c9932ea83a2553a79a951e9254cf72505b7a"
)
EXPECTED_GATE_CLAIMS = {
    "RK-002": False,
    "RK-003": False,
    "RK-004": False,
    "RK-005": False,
    "RK-006": False,
    "RS-001": False,
}
EXPECTED_REPOSITORY_INPUTS = (
    ".github/workflows/rocky-kernel-config-resolution.yml",
    "host-kernel/rocky/config-policy.json",
    "host-kernel/rocky/configs/rust-minimal.config",
    "host-kernel/rocky/evidence/config-resolution-contract-v1.json",
    "host-kernel/rocky/patches/series.json",
    "host-kernel/rocky/source-lock.json",
    "host-kernel/rocky/toolchain-lock.json",
    "scripts/rocky_kernel_config_resolution.py",
)
EXPECTED_ARCHIVE_PATHS = (
    "capture.exit-code",
    "capture.log",
    "capture/SHA256SUMS",
    "capture/baseline.config",
    "capture/blockers.json",
    "capture/checkpoint.json",
    "capture/commands.json",
    "capture/config-delta.json",
    "capture/control-pass-1.config",
    "capture/control-pass-2.config",
    "capture/dependency-assertions.json",
    "capture/environment.json",
    "capture/fragment.config",
    "capture/resolved-pass-1.config",
    "capture/resolved-pass-2.config",
    "workflow-state",
)
EXPECTED_CHECKSUM_NAMES = (
    "baseline.config",
    "fragment.config",
    "control-pass-1.config",
    "control-pass-2.config",
    "resolved-pass-1.config",
    "resolved-pass-2.config",
    "commands.json",
    "environment.json",
    "config-delta.json",
    "dependency-assertions.json",
    "blockers.json",
    "checkpoint.json",
)
EXPECTED_REQUESTED_CHANGES = [
    {"after": "n", "before": "y", "symbol": "CONFIG_MODVERSIONS"},
    {"after": "y", "before": "n", "symbol": "CONFIG_RUST"},
]
EXPECTED_DERIVED_CHANGES = [
    {"after": "n", "before": "y", "symbol": "CONFIG_ASM_MODVERSIONS"}
]
EXPECTED_REQUESTED_GENERATED_CHANGES = [
    {
        "after": '"bindgen 0.72.1"',
        "before": "n",
        "symbol": "CONFIG_BINDGEN_VERSION_TEXT",
    },
    {
        "after": (
            '"rustc 1.92.0 (ded5c06cf 2025-12-08) '
            '(Red Hat 1.92.0-1.el10)"'
        ),
        "before": "n",
        "symbol": "CONFIG_RUSTC_VERSION_TEXT",
    },
]
EXPECTED_GENERATED_SYMBOL_RESULTS = {
    "CONFIG_BINDGEN_VERSION_TEXT": '"bindgen 0.72.1"',
    "CONFIG_PAHOLE_HAS_BTF_TAG": "y",
    "CONFIG_PAHOLE_HAS_LANG_EXCLUDE": "y",
    "CONFIG_PAHOLE_HAS_SPLIT_BTF": "y",
    "CONFIG_PAHOLE_VERSION": "131",
    "CONFIG_RUSTC_HAS_UNNECESSARY_TRANSMUTES": "y",
    "CONFIG_RUSTC_LLVM_VERSION": "210106",
    "CONFIG_RUSTC_VERSION": "109200",
    "CONFIG_RUSTC_VERSION_TEXT": (
        '"rustc 1.92.0 (ded5c06cf 2025-12-08) '
        '(Red Hat 1.92.0-1.el10)"'
    ),
    "CONFIG_RUST_IS_AVAILABLE": "y",
}
EXPECTED_TOOL_PROBES = {
    "bindgen": {
        "owner": "bindgen-cli-0:0.72.1-1.el10.x86_64",
        "sha256": "55880234cb76e4fd13f7401308c61db687301624be48adfd23c3c2cd0797b37c",
    },
    "clang": {
        "owner": "clang-0:21.1.8-1.el10.x86_64",
        "sha256": "48271e3fbb759560a54e6f0a13e05a4a0b768eea2ffd6aa2f1e14b8cbb76fb7f",
    },
    "lld": {
        "owner": "lld-0:21.1.8-1.el10.x86_64",
        "sha256": "52029c7d731c74ab72a2eca8126d578547242b3192ba74e27c94c1b51be001f9",
    },
    "llvm": {
        "owner": "llvm-devel-0:21.1.8-1.el10.x86_64",
        "sha256": "bdf82677530a0997abccadea0d9ce6aa3146d5d542ded5b589a095e4121b3cf0",
    },
    "pahole": {
        "owner": "dwarves-0:1.31-1.el10.x86_64",
        "sha256": "099aa2c9d0f4d22cad3cf65a1dab89bfc11b500f568497a276eec0052b65398b",
    },
    "rust_src_core": {
        "owner": "rust-src-0:1.92.0-1.el10.noarch",
        "sha256": "38ed9003ea2427f8803317e3e040d69f988d88534468bb28cbf83f27e2b51080",
    },
    "rustc": {
        "owner": "rust-0:1.92.0-1.el10.x86_64",
        "sha256": "38eeb1652fb59753cb7736e354ec1579a543da9a2eb8a68be102a41e88eb5dc6",
    },
}
EXPECTED_ENVIRONMENT_DERIVED = {
    "bindgen_version_text": "bindgen 0.72.1",
    "pahole_version": 131,
    "rustc_llvm_version": 210106,
    "rustc_version": 109200,
    "rustc_version_text": (
        "rustc 1.92.0 (ded5c06cf 2025-12-08) (Red Hat 1.92.0-1.el10)"
    ),
}
EXPECTED_FIXED_ENVIRONMENT = {
    "ARCH": "x86_64",
    "HOME": "/root",
    "LANG": "C",
    "LC_ALL": "C",
    "PATH": "/usr/sbin:/usr/bin:/sbin:/bin",
    "TZ": "UTC",
}
EXPECTED_REMAINING_PREREQUISITES = [
    (
        "Durably archive the exact artifact ZIP; the GitHub Actions copy has "
        "only 30-day retention."
    ),
    (
        "Reconcile CONFIG_RUSTC_HAS_UNNECESSARY_TRANSMUTES into the RK-005 "
        "generated-symbol policy and platform-lock checker."
    ),
    (
        "Reconcile the RK-003 llvm-config authority from llvm to the observed "
        "llvm-devel package owner."
    ),
    (
        "Represent and enforce the baseline-to-control-to-resolved "
        "classification before ingesting this evidence into the RK-005 authority lock."
    ),
    (
        "Independently review and durably archive the RK-003 closure/offline "
        "replay before RK-005 inherits toolchain authority."
    ),
    (
        "Prove a production kernel build final .config is byte-identical to the "
        "reviewed resolved config sha256 {}."
    ).format(RESOLVED_CONFIG_SHA256),
]
EXPECTED_DEPENDENCIES = {
    "CONFIG_CALL_PADDING": "y",
    "CONFIG_CFI_CLANG": "n",
    "CONFIG_GCC_PLUGIN_RANDSTRUCT": "n",
    "CONFIG_HAVE_RUST": "y",
    "CONFIG_KASAN": "n",
    "CONFIG_KASAN_SW_TAGS": "n",
    "CONFIG_MITIGATION_RETHUNK": "y",
    "CONFIG_MODVERSIONS": "n",
    "CONFIG_PAHOLE_HAS_LANG_EXCLUDE": "y",
    "CONFIG_RANDSTRUCT": "n",
    "CONFIG_RUST_IS_AVAILABLE": "y",
}
EXPECTED_PRESERVATION = {
    "btf_debug": {
        "CONFIG_BPF_SYSCALL": "y",
        "CONFIG_DEBUG_INFO": "y",
        "CONFIG_DEBUG_INFO_BTF": "y",
        "CONFIG_DEBUG_INFO_BTF_MODULES": "y",
        "CONFIG_DEBUG_INFO_DWARF_TOOLCHAIN_DEFAULT": "y",
        "CONFIG_DEBUG_INFO_REDUCED": "n",
        "CONFIG_DEBUG_INFO_SPLIT": "n",
    },
    "module_signing": {
        "CONFIG_CRYPTO_RSA": "y",
        "CONFIG_CRYPTO_SHA512": "y",
        "CONFIG_MODULES": "y",
        "CONFIG_MODULE_ALLOW_BTF_MISMATCH": "n",
        "CONFIG_MODULE_SIG": "y",
        "CONFIG_MODULE_SIG_ALL": "y",
        "CONFIG_MODULE_SIG_FORCE": "n",
        "CONFIG_MODULE_SIG_KEY": '"certs/signing_key.pem"',
        "CONFIG_MODULE_SIG_KEY_TYPE_RSA": "y",
        "CONFIG_MODULE_SIG_SHA512": "y",
    },
}


class ConfigReviewError(RuntimeError):
    """Raised when a review or artifact is malformed or overclaims evidence."""


def reject_duplicate_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ConfigReviewError("duplicate JSON key: {!r}".format(key))
        result[key] = value
    return result


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
        raise ConfigReviewError("value is not canonical JSON: {}".format(exc))
    return (text + "\n").encode("ascii")


def read_json_bytes(data, label, require_canonical=False):
    try:
        text = data.decode("ascii")
        value = json.loads(text, object_pairs_hook=reject_duplicate_pairs)
    except (UnicodeError, ValueError) as exc:
        raise ConfigReviewError("{} is not valid JSON: {}".format(label, exc))
    if not isinstance(value, dict):
        raise ConfigReviewError("{} must be a JSON object".format(label))
    if require_canonical and data != canonical_json_bytes(value):
        raise ConfigReviewError("{} is not canonical JSON".format(label))
    return value


def exact_keys(value, expected, label):
    if not isinstance(value, dict) or set(value) != set(expected):
        raise ConfigReviewError("{} has unexpected keys".format(label))
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
            same_value_and_type(left, right)
            for left, right in zip(actual, expected)
        )
    return actual == expected


def require_exact(actual, expected, label):
    if not same_value_and_type(actual, expected):
        raise ConfigReviewError(
            "{} differs: {!r} != {!r}".format(label, actual, expected)
        )


def require_positive_int(value, label):
    if type(value) is not int or value < 1:
        raise ConfigReviewError("{} is not a positive integer".format(label))
    return value


def validate_sha256(value, label):
    if not isinstance(value, str) or HEX_SHA256.fullmatch(value) is None:
        raise ConfigReviewError("{} is not a SHA-256".format(label))


def safe_relative_path(value, label):
    if not isinstance(value, str):
        raise ConfigReviewError("{} is not text".format(label))
    path = PurePosixPath(value)
    if (
        path.is_absolute()
        or not path.parts
        or "\\" in value
        or "\x00" in value
        or "//" in value
        or any(part in ("", ".", "..") for part in value.split("/"))
    ):
        raise ConfigReviewError("{} is unsafe: {!r}".format(label, value))
    return value


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def regular_file(path, label):
    try:
        status = path.lstat()
    except OSError as exc:
        raise ConfigReviewError("cannot inspect {}: {}".format(label, exc))
    if not stat.S_ISREG(status.st_mode) or path.is_symlink():
        raise ConfigReviewError("{} is not a regular file".format(label))
    return path


def within(root, candidate):
    try:
        common = os.path.commonpath((str(root), str(candidate)))
    except ValueError:
        return False
    return Path(common) == root


def repository_file(repo, relative, label):
    relative = safe_relative_path(relative, label + " path")
    root = repo.resolve()
    requested = root.joinpath(*PurePosixPath(relative).parts)
    try:
        resolved = requested.resolve()
    except OSError as exc:
        raise ConfigReviewError("cannot resolve {}: {}".format(label, exc))
    if not within(root, resolved):
        raise ConfigReviewError("{} escapes the repository".format(label))
    if requested != resolved:
        raise ConfigReviewError("{} traverses a symlink".format(label))
    return regular_file(requested, label)


def run_git(repo, arguments, allow_failure=False):
    command = ["git", "-C", str(repo)] + list(arguments)
    try:
        completed = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except OSError as exc:
        raise ConfigReviewError("git failed to execute: {}".format(exc))
    if completed.returncode != 0 and not allow_failure:
        raise ConfigReviewError(
            "git command failed: {}".format(
                completed.stderr.decode("utf-8", errors="replace").strip()
            )
        )
    return completed


def git_tree_record(repo, revision, path, label):
    completed = run_git(repo, ["ls-tree", revision, "--", path])
    rows = completed.stdout.decode("ascii").splitlines()
    if len(rows) != 1:
        raise ConfigReviewError("{} has no unique tree entry".format(label))
    match = re.fullmatch(r"(100644) blob ([0-9a-f]{40})\t(.+)", rows[0])
    if match is None or match.group(3) != path:
        raise ConfigReviewError("{} tree entry is malformed".format(label))
    return match.group(1), match.group(2)


def git_blob_bytes(repo, blob, label):
    completed = run_git(repo, ["cat-file", "blob", blob])
    if sha256_bytes(completed.stdout) == EMPTY_SHA256:
        raise ConfigReviewError("{} is unexpectedly empty".format(label))
    return completed.stdout


def validate_input_row(repo, runtime_head, row, current_head, label):
    exact_keys(row, {"git_blob_sha1", "path", "sha256", "size"}, label)
    path = safe_relative_path(row["path"], label + ".path")
    require_positive_int(row["size"], label + " size")
    validate_sha256(row["sha256"], label + ".sha256")
    if not isinstance(row["git_blob_sha1"], str) or HEX_SHA1.fullmatch(
        row["git_blob_sha1"]
    ) is None:
        raise ConfigReviewError("{} has invalid Git blob".format(label))
    _, runtime_blob = git_tree_record(repo, runtime_head, path, label + " runtime")
    require_exact(runtime_blob, row["git_blob_sha1"], label + " runtime blob")
    data = git_blob_bytes(repo, runtime_blob, label + " runtime blob")
    require_exact(len(data), row["size"], label + " runtime size")
    require_exact(sha256_bytes(data), row["sha256"], label + " runtime digest")

    _, head_blob = git_tree_record(repo, current_head, path, label + " current HEAD")
    require_exact(head_blob, runtime_blob, label + " current HEAD blob")
    index = run_git(repo, ["ls-files", "--stage", "--", path])
    index_rows = index.stdout.decode("ascii").splitlines()
    if len(index_rows) != 1:
        raise ConfigReviewError("{} has no unique index entry".format(label))
    index_match = re.fullmatch(r"100644 ([0-9a-f]{40}) 0\t(.+)", index_rows[0])
    if index_match is None or index_match.group(2) != path:
        raise ConfigReviewError("{} index entry is malformed".format(label))
    require_exact(index_match.group(1), runtime_blob, label + " index blob")
    worktree = repository_file(repo, path, label + " worktree")
    worktree_data = worktree.read_bytes()
    require_exact(len(worktree_data), row["size"], label + " worktree size")
    require_exact(
        sha256_bytes(worktree_data), row["sha256"], label + " worktree digest"
    )


def discover_review(repo, explicit=None):
    if explicit is not None:
        path = explicit if explicit.is_absolute() else repo / explicit
        return regular_file(path, "review manifest")
    root = repo / REVIEW_DIRECTORY
    candidates = sorted(root.glob(REVIEW_GLOB))
    if len(candidates) != 1:
        raise ConfigReviewError(
            "expected exactly one {} manifest, found {}".format(
                REVIEW_GLOB, len(candidates)
            )
        )
    return regular_file(candidates[0], "review manifest")


def load_review(path):
    data = path.read_bytes()
    require_exact(sha256_bytes(data), REVIEW_SHA256, "review manifest digest")
    return read_json_bytes(data, "review manifest", require_canonical=True)


def validate_review_object(review):
    exact_keys(
        review,
        {
            "caveats",
            "claims",
            "current_repository_input_policy",
            "remaining_prerequisites",
            "review_id",
            "review_kind",
            "runtime_candidate",
            "schema_version",
            "source_artifact",
            "verified_facts",
            "zip_closure",
        },
        "review",
    )
    require_exact(review["schema_version"], SCHEMA_VERSION, "review schema")
    require_exact(review["review_id"], REVIEW_ID, "review id")
    require_exact(
        review["review_kind"],
        "historical-exact-config-resolution-bounded-pass",
        "review kind",
    )
    claims = exact_keys(
        review["claims"],
        {
            "credit_eligible",
            "gate_claims",
            "network_isolation_claimed",
            "offline_toolchain_proven",
            "production_build_proven",
            "runtime_identity_claimed",
            "tracker_credit",
        },
        "claims",
    )
    require_exact(claims["gate_claims"], EXPECTED_GATE_CLAIMS, "gate claims")
    for key in claims:
        if key != "gate_claims" and claims[key] is not False:
            raise ConfigReviewError("{} must remain false".format(key))
    policy = exact_keys(
        review["current_repository_input_policy"],
        {
            "bound_input_count",
            "relationship",
            "require_head_index_worktree_equality",
            "runtime_identity_claimed",
        },
        "current input policy",
    )
    require_exact(policy["relationship"], "descendant-or-equal", "relationship")
    require_exact(
        policy["require_head_index_worktree_equality"], True, "input equality"
    )
    require_exact(
        policy["runtime_identity_claimed"], False, "current runtime claim"
    )
    caveats = exact_keys(
        review["caveats"],
        {
            "archive_bytes_committed",
            "artifact_retention_is_durable",
            "checkpoint_excludes_self_but_sha256sums_covers_it",
            "config_werror_is_observed_not_policy_locked",
            "container_claim_boundary",
            "current_head_runtime_identity",
            "production_build_config_bound",
            "raw_rustavailable_stdout_archived",
        },
        "caveats",
    )
    for key in (
        "archive_bytes_committed",
        "artifact_retention_is_durable",
        "current_head_runtime_identity",
        "production_build_config_bound",
        "raw_rustavailable_stdout_archived",
    ):
        require_exact(caveats.get(key), False, "caveat " + key)
    require_exact(
        caveats.get("checkpoint_excludes_self_but_sha256sums_covers_it"),
        True,
        "checkpoint caveat",
    )
    require_exact(
        caveats.get("config_werror_is_observed_not_policy_locked"),
        True,
        "CONFIG_WERROR caveat",
    )
    require_exact(
        caveats["container_claim_boundary"],
        (
            "GitHub job logs prove selection, pull, and creation of the "
            "digest-pinned Rocky 10.2 image; the artifact records that "
            "selection but does not contain a separate in-container OCI "
            "manifest attestation."
        ),
        "container claim boundary",
    )

    source = exact_keys(
        review["source_artifact"],
        {"artifact", "durable_archive", "expires_at", "github", "retention_days"},
        "source artifact",
    )
    require_exact(source["durable_archive"], False, "durable archive claim")
    require_exact(source["retention_days"], 30, "artifact retention")
    require_exact(source["expires_at"], ARTIFACT_EXPIRES_AT, "artifact expiry")
    artifact = exact_keys(
        source["artifact"],
        {"archive_file_name", "id", "name", "sha256", "size"},
        "artifact",
    )
    require_exact(artifact["id"], ARTIFACT_ID, "artifact id")
    require_exact(artifact["name"], ARTIFACT_NAME, "artifact name")
    require_exact(
        artifact["archive_file_name"], ARTIFACT_NAME + ".zip", "archive name"
    )
    require_exact(artifact["size"], ARTIFACT_SIZE, "artifact size")
    require_exact(artifact["sha256"], ARTIFACT_SHA256, "artifact digest")
    github = exact_keys(
        source["github"],
        {"job_id", "repository", "run_attempt", "run_id", "runtime_head_sha"},
        "GitHub identity",
    )
    require_exact(github["repository"], GITHUB_REPOSITORY, "repository")
    require_exact(github["run_id"], GITHUB_RUN_ID, "GitHub run id")
    require_exact(github["run_attempt"], GITHUB_RUN_ATTEMPT, "GitHub run attempt")
    require_exact(github["job_id"], GITHUB_JOB_ID, "GitHub job id")
    require_exact(github["runtime_head_sha"], RUNTIME_HEAD_SHA, "GitHub runtime head")

    runtime = exact_keys(
        review["runtime_candidate"],
        {"committed_inputs", "container", "head_sha", "tree_sha"},
        "runtime candidate",
    )
    for key in ("head_sha", "tree_sha"):
        if not isinstance(runtime[key], str) or HEX_SHA1.fullmatch(runtime[key]) is None:
            raise ConfigReviewError("runtime {} is invalid".format(key))
    require_exact(runtime["head_sha"], RUNTIME_HEAD_SHA, "runtime head")
    require_exact(runtime["tree_sha"], RUNTIME_TREE_SHA, "runtime tree")
    require_exact(github["runtime_head_sha"], runtime["head_sha"], "runtime head")
    container = exact_keys(
        runtime["container"],
        {
            "image",
            "manifest_digest",
            "runtime_architecture",
            "runtime_os_id",
            "runtime_os_version_id",
        },
        "container",
    )
    require_exact(container["image"], CONTAINER_IMAGE, "container image")
    require_exact(
        container["manifest_digest"], CONTAINER_IMAGE.split("@", 1)[1], "container digest"
    )
    require_exact(container["runtime_architecture"], "x86_64", "container arch")
    require_exact(container["runtime_os_id"], "rocky", "container OS")
    require_exact(container["runtime_os_version_id"], "10.2", "container version")

    inputs = runtime["committed_inputs"]
    if not isinstance(inputs, list):
        raise ConfigReviewError("committed inputs must be a list")
    require_exact(
        tuple(row.get("path") for row in inputs),
        EXPECTED_REPOSITORY_INPUTS,
        "committed input paths",
    )
    for index, row in enumerate(inputs):
        exact_keys(
            row,
            {"git_blob_sha1", "path", "sha256", "size"},
            "committed input {}".format(index),
        )
        safe_relative_path(row["path"], "committed input path")
        validate_sha256(row["sha256"], "committed input digest")
        require_positive_int(row["size"], "committed input size")
        if not isinstance(row["git_blob_sha1"], str) or HEX_SHA1.fullmatch(
            row["git_blob_sha1"]
        ) is None:
            raise ConfigReviewError("committed input Git blob is invalid")

    facts = exact_keys(
        review["verified_facts"],
        {
            "artifact_state",
            "configurations",
            "delta",
            "dependency_assertions",
            "patch_authority",
            "tool_probes",
        },
        "verified facts",
    )
    artifact_state = exact_keys(
        facts["artifact_state"],
        {
            "capture_exit_code",
            "capture_log_sha256",
            "workflow_state",
            "workflow_state_sha256",
        },
        "artifact state",
    )
    require_exact(artifact_state["capture_exit_code"], 0, "capture exit code")
    require_exact(
        artifact_state["workflow_state"], "bootstrap-complete", "workflow state"
    )
    validate_sha256(artifact_state["capture_log_sha256"], "capture log digest")
    validate_sha256(artifact_state["workflow_state_sha256"], "workflow state digest")
    patch_authority = exact_keys(
        facts["patch_authority"], {"count", "patches"}, "patch authority"
    )
    patches = patch_authority["patches"]
    if not isinstance(patches, list) or len(patches) != patch_authority["count"]:
        raise ConfigReviewError("patch authority count is inconsistent")
    require_exact(len(patches), 23, "compatibility patch count")
    patch_paths = []
    for index, row in enumerate(patches):
        exact_keys(row, {"path", "sha256"}, "patch {}".format(index))
        safe_relative_path(row["path"], "patch path")
        validate_sha256(row["sha256"], "patch digest")
        patch_paths.append(row["path"])
    if len(set(patch_paths)) != len(patch_paths):
        raise ConfigReviewError("patch paths are duplicated")
    require_exact(
        policy["bound_input_count"], len(inputs) + len(patches), "bound input count"
    )

    configurations = exact_keys(
        facts["configurations"],
        {"baseline", "control", "fragment", "resolved"},
        "configurations",
    )
    exact_keys(
        configurations["baseline"],
        {"path", "sha256", "size", "symbol_count"},
        "baseline configuration",
    )
    exact_keys(
        configurations["fragment"],
        {"path", "sha256", "size"},
        "fragment configuration",
    )
    for name in ("control", "resolved"):
        exact_keys(
            configurations[name],
            {"byte_identical", "paths", "sha256", "size", "symbol_count"},
            name + " configuration",
        )
        require_exact(configurations[name]["byte_identical"], True, name + " equivalence")
    require_exact(
        configurations["baseline"]["path"],
        "capture/baseline.config",
        "baseline path",
    )
    require_exact(
        configurations["fragment"]["path"],
        "capture/fragment.config",
        "fragment path",
    )
    require_exact(
        configurations["control"]["paths"],
        ["capture/control-pass-1.config", "capture/control-pass-2.config"],
        "control paths",
    )
    require_exact(
        configurations["resolved"]["paths"],
        ["capture/resolved-pass-1.config", "capture/resolved-pass-2.config"],
        "resolved paths",
    )
    for name in ("baseline", "control", "fragment", "resolved"):
        validate_sha256(configurations[name]["sha256"], name + " digest")
        require_positive_int(configurations[name]["size"], name + " size")
        if "symbol_count" in configurations[name]:
            require_positive_int(
                configurations[name]["symbol_count"], name + " symbol count"
            )
    require_exact(
        configurations["baseline"]["sha256"],
        BASELINE_CONFIG_SHA256,
        "baseline digest",
    )
    require_exact(
        configurations["control"]["sha256"],
        CONTROL_CONFIG_SHA256,
        "control digest",
    )
    require_exact(
        configurations["fragment"]["sha256"],
        FRAGMENT_CONFIG_SHA256,
        "fragment digest",
    )
    require_exact(
        configurations["resolved"]["sha256"],
        RESOLVED_CONFIG_SHA256,
        "resolved digest",
    )
    delta = exact_keys(
        facts["delta"],
        {
            "derived_changes",
            "environment_generated_change_count",
            "generated_symbol_results",
            "requested_changes",
            "requested_generated_symbols",
            "unexpected_generated_symbols",
        },
        "config delta",
    )
    require_exact(delta["requested_changes"], EXPECTED_REQUESTED_CHANGES, "requested delta")
    require_exact(delta["derived_changes"], EXPECTED_DERIVED_CHANGES, "derived delta")
    require_exact(
        delta["requested_generated_symbols"],
        EXPECTED_REQUESTED_GENERATED_CHANGES,
        "requested generated delta",
    )
    require_exact(
        delta["generated_symbol_results"],
        EXPECTED_GENERATED_SYMBOL_RESULTS,
        "generated symbol results",
    )
    require_exact(delta["unexpected_generated_symbols"], [], "unexpected symbols")
    require_exact(
        delta["environment_generated_change_count"], 1733, "environment delta count"
    )

    dependency_facts = exact_keys(
        facts["dependency_assertions"],
        {"dependency_count", "preservation_group_counts"},
        "dependency assertion facts",
    )
    require_exact(
        dependency_facts["dependency_count"],
        len(EXPECTED_DEPENDENCIES),
        "dependency assertion count",
    )
    require_exact(
        dependency_facts["preservation_group_counts"],
        {"btf_debug": 7, "module_signing": 10},
        "preservation group counts",
    )

    tool_probes = exact_keys(
        facts["tool_probes"], set(EXPECTED_TOOL_PROBES), "reviewed tool probes"
    )
    for name, expected in EXPECTED_TOOL_PROBES.items():
        exact_keys(tool_probes[name], {"owner", "sha256"}, name + " reviewed probe")
        require_exact(tool_probes[name], expected, name + " reviewed probe")

    prerequisites = review["remaining_prerequisites"]
    require_exact(
        prerequisites, EXPECTED_REMAINING_PREREQUISITES, "remaining prerequisites"
    )

    closure = exact_keys(
        review["zip_closure"],
        {
            "compressed_payload_size",
            "compression_methods",
            "crc_verified",
            "duplicate_paths",
            "entry_count",
            "entry_index_sha256",
            "external_attributes",
            "internal_sha256sums_sha256",
            "path_index_sha256",
            "safe_regular_files_only",
            "uncompressed_size",
        },
        "ZIP closure",
    )
    require_exact(closure["entry_count"], len(EXPECTED_ARCHIVE_PATHS), "ZIP count")
    require_exact(closure["compression_methods"], [0], "ZIP compression")
    require_exact(closure["crc_verified"], True, "ZIP CRC claim")
    require_exact(closure["duplicate_paths"], False, "ZIP duplicate claim")
    require_exact(closure["safe_regular_files_only"], True, "ZIP safety claim")
    require_positive_int(closure["compressed_payload_size"], "ZIP compressed size")
    require_positive_int(closure["uncompressed_size"], "ZIP uncompressed size")
    require_exact(
        closure["external_attributes"],
        [2164260896, 2175008800],
        "ZIP external attributes",
    )
    for key in ("entry_index_sha256", "internal_sha256sums_sha256", "path_index_sha256"):
        validate_sha256(closure[key], "ZIP " + key)
    return review


def validate_repository(repo, review):
    runtime = review["runtime_candidate"]
    runtime_head = runtime["head_sha"]
    current_head = run_git(repo, ["rev-parse", "HEAD"]).stdout.decode("ascii").strip()
    if HEX_SHA1.fullmatch(current_head) is None:
        raise ConfigReviewError("current HEAD is malformed")
    runtime_type = run_git(repo, ["cat-file", "-t", runtime_head]).stdout.decode(
        "ascii"
    ).strip()
    require_exact(runtime_type, "commit", "runtime object type")
    runtime_tree = run_git(repo, ["show", "-s", "--format=%T", runtime_head]).stdout.decode(
        "ascii"
    ).strip()
    require_exact(runtime_tree, runtime["tree_sha"], "runtime tree")
    ancestor = run_git(
        repo, ["merge-base", "--is-ancestor", runtime_head, current_head], allow_failure=True
    )
    if ancestor.returncode != 0:
        raise ConfigReviewError("current HEAD is not a descendant of the reviewed head")
    rows = list(runtime["committed_inputs"]) + list(
        review["verified_facts"]["patch_authority"]["patches"]
    )
    for index, original in enumerate(rows):
        row = dict(original)
        if "git_blob_sha1" not in row:
            path = row["path"]
            _, blob = git_tree_record(repo, runtime_head, path, "patch {}".format(index))
            data = git_blob_bytes(repo, blob, "patch {}".format(index))
            row["git_blob_sha1"] = blob
            row["size"] = len(data)
        validate_input_row(
            repo,
            runtime_head,
            row,
            current_head,
            "bound input {}".format(index),
        )
    return current_head


def safe_zip_path(name):
    safe_relative_path(name, "ZIP entry")
    if name.endswith("/"):
        raise ConfigReviewError("ZIP directories are forbidden")
    return name


def zip_entry_records(archive):
    records = []
    names = []
    for info in archive.infolist():
        name = safe_zip_path(info.filename)
        names.append(name)
        mode = info.external_attr >> 16
        if not stat.S_ISREG(mode):
            raise ConfigReviewError("ZIP entry is not a regular file: " + name)
        if info.flag_bits & 0x1:
            raise ConfigReviewError("encrypted ZIP entries are forbidden")
        try:
            data = archive.read(info)
        except (OSError, RuntimeError, zipfile.BadZipFile) as exc:
            raise ConfigReviewError("cannot read ZIP entry {}: {}".format(name, exc))
        records.append(
            {
                "compressed_size": info.compress_size,
                "compression_method": info.compress_type,
                "crc32": format(info.CRC, "08x"),
                "external_attributes": info.external_attr,
                "path": name,
                "sha256": sha256_bytes(data),
                "size": info.file_size,
            }
        )
    if len(names) != len(set(names)):
        raise ConfigReviewError("ZIP contains duplicate paths")
    records.sort(key=lambda row: row["path"])
    return records


def parse_sha256sums(data):
    try:
        text = data.decode("ascii")
    except UnicodeError as exc:
        raise ConfigReviewError("SHA256SUMS is not ASCII: {}".format(exc))
    if not text.endswith("\n"):
        raise ConfigReviewError("SHA256SUMS lacks its final newline")
    result = {}
    for line in text.splitlines():
        match = SHA256SUM.fullmatch(line)
        if match is None:
            raise ConfigReviewError("SHA256SUMS has a malformed row")
        digest, name = match.groups()
        safe_relative_path(name, "checksum path")
        if name in result:
            raise ConfigReviewError("SHA256SUMS has a duplicate path")
        result[name] = digest
    require_exact(tuple(result), EXPECTED_CHECKSUM_NAMES, "checksum paths")
    return result


def parse_config(data, label):
    try:
        text = data.decode("utf-8")
    except UnicodeError as exc:
        raise ConfigReviewError("{} is not UTF-8: {}".format(label, exc))
    values = {}
    for line_number, line in enumerate(text.splitlines(), 1):
        match = CONFIG_VALUE.fullmatch(line)
        if match is not None:
            symbol, value = match.groups()
        else:
            match = CONFIG_UNSET.fullmatch(line)
            if match is None:
                continue
            symbol, value = match.group(1), "n"
        if symbol in values:
            raise ConfigReviewError(
                "{}:{} duplicates {}".format(label, line_number, symbol)
            )
        values[symbol] = value
    if not values:
        raise ConfigReviewError("{} contains no config symbols".format(label))
    return values


def semantic_config_value(value):
    return "n" if value == "<absent>" else value


def changed_symbols(before, after):
    return [
        {
            "after": semantic_config_value(after.get(symbol, "<absent>")),
            "before": semantic_config_value(before.get(symbol, "<absent>")),
            "symbol": symbol,
        }
        for symbol in sorted(set(before) | set(after))
        if semantic_config_value(before.get(symbol, "<absent>"))
        != semantic_config_value(after.get(symbol, "<absent>"))
    ]


def verify_config_record(files, record, label):
    paths = record.get("paths") or [record.get("path")]
    if not paths or any(path not in files for path in paths):
        raise ConfigReviewError("{} paths are incomplete".format(label))
    values = []
    for path in paths:
        data = files[path]
        require_exact(len(data), record["size"], label + " size")
        require_exact(sha256_bytes(data), record["sha256"], label + " digest")
        values.append(parse_config(data, label))
    if "symbol_count" in record:
        for config in values:
            require_exact(len(config), record["symbol_count"], label + " symbol count")
    if len(paths) == 2:
        require_exact(files[paths[0]], files[paths[1]], label + " byte equivalence")
        require_exact(values[0], values[1], label + " map equivalence")
    return values[0]


def verify_environment_document(environment, review, identity):
    exact_keys(
        environment,
        {"container_image", "fixed_environment", "github", "probes", "schema_version"},
        "environment",
    )
    require_exact(environment["container_image"], CONTAINER_IMAGE, "environment image")
    require_exact(environment["github"], identity, "environment identity")
    require_exact(environment["schema_version"], 1, "environment schema")
    require_exact(
        environment["fixed_environment"],
        EXPECTED_FIXED_ENVIRONMENT,
        "fixed environment",
    )
    probes = exact_keys(
        environment["probes"],
        set(EXPECTED_TOOL_PROBES) | {"derived"},
        "environment probes",
    )
    require_exact(
        probes["derived"], EXPECTED_ENVIRONMENT_DERIVED, "environment derivations"
    )
    reviewed_probes = review["verified_facts"]["tool_probes"]
    for name, expected in reviewed_probes.items():
        probe = probes[name]
        if name == "rust_src_core":
            exact_keys(
                probe,
                {
                    "command",
                    "file_path",
                    "file_sha256",
                    "owner_command",
                    "package_nevra",
                    "stderr_sha256",
                    "stdout_sha256",
                },
                name + " environment probe",
            )
        else:
            exact_keys(
                probe,
                {
                    "binary_path",
                    "binary_sha256",
                    "command",
                    "owner_command",
                    "package_nevra",
                    "stderr_sha256",
                    "stdout_sha256",
                    "text",
                },
                name + " environment probe",
            )
        require_exact(probe["package_nevra"], expected["owner"], name + " owner")
        digest_key = "file_sha256" if name == "rust_src_core" else "binary_sha256"
        require_exact(probe[digest_key], expected["sha256"], name + " binary digest")
        validate_sha256(probe["stdout_sha256"], name + " stdout digest")
        if "text" in probe:
            require_exact(
                sha256_bytes(probe["text"].encode("utf-8")),
                probe["stdout_sha256"],
                name + " stdout digest",
            )
        require_exact(probe["stderr_sha256"], EMPTY_SHA256, name + " stderr")


def verify_artifact(artifact_path, review):
    artifact_path = regular_file(artifact_path, "artifact ZIP")
    artifact_bytes = artifact_path.read_bytes()
    artifact = review["source_artifact"]["artifact"]
    require_exact(len(artifact_bytes), artifact["size"], "artifact size")
    require_exact(sha256_bytes(artifact_bytes), artifact["sha256"], "artifact digest")
    try:
        archive = zipfile.ZipFile(str(artifact_path), "r")
    except (OSError, zipfile.BadZipFile) as exc:
        raise ConfigReviewError("artifact is not a readable ZIP: {}".format(exc))
    with archive:
        if archive.comment:
            raise ConfigReviewError("ZIP comments are forbidden")
        records = zip_entry_records(archive)
        paths = tuple(row["path"] for row in records)
        require_exact(paths, EXPECTED_ARCHIVE_PATHS, "artifact paths")
        closure = review["zip_closure"]
        require_exact(len(records), closure["entry_count"], "ZIP entry count")
        require_exact(
            sum(row["compressed_size"] for row in records),
            closure["compressed_payload_size"],
            "ZIP compressed payload size",
        )
        require_exact(
            sum(row["size"] for row in records),
            closure["uncompressed_size"],
            "ZIP uncompressed size",
        )
        require_exact(
            sorted(set(row["compression_method"] for row in records)),
            closure["compression_methods"],
            "ZIP compression methods",
        )
        require_exact(
            sorted(set(row["external_attributes"] for row in records)),
            closure["external_attributes"],
            "ZIP external attributes",
        )
        require_exact(
            sha256_bytes(canonical_json_bytes(records)),
            closure["entry_index_sha256"],
            "ZIP entry index",
        )
        require_exact(
            sha256_bytes(canonical_json_bytes(sorted(paths))),
            closure["path_index_sha256"],
            "ZIP path index",
        )
        files = {name: archive.read(name) for name in paths}

    require_exact(files["capture.exit-code"], b"0\n", "capture exit code")
    require_exact(files["workflow-state"], b"bootstrap-complete\n", "workflow state")
    state = review["verified_facts"]["artifact_state"]
    require_exact(state["capture_exit_code"], 0, "reviewed exit code")
    require_exact(
        sha256_bytes(files["capture.log"]), state["capture_log_sha256"], "capture log"
    )
    require_exact(
        sha256_bytes(files["workflow-state"]),
        state["workflow_state_sha256"],
        "workflow state digest",
    )
    require_exact(
        state["workflow_state"], "bootstrap-complete", "reviewed workflow state"
    )

    sums_data = files["capture/SHA256SUMS"]
    require_exact(
        sha256_bytes(sums_data),
        review["zip_closure"]["internal_sha256sums_sha256"],
        "internal SHA256SUMS digest",
    )
    sums = parse_sha256sums(sums_data)
    for name, digest in sums.items():
        require_exact(
            sha256_bytes(files["capture/" + name]), digest, "checksum " + name
        )

    json_names = (
        "blockers.json",
        "checkpoint.json",
        "commands.json",
        "config-delta.json",
        "dependency-assertions.json",
        "environment.json",
    )
    documents = {
        name: read_json_bytes(files["capture/" + name], name, require_canonical=True)
        for name in json_names
    }
    exact_keys(
        documents["blockers.json"], {"gate_claims", "success_blockers"}, "blockers"
    )
    exact_keys(
        documents["checkpoint.json"],
        {
            "credit_eligible",
            "gate_claims",
            "github",
            "manifests",
            "phase",
            "schema_version",
            "two_independent_resolutions_identical",
        },
        "checkpoint",
    )
    exact_keys(
        documents["commands.json"], {"passes", "patches", "schema_version"}, "commands"
    )
    exact_keys(
        documents["config-delta.json"],
        {
            "derived_changes",
            "environment_generated_changes",
            "generated_symbol_results",
            "requested_changes",
            "requested_generated_symbols",
            "unexpected_generated_symbols",
        },
        "config delta",
    )
    exact_keys(
        documents["dependency-assertions.json"],
        {"dependencies", "preservation_groups"},
        "dependency assertions",
    )
    exact_keys(
        documents["environment.json"],
        {"container_image", "fixed_environment", "github", "probes", "schema_version"},
        "environment",
    )
    github = review["source_artifact"]["github"]
    identity = {
        "head_sha": github["runtime_head_sha"],
        "repository": github["repository"],
        "run_attempt": github["run_attempt"],
        "run_id": github["run_id"],
    }
    checkpoint = documents["checkpoint.json"]
    require_exact(checkpoint["credit_eligible"], False, "checkpoint credit")
    require_exact(checkpoint["gate_claims"], EXPECTED_GATE_CLAIMS, "checkpoint gates")
    require_exact(checkpoint["github"], identity, "checkpoint identity")
    require_exact(checkpoint["phase"], "config-resolution", "checkpoint phase")
    require_exact(checkpoint["schema_version"], 1, "checkpoint schema")
    require_exact(
        checkpoint["two_independent_resolutions_identical"],
        True,
        "checkpoint equivalence",
    )
    checkpoint_manifests = checkpoint["manifests"]
    if not isinstance(checkpoint_manifests, list):
        raise ConfigReviewError("checkpoint manifests must be a list")
    checkpoint_rows = {}
    for index, row in enumerate(checkpoint_manifests):
        exact_keys(row, {"path", "sha256", "size"}, "checkpoint row {}".format(index))
        path = safe_relative_path(row["path"], "checkpoint path")
        if path in checkpoint_rows:
            raise ConfigReviewError("checkpoint manifests contain a duplicate path")
        validate_sha256(row["sha256"], "checkpoint digest")
        require_positive_int(row["size"], "checkpoint size")
        checkpoint_rows[path] = (row["sha256"], row["size"])
    require_exact(
        set(checkpoint_rows), set(EXPECTED_CHECKSUM_NAMES) - {"checkpoint.json"},
        "checkpoint manifest paths",
    )
    for name, (digest, size) in checkpoint_rows.items():
        data = files["capture/" + name]
        require_exact((sha256_bytes(data), len(data)), (digest, size), "checkpoint " + name)

    blockers = documents["blockers.json"]
    require_exact(blockers["gate_claims"], EXPECTED_GATE_CLAIMS, "blocker gates")
    if not isinstance(blockers["success_blockers"], list) or len(
        blockers["success_blockers"]
    ) < 7:
        raise ConfigReviewError("artifact success blockers are incomplete")
    if not all(isinstance(item, str) and item for item in blockers["success_blockers"]):
        raise ConfigReviewError("artifact success blockers must be nonempty text")
    blocker_text = "\n".join(blockers["success_blockers"])
    for phrase in ("independent review", "production kernel build", "remain false"):
        if phrase not in blocker_text:
            raise ConfigReviewError("artifact blocker is missing: " + phrase)

    environment = documents["environment.json"]
    verify_environment_document(environment, review, identity)

    configurations = review["verified_facts"]["configurations"]
    baseline = verify_config_record(files, configurations["baseline"], "baseline")
    control = verify_config_record(files, configurations["control"], "control")
    resolved = verify_config_record(files, configurations["resolved"], "resolved")
    fragment_record = configurations["fragment"]
    fragment_data = files[fragment_record["path"]]
    require_exact(len(fragment_data), fragment_record["size"], "fragment size")
    require_exact(sha256_bytes(fragment_data), fragment_record["sha256"], "fragment digest")
    require_exact(
        fragment_data,
        b"CONFIG_RUST=y\n# CONFIG_MODVERSIONS is not set\n",
        "fragment bytes",
    )
    for name, values in (("baseline", baseline), ("control", control), ("resolved", resolved)):
        require_exact(values.get("CONFIG_WERROR"), "y", name + " CONFIG_WERROR")
    require_exact(resolved.get("CONFIG_RUST"), "y", "resolved CONFIG_RUST")
    require_exact(resolved.get("CONFIG_MODVERSIONS"), "n", "resolved MODVERSIONS")

    delta = documents["config-delta.json"]
    reviewed_delta = review["verified_facts"]["delta"]
    require_exact(
        delta["environment_generated_changes"],
        changed_symbols(baseline, control),
        "environment-generated delta",
    )
    require_exact(
        len(delta["environment_generated_changes"]),
        reviewed_delta["environment_generated_change_count"],
        "environment-generated delta count",
    )
    requested = changed_symbols(control, resolved)
    classified = sorted(
        delta["requested_changes"]
        + delta["derived_changes"]
        + delta["requested_generated_symbols"],
        key=lambda row: row["symbol"],
    )
    require_exact(classified, requested, "classified requested delta")
    for key in (
        "requested_changes",
        "derived_changes",
        "requested_generated_symbols",
        "unexpected_generated_symbols",
        "generated_symbol_results",
    ):
        require_exact(delta[key], reviewed_delta[key], "reviewed delta " + key)
    for symbol, expected in delta["generated_symbol_results"].items():
        actual = semantic_config_value(resolved.get(symbol, "<absent>"))
        require_exact(actual, expected, "generated " + symbol)

    assertions = documents["dependency-assertions.json"]
    require_exact(assertions["dependencies"], EXPECTED_DEPENDENCIES, "dependencies")
    require_exact(
        assertions["preservation_groups"], EXPECTED_PRESERVATION, "preservation groups"
    )
    for symbol, expected in EXPECTED_DEPENDENCIES.items():
        actual = semantic_config_value(resolved.get(symbol, "<absent>"))
        require_exact(actual, expected, "dependency " + symbol)
    for group, values in EXPECTED_PRESERVATION.items():
        require_exact(
            len(values),
            review["verified_facts"]["dependency_assertions"][
                "preservation_group_counts"
            ][group],
            group + " count",
        )
        for symbol, expected in values.items():
            require_exact(resolved.get(symbol), expected, "resolved " + symbol)
            require_exact(baseline.get(symbol), expected, "baseline " + symbol)
    require_exact(
        len(EXPECTED_DEPENDENCIES),
        review["verified_facts"]["dependency_assertions"]["dependency_count"],
        "dependency count",
    )

    commands = documents["commands.json"]
    require_exact(commands["schema_version"], 1, "commands schema")
    require_exact(
        commands["patches"],
        review["verified_facts"]["patch_authority"]["patches"],
        "artifact patch authority",
    )
    passes = commands["passes"]
    if not isinstance(passes, list) or len(passes) != 2:
        raise ConfigReviewError("commands require two passes")
    for number, row in enumerate(passes, 1):
        exact_keys(
            row,
            {
                "control_olddefconfig",
                "control_process_configs",
                "control_process_environment",
                "fragment_merge",
                "requested_olddefconfig",
                "requested_process_configs",
                "requested_process_environment",
                "requested_rustavailable",
                "source_cleanup",
            },
            "command pass {}".format(number),
        )
        marker = "/pass-{}/".format(number)
        if marker not in canonical_json_bytes(row).decode("ascii"):
            raise ConfigReviewError("command pass {} is not independently rooted".format(number))
        rustavailable = row["requested_rustavailable"]
        exact_keys(
            rustavailable,
            {
                "command",
                "exit_code",
                "stderr_sha256",
                "stdout_sha256",
                "success_line_count",
            },
            "rustavailable pass {}".format(number),
        )
        require_exact(rustavailable["exit_code"], 0, "rustavailable exit")
        require_exact(rustavailable["stderr_sha256"], EMPTY_SHA256, "rustavailable stderr")
        validate_sha256(rustavailable["stdout_sha256"], "rustavailable stdout")
        require_exact(rustavailable["success_line_count"], 1, "rustavailable success")
    return {
        "artifact_sha256": artifact["sha256"],
        "resolved_config_sha256": configurations["resolved"]["sha256"],
    }


def parse_args(argv):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--review", type=Path)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--check", action="store_true")
    modes.add_argument("--verify-artifact", type=Path)
    return parser.parse_args(argv)


def main(argv):
    args = parse_args(argv)
    repo = args.repo.resolve()
    try:
        path = discover_review(repo, args.review)
        review = validate_review_object(load_review(path))
        current_head = validate_repository(repo, review)
        if args.check:
            print(
                "bounded RK-005 config review verified at current descendant-or-equal {}; "
                "all gate and tracker claims remain false".format(current_head)
            )
            return 0
        result = verify_artifact(args.verify_artifact.resolve(), review)
        print(
            "bounded RK-005 artifact verified: zip sha256={} resolved config sha256={}; "
            "all gate and tracker claims remain false".format(
                result["artifact_sha256"], result["resolved_config_sha256"]
            )
        )
        return 0
    except (ConfigReviewError, OSError, UnicodeError, ValueError, zipfile.BadZipFile) as exc:
        print("Rocky config-review error: {}".format(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
