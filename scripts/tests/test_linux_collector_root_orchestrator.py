"""Controlled recovery-owner tests; Docker/root/runtime are never used."""
import importlib.util
import copy
import fcntl
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock

PATH = Path(__file__).parent / 'fixtures/application-collector-v1/linux-sealed-v1/root_orchestrator.py'
spec = importlib.util.spec_from_file_location('collector_root_orchestrator', PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class RecoveryOwnerTests(unittest.TestCase):
    def _rebuild_record(self):
        path = module.BUILD / 'record.json'
        return json.loads(path.read_text())

    def test_rebuild_owner_binding_is_exact(self):
        record = self._rebuild_record()
        module.validate_build_record_schema(record)
        self.assertEqual(module.BUILD_SHA,
                         'fa12fe8df3092f64fbe757bbd3ccad62bd8a672cbda39fb4153ffd54c6d917ed')
        self.assertEqual(module.BUILD_CONTAINER_PREFIX, '/work/stability-linux-collector-build-20260915-2')
        self.assertEqual(len(record['compiler_dependencies']), 179)
        self.assertEqual(record['status'], 'PASS_LINUX_COLLECTOR_REBUILD_SHA9_BUILDER_NEGATIVE_ONLY')
        self.assertNotIn('source_review', record)
        self.assertEqual(record['helper']['sha256'], '6ae0e29dbebf2593f91b4cfa19a5252a157241b83715b2243826cf528efca0e2')
        self.assertEqual(record['loader_dependencies'], module.BUILD_LOADER_DEPENDENCIES)
        self.assertEqual(module.mapped('/work/stability-linux-collector-build-20260915-2/linux-collector'),
                         module.BUILD / 'linux-collector')

    def test_rebuild_owner_rejects_stale_or_hostile_records(self):
        record = self._rebuild_record()
        mutations = []
        stale = copy.deepcopy(record)
        stale['status'] = 'PASS_LINUX_COLLECTOR_BUILD_SHA9_BUILDER_NEGATIVE_ONLY'
        mutations.append(stale)
        stale = copy.deepcopy(record)
        stale['compiler_dependencies'].pop()
        mutations.append(stale)
        hostile = copy.deepcopy(record)
        hostile['loader_dependencies'][0]['sha256'] = 'f' * 64
        mutations.append(hostile)
        hostile = copy.deepcopy(record)
        hostile['source_review'] = {'path': '/workspace/old-review.json'}
        mutations.append(hostile)
        hostile = copy.deepcopy(record)
        hostile['helper']['path'] = '/work/hostile.py'
        mutations.append(hostile)
        for candidate in mutations:
            with self.subTest(candidate=candidate):
                with self.assertRaises(ValueError):
                    module.validate_build_record_schema(candidate)

    def test_failed_then_successful_retry_records_first_failure(self):
        outcomes = iter(({'absence_verified': False, 'errors': ['remove failed']},
                         {'absence_verified': True, 'errors': []}))
        with mock.patch.object(module, 'cleanup', side_effect=outcomes):
            journal = []
            result = module.recover_cleanup(mock.Mock(), {}, 'test', max_passes=3,
                                            sleeper=lambda _: None, journal=journal.append)
        self.assertEqual(result['state'], 'ABSENCE_VERIFIED')
        self.assertEqual(len(result['attempts']), 2)
        self.assertEqual(result['first_failure']['reason'], 'remove failed')
        self.assertTrue(result['recovery_owner']['pid'])
        self.assertEqual(len(journal), 2)

    def test_exhausted_passes_retain_recovery(self):
        with mock.patch.object(module, 'cleanup', return_value={'absence_verified': False,
                                                                  'errors': ['lookup failed']}):
            result = module.recover_cleanup(mock.Mock(), {}, 'test', max_passes=2,
                                            sleeper=lambda _: None)
        self.assertEqual(result['state'], 'RECOVERING')
        self.assertFalse(result['absence_verified'])
        self.assertEqual(len(result['attempts']), 2)

    def test_exception_is_recorded_and_retried(self):
        with mock.patch.object(module, 'cleanup', side_effect=[RuntimeError('EOF'),
                                                                  {'absence_verified': True}]):
            result = module.recover_cleanup(mock.Mock(), {}, 'test', max_passes=2,
                                            sleeper=lambda _: None)
        self.assertEqual(result['first_failure']['reason'], 'EOF')
        self.assertTrue(result['absence_verified'])

    def test_flock_denied_until_recovery_verified(self):
        with tempfile.NamedTemporaryFile() as lock:
            fd = os.open(lock.name, os.O_RDWR)
            fcntl.flock(fd, fcntl.LOCK_EX)
            probe = subprocess.run([module.PYTHON, '-c',
                'import fcntl,sys; f=open(sys.argv[1],"r+");\n'
                'try: fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB); print("acquired")\n'
                'except BlockingIOError: print("denied")', lock.name], capture_output=True, text=True)
            self.assertEqual(probe.stdout.strip(), 'denied')
            self.assertFalse(module.release_lock_allowed({'absence_verified': False}, 0))
            fcntl.flock(fd, fcntl.LOCK_UN)
            probe = subprocess.run([module.PYTHON, '-c',
                'import fcntl,sys; f=open(sys.argv[1],"r+"); fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB); print("acquired")', lock.name], capture_output=True, text=True)
            self.assertEqual(probe.stdout.strip(), 'acquired')
            self.assertTrue(module.release_lock_allowed({'absence_verified': True}, 0))

    def test_unique_exclusive_recovery_journals(self):
        with tempfile.TemporaryDirectory() as directory:
            host = Path(directory)
            state = {'attempts': [{'number': 1}]}
            module.recovery_journal(host, 'owner', state)
            state['attempts'].append({'number': 2})
            module.recovery_journal(host, 'owner', state)
            self.assertEqual(sorted(p.name for p in host.iterdir()),
                             ['owner-recovery-001.json', 'owner-recovery-002.json'])
            self.assertEqual(json.loads((host / 'owner-recovery-001.json').read_text()),
                             {'attempts': [{'number': 1}]})
            with self.assertRaises(FileExistsError):
                module.recovery_journal(host, 'owner', {'attempts': [{'number': 1}]})

    def test_recovery_continues_after_repeated_journal_failures(self):
        outcomes = iter(({'absence_verified': False, 'errors': ['lookup failed']},
                         {'absence_verified': False, 'errors': ['remove failed']},
                         {'absence_verified': True, 'errors': []}))
        journal = mock.Mock(side_effect=RuntimeError('journal unavailable'))
        with mock.patch.object(module, 'cleanup', side_effect=outcomes):
            result = module.recover_cleanup(mock.Mock(), {}, 'test', max_passes=3,
                                            sleeper=lambda _: None, journal=journal)
        self.assertTrue(result['absence_verified'])
        self.assertEqual(len(result['attempts']), 3)
        self.assertEqual(result['first_failure']['reason'], 'lookup failed')
        self.assertEqual(journal.call_count, 3)

    def test_verified_cleanup_with_journal_failure_is_not_evidence_complete(self):
        journal = mock.Mock(side_effect=RuntimeError('ENOSPC'))
        with mock.patch.object(module, 'cleanup', return_value={'absence_verified': True, 'errors': []}):
            result = module.recover_cleanup(mock.Mock(), {}, 'test', max_passes=1,
                                            sleeper=lambda _: None, journal=journal)
        self.assertTrue(result['absence_verified'])
        self.assertFalse(result['evidence_complete'])
        self.assertEqual(result['journal_error_count'], 1)
        self.assertEqual(result['journal_errors'][0]['message'], 'ENOSPC')
        self.assertTrue(module.release_lock_allowed(result, 0))
        self.assertFalse(result['evidence_complete'] and module.release_lock_allowed(result, 0))

    def test_safe_first_failure_contains_diagnostic_error(self):
        sink = []
        with mock.patch.object(module, 'first_failure', side_effect=OSError('ENOSPC')):
            module.safe_first_failure(Path('/unwritable'), 'diagnostic', RuntimeError('original'), sink)
        self.assertEqual(sink[0]['type'], 'OSError')
        self.assertEqual(sink[0]['message'], 'ENOSPC')

    def test_parent_status_guard_rejects_incomplete_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            host = Path(directory)
            result = {'collected_infrastructure_candidate': True, 'diagnostic_errors': [],
                      'watchdog_raw_wait_status': 0,
                      'cleanup': {'absence_verified': True, 'evidence_complete': True,
                                  'first_failure': {'attempt': 1, 'reason': 'transient'}}}
            self.assertFalse(module.infrastructure_pass_allowed(result, host))
            result['cleanup']['first_failure'] = None
            self.assertTrue(module.infrastructure_pass_allowed(result, host))

    def test_journal_error_memory_is_bounded(self):
        journal = mock.Mock(side_effect=OSError('EIO' * 1000))
        with mock.patch.object(module, 'cleanup', return_value={'absence_verified': False,
                                                                  'errors': ['still present']}):
            result = module.recover_cleanup(mock.Mock(), {}, 'test', max_passes=70,
                                            sleeper=lambda _: None, journal=journal)
        self.assertEqual(result['journal_error_count'], 70)
        self.assertEqual(len(result['journal_errors']), 64)
        self.assertTrue(all(len(row['message']) == 1024 for row in result['journal_errors']))
        self.assertEqual(len(result['attempts']), 64)

    def test_commands_budget_is_fresh_each_pass(self):
        commands = mock.Mock(number=95)
        seen = []
        def pass_result(*_):
            seen.append(commands.number)
            commands.number += 95
            return {'absence_verified': len(seen) == 2, 'errors': []}
        with mock.patch.object(module, 'cleanup', side_effect=pass_result):
            result = module.recover_cleanup(commands, {}, 'test', max_passes=2,
                                            sleeper=lambda _: None)
        self.assertTrue(result['absence_verified'])
        self.assertEqual(seen, [0, 0])

    def test_recovery_subprocess_retains_flock_until_verified(self):
        with tempfile.NamedTemporaryFile() as lock:
            ready_r, ready_w = os.pipe()
            control_r, control_w = os.pipe()
            lock_fd = os.open(lock.name, os.O_RDWR)
            fcntl.flock(lock_fd, fcntl.LOCK_EX)
            owner = os.fork()
            if owner == 0:
                try:
                    os.close(ready_r); os.close(control_w)
                    passes = []
                    def actual_recovery_pass(*_):
                        passes.append(len(passes) + 1)
                        if len(passes) == 1:
                            os.write(ready_w, b'ready')
                            return {'absence_verified': False, 'errors': ['container remains']}
                        return {'absence_verified': True, 'errors': []}
                    def controlled_backoff(_):
                        os.read(control_r, 1)
                    module.first_failure = mock.Mock(side_effect=OSError('ENOSPC'))
                    diagnostic_errors = []
                    module.safe_first_failure(Path('/unused'), 'parent-disappeared',
                                              RuntimeError('control EOF'), diagnostic_errors)
                    with mock.patch.object(module, 'cleanup', side_effect=actual_recovery_pass):
                        result = module.recover_cleanup(mock.Mock(), {}, 'inherited-owner',
                                                        max_passes=2,
                                                        sleeper=controlled_backoff)
                    good = (result['absence_verified'] is True and passes == [1, 2] and
                            diagnostic_errors[0]['type'] == 'OSError')
                    # The inherited descriptor is closed only after the actual
                    # RecoveryOwner has verified absence; process exit is the
                    # ownership transfer, with no hand-written unlock.
                    os.close(lock_fd)
                    os._exit(0 if good else 2)
                except BaseException:
                    os._exit(3)
            os.close(ready_w); os.close(control_r); os.close(lock_fd)
            try:
                self.assertEqual(os.read(ready_r, 5), b'ready')
                probe = subprocess.run([module.PYTHON, '-c',
                    'import fcntl,sys; f=open(sys.argv[1],"r+");\n'
                    'try: fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB); print("acquired")\n'
                    'except BlockingIOError: print("denied")', lock.name], capture_output=True, text=True)
                self.assertEqual(probe.stdout.strip(), 'denied')
                os.write(control_w, b'1')
                waited, raw = os.waitpid(owner, 0)
                self.assertEqual(waited, owner)
                self.assertEqual(raw, 0)
                probe = subprocess.run([module.PYTHON, '-c',
                    'import fcntl,sys; f=open(sys.argv[1],"r+"); fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB); print("acquired")', lock.name], capture_output=True, text=True)
                self.assertEqual(probe.stdout.strip(), 'acquired')
            finally:
                os.close(ready_r); os.close(control_w)


if __name__ == '__main__':
    unittest.main()
