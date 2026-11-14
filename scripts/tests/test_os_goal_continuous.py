#!/usr/bin/env python3
"""Offline continuous-run integration: fake RPC only, no model or OS workload."""

from contextlib import redirect_stdout
import copy
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts.tests.test_os_goal_launcher import FakeRPC, goal, launcher


class ContinuousCampaignTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="os-goal-continuous-test-")
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name) / "os-autopilot"
        self.directory.mkdir()
        self.args = launcher.arguments([
            "--hours", "0", "--agent-windows", "off", "--recovered",
            "--repair-agent-failures",
        ])
        self.clock = [100.0]

    def saved(self, current):
        launcher.atomic_json(self.directory / "state.json", {
            "schema_version": 1, "repo": str(self.directory),
            "thread_id": "test-thread", "goal": current,
        })

    def state(self):
        return json.loads((self.directory / "state.json").read_text())

    def run_fake(self, rpc, expected):
        # This exemption is scoped to an injected fake transport. It neither
        # changes production resource admission nor admits a real workload.
        self.assertIsInstance(rpc, FakeRPC)
        with patch.object(launcher, "check_resources"), patch.object(
                launcher.time, "monotonic", side_effect=lambda: self.clock[0]), \
                redirect_stdout(io.StringIO()):
            campaign = launcher.Campaign(
                self.args, self.directory, self.directory, rpc.factory)
            self.assertEqual(campaign.run(), expected)
        return self.state()

    def starts(self, rpc):
        return [params for method, params in rpc.calls if method == "turn/start"]

    def assert_no_activation(self, rpc):
        self.assertFalse(any(method == "thread/goal/set" and params.get("status") == "active"
                             for method, params in rpc.calls))
        self.assertFalse(any(method == "thread/start" for method, _ in rpc.calls))

    def test_without_repair_blocked_transition_exits_twenty(self):
        self.args.repair_agent_failures = False
        self.saved(goal())
        rpc = FakeRPC(self.args, goal(), [lambda r: (r.completed(), r.status("blocked"))])
        state = self.run_fake(rpc, 20)
        self.assertEqual(state["goal"]["status"], "blocked")
        self.assertEqual(self.starts(rpc), [])
        self.assert_no_activation(rpc)

    def test_recovered_blocked_root_gets_one_diagnostic_without_activation(self):
        self.saved(goal("blocked"))

        def finish_review(rpc):
            self.assertEqual(rpc.goal["status"], "blocked")
            self.assertEqual(len(self.starts(rpc)), 1)
            prompt = self.starts(rpc)[0]["input"][0]["text"]
            self.assertIn("same-Root diagnostic review", prompt)
            self.assertEqual(self.starts(rpc)[0]["threadId"], "test-thread")
            rpc.completed()

        def stop_wait(rpc):
            self.assertEqual(self.state()["phase"], "waiting_for_input")
            self.assertEqual(self.state()["active_turns"], {})
            self.assertEqual(len(self.starts(rpc)), 1)
            rpc.status("paused")

        rpc = FakeRPC(self.args, goal("blocked"), [finish_review, stop_wait])
        state = self.run_fake(rpc, 10)
        self.assertEqual(len(state["blocked_repair_reviews"]), 1)
        self.assert_no_activation(rpc)

    def test_finished_diagnostic_waits_past_continuation_timeout(self):
        self.saved(goal())

        def finish_review(rpc):
            self.assertEqual(len(self.starts(rpc)), 1)
            rpc.completed()
            self.clock[0] = 221.0

        def observe_wait(rpc):
            state = self.state()
            self.assertEqual(state["phase"], "waiting_for_input")
            self.assertEqual(state["goal"]["status"], "blocked")
            self.assertEqual(state["active_turns"], {})
            self.assertEqual(len(self.starts(rpc)), 1)
            self.assertNotIn("transport_failure", state)
            self.clock[0] = 500.0

        rpc = FakeRPC(self.args, goal(), [
            lambda r: (r.completed(), r.status("blocked")), finish_review,
            observe_wait, lambda r: r.status("paused"),
        ])
        state = self.run_fake(rpc, 10)
        self.assertNotEqual(state["stop_reason"], "active_goal_did_not_continue")
        self.assertEqual(len(self.starts(rpc)), 1)
        self.assert_no_activation(rpc)

    def test_queued_user_instruction_reaches_idle_blocked_root(self):
        self.saved(goal())
        queued = []
        text = "New eligible input: validate the corrected source-fetch workflow."

        def queue_after_review(rpc):
            rpc.completed()
            # Exercise the public --instruct path. Only Git directory discovery
            # is faked so this command addresses the isolated campaign fixture.
            with patch.object(launcher, "REPO", self.directory), patch.object(
                    launcher.subprocess, "check_output", return_value=str(self.directory.parent)):
                self.assertEqual(launcher.main(["--instruct", text]), 0)
            queued.append(next((self.directory / "instructions/pending").glob("*.json")).stem)

        def receive_instruction(rpc):
            starts = self.starts(rpc)
            self.assertEqual(len(starts), 2)
            self.assertEqual(starts[1]["threadId"], "test-thread")
            self.assertIn(text, starts[1]["input"][0]["text"])
            self.assertIn(queued[0], starts[1]["input"][0]["text"])
            self.assertEqual(rpc.goal["status"], "blocked")
            rpc.completed()
            rpc.status("paused")

        rpc = FakeRPC(self.args, goal(), [
            lambda r: (r.completed(), r.status("blocked")),
            queue_after_review, receive_instruction,
        ])
        state = self.run_fake(rpc, 10)
        self.assertEqual(state["last_instruction"]["id"], queued[0])
        self.assertEqual(state["last_instruction"]["status"], "accepted_by_server")
        self.assertTrue((self.directory / "instructions/delivered" / (queued[0] + ".json")).is_file())
        self.assertEqual(list((self.directory / "instructions/pending").glob("*.json")), [])
        self.assert_no_activation(rpc)

    def test_delayed_turn_started_notification_cannot_duplicate_dispatch(self):
        class DelayedNotificationRPC(FakeRPC):
            def call(inner, method, params, **kwargs):
                if method == "turn/start":
                    inner.calls.append((method, params))
                    turn = {"id": "accepted-before-notification", "items": [], "status": "inProgress"}
                    inner.turns[params["threadId"]] = turn
                    return {"turn": dict(turn)}
                return super().call(method, params, **kwargs)

        self.saved(goal())

        def queue_during_review(rpc):
            self.assertEqual(self.state()["active_turns"], {
                "test-thread": "accepted-before-notification"})
            launcher.queue_instruction(self.directory, "Use the newly corrected source manifest.")

        def observe_steering(rpc):
            self.assertEqual(len(self.starts(rpc)), 1)
            steers = [p for method, p in rpc.calls if method == "turn/steer"]
            self.assertEqual(len(steers), 1)
            self.assertEqual(steers[0]["expectedTurnId"], "accepted-before-notification")
            rpc.status("paused")

        rpc = DelayedNotificationRPC(self.args, goal(), [
            lambda r: (r.completed(), r.status("blocked")), queue_during_review, observe_steering,
        ])
        state = self.run_fake(rpc, 10)
        self.assertEqual(state["last_instruction"]["status"], "accepted_by_server")
        self.assert_no_activation(rpc)

    def test_server_resumption_changes_waiting_phase_to_running(self):
        self.saved(goal())

        def resume_from_new_work(rpc):
            self.assertEqual(self.state()["phase"], "waiting_for_input")
            rpc.status("active")
            rpc.started("new-eligible-work")

        def finish_new_work(rpc):
            self.assertEqual(self.state()["phase"], "running")
            self.assertEqual(self.state()["active_turns"], {"test-thread": "new-eligible-work"})
            rpc.completed()
            rpc.status("paused")

        rpc = FakeRPC(self.args, goal(), [
            lambda r: (r.completed(), r.status("blocked")), lambda r: r.completed(),
            resume_from_new_work, finish_new_work,
        ])
        self.run_fake(rpc, 10)
        self.assertEqual(len(self.starts(rpc)), 1)
        self.assert_no_activation(rpc)

    def test_fresh_pause_policy_and_usage_stops_are_never_repaired(self):
        cases = (
            ("pause", 10, None),
            ("policy", 23, "server_error"),
            ("usage", 21, "included_usage_guard"),
        )
        for kind, expected, reason in cases:
            with self.subTest(kind=kind):
                self.saved(goal())

                def stopped(rpc):
                    rpc.completed()
                    rpc.status("blocked")
                    if kind == "pause":
                        rpc.status("paused")
                    elif kind == "policy":
                        rpc.emit("error", {"threadId": "test-thread", "error": {
                            "message": "service stop", "codexErrorInfo": "cyberPolicy"},
                            "willRetry": False})
                    else:
                        limits = copy.deepcopy(rpc.limits)
                        limits["primary"]["usedPercent"] = 100
                        rpc.emit("account/rateLimits/updated", {"rateLimits": limits})

                rpc = FakeRPC(self.args, goal(), [stopped])
                state = self.run_fake(rpc, expected)
                self.assertEqual(self.starts(rpc), [])
                self.assertEqual(state["stop_reason"], reason)
                self.assert_no_activation(rpc)

    def test_stop_arriving_during_final_diagnostic_read_prevents_dispatch(self):
        for kind, expected in (("pause", 10), ("policy", 23), ("usage", 21)):
            with self.subTest(kind=kind):
                self.saved(goal())

                class StoppingReadRPC(FakeRPC):
                    armed = False

                    def call(inner, method, params, **kwargs):
                        if inner.armed and method == "thread/goal/get":
                            inner.armed = False
                            if kind == "pause":
                                inner.status("paused")
                            elif kind == "policy":
                                inner.emit("error", {"threadId": "test-thread", "error": {
                                    "codexErrorInfo": "cyberPolicy"}, "willRetry": False})
                            else:
                                limits = copy.deepcopy(inner.limits)
                                limits["primary"]["usedPercent"] = 100
                                inner.emit("account/rateLimits/updated", {"rateLimits": limits})
                        return super().call(method, params, **kwargs)

                def block(rpc):
                    rpc.completed()
                    rpc.status("blocked")
                    rpc.armed = True

                rpc = StoppingReadRPC(self.args, goal(), [block, lambda r: None])
                self.run_fake(rpc, expected)
                self.assertEqual(self.starts(rpc), [])
                self.assert_no_activation(rpc)

    def test_uncertain_diagnostic_delivery_is_not_resent_after_recovery(self):
        class UncertainRPC(FakeRPC):
            def call(self, method, params, **kwargs):
                result = super().call(method, params, **kwargs)
                if method == "turn/start":
                    # Server accepted; the client never received its receipt.
                    raise TimeoutError("accepted turn, lost reply")
                return result

        self.saved(goal())
        rpc = UncertainRPC(self.args, goal(), [lambda r: (r.completed(), r.status("blocked"))])
        state = self.run_fake(rpc, 23)
        self.assertEqual(len(self.starts(rpc)), 1)
        self.assertEqual(state["transport_uncertain"]["method"], "turn/start")
        receipts = state["blocked_repair_reviews"]
        self.assertEqual(next(iter(receipts.values()))["status"], "delivery_uncertain")
        recovered = FakeRPC(self.args, goal("blocked"))
        state = self.run_fake(recovered, 1)
        self.assertEqual(recovered.calls, [])
        self.assertEqual(state["blocked_repair_reviews"], receipts)
        self.assert_no_activation(rpc)

    def test_completed_diagnostic_key_is_stable_across_recovery(self):
        self.saved(goal())
        rpc = FakeRPC(self.args, goal(), [
            lambda r: (r.completed(), r.status("blocked")),
            lambda r: r.completed(),
            lambda r: r.on_event.__self__.on_signal(2, None),
        ])
        first = self.run_fake(rpc, 10)
        receipts = first["blocked_repair_reviews"]
        self.assertEqual(len(receipts), 1)
        self.assertEqual(first["goal"]["status"], "blocked")
        changed = dict(first["goal"], updatedAt=99, tokensUsed=9000, timeUsedSeconds=700)

        def finish_wait(rpc):
            self.assertEqual(self.starts(rpc), [])
            self.assertEqual(self.state()["phase"], "waiting_for_input")
            rpc.on_event.__self__.on_signal(2, None)

        recovered = FakeRPC(self.args, changed, [finish_wait])
        final = self.run_fake(recovered, 10)
        self.assertEqual(final["blocked_repair_reviews"], receipts)
        self.assertEqual(self.starts(recovered), [])
        self.assert_no_activation(recovered)


class MilestoneAcceptanceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="os-milestone-acceptance-")
        self.addCleanup(self.temp.cleanup)
        self.repo = Path(self.temp.name)
        self.path = self.repo / "docs/verification/m14-m15-closure-progress.json"
        self.path.parent.mkdir(parents=True)

    def accepted(self):
        summaries, rows = {}, []
        for milestone, files, integrations in (("M14", 6, 3), ("M15", 8, 4)):
            ids = (["%s-F%02d" % (milestone, n) for n in range(1, files + 1)] +
                   ["%s-I%02d" % (milestone, n) for n in range(1, integrations + 1)])
            summaries[milestone] = {"original_gate_ids": ids,
                                    "milestone_accepted": True, "completion_percent": 100}
            rows.extend({"id": ident, "accepted": True, "completion_percent": 100} for ident in ids)
        return {"original_criteria_unchanged": True, "summaries": summaries, "requirements": rows}

    def write(self, data):
        self.path.write_text(json.dumps(data))

    def test_percentages_never_replace_original_binary_acceptance(self):
        for mutation in (
            lambda d: d["summaries"]["M14"].update(milestone_accepted=False),
            lambda d: d["summaries"]["M15"].update(milestone_accepted=False),
            lambda d: d["requirements"][0].update(accepted=False),
            lambda d: d.update(original_criteria_unchanged=False),
        ):
            data = self.accepted()
            mutation(data)
            with self.subTest(data=data):
                self.write(data)
                self.assertFalse(launcher.m14_m15_closed(self.repo))

    def test_missing_and_duplicate_original_gates_are_rejected(self):
        for mutation in (
            lambda d: d["requirements"].pop(),
            lambda d: d["requirements"].append(dict(d["requirements"][0])),
            lambda d: d["summaries"]["M14"]["original_gate_ids"].pop(),
            lambda d: d["summaries"]["M15"]["original_gate_ids"].append("M15-F01"),
        ):
            data = self.accepted()
            mutation(data)
            with self.subTest(data=data):
                self.write(data)
                self.assertFalse(launcher.m14_m15_closed(self.repo))

    def test_both_accepted_milestones_checkpoint_the_larger_goal(self):
        self.write(self.accepted())
        self.assertTrue(launcher.m14_m15_closed(self.repo))
        args = launcher.arguments([
            "--hours", "0", "--agent-windows", "off", "--recovered", "--stop-after-m14-m15",
        ])
        launcher.atomic_json(self.repo / "state.json", {
            "schema_version": 1, "repo": str(self.repo),
            "thread_id": "test-thread", "goal": goal(),
        })
        rpc = FakeRPC(args, goal())
        with patch.object(launcher, "check_resources"), redirect_stdout(io.StringIO()):
            campaign = launcher.Campaign(args, self.repo, self.repo, rpc.factory)
            self.assertEqual(campaign.run(), 10)
        state = json.loads((self.repo / "state.json").read_text())
        self.assertEqual(state["stop_reason"], "requested_milestones_complete")
        self.assertEqual(state["goal"]["status"], "paused")
        self.assertEqual(state["goal"]["objective"], launcher.OBJECTIVE)
        updates = [params["status"] for method, params in rpc.calls if method == "thread/goal/set"]
        self.assertEqual(updates, ["paused"])
        self.assertEqual(state["active_turns"], {})


    def run_terminal_milestone_case(self, rpc, expected, status, reason=None):
        # All transport and state are isolated FakeRPC/tempdir fixtures. The
        # original ledger is genuinely closed, not a mocked acceptance result.
        self.assertIsInstance(rpc, FakeRPC)
        with patch.object(launcher, "check_resources"), redirect_stdout(io.StringIO()):
            campaign = launcher.Campaign(self.terminal_args, self.repo, self.repo, rpc.factory)
            self.assertEqual(campaign.run(), expected)
        self.assertTrue(rpc.closed)
        state = json.loads((self.repo / "state.json").read_text())
        self.assertEqual(state["goal"], rpc.goal)
        self.assertEqual(state["goal"]["status"], status)
        self.assertEqual(state["stop_reason"], reason)
        self.assertEqual(state["exit_code"], expected)
        self.assertEqual(state["stop_decision"]["goal_status"], status)
        self.assertEqual(state["stop_decision"]["reason"], reason)
        self.assertFalse(campaign.checkpoint_requested)
        self.assertFalse(any(method in {"thread/start", "thread/goal/set", "turn/start", "turn/steer"}
                             for method, _ in rpc.calls))
        records = [json.loads(line) for line in (self.repo / "stop-events.jsonl").read_text().splitlines()]
        stopped = records[-1]
        self.assertEqual(stopped, json.loads((self.repo / "latest-stop.json").read_text()))
        self.assertEqual(stopped["event"], "worker_stopped")
        self.assertEqual(stopped["exit_code"], expected)
        self.assertEqual(stopped["goal_status"], status)
        self.assertEqual(stopped["reason"], reason)
        self.assertEqual(stopped["log_dir"], state["log_dir"])
        self.assertNotEqual(stopped["category"], "requested_milestones_complete")
        self.assertNotIn("requested_milestones_complete", [row["reason"] for row in records])
        return state, stopped

    def terminal_milestone_saved(self, status):
        self.terminal_args = launcher.arguments([
            "--hours", "0", "--agent-windows", "off", "--recovered", "--stop-after-m14-m15",
        ])
        current = goal(status)
        launcher.atomic_json(self.repo / "state.json", {
            "schema_version": 1, "repo": str(self.repo),
            "thread_id": "test-thread", "goal": current,
        })
        return current

    def test_milestone_checkpoint_preserves_saved_complete(self):
        self.write(self.accepted())
        self.assertTrue(launcher.m14_m15_closed(self.repo))
        current = self.terminal_milestone_saved("complete")
        rpc = FakeRPC(self.terminal_args, copy.deepcopy(current))
        state, stopped = self.run_terminal_milestone_case(rpc, 0, "complete")
        self.assertEqual(state["goal"], current)
        self.assertEqual(stopped["category"], "goal_completed")
        self.assertFalse(any(method == "thread/resume" for method, _ in rpc.calls))

    def test_milestone_checkpoint_preserves_recovered_usage_limited(self):
        self.write(self.accepted())
        self.assertTrue(launcher.m14_m15_closed(self.repo))
        current = self.terminal_milestone_saved("usageLimited")
        rpc = FakeRPC(self.terminal_args, copy.deepcopy(current))
        state, _ = self.run_terminal_milestone_case(rpc, 21, "usageLimited")
        self.assertEqual(state["goal"], current)
        self.assertFalse(any(method == "thread/resume" for method, _ in rpc.calls))

    def test_milestone_checkpoint_preserves_recovered_budget_limited(self):
        self.write(self.accepted())
        self.assertTrue(launcher.m14_m15_closed(self.repo))
        current = self.terminal_milestone_saved("budgetLimited")
        rpc = FakeRPC(self.terminal_args, copy.deepcopy(current))
        state, _ = self.run_terminal_milestone_case(rpc, 22, "budgetLimited")
        self.assertEqual(state["goal"], current)
        self.assertFalse(any(method == "thread/resume" for method, _ in rpc.calls))

    def test_live_terminal_update_precedes_newly_closed_milestone_checkpoint(self):
        for status, expected in (("complete", 0), ("usageLimited", 21), ("budgetLimited", 22)):
            with self.subTest(status=status):
                data = self.accepted()
                data["requirements"][0]["accepted"] = False
                self.write(data)
                self.assertFalse(launcher.m14_m15_closed(self.repo))
                self.terminal_milestone_saved("active")

                def finish(rpc):
                    rpc.completed()
                    rpc.status(status)
                    self.write(self.accepted())
                    self.assertTrue(launcher.m14_m15_closed(self.repo))

                rpc = FakeRPC(self.terminal_args, goal(), [finish])
                self.run_terminal_milestone_case(rpc, expected, status)

    def test_terminal_goal_discovered_by_checkpoint_pause_read_is_preserved(self):
        for status, expected in (("complete", 0), ("usageLimited", 21), ("budgetLimited", 22)):
            with self.subTest(status=status):
                self.write(self.accepted())
                self.assertTrue(launcher.m14_m15_closed(self.repo))
                self.terminal_milestone_saved("active")

                class TerminalAtPauseRPC(FakeRPC):
                    goal_reads = 0
                    terminal_read_delivered = False

                    def call(inner, method, params, **kwargs):
                        if method == "thread/goal/get":
                            inner.goal_reads += 1
                            # The saved-goal read and post-resume read stay
                            # ACTIVE. The checkpoint's real pause() read is the
                            # first observation of this external terminal state.
                            if inner.goal_reads == 3:
                                inner.completed()
                                inner.status(status)
                                inner.terminal_read_delivered = True
                        return super().call(method, params, **kwargs)

                rpc = TerminalAtPauseRPC(self.terminal_args, goal())
                self.run_terminal_milestone_case(rpc, expected, status)
                self.assertTrue(rpc.terminal_read_delivered)

    def test_current_hard_stop_precedes_terminal_and_closed_milestones(self):
        for kind, expected, reason, category in (
            ("usage", 21, "included_usage_guard", "usage_limit"),
            ("policy", 23, "server_error", "policy_rejection"),
        ):
            with self.subTest(kind=kind):
                data = self.accepted()
                data["requirements"][0]["accepted"] = False
                self.write(data)
                self.terminal_milestone_saved("active")

                def stop(rpc):
                    rpc.completed()
                    rpc.status("complete")
                    self.write(self.accepted())
                    if kind == "usage":
                        limits = copy.deepcopy(rpc.limits)
                        limits["primary"]["usedPercent"] = 100
                        rpc.emit("account/rateLimits/updated", {"rateLimits": limits})
                    else:
                        rpc.emit("error", {"threadId": "test-thread", "error": {
                            "message": "service stop", "codexErrorInfo": "cyberPolicy"},
                            "willRetry": False})

                rpc = FakeRPC(self.terminal_args, goal(), [stop])
                _, stopped = self.run_terminal_milestone_case(rpc, expected, "complete", reason)
                self.assertEqual(stopped["category"], category)



if __name__ == "__main__":
    unittest.main()
