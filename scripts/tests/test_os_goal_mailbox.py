#!/usr/bin/env python3
"""Offline mailbox contracts: temporary files and mocked GitHub only."""
import copy
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import os_goal_mailbox as mailbox


class MailboxTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="os-goal-mailbox-test-")
        self.addCleanup(self.temp.cleanup)
        self.repo = Path(self.temp.name)
        self.directory = self.repo / "control"
        self.directory.mkdir()
        self.saved = {"thread_id": "saved-root", "phase": "waiting_for_input",
                      "goal": {"status": "blocked"}, "stop_reason": None}
        (self.directory / "state.json").write_text(json.dumps(self.saved))
        self.config = {"repo": "phoenix-hacking/mckernel", "issue_number": 123,
                       "authorized_user_id": 175406809, "authorized_user_login": "phoenix-hacking",
                       "workflow_ref": "development", "poll_seconds": 600}
        self.mailbox = mailbox.Mailbox(self.repo, self.directory, self.config)
        self.clock = [1000.0]
        self.comments, self.dispatches = [], []
        self.context = {"status": "HELD", "missing_input": "Correct supported source binding",
                        "engine_state": {"log_dir": "current-invocation", "thread_id": "saved-root"},
                        "latest_stop": {"log_dir": "current-invocation", "identities": {"thread_id": "saved-root"},
                                        "category": "campaign_blocked", "reason": "source_binding_impasse",
                                        "route": "original_owner", "goal_status": "blocked"}}
        self.time_patch = patch.object(mailbox.time, "time", side_effect=lambda: self.clock[0])
        self.api_patch = patch.object(mailbox, "_gh_api", side_effect=self.api)
        self.time_patch.start()
        self.api_mock = self.api_patch.start()
        self.addCleanup(self.time_patch.stop)
        self.addCleanup(self.api_patch.stop)

    def api(self, endpoint, *, method="GET", payload=None, timeout=10):
        self.assertGreater(timeout, 0)
        self.assertLessEqual(timeout, 10)
        if method == "GET":
            self.assertEqual(endpoint, "repos/phoenix-hacking/mckernel/issues/123/comments?per_page=100&page=1")
            return copy.deepcopy(self.comments)
        self.assertEqual(endpoint, "repos/phoenix-hacking/mckernel/actions/workflows/mckernel-mailbox-notify.yml/dispatches")
        self.assertEqual(method, "POST")
        state = self.state()
        event_id = payload["inputs"]["event_id"]
        self.assertIn(event_id, state["notices"], "Outbox must be durable before dispatch")
        self.assertEqual(state["notices"][event_id]["body"], payload["inputs"]["body"])
        self.assertEqual(set(payload["inputs"]), {"event_id", "body"})
        self.assertEqual(payload["ref"], "development")
        self.assertEqual(len(event_id), 64)
        self.assertLessEqual(len(payload["inputs"]["body"].encode()), 6000)
        self.dispatches.append(copy.deepcopy(payload))
        return None

    def state(self):
        return json.loads((self.directory / mailbox.STATE_FILE).read_text())

    def advance(self, seconds=600):
        self.clock[0] += seconds

    def comment(self, ident=10, body="/mckernel-instruct\nFix the source-fetch path.", **changes):
        result = {"id": ident, "body": body, "created_at": "2026-11-10T03:00:00Z",
                  "updated_at": "2026-11-10T03:00:00Z",
                  "user": {"id": 175406809, "login": "phoenix-hacking", "type": "User"}}
        result.update(changes)
        return result

    def pending(self):
        return list((self.directory / "instructions/pending").glob("*.json"))

    def test_one_notice_per_material_blocker_ignores_heartbeat_and_identity_churn(self):
        first = self.mailbox.poll(self.context)
        self.assertEqual(first["status"], "POLLED")
        self.assertTrue(first["notice_requested"])
        self.assertFalse(first["observed_notice"])
        self.assertNotIn("email_delivered", first)
        self.comments = [self.comment(20, mailbox.MARKER.format(event_id=first["notice_event_id"]),
                                     user={"id": 41898282, "login": "github-actions[bot]", "type": "Bot"})]
        self.advance()
        changed = copy.deepcopy(self.context)
        changed.update(heartbeat_at="later", worker_pid=999, updated_at="new")
        changed["latest_stop"].update(record_id="another", recorded_at="later", invocation="new")
        self.mailbox.poll(changed)
        self.assertEqual(len(self.dispatches), 1)
        changed["missing_input"] = "A newly identified supported SDK mapping"
        self.advance()
        second = self.mailbox.poll(changed)
        self.assertEqual(len(self.dispatches), 2)
        self.assertNotEqual(first["notice_event_id"], second["notice_event_id"])

    def test_active_context_does_not_report_historical_stop_as_current(self):
        context = dict(self.context, status="ACTIVE")
        self.mailbox.poll(context)
        self.assertEqual(self.dispatches, [])

    def test_guardian_nested_engine_context_reports_waiting_and_suppresses_old_stop(self):
        (self.directory / "latest-stop.json").write_text(json.dumps(self.context["latest_stop"]))
        active = {"phase": "SUPERVISED", "reason": None,
                  "engine_state": {"phase": "running", "goal": {"status": "active"}}}
        self.mailbox.poll(active)
        self.assertEqual(self.dispatches, [])
        self.advance()
        waiting = {"phase": "SUPERVISED", "reason": None,
                   "engine_state": {"phase": "waiting_for_input", "goal": {"status": "blocked"}}}
        self.mailbox.poll(waiting)
        self.assertEqual(len(self.dispatches), 1)
        self.advance()
        held = {"phase": "HELD", "reason": "supervisor_and_worker_outcomes_unreconciled", "engine_state": {}}
        self.mailbox.poll(held)
        self.assertEqual(len(self.dispatches), 2)
        self.assertIn("supervisor_and_worker_outcomes_unreconciled", self.dispatches[-1]["inputs"]["body"])

    def test_old_policy_stop_cannot_supply_current_source_blocker_or_override_empty_context(self):
        old = {"event": "guardian_held", "category": "policy_rejection", "reason": "old_server_error",
               "log_dir": "old-invocation", "identities": {"thread_id": "saved-root"},
               "error": {"code": "cyberPolicy", "message": "old policy rejection"},
               "remedy": "Old supported-review remedy", "route": "supported_review"}
        (self.directory / "latest-stop.json").write_text(json.dumps(old))
        current = {"phase": "HELD", "reason": "new_source_binding_impasse",
                   "missing_input": "Actual current supported source is missing",
                   "engine_state": {"log_dir": "current-invocation", "thread_id": "saved-root", "goal": {"status": "blocked"}}}
        for explicit in (False, True):
            with self.subTest(explicit_empty_stop=explicit):
                context = dict(current, latest_stop={}) if explicit else current
                material, body = self.mailbox._blocker(context)
                self.assertEqual(material["reason"], "new_source_binding_impasse")
                self.assertEqual(material["missing_input"], "Actual current supported source is missing")
                self.assertEqual(material["category"], "")
                self.assertEqual(material["error_code"], "")
                self.assertEqual(material["next_action"], "")
                self.assertEqual(material["route"], "")
                self.assertNotIn("cyberPolicy", body)
                self.assertNotIn("old policy rejection", body)
        # Explicit {} must also suppress an otherwise attributable on-disk stop.
        old.update(log_dir="current-invocation")
        (self.directory / "latest-stop.json").write_text(json.dumps(old))
        material, _ = self.mailbox._blocker(dict(current, latest_stop={}))
        self.assertEqual(material["error_code"], "")

    def test_only_bound_invocation_or_matching_current_guardian_hold_supplies_stop_details(self):
        stop = {"log_dir": "current-invocation", "identities": {"worker_pid": "42", "worker_start": "123"},
                "category": "permission_denied", "reason": "permission_denied",
                "error": {"code": "EACCES", "message": "actual current permission denied"}, "remedy": "Contact access owner"}
        state = {"log_dir": "current-invocation", "worker_pid": 42, "worker_start": "123"}
        context = {"phase": "HELD", "reason": "permission_denied", "engine_state": state, "latest_stop": stop}
        self.assertEqual(self.mailbox._blocker(context)[0]["error_code"], "EACCES")
        context["engine_state"] = dict(state, worker_start="other")
        self.assertEqual(self.mailbox._blocker(context)[0]["error_code"], "")
        stop.update(event="guardian_held", reason="engine_metadata_unreadable")
        context.update(reason="engine_metadata_unreadable", engine_state={})
        self.assertEqual(self.mailbox._blocker(context)[0]["error_code"], "EACCES")
        context["reason"] = "different_current_hold"
        self.assertEqual(self.mailbox._blocker(context)[0]["error_code"], "")

    def test_observed_bot_notice_is_distinct_from_requested(self):
        result = self.mailbox.poll(self.context)
        self.comments = [self.comment(20, mailbox.MARKER.format(event_id=result["notice_event_id"]),
                                     user={"id": 41898282, "login": "github-actions[bot]", "type": "Bot"})]
        self.advance()
        observed = self.mailbox.poll(self.context)
        self.assertTrue(observed["observed_notice"])
        self.advance(700)
        self.mailbox.poll(self.context)
        self.assertEqual(len(self.dispatches), 1)

    def test_unobserved_requested_notice_can_redispatch_same_event_after_timeout(self):
        first = self.mailbox.poll(self.context)
        self.advance(600)
        self.mailbox.poll(self.context)
        self.assertEqual(len(self.dispatches), 2)
        self.assertEqual(self.dispatches[0]["inputs"]["event_id"], first["notice_event_id"])
        self.assertEqual(self.dispatches[0], self.dispatches[1])

    def test_unknown_dispatch_retries_same_durable_event_after_backoff(self):
        normal = self.api
        def lost_reply(endpoint, **kwargs):
            if kwargs.get("method") == "POST":
                normal(endpoint, **kwargs)
                raise subprocess.TimeoutExpired(["gh", "api"], 10)
            return normal(endpoint, **kwargs)
        self.api_mock.side_effect = lost_reply
        result = self.mailbox.poll(self.context)
        self.assertEqual(result["status"], "ERROR")
        self.assertFalse(result["notice_requested"])
        self.assertEqual(len(self.dispatches), 1)
        self.assertEqual(self.mailbox.poll(self.context)["status"], "BACKOFF")
        self.assertEqual(len(self.dispatches), 1)
        self.advance()
        self.api_mock.side_effect = normal
        recovered = self.mailbox.poll(self.context)
        self.assertTrue(recovered["notice_requested"])
        self.assertEqual(self.dispatches[0], self.dispatches[1])

    def test_reports_are_redacted_bounded_and_do_not_mention_unrequested_people(self):
        context = copy.deepcopy(self.context)
        context["missing_input"] = "@outsider " + "😀" * 2000
        context["latest_stop"]["error"] = {"code": "build_failed", "message":
            "password='hunter2' token=abc123 https://alice:secret@example.test/path " + "😀" * 2000}
        self.mailbox.poll(context)
        body = self.dispatches[0]["inputs"]["body"]
        for secret in ("hunter2", "abc123", "alice:secret", "@outsider"):
            self.assertNotIn(secret, body)
        self.assertLessEqual(len(body.encode()), 6000)

    def test_only_exact_verified_human_first_line_instruction_is_queued(self):
        self.comments = [
            self.comment(1, user={"id": 7, "login": "phoenix-hacking", "type": "User"}),
            self.comment(2, user={"id": "175406809", "login": "phoenix-hacking", "type": "User"}),
            self.comment(3, user={"id": 175406809, "login": "phoenix-hacking", "type": "Bot"}),
            self.comment(4, user={"id": 175406809, "login": "other-user", "type": "User"}),
            self.comment(5, "Status from our authenticated account.\n/mckernel-instruct\nNot a reply."),
            self.comment(6, updated_at="2026-11-10T03:01:00Z"),
            self.comment(7, "/mckernel-instruct\n"),
            self.comment(8, "/mckernel-instruct\nFix the actual build error; retain holds."),
        ]
        result = self.mailbox.poll(self.context)
        self.assertEqual(len(result["queued_instruction_ids"]), 1)
        self.assertNotIn("resume_request_id", result)
        self.assertEqual(len(self.pending()), 1)
        text = json.loads(self.pending()[0].read_text())["text"]
        self.assertIn("#issuecomment-8", text)
        self.assertIn("Fix the actual build error", text)
        self.assertEqual(len(self.dispatches), 1)
        self.assertIn("📥 RECEIVED", self.dispatches[0]["inputs"]["body"])
        self.assertTrue(all(n.get("kind") == "received" for n in self.state()["notices"].values()))
        self.assertEqual(self.state()["messages"]["5"]["delivery_status"], "NOT_QUEUED")

    def test_replayed_or_edited_comment_never_enqueues_again(self):
        self.comments = [self.comment()]
        first = self.mailbox.poll(self.context)
        self.advance()
        self.comments[0].update(body="/mckernel-resume\nEdited instruction", updated_at="later")
        second = self.mailbox.poll(self.context)
        self.assertEqual(second["queued_instruction_ids"], [])
        self.assertNotIn("resume_request_id", second)
        self.assertEqual(len(self.pending()), 1)
        self.assertEqual(len(first["queued_instruction_ids"]), 1)

    def test_reply_epoch_allows_one_new_report_if_blocker_persists(self):
        first = self.mailbox.poll(self.context)
        self.comments = [self.comment()]
        self.advance()
        self.mailbox.poll(self.context)
        self.assertEqual(len(self.dispatches), 2)
        self.assertIn("📥 RECEIVED", self.dispatches[-1]["inputs"]["body"])
        self.advance()
        self.mailbox.poll(self.context)
        self.assertEqual(len(self.dispatches), 3)
        self.assertNotEqual(first["notice_event_id"], self.dispatches[-1]["inputs"]["event_id"])

    def test_resume_is_returned_only_after_durable_queue_and_until_ack(self):
        self.comments = [self.comment(body="/mckernel-resume")]
        result = self.mailbox.poll(self.context)
        request_id = result["resume_request_id"]
        self.assertTrue((self.directory / "instructions/pending" / (request_id + ".json")).is_file())
        self.assertEqual(result["resume_comment_id"], 10)
        self.assertEqual(self.mailbox.poll(self.context)["resume_request_id"], request_id)
        self.mailbox.ack_resume(request_id)
        self.assertNotIn("resume_request_id", self.mailbox.poll(self.context))
        self.assertEqual(len(self.pending()), 1)

    def test_resume_never_changes_policy_or_permission_holds_or_goal(self):
        held = dict(self.saved, stop_reason="server_error", policy_hold=True,
                    last_error={"codexErrorInfo": "cyberPolicy"})
        path = self.directory / "state.json"
        path.write_text(json.dumps(held))
        before = path.read_bytes()
        self.comments = [self.comment(body="/mckernel-resume\nContinue eligible work.")]
        result = self.mailbox.poll(dict(self.context, state=held))
        self.assertIn("resume_request_id", result)
        self.assertEqual(path.read_bytes(), before)

    def test_crash_after_queue_recovers_exact_instruction_once_and_retains_resume(self):
        self.comments = [self.comment(body="/mckernel-resume\nUse the corrected source.")]
        original = mailbox.queue_instruction
        def crash_after_queue(*args, **kwargs):
            original(*args, **kwargs)
            raise SystemExit("simulated process crash after durable queue")
        with patch.object(mailbox, "queue_instruction", side_effect=crash_after_queue):
            with self.assertRaises(SystemExit):
                self.mailbox.poll(self.context)
        self.assertIn("enqueue_intent", self.state())
        self.assertEqual(len(self.pending()), 1)
        # Recovery uses the immutable accepted snapshot, even if the comment was edited or deleted.
        self.comments = []
        recovered = mailbox.Mailbox(self.repo, self.directory, self.config).poll(self.context)
        self.assertIn("resume_request_id", recovered)
        self.assertEqual(len(self.pending()), 1)
        self.assertNotIn("enqueue_intent", self.state())
        self.assertEqual(self.state()["reply_epoch"], 1)

    def test_resume_server_timestamp_survives_queue_crash_deleted_comment_and_late_poll(self):
        created = "2026-11-10T03:00:00Z"
        expected = datetime(2026, 11, 10, 3, tzinfo=timezone.utc).timestamp()
        self.comments = [self.comment(body="/mckernel-resume", created_at=created, updated_at=created)]
        original = mailbox.queue_instruction
        def crash_after_queue(*args, **kwargs):
            original(*args, **kwargs)
            raise SystemExit("crash after durable queue")
        with patch.object(mailbox, "queue_instruction", side_effect=crash_after_queue):
            with self.assertRaises(SystemExit):
                self.mailbox.poll(self.context)
        self.assertEqual(self.state()["enqueue_intent"]["resume_created_at"], expected)
        self.clock[0] = expected + 3600
        self.comments = []
        recovered = mailbox.Mailbox(self.repo, self.directory, self.config).poll(self.context)
        self.assertEqual(recovered["resume_created_at"], expected)
        self.assertLess(recovered["resume_created_at"], self.clock[0])
        self.assertEqual(self.state()["pending_resumes"][0]["resume_created_at"], expected)
        self.assertEqual(len(self.pending()), 1)

    def test_queue_failure_never_returns_manual_resume_authorization(self):
        self.comments = [self.comment(body="/mckernel-resume")]
        with patch.object(mailbox, "queue_instruction", side_effect=OSError("disk unavailable")):
            result = self.mailbox.poll(self.context)
        self.assertEqual(result["status"], "ERROR")
        self.assertNotIn("resume_request_id", result)
        self.assertIn("enqueue_intent", self.state())
        self.assertEqual(self.pending(), [])

    def test_oversized_reply_is_rejected_without_blocking_a_later_valid_comment(self):
        self.comments = [self.comment(10, "/mckernel-instruct\n" + "x" * 8192), self.comment(11)]
        result = self.mailbox.poll(self.context)
        self.assertEqual(len(result["queued_instruction_ids"]), 1)
        self.assertEqual(self.state()["rejected_comment"]["comment_id"], 10)
        self.assertEqual(self.state()["last_seen_comment_id"], 11)

    def test_comments_are_paginated_and_only_exact_pr_endpoint_is_read(self):
        pages = []
        def api(endpoint, **kwargs):
            if kwargs.get("method") == "POST":
                return self.api(endpoint, **kwargs)
            pages.append(endpoint)
            if endpoint.endswith("page=1"):
                return [self.comment(n, "No instruction marker") for n in range(1, 101)]
            if endpoint.endswith("page=2"):
                return [self.comment(101)]
            raise AssertionError(endpoint)
        self.api_mock.side_effect = api
        result = self.mailbox.poll(self.context)
        self.assertEqual(len(pages), 2)
        self.assertTrue(all("/issues/123/comments?" in p for p in pages))
        self.assertEqual(len(result["queued_instruction_ids"]), 1)

    def test_malformed_network_response_has_backoff_and_no_instruction(self):
        self.api_mock.return_value = None
        self.api_mock.side_effect = None
        result = self.mailbox.poll(self.context)
        self.assertEqual(result["status"], "ERROR")
        self.assertEqual(self.pending(), [])
        calls = self.api_mock.call_count
        self.assertEqual(self.mailbox.poll(self.context)["status"], "BACKOFF")
        self.assertEqual(self.api_mock.call_count, calls)

    def test_poll_attempt_and_success_times_distinguish_failure_and_backoff(self):
        self.mailbox.poll(self.context)
        self.assertEqual(self.state()["last_poll_at"], 1000)
        self.assertEqual(self.state()["last_successful_poll_at"], 1000)
        self.advance()
        self.api_mock.side_effect = RuntimeError("GitHub authentication unavailable")
        failed = self.mailbox.poll(self.context)
        self.assertEqual(failed["status"], "ERROR")
        self.assertEqual(self.state()["last_poll_at"], 1600)
        self.assertEqual(self.state()["last_successful_poll_at"], 1000)
        self.assertIn("authentication", self.state()["last_error"])
        before = self.state()
        self.advance(10)
        self.assertEqual(self.mailbox.poll(self.context)["status"], "BACKOFF")
        self.assertEqual(self.state(), before)
        self.advance(590)
        self.api_mock.side_effect = self.api
        self.mailbox.poll(self.context)
        self.assertEqual(self.state()["last_poll_at"], 2200)
        self.assertEqual(self.state()["last_successful_poll_at"], 2200)
        self.assertIsNone(self.state()["last_error"])

    def write_delivery(self, request_id, **changes):
        receipt = {"id": request_id, "status": "accepted_by_server", "thread_id": "saved-root",
                   "turn_id": "accepted-turn", "delivered_at": "2026-11-10T03:10:00Z"}
        receipt.update(changes)
        directory = self.directory / "instructions/delivered"
        directory.mkdir(parents=True, exist_ok=True)
        (directory / (request_id + ".json")).write_text(json.dumps(receipt))

    def test_ten_minute_reads_allow_one_prompt_receipt_post_each_monitor_tick(self):
        self.comments = [self.comment(10), self.comment(11)]
        first = self.mailbox.poll(self.context)
        self.assertEqual(first["next_poll_at"], 1600)
        self.assertEqual(len(self.dispatches), 1)
        get_calls = lambda: sum(c.kwargs.get("method", "GET") == "GET" for c in self.api_mock.call_args_list)
        self.assertEqual(get_calls(), 1)
        self.assertEqual(len(self.pending()), 2)
        for ident in first["queued_instruction_ids"]:
            self.write_delivery(ident)
        self.advance(10)
        second = self.mailbox.poll(self.context)
        self.assertEqual(second["status"], "BACKOFF")
        self.assertEqual(get_calls(), 1)
        self.assertEqual(len(self.dispatches), 2)
        self.assertTrue(all("📥 RECEIVED — phone" in p["inputs"]["body"] for p in self.dispatches))
        self.advance(10)
        self.mailbox.poll(self.context)
        self.assertEqual(get_calls(), 1)
        self.assertEqual(len(self.dispatches), 2, "Submitted receipts are not yet observed in GitHub")
        for number, message in enumerate(self.state()["messages"].values(), 20):
            self.comments.append(self.comment(number, mailbox.MARKER.format(event_id=message["received_event_id"]),
                user={"id": 41898282, "login": "github-actions[bot]", "type": "Bot"}))
        self.advance(580)
        self.mailbox.poll(self.context)
        self.assertEqual(get_calls(), 2)
        self.assertEqual(len(self.dispatches), 3)
        self.assertIn("✅ RECEIVED BY CONTROLLER", self.dispatches[-1]["inputs"]["body"])
        self.advance(10)
        self.mailbox.poll(self.context)
        self.assertEqual(get_calls(), 2)
        self.assertEqual(len(self.dispatches), 4)
        self.assertEqual(len({p["inputs"]["event_id"] for p in self.dispatches}), 4)
        self.assertTrue(all(m["delivery_status"] == "ACCEPTED" for m in self.state()["messages"].values()))

    def test_queue_and_ambiguous_delivery_records_keep_visible_waiting(self):
        self.comments = [self.comment()]
        first = self.mailbox.poll(self.context)
        request_id = first["queued_instruction_ids"][0]
        body = self.dispatches[0]["inputs"]["body"]
        self.assertIn("📥 RECEIVED", body)
        self.assertIn("⏳ WAITING for controller acceptance", body)
        self.assertIn("2026-11-10T03:00:00Z", body)
        self.assertIn("1970-01-01T00:16:40Z", body)
        self.assertIn(request_id, body)
        for changes in ({"id": "unrelated"}, {"status": "delivery_uncertain"},
                        {"turn_id": ""}, {"delivered_at": "not-a-time"}, {"delivered_at": "2026-11-10T03:10:00"}):
            with self.subTest(changes=changes):
                self.write_delivery(request_id, **changes)
                self.advance(10)
                self.mailbox.poll(self.context)
                self.assertEqual(self.state()["messages"]["10"]["delivery_status"], "WAITING")
                self.assertEqual(len(self.dispatches), 1)
        self.write_delivery(request_id)
        sending = self.directory / "instructions/sending"
        sending.mkdir()
        (sending / (request_id + ".json")).write_text("{}")
        self.advance(10)
        self.mailbox.poll(self.context)
        message = self.state()["messages"]["10"]
        self.assertEqual(message["delivery_status"], "ACCEPTED")
        self.assertEqual(message["controller_accepted_at"], "2026-11-10T03:10:00Z")
        self.assertEqual(len(self.dispatches), 1, "Accepted post must wait for observed received post")
        self.comments.append(self.comment(20, mailbox.MARKER.format(event_id=message["received_event_id"]),
            user={"id": 41898282, "login": "github-actions[bot]", "type": "Bot"}))
        self.advance(540)
        self.mailbox.poll(dict(self.context, status="ACTIVE"))
        self.assertIn("⏳ WAITING for the work result", self.dispatches[-1]["inputs"]["body"])
        self.assertEqual(len(self.pending()), 1, "Delivery observation must never replay the instruction")

    def test_unknown_received_post_blocks_acceptance_until_received_is_observed(self):
        self.comments = [self.comment()]
        normal = self.api
        def lost_reply(endpoint, **kwargs):
            if kwargs.get("method") == "POST":
                normal(endpoint, **kwargs)
                raise subprocess.TimeoutExpired(["gh", "api"], 10)
            return normal(endpoint, **kwargs)
        self.api_mock.side_effect = lost_reply
        first = self.mailbox.poll(self.context)
        self.assertEqual(first["status"], "ERROR")
        request_id = first["queued_instruction_ids"][0]
        self.write_delivery(request_id)
        self.advance(10)
        self.api_mock.side_effect = normal
        context = dict(self.context, status="ACTIVE")
        self.mailbox.poll(context)
        self.assertEqual(len(self.dispatches), 1)
        self.assertEqual(self.state()["messages"]["10"]["delivery_status"], "ACCEPTED")
        self.advance(590)
        self.mailbox.poll(context)
        self.assertEqual(len(self.dispatches), 2)
        self.assertEqual(self.dispatches[0], self.dispatches[1])
        self.advance(10)
        self.mailbox.poll(context)
        self.assertEqual(len(self.dispatches), 2, "Dispatch acknowledgement alone does not prove a GitHub post")
        message = self.state()["messages"]["10"]
        self.comments.append(self.comment(20, mailbox.MARKER.format(event_id=message["received_event_id"]),
            user={"id": 41898282, "login": "github-actions[bot]", "type": "Bot"}))
        self.advance(590)
        self.mailbox.poll(context)
        self.assertEqual(len(self.dispatches), 3)
        self.assertIn("✅ RECEIVED BY CONTROLLER", self.dispatches[-1]["inputs"]["body"])

    def test_pending_blocker_is_superseded_by_healthy_backoff_without_extra_get_or_post(self):
        self.comments = [self.comment(body="Hello from my phone")]
        self.mailbox.poll(dict(self.context, status="ACTIVE"))
        self.advance()
        self.mailbox.poll(self.context)
        blockers = [n for n in self.state()["notices"].values() if n.get("kind") == "blocker"]
        self.assertEqual(len(blockers), 1)
        self.assertFalse(blockers[0]["requested"], "A receipt retry used this tick's one POST")
        calls = len(self.api_mock.call_args_list)
        posted = len(self.dispatches)
        self.advance(10)
        result = self.mailbox.poll(dict(self.context, status="ACTIVE"))
        self.assertEqual(result["status"], "BACKOFF")
        self.assertIsNone(result["notice_event_id"])
        self.assertEqual(len(self.api_mock.call_args_list), calls)
        self.assertEqual(len(self.dispatches), posted)
        self.assertTrue(self.state()["notices"][blockers[0]["event_id"]]["superseded"])
        self.advance(10)
        self.mailbox.poll(dict(self.context, missing_input="A different real prerequisite"))
        self.assertEqual(len(self.api_mock.call_args_list), calls)
        self.assertEqual(sum(n.get("kind") == "blocker" for n in self.state()["notices"].values()), 1,
                         "Changed local blocker invalidates old work but creates no event before normal poll")

    def test_owner_plain_comment_gets_received_help_once_without_queue_or_resume(self):
        self.comments = [self.comment(body="Please fix the problem from my phone.")]
        result = self.mailbox.poll(self.context)
        self.assertEqual(result["queued_instruction_ids"], [])
        self.assertNotIn("resume_request_id", result)
        self.assertEqual(self.pending(), [])
        message = self.state()["messages"]["10"]
        self.assertFalse(message["command_recognized"])
        self.assertEqual(message["delivery_status"], "NOT_QUEUED")
        self.assertIn("📥 RECEIVED", self.dispatches[0]["inputs"]["body"])
        self.assertIn("⏳ WAITING", self.dispatches[0]["inputs"]["body"])
        self.assertIn("NOT QUEUED", self.dispatches[0]["inputs"]["body"])
        event_id = message["received_event_id"]
        self.comments += [self.comment(20, mailbox.MARKER.format(event_id=event_id),
                                      user={"id": 41898282, "login": "github-actions[bot]", "type": "Bot"})]
        self.advance()
        self.mailbox.poll(dict(self.context, status="ACTIVE"))
        self.assertEqual(len(self.dispatches), 1)
        notice = self.state()["notices"][event_id]
        self.assertEqual(notice["observed_comment_id"], 20)
        self.assertEqual(notice["observed_sent_at"], "2026-11-10T03:00:00Z")
        self.assertIn("observed_at", notice)
        self.assertNotIn("email_delivered", notice)

    def test_receipt_timestamps_survive_crash_before_queue_return(self):
        self.comments = [self.comment()]
        original = mailbox.queue_instruction
        def crash_after_queue(*args, **kwargs):
            original(*args, **kwargs)
            raise SystemExit("simulated crash")
        with patch.object(mailbox, "queue_instruction", side_effect=crash_after_queue):
            with self.assertRaises(SystemExit):
                self.mailbox.poll(self.context)
        self.comments = []
        self.advance(3600)
        self.mailbox.poll(self.context)
        message = self.state()["messages"]["10"]
        self.assertEqual(message["source_created_at"], "2026-11-10T03:00:00Z")
        self.assertEqual(message["received_at"], "1970-01-01T00:16:40Z")
        self.assertEqual(len(self.pending()), 1)
        self.assertEqual(len(self.dispatches), 1)
        self.assertIn("1970-01-01T00:16:40Z", self.dispatches[0]["inputs"]["body"])

    def test_outgoing_blocker_has_sent_and_waiting_signs_and_default_interval_is_600(self):
        config = dict(self.config)
        config.pop("poll_seconds")
        self.assertEqual(mailbox.Mailbox(self.repo, self.directory, config).poll_seconds, 600)
        self.mailbox.poll(self.context)
        body = self.dispatches[0]["inputs"]["body"]
        self.assertIn("📤 SENT — computer → phone", body)
        self.assertIn("⏳ WAITING FOR YOUR REPLY", body)
        self.assertNotIn("human received", body)
        self.assertNotIn("email delivered", body)

    def test_config_binding_change_does_not_reuse_old_receipts(self):
        self.mailbox.poll(self.context)
        changed = dict(self.config, issue_number=124)
        with self.assertRaises(ValueError):
            mailbox.Mailbox(self.repo, self.directory, changed).poll(self.context)

    def test_plain_reply_never_executes_shell_syntax(self):
        text = "$(touch /tmp/mailbox-should-never-execute); `id`; rm -rf /example"
        self.comments = [self.comment(body="/mckernel-instruct\n" + text)]
        with patch.object(mailbox.subprocess, "run", side_effect=AssertionError("No shell/process")):
            result = self.mailbox.poll(self.context)
        self.assertEqual(len(result["queued_instruction_ids"]), 1)
        self.assertIn(text, json.loads(self.pending()[0].read_text())["text"])


class TransportTests(unittest.TestCase):
    def test_gh_api_uses_supported_auth_stdin_and_bounded_no_shell_request(self):
        completed = Mock(returncode=0, stdout="", stderr="")
        payload = {"ref": "development", "inputs": {"body": "literal $(echo no-shell)"}}
        with patch.object(mailbox.shutil, "which", return_value="/fake/gh"), \
                patch.object(mailbox.subprocess, "run", return_value=completed) as run:
            self.assertIsNone(mailbox._gh_api("repos/o/r/actions/workflows/w.yml/dispatches", method="POST", payload=payload))
        command = run.call_args.args[0]
        self.assertEqual(command, ["/fake/gh", "api", "--method", "POST", "repos/o/r/actions/workflows/w.yml/dispatches", "--input", "-"])
        self.assertEqual(json.loads(run.call_args.kwargs["input"]), payload)
        self.assertLessEqual(run.call_args.kwargs["timeout"], 10)
        self.assertFalse(run.call_args.kwargs.get("shell", False))
        self.assertNotIn("token", " ".join(command))

    def test_transport_failure_does_not_expose_cli_output_credentials(self):
        completed = Mock(returncode=1, stdout="token=secret-value", stderr="password=another-secret")
        with patch.object(mailbox.shutil, "which", return_value="/fake/gh"), \
                patch.object(mailbox.subprocess, "run", return_value=completed):
            with self.assertRaises(RuntimeError) as error:
                mailbox._gh_api("repos/o/r/issues/1/comments")
        self.assertNotIn("secret", str(error.exception))


if __name__ == "__main__":
    unittest.main()
