#!/usr/bin/env python3
"""Capture deterministic, credit-forbidden RK-005 config resolution evidence."""

from __future__ import print_function

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path, PurePosixPath


CONTRACT_PATH = Path("host-kernel/rocky/evidence/config-resolution-contract-v1.json")
WORKFLOW_PATH = Path(".github/workflows/rocky-kernel-config-resolution.yml")
SOURCE_LOCK_PATH = Path("host-kernel/rocky/source-lock.json")
TOOLCHAIN_LOCK_PATH = Path("host-kernel/rocky/toolchain-lock.json")
CONFIG_POLICY_PATH = Path("host-kernel/rocky/config-policy.json")
CONFIG_FRAGMENT_PATH = Path("host-kernel/rocky/configs/rust-minimal.config")
EXPECTED_CONTRACT_SHA256 = (
    "b7f264c647dcad3d841b0c4f20ca330c9c8f647dac6c688ac1a306c575c77042"
)
EXPECTED_WORKFLOW_SHA256 = (
    "d49e4ec8331a67e867f83fc9db39858a0c8a9eb25a2a802fa721bb513120f082"
)
CONTAINER_IMAGE = (
    "rockylinux/rockylinux:10.2@"
    "sha256:e372170ca8630f0f03e9b70fdd0bf4a3ce3426b0de7cdba615f06337389de176"
)
PHASE_ID = "config-resolution"
SCHEMA_VERSION = 1
HEX_SHA256 = re.compile(r"^[0-9a-f]{64}$")
HEX_SHA1 = re.compile(r"^[0-9a-f]{40}$")
GITHUB_REPOSITORY = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
CONFIG_VALUE = re.compile(r"^(CONFIG_[A-Za-z0-9_]+)=(.*)$")
CONFIG_UNSET = re.compile(r"^# (CONFIG_[A-Za-z0-9_]+) is not set$")
EXPECTED_WORKFLOW_USES = [
    "actions/checkout@11d5960a326750d5838078e36cf38b85af677262",
    "actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02",
]
EXPECTED_COMPATIBILITY_PATCHES = [
    "host-kernel/rocky/patches/0001-x86-rust-set-rustc-abi-x86-softfloat.patch",
    "host-kernel/rocky/patches/0002-rust-support-rust-1.91-target-spec.patch",
    "host-kernel/rocky/patches/0003-kbuild-rust-add-rustc-min-version.patch",
    "host-kernel/rocky/patches/0004-rust-compile-libcore-edition-2024.patch",
    "host-kernel/rocky/patches/0005-rust-clean-unnecessary-transmutes-lint.patch",
    "host-kernel/rocky/patches/0006-rust-init-allow-dead-code-rust-1.89.patch",
    "host-kernel/rocky/patches/0007-rust-use-used-compiler-rust-1.89.patch",
    "host-kernel/rocky/patches/0008-rust-enable-arbitrary-self-types-rust-1.92.patch",
    "host-kernel/rocky/patches/0009-rust-block-drop-removed-merge-flag.patch",
    "host-kernel/rocky/patches/0010-kbuild-disable-default-const-init-unsafe.patch",
    "host-kernel/rocky/patches/0011-mm-ksm-fix-clang-21-uninitialized.patch",
    "host-kernel/rocky/patches/0012-netfs-mark-nonstring-lookup-tables.patch",
]
CAPTURE_ENVIRONMENT = {
    "ARCH": "x86_64",
    "HOME": "/root",
    "LANG": "C",
    "LC_ALL": "C",
    "PATH": "/usr/sbin:/usr/bin:/sbin:/bin",
    "TZ": "UTC",
}
PROBE_COMMANDS = {
    "bindgen": ["bindgen", "--version", "workaround-for-0.69.0"],
    "clang": ["clang", "--version"],
    "llvm": ["llvm-config", "--version"],
    "pahole": ["pahole", "--version"],
    "rustc": ["rustc", "--version", "--verbose"],
}
RUST_SRC_PROBE_COMMAND = ["rustc", "--print", "sysroot"]
EVIDENCE_NAMES = [
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
]


class ConfigResolutionError(RuntimeError):
    """Raised when RK-005 evidence cannot be captured exactly."""


def reject_duplicate_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ConfigResolutionError("duplicate JSON key: {!r}".format(key))
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
        raise ConfigResolutionError("value is not canonical JSON: {}".format(exc))
    return (text + "\n").encode("ascii")


def sha256_file(path):
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as stream:
        while True:
            chunk = stream.read(1024 * 1024)
            if not chunk:
                break
            size += len(chunk)
            digest.update(chunk)
    return size, digest.hexdigest()


def require_exact(value, expected, label):
    if value != expected or type(value) is not type(expected):
        raise ConfigResolutionError(
            "{} changed: actual={!r}, expected={!r}".format(label, value, expected)
        )


def exact_keys(value, expected, label):
    if not isinstance(value, dict) or set(value) != set(expected):
        actual = sorted(value) if isinstance(value, dict) else type(value).__name__
        raise ConfigResolutionError(
            "{} fields changed: actual={!r}, expected={!r}".format(
                label, actual, sorted(expected)
            )
        )
    return value


def read_json(path, label):
    if path.is_symlink() or not path.is_file():
        raise ConfigResolutionError("{} must be a regular file".format(label))
    data = path.read_bytes()
    try:
        value = json.loads(
            data.decode("utf-8"), object_pairs_hook=reject_duplicate_pairs
        )
    except (UnicodeDecodeError, ValueError) as exc:
        raise ConfigResolutionError("cannot parse {}: {}".format(label, exc))
    if not isinstance(value, dict):
        raise ConfigResolutionError("{} must contain a JSON object".format(label))
    return value, data


def safe_repo_file(repo, relative, label):
    path = PurePosixPath(str(relative))
    if path.is_absolute() or any(part in ("", ".", "..") for part in path.parts):
        raise ConfigResolutionError("{} path is unsafe".format(label))
    candidate = repo.joinpath(*path.parts)
    root = repo.resolve()
    resolved = candidate.resolve()
    try:
        common = os.path.commonpath((str(root), str(resolved)))
    except ValueError:
        common = ""
    if (
        common != str(root)
        or candidate != resolved
        or candidate.is_symlink()
        or not candidate.is_file()
    ):
        raise ConfigResolutionError("{} must be a confined regular file".format(label))
    return candidate


def regular_file(path, label):
    resolved = path.resolve()
    if path.is_symlink() or not resolved.is_file():
        raise ConfigResolutionError("{} must be a regular file".format(label))
    return resolved


def regular_directory(path, label):
    if path.is_symlink() or not path.is_dir() or path.resolve() != path:
        raise ConfigResolutionError("{} must be a canonical regular directory".format(label))
    return path


def validate_binding(repo, binding, label):
    exact_keys(binding, {"id", "path", "sha256"}, label)
    if not HEX_SHA256.fullmatch(str(binding["sha256"])):
        raise ConfigResolutionError("{} digest is malformed".format(label))
    path = safe_repo_file(repo, binding["path"], label)
    _, digest = sha256_file(path)
    require_exact(digest, binding["sha256"], label + " digest")
    value, _ = read_json(path, label)
    require_exact(value.get("lock_id"), binding["id"], label + " ID")
    return value


def validate_contract(repo):
    path = safe_repo_file(repo, CONTRACT_PATH.as_posix(), "config contract")
    contract, data = read_json(path, "config contract")
    require_exact(
        hashlib.sha256(data).hexdigest(),
        EXPECTED_CONTRACT_SHA256,
        "config contract digest",
    )
    exact_keys(
        contract,
        {
            "architecture",
            "claim_scope",
            "config_policy",
            "conditional_dependencies",
            "dependency_symbols",
            "gate_claims",
            "generated_environment",
            "outputs",
            "patch_authority",
            "phase_id",
            "preservation_groups",
            "process_configs",
            "requested_delta",
            "resolution",
            "schema_version",
            "source_assets",
            "source_lock",
            "success_blockers",
            "tool_environment",
            "toolchain_lock",
        },
        "config contract",
    )
    require_exact(contract["schema_version"], SCHEMA_VERSION, "contract schema")
    require_exact(contract["phase_id"], PHASE_ID, "contract phase")
    require_exact(contract["architecture"], "x86_64", "contract architecture")
    if "never awards" not in str(contract["claim_scope"]):
        raise ConfigResolutionError("contract scope is not credit-forbidden")
    expected_claims = {
        "RK-002": False,
        "RK-003": False,
        "RK-004": False,
        "RK-005": False,
        "RK-006": False,
        "RS-001": False,
    }
    require_exact(contract["gate_claims"], expected_claims, "gate claims")
    source = validate_binding(repo, contract["source_lock"], "source lock")
    toolchain = validate_binding(repo, contract["toolchain_lock"], "toolchain lock")
    policy = validate_binding(repo, contract["config_policy"], "config policy")
    require_exact(source.get("gate", {}).get("credit_eligible"), False, "RK-001 credit")
    require_exact(toolchain.get("gate", {}).get("credit_eligible"), False, "RK-003 credit")
    require_exact(policy.get("gate", {}).get("credit_eligible"), False, "RK-005 credit")
    outputs = contract["outputs"]
    require_exact(outputs, EVIDENCE_NAMES + ["SHA256SUMS"], "contract outputs")

    requested = contract["requested_delta"]
    require_exact(
        requested,
        [
            {"baseline": "n", "resolved": "y", "symbol": "CONFIG_RUST"},
            {
                "baseline": "y",
                "resolved": "n",
                "symbol": "CONFIG_MODVERSIONS",
            },
        ],
        "requested delta",
    )
    require_exact(
        contract["conditional_dependencies"],
        {
            "CONFIG_CALL_PADDING": {
                "allowed_values": ["n", "y"],
                "rustc_minimum_if_y": 108100,
            }
        },
        "conditional dependencies",
    )
    policy_requested = [
        {
            "baseline": item["baseline"],
            "resolved": item["resolved"],
            "symbol": item["symbol"],
        }
        for item in policy.get("delta", {}).get("changes", [])
    ]
    require_exact(policy_requested, requested, "policy requested delta")
    fragment = safe_repo_file(
        repo, policy["delta"]["fragment_path"], "config fragment"
    )
    _, fragment_digest = sha256_file(fragment)
    require_exact(
        fragment_digest, policy["delta"]["fragment_sha256"], "fragment digest"
    )

    generated = exact_keys(
        contract["generated_environment"],
        {
            "classification",
            "historical_policy_symbols",
            "supplemental_symbols",
            "unexpected_symbols_forbidden",
        },
        "generated environment",
    )
    historical = (
        policy.get("verification_evidence", {})
        .get("olddefconfig_delta", {})
        .get("generated_symbol_allowlist", [])
    )
    require_exact(
        generated["historical_policy_symbols"], historical, "historical allowlist"
    )
    supplemental = exact_keys(
        generated["supplemental_symbols"],
        {"CONFIG_RUSTC_HAS_UNNECESSARY_TRANSMUTES"},
        "supplemental symbols",
    )
    require_exact(
        supplemental["CONFIG_RUSTC_HAS_UNNECESSARY_TRANSMUTES"],
        {
            "expected": "y",
            "minimum_rustc_version": 108800,
            "patch": (
                "host-kernel/rocky/patches/"
                "0005-rust-clean-unnecessary-transmutes-lint.patch"
            ),
        },
        "supplemental transmute symbol",
    )
    require_exact(
        generated["unexpected_symbols_forbidden"], True, "unexpected symbol policy"
    )

    patch_authority = exact_keys(
        contract["patch_authority"],
        {"configuration_effects", "rocky_series", "rust_compatibility"},
        "patch authority",
    )
    configuration_effects = exact_keys(
        patch_authority["configuration_effects"],
        {"generated_symbols", "no_config_symbol_changes"},
        "patch configuration effects",
    )
    require_exact(
        configuration_effects["generated_symbols"],
        {
            "CONFIG_RUSTC_HAS_UNNECESSARY_TRANSMUTES": (
                "host-kernel/rocky/patches/"
                "0005-rust-clean-unnecessary-transmutes-lint.patch"
            )
        },
        "patch-generated symbols",
    )
    require_exact(
        configuration_effects["no_config_symbol_changes"],
        EXPECTED_COMPATIBILITY_PATCHES[:4] + EXPECTED_COMPATIBILITY_PATCHES[5:],
        "patches without config symbols",
    )
    rocky_series = exact_keys(
        patch_authority["rocky_series"], {"path", "sha256"}, "Rocky patch series"
    )
    series_path = safe_repo_file(repo, rocky_series["path"], "Rocky patch series")
    _, series_digest = sha256_file(series_path)
    require_exact(series_digest, rocky_series["sha256"], "Rocky series digest")
    patches = patch_authority["rust_compatibility"]
    if not isinstance(patches, list) or len(patches) != 12:
        raise ConfigResolutionError("exactly twelve compatibility patches are required")
    patch_directory = repo / "host-kernel/rocky/patches"
    discovered_patches = sorted(
        path.relative_to(repo).as_posix()
        for path in patch_directory.glob("[0-9][0-9][0-9][0-9]-*.patch")
    )
    require_exact(
        discovered_patches,
        EXPECTED_COMPATIBILITY_PATCHES,
        "repository compatibility patch authority",
    )
    require_exact(
        [row.get("path") for row in patches],
        EXPECTED_COMPATIBILITY_PATCHES,
        "compatibility patch order",
    )
    for index, row in enumerate(patches):
        if not isinstance(row, dict):
            raise ConfigResolutionError(
                "compatibility patch {} must be an object".format(index)
            )
        if "path" not in row or "sha256" not in row:
            raise ConfigResolutionError(
                "compatibility patch {} lacks a path or digest".format(index)
            )
        patch = safe_repo_file(repo, row["path"], "compatibility patch")
        _, digest = sha256_file(patch)
        require_exact(digest, row["sha256"], "compatibility patch digest")
        text = patch.read_text(encoding="utf-8")
        expected_fields = {"path", "sha256"}
        identity_count = 0
        for field, prefix in (
            ("upstream_commit", "Upstream-Commit: "),
            ("stable_commit", "Stable-Commit: "),
        ):
            identities = re.findall(
                r"(?m)^{}([0-9a-f]{{40}})$".format(re.escape(prefix)), text
            )
            if identities:
                if len(identities) != 1:
                    raise ConfigResolutionError(
                        "compatibility patch identity is ambiguous"
                    )
                expected_fields.add(field)
                identity_count += 1
                require_exact(row.get(field), identities[0], field)
        if identity_count == 0:
            raise ConfigResolutionError("compatibility patch has no commit identity")
        exact_keys(row, expected_fields, "compatibility patch {}".format(index))
        changed_paths = re.findall(
            r"(?m)^diff --git a/(\S+) b/(\S+)$", text
        )
        if not changed_paths or any(left != right for left, right in changed_paths):
            raise ConfigResolutionError("compatibility patch paths are ambiguous")
        if row["path"] in configuration_effects["no_config_symbol_changes"]:
            if any(
                PurePosixPath(left).name.startswith("Kconfig")
                for left, _ in changed_paths
            ):
                raise ConfigResolutionError(
                    "no-config compatibility patch changes Kconfig"
                )
        else:
            require_exact(
                text.count("config RUSTC_HAS_UNNECESSARY_TRANSMUTES"),
                1,
                "supplemental generated-symbol definition",
            )

    process = exact_keys(
        contract["process_configs"],
        {"command", "environment", "path", "sha256", "source", "working_directory"},
        "process_configs authority",
    )
    require_exact(
        process["sha256"],
        contract["source_assets"]["process_configs"]["sha256"],
        "process_configs asset digest",
    )
    require_exact(
        process["command"],
        [
            "SOURCE_ROOT/redhat/configs/process_configs.sh",
            "-m",
            "LLVM=1",
            "6.12.0",
            "rhel",
        ],
        "process_configs command",
    )
    process_environment = dict(CAPTURE_ENVIRONMENT)
    process_environment.update(
        {
            "FLAVOR": "rhel",
            "RHJOBS": "1",
            "SPECPACKAGE_NAME": "kernel-rk005-{control,requested}-pass-N",
        }
    )
    require_exact(
        process["environment"], process_environment, "process_configs environment"
    )
    require_exact(
        process["working_directory"],
        "SOURCE_ROOT/redhat/configs",
        "process_configs working directory",
    )
    resolution = exact_keys(
        contract["resolution"],
        {
            "clean_build_directories",
            "comparison",
            "fragment_merge_command",
            "olddefconfig_command",
            "passes",
            "process_configs_required",
        },
        "resolution commands",
    )
    require_exact(resolution["passes"], 2, "resolution pass count")
    require_exact(
        resolution["clean_build_directories"], True, "clean resolution directories"
    )
    require_exact(
        resolution["process_configs_required"], True, "process_configs requirement"
    )
    require_exact(
        resolution["fragment_merge_command"],
        [
            "SOURCE_ROOT/scripts/kconfig/merge_config.sh",
            "-m",
            "-O",
            "MERGE_DIR",
            "MERGE_DIR/.config",
            "FRAGMENT",
        ],
        "fragment merge command",
    )
    require_exact(
        resolution["olddefconfig_command"],
        [
            "make",
            "-C",
            "SOURCE_ROOT",
            "O=BUILD_DIR",
            "ARCH=x86_64",
            "LLVM=1",
            "olddefconfig",
        ],
        "olddefconfig command",
    )
    comparison = str(resolution["comparison"])
    if "complete resolved config bytes" not in comparison or "symbol maps" not in comparison:
        raise ConfigResolutionError("two-pass comparison contract is incomplete")
    if contract["success_blockers"][1].find(
        "CONFIG_RUSTC_HAS_UNNECESSARY_TRANSMUTES"
    ) < 0:
        raise ConfigResolutionError("policy reconciliation blocker is missing")
    if not any(
        "0006 through 0012" in item and "compile probes" in item
        for item in contract["success_blockers"]
    ):
        raise ConfigResolutionError("compatibility compile-scope blocker is missing")
    tool_environment = exact_keys(
        contract["tool_environment"],
        {
            "expected_binary_owners",
            "expected_file_owners",
            "expected_rustc_llvm_version",
            "expected_versions",
            "fixed_environment",
            "llvm_config_authority_blocker",
            "probe_commands",
        },
        "tool environment",
    )
    require_exact(
        tool_environment["fixed_environment"],
        CAPTURE_ENVIRONMENT,
        "fixed capture environment",
    )
    expected_versions = {
        "bindgen": "0.72.1",
        "clang": "21.1.8",
        "llvm": "21.1.8",
        "pahole": "1.31",
        "rustc": "1.92.0",
    }
    require_exact(
        tool_environment["expected_versions"], expected_versions, "tool versions"
    )
    require_exact(
        tool_environment["expected_rustc_llvm_version"],
        "21.1.6",
        "rustc bundled LLVM version",
    )
    expected_probe_commands = dict(PROBE_COMMANDS)
    expected_probe_commands["rust_src_core"] = RUST_SRC_PROBE_COMMAND
    require_exact(
        tool_environment["probe_commands"],
        expected_probe_commands,
        "tool probe commands",
    )
    artifact_by_name = {
        item["name"]: item for item in toolchain.get("direct_artifacts", [])
    }
    expected_owners = {
        "bindgen": artifact_by_name["bindgen-cli"]["nevra"],
        "clang": artifact_by_name["clang"]["nevra"],
        "llvm": "llvm-devel-0:21.1.8-1.el10.x86_64",
        "pahole": artifact_by_name["dwarves"]["nevra"],
        "rustc": artifact_by_name["rust"]["nevra"],
    }
    require_exact(
        tool_environment["expected_binary_owners"], expected_owners, "tool owners"
    )
    require_exact(
        tool_environment["expected_file_owners"],
        {"rust_src_core": artifact_by_name["rust-src"]["nevra"]},
        "tool file owners",
    )
    require_exact(
        artifact_by_name["llvm"]["nevra"],
        "llvm-0:21.1.8-1.el10.x86_64",
        "historical llvm-config owner authority",
    )
    if "llvm-devel-0:21.1.8-1.el10.x86_64" not in str(
        tool_environment["llvm_config_authority_blocker"]
    ):
        raise ConfigResolutionError("LLVM owner reconciliation blocker is missing")
    return contract


def validate_workflow(repo):
    path = safe_repo_file(repo, WORKFLOW_PATH.as_posix(), "config workflow")
    data = path.read_bytes()
    require_exact(
        hashlib.sha256(data).hexdigest(), EXPECTED_WORKFLOW_SHA256, "workflow digest"
    )
    text = data.decode("utf-8")
    required_counts = {
        "python3 scripts/rocky_kernel_config_resolution.py": 2,
        "--phase config-resolution": 1,
        "credit forbidden": 1,
        "compression-level: 0": 1,
        "permissions:\n  contents: read": 1,
        "runs-on: ubuntu-24.04": 1,
        "image: " + CONTAINER_IMAGE: 1,
        "persist-credentials: false": 1,
        "include-hidden-files: true": 1,
    }
    for needle, count in required_counts.items():
        require_exact(text.count(needle), count, "workflow fragment {!r}".format(needle))
    uses = []
    for line in text.splitlines():
        if re.match(r"^\s*uses\s*:", line):
            match = re.fullmatch(r"\s*uses:\s+(\S+)(?:\s+#.*)?", line)
            if match is None:
                raise ConfigResolutionError("workflow action identity is ambiguous")
            uses.append(match.group(1))
    require_exact(uses, EXPECTED_WORKFLOW_USES, "workflow actions")


def validate_identity(head_sha, run_id, run_attempt, repository, container_image):
    if not HEX_SHA1.fullmatch(str(head_sha)):
        raise ConfigResolutionError("GitHub head SHA is malformed")
    if not str(run_id).isdigit() or int(run_id) < 1:
        raise ConfigResolutionError("GitHub run ID is malformed")
    if not str(run_attempt).isdigit() or int(run_attempt) < 1:
        raise ConfigResolutionError("GitHub run attempt is malformed")
    if not GITHUB_REPOSITORY.fullmatch(str(repository)):
        raise ConfigResolutionError("GitHub repository identity is malformed")
    require_exact(container_image, CONTAINER_IMAGE, "container image")
    return {
        "head_sha": head_sha,
        "repository": repository,
        "run_attempt": int(run_attempt),
        "run_id": int(run_id),
    }


def parse_config(path):
    values = {}
    text = regular_file(path, "config").read_text(encoding="utf-8")
    for line in text.splitlines():
        match = CONFIG_VALUE.fullmatch(line)
        if match:
            symbol, value = match.groups()
        else:
            match = CONFIG_UNSET.fullmatch(line)
            if not match:
                continue
            symbol, value = match.group(1), "n"
        if symbol in values:
            raise ConfigResolutionError("duplicate config symbol {}".format(symbol))
        values[symbol] = value
    if not values:
        raise ConfigResolutionError("config contains no symbols")
    return values


def changed_symbols(before, after):
    return [
        {
            "before": before.get(symbol, "<absent>"),
            "after": after.get(symbol, "<absent>"),
            "symbol": symbol,
        }
        for symbol in sorted(set(before) | set(after))
        if before.get(symbol, "<absent>") != after.get(symbol, "<absent>")
    ]


def rpm_file_owner(path):
    command = [
        "rpm",
        "-qf",
        "--qf",
        "%{NAME}-%{EPOCHNUM}:%{VERSION}-%{RELEASE}.%{ARCH}\\n",
        str(path),
    ]
    owner_stdout, owner_stderr = run_command(command, env=CAPTURE_ENVIRONMENT)
    if owner_stderr:
        raise ConfigResolutionError("tool owner query wrote stderr")
    owner_rows = owner_stdout.decode("utf-8").splitlines()
    if len(owner_rows) != 1:
        raise ConfigResolutionError("tool owner query is ambiguous")
    return owner_rows[0], command


def probe_environment(contract):
    results = {}
    tool_environment = contract["tool_environment"]
    for probe_id in sorted(PROBE_COMMANDS):
        command = PROBE_COMMANDS[probe_id]
        binary = shutil.which(command[0], path=CAPTURE_ENVIRONMENT["PATH"])
        if binary is None:
            raise ConfigResolutionError("probe binary is missing: {}".format(command[0]))
        completed = run_command(command, env=CAPTURE_ENVIRONMENT)
        owner, owner_command = rpm_file_owner(Path(binary))
        require_exact(
            owner,
            tool_environment["expected_binary_owners"][probe_id],
            "{} binary owner".format(probe_id),
        )
        results[probe_id] = {
            "binary_path": binary,
            "binary_sha256": sha256_file(Path(binary))[1],
            "command": command,
            "owner_command": owner_command,
            "package_nevra": owner,
            "stderr_sha256": hashlib.sha256(completed[1]).hexdigest(),
            "stdout_sha256": hashlib.sha256(completed[0]).hexdigest(),
            "text": (completed[0] + completed[1]).decode("utf-8", errors="strict"),
        }
    rust_sysroot_command = RUST_SRC_PROBE_COMMAND
    sysroot_stdout, sysroot_stderr = run_command(
        rust_sysroot_command, env=CAPTURE_ENVIRONMENT
    )
    if sysroot_stderr:
        raise ConfigResolutionError("rustc sysroot probe wrote stderr")
    sysroot_rows = sysroot_stdout.decode("utf-8").splitlines()
    if len(sysroot_rows) != 1:
        raise ConfigResolutionError("rustc sysroot probe is ambiguous")
    sysroot = Path(sysroot_rows[0])
    if not sysroot.is_absolute() or not sysroot.is_dir() or sysroot.resolve() != sysroot:
        raise ConfigResolutionError("rustc sysroot is not a canonical directory")
    rust_src_core = regular_file(
        sysroot / "lib/rustlib/src/rust/library/core/src/lib.rs",
        "rust-src core",
    )
    if os.path.commonpath((str(sysroot), str(rust_src_core))) != str(sysroot):
        raise ConfigResolutionError("rust-src core escapes the rustc sysroot")
    rust_src_owner, rust_src_owner_command = rpm_file_owner(rust_src_core)
    require_exact(
        rust_src_owner,
        tool_environment["expected_file_owners"]["rust_src_core"],
        "rust-src core owner",
    )
    results["rust_src_core"] = {
        "command": rust_sysroot_command,
        "file_path": str(rust_src_core),
        "file_sha256": sha256_file(rust_src_core)[1],
        "owner_command": rust_src_owner_command,
        "package_nevra": rust_src_owner,
        "stderr_sha256": hashlib.sha256(sysroot_stderr).hexdigest(),
        "stdout_sha256": hashlib.sha256(sysroot_stdout).hexdigest(),
    }
    rust = results["rustc"]["text"]
    rust_match = re.search(r"(?m)^rustc 1\.92\.0(?:\s|$)", rust)
    llvm_match = re.search(r"(?m)^LLVM version:\s*([0-9]+)\.([0-9]+)\.([0-9]+)", rust)
    if rust_match is None or llvm_match is None:
        raise ConfigResolutionError("rustc probe does not prove Rust 1.92.0 and LLVM")
    version_patterns = {
        "bindgen": r"(?m)^bindgen 0\.72\.1(?:\s|$)",
        "clang": r"(?m)clang version 21\.1\.8(?:\s|$)",
        "llvm": r"(?m)^21\.1\.8$",
        "pahole": r"(?m)^v?1\.31$",
        "rustc": r"(?m)^rustc 1\.92\.0(?:\s|$)",
    }
    for probe_id, pattern in sorted(version_patterns.items()):
        if re.search(pattern, results[probe_id]["text"]) is None:
            raise ConfigResolutionError(
                "{} probe does not prove exact version {}".format(
                    probe_id,
                    tool_environment["expected_versions"][probe_id],
                )
            )
    require_exact(
        "{}.{}.{}".format(*llvm_match.groups()),
        tool_environment["expected_rustc_llvm_version"],
        "rustc LLVM version",
    )
    results["derived"] = {
        "bindgen_version_text": first_line(results["bindgen"]["text"]),
        "pahole_version": numeric_version(results["pahole"]["text"], 100),
        "rustc_llvm_version": canonical_version(llvm_match.groups(), 10000),
        "rustc_version": 109200,
        "rustc_version_text": first_line(results["rustc"]["text"]),
    }
    return results


def first_line(text):
    rows = [row.strip() for row in text.splitlines() if row.strip()]
    if not rows:
        raise ConfigResolutionError("tool probe output is empty")
    return rows[0]


def canonical_version(groups, multiplier):
    major, minor, patch = (int(item) for item in groups)
    if multiplier == 10000:
        return major * 10000 + minor * 100 + patch
    return major * 100000 + minor * 100 + patch


def numeric_version(text, multiplier):
    match = re.search(r"(?:v)?([0-9]+)\.([0-9]+)(?:\.([0-9]+))?", text)
    if match is None:
        raise ConfigResolutionError("tool version is not parseable")
    patch = match.group(3) or "0"
    if multiplier == 100:
        return int(match.group(1)) * 100 + int(match.group(2))
    return canonical_version((match.group(1), match.group(2), patch), multiplier)


def expected_generated_values(probes):
    derived = probes["derived"]
    pahole = derived["pahole_version"]
    rustc = derived["rustc_version"]
    return {
        "CONFIG_BINDGEN_VERSION_TEXT": '"{}"'.format(
            derived["bindgen_version_text"]
        ),
        "CONFIG_PAHOLE_HAS_BTF_TAG": "y" if pahole >= 123 else "n",
        "CONFIG_PAHOLE_HAS_LANG_EXCLUDE": "y" if pahole >= 124 else "n",
        "CONFIG_PAHOLE_HAS_SPLIT_BTF": "y" if pahole >= 119 else "n",
        "CONFIG_PAHOLE_VERSION": str(pahole),
        "CONFIG_RUSTC_HAS_UNNECESSARY_TRANSMUTES": (
            "y" if rustc >= 108800 else "n"
        ),
        "CONFIG_RUSTC_LLVM_VERSION": str(derived["rustc_llvm_version"]),
        "CONFIG_RUSTC_VERSION": str(rustc),
        "CONFIG_RUSTC_VERSION_TEXT": '"{}"'.format(
            derived["rustc_version_text"]
        ),
        "CONFIG_RUST_IS_AVAILABLE": "y",
    }


def validate_config_pair(contract, baseline_path, control_paths, resolved_paths, probes):
    baseline = parse_config(baseline_path)
    controls = [parse_config(path) for path in control_paths]
    resolved = [parse_config(path) for path in resolved_paths]
    if regular_file(control_paths[0], "control pass 1").read_bytes() != regular_file(
        control_paths[1], "control pass 2"
    ).read_bytes():
        raise ConfigResolutionError("independent control resolutions differ byte-for-byte")
    if regular_file(resolved_paths[0], "resolved pass 1").read_bytes() != regular_file(
        resolved_paths[1], "resolved pass 2"
    ).read_bytes():
        raise ConfigResolutionError("independent requested resolutions differ byte-for-byte")
    require_exact(controls[0], controls[1], "control symbol maps")
    require_exact(resolved[0], resolved[1], "resolved symbol maps")

    environment_delta = changed_symbols(baseline, controls[0])
    requested_delta = changed_symbols(controls[0], resolved[0])
    expected_requested = [
        {"before": row["baseline"], "after": row["resolved"], "symbol": row["symbol"]}
        for row in contract["requested_delta"]
    ]
    expected_requested.sort(key=lambda item: item["symbol"])
    requested_existing = [
        row for row in requested_delta if row["before"] != "<absent>"
    ]
    requested_existing.sort(key=lambda item: item["symbol"])
    require_exact(requested_existing, expected_requested, "requested existing-symbol delta")

    generated_contract = contract["generated_environment"]
    generated_allowed = set(generated_contract["historical_policy_symbols"])
    generated_allowed.update(generated_contract["supplemental_symbols"])
    requested_new = [row for row in requested_delta if row["before"] == "<absent>"]
    unexpected_new = sorted(
        row["symbol"] for row in requested_new if row["symbol"] not in generated_allowed
    )
    if unexpected_new:
        raise ConfigResolutionError(
            "requested config introduced unexpected generated symbols: {}".format(
                ", ".join(unexpected_new)
            )
        )
    expected_generated = expected_generated_values(probes)
    generated_results = {}
    for symbol in sorted(generated_allowed):
        actual = resolved[0].get(symbol, "<absent>")
        expected = expected_generated[symbol]
        if actual != expected:
            raise ConfigResolutionError(
                "generated {} differs from tool probe: {!r} != {!r}".format(
                    symbol, actual, expected
                )
            )
        generated_results[symbol] = actual

    assertions = {}
    for symbol, expected in sorted(contract["dependency_symbols"].items()):
        actual = resolved[0].get(symbol, "<absent>")
        if actual != expected:
            raise ConfigResolutionError(
                "dependency {} differs: {!r} != {!r}".format(symbol, actual, expected)
            )
        assertions[symbol] = actual
    for symbol, rule in sorted(contract["conditional_dependencies"].items()):
        actual = resolved[0].get(symbol, "<absent>")
        if actual not in rule["allowed_values"]:
            raise ConfigResolutionError(
                "conditional dependency {} has invalid value {!r}".format(
                    symbol, actual
                )
            )
        if actual == "y" and probes["derived"]["rustc_version"] < rule[
            "rustc_minimum_if_y"
        ]:
            raise ConfigResolutionError(
                "conditional dependency {} requires newer rustc".format(symbol)
            )
        assertions[symbol] = actual
    preserved = {}
    for group, values in sorted(contract["preservation_groups"].items()):
        preserved[group] = {}
        for symbol, expected in sorted(values.items()):
            actual = resolved[0].get(symbol, "<absent>")
            if actual != expected:
                raise ConfigResolutionError(
                    "preserved {} differs: {!r} != {!r}".format(
                        symbol, actual, expected
                    )
                )
            if baseline.get(symbol, "<absent>") != actual:
                raise ConfigResolutionError("preserved {} drifted from baseline".format(symbol))
            preserved[group][symbol] = actual

    return {
        "environment_generated_changes": environment_delta,
        "generated_symbol_results": generated_results,
        "requested_changes": requested_existing,
        "requested_generated_symbols": requested_new,
        "unexpected_generated_symbols": unexpected_new,
    }, {"dependencies": assertions, "preservation_groups": preserved}


def run_command(arguments, cwd=None, env=None, timeout=600):
    if not arguments or not all(isinstance(item, str) and item for item in arguments):
        raise ConfigResolutionError("command arguments are invalid")
    try:
        completed = subprocess.run(
            list(arguments),
            cwd=str(cwd) if cwd is not None else None,
            env=dict(env) if env is not None else None,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ConfigResolutionError("command failed to execute: {}".format(exc))
    if completed.returncode != 0:
        raise ConfigResolutionError(
            "command failed ({}): {}".format(
                completed.returncode,
                completed.stderr.decode("utf-8", errors="replace")[-2000:],
            )
        )
    return completed.stdout, completed.stderr


def verify_asset(path, record, label):
    path = regular_file(path, label)
    size, digest = sha256_file(path)
    require_exact(size, record["size"], label + " size")
    require_exact(digest, record["sha256"], label + " digest")
    return path


def safe_tar_member(member, root):
    name = member.name.rstrip("/")
    parts = name.split("/")
    if (
        not name
        or name.startswith("/")
        or "\\" in name
        or any(part in ("", ".", "..") for part in parts)
        or parts[0] != root
        or member.issym()
        or member.islnk()
        or not (member.isfile() or member.isdir())
    ):
        raise ConfigResolutionError("source archive member is unsafe: {}".format(member.name))


def extract_source(archive, target, root_name):
    try:
        stream = tarfile.open(str(archive), "r:xz")
    except (OSError, tarfile.TarError) as exc:
        raise ConfigResolutionError("cannot open source archive: {}".format(exc))
    with stream:
        members = stream.getmembers()
        if not members:
            raise ConfigResolutionError("source archive is empty")
        for member in members:
            safe_tar_member(member, root_name)
        stream.extractall(str(target))
    source = target / root_name
    if source.is_symlink() or not (source / "Makefile").is_file():
        raise ConfigResolutionError("source archive root is invalid")
    return source


def apply_patch(source, path, fuzz_zero):
    command = [
        "patch",
        "-d",
        str(source),
        "-p1",
        "--batch",
        "--forward",
    ]
    if fuzz_zero:
        command.append("--fuzz=0")
    command.extend(["--no-backup-if-mismatch", "-i", str(path)])
    run_command(command, timeout=300)


def run_resolution(source, baseline, fragment, pass_number, contract):
    process_source = source / contract["process_configs"]["path"]
    verify_asset(
        process_source,
        {
            "sha256": contract["process_configs"]["sha256"],
            "size": contract["source_assets"]["process_configs"]["size"],
        },
        "source process_configs",
    )
    configs = source / "redhat/configs"
    control_name = "kernel-rk005-control-pass-{}".format(pass_number)
    requested_name = "kernel-rk005-requested-pass-{}".format(pass_number)
    control_input = configs / "{}-6.12.0-x86_64-rhel.config".format(
        control_name
    )
    requested_input = configs / "{}-6.12.0-x86_64-rhel.config".format(
        requested_name
    )
    shutil.copyfile(str(baseline), str(control_input))
    control_environment = dict(CAPTURE_ENVIRONMENT)
    control_environment.update(
        {
            "FLAVOR": "rhel",
            "RHJOBS": "1",
            "SPECPACKAGE_NAME": control_name,
        }
    )
    control_process_command = [
        str(process_source),
        "-m",
        "LLVM=1",
        "6.12.0",
        "rhel",
    ]
    run_command(
        control_process_command,
        cwd=configs,
        env=control_environment,
        timeout=1800,
    )
    control_output = configs / control_input.name
    if not control_output.is_file():
        raise ConfigResolutionError("process_configs did not emit the control config")

    merge_dir = source.parent / "fragment-merge"
    merge_dir.mkdir(mode=0o700)
    shutil.copyfile(str(baseline), str(merge_dir / ".config"))
    merge = source / "scripts/kconfig/merge_config.sh"
    merge_command = [
        str(merge),
        "-m",
        "-O",
        str(merge_dir),
        str(merge_dir / ".config"),
        str(fragment),
    ]
    run_command(
        merge_command,
        cwd=source,
        env=CAPTURE_ENVIRONMENT,
        timeout=300,
    )
    shutil.copyfile(str(merge_dir / ".config"), str(requested_input))
    requested_environment = dict(CAPTURE_ENVIRONMENT)
    requested_environment.update(
        {
            "FLAVOR": "rhel",
            "RHJOBS": "1",
            "SPECPACKAGE_NAME": requested_name,
        }
    )
    requested_process_command = [
        str(process_source),
        "-m",
        "LLVM=1",
        "6.12.0",
        "rhel",
    ]
    run_command(
        requested_process_command,
        cwd=configs,
        env=requested_environment,
        timeout=1800,
    )
    requested_output = configs / requested_input.name
    if not requested_output.is_file():
        raise ConfigResolutionError("process_configs did not emit the requested config")
    control_dir = source.parent / "control-build"
    requested_dir = source.parent / "requested-build"
    control_dir.mkdir(mode=0o700)
    requested_dir.mkdir(mode=0o700)
    shutil.copyfile(str(control_output), str(control_dir / ".config"))
    shutil.copyfile(str(requested_output), str(requested_dir / ".config"))
    make_control = [
        "make",
        "-C",
        str(source),
        "O=" + str(control_dir),
        "ARCH=x86_64",
        "LLVM=1",
        "olddefconfig",
    ]
    make_requested = [
        "make",
        "-C",
        str(source),
        "O=" + str(requested_dir),
        "ARCH=x86_64",
        "LLVM=1",
        "olddefconfig",
    ]
    run_command(make_control, env=CAPTURE_ENVIRONMENT, timeout=1800)
    run_command(make_requested, env=CAPTURE_ENVIRONMENT, timeout=1800)
    return {
        "control": control_dir / ".config",
        "control_process_environment": control_environment,
        "control_process_command": control_process_command,
        "merge_command": merge_command,
        "requested": requested_dir / ".config",
        "requested_process_environment": requested_environment,
        "requested_process_command": requested_process_command,
        "requested_command": make_requested,
        "control_command": make_control,
    }


def prepare_output(path):
    if not path.is_absolute():
        raise ConfigResolutionError("output directory must be absolute")
    parent = path.parent
    if parent.is_symlink() or not parent.is_dir() or parent.resolve() != parent:
        raise ConfigResolutionError("output parent is unsafe")
    if path.exists() or path.is_symlink():
        raise ConfigResolutionError("output directory already exists")
    path.mkdir(mode=0o700)
    return path


def write_output(root, name, data):
    relative = PurePosixPath(name)
    if relative.is_absolute() or len(relative.parts) != 1:
        raise ConfigResolutionError("output path is unsafe")
    target = root / name
    if target.exists() or target.is_symlink():
        raise ConfigResolutionError("output already exists: {}".format(name))
    mode = "xb"
    with target.open(mode) as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    target.chmod(0o400)


def write_json(root, name, value):
    write_output(root, name, canonical_json_bytes(value))


def write_sha256sums(root):
    rows = []
    for name in EVIDENCE_NAMES:
        path = root / name
        size, digest = sha256_file(path)
        if size < 1:
            raise ConfigResolutionError("evidence output is empty: {}".format(name))
        rows.append("{}  {}".format(digest, name))
    write_output(root, "SHA256SUMS", ("\n".join(rows) + "\n").encode("ascii"))


def capture(repo, source_assets, output_dir, identity, contract):
    assets = contract["source_assets"]
    archive = verify_asset(
        source_assets / Path(assets["linux_archive"]["path"]).name,
        assets["linux_archive"],
        "Linux archive",
    )
    baseline = verify_asset(
        source_assets / Path(assets["baseline"]["path"]).name,
        assets["baseline"],
        "Rocky baseline config",
    )
    process_asset = verify_asset(
        source_assets / Path(assets["process_configs"]["path"]).name,
        assets["process_configs"],
        "SRPM process_configs",
    )
    debrand = verify_asset(
        source_assets / Path(assets["debrand_patch"]["path"]).name,
        assets["debrand_patch"],
        "Rocky debrand patch",
    )
    fragment = safe_repo_file(repo, CONFIG_FRAGMENT_PATH.as_posix(), "config fragment")
    output = prepare_output(output_dir)
    probes = probe_environment(contract)
    runs = []
    with tempfile.TemporaryDirectory(prefix="rk005-config-") as temporary_name:
        temporary = Path(temporary_name)
        for number in (1, 2):
            run_root = temporary / "pass-{}".format(number)
            run_root.mkdir(mode=0o700)
            source = extract_source(
                archive, run_root, assets["linux_archive"]["root"]
            )
            source_process = source / contract["process_configs"]["path"]
            require_exact(
                source_process.read_bytes(),
                process_asset.read_bytes(),
                "archive/SRPM process_configs bytes",
            )
            apply_patch(source, debrand, False)
            for patch in contract["patch_authority"]["rust_compatibility"]:
                apply_patch(
                    source,
                    safe_repo_file(repo, patch["path"], "compatibility patch"),
                    True,
                )
            runs.append(run_resolution(source, baseline, fragment, number, contract))

        delta, assertions = validate_config_pair(
            contract,
            baseline,
            [runs[0]["control"], runs[1]["control"]],
            [runs[0]["requested"], runs[1]["requested"]],
            probes,
        )
        write_output(output, "baseline.config", baseline.read_bytes())
        write_output(output, "fragment.config", fragment.read_bytes())
        write_output(output, "control-pass-1.config", runs[0]["control"].read_bytes())
        write_output(output, "control-pass-2.config", runs[1]["control"].read_bytes())
        write_output(output, "resolved-pass-1.config", runs[0]["requested"].read_bytes())
        write_output(output, "resolved-pass-2.config", runs[1]["requested"].read_bytes())
        command_manifest = {
            "patches": [
                {"path": row["path"], "sha256": row["sha256"]}
                for row in contract["patch_authority"]["rust_compatibility"]
            ],
            "passes": [
                {
                    "control_olddefconfig": runs[index]["control_command"],
                    "control_process_configs": runs[index][
                        "control_process_command"
                    ],
                    "control_process_environment": runs[index][
                        "control_process_environment"
                    ],
                    "fragment_merge": runs[index]["merge_command"],
                    "requested_process_configs": runs[index][
                        "requested_process_command"
                    ],
                    "requested_process_environment": runs[index][
                        "requested_process_environment"
                    ],
                    "requested_olddefconfig": runs[index]["requested_command"],
                }
                for index in range(2)
            ],
            "schema_version": SCHEMA_VERSION,
        }
        environment = {
            "container_image": CONTAINER_IMAGE,
            "fixed_environment": CAPTURE_ENVIRONMENT,
            "github": identity,
            "probes": probes,
            "schema_version": SCHEMA_VERSION,
        }
        blockers = {
            "gate_claims": contract["gate_claims"],
            "success_blockers": contract["success_blockers"],
        }
        write_json(output, "commands.json", command_manifest)
        write_json(output, "environment.json", environment)
        write_json(output, "config-delta.json", delta)
        write_json(output, "dependency-assertions.json", assertions)
        write_json(output, "blockers.json", blockers)
        manifests = []
        for name in EVIDENCE_NAMES[:-1]:
            path = output / name
            manifests.append(
                {"path": name, "sha256": sha256_file(path)[1], "size": path.stat().st_size}
            )
        checkpoint = {
            "credit_eligible": False,
            "gate_claims": contract["gate_claims"],
            "github": identity,
            "manifests": manifests,
            "phase": PHASE_ID,
            "schema_version": SCHEMA_VERSION,
            "two_independent_resolutions_identical": True,
        }
        write_json(output, "checkpoint.json", checkpoint)
    write_sha256sums(output)


def parse_args(argv):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[1])
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--check", action="store_true")
    modes.add_argument("--capture", action="store_true")
    parser.add_argument("--phase", choices=[PHASE_ID])
    parser.add_argument("--source-assets", type=Path)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--github-head-sha")
    parser.add_argument("--github-run-id")
    parser.add_argument("--github-run-attempt")
    parser.add_argument("--github-repository")
    parser.add_argument("--container-image")
    return parser.parse_args(argv)


def main(argv):
    args = parse_args(argv)
    repo = args.repo.resolve()
    try:
        contract = validate_contract(repo)
        validate_workflow(repo)
        run_only = (
            args.phase,
            args.source_assets,
            args.output_dir,
            args.github_head_sha,
            args.github_run_id,
            args.github_run_attempt,
            args.github_repository,
            args.container_image,
        )
        if args.check:
            if any(item is not None for item in run_only):
                raise ConfigResolutionError("--check rejects capture-only arguments")
            print("RK-005 config-resolution contract verified; gate credit remains forbidden")
            return 0
        required = {
            "--phase": args.phase,
            "--source-assets": args.source_assets,
            "--output-dir": args.output_dir,
            "--github-head-sha": args.github_head_sha,
            "--github-run-id": args.github_run_id,
            "--github-run-attempt": args.github_run_attempt,
            "--github-repository": args.github_repository,
            "--container-image": args.container_image,
        }
        missing = [key for key, value in required.items() if value is None]
        if missing:
            raise ConfigResolutionError(
                "capture requires {}".format(", ".join(missing))
            )
        require_exact(args.phase, PHASE_ID, "capture phase")
        identity = validate_identity(
            args.github_head_sha,
            args.github_run_id,
            args.github_run_attempt,
            args.github_repository,
            args.container_image,
        )
        capture(
            repo,
            regular_directory(args.source_assets, "source assets"),
            args.output_dir,
            identity,
            contract,
        )
        print("captured deterministic config evidence; RK-005 credit remains forbidden")
        return 0
    except (ConfigResolutionError, OSError, UnicodeError, ValueError) as exc:
        print("Rocky config-resolution error: {}".format(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
