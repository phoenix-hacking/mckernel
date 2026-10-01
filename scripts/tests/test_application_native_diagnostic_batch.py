import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("batch", ROOT / "scripts/application-tests/native_diagnostic_batch.py")
batch = importlib.util.module_from_spec(spec); spec.loader.exec_module(batch)


class BatchTests(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory()
        self.root = Path(self.t.name)
        self.manifest = self.root / "manifest"; self.manifest.write_bytes(b"manifest")
        self.release = self.root / "release"
        self.cmds = [["case-a"], ["case-b"], ["case-c"]]
        self._write_release("a", self.cmds[0]); self._write_release("b", self.cmds[1]); self._write_release("c", self.cmds[2])

    def tearDown(self): self.t.cleanup()

    def _write_release(self, cid, command):
        obj = {"status": "PASS_EXECUTION", "case_id": cid,
               "manifest_sha256": hashlib.sha256(self.manifest.read_bytes()).hexdigest(), "command": command}
        (self.root / ("release-" + cid)).write_text(json.dumps(obj))

    def _spec(self, ids=("a", "b", "c")):
        cases = []
        for cid in ids:
            command = self.cmds[ord(cid)-97]
            cases.append({"case_id": cid, "command": command, "timeout_seconds": 2,
                          "manifest": {"path": str(self.manifest), "sha256": hashlib.sha256(self.manifest.read_bytes()).hexdigest()},
                          "release": {"path": str(self.root / ("release-" + cid)), "sha256": hashlib.sha256((self.root / ("release-" + cid)).read_bytes()).hexdigest()},
                          "output_name": cid + ".json"})
        return {"schema_version": 1, "kind": "native-diagnostic-batch", "cases": cases}

    def _write_spec(self, obj):
        p = self.root / "batch.json"; p.write_text(json.dumps(obj)); return p

    def test_stop_on_first_nonzero_and_preserve_exact_bytes(self):
        calls = []
        def runner(command, **kwargs):
            calls.append(command)
            return subprocess.CompletedProcess(command, 0 if command != ["case-b"] else 7,
                                               b"out-" + command[0].encode(), b"err")
        out = self.root / "out"
        result = batch.run_batch(self._write_spec(self._spec()), out, runner=runner, now=iter([1, 2, 3, 4, 5, 6]).__next__)
        self.assertEqual(calls, [["case-a"], ["case-b"]]); self.assertTrue(result["stopped_on_failure"])
        self.assertEqual(json.loads((out / "b.json").read_text())["stdout_hex"], b"out-case-b".hex())
        self.assertFalse((out / "c.json").exists())

    def test_reject_duplicate_command_and_release_mismatch(self):
        obj = self._spec(); obj["cases"][1]["command"] = ["case-a"]
        with self.assertRaises(batch.BatchError): batch.validate_spec(obj)
        obj = self._spec(); release = self.root / "release-a"; data = json.loads(release.read_text()); data["case_id"] = "wrong"; release.write_text(json.dumps(data))
        obj["cases"][0]["release"]["sha256"] = hashlib.sha256(release.read_bytes()).hexdigest()
        with self.assertRaises(batch.BatchError): batch.validate_spec(obj)

    def test_timeout_is_uncertain_and_stops(self):
        def runner(command, **kwargs): raise subprocess.TimeoutExpired(command, kwargs["timeout"], output=b"partial")
        result = batch.run_batch(self._write_spec(self._spec()), self.root / "out", runner=runner)
        self.assertTrue(result["stopped_on_failure"])
        row = json.loads((self.root / "out" / "a.json").read_text()); self.assertTrue(row["uncertain"])


if __name__ == "__main__": unittest.main()
