#!/usr/bin/env python3
"""Mutation and exact-replay tests for the credit-forbidden RS-006 substrate."""

from __future__ import print_function

import ast
import json
import os
import subprocess
import sys
import tempfile
import unittest


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from scripts import rs006_miscdevice_substrate as substrate


def read_bytes(relative):
    with open(os.path.join(REPO_ROOT, relative), "rb") as stream:
        return stream.read()


def canonical_json(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


class Rs006MiscdeviceSubstrateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = read_bytes(substrate.CONTRACT_PATH)
        cls.patches = {
            row["path"]: read_bytes(row["path"])
            for row in substrate.CANDIDATE_PATCHES
        }

    def test_repository_contract_is_not_ready_and_credit_forbidden(self):
        contract, replay = substrate.check(REPO_ROOT)
        self.assertIsNone(replay)
        self.assertEqual("RS-006", contract["target"]["gate_id"])
        self.assertEqual("NOT_READY", contract["readiness"]["status"])
        self.assertFalse(contract["readiness"]["credit_eligible"])
        self.assertEqual(
            substrate.READINESS_BLOCKERS,
            tuple(contract["readiness"]["blockers"]),
        )
        integration = contract["integration"]
        self.assertFalse(integration["temporary_filenames"])
        self.assertTrue(integration["source_lock_integrated"])
        self.assertTrue(integration["license_authority_integrated"])
        self.assertTrue(integration["workflow_integrated"])
        self.assertTrue(integration["main_compatibility_series_integrated"])
        self.assertEqual(
            ["0019", "0020"],
            [row["filename"][:4] for row in integration["final_order_guidance"]],
        )

    def test_checker_and_tests_parse_as_python_3_6(self):
        for relative in (
                "scripts/rs006_miscdevice_substrate.py",
                "scripts/tests/test_rs006_miscdevice_substrate.py"):
            source = read_bytes(relative).decode("utf-8")
            try:
                ast.parse(source, filename=relative, feature_version=(3, 6))
            except TypeError:
                ast.parse(source, filename=relative, feature_version=6)

    def test_contract_digest_and_duplicate_keys_fail_closed(self):
        mutated = self.contract.replace(b'"status": "NOT_READY"', b'"status": "PASS"', 1)
        with self.assertRaisesRegex(substrate.ContractError, "contract digest changed"):
            substrate.check(REPO_ROOT, contract_override=mutated)
        duplicate = self.contract.replace(
            b'"schema_version": 1,', b'"schema_version": 1,\n  "schema_version": 1,', 1)
        with self.assertRaises(substrate.ContractError):
            substrate.check(REPO_ROOT, contract_override=duplicate)

    def test_credit_and_integration_flags_cannot_flip(self):
        contract = json.loads(self.contract.decode("utf-8"))
        for field in (
                "source_lock_integrated", "license_authority_integrated",
                "workflow_integrated", "main_compatibility_series_integrated"):
            mutated = json.loads(self.contract.decode("utf-8"))
            mutated["integration"][field] = False
            with self.subTest(field=field):
                with self.assertRaises(substrate.ContractError):
                    substrate._load_contract(canonical_json(mutated))
        contract["readiness"] = {"blockers": [], "credit_eligible": True, "status": "PASS"}
        with self.assertRaises(substrate.ContractError):
            substrate._load_contract(canonical_json(contract))

    def test_prerequisite_order_and_active_numbers_cannot_drift(self):
        for mutation in ("swap", "predecessor", "active"):
            contract = json.loads(self.contract.decode("utf-8"))
            if mutation == "swap":
                contract["upstream_series"].reverse()
            elif mutation == "predecessor":
                contract["integration"]["preserved_predecessor_numbers"] = ["0013"]
            else:
                contract["integration"]["active_patch_numbers"] = ["0019"]
            with self.subTest(mutation=mutation):
                with self.assertRaises(substrate.ContractError):
                    substrate._load_contract(canonical_json(contract))

    def test_every_candidate_patch_byte_mutation_is_rejected(self):
        for relative, data in sorted(self.patches.items()):
            mutated = data[:-1] + bytes(bytearray([data[-1] ^ 1]))
            with self.subTest(relative=relative):
                with self.assertRaisesRegex(substrate.ContractError, "patch identity changed"):
                    substrate.check(REPO_ROOT, patch_overrides={relative: mutated})

    def test_commit_header_and_subject_are_explicitly_bound(self):
        for expected in substrate.CANDIDATE_PATCHES:
            data = self.patches[expected["path"]]
            substrate._validate_patch(data, expected)
            weakened = dict(expected)
            weakened["sha256"] = substrate._sha256(
                data.replace(expected["commit"].encode("ascii"), b"0" * 40, 1))
            weakened["bytes"] = len(data)
            mutated = data.replace(expected["commit"].encode("ascii"), b"0" * 40, 1)
            with self.subTest(relative=expected["path"]):
                with self.assertRaisesRegex(substrate.ContractError, "commit provenance"):
                    substrate._validate_patch(mutated, weakened)

    def test_patch_path_vector_cannot_expand(self):
        expected = dict(substrate.CANDIDATE_PATCHES[0])
        data = self.patches[expected["path"]]
        mutated = data.replace(
            b"diff --git a/rust/kernel/types.rs b/rust/kernel/types.rs",
            b"diff --git a/rust/kernel/other.rs b/rust/kernel/other.rs",
            1,
        )
        expected["sha256"] = substrate._sha256(mutated)
        expected["bytes"] = len(mutated)
        with self.assertRaisesRegex(substrate.ContractError, "path vector changed"):
            substrate._validate_patch(mutated, expected)

    def test_exact_rocky_source_replay_when_configured(self):
        source = os.environ.get("MCKERNEL_ROCKY_SOURCE_6_12")
        if not source:
            self.skipTest("set MCKERNEL_ROCKY_SOURCE_6_12 for strict source replay")
        _contract, replay = substrate.check(REPO_ROOT, kernel_source=source)
        self.assertEqual(18, replay["baseline_patch_count"])
        self.assertEqual(2, replay["candidate_patch_count"])
        self.assertEqual(4, replay["postimage_count"])
        self.assertEqual(0, replay["strict_fuzz"])

    def test_binding_header_semantics_reject_legacy_api_drift(self):
        source = os.environ.get("MCKERNEL_ROCKY_SOURCE_6_12")
        if not source:
            self.skipTest("set MCKERNEL_ROCKY_SOURCE_6_12 for C API replay")
        with tempfile.TemporaryDirectory(prefix="rs006-mutated-headers-") as temporary:
            for relative in ("include/linux/miscdevice.h", "include/linux/fs.h"):
                destination = os.path.join(temporary, *relative.split("/"))
                parent = os.path.dirname(destination)
                if not os.path.isdir(parent):
                    os.makedirs(parent)
                with open(os.path.join(source, *relative.split("/")), "rb") as stream:
                    data = stream.read()
                if relative == "include/linux/miscdevice.h":
                    data = data.replace(b"MISC_DYNAMIC_MINOR\t255", b"MISC_DYNAMIC_MINOR\t254", 1)
                with open(destination, "wb") as stream:
                    stream.write(data)
            with self.assertRaisesRegex(substrate.ContractError, "dynamic misc minor"):
                substrate._validate_binding_headers(temporary)

    def test_source_replay_rejects_a_mutated_base_preimage(self):
        source = os.environ.get("MCKERNEL_ROCKY_SOURCE_6_12")
        if not source:
            self.skipTest("set MCKERNEL_ROCKY_SOURCE_6_12 for strict source replay")
        with tempfile.TemporaryDirectory(prefix="rs006-mutated-source-") as temporary:
            for relative, _size, _digest, _blob in substrate.BASE_RELEVANT:
                destination = os.path.join(temporary, *relative.split("/"))
                parent = os.path.dirname(destination)
                if not os.path.isdir(parent):
                    os.makedirs(parent)
                with open(os.path.join(source, *relative.split("/")), "rb") as stream:
                    data = stream.read()
                if relative == "rust/kernel/types.rs":
                    data += b"\n"
                with open(destination, "wb") as stream:
                    stream.write(data)
            with self.assertRaisesRegex(substrate.ContractError, "base preimage"):
                substrate.check(REPO_ROOT, kernel_source=temporary)

    def test_cli_requires_source_when_requested(self):
        process = subprocess.Popen(
            [sys.executable, "scripts/rs006_miscdevice_substrate.py", "--repo", REPO_ROOT,
             "--require-source-replay"],
            cwd=REPO_ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        _stdout, stderr = process.communicate()
        self.assertNotEqual(0, process.returncode)
        self.assertIn(b"requires --kernel-source", stderr)


if __name__ == "__main__":
    unittest.main()
