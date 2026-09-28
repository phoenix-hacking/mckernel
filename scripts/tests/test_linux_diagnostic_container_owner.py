import json
import tempfile
import unittest
from pathlib import Path
import importlib.util

SOURCE = Path(__file__).parents[1] / "application-tests" / "linux_diagnostic_container_owner.py"
spec = importlib.util.spec_from_file_location("owner", SOURCE)
owner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(owner)


class Result:
    def __init__(self, code=0, out="", err=""):
        self.returncode, self.stdout, self.stderr = code, out, err


class Fake:
    def __init__(self, states=None):
        self.calls = []
        self.states = iter(states or [])

    def call(self, argv, **kwargs):
        self.calls.append(argv)
        if argv[0] == "create":
            return Result(out="container-id\n")
        if argv[0] == "ps":
            return Result(out="" if any(call[0] == "rm" for call in self.calls) else "container-id\n")
        if argv[0] == "inspect":
            return Result(out=json.dumps({"Status":"exited", "Running":False, "Paused":False,
                "Restarting":False, "OOMKilled":False, "Dead":False, "Error":"", "ExitCode":0}))
        return Result()


class OwnerTests(unittest.TestCase):
    def manifest(self):
        return {"complete": True, "files": [{"canonical_path":"/lib64/ld-linux-x86-64.so.2", "sha256":"a"*64}]}

    def test_rejects_incomplete_closure_before_create(self):
        with tempfile.TemporaryDirectory() as directory:
            fake = Fake(); runner = owner.DiagnosticOwner(directory, backend=fake, nonce="n")
            with self.assertRaises(owner.OwnerError): runner.run(closure_manifest={"complete":False})
            self.assertEqual(fake.calls, [])

    def test_fake_backend_enforces_owner_and_reports_statuses(self):
        with tempfile.TemporaryDirectory() as directory:
            fake = Fake(); result = owner.DiagnosticOwner(directory, backend=fake, nonce="n").run(closure_manifest=self.manifest())
            self.assertEqual(result["collector"], "PASS")
            self.assertEqual(result["supervisor"], "COMPLETED")
            self.assertTrue(any(call[0:2] == ["start", "--attach"] for call in fake.calls))

    def test_create_argv_has_no_shell_or_network(self):
        with tempfile.TemporaryDirectory() as directory:
            argv = owner.DiagnosticOwner(directory, nonce="n")._create_argv()
            self.assertIn("--network=none", argv)
            self.assertNotIn("sh", argv)
            self.assertEqual(argv[0], "create")


if __name__ == "__main__":
    unittest.main()
