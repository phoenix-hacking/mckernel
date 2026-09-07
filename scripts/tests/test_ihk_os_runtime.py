"""Execute the complete native OS adapter with fault-injectable Linux mocks."""

import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]


class NativeOsRuntimeTests(unittest.TestCase):
    def test_complete_adapter_ownership_failure_and_race_cases(self):
        rustc = os.environ.get("MCKERNEL_RUSTC_1_92") or os.environ.get("RUSTC") or shutil.which("rustc")
        if not rustc:
            self.skipTest("rustc is unavailable for native OS adapter execution")
        template = (ROOT / "scripts/tests/fixtures/ihk_os_runtime_compile.rs").read_text()
        modules = []
        for name in ("abi", "device_registry", "os_registry", "ihk_ioctl", "os_runtime"):
            relative = "abi/x86_64.rs" if name == "abi" else name + ".rs"
            path = ROOT / "host-kernel/native-rust" / relative
            # Match the production crate's data-only ABI-module visibility lint.
            attributes = '#[allow(unreachable_pub)]\n' if name == 'abi' else ''
            modules.append(attributes + '#[path = "' + str(path) + '"]\nmod ' + name + ';')
        self.assertEqual(1, template.count("// SOURCE_MODULES"))
        with tempfile.TemporaryDirectory(prefix="ihk-os-runtime-") as temporary:
            directory = Path(temporary)
            fixture = directory / "fixture.rs"
            fixture.write_text(template.replace("// SOURCE_MODULES", "\n".join(modules)))
            binary = directory / "tests"
            environment = dict(os.environ, RUSTC_BOOTSTRAP="1")
            result = subprocess.run(
                [rustc, "--edition=2021", "--test", "--cfg", "CONFIG_COMPAT", "-Dwarnings", "-Dunreachable-pub",
                 str(fixture), "-o", str(binary)],
                env=environment, capture_output=True, text=True, timeout=90,
            )
            self.assertEqual(0, result.returncode, result.stdout + result.stderr)
            result = subprocess.run([str(binary), "--test-threads=1"],
                                    capture_output=True, text=True, timeout=90)
            self.assertEqual(0, result.returncode, result.stdout + result.stderr)
            self.assertIn("47 passed; 0 failed", result.stdout)


if __name__ == "__main__":
    unittest.main()
