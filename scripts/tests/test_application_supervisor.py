#!/usr/bin/env python3
"""Bounded Python process tests, not McKernel application/ISA execution."""

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from unittest import mock


SOURCE = Path(__file__).resolve().parents[1] / "application-tests" / "supervisor.py"
SPEC = importlib.util.spec_from_file_location("application_supervisor", SOURCE)
supervisor = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(supervisor)


@unittest.skipUnless(sys.platform == "linux", "requires Linux subreaper and /proc")
class ApplicationSupervisorTests(unittest.TestCase):
    def setUp(self):
        self.directory = Path(tempfile.mkdtemp(prefix="application-supervisor-test-"))
        self.counter = 0

    def tearDown(self):
        # Keep complete original attempt artifacts on an unexpected test failure.
        result = self._outcome.result
        failed = any(test is self for test, _ in result.failures + result.errors)
        failed = failed or any(error is not None and
                               (test is self or getattr(test, "test_case", None) is self)
                               for test, error in getattr(self._outcome, "errors", ()))
        if failed:
            print("PRESERVED FAILED SUPERVISOR TEST: {}".format(self.directory), file=sys.stderr)
        else:
            shutil.rmtree(self.directory)

    def run_python(self, source, **overrides):
        self.counter += 1
        attempt = self.directory / "attempt-{}".format(self.counter)
        options = dict(cwd=str(self.directory), env={"LC_ALL": "C"},
                       attempt_dir=str(attempt), timeout_seconds=2,
                       cleanup_timeout_seconds=1, stdout_limit_bytes=65536,
                       stderr_limit_bytes=65536)
        options.update(overrides)
        result = supervisor.run_supervised([sys.executable, "-I", "-B", "-c", source], **options)
        self.assertEqual(result, json.loads((attempt / "report.json").read_text()))
        for stream in result.get("streams", {}).values():
            artifact = stream["artifact"]
            data = Path(artifact["path"]).read_bytes()
            self.assertEqual(len(data), artifact["size"])
            self.assertEqual(hashlib.sha256(data).hexdigest(), artifact["sha256"])
            self.assertLessEqual(len(data), stream["limit_bytes"])
        return result, attempt

    def assert_collected(self, result, code=0):
        self.assertEqual("COMPLETED", result["status"])
        self.assertFalse(result["application_acceptance"])
        self.assertTrue(result["cleanup_complete"])
        self.assertEqual({"kind": "exited", "code": code}, result["wait_status"])
        self.assertTrue(os.WIFEXITED(result["raw_wait_status"]))
        self.assertEqual(code, os.WEXITSTATUS(result["raw_wait_status"]))
        self.assertTrue(all(stream["eof"] for stream in result["streams"].values()))

    def test_explicit_environment_cwd_stdin_and_literal_argv(self):
        input_path = self.directory / "input.bin"
        input_path.write_bytes(b"input\x00bytes\xff\n")
        self.counter += 1
        attempt = self.directory / "attempt-{}".format(self.counter)
        literal = "$(touch SHOULD_NOT_EXIST); literal argument"
        source = ("import json,os,sys; "
                  "print(json.dumps({'cwd':os.getcwd(),'env':dict(os.environ),"
                  "'args':sys.argv[1:],'stdin':sys.stdin.buffer.read().hex()},sort_keys=True))")
        result = supervisor.run_supervised(
            [sys.executable, "-I", "-B", "-c", source, literal],
            cwd=str(self.directory), env={"LC_ALL": "C", "TOKEN": "fixed"},
            attempt_dir=str(attempt), timeout_seconds=2, cleanup_timeout_seconds=1,
            stdout_limit_bytes=65536, stderr_limit_bytes=65536,
            stdin_path=str(input_path))
        self.assert_collected(result)
        data = json.loads((attempt / "stdout.bin").read_text())
        self.assertEqual(str(self.directory), data["cwd"])
        self.assertEqual({"LC_ALL": "C", "TOKEN": "fixed"}, data["env"])
        self.assertEqual([literal], data["args"])
        self.assertEqual(input_path.read_bytes().hex(), data["stdin"])
        self.assertFalse((self.directory / "SHOULD_NOT_EXIST").exists())
        self.assertEqual(hashlib.sha256(input_path.read_bytes()).hexdigest(), result["stdin"]["sha256"])

    def test_concurrent_pipe_pressure_is_collected_exactly(self):
        source = ("import os\n"
                  "for i in range(32):\n"
                  " os.write(1,b'A'*8192)\n"
                  " os.write(2,b'B'*8192)\n")
        result, attempt = self.run_python(source, stdout_limit_bytes=262144,
                                          stderr_limit_bytes=262144)
        self.assert_collected(result)
        self.assertEqual(b"A" * 262144, (attempt / "stdout.bin").read_bytes())
        self.assertEqual(b"B" * 262144, (attempt / "stderr.bin").read_bytes())
        self.assertFalse(result["streams"]["stdout"]["truncated"])

    def test_explicit_executable_preserves_custom_argv0_and_empty_argument(self):
        attempt = self.directory / "custom-argv0"
        source = ("import os; print(open('/proc/self/cmdline','rb').read().hex())")
        argv = ["app", "-I", "-B", "-c", source, "A", "", "B"]
        result = supervisor.run_supervised(
            argv, executable_path=sys.executable, cwd=str(self.directory), env={},
            attempt_dir=str(attempt), timeout_seconds=2, cleanup_timeout_seconds=1,
            stdout_limit_bytes=65536, stderr_limit_bytes=65536)
        self.assert_collected(result)
        observed = bytes.fromhex((attempt / "stdout.bin").read_text().strip()).split(b"\0")[:-1]
        self.assertEqual([arg.encode() for arg in argv], observed)
        self.assertEqual(argv, result["argv"])
        self.assertEqual(str(Path(sys.executable).resolve()), result["executable"]["path"])
        self.assertEqual(hashlib.sha256(Path(sys.executable).read_bytes()).hexdigest(),
                         result["executable"]["sha256"])

    def test_actual_signal_differs_from_exit_128_plus_signal(self):
        signaled, _ = self.run_python("import os,signal; os.kill(os.getpid(),signal.SIGTERM)")
        exited, _ = self.run_python("import sys; sys.exit(143)")
        self.assertEqual("COMPLETED", signaled["status"])
        self.assertTrue(os.WIFSIGNALED(signaled["raw_wait_status"]))
        self.assertEqual(signal.SIGTERM, signaled["wait_status"]["signal"])
        self.assertEqual("signaled", signaled["wait_status"]["kind"])
        self.assert_collected(exited, code=143)
        self.assertNotEqual(signaled["raw_wait_status"], exited["raw_wait_status"])

    def test_timeout_kills_sigterm_ignoring_process_and_retains_prefix(self):
        start = time.monotonic()
        result, attempt = self.run_python(
            "import os,signal,time; signal.signal(signal.SIGTERM,signal.SIG_IGN); "
            "os.write(1,b'READY\\n'); time.sleep(60)", timeout_seconds=0.2)
        self.assertEqual("TIMED_OUT", result["status"])
        self.assertTrue(result["cleanup_complete"])
        self.assertEqual(signal.SIGKILL, result["wait_status"]["signal"])
        self.assertEqual(b"READY\n", (attempt / "stdout.bin").read_bytes())
        self.assertLess(time.monotonic() - start, 3)

    def test_output_limit_is_explicit_failure_with_bounded_artifact(self):
        result, attempt = self.run_python(
            "import os,time; os.write(1,b'X'*8192); time.sleep(60)",
            stdout_limit_bytes=1024)
        self.assertEqual("OUTPUT_LIMIT", result["status"])
        self.assertTrue(result["cleanup_complete"])
        stdout = result["streams"]["stdout"]
        self.assertTrue(stdout["truncated"])
        self.assertEqual(8192, stdout["bytes_observed"])
        self.assertEqual(7168, stdout["discarded_observed_bytes"])
        self.assertEqual(b"X" * 1024, (attempt / "stdout.bin").read_bytes())

    def test_late_completion_observation_cannot_accept_overdue_exit(self):
        attempt = self.directory / "delayed-observer"
        source = (
            "import importlib.util,time\n"
            "from pathlib import Path\n"
            "spec=importlib.util.spec_from_file_location('s',{source!r})\n"
            "s=importlib.util.module_from_spec(spec); spec.loader.exec_module(s)\n"
            "original=s._exited\n"
            "def delayed(pid):\n"
            " time.sleep(.15); return original(pid)\n"
            "s._exited=delayed\n"
            "s._worker(Path({attempt!r}))\n"
        ).format(source=str(SOURCE), attempt=str(attempt))
        with mock.patch.object(supervisor, "_worker_command",
                               return_value=[sys.executable, "-I", "-B", "-c", source]):
            result = supervisor.run_supervised(
                [sys.executable, "-I", "-B", "-c", "import time; time.sleep(.05)"],
                cwd=str(self.directory), env={}, attempt_dir=str(attempt),
                timeout_seconds=.03, cleanup_timeout_seconds=1,
                stdout_limit_bytes=64, stderr_limit_bytes=64)
        self.assertEqual("TIMED_OUT", result["status"])
        self.assertTrue(result["cleanup_complete"])
        self.assertEqual({"kind": "exited", "code": 0}, result["wait_status"])
        self.assertGreater(result["payload_completion_observed_monotonic"],
                           result["payload_monotonic_deadline"])

    def test_delayed_spawn_return_cannot_shift_payload_deadline(self):
        attempt = self.directory / "delayed-spawn-return"
        source = (
            "import importlib.util,time\n"
            "from pathlib import Path\n"
            "spec=importlib.util.spec_from_file_location('s',{source!r})\n"
            "s=importlib.util.module_from_spec(spec); spec.loader.exec_module(s)\n"
            "original=s.subprocess.Popen\n"
            "def delayed(*args,**kwargs):\n"
            " process=original(*args,**kwargs); time.sleep(.15); return process\n"
            "s.subprocess.Popen=delayed\n"
            "s._worker(Path({attempt!r}))\n"
        ).format(source=str(SOURCE), attempt=str(attempt))
        with mock.patch.object(supervisor, "_worker_command",
                               return_value=[sys.executable, "-I", "-B", "-c", source]):
            result = supervisor.run_supervised(
                [sys.executable, "-I", "-B", "-c", "import time; time.sleep(.05)"],
                cwd=str(self.directory), env={}, attempt_dir=str(attempt),
                timeout_seconds=.03, cleanup_timeout_seconds=1,
                stdout_limit_bytes=64, stderr_limit_bytes=64)
        self.assertEqual("TIMED_OUT", result["status"])
        self.assertTrue(result["cleanup_complete"])
        self.assertEqual({"kind": "exited", "code": 0}, result["wait_status"])
        self.assertGreater(result["payload_completion_observed_monotonic"] -
                           result["payload_monotonic_started"], .1)

    def test_stderr_limit_is_independent(self):
        result, attempt = self.run_python(
            "import os; os.write(1,b'OK'); os.write(2,b'E'*4096)",
            stdout_limit_bytes=100, stderr_limit_bytes=17)
        self.assertEqual("OUTPUT_LIMIT", result["status"])
        self.assertEqual(b"OK", (attempt / "stdout.bin").read_bytes())
        self.assertEqual(b"E" * 17, (attempt / "stderr.bin").read_bytes())
        self.assertFalse(result["streams"]["stdout"]["truncated"])

    def test_empty_streams_allow_zero_limit(self):
        result, _ = self.run_python("pass", stdout_limit_bytes=0, stderr_limit_bytes=0)
        self.assert_collected(result)

    def test_inherited_pipe_holder_is_killed_and_reaped(self):
        source = ("import os,time\n"
                  "pid=os.fork()\n"
                  "if pid == 0:\n"
                  " os.write(1,('child=%d\\n'%os.getpid()).encode()); time.sleep(60)\n"
                  "else:\n"
                  " time.sleep(.05); os._exit(0)\n")
        result, attempt = self.run_python(source)
        self.assertEqual("ORPHANED_DESCENDANTS", result["status"])
        self.assertTrue(result["cleanup_complete"])
        pid = int((attempt / "stdout.bin").read_text().strip().split("=")[1])
        self.assertIn(pid, [record["pid"] for record in result["descendants"]])
        self.assertFalse(Path("/proc/{}".format(pid)).exists())
        self.assertTrue(all(stream["eof"] for stream in result["streams"].values()))

    def test_session_escaping_pipe_holder_is_adopted_and_reaped(self):
        source = ("import os,signal,time\n"
                  "pid=os.fork()\n"
                  "if pid == 0:\n"
                  " os.setsid(); signal.signal(signal.SIGTERM,signal.SIG_IGN)\n"
                  " os.write(2,('child=%d\\n'%os.getpid()).encode()); time.sleep(60)\n"
                  "else:\n"
                  " time.sleep(.05); os._exit(0)\n")
        result, attempt = self.run_python(source)
        self.assertEqual("ORPHANED_DESCENDANTS", result["status"])
        self.assertTrue(result["cleanup_complete"])
        pid = int((attempt / "stderr.bin").read_text().strip().split("=")[1])
        child = next(record for record in result["descendants"] if record["pid"] == pid)
        self.assertNotEqual(result["process"]["session"], child["session"])
        self.assertFalse(Path("/proc/{}".format(pid)).exists())

    def test_missing_executable_preserves_launch_error(self):
        attempt = self.directory / "missing-executable"
        result = supervisor.run_supervised(
            [str(self.directory / "does-not-exist")], cwd=str(self.directory), env={},
            attempt_dir=str(attempt), timeout_seconds=1, cleanup_timeout_seconds=1,
            stdout_limit_bytes=64, stderr_limit_bytes=64)
        self.assertEqual("LAUNCH_ERROR", result["status"])
        self.assertEqual(2, result["errno"])
        self.assertIsNone(result["raw_wait_status"])
        self.assertTrue(result["cleanup_complete"])
        self.assertEqual(b"", (attempt / "stdout.bin").read_bytes())

    def test_nonregular_or_symlink_stdin_is_rejected_without_blocking(self):
        regular = self.directory / "regular"
        regular.write_bytes(b"data")
        symlink = self.directory / "symlink"
        symlink.symlink_to(regular)
        fifo = self.directory / "fifo"
        os.mkfifo(str(fifo))
        for path in (symlink, fifo):
            with self.subTest(path=path):
                result, _ = self.run_python("raise RuntimeError('must not run')",
                                            stdin_path=str(path))
                self.assertEqual("SUPERVISOR_ERROR", result["status"])
                self.assertTrue(result["cleanup_complete"])
                self.assertIsNone(result["raw_wait_status"])

    def test_stopped_private_worker_has_independent_deadline_and_tree_rescue(self):
        child_file = self.directory / "stalled-child"
        grandchild_file = self.directory / "stalled-grandchild"
        source = (
            "import importlib.util,os,signal,time\n"
            "from pathlib import Path\n"
            "spec=importlib.util.spec_from_file_location('s',{source!r})\n"
            "s=importlib.util.module_from_spec(spec); spec.loader.exec_module(s)\n"
            "s._set_subreaper()\n"
            "def finish(signum,frame):\n"
            " while True:\n"
            "  try: os.waitpid(-1,0)\n"
            "  except ChildProcessError: break\n"
            " os._exit(0)\n"
            "signal.signal(signal.SIGTERM,finish)\n"
            "pid=os.fork()\n"
            "if pid == 0:\n"
            " os.setsid(); signal.signal(signal.SIGTERM,signal.SIG_IGN)\n"
            " grandchild=os.fork()\n"
            " if grandchild == 0:\n"
            "  os.setsid(); Path({grandchild!r}).write_text(str(os.getpid()))\n"
            " else:\n"
            "  Path({child!r}).write_text(str(os.getpid()))\n"
            " time.sleep(60)\n"
            "else:\n"
            " while not Path({grandchild!r}).exists(): time.sleep(.005)\n"
            " os.kill(os.getpid(),signal.SIGSTOP); time.sleep(60)\n"
        ).format(source=str(SOURCE), child=str(child_file), grandchild=str(grandchild_file))
        attempt = self.directory / "stalled-worker"
        with mock.patch.object(supervisor, "_worker_command",
                               return_value=[sys.executable, "-I", "-B", "-c", source]):
            start = time.monotonic()
            result = supervisor.run_supervised(
                [sys.executable, "-c", "pass"], cwd=str(self.directory), env={},
                attempt_dir=str(attempt), timeout_seconds=.05, cleanup_timeout_seconds=.5,
                stdout_limit_bytes=64, stderr_limit_bytes=64)
        self.assertLess(time.monotonic() - start, 4)
        self.assertEqual("SUPERVISOR_ERROR", result["status"])
        self.assertFalse(result["application_acceptance"])
        self.assertFalse(result["cleanup_complete"])
        self.assertEqual("independent worker deadline", result["watchdog_rescue"]["reason"])
        self.assertTrue((attempt / "worker-failure.json").is_file())
        for path in (child_file, grandchild_file):
            pid = int(path.read_text())
            self.assertFalse(Path("/proc/{}".format(pid)).exists())

    def test_parent_keyboard_interrupt_preserves_failure_and_cleans_child(self):
        attempt = self.directory / "interrupted-parent"
        source = (
            "import importlib.util,sys\n"
            "spec=importlib.util.spec_from_file_location('s',{source!r})\n"
            "s=importlib.util.module_from_spec(spec); spec.loader.exec_module(s)\n"
            "try:\n"
            " s.run_supervised([sys.executable,'-I','-B','-c',"
            "\"import os,time; os.write(1,('child=%d\\\\n'%os.getpid()).encode()); time.sleep(60)\"],"
            "cwd={cwd!r},env={{}},attempt_dir={attempt!r},timeout_seconds=10,"
            "cleanup_timeout_seconds=1,stdout_limit_bytes=64,stderr_limit_bytes=64)\n"
            "except KeyboardInterrupt:\n"
            " sys.exit(130)\n"
        ).format(source=str(SOURCE), cwd=str(self.directory), attempt=str(attempt))
        with (self.directory / "parent.stderr").open("wb") as error:
            parent = subprocess.Popen([sys.executable, "-I", "-B", "-c", source],
                                      stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                      stderr=error, start_new_session=True)
            try:
                deadline = time.monotonic() + 3
                output = attempt / "stdout.bin"
                while time.monotonic() < deadline:
                    if output.exists() and output.stat().st_size:
                        break
                    time.sleep(.01)
                self.assertTrue(output.exists() and output.stat().st_size,
                                "private child did not reach READY before deadline")
                parent.send_signal(signal.SIGINT)
                self.assertEqual(130, parent.wait(timeout=3))
                report = json.loads((attempt / "worker-failure.json").read_text())
                self.assertEqual("INTERRUPTED", report["status"])
                self.assertFalse(report["application_acceptance"])
                pid = int(output.read_text().strip().split("=")[1])
                self.assertFalse(Path("/proc/{}".format(pid)).exists())
            finally:
                if parent.poll() is None:
                    parent.kill()
                    parent.wait(timeout=2)

    def test_preexisting_attempt_is_never_overwritten(self):
        attempt = self.directory / "existing"
        attempt.mkdir()
        sentinel = attempt / "report.json"
        sentinel.write_bytes(b"immutable\n")
        with self.assertRaises(FileExistsError):
            supervisor.run_supervised(
                [sys.executable, "-c", "pass"], cwd=str(self.directory), env={},
                attempt_dir=str(attempt), timeout_seconds=1, cleanup_timeout_seconds=1,
                stdout_limit_bytes=64, stderr_limit_bytes=64)
        self.assertEqual(b"immutable\n", sentinel.read_bytes())
        self.assertEqual([sentinel], list(attempt.iterdir()))

    def test_malformed_arguments_fail_before_attempt_creation(self):
        cases = [dict(argv="echo bad"), dict(argv=[]), dict(argv=["python3"]),
                 dict(argv=[sys.executable, "bad\0argument"]),
                 dict(env={"A=B": "bad"}), dict(env={"A": 3}),
                 dict(timeout_seconds=float("nan")), dict(timeout_seconds=0),
                 dict(cleanup_timeout_seconds=True), dict(stdout_limit_bytes=-1),
                 dict(stderr_limit_bytes=True)]
        for i, override in enumerate(cases):
            with self.subTest(override=override):
                attempt = self.directory / "invalid-{}".format(i)
                options = dict(argv=[sys.executable, "-c", "pass"],
                               cwd=str(self.directory), env={}, attempt_dir=str(attempt),
                               timeout_seconds=1, cleanup_timeout_seconds=1,
                               stdout_limit_bytes=64, stderr_limit_bytes=64)
                options.update(override)
                with self.assertRaises(ValueError):
                    supervisor.run_supervised(**options)
                self.assertFalse(attempt.exists())


if __name__ == "__main__":
    unittest.main()
