#!/usr/bin/env python3
"""Pure reporting tests; no temporary files, builds, guests or campaign work."""

from __future__ import annotations

import copy
import importlib.util
import io
import json
import unittest
from contextlib import ExitStack, redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock


SCRIPT = Path(__file__).resolve().parents[1] / "stable_core_tracker.py"
SPEC = importlib.util.spec_from_file_location("stable_core_tracker", SCRIPT)
tracker = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(tracker)


def fixture():
    """Every status appears once in each kind, independent of live repo data."""
    doc = {
        "schema_version": 1,
        "milestone": "SC1",
        "title": "Stable core engineering tracker",
        "as_of": "2026-09-28",
        "source_revision": "abcde12345" * 4,
        "status": "NOT YET DEMONSTRATED",
        "profile": ["One declared CPU and input pair."],
        "definition": ["Every required scoped behavior passes its original contract."],
        "scope_notes": ["Historical evidence requires replay on changed sources."],
        "exclusions": [{"name": "MPI", "route": "M07", "reason": "Separate profile."}],
        "priority": ["core-blocked", "core-baseline", "enabler-verified"],
        "references": {"measurement": "evidence/result.json", "scope": "docs/scope.md"},
        "areas": [
            {"id": "core", "title": "Core behavior", "kind": "core", "owner": "Core role",
             "task_refs": ["M01-A"]},
            {"id": "enabler", "title": "Observation tools", "kind": "enabler",
             "owner": "Observer role", "task_refs": ["M00-A"]},
        ],
        "items": [],
    }
    for area in ("core", "enabler"):
        for status in tracker.STATUSES:
            doc["items"].append({
                "id": f"{area}-{status}", "area": area,
                "title": f"Observe {area} {status} boundary",
                "status": status,
                "result": f"Exact scoped {area} {status} result",
                "next_check": f"Check {area} {status} against the retained input pair",
                "depends_on": ["core-baseline"] if status == "blocked" else [],
                "evidence": ["scope" if status in ("unmeasured", "planned") else "measurement"],
            })
    return doc


class MemoryRepo:
    """A mocked filesystem that records writes without creating any files."""

    def __init__(self, doc=None):
        self.root = Path("/reporting-test-repository")
        self.doc = fixture() if doc is None else doc
        self.files = {
            self.root / tracker.INPUT_RELATIVE: json.dumps(self.doc).encode(),
            self.root / tracker.TASKS_RELATIVE: json.dumps({
                "tasks": [{"id": "M01-A"}, {"id": "M00-A"}]
            }).encode(),
            self.root / "evidence/result.json": b'{"result": "preserved"}\n',
            self.root / "docs/scope.md": b"Declared scope\n",
        }
        self.symlinks = {}
        self.writes = []

    def read_bytes(self, path):
        if path not in self.files:
            raise FileNotFoundError(str(path))
        return self.files[path]

    def read_text(self, path, encoding=None, **kwargs):
        return self.read_bytes(path).decode(encoding or "utf-8")

    def write_bytes(self, path, data):
        self.writes.append((path, data))
        self.files[path] = data
        return len(data)

    def __enter__(self):
        self.stack = ExitStack()
        methods = {
            "resolve": lambda path, **kwargs: self.symlinks.get(path, path),
            "is_file": lambda path: path in self.files,
            "is_symlink": lambda path: path in self.symlinks,
            "read_bytes": self.read_bytes,
            "read_text": self.read_text,
            "write_bytes": self.write_bytes,
            "write_text": AssertionError("unexpected text write"),
            "mkdir": AssertionError("unexpected directory write"),
            "unlink": AssertionError("unexpected deletion"),
            "touch": AssertionError("unexpected file creation"),
        }
        for method, implementation in methods.items():
            self.stack.enter_context(mock.patch.object(
                Path, method, autospec=True, side_effect=implementation))
        return self

    def __exit__(self, *args):
        return self.stack.__exit__(*args)


class ValidationTests(unittest.TestCase):
    def setUp(self):
        self.doc = fixture()

    def reject(self, doc, message):
        with self.assertRaisesRegex(tracker.TrackerError, message):
            tracker.validate(doc)

    def test_complete_fixture_and_no_mutation(self):
        before = copy.deepcopy(self.doc)
        self.assertIsNone(tracker.validate(self.doc))
        with MemoryRepo(self.doc) as repo:
            self.assertIsNone(tracker.validate(self.doc, root=repo.root))
            self.assertEqual(repo.writes, [])
        self.assertEqual(before, self.doc)

    def test_unknown_area_evidence_dependency_and_priority(self):
        for field, bad, message in (
            ("area", "missing", "unknown area"),
            ("evidence", ["missing"], "unknown evidence reference"),
            ("depends_on", ["missing"], "unknown dependency"),
        ):
            with self.subTest(field=field):
                doc = copy.deepcopy(self.doc)
                doc["items"][0][field] = bad
                self.reject(doc, message)
        self.doc["priority"] = ["missing"]
        self.reject(self.doc, "unknown priority")

    def test_duplicate_item_area_and_priority(self):
        for field, message in (("areas", "duplicate area"), ("items", "duplicate item"),
                               ("priority", "duplicate priority")):
            with self.subTest(field=field):
                doc = copy.deepcopy(self.doc)
                doc[field].append(copy.deepcopy(doc[field][0]))
                self.reject(doc, message)

    def test_self_dependency_and_cycles_including_disconnected_component(self):
        self.doc["items"][0]["depends_on"] = [self.doc["items"][0]["id"]]
        self.reject(self.doc, "self dependency")
        for indexes in ((0, 1), (9, 10, 11)):
            with self.subTest(indexes=indexes):
                doc = fixture()
                for index, next_index in zip(indexes, indexes[1:] + indexes[:1]):
                    doc["items"][index]["depends_on"] = [doc["items"][next_index]["id"]]
                self.reject(doc, "dependency cycle")

    def test_long_valid_dependency_chain_avoids_recursion_limit(self):
        template = self.doc["items"][0]
        self.doc["items"] = [dict(template, id=f"step-{index}",
                                  depends_on=[f"step-{index - 1}"] if index else [])
                             for index in range(1200)]
        self.doc["priority"] = ["step-1199"]
        tracker.validate(self.doc)

    def test_evidence_and_result_required_for_observed_source_and_blocked_states(self):
        for status in ("verified", "baseline", "implemented", "partial", "blocked"):
            for field, bad in (("evidence", []), ("result", ""), ("result", " \n")):
                with self.subTest(status=status, field=field, bad=bad):
                    doc = fixture()
                    doc["items"][0].update(status=status)
                    doc["items"][0][field] = bad
                    self.reject(doc, field)

    def test_planned_and_unmeasured_allow_scope_evidence_and_empty_results(self):
        for status in ("planned", "unmeasured"):
            for evidence in ([], ["scope"]):
                with self.subTest(status=status, evidence=evidence):
                    self.doc["items"][0].update(status=status, evidence=evidence, result="")
                    tracker.validate(self.doc)
                    self.assertIn("No result recorded.", tracker.render(self.doc))

    def test_unsupported_status_and_kind(self):
        for status in ("PASS", "complete", "absent", "VERIFIED", "unknown"):
            with self.subTest(status=status):
                doc = fixture()
                doc["items"][0]["status"] = status
                self.reject(doc, "unsupported status")
        self.doc["areas"][0]["kind"] = "infrastructure"
        self.reject(self.doc, "kind")

    def test_required_is_strictly_boolean(self):
        for value in (0, 1, "true", "false", None, [], {}):
            with self.subTest(value=value):
                doc = fixture()
                doc["items"][0]["required"] = value
                self.reject(doc, "required must be boolean")
        for value in (True, False):
            self.doc["items"][0]["required"] = value
            tracker.validate(self.doc)

    def test_missing_top_level_fields_and_wrong_types(self):
        for field in self.doc:
            with self.subTest(missing=field):
                doc = fixture()
                del doc[field]
                self.reject(doc, field)
        for field in self.doc:
            with self.subTest(null=field):
                doc = fixture()
                doc[field] = None
                self.reject(doc, field)
        for value in (None, [], "tracker", 1, True):
            with self.subTest(root=value):
                self.reject(value, "tracker must be an object")

    def test_missing_nested_fields_and_malformed_objects(self):
        for collection in ("items", "areas", "exclusions"):
            for field in self.doc[collection][0]:
                with self.subTest(collection=collection, missing=field):
                    doc = fixture()
                    del doc[collection][0][field]
                    self.reject(doc, field)
            for value in (None, "row", [], 42):
                with self.subTest(collection=collection, value=value):
                    doc = fixture()
                    doc[collection][0] = value
                    self.reject(doc, "must be an object")

    def test_malformed_string_lists_and_blank_strings(self):
        for field in ("profile", "definition", "scope_notes", "priority"):
            for value in ("a string", [1], [None], [" "], {}):
                with self.subTest(field=field, value=value):
                    doc = fixture()
                    doc[field] = value
                    self.reject(doc, field)
        for collection, fields in (
            ("items", ("id", "area", "title", "status", "next_check")),
            ("areas", ("id", "title", "kind", "owner")),
            ("exclusions", ("name", "route", "reason")),
        ):
            for field in fields:
                for value in (None, " ", 1, [], {}):
                    with self.subTest(collection=collection, field=field, value=value):
                        doc = fixture()
                        doc[collection][0][field] = value
                        self.reject(doc, field)
        for collection, field in (("items", "depends_on"), ("items", "evidence"),
                                  ("areas", "task_refs")):
            for value in (None, "ID", [1], [" "], {}):
                with self.subTest(collection=collection, field=field, value=value):
                    doc = fixture()
                    doc[collection][0][field] = value
                    self.reject(doc, field)

    def test_invalid_version_date_revision_and_milestone(self):
        for field, values in (
            ("schema_version", (True, 1.0, "1", 2)),
            ("as_of", ("2026-9-28", "2026-02-29", "2026-04-31", "0000-01-01",
                       "2026-09-28T00:00:00", "2026-09-28\n")),
            ("source_revision", ("abc1234", "g" * 40, "a" * 39, "a" * 41, "a" * 40 + "\n")),
            ("milestone", ("SC2", "sc1", True, [])),
            ("status", ("PASS", "stable", "")),
        ):
            for value in values:
                with self.subTest(field=field, value=value):
                    doc = fixture()
                    doc[field] = value
                    self.reject(doc, field)
        self.doc["as_of"] = "2024-02-29"
        self.doc["source_revision"] = "A" * 40
        tracker.validate(self.doc)

    def test_stable_is_manual_and_requires_all_required_rows_verified(self):
        self.doc["status"] = "STABLE ON DECLARED PROFILE"
        for status in tracker.STATUSES[1:]:
            with self.subTest(status=status):
                doc = fixture()
                doc["status"] = self.doc["status"]
                for item in doc["items"]:
                    item["status"] = "verified"
                doc["items"][-1]["status"] = status
                self.reject(doc, "every required item verified")
        for item in self.doc["items"]:
            item["status"] = "verified"
        tracker.validate(self.doc)
        self.doc["items"][-1].update(status="planned", required=False)
        tracker.validate(self.doc)
        self.doc["status"] = "NOT YET DEMONSTRATED"
        self.assertIn("Milestone: SC1 — NOT YET DEMONSTRATED", tracker.render(self.doc))
        self.assertEqual(self.doc["status"], "NOT YET DEMONSTRATED")

    def test_stable_rejects_empty_scope_and_vacuous_completion(self):
        for item in self.doc["items"]:
            item["status"] = "verified"
        self.doc["status"] = "STABLE ON DECLARED PROFILE"
        for field in ("profile", "definition", "scope_notes", "areas", "items"):
            with self.subTest(field=field):
                doc = copy.deepcopy(self.doc)
                doc[field] = []
                self.reject(doc, field)
        for item in self.doc["items"]:
            item["required"] = False
        self.reject(self.doc, "at least one required item")

    def test_item_assignment_and_contracts_must_inherit_area(self):
        for field, value in (("owner", "Agent"), ("task_refs", ["M01-A"])):
            with self.subTest(field=field):
                doc = fixture()
                doc["items"][0][field] = value
                self.reject(doc, "inherit from the area")


class FileValidationTests(unittest.TestCase):
    def test_traversal_absolute_url_and_noncanonical_paths(self):
        for path in ("../outside", "docs/../../outside", "/etc/passwd", "C:/secret",
                     "C:secret", "\\\\server\\share", "docs\\..\\outside", "https://site/file",
                     "file:secret", "docs//scope.md", "docs/./scope.md", ".", "docs/",
                     "docs/line\nfile", "docs/zero\x00file", "", None, 4, []):
            with self.subTest(path=path):
                doc = fixture()
                doc["references"]["measurement"] = path
                with self.assertRaisesRegex(tracker.TrackerError, "references.measurement"):
                    tracker.validate(doc)

    def test_bad_reference_keys_and_unreferenced_bad_paths(self):
        for key in ("", " ", 1, None):
            with self.subTest(key=key):
                doc = fixture()
                doc["references"][key] = "docs/scope.md"
                with self.assertRaisesRegex(tracker.TrackerError, "reference key"):
                    tracker.validate(doc)
        doc = fixture()
        doc["references"]["unused"] = "../outside"
        with self.assertRaisesRegex(tracker.TrackerError, "references.unused"):
            tracker.validate(doc)

    def test_missing_file_directory_and_symlink_escape(self):
        for path in ("missing.json", "docs"):
            with self.subTest(path=path), MemoryRepo() as repo:
                repo.doc["references"]["measurement"] = path
                with self.assertRaisesRegex(tracker.TrackerError, "real in-repo file"):
                    tracker.validate(repo.doc, root=repo.root)
        with MemoryRepo() as repo:
            repo.symlinks[repo.root / "evidence/result.json"] = Path("/outside/result.json")
            repo.files[Path("/outside/result.json")] = b"exists but outside"
            with self.assertRaisesRegex(tracker.TrackerError, "real in-repo file"):
                tracker.validate(repo.doc, root=repo.root)

    def test_internal_symlink_is_valid_evidence(self):
        with MemoryRepo() as repo:
            repo.symlinks[repo.root / "evidence/result.json"] = repo.root / "docs/scope.md"
            tracker.validate(repo.doc, root=repo.root)

    def test_task_refs_are_checked_only_with_root(self):
        doc = fixture()
        doc["areas"][0]["task_refs"] = ["UNKNOWN"]
        tracker.validate(doc)
        with MemoryRepo(doc) as repo:
            with self.assertRaisesRegex(tracker.TrackerError, "unknown original task ID"):
                tracker.validate(doc, root=repo.root)

    def test_tasks_file_must_exist_be_valid_and_remain_in_repo(self):
        with MemoryRepo() as repo:
            del repo.files[repo.root / tracker.TASKS_RELATIVE]
            with self.assertRaisesRegex(tracker.TrackerError, "tasks.json"):
                tracker.validate(repo.doc, root=repo.root)
        for tasks in ([], {}, {"tasks": "wrong"}, {"tasks": [None]},
                      {"tasks": [{"id": 3}]}, {"tasks": [{"id": "M00-A"}] * 2}):
            with self.subTest(tasks=tasks), MemoryRepo() as repo:
                repo.files[repo.root / tracker.TASKS_RELATIVE] = json.dumps(tasks).encode()
                with self.assertRaises(tracker.TrackerError):
                    tracker.validate(repo.doc, root=repo.root)
        with MemoryRepo() as repo:
            repo.symlinks[repo.root / tracker.TASKS_RELATIVE] = Path("/outside/tasks.json")
            with self.assertRaisesRegex(tracker.TrackerError, "tasks.json"):
                tracker.validate(repo.doc, root=repo.root)

    def test_load_reports_invalid_json_duplicate_keys_and_utf8(self):
        for content in (b"{", b'{"schema_version":1,"schema_version":2}',
                        b'{"references":{"x":"a","x":"b"}}', b"\xff"):
            with self.subTest(content=content), MemoryRepo() as repo:
                repo.files[repo.root / tracker.INPUT_RELATIVE] = content
                with self.assertRaisesRegex(tracker.TrackerError, "cannot load"):
                    tracker.load_tracker(repo.root / tracker.INPUT_RELATIVE)

    def test_load_default_path(self):
        with mock.patch.object(Path, "read_text", return_value=json.dumps(fixture())) as read:
            self.assertEqual(tracker.load_tracker(), fixture())
            read.assert_called_once_with(encoding="utf-8")

    def test_real_data_if_present(self):
        if not tracker.DEFAULT_INPUT.is_file():
            self.skipTest("stable-core.json has not been supplied by the integration lane")
        doc = tracker.load_tracker()
        tracker.validate(doc, root=tracker.REPO_ROOT)
        self.assertEqual(tracker.render(doc), tracker.render(copy.deepcopy(doc)))


class RenderingTests(unittest.TestCase):
    def test_all_statuses_count_separately_by_kind_area_and_total(self):
        doc = fixture()
        before = copy.deepcopy(doc)
        summary = tracker.summarize(doc)
        self.assertEqual(summary["total"], dict.fromkeys(tracker.STATUSES, 2))
        for kind in ("core", "enabler"):
            self.assertEqual(summary["by_kind"][kind], dict.fromkeys(tracker.STATUSES, 1))
            self.assertEqual(summary["by_area"][kind], dict.fromkeys(tracker.STATUSES, 1))
        self.assertEqual(before, doc)
        self.assertNotIn("percent", json.dumps(summary))
        self.assertNotIn("weight", json.dumps(summary))

    def test_historical_baseline_never_becomes_verified_count(self):
        doc = fixture()
        for item in doc["items"]:
            item["status"] = "baseline"
        summary = tracker.summarize(doc)
        self.assertEqual(summary["total"]["baseline"], 14)
        self.assertEqual(summary["total"]["verified"], 0)
        self.assertIn("| core | 7 | 0 | 7 | 0 | 0 | 0 | 0 | 0 |", tracker.render(doc))

    def test_render_is_deterministic_even_when_object_keys_reordered(self):
        doc = fixture()
        rendered = tracker.render(doc)
        reordered = json.loads(json.dumps(doc, sort_keys=True))
        self.assertEqual(rendered, tracker.render(reordered))
        self.assertTrue(rendered.endswith("\n"))
        self.assertNotIn("\r", rendered)
        self.assertNotIn("%", rendered)

    def test_report_contains_provenance_counts_contracts_exclusions_and_instructions(self):
        doc = fixture()
        rendered = tracker.render(doc)
        for text in (
            doc["as_of"], doc["source_revision"], "Manual snapshot, not live telemetry",
            "Campaign state is not inferred from this snapshot", "does not start/resume or change it",
            "Owner labels are responsibility roles, not live runtime status", "Practical progress counts",
            "historical baselines", "Status legend", "Declared profile", "Finish definition",
            "Scope notes", "Priority queue", "Blockers / unmet dependencies",
            "Original contracts", "Core role", "Observer role", "Explicit exclusions",
            "MPI", "M07", "Separate profile.", "Edit only", "original gates",
            "python3 -B scripts/stable_core_tracker.py --check", "--stdout",
            "[measurement](evidence/result.json)", "[scope](docs/scope.md)",
            "[M01-A](docs/verification/os-milestones-20260914/tasks.json)",
        ):
            with self.subTest(text=text):
                self.assertIn(text, rendered)
        for item in doc["items"]:
            self.assertIn(item["title"], rendered)
            self.assertIn(item["result"], rendered)
            self.assertIn(item["next_check"], rendered)
        self.assertIn("core-baseline (baseline): Exact scoped core baseline result", rendered)

    def test_campaign_and_agent_state_come_only_from_snapshot_data(self):
        doc = fixture()
        rendered = tracker.render(doc)
        self.assertNotIn("STOPPED", rendered)
        self.assertNotIn("unassigned", rendered)
        doc["scope_notes"].append("The campaign remains stopped for this snapshot.")
        doc["areas"][0]["owner"] = "Core role; unassigned"
        rendered = tracker.render(doc)
        self.assertIn("The campaign remains stopped for this snapshot.", rendered)
        self.assertIn("Owner role: Core role; unassigned.", rendered)

    def test_optional_rows_and_empty_sections_are_explicit(self):
        doc = fixture()
        doc["items"][0]["required"] = False
        doc["priority"] = []
        doc["exclusions"] = []
        rendered = tracker.render(doc)
        self.assertIn("core-verified (optional)", rendered)
        self.assertIn("No priority substeps declared.", rendered)
        self.assertIn("No exclusions declared.", rendered)
        self.assertEqual(sum(tracker.summarize(doc)["total"].values()), 14)

    def test_markdown_cells_and_link_destinations_are_escaped(self):
        doc = fixture()
        doc["items"][0]["result"] = "a|b\n<script>alert('x')</script> [link] *done*"
        doc["references"]["measurement"] = "evidence/a b(#).json"
        rendered = tracker.render(doc)
        self.assertIn("a\\|b<br>&lt;script&gt;", rendered)
        self.assertNotIn("<script>", rendered)
        self.assertIn("\\[link\\] \\*done\\*", rendered)
        self.assertIn("(evidence/a%20b%28%23%29.json)", rendered)

    def test_public_reporting_functions_validate_before_rendering(self):
        doc = fixture()
        doc["items"][0]["status"] = "invented"
        for function in (tracker.summarize, tracker.render):
            with self.subTest(function=function.__name__):
                with self.assertRaises(tracker.TrackerError):
                    function(doc)


class CommandTests(unittest.TestCase):
    def run_cli(self, repo, *args):
        stdout, stderr = io.StringIO(), io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            code = tracker.main(["--root", str(repo.root), *args])
        return code, stdout.getvalue(), stderr.getvalue()

    def test_check_current_is_read_only(self):
        with MemoryRepo() as repo:
            repo.files[repo.root / tracker.OUTPUT_RELATIVE] = tracker.render(repo.doc).encode()
            before = dict(repo.files)
            self.assertEqual(self.run_cli(repo, "--check"), (0, "", ""))
            self.assertEqual(repo.files, before)
            self.assertEqual(repo.writes, [])

    def test_check_stale_missing_and_different_newlines_fail_without_writes(self):
        for content in (None, b"stale\n", tracker.render(fixture()).replace("\n", "\r\n").encode()):
            with self.subTest(content=content and content[:20]), MemoryRepo() as repo:
                if content is not None:
                    repo.files[repo.root / tracker.OUTPUT_RELATIVE] = content
                before = dict(repo.files)
                code, stdout, stderr = self.run_cli(repo, "--check")
                self.assertEqual(code, 1)
                self.assertEqual(stdout, "")
                self.assertIn("stale or missing", stderr)
                self.assertEqual(repo.files, before)
                self.assertEqual(repo.writes, [])

    def test_stdout_is_exact_render_and_read_only(self):
        with MemoryRepo() as repo:
            before = dict(repo.files)
            self.assertEqual(self.run_cli(repo, "--stdout"), (0, tracker.render(repo.doc), ""))
            self.assertEqual(repo.files, before)
            self.assertEqual(repo.writes, [])

    def test_default_updates_only_markdown_and_then_check_passes(self):
        with MemoryRepo() as repo:
            before = dict(repo.files)
            self.assertEqual(self.run_cli(repo), (0, "", ""))
            self.assertEqual(repo.writes, [(repo.root / tracker.OUTPUT_RELATIVE,
                                           tracker.render(repo.doc).encode())])
            for path, data in before.items():
                self.assertEqual(repo.files[path], data)
            self.assertEqual(self.run_cli(repo, "--check"), (0, "", ""))
            self.assertEqual(len(repo.writes), 1)

    def test_invalid_input_all_modes_fail_before_writing(self):
        for mode in ((), ("--check",), ("--stdout",)):
            with self.subTest(mode=mode), MemoryRepo() as repo:
                repo.doc["items"][0]["evidence"] = []
                repo.files[repo.root / tracker.INPUT_RELATIVE] = json.dumps(repo.doc).encode()
                before = dict(repo.files)
                code, stdout, stderr = self.run_cli(repo, *mode)
                self.assertEqual(code, 1)
                self.assertEqual(stdout, "")
                self.assertIn("evidence", stderr)
                self.assertEqual(repo.files, before)
                self.assertEqual(repo.writes, [])

    def test_missing_input_and_io_failure_are_clear_errors(self):
        with MemoryRepo() as repo:
            del repo.files[repo.root / tracker.INPUT_RELATIVE]
            code, _, stderr = self.run_cli(repo, "--check")
            self.assertEqual(code, 1)
            self.assertIn("tracker input", stderr)
            self.assertEqual(repo.writes, [])
        with MemoryRepo() as repo:
            with mock.patch.object(Path, "write_bytes", side_effect=PermissionError("read-only")):
                code, _, stderr = self.run_cli(repo)
            self.assertEqual(code, 1)
            self.assertIn("read-only", stderr)

    def test_input_escape_and_output_symlinks_are_rejected(self):
        with MemoryRepo() as repo:
            repo.symlinks[repo.root / tracker.INPUT_RELATIVE] = Path("/outside/tracker.json")
            self.assertEqual(self.run_cli(repo, "--stdout")[0], 1)
            self.assertEqual(repo.writes, [])
        for mode in ((), ("--check",)):
            for destination in (Path("/outside/report.md"), tracker.TASKS_RELATIVE):
                with self.subTest(mode=mode, destination=destination), MemoryRepo() as repo:
                    repo.symlinks[repo.root / tracker.OUTPUT_RELATIVE] = repo.root / destination
                    code, _, stderr = self.run_cli(repo, *mode)
                    self.assertEqual(code, 1)
                    self.assertIn("must not be a symlink", stderr)
                    self.assertEqual(repo.writes, [])

    def test_check_and_stdout_are_mutually_exclusive(self):
        with MemoryRepo() as repo, redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as raised:
                tracker.main(["--root", str(repo.root), "--check", "--stdout"])
            self.assertEqual(raised.exception.code, 2)
            self.assertEqual(repo.writes, [])

    def test_import_does_not_run_main_or_write(self):
        with mock.patch.object(Path, "write_bytes") as write_bytes, \
                mock.patch.object(Path, "write_text") as write_text, \
                mock.patch.object(Path, "read_text") as read_text, \
                redirect_stdout(io.StringIO()) as stdout, redirect_stderr(io.StringIO()) as stderr:
            spec = importlib.util.spec_from_file_location("import_only_tracker", SCRIPT)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            write_bytes.assert_not_called()
            write_text.assert_not_called()
            read_text.assert_not_called()
            self.assertEqual(stdout.getvalue(), "")
            self.assertEqual(stderr.getvalue(), "")


if __name__ == "__main__":
    unittest.main()
