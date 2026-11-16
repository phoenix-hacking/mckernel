"""Focused offline parser, original weighting and complete Markdown reporting."""

from contextlib import redirect_stdout
import copy
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


SPEC = importlib.util.spec_from_file_location(
    "m14_m15_progress", Path(__file__).resolve().parents[1] / "m14_m15_progress.py")
progress = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(progress)
REPO = Path(__file__).resolve().parents[2]


def small_tracker():
    tasks = []
    for ident, parent, value in (("M14-F01-a", "M14-F01", 100),
                                  ("M14-F01-b", "M14-F01", 0),
                                  ("M14-F02-a", "M14-F02", 100),
                                  ("M15-F01-a", "M15-F01", 0)):
        tasks.append(dict(id=ident, parent=parent, percent_complete=value,
                          counted_in_requirement_rollup=True, title="Real required behavior",
                          done_when="Matching behavior and ownership are proved.",
                          owner="Root", evidence=["docs/verification/pass.json"]))
    tasks.append(dict(id="REGISTER:not-an-original", percent_complete=100,
                      counted_in_requirement_rollup=False))
    requirements = [dict(id=ident, parent=None, accepted=False,
                         task_ids=[task["id"] for task in tasks if task.get("parent") == ident])
                    for ident in ("M14-F01", "M14-F02", "M15-F01")]
    return dict(schema="mckernel-m14-m15-closure-progress-v1", original_criteria_unchanged=True,
                tasks=tasks, requirements=requirements, updated_at="2026-11-15T00:00:00Z",
                summaries={"M14": dict(original_gate_ids=["M14-F01", "M14-F02"], milestone_accepted=False),
                           "M15": dict(original_gate_ids=["M15-F01"], milestone_accepted=False)})


def sidecar(entry):
    return dict(schema="mckernel-m14-m15-engineering-progress-v1", checks={"M14-F01-b": entry})


class ProgressTests(unittest.TestCase):
    def test_original_weights_are_gate_means_not_flat_atomic_count(self):
        document = small_tracker()
        original = copy.deepcopy(document)
        report = progress.parse_tracker(document, expected_count=4)
        self.assertEqual((report["accepted"], report["open"], report["total"]), (2, 2, 4))
        self.assertEqual(report["parent_percent"]["M14-F01"], 50)
        self.assertEqual(report["milestones"]["M14"]["checklist_percent"], 75)
        self.assertEqual(document, original)
        document["requirements"][0]["accepted"] = True
        self.assertEqual(progress.parse_tracker(document, expected_count=4)["parent_percent"]["M14-F01"], 100)

    def test_nested_declared_children_and_cycle_rejection(self):
        document = small_tracker()
        document["requirements"].append(dict(id="M14-region", parent="M14-F01", accepted=False,
                                               task_ids=["M14-F01-b"]))
        document["tasks"][1]["parent"] = "M14-region"
        document["requirements"][0]["task_ids"] = ["M14-F01-a"]
        document["requirements"][0]["child_requirements"] = ["M14-region"]
        report = progress.parse_tracker(document, expected_count=4)
        self.assertEqual(report["parent_percent"]["M14-F01"], 50)
        document["requirements"][-1]["child_requirements"] = ["M14-F01"]
        document["requirements"][0]["parent"] = "M14-region"
        with self.assertRaisesRegex(ValueError, "Cycle"):
            progress.parse_tracker(document, expected_count=4)

    def test_parser_rejects_changed_denominator_partial_acceptance_and_reparenting(self):
        for mutate in (
            lambda doc: doc["tasks"].append(copy.deepcopy(doc["tasks"][0])),
            lambda doc: doc["tasks"][0].update(percent_complete=90),
            lambda doc: doc["tasks"][0].update(percent_complete=True),
            lambda doc: doc["tasks"][0].update(parent="M15-F01"),
            lambda doc: doc.update(original_criteria_unchanged=False),
        ):
            document = small_tracker()
            mutate(document)
            with self.assertRaises(ValueError):
                progress.parse_tracker(document, expected_count=4)
        with self.assertRaisesRegex(ValueError, "denominator"):
            progress.parse_tracker(small_tracker())

    def test_engineering_completed_steps_require_evidence_and_do_not_accept_check(self):
        entry = dict(engineering_steps=[
            dict(id="emit", description="Changed object emitted", done=True, evidence=["actual.json"]),
            dict(id="behavior", description="Matching behavior", done=False, evidence=[])])
        engineering = progress.parse_engineering(sidecar(entry), {"M14-F01-b"})["M14-F01-b"]
        self.assertEqual(engineering["checkpoint_percent"], 50)
        self.assertEqual(progress.parse_tracker(small_tracker(), expected_count=4)["tasks"]["M14-F01-b"]["percent_complete"], 0)
        entry["engineering_steps"][0]["evidence"] = []
        with self.assertRaisesRegex(ValueError, "no evidence"):
            progress.parse_engineering(sidecar(entry), {"M14-F01-b"})
        with self.assertRaisesRegex(ValueError, "override original acceptance"):
            progress.parse_engineering(sidecar(dict(acceptance_percent=90)), {"M14-F01-b"})

    def test_explicit_weights_and_estimate_ranges_require_rationale(self):
        entry = dict(engineering_steps=[
            dict(id="one", description="Concrete result", done=True, evidence=["actual.json"], weight=2),
            dict(id="two", description="Remaining result", done=False, evidence=[], weight=1)])
        with self.assertRaisesRegex(ValueError, "rationale"):
            progress.parse_engineering(sidecar(entry), {"M14-F01-b"})
        entry["weight_rationale"] = "Original operation has two independent checks plus one remaining check."
        self.assertEqual(progress.parse_engineering(sidecar(entry), {"M14-F01-b"})["M14-F01-b"]["checkpoint_percent"], 66.67)
        estimate = dict(estimate_range=[30, 50], rationale="Bounded estimate only", latest_passing_evidence=["actual.json"])
        self.assertEqual(progress.parse_engineering(sidecar(estimate), {"M14-F01-b"})["M14-F01-b"]["checkpoint_percent"], None)
        for bad in ([90, 20], [0, 101], [False, 50], [float("nan"), 50]):
            estimate["estimate_range"] = bad
            with self.assertRaises(ValueError):
                progress.parse_engineering(sidecar(estimate), {"M14-F01-b"})

    def test_actual_original_counts_rollups_and_every_open_row_stopped(self):
        report = progress.load_progress(REPO)
        canonical = json.loads((REPO / progress.TRACKER).read_text())
        counted = [row for row in canonical["tasks"] if row["counted_in_requirement_rollup"] is True]
        closed = sum(row["percent_complete"] == 100 for row in counted)
        self.assertEqual((report["total"], report["accepted"], report["open"]), (156, closed, 156 - closed))
        for milestone in ("M14", "M15"):
            self.assertEqual(report["milestones"][milestone]["open"],
                             sum(row["percent_complete"] == 0 and row["id"].startswith(milestone + "-")
                                 for row in counted))
            self.assertEqual(report["milestones"][milestone]["checklist_percent"],
                             canonical["summaries"][milestone]["checklist_percent_complete"])
        text = progress._markdown(report, "STOPPED")
        for row in report["open_rows"]:
            self.assertIn("| `" + row["id"] + "` —", text)
        self.assertEqual(sum(line.startswith("| `M") for line in text.splitlines()), report["open"])
        self.assertIn("**Campaign: STOPPED.**", text)
        self.assertIn("python3 -B scripts/m14_m15.py stop", text)
        self.assertIn("unknown", text)
        self.assertNotIn("0% — active", text)

    def test_aggregate_accept_lists_actual_unmet_original_children(self):
        document = small_tracker()
        row = dict(id="M14-F01-ACCEPT", parent="M14-F01", percent_complete=0,
                   counted_in_requirement_rollup=True, done_when="Root accepts original scope.")
        document["tasks"].append(row)
        document["requirements"][0]["task_ids"].append(row["id"])
        report = progress.parse_tracker(document, expected_count=5)
        missing = progress._next_missing(row, report)
        self.assertIn("M14-F01-b", missing)
        self.assertNotIn("M14-F01-a", missing)

    def test_render_is_atomic_only_on_change_and_cli_repeats_all_rows(self):
        with tempfile.TemporaryDirectory() as temporary:
            repo = Path(temporary)
            path = repo / progress.TRACKER
            path.parent.mkdir(parents=True)
            path.write_bytes((REPO / progress.TRACKER).read_bytes())
            expected = progress.render_progress(repo)
            target = repo / progress.MARKDOWN
            before = target.stat().st_mtime_ns
            with patch.object(progress.os, "replace", side_effect=AssertionError("Unchanged write")):
                self.assertEqual(progress.render_progress(repo), expected)
            self.assertEqual(target.stat().st_mtime_ns, before)
            for _ in range(2):
                stdout = io.StringIO()
                with redirect_stdout(stdout):
                    self.assertEqual(progress.main(["status", "--repo", str(repo)]), 0)
                self.assertEqual(stdout.getvalue(), expected)
            with patch.object(progress.os, "replace", wraps=progress.os.replace) as replace:
                progress.render_progress(repo, campaign_state="RUNNING")
                self.assertEqual(replace.call_count, 2)
                self.assertEqual({call.args[1] for call in replace.call_args_list},
                                 {repo / progress.MARKDOWN, repo / progress.ENGINEERING_MARKDOWN})
            self.assertFalse(list(target.parent.glob(".M14-M15-OPEN-DELIVERABLES.md.*")))

    def test_invalid_optional_sidecar_does_not_hide_any_original_open_row(self):
        with tempfile.TemporaryDirectory() as temporary:
            repo = Path(temporary)
            path = repo / progress.TRACKER
            path.parent.mkdir(parents=True)
            path.write_bytes((REPO / progress.TRACKER).read_bytes())
            (repo / progress.ENGINEERING).write_text('{"schema":"bad"}')
            report = progress.load_progress(repo)
            self.assertEqual(len(report["open_rows"]), progress.load_progress(REPO)["open"])
            self.assertIn("unknown", report["engineering_warning"])
            self.assertTrue(all(not row["engineering"] for row in report["open_rows"]))

    def test_stop_state_overrides_explicit_check_activity_and_distinguishes_stopping(self):
        report = progress.load_progress(REPO)
        ident = report["open_rows"][0]["id"]
        runtime = dict(phase="running", goal={"status": "active"}, updated_at="actual-time",
                       active_turns={"root": "turn"},
                       active_work=[dict(original_check=ident, status="running",
                                         owner="Actual assigned owner", updated_at="assignment-time")],
                       agents={"unrelated": {"status": "active"}})
        state, updated, work = progress._runtime(REPO, "STOPPED", runtime)
        self.assertEqual((state, updated), ("STOPPING", "actual-time"))
        text = progress._markdown(report, state, updated, work)
        self.assertIn("Actual assigned owner", text)
        self.assertIn("assignment-time", text)
        self.assertNotIn("working / open", text)
        runtime["active_turns"] = {}
        self.assertEqual(progress._runtime(REPO, "STOPPED", runtime)[0], "STOPPED")
        self.assertEqual(progress._runtime(REPO, None, runtime)[0], "RUNNING")
        row = next(row for row in report["open_rows"] if row["id"] == ident)
        self.assertEqual(progress._row_state(row, "RUNNING", work[row["id"]]), "working / open")
        self.assertEqual(progress._row_state(row, "RUNNING", {}), "open")
        self.assertEqual(progress._row_state(row, "RUNNING", {"status": "blocked"}), "waiting / open")

    def test_default_runtime_reads_only_existing_canonical_state(self):
        with tempfile.TemporaryDirectory() as temporary:
            repo = Path(temporary)
            state = repo / ".git/os-autopilot/state.json"
            state.parent.mkdir(parents=True)
            state.write_text(json.dumps(dict(phase="running", goal={"status": "active"},
                                             stop_now=True, active_turns={}, updated_at="state-time")))
            self.assertEqual(progress._runtime(repo), ("STOPPED", "state-time", {}))

    def test_remaining_estimates_are_explicit_and_acceptance_is_independent(self):
        document = dict(schema="mckernel-engineering-work-remaining-v1", estimates={
            "M14-F01-b": dict(remaining_range=[25, 55], confidence="low",
                rationale="Source exists; actual matching behavior remains unobserved.",
                evidence=["actual-source.rs"])})
        entries = progress.parse_remaining(document, {"M14-F01-b"})
        report = dict(remaining=entries)
        self.assertEqual(progress._remaining_text(report, "M14-F01-b"),
                         "25–55% remaining (low confidence)")
        self.assertEqual(progress._remaining_text(report, "M14-F01-b", accepted=True),
                         "0% — accepted")
        self.assertEqual(progress._remaining_text(report, "unassessed"), "unknown")
        for bad in ([55, 25], [0, 101], [False, 50]):
            document["estimates"]["M14-F01-b"]["remaining_range"] = bad
            with self.assertRaises(ValueError):
                progress.parse_remaining(document, {"M14-F01-b"})

    def test_display_shows_all_parent_scopes_and_only_remaining_work_percentages(self):
        report = progress.load_progress(REPO)
        rendered = progress._markdown(report, "RUNNING")
        parents = [r for r in report["requirements"].values() if r.get("parent") is None]
        for row in parents:
            self.assertIn("| " + row["id"] + " —", rendered)
        self.assertIn("Every percentage below estimates engineering work remaining", rendered)
        self.assertNotIn("80.19%", rendered)
        self.assertNotIn("76.25%", rendered)
        self.assertNotIn("% checkpoints", rendered)
        self.assertIn("Smaller engineering increments", rendered)
        self.assertIn("four affected controller-consumer integration methods", rendered)
        self.assertEqual(sum(line.startswith("| `M") for line in rendered.splitlines()), report["open"])

    def test_invalid_remaining_estimates_never_hide_original_checks(self):
        with tempfile.TemporaryDirectory() as temporary:
            repo = Path(temporary)
            path = repo / progress.TRACKER
            path.parent.mkdir(parents=True)
            path.write_bytes((REPO / progress.TRACKER).read_bytes())
            (repo / progress.ESTIMATES).write_text('{"schema":"invalid"}')
            report = progress.load_progress(repo)
            self.assertTrue(report["engineering_warning"])
            self.assertFalse(report["remaining"])
            self.assertEqual(len(report["open_rows"]), report["open"])
            self.assertIn("unknown", progress._markdown(report, "STOPPED"))


if __name__ == "__main__":
    unittest.main()
