"""Functional manual-launch defaults; no model, service or runtime work."""
import fcntl
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import launch_m14_m15 as launch
from os_goal_writer import SAVED_ROOT
import run_os_goal


class LaunchTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name)
        self.codex_home = self.directory / "codex"
        self.saved = {"thread_id": SAVED_ROOT, "repo": str(launch.REPO.resolve()),
                      "goal": {"threadId": SAVED_ROOT, "objective": run_os_goal.OBJECTIVE,
                               "status": "paused"}}
        (self.directory / "state.json").write_text(json.dumps(self.saved))
        runtime = patch.object(launch, "runtime_directory", return_value=self.directory)
        environment = patch.dict(os.environ, {"CODEX_HOME": str(self.codex_home)})
        runtime.start()
        environment.start()
        self.addCleanup(runtime.stop)
        self.addCleanup(environment.stop)

    def test_command_preserves_same_cumulative_budget_and_pins_max_dispatch(self):
        command = launch.controller_command(launch.arguments([]))
        parsed = run_os_goal.arguments(command[3:])
        self.assertEqual((parsed.model, parsed.effort, parsed.max_agents), ("gpt-6.1-sol", "max", 11))
        self.assertEqual(parsed.credit_run_id, "7c6ef3604bfb4008a917bba8cfb6cfaa")
        self.assertEqual(str(parsed.credit_budget), "52079.8011050000")
        self.assertTrue(parsed.stop_after_m14_m15)
        self.assertFalse(parsed.fresh_session)
        self.assertFalse(parsed.recovered)
        self.assertEqual(parsed.work_memory_gib, 28)
        self.assertIsNone(parsed.memory_gib)
        self.assertEqual(parsed.build_jobs, 5)

    def test_selected_resources_reach_existing_parser(self):
        command = launch.controller_command(launch.arguments([
            "--agents", "12", "--jobs", "4", "--memory-gib", "6", "--cpus", "0,1,6,7"]))
        parsed = run_os_goal.arguments(command[3:])
        self.assertEqual((parsed.max_agents, parsed.build_jobs, parsed.memory_gib, parsed.host_cpus),
                         (12, 4, 6, [0, 1, 6, 7]))

    def test_check_never_submits_background_work(self):
        with patch("os_goal_power.probe_inhibition"), patch.object(launch.subprocess, "run") as run, \
                patch.object(launch.subprocess, "Popen") as spawn:
            run.return_value.returncode = 0
            self.assertEqual(launch.main(["--check"]), 0)
            self.assertIn("--check", run.call_args[0][0])
            spawn.assert_not_called()

    def test_closing_log_view_preserves_detached_run(self):
        child = Mock(pid=123456)
        with patch.object(launch.shutil, "which", side_effect=lambda name: "/usr/bin/" + name), \
                patch.object(launch.subprocess, "run", side_effect=[Mock(returncode=0), KeyboardInterrupt]), \
                patch.object(launch.subprocess, "Popen", return_value=child) as spawn:
            self.assertEqual(launch.main([]), 0)
            self.assertTrue(spawn.call_args.kwargs["start_new_session"])
            self.assertIn("/usr/bin/taskset", spawn.call_args.args[0])
            child.terminate.assert_not_called()
            child.kill.assert_not_called()
            child.send_signal.assert_not_called()
            child.wait.assert_not_called()

    def test_held_saved_writer_blocks_check_and_background_submission(self):
        lock = self.codex_home / "thread-writer-locks" / (SAVED_ROOT + ".lock")
        lock.parent.mkdir(parents=True)
        lock.write_text("existing owner")
        with lock.open("r") as owner:
            fcntl.flock(owner.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            for argv in (["--check"], []):
                with self.subTest(argv=argv), patch("os_goal_power.probe_inhibition") as inhibit, \
                        patch.object(launch.subprocess, "run") as run, \
                        patch.object(launch.subprocess, "Popen") as spawn:
                    with self.assertRaisesRegex(RuntimeError, "already has an active writer"):
                        launch.main(argv)
                    inhibit.assert_not_called()
                    run.assert_not_called()
                    spawn.assert_not_called()
        self.assertFalse((self.directory / "manual-launches").exists())

    def test_missing_or_foreign_campaign_never_reaches_controller(self):
        path = self.directory / "state.json"
        for saved in (None, dict(self.saved, thread_id="another-root"),
                      dict(self.saved, repo="/another/checkout"),
                      dict(self.saved, goal={"objective": "another objective"}),
                      dict(self.saved, goal=dict(self.saved["goal"], threadId="another-root"))):
            if saved is None:
                path.unlink(missing_ok=True)
            else:
                path.write_text(json.dumps(saved))
            for argv in (["--check"], []):
                with self.subTest(saved=saved, argv=argv), \
                        patch.object(launch.subprocess, "run") as run, \
                        patch.object(launch.subprocess, "Popen") as spawn:
                    with self.assertRaisesRegex(RuntimeError, "Saved.*campaign"):
                        launch.main(argv)
                    run.assert_not_called()
                    spawn.assert_not_called()


if __name__ == "__main__":
    unittest.main()
