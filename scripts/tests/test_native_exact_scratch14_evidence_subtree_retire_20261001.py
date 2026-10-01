"""Synthetic safety tests for the one-shot scratch14 evidence retirement."""
import hashlib
import importlib.util
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / 'docs/verification/evidence/native-exact-scratch14-evidence-subtree-retire-20261001.py'
SPEC = importlib.util.spec_from_file_location('retire_evidence', SRC)
M = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(M)


class RetirementSafety(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='retire-evidence-')
        self.base = Path(self.temp.name) / 'evidence'
        (self.base / 'nested').mkdir(parents=True)
        (self.base / 'a').write_bytes(b'alpha')
        (self.base / 'nested/b').write_bytes(b'beta')
        self.rows = [self.row(self.base, 'directory'),
                     self.row(self.base / 'nested', 'directory'),
                     self.row(self.base / 'a', 'regular'),
                     self.row(self.base / 'nested/b', 'regular')]

    def tearDown(self):
        self.temp.cleanup()

    def row(self, path, kind):
        value = path.lstat()
        result = {'root': 'candidate', 'classification': 'reconstructible',
                  'path': 'docs/verification/evidence' +
                          ('' if path == self.base else '/' + str(path.relative_to(self.base))),
                  'type': kind, 'uid': value.st_uid, 'gid': value.st_gid,
                  'mode': value.st_mode & 0o777, 'size': value.st_size}
        if kind == 'regular':
            result['sha256'] = hashlib.sha256(path.read_bytes()).hexdigest()
        return result

    def test_constants_are_exact_and_operation_is_one_shot(self):
        self.assertEqual(M.ROOT_ID, (1831, 1464725, 1000, 1000, 0o755))
        self.assertEqual(M.TARGET_ID, (1831, 1465177, 1000, 1000, 0o755))
        self.assertEqual(M.ARTIFACT_COMMIT, 'bca2aa984fb1efda83d3355aba8c9beeda3ec084')
        self.assertIn('.retired-evidence-c81aeaca-20261001-1', str(M.QUARANTINE))
        with self.assertRaises(M.Refusal):
            M.main(['--anything-else'])

    def test_census_accepts_exact_tree_and_rejects_content_drift(self):
        rows = [dict(row) for row in self.rows]
        with mock.patch.object(M, 'DEVICE', self.base.stat().st_dev):
            self.assertEqual(len(M.census(self.base, rows)), 4)
            (self.base / 'a').write_bytes(b'wrong')
            with self.assertRaises(M.Refusal):
                M.census(self.base, rows)

    def test_census_rejects_symlink_and_hardlink(self):
        (self.base / 'link').symlink_to('a')
        rows = self.rows + [self.row(self.base / 'a', 'regular')]
        rows[-1]['path'] += '-alias'
        with mock.patch.object(M, 'DEVICE', self.base.stat().st_dev), self.assertRaises(M.Refusal):
            M.census(self.base, rows)
        (self.base / 'link').unlink()
        os.link(self.base / 'a', self.base / 'hard')
        hard = self.row(self.base / 'hard', 'regular')
        with mock.patch.object(M, 'DEVICE', self.base.stat().st_dev), self.assertRaises(M.Refusal):
            M.census(self.base, self.rows + [hard])

    def test_rename_is_noreplace(self):
        destination = self.base.parent / 'quarantine'
        destination.mkdir()
        with self.assertRaises(OSError):
            M.rename_noreplace(self.base, destination)
        self.assertTrue(self.base.is_dir())
        destination.rmdir()
        M.rename_noreplace(self.base, destination)
        self.assertFalse(self.base.exists())
        self.assertTrue(destination.is_dir())

    def test_rename_rejects_intermediate_symlink(self):
        real = self.base.parent
        alias = real.parent / (real.name + '-alias')
        alias.symlink_to(real, target_is_directory=True)
        try:
            with self.assertRaises(OSError):
                M.rename_noreplace(alias / self.base.name, alias / 'quarantine')
            self.assertTrue(self.base.exists())
        finally:
            alias.unlink()

    def test_purge_removes_only_authenticated_tree(self):
        outside = self.base.parent / 'sentinel'
        outside.write_bytes(b'keep')
        journal = mock.Mock()
        with mock.patch.object(M, 'DEVICE', self.base.stat().st_dev):
            snapshot = M.census(self.base, self.rows)
            M.purge_directory(self.base, snapshot, journal)
        self.assertFalse(self.base.exists())
        self.assertEqual(outside.read_bytes(), b'keep')

    def test_purge_rejects_member_inserted_after_census(self):
        journal = mock.Mock()
        with mock.patch.object(M, 'DEVICE', self.base.stat().st_dev):
            snapshot = M.census(self.base, self.rows)
            (self.base / 'late').write_bytes(b'late')
            with self.assertRaises(M.Refusal):
                M.purge_directory(self.base, snapshot, journal)
        self.assertTrue((self.base / 'late').exists())

    def test_deleted_inode_audit_rejects_visibility_error(self):
        result = mock.Mock(returncode=1, stdout=b'', stderr=b'permission denied')
        with mock.patch.object(M, 'run', return_value=result), self.assertRaises(M.Refusal):
            M.no_deleted_inodes(set())

    def test_success_record_is_not_authoritative_pass(self):
        source = SRC.read_text()
        self.assertIn("'status': 'READY_FOR_VERIFICATION'", source)
        self.assertNotIn("'status': 'PASS'", source)
        self.assertIn("journal.append({'event': 'failure'", source)
        self.assertIn('no_deleted_inodes({', source)
        self.assertIn("require(os.geteuid() == 0, 'root-required')", source)
        self.assertIn('os.fchown(quarantine_fd, 0, 0)', source)
        self.assertIn("root_override=(0, 0, 0o500)", source)
        self.assertGreaterEqual(source.count('no_live_references(QUARANTINE)'), 2)
        self.assertIn("'-u', '#1000'", source)


if __name__ == '__main__':
    unittest.main()
