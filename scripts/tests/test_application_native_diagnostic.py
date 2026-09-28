import hashlib
import json
import os
from pathlib import Path
import stat
import tempfile
import unittest
import importlib.util

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("native_diagnostic", ROOT / "scripts/application-tests/native_diagnostic.py")
ND = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ND)


class NativeDiagnosticTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.files = {}
        for name in ("bzImage", "initramfs", "root_base", "mckernel_image", "mcexec", "payload", *ND.MODULE_NAMES):
            path = self.root / name
            path.write_bytes(name.encode())
            path.chmod(0o644)
            self.files[name] = path
        self.manifest_path = self.root / "manifest.json"
        self.manifest_path.write_text(json.dumps(self.raw_manifest()))

    def tearDown(self):
        self.tmp.cleanup()

    def ref(self, name):
        data = self.files[name].read_bytes()
        return {"path": str(self.files[name]), "size": len(data), "sha256": hashlib.sha256(data).hexdigest(), "mode": stat.S_IFREG | 0o644}

    def raw_manifest(self):
        return {"schema_version": 1, "kind": "native-diagnostic-manifest", "case_id": "pilot",
                "artifacts": {name: self.ref(name) for name in ND.ARTIFACTS},
                "modules": [self.ref(name) for name in ND.MODULE_NAMES],
                "profile": {"memory_mib": 8192, "vcpus": 4, "numa_nodes": 2},
                "payload": {"cwd": "/case/work", "argv": ["/bin/mcexec", "-t", "1", "0", "app", "A", "", "B"],
                            "env": {"PATH": "/usr/bin:/bin"}}}

    def manifest(self):
        return ND.load_manifest(str(self.manifest_path))

    def observation(self, **changes):
        value = {"stdout": b"", "stderr": b"", "exit_code": 0, "serial": "boot", "debugcon": "debug",
                 "qmp": {"status": "running"}, "teardown": True, "timed_out": False, "truncated": False}
        value.update(changes)
        return value

    def test_positive_prepare_command_overlay_evaluation(self):
        m = self.manifest()
        attempt = ND.prepare_attempt(m, self.root, "attempt-1")
        command = ND.build_command(m, attempt)
        self.assertEqual(command["argv"][:5], [ND.QEMU, "-m", "8192", "-smp", "4"])
        self.assertEqual(command["argv"].count("-numa"), 2)
        self.assertIn("-qmp", command["argv"])
        self.assertEqual(command["overlay"]["load_modules"], list(ND.MODULE_NAMES))
        self.assertFalse(ND.evaluate(m, self.observation())["application_acceptance"])

    def test_hash_drift(self):
        self.files["mcexec"].write_bytes(b"changed")
        with self.assertRaises(ND.DiagnosticError): self.manifest()

    def test_malformed_manifest(self):
        self.manifest_path.write_text("{\"schema_version\":1,}")
        with self.assertRaises(ND.DiagnosticError): ND.load_manifest(str(self.manifest_path))

    def test_stale_attempt_and_socket(self):
        m = self.manifest()
        attempt = self.root / "attempt-1"
        attempt.mkdir(); attempt.chmod(0o700)
        with self.assertRaises(ND.DiagnosticError): ND.prepare_attempt(m, self.root, "attempt-1")
        (attempt / "qmp.sock").touch()
        with self.assertRaises(ND.DiagnosticError): ND.build_command(m, attempt)

    def test_wrong_exit_output(self):
        m = self.manifest()
        with self.assertRaises(ND.DiagnosticError): ND.evaluate(m, self.observation(exit_code=2))
        with self.assertRaises(ND.DiagnosticError): ND.evaluate(m, self.observation(stdout=b"noise"))

    def test_timeout_and_teardown_uncertainty(self):
        m = self.manifest()
        with self.assertRaises(ND.DiagnosticError): ND.evaluate(m, self.observation(timed_out=True))
        with self.assertRaises(ND.DiagnosticError): ND.evaluate(m, self.observation(teardown=False))

    def test_adversarial_markers_types_and_backend_lifecycle(self):
        raw = self.raw_manifest(); raw["schema_version"] = True
        self.manifest_path.write_text(json.dumps(raw))
        with self.assertRaises(ND.DiagnosticError): self.manifest()
        raw = self.raw_manifest(); raw["payload"]["env"]["PATH"] = "bad\0path"
        self.manifest_path.write_text(json.dumps(raw))
        with self.assertRaises(ND.DiagnosticError): self.manifest()
        self.manifest_path.write_text(json.dumps(self.raw_manifest()))
        m = self.manifest(); attempt = ND.prepare_attempt(m, self.root, "attempt-3")

        class Process:
            returncode = 0
            def communicate(self, timeout): return b"", b""
            def poll(self): return 0
            def wait(self, timeout): return 0
            def terminate(self): pass
        class Qmp:
            def negotiate(self): pass
            def resume(self): pass
            def query_status(self): return {"status": "running"}
            def terminate(self): pass
            def close(self): pass
        result = ND.run_diagnostic(m, attempt, lambda *a, **k: Process(), lambda socket: Qmp())
        self.assertEqual(result["status"], "PASS")
        self.assertFalse(result["application_acceptance"])
        with self.assertRaises(ND.DiagnosticError): ND.run_diagnostic(m, attempt, None, None)

        bad = self.observation(serial="kernel BUG: bad")
        with self.assertRaises(ND.DiagnosticError): ND.evaluate(m, bad)

    def test_first_failure_and_atomic_record(self):
        m = self.manifest(); attempt = ND.prepare_attempt(m, self.root, "attempt-2")
        ND.write_record(attempt, {"status": "FAIL"}, {"error": "timeout"})
        self.assertEqual(json.loads((attempt / "result.json").read_text())["status"], "FAIL")
        self.assertIn("timeout", (attempt / "first-failure.jsonl").read_text())


if __name__ == "__main__": unittest.main()
