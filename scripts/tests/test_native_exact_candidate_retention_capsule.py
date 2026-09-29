import hashlib
import json
import os
import socket
import subprocess
import tempfile
import unittest
from unittest import mock

from scripts.native_exact_candidate_retention_capsule import InventoryError, build_plan, main, write_atomic


class RetentionCapsuleTests(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.c = os.path.join(self.td.name, "candidate")
        self.m = os.path.join(self.td.name, "metadata")
        os.mkdir(self.c); os.mkdir(self.m)

    def tearDown(self):
        self.td.cleanup()

    def _git(self):
        subprocess.check_call(["git", "init", "-q", self.c])
        subprocess.check_call(["git", "-C", self.c, "config", "user.email", "x@y"])
        subprocess.check_call(["git", "-C", self.c, "config", "user.name", "x"])
        with open(os.path.join(self.c, "tracked"), "wb") as f: f.write(b"stable\n")
        subprocess.check_call(["git", "-C", self.c, "add", "tracked"])
        subprocess.check_call(["git", "-C", self.c, "commit", "-qm", "fixture"])
        return subprocess.check_output(["git", "-C", self.c, "rev-parse", "HEAD"], universal_newlines=True).strip()

    def _config_git(self, path):
        subprocess.check_call(["git", "init", "-q", path])
        subprocess.check_call(["git", "-C", path, "config", "user.email", "x@y"])
        subprocess.check_call(["git", "-C", path, "config", "user.name", "x"])

    def test_deterministic_inventory_and_git_proof(self):
        rev = self._git()
        os.chmod(os.path.join(self.c, "tracked"), 0o600)
        with open(os.path.join(self.c, "untracked"), "wb") as f: f.write(b"u")
        os.mkdir(os.path.join(self.m, "backup"))
        with open(os.path.join(self.m, "backup", "state"), "wb") as f: f.write(b"meta")
        a = build_plan(self.c, self.m, rev, None)
        b = build_plan(self.c, self.m, rev, None)
        self.assertEqual(a, b)
        rows = {(x["root"], x["path"]): x for x in a["entries"]}
        self.assertEqual(rows[("candidate", "tracked")]["classification"], "reconstructible")
        self.assertEqual(rows[("candidate", "tracked")]["mode"], 0o600)
        self.assertEqual(rows[("candidate", "untracked")]["classification"], "capsule-required")
        self.assertEqual(rows[("metadata-backup", "backup")]["classification"], "capsule-required")
        self.assertIn("metadata-backup:backup/state", a["capsule_required"])
        out = os.path.join(self.td.name, "manifest.json")
        write_atomic(out, a)
        with open(out) as f: self.assertEqual(json.load(f), a)

    def test_rejects_symlink_fifo_and_hardlink(self):
        with open(os.path.join(self.c, "one"), "wb") as f: f.write(b"x")
        os.link(os.path.join(self.c, "one"), os.path.join(self.c, "alias"))
        with self.assertRaises(InventoryError): build_plan(self.c, self.m)
        os.unlink(os.path.join(self.c, "alias")); os.symlink("one", os.path.join(self.c, "link"))
        with self.assertRaises(InventoryError): build_plan(self.c, self.m)

    def test_missing_git_coverage_is_fail_closed(self):
        with open(os.path.join(self.c, "plain"), "wb") as f: f.write(b"x")
        with self.assertRaises(InventoryError):
            build_plan(self.c, self.m, "deadbeef", None)

    def test_nested_ihk_and_tracked_safe_symlink(self):
        self._config_git(self.c)
        ihk = os.path.join(self.c, "ihk")
        self._config_git(ihk)
        with open(os.path.join(ihk, "source"), "wb") as f: f.write(b"ihk\n")
        os.symlink("source", os.path.join(ihk, "safe-link"))
        subprocess.check_call(["git", "-C", ihk, "add", "source", "safe-link"])
        subprocess.check_call(["git", "-C", ihk, "commit", "-qm", "ihk"])
        ihk_rev = subprocess.check_output(["git", "-C", ihk, "rev-parse", "HEAD"], universal_newlines=True).strip()
        subprocess.check_call(["git", "-C", self.c, "add", "ihk"])
        subprocess.check_call(["git", "-C", self.c, "commit", "-qm", "main"])
        main_rev = subprocess.check_output(["git", "-C", self.c, "rev-parse", "HEAD"], universal_newlines=True).strip()
        plan = build_plan(self.c, self.m, main_rev, ihk_rev)
        rows = {(x["root"], x["path"]): x for x in plan["entries"]}
        self.assertEqual(rows[("candidate", "ihk/source")]["classification"], "reconstructible")
        self.assertEqual(rows[("candidate", "ihk/safe-link")]["classification"], "reconstructible")
        self.assertEqual(rows[("candidate", "ihk/safe-link")]["target"], "source")

    def test_absolute_and_escape_symlinks_rejected(self):
        os.symlink("/etc/passwd", os.path.join(self.c, "absolute"))
        with self.assertRaises(InventoryError): build_plan(self.c, self.m)

    def test_git_metadata_symlinks_rejected_during_descriptor_walk(self):
        os.mkdir(os.path.join(self.c, "target"))
        os.symlink("target", os.path.join(self.c, ".git"))
        with self.assertRaises(InventoryError): build_plan(self.c, self.m)
        os.unlink(os.path.join(self.c, ".git"))
        os.mkdir(os.path.join(self.c, "ihk"))
        os.symlink("../target", os.path.join(self.c, "ihk", ".git"))
        with self.assertRaises(InventoryError): build_plan(self.c, self.m)

    def test_backup_symlink_rejected_during_descriptor_walk(self):
        with open(os.path.join(self.m, "state"), "wb") as out: out.write(b"state")
        os.symlink("state", os.path.join(self.m, "link"))
        with self.assertRaises(InventoryError): build_plan(self.c, self.m)

    def test_special_rejection_precedes_any_git_invocation(self):
        rev = self._git()
        os.mkfifo(os.path.join(self.c, "fifo"))
        import scripts.native_exact_candidate_retention_capsule as capsule
        calls, original = [], capsule._git
        def counted(root, args):
            calls.append((root, args))
            return original(root, args)
        with mock.patch.object(capsule, "_git", side_effect=counted):
            with self.assertRaises(InventoryError): build_plan(self.c, self.m, rev)
        self.assertEqual(calls, [])

    def test_roots_are_revalidated_after_git_proof(self):
        rev = self._git()
        import scripts.native_exact_candidate_retention_capsule as capsule
        original, altered = capsule._git, [False]
        def mutate_after_proof(root, args):
            answer = original(root, args)
            if args[:2] == ["ls-tree", "-rz"] and not altered[0]:
                altered[0] = True
                with open(os.path.join(self.c, "after-git"), "wb") as out: out.write(b"race")
            return answer
        with mock.patch.object(capsule, "_git", side_effect=mutate_after_proof):
            with self.assertRaises(InventoryError): build_plan(self.c, self.m, rev)

    def test_root_symlinked_ancestor_rejected(self):
        real_parent = os.path.join(self.td.name, "real-parent")
        os.mkdir(real_parent)
        candidate = os.path.join(real_parent, "candidate")
        os.mkdir(candidate)
        parent_link = os.path.join(self.td.name, "parent-link")
        os.symlink(real_parent, parent_link)
        with self.assertRaises(InventoryError):
            build_plan(os.path.join(parent_link, "candidate"), self.m)

    def test_exact_tracked_symlink_set_and_mutation(self):
        rev = self._git()
        os.symlink("tracked", os.path.join(self.c, "extra"))
        with self.assertRaises(InventoryError): build_plan(self.c, self.m, rev)
        os.unlink(os.path.join(self.c, "extra"))
        os.symlink("tracked", os.path.join(self.c, "link"))
        subprocess.check_call(["git", "-C", self.c, "add", "link"])
        subprocess.check_call(["git", "-C", self.c, "commit", "-qm", "link"])
        rev = subprocess.check_output(["git", "-C", self.c, "rev-parse", "HEAD"], universal_newlines=True).strip()
        self.assertEqual(build_plan(self.c, self.m, rev)["format"], "native-exact-candidate-retention-v1")
        os.unlink(os.path.join(self.c, "link")); os.symlink("missing", os.path.join(self.c, "link"))
        with self.assertRaises(InventoryError): build_plan(self.c, self.m, rev)

    def test_special_and_cross_root_hardlink_rejected(self):
        os.mkfifo(os.path.join(self.c, "fifo"))
        with self.assertRaises(InventoryError): build_plan(self.c, self.m)
        os.unlink(os.path.join(self.c, "fifo"))
        sock = socket.socket(socket.AF_UNIX)
        try:
            sock.bind(os.path.join(self.c, "socket"))
            with self.assertRaises(InventoryError): build_plan(self.c, self.m)
        finally:
            sock.close()
        os.unlink(os.path.join(self.c, "socket"))
        with open(os.path.join(self.c, "one"), "wb") as out: out.write(b"x")
        os.link(os.path.join(self.c, "one"), os.path.join(self.m, "alias"))
        with self.assertRaises(InventoryError): build_plan(self.c, self.m)

    def test_directory_and_regular_mutation_detected(self):
        with open(os.path.join(self.c, "one"), "wb") as out: out.write(b"x")
        real_listdir, calls = os.listdir, [0]
        def mutate_listdir(fd):
            calls[0] += 1
            if calls[0] == 2:
                with open(os.path.join(self.c, "late"), "wb") as out: out.write(b"late")
            return real_listdir(fd)
        with mock.patch("scripts.native_exact_candidate_retention_capsule.os.listdir", side_effect=mutate_listdir):
            with self.assertRaises(InventoryError): build_plan(self.c, self.m)
        os.unlink(os.path.join(self.c, "late"))
        real_read, altered = os.read, [False]
        def mutate_read(fd, size):
            answer = real_read(fd, size)
            if answer and not altered[0]:
                altered[0] = True
                with open(os.path.join(self.c, "one"), "ab") as out: out.write(b"!")
            return answer
        with mock.patch("scripts.native_exact_candidate_retention_capsule.os.read", side_effect=mutate_read):
            with self.assertRaises(InventoryError): build_plan(self.c, self.m)

    def test_regular_content_is_never_path_reopened(self):
        with open(os.path.join(self.c, "one"), "wb") as out: out.write(b"x")
        real_open = os.open
        def guarded(path, flags, mode=0o777, *, dir_fd=None):
            if path == os.path.join(self.c, "one"):
                raise AssertionError("path-based content reopen")
            return real_open(path, flags, mode, dir_fd=dir_fd)
        with mock.patch("scripts.native_exact_candidate_retention_capsule.os.open", side_effect=guarded):
            build_plan(self.c, self.m)

    def test_git_parser_rejects_malformed_duplicate_and_ignores_poisoned_environment(self):
        rev = self._git()
        with mock.patch.dict(os.environ, {"GIT_DIR": "/missing", "GIT_WORK_TREE": "/"}):
            self.assertEqual(build_plan(self.c, self.m, rev)["revisions"]["main"], rev)
        import scripts.native_exact_candidate_retention_capsule as capsule
        original = capsule._git
        def malformed(root, args):
            if args[:2] == ["ls-tree", "-rz"]: return b"bad\0"
            return original(root, args)
        with mock.patch.object(capsule, "_git", side_effect=malformed):
            with self.assertRaises(InventoryError): build_plan(self.c, self.m, rev)
        def duplicate(root, args):
            if args[:2] == ["ls-tree", "-rz"]:
                return b"100644 blob " + b"0" * 40 + b"\ttracked\0" + b"100644 blob " + b"0" * 40 + b"\ttracked\0"
            return original(root, args)
        with mock.patch.object(capsule, "_git", side_effect=duplicate):
            with self.assertRaises(InventoryError): build_plan(self.c, self.m, rev)
        def noncanonical(root, args):
            if args[:2] == ["ls-tree", "-rz"]:
                return b"0100644 blob " + b"0" * 40 + b"\ttracked\0"
            return original(root, args)
        with mock.patch.object(capsule, "_git", side_effect=noncanonical):
            with self.assertRaises(InventoryError): build_plan(self.c, self.m, rev)

    def test_no_replace_output_and_symlink_parent_and_root_alias(self):
        output = os.path.join(self.td.name, "manifest.json")
        write_atomic(output, {"x": 1})
        with self.assertRaises(InventoryError): write_atomic(output, {"x": 2})
        link_parent = os.path.join(self.td.name, "linked")
        os.symlink(self.td.name, link_parent)
        with self.assertRaises(OSError): write_atomic(os.path.join(link_parent, "other.json"), {"x": 1})
        with self.assertRaises(InventoryError): main(["--candidate-root", self.c, "--metadata-backup-root", self.m,
                                                       "--output", os.path.join(self.c, "not-allowed.json")])


if __name__ == "__main__":
    unittest.main()
