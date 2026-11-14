"""HOST-only executor descriptor lifetime fixture, intended for hosted CI.

Functional McKernel OS/apps/Rust only; no security testing. Compile the verbatim
selected act_execve_phase2 body and real request/transfer declarations against
allocator/provider doubles. No production executor, device, container or native
program runs; the existing 78-word ABI qualification is reused, not repeated.
"""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from scripts.tests.test_m15_executor_libdir import ROOT, item


class ExecveDescriptorCleanupTests(unittest.TestCase):
    def test_all_phase2_returns_release_only_the_copied_descriptor(self):
        compiler = os.environ.get("RUSTC") or shutil.which("rustc")
        self.assertIsNotNone(compiler, "Bind the hosted Rust compiler; this lifetime check must not silently skip")
        source = (ROOT / "executer/user/rust/mcexec_helpers.rs").read_text()
        declarations = ["#[repr(C)]\n" + item(source, signature) for signature in (
            "struct RemoteTransfer {", "pub struct McexecSyscallRequest {", "pub struct McexecSyscallWaitDesc {")]
        constants = [next(line for line in source.splitlines() if line.startswith("const " + name + ":"))
                     for name in ("MCEXEC_UP_TRANSFER", "MCEXEC_UP_TRANSFER_FROM_REMOTE", "MCEXEC_UP_CLOSE_EXEC")]
        actual = "\n".join(constants + declarations + [
            item(source, "unsafe fn zero_bytes("),
            '#[no_mangle]\n' + item(source, 'pub unsafe extern "C" fn act_execve_phase2('),
        ])
        template = (Path(__file__).parent / "fixtures/m15_f02_execve_descriptor_cleanup.rs").read_text()
        # The placeholder occurs once outside the explanatory comment.
        self.assertEqual(template.count("\n@ACTUAL_ITEMS@\n"), 1)
        with tempfile.TemporaryDirectory(prefix="m15-f02-descriptor-cleanup-") as temporary:
            directory = Path(temporary)
            fixture, binary = directory / "fixture.rs", directory / "fixture"
            fixture.write_text(template.replace("\n@ACTUAL_ITEMS@\n", "\n" + actual + "\n"))
            result = subprocess.run([compiler, "--edition=2021", "--test", "-C", "opt-level=1",
                                     str(fixture), "-o", str(binary)], capture_output=True, text=True, timeout=90)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            result = subprocess.run([str(binary), "--test-threads=1"], capture_output=True, text=True, timeout=45)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("6 passed; 0 failed", result.stdout)


if __name__ == "__main__":
    unittest.main()
