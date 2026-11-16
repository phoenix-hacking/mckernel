"""Mock-only local user STOP: no live RPC, signals, services or OS workloads."""
import copy
import os
from pathlib import Path
import tempfile
from types import MethodType, SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from scripts.tests.test_os_goal_launcher import launcher
import m14_m15_control as control
from os_goal_guard_protocol import atomic_json, read_json


class StopRPC:
    def __init__(self):
        self.proc = SimpleNamespace(pid=987654321)
        self.calls = []
        self.goal = {"objective": launcher.OBJECTIVE, "status": "active"}
        self.turns = {"root": "root-turn", "loaded-child": "child-turn"}
        self.failures = {}
        self.close = Mock(side_effect=AssertionError("Original channel must remain open"))

    def call(self, method, params, **kwargs):
        self.calls.append((method, copy.deepcopy(params)))
        if method in self.failures:
            raise self.failures[method]
        if method == "thread/goal/get":
            return {"goal": dict(self.goal)}
        if method == "thread/goal/set":
            self.goal["status"] = params["status"]
            return {"goal": dict(self.goal)}
        if method == "thread/loaded/list":
            return {"data": list(self.turns), "nextCursor": None}
        if method == "thread/turns/list":
            turn = self.turns.get(params["threadId"])
            return {"data": [{"id": turn, "status": "inProgress"}] if turn else []}
        if method == "turn/interrupt":
            self.turns.pop(params["threadId"], None)
            return {}
        raise AssertionError("Unexpected RPC, including account reads: " + method)


class UserStopTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="m14-m15-stop-")
        self.addCleanup(temporary.cleanup)
        self.repo = Path(temporary.name)
        self.directory = self.repo / ".git" / "os-autopilot"
        self.directory.mkdir(parents=True)
        self.rpc = StopRPC()
        self.state = {"repo": str(self.repo), "thread_id": "root", "log_dir": str(self.directory / "runs/current"),
                      "worker_pid": os.getpid(), "worker_start": "100", "server_pid": self.rpc.proc.pid,
                      "server_start": "101", "controller_dispatch_enabled": True,
                      "active_turns": {"root": "root-turn", "event-child": "event-turn"},
                      "phase": "owner_retained", "credit_budget_error": "account read unavailable",
                      "credit_budget": {"id": "7c6ef3604bfb4008a917bba8cfb6cfaa", "spent": "123", "budget": "52079.8011050000"},
                      "native_hold": {"owner": "original-native", "bytes": 12 * 1024 ** 3, "outcome": "UNKNOWN"},
                      "resource_hold": {"owner": "retained-host", "jobs": 2, "bytes": 402653184}}
        self.campaign = SimpleNamespace(directory=self.directory, repo=self.repo, state=self.state,
            log_dir=self.state["log_dir"], rpc=self.rpc, controlled=True, stopping=True,
            args=SimpleNamespace(retain_owner_on_stop=False),
            stop_reason="credit_budget_unknown", stop_now=True, checkpoint_requested=False,
            primary_stop_generation=0, goal=dict(self.rpc.goal), active=dict(self.state["active_turns"]))

        def save(**fields):
            self.state.update(fields)
            self.state["active_turns"] = dict(self.campaign.active)
            atomic_json(self.directory / "state.json", self.state)

        self.campaign.save = Mock(side_effect=save)
        self.campaign.pause = MethodType(launcher.Campaign.pause, self.campaign)
        self.campaign.save()
        self.preserved = copy.deepcopy({key: self.state[key] for key in ("credit_budget", "native_hold", "resource_hold")})
        for target, kwargs in (
            ("runtime_directory", {"return_value": self.directory}),
            ("_boot_id", {"return_value": "same-boot"}),
            ("_timer_stop", {"return_value": "inactive"}),
            ("process_start", {"side_effect": lambda pid: {os.getpid(): "100", self.rpc.proc.pid: "101"}.get(pid)})):
            patcher = patch.object(control, target, **kwargs)
            patcher.start()
            self.addCleanup(patcher.stop)

    def test_user_stop_interrupts_retained_account_error_owner_without_account_freshness(self):
        report = control.request_stop(self.repo)
        self.assertTrue(report["controller_dispatch_enabled"])
        self.assertEqual(report["stop_request"]["status"], "pending")
        self.assertTrue(control.consume_stop(self.campaign))
        self.assertEqual((self.campaign.stop_reason, self.campaign.stop_now), ("user_stop", True))
        self.assertFalse(self.state["controller_dispatch_enabled"])
        self.assertEqual(self.rpc.goal["status"], "paused")
        interrupted = {tuple(params.values()) for method, params in self.rpc.calls if method == "turn/interrupt"}
        self.assertEqual(interrupted, {("root", "root-turn"), ("event-child", "event-turn"), ("loaded-child", "child-turn")})
        self.assertEqual(self.state["user_stop"]["status"], "consumed")
        self.assertEqual({key: self.state[key] for key in self.preserved}, self.preserved)
        self.rpc.close.assert_not_called()
        self.assertIs(self.campaign.rpc, self.rpc)
        self.assertTrue(self.campaign.args.retain_owner_on_stop)
        self.assertTrue(self.rpc.owner_custody_retained)
        self.assertFalse(self.state["cleanup_verified"])
        self.assertFalse(any(method.startswith("account/") for method, _ in self.rpc.calls))

    def test_repeated_request_and_consumption_do_not_replay_interrupts(self):
        control.request_stop(self.repo)
        control.consume_stop(self.campaign)
        before = (self.directory / control.REQUEST).read_bytes()
        calls = copy.deepcopy(self.rpc.calls)
        control.request_stop(self.repo)
        self.assertTrue(control.consume_stop(self.campaign))
        self.assertEqual((self.directory / control.REQUEST).read_bytes(), before)
        self.assertEqual(self.rpc.calls, calls)

    def test_user_stop_pauses_the_same_blocked_goal(self):
        self.rpc.goal["status"] = "blocked"
        self.campaign.goal = dict(self.rpc.goal)
        control.request_stop(self.repo)
        self.assertTrue(control.consume_stop(self.campaign))
        self.assertEqual(self.rpc.goal["status"], "paused")
        self.assertIn(("thread/goal/set", {"threadId": "root", "status": "paused"}), self.rpc.calls)

    def test_stale_or_wrong_owner_cannot_stop_another_invocation(self):
        control.request_stop(self.repo)
        for change in ({"worker_start": "999"}, {"thread_id": "other-root"},
                       {"log_dir": str(self.directory / "runs/future")}, {"server_start": "999"}):
            original = copy.deepcopy(self.state)
            self.state.update(change)
            with self.subTest(change=change):
                self.assertFalse(control.consume_stop(self.campaign))
                self.assertEqual(self.rpc.calls, [])
            self.state.clear()
            self.state.update(original)
        with patch.object(control, "process_start", return_value="reused-birth"):
            self.assertFalse(control.consume_stop(self.campaign))
        with patch.object(control, "_boot_id", return_value="later-boot"):
            self.assertFalse(control.consume_stop(self.campaign))
        self.assertEqual(self.campaign.stop_reason, "credit_budget_unknown")

    def test_uncertain_interrupt_is_visible_and_never_replayed(self):
        control.request_stop(self.repo)
        self.rpc.failures["turn/interrupt"] = TimeoutError("delivery not confirmed")
        self.assertTrue(control.consume_stop(self.campaign))
        request = read_json(self.directory / control.REQUEST)
        self.assertEqual(request["status"], "uncertain")
        self.assertTrue(request["errors"])
        self.assertTrue(all(row["status"] == "delivery_uncertain" for row in request["interrupts"]))
        calls = copy.deepcopy(self.rpc.calls)
        self.assertTrue(control.consume_stop(self.campaign))
        self.assertEqual(self.rpc.calls, calls)
        self.assertFalse(self.state["controller_dispatch_enabled"])

    def test_explicit_resume_acknowledges_only_this_consumed_stop(self):
        control.request_stop(self.repo)
        control.consume_stop(self.campaign)
        request = read_json(self.directory / control.REQUEST)
        self.state["last_instruction"] = {"status": "accepted_by_server", "control_kind": "resume_same_owner",
                                          "user_stop_request_id": request["id"], "owner": request["owner"]}
        self.campaign.stop_reason, self.campaign.stop_now = None, False
        self.assertFalse(control.consume_stop(self.campaign))
        self.assertIsNone(self.campaign.stop_reason)
        self.state["last_instruction"]["user_stop_request_id"] = "another-stop"
        self.assertTrue(control.consume_stop(self.campaign))
        self.assertEqual(self.campaign.stop_reason, "user_stop")

    def test_absent_server_does_not_clear_stop_or_claim_resource_release(self):
        control.request_stop(self.repo)
        with patch.object(control, "process_start", side_effect=lambda pid: "100" if pid == os.getpid() else None):
            self.assertTrue(control.consume_stop(self.campaign))
        self.assertFalse(self.state["controller_dispatch_enabled"])
        self.assertEqual(self.state["user_stop"]["status"], "uncertain")
        self.assertEqual(self.rpc.calls, [])
        self.assertEqual({key: self.state[key] for key in self.preserved}, self.preserved)

    def test_new_user_stop_after_explicit_same_owner_resume_gets_a_new_request(self):
        control.request_stop(self.repo)
        control.consume_stop(self.campaign)
        prior = read_json(self.directory / control.REQUEST)
        self.state["last_instruction"] = {"status": "accepted_by_server", "control_kind": "resume_same_owner",
                                          "user_stop_request_id": prior["id"], "owner": prior["owner"]}
        self.campaign.stop_reason, self.campaign.stop_now = None, False
        self.campaign.save(stop_reason=None, stop_now=False, controller_dispatch_enabled=True)
        self.rpc.turns = {"root": "new-turn"}
        self.campaign.active = {"root": "new-turn"}
        report = control.request_stop(self.repo)
        self.assertNotEqual(report["stop_request"]["id"], prior["id"])
        self.assertEqual(report["stop_request"]["status"], "pending")
        self.assertTrue(control.consume_stop(self.campaign))
        self.assertEqual(self.campaign.stop_reason, "user_stop")
        self.assertIn(("turn/interrupt", {"threadId": "root", "turnId": "new-turn"}), self.rpc.calls)

    def test_durable_resume_ack_survives_later_instruction_and_binds_exact_owner(self):
        control.request_stop(self.repo)
        control.consume_stop(self.campaign)
        prior = read_json(self.directory / control.REQUEST)
        acknowledgment = {"request_id": prior["id"], "resume": {
            "id": "explicit-resume", "status": "accepted_by_server", "control_kind": "resume_same_owner",
            "user_stop_request_id": prior["id"], "owner": prior["owner"]}}
        self.state["acknowledged_user_stop"] = acknowledgment
        self.state["last_instruction"] = {"id": "later-ordinary-instruction", "status": "accepted_by_server"}
        self.campaign.stop_reason, self.campaign.stop_now = None, False
        calls = copy.deepcopy(self.rpc.calls)
        self.assertFalse(control.consume_stop(self.campaign))
        self.assertEqual(self.rpc.calls, calls)
        self.assertIsNone(self.campaign.stop_reason)
        wrong_owner = copy.deepcopy(acknowledgment)
        wrong_owner["resume"]["owner"]["worker_start"] = "another-birth"
        self.state["acknowledged_user_stop"] = wrong_owner
        self.assertTrue(control.consume_stop(self.campaign))
        self.assertEqual(self.campaign.stop_reason, "user_stop")

    def test_new_stop_after_durable_resume_ack_uses_new_id_and_interrupts_new_turn(self):
        control.request_stop(self.repo)
        control.consume_stop(self.campaign)
        prior = read_json(self.directory / control.REQUEST)
        self.state["acknowledged_user_stop"] = {"request_id": prior["id"], "resume": {
            "id": "explicit-resume", "status": "accepted_by_server", "control_kind": "resume_same_owner",
            "user_stop_request_id": prior["id"], "owner": prior["owner"]}}
        self.state["last_instruction"] = {"id": "ordinary", "status": "accepted_by_server"}
        self.campaign.stop_reason, self.campaign.stop_now = None, False
        self.campaign.save(stop_reason=None, stop_now=False, controller_dispatch_enabled=True)
        self.campaign.active = self.rpc.turns = {"root": "new-after-durable-ack"}
        report = control.request_stop(self.repo)
        self.assertNotEqual(report["stop_request"]["id"], prior["id"])
        self.assertEqual(report["stop_request"]["status"], "pending")
        self.assertTrue(control.consume_stop(self.campaign))
        self.assertIn(("turn/interrupt", {"threadId": "root", "turnId": "new-after-durable-ack"}), self.rpc.calls)

    def test_durable_ack_does_not_clear_an_uncertain_or_errored_stop(self):
        owner = control._owner(self.state)
        receipt = {"status": "accepted_by_server", "control_kind": "resume_same_owner",
                   "user_stop_request_id": "stop-id", "owner": owner}
        state = dict(self.state, stop_now=False, stop_reason=None,
                     acknowledged_user_stop={"request_id": "stop-id", "resume": receipt})
        for request in ({"id": "stop-id", "status": "uncertain", "errors": []},
                        {"id": "stop-id", "status": "consumed", "errors": ["pause unconfirmed"]},
                        {"id": "another-stop", "status": "consumed", "errors": []}):
            with self.subTest(request=request):
                self.assertFalse(control._resumed(request, owner, state))

    def test_resumed_old_stop_never_replaces_a_later_technical_failure(self):
        control.request_stop(self.repo)
        control.consume_stop(self.campaign)
        prior = read_json(self.directory / control.REQUEST)
        self.state["acknowledged_user_stop"] = {"request_id": prior["id"], "resume": {
            "status": "accepted_by_server", "control_kind": "resume_same_owner",
            "user_stop_request_id": prior["id"], "owner": prior["owner"]}}
        self.state["last_instruction"] = {"id": "ordinary-instruction"}
        for reason in ("turn_failed", "server_error", "quota_exhausted", "user_stop"):
            with self.subTest(reason=reason):
                self.campaign.stop_reason, self.campaign.stop_now = reason, True
                self.campaign.save(stop_reason=reason, stop_now=True, controller_dispatch_enabled=False)
                calls = copy.deepcopy(self.rpc.calls)
                self.assertFalse(control.consume_stop(self.campaign))
                self.assertEqual((self.campaign.stop_reason, self.campaign.stop_now), (reason, True))
                self.assertFalse(self.state["controller_dispatch_enabled"])
                self.assertEqual(self.rpc.calls, calls)
                self.assertEqual({key: self.state[key] for key in self.preserved}, self.preserved)

    def test_fresh_stop_after_resumed_technical_failure_is_a_new_request(self):
        control.request_stop(self.repo)
        control.consume_stop(self.campaign)
        prior = read_json(self.directory / control.REQUEST)
        self.state["acknowledged_user_stop"] = {"request_id": prior["id"], "resume": {
            "status": "accepted_by_server", "control_kind": "resume_same_owner",
            "user_stop_request_id": prior["id"], "owner": prior["owner"]}}
        self.campaign.stop_reason, self.campaign.stop_now = "turn_failed", True
        self.campaign.save(stop_reason="turn_failed", stop_now=True, controller_dispatch_enabled=False)
        self.campaign.active = self.rpc.turns = {"root": "remaining-turn"}
        report = control.request_stop(self.repo)
        self.assertNotEqual(report["stop_request"]["id"], prior["id"])
        self.assertEqual(report["stop_request"]["status"], "pending")
        self.assertTrue(control.consume_stop(self.campaign))
        self.assertIn(("turn/interrupt", {"threadId": "root", "turnId": "remaining-turn"}), self.rpc.calls)

    def test_known_unavailable_channel_does_not_claim_interruption_or_release(self):
        control.request_stop(self.repo)
        self.state["transport_failure"] = {"channel_unusable": True}
        control.consume_stop(self.campaign)
        self.assertEqual(self.rpc.calls, [])
        self.assertEqual(self.state["user_stop"]["status"], "uncertain")
        self.assertFalse(self.state["controller_dispatch_enabled"])
        self.assertEqual({key: self.state[key] for key in self.preserved}, self.preserved)

    def test_status_never_infers_cleanup_from_absent_processes(self):
        with patch.object(control, "process_start", return_value=None):
            report = control.status(self.repo)
        self.assertEqual(report["active_turns"], self.state["active_turns"])
        self.assertIn("not runtime cleanup", report["turn_observation"])
        self.assertIsNone(report["worker_birth_observation"])

    def test_only_obsolete_timer_is_stopped_if_active(self):
        with patch.object(control.subprocess, "run", side_effect=[
                SimpleNamespace(returncode=0, stdout="active\n"),
                SimpleNamespace(returncode=0, stdout="")]) as run:
            # Bypass the per-test timer stub, still using only mocked subprocess.
            outcome = self.timer_function()
        self.assertEqual(outcome, "stop_requested")
        self.assertEqual([call.args[0] for call in run.call_args_list], [
            ["systemctl", "--user", "is-active", control.SUPERVISION_TIMER],
            ["systemctl", "--user", "stop", control.SUPERVISION_TIMER]])

    timer_function = staticmethod(control._timer_stop)


if __name__ == "__main__":
    unittest.main()
