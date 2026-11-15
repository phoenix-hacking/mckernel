"""Bounded mailbox submission retries; no manager, network or engine effects."""
from contextlib import redirect_stdout
import io
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import os_goal_guard_protocol as protocol
import os_goal_readiness as readiness
import os_goal_service as service
import run_os_goal as launcher
import watch_os_goal


class StartupTests(unittest.TestCase):
    def setUp(self):
        self.clock = [100.0]
        self.ready = {"monitoring_mode": "independent", "stages": {
            "monitor": {"ready": True, "missing": []}, "mailbox": {"ready": True, "missing": []}}}
        self.not_ready = {"monitoring_mode": "independent", "stages": {
            "monitor": {"ready": False, "missing": ["Monitor unavailable"]},
            "mailbox": {"ready": False, "missing": ["No current poll"]}}}
        self.timer = patch.object(launcher.time, "monotonic", side_effect=lambda: self.clock[0])
        self.timer.start()
        self.addCleanup(self.timer.stop)
        self.sleep = patch.object(launcher.time, "sleep", side_effect=lambda delay: self.clock.__setitem__(0, self.clock[0] + delay))
        self.sleep.start()
        self.addCleanup(self.sleep.stop)

    def test_verified_pre_submission_busy_retries_then_accepts_current_reader(self):
        with patch.object(service, "start_mailbox", side_effect=[
                protocol.EngineLaunchDeferred("launch lock publishing"),
                {"status": "MAILBOX_START_REQUESTED"}]) as start, \
                patch.object(readiness, "evaluate_readiness", return_value=self.ready):
            self.assertEqual(launcher.ensure_mailbox_ready("repo", "runtime", timeout_seconds=1), self.ready)
        self.assertEqual(start.call_count, 2)

    def test_busy_submission_and_poll_wait_share_one_original_deadline(self):
        def start(*args):
            if self.clock[0] < 100.25:
                raise protocol.EngineLaunchDeferred("original launcher publishing")
            return {"status": "MAILBOX_START_REQUESTED"}
        with patch.object(service, "start_mailbox", side_effect=start), \
                patch.object(readiness, "evaluate_readiness", return_value=self.not_ready), \
                self.assertRaisesRegex(RuntimeError, "not verified ready"):
            launcher.ensure_mailbox_ready("repo", "runtime", timeout_seconds=.5)
        self.assertAlmostEqual(self.clock[0], 100.5)

    def test_continuous_busy_is_finite_and_never_reads_an_unsubmitted_reader(self):
        with patch.object(service, "start_mailbox", side_effect=protocol.EngineLaunchDeferred("busy")), \
                patch.object(readiness, "evaluate_readiness") as observe, \
                self.assertRaisesRegex(RuntimeError, "another service submission"):
            launcher.ensure_mailbox_ready("repo", "runtime", timeout_seconds=.25)
        self.assertAlmostEqual(self.clock[0], 100.25)
        observe.assert_not_called()

    def test_ambiguous_service_failure_is_not_retried(self):
        with patch.object(service, "start_mailbox", side_effect=RuntimeError("systemctl outcome uncertain")) as start, \
                patch.object(readiness, "evaluate_readiness") as observe, \
                self.assertRaisesRegex(RuntimeError, "outcome uncertain"):
            launcher.ensure_mailbox_ready("repo", "runtime", timeout_seconds=1)
        self.assertEqual(start.call_count, 1)
        observe.assert_not_called()

    def test_zero_timeout_still_submits_once_and_checks_once(self):
        with patch.object(service, "start_mailbox", return_value={"status": "MAILBOX_START_REQUESTED"}) as start, \
                patch.object(readiness, "evaluate_readiness", return_value=self.not_ready) as observe, \
                self.assertRaisesRegex(RuntimeError, "not verified ready"):
            launcher.ensure_mailbox_ready("repo", "runtime", timeout_seconds=0)
        self.assertEqual(start.call_count, 1)
        self.assertEqual(observe.call_count, 1)

    def test_optional_mailbox_failure_does_not_block_local_work_but_required_does(self):
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            (repo / "scripts").mkdir()
            (repo / "scripts/os_goal_mailbox.json").write_text("{}")
            for mode in ("auto", "required"):
                with self.subTest(mode=mode), patch.object(launcher, "REPO", repo), \
                        patch.object(launcher.subprocess, "check_output", return_value=".git"), \
                        patch.object(launcher.shutil, "which", return_value="codex"), \
                        patch.object(launcher, "launch_resources", return_value={}), \
                        patch.object(launcher, "check_resources"), \
                        patch.object(launcher, "ensure_mailbox_ready", side_effect=RuntimeError("observer unavailable")) as monitor, \
                        patch.object(watch_os_goal, "supervise", return_value=0) as launch, \
                        redirect_stdout(io.StringIO()):
                    if mode == "required":
                        with self.assertRaisesRegex(RuntimeError, "observer unavailable"):
                            launcher.main(["--supervisor", "--mailbox-monitor", mode])
                        launch.assert_not_called()
                    else:
                        self.assertEqual(launcher.main(["--supervisor", "--mailbox-monitor", mode]), 0)
                        launch.assert_called_once()
                    monitor.assert_called_once()


if __name__ == "__main__":
    unittest.main()
