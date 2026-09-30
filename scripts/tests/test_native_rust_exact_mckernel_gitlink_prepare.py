"""Focused real-Git coverage for libdwarf gitlink preparation."""
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("gitlink_prepare", ROOT / "scripts/native_rust_exact_mckernel_gitlink_prepare.py")
prepare = importlib.util.module_from_spec(spec); spec.loader.exec_module(prepare)


class LibdwarfPrepare(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name); self.source = self.root / "source"; self.source.mkdir()
        self.git("init", "-q"); self.git("config", "user.name", "Fixture"); self.git("config", "user.email", "fixture@example.invalid")
        (self.source / "dwarf.c").write_text("int dwarf;\n"); (self.source / "dwarf.c").chmod(0o644)
        (self.source / "run.sh").write_text("#!/bin/sh\nexit 0\n"); (self.source / "run.sh").chmod(0o755)
        self.git("add", "."); self.git("commit", "-qm", "libdwarf"); self.commit = self.git("rev-parse", "HEAD").decode().strip()
        self.candidate = "1" * 40; self.ihk = "2" * 40; self.base = self.root / "base.json"
        self.base.write_text(json.dumps({"candidate_sha": self.candidate, "ihk_sha": self.ihk, "gitlinks": {prepare.LIBDWARF_PATH: self.commit}}))

    def git(self, *args, cwd=None):
        return subprocess.run(["git", "-C", str(cwd or self.source), *args], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE).stdout

    def invoke(self, **kwargs):
        args = dict(source=self.source, checkout=self.root / "checkout", output=self.root / "out.json", base_manifest=self.base, candidate_sha=self.candidate, ihk_sha=self.ihk, expected_commit=self.commit)
        args.update(kwargs); return prepare.prepare(**args)

    def test_fresh_full_commit_manifest_binds_modes_blobs_sha256_and_git_metadata(self):
        doc = self.invoke(); row = doc["consumed_gitlinks"][prepare.LIBDWARF_PATH]
        self.assertEqual(row["commit"], self.commit); self.assertEqual(row["files"]["dwarf.c"]["mode"], "100644"); self.assertEqual(row["files"]["run.sh"]["mode"], "100755")
        self.assertEqual(row["files"]["dwarf.c"]["sha256"], hashlib.sha256(b"int dwarf;\n").hexdigest()); self.assertIn("HEAD", row["git_metadata"]); self.assertIn("index", row["git_metadata"])
        self.assertEqual(doc["base_manifest_sha256"], hashlib.sha256(self.base.read_bytes()).hexdigest()); self.assertEqual((self.root / "out.json").stat().st_mode & 0o777, 0o600)

    def test_wrong_commit_and_base_gitlink_mismatch_rejected(self):
        with self.assertRaisesRegex(prepare.GitlinkPreparationError, "exact libdwarf commit|lacks exact|git command failed"): self.invoke(expected_commit="3" * 40)
        self.base.write_text(json.dumps({"candidate_sha": self.candidate, "ihk_sha": self.ihk, "gitlinks": {prepare.LIBDWARF_PATH: "3" * 40}}))
        with self.assertRaisesRegex(prepare.GitlinkPreparationError, "base manifest gitlink"):
            self.invoke(checkout=self.root / "checkout-2", output=self.root / "out-2.json")

    def test_dirty_and_ignored_extras_are_rejected_by_inventory(self):
        (self.source / "extra").write_text("x")
        with self.assertRaises(prepare.GitlinkPreparationError): prepare.inventory(self.source)
        (self.source / "extra").unlink(); (self.source / ".gitignore").write_text("ignored\n"); self.git("add", ".gitignore"); self.git("commit", "-qm", "ignore"); (self.source / "ignored").write_text("x")
        with self.assertRaisesRegex(prepare.GitlinkPreparationError, "dirty|ignored"): prepare.inventory(self.source)

    def test_staged_unstaged_mode_and_missing_file_rejected(self):
        (self.source / "dwarf.c").write_text("changed\n"); self.git("add", "dwarf.c")
        with self.assertRaises(prepare.GitlinkPreparationError): prepare.inventory(self.source)
        self.git("checkout", "--", "."); self.git("update-index", "--chmod=+x", "dwarf.c")
        with self.assertRaises(prepare.GitlinkPreparationError): prepare.inventory(self.source)
        (self.source / "dwarf.c").unlink()
        with self.assertRaises(prepare.GitlinkPreparationError): prepare.inventory(self.source)

    def test_symlink_nested_gitlink_and_path_traversal_rejected(self):
        (self.source / "dwarf.c").unlink(); (self.source / "dwarf.c").symlink_to("run.sh")
        with self.assertRaisesRegex(prepare.GitlinkPreparationError, "not regular|symlink|dirty"): prepare.inventory(self.source)
        with self.assertRaises(prepare.GitlinkPreparationError): prepare._safe_rel("../escape")
        with self.assertRaises(prepare.GitlinkPreparationError): prepare._safe_rel("a//b")
        self.git("checkout", "--", "."); self.git("update-index", "--add", "--cacheinfo", "160000," + self.commit + ",nested"); self.git("commit", "-qm", "nested")
        with self.assertRaisesRegex(prepare.GitlinkPreparationError, "unsupported|not regular|dirty"): prepare.inventory(self.source)

    def test_external_git_metadata_alternates_rejected(self):
        meta = self.source / ".git"; (meta / "objects/info").mkdir(parents=True, exist_ok=True); (meta / "objects/info/alternates").write_text(str(self.root / "objects"))
        with self.assertRaisesRegex(prepare.GitlinkPreparationError, "external|replacement|git command failed"): prepare.inventory(self.source)
        (meta / "objects/info/alternates").unlink(); (meta / "shallow").write_text(self.commit + "\n")
        with self.assertRaisesRegex(prepare.GitlinkPreparationError, "external|replacement|shallow"): prepare.inventory(self.source)
        (meta / "shallow").unlink(); (meta / "refs/replace").mkdir(parents=True); (meta / "refs/replace/dead").write_text(self.commit + "\n")
        with self.assertRaisesRegex(prepare.GitlinkPreparationError, "external|replacement"): prepare.inventory(self.source)

    def test_fresh_output_checkout_and_identity_requirements(self):
        self.invoke()
        with self.assertRaisesRegex(prepare.GitlinkPreparationError, "fresh"): self.invoke()
        with self.assertRaisesRegex(prepare.GitlinkPreparationError, "fresh"):
            prepare.prepare(source=self.source, checkout=Path("relative"), output=self.root / "x", base_manifest=self.base, candidate_sha=self.candidate, ihk_sha=self.ihk, expected_commit=self.commit)


if __name__ == "__main__": unittest.main()
