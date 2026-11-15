"""Read-only writer readiness with temporary locks; no model/runtime work."""
import fcntl
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import os_goal_writer as writer


class WriterTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name)
        self.home = self.directory / "codex"
        self.lock = self.home / "thread-writer-locks" / (writer.SAVED_ROOT + ".lock")
        self.proc_locks = self.directory / "proc-locks"

    def existing_lock(self):
        self.lock.parent.mkdir(parents=True)
        self.lock.write_text("preserve original writer file\n")
        return self.lock.stat()

    def lock_row(self, info, pid, *, major=None, waiter=False):
        device = "{:x}:{:x}:{}".format(os.major(info.st_dev) if major is None else major,
                                      os.minor(info.st_dev), info.st_ino)
        return "10: " + ("-> " if waiter else "") + "FLOCK ADVISORY WRITE {} {} 0 EOF\n".format(pid, device)

    def probe(self):
        return writer.probe_writer_lock(codex_home=self.home, proc_locks=self.proc_locks)

    def test_absent_lock_is_observed_without_creating_any_path(self):
        result = self.probe()
        self.assertEqual(result["status"], "WRITER_READY")
        self.assertFalse(result["lock_present"])
        self.assertFalse(self.home.exists())

    def test_free_existing_lock_is_preserved_and_probe_releases_its_flock(self):
        before = self.existing_lock()
        result = self.probe()
        self.assertEqual(result["status"], "WRITER_READY")
        self.assertTrue(result["lock_present"])
        self.assertEqual(result["inode"], before.st_ino)
        self.assertEqual(self.lock.read_text(), "preserve original writer file\n")
        self.assertEqual(self.lock.stat().st_mtime_ns, before.st_mtime_ns)
        with self.lock.open("r") as owner:
            fcntl.flock(owner.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)

    def test_held_lock_reports_exact_device_inode_holder_and_keeps_owner(self):
        info = self.existing_lock()
        self.proc_locks.write_text(self.lock_row(info, 2661998)
                                  + self.lock_row(info, 999, major=os.major(info.st_dev) + 1)
                                  + self.lock_row(info, 888, waiter=True))
        with self.lock.open("r") as owner:
            fcntl.flock(owner.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            result = self.probe()
            self.assertEqual(result["status"], "WRITER_HELD")
            self.assertEqual(result["holder_pids"], [2661998])
            self.assertEqual(result["holder_pid"], 2661998)
            self.assertEqual(result["inode"], info.st_ino)
            with self.lock.open("r") as competing:
                with self.assertRaises(BlockingIOError):
                    fcntl.flock(competing.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        self.assertEqual(self.lock.read_text(), "preserve original writer file\n")

    def test_unavailable_proc_locks_does_not_turn_held_writer_into_ready(self):
        self.existing_lock()
        with self.lock.open("r") as owner:
            fcntl.flock(owner.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            result = self.probe()
        self.assertEqual(result["status"], "WRITER_HELD")
        self.assertEqual(result["holder_pids"], [])
        self.assertIsNone(result["holder_pid"])

    def test_codex_home_environment_and_default_select_the_exact_root(self):
        with patch.dict(os.environ, {"CODEX_HOME": str(self.home)}):
            result = writer.probe_writer_lock()
        self.assertEqual(Path(result["lock_path"]), self.lock)
        with patch.dict(os.environ, {"CODEX_HOME": ""}), patch.object(Path, "home", return_value=self.directory):
            result = writer.probe_writer_lock()
        self.assertEqual(Path(result["lock_path"]), self.directory / ".codex" / "thread-writer-locks"
                         / (writer.SAVED_ROOT + ".lock"))

    def test_symlink_writer_file_is_not_followed(self):
        self.lock.parent.mkdir(parents=True)
        target = self.directory / "foreign.lock"
        target.write_text("untouched")
        self.lock.symlink_to(target)
        with self.assertRaises(OSError):
            self.probe()
        self.assertEqual(target.read_text(), "untouched")

    def test_campaign_guard_reports_holder_without_modifying_saved_state(self):
        state = {"thread_id": writer.SAVED_ROOT, "repo": str(self.directory.resolve()),
                 "goal": {"threadId": writer.SAVED_ROOT, "objective": "functional original goal"}}
        path = self.directory / "state.json"
        original = json.dumps(state)
        path.write_text(original)
        info = self.existing_lock()
        self.proc_locks.write_text(self.lock_row(info, 2661998))
        with self.lock.open("r") as owner:
            fcntl.flock(owner.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            with self.assertRaisesRegex(RuntimeError, "holder PID=2661998;.*inode=" + str(info.st_ino)):
                writer.require_saved_writer_ready(self.directory, expected_repo=self.directory,
                    expected_objective="functional original goal", codex_home=self.home,
                    proc_locks=self.proc_locks)
        self.assertEqual(path.read_text(), original)


if __name__ == "__main__":
    unittest.main()
