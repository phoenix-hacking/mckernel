"""Existing queue -> consumer integration; fake RPC/account and temp /proc only."""
import copy
from decimal import Decimal
import json
import os
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from scripts.tests.test_os_goal_launcher import launcher
from scripts.tests import test_os_goal_source_work as source_fixture
import os_goal_source_work as work


class SourceRPC:
    def __init__(self, server_pid):
        self.proc = SimpleNamespace(pid=server_pid)
        self.calls = []
        self.uncertain = False

    def call(self, method, params, **kwargs):
        self.calls.append((method, params))
        if method == "thread/turns/list":
            return {"data": [{"id": "original-turn", "status": "failed"}], "nextCursor": None}
        if method == "turn/start":
            if self.uncertain:
                raise TimeoutError("fake uncertain original delivery")
            return {"turn": {"id": "source-turn", "status": "inProgress"}}
        raise AssertionError("Unexpected RPC: " + method)


class SourceBridgeTests(unittest.TestCase):
    def setUp(self):
        self.fixture = source_fixture.SourceWorkTests("runTest")
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        f = self.fixture
        f.registry.unlink()
        f.sending.unlink()
        f.spec["blocker"]["thread_id"] = "root"
        self.owner = dict(f.binding, server_pid=f.child, server_start="101", repo=str(f.repo),
                          credit_budget="10", credit_ledger_path=str(f.control / "ledger.json"))
        self.owner.pop("invocation")
        f.private_json(Path(self.owner["credit_ledger_path"]), {"id": "finite-run", "budget": "10"})
        state = dict(f.state, repo=str(f.repo), server_pid=f.child, server_start="101",
                     credit_budget={"id": "finite-run", "budget": "10"}, source_work_capability=1,
                     same_owner_control_capability=1,
                     retained_resource_charges=copy.deepcopy(f.retained),
                     repair_context={"account_gate_clear": True})
        f.private_json(f.control / "state.json", state)
        campaign = launcher.Campaign.__new__(launcher.Campaign)
        campaign.state, campaign.state_path = state, f.control / "state.json"
        campaign.directory, campaign.repo, campaign.log_dir = f.control, f.repo, f.control / "log"
        campaign.args = SimpleNamespace(same_owner_control=True, repair_agent_failures=True, continuous=True)
        campaign.goal, campaign.active = copy.deepcopy(f.goal), {}
        campaign.controlled, campaign.stop_now, campaign.checkpoint_requested = True, False, False
        campaign.stop_reason, campaign.primary_stop_generation = None, 0
        campaign.credit_guard = SimpleNamespace(identifier="finite-run", budget=Decimal("10"),
                                               path=Path(self.owner["credit_ledger_path"]))
        campaign.rpc = SourceRPC(f.child)
        campaign.output = SimpleNamespace(notice=lambda text: None)

        def save(**fields):
            campaign.state.update(fields, active_turns=dict(campaign.active))
            launcher.atomic_json(campaign.state_path, campaign.state)
        campaign.save = save
        campaign.refresh_credit_budget = lambda: campaign.state.update(
            last_account_control_observation={"status": "OBSERVED", "owner": self.owner})
        records = {"allowed_roots": [f.repo],
                   "process_roots": [{"pid": f.pid, "start": "100", "role": "controller"}],
                   "retained_charges": f.retained, "exclusive_scopes": f.scopes}
        # This is controller code reading its current original registry fixture,
        # not an attachment/state complete=True claim.
        registry_path = f.control / "original-registry.json"
        f.private_json(registry_path, {key: [str(value) for value in values] if key == "allowed_roots"
                                      else values for key, values in records.items()})

        def provider(owner):
            self.assertEqual(owner, self.owner)
            current = launcher._read_private_json(registry_path)
            return dict(current, owner=owner, hold_fields=sorted(f.spec["blocker"]["hold_fields"]),
                        observed_utc_ns=f.now[0], observed_mono_ns=f.now[1],
                        records_sha256=launcher._account_value_sha256(current))
        campaign.source_work_registry_provider = provider
        self.campaign = campaign
        self.account_calls = []

        def account(state, ledger, owner, utc, mono, **kwargs):
            self.account_calls.append((owner, ledger))
            if state.get("last_account_control_observation", {}).get("status") != "OBSERVED":
                raise ValueError("No observed original account callback")
            self.assertEqual(owner, self.owner)
            self.assertEqual(ledger["id"], "finite-run")
            return dict(state["last_account_control_observation"],
                        received_utc_ns=f.now[0], received_mono_ns=f.now[1])
        real_validate = work.validate_registered_source_work

        def validate(item, **kwargs):
            kwargs.update(proc_root=f.proc, scratch_path=f.base, clock=lambda: f.now,
                          affinity_reader=lambda pid: {0, 6, 7},
                          disk_usage=lambda path: SimpleNamespace(free=32 * 1024 ** 3))
            return real_validate(item, **kwargs)
        for patcher in (
                patch.object(launcher, "_account_control_owner", return_value=self.owner),
                patch.object(launcher, "observed_account_control", side_effect=account),
                patch.object(work, "validate_registered_source_work", side_effect=validate),
                patch.object(launcher.time, "time_ns", return_value=f.now[0]),
                patch.object(launcher.time, "monotonic_ns", return_value=f.now[1])):
            patcher.start()
            self.addCleanup(patcher.stop)

    def queue(self, text=None):
        f = self.fixture
        return launcher.queue_instruction(f.control, f.text if text is None else text,
                                          source_id=f.source_id, source_work=f.spec)

    def starts(self):
        return [params for method, params in self.campaign.rpc.calls if method == "turn/start"]

    def test_real_queue_and_consumer_use_original_callbacks_and_keep_retained_charges(self):
        ident = self.queue()
        self.campaign.deliver_instruction()
        self.assertEqual(len(self.starts()), 1)
        self.assertTrue(self.account_calls)
        delivered = launcher._read_private_json(self.fixture.control / "instructions" / "delivered" / (ident + ".json"))
        self.assertEqual(delivered["status"], "accepted_by_server")
        self.assertFalse(delivered["execution_admission"])
        self.assertFalse(delivered["release_authorized"])
        self.assertEqual(delivered["source_resources"]["retained_jobs"], 2)
        self.assertEqual(delivered["source_resources"]["retained_bytes"], 2 * 1024 ** 3 + 256 * 1024 ** 2)
        self.assertNotIn("repair_context", self.campaign.state)
        self.assertIn("explicit Sol/MAX", self.starts()[0]["input"][0]["text"])
        self.assertFalse(any(method == "thread/goal/set" for method, _ in self.campaign.rpc.calls))
        self.fixture.source.write_text("legitimate source edit after the one dispatch\n")
        self.assertEqual(self.queue(), ident)  # No re-pin or duplicate on same durable source.
        self.assertEqual(list((self.fixture.control / "instructions" / "pending").glob("*.json")), [])

    def test_missing_current_registry_or_account_refuses_without_plain_text_fallback(self):
        ident = self.queue()
        del self.campaign.source_work_registry_provider
        self.campaign.deliver_instruction()
        self.assertEqual(self.starts(), [])
        receipt = launcher._read_private_json(self.fixture.control / "instructions" / "refused" / (ident + ".receipt.json"))
        self.assertEqual(receipt["status"], "source_work_refused_before_dispatch")
        self.assertEqual(self.campaign.goal["status"], "blocked")

    def test_unknown_account_never_dispatches(self):
        ident = self.queue()
        self.campaign.refresh_credit_budget = lambda: None
        self.campaign.deliver_instruction()
        self.assertEqual(self.starts(), [])
        self.assertTrue((self.fixture.control / "instructions" / "refused" / (ident + ".json")).exists())

    def test_partial_send_retains_intent_and_is_not_repeated(self):
        ident = self.queue()
        self.campaign.rpc.uncertain = True
        self.campaign.deliver_instruction()
        self.assertEqual(len(self.starts()), 1)
        sending = self.fixture.control / "instructions" / "sending" / (ident + ".json")
        self.assertTrue(sending.exists())
        self.assertTrue(sending.with_name(sending.stem + ".control-intent.json").exists())
        self.assertEqual(self.campaign.state["last_instruction"]["status"], "delivery_uncertain")
        self.campaign.deliver_instruction()
        self.assertEqual(len(self.starts()), 1)

    def test_legacy_envelope_refuses_and_source_id_rejects_changed_spec(self):
        ident = self.queue()
        item = launcher._read_private_json(self.fixture.control / "instructions" / "pending" / (ident + ".json"))
        self.assertEqual(item["capture_progress"], launcher.SOURCE_WORK_LEGACY_BARRIER)
        with self.assertRaises(ValueError):
            self.campaign.register_instruction_capture_progress(item, {})
        self.fixture.spec["limits"]["source_overhead_reserve_bytes"] += 1
        with self.assertRaises(ValueError):
            self.queue()

    def test_cli_requires_explicit_source_identity_and_keeps_unlimited_logical_text(self):
        with self.assertRaises(SystemExit):
            launcher.arguments(["--instruct", "source", "--source-work-file", "spec.json"])
        text = "source-only logical instruction " + "x" * 100000
        self.queue(text)
        self.campaign.deliver_instruction()
        self.assertEqual(len(self.starts()), 1)
        self.assertIn(text, self.starts()[0]["input"][0]["text"])


if __name__ == "__main__":
    unittest.main()
