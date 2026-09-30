import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest import mock

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import native_rust_exact_mckernel_image_request_prepare as prepare
from scripts.tests.test_native_rust_exact_mckernel_image_container_owner import OwnerTests


class RequestPrepareTests(unittest.TestCase):
    def test_supported_v2_rustc_identity_is_exact(self):
        self.assertEqual(prepare.owner.EXPECTED_V2_RUSTC_VERSION,
                         "rustc 1.95.0-nightly (c04308580 2026-02-18)")

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

    def test_publish_never_replaces_an_existing_final(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); toolchain = root / "toolchain.json"; request = root / "request.json"
            toolchain.write_text('{"incumbent":true}\n', encoding="utf-8")
            with self.assertRaisesRegex(prepare.PreparationError, "toolchain manifest must be fresh"):
                prepare._publish({"schema": "fixture"}, toolchain, request,
                                 lambda path: {"toolchain_manifest": str(path)}, lambda _value: None)
            self.assertEqual(toolchain.read_text(encoding="utf-8"), '{"incumbent":true}\n')
            self.assertFalse(request.exists())
            self.assertFalse(any(path.name.startswith(".mckernel-image-") for path in root.iterdir()))

    def test_failed_private_stage_write_preserves_error_and_leaves_no_artifact(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            def short_write(path, _value):
                Path(path).write_text("{", encoding="utf-8")
                raise OSError("injected short staging write")
            with mock.patch.object(prepare, "_write_new", side_effect=short_write):
                with self.assertRaisesRegex(OSError, "injected short staging write"):
                    prepare._staged_json(root, "mckernel-image-request", {"schema": "fixture"})
            self.assertFalse(any(path.name.startswith(".mckernel-image-request-") for path in root.iterdir()))

    def test_concurrent_publication_is_no_replace_and_never_exposes_partial_json(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); toolchain = root / "toolchain.json"; request = root / "request.json"
            start = threading.Barrier(7); errors = []; successes = []

            def make(path):
                return {"toolchain_manifest": str(path), "sha256": prepare._digest(path)}

            def validate(value):
                self.assertTrue(Path(value["toolchain_manifest"]).is_file())

            def publisher(index):
                start.wait()
                try:
                    successes.append(prepare._publish({"schema": "fixture", "writer": index},
                                                       toolchain, request, make, validate))
                except prepare.PreparationError as exc:
                    errors.append(str(exc))

            workers = [threading.Thread(target=publisher, args=(index,)) for index in range(6)]
            for worker in workers: worker.start()
            start.wait()
            while any(worker.is_alive() for worker in workers):
                for path in (toolchain, request):
                    if path.exists():
                        # The reader races publication: an existing name must
                        # always name a complete, parseable JSON document.
                        json.loads(path.read_text(encoding="utf-8"))
            for worker in workers: worker.join()
            self.assertEqual(len(successes), 1)
            self.assertEqual(len(errors), 5)
            self.assertTrue(all("must be fresh" in error or "already exists" in error
                                for error in errors))
            self.assertEqual(json.loads(request.read_text(encoding="utf-8")), successes[0])
            self.assertFalse(any(path.name.startswith(".mckernel-image-") for path in root.iterdir()))

    def _v2_prepare_fixture(self):
        """Reuse the owner's full admitted v2 fixture, then prepare fresh outputs."""
        fixture = OwnerTests("test_v2_owner_admission_and_offline_container_fixture")
        fixture.setUp()
        try:
            fixture.test_v2_owner_admission_and_offline_container_fixture()
            nightly = fixture.root / "v2-nightly"
            rustc = nightly / "bin/rustc"
            rustc.write_text("#!/bin/sh\necho '" + prepare.owner.EXPECTED_V2_RUSTC_VERSION + "'\n", encoding="utf-8")
            rustc.chmod(0o755)
            toolchain = json.loads(fixture.toolchain.read_text(encoding="utf-8"))
            toolchain["mounted_tools"]["rustc"]["sha256"] = prepare._digest(rustc)
            toolchain["toolchain_roots"][1]["inventory"] = prepare.owner._closure_inventory(
                nightly, nightly, Path("/nightly"))
            fixture.toolchain.write_text(json.dumps(toolchain, sort_keys=True), encoding="utf-8")
            work = fixture.root / "prepare-work"; work.mkdir(); work.chmod(0o700)
            owner_evidence = fixture.root / "prepare-owner-evidence"; owner_evidence.mkdir()
            values = {
                "candidate_manifest": fixture.manifest,
                "backup_root": fixture.backup,
                "backup_inventory": prepare.owner._tree_inventory(fixture.backup),
                "build_output": fixture.root / "v2-out",
                "image_receipt": fixture.root / "image-receipt.json",
                "image_id": fixture.image,
                "nightly_root": nightly,
                "host_git": {"path": str(fixture.tools / "git"),
                             "sha256": prepare._digest(fixture.tools / "git")},
                "driver_path": fixture.driver,
                "provenance_path": fixture.provenance,
                "host_owner_path": prepare.owner._HOST_OWNER_PATH,
                "source_root": fixture.source,
                "owner_work_root": work,
                "owner_evidence_root": owner_evidence,
                "output_root": work / "output",
                "evidence_root": work / "evidence",
                "attempt_root": owner_evidence / "attempt",
                "lease_path": fixture.root / "prepare-lease.json",
                "common_exclusion_path": str(fixture.common),
                "toolchain_manifest": fixture.root / "prepared-toolchain.json",
                "request_path": fixture.root / "prepared-request.json",
                "disk_admission": {"host_root": str(fixture.root), "scratch_root": str(fixture.root),
                                   "host_device": fixture.root.stat().st_dev,
                                   "scratch_device": fixture.root.stat().st_dev,
                                   "host_free_floor": 16 * 2**30,
                                   "scratch_free_floor": 12 * 2**30},
                "expected_toolchain_lock_sha256": "fd3d7a13e1b8b5d103f7e59d22f17c9e4b99cc937637decaa66749acfae6c802",
            }
            return fixture, values
        except BaseException:
            fixture.tearDown()
            raise

    def test_prepare_publishes_a_request_accepted_by_actual_owner_validation(self):
        fixture, values = self._v2_prepare_fixture()
        try:
            request = prepare.prepare(**values)
            self.assertEqual(json.loads(Path(values["request_path"]).read_text(encoding="utf-8")), request)
            self.assertEqual(request["toolchain_lock_sha256"], values["expected_toolchain_lock_sha256"])
            self.assertEqual(prepare.owner.ImageOwner(request).validate()["toolchain"],
                             Path(values["toolchain_manifest"]))
        finally:
            fixture.tearDown()

    def test_prepare_rejects_receipt_lock_that_differs_from_independent_expected_value(self):
        fixture, values = self._v2_prepare_fixture()
        try:
            values["expected_toolchain_lock_sha256"] = "0" * 64
            with self.assertRaisesRegex(prepare.PreparationError, "toolchain lock differs"):
                prepare.prepare(**values)
            self.assertFalse(Path(values["toolchain_manifest"]).exists())
            self.assertFalse(Path(values["request_path"]).exists())
        finally:
            fixture.tearDown()

    def test_prepare_rejects_drifted_library_observation_evidence(self):
        fixture, values = self._v2_prepare_fixture()
        try:
            (fixture.root / "tool-observation.json").write_text('{"libraries":{}}\n', encoding="utf-8")
            with self.assertRaisesRegex(prepare.PreparationError, "evidence drift"):
                prepare.prepare(**values)
            self.assertFalse(Path(values["toolchain_manifest"]).exists())
            self.assertFalse(Path(values["request_path"]).exists())
        finally:
            fixture.tearDown()

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
