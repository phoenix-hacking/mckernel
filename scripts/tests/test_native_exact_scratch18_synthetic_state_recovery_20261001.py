import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

SOURCE = Path(__file__).resolve().parents[2] / 'docs/verification/evidence/native-exact-scratch18-synthetic-state-recovery-20261001.py'

def load():
    spec = importlib.util.spec_from_file_location('synthetic_recovery', SOURCE)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module); return module

class SyntheticRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.m = load(); self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name); root.chmod(0o700)
        self.m.ROOT = root; self.m.DEVICE = root.stat().st_dev
        self.m.UID, self.m.GID = os.getuid(), os.getgid()
        self.m.PLAN = root / 'plan'; self.m.JOURNAL = root / 'journal'
        self.m.PLAN_ARCHIVE = root / 'plan.synthetic-v1.archive'
        self.m.JOURNAL_ARCHIVE = root / 'journal.synthetic-v1.archive'
        self.m.PLAN_SENTINEL = root / 'plan.synthetic-v1.sentinel'
        self.m.JOURNAL_SENTINEL = root / 'journal.synthetic-v1.sentinel'
        plan = json.dumps({'device': 66306, 'records': list(self.m.TMP_RECORDS),
                           'schema': 'native-exact-scratch18-interrupt-cleanup-v1'},
                          sort_keys=True, separators=(', ', ': ')).encode()
        journal = b''.join((json.dumps({'event': e, 'hash': h, 'index': i, 'previous': p},
                                       sort_keys=True).encode() + b'\n')
                           for e, i, p, h in self.m.EVENTS)
        self.m.PLAN.write_bytes(plan); self.m.JOURNAL.write_bytes(journal)
        self.m.PLAN.chmod(0o600); self.m.JOURNAL.chmod(0o600)
        self.m.PLAN_RECORD = (self.m.digest(plan), self.m.PLAN.stat().st_ino, len(plan))
        self.m.JOURNAL_RECORD = (self.m.digest(journal), self.m.JOURNAL.stat().st_ino, len(journal))
        self.m.ARCHIVES = ((self.m.PLAN, self.m.PLAN_ARCHIVE, self.m.PLAN_RECORD),
                           (self.m.JOURNAL, self.m.JOURNAL_ARCHIVE, self.m.JOURNAL_RECORD))

    def test_validate_only_is_byte_and_inode_stable(self):
        before = {p: (p.stat().st_ino, p.read_bytes()) for p in (self.m.PLAN, self.m.JOURNAL)}
        self.assertEqual(self.m.recover(), {'status': 'PASS_VALIDATE_ONLY', 'terminal': False})
        self.assertEqual(before, {p: (p.stat().st_ino, p.read_bytes()) for p in before})

    def test_execute_and_exact_terminal_replay(self):
        self.assertEqual(self.m.recover(True)['status'], 'PASS_EXECUTED')
        self.assertFalse(self.m.PLAN.exists()); self.assertFalse(self.m.JOURNAL.exists())
        before = {p: (p.stat().st_ino, p.read_bytes()) for p in (self.m.PLAN_ARCHIVE, self.m.JOURNAL_ARCHIVE)}
        self.assertEqual(self.m.recover(True), {'status': 'PASS_TERMINAL_REPLAY', 'terminal': True})
        self.assertEqual(before, {p: (p.stat().st_ino, p.read_bytes()) for p in before})

    def test_collision_refuses_without_mutation(self):
        self.m.PLAN_ARCHIVE.write_bytes(b'foreign'); self.m.PLAN_ARCHIVE.chmod(0o600)
        with self.assertRaisesRegex(self.m.Refusal, 'illegal-record-state'):
            self.m.recover(True)
        self.assertTrue(self.m.PLAN.exists()); self.assertEqual(self.m.PLAN_ARCHIVE.read_bytes(), b'foreign')

    def test_replacement_before_execute_refuses(self):
        self.m.PLAN.unlink(); self.m.PLAN.symlink_to(self.m.JOURNAL)
        with self.assertRaises((OSError, self.m.Refusal)):
            self.m.recover(True)
        self.assertTrue(self.m.JOURNAL.exists()); self.assertFalse(self.m.PLAN_ARCHIVE.exists())

    def test_rename_failure_does_not_rename_journal(self):
        original = self.m._rename_noreplace
        def fail(fd, source, destination):
            if source == self.m.PLAN_SENTINEL.name: raise RuntimeError('injected-crash')
            return original(fd, source, destination)
        with mock.patch.object(self.m, '_rename_noreplace', fail):
            with self.assertRaisesRegex(RuntimeError, 'injected-crash'): self.m.recover(True)
        self.assertTrue(self.m.PLAN.exists()); self.assertTrue(self.m.JOURNAL.exists())

    def test_replacement_before_exchange_is_detected(self):
        original = self.m._exchange
        def replace_then_exchange(fd, source, sentinel):
            self.m.PLAN.unlink()
            self.m.PLAN.write_bytes(b'foreign'); self.m.PLAN.chmod(0o600)
            return original(fd, source, sentinel)
        with mock.patch.object(self.m, '_exchange', replace_then_exchange):
            with self.assertRaisesRegex(self.m.Refusal, 'record-identity'):
                self.m.recover(True)
        self.assertFalse(self.m.PLAN_ARCHIVE.exists())

    def test_live_source_reappearance_refuses_terminal_replay(self):
        self.m.recover(True)
        if self.m.PLAN.exists(): self.m.PLAN.rmdir()
        self.m.PLAN.write_bytes(b'foreign'); self.m.PLAN.chmod(0o600)
        with self.assertRaisesRegex(self.m.Refusal, 'illegal-record-state'):
            self.m.recover(True)

    def test_every_durable_mutation_frontier_resumes(self):
        # mkdir, exchange, file archive, marker archive for each record.
        for frontier in range(1, 9):
            with self.subTest(frontier=frontier):
                case = SyntheticRecoveryTests()
                case.setUp()
                try:
                    m = case.m
                    calls = [0]
                    def after(fn):
                        def wrapped(*args, **kwargs):
                            result = fn(*args, **kwargs)
                            calls[0] += 1
                            if calls[0] == frontier:
                                raise RuntimeError('crash')
                            return result
                        return wrapped
                    with mock.patch.object(m.os, 'mkdir', after(os.mkdir)), \
                         mock.patch.object(m, '_exchange', after(m._exchange)), \
                         mock.patch.object(m, '_rename_noreplace', after(m._rename_noreplace)):
                        with self.assertRaisesRegex(RuntimeError, 'crash'):
                            m.recover(True)
                    m.recover(True)
                    self.assertEqual(m.recover(True)['status'], 'PASS_TERMINAL_REPLAY')
                    for source, archive, record in m.ARCHIVES:
                        self.assertFalse(source.exists())
                        self.assertEqual(archive.stat().st_ino, record[1])
                finally:
                    case.doCleanups()

    def test_capture_foreign_source_preserves_both_objects(self):
        original = self.m._exchange
        preserved = self.m.ROOT / 'preserved-plan'
        def replace(fd, source, sentinel):
            self.m.PLAN.rename(preserved)
            self.m.PLAN.write_bytes(b'foreign')
            self.m.PLAN.chmod(0o600)
            return original(fd, source, sentinel)
        with mock.patch.object(self.m, '_exchange', replace):
            with self.assertRaises(self.m.Refusal):
                self.m.recover(True)
        self.assertEqual(self.m.PLAN_SENTINEL.read_bytes(), b'foreign')
        self.assertTrue(self.m.PLAN.is_dir())
        self.assertEqual(preserved.stat().st_ino, self.m.PLAN_RECORD[1])

    def test_foreign_marker_at_final_rename_is_retained_and_refused(self):
        original = self.m._rename_noreplace
        preserved = self.m.ROOT / 'original-marker'
        def replace(fd, source, destination):
            if source == self.m.PLAN.name:
                self.m.PLAN.rename(preserved)
                self.m.PLAN.mkdir(mode=0o700)
            return original(fd, source, destination)
        with mock.patch.object(self.m, '_rename_noreplace', replace):
            with self.assertRaisesRegex(self.m.Refusal, 'sentinel-replaced'):
                self.m.recover(True)
        self.assertTrue(preserved.is_dir())
        self.assertTrue(self.m._retained(self.m.PLAN_SENTINEL).is_dir())
        self.assertTrue(self.m.PLAN_ARCHIVE.is_file())
        self.assertTrue(self.m.JOURNAL.is_file())

    def test_archive_rename_collision_preserves_capture(self):
        original = self.m._rename_noreplace
        def collide(fd, source, destination):
            if source == self.m.PLAN_SENTINEL.name:
                self.m.PLAN_ARCHIVE.write_bytes(b'collision')
            return original(fd, source, destination)
        with mock.patch.object(self.m, '_rename_noreplace', collide):
            with self.assertRaises(FileExistsError):
                self.m.recover(True)
        self.assertEqual(self.m.PLAN_SENTINEL.stat().st_ino, self.m.PLAN_RECORD[1])
        self.assertEqual(self.m.PLAN_ARCHIVE.read_bytes(), b'collision')

    def test_retained_marker_collision_refuses(self):
        self.m._retained(self.m.PLAN_SENTINEL).mkdir(mode=0o700)
        with self.assertRaisesRegex(self.m.Refusal, 'illegal-record-state'):
            self.m.recover(True)
        self.assertTrue(self.m.PLAN.is_file())

    def test_out_of_order_journal_prefix_refuses(self):
        self.m.JOURNAL_SENTINEL.mkdir(mode=0o700)
        with self.assertRaisesRegex(self.m.Refusal, 'out-of-order-prefix'):
            self.m.recover(True)

    def test_nonempty_marker_refuses_without_deletion(self):
        self.m.PLAN_SENTINEL.mkdir(mode=0o700)
        foreign = self.m.PLAN_SENTINEL / 'foreign'
        foreign.write_bytes(b'preserve')
        with self.assertRaisesRegex(self.m.Refusal, 'sentinel-identity'):
            self.m.recover(True)
        self.assertEqual(foreign.read_bytes(), b'preserve')

    def test_tmp_absence_check_is_descriptor_relative_and_nofollow(self):
        original = self.m.os.stat
        observed = []
        def stat_checked(path, *args, **kwargs):
            if path == 'tmp8aj5goke':
                observed.append(kwargs)
                raise FileNotFoundError()
            return original(path, *args, **kwargs)
        with mock.patch.object(self.m.os, 'stat', stat_checked), \
             mock.patch.object(self.m.os.path, 'lexists', side_effect=AssertionError('lexists forbidden')):
            self.m.recover()
        self.assertEqual(len(observed), 1)
        self.assertIsInstance(observed[0]['dir_fd'], int)
        self.assertIs(observed[0]['follow_symlinks'], False)

    def test_tmp_permission_error_is_not_absence(self):
        original = self.m.os.stat
        def denied(path, *args, **kwargs):
            if path == 'tmp8aj5goke':
                raise PermissionError('denied')
            return original(path, *args, **kwargs)
        with mock.patch.object(self.m.os, 'stat', denied):
            with self.assertRaises(PermissionError):
                self.m.recover(True)
        self.assertTrue(self.m.PLAN.is_file())

    def test_present_tmp_ancestor_always_refuses(self):
        original = self.m.os.stat
        def present(path, *args, **kwargs):
            if path == 'tmp8aj5goke':
                return original(self.m.ROOT)
            return original(path, *args, **kwargs)
        with mock.patch.object(self.m.os, 'stat', present):
            with self.assertRaisesRegex(self.m.Refusal, 'synthetic-source-present'):
                self.m.recover(True)

    def test_terminal_sentinel_reappearance_refuses(self):
        self.m.recover(True)
        self.m.PLAN_SENTINEL.symlink_to(self.m.PLAN_ARCHIVE)
        with self.assertRaisesRegex(self.m.Refusal, 'illegal-record-state'):
            self.m.recover(True)

    def test_real_read_atime_change_preserves_stable_identity(self):
        # Use a real filesystem atime update, not a mocked stat_result. An old
        # atime guarantees eligibility under the test filesystem's relatime.
        old = self.m.PLAN.stat()
        os.utime(self.m.PLAN, ns=(1, old.st_mtime_ns))
        before = self.m.PLAN.stat()
        fd = self.m._open_root()
        try:
            data = self.m._read(fd, self.m.PLAN, self.m.PLAN_RECORD)
        finally:
            os.close(fd)
        after = self.m.PLAN.stat()
        self.assertGreater(after.st_atime_ns, before.st_atime_ns)
        self.assertEqual(after.st_mtime_ns, before.st_mtime_ns)
        self.assertEqual(after.st_ctime_ns, before.st_ctime_ns)
        self.assertEqual(self.m.digest(data), self.m.PLAN_RECORD[0])

    def test_metadata_mutation_during_read_still_refuses(self):
        original = self.m.os.read
        def mutate(fd, size):
            data = original(fd, size)
            os.fchmod(fd, 0o640)
            return data
        fd = self.m._open_root()
        try:
            with mock.patch.object(self.m.os, 'read', mutate):
                with self.assertRaisesRegex(self.m.Refusal, 'record-mutated'):
                    self.m._read(fd, self.m.PLAN, self.m.PLAN_RECORD)
        finally:
            os.close(fd)

    def test_production_exchanged_plan_prefix_validates_and_resumes(self):
        # Production refusal left PLAN=directory, PLAN_SENTINEL=exact file,
        # JOURNAL=exact live file; no archives or journal sentinel exist.
        self.m.PLAN_SENTINEL.mkdir(mode=0o700)
        marker_inode = self.m.PLAN_SENTINEL.stat().st_ino
        fd = self.m._open_root()
        try:
            self.m._exchange(fd, self.m.PLAN.name, self.m.PLAN_SENTINEL.name)
            os.fsync(fd)
            _, states = self.m._states(fd)
            self.assertEqual([stage for stage, _ in states], [2, 0])
        finally:
            os.close(fd)
        captured = self.m.PLAN_SENTINEL.stat()
        os.utime(self.m.PLAN_SENTINEL, ns=(1, captured.st_mtime_ns))
        self.assertEqual(self.m.recover(), {'status': 'PASS_VALIDATE_ONLY', 'terminal': False})
        self.assertEqual(self.m.PLAN.stat().st_ino, marker_inode)
        self.assertEqual(self.m.PLAN_SENTINEL.stat().st_ino, self.m.PLAN_RECORD[1])
        self.assertFalse(self.m.PLAN_ARCHIVE.exists())
        with mock.patch.object(self.m, '_exchange', wraps=self.m._exchange) as exchange:
            self.assertEqual(self.m.recover(True)['status'], 'PASS_EXECUTED')
        self.assertEqual(exchange.call_count, 1)
        self.assertEqual(exchange.call_args.args[1:], (self.m.JOURNAL.name, self.m.JOURNAL_SENTINEL.name))
        self.assertEqual(self.m._retained(self.m.PLAN_SENTINEL).stat().st_ino, marker_inode)
        self.assertEqual(self.m.PLAN_ARCHIVE.stat().st_ino, self.m.PLAN_RECORD[1])
        self.assertEqual(self.m.JOURNAL_ARCHIVE.stat().st_ino, self.m.JOURNAL_RECORD[1])

if __name__ == '__main__': unittest.main()
