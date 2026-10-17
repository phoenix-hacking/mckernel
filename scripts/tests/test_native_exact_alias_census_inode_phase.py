"""Exact extracted active-census functions; disposable inode/race controls."""
import ast
import hashlib
import os
from pathlib import Path
import stat
import tempfile
import time
import types
import unittest
from unittest import mock


WORKTREE = Path(__file__).resolve().parents[2]
SOURCE = WORKTREE / 'scripts/prepare_native_exact_scratch22_authority3.py'
ORIGINAL = Path('/home/holden/mckernel/scripts/prepare_native_exact_scratch22_authority3.py')
ANCESTOR = Path('/home/holden/mckernel/docs/verification/evidence/native-exact-candidate-delta-preparation-scratch18-20261001.py')
BASE_SHA = '1f6aa36d4cf64d03ea62989248ed522b8575b1ab56d66cc66c211e9a8260fbf5'


class Refusal(RuntimeError):
    pass


def extracted(path, names, **extra):
    tree = ast.parse(path.read_text())
    selected = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in names]
    if {node.name for node in selected} != set(names):
        raise AssertionError('actual function extraction incomplete')
    scope = dict(Path=Path, os=os, stat=stat, hashlib=hashlib, Refusal=Refusal, **extra)
    exec(compile(ast.Module(body=selected, type_ignores=[]), str(path), 'exec'), scope)
    return scope


class InodePhaseTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='alias-inode-phase-')
        self.addCleanup(self.temporary.cleanup)
        self.top = Path(self.temporary.name)
        self.roots = tuple(self.top / str(index) for index in range(9))
        for root in self.roots:
            root.mkdir()
        self.payload = b'checked-phase-content\n' * 2048
        self.shared = [self.add_file('evidence', self.payload)]
        self.scope = extracted(SOURCE, ('_alias_phase_metadata', '_alias_inode_digest', 'alias_census'))
        self.census = self.scope['alias_census']

    def add_file(self, name, payload):
        path = self.roots[0] / name
        path.write_bytes(payload)
        path.chmod(0o644)
        for root in self.roots[1:]:
            os.link(path, root / name)
        return name, '100644', hashlib.sha1(b'blob ' + str(len(payload)).encode() + b'\0' + payload).hexdigest()

    def run_tracked(self, operation=None):
        stats = dict(streams=0, bytes=0, reads=0, flags=[])
        real_open, real_read = os.open, os.read
        def opening(path, flags, *args, **kwargs):
            descriptor = real_open(path, flags, *args, **kwargs)
            stats['streams'] += 1
            stats['flags'].append(flags)
            return descriptor
        def reading(descriptor, size):
            block = real_read(descriptor, size)
            stats['reads'] += 1
            stats['bytes'] += len(block)
            if operation is not None:
                operation(descriptor, block, stats)
            return block
        with mock.patch.object(os, 'open', side_effect=opening), mock.patch.object(os, 'read', side_effect=reading):
            self.assertEqual(self.census(self.roots, self.shared), 9)
        return stats

    def test_one_stream_for_nine_aliases_and_second_phase_reads_again(self):
        first = self.run_tracked()
        second = self.run_tracked()
        self.assertEqual((first['streams'], first['bytes']), (1, len(self.payload)))
        self.assertEqual((second['streams'], second['bytes']), (1, len(self.payload)))
        self.assertTrue(first['flags'][0] & os.O_NOFOLLOW)
        self.assertTrue(first['flags'][0] & os.O_CLOEXEC)
        self.assertTrue(first['flags'][0] & os.O_NONBLOCK)

    def test_private_single_pass_binds_git_blob_and_sha256(self):
        path = self.roots[0] / 'evidence'
        meta = self.scope['_alias_phase_metadata'](path)
        blob, checksum = self.scope['_alias_inode_digest'](path, meta)
        self.assertEqual(blob, self.shared[0][2])
        self.assertEqual(checksum, hashlib.sha256(self.payload).hexdigest())

    def test_tiny_fixture_original_nineteen_streams_become_one(self):
        legacy = extracted(ANCESTOR, ('regular', 'digest', 'identity', 'snapshot'))
        def git(_root, *args):
            self.assertEqual(args[:2], ('hash-object', '--no-filters'))
            path = Path(args[-1])
            digest = hashlib.sha1(b'blob ' + str(path.stat().st_size).encode() + b'\0')
            with path.open('rb') as stream:
                for block in iter(lambda: stream.read(1 << 20), b''):
                    digest.update(block)
            return (digest.hexdigest() + '\n').encode()
        baseline = extracted(ORIGINAL, ('alias_census',), ROOT=self.top,
                             _IMPL=types.SimpleNamespace(snapshot=legacy['snapshot'], git=git))
        count = dict(streams=0, bytes=0)
        real_open = Path.open
        class Reader:
            def __init__(self, stream): self.stream = stream
            def __enter__(self): return self
            def __exit__(self, *args): self.stream.close()
            def read(self, size):
                block = self.stream.read(size)
                count['bytes'] += len(block)
                return block
        def opening(path, *args, **kwargs):
            count['streams'] += 1
            return Reader(real_open(path, *args, **kwargs))
        with mock.patch.object(Path, 'open', new=opening):
            self.assertEqual(baseline['alias_census'](self.roots, self.shared), 9)
        optimized = self.run_tracked()
        self.assertEqual(count, dict(streams=19, bytes=19 * len(self.payload)))
        self.assertEqual((optimized['streams'], optimized['bytes']), (1, len(self.payload)))

    def test_all_alias_metadata_precedes_any_content_read(self):
        self.shared.append(self.add_file('second', b'another inode'))
        (self.roots[0] / 'second').chmod(0o600)
        with mock.patch.object(os, 'read') as read:
            with self.assertRaisesRegex(Refusal, 'bytes/mode'):
                self.census(self.roots, self.shared)
        read.assert_not_called()

    def test_wrong_oid_refuses(self):
        self.shared[0] = ('evidence', '100644', '0' * 40)
        with self.assertRaisesRegex(Refusal, 'bytes/inode'):
            self.census(self.roots, self.shared)

    def test_unknown_link_and_same_bytes_replaced_alias_refuse(self):
        os.link(self.roots[0] / 'evidence', self.top / 'unlisted')
        with self.assertRaisesRegex(Refusal, 'incomplete authenticated'):
            self.census(self.roots, self.shared)
        (self.top / 'unlisted').unlink()
        (self.roots[-1] / 'evidence').unlink()
        (self.roots[-1] / 'evidence').write_bytes(self.payload)
        (self.roots[-1] / 'evidence').chmod(0o644)
        os.link(self.roots[0] / 'evidence', self.top / 'unlisted')
        with self.assertRaisesRegex(Refusal, 'incomplete authenticated'):
            self.census(self.roots, self.shared)

    def test_symlink_and_mode_and_size_drift_refuse(self):
        alias = self.roots[-1] / 'evidence'
        alias.unlink()
        alias.symlink_to(self.roots[0] / 'evidence')
        with self.assertRaisesRegex(Refusal, 'noncanonical'):
            self.census(self.roots, self.shared)
        alias.unlink()
        os.link(self.roots[0] / 'evidence', alias)
        (self.roots[0] / 'evidence').chmod(0o600)
        with self.assertRaisesRegex(Refusal, 'bytes/mode'):
            self.census(self.roots, self.shared)
        (self.roots[0] / 'evidence').chmod(0o644)
        alias.unlink()
        alias.write_bytes(self.payload + b'longer')
        alias.chmod(0o644)
        os.link(self.roots[0] / 'evidence', self.top / 'unlisted')
        with self.assertRaisesRegex(Refusal, 'incomplete authenticated'):
            self.census(self.roots, self.shared)

    def test_growth_during_hash_is_bounded_and_refused(self):
        def grow(_descriptor, block, stats):
            if block and stats['reads'] == 1:
                with (self.roots[0] / 'evidence').open('ab') as stream:
                    stream.write(b'+')
        with self.assertRaisesRegex(Refusal, 'size grew'):
            self.run_tracked(grow)

    def test_mtime_restored_content_aba_refuses_on_ctime(self):
        path = self.roots[0] / 'evidence'
        before = path.stat()
        def mutate_restore(_descriptor, block, stats):
            if block and stats['reads'] == 1:
                time.sleep(0.02)  # Ensure a later filesystem timestamp tick.
                path.write_bytes(b'x' + self.payload[1:])
                path.write_bytes(self.payload)
                os.utime(path, ns=(before.st_atime_ns, before.st_mtime_ns))
        with self.assertRaisesRegex(Refusal, 'metadata raced'):
            self.run_tracked(mutate_restore)
        after = path.stat()
        self.assertEqual(after.st_mtime_ns, before.st_mtime_ns)
        self.assertNotEqual(after.st_ctime_ns, before.st_ctime_ns)

    def test_alias_replaced_during_hash_refuses(self):
        def replace(_descriptor, block, stats):
            if block and stats['reads'] == 1:
                alias = self.roots[-1] / 'evidence'
                alias.unlink()
                alias.write_bytes(self.payload)
        with self.assertRaises(Refusal):
            self.run_tracked(replace)

    def test_root_metadata_drift_after_content_refuses(self):
        def change_root(_descriptor, block, stats):
            if block and stats['reads'] == 1:
                self.roots[-1].chmod(0o711)
        with self.assertRaisesRegex(Refusal, 'root metadata raced'):
            self.run_tracked(change_root)

    def test_later_inode_read_cannot_hide_earlier_inode_mutation(self):
        self.shared.append(self.add_file('second', b'second inode content'))
        second_inode = (self.roots[0] / 'second').stat().st_ino
        def mutate_earlier(descriptor, block, _stats):
            if block and os.fstat(descriptor).st_ino == second_inode:
                (self.roots[0] / 'evidence').write_bytes(self.payload + b'changed after its hash')
        with self.assertRaisesRegex(Refusal, 'census raced'):
            self.run_tracked(mutate_earlier)

    def test_no_follow_swap_between_metadata_and_open_refuses(self):
        real_open = os.open
        def swap(path, flags):
            Path(path).unlink()
            Path(path).symlink_to(self.roots[-1] / 'evidence')
            return real_open(path, flags)
        with mock.patch.object(os, 'open', side_effect=swap):
            with self.assertRaisesRegex(Refusal, 'descriptor authentication unavailable'):
                self.census(self.roots, self.shared)

    def test_only_active_census_and_two_private_helpers_changed(self):
        self.assertEqual(hashlib.sha256(ORIGINAL.read_bytes()).hexdigest(), BASE_SHA)
        original = ast.parse(ORIGINAL.read_text())
        current = ast.parse(SOURCE.read_text())
        allowed = {'alias_census', '_alias_phase_metadata', '_alias_inode_digest'}
        def unchanged(tree):
            return [ast.dump(node) for node in tree.body
                    if not isinstance(node, ast.FunctionDef) or node.name not in allowed]
        self.assertEqual(unchanged(original), unchanged(current))


if __name__ == '__main__':
    unittest.main()
