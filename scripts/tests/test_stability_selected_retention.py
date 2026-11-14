"""Source-contract tests only; no compilation or runtime acceptance."""

import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).parent))
import prepare_stability_selected_retention as retention


class SourceContractTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.bytes = {name: ("synthetic:" + name).encode() for name in (
            "stability_observer.rs", "sysfs_memory.rs", "smp_application.rs",
            "smp_service.rs", "smp_memory.rs", "ihk_smp_x86_64.rs",
            "mcctrl_process.rs", "application_syscall.rs")}
        self.manifest = {name: hashlib.sha256(data).hexdigest()
                         for name, data in self.bytes.items()}
        self.source = self.root / "source"
        self.source.mkdir()
        for name, data in self.bytes.items():
            (self.source / name).write_bytes(data)

    def tearDown(self):
        self.tmp.cleanup()

    def test_positive_contract_membership(self):
        got = retention.validate_source_contract(self.source, 2, self.manifest)
        self.assertEqual(got, self.bytes)

    def test_each_ownership_critical_drift_is_rejected(self):
        for name in ("stability_observer.rs", "sysfs_memory.rs", "smp_application.rs",
                     "smp_service.rs", "smp_memory.rs"):
            with self.subTest(name=name):
                (self.source / name).write_bytes(b"drift:" + name.encode())
                with self.assertRaisesRegex(ValueError, "hash mismatch"):
                    retention.validate_source_contract(self.source, 2, self.manifest)
                (self.source / name).write_bytes(self.bytes[name])

    def test_missing_and_extra_members_are_rejected(self):
        (self.source / "stability_observer.rs").unlink()
        with self.assertRaisesRegex(ValueError, "membership mismatch"):
            retention.validate_source_contract(self.source, 2, self.manifest)
        (self.source / "stability_observer.rs").write_bytes(self.bytes["stability_observer.rs"])
        (self.source / "unexpected.rs").write_bytes(b"extra")
        with self.assertRaisesRegex(ValueError, "membership mismatch"):
            retention.validate_source_contract(self.source, 2, self.manifest)

    def test_authoritative_modes_are_exact_held_v1(self):
        for number in (2, 3):
            with self.subTest(mode=number):
                manifest, authority = retention.authoritative_source_manifest(number)
                self.assertEqual(len(manifest), 51)
                self.assertEqual(authority["manifest"]["sha256"], retention.SOURCE_MANIFEST_IDENTITY["sha256"])
                self.assertEqual(manifest["application_syscall.rs"], retention.FROZEN_SOURCE[number]["application_syscall.rs"])
                self.assertEqual(manifest["smp_application_syscall.rs"], retention.FROZEN_SOURCE[number]["smp_application_syscall.rs"])
                self.assertEqual(manifest["stability_phase.rs"], retention.FROZEN_SOURCE[number]["stability_phase.rs"])
                actual = retention.validate_source_contract(Path(authority["tree"]), number)
                self.assertEqual(sorted(actual), sorted(manifest))

    def test_authoritative_manifest_byte_drift_is_rejected(self):
        package = self.root / "package"
        package.mkdir()
        original = (Path(retention.__file__).resolve().parent / "fixtures" /
                    "stability-selected-retention-v1" / retention.SOURCE_MANIFEST_NAME).read_bytes()
        (package / retention.SOURCE_MANIFEST_NAME).write_bytes(original + b" ")
        with self.assertRaisesRegex(ValueError, "manifest identity drifted"):
            retention.authoritative_source_manifest(2, package)

    def test_directory_enumeration_is_bounded(self):
        large = self.root / "large"
        large.mkdir()
        for index in range(retention.MAX_FILES + 1):
            (large / ("member-%03d.rs" % index)).write_bytes(b"")
        with self.assertRaisesRegex(ValueError, "flat bounded"):
            retention.source_names(large)

    def test_full_staging_for_each_exact_mode(self):
        for number, mode in ((2, "postpublish-notify"), (3, "recoverable-backpressure")):
            with self.subTest(mode=mode):
                _, authority = retention.authoritative_source_manifest(number)
                output = self.root / ("out-" + str(number))
                retention.prepare(Path(authority["tree"]), output, mode)
                record = json.loads((output / "record.json").read_text())
                self.assertEqual(record["status"], "PREPARED_NOT_COMPILED_NOT_EXECUTED")
                self.assertFalse(record["execution_authorized"])
                self.assertEqual(len(record["authoritative_source"]["members"]), 51)
                self.assertEqual(record["original_held_source_bindings"], retention.FROZEN_SOURCE[number])
                self.assertTrue(all(row["inverse_restoration_byte_equal"] for row in record["files"]))


if __name__ == "__main__":
    unittest.main()
