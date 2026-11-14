"""Functional Campaign.run retention integration with fake RPC, handles and time.

No service, process, native operation, inference or runtime cleanup is performed.
The BaseException sentinel bounds a deliberately persistent owning controller.
"""

from contextlib import ExitStack, redirect_stdout
import copy
import io
import json
import os
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import Mock, patch

from scripts.tests.test_os_goal_launcher import FakeRPC, goal, launcher
import os_goal_guard_protocol
import watch_os_goal


class RetainedScenarioEnd(BaseException):
    """An offline fixture boundary, never an instruction to release custody."""


class FakeOutput:
    def __init__(self, log_dir, **kwargs):
        self.primary = None
        self.agent_event_count = 0
        self.close_calls = 0
        self.notices = []

    def snapshot(self):
        return {}

    def event(self, message):
        self.agent_event_count += 1

    def notice(self, value):
        self.notices.append(value)

    def flush(self, **kwargs):
        pass

    def heartbeat(self, *args, **kwargs):
        pass

    def close(self):
        self.close_calls += 1


class RetentionRPC(FakeRPC):
    def __init__(self, args, clock, live_goal):
        super().__init__(args, live_goal)
        self.clock = clock
        self.close_calls = 0
        self.fail_calls = {}
        self.proc = SimpleNamespace(pid=987654321, stdin=object(), stdout=object(),
                                    stderr=object(), wait=Mock(), terminate=Mock(), kill=Mock())

    def call(self, method, params, **kwargs):
        failure = self.fail_calls.pop(method, None)
        if failure is not None:
            self.calls.append((method, params))
            raise failure
        return super().call(method, params, **kwargs)

    def pump(self, timeout=1):
        self.clock[0] += max(0.25, timeout)
        if not self.steps:
            raise RetainedScenarioEnd("finite offline owner scenario complete")
        self.steps.popleft()(self)

    def close(self):
        self.close_calls += 1
        self.closed = True


class CampaignOwnerRetentionTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="os-goal-owner-retention-")
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name)
        self.args = launcher.arguments(["--hours", "0", "--agent-windows", "off"])
        self.args.retain_owner_on_stop = True
        self.args.continuous = False
        self.args.same_owner_control = True
        self.args.heartbeat_seconds = 1000
        self.clock = [100.0]
        with patch.object(launcher, "LiveOutput", FakeOutput):
            self.campaign = launcher.Campaign(self.args, self.directory, self.directory)
        self.rpc = RetentionRPC(self.args, self.clock, goal("paused"))
        self.rpc.on_event = self.campaign.event
        self.native = SimpleNamespace(close=Mock(), poll=Mock())
        self.original_output = self.campaign.output
        self.original_proc = self.rpc.proc
        self.original_handles = (self.rpc.proc.stdin, self.rpc.proc.stdout, self.rpc.proc.stderr)
        self.holds = {"source_hold": {"scope": "original-source", "outcome": "UNKNOWN"},
                      "native_hold": {"owner": "original-native", "bytes": 12 * 1024 ** 3},
                      "resource_hold": {"owner": "original-host", "bytes": 2415919104, "jobs": 2},
                      "logical_lease": {"owner": "original-runtime", "outcome": "UNKNOWN"}}
        self.ledger = {"schema_version": 1, "id": "a" * 32, "budget": "100", "spent": "12",
                       "initial_balance": "1000", "minimum_balance": "988", "last_balance": "988",
                       "remaining": "88"}
        self.ledger_path = self.directory / "credit-runs" / (self.ledger["id"] + ".json")
        self.ledger_path.parent.mkdir()
        self.ledger_bytes = (json.dumps(self.ledger, indent=3) + "\n").encode()
        self.ledger_path.write_bytes(self.ledger_bytes)
        self.entry = None
        self.boundary_states = []
        self.sleep_failures = []
        self.resource_admission = Mock()
        self.returned_from_wait = []
        self.initial_status = "paused"
        self.initial_reason = None
        self.initial_stop_now = False
        self.initial_controlled = True
        self.initial_active = False
        self.before_begin_return = None
        self.campaign.stop = Mock(wraps=self.campaign.stop)
        self.campaign.review_blocked_goal = Mock()
        self.campaign.deliver_instruction = Mock(wraps=self.campaign.deliver_instruction)
        self.campaign.poll_native_owner_control = Mock()
        self.campaign.refresh_credit_budget = Mock()
        actual_retain = self.campaign.retain_owner

        def observe_retain(reason):
            if self.entry is None:
                self.entry = {"instruction_calls": self.campaign.deliver_instruction.call_count,
                              "repair_calls": self.campaign.review_blocked_goal.call_count,
                              "admission_calls": self.campaign.refresh_credit_budget.call_count,
                              "native_poll_calls": self.campaign.poll_native_owner_control.call_count}
            return actual_retain(reason)

        self.campaign.retain_owner = Mock(side_effect=observe_retain)
        self.campaign.begin = Mock(side_effect=self.install_original_owner)

    def install_original_owner(self):
        campaign = self.campaign
        campaign.rpc = self.rpc
        campaign.native_owner_control = self.native
        campaign.controlled = self.initial_controlled
        campaign.goal = goal(self.initial_status) if self.initial_status is not None else None
        self.rpc.goal = copy.deepcopy(campaign.goal)
        campaign.stop_reason = self.initial_reason
        campaign.stop_now = self.initial_stop_now
        campaign.active = {}
        self.rpc.turns = {}
        if self.initial_active:
            campaign.active["test-thread"] = "original-turn"
            self.rpc.turns["test-thread"] = {"id": "original-turn", "items": [], "status": "inProgress"}
        campaign.save(thread_id="test-thread" if campaign.goal is not None else None,
                      worker_pid=os.getpid(), worker_start="100", server_pid=self.rpc.proc.pid,
                      server_start="101", phase="running" if campaign.controlled else "starting",
                      auth_mode="chatgpt", goal=campaign.goal, stop_reason=campaign.stop_reason,
                      credit_budget=copy.deepcopy(self.ledger), **copy.deepcopy(self.holds))
        if self.before_begin_return is not None:
            self.before_begin_return()

    def owner(self):
        return {"boot_id": "offline-boot", "repo": str(self.directory), "guardian_run_id": None,
                "log_dir": str(self.campaign.log_dir), "thread_id": "test-thread",
                "goal_objective_sha256": launcher._account_value_sha256(launcher.OBJECTIVE),
                "worker_pid": os.getpid(), "worker_start": "100", "server_pid": self.rpc.proc.pid,
                "server_start": "101", "credit_run_id": self.ledger["id"], "credit_budget": "100",
                "credit_ledger_path": str(self.ledger_path)}

    def run_to_fixture_boundary(self, *, atomic_json=None):
        def birth(pid):
            return {os.getpid(): "100", os.getppid(): "90", self.rpc.proc.pid: "101"}.get(pid)

        def sleep(seconds):
            self.clock[0] += seconds
            if self.sleep_failures:
                raise self.sleep_failures.pop(0)

        with ExitStack() as stack:
            stack.enter_context(patch.object(launcher.time, "monotonic", side_effect=lambda: self.clock[0]))
            stack.enter_context(patch.object(launcher.time, "sleep", side_effect=sleep))
            stack.enter_context(patch.object(launcher, "check_resources", self.resource_admission))
            stack.enter_context(patch.object(watch_os_goal, "process_start", side_effect=birth))
            stack.enter_context(patch.object(os_goal_guard_protocol, "process_start", side_effect=birth))
            stack.enter_context(patch.object(launcher, "_account_control_owner", side_effect=lambda *args: self.owner()))
            if atomic_json is not None:
                stack.enter_context(patch.object(launcher, "atomic_json", side_effect=atomic_json))
            stack.enter_context(redirect_stdout(io.StringIO()))
            with self.assertRaises(RetainedScenarioEnd):
                self.campaign.run()

    def assert_original_custody_survives(self, *, parked=True):
        campaign = self.campaign
        self.assertIs(campaign.rpc, self.rpc)
        self.assertIs(campaign.rpc.proc, self.original_proc)
        self.assertIs(campaign.native_owner_control, self.native)
        self.assertIs(campaign.output, self.original_output)
        self.assertEqual((self.rpc.proc.stdin, self.rpc.proc.stdout, self.rpc.proc.stderr), self.original_handles)
        self.assertEqual(self.rpc.close_calls, 0)
        self.assertFalse(self.rpc.closed)
        self.native.close.assert_not_called()
        campaign.stop.assert_not_called()
        self.assertEqual(self.original_output.close_calls, 0)
        self.rpc.proc.wait.assert_not_called()
        self.rpc.proc.terminate.assert_not_called()
        self.rpc.proc.kill.assert_not_called()
        self.resource_admission.assert_not_called()
        for key, value in self.holds.items():
            self.assertEqual(campaign.state[key], value)
        self.assertEqual(campaign.state["credit_budget"], self.ledger)
        self.assertEqual(self.ledger_path.read_bytes(), self.ledger_bytes)
        self.assertTrue(self.rpc.owner_custody_retained)
        self.assertIsNotNone(self.entry)
        if parked:
            self.assertTrue(self.boundary_states)
            self.assertTrue(all(row["phase"] == "owner_retained" for row in self.boundary_states),
                            self.boundary_states)
            self.assertEqual(campaign.state["phase"], "owner_retained")
            self.assertTrue(campaign.retained_for_stop)
            receipt = campaign.state["owner_retention"]
            self.assertEqual(receipt["custody"], "UNKNOWN")
            self.assertFalse(receipt["release_authorized"])
            self.assertEqual(receipt["inflight_turn_quiescence"], "unverified")
            self.assertEqual(campaign.review_blocked_goal.call_count, self.entry["repair_calls"])
            self.assertEqual(campaign.poll_native_owner_control.call_count, self.entry["native_poll_calls"])
        self.assertFalse(any(method in {"turn/start", "turn/steer", "turn/interrupt", "thread/start", "thread/resume"}
                             for method, _ in self.rpc.calls))

    def end_while_retained(self, rpc):
        # Assert the observed boundary outside Campaign's Exception handlers.
        # An AssertionError raised here could otherwise be swallowed as a
        # recoverable monitor failure and falsely pass after a later pump.
        self.boundary_states.append({"phase": self.campaign.state.get("phase"),
                                     "stop_reason": self.campaign.stop_reason})
        raise RetainedScenarioEnd("inspect original retained objects")

    def diagnostic_text(self):
        return str(self.campaign.state) + str(self.campaign.retention_errors)

    def test_user_pause_retains_original_owner_without_turn_or_handle_cleanup(self):
        self.rpc.steps.append(self.end_while_retained)
        self.run_to_fixture_boundary()
        self.assert_original_custody_survives()
        self.assertEqual(self.campaign.goal["status"], "paused")

    def test_budget_unknown_retains_active_original_operation_and_all_charges(self):
        self.initial_status, self.initial_active = "active", True
        self.initial_reason, self.initial_stop_now = "credit_budget_unknown", True
        self.rpc.steps.append(self.end_while_retained)
        self.run_to_fixture_boundary()
        self.assert_original_custody_survives()
        self.assertEqual(self.campaign.stop_reason, "credit_budget_unknown")
        self.assertEqual(self.campaign.active, {"test-thread": "original-turn"})

    def test_budget_exhaustion_preserves_stop_and_original_owner(self):
        self.initial_status = "active"
        self.initial_reason, self.initial_stop_now = "credit_budget_exhausted", True
        self.rpc.steps.append(self.end_while_retained)
        self.run_to_fixture_boundary()
        self.assert_original_custody_survives()
        self.assertEqual(self.campaign.stop_reason, "credit_budget_exhausted")

    def test_work_window_quiesces_without_checkpoint_steer_or_grace_kill(self):
        self.args.continuous = True
        self.args.hours, self.args.grace_seconds = 1 / 3600, 0
        self.initial_status, self.initial_active = "active", True
        self.rpc.steps.extend([lambda rpc: None, self.end_while_retained])
        self.run_to_fixture_boundary()
        self.assert_original_custody_survives()
        self.assertEqual(self.campaign.stop_reason, "work_window")

    def test_checkpoint_with_remaining_grace_enters_retention_before_polling_controls(self):
        self.args.continuous = True
        self.args.hours, self.args.grace_seconds = 20 / 3600, 10
        self.initial_status, self.initial_active = "active", True

        def reach_checkpoint(rpc):
            self.clock[0] = 111.0  # Checkpoint at 110; work deadline still 120.

        self.rpc.steps.extend([reach_checkpoint, self.end_while_retained])
        self.run_to_fixture_boundary()
        self.assert_original_custody_survives()
        self.assertEqual(self.campaign.stop_reason, "work_window")
        self.assertEqual(self.campaign.poll_native_owner_control.call_count, 1)

    def test_running_pump_exception_retains_original_owner_instead_of_finally_cleanup(self):
        self.initial_status, self.initial_active = "active", True

        def failed_pump(rpc):
            raise RuntimeError("original RPC pump failed")

        self.rpc.steps.extend([failed_pump, self.end_while_retained])
        self.run_to_fixture_boundary()
        self.assert_original_custody_survives()
        self.assertIn("original RPC pump failed", self.diagnostic_text())

    def test_preflight_exception_retains_even_a_bare_original_rpc(self):
        self.initial_status, self.initial_controlled = None, False

        def fail_preflight():
            raise RuntimeError("offline preflight read failed")

        self.before_begin_return = fail_preflight
        self.rpc.steps.append(self.end_while_retained)
        self.run_to_fixture_boundary()
        self.assert_original_custody_survives()
        self.assertFalse(self.campaign.controlled)

    def test_retained_pump_error_remains_unknown_and_keeps_original_handles(self):
        def failed_pump(rpc):
            raise RuntimeError("retained pump failed")

        self.rpc.steps.extend([failed_pump, self.end_while_retained])
        self.run_to_fixture_boundary()
        self.assert_original_custody_survives()
        self.assertIn("retained pump failed", self.diagnostic_text())

    def test_unconfirmed_pause_cannot_release_original_runtime(self):
        self.initial_status = "active"
        self.initial_reason, self.initial_stop_now = "user_requested", True
        self.rpc.fail_calls["thread/goal/get"] = RuntimeError("same-owner pause unavailable")
        self.rpc.steps.append(self.end_while_retained)
        self.run_to_fixture_boundary()
        self.assert_original_custody_survives()
        self.assertIn("same-owner pause unavailable", self.diagnostic_text())
        self.assertEqual(self.campaign.stop_reason, "user_requested")

    def test_failed_retention_save_keeps_in_memory_custody_and_skips_all_finally_cleanup(self):
        original_write = launcher.atomic_json

        def failing_write(path, value):
            if Path(path) == self.campaign.state_path and value.get("phase") == "owner_retained":
                raise OSError("retention receipt publication failed")
            return original_write(path, value)

        self.rpc.steps.append(self.end_while_retained)
        self.run_to_fixture_boundary(atomic_json=failing_write)
        self.assert_original_custody_survives()
        self.assertIn("retention receipt publication failed", self.diagnostic_text())

    def assert_real_interrupt_keeps_owner(self, error_type, stage):
        message = "offline " + stage + " interruption"
        error = error_type(message)
        write = None
        if stage == "pause":
            self.initial_status = "active"
            self.initial_reason, self.initial_stop_now = "credit_budget_unknown", True
            self.rpc.fail_calls["thread/goal/get"] = error
        elif stage in {"work_loop", "monitor"}:
            if stage == "work_loop":
                self.initial_status, self.initial_active = "active", True

            def interrupted_pump(rpc):
                raise error

            self.rpc.steps.append(interrupted_pump)
        elif stage == "backoff":
            def failed_monitor(rpc):
                raise RuntimeError("offline monitor fault before interrupted backoff")

            self.rpc.steps.append(failed_monitor)
            self.sleep_failures.append(error)
        elif stage == "save":
            original_write = launcher.atomic_json
            pending = [error]

            def interrupted_write(path, value):
                if (Path(path) == self.campaign.state_path
                        and value.get("phase") == "owner_retained" and pending):
                    raise pending.pop()
                return original_write(path, value)

            write = interrupted_write
            self.rpc.steps.append(lambda rpc: None)  # Prove monitoring survives the interrupted save.
        else:
            self.fail("unknown fixture interruption stage")
        self.rpc.steps.append(self.end_while_retained)
        self.run_to_fixture_boundary(atomic_json=write)
        self.assert_original_custody_survives()
        self.assertTrue(any((row["stage"] == stage or stage == "backoff")
                            and row["error_type"] == error_type.__name__
                            and message in row["error"] for row in self.campaign.retention_errors))
        if stage == "pause":
            self.assertEqual(self.campaign.stop_reason, "credit_budget_unknown")

    def test_keyboard_interrupt_in_work_loop_keeps_original_custody(self):
        self.assert_real_interrupt_keeps_owner(KeyboardInterrupt, "work_loop")

    def test_system_exit_in_work_loop_keeps_original_custody(self):
        self.assert_real_interrupt_keeps_owner(SystemExit, "work_loop")

    def test_keyboard_interrupt_during_pause_keeps_original_custody(self):
        self.assert_real_interrupt_keeps_owner(KeyboardInterrupt, "pause")

    def test_system_exit_during_pause_keeps_original_custody(self):
        self.assert_real_interrupt_keeps_owner(SystemExit, "pause")

    def test_keyboard_interrupt_in_retained_monitor_keeps_original_custody(self):
        self.assert_real_interrupt_keeps_owner(KeyboardInterrupt, "monitor")

    def test_system_exit_in_retained_monitor_keeps_original_custody(self):
        self.assert_real_interrupt_keeps_owner(SystemExit, "monitor")

    def test_keyboard_interrupt_during_retention_save_keeps_original_custody(self):
        self.assert_real_interrupt_keeps_owner(KeyboardInterrupt, "save")

    def test_system_exit_during_retention_save_keeps_original_custody(self):
        self.assert_real_interrupt_keeps_owner(SystemExit, "save")

    def test_keyboard_interrupt_during_monitor_backoff_keeps_original_controller(self):
        self.assert_real_interrupt_keeps_owner(KeyboardInterrupt, "backoff")

    def test_system_exit_during_monitor_backoff_keeps_original_controller(self):
        self.assert_real_interrupt_keeps_owner(SystemExit, "backoff")

    def test_monitor_interrupt_preserves_the_original_account_stop(self):
        self.initial_status, self.initial_active = "active", True
        self.initial_reason, self.initial_stop_now = "credit_budget_unknown", True

        def interrupted_monitor(rpc):
            raise KeyboardInterrupt("offline interrupt after original account stop")

        self.rpc.steps.extend([interrupted_monitor, self.end_while_retained])
        self.run_to_fixture_boundary()
        self.assert_original_custody_survives()
        self.assertEqual(self.campaign.stop_reason, "credit_budget_unknown")
        self.assertTrue(self.campaign.stop_now)
        self.assertIn("offline interrupt after original account stop", self.diagnostic_text())

    def accepted_control(self, *, owner_changes=None, generation_delta=0):
        owner = self.owner()
        owner.update(owner_changes or {})
        return {"id": "source-offline-explicit-user", "status": "accepted_by_server",
                "control_kind": "resume_same_owner", "owner": owner,
                "primary_stop_generation": self.campaign.primary_stop_generation + generation_delta,
                "execution_admission": False, "hold_release": False}

    def park_from_begin(self):
        self.campaign.retain_owner("blocked")
        self.campaign.wait_retained_owner("blocked")
        self.returned_from_wait.append(self.campaign.state["phase"])

    def test_verified_explicit_control_can_resume_only_continuous_stop_free_owner(self):
        self.args.continuous = True
        self.initial_status = "blocked"
        self.before_begin_return = self.park_from_begin

        def explicit_resume(rpc):
            self.campaign.save(last_instruction=self.accepted_control())
            rpc.status("active")

        def resumed_run(rpc):
            self.assertEqual(self.campaign.state["phase"], "running")
            self.assertEqual(self.returned_from_wait, ["running"])
            self.assertFalse(self.campaign.retained_for_stop)
            raise RetainedScenarioEnd("same original owner resumed")

        self.rpc.steps.extend([explicit_resume, resumed_run])
        self.run_to_fixture_boundary()
        self.assert_original_custody_survives(parked=False)
        self.assertEqual(self.returned_from_wait, ["running"])

    def test_verified_activation_can_resume_with_its_immediate_same_root_turn(self):
        self.args.continuous = True
        self.initial_status = "blocked"
        self.before_begin_return = self.park_from_begin
        original_record = []
        resumed_frames = []

        def explicit_resume_with_root_turn(rpc):
            original_record.append(copy.deepcopy(self.campaign.state["owner_retention"]))
            self.campaign.save(last_instruction=self.accepted_control())
            rpc.status("active")
            rpc.started("immediate-root-turn")

        def resumed_run(rpc):
            resumed_frames.append({"phase": self.campaign.state.get("phase"),
                                   "active": dict(self.campaign.active),
                                   "retained_for_stop": self.campaign.retained_for_stop,
                                   "owner_retention": copy.deepcopy(self.campaign.state["owner_retention"])})
            raise RetainedScenarioEnd("same Root immediately active after explicit control")

        self.rpc.steps.extend([explicit_resume_with_root_turn, resumed_run])
        self.run_to_fixture_boundary()
        self.assert_original_custody_survives(parked=False)
        self.assertEqual(self.returned_from_wait, ["running"])
        self.assertEqual(resumed_frames, [{"phase": "running", "active": {"test-thread": "immediate-root-turn"},
                                         "retained_for_stop": False, "owner_retention": original_record[0]}])

    def test_verified_activation_does_not_ignore_an_active_descendant(self):
        self.args.continuous = True
        self.initial_status = "blocked"
        self.before_begin_return = self.park_from_begin

        def explicit_resume_with_other_turn(rpc):
            self.campaign.save(last_instruction=self.accepted_control())
            rpc.status("active")
            rpc.started("immediate-root-turn")
            rpc.started("unresolved-child-turn", thread="original-child")

        self.rpc.steps.extend([explicit_resume_with_other_turn, self.end_while_retained])
        self.run_to_fixture_boundary()
        self.assert_original_custody_survives()
        self.assertEqual(self.returned_from_wait, [])

    def test_active_goal_without_explicit_control_stays_retained(self):
        self.args.continuous = True
        self.initial_status = "blocked"
        self.before_begin_return = self.park_from_begin
        self.rpc.steps.extend([lambda rpc: rpc.status("active"), self.end_while_retained])
        self.run_to_fixture_boundary()
        self.assert_original_custody_survives()
        self.assertEqual(self.returned_from_wait, [])

    def test_plain_queued_instruction_cannot_dispatch_a_parked_continuous_owner(self):
        self.args.continuous = True
        self.args.repair_agent_failures = True
        self.initial_status = "blocked"

        def park_with_plain_instruction():
            launcher.queue_instruction(self.directory, "Ordinary source review instruction",
                                       source_id="offline-ordinary-instruction")
            self.park_from_begin()

        self.before_begin_return = park_with_plain_instruction
        self.rpc.steps.append(self.end_while_retained)
        self.run_to_fixture_boundary()
        self.assert_original_custody_survives()
        self.assertEqual(len(list((self.directory / "instructions" / "pending").glob("*.json"))), 1)
        self.assertEqual(self.returned_from_wait, [])

    def test_explicit_control_does_not_clear_a_later_user_stop(self):
        self.args.continuous = True
        self.initial_status = "blocked"
        self.before_begin_return = self.park_from_begin

        def resume_then_stop(rpc):
            self.campaign.save(last_instruction=self.accepted_control())
            rpc.status("active")
            self.campaign.on_signal(15, None)

        self.rpc.steps.extend([resume_then_stop, self.end_while_retained])
        self.run_to_fixture_boundary()
        self.assert_original_custody_survives()
        self.assertEqual(self.campaign.stop_reason, "signal_15")
        self.assertEqual(self.returned_from_wait, [])

    def test_noncontinuous_owner_cannot_resume_from_a_control_receipt(self):
        self.initial_status = "blocked"
        self.before_begin_return = self.park_from_begin

        def explicit_resume(rpc):
            self.campaign.save(last_instruction=self.accepted_control())
            rpc.status("active")

        self.rpc.steps.extend([explicit_resume, self.end_while_retained])
        self.run_to_fixture_boundary()
        self.assert_original_custody_survives()
        self.assertEqual(self.returned_from_wait, [])

    def test_different_owner_or_stop_generation_cannot_resume_retained_controller(self):
        self.args.continuous = True
        self.initial_status = "blocked"
        self.before_begin_return = self.park_from_begin

        def different_owner(rpc):
            self.campaign.save(last_instruction=self.accepted_control(owner_changes={"server_start": "999"}))
            rpc.status("active")

        def stale_generation(rpc):
            self.campaign.save(last_instruction=self.accepted_control(generation_delta=-1))

        self.rpc.steps.extend([different_owner, stale_generation, self.end_while_retained])
        self.run_to_fixture_boundary()
        self.assert_original_custody_survives()
        self.assertEqual(self.returned_from_wait, [])

    def test_continuous_alias_enables_resident_control_without_resetting_limits(self):
        args = launcher.arguments(["--continuous", "--hours", "2", "--agent-windows", "off"])
        self.assertTrue(args.continuous)
        self.assertTrue(args.retain_owner_on_stop)
        self.assertTrue(args.same_owner_control)
        self.assertTrue(args.repair_agent_failures)
        self.assertEqual(args.hours, 2)


if __name__ == "__main__":
    unittest.main()
