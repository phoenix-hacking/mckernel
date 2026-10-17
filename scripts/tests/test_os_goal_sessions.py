"""Fresh local conversation cursors, using only temporary files and local PIDs."""
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import os_goal_sessions as sessions
from watch_os_goal import process_start


def atomic_json(path, value):
    temporary = path.with_name("fresh-test.tmp")
    with temporary.open("w") as stream:
        json.dump(value, stream)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)
    fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


class FreshSessionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pid = os.fork()
        if pid == 0:
            os._exit(0)
        os.waitpid(pid, 0)
        cls.dead_pid = pid

    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="os-goal-fresh-test-")
        self.addCleanup(temporary.cleanup)
        self.base = Path(temporary.name)
        self.repo = self.base / "repo"
        self.repo.mkdir()
        self.directory = self.base / "campaign"
        self.directory.mkdir()
        self.path = self.directory / "state.json"
        self.state = {"schema_version": 1, "repo": str(self.repo),
                      "thread_id": "old-thread", "phase": "stopped",
                      "worker_pid": self.dead_pid, "server_pid": self.dead_pid,
                      "goal": {"objective": "Retained original objective", "status": "blocked",
                               "tokenBudget": 12345, "tokensUsed": 987},
                      "stop_reason": "turn_failed",
                      "last_error": {"codexErrorInfo": "cyberPolicy", "message": "Retain verbatim"}}
        self.save()
        (self.directory / "logs").mkdir()
        (self.directory / "logs" / "old.jsonl").write_bytes(b"old log\n")
        (self.directory / "runtime-marker").write_bytes(b"preserve runtime")

    def save(self):
        # Noncanonical whitespace is part of the archival contract.
        self.raw = (json.dumps(self.state, indent=3) + " \n\n").encode()
        self.path.write_bytes(self.raw)

    def snapshot(self):
        return {str(path.relative_to(self.directory)): path.read_bytes()
                for path in self.directory.rglob("*") if path.is_file()}

    def fresh(self, **kwargs):
        return sessions.prepare_fresh_session(self.directory, self.repo, atomic_json, **kwargs)

    def proof(self, *, code=-9, watchdog=False, **changes):
        value = {"schema_version": 1, "watcher_pid": os.getppid(),
                 "watcher_start": process_start(os.getppid()),
                 "worker_pid": self.state["worker_pid"], "thread_id": self.state["thread_id"],
                 "state_sha256": hashlib.sha256(self.path.read_bytes()).hexdigest(),
                 "exit_code": code, "watchdog": watchdog, "stopped": False, "server_retired": True}
        value.update(changes)
        path = self.directory / "fresh-recovery-1.json"
        path.write_text(json.dumps(value))
        return path

    def assert_refused(self, **kwargs):
        before = self.snapshot()
        with self.assertRaises((ValueError, OSError)):
            self.fresh(**kwargs)
        self.assertEqual(before, self.snapshot())

    def test_explicit_fresh_archives_policy_block_verbatim_and_preserves_everything(self):
        pending = self.directory / "instructions" / "pending"
        pending.mkdir(parents=True)
        (pending / "old.json").write_bytes(b"old pending instruction\n")
        historical = self.directory / "session-archives" / "historical"
        historical.mkdir(parents=True)
        (historical / "state.json").write_bytes(b"historical unchanged")
        before = self.snapshot()
        fresh = self.fresh()
        archived = Path(fresh["previous_session"]["state_path"])
        self.assertEqual(archived.read_bytes(), self.raw)
        self.assertEqual(json.loads(archived.read_bytes()), self.state)
        self.assertEqual(fresh, json.loads(self.path.read_bytes()))
        self.assertIsNone(fresh["thread_id"])
        self.assertEqual(set(fresh), {"schema_version", "repo", "thread_id", "created_at", "previous_session"})
        self.assertEqual(fresh["previous_session"]["goal_status"], "blocked")
        self.assertEqual(fresh["previous_session"]["stop_reason"], "turn_failed")
        for name, raw in before.items():
            if name != "state.json":
                self.assertEqual((self.directory / name).read_bytes(), raw)

    def test_archive_is_present_and_fsynced_before_atomic_state_publication(self):
        syncs = []
        real_sync = os.fsync

        def sync(fd):
            syncs.append(fd)
            real_sync(fd)

        def publish(path, value):
            self.assertEqual(self.path.read_bytes(), self.raw)
            self.assertEqual(Path(value["previous_session"]["state_path"]).read_bytes(), self.raw)
            self.assertGreaterEqual(len(syncs), 4)
            atomic_json(path, value)

        with patch.object(sessions.os, "fsync", side_effect=sync):
            sessions.prepare_fresh_session(self.directory, self.repo, publish)

    def test_manual_requires_stopped_paused_or_blocked_goal(self):
        for phase, status in (("running", "paused"), ("stopped", "active"),
                              ("stopped", "complete"), ("stopped", "usageLimited"),
                              ("stopped", "budgetLimited")):
            with self.subTest(phase=phase, status=status):
                self.state.update(phase=phase)
                self.state["goal"]["status"] = status
                self.save()
                self.assert_refused()

    def test_valid_paused_goal_and_null_server_are_accepted(self):
        self.state["goal"]["status"] = "paused"
        self.state["server_pid"] = None
        self.save()
        self.assertIsNone(self.fresh()["thread_id"])

    def test_expected_objective_mismatch_refuses_before_archival(self):
        self.assert_refused(expected_objective="Another launcher's objective")
        self.assertFalse((self.directory / "session-archives").exists())
        self.assertIsNone(self.fresh(expected_objective=self.state["goal"]["objective"])["thread_id"])

    def test_account_guard_baseline_is_preserved_unchanged(self):
        self.state["last_rate_limits"] = {
            "credits": {"balance": "123.45", "hasCredits": True},
            "primary": {"usedPercent": 71, "resetsAt": 123456}}
        self.save()
        fresh = self.fresh()
        self.assertEqual(fresh["last_rate_limits"], self.state["last_rate_limits"])
        self.assertEqual(json.loads(self.path.read_bytes())["last_rate_limits"], self.state["last_rate_limits"])
        archived = Path(fresh["previous_session"]["state_path"])
        self.assertEqual(archived.read_bytes(), self.raw)

    def test_prepared_seed_retry_reuses_same_archive_without_any_mutation(self):
        fresh = self.fresh(expected_objective=self.state["goal"]["objective"])
        before = self.snapshot()
        self.assertEqual(self.fresh(expected_objective=self.state["goal"]["objective"]), fresh)
        self.assertEqual(self.snapshot(), before)
        self.assert_refused(expected_objective="Foreign objective")

    def test_prepared_seed_requires_unchanged_owned_archive_metadata(self):
        fresh = self.fresh()
        fresh["previous_session"]["thread_id"] = "foreign-thread"
        atomic_json(self.path, fresh)
        self.assert_refused()

    def test_missing_malformed_foreign_or_initial_state_is_refused(self):
        original = json.loads(self.raw)
        for changes in ({"schema_version": True}, {"schema_version": 2}, {"repo": "/elsewhere"},
                        {"thread_id": None}, {"goal": None}, {"goal": {"status": "paused"}},
                        {"worker_pid": None}, {"worker_pid": True}, {"worker_pid": 0},
                        {"server_pid": -1}, {"server_pid": "123"}):
            with self.subTest(changes=changes):
                self.state = dict(original, **changes)
                self.save()
                self.assert_refused()
        self.path.write_bytes(b"not JSON")
        self.assert_refused()
        self.path.unlink()
        self.assert_refused()

    def test_live_worker_or_server_refuses_without_signalling(self):
        for field in ("worker_pid", "server_pid"):
            with self.subTest(field=field):
                self.state[field] = os.getpid()
                self.save()
                self.assert_refused()
                self.state[field] = self.dead_pid

    def test_unknown_pid_liveness_is_refused(self):
        with patch.object(sessions.os, "kill", side_effect=PermissionError("unknown")):
            self.assert_refused()

    def test_uncertain_instruction_delivery_is_refused(self):
        for field in ("resume_instruction", "last_instruction"):
            for status in ("sending", "delivery_uncertain", "unknown", None):
                with self.subTest(field=field, status=status):
                    self.state[field] = {"status": status}
                    self.save()
                    self.assert_refused()
            self.state.pop(field)
        self.save()
        sending = self.directory / "instructions" / "sending"
        sending.mkdir(parents=True)
        (sending / "even-non-json-entry").write_bytes(b"uncertain")
        self.assert_refused()

    def test_symlinks_and_nonregular_state_are_refused(self):
        retained = self.base / "retained.json"
        self.path.rename(retained)
        self.path.symlink_to(retained)
        self.assert_refused()
        self.assertEqual(retained.read_bytes(), self.raw)
        self.path.unlink()
        os.mkfifo(self.path)
        with self.assertRaises(ValueError):
            self.fresh()
        self.path.unlink()
        self.path.write_bytes(self.raw)
        archives = self.directory / "session-archives"
        archives.symlink_to(self.repo, target_is_directory=True)
        self.assert_refused()

    def test_duplicate_json_keys_are_refused(self):
        self.path.write_bytes(b'{"schema_version": 1, "schema_version": 1}')
        self.assert_refused()

    def test_running_crash_needs_exact_live_parent_retirement_and_classification_proof(self):
        self.state.update(phase="running", stop_reason=None)
        self.state["goal"]["status"] = "active"
        self.state.pop("last_error")
        self.save()
        self.assert_refused(recovery=True)
        proof = self.proof()
        fresh = self.fresh(recovery=True, recovery_proof=proof)
        self.assertEqual(Path(fresh["previous_session"]["state_path"]).read_bytes(), self.raw)
        self.assertTrue(proof.exists())
        self.assert_refused(recovery=True, recovery_proof=proof)

    def test_recovery_proof_mismatches_refuse_without_archival(self):
        self.state.update(phase="running", stop_reason=None)
        self.state["goal"]["status"] = "active"
        self.state.pop("last_error")
        self.save()
        for changes in ({"watcher_pid": os.getpid()}, {"watcher_start": "unknown"},
                        {"worker_pid": self.dead_pid + 1}, {"thread_id": "other"},
                        {"state_sha256": "0" * 64}, {"server_retired": False},
                        {"stopped": True}, {"exit_code": True}, {"watchdog": "yes"},
                        {"exit_code": 1}, {"schema_version": True}):
            with self.subTest(changes=changes):
                proof = self.proof(**changes)
                self.assert_refused(recovery=True, recovery_proof=proof)

    def test_all_recorded_stops_override_watchdog_fresh_recovery(self):
        self.state["goal"]["status"] = "active"
        self.state.pop("last_error")
        for reason in ("work_window", "signal_15", "quota_exhausted", "quota_or_rate_limit",
                       "included_usage_guard", "included_usage_unknown", "credit_balance_unknown",
                       "credit_balance_decreased", "chatgpt_auth_required", "chatgpt_auth_changed",
                       "needs_user_input", "goal_cleared", "cyberPolicy"):
            with self.subTest(reason=reason):
                self.state.update(phase="running", stop_reason=reason)
                self.save()
                self.assert_refused(recovery=True, recovery_proof=self.proof(watchdog=True))
        for status in ("complete", "usageLimited", "budgetLimited"):
            self.state["goal"]["status"] = status
            self.state["stop_reason"] = None
            self.save()
            self.assert_refused(recovery=True, recovery_proof=self.proof(watchdog=True))

    def test_policy_failure_refuses_even_with_stale_retryable_running_snapshot(self):
        for reason in (None, "launcher_error", "turn_failed", "server_error"):
            with self.subTest(reason=reason):
                self.state.update(phase="running", stop_reason=reason, retryable=True)
                self.save()
                self.assert_refused(recovery=True, recovery_proof=self.proof(code=1, watchdog=True))

    def test_state_race_is_detected_before_creating_archive(self):
        real_read = sessions._read
        calls = 0

        def read(fd, name):
            nonlocal calls
            if name == "state.json":
                calls += 1
                if calls == 2:
                    self.path.write_bytes(self.raw + b" ")
            return real_read(fd, name)

        with patch.object(sessions, "_read", side_effect=read):
            with self.assertRaisesRegex(ValueError, "changed before archival"):
                self.fresh()
        self.assertEqual(self.path.read_bytes(), self.raw + b" ")
        self.assertFalse((self.directory / "session-archives").exists())

    def test_writer_failure_keeps_original_state_and_complete_archive(self):
        def fail(path, value):
            raise OSError("publication unavailable")

        with self.assertRaises(OSError):
            sessions.prepare_fresh_session(self.directory, self.repo, fail)
        self.assertEqual(self.path.read_bytes(), self.raw)
        archives = list((self.directory / "session-archives").glob("*/state.json"))
        self.assertEqual(len(archives), 1)
        self.assertEqual(archives[0].read_bytes(), self.raw)


if __name__ == "__main__":
    unittest.main()
