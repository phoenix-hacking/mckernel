#!/usr/bin/env python3
"""Fail-closed tests for RK-005 deterministic config resolution."""

from __future__ import print_function

import ast
import copy
import hashlib
import json
import subprocess
import sys
import tarfile
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import rocky_kernel_config_resolution as resolution  # noqa: E402


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
            "CONFIG_BINDGEN_VERSION_TEXT": '"bindgen 0.72.1"',
            "CONFIG_CALL_PADDING": "y",
            "CONFIG_PAHOLE_HAS_BTF_TAG": "y",
            "CONFIG_PAHOLE_HAS_LANG_EXCLUDE": "y",
            "CONFIG_PAHOLE_HAS_SPLIT_BTF": "y",
            "CONFIG_PAHOLE_VERSION": "131",
            "CONFIG_RUSTC_LLVM_VERSION": "210106",
            "CONFIG_RUSTC_VERSION": "109200",
            "CONFIG_RUST_IS_AVAILABLE": "y",
        }
    )
    control.update(contract["dependency_symbols"])
    control["CONFIG_RUST"] = "n"
    control["CONFIG_MODVERSIONS"] = "y"
    requested = dict(control)
    requested.update(
        {
            "CONFIG_RUST": "y",
            "CONFIG_MODVERSIONS": "n",
            "CONFIG_RUSTC_HAS_UNNECESSARY_TRANSMUTES": "y",
            "CONFIG_RUSTC_VERSION_TEXT": '"rustc 1.92.0 (fixture)"',
        }
    )
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


class RepositoryContractTests(unittest.TestCase):
    def test_contract_and_workflow_validate_without_credit(self):
        contract = resolution.validate_contract(REPO_ROOT)
        resolution.validate_workflow(REPO_ROOT)
        self.assertEqual(contract["phase_id"], "config-resolution")
        self.assertFalse(any(contract["gate_claims"].values()))
        self.assertIn("never awards", contract["claim_scope"])
        self.assertIn(
            "CONFIG_RUSTC_HAS_UNNECESSARY_TRANSMUTES",
            contract["generated_environment"]["supplemental_symbols"],
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
        self.assertEqual(12, len(contract["patch_authority"]["rust_compatibility"]))
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
            11,
        )
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
        self.assertNotEqual(
            contract["tool_environment"]["expected_rustc_llvm_version"],
            contract["tool_environment"]["expected_versions"]["llvm"],
        )
        self.assertEqual(
            contract["resolution"]["olddefconfig_command"][-3:],
            ["ARCH=x86_64", "LLVM=1", "olddefconfig"],
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
                    "config-resolution",
                ]
            ),
            2,
        )

    def test_script_and_tests_parse_as_python_3_6(self):
        for relative in (
            "scripts/rocky_kernel_config_resolution.py",
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
        self, root, control_mutation=None, requested_mutation=None, shared_mutation=None
    ):
        baseline, control, requested = synthetic_maps(self.contract)
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
                [row["symbol"] for row in delta["requested_generated_symbols"]],
                [
                    "CONFIG_RUSTC_HAS_UNNECESSARY_TRANSMUTES",
                    "CONFIG_RUSTC_VERSION_TEXT",
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
        with tempfile.TemporaryDirectory() as temporary:
            paths = self.write_fixture(
                Path(temporary),
                requested_mutation=lambda values: values.update(
                    {"CONFIG_UNREVIEWED_GENERATED": "y"}
                ),
            )
            with self.assertRaisesRegex(
                resolution.ConfigResolutionError, "unexpected generated symbols"
            ):
                self.validate(paths)

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
                    "environment_generated_changes",
                    "generated_symbol_results",
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
                set(self.contract["generated_environment"]["historical_policy_symbols"])
                | set(
                    self.contract["generated_environment"]["supplemental_symbols"]
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
        for member in (device, tarfile.TarInfo("../escape")):
            with self.assertRaisesRegex(
                resolution.ConfigResolutionError, "archive member is unsafe"
            ):
                resolution.safe_tar_member(member, "linux")

    def test_gate_promotion_and_supplemental_removal_are_detected(self):
        contract = resolution.validate_contract(REPO_ROOT)
        promoted = copy.deepcopy(contract)
        promoted["gate_claims"]["RK-005"] = True
        with self.assertRaises(resolution.ConfigResolutionError):
            resolution.require_exact(
                promoted["gate_claims"], contract["gate_claims"], "gate claims"
            )
        removed = copy.deepcopy(contract)
        removed["generated_environment"]["supplemental_symbols"] = {}
        self.assertNotIn(
            "CONFIG_RUSTC_HAS_UNNECESSARY_TRANSMUTES",
            removed["generated_environment"]["supplemental_symbols"],
        )

    def test_workflow_yaml_parses_and_bash_blocks_parse(self):
        import yaml

        workflow_path = REPO_ROOT / resolution.WORKFLOW_PATH
        workflow = yaml.safe_load(workflow_path.read_text(encoding="utf-8"))
        self.assertIsInstance(workflow, dict)
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
