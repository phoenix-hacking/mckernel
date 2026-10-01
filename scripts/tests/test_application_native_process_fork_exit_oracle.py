import importlib.util
from pathlib import Path
import unittest

MODULE = Path(__file__).resolve().parents[1] / "application-tests/native_process_fork_exit_oracle.py"
spec = importlib.util.spec_from_file_location("fork_oracle", MODULE)
oracle = importlib.util.module_from_spec(spec)
spec.loader.exec_module(oracle)


class ForkExitOracleTest(unittest.TestCase):
    def result(self):
        return {"case_id": oracle.CASE_ID, "status": "PROTOCOL_PASS",
                "application_acceptance": False, "exit_code": 0, "stderr": b"",
                "stdout": oracle.EXPECTED_STDOUT, "source_sha256": oracle.SOURCE_SHA256,
                "oracle_sha256": oracle.ORACLE_SHA256, "payload_sha256": "p" * 64}

    def test_exact_relation_and_identity(self):
        self.assertEqual(oracle.validate(self.result(), payload_sha256="p" * 64)["case_id"], oracle.CASE_ID)

    def test_rejects_wrong_pid_relation(self):
        row = self.result(); row["stdout"] = b"child_pid_positive=0 reaped_match=1 exited=1 code=23\n"
        with self.assertRaises(ValueError): oracle.validate(row, payload_sha256="p" * 64)

    def test_rejects_wrong_exit_or_stderr_or_acceptance(self):
        for key, value in (("exit_code", 23), ("stderr", b"noise"), ("application_acceptance", True)):
            row = self.result(); row[key] = value
            with self.assertRaises(ValueError): oracle.validate(row, payload_sha256="p" * 64)

    def test_rejects_identity_drift(self):
        for key in ("source_sha256", "oracle_sha256", "payload_sha256"):
            row = self.result(); row[key] = "0" * 64
            with self.assertRaises(ValueError): oracle.validate(row, payload_sha256="p" * 64)


if __name__ == "__main__":
    unittest.main()
