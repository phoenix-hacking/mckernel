"""Static/cheap contract checks for the bounded native shutdown fixture.

No device, module, root privilege, guest, or production build is involved.
"""
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "scripts/tests/fixtures/native-shutdown.c"


class NativeShutdownFixtureTests(unittest.TestCase):
    def test_freestanding_x86_64_fixture_compiles(self):
        cc = shutil.which("cc")
        if cc is None:
            self.skipTest("C compiler unavailable")
        with tempfile.TemporaryDirectory(prefix="native-shutdown-fixture-") as directory:
            result = subprocess.run(
                [cc, "-std=gnu11", "-O2", "-ffreestanding", "-fno-stack-protector",
                 "-fno-pie", "-no-pie", "-DCPUHP_FAILURE_STATE=0", "-c", str(FIXTURE),
                 "-o", str(Path(directory) / "native-shutdown.o")],
                capture_output=True, text=True, timeout=15)
            self.assertEqual(0, result.returncode, result.stdout + result.stderr)

    def test_shutdown_contract_is_ordered_and_fail_closed(self):
        text = FIXTURE.read_text()
        for token in ("/dev/mcos0", "IHK_OS_SHUTDOWN", "/dev/mcd0", "OS_DESTROY",
                      "cpus[0] == 1", "request(control, RELEASE", "query_memory(control)",
                      "release_memory(control)",
                      "NATIVE_SHUTDOWN x86_64 os0-shutdown-destroy-release-empty PASS"):
            self.assertIn(token, text)
        shutdown_body = text[text.index("static void shutdown_os_zero"):
                             text.index("int main(void)")]
        shutdown_call = "require(call(SYS_IOCTL, os, IHK_OS_SHUTDOWN, 0) == 0);"
        destroy_call = "require(call(SYS_IOCTL, control, OS_DESTROY, 0) == 0);"
        self.assertIn("int os = call(SYS_OPEN, (long)\"/dev/mcos0\", 2, 0);", shutdown_body)
        self.assertIn(shutdown_call, shutdown_body)
        self.assertIn("close_fd(os);", shutdown_body)
        self.assertIn(destroy_call, shutdown_body)
        self.assertLess(shutdown_body.index(shutdown_call), shutdown_body.index("close_fd(os);"))
        self.assertLess(shutdown_body.index("close_fd(os);"), shutdown_body.index(destroy_call))
        main_body = text[text.index("int main(void)"):]
        cpu = "query_returned_cpu_and_release(control);"
        memory = "require(query_memory(control) > 0);"
        release = "release_memory(control);"
        marker = "NATIVE_SHUTDOWN \" ARCH_LABEL \" os0-shutdown-destroy-release-empty PASS"
        self.assertLess(main_body.index(cpu), main_body.index(memory))
        self.assertLess(main_body.index(memory), main_body.index(release))
        self.assertLess(main_body.index(release), main_body.index(marker))
        self.assertNotIn("SYS_DELETE_MODULE", text)
        self.assertNotIn("ihk_smp_x86_64", text)


if __name__ == "__main__":
    unittest.main()
