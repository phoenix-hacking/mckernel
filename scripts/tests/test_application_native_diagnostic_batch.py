import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
module = importlib.util.spec_from_file_location(
    "native_diagnostic_batch", ROOT / "scripts/application-tests/native_diagnostic_batch.py")
batch = importlib.util.module_from_spec(module)
module.loader.exec_module(batch)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


class FakeProcess:
    def __init__(self, command, code=0, timed_out=False):
        self.command = command
        self.code = code
        self.timed_out = timed_out
        self.pid = 424242
        self.waits = []
        self.polls = 0

    def wait(self, timeout):
        self.waits.append(timeout)
        if self.timed_out:
            raise subprocess.TimeoutExpired(self.command, timeout)
        return self.code

    def poll(self):
        self.polls += 1
        return None if self.timed_out else self.code

    def kill(self):
        raise AssertionError("the sidecar must never kill the owner")

    def terminate(self):
        raise AssertionError("the sidecar must never signal the owner")


class BatchTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.owner_hash = digest(Path(batch.OWNER).read_bytes())
        self.manifest = self.root / "manifest.json"
        self.manifest.write_bytes(b'{"diagnostic":true}\n')
        self.manifest_hash = digest(self.manifest.read_bytes())
        self.spec_path = self.root / "batch.json"

    def case(self, cid):
        parent = self.root / ("attempt-parent-" + cid)
        parent.mkdir(mode=0o700, exist_ok=True)
        nonce = ("%032x" % (ord(cid) - ord("a") + 1))
        command = batch.PREFIX + [
            "--attempt-parent", str(parent), "--nonce", nonce,
            "--owner-sha256", self.owner_hash, "--manifest", str(self.manifest),
            "--manifest-sha256", self.manifest_hash]
        invocation = digest(json.dumps(command, separators=(",", ":")).encode("utf-8"))
        release = self.root / ("release-" + cid + ".json")
        release.write_text(json.dumps({
            "status": "PASS_EXECUTION", "case_id": cid, "command": command,
            "manifest_sha256": self.manifest_hash,
            "args_manifest_sha256": self.manifest_hash,
            "owner_sha256": self.owner_hash, "owner_uid": 0,
            "attempt_nonce": nonce, "attempt_parent": str(parent),
            "invocation_sha256": invocation,
        }))
        return {"case_id": cid, "command": command, "timeout_seconds": 2,
                "manifest": {"path": str(self.manifest), "sha256": self.manifest_hash},
                "release": {"path": str(release), "sha256": digest(release.read_bytes())},
                "output_name": cid + ".json"}

    def spec(self, ids="abc"):
        return {"schema_version": 1, "kind": "native-diagnostic-batch",
                "cases": [self.case(cid) for cid in ids]}

    def write_spec(self, obj):
        self.spec_path.write_text(json.dumps(obj))
        return self.spec_path

    def test_runs_sequentially_and_stops_on_first_failure(self):
        spec = self.spec()
        calls = []

        def runner(command, **kwargs):
            calls.append((command, kwargs))
            return FakeProcess(command, 7 if len(calls) == 2 else 0)

        out = self.root / "out"
        result = batch.run_batch(self.write_spec(spec), out, runner=runner)
        self.assertEqual([call[0] for call in calls],
                         [spec["cases"][0]["command"], spec["cases"][1]["command"]])
        self.assertTrue(all(call[1]["start_new_session"] and
                            call[1]["stdout"] == subprocess.DEVNULL and
                            call[1]["stderr"] == subprocess.DEVNULL for call in calls))
        self.assertTrue(result["stopped_on_failure"])
        self.assertEqual(result["results"], ["a", "b"])
        self.assertEqual(json.loads((out / "b.json").read_text())["returncode"], 7)
        self.assertFalse((out / "c.json").exists())
        self.assertFalse(list(out.glob(".batch.*")))

    def test_all_success_and_exclusive_output_directory(self):
        spec = self.spec("ab")
        out = self.root / "out"
        result = batch.run_batch(self.write_spec(spec), out,
                                 runner=lambda command, **_: FakeProcess(command))
        self.assertFalse(result["stopped_on_failure"])
        self.assertEqual(result["results"], ["a", "b"])
        self.assertEqual(json.loads((out / "batch-result.json").read_text()), result)
        with self.assertRaises(batch.BatchError):
            batch.run_batch(self.spec_path, out, runner=lambda *_a, **_k: None)

    def test_timeout_retains_uncertain_owner_and_stops(self):
        spec = self.spec()
        calls = []
        process = FakeProcess(spec["cases"][0]["command"], timed_out=True)

        def runner(command, **kwargs):
            calls.append(command)
            return process

        out = self.root / "out"
        result = batch.run_batch(self.write_spec(spec), out, runner=runner)
        self.assertTrue(result["stopped_on_failure"])
        self.assertEqual(len(calls), 1)
        self.assertEqual(process.waits, [2.0])
        self.assertEqual(process.polls, 1)
        row = json.loads((out / "a.json").read_text())
        self.assertEqual(row["error"], "TIMED_OUT_OWNER_RETAINED")
        self.assertTrue(row["uncertain"])
        self.assertEqual(row["launcher_pid"], process.pid)
        self.assertEqual(row["stdio"], "discarded")
        self.assertFalse((out / "b.json").exists())

    def test_timeout_drift_preserves_uncertainty_and_owner_identity(self):
        spec = self.spec()
        process = FakeProcess(spec["cases"][0]["command"], timed_out=True)

        def runner(command, **kwargs):
            self.manifest.write_bytes(b"drift-after-timeout")
            return process

        out = self.root / "out"
        result = batch.run_batch(self.write_spec(spec), out, runner=runner)
        self.assertTrue(result["stopped_on_failure"])
        row = json.loads((out / "a.json").read_text())
        self.assertEqual(row["error"], "POSTRUN_REFUSAL")
        self.assertTrue(row["uncertain"])
        self.assertEqual(row["launcher_pid"], process.pid)
        self.assertIn("launcher_starttime", row)
        self.assertFalse((out / "b.json").exists())

    def test_rechecks_manifest_before_next_case(self):
        spec = self.spec("ab")
        calls = []

        def runner(command, **kwargs):
            calls.append(command)
            self.manifest.write_bytes(b"drift")
            return FakeProcess(command)

        out = self.root / "out"
        result = batch.run_batch(self.write_spec(spec), out, runner=runner)
        self.assertEqual(len(calls), 1)
        self.assertTrue(result["stopped_on_failure"])
        self.assertEqual(json.loads((out / "a.json").read_text())["error"],
                         "POSTRUN_REFUSAL")
        self.assertFalse((out / "b.json").exists())

    def test_rejects_command_release_and_manifest_mismatch(self):
        for change in ("flag", "owner", "nonce", "release", "manifest"):
            with self.subTest(change=change):
                obj = self.spec("a")
                case = obj["cases"][0]
                if change == "flag":
                    case["command"][5] = "--inside"
                elif change == "owner":
                    case["command"][4] = "/tmp/native_diagnostic_container_owner.py"
                elif change == "nonce":
                    case["command"][8] = "f" * 32
                elif change == "release":
                    path = Path(case["release"]["path"])
                    data = json.loads(path.read_text())
                    data["case_id"] = "wrong"
                    path.write_text(json.dumps(data))
                    case["release"]["sha256"] = digest(path.read_bytes())
                else:
                    case["command"][-1] = "f" * 64
                with self.assertRaises(batch.BatchError):
                    batch.validate_spec(obj)

    def test_rejects_reuse_and_bad_bounds(self):
        obj = self.spec("ab")
        obj["cases"][1]["command"] = obj["cases"][0]["command"]
        with self.assertRaises(batch.BatchError):
            batch.validate_spec(obj)
        obj = self.spec("a")
        obj["cases"][0]["timeout_seconds"] = float("nan")
        with self.assertRaises(batch.BatchError):
            batch.validate_spec(obj)
        obj = self.spec("a")
        obj["cases"][0]["output_name"] = "batch-result.json"
        with self.assertRaises(batch.BatchError):
            batch.validate_spec(obj)

    def test_release_fields_bind_the_exact_invocation(self):
        changes = {"attempt_nonce": "f" * 32, "attempt_parent": "/tmp/other",
                   "owner_sha256": "f" * 64, "owner_uid": True,
                   "manifest_sha256": "f" * 64, "args_manifest_sha256": "f" * 64,
                   "invocation_sha256": "f" * 64, "status": "NOT_RELEASED"}
        for field, value in changes.items():
            with self.subTest(field=field):
                obj = self.spec("a")
                path = Path(obj["cases"][0]["release"]["path"])
                release = json.loads(path.read_text())
                release[field] = value
                path.write_text(json.dumps(release))
                obj["cases"][0]["release"]["sha256"] = digest(path.read_bytes())
                with self.assertRaises(batch.BatchError):
                    batch.validate_spec(obj)

    def test_existing_destination_is_never_unlinked(self):
        spec = self.spec("a")
        out = self.root / "out"

        def runner(command, **kwargs):
            (out / "a.json").write_bytes(b"other writer")
            return FakeProcess(command)

        with self.assertRaises(FileExistsError):
            batch.run_batch(self.write_spec(spec), out, runner=runner)
        self.assertEqual((out / "a.json").read_bytes(), b"other writer")
        self.assertFalse(list(out.glob(".batch.*")))


if __name__ == "__main__":
    unittest.main()
