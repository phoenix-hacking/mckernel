"""Bounded synthetic tests for scratch18 pre-owner recovery.

No production paths are mutated and no root, Docker, network, build, or guest
operation is performed.
"""
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "docs/verification/evidence/native-exact-scratch18-preowner-recovery-20261001.py"

def load():
    spec = importlib.util.spec_from_file_location("scratch18_preowner", SOURCE)
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); return mod

class Recovery(unittest.TestCase):
    def setUp(self):
        self.m = load(); self.tmp = tempfile.TemporaryDirectory(); self.root = Path(self.tmp.name)
        self.attempt = self.root / "exclusion.json"; self.shared = self.root / "shared.lock"
        self.attempt.write_bytes(b"attempt-retained\n"); self.shared.write_bytes(b"shared-retained\n")
        for p in (self.attempt, self.shared): os.chmod(p, 0o600)
        def rec(p):
            st = p.stat(); return {"path": str(p), "inode": st.st_ino, "sha256": self.m.sha(p.read_bytes()),
                                   "mode": "0600", "uid": st.st_uid, "gid": st.st_gid}
        self.failure = {"owner_identity": {"pid": 3288332, "starttime": "107474009", "current_state": "absent"},
                        "retained_locks": {"attempt": rec(self.attempt), "shared": rec(self.shared)},
                        "postflight": {"output": {"device": 1831, "inode": 3571962, "files": 0},
                                        "evidence": {"device": 1831, "inode": 3571963, "files": 0},
                                        "relevant_processes": 0, "new_container": False,
                                        "build_lease": "absent"}}
        self.failure["request"] = {"path": str(self.root / "derived-request"), "sha256": "80de5f1c02867bcbee69752e186f7fc11d201c2df3c78887ea08aa85f92e2bd7", "inode": 90729, "mode": "0600", "uid": 1000, "gid": 1000, "normalized_sha256": "3312fb6e6297ec1abae6836720c6bb1c6c49d958a48acf665d9cc4070b547c06"}
        self.obs_data = {"authenticated": True, "wrapper_sha256": self.m.WRAPPER_SHA256,
                    "processes": [], "docker": {"new_container": False}, "lease": {"present": False},
                    "capacity": {"sufficient": True}, "artifacts": self.failure["postflight"],
                    "owner": self.failure["owner_identity"], "request": self.failure["request"], "boot": {"boot_id": "c733d83b-test"}}
        self.obs = self.m.seal_observations(self.obs_data)
        self.archives = self.root / "archives"

    def tearDown(self): self.tmp.cleanup()

    def test_validate_only_positive_and_default_execute_refuses(self):
        self.assertEqual(self.m.recover(self.failure, self.obs, self.archives)["status"], "PASS_VALIDATE_ONLY")
        self.assertFalse(self.archives.exists())
        with self.assertRaisesRegex(self.m.Refusal, "production-observer-not-installed"):
            self.m.recover(self.failure, execute=True)

    def test_execute_archives_attempt_then_shared_and_journals(self):
        result = self.m.recover(self.failure, self.obs, self.archives, execute=True)
        self.assertEqual(result["status"], "PASS"); self.assertFalse(self.attempt.exists()); self.assertFalse(self.shared.exists())
        self.assertEqual([Path(x).read_bytes() for x in result["archives"]], [b"attempt-retained\n", b"shared-retained\n"])
        self.assertTrue(Path(result["journal"]).exists()); self.assertTrue(list(self.archives.glob("recovery-*.terminal.json")))

    def test_rejects_replacement_pid_observation_container_lease_and_output(self):
        for change in ({"owner": {**self.failure["owner_identity"], "current_state": "running"}},
                       {"processes": [{"pid": 99}]}, {"docker": {"new_container": True}},
                       {"lease": {"present": True}}, {"artifacts": {**self.failure["postflight"], "relevant_processes": 1}}):
            bad = dict(self.obs_data); bad.update(change)
            with self.assertRaises(self.m.Refusal): self.m.recover(self.failure, self.m.seal_observations(bad), self.archives)

    def test_rejects_wrapper_and_incomplete_census(self):
        bad = dict(self.obs_data); bad["wrapper_sha256"] = "f" * 64
        with self.assertRaisesRegex(self.m.Refusal, "wrapper-hash"): self.m.recover(self.failure, self.m.seal_observations(bad), self.archives)
        bad = dict(self.obs_data); del bad["capacity"]
        with self.assertRaisesRegex(self.m.Refusal, "incomplete-census-capacity"): self.m.recover(self.failure, self.m.seal_observations(bad), self.archives)

    def test_rejects_lock_replacement_and_link(self):
        self.attempt.unlink(); self.attempt.symlink_to(self.shared)
        with self.assertRaises(self.m.Refusal): self.m.recover(self.failure, self.obs, self.archives)

    def test_collision_and_first_rename_failure_are_fail_closed(self):
        with mock.patch.object(self.m.secrets, "token_hex", return_value="fixed"):
            self.archives.mkdir(); (self.archives / "exclusion.json.attempt.fixed.archive").write_bytes(b"other")
            with self.assertRaisesRegex(self.m.Refusal, "archive-collision"): self.m.recover(self.failure, self.obs, self.archives, execute=True)
        self.assertTrue(self.attempt.exists()); self.assertTrue(self.shared.exists())
        with self.assertRaisesRegex(self.m.Refusal, "archive-rename-failure"):
            self.m.recover(self.failure, self.obs, self.archives, execute=True, fault="rename")
        self.assertTrue(self.attempt.exists()); self.assertTrue(self.shared.exists())

    def test_second_rename_failure_leaves_shared_last(self):
        original = self.m._archive_one
        def fail_second(source, record, directory, label, fault=None):
            if label == "shared": raise self.m.Refusal("archive-rename-failure")
            return original(source, record, directory, label, fault)
        with mock.patch.object(self.m, "_archive_one", side_effect=fail_second), self.assertRaises(self.m.Refusal):
            self.m.recover(self.failure, self.obs, self.archives, execute=True)
        self.assertFalse(self.attempt.exists()); self.assertTrue(self.shared.exists())

    def test_replay_is_refused_and_no_secrets(self):
        with self.assertRaisesRegex(self.m.Refusal, "replay-refused"): self.m.replay(self.root / "terminal.json")
        text = SOURCE.read_text()
        self.assertNotIn("password", text.lower()); self.assertNotIn("token =", text.lower())

if __name__ == "__main__": unittest.main()
