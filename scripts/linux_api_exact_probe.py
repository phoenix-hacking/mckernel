#!/usr/bin/env python3
"""Capture and verify exact Rocky Linux API evidence for RS-001.

The frozen API-needs manifest is an R0 inventory, not a Rocky 10.2 claim.  This
tool adds a separate, immutable evidence layer tied to the checksum-locked
Rocky source RPM, source archive, patched source tree, selected configuration,
kernel build outputs, generated Rust bindings, and tool binaries.

The tool never awards RS-001 credit.  Even a technically complete capture is
marked review-required and credit-ineligible; missing exact inputs or reviewed
maps keep technical readiness false.
"""

from __future__ import print_function

import argparse
import copy
import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple


SCHEMA_VERSION = 1
CONTRACT_ID = "mckernel-rs001-exact-linux-api-probe-v1"
EVIDENCE_PROFILE = "rocky-10.2-exact-linux-api-evidence-v1"
EXPECTED_NEED_COUNT = 268
EXPECTED_MODULES = ("ihk", "ihk_smp_x86_64", "mcctrl")
NEEDS_PATH = Path("host-kernel/contracts/linux-api-needs-v1.json")
CONTRACT_PATH = Path("host-kernel/contracts/linux-api-exact-probe-v1.json")
SOURCE_LOCK_PATH = Path("host-kernel/rocky/source-lock.json")
PATCH_SERIES_PATH = Path("host-kernel/rocky/patches/series.json")
RUST_COMPAT_PATCH_PATHS = (
    Path("host-kernel/rocky/patches/0001-x86-rust-set-rustc-abi-x86-softfloat.patch"),
    Path("host-kernel/rocky/patches/0002-rust-support-rust-1.91-target-spec.patch"),
)
CONFIG_POLICY_PATH = Path("host-kernel/rocky/config-policy.json")
TOOLCHAIN_LOCK_PATH = Path("host-kernel/rocky/toolchain-lock.json")
WORKFLOW_PATH = Path(".github/workflows/rs001-linux-api-exact-probe.yml")
SCRIPT_PATH = Path("scripts/linux_api_exact_probe.py")
RUST_COMPAT_FIXTURE_PATH = Path(
    "scripts/tests/fixtures/generate-rust-target-rocky-6.12.rs"
)
RUST_COMPAT_FIXTURE_SHA256 = (
    "9c21a1b67751db98e407439b77d014be6b92ba3cf6457fde6a4118a798f4fa05"
)
RUST_COMPAT_POSTIMAGE_SHA256 = (
    "555ff4dff6548bb5f24087cdad737363b5694668aa462f77adfb3571498ec678"
)
HEX64 = re.compile(r"^[0-9a-f]{64}$")
HEX40 = re.compile(r"^[0-9a-f]{40}$")
CONFIG_LINE = re.compile(r"^(CONFIG_[A-Za-z0-9_]+)=(.*)$")
CONFIG_UNSET = re.compile(r"^# (CONFIG_[A-Za-z0-9_]+) is not set$")
RUST_BINDING = re.compile(
    r"\bpub\s+(?:(?:unsafe|const)\s+)*(?:fn|static(?:\s+mut)?)\s+([A-Za-z_][A-Za-z0-9_]*)"
)
TOOL_PROBES = (
    ("python", (sys.executable, "--version")),
    ("make", ("make", "--version")),
    ("clang", ("clang", "--version")),
    ("ld.lld", ("ld.lld", "--version")),
    ("llvm-nm", ("llvm-nm", "--version")),
    ("rustc", ("rustc", "--version", "--verbose")),
    ("bindgen", ("bindgen", "--version")),
    ("pahole", ("pahole", "--version")),
    ("patch", ("patch", "--version")),
    ("rpm", ("rpm", "--version")),
)
RUST_COMPAT_UPSTREAM_COMMITS = (
    "6273a058383e05465083b535ed9469f2c8a48321",
    "8851e27d2cb947ea8bbbe8e812068f7bf5cbd00b",
)


class ProbeError(RuntimeError):
    """Raised when an exact-source contract or capture is malformed."""


def canonical_bytes(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode(
        "utf-8"
    )


def pretty(value):
    return json.dumps(value, indent=2, sort_keys=True) + "\n"


def sha256_bytes(value):
    return hashlib.sha256(value).hexdigest()


def sha256_file(path):
    digest = hashlib.sha256()
    try:
        with open(str(path), "rb") as stream:
            while True:
                chunk = stream.read(1024 * 1024)
                if not chunk:
                    break
                digest.update(chunk)
    except (IOError, OSError) as exc:
        raise ProbeError("cannot hash {0}: {1}".format(path, exc))
    return digest.hexdigest()


def object_without_duplicates(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ProbeError("duplicate JSON key: {0}".format(key))
        result[key] = value
    return result


def read_json(path):
    try:
        with open(str(path), "r", encoding="utf-8") as stream:
            value = json.load(stream, object_pairs_hook=object_without_duplicates)
    except (IOError, OSError, ValueError) as exc:
        raise ProbeError("cannot parse {0}: {1}".format(path, exc))
    if not isinstance(value, dict):
        raise ProbeError("{0} must contain one JSON object".format(path))
    return value


def atomic_write(path, text):
    parent = path.parent
    parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=path.name + ".", dir=str(parent))
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, str(path))
    except Exception:
        try:
            os.unlink(temporary)
        except OSError:
            pass
        raise


def require_keys(value, keys, label):
    if not isinstance(value, dict):
        raise ProbeError("{0} must be an object".format(label))
    if set(value) != set(keys):
        raise ProbeError(
            "{0} keys differ: missing={1}, extra={2}".format(
                label, sorted(set(keys) - set(value)), sorted(set(value) - set(keys))
            )
        )
    return value


def regular_file(path, label):
    resolved = path.resolve()
    if path.is_symlink() or not resolved.is_file():
        raise ProbeError("{0} is missing, non-regular, or a symlink: {1}".format(label, path))
    return resolved


def repository_file(repo, relative, label):
    if relative.is_absolute() or ".." in relative.parts:
        raise ProbeError("{0} escapes repository: {1}".format(label, relative))
    candidate = repo / relative
    resolved = candidate.resolve()
    try:
        common = os.path.commonpath((str(resolved), str(repo.resolve())))
    except ValueError:
        common = ""
    if common != str(repo.resolve()):
        raise ProbeError("{0} escapes repository: {1}".format(label, candidate))
    return regular_file(candidate, label)


def file_record(path):
    path = regular_file(path, "capture input")
    return {
        "bytes": path.stat().st_size,
        "sha256": sha256_file(path),
    }


def evidence_digest(value):
    unsigned = copy.deepcopy(value)
    unsigned.pop("evidence_sha256", None)
    return sha256_bytes(canonical_bytes(unsigned))


def contract_digest(value):
    unsigned = copy.deepcopy(value)
    unsigned.pop("contract_sha256", None)
    return sha256_bytes(canonical_bytes(unsigned))


def validate_needs_manifest(manifest):
    if manifest.get("schema_version") != 1:
        raise ProbeError("Linux API needs schema changed")
    if manifest.get("manifest_id") != "mckernel-native-rust-linux-api-needs-v1":
        raise ProbeError("Linux API needs identity changed")
    unsigned = copy.deepcopy(manifest)
    recorded = unsigned.pop("manifest_sha256", None)
    if recorded != sha256_bytes(canonical_bytes(unsigned)):
        raise ProbeError("Linux API needs manifest digest is stale")
    needs = manifest.get("needs")
    if not isinstance(needs, list) or len(needs) != EXPECTED_NEED_COUNT:
        raise ProbeError("Linux API needs must contain exactly 268 rows")
    ids = []
    prior = None
    for index, need in enumerate(needs):
        if not isinstance(need, dict):
            raise ProbeError("need {0} is malformed".format(index))
        need_id = need.get("id")
        symbol = need.get("symbol")
        kind = need.get("lookup_kind")
        modules = need.get("owner", {}).get("consuming_modules")
        if (
            not isinstance(need_id, str)
            or not isinstance(symbol, str)
            or kind not in ("module_import", "dynamic_kallsyms")
            or not isinstance(modules, list)
            or not modules
            or any(module not in EXPECTED_MODULES for module in modules)
        ):
            raise ProbeError("need {0} has invalid identity".format(index))
        key = (0 if kind == "module_import" else 1, symbol)
        if prior is not None and key <= prior:
            raise ProbeError("Linux API needs are not unique and sorted")
        prior = key
        ids.append(need_id)
    if len(ids) != len(set(ids)):
        raise ProbeError("Linux API need IDs are duplicated")
    coverage = manifest.get("coverage")
    if not isinstance(coverage, dict) or coverage.get("need_count") != len(needs):
        raise ProbeError("Linux API needs coverage is stale")
    return needs


def lock_record(repo, relative):
    path = repository_file(repo, relative, str(relative))
    value = read_json(path)
    return value, {
        "path": str(relative),
        "sha256": sha256_file(path),
    }


def rust_compatibility_patch_records(repo):
    fixture = repository_file(
        repo, RUST_COMPAT_FIXTURE_PATH, "Rocky Rust target generator fixture"
    )
    if sha256_file(fixture) != RUST_COMPAT_FIXTURE_SHA256:
        raise ProbeError("Rocky Rust target generator fixture digest changed")
    records = []
    required_additions = (
        {
            "+    fn rustc_version_atleast(&self, major: u32, minor: u32, patch: u32)": 1,
            "+        if cfg.rustc_version_atleast(1, 86, 0) {": 2,
            '+            ts.push("rustc-abi", "x86-softfloat");': 2,
        },
        {
            "+        if cfg.rustc_version_atleast(1, 91, 0) {": 2,
            '+            ts.push("target-pointer-width", 64);': 1,
            '+            ts.push("target-pointer-width", 32);': 1,
        },
    )
    for index, relative in enumerate(RUST_COMPAT_PATCH_PATHS):
        path = repository_file(repo, relative, "Rust target compatibility patch")
        try:
            raw = path.read_bytes()
            text = raw.decode("utf-8")
        except (IOError, OSError, UnicodeDecodeError) as exc:
            raise ProbeError(
                "cannot read Rust target compatibility patch: {0}".format(exc)
            )
        if not raw.endswith(b"\n") or b"\r" in raw:
            raise ProbeError("Rust target compatibility patch must be LF-only text")
        commit = RUST_COMPAT_UPSTREAM_COMMITS[index]
        if text.count(commit) != 2 or text.count("diff --git ") != 1 or any(
            text.count(fragment) != count
            for fragment, count in required_additions[index].items()
        ):
            raise ProbeError(
                "Rust target compatibility patch is not frozen upstream commit {0}".format(
                    commit
                )
            )
        records.append(
            {
                "applied_after": (
                    "exact Rocky dist-git patch series"
                    if index == 0
                    else str(RUST_COMPAT_PATCH_PATHS[index - 1])
                ),
                "path": str(relative),
                "sha256": sha256_bytes(raw),
                "size": len(raw),
                "upstream_commit": commit,
            }
        )
    return records


def verify_rust_compatibility_patch_replay(repo, records):
    fixture = repository_file(
        repo, RUST_COMPAT_FIXTURE_PATH, "Rocky Rust target generator fixture"
    )
    with tempfile.TemporaryDirectory(prefix="rs001-rust-compat-") as temporary:
        root = Path(temporary)
        target = root / "scripts/generate_rust_target.rs"
        target.parent.mkdir()
        shutil.copyfile(str(fixture), str(target))
        for record in records:
            patch_path = repository_file(
                repo, Path(record["path"]), "Rust target compatibility patch"
            )
            run_checked(
                [
                    shutil.which("patch") or "patch",
                    "-p1",
                    "--batch",
                    "--forward",
                    "--no-backup-if-mismatch",
                    "-i",
                    str(patch_path),
                ],
                root,
            )
        if sha256_file(target) != RUST_COMPAT_POSTIMAGE_SHA256:
            raise ProbeError("Rust target compatibility patch postimage changed")


def build_contract(repo):
    needs_path = repository_file(repo, NEEDS_PATH, "Linux API needs")
    needs_manifest = read_json(needs_path)
    needs = validate_needs_manifest(needs_manifest)
    source_lock, source_record = lock_record(repo, SOURCE_LOCK_PATH)
    patch_series, patch_record = lock_record(repo, PATCH_SERIES_PATH)
    config_policy, config_record = lock_record(repo, CONFIG_POLICY_PATH)
    toolchain_lock, toolchain_record = lock_record(repo, TOOLCHAIN_LOCK_PATH)
    rust_compat_records = rust_compatibility_patch_records(repo)
    verify_rust_compatibility_patch_replay(repo, rust_compat_records)
    source_rpm = source_lock.get("source_rpm", {})
    embedded = source_lock.get("embedded_objects", [])
    archives = [
        row
        for row in embedded
        if isinstance(row, dict)
        and row.get("role") == "Rocky-derived Linux source archive"
    ]
    if len(archives) != 1:
        raise ProbeError("source lock must name exactly one Linux source archive")
    if source_lock.get("lock_id") != config_policy.get("source_lock_id"):
        raise ProbeError("source and config locks diverge")
    if source_lock.get("lock_id") != toolchain_lock.get("source_lock", {}).get(
        "lock_id"
    ):
        raise ProbeError("source and toolchain locks diverge")
    patch_rows = patch_series.get("patches")
    if not isinstance(patch_rows, list):
        raise ProbeError("patch series is malformed")
    ids = [row["id"] for row in needs]
    workflow = repository_file(repo, WORKFLOW_PATH, "RS-001 workflow")
    script = repository_file(repo, SCRIPT_PATH, "RS-001 checker")
    contract = {
        "schema_version": SCHEMA_VERSION,
        "contract_id": CONTRACT_ID,
        "gate": {
            "gate_id": "RS-001",
            "credit_eligible": False,
            "self_attestation_forbidden": True,
            "policy": (
                "Capture may prove exact technical facts but can never mark RS-001 PASS; "
                "independent review and evidence registration are required."
            ),
        },
        "target": {
            "distribution": "Rocky Linux",
            "release": "10.2",
            "architecture": "x86_64",
            "kernel_nvr": source_rpm.get("nvr"),
            "source_rpm_filename": source_rpm.get("filename"),
            "source_rpm_bytes": source_rpm.get("size"),
            "source_rpm_sha256": source_rpm.get("sha256"),
            "source_archive_filename": archives[0].get("path", "").split("/")[-1],
            "source_archive_root": archives[0].get("path", "").split("/")[-1].rsplit(
                ".tar.xz", 1
            )[0],
            "source_archive_bytes": archives[0].get("size"),
            "source_archive_sha256": archives[0].get("sha256"),
        },
        "frozen_needs": {
            "path": str(NEEDS_PATH),
            "file_sha256": sha256_file(needs_path),
            "manifest_sha256": needs_manifest["manifest_sha256"],
            "need_count": len(needs),
            "need_ids_sha256": sha256_bytes(canonical_bytes(ids)),
        },
        "repository_inputs": {
            "source_lock": source_record,
            "patch_series": patch_record,
            "rust_target_compatibility_patches": rust_compat_records,
            "rust_target_generator_preimage": {
                "path": str(RUST_COMPAT_FIXTURE_PATH),
                "sha256": RUST_COMPAT_FIXTURE_SHA256,
            },
            "config_policy": config_record,
            "toolchain_lock": toolchain_record,
            "checker": {"path": str(SCRIPT_PATH), "sha256": sha256_file(script)},
            "workflow": {"path": str(WORKFLOW_PATH), "sha256": sha256_file(workflow)},
        },
        "source_patch_contract": {
            "patches": [
                {
                    "applied": row.get("applied"),
                    "empty": row.get("empty"),
                    "path": row.get("path"),
                    "sha256": row.get("sha256"),
                    "size": row.get("size"),
                }
                for row in patch_rows
            ]
            + [
                {
                    "applied": True,
                    "empty": False,
                    "path": record["path"],
                    "sha256": record["sha256"],
                    "size": record["size"],
                }
                for record in rust_compat_records
            ],
            "tree_comparison": (
                "fresh locked archive plus every applied Rocky patch and the bound "
                "Rust target compatibility patch must byte-match the supplied "
                "out-of-tree build source"
            ),
        },
        "required_capture_inputs": [
            "locked source RPM bytes",
            "locked Linux source archive bytes",
            "all locked Rocky and repository compatibility patch bytes",
            "byte-exact patched source tree",
            "locked Rocky x86_64 baseline config",
            "first and second idempotent resolved configs",
            "Module.symvers from the exact selected build",
            "System.map from the exact selected build",
            "generated Rust bindings from the exact selected build",
            "kernel.release and compiler/tool provenance",
        ],
        "per_need_evidence": [
            "availability in System.map and/or Module.symvers",
            "export class, provider module, and namespace",
            "selected config digest plus separately reviewed Kconfig requirements",
            "generated Rust binding or separately reviewed Rust abstraction",
            "separately reviewed compiler-backed consumer context classification",
        ],
        "reviewed_map_pins": {
            "config_requirements_sha256": None,
            "consumer_contexts_sha256": None,
            "rust_abstractions_sha256": None,
        },
        "readiness_without_exact_capture": {
            "gate_status": "NOT_READY",
            "technical_complete": False,
            "credit_eligible": False,
            "blocker": "exact compiler/source/build inputs and pinned reviewed maps are absent",
        },
        "evidence_profile": EVIDENCE_PROFILE,
    }
    contract["contract_sha256"] = contract_digest(contract)
    return contract


def validate_contract(contract, repo):
    if contract.get("schema_version") != SCHEMA_VERSION:
        raise ProbeError("probe contract schema changed")
    if contract.get("contract_id") != CONTRACT_ID:
        raise ProbeError("probe contract identity changed")
    if contract.get("contract_sha256") != contract_digest(contract):
        raise ProbeError("probe contract digest is stale")
    expected = build_contract(repo)
    if contract != expected:
        raise ProbeError("exact Linux API probe contract is stale")
    gate = contract.get("gate", {})
    if gate.get("credit_eligible") is not False or gate.get(
        "self_attestation_forbidden"
    ) is not True:
        raise ProbeError("probe contract permits self-attested gate credit")
    readiness = contract.get("readiness_without_exact_capture", {})
    if readiness != {
        "gate_status": "NOT_READY",
        "technical_complete": False,
        "credit_eligible": False,
        "blocker": "exact compiler/source/build inputs and pinned reviewed maps are absent",
    }:
        raise ProbeError("absent-input readiness must remain fail-closed")


def parse_config(path):
    values = {}
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (IOError, OSError, UnicodeDecodeError) as exc:
        raise ProbeError("cannot parse config {0}: {1}".format(path, exc))
    for line in lines:
        match = CONFIG_LINE.match(line)
        if match:
            name, value = match.groups()
        else:
            match = CONFIG_UNSET.match(line)
            if not match:
                continue
            name, value = match.group(1), "n"
        if name in values:
            raise ProbeError("duplicate config symbol {0} in {1}".format(name, path))
        values[name] = value
    if not values:
        raise ProbeError("config has no symbols: {0}".format(path))
    return values


def config_capture(baseline, resolved, second, policy, repo):
    baseline = regular_file(baseline, "baseline config")
    resolved = regular_file(resolved, "resolved config")
    second = regular_file(second, "second-pass config")
    baseline_values = parse_config(baseline)
    resolved_values = parse_config(resolved)
    second_values = parse_config(second)
    baseline_sha = sha256_file(baseline)
    resolved_sha = sha256_file(resolved)
    second_sha = sha256_file(second)
    expected_baseline = policy.get("baseline", {}).get("sha256")
    if baseline_sha != expected_baseline:
        raise ProbeError("baseline config does not match Rocky lock")
    fragment_relative = Path(policy.get("delta", {}).get("fragment_path", ""))
    fragment = repository_file(repo, fragment_relative, "Rust config fragment")
    if sha256_file(fragment) != policy.get("delta", {}).get("fragment_sha256"):
        raise ProbeError("Rust config fragment digest changed")
    all_names = set(baseline_values) | set(resolved_values)
    changed = sorted(
        name
        for name in all_names
        if baseline_values.get(name, "<absent>")
        != resolved_values.get(name, "<absent>")
    )
    allowed = set(policy.get("delta", {}).get("allowed_symbols", []))
    allowed.update(
        policy.get("verification_evidence", {})
        .get("olddefconfig_delta", {})
        .get("generated_symbol_allowlist", [])
    )
    unexpected = sorted(set(changed) - allowed)
    assertions = []
    for row in policy.get("delta", {}).get("changes", []):
        assertions.append(
            {
                "symbol": row.get("symbol"),
                "expected": row.get("resolved"),
                "actual": resolved_values.get(row.get("symbol"), "<absent>"),
                "matches": resolved_values.get(row.get("symbol"), "<absent>")
                == row.get("resolved"),
            }
        )
    for row in policy.get("preserve", []):
        assertions.append(
            {
                "symbol": row.get("symbol"),
                "expected": row.get("value"),
                "actual": resolved_values.get(row.get("symbol"), "<absent>"),
                "matches": resolved_values.get(row.get("symbol"), "<absent>")
                == row.get("value"),
            }
        )
    exact = (
        resolved_sha == second_sha
        and resolved_values == second_values
        and not unexpected
        and all(row["matches"] for row in assertions)
    )
    return {
        "baseline": dict(file_record(baseline), path_role="locked Rocky baseline"),
        "fragment": dict(file_record(fragment), path=str(fragment_relative)),
        "resolved": dict(file_record(resolved), path_role="first olddefconfig pass"),
        "second_pass": dict(file_record(second), path_role="second olddefconfig pass"),
        "changed_symbols": changed,
        "allowed_changed_symbols": sorted(allowed),
        "unexpected_changed_symbols": unexpected,
        "assertions": assertions,
        "idempotent": resolved_sha == second_sha and resolved_values == second_values,
        "exact_policy_match": exact,
        "selected_config_sha256": resolved_sha,
    }


def safe_member_name(name, root):
    normalized = name.rstrip("/")
    if not normalized or normalized.startswith("/") or "\\" in normalized:
        raise ProbeError("unsafe archive member: {0}".format(name))
    parts = normalized.split("/")
    if any(part in ("", ".", "..") for part in parts):
        raise ProbeError("unsafe archive member: {0}".format(name))
    if parts[0] != root:
        raise ProbeError("archive member escapes locked root: {0}".format(name))
    return parts


def validate_archive(archive, target):
    archive = regular_file(archive, "Linux source archive")
    if archive.name != target["source_archive_filename"]:
        raise ProbeError("Linux source archive filename changed")
    if archive.stat().st_size != target["source_archive_bytes"]:
        raise ProbeError("Linux source archive size changed")
    if sha256_file(archive) != target["source_archive_sha256"]:
        raise ProbeError("Linux source archive digest changed")
    root = target["source_archive_root"]
    try:
        stream = tarfile.open(str(archive), "r:xz")
    except (IOError, OSError, tarfile.TarError) as exc:
        raise ProbeError("cannot open Linux source archive: {0}".format(exc))
    with stream:
        members = stream.getmembers()
        if not members:
            raise ProbeError("Linux source archive is empty")
        for member in members:
            safe_member_name(member.name, root)
            if member.issym() or member.islnk():
                link = member.linkname
                if link.startswith("/") or "\\" in link:
                    raise ProbeError("unsafe archive link: {0}".format(member.name))
                combined = os.path.normpath(
                    os.path.join(os.path.dirname(member.name), link)
                )
                safe_member_name(combined, root)
            if not (
                member.isfile()
                or member.isdir()
                or member.issym()
                or member.islnk()
            ):
                raise ProbeError("unsupported archive member type: {0}".format(member.name))
    return archive


def tree_manifest(root):
    root = root.resolve()
    if not root.is_dir() or root.is_symlink():
        raise ProbeError("source tree is missing or a symlink: {0}".format(root))
    rows = []
    for directory, names, files in os.walk(str(root), followlinks=False):
        names.sort()
        files.sort()
        base = Path(directory)
        for name in list(names) + files:
            path = base / name
            relative = str(path.relative_to(root))
            if path.is_symlink():
                rows.append(
                    {"kind": "symlink", "path": relative, "target": os.readlink(str(path))}
                )
            elif path.is_file():
                rows.append(
                    {
                        "kind": "file",
                        "path": relative,
                        "bytes": path.stat().st_size,
                        "sha256": sha256_file(path),
                    }
                )
    rows.sort(key=lambda row: (row["path"], row["kind"]))
    return rows


def locate_asset(asset_root, logical_path):
    basename = Path(logical_path).name
    matches = [path for path in asset_root.rglob(basename) if path.is_file()]
    if len(matches) != 1:
        raise ProbeError(
            "expected one source asset {0}, found {1}".format(basename, len(matches))
        )
    return regular_file(matches[0], "source asset " + basename)


def run_checked(argv, cwd):
    try:
        completed = subprocess.run(
            list(argv),
            cwd=str(cwd),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=300,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ProbeError("command failed to execute: {0}".format(exc))
    if completed.returncode != 0:
        raise ProbeError(
            "command failed ({0}): {1}".format(
                completed.returncode,
                completed.stderr.decode("utf-8", errors="replace")[-2000:],
            )
        )
    return completed


def source_capture(source_rpm, archive, source_root, asset_root, contract):
    source_rpm = regular_file(source_rpm, "source RPM")
    target = contract["target"]
    if source_rpm.name != target["source_rpm_filename"]:
        raise ProbeError("source RPM filename changed")
    if source_rpm.stat().st_size != target["source_rpm_bytes"]:
        raise ProbeError("source RPM size changed")
    if sha256_file(source_rpm) != target["source_rpm_sha256"]:
        raise ProbeError("source RPM digest changed")
    archive = validate_archive(archive, target)
    asset_root = asset_root.resolve()
    if not asset_root.is_dir() or asset_root.is_symlink():
        raise ProbeError("source asset directory is invalid")
    patch_records = []
    applied = []
    for row in contract["source_patch_contract"]["patches"]:
        path = locate_asset(asset_root, row["path"])
        record = {
            "path": row["path"],
            "bytes": path.stat().st_size,
            "sha256": sha256_file(path),
            "applied": row["applied"],
            "empty": row["empty"],
        }
        if record["bytes"] != row["size"] or record["sha256"] != row["sha256"]:
            raise ProbeError("locked patch bytes changed: {0}".format(row["path"]))
        patch_records.append(record)
        if row["applied"] and not row["empty"]:
            applied.append(path)
    source_root = source_root.resolve()
    actual_rows = tree_manifest(source_root)
    with tempfile.TemporaryDirectory(prefix="rs001-source-") as temporary:
        temporary_root = Path(temporary)
        with tarfile.open(str(archive), "r:xz") as stream:
            stream.extractall(str(temporary_root))
        expected_root = temporary_root / target["source_archive_root"]
        patch_binary = shutil.which("patch")
        if not patch_binary:
            raise ProbeError("patch is required for exact source replay")
        for path in applied:
            run_checked(
                [
                    patch_binary,
                    "-p1",
                    "--batch",
                    "--forward",
                    "--no-backup-if-mismatch",
                    "-i",
                    str(path),
                ],
                expected_root,
            )
        expected_rows = tree_manifest(expected_root)
    if actual_rows != expected_rows:
        limit = min(len(actual_rows), len(expected_rows))
        mismatch = next(
            (
                index
                for index in range(limit)
                if actual_rows[index] != expected_rows[index]
            ),
            limit,
        )
        raise ProbeError(
            "patched source tree differs from locked replay at row {0}; actual={1}, expected={2}".format(
                mismatch,
                actual_rows[mismatch] if mismatch < len(actual_rows) else "<missing>",
                expected_rows[mismatch] if mismatch < len(expected_rows) else "<missing>",
            )
        )
    tree_sha = sha256_bytes(canonical_bytes(actual_rows))
    return {
        "source_rpm": dict(file_record(source_rpm), filename=source_rpm.name),
        "source_archive": dict(file_record(archive), filename=archive.name),
        "patches": patch_records,
        "patched_tree_file_count": len(actual_rows),
        "patched_tree_manifest_sha256": tree_sha,
        "exact_locked_replay": True,
    }


def parse_module_symvers(path):
    path = regular_file(path, "Module.symvers")
    symbols = defaultdict(list)
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (IOError, OSError, UnicodeDecodeError) as exc:
        raise ProbeError("cannot parse Module.symvers: {0}".format(exc))
    for number, line in enumerate(lines, 1):
        if not line.strip():
            continue
        fields = line.split("\t") if "\t" in line else line.split()
        if len(fields) < 4 or not fields[1]:
            raise ProbeError("malformed Module.symvers line {0}".format(number))
        row = {
            "crc": fields[0],
            "symbol": fields[1],
            "provider": fields[2],
            "export_class": fields[3],
            "namespace": fields[4] if len(fields) >= 5 else "",
        }
        symbols[row["symbol"]].append(row)
    if not symbols:
        raise ProbeError("Module.symvers contains no symbols")
    return path, symbols


def parse_system_map(path):
    path = regular_file(path, "System.map")
    symbols = defaultdict(list)
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (IOError, OSError, UnicodeDecodeError) as exc:
        raise ProbeError("cannot parse System.map: {0}".format(exc))
    for number, line in enumerate(lines, 1):
        fields = line.split()
        if len(fields) < 3:
            if line.strip():
                raise ProbeError("malformed System.map line {0}".format(number))
            continue
        address, kind, symbol = fields[:3]
        if not re.match(r"^[0-9a-fA-F]+$", address) or len(kind) != 1:
            raise ProbeError("malformed System.map line {0}".format(number))
        symbols[symbol].append({"address": address.lower(), "type": kind})
    if not symbols:
        raise ProbeError("System.map contains no symbols")
    return path, symbols


def rust_bindings(path):
    path = regular_file(path, "generated Rust bindings")
    try:
        text = path.read_text(encoding="utf-8")
    except (IOError, OSError, UnicodeDecodeError) as exc:
        raise ProbeError("cannot parse generated Rust bindings: {0}".format(exc))
    names = sorted(set(match.group(1) for match in RUST_BINDING.finditer(text)))
    if not names:
        raise ProbeError("generated Rust bindings expose no public functions/statics")
    return path, set(names), sha256_bytes(canonical_bytes(names))


def tool_capture():
    rows = []
    for probe_id, command in TOOL_PROBES:
        executable = command[0]
        found = executable if os.path.isabs(executable) else shutil.which(executable)
        if not found:
            rows.append(
                {
                    "id": probe_id,
                    "command": list(command),
                    "status": "missing",
                    "path": None,
                    "sha256": None,
                    "exit_code": None,
                    "stdout_sha256": None,
                    "stderr_sha256": None,
                    "version_excerpt": None,
                    "rpm_owner": None,
                    "rpm_owner_query_sha256": None,
                }
            )
            continue
        path = Path(found).resolve()
        if not path.is_file():
            raise ProbeError("tool is not a regular file: {0}".format(found))
        try:
            completed = subprocess.run(
                list(command),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=30,
            )
            stdout = completed.stdout
            stderr = completed.stderr
            exit_code = completed.returncode
        except (OSError, subprocess.TimeoutExpired) as exc:
            stdout = b""
            stderr = str(exc).encode("utf-8")
            exit_code = -1
        combined = (stdout + b"\n" + stderr).decode("utf-8", errors="replace")
        rpm_owner = None
        rpm_owner_query = b""
        rpm_binary = shutil.which("rpm")
        if rpm_binary:
            try:
                owner = subprocess.run(
                    [rpm_binary, "-qf", str(path), "--qf", "%{NEVRA}\\n"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    timeout=30,
                )
                rpm_owner_query = owner.stdout + b"\n" + owner.stderr
                if owner.returncode == 0:
                    rpm_owner = owner.stdout.decode(
                        "utf-8", errors="replace"
                    ).strip()
            except (OSError, subprocess.TimeoutExpired) as exc:
                rpm_owner_query = str(exc).encode("utf-8")
        rows.append(
            {
                "id": probe_id,
                "command": list(command),
                "status": "captured" if exit_code == 0 else "failed",
                "path": str(path),
                "sha256": sha256_file(path),
                "exit_code": exit_code,
                "stdout_sha256": sha256_bytes(stdout),
                "stderr_sha256": sha256_bytes(stderr),
                "version_excerpt": combined[:500],
                "rpm_owner": rpm_owner,
                "rpm_owner_query_sha256": sha256_bytes(rpm_owner_query),
            }
        )
    return rows


def read_os_release():
    path = Path("/etc/os-release")
    if not path.is_file():
        return {"id": None, "version_id": None, "sha256": None}
    data = path.read_bytes()
    values = {}
    for line in data.decode("utf-8", errors="replace").splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key] = value.strip().strip('"')
    return {
        "id": values.get("ID"),
        "version_id": values.get("VERSION_ID"),
        "sha256": sha256_bytes(data),
    }


def optional_pinned_map(path, pin, label):
    if path is None:
        return None, {"status": "missing", "sha256": None, "trusted": False}
    path = regular_file(path, label)
    digest = sha256_file(path)
    value = read_json(path)
    trusted = isinstance(pin, str) and HEX64.match(pin) and digest == pin
    return value, {"status": "captured", "sha256": digest, "trusted": trusted}


def per_need_rows(needs, symvers, system_map, bindings, config_sha, maps, pins):
    config_map, context_map, abstraction_map = maps
    config_pin, context_pin, abstraction_pin = pins
    rows = []
    for need in needs:
        need_id = need["id"]
        symbol = need["symbol"]
        kind = need["lookup_kind"]
        exports = sorted(
            symvers.get(symbol, []),
            key=lambda row: (
                row["provider"], row["export_class"], row["namespace"], row["crc"]
            ),
        )
        map_rows = sorted(
            system_map.get(symbol, []), key=lambda row: (row["type"], row["address"])
        )
        if exports:
            availability = "exported"
        elif map_rows:
            availability = "present_unexported"
        else:
            availability = "absent_from_selected_build"
        config_entry = (
            config_map.get("requirements", {}).get(need_id)
            if isinstance(config_map, dict)
            else None
        )
        context_entry = (
            context_map.get("contexts", {}).get(need_id)
            if isinstance(context_map, dict)
            else None
        )
        abstraction_entry = (
            abstraction_map.get("abstractions", {}).get(need_id)
            if isinstance(abstraction_map, dict)
            else None
        )
        config_resolved = config_pin and isinstance(config_entry, dict)
        context_resolved = context_pin and isinstance(context_entry, dict)
        abstraction_resolved = abstraction_pin and isinstance(abstraction_entry, dict)
        direct_binding = symbol in bindings
        if kind == "dynamic_kallsyms":
            rust_status = (
                "reviewed_replacement"
                if abstraction_resolved
                else "private_lookup_retirement_unresolved"
            )
            disposition = "retire_dynamic_lookup"
        else:
            rust_status = (
                "generated_binding"
                if direct_binding
                else "reviewed_abstraction"
                if abstraction_resolved
                else "rust_callable_surface_unresolved"
            )
            disposition = "direct_or_reviewed_rust_api"
        rows.append(
            {
                "id": need_id,
                "symbol": symbol,
                "lookup_kind": kind,
                "consuming_modules": need["owner"]["consuming_modules"],
                "availability": {
                    "status": availability,
                    "system_map_entries": map_rows,
                },
                "export": {
                    "status": (
                        "unique"
                        if len(exports) == 1
                        else "absent"
                        if not exports
                        else "ambiguous"
                    ),
                    "entries": exports,
                },
                "configuration": {
                    "selected_config_sha256": config_sha,
                    "status": (
                        "reviewed_requirements_pinned"
                        if config_resolved
                        else "selected_config_only_requirements_unresolved"
                    ),
                    "reviewed_requirement": config_entry if config_resolved else None,
                },
                "rust_callable": {
                    "generated_binding": direct_binding,
                    "status": rust_status,
                    "reviewed_abstraction": (
                        abstraction_entry if abstraction_resolved else None
                    ),
                },
                "call_context": {
                    "status": (
                        "reviewed_contexts_pinned"
                        if context_resolved
                        else "compiler_backed_context_unresolved"
                    ),
                    "reviewed_context": context_entry if context_resolved else None,
                },
                "production_disposition": disposition,
            }
        )
    return rows


def build_evidence(args, repo, contract):
    needs_manifest = read_json(repository_file(repo, NEEDS_PATH, "Linux API needs"))
    needs = validate_needs_manifest(needs_manifest)
    source_lock = read_json(repository_file(repo, SOURCE_LOCK_PATH, "source lock"))
    config_policy = read_json(
        repository_file(repo, CONFIG_POLICY_PATH, "config policy")
    )
    toolchain_lock = read_json(
        repository_file(repo, TOOLCHAIN_LOCK_PATH, "toolchain lock")
    )
    source = source_capture(
        args.source_rpm,
        args.source_archive,
        args.source_root,
        args.source_assets,
        contract,
    )
    config = config_capture(
        args.baseline_config,
        args.resolved_config,
        args.second_pass_config,
        config_policy,
        repo,
    )
    symvers_path, symvers = parse_module_symvers(args.module_symvers)
    system_map_path, system_map = parse_system_map(args.system_map)
    bindings_path, bindings, binding_set_sha = rust_bindings(args.rust_bindings)
    pins = contract["reviewed_map_pins"]
    config_map, config_map_record = optional_pinned_map(
        args.config_requirements,
        pins["config_requirements_sha256"],
        "config requirements map",
    )
    context_map, context_map_record = optional_pinned_map(
        args.consumer_contexts,
        pins["consumer_contexts_sha256"],
        "consumer context map",
    )
    abstraction_map, abstraction_map_record = optional_pinned_map(
        args.rust_abstractions,
        pins["rust_abstractions_sha256"],
        "Rust abstraction map",
    )
    rows = per_need_rows(
        needs,
        symvers,
        system_map,
        bindings,
        config["selected_config_sha256"],
        (config_map, context_map, abstraction_map),
        (
            config_map_record["trusted"],
            context_map_record["trusted"],
            abstraction_map_record["trusted"],
        ),
    )
    tools = tool_capture()
    counts = {
        "availability": dict(sorted(Counter(row["availability"]["status"] for row in rows).items())),
        "export": dict(sorted(Counter(row["export"]["status"] for row in rows).items())),
        "configuration": dict(sorted(Counter(row["configuration"]["status"] for row in rows).items())),
        "rust_callable": dict(sorted(Counter(row["rust_callable"]["status"] for row in rows).items())),
        "call_context": dict(sorted(Counter(row["call_context"]["status"] for row in rows).items())),
    }
    blockers = []
    if source_lock.get("gate", {}).get("credit_eligible") is not True:
        blockers.append(
            "Rocky source acquisition/signature/license evidence is not independently gate-ready"
        )
    if not config["exact_policy_match"]:
        blockers.append("selected config does not exactly satisfy the locked delta/preservation policy")
    if config_policy.get("gate", {}).get("credit_eligible") is not True:
        blockers.append(
            "the resolved config is not yet registered as the exact Rocky RPM production config"
        )
    closure = toolchain_lock.get("closure", {})
    if closure.get("status") != "verified" or closure.get("all_archives_verified") is not True:
        blockers.append("exact archived and signature-verified toolchain closure is missing")
    missing_tools = [row["id"] for row in tools if row["status"] != "captured"]
    if missing_tools:
        blockers.append("required tool probes are missing or failed: " + ",".join(missing_tools))
    for label, record in (
        ("per-need CONFIG requirements", config_map_record),
        ("compiler-backed consumer contexts", context_map_record),
        ("reviewed Rust abstractions", abstraction_map_record),
    ):
        if not record["trusted"]:
            blockers.append(label + " are not pinned by the contract")
    unavailable = [
        row["id"]
        for row in rows
        if row["lookup_kind"] == "module_import"
        and row["availability"]["status"] != "exported"
    ]
    if unavailable:
        blockers.append(
            "{0} imported APIs are not exported by the selected build".format(
                len(unavailable)
            )
        )
    unresolved_rust = [
        row["id"]
        for row in rows
        if row["rust_callable"]["status"]
        in (
            "rust_callable_surface_unresolved",
            "private_lookup_retirement_unresolved",
        )
    ]
    if unresolved_rust:
        blockers.append(
            "{0} needs lack a pinned Rust-callable/replacement disposition".format(
                len(unresolved_rust)
            )
        )
    blockers.append(
        "independent RS-001 review and immutable evidence registration are required; this capture cannot award gate credit"
    )
    head = args.github_head_sha or git_head(repo)
    if not HEX40.match(head):
        raise ProbeError("repository capture commit must be exact 40-hex")
    os_release = read_os_release()
    evidence = {
        "schema_version": SCHEMA_VERSION,
        "profile": EVIDENCE_PROFILE,
        "contract_id": CONTRACT_ID,
        "contract_sha256": contract["contract_sha256"],
        "capture_identity": {
            "repository_commit": head,
            "github_repository": args.github_repository,
            "github_run_id": args.github_run_id,
            "github_run_attempt": args.github_run_attempt,
        },
        "target": contract["target"],
        "inputs": {
            "frozen_needs_file_sha256": contract["frozen_needs"]["file_sha256"],
            "frozen_needs_manifest_sha256": contract["frozen_needs"]["manifest_sha256"],
            "source_lock_sha256": contract["repository_inputs"]["source_lock"]["sha256"],
            "config_policy_sha256": contract["repository_inputs"]["config_policy"]["sha256"],
            "toolchain_lock_sha256": contract["repository_inputs"]["toolchain_lock"]["sha256"],
            "patch_series_sha256": contract["repository_inputs"]["patch_series"]["sha256"],
            "rust_target_compatibility_patch_sha256s": [
                row["sha256"]
                for row in contract["repository_inputs"][
                    "rust_target_compatibility_patches"
                ]
            ],
        },
        "environment": {
            "architecture": platform.machine(),
            "os_release": os_release,
            "uname": platform.uname()._asdict(),
            "tools": tools,
        },
        "source": source,
        "configuration": config,
        "build_outputs": {
            "module_symvers": dict(file_record(symvers_path), symbol_count=len(symvers)),
            "system_map": dict(file_record(system_map_path), symbol_count=len(system_map)),
            "rust_bindings": dict(
                file_record(bindings_path),
                binding_count=len(bindings),
                binding_set_sha256=binding_set_sha,
            ),
            "kernel_release": args.kernel_release,
        },
        "reviewed_maps": {
            "config_requirements": config_map_record,
            "consumer_contexts": context_map_record,
            "rust_abstractions": abstraction_map_record,
        },
        "needs": rows,
        "coverage": {
            "need_count": len(rows),
            "need_ids_sha256": sha256_bytes(canonical_bytes([row["id"] for row in rows])),
            "by_status": counts,
        },
        "readiness": {
            "gate": "RS-001",
            "gate_status": "NOT_READY",
            "technical_complete": False,
            "credit_eligible": False,
            "review_required": True,
            "blockers": blockers,
        },
    }
    evidence["evidence_sha256"] = evidence_digest(evidence)
    validate_evidence(evidence, contract, needs_manifest)
    return evidence


def git_head(repo):
    try:
        completed = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(repo),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=20,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ProbeError("cannot resolve repository commit: {0}".format(exc))
    value = completed.stdout.decode("ascii", errors="replace").strip()
    if completed.returncode != 0 or not HEX40.match(value):
        raise ProbeError("cannot resolve exact repository commit")
    return value


def validate_evidence(evidence, contract, needs_manifest):
    require_keys(
        evidence,
        {
            "schema_version",
            "profile",
            "contract_id",
            "contract_sha256",
            "capture_identity",
            "target",
            "inputs",
            "environment",
            "source",
            "configuration",
            "build_outputs",
            "reviewed_maps",
            "needs",
            "coverage",
            "readiness",
            "evidence_sha256",
        },
        "evidence",
    )
    if evidence["schema_version"] != SCHEMA_VERSION or evidence["profile"] != EVIDENCE_PROFILE:
        raise ProbeError("evidence schema/profile changed")
    if evidence["contract_id"] != CONTRACT_ID or evidence["contract_sha256"] != contract["contract_sha256"]:
        raise ProbeError("evidence is not bound to the exact contract")
    if evidence["evidence_sha256"] != evidence_digest(evidence):
        raise ProbeError("evidence digest is stale")
    if evidence["target"] != contract["target"]:
        raise ProbeError("evidence target diverges from the contract")
    expected_inputs = {
        "frozen_needs_file_sha256": contract["frozen_needs"]["file_sha256"],
        "frozen_needs_manifest_sha256": contract["frozen_needs"]["manifest_sha256"],
        "source_lock_sha256": contract["repository_inputs"]["source_lock"]["sha256"],
        "config_policy_sha256": contract["repository_inputs"]["config_policy"]["sha256"],
        "toolchain_lock_sha256": contract["repository_inputs"]["toolchain_lock"]["sha256"],
        "patch_series_sha256": contract["repository_inputs"]["patch_series"]["sha256"],
        "rust_target_compatibility_patch_sha256s": [
            row["sha256"]
            for row in contract["repository_inputs"][
                "rust_target_compatibility_patches"
            ]
        ],
    }
    if evidence["inputs"] != expected_inputs:
        raise ProbeError("evidence repository input bindings changed")
    identity = require_keys(
        evidence["capture_identity"],
        {
            "repository_commit",
            "github_repository",
            "github_run_id",
            "github_run_attempt",
        },
        "capture identity",
    )
    if not HEX40.match(str(identity["repository_commit"])):
        raise ProbeError("capture identity is not an exact commit")
    environment = require_keys(
        evidence["environment"],
        {"architecture", "os_release", "uname", "tools"},
        "capture environment",
    )
    if environment["architecture"] != "x86_64":
        raise ProbeError("capture architecture is not x86_64")
    os_release = environment["os_release"]
    if (
        not isinstance(os_release, dict)
        or os_release.get("id") != "rocky"
        or os_release.get("version_id") != "10.2"
        or not HEX64.match(str(os_release.get("sha256")))
    ):
        raise ProbeError("capture runtime is not hash-bound Rocky 10.2")
    tools = environment["tools"]
    if not isinstance(tools, list) or [row.get("id") for row in tools] != [
        row[0] for row in TOOL_PROBES
    ]:
        raise ProbeError("tool capture is incomplete or reordered")
    for tool in tools:
        require_keys(
            tool,
            {
                "id",
                "command",
                "status",
                "path",
                "sha256",
                "exit_code",
                "stdout_sha256",
                "stderr_sha256",
                "version_excerpt",
                "rpm_owner",
                "rpm_owner_query_sha256",
            },
            "tool capture",
        )
        if tool.get("status") not in ("captured", "failed", "missing"):
            raise ProbeError("tool capture status is invalid")
        if tool.get("status") == "captured" and (
            tool.get("exit_code") != 0
            or not HEX64.match(str(tool.get("sha256")))
            or not HEX64.match(str(tool.get("stdout_sha256")))
            or not HEX64.match(str(tool.get("stderr_sha256")))
        ):
            raise ProbeError("captured tool lacks immutable provenance")
        if tool.get("status") != "missing" and not HEX64.match(
            str(tool.get("rpm_owner_query_sha256"))
        ):
            raise ProbeError("tool RPM-owner query is not digest-bound")
    source = require_keys(
        evidence["source"],
        {
            "source_rpm",
            "source_archive",
            "patches",
            "patched_tree_file_count",
            "patched_tree_manifest_sha256",
            "exact_locked_replay",
        },
        "source evidence",
    )
    if source["exact_locked_replay"] is not True:
        raise ProbeError("source evidence is not an exact locked replay")
    if source["source_rpm"] != {
        "bytes": contract["target"]["source_rpm_bytes"],
        "sha256": contract["target"]["source_rpm_sha256"],
        "filename": contract["target"]["source_rpm_filename"],
    }:
        raise ProbeError("source RPM evidence diverges from lock")
    if source["source_archive"] != {
        "bytes": contract["target"]["source_archive_bytes"],
        "sha256": contract["target"]["source_archive_sha256"],
        "filename": contract["target"]["source_archive_filename"],
    }:
        raise ProbeError("source archive evidence diverges from lock")
    expected_patches = contract["source_patch_contract"]["patches"]
    if len(source["patches"]) != len(expected_patches):
        raise ProbeError("source patch evidence count changed")
    for actual, expected in zip(source["patches"], expected_patches):
        if actual != {
            "path": expected["path"],
            "bytes": expected["size"],
            "sha256": expected["sha256"],
            "applied": expected["applied"],
            "empty": expected["empty"],
        }:
            raise ProbeError("source patch evidence diverges from lock")
    if (
        not isinstance(source["patched_tree_file_count"], int)
        or source["patched_tree_file_count"] < 1
        or not HEX64.match(str(source["patched_tree_manifest_sha256"]))
    ):
        raise ProbeError("patched source tree evidence is malformed")
    configuration = evidence["configuration"]
    required_config = {
        "baseline",
        "fragment",
        "resolved",
        "second_pass",
        "changed_symbols",
        "allowed_changed_symbols",
        "unexpected_changed_symbols",
        "assertions",
        "idempotent",
        "exact_policy_match",
        "selected_config_sha256",
    }
    require_keys(configuration, required_config, "configuration evidence")
    if configuration["selected_config_sha256"] != configuration["resolved"].get(
        "sha256"
    ):
        raise ProbeError("selected config digest is not the resolved config")
    recomputed_config_exact = (
        configuration["idempotent"] is True
        and not configuration["unexpected_changed_symbols"]
        and isinstance(configuration["assertions"], list)
        and bool(configuration["assertions"])
        and all(row.get("matches") is True for row in configuration["assertions"])
    )
    if configuration["exact_policy_match"] is not recomputed_config_exact:
        raise ProbeError("configuration exactness result is stale")
    outputs = require_keys(
        evidence["build_outputs"],
        {"module_symvers", "system_map", "rust_bindings", "kernel_release"},
        "build outputs",
    )
    if not isinstance(outputs["kernel_release"], str) or not outputs["kernel_release"]:
        raise ProbeError("kernel release evidence is missing")
    for label, count_key in (
        ("module_symvers", "symbol_count"),
        ("system_map", "symbol_count"),
        ("rust_bindings", "binding_count"),
    ):
        record = outputs[label]
        if (
            not isinstance(record, dict)
            or not HEX64.match(str(record.get("sha256")))
            or not isinstance(record.get("bytes"), int)
            or record.get("bytes") < 1
            or not isinstance(record.get(count_key), int)
            or record.get(count_key) < 1
        ):
            raise ProbeError("{0} build evidence is malformed".format(label))
    if not HEX64.match(str(outputs["rust_bindings"].get("binding_set_sha256"))):
        raise ProbeError("Rust binding set digest is missing")
    reviewed_maps = evidence["reviewed_maps"]
    if set(reviewed_maps) != {
        "config_requirements",
        "consumer_contexts",
        "rust_abstractions",
    }:
        raise ProbeError("reviewed map evidence is malformed")
    pins = contract["reviewed_map_pins"]
    for label, pin_name in (
        ("config_requirements", "config_requirements_sha256"),
        ("consumer_contexts", "consumer_contexts_sha256"),
        ("rust_abstractions", "rust_abstractions_sha256"),
    ):
        record = reviewed_maps[label]
        expected_trust = (
            isinstance(pins[pin_name], str)
            and record.get("sha256") == pins[pin_name]
        )
        if record.get("trusted") is not expected_trust:
            raise ProbeError("reviewed map trust is not contract-derived")
    needs = validate_needs_manifest(needs_manifest)
    rows = evidence["needs"]
    if not isinstance(rows, list) or len(rows) != EXPECTED_NEED_COUNT:
        raise ProbeError("evidence must contain exactly 268 need rows")
    expected_ids = [need["id"] for need in needs]
    actual_ids = [row.get("id") for row in rows if isinstance(row, dict)]
    if actual_ids != expected_ids or len(actual_ids) != len(set(actual_ids)):
        raise ProbeError("evidence need identities diverge from frozen manifest")
    for need, row in zip(needs, rows):
        require_keys(
            row,
            {
                "id",
                "symbol",
                "lookup_kind",
                "consuming_modules",
                "availability",
                "export",
                "configuration",
                "rust_callable",
                "call_context",
                "production_disposition",
            },
            "need evidence " + need["id"],
        )
        if (
            row["symbol"] != need["symbol"]
            or row["lookup_kind"] != need["lookup_kind"]
            or row["consuming_modules"] != need["owner"]["consuming_modules"]
        ):
            raise ProbeError("need evidence identity changed: " + need["id"])
        if row["configuration"].get("selected_config_sha256") != evidence[
            "configuration"
        ].get("selected_config_sha256"):
            raise ProbeError("need config binding changed: " + need["id"])
        exports = row["export"].get("entries")
        if not isinstance(exports, list):
            raise ProbeError("need export rows are malformed: " + need["id"])
        for export in exports:
            require_keys(
                export,
                {"crc", "symbol", "provider", "export_class", "namespace"},
                "export row",
            )
            if export["symbol"] != need["symbol"]:
                raise ProbeError("export row symbol changed: " + need["id"])
        map_rows = row["availability"].get("system_map_entries")
        if not isinstance(map_rows, list):
            raise ProbeError("System.map rows are malformed: " + need["id"])
        expected_availability = (
            "exported"
            if exports
            else "present_unexported"
            if map_rows
            else "absent_from_selected_build"
        )
        expected_export = (
            "unique" if len(exports) == 1 else "absent" if not exports else "ambiguous"
        )
        if (
            row["availability"].get("status") != expected_availability
            or row["export"].get("status") != expected_export
        ):
            raise ProbeError("availability/export status is stale: " + need["id"])
        if pins["config_requirements_sha256"] is None and row["configuration"].get(
            "status"
        ) != "selected_config_only_requirements_unresolved":
            raise ProbeError("unpinned CONFIG review was trusted: " + need["id"])
        if pins["consumer_contexts_sha256"] is None and row["call_context"].get(
            "status"
        ) != "compiler_backed_context_unresolved":
            raise ProbeError("unpinned context review was trusted: " + need["id"])
    coverage = evidence["coverage"]
    if coverage.get("need_count") != len(rows):
        raise ProbeError("evidence coverage total is stale")
    if coverage.get("need_ids_sha256") != sha256_bytes(canonical_bytes(actual_ids)):
        raise ProbeError("evidence need ID digest is stale")
    expected_counts = {
        "availability": dict(sorted(Counter(row["availability"]["status"] for row in rows).items())),
        "export": dict(sorted(Counter(row["export"]["status"] for row in rows).items())),
        "configuration": dict(sorted(Counter(row["configuration"]["status"] for row in rows).items())),
        "rust_callable": dict(sorted(Counter(row["rust_callable"]["status"] for row in rows).items())),
        "call_context": dict(sorted(Counter(row["call_context"]["status"] for row in rows).items())),
    }
    if coverage.get("by_status") != expected_counts:
        raise ProbeError("evidence status coverage is stale")
    readiness = evidence["readiness"]
    if (
        readiness.get("gate") != "RS-001"
        or readiness.get("gate_status") != "NOT_READY"
        or readiness.get("technical_complete") is not False
        or readiness.get("credit_eligible") is not False
        or readiness.get("review_required") is not True
        or not isinstance(readiness.get("blockers"), list)
        or not readiness["blockers"]
    ):
        raise ProbeError("evidence overclaims RS-001 readiness")
    if not any("cannot award gate credit" in blocker for blocker in readiness["blockers"]):
        raise ProbeError("independent review blocker is missing")
    forbidden = re.compile(r"^(?:PASS|READY)$", re.IGNORECASE)
    for value in readiness.values():
        if isinstance(value, str) and forbidden.match(value):
            raise ProbeError("self-attested readiness is forbidden")


def add_capture_arguments(parser):
    parser.add_argument("--source-rpm", type=Path, required=True)
    parser.add_argument("--source-archive", type=Path, required=True)
    parser.add_argument("--source-assets", type=Path, required=True)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--baseline-config", type=Path, required=True)
    parser.add_argument("--resolved-config", type=Path, required=True)
    parser.add_argument("--second-pass-config", type=Path, required=True)
    parser.add_argument("--module-symvers", type=Path, required=True)
    parser.add_argument("--system-map", type=Path, required=True)
    parser.add_argument("--rust-bindings", type=Path, required=True)
    parser.add_argument("--kernel-release", required=True)
    parser.add_argument("--config-requirements", type=Path)
    parser.add_argument("--consumer-contexts", type=Path)
    parser.add_argument("--rust-abstractions", type=Path)
    parser.add_argument("--github-head-sha")
    parser.add_argument("--github-repository")
    parser.add_argument("--github-run-id")
    parser.add_argument("--github-run-attempt")


def parse_args(argv):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[1])
    modes = parser.add_subparsers(dest="mode")
    modes.required = True
    modes.add_parser("check-contract")
    modes.add_parser("update-contract")
    capture = modes.add_parser("capture")
    add_capture_arguments(capture)
    capture.add_argument("--output", type=Path, required=True)
    verify = modes.add_parser("verify-evidence")
    verify.add_argument("--evidence", type=Path, required=True)
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv or sys.argv[1:])
    repo = args.repo.resolve()
    try:
        if not repo.is_dir():
            raise ProbeError("repository is missing: {0}".format(repo))
        contract_path = repo / CONTRACT_PATH
        if args.mode == "update-contract":
            contract = build_contract(repo)
            atomic_write(contract_path, pretty(contract))
            print(
                "updated {0}: {1} frozen needs; readiness remains NOT_READY".format(
                    contract_path, contract["frozen_needs"]["need_count"]
                )
            )
            return 0
        contract = read_json(repository_file(repo, CONTRACT_PATH, "probe contract"))
        validate_contract(contract, repo)
        if args.mode == "check-contract":
            print(
                "RS-001 exact probe contract verified: 268 needs; NOT_READY without exact capture and pinned reviews"
            )
            return 0
        needs_manifest = read_json(
            repository_file(repo, NEEDS_PATH, "Linux API needs")
        )
        if args.mode == "capture":
            evidence = build_evidence(args, repo, contract)
            atomic_write(args.output.resolve(), pretty(evidence))
            print(
                "captured {0} exact-source API rows; RS-001 remains NOT_READY; sha256={1}".format(
                    len(evidence["needs"]), evidence["evidence_sha256"]
                )
            )
            return 0
        if args.mode == "verify-evidence":
            evidence = read_json(regular_file(args.evidence, "RS-001 evidence"))
            validate_evidence(evidence, contract, needs_manifest)
            print(
                "verified immutable RS-001 evidence structure: 268 needs; gate_status=NOT_READY; sha256={0}".format(
                    evidence["evidence_sha256"]
                )
            )
            return 0
        raise ProbeError("unsupported mode")
    except ProbeError as exc:
        print("RS-001 exact API probe error: {0}".format(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
