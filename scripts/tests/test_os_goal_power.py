#!/usr/bin/env python3
"""Power helpers use fake commands only; no host linger or inhibitors are changed."""
from types import SimpleNamespace
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import os_goal_power as power


class PowerReadinessTests(unittest.TestCase):
    def setUp(self):
        self.which = patch.object(power.shutil, "which", side_effect=lambda name: "/fake/" + name)
        self.uid = patch.object(power.os, "getuid", return_value=1000)
        self.run = patch.object(power.subprocess, "run")
        self.which.start()
        self.uid_mock = self.uid.start()
        self.command = self.run.start()
        self.addCleanup(self.which.stop)
        self.addCleanup(self.uid.stop)
        self.addCleanup(self.run.stop)

    @staticmethod
    def result(stdout="", code=0, stderr=""):
        return SimpleNamespace(stdout=stdout, stderr=stderr, returncode=code)

    def assert_command_bounds(self):
        for call in self.command.call_args_list:
            self.assertIsInstance(call.args[0], list)
            self.assertTrue(Path(call.args[0][0]).is_absolute())
            self.assertEqual(call.kwargs["stdin"], subprocess.DEVNULL)
            self.assertIs(call.kwargs["shell"], False)
            self.assertEqual(call.kwargs["timeout"], 10)
            self.assertTrue(call.kwargs["capture_output"])
            self.assertFalse(call.kwargs["check"])
            self.assertNotIn("sudo", call.args[0])

    def test_check_linger_reads_only_the_current_numeric_user(self):
        for value, expected in (("yes\n", True), ("no\n", False)):
            with self.subTest(value=value):
                self.command.return_value = self.result(value)
                self.assertEqual(power.check_linger(), {"enabled": expected, "uid": 1000})
                self.assertEqual(self.command.call_args.args[0], ["/fake/loginctl", "--no-ask-password",
                    "show-user", "1000", "--property=Linger", "--value"])
        self.assert_command_bounds()

    def test_enabled_linger_is_idempotent_and_never_calls_enable(self):
        self.command.return_value = self.result("yes\n")
        self.assertEqual(power.ensure_linger(), {"enabled": True, "uid": 1000, "changed": False})
        self.assertEqual(self.command.call_count, 1)
        self.assertNotIn("enable-linger", self.command.call_args.args[0])

    def test_disabled_linger_enables_current_uid_once_then_rereads(self):
        self.command.side_effect = [self.result("no\n"), self.result(), self.result("yes\n")]
        self.assertEqual(power.ensure_linger(), {"enabled": True, "uid": 1000, "changed": True})
        calls = [c.args[0] for c in self.command.call_args_list]
        self.assertEqual(calls[1], ["/fake/loginctl", "--no-ask-password", "enable-linger", "1000"])
        self.assertEqual(calls[0], calls[2])
        self.assert_command_bounds()

    def test_failed_enable_or_negative_readback_never_claims_enabled(self):
        for responses in ([self.result("no"), self.result(code=1)],
                          [self.result("no"), self.result(), self.result("no")],
                          [self.result("no"), self.result(), self.result("unknown")]):
            with self.subTest(responses=responses):
                self.command.reset_mock()
                self.command.side_effect = responses
                with self.assertRaises(RuntimeError):
                    power.ensure_linger()
                self.assertLessEqual(self.command.call_count, 3)
                self.assertEqual(sum("enable-linger" in c.args[0] for c in self.command.call_args_list), 1)

    def test_unknown_reading_cannot_trigger_enable(self):
        for output in ("", "true", "Linger=yes", "unknown", "yes\nno"):
            with self.subTest(output=output):
                self.command.reset_mock()
                self.command.return_value = self.result(output)
                with self.assertRaises(RuntimeError):
                    power.ensure_linger()
                self.assertEqual(self.command.call_count, 1)

    def test_user_identity_change_during_enable_is_not_success(self):
        self.uid_mock.side_effect = [1000, 1001]
        self.command.side_effect = [self.result("no"), self.result(), self.result("yes")]
        with self.assertRaisesRegex(RuntimeError, "not verified"):
            power.ensure_linger()
        self.assertEqual(self.command.call_args_list[1].args[0][-1], "1000")

    def test_probe_takes_only_scoped_lock_and_runs_short_literal_python(self):
        self.command.return_value = self.result()
        with patch.object(power.sys, "executable", "/fake/python"):
            result = power.probe_inhibition()
        self.assertEqual(result, {"verified": True, "what": "idle:sleep:handle-lid-switch",
                                  "mode": "block", "persistent": False})
        command = self.command.call_args.args[0]
        self.assertEqual(command[0], "/fake/systemd-inhibit")
        self.assertEqual(command[1:3], ["--what=idle:sleep:handle-lid-switch", "--mode=block"])
        self.assertNotIn("--no-ask-password", command)
        self.assertEqual(command[command.index("--") + 1:], ["/fake/python", "-B", "-c", "pass"])
        self.assertNotIn("shutdown", command[1])
        self.assertEqual(self.command.call_count, 1)
        self.assert_command_bounds()

    def test_probe_failure_timeout_and_cli_output_cannot_claim_verified_or_expose_secrets(self):
        for failure in (self.result(code=1, stdout="token=secret", stderr="password=hidden"),
                        subprocess.TimeoutExpired(["systemd-inhibit"], 10), OSError("secret credential detail")):
            with self.subTest(failure=type(failure).__name__):
                self.command.reset_mock()
                self.command.side_effect = failure if isinstance(failure, BaseException) else None
                self.command.return_value = failure
                with self.assertRaises(RuntimeError) as error:
                    power.probe_inhibition()
                self.assertNotIn("secret", str(error.exception))
                self.assertNotIn("hidden", str(error.exception))
                self.assertEqual(self.command.call_count, 1)

    def test_missing_or_relative_supported_binary_has_no_fallback(self):
        for binary in (None, "relative/loginctl"):
            with self.subTest(binary=binary), patch.object(power.shutil, "which", return_value=binary):
                with self.assertRaisesRegex(RuntimeError, "no fallback"):
                    power.check_linger()
                with self.assertRaisesRegex(RuntimeError, "no fallback"):
                    power.probe_inhibition()
        self.command.assert_not_called()


if __name__ == "__main__":
    unittest.main()
