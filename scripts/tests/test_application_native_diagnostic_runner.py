"""Focused host-only tests for the strict native diagnostic entry point."""

import importlib.util
import json
from pathlib import Path
import signal
import tempfile
import time
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "native_diagnostic_runner", ROOT / "scripts/application-tests/native_diagnostic_runner.py")
RUNNER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RUNNER)
SPEC = importlib.util.spec_from_file_location(
    "runner_diagnostic_fixture", ROOT / "scripts/tests/test_application_native_diagnostic.py")
FIXTURE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(FIXTURE)
ND = FIXTURE.ND


class RunnerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.parent = self.root / "attempts"
        self.parent.mkdir(mode=0o700)
        self.manifest_path = self.root / "manifest.json"
        self.manifest_path.write_text("{}")
        self.manifest = {"case_id": "pilot"}
        self.attempt = self.parent / "fresh"
        self.plan = {"argv": ["/usr/libexec/qemu-kvm", "-qmp", "exact"],
                     "qmp_socket": str(self.attempt / "qmp.sock")}
        self.diagnostic = mock.Mock()
        self.diagnostic.record_failure.side_effect = lambda attempt, exc, phase: ND.record_failure(
            attempt, exc, phase, writer=self.diagnostic.write_record)
        self.backend = mock.Mock()
        self.diagnostic.load_manifest.return_value = self.manifest
        self.diagnostic.prepare_attempt.return_value = self.attempt
        self.diagnostic.build_command.return_value = self.plan
        self.diagnostic.run_diagnostic.return_value = {"status": "PROTOCOL_PASS", "case_id": "pilot"}
        self.process_factory = mock.Mock(name="process_factory", return_value=mock.Mock())
        self.qmp_factory = mock.Mock(name="qmp_factory", return_value=mock.Mock())
        self.backend.process_factory = self.process_factory
        self.backend.qmp_factory = self.qmp_factory

    def tearDown(self):
        self.tmp.cleanup()

    def test_success_binds_one_plan_and_one_private_socket(self):
        result = RUNNER.run(str(self.manifest_path), str(self.parent), "fresh", "12.5",
                            diagnostic=self.diagnostic, backend=self.backend)
        self.assertEqual(result["status"], "PROTOCOL_PASS")
        self.diagnostic.load_manifest.assert_called_once_with(str(self.manifest_path))
        self.diagnostic.prepare_attempt.assert_called_once_with(self.manifest, str(self.parent), "fresh")
        self.diagnostic.build_command.assert_called_once_with(self.manifest, self.attempt)
        self.process_factory.assert_called_once_with(self.plan["argv"], str(self.attempt))
        self.qmp_factory.assert_called_once_with(self.plan["qmp_socket"])
        self.diagnostic.run_diagnostic.assert_called_once_with(
            self.manifest, self.attempt, self.process_factory.return_value,
            self.qmp_factory.return_value, timeout=12.5, expected_plan=self.plan)

    def test_invalid_inputs_are_rejected_before_any_runtime_action(self):
        bad = ((str(self.manifest_path.parent) + "/./" + self.manifest_path.name, str(self.parent), "x", "1"),
               (str(self.manifest_path), str(self.parent), "../x", "1"),
               (str(self.manifest_path), str(self.parent), "x", "nan"),
               (str(self.manifest_path), str(self.parent), "x", "3600.1"))
        for args in bad:
            with self.subTest(args=args), self.assertRaises(ValueError):
                RUNNER.run(*args, diagnostic=self.diagnostic, backend=self.backend)
        self.diagnostic.load_manifest.assert_not_called()
        self.process_factory.assert_not_called()
        self.qmp_factory.assert_not_called()

    def test_existing_attempt_is_rejected_without_factories(self):
        self.attempt.mkdir(mode=0o700)
        self.diagnostic.prepare_attempt.side_effect = ValueError("existing attempt")
        with self.assertRaisesRegex(ValueError, "existing"):
            RUNNER.run(str(self.manifest_path), str(self.parent), "fresh", 1,
                       diagnostic=self.diagnostic, backend=self.backend)
        self.process_factory.assert_not_called()
        self.qmp_factory.assert_not_called()

    def test_plan_failure_publishes_bounded_fail_closed_evidence(self):
        original = RuntimeError("plan rejected")
        self.diagnostic.build_command.side_effect = original
        with self.assertRaises(RuntimeError) as raised:
            RUNNER.run(str(self.manifest_path), str(self.parent), "fresh", 1,
                       diagnostic=self.diagnostic, backend=self.backend)
        self.assertIs(raised.exception, original)
        self.diagnostic.write_record.assert_called_once()
        attempt, record, failure = self.diagnostic.write_record.call_args.args
        self.assertEqual(attempt, self.attempt)
        self.assertEqual(record["status"], "BLOCKED")
        self.assertEqual(failure["phase"], "setup")
        self.process_factory.assert_not_called()
        self.qmp_factory.assert_not_called()

    def test_factory_failure_is_recorded_and_lifecycle_is_not_called(self):
        original = RuntimeError("factory rejected")
        self.process_factory.side_effect = original
        with self.assertRaises(RuntimeError) as raised:
            RUNNER.run(str(self.manifest_path), str(self.parent), "fresh", 1,
                       diagnostic=self.diagnostic, backend=self.backend)
        self.assertIs(raised.exception, original)
        self.diagnostic.write_record.assert_called_once()
        self.diagnostic.run_diagnostic.assert_not_called()

    def test_setup_keyboard_interrupt_is_republished_without_masking_original(self):
        original = KeyboardInterrupt("factory stop")
        self.process_factory.side_effect = original
        self.diagnostic.write_record.side_effect = KeyboardInterrupt("publisher stop")
        with self.assertRaises(KeyboardInterrupt) as raised:
            RUNNER.run(str(self.manifest_path), str(self.parent), "fresh", 1,
                       diagnostic=self.diagnostic, backend=self.backend)
        self.assertIs(raised.exception, original)

    def test_blocking_setup_publisher_is_bounded(self):
        original = RuntimeError("factory stop")
        self.process_factory.side_effect = original
        def block(*args):
            signal.pause()
        self.diagnostic.write_record.side_effect = block
        started = time.monotonic()
        with self.assertRaises(RuntimeError) as raised:
            RUNNER.run(str(self.manifest_path), str(self.parent), "fresh", 1,
                       diagnostic=self.diagnostic, backend=self.backend)
        self.assertIs(raised.exception, original)
        self.assertLess(time.monotonic() - started, 3)

    def test_setup_never_calls_hostile_exception_formatter(self):
        calls = []
        class Hostile(RuntimeError):
            def __str__(self):
                calls.append("str")
                signal.pause()
            def __repr__(self):
                calls.append("repr")
                raise AssertionError("repr called")
        original = Hostile("safe primitive message")
        self.diagnostic.build_command.side_effect = original
        with self.assertRaises(Hostile) as raised:
            RUNNER.run(str(self.manifest_path), str(self.parent), "fresh", 1,
                       diagnostic=self.diagnostic, backend=self.backend)
        self.assertIs(raised.exception, original)
        self.assertEqual(calls, [])
        self.assertEqual(RUNNER._failure_text(original), "safe primitive message")
        self.assertEqual(calls, [])
        self.diagnostic.write_record.assert_called_once()

    def test_setup_ambient_timer_declines_publisher_and_preserves_original(self):
        original = SystemExit(37)
        self.diagnostic.build_command.side_effect = original
        # No timer or handler mutation is allowed, even if an injected writer
        # would otherwise ignore timeout arguments or block indefinitely.
        with mock.patch.object(ND.signal, "getitimer", return_value=(30.0, 0.0)), \
             mock.patch.object(ND.signal, "setitimer") as timer, \
             mock.patch.object(ND.signal, "signal") as handler:
            with self.assertRaises(SystemExit) as raised:
                RUNNER.run(str(self.manifest_path), str(self.parent), "fresh", 1,
                           diagnostic=self.diagnostic, backend=self.backend)
        self.assertIs(raised.exception, original)
        self.diagnostic.write_record.assert_not_called()
        timer.assert_not_called(); handler.assert_not_called()

    def test_setup_and_cli_use_total_metadata_for_hostile_exceptions(self):
        original, hooks = FIXTURE.hostile_exception()
        self.process_factory.side_effect = original
        with self.assertRaises(Exception) as raised:
            RUNNER.run(str(self.manifest_path), str(self.parent), "fresh", 1,
                       diagnostic=self.diagnostic, backend=self.backend)
        self.assertIs(raised.exception, original)
        self.diagnostic.write_record.assert_called_once()
        failure = self.diagnostic.write_record.call_args.args[2]
        self.assertEqual(failure, {"phase": "setup", "type": "BaseException",
                                   "error": "<exception metadata unavailable>"})
        self.assertEqual(RUNNER._failure_text(original), "<exception metadata unavailable>")
        self.assertEqual(hooks, [])
        with mock.patch.object(RUNNER, "_module", side_effect=original):
            self.assertEqual(RUNNER._failure_text(original), "<exception metadata unavailable>")
        self.assertEqual(hooks, [])

    def test_backend_uses_exact_sibling_qmp_capture_against_ambient_poison(self):
        absent = object()
        previous = RUNNER.sys.modules.get("qmp_capture", absent)
        malicious = type("Malicious", (), {})
        fake = mock.Mock(QmpSession=malicious)
        with mock.patch.dict(RUNNER.sys.modules, {"qmp_capture": fake}):
            backend = RUNNER._backend_module()
            self.assertIs(RUNNER.sys.modules["qmp_capture"], fake)
        bound = backend.QmpBackend.__init__.__globals__["QmpSession"]
        self.assertEqual(bound.__module__, "native_diagnostic_runner_qmp_capture")
        self.assertIsNot(bound, malicious)
        self.assertIs(RUNNER.sys.modules.get("qmp_capture", absent), previous)

    def test_backend_restores_initially_absent_qmp_capture(self):
        absent = object()
        previous = RUNNER.sys.modules.get("qmp_capture", absent)
        with mock.patch.dict(RUNNER.sys.modules):
            RUNNER.sys.modules.pop("qmp_capture", None)
            backend = RUNNER._backend_module()
            bound = backend.QmpBackend.__init__.__globals__["QmpSession"]
            self.assertEqual(bound.__module__, "native_diagnostic_runner_qmp_capture")
            self.assertNotIn("qmp_capture", RUNNER.sys.modules)
        self.assertIs(RUNNER.sys.modules.get("qmp_capture", absent), previous)

    def test_backend_restores_exact_preloaded_legitimate_qmp_capture(self):
        absent = object()
        previous = RUNNER.sys.modules.get("qmp_capture", absent)
        legitimate = RUNNER._module("runner_test_preloaded_qmp", RUNNER._HERE / "qmp_capture.py")
        with mock.patch.dict(RUNNER.sys.modules, {"qmp_capture": legitimate}):
            backend = RUNNER._backend_module()
            bound = backend.QmpBackend.__init__.__globals__["QmpSession"]
            self.assertEqual(bound.__module__, "native_diagnostic_runner_qmp_capture")
            self.assertIsNot(bound, legitimate.QmpSession)
            self.assertIs(RUNNER.sys.modules["qmp_capture"], legitimate)
        self.assertIs(RUNNER.sys.modules.get("qmp_capture", absent), previous)

    def test_import_does_not_spawn_or_open_qmp(self):
        with mock.patch("subprocess.Popen", side_effect=AssertionError("spawn")), \
             mock.patch("socket.socket", side_effect=AssertionError("qmp")):
            spec = importlib.util.spec_from_file_location(
                "native_diagnostic_runner_import", ROOT / "scripts/application-tests/native_diagnostic_runner.py")
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)


class RunnerIntegrationTests(unittest.TestCase):
    """Real manifest, plan, revalidation and evidence; no process/QMP runtime."""
    def setUp(self):
        self.fixture = FIXTURE.NativeDiagnosticTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.tearDown)
        self.backend = mock.Mock()
        self.parent = self.fixture.root / "attempts"
        self.parent.mkdir(mode=0o700)
        self.attempt = self.parent / "fresh"

    def run_runner(self):
        return RUNNER.run(str(self.fixture.manifest_path), str(self.parent), "fresh", 1,
                          diagnostic=ND, backend=self.backend)

    def test_real_plan_and_factories_join_before_lifecycle(self):
        with mock.patch.object(ND, "exercise_lifecycle", return_value={"status": "PROTOCOL_PASS"}) as lifecycle:
            result = self.run_runner()
        self.assertEqual(result["status"], "PROTOCOL_PASS")
        argv, cwd = self.backend.process_factory.call_args.args
        self.assertEqual(argv.count("-S"), 1)
        self.assertEqual(cwd, str(self.attempt))
        self.backend.qmp_factory.assert_called_once_with(str(self.attempt / "qmp.sock"))
        lifecycle.assert_called_once()
        self.assertIs(lifecycle.call_args.args[2], self.backend.process_factory.return_value)
        self.assertIs(lifecycle.call_args.args[3], self.backend.qmp_factory.return_value)

    def test_second_build_base_exception_has_one_authoritative_record(self):
        for error in (KeyboardInterrupt("second validation"), SystemExit(37)):
            with self.subTest(error=type(error).__name__):
                # A fresh reserved attempt for each distinct original failure.
                self.parent = self.fixture.root / ("attempts-" + type(error).__name__)
                self.parent.mkdir(mode=0o700)
                self.attempt = self.parent / "fresh"
                real_build = ND.build_command
                calls = []
                def build(manifest, attempt):
                    calls.append(attempt)
                    if len(calls) == 2:
                        raise error
                    return real_build(manifest, attempt)
                with mock.patch.object(ND, "build_command", side_effect=build), \
                     mock.patch.object(ND, "write_record", wraps=ND.write_record) as publish, \
                     mock.patch.object(ND, "exercise_lifecycle") as lifecycle:
                    with self.assertRaises(type(error)) as raised:
                        self.run_runner()
                self.assertIs(raised.exception, error)
                self.assertEqual(len(calls), 2)
                publish.assert_called_once(); lifecycle.assert_not_called()
                record = json.loads((self.attempt / "result.json").read_text())
                self.assertEqual(record["failure"]["phase"], "staging")
                self.assertEqual(record["failure"]["type"], type(error).__name__)
                self.assertEqual(len((self.attempt / "first-failure.jsonl").read_text().splitlines()), 1)

    def test_second_build_writer_base_exception_does_not_trigger_second_publication(self):
        original = KeyboardInterrupt("second validation")
        real_build = ND.build_command
        calls = []
        def build(manifest, attempt):
            calls.append(attempt)
            if len(calls) == 2:
                raise original
            return real_build(manifest, attempt)
        with mock.patch.object(ND, "build_command", side_effect=build), \
             mock.patch.object(ND, "write_record", side_effect=SystemExit("writer")) as publish, \
             mock.patch.object(ND, "exercise_lifecycle") as lifecycle:
            with self.assertRaises(KeyboardInterrupt) as raised:
                self.run_runner()
        self.assertIs(raised.exception, original)
        publish.assert_called_once(); lifecycle.assert_not_called()


if __name__ == "__main__":
    unittest.main()
