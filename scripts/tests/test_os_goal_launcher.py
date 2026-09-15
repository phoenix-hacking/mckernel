#!/usr/bin/env python3
"""Offline launcher lifecycle/transport tests: no Codex inference or OS payloads."""

from collections import deque
from contextlib import redirect_stdout
import importlib.util
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch


SOURCE = Path(__file__).resolve().parents[1] / "run_os_goal.py"
SPEC = importlib.util.spec_from_file_location("os_goal_launcher", SOURCE)
launcher = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(launcher)


def goal(status="active", objective=launcher.OBJECTIVE):
    return {"threadId": "test-thread", "objective": objective, "status": status,
            "tokensUsed": 1234, "timeUsedSeconds": 80, "tokenBudget": None,
            "createdAt": 1, "updatedAt": 2}


class FakeRPC:
    """Simulates the server's goal engine, including unsolicited continuation turns."""
    def __init__(self, args, live_goal=None, steps=()):
        self.args, self.goal = args, live_goal
        self.steps, self.calls = deque(steps), []
        self.on_event = None
        self.closed = False
        self.turns = {}
        self.bad_config = False

    def factory(self, argv, log_dir, event):
        self.on_event = event
        return self

    def emit(self, method, params):
        self.on_event({"method": method, "params": params})

    def started(self, ident="turn-1", thread="test-thread"):
        self.turns[thread] = {"id": ident, "items": [], "status": "inProgress"}
        self.emit("turn/started", {"threadId": thread, "turn": self.turns[thread]})

    def completed(self, thread="test-thread"):
        turn = dict(self.turns.pop(thread))
        turn["status"] = "completed"
        self.emit("turn/completed", {"threadId": thread, "turn": turn})

    def status(self, status):
        self.goal["status"] = status
        self.emit("thread/goal/updated", {"threadId": "test-thread", "goal": dict(self.goal)})

    def send(self, message):
        assert message["method"] == "initialized"

    def call(self, method, params, **kwargs):
        self.calls.append((method, params))
        if method == "initialize":
            return {}
        if method == "config/read":
            return {"config": {"model": self.args.model, "model_reasoning_effort": self.args.effort,
                "approval_policy": "never", "features": {"goals": True}, "agents": {
                    "enabled": True, "max_concurrent_threads_per_session": 4 if self.bad_config else 3,
                    "max_depth": 1, "default_subagent_model": "gpt-5.6-luna",
                    "default_subagent_reasoning_effort": "low"}}}
        if method == "model/list":
            return {"data": [{"model": model, "supportedReasoningEfforts": [
                {"reasoningEffort": effort} for effort in ["low", "medium", "high"]]}
                for model in [self.args.model, "gpt-5.6-luna", "gpt-6-astra"]], "nextCursor": None}
        if method in ("thread/start", "thread/resume"):
            if method == "thread/resume" and self.goal["status"] == "active":
                self.started()
            return {"thread": {"id": "test-thread"}, "model": self.args.model, "reasoningEffort": self.args.effort,
                    "sandbox": {"type": "dangerFullAccess"}, "approvalPolicy": "never"}
        if method == "thread/goal/get":
            return {"goal": dict(self.goal) if self.goal else None}
        if method == "thread/goal/set":
            if not self.goal:
                self.goal = goal(objective=params["objective"])
            self.goal.update({key: params[key] for key in ("status", "tokenBudget") if key in params})
            self.status(self.goal["status"])
            if self.goal["status"] == "active" and "test-thread" not in self.turns:
                self.started()
            return {"goal": dict(self.goal)}
        if method == "turn/steer":
            self.completed()
            return {}
        if method == "thread/loaded/list":
            return {"data": list(self.turns), "nextCursor": None}
        if method == "thread/turns/list":
            assert params["itemsView"] == "notLoaded"
            return {"data": [self.turns[params["threadId"]]], "nextCursor": None}
        if method == "turn/interrupt":
            self.completed(params["threadId"])
            return {}
        raise AssertionError("Unexpected RPC: " + method)

    def pump(self, timeout=1):
        if not self.steps:
            raise RuntimeError("Fake server exhausted its finite scenario")
        self.steps.popleft()(self)

    def close(self):
        self.closed = True


class CampaignTests(unittest.TestCase):
    all_calls = []

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="os-goal-test-")
        self.directory = Path(self.temp.name)
        self.args = launcher.arguments(["--hours", "0"])

    def tearDown(self):
        self.temp.cleanup()

    def saved(self, saved_goal):
        launcher.atomic_json(self.directory / "state.json", {"schema_version": 1,
            "repo": str(self.directory), "thread_id": "test-thread", "goal": saved_goal})

    def run_campaign(self, rpc, expected):
        campaign = launcher.Campaign(self.args, self.directory, self.directory, rpc.factory)
        with redirect_stdout(io.StringIO()):
            self.assertEqual(campaign.run(), expected)
        self.assertTrue(rpc.closed)
        self.all_calls.extend(rpc.calls)
        return json.loads((self.directory / "state.json").read_text())

    def test_sol_and_bounded_luna_defaults(self):
        self.assertEqual(self.args.model, "gpt-5.6-sol")
        self.assertIsNone(self.args.token_budget)
        command = launcher.server_argv(self.args, self.directory)
        self.assertIn("agents.max_depth=1", command)
        self.assertNotIn("--dangerously-bypass-approvals-and-sandbox", command)

    def test_new_goal_continues_multiple_turns_without_client_prompt_loop(self):
        def next_turn(rpc):
            rpc.completed()
            rpc.started("turn-2")
        def finish(rpc):
            rpc.completed()
            rpc.status("blocked")
        rpc = FakeRPC(self.args, steps=[next_turn, finish])
        state = self.run_campaign(rpc, 20)
        self.assertEqual(state["goal"]["status"], "blocked")
        self.assertEqual(state["last_turn"]["id"], "turn-2")
        self.assertEqual(sum(m == "thread/start" for m, p in rpc.calls), 1)
        self.assertEqual(sum(m == "thread/goal/set" for m, p in rpc.calls), 1)
        self.assertFalse(any(m == "turn/start" for m, p in rpc.calls))

    def test_resume_preserves_thread_objective_and_usage(self):
        self.saved(goal("usageLimited"))
        rpc = FakeRPC(self.args, goal("usageLimited"), [lambda r: (r.completed(), r.status("blocked"))])
        state = self.run_campaign(rpc, 20)
        resumes = [p for m, p in rpc.calls if m == "thread/resume"]
        self.assertEqual(resumes[0]["threadId"], "test-thread")
        self.assertTrue(resumes[0]["excludeTurns"])
        self.assertEqual(state["goal"]["tokensUsed"], 1234)
        self.assertFalse(any(m == "thread/start" or "objective" in p or "tokenBudget" in p
                             for m, p in rpc.calls))

    def test_quota_stops_without_another_inference_attempt(self):
        def quota(rpc):
            rpc.status("usageLimited")
            rpc.emit("error", {"threadId": "test-thread", "turnId": "turn-1",
                "willRetry": True, "error": {"message": "quota", "codexErrorInfo": "usageLimitExceeded"}})
        rpc = FakeRPC(self.args, steps=[quota])
        state = self.run_campaign(rpc, 21)
        self.assertEqual(state["goal"]["status"], "usageLimited")
        self.assertEqual(state["stop_reason"], "quota_or_rate_limit")
        self.assertEqual(sum(m == "thread/goal/set" and p.get("status") == "active" for m, p in rpc.calls), 1)
        self.assertFalse(state["cleanup_verified"])

    def test_active_resume_is_not_replaced_or_started_twice(self):
        self.saved(goal())
        rpc = FakeRPC(self.args, goal(), [lambda r: (r.completed(), r.status("blocked"))])
        self.run_campaign(rpc, 20)
        self.assertFalse(any(m in ("thread/start", "thread/goal/set", "turn/start") for m, p in rpc.calls))

    def test_completed_goal_does_not_resume(self):
        self.saved(goal("complete"))
        rpc = FakeRPC(self.args, goal("complete"))
        self.run_campaign(rpc, 0)
        self.assertFalse(any(m in ("thread/start", "thread/resume", "thread/goal/set") for m, p in rpc.calls))

    def test_budget_limited_requires_explicit_new_budget(self):
        self.saved(goal("budgetLimited"))
        rpc = FakeRPC(self.args, goal("budgetLimited"))
        self.run_campaign(rpc, 22)
        self.assertFalse(any(m in ("thread/resume", "thread/goal/set") for m, p in rpc.calls))

    def test_different_goal_is_neither_resumed_nor_paused(self):
        self.saved(goal())
        rpc = FakeRPC(self.args, goal(objective="Another user objective"))
        state = self.run_campaign(rpc, 1)
        self.assertIn("different objective", state["last_error"])
        self.assertFalse(any(m in ("thread/resume", "thread/goal/set", "turn/interrupt") for m, p in rpc.calls))

    def test_cleared_goal_is_not_silently_recreated(self):
        self.saved(goal())
        rpc = FakeRPC(self.args)
        state = self.run_campaign(rpc, 1)
        self.assertIn("cleared", state["last_error"])
        self.assertFalse(any(m in ("thread/start", "thread/resume", "thread/goal/set") for m, p in rpc.calls))

    def test_misconfigured_concurrency_fails_before_thread_start(self):
        rpc = FakeRPC(self.args)
        rpc.bad_config = True
        self.run_campaign(rpc, 1)
        self.assertFalse(any(m.startswith("thread/") for m, p in rpc.calls))

    def test_window_pauses_and_requests_checkpoint(self):
        self.args.hours = 1 / 3600
        self.args.grace_seconds = 1
        clock = [100.0]
        rpc = FakeRPC(self.args, steps=[lambda r: clock.__setitem__(0, 100.75)])
        with patch.object(launcher.time, "monotonic", side_effect=lambda: clock[0]):
            state = self.run_campaign(rpc, 10)
        self.assertEqual(state["goal"]["status"], "paused")
        self.assertEqual(state["stop_reason"], "work_window")
        self.assertEqual(sum(m == "turn/steer" for m, p in rpc.calls), 1)
        self.assertEqual(state["active_turns"], {})

    def test_stop_discovers_unobserved_child_and_interrupts_it(self):
        def stop(rpc):
            rpc.turns["child-thread"] = {"id": "child-turn", "items": [], "status": "inProgress"}
            rpc.completed()
            rpc.status("blocked")
        rpc = FakeRPC(self.args, steps=[stop])
        self.run_campaign(rpc, 20)
        self.assertIn(("turn/interrupt", {"threadId": "child-thread", "turnId": "child-turn"}), rpc.calls)

    def test_interrupt_requests_checkpoint_without_completing_goal(self):
        rpc = FakeRPC(self.args, steps=[lambda r: r.on_event.__self__.on_signal(2, None)])
        state = self.run_campaign(rpc, 10)
        self.assertEqual(state["stop_reason"], "signal_2")
        self.assertEqual(state["goal"]["status"], "paused")
        self.assertEqual(sum(m == "turn/steer" for m, p in rpc.calls), 1)

    def test_missing_automatic_continuation_stops_instead_of_prompt_loop(self):
        clock = [100.0]
        def idle(rpc):
            rpc.completed()
            clock[0] = 221.0
        rpc = FakeRPC(self.args, steps=[idle])
        with patch.object(launcher.time, "monotonic", side_effect=lambda: clock[0]):
            state = self.run_campaign(rpc, 24)
        self.assertEqual(state["stop_reason"], "active_goal_did_not_continue")
        self.assertFalse(any(m == "turn/start" for m, p in rpc.calls))

    def test_disconnect_keeps_cursor_and_reports_failure(self):
        rpc = FakeRPC(self.args)
        state = self.run_campaign(rpc, 1)
        self.assertEqual(state["thread_id"], "test-thread")
        self.assertEqual(state["phase"], "stopped")
        self.assertEqual(state["goal"]["status"], "paused")

    def test_lease_and_corrupted_state_fail_closed(self):
        lease = launcher.Lease(self.directory / "run.lock")
        try:
            with self.assertRaisesRegex(RuntimeError, "holds the repository lease"):
                launcher.Lease(self.directory / "run.lock")
        finally:
            lease.close()
        state_path = self.directory / "state.json"
        state_path.write_text("{incomplete")
        with self.assertRaises(ValueError):
            launcher.Campaign(self.args, self.directory, self.directory)
        self.assertEqual(state_path.read_text(), "{incomplete")

    @classmethod
    def tearDownClass(cls):
        # Optional validation against schemas emitted by the installed Codex binary.
        directory = os.environ.get("OS_GOAL_PROTOCOL_SCHEMA")
        if directory:
            import jsonschema
            files = {"initialize": "v1/InitializeParams.json", "config/read": "v2/ConfigReadParams.json",
                "model/list": "v2/ModelListParams.json", "thread/start": "v2/ThreadStartParams.json",
                "thread/resume": "v2/ThreadResumeParams.json", "thread/goal/get": "v2/ThreadGoalGetParams.json",
                "thread/goal/set": "v2/ThreadGoalSetParams.json", "turn/steer": "v2/TurnSteerParams.json",
                "thread/loaded/list": "v2/ThreadLoadedListParams.json",
                "thread/turns/list": "v2/ThreadTurnsListParams.json", "turn/interrupt": "v2/TurnInterruptParams.json"}
            schemas = {method: json.loads((Path(directory) / name).read_text()) for method, name in files.items()}
            for method, params in cls.all_calls:
                jsonschema.Draft7Validator(schemas[method]).validate(params)


class TransportTests(unittest.TestCase):
    def test_fragmented_events_and_unsupported_approval_are_handled_without_approval(self):
        source = r'''
import json,sys,time
request=json.loads(sys.stdin.readline())
event={'method':'item/permissions/requestApproval','id':99,'params':{'threadId':'test-thread'}}
encoded=json.dumps(event)+'\n'
sys.stdout.write(encoded[:12]); sys.stdout.flush()
time.sleep(0.01)
sys.stdout.write(encoded[12:]); sys.stdout.flush()
reply=json.loads(sys.stdin.readline())
sys.stdout.write(json.dumps({'id':request['id'],'result':{'reply':reply}})+'\n'); sys.stdout.flush()
sys.stdin.read()
'''
        with tempfile.TemporaryDirectory(prefix="os-goal-transport-") as temp:
            events = []
            rpc = launcher.RPC([sys.executable, "-u", "-c", source], Path(temp), events.append)
            try:
                result = rpc.call("initialize", {}, timeout=5)
                self.assertIn("error", result["reply"])
                self.assertNotIn("result", result["reply"])
                self.assertEqual(events[0]["id"], 99)
            finally:
                rpc.close()


if __name__ == "__main__":
    unittest.main()
