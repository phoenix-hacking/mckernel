"""Fail-closed, source-only checks for the scratch18 retry2 image packet."""
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
PACKET = ROOT / "docs/verification/evidence/native-exact-scratch18-retry2-image-preparation-20261001.json"


class Scratch18Retry2ImagePacket(unittest.TestCase):
    def setUp(self):
        self.d = json.loads(PACKET.read_text())
        self.fresh = self.d["fresh_targets"]

    def test_candidate_and_scope_are_exact(self):
        self.assertEqual(self.d["status"], "PREPARED_NOT_EXECUTED")
        self.assertEqual(self.d["candidate_sha"], "89ab5c555aac9177a789efc67ddc775dacb25d6d")
        self.assertIn("no build", self.d["scope"])
        self.assertIn("Docker", self.d["scope"])
        self.assertIn("sudo", self.d["scope"])

    def test_all_runtime_outputs_are_fresh_candidate_specific(self):
        for key, value in self.fresh.items():
            if key == "common_exclusion":
                self.assertEqual(value, "/home/holden/mckernel-work/scratch/native-exact-candidate-operational-exclusion-scratch18-image-1.json")
            else:
                self.assertIn("89ab5c55", value, key)
            self.assertFalse("c81aeaca" in value, key)
            self.assertFalse(Path(value).exists(), "packet must not create target: " + key)
        git = self.d["gitlink"]
        for key in ("fresh_checkout", "fresh_manifest"):
            self.assertIn("89ab5c55", git[key])
            self.assertFalse(Path(git[key]).exists())

    def test_preserved_inputs_are_not_targets(self):
        inputs = self.d["inputs"]
        self.assertTrue(inputs["source_root"].endswith("mckernel-exact-candidate-scratch-18"))
        self.assertTrue(inputs["metadata_backup"].endswith("scratch-18-metadata-backup"))
        self.assertTrue(inputs["build_output_read_only"].endswith("4e99a82c-scratch-12"))
        self.assertNotIn(inputs["build_output_read_only"], self.fresh.values())
        self.assertNotIn("native-exact-image-c81aeaca-7", " ".join(self.fresh.values()))
        self.assertEqual(Path(self.fresh["output"]).parent, Path(self.fresh["owner_work"]))
        self.assertEqual(Path(self.fresh["evidence"]).parent, Path(self.fresh["owner_work"]))
        self.assertIn("c81aeaca", inputs["source_tool_image_receipt"])
        self.assertIn("89ab5c55", inputs["fresh_tool_image_receipt"])
        self.assertNotEqual(inputs["source_tool_image_receipt"], inputs["fresh_tool_image_receipt"])
        self.assertEqual(Path(inputs["fresh_tool_image_receipt"]).parent,
                         Path(inputs["fresh_tool_image_evidence"]))

    def test_bindings_and_proposed_sequence_are_complete(self):
        for key in ("request_prepare", "image_owner", "offline_driver", "provenance", "host_owner", "image_rebind"):
            name, digest = self.d["producer_bindings"][key].split("@")
            self.assertTrue(name.startswith("scripts/"), key)
            self.assertEqual(len(digest), 64, key)
        self.assertEqual(len(self.d["proposed_sequence"]), 5)
        self.assertIn("prepare", self.d["proposed_sequence"][0])
        self.assertIn("rebind", self.d["proposed_sequence"][1])
        self.assertIn("native_rust_exact_build_image_rebind.py", self.d["proposed_sequence"][1])
        self.assertIn("PASS receipt", self.d["proposed_sequence"][2])
        self.assertEqual(self.fresh["common_exclusion"], "/home/holden/mckernel-work/scratch/native-exact-candidate-operational-exclusion-scratch18-image-1.json")


if __name__ == "__main__":
    unittest.main()
