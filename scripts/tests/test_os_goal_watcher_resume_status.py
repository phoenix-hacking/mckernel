"""Display-only retained dispatch status; fake watcher, no model/native work."""
from copy import deepcopy
import signal
import unittest
from unittest.mock import patch

from scripts.tests import test_os_goal_watcher_retention as fixtures


class RetainedDispatchLabelTests(unittest.TestCase):
    def setUp(self):
        self.current = {"worker_pid": 101, "worker_start": "1000", "server_pid": 102,
                        "server_start": "1001", "thread_id": "same-saved-root",
                        "log_dir": "/temporary/original-invocation", "phase": "running",
                        "goal": {"threadId": "same-saved-root", "status": "active"},
                        "controller_dispatch_enabled": True, "stop_reason": None,
                        "stop_now": False, "checkpoint_requested": False}
        self.owner = fixtures.custody.current_owner_identity(self.current,
            worker_pid=self.current["worker_pid"], worker_start=self.current["worker_start"])

    def label(self, current=None, owner=None):
        return fixtures.watcher.retained_dispatch_label(
            self.current if current is None else current, self.owner if owner is None else owner)

    def test_exact_resumed_owner_reports_active_without_mutating_custody_or_state(self):
        self.current["owner_retention"] = {"custody": "UNKNOWN", "release_authorized": False}
        before = deepcopy((self.current, self.owner))
        self.assertEqual(self.label(), "DISPATCH ACTIVE; runtime custody retained")
        self.assertEqual((self.current, self.owner), before)

    def test_paused_stopped_and_unknown_dispatch_states_keep_stopped_label(self):
        variants = ({"phase": "owner_retained"}, {"goal": {"status": "paused"}},
                    {"goal": {"status": "blocked"}}, {"goal": {"status": "complete"}},
                    {"controller_dispatch_enabled": False}, {"controller_dispatch_enabled": 1},
                    {"controller_dispatch_enabled": None}, {"stop_reason": "signal_15"},
                    {"stop_reason": "credit_budget_exhausted"}, {"stop_now": True},
                    {"stop_now": None}, {"checkpoint_requested": True},
                    {"checkpoint_requested": None}, {"goal": None}, {"goal": []},
                    {"goal": {"threadId": "foreign-root", "status": "active"}})
        for change in variants:
            with self.subTest(change=change):
                self.assertEqual(self.label(dict(self.current, **change)),
                                 "DISPATCH STOPPED; runtime custody retained")

    def test_foreign_or_incomplete_identity_never_reports_active(self):
        for field in fixtures.custody.IDENTITY_FIELDS:
            missing = dict(self.current)
            missing.pop(field)
            changed = dict(self.current, **{field: {"worker_pid": 103, "server_pid": 104}.get(field, "foreign")})
            for current in (missing, changed):
                with self.subTest(field=field, current=current):
                    self.assertEqual(self.label(current), "DISPATCH STOPPED; runtime custody retained")
        for current, owner in (({}, self.owner), (None, self.owner), (self.current, None),
                               (self.current, {}), (self.current, dict(self.owner, thread_id=None))):
            with self.subTest(current=current, owner=owner):
                self.assertEqual(fixtures.watcher.retained_dispatch_label(current, owner),
                                 "DISPATCH STOPPED; runtime custody retained")


class RetainedWatcherDisplayTests(unittest.TestCase):
    def test_resumed_label_does_not_clear_latch_or_enable_deadline_recovery(self):
        fixture = fixtures.WatcherRetentionTests(methodName="runTest")
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        fixture.args.hours = 0.0001
        fixture.args.watchdog_seconds = 0.1
        fixture.args.stall_seconds = 0.1
        fixture.state.update(goal={"status": "paused"}, controller_dispatch_enabled=False,
                             stop_reason="closure_decision_unresolved", stop_now=False,
                             checkpoint_requested=True)
        fixture.retain()
        original_retention = deepcopy(fixture.state["owner_retention"])

        def advance(clock):
            if clock.sleeps == 1:
                fixture.state.update(phase="running", goal={"status": "active"},
                    controller_dispatch_enabled=True, stop_reason=None, stop_now=False,
                    checkpoint_requested=False)
                fixture.write_json(fixture.state_path, fixture.state)
            if clock.sleeps == 2:
                fixture.handlers[signal.SIGTERM](signal.SIGTERM, None)
                clock.now += 1000
            if clock.sleeps == 3:
                fixture.state.update(phase="owner_retained", goal={"status": "paused"},
                                     controller_dispatch_enabled=False)
                fixture.write_json(fixture.state_path, fixture.state)
            if clock.sleeps == 4:
                fixture.worker.returncode = 1

        fixture.clock.step = advance
        with patch.object(fixtures.watcher, "print", create=True) as output:
            self.assertEqual(fixture.run_watcher(), 1)
        fixture.assert_original_owner_untouched()
        self.assertEqual(fixture.worker.signals, [])
        fixture.diagnostics.assert_not_called()
        lines = [call.args[0] for call in output.call_args_list]
        self.assertTrue(any(line.startswith("[os-watch] DISPATCH ACTIVE; runtime custody retained;")
                            for line in lines))
        self.assertTrue(any(line.startswith("[os-watch] DISPATCH STOPPED; runtime custody retained;")
                            for line in lines))
        self.assertEqual(fixture.state["owner_retention"], original_retention)
        events = fixture.events()
        self.assertEqual(sum(row["event"] == "owner_retained" for row in events), 1)
        self.assertTrue(events[-1]["recovery_held"])
        self.assertEqual(events[-1]["custody"], "UNKNOWN")
        self.assertFalse(events[-1]["server_retirement_attempted"])
        self.assertFalse(events[-1]["native_release_authorized"])


if __name__ == "__main__":
    unittest.main()
