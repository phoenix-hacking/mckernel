import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import signal
import sys
import tempfile
import unittest
from unittest import mock


SOURCE = Path(__file__).resolve().parents[1] / "application-tests" / "linux_diagnostic.py"
spec = importlib.util.spec_from_file_location("linux_diagnostic", SOURCE)
diagnostic = importlib.util.module_from_spec(spec)
spec.loader.exec_module(diagnostic)


class LinuxDiagnosticTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="linux-diagnostic-test-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.fixture = self.root / "fixture.py"
        self.fixture.write_text("import os,sys; assert sys.argv[1:] == ['']; os.write(2,b'ERR\\n')\n")
        self.oracle = self.root / "oracle.json"
        self.expected = {"schema_version": 1, "kind": "linux-diagnostic-oracle", "case_id": "test.empty",
                         "wait_status": {"kind": "exited", "code": 0}, "stdout_hex": "", "stderr_hex": "4552520a"}
        self.payload = Path(sys.executable).resolve()
        self.counter = 0

    def ref(self, path):
        data = path.read_bytes()
        return {"path": str(path), "size": len(data), "sha256": hashlib.sha256(data).hexdigest()}

    def request(self, **changes):
        self.counter += 1
        self.oracle.write_text(json.dumps(self.expected) + "\n")
        value = {"schema_version": 1, "kind": "linux-diagnostic-request", "case_id": "test.empty",
                 "source": self.ref(self.fixture), "oracle": self.ref(self.oracle), "payload": self.ref(self.payload),
                 "argv": [str(self.payload), "-B", str(self.fixture), ""], "executable_path": str(self.payload),
                 "cwd": str(self.root), "env": {"LC_ALL": "C"}, "stdin": None,
                 "timeout_seconds": 2, "cleanup_timeout_seconds": 1, "stdout_limit_bytes": 4096,
                 "stderr_limit_bytes": 4096, "application_acceptance": False,
                 "mckernel_application_executed": False, "attempt": str(self.root / ("attempt-" + str(self.counter)))}
        value.update(changes)
        return value

    def write(self, value):
        path = self.root / ("request-" + str(self.counter) + ".json")
        path.write_text(json.dumps(value) + "\n")
        return path

    def run_request(self, value=None):
        path = self.write(self.request() if value is None else value)
        return diagnostic.evaluate(diagnostic.load_request(str(path)), str(path))

    def assert_failed(self, result):
        self.assertEqual("FAIL", result["status"], result)
        self.assertIs(result["application_acceptance"], False)
        self.assertIs(result["mckernel_application_executed"], False)

    def test_real_literal_empty_argument_and_bound_result(self):
        result = self.run_request()
        self.assertEqual("PASS", result["status"], result)
        self.assertEqual(0, result["observed"]["raw_wait_status"])
        self.assertEqual(self.ref(self.fixture), result["source"])
        self.assertEqual(self.ref(Path(result["request"]["path"])), result["request"])
        self.assertIs(result["application_acceptance"], False)
        self.assertIs(result["mckernel_application_executed"], False)

    def test_actual_nonzero_exit_matches_oracle_and_mismatch_fails(self):
        self.fixture.write_text("import sys; sys.exit(7)\n")
        self.expected.update(wait_status={"kind": "exited", "code": 7}, stderr_hex="")
        result = self.run_request()
        self.assertEqual("PASS", result["status"], result)
        self.assertEqual(7 << 8, result["observed"]["raw_wait_status"])
        self.expected["wait_status"]["code"] = 0
        self.assert_failed(self.run_request())

    def test_actual_signal_matches_oracle(self):
        self.fixture.write_text("import os,signal; os.kill(os.getpid(),signal.SIGTERM)\n")
        self.expected.update(wait_status={"kind": "signaled", "signal": signal.SIGTERM}, stderr_hex="")
        result = self.run_request()
        self.assertEqual("PASS", result["status"], result)
        self.assertEqual(signal.SIGTERM, os.WTERMSIG(result["observed"]["raw_wait_status"]))

    def test_actual_timeout_and_truncation_fail(self):
        self.expected["stderr_hex"] = ""
        self.fixture.write_text("import time; time.sleep(10)\n")
        result = self.run_request(self.request(timeout_seconds=0.1))
        self.assert_failed(result)
        self.assertEqual("TIMED_OUT", result["observed"]["status"])
        self.fixture.write_text("import os; os.write(1,b'x'*10000)\n")
        result = self.run_request(self.request(stdout_limit_bytes=8))
        self.assert_failed(result)
        self.assertEqual("OUTPUT_LIMIT", result["observed"]["status"])
        self.assertIs(result["observed"]["streams"]["stdout"]["truncated"], True)

    def test_actual_stdin_file_and_devnull(self):
        self.fixture.write_text("import os,sys; os.write(1,sys.stdin.buffer.read())\n")
        self.expected["stderr_hex"] = ""
        self.assertEqual("PASS", self.run_request()["status"])
        stdin = self.root / "input.bin"
        stdin.write_bytes(b"input\x00\xff")
        self.expected["stdout_hex"] = stdin.read_bytes().hex().upper()
        result = self.run_request(self.request(stdin=self.ref(stdin)))
        self.assertEqual("PASS", result["status"], result)
        self.assertEqual("file", result["observed"]["stdin"]["kind"])

    def mutated_report(self, mutate, request=None):
        real = diagnostic.supervisor.run_supervised
        def run(*args, **kwargs):
            observed = real(*args, **kwargs)
            mutate(observed)
            return observed
        with mock.patch.object(diagnostic.supervisor, "run_supervised", side_effect=run):
            return self.run_request(request)

    def test_raw_and_decoded_wait_types_range_terminal_and_contradiction(self):
        for raw in (False, -1, 65536, 0.0, "0", None, 0x7f, 0xffff, 256):
            with self.subTest(raw=raw):
                self.assert_failed(self.mutated_report(lambda report: report.update(raw_wait_status=raw)))
        for wait in ({"kind": "exited", "code": False}, {"kind": "exited", "code": 0.0},
                     {"kind": "exited", "code": 0, "extra": 1}, {"kind": "signaled", "signal": 0}):
            with self.subTest(wait=wait):
                self.assert_failed(self.mutated_report(lambda report: report.update(wait_status=wait)))

    def test_missing_and_wrong_stdin_reports_fail(self):
        for stdin in (None, {}, {"kind": "file"}, {"kind": "devnull", "path": "/dev/null"}):
            with self.subTest(stdin=stdin):
                self.assert_failed(self.mutated_report(lambda report: report.update(stdin=stdin)))
        file = self.root / "stdin.bin"
        other = self.root / "other.bin"
        file.write_bytes(b"same"); other.write_bytes(b"same")
        self.assert_failed(self.mutated_report(lambda report: report["stdin"].update(path=str(other)), self.request(stdin=self.ref(file))))

    def test_report_executable_and_schema_types(self):
        self.assert_failed(self.mutated_report(lambda report: report.update(schema_version=True)))
        self.assert_failed(self.mutated_report(lambda report: report["executable"].update(size=True)))
        self.assert_failed(self.mutated_report(lambda report: report["executable"].update(path=str(self.fixture))))

    def test_wrong_stream_artifact_is_never_compared_to_another_file(self):
        other = self.root / "other.bin"; other.write_bytes(b"BAD\n")
        self.assert_failed(self.mutated_report(lambda report: report["streams"]["stderr"].update(artifact=self.ref(other))))
        other.write_bytes(b"ERR\n")
        self.assert_failed(self.mutated_report(lambda report: report["streams"]["stderr"].update(artifact=self.ref(other))))
        self.assert_failed(self.mutated_report(lambda report: report["streams"]["stderr"]["artifact"].update(sha256="0"*64)))

    def test_strict_stream_accounting_and_requested_limit(self):
        for key in ("bytes_observed", "bytes_retained", "discarded_observed_bytes", "limit_bytes"):
            for value in (-1, False, 0.0, "0", None, 4097):
                with self.subTest(key=key, value=value):
                    self.assert_failed(self.mutated_report(lambda report: report["streams"]["stdout"].update({key: value})))
        for changes in ({"bytes_observed": 3, "bytes_retained": 3}, {"discarded_observed_bytes": 1}, {"limit_bytes": 4095}):
            self.assert_failed(self.mutated_report(lambda report: report["streams"]["stderr"].update(changes)))

    def test_request_changed_before_and_after_launch(self):
        value = self.request(); path = self.write(value); loaded = diagnostic.load_request(str(path))
        original = loaded.request.reference()
        path.write_text("{}")
        with mock.patch.object(diagnostic.supervisor, "run_supervised") as run:
            result = diagnostic.evaluate(loaded, str(path))
        run.assert_not_called(); self.assert_failed(result)
        self.assertEqual(original, result["request"])
        value = self.request(); path = self.write(value); loaded = diagnostic.load_request(str(path))
        real = diagnostic.supervisor.run_supervised
        def change(*args, **kwargs):
            report = real(*args, **kwargs); path.write_text("{}"); return report
        with mock.patch.object(diagnostic.supervisor, "run_supervised", side_effect=change):
            self.assert_failed(diagnostic.evaluate(loaded, str(path)))

    def test_same_bytes_replaced_request_identity_rejected(self):
        value = self.request(); path = self.write(value); loaded = diagnostic.load_request(str(path))
        replacement = self.root / "replacement.json"; replacement.write_bytes(path.read_bytes()); replacement.replace(path)
        with mock.patch.object(diagnostic.supervisor, "run_supervised") as run:
            self.assert_failed(diagnostic.evaluate(loaded, str(path)))
        run.assert_not_called()

    def test_changed_source_or_oracle_or_stdin_rejected_before_launch(self):
        stdin = self.root / "stdin.bin"; stdin.write_bytes(b"input")
        for field in ("source", "oracle", "stdin"):
            with self.subTest(field=field):
                value = self.request(stdin=self.ref(stdin)); path = self.write(value); loaded = diagnostic.load_request(str(path))
                target = Path(value[field]["path"]); original = target.read_bytes(); target.write_bytes(original + b" ")
                with mock.patch.object(diagnostic.supervisor, "run_supervised") as run:
                    self.assert_failed(diagnostic.evaluate(loaded, str(path)))
                run.assert_not_called(); target.write_bytes(original)

    def test_setup_then_publication_failure_preserves_original_first(self):
        value = self.request()
        with mock.patch.object(diagnostic.supervisor, "run_supervised", side_effect=RuntimeError("original setup failure")), \
                mock.patch.object(diagnostic, "_publish", side_effect=OSError("later publication failure")):
            result = self.run_request(value)
        self.assert_failed(result)
        self.assertIn("original setup failure", result["reasons"][0])
        events = [json.loads(line) for line in Path(result["failure_journal"]).read_text().splitlines()]
        self.assertEqual("collection_failure", events[1]["event"])
        self.assertIn("original setup failure", events[1]["error"])
        self.assertEqual("publication_failure", events[-1]["event"])

    def test_preexisting_sidecar_and_evaluation_never_overwritten(self):
        value = self.request(); sidecar = Path(value["attempt"] + ".diagnostic-failure.jsonl")
        sidecar.write_text("original")
        with mock.patch.object(diagnostic.supervisor, "run_supervised") as run:
            with self.assertRaises(FileExistsError): self.run_request(value)
        run.assert_not_called(); self.assertEqual("original", sidecar.read_text())
        def insert(report):
            path = Path(report["streams"]["stdout"]["artifact"]["path"]).parent / "diagnostic-evaluation.json"
            path.write_text("original")
        result = self.mutated_report(insert)
        self.assert_failed(result)
        self.assertEqual("original", (Path(result["observed"]["streams"]["stdout"]["artifact"]["path"]).parent / "diagnostic-evaluation.json").read_text())

    def test_paths_and_preexisting_attempts(self):
        link = self.root / "linked"; link.symlink_to(self.root, target_is_directory=True)
        for path in (str(self.root) + "//attempt", str(self.root) + "/./attempt", str(self.root) + "/x/../attempt",
                     str(self.root) + "/attempt/", str(link / "attempt"), "relative", 42):
            with self.subTest(path=path):
                with self.assertRaises((ValueError, OSError)): diagnostic.load_request(str(self.write(self.request(attempt=path))))
        value = self.request(); Path(value["attempt"]).symlink_to(self.root / "missing")
        with self.assertRaises(ValueError): diagnostic.load_request(str(self.write(value)))
        value = self.request(); Path(value["attempt"]).mkdir()
        with self.assertRaises(ValueError): diagnostic.load_request(str(self.write(value)))
        value = self.request(); real = self.write(value); request_link = self.root / "request-link"; request_link.symlink_to(real)
        with self.assertRaises(ValueError): diagnostic.load_request(str(request_link))

    def test_stale_refs_and_payload_mismatch(self):
        for field in ("source", "oracle", "payload"):
            value = self.request(); value[field]["sha256"] = "0" * 64
            with self.assertRaises(ValueError): diagnostic.load_request(str(self.write(value)))
        value = self.request(); value["payload"] = self.ref(self.fixture)
        with self.assertRaises(ValueError): diagnostic.load_request(str(self.write(value)))

    def test_strict_schema_types_and_bounds(self):
        invalid = {"schema_version": (True, 1.0), "timeout_seconds": (False, 0, -1, 1e100, float("nan")),
                   "cleanup_timeout_seconds": (True, 3601), "stdout_limit_bytes": (False, -1, 2**63),
                   "stderr_limit_bytes": (1.0, 2**63), "application_acceptance": (0, True)}
        for field, values in invalid.items():
            for value in values:
                with self.subTest(field=field, value=value):
                    with self.assertRaises(ValueError): diagnostic.load_request(str(self.write(self.request(**{field: value}))))
        for changes in ({"schema_version": True}, {"wait_status": {"kind": "exited", "code": False}},
                        {"wait_status": {"kind": "signaled", "signal": True}}, {"stdout_hex": "0"}):
            original = copy.deepcopy(self.expected); self.expected.update(changes)
            with self.assertRaises(ValueError): diagnostic.load_request(str(self.write(self.request())))
            self.expected = original
        with self.assertRaises(ValueError): diagnostic.load_request(str(self.write(self.request(stderr_limit_bytes=3))))


if __name__ == "__main__":
    unittest.main()
