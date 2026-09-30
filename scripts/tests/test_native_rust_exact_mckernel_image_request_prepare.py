import json
from pathlib import Path
import tempfile
import unittest

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import native_rust_exact_mckernel_image_request_prepare as prepare


class RequestPrepareTests(unittest.TestCase):
    def test_publish_validates_staged_then_final_and_writes_request_last(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); toolchain = root / "toolchain.json"; request = root / "request.json"
            seen = []
            def make(path):
                return {"toolchain_manifest": str(path), "sha256": prepare._digest(path)}
            def validate(value):
                self.assertTrue(Path(value["toolchain_manifest"]).is_file())
                self.assertFalse(request.exists())
                seen.append(Path(value["toolchain_manifest"]))
            result = prepare._publish({"schema": "fixture"}, toolchain, request, make, validate)
            self.assertEqual([path.parent == toolchain.parent for path in seen], [False, True])
            self.assertEqual(json.loads(request.read_text()), result)

    def test_publish_late_staged_failure_leaves_no_final_files(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); toolchain = root / "toolchain.json"; request = root / "request.json"
            def make(path): return {"toolchain_manifest": str(path)}
            def reject(_value): raise prepare.PreparationError("late fixture failure")
            with self.assertRaisesRegex(prepare.PreparationError, "late fixture failure"):
                prepare._publish({"schema": "fixture"}, toolchain, request, make, reject)
            self.assertFalse(toolchain.exists())
            self.assertFalse(request.exists())
            self.assertFalse(any(path.name.startswith(".mckernel-image-request-") for path in root.iterdir()))

    def test_publication_destination_overlap_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); protected = root / "source"; protected.mkdir()
            destination = protected / "request.json"
            with self.assertRaises(prepare.owner.OwnerError):
                prepare.owner._disjoint((protected, destination))

    def test_malformed_receipt_fails_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); receipt = root / "receipt.json"
            receipt.write_text("not-json", encoding="utf-8")
            (root / "inputs.json").write_text("{}", encoding="utf-8")
            with self.assertRaises((ValueError, json.JSONDecodeError, prepare.PreparationError)):
                prepare.prepare(candidate_manifest=root / "inputs.json", backup_root=root,
                                backup_inventory={}, build_output=root, image_receipt=receipt,
                                image_id="sha256:" + "a" * 64, nightly_root=root,
                                host_git={}, driver_path=root / "driver", provenance_path=root / "prov",
                                host_owner_path=root / "owner", source_root=root,
                                owner_work_root=root, owner_evidence_root=root, output_root=root / "out",
                                evidence_root=root / "evidence", attempt_root=root / "attempt",
                                lease_path=root / "lease")

    def test_existing_output_rejected_before_publication(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); output = root / "out"; output.mkdir()
            with self.assertRaises(prepare.PreparationError):
                prepare._fresh(output, "output root")


if __name__ == "__main__":
    unittest.main()
