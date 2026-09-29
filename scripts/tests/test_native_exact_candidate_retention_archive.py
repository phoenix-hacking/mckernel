import hashlib
import json
import os
import stat
import tempfile
import tarfile
import unittest
from unittest import mock

from scripts.native_exact_candidate_retention_capsule import build_plan, write_atomic
from scripts import native_exact_candidate_retention_archive as archive
from scripts.native_exact_candidate_retention_archive import ArchiveError, build_archive, verify_archive, verify_archive_bytes


class RetentionArchiveTests(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.c = os.path.join(self.td.name, "candidate")
        self.m = os.path.join(self.td.name, "metadata")
        os.mkdir(self.c); os.mkdir(self.m)
        with open(os.path.join(self.c, "required"), "wb") as f: f.write(b"candidate\n")
        os.mkdir(os.path.join(self.m, "state"))
        with open(os.path.join(self.m, "state", "x"), "wb") as f: f.write(b"metadata\n")
        self.plan = build_plan(self.c, self.m)
        self.manifest = os.path.join(self.td.name, "manifest.json")
        write_atomic(self.manifest, self.plan)

    def tearDown(self):
        self.td.cleanup()

    def replace_manifest(self, value):
        # Planner publication is intentionally no-overwrite.  Test fixtures may
        # replace their own disposable manifest explicitly.
        os.unlink(self.manifest)
        write_atomic(self.manifest, value)

    def refresh_root_identities(self, value):
        for root in value["roots"]:
            st = os.stat(root["path"])
            root["identity"] = {"dev": st.st_dev, "inode": st.st_ino,
                                "uid": st.st_uid, "gid": st.st_gid,
                                "mode": stat.S_IMODE(st.st_mode),
                                "nlink": st.st_nlink, "size": st.st_size,
                                "mtime_ns": st.st_mtime_ns,
                                "ctime_ns": st.st_ctime_ns}

    def test_exact_positive_and_determinism(self):
        a = os.path.join(self.td.name, "a.tar")
        b = os.path.join(self.td.name, "b.tar")
        build_archive(self.manifest, self.c, self.m, a)
        build_archive(self.manifest, self.c, self.m, b)
        with open(a, "rb") as f: aa = f.read()
        with open(b, "rb") as f: bb = f.read()
        self.assertEqual(aa, bb)
        self.assertEqual(hashlib.sha256(aa).hexdigest(), hashlib.sha256(bb).hexdigest())
        verify_archive(a)

    def test_changed_missing_additional_and_collision(self):
        out = os.path.join(self.td.name, "x.tar")
        with open(os.path.join(self.c, "required"), "ab") as f: f.write(b"changed")
        with self.assertRaises(ArchiveError): build_archive(self.manifest, self.c, self.m, out)
        os.unlink(os.path.join(self.c, "required"))
        with self.assertRaises(ArchiveError): build_archive(self.manifest, self.c, self.m, out)
        with open(os.path.join(self.c, "required"), "wb") as f: f.write(b"candidate\n")
        with open(os.path.join(self.c, "extra"), "wb") as f: f.write(b"extra")
        with self.assertRaises(ArchiveError): build_archive(self.manifest, self.c, self.m, out)
        os.unlink(os.path.join(self.c, "extra"))
        self.replace_manifest(build_plan(self.c, self.m))
        build_archive(self.manifest, self.c, self.m, out)
        with self.assertRaises((ArchiveError, FileExistsError, OSError)): build_archive(self.manifest, self.c, self.m, out)

    def test_rejects_symlink_hardlink_and_special(self):
        os.symlink("required", os.path.join(self.c, "link"))
        p = json.loads(json.dumps(self.plan))
        p["entries"].append({"root": "candidate", "path": "link", "type": "symlink", "mode": 0o777, "uid": os.getuid(), "gid": os.getgid(), "size": len(b"required"), "target": "required", "classification": "reconstructible"})
        p["entries"].sort(key=lambda x: (x["root"], x["path"]))
        self.refresh_root_identities(p)
        self.replace_manifest(p)
        # Reconstructible symlinks are inventoried and verified, but omitted.
        build_archive(self.manifest, self.c, self.m, os.path.join(self.td.name, "s.tar"))
        os.unlink(os.path.join(self.c, "link"))
        os.link(os.path.join(self.c, "required"), os.path.join(self.c, "alias"))
        with self.assertRaises(ArchiveError): build_archive(self.manifest, self.c, self.m, os.path.join(self.td.name, "h.tar"))

    def test_changed_symlink_rejected(self):
        os.symlink("required", os.path.join(self.c, "link"))
        p = json.loads(json.dumps(self.plan))
        p["entries"].append({"root": "candidate", "path": "link", "type": "symlink", "mode": 0o777, "uid": os.getuid(), "gid": os.getgid(), "size": len(b"required"), "target": "required", "classification": "reconstructible"})
        p["entries"].sort(key=lambda x: (x["root"], x["path"]))
        self.refresh_root_identities(p)
        self.replace_manifest(p)
        os.unlink(os.path.join(self.c, "link")); os.symlink("/tmp", os.path.join(self.c, "link"))
        with self.assertRaises(ArchiveError): build_archive(self.manifest, self.c, self.m, os.path.join(self.td.name, "changed-link.tar"))

    def test_duplicate_and_path_escape_manifest(self):
        with open(self.manifest) as source:
            data = json.load(source)
        data["entries"].append(dict(data["entries"][0]))
        self.replace_manifest(data)
        with self.assertRaises(ArchiveError): build_archive(self.manifest, self.c, self.m, os.path.join(self.td.name, "d.tar"))

        data = build_plan(self.c, self.m)
        data["entries"][0]["path"] = "../escape"
        self.replace_manifest(data)
        with self.assertRaises(ArchiveError): build_archive(self.manifest, self.c, self.m, os.path.join(self.td.name, "e.tar"))

    def test_required_symlink_fifo_and_external_hardlink_rejected(self):
        os.symlink("required", os.path.join(self.c, "required-link"))
        plan = json.loads(json.dumps(self.plan))
        plan["entries"].append({"root": "candidate", "path": "required-link",
                                "type": "symlink", "mode": 0o777,
                                "uid": os.getuid(), "gid": os.getgid(),
                                "size": len(b"required"), "target": "required",
                                "classification": "capsule-required"})
        plan["entries"].sort(key=lambda x: (x["root"], x["path"]))
        plan["capsule_required"].append("candidate:required-link")
        self.refresh_root_identities(plan)
        self.replace_manifest(plan)
        with self.assertRaises(ArchiveError): build_archive(self.manifest, self.c, self.m, os.path.join(self.td.name, "link.tar"))
        os.unlink(os.path.join(self.c, "required-link"))
        os.mkfifo(os.path.join(self.c, "pipe"))
        with self.assertRaises(ArchiveError): build_archive(self.manifest, self.c, self.m, os.path.join(self.td.name, "fifo.tar"))
        os.unlink(os.path.join(self.c, "pipe"))
        external = os.path.join(self.td.name, "external")
        os.link(os.path.join(self.c, "required"), external)
        with self.assertRaises(ArchiveError): build_archive(self.manifest, self.c, self.m, os.path.join(self.td.name, "hard.tar"))

    def test_nested_required_directories_and_archive_headers(self):
        os.mkdir(os.path.join(self.c, ".git"))
        os.mkdir(os.path.join(self.c, ".git", "ihk"))
        with open(os.path.join(self.c, ".git", "ihk", "HEAD"), "wb") as out:
            out.write(b"ref: nested\n")
        plan = build_plan(self.c, self.m)
        self.replace_manifest(plan)
        archive = os.path.join(self.td.name, "nested.tar")
        build_archive(self.manifest, self.c, self.m, archive)
        with tarfile.open(archive, "r:") as opened:
            self.assertIn("candidate/.git", opened.getnames())
            self.assertIn("candidate/.git/ihk/HEAD", opened.getnames())
            header_offset = opened.getmember("candidate/.git").offset
        # Header-only corruption is rejected even when member bytes survive.
        with open(archive, "r+b") as out:
            out.seek(header_offset + 100)  # ustar mode field
            out.write(b"0000777\0")
        with self.assertRaises(ArchiveError): verify_archive(archive)

    def test_source_swap_parent_symlink_duplicate_and_fd_cleanup(self):
        target = os.path.join(self.c, "required")
        output = os.path.join(self.td.name, "swap.tar")
        original = archive._open_member
        changed = [False]

        def swap(*args):
            if not changed[0]:
                changed[0] = True
                os.unlink(target)
                os.mkdir(target)
            return original(*args)

        with mock.patch.object(archive, "_open_member", side_effect=swap):
            with self.assertRaises(ArchiveError): build_archive(self.manifest, self.c, self.m, output)
        self.assertFalse(os.path.exists(output))
        os.rmdir(target)
        with open(target, "wb") as out:
            out.write(b"candidate\n")
        self.replace_manifest(build_plan(self.c, self.m))
        before = set(os.listdir("/proc/self/fd"))
        archive_path = os.path.join(self.td.name, "clean.tar")
        build_archive(self.manifest, self.c, self.m, archive_path)
        self.assertEqual(before, set(os.listdir("/proc/self/fd")))
        with tarfile.open(archive_path, "a:") as opened:
            info = tarfile.TarInfo("candidate/required")
            info.size = 0
            opened.addfile(info)
        with self.assertRaises(ArchiveError): verify_archive(archive_path)

    def test_regular_to_fifo_open_race_is_nonblocking_and_closes_fd(self):
        target = os.path.join(self.c, "required")
        original_open = archive.os.open
        swapped = [False]
        before = set(os.listdir("/proc/self/fd"))

        def fifo_after_lstat(name, flags, *args, **kwargs):
            if name == "required" and not swapped[0]:
                swapped[0] = True
                # Make a future regression fail deterministically before it can
                # block on the FIFO: then exercise the real nonblocking open.
                self.assertTrue(flags & getattr(os, "O_NONBLOCK", 0))
                os.unlink(target)
                os.mkfifo(target)
            return original_open(name, flags, *args, **kwargs)

        with mock.patch.object(archive.os, "open", side_effect=fifo_after_lstat):
            with self.assertRaises(ArchiveError):
                build_archive(self.manifest, self.c, self.m,
                              os.path.join(self.td.name, "fifo-race.tar"))
        self.assertTrue(swapped[0])
        self.assertEqual(before, set(os.listdir("/proc/self/fd")))

    def test_manifest_and_output_symlink_ancestors_and_fsync_failure(self):
        real = os.path.join(self.td.name, "real")
        alias = os.path.join(self.td.name, "alias")
        os.mkdir(real)
        os.symlink(real, alias)
        with self.assertRaises(ArchiveError): build_archive(
            os.path.join(alias, "manifest.json"), self.c, self.m,
            os.path.join(self.td.name, "no.tar"))
        with self.assertRaises(ArchiveError): build_archive(
            self.manifest, self.c, self.m, os.path.join(alias, "out.tar"))
        out = os.path.join(self.td.name, "fsync.tar")
        with mock.patch.object(archive.os, "fsync", side_effect=OSError("injected")):
            with self.assertRaises(OSError): build_archive(self.manifest, self.c, self.m, out)
        self.assertFalse(os.path.exists(out))

    def test_verifier_uses_one_stable_byte_snapshot(self):
        path = os.path.join(self.td.name, "stable.tar")
        build_archive(self.manifest, self.c, self.m, path)
        with open(path, "rb") as source:
            expected = source.read()
        original = archive._read_regular_bytes
        calls = [0]

        def read_then_replace(name, label):
            calls[0] += 1
            captured = original(name, label)
            os.unlink(name)
            with open(name, "wb") as replacement:
                replacement.write(b"not an archive")
            return captured

        with mock.patch.object(archive, "_read_regular_bytes", side_effect=read_then_replace):
            self.assertTrue(verify_archive(path))
        self.assertEqual(calls, [1])
        self.assertTrue(verify_archive_bytes(expected))
        with self.assertRaises(ArchiveError): verify_archive_bytes(bytearray(expected))
        alias = os.path.join(self.td.name, "stable-alias.tar")
        os.symlink(path, alias)
        with self.assertRaises(ArchiveError): verify_archive(alias)

    def test_archive_mutation_detected(self):
        out = os.path.join(self.td.name, "m.tar")
        build_archive(self.manifest, self.c, self.m, out)
        with open(out, "r+b") as f:
            blob = f.read(); pos = blob.find(b"metadata\n")
            self.assertGreaterEqual(pos, 0)
            f.seek(pos); f.write(b"METADATA\n")
        with self.assertRaises(ArchiveError): verify_archive(out)


if __name__ == "__main__":
    unittest.main()
