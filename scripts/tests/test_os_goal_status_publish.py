#!/usr/bin/env python3
"""Status publication tests use only fake GitHub and temporary local files."""
import base64
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import os_goal_status_publish as publish


class StatusPublishTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="os-status-publish-test-")
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.snapshot = self.directory / "status.txt"
        self.snapshot.write_text("Generated snapshot A\nOriginal M14/M15 unfinished\n")
        self.remote = b"Previously published snapshot\n"
        self.clock = [1000.0]
        self.publisher = publish.StatusPublisher(self.directory)
        self.calls = []
        self.time_patch = patch.object(publish.time, "time", side_effect=lambda: self.clock[0])
        self.api_patch = patch.object(publish, "_gh_api", side_effect=self.api)
        self.time_patch.start()
        self.api_mock = self.api_patch.start()
        self.addCleanup(self.time_patch.stop)
        self.addCleanup(self.api_patch.stop)

    def state(self):
        return json.loads((self.directory / publish.STATE_FILE).read_text())

    def advance(self, seconds=600):
        self.clock[0] += seconds

    def remote_file(self):
        return {"type": "file", "path": "status.txt", "encoding": "base64", "size": len(self.remote),
                "sha": publish._blob_sha(self.remote), "content": base64.b64encode(self.remote).decode()}

    def api(self, endpoint, *, method="GET", payload=None, timeout=10):
        self.calls.append((method, endpoint, copy.deepcopy(payload)))
        self.assertLessEqual(timeout, 10)
        self.assertGreater(timeout, 0)
        if method == "GET":
            self.assertEqual(endpoint, "repos/phoenix-hacking/mckernel/contents/status.txt?ref=codex%2Fmckernel-control-mailbox")
            return self.remote_file()
        self.assertEqual(method, "PUT")
        self.assertEqual(endpoint, "repos/phoenix-hacking/mckernel/contents/status.txt")
        self.assertEqual(payload["branch"], "codex/mckernel-control-mailbox")
        self.assertIn("[skip ci]", payload["message"])
        self.assertEqual(payload["sha"], publish._blob_sha(self.remote))
        body = base64.b64decode(payload["content"], validate=True)
        intent = self.state()["intent"]
        self.assertEqual(intent["body"].encode(), body)
        self.assertEqual(intent["expected_sha256"], publish._digest(body))
        self.assertEqual(intent["base_sha"], payload["sha"])
        self.assertEqual(intent["status"], "sending")
        self.assertLessEqual(len(body), 200 * 1024)
        self.remote = body
        return {"content": {"path": "status.txt", "sha": publish._blob_sha(body)}, "commit": {"sha": "c" * 40}}

    def counts(self):
        return {method: sum(row[0] == method for row in self.calls) for method in ("GET", "PUT")}

    def test_publish_fixed_file_with_cas_durable_intent_and_skip_ci(self):
        result = self.publisher.publish(self.snapshot)
        self.assertEqual(result["status"], "PUBLISHED")
        self.assertTrue(result["desired_current"])
        self.assertEqual(self.remote, self.snapshot.read_bytes())
        self.assertEqual(self.counts(), {"GET": 1, "PUT": 1})
        self.assertIsNone(self.state()["intent"])
        self.assertEqual(result["next_publish_at"], 1600)
        self.assertEqual(self.state()["published_commit_sha"], "c" * 40)
        self.assertIn("[skip ci]", self.calls[1][2]["message"])

    def test_identical_remote_bytes_are_verified_without_another_commit(self):
        self.remote = self.snapshot.read_bytes()
        result = self.publisher.publish()
        self.assertEqual(result["status"], "UNCHANGED")
        self.assertTrue(result["desired_current"])
        self.assertEqual(self.counts(), {"GET": 1, "PUT": 0})
        self.assertEqual(result["published_sha256"], publish._digest(self.remote))
        self.assertIn("published_verified_at", result)
        self.assertNotIn("published_commit_sha", self.state())

    def test_dynamic_local_timestamp_does_not_bypass_600_second_interval(self):
        self.publisher.publish()
        before = self.state()
        self.snapshot.write_text("New generated timestamp after ten seconds\n")
        self.advance(10)
        result = self.publisher.publish()
        self.assertEqual(result["status"], "BACKOFF")
        self.assertEqual(self.counts(), {"GET": 1, "PUT": 1})
        self.assertEqual(self.state(), before)
        self.advance(590)
        self.assertEqual(self.publisher.publish()["status"], "PUBLISHED")
        self.assertEqual(self.counts(), {"GET": 2, "PUT": 2})

    def test_lost_success_reconciles_prior_bytes_before_publishing_new_snapshot(self):
        normal = self.api
        def lost_response(endpoint, **kwargs):
            response = normal(endpoint, **kwargs)
            if kwargs.get("method") == "PUT":
                raise subprocess.TimeoutExpired(["gh", "api"], 10)
            return response
        self.api_mock.side_effect = lost_response
        original = self.snapshot.read_bytes()
        result = self.publisher.publish()
        self.assertEqual(result["status"], "UNKNOWN")
        self.assertIsNone(result["published_sha256"])
        self.assertEqual(self.state()["intent"]["body"].encode(), original)
        self.assertEqual(self.remote, original)
        self.snapshot.write_text("Generated snapshot B, with a later timestamp\n")
        self.advance()
        self.api_mock.side_effect = normal
        result = self.publisher.publish()
        self.assertEqual(result["status"], "PUBLISHED")
        self.assertEqual(self.remote, self.snapshot.read_bytes())
        self.assertEqual(self.counts(), {"GET": 2, "PUT": 2})
        self.assertNotEqual(self.calls[-1][2]["content"], self.calls[1][2]["content"])
        self.assertIsNone(self.state()["intent"])

    def test_unknown_unapplied_intent_retries_exact_old_body_with_current_cas(self):
        normal = self.api
        def never_applied(endpoint, **kwargs):
            if kwargs.get("method") == "PUT":
                self.calls.append(("PUT", endpoint, copy.deepcopy(kwargs["payload"])))
                raise subprocess.TimeoutExpired(["gh", "api"], 10)
            return normal(endpoint, **kwargs)
        self.api_mock.side_effect = never_applied
        original = self.snapshot.read_bytes()
        self.assertEqual(self.publisher.publish()["status"], "UNKNOWN")
        first_payload = self.calls[1][2]
        self.snapshot.write_text("Generated snapshot B\n")
        self.advance()
        self.api_mock.side_effect = normal
        result = self.publisher.publish()
        self.assertEqual(result["status"], "PUBLISHED")
        self.assertFalse(result["desired_current"], "An older reconciled snapshot is not the newest renderer output")
        self.assertEqual(self.remote, original)
        self.assertEqual(self.calls[-1][2], first_payload)
        self.assertEqual(self.counts(), {"GET": 2, "PUT": 2})
        self.advance()
        self.assertTrue(self.publisher.publish()["desired_current"])
        self.assertEqual(self.remote, self.snapshot.read_bytes())

    def test_intervening_remote_blob_preserves_unknown_instead_of_overwriting(self):
        normal = self.api
        def lost_response(endpoint, **kwargs):
            if kwargs.get("method") == "PUT":
                self.calls.append(("PUT", endpoint, copy.deepcopy(kwargs["payload"])))
                raise subprocess.TimeoutExpired(["gh", "api"], 10)
            return normal(endpoint, **kwargs)
        self.api_mock.side_effect = lost_response
        self.publisher.publish()
        original_intent = self.state()["intent"]
        self.remote = b"Someone else's intervening status revision\n"
        self.snapshot.write_text("A newer local generated snapshot\n")
        self.advance()
        self.api_mock.side_effect = normal
        result = self.publisher.publish()
        self.assertEqual(result["status"], "UNKNOWN")
        self.assertEqual(self.counts(), {"GET": 2, "PUT": 1})
        self.assertEqual(self.state()["intent"], original_intent)
        self.assertIn("reconciliation", result["last_error"])

    def test_conditional_write_race_retains_intent_and_reconciles_next_due(self):
        normal = self.api
        def raced(endpoint, **kwargs):
            if kwargs.get("method") == "PUT":
                self.calls.append(("PUT", endpoint, copy.deepcopy(kwargs["payload"])))
                self.remote = b"Concurrent status update\n"
                raise RuntimeError("Conditional GitHub update rejected")
            return normal(endpoint, **kwargs)
        self.api_mock.side_effect = raced
        self.assertEqual(self.publisher.publish()["status"], "UNKNOWN")
        self.advance()
        self.api_mock.side_effect = normal
        self.assertEqual(self.publisher.publish()["status"], "UNKNOWN")
        self.assertEqual(self.counts(), {"GET": 2, "PUT": 1})

    def test_malformed_success_ack_remains_unknown_until_exact_get_proof(self):
        normal = self.api
        def empty_ack(endpoint, **kwargs):
            response = normal(endpoint, **kwargs)
            return None if kwargs.get("method") == "PUT" else response
        self.api_mock.side_effect = empty_ack
        result = self.publisher.publish()
        self.assertEqual(result["status"], "UNKNOWN")
        self.assertIsNotNone(self.state()["intent"])
        self.assertIsNone(result["published_sha256"])
        self.advance()
        self.api_mock.side_effect = normal
        result = self.publisher.publish()
        self.assertEqual(result["status"], "UNCHANGED")
        self.assertTrue(result["desired_current"])
        self.assertEqual(self.counts(), {"GET": 2, "PUT": 1})

    def test_unavailable_branch_or_authentication_is_local_error_with_backoff(self):
        self.api_mock.side_effect = RuntimeError("GitHub API request failed; check authentication or branch")
        result = self.publisher.publish()
        self.assertEqual(result["status"], "ERROR")
        self.assertIsNone(result["published_sha256"])
        self.assertIsNone(self.state()["intent"])
        self.assertIn("authentication", result["last_error"])
        self.assertEqual(self.publisher.publish()["status"], "BACKOFF")
        self.assertEqual(self.api_mock.call_count, 1)
        self.advance()
        self.publisher.publish()
        self.assertEqual(self.state()["next_publish_at"], 2800)

    def test_oversized_empty_and_non_utf8_local_snapshots_never_call_github(self):
        for body in (b"x" * (publish.MAX_BYTES + 1), b"", b"\xff\xfe"):
            with self.subTest(length=len(body)):
                self.snapshot.write_bytes(body)
                self.assertEqual(self.publisher.publish()["status"], "ERROR")
                self.advance(3600)
        self.api_mock.assert_not_called()

    def test_exact_200_kib_utf8_snapshot_can_publish_without_workflow_size_limit(self):
        text = "😀" * (publish.MAX_BYTES // 4)
        self.assertEqual(self.publisher.publish(text)["status"], "PUBLISHED")
        self.assertEqual(len(self.remote), publish.MAX_BYTES)
        self.assertEqual(self.counts(), {"GET": 1, "PUT": 1})

    def test_malformed_remote_file_sha_or_content_never_triggers_put(self):
        base = self.remote_file()
        variants = ({"path": "scripts/run_os_goal.py"}, {"type": "dir"}, {"content": "!invalid!"},
                    {"sha": "0" * 40}, {"size": 9999}, {"encoding": "utf-8"})
        for variant in variants:
            with self.subTest(variant=variant):
                self.api_mock.side_effect = None
                self.api_mock.return_value = dict(base, **variant)
                self.assertEqual(self.publisher.publish()["status"], "ERROR")
                self.assertIsNone(self.state()["intent"])
                self.advance(3600)
        self.assertTrue(all(c.kwargs.get("method", "GET") == "GET" for c in self.api_mock.call_args_list))

    def test_modified_pending_intent_fails_closed_before_any_network(self):
        self.api_mock.side_effect = subprocess.TimeoutExpired(["gh", "api"], 10)
        # Establish the pending write through a real GET and uncertain PUT first.
        normal = self.api
        def lost(endpoint, **kwargs):
            if kwargs.get("method") == "PUT":
                raise subprocess.TimeoutExpired(["gh", "api"], 10)
            return normal(endpoint, **kwargs)
        self.api_mock.side_effect = lost
        self.publisher.publish()
        state = self.state()
        state["intent"]["body"] = "Tampered body\n"
        (self.directory / publish.STATE_FILE).write_text(json.dumps(state))
        calls = self.api_mock.call_count
        self.advance()
        with self.assertRaises(ValueError):
            self.publisher.publish()
        self.assertEqual(self.api_mock.call_count, calls)

    def test_fixed_destination_binding_cannot_be_redirected_by_state(self):
        self.publisher.publish()
        state = self.state()
        state["branch"] = "development"
        (self.directory / publish.STATE_FILE).write_text(json.dumps(state))
        self.advance()
        calls = self.api_mock.call_count
        with self.assertRaises(ValueError):
            self.publisher.publish()
        self.assertEqual(self.api_mock.call_count, calls)

    def test_synthetic_shell_text_remains_file_content_only(self):
        text = "Generated snapshot\n$(id); `whoami`; no shell is executed\n"
        with patch.object(publish.subprocess, "run", side_effect=AssertionError("No process calls")):
            result = self.publisher.publish(text)
        self.assertEqual(result["status"], "PUBLISHED")
        self.assertEqual(self.remote.decode(), text)


if __name__ == "__main__":
    unittest.main()
