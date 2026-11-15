"""Saved-writer startup rejection with fake RPC only; no model/native work.

Functional McKernel OS/apps and Rust/allowed assembly; NO SECURITY TESTING.
"""
from contextlib import redirect_stdout
import copy
import io
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from scripts.tests.test_os_goal_launcher import FakeRPC, goal, launcher
from scripts.tests import test_os_goal_watcher_retention as watcher_fixture


ROOT = "01a18bc3-e072-7810-9426-75101b0856c0"


def conflict(thread_id=ROOT, *, method="thread/resume", code=-32600):
    return launcher.RPCResponseError(method, {
        "code": code, "message": "thread " + thread_id + " already has an active writer"})


class RejectingRPC(FakeRPC):
    def __init__(self, args, live_goal, rejection):
        super().__init__(args, live_goal)
        self.rejection = rejection
        self.before_rejection = None
        self.close_calls = 0
        self.close_guards = []
        self.close_error = None
        self.proc = SimpleNamespace(pid=987654321)

    def call(self, method, params, **kwargs):
        if method == "thread/resume":
            self.calls.append((method, params))
            if self.before_rejection is not None:
                self.before_rejection()
            raise self.rejection
        return super().call(method, params, **kwargs)

    def close(self):
        retained = getattr(self, "owner_custody_retained", False)
        self.close_guards.append(retained)
        launcher.guard_owner_close(retained)
        self.close_calls += 1
        if self.close_error is not None:
            raise self.close_error
        self.closed = True


class WriterConflictLifecycleTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="os-goal-writer-conflict-")
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name)
        self.args = launcher.arguments(["--hours", "0", "--agent-windows", "off", "--continuous"])
        self.saved_goal = dict(goal("paused"), threadId=ROOT)
        self.credit = {"schema_version": 1, "id": "7c6ef3604bfb4008a917bba8cfb6cfaa",
                       "budget": "52079.8011050000", "initial_balance": "60000",
                       "minimum_balance": "59988", "last_balance": "59988",
                       "spent": "12", "remaining": "52067.8011050000"}
        self.holds = {"source_hold": {"owner": "original-source", "outcome": "UNKNOWN"},
                      "native_hold": {"owner": "original-native", "bytes": 12 * 1024 ** 3},
                      "resource_hold": {"owner": "original-host", "bytes": 402653184, "jobs": 2},
                      "excluded_task": {"thread_id": "rejected-worker", "turn_id": "rejected-turn"}}
        self.saved = dict(schema_version=1, repo=str(self.directory), thread_id=ROOT,
                          goal=copy.deepcopy(self.saved_goal), credit_budget=copy.deepcopy(self.credit),
                          **copy.deepcopy(self.holds))
        launcher.atomic_json(self.directory / "state.json", self.saved)
        self.ledger_path = self.directory / "credit-runs" / (self.credit["id"] + ".json")
        self.ledger_path.parent.mkdir()
        self.ledger_bytes = (json.dumps(self.credit, indent=2) + "\n").encode()
        self.ledger_path.write_bytes(self.ledger_bytes)
        for target in ("check_resources", "check_machine_headroom"):
            mocked = patch.object(launcher, target, return_value=None)
            mocked.start()
            self.addCleanup(mocked.stop)
        birth = patch("watch_os_goal.process_start", return_value="900")
        birth.start()
        self.addCleanup(birth.stop)

    def campaign(self, rejection=None):
        rpc = RejectingRPC(self.args, copy.deepcopy(self.saved_goal), rejection or conflict())
        campaign = launcher.Campaign(self.args, self.directory, self.directory, rpc.factory)
        self.addCleanup(campaign.output.close)
        return campaign, rpc

    def assert_saved_contracts(self, campaign, rpc):
        self.assertEqual(campaign.state["thread_id"], ROOT)
        self.assertEqual(campaign.state["goal"], self.saved_goal)
        self.assertEqual(rpc.goal, self.saved_goal)
        self.assertEqual(campaign.state["credit_budget"], self.credit)
        self.assertEqual(self.ledger_path.read_bytes(), self.ledger_bytes)
        for key, value in self.holds.items():
            self.assertEqual(campaign.state[key], value)
        self.assertFalse(any(method in {"thread/start", "thread/goal/set", "turn/start",
                                        "turn/steer", "turn/interrupt"} for method, _ in rpc.calls))

    def test_exact_unacquired_resume_rejection_closes_only_bare_server_and_run_exits(self):
        campaign, rpc = self.campaign()
        campaign.wait_retained_owner = Mock(side_effect=AssertionError("bare server must not become a keeper"))
        campaign.retain_owner = Mock(side_effect=AssertionError("unacquired server has no Root custody"))
        with redirect_stdout(io.StringIO()):
            self.assertEqual(campaign.run(), 1)
        self.assertEqual(campaign.stop_reason, "thread_writer_conflict")
        self.assertEqual(campaign.state["stop_reason"], "thread_writer_conflict")
        self.assertEqual(campaign.state["phase"], "stopped")
        self.assertEqual(rpc.close_calls, 1)
        self.assertEqual(rpc.close_guards, [False])
        self.assertTrue(rpc.closed)
        self.assertIsNone(campaign.rpc)
        self.assertFalse(campaign.controlled)
        self.assertEqual(campaign.active, {})
        campaign.wait_retained_owner.assert_not_called()
        campaign.retain_owner.assert_not_called()
        rejection = campaign.state["startup_rejection"]
        self.assertEqual(rejection["thread_id"], ROOT)
        self.assertEqual(rejection["server_pid"], rpc.proc.pid)
        self.assertEqual(rejection["status"], "own_bare_server_closed")
        self.assertFalse(rejection["root_session_acquired"])
        self.assertFalse(rejection["payload_release_authorized"])
        self.assertEqual([method for method, _ in rpc.calls].count("thread/resume"), 1)
        self.assert_saved_contracts(campaign, rpc)

    def test_nonmatching_received_error_does_not_close_or_discard_server(self):
        campaign, rpc = self.campaign(conflict(code=-32603))
        with redirect_stdout(io.StringIO()), self.assertRaises(launcher.RPCResponseError):
            campaign.begin()
        self.assertIs(campaign.rpc, rpc)
        self.assertEqual(rpc.close_calls, 0)
        self.assertTrue(rpc.owner_custody_retained)
        self.assertNotIn("startup_rejection", campaign.state)
        self.assert_saved_contracts(campaign, rpc)

    def test_exact_rejection_with_active_child_does_not_close_or_drop_ownership(self):
        campaign, rpc = self.campaign()
        rpc.before_rejection = lambda: rpc.started("owned-child-turn", "owned-child")
        with redirect_stdout(io.StringIO()), self.assertRaises(launcher.RPCResponseError):
            campaign.begin()
        self.assertEqual(campaign.active, {"owned-child": "owned-child-turn"})
        self.assertIs(campaign.rpc, rpc)
        self.assertEqual(rpc.close_calls, 0)
        self.assertTrue(rpc.owner_custody_retained)
        self.assertNotIn("startup_rejection", campaign.state)
        self.assert_saved_contracts(campaign, rpc)

    def test_exact_rejection_with_native_owner_does_not_close_either_owner(self):
        campaign, rpc = self.campaign()
        native = SimpleNamespace(close=Mock())
        rpc.before_rejection = lambda: setattr(campaign, "native_owner_control", native)
        with redirect_stdout(io.StringIO()), self.assertRaises(launcher.RPCResponseError):
            campaign.begin()
        self.assertIs(campaign.native_owner_control, native)
        native.close.assert_not_called()
        self.assertIs(campaign.rpc, rpc)
        self.assertEqual(rpc.close_calls, 0)
        self.assertTrue(rpc.owner_custody_retained)
        self.assertNotIn("startup_rejection", campaign.state)
        self.assert_saved_contracts(campaign, rpc)

    def test_failed_bare_server_close_restores_guard_and_keeps_rpc_identity(self):
        campaign, rpc = self.campaign()
        rpc.close_error = OSError("unconfirmed own-server close")
        with redirect_stdout(io.StringIO()), self.assertRaisesRegex(OSError, "unconfirmed own-server close"):
            campaign.begin()
        self.assertIs(campaign.rpc, rpc)
        self.assertTrue(rpc.owner_custody_retained)
        self.assertFalse(rpc.closed)
        self.assertEqual(campaign.state["startup_rejection"]["status"], "closing_own_bare_server")
        self.assert_saved_contracts(campaign, rpc)


class WriterConflictResponseTests(unittest.TestCase):
    def test_only_exact_received_method_code_and_thread_message_match(self):
        self.assertTrue(launcher.thread_writer_conflict(conflict(), ROOT))
        variants = [RuntimeError(str(conflict())), conflict("another-root"),
                    conflict(method="thread/start"), conflict(code=-32603), conflict(code="-32600"),
                    launcher.RPCResponseError("thread/resume", None),
                    launcher.RPCResponseError("thread/resume", {"code": -32600,
                        "message": "thread " + ROOT + " already has an active writer; try again"})]
        for error in variants:
            with self.subTest(error=str(error)):
                self.assertFalse(launcher.thread_writer_conflict(error, ROOT))
        self.assertFalse(launcher.thread_writer_conflict(conflict(), "another-root"))

    def test_call_preserves_typed_received_error_and_clears_request_bookkeeping(self):
        rpc = launcher.RPC.__new__(launcher.RPC)
        rpc.next_id = 0
        rpc.responses, rpc.pending_methods, rpc.response_contexts = {}, {}, {}
        rpc.events = io.StringIO()
        received = {"code": -32600, "message": "thread " + ROOT + " already has an active writer",
                    "data": {"reason": "writer already owned"}}

        def send(request, **kwargs):
            rpc.responses[request["id"]] = {"id": request["id"], "error": received}

        rpc.send = Mock(side_effect=send)
        rpc.pump = Mock(side_effect=AssertionError("received response requires no additional pump"))
        with self.assertRaises(launcher.RPCResponseError) as caught:
            rpc.call("thread/resume", {"threadId": ROOT})
        self.assertEqual(caught.exception.method, "thread/resume")
        self.assertIs(caught.exception.error, received)
        self.assertTrue(launcher.thread_writer_conflict(caught.exception, ROOT))
        self.assertFalse(hasattr(caught.exception, "rpc_send_incomplete"))
        self.assertEqual(rpc.pending_methods, {})
        self.assertEqual(rpc.responses, {})
        self.assertEqual(rpc.response_contexts, {})
        self.assertIsNone(rpc._call_deadline)
        rpc.pump.assert_not_called()


class WriterConflictWatcherTests(unittest.TestCase):
    def scenario(self):
        fixture = watcher_fixture.WatcherRetentionTests(methodName="runTest")
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        fixture.state.update(thread_id=ROOT, phase="stopped", stop_reason="thread_writer_conflict",
                             goal=dict(goal("paused"), threadId=ROOT))
        fixture.state["startup_rejection"] = dict(
            {key: fixture.state[key] for key in watcher_fixture.custody.IDENTITY_FIELDS},
            method="thread/resume", error=conflict().error, status="own_bare_server_closed",
            root_session_acquired=False, payload_release_authorized=False, close_errors=[])
        fixture.clock.step = lambda clock: setattr(fixture.worker, "returncode", 1)
        return fixture

    def test_positive_closed_rejected_startup_exits_once_without_retirement_or_custody_claim(self):
        fixture = self.scenario()
        self.assertEqual(fixture.run_watcher(), 1)
        fixture.assert_original_owner_untouched()
        fixture.diagnostics.assert_not_called()
        self.assertEqual(fixture.worker.signals, [])
        events = fixture.events()
        self.assertEqual(sum(row["event"] == "worker_started" for row in events), 1)
        self.assertEqual(sum(row["event"] == "startup_rejection_closed" for row in events), 1)
        self.assertFalse(any(row["event"] == "owner_controller_lost" for row in events))
        final = events[-1]
        self.assertEqual(final["event"], "watcher_retirement")
        self.assertTrue(final["startup_rejection_closed"])
        self.assertFalse(final["server_retirement_attempted"])
        self.assertFalse(final["recovery_held"])
        self.assertIsNone(final["custody"])
        self.assertFalse(final["operator_required"])
        self.assertFalse(final["native_release_authorized"])

    def test_unmatched_or_unconfirmed_close_receipt_keeps_conservative_owner_loss(self):
        variants = (
            {"worker_start": "another-worker-birth"},
            {"server_pid": 123456789},
            {"error": conflict(code=-32603).error},
            {"root_session_acquired": True},
            {"close_errors": ["unconfirmed close"]},
        )
        for changed in variants:
            with self.subTest(changed=changed):
                fixture = self.scenario()
                fixture.state["startup_rejection"].update(changed)
                self.assertEqual(fixture.run_watcher(), 1)
                fixture.assert_original_owner_untouched()
                self.assertEqual(fixture.worker.signals, [])
                events = fixture.events()
                self.assertFalse(any(row["event"] == "startup_rejection_closed" for row in events))
                self.assertTrue(any(row["event"] == "owner_controller_lost" for row in events))
                final = events[-1]
                self.assertFalse(final["startup_rejection_closed"])
                self.assertTrue(final["recovery_held"])
                self.assertEqual(final["custody"], "UNKNOWN")
                self.assertTrue(final["operator_required"])
                self.assertFalse(final["native_release_authorized"])


if __name__ == "__main__":
    unittest.main()
