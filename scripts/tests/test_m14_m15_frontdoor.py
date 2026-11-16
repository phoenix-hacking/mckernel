"""Functional CLI checks; no model, account, process-control or native effects."""
import contextlib
import io
from pathlib import Path
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import m14_m15 as cli


class FrontdoorTests(unittest.TestCase):
    def state(self, **changes):
        value = {"thread_id": cli.ROOT, "worker_start": "100", "server_start": "200",
                 "phase": "owner_retained", "active_turns": {}, "simple_m14_m15": False}
        value.update(changes)
        return value

    def owner(self):
        return {"worker_birth_observation": "100", "server_birth_observation": "200"}

    def test_no_replacement_for_missing_or_changed_owner(self):
        for state, owner in (({}, self.owner()),
                             (self.state(), dict(self.owner(), server_birth_observation="changed"))):
            with self.subTest(state=state), patch.object(cli, "read_state", return_value=state), \
                    patch.object(cli, "control_status", return_value=owner), \
                    patch("run_os_goal.queue_same_owner_resume") as resume:
                with self.assertRaises(ValueError):
                    cli.start_existing(Path("/repo"))
                resume.assert_not_called()

    def test_existing_work_is_neither_duplicated_nor_silently_switched(self):
        for state in (self.state(phase="running"), self.state(active_turns={"child": "turn"})):
            with self.subTest(state=state), patch.object(cli, "read_state", return_value=state), \
                    patch.object(cli, "control_status", return_value=self.owner()), \
                    patch("run_os_goal.queue_same_owner_resume") as resume:
                with self.assertRaises(ValueError):
                    cli.start_existing(Path("/repo"))
                resume.assert_not_called()
        with patch.object(cli, "read_state", return_value=self.state(phase="running", simple_m14_m15=True)), \
                patch.object(cli, "control_status", return_value=self.owner()), \
                patch("run_os_goal.queue_same_owner_resume") as resume:
            self.assertEqual(cli.start_existing(Path("/repo"))["status"], "already_running")
            resume.assert_not_called()

    def test_explicit_run_uses_bound_same_owner_control_and_one_goal(self):
        with patch.object(cli, "read_state", return_value=self.state()), \
                patch.object(cli, "control_status", return_value=self.owner()), \
                patch.object(cli, "runtime_directory", return_value="/repo/.git/os-autopilot"), \
                patch("run_os_goal.simple_dispatch_instruction", return_value="M14 then M15") as goal, \
                patch("run_os_goal.queue_same_owner_resume", return_value="resume") as resume, \
                patch("run_os_goal.queue_instruction", return_value="instruction") as steer:
            result = cli.start_existing(Path("/repo"))
            self.assertFalse(result["new_controller_started"])
            self.assertEqual(result["thread_id"], cli.ROOT)
            self.assertEqual(resume.call_args.args[:2],
                             (Path("/repo/.git/os-autopilot"), "M14 then M15"))
            self.assertTrue(resume.call_args.kwargs["simple_m14_m15"])
            self.assertFalse(resume.call_args.kwargs["allow_active_primary"])
            self.assertEqual(steer.call_args.args[1], "M14 then M15")
            goal.assert_called_once_with()

    def test_refused_resume_does_not_queue_work(self):
        with patch.object(cli, "read_state", return_value=self.state()), \
                patch.object(cli, "control_status", return_value=self.owner()), \
                patch.object(cli, "runtime_directory", return_value="/repo/.git/os-autopilot"), \
                patch("run_os_goal.queue_same_owner_resume", side_effect=ValueError("actual hold")), \
                patch("run_os_goal.queue_instruction") as steer:
            with self.assertRaisesRegex(ValueError, "actual hold"):
                cli.start_existing(Path("/repo"))
            steer.assert_not_called()

    def test_status_and_watch_are_read_only(self):
        with patch.object(cli, "read_state", return_value={}), \
                patch.object(cli, "render_progress", return_value="ALL44\n") as render, \
                patch.object(cli, "request_stop") as stop, \
                patch.object(cli, "start_existing") as run:
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                cli.main(["status"], repo=Path("/repo"))
                cli.main(["watch", "--once"], repo=Path("/repo"))
            self.assertEqual(out.getvalue(), "ALL44\nALL44\n")
            self.assertEqual(render.call_count, 2)
            stop.assert_not_called()
            run.assert_not_called()

    def test_watch_does_not_flood_unchanged_reports(self):
        out = io.StringIO()
        with patch.object(cli, "read_state", return_value={}), \
                patch.object(cli, "render_progress", return_value="ALL44\n"), \
                patch.object(cli.time, "sleep", side_effect=[None, KeyboardInterrupt]):
            with self.assertRaises(KeyboardInterrupt):
                cli.watch(Path("/repo"), stream=out)
        self.assertEqual(out.getvalue(), "ALL44\n")

    def test_simple_resume_discards_old_startup_instructions_and_pins_dispatcher(self):
        import run_os_goal
        owner = run_os_goal.Campaign.__new__(run_os_goal.Campaign)
        owner.args = SimpleNamespace(startup_instruction="OBSOLETE_STARTUP_CHAIN", work_memory_gib=28)
        owner.state = {}
        owner.repo = Path("/repo")
        owner.adopt_simple_policy()
        self.assertIsNone(owner.args.startup_instruction)
        self.assertEqual((owner.args.model, owner.args.effort), ("gpt-6.1-sol", "max"))
        self.assertEqual(owner.args.work_memory_gib, 28)
        owner.args.startup_instruction = "OBSOLETE_STARTUP_CHAIN"
        with patch.object(run_os_goal, "launch_resources", return_value={}), \
                patch.object(run_os_goal, "resource_instructions", return_value="RESOURCES"):
            prompt = owner.instructions()
        self.assertNotIn("OBSOLETE_STARTUP_CHAIN", prompt)
        self.assertIn("M14-M15-OPEN-DELIVERABLES.md", prompt)


if __name__ == "__main__":
    unittest.main()
