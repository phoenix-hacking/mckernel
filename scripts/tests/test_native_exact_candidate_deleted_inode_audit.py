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
                ("_classification_bound", lambda bound, task=False: "ordinary"),
                ("os.listdir", lambda p: self.directories[p]),
                ("os.scandir", scandir),
                ("os.readlink", lambda p: "/" if p.endswith("/root") else p.rsplit("/", 1)[1] + ":[41]")]:
            self.stack.enter_context(mock.patch.object(audit, target, value) if "." not in target
                                     else mock.patch("native_exact_candidate_deleted_inode_audit." + target, value))
        self.stack.enter_context(mock.patch("builtins.open", mock.mock_open(
            read_data="31 26 0:26 / /dev/shm rw - tmpfs tmpfs rw\n")))
        return self

    def __exit__(self, *args):
        self.stack.close()


class SpecialProcFixture(ProcFixture):
    """Stable typed identities with every permitted surface initially absent."""
    def __init__(self, classification, empty_mountinfo=False):
        super().__init__()
        self.classes = {(7, None): classification, (7, 7): classification, (7, 8): classification}
        self.absent = set()
        self.errors = {}
        self.empty_mountinfo = empty_mountinfo
        for base in ("/proc/7", "/proc/7/task/7", "/proc/7/task/8"):
            self.absent.update(base + "/" + name for name in
                               ("cwd", "root", "exe", "fd", "mountinfo"))
            self.absent.update(base + "/ns/" + name for name in
                               ("pid", "net", "user", "uts", "ipc", "mnt"))
        self.absent.add("/proc/7/map_files")
        # Namespace membership must always be observable. The leader task is
        # an independent full-root representative for the other absent views.
        for base in ("/proc/7", "/proc/7/task/7", "/proc/7/task/8"):
            self.absent.remove(base + "/ns/mnt")
        self.absent.remove("/proc/7/task/7/root")
        self.absent.remove("/proc/7/task/7/mountinfo")

    def check(self, path):
        if path in self.errors:
            raise self.errors[path]
        if path in self.absent:
            raise FileNotFoundError(errno.ENOENT, "typed absence", path)

    def __enter__(self):
        super().__enter__()
        original_stat, original_listdir = audit.os.stat, audit.os.listdir
        original_scandir, original_readlink = audit.os.scandir, audit.os.readlink
        original_open = open
        def guarded(fn):
            def call(path, *args, **kwargs):
                self.check(path)
                if fn == original_stat and path == "/proc/7/task/7/root":
                    return SimpleNamespace(st_dev=2, st_ino=43)
                return fn(path, *args, **kwargs)
            return call
        def read(path, *args, **kwargs):
            if (self.empty_mountinfo and path.endswith("/mountinfo") and path not in self.errors
                    and path != "/proc/7/task/7/mountinfo"):
                return mock.mock_open(read_data="")(path, *args, **kwargs)
            return guarded(original_open)(path, *args, **kwargs)
        for target, value in [("stat", guarded(original_stat)), ("listdir", guarded(original_listdir)),
                              ("scandir", guarded(original_scandir)), ("readlink", guarded(original_readlink))]:
            self.stack.enter_context(mock.patch.object(audit.os, target, value))
        self.stack.enter_context(mock.patch.object(audit, "_classification_bound",
            side_effect=lambda bound, task=False: self.classes[(bound[0], bound[1] if task else None)]))
        self.stack.enter_context(mock.patch("builtins.open", side_effect=read))
        return self


def stat_row(pid, overrides=None, classification="kernel-thread"):
    fields = ["S"] + ["0"] * 49
    fields[6] = str(0x00200000 if classification == "kernel-thread" else 0)
    fields[0] = "Z" if classification == "zombie" else "S"
    fields[19] = "123"
    for number, value in (overrides or {}).items():
        fields[number - 3] = str(value)
    return "%d (fixture) %s\n" % (pid, " ".join(fields))


class StatProcFixture(SpecialProcFixture):
    """Run the production identity/classification parser throughout a census."""
    def __init__(self, classification, overrides):
        super().__init__(classification)
        self.overrides = overrides

    def __enter__(self):
        identity, classify = audit._identity, audit._classification_bound
        super().__enter__()
        ordinary_open = open
        def read(path, *args, **kwargs):
            if path.endswith("/stat"):
                parts = path.split("/")
                pid = int(parts[-2])
                key = (int(parts[2]), pid if "task" in parts else None)
                data = stat_row(pid, self.overrides.get(path), self.classes[key])
                return mock.mock_open(read_data=data)(path, *args, **kwargs)
            return ordinary_open(path, *args, **kwargs)
        self.stack.enter_context(mock.patch.object(audit, "_identity", identity))
        self.stack.enter_context(mock.patch.object(audit, "_classification_bound", classify))
        self.stack.enter_context(mock.patch("builtins.open", side_effect=read))
        return self


class DeletedInodeAuditTests(unittest.TestCase):
    @contextmanager
    def mount_views(self, roots=None, namespaces=None, data=None):
        """Override only proc mount surfaces; run the entire production census."""
        roots, namespaces, data = roots or {}, namespaces or {}, data or {}
        counts = {}
        original_link, original_open = audit.os.readlink, open
        def value(table, base, fallback):
            result = table.get(base, fallback)
            if isinstance(result, list):
                key = (id(table), base)
                index = counts.get(key, 0)
                counts[key] = index + 1
                result = result[min(index, len(result) - 1)]
            if isinstance(result, Exception):
                raise result
            return result
        def linked(path):
            if path.endswith("/root"):
                return value(roots, path[:-5], "/")
            if path.endswith("/ns/mnt"):
                return value(namespaces, path[:-7], "mnt:[41]")
            return original_link(path)
        def opened(path, *args, **kwargs):
            if path.endswith("/mountinfo"):
                content = value(data, path[:-10], "31 26 0:26 / /dev/shm rw - tmpfs tmpfs rw\n")
                return mock.mock_open(read_data=content)(path, *args, **kwargs)
            return original_open(path, *args, **kwargs)
        with mock.patch.object(audit.os, "readlink", side_effect=linked), \
                mock.patch("builtins.open", side_effect=opened):
            yield

    def test_full_census_chroot_views_require_exact_full_representative(self):
        peer = "/proc/7/task/8"
        for content in ("", "31 26 0:27 /subdir /inside rw - tmpfs tmpfs rw\n"):
            for namespace, accepted in (("mnt:[41]", True), ("mnt:[42]", False)):
                with ProcFixture(), self.mount_views({peer: "/etc/avahi"}, {peer: namespace}, {peer: content}):
                    identities, failures, _, _ = audit.audit_round(set())
                self.assertEqual(bool(identities), accepted, failures)
                self.assertEqual(not failures, accepted, failures)
                if not accepted:
                    self.assertIn("mount-namespace-uncovered:mnt:[42]", failures)

    def test_full_census_no_complete_representative_fails(self):
        bases = ("/proc/7", "/proc/7/task/7", "/proc/7/task/8")
        for content in ("", "31 26 0:26 / /visible rw - tmpfs tmpfs rw\n"):
            with ProcFixture(), self.mount_views(dict.fromkeys(bases, "/jail"), data=dict.fromkeys(bases, content)):
                identities, failures, _, _ = audit.audit_round(set())
            self.assertEqual(identities, [])
            self.assertIn("mount-namespace-uncovered:mnt:[41]", failures)
        with ProcFixture(), self.mount_views(data=dict.fromkeys(bases, "")):
            identities, failures, _, _ = audit.audit_round(set())
        self.assertEqual(identities, [])
        self.assertIn("mount-namespace-uncovered:mnt:[41]", failures)

    def test_full_census_root_and_namespace_errors_are_not_covered_by_peer(self):
        peer = "/proc/7/task/8"
        for bad in ("relative", "//", "/a/../b", "/gone (deleted)", "/bad\0name",
                    PermissionError(errno.EACCES, "denied"), FileNotFoundError(errno.ENOENT, "absent"),
                    ["/jail", "/changed"]):
            with self.subTest(root=bad), ProcFixture(), self.mount_views({peer: bad}, data={peer: ""}):
                identities, failures, _, _ = audit.audit_round(set())
            self.assertEqual(identities, [])
            self.assertTrue(any(x.startswith("mount-root-") for x in failures), failures)
        for bad in (["mnt:[41]", "mnt:[42]"], "mnt:bad", FileNotFoundError(errno.ENOENT, "gone")):
            with ProcFixture(), self.mount_views({peer: "/jail"}, {peer: bad}, {peer: ""}):
                identities, failures, _, _ = audit.audit_round(set())
            self.assertEqual(identities, [])
            self.assertTrue(failures)
        for error in (OSError(errno.EIO, "read"), PermissionError(errno.EACCES, "denied")):
            with ProcFixture(), self.mount_views({peer: "/jail"}, data={peer: error}):
                identities, failures, _, _ = audit.audit_round(set())
            self.assertEqual(identities, [])
            self.assertIn("mountinfo-uninspected:7:8", failures)
        with ProcFixture(), self.mount_views({peer: "/jail"}, data={peer: "malformed\n"}):
            identities, failures, _, _ = audit.audit_round(set())
        self.assertEqual(identities, [])
        self.assertIn("mountinfo-uninspected:7:8", failures)

    def test_aliases_are_reported_in_full_and_filtered_views(self):
        for base in ("/proc/7", "/proc/7/task/7", "/proc/7/task/8"):
            for root in ("/", "/jail"):
                with ProcFixture(), self.mount_views({base: root}, data={base:
                        "31 26 0:26 /retained/child /visible rw - tmpfs tmpfs rw\n"}):
                    identities, failures, _, _ = audit.audit_round(set(), ((26, "/retained"),))
                self.assertEqual(identities, [])
                self.assertTrue(any(x.startswith("mount-alias:") for x in failures), failures)

    def test_complete_representative_must_survive_final_revalidation(self):
        bases = ("/proc/7", "/proc/7/task/7", "/proc/7/task/8")
        roots = dict.fromkeys(bases, "/jail")
        for replacement in ("/later-chroot", PermissionError(errno.EACCES, "denied")):
            roots["/proc/7/task/7"] = ["/", "/", replacement]
            with ProcFixture(), self.mount_views(roots):
                identities, failures, _, _ = audit.audit_round(set())
            self.assertEqual(identities, [])
            self.assertIn("mount-namespace-uncovered:mnt:[41]", failures)
        roots["/proc/7/task/7"] = "/"
        with ProcFixture(), self.mount_views(roots, {"/proc/7/task/7": ["mnt:[41]", "mnt:[41]", "mnt:[42]"]}):
            identities, failures, _, _ = audit.audit_round(set())
        self.assertEqual(identities, [])
        self.assertIn("mount-representative-churn:7:7", failures)

    def test_special_mount_absence_needs_observed_exact_namespace(self):
        for classification in ("kernel-thread", "zombie"):
            for missing in ("/proc/7/ns/mnt", "/proc/7/task/8/ns/mnt"):
                with SpecialProcFixture(classification) as proc:
                    proc.absent.add(missing)
                    identities, failures, _, _ = audit.audit_round(set())
                self.assertEqual(identities, [])
                self.assertTrue(any(x.startswith("mountinfo-uninspected:") for x in failures), failures)
            with SpecialProcFixture(classification) as proc:
                proc.absent.add("/proc/7/task/7/root")
                identities, failures, _, _ = audit.audit_round(set())
            self.assertEqual(identities, [])
            self.assertIn("mount-namespace-uncovered:mnt:[41]", failures)

    def test_real_unprivileged_mount_view_authenticates_full_root(self):
        pid = os.getpid()
        self.assertEqual(os.readlink("/proc/self/root"), "/")
        coverage = {"observed": set(), "full": []}
        failures = []
        audit._scan_mountinfo(pid, failures, bound=audit._identity(pid), coverage=coverage)
        audit._finish_mount_coverage(coverage, failures)
        self.assertEqual(failures, [])
        self.assertEqual(coverage["observed"], {os.readlink("/proc/self/ns/mnt")})
        self.assertEqual(len(coverage["full"]), 1)

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
                    mock.patch.object(audit.os, "readlink", side_effect=lambda p: "/" if p.endswith("/root") else "mnt:[42]") as linked:
                audit._scan_mountinfo(7, failures, ((26, "/retained"),), 8)
                opened.assert_called_once_with("/proc/7/task/8/mountinfo", "r")
                self.assertEqual(linked.call_args_list, [mock.call("/proc/7/task/8/ns/mnt"),
                    mock.call("/proc/7/task/8/root"), mock.call("/proc/7/task/8/root"),
                    mock.call("/proc/7/task/8/ns/mnt")])
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

    def test_empty_open_mountinfo_only_defers_to_namespace_coverage(self):
        cases = [
            ("stable", {"read_data": ""}, "mnt:[42]", False),
            ("missing", {"side_effect": FileNotFoundError(errno.ENOENT, "gone")},
             "mnt:[42]", True),
            ("malformed", {"read_data": ""}, "mnt:bad", True),
            ("denied", {"read_data": ""}, PermissionError(errno.EACCES, "denied"), True),
        ]
        for name, opening, link, rejected in cases:
            if "side_effect" in opening:
                open_patch = mock.patch("builtins.open", side_effect=opening["side_effect"])
            else:
                open_patch = mock.patch("builtins.open", mock.mock_open(read_data=opening["read_data"]))
            def linked(path):
                if path.endswith("/root"):
                    return "/chroot"
                if isinstance(link, Exception):
                    raise link
                return link
            link_patch = mock.patch.object(audit.os, "readlink", side_effect=linked)
            with self.subTest(name=name), open_patch, link_patch:
                failures = []
                coverage = {"observed": set(), "full": []}
                audit._scan_mountinfo(7, failures, coverage=coverage)
            self.assertEqual(bool(failures), rejected, failures)
            self.assertEqual(coverage["full"], [])
            audit._finish_mount_coverage(coverage, failures)
            self.assertTrue(failures)
        failures = []
        links = iter(["mnt:[1]", "mnt:[2]"])
        with mock.patch("builtins.open", mock.mock_open(read_data="")), \
                mock.patch.object(audit.os, "readlink", side_effect=lambda p: "/chroot" if p.endswith("/root") else next(links)):
            audit._scan_mountinfo(7, failures)
        self.assertTrue(any(x.startswith("mount-namespace-churn:") for x in failures), failures)

    def test_open_success_read_error_never_passes_empty_mountinfo(self):
        class ReadErrorFile:
            def __enter__(self):
                return self
            def __exit__(self, *args):
                return False
            def read(self):
                raise OSError(errno.EIO, "read error")

        for allowed in (None, "kernel-thread"):
            failures = []
            with self.subTest(allowed=allowed), \
                    mock.patch("builtins.open", return_value=ReadErrorFile()), \
                    mock.patch.object(audit.os, "readlink", return_value="mnt:[42]"):
                audit._scan_mountinfo(7, failures, bound=(7, 7, "123") if allowed else None,
                                      allowed_absence=allowed)
            self.assertTrue(any(x.startswith("mountinfo-uninspected:") for x in failures), failures)

    def test_live_mountinfo_accepts_kernel_nsfs_roots(self):
        with open("/proc/self/mountinfo") as mountinfo:
            rows = audit._mount_rows(mountinfo.read())
        self.assertTrue(rows)
        nsfs = [root for _, root, _ in rows if ":" in root and not root.startswith("/")]
        self.assertTrue(nsfs)
        for root in nsfs:
            self.assertRegex(root, r"^(?:cgroup|ipc|mnt|net|pid|pid_for_children|time|time_for_children|user|uts):\[[1-9][0-9]*\]$")

    def test_nsfs_mount_root_vectors_are_strict(self):
        for token in ("mnt:[1]", "net:[4026532874]", "pid_for_children:[7]"):
            data = "24 26 0:4 %s /run/ns rw - nsfs nsfs rw\n" % token
            self.assertEqual(audit._mount_rows(data)[0][1], token)
        for fstype, token in (("tmpfs", "mnt:[1]"), ("nsfs", "relative"),
                              ("nsfs", "mnt:[0]"), ("nsfs", "mnt:[1]/x"),
                              ("nsfs", r"mnt:\040[1]"), ("nsfs", "mnt:[1] (deleted)")):
            data = "24 26 0:4 %s /run/ns rw - %s %s rw\n" % (token, fstype, fstype)
            with self.subTest(fstype=fstype, token=token), self.assertRaises(ValueError):
                audit._mount_rows(data)

    def test_tmpfs_descendant_alias_rules_remain_strict(self):
        for root in ("/retained/descendant", "/retained-other", r"/retained\040(deleted)"):
            data = "24 26 0:26 %s /alias rw - tmpfs tmpfs rw\n" % root
            failures = []
            with mock.patch("builtins.open", mock.mock_open(read_data=data)), \
                    mock.patch.object(audit.os, "readlink", return_value="mnt:[42]"):
                audit._scan_mountinfo(7, failures, ((26, "/retained"),))
            self.assertEqual(any(x.startswith("mount-alias:") for x in failures),
                             root != "/retained-other")

    def test_mount_namespace_format_and_churn_fail(self):
        for links in [["mnt:[1]", "mnt:[2]"], ["mnt:bad"], ["pid:[1]"], ["mnt:[0]"],
                      [PermissionError(errno.EACCES, "denied")]]:
            failures = []
            values = iter(links if len(links) == 2 else links * 2)
            def linked(path):
                if path.endswith("/root"):
                    return "/"
                value = next(values)
                if isinstance(value, Exception):
                    raise value
                return value
            with mock.patch("builtins.open", mock.mock_open(read_data="24 26 0:26 / /dev/shm rw - tmpfs tmpfs rw\n")), \
                    mock.patch.object(audit.os, "readlink", side_effect=linked):
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

    def test_stat_classification_uses_pf_kthread_or_zombie_state(self):
        fields = ["S", "2", "0", "0", "0", "-1"] + ["0"] * 44
        fields[6] = str(0x00200000)
        fields[19] = "123"
        kthread = "7 (bracketed-user-name) " + " ".join(fields)
        with mock.patch("builtins.open", mock.mock_open(read_data=kthread)):
            self.assertEqual(audit._read_stat(7), ("123", "kernel-thread"))
        fields[0] = "Z"
        fields[6] = "0"
        zombie = "7 (ordinary-looking-name) " + " ".join(fields)
        with mock.patch("builtins.open", mock.mock_open(read_data=zombie)):
            self.assertEqual(audit._read_stat(7), ("123", "zombie"))
        fields[0] = "S"
        fields[6] = "0"
        ordinary = "7 (kworker/0:1) " + " ".join(fields)
        with mock.patch("builtins.open", mock.mock_open(read_data=ordinary)):
            self.assertEqual(audit._read_stat(7), ("123", "ordinary"))

    def test_stat_rejects_negative_unsigned_fields_and_flag_exploits(self):
        # Proc field numbers, independent of the parser's zero-based indices.
        nonnegative = [4, 5, 6, 9, 10, 11, 12, 13, 14, 15, 20, 22, 23,
                       25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37,
                       39, 40, 41, 42, 43, 45, 46, 47, 48, 49, 50, 51]
        for number, value in [(n, "-1") for n in nonnegative] + [(9, "-2097152"), (9, "4297064448")]:
            with self.subTest(field=number, value=value):
                fields = ["S"] + ["0"] * 49
                fields[19] = "123"
                fields[number - 3] = value
                with mock.patch("builtins.open", mock.mock_open(read_data="7 (x) " + " ".join(fields))):
                    with self.assertRaises(ValueError):
                        audit._read_stat(7)
                    with self.assertRaises(ValueError):
                        audit._classification_bound((7, 7, "123"))

    def test_stat_preserves_legitimately_signed_fields_and_real_self(self):
        fields = ["S"] + ["0"] * 49
        fields[19] = "123"
        for number in (7, 8, 16, 17, 18, 19, 21, 24, 38, 44, 52):
            fields[number - 3] = "-1"
        with mock.patch("builtins.open", mock.mock_open(read_data="7 (x) " + " ".join(fields))):
            self.assertEqual(audit._read_stat(7), ("123", "ordinary"))
        self.assertEqual(audit._read_stat(os.getpid())[1], "ordinary")

    def test_stat_linux_lp64_width_boundaries(self):
        # Local proc(5) format declarations: %d, %u, %ld, %lu/%llu.
        groups = [([7, 8, 38, 52], -(1 << 31), (1 << 31) - 1),
                  ([4, 5, 6, 39], 0, (1 << 31) - 1),
                  ([9, 40, 41], 0, (1 << 32) - 1),
                  ([16, 17, 18, 19, 21, 24, 44], -(1 << 63), (1 << 63) - 1),
                  ([20], 0, (1 << 63) - 1),
                  ([10, 11, 12, 13, 14, 15, 22, 23, 25, 26, 27, 28, 29, 30,
                    31, 32, 33, 34, 35, 36, 37, 42, 43, 45, 46, 47, 48, 49, 50, 51],
                   0, (1 << 64) - 1)]
        self.assertEqual(sorted(n for numbers, _, _ in groups for n in numbers), list(range(4, 53)))
        for numbers, minimum, maximum in groups:
            for number in numbers:
                for value in (minimum, maximum, minimum - 1, maximum + 1):
                    with self.subTest(field=number, value=value), \
                            mock.patch("builtins.open", mock.mock_open(read_data=stat_row(7, {number: value}))):
                        if minimum <= value <= maximum:
                            audit._read_stat(7)
                        else:
                            with self.assertRaises(ValueError):
                                audit._read_stat(7)
        for pid in (0, 1 << 31):
            with mock.patch("builtins.open", mock.mock_open(read_data=stat_row(pid))), self.assertRaises(ValueError):
                audit._read_stat(pid)

    def test_full_census_malformed_stat_cannot_grant_special_absence(self):
        invalid = [(4, 1 << 31), (7, -(1 << 31) - 1), (8, 1 << 31),
                   (9, 1 << 32), (10, 1 << 64), (18, -(1 << 63) - 1),
                   (20, 1 << 63), (22, 1 << 64), (23, 1 << 64),
                   (24, 1 << 63), (39, 1 << 31), (40, 1 << 32),
                   (41, 1 << 32), (44, -(1 << 63) - 1), (52, 1 << 31)]
        for classification in ("kernel-thread", "zombie"):
            for path in ("/proc/7/stat", "/proc/7/task/7/stat", "/proc/7/task/8/stat"):
                for number, value in invalid:
                    with self.subTest(classification=classification, path=path, field=number), \
                            StatProcFixture(classification, {path: {number: value}}):
                        identities, failures, refs, _ = audit.audit_round(set())
                    self.assertEqual(identities, [])
                    self.assertEqual(refs, [])
                    expected = "identity:7:malformed" if path == "/proc/7/stat" else "task-identity:7:" + path.split("/")[-2]
                    self.assertIn(expected, failures)

    def test_full_census_valid_stat_boundaries_preserve_special_absence(self):
        valid = {7: -(1 << 31), 8: -1, 10: (1 << 64) - 1, 18: -(1 << 63),
                 19: -20, 22: (1 << 64) - 1, 23: (1 << 64) - 1,
                 24: (1 << 63) - 1, 25: (1 << 64) - 1, 44: -(1 << 63), 52: -(1 << 31)}
        for classification in ("kernel-thread", "zombie"):
            overrides = {path: valid for path in ("/proc/7/stat", "/proc/7/task/7/stat", "/proc/7/task/8/stat")}
            with StatProcFixture(classification, overrides):
                identities, failures, refs, _ = audit.audit_round(set())
            self.assertEqual(failures, [])
            self.assertEqual(refs, [])
            self.assertEqual(set(identities), {(7, 7, str((1 << 64) - 1)), (7, 8, str((1 << 64) - 1))})

    def test_real_pid2_stat_when_exposed(self):
        try:
            parsed = audit._read_stat(2)
        except FileNotFoundError:
            self.skipTest("PID 2 is absent in this PID namespace")
        self.assertTrue(parsed[0].isdigit())
        self.assertIn(parsed[1], ("ordinary", "kernel-thread", "zombie"))

    def test_full_census_map_files_requires_unsigned_64bit_ordered_addresses(self):
        for entry in ("10000000000000000-10000000000001000", "1-10000000000000000",
                      "ffffffffffffffff-ffffffffffffffff", "ffffffffffffffff-0"):
            with self.subTest(entry=entry), ProcFixture() as proc:
                proc.directories["/proc/7/map_files"] = [entry]
                identities, failures, refs, _ = audit.audit_round(set())
            self.assertEqual(identities, [])
            self.assertIn("malformed-map-entry:7", failures)
            self.assertEqual(refs, [])
        for entry in ("0-1", "fffffffffffffffe-ffffffffffffffff", "0-ffffffffffffffff"):
            with self.subTest(entry=entry), ProcFixture() as proc:
                proc.directories["/proc/7/map_files"] = [entry]
                identities, failures, refs, counters = audit.audit_round({(1, 42)})
            self.assertTrue(identities)
            self.assertEqual(failures, [])
            self.assertEqual(counters["map_files_entries"], 1)
            self.assertIn({"identity": [1, 42], "source": "map_files/7/" + entry}, refs)

    def test_missing_or_invalid_mnt_namespace_never_hides_existing_alias(self):
        data = "24 26 0:26 /retained/child /elsewhere rw - tmpfs tmpfs rw\n"
        for classification in ("kernel-thread", "zombie", "ordinary"):
            for error in (FileNotFoundError(errno.ENOENT, "gone"),
                          PermissionError(errno.EACCES, "denied"), ValueError("malformed")):
                for tid in (None, 8):
                    with self.subTest(classification=classification, error=error, tid=tid):
                        failures = []
                        with mock.patch.object(audit, "_namespace", side_effect=error), \
                                mock.patch.object(audit, "_identity_state", return_value=audit.IdentityState.LIVE), \
                                mock.patch.object(audit, "_classification_bound", return_value=classification), \
                                mock.patch("builtins.open", mock.mock_open(read_data=data)) as read:
                            audit._scan_mountinfo(7, failures, ((os.makedev(0, 26), "/retained"),), tid,
                                                  (7, tid or 7, "123"), classification)
                        label = "7:%d" % (tid or 7)
                        self.assertIn("mount-alias:" + label, failures)
                        self.assertIn("mountinfo-uninspected:" + label, failures)
                        read.assert_called_once_with(audit._base(7, tid) + "/mountinfo", "r")

    def test_mount_namespace_churn_does_not_hide_alias_or_empty_file(self):
        for data in ("", "24 26 0:26 /retained /elsewhere rw - tmpfs tmpfs rw\n"):
            for after in ("mnt:[43]", FileNotFoundError(errno.ENOENT, "gone")):
                failures = []
                with mock.patch.object(audit, "_namespace", side_effect=["mnt:[42]", after]), \
                        mock.patch.object(audit, "_identity_state", return_value=audit.IdentityState.LIVE), \
                        mock.patch.object(audit, "_classification_bound", return_value="kernel-thread"), \
                        mock.patch("builtins.open", mock.mock_open(read_data=data)):
                    audit._scan_mountinfo(7, failures, ((os.makedev(0, 26), "/retained"),),
                                          bound=(7, 7, "123"), allowed_absence="kernel-thread")
                self.assertIn("mount-namespace-churn:7:7", failures)
                if data:
                    self.assertIn("mount-alias:7:7", failures)

    def test_special_full_census_absent_and_empty_surfaces(self):
        for classification in ("kernel-thread", "zombie"):
            for empty in (False, True):
                with self.subTest(classification=classification, empty=empty), SpecialProcFixture(classification, empty):
                    identities, failures, refs, counters = audit.audit_round(set())
                self.assertEqual(failures, [])
                self.assertEqual(set(identities), {(7, 7, "123"), (7, 8, "123")})
                self.assertEqual(refs, [])
                self.assertEqual(counters["map_files_denials"], 0)

    def test_special_full_census_denial_of_each_surface_fails(self):
        for classification in ("kernel-thread", "zombie"):
            surfaces = SpecialProcFixture(classification).absent
            for path in sorted(surfaces):
                with self.subTest(classification=classification, path=path), SpecialProcFixture(classification) as proc:
                    proc.errors[path] = PermissionError(errno.EACCES, "denied")
                    identities, failures, _, _ = audit.audit_round(set())
                self.assertEqual(identities, [])
                self.assertTrue(failures)

    def test_special_full_census_inspects_every_existing_target(self):
        for classification in ("kernel-thread", "zombie"):
            for base in ("/proc/7", "/proc/7/task/7", "/proc/7/task/8"):
                for name in ("cwd", "root", "exe", "fd", "map_files"):
                    if name == "map_files" and base != "/proc/7":
                        continue
                    if name == "root" and base == "/proc/7/task/7":
                        continue  # separately authenticated representative root
                    with self.subTest(classification=classification, base=base, name=name), SpecialProcFixture(classification) as proc:
                        proc.absent.remove(base + "/" + name)
                        if name == "fd":
                            proc.directories[base + "/fd"] = ["9"]
                        identities, failures, refs, _ = audit.audit_round({(1, 42)})
                    self.assertEqual(failures, [])
                    self.assertTrue(identities)
                    self.assertEqual(len(refs), 1, refs)
                    self.assertEqual(refs[0]["identity"], [1, 42])

    def test_special_task_class_is_never_inherited_from_leader(self):
        for classification in ("kernel-thread", "zombie"):
            with SpecialProcFixture(classification) as proc:
                proc.classes[(7, 8)] = "ordinary"
                identities, failures, _, _ = audit.audit_round(set())
            self.assertEqual(identities, [])
            self.assertIn("unresolved-target-churn:7/8/cwd", failures)

    def test_ordinary_map_files_absence_is_mandatory_and_typed_parameter_is_checked(self):
        with ProcFixture():
            listing = audit.os.listdir
            def missing(path):
                if path == "/proc/7/map_files":
                    raise FileNotFoundError(errno.ENOENT, "gone")
                return listing(path)
            with mock.patch.object(audit.os, "listdir", side_effect=missing):
                identities, failures, _, counters = audit.audit_round(set())
        self.assertEqual(identities, [])
        self.assertIn("map_files-directory:7:2", failures)
        self.assertEqual(counters["map_files_denials"], 1)
        failures = []
        with mock.patch.object(audit.os, "stat", side_effect=FileNotFoundError(errno.ENOENT, "gone")), \
                mock.patch.object(audit, "_identity_state", return_value=audit.IdentityState.LIVE), \
                mock.patch.object(audit, "_classification_bound", return_value="ordinary"):
            audit._stat_target("/proc/7/cwd", set(), failures, [], "7/cwd", bound=(7, 7, "123"),
                               allowed_absence="ordinary")
        self.assertIn("unresolved-target-churn:7/cwd", failures)

    def test_special_empty_mountinfo_never_excuses_malformed_namespace(self):
        for classification in ("kernel-thread", "zombie"):
            for link in ("mnt:bad", "pid:[41]", "mnt:[0]"):
                with SpecialProcFixture(classification, empty_mountinfo=True):
                    original = audit.os.readlink
                    def readlink(path):
                        if path == "/proc/7/task/8/ns/mnt":
                            return link
                        return original(path)
                    with mock.patch.object(audit.os, "readlink", side_effect=readlink):
                        identities, failures, _, _ = audit.audit_round(set())
                self.assertEqual(identities, [])
                self.assertTrue(any(x.startswith("mountinfo-uninspected:") for x in failures), failures)

    def test_special_task_identity_reuse_during_absence_fails(self):
        for classification in ("kernel-thread", "zombie"):
            for key in ((7, None), (7, 7), (7, 8)):
                with self.subTest(classification=classification, key=key), SpecialProcFixture(classification) as proc:
                    proc.identity_faults[(key, 2)] = (7, key[1] or 7, "999")
                    identities, failures, _, _ = audit.audit_round(set())
                self.assertEqual(identities, [])
                self.assertIn("identity-reused:7:%d" % (key[1] or 7), failures)

    def test_every_identity_class_is_revalidated_through_final_census(self):
        for classification, changed in (("kernel-thread", "ordinary"), ("zombie", "kernel-thread"),
                                         ("ordinary", "zombie")):
            for key in ((7, None), (7, 7), (7, 8)):
                for change_at in (2, 3):  # end-of-surface and final census reads
                    with self.subTest(classification=classification, key=key, change_at=change_at), ProcFixture():
                        counts = {}
                        def classify(bound, task=False):
                            current = (bound[0], bound[1] if task else None)
                            counts[current] = counts.get(current, 0) + 1
                            return changed if current == key and counts[current] >= change_at else classification
                        with mock.patch.object(audit, "_classification_bound", side_effect=classify):
                            identities, failures, _, _ = audit.audit_round(set())
                    self.assertEqual(identities, [])
                    self.assertIn("classification-churn:7:%d" % (key[1] or 7), failures)

    def test_only_bound_kernel_thread_or_zombie_absence_is_allowed(self):
        bound = (7, 7, "123")
        for classification in ("kernel-thread", "zombie"):
            failures, refs = [], []
            with mock.patch.object(audit.os, "stat", side_effect=FileNotFoundError(errno.ENOENT, "gone")), \
                    mock.patch.object(audit, "_identity_state", return_value=audit.IdentityState.LIVE), \
                    mock.patch.object(audit, "_classification_bound", return_value=classification):
                self.assertFalse(audit._stat_target("/proc/7/cwd", set(), failures, refs, "7/cwd",
                                                    bound=bound, allowed_absence=classification))
            self.assertEqual(failures, [])
        failures, refs = [], []
        with mock.patch.object(audit.os, "stat", side_effect=FileNotFoundError(errno.ENOENT, "gone")), \
                mock.patch.object(audit, "_identity_state", return_value=audit.IdentityState.LIVE):
            audit._stat_target("/proc/7/cwd", set(), failures, refs, "7/cwd", bound=bound,
                               allowed_absence="ordinary")
        self.assertTrue(any(x.startswith("unresolved-target-churn:") for x in failures), failures)

    def test_absence_classification_change_and_existing_reference_fail_or_record(self):
        bound = (7, 7, "123")
        failures, refs = [], []
        with mock.patch.object(audit.os, "stat", side_effect=FileNotFoundError(errno.ENOENT, "gone")), \
                mock.patch.object(audit, "_identity_state", return_value=audit.IdentityState.LIVE), \
                mock.patch.object(audit, "_classification_bound", return_value="ordinary"):
            audit._stat_target("/proc/7/root", set(), failures, refs, "7/root", bound=bound,
                               allowed_absence="zombie")
        self.assertIn("classification-churn:7:7", failures)
        failures, refs = [], []
        with mock.patch.object(audit.os, "stat", return_value=SimpleNamespace(st_dev=1, st_ino=42)), \
                mock.patch.object(audit, "_identity_state", return_value=audit.IdentityState.LIVE), \
                mock.patch.object(audit, "_classification_bound", return_value="kernel-thread"):
            self.assertTrue(audit._stat_target("/proc/7/exe", {(1, 42)}, failures, refs, "7/exe", bound=bound,
                                               allowed_absence="kernel-thread"))
        self.assertEqual(refs, [{"identity": [1, 42], "source": "7/exe"}])
        self.assertEqual(failures, [])

    def test_full_process_scan_allows_only_typed_kernel_or_zombie_surfaces(self):
        for classification in ("kernel-thread", "zombie"):
            with self.subTest(classification=classification), ProcFixture() as proc:
                real_stat = proc.stat
                def stat(path):
                    if path in ("/proc/7/cwd", "/proc/7/root", "/proc/7/exe"):
                        raise FileNotFoundError(errno.ENOENT, "gone")
                    return real_stat(path)
                real_scandir = audit.os.scandir
                def scandir(path):
                    if path == "/proc/7/fd":
                        raise FileNotFoundError(errno.ENOENT, "gone")
                    return real_scandir(path)
                real_listdir = audit.os.listdir
                def listdir(path):
                    if path == "/proc/7/map_files":
                        raise FileNotFoundError(errno.ENOENT, "gone")
                    return real_listdir(path)
                with mock.patch.object(audit, "_classification_bound", return_value=classification), \
                        mock.patch.object(audit.os, "stat", side_effect=stat), \
                        mock.patch.object(audit.os, "scandir", side_effect=scandir), \
                        mock.patch.object(audit.os, "listdir", side_effect=listdir), \
                        mock.patch("builtins.open", mock.mock_open(read_data="")):
                    failures, refs, counters = [], [], {"processes": 0, "tasks": 0,
                                                        "map_files_entries": 0, "map_files_denials": 0}
                    result = audit._scan_process(7, set(), failures, refs, counters)
                self.assertEqual(result, (7, 7, "123"))
                self.assertEqual(failures, [])

    def test_ordinary_process_missing_surface_and_namespace_denial_fail(self):
        with ProcFixture() as proc:
            real_stat = proc.stat
            def stat(path):
                if path == "/proc/7/cwd":
                    raise FileNotFoundError(errno.ENOENT, "gone")
                return real_stat(path)
            with mock.patch.object(audit.os, "stat", side_effect=stat), \
                    mock.patch.object(audit, "_classification_bound", return_value="ordinary"):
                failures, refs, counters = [], [], {"processes": 0, "tasks": 0,
                                                    "map_files_entries": 0, "map_files_denials": 0}
                self.assertIsNone(audit._scan_process(7, set(), failures, refs, counters))
                self.assertTrue(any(x.startswith("unresolved-target-churn:") for x in failures), failures)
        failures = []
        with mock.patch.object(audit, "_namespace", side_effect=PermissionError(errno.EACCES, "denied")):
            audit._scan_namespace("/proc/7", "pid", failures, (7, 7, "123"), "kernel-thread")
        self.assertTrue(any(x.endswith(":13") for x in failures), failures)

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
