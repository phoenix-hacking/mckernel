"""Unattended control decisions through the real controller with a fake RPC.

These tests launch no model, native workload, service, or external operation.
They verify the actual delivery/advisory boundary, including interrupted writes.
"""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_os_goal_launcher as fixtures
import os_goal_progress as progress
FakeRPC, goal, launcher = fixtures.FakeRPC, fixtures.goal, fixtures.launcher


class ReliabilityIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.CampaignTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.tearDown)
        self.repo = self.fixture.directory
        destination = self.repo / progress.LEDGER_PATH
        destination.parent.mkdir(parents=True)
        shutil.copyfile(launcher.REPO / progress.LEDGER_PATH, destination)
        ledger = json.loads(destination.read_text())
        # These controller scenarios require two open originals; conditions,
        # identities and denominator remain the real immutable originals.
        for row in ledger["tasks"]:
            if row["id"] in {"M15-F02-complete-ABI-behavior", "M15-F05-original-behavior"}:
                row["percent_complete"] = 0
        destination.write_text(json.dumps(ledger))
        self.closed_count = sum(row.get("counted_in_requirement_rollup") is True and row["percent_complete"] == 100
                                for row in ledger["tasks"])
        self.open_ids = {row["original_check"] for row in progress.remaining_work_view(ledger)}
        self.fixture.args.progress_control = True
        self.fixture.args.quiet = True
        self.fixture.saved(goal())
        self.rpc = FakeRPC(self.fixture.args, goal())
        self.campaign = launcher.Campaign(self.fixture.args, self.repo, self.repo, self.rpc.factory)
        self.addCleanup(self.campaign.output.close)
        self.campaign.rpc = self.rpc.factory([], self.campaign.log_dir, self.campaign.event)
        self.campaign.controlled = True
        self.campaign.goal = deepcopy(self.rpc.goal)
        self.rpc.started()
        self.campaign.save(phase="running", goal=self.campaign.goal,
                           worker_pid=os.getpid(), worker_start="123", server_pid=1234, server_start="456")
        self.check = "M15-F02-complete-ABI-behavior"

    def target(self):
        return {"schema_version": 1, "original_check": self.check,
                "owner": "existing executor owner", "next_action": "Finish the next missing required executor branch",
                "input_bindings": {}, "evidence": [], "operation": None}

    def steers(self):
        return [params for method, params in self.rpc.calls if method == "turn/steer"]

    def poll_again(self):
        self.campaign.next_progress_check = 0
        self.campaign.poll_progress()

    def test_missing_target_drives_one_concrete_same_root_decision(self):
        before = deepcopy(self.campaign.goal)
        self.campaign.poll_progress()
        self.assertEqual(len(self.steers()), 1)
        request = self.steers()[0]
        self.assertEqual(request["threadId"], "test-thread")
        self.assertEqual(request["expectedTurnId"], "turn-1")
        text = request["input"][0]["text"]
        self.assertIn("Harness-origin", text)
        self.assertIn("concrete decision", text)
        self.assertIn("--set-closure-target", text)
        self.assertTrue(any(ident + " [parent=" in text for ident in self.open_ids))
        self.assertIn("UNASSESSED, not execution grants", text)
        self.assertIn("install missing required packages", text)
        self.assertIn("real provider adapter as our engineering work", text)
        self.assertNotIn("M14-I01-ACCEPT [", text)
        self.assertFalse(text.startswith("Live user instruction"))
        self.assertEqual(self.campaign.goal, before)
        self.rpc.started("turn-2")
        self.poll_again()
        self.assertEqual(len(self.steers()), 1)
        self.assertFalse(any(method in {"thread/start", "thread/resume", "thread/goal/set"}
                             for method, _ in self.rpc.calls))

    def test_startup_contract_demands_actual_input_resolution_and_remaining_original_work(self):
        text = self.campaign.instructions()
        self.assertIn("--set-closure-target PATH", text)
        self.assertIn("install missing required packages", text)
        self.assertIn("derive the real source/header/caller/ABI", text)
        self.assertIn("real provider adapter as our engineering work", text)
        self.assertIn("immediately hand off to the next open original", text)
        self.assertIn("UNASSESSED, not execution grants", text)

    def test_target_submission_is_applied_by_controller_and_grants_nothing(self):
        source = self.repo / "target.json"
        source.write_text(json.dumps(self.target()))
        ident = launcher.queue_closure_target(self.repo, self.repo, source)
        self.assertEqual(launcher.queue_closure_target(self.repo, self.repo, source), ident)
        self.assertNotIn("closure_target", self.campaign.state)
        self.campaign.poll_closure_targets()
        self.assertEqual(self.campaign.state["closure_target"], self.target())
        receipt = self.campaign.state["closure_target_receipt"]
        self.assertEqual(receipt["status"], "applied")
        self.assertIs(receipt["execution_admission"], False)
        self.assertTrue((self.repo / "closure-targets/applied" / (ident + ".json")).is_file())
        self.assertEqual(launcher.queue_closure_target(self.repo, self.repo, source), ident)
        self.assertEqual(self.rpc.calls, [])

    def test_target_from_previous_invocation_is_refused(self):
        source = self.repo / "target.json"
        source.write_text(json.dumps(self.target()))
        launcher.queue_closure_target(self.repo, self.repo, source)
        self.campaign.state["worker_start"] = "different-birth"
        self.campaign.poll_closure_targets()
        self.assertEqual(self.campaign.state["closure_target_receipt"]["status"], "refused")
        self.assertNotIn("closure_target", self.campaign.state)
        self.assertEqual(self.rpc.calls, [])

    def test_newest_target_supersedes_older_pending_plans_in_submission_order(self):
        source = self.repo / "target.json"
        old = self.target()
        source.write_text(json.dumps(old))
        first = launcher.queue_closure_target(self.repo, self.repo, source)
        new = dict(old, next_action="Use the newly supplied exact current provider evidence")
        source.write_text(json.dumps(new))
        second = launcher.queue_closure_target(self.repo, self.repo, source)
        self.campaign.poll_closure_targets()
        self.assertEqual(self.campaign.state["closure_target"], new)
        self.assertEqual(self.campaign.state["closure_target_receipt"]["id"], second)
        self.assertEqual(self.campaign.state["closure_target_receipt"]["request_sequence"], 2)
        superseded = launcher._read_private_json(self.repo / "closure-targets/superseded" / (first + ".json"))
        self.assertEqual(superseded["receipt"]["superseded_by"], second)
        self.campaign.poll_closure_targets()
        self.assertEqual(self.campaign.state["closure_target"], new)

    def test_applied_plan_a_can_be_reselected_after_independent_plan_b(self):
        source = self.repo / "target.json"
        plan_a = self.target()
        plan_b = dict(plan_a, original_check="M15-F05-original-behavior", next_action="Resolve the original library provider input")
        ids = []
        for target in (plan_a, plan_b, plan_a):
            source.write_text(json.dumps(target))
            ident = launcher.queue_closure_target(self.repo, self.repo, source)
            self.assertEqual(launcher.queue_closure_target(self.repo, self.repo, source), ident)
            ids.append(ident)
            self.campaign.poll_closure_targets()
            self.assertEqual(self.campaign.state["closure_target"], target)
        self.assertEqual(len(set(ids)), 3)
        self.assertEqual(self.campaign.state["closure_target_receipt"]["request_sequence"], 3)
        first = launcher._read_private_json(self.repo / "closure-targets/applied" / (ids[0] + ".json"))
        third = launcher._read_private_json(self.repo / "closure-targets/applied" / (ids[2] + ".json"))
        self.assertEqual(first["plan_digest"], third["plan_digest"])
        self.assertNotEqual(first["id"], third["id"])
        self.assertEqual(launcher.queue_closure_target(self.repo, self.repo, source), ids[2])

    def test_superseded_plan_a_can_be_reselected_with_a_new_sequence(self):
        source = self.repo / "target.json"
        plan_a = self.target()
        source.write_text(json.dumps(plan_a))
        first = launcher.queue_closure_target(self.repo, self.repo, source)
        source.write_text(json.dumps(dict(plan_a, next_action="Perform the independent current input action")))
        second = launcher.queue_closure_target(self.repo, self.repo, source)
        self.campaign.poll_closure_targets()
        self.assertTrue((self.repo / "closure-targets/superseded" / (first + ".json")).is_file())
        observed = progress.observe_progress(self.repo, self.campaign.state)
        self.campaign.state["progress_monitor"] = observed["monitor"]
        source.write_text(json.dumps(plan_a))
        third = launcher.queue_closure_target(self.repo, self.repo, source)
        self.assertNotIn(third, {first, second})
        self.campaign.poll_closure_targets()
        self.assertEqual(self.campaign.state["closure_target"], plan_a)
        self.assertEqual(self.campaign.state["closure_target_receipt"]["request_sequence"], 3)
        next_observation = progress.observe_progress(self.repo, self.campaign.state)
        self.assertFalse(next_observation["snapshot"]["semantic_progress_changed"])
        self.assertEqual(next_observation["monitor"]["last_semantic_at"], observed["monitor"]["last_semantic_at"])

    def test_pending_stall_is_canceled_when_a_healthy_bounded_operation_is_declared(self):
        target = self.target()
        target["input_bindings"] = {"source": "a" * 64}
        self.campaign.state.update(closure_target=target, user_pause=True)
        self.campaign.poll_progress()
        self.campaign.state["progress_monitor"]["last_semantic_at"] = time.time() - 2500
        self.poll_again()
        self.assertEqual(self.campaign.state["progress_advisory"]["status"], "pending")
        ledger = progress.load_ledger(self.repo)
        row = next(row for row in ledger["tasks"] if row["id"] == self.check)
        now = time.time()
        receipt = {"schema": progress.OPERATION_SCHEMA, "original_check": self.check,
                   "condition_sha256": progress.condition_sha256(row), "input_bindings": target["input_bindings"],
                   "name": "the actual bounded admitted build", "status": "running", "healthy": True,
                   "started_at": now, "observed_at": now, "deadline_at": now + 3600}
        path = self.repo / "operation.json"
        path.write_text(json.dumps(receipt))
        target["operation"] = {"name": receipt["name"], "deadline_at": receipt["deadline_at"],
                               "receipt": {"path": path.name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}}
        self.campaign.state.pop("user_pause")
        self.poll_again()
        self.assertEqual(self.steers(), [])
        self.assertEqual(self.campaign.state["progress_advisory"]["status"], "superseded_before_dispatch")

    def test_pending_failure_is_canceled_after_its_matching_receipt_is_removed(self):
        target = self.target()
        target["input_bindings"] = {"source": "a" * 64}
        ledger = progress.load_ledger(self.repo)
        row = next(row for row in ledger["tasks"] if row["id"] == self.check)
        failure = {"schema": progress.EVIDENCE_SCHEMA, "kind": "ordinary_failure", "status": "failed",
                   "original_check": self.check, "condition_sha256": progress.condition_sha256(row),
                   "input_bindings": target["input_bindings"], "stage": "compile", "diagnostic_sha256": "b" * 64,
                   "defect": "Actual missing required provider", "owner": "existing source owner"}
        path = self.repo / "failure.json"
        path.write_text(json.dumps(failure))
        target["evidence"] = [{"path": path.name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}]
        self.campaign.state.update(closure_target=target, user_pause=True)
        self.campaign.poll_progress()
        self.assertEqual(self.campaign.state["progress_advisory"]["status"], "pending")
        target["evidence"] = []
        self.campaign.state.pop("user_pause")
        self.poll_again()
        self.assertEqual(self.steers(), [])
        self.assertEqual(self.campaign.state["progress_advisory"]["status"], "superseded_before_dispatch")

    def test_pending_review_never_steers_the_obsolete_original_after_target_changes(self):
        self.campaign.state.update(closure_target=self.target(), user_pause=True)
        self.campaign.poll_progress()
        self.campaign.state["progress_monitor"]["last_semantic_at"] = time.time() - 2500
        self.poll_again()
        other = dict(self.target(), original_check="M15-F05-original-behavior")
        self.campaign.state["closure_target"] = other
        self.campaign.state.pop("user_pause")
        self.poll_again()
        self.assertEqual(len(self.steers()), 1)
        self.assertIn("Original target: " + other["original_check"], self.steers()[0]["input"][0]["text"])
        self.assertNotIn("Original target: " + self.check, self.steers()[0]["input"][0]["text"])

    def test_a_proved_pre_rpc_refusal_can_send_once_after_the_stop_clears(self):
        original = self.campaign.save
        stopped = False
        def save(**fields):
            nonlocal stopped
            original(**fields)
            if isinstance(fields.get("progress_review"), dict) and fields["progress_review"].get("status") == "sending" and not stopped:
                self.campaign.stop_reason = "user_requested"
                stopped = True
        self.campaign.save = save
        self.campaign.poll_progress()
        self.assertEqual(self.steers(), [])
        self.assertEqual(self.campaign.state["progress_review"]["status"], "refused_before_rpc")
        self.assertIs(self.campaign.state["progress_review"]["rpc_attempted"], False)
        self.campaign.stop_reason = None
        self.campaign.save = original
        self.poll_again()
        self.assertEqual(len(self.steers()), 1)
        self.poll_again()
        self.assertEqual(len(self.steers()), 1)

    def test_genuine_target_closure_immediately_steers_successor_selection(self):
        self.campaign.state["closure_target"] = self.target()
        self.campaign.poll_progress()
        path = self.repo / progress.LEDGER_PATH
        ledger = json.loads(path.read_text())
        row = next(row for row in ledger["tasks"] if row["id"] == self.check)
        row["percent_complete"] = 100
        path.write_text(json.dumps(ledger))
        self.poll_again()
        self.assertEqual(len(self.steers()), 1)
        self.assertIn("Select the next eligible original check", self.steers()[0]["input"][0]["text"])

    def test_new_qualified_result_cancels_a_pending_stall_before_dispatch(self):
        target = self.target()
        target["input_bindings"] = {"source": "a" * 64}
        self.campaign.state.update(closure_target=target, user_pause=True)
        self.campaign.poll_progress()
        self.campaign.state["progress_monitor"]["last_semantic_at"] = time.time() - 2500
        self.poll_again()
        ledger = progress.load_ledger(self.repo)
        row = next(row for row in ledger["tasks"] if row["id"] == self.check)
        proof = {"schema": progress.EVIDENCE_SCHEMA, "kind": "required_evidence", "status": "qualified",
                 "original_check": self.check, "condition_sha256": progress.condition_sha256(row),
                 "input_bindings": target["input_bindings"], "scope": "partial", "qualified_fact_sha256s": ["b" * 64]}
        path = self.repo / "qualified-result.json"
        path.write_text(json.dumps(proof))
        target["evidence"] = [{"path": path.name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}]
        self.campaign.state.pop("user_pause")
        self.poll_again()
        self.assertEqual(self.steers(), [])
        self.assertTrue(self.campaign.state["progress_snapshot"]["semantic_progress_changed"])
        self.assertEqual(self.campaign.state["progress_advisory"]["status"], "superseded_before_dispatch")

    def test_accepted_advice_has_one_bounded_followup_then_explicit_owner_action_required(self):
        self.campaign.poll_progress()
        first_key = self.campaign.state["progress_review"]["key"]
        now = time.time()
        self.campaign.state["progress_monitor"]["issued_review_keys"][first_key] = now - 2600
        self.campaign.state["progress_review"]["delivered_at"] = now - 2500
        self.rpc.started("turn-2")  # The prior fixture steer finishes its turn.
        self.poll_again()
        self.assertEqual(len(self.steers()), 2)
        self.assertIn("one bounded followup", self.steers()[1]["input"][0]["text"])
        self.assertEqual(self.campaign.state["progress_snapshot"]["decision_status"], "owner_action_required")
        self.poll_again()
        self.assertEqual(len(self.steers()), 2)
        self.assertTrue(self.campaign.state["progress_snapshot"]["review_required"])

    def test_noisy_activity_does_not_avoid_stagnation_decision(self):
        self.campaign.state["closure_target"] = self.target()
        self.campaign.poll_progress()
        self.assertEqual(self.steers(), [])
        self.campaign.state["progress_monitor"]["last_semantic_at"] = time.time() - 2500
        self.campaign.state["agent_event_count"] = 1_000_000
        self.campaign.state["heartbeat_at"] = datetime.now(timezone.utc).isoformat()
        self.poll_again()
        self.assertEqual(len(self.steers()), 1)
        self.assertIn("No original closure", self.steers()[0]["input"][0]["text"])
        self.assertEqual(len(self.campaign.state["progress_snapshot"]["closed_original_checks"]), self.closed_count)

    def test_unresolved_bounded_followup_stops_dispatch_without_a_third_review(self):
        self.campaign.poll_progress()
        first = self.campaign.state["progress_review"]["key"]
        now = time.time()
        self.campaign.state["progress_monitor"]["issued_review_keys"][first] = now - 5200
        self.campaign.state["progress_review"]["delivered_at"] = now - 5000
        self.rpc.started("second-turn")
        self.poll_again()
        followup = self.campaign.state["progress_review"]["key"]
        self.campaign.state["progress_monitor"]["issued_review_keys"][followup] = now - 2600
        self.campaign.state["progress_monitor"]["last_semantic_at"] = now - 6000
        self.campaign.state["progress_review"]["delivered_at"] = now - 2500
        self.rpc.started("third-turn")
        self.poll_again()
        self.assertEqual(len(self.steers()), 2)
        self.assertEqual(self.campaign.stop_reason, "closure_decision_unresolved")
        self.assertFalse(self.campaign.state["controller_dispatch_enabled"])
        self.assertEqual(self.campaign.state["progress_snapshot"]["decision_status"], "stop_required")
        self.assertTrue(self.campaign.state["progress_snapshot"]["stop_required"])

    def test_current_ordinary_failure_drives_a_specific_fix(self):
        target = self.target()
        target["input_bindings"] = {"source": "a" * 64}
        ledger = progress.load_ledger(self.repo)
        row = next(row for row in ledger["tasks"] if row["id"] == self.check)
        receipt = {"schema": progress.EVIDENCE_SCHEMA, "kind": "ordinary_failure", "status": "failed",
                   "original_check": self.check, "condition_sha256": progress.condition_sha256(row),
                   "input_bindings": target["input_bindings"], "stage": "compile",
                   "diagnostic_sha256": "b" * 64, "defect": "Incorrect checked arithmetic in the required caller",
                   "owner": "existing executor owner"}
        path = self.repo / "failure.json"
        path.write_text(json.dumps(receipt))
        target["evidence"] = [{"path": path.name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}]
        self.campaign.state["closure_target"] = target
        self.campaign.poll_progress()
        self.assertEqual(len(self.steers()), 1)
        text = self.steers()[0]["input"][0]["text"]
        self.assertIn(receipt["defect"], text)
        self.assertIn(receipt["owner"], text)
        self.assertIn("run only the affected check", text)
        self.assertEqual(len(self.campaign.state["progress_snapshot"]["closed_original_checks"]), self.closed_count)

    def test_hard_holds_and_user_stop_prevent_advisory_dispatch(self):
        for name in launcher._CONTROL_HOLD_FLAGS + ("transport_uncertain",):
            with self.subTest(name=name):
                self.campaign.state[name] = True
                self.poll_again()
                self.assertEqual(self.steers(), [])
                self.campaign.state.pop(name)
        self.campaign.stop_reason = "signal_15"
        self.poll_again()
        self.assertEqual(self.steers(), [])

    def test_queued_user_instruction_has_priority(self):
        launcher.queue_instruction(self.repo, "Checkpoint the current work")
        self.campaign.poll_progress()
        self.assertEqual(self.steers(), [])
        self.assertEqual(self.campaign.state["progress_advisory"]["status"], "pending")

    def test_stop_arriving_during_fresh_goal_read_wins(self):
        original = self.rpc.call
        def call(method, params, **kwargs):
            result = original(method, params, **kwargs)
            if method == "thread/goal/get":
                self.campaign.stop_reason = "user_requested"
            return result
        self.rpc.call = call
        self.campaign.poll_progress()
        self.assertEqual(self.steers(), [])

    def test_uncertain_progress_delivery_is_not_replayed_after_recovery(self):
        original = self.rpc.call
        def call(method, params, **kwargs):
            if method == "turn/steer":
                raise TimeoutError("response lost after possible acceptance")
            return original(method, params, **kwargs)
        self.rpc.call = call
        self.campaign.poll_progress()
        self.assertTrue(self.campaign.stop_now)
        self.assertEqual(self.campaign.state["progress_review"]["status"], "delivery_uncertain")
        recovered = launcher.Campaign(self.fixture.args, self.repo, self.repo, self.rpc.factory)
        self.addCleanup(recovered.output.close)
        with self.assertRaisesRegex(RuntimeError, "uncertain"):
            recovered.begin()
        self.assertFalse(any(method in {"thread/start", "thread/resume"} for method, _ in self.rpc.calls))

    def test_durable_progress_attempt_is_required_before_rpc(self):
        original = launcher.atomic_json
        def write(path, value):
            if Path(path).parent.name == "progress-reviews":
                raise OSError("journal unavailable")
            return original(path, value)
        with patch.object(launcher, "atomic_json", side_effect=write), self.assertRaises(OSError):
            self.campaign.poll_progress()
        self.assertEqual(self.steers(), [])

    def test_instruction_receipt_pins_attempt_and_actual_invocation(self):
        ident = launcher.queue_instruction(self.repo, "Finish the named original condition", source_id="verified-source")
        original = self.rpc.call
        def call(method, params, **kwargs):
            if method == "turn/steer":
                attempt = launcher._read_private_json(self.repo / "instructions/attempts" / (ident + ".json"))
                self.assertEqual(attempt["status"], "sending")
                self.assertEqual(attempt["expected_turn_id"], "turn-1")
                self.assertEqual(attempt["invocation_id"], self.campaign.log_dir.name)
            return original(method, params, **kwargs)
        self.rpc.call = call
        self.campaign.deliver_instruction()
        receipt = launcher._read_private_json(self.repo / "instructions/delivered" / (ident + ".json"))
        self.assertEqual(receipt["schema_version"], 2)
        self.assertEqual(receipt["source_id"], "verified-source")
        self.assertEqual(receipt["text_sha256"], hashlib.sha256(b"Finish the named original condition").hexdigest())
        self.assertEqual(receipt["worker_start"], "123")
        self.assertEqual(receipt["server_start"], "456")

    def test_mailbox_submission_is_not_claimed_ready_before_current_poll(self):
        stages = {"monitor": {"ready": False, "missing": ["first poll pending"]},
                  "mailbox": {"ready": False, "missing": ["no current observer receipt"]}}
        with patch("os_goal_service.start_mailbox", return_value={"status": "MAILBOX_START_REQUESTED"}), \
                patch("os_goal_readiness.evaluate_readiness", return_value={"monitoring_mode": "independent", "stages": stages}), \
                self.assertRaisesRegex(RuntimeError, "no new engine started"):
            launcher.ensure_mailbox_ready(self.repo, self.repo, timeout_seconds=0)
        self.assertEqual(self.rpc.calls, [])

    def test_positive_manual_supervisor_binding_is_required(self):
        ident = "a" * 32
        args = SimpleNamespace(worker=True, supervision_mode="manual", supervision_id=ident,
                               supervisor_pid=42, supervisor_start="100", guardian_run_id=None)
        watch = {"watcher_pid": 42, "watcher_start": "100", "supervision_mode": "manual",
                 "supervision_id": ident, "guardian_run_id": None}
        with patch.object(launcher.os, "getppid", return_value=42), \
                patch("os_goal_guard_protocol.process_start", return_value="100"), \
                patch("os_goal_guard_protocol.lease_free", return_value=False), \
                patch("os_goal_guard_protocol.read_json", return_value=watch):
            self.assertEqual(launcher.supervision_binding(args, self.repo)["supervision_mode"], "manual")
            args.supervision_id = "b" * 32
            with self.assertRaisesRegex(RuntimeError, "lineage"):
                launcher.supervision_binding(args, self.repo)
        self.assertEqual(launcher.supervision_binding(SimpleNamespace(), self.repo)["supervision_mode"], "direct")


if __name__ == "__main__":
    unittest.main()
