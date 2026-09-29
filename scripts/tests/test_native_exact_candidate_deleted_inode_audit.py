import json
import os
import subprocess
import sys
import tempfile
import unittest
import ctypes
import errno
from contextlib import ExitStack, contextmanager
from types import SimpleNamespace
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import native_exact_candidate_deleted_inode_audit as audit


class ProcFixture:
    """One leader and one thread; all primitives consumed by the real scanner."""
    def __init__(self):
        self.calls = {}
        self.identity_faults = {}
        self.stat_faults = {}
        self.directories = {"/proc": ["7"], "/proc/7/task": ["7", "8"],
                            "/proc/7/fd": [], "/proc/7/map_files": ["1000-2000"],
                            "/proc/7/task/7/fd": [], "/proc/7/task/8/fd": []}

    def identity(self, pid, tid=None):
        key = (pid, tid)
        self.calls[key] = self.calls.get(key, 0) + 1
        result = self.identity_faults.get((key, self.calls[key]))
        if isinstance(result, Exception):
            raise result
        return result or (pid, pid if tid is None else tid, "123")

    def stat(self, path):
        error = self.stat_faults.get(path)
        if error:
            raise error
        return SimpleNamespace(st_dev=1, st_ino=42)

    def __enter__(self):
        self.stack = ExitStack()
        @contextmanager
        def scandir(path):
            yield iter(SimpleNamespace(name=x) for x in self.directories[path])
        for target, value in [
                ("_identity", self.identity), ("os.stat", self.stat),
                ("os.listdir", lambda p: self.directories[p]),
                ("os.scandir", scandir),
                ("os.readlink", lambda p: p.rsplit("/", 1)[1] + ":[41]")]:
            self.stack.enter_context(mock.patch.object(audit, target, value) if "." not in target
                                     else mock.patch("native_exact_candidate_deleted_inode_audit." + target, value))
        self.stack.enter_context(mock.patch("builtins.open", mock.mock_open(
            read_data="31 26 0:26 / /dev/shm rw - tmpfs tmpfs rw\n")))
        return self

    def __exit__(self, *args):
        self.stack.close()


class DeletedInodeAuditTests(unittest.TestCase):
    def test_identity_set_and_canonical_hash_are_stable(self):
        values = [(2, 4), (1, 3)]
        expected = audit.hashlib.sha256(audit.canonical_json(sorted(set(values))).encode()).hexdigest()
        self.assertEqual(expected, "b8071183795a2d11bef66cd2c5b27c2f8fb12f6152b34e4ddfd0c87c895fdbb5")

    def test_map_files_finds_closed_mmap(self):
        libc = ctypes.CDLL(None, use_errno=True)
        libc.mmap.restype = ctypes.c_void_p
        fd, path = tempfile.mkstemp()
        os.write(fd, b"x" * 4096)
        addr = libc.mmap(None, 4096, 1, 1, fd, 0)  # PROT_READ, MAP_SHARED
        self.assertNotEqual(addr, ctypes.c_void_p(-1).value)
        dev = os.fstat(fd).st_dev; ino = os.fstat(fd).st_ino
        os.unlink(path)
        os.close(fd)
        try:
            # Prove descriptor-free retention and select this exact mapping,
            # rather than accepting a denial on an unrelated Python mapping.
            for fdname in os.listdir("/proc/self/fd"):
                try:
                    s = os.stat("/proc/self/fd/" + fdname)
                except FileNotFoundError:
                    continue
                self.assertNotEqual((s.st_dev, s.st_ino), (dev, ino))
            entry = "%x-%x" % (addr, addr + 4096)
            target = "/proc/%d/map_files/%s" % (os.getpid(), entry)
            self.assertIn(entry, os.listdir("/proc/%d/map_files" % os.getpid()))
            refs, failures = [], []
            label = "map_files/%d/%s" % (os.getpid(), entry)
            ok = audit._stat_target(target, {(dev, ino)}, failures, refs, label,
                                    bound=audit._identity(os.getpid()))
            if ok:
                self.assertEqual(refs, [{"identity": [dev, ino], "source": label}])
                self.assertEqual(failures, [])
            else:
                self.assertTrue(any(x in failures for x in
                    ("stat:%s:%d" % (label, errno.EPERM), "stat:%s:%d" % (label, errno.EACCES))), failures)
                self.assertEqual(refs, [])
        finally:
            self.assertEqual(libc.munmap(ctypes.c_void_p(addr), 4096), 0)

    def test_exclusive_output(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "out.json")
            audit._write_exclusive(p, {"ok": True})
            with self.assertRaises(FileExistsError): audit._write_exclusive(p, {"ok": False})
            with open(p) as f:
                self.assertEqual(json.load(f)["ok"], True)

    def test_mount_alias_is_not_a_clean_scan(self):
        data = "24 26 0:26 /retained /elsewhere rw - tmpfs tmpfs rw\n"
        failures = []
        with mock.patch("builtins.open", mock.mock_open(read_data=data)), mock.patch.object(audit.os, "readlink", return_value="mnt:[42]"):
            audit._scan_mountinfo(7, failures, ((os.makedev(0, 26), "/retained"),))
        self.assertTrue(any(x.startswith("mount-alias:") for x in failures), failures)

    def test_map_entry_disappearance_is_unresolved_while_process_lives(self):
        failures, refs, reconciled = [], [], []
        audit._stat_target("/definitely/absent", {(1, 2)}, failures, refs,
                           "map_files/%d/1-2" % os.getpid(), reconciled, audit._identity(os.getpid()))
        self.assertTrue(any(x.startswith("unresolved-target-churn:") for x in failures), failures)
        self.assertEqual(reconciled, [])

    def test_positive_complete_census_and_injected_mmap_reference(self):
        with ProcFixture():
            identities, failures, refs, counters = audit.audit_round({(1, 42)})
        self.assertEqual(failures, [])
        self.assertEqual(set(identities), {(7, 7, "123"), (7, 8, "123")})
        self.assertEqual(counters["map_files_entries"], 1)
        self.assertIn({"identity": [1, 42], "source": "map_files/7/1000-2000"}, refs)

    def test_postscan_identity_errors_never_authorize_anchors(self):
        for key, call in [((7, None), 2), ((7, None), 3), ((7, 7), 2), ((7, 8), 2), ((7, 8), 3)]:
            for error in [PermissionError(errno.EACCES, "denied"), ValueError("malformed"),
                          FileNotFoundError(errno.ENOENT, "stat only"), (7, 7, "999")]:
                with self.subTest(key=key, call=call, error=error), ProcFixture() as proc:
                    proc.identity_faults[(key, call)] = error
                    identities, failures, _, _ = audit.audit_round(set())
                self.assertEqual(identities, [])
                self.assertTrue(failures)

    def test_only_proven_directory_disappearance_is_exit(self):
        bound = (7, 7, "123")
        for err in [PermissionError(errno.EACCES, "denied"), ValueError("malformed")]:
            with mock.patch.object(audit, "_identity", side_effect=err), mock.patch.object(audit.os, "stat") as stat_call:
                self.assertEqual(audit._identity_state(bound), audit.IdentityState.UNCERTAIN)
                stat_call.assert_not_called()
        with mock.patch.object(audit, "_identity", side_effect=FileNotFoundError(errno.ENOENT, "gone")):
            for err, expected in [(FileNotFoundError(errno.ENOENT, "gone"), audit.IdentityState.EXITED),
                                  (PermissionError(errno.EACCES, "denied"), audit.IdentityState.UNCERTAIN),
                                  (ProcessLookupError(errno.ESRCH, "uncertain"), audit.IdentityState.UNCERTAIN)]:
                with mock.patch.object(audit.os, "stat", side_effect=err):
                    self.assertEqual(audit._identity_state(bound), expected)

    def test_map_disappearance_checks_bound_process(self):
        for identity_error in [PermissionError(errno.EACCES, "denied"), ValueError("malformed"),
                               (7, 7, "999"), (7, 7, "123")]:
            failures, refs, exits = [], [], []
            with mock.patch.object(audit.os, "stat", side_effect=FileNotFoundError(errno.ENOENT, "gone")), \
                    mock.patch.object(audit, "_identity", **({"side_effect": identity_error} if isinstance(identity_error, Exception) else {"return_value": identity_error})):
                audit._stat_target("/proc/7/map_files/1-2", set(), failures, refs, "map_files/7/1-2", exits, (7, 7, "123"))
            self.assertTrue(failures)
            self.assertEqual(exits, [])
        failures, refs, exits = [], [], []
        with mock.patch.object(audit.os, "stat", side_effect=FileNotFoundError(errno.ENOENT, "gone")), \
                mock.patch.object(audit, "_identity", side_effect=FileNotFoundError(errno.ENOENT, "gone")):
            audit._stat_target("/proc/7/map_files/1-2", set(), failures, refs, "map_files/7/1-2", exits, (7, 7, "123"))
        self.assertEqual(failures, [])
        self.assertEqual(exits, ["exit:7:7"])

    def test_map_denial_stays_failure_even_if_process_exits(self):
        failures = []
        with mock.patch.object(audit.os, "stat", side_effect=PermissionError(errno.EACCES, "denied")), \
                mock.patch.object(audit, "_identity_state", return_value=audit.IdentityState.EXITED) as probe:
            audit._stat_target("unused", set(), failures, [], "map_files/7/1-2", [], (7, 7, "123"))
        self.assertEqual(failures, ["stat:map_files/7/1-2:13"])
        probe.assert_not_called()

    def test_mount_semantics_and_task_specific_input(self):
        for root, mountpoint, device, reject in [
                ("/retained", "/alias", "0:26", True),
                ("/retained/descendant", "/alias", "0:26", True),
                (r"/retained\040(deleted)", "/alias", "0:26", True),
                ("/", "/dev/shm", "0:26", False),
                ("/ancestor", "/other", "0:26", False),
                ("/retained-other", "/alias", "0:26", False),
                ("/retained", "/alias", "0:27", False)]:
            data = "24 26 %s %s %s rw - tmpfs tmpfs rw\n" % (device, root, mountpoint)
            failures = []
            with self.subTest(root=root, device=device), mock.patch("builtins.open", mock.mock_open(read_data=data)) as opened, \
                    mock.patch.object(audit.os, "readlink", return_value="mnt:[42]") as linked:
                audit._scan_mountinfo(7, failures, ((26, "/retained"),), 8)
                opened.assert_called_once_with("/proc/7/task/8/mountinfo", "r")
                self.assertEqual(linked.call_args_list, [mock.call("/proc/7/task/8/ns/mnt")] * 2)
            self.assertEqual(bool(failures), reject, failures)

    def test_mountinfo_rejects_empty_malformed_incomplete_and_duplicate(self):
        valid = "24 26 0:26 / /dev/shm rw - tmpfs tmpfs rw\n"
        for data in ["", "\n", valid.rstrip(), "garbage\n", valid + valid,
                     valid.replace("0:26", "bad"), valid.replace(" / ", " relative "),
                     valid.replace("/dev/shm", r"/bad\099"), valid.replace(" - ", " "),
                     valid.replace("rw -", "rw bad:optional -"),
                     valid.replace("rw -", "rw, -"),
                     valid.replace("tmpfs tmpfs rw", "tmpfs tmpfs")]:
            with self.subTest(data=data), self.assertRaises((ValueError, OverflowError)):
                audit._mount_rows(data)

    def test_mount_namespace_format_and_churn_fail(self):
        for links in [["mnt:[1]", "mnt:[2]"], ["mnt:bad"], ["pid:[1]"], ["mnt:[0]"],
                      [PermissionError(errno.EACCES, "denied")]]:
            failures = []
            with mock.patch("builtins.open", mock.mock_open(read_data="24 26 0:26 / /dev/shm rw - tmpfs tmpfs rw\n")), \
                    mock.patch.object(audit.os, "readlink", side_effect=links):
                audit._scan_mountinfo(7, failures)
            self.assertTrue(failures)

    def test_target_mount_root_binding_is_observer_derived(self):
        root = {"device_number": 26, "filesystem_root": "/retained", "path": "/dev/shm/retained",
                "observer_mount": {"device": "0:26", "root": "/", "mountpoint": "/dev/shm"}}
        self.assertEqual(audit.retained_mount_roots({"roots": [root]}), ((26, "/retained"),))
        for field, value in [("filesystem_root", "/guess"), ("filesystem_root", "/"), ("device_number", True), ("path", "/elsewhere")]:
            with self.subTest(field=field), self.assertRaises(audit.AuditError):
                audit.retained_mount_roots({"roots": [dict(root, **{field: value})]})

    def test_starttime_uses_exact_task_path_and_rejects_malformed_stat(self):
        body = "8 (comm with ) delimiter) S " + " ".join(["0"] * 18 + ["123"] + ["0"] * 30)
        with mock.patch("builtins.open", mock.mock_open(read_data=body)) as opened:
            self.assertEqual(audit._identity(7, 8), (7, 8, "123"))
            opened.assert_called_once_with("/proc/7/task/8/stat", "r")
        for data in [body.replace("8 (", "9 ("), body.replace(") S ", ") bad "),
                     body.replace(" 0 ", " bad ", 1), "8 (x) S " + "0 " * 19]:
            with mock.patch("builtins.open", mock.mock_open(read_data=data)), self.assertRaises(ValueError):
                audit._identity(7, 8)

    def test_three_round_run_authenticates_only_exact_live_anchors(self):
        root = {"device_number": 26, "filesystem_root": "/retained", "path": "/dev/shm/retained",
                "observer_mount": {"device": "0:26", "root": "/", "mountpoint": "/dev/shm"}}
        baseline = ({"boot_id": "boot", "roots": [root]}, {}, {(26, 99)}, [1], ["/dev/shm/old"])
        for anchor, expect, fault in [("7:123", 0, False), ("7:122", 1, False),
                                      ("8:123", 1, False), ("7:123", 1, True)]:
            args = SimpleNamespace(archive="archive", inventory="inventory", output="output",
                                   anchor=[anchor], rounds=3, delay=0)
            with self.subTest(anchor=anchor, fault=fault), ProcFixture() as proc:
                if fault:
                    proc.identity_faults[((7, None), 3)] = PermissionError(errno.EACCES, "denied")
                with mock.patch.object(audit.os, "geteuid", return_value=0), \
                        mock.patch.object(audit, "load_baseline", return_value=baseline), \
                        mock.patch.object(audit.os, "lstat", side_effect=FileNotFoundError(errno.ENOENT, "gone")), \
                        mock.patch.object(audit, "sha256_file", return_value="hash"), \
                        mock.patch.object(audit, "_write_exclusive") as written:
                    ordinary_open = open
                    def read(path, *a, **kw):
                        if path == "/proc/sys/kernel/random/boot_id":
                            return mock.mock_open(read_data="boot\n")(path, *a, **kw)
                        return ordinary_open(path, *a, **kw)
                    with mock.patch("builtins.open", side_effect=read):
                        self.assertEqual(audit.run(args), expect)
            result = written.call_args[0][1]
            self.assertEqual(len(result["rounds"]), 3)
            if expect:
                self.assertTrue(any(x.startswith("anchor-missing:") for x in result["failures"]))
            else:
                self.assertEqual(result["failures"], [])

    def test_census_cannot_drop_live_unscanned_or_new_tasks(self):
        with ProcFixture() as proc:
            original = proc.directories["/proc/7/task"]
            listing = audit.os.listdir
            counts = {}
            def changed(path):
                counts[path] = counts.get(path, 0) + 1
                if path == "/proc/7/task" and counts[path] == 2:
                    return original + ["9"]
                return listing(path)
            with mock.patch.object(audit.os, "listdir", side_effect=changed):
                identities, failures, _, _ = audit.audit_round(set())
        self.assertEqual(identities, [])
        self.assertIn("task-census-churn:7", failures)

    def test_nonroot_run_refuses_before_loading_inputs(self):
        with mock.patch.object(audit.os, "geteuid", return_value=1000), \
                mock.patch.object(audit, "load_baseline") as load, self.assertRaises(audit.AuditError):
            audit.run(SimpleNamespace())
        load.assert_not_called()

    def test_self_fd_scan_keeps_enumerator_alive(self):
        failures, refs = [], []
        pid = os.getpid()
        audit._scan_fds("/proc/%d" % pid, audit._identity(pid), False, set(), failures, refs, [])
        self.assertEqual(failures, [])
        self.assertEqual(refs, [])

    def test_malformed_map_entries_and_directory_denials_fail_closed(self):
        for entries in [["bad"], ["1000-1000"], ["2000-1000"]]:
            with ProcFixture() as proc:
                proc.directories["/proc/7/map_files"] = entries
                identities, failures, _, _ = audit.audit_round(set())
            self.assertEqual(identities, [])
            self.assertIn("malformed-map-entry:7", failures)
        with ProcFixture():
            listing = audit.os.listdir
            def denied(path):
                if path == "/proc/7/map_files":
                    raise PermissionError(errno.EACCES, "denied")
                return listing(path)
            with mock.patch.object(audit.os, "listdir", side_effect=denied):
                identities, failures, _, counters = audit.audit_round(set())
        self.assertEqual(identities, [])
        self.assertEqual(counters["map_files_denials"], 1)
        self.assertIn("map_files-directory:7:13", failures)

    def test_output_full_write_and_durability(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "out")
            real_write, real_sync = os.write, os.fsync
            with mock.patch.object(audit.os, "write", side_effect=lambda fd, b: real_write(fd, b[:2])) as writes, \
                    mock.patch.object(audit.os, "fsync", wraps=real_sync) as syncs:
                audit._write_exclusive(path, {"some": "output"})
            self.assertGreater(writes.call_count, 1)
            self.assertEqual(syncs.call_count, 2)
            with open(path) as f:
                self.assertEqual(json.load(f), {"some": "output"})
            self.assertEqual(os.stat(path).st_mode & 0o777, 0o600)

    def test_output_zero_write_and_fsync_errors_propagate(self):
        with tempfile.TemporaryDirectory() as d:
            with mock.patch.object(audit.os, "write", return_value=0), self.assertRaises(OSError):
                audit._write_exclusive(os.path.join(d, "zero"), {})
            with mock.patch.object(audit.os, "fsync", side_effect=OSError(errno.EIO, "sync")), self.assertRaises(OSError):
                audit._write_exclusive(os.path.join(d, "sync"), {})


if __name__ == "__main__":
    unittest.main()
