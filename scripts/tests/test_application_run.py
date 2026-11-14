#!/usr/bin/env python3
"""Synthetic metadata-only runner boundaries; every attempt remains retained."""

import contextlib
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest import mock


TESTS = Path(__file__).resolve().parent


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


runner = module("application_run_preflight", TESTS.parent / "application-tests/run.py")
fixture_module = module("preflight_metadata_fixture", TESTS / "test_application_runtime_contracts.py")


class PreflightTests(unittest.TestCase):
    def setUp(self):
        self.directory = Path(tempfile.mkdtemp(prefix="application-preflight-test-"))
        print("RETAINED_APPLICATION_PREFLIGHT", self.id(), self.directory, flush=True)
        self.inputs = self.directory / "original-inputs"
        self.inputs.mkdir()
        self.fixture = fixture_module.MetadataFixture(self.inputs)
        self.serial = 0
        sources = self.directory / "test-sources"
        sources.mkdir()
        for path in (Path(__file__), Path(runner.__file__), Path(runner.contracts.__file__),
                     Path(fixture_module.__file__)):
            shutil.copyfile(path, sources / path.name)
        # Metadata authorization fields can never cause an OS process launch.
        for name in ("Popen", "run"):
            patch = mock.patch.object(subprocess, name, side_effect=AssertionError("forbidden process launch"))
            patch.start()
            self.addCleanup(patch.stop)
        patch = mock.patch.object(os, "execve", side_effect=AssertionError("forbidden execve"))
        patch.start()
        self.addCleanup(patch.stop)

    def run_preflight(self, bundle=None, **overrides):
        self.serial += 1
        kwargs = dict(case_id="startup.argv-empty", attempt_dir=str(self.directory / ("attempt-%02d" % self.serial)),
                      profile="baseline-root-1cpu", mode="differential-guest")
        kwargs.update(overrides)
        result = runner.preflight(str(bundle or self.fixture.build()), **kwargs)
        self.assertEqual("NOT_RUN", result["execution_status"])
        self.assertIs(result["application_acceptance"], False)
        self.assertIs(result["transport_acceptance"], False)
        self.assertIs(result["production_gate_credit"], False)
        self.assertIs(result["backend_implemented"], False)
        self.assertEqual(result, json.loads((Path(kwargs["attempt_dir"]) / "report.json").read_bytes()))
        return result

    def test_eligible_metadata_still_blocks_and_retains_exact_original_graph(self):
        bundle = self.fixture.build()
        original = bundle.read_bytes()
        result = self.run_preflight(bundle)
        self.assertEqual("PASS", result["metadata"]["status"])
        self.assertEqual("BLOCKED", result["status"])
        self.assertTrue(any("backend" in reason for reason in result["reasons"]))
        self.assertIs(result["schema_reference_capture_complete"], True)
        index = json.loads(Path(result["retention_index"]["path"]).read_bytes())
        originals = {row["original"]["path"] for row in index["entries"]}
        self.assertIn(str(bundle), originals)
        self.assertIn(self.fixture.proof["path"], originals)
        self.assertIn(self.fixture.inputs["payloads"]["startup.argv-empty"]["executable"]["path"], originals)
        for row in index["entries"]:
            data = Path(row["retained"]["path"]).read_bytes()
            self.assertEqual(Path(row["original"]["path"]).read_bytes(), data)
            self.assertEqual(row["original"]["sha256"], hashlib.sha256(data).hexdigest())
        self.assertEqual(original, bundle.read_bytes())

    def test_missing_blocked_unsupported_and_disabled_capabilities_never_release(self):
        for state in ("blocked", "unsupported"):
            with self.subTest(state=state):
                self.fixture.cap_states["runtime-transport-fault-injection"] = state
                result = self.run_preflight()
                self.assertEqual("BLOCKED", result["metadata"]["status"])
                self.assertTrue(any("runtime-transport-fault-injection" in text for text in result["reasons"]))
        self.fixture.cap_states.clear()
        self.fixture.required.remove("runtime-transport-fault-injection")
        self.assertEqual("BLOCKED", self.run_preflight()["metadata"]["status"])
        self.fixture.required.add("runtime-transport-fault-injection")
        self.fixture.packet_overrides["execution_enabled"] = False
        self.assertTrue(any("disabled" in text for text in self.run_preflight()["reasons"]))

    def test_unselected_case_and_unsupported_oracle_stay_blocked(self):
        self.assertEqual("BLOCKED", self.run_preflight(case_id="memory.calloc-zero")["metadata"]["status"])
        self.fixture.oracles["startup.argv-empty"]["predicates"] = [{"kind": "future-resource-invariant"}]
        self.assertTrue(any("not implemented" in text for text in self.run_preflight()["reasons"]))

    def test_malformed_bundle_bytes_are_retained_before_json_rejection(self):
        for i, raw in enumerate((b'{"a":1,"a":2}', b'{"x":NaN}', b'{"x":1e999}', b'[]')):
            with self.subTest(raw=raw):
                path = self.inputs / ("bad-%d.json" % i)
                path.write_bytes(raw)
                result = self.run_preflight(path)
                self.assertEqual("FAIL", result["status"])
                index = json.loads(Path(result["retention_index"]["path"]).read_bytes())
                entry = next(row for row in index["entries"] if row["original_path"] == str(path))
                self.assertEqual(raw, Path(entry["retained"]["path"]).read_bytes())
                self.assertIs(result["schema_reference_capture_complete"], False)

    def test_existing_or_symlinked_attempt_never_overwrites(self):
        existing = self.directory / "existing"
        existing.mkdir()
        marker = existing / "marker"
        marker.write_bytes(b"original attempt must remain unchanged\n")
        with self.assertRaises(FileExistsError):
            self.run_preflight(attempt_dir=str(existing))
        self.assertEqual([marker], list(existing.iterdir()))
        link = self.directory / "linked-parent"
        link.symlink_to(existing, target_is_directory=True)
        with self.assertRaises(runner.contracts.ContractError):
            self.run_preflight(attempt_dir=str(link / "new-attempt"))
        self.assertEqual(b"original attempt must remain unchanged\n", marker.read_bytes())

    def test_fifo_symlink_and_nonregular_inputs_fail_without_open_wait(self):
        valid = self.fixture.build()
        link = self.inputs / "bundle-link"
        link.symlink_to(valid)
        fifo = self.inputs / "bundle-fifo"
        os.mkfifo(str(fifo))
        for path in (link, fifo, self.inputs):
            with self.subTest(path=path):
                result = self.run_preflight(path)
                self.assertEqual("FAIL", result["status"])

    def test_stale_payload_and_changed_after_loader_fail_closed(self):
        bundle = self.fixture.build()
        payload = Path(self.fixture.inputs["payloads"]["startup.argv-empty"]["executable"]["path"])
        original = payload.read_bytes()
        payload.write_bytes(b"X" + original[1:])
        self.assertEqual("FAIL", self.run_preflight(bundle)["status"])
        payload.write_bytes(original)
        load = runner.contracts.load_runtime_bundle

        def mutate_after_loading(path):
            loaded = load(path)
            payload.write_bytes(b"Y" + original[1:])
            return loaded

        with mock.patch.object(runner.contracts, "load_runtime_bundle", side_effect=mutate_after_loading):
            self.assertEqual("FAIL", self.run_preflight(bundle)["status"])

    def test_source_stale_capability_and_increased_limit_fail(self):
        self.fixture.evidence_overrides["current-inputs"] = {"selected_inputs_sha256": "0" * 64}
        self.assertEqual("FAIL", self.run_preflight()["status"])
        self.fixture.evidence_overrides.clear()
        self.fixture.cases[0]["limits"]["payload_timeout_seconds"] += 1
        self.assertEqual("FAIL", self.run_preflight()["status"])

    def test_temporary_original_bundle_swap_cannot_replace_captured_metadata(self):
        self.fixture.cap_states["runtime-transport-fault-injection"] = "blocked"
        original_path = self.fixture.build()
        original_bytes = original_path.read_bytes()
        self.fixture.cap_states.clear()
        alternate_bytes = self.fixture.build().read_bytes()
        self.assertNotEqual(original_bytes, alternate_bytes)
        load = runner.contracts.load_runtime_bundle

        def swap_while_loading(path):
            original_path.write_bytes(alternate_bytes)
            try:
                return load(path)
            finally:
                original_path.write_bytes(original_bytes)

        with mock.patch.object(runner.contracts, "load_runtime_bundle", side_effect=swap_while_loading):
            result = self.run_preflight(original_path)
        self.assertEqual("BLOCKED", result["metadata"]["status"])
        self.assertTrue(any("runtime-transport-fault-injection" in text for text in result["metadata"]["reasons"]))
        self.assertEqual(original_bytes, original_path.read_bytes())

    def test_retention_count_and_aggregate_bounds_fail_explicitly(self):
        for constant, limit, text in (("MAX_REFERENCES", 3, "reference count"),
                                      ("MAX_RETAINED_BYTES", 1, "aggregate input")):
            with self.subTest(constant=constant), mock.patch.object(runner, constant, limit):
                result = self.run_preflight()
                self.assertEqual("FAIL", result["status"])
                self.assertTrue(any(text in reason for reason in result["reasons"]))

    def test_repeated_references_count_toward_work_bound(self):
        self.fixture.inputs["payloads"]["startup.argv-empty"]["dsos"] = [self.fixture.proof] * 257
        result = self.run_preflight()
        self.assertEqual("FAIL", result["status"])
        self.assertTrue(any("reference count" in text for text in result["reasons"]))
        index = json.loads(Path(result["retention_index"]["path"]).read_bytes())
        self.assertLess(len(index["entries"]), 256)
        self.assertEqual(256, index["reference_uses"])

    def test_planned_cli_returns_blocked_and_has_no_execution_switch(self):
        bundle = self.fixture.build()
        args = ["--inputs", str(bundle), "--case", "startup.argv-empty", "--attempt",
                str(self.directory / "cli-attempt"), "--profile", "baseline-root-1cpu",
                "--mode", "differential-guest"]
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = runner.main(args)
        (self.directory / "cli.stdout").write_text(out.getvalue())
        (self.directory / "cli.stderr").write_text(err.getvalue())
        self.assertEqual(2, code)
        self.assertEqual("BLOCKED", json.loads(out.getvalue())["status"])
        with contextlib.redirect_stderr(err), self.assertRaises(SystemExit) as rejected:
            runner.main(args + ["--execute"])
        self.assertEqual(2, rejected.exception.code)
        (self.directory / "cli-invalid.stderr").write_text(err.getvalue())


if __name__ == "__main__":
    unittest.main()
