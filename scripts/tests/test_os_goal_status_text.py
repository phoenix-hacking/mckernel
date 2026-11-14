"""Pure status rendering and temporary-file writes; no network or model calls."""
import copy
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import os_goal_status_text as subject


NOW = datetime(2026, 11, 10, 5, 0, tzinfo=timezone.utc)


class StatusTextTests(unittest.TestCase):
    def setUp(self):
        self.ledger = {"updated_at": "2026-11-10T00:52:00Z", "scope": "M14/M15 only",
            "summaries": {"M14": {"original_gate_ids": ["M14-F01"], "checklist_percent_complete": 50,
                "milestone_accepted": False, "original_file_gate_count": 1, "original_integration_gate_count": 0}},
            "requirements": [{"id": "M14-F01", "title": "Original gate", "accepted": False,
                "percent_complete": 50, "parent": "M14", "target": "source.rs", "owner": "Root",
                "dependencies": ["INPUT"], "remaining_actions": ["Bind matching native result."]}],
            "tasks": [{"id": "COUNTED", "parent": "M14-F01", "title": "Counted evidence", "owner": "Root",
                "status": "verified_at_stated_scope", "percent_complete": 100, "counted_in_requirement_rollup": True,
                "done_when": "Exact matching evidence passes.", "scope_limit": "HOST only", "dependencies": ["INPUT"], "evidence": ["proof.json"]},
                {"id": "SUPPORT", "parent": "M14-F01", "title": "Supporting preparation", "owner": "Root",
                "status": "open", "percent_complete": 0, "counted_in_requirement_rollup": False,
                "done_when": "Original input arrives.", "scope_limit": "No acceptance credit", "dependencies": [], "evidence": []}],
            "optional_or_deferred_decisions": [{"id": "OPTIONAL", "owner": "Root", "percent_complete": 0,
                "state": "deferred", "done_when": "Real caller appears.", "required_for_closure": False}],
            "blocking_input_tasks": ["INPUT"], "execution_packet_gaps": ["PACKET"],
            "registers": {"modules": ["one.ko"], "count": 1}, "dependency_aliases": {"ALIAS": "INPUT"}}
        self.runtime = {"state": {"worker_pid": 101, "worker_start": "111", "thread_id": "root",
            "heartbeat_at": "2026-11-10T04:59:55Z", "updated_at": "2026-11-10T04:59:55Z",
            "phase": "running", "goal": {"status": "active", "objective": "PRIVATE PROMPT"},
            "agents": {"root": {"label": "Root", "status": "inProgress", "activity": "SECRET COMMAND"},
                       "old": {"status": "inProgress", "activity": "SECRET COMMAND"}},
            "active_turns": {"root": "turn-root", "child-no-metadata": "turn-child"}},
            "watcher": {"watcher_pid": 102, "watcher_start": "222", "worker_pid": 101, "event": "heartbeat", "at": NOW.timestamp()},
            "guardian": {"pid": 103, "start": "333", "phase": "SUPERVISED"},
            "mailbox": {"last_poll_at": NOW.timestamp(), "next_poll_at": NOW.timestamp() + 600,
                "messages": {"1": {"delivery_status": "ACCEPTED"}, "2": {"delivery_status": "WAITING"}}}}

    def render(self, **kwargs):
        return subject.render_status_text(self.ledger, generated_at=NOW, **kwargs)

    def test_unavailable_workstation_is_not_zero_agents_or_milestone_completion(self):
        text = self.render(runtime=None)
        self.assertIn("Workstation runtime: UNAVAILABLE", text)
        self.assertIn("UNKNOWN, not zero", text)
        self.assertIn("milestone OPEN", text)
        self.assertIn("Counted evidence tasks: 1; verified at 100%: 1", text)
        self.assertIn("Uncounted definition/preparation/register/support tasks: 1", text)

    def test_complete_canonical_ledger_renders_every_row_once_with_fixed_counts(self):
        path = Path(__file__).resolve().parents[2] / "docs/verification/m14-m15-closure-progress.json"
        ledger = json.loads(path.read_text())
        text = subject.render_status_text(ledger, generated_at=NOW, source_commit="verified-source", runtime=None)
        for key, prefix in (("requirements", "REQUIREMENT"), ("tasks", "TASK"), ("optional_or_deferred_decisions", "OPTIONAL")):
            rendered = re.findall(r"^" + prefix + r" (\S+) \|", text, re.M)
            self.assertEqual(rendered, [row["id"] for row in ledger[key]])
        self.assertIn("Rows: 31 requirements", text)
        self.assertIn("391 tasks", text)
        self.assertIn("Counted evidence tasks: 156; verified at 100%: 73", text)
        self.assertIn("accepted files 4/6; accepted integrations 0/3", text)
        self.assertIn("accepted files 1/8; accepted integrations 0/4", text)
        self.assertLessEqual(len(text.encode()), subject.MAX_BYTES)

    def test_current_agents_are_union_of_roster_and_observed_turns(self):
        self.runtime["state"]["agents"]["root"].update(last_event_at="2026-11-10T04:59:54Z",
            quiet_seconds=6.0, retired=False, role="recorded dispatcher")
        text = self.render(runtime=self.runtime, identity_checker=lambda pid, birth: True)
        agents = re.findall(r"^AGENT (\S+) \| ([^|]+)", text, re.M)
        self.assertEqual({ident for ident, status in agents}, {"root", "old", "child-no-metadata"})
        self.assertIn("AGENT child-no-metadata | ACTIVE TURN OBSERVED | label=UNKNOWN", text)
        self.assertIn("AGENT old | SAVED / NOT VERIFIED LIVE", text)
        self.assertIn("Fresh controller snapshot active-turn count: 2", text)
        self.assertNotIn("PRIVATE PROMPT", text)
        self.assertNotIn("SECRET COMMAND", text)
        self.assertIn("WAITING=1; ACCEPTED=1; NOT_QUEUED=0", text)
        self.assertIn("last event UTC=2026-11-10T04:59:54Z", text)
        self.assertIn("controller role=Root (recorded primary thread)", text)
        self.assertIn("quiet_seconds=6.0 | retired=False | role=recorded dispatcher", text)

    def test_stale_snapshot_or_missing_identity_checks_never_claim_live_turns(self):
        for stale, checker in ((False, None), (True, lambda pid, birth: True)):
            with self.subTest(stale=stale):
                runtime = copy.deepcopy(self.runtime)
                if stale:
                    runtime["state"]["heartbeat_at"] = "2026-11-10T04:00:00Z"
                text = self.render(runtime=runtime, identity_checker=checker)
                self.assertIn("STALE OR UNVERIFIED", text)
                self.assertIn("Fresh controller snapshot active-turn count: UNKNOWN", text)
                self.assertNotIn("ACTIVE TURN OBSERVED", text)

    def test_stopped_worker_with_fresh_saved_status_is_not_current(self):
        self.runtime["state"]["phase"] = "stopped"
        self.assertNotIn("ACTIVE TURN OBSERVED", self.render(runtime=self.runtime, identity_checker=lambda p, b: True))

    def test_epoch_utc_boise_ci_and_attributed_notes(self):
        text = subject.render_status_text(self.ledger, generated_at=NOW.timestamp(),
            ci={"status": "cancelled", "summary": "182 failures; 232 errors; tracker unchanged", "raw_command": "SECRET COMMAND"},
            notes=["Verified CI observation only. api_key=private"])
        self.assertIn("2026-11-10T05:00:00Z", text)
        self.assertIn("2026-11-09T22:00:00-07:00", text)
        self.assertIn("Treat this snapshot as stale after UTC: 2026-11-10T05:15:00Z", text)
        self.assertIn("America/Boise: 2026-11-09T22:15:00-07:00", text)
        self.assertIn("REMOTE CI", text)
        self.assertIn("182 failures; 232 errors", text)
        self.assertNotIn("SECRET COMMAND", text)
        self.assertNotIn("private", text)

    def test_missing_gate_metadata_is_unknown_not_zero_credit_or_acceptance(self):
        self.ledger["requirements"] = []
        text = self.render()
        self.assertIn("accepted files UNKNOWN/1", text)
        self.assertIn("gate rows or binary acceptance metadata incomplete", text)
        self.ledger["tasks"][0].pop("owner")
        self.assertIn("tasks row 1: missing owner", self.render())

    def test_duplicate_gate_ids_and_rows_or_nonbinary_acceptance_make_counts_unknown(self):
        original = copy.deepcopy(self.ledger)
        mutations = (lambda: self.ledger["summaries"]["M14"]["original_gate_ids"].append("M14-F01"),
                     lambda: self.ledger["requirements"].append(copy.deepcopy(self.ledger["requirements"][0])),
                     lambda: self.ledger["requirements"][0].update(accepted=1))
        for mutate in mutations:
            self.ledger = copy.deepcopy(original)
            mutate()
            self.assertIn("accepted files UNKNOWN/1", self.render())

    def test_retained_stop_is_labeled_and_credentials_redacted(self):
        self.runtime["latest_stop"] = {"log_dir": "/old/run", "reason": "server_error",
             "error": {"message": "Bearer secret-token password=hidden", "code": "old"}}
        text = self.render(runtime=self.runtime)
        self.assertIn("retained/unattributed", text)
        self.assertNotIn("secret-token", text)
        self.assertNotIn("hidden", text)

    def test_atomic_write_and_oversize_failure_preserve_existing_complete_file(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "status.txt"
            result = subject.write_status_text(path, self.ledger, generated_at=NOW)
            before = path.read_bytes()
            self.assertEqual(result["bytes"], len(before))
            self.assertEqual(result["row_counts"]["tasks"], 2)
            with patch.object(subject, "MAX_BYTES", 10), self.assertRaisesRegex(ValueError, "No rows were truncated"):
                subject.write_status_text(path, self.ledger, generated_at=NOW)
            self.assertEqual(path.read_bytes(), before)
            self.assertFalse(list(path.parent.glob(".status-*.tmp")))

    def test_missing_optional_list_and_oversized_field_are_explicit(self):
        self.ledger.pop("optional_or_deferred_decisions")
        self.assertIn("optional_or_deferred_decisions: missing or malformed row list", self.render())
        self.ledger["tasks"][0]["title"] = "x" * 9000
        with self.assertRaisesRegex(ValueError, "without truncation"):
            self.render()


if __name__ == "__main__":
    unittest.main()
