"""Pure Python contracts for the existing M14 focused runner.

These tests substitute tiny unittest suites and tool metadata. They do not run
the production allowlist, a compiler, a native controller, or a device operation.
"""
from contextlib import redirect_stderr, redirect_stdout
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import run_m14_focused_checks as runner


def fixture_suite(kind):
    class Fixture(unittest.TestCase):
        def test_case(self):
            if kind == "skip":
                self.skipTest("fixture tool unavailable")
            if kind in ("failure", "expected_failure"):
                self.fail("fixture assertion")
            if kind == "error":
                raise RuntimeError("fixture error")

    if kind in ("expected_failure", "unexpected_success"):
        Fixture.test_case = unittest.expectedFailure(Fixture.test_case)
    return unittest.TestSuite() if kind == "empty" else unittest.defaultTestLoader.loadTestsFromTestCase(Fixture)


class M14FocusedRunnerTests(unittest.TestCase):
    def invoke(self, arguments=(), *, kind="pass", fingerprint_errors=None, load_error=None):
        suite = fixture_suite(kind)
        stdout, stderr = io.StringIO(), io.StringIO()
        with tempfile.TemporaryDirectory(prefix="m14-runner-test-") as temporary:
            report = Path(temporary) / "results.json"
            with patch.object(runner.unittest.defaultTestLoader, "loadTestsFromNames",
                              return_value=suite, side_effect=load_error) as loader, \
                    patch.object(runner, "source_fingerprints",
                                 return_value=({"fixture.c": "abc"}, fingerprint_errors or {})), \
                    patch.object(runner, "output", return_value="fixture-head"), \
                    patch.object(runner, "version", return_value="fixture-tool"), \
                    patch.object(runner.subprocess, "run", side_effect=AssertionError("tool invoked")), \
                    patch.object(runner.sys, "path", list(runner.sys.path)), \
                    redirect_stdout(stdout), redirect_stderr(stderr):
                status = runner.main([*arguments, "--json-output", str(report)])
            record = json.loads(report.read_text()) if report.exists() else None
        return status, record, stdout.getvalue(), stderr.getvalue(), loader

    def assert_no_acceptance(self, record):
        self.assertEqual(record["scope"], "M14_FOCUSED_HOST_SOURCE_ABI_BUILD_ONLY")
        self.assertEqual(record["acceptance"], {
            "establishes_file_closure": False,
            "establishes_c_retirement": False,
            "establishes_native_qualification": False,
        })

    def test_list_performs_no_test_import_fingerprint_or_tool_probe(self):
        stdout = io.StringIO()
        with patch.object(runner.unittest.defaultTestLoader, "loadTestsFromNames",
                          side_effect=AssertionError("test import")), \
                patch.object(runner, "source_fingerprints", side_effect=AssertionError("fingerprint")), \
                patch.object(runner.subprocess, "run", side_effect=AssertionError("tool probe")), \
                redirect_stdout(stdout):
            self.assertEqual(runner.main(["--list"]), 0)
        self.assertEqual(stdout.getvalue().splitlines(), list(runner.MODULES))
        self.assertEqual(len(runner.MODULES), 19)

    def test_unknown_module_fails_before_loading_tests_or_probing_tools(self):
        with patch.object(runner.unittest.defaultTestLoader, "loadTestsFromNames") as loader, \
                patch.object(runner.subprocess, "run") as subprocess_run, \
                redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as raised:
            runner.main(["--module", "scripts.tests.not_allowlisted"])
        self.assertEqual(raised.exception.code, 2)
        loader.assert_not_called()
        subprocess_run.assert_not_called()

    def test_subset_deduplicates_in_allowlist_order_and_labels_result(self):
        first, second = runner.MODULES[1], runner.MODULES[3]
        status, record, stdout, _, loader = self.invoke([
            "--module", second, "--module", first, "--module", second,
        ])
        self.assertEqual(status, 0)
        loader.assert_called_once_with((first, second))
        self.assertEqual(record["modules"], [first, second])
        self.assertEqual(record["requested_modules"], [first, second])
        self.assertEqual(record["unselected_modules"],
                         [name for name in runner.MODULES if name not in (first, second)])
        self.assertEqual(record["selection_mode"], "subset")
        self.assertIs(record["full_allowlist_selected"], False)
        self.assertIs(record["passed_without_skips"], True)
        self.assertIn("M14 focused subset:", stdout)
        self.assert_no_acceptance(record)

    def test_default_preserves_complete_allowlist(self):
        status, record, stdout, _, loader = self.invoke()
        self.assertEqual(status, 0)
        loader.assert_called_once_with(runner.MODULES)
        self.assertEqual(record["modules"], list(runner.MODULES))
        self.assertIsNone(record["requested_modules"])
        self.assertEqual(record["unselected_modules"], [])
        self.assertEqual(record["selection_mode"], "full")
        self.assertIs(record["full_allowlist_selected"], True)
        self.assertIn("M14 focused full allowlist:", stdout)
        self.assert_no_acceptance(record)

    def test_explicit_all_modules_still_reports_full_selection(self):
        arguments = [part for name in reversed(runner.MODULES) for part in ("--module", name)]
        status, record, _, _, loader = self.invoke(arguments)
        self.assertEqual(status, 0)
        loader.assert_called_once_with(runner.MODULES)
        self.assertEqual(record["selection_mode"], "full")
        self.assertEqual(record["requested_modules"], list(runner.MODULES))

    def test_nonpassing_and_empty_suites_never_produce_passing_record(self):
        cases = {
            "skip": "skipped", "failure": "failures", "error": "errors",
            "expected_failure": "expected_failures", "unexpected_success": "unexpected_successes",
            "empty": None,
        }
        for kind, key in cases.items():
            with self.subTest(kind=kind):
                status, record, stdout, _, _ = self.invoke(
                    ["--module", runner.MODULES[0]], kind=kind)
                self.assertEqual(status, 1)
                self.assertIs(record["passed_without_skips"], False)
                self.assertEqual(record["checks_run"], 0 if kind == "empty" else 1)
                if key is not None:
                    self.assertEqual(len(record[key]), 1)
                self.assertIn("focused result FAIL", stdout)
                self.assert_no_acceptance(record)

    def test_loader_exception_is_reported_as_failure(self):
        status, record, _, stderr, _ = self.invoke(load_error=RuntimeError("broken import"))
        self.assertEqual(status, 1)
        self.assertEqual(record["checks_run"], 0)
        self.assertEqual(record["runner_errors"], ["RuntimeError: broken import"])
        self.assertIs(record["passed_without_skips"], False)
        self.assertIn("broken import", stderr)
        self.assert_no_acceptance(record)

    def test_fingerprint_error_keeps_test_success_from_becoming_passing_record(self):
        errors = {"absent.h": "FileNotFoundError: fixture input absent"}
        status, record, _, stderr, _ = self.invoke(fingerprint_errors=errors)
        self.assertEqual(status, 1)
        self.assertEqual(record["checks_run"], 1)
        self.assertEqual(record["source_fingerprint_errors"], errors)
        self.assertEqual(record["source_files_sha256"], {"fixture.c": "abc"})
        self.assertIs(record["passed_without_skips"], False)
        self.assertIn("fingerprint errors: 1", stderr)
        self.assert_no_acceptance(record)

    def test_fingerprinting_retains_successes_and_reports_missing_input(self):
        with tempfile.TemporaryDirectory(prefix="m14-fingerprint-test-") as temporary:
            root = Path(temporary)
            (root / "present.c").write_bytes(b"actual fixture source\n")
            with patch.object(runner, "ROOT", root):
                hashes, errors = runner.source_fingerprints(("present.c", "absent.h"))
        self.assertEqual(hashes, {"present.c": hashlib.sha256(b"actual fixture source\n").hexdigest()})
        self.assertEqual(set(errors), {"absent.h"})
        self.assertIn("FileNotFoundError", errors["absent.h"])

    def test_result_write_failure_returns_nonzero(self):
        stdout, stderr = io.StringIO(), io.StringIO()
        with tempfile.TemporaryDirectory(prefix="m14-report-test-") as temporary:
            with patch.object(runner.unittest.defaultTestLoader, "loadTestsFromNames",
                              return_value=fixture_suite("pass")), \
                    patch.object(runner, "source_fingerprints", return_value=({}, {})), \
                    patch.object(runner, "output", return_value="fixture-head"), \
                    patch.object(runner, "version", return_value="fixture-tool"), \
                    patch.object(runner.sys, "path", list(runner.sys.path)), \
                    redirect_stdout(stdout), redirect_stderr(stderr):
                status = runner.main(["--json-output", temporary])
        self.assertEqual(status, 1)
        self.assertIn("result record could not be written", stderr.getvalue())
        self.assertIn("focused result FAIL", stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
