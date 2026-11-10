"""Offline handoff provenance regression; only temporary files, no launcher/RPC/workload."""
import copy
import importlib.util
import json
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock
import sys

SOURCE = Path(os.environ.get(
    "OS_GOAL_HANDOFF_SOURCE", Path(__file__).resolve().parents[1] / "os_goal_handoff.py"))
SPEC = importlib.util.spec_from_file_location("handoff_provenance_subject", SOURCE)
handoff = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(handoff)
LAUNCHER_SOURCE = Path(os.environ.get(
    "OS_GOAL_LAUNCHER_SOURCE", Path(__file__).resolve().parents[1] / "run_os_goal.py"))
# Private candidate files may depend on unchanged canonical support modules.
SUPPORT = Path(os.environ.get("OS_GOAL_SUPPORT_SCRIPTS", Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(SUPPORT))
LAUNCHER_SPEC = importlib.util.spec_from_file_location("handoff_provenance_launcher", LAUNCHER_SOURCE)
launcher = importlib.util.module_from_spec(LAUNCHER_SPEC)
LAUNCHER_SPEC.loader.exec_module(launcher)


class HandoffProvenanceTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="handoff-provenance-")
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name)
        self.repo = self.directory / "repo"
        self.repo.mkdir()
        (self.repo / "CAMPAIGN.md").write_text("Sole active functional campaign plan.\n")
        self.current_log = str(self.directory / "current-run")
        self.previous_log = str(self.directory / "previous-run")
        self.old_error = {"message": "Retained HTTP 503 Service Unavailable"}
        self.old_failure = {
            "thread_id": "same-root", "id": "older-turn", "log_dir": self.previous_log,
            "error": {"message": "Retained network disconnect"}, "reason": "server_error"}
        self.state = {
            "thread_id": "same-root", "phase": "stopped", "stop_reason": None,
            "exit_code": 20, "goal": {"status": "blocked", "objective": "same objective"},
            "log_dir": self.current_log, "worker_pid": 421, "worker_start": "1000",
            "server_pid": 422, "server_start": "1001", "cleanup_verified": False,
            "last_error": copy.deepcopy(self.old_error),
            "last_failure": copy.deepcopy(self.old_failure),
            "credit_budget": {"id": "same-ledger", "budget": "100", "spent": "31", "remaining": "69"},
            "billing_hold": {"retained": True, "clear_authorized": False},
            "native_ownership": {"status": "UNKNOWN", "reserved_bytes": 18 * 1024 ** 3},
            "capture_progress": [{"status": "UNKNOWN", "owner": "retained-native-owner"}],
        }

    def record(self):
        before = copy.deepcopy(self.state)
        record = handoff.context_record(self.repo, self.state, remaining_seconds=123.5)
        self.assertEqual(self.state, before, "context creation must not rewrite saved facts")
        self.assertEqual(record["raw_worker_snapshot"], before)
        return record

    def provenance(self, log_dir, error=None):
        return {"error": copy.deepcopy(self.state["last_error"] if error is None else error),
                "log_dir": log_dir, "worker_pid": 421, "worker_start": "1000",
                "server_pid": 422, "server_start": "1001", "thread_id": "same-root"}

    def bare_campaign(self, mode):
        # Never call Campaign.__init__/begin/stop or an RPC factory. The run-except
        # test forces the exception at a mocked begin, before any real launch.
        campaign = object.__new__(launcher.Campaign)
        campaign.directory = self.directory
        campaign.active = {}
        campaign.state = copy.deepcopy(self.state)
        campaign.state["worker_pid"] = os.getpid()
        campaign.state["last_error_provenance"] = self.provenance(self.previous_log)
        if mode == "preserve-none":
            campaign.state["last_error"] = None
        elif mode == "introduce":
            campaign.state.pop("last_error")
            campaign.state.pop("last_error_provenance")
        campaign.log_dir = Path(self.current_log)
        campaign.stop_reason = None if mode == "replace" else "user_requested"
        campaign.stop_now = mode != "replace"
        campaign.controlled = True
        campaign.args = SimpleNamespace(hours=0, grace_seconds=0)
        campaign.credit_guard = None
        campaign.output = Mock()
        campaign.rpc = None
        campaign.goal = copy.deepcopy(self.state["goal"])
        campaign.state_path = self.directory / "not-written-state.json"
        campaign.begin = Mock(side_effect=RuntimeError("current launch exception"))
        campaign.stop = Mock()
        campaign.transport_error_record = Mock(return_value=None)
        campaign.save = Mock(side_effect=lambda **fields: campaign.state.update(fields))
        return campaign

    def check_error_writer(self, campaign, before, mode, new_error):
        if mode in ("preserve", "preserve-none"):
            self.assertEqual(campaign.state["last_error"], before["last_error"])
            self.assertEqual(campaign.state["last_error_provenance"], before["last_error_provenance"])
        else:
            self.assertEqual(campaign.state["last_error"], new_error)
            provenance = campaign.state["last_error_provenance"]
            self.assertEqual(provenance["error"], new_error)
            self.assertEqual(provenance["log_dir"], self.current_log)
            self.assertEqual(provenance["worker_pid"], os.getpid())
            self.assertEqual(provenance["worker_start"], before["worker_start"])
            self.assertTrue(provenance["recorded_at"])
            record = handoff.context_record(self.repo, campaign.state)
            self.assertEqual(record["current_invocation"]["last_error"], new_error)
        self.assertFalse(campaign.state_path.exists())

    def test_blocked_exit20_is_current_stop_not_retained_503_technical_failure(self):
        record = self.record()
        current = record["current_invocation"]
        self.assertEqual(current["log_dir"], self.current_log)
        self.assertEqual(current["goal_status"], "blocked")
        self.assertEqual(current["exit_code"], 20)
        self.assertIsNone(current["stop_reason"])
        self.assertNotIn("last_error", current)
        self.assertNotIn("last_failure", current)
        retained = record["retained_diagnostics"]
        self.assertEqual(retained["last_error"]["value"], self.old_error)
        self.assertEqual(retained["last_error"]["attribution"], "unknown")
        self.assertIsNone(retained["last_error"]["provenance"])
        self.assertEqual(retained["last_failure"]["value"], self.old_failure)
        self.assertEqual(retained["last_failure"]["attribution"], "other_invocation")
        self.assertEqual(record["last_error"], self.old_error)
        self.assertEqual(record["last_failure"], self.old_failure)

    def test_matching_current_error_and_failure_are_visible(self):
        error = {"message": "Current service failure", "codexErrorInfo": "serverOverloaded"}
        self.state.update(phase="stopped", stop_reason="server_error", exit_code=23,
                          last_error=error, last_error_provenance=self.provenance(self.current_log, error))
        failure = {"thread_id": "same-root", "id": "current-turn", "log_dir": self.current_log,
                   "error": error, "reason": "server_error"}
        self.state["last_failure"] = failure
        record = self.record()
        self.assertEqual(record["current_invocation"]["last_error"], error)
        self.assertEqual(record["current_invocation"]["last_failure"], failure)
        self.assertNotIn("last_error", record["retained_diagnostics"])
        self.assertNotIn("last_failure", record["retained_diagnostics"])
        self.assertIn("Current service failure", handoff.render(record))

    def test_equal_error_text_from_different_log_is_not_promoted_to_current(self):
        error = {"message": "identical text across two runs"}
        self.state["last_error"] = error
        self.state["last_error_provenance"] = self.provenance(self.previous_log)
        self.state["last_failure"] = {
            "thread_id": "same-root", "id": "current-turn", "log_dir": self.current_log,
            "error": copy.deepcopy(error), "reason": "server_error"}
        record = self.record()
        self.assertNotIn("last_error", record["current_invocation"])
        self.assertEqual(record["current_invocation"]["last_failure"], self.state["last_failure"])
        self.assertEqual(record["retained_diagnostics"]["last_error"]["value"], error)
        self.assertEqual(record["retained_diagnostics"]["last_error"]["attribution"], "other_invocation")

    def test_current_legacy_failure_does_not_invent_last_error_provenance(self):
        self.state["last_failure"] = {
            "thread_id": "same-root", "id": "current-turn", "log_dir": self.current_log,
            "error": copy.deepcopy(self.old_error), "reason": "server_error"}
        record = self.record()
        self.assertNotIn("last_error", record["current_invocation"])
        self.assertEqual(record["current_invocation"]["last_failure"], self.state["last_failure"])
        self.assertEqual(record["retained_diagnostics"]["last_error"]["attribution"], "unknown")
        self.assertIsNone(record["retained_diagnostics"]["last_error"]["provenance"])

    def test_same_log_with_different_worker_birth_is_not_current(self):
        provenance = self.provenance(self.current_log)
        provenance["worker_start"] = "999"
        self.state["last_error_provenance"] = provenance
        record = self.record()
        self.assertNotIn("last_error", record["current_invocation"])
        self.assertEqual(record["retained_diagnostics"]["last_error"]["value"], self.old_error)
        self.assertEqual(record["retained_diagnostics"]["last_error"]["provenance"], provenance)

    def test_matching_log_cannot_attribute_provenance_bound_to_another_error(self):
        self.state["last_error_provenance"] = self.provenance(
            self.current_log, {"message": "a different saved failure"})
        record = self.record()
        self.assertNotIn("last_error", record["current_invocation"])
        self.assertEqual(record["retained_diagnostics"]["last_error"]["value"], self.old_error)
        self.assertEqual(record["retained_diagnostics"]["last_error"]["attribution"], "unknown")

    def test_healthy_current_state_keeps_old_metadata_unattributed(self):
        self.state.update(phase="working", goal={"status": "active", "objective": "same objective"},
                          exit_code=None, stop_reason=None)
        record = self.record()
        current = record["current_invocation"]
        self.assertEqual((current["phase"], current["goal_status"], current["exit_code"]),
                         ("working", "active", None))
        self.assertNotIn("last_error", current)
        self.assertNotIn("last_failure", current)
        self.assertEqual(record["retained_diagnostics"]["last_error"]["attribution"], "unknown")
        self.assertEqual(record["retained_diagnostics"]["last_failure"]["value"], self.old_failure)

    def test_campaign_only_directions_preserve_configured_window_and_ownership(self):
        record = self.record()
        self.assertEqual(record["source_documents"], [str(self.repo / "CAMPAIGN.md")])
        self.assertEqual(record["remaining_seconds_observed"], 123.5)
        self.assertEqual(record["credit_accounting"], self.state["credit_budget"])
        self.assertFalse(record["release_authorized"])
        self.assertFalse(record["cleanup_verified"])
        raw = record["raw_worker_snapshot"]
        for key in ("goal", "billing_hold", "native_ownership", "capture_progress",
                    "worker_pid", "worker_start", "server_pid", "server_start"):
            self.assertEqual(raw[key], self.state[key])
        text = handoff.render(record)
        self.assertIn("CAMPAIGN.md", text)
        self.assertNotIn("CURRENT.md", text)
        self.assertNotIn("HANDOFF.md", text)
        self.assertNotIn("fixed deadline", text)
        self.assertNotIn("actual fixed window", text)
        self.assertIn("Resolve uncertain submissions", text)
        self.assertIn("native", text)

    def test_event_error_writer_binds_new_values_and_preserves_existing_stop_errors(self):
        for mode in ("replace", "preserve", "preserve-none", "introduce"):
            with self.subTest(mode=mode):
                campaign = self.bare_campaign(mode)
                before = copy.deepcopy(campaign.state)
                new_error = {"message": "current event failure"}
                prior_stop = campaign.stop_reason
                launcher.Campaign.record_failure(
                    campaign, new_error, "server_error", will_retry=True,
                    thread_id="same-root", turn_id="current-turn")
                self.check_error_writer(campaign, before, mode, new_error)
                self.assertEqual(campaign.stop_reason, prior_stop)
                self.assertEqual(campaign.state["last_failure"]["error"], new_error)
                self.assertEqual(campaign.state["last_failure"]["log_dir"], self.current_log)
                self.assertEqual(campaign.state["last_failure"]["worker_pid"], os.getpid())
                campaign.begin.assert_not_called()
                campaign.stop.assert_not_called()

    def test_run_exception_writer_binds_values_without_starting_or_retiring_workers(self):
        for mode in ("replace", "preserve", "preserve-none", "introduce"):
            with self.subTest(mode=mode):
                campaign = self.bare_campaign(mode)
                before = copy.deepcopy(campaign.state)
                result = launcher.Campaign.run(campaign)
                self.assertEqual(result, 1)
                self.check_error_writer(campaign, before, mode, "current launch exception")
                self.assertEqual(campaign.stop_reason, "launcher_error" if mode == "replace" else "user_requested")
                campaign.begin.assert_called_once_with()
                campaign.stop.assert_called_once_with()
                campaign.transport_error_record.assert_called_once()
                self.assertIsNone(campaign.rpc)
                self.assertFalse(campaign.state["cleanup_verified"])

    def test_checkpoint_pause_and_actual_steer_use_only_campaign_directions(self):
        campaign = self.bare_campaign("replace")
        campaign.active = {"same-root": "current-turn"}
        campaign.checkpoint_requested = False
        events = []
        campaign.pause = Mock(side_effect=lambda: events.append("pause"))

        def observe_steer(method, params):
            self.assertTrue(campaign.checkpoint_requested)
            self.assertEqual(campaign.pause.call_count, 1)
            events.append("steer")
            return {}

        campaign.rpc = SimpleNamespace(call=Mock(side_effect=observe_steer))
        launcher.Campaign.request_checkpoint(campaign)
        campaign.pause.assert_called_once_with()
        self.assertEqual(events, ["pause", "steer"])
        campaign.rpc.call.assert_called_once()
        method, params = campaign.rpc.call.call_args.args
        self.assertEqual(method, "turn/steer")
        self.assertEqual(params["threadId"], "same-root")
        self.assertEqual(params["expectedTurnId"], "current-turn")
        self.assertEqual(len(params["input"]), 1)
        self.assertEqual(params["input"][0]["type"], "text")
        text = params["input"][0]["text"]
        self.assertIn("CAMPAIGN.md", text)
        self.assertIn("sole active plan", text)
        self.assertNotIn("CURRENT.md", text)
        self.assertNotIn("HANDOFF.md", text)
        self.assertNotIn("fixed deadline", text)
        self.assertIn("explicitly configured time limit", text)
        self.assertIn("paused future goal continuations", text)
        campaign.begin.assert_not_called()
        campaign.stop.assert_not_called()
        self.assertFalse(campaign.state_path.exists())

    def test_replacement_keeps_old_snapshot_bytes_and_raw_history_immutable(self):
        state_before = copy.deepcopy(self.state)
        current_path = handoff.write_recovery_handoff(
            self.repo, self.directory, self.state, remaining_seconds=123.5)
        archive = self.directory / "recovery"
        first_files = {path.name: path.read_bytes() for path in archive.iterdir()}
        first_json = next(path for path in archive.iterdir() if path.suffix == ".json")
        first_record = json.loads(first_json.read_text())
        self.assertEqual(first_record["raw_worker_snapshot"], state_before)
        self.assertEqual(self.state, state_before)
        self.state.update(phase="working", goal={"status": "active"}, exit_code=None)
        handoff.write_recovery_handoff(self.repo, self.directory, self.state, remaining_seconds=100)
        for name, contents in first_files.items():
            self.assertEqual((archive / name).read_bytes(), contents)
        snapshots = [path for path in archive.iterdir() if path.suffix == ".json"]
        self.assertEqual(len(snapshots), 2)
        self.assertEqual(current_path.stat().st_mode & 0o777, 0o600)
        self.assertIn('"goal_status": "active"', current_path.read_text())
        self.assertFalse(list(self.directory.glob(".recovery-*")))


if __name__ == "__main__":
    unittest.main()

