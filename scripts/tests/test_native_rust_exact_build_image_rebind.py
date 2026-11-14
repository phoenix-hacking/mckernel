import hashlib
import json
import tempfile
import unittest
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parents[1]))
import native_rust_exact_build_image_rebind as rebind


class RebindTests(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory()
        self.root = Path(self.t.name)
        self.ev = self.root / "evidence"; self.ev.mkdir()
        (self.root / "target").mkdir()
        observation = self.ev / "offline-observation.json"
        observation.write_text('{"probe":"pass"}\n')
        sha = hashlib.sha256(observation.read_bytes()).hexdigest()
        self.source = "6fed3a1022db0b4f9828dd42a8bd8f88fc052053"
        self.target = "7fed3a1022db0b4f9828dd42a8bd8f88fc052053"
        self.image = "sha256:" + "a" * 64
        self.lock = "b" * 64
        self.receipt = self.root / "receipt.json"
        self.receipt.write_text(json.dumps({
            "status": "PASS", "source_free": True, "runtime_network": "none",
            "retired": True, "candidate_sha": self.source, "image_id": self.image,
            "toolchain_lock_sha256": self.lock, "immutable_image_sha256": "c" * 64,
            "tools": {"probe": "sha256:" + "d" * 64}, "libraries": {"lib": "sha256:" + "e" * 64},
            "evidence": {observation.name: {"sha256": sha, "size": observation.stat().st_size}},
        }))
        self.receipt_sha = hashlib.sha256(self.receipt.read_bytes()).hexdigest()

    def call(self, **extra):
        args = dict(receipt_path=self.receipt, evidence_root=self.ev,
                    source_candidate_sha=self.source, target_candidate_sha=self.target,
                    source_receipt_sha256=self.receipt_sha,
                    image_id=self.image,
                    toolchain_lock_sha256=self.lock,
                    output_path=self.root / "request.json",
                    target_receipt_path=self.root / "target" / "evidence" / "receipt.json",
                    target_evidence_root=self.root / "target" / "evidence")
        args.update(extra)
        return rebind.rebind(**args)

    def test_creates_candidate_bound_noncrediting_request(self):
        doc = self.call()
        self.assertEqual(doc["status"], "READY_FOR_REVIEWED_EXECUTION")
        self.assertFalse(doc["execution_claim"])
        doc = json.loads((self.root / "request.json").read_text())
        self.assertEqual(doc["source_candidate_sha"], self.source)
        self.assertEqual(doc["target_candidate_sha"], self.target)
        self.assertNotIn("candidate_sha", doc)

    def test_candidate_mismatch_rejected(self):
        with self.assertRaises(rebind.RebindError): self.call(source_candidate_sha="d" * 40)

    def test_source_target_mismatch_is_explicitly_supported(self):
        self.assertNotEqual(self.source, self.target)
        doc = self.call()
        self.assertEqual(doc["source_candidate_sha"], self.source)
        self.assertEqual(doc["target_candidate_sha"], self.target)

    def test_swapped_receipt_rejected(self):
        with self.assertRaises(rebind.RebindError): self.call(source_candidate_sha=self.target)

    def test_target_must_be_git_sha(self):
        with self.assertRaises(rebind.RebindError): self.call(target_candidate_sha="z" * 40)

    def test_evidence_drift_rejected(self):
        (self.ev / "offline-observation.json").write_text("drift\n")
        with self.assertRaises(rebind.RebindError): self.call()

    def test_tool_data_mismatch_rejected(self):
        doc = json.loads(self.receipt.read_text()); doc.pop("tools")
        self.receipt.write_text(json.dumps(doc))
        with self.assertRaises(rebind.RebindError): self.call()

    def test_receipt_digest_mismatch_rejected(self):
        with self.assertRaises(rebind.RebindError): self.call(source_receipt_sha256="d" * 64)

    def test_evidence_traversal_rejected(self):
        doc = json.loads(self.receipt.read_text())
        row = doc["evidence"].pop("offline-observation.json")
        doc["evidence"]["../offline-observation.json"] = row
        self.receipt.write_text(json.dumps(doc)); self.receipt_sha = hashlib.sha256(self.receipt.read_bytes()).hexdigest()
        with self.assertRaises(rebind.RebindError): self.call()

    def test_probe_is_deferred(self):
        with self.assertRaises(rebind.RebindError): self.call(image_probe={"status": "PASS"})

    def test_no_replace(self):
        self.call();
        with self.assertRaises(rebind.RebindError): self.call(output_path=self.root / "request.json")

    def test_request_may_not_replace_target_evidence_directory(self):
        target = self.root / "collision"
        with self.assertRaises(rebind.RebindError):
            self.call(output_path=target, target_evidence_root=target,
                      target_receipt_path=target / "receipt.json")

    def test_request_may_not_be_inside_target_evidence_directory(self):
        target = self.root / "collision"
        with self.assertRaises(rebind.RebindError):
            self.call(output_path=target / "request.json", target_evidence_root=target,
                      target_receipt_path=target / "receipt.json")

    def test_lease_release_requires_retirement_in_contract(self):
        doc = self.call()
        self.assertTrue(doc["probe"]["retire_before_lease_release"])
        self.assertTrue(doc["probe"]["fresh_container"])


if __name__ == "__main__": unittest.main()
