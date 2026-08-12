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
        self.assertEqual(generated["coverage"]["behavior_count"], 388)
        self.assertEqual(generated["coverage"]["test_count"], 388)
        self.assertEqual(
            generated["coverage"]["by_module"],
            {"ihk": 172, "ihk_smp_x86_64": 20, "mcctrl": 196},
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

    def test_all_frozen_errno_tokens_are_mapped(self) -> None:
        expected = contracts.source_errno_surface(REPO_ROOT, self.legacy)
        mapped: dict[str, set[str]] = {
            module: set() for module in contracts.EXPECTED_MODULES
        }
        for behavior in self.contract["behaviors"]:
            if behavior["kind"] == "legacy_errno":
                mapped[behavior["module"]].add(behavior["legacy"]["errno"])
        for module, entries in expected.items():
            self.assertEqual(mapped[module], {entry["errno"] for entry in entries})

    def test_missing_test_mapping_fails_closed(self) -> None:
        broken = copy.deepcopy(self.contract)
        broken["behaviors"][0]["acceptance_test_ids"] = []
        with self.assertRaises(contracts.ContractError):
            contracts.validate_contract(broken, self.policy, self.legacy, REPO_ROOT)


if __name__ == "__main__":
    unittest.main()
