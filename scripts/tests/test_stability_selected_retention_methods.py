"""Structural source-contract checks for the native retention method harness."""
from pathlib import Path
import unittest

ROOT = Path(__file__).parent / "fixtures/stability-selected-retention-v1"


class NativeRetentionMethodHarnessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.harness = (ROOT / "native_methods_harness.rs").read_text()

    def test_harness_binds_actual_staged_method_snippets(self):
        for name in ("response-prepare.rs", "return-prepare.rs", "cancel-guard.rs",
                     "mailbox-retention.append.rs", "phase-retention.append.rs"):
            self.assertIn('include_str!("%s")' % name, self.harness)
            self.assertTrue((ROOT / name).is_file())
        self.assertIn("verification_prepare_retained", (ROOT / "response-prepare.rs").read_text())
        self.assertIn("stability_retention_pre_publish", (ROOT / "mailbox-retention.append.rs").read_text())

    def test_required_stage_commit_wake_matrix_and_claim_cases(self):
        for stage in (0, 1, 2, 4, 5, 6, 255):
            self.assertIn("stage: %d" % stage, self.harness)
        for commit in (0, 1, 2):
            self.assertIn("commit: %d" % commit, self.harness)
        self.assertGreaterEqual(self.harness.count("wake: false"), 3)
        self.assertGreaterEqual(self.harness.count("wake: true"), 3)
        self.assertIn("changed: true", self.harness)
        self.assertIn("selected: false", self.harness)

    def test_cancellation_and_aligned_drop_contracts_are_explicit(self):
        self.assertIn("cancel_after: true", self.harness)
        self.assertIn("aligned_backing_counters", self.harness)
        self.assertIn("explicit_no_release_drop_assertions", self.harness)
        self.assertIn("assert!(aligned_backing_counters", self.harness)


if __name__ == "__main__":
    unittest.main()
