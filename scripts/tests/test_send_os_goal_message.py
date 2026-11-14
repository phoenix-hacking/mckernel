"""Sender contracts use in-memory API replies and never contact GitHub."""
import contextlib
import copy
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import os_goal_mailbox_protocol as protocol
import send_os_goal_message as sender


CONFIG = {"repo": "phoenix-hacking/mckernel", "issue_number": 3,
          "authorized_user_id": 175406809, "authorized_user_login": "phoenix-hacking"}
USER = {"id": 175406809, "login": "phoenix-hacking", "type": "User"}


def comment(body, ident=1, **changes):
    row = {"id": ident, "body": body, "user": dict(USER),
           "created_at": "2026-11-13T03:00:00Z", "updated_at": "2026-11-13T03:00:00Z"}
    row.update(changes)
    return row


class FakeAPI:
    def __init__(self, comments=()):
        self.comments = copy.deepcopy(list(comments))
        self.calls = []
        self.fail_post = False
        self.user = dict(USER)
        self.pull = {"number": 3, "user": dict(USER), "base": {"repo": {"full_name": CONFIG["repo"]}},
                     "state": "open", "draft": True, "merged": False}

    def __call__(self, endpoint, *, method="GET", payload=None, timeout=10):
        self.calls.append((endpoint, method, copy.deepcopy(payload)))
        if method == "POST":
            if endpoint != "repos/phoenix-hacking/mckernel/issues/3/comments":
                raise AssertionError(endpoint)
            row = comment(payload["body"], max((row["id"] for row in self.comments), default=0) + 1)
            self.comments.append(row)
            if self.fail_post:
                raise subprocess.TimeoutExpired(["gh", "api"], 10)
            return copy.deepcopy(row)
        if endpoint == "user":
            return copy.deepcopy(self.user)
        if endpoint == "repos/phoenix-hacking/mckernel/pulls/3":
            return copy.deepcopy(self.pull)
        prefix = "repos/phoenix-hacking/mckernel/issues/3/comments?per_page=100&page="
        if endpoint.startswith(prefix):
            page = int(endpoint[len(prefix):])
            return copy.deepcopy(self.comments[(page - 1) * 100:page * 100])
        raise AssertionError(endpoint)

    def posts(self):
        return [call for call in self.calls if call[1] == "POST"]


class MailboxSenderTests(unittest.TestCase):
    def setUp(self):
        self.text = " \r\n" + ("🐦 café漢字 @<>\t\r\n" * 14000) + "\n  "
        self.bodies = protocol.format_instruction_comments(self.text)
        self.assertGreater(len(self.text.encode("utf-8")), 256 * 1024)
        self.assertGreater(len(self.bodies), 2)
        self.message_id = hashlib.sha256(self.text.encode("utf-8")).hexdigest()

    def test_posts_in_order_and_rerun_reuses_verified_durable_parts(self):
        api = FakeAPI()
        result = sender.send_message(self.text, CONFIG, api=api)
        self.assertEqual(result["message_id"], self.message_id)
        self.assertEqual(result["posted_parts"], len(self.bodies))
        self.assertEqual([call[2]["body"] for call in api.posts()], self.bodies)
        api.calls.clear()
        result = sender.send_message(self.text, CONFIG, api=api)
        self.assertEqual(result["existing_parts"], len(self.bodies))
        self.assertEqual(result["posted_parts"], 0)
        self.assertEqual(api.posts(), [])

    def test_unknown_post_stops_once_then_explicit_rerun_scans_before_resuming(self):
        api = FakeAPI()
        api.fail_post = True
        with self.assertRaises(sender.SendError) as caught:
            sender.send_message(self.text, CONFIG, api=api)
        self.assertTrue(caught.exception.uncertain)
        self.assertEqual(caught.exception.message_id, self.message_id)
        self.assertEqual(len(api.posts()), 1)
        self.assertEqual(len(api.comments), 1, "Simulate POST success with a lost response")
        api.fail_post = False
        api.calls.clear()
        result = sender.send_message(self.text, CONFIG, api=api)
        self.assertEqual(result["existing_parts"], 1)
        self.assertEqual(result["posted_parts"], len(self.bodies) - 1)
        self.assertEqual([row["body"] for row in api.comments], self.bodies)
        first_post = next(index for index, call in enumerate(api.calls) if call[1] == "POST")
        self.assertTrue(any("comments?" in call[0] for call in api.calls[:first_post]))

    def test_spoof_and_edited_parts_are_not_deduplication_evidence(self):
        spoof = dict(USER, id=7)
        rows = [comment(self.bodies[0], 1, user=spoof),
                comment(self.bodies[1], 2, updated_at="2026-11-13T03:01:00Z"),
                comment(self.bodies[2], 3)]
        api = FakeAPI(rows)
        result = sender.send_message(self.text, CONFIG, api=api)
        self.assertEqual(result["existing_parts"], 1)
        self.assertEqual([call[2]["body"] for call in api.posts()], self.bodies[:2] + self.bodies[3:])

    def test_conflicting_unedited_owner_parts_prevent_every_mutation(self):
        command, _, payload = self.bodies[0].partition("\n")
        for body in (command + "\nchanged" + payload,
                     command.replace("1/", "01/", 1) + "\n" + payload,
                     f"{protocol.PART_COMMAND} {self.message_id} 1/99999\n" + payload):
            with self.subTest(body=body[:120]):
                api = FakeAPI([comment(body)])
                with self.assertRaises(sender.SendError) as caught:
                    sender.send_message(self.text, CONFIG, api=api)
                self.assertFalse(caught.exception.uncertain)
                self.assertEqual(api.posts(), [])

    def test_history_has_no_1000_comment_or_total_page_cap(self):
        rows = [comment("Unrelated existing comment", index) for index in range(1, 1101)]
        body = protocol.format_instruction_comments("A small instruction.\n")[0]
        rows.append(comment(body, 1101))
        api = FakeAPI(rows)
        result = sender.send_message("A small instruction.\n", CONFIG, api=api)
        self.assertEqual(result["comment_ids"], [1101])
        self.assertEqual(api.posts(), [])
        self.assertTrue(any(call[0].endswith("page=12") for call in api.calls))

    def test_authentication_and_pr_binding_are_verified_before_posts(self):
        for field in ("user_id", "user_login", "pr_author", "pr_repo", "pr_number", "closed", "nondraft", "merged"):
            with self.subTest(field=field):
                api = FakeAPI()
                if field == "user_id": api.user["id"] = 7
                if field == "user_login": api.user["login"] = "another-user"
                if field == "pr_author": api.pull["user"]["id"] = 7
                if field == "pr_repo": api.pull["base"]["repo"]["full_name"] = "someone/else"
                if field == "pr_number": api.pull["number"] = 4
                if field == "closed": api.pull["state"] = "closed"
                if field == "nondraft": api.pull["draft"] = False
                if field == "merged": api.pull["merged"] = True
                with self.assertRaises(sender.SendError):
                    sender.send_message("Instruction", CONFIG, api=api)
                self.assertEqual(api.posts(), [])

    def test_invalid_post_receipt_stops_without_posting_the_next_part(self):
        api = FakeAPI()
        def lost_receipt(endpoint, **kwargs):
            result = api(endpoint, **kwargs)
            return None if kwargs.get("method") == "POST" else result
        with self.assertRaises(sender.SendError) as caught:
            sender.send_message(self.text, CONFIG, api=lost_receipt)
        self.assertTrue(caught.exception.uncertain)
        self.assertEqual(len(api.posts()), 1)

    def test_cli_preserves_file_bytes_and_reports_failed_logical_id(self):
        with tempfile.TemporaryDirectory(prefix="mailbox-sender-test-") as directory:
            message = Path(directory) / "message.txt"
            config = Path(directory) / "config.json"
            raw = "  exact\r\nUnicode 🐦\r\n\t"
            message.write_bytes(raw.encode("utf-8"))
            config.write_text(json.dumps(CONFIG))
            with patch.object(sender, "send_message", return_value={"status": "sent"}) as send, \
                    contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(sender.main(["--message-file", str(message), "--config", str(config)]), 0)
                send.assert_called_once_with(raw, CONFIG)
            output = io.StringIO()
            error = sender.SendError(self.message_id, "POST outcome is unconfirmed", uncertain=True)
            with patch.object(sender, "send_message", side_effect=error), contextlib.redirect_stderr(output):
                self.assertEqual(sender.main(["--message-file", str(message), "--config", str(config)]), 1)
            self.assertEqual(json.loads(output.getvalue())["message_id"], self.message_id)
            self.assertTrue(json.loads(output.getvalue())["uncertain_post"])


class SenderGhTests(unittest.TestCase):
    def test_gh_uses_supported_auth_json_stdin_and_no_shell(self):
        payload = {"body": "literal $(not-a-command) `also-not` 🐦\r\n"}
        completed = Mock(returncode=0, stdout='{"id": 1}', stderr="")
        with patch.object(sender.shutil, "which", return_value="/fake/gh"), \
                patch.object(sender.subprocess, "run", return_value=completed) as run:
            self.assertEqual(sender._gh_api("repos/o/r/issues/3/comments", method="POST", payload=payload), {"id": 1})
        self.assertEqual(run.call_args.args[0], ["/fake/gh", "api", "--method", "POST", "repos/o/r/issues/3/comments", "--input", "-"])
        self.assertEqual(json.loads(run.call_args.kwargs["input"]), payload)
        self.assertLessEqual(run.call_args.kwargs["timeout"], 10)
        self.assertFalse(run.call_args.kwargs.get("shell", False))

    def test_gh_error_does_not_print_cli_credentials_or_request_body(self):
        completed = Mock(returncode=1, stdout="token=private", stderr="password=private")
        with patch.object(sender.shutil, "which", return_value="/fake/gh"), \
                patch.object(sender.subprocess, "run", return_value=completed):
            with self.assertRaises(RuntimeError) as caught:
                sender._gh_api("user")
        self.assertNotIn("private", str(caught.exception))


if __name__ == "__main__":
    unittest.main()
