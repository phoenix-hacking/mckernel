"""Source-only restoration using real Git commits, bundles and local transport.

These fixtures never build IHK or execute anything from a recovered checkout.
The small synthetic history tests preservation and failure cases without network.
"""
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

from scripts.restore_ihk_source import RestoreError, git, restore


class RestoreIhkSourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.work = tempfile.TemporaryDirectory(prefix="ihk-source-fixture-")
        cls.addClassCleanup(cls.work.cleanup)
        root = Path(cls.work.name)
        cls.source = root / "source"
        cls.parent = root / "parent"
        for repo in (cls.source, cls.parent):
            repo.mkdir()
            git(repo, "init", "--quiet")
            git(repo, "config", "user.name", "Source fixture")
            git(repo, "config", "user.email", "fixture@example.invalid")
        cls.commits = []
        for index in range(3):
            (cls.source / "source.txt").write_text(f"source revision {index}\n")
            git(cls.source, "add", "source.txt")
            git(cls.source, "-c", "core.hooksPath=/dev/null", "commit", "--quiet", "-m", f"source {index}")
            cls.commits.append(git(cls.source, "rev-parse", "HEAD").decode().strip())
        cls.expected_tree = git(cls.source, "rev-parse", "HEAD^{tree}").decode().strip()
        bundles = []
        for index in (1, 2):
            path = f"evidence/source-{index}.bundle"
            bundle = cls.parent / path
            bundle.parent.mkdir(exist_ok=True)
            ref = f"refs/heads/bundle-{index}"
            git(cls.source, "update-ref", ref, cls.commits[index])
            git(cls.source, "bundle", "create", str(bundle), ref, f"^{cls.commits[index-1]}")
            oid = git(cls.parent, "hash-object", str(bundle)).decode().strip()
            bundles.append({"path": path, "blob": oid, "tip": cls.commits[index]})
        cls.manifest = {
            "version": 1,
            "base": {"url": "https://github.com/ihkmckernel/ihk.git", "commit": cls.commits[0]},
            "bundles": bundles,
        }
        manifest_path = cls.parent / "scripts/ihk_source_bundles.json"
        manifest_path.parent.mkdir()
        manifest_path.write_text(json.dumps(cls.manifest))
        git(cls.parent, "add", "scripts", "evidence")
        git(cls.parent, "update-index", "--add", "--cacheinfo", f"160000,{cls.commits[-1]},ihk")
        git(cls.parent, "-c", "core.hooksPath=/dev/null", "commit", "--quiet", "-m", "pinned source bundles")
        # Remove working files: restoration must read committed Git blobs.
        for bundle in bundles:
            (cls.parent / bundle["path"]).unlink()

    def setUp(self):
        self.work = tempfile.TemporaryDirectory(prefix="ihk-source-case-")
        self.addCleanup(self.work.cleanup)
        self.root = Path(self.work.name)
        self.destination = self.root / "ihk"

    def restore(self, manifest=None):
        path = None
        if manifest is not None:
            path = self.root / "manifest.json"
            path.write_text(json.dumps(manifest))
        return restore(self.parent, self.destination, self.source, path)

    def manifest_copy(self):
        return json.loads(json.dumps(self.manifest))

    def clone_source(self):
        result = subprocess.run(
            ["git", "clone", "--quiet", "--no-hardlinks", str(self.source), str(self.destination)],
            capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_reconstructs_from_committed_blobs_and_empty_destination(self):
        self.destination.mkdir()
        target, changed = self.restore()
        self.assertEqual(target, self.commits[-1])
        self.assertTrue(changed)
        self.assertEqual(git(self.destination, "rev-parse", "HEAD^{tree}").decode().strip(), self.expected_tree)
        self.assertEqual((self.destination / "source.txt").read_text(), "source revision 2\n")
        self.assertEqual(git(self.destination, "status", "--porcelain"), b"")
        self.assertEqual(list(self.root.glob(".ihk-source-*")), [])

    def test_exact_clean_checkout_is_unchanged_noop(self):
        self.clone_source()
        head = self.destination / ".git/HEAD"
        before = (head.read_bytes(), head.stat().st_mtime_ns)
        self.assertEqual(self.restore(), (self.commits[-1], False))
        self.assertEqual((head.read_bytes(), head.stat().st_mtime_ns), before)

    def test_dirty_working_manifest_does_not_change_committed_chain(self):
        working = self.parent / "scripts/ihk_source_bundles.json"
        before = working.read_bytes()
        try:
            working.write_text('{"version": "local edit must be ignored"}')
            self.assertEqual(self.restore(), (self.commits[-1], True))
            self.assertEqual((self.destination / "source.txt").read_text(), "source revision 2\n")
            self.assertEqual(working.read_text(), '{"version": "local edit must be ignored"}')
        finally:
            working.write_bytes(before)

    def test_sparse_checkout_is_refused_without_populating_files(self):
        self.clone_source()
        git(self.destination, "sparse-checkout", "set", "--no-cone", "missing-path")
        tracked = self.destination / "source.txt"
        self.assertFalse(tracked.exists())
        before = (self.destination / ".git/index").read_bytes()
        with self.assertRaisesRegex(RestoreError, "sparse checkout"):
            self.restore()
        self.assertFalse(tracked.exists())
        self.assertEqual((self.destination / ".git/index").read_bytes(), before)

    def test_hidden_index_entries_are_refused_and_preserved(self):
        self.clone_source()
        for flag in ("skip-worktree", "assume-unchanged"):
            with self.subTest(flag=flag):
                git(self.destination, "update-index", f"--{flag}", "source.txt")
                tracked = self.destination / "source.txt"
                tracked.write_text(f"preserve hidden {flag} edit\n")
                before = git(self.destination, "ls-files", "-v", "-z")
                with self.assertRaisesRegex(RestoreError, "hidden tracked index"):
                    self.restore()
                self.assertEqual(tracked.read_text(), f"preserve hidden {flag} edit\n")
                self.assertEqual(git(self.destination, "ls-files", "-v", "-z"), before)
                git(self.destination, "update-index", f"--no-{flag}", "source.txt")
                git(self.destination, "checkout", "--", "source.txt")

    def test_dirty_and_mismatched_checkouts_are_preserved(self):
        self.clone_source()
        tracked = self.destination / "source.txt"
        tracked.write_text("preserve local work\n")
        with self.assertRaisesRegex(RestoreError, "dirty or mismatched"):
            self.restore()
        self.assertEqual(tracked.read_text(), "preserve local work\n")
        git(self.destination, "checkout", "--quiet", "--detach", "--force", self.commits[0])
        with self.assertRaisesRegex(RestoreError, "dirty or mismatched"):
            self.restore()
        self.assertEqual(git(self.destination, "rev-parse", "HEAD").decode().strip(), self.commits[0])
        self.assertEqual(tracked.read_text(), "source revision 0\n")

    def test_unrelated_nonempty_and_symlink_destinations_are_preserved(self):
        self.destination.mkdir()
        sentinel = self.destination / "keep.txt"
        sentinel.write_bytes(b"preserve this directory\n")
        with self.assertRaisesRegex(RestoreError, "unrelated"):
            self.restore()
        self.assertEqual(sentinel.read_bytes(), b"preserve this directory\n")
        link = self.root / "link"
        link.symlink_to(self.destination, target_is_directory=True)
        with self.assertRaisesRegex(RestoreError, "symlink"):
            restore(self.parent, link, self.source)
        self.assertEqual(sentinel.read_bytes(), b"preserve this directory\n")

    def test_manifest_hash_and_gitlink_bindings_reject_changes(self):
        for mutation, message in (
            (lambda m: m["base"].update(commit="bad"), "40-digit"),
            (lambda m: m["bundles"][0].update(blob=self.commits[0]), "committed tree"),
            (lambda m: m["bundles"][-1].update(tip=self.commits[0]), "gitlink"),
        ):
            with self.subTest(message=message):
                manifest = self.manifest_copy()
                mutation(manifest)
                with self.assertRaisesRegex(RestoreError, message):
                    self.restore(manifest)
                self.assertFalse(self.destination.exists())

    def test_missing_bundle_prerequisite_preserves_absent_destination(self):
        manifest = self.manifest_copy()
        manifest["bundles"] = manifest["bundles"][1:]
        with self.assertRaisesRegex(RestoreError, "bundle verify.*failed"):
            self.restore(manifest)
        self.assertFalse(self.destination.exists())
        self.assertEqual(list(self.root.glob(".ihk-source-*")), [])


if __name__ == "__main__":
    unittest.main()
