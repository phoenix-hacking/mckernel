"""SIMPLE policy regressions: temporary state and existing FakeRPC only."""
import copy
import json
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from scripts.tests import test_os_goal_continuous_eligibility as controls
from scripts.tests.test_os_goal_launcher import launcher, goal
import m14_m15_control


class SimpleTests(unittest.TestCase):
    def fixture(self):
        f = controls.ContinuousEligibilityTests("runTest")
        f.setUp()
        self.addCleanup(f.doCleanups)
        return f

    def original_identity(self):
        return patch.multiple(launcher, SIMPLE_ROOT_ID="test-thread",
                              SIMPLE_CREDIT_RUN_ID="a" * 32, SIMPLE_CREDIT_BUDGET="100")

    def stopped(self, f, *, status="consumed", errors=None):
        f.retained_paused_owner()
        c = f.campaign
        request = {"schema_version": 1, "reason": "user_stop", "id": "explicit-user-stop-1", "status": status, "errors": errors or [],
                   "owner": m14_m15_control._owner(c.state), "boot_id": m14_m15_control._boot_id()}
        launcher.atomic_json(f.directory / m14_m15_control.REQUEST, request)
        c.stop_reason, c.stop_now, c.checkpoint_requested, c.stopping = "user_stop", True, False, True
        c.save(stop_reason="user_stop", user_stop=request, controller_dispatch_enabled=False)
        c.refresh_credit_budget(control_only=True)
        return request

    def test_simple_args_keep_original_finite_identity_without_optional_monitors(self):
        args = launcher.arguments(["--simple-m14-m15"])
        self.assertEqual((args.credit_run_id, args.credit_budget),
                         ("7c6ef3604bfb4008a917bba8cfb6cfaa", "52079.8011050000"))
        self.assertEqual((args.model, args.effort, args.max_agents), ("gpt-6.1-sol", "max", 11))
        self.assertTrue(args.same_owner_control and args.retain_owner_on_stop)
        self.assertEqual((args.max_restarts, args.watchdog_seconds, args.stall_seconds), (0, 0, 0))
        self.assertEqual((args.agent_windows, args.mailbox_monitor), ("off", "off"))
        self.assertFalse(args.progress_control or args.stop_on_closure_stall)

    def test_simple_constructor_refuses_missing_saved_campaign_before_runtime_creation(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            with self.assertRaisesRegex(RuntimeError, "existing saved Root"):
                launcher.Campaign(launcher.arguments(["--simple-m14-m15"]), directory, directory)
            self.assertFalse((directory / "runs").exists())

    def test_simple_skips_registry_and_progress_windows_but_keeps_ledger(self):
        f = self.fixture()
        before = f.campaign.credit_guard.path.read_bytes()
        f.args.simple_m14_m15 = True
        with self.original_identity(), patch("os_goal_source_registry.SourceWorkRegistry", side_effect=AssertionError("registry created")):
            c = launcher.Campaign(f.args, f.directory, f.directory)
        self.addCleanup(c.output.close)
        self.assertIsNone(c.source_work_registry)
        self.assertIsNone(c.source_work_registry_provider)
        self.assertFalse(c.progress_enabled())
        self.assertEqual(before, c.credit_guard.path.read_bytes())
        text = c.instructions()
        self.assertIn("instructions/CAMPAIGN.md", text)
        self.assertIn("docs/verification/M14-M15-OPEN-DELIVERABLES.md", text)
        self.assertIn("replaces old GOAL/START/CURRENT/archive reading lists", text)
        self.assertNotIn("--set-closure-target", text)

    def test_explicit_consumed_stop_resume_adopts_simple_without_new_writer_or_ledger(self):
        f = self.fixture()
        c, rpc = f.campaign, f.rpc
        request = self.stopped(f)
        before = c.credit_guard.path.read_bytes()
        with self.original_identity():
            queued = launcher.queue_same_owner_resume(f.directory, "Explicitly run SIMPLE.",
                source_id="manual-simple-run", simple_m14_m15=True)
            self.assertIsInstance(queued, str)
            c.deliver_instruction(control_only=True)
        receipt = c.state["last_instruction"]
        self.assertEqual(receipt["status"], "accepted_by_server")
        self.assertEqual(receipt["user_stop_request_id"], request["id"])
        self.assertTrue(c.args.simple_m14_m15)
        self.assertFalse(c.progress_enabled())
        self.assertIsNone(c.source_work_registry)
        self.assertIsNone(c.stop_reason)
        self.assertFalse(c.stop_now or c.checkpoint_requested or c.stopping)
        self.assertIs(c.rpc, rpc)
        self.assertEqual(c.state["thread_id"], "test-thread")
        self.assertEqual(c.credit_guard.path.read_bytes(), before)
        self.assertFalse(any(method in {"thread/start", "thread/resume", "turn/start"} for method, _ in rpc.calls))
        f.assert_holds_retained()
        # Ordinary instructions must not make a consumed STOP latch again.
        c.state["last_instruction"] = {"id": "ordinary", "status": "accepted_by_server"}
        self.assertFalse(m14_m15_control.consume_stop(c))

    def test_uncertain_user_stop_and_real_holds_refuse_resume(self):
        for updates in ({"uncertain": True}, {"service_hold": {"reason": "actual"}},
                        {"transport_uncertain": {"method": "turn/steer"}}):
            with self.subTest(updates=updates):
                f = self.fixture()
                self.stopped(f, status="uncertain" if updates.get("uncertain") else "consumed",
                             errors=["interrupt not confirmed"] if updates.get("uncertain") else [])
                if not updates.get("uncertain"):
                    f.campaign.save(**updates)
                with self.original_identity(), self.assertRaises(ValueError):
                    launcher.queue_same_owner_resume(f.directory, "run", source_id="refused", simple_m14_m15=True)
                self.assertTrue(f.campaign.stop_now)
                self.assertEqual(f.campaign.stop_reason, "user_stop")
                self.assertFalse(any(method == "thread/goal/set" and params.get("status") == "active"
                                     for method, params in f.rpc.calls))
                f.assert_holds_retained()

    def test_user_stop_account_transport_recovery_never_resumes_or_clears_stop(self):
        f = self.fixture()
        c = f.campaign
        self.stopped(f)
        ledger = c.credit_guard.path.read_bytes()
        error = "App-server request timed out: account/rateLimits/read"
        f.rpc.usage_error = RuntimeError(error)
        with patch.object(launcher.time, "sleep"):
            c.refresh_credit_budget(control_only=True)
        self.assertEqual(c.stop_reason, "user_stop")
        self.assertEqual(c.state["credit_budget_error"], error)
        self.assertTrue(launcher.account_read_retry_eligible(c.state))
        with self.assertRaisesRegex(ValueError, "fresh successful"):
            f.queue("not-yet-recovered")
        f.rpc.usage_error = None
        c.refresh_credit_budget(control_only=True)
        self.assertEqual(c.stop_reason, "user_stop")
        self.assertTrue(c.stop_now)
        self.assertIsNone(c.state["credit_budget_error"])
        self.assertEqual(c.goal["status"], "paused")
        self.assertEqual(c.credit_guard.path.read_bytes(), ledger)
        self.assertFalse(any(method == "thread/goal/set" and params.get("status") == "active"
                             for method, params in f.rpc.calls))
        f.assert_holds_retained()

    def test_simple_no_ready_timeout_ignores_old_optional_progress_window(self):
        f = self.fixture()
        c = f.campaign
        c.args.simple_m14_m15 = True
        c.save(progress_snapshot={"operation": {"status": "HEALTHY_BOUNDED_OPERATION",
                                                "deadline_at": "2099-01-01T00:00:00Z"}})
        c.blocked_idle_since = time.monotonic() - c.args.blocked_idle_seconds - 1
        c.save(blocked_idle={"status": "waiting_for_ready_work"})
        c.poll_blocked_idle()
        self.assertEqual(c.stop_reason, "blocked_no_ready_work")
        self.assertFalse(c.state["controller_dispatch_enabled"])
        self.assertEqual(c.goal["status"], "blocked")
        f.assert_holds_retained()

    def test_stop_hook_precedes_reads_in_normal_and_retained_loop(self):
        f = self.fixture()
        c = f.campaign
        c.args.retain_owner_on_stop = True
        def stop():
            c.stop_reason, c.stop_now = "user_stop", True
        with patch.object(c, "consume_user_stop", side_effect=stop) as hook, \
                patch.object(c, "refresh_credit_budget") as read, patch.object(c, "retain_owner"):
            self.assertEqual(c._run_until_stop(begin=False), 23)
            hook.assert_called_once()
            read.assert_not_called()
        class EndFixture(BaseException):
            pass
        with patch.object(c, "consume_user_stop", side_effect=EndFixture) as hook, \
                patch.object(c, "refresh_credit_budget") as read, patch.object(c, "retain_owner"):
            with self.assertRaises(EndFixture):
                c.wait_retained_owner("user_stop")
            hook.assert_called_once()
            read.assert_not_called()

    def test_render_is_local_and_reporting_failure_does_not_stop_engineering(self):
        f = self.fixture()
        c = f.campaign
        c.args.simple_m14_m15 = True
        c.goal = goal("active")
        with patch("m14_m15_progress.render_progress", side_effect=OSError("display unavailable")) as render:
            c.render_simple_progress()
        render.assert_called_once()
        self.assertIsNone(c.stop_reason)
        self.assertFalse(c.stop_now)


class NotificationFallbackTests(unittest.TestCase):
    def fixture(self):
        f = controls.ContinuousEligibilityTests("runTest")
        f.setUp()
        self.addCleanup(f.doCleanups)
        c, rpc = f.campaign, f.rpc
        c.goal = rpc.goal = goal("active")
        c.save(phase="running", goal=c.goal)
        context = rpc.context(rpc.limits, source="notification")
        context.pop("response_error")  # Actual notification shape.
        rpc.last_account_notification = context
        rpc.emit("account/rateLimits/updated", {"rateLimits": rpc.limits})
        self.assertEqual(c.state["last_account_observation"]["status"], "ACCEPTED")
        return f

    def test_null_transport_error_preserves_original_accepted_notification_and_clocks(self):
        f = self.fixture()
        c = f.campaign
        before = copy.deepcopy(c.state["last_account_observation"])
        ledger = c.credit_guard.path.read_bytes()
        f.rpc.usage_error = RuntimeError('account/rateLimits/read: ' + json.dumps({
            "code": -32603, "message": "failed to fetch codex rate limits: GET https://chatgpt.com/backend-api/wham/usage failed: 503 Service Unavailable; temporary backend failure"}))
        c.refresh_credit_budget()
        self.assertEqual(c.state["last_account_observation"], before)
        self.assertEqual(c.state["last_usage_read_error_context"]["receive"]["rate_limits_sha256"],
                         launcher._account_value_sha256(None))
        self.assertEqual(c.credit_guard.path.read_bytes(), ledger)
        launcher.accepted_account_observation(c.state, f.ledger(), f.owner(), time.time_ns(), time.monotonic_ns())
        self.assertFalse(c.stop_now)
        self.assertIsNone(c.stop_reason)
        f.assert_holds_retained()

    def test_stale_foreign_and_protected_error_never_get_notification_fallback(self):
        for variant in ("stale", "foreign", "auth", "real_hold"):
            with self.subTest(variant=variant):
                f = self.fixture()
                c = f.campaign
                completion = f.rpc.context(None, response_error=True)
                error = RuntimeError("App-server request timed out: account/rateLimits/read")
                if variant == "stale":
                    c.last_credit_notification = (f.rpc, time.monotonic() - 26)
                elif variant == "foreign":
                    f.rpc.last_account_notification["server_pid"] += 1
                elif variant == "auth":
                    error = RuntimeError("401 Unauthorized")
                else:
                    c.save(service_hold={"reason": "actual"})
                before = copy.deepcopy(c.state["last_account_observation"])
                self.assertFalse(c.preserve_validated_notification(error, completion))
                self.assertEqual(c.state["last_account_observation"], before)
                self.assertNotIn("last_usage_read_notification_fallback", c.state)


if __name__ == "__main__":
    unittest.main()
