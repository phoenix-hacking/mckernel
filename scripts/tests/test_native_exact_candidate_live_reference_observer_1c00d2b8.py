#!/usr/bin/env python3
"""Focused pure and mmap regression tests for observer v3."""
import importlib.util
import ctypes
import mmap
import os
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
from pathlib import Path
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[2]
ADAPTER_PATH = ROOT / 'docs/verification/evidence/native-exact-candidate-live-reference-observer-1c00d2b8-1.py'


def load_adapter():
    spec = importlib.util.spec_from_file_location('retirement_observer_1c00d2b8_3', ADAPTER_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ObserverV3Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.observer = load_adapter()

    def test_self_test_and_compile(self):
        result = subprocess.run([sys.executable, str(ADAPTER_PATH), '--self-test'],
                                cwd=ROOT, capture_output=True, text=True, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('observer v3 pure synthetic assertions passed', result.stdout)

    def test_exact_adapter_target_paths_and_rejections(self):
        o = self.observer
        self.assertEqual(o.parse_targets(['--target', str(o.ORIGINAL[0]), '--target',
                                          str(o.ORIGINAL[1])]), o.ORIGINAL)
        self.assertEqual(o.parse_targets(['--target', str(o.QUARANTINE[0]), '--target',
                                          str(o.QUARANTINE[1])]), o.QUARANTINE)
        for first, second in ((o.ORIGINAL[1], o.ORIGINAL[0]),
                              (o.ORIGINAL[0], o.QUARANTINE[1]),
                              (Path('/dev/shm/arbitrary-a'), Path('/dev/shm/arbitrary-b'))):
            with self.subTest(first=first, second=second):
                with self.assertRaises(RuntimeError):
                    o.parse_targets(['--target', str(first), '--target', str(second)])

    def test_root_owner_and_path_revalidation_are_bound(self):
        o = self.observer
        before = SimpleNamespace(st_dev=1, st_ino=2, st_uid=3, st_gid=4, st_mode=0o40700)
        changed = SimpleNamespace(st_dev=1, st_ino=2, st_uid=30, st_gid=4, st_mode=0o40700)
        child = SimpleNamespace(st_dev=1, st_ino=3, st_uid=3, st_gid=4, st_mode=0o100600)
        self.assertNotEqual(o.node_identity(before), o.node_identity(changed))
        baseline = {'path': '/synthetic', 'root_identity': o.node_identity(before),
                    'members': {o.node_identity(before), o.node_identity(child)},
                    'member_count': 2,
                    'membership_sha256': o.membership_digest(
                        {o.node_identity(before), o.node_identity(child)})}
        original = o.tree_baseline
        try:
            o.tree_baseline = lambda path: dict(
                baseline, root_identity=o.node_identity(changed),
                members={o.node_identity(changed), o.node_identity(child)},
                membership_sha256=o.membership_digest(
                    {o.node_identity(changed), o.node_identity(child)}))
            failure = o.revalidate_tree(baseline)
        finally:
            o.tree_baseline = original
        self.assertEqual(failure['kind'], 'tree-root-identity-changed')

    def test_emitted_root_owner_is_from_observed_root(self):
        o = self.observer
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / 'root'
            root.mkdir()
            real_info = root.stat()
            names = ('starttime', 'mount_rows', 'open_tree', 'coordinate', 'canonical',
                     'task_set', 'revalidate_tree', 'utcnow')
            original = {name: getattr(o, name) for name in names}
            fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY)
            try:
                o.starttime = lambda path: '1'
                o.mount_rows = lambda pid, tid: []
                o.open_tree = lambda path: (real_info, {o.node_identity(real_info)},
                                                   os.dup(fd), [])
                o.coordinate = lambda path, rows: ('0:0', '/', {'device': '0:0'})
                o.canonical = lambda rows, targets: {
                    'device': '0:0', 'root': '/', 'mountpoint': '/dev/shm',
                    'filesystem': 'tmpfs'}
                o.task_set = lambda: set()
                o.revalidate_tree = lambda baseline: None
                o.utcnow = lambda: '1970-01-01T00:00:00Z'
                result = o.observe((root, root))
            finally:
                for name, value in original.items():
                    setattr(o, name, value)
                try:
                    os.close(fd)
                except OSError:
                    pass
            self.assertEqual(result['status'], 'FAIL')  # Empty proc census never authorizes deletion.
            self.assertEqual(result['roots'][0]['uid'], real_info.st_uid)
            self.assertEqual(result['roots'][0]['gid'], real_info.st_gid)

    def test_process_map_files_detects_closed_fd_mmap(self):
        o = self.observer
        with tempfile.TemporaryDirectory() as directory:
            mapped = Path(directory) / 'mapped-file'
            mapped.write_bytes(b'x' * mmap.PAGESIZE)
            fd = os.open(mapped, os.O_RDONLY)
            # Use the libc syscall directly: Python's mmap wrapper may retain
            # an internal duplicate descriptor, defeating this regression.
            libc = ctypes.CDLL(None, use_errno=True)
            libc.mmap.restype = ctypes.c_void_p
            libc.munmap.argtypes = [ctypes.c_void_p, ctypes.c_size_t]
            address = libc.mmap(None, mmap.PAGESIZE, 1, 2, fd, 0)
            self.assertNotEqual(address, ctypes.c_void_p(-1).value)
            os.close(fd)
            try:
                expected = (mapped.stat().st_dev, mapped.stat().st_ino)
                fd_matches = []
                with os.scandir('/proc/self/fd') as entries:
                    for entry in entries:
                        try:
                            info = Path(entry.path).stat()
                        except FileNotFoundError:
                            continue
                        if (info.st_dev, info.st_ino) == expected:
                            fd_matches.append(entry.name)
                self.assertEqual(fd_matches, [], 'descriptor scan unexpectedly found closed fd')
                pid, tid = os.getpid(), os.getpid()
                process_map_dir = Path('/proc') / str(pid) / 'map_files'
                task_map_dir = Path('/proc') / str(pid) / 'task' / str(tid) / 'map_files'
                self.assertEqual(process_map_dir, Path('/proc/self/map_files').resolve())
                self.assertNotEqual(process_map_dir, task_map_dir)
                map_matches = []
                # Unprivileged kernels deny stat(2) on map_files symlinks.
                # readlink(2) remains available, so resolve the link and bind
                # its target back to the exact dev/inode of the mapped file.
                with os.scandir('/proc/self/map_files') as entries:
                    for entry in entries:
                        try:
                            target = os.readlink(entry.path)
                            info = Path(target).stat()
                        except (FileNotFoundError, PermissionError):
                            continue
                        if (info.st_dev, info.st_ino) == expected:
                            map_matches.append(entry.name)
                self.assertTrue(map_matches, 'process map_files did not expose the mmap')

                who = (pid, tid, o.starttime(Path('/proc') / str(pid) / 'stat'))
                reference = {'device': '0:0', 'root': '/', 'mountpoint': '/dev/shm',
                             'filesystem': 'tmpfs'}

                def scan_stat(path):
                    path = Path(path)
                    if path.parent == process_map_dir:
                        target = os.readlink(path)
                        if target == str(mapped):
                            return mapped.stat()
                        # Unprivileged map_files stat is denied; retain the
                        # real target entry while forcing a fail-closed scan.
                        raise PermissionError(target)
                    return path.stat()

                record = o.scan_identity(
                    who, [], reference, {expected}, pid, set(),
                    stat_reader=scan_stat,
                    mount_reader=lambda scan_pid, scan_tid: [{
                        'mount_id': '1', 'parent_id': '0', 'device': '0:0',
                        'root': '/', 'mountpoint': '/dev/shm', 'options': 'rw',
                        'optional_fields': [], 'filesystem': 'tmpfs', 'source': 'tmpfs',
                        'super_options': ['rw']}])
                map_refs = [item for item in record['references']
                            if item['field'].startswith('map_files/')]
                self.assertTrue(any((item['device'], item['inode']) == expected
                                    for item in map_refs))
                self.assertFalse(record['successful'])
            finally:
                self.assertEqual(libc.munmap(address, mmap.PAGESIZE), 0)

    def test_map_range_validation_rejects_equal_reversed_and_overflow(self):
        o = self.observer
        self.assertTrue(o.valid_map_range('10-20'))
        for name in ('10-10', '20-10', '10000000000000000-10000000000000001',
                     '10-', '-20', '0x10-20', '10-20-extra', 'gg-20'):
            with self.subTest(name=name):
                self.assertFalse(o.valid_map_range(name))

    def test_missing_whole_process_map_files_is_incomplete_live(self):
        o = self.observer
        with tempfile.TemporaryDirectory() as directory:
            proc = Path(directory)
            task = proc / '123' / 'task' / '456'
            (task / 'fd').mkdir(parents=True)
            (task / 'ns').mkdir()
            for field in ('cwd', 'root', 'exe'):
                (task / field).symlink_to('/')
            who = (123, 456, '9')
            record = o.scan_identity(
                who, [], {'device': '0:0', 'root': '/', 'mountpoint': '/dev/shm', 'filesystem': 'tmpfs'},
                set(), 1, set(), proc_root=proc,
                identity_reader=lambda pid, tid: who,
                mount_reader=lambda pid, tid: [],
                link_reader=lambda path: '/')
            self.assertFalse(record['successful'])
            self.assertTrue(any(item.get('resolution') ==
                                'whole-directory-missing-while-live'
                                for item in record['incomplete']))

    def test_malformed_map_files_entry_fails_closed(self):
        o = self.observer
        with tempfile.TemporaryDirectory() as directory:
            proc = Path(directory)
            task = proc / '8' / 'task' / '8'
            (task / 'fd').mkdir(parents=True)
            (proc / '8' / 'map_files').mkdir(parents=True)
            (task / 'ns').mkdir()
            for field in ('cwd', 'root', 'exe'):
                (task / field).symlink_to('/')
            (task / 'ns' / 'mnt').symlink_to('/proc/1/ns/mnt')
            (proc / '8' / 'map_files' / 'not-a-vma').symlink_to('/')
            who = (8, 8, '1')
            result = o.scan_identity(
                who, [], {'device': '0:0', 'root': '/', 'mountpoint': '/dev/shm', 'filesystem': 'tmpfs'},
                set(), 1, set(), proc_root=proc,
                identity_reader=lambda pid, tid: who,
                mount_reader=lambda pid, tid: [],
                link_reader=lambda path: '/')
            self.assertFalse(result['successful'])
            self.assertTrue(any(item.get('resolution') == 'malformed-entry'
                                for item in result['incomplete']))

    def scan_fixture(self, coverage=None):
        o = self.observer
        a = o.audit_module()
        return o.scan_identity((7, 8, '123'), [], {}, {(1, 42)}, 999, set(),
                               identity_reader=lambda pid, tid: a._identity(pid, tid),
                               stat_reader=lambda path: a.os.stat(str(path)),
                               mount_reader=lambda pid, tid: [], mount_coverage=coverage)

    def test_exact_reviewed_audit_bytes_are_imported(self):
        import hashlib
        o = self.observer
        path = ROOT / 'scripts/native_exact_candidate_deleted_inode_audit.py'
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), o.AUDIT_SHA256)
        self.assertEqual(o.audit_module()._read_stat(os.getpid())[1], 'ordinary')
        with mock.patch.object(o, '_AUDIT', None), mock.patch.object(o, 'AUDIT_SHA256', '0' * 64):
            with self.assertRaisesRegex(RuntimeError, 'audit source hash'):
                o.audit_module()

    def test_typed_special_absence_and_all_existing_surfaces(self):
        from scripts.tests import test_native_exact_candidate_deleted_inode_audit as reference
        a = self.observer.audit_module()
        for kind in ('kernel-thread', 'zombie'):
            with self.subTest(kind=kind), mock.patch.object(reference, 'audit', a):
                fixture = reference.SpecialProcFixture(kind)
                with fixture:
                    coverage = {'observed': set(), 'full': []}
                    # The leader authenticates the namespace's full '/' view.
                    errors = []
                    a._scan_mountinfo(7, errors, (), 7, (7, 7, '123'), kind, coverage)
                    result = self.scan_fixture(coverage)
                    a._finish_mount_coverage(coverage, errors)
                    self.assertEqual(errors, [])
                    self.assertTrue(result['successful'], result)
                    self.assertEqual({x['field'] for x in result['expected_absences']}, {'cwd', 'root', 'exe'})
                for surface in ('cwd', 'root', 'exe', 'fd/3', 'map_files/1000-2000'):
                    fixture = reference.SpecialProcFixture(kind)
                    if surface.startswith('map_files/'):
                        fixture.absent.remove('/proc/7/map_files')
                    elif surface.startswith('fd/'):
                        fixture.absent.remove('/proc/7/task/8/fd')
                        fixture.directories['/proc/7/task/8/fd'] = ['3']
                    else:
                        fixture.absent.remove('/proc/7/task/8/' + surface)
                    with self.subTest(surface=surface), fixture:
                        result = self.scan_fixture()
                        self.assertFalse(result['successful'])
                        self.assertTrue(any(x['field'] == surface for x in result['references']), result)

    def test_ordinary_absence_denial_and_classification_churn_fail_closed(self):
        from scripts.tests import test_native_exact_candidate_deleted_inode_audit as reference
        a = self.observer.audit_module()
        with mock.patch.object(reference, 'audit', a):
            for kind in ('ordinary', 'kernel-thread'):
                fixture = reference.SpecialProcFixture(kind)
                if kind == 'kernel-thread':
                    fixture.errors['/proc/7/task/8/exe'] = PermissionError(13, 'denied')
                with fixture:
                    result = self.scan_fixture()
                    self.assertFalse(result['successful'])
                    if kind == 'ordinary':
                        self.assertTrue(any(x['field'] == 'exe' for x in result['incomplete']))
                    else:
                        self.assertTrue(any(x['field'] == 'exe' for x in result['denials']))
            with reference.SpecialProcFixture('kernel-thread'):
                with mock.patch.object(a, '_classification_bound', side_effect=['kernel-thread'] + ['ordinary'] * 100):
                    result = self.scan_fixture()
                    self.assertFalse(result['successful'])
                    self.assertTrue(any('classification-churn' in x.get('resolution', '') for x in result['incomplete']))

    def test_namespace_coverage_and_parser_use_actual_reviewed_implementation(self):
        from scripts.tests import test_native_exact_candidate_deleted_inode_audit as reference
        a = self.observer.audit_module()
        # These retained vectors invoke the actual scanner and finalizer now
        # consumed by this observer, including full census and nsfs controls.
        names = ('test_full_census_chroot_views_require_exact_full_representative',
                 'test_full_census_no_complete_representative_fails',
                 'test_full_census_root_and_namespace_errors_are_not_covered_by_peer',
                 'test_complete_representative_must_survive_final_revalidation',
                 'test_empty_open_mountinfo_only_defers_to_namespace_coverage',
                 'test_nsfs_mount_root_vectors_are_strict',
                 'test_stat_rejects_negative_unsigned_fields_and_flag_exploits',
                 'test_stat_linux_lp64_width_boundaries')
        with mock.patch.object(reference, 'audit', a):
            for name in names:
                with self.subTest(vector=name):
                    getattr(reference.DeletedInodeAuditTests(), name)()


if __name__ == '__main__':
    unittest.main()
