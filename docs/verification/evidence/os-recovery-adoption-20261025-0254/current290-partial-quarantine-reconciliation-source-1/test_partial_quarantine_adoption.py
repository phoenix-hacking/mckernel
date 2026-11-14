"""Functional OS fixtures only; no security testing. Private files only."""
import copy
import fcntl
import importlib.util
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock
import types

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('partial', HERE / 'partial_quarantine_adoption.py')
p = importlib.util.module_from_spec(spec)
spec.loader.exec_module(p)


class ActualPrivateTransaction:
    def __enter__(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='partial-fixture-', dir=HERE)
        self.root = Path(self.tmp.name)
        self.ns = self.root / 'namespace'
        self.ns.mkdir(mode=0o700)
        m = self.m = p.reviewed_phase_algorithms()
        m.ROOT, m.NAMESPACE = self.root, self.ns
        m.DEVICE, m.UID, m.GID = self.root.stat().st_dev, os.getuid(), os.getgid()
        m.ATTEMPT = self.ns / 'common'
        m.SHARED = self.root / 'shared'
        m.MUTEX, m.PLAN, m.JOURNAL = [self.root / x for x in ('mutex', 'plan', 'journal')]
        m.CAPTURE, m.QUARANTINE = [self.root / x for x in ('capture', 'quarantine')]
        m.OUTPUT, m.EVIDENCE = self.ns / 'owner-work', self.ns / 'owner-evidence'
        m.TERMINAL = m.EVIDENCE / 'owner-receipt'
        m.LIMIT = 1 << 20
        m.ARCHIVE_NAMES = ('common.archive', 'shared.archive')
        m.owned_record_paths = lambda: [m.ATTEMPT, m.SHARED]
        m.path_device = lambda path: m.DEVICE
        for path in (m.OUTPUT, m.EVIDENCE):
            path.mkdir(mode=0o700)
        self.write(m.TERMINAL, b'original terminal\n')
        m.TERMINAL_SHA = p.digest(m.TERMINAL.read_bytes())
        m.TERMINAL_INODE, m.TERMINAL_SIZE = m.TERMINAL.stat().st_ino, m.TERMINAL.stat().st_size
        m.DIRS = {x: (x.stat().st_dev, x.stat().st_ino, x.stat().st_nlink) for x in (m.OUTPUT, m.EVIDENCE)}
        self.common_archive = self.ns / m.ARCHIVE_NAMES[0]
        self.write(self.common_archive, b'original common bytes\n')
        self.write(m.SHARED, b'original shared bytes\n')
        self.shared_sentinel = self.root / m.ARCHIVE_NAMES[1]
        self.shared_sentinel.mkdir(mode=0o700)
        # A common sentinel was already released. Its original inode is retained
        # only in the immutable plan; never recreate it for continuation.
        gone = self.ns / 'released-common-sentinel'
        gone.mkdir(mode=0o700)
        common_sentinel = [gone.stat().st_dev, gone.stat().st_ino]
        gone.rmdir()
        m.RECORDS = {x: (p.digest(actual.read_bytes()), actual.stat().st_ino, actual.stat().st_size)
                     for x, actual in ((m.ATTEMPT, self.common_archive), (m.SHARED, m.SHARED))}
        self.plan = dict(schema='fixture-original-release-plan', release_sha256='original-release',
                         sentinels=[common_sentinel, [self.shared_sentinel.stat().st_dev, self.shared_sentinel.stat().st_ino]])
        self.plan_raw = p.canonical(self.plan) + b'\n'
        self.write(m.PLAN, self.plan_raw)
        self.write(m.JOURNAL, b'')
        self.tx = m.Transaction()
        self.tx.fd = os.open(self.root, os.O_RDONLY | os.O_DIRECTORY)
        self.tx.nfd = os.open(self.ns, os.O_RDONLY | os.O_DIRECTORY)
        self.tx.pinned = self.pinned
        self.rows = []
        for event in ('before_exchange', 'after_exchange', 'release', 'after_release'):
            self.tx.append(self.plan, self.rows, event, 0)
        self.journal_raw = m.JOURNAL.read_bytes()
        self.common_meta = self.common_archive.stat()
        self.protected_raw = m.TERMINAL.read_bytes()
        return self

    @staticmethod
    def write(path, raw):
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        try:
            os.write(fd, raw)
        finally:
            os.close(fd)

    def pinned(self):
        # Fixture namespace binding replaces root/mount/actor controls only.
        # The original preserved(), state(), append(), sentinel() are unchanged.
        for path, fd in ((self.root, self.tx.fd), (self.ns, self.tx.nfd)):
            if (path.stat().st_dev, path.stat().st_ino) != (os.fstat(fd).st_dev, os.fstat(fd).st_ino):
                raise p.Refusal('fixture-parent-replaced')

    def __exit__(self, *args):
        os.close(self.tx.fd)
        os.close(self.tx.nfd)
        self.tmp.cleanup()


class PhaseTests(unittest.TestCase):
    def test_exact_retained_snapshot_has_no_runtime_authority(self):
        proof = p.authenticate_retained_snapshot()
        self.assertEqual(proof['remaining_record_indices'], [1])
        self.assertFalse(proof['runtime_authority'])
        self.assertFalse(proof['fresh_live_state'])

    def test_real_files_partial_phase_and_all_shared_transitions(self):
        with ActualPrivateTransaction() as f:
            m, tx = f.m, f.tx
            self.assertEqual(p.require_partial_phase(tx, f.plan, f.plan_raw, f.journal_raw), (1,))
            original = f.common_archive.read_bytes()
            original_stat = f.common_archive.stat()
            # Functional local fixture exercises only the remaining index1 with
            # original reviewed state/append/exchange/release primitives.
            tx.append(f.plan, f.rows, 'before_exchange', 1)
            self.assertEqual(tx.state(f.plan)[1], ['after_release', 'before_exchange'])
            m.rename_exchange(tx.fd, m.SHARED.name, m.ARCHIVE_NAMES[1])
            os.fsync(tx.fd)
            self.assertEqual(tx.state(f.plan)[1], ['after_release', 'after_exchange'])
            tx.append(f.plan, f.rows, 'after_exchange', 1)
            tx.append(f.plan, f.rows, 'release', 1)
            tx.sentinel(m.SHARED.name, f.plan['sentinels'][1], tx.fd)
            os.rmdir(m.SHARED.name, dir_fd=tx.fd)
            os.fsync(tx.fd)
            self.assertEqual(tx.state(f.plan)[1], ['after_release', 'after_release'])
            tx.append(f.plan, f.rows, 'after_release', 1)
            tx.append(f.plan, f.rows, 'complete', 2)
            self.assertEqual(len(tx.state(f.plan)[0]), 9)
            self.assertEqual(f.common_archive.read_bytes(), original)
            after = f.common_archive.stat()
            for field in ('st_dev', 'st_ino', 'st_nlink', 'st_size', 'st_mtime_ns', 'st_ctime_ns'):
                self.assertEqual(getattr(after, field), getattr(original_stat, field))
            self.assertFalse(m.ATTEMPT.exists())
            self.assertEqual(m.TERMINAL.read_bytes(), f.protected_raw)
            self.assertTrue(m.JOURNAL.read_bytes().startswith(f.journal_raw))

    def test_shared_foreign_bytes_refused(self):
        with ActualPrivateTransaction() as f:
            f.m.SHARED.write_bytes(b'changed foreign bytes\n')
            with self.assertRaises(p.Refusal):
                p.require_partial_phase(f.tx, f.plan, f.plan_raw, f.journal_raw)

    def test_common_archive_change_refused(self):
        with ActualPrivateTransaction() as f:
            f.common_archive.write_bytes(b'wrong common\n')
            with self.assertRaises(p.Refusal):
                f.tx.state(f.plan)

    def test_common_sentinel_reappearance_refused(self):
        with ActualPrivateTransaction() as f:
            f.m.ATTEMPT.mkdir(mode=0o700)
            with self.assertRaisesRegex(p.Refusal, 'sentinel-reappeared-after-release'):
                f.tx.state(f.plan)

    def test_journal_torn_or_reordered_refused(self):
        for mode in ('torn', 'reordered'):
            with self.subTest(mode=mode), ActualPrivateTransaction() as f:
                raw = f.journal_raw[:-1] if mode == 'torn' else b'\n'.join(reversed(f.journal_raw.splitlines())) + b'\n'
                f.m.JOURNAL.write_bytes(raw)
                with self.assertRaises(p.Refusal):
                    f.tx.state(f.plan)

    def test_nonempty_remaining_sentinel_refused(self):
        with ActualPrivateTransaction() as f:
            (f.shared_sentinel / 'foreign').write_text('preserve')
            with self.assertRaisesRegex(p.Refusal, 'sentinel-binding'):
                f.tx.state(f.plan)

    def test_protected_terminal_change_refused(self):
        with ActualPrivateTransaction() as f:
            f.m.TERMINAL.write_bytes(b'changed terminal')
            with self.assertRaises(p.Refusal):
                f.tx.state(f.plan)

    def test_adoption_rejects_progress_beyond_exact_prefix(self):
        with ActualPrivateTransaction() as f:
            f.tx.append(f.plan, f.rows, 'before_exchange', 1)
            with self.assertRaisesRegex(p.Refusal, 'adoption-journal-raw-binding'):
                p.require_partial_phase(f.tx, f.plan, f.plan_raw, f.journal_raw)

    def test_same_inode_new_open_is_not_held_description(self):
        with tempfile.TemporaryDirectory(prefix='custody-fixture-', dir=HERE) as tmp:
            path = Path(tmp) / 'private.lock'
            path.touch(mode=0o600)
            holder = os.open(path, os.O_RDONLY)
            duplicate = independent = None
            try:
                fcntl.flock(holder, fcntl.LOCK_EX | fcntl.LOCK_NB)
                duplicate = os.dup(holder)
                fields = ('st_dev', 'st_ino', 'st_mode', 'st_uid', 'st_gid', 'st_nlink', 'st_size', 'st_mtime_ns', 'st_ctime_ns')
                meta = {name: getattr(os.fstat(holder), name) for name in fields}
                self.assertTrue(p.verify_description_custody(duplicate, os.getpid(), holder, path, meta)['same_description_observed'])
                independent = os.open(path, os.O_RDONLY)
                with self.assertRaisesRegex(p.Refusal, 'custody-same-description-lock'):
                    p.verify_description_custody(independent, os.getpid(), holder, path, meta)
                os.close(holder)
                holder = None
                with self.assertRaises(BlockingIOError):
                    fcntl.flock(independent, fcntl.LOCK_EX | fcntl.LOCK_NB)
                os.close(duplicate)
                duplicate = None
                fcntl.flock(independent, fcntl.LOCK_EX | fcntl.LOCK_NB)
            finally:
                for fd in (holder, duplicate, independent):
                    if fd is not None:
                        os.close(fd)


class StandbyProtocolTests(unittest.TestCase):
    def load(self):
        spec = importlib.util.spec_from_file_location('standby', HERE / 'fixed_root_custody_standby.SOURCE-ONLY.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def run_protocol(self, fail_after_copy=False, fail_before_copy=False, denied=False):
        module = self.load()
        events = []
        class Syscall:
            restype = None
            def __call__(self, number, *args):
                n = number.value
                events.append(('syscall', n, [arg.value for arg in args]))
                return 77 if n == 434 else (-1 if denied else 88)
        libc = types.SimpleNamespace(syscall=Syscall())
        metadata = types.SimpleNamespace(st_dev=27, st_ino=4, st_uid=0, st_gid=0,
                                         st_nlink=1, st_size=0, st_mode=0o100644,
                                         st_mtime_ns=123, st_ctime_ns=456)
        fake_p = types.SimpleNamespace(need=p.need, ROOT_MUTEX=Path('/fixture-only/unopened'),
                                        ROOT_ACTOR=p.ROOT_ACTOR, SCOPE=p.SCOPE)
        def verify(*args):
            events.append(('custody', args[0]))
            if fail_after_copy:
                raise p.Refusal('mock postcopy proof refusal')
            return dict(device=27, inode=4)
        fake_p.verify_description_custody = verify
        def live(_p, pidfd):
            events.append(('live', pidfd))
            if fail_before_copy:
                raise p.Refusal('mock pre-copy dead pidfd')
        with mock.patch.object(module, 'adoption', return_value=fake_p), \
             mock.patch.object(module, 'actor_binding', side_effect=lambda _p: ('exact-actor', 'exact-parent')), \
             mock.patch.object(module, 'live_pidfd', side_effect=live), \
             mock.patch.object(module.os, 'stat', return_value=metadata), \
             mock.patch.object(module.os, 'close', side_effect=lambda fd: events.append(('close', fd))), \
             mock.patch.object(module.ctypes, 'CDLL', return_value=libc):
            if fail_before_copy or denied:
                with self.assertRaises((p.Refusal, OSError)):
                    module.acquire_exact_standby()
                return events, None
            return events, module.acquire_exact_standby()

    def test_standby_authenticates_before_getfd_and_keeps_both_fds(self):
        events, hold = self.run_protocol()
        self.assertTrue(hold.verified)
        self.assertEqual((hold.fd, hold.pidfd), (88, 77))
        self.assertLess(events.index(('live', 77)), events.index(('syscall', 438, [77, 3, 0])))
        self.assertLess(events.index(('syscall', 438, [77, 3, 0])), events.index(('custody', 88)))
        self.assertFalse(any(event[0] == 'close' for event in events))
        self.assertFalse(hold.proof['actual_retirement'])

    def test_postcopy_failure_returns_retained_unverified_hold(self):
        events, hold = self.run_protocol(fail_after_copy=True)
        self.assertFalse(hold.verified)
        self.assertIn('postcopy proof refusal', hold.error)
        self.assertEqual((hold.fd, hold.pidfd), (88, 77))
        self.assertFalse(any(event[0] == 'close' for event in events))

    def test_dead_pidfd_before_copy_never_requests_getfd(self):
        events, _ = self.run_protocol(fail_before_copy=True)
        self.assertNotIn(('syscall', 438, [77, 3, 0]), events)
        self.assertEqual(events[-1], ('close', 77))

    def test_getfd_denied_closes_only_pidfd_and_never_falls_back(self):
        events, _ = self.run_protocol(denied=True)
        self.assertEqual([event for event in events if event[0] == 'syscall'],
                         [('syscall', 434, [1060806, 0]), ('syscall', 438, [77, 3, 0])])
        self.assertEqual(events[-1], ('close', 77))


if __name__ == '__main__':
    unittest.main(verbosity=2)
