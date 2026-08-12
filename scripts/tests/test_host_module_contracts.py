#!/usr/bin/env python3
"""Fail-closed tests for the native Rust module policy and behavior map."""

from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import host_module_contracts as contracts  # noqa: E402


class ContractFixture(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.policy = contracts.read_json(REPO_ROOT / contracts.POLICY_PATH)
        cls.legacy = contracts.read_json(REPO_ROOT / contracts.INVENTORY_PATH)
        cls.contract = contracts.read_json(REPO_ROOT / contracts.CONTRACT_PATH)


class PolicyTests(ContractFixture):
    def test_scope_is_exactly_three_native_rust_modules(self) -> None:
        contracts.validate_policy(self.policy)
        modules = self.policy["conversion_scope"]["included_modules"]
        self.assertEqual(
            [entry["crate"] for entry in modules],
            ["ihk", "ihk_smp_x86_64", "mcctrl"],
        )
        self.assertEqual(
            self.policy["conversion_scope"]["required_implementation_language"],
            "Rust-for-Linux",
        )
        self.assertFalse(self.policy["host_platform"]["kernel_core_conversion_target"])

    def test_oracles_namespaces_and_modversions_are_exact(self) -> None:
        contracts.validate_policy(self.policy)
        profiles = self.policy["module_oracles"]["profiles"]
        self.assertEqual(set(profiles), {"R0", "R1", "R2"})
        self.assertEqual(profiles["R0"]["kernel_specific_metadata"], "provenance only")
        self.assertEqual(profiles["R2"]["kernel_specific_metadata"], "must equal R1")
        symbols = self.policy["module_symbol_contract"]
        self.assertEqual(
            symbols["production_namespaces"], {"ihk": "MCKERNEL_IHK_V1"}
        )
        self.assertEqual(
            symbols["required_imports"],
            {
                "ihk_smp_x86_64": ["MCKERNEL_IHK_V1"],
                "mcctrl": ["MCKERNEL_IHK_V1"],
            },
        )
        self.assertIn("R1/R2", symbols["modversions"]["enabled"])
        self.assertIn("omit symbol CRC", symbols["modversions"]["disabled"])

        broken = copy.deepcopy(self.policy)
        broken["module_symbol_contract"]["production_namespaces"]["ihk"] = "IHK"
        with self.assertRaises(contracts.ContractError):
            contracts.validate_policy(broken)

    def test_zero_project_c_and_reference_isolation_are_non_negotiable(self) -> None:
        completion = self.policy["completion_definition"]
        self.assertEqual(completion["production_link_graph_project_c_objects"], 0)
        self.assertEqual(
            completion["production_module_project_c_implementation_bodies"], 0
        )
        self.assertEqual(
            completion["production_module_project_c_dispatch_targets"], 0
        )
        forbidden = "\n".join(self.policy["forbidden_production_inputs"]).lower()
        self.assertIn("c implementation", forbidden)
        self.assertIn("c fallback", forbidden)
        self.assertIn("prebuilt", forbidden)
        locations = self.policy["reference_isolation"]["forbidden_locations"]
        self.assertIn("production module link graph", locations)
        self.assertIn("production runtime dispatch graph", locations)

    def test_scope_expansion_or_c_escape_hatch_fails_closed(self) -> None:
        expanded = copy.deepcopy(self.policy)
        expanded["conversion_scope"]["included_modules"].append(
            {
                "crate": "unexpected",
                "filename": "unexpected.ko",
                "normalized_name": "unexpected",
                "permitted_project_module_dependencies": [],
            }
        )
        with self.assertRaises(contracts.ContractError):
            contracts.validate_policy(expanded)

        c_enabled = copy.deepcopy(self.policy)
        c_enabled["completion_definition"][
            "production_link_graph_project_c_objects"
        ] = 1
        with self.assertRaises(contracts.ContractError):
            contracts.validate_policy(c_enabled)


class BehaviorContractTests(ContractFixture):
    def test_generated_contract_is_complete_and_current(self) -> None:
        generated = contracts.build_contract(REPO_ROOT, self.policy, self.legacy)
        contracts.validate_contract(generated, self.policy, self.legacy, REPO_ROOT)
        self.assertEqual(generated, self.contract)
        self.assertEqual(generated["coverage"]["behavior_count"], 1280)
        self.assertEqual(generated["coverage"]["test_count"], 1280)
        self.assertEqual(
            generated["coverage"]["by_module"],
            {"ihk": 295, "ihk_smp_x86_64": 223, "mcctrl": 762},
        )
        self.assertEqual(
            generated["coverage"]["errno_sites_by_module"],
            {"ihk": 135, "ihk_smp_x86_64": 212, "mcctrl": 593},
        )

    def test_every_behavior_has_native_rust_and_bidirectional_test_mapping(self) -> None:
        tests = {entry["id"]: entry for entry in self.contract["acceptance_tests"]}
        referenced: set[str] = set()
        for behavior in self.contract["behaviors"]:
            replacement = behavior["rust_replacement"]
            self.assertEqual(replacement["crate"], behavior["module"])
            self.assertTrue(replacement["native_path"].startswith("crate::"))
            self.assertFalse(replacement["project_c_dispatch_permitted"])
            self.assertTrue(behavior["acceptance_test_ids"])
            for test_id in behavior["acceptance_test_ids"]:
                referenced.add(test_id)
                self.assertIn(test_id, tests)
                self.assertIn(behavior["id"], tests[test_id]["behavior_ids"])
        self.assertEqual(referenced, set(tests))

    def test_every_active_explicit_errno_site_is_mapped(self) -> None:
        expected = contracts.source_errno_surface(REPO_ROOT, self.legacy)
        mapped: dict[str, set[str]] = {
            module: set() for module in contracts.EXPECTED_MODULES
        }
        for behavior in self.contract["behaviors"]:
            if behavior["kind"] == "legacy_errno":
                mapped[behavior["module"]].add(behavior["legacy"]["site_id"])
        for module, entries in expected.items():
            self.assertEqual(mapped[module], {entry["site_id"] for entry in entries})

    def test_r0_kernel_metadata_is_provenance_not_a_production_requirement(self) -> None:
        identities = [
            behavior
            for behavior in self.contract["behaviors"]
            if behavior["kind"] == "module_identity"
        ]
        self.assertEqual(len(identities), 3)
        for behavior in identities:
            legacy = behavior["legacy"]
            self.assertTrue(legacy["r0_reference"]["vermagic"])
            production = legacy["production_contract"]
            self.assertNotIn("vermagic", production)
            self.assertIn("R1", production["vermagic_policy"])
            self.assertIn("R2", production["vermagic_policy"])

        broken = copy.deepcopy(self.contract)
        identity = next(
            behavior
            for behavior in broken["behaviors"]
            if behavior["kind"] == "module_identity"
        )
        identity["legacy"]["production_contract"]["vermagic"] = identity["legacy"][
            "r0_reference"
        ]["vermagic"]
        with self.assertRaises(contracts.ContractError):
            contracts.validate_contract(broken, self.policy, self.legacy, REPO_ROOT)

    def test_exports_declare_namespace_and_conditional_modversions_policy(self) -> None:
        exports = [
            behavior
            for behavior in self.contract["behaviors"]
            if behavior["kind"] == "exported_symbol"
        ]
        self.assertEqual(len(exports), 70)
        for behavior in exports:
            production = behavior["legacy"]["production_contract"]
            self.assertEqual(production["namespace"], "MCKERNEL_IHK_V1")
            self.assertIn("R1 and R2", production["symbol_version_policy"])
            self.assertIn("R0 CRC is provenance only", production["symbol_version_policy"])
            self.assertIn("crc", behavior["legacy"]["r0_reference"])

    def test_all_module_parameter_defaults_are_source_derived(self) -> None:
        parameters = [
            behavior
            for behavior in self.contract["behaviors"]
            if behavior["kind"] == "module_parameter"
        ]
        self.assertEqual(len(parameters), 6)
        self.assertEqual(
            {behavior["legacy"]["name"] for behavior in parameters},
            {
                "ihk_cores",
                "ihk_ikc_irq_core",
                "ihk_mem",
                "ihk_phys_start",
                "ihk_start_irq",
                "ihk_trampoline",
            },
        )
        for behavior in parameters:
            default = behavior["legacy"]["default"]
            self.assertEqual(default["expression"], "0")
            self.assertEqual(default["value"], 0)
            self.assertIn("effective_filtered_sha256", default["source_provenance"])

    def test_compatibility_overlay_application_fails_closed(self) -> None:
        original = "alpha\nbeta\ngamma\n"
        patch = (
            "diff --git a/sample.c b/sample.c\n"
            "--- a/sample.c\n"
            "+++ b/sample.c\n"
            "@@ -1,3 +1,3 @@\n"
            " alpha\n"
            "-beta\n"
            "+delta\n"
            " gamma\n"
        )
        effective, applied = contracts.apply_unified_diff_to_text(
            original, patch, "ihk/sample.c"
        )
        self.assertTrue(applied)
        self.assertEqual(effective, "alpha\ndelta\ngamma\n")
        with self.assertRaises(contracts.ContractError):
            contracts.apply_unified_diff_to_text(
                "alpha\nwrong\ngamma\n", patch, "ihk/sample.c"
            )

    def test_missing_failure_site_fails_closed(self) -> None:
        broken = copy.deepcopy(self.contract)
        index = next(
            index
            for index, behavior in enumerate(broken["behaviors"])
            if behavior["kind"] == "legacy_errno"
        )
        behavior = broken["behaviors"].pop(index)
        test_id = behavior["acceptance_test_ids"][0]
        broken["acceptance_tests"] = [
            test for test in broken["acceptance_tests"] if test["id"] != test_id
        ]
        broken["coverage"]["behavior_count"] -= 1
        broken["coverage"]["test_count"] -= 1
        broken["coverage"]["by_kind"]["legacy_errno"] -= 1
        broken["coverage"]["by_module"][behavior["module"]] -= 1
        broken["coverage"]["errno_sites_by_module"][behavior["module"]] -= 1
        with self.assertRaises(contracts.ContractError):
            contracts.validate_contract(broken, self.policy, self.legacy, REPO_ROOT)

    def test_missing_test_mapping_fails_closed(self) -> None:
        broken = copy.deepcopy(self.contract)
        broken["behaviors"][0]["acceptance_test_ids"] = []
        with self.assertRaises(contracts.ContractError):
            contracts.validate_contract(broken, self.policy, self.legacy, REPO_ROOT)


if __name__ == "__main__":
    unittest.main()
