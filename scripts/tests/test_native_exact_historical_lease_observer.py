"""Unprivileged tests of the exact read-only historical lease observer."""
import hashlib
import os
from pathlib import Path
import stat
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
            meta = types.SimpleNamespace(st_dev=1831, st_ino=inode, st_size=len(data),
                                         st_mode=stat.S_IFREG | 0o600, st_uid=0, st_gid=0)
            blobs[str(observer.ROOT / ('native-exact-build-lease-' + suffix + '.json'))] = (data, meta)
        return blobs, bindings, leases

    def invoke(self, mutate=None, live=False):
        blobs, bindings, leases = self.fixtures()
        if mutate: mutate(blobs)
        def read_text(path, *args, **kwargs):
            if str(path).endswith('boot_id'): return observer.BOOT
            if live:
                return '1 (owner) ' + ' '.join(['S'] + ['0'] * 18 + [leases[0][5]])
            raise FileNotFoundError(str(path))
        with mock.patch.object(observer.os, 'geteuid', return_value=0), \
             mock.patch.object(observer, '_read', side_effect=lambda p, **k: blobs[str(p)]), \
             mock.patch.object(observer, 'EVIDENCE_BINDINGS', bindings), \
             mock.patch.object(observer, 'LEASES', leases), \
             mock.patch.object(Path, 'read_text', read_text):
            return observer.observe()

    def test_exact_positive_and_metadata_content_mutations(self):
        self.assertEqual(len(self.invoke()['leases']), 7)
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


if __name__ == '__main__': unittest.main()
