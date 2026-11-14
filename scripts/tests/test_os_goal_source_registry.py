"""Offline production adapter integration; fake RPC/account, temp source/proc only.

Functional McKernel OS/Rust harness behavior; no live owner, service, process,
account or operation is contacted. The admission fixtures preserve the actual
current publisher/action formats, without executing their argv.
"""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from scripts.tests import test_os_goal_source_work_bridge as bridge_fixture
from scripts.tests.test_os_goal_launcher import launcher
import os_goal_source_registry as registry


class SourceRegistryTests(unittest.TestCase):
    def setUp(self):
        self.bridge = bridge_fixture.SourceBridgeTests("runTest")
        self.bridge.setUp()
        self.addCleanup(self.bridge.doCleanups)
        self.f = self.bridge.fixture
        self.c, self.owner = self.bridge.campaign, self.bridge.owner
        self.c.capacity_children, self.c.child_capacity_failures = {}, []
        self.c.stopping = False
        self.c.output.event = lambda message: None
        self.adapter = registry.SourceWorkRegistry(self.c, clock=lambda: self.f.now)
        self.c.source_work_registry = self.adapter
        self.c.source_work_registry_provider = self.adapter
        self.rows = {"blocked-child": [{"id": "original-turn", "status": "completed"}],
                     "review-child": [{"id": "review-turn", "status": "completed"}]}
        old_call = self.c.rpc.call

        def call(method, params, **kwargs):
            if method == "thread/turns/list" and params["threadId"] in self.rows:
                self.c.rpc.calls.append((method, params))
                return {"data": copy.deepcopy(self.rows[params["threadId"]]), "nextCursor": None}
            return old_call(method, params, **kwargs)
        self.c.rpc.call = call
        self.observe("blocked-child", "native_current_binding", "original-turn")
        self.f.spec["blocker"]["thread_id"] = "blocked-child"
        self.publish()
        self.observe("review-child", "m15_installed_leaf_review", "review-turn", self.attestation())

    def ref(self, name, value):
        path = self.f.control / name
        self.f.private_json(path, value)
        raw = path.read_bytes()
        return {"path": str(path), "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}

    def observe(self, child, slot, turn, output=None):
        # Exercise the Campaign hooks, not manually populated provenance/state.
        self.c.active["root"] = "root-observer"
        self.c.remember_child_provenance({"threadId": "root", "turnId": "root-observer",
            "item": {"type": "subAgentActivity", "kind": "interacted", "agentThreadId": child,
                     "agentPath": "/root/" + slot}})
        self.c.event({"method": "turn/started", "params": {"threadId": child,
                     "turn": {"id": turn, "status": "inProgress"}}})
        if output is not None:
            self.c.event({"method": "item/completed", "params": {"threadId": child, "turnId": turn,
                "item": {"id": "output-" + turn, "type": "agentMessage", "text": json.dumps(output)}}})
        self.c.event({"method": "turn/completed", "params": {"threadId": child,
                     "turn": {"id": turn, "status": "completed"}}})
        self.c.active.pop("root")

    def review(self, turn="review-turn"):
        record = self.record
        record["review"] = self.ref("source-review.json", {
            "schema": registry.REVIEW_SCHEMA, "owner": self.owner,
            "decision": "PASS_SOURCE_COORDINATION_ONLY",
            "records_sha256": registry._digest({k: v for k, v in record.items()
                if k not in {"review", "observed_utc_ns", "observed_mono_ns"}}),
            "operation_ids": [row["id"] for row in record["operations"]],
            "reviewer_thread_id": "review-child", "reviewer_turn_id": turn})
        self.f.private_json(self.adapter.path, record)

    def attestation(self):
        review = json.loads(Path(self.record["review"]["path"]).read_text())
        return {"schema": registry.ATTESTATION_SCHEMA,
                "records_sha256": review["records_sha256"],
                "review_sha256": self.record["review"]["sha256"],
                "operation_ids": review["operation_ids"]}

    def publish(self):
        owner = self.owner
        common = {"invocation": Path(owner["log_dir"]).name,
                  "same_Root_finite_credit_run_id": owner["credit_run_id"]}
        old_review = self.ref("original-publisher-review.json", {
            "status": "PASS_ACTUAL_INSTALL_ONLY", "scope": "ROOT_CODE_INSTALL_ONLY"})
        publisher_argv = ["/usr/bin/python3", str(self.f.source)]
        publisher = self.ref("original-publisher-admission.json", dict(common,
            schema=registry.PUBLISHER_SCHEMA, saved_Root=owner["thread_id"],
            new_current_family_bytes=2 * 1024 ** 3, new_current_jobs=1,
            operation_review=old_review,
            approved_argv=self.ref("original-publisher-argv.json", {"producer_argv": publisher_argv})))
        custody = self.ref("original-publisher-clients.json", [{
            "creation_attempted": True, "popen_returned": True, "pid": self.f.payload,
            "birth": "200", "argv": publisher_argv,
            "direct_wait_joined": False, "lifecycle_UNKNOWN": True}])
        action_review = self.ref("original-action-review.json", {
            "schema": "mckernel.current-4296-one-parent-nine-independent-operation-review.v1",
            "decision": "GO_SOURCE_BOUND_ORIGINAL_OPERATION", "request_sha256": "b" * 64})
        self.grant = self.ref("original-action-grant.UNISSUED.json", dict(common,
            schema=registry.ACTION_SCHEMA, Root_thread_id=owner["thread_id"],
            charge={"planning_bytes": 256 * 1024 ** 2, "jobs": 1},
            runtime_operation_review=action_review, request_sha256="b" * 64))
        action = self.ref("original-action-execution-admission.json", {
            "accepted_account_method": "account/rateLimits/read", "accepted_account_source": "read",
            "external_charge_used_not_reissued": True, "external_grant_reference": self.grant,
            "operation_review_reference": action_review})
        # A positive process wait still leaves its UNKNOWN descriptor/lease and
        # planning charge retained. It cannot require a nonexistent /proc cut.
        action_custody = self.ref("original-action-result.json", {"clients": [{
            "creation_attempted": True, "popen_returned": True, "pid": self.f.payload + 1,
            "birth": "201", "argv": ["/usr/bin/python3", self.grant["path"], self.grant["sha256"]],
            "direct_wait_joined": True, "exit": 0, "lifecycle_UNKNOWN": True}]})
        scope = {"scope": "operation", "source_access": "disjoint_paths",
                 "protected_paths": [str(self.f.base / "held-operation")]}
        self.record = {"schema": registry.RECORD_SCHEMA, "owner": owner,
            "observed_utc_ns": self.f.now[0], "observed_mono_ns": self.f.now[1],
            "allowed_roots": [str(self.f.repo)], "hold_fields": sorted(self.f.spec["blocker"]["hold_fields"]),
            "process_roots": [{"pid": self.f.pid, "start": "100", "role": "controller"}],
            "operations": [{"id": "original40491", "admission": publisher, "custody": custody,
                            "exclusive_scope": copy.deepcopy(scope)},
                           {"id": "original18067", "admission": action, "custody": action_custody,
                            "exclusive_scope": copy.deepcopy(scope)}]}
        self.review()

    def test_normal_campaign_installs_the_provider_and_names_the_missing_suppliers(self):
        with tempfile.TemporaryDirectory(prefix="source-normal-init-") as path:
            directory = Path(path)
            args = launcher.arguments(["--agent-windows", "off"])
            campaign = launcher.Campaign(args, directory, directory)
            self.addCleanup(campaign.output.log.close)
            self.assertIs(campaign.source_work_registry_provider, campaign.source_work_registry)
            self.assertEqual(campaign.source_work_registry.path, directory / "source-work-registry.json")
            with self.assertRaisesRegex(ValueError, "suppliers: Root compositor.*original Popen owners.*peer reviewer"):
                campaign.source_work_registry_provider(self.owner)

    def test_existing_queue_dispatches_using_original_records_and_parks_only_logical_slot(self):
        old_charges = copy.deepcopy(self.c.state["retained_resource_charges"])
        ident = self.bridge.queue()
        self.c.deliver_instruction()
        self.assertEqual(len(self.bridge.starts()), 1)
        receipt = launcher._read_private_json(self.f.control / "instructions" / "delivered" / (ident + ".json"))
        self.assertEqual(receipt["source_resources"]["retained_bytes"], 2415919104)
        self.assertEqual(receipt["source_resources"]["retained_jobs"], 2)
        parked = receipt["parked_model_turn"]
        self.assertEqual(parked["slot"], "native_current_binding")
        self.assertTrue(parked["logical_slot_available"])
        self.assertTrue(parked["physical_charges_retained"])
        self.assertFalse(receipt["release_authorized"])
        self.assertEqual(self.c.state["retained_resource_charges"], old_charges)
        self.assertNotIn("repair_context", self.c.state)

    def test_empty_inventory_and_operator_style_booleans_cannot_prove_coverage(self):
        self.record["operations"] = []
        self.review()
        with self.assertRaisesRegex(ValueError, "empty registry"):
            self.adapter(self.owner)
        self.publish()
        self.record["retained_charges_complete"] = True
        self.review()
        with self.assertRaisesRegex(ValueError, "schema differs"):
            self.adapter(self.owner)

    def test_omitting_one_nonempty_operation_and_repinning_review_cannot_reuse_completed_peer(self):
        before = self.adapter(self.owner)
        self.assertEqual(sum(row["planning_bytes"] for row in before["retained_charges"]), 2415919104)
        self.record["operations"] = self.record["operations"][:1]
        self.review()  # Locally forged replacement cannot change actual peer output.
        with self.assertRaisesRegex(ValueError, "controller-observed peer output"):
            self.adapter(self.owner)

    def test_new_genuine_output_cannot_drop_independently_observed_retained_coverage(self):
        self.record["operations"] = self.record["operations"][:1]
        self.review(turn="later-review")
        self.rows["review-child"].insert(0, {"id": "later-review", "status": "completed"})
        self.observe("review-child", "m15_installed_leaf_review", "later-review", self.attestation())
        with self.assertRaisesRegex(ValueError, "omits independently observed retained operations"):
            self.adapter(self.owner)

    def test_completed_peer_and_saved_output_cannot_replace_actual_attestation(self):
        proof = copy.deepcopy(self.adapter.peer_attestations)
        self.adapter.peer_attestations.clear()
        self.c.state["source_work_peer_output"] = list(proof.values())
        # A late item for a completed turn is not a new authenticated review.
        self.c.event({"method": "item/completed", "params": {"threadId": "review-child",
            "turnId": "review-turn", "item": {"id": "saved-output", "type": "agentMessage",
            "text": json.dumps(self.attestation())}}})
        with self.assertRaisesRegex(ValueError, "controller-observed peer output"):
            self.adapter(self.owner)
        self.assertEqual(self.adapter.peer_attestations, {})

    def test_unissued_grant_without_actual_execution_admission_cannot_cover_action(self):
        self.record["operations"][1]["admission"] = self.grant
        self.review(turn="unissued-review")
        self.rows["review-child"].insert(0, {"id": "unissued-review", "status": "completed"})
        self.observe("review-child", "m15_installed_leaf_review", "unissued-review", self.attestation())
        with self.assertRaisesRegex(ValueError, "execution ADMISSION is missing"):
            self.adapter(self.owner)

    def test_missing_or_mutated_original_custody_is_refused_before_dispatch(self):
        custody = Path(self.record["operations"][0]["custody"]["path"])
        custody.unlink()
        ident = self.bridge.queue()
        self.c.deliver_instruction()
        self.assertEqual(self.bridge.starts(), [])
        receipt = launcher._read_private_json(self.f.control / "instructions" / "refused" / (ident + ".receipt.json"))
        self.assertIn("supplier: original Root compositor/Popen owning runtime", receipt["reason"])

    def test_registry_is_reobserved_after_account_and_changed_records_never_start(self):
        refresh = self.c.refresh_credit_budget

        def changed():
            refresh()
            self.record["observed_utc_ns"] -= 1
            self.f.private_json(self.adapter.path, self.record)
        self.c.refresh_credit_budget = changed
        self.bridge.queue()
        self.c.deliver_instruction()
        self.assertEqual(self.bridge.starts(), [])

    def test_actual_completed_child_not_saved_renderer_metadata_authenticates_slot(self):
        receipt = self.adapter.terminal("blocked-child", "original-turn", self.owner)
        self.assertEqual(receipt["slot"], "native_current_binding")
        fresh = registry.SourceWorkRegistry(self.c, clock=lambda: self.f.now)
        self.c.state["agents"] = {"blocked-child": {"name": "/root/native_current_binding", "status": "completed"}}
        with self.assertRaisesRegex(ValueError, "observed direct canonical"):
            fresh.terminal("blocked-child", "original-turn", self.owner)
        with self.assertRaisesRegex(ValueError, "observed direct canonical"):
            fresh(self.owner)

    def test_active_uncertain_unseen_and_noncanonical_turns_cannot_free_slots(self):
        for setup, cleanup in (
                (lambda: self.c.active.update({"blocked-child": "original-turn"}), self.c.active.clear),
                (lambda: self.c.state.update(transport_uncertain={"method": "turn/start"}),
                 lambda: self.c.state.pop("transport_uncertain"))):
            setup()
            with self.assertRaisesRegex(ValueError, "active/uncertain"):
                self.adapter.terminal("blocked-child", "original-turn", self.owner)
            cleanup()
        self.rows["blocked-child"].append({"id": "new-unknown", "status": "inProgress"})
        with self.assertRaisesRegex(ValueError, "active or uncertain"):
            self.adapter.terminal("blocked-child", "original-turn", self.owner)
        self.observe("other-child", "noncanonical", "other-turn")
        self.assertNotIn("other-child", self.adapter.children)

    def test_incomplete_peer_inventory_wrong_owner_and_stale_record_refuse(self):
        for field, value in (("owner", dict(self.owner, credit_run_id="new-run")),
                             ("observed_utc_ns", self.f.now[0] - 25_000_000_001)):
            self.publish()
            self.record[field] = value
            self.review()
            with self.assertRaises(ValueError):
                self.adapter(self.owner)
        self.publish()
        self.rows["review-child"][0]["status"] = "failed"
        with self.assertRaises(ValueError):
            self.adapter(self.owner)


if __name__ == "__main__":
    unittest.main()
