"""Immutable Git file mailbox contracts: in-memory API replies only."""
import base64
import copy
import hashlib
from pathlib import Path
import sys
import unittest
from urllib.parse import quote, urlencode

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import os_goal_file_mailbox as mailbox


CONFIG = {"repo": "phoenix-hacking/mckernel", "authorized_user_id": 175406809,
          "authorized_user_login": "phoenix-hacking", "file_inbox_branch": "codex/mckernel-control-mailbox",
          "file_inbox_path": "mailbox.txt", "file_reply_path": "mailbox-reply.txt"}
OWNER = {"id": 175406809, "login": "phoenix-hacking", "type": "User"}
WEB_FLOW = {"id": 19864447, "login": "web-flow", "type": "User"}
COMMIT = "a" * 40


def blob_sha(raw):
    return hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


def metadata(raw, path="mailbox.txt", *, omitted=False):
    return {"type": "file", "path": path, "sha": blob_sha(raw), "size": len(raw),
            "encoding": "none" if omitted else "base64",
            "content": "" if omitted else base64.encodebytes(raw).decode("ascii"),
            "download_url": "https://unrelated.example/never-follow-this"}


class FileAPI:
    def __init__(self, raw=b"An instruction.\n", *, config=None, omitted=False):
        self.config = dict(CONFIG if config is None else config)
        self.calls = []
        self.commits = [{"sha": COMMIT, "author": dict(OWNER), "committer": dict(WEB_FLOW),
                         "commit": {"verification": {"verified": True, "reason": "valid"}}}]
        self.file = metadata(raw, self.config["file_inbox_path"], omitted=omitted)
        self.blob = {"sha": blob_sha(raw), "size": len(raw), "encoding": "base64",
                     "content": base64.encodebytes(raw).decode("ascii")}
        self.reply = metadata(b"", self.config["file_reply_path"])
        self.fail_put = False
        self.put_receipt_change = None

    def __call__(self, endpoint, *, method="GET", payload=None, timeout=10, accept=None):
        if timeout != 10:
            raise AssertionError("Every API request must retain its timeout")
        if method == "GET" and "/contents/" in endpoint and accept != "application/vnd.github.object+json":
            raise AssertionError("Contents metadata requires GitHub object media type for large files")
        self.calls.append((endpoint, method, copy.deepcopy(payload)))
        remote = "repos/" + self.config["repo"]
        inbox_path = quote(self.config["file_inbox_path"], safe="/")
        reply_path = quote(self.config["file_reply_path"], safe="/")
        branch_query = urlencode({"ref": self.config["file_inbox_branch"]}, quote_via=quote, safe="")
        commit_query = urlencode({"sha": self.config["file_inbox_branch"],
                                  "path": self.config["file_inbox_path"], "per_page": 1}, quote_via=quote, safe="")
        if method == "GET" and endpoint == remote + "/commits?" + commit_query:
            return copy.deepcopy(self.commits)
        if method == "GET" and endpoint == f"{remote}/contents/{inbox_path}?ref={COMMIT}":
            return copy.deepcopy(self.file)
        if method == "GET" and endpoint == f"{remote}/git/blobs/{self.file['sha']}":
            return copy.deepcopy(self.blob)
        if method == "GET" and endpoint == f"{remote}/contents/{reply_path}?{branch_query}":
            return copy.deepcopy(self.reply)
        if method == "PUT" and endpoint == f"{remote}/contents/{reply_path}":
            if payload["sha"] != self.reply["sha"] or payload["branch"] != self.config["file_inbox_branch"]:
                raise AssertionError("The reply PUT must compare-and-swap the observed branch blob")
            raw = base64.b64decode(payload["content"], validate=True)
            self.reply = metadata(raw, self.config["file_reply_path"])
            if self.fail_put:
                raise RuntimeError("Simulated lost successful PUT response")
            response = {"content": copy.deepcopy(self.reply), "commit": {"sha": "b" * 40}}
            if self.put_receipt_change:
                self.put_receipt_change(response)
            return response
        raise AssertionError("Unexpected API request: " + endpoint)

    def puts(self):
        return [call for call in self.calls if call[1] == "PUT"]


class FileMailboxReadTests(unittest.TestCase):
    def test_exact_utf8_crlf_and_whitespace_are_bound_to_immutable_commit(self):
        text = "  🐦 café e\u0301 漢字\r\n/mckernel-instruct\nleave this whole text intact \t\r\n"
        api = FileAPI(text.encode("utf-8"))
        result = mailbox.read_revision(CONFIG, api=api)
        self.assertEqual(result["status"], "READY")
        self.assertEqual(result["text"], text)
        self.assertEqual(result["commit_sha"], COMMIT)
        self.assertEqual(result["blob_sha"], blob_sha(text.encode("utf-8")))
        self.assertEqual(result["byte_size"], len(text.encode("utf-8")))
        self.assertEqual(result["author_id"], OWNER["id"])
        self.assertEqual(result["committer_id"], WEB_FLOW["id"])
        self.assertEqual(result["source_url"], f"https://github.com/phoenix-hacking/mckernel/blob/{COMMIT}/mailbox.txt")
        self.assertEqual(len(api.calls), 2)
        self.assertTrue(api.calls[1][0].endswith("?ref=" + COMMIT))
        self.assertTrue(all(call[1] == "GET" for call in api.calls))

    def test_more_than_one_mib_uses_git_blob_fallback_without_truncation(self):
        text = ("🐦 λ漢字\r\n" * 180000) + "\r\n  "
        raw = text.encode("utf-8")
        self.assertGreater(len(raw), 1024 * 1024)
        api = FileAPI(raw, omitted=True)
        result = mailbox.read_revision(CONFIG, api=api)
        self.assertEqual(result["text"], text)
        self.assertEqual(result["blob_sha"], blob_sha(raw))
        self.assertEqual(api.calls[-1][0], "repos/phoenix-hacking/mckernel/git/blobs/" + blob_sha(raw))
        self.assertEqual(len(api.calls), 3)

    def test_branch_and_path_are_url_encoded_and_file_read_never_uses_mutable_ref(self):
        config = dict(CONFIG, file_inbox_branch="control/phone#edits", file_inbox_path="notes/my mailbox?.txt")
        api = FileAPI(config=config)
        result = mailbox.read_revision(config, api=api)
        self.assertIn("sha=control%2Fphone%23edits", api.calls[0][0])
        self.assertIn("path=notes%2Fmy%20mailbox%3F.txt", api.calls[0][0])
        self.assertEqual(api.calls[1][0], f"repos/phoenix-hacking/mckernel/contents/notes/my%20mailbox%3F.txt?ref={COMMIT}")
        self.assertIn("/" + COMMIT + "/notes/my%20mailbox%3F.txt", result["source_url"])
        self.assertFalse(any("unrelated.example" in call[0] for call in api.calls))

    def test_empty_template_and_missing_history_are_inactive_without_author_trust(self):
        for raw in (b"", b" \t\r\n"):
            with self.subTest(raw=raw):
                api = FileAPI(raw)
                api.commits[0].update(author=None, committer=None, commit={"verification": {"verified": False}})
                result = mailbox.read_revision(CONFIG, api=api)
                self.assertEqual(result["status"], "EMPTY")
                self.assertEqual(result["text"], raw.decode("utf-8"))
                self.assertEqual(result["commit_sha"], COMMIT)
        api = FileAPI()
        api.commits = []
        result = mailbox.read_revision(CONFIG, api=api)
        self.assertEqual(result["status"], "EMPTY")
        self.assertIsNone(result["commit_sha"])
        self.assertEqual(len(api.calls), 1)

    def test_signed_owner_committer_is_also_supported(self):
        api = FileAPI()
        api.commits[0]["committer"] = dict(OWNER)
        self.assertEqual(mailbox.read_revision(CONFIG, api=api)["status"], "READY")

    def test_unsigned_foreign_or_misattributed_commits_are_refused(self):
        changes = [lambda row: row["author"].update(id=7),
                   lambda row: row["author"].update(login="someone-else"),
                   lambda row: row.update(author=None),
                   lambda row: row["committer"].update(id=7),
                   lambda row: row["committer"].update(login="another-account"),
                   lambda row: row["committer"].update(type="Bot"),
                   lambda row: row["commit"]["verification"].update(verified=False),
                   lambda row: row["commit"]["verification"].update(verified=1),
                   lambda row: row["commit"]["verification"].update(reason="unsigned"),
                   lambda row: row["commit"].pop("verification")]
        for change in changes:
            with self.subTest(change=changes.index(change)):
                api = FileAPI()
                change(api.commits[0])
                with self.assertRaisesRegex(ValueError, "verified owner-authored"):
                    mailbox.read_revision(CONFIG, api=api)
                self.assertTrue(all(call[1] == "GET" for call in api.calls))

    def test_bad_commit_and_file_metadata_are_refused(self):
        for change in (lambda api: api.commits[0].update(sha="main"),
                       lambda api: api.file.update(path="somewhere-else.txt"),
                       lambda api: api.file.update(type="symlink"),
                       lambda api: api.file.update(target="another-file"),
                       lambda api: api.file.update(sha="f" * 39),
                       lambda api: api.file.update(size=-1),
                       lambda api: api.file.update(size=True)):
            api = FileAPI()
            change(api)
            with self.assertRaises(ValueError):
                mailbox.read_revision(CONFIG, api=api)

    def test_corrupt_truncated_and_mismatched_blob_content_is_refused(self):
        for omitted in (False, True):
            for field, value in (("content", "!invalid-base64!"), ("content", "eA=="),
                                 ("sha", "f" * 40), ("size", 1), ("encoding", "utf-8")):
                with self.subTest(omitted=omitted, field=field):
                    api = FileAPI(b"original text\r\n", omitted=omitted)
                    data = api.blob if omitted else api.file
                    data[field] = value
                    with self.assertRaises(ValueError):
                        mailbox.read_revision(CONFIG, api=api)

    def test_binary_and_lfs_pointer_are_explicit_errors(self):
        for raw in (b"\xff", b"hello\0world", b"hello\x7fworld",
                    b"version https://git-lfs.github.com/spec/v1\noid sha256:" + b"0" * 64 + b"\nsize 2000000\n"):
            with self.subTest(raw=raw[:40]), self.assertRaises(ValueError):
                mailbox.read_revision(CONFIG, api=FileAPI(raw))


class FileMailboxReplyTests(unittest.TestCase):
    def test_reply_updates_only_separate_file_with_exact_large_text_and_cas(self):
        text = ("  🐦 exact reply\r\n" * 120000) + "\n \t"
        api = FileAPI()
        initial = api.reply["sha"]
        result = mailbox.write_reply(CONFIG, text, api=api)
        self.assertEqual(result["status"], "POSTED")
        self.assertEqual(result["blob_sha"], blob_sha(text.encode("utf-8")))
        self.assertEqual(result["commit_sha"], "b" * 40)
        self.assertEqual(len(api.puts()), 1)
        endpoint, _, payload = api.puts()[0]
        self.assertEqual(endpoint, "repos/phoenix-hacking/mckernel/contents/mailbox-reply.txt")
        self.assertEqual(payload["sha"], initial)
        self.assertEqual(payload["branch"], CONFIG["file_inbox_branch"])
        self.assertEqual(payload["message"], "Update McKernel mailbox reply [skip ci]")
        self.assertEqual(base64.b64decode(payload["content"]).decode("utf-8"), text)
        self.assertEqual(len(api.calls), 2)

    def test_equal_reply_blob_is_observed_without_put_or_author_checks(self):
        text = "Exact reply.\r\n"
        api = FileAPI()
        api.reply = metadata(text.encode("utf-8"), CONFIG["file_reply_path"])
        self.assertEqual(mailbox.write_reply(CONFIG, text, api=api)["status"], "OBSERVED")
        self.assertEqual(api.puts(), [])
        self.assertEqual(len(api.calls), 1)

    def test_expected_blob_guard_preserves_a_newer_work_result(self):
        previous = blob_sha(b"Received; waiting for acceptance.\n")
        result_text = "Work complete. Exact evidence is available.\r\n"
        api = FileAPI()
        api.reply = metadata(result_text.encode("utf-8"), CONFIG["file_reply_path"])
        result = mailbox.write_reply(CONFIG, "Accepted; waiting for the work result.", api=api,
                                     expected_blob_sha=previous)
        self.assertEqual(result["status"], "PRESERVED")
        self.assertEqual(result["blob_sha"], blob_sha(result_text.encode("utf-8")))
        self.assertEqual(result["byte_size"], len(result_text.encode("utf-8")))
        self.assertIsNone(result["commit_sha"])
        self.assertEqual(result["path"], CONFIG["file_reply_path"])
        self.assertEqual(result["branch"], CONFIG["file_inbox_branch"])
        self.assertEqual(api.puts(), [])

    def test_expected_current_blob_allows_one_cas_update(self):
        api = FileAPI()
        expected = api.reply["sha"]
        result = mailbox.write_reply(CONFIG, "Accepted.", api=api, expected_blob_sha=expected)
        self.assertEqual(result["status"], "POSTED")
        self.assertEqual(len(api.puts()), 1)
        self.assertEqual(api.puts()[0][2]["sha"], expected)

    def test_explicit_none_preserves_existing_content_but_omitted_guard_replaces_it(self):
        api = FileAPI()
        api.reply = metadata(b"A completed work result.\n", CONFIG["file_reply_path"])
        result = mailbox.write_reply(CONFIG, "Waiting.", api=api, expected_blob_sha=None)
        self.assertEqual(result["status"], "PRESERVED")
        self.assertEqual(api.puts(), [])
        result = mailbox.write_reply(CONFIG, "Waiting.", api=api)
        self.assertEqual(result["status"], "POSTED")
        self.assertEqual(len(api.puts()), 1)

    def test_guarded_retry_observes_desired_success_even_when_expected_is_old_or_none(self):
        text = "Accepted by controller.\r\n"
        api = FileAPI()
        expected = api.reply["sha"]
        api.fail_put = True
        with self.assertRaises(mailbox.ReplyWriteError):
            mailbox.write_reply(CONFIG, text, api=api, expected_blob_sha=expected)
        self.assertEqual(len(api.puts()), 1)
        api.fail_put = False
        api.calls.clear()
        for guard in (expected, None):
            with self.subTest(guard=guard):
                result = mailbox.write_reply(CONFIG, text, api=api, expected_blob_sha=guard)
                self.assertEqual(result["status"], "OBSERVED")
                self.assertEqual(result["blob_sha"], blob_sha(text.encode("utf-8")))
        self.assertEqual(api.puts(), [])

    def test_guarded_retry_preserves_result_written_after_uncertain_status_update(self):
        api = FileAPI()
        expected = api.reply["sha"]
        api.fail_put = True
        with self.assertRaises(mailbox.ReplyWriteError):
            mailbox.write_reply(CONFIG, "Accepted; waiting.", api=api, expected_blob_sha=expected)
        api.reply = metadata(b"New completed work result.\r\n", CONFIG["file_reply_path"])
        api.fail_put = False
        api.calls.clear()
        result = mailbox.write_reply(CONFIG, "Accepted; waiting.", api=api, expected_blob_sha=expected)
        self.assertEqual(result["status"], "PRESERVED")
        self.assertEqual(api.puts(), [])

    def test_uncertain_put_stops_once_and_next_get_observes_previous_success(self):
        text = "Complete reply after a lost response.\r\n"
        api = FileAPI()
        api.fail_put = True
        with self.assertRaises(mailbox.ReplyWriteError) as caught:
            mailbox.write_reply(CONFIG, text, api=api)
        self.assertTrue(caught.exception.uncertain)
        self.assertEqual(len(api.puts()), 1)
        api.fail_put = False
        api.calls.clear()
        result = mailbox.write_reply(CONFIG, text, api=api)
        self.assertEqual(result["status"], "OBSERVED")
        self.assertEqual(api.puts(), [])
        self.assertEqual(len(api.calls), 1)

    def test_bad_put_receipt_is_uncertain_and_never_retried(self):
        for change in (lambda row: row["content"].update(sha="f" * 40),
                       lambda row: row["content"].update(path=CONFIG["file_inbox_path"]),
                       lambda row: row["content"].update(type="symlink"),
                       lambda row: row["content"].update(size=0),
                       lambda row: row["commit"].update(sha="not-a-sha")):
            api = FileAPI()
            api.put_receipt_change = change
            with self.assertRaises(mailbox.ReplyWriteError):
                mailbox.write_reply(CONFIG, "Reply", api=api)
            self.assertEqual(len(api.puts()), 1)

    def test_invalid_reply_metadata_or_alias_to_user_inbox_prevents_put(self):
        for change in (lambda api: api.reply.update(path="wrong.txt"),
                       lambda api: api.reply.update(type="symlink"),
                       lambda api: api.reply.update(sha="not-a-sha")):
            api = FileAPI()
            change(api)
            with self.assertRaises(ValueError):
                mailbox.write_reply(CONFIG, "Reply", api=api)
            self.assertEqual(api.puts(), [])
        api = FileAPI()
        with self.assertRaises(ValueError):
            mailbox.write_reply(dict(CONFIG, file_reply_path=CONFIG["file_inbox_path"]), "Reply", api=api)
        self.assertEqual(api.calls, [])


if __name__ == "__main__":
    unittest.main()
