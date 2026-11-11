"""Focused real-source account-read persistence tests. Private lower effects only.

Actual SDK source39a03dd8 is frozen; behavior/type correctness is unproved until
the admitted HOST command. This is never a launcher/account entrypoint.
"""
from contextlib import ExitStack, redirect_stdout
import copy
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from unittest.mock import patch

RUN_ID = "a" * 32  # Isolated fake ledger only; never an actual launch identifier.
METHOD = "account/rateLimits/read"


def limits(balance="1000", **fields):
    value = {"primary": {"usedPercent": 46, "windowDurationMins": 10080}, "credits": {
        "hasCredits": True, "unlimited": False, "balance": balance}}
    value.update(fields)
    return value


class Clock:
    def __init__(self):
        self.seconds = 100.0
        self.wall = 1800000100.0

    def monotonic(self):
        return self.seconds

    def monotonic_ns(self):
        return int(self.seconds * 1000000000)

    def time(self):
        return self.wall

    def time_ns(self):
        return int(self.wall * 1000000000)

    def utc(self):
        return datetime.fromtimestamp(self.wall, timezone.utc).isoformat()

    def receive(self):
        self.seconds += 1.0
        self.wall += 1.0


class FakePipe:
    def __init__(self, descriptor):
        self.descriptor = descriptor
        self.closed = False

    def fileno(self):
        return self.descriptor

    def close(self):
        self.closed = True


class FakeSelector:
    def __init__(self):
        self.registered = None
        self.closed = False

    def register(self, pipe, events):
        self.registered = pipe

    def select(self, timeout):
        return [(self.registered, 1)]

    def close(self):
        self.closed = True


class ProtocolHarness:
    """Only lower process/pipe/clock effects are controlled.

    RPC construction, id assignment, JSON send/receive, pump and call remain the
    actual candidate. No synthetic completion/receipt is assigned by this class.
    """
    def __init__(self, launcher, directory, clock, on_event):
        self.launcher, self.directory, self.clock = launcher, directory, clock
        self.on_event = on_event
        self.replies = []
        self.sent = []
        self.pending = []
        self.infer_or_mutate = []
        self.stdout = FakePipe(931)
        self.stdin = self
        self.pid = os.getpid()  # Explicit controlled server identity; no child.
        self.returncode = 0
        self.selector = FakeSelector()
        self.rpc = None

    def spawn(self, argv, **kwargs):
        if argv != ["controlled-lower-server-never-executed"]:
            raise AssertionError("Unexpected subprocess request")
        return self

    def write(self, raw):
        request = json.loads(raw)
        self.sent.append(request)
        if request.get("method") != METHOD:
            self.infer_or_mutate.append(request)
            raise AssertionError("Only the finite read-only account method is allowed")
        if not self.replies:
            raise AssertionError("Finite scripted reply vector exhausted")
        script = self.replies.pop(0)
        messages = script(request) if callable(script) else [
            {"id": request["id"], "result": script}]
        self.pending.append(b"".join((json.dumps(m) + "\n").encode() for m in messages))
        return len(raw)

    def flush(self):
        return None

    def close(self):
        return None

    def wait(self, timeout):
        return 0

    def poll(self):
        return 0

    def terminate(self):
        raise AssertionError("No real or fake server termination is permitted")

    def kill(self):
        raise AssertionError("No real or fake server kill is permitted")

    def read(self, descriptor, maximum):
        if descriptor != self.stdout.fileno():
            raise AssertionError("Unexpected transport descriptor")
        self.clock.receive()
        if not self.pending:
            self.clock.seconds += 60
            return b""
        value = self.pending.pop(0)
        if len(value) > maximum:
            self.pending.insert(0, value[maximum:])
        return value[:maximum]

    def open(self, testcase):
        module = self.launcher
        for manager in [
            patch.object(module.subprocess, "Popen", side_effect=self.spawn),
            patch.object(module.selectors, "DefaultSelector", return_value=self.selector),
            patch.object(module.os, "read", side_effect=self.read),
            patch.object(module.time, "monotonic", side_effect=self.clock.monotonic),
            patch.object(module.time, "monotonic_ns", side_effect=self.clock.monotonic_ns),
            patch.object(module.time, "time", side_effect=self.clock.time),
            patch.object(module.time, "time_ns", side_effect=self.clock.time_ns),
            patch.object(module, "utc", side_effect=self.clock.utc),
            patch.object(module.time, "sleep", return_value=None),
        ]:
            testcase.contexts.enter_context(manager)
        self.rpc = module.RPC(["controlled-lower-server-never-executed"], self.directory, self.on_event)
        # Close only real private files/selector and fake pipe. No child exists.
        testcase.addCleanup(self.rpc.close)
        return self.rpc


class FocusedReceiptTests(unittest.TestCase):
    launcher = None  # Bound to exact frozen candidate by final source tuple.

    def setUp(self):
        self.contexts = ExitStack()
        self.addCleanup(self.contexts.close)
        temporary = tempfile.TemporaryDirectory(prefix="account-read-receipt-test-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        args = self.launcher.arguments(["--hours", "0", "--agent-windows", "off",
            "--quiet", "--credit-budget", "100", "--credit-run-id", RUN_ID])
        self.c = self.launcher.Campaign(args, self.root, self.root)
        self.addCleanup(self.c.output.close)
        self.clock = Clock()
        self.transport = ProtocolHarness(self.launcher, self.c.log_dir, self.clock, self.c.event)
        self.c.rpc = self.transport.open(self)
        stat_fields = Path("/proc/self/stat").read_text().rsplit(")", 1)[1].split()
        self.c.state.update(worker_pid=os.getpid(), worker_start=stat_fields[19],
            server_pid=self.transport.pid, server_start=stat_fields[19],
            guardian_run_id="private-test-guardian",
            thread_id="isolated-receipt-test-root", phase="running", auth_mode="chatgpt",
            goal={"status": "active", "threadId": "isolated-receipt-test-root",
                  "objective": "Private receipt fixture; never a production goal"})
        self.original_atomic_json = self.launcher.atomic_json
        self.original_credit_write = self.c.credit_guard.write_json

    def poll(self, balance="1000", **fields):
        self.transport.replies.append({"rateLimits": limits(balance, **fields)})
        self.c.refresh_credit_budget()

    def durable_state(self):
        return json.loads(self.c.state_path.read_text())

    def durable_ledger(self):
        return json.loads(self.c.credit_guard.path.read_text())

    def assert_no_external_calls(self):
        self.assertEqual(self.transport.infer_or_mutate, [])
        self.assertTrue(all(item["method"] == METHOD for item in self.transport.sent))

    def owner(self, campaign=None):
        campaign = self.c if campaign is None else campaign
        birth = Path("/proc/self/stat").read_text().rsplit(")", 1)[1].split()[19]
        objective = campaign.state["goal"]["objective"]
        return {"boot_id": Path("/proc/sys/kernel/random/boot_id").read_text().strip(),
            "repo": str(campaign.repo), "guardian_run_id": "private-test-guardian",
            "log_dir": str(campaign.log_dir), "thread_id": campaign.state["thread_id"],
            "goal_objective_sha256": hashlib.sha256(json.dumps(objective,
                sort_keys=True, separators=(",", ":")).encode()).hexdigest(),
            "worker_pid": os.getpid(), "worker_start": birth,
            "server_pid": self.transport.pid, "server_start": birth,
            "credit_run_id": campaign.credit_guard.identifier, "credit_budget": "100",
            "credit_ledger_path": str(campaign.credit_guard.path)}

    def accepted(self, *, state=None, ledger=None, owner=None, utc_ns=None, mono_ns=None):
        return self.launcher.accepted_account_observation(
            self.durable_state() if state is None else state,
            self.durable_ledger() if ledger is None else ledger,
            self.owner() if owner is None else owner,
            self.clock.time_ns() if utc_ns is None else utc_ns,
            self.clock.monotonic_ns() if mono_ns is None else mono_ns)

    def unusable(self):
        with self.assertRaises((ValueError, FileNotFoundError)):
            self.accepted()

    def note(self, **values):
        self.observations.append({"test": self._testMethodName, **values})

    def notification(self, balance="1000", **fields):
        return {"method": "account/rateLimits/updated",
                "params": {"rateLimits": limits(balance, **fields)}}

    def queue_error(self):
        # Exact existing read-only temporary usage-reporting error class. It is
        # lower transport data, never an actual network or account operation.
        def error(request):
            return [{"id": request["id"], "error": {"code": -32603,
                "message": "failed to fetch codex rate limits: GET "
                "https://chatgpt.com/backend-api/wham/usage failed: "
                "502 Bad Gateway; controlled private transport"}}]
        self.transport.replies.append(error)

    def tearDown(self):
        self.assert_no_external_calls()

    def test_rpc_receive_id_time_and_wrong_reply(self):
        sent_utc, sent_mono = self.clock.time_ns(), self.clock.monotonic_ns()
        self.transport.replies.append({"rateLimits": limits()})
        result = self.c.rpc.call(METHOD, {}, timeout=10)
        completion = self.c.rpc.last_account_read_completion
        self.assertEqual(result, {"rateLimits": limits()})
        self.assertEqual((completion["method"], completion["request_id"],
                          completion["server_pid"], completion["sequence"]),
                         (METHOD, self.transport.sent[0]["id"], self.transport.pid, 1))
        self.assertEqual((completion["received_utc_ns"], completion["received_mono_ns"]),
                         (sent_utc + 1000000000, sent_mono + 1000000000))
        self.assertFalse(completion["response_error"])
        self.assertIsNone(self.c.rpc.last_account_notification)
        self.assertNotIn("successful_account_read", self.c.state)
        self.queue_error()
        with self.assertRaises(RuntimeError):
            self.c.rpc.call(METHOD, {}, timeout=10)
        self.assertTrue(self.c.rpc.last_account_read_completion["response_error"])
        self.assertNotIn("successful_account_read", self.c.state)
        self.transport.replies.append(lambda request: [
            {"id": request["id"] + 50, "result": {"rateLimits": limits()}}])
        with self.assertRaises(self.launcher.RecoverableFailure):
            self.c.rpc.call(METHOD, {}, timeout=10)
        self.assertIsNone(self.c.rpc.last_account_read_completion)
        self.assertEqual(self.c.rpc.pending_methods, {})
        self.note(reply_id=1, receive_delay_ns=1000000000,
                  wrong_id_does_not_complete=True, error_does_not_publish=True)

    def test_no_notification_poll_persists_original_guard(self):
        observed_boundaries = []
        def ledger_write(path, value):
            self.unusable()
            self.original_credit_write(path, value)
            observed_boundaries.append("ledger_durable")
        def state_write(path, value):
            if Path(path) == self.c.state_path:
                # A staged ACCEPTED value is not yet a durable receipt. Invoke
                # the real validator over the actual disk state at this point.
                self.unusable()
                self.original_atomic_json(path, value)
                if value.get("successful_account_read", {}).get("status") == "ACCEPTED":
                    observed_boundaries.append("receipt_state_durable")
            else:
                self.original_atomic_json(path, value)
        with patch.object(self.c.credit_guard, "write_json", side_effect=ledger_write), \
                patch.object(self.launcher, "atomic_json", side_effect=state_write):
            self.poll()
        self.assertEqual(observed_boundaries, ["ledger_durable", "receipt_state_durable"])
        receipt = self.accepted()
        self.assertEqual((receipt["source"], receipt["request_id"]), ("read", 1))
        self.assertIsNone(self.c.last_credit_notification)
        self.poll("950")
        ledger = self.durable_ledger()
        self.assertEqual((ledger["id"], ledger["budget"], ledger["spent"], ledger["remaining"]),
                         (RUN_ID, "100", "50", "50"))
        self.assertEqual(self.accepted()["request_id"], 2)
        self.note(source="read", no_notification=True,
                  persistence_order=observed_boundaries, spent="50", remaining="50")

    def test_ledger_write_failure_is_not_success(self):
        def fail(path, value):
            raise OSError("private fixture ledger durability failure")
        with patch.object(self.c.credit_guard, "write_json", side_effect=fail):
            self.poll()
        self.assertEqual(self.c.stop_reason, "credit_budget_unknown")
        self.assertEqual(self.durable_state()["last_account_observation"]["status"], "REJECTED")
        self.unusable()
        self.note(failed_boundary="ledger", usable=False)

    def test_credit_state_write_failure_is_not_success(self):
        self.poll()
        failed = []
        def state_write(path, value):
            if (not failed and Path(path) == self.c.state_path
                    and value.get("credit_budget", {}).get("spent") == "50"):
                failed.append("credit_state")
                raise OSError("private fixture credit-state durability failure")
            self.original_atomic_json(path, value)
        with patch.object(self.launcher, "atomic_json", side_effect=state_write):
            self.poll("950")
        self.assertEqual(failed, ["credit_state"])
        self.assertEqual(self.c.stop_reason, "credit_budget_unknown")
        self.assertEqual(self.durable_ledger()["spent"], "50")
        self.assertEqual(self.durable_ledger()["id"], RUN_ID)
        self.unusable()
        self.note(failed_boundary="credit_state_after_real_observe", spent="50", usable=False)

    def test_receipt_state_write_failure_is_not_success(self):
        failed = []
        def state_write(path, value):
            if (not failed and Path(path) == self.c.state_path
                    and value.get("successful_account_read", {}).get("status") == "ACCEPTED"):
                self.unusable()
                failed.append("receipt_state")
                raise OSError("private fixture receipt-state durability failure")
            self.original_atomic_json(path, value)
        with patch.object(self.launcher, "atomic_json", side_effect=state_write):
            self.poll()
        self.assertEqual(failed, ["receipt_state"])
        self.assertEqual(self.c.stop_reason, "credit_budget_unknown")
        self.unusable()
        self.note(failed_boundary="receipt_state", usable=False)

    def test_hold_after_observe_vetoes_success(self):
        def ledger_write(path, value):
            self.original_credit_write(path, value)
            self.c.stop_reason, self.c.stop_now = "private_fixture_existing_stop", True
        with patch.object(self.c.credit_guard, "write_json", side_effect=ledger_write):
            self.poll()
        self.assertEqual(self.c.stop_reason, "private_fixture_existing_stop")
        self.assertEqual(self.durable_state()["last_account_observation"]["status"], "REJECTED")
        self.unusable()
        self.note(hold_after_observe=True, hold_preserved=True, usable=False)

    def test_newer_unknown_notification_vetoes_read(self):
        self.poll()
        invalid = limits("990")
        invalid["primary"]["usedPercent"] = None
        self.transport.replies.append(lambda request: [
            {"id": request["id"], "result": {"rateLimits": limits("995")}},
            {"method": "account/rateLimits/updated", "params": {"rateLimits": invalid}}])
        self.c.refresh_credit_budget()
        newest = self.durable_state()["last_account_observation"]
        self.assertEqual((newest["source"], newest["status"], newest["sequence"]),
                         ("notification", "REJECTED", 3))
        self.assertEqual(self.c.stop_reason, "included_usage_unknown")
        self.assertLess(self.clock.monotonic_ns() - self.c.state["successful_account_read"]["received_mono_ns"],
                        25 * 1000000000)
        self.unusable()
        self.note(newest="unknown_notification", sequence=3, older_read_fresh=True, usable=False)

    def test_newer_spend_notification_vetoes_read(self):
        self.poll()
        self.transport.replies.append(lambda request: [
            {"id": request["id"], "result": {"rateLimits": limits("995")}},
            self.notification("990", spendControlReached=True)])
        self.c.refresh_credit_budget()
        newest = self.durable_state()["last_account_observation"]
        self.assertEqual((newest["source"], newest["status"], newest["sequence"]),
                         ("notification", "REJECTED", 3))
        self.assertEqual(self.c.stop_reason, "credit_budget_unknown")
        self.assertIn("spending control", self.c.state["credit_budget_error"].lower())
        self.unusable()
        self.note(newest="spend_notification", sequence=3, older_read_fresh=True, usable=False)

    def test_newer_valid_notification_retains_time_and_same_ledger(self):
        self.poll()
        self.transport.replies.append(lambda request: [
            {"id": request["id"], "result": {"rateLimits": limits("990")}},
            self.notification("980")])
        self.c.refresh_credit_budget()
        selected, ledger = self.accepted(), self.durable_ledger()
        received = self.c.rpc.last_account_notification
        self.assertEqual((selected["source"], selected["request_id"], selected["sequence"]),
                         ("notification", None, 3))
        self.assertEqual((selected["received_utc_ns"], selected["received_mono_ns"]),
                         (received["received_utc_ns"], received["received_mono_ns"]))
        self.assertEqual(self.durable_state()["last_rate_limits"], limits("980"))
        # Literal conservative original-ledger result: 1000->980->990->980.
        # No allowance refund/reset; the late snapshot cannot refresh time.
        self.assertEqual((ledger["id"], ledger["spent"], ledger["remaining"]), (RUN_ID, "30", "70"))
        self.note(newest="notification", sequence=3, unchanged_receive_clock=True, spent="30", remaining="70")

    def test_newer_valid_read_follows_notification(self):
        self.poll()
        self.transport.replies.append(lambda request: [
            self.notification("990"),
            {"id": request["id"], "result": {"rateLimits": limits("980")}}])
        self.c.refresh_credit_budget()
        selected, ledger = self.accepted(), self.durable_ledger()
        self.assertEqual((selected["source"], selected["request_id"], selected["sequence"]), ("read", 2, 3))
        self.assertEqual((ledger["id"], ledger["spent"], ledger["remaining"]), (RUN_ID, "20", "80"))
        self.note(newest="read", sequence=3, spent="20", remaining="80")

    def test_current_owner_clock_and_method_validation(self):
        self.poll()
        state, ledger, owner = self.durable_state(), self.durable_ledger(), self.owner()
        selected = self.accepted()
        for key, value in (("worker_start", "0"), ("server_start", "0"),
                           ("thread_id", "different-private-root"),
                           ("guardian_run_id", "different-private-guardian")):
            with self.subTest(owner_field=key):
                wrong = dict(owner, **{key: value})
                with self.assertRaises(ValueError):
                    self.accepted(state=state, ledger=ledger, owner=wrong)
        for delta in (-1, 25000000000):
            with self.subTest(age_ns=delta):
                with self.assertRaises(ValueError):
                    self.accepted(utc_ns=selected["received_utc_ns"] + delta,
                                  mono_ns=selected["received_mono_ns"] + delta)
        self.assertEqual(self.accepted(utc_ns=selected["received_utc_ns"] + 24999999999,
            mono_ns=selected["received_mono_ns"] + 24999999999)["source"], "read")
        for field, value in (("method", "account/read"), ("request_id", "1")):
            with self.subTest(context_field=field):
                wrong = copy.deepcopy(state)
                for key in ("last_account_observation", "successful_account_read"):
                    wrong[key][field] = value
                with self.assertRaises(ValueError):
                    self.accepted(state=wrong)
        for hold in ("policy_hold", "chatgpt_auth_changed", "credit_budget_unknown", "signal_2"):
            with self.subTest(hold=hold):
                with self.assertRaises(ValueError):
                    self.accepted(state=dict(state, stop_reason=hold))
        self.note(owner_mismatches_rejected=4, exact_25s_rejected=True,
                  future_rejected=True, accepted_below_25s=True, holds_veto=True)

    def test_timestamps_without_rpc_cannot_create_or_revive_receipt(self):
        self.c.record_rate_limits(limits())
        heartbeat = self.root / "heartbeat.json"
        heartbeat.write_text("{}\n")
        self.c.save(updated_at=self.clock.utc())
        for path in (heartbeat, self.c.state_path, self.c.credit_guard.path):
            os.utime(path, ns=(self.clock.time_ns(), self.clock.time_ns()))
        self.unusable()
        self.poll("990")
        self.accepted()
        self.clock.seconds += 25
        self.clock.wall += 25
        self.c.save(updated_at=self.clock.utc())
        for path in (heartbeat, self.c.state_path, self.c.credit_guard.path):
            os.utime(path, ns=(self.clock.time_ns(), self.clock.time_ns()))
        self.unusable()
        self.note(heartbeat_and_mtime_never_sufficient=True, stale_not_revived=True)

    def test_successful_read_never_grants_timeout_fallback(self):
        self.poll()
        self.assertIsNone(self.c.last_credit_notification)
        for unused in range(3):
            self.queue_error()
        self.c.refresh_credit_budget()
        self.assertEqual(len(self.transport.sent), 4)
        self.assertEqual(self.c.stop_reason, "credit_budget_unknown")
        self.assertNotIn("last_usage_read_notification_fallback", self.c.state)
        self.unusable()
        self.note(successful_poll_is_not_notification_fallback=True, later_read_attempts=3)

    def test_existing_notification_fallback_unchanged(self):
        self.transport.pending.append((json.dumps(self.notification()) + "\n").encode())
        self.c.rpc.pump()
        self.assertEqual(self.accepted()["source"], "notification")
        observed_rpc, observed_at = self.c.last_credit_notification
        self.queue_error()
        self.c.refresh_credit_budget()
        self.assertIsNone(self.c.stop_reason)
        self.assertIs(observed_rpc, self.c.rpc)
        self.assertEqual(self.c.last_credit_notification, (observed_rpc, observed_at))
        fallback = self.c.state["last_usage_read_notification_fallback"]
        self.assertEqual((fallback["source"], fallback["age_seconds"]),
                         ("same_worker_server_validated_persisted_notification", 1.0))
        self.assertEqual(len(self.transport.sent), 1)
        self.assertNotIn("successful_account_read", self.c.state)
        self.note(notification_only_fallback=True, same_rpc=True, age_seconds=1.0)

    def test_saved_receipt_not_inherited_by_new_campaign(self):
        self.poll()
        before = self.durable_state()
        args = self.launcher.arguments(["--hours", "0", "--agent-windows", "off", "--quiet",
            "--credit-budget", "100", "--credit-run-id", RUN_ID])
        successor = self.launcher.Campaign(args, self.root, self.root)
        self.addCleanup(successor.output.close)
        for key in ("last_account_observation", "last_account_notification", "successful_account_read"):
            self.assertNotIn(key, successor.state)
        with self.assertRaises(ValueError):
            self.launcher.accepted_account_observation(before, self.durable_ledger(),
                self.owner(successor), self.clock.time_ns(), self.clock.monotonic_ns())
        self.assertEqual(self.durable_ledger()["id"], RUN_ID)
        self.assertEqual(self.durable_ledger()["spent"], "0")
        self.note(saved_receipt_not_inherited=True, same_ledger_retained=True)

    def consumer_fixture(self):
        # Hardcoded normal-owner constants belong to the actual consumer. These
        # literals are exercised ONLY in a new private model repository; no real
        # goal, credit ledger, RPC, issuer or canonical module is changed.
        repo = self.root / "isolated-normal-repo"
        scripts = repo / "scripts"
        scripts.mkdir(parents=True)
        (scripts / "run_os_goal.py").write_bytes(SOURCE.read_bytes())
        directory = repo / ".git/os-autopilot"
        directory.mkdir(parents=True)
        consumer_path = Path("/home/holden/mckernel-work/m14-blocker-resolution-20261110/account-read-receipt-consumer-root-1/correction-1/current_account_snapshot.py")
        if hashlib.sha256(consumer_path.read_bytes()).hexdigest() != "43935afcd79375e9e19a37c71ecab5c901561434dc6a31b9df63157c94c3798a":
            raise ValueError("Root consumer source changed")
        spec = importlib.util.spec_from_file_location("actual_snapshot_consumer", consumer_path)
        consumer = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(consumer)
        consumer.REPO = repo  # Explicit lower filesystem namespace only.
        saved_module = sys.modules.pop("run_os_goal", None)
        old_search_path = list(sys.path)
        def restore_import_namespace():
            sys.modules.pop("run_os_goal", None)
            if saved_module is not None:
                sys.modules["run_os_goal"] = saved_module
            sys.path[:] = old_search_path
        self.addCleanup(restore_import_namespace)
        validator = consumer._load_current_validator()
        normal = sys.modules["run_os_goal"]
        self.assertIs(validator, normal.accepted_account_observation)
        self.assertEqual(Path(normal.__file__), scripts / "run_os_goal.py")
        self.assertEqual(hashlib.sha256(Path(normal.__file__).read_bytes()).hexdigest(), SOURCE_SHA256)
        args = normal.arguments(["--hours", "0", "--agent-windows", "off", "--quiet",
            "--credit-budget", "100", "--credit-run-id", "7c6ef3604bfb4008a917bba8cfb6cfaa"])
        campaign = normal.Campaign(args, repo, directory)
        self.addCleanup(campaign.output.close)
        transport = ProtocolHarness(normal, campaign.log_dir, self.clock, campaign.event)
        campaign.rpc = transport.open(self)
        birth = Path("/proc/self/stat").read_text().rsplit(")", 1)[1].split()[19]
        thread = "01a18bc3-e072-7810-9426-75101b0856c0"
        campaign.state.update(worker_pid=os.getpid(), worker_start=birth,
            server_pid=transport.pid, server_start=birth,
            guardian_run_id="private-test-guardian", thread_id=thread,
            phase="running", auth_mode="chatgpt", stop_reason=None,
            weekly_usage_error=None, weekly_confirmation_pending=False,
            goal={"status": "active", "threadId": thread,
                  "objective": "Private receipt fixture; never a production goal"})
        transport.replies.append({"rateLimits": limits()})
        campaign.refresh_credit_budget()
        expected_owner = self.owner(campaign)
        return consumer, normal, campaign, transport, expected_owner

    def test_consumer_no_notification_reads_matching_durable_receipt(self):
        consumer, normal, campaign, transport, expected = self.consumer_fixture()
        state, usage, ledger, observed = consumer.current_account_snapshot(expected)
        self.assertEqual((usage["source_kind"], usage["source_event"]), ("read", METHOD))
        self.assertEqual(usage["receipt_received_utc_ns"],
                         state["successful_account_read"]["received_utc_ns"])
        self.assertEqual(observed, usage["receipt_received_utc_ns"] / 1000000000)
        self.assertEqual(ledger, json.loads(campaign.credit_guard.path.read_text()))
        self.assertEqual((ledger["id"], ledger["spent"], ledger["remaining"]),
                         ("7c6ef3604bfb4008a917bba8cfb6cfaa", "0", "100"))
        self.assertIsNone(campaign.last_credit_notification)
        self.assertEqual(len(transport.sent), 1)
        self.assertEqual(transport.infer_or_mutate, [])
        self.note(consumer_actual_normal_importer=True, no_notification=True,
                  same_durable_ledger=True, no_refresh_or_issuer_call=True)

    def test_consumer_holds_owner_expiry_and_timestamps(self):
        consumer, normal, campaign, transport, expected = self.consumer_fixture()
        baseline = json.loads(campaign.state_path.read_text())
        for field, value in (("service_hold", True), ("auth_hold", True),
                ("billing_hold", True), ("policy_hold", True),
                ("credit_budget_error", "private persistence failure"),
                ("weekly_usage_error", "private unknown"),
                ("weekly_confirmation_pending", True)):
            with self.subTest(hold=field):
                normal.atomic_json(campaign.state_path, dict(baseline, **{field: value}))
                with self.assertRaises((AssertionError, ValueError)):
                    consumer.current_account_snapshot(expected)
        normal.atomic_json(campaign.state_path, baseline)
        with self.assertRaises((AssertionError, ValueError)):
            consumer.current_account_snapshot(dict(expected, server_start="0"))
        # A fresh file/heartbeat timestamp cannot make the actual read fresh.
        self.clock.seconds += 25
        self.clock.wall += 25
        heartbeat = campaign.directory / "heartbeat.json"
        heartbeat.write_text("{}\n")
        for path in (heartbeat, campaign.state_path, campaign.credit_guard.path):
            os.utime(path, ns=(self.clock.time_ns(), self.clock.time_ns()))
        with self.assertRaises((AssertionError, ValueError)):
            consumer.current_account_snapshot(expected)
        self.assertEqual(len(transport.sent), 1)
        self.note(consumer_holds_rejected=7, wrong_birth_rejected=True,
                  exact_25s_rejected=True, timestamp_not_authority=True)

    def test_consumer_bounded_bookends_and_postcoherence_freshness(self):
        consumer, normal, campaign, transport, expected = self.consumer_fixture()
        state1 = campaign.state_path.read_bytes()
        transport.replies.append({"rateLimits": limits("990")})
        campaign.refresh_credit_budget()
        state2, ledger2 = campaign.state_path.read_bytes(), campaign.credit_guard.path.read_bytes()
        original_read = Path.read_bytes
        def scenario(states, credits, expire_at_second_bookend=False):
            states, credits = list(states), list(credits)
            calls = {"states": 0, "ledgers": 0}
            def read(path):
                if path == campaign.state_path:
                    calls["states"] += 1
                    if expire_at_second_bookend and calls["states"] == 2:
                        self.clock.seconds += 25
                        self.clock.wall += 25
                    return states.pop(0)
                if path == campaign.credit_guard.path:
                    calls["ledgers"] += 1
                    return credits.pop(0)
                return original_read(path)
            return read, calls, states, credits
        read, calls, remaining_states, remaining_ledgers = scenario(
            [state1, state2, state2, state2], [ledger2, ledger2])
        with patch.object(Path, "read_bytes", read), patch.object(normal,
                "accepted_account_observation", wraps=normal.accepted_account_observation) as validate:
            state, usage, credit, observed = consumer.current_account_snapshot(expected)
            self.assertEqual(validate.call_count, 1)
        self.assertEqual((calls, remaining_states, remaining_ledgers),
                         ({"states": 4, "ledgers": 2}, [], []))
        self.assertEqual(state["successful_account_read"]["request_id"], 2)
        self.assertEqual((credit["spent"], credit["remaining"]), ("10", "90"))
        read, calls, remaining_states, remaining_ledgers = scenario(
            [state1, state2] * 3, [ledger2] * 3)
        with patch.object(Path, "read_bytes", read), patch.object(normal,
                "accepted_account_observation", wraps=normal.accepted_account_observation) as validate:
            with self.assertRaisesRegex(AssertionError, "did not stabilize"):
                consumer.current_account_snapshot(expected)
            self.assertEqual(validate.call_count, 0)
        self.assertEqual((calls, remaining_states, remaining_ledgers),
                         ({"states": 6, "ledgers": 3}, [], []))
        read, calls, remaining_states, remaining_ledgers = scenario(
            [state2, state2], [ledger2], expire_at_second_bookend=True)
        with patch.object(Path, "read_bytes", read):
            with self.assertRaisesRegex(ValueError, "stale"):
                consumer.current_account_snapshot(expected)
        self.assertEqual((calls, remaining_states, remaining_ledgers),
                         ({"states": 2, "ledgers": 1}, [], []))
        self.assertEqual(transport.infer_or_mutate, [])
        self.note(bookend_reads_before_accept=[4, 2], bounded_mismatch_reads=[6, 3],
                  validation_after_coherence=True, expiry_during_bookends_rejected=True)

SOURCE = Path("/home/holden/mckernel-work/m14-blocker-resolution-20261110/account-read-receipt-source-sdk-max-1/candidate/scripts/run_os_goal.py")
SOURCE_SHA256 = "39a03dd8bb33ea943cad02897dee9b6b113187eee30d33ed22a89886b944d870"
SOURCE_BYTES = 155857


def main():
    if len(sys.argv) != 2:
        raise ValueError("Expected one fresh private detail-output path")
    detail_path = Path(sys.argv[1])
    if detail_path.exists() or not detail_path.parent.is_dir():
        raise ValueError("Details must be a new file beneath Root-created private output")
    source = SOURCE.read_bytes()
    if len(source) != SOURCE_BYTES or hashlib.sha256(source).hexdigest() != SOURCE_SHA256:
        raise ValueError("Actual SDK candidate binding changed")
    sys.path.insert(0, "/home/holden/mckernel/scripts")
    spec = importlib.util.spec_from_file_location("receipt_candidate_under_test", SOURCE)
    launcher = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = launcher
    spec.loader.exec_module(launcher)
    FocusedReceiptTests.launcher = launcher
    FocusedReceiptTests.observations = []
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(FocusedReceiptTests)
    methods = sorted(test._testMethodName for test in suite)
    diagnostics, captured_console = io.StringIO(), io.StringIO()
    with redirect_stdout(captured_console):
        result = unittest.TextTestRunner(stream=diagnostics, verbosity=2).run(suite)
    details = {"source_sha256": SOURCE_SHA256,
        "observations": FocusedReceiptTests.observations,
        "private_console": captured_console.getvalue(),
        "unittest_diagnostics": diagnostics.getvalue(),
        "tests_run": result.testsRun, "failures": len(result.failures), "errors": len(result.errors)}
    with detail_path.open("x") as stream:
        json.dump(details, stream, indent=2, sort_keys=True)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    if not result.wasSuccessful():
        sys.stderr.write(diagnostics.getvalue())
        return 1
    print(json.dumps({"status": "PASS_FOCUSED_ACCOUNT_READ_RECEIPT_CONTRACTS",
        "methods": methods, "tests_run": result.testsRun, "failures": 0, "errors": 0,
        "actual_account_or_issuer_effects": 0, "actual_controller_or_native_actions": 0,
        "private_ledger_only": True}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
