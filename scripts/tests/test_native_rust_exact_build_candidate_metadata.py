#!/usr/bin/env python3
"""Cheap real-Git regression tests for exact metadata relocation."""
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest import mock

from scripts import native_rust_exact_build_candidate_metadata as relocator


class MetadataRelocationTest(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="exact-metadata-test-"))
        self.source = self.root / "source"
        self.ihk_source = self.root / "ihk-source"
        self.candidate = self.root / "candidate"
        self.ihk = self.candidate / "ihk"
        self._repo(self.source)
        self._repo(self.ihk_source)
        self._commit(self.ihk_source, "old.txt", "old\n", "old")
        self.old_ihk = self._sha(self.ihk_source)
        self._commit(self.ihk_source, "current.txt", "current\n", "current")
        self.ihk_sha = self._sha(self.ihk_source)
        subprocess.check_call(["git", "-C", str(self.ihk_source), "tag", "historical"])
        self._commit(self.source, "main.txt", "main\n", "main")
        # A gitlink exercises index parsing without requiring main blobs in the
        # relocated object store.
        subprocess.check_call(["git", "-C", str(self.source), "update-index", "--add",
                               "--cacheinfo", "160000,%s,ihk" % self.ihk_sha])
        (self.source / "link").symlink_to("main.txt")
        subprocess.check_call(["git", "-C", str(self.source), "add", "link"])
        subprocess.check_call(["git", "-C", str(self.source), "commit", "-qm", "gitlink"])
        self.main_sha = self._sha(self.source)
        subprocess.check_call(["git", "clone", "-q", "--separate-git-dir", str(self.root / "main-meta"),
                               str(self.source), str(self.candidate)])
        # clone does not materialize a gitlink; provide its exact nested repo.
        self.ihk.rmdir()
        subprocess.check_call(["git", "clone", "-q", "--separate-git-dir", str(self.root / "ihk-meta"),
                               str(self.ihk_source), str(self.ihk)])
        self.backup = self.root / "backup"
        self.evidence = self.root / "evidence"

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    @staticmethod
    def _repo(path):
        path.mkdir(parents=True)
        subprocess.check_call(["git", "init", "-q", str(path)])
        subprocess.check_call(["git", "-C", str(path), "config", "user.email", "test@example.invalid"])
        subprocess.check_call(["git", "-C", str(path), "config", "user.name", "test"])

    @staticmethod
    def _commit(repo, name, text, message):
        (repo / name).write_text(text)
        subprocess.check_call(["git", "-C", str(repo), "add", name])
        subprocess.check_call(["git", "-C", str(repo), "commit", "-qm", message])

    @staticmethod
    def _sha(repo, ref="HEAD"):
        return subprocess.check_output(["git", "-C", str(repo), "rev-parse", ref], text=True).strip()

    def _args(self, **extra):
        values = dict(main=self.candidate, ihk=self.ihk, source_main=self.source / ".git",
                      source_ihk=self.ihk_source / ".git", backup=self.backup,
                      evidence=self.evidence, main_sha=self.main_sha, ihk_sha=self.ihk_sha)
        values.update(extra)
        return type("Args", (), values)()

    def test_relocation_has_only_required_main_symlink_blobs_and_retains_ihk_history(self):
        # The explicit object source may have a different HEAD/index; only its
        # exact requested objects are consumed.
        subprocess.check_call(["git", "-C", str(self.ihk_source), "update-ref", "HEAD", self.old_ihk])
        link_mode = (self.candidate / "link").lstat().st_mode
        link_text = os.readlink(self.candidate / "link")
        result = relocator.relocate(self._args())
        self.assertEqual(result["status"], "PASS")
        self.assertTrue((self.candidate / ".git").is_dir())
        self.assertTrue((self.ihk / ".git").is_dir())
        self.assertEqual(subprocess.check_output(["git", "-C", str(self.ihk), "show", "historical:old.txt"], text=True), "old\n")
        types = subprocess.check_output(["git", "--git-dir", str(self.candidate / ".git"),
                                         "cat-file", "--batch-all-objects", "--batch-check"], text=True)
        self.assertEqual(sum(line.split()[1] == "blob" for line in types.splitlines()), 1)
        self.assertEqual(result["installed"]["main"]["symlink_blobs"], 1)
        self.assertEqual(subprocess.check_output(["git", "-C", str(self.candidate), "ls-files"], text=True).splitlines(), ["ihk", "link", "main.txt"])
        self.assertEqual((self.candidate / "link").lstat().st_mode, link_mode)
        self.assertEqual(os.readlink(self.candidate / "link"), link_text)
        # The original external/shared stores can disappear after conversion.
        self.source.rename(self.root / "source-hidden")
        self.ihk_source.rename(self.root / "ihk-source-hidden")
        (self.root / "main-meta").rename(self.root / "main-meta-hidden")
        (self.root / "ihk-meta").rename(self.root / "ihk-meta-hidden")
        self.assertEqual(self._sha(self.candidate), self.main_sha)
        self.assertEqual(self._sha(self.ihk), self.ihk_sha)
        self.assertEqual(subprocess.check_output(["git", "-C", str(self.ihk), "show", "historical:old.txt"], text=True), "old\n")
        self.assertEqual(subprocess.check_output(["git", "-C", str(self.candidate), "status", "--porcelain"], text=True), "")
        (self.candidate / "main.txt").write_text("changed\n")
        self.assertEqual(subprocess.check_output(["git", "-C", str(self.candidate), "status", "--porcelain"], text=True), " M main.txt\n")
        receipt = json.loads((self.evidence / "receipt.json").read_text())
        self.assertEqual(receipt["status"], "PASS")
        self.assertEqual(receipt["installed"]["main"]["index"],
                         str(self.candidate / ".git" / "index"))

    def test_wrong_sha_and_dirty_inputs_rejected_before_mutation(self):
        bad = self._args(main_sha="0" * 40)
        with self.assertRaises(relocator.Reject):
            relocator.relocate(bad)
        (self.candidate / "untracked").write_text("dirty")
        with self.assertRaises(relocator.Reject):
            relocator.relocate(self._args(backup=self.root / "backup2", evidence=self.root / "evidence2"))
        self.assertTrue((self.candidate / ".git").is_file())

    def test_missing_source_object_rejected_without_output(self):
        oid = self._sha(self.source)
        tree = self._sha(self.source, "HEAD^{tree}")
        raw = relocator.object_bytes(self.root / "main-meta", "commit", oid)
        self.assertTrue(raw and tree)
        objects = self.source / ".git" / "objects"
        shutil.rmtree(objects)
        objects.mkdir()
        with self.assertRaises(relocator.Reject):
            relocator.relocate(self._args(backup=self.root / "backup3", evidence=self.root / "evidence3"))
        self.assertTrue((self.candidate / ".git").is_file())

    def test_post_move_failure_restores_both_original_gitfiles(self):
        backup, evidence = self.root / "rollback-backup", self.root / "rollback-evidence"
        original_replace = relocator.os.replace

        def fail_second(source, destination):
            if Path(destination).name == "ihk.git" and Path(destination).parent == backup:
                raise OSError("injected install failure")
            return original_replace(source, destination)

        with mock.patch.object(relocator.os, "replace", side_effect=fail_second):
            with self.assertRaises(OSError):
                relocator.relocate(self._args(backup=backup, evidence=evidence))
        self.assertTrue((self.candidate / ".git").is_file())
        self.assertTrue((self.ihk / ".git").is_file())
        receipt = json.loads((evidence / "receipt.json").read_text())
        self.assertEqual(receipt["rollback"], "restored")


if __name__ == "__main__":
    unittest.main()
