"""Offline guardian protocol tests; no model, service or real signal operations."""
import json
import os
from pathlib import Path
import signal
import sys
import tempfile
import time
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import os_goal_guardian as subject
import os_goal_guard_protocol as protocol


class GuardianTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name)
        self.launch, self.mailbox, self.notify = Mock(return_value={"started": True}), Mock(return_value={}), Mock()
        self.guard = subject.Guardian(self.directory, self.directory, launch_engine=self.launch,
                                      mailbox_poll=self.mailbox, heartbeat=self.notify, stale_seconds=30)
        self.addCleanup(self.guard.close)
        self.births = {20000001: "111", 20000002: "222", 20000003: "333"}
        real_start = protocol.process_start
        def observed(pid):
            return self.births[pid] if pid in self.births else real_start(pid)
        for module in (subject, protocol):
            handle = patch.object(module, "process_start", side_effect=observed)
            handle.start()
            self.addCleanup(handle.stop)
        self.send = patch.object(subject, "signal_exact").start()
        self.addCleanup(patch.stopall)
        self.state = {"guardian_run_id": self.guard.guard["run_id"], "worker_pid": 20000002,
                      "worker_start": "222", "server_pid": 20000003, "server_start": "333",
                      "thread_id": "same-root", "log_dir": "/runs/current", "phase": "running",
                      "goal": {"status": "active", "threadId": "same-root", "objective": "unchanged", "tokenBudget": 100, "tokensUsed": 40},
                      "active_turns": {"same-root": "turn"}, "stop_reason": None}
        self.watcher = {"guardian_run_id": self.guard.guard["run_id"], "watcher_pid": 20000001,
                        "watcher_start": "111", "worker_pid": 20000002, "at": time.time()}

    def save(self):
        protocol.atomic_json(self.directory / "state.json", self.state)
        protocol.atomic_json(self.directory / "watcher.json", self.watcher)

    def request(self):
        self.watcher["at"] = time.time() - 100
        self.save()
        self.guard.tick()
        return self.guard.guard["checkpoint"]

    def finish(self, request):
        self.state.update(phase="stopped", active_turns={}, stop_reason="guardian_recovery",
                          guardian_checkpoint={"run_id": request["run_id"], "request_id": request["request_id"],
                                               "worker_pid": request["worker_pid"], "worker_start": request["worker_start"]})
        self.state["goal"]["status"] = "paused"
        self.births.update({20000001: None, 20000002: None, 20000003: None})
        self.save()

    def test_restart_without_explicit_intent_never_starts_engine_and_polls_mailbox(self):
        self.guard.tick()
        self.guard.tick()
        self.launch.assert_not_called()
        self.assertEqual(self.mailbox.call_count, 2)
        self.assertEqual(self.notify.call_count, 4)

    def test_explicit_start_is_persisted_before_launch_and_not_replayed(self):
        subject.authorize_start(self.directory, request_id="user-start")
        def launch(proof):
            self.assertIsNone(proof)
            intent = protocol.read_json(next((self.directory / "guardian-intents").glob("*.json")))
            self.assertEqual(intent["status"], "sending")
        self.launch.side_effect = launch
        self.guard.tick()
        run_id = self.guard.guard["run_id"]
        self.guard.close()
        self.guard = subject.Guardian(self.directory, self.directory, launch_engine=self.launch,
                                      mailbox_poll=self.mailbox, heartbeat=self.notify)
        self.assertEqual(self.guard.guard["run_id"], run_id)
        self.guard.tick()
        self.launch.assert_called_once_with(None)

    def test_new_guardian_instance_resets_receipt_freshness_without_new_goal_identity(self):
        original_id = self.guard.guard["run_id"]
        self.guard.close()
        with patch.object(subject.time, "time", return_value=2000000000):
            self.guard = subject.Guardian(self.directory, self.directory, launch_engine=self.launch,
                                          mailbox_poll=self.mailbox, heartbeat=self.notify)
        self.assertEqual(self.guard.guard["run_id"], original_id)
        self.assertEqual(self.guard.guard["started_at"], 2000000000)
        self.assertEqual(protocol.read_json(self.directory / "guardian.json")["started_at"], 2000000000)
        self.launch.assert_not_called()

    def test_terminal_policy_and_budget_stops_keep_mailbox_alive_without_launch(self):
        for reason in ("signal_15", "quota_exhausted", "cyberPolicy", "permission_denied"):
            self.state["stop_reason"] = reason
            self.save()
            self.guard.tick()
        self.launch.assert_not_called()
        self.send.assert_not_called()
        self.assertEqual(self.mailbox.call_count, 4)

    def test_existing_owner_prevents_manual_duplicate(self):
        self.save()
        self.watcher["guardian_run_id"] = "different"
        self.save()
        subject.authorize_start(self.directory)
        with patch.object(subject, "lease_free", return_value=False):
            self.guard.tick()
        self.launch.assert_not_called()

    def test_healthy_supervisor_silent_work_is_not_a_stall(self):
        self.save()
        self.guard.tick()
        self.assertEqual(self.guard.guard["phase"], "SUPERVISED")
        self.send.assert_not_called()

    def test_stale_supervisor_requests_exact_worker_checkpoint_once(self):
        request = self.request()
        self.assertEqual(request["worker_pid"], 20000002)
        self.send.assert_called_once_with(20000002, "222", signal.SIGUSR1)
        self.guard.tick()
        self.assertEqual(self.send.call_count, 1)
        self.launch.assert_not_called()

    def test_crashed_supervisor_recovers_only_from_exact_clean_checkpoint(self):
        request = self.request()
        self.finish(request)
        self.guard.tick()
        path = self.launch.call_args.args[0]
        self.assertIsNotNone(path)
        proof = protocol.read_json(path)
        self.assertEqual(proof["goal_after"]["tokenBudget"], 100)
        self.assertEqual(proof["goal_after"]["tokensUsed"], 40)
        self.assertEqual(proof["thread_id"], "same-root")
        self.guard.tick()
        self.assertEqual(self.launch.call_count, 1)

    def test_engine_retiring_defers_proof_then_submits_exactly_once(self):
        request = self.request()
        self.finish(request)
        submitted = Mock()
        busy = [True]
        def launch(proof):
            if busy:
                busy.pop()
                raise protocol.EngineLaunchDeferred("engine unit deactivating; no submission")
            submitted(proof)
            return {"started": True}
        self.launch.side_effect = launch
        self.guard.tick()
        self.assertEqual(self.guard.guard["phase"], "WAITING")
        self.assertEqual(self.guard.guard["checkpoint"]["request_id"], request["request_id"])
        self.assertIsNone(self.guard.guard["launch"])
        submitted.assert_not_called()
        self.guard.tick()
        self.assertIsNone(self.guard.guard["checkpoint"])
        submitted.assert_called_once()
        self.guard.tick()
        submitted.assert_called_once()

    def test_user_stop_during_checkpoint_cannot_be_recovered(self):
        request = self.request()
        self.finish(request)
        self.state["stop_reason"] = "signal_15"
        self.save()
        self.guard.tick()
        self.launch.assert_not_called()

    def test_live_server_or_unreconciled_delivery_prevents_replacement(self):
        request = self.request()
        self.finish(request)
        self.births[20000003] = "333"
        self.guard.tick()
        self.launch.assert_not_called()
        self.births[20000003] = None
        self.state["transport_uncertain"] = {"method": "turn/start"}
        self.save()
        self.guard.tick()
        self.launch.assert_not_called()

    def test_hung_watcher_only_retired_after_clean_worker_and_server_exit(self):
        request = self.request()
        self.finish(request)
        self.births[20000001] = "111"
        self.guard.tick()
        self.send.assert_called_with(20000001, "111", signal.SIGTERM)
        self.assertEqual(self.send.call_count, 2)
        self.launch.assert_not_called()

    def test_mailbox_failure_does_not_disable_supervisor_health(self):
        self.mailbox.side_effect = RuntimeError("network unavailable")
        self.save()
        self.guard.tick()
        self.assertEqual(self.guard.guard["phase"], "SUPERVISED")
        self.assertIn("mailbox_error", self.guard.guard)

    def test_returned_mailbox_error_survives_backoff_and_clears_only_on_success(self):
        self.save()
        self.mailbox.side_effect = [{"status": "ERROR", "reason": "Bearer private-token " + "x" * 700},
                                    {"status": "BACKOFF"}, {"status": "THROTTLED"}, {"status": "POLLED"}]
        self.guard.tick()
        first = self.guard.guard["mailbox_error"]
        self.assertEqual(first["type"], "MailboxPollError")
        self.assertLessEqual(len(first["reason"]), 500)
        self.assertNotIn("private-token", first["reason"])
        self.guard.tick()
        self.assertEqual(self.guard.guard["mailbox_error"], first)
        self.guard.tick()
        self.assertEqual(self.guard.guard["mailbox_error"], first)
        self.guard.tick()
        self.assertIsNone(self.guard.guard["mailbox_error"])
        self.assertEqual(self.guard.guard["phase"], "SUPERVISED")

    def test_ready_precedes_first_poll_and_watchdog_precedes_engine_launch(self):
        sequence = []
        self.guard.heartbeat = lambda status: sequence.append("heartbeat")
        subject.authorize_start(self.directory, request_id="start-for-timing")
        def poll(directory, context):
            sequence.append("mailbox")
            return {"status": "POLLED"}
        def launch(proof):
            sequence.append("launch")
            self.guard.stopping = "requested"
        self.guard.mailbox_poll = poll
        self.guard.launch_engine = launch
        # A fake sleep advances the shutdown path without running any engine.
        with patch.object(subject.time, "sleep"):
            self.guard.run(interval=0)
        self.assertEqual(sequence[:4], ["heartbeat", "mailbox", "heartbeat", "launch"])
        self.assertEqual(sequence[-1], "heartbeat")

    def test_stop_received_during_mailbox_prevents_pending_launch(self):
        subject.authorize_start(self.directory, request_id="pending-user-start")
        def poll(directory, context):
            self.guard.stopping = "requested"
            return {"status": "POLLED"}
        self.guard.mailbox_poll = poll
        self.guard.tick()
        self.launch.assert_not_called()

    def test_malformed_engine_state_still_polls_mailbox(self):
        (self.directory / "state.json").write_text("not json")
        self.guard.tick()
        self.mailbox.assert_called_once()
        self.launch.assert_not_called()

    def test_resume_ack_follows_durable_idempotent_intent(self):
        ack = Mock()
        self.guard.mailbox_ack = ack
        self.mailbox.return_value = {"resume_request_id": "github-comment-123", "resume_created_at": time.time()}
        self.guard.tick()
        self.guard.tick()
        self.assertEqual(len(list((self.directory / "guardian-intents").glob("*.json"))), 1)
        self.assertEqual(self.launch.call_count, 1)
        ack.assert_called_with("github-comment-123")

    def test_worker_rejects_unauthenticated_checkpoint_request(self):
        self.state.update(worker_pid=os.getpid(), worker_start=self.guard.guard["start"])
        request = {"request_id": "request", "run_id": self.guard.guard["run_id"],
                   "guardian_pid": os.getpid(), "guardian_start": self.guard.guard["start"],
                   "worker_pid": os.getpid(), "worker_start": self.state["worker_start"],
                   "thread_id": "same-root", "log_dir": "/runs/current", "reason": "supervisor_unavailable",
                   "expires_at": time.time() + 60}
        protocol.atomic_json(self.directory / "guardian-checkpoint.json", request)
        self.assertEqual(protocol.checkpoint_request(self.directory, self.state)["request_id"], "request")
        request["run_id"] = "wrong"
        protocol.atomic_json(self.directory / "guardian-checkpoint.json", request)
        self.assertIsNone(protocol.checkpoint_request(self.directory, self.state))

    def test_explicit_resume_can_repair_generic_failure_but_never_policy(self):
        state = dict(self.state, last_error="old technical failure")
        self.assertIsNone(protocol.recovery_blocker(state, explicit_user=True))
        self.assertEqual(protocol.recovery_blocker(state), "current_or_unattributed_failure")
        state["last_error"] = {"codexErrorInfo": "cyberPolicy", "message": "denied"}
        self.assertIsNotNone(protocol.recovery_blocker(state, explicit_user=True))

    def test_durable_user_stop_keeps_mailbox_and_never_restarts(self):
        self.save()
        subject.authorize_start(self.directory, request_id="older-start")
        subject.request_stop(self.directory, request_id="stop-now")
        self.guard.tick()
        self.send.assert_called_once_with(20000001, "111", signal.SIGTERM)
        self.guard.tick()
        self.assertEqual(self.send.call_count, 1)
        self.assertEqual(self.mailbox.call_count, 2)
        self.launch.assert_not_called()

    def test_restarted_guardian_rebinds_one_idempotent_checkpoint(self):
        request = self.request()
        self.guard.guard["checkpoint"] = dict(request, guardian_start="old-birth")
        self.guard.tick()
        self.assertEqual(self.send.call_count, 2)
        self.assertEqual(self.guard.guard["checkpoint"]["request_id"], request["request_id"])
        self.guard.tick()
        self.assertEqual(self.send.call_count, 2)

    def test_old_mailbox_resume_polled_after_new_user_stop_cannot_resume(self):
        authored_at = time.time() - 60
        subject.request_stop(self.directory)
        self.mailbox.return_value = {"resume_request_id": "old-comment", "resume_created_at": authored_at}
        self.guard.tick()
        self.launch.assert_not_called()
        intent = protocol.read_json(next((self.directory / "guardian-intents").glob("*.json")))
        self.assertEqual(intent["status"], "cancelled_by_user_stop")
        self.assertEqual(intent["authored_at"], authored_at)

    def test_native_and_budget_hold_prevent_explicit_launch_and_auto_recovery(self):
        for hold in ("native_hold", "budget_hold"):
            with self.subTest(hold=hold):
                state = dict(self.state, **{hold: True})
                self.assertIsNotNone(protocol.recovery_blocker(state))
                self.assertIsNotNone(protocol.recovery_blocker(state, explicit_user=True))


if __name__ == "__main__":
    unittest.main()
