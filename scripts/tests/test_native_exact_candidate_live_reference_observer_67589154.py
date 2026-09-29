#!/usr/bin/env python3
"""Pure regression tests for the 67589154 observer adapter.

These tests import helpers and run the observer's synthetic self-test only;
they never create, scan, or retire live roots.
"""
import importlib.util
import os
import subprocess
import sys
import tempfile
import unittest
from types import SimpleNamespace
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
ADAPTER_PATH = ROOT / 'docs/verification/evidence/native-exact-candidate-live-reference-observer-67589154-1.py'
REVIEWED_PATH = ROOT / 'docs/verification/evidence/native-exact-candidate-live-reference-observer-68cf089a-2.py'


def load_adapter():
    spec = importlib.util.spec_from_file_location('retirement_observer_67589154', ADAPTER_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ObserverAdapterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.observer = load_adapter()

    def test_admits_only_exact_ordered_pairs(self):
        o = self.observer
        self.assertEqual(o.parse_targets([
            '--target', str(o.ORIGINAL[0]), '--target', str(o.ORIGINAL[1])]), o.ORIGINAL)
        self.assertEqual(o.parse_targets([
            '--target', str(o.QUARANTINE[0]), '--target', str(o.QUARANTINE[1])]), o.QUARANTINE)

    def test_rejects_mixing_reversal_and_arbitrary_pairs(self):
        o = self.observer
        rejected = (
            (o.ORIGINAL[0], o.QUARANTINE[1]),
            (o.QUARANTINE[0], o.ORIGINAL[1]),
            (o.ORIGINAL[1], o.ORIGINAL[0]),
            (Path('/dev/shm/arbitrary-a'), Path('/dev/shm/arbitrary-b')),
        )
        for first, second in rejected:
            with self.subTest(first=first, second=second):
                with self.assertRaises(RuntimeError):
                    o.parse_targets(['--target', str(first), '--target', str(second)])

    def test_source_self_test_is_pure_and_passes(self):
        result = subprocess.run(
            [sys.executable, str(ADAPTER_PATH), '--self-test'],
            cwd=ROOT, capture_output=True, text=True, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('pure synthetic assertions passed', result.stdout)

    def test_emitted_root_uid_gid_come_from_root_identity(self):
        o = self.observer
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / 'root'
            root.mkdir()
            target = (root,)
            real_info = root.stat()
            original = {name: getattr(o, name) for name in
                        ('starttime', 'mount_rows', 'open_tree', 'coordinate', 'canonical',
                         'task_set', 'revalidate_tree', 'utcnow')}
            fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY)
            try:
                o.starttime = lambda path: '1'
                o.mount_rows = lambda pid, tid: []
                o.open_tree = lambda path: (real_info, {o.node_identity(real_info)}, fd, [])
                o.coordinate = lambda path, rows: ('0:0', '/', {'device': '0:0'})
                o.canonical = lambda rows, targets: {'device': '0:0', 'root': '/',
                                                     'mountpoint': '/dev/shm', 'filesystem': 'tmpfs'}
                o.task_set = lambda: set()
                o.revalidate_tree = lambda baseline: None
                o.utcnow = lambda: '1970-01-01T00:00:00Z'
                result = o.observe(target)
            finally:
                for name, value in original.items():
                    setattr(o, name, value)
                try:
                    os.close(fd)
                except OSError:
                    pass
            self.assertEqual(result['status'], 'PASS')
            self.assertEqual(result['roots'][0]['uid'], real_info.st_uid)
            self.assertEqual(result['roots'][0]['gid'], real_info.st_gid)
            self.assertEqual(result['roots'][0]['tree_member_identities'],
                             [list(o.node_identity(real_info))])

    def test_node_identity_and_revalidation_bind_owner_changes(self):
        o = self.observer
        before = SimpleNamespace(st_dev=1, st_ino=2, st_uid=3, st_gid=4, st_mode=0o40700)
        changed = SimpleNamespace(st_dev=1, st_ino=2, st_uid=30, st_gid=4, st_mode=0o40700)
        child = SimpleNamespace(st_dev=1, st_ino=3, st_uid=3, st_gid=4, st_mode=0o100600)
        changed_child = SimpleNamespace(st_dev=1, st_ino=3, st_uid=3, st_gid=40, st_mode=0o100600)
        self.assertNotEqual(o.node_identity(before), o.node_identity(changed))
        baseline = {'path': '/synthetic', 'root_identity': o.node_identity(before),
                    'members': {o.node_identity(before), o.node_identity(child)}, 'member_count': 2,
                    'membership_sha256': o.membership_digest({o.node_identity(before), o.node_identity(child)})}
        original = o.tree_baseline
        try:
            o.tree_baseline = lambda path: dict(baseline,
                                                members={o.node_identity(before), o.node_identity(changed_child)},
                                                membership_sha256=o.membership_digest({o.node_identity(before), o.node_identity(changed_child)}))
            failure = o.revalidate_tree(baseline)
            self.assertEqual(failure['kind'], 'tree-membership-changed')
            o.tree_baseline = lambda path: dict(baseline, root_identity=o.node_identity(changed),
                                                members={o.node_identity(changed), o.node_identity(child)},
                                                membership_sha256=o.membership_digest({o.node_identity(changed), o.node_identity(child)}))
            failure = o.revalidate_tree(baseline)
        finally:
            o.tree_baseline = original
        self.assertEqual(failure['kind'], 'tree-root-identity-changed')

    def test_semantics_match_reviewed_source_except_exact_adapter_naming(self):
        adapted = ADAPTER_PATH.read_text(encoding='utf-8')
        reviewed = REVIEWED_PATH.read_text(encoding='utf-8')
        replacements = {
            'retirement cleanup roots': 'quarantined cleanup roots',
            'mckernel-exact-candidate-67589154-1': 'mckernel-exact-candidate-68cf089a-1',
            'mckernel-exact-metadata-backup-67589154-1': 'mckernel-exact-metadata-backup-68cf089a-1',
            '.mckernel-retirement-candidate-67589154-1': '.mckernel-quarantine-mckernel-exact-candidate-68cf089a-1',
            '.mckernel-retirement-metadata-backup-67589154-1': '.mckernel-quarantine-mckernel-exact-metadata-backup-68cf089a-1',
        }
        for old, new in replacements.items():
            adapted = adapted.replace(old, new)
        adapted = adapted.replace("                            'uid': info.st_uid, 'gid': info.st_gid,\n", '')
        adapted = adapted.replace("    return (info.st_dev, info.st_ino, info.st_uid, info.st_gid,\n            stat.S_IFMT(info.st_mode), stat.S_IMODE(info.st_mode))\n", "    return (info.st_dev, info.st_ino, stat.S_IFMT(info.st_mode), stat.S_IMODE(info.st_mode))\n")
        adapted = adapted.replace("    text = ''.join(':'.join(str(value) for value in member) + '\\n' for member in sorted(members))\n", "    text = ''.join('%d:%d\\n' % member for member in sorted(members))\n")
        adapted = adapted.replace("            found, stack = {node_identity(initial)}, [(rootfd, initial.st_dev)]\n", "            found, stack = {(initial.st_dev, initial.st_ino)}, [(rootfd, initial.st_dev)]\n")
        adapted = adapted.replace("                            found.add(node_identity(info))\n", "                            found.add((info.st_dev, info.st_ino))\n")
        adapted = adapted.replace("            inode_ids.update((member[0], member[1]) for member in members)\n", "            inode_ids.update(members)\n")
        self.assertEqual(adapted, reviewed)


if __name__ == '__main__':
    unittest.main()
