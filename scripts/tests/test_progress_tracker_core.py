#!/usr/bin/env python3
"""Reporting-only SC1 dashboard integration checks; no campaign execution."""
import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
try:
    spec = importlib.util.spec_from_file_location(
        "progress_tracker_core_under_test", ROOT / "scripts/update_progress_tracker.py"
    )
    progress = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(progress)
finally:
    sys.path.pop(0)


class ProgressCoreIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.doc = progress.stable_core_tracker.load_tracker()

    def test_engineering_view_precedes_acceptance_without_percentage(self):
        with mock.patch.object(progress, "read_json", return_value={}):
            report = progress.render(self.doc)
        panel = report.split("## Stable kernel core: engineering progress", 1)[1].split(
            "## Acceptance Bars", 1
        )[0]
        self.assertIn("../../../STABLE-CORE.md", panel)
        self.assertIn(self.doc["as_of"], panel)
        self.assertIn(self.doc["source_revision"], panel)
        self.assertIn(self.doc["status"], panel)
        self.assertNotIn("%", panel)
        self.assertIn("Infrastructure results never count as kernel results", panel)
        counts = progress.stable_core_tracker.summarize(self.doc)["by_kind"]
        for kind, label in (("core", "Kernel behavior"), ("enabler", "Test / execution infrastructure")):
            row = "| " + label + " | " + " | ".join(
                str(counts[kind][status]) for status in progress.stable_core_tracker.STATUSES
            ) + " |"
            self.assertIn(row, panel)

    def test_default_refresh_writes_only_both_reports_in_disposable_root(self):
        with tempfile.TemporaryDirectory(prefix="mckernel-report-test-") as directory:
            root = Path(directory)
            output = root / "PROGRESS.md"
            with mock.patch.object(progress, "ROOT", root), \
                    mock.patch.object(progress.stable_core_tracker, "validate") as validate, \
                    mock.patch.object(progress.stable_core_tracker, "load_tracker", return_value=self.doc), \
                    mock.patch.object(progress, "read_json", return_value={}), \
                    mock.patch.object(sys, "argv", ["update_progress_tracker.py", "--output", str(output)]), \
                    mock.patch("builtins.print"):
                self.assertEqual(progress.main(), 0)
                validate.assert_any_call(self.doc, root=root)
            self.assertEqual({p.name for p in root.iterdir()}, {"PROGRESS.md", "STABLE-CORE.md"})
            self.assertEqual((root / "STABLE-CORE.md").read_text(),
                             progress.stable_core_tracker.render(self.doc))
            self.assertIn(self.doc["status"], output.read_text())

    def test_invalid_core_data_fails_before_any_write(self):
        with mock.patch.object(progress.stable_core_tracker, "load_tracker", return_value={}), \
                mock.patch.object(sys, "argv", ["update_progress_tracker.py"]), \
                mock.patch.object(Path, "write_text") as write:
            with self.assertRaises(progress.stable_core_tracker.TrackerError):
                progress.main()
            write.assert_not_called()

    def test_generated_core_symlink_is_not_followed(self):
        with tempfile.TemporaryDirectory(prefix="mckernel-report-test-") as directory:
            root = Path(directory)
            (root / "STABLE-CORE.md").symlink_to(root / "unrelated.md")
            with mock.patch.object(progress, "ROOT", root), \
                    mock.patch.object(progress.stable_core_tracker, "validate"), \
                    mock.patch.object(progress.stable_core_tracker, "load_tracker", return_value=self.doc), \
                    mock.patch.object(progress, "read_json", return_value={}), \
                    mock.patch.object(sys, "argv", ["update_progress_tracker.py", "--output", str(root / "PROGRESS.md")]):
                with self.assertRaises(progress.stable_core_tracker.TrackerError):
                    progress.main()
            self.assertFalse((root / "unrelated.md").exists())
            self.assertFalse((root / "PROGRESS.md").exists())


if __name__ == "__main__":
    unittest.main()
