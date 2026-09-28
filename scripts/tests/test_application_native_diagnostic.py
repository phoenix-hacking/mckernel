import copy
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import stat
import subprocess
import tempfile
import time
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("native_diagnostic", ROOT / "scripts/application-tests/native_diagnostic.py")
ND = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ND)


class Process:
    def __init__(self, stuck=False, never_reap=False):
        self.calls, self.stuck, self.never_reap = [], stuck, never_reap
    def communicate(self, timeout):
        self.calls.append("communicate")
        return b"QEMU stdout is not payload", b"QEMU stderr is not payload"
    def terminate(self): self.calls.append("terminate")
    def kill(self): self.calls.append("kill")
    def wait(self, timeout):
        self.calls.append("wait")
        if self.never_reap or (self.stuck and "kill" not in self.calls):
            raise subprocess.TimeoutExpired("fake", timeout)
        return 0


class Qmp:
    def negotiate(self, timeout): pass
    def resume(self, timeout): pass
    def wait_shutdown(self, timeout): return {"status": "shutdown"}
    def terminate(self, timeout): pass
    def close(self, timeout): pass


class NativeDiagnosticTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.files = {}
        for name in (*ND.ARTIFACTS, *ND.MODULE_NAMES):
            path = self.root / name
            path.write_bytes(name.encode()); path.chmod(0o644)
            self.files[name] = path
        self.manifest_path = self.root / "manifest.json"
        self.raw = {"schema_version": 1, "kind": "native-diagnostic-manifest", "case_id": "pilot",
                    "artifacts": {name: self.ref(name) for name in ND.ARTIFACTS},
                    "modules": [self.ref(name) for name in ND.MODULE_NAMES],
                    "profile": {"memory_mib": 8192, "vcpus": 4, "numa_nodes": 2},
                    "payload": {"cwd": "/case/work", "argv": ["/bin/mcexec", "-t", "1", "0", "app", "A", "", "B"],
                                "env": {"PATH": "/usr/bin:/bin", "COKERNEL_PATH": "/apps"},
                                "oracle": {"stdout_hex": "4100420a", "stderr_hex": "", "exit_code": 37},
                                "stdout_limit_bytes": 1024, "stderr_limit_bytes": 1024}}
        self.manifest_path.write_text(json.dumps(self.raw))
        self.manifest = ND.load_manifest(str(self.manifest_path))
        self.counter = 0

    def tearDown(self): self.tmp.cleanup()

    def ref(self, name):
        data = self.files[name].read_bytes()
        return {"path": str(self.files[name]), "size": len(data), "sha256": hashlib.sha256(data).hexdigest(), "mode": stat.S_IFREG | 0o644}

    def report(self):
        report = {key: copy.deepcopy(self.manifest["payload"][key]) for key in ("argv", "env", "cwd")}
        report.update(raw_wait_status=37 << 8, started_ns=100, reaped_ns=200, finished_ns=300, procfs_empty=True, streams={})
        for name in ("stdout", "stderr"):
            data = self.manifest["payload"]["oracle"][name + "_hex"]
            report["streams"][name] = {"hex": data, "eof": True, "truncated": False,
                                       "observed": len(data) // 2, "retained": len(data) // 2,
                                       "discarded": 0, "limit": 1024, "eof_ns": 250}
        return report

    def serial(self, report=None):
        # Synthetic protocol fixture, never actual McKernel evidence.
        return "\n".join([
            "application SCHEDULE os=0 generation=1 pid=12 cpu=0",
            "application procfs published os=0 generation=1 pid=12 tid=12",
            "application_syscall=delivered os=0 generation=1 pid=12 worker=9 delivery=3 cpu=0 number=1",
            "application_syscall=returned os=0 generation=1 pid=12 worker=9 delivery=3 cpu=0 value=4",
            "application_syscall=return_route os=0 generation=1 pid=12 worker=9 delivery=3 launcher_cpu=1 guest_cpu=0",
            "application_syscall=delivered os=0 generation=1 pid=12 worker=9 delivery=4 cpu=0 number=231",
            "application procfs deleted os=0 generation=1 pid=12 tid=12",
            "application retirement os=0 generation=1 pid=12 token=2 errno=0",
            "application_process=release os=0 generation=1 pid=12 cleanup_errno=0",
            "ND_PAYLOAD " + json.dumps(self.report() if report is None else report), ""])

    def observation(self, report=None):
        return {"serial": self.serial(report), "debugcon": "guest log", "qmp": {"status": "shutdown"},
                "teardown": True, "started_at": 1, "finished_at": 2, "deadline": 3}

    def attempt(self):
        self.counter += 1
        attempt = ND.prepare_attempt(self.manifest, self.root, "attempt-" + str(self.counter))
        (attempt / "serial.log").write_text(self.serial())
        (attempt / "debugcon.log").write_text("guest log")
        return attempt

    def exercise(self, attempt, process=None, qmp=None, timeout=1):
        return ND.exercise_lifecycle(self.manifest, attempt, lambda **kw: process or Process(), lambda **kw: qmp or Qmp(), timeout)

    def test_staging_blocker_prevents_spawn_and_records_terminal(self):
        attempt = self.attempt(); factory = mock.Mock(side_effect=AssertionError("must not spawn"))
        with self.assertRaisesRegex(ND.DiagnosticError, "guest staging unavailable"):
            ND.run_diagnostic(self.manifest, attempt, factory, factory)
        factory.assert_not_called()
        result = json.loads((attempt / "result.json").read_text())
        self.assertEqual(result["status"], "BLOCKED")
        self.assertFalse(result["mckernel_application_executed"])
        self.assertTrue((attempt / "first-failure.jsonl").read_text())
        self.assertFalse((attempt / "root.img").exists())

    def test_retained_profile_and_payload_plan(self):
        plan = ND.build_command(self.manifest, self.attempt()); args = plan["argv"]
        self.assertEqual(args[:7], [ND.QEMU, "-machine", "q35", "-accel", "tcg,thread=multi", "-cpu", "max,la57=off"])
        for item in ("4,sockets=2,cores=2,threads=1", "-no-reboot", "-no-shutdown", "-nic", ND.APPEND): self.assertIn(item, args)
        self.assertEqual(args.count("-numa"), 2); self.assertNotIn("-drive", args)
        self.assertFalse(plan["runtime_ready"])
        for item in ("/apps/app", "/images/mckernel.img"): self.assertIn(item, plan["overlay"]["guest_destinations"])
        self.assertIn("insmod /modules/ihk-smp-x86_64.ko ihk_trampoline=524288", plan["overlay"]["init_sequence"])

    def test_manifest_rejects_implicit_oracle_env_profile_and_types(self):
        variants = []
        for field in ("oracle", "stdout_limit_bytes"):
            value = copy.deepcopy(self.raw); del value["payload"][field]; variants.append(value)
        value = copy.deepcopy(self.raw); value["profile"]["append"] = "console=ttyS0"; variants.append(value)
        value = copy.deepcopy(self.raw); del value["payload"]["env"]["COKERNEL_PATH"]; variants.append(value)
        value = copy.deepcopy(self.raw); value["schema_version"] = True; variants.append(value)
        for value in variants:
            self.manifest_path.write_text(json.dumps(value))
            with self.assertRaises(ND.DiagnosticError): ND.load_manifest(str(self.manifest_path))

    def test_artifact_drift_duplicate_json_and_stale_attempt(self):
        self.files["mcexec"].write_bytes(b"wrong")
        with self.assertRaises(ND.DiagnosticError): ND.load_manifest(str(self.manifest_path))
        self.manifest_path.write_text('{"schema_version":1,"schema_version":1}')
        with self.assertRaises(ND.DiagnosticError): ND.load_manifest(str(self.manifest_path))
        attempt = self.attempt()
        with self.assertRaises(ND.DiagnosticError): ND.prepare_attempt(self.manifest, self.root, attempt.name)
        (attempt / "qmp.sock").touch()
        with self.assertRaises(ND.DiagnosticError): ND.build_command(self.manifest, attempt)

    def test_positive_fake_lifecycle_is_only_protocol_evidence(self):
        attempt = self.attempt(); process = Process(); result = self.exercise(attempt, process)
        self.assertEqual(result["status"], "PROTOCOL_PASS")
        self.assertFalse(result["mckernel_application_executed"])
        self.assertEqual(result["guest_report"]["raw_wait_status"], 37 << 8)
        self.assertIn("QEMU stdout", (attempt / "qemu.stdout").read_text())
        self.assertEqual(process.calls, ["communicate", "terminate", "wait"])

    def test_qemu_output_alone_cannot_pass(self):
        attempt = self.attempt(); (attempt / "serial.log").write_text("")
        with self.assertRaisesRegex(ND.DiagnosticError, "guest payload report"): self.exercise(attempt)

    def test_wait_eof_accounting_timestamps_and_routes(self):
        variants = []
        for key, value in (("raw_wait_status", 9), ("raw_wait_status", True), ("raw_wait_status", 0), ("started_ns", 400), ("procfs_empty", False)):
            report = self.report(); report[key] = value; variants.append(self.observation(report))
        for key, value in (("eof", False), ("truncated", True), ("observed", 5), ("retained", True), ("discarded", 1), ("limit", 1025), ("eof_ns", 301), ("hex", "41")):
            report = self.report(); report["streams"]["stdout"][key] = value; variants.append(self.observation(report))
        for old, new in (("delivery=3 launcher", "delivery=99 launcher"), ("cleanup_errno=0", "cleanup_errno=1"), ("number=231", "number=0"), ("guest_cpu=0", "guest_cpu=1")):
            obs = self.observation(); obs["serial"] = obs["serial"].replace(old, new); variants.append(obs)
        for obs in variants:
            with self.subTest(obs=obs):
                with self.assertRaises(ND.DiagnosticError): ND.evaluate(self.manifest, obs)

    def test_all_original_failure_markers_reject(self):
        for marker in ("WARNING:", "soft lockup", "clear_host_pte failed", "Kernel panic", "Oops:", "BUG:", "rcu_preempt detected stalls", "hard LOCKUP", "continuing service error", "cleanup retained"):
            obs = self.observation(); obs["debugcon"] += marker
            with self.assertRaises(ND.DiagnosticError): ND.evaluate(self.manifest, obs)

    def test_nonfinite_timeout_recorded(self):
        for timeout in (math.nan, math.inf, -1, 0, True):
            attempt = self.attempt()
            with self.assertRaisesRegex(ND.DiagnosticError, "finite deadline"): self.exercise(attempt, timeout=timeout)
            self.assertEqual(json.loads((attempt / "result.json").read_text())["status"], "FAIL")

    def test_qmp_deadline_and_errors_cannot_skip_kill_reap(self):
        class BrokenQmp(Qmp):
            def negotiate(self, timeout): time.sleep(1)
            def terminate(self, timeout): raise RuntimeError("quit broken")
            def close(self, timeout): raise RuntimeError("close broken")
        attempt = self.attempt(); process = Process(stuck=True); start = time.monotonic()
        with self.assertRaisesRegex(ND.DiagnosticError, "absolute deadline"): self.exercise(attempt, process, BrokenQmp(), timeout=0.02)
        self.assertLess(time.monotonic() - start, 0.5)
        self.assertEqual(process.calls, ["terminate", "wait", "kill", "wait"])
        result = json.loads((attempt / "result.json").read_text())
        self.assertTrue(result["cleanup"]["reaped"])
        self.assertEqual(result["failure"]["type"], "TimeoutError")
        self.assertIn("quit broken", str(result["cleanup"]["errors"]))

    def test_each_blocking_qmp_or_communicate_step_is_bounded(self):
        for phase in ("negotiate", "resume", "wait_shutdown", "communicate"):
            attempt = self.attempt(); process = Process(); qmp = Qmp()
            def block(timeout): time.sleep(1)
            setattr(process if phase == "communicate" else qmp, phase, block)
            with self.assertRaisesRegex(ND.DiagnosticError, "absolute deadline"):
                self.exercise(attempt, process, qmp, timeout=0.01)
            self.assertIn("wait", process.calls)
            self.assertEqual(len((attempt / "first-failure.jsonl").read_text().splitlines()), 1)

    def test_journal_write_failure_does_not_skip_reaping(self):
        attempt = self.attempt(); process = Process()
        (attempt / "serial.log").write_text("no guest report")
        with mock.patch.object(ND, "_append_failure", side_effect=OSError("disk failure")):
            with self.assertRaises(OSError): self.exercise(attempt, process)
        self.assertIn("wait", process.calls)

    def test_dangling_terminal_symlink_cannot_be_replaced(self):
        attempt = self.attempt(); target = attempt / "result.json"
        target.symlink_to(attempt / "absent")
        with self.assertRaises(ND.DiagnosticError): ND.write_record(attempt, {"status": "PASS"})
        self.assertTrue(target.is_symlink())

    def test_factory_and_communicate_errors_preserved(self):
        for phase in ("process", "qmp", "communicate"):
            attempt = self.attempt(); process = Process()
            def fail(**kwargs): raise RuntimeError(phase + " failure")
            if phase == "communicate": process.communicate = fail
            with self.assertRaisesRegex(ND.DiagnosticError, phase + " failure"):
                ND.exercise_lifecycle(self.manifest, attempt, fail if phase == "process" else lambda **kw: process,
                                      fail if phase == "qmp" else lambda **kw: Qmp())
            result = json.loads((attempt / "result.json").read_text())
            self.assertIn(phase, result["failure"]["error"])
            if phase != "process": self.assertIn("wait", process.calls)

    def test_unreaped_process_late_completion_capture_overflow(self):
        attempt = self.attempt()
        with self.assertRaisesRegex(ND.DiagnosticError, "teardown uncertain"): self.exercise(attempt, Process(never_reap=True))
        self.assertFalse(json.loads((attempt / "result.json").read_text())["cleanup"]["reaped"])
        obs = self.observation(); obs["finished_at"] = 3
        with self.assertRaisesRegex(ND.DiagnosticError, "late completion"): ND.evaluate(self.manifest, obs)
        attempt = self.attempt(); (attempt / "serial.log").write_bytes(b"x" * (ND.MAX_JSON + 1))
        with self.assertRaisesRegex(ND.DiagnosticError, "capture limit"): self.exercise(attempt)

    def test_terminal_record_cannot_be_replaced_or_raced(self):
        attempt = self.attempt(); ND.write_record(attempt, {"status": "FAIL"}, {"error": "original"})
        original = (attempt / "result.json").read_bytes()
        with self.assertRaises(ND.DiagnosticError): ND.write_record(attempt, {"status": "PASS"})
        self.assertEqual((attempt / "result.json").read_bytes(), original)
        attempt = self.attempt(); original_link = ND.os.link
        def race(source, dest, **kw):
            Path(dest).write_text("concurrent terminal")
            return original_link(source, dest, **kw)
        with mock.patch.object(ND.os, "link", race):
            with self.assertRaises(FileExistsError): ND.write_record(attempt, {"status": "PASS"})
        self.assertEqual((attempt / "result.json").read_text(), "concurrent terminal")


if __name__ == "__main__": unittest.main()
