"""Check the retained guest producer with both explicit control-kernel ABIs."""
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


class McKernelIrqWorkTests(unittest.TestCase):
    def test_legacy_and_native_producers(self):
        rustc = shutil.which("rustc")
        if rustc is None:
            self.skipTest("Rust compiler unavailable")
        with tempfile.TemporaryDirectory(prefix="mckernel-irq-work-") as temporary:
            for native in (False, True):
                binary = Path(temporary) / ("native" if native else "legacy")
                command = [rustc, "--edition=2021", "-Dwarnings", "-Aunused-imports",
                           str(ROOT / "scripts/tests/fixtures/mckernel_irq_work_compile.rs"),
                           "-o", str(binary)]
                if native:
                    command += ["--cfg", "native_linux_irq_work_v6_12"]
                result = subprocess.run(command, capture_output=True, text=True, timeout=120)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                result = subprocess.run([str(binary)], capture_output=True, text=True, timeout=30)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertIn("callbacks=1027", result.stdout)
                if native:
                    result = subprocess.run([str(binary), "concurrent"], capture_output=True,
                                            text=True, timeout=30)
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                    self.assertIn("one-allocation callbacks=8192", result.stdout)


if __name__ == "__main__":
    unittest.main()
