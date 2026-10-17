"""No live target/proc/rootlock/Docker access: exact recovery proof sequencing."""
import ast
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import select
import signal
import tempfile
import unittest
from unittest import mock

SOURCE = Path(__file__).resolve().parents[1] / 'native_exact_scratch22_authority1_quarantine_recovery.py'
spec = importlib.util.spec_from_file_location('recovery_under_test', SOURCE)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class Hold(BaseException):
    pass


class RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.handlers = {number: signal.getsignal(number) for number in m.DEFERRED_SIGNALS}
        self.mask = signal.pthread_sigmask(signal.SIG_BLOCK, set())
        self.addCleanup(self.restore_signals)
        self.events = []
        self.release = {'source_checkpoint': 'a' * 40}
        self.proof = {'inputs': {'retained': 'exact'}, 'captures': {}, 'root_locks': []}

    def restore_signals(self):
        signal.pthread_sigmask(signal.SIG_BLOCK, m.DEFERRED_SIGNALS)
        for number, handler in self.handlers.items():
            signal.signal(number, handler)
        signal.pthread_sigmask(signal.SIG_SETMASK, self.mask)

    def run_mocked(self, failure=None):
        def snapshot(label, *args):
            self.events.append(label)
            if failure == label:
                raise m.Refusal('disposable proof uncertainty')
            return copy.deepcopy(self.proof)
        def publish(path, raw):
            self.events.append(path.name)
            if failure == 'complete-write' and path == m.COMPLETE:
                raise OSError('disposable receipt writer failure')
            if path == m.PREPARED:
                self.assertEqual(json.loads(raw)['signal_budget'], 1)
        def sigkill(fd):
            self.events.append('sole-sigkill')
            self.assertIn(m.PREPARED.name, self.events)
            if failure == 'signal-response':
                raise OSError('uncertain syscall response')
            return {'syscall': 424, 'signal': 9, 'returncode': 0}
        def hold(fd):
            self.events.append(('hold', fd))
            raise Hold()
        with mock.patch.object(m, 'bind_release', return_value=(self.release, {})), \
             mock.patch.object(m, 'snapshot', side_effect=snapshot), \
             mock.patch.object(m, 'pidfd_open', return_value=41), \
             mock.patch.object(m, 'bind_pidfd', return_value={'pid': m.PID, 'starttime': m.START}) as bind, \
             mock.patch.object(m, 'publish', side_effect=publish), \
             mock.patch.object(m, 'require_lock_holder'), \
             mock.patch.object(m, 'sole_sigkill', side_effect=sigkill) as sent, \
             mock.patch.object(m, 'exit_ready', return_value={'pidfd_exit_ready': True}), \
             mock.patch.object(m, 'acquire_root_lock', return_value=42), \
             mock.patch.object(m, 'quarantine_hold', side_effect=hold), \
             mock.patch.object(m.os, 'close', side_effect=lambda fd: self.events.append(('close', fd))):
            if failure in ('signal-response', 'after', 'complete-write'):
                with self.assertRaises(Hold):
                    m.execute(Path('/disposable-release'), 'b' * 64)
                self.assertEqual(sent.call_count, 1)
                self.assertNotIn(('close', 42), self.events)
                return
            if failure:
                with self.assertRaises(m.Refusal):
                    m.execute(Path('/disposable-release'), 'b' * 64)
                sent.assert_not_called()
                return
            result = m.execute(Path('/disposable-release'), 'b' * 64)
            self.assertEqual(result['status'], 'COMPLETE_PROCESS_RECOVERY')
            self.assertEqual(result['build_status'], 'FAIL')
            self.assertTrue(result['cleanup_required'])
            sent.assert_called_once_with(41)
            self.assertEqual(bind.call_count, 3)

    def test_prepared_before_sole_signal_and_complete_before_root_unlock(self):
        self.run_mocked()
        self.assertLess(self.events.index(m.PREPARED.name), self.events.index('sole-sigkill'))
        self.assertLess(self.events.index(m.COMPLETE.name), self.events.index(('close', 42)))
        self.assertEqual(self.events[:2], ['before1', 'before2'])

    def test_pre_signal_failure_never_sends_or_acquires_replacement(self):
        self.run_mocked('before2')
        self.assertNotIn('sole-sigkill', self.events)
        self.assertNotIn(('close', 42), self.events)

    def test_uncertain_signal_response_consumes_budget_and_never_retries(self):
        self.run_mocked('signal-response')
        self.assertIn(('hold', None), self.events)

    def test_postflight_or_complete_writer_failure_keeps_replacement_lock(self):
        for failure in ('after', 'complete-write'):
            with self.subTest(failure=failure):
                self.events.clear()
                self.run_mocked(failure)
                self.assertIn(('hold', 42), self.events)

    def test_pidfd_syscalls_only_and_no_numeric_fallback(self):
        libc = mock.Mock()
        libc.syscall.side_effect = [23, 0]
        with mock.patch.object(m.ctypes, 'CDLL', return_value=libc), mock.patch.object(m.os, 'kill') as kill:
            self.assertEqual(m.pidfd_open(), 23)
            self.assertEqual(m.sole_sigkill(23)['returncode'], 0)
        calls = libc.syscall.call_args_list
        self.assertEqual(calls[0].args[0], 434)
        self.assertEqual(calls[0].args[1].value, 80259)
        self.assertEqual(calls[1].args[0], 424)
        self.assertEqual(calls[1].args[1].value, 23)
        self.assertEqual(calls[1].args[2].value, signal.SIGKILL)
        kill.assert_not_called()
        libc.syscall.side_effect = [-1]
        with mock.patch.object(m.ctypes, 'CDLL', return_value=libc), mock.patch.object(m.os, 'kill') as kill:
            with self.assertRaises(OSError): m.pidfd_open()
        kill.assert_not_called()

    def test_pidfd_fdinfo_must_name_exact_target_before_identity_check(self):
        with mock.patch.object(m, 'proc_bytes', return_value=b'Pid:\t80260\n'), \
             mock.patch.object(m, 'guard_identity') as guard:
            with self.assertRaisesRegex(m.Refusal, 'pidfd target'): m.bind_pidfd(41, {})
            guard.assert_not_called()
        with mock.patch.object(m, 'proc_bytes', return_value=b'Pid:\t80259\n'), \
             mock.patch.object(m, 'guard_identity', return_value={'exact': True}) as guard:
            self.assertEqual(m.bind_pidfd(41, {}), {'exact': True})
            guard.assert_called_once_with({})

    def report(self, before=True):
        rows = [[1, 0, '1'], [91, 1, '100']]
        if before: rows.append([m.PID, m.PARENT, m.START])
        return {'schema': 'scratch21.proc.v1', 'uid': 0, 'boot_id': m.BOOT,
                'challenge': 'fresh', 'caller': [91, '100'],
                'publishers': [[m.PID, m.START, '/usr/bin/python3.8']] * 2 if before else [],
                'snapshots': [copy.deepcopy(rows), copy.deepcopy(rows)]}

    def test_exact_twice_before_and_no_publisher_after_root_census(self):
        m.validate_process_report(self.report(), 'fresh', [91, '100'], True)
        m.validate_process_report(self.report(False), 'fresh', [91, '100'], False)
        for mutation in (lambda r: r.update(challenge='stale'), lambda r: r.update(boot_id='stale'),
                         lambda r: r.update(publishers=[]),
                         lambda r: r['snapshots'][0].append([80867, 1, 'reused']),
                         lambda r: r['snapshots'][0].append([101, m.PID, '2'])):
            report = self.report(); mutation(report)
            with self.assertRaises(m.Refusal): m.validate_process_report(report, 'fresh', [91, '100'], True)
        report = self.report(False); report['publishers'] = [[m.PID, m.START, '/usr/bin/python3.8']]
        with self.assertRaises(m.Refusal): m.validate_process_report(report, 'fresh', [91, '100'], False)

    def test_positive_exit_allows_reaped_pidfd_hup_but_no_error_or_timeout(self):
        poller = mock.Mock()
        for events in ([(41, select.POLLIN)], [(41, select.POLLIN | select.POLLHUP)]):
            poller.poll.return_value = events
            with mock.patch.object(m.select, 'poll', return_value=poller):
                self.assertTrue(m.exit_ready(41)['pidfd_exit_ready'])
        for events in ([], [(41, select.POLLHUP)], [(41, select.POLLNVAL)], [(42, select.POLLIN)]):
            poller.poll.return_value = events
            with mock.patch.object(m.select, 'poll', return_value=poller), self.assertRaises(m.Refusal):
                m.exit_ready(41)

    def test_profile_file_fields_do_not_mistake_semantic_fields_for_metadata(self):
        profile = json.loads(m.PROFILE.read_bytes())  # Reviewed source document only.
        rows = m.profile_inputs(profile)
        self.assertEqual(len(rows), 9)
        self.assertTrue(all(set(row) <= {'path', 'device', 'inode', 'size', 'sha256'} for row in rows))
        self.assertEqual(hashlib.sha256(m.PROFILE.read_bytes()).hexdigest(), m.PROFILE_SHA)

    def test_accepted_process_code_is_extracted_verbatim(self):
        raw = m.PROC_SOURCE.read_bytes()  # Reviewed source document, never active proc.
        tree = ast.parse(raw)
        expected = next(ast.literal_eval(node.value) for node in tree.body if isinstance(node, ast.Assign) and
                        any(isinstance(target, ast.Name) and target.id == 'PROC_CODE' for target in node.targets))
        self.assertEqual(m.process_code(), expected)
        self.assertEqual(hashlib.sha256(raw).hexdigest(), m.PROC_SOURCE_SHA)

    def test_stream_hash_preserves_original_and_publications_are_one_shot(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / 'proof'
            payload = b'complete retained bytes'
            m.publish(path, payload)
            before = path.stat()
            row, raw = m.file_identity(path, keep=False)
            self.assertIsNone(raw)
            self.assertEqual(row['sha256'], hashlib.sha256(payload).hexdigest())
            self.assertEqual(path.stat().st_mtime_ns, before.st_mtime_ns)
            with self.assertRaises(FileExistsError): m.publish(path, b'overwrite forbidden')
            self.assertEqual(path.read_bytes(), payload)

    def test_cli_without_execute_never_enters_recovery(self):
        with mock.patch.object(m, 'execute') as execute:
            with self.assertRaises(m.Refusal):
                m.main(['--release', '/not-opened', '--release-sha256', 'b' * 64])
        execute.assert_not_called()

    def test_future_source_authorization_and_one_shot_gate_are_exact(self):
        files = {str(m.SELF.relative_to(m.REPO)): '1' * 64,
                 str(m.TEST.relative_to(m.REPO)): '2' * 64}
        review_path = Path('/disposable-independent-review')
        release = {'schema': 'scratch22-authority1.quarantine-recovery-release.v1',
                   'status': 'PASS_EXECUTION_RELEASE', 'profile_sha256': m.PROFILE_SHA,
                   'execution_count': 1, 'fetched_source_verified': True,
                   'source_checkpoint': 'a' * 40, 'author': '/author', 'files_sha256': files,
                   'source_review': {'path': str(review_path), 'sha256': '3' * 64}}
        review = {'decision': 'PASS_SOURCE', 'implementation_ownership': False,
                  'reviewer': '/independent', 'files_sha256': files,
                  'profile_sha256': m.PROFILE_SHA, 'source_checkpoint': 'a' * 40}
        def read(path, expected):
            if path == m.PROFILE:
                self.assertEqual(expected, m.PROFILE_SHA)
                return {'decision': 'PASS_PROPOSED_PROCESS_RETIREMENT_PROFILE'}
            if path == review_path:
                self.assertEqual(expected, '3' * 64)
                return review
            return release
        def identity(path):
            return {'sha256': files[str(path.relative_to(m.REPO))]}, None
        with mock.patch.object(m, 'read_json', side_effect=read), \
             mock.patch.object(m, 'file_identity', side_effect=identity), \
             mock.patch.object(m.os, 'getuid', return_value=1000), \
             mock.patch.object(m.os, 'getgid', return_value=1000), \
             mock.patch.object(m.os, 'geteuid', return_value=1000), \
             mock.patch.object(m.os, 'getegid', return_value=1000), \
             mock.patch.object(m.os, 'sched_getaffinity', return_value={0}), \
             mock.patch.object(m.os.path, 'lexists', return_value=False):
            self.assertEqual(m.bind_release(Path('/disposable-release'), '4' * 64)[0], release)
            review['reviewer'] = '/author'
            with self.assertRaisesRegex(m.Refusal, 'independent exact'): m.bind_release(Path('/disposable-release'), '4' * 64)
            review['reviewer'] = '/independent'
            with mock.patch.object(m.os.path, 'lexists', return_value=True):
                with self.assertRaisesRegex(m.Refusal, 'one-shot'): m.bind_release(Path('/disposable-release'), '4' * 64)
            release['execution_count'] = True
            with self.assertRaisesRegex(m.Refusal, 'exact recovery release'): m.bind_release(Path('/disposable-release'), '4' * 64)


if __name__ == '__main__':
    unittest.main()
