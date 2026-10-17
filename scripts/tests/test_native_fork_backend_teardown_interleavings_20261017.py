"""Only three new deterministic teardown interleavings of accepted actual bodies."""
from pathlib import Path
import json
import os
import subprocess
import tempfile
import unittest
from scripts.tests.test_native_fork_backend_reservation_20261017 import (
    ROOT, RUSTC, generated_source as accepted_source,
)

FIXTURE = ROOT / "scripts/tests/fixtures/native_fork_backend_teardown_interleavings_20261017.rs"


def generated_source():
    return accepted_source() + "\n" + FIXTURE.read_text()


class NativeForkBackendTeardownInterleavingTests(unittest.TestCase):
    def test_source_reuses_frozen_actual_bodies(self):
        original = accepted_source()
        source = generated_source()
        self.assertTrue(source.startswith(original + "\n"))
        self.assertEqual(FIXTURE.read_text().count("#[test]"), 3)
        self.assertEqual(source.count("fn teardown_interleaving_"), 3)

    def test_only_new_actual_interleavings(self):
        compiler = Path(str(RUSTC))
        self.assertTrue(compiler.is_file(), "pinned Rust 1.92 required")
        attempt = Path(tempfile.mkdtemp(prefix="native-fork-backend-teardown-20261017-"))
        print("fork_backend_teardown_evidence=" + str(attempt), flush=True)
        source, binary = attempt / "generated.rs", attempt / "test"
        source.write_text(generated_source())

        def captured(label, command, timeout):
            (attempt / (label + ".command.json")).write_text(json.dumps(command) + "\n")
            try:
                result = subprocess.run(command, capture_output=True, timeout=timeout,
                                        env={**os.environ, "RUST_TEST_THREADS": "1"})
            except subprocess.TimeoutExpired as error:
                (attempt / (label + ".stdout")).write_bytes(error.stdout or b"")
                (attempt / (label + ".stderr")).write_bytes(error.stderr or b"")
                (attempt / (label + ".status.json")).write_text(json.dumps({"timeout_seconds": timeout, "returncode": None}) + "\n")
                raise
            (attempt / (label + ".stdout")).write_bytes(result.stdout)
            (attempt / (label + ".stderr")).write_bytes(result.stderr)
            (attempt / (label + ".status.json")).write_text(json.dumps({"returncode": result.returncode}) + "\n")
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            return result

        version = captured("version", [str(compiler), "--version"], 15)
        self.assertTrue(version.stdout.startswith(b"rustc 1.92.0 "), version.stdout)
        captured("compile", [str(compiler), "--edition=2021", "--test", str(source), "-o", str(binary)], 60)
        result = captured("run", [str(binary), "--test-threads=1", "teardown_interleaving_"], 30)
        self.assertIn(b"3 passed; 0 failed", result.stdout)
        self.assertIn(b"5 filtered out", result.stdout)


if __name__ == "__main__":
    unittest.main()
