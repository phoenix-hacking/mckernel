"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

Proposed tiny fixture cases. Do not run without an applicable reviewed profile.
Temporary directories are deliberately retained for owner inspection.
"""
import errno
import hashlib
import importlib.util
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

spec = importlib.util.spec_from_file_location('xpmem_generator_under_test', Path(__file__).parent / 'generate.py')
g = importlib.util.module_from_spec(spec)
spec.loader.exec_module(g)

class HeldDirectoryCases(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix='m14-xpmem-dirfd-fixture-'))
        self.d = self.root / 'out'
        self.d.mkdir()

    def test_existing_regular_cannot_be_overwritten(self):
        p = self.d / 'fixture.rs'
        p.write_bytes(b'prior')
        with g.PinnedDir(self.d) as owner:
            with self.assertRaises(FileExistsError):
                g.create_exclusive(owner, 'fixture.rs', b'new')
        self.assertEqual(p.read_bytes(), b'prior')

    def test_dangling_symlink_cannot_be_an_output(self):
        os.symlink('missing-target', self.d / 'fixture.rs')
        with g.PinnedDir(self.d) as owner:
            with self.assertRaises(FileExistsError):
                g.create_exclusive(owner, 'fixture.rs', b'new')
        self.assertTrue((self.d / 'fixture.rs').is_symlink())
        self.assertFalse((self.d / 'missing-target').exists())

    def test_intermediate_symlink_is_rejected(self):
        target = self.root / 'target'
        target.mkdir()
        (target / 'child').mkdir()
        os.symlink(target, self.root / 'alias')
        with self.assertRaises(OSError) as exc:
            with g.PinnedDir(self.root / 'alias' / 'child'):
                pass
        self.assertIn(exc.exception.errno, (errno.ELOOP, errno.ENOTDIR))

    def test_directory_replacement_is_rejected(self):
        with g.PinnedDir(self.d) as owner:
            self.d.rename(self.root / 'retained-original')
            self.d.mkdir()
            with self.assertRaises(g.CustodyError):
                owner.verify()

    def test_output_replacement_is_rejected(self):
        with g.PinnedDir(self.d) as owner:
            fd = g.create_exclusive(owner, 'fixture.rs', b'good')
            try:
                (self.d / 'fixture.rs').rename(self.d / 'retained-original')
                (self.d / 'fixture.rs').write_bytes(b'good')
                with self.assertRaises(g.CustodyError):
                    g.verify_output(owner, 'fixture.rs', fd, b'good')
                self.assertEqual((self.d / 'retained-original').read_bytes(), b'good')
            finally:
                os.close(fd)

    def test_partial_write_is_retained_on_error(self):
        real_write = os.write
        calls = []
        def failing_write(fd, data):
            calls.append(1)
            if len(calls) == 1:
                return real_write(fd, data[:2])
            raise OSError(errno.EIO, 'fixture write failure')
        with g.PinnedDir(self.d) as owner:
            with mock.patch.object(g.os, 'write', side_effect=failing_write):
                with self.assertRaises(OSError) as exc:
                    g.create_exclusive(owner, 'fixture.rs', b'123456')
                self.assertEqual(exc.exception.errno, errno.EIO)
        self.assertEqual((self.d / 'fixture.rs').read_bytes(), b'12')

    def test_bound_input_and_final_symlink(self):
        p = self.root / 'source'
        p.write_bytes(b'input')
        digest = hashlib.sha256(b'input').hexdigest()
        self.assertEqual(g.read_regular(p, digest, 5), b'input')
        os.symlink('source', self.root / 'input-link')
        with self.assertRaises(OSError) as exc:
            g.read_regular(self.root / 'input-link', digest, 5)
        self.assertEqual(exc.exception.errno, errno.ELOOP)

    def test_oversize_output_is_rejected_before_readback(self):
        with g.PinnedDir(self.d) as owner:
            fd = g.create_exclusive(owner, 'fixture.rs', b'good')
            try:
                os.write(fd, b'extra')
                with mock.patch.object(g.os, 'pread', side_effect=AssertionError('must not read oversized output')):
                    with self.assertRaises(g.CustodyError) as exc:
                        g.verify_output(owner, 'fixture.rs', fd, b'good')
                self.assertIn('output size differs', str(exc.exception))
            finally:
                os.close(fd)
        self.assertEqual((self.d / 'fixture.rs').read_bytes(), b'goodextra')

    def test_fifo_is_rejected_before_read(self):
        fifo = self.root / 'input-fifo'
        os.mkfifo(fifo)
        with mock.patch.object(g.os, 'read', side_effect=AssertionError('must not read FIFO')):
            with self.assertRaises(g.CustodyError) as exc:
                g.read_regular(fifo, hashlib.sha256(b'input').hexdigest(), 5)
        self.assertIn('regular file', str(exc.exception))

    def test_oversize_file_is_rejected_before_read(self):
        source = self.root / 'oversize'
        source.write_bytes(b'123456')
        with mock.patch.object(g.os, 'read', side_effect=AssertionError('must not read oversized input')):
            with self.assertRaises(g.CustodyError) as exc:
                g.read_regular(source, hashlib.sha256(b'12345').hexdigest(), 5)
        self.assertIn('size differs', str(exc.exception))
        self.assertEqual(source.stat().st_size, 6)

    def test_invalid_bound_is_rejected_before_open(self):
        with mock.patch.object(g.os, 'open', side_effect=AssertionError('must not open')):
            with self.assertRaises(g.CustodyError):
                g.read_regular(self.root / 'no-file', '0' * 64, -1)
            with self.assertRaises(g.CustodyError):
                g.read_regular(self.root / 'no-file', '0' * 64, g.MAX_BOUND_INPUT_SIZE + 1)

if __name__ == '__main__':
    unittest.main()
