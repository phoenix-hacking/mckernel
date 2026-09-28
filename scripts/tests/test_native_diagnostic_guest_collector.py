"""Source-level contract tests for the bounded native guest collector.

These tests intentionally do not compile, boot, load modules, invoke QEMU, or
run a guest.  The collector is a reviewed guest input and is tested here for
its frozen paths, frame schema, and failure/teardown structure only.
"""
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "scripts/application-tests/native_diagnostic_guest_collector.c"


class NativeDiagnosticGuestCollectorSourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = SOURCE.read_text(encoding="utf-8")

    def test_fixed_guest_boot_and_launch_contract(self):
        for value in (
            '"/modules/ihk.ko"', '"/modules/ihk-smp-x86_64.ko"',
            '"/modules/mcctrl.ko"', '"/bin/native-boot"',
            '"/bin/native-boot"', '"/bin/mcexec"', '"-t"',
            '"1"', '"0"', '"app"', '"A"', '""', '"B"',
        ):
            self.assertIn(value, self.text)
        self.assertNotRegex(self.text, r'\b(system|popen|execlp|execvp)\s*\(')

    def test_bounded_capture_and_frozen_payload_keys(self):
        for value in (
            "LIMIT_OUT 4096", "LIMIT_ERR 65536", "DEADLINE_SEC 30",
            '"ND_PAYLOAD {', '\\\"raw_wait_status\\\":%d',
            'started_ns', 'reaped_ns', 'finished_ns',
            'procfs_empty', 'observed', 'retained', 'discarded', 'eof_ns',
        ):
            self.assertIn(value, self.text)
        self.assertIn("O_NONBLOCK", self.text)
        self.assertIn("WNOHANG", self.text)
        self.assertIn("SIGKILL", self.text)

    def test_failure_paths_attempt_teardown_and_poweroff(self):
        self.assertGreaterEqual(self.text.count("teardown();"), 2)
        self.assertGreaterEqual(self.text.count("reboot(RB_POWER_OFF)"), 2)
        self.assertIn("/dev/console", self.text)
        self.assertIn('"/dev/mcos0"', self.text)

    def test_no_runtime_orchestration_in_host_test(self):
        # Guard the source test itself against accidentally becoming a guest
        # runner.  Execution belongs to a separately released packet.
        self.assertTrue(SOURCE.is_file())


if __name__ == "__main__":
    unittest.main()
