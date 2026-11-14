"""Compile and execute the actual collector close_except implementation."""
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).parent / "fixtures/application-collector-v1/linux-sealed-v1"


class CloseExceptContractTests(unittest.TestCase):
    def test_actual_c_fallback_matrix(self):
        with tempfile.TemporaryDirectory() as directory:
            binary = Path(directory) / "close-except"
            compiled = subprocess.run([
                "gcc", "-std=c11", "-O2", "-Wall", "-Wextra", "-Werror",
                "-ffunction-sections", "-fdata-sections", str(ROOT / "close_except_harness.c"),
                "-Wl,--gc-sections", "-o", str(binary),
            ], capture_output=True, timeout=30)
            self.assertEqual(compiled.returncode, 0, compiled.stderr.decode(errors="replace"))
            run = subprocess.run([str(binary)], capture_output=True, timeout=10)
            self.assertEqual(run.returncode, 0, run.stderr.decode(errors="replace"))
            self.assertEqual(run.stdout, b"PASS close-except\n")
            self.assertEqual(run.stderr, b"")


if __name__ == '__main__':
    unittest.main()
