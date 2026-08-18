#!/usr/bin/env python3
"""Fail-closed tests for RK-005 deterministic config resolution."""

from __future__ import print_function

import ast
import copy
import hashlib
import io
import json
import os
import re
import subprocess
import sys
import tarfile
import tempfile
import unittest
from unittest import mock
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import rocky_kernel_config_resolution_v2 as resolution  # noqa: E402


def write_config(path, values):
    lines = []
    for symbol, value in sorted(values.items()):
        if value == "n":
            lines.append("# {} is not set".format(symbol))
        else:
            lines.append("{}={}".format(symbol, value))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def synthetic_maps(contract):
    baseline = {}
    for row in contract["requested_delta"]:
        baseline[row["symbol"]] = row["baseline"]
    for group in contract["preservation_groups"].values():
        baseline.update(group)
    control = dict(baseline)
    control.update(
        {
            "CONFIG_CALL_PADDING": "y",
            "CONFIG_PAHOLE_HAS_BTF_TAG": "y",
            "CONFIG_PAHOLE_HAS_LANG_EXCLUDE": "y",
            "CONFIG_PAHOLE_HAS_SPLIT_BTF": "y",
            "CONFIG_PAHOLE_VERSION": "131",
            "CONFIG_RUSTC_HAS_UNNECESSARY_TRANSMUTES": "y",
            "CONFIG_RUSTC_LLVM_VERSION": "210106",
            "CONFIG_RUSTC_VERSION": "109200",
            "CONFIG_RUST_IS_AVAILABLE": "y",
        }
    )
    control.update(contract["dependency_symbols"])
    # Rocky process_configs may omit a dependency-hidden disabled bool instead
    # of retaining an explicit ``# CONFIG_RUST is not set`` line.
    control.pop("CONFIG_RUST", None)
    control["CONFIG_MODVERSIONS"] = "y"
    control["CONFIG_ASM_MODVERSIONS"] = "y"
    requested = dict(control)
    requested.pop("CONFIG_ASM_MODVERSIONS")
    requested.update(
        {
            "CONFIG_BINDGEN_VERSION_TEXT": '"bindgen 0.72.1"',
            "CONFIG_RUST": "y",
            "CONFIG_MODVERSIONS": "n",
            "CONFIG_RUSTC_VERSION_TEXT": '"rustc 1.92.0 (fixture)"',
        }
    )
    for symbol in (
        "CONFIG_BLK_DEV_RUST_NULL",
        "CONFIG_DRM_NOVA",
        "CONFIG_RUST_BUILD_ASSERT_ALLOW",
        "CONFIG_RUST_DEBUG_ASSERTIONS",
        "CONFIG_RUST_FW_LOADER_ABSTRACTIONS",
        "CONFIG_RUST_OVERFLOW_CHECKS",
        "CONFIG_RUST_PHYLIB_ABSTRACTIONS",
        "CONFIG_SAMPLES_RUST",
    ):
        requested[symbol] = "n"
    return baseline, control, requested


def synthetic_probes():
    return {
        "derived": {
            "bindgen_version_text": "bindgen 0.72.1",
            "pahole_version": 131,
            "rustc_llvm_version": 210106,
            "rustc_version": 109200,
            "rustc_version_text": "rustc 1.92.0 (fixture)",
        }
    }


def add_tar_directory(stream, name, mode=0o755):
    member = tarfile.TarInfo(name)
    member.type = tarfile.DIRTYPE
    member.mode = mode
    member.mtime = 123456789
    stream.addfile(member)


def add_tar_file(stream, name, data, mode=0o644):
    member = tarfile.TarInfo(name)
    member.type = tarfile.REGTYPE
    member.mode = mode
    member.mtime = 123456789
    member.size = len(data)
    stream.addfile(member, io.BytesIO(data))


def write_source_archive(path, changes_target="process/changes.rst"):
    with tarfile.open(str(path), "w:xz") as stream:
        add_tar_directory(stream, "linux")
        add_tar_file(stream, "linux/Makefile", b"all:\n\t@true\n", 0o755)
        add_tar_file(stream, "linux/COPYING", b"fixture license\n")
        add_tar_directory(stream, "linux/Documentation")
        add_tar_directory(stream, "linux/Documentation/process")
        add_tar_file(
            stream,
            "linux/Documentation/process/changes.rst",
            b"fixture changes\n",
        )
        add_tar_directory(stream, "linux/arch")
        add_tar_directory(stream, "linux/arch/arm64")
        add_tar_directory(stream, "linux/arch/arm64/tools")
        add_tar_directory(stream, "linux/scripts")
        add_tar_file(stream, "linux/scripts/syscall.tbl", b"fixture syscall\n")
        changes = tarfile.TarInfo("linux/Documentation/Changes")
        changes.type = tarfile.SYMTYPE
        changes.linkname = changes_target
        changes.mtime = 123456789
        stream.addfile(changes)
        syscall = tarfile.TarInfo("linux/arch/arm64/tools/syscall_64.tbl")
        syscall.type = tarfile.SYMTYPE
        syscall.linkname = "../../../scripts/syscall.tbl"
        syscall.mtime = 123456789
        stream.addfile(syscall)
        copying = tarfile.TarInfo("linux/COPYING.hard")
        copying.type = tarfile.LNKTYPE
        copying.linkname = "linux/COPYING"
        copying.mtime = 123456789
        stream.addfile(copying)


def local_patch_contract_row():
    path = REPO_ROOT / resolution.LOCAL_COMPATIBILITY_PATCH
    return {
        "failure_evidence": dict(
            resolution.LOCAL_COMPATIBILITY_FAILURE_EVIDENCE
        ),
        "license": resolution.LOCAL_COMPATIBILITY_LICENSE,
        "local_origin": resolution.LOCAL_COMPATIBILITY_ORIGIN,
        "path": resolution.LOCAL_COMPATIBILITY_PATCH,
        "rocky_base": resolution.LOCAL_COMPATIBILITY_ROCKY_BASE,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "stable_commit": None,
        "upstream_commit": None,
    }


def allocator_patch_contract_row():
    path = REPO_ROOT / resolution.ALLOC_SHIM_COMPATIBILITY_PATCH
    return {
        "failure_evidence": dict(resolution.ALLOC_SHIM_FAILURE_EVIDENCE),
        "license": resolution.ALLOC_SHIM_LICENSE,
        "linux_reference": dict(resolution.ALLOC_SHIM_LINUX_REFERENCE),
        "local_origin": resolution.ALLOC_SHIM_LOCAL_ORIGIN,
        "path": resolution.ALLOC_SHIM_COMPATIBILITY_PATCH,
        "postimages": [dict(row) for row in resolution.ALLOC_SHIM_POSTIMAGES],
        "preimages": [dict(row) for row in resolution.ALLOC_SHIM_PREIMAGES],
        "rocky_base": resolution.ALLOC_SHIM_ROCKY_BASE,
        "rust_reference": dict(resolution.ALLOC_SHIM_RUST_REFERENCE),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "stable_commit": None,
        "upstream_commit": None,
    }


class LocalPatchProvenanceTests(unittest.TestCase):
    def setUp(self):
        path = REPO_ROOT / resolution.LOCAL_COMPATIBILITY_PATCH
        self.text = path.read_text(encoding="utf-8")
        self.row = local_patch_contract_row()
        self.index = resolution.EXPECTED_COMPATIBILITY_PATCHES.index(
            resolution.LOCAL_COMPATIBILITY_PATCH
        )

    def validate(self, row=None, text=None):
        resolution.validate_compatibility_patch_provenance(
            self.row if row is None else row,
            self.text if text is None else text,
            self.index,
        )

    def test_local_origin_and_failure_evidence_are_accepted(self):
        self.validate()

    def test_local_patch_does_not_claim_an_upstream_or_stable_commit(self):
        for field in ("upstream_commit", "stable_commit"):
            with self.subTest(field=field):
                row = copy.deepcopy(self.row)
                row[field] = "1" * 40
                with self.assertRaises(resolution.ConfigResolutionError):
                    self.validate(row=row)
        for header in ("Upstream-Commit", "Stable-Commit"):
            with self.subTest(header=header):
                text = self.text.replace(
                    "Local-Origin:",
                    "{}: {}\nLocal-Origin:".format(header, "1" * 40),
                    1,
                )
                with self.assertRaisesRegex(
                    resolution.ConfigResolutionError, "must not claim"
                ):
                    self.validate(text=text)

    def test_every_local_provenance_header_is_required_exactly_once(self):
        headers = (
            "Local-Origin",
            "Rocky-Base",
            "Failure-Run",
            "Failure-Job",
            "Failure-Artifact",
            "Failure-Commit",
            "Failure-Phase",
            "Failure-Exit-Code",
            "Failure-Log-SHA256",
            "Failure-Log-Bytes",
            "License",
        )
        for header in headers:
            with self.subTest(header=header):
                missing = re.sub(
                    r"(?m)^{}: .*\n".format(re.escape(header)),
                    "",
                    self.text,
                    count=1,
                )
                with self.assertRaises(resolution.ConfigResolutionError):
                    self.validate(text=missing)
                matching = re.search(
                    r"(?m)^{}: .*\n".format(re.escape(header)), self.text
                )
                self.assertIsNotNone(matching)
                duplicate = self.text.replace(
                    matching.group(0), matching.group(0) * 2, 1
                )
                with self.assertRaises(resolution.ConfigResolutionError):
                    self.validate(text=duplicate)

    def test_local_contract_metadata_is_exact(self):
        for field in ("license", "local_origin", "path", "rocky_base"):
            with self.subTest(field=field):
                row = copy.deepcopy(self.row)
                row[field] += "-drift"
                with self.assertRaises(resolution.ConfigResolutionError):
                    self.validate(row=row)

    def test_local_contract_failure_evidence_is_exact(self):
        for field in resolution.LOCAL_COMPATIBILITY_FAILURE_EVIDENCE:
            with self.subTest(field=field):
                row = copy.deepcopy(self.row)
                row["failure_evidence"][field] = None
                with self.assertRaisesRegex(
                    resolution.ConfigResolutionError, "failure evidence changed"
                ):
                    self.validate(row=row)


class AllocatorPatchProvenanceTests(unittest.TestCase):
    def setUp(self):
        path = REPO_ROOT / resolution.ALLOC_SHIM_COMPATIBILITY_PATCH
        self.text = path.read_text(encoding="utf-8")
        self.row = allocator_patch_contract_row()
        self.index = resolution.EXPECTED_COMPATIBILITY_PATCHES.index(
            resolution.ALLOC_SHIM_COMPATIBILITY_PATCH
        )

    def validate(self, row=None, text=None):
        resolution.validate_compatibility_patch_provenance(
            self.row if row is None else row,
            self.text if text is None else text,
            self.index,
        )

    def test_allocator_provenance_is_accepted(self):
        self.validate()

    def test_allocator_provenance_and_preimages_are_fail_closed(self):
        row = copy.deepcopy(self.row)
        row["preimages"][0]["sha256"] = "0" * 64
        with self.assertRaises(resolution.ConfigResolutionError):
            self.validate(row=row)
        text = self.text.replace("Observed-Run-ID: 32082343363", "Observed-Run-ID: 1", 1)
        with self.assertRaises(resolution.ConfigResolutionError):
            self.validate(text=text)
        text = self.text.replace(
            "+#![allow(internal_features)]",
            "+#![allow(warnings)]",
            1,
        )
        with self.assertRaises(resolution.ConfigResolutionError):
            self.validate(text=text)


class RepositoryContractTests(unittest.TestCase):
    def assert_contract_mutation_rejected(self, mutate, pattern):
        contract = resolution.validate_contract(REPO_ROOT)
        mutate(contract)
        with tempfile.TemporaryDirectory(dir=str(REPO_ROOT)) as temporary:
            path = Path(temporary) / "contract.json"
            data = (
                json.dumps(contract, indent=2, sort_keys=True) + "\n"
            ).encode("utf-8")
            path.write_bytes(data)
            relative = path.relative_to(REPO_ROOT)
            with mock.patch.object(resolution, "CONTRACT_PATH", relative), mock.patch.object(
                resolution,
                "EXPECTED_CONTRACT_SHA256",
                hashlib.sha256(data).hexdigest(),
            ):
                with self.assertRaisesRegex(
                    resolution.ConfigResolutionError, pattern
                ):
                    resolution.validate_contract(REPO_ROOT)

    def test_source_cleanup_is_ordered_after_processed_configs_are_copied(self):
        contract = resolution.validate_contract(REPO_ROOT)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "linux"
            configs = source / "redhat" / "configs"
            configs.mkdir(parents=True)
            (configs / "process_configs.sh").write_text(
                "#!/bin/sh\nexit 0\n", encoding="utf-8"
            )
            (source / "scripts" / "kconfig").mkdir(parents=True)
            baseline = root / "baseline.config"
            fragment = root / "fragment.config"
            baseline.write_text("# x86_64\n# CONFIG_RUST is not set\n", encoding="utf-8")
            fragment.write_text("CONFIG_RUST=y\n", encoding="utf-8")
            commands = []

            def fake_run_command(arguments, cwd=None, env=None, timeout=600):
                commands.append(list(arguments))
                if arguments[-1] == "rustavailable":
                    return b"Rust is available!\n", b""
                return b"", b""

            original_run_command = resolution.run_command
            original_verify_asset = resolution.verify_asset
            resolution.run_command = fake_run_command
            resolution.verify_asset = lambda path, record, label: Path(path)
            try:
                result = resolution.run_resolution(
                    source, baseline, fragment, 1, contract
                )
            finally:
                resolution.run_command = original_run_command
                resolution.verify_asset = original_verify_asset

            self.assertEqual(commands[3], result["source_cleanup_command"])
            self.assertEqual(commands[3][-3:], ["ARCH=x86_64", "LLVM=1", "mrproper"])
            self.assertEqual(commands[4], result["control_command"])
            self.assertEqual(commands[5], result["requested_command"])
            self.assertEqual(commands[6], result["rustavailable"]["command"])
            self.assertEqual(commands[6][-1], "rustavailable")
            self.assertEqual(result["rustavailable"]["success_line_count"], 1)
            self.assertEqual(result["control"].read_bytes(), baseline.read_bytes())
            self.assertEqual(result["requested"].read_bytes(), baseline.read_bytes())

    def test_contract_and_workflow_validate_without_credit(self):
        contract = resolution.validate_contract(REPO_ROOT)
        resolution.validate_workflow(REPO_ROOT)
        self.assertEqual(resolution.SCHEMA_VERSION, 2)
        self.assertEqual(contract["schema_version"], 2)
        self.assertEqual(contract["phase_id"], "config-resolution-v2")
        self.assertFalse(any(contract["gate_claims"].values()))
        self.assertIn("never awards", contract["claim_scope"])
        self.assertIn(
            "CONFIG_RUSTC_HAS_UNNECESSARY_TRANSMUTES",
            contract["generated_environment"]["policy_symbols"],
        )
        self.assertEqual(
            contract["tool_environment"]["llvm_config_owner_policy"][
                "expected_package_nevra"
            ],
            "llvm-devel-0:21.1.8-1.el10.x86_64",
        )
        self.assertEqual(
            contract["preservation_groups"]["warning_policy"]["CONFIG_WERROR"],
            "y",
        )

    def test_claim_scope_and_every_success_blocker_are_exact(self):
        self.assert_contract_mutation_rejected(
            lambda contract: contract.update(
                {
                    "claim_scope": contract["claim_scope"]
                    + " Exception: credit may be awarded by this phase."
                }
            ),
            "claim scope changed",
        )
        contract = resolution.validate_contract(REPO_ROOT)
        for index in range(len(contract["success_blockers"])):
            with self.subTest(removed_blocker=index):
                self.assert_contract_mutation_rejected(
                    lambda value, row=index: value["success_blockers"].pop(row),
                    "success blockers changed",
                )
        self.assert_contract_mutation_rejected(
            lambda contract: contract["success_blockers"].reverse(),
            "success blockers changed",
        )
        self.assert_contract_mutation_rejected(
            lambda contract: contract["success_blockers"].append(
                "A non-authoritative extra blocker."
            ),
            "success blockers changed",
        )

    def test_authority_bindings_and_classification_text_are_exact(self):
        for binding in ("config_policy", "source_lock", "toolchain_lock"):
            with self.subTest(binding=binding):
                self.assert_contract_mutation_rejected(
                    lambda contract, name=binding: contract[name].update(
                        {"path": "host-kernel/rocky/arbitrary.json"}
                    ),
                    "{} binding changed".format(binding.replace("_", " ")),
                )
        self.assert_contract_mutation_rejected(
            lambda contract: contract["generated_environment"].update(
                {"classification": "All generated drift is acceptable."}
            ),
            "generated classification changed",
        )
        self.assert_contract_mutation_rejected(
            lambda contract: contract["generated_environment"].update(
                {"classification": False}
            ),
            "generated classification changed",
        )
        self.assert_contract_mutation_rejected(
            lambda contract: contract["resolution"].update(
                {
                    "comparison": (
                        contract["resolution"]["comparison"]
                        + " Symbol mismatches may be ignored."
                    )
                }
            ),
            "resolution comparison changed",
        )
        self.assert_contract_mutation_rejected(
            lambda contract: contract["resolution"].update(
                {"comparison": ["complete resolved config bytes", "symbol maps"]}
            ),
            "resolution comparison changed",
        )

    def test_generated_policy_and_direct_artifact_duplicates_fail_closed(self):
        policy, _ = resolution.read_json(
            REPO_ROOT / resolution.CONFIG_POLICY_PATH, "config policy"
        )
        duplicated_policy = copy.deepcopy(policy)
        duplicated_policy["verification_evidence"]["olddefconfig_delta"][
            "generated_symbol_allowlist"
        ].append(
            duplicated_policy["verification_evidence"]["olddefconfig_delta"][
                "generated_symbol_allowlist"
            ][0]
        )
        with self.assertRaisesRegex(
            resolution.ConfigResolutionError,
            "bound platform authority is invalid",
        ):
            resolution.validate_platform_authorities(
                REPO_ROOT,
                resolution.read_json(
                    REPO_ROOT / resolution.TOOLCHAIN_LOCK_PATH, "toolchain lock"
                )[0],
                duplicated_policy,
                (REPO_ROOT / resolution.CONFIG_FRAGMENT_PATH).read_bytes(),
            )

        toolchain, _ = resolution.read_json(
            REPO_ROOT / resolution.TOOLCHAIN_LOCK_PATH, "toolchain lock"
        )
        duplicated_toolchain = copy.deepcopy(toolchain)
        duplicated_toolchain["direct_artifacts"].append(
            copy.deepcopy(duplicated_toolchain["direct_artifacts"][0])
        )
        with self.assertRaisesRegex(
            resolution.ConfigResolutionError, "bound platform authority is invalid"
        ):
            resolution.validate_platform_authorities(
                REPO_ROOT,
                duplicated_toolchain,
                policy,
                (REPO_ROOT / resolution.CONFIG_FRAGMENT_PATH).read_bytes(),
            )

        source_drift = copy.deepcopy(policy)
        source_drift["dependency_contract"]["requirements"][0]["source"] = ""
        with self.assertRaisesRegex(
            resolution.ConfigResolutionError, "bound platform authority is invalid"
        ):
            resolution.validate_platform_authorities(
                REPO_ROOT,
                toolchain,
                source_drift,
                (REPO_ROOT / resolution.CONFIG_FRAGMENT_PATH).read_bytes(),
            )

    def test_source_assets_and_process_authority_are_exact(self):
        mutations = (
            lambda contract: contract["source_assets"]["baseline"].update(
                {"path": "SOURCES/kernel-aarch64-rhel.config"}
            ),
            lambda contract: contract["source_assets"]["debrand_patch"].update(
                {"sha256": "0" * 64}
            ),
            lambda contract: contract["source_assets"]["linux_archive"].update(
                {"root": "arbitrary-linux"}
            ),
            lambda contract: contract["source_assets"]["process_configs"].update(
                {"size": 1}
            ),
            lambda contract: contract["source_assets"]["baseline"].update(
                {"unknown": "accepted before closure"}
            ),
        )
        for index, mutation in enumerate(mutations):
            with self.subTest(source_asset_mutation=index):
                self.assert_contract_mutation_rejected(
                    mutation, "source assets changed"
                )
        self.assert_contract_mutation_rejected(
            lambda contract: contract["process_configs"].update(
                {"path": "scripts/arbitrary-process-configs.sh"}
            ),
            "process_configs path changed",
        )
        self.assert_contract_mutation_rejected(
            lambda contract: contract["process_configs"].update(
                {"source": "arbitrary script with matching digest"}
            ),
            "process_configs source changed",
        )

    def test_rocky_series_cannot_retarget_an_arbitrary_safe_file(self):
        arbitrary = REPO_ROOT / resolution.CONFIG_POLICY_PATH
        arbitrary_digest = hashlib.sha256(arbitrary.read_bytes()).hexdigest()
        self.assert_contract_mutation_rejected(
            lambda contract: contract["patch_authority"].update(
                {
                    "rocky_series": {
                        "path": resolution.CONFIG_POLICY_PATH.as_posix(),
                        "sha256": arbitrary_digest,
                    }
                }
            ),
            "Rocky patch series binding changed",
        )

    def test_preservation_and_dependency_mappings_are_closed(self):
        preservation_mutations = (
            lambda contract: contract["preservation_groups"][
                "module_signing"
            ].pop("CONFIG_MODULE_SIG_FORCE"),
            lambda contract: contract["preservation_groups"][
                "module_signing"
            ].update({"CONFIG_MODULE_SIG_FORCE": "y"}),
            lambda contract: contract["preservation_groups"][
                "module_signing"
            ].update({"CONFIG_UNBOUND_EXTRA": "n"}),
        )
        for index, mutation in enumerate(preservation_mutations):
            with self.subTest(preservation_mutation=index):
                self.assert_contract_mutation_rejected(
                    mutation, "preservation groups changed"
                )

        dependency_mutations = (
            lambda contract: contract["dependency_symbols"].pop(
                "CONFIG_HAVE_RUST"
            ),
            lambda contract: contract["dependency_symbols"].update(
                {"CONFIG_HAVE_RUST": "n"}
            ),
            lambda contract: contract["dependency_symbols"].update(
                {"CONFIG_UNBOUND_EXTRA": "y"}
            ),
        )
        for index, mutation in enumerate(dependency_mutations):
            with self.subTest(dependency_mutation=index):
                self.assert_contract_mutation_rejected(
                    mutation, "dependency symbols changed"
                )

    def test_contract_binds_source_config_toolchain_and_patch_bytes(self):
        contract = resolution.validate_contract(REPO_ROOT)
        for binding in (
            contract["source_lock"],
            contract["toolchain_lock"],
            contract["config_policy"],
        ):
            path = REPO_ROOT / binding["path"]
            self.assertEqual(
                hashlib.sha256(path.read_bytes()).hexdigest(), binding["sha256"]
            )
        self.assertEqual(23, len(contract["patch_authority"]["rust_compatibility"]))
        self.assertEqual(
            [row["path"] for row in contract["patch_authority"]["rust_compatibility"]],
            resolution.EXPECTED_COMPATIBILITY_PATCHES,
        )
        self.assertEqual(
            contract["patch_authority"]["configuration_effects"][
                "generated_symbols"
            ],
            {
                "CONFIG_RUSTC_HAS_UNNECESSARY_TRANSMUTES": (
                    "host-kernel/rocky/patches/"
                    "0005-rust-clean-unnecessary-transmutes-lint.patch"
                )
            },
        )
        self.assertEqual(
            len(
                contract["patch_authority"]["configuration_effects"][
                    "no_config_symbol_changes"
                ]
            ),
            22,
        )
        self.assertEqual(
            contract["patch_authority"]["rust_compatibility"][-2],
            local_patch_contract_row(),
        )
        self.assertEqual(
            contract["patch_authority"]["rust_compatibility"][-1],
            allocator_patch_contract_row(),
        )
        objtool_patch = contract["patch_authority"]["rust_compatibility"][-3]
        self.assertEqual(
            objtool_patch["observed_failure"],
            resolution.EXPECTED_OBJTOOL_NORETURN_FAILURE,
        )
        self.assertEqual(
            objtool_patch["preimage"],
            resolution.EXPECTED_OBJTOOL_NORETURN_PREIMAGE,
        )
        self.assertEqual(
            objtool_patch["postimage"],
            resolution.EXPECTED_OBJTOOL_NORETURN_POSTIMAGE,
        )
        self.assertNotIn("upstream_commit", objtool_patch)
        self.assertNotIn("stable_commit", objtool_patch)
        self.assertEqual(
            contract["tool_environment"]["expected_file_owners"]["rust_src_core"],
            "rust-src-0:1.92.0-1.el10.noarch",
        )
        self.assertEqual(
            contract["tool_environment"]["probe_commands"]["rust_src_core"],
            ["rustc", "--print", "sysroot"],
        )
        self.assertEqual(
            contract["tool_environment"]["expected_rustc_llvm_version"],
            "21.1.6",
        )
        self.assertEqual(
            contract["tool_environment"]["expected_versions"]["llvm"],
            "21.1.8",
        )
        self.assertEqual(
            contract["tool_environment"]["expected_versions"]["lld"],
            "21.1.8",
        )
        self.assertEqual(
            contract["tool_environment"]["expected_binary_owners"]["lld"],
            "lld-0:21.1.8-1.el10.x86_64",
        )
        self.assertEqual(
            contract["tool_environment"]["probe_commands"]["lld"],
            ["ld.lld", "--version"],
        )
        self.assertNotEqual(
            contract["tool_environment"]["expected_rustc_llvm_version"],
            contract["tool_environment"]["expected_versions"]["llvm"],
        )
        self.assertEqual(
            contract["resolution"]["olddefconfig_command"][-3:],
            ["ARCH=x86_64", "LLVM=1", "olddefconfig"],
        )
        self.assertEqual(
            contract["resolution"]["source_cleanup_command"],
            [
                "make",
                "-C",
                "SOURCE_ROOT",
                "ARCH=x86_64",
                "LLVM=1",
                "mrproper",
            ],
        )
        self.assertEqual(
            contract["resolution"]["rustavailable"],
            {
                "command": [
                    "make",
                    "-C",
                    "SOURCE_ROOT",
                    "O=REQUESTED_BUILD_DIR",
                    "ARCH=x86_64",
                    "LLVM=1",
                    "rustavailable",
                ],
                "passes": 2,
                "required_stdout_line": "Rust is available!",
                "stderr_must_be_empty": True,
            },
        )
        self.assertEqual(
            contract["process_configs"]["sha256"],
            "23501d7f0709000203940749953be512a36c55bd857ba35309224f902ed1e791",
        )

    def test_requested_delta_and_preservation_are_explicit(self):
        contract = resolution.validate_contract(REPO_ROOT)
        self.assertEqual(
            contract["requested_delta"],
            [
                {"baseline": "n", "resolved": "y", "symbol": "CONFIG_RUST"},
                {
                    "baseline": "y",
                    "resolved": "n",
                    "symbol": "CONFIG_MODVERSIONS",
                },
            ],
        )
        self.assertEqual(
            contract["derived_delta"],
            [
                {
                    "baseline": "y",
                    "depends_on": "CONFIG_MODVERSIONS",
                    "reason": (
                        "CONFIG_ASM_MODVERSIONS is visible only when "
                        "CONFIG_MODVERSIONS is enabled."
                    ),
                    "resolved": "n",
                    "symbol": "CONFIG_ASM_MODVERSIONS",
                }
            ],
        )
        self.assertEqual(
            contract["preservation_groups"]["btf_debug"]["CONFIG_DEBUG_INFO_BTF"],
            "y",
        )
        self.assertEqual(
            contract["preservation_groups"]["module_signing"]["CONFIG_MODULE_SIG"],
            "y",
        )

    def test_cli_check_and_capture_argument_boundary(self):
        self.assertEqual(resolution.main(["--repo", str(REPO_ROOT), "--check"]), 0)
        self.assertEqual(
            resolution.main(
                [
                    "--repo",
                    str(REPO_ROOT),
                    "--check",
                    "--phase",
                    "config-resolution-v2",
                ]
            ),
            2,
        )

    def test_script_and_tests_parse_as_python_3_6(self):
        for relative in (
            "scripts/rocky_kernel_config_resolution_v2.py",
            "scripts/tests/test_rocky_kernel_config_resolution.py",
        ):
            source = (REPO_ROOT / relative).read_text(encoding="utf-8")
            try:
                tree = ast.parse(source, filename=relative, feature_version=(3, 6))
            except TypeError:
                tree = ast.parse(source, filename=relative, feature_version=6)
            self.assertIsNotNone(tree)
            self.assertNotIn("from __future__ import " + "annotations", source)
            self.assertNotRegex(source, r"\b(?:list|dict|set|tuple)\[[^\]]")
            self.assertNotRegex(source, r"\s\|\sNone\b")


class ConfigClassificationTests(unittest.TestCase):
    def setUp(self):
        self.contract = resolution.validate_contract(REPO_ROOT)

    def write_fixture(
        self,
        root,
        baseline_mutation=None,
        control_mutation=None,
        requested_mutation=None,
        shared_mutation=None,
    ):
        baseline, control, requested = synthetic_maps(self.contract)
        if baseline_mutation:
            baseline_mutation(baseline)
        if shared_mutation:
            shared_mutation(control)
            shared_mutation(requested)
        if control_mutation:
            control_mutation(control)
        if requested_mutation:
            requested_mutation(requested)
        paths = {
            "baseline": root / "baseline.config",
            "control1": root / "control1.config",
            "control2": root / "control2.config",
            "resolved1": root / "resolved1.config",
            "resolved2": root / "resolved2.config",
        }
        write_config(paths["baseline"], baseline)
        write_config(paths["control1"], control)
        write_config(paths["control2"], control)
        write_config(paths["resolved1"], requested)
        write_config(paths["resolved2"], requested)
        return paths

    def validate(self, paths):
        return resolution.validate_config_pair(
            self.contract,
            paths["baseline"],
            [paths["control1"], paths["control2"]],
            [paths["resolved1"], paths["resolved2"]],
            synthetic_probes(),
        )

    def test_exact_requested_environment_and_preservation_partition_passes(self):
        with tempfile.TemporaryDirectory() as temporary:
            paths = self.write_fixture(Path(temporary))
            delta, assertions = self.validate(paths)
            self.assertEqual(
                [row["symbol"] for row in delta["requested_changes"]],
                ["CONFIG_MODVERSIONS", "CONFIG_RUST"],
            )
            self.assertEqual(
                delta["derived_changes"],
                [
                    {
                        "after": "<absent>",
                        "before": "y",
                        "symbol": "CONFIG_ASM_MODVERSIONS",
                    }
                ],
            )
            self.assertNotIn(
                "CONFIG_RUST_DEBUG_ASSERTIONS",
                [row["symbol"] for row in delta["requested_generated_symbols"]],
            )
            self.assertEqual(
                [row["symbol"] for row in delta["requested_generated_symbols"]],
                [
                    "CONFIG_BINDGEN_VERSION_TEXT",
                    "CONFIG_RUSTC_VERSION_TEXT",
                ],
            )
            self.assertEqual(
                [row["symbol"] for row in delta["representation_changes"]],
                [
                    "CONFIG_BLK_DEV_RUST_NULL",
                    "CONFIG_DRM_NOVA",
                    "CONFIG_RUST_BUILD_ASSERT_ALLOW",
                    "CONFIG_RUST_DEBUG_ASSERTIONS",
                    "CONFIG_RUST_FW_LOADER_ABSTRACTIONS",
                    "CONFIG_RUST_OVERFLOW_CHECKS",
                    "CONFIG_RUST_PHYLIB_ABSTRACTIONS",
                    "CONFIG_SAMPLES_RUST",
                ],
            )
            self.assertEqual(
                assertions["preservation_groups"]["module_signing"]["CONFIG_MODULE_SIG"],
                "y",
            )

    def test_two_independent_resolutions_must_be_byte_identical(self):
        with tempfile.TemporaryDirectory() as temporary:
            paths = self.write_fixture(Path(temporary))
            with paths["resolved2"].open("a", encoding="utf-8") as stream:
                stream.write("# harmless-looking byte drift\n")
            with self.assertRaisesRegex(
                resolution.ConfigResolutionError, "byte-for-byte"
            ):
                self.validate(paths)

    def test_unexpected_requested_symbol_fails_closed(self):
        for value in ("y", "m", '"unreviewed"', "42"):
            with self.subTest(value=value):
                with tempfile.TemporaryDirectory() as temporary:
                    paths = self.write_fixture(
                        Path(temporary),
                        requested_mutation=lambda values, item=value: values.update(
                            {"CONFIG_UNREVIEWED_GENERATED": item}
                        ),
                    )
                    with self.assertRaisesRegex(
                        resolution.ConfigResolutionError,
                        "unclassified symbols",
                    ):
                        self.validate(paths)

    def test_absent_and_explicit_n_presence_drift_is_reported(self):
        self.assertEqual(
            resolution.changed_symbols({}, {"CONFIG_DISABLED": "n"}),
            [
                {
                    "after": "n",
                    "before": "<absent>",
                    "symbol": "CONFIG_DISABLED",
                }
            ],
        )
        self.assertEqual(
            resolution.changed_symbols({"CONFIG_DISABLED": "n"}, {}),
            [
                {
                    "after": "<absent>",
                    "before": "n",
                    "symbol": "CONFIG_DISABLED",
                }
            ],
        )
        for value in ("y", "m", '"n"', "0"):
            with self.subTest(value=value):
                self.assertEqual(
                    resolution.changed_symbols({}, {"CONFIG_VISIBLE": value}),
                    [
                        {
                            "after": value,
                            "before": "<absent>",
                            "symbol": "CONFIG_VISIBLE",
                        }
                    ],
                )

    def test_expected_n_assertions_accept_absence_but_other_values_do_not(self):
        def remove_disabled_assertions(values):
            for symbol in (
                "CONFIG_CALL_PADDING",
                "CONFIG_DEBUG_INFO_REDUCED",
                "CONFIG_GCC_PLUGIN_RANDSTRUCT",
            ):
                values.pop(symbol)

        with tempfile.TemporaryDirectory() as temporary:
            paths = self.write_fixture(
                Path(temporary),
                baseline_mutation=lambda values: values.pop(
                    "CONFIG_DEBUG_INFO_REDUCED"
                ),
                shared_mutation=remove_disabled_assertions,
            )
            _, assertions = self.validate(paths)
            self.assertEqual(
                assertions["dependencies"]["CONFIG_GCC_PLUGIN_RANDSTRUCT"],
                "n",
            )
            self.assertEqual(
                assertions["dependencies"]["CONFIG_CALL_PADDING"], "n"
            )
            self.assertEqual(
                assertions["preservation_groups"]["btf_debug"][
                    "CONFIG_DEBUG_INFO_REDUCED"
                ],
                "n",
            )

        self.assertEqual(
            resolution.asserted_config_value(
                {}, "CONFIG_HIDDEN", "n", "generated tool probe"
            ),
            "n",
        )
        for expected in ("y", "m", '"value"', "42"):
            with self.subTest(expected=expected):
                with self.assertRaisesRegex(
                    resolution.ConfigResolutionError, "differs"
                ):
                    resolution.asserted_config_value(
                        {}, "CONFIG_HIDDEN", expected, "fixture"
                    )

    def test_rust_cannot_be_removed_from_requested_classification(self):
        with tempfile.TemporaryDirectory() as temporary:
            paths = self.write_fixture(Path(temporary))
            contract = copy.deepcopy(self.contract)
            contract["requested_delta"] = [
                row
                for row in contract["requested_delta"]
                if row["symbol"] != "CONFIG_RUST"
            ]
            with self.assertRaisesRegex(
                resolution.ConfigResolutionError, "unclassified symbols"
            ):
                resolution.validate_config_pair(
                    contract,
                    paths["baseline"],
                    [paths["control1"], paths["control2"]],
                    [paths["resolved1"], paths["resolved2"]],
                    synthetic_probes(),
                )

    def test_asm_modversions_derived_classification_is_exact(self):
        for mutation, message in (
            (lambda rows: [], "unclassified symbols"),
            (
                lambda rows: [dict(rows[0], resolved="y")],
                "derived semantic delta",
            ),
        ):
            with self.subTest(message=message):
                with tempfile.TemporaryDirectory() as temporary:
                    paths = self.write_fixture(Path(temporary))
                    contract = copy.deepcopy(self.contract)
                    contract["derived_delta"] = mutation(contract["derived_delta"])
                    with self.assertRaisesRegex(
                        resolution.ConfigResolutionError, message
                    ):
                        resolution.validate_config_pair(
                            contract,
                            paths["baseline"],
                            [paths["control1"], paths["control2"]],
                            [paths["resolved1"], paths["resolved2"]],
                            synthetic_probes(),
                        )

    def test_tool_probe_mismatch_fails_closed(self):
        with tempfile.TemporaryDirectory() as temporary:
            paths = self.write_fixture(
                Path(temporary),
                shared_mutation=lambda values: values.update(
                    {"CONFIG_RUSTC_VERSION": "109199"}
                ),
            )
            with self.assertRaisesRegex(
                resolution.ConfigResolutionError, "tool probe"
            ):
                self.validate(paths)

    def test_llvm_config_probe_path_is_exact(self):
        tool_environment = self.contract["tool_environment"]
        resolution.validate_probe_binary_path(
            "llvm", "/usr/bin/llvm-config", tool_environment
        )
        with self.assertRaisesRegex(
            resolution.ConfigResolutionError, "llvm-config binary path"
        ):
            resolution.validate_probe_binary_path(
                "llvm", "/usr/sbin/llvm-config", tool_environment
            )

    def test_environment_delta_is_dynamic_but_output_schema_is_exact(self):
        with tempfile.TemporaryDirectory() as temporary:
            paths = self.write_fixture(
                Path(temporary),
                shared_mutation=lambda values: values.update(
                    {"CONFIG_DYNAMIC_ENVIRONMENT_FIXTURE": "y"}
                ),
            )
            delta, _ = self.validate(paths)
            self.assertEqual(
                set(delta),
                {
                    "classification",
                    "derived_changes",
                    "environment_generated_changes",
                    "generated_symbol_results",
                    "representation_changes",
                    "requested_changes",
                    "requested_generated_symbols",
                    "unexpected_generated_symbols",
                },
            )
            self.assertIn(
                "CONFIG_DYNAMIC_ENVIRONMENT_FIXTURE",
                [
                    row["symbol"]
                    for row in delta["environment_generated_changes"]
                ],
            )
            self.assertEqual(
                set(delta["generated_symbol_results"]),
                set(self.contract["generated_environment"]["policy_symbols"]),
            )
            self.assertEqual(
                delta["classification"]["control_to_resolved"],
                sorted(
                    delta["requested_changes"]
                    + delta["derived_changes"]
                    + delta["requested_generated_symbols"]
                    + delta["representation_changes"],
                    key=lambda row: row["symbol"],
                ),
            )

    def test_btf_and_signing_drift_fail_closed(self):
        for symbol in ("CONFIG_DEBUG_INFO_BTF", "CONFIG_MODULE_SIG"):
            with self.subTest(symbol=symbol):
                with tempfile.TemporaryDirectory() as temporary:
                    paths = self.write_fixture(
                        Path(temporary),
                        requested_mutation=lambda values, name=symbol: values.update(
                            {name: "n"}
                        ),
                    )
                    with self.assertRaises(resolution.ConfigResolutionError):
                        self.validate(paths)

    def test_werror_is_preserved_in_baseline_control_and_resolved(self):
        mutations = (
            ("baseline", {"baseline_mutation": lambda values: values.update({"CONFIG_WERROR": "n"})}),
            ("control", {"control_mutation": lambda values: values.update({"CONFIG_WERROR": "n"})}),
            ("resolved", {"requested_mutation": lambda values: values.update({"CONFIG_WERROR": "n"})}),
        )
        for stage, keyword in mutations:
            with self.subTest(stage=stage):
                with tempfile.TemporaryDirectory() as temporary:
                    paths = self.write_fixture(Path(temporary), **keyword)
                    with self.assertRaisesRegex(
                        resolution.ConfigResolutionError,
                        stage + " preserved.*CONFIG_WERROR",
                    ):
                        self.validate(paths)

    def test_call_padding_requires_the_contract_rustc_minimum(self):
        with tempfile.TemporaryDirectory() as temporary:
            paths = self.write_fixture(
                Path(temporary),
                shared_mutation=lambda values: values.update(
                    {
                        "CONFIG_RUSTC_HAS_UNNECESSARY_TRANSMUTES": "n",
                        "CONFIG_RUSTC_VERSION": "108000",
                    }
                ),
            )
            probes = synthetic_probes()
            probes["derived"]["rustc_version"] = 108000
            with self.assertRaisesRegex(
                resolution.ConfigResolutionError, "requires newer rustc"
            ):
                resolution.validate_config_pair(
                    self.contract,
                    paths["baseline"],
                    [paths["control1"], paths["control2"]],
                    [paths["resolved1"], paths["resolved2"]],
                    probes,
                )

    def test_duplicate_config_symbol_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "duplicate.config"
            path.write_text("CONFIG_RUST=y\n# CONFIG_RUST is not set\n", encoding="utf-8")
            with self.assertRaisesRegex(
                resolution.ConfigResolutionError, "duplicate config symbol"
            ):
                resolution.parse_config(path)


class RustavailableTests(unittest.TestCase):
    def setUp(self):
        self.contract = resolution.validate_contract(REPO_ROOT)
        self.command = [
            "make",
            "-C",
            "/source",
            "O=/requested-build",
            "ARCH=x86_64",
            "LLVM=1",
            "rustavailable",
        ]

    def invoke(self, stdout=b"Rust is available!\n", stderr=b"", error=None):
        original = resolution.run_command

        def fake_run_command(arguments, cwd=None, env=None, timeout=600):
            self.assertEqual(arguments, self.command)
            self.assertEqual(env, resolution.CAPTURE_ENVIRONMENT)
            self.assertEqual(timeout, 1800)
            if error is not None:
                raise error
            return stdout, stderr

        resolution.run_command = fake_run_command
        try:
            return resolution.run_rustavailable(self.command, self.contract)
        finally:
            resolution.run_command = original

    def test_exact_success_is_digest_bound(self):
        record = self.invoke(
            b"make: Entering directory '/source'\nRust is available!\n"
        )
        self.assertEqual(record["command"], self.command)
        self.assertEqual(record["exit_code"], 0)
        self.assertEqual(record["success_line_count"], 1)
        self.assertEqual(
            record["stderr_sha256"], hashlib.sha256(b"").hexdigest()
        )

    def test_nonzero_exit_is_not_swallowed(self):
        with self.assertRaisesRegex(resolution.ConfigResolutionError, r"failed \(7\)"):
            self.invoke(error=resolution.ConfigResolutionError("command failed (7)"))

    def test_stderr_and_missing_or_duplicate_success_fail_closed(self):
        cases = (
            (b"Rust is available!\n", b"warning\n", "wrote stderr"),
            (b"make output only\n", b"", "unique success line"),
            (
                b"Rust is available!\nRust is available!\n",
                b"",
                "unique success line",
            ),
        )
        for stdout, stderr, message in cases:
            with self.subTest(message=message):
                with self.assertRaisesRegex(
                    resolution.ConfigResolutionError, message
                ):
                    self.invoke(stdout=stdout, stderr=stderr)

    def test_commands_manifest_binds_rustavailable_for_both_runs(self):
        runs = []
        for number in (1, 2):
            runs.append(
                {
                    "control_command": ["control-olddefconfig", str(number)],
                    "control_process_command": ["control-process", str(number)],
                    "control_process_environment": {"PASS": str(number)},
                    "merge_command": ["merge", str(number)],
                    "requested_process_command": ["requested-process", str(number)],
                    "requested_process_environment": {"PASS": str(number)},
                    "requested_command": ["requested-olddefconfig", str(number)],
                    "rustavailable": {
                        "command": ["rustavailable", str(number)],
                        "exit_code": 0,
                        "stderr_sha256": hashlib.sha256(b"").hexdigest(),
                        "stdout_sha256": hashlib.sha256(
                            "pass {}\n".format(number).encode("ascii")
                        ).hexdigest(),
                        "success_line_count": 1,
                    },
                    "source_cleanup_command": ["mrproper", str(number)],
                }
            )
        manifest = resolution.build_command_manifest(runs, self.contract)
        self.assertEqual(manifest["schema_version"], 2)
        self.assertEqual(len(manifest["passes"]), 2)
        self.assertEqual(
            [row["requested_rustavailable"] for row in manifest["passes"]],
            [run["rustavailable"] for run in runs],
        )
        with self.assertRaisesRegex(
            resolution.ConfigResolutionError, "exactly two runs"
        ):
            resolution.build_command_manifest(runs[:1], self.contract)


class InputSafetyTests(unittest.TestCase):
    def test_duplicate_json_keys_are_rejected(self):
        with self.assertRaisesRegex(resolution.ConfigResolutionError, "duplicate JSON"):
            json.loads('{"a":1,"a":2}', object_pairs_hook=resolution.reject_duplicate_pairs)

    def test_symlinked_repository_input_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            target = root / "target"
            target.write_text("x", encoding="utf-8")
            link = root / "link"
            link.symlink_to(target)
            with self.assertRaisesRegex(
                resolution.ConfigResolutionError, "regular file"
            ):
                resolution.safe_repo_file(root, "link", "fixture")

    def test_symlinked_asset_directory_and_special_tar_members_are_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            parent = Path(temporary)
            target = parent / "assets"
            target.mkdir()
            link = parent / "assets-link"
            link.symlink_to(target, target_is_directory=True)
            with self.assertRaisesRegex(
                resolution.ConfigResolutionError, "regular directory"
            ):
                resolution.regular_directory(link, "fixture assets")
        device = tarfile.TarInfo("linux/device")
        device.type = tarfile.CHRTYPE
        sparse = tarfile.TarInfo("linux/sparse")
        sparse.type = tarfile.GNUTYPE_SPARSE
        malformed_names = (
            "/absolute",
            "../escape",
            "other/file",
            "linux/../escape",
            "linux/./escape",
            "linux//escape",
            "linux\\escape",
        )
        for member in (device, sparse) + tuple(
            tarfile.TarInfo(name) for name in malformed_names
        ):
            with self.assertRaisesRegex(
                resolution.ConfigResolutionError, "archive member is unsafe"
            ):
                resolution.safe_tar_member(member, "linux")

    def test_exact_documentation_changes_and_in_root_hardlink_extract(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            archive = root / "linux.tar.xz"
            write_source_archive(archive)
            target = root / "extract"
            target.mkdir()
            source = resolution.extract_source(archive, target, "linux")
            changes = source / "Documentation" / "Changes"
            self.assertTrue(changes.is_symlink())
            self.assertEqual(os.readlink(str(changes)), "process/changes.rst")
            self.assertEqual(changes.read_text(encoding="utf-8"), "fixture changes\n")
            syscall = source / "arch" / "arm64" / "tools" / "syscall_64.tbl"
            self.assertTrue(syscall.is_symlink())
            self.assertEqual(
                os.readlink(str(syscall)), "../../../scripts/syscall.tbl"
            )
            self.assertEqual(syscall.read_text(encoding="utf-8"), "fixture syscall\n")
            copying = source / "COPYING"
            hardlink = source / "COPYING.hard"
            self.assertEqual(hardlink.read_bytes(), copying.read_bytes())
            self.assertEqual(hardlink.stat().st_ino, copying.stat().st_ino)
            self.assertEqual((source / "Makefile").stat().st_mode & 0o777, 0o755)

    def test_documentation_changes_link_mutations_fail_closed(self):
        mutations = (
            "/etc/passwd",
            "../../outside",
            "../../../linux/Documentation/process/changes.rst",
            "process\\changes.rst",
            "process//changes.rst",
            "",
        )
        for target in mutations:
            with self.subTest(target=target):
                member = tarfile.TarInfo("linux/Documentation/Changes")
                member.type = tarfile.SYMTYPE
                member.linkname = target
                with self.assertRaisesRegex(
                    resolution.ConfigResolutionError,
                    "link target (?:is unsafe|escapes its root)",
                ):
                    resolution.safe_tar_member(member, "linux")

    def test_hardlink_escape_and_missing_link_targets_fail_closed(self):
        for target in ("/etc/passwd", "../outside", "linux/../../outside"):
            with self.subTest(target=target):
                member = tarfile.TarInfo("linux/COPYING.hard")
                member.type = tarfile.LNKTYPE
                member.linkname = target
                with self.assertRaisesRegex(
                    resolution.ConfigResolutionError,
                    "link target (?:is unsafe|escapes its root)",
                ):
                    resolution.safe_tar_member(member, "linux")

        root = tarfile.TarInfo("linux")
        root.type = tarfile.DIRTYPE
        missing = tarfile.TarInfo("linux/Documentation/Changes")
        missing.type = tarfile.SYMTYPE
        missing.linkname = "process/changes.rst"
        with self.assertRaisesRegex(
            resolution.ConfigResolutionError, "link target is not a member"
        ):
            resolution.validated_tar_members([root, missing], "linux")

    def test_archive_is_fully_validated_before_any_member_is_written(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            archive = root / "linux.tar.xz"
            write_source_archive(archive, changes_target="../../outside")
            target = root / "extract"
            target.mkdir()
            with self.assertRaisesRegex(
                resolution.ConfigResolutionError, "link target escapes its root"
            ):
                resolution.extract_source(archive, target, "linux")
            self.assertEqual(list(target.iterdir()), [])

    def test_duplicate_and_link_ancestor_members_fail_closed(self):
        root = tarfile.TarInfo("linux")
        root.type = tarfile.DIRTYPE
        first = tarfile.TarInfo("linux/Makefile")
        second = tarfile.TarInfo("linux/Makefile")
        with self.assertRaisesRegex(
            resolution.ConfigResolutionError, "duplicate member"
        ):
            resolution.validated_tar_members([root, first, second], "linux")

        linked_directory = tarfile.TarInfo("linux/Documentation")
        linked_directory.type = tarfile.SYMTYPE
        linked_directory.linkname = "."
        child = tarfile.TarInfo("linux/Documentation/Changes")
        with self.assertRaisesRegex(
            resolution.ConfigResolutionError, "descends through a non-directory"
        ):
            resolution.validated_tar_members(
                [root, linked_directory, child], "linux"
            )

    def test_gate_promotion_and_generated_policy_removal_are_detected(self):
        contract = resolution.validate_contract(REPO_ROOT)
        promoted = copy.deepcopy(contract)
        promoted["gate_claims"]["RK-005"] = True
        with self.assertRaises(resolution.ConfigResolutionError):
            resolution.require_exact(
                promoted["gate_claims"], contract["gate_claims"], "gate claims"
            )
        removed = copy.deepcopy(contract)
        removed["generated_environment"]["policy_symbols"].remove(
            "CONFIG_RUSTC_HAS_UNNECESSARY_TRANSMUTES"
        )
        self.assertNotIn(
            "CONFIG_RUSTC_HAS_UNNECESSARY_TRANSMUTES",
            removed["generated_environment"]["policy_symbols"],
        )

    def test_workflow_yaml_parses_and_bash_blocks_parse(self):
        import yaml

        workflow_path = REPO_ROOT / resolution.WORKFLOW_PATH
        workflow_text = workflow_path.read_text(encoding="utf-8")
        workflow = yaml.safe_load(workflow_text)
        self.assertIsInstance(workflow, dict)
        self.assertIn("gzip lld llvm", workflow_text)
        self.assertIn('test "$(command -v ld.lld)" = /usr/bin/ld.lld', workflow_text)
        self.assertIn("rpm -qf --qf '%{NAME}\\n' /usr/bin/ld.lld", workflow_text)
        self.assertIn("ld.lld --version", workflow_text)
        for job in workflow["jobs"].values():
            for step in job.get("steps", []):
                script = step.get("run")
                if script:
                    completed = subprocess.run(
                        ["bash", "-n"],
                        input=script.encode("utf-8"),
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                    )
                    self.assertEqual(
                        completed.returncode,
                        0,
                        completed.stderr.decode("utf-8", errors="replace"),
                    )


if __name__ == "__main__":
    unittest.main()
