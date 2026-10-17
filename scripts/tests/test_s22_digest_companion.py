"""Regress the actual scratch22 root-digest companion failure without builds."""

from __future__ import print_function

import copy
import io
from contextlib import redirect_stderr
import unittest
from unittest import mock

from scripts import native_rust_build_surface_audit as audit
from scripts import rocky_rust_staging as staging
from scripts.tests import test_native_rust_build_surface_audit as fixtures


OLD_ROOT_SHA256 = "ead31123d69508bd678f321137e9fba023621a46cdf86aa3466381b966b52b44"
CURRENT_ROOT_SHA256 = "a353b2915a4038e7739d01cc440376daf091367f976cf6de297bceb1dd59fce8"
ROOT_PATH = "host-kernel/native-rust/ihk_smp_x86_64.rs"


class Scratch22DigestCompanionTests(unittest.TestCase):
    def setUp(self):
        # Reuse the existing complete source-surface fixture and its teardown.
        self.fixture = fixtures.NativeRustBuildSurfaceAuditTests(
            "test_repository_has_one_authoritative_surface"
        )
        self.fixture.setUp()

    def tearDown(self):
        self.fixture.tearDown()

    def test_current_exact_root_and_companion_bindings_pass(self):
        manifest = self.fixture.load_manifest()
        root = next(row["source"] for row in manifest["modules"]
                    if row["source"]["repository_path"] == ROOT_PATH)
        self.assertEqual(CURRENT_ROOT_SHA256, root["sha256"])
        result = audit.audit(self.fixture.repo)
        self.assertEqual(3, result["module_count"])

    def test_actual_old_locked_digest_refuses_current_root(self):
        # Recreate the real failure: manifest and checker agree with each other
        # on the old digest, but the corrected production root has new bytes.
        manifest = self.fixture.load_manifest()
        for row in manifest["modules"]:
            if row["source"]["repository_path"] == ROOT_PATH:
                row["source"]["sha256"] = OLD_ROOT_SHA256
        self.fixture.write_manifest(manifest)
        modules = copy.deepcopy(staging.EXPECTED_MODULES)
        for row in modules:
            if row["source_repository_path"] == ROOT_PATH:
                row["source_sha256"] = OLD_ROOT_SHA256
        captured = io.StringIO()
        with mock.patch.object(staging, "EXPECTED_MODULES", modules):
            with redirect_stderr(captured):
                status = audit.main(["--repo", self.fixture.repo])
        self.assertEqual(1, status)
        self.assertEqual(
            "native Rust build-surface audit failed: module root digest drift: "
            "ihk_smp_x86_64.rs\n",
            captured.getvalue(),
        )


if __name__ == "__main__":
    unittest.main()
