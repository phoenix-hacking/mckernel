"""Unprivileged tests of the exact read-only historical lease observer."""
import hashlib
import os
from pathlib import Path
import stat
import struct
import sys
import tempfile
import types
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import native_exact_historical_lease_observer as observer


class LeaseObserverTests(unittest.TestCase):
    def fixtures(self):
        blobs = {}
        bindings = {}
        for key in observer.EVIDENCE_BINDINGS:
            data = ('evidence-' + key).encode()
            relative = observer.EVIDENCE_BINDINGS[key][0]
            bindings[key] = relative, hashlib.sha256(data).hexdigest()
            blobs[str(observer.EVIDENCE / relative)] = (data, None)
        leases = []
        for suffix, inode, size, digest, pid, start, evidence in observer.LEASES:
            data = ('lease-' + suffix).encode()
            leases.append((suffix, inode, len(data), hashlib.sha256(data).hexdigest(), pid, start, evidence))
            meta = types.SimpleNamespace(st_dev=observer.CURRENT_DEVICE, st_ino=inode, st_size=len(data),
                                         st_mode=stat.S_IFREG | 0o600, st_uid=0, st_gid=0)
            blobs[str(observer.ROOT / ('native-exact-build-lease-' + suffix + '.json'))] = (data, meta)
        return blobs, bindings, leases

    def invoke(self, mutate=None, live=False):
        blobs, bindings, leases = self.fixtures()
        if mutate: mutate(blobs)
        def read_text(path, *args, **kwargs):
            if str(path).endswith('boot_id'): return observer.CURRENT_BOOT
            if live:
                return '1 (owner) ' + ' '.join(['S'] + ['0'] * 18 + [leases[0][5]])
            raise FileNotFoundError(str(path))
        with mock.patch.object(observer.os, 'geteuid', return_value=0), \
             mock.patch.object(observer, '_read', side_effect=lambda p, **k: blobs[str(p)]), \
             mock.patch.object(observer, 'EVIDENCE_BINDINGS', bindings), \
             mock.patch.object(observer, 'LEASES', leases), \
             mock.patch.object(observer, 'ScratchBinding') as mount, \
             mock.patch.object(Path, 'read_text', read_text):
            result = observer.observe()
            mount.return_value.__enter__.return_value.check.assert_called_once_with()
            return result

    def test_exact_positive_and_metadata_content_mutations(self):
        result = self.invoke()
        self.assertEqual(len(result['leases']), 7)
        self.assertEqual(result['boot_id'], observer.CURRENT_BOOT)
        self.assertEqual(result['authority']['historical_boot_id'], observer.HISTORICAL_BOOT)
        self.assertEqual(result['authority']['historical_device'], 1831)
        self.assertEqual(result['authority']['current_device'], 1828)
        self.assertEqual(result['authority']['filesystem_uuid'], observer.FILESYSTEM_UUID)
        lease_path = str(observer.ROOT / 'native-exact-build-lease-67589154-1.json')
        for field, value in (('st_dev', 2), ('st_ino', 5), ('st_size', 1),
                             ('st_uid', 1000), ('st_gid', 1000), ('st_mode', stat.S_IFREG | 0o644)):
            def mutate(blobs, field=field, value=value): setattr(blobs[lease_path][1], field, value)
            with self.subTest(field=field), self.assertRaisesRegex(observer.Refusal, 'binding changed'):
                self.invoke(mutate)
        def tamper(blobs):
            data, meta = blobs[lease_path]; blobs[lease_path] = (data + b'!', meta)
        with self.assertRaisesRegex(observer.Refusal, 'binding changed'): self.invoke(tamper)

    def test_evidence_and_live_owner_mutations(self):
        def tamper(blobs):
            path = str(observer.EVIDENCE / observer.EVIDENCE_BINDINGS['675'][0])
            blobs[path] = (b'tampered', None)
        with self.assertRaisesRegex(observer.Refusal, 'evidence changed'): self.invoke(tamper)
        with self.assertRaisesRegex(observer.Refusal, 'owner is live'): self.invoke(live=True)

    def test_boot_and_privilege_are_required(self):
        with mock.patch.object(observer.os, 'geteuid', return_value=1000):
            with self.assertRaisesRegex(observer.Refusal, 'privileged'): observer.observe()
        with mock.patch.object(observer.os, 'geteuid', return_value=0), \
             mock.patch.object(Path, 'read_text', return_value='other-boot'):
            with self.assertRaisesRegex(observer.Refusal, 'boot identity'): observer.observe()

    def test_actual_descriptor_read_preserves_file_and_rejects_aliases(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / 'lease'; path.write_bytes(b'unchanged')
            before = path.stat()
            data, after = observer._read(path)
            self.assertEqual(data, b'unchanged'); self.assertEqual(before, after)
            link = Path(td) / 'alias'; link.symlink_to(path)
            with self.assertRaises(OSError): observer._read(link)
            link.unlink(); os.link(path, link)
            with self.assertRaisesRegex(observer.Refusal, 'nonunique'): observer._read(path)

    def test_missing_immutable_flag_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / 'lease'; path.write_bytes(b'unchanged')
            with mock.patch.object(observer.fcntl, 'ioctl', return_value=b'\0' * 4):
                with self.assertRaisesRegex(observer.Refusal, 'not immutable'):
                    observer._read(path, immutable=True)

    def test_immutable_flag_changes_and_ioctl_failure_are_refused(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / 'lease'; path.write_bytes(b'unchanged')
            for answers in ((struct.pack('I', 0x10), struct.pack('I', 0)),
                            (struct.pack('I', 0x10), struct.pack('I', 0x80010))):
                with self.subTest(answers=answers), \
                     mock.patch.object(observer.fcntl, 'ioctl', side_effect=answers):
                    with self.assertRaisesRegex(observer.Refusal, 'flags changed'):
                        observer._read(path, immutable=True)
            with mock.patch.object(observer.fcntl, 'ioctl', side_effect=OSError('unavailable')):
                with self.assertRaises(OSError): observer._read(path, immutable=True)

    def test_original_retirement_catalog_remains_exact(self):
        self.assertEqual(len(observer.LEASES), 7)
        self.assertEqual(len(observer.EVIDENCE_BINDINGS), 4)
        self.assertEqual(observer.HISTORICAL_BOOT, 'c733d83b-a5ae-4f91-9ce6-9f8ccf119afd')
        self.assertEqual(observer.HISTORICAL_DEVICE, 1831)
        self.assertNotEqual(observer.HISTORICAL_BOOT, observer.CURRENT_BOOT)
        self.assertNotEqual(observer.HISTORICAL_DEVICE, observer.CURRENT_DEVICE)


class ScratchBindingTests(unittest.TestCase):
    def setUp(self):
        self.root = types.SimpleNamespace(st_dev=1828, st_ino=2, st_mode=stat.S_IFDIR | 0o700,
                                          st_uid=1000, st_gid=1000)
        self.block = types.SimpleNamespace(st_dev=5, st_ino=36, st_rdev=1828,
                                           st_mode=stat.S_IFBLK | 0o660,
                                           st_uid=0, st_gid=6, st_nlink=1)
        self.superblock = bytearray(1024)
        self.superblock[0x38:0x3a] = b'\x53\xef'
        self.superblock[0x68:0x78] = observer.uuid.UUID(observer.FILESYSTEM_UUID).bytes
        self.raw = bytes(self.superblock)
        self.root_chain = [observer._directory_identity(self.root)]
        self.block_chain = [(5, 1, stat.S_IFDIR | 0o755, 0, 0)]
        def directory(path):
            if path == observer.ROOT: return 11, self.root_chain
            if path == observer.BLOCK_DEVICE.parent: return 12, self.block_chain
            raise AssertionError('unexpected directory path')
        for target, value in (('_directory', mock.Mock(side_effect=directory)),):
            patch = mock.patch.object(observer, target, value)
            patch.start(); self.addCleanup(patch.stop)
        for target, value in (('open', mock.Mock(return_value=13)),
                              ('close', mock.Mock()),
                              ('fstat', mock.Mock(side_effect=lambda fd: self.root if fd == 11 else self.block)),
                              ('stat', mock.Mock(side_effect=lambda *a, **k: self.block)),
                              ('pread', mock.Mock(side_effect=lambda *a: self.raw))):
            patch = mock.patch.object(observer.os, target, value)
            patch.start(); self.addCleanup(patch.stop)
        self.boot = mock.patch.object(Path, 'read_text', return_value=observer.CURRENT_BOOT)
        self.boot_mock = self.boot.start(); self.addCleanup(self.boot.stop)

    def test_exact_current_uuid_and_block_descriptors_stay_pinned(self):
        with observer.ScratchBinding() as binding:
            self.assertEqual(binding.block_fd, 13)
            observer.os.close.assert_any_call(11)  # Fresh revalidation descriptor only.
            self.assertNotIn(mock.call(13), observer.os.close.call_args_list)
            binding.check()
        observer.os.close.assert_any_call(13)
        observer.os.pread.assert_called_with(13, 1024, 1024)
        flags = observer.os.open.call_args.args[1]
        self.assertEqual(flags & os.O_ACCMODE, os.O_RDONLY)
        for flag in (os.O_NOFOLLOW, os.O_CLOEXEC, os.O_NONBLOCK, os.O_NOATIME):
            self.assertTrue(flags & flag)
        observer.os.open.assert_called_once_with('loop36', flags, dir_fd=12)

    def test_wrong_uuid_magic_and_truncated_superblock_are_refused(self):
        wrong = bytearray(self.raw); wrong[0x68] ^= 1
        bad_magic = bytearray(self.raw); bad_magic[0x38] = 0
        for raw in (bytes(wrong), bytes(bad_magic), self.raw[:-1]):
            with self.subTest(raw=raw[0x38:0x3a]):
                self.raw = raw
                with self.assertRaisesRegex(observer.Refusal, 'UUID proof'):
                    with observer.ScratchBinding(): pass

    def test_wrong_current_device_root_inode_and_block_type_are_refused(self):
        for field, value in (('st_dev', 1831), ('st_ino', 3), ('st_uid', 0)):
            previous = getattr(self.root, field)
            setattr(self.root, field, value)
            with self.subTest(root_field=field), self.assertRaisesRegex(observer.Refusal, 'root binding'):
                with observer.ScratchBinding(): pass
            setattr(self.root, field, previous)
        for field, value in (('st_rdev', 1831), ('st_mode', stat.S_IFREG | 0o600),
                             ('st_uid', 1000), ('st_nlink', 2)):
            previous = getattr(self.block, field)
            setattr(self.block, field, value)
            with self.subTest(block_field=field), self.assertRaisesRegex(observer.Refusal, 'block binding'):
                with observer.ScratchBinding(): pass
            setattr(self.block, field, previous)

    def test_boot_block_identity_and_ancestry_drift_are_refused(self):
        with observer.ScratchBinding() as binding:
            self.boot_mock.return_value = observer.HISTORICAL_BOOT
            with self.assertRaisesRegex(observer.Refusal, 'boot identity'): binding.check()
            self.boot_mock.return_value = observer.CURRENT_BOOT
            self.block.st_ino += 1
            with self.assertRaisesRegex(observer.Refusal, 'block identity'): binding.check()
            self.block.st_ino -= 1
            self.root_chain = [(1828, 999, stat.S_IFDIR | 0o700, 1000, 1000)]
            with self.assertRaisesRegex(observer.Refusal, 'ancestry'): binding.check()

    def test_uuid_read_failure_and_boot_race_are_refused(self):
        with mock.patch.object(observer.os, 'pread', side_effect=OSError('unavailable')):
            with self.assertRaises(OSError):
                with observer.ScratchBinding(): pass
        self.boot_mock.side_effect = [observer.CURRENT_BOOT, 'changed-boot']
        with self.assertRaisesRegex(observer.Refusal, 'boot changed'):
            with observer.ScratchBinding(): pass


if __name__ == '__main__': unittest.main()
