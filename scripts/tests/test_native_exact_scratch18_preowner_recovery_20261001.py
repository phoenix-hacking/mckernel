"""Actual local filesystem/crash tests; no sudo, Docker, production or guest."""
import errno
import importlib.util
import json
import os
from pathlib import Path
import stat
import tempfile
import types
import copy
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / 'docs/verification/evidence/native-exact-scratch18-preowner-recovery-20261001.py'


def load():
    spec = importlib.util.spec_from_file_location('scratch18_preowner', SOURCE)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class Recovery(unittest.TestCase):
    def setUp(self):
        self.m = load()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / 'scratch'
        self.root.mkdir(mode=0o700)
        self.attempt = self.root / 'attempt.json'
        self.shared = self.root / 'shared.lock'
        self.attempt.write_bytes(b'attempt-retained\n')
        self.shared.write_bytes(b'shared-retained\n')
        def record(path):
            path.chmod(0o600)
            st = path.stat()
            return {'path': str(path), 'device': st.st_dev, 'inode': st.st_ino,
                    'sha256': self.m.sha(path.read_bytes()), 'mode': '0600',
                    'uid': st.st_uid, 'gid': st.st_gid}
        self.failure = {'retained_locks': {'attempt': record(self.attempt), 'shared': record(self.shared)}}
        self.device = self.root.stat().st_dev
        self.archive = self.root / self.m.ARCHIVE
        self.observe = mock.Mock(return_value={'fresh': True})

    def tearDown(self):
        self.tmp.cleanup()

    def recover(self, execute=True):
        return self.m._recover(self.failure, self.root, self.device, self.observe, execute)

    def fork_run(self, action, code=0):
        pid = os.fork()
        if pid == 0:
            try:
                action()
            except BaseException:
                os._exit(99)
            os._exit(0)
        _, status = os.waitpid(pid, 0)
        self.assertEqual(os.waitstatus_to_exitcode(status), code)
        return pid

    def crash(self, point):
        def child():
            rename = self.m._rename_noreplace
            journal = self.m._Transaction.journal
            count = [0]
            def crash_rename(*args):
                count[0] += 1
                rename(*args)
                if point == 'rename' + str(count[0]):
                    os._exit(73)
            def crash_journal(tx, plan, events, event, **fields):
                journal(tx, plan, events, event, **fields)
                if point == 'before' + str(fields.get('move')) and event == 'before':
                    os._exit(73)
                if point == 'after' + str(fields.get('move')) and event == 'after':
                    os._exit(73)
            with mock.patch.object(self.m, '_rename_noreplace', side_effect=crash_rename), \
                    mock.patch.object(self.m._Transaction, 'journal', crash_journal):
                self.recover()
        self.fork_run(child, 73)

    def test_validate_only_does_not_create_recovery_metadata(self):
        self.assertEqual(self.recover(False)['status'], 'PASS_VALIDATE_ONLY')
        self.assertEqual(sorted(p.name for p in self.root.iterdir()), ['attempt.json', 'shared.lock'])

    def test_success_exact_inodes_and_durable_plan(self):
        result = self.recover()
        self.assertEqual(result['status'], 'PASS')
        self.assertEqual(self.observe.call_count, 4)
        self.assertFalse(self.attempt.exists())
        self.assertFalse(self.shared.exists())
        for label in ('attempt', 'shared'):
            rec = self.failure['retained_locks'][label]
            path = self.archive / (label + '.archive')
            self.assertEqual(path.stat().st_ino, rec['inode'])
            self.assertEqual(self.m.sha(path.read_bytes()), rec['sha256'])
        plan = json.loads((self.archive / self.m.PLAN).read_text())
        self.assertEqual(plan['moves'][0]['destination'], 'attempt.archive')
        self.assertEqual(plan['moves'][1]['destination'], 'shared.archive')
        self.assertEqual(plan['root_identity']['device'], self.device)
        events = [json.loads(x) for x in (self.archive / self.m.JOURNAL).read_text().splitlines()]
        self.assertEqual([x['event'] for x in events], ['owner', 'reconciled', 'before', 'after', 'before', 'after', 'complete'])

    def test_real_crashes_before_after_both_renames_resume_and_finalize(self):
        # Each subtest owns fresh files and a real child that dies at the point.
        for point in ('before0', 'rename1', 'after0', 'before1', 'rename2', 'after1'):
            with self.subTest(point=point):
                if point != 'before0':
                    self.tearDown()
                    self.setUp()
                self.crash(point)
                expected_state = 0 if point == 'before0' else 2 if point in ('rename2', 'after1') else 1
                self.assertEqual(int(not self.attempt.exists()) + int(not self.shared.exists()), expected_state)
                self.assertEqual(self.recover()['status'], 'PASS')
                events = [json.loads(x) for x in (self.archive / self.m.JOURNAL).read_text().splitlines()]
                self.assertIn(expected_state, [x['state'] for x in events if x['event'] == 'reconciled'])
                self.assertEqual(events[-1]['event'], 'complete')

    def test_resume_rejects_changed_plan(self):
        self.crash('rename1')
        plan = self.archive / self.m.PLAN
        raw = plan.read_bytes()
        plan.write_bytes(raw.replace(b'attempt.archive', b'wrong.archive'))
        with self.assertRaisesRegex(self.m.Refusal, 'plan-binding'):
            self.recover()
        self.assertTrue(self.shared.exists())

    def test_resume_rejects_missing_or_replaced_archive(self):
        self.crash('rename1')
        (self.archive / 'attempt.archive').write_bytes(b'wrong')
        with self.assertRaisesRegex(self.m.Refusal, 'artifact-binding'):
            self.recover()
        self.assertTrue(self.shared.exists())

    def test_resume_rejects_source_and_archive_both_present(self):
        self.crash('rename1')
        self.attempt.write_bytes(b'replacement')
        with self.assertRaisesRegex(self.m.Refusal, 'ambiguous-lock-state'):
            self.recover()
        self.assertEqual(self.attempt.read_bytes(), b'replacement')

    def test_reverse_transition_refused(self):
        self.crash('before0')
        os.rename(self.shared, self.archive / 'shared.archive')
        with self.assertRaisesRegex(self.m.Refusal, 'invalid-transition-order'):
            self.recover()
        self.assertTrue(self.attempt.exists())

    def test_live_prior_owner_refused_after_mutex_release(self):
        original = self.m._rename_noreplace
        with mock.patch.object(self.m, '_rename_noreplace', side_effect=OSError(errno.EIO, 'test')):
            with self.assertRaises(OSError):
                self.recover()
        with self.assertRaisesRegex(self.m.Refusal, 'recovery-owner-not-absent'):
            self.recover()
        self.assertTrue(self.attempt.exists())
        self.assertTrue(self.shared.exists())

    def test_mutex_excludes_real_other_process(self):
        tx = self.m._Transaction(self.failure, self.root, self.device)
        try:
            tx.lock()
            def child():
                # Inherited descriptor must close; parent retains flock.
                os.close(tx.mfd)
                try:
                    self.recover()
                except self.m.Refusal as exc:
                    if str(exc) == 'recovery-busy':
                        return
                    raise
                raise AssertionError('concurrent recovery admitted')
            self.fork_run(child)
        finally:
            tx.close()
        self.assertTrue(self.attempt.exists())

    def test_actual_noreplace_collision_preserves_both(self):
        original = self.m._rename_noreplace
        def collide(sfd, source, dfd, dest):
            fd = os.open(dest, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600, dir_fd=dfd)
            os.write(fd, b'competing-destination')
            os.close(fd)
            original(sfd, source, dfd, dest)
        with mock.patch.object(self.m, '_rename_noreplace', side_effect=collide):
            with self.assertRaises(FileExistsError):
                self.recover()
        self.assertTrue(self.attempt.exists())
        self.assertTrue(self.shared.exists())
        self.assertEqual((self.archive / 'attempt.archive').read_bytes(), b'competing-destination')

    def test_source_replaced_before_transition_refused(self):
        calls = [0]
        def observe(*args):
            calls[0] += 1
            if calls[0] == 3:
                self.attempt.write_bytes(b'changed')
        self.observe.side_effect = observe
        with self.assertRaisesRegex(self.m.Refusal, 'artifact-binding'):
            self.recover()
        self.assertTrue(self.shared.exists())
        self.assertFalse((self.archive / 'attempt.archive').exists())

    def test_parent_replacement_does_not_redirect_rename(self):
        calls = [0]
        moved = self.root.with_name('moved')
        def observe(*args):
            calls[0] += 1
            if calls[0] == 3:
                self.root.rename(moved)
                self.root.mkdir(mode=0o700)
                (self.root / 'attempt.json').write_bytes(b'decoy')
        self.observe.side_effect = observe
        with self.assertRaisesRegex(self.m.Refusal, 'scratch-parent-replaced'):
            self.recover()
        self.assertEqual((self.root / 'attempt.json').read_bytes(), b'decoy')
        self.assertTrue((moved / 'attempt.json').exists())

    def test_archive_parent_replacement_refused(self):
        calls = [0]
        def observe(*args):
            calls[0] += 1
            if calls[0] == 3:
                self.archive.rename(self.root / 'moved-archive')
                self.archive.mkdir(mode=0o700)
        self.observe.side_effect = observe
        with self.assertRaisesRegex(self.m.Refusal, 'archive-parent-replaced'):
            self.recover()
        self.assertTrue(self.attempt.exists())

    def test_symlink_hardlink_mode_device_refusal(self):
        for defect in ('symlink', 'hardlink', 'mode', 'device'):
            with self.subTest(defect=defect):
                if defect != 'symlink':
                    self.tearDown()
                    self.setUp()
                if defect == 'symlink':
                    self.attempt.unlink()
                    self.attempt.symlink_to(self.shared)
                elif defect == 'hardlink':
                    os.link(self.attempt, self.root / 'extra')
                elif defect == 'mode':
                    self.attempt.chmod(0o644)
                else:
                    self.device += 1
                with self.assertRaises((self.m.Refusal, OSError)):
                    self.recover()
                self.assertTrue(self.shared.exists())

    def test_observer_failure_mutates_nothing(self):
        self.observe.side_effect = self.m.Refusal('observer-refused')
        with self.assertRaisesRegex(self.m.Refusal, 'observer-refused'):
            self.recover()
        self.assertEqual(sorted(p.name for p in self.root.iterdir()), ['attempt.json', 'shared.lock'])

    def test_short_write_loop_executes_real_writes(self):
        write = os.write
        counts = []
        def short(fd, data):
            counts.append(len(data))
            return write(fd, data[:7])
        with mock.patch.object(self.m.os, 'write', side_effect=short):
            self.assertEqual(self.recover()['status'], 'PASS')
        self.assertGreater(len(counts), 100)
        json.loads((self.archive / self.m.PLAN).read_text())

    def test_zero_write_refuses_before_any_move(self):
        with mock.patch.object(self.m.os, 'write', return_value=0):
            with self.assertRaisesRegex(self.m.Refusal, 'write-no-progress'):
                self.recover()
        self.assertTrue(self.attempt.exists())
        self.assertTrue(self.shared.exists())

    def test_both_parents_fsynced_after_each_real_rename(self):
        fsync = os.fsync
        rename = self.m._rename_noreplace
        events = []
        def sync(fd):
            events.append(('fsync', os.fstat(fd).st_ino))
            return fsync(fd)
        def move(*args):
            result = rename(*args)
            events.append(('rename', args[1]))
            return result
        with mock.patch.object(self.m.os, 'fsync', side_effect=sync), \
                mock.patch.object(self.m, '_rename_noreplace', side_effect=move):
            self.recover()
        expected = [('fsync', self.root.stat().st_ino), ('fsync', self.archive.stat().st_ino)]
        for index, event in enumerate(events):
            if event[0] == 'rename':
                self.assertEqual(events[index + 1:index + 3], expected)

    def test_fsync_failure_after_rename_retains_shared_and_can_resume(self):
        def child():
            fsync = os.fsync
            rename = self.m._rename_noreplace
            moved = [False]
            def move(*args):
                rename(*args)
                moved[0] = True
            def sync(fd):
                if moved[0]:
                    raise OSError(errno.EIO, 'injected fsync failure')
                return fsync(fd)
            with mock.patch.object(self.m, '_rename_noreplace', side_effect=move), \
                    mock.patch.object(self.m.os, 'fsync', side_effect=sync):
                try:
                    self.recover()
                except OSError:
                    return
                raise AssertionError('fsync failure ignored')
        self.fork_run(child)
        self.assertFalse(self.attempt.exists())
        self.assertTrue(self.shared.exists())
        self.assertEqual(self.recover()['status'], 'PASS')

    def test_no_public_sealing_or_observation_injection(self):
        self.assertFalse(hasattr(self.m, 'seal_observations'))
        with self.assertRaises(TypeError):
            self.m.recover(observations={'authenticated': True})

    def test_journal_regression_after_completed_move_refused(self):
        self.crash('after0')
        os.rename(self.archive / 'attempt.archive', self.attempt)
        with self.assertRaisesRegex(self.m.Refusal, 'journal-state-regression'):
            self.recover()
        self.assertTrue(self.shared.exists())

    def completed_snapshot(self):
        return {path.name: (path.stat().st_ino, path.read_bytes())
                for path in self.archive.iterdir()}

    def append_fixture_event(self, event, **fields):
        journal = self.archive / self.m.JOURNAL
        raw = journal.read_bytes()
        rows = [json.loads(line) for line in raw.splitlines()]
        record = dict(fields, event=event, sequence=len(rows),
                      plan_sha256=rows[-1]['plan_sha256'],
                      previous=self.m.sha(self.m.canonical(rows[-1])))
        journal.write_bytes(raw + self.m.canonical(record) + b'\n')

    def test_completed_recovery_execute_replay_refuses_with_owner_absent(self):
        self.fork_run(self.recover)
        before = self.completed_snapshot()
        original = self.m._Transaction.reconcile_journal
        def check_mutex(tx, events, state):
            other = self.m._Transaction(self.failure, self.root, self.device)
            try:
                with self.assertRaisesRegex(self.m.Refusal, 'recovery-busy'):
                    other.lock()
            finally:
                other.close()
            return original(tx, events, state)
        with mock.patch.object(self.m._Transaction, 'reconcile_journal', check_mutex), \
                mock.patch.object(self.m._Transaction, 'journal') as append, \
                mock.patch.object(self.m, '_rename_noreplace') as rename:
            with self.assertRaisesRegex(self.m.Refusal, 'recovery-already-complete'):
                self.recover()
            append.assert_not_called()
            rename.assert_not_called()
        self.assertEqual(self.completed_snapshot(), before)
        self.assertEqual(self.recover(False), {'status': 'PASS_VALIDATE_ONLY', 'state': 2, 'terminal': True})
        self.assertEqual(self.completed_snapshot(), before)

    def test_event_after_complete_refuses_even_with_valid_hash_chain(self):
        self.fork_run(self.recover)
        self.append_fixture_event('owner', owner=self.m._owner())
        before = self.completed_snapshot()
        for execute in (False, True):
            with self.subTest(execute=execute):
                with self.assertRaisesRegex(self.m.Refusal, 'journal-after-complete'):
                    self.recover(execute)
                self.assertEqual(self.completed_snapshot(), before)

    def test_duplicate_complete_refuses_even_with_valid_hash_chain(self):
        self.fork_run(self.recover)
        self.append_fixture_event('complete', state=2)
        before = self.completed_snapshot()
        for execute in (False, True):
            with self.subTest(execute=execute):
                with self.assertRaisesRegex(self.m.Refusal, 'journal-after-complete'):
                    self.recover(execute)
                self.assertEqual(self.completed_snapshot(), before)

    def test_state_two_without_complete_resumes_only_finalization(self):
        self.crash('rename2')
        self.assertEqual(self.recover(False), {'status': 'PASS_VALIDATE_ONLY', 'state': 2, 'terminal': False})
        journal = self.archive / self.m.JOURNAL
        before = [json.loads(line) for line in journal.read_bytes().splitlines()]
        self.assertFalse(any(row['event'] == 'complete' for row in before))
        with mock.patch.object(self.m, '_rename_noreplace', side_effect=AssertionError('must not rename again')):
            self.assertEqual(self.recover()['status'], 'PASS')
        after = [json.loads(line) for line in journal.read_bytes().splitlines()]
        self.assertEqual(after[:len(before)], before)
        self.assertEqual([row['event'] for row in after[len(before):]], ['owner', 'reconciled', 'complete'])
        self.assertEqual(sum(row['event'] == 'complete' for row in after), 1)
        with self.assertRaisesRegex(self.m.Refusal, 'recovery-already-complete'):
            self.recover()

    def test_truncated_journal_refused(self):
        self.crash('before0')
        journal = self.archive / self.m.JOURNAL
        journal.write_bytes(journal.read_bytes()[:-2])
        with self.assertRaisesRegex(self.m.Refusal, 'journal-binding'):
            self.recover()
        self.assertTrue(self.attempt.exists())

    def test_validate_only_checks_live_lock_identity(self):
        self.attempt.write_bytes(b'changed')
        with self.assertRaisesRegex(self.m.Refusal, 'artifact-binding'):
            self.recover(False)


class ProductionConsumer(unittest.TestCase):
    """Real report validator and prepared-file checks; external transports mocked."""
    def setUp(self):
        self.m = load()
        self.wrapper = self.m._module(ROOT / 'scripts/native_rust_exact_disk_build_wrapper.py', self.m.WRAPPER_SHA256)
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.fd = self.m._directory(self.root)
        self.request = {'host_floor': 16 * 2**30, 'scratch_floor': 12 * 2**30}
        self.failure = {'owner_identity': {'pid': 3288332, 'starttime': '107474009', 'current_state': 'absent'},
                        'request': {'path': str(self.root / 'request.json'), 'sha256': 'a' * 64,
                                    'normalized_sha256': 'b' * 64, 'inode': 100, 'mode': '0600', 'uid': os.getuid(), 'gid': os.getgid()},
                        'postflight': {'latest_mckernel_container_before_attempt': {'id': 'c' * 64, 'name': 'retained', 'state': 'exited'}}}
        self.history = types.SimpleNamespace(LEASES=[], EVIDENCE_BINDINGS={'e': ('retained', 'd' * 64)})
        rows = []
        for index in range(7):
            path = self.root / ('native-exact-build-lease-test%d.json' % index)
            path.write_bytes(b'authenticated historical fixture')
            meta = path.stat()
            digest = self.m.sha(path.read_bytes())
            self.history.LEASES.append(('test%d' % index, meta.st_ino, meta.st_size, digest, 100 + index, '123', 'e'))
            rows.append({'path': str(path), 'device': meta.st_dev, 'inode': meta.st_ino,
                         'size': meta.st_size, 'sha256': digest, 'pid': 100 + index,
                         'starttime': '123', 'evidence_sha256': 'd' * 64})
        self.report = {'schema': 'mckernel.heavy-recovery-census.v1', 'status': 'PASS_READ_ONLY',
                       'execution_released': False, 'boot_id': self.m.BOOT_ID,
                       'request': dict(self.failure['request'], device=self.root.stat().st_dev),
                       'processes': [], 'containers': [], 'leases': rows,
                       'resources': {'host_free': 30 * 2**30, 'scratch_free': 20 * 2**30,
                                     'memory_available': 20 * 2**30, 'cpus': [2, 3, 4, 5, 6, 7]}}
        self.runner = mock.Mock(side_effect=self.transport)
        self.patches = [mock.patch.object(self.m, 'ROOT', self.root),
                        mock.patch.object(self.m, '_module', side_effect=lambda path, digest: self.wrapper if path.name.endswith('wrapper.py') else self.history),
                        mock.patch.object(self.m, '_prepared', return_value=self.request),
                        mock.patch.object(self.m, '_starttime', return_value=None),
                        mock.patch.object(self.m, '_read_path', return_value=(b'', None)),
                        mock.patch.object(self.wrapper, '_run_bounded_observer', self.runner)]
        for patch in self.patches:
            patch.start()

    def tearDown(self):
        for patch in reversed(self.patches):
            patch.stop()
        os.close(self.fd)
        self.tmp.cleanup()

    def observe(self):
        return self.m.observe_production(self.failure, self.fd)

    def transport(self, command, *args, **kwargs):
        if '--census-only' in command:
            raw = self.m.canonical(self.report)
        elif 'inspect' in command:
            raw = self.m.canonical({'Id': 'c' * 64, 'Name': '/retained', 'State': {'Status': 'exited'}})
        else:
            raw = b''
        return types.SimpleNamespace(returncode=0, stdout=raw)

    def test_exact_positive_census_command_and_retained_history(self):
        self.assertEqual(self.observe(), self.report)
        command = self.runner.call_args_list[0].args[0]
        self.assertEqual(command, ['/usr/bin/python3', '-I', '-B', str(ROOT / 'scripts/native_rust_exact_disk_build_wrapper.py'),
                                   self.failure['request']['path'], '--census-only', '--request-sha256', 'a' * 64])
        self.assertIn('inspect', self.runner.call_args_list[1].args[0])
        self.assertIn('-a', self.runner.call_args_list[2].args[0])
        self.assertIn('since=' + 'c' * 64, self.runner.call_args_list[2].args[0])
        self.assertEqual(self.m._prepared.call_count, 2)

    def test_binding_and_idle_rejections(self):
        original = copy.deepcopy(self.report)
        changes = [('boot_id', 'c733d83b-wrong'), ('execution_released', True),
                   ('schema', 'wrong'), ('status', 'PASS'), ('processes', [{'pid': 9}]),
                   ('containers', [{'ID': 'e' * 64}]), ('leases', original['leases'][:-1]),
                   ('request', dict(original['request'], inode=99))]
        for key, value in changes:
            with self.subTest(key=key):
                self.report = copy.deepcopy(original)
                self.report[key] = value
                with self.assertRaises((self.m.Refusal, self.wrapper.AdmissionError)):
                    self.observe()

    def test_capacity_floor_and_shape_rejections(self):
        for key in ('host_free', 'scratch_free', 'memory_available', 'cpus'):
            with self.subTest(key=key):
                saved = self.report['resources'][key]
                self.report['resources'][key] = [] if key == 'cpus' else 0
                with self.assertRaises((self.m.Refusal, self.wrapper.AdmissionError)):
                    self.observe()
                self.report['resources'][key] = saved

    def test_live_or_reused_owner_refuses_before_transport(self):
        self.m._starttime.return_value = 'different-start'
        with self.assertRaisesRegex(self.m.Refusal, 'retained-owner-not-absent'):
            self.observe()
        self.runner.assert_not_called()

    def test_unknown_lease_and_container_refuse(self):
        extra = self.root / 'native-exact-build-lease-unexpected.json'
        extra.write_bytes(b'{}')
        with self.assertRaisesRegex(self.m.Refusal, 'lease-set-changed'):
            self.observe()
        extra.unlink()
        self.runner.side_effect = lambda command, *args, **kw: (
            types.SimpleNamespace(returncode=0, stdout=b'{"ID":"new-exited"}\n')
            if 'ps' in command else self.transport(command))
        with self.assertRaisesRegex(self.m.Refusal, 'new-or-unverifiable-container'):
            self.observe()

    def test_missing_or_changed_container_boundary_refused(self):
        for status, raw in ((1, b''), (0, b'{}')):
            with self.subTest(status=status):
                self.runner.side_effect = lambda command, *args, **kw: (
                    types.SimpleNamespace(returncode=status, stdout=raw)
                    if 'inspect' in command else self.transport(command))
                with self.assertRaisesRegex(self.m.Refusal, 'container-boundary'):
                    self.observe()

    def test_census_failures_and_duplicate_json_refused(self):
        for status, payload in ((1, b''), (0, b'{}'), (0, b'{"schema":1,"schema":2}'), (0, b'x' * (self.m.MAX_RECORD + 1))):
            with self.subTest(status=status, size=len(payload)):
                self.runner.side_effect = None
                self.runner.return_value = types.SimpleNamespace(returncode=status, stdout=payload)
                with self.assertRaises(self.m.Refusal):
                    self.observe()


class PreparedArtifacts(unittest.TestCase):
    def setUp(self):
        self.m = load()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.fd = self.m._directory(self.root)
        self.request = {}
        def artifact(name):
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(name.encode())
            return path, self.m.sha(path.read_bytes())
        for key in ('owner_path', 'driver_path', 'provenance_path', 'input_manifest', 'image_receipt', 'ihk_overlay_path'):
            path, digest = artifact(key)
            self.request[key] = str(path)
            self.request['ihk_overlay_sha256' if key == 'ihk_overlay_path' else key + '_sha256'] = digest
        log, logsha = artifact('log')
        terminal, termsha = artifact('terminal')
        result, resultsha = artifact('ihk/test/ihklib/whitebox/src/driver/mckernel/syscall.c')
        self.packet = types.SimpleNamespace(LOG=log, LOG_SHA256=logsha, TERMINAL=terminal,
                                            TERMINAL_SHA256=termsha, IHK=self.root / 'ihk', OVERLAY_RESULT_SHA256=resultsha)
        self.failure = {'postflight': {}, 'packet_sha256': 'f' * 64}
        for label in ('output', 'evidence'):
            path = self.root / label
            path.mkdir()
            self.request[label + '_root'] = str(path)
            self.failure['postflight'][label] = dict(self.m._identity(path.stat()), files=0)
        self.request['lease_path'] = str(self.root / 'lease.json')
        path = self.root / 'request.json'
        path.write_bytes(self.m.canonical(self.request) + b'\n')
        path.chmod(0o600)
        self.failure['request'] = dict(self.m._identity(path.stat()), path=str(path),
                                       sha256=self.m.sha(path.read_bytes()), normalized_sha256=self.m.sha(self.m.canonical(self.request)),
                                       mode='0600', uid=os.getuid(), gid=os.getgid())
        self.patches = [mock.patch.object(self.m, 'ROOT', self.root), mock.patch.object(self.m, '_module', return_value=self.packet)]
        for patch in self.patches:
            patch.start()

    def tearDown(self):
        for patch in reversed(self.patches):
            patch.stop()
        os.close(self.fd)
        self.tmp.cleanup()

    def test_real_prepared_files_positive(self):
        self.assertEqual(self.m._prepared(self.failure, self.fd), self.request)

    def test_artifact_change_refuses(self):
        Path(self.request['owner_path']).write_bytes(b'changed')
        with self.assertRaisesRegex(self.m.Refusal, 'artifact-hash'):
            self.m._prepared(self.failure, self.fd)

    def test_output_nonempty_or_identity_change_refuses(self):
        (self.root / 'output' / 'unexpected').write_bytes(b'changed')
        with self.assertRaisesRegex(self.m.Refusal, 'prepared-directory-changed'):
            self.m._prepared(self.failure, self.fd)

    def test_request_replaced_refuses(self):
        path = self.root / 'request.json'
        raw = path.read_bytes()
        path.rename(self.root / 'original-request')
        path.write_bytes(raw)
        path.chmod(0o600)
        with self.assertRaisesRegex(self.m.Refusal, 'artifact-binding'):
            self.m._prepared(self.failure, self.fd)

    def test_existing_lease_refuses(self):
        Path(self.request['lease_path']).write_bytes(b'{}')
        with self.assertRaisesRegex(self.m.Refusal, 'build-lease-present'):
            self.m._prepared(self.failure, self.fd)


if __name__ == '__main__':
    unittest.main()
