#!/usr/bin/env python3
"""Offline launcher lifecycle/transport tests: no Codex inference or OS payloads."""

from collections import deque
from contextlib import redirect_stderr, redirect_stdout
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch


SOURCE = Path(__file__).resolve().parents[1] / "run_os_goal.py"
sys.path.insert(0, str(SOURCE.parent))
SPEC = importlib.util.spec_from_file_location("os_goal_launcher", SOURCE)
launcher = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(launcher)
ASKPASS_SPEC = importlib.util.spec_from_file_location("os_goal_askpass", SOURCE.with_name("os_goal_sudo_askpass.py"))
askpass = importlib.util.module_from_spec(ASKPASS_SPEC)
ASKPASS_SPEC.loader.exec_module(askpass)
WATCH_SPEC = importlib.util.spec_from_file_location("os_goal_watch", SOURCE.with_name("watch_os_goal.py"))
watcher = importlib.util.module_from_spec(WATCH_SPEC)
WATCH_SPEC.loader.exec_module(watcher)


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
        self.bad_environment = False
        self.worker_model = "gpt-6.1-sol"
        self.worker_effort = "medium"
        self.models = {"gpt-6.1-sol": ["low", "medium", "high"]}
        self.account_type = "chatgpt"
        self.limits = {"primary": {"usedPercent": 0, "windowDurationMins": 10080},
                       "credits": {"hasCredits": False, "balance": "0"}, "planType": "pro"}

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
                "shell_environment_policy": {"set": {} if self.bad_environment else
                    launcher.resource_environment(launcher.launch_resources(self.args, launcher.REPO))},
                "approval_policy": "never", "features": {"goals": True}, "agents": {
                    "enabled": True, "max_concurrent_threads_per_session":
                        launcher.launch_resources(self.args, launcher.REPO)["max_agents"] + int(self.bad_config),
                    "max_depth": 1, "default_subagent_model": self.worker_model,
                    "default_subagent_reasoning_effort": self.worker_effort}}}
        if method == "model/list":
            return {"data": [{"model": model, "supportedReasoningEfforts": [
                {"reasoningEffort": effort} for effort in efforts]}
                for model, efforts in self.models.items()], "nextCursor": None}
        if method == "account/read":
            return {"account": {"type": self.account_type}}
        if method == "account/rateLimits/read":
            return {"rateLimits": self.limits}
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
        if method == "turn/start":
            assert params["threadId"] not in self.turns, "Cannot seed an already active turn"
            self.started("startup-turn-1", params["threadId"])
            return {"turn": dict(self.turns[params["threadId"]])}
        if method == "turn/steer":
            self.completed()
            return {}
        if method == "thread/loaded/list":
            return {"data": list(self.turns), "nextCursor": None}
        if method == "thread/turns/list":
            assert params["itemsView"] == "notLoaded"
            turn = self.turns.get(params["threadId"])
            return {"data": [dict(turn)] if turn else [], "nextCursor": None}
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
        self.args = launcher.arguments(["--hours", "0", "--agent-windows", "off"])

    def tearDown(self):
        self.temp.cleanup()

    def saved(self, saved_goal):
        launcher.atomic_json(self.directory / "state.json", {"schema_version": 1,
            "repo": str(self.directory), "thread_id": "test-thread", "goal": saved_goal})

    def startup_arguments(self, *extra):
        note = self.directory / "startup-note.txt"
        note.write_text("Resume the OS work with GPT-6.1; reconcile the historical preparation hold.")
        digest = hashlib.sha256(note.read_bytes()).hexdigest()
        self.args = launcher.arguments(["--hours", "0", "--agent-windows", "off",
            "--startup-instruction-file", str(note), "--startup-instruction-sha256", digest, *extra])
        return note.read_text(), digest

    def run_campaign(self, rpc, expected):
        campaign = launcher.Campaign(self.args, self.directory, self.directory, rpc.factory)
        with redirect_stdout(io.StringIO()):
            self.assertEqual(campaign.run(), expected)
        self.assertTrue(rpc.closed)
        self.all_calls.extend(rpc.calls)
        return json.loads((self.directory / "state.json").read_text())

    def test_gpt_61_coordinator_and_worker_defaults_keep_aggressive_limits(self):
        self.assertEqual(self.args.model, "gpt-6.1-sol")
        self.assertEqual(self.args.effort, "medium")
        self.assertIsNone(self.args.token_budget)
        self.assertEqual(self.args.profile, "aggressive")
        self.assertEqual(self.args.stall_seconds, 0)
        command = launcher.server_argv(self.args, self.directory)
        resources = launcher.launch_resources(self.args, self.directory)
        self.assertIn("agents.max_concurrent_threads_per_session=" + str(resources["max_agents"]), command)
        self.assertIn('shell_environment_policy.set.CARGO_BUILD_JOBS="' + str(resources["build_jobs"]) + '"', command)
        self.assertIn("agents.max_depth=1", command)
        self.assertIn('model="gpt-6.1-sol"', command)
        self.assertIn('model_reasoning_effort="medium"', command)
        self.assertIn('agents.default_subagent_model="gpt-6.1-sol"', command)
        self.assertIn('agents.default_subagent_reasoning_effort="medium"', command)
        self.assertIn('sandbox_mode="danger-full-access"', command)
        self.assertIn('approval_policy="never"', command)
        self.assertNotIn("--dangerously-bypass-approvals-and-sandbox", command)

    def test_model_routing_uses_only_gpt_61_for_every_role(self):
        routing = launcher.model_routing(self.args)
        self.assertEqual(routing, {
            "dispatcher": {"model": "gpt-6.1-sol", "effort": "medium"},
            "default_worker": {"model": "gpt-6.1-sol", "effort": "medium"},
            "complex_worker": {"model": "gpt-6.1-sol", "effort": "high"},
            "auditor": {"model": "gpt-6.1-sol", "effort": "low"},
            "reviewer": {"model": "gpt-6.1-sol", "effort": "high"},
        })
        self.assertTrue(all(selection["model"] == "gpt-6.1-sol" for selection in routing.values()))

    def test_coordinator_rejects_other_models_before_launch(self):
        for model in ("gpt-5.6-sol", "gpt-5.6-luna", "gpt-6-astra", "unknown"):
            with self.subTest(model=model), redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                launcher.arguments(["--model", model])

    def test_coordinator_rejects_efforts_above_high(self):
        for effort in ("xhigh", "max", "ultra"):
            with self.subTest(effort=effort), redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                launcher.arguments(["--effort", effort])

    def test_coordinator_effort_override_keeps_all_roles_on_gpt_61(self):
        for effort in ("low", "high"):
            with self.subTest(effort=effort):
                self.args = launcher.arguments(["--model", "gpt-6.1-sol", "--effort", effort,
                                                "--agent-windows", "off"])
                rpc = FakeRPC(self.args)
                settings = launcher.preflight(rpc, self.args, self.directory)
                self.assertEqual(settings["model"], "gpt-6.1-sol")
                self.assertEqual(settings["effort"], effort)
                self.assertEqual(settings["model_routing"]["dispatcher"],
                                 {"model": "gpt-6.1-sol", "effort": effort})
                self.assertEqual(settings["model_routing"]["default_worker"],
                                 {"model": "gpt-6.1-sol", "effort": "medium"})
                self.assertEqual(settings["agents"]["default_subagent_model"], "gpt-6.1-sol")
                self.assertFalse(any(method.startswith("thread/") for method, _ in rpc.calls))

    def test_live_instruction_is_queued_and_delivered_to_active_coordinator(self):
        campaign = launcher.Campaign(self.args, self.directory, self.directory)
        try:
            campaign.state["thread_id"] = "test-thread"
            campaign.controlled = True
            campaign.goal = goal()
            campaign.active["test-thread"] = "turn-1"
            campaign.save()
            ident = launcher.queue_instruction(self.directory, "Prioritize the next app smoke")
            rpc = FakeRPC(self.args, goal())
            rpc.on_event = campaign.event
            rpc.turns["test-thread"] = {"id": "turn-1", "items": [], "status": "inProgress"}
            campaign.rpc = rpc
            campaign.deliver_instruction()
            steering = [params for method, params in rpc.calls if method == "turn/steer"]
            self.assertEqual(len(steering), 1)
            self.assertEqual(steering[0]["expectedTurnId"], "turn-1")
            self.assertIn("Prioritize the next app smoke", steering[0]["input"][0]["text"])
            receipt = json.loads((self.directory / "instructions" / "delivered" /
                                  (ident + ".json")).read_text())
            self.assertEqual(receipt["status"], "accepted_by_server")
            self.assertFalse(list((self.directory / "instructions" / "pending").glob("*.json")))
            self.assertFalse(list((self.directory / "instructions" / "sending").glob("*.json")))
        finally:
            campaign.output.close()

    def test_live_instruction_waits_during_checkpoint_and_rejects_invalid_text(self):
        campaign = launcher.Campaign(self.args, self.directory, self.directory)
        try:
            campaign.state["thread_id"] = "test-thread"
            campaign.controlled = True
            campaign.goal = goal()
            campaign.active["test-thread"] = "turn-1"
            campaign.save()
            with self.assertRaises(ValueError):
                launcher.queue_instruction(self.directory, "   ")
            with self.assertRaises(ValueError):
                launcher.queue_instruction(self.directory, "x" * 8193)
            ident = launcher.queue_instruction(self.directory, "Continue after checkpoint")
            campaign.checkpoint_requested = True
            campaign.rpc = FakeRPC(self.args, goal())
            campaign.deliver_instruction()
            self.assertTrue((self.directory / "instructions" / "pending" /
                             (ident + ".json")).exists())
            self.assertFalse(campaign.rpc.calls)
        finally:
            campaign.output.close()

    def test_progress_report_leads_with_practical_checks_and_preserves_live_runner(self):
        campaign = launcher.Campaign(self.args, self.directory, self.directory)
        try:
            campaign.state["thread_id"] = "test-thread"
            campaign.active.update({"test-thread": "turn-1", "child": "turn-2"})
            campaign.save(phase="running", goal=goal(), settings={"resources": {"max_agents": 8}})
            dashboard = self.directory / launcher.PLAN_REL / "PROGRESS.md"
            dashboard.parent.mkdir(parents=True)
            dashboard.write_text("- Dashboard refreshed: yesterday\n"
                                 "- Native production gates: 6/130\n"
                                 "| M02 | comparison | partial |\n")
            tracker = dashboard.with_name("practical-milestones.json")
            tracker.write_text(json.dumps({
                "scope_id": "practical-kernel-apps-v1-20261017", "effective_date": "2026-10-17",
                "milestones": [{"checks": [{"status": status} for status in
                                            ("complete", "open", "open", "unassessed")]}]}))
            report = launcher.progress_report(self.directory, self.directory)
            self.assertTrue(report.startswith("Practical exit checks (recorded): 1 complete, 2 open, 1 unassessed, 4 total."))
            self.assertIn("active child agents: 1/8", report)
            self.assertIn("filesystem time; not an evidence date", report)
            self.assertIn("Source: " + str(tracker), report)
            self.assertIn("Historical / DEFERRED qualification", report)
            self.assertNotIn("6/130", report)
            self.assertNotIn("| M02 | comparison", report)
            self.assertNotIn("%", report)
            for contents in (None, "{", json.dumps({"scope_id": "other"}),
                             json.dumps({"scope_id": "practical-kernel-apps-v1-20261017",
                                         "milestones": [{"checks": [{"status": "passed"}]}]})):
                if contents is None:
                    tracker.unlink()
                else:
                    tracker.write_text(contents)
                report = launcher.progress_report(self.directory, self.directory)
                self.assertTrue(report.startswith("Practical exit checks: unavailable"))
                self.assertIn("active child agents: 1/8", report)
                self.assertNotIn("6/130", report)
        finally:
            campaign.output.close()

    def test_default_run_has_no_deadline_or_recovery_limit(self):
        self.args = launcher.arguments([])
        self.assertEqual(self.args.hours, 0)
        self.assertEqual(self.args.max_restarts, -1)
        clock = [100.0]
        rpc = FakeRPC(self.args, steps=[
            lambda r: clock.__setitem__(0, 100.0 + 120 * 24 * 3600),
            lambda r: (r.completed(), r.status("complete"))])
        with patch.object(launcher.time, "monotonic", side_effect=lambda: clock[0]):
            state = self.run_campaign(rpc, 0)
        self.assertIsNone(state["stop_reason"])
        self.assertFalse(any(m == "turn/steer" for m, p in rpc.calls))

    def test_blocked_resume_replaces_historical_window_instructions(self):
        self.saved(goal("blocked"))
        self.args.recovered = True
        rpc = FakeRPC(self.args, goal("blocked"), [lambda r: (r.completed(), r.status("complete"))])
        state = self.run_campaign(rpc, 0)
        params = next(p for m, p in rpc.calls if m == "thread/resume")
        self.assertIn("no time limit", params["developerInstructions"])
        self.assertIn("historical and do not pause", params["developerInstructions"])
        self.assertIn("Reconcile source changes", params["developerInstructions"])
        self.assertEqual(state["goal"]["objective"], launcher.OBJECTIVE)
        self.assertEqual(state["goal"]["tokensUsed"], 1234)
        self.assertFalse(any("objective" in p or "tokenBudget" in p for m, p in rpc.calls))

    def test_explicit_window_instructions_preserve_user_limit(self):
        self.args.hours = 2
        campaign = launcher.Campaign(self.args, self.directory, self.directory)
        try:
            self.assertIn("finite work window", campaign.instructions())
            self.assertNotIn("no time limit", campaign.instructions())
        finally:
            campaign.output.close()

    def test_startup_instruction_precedes_saved_goal_resume_and_activation(self):
        self.saved(goal("paused"))
        self.args.startup_instruction = "Reconcile the old preparation hold before dispatch."
        rpc = FakeRPC(self.args, goal("paused"), [lambda r: (r.completed(), r.status("complete"))])
        state = self.run_campaign(rpc, 0)
        params = next(p for m, p in rpc.calls if m == "thread/resume")
        self.assertTrue(params["developerInstructions"].startswith("Current user instruction for this invocation"))
        self.assertIn(self.args.startup_instruction, params["developerInstructions"])
        methods = [m for m, p in rpc.calls]
        self.assertLess(methods.index("thread/resume"), methods.index("thread/goal/set"))
        self.assertEqual(state["goal"]["objective"], launcher.OBJECTIVE)
        self.assertEqual(state["goal"]["tokensUsed"], 1234)

    def test_instructions_prioritize_diagnostic_app_pilot_without_acceptance_credit(self):
        campaign = launcher.Campaign(self.args, self.directory, self.directory)
        try:
            instructions = campaign.instructions()
            for expected in ("functional, stable, app-testable McKernel core",
                             "fast diagnostic loop", "smallest real McKernel startup app",
                             "diagnostic result is never formal application",
                             "already reviewed reusable profile",
                             "do not create a fresh packet, archive or",
                             "independent review for each edit or test vector",
                             "applicable independent execution release",
                             "isolation, resource lease and cleanup requirements",
                             "independent kernel/Rust repair, candidate build binding",
                             "count of real guest apps and current-candidate builds"):
                self.assertIn(expected, instructions)
            self.assertEqual(launcher.OBJECTIVE, goal()["objective"])
        finally:
            campaign.output.close()

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
        start = next(p for m, p in rpc.calls if m == "thread/start")
        self.assertEqual(start["sandbox"], "danger-full-access")
        self.assertEqual(start["approvalPolicy"], "never")
        self.assertEqual(sum(m == "thread/goal/set" for m, p in rpc.calls), 1)
        self.assertFalse(any(m == "turn/start" for m, p in rpc.calls))

    def test_resume_preserves_thread_objective_and_usage(self):
        self.saved(goal("usageLimited"))
        rpc = FakeRPC(self.args, goal("usageLimited"), [lambda r: (r.completed(), r.status("blocked"))])
        state = self.run_campaign(rpc, 20)
        resumes = [p for m, p in rpc.calls if m == "thread/resume"]
        self.assertEqual(resumes[0]["threadId"], "test-thread")
        self.assertTrue(resumes[0]["excludeTurns"])
        self.assertEqual(resumes[0]["sandbox"], "danger-full-access")
        self.assertEqual(resumes[0]["approvalPolicy"], "never")
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
        self.assertEqual(state["stop_reason"], "quota_exhausted")
        self.assertEqual(sum(m == "thread/goal/set" and p.get("status") == "active" for m, p in rpc.calls), 1)
        self.assertFalse(state["cleanup_verified"])

    def test_quota_survives_later_failed_turn_and_blocked_events(self):
        def quota(rpc):
            rpc.emit("error", {"threadId": "test-thread", "willRetry": False,
                "error": {"message": "quota", "codexErrorInfo": "usageLimitExceeded"}})
            rpc.emit("turn/completed", {"threadId": "test-thread", "turn": {
                "id": "turn-1", "status": "failed", "error": {"message": "failed"}}})
            rpc.status("blocked")
        rpc = FakeRPC(self.args, steps=[quota])
        state = self.run_campaign(rpc, 21)
        self.assertEqual(state["stop_reason"], "quota_exhausted")
        self.assertFalse(watcher.should_restart(21, state, watchdog=True))

    def test_zero_credit_account_update_preserves_included_plan_allowance(self):
        def no_credits(rpc):
            rpc.emit("account/rateLimits/updated", {"rateLimits": {
                "primary": {"usedPercent": 53},
                "credits": {"hasCredits": False, "unlimited": False, "balance": "0"},
                "planType": "pro"}})
            rpc.completed()
            rpc.status("complete")
        rpc = FakeRPC(self.args, steps=[no_credits])
        state = self.run_campaign(rpc, 0)
        self.assertIsNone(state["stop_reason"])
        self.assertEqual(state["last_rate_limits"]["primary"]["usedPercent"], 53)
        self.assertEqual(state["last_rate_limits"]["credits"]["balance"], "0")

    def test_included_limit_guard_stops_before_starting_inference(self):
        for percent in (100,):
            with self.subTest(percent=percent):
                rpc = FakeRPC(self.args)
                rpc.limits["primary"]["usedPercent"] = percent
                state = self.run_campaign(rpc, 21)
                self.assertEqual(state["stop_reason"], "included_usage_guard")
                self.assertFalse(any(m in ("thread/start", "thread/resume", "thread/goal/set")
                                     for m, _ in rpc.calls))
                self.assertFalse(watcher.should_restart(21, state))

    def credit_arguments(self):
        self.args.credit_budget = "100"
        self.args.credit_run_id = "a" * 32

    def test_explicit_prepaid_budget_allows_exhausted_included_plan(self):
        self.credit_arguments()
        rpc = FakeRPC(self.args, steps=[lambda r: (r.completed(), r.status("complete"))])
        rpc.limits = {"primary": {"usedPercent": 100},
                      "credits": {"hasCredits": True, "unlimited": False, "balance": "1000"}}
        state = self.run_campaign(rpc, 0)
        self.assertIsNone(state["stop_reason"])
        self.assertEqual(state["credit_budget"]["budget"], "100")
        self.assertTrue(any(m == "thread/start" for m, _ in rpc.calls))
        instructions = next(p["developerInstructions"] for m, p in rpc.calls if m == "thread/start")
        self.assertIn("up to 100 existing prepaid credits", instructions)

    def test_paid_budget_threshold_stops_without_automatic_recovery(self):
        self.credit_arguments()
        def spend(rpc):
            rpc.emit("account/rateLimits/updated", {"rateLimits": {
                "primary": {"usedPercent": 100},
                "credits": {"hasCredits": True, "unlimited": False, "balance": "900"}}})
        rpc = FakeRPC(self.args, steps=[spend])
        rpc.limits = {"primary": {"usedPercent": 100},
                      "credits": {"hasCredits": True, "unlimited": False, "balance": "1000"}}
        state = self.run_campaign(rpc, 21)
        self.assertEqual(state["stop_reason"], "credit_budget_exhausted")
        self.assertEqual(state["credit_budget"]["spent"], "100")
        self.assertFalse(watcher.should_restart(21, state, watchdog=True))

    def test_paid_mode_does_not_ignore_real_service_quota_error(self):
        self.credit_arguments()
        def denied(rpc):
            rpc.emit("error", {"threadId": "test-thread", "turnId": "turn-1",
                     "error": {"codexErrorInfo": "usageLimitExceeded"}, "willRetry": False})
        rpc = FakeRPC(self.args, steps=[denied])
        rpc.limits = {"primary": {"usedPercent": 100},
                      "credits": {"hasCredits": True, "unlimited": False, "balance": "1000"}}
        state = self.run_campaign(rpc, 21)
        self.assertEqual(state["stop_reason"], "quota_exhausted")
        self.assertFalse(watcher.should_restart(21, state))

    def test_paid_mode_unknown_balance_refuses_before_inference(self):
        self.credit_arguments()
        rpc = FakeRPC(self.args)
        rpc.limits = {"primary": {"usedPercent": 100}, "credits": {"hasCredits": False}}
        state = self.run_campaign(rpc, 21)
        self.assertEqual(state["stop_reason"], "credit_budget_unknown")
        self.assertFalse(any(m in ("thread/start", "thread/resume") for m, _ in rpc.calls))

    def test_paid_refresh_reads_balance_without_unsolicited_events(self):
        self.credit_arguments()
        campaign = launcher.Campaign(self.args, self.directory, self.directory)
        try:
            initial = {"primary": {"usedPercent": 100},
                       "credits": {"hasCredits": True, "unlimited": False, "balance": "1000"}}
            campaign.record_rate_limits(initial)
            campaign.rpc = Mock()
            current = dict(initial, credits=dict(initial["credits"], balance="900"))
            campaign.rpc.call.return_value = {"rateLimits": current}
            campaign.refresh_credit_budget()
            campaign.rpc.call.assert_called_once_with("account/rateLimits/read", {}, timeout=10)
            self.assertEqual(campaign.stop_reason, "credit_budget_exhausted")
            self.assertTrue(campaign.stop_now)
        finally:
            campaign.output.close()

    def test_paid_refresh_failure_stops_instead_of_waiting_for_notifications(self):
        self.credit_arguments()
        campaign = launcher.Campaign(self.args, self.directory, self.directory)
        try:
            campaign.rpc = Mock()
            campaign.rpc.call.side_effect = TimeoutError("account unavailable")
            campaign.refresh_credit_budget()
            self.assertEqual(campaign.stop_reason, "credit_budget_unknown")
            self.assertTrue(campaign.stop_now)
        finally:
            campaign.output.close()

    def test_included_usage_through_99_percent_uses_full_included_allowance(self):
        self.assertEqual(launcher.INCLUDED_USAGE_STOP_PERCENT, 100)
        for percent in (97, 99, 99.9):
            with self.subTest(percent=percent):
                # Each successful campaign leaves a completed saved goal.
                self.directory = Path(self.temp.name) / ("usage-" + str(percent))
                self.directory.mkdir()
                rpc = FakeRPC(self.args, steps=[lambda r: (r.completed(), r.status("complete"))])
                rpc.limits["primary"]["usedPercent"] = percent
                state = self.run_campaign(rpc, 0)
                self.assertIsNone(state["stop_reason"])
                self.assertTrue(any(method == "thread/start" for method, _ in rpc.calls))

    def test_invalid_included_usage_refuses_inference(self):
        for percent in (float("nan"), float("inf"), -1, 101, True, None, "97"):
            with self.subTest(percent=percent):
                rpc = FakeRPC(self.args)
                rpc.limits["primary"]["usedPercent"] = percent
                state = self.run_campaign(rpc, 21)
                self.assertEqual(state["stop_reason"], "included_usage_unknown")
                self.assertFalse(any(method in ("thread/start", "thread/resume", "turn/start",
                                                "thread/goal/set") for method, _ in rpc.calls))

    def test_api_key_auth_is_rejected_before_inference(self):
        rpc = FakeRPC(self.args)
        rpc.account_type = "apiKey"
        state = self.run_campaign(rpc, 21)
        self.assertEqual(state["stop_reason"], "chatgpt_auth_required")
        self.assertFalse(any(m in ("thread/start", "thread/resume") for m, _ in rpc.calls))

    def test_falling_credit_balance_stops_active_campaign(self):
        def spent(rpc):
            rpc.emit("account/rateLimits/updated", {"rateLimits": {
                "primary": {"usedPercent": 3, "windowDurationMins": 10080},
                "credits": {"hasCredits": True, "balance": "99.5"}, "planType": "pro"}})
        rpc = FakeRPC(self.args, steps=[spent])
        rpc.limits["credits"] = {"hasCredits": True, "balance": "100"}
        state = self.run_campaign(rpc, 21)
        self.assertEqual(state["stop_reason"], "credit_balance_decreased")
        self.assertFalse(watcher.should_restart(21, state))

    def test_failed_turn_without_error_event_preserves_credit_exhaustion(self):
        for info in ("usageLimitExceeded", "sessionBudgetExceeded"):
            with self.subTest(info=info):
                def fail(rpc):
                    rpc.emit("turn/completed", {"threadId": "test-thread", "turn": {
                        "id": "turn-1", "status": "failed", "error": {"codexErrorInfo": info}}})
                self.saved(goal())
                rpc = FakeRPC(self.args, goal(), steps=[fail])
                state = self.run_campaign(rpc, 21)
                self.assertEqual(state["stop_reason"], "quota_exhausted")
                self.assertFalse(watcher.should_restart(21, state))

    def test_automatic_recovery_does_not_resume_exhausted_credits(self):
        self.saved(goal("usageLimited"))
        self.args.recovered = True
        rpc = FakeRPC(self.args, goal("usageLimited"))
        self.run_campaign(rpc, 21)
        self.assertFalse(any(m in ("thread/resume", "thread/goal/set") for m, p in rpc.calls))

    def test_policy_failed_turn_notice_recommends_feedback_without_retry(self):
        self.saved(goal())
        calls_at_failure = []

        def fail(rpc):
            rpc.turns.pop("test-thread")
            rpc.emit("turn/completed", {"threadId": "test-thread", "turn": {
                "id": "turn-1", "status": "failed", "error": {
                    "message": "service policy refusal", "codexErrorInfo": "cyberPolicy"}}})
            calls_at_failure.extend(rpc.calls)

        rpc = FakeRPC(self.args, goal(), steps=[fail])
        campaign = launcher.Campaign(self.args, self.directory, self.directory, rpc.factory)
        output = io.StringIO()
        with redirect_stdout(output):
            self.assertEqual(campaign.run(), 23)
        self.assertTrue(rpc.closed)
        state = json.loads((self.directory / "state.json").read_text())
        notice = next(line for line in output.getvalue().splitlines() if "State: " in line)
        self.assertIn("service-side", notice)
        self.assertIn("/feedback", notice)
        self.assertIn("test-thread", notice)
        self.assertIn("turn-1", notice)
        self.assertNotIn("run the same command", notice)
        self.assertEqual(state["stop_reason"], "turn_failed")
        self.assertEqual(state["last_error"]["codexErrorInfo"], "cyberPolicy")
        self.assertEqual(state["stop_errors"], [])
        self.assertFalse(state.get("retryable", False))
        self.assertFalse(watcher.should_restart(23, state))
        self.assertFalse(watcher.should_restart(23, state, watchdog=True))
        self.assertEqual(sum(method == "thread/resume" for method, _ in rpc.calls), 1)
        self.assertFalse(any(method in ("thread/start", "turn/start")
                             for method, _ in rpc.calls[len(calls_at_failure):]))
        self.assertFalse(any(method == "thread/goal/set" and params.get("status") == "active"
                             for method, params in rpc.calls[len(calls_at_failure):]))
        self.assertFalse(any(method == "thread/resume"
                             for method, _ in rpc.calls[len(calls_at_failure):]))

    def test_child_failure_identity_survives_sibling_interruptions(self):
        class InterruptingRPC(FakeRPC):
            def call(self, method, params, **kwargs):
                if method == "turn/interrupt":
                    self.calls.append((method, params))
                    turn = dict(self.turns.pop(params["threadId"]))
                    turn["status"] = "interrupted"
                    self.emit("turn/completed", {"threadId": params["threadId"], "turn": turn})
                    return {}
                return super().call(method, params, **kwargs)

        for event in ("turn/completed", "error"):
            with self.subTest(event=event):
                self.saved(goal())

                def fail(rpc):
                    rpc.started("failed-child-turn", "failed-worker")
                    rpc.started("later-review-turn", "later-reviewer")
                    error = {"message": "service policy refusal", "codexErrorInfo": "cyberPolicy"}
                    if event == "turn/completed":
                        rpc.turns.pop("failed-worker")
                        rpc.emit(event, {"threadId": "failed-worker", "turn": {
                            "id": "failed-child-turn", "status": "failed", "error": error}})
                    else:
                        rpc.emit(event, {"threadId": "failed-worker", "error": error,
                                         "willRetry": False})

                rpc = InterruptingRPC(self.args, goal(), steps=[fail])
                campaign = launcher.Campaign(self.args, self.directory, self.directory, rpc.factory)
                output = io.StringIO()
                with redirect_stdout(output):
                    self.assertEqual(campaign.run(), 23)
                state = json.loads((self.directory / "state.json").read_text())
                self.assertEqual(state["last_turn"]["status"], "interrupted")
                self.assertEqual(state["last_failure"]["thread_id"], "failed-worker")
                self.assertEqual(state["last_failure"]["id"], "failed-child-turn")
                advice = launcher.restart_advice(state)
                self.assertIn("thread=failed-worker; turn=failed-child-turn", advice)
                self.assertNotIn("later-reviewer", advice)
                self.assertFalse(watcher.should_restart(23, state))
                self.assertFalse(watcher.should_restart(23, state, watchdog=True))
                self.assertFalse(any(method in ("thread/start", "turn/start") for method, _ in rpc.calls))
                self.assertEqual(sum(method == "thread/resume" for method, _ in rpc.calls), 1)

    def test_legacy_failure_advice_uses_unique_failed_worker_not_interrupted_reviewer(self):
        state = {"thread_id": "dispatcher", "stop_reason": "turn_failed",
                 "last_error": {"codexErrorInfo": "cyberPolicy"}, "log_dir": "current-run",
                 "last_turn": {"thread_id": "reviewer", "id": "interrupted-turn",
                               "status": "interrupted"},
                 "agents": {"failed-worker": {"status": "failed", "turn_id": "actual-failure"},
                            "reviewer": {"status": "interrupted", "turn_id": "interrupted-turn"}},
                 "last_failure": {"thread_id": "old-worker", "id": "old-failure",
                                  "log_dir": "previous-run", "error": {"codexErrorInfo": "cyberPolicy"}}}
        advice = launcher.restart_advice(state)
        self.assertIn("thread=failed-worker; turn=actual-failure", advice)
        self.assertNotIn("interrupted-turn", advice)
        self.assertNotIn("old-failure", advice)
        state["agents"]["another-failure"] = {"status": "failed", "turn_id": "ambiguous"}
        self.assertIn("turn=unknown", launcher.restart_advice(state))

    def test_signal_notice_keeps_resume_hint_with_stale_policy_error(self):
        self.saved(goal())
        saved = json.loads((self.directory / "state.json").read_text())
        saved.update(last_error={"codexErrorInfo": "cyberPolicy"},
                     last_turn={"thread_id": "test-thread", "id": "historical-policy-turn",
                                "status": "failed"})
        launcher.atomic_json(self.directory / "state.json", saved)
        rpc = FakeRPC(self.args, goal(), steps=[lambda r: r.on_event.__self__.on_signal(2, None)])
        campaign = launcher.Campaign(self.args, self.directory, self.directory, rpc.factory)
        output = io.StringIO()
        with redirect_stdout(output):
            self.assertEqual(campaign.run(), 10)
        self.assertTrue(rpc.closed)
        state = json.loads((self.directory / "state.json").read_text())
        notice = next(line for line in output.getvalue().splitlines() if "State: " in line)
        self.assertEqual(state["stop_reason"], "signal_2")
        self.assertIn("run the same command", notice)
        self.assertNotIn("/feedback", notice)

    def test_restart_advice_only_special_cases_current_policy_stop(self):
        for reason in ("turn_failed", "server_error"):
            with self.subTest(reason=reason):
                advice = launcher.restart_advice({"stop_reason": reason,
                    "thread_id": "current-thread", "last_error": {"codexErrorInfo": "cyberPolicy"},
                    "last_turn": {"thread_id": "current-thread", "id": "failed-turn", "status": "failed"}})
                for expected in ("service-side", "/feedback", "current-thread", "failed-turn"):
                    self.assertIn(expected, advice)
                self.assertNotIn("run the same command", advice)
        for reason, error in (("signal_2", {"codexErrorInfo": "cyberPolicy"}),
                              ("launcher_error", {"codexErrorInfo": "cyberPolicy"}),
                              ("turn_failed", {"codexErrorInfo": "serverOverloaded"}),
                              ("server_error", "cyberPolicy"), ("turn_failed", None)):
            with self.subTest(reason=reason, error=error):
                advice = launcher.restart_advice({"stop_reason": reason, "last_error": error})
                self.assertIn("run the same command", advice)
                self.assertNotIn("/feedback", advice)

    def test_capacity_and_temporary_rate_errors_are_recoverable(self):
        for info, event in (("serverOverloaded", "turn/completed"),
                            ("rateLimitExceeded", "error")):
            with self.subTest(info=info):
                def fail(rpc):
                    error = {"message": "temporary capacity limit", "codexErrorInfo": info}
                    if event == "error":
                        rpc.emit(event, {"threadId": "test-thread", "willRetry": False, "error": error})
                    else:
                        rpc.emit(event, {"threadId": "test-thread", "turn": {
                            "id": "turn-1", "status": "failed", "error": error}})
                    rpc.status("blocked")
                self.saved(goal())
                rpc = FakeRPC(self.args, goal(), steps=[fail])
                state = self.run_campaign(rpc, 23)
                self.assertTrue(watcher.should_restart(23, state))

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

    def test_misconfigured_build_environment_fails_before_thread_start(self):
        rpc = FakeRPC(self.args)
        rpc.bad_environment = True
        state = self.run_campaign(rpc, 1)
        self.assertIn("build environment", state["last_error"])
        self.assertFalse(any(m.startswith("thread/") for m, p in rpc.calls))

    def test_misconfigured_worker_model_or_effort_fails_before_resume(self):
        for attribute, value in (("worker_model", "gpt-5.6-luna"), ("worker_effort", "low")):
            with self.subTest(attribute=attribute):
                self.saved(goal("paused"))
                rpc = FakeRPC(self.args, goal("paused"))
                setattr(rpc, attribute, value)
                state = self.run_campaign(rpc, 1)
                self.assertIn("Effective Codex settings", state["last_error"])
                self.assertEqual(rpc.goal["status"], "paused")
                self.assertFalse(any(m.startswith("thread/") for m, p in rpc.calls))

    def test_missing_gpt_61_refuses_resume_even_with_legacy_models_available(self):
        self.saved(goal("paused"))
        rpc = FakeRPC(self.args, goal("paused"))
        rpc.models = {"gpt-5.6-sol": ["low", "medium", "high"],
                      "gpt-5.6-luna": ["low", "medium", "high"],
                      "gpt-6-astra": ["low", "medium", "high"]}
        state = self.run_campaign(rpc, 1)
        self.assertIn("gpt-6.1-sol/medium", state["last_error"])
        self.assertEqual(rpc.goal["status"], "paused")
        self.assertFalse(any(m.startswith("thread/") for m, p in rpc.calls))

    def test_unadvertised_routed_effort_refuses_resume_without_fallback(self):
        for effort in ("low", "medium", "high"):
            with self.subTest(effort=effort):
                self.saved(goal("paused"))
                rpc = FakeRPC(self.args, goal("paused"))
                rpc.models["gpt-6.1-sol"].remove(effort)
                state = self.run_campaign(rpc, 1)
                self.assertIn("gpt-6.1-sol/" + effort, state["last_error"])
                self.assertEqual(rpc.goal["status"], "paused")
                self.assertFalse(any(m.startswith("thread/") for m, p in rpc.calls))

    def test_only_gpt_61_catalogue_supports_all_routes(self):
        rpc = FakeRPC(self.args)
        settings = launcher.preflight(rpc, self.args, self.directory)
        self.assertEqual(settings["model_routing"]["auditor"],
                         {"model": "gpt-6.1-sol", "effort": "low"})
        self.assertTrue(all(selection["model"] == "gpt-6.1-sol"
                            for selection in settings["model_routing"].values()))
        self.assertFalse(any(m.startswith("thread/") for m, p in rpc.calls))

    def test_stop_reason_survives_late_transient_error(self):
        campaign = launcher.Campaign(self.args, self.directory, self.directory)
        try:
            campaign.on_signal(2, None)
            campaign.record_failure({"codexErrorInfo": "serverOverloaded"}, "server_error")
            self.assertEqual(campaign.stop_reason, "signal_2")
            self.assertFalse(campaign.stop_now)
            self.assertFalse(watcher.should_restart(23, dict(campaign.state, stop_reason=campaign.stop_reason)))
        finally:
            campaign.output.close()

    def test_signal_overrides_an_earlier_transient_error(self):
        campaign = launcher.Campaign(self.args, self.directory, self.directory)
        try:
            campaign.record_failure({"codexErrorInfo": "serverOverloaded"}, "server_error")
            campaign.on_signal(2, None)
            self.assertEqual(campaign.stop_reason, "signal_2")
            self.assertFalse(watcher.should_restart(23, dict(campaign.state, stop_reason=campaign.stop_reason)))
        finally:
            campaign.output.close()

    def test_resource_rejection_replaces_previous_retryable_worker_snapshot(self):
        self.saved(goal("paused"))
        state_path = self.directory / "state.json"
        saved = json.loads(state_path.read_text())
        saved.update(worker_pid=-100, retryable=True, stop_reason="server_error",
                     last_error={"codexErrorInfo": "serverOverloaded"})
        launcher.atomic_json(state_path, saved)
        campaign = launcher.Campaign(self.args, self.directory, self.directory)
        with patch.object(launcher, "check_resources", side_effect=RuntimeError("Insufficient resources")), \
                redirect_stdout(io.StringIO()):
            self.assertEqual(campaign.run(), 1)
        state = json.loads(state_path.read_text())
        self.assertEqual(state["worker_pid"], os.getpid())
        self.assertFalse(state["retryable"])
        self.assertFalse(watcher.should_restart(1, state))

    def test_shutdown_stops_touching_threads_after_objective_ownership_changes(self):
        campaign = launcher.Campaign(self.args, self.directory, self.directory)
        rpc = FakeRPC(self.args, goal(objective="Changed outside the launcher"))
        campaign.rpc, campaign.controlled = rpc, True
        campaign.state["thread_id"] = "test-thread"
        try:
            campaign.stop()
            self.assertFalse(campaign.controlled)
            self.assertEqual([method for method, params in rpc.calls], ["thread/goal/get"])
            self.assertIn("changed externally", campaign.state["stop_errors"][0])
        finally:
            campaign.output.close()

    def test_resource_guard_fails_before_starting_server(self):
        rpc = FakeRPC(self.args)
        with patch.object(launcher, "check_resources", side_effect=RuntimeError("Insufficient disk")):
            campaign = launcher.Campaign(self.args, self.directory, self.directory, rpc.factory)
            with redirect_stdout(io.StringIO()):
                self.assertEqual(campaign.run(), 1)
        self.assertFalse(rpc.calls)
        self.assertIn("Insufficient disk", json.loads((self.directory / "state.json").read_text())["last_error"])

    def test_resume_receives_profile_and_convergence_without_replacing_goal(self):
        saved_goal = dict(goal("paused"), tokenBudget=432100)
        self.saved(saved_goal)
        rpc = FakeRPC(self.args, dict(saved_goal), [lambda r: (r.completed(), r.status("complete"))])
        state = self.run_campaign(rpc, 0)
        params = next(p for m, p in rpc.calls if m == "thread/resume")
        for name in ("CONVERGENCE.md", "HANDOFF.md", "disjoint", "failure family"):
            self.assertIn(name, params["developerInstructions"])
        self.assertEqual(state["settings"]["resources"]["profile"], "aggressive")
        self.assertEqual(params["model"], "gpt-6.1-sol")
        self.assertEqual(params["config"]["model_reasoning_effort"], "medium")
        self.assertEqual(state["settings"]["agents"]["default_subagent_model"], "gpt-6.1-sol")
        self.assertEqual(state["goal"]["objective"], saved_goal["objective"])
        self.assertEqual(state["goal"]["tokenBudget"], saved_goal["tokenBudget"])
        self.assertEqual(state["goal"]["tokensUsed"], saved_goal["tokensUsed"])
        self.assertFalse(any("objective" in p or "tokenBudget" in p for m, p in rpc.calls))

    def test_stale_bound_hold_is_archived_before_resume_and_never_steered(self):
        saved_goal = dict(goal("paused"), tokenBudget=432100)
        self.saved(saved_goal)
        stale_text = "Preparation only: do not start the historical campaign."
        ident = launcher.queue_instruction(self.directory, stale_text)
        pending = self.directory / "instructions" / "pending" / (ident + ".json")
        original = pending.read_bytes()
        original_inode = pending.stat().st_ino
        archived = self.directory / "instructions" / "superseded" / pending.name
        receipt = self.directory / "instructions" / "reconciliation" / pending.name
        note, digest = self.startup_arguments("--supersede-instruction",
            ident + ":" + hashlib.sha256(original).hexdigest())
        checked = []

        class ArchivalRPC(FakeRPC):
            def call(rpc, method, params, **kwargs):
                if method == "thread/resume":
                    self.assertFalse(pending.exists())
                    self.assertEqual(archived.read_bytes(), original)
                    self.assertEqual(archived.stat().st_ino, original_inode)
                    self.assertEqual(json.loads(receipt.read_text())["status"], "superseded")
                    checked.append(True)
                return super().call(method, params, **kwargs)

        rpc = ArchivalRPC(self.args, dict(saved_goal),
                          [lambda r: (r.completed(), r.status("complete"))])
        state = self.run_campaign(rpc, 0)
        self.assertEqual(checked, [True])
        self.assertEqual(archived.read_bytes(), original)
        self.assertEqual(json.loads(receipt.read_text())["startup_instruction_sha256"], digest)
        self.assertFalse(any(method == "turn/steer" for method, _ in rpc.calls))
        seeds = [params for method, params in rpc.calls if method == "turn/start"]
        self.assertEqual(len(seeds), 1)
        self.assertIn(note, seeds[0]["input"][0]["text"])
        self.assertTrue(seeds[0]["input"][0]["text"].startswith("EXPLICIT USER RESUME"))
        self.assertEqual(state["goal"]["objective"], saved_goal["objective"])
        self.assertEqual(state["goal"]["tokenBudget"], saved_goal["tokenBudget"])

    def test_fresh_startup_user_message_precedes_goal_activation_once(self):
        note, digest = self.startup_arguments()
        saved_goal = dict(goal("paused"), tokenBudget=432100)
        self.saved(saved_goal)
        rpc = FakeRPC(self.args, dict(saved_goal),
                      [lambda r: (r.completed(), r.status("complete"))])
        state = self.run_campaign(rpc, 0)
        starts = [(index, params) for index, (method, params) in enumerate(rpc.calls)
                  if method == "turn/start"]
        self.assertEqual(len(starts), 1)
        seed_index, seed = starts[0]
        activation = next(index for index, (method, params) in enumerate(rpc.calls)
                          if method == "thread/goal/set" and params.get("status") == "active")
        self.assertLess(seed_index, activation)
        self.assertEqual(seed["threadId"], "test-thread")
        message = seed["input"][0]["text"]
        self.assertTrue(message.startswith("EXPLICIT USER RESUME"))
        self.assertIn(note, message)
        self.assertIn("supersedes earlier user stop/pause requests", message)
        self.assertEqual(state["resume_instruction"]["message_sha256"],
                         hashlib.sha256(message.encode()).hexdigest())
        self.assertEqual(Path(state["resume_instruction"]["message_path"]).read_text(), message)
        self.assertEqual(state["resume_instruction"]["sha256"], digest)
        self.assertEqual(state["resume_instruction"]["turn_id"], "startup-turn-1")
        self.assertEqual(state["resume_instruction"]["status"], "accepted_by_server")
        self.assertEqual(state["goal"]["objective"], saved_goal["objective"])
        self.assertEqual(state["goal"]["tokenBudget"], saved_goal["tokenBudget"])
        self.assertEqual(state["goal"]["tokensUsed"], saved_goal["tokensUsed"])
        self.assertFalse(any("objective" in params or "tokenBudget" in params
                             for _, params in rpc.calls))

    def test_automatic_recovery_never_seeds_a_duplicate_startup_message(self):
        self.startup_arguments("--recovered")
        self.saved(goal("paused"))
        rpc = FakeRPC(self.args, goal("paused"),
                      [lambda r: (r.completed(), r.status("complete"))])
        self.run_campaign(rpc, 0)
        self.assertTrue(any(method == "thread/resume" for method, _ in rpc.calls))
        self.assertFalse(any(method == "turn/start" for method, _ in rpc.calls))

    def test_manual_resume_without_note_overrides_the_saved_user_pause(self):
        self.saved(goal("paused"))
        state_path = self.directory / "state.json"
        saved = json.loads(state_path.read_text())
        saved["last_instruction"] = {"id": "user-stop-014328", "status": "accepted_by_server"}
        launcher.atomic_json(state_path, saved)
        rpc = FakeRPC(self.args, goal("paused"),
                      [lambda r: (r.completed(), r.status("complete"))])
        state = self.run_campaign(rpc, 0)
        starts = [p for m, p in rpc.calls if m == "turn/start"]
        self.assertEqual(len(starts), 1)
        message = starts[0]["input"][0]["text"]
        self.assertIn("EXPLICIT USER RESUME", message)
        self.assertIn("user-stop-014328", message)
        self.assertIn("A new stop received", message)
        self.assertIsNone(state["resume_instruction"]["sha256"])
        self.assertEqual(state["resume_instruction"]["message_sha256"],
                         hashlib.sha256(message.encode()).hexdigest())

    def test_new_pause_or_block_during_manual_resume_prevents_activation(self):
        for status in ("paused", "blocked"):
            for event in (True, False):
                with self.subTest(status=status, event=event):
                    self.startup_arguments()
                    self.saved(goal("paused"))

                    class StoppedDuringSeedRPC(FakeRPC):
                        def call(rpc, method, params, **kwargs):
                            result = super().call(method, params, **kwargs)
                            if method == "turn/start":
                                if event:
                                    rpc.status(status)
                                else:
                                    rpc.goal.update(status=status, updatedAt=3)
                            return result

                    rpc = StoppedDuringSeedRPC(self.args, goal("paused"))
                    campaign = launcher.Campaign(self.args, self.directory, self.directory, rpc.factory)
                    try:
                        with redirect_stdout(io.StringIO()):
                            campaign.begin()
                        self.assertEqual(campaign.stop_reason, "startup_goal_stopped")
                        self.assertTrue(campaign.stop_now)
                        self.assertEqual(campaign.goal["status"], status)
                        self.assertFalse(any(m == "thread/goal/set" for m, _ in rpc.calls))
                    finally:
                        rpc.close()
                        campaign.output.close()

    def test_startup_user_message_refuses_an_existing_active_turn(self):
        self.startup_arguments()
        self.saved(goal("paused"))
        rpc = FakeRPC(self.args, goal("paused"))
        rpc.turns["test-thread"] = {"id": "existing-turn", "items": [], "status": "inProgress"}
        campaign = launcher.Campaign(self.args, self.directory, self.directory, rpc.factory)
        try:
            with redirect_stdout(io.StringIO()), self.assertRaises(RuntimeError):
                campaign.begin()
            self.assertFalse(any(method == "turn/start" for method, _ in rpc.calls))
            self.assertFalse(any(method == "thread/goal/set" and params.get("status") == "active"
                                 for method, params in rpc.calls))
            self.assertEqual(rpc.goal["status"], "paused")
            self.assertEqual(rpc.turns["test-thread"]["id"], "existing-turn")
        finally:
            rpc.close()
            campaign.output.close()

    def test_uncertain_startup_delivery_keeps_goal_paused_and_records_receipt(self):
        _, digest = self.startup_arguments()
        self.saved(goal("paused"))

        class UncertainRPC(FakeRPC):
            def call(rpc, method, params, **kwargs):
                result = super().call(method, params, **kwargs)
                if method == "turn/start":
                    raise OSError("Response lost after the server accepted the startup turn")
                return result

        rpc = UncertainRPC(self.args, goal("paused"))
        campaign = launcher.Campaign(self.args, self.directory, self.directory, rpc.factory)
        try:
            with redirect_stdout(io.StringIO()), self.assertRaisesRegex(RuntimeError, "delivery uncertain"):
                campaign.begin()
            receipt = json.loads((self.directory / "state.json").read_text())["resume_instruction"]
            self.assertEqual(receipt["sha256"], digest)
            self.assertEqual(receipt["status"], "delivery_uncertain")
            self.assertEqual(sum(method == "turn/start" for method, _ in rpc.calls), 1)
            self.assertFalse(any(method == "thread/goal/set" and params.get("status") == "active"
                                 for method, params in rpc.calls))
            self.assertEqual(rpc.goal["status"], "paused")
        finally:
            rpc.close()
            campaign.output.close()

    def test_uncertain_startup_receipt_blocks_fresh_launch_and_recovery_before_rpc(self):
        for status in ("sending", "delivery_uncertain"):
            for recovered in (False, True):
                with self.subTest(status=status, recovered=recovered):
                    _, digest = self.startup_arguments(*(["--recovered"] if recovered else []))
                    self.saved(goal("paused"))
                    state_path = self.directory / "state.json"
                    state = json.loads(state_path.read_text())
                    state["resume_instruction"] = {"sha256": digest, "status": status}
                    launcher.atomic_json(state_path, state)
                    original = state_path.read_bytes()
                    factory = Mock(side_effect=AssertionError("RPC must not be started"))
                    campaign = launcher.Campaign(self.args, self.directory, self.directory, factory)
                    try:
                        with self.assertRaisesRegex(RuntimeError, "delivery is uncertain"):
                            campaign.begin()
                        factory.assert_not_called()
                        self.assertIsNone(campaign.rpc)
                        self.assertEqual(state_path.read_bytes(), original)
                        self.assertEqual(campaign.state["goal"]["status"], "paused")
                    finally:
                        campaign.output.close()

    def test_signal_or_usage_stop_during_startup_message_prevents_goal_activation(self):
        for cause in ("signal", "usage_guard"):
            with self.subTest(cause=cause):
                self.startup_arguments()
                self.saved(goal("paused"))

                class StopDuringSeedRPC(FakeRPC):
                    def call(rpc, method, params, **kwargs):
                        result = super().call(method, params, **kwargs)
                        if method == "turn/start":
                            if cause == "signal":
                                rpc.on_event.__self__.on_signal(2, None)
                            else:
                                rpc.emit("account/rateLimits/updated", {"rateLimits": {
                                    "primary": {"usedPercent": 100}, "credits": {"balance": "0"}}})
                        return result

                rpc = StopDuringSeedRPC(self.args, goal("paused"))
                campaign = launcher.Campaign(self.args, self.directory, self.directory, rpc.factory)
                try:
                    with redirect_stdout(io.StringIO()):
                        campaign.begin()
                    self.assertEqual(campaign.stop_reason,
                                     "signal_2" if cause == "signal" else "included_usage_guard")
                    self.assertEqual(sum(method == "turn/start" for method, _ in rpc.calls), 1)
                    self.assertFalse(any(method == "thread/goal/set" for method, _ in rpc.calls))
                    self.assertEqual(rpc.goal["status"], "paused")
                    self.assertEqual(campaign.state["resume_instruction"]["status"], "accepted_by_server")
                finally:
                    rpc.close()
                    campaign.output.close()

    def test_startup_message_cannot_overwrite_a_terminal_cleared_or_changed_goal(self):
        for change in ("complete", "usageLimited", "budgetLimited", "cleared", "different_objective"):
            with self.subTest(change=change):
                self.startup_arguments()
                saved_goal = dict(goal("paused"), tokenBudget=432100)
                self.saved(saved_goal)

                class ChangedDuringSeedRPC(FakeRPC):
                    def call(rpc, method, params, **kwargs):
                        result = super().call(method, params, **kwargs)
                        if method == "turn/start":
                            if change == "cleared":
                                rpc.goal = None
                            elif change == "different_objective":
                                rpc.goal["objective"] = "Another user objective"
                            else:
                                rpc.status(change)
                        return result

                rpc = ChangedDuringSeedRPC(self.args, dict(saved_goal))
                campaign = launcher.Campaign(self.args, self.directory, self.directory, rpc.factory)
                try:
                    with redirect_stdout(io.StringIO()):
                        if change in ("cleared", "different_objective"):
                            with self.assertRaisesRegex(RuntimeError, "goal changed"):
                                campaign.begin()
                        else:
                            campaign.begin()
                            self.assertEqual(campaign.goal["status"], change)
                            self.assertEqual(campaign.goal["tokenBudget"], saved_goal["tokenBudget"])
                    self.assertEqual(sum(method == "turn/start" for method, _ in rpc.calls), 1)
                    self.assertFalse(any(method == "thread/goal/set" for method, _ in rpc.calls))
                    if change == "cleared":
                        self.assertIsNone(rpc.goal)
                    elif change == "different_objective":
                        self.assertEqual(rpc.goal["objective"], "Another user objective")
                    else:
                        self.assertEqual(rpc.goal["status"], change)
                finally:
                    rpc.close()
                    campaign.output.close()

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

    def test_clarification_request_does_not_stop_campaign(self):
        def ask(rpc):
            rpc.on_event({"id": 50, "method": launcher.USER_INPUT_METHOD, "params": {
                "threadId": "test-thread", "questions": [{"id": "approach"}]}})
        rpc = FakeRPC(self.args, steps=[ask, lambda r: (r.completed(), r.status("blocked"))])
        state = self.run_campaign(rpc, 20)
        self.assertIsNone(state["stop_reason"])
        self.assertNotIn("pending_request", state)
        self.assertEqual(state["last_automatic_input"]["question_ids"], ["approach"])

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

    def test_heartbeat_stays_live_without_resetting_agent_quiet_time(self):
        clock = [100.0]
        self.args.quiet = True
        rpc = FakeRPC(self.args, steps=[
            lambda r: clock.__setitem__(0, 116.0),
            lambda r: clock.__setitem__(0, 301.0),
            lambda r: (r.completed(), r.status("blocked"))])
        output = io.StringIO()
        with patch.object(launcher.time, "monotonic", side_effect=lambda: clock[0]), redirect_stdout(output):
            campaign = launcher.Campaign(self.args, self.directory, self.directory, rpc.factory)
            self.assertEqual(campaign.run(), 20)
        self.assertGreaterEqual(output.getvalue().count("HEARTBEAT alive"), 2)
        self.assertIn("201.0s ago", output.getvalue())
        self.assertIn("POSSIBLY STALLED", output.getvalue())
        self.assertNotIn("Goal active; local status", output.getvalue())
        state = json.loads((self.directory / "state.json").read_text())
        self.assertIn("heartbeat_at", state)
        self.assertEqual(state["agents"]["test-thread"]["label"], "dispatcher")
        self.assertIn("HEARTBEAT alive", Path(state["console_log"]).read_text())

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
                "account/read": "v2/GetAccountParams.json",
                "account/rateLimits/read": "v2/NullableGetAccountRateLimitsParams.json",
                "thread/resume": "v2/ThreadResumeParams.json", "thread/goal/get": "v2/ThreadGoalGetParams.json",
                "thread/goal/set": "v2/ThreadGoalSetParams.json", "turn/start": "v2/TurnStartParams.json",
                "turn/steer": "v2/TurnSteerParams.json",
                "thread/loaded/list": "v2/ThreadLoadedListParams.json",
                "thread/turns/list": "v2/ThreadTurnsListParams.json", "turn/interrupt": "v2/TurnInterruptParams.json"}
            schemas = {method: json.loads((Path(directory) / name).read_text()) for method, name in files.items()}
            for method, params in cls.all_calls:
                jsonschema.Draft7Validator(schemas[method]).validate(params)


class LiveOutputTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="os-goal-output-")
        self.directory = Path(self.temp.name)
        self.output = launcher.LiveOutput(self.directory, quiet=True)
        self.output.primary = "parent"

    def tearDown(self):
        self.output.close()
        self.temp.cleanup()

    def event(self, method, thread="parent", **params):
        self.output.event({"method": method, "params": dict(threadId=thread, **params)})

    def log(self):
        return (self.directory / "console.log").read_text()

    def test_interleaved_agents_partial_lines_completion_and_output_fallback(self):
        self.event("item/started", item={"type": "subAgentActivity", "id": "spawn",
                   "kind": "started", "agentThreadId": "child", "agentPath": "/root/audit"})
        self.event("item/agentMessage/delta", itemId="one", delta="Parent ")
        self.event("item/agentMessage/delta", thread="child", itemId="two", delta="Child ready\n")
        self.event("item/agentMessage/delta", itemId="one", delta="ready\n")
        self.event("item/completed", item={"type": "agentMessage", "id": "one", "text": "Parent ready\n"})
        self.assertEqual(self.log().count("Parent ready"), 1)
        self.assertIn("[/root/audit/message] Child ready", self.log())
        self.event("item/completed", item={"type": "commandExecution", "id": "cmd",
                   "command": "test", "status": "failed", "exitCode": 7, "aggregatedOutput": "failure details\n"})
        self.assertIn("failure details", self.log())
        self.assertIn("exit=7", self.log())

    def test_partial_fragments_flush_on_timer_and_buffers_are_bounded(self):
        clock = [10.0]
        with patch.object(launcher.time, "monotonic", side_effect=lambda: clock[0]):
            self.event("item/agentMessage/delta", itemId="partial", delta="still working")
            self.output.flush()
            self.assertNotIn("still working", self.log())
            clock[0] += 0.3
            self.output.flush()
            self.assertIn("still working", self.log())
        self.event("item/commandExecution/outputDelta", itemId="long", delta="x" * 50000)
        self.assertLess(len(self.output.pending[("parent", "long", "output")][0]), 4096)

    def test_quiet_keeps_log_and_heartbeat_and_omits_raw_reasoning(self):
        console = io.StringIO()
        with redirect_stdout(console):
            self.event("item/completed", item={"type": "agentMessage", "id": "msg", "text": "visible in log"})
            self.event("item/completed", item={"type": "reasoning", "id": "thought", "content": ["raw-private-text"]})
            self.output.heartbeat(goal(), {"parent": "turn"}, 20, 100, 200)
        self.assertIn("visible in log", self.log())
        self.assertNotIn("visible in log", console.getvalue())
        self.assertNotIn("raw-private-text", self.log())
        self.assertIn("HEARTBEAT alive", console.getvalue())
        self.assertIn("worker_pid=100; server_pid=200", console.getvalue())

    def test_real_transport_streams_before_command_completes_and_retains_stderr(self):
        source = r'''
import json,sys
first=json.loads(sys.stdin.readline())
def emit(value):
    print(json.dumps(value), flush=True)
emit({'method':'item/commandExecution/outputDelta','params':{
    'threadId':'parent','itemId':'cmd','delta':'live command output\n'}})
sys.stderr.write('server diagnostic\n'); sys.stderr.flush()
emit({'id':first['id'],'result':{}})
second=json.loads(sys.stdin.readline())
emit({'method':'item/completed','params':{'threadId':'parent','item':{
    'type':'commandExecution','id':'cmd','command':'fake build','status':'completed',
    'exitCode':0,'aggregatedOutput':'live command output\n'}}})
emit({'id':second['id'],'result':{}})
sys.stdin.read()
'''
        self.output.quiet = False
        console = io.StringIO()
        rpc = launcher.RPC([sys.executable, "-u", "-c", source], self.directory, self.output.event)
        try:
            with redirect_stdout(console):
                rpc.call("start", {}, timeout=5)
                self.assertIn("live command output", console.getvalue())
                self.assertNotIn("Command completed", console.getvalue())
                rpc.call("finish", {}, timeout=5)
                rpc.close()
                self.output.flush(force=True)
            self.assertEqual(console.getvalue().count("live command output"), 1)
            self.assertIn("server diagnostic", console.getvalue())
            self.assertIn("exit=0", console.getvalue())
            self.assertIn("server diagnostic", (self.directory / "server.stderr.log").read_text())
        finally:
            if rpc.proc.poll() is None:
                rpc.close()


class StatusTests(unittest.TestCase):
    def test_forced_stop_labels_stale_snapshot_without_mutation_or_server(self):
        with tempfile.TemporaryDirectory(prefix="os-goal-status-") as temp:
            repo = Path(temp)
            directory = repo / ".git/os-autopilot"
            directory.mkdir(parents=True)
            original = {"phase": "running", "worker_pid": 456, "active_turns": {"parent": "turn"}}
            launcher.atomic_json(directory / "state.json", original)
            launcher.atomic_json(directory / "watcher.json", {"event": "watcher_stopped", "worker_pid": 456})
            console = io.StringIO()
            with patch.object(launcher, "REPO", repo), \
                    patch.object(launcher.subprocess, "check_output", return_value=".git"), \
                    patch.object(launcher, "RPC") as rpc, redirect_stdout(console):
                self.assertEqual(launcher.main(["--status"]), 0)
            state = json.loads(console.getvalue())
            self.assertEqual(state["phase"], "stopped")
            self.assertEqual(state["last_worker_phase"], "running")
            self.assertEqual(state["active_turns"], {})
            self.assertEqual(state["last_recorded_active_turns"], original["active_turns"])
            self.assertEqual(json.loads((directory / "state.json").read_text()), original)
            rpc.assert_not_called()


class SudoHelperTests(unittest.TestCase):
    def test_helper_watch_retries_transient_failure_but_not_bad_credentials(self):
        failed = launcher.subprocess.CompletedProcess([], 75, b"", b"temporary read error\n")
        permanent = launcher.subprocess.CompletedProcess([], 1, b"", b"missing credential\n")
        output = type("Output", (), {"buffer": io.BytesIO(), "write": lambda self, value: None,
                                     "flush": lambda self: None})()
        with patch.object(sys, "argv", ["askpass"]), patch.object(sys, "stderr", output), \
                patch.object(askpass.time, "sleep"), patch.object(askpass.subprocess, "run", side_effect=[failed, permanent]) as run:
            self.assertEqual(askpass.main(), 1)
            self.assertEqual(run.call_count, 2)
        with patch.object(sys, "argv", ["askpass"]), patch.object(sys, "stderr", output), \
                patch.object(askpass.subprocess, "run", return_value=permanent) as run:
            self.assertEqual(askpass.main(), 1)
            self.assertEqual(run.call_count, 1)

    def test_private_credential_is_read_and_insecure_files_are_rejected(self):
        with tempfile.TemporaryDirectory(prefix="os-goal-credential-test-") as temp:
            path = Path(temp) / "credential"
            path.write_bytes(b"offline-test-password\n")
            path.chmod(0o600)
            self.assertEqual(askpass.read_credential(path), b"offline-test-password")
            path.chmod(0o644)
            with self.assertRaises(ValueError):
                askpass.read_credential(path)
            path.chmod(0o600)
            link = Path(temp) / "link"
            link.symlink_to(path)
            with self.assertRaises(OSError):
                askpass.read_credential(link)
            with patch.object(askpass.os, "getuid", return_value=os.getuid() + 1):
                with self.assertRaises(ValueError):
                    askpass.read_credential(path)

    def test_invalid_credential_contents_are_rejected(self):
        with tempfile.TemporaryDirectory(prefix="os-goal-credential-test-") as temp:
            path = Path(temp) / "credential"
            path.touch(mode=0o600)
            for value in (b"", b"\n", b"two\nlines", b"nul\0byte", b"x" * 4097):
                path.write_bytes(value)
                with self.subTest(size=len(value)), self.assertRaises(ValueError):
                    askpass.read_credential(path)

    def test_askpass_process_uses_only_private_file_and_stdout(self):
        with tempfile.TemporaryDirectory(prefix="os-goal-credential-test-") as temp:
            path = Path(temp) / "credential"
            path.write_bytes(b"offline-test-password\n")
            path.chmod(0o600)
            environment = launcher.runtime_environment()
            environment["MCKERNEL_OS_SUDO_CREDENTIAL"] = str(path)
            self.assertNotIn("offline-test-password", environment.values())
            result = launcher.subprocess.run([environment["SUDO_ASKPASS"], "sudo prompt"],
                env=environment, stdin=launcher.subprocess.DEVNULL, capture_output=True, timeout=5)
            self.assertEqual(result.returncode, 0)
            self.assertEqual(result.stdout, b"offline-test-password\n")
            self.assertEqual(result.stderr, b"")


class WatcherTests(unittest.TestCase):
    def test_progress_marker_requires_current_running_worker(self):
        state = {"worker_pid": 10, "phase": "running", "goal": {"status": "active"},
                 "agent_event_count": 5, "heartbeat_at": "later"}
        self.assertEqual(watcher.progress_marker(state, 10), 5)
        self.assertIsNone(watcher.progress_marker(state, 20))
        state["goal"]["status"] = "paused"
        self.assertIsNone(watcher.progress_marker(state, 10))
        for reason in ("quota_or_rate_limit", "quota_exhausted", "needs_user_input", "goal_cleared"):
            self.assertFalse(watcher.should_restart(23, {"stop_reason": reason}, watchdog=True))

    def test_agent_stall_recovers_even_when_worker_keeps_writing_heartbeats(self):
        source = r'''
import json,os,signal,sys,time
from pathlib import Path
path=Path(__file__).resolve().parents[1]/'.git/os-autopilot/state.json'
state={'thread_id':'quiet-thread','worker_pid':os.getpid(),'phase':'running',
       'agent_event_count':1,'goal':{'status':'active'}}
signal.signal(signal.SIGTERM, signal.SIG_IGN)
signal.signal(signal.SIGUSR1, signal.SIG_IGN)
if '--recovered' in sys.argv:
    state['goal']['status']='complete'
while True:
    state['heartbeat_at']=time.time()
    temporary=path.with_suffix('.tmp')
    temporary.write_text(json.dumps(state)); temporary.replace(path)
    if '--recovered' in sys.argv: break
    time.sleep(0.03)
'''
        with tempfile.TemporaryDirectory(prefix="os-goal-progress-stall-") as temp:
            repo = Path(temp)
            (repo / "scripts").mkdir()
            (repo / "scripts/run_os_goal.py").write_text(source)
            directory = repo / ".git/os-autopilot"
            args = launcher.arguments(["--hours", "0", "--restart-delay", "0", "--max-restarts", "1",
                                       "--stall-seconds", "0.15", "--grace-seconds", "0.05",
                                       "--heartbeat-seconds", "0.025", "--watchdog-seconds", "5"])
            with redirect_stdout(io.StringIO()):
                self.assertEqual(watcher.supervise(args, repo, directory, [], launcher.Lease, launcher.atomic_json), 0)
            events = [json.loads(line) for line in (directory / "watcher.jsonl").read_text().splitlines()]
            stalled = next(row for row in events if row["event"] == "agent_progress_stalled")
            self.assertLess(stalled["seconds_without_update"], 0.15)
            self.assertIn("worker_forced_stop", [row["event"] for row in events])
            capture = json.loads(Path(stalled["diagnostics"]).read_text())
            self.assertEqual(capture["state"]["agent_event_count"], 1)
            self.assertIn("meminfo", capture["resources"])
            self.assertEqual(json.loads((directory / "state.json").read_text())["thread_id"], "quiet-thread")

    def test_agent_events_keep_a_quiet_campaign_running(self):
        source = r'''
import json,os,time
from pathlib import Path
path=Path(__file__).resolve().parents[1]/'.git/os-autopilot/state.json'
state={'thread_id':'busy-thread','worker_pid':os.getpid(),'phase':'running',
       'agent_event_count':0,'goal':{'status':'active'}}
deadline=time.monotonic()+1
while True:
    state['agent_event_count']+=1
    done=time.monotonic()>=deadline
    if done: state['goal']['status']='complete'
    temporary=path.with_suffix('.tmp')
    temporary.write_text(json.dumps(state)); temporary.replace(path)
    if done: break
    time.sleep(0.03)
'''
        with tempfile.TemporaryDirectory(prefix="os-goal-progress-live-") as temp:
            repo = Path(temp)
            (repo / "scripts").mkdir()
            (repo / "scripts/run_os_goal.py").write_text(source)
            directory = repo / ".git/os-autopilot"
            args = launcher.arguments(["--hours", "0", "--stall-seconds", "0.15", "--max-restarts", "0",
                                       "--heartbeat-seconds", "0.025"])
            with redirect_stdout(io.StringIO()):
                self.assertEqual(watcher.supervise(args, repo, directory, [], launcher.Lease, launcher.atomic_json), 0)
            self.assertNotIn("agent_progress_stalled", (directory / "watcher.jsonl").read_text())

    def test_only_recoverable_failures_restart(self):
        self.assertTrue(watcher.should_restart(1, {"retryable": True}))
        self.assertTrue(watcher.should_restart(-9, {}))
        self.assertTrue(watcher.should_restart(24, {}))
        self.assertFalse(watcher.should_restart(1, {"retryable": False}))
        for status in ("complete", "usageLimited", "budgetLimited"):
            self.assertFalse(watcher.should_restart(-9, {"goal": {"status": status}}, watchdog=True))
        for code in (0, 10, 20, 21, 22, 23):
            self.assertFalse(watcher.should_restart(code, {}))
        self.assertFalse(watcher.should_restart(-9, {}, stopped=True))

    def test_only_classified_transients_restart_and_user_stops_do_not(self):
        for code, state in ((23, {"stop_reason": "turn_failed", "last_error": {"codexErrorInfo": "serverOverloaded"}}),
                            (23, {"stop_reason": "server_error", "last_error": {"codexErrorInfo": "rateLimitExceeded"}}),
                            (23, {"stop_reason": "rate_limit"})):
            with self.subTest(code=code, state=state):
                self.assertTrue(watcher.should_restart(code, state))
                self.assertFalse(watcher.should_restart(code, state, stopped=True))
        for reason in ("work_window", "signal_2", "signal_15", "signal_1"):
            state = {"goal": {"status": "paused"}, "stop_reason": reason}
            self.assertFalse(watcher.should_restart(10, state))
        self.assertFalse(watcher.should_restart(10, {"stop_reason": "signal_15"}, watchdog=True))
        self.assertFalse(watcher.should_restart(20, {"goal": {"status": "blocked"}}))
        self.assertFalse(watcher.should_restart(10, {"goal": {"status": "paused"}}))

    def test_backoff_stays_bounded_after_months_of_retries(self):
        self.assertEqual([watcher.restart_delay(5, n) for n in range(1, 6)], [5, 10, 20, 40, 60])
        self.assertEqual(watcher.restart_delay(5, 10 ** 9), 60)
        self.assertEqual(watcher.restart_delay(0, 10 ** 9), 0)

    def test_unlimited_supervisor_recovers_more_than_three_times_then_stops_on_quota(self):
        source = r'''
import json,os,sys
from pathlib import Path
path=Path(__file__).resolve().parents[1]/'.git/os-autopilot/state.json'
state=json.loads(path.read_text()) if path.exists() else {'thread_id':'retained-thread','attempts':0,'windows':[]}
state['attempts']+=1
state['windows'].append(float(sys.argv[sys.argv.index('--hours')+1]))
scenarios=[(23,'blocked','turn_failed'),(23,'active','server_error'),(23,'paused','rate_limit'),
           (1,'paused','launcher_error'),(24,'active','active_goal_did_not_continue'),
           (21,'blocked','quota_exhausted')]
code,status,reason=scenarios[state['attempts']-1]
state.update(worker_pid=os.getpid(),retryable=True,goal={'status':status},stop_reason=reason)
state['last_error']={'codexErrorInfo':'serverOverloaded'}
path.write_text(json.dumps(state))
sys.exit(code)
'''
        with tempfile.TemporaryDirectory(prefix="os-goal-continuous-") as temp:
            repo = Path(temp)
            (repo / "scripts").mkdir()
            (repo / "scripts/run_os_goal.py").write_text(source)
            directory = repo / ".git/os-autopilot"
            args = launcher.arguments(["--restart-delay", "0"])
            with redirect_stdout(io.StringIO()):
                code = watcher.supervise(args, repo, directory, [], launcher.Lease, launcher.atomic_json)
            self.assertEqual(code, 21)
            state = json.loads((directory / "state.json").read_text())
            self.assertEqual(state["thread_id"], "retained-thread")
            self.assertEqual(state["attempts"], 6)
            self.assertEqual(state["windows"], [0] * 6)
            self.assertEqual(json.loads((directory / "watcher.json").read_text())["restarts"], 5)

    def test_recovery_keeps_thread_and_original_work_window(self):
        source = r'''
import json,os,sys
from pathlib import Path
path=Path(__file__).resolve().parents[1]/'.git/os-autopilot/state.json'
state=json.loads(path.read_text()) if path.exists() else {'thread_id':'retained-thread','windows':[]}
state['windows'].append(float(sys.argv[sys.argv.index('--hours')+1]))
state['worker_pid']=os.getpid()
state['retryable']=True
state['goal']={'status':'complete' if '--recovered' in sys.argv else 'active'}
path.write_text(json.dumps(state))
sys.exit(0 if '--recovered' in sys.argv else 1)
'''
        with tempfile.TemporaryDirectory(prefix="os-goal-watcher-test-") as temp:
            repo = Path(temp)
            (repo / "scripts").mkdir()
            (repo / "scripts/run_os_goal.py").write_text(source)
            directory = repo / ".git/os-autopilot"
            args = launcher.arguments(["--hours", "0.01", "--restart-delay", "0", "--max-restarts", "1"])
            with redirect_stdout(io.StringIO()):
                code = watcher.supervise(args, repo, directory, [], launcher.Lease, launcher.atomic_json)
            self.assertEqual(code, 0)
            state = json.loads((directory / "state.json").read_text())
            self.assertEqual(state["thread_id"], "retained-thread")
            self.assertEqual(len(state["windows"]), 2)
            self.assertLess(state["windows"][1], state["windows"][0])
            self.assertEqual(json.loads((directory / "watcher.json").read_text())["restarts"], 1)

    def test_server_retirement_does_not_signal_reused_or_unverified_pid(self):
        state = {"server_pid": 123, "server_start": "original", "worker_pid": 456}
        with patch.object(watcher, "process_start", return_value="replacement"), patch.object(watcher.os, "kill") as kill:
            self.assertTrue(watcher.retire_server(state, 456))
            kill.assert_not_called()
        with patch.object(watcher, "process_start", return_value="original"), patch.object(watcher.os, "kill") as kill:
            self.assertFalse(watcher.retire_server(state, 999))
            kill.assert_not_called()

    def test_stalled_worker_recovers_without_losing_session(self):
        source = r'''
import json,os,sys,time
from pathlib import Path
path=Path(__file__).resolve().parents[1]/'.git/os-autopilot/state.json'
state={'thread_id':'stalled-thread','worker_pid':os.getpid(),
       'goal':{'status':'complete' if '--recovered' in sys.argv else 'active'}}
path.write_text(json.dumps(state))
if '--recovered' not in sys.argv: time.sleep(10)
'''
        with tempfile.TemporaryDirectory(prefix="os-goal-watchdog-test-") as temp:
            repo = Path(temp)
            (repo / "scripts").mkdir()
            (repo / "scripts/run_os_goal.py").write_text(source)
            directory = repo / ".git/os-autopilot"
            args = launcher.arguments(["--hours", "0", "--restart-delay", "0",
                                       "--max-restarts", "1", "--watchdog-seconds", "0.05",
                                       "--heartbeat-seconds", "0.025"])
            console = io.StringIO()
            with redirect_stdout(console):
                self.assertEqual(watcher.supervise(args, repo, directory, [], launcher.Lease, launcher.atomic_json), 0)
            self.assertIn("[os-watch] HEARTBEAT alive", console.getvalue())
            self.assertIn("state_updated=", console.getvalue())
            state = json.loads((directory / "state.json").read_text())
            self.assertEqual(state["thread_id"], "stalled-thread")
            self.assertEqual(state["goal"]["status"], "complete")
            events = [json.loads(line)["event"] for line in (directory / "watcher.jsonl").read_text().splitlines()]
            self.assertIn("heartbeat_stalled", events)
            self.assertIn("restarting_saved_session", events)


class TransportTests(unittest.TestCase):
    def test_questions_return_standing_instruction_without_selecting_approval_or_secret(self):
        source = r'''
import json,os,sys
request=json.loads(sys.stdin.readline())
event={'method':'item/tool/requestUserInput','id':99,'params':{'questions':[
    {'id':'approach','options':[{'label':'Accept'},{'label':'Decline'}]},
    {'id':'password','isSecret':True}]}}
sys.stdout.write(json.dumps(event)+'\n'); sys.stdout.flush()
reply=json.loads(sys.stdin.readline())
sys.stdout.write(json.dumps({'id':request['id'],'result':{'reply':reply,
    'git_prompt':os.environ['GIT_TERMINAL_PROMPT']}})+'\n'); sys.stdout.flush()
sys.stdin.read()
'''
        with tempfile.TemporaryDirectory(prefix="os-goal-unattended-") as temp:
            rpc = launcher.RPC([sys.executable, "-u", "-c", source], Path(temp), lambda e: None)
            try:
                result = rpc.call("initialize", {}, timeout=5)
                answers = result["reply"]["result"]["answers"]
                self.assertEqual(answers["approach"]["answers"], [launcher.AUTONOMY_REPLY])
                self.assertEqual(answers["password"]["answers"], [])
                self.assertEqual(result["git_prompt"], "0")
                directory = os.environ.get("OS_GOAL_PROTOCOL_SCHEMA")
                if directory:
                    import jsonschema
                    schema = json.loads((Path(directory) / "ToolRequestUserInputResponse.json").read_text())
                    jsonschema.Draft7Validator(schema).validate(result["reply"]["result"])
            finally:
                rpc.close()

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
