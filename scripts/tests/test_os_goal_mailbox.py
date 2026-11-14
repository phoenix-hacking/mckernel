#!/usr/bin/env python3
"""Offline mailbox contracts: temporary files and mocked GitHub only."""
import copy
from datetime import datetime, timezone
import json
import hashlib
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
        if endpoint == "graphql":
            self.assertEqual(method, "POST")
            self.assertEqual(payload["query"], mailbox._COMMENTS_QUERY)
            variables = payload["variables"]
            self.assertEqual({k: variables[k] for k in ("owner", "name", "number")},
                             {"owner": "phoenix-hacking", "name": "mckernel", "number": 123})
            after = int(variables["after"].split(":")[1]) if variables["after"] else 0
            rows = [c for c in self.comments if type(c.get("id")) is int and c["id"] > after]
            rows.sort(key=lambda c: c["id"])
            page = copy.deepcopy(rows[:mailbox._COMMENT_PAGE_SIZE])
            return self.page(page, more=len(rows) > len(page))
        self.assertEqual(endpoint, "repos/phoenix-hacking/mckernel/actions/workflows/mckernel-mailbox-notify.yml/dispatches")
        self.assertEqual(method, "POST")
        state = self.state()
        event_id = payload["inputs"]["event_id"]
        parts = [part for notice in state["notices"].values()
                 for part in notice.get("parts", [notice])]
        stored = next(part for part in parts if part["event_id"] == event_id)
        self.assertEqual(stored["body"], payload["inputs"]["body"], "Outbox must be durable before dispatch")
        self.assertEqual(set(payload["inputs"]), {"event_id", "body"})
        self.assertEqual(payload["ref"], "development")
        self.assertEqual(len(event_id), 64)
        self.assertLessEqual(len(json.dumps(payload).encode()), 65535)
        self.dispatches.append(copy.deepcopy(payload))
        return None

    @staticmethod
    def page(rows, more=False):
        return {"data": {"repository": {"pullRequest": {"comments": {
            "nodes": rows, "pageInfo": {
                "endCursor": "comment:" + str(rows[-1]["id"]) if rows else None,
                "hasNextPage": more}}}}}}

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
            if endpoint != "graphql" and kwargs.get("method") == "POST":
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
        self.assertGreater(len(body.encode()), 6000)
        self.assertLessEqual(len(body.encode()), 48000)

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

    def test_large_reply_is_preserved_and_does_not_block_a_later_comment(self):
        text = "é🙂" * 9000 + " trailing spaces \n"
        self.comments = [self.comment(10, "/mckernel-instruct\n" + text), self.comment(11)]
        result = self.mailbox.poll(self.context)
        self.assertEqual(len(result["queued_instruction_ids"]), 2)
        item = next(json.loads(p.read_text()) for p in self.pending()
                    if json.loads(p.read_text())["source_id"].endswith(":10"))
        self.assertTrue(item["text"].endswith("\n\n" + text))
        receipt = self.state()["messages"]["10"]
        self.assertEqual(receipt["instruction_sha256"], hashlib.sha256(item["text"].encode()).hexdigest())
        self.assertEqual(self.state()["last_seen_comment_id"], 11)

    def test_comments_are_cursor_paginated_with_no_total_history_cap(self):
        self.comments = [self.comment(n, "unrelated", user={"type": "User", "id": 1, "login": "other"})
                         for n in range(1, 1202)] + [self.comment(1202)]
        result = self.mailbox.poll(self.context)
        reads = [call for call in self.api_mock.call_args_list if call.args[0] == "graphql"]
        self.assertEqual(len(reads), 25)
        self.assertEqual(len(result["queued_instruction_ids"]), 1)
        self.assertEqual(self.state()["comment_cursor"], "comment:1202")
        self.assertFalse(result["comment_scan_pending"])
        self.advance()
        self.mailbox.poll(self.context)
        self.assertEqual([c for c in self.api_mock.call_args_list if c.args[0] == "graphql"][-1].kwargs["payload"]["variables"]["after"],
                         "comment:1202")

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
        get_calls = lambda: sum(c.args[0] == "graphql" for c in self.api_mock.call_args_list)
        self.assertEqual(get_calls(), 1)
        self.assertEqual(len(self.pending()), 2)
        for ident in first["queued_instruction_ids"]:
            self.write_delivery(ident)
        self.advance(10)
        second = self.mailbox.poll(self.context)
        self.assertEqual(second["status"], "BACKOFF")
        self.assertEqual(get_calls(), 1)
        self.assertEqual(len(self.dispatches), 2)
        self.assertTrue(all("📥 RECEIVED:" in p["inputs"]["body"] for p in self.dispatches))
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
        message = self.state()["messages"]["10"]
        self.assertEqual(message["source_created_at"], "2026-11-10T03:00:00Z")
        self.assertEqual(message["received_at"], "1970-01-01T00:16:40Z")
        self.assertEqual(message["request_id"], request_id)
        self.assertNotIn("timestamp", body)
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
            if endpoint != "graphql" and kwargs.get("method") == "POST":
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
        self.assertIn("Not queued:", self.dispatches[0]["inputs"]["body"])
        self.assertNotIn("Put `/mckernel", self.dispatches[0]["inputs"]["body"])
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
        self.assertNotIn("timestamp", self.dispatches[0]["inputs"]["body"])

    def test_outgoing_blocker_is_message_only_and_default_interval_is_600(self):
        config = dict(self.config)
        config.pop("poll_seconds")
        self.assertEqual(mailbox.Mailbox(self.repo, self.directory, config).poll_seconds, 600)
        self.mailbox.poll(self.context)
        body = self.dispatches[0]["inputs"]["body"]
        self.assertTrue(body.startswith("M14/M15 is blocked."))
        self.assertNotIn("SENT", body)
        self.assertNotIn("Reply in this PR", body)
        self.assertTrue(self.state()["notices"][self.state()["active_notice_event_id"]]["requested"])
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


    def test_page_deadline_checkpoints_and_next_poll_continues(self):
        self.comments = [self.comment(n, "unrelated", user={"type": "User", "id": 1, "login": "other"})
                         for n in range(1, 51)] + [self.comment(51)]
        with patch.object(mailbox.time, "monotonic", side_effect=[0.0, 0.0, 31.0]):
            first = self.mailbox.poll(dict(self.context, status="ACTIVE"))
        self.assertEqual(first["status"], "POLLED")
        self.assertTrue(first["comment_scan_pending"])
        self.assertEqual(self.state()["comment_cursor"], "comment:50")
        self.assertEqual(self.pending(), [])
        self.advance()
        second = self.mailbox.poll(self.context)
        self.assertEqual(len(second["queued_instruction_ids"]), 1)
        reads = [c for c in self.api_mock.call_args_list if c.args[0] == "graphql"]
        self.assertEqual(reads[-1].kwargs["payload"]["variables"]["after"], "comment:50")
        self.assertFalse(second["comment_scan_pending"])

    def test_graphql_partial_error_never_advances_the_affected_page(self):
        self.comments = [self.comment()]
        original = self.api
        def api(endpoint, **kwargs):
            result = original(endpoint, **kwargs)
            if endpoint == "graphql":
                result["errors"] = [{"message": "partial query error"}]
            return result
        self.api_mock.side_effect = api
        result = self.mailbox.poll(self.context)
        self.assertEqual(result["status"], "ERROR")
        self.assertEqual(self.pending(), [])
        self.assertIsNone(self.state().get("comment_cursor"))
        self.assertEqual(self.state()["last_seen_comment_id"], 0)

    def test_graphql_bigint_comment_id_is_exact(self):
        comment = self.comment(6862643464)
        comment["id"] = str(comment["id"])
        original = self.api
        self.api_mock.side_effect = lambda endpoint, **kwargs: (
            self.page([copy.deepcopy(comment)]) if endpoint == "graphql" else original(endpoint, **kwargs))
        result = self.mailbox.poll(self.context)
        self.assertEqual(len(result["queued_instruction_ids"]), 1)
        self.assertEqual(self.state()["last_seen_comment_id"], 6862643464)
        self.assertIn("6862643464", self.state()["messages"])

    def test_multipart_preserves_large_utf8_text_and_queues_only_after_all_parts(self):
        from os_goal_mailbox_protocol import format_instruction_comments
        text = ("A complete source plan 🙂é\r\n \t" * 14000) + "end \n"
        self.assertGreater(len(text.encode()), 256 * 1024)
        parts = format_instruction_comments(text)
        self.assertGreater(len(parts), 1)
        self.comments = [self.comment(index, body) for index, body in enumerate(parts[:-1], 1)]
        first = self.mailbox.poll(self.context)
        self.assertEqual(first["queued_instruction_ids"], [])
        self.assertEqual(self.pending(), [])
        self.assertEqual(self.dispatches, [], "Do not email a receipt for every transport part")
        self.assertTrue(all(m["delivery_status"] == "ASSEMBLING" for m in self.state()["messages"].values()))
        self.comments.append(self.comment(len(parts), parts[-1]))
        self.advance()
        result = self.mailbox.poll(self.context)
        self.assertEqual(len(result["queued_instruction_ids"]), 1)
        item = json.loads(self.pending()[0].read_text())
        self.assertTrue(item["text"].endswith("\n\n" + text))
        self.assertEqual(len(self.dispatches), 1)
        self.assertEqual(self.state()["messages"][str(len(parts))]["delivery_status"], "WAITING")
        # A retry with new GitHub comment IDs is still the same logical message.
        self.comments.extend(self.comment(len(parts) + index, body) for index, body in enumerate(parts, 1))
        self.advance()
        again = self.mailbox.poll(self.context)
        self.assertEqual(again["queued_instruction_ids"], [])
        self.assertEqual(len(self.pending()), 1)
        self.assertEqual(json.loads(self.pending()[0].read_text())["text"], item["text"])

    def test_multipart_foreign_edited_or_conflicting_parts_do_not_execute(self):
        from os_goal_mailbox_protocol import format_instruction_comments
        text = "verified 🙂 " * 10000
        parts = format_instruction_comments(text)
        self.assertGreater(len(parts), 2)
        self.comments = [self.comment(1, parts[0]),
            self.comment(2, parts[1], user={"type": "User", "id": 2, "login": "other"}),
            self.comment(3, parts[1], updated_at="later"),
            self.comment(4, parts[0] + "conflict")]
        self.comments.extend(self.comment(index, body) for index, body in enumerate(parts[2:], 5))
        first = self.mailbox.poll(self.context)
        self.assertEqual(first["queued_instruction_ids"], [])
        self.assertIn("Conflicting", self.state()["messages"]["4"]["not_queued_reason"])
        ident = self.comments[-1]["id"] + 1
        self.comments.append(self.comment(ident, parts[1]))
        self.advance()
        result = self.mailbox.poll(self.context)
        self.assertEqual(len(result["queued_instruction_ids"]), 1)
        self.assertTrue(json.loads(self.pending()[0].read_text())["text"].endswith("\n\n" + text))

    def test_duplicate_part_receipts_follow_the_completed_logical_message(self):
        from os_goal_mailbox_protocol import format_instruction_comments
        parts = format_instruction_comments("duplicate part status " * 4000)
        self.comments = [self.comment(1, parts[0]), self.comment(2, parts[0])]
        self.comments.extend(self.comment(index, body) for index, body in enumerate(parts[1:], 3))
        result = self.mailbox.poll(self.context)
        self.assertEqual(len(result["queued_instruction_ids"]), 1)
        for ident in ("1", "2"):
            receipt = self.state()["messages"][ident]
            self.assertEqual(receipt["delivery_status"], "PART_OF_QUEUED")
            self.assertEqual(receipt["logical_request_id"], result["queued_instruction_ids"][0])

    def test_multipart_digest_mismatch_is_not_queued_and_later_message_runs(self):
        body = "/mckernel-instruct-part " + "a" * 64 + " 1/1\nwrong content"
        self.comments = [self.comment(1, body), self.comment(2)]
        result = self.mailbox.poll(self.context)
        self.assertEqual(len(result["queued_instruction_ids"]), 1)
        self.assertIn("digest", self.state()["messages"]["1"]["not_queued_reason"])
        self.assertTrue(json.loads(self.pending()[0].read_text())["source_id"].endswith(":2"))

    def test_failed_digest_is_retained_and_a_fresh_complete_resend_can_succeed(self):
        text = "first second"
        digest = hashlib.sha256(text.encode()).hexdigest()
        command = "/mckernel-instruct-part " + digest
        self.comments = [self.comment(1, command + " 1/2\nwrong "),
                         self.comment(2, command + " 2/2\nsecond")]
        first = self.mailbox.poll(self.context)
        self.assertEqual(first["queued_instruction_ids"], [])
        self.assertEqual(self.state()["messages"]["1"]["delivery_status"], "REJECTED_ASSEMBLY")
        self.comments += [self.comment(3, command + " 1/2\nfirst "),
                          self.comment(4, command + " 2/2\nsecond")]
        self.advance()
        second = self.mailbox.poll(self.context)
        self.assertEqual(len(second["queued_instruction_ids"]), 1)
        self.assertTrue(json.loads(self.pending()[0].read_text())["text"].endswith("\n\n" + text))
        group = self.state()["multipart"][digest]
        self.assertEqual(group["rejected_attempts"][0]["parts"]["1"]["text"], "wrong ")
        self.assertEqual(self.state()["messages"]["1"]["delivery_status"], "REJECTED_ASSEMBLY")

    def test_multipart_queue_crash_recovers_once_without_source_comments(self):
        from os_goal_mailbox_protocol import format_instruction_comments
        text = "exact repeated Unicode 🙂\n" * 3000
        parts = format_instruction_comments(text)
        self.comments = [self.comment(index, body) for index, body in enumerate(parts, 1)]
        original = mailbox.queue_instruction
        def crash(*args, **kwargs):
            original(*args, **kwargs)
            raise SystemExit("after durable queue, before acknowledgement")
        with patch.object(mailbox, "queue_instruction", side_effect=crash):
            with self.assertRaises(SystemExit):
                self.mailbox.poll(self.context)
        self.assertEqual(len(self.pending()), 1)
        self.assertIn("enqueue_intent", self.state())
        self.comments = []
        self.advance()
        result = self.mailbox.poll(self.context)
        self.assertEqual(len(result["queued_instruction_ids"]), 1)
        self.assertEqual(len(self.pending()), 1)
        self.assertTrue(json.loads(self.pending()[0].read_text())["text"].endswith("\n\n" + text))
        self.assertNotIn("enqueue_intent", self.state())

    def test_long_outbox_keeps_all_text_and_waits_for_every_part_receipt(self):
        context = dict(self.context, missing_input="long detailed result 🙂\n" * 5000)
        result = self.mailbox.poll(context)
        event_id = result["notice_event_id"]
        expected = self.state()["notices"][event_id]["body"]
        count = len(self.state()["notices"][event_id]["parts"])
        self.assertGreater(count, 1)
        for _ in range(count - 1):
            self.advance(1)
            self.mailbox.poll(context)
        self.assertEqual(len(self.dispatches), count)
        self.assertEqual("".join(p["inputs"]["body"] for p in self.dispatches), expected)
        self.assertEqual(len({p["inputs"]["event_id"] for p in self.dispatches}), count)
        self.comments = [self.comment(1, mailbox.MARKER.format(event_id=self.dispatches[0]["inputs"]["event_id"]),
                                      user={"type": "Bot", "login": "github-actions[bot]"})]
        self.advance(600)
        partial = self.mailbox.poll(context)
        self.assertFalse(partial["observed_notice"])
        self.comments.extend(self.comment(index, mailbox.MARKER.format(event_id=payload["inputs"]["event_id"]),
                             user={"type": "Bot", "login": "github-actions[bot]"})
                             for index, payload in enumerate(self.dispatches[1:count], 2))
        self.advance()
        complete = self.mailbox.poll(context)
        self.assertTrue(complete["observed_notice"])
        self.assertEqual(len(self.state()["notices"][event_id]["observed_comment_ids"]), count)

    def file_revision(self, commit="a" * 40, text="Continue the current functional work.\r\n"):
        return {"status": "READY", "commit_sha": commit, "blob_sha": "b" * 40,
                "text": text, "source_url": "https://github.com/phoenix-hacking/mckernel/blob/" + commit + "/mailbox.txt",
                "author_login": "phoenix-hacking", "author_id": 175406809}

    def enable_file(self):
        self.mailbox.config.update(file_inbox_branch="codex/mckernel-control-mailbox",
                                   file_inbox_path="mailbox.txt", file_reply_path="mailbox-reply.txt")
        self.mailbox.file_enabled = True

    def test_file_revision_is_queued_once_and_new_revision_is_independent(self):
        self.enable_file()
        revision = self.file_revision(text="plain text without a slash command\r\n" * 10000)
        with patch.object(mailbox, "read_revision", return_value=revision), \
                patch.object(mailbox, "write_reply", return_value={"status": "POSTED", "blob_sha": "c" * 40}):
            first = self.mailbox.poll(self.context)
            self.assertEqual(len(first["queued_instruction_ids"]), 1)
            item = json.loads(self.pending()[0].read_text())
            self.assertTrue(item["text"].endswith("\n\n" + revision["text"]))
            self.assertEqual(self.state()["last_seen_comment_id"], 0)
            self.advance()
            self.assertEqual(self.mailbox.poll(self.context)["queued_instruction_ids"], [])
        changed = self.file_revision(commit="d" * 40, text="A new revision.")
        with patch.object(mailbox, "read_revision", return_value=changed), \
                patch.object(mailbox, "write_reply", return_value={"status": "POSTED"}):
            self.advance()
            second = self.mailbox.poll(self.context)
        self.assertEqual(len(second["queued_instruction_ids"]), 1)
        self.assertEqual(len(self.pending()), 2)

    def test_file_receipt_acceptance_is_mirrored_as_plain_latest_reply(self):
        self.enable_file()
        revision = self.file_revision()
        with patch.object(mailbox, "read_revision", return_value=revision), \
                patch.object(mailbox, "write_reply", return_value={"status": "POSTED"}) as writer:
            first = self.mailbox.poll(self.context)
            self.assertIn("📥 RECEIVED", writer.call_args.args[1])
            self.write_delivery(first["queued_instruction_ids"][0])
            self.advance(10)
            self.mailbox.poll(self.context)
            self.assertEqual(self.state()["file_inbox"]["status"], "ACCEPTED")
            self.assertIn("✅ RECEIVED BY CONTROLLER", writer.call_args.args[1])
            self.assertIn("WAITING for the work result", writer.call_args.args[1])
            self.assertNotIn("Reply here", writer.call_args.args[1])
            self.assertEqual(writer.call_count, 2)

    def test_file_read_failure_does_not_block_valid_comment(self):
        self.enable_file()
        self.comments = [self.comment()]
        with patch.object(mailbox, "read_revision", side_effect=ValueError("Unverified file commit")), \
                patch.object(mailbox, "write_reply", return_value={"status": "POSTED"}):
            result = self.mailbox.poll(self.context)
        self.assertEqual(result["status"], "POLLED")
        self.assertEqual(len(result["queued_instruction_ids"]), 1)
        self.assertEqual(self.state()["file_inbox"]["status"], "ERROR")
        self.assertNotIn("last_seen_commit", self.state()["file_inbox"])

    def test_late_acceptance_preserves_a_newer_work_result(self):
        self.enable_file()
        state = self.mailbox._state()
        self.mailbox._event(state, "received", "first", "Received instruction")
        with patch.object(mailbox, "write_reply", return_value={"status": "POSTED", "blob_sha": "c" * 40}):
            self.mailbox._publish_reply(state, self.clock[0])
        accepted = self.mailbox._event(state, "accepted", "first", "WAITING for the work result")
        with patch.object(mailbox, "write_reply", return_value={"status": "PRESERVED", "blob_sha": "d" * 40}) as writer:
            self.mailbox._publish_reply(state, self.clock[0] + 1)
            self.assertEqual(writer.call_args.kwargs["expected_blob_sha"], "c" * 40)
            self.assertEqual(state["file_reply"]["event_id"], accepted)
            self.assertEqual(state["file_reply"]["status"], "PRESERVED")
            self.assertNotIn("published_at", state["file_reply"])
            self.mailbox._publish_reply(state, self.clock[0] + 601)
            self.assertEqual(writer.call_count, 1)
            self.mailbox._event(state, "accepted", "second", "A later acceptance")
            self.mailbox._publish_reply(state, self.clock[0] + 602)
            self.assertIsNone(writer.call_args.kwargs["expected_blob_sha"])

    def test_uncertain_acceptance_preserves_expected_reply_blob_across_restart(self):
        self.enable_file()
        state = self.mailbox._state()
        state["file_reply"] = {"event_id": "previous", "status": "POSTED", "blob_sha": "c" * 40}
        self.mailbox._event(state, "accepted", "first", "WAITING for the work result")
        with patch.object(mailbox, "write_reply", side_effect=RuntimeError("Unconfirmed PUT")) as writer:
            self.mailbox._publish_reply(state, self.clock[0])
            self.assertEqual(writer.call_args.kwargs["expected_blob_sha"], "c" * 40)
        restored = self.mailbox._state()
        self.assertEqual(restored["file_reply"]["status"], "ERROR")
        self.assertEqual(restored["file_reply"]["expected_blob_sha"], "c" * 40)
        with patch.object(mailbox, "write_reply", return_value={"status": "OBSERVED", "blob_sha": "d" * 40}) as writer:
            self.mailbox._publish_reply(restored, self.clock[0] + 600)
            self.assertEqual(writer.call_args.kwargs["expected_blob_sha"], "c" * 40)
        # With no prior confirmed mirror, acceptance must expect an absent file.
        fresh = self.mailbox._state()
        fresh.pop("file_reply")
        with patch.object(mailbox, "write_reply", return_value={"status": "PRESERVED", "blob_sha": "e" * 40}) as writer:
            self.mailbox._publish_reply(fresh, self.clock[0] + 1200)
            self.assertIn("expected_blob_sha", writer.call_args.kwargs)
            self.assertIsNone(writer.call_args.kwargs["expected_blob_sha"])

    def test_file_queue_crash_recovers_original_revision_once(self):
        self.enable_file()
        revision = self.file_revision()
        original = mailbox.queue_instruction
        def crash(*args, **kwargs):
            original(*args, **kwargs)
            raise SystemExit("after file instruction queued")
        with patch.object(mailbox, "read_revision", return_value=revision), \
                patch.object(mailbox, "queue_instruction", side_effect=crash):
            with self.assertRaises(SystemExit):
                self.mailbox.poll(self.context)
        self.assertEqual(len(self.pending()), 1)
        self.assertEqual(self.state()["enqueue_intent"]["source_kind"], "file")
        with patch.object(mailbox, "read_revision", return_value=revision), \
                patch.object(mailbox, "write_reply", return_value={"status": "POSTED"}):
            result = self.mailbox.poll(self.context)
        self.assertEqual(len(result["queued_instruction_ids"]), 1)
        self.assertEqual(len(self.pending()), 1)
        self.assertEqual(self.state()["file_inbox"]["last_seen_commit"], revision["commit_sha"])

    def test_file_read_recovery_keeps_an_already_accepted_delivery(self):
        self.enable_file()
        revision = self.file_revision()
        with patch.object(mailbox, "read_revision", return_value=revision) as reader, \
                patch.object(mailbox, "write_reply", return_value={"status": "POSTED", "blob_sha": "c" * 40}):
            first = self.mailbox.poll(self.context)
            self.write_delivery(first["queued_instruction_ids"][0])
            self.advance(10)
            self.mailbox.poll(self.context)
            self.assertEqual(self.state()["file_inbox"]["status"], "ACCEPTED")
            reader.side_effect = RuntimeError("Temporary file read failure")
            self.advance(590)
            self.mailbox.poll(self.context)
            self.assertEqual(self.state()["file_inbox"]["status"], "ERROR")
            reader.side_effect = None
            self.advance()
            result = self.mailbox.poll(self.context)
            self.assertEqual(result["queued_instruction_ids"], [])
            self.assertEqual(self.state()["file_inbox"]["status"], "ACCEPTED")
            self.assertEqual(len(self.state()["messages"]), 1)

    def test_empty_file_is_inactive_and_does_not_cancel_existing_instruction(self):
        self.enable_file()
        with patch.object(mailbox, "read_revision", return_value={"status": "EMPTY", "commit_sha": "a" * 40}), \
                patch.object(mailbox, "write_reply", return_value={"status": "POSTED"}):
            result = self.mailbox.poll(dict(self.context, status="ACTIVE"))
        self.assertEqual(result["queued_instruction_ids"], [])
        self.assertEqual(self.pending(), [])
        self.assertEqual(self.state()["file_inbox"]["status"], "EMPTY")
        self.assertEqual(json.loads((self.directory / "state.json").read_text()), self.saved)

    def test_uncertain_reply_write_backs_off_without_disabling_email(self):
        self.enable_file()
        with patch.object(mailbox, "read_revision", return_value=self.file_revision()), \
                patch.object(mailbox, "write_reply", side_effect=RuntimeError("Unconfirmed PUT")) as writer:
            first = self.mailbox.poll(self.context)
            self.assertEqual(first["status"], "POLLED")
            self.assertEqual(len(self.dispatches), 1)
            self.assertEqual(self.state()["file_reply"]["status"], "ERROR")
            self.advance(10)
            self.mailbox.poll(self.context)
            self.assertEqual(writer.call_count, 1)
        with patch.object(mailbox, "read_revision", return_value=self.file_revision()), \
                patch.object(mailbox, "write_reply", return_value={"status": "OBSERVED"}) as writer:
            self.advance(590)
            self.mailbox.poll(dict(self.context, status="ACTIVE"))
            self.assertEqual(writer.call_count, 1)
            self.assertEqual(self.state()["file_reply"]["status"], "OBSERVED")

    def test_mailbox_state_above_old_two_mib_cap_reloads_without_loss(self):
        state = self.mailbox._state()
        state["retained_test_message"] = "🙂" * 200000
        mailbox._save(self.mailbox.path, state)
        self.assertGreater(self.mailbox.path.stat().st_size, 2 * 1024 * 1024)
        self.assertEqual(self.mailbox._state(), state)
        before = self.mailbox.path.read_bytes()
        with patch.object(mailbox.json, "dump", side_effect=OSError("storage unavailable")):
            with self.assertRaises(OSError):
                mailbox._save(self.mailbox.path, dict(state, new=True))
        self.assertEqual(self.mailbox.path.read_bytes(), before)
        self.assertEqual(list(self.directory.glob("mailbox-state.json.*.tmp")), [])


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

