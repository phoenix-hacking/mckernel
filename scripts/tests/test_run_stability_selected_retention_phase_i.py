import os
import tempfile
import unittest
from pathlib import Path
import importlib.util
import hashlib

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("driver", HERE / "run_stability_selected_retention_phase_i.py")
driver = importlib.util.module_from_spec(spec); spec.loader.exec_module(driver)

class DriverTests(unittest.TestCase):
    def roots(self):
        t = tempfile.TemporaryDirectory(); base = Path(t.name)
        return t, base / "candidate", base / "diagnostics"

    def reviewed(self, c, command, data=b"ok\n"):
        return {"command_argv": command,
                "expected_membership": {"result.txt": {"size": len(data), "sha256": hashlib.sha256(data).hexdigest()}},
                "archive_mapping": {"result.txt": "fixture"}}

    def test_exit_zero_records_literal_argv_and_streams(self):
        t, c, d = self.roots()
        with t:
            command = ["python3", "-c", f"from pathlib import Path; Path({str(c)!r}, 'result.txt').write_bytes(b'ok\\n')"]
            result = driver.run_phase_i(c, d, command, reviewed=self.reviewed(c, command))
            self.assertEqual(result["returncode"], 0)
            self.assertIn('"argv":["python3","-c"', (d / "authentication.json").read_text())
            self.assertTrue((d / "controls.json").exists())

    def test_nonzero_preserves_six_field_failure(self):
        t, c, d = self.roots()
        with t:
            command = ["python3", "-c", f"from pathlib import Path; Path({str(c)!r}, 'result.txt').write_bytes(b'ok\\n'); raise SystemExit(7)"]
            with self.assertRaises(RuntimeError): driver.run_phase_i(c, d, command, reviewed=self.reviewed(c, command))
            self.assertEqual(len((c / "phase-i-failure.txt").read_text().splitlines()), 6)

    def test_symlink_alias_rejected(self):
        t, c, d = self.roots()
        with t:
            c.parent.mkdir(exist_ok=True); real = c.parent / "real"; real.mkdir(); c.symlink_to(real, target_is_directory=True)
            with self.assertRaises(ValueError): driver.run_phase_i(c, d, ["true"])

    def test_control_payloads_and_strict_names(self):
        self.assertEqual(len(driver.CONTROL_CASES), 5)
        self.assertNotIn("validation.stdout", driver.DIAGNOSTIC_NAMES)

if __name__ == "__main__": unittest.main()
