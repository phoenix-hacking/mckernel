#!/usr/bin/env python3
"""Verify one bounded, non-crediting hosted Rocky runtime artifact review.

This checker is deliberately historical and exact-head-only.  It validates the
review manifest and, when supplied, the expiring GitHub Actions artifact bytes.
It cannot award a gate, tracker credit, broad hardware compatibility, or future
runtime equivalence.
"""

from __future__ import print_function

import argparse
import hashlib
import io
import json
import os
import re
import stat
import subprocess
import sys
import tarfile
import zipfile
from pathlib import Path, PurePosixPath


REVIEW_DIRECTORY = Path("host-kernel/rocky/evidence")
REVIEW_GLOB = "hosted-runtime-review-*-v1.json"
REVIEW_SHA256 = "525b2a625ecf6a1ff9f1d8e11330dda231cf0d846c4fa7edf07715badb6a4b52"
SCHEMA_VERSION = 1
REVIEW_ID = "hosted-rocky-runtime-review-4acb611f-v1"
RUNTIME_HEAD_SHA = "4acb611f85600cb7258144a6e3e75c5588416aef"
RUNTIME_TREE_SHA = "59971603e9e9c4bb1bc1a28096709ed4b4b0afb9"
GITHUB_REPOSITORY = "phoenix-hacking/mckernel"
GITHUB_RUN_ID = 32093431704
GITHUB_RUN_ATTEMPT = 1
GITHUB_JOB_ID = 95580616390
GITHUB_WORKFLOW_ID = 330263359
ARTIFACT_ID = 9309472206
ARTIFACT_NAME = "hosted-rocky-boot-32093431704-1"
ARTIFACT_FILE_NAME = ARTIFACT_NAME + ".zip"
ARTIFACT_SIZE = 416712
ARTIFACT_SHA256 = "d352557c5f6843271e36712a0cd13aa7d4a8bc7bccb3ea1d377becf63e026106"
ARTIFACT_EXPIRES_AT = "2026-11-16T02:52:51Z"
ZIP_PREFIX = "_temp/mckernel-hosted-boot-32093431704-1/"
HEX_SHA1 = re.compile(r"^[0-9a-f]{40}$")
HEX_SHA256 = re.compile(r"^[0-9a-f]{64}$")
SHA256SUM = re.compile(r"^([0-9a-f]{64})  (\./[A-Za-z0-9][A-Za-z0-9_.-]*)$")
PRODUCT_SUM = re.compile(r"^([0-9a-f]{64})  (/tmp/mckernel-rocky-rust/.+)$")
PRIVATE_KEY = re.compile(
    br"-----BEGIN (?:(?:OPENSSH|RSA|DSA|EC) PRIVATE KEY|PRIVATE KEY|"
    br"ENCRYPTED PRIVATE KEY|PGP PRIVATE KEY BLOCK)-----"
)
LINUX_FATAL_SIGNATURE = re.compile(
    r"(?:BUG:|Oops:|general protection fault|Kernel panic|panic - not syncing|"
    r"WARNING: CPU:|Unable to handle kernel)",
    re.IGNORECASE,
)
MCKERNEL_FATAL_SIGNATURE = re.compile(
    r"(?:mcexec_v10: fatal|(?:^|\s)PANIC(?::|\s|$)|(?:^|\s)panic:|BUG:|"
    r"Oops:|general protection fault|unhandled page fault|assert(?:ion)? failed|"
    r"stack (?:smashing|corruption))",
    re.IGNORECASE,
)
EXPECTED_GATE_CLAIMS = {
    "RK-002": False,
    "RK-003": False,
    "RK-004": False,
    "RK-005": False,
    "RK-006": False,
    "RS-001": False,
}
EXPECTED_CLAIMS = {
    "broad_hardware_compatibility": False,
    "credit_eligible": False,
    "future_head_runtime_equivalence": False,
    "gate_claims": EXPECTED_GATE_CLAIMS,
    "general_runtime_reproducibility": False,
    "network_isolation_claimed": False,
    "production_readiness": False,
    "tracker_credit": False,
}
EXPECTED_CAVEATS = {
    "artifact_bytes_committed": False,
    "artifact_retention_is_durable": False,
    "embedded_progress_is_credit_authority": False,
    "ephemeral_guest_image_archived": False,
    "guest_image_signature_reviewed": False,
    "single_hosted_run_proves_hardware_breadth": False,
    "ssh_private_keys_archived": False,
}
EXPECTED_REMAINING_PREREQUISITES = [
    (
        "Durably archive the exact artifact ZIP before its GitHub Actions copy "
        "expires at 2026-11-16T02:52:51Z."
    ),
    (
        "Reproduce the runtime on additional independently reviewed hosts before "
        "making any broad hardware-compatibility or runtime-reproducibility claim."
    ),
    (
        "Capture a fresh exact-head runtime artifact for every future source tree; "
        "this review cannot transfer runtime identity to descendants."
    ),
    (
        "Review guest-image signature provenance and durably archive the exact "
        "2065760256-byte base image before claiming durable acquisition reproducibility."
    ),
    (
        "Any gate or tracker credit requires a separate authority update; this "
        "bounded artifact review cannot award it."
    ),
]
EXPECTED_ARCHIVE_FILE_RECORDS = [
    {"path": "host-environment.txt", "sha256": "892000d31021bd661ec084826e36c195bc3ba2398360d9dd29167da9889780c9", "size": 5440},
    {"path": "post-validation.txt", "sha256": "57e83a87e6028f968b56ed8d229800363b1889aa00a0be3c9fda481646143441", "size": 1088},
    {"path": "run.log", "sha256": "aa76a69a2e24c4273feb07793b318c3bb9d02c8978c681d8bae545ab1540c3ec", "size": 332215},
    {"path": "qemu/guest-cleanup.log", "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855", "size": 0},
    {"path": "qemu/guest-command.log", "sha256": "e33feab1ffc31181392ca7e4f6588b7f3ed54a8381d2a972aace19e66e5ce499", "size": 329524},
    {"path": "qemu/guest-evidence.tar", "sha256": "a4b2b5d7350cde6743ddaeab08cd63c01a278f70d3a3dcfb02437174646a750d", "size": 1361920},
    {"path": "qemu/guest-evidence.tar.sha256", "sha256": "f5a307b8e82e37f62d8e26801527836f549969d3500cfd4ffbca25ff41bc2865", "size": 85},
    {"path": "qemu/guest-evidence/SHA256SUMS", "sha256": "f6c4573bf395a815ac92909f1c233b43ee23f21e27f154c8f4dccac5c77f5e15", "size": 1606},
    {"path": "qemu/guest-evidence/linux-dmesg-delta.log", "sha256": "5f4b58497bcb6ee57c86f099995002d6c3ef781b13f73df84d650a85b4ac8300", "size": 3752},
    {"path": "qemu/guest-evidence/mckernel-final.kmsg", "sha256": "2781e606d48f59265f98a1f0e10aeb49c6501bdc3b837d226f417826d21a3f71", "size": 153331},
    {"path": "qemu/guest-evidence/mckernel-linked-text-ownership.json", "sha256": "a04fac7f2bac45aea62b174db355dd789e6b06add3398b3b2412361466d840a0", "size": 2049},
    {"path": "qemu/guest-evidence/mckernel-syscall-offload-composition.json", "sha256": "3b2c191a8bca6a7215974ff8d241d050730a9834ca4421e67faac0c5f97e5ef4", "size": 2575},
    {"path": "qemu/guest-evidence/mckernel-workload-delta.kmsg", "sha256": "6e4ad12dc0531cd39723d28b048bf2601b9ed9e409dd76717d63e5a3348a83dc", "size": 152217},
    {"path": "qemu/guest-evidence/runtime-environment.txt", "sha256": "9f953e216179d9000546e0e9769062522145167be76e97b025ca85eb8e8952d1", "size": 1486},
    {"path": "qemu/qemu-cpu-model.txt", "sha256": "e9dfa7da51bbca5ab3350e2ef938089e4efa6cb877c664698461c1ad16274a33", "size": 14},
    {"path": "qemu/qmp-status.jsonl", "sha256": "95d3083b8573f2316c9dc8123f25d86d8ac7b5912288fb8d2a5b82645735bddd", "size": 2196},
]
EXPECTED_ORDERED_MARKERS = [
    {"count": 1, "first_line": 3, "line": "QEMU guest LA57: absent"},
    {"count": 1, "first_line": 2306, "line": "Runtime provenance manifest: files=8 sha256=fb383946fdcbad7ea7467b5c07a56060eb32379fd00c82c9b4737a5d1eee2da2"},
    {"count": 1, "first_line": 2332, "line": "McKernel status: RUNNING"},
    {"count": 2, "first_line": 2333, "line": "IHK/McKernel started."},
    {"count": 2, "first_line": 2334, "line": "IHK/McKernel booted."},
    {"count": 1, "first_line": 2338, "line": "IHK remaining unassigned CPU reserves: none"},
    {"count": 1, "first_line": 2339, "line": "IHK remaining unassigned memory reserves: none"},
    {"count": 1, "first_line": 2340, "line": "McKernel assigned CPU evidence: 1"},
    {"count": 1, "first_line": 2341, "line": "McKernel assigned memory evidence: 536870912@0"},
    {"count": 1, "first_line": 2342, "line": "McKernel free-memory evidence: 533000192@0"},
    {"count": 1, "first_line": 2343, "line": "McKernel requested CPU assignment: verified 1"},
    {"count": 1, "first_line": 2344, "line": "McKernel requested memory assignment: verified 536870912@0"},
    {"count": 1, "first_line": 2351, "line": "mcexec-true: OK"},
    {"count": 1, "first_line": 2356, "line": "mcexec-hostname: OK"},
    {"count": 1, "first_line": 2361, "line": "mcexec-hostname-absolute: OK"},
    {"count": 1, "first_line": 2365, "line": "mckernel-rust-smoke: OK bytes=1048576 sum=133693440"},
    {"count": 1, "first_line": 2366, "line": "mcexec-rust-workload: OK"},
    {"count": 1, "first_line": 2377, "line": "syscall-offload owner=rust send+forward+wait markers: OK"},
    {"count": 1, "first_line": 2378, "line": "McKernel deterministic-workload kmsg delta: lines=1543 sha256=6e4ad12dc0531cd39723d28b048bf2601b9ed9e409dd76717d63e5a3348a83dc"},
    {"count": 1, "first_line": 2386, "line": "mcstat: OK"},
    {"count": 1, "first_line": 2388, "line": "McKernel post-workload status: RUNNING"},
    {"count": 1, "first_line": 2389, "line": "McKernel post-workload fatal scan: clean lines=1566 sha256=2781e606d48f59265f98a1f0e10aeb49c6501bdc3b837d226f417826d21a3f71"},
    {"count": 1, "first_line": 2393, "line": "mcstop+release: OK"},
    {"count": 1, "first_line": 2399, "line": "SELinux mode restored: enforcing"},
    {"count": 1, "first_line": 2406, "line": "IHK/McKernel modules after shutdown: none"},
    {"count": 1, "first_line": 2407, "line": "McKernel device nodes after shutdown: none"},
    {"count": 1, "first_line": 2408, "line": "guest-cleanup: OK"},
    {"count": 1, "first_line": 2409, "line": "Linux dmesg delta fatal scan: clean lines=54 sha256=5f4b58497bcb6ee57c86f099995002d6c3ef781b13f73df84d650a85b4ac8300"},
    {"count": 1, "first_line": 2410, "line": "===== BEGIN raw McKernel kmsg ====="},
    {"count": 1, "first_line": 3978, "line": "===== END raw McKernel kmsg ====="},
    {"count": 1, "first_line": 3979, "line": "===== BEGIN raw Linux dmesg delta ====="},
    {"count": 1, "first_line": 4035, "line": "===== END raw Linux dmesg delta ====="},
    {"count": 1, "first_line": 4036, "line": "Runtime raw evidence preserved: files=17 manifest_sha256=f6c4573bf395a815ac92909f1c233b43ee23f21e27f154c8f4dccac5c77f5e15"},
]
EXPECTED_INPUTS = (
    (
        ".github/workflows/rust-x86_64-validation.yml",
        "420d99a8895e26d603993a0bd3d6d7b197c97921",
        "6ca088aa0b1b5c48b1fc3830f556d4f5759db718fa43111a402aacdc2c7bb1ba",
        43497,
    ),
    (
        "VALIDATION_PROGRESS.MD",
        "9f7751ba9839dd8b91e38649388d7838cdd4a7c5",
        "c176bb63a417f014c3efc515eb3b9fffacf80f70d6397f379948b3e85887a3d2",
        21780,
    ),
    (
        "scripts/qemu-rocky-rust-validation.sh",
        "9eec7610e2f713ea22585e0739f4c2f156e99765",
        "b1b05d094be8742c1ae6e81bbcefc565800f43bdf2aa7e1f48986c68e6907931",
        6568,
    ),
    (
        "scripts/rocky-rust-validation.sh",
        "cfe2ee1035876d53e8f19394e7989a8de9786c62",
        "38bc29b04eb4f61605e4d2133865974e1a12f9e65ecab52193255404107df6d0",
        68485,
    ),
)
EXPECTED_INPUT_MODES = {
    ".github/workflows/rust-x86_64-validation.yml": "100644",
    "VALIDATION_PROGRESS.MD": "100644",
    "scripts/qemu-rocky-rust-validation.sh": "100755",
    "scripts/rocky-rust-validation.sh": "100755",
}
EXPECTED_ZIP_PATHS = tuple(
    ZIP_PREFIX + name
    for name in (
        "CHECKSUM",
        "host-environment.txt",
        "post-validation.txt",
        "qemu/debugcon.log",
        "qemu/guest-cleanup.log",
        "qemu/guest-command.log",
        "qemu/guest-evidence.tar",
        "qemu/guest-evidence.tar.sha256",
        "qemu/guest-evidence/SHA256SUMS",
        "qemu/guest-evidence/linux-dmesg-after.log",
        "qemu/guest-evidence/linux-dmesg-before.log",
        "qemu/guest-evidence/linux-dmesg-delta.log",
        "qemu/guest-evidence/linux-irq-affinity-before.tsv",
        "qemu/guest-evidence/mckernel-after-workload.kmsg",
        "qemu/guest-evidence/mckernel-before-workload.kmsg",
        "qemu/guest-evidence/mckernel-boot.kmsg",
        "qemu/guest-evidence/mckernel-final.kmsg",
        "qemu/guest-evidence/mckernel-linked-text-ownership.json",
        "qemu/guest-evidence/mckernel-symbol-source-attribution.json",
        "qemu/guest-evidence/mckernel-syscall-offload-composition.json",
        "qemu/guest-evidence/mckernel-workload-delta.kmsg",
        "qemu/guest-evidence/mckernel.img.map",
        "qemu/guest-evidence/runtime-artifacts.sha256",
        "qemu/guest-evidence/runtime-environment.txt",
        "qemu/guest-evidence/runtime-repositories.txt",
        "qemu/guest-evidence/runtime-rpms.txt",
        "qemu/qemu-cpu-model.txt",
        "qemu/qemu-started.pid",
        "qemu/qemu-startup.log",
        "qemu/qmp-status.jsonl",
        "qemu/serial.log",
        "run.log",
    )
) + ("mckernel/mckernel/VALIDATION_PROGRESS.MD",)
EXPECTED_TAR_FILES = (
    "SHA256SUMS",
    "linux-dmesg-after.log",
    "linux-dmesg-before.log",
    "linux-dmesg-delta.log",
    "linux-irq-affinity-before.tsv",
    "mckernel-after-workload.kmsg",
    "mckernel-before-workload.kmsg",
    "mckernel-boot.kmsg",
    "mckernel-final.kmsg",
    "mckernel-linked-text-ownership.json",
    "mckernel-symbol-source-attribution.json",
    "mckernel-syscall-offload-composition.json",
    "mckernel-workload-delta.kmsg",
    "mckernel.img.map",
    "runtime-artifacts.sha256",
    "runtime-environment.txt",
    "runtime-repositories.txt",
    "runtime-rpms.txt",
)
EXPECTED_CHECKSUM_NAMES = (
    "./linux-dmesg-after.log",
    "./linux-dmesg-before.log",
    "./linux-dmesg-delta.log",
    "./linux-irq-affinity-before.tsv",
    "./mckernel-after-workload.kmsg",
    "./mckernel-before-workload.kmsg",
    "./mckernel-boot.kmsg",
    "./mckernel-final.kmsg",
    "./mckernel.img.map",
    "./mckernel-linked-text-ownership.json",
    "./mckernel-symbol-source-attribution.json",
    "./mckernel-syscall-offload-composition.json",
    "./mckernel-workload-delta.kmsg",
    "./runtime-artifacts.sha256",
    "./runtime-environment.txt",
    "./runtime-repositories.txt",
    "./runtime-rpms.txt",
)
EXPECTED_PRODUCTS = {
    "ihk-smp-x86_64.ko": "4a38092d3e7799af1c4bbc8eab102ad33fb9bf7f6686748c15fce0c43d9be222",
    "ihk.ko": "aa6ff4753dd97b6c7a7af8b0474f0f1ef89d339d2fdee0f2daa72fb84c0858cc",
    "mcctrl.ko": "c7e7a51c4ff5c3b71fbff7a24b2fdb2e46c12e40bb8ed8856584978eccd8ba1c",
    "mcexec": "c4c9de7ed00e99da9cb2be6367d33dc609e1831cbf960c179329d1c7f4eb2400",
    "mcexec-rust-smoke": "5f5f1cbcfb0dc132dffb222a283aa88c51856303eb0dfb30e9f7385ab1745370",
    "mckernel.img": "af06d3a87530315204a027353f9d60c011b3ca0118280b1b4a2cafe70bd1fd89",
}
PRODUCT_BASENAMES = {
    "/tmp/mckernel-rocky-rust/kernel/mckernel.img": "mckernel.img",
    "/tmp/mckernel-rocky-rust/ihk/linux/core/ihk.ko": "ihk.ko",
    "/tmp/mckernel-rocky-rust/ihk/linux/driver/smp/ihk-smp-x86_64.ko": "ihk-smp-x86_64.ko",
    "/tmp/mckernel-rocky-rust/executer/kernel/mcctrl/mcctrl.ko": "mcctrl.ko",
    "/tmp/mckernel-rocky-rust/executer/user/mcexec": "mcexec",
    "/tmp/mckernel-rocky-rust/mcexec-rust-smoke": "mcexec-rust-smoke",
}


class HostedRuntimeReviewError(RuntimeError):
    """Raised when review bytes, repository state, or artifact bytes fail closed."""


def reject_duplicate_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise HostedRuntimeReviewError("duplicate JSON key: {!r}".format(key))
        result[key] = value
    return result


def canonical_json_bytes(value):
    try:
        text = json.dumps(
            value, allow_nan=False, ensure_ascii=True, separators=(",", ":"), sort_keys=True
        )
    except (TypeError, ValueError) as exc:
        raise HostedRuntimeReviewError("value is not canonical JSON: {}".format(exc))
    return (text + "\n").encode("ascii")


def read_json_bytes(data, label, canonical=False):
    try:
        value = json.loads(data.decode("ascii"), object_pairs_hook=reject_duplicate_pairs)
    except (UnicodeError, ValueError) as exc:
        raise HostedRuntimeReviewError("{} is not valid JSON: {}".format(label, exc))
    if not isinstance(value, dict):
        raise HostedRuntimeReviewError("{} must be a JSON object".format(label))
    if canonical and data != canonical_json_bytes(value):
        raise HostedRuntimeReviewError("{} is not canonical JSON".format(label))
    return value


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def exact_keys(value, expected, label):
    if type(value) is not dict or set(value) != set(expected):
        raise HostedRuntimeReviewError("{} has unexpected keys".format(label))
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
            same_value_and_type(left, right) for left, right in zip(actual, expected)
        )
    return actual == expected


def require_exact(actual, expected, label):
    if not same_value_and_type(actual, expected):
        raise HostedRuntimeReviewError("{} differs: {!r} != {!r}".format(label, actual, expected))


def require_type(value, expected_type, label):
    if type(value) is not expected_type:
        raise HostedRuntimeReviewError("{} has wrong type".format(label))
    return value


def require_positive_int(value, label):
    require_type(value, int, label)
    if value < 1:
        raise HostedRuntimeReviewError("{} is not positive".format(label))
    return value


def validate_sha(value, expression, label):
    if type(value) is not str or expression.fullmatch(value) is None:
        raise HostedRuntimeReviewError("{} is not a digest".format(label))


def safe_relative_path(value, label):
    if type(value) is not str:
        raise HostedRuntimeReviewError("{} is not text".format(label))
    path = PurePosixPath(value)
    if (
        not value
        or path.is_absolute()
        or "\\" in value
        or "\x00" in value
        or "//" in value
        or any(part in ("", ".", "..") for part in value.split("/"))
    ):
        raise HostedRuntimeReviewError("{} is unsafe: {!r}".format(label, value))
    return value


def regular_file(path, label, maximum=None):
    path = Path(path)
    try:
        info = path.lstat()
    except OSError as exc:
        raise HostedRuntimeReviewError("cannot inspect {}: {}".format(label, exc))
    if stat.S_ISLNK(info.st_mode) or not stat.S_ISREG(info.st_mode):
        raise HostedRuntimeReviewError("{} is not a non-symlink regular file".format(label))
    if maximum is not None and info.st_size > maximum:
        raise HostedRuntimeReviewError("{} exceeds size bound".format(label))
    return path


def contained_repository_file(repo, relative, label):
    safe_relative_path(relative, label)
    repo = Path(repo).resolve()
    candidate = repo / relative
    current = repo
    for part in PurePosixPath(relative).parts:
        current = current / part
        try:
            info = current.lstat()
        except OSError as exc:
            raise HostedRuntimeReviewError("cannot inspect {}: {}".format(label, exc))
        if stat.S_ISLNK(info.st_mode):
            raise HostedRuntimeReviewError("{} traverses a symlink".format(label))
    if candidate.resolve().parent != (repo / relative).parent.resolve():
        raise HostedRuntimeReviewError("{} escapes repository".format(label))
    return regular_file(candidate, label, maximum=4 * 1024 * 1024)


def contained_repository_directory(repo, relative, label):
    safe_relative_path(relative, label)
    current = Path(repo).resolve()
    for part in PurePosixPath(relative).parts:
        current = current / part
        try:
            info = current.lstat()
        except OSError as exc:
            raise HostedRuntimeReviewError("cannot inspect {}: {}".format(label, exc))
        if stat.S_ISLNK(info.st_mode):
            raise HostedRuntimeReviewError("{} traverses a symlink".format(label))
        if not stat.S_ISDIR(info.st_mode):
            raise HostedRuntimeReviewError("{} is not a directory".format(label))
    return current


def discover_review(repo):
    repo = Path(repo).resolve()
    directory = contained_repository_directory(
        repo, REVIEW_DIRECTORY.as_posix(), "review directory"
    )
    candidates = sorted(directory.glob(REVIEW_GLOB))
    if len(candidates) != 1:
        raise HostedRuntimeReviewError("expected exactly one hosted runtime review manifest")
    relative = candidates[0].relative_to(repo).as_posix()
    return contained_repository_file(repo, relative, "review manifest")


def load_review(path):
    path = regular_file(path, "review manifest", maximum=128 * 1024)
    data = path.read_bytes()
    require_exact(sha256_bytes(data), REVIEW_SHA256, "review manifest digest")
    return read_json_bytes(data, "review manifest", canonical=True)


def _row_schema(rows, keys, label):
    require_type(rows, list, label)
    for index, row in enumerate(rows):
        exact_keys(row, keys, "{} {}".format(label, index))


def validate_review_object(review):
    exact_keys(
        review,
        {
            "caveats", "claims", "remaining_prerequisites", "review_id", "review_kind",
            "runtime_candidate", "schema_version", "source_artifact", "verified_facts",
        },
        "review",
    )
    require_exact(review["schema_version"], SCHEMA_VERSION, "schema version")
    require_exact(review["review_id"], REVIEW_ID, "review id")
    require_exact(
        review["review_kind"],
        "exact-head-single-hosted-kvm-runtime-artifact-bounded-pass",
        "review kind",
    )
    require_exact(review["claims"], EXPECTED_CLAIMS, "bounded claims")
    require_exact(review["caveats"], EXPECTED_CAVEATS, "review caveats")
    require_exact(
        review["remaining_prerequisites"],
        EXPECTED_REMAINING_PREREQUISITES,
        "remaining prerequisites",
    )

    candidate = exact_keys(
        review["runtime_candidate"],
        {"committed_inputs", "current_repository_policy", "head_sha", "tree_sha"},
        "runtime candidate",
    )
    require_exact(candidate["head_sha"], RUNTIME_HEAD_SHA, "runtime head")
    require_exact(candidate["tree_sha"], RUNTIME_TREE_SHA, "runtime tree")
    require_exact(
        candidate["current_repository_policy"],
        {"bound_input_count": 4, "relationship": "descendant-or-equal", "runtime_equivalence_claimed": False},
        "current repository policy",
    )
    _row_schema(candidate["committed_inputs"], {"git_blob_sha1", "path", "sha256", "size"}, "committed inputs")
    expected_rows = [
        {"path": path, "git_blob_sha1": blob, "sha256": digest, "size": size}
        for path, blob, digest, size in EXPECTED_INPUTS
    ]
    require_exact(candidate["committed_inputs"], expected_rows, "committed inputs")

    source = exact_keys(
        review["source_artifact"],
        {"artifact", "durable_archive", "expires_at", "github", "retention_days"},
        "source artifact",
    )
    require_exact(source["durable_archive"], False, "durable archive claim")
    require_exact(source["expires_at"], ARTIFACT_EXPIRES_AT, "artifact expiration")
    require_exact(source["retention_days"], 90, "artifact retention")
    require_exact(
        source["artifact"],
        {
            "archive_file_name": ARTIFACT_FILE_NAME,
            "created_at": "2026-08-18T03:11:24Z",
            "id": ARTIFACT_ID,
            "name": ARTIFACT_NAME,
            "sha256": ARTIFACT_SHA256,
            "size": ARTIFACT_SIZE,
        },
        "artifact identity",
    )
    require_exact(
        source["github"],
        {
            "event": "pull_request",
            "head_branch": "codex/rocky-rust-validation",
            "job_conclusion": "success",
            "job_id": GITHUB_JOB_ID,
            "repository": GITHUB_REPOSITORY,
            "run_attempt": GITHUB_RUN_ATTEMPT,
            "run_conclusion": "success",
            "run_id": GITHUB_RUN_ID,
            "run_number": 105,
            "runtime_head_sha": RUNTIME_HEAD_SHA,
            "workflow_id": GITHUB_WORKFLOW_ID,
        },
        "GitHub identity",
    )

    facts = exact_keys(
        review["verified_facts"],
        {
            "archive_file_records", "build_products", "cleanup", "embedded_progress",
            "fatal_scans", "guest_image", "marker_review", "qemu", "runtime",
            "tar_closure", "zip_closure",
        },
        "verified facts",
    )
    _row_schema(facts["archive_file_records"], {"path", "sha256", "size"}, "archive records")
    require_exact(
        facts["archive_file_records"],
        EXPECTED_ARCHIVE_FILE_RECORDS,
        "archive file records",
    )
    archive_paths = []
    for row in facts["archive_file_records"]:
        archive_paths.append(safe_relative_path(row["path"], "selected archive path"))
        validate_sha(row["sha256"], HEX_SHA256, "selected archive digest")
        require_type(row["size"], int, "selected archive size")
        if row["size"] < 0:
            raise HostedRuntimeReviewError("selected archive size is negative")
    if len(archive_paths) != len(set(archive_paths)):
        raise HostedRuntimeReviewError("selected archive paths are duplicated")
    require_exact(facts["build_products"], EXPECTED_PRODUCTS, "build products")
    require_exact(
        facts["cleanup"],
        {
            "backing_image_unchanged": True,
            "guest_cleanup_log_empty": True,
            "guest_overlay_removed": True,
            "host_modules_after_validation": "none",
            "hosted_post_validation": "OK",
            "qemu_exit": "OK",
            "ssh_private_key_material_present": False,
        },
        "cleanup facts",
    )
    require_exact(
        facts["embedded_progress"],
        {
            "credit_authority": False,
            "git_blob_sha1": EXPECTED_INPUTS[1][1],
            "path": "mckernel/mckernel/VALIDATION_PROGRESS.MD",
            "sha256": EXPECTED_INPUTS[1][2],
            "size": EXPECTED_INPUTS[1][3],
        },
        "embedded progress",
    )
    fatal = exact_keys(facts["fatal_scans"], {"linux_dmesg_delta", "mckernel_final"}, "fatal scans")
    for name in ("linux_dmesg_delta", "mckernel_final"):
        exact_keys(fatal[name], {"fatal_signature_count", "line_count", "prefix_chain_verified", "sha256"}, name)
        require_exact(fatal[name]["fatal_signature_count"], 0, name + " fatal count")
        require_exact(fatal[name]["prefix_chain_verified"], True, name + " prefix chain")
        require_positive_int(fatal[name]["line_count"], name + " line count")
        validate_sha(fatal[name]["sha256"], HEX_SHA256, name + " digest")
    require_exact(
        facts["guest_image"],
        {
            "archive_included": False,
            "bytes": 2065760256,
            "name": "Rocky-8-GenericCloud-Base-8.10-20240528.0.x86_64.qcow2",
            "sha256": "e56066c58606191e96184de9a9183a3af33c59bcbd8740d8b10ca054a7a89c14",
            "signature_reviewed": False,
            "url": "https://download.rockylinux.org/pub/rocky/8.10/images/x86_64/Rocky-8-GenericCloud-Base-8.10-20240528.0.x86_64.qcow2",
        },
        "guest image",
    )
    markers = exact_keys(
        facts["marker_review"],
        {"guest_command_line_count", "ordered_exact_lines", "trace_counts", "trace_group_order", "workload_delta_line_count"},
        "marker review",
    )
    require_positive_int(markers["guest_command_line_count"], "guest command line count")
    require_positive_int(markers["workload_delta_line_count"], "workload delta line count")
    _row_schema(markers["ordered_exact_lines"], {"count", "first_line", "line"}, "ordered markers")
    require_exact(
        markers["ordered_exact_lines"],
        EXPECTED_ORDERED_MARKERS,
        "ordered exact markers",
    )
    for row in markers["ordered_exact_lines"]:
        require_positive_int(row["count"], "marker count")
        require_positive_int(row["first_line"], "marker first line")
        require_type(row["line"], str, "marker line")
    trace_counts = exact_keys(
        markers["trace_counts"],
        {"enter_user", "generic_forwarding_owner_rust", "offload_return", "offload_wait_owner_rust", "prepared", "schedule_process_queued", "send_syscall", "send_syscall_owner_rust"},
        "trace count keys",
    )
    for key, value in trace_counts.items():
        require_positive_int(value, "trace count " + key)
    require_exact(markers["trace_group_order"], ["generic_forwarding_owner_rust", "send_syscall_owner_rust", "offload_wait_owner_rust", "offload_return"], "trace group order")
    require_exact(
        facts["qemu"],
        {"cpu_count": 4, "cpu_model": "host,la57=off", "guest_la57": "absent", "qmp_phase_order": ["start", "preflight"], "qmp_record_count": 8, "qmp_status": "running", "qmp_version": "8.2.2", "serial_evidence_bytes": 64204},
        "QEMU facts",
    )
    require_exact(
        facts["runtime"],
        {"architecture": "x86_64", "ihk_commit": "3114d9e7101ad52030eb3effa849a5c108972a1f", "kernel_release": "4.18.0-553.el8_10.x86_64", "llvm_version": "22.1.0", "os_id": "rocky", "os_version": "8.10", "rust_executable_text_bytes": 614183, "rust_executable_text_percent": "78.354960", "rustc_commit": "c043085801b7a884054add21a94882216df5971c", "rustc_version": "rustc 1.95.0-nightly (c04308580 2026-02-18)", "source_commit": RUNTIME_HEAD_SHA, "syscall_offload_composition": "PASS", "total_executable_text_bytes": 783847},
        "runtime facts",
    )
    require_exact(
        facts["zip_closure"],
        {"compressed_payload_size": 408806, "compression_methods": [8], "crc_verified": True, "duplicate_paths": False, "entry_count": 33, "entry_index_sha256": "dfc1c345036fed540ec9d3b13ce0ccdd1a8ce0e643be6c3740f947c0ba6d8928", "external_attributes": [2174746656, 2175008800], "path_index_sha256": "3ed3a74bac662664f59ff357ec42e784c3ac7f12391b328ec28031973dff3f43", "safe_regular_files_only": True, "uncompressed_size": 3461447},
        "ZIP closure",
    )
    require_exact(
        facts["tar_closure"],
        {"archive_sha256": "a4b2b5d7350cde6743ddaeab08cd63c01a278f70d3a3dcfb02437174646a750d", "archive_size": 1361920, "checksum_entry_count": 17, "checksum_manifest_sha256": "f6c4573bf395a815ac92909f1c233b43ee23f21e27f154c8f4dccac5c77f5e15", "directory_count": 1, "duplicate_paths": False, "entry_index_sha256": "49058dc6ebd80dbb61de8b7e231ffc04cb3a5182b9e372e0cdafea3090768990", "exploded_zip_bytes_equal": True, "file_count": 18, "member_count": 19, "path_index_sha256": "4e40fe40024b7dfcdf950e16ec2d811dd5990262900c62df9241a57fc99a613b", "portable_digest_verified": True, "safe_regular_files_and_root_directory_only": True, "uncompressed_file_bytes": 1336611},
        "tar closure",
    )
    return review


def run_git(repo, arguments, label):
    result = subprocess.run(
        ["git", "-C", str(repo)] + list(arguments),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if result.returncode:
        raise HostedRuntimeReviewError("{} failed: {}".format(label, result.stderr.decode("utf-8", "replace").strip()))
    return result.stdout


def git_tree_record(repo, commit, relative, label):
    output = run_git(repo, ["ls-tree", commit, "--", relative], label).decode("ascii").strip()
    rows = output.splitlines()
    if len(rows) != 1:
        raise HostedRuntimeReviewError("{} is absent or ambiguous".format(label))
    match = re.fullmatch(r"(100644|100755) blob ([0-9a-f]{40})\t(.+)", rows[0])
    if match is None or match.group(3) != relative:
        raise HostedRuntimeReviewError("{} is not a regular Git blob".format(label))
    return match.group(1), match.group(2)


def git_blob_bytes(repo, blob, label):
    validate_sha(blob, HEX_SHA1, label)
    return run_git(repo, ["cat-file", "blob", blob], label)


def validate_repository(repo, review):
    repo = Path(repo).resolve()
    current_head = run_git(repo, ["rev-parse", "HEAD"], "current HEAD").decode("ascii").strip()
    runtime_tree = run_git(repo, ["rev-parse", RUNTIME_HEAD_SHA + "^{tree}"], "runtime tree").decode("ascii").strip()
    require_exact(runtime_tree, RUNTIME_TREE_SHA, "runtime tree")
    ancestry = subprocess.run(
        ["git", "-C", str(repo), "merge-base", "--is-ancestor", RUNTIME_HEAD_SHA, current_head],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    if ancestry.returncode != 0:
        raise HostedRuntimeReviewError("current HEAD is not descendant-or-equal to runtime head")
    rows = review["runtime_candidate"]["committed_inputs"]
    for row in rows:
        path = row["path"]
        runtime_mode, runtime_blob = git_tree_record(repo, RUNTIME_HEAD_SHA, path, "runtime input " + path)
        require_exact(runtime_mode, EXPECTED_INPUT_MODES[path], "runtime input mode " + path)
        require_exact(runtime_blob, row["git_blob_sha1"], "runtime input blob " + path)
        data = git_blob_bytes(repo, runtime_blob, "runtime input " + path)
        require_exact(len(data), row["size"], "runtime input size " + path)
        require_exact(sha256_bytes(data), row["sha256"], "runtime input digest " + path)
        current_mode, current_blob = git_tree_record(repo, current_head, path, "current input " + path)
        require_exact(current_mode, runtime_mode, "current input mode " + path)
        require_exact(current_blob, runtime_blob, "current input blob " + path)
        index = run_git(repo, ["ls-files", "-s", "--", path], "index input " + path).decode("ascii").strip()
        require_exact(index, "{} {} 0\t{}".format(runtime_mode, runtime_blob, path), "index input " + path)
        worktree = contained_repository_file(repo, path, "worktree input " + path).read_bytes()
        require_exact(worktree, data, "worktree input bytes " + path)
    return current_head


def zip_entry_records(archive):
    records = []
    names = []
    for info in archive.infolist():
        name = safe_relative_path(info.filename, "ZIP entry")
        if name.endswith("/"):
            raise HostedRuntimeReviewError("ZIP directories are forbidden")
        names.append(name)
        mode = info.external_attr >> 16
        if not stat.S_ISREG(mode):
            raise HostedRuntimeReviewError("ZIP entry is not regular: " + name)
        if info.flag_bits & 0x1:
            raise HostedRuntimeReviewError("encrypted ZIP entries are forbidden")
        if info.extra:
            raise HostedRuntimeReviewError("ZIP entry extra fields are forbidden")
        data = archive.read(info)
        if len(data) != info.file_size:
            raise HostedRuntimeReviewError("ZIP entry size mismatch: " + name)
        records.append({"compressed_size": info.compress_size, "compression_method": info.compress_type, "crc32": format(info.CRC, "08x"), "external_attributes": info.external_attr, "path": name, "sha256": sha256_bytes(data), "size": info.file_size})
    if len(names) != len(set(names)):
        raise HostedRuntimeReviewError("ZIP contains duplicate paths")
    return sorted(records, key=lambda row: row["path"])


def tar_entry_records(data):
    try:
        archive = tarfile.open(fileobj=io.BytesIO(data), mode="r:")
    except tarfile.TarError as exc:
        raise HostedRuntimeReviewError("guest evidence tar is unreadable: {}".format(exc))
    records = []
    files = {}
    names = []
    with archive:
        for member in archive.getmembers():
            name = member.name
            if name == ".":
                if member.type != tarfile.DIRTYPE:
                    raise HostedRuntimeReviewError("tar root is not a directory")
                normalized = "."
                payload = b""
                type_name = "5"
            elif name.startswith("./"):
                normalized = safe_relative_path(name[2:], "tar entry")
                if member.type not in (tarfile.REGTYPE, tarfile.AREGTYPE) or not member.isfile():
                    raise HostedRuntimeReviewError("tar entry is not regular: " + name)
                stream = archive.extractfile(member)
                if stream is None:
                    raise HostedRuntimeReviewError("tar entry has no payload: " + name)
                payload = stream.read()
                require_exact(len(payload), member.size, "tar entry size " + name)
                files[normalized] = payload
                type_name = "0"
            else:
                raise HostedRuntimeReviewError("tar entry path is unsafe: {!r}".format(name))
            if member.linkname:
                raise HostedRuntimeReviewError("tar links are forbidden")
            names.append(name)
            records.append({"gid": member.gid, "linkname": member.linkname, "mode": member.mode, "mtime": member.mtime, "name": name, "sha256": sha256_bytes(payload), "size": member.size, "type": type_name, "uid": member.uid})
    if len(names) != len(set(names)) or len(files) != len(set(files)):
        raise HostedRuntimeReviewError("tar contains duplicate paths")
    return sorted(records, key=lambda row: row["name"]), files


def parse_sha256sums(data):
    try:
        text = data.decode("ascii")
    except UnicodeError as exc:
        raise HostedRuntimeReviewError("SHA256SUMS is not ASCII: {}".format(exc))
    if not text.endswith("\n"):
        raise HostedRuntimeReviewError("SHA256SUMS lacks final newline")
    result = {}
    for line in text.splitlines():
        match = SHA256SUM.fullmatch(line)
        if match is None:
            raise HostedRuntimeReviewError("SHA256SUMS has malformed row")
        digest, name = match.groups()
        if name in result:
            raise HostedRuntimeReviewError("SHA256SUMS has duplicate path")
        result[name] = digest
    require_exact(tuple(result), EXPECTED_CHECKSUM_NAMES, "SHA256SUMS paths and order")
    return result


def _text(data, label):
    try:
        return data.decode("utf-8")
    except UnicodeError as exc:
        raise HostedRuntimeReviewError("{} is not UTF-8: {}".format(label, exc))


def verify_markers(command_data, delta_data, markers):
    command_lines = _text(command_data, "guest command log").splitlines()
    require_exact(len(command_lines), markers["guest_command_line_count"], "guest command line count")
    previous = -1
    for row in markers["ordered_exact_lines"]:
        positions = [index for index, line in enumerate(command_lines) if line == row["line"]]
        require_exact(len(positions), row["count"], "marker count " + row["line"])
        require_exact(positions[0] + 1, row["first_line"], "marker first line " + row["line"])
        if positions[0] <= previous:
            raise HostedRuntimeReviewError("reviewed markers are out of order")
        previous = positions[0]

    lines = _text(delta_data, "workload delta").splitlines()
    require_exact(len(lines), markers["workload_delta_line_count"], "workload delta line count")
    patterns = {
        "prepared": re.compile(r"mcexec_v10: prepared pid="),
        "schedule_process_queued": re.compile(r"mcexec_v10: schedule_process queued pid="),
        "enter_user": re.compile(r"mcexec_v10: enter_user cpu="),
        "generic_forwarding_owner_rust": re.compile(r"mcexec_v10: generic_forwarding owner=rust cpu="),
        "send_syscall": re.compile(r"mcexec_v10: send_syscall "),
        "send_syscall_owner_rust": re.compile(r"mcexec_v10: send_syscall owner=rust cpu="),
        "offload_wait_owner_rust": re.compile(r"mcexec_v10: offload_wait owner=rust cpu="),
        "offload_return": re.compile(r"mcexec_v10: offload_return cpu="),
    }
    for key, pattern in patterns.items():
        require_exact(sum(pattern.search(line) is not None for line in lines), markers["trace_counts"][key], "trace count " + key)

    group_patterns = [
        ("generic_forwarding_owner_rust", re.compile(r"generic_forwarding owner=rust .* pid=(\d+) nr=(\d+)$")),
        ("send_syscall_owner_rust", re.compile(r"send_syscall owner=rust .* pid=(\d+) .* nr=(\d+) ")),
        ("offload_wait_owner_rust", re.compile(r"offload_wait owner=rust .* pid=(\d+) .* nr=(\d+)$")),
        ("offload_return", re.compile(r"offload_return .* pid=(\d+) .* nr=(\d+) ")),
    ]
    events = []
    for line in lines:
        for key, pattern in group_patterns:
            match = pattern.search(line)
            if match is not None:
                events.append((key, match.group(1), match.group(2)))
                break
    require_exact(len(events), 1024, "offload lifecycle event count")
    for offset in range(0, len(events), 4):
        group = events[offset:offset + 4]
        require_exact([event[0] for event in group], markers["trace_group_order"], "offload lifecycle order")
        if len({(event[1], event[2]) for event in group}) != 1:
            raise HostedRuntimeReviewError("offload lifecycle pid/nr mismatch")


def verify_qmp(data, qemu):
    lines = _text(data, "QMP log").splitlines()
    require_exact(len(lines), qemu["qmp_record_count"], "QMP record count")
    records = []
    for index, line in enumerate(lines):
        try:
            record = json.loads(line, object_pairs_hook=reject_duplicate_pairs)
        except ValueError as exc:
            raise HostedRuntimeReviewError("QMP row is invalid: {}".format(exc))
        require_type(record, dict, "QMP row")
        records.append(record)
    require_exact([records[0]["label"], records[4]["label"]], qemu["qmp_phase_order"], "QMP phase order")
    for offset in (0, 4):
        label = qemu["qmp_phase_order"][offset // 4]
        require_exact(records[offset]["label"], label, "QMP greeting label")
        version = records[offset]["greeting"]["QMP"]["version"]["qemu"]
        require_exact(version, {"major": 8, "micro": 2, "minor": 2}, "QMP version")
        require_exact(records[offset + 1]["command"], "qmp_capabilities", "QMP capabilities command")
        status = records[offset + 2]
        require_exact(status["command"], "query-status", "QMP status command")
        require_exact(status["response"]["return"], {"running": True, "singlestep": False, "status": "running"}, "QMP running status")
        cpus = records[offset + 3]
        require_exact(cpus["command"], "query-cpus-fast", "QMP CPU command")
        rows = cpus["response"]["return"]
        require_exact([row["cpu-index"] for row in rows], [0, 1, 2, 3], "QMP CPU indexes")
        require_exact([row["target"] for row in rows], ["x86_64"] * 4, "QMP CPU targets")


def reject_private_key_material(files):
    for name, data in files.items():
        lowered = name.lower()
        if any(
            token in lowered
            for token in ("id_rsa", "id_ed25519", "private_key", ".pem")
        ) or PRIVATE_KEY.search(data):
            raise HostedRuntimeReviewError(
                "SSH/private-key material is forbidden: " + name
            )


def verify_fatal_scan(payload, row, pattern, label):
    text = _text(payload, label)
    require_exact(len(text.splitlines()), row["line_count"], label + " line count")
    require_exact(sha256_bytes(payload), row["sha256"], label + " digest")
    require_exact(
        len(pattern.findall(text)),
        row["fatal_signature_count"],
        label + " fatal scan",
    )


def verify_artifact(artifact_path, review):
    artifact_path = regular_file(artifact_path, "artifact ZIP", maximum=8 * 1024 * 1024)
    artifact_bytes = artifact_path.read_bytes()
    require_exact(len(artifact_bytes), ARTIFACT_SIZE, "artifact size")
    require_exact(sha256_bytes(artifact_bytes), ARTIFACT_SHA256, "artifact digest")
    try:
        archive = zipfile.ZipFile(str(artifact_path), "r")
    except (OSError, zipfile.BadZipFile) as exc:
        raise HostedRuntimeReviewError("artifact is not a readable ZIP: {}".format(exc))
    with archive:
        if archive.comment:
            raise HostedRuntimeReviewError("ZIP comments are forbidden")
        records = zip_entry_records(archive)
        paths = tuple(row["path"] for row in records)
        require_exact(paths, tuple(sorted(EXPECTED_ZIP_PATHS)), "ZIP path closure")
        closure = review["verified_facts"]["zip_closure"]
        require_exact(len(records), closure["entry_count"], "ZIP entry count")
        require_exact(sum(row["compressed_size"] for row in records), closure["compressed_payload_size"], "ZIP compressed payload")
        require_exact(sum(row["size"] for row in records), closure["uncompressed_size"], "ZIP uncompressed size")
        require_exact(sorted(set(row["compression_method"] for row in records)), closure["compression_methods"], "ZIP compression methods")
        require_exact(sorted(set(row["external_attributes"] for row in records)), closure["external_attributes"], "ZIP external attributes")
        require_exact(sha256_bytes(canonical_json_bytes(records)), closure["entry_index_sha256"], "ZIP entry index")
        require_exact(sha256_bytes(canonical_json_bytes(sorted(paths))), closure["path_index_sha256"], "ZIP path index")
        files = {name: archive.read(name) for name in paths}

    selected = {row["path"]: row for row in review["verified_facts"]["archive_file_records"]}
    require_exact(len(selected), len(review["verified_facts"]["archive_file_records"]), "selected archive paths")
    for relative, row in selected.items():
        path = ZIP_PREFIX + relative
        if path not in files:
            raise HostedRuntimeReviewError("selected archive path is absent: " + relative)
        require_exact(len(files[path]), row["size"], "selected file size " + relative)
        require_exact(sha256_bytes(files[path]), row["sha256"], "selected file digest " + relative)

    tar_data = files[ZIP_PREFIX + "qemu/guest-evidence.tar"]
    tar_closure = review["verified_facts"]["tar_closure"]
    require_exact(len(tar_data), tar_closure["archive_size"], "tar size")
    require_exact(sha256_bytes(tar_data), tar_closure["archive_sha256"], "tar digest")
    portable = files[ZIP_PREFIX + "qemu/guest-evidence.tar.sha256"]
    require_exact(portable, (tar_closure["archive_sha256"] + "  guest-evidence.tar\n").encode("ascii"), "portable tar digest")
    tar_records, tar_files = tar_entry_records(tar_data)
    require_exact(tuple(sorted(tar_files)), EXPECTED_TAR_FILES, "tar file closure")
    require_exact(len(tar_records), tar_closure["member_count"], "tar member count")
    require_exact(len(tar_files), tar_closure["file_count"], "tar file count")
    require_exact(sum(row["size"] for row in tar_records if row["type"] == "0"), tar_closure["uncompressed_file_bytes"], "tar file bytes")
    require_exact(sha256_bytes(canonical_json_bytes(tar_records)), tar_closure["entry_index_sha256"], "tar entry index")
    require_exact(sha256_bytes(canonical_json_bytes(sorted(row["name"] for row in tar_records))), tar_closure["path_index_sha256"], "tar path index")
    sums_data = tar_files["SHA256SUMS"]
    require_exact(sha256_bytes(sums_data), tar_closure["checksum_manifest_sha256"], "SHA256SUMS digest")
    sums = parse_sha256sums(sums_data)
    require_exact(len(sums), tar_closure["checksum_entry_count"], "checksum count")
    for name, digest in sums.items():
        normalized = name[2:]
        require_exact(sha256_bytes(tar_files[normalized]), digest, "checksum " + name)
    for name, data in tar_files.items():
        exploded = ZIP_PREFIX + "qemu/guest-evidence/" + name
        require_exact(files[exploded], data, "exploded tar equivalence " + name)

    reject_private_key_material(files)

    post = _text(files[ZIP_PREFIX + "post-validation.txt"], "post-validation")
    required_post = (
        "run-id={}\n".format(GITHUB_RUN_ID),
        "run-attempt={}\n".format(GITHUB_RUN_ATTEMPT),
        "validation-head={}\n".format(RUNTIME_HEAD_SHA),
        "backing-image: unchanged\n",
        "host IHK/McKernel modules after validation: none\n",
        "guest-overlay: removed\n",
        "qemu-cpu-policy: host,la57=off\n",
        "serial-evidence: bytes=64204\n",
        "guest evidence archive digest: verified\n",
        "qemu-exit: OK\n",
        "hosted-post-validation: OK\n",
    )
    for marker in required_post:
        require_exact(post.count(marker), 1, "post-validation marker " + marker.strip())
    require_exact(files[ZIP_PREFIX + "qemu/guest-cleanup.log"], b"", "guest cleanup log")
    require_exact(files[ZIP_PREFIX + "qemu/qemu-cpu-model.txt"], b"host,la57=off\n", "QEMU CPU policy")
    require_exact(len(files[ZIP_PREFIX + "qemu/serial.log"]), 64204, "serial evidence bytes")
    verify_qmp(files[ZIP_PREFIX + "qemu/qmp-status.jsonl"], review["verified_facts"]["qemu"])

    environment = _text(tar_files["runtime-environment.txt"], "runtime environment")
    expected_environment = (
        "source_commit=" + RUNTIME_HEAD_SHA,
        "os_id=rocky", "os_version=8.10", "arch=x86_64",
        "4.18.0-553.el8_10.x86_64", "rustc 1.95.0-nightly (c04308580 2026-02-18)",
        "commit-hash: c043085801b7a884054add21a94882216df5971c", "LLVM version: 22.1.0",
        "3114d9e7101ad52030eb3effa849a5c108972a1f ihk",
    )
    for marker in expected_environment:
        if marker not in environment:
            raise HostedRuntimeReviewError("runtime environment marker absent: " + marker)

    products = {}
    product_text = _text(tar_files["runtime-artifacts.sha256"], "runtime product checksums")
    if not product_text.endswith("\n"):
        raise HostedRuntimeReviewError("runtime product checksums lack final newline")
    for line in product_text.splitlines():
        match = PRODUCT_SUM.fullmatch(line)
        if match is None or match.group(2) not in PRODUCT_BASENAMES:
            raise HostedRuntimeReviewError("runtime product checksum row is malformed")
        name = PRODUCT_BASENAMES[match.group(2)]
        if name in products:
            raise HostedRuntimeReviewError("runtime product checksum is duplicated")
        products[name] = match.group(1)
    require_exact(products, EXPECTED_PRODUCTS, "runtime products")

    ownership = read_json_bytes(tar_files["mckernel-linked-text-ownership.json"], "ownership")
    exact_keys(ownership, {"architecture", "definition", "executable_sections", "inputs", "metric_scope", "non_rust_or_padding_executable_text_bytes", "rust_executable_text_bytes", "rust_executable_text_percent", "rust_input_contribution_count", "schema", "source_commit", "total_executable_text_bytes"}, "ownership")
    require_exact(ownership["source_commit"], RUNTIME_HEAD_SHA, "ownership source")
    require_exact(ownership["architecture"], "x86_64", "ownership architecture")
    require_exact(ownership["rust_executable_text_bytes"], 614183, "Rust executable bytes")
    require_exact(ownership["total_executable_text_bytes"], 783847, "total executable bytes")
    require_exact(ownership["rust_executable_text_percent"], "78.354960", "Rust executable percent")
    require_exact(ownership["inputs"]["image"]["sha256"], EXPECTED_PRODUCTS["mckernel.img"], "ownership image")

    composition = read_json_bytes(tar_files["mckernel-syscall-offload-composition.json"], "composition")
    exact_keys(composition, {"artifacts", "contract", "result", "schema", "source_commit", "symbol_evidence"}, "composition")
    require_exact(composition["source_commit"], RUNTIME_HEAD_SHA, "composition source")
    require_exact(composition["result"], "PASS", "composition result")
    require_exact(composition["artifacts"]["image"]["sha256"], EXPECTED_PRODUCTS["mckernel.img"], "composition image")

    before = tar_files["mckernel-before-workload.kmsg"]
    after = tar_files["mckernel-after-workload.kmsg"]
    final = tar_files["mckernel-final.kmsg"]
    delta = tar_files["mckernel-workload-delta.kmsg"]
    require_exact(after.startswith(before), True, "McKernel before/after prefix chain")
    require_exact(final.startswith(after), True, "McKernel after/final prefix chain")
    require_exact(after[len(before):], delta, "McKernel workload delta")
    linux_before = tar_files["linux-dmesg-before.log"]
    linux_after = tar_files["linux-dmesg-after.log"]
    linux_delta = tar_files["linux-dmesg-delta.log"]
    require_exact(linux_after.startswith(linux_before), True, "Linux before/after prefix chain")
    require_exact(linux_after[len(linux_before):], linux_delta, "Linux dmesg delta")
    fatal = review["verified_facts"]["fatal_scans"]
    verify_fatal_scan(
        final,
        fatal["mckernel_final"],
        MCKERNEL_FATAL_SIGNATURE,
        "mckernel_final",
    )
    verify_fatal_scan(
        linux_delta,
        fatal["linux_dmesg_delta"],
        LINUX_FATAL_SIGNATURE,
        "linux_dmesg_delta",
    )
    verify_markers(files[ZIP_PREFIX + "qemu/guest-command.log"], delta, review["verified_facts"]["marker_review"])
    return {"artifact_sha256": ARTIFACT_SHA256, "entry_count": len(records), "tar_member_count": len(tar_records)}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=".")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--verify-artifact", metavar="ZIP")
    args = parser.parse_args(argv)
    if not args.check and not args.verify_artifact:
        parser.error("at least one of --check or --verify-artifact is required")
    repo = Path(args.repo).resolve()
    review = validate_review_object(load_review(discover_review(repo)))
    current_head = validate_repository(repo, review)
    if args.verify_artifact:
        verify_artifact(args.verify_artifact, review)
    print("hosted runtime review: bounded PASS")
    print("runtime head: {}".format(RUNTIME_HEAD_SHA))
    print("current head: {}".format(current_head))
    print("gate/tracker/broad-runtime credit: false")
    print("artifact durable: false; expires {}".format(ARTIFACT_EXPIRES_AT))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except HostedRuntimeReviewError as exc:
        print("hosted runtime review: FAIL: {}".format(exc), file=sys.stderr)
        sys.exit(1)
