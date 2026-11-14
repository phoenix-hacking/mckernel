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

    def test_practical_target_is_primary_and_legacy_values_are_deferred(self):
        practical = dict(scope_id="practical-kernel-apps-v1-20261017", milestones=[dict(
            id="M05", title="Lifecycle", engineering_state="blocked", completion_status="unassessed",
            exit_condition="Restore ownership", current_evidence_summary="Known shutdown failure",
            checks=[dict(id="P-M05-01", description="Resolve shutdown", status="open", evidence=["retained-failure.json"]),
                    dict(id="P-M05-02", description="Assess restoration", status="unassessed", evidence=[]),
                    dict(id="P-M05-03", description="Earlier bounded result", status="complete", evidence=[{"path":"result.json","sha256":"a"*64}])])],
            validation_budget=dict(fresh_guest_boots=2, complete_native_lifecycle_cycles=10,
                                   successful_application_launches=100, mixed_workload_minutes=60),
            next_actions=["Run the next reviewed repair"])
        def read(path, default):
            if path.name == "practical-milestones.json": return practical
            if path.name == "gate-map.json": return dict(status_counts={"PASS":2},native_gate_count=130,earned_points=3,total_points=100)
            return {}
        with mock.patch.object(progress,"read_json",side_effect=read),mock.patch.object(Path,"write_text") as write:
            report=progress.render(self.doc)
        write.assert_not_called()
        self.assertLess(report.index("## Primary target:"),report.index("## Stable kernel core:"))
        self.assertLess(report.index("## Stable kernel core:"),report.index("## Historical / DEFERRED qualification counters"))
        primary=report.split("## Primary target:",1)[1].split("## Snapshot",1)[0]
        self.assertIn("| M05 | Lifecycle | blocked | unassessed |",primary)
        self.assertIn("| P-M05-01 | Resolve shutdown | open | retained-failure.json |",primary)
        self.assertIn("| P-M05-02 | Assess restoration | unassessed | not recorded |",primary)
        self.assertIn('"sha256": "'+'a'*64+'"',primary)
        self.assertIn("Run the next reviewed repair",primary)
        self.assertNotIn("%",primary)
        self.assertIn(progress.bar(2,130),report)
        self.assertIn(progress.bar(3,100),report)
        self.assertIn("DEFERRED (historical ACTIVE)",report)

    def test_absent_practical_file_keeps_existing_render(self):
        with mock.patch.object(progress,"read_json",return_value={}):report=progress.render(self.doc)
        self.assertIn("## Acceptance Bars",report)
        self.assertNotIn("## Primary target:",report)
        self.assertIn("## Stable kernel core:",report)

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
