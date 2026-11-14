"""Frozen-ledger projection and temporary receipts; no live controls or execution."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import os_goal_progress as subject


REPO = Path(__file__).resolve().parents[2]


class ProgressTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.canonical = subject.load_ledger(REPO)

    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.repo = Path(temporary.name)
        self.ledger = copy.deepcopy(self.canonical)
        self.ident = "M14-03-01-FUNCTIONAL"
        self.row = next(row for row in self.ledger["tasks"] if row["id"] == self.ident)
        self.row["percent_complete"] = 0  # Exercise one open original even after future campaign closure.
        next(row for row in self.ledger["tasks"] if row["id"] == "M14-03-02-FUNCTIONAL")["percent_complete"] = 0
        self.closed_count = sum(row.get("counted_in_requirement_rollup") is True and row["percent_complete"] == 100
                                for row in self.ledger["tasks"])
        self.remaining_count = subject.ORIGINAL_COUNT - self.closed_count
        self.write_ledger()
        self.target = {"schema_version": 1, "original_check": self.ident, "owner": "existing source owner",
                       "next_action": "Supply exact provider evidence, then review the original whole condition",
                       "input_bindings": {"source": "a" * 64, "profile": "b" * 64}, "evidence": [], "operation": None}
        self.state = {"closure_target": self.target}

    def write_ledger(self):
        path = self.repo / subject.LEDGER_PATH
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.ledger))

    def reference(self, value, filename="receipt.json"):
        path = self.repo / filename
        path.write_text(json.dumps(value))
        return {"path": filename, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}

    def receipt(self, **changes):
        value = {"schema": subject.EVIDENCE_SCHEMA, "kind": "required_evidence", "status": "qualified",
                 "original_check": self.ident, "condition_sha256": subject.condition_sha256(self.row),
                 "input_bindings": self.target["input_bindings"], "scope": "partial",
                 "qualified_fact_sha256s": ["c" * 64]}
        value.update(changes)
        return value

    def blocked_receipt(self, classification="external"):
        resolution = {"classification": classification,
                      "attempted_action": "Fetch the exact pinned SDK" if classification == "external" else "Install the required build package",
                      "outcome": "External access refused" if classification == "external" else "Required package is absent",
                      "missing_input": "Exact pinned external SDK access" if classification == "external" else "Required development package",
                      "supplying_owner": "existing dependency owner"}
        attempt = {"schema": subject.INPUT_RESOLUTION_SCHEMA, "status": "failed",
                   "original_check": self.ident, "condition_sha256": subject.condition_sha256(self.row),
                   "input_bindings": self.target["input_bindings"], **resolution}
        resolution["evidence"] = self.reference(attempt, "input-attempt.json")
        return self.receipt(kind="blocker_disposition", status="blocked", blocker_sha256="d" * 64,
                            resolution=resolution)

    def observe(self, now):
        result = subject.observe_progress(self.repo, self.state, now)
        self.state["progress_monitor"] = result["monitor"]
        return result

    def test_projection_preserves_exact_original_counts_and_does_not_choose_a_native_grant(self):
        result = self.observe(0)
        snapshot = result["snapshot"]
        self.assertEqual(snapshot["counted_total"], 156)
        self.assertEqual(snapshot["remaining_count"], self.remaining_count)
        self.assertEqual(snapshot["target_status"], "UNKNOWN")
        self.assertEqual(snapshot["remaining_conditions"], [self.row["done_when"]])
        self.assertIn("not execution grants", snapshot["dependency_caveat"])
        self.assertIsNone(result["advisory_text"])

    def test_noise_and_new_attempt_ids_do_not_make_semantic_progress(self):
        receipt = self.receipt(attempt_id="first", observed_at=0, text="first narrative")
        self.target["evidence"] = [self.reference(receipt)]
        first = self.observe(0)
        self.state.update(heartbeat_at="changed", updated_at="changed", active_turns={"one": "attempt2"},
                          source_commit="new commit", activity="look busy")
        self.target["owner"], self.target["next_action"] = "renamed owner", "Narrative changed"
        self.ledger["updated_at"] = "changed"
        self.write_ledger()
        receipt.update(attempt_id="second", observed_at=1200, text="another narrative")
        self.target["evidence"] = [self.reference(receipt)]
        second = self.observe(1200)
        self.assertEqual(first["snapshot"]["semantic_fingerprint"], second["snapshot"]["semantic_fingerprint"])
        self.assertFalse(second["snapshot"]["semantic_progress_changed"])
        self.assertEqual(second["monitor"]["last_semantic_at"], 0)

    def test_two_interval_stall_has_one_persistent_review_and_visible_pending_age(self):
        self.observe(0)
        checkpoint = self.observe(1200)
        self.assertTrue(checkpoint["checkpoint_due"])
        self.assertIsNone(checkpoint["advisory_text"])
        stalled = self.observe(2400)
        self.assertTrue(stalled["advisory_key"])
        self.assertIn("Harness-origin", stalled["advisory_text"])
        self.assertNotIn("Live user instruction", stalled["advisory_text"])
        self.assertIn("fix the exact confirmed ordinary defect once", stalled["advisory_text"])
        again = self.observe(4800)
        self.assertIsNone(again["advisory_text"])
        self.assertTrue(again["snapshot"]["review_required"])
        self.assertEqual(again["snapshot"]["decision_pending_seconds"], 2400)

    def test_new_qualified_evidence_rearms_after_the_next_two_intervals(self):
        self.observe(0)
        old = self.observe(2400)
        self.target["evidence"] = [self.reference(self.receipt())]
        new = self.observe(2500)
        self.assertTrue(new["snapshot"]["semantic_progress_changed"])
        self.assertFalse(new["snapshot"]["review_required"])
        self.assertEqual(new["monitor"]["last_semantic_at"], 2500)
        self.assertEqual(new["snapshot"]["seconds_since_semantic_progress"], 0)
        self.assertEqual(new["snapshot"]["closure_velocity"]["state"], "below_target")
        self.assertEqual(new["snapshot"]["closure_velocity"]["new_verified_in_window"], 0)
        self.assertEqual(new["monitor"]["velocity_started_at"], 0)
        velocity_review = self.observe(4899)
        self.assertTrue(velocity_review["advisory_key"].startswith("closure-velocity-"))
        self.assertNotEqual(velocity_review["advisory_key"], old["advisory_key"])
        self.assertEqual(velocity_review["snapshot"]["closure_velocity"]["new_verified_in_window"], 0)
        self.assertIsNone(self.observe(4900)["advisory_text"])

    def test_partial_cases_and_whole_receipt_claims_never_close_original_checks(self):
        for scope in ("partial", "whole"):
            self.target["evidence"] = [self.reference(self.receipt(scope=scope))]
            snapshot = self.observe(0)["snapshot"]
            self.assertNotIn(self.ident, snapshot["closed_original_checks"])
            self.assertEqual(snapshot["remaining_conditions"], [self.row["done_when"]])
            self.assertEqual(snapshot["target_status"], "UNKNOWN")

    def test_healthy_named_bounded_operation_survives_quiet_until_its_declared_deadline(self):
        receipt = {"schema": subject.OPERATION_SCHEMA, "original_check": self.ident,
                   "condition_sha256": subject.condition_sha256(self.row), "input_bindings": self.target["input_bindings"],
                   "name": "matching bounded real build", "status": "running", "healthy": True,
                   "started_at": 0, "observed_at": 0, "deadline_at": 7200}
        self.target["operation"] = {"name": receipt["name"], "deadline_at": 7200, "receipt": self.reference(receipt)}
        self.observe(0)
        self.assertIsNone(self.observe(5000)["advisory_text"])
        expired = self.observe(7200)
        self.assertTrue(expired["advisory_text"])
        self.assertEqual(expired["snapshot"]["operation"]["status"], "UNKNOWN")

    def test_readiness_requires_current_matching_operation_and_all_explicit_gates(self):
        receipt = {"schema": subject.OPERATION_SCHEMA, "original_check": self.ident,
                   "condition_sha256": subject.condition_sha256(self.row), "input_bindings": self.target["input_bindings"],
                   "name": "one exact operation", "status": "ready", "started_at": 0, "observed_at": 10,
                   "deadline_at": 5000, "gates": {name: "clear" for name in subject.GATE_NAMES}}
        self.target["operation"] = {"name": receipt["name"], "deadline_at": 5000, "receipt": self.reference(receipt)}
        self.assertEqual(self.observe(10)["snapshot"]["target_status"], "READY_FOR_CONTROLLER_REVIEW")
        self.assertEqual(self.observe(200)["snapshot"]["target_status"], "UNKNOWN")
        receipt["gates"]["source"] = "unknown"
        self.target["operation"]["receipt"] = self.reference(receipt)
        self.assertEqual(self.observe(10)["snapshot"]["target_status"], "UNKNOWN")
        receipt["gates"]["source"] = "clear"
        self.target["operation"]["receipt"] = self.reference(receipt)
        self.state["account_hold"] = True
        self.assertEqual(self.observe(10)["snapshot"]["target_status"], "HELD_OR_UNKNOWN")

    def test_proof_reuse_needs_exact_nonempty_source_and_original_condition_bindings(self):
        self.observe(0)
        for changes in ({"condition_sha256": "d" * 64}, {"input_bindings": {}},
                        {"input_bindings": {"source": "f" * 64}}, {"status": "unknown"}):
            self.target["evidence"] = [self.reference(self.receipt(**changes))]
            result = self.observe(100)
            self.assertFalse(result["snapshot"]["semantic_progress_changed"])
            self.assertTrue(result["snapshot"]["evidence_errors"])
            self.assertEqual(result["monitor"]["accepted_records"], [])

    def test_ledger_errors_and_closure_regressions_never_reset_the_stall_clock(self):
        first = self.observe(0)
        (self.repo / subject.LEDGER_PATH).write_text("{bad")
        failed = self.observe(1300)
        self.assertIn("ledger_error", failed["snapshot"])
        self.assertFalse(failed["snapshot"]["semantic_progress_changed"])
        self.write_ledger()
        restored = self.observe(1400)
        self.assertFalse(restored["snapshot"]["semantic_progress_changed"])
        self.assertEqual(restored["monitor"]["last_semantic_at"], 0)
        self.assertEqual(first["snapshot"]["semantic_fingerprint"], restored["snapshot"]["semantic_fingerprint"])
        closed = next(row for row in self.ledger["tasks"] if row.get("counted_in_requirement_rollup") and row["percent_complete"] == 100)
        closed["percent_complete"] = 0
        self.write_ledger()
        regressed = self.observe(1500)
        self.assertIn("acceptance_regression", regressed["snapshot"])
        self.assertEqual(regressed["monitor"]["last_semantic_at"], 0)

    def test_strict_sequential_dispatch_chooses_only_current_milestone(self):
        self.assertEqual(subject.priority_milestone(self.ledger), "M14")
        remaining = subject.remaining_work_view(self.ledger)
        text = subject.remaining_work_instruction(remaining, "M14")
        self.assertIn("Current required milestone: M14", text)
        self.assertNotIn("Concrete candidates for the existing Root to assess (UNASSESSED, not execution grants): M15-", text)
        self.assertIn("EVERY existing active or idle child owner", subject.dispatcher_agent_instruction("M14"))
        self.assertIn("rolling 30 minutes", subject.dispatcher_agent_instruction("M14"))
        self.ledger["summaries"]["M14"]["milestone_accepted"] = True
        self.assertEqual(subject.priority_milestone(self.ledger), "M15")

    def test_rolling_velocity_counts_only_new_canonical_binary_closures(self):
        first = self.observe(0)
        self.assertEqual(first["snapshot"]["closure_velocity"]["new_verified_in_window"], 0)
        self.target["evidence"] = [self.reference(self.receipt())]
        self.observe(100)  # Qualified partial evidence is not a closed original check.
        slow = self.observe(1800)
        self.assertEqual(slow["snapshot"]["closure_velocity"]["state"], "below_target")
        self.assertEqual(slow["snapshot"]["closure_velocity"]["new_verified_in_window"], 0)
        self.assertTrue(slow["advisory_key"].startswith("closure-velocity-"))
        self.row["percent_complete"] = 100
        self.write_ledger()
        closed = self.observe(1900)
        self.assertEqual(closed["snapshot"]["closure_velocity"]["new_verified_in_window"], 1)
        self.assertEqual(closed["snapshot"]["closure_velocity"]["state"], "meeting_target")
        self.assertEqual(self.observe(2000)["snapshot"]["closure_velocity"]["new_verified_in_window"], 1)
        later = self.observe(3701)
        self.assertEqual(later["snapshot"]["closure_velocity"]["new_verified_in_window"], 0)

    def test_out_of_order_target_requests_safe_redirection_not_operation_replay(self):
        later = next(row for row in self.ledger["tasks"]
                     if row.get("counted_in_requirement_rollup") and row["percent_complete"] == 0
                     and row["id"].startswith("M15-"))
        self.target["original_check"] = later["id"]
        seen = self.observe(0)
        self.assertEqual(seen["snapshot"]["priority_milestone"], "M14")
        self.assertEqual(seen["snapshot"]["current_target"]["original_check"], later["id"])
        self.assertIsNone(seen["advisory_key"])  # Preserve existing work; prioritize M14 in the next safe assignment.

    def test_real_original_closure_is_progress_but_changes_no_denominator(self):
        self.observe(0)
        self.row["percent_complete"] = 100
        self.write_ledger()
        result = self.observe(500)
        self.assertTrue(result["snapshot"]["semantic_progress_changed"])
        self.assertEqual(result["snapshot"]["counted_total"], 156)
        self.assertEqual(result["snapshot"]["remaining_count"], self.remaining_count - 1)
        self.assertTrue(result["advisory_key"].startswith("next-target-"))
        self.assertIn("Select the next eligible original check", result["advisory_text"])

    def test_all_counted_closed_requests_exact_acceptance_instead_of_an_invented_next_task(self):
        for row in self.ledger["tasks"]:
            if row.get("counted_in_requirement_rollup") is True:
                row["percent_complete"] = 100
        self.ledger["summaries"]["M14"]["milestone_accepted"] = False
        self.write_ledger()
        result = self.observe(0)
        self.assertTrue(result["advisory_key"].startswith("original-acceptance-review-"))
        self.assertIn("still-unaccepted original gates/milestones", result["advisory_text"])
        self.assertNotIn("Select the next eligible original check", result["advisory_text"])

    def test_invalid_target_requires_one_immediate_checked_correction(self):
        self.target["original_check"] = "M15-invented"
        first = self.observe(0)
        self.assertTrue(first["advisory_key"].startswith("invalid-target-"))
        self.assertIsNone(self.observe(1200)["advisory_text"])

    def test_accepted_review_gets_one_bounded_followup_without_claiming_a_completed_fix(self):
        self.observe(0)
        first = self.observe(2400)
        self.state["progress_advisory"] = {"key": first["advisory_key"], "status": "accepted_by_server"}
        self.state["progress_review"] = {"key": first["advisory_key"], "status": "accepted_by_server", "delivered_at": 2500}
        self.assertIsNone(self.observe(4800)["advisory_text"])
        overdue = self.observe(4900)
        self.assertTrue(overdue["advisory_key"].startswith("decision-overdue-"))
        self.assertEqual(overdue["snapshot"]["decision_status"], "owner_action_required")
        self.assertIn("accepted by the server but has no completed", overdue["advisory_text"])
        self.state["progress_advisory"] = {"key": overdue["advisory_key"], "status": "accepted_by_server"}
        self.state["progress_review"] = {"key": overdue["advisory_key"], "status": "accepted_by_server", "delivered_at": 4900}
        self.assertIsNone(self.observe(10000)["advisory_text"])
        self.assertEqual(self.state["progress_monitor"]["decision_status"], "owner_action_required")

    def test_operation_deadline_cannot_be_absurd_or_extended_by_attempt_metadata(self):
        receipt = {"schema": subject.OPERATION_SCHEMA, "original_check": self.ident,
                   "condition_sha256": subject.condition_sha256(self.row), "input_bindings": self.target["input_bindings"],
                   "name": "bounded build", "status": "running", "healthy": True,
                   "started_at": 0, "observed_at": 0, "deadline_at": 7200}
        self.target["operation"] = {"name": receipt["name"], "deadline_at": 7200, "receipt": self.reference(receipt)}
        self.observe(0)
        receipt.update(attempt_id="another attempt", name="renamed attempt", deadline_at=10000, observed_at=7000)
        self.target["operation"].update(name=receipt["name"], deadline_at=10000, receipt=self.reference(receipt))
        extended = self.observe(7200)
        self.assertEqual(extended["snapshot"]["operation"]["status"], "UNKNOWN")
        self.assertEqual(extended["snapshot"]["operation"]["deadline_at"], "1970-01-01T02:00:00Z")
        receipt["deadline_at"] = subject.MAX_OPERATION_SECONDS + 1
        self.target["operation"].update(deadline_at=receipt["deadline_at"], receipt=self.reference(receipt))
        absurd = self.observe(7500)
        self.assertEqual(absurd["snapshot"]["operation"]["status"], "UNKNOWN")

    def test_invented_ids_reparenting_and_weakened_conditions_fail_closed(self):
        original = copy.deepcopy(self.ledger)
        for mutate in (lambda: self.row.update(id=self.ident + "-invented"),
                       lambda: self.row.update(parent="M15-F05"),
                       lambda: self.row.update(done_when="Only one convenient passing case")):
            mutate()
            self.write_ledger()
            result = self.observe(0)
            self.assertIn("ledger_error", result["snapshot"])
            self.ledger = copy.deepcopy(original)
            self.row = next(row for row in self.ledger["tasks"] if row["id"] == self.ident)

    def test_blocked_disposition_is_visible_but_only_a_resolved_blocker_is_progress(self):
        self.observe(0)
        receipt = self.blocked_receipt()
        self.target["evidence"] = [self.reference(receipt)]
        blocked = self.observe(1000)
        self.assertFalse(blocked["snapshot"]["semantic_progress_changed"])
        self.assertEqual(blocked["snapshot"]["target_status"], "BLOCKED_BY_MATCHING_RECEIPT")
        receipt["status"] = "resolved"
        self.target["evidence"] = [self.reference(receipt)]
        self.assertFalse(self.observe(1100)["snapshot"]["semantic_progress_changed"])
        attempt = json.loads((self.repo / "input-attempt.json").read_text())
        attempt.update(status="completed", outcome="Exact pinned SDK fetched and verified")
        receipt["resolution"]["outcome"] = attempt["outcome"]
        receipt["resolution"]["evidence"] = self.reference(attempt, "input-attempt.json")
        self.target["evidence"] = [self.reference(receipt)]
        self.assertTrue(self.observe(1200)["snapshot"]["semantic_progress_changed"])

    def test_missing_engineering_package_requires_get_install_or_implement_action_not_a_terminal_block(self):
        receipt = self.blocked_receipt("engineering")
        self.target["evidence"] = [self.reference(receipt)]
        result = self.observe(0)
        self.assertEqual(result["snapshot"]["target_status"], "INPUT_RESOLUTION_REQUIRED")
        self.assertTrue(result["advisory_key"].startswith("input-resolution-"))
        self.assertIn("install missing required packages", result["advisory_text"])
        self.assertIn("implement real missing adapters/provider code", result["advisory_text"])
        self.assertIn("real provider adapter as our engineering work", result["advisory_text"])
        self.assertEqual(result["snapshot"]["closed_original_checks"], sorted(
            row["id"] for row in self.ledger["tasks"]
            if row.get("counted_in_requirement_rollup") is True and row["percent_complete"] == 100))

    def test_external_input_blocks_only_with_exact_matching_actual_resolution_attempt(self):
        receipt = self.blocked_receipt()
        self.target["evidence"] = [self.reference(receipt)]
        valid = self.observe(0)
        self.assertEqual(valid["snapshot"]["target_status"], "BLOCKED_BY_MATCHING_RECEIPT")
        self.assertIn("existing dependency owner", valid["advisory_text"])
        path = self.repo / "input-attempt.json"
        attempt = json.loads(path.read_text())
        attempt["input_bindings"] = {"source": "f" * 64}
        receipt["resolution"]["evidence"] = self.reference(attempt, path.name)
        self.target["evidence"] = [self.reference(receipt)]
        rejected = self.observe(100)
        self.assertEqual(rejected["snapshot"]["target_status"], "INPUT_RESOLUTION_REQUIRED")
        self.assertIn("no matching actual resolution attempt", rejected["snapshot"]["input_resolution_error"])

    def test_unsubstantiated_blocker_claim_never_becomes_terminal_external_block(self):
        receipt = self.receipt(kind="blocker_disposition", status="blocked", blocker_sha256="d" * 64)
        self.target["evidence"] = [self.reference(receipt)]
        result = self.observe(0)
        self.assertEqual(result["snapshot"]["target_status"], "INPUT_RESOLUTION_REQUIRED")
        self.assertTrue(result["advisory_key"].startswith("input-resolution-"))
        self.assertEqual(result["monitor"]["accepted_records"], [])

    def test_missing_target_gets_one_visible_initial_decision_without_execution_authority(self):
        self.state.pop("closure_target")
        first = self.observe(0)
        self.assertTrue(first["advisory_text"])
        self.assertIn("NEEDS_TARGET", first["snapshot"]["target_status"])
        self.assertIsNone(self.observe(1200)["advisory_text"])

    def test_failure_is_immediate_and_attempt_metadata_cannot_reissue_same_fix(self):
        failure = self.receipt(kind="ordinary_failure", status="failed", stage="compile", diagnostic_sha256="e" * 64,
                               defect="Undefined required provider at the actual link", owner="existing compiler owner")
        self.target["evidence"] = [self.reference(failure)]
        first = self.observe(0)
        self.assertTrue(first["advisory_key"].startswith("ordinary-failure-"))
        self.assertIn("Undefined required provider", first["advisory_text"])
        failure.update(attempt_id="fresh wrapper", heartbeat_at=9999)
        self.target["evidence"] = [self.reference(failure)]
        self.assertIsNone(self.observe(5000)["advisory_text"])
        self.assertEqual(first["monitor"]["last_semantic_at"], 0)

    def test_runner_failure_adapter_is_consumed_without_a_new_proof_wrapper(self):
        adapter = self.receipt(kind="ordinary_failure", status="failed", stage="payload_exit", diagnostic_sha256="e" * 64,
                               defect="Unexpected exit status 1", owner="existing build owner")
        record = {"schema": "mckernel-host-operation-v1", "payload_state": "FAIL", "ordinary_failure": adapter,
                  "spec": {"closure_target": {name: adapter[name] for name in ("original_check", "condition_sha256", "input_bindings")}}}
        self.target["evidence"] = [self.reference(record)]
        self.assertTrue(self.observe(0)["advisory_text"])
        record["payload_state"] = "PASS"
        self.target["evidence"] = [self.reference(record)]
        snapshot = self.observe(500)["snapshot"]
        self.assertEqual(snapshot["ordinary_failures"], [])
        self.assertEqual(snapshot["evidence_records"], [])

    def test_reusing_earned_proof_after_another_target_never_counts_twice(self):
        proof = self.reference(self.receipt())
        self.observe(0)
        self.target["evidence"] = [proof]
        self.assertTrue(self.observe(100)["snapshot"]["semantic_progress_changed"])
        self.target["evidence"] = []
        self.assertFalse(self.observe(200)["snapshot"]["semantic_progress_changed"])
        self.target["evidence"] = [proof]
        self.assertFalse(self.observe(300)["snapshot"]["semantic_progress_changed"])

    def test_target_accepts_only_original_counted_ids_and_safe_nonpayload_refs(self):
        self.assertEqual(subject.validate_target(self.target, self.ledger, self.repo), self.target)
        for changes in ({"original_check": "M14-F01"}, {"original_check": self.ident + "-invented"},
                        {"evidence": [{"path": "../elsewhere.json", "sha256": "a" * 64}]}):
            with self.assertRaises(ValueError):
                subject.validate_target(dict(self.target, **changes), self.ledger, self.repo)


if __name__ == "__main__":
    unittest.main()
