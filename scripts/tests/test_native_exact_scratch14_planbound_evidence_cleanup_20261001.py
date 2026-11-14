"""Synthetic safety tests for the c81 scratch14 plan-bound cleanup tool."""
import hashlib
import importlib.util
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

SRC = Path(__file__).resolve().parents[2] / 'docs/verification/evidence/native-exact-scratch14-planbound-evidence-cleanup-20261001.py'
spec = importlib.util.spec_from_file_location('scratch14_cleanup', SRC)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class Scratch14Safety(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory(prefix='scratch14-test-')
        self.root = Path(self.t.name) / 'mckernel-exact-candidate-c81aeaca-scratch-14'
        (self.root / 'docs/verification/evidence').mkdir(parents=True)

    def tearDown(self):
        self.t.cleanup()

    def test_constants_bind_exact_candidate(self):
        self.assertEqual(m.EXPECTED_COMMIT, 'c81aeaca5cedd893981a058444fa11a03a49a744')
        self.assertTrue(m.EXPECTED_ROOT.endswith('mckernel-exact-candidate-c81aeaca-scratch-14'))
        self.assertTrue(m.parse_args(['--audit', '--plan', '/tmp/p']).audit)

    def test_validate_rejects_symlink_target(self):
        p = self.root / 'docs/verification/evidence' / 'bad'
        p.symlink_to('/dev/null')
        row = {'path': str(p), 'restore_git_path': 'docs/verification/evidence/bad',
               'blob': '0' * 40, 'dev': 1, 'ino': 2, 'mode': 0o644, 'mtime_ns': 1,
               'nlink': 1, 'size': 0, 'sha256': hashlib.sha256(b'').hexdigest(),
               'allocated_bytes': 0}
        with self.assertRaises((m.Refusal, OSError)):
            with m.opened(str(p)) as fd:
                m.verify_fd(fd, row)

    def test_validate_rejects_hardlink(self):
        p = self.root / 'docs/verification/evidence' / 'a'
        q = self.root / 'docs/verification/evidence' / 'b'
        p.write_bytes(b'x'); os.link(p, q)
        s = p.stat()
        row = {'path': str(p), 'restore_git_path': 'docs/verification/evidence/a',
               'blob': '0' * 40, **m.metadata(s), 'sha256': m.sha(b'x'), 'allocated_bytes': s.st_blocks * 512}
        with self.assertRaises(m.Refusal):
            with m.opened(str(p)) as fd:
                m.verify_fd(fd, row)

    def _audit_rejects(self, make):
        make()
        out = self.root / 'plan.json'
        old_root, old_git = m.EXPECTED_ROOT, m.git
        try:
            m.EXPECTED_ROOT = str(self.root)
            m.git = lambda repo, *args: (b'c81aeaca5cedd893981a058444fa11a03a49a744\n'
                                         if args[:2] == ('rev-parse', 'HEAD') else b'')
            with self.assertRaises(m.Refusal):
                m.audit_plan(str(self.root), str(out))
            self.assertFalse(out.exists())
        finally:
            m.EXPECTED_ROOT, m.git = old_root, old_git

    def test_audit_rejects_symlink(self):
        self._audit_rejects(lambda: (self.root / 'docs/verification/evidence' / 'bad').symlink_to('/dev/null'))

    def test_audit_rejects_hardlink(self):
        def make():
            p = self.root / 'docs/verification/evidence' / 'a'; p.write_bytes(b'x'); os.link(p, str(p) + '-hard')
        self._audit_rejects(make)

    def test_execute_requires_authenticated_plan(self):
        src = SRC.read_text()
        self.assertIn("require(release['plan'] == plan, 'release-plan-mismatch')", src)
        self.assertIn("release['schema'] == 'mckernel.scratch14-cleanup-release.v1'", src)
        self.assertIn("release['outputs'] == outputs", src)

    def test_audit_validate_nested_and_tracked_modified_preserved(self):
        evidence = self.root / 'docs/verification/evidence'
        nested = evidence / 'nested'; nested.mkdir()
        tracked = nested / 'same'; tracked.write_bytes(b'tracked\n'); tracked.chmod(0o644)
        modified = evidence / 'modified'; modified.write_bytes(b'working\n'); modified.chmod(0o644)
        untracked = evidence / 'local'; untracked.write_bytes(b'local\n'); untracked.chmod(0o644)
        original = b'tracked-original\n'
        blobs = {
            'docs/verification/evidence/nested/same': original,
            'docs/verification/evidence/modified': b'committed-original\n',
        }
        old_root, old_git = m.EXPECTED_ROOT, m.git
        plan_path = self.root.parent / 'audit-plan.json'
        try:
            m.EXPECTED_ROOT = str(self.root)
            def fake_git(repo, *args):
                if args[:2] == ('rev-parse', 'HEAD'):
                    return (m.EXPECTED_COMMIT + '\n').encode()
                if args[:1] == ('ls-tree',):
                    rel = args[-1]
                    data = blobs.get(rel)
                    if data is None:
                        return b''
                    blob = hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
                    return ('100644 blob ' + blob + '\t' + rel + '\0').encode()
                if args[:1] == ('cat-file',):
                    return next(data for data in blobs.values()
                                if hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest() == args[-1])
                raise AssertionError(args)
            m.git = fake_git
            plan = m.audit_plan(str(self.root), str(plan_path))
            self.assertEqual(len(plan['targets']), 0)
            preserved = {r['restore_git_path']: r for r in plan['preserved']}
            self.assertEqual(preserved['docs/verification/evidence/modified']['blob'],
                             hashlib.sha1(b'blob 19\0committed-original\n').hexdigest())
            self.assertIn('docs/verification/evidence/nested/same', preserved)
            self.assertIsNone(preserved['docs/verification/evidence/local']['blob'])
            self.assertEqual(m.validate_plan(str(plan_path))['candidate_root'], str(self.root))
        finally:
            m.EXPECTED_ROOT, m.git = old_root, old_git

    def test_plan_publication_rejects_existing_symlink_and_candidate_paths(self):
        plan = {'status': 'AUDIT_PASS'}
        existing = self.root.parent / 'existing.json'; existing.write_text('x')
        symlink = self.root.parent / 'link.json'; symlink.symlink_to(existing)
        for path in (existing, symlink, self.root / '.git'):
            with self.assertRaises((m.Refusal, OSError)):
                m.publish_plan(str(path), plan, str(self.root))

    def test_transaction_partial_stage_failure_restores_all_entries(self):
        evidence = self.root / 'docs/verification/evidence'
        rows = []
        for i in range(2):
            p = evidence / ('f' + str(i)); data = ('x' + str(i)).encode(); p.write_bytes(data)
            s = p.stat(); rows.append({'path': str(p), 'restore_git_path': str(p.relative_to(self.root)),
                'blob': '0' * 40, **m.metadata(s), 'sha256': m.sha(data), 'allocated_bytes': s.st_blocks * 512})
        plan = {'candidate_root': str(self.root), 'candidate_identity': f'{self.root.stat().st_dev}:{self.root.stat().st_ino}',
                'candidate_commit': m.EXPECTED_COMMIT, 'targets': rows, 'preserved': [],
                'protected_paths': [], 'protected_inventory': []}
        journal_path = self.root.parent / 'j'; journal = m.Journal(str(journal_path)); q = self.root / '.planbound-cleanup-test'
        real_rename = m.rename_noreplace; count = {'n': 0}
        def fail_second(*args):
            count['n'] += 1
            if count['n'] == 2: raise m.Refusal('injected-stage-failure')
            return real_rename(*args)
        try:
            with mock.patch.object(m, 'rename_noreplace', side_effect=fail_second), \
                 mock.patch.object(m, 'validate_protected'), \
                 mock.patch.object(m, 'collect_census'):
                result = m.transact(plan, {'quarantine': str(q)}, journal)
            self.assertEqual(result['status'], 'FAIL')
            self.assertTrue(all(Path(row['path']).exists() for row in rows))
        finally:
            journal.close()

    def test_source_has_terminal_publication_and_live_lease_guards(self):
        src = SRC.read_text()
        self.assertIn("require(not os.path.lexists(lease), 'active-lease')", src)
        self.assertIn('finalization_error', src)
        self.assertIn('transaction-unwind-failure', src)

    def test_protected_lookalike_is_not_keyword_discovered(self):
        p = self.root / 'metadata-backup-lookalike'; p.write_bytes(b'x')
        src = SRC.read_text()
        self.assertIn("'/metadata-backup.json'", src)
        self.assertNotIn("any(token in low", src)

    def test_explicit_protected_overlap_and_drift_are_rejected(self):
        overlap = self.root / 'docs/verification/evidence' / 'ihk'
        plan = {'candidate_root': str(self.root),
                'protected_paths': [str(overlap)],
                'protected_inventory': [{'path': str(overlap), 'type': 'directory',
                                        'dev': 1, 'ino': 1, 'mode': 0o755}]}
        with self.assertRaises(m.Refusal):
            m.validate_protected(plan)
        src = SRC.read_text()
        self.assertIn("'protected-evidence-overlap'", src)
        self.assertIn("'file-metadata'", src)

    def test_finalization_faults_are_terminal_not_success(self):
        src = SRC.read_text()
        self.assertIn("'event': 'finalization-terminal-ready'", src)
        self.assertIn("journal.close()", src)
        self.assertIn("result.get('status') == 'PASS'", src)
        self.assertIn("status_publication_error", src)

    def test_generated_audit_plan_rejects_untracked_mode_0600(self):
        row = {'path': str(self.root / 'docs/verification/evidence/untracked'),
               'restore_git_path': 'docs/verification/evidence/untracked',
               'blob': None, 'dev': 1, 'ino': 2, 'mode': 0o600, 'mtime_ns': 1,
               'nlink': 1, 'size': 1, 'sha256': m.sha(b'x'), 'allocated_bytes': 512}
        plan = {'schema': 'mckernel.exact-git-source-audit.v1', 'status': 'AUDIT_PASS',
                'candidate_root': str(self.root), 'targets': [], 'preserved': [row],
                'protected_paths': [], 'protected_inventory': []}
        with self.assertRaises(m.Refusal):
            m.validate_generated_plan(plan)

    def test_journal_close_fsync_failure_is_not_silent(self):
        path = self.root.parent / 'journal'
        j = m.Journal(str(path))
        with mock.patch.object(m.os, 'fsync', side_effect=OSError('injected-fsync')):
            with self.assertRaises(OSError):
                j.close()
        self.assertIsNone(j.fd)


if __name__ == '__main__':
    unittest.main()
