"""Temporary queue/proc fixtures and fake callbacks; no RPC or live target reads."""
import copy
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import os_goal_source_work as work

GIB, MIB = 1024 ** 3, 1024 ** 2


class OriginalReceipts:
    def __init__(self, binding, now):
        self.binding, self.now = binding, now
        self.turn_calls, self.account_calls = [], []
        self.terminal = {"root_thread_id": binding["thread_id"], "invocation": binding["invocation"],
                         "thread_id": "blocked-child", "turn_id": "original-turn", "status": "failed"}
        self.account = {"decision": "CLEAR_SOURCE_DISPATCH_ONLY", "binding": binding,
                        "observed_utc_ns": now[0], "observed_mono_ns": now[1], "receipt_sha256": "a" * 64}

    def turn(self, thread, turn):
        self.turn_calls.append((thread, turn))
        return copy.deepcopy(self.terminal)

    def account_guard(self, binding, utc, mono):
        self.account_calls.append((binding, utc, mono))
        return copy.deepcopy(self.account)


class SourceWorkTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="os-goal-source-fixture-")
        self.addCleanup(temporary.cleanup)
        self.base = Path(temporary.name)
        self.repo, self.control, self.proc = [self.base / name for name in ("repo", "control", "proc")]
        for path in (self.repo, self.control, self.proc, self.control / "log"):
            path.mkdir(mode=0o700, parents=True, exist_ok=True)
        self.pid, self.child, self.payload = os.getpid(), os.getpid() + 100000, os.getpid() + 200000
        self.binding = {"thread_id": "root", "invocation": "this-invocation", "worker_pid": self.pid,
                        "worker_start": "100", "log_dir": str(self.control / "log"), "credit_run_id": "finite-run"}
        self.now = (9_000_000_000_000_000_000, 100_000_000_000)
        self.source = self.repo / "changed.rs"
        self.source.write_text("fn original_source() {}\n")
        raw = self.source.read_bytes()
        self.text, self.source_id = "Prepare only the isolated Rust source change; do not execute it.", "explicit-owner-source-1"
        self.spec = {
            "task_id": "new-source-task", "original_check": "M15-F05-original-behavior", "kind": "source",
            "blocker": {"task_id": "parked-publication", "thread_id": "blocked-child", "turn_id": "original-turn",
                        "hold_fields": ["source_hold", "resource_hold"]},
            "inputs": [{"id": "changed-source", "kind": "source", "path": str(self.source),
                        "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}],
            "write_paths": [str(self.repo / "new.rs")],
            "limits": {"source_overhead_reserve_bytes": 64 * MIB, "host_floor_bytes": 17 * GIB,
                       "scratch_floor_bytes": 13 * GIB, "max_age_ns": 25_000_000_000}}
        self.attachment = work.prepare_attachment(self.spec, binding=self.binding, source_id=self.source_id,
                                                  text=self.text, allowed_roots=[self.repo])
        digest = hashlib.sha256(self.source_id.encode()).hexdigest()
        self.item = {"id": "source-" + digest, "source_id": self.source_id, "text": self.text,
                     "text_sha256": hashlib.sha256(self.text.encode()).hexdigest(),
                     "submitted_at": "2026-11-13T00:00:00+00:00", "source_work": self.attachment}
        self.registry = self.control / "instructions" / "sources" / (digest + ".json")
        self.sending = self.control / "instructions" / "sending" / (self.item["id"] + ".json")
        self.publish()
        self.process(self.pid, "100", 1, 128 * MIB, [self.child, self.payload])
        self.process(self.child, "101", self.pid, 64 * MIB, [])
        # A held payload contributes its entire planning charge. Its status,
        # account/caps and descendants are deliberately absent from this fixture.
        payload = self.proc / str(self.payload)
        payload.mkdir()
        (payload / "stat").write_text(self.stat(self.payload, "200", self.pid))
        (self.proc / "meminfo").write_text("MemAvailable: {} kB\n".format(26 * GIB // 1024))
        self.retained = [
            {"owner": "same-root", "state": "UNKNOWN", "planning_bytes": 2 * GIB, "jobs": 1,
             "process_roots": [{"pid": self.payload, "start": "200"}]},
            {"owner": "same-root", "state": "RETAINED", "planning_bytes": 256 * MIB, "jobs": 1,
             "process_roots": []}]
        self.scopes = [{"scope": "operation", "source_access": "disjoint_paths",
                        "protected_paths": [str(self.base / "held-operation")]}]
        self.state = dict(thread_id="root", worker_pid=self.pid, worker_start="100",
                          log_dir=self.binding["log_dir"], active_turns={}, stop_reason=None,
                          source_hold=True, resource_hold=True)
        self.goal = {"threadId": "root", "status": "blocked", "objective": "Original M14 then M15"}
        self.receipts = OriginalReceipts(self.binding, self.now)

    @staticmethod
    def stat(pid, start, parent):
        fields = ["S", str(parent)] + ["0"] * 18
        fields[19] = start
        return "{} (fixture) {}\n".format(pid, " ".join(fields))

    def process(self, pid, start, parent, rss, children, cpus="0,6-7"):
        path = self.proc / str(pid)
        (path / "task" / str(pid)).mkdir(parents=True, exist_ok=True)
        (path / "stat").write_text(self.stat(pid, start, parent))
        (path / "status").write_text("VmRSS: {} kB\nCpus_allowed_list: {}\n".format(rss // 1024, cpus))
        (path / "task" / str(pid) / "children").write_text(" ".join(map(str, children)))

    @staticmethod
    def private_json(path, value):
        path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        path.write_text(json.dumps(value, sort_keys=True))
        path.chmod(0o600)

    def publish(self):
        self.private_json(self.registry, {"status": "queued", "item": self.item})
        self.private_json(self.sending, self.item)

    def validate(self, **changes):
        args = dict(directory=self.control, binding=self.binding, goal=self.goal, state=self.state,
                    allowed_roots=[self.repo], terminal_turn_lookup=self.receipts.turn,
                    account_guard=self.receipts.account_guard,
                    process_roots=[{"pid": self.pid, "start": "100", "role": "controller"}],
                    retained_charges=self.retained, exclusive_scopes=self.scopes, proc_root=self.proc,
                    queue_reader=lambda path: json.loads(path.read_text()),
                    scratch_path=self.base, clock=lambda: self.now, affinity_reader=lambda pid: {0, 6, 7},
                    disk_usage=lambda path: SimpleNamespace(free=32 * GIB))
        args.update(changes)
        return work.validate_registered_source_work(self.item, **args)

    def test_existing_source_queue_actual_callbacks_and_fake_proc_produce_only_source_context(self):
        before = copy.deepcopy((self.state, self.retained, self.item))
        result = self.validate()
        self.assertEqual(self.receipts.turn_calls, [("blocked-child", "original-turn")])
        self.assertEqual(len(self.receipts.account_calls), 1)
        self.assertEqual(result["resources"]["retained_bytes"], 2 * GIB + 256 * MIB)
        self.assertEqual(result["resources"]["retained_jobs"], 2)
        self.assertEqual(result["resources"]["measured_overhead_bytes"], 192 * MIB)
        self.assertEqual(result["resources"]["accounted_total_bytes"], 2 * GIB + 512 * MIB)
        self.assertEqual(result["payload_jobs_created"], 0)
        self.assertFalse(result["release_authorized"])
        self.assertFalse(result["native_or_payload_admission"])
        self.assertTrue(result["repair_context"]["blocker"]["runtime_resources_retained"])
        self.assertEqual((self.state, self.retained, self.item), before)
        self.assertFalse((self.proc / str(self.payload) / "status").exists())

    def test_persisted_booleans_cannot_replace_registered_sending_item_or_source_bytes(self):
        self.state["repair_context"] = {"account_gate_clear": True, "source_overhead_accounted": True}
        self.registry.unlink()
        with self.assertRaises(ValueError):
            self.validate()
        self.publish()
        self.source.write_text("changed after registration\n")
        with self.assertRaises(ValueError):
            self.validate()
        self.assertEqual(self.receipts.account_calls, [])

    def test_wrong_root_text_or_attachment_and_unfinished_original_turn_are_refused(self):
        for field in ("invocation", "thread_id", "credit_run_id"):
            binding = dict(self.binding, **{field: "other"})
            with self.assertRaises(ValueError):
                self.validate(binding=binding)
        self.receipts.terminal["status"] = "inProgress"
        with self.assertRaises(ValueError):
            self.validate()
        self.receipts.terminal["status"] = "failed"
        self.item["text"] += " mutated"
        self.publish()
        with self.assertRaises(ValueError):
            self.validate()

    def test_unknown_global_exclusivity_or_shared_source_footprint_refuses(self):
        for scope in ({"scope": "UNKNOWN"}, {"scope": "global", "source_access": "disjoint_paths"},
                      {"scope": "operation", "source_access": "disjoint_paths", "protected_paths": [str(self.repo)]}):
            with self.subTest(scope=scope), self.assertRaises(ValueError):
                self.validate(exclusive_scopes=[scope])
        with self.assertRaises(ValueError):
            self.validate(retained_charges=None)

    def test_native_affinity_missing_rss_or_process_reuse_never_invents_headroom(self):
        with self.assertRaises(ValueError):
            self.validate(affinity_reader=lambda pid: set(range(8)))
        self.process(self.child, "101", self.pid, 64 * MIB, [], cpus="2-5")
        with self.assertRaises(ValueError):
            self.validate()
        self.process(self.child, "101", self.pid, 64 * MIB, [])
        (self.proc / str(self.child) / "status").write_text("Cpus_allowed_list: 0,6-7\n")
        with self.assertRaises(ValueError):
            self.validate()

    def test_overhead_reserve_counts_but_creates_no_payload_job(self):
        self.spec["limits"]["source_overhead_reserve_bytes"] = 2 * GIB
        self.item["source_work"] = work.prepare_attachment(self.spec, binding=self.binding,
            source_id=self.source_id, text=self.text, allowed_roots=[self.repo])
        self.publish()
        with self.assertRaisesRegex(ValueError, "4GiB"):
            self.validate()

    def test_missing_stale_account_and_user_pause_override_source_readiness(self):
        self.receipts.account["decision"] = "UNKNOWN"
        with self.assertRaises(ValueError):
            self.validate()
        self.receipts.account["decision"] = "CLEAR_SOURCE_DISPATCH_ONLY"
        self.receipts.account["observed_utc_ns"] -= 25_000_000_001
        with self.assertRaises(ValueError):
            self.validate()
        self.receipts.account["observed_utc_ns"] = self.now[0]
        for field in ("account_hold", "user_pause", "budget_unknown"):
            state = dict(self.state, **{field: True})
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.validate(state=state)

    def test_source_registration_rejects_payload_kind_and_outside_paths(self):
        for kind in ("native", "payload", "test_execution"):
            with self.assertRaises(ValueError):
                work.prepare_attachment(dict(self.spec, kind=kind), binding=self.binding,
                    source_id=self.source_id, text=self.text, allowed_roots=[self.repo])
        with self.assertRaises(ValueError):
            work.prepare_attachment(dict(self.spec, write_paths=[str(self.control / "state.json")]),
                binding=self.binding, source_id=self.source_id, text=self.text, allowed_roots=[self.repo])

    def test_attachment_adds_no_instruction_or_queue_record_size_cap(self):
        self.text = "source-only instruction " + "x" * 100000
        self.item["text"] = self.text
        self.item["text_sha256"] = hashlib.sha256(self.text.encode()).hexdigest()
        self.item["source_work"] = work.prepare_attachment(self.spec, binding=self.binding,
            source_id=self.source_id, text=self.text, allowed_roots=[self.repo])
        self.publish()  # Fixture publication; production uses its existing source-ID dedup.
        self.assertGreater(self.sending.stat().st_size, 65536)
        self.assertEqual(self.validate()["payload_jobs_created"], 0)


if __name__ == "__main__":
    unittest.main()
