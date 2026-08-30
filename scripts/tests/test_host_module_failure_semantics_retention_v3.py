import ast
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest

SCRIPTS_ROOT = Path(__file__).resolve().parent.parent
if not hasattr(sys, "_mckernel_fp0006_authority_context"):
    sys.path.insert(0, str(SCRIPTS_ROOT))

import host_module_failure_semantics_retention_v3 as retention
import host_module_failure_semantics_v3 as semantics


class RetentionV3Tests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="hfs-retention-v3-")
        self.root = Path(self.temporary.name)
        self.build = self.root / "build"
        self.evidence = self.root / "evidence"
        self.build.mkdir()
        self.evidence.mkdir()

    def tearDown(self):
        self.temporary.cleanup()

    def test_sibling_imports_are_bound_to_the_exact_scripts_tree(self):
        self.assertEqual(
            (SCRIPTS_ROOT / "host_module_failure_semantics_retention_v3.py").resolve(),
            Path(retention.__file__).resolve(),
        )
        self.assertEqual(
            (SCRIPTS_ROOT / "host_module_failure_semantics_v3.py").resolve(),
            Path(semantics.__file__).resolve(),
        )

    def canonical_pair(self):
        manifest = semantics.canonical_bytes({"fixture": "retention-v3"})
        bundle = semantics.canonical_tar({"manifest.json": manifest})
        sidecar = semantics.raw_sidecar_bytes(retention.BUNDLE_NAME, bundle)
        return bundle, sidecar

    def write(self, name, data):
        (self.build / name).write_bytes(data)

    def status(self):
        return json.loads((self.evidence / retention.STATUS_NAME).read_text(
            encoding="utf-8"))

    def test_absent_pair_is_distinct_from_verified(self):
        result = retention.retain(self.build, self.evidence)
        self.assertEqual("absent", result["state"])
        self.assertEqual({}, result["retained"])
        self.assertEqual("absent", self.status()["state"])

    def test_canonical_pair_is_retained_and_verified(self):
        bundle, sidecar = self.canonical_pair()
        self.write(retention.BUNDLE_NAME, bundle)
        self.write(retention.SIDECAR_NAME, sidecar)
        result = retention.retain(self.build, self.evidence)
        self.assertEqual("verified", result["state"])
        self.assertEqual(bundle, (self.evidence / retention.BUNDLE_NAME).read_bytes())
        self.assertEqual(sidecar, (self.evidence / retention.SIDECAR_NAME).read_bytes())
        self.assertEqual(
            semantics.sha256_bytes(bundle),
            result["retained"][retention.BUNDLE_NAME]["sha256"],
        )

    def test_one_member_is_retained_but_classified_incomplete(self):
        bundle, _sidecar = self.canonical_pair()
        self.write(retention.BUNDLE_NAME, bundle)
        result = retention.retain(self.build, self.evidence)
        self.assertEqual("incomplete", result["state"])
        self.assertTrue((self.evidence / retention.BUNDLE_NAME).is_file())
        self.assertFalse((self.evidence / retention.SIDECAR_NAME).exists())

    def test_sidecar_cannot_bind_another_filename(self):
        bundle, _sidecar = self.canonical_pair()
        self.write(retention.BUNDLE_NAME, bundle)
        self.write(
            retention.SIDECAR_NAME,
            (semantics.sha256_bytes(bundle) + "  other.tar\n").encode("ascii"),
        )
        result = retention.retain(self.build, self.evidence)
        self.assertEqual("invalid", result["state"])
        self.assertIn("non-canonical", result["errors"][0]["reason"])
        self.assertTrue((self.evidence / retention.BUNDLE_NAME).is_file())
        self.assertTrue((self.evidence / retention.SIDECAR_NAME).is_file())

    def test_matching_sidecar_does_not_promote_noncanonical_tar(self):
        bundle = b"not a canonical tar"
        self.write(retention.BUNDLE_NAME, bundle)
        self.write(
            retention.SIDECAR_NAME,
            semantics.raw_sidecar_bytes(retention.BUNDLE_NAME, bundle),
        )
        result = retention.retain(self.build, self.evidence)
        self.assertEqual("invalid", result["state"])
        self.assertTrue(any(
            item["name"] == retention.BUNDLE_NAME for item in result["errors"]
        ))

    def test_symlink_source_is_rejected_without_dereference(self):
        bundle, sidecar = self.canonical_pair()
        target = self.root / "outside.tar"
        target.write_bytes(bundle)
        (self.build / retention.BUNDLE_NAME).symlink_to(target)
        self.write(retention.SIDECAR_NAME, sidecar)
        result = retention.retain(self.build, self.evidence)
        self.assertEqual("invalid", result["state"])
        self.assertFalse((self.evidence / retention.BUNDLE_NAME).exists())
        self.assertTrue((self.evidence / retention.SIDECAR_NAME).is_file())

    def test_symlink_build_directory_is_not_resolved(self):
        bundle, sidecar = self.canonical_pair()
        self.write(retention.BUNDLE_NAME, bundle)
        self.write(retention.SIDECAR_NAME, sidecar)
        alias = self.root / "build-alias"
        alias.symlink_to(self.build, target_is_directory=True)
        result = retention.retain(alias, self.evidence)
        self.assertEqual("invalid", result["state"])
        self.assertEqual({}, result["retained"])

    def test_preexisting_retention_output_fails_closed(self):
        (self.evidence / retention.STATUS_NAME).write_text("occupied\n", encoding="utf-8")
        with self.assertRaises(retention.RetentionError):
            retention.retain(self.build, self.evidence)

    def test_cli_succeeds_only_for_a_canonical_verified_pair(self):
        cases = ("verified", "absent", "incomplete", "stale", "noncanonical", "symlink")
        for case in cases:
            with self.subTest(case=case), tempfile.TemporaryDirectory(
                prefix="hfs-retention-v3-cli-"
            ) as directory:
                root = Path(directory)
                build = root / "build"
                evidence = root / "evidence"
                build.mkdir()
                evidence.mkdir()
                manifest = semantics.canonical_bytes({"fixture": case})
                bundle = semantics.canonical_tar({"manifest.json": manifest})
                sidecar = semantics.raw_sidecar_bytes(retention.BUNDLE_NAME, bundle)
                if case == "verified":
                    (build / retention.BUNDLE_NAME).write_bytes(bundle)
                    (build / retention.SIDECAR_NAME).write_bytes(sidecar)
                elif case == "incomplete":
                    (build / retention.BUNDLE_NAME).write_bytes(bundle)
                elif case == "stale":
                    (build / retention.BUNDLE_NAME).write_bytes(bundle)
                    (build / retention.SIDECAR_NAME).write_bytes(
                        semantics.raw_sidecar_bytes(
                            retention.BUNDLE_NAME, bundle + b"stale"
                        )
                    )
                elif case == "noncanonical":
                    bundle = b"not a canonical tar"
                    (build / retention.BUNDLE_NAME).write_bytes(bundle)
                    (build / retention.SIDECAR_NAME).write_bytes(
                        semantics.raw_sidecar_bytes(retention.BUNDLE_NAME, bundle)
                    )
                elif case == "symlink":
                    outside = root / "outside.tar"
                    outside.write_bytes(bundle)
                    (build / retention.BUNDLE_NAME).symlink_to(outside)
                    (build / retention.SIDECAR_NAME).write_bytes(sidecar)
                result = retention.main(
                    [
                        "--build-dir",
                        str(build),
                        "--evidence-dir",
                        str(evidence),
                    ]
                )
                self.assertEqual(0 if case == "verified" else 1, result)
                expected_state = {
                    "stale": "invalid",
                    "noncanonical": "invalid",
                    "symlink": "invalid",
                }.get(case, case)
                self.assertEqual(expected_state, json.loads(
                    (evidence / retention.STATUS_NAME).read_text(encoding="utf-8")
                )["state"])

    def test_module_parses_as_python_3_6(self):
        source = Path(retention.__file__).read_text(encoding="utf-8")
        try:
            ast.parse(source, filename=retention.__file__, feature_version=(3, 6))
        except TypeError:
            try:
                ast.parse(source, filename=retention.__file__, feature_version=6)
            except TypeError:
                ast.parse(source, filename=retention.__file__)


if __name__ == "__main__":
    unittest.main()
