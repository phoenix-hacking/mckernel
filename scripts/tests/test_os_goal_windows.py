"""Offline synthetic window/log tests; terminal creation is always mocked."""

from contextlib import ExitStack, redirect_stdout
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from os_goal_output import LiveOutput
import os_goal_windows as windows


class WindowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="os-goal-windows-")
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.spawn = self.stack.enter_context(patch.object(windows.subprocess, "Popen"))
        self.spawn.return_value = Mock(poll=Mock(return_value=0))
        self.stack.enter_context(patch.dict(os.environ, {"DISPLAY": ":0", "WAYLAND_DISPLAY": ""}))
        self.stack.enter_context(patch.object(windows.shutil, "which", return_value="/usr/bin/gnome-terminal"))
        self.console = self.stack.enter_context(redirect_stdout(io.StringIO()))

    def output(self, mode="off"):
        result = LiveOutput(self.directory, quiet=True, agent_windows=mode)
        self.addCleanup(result.close)
        return result

    def event(self, output, method, thread="child", **params):
        output.event({"method": method, "params": dict(threadId=thread, **params)})

    def started(self, output, thread, name="review", **fields):
        output.event({"method": "thread/started", "params": {
            "thread": dict(id=thread, agentNickname=name, **fields)}})

    def message(self, output, thread, text, ident="msg"):
        self.event(output, "item/agentMessage/delta", thread=thread, itemId=ident, delta=text)

    def test_default_off_preserves_console_and_isolates_identical_labels_and_item_ids(self):
        output = LiveOutput(self.directory, quiet=True)
        self.addCleanup(output.close)
        output.primary = "parent"
        for thread in ("parent", "../child-A", "child-B"):
            self.started(output, thread)
        self.message(output, "../child-A", "First ")
        self.message(output, "child-B", "Second ready\n")
        self.message(output, "../child-A", "ready\n")
        self.message(output, "parent", "Dispatcher ready\n")
        rows = output.snapshot()
        for thread, expected, absent in (("../child-A", "First ready", "Second ready"),
                                         ("child-B", "Second ready", "First ready")):
            path = Path(rows[thread]["path"])
            self.assertEqual(path.parent, self.directory / "agents")
            self.assertEqual(path.name, hashlib.sha256(thread.encode()).hexdigest() + ".log")
            self.assertIn(expected, path.read_text())
            self.assertNotIn(absent, path.read_text())
            self.assertEqual(rows[thread]["window_status"], "off")
        console_log = (self.directory / "console.log").read_text()
        self.assertIn("First ready", console_log)
        self.assertIn("Second ready", console_log)
        self.assertIn("[dispatcher/message] Dispatcher ready", console_log)
        self.assertEqual(self.console.getvalue(), "")
        self.spawn.assert_not_called()

    def test_unknown_primary_defers_events_then_opens_one_window_per_child(self):
        output = self.output("auto")
        self.started(output, "parent")
        self.started(output, "child-a")
        self.started(output, "child-b")
        self.message(output, "parent", "starting\n")
        self.assertEqual(output.snapshot()["parent"]["window_status"], "pending_primary")
        self.spawn.assert_not_called()
        output.primary = "parent"
        output.flush()
        output.snapshot()
        self.assertEqual(self.spawn.call_count, 2)
        self.assertEqual(output.snapshot()["parent"]["window_status"], "primary")
        for call in self.spawn.call_args_list:
            argv = call.args[0]
            self.assertEqual(argv[:4], ["/usr/bin/gnome-terminal", "--window", "--title", "McKernel review"])
            self.assertIn("--", argv)
            self.assertNotIn("shell", call.kwargs)
            self.assertTrue(call.kwargs["start_new_session"])
            self.assertEqual(call.kwargs["stdin"], subprocess.DEVNULL)
            self.assertEqual(Path(argv[argv.index("--log") + 1]).parent, output.agents_dir)

    def test_explicit_child_source_and_subagent_activity_before_primary(self):
        output = self.output("on")
        self.started(output, "parent")
        self.started(output, "early", source={"subagent": {"thread_spawn": {"parent_thread_id": "parent"}}})
        self.assertEqual(self.spawn.call_count, 1)
        self.event(output, "item/started", thread="parent", item={"id": "spawn", "type": "subAgentActivity",
                   "agentThreadId": "later", "agentPath": "audit", "kind": "started"})
        self.assertEqual(self.spawn.call_count, 2)
        output.primary = "parent"
        self.assertEqual(self.spawn.call_count, 2)

    def test_late_discovery_and_rename_preserve_path_and_do_not_respawn(self):
        output = self.output("on")
        output.primary = "parent"
        self.message(output, "child", "before name\n")
        before = output.snapshot()["child"]["path"]
        self.started(output, "child", "later")
        self.event(output, "thread/name/updated", name="renamed")
        self.message(output, "child", "after name\n")
        row = output.snapshot()["child"]
        self.assertEqual(row["path"], before)
        self.assertEqual(row["name"], "renamed")
        self.assertIn("[renamed/message] after name", Path(before).read_text())
        self.assertEqual(self.spawn.call_count, 1)
        index = json.loads(output.agent_index_path.read_text())
        self.assertEqual(index["agents"][0]["name"], "renamed")

    def test_sanitized_names_streams_and_metadata_never_include_reasoning(self):
        output = self.output("on")
        output.primary = "parent"
        self.started(output, "child", "\x1b]0;bad title\aReview\n\x1b[31m" + "x" * 200,
                     credentials="credential-not-for-index")
        self.message(output, "child", "visible\x1b]52;c;")
        output.flush(force=True)
        self.message(output, "child", "clipboard-data\a\x1b[31mclean\x1b[0m\x00\n")
        self.event(output, "item/started", item={"type": "reasoning", "id": "r",
                   "content": "private-reasoning", "summary": "private-summary"})
        self.event(output, "item/reasoning/textDelta", itemId="r", delta="private-delta")
        self.event(output, "item/completed", item={"type": "reasoning", "id": "r",
                   "content": "private-reasoning"})
        row = output.snapshot()["child"]
        self.assertLessEqual(len(row["name"]), 96)
        for path in (self.directory / "console.log", Path(row["path"]), output.agent_index_path):
            text = path.read_text()
            for forbidden in ("\x1b", "\x00", "clipboard-data", "bad title", "private-", "credential-not-for-index"):
                self.assertNotIn(forbidden, text)
        self.assertIn("visible", Path(row["path"]).read_text())
        self.assertIn("clean", Path(row["path"]).read_text())
        title = self.spawn.call_args.args[0][3]
        self.assertTrue(title.startswith("McKernel Review"))
        self.assertNotIn("\n", title)

    def test_capability_probe_never_spawns_and_handles_display_backends(self):
        self.assertEqual(windows.window_capability(), {"enabled": True, "backend": "/usr/bin/gnome-terminal",
                                                      "display": ":0", "error": None})
        self.assertFalse(windows.window_capability("off")["enabled"])
        with patch.dict(os.environ, {"DISPLAY": "", "WAYLAND_DISPLAY": "wayland-0"}):
            self.assertTrue(windows.window_capability("auto")["enabled"])
        with patch.dict(os.environ, {"DISPLAY": "", "WAYLAND_DISPLAY": ""}):
            capability = windows.window_capability("on")
            self.assertFalse(capability["enabled"])
            self.assertIn("unset", capability["error"])
            json.dumps(capability)
        with patch.object(windows.shutil, "which", return_value=None):
            self.assertIn("gnome-terminal", windows.window_capability()["error"])
        self.spawn.assert_not_called()

    def test_forced_on_unavailable_is_visible_and_logs_continue(self):
        with patch.object(windows.shutil, "which", return_value=None):
            output = self.output("on")
        output.primary = "parent"
        self.message(output, "child", "fallback works\n")
        row = output.snapshot()["child"]
        self.assertEqual(row["window_status"], "unavailable")
        self.assertIn("fallback readable logs", self.console.getvalue())
        self.assertIn("fallback works", Path(row["path"]).read_text())
        self.spawn.assert_not_called()

    def test_spawn_error_is_recorded_visible_and_not_retried(self):
        self.spawn.side_effect = OSError("desktop refused")
        output = self.output("on")
        output.primary = "parent"
        self.message(output, "child", "worker continues\n")
        row = output.snapshot()["child"]
        self.assertEqual(row["window_status"], "failed")
        self.assertIn("desktop refused", row["window_error"])
        self.assertIn("fallback readable log", self.console.getvalue())
        self.assertIn("worker continues", Path(row["path"]).read_text())
        self.assertEqual(self.spawn.call_count, 1)

    def test_async_launch_exit_failure_is_not_reported_as_success(self):
        process = self.spawn.return_value
        process.poll.return_value = None
        output = self.output("on")
        output.primary = "parent"
        self.started(output, "child")
        self.assertEqual(output.snapshot()["child"]["window_status"], "launching")
        process.poll.return_value = 1
        self.assertEqual(output.snapshot()["child"]["window_status"], "failed")
        self.assertIn("exit 1", self.console.getvalue())
        output.close()
        process.terminate.assert_not_called()
        process.kill.assert_not_called()

    def test_close_writes_marker_after_final_partial_output_and_is_idempotent(self):
        output = self.output()
        self.message(output, "child", "last fragment")
        self.assertFalse(output.agent_complete_path.exists())
        owner = json.loads(output.agent_owner_path.read_text())
        self.assertEqual(owner, {"pid": os.getpid(), "birth": windows.process_birth(os.getpid())})
        output.close()
        output.close()
        self.assertTrue(output.agent_complete_path.exists())
        self.assertIn("last fragment", Path(output.snapshot()["child"]["path"]).read_text())
        self.assertTrue(json.loads(output.agent_index_path.read_text())["agents"][0]["run_complete"])

    def test_closed_child_flushes_final_output_and_releases_file_descriptors(self):
        output = self.output()
        output.primary = "parent"
        fd_count = len(list(Path("/proc/self/fd").iterdir()))
        for number in range(40):
            thread = "retired-" + str(number)
            self.message(output, thread, "last partial")
            self.event(output, "thread/closed", thread=thread)
            row = output.snapshot()[thread]
            self.assertTrue(Path(row["closed_path"]).exists())
            self.assertEqual(row["window_status"], "closed")
            self.assertIn("last partial", Path(row["path"]).read_text())
        self.assertEqual(len(list(Path("/proc/self/fd").iterdir())), fd_count)
        self.message(output, "retired-0", "resumed output\n")
        self.assertIn("resumed output", Path(output.snapshot()["retired-0"]["path"]).read_text())

    def test_turn_completion_preserves_last_message_until_actual_shutdown(self):
        output = self.output()
        output.primary = "parent"
        self.message(output, "child", "last answer")
        self.event(output, "turn/completed", turn={"id": "t", "status": "completed"})
        row = output.snapshot()["child"]
        self.assertFalse(Path(row["closed_path"]).exists())
        self.event(output, "item/completed", thread="parent", item={"id": "close", "type": "collabAgentToolCall",
                   "tool": "closeAgent", "status": "completed", "receiverThreadIds": ["child"],
                   "agentsStates": {"child": {"status": "shutdown", "message": "not copied"}}})
        self.assertTrue(Path(row["closed_path"]).exists())
        log = Path(row["path"]).read_text()
        self.assertLess(log.index("last answer"), log.index("Thread shutdown"))

    def test_retired_child_resume_uses_new_marker_and_window(self):
        old_process = Mock(poll=Mock(return_value=None))
        self.spawn.side_effect = [old_process, Mock(poll=Mock(return_value=0)),
                                  Mock(poll=Mock(return_value=0))]
        output = self.output("on")
        output.primary = "parent"
        self.started(output, "child")
        log_path = Path(output.snapshot()["child"]["path"])
        markers = []
        for generation, method in enumerate(("thread/started", "turn/started"), 1):
            with self.subTest(resume_event=method):
                self.message(output, "child", "final partial " + str(generation))
                self.event(output, "thread/closed")
                old_marker = Path(output.snapshot()["child"]["closed_path"])
                markers.append(old_marker)
                marker_bytes = old_marker.read_bytes()
                for _ in range(2):
                    if method == "thread/started":
                        self.started(output, "child")
                    else:
                        self.event(output, method, turn={"id": "resumed", "status": "inProgress"})
                row = output.snapshot()["child"]
                new_marker = Path(row["closed_path"])
                self.assertFalse(row.get("retired", False))
                self.assertEqual(row["generation"], generation)
                self.assertEqual(row["path"], str(log_path))
                self.assertEqual(old_marker.read_bytes(), marker_bytes)
                self.assertFalse(new_marker.exists())
                self.assertEqual(self.spawn.call_count, generation + 1)
                argv = self.spawn.call_args.args[0]
                self.assertEqual(argv[argv.index("--closed") + 1], str(new_marker))
                old_process.poll.return_value = 1
                self.assertEqual(output.snapshot()["child"]["window_status"], "launched")
                with patch.object(windows.time, "sleep") as sleep, patch("builtins.input") as prompt:
                    windows.follow(log_path, output.agent_owner_path, output.agent_complete_path,
                                   output.agent_index_path, old_marker)
                sleep.assert_not_called()
                prompt.assert_not_called()

        def close_resumed(_):
            self.message(output, "child", "resumed final output")
            self.event(output, "thread/closed")

        with redirect_stdout(io.StringIO()) as stdout, \
                patch.object(windows.time, "sleep", side_effect=close_resumed) as sleep, \
                patch("builtins.input") as prompt:
            windows.main(["follow", "--log", str(log_path), "--owner", str(output.agent_owner_path),
                          "--complete", str(output.agent_complete_path), "--index", str(output.agent_index_path),
                          "--closed", str(new_marker)])
        sleep.assert_called_once()
        prompt.assert_not_called()
        self.assertIn("resumed final output", stdout.getvalue())
        self.assertTrue(all(marker.exists() for marker in markers))


class FollowerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="os-goal-follower-")
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.log, self.owner, self.complete, self.index = [self.directory / name for name in
                                                          ("agent.log", "owner.json", "complete", "index.json")]
        self.log.write_text("initial\n")
        windows.atomic_json(self.owner, {"pid": os.getpid(), "birth": windows.process_birth(os.getpid())})
        windows.atomic_json(self.index, {"agents": [{"path": str(self.log), "name": "initial name"}]})

    def test_appends_then_complete_marker_drains_tail_and_holds_prompt(self):
        stdout, stdin = io.StringIO(), Mock(isatty=Mock(return_value=True))

        def finish(_):
            with self.log.open("a") as stream:
                stream.write("final\n")
            self.complete.touch()

        with redirect_stdout(stdout), patch.object(windows.sys, "stdin", stdin), \
                patch.object(windows.time, "sleep", side_effect=finish), patch("builtins.input") as prompt:
            windows.follow(self.log, self.owner, self.complete, self.index)
        self.assertIn("initial\nfinal\n", stdout.getvalue())
        self.assertIn("stopped following", stdout.getvalue())
        prompt.assert_called_once()

    def test_owner_disappearance_or_pid_reuse_stops_without_marker(self):
        for birth in (None, "different-birth"):
            with self.subTest(birth=birth), redirect_stdout(io.StringIO()) as stdout, \
                    patch.object(windows, "process_birth", return_value=birth), \
                    patch.object(windows.sys, "stdin", Mock(isatty=Mock(return_value=False))), \
                    patch.object(windows.time, "sleep") as sleep:
                windows.follow(self.log, self.owner, self.complete, self.index)
                sleep.assert_not_called()
                self.assertIn("initial", stdout.getvalue())

    def test_closed_child_drains_log_and_exits_without_prompt(self):
        self.log.write_text("final output\n" * 20000)
        self.log.with_suffix(".closed").touch()
        with redirect_stdout(io.StringIO()) as stdout, \
                patch.object(windows.sys, "stdin", Mock(isatty=Mock(return_value=True))), \
                patch("builtins.input") as prompt, patch.object(windows.time, "sleep") as sleep:
            windows.follow(self.log, self.owner, self.complete, self.index)
        self.assertEqual(stdout.getvalue().count("final output\n"), 20000)
        prompt.assert_not_called()
        sleep.assert_not_called()

    def test_follower_updates_title_from_renamed_index(self):
        stdout = Mock(wraps=io.StringIO())
        stdout.isatty.return_value = True

        def rename(_):
            windows.atomic_json(self.index, {"agents": [{"path": str(self.log), "name": "renamed\x1b]2;bad\a"}]})
            self.complete.touch()

        with patch.object(windows.sys, "stdout", stdout), \
                patch.object(windows.sys, "stdin", Mock(isatty=Mock(return_value=False))), \
                patch.object(windows.time, "sleep", side_effect=rename):
            windows.follow(self.log, self.owner, self.complete, self.index)
        rendered = "".join(call.args[0] for call in stdout.write.call_args_list)
        self.assertIn("\x1b]0;McKernel initial name\a", rendered)
        self.assertIn("\x1b]0;McKernel renamed\a", rendered)
        self.assertNotIn("bad", rendered)

    def test_real_stdlib_entrypoint_exits_for_dead_owner_without_gui(self):
        windows.atomic_json(self.owner, {"pid": 999999999, "birth": "gone"})
        result = subprocess.run([sys.executable, "-B", str(Path(windows.__file__)), "follow",
                                 "--log", str(self.log), "--owner", str(self.owner),
                                 "--complete", str(self.complete), "--index", str(self.index)],
                                stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=5)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("initial", result.stdout)
        self.assertIn("stopped following", result.stdout)


if __name__ == "__main__":
    unittest.main()
