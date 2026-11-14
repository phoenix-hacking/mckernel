"""Bounded real-Git tests for the supplemental libdwarf gitlink contract."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


owner = load("gitlink_owner", ROOT / "scripts/native_rust_exact_mckernel_image_container_owner.py")
offline = load("gitlink_offline", ROOT / "scripts/native_rust_exact_mckernel_image_offline.py")
prep = load("gitlink_prepare", ROOT / "scripts/native_rust_exact_mckernel_gitlink_prepare.py")


class GitlinkContract(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.repo = self.root / "libdwarf-source"
        self.repo.mkdir()
        self.git("init", "-q")
        self.git("config", "user.name", "fixture")
        self.git("config", "user.email", "fixture@example.invalid")
        (self.repo / "README").write_text("fixture\n")
        (self.repo / "src").mkdir()
        (self.repo / "src" / "dwarf.c").write_text("int dwarf_fixture(void) { return 7; }\n")
        self.git("add", ".")
        self.git("commit", "-qm", "fixture")
        self.commit = self.git("rev-parse", "HEAD").strip()
        self.tree = self.git("rev-parse", "HEAD^{tree}").strip()
        self.checkout = self.root / "checkout"
        self.git_root("clone", "--no-local", str(self.repo), str(self.checkout))
        self.git_at(self.checkout, "remote", "remove", "origin")
        self.base = self.root / "base.json"
        self.base.write_text(json.dumps({"candidate_sha": "a" * 40, "ihk_sha": "b" * 40,
                                         "gitlinks": {prep.LIBDWARF_PATH: self.commit}}, sort_keys=True) + "\n")
        self.supplemental = self.root / "supplemental.json"
        self.document = prep.prepare(source=self.repo, checkout=self.root / "prepared",
                                     output=self.supplemental, base_manifest=self.base,
                                     candidate_sha="a" * 40, ihk_sha="b" * 40,
                                     expected_commit=self.commit)
        # Git's checkout mode follows the process umask; normalize the
        # reviewed regular files to the contract's explicit 0644 mode.
        for relative, row in self.row_files().items():
            (self.root / "prepared" / relative).chmod(int(row["mode"], 8) & 0o7777)
        self.row = self.document["consumed_gitlinks"][prep.LIBDWARF_PATH]

    def row_files(self):
        return self.document["consumed_gitlinks"][prep.LIBDWARF_PATH]["files"]

    def git(self, *args):
        return self.git_at(self.repo, *args)

    @staticmethod
    def git_root(*args):
        return subprocess.run(["/usr/bin/git", *args], check=True, text=True,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE).stdout

    @staticmethod
    def git_at(root, *args):
        return subprocess.run(["/usr/bin/git", "-C", str(root), *args], check=True,
                              text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE).stdout

    def owner_ok(self, document=None, checkout=None):
        return owner._validate_gitlink_manifest(document or self.document, self.supplemental,
                                                checkout or self.root / "prepared", self.base,
                                                "a" * 40, "b" * 40)

    def offline_ok(self, document=None):
        source = self.root / "source"
        target = source / "executer/user/lib/libdwarf/libdwarf"
        target.parent.mkdir(parents=True)
        shutil.copytree(self.root / "prepared", target)
        manifest = self.root / "offline.json"
        manifest.write_text(json.dumps(document or self.document, sort_keys=True) + "\n")
        tool = {"path": "/usr/bin/git", "sha256": hashlib.sha256(Path("/usr/bin/git").read_bytes()).hexdigest()}
        return offline._validate_gitlink_closure(
            source, manifest, self.base, "a" * 40, "b" * 40, tool)

    def test_valid_exact_closure_owner_and_offline(self):
        self.assertEqual(self.owner_ok(), self.root / "prepared")
        self.assertEqual(self.offline_ok()["schema"], self.document["schema"])

    def test_identity_and_manifest_substitutions_rejected(self):
        for field, value in (("base_manifest_sha256", "0" * 64), ("candidate_sha", "c" * 40),
                             ("ihk_sha", "c" * 40)):
            doc = copy.deepcopy(self.document); doc[field] = value
            with self.assertRaises(owner.OwnerError): self.owner_ok(doc)
        for field in ("commit", "tree"):
            doc = copy.deepcopy(self.document); doc["consumed_gitlinks"][prep.LIBDWARF_PATH][field] = "0" * 40
            with self.assertRaises(owner.OwnerError): self.owner_ok(doc)

    def test_file_mode_blob_sha_metadata_and_set_substitutions_rejected(self):
        cases = []
        doc = copy.deepcopy(self.document); doc["consumed_gitlinks"][prep.LIBDWARF_PATH]["files"]["README"]["blob"] = "0" * 40; cases.append(doc)
        doc = copy.deepcopy(self.document); doc["consumed_gitlinks"][prep.LIBDWARF_PATH]["files"]["README"]["sha256"] = "0" * 64; cases.append(doc)
        doc = copy.deepcopy(self.document); doc["consumed_gitlinks"][prep.LIBDWARF_PATH]["files"]["README"]["mode"] = "100755"; cases.append(doc)
        doc = copy.deepcopy(self.document); doc["consumed_gitlinks"][prep.LIBDWARF_PATH]["git_metadata"]["HEAD"]["size"] += 1; cases.append(doc)
        doc = copy.deepcopy(self.document); doc["consumed_gitlinks"][prep.LIBDWARF_PATH]["files"]["extra"] = doc["consumed_gitlinks"][prep.LIBDWARF_PATH]["files"]["README"]; cases.append(doc)
        for bad in cases:
            with self.assertRaises(owner.OwnerError): self.owner_ok(bad)

    def test_path_traversal_and_extra_tracked_or_ignored_file_rejected(self):
        doc = copy.deepcopy(self.document); files = doc["consumed_gitlinks"][prep.LIBDWARF_PATH]["files"]
        files["../escape"] = files.pop("README")
        with self.assertRaises(owner.OwnerError): self.owner_ok(doc)
        (self.root / "prepared" / "untracked").write_text("bad\n")
        with self.assertRaises(owner.OwnerError): self.owner_ok()
        (self.root / "prepared" / "untracked").unlink()
        (self.root / "prepared" / ".gitignore").write_text("ignored\n")
        (self.root / "prepared" / "ignored").write_text("bad\n")
        with self.assertRaises(owner.OwnerError): self.owner_ok()
        (self.root / "prepared" / "tracked-extra").write_text("bad\n")
        self.git_at(self.root / "prepared", "add", "tracked-extra")
        self.git_at(self.root / "prepared", "commit", "-qm", "extra")
        with self.assertRaises(owner.OwnerError): self.owner_ok()

    def test_authenticated_git_descriptor_and_root_contracts(self):
        descriptor = {"path": "/usr/bin/git", "sha256": hashlib.sha256(Path("/usr/bin/git").read_bytes()).hexdigest()}
        self.assertEqual(self.offline_ok(), self.document)
        bad = dict(descriptor, sha256="0" * 64)
        with self.assertRaises(offline.ImageBuildError): offline._tool_descriptor(bad, "Git")
        with self.assertRaises(owner.OwnerError): owner._disjoint((self.root / "prepared", self.root / "prepared" / "nested"))
        self.assertEqual(owner._disjoint((self.root / "prepared", self.root / "other")), None)

    def test_clean_filter_and_skip_worktree_cannot_hide_raw_byte_drift(self):
        checkout = self.root / "prepared"
        self.git_at(checkout, "config", "core.autocrlf", "true")
        readme = checkout / "README"
        readme.write_bytes(b"fixture\r\n")
        self.git_at(checkout, "update-index", "--skip-worktree", "README")
        # Rebind every mutable supplemental value an attacker controlled in
        # the old contract.  The pinned HEAD tree still carries the LF blob,
        # so --no-filters must reject the consumed CRLF bytes.
        forged = copy.deepcopy(self.document)
        row = forged["consumed_gitlinks"][prep.LIBDWARF_PATH]
        row["files"]["README"]["sha256"] = hashlib.sha256(b"fixture\r\n").hexdigest()
        row["git_metadata"] = prep._metadata_inventory(checkout / ".git")
        self.assertEqual(self.git_at(checkout, "status", "--porcelain=v1").strip(), "")
        with self.assertRaisesRegex(owner.OwnerError, "worktree differs|inventory differs"):
            self.owner_ok(forged)


if __name__ == "__main__":
    unittest.main()
