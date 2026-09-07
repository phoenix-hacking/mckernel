"""Exercise image preflight with the existing ownership and mapping cores."""
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


class NativeSmpImageTests(unittest.TestCase):
    def test_image_and_reused_resource_mapping_policies(self):
        self.compile_and_run("ihk_smp_image_compile.rs")

    def test_bounded_linux_file_owner(self):
        self.compile_and_run("ihk_smp_loader_compile.rs")

    def test_startup_page_tables_match_independent_address_translation(self):
        self.compile_and_run("ihk_smp_startup_compile.rs")

    def compile_and_run(self, fixture):
        rustc = shutil.which("rustc")
        if rustc is None:
            self.skipTest("Rust compiler unavailable")
        with tempfile.TemporaryDirectory(prefix="native-smp-image-") as temporary:
            binary = Path(temporary) / "image-tests"
            result = subprocess.run([rustc, "--edition=2021", "--test", "-Dwarnings",
                            str(ROOT / "scripts/tests/fixtures" / fixture),
                            "-o", str(binary)], capture_output=True, text=True)
            self.assertEqual(0, result.returncode, result.stdout + result.stderr)
            result = subprocess.run([str(binary), "--test-threads=1"],
                                    capture_output=True, text=True)
            self.assertEqual(0, result.returncode, result.stdout + result.stderr)
            self.assertIn("test result: ok.", result.stdout)


if __name__ == "__main__":
    unittest.main()
