"""Focused authority2 adaptation; disposable files only, no child/live actions."""
import ast
import hashlib
import importlib.util
import os
from pathlib import Path
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / 'scripts/native_exact_scratch22_authority2_terminal_cleanup.py'
BASELINE_TESTS = ROOT / 'scripts/tests/test_native_exact_scratch21_terminal_cleanup.py'
BASELINE_TESTS_SHA = 'e1467625cfcc848c7834e23c6bff26a535b40115a0d85bb512f488bf8fcb7d90'
AUTHORITY1_SOURCE = ROOT / 'scripts/native_exact_scratch22_authority1_terminal_cleanup.py'
AUTHORITY1_SOURCE_SHA = '15b7f9241741ccaff065819ea6847323d6ce47ac1fc69a3ea87fbdbad9b01098'


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


if hashlib.sha256(BASELINE_TESTS.read_bytes()).hexdigest() != BASELINE_TESTS_SHA:
    raise RuntimeError('reviewed scratch21 test baseline changed')
baseline = load(BASELINE_TESTS, 'authority2_reviewed_fault_fixture')
baseline.SOURCE = SOURCE
baseline_set_up = baseline.CleanupTests.setUp


def authority2_fixture(case):
    baseline_set_up(case)
    m = case.m
    # All identities here belong solely to the disposable fixture, never a live
    # container/request. The production module starts with every runtime ID None.
    m.CONTAINER = 'a' * 64
    m.CONTAINER_NAME = 'disposable-authority2'
    m.OWNER_NONCE = 'disposable-nonce'
    m.OWNER_PID, m.OWNER_START, m.EXPECTED_EXIT = 99999999, '1', 0
    m.CANDIDATE = m.ROOT / 'candidate'
    m.CANDIDATE.mkdir(mode=0o700)
    artifact = m.OUTPUT / 'mckernel.img'
    artifact.write_bytes(b'disposable successful kernel image')
    artifact.chmod(0o600)
    m.PROTECTED.append(m.observe_identity(artifact))
    m.RELEASE = {'observation': {
        'candidate_root': m.observe_identity(m.CANDIDATE),
        'inventories': {str(path): m.metadata_inventory(path) for path in (m.OUTPUT, m.EVIDENCE)}}}


baseline.CleanupTests.setUp = authority2_fixture


class Authority2CleanupTests(unittest.TestCase):
    def setUp(self):
        self.case = baseline.CleanupTests()
        self.case.setUp()
        self.addCleanup(self.case.doCleanups)
        self.m = self.case.m

    def test_fresh_namespace_and_no_runtime_identity_fallback(self):
        m = load(SOURCE, 'authority2_unconfigured')
        for key in ('CONTAINER', 'CONTAINER_NAME', 'OWNER_NONCE', 'OWNER_PID',
                    'OWNER_START', 'EXPECTED_EXIT', 'TERMINAL_SHA', 'TERMINAL_INODE',
                    'TERMINAL_SIZE', 'BOOT_ID', 'DEVICE', 'RELEASE'):
            self.assertIsNone(getattr(m, key), key)
        self.assertEqual(m.REQUEST.name, 'native-exact-build-request-scratch-22-authority2.execution.json')
        self.assertEqual(m.LEASE.name, 'native-exact-build-lease-scratch-22-authority2.json')
        for path in (m.CANDIDATE, m.OUTPUT, m.EVIDENCE, m.MUTEX, m.PLAN, m.JOURNAL, m.CAPTURE):
            self.assertIn('22-authority2', path.name)
        self.assertEqual(m.ATTEMPT.name, 'native-exact-candidate-operational-exclusion-scratch18.json')
        self.assertEqual(m.SHARED.name, 'mckernel-heavy-operation.lock')
        with mock.patch.object(m.os, 'open') as opened:
            with self.assertRaisesRegex(m.Refusal, 'release-not-configured'):
                m.recover()
        opened.assert_not_called()

    def test_fixed_authority2_attempt_and_exact_integer_binding(self):
        m = self.m
        identity = {'path': str(m.REQUEST), 'sha256': m.REQUEST_SHA}
        m.validate_attempt_binding(dict(m.KNOWN_TARGET), identity)
        for key, changed in (('owner_pid', True), ('owner_pid', 244087),
                             ('owner_starttime', 1324045), ('owner_nonce', 'old-attempt'),
                             ('container_id', 'a' * 64), ('exit_code', True), ('exit_code', 0)):
            target = dict(m.KNOWN_TARGET); target[key] = changed
            with self.subTest(key=key, changed=changed), self.assertRaisesRegex(m.Refusal, 'exact-authority2'):
                m.validate_attempt_binding(target, identity)
        for changed in ({'path': str(m.REQUEST), 'sha256': '0' * 64},
                        {'path': '/old-request', 'sha256': m.REQUEST_SHA}):
            with self.assertRaises(m.Refusal): m.validate_attempt_binding(m.KNOWN_TARGET, changed)
        self.assertEqual(m.WAITER_PIDS, (243497,))
        self.assertEqual(m.ROOT_TERMINAL.name, 'native-exact-scratch-22-authority2-heavy-build.terminal.json')

    def test_reviewed_transaction_and_guards_are_mechanically_unchanged(self):
        raw = AUTHORITY1_SOURCE.read_bytes()
        self.assertEqual(hashlib.sha256(raw).hexdigest(), AUTHORITY1_SOURCE_SHA)
        before = ast.parse(raw)
        after = ast.parse(SOURCE.read_text().replace('authority2', 'authority1'))
        wanted = ('Transaction', 'recover', 'quarantine_wait', 'metadata_inventory',
                  'protected_files', 'capture_logs', 'observe_identity', 'validate_process_report',
                  'validate_container_profile', 'census', 'rename_exchange', 'read_bounded', 'read_at')
        def bodies(tree):
            return {node.name: ast.dump(node) for node in tree.body
                    if isinstance(node, (ast.ClassDef, ast.FunctionDef)) and node.name in wanted}
        self.assertEqual(bodies(before), bodies(after))
        self.assertEqual(self.m.PROTECTED_LIMIT, 128 << 20)
        self.assertEqual(self.m.DOCUMENT_LIMIT, 256 << 20)
        self.assertEqual(self.m.INVENTORY_LIMIT, 400000)

    def test_nonempty_successful_output_is_preserved_through_cleanup_and_replay(self):
        before = (self.m.OUTPUT / 'mckernel.img').read_bytes()
        self.case.test_read_only_and_terminal_replay_are_immutable()
        self.assertEqual((self.m.OUTPUT / 'mckernel.img').read_bytes(), before)
        self.assertTrue(self.m.CANDIDATE.is_dir())

    def test_complete_inventory_rejects_added_or_changed_output_without_hashing_whole_tree(self):
        self.m.protected_files()
        extra = self.m.OUTPUT / 'undeclared'
        extra.write_bytes(b'preserve unknown artifact')
        with self.assertRaisesRegex(self.m.Refusal, 'protected-inventory-drift'):
            self.m.protected_files()
        self.assertEqual(extra.read_bytes(), b'preserve unknown artifact')

    def test_selected_image_hash_rejects_same_metadata_inventory_rebinding(self):
        image = self.m.OUTPUT / 'mckernel.img'
        image.write_bytes(b'changed kernel image')
        self.m.RELEASE['observation']['inventories'][str(self.m.OUTPUT)] = self.m.metadata_inventory(self.m.OUTPUT)
        with self.assertRaisesRegex(self.m.Refusal, 'selected-artifact-or-receipt-drift'):
            self.m.protected_files()

    def test_source_root_and_lease_drift_are_fail_closed(self):
        self.m.LEASE.write_bytes(b'uncertain owner')
        with self.assertRaisesRegex(self.m.Refusal, 'request-lease-reappeared'):
            self.m.protected_files()
        self.m.LEASE.unlink()  # Disposable fixture only.
        self.m.CANDIDATE.rename(self.m.ROOT / 'retained-source')
        self.m.CANDIDATE.mkdir(mode=0o700)
        with self.assertRaisesRegex(self.m.Refusal, 'candidate-root-drift'):
            self.m.protected_files()

    def test_unreleased_template_and_missing_future_observation_cannot_execute(self):
        draft = self.m.prepare_release({}, 'f' * 40, 'e' * 40)
        self.assertEqual(draft['status'], 'NOT_RELEASED')
        self.assertEqual(draft['observation'], {})
        with self.assertRaisesRegex(self.m.Refusal, 'cleanup-not-released'):
            self.m.configure(draft, execute=True)
        self.assertIsNone(self.m.RELEASE)

    def test_metadata_inventory_preserves_symlink_target_without_following(self):
        link = self.m.OUTPUT / 'source'
        link.symlink_to(self.m.CANDIDATE, target_is_directory=True)
        rows = self.m.metadata_inventory(self.m.OUTPUT)
        self.assertEqual(rows[-1]['target'], str(self.m.CANDIDATE))
        self.assertEqual(len(rows), 3)

    def test_reviewed_exchange_and_release_crash_frontiers(self):
        self.case.test_each_durable_and_filesystem_frontier_recovers()

    def test_reviewed_root_lock_and_quarantine_writer_failure(self):
        self.case.test_root_lock_is_held_through_all_mutations_and_quarantine()


class ActualSizeTests(unittest.TestCase):
    def setUp(self):
        self.case = baseline.CleanupTests()
        self.case.setUp()
        self.addCleanup(self.case.doCleanups)
        self.m = self.case.m

    def sparse(self, name, size):
        path = self.m.ROOT / name
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        try:
            os.ftruncate(fd, size)
        finally:
            os.close(fd)
        return path

    def test_actual_owner_receipt_size_streams_hash_in_bounded_chunks(self):
        size = 89341228
        path = self.sparse('actual-size-receipt.json', size)
        expected = hashlib.sha256()
        remaining = size
        zero = bytes(1 << 20)
        while remaining:
            block = zero[:min(len(zero), remaining)]
            expected.update(block)
            remaining -= len(block)
        real_read = os.read
        with mock.patch.object(self.m, 'read_bounded', side_effect=AssertionError('buffered selected receipt')), \
             mock.patch.object(self.m.os, 'read', wraps=real_read) as read:
            row = self.m.observe_identity(path)
        self.assertEqual(row['size'], size)
        self.assertEqual(row['sha256'], expected.hexdigest())
        self.assertLessEqual(max(call.args[1] for call in read.call_args_list), 1 << 20)

    def test_selected_file_over_finite_stream_limit_is_refused_before_read(self):
        path = self.sparse('too-large-selected', self.m.PROTECTED_LIMIT + 1)
        with mock.patch.object(self.m.os, 'read') as read:
            with self.assertRaisesRegex(self.m.Refusal, 'protected-file-size-bound'):
                self.m.observe_identity(path)
        read.assert_not_called()

    def test_observation_documents_exceed_old_limit_but_remain_finitely_bounded(self):
        size = (32 << 20) + 1
        path = self.sparse('large-observation.json', size)
        self.assertEqual(len(self.m.read_bounded(path)), size)
        with path.open('r+b') as stream:
            stream.truncate(self.m.DOCUMENT_LIMIT + 1)
        with mock.patch.object(self.m.os, 'read') as read:
            with self.assertRaisesRegex(self.m.Refusal, 'bounded-file-shape'):
                self.m.read_bounded(path)
        read.assert_not_called()

    def test_complete_inventory_exact_bound_and_overflow_preserve_all_entries(self):
        root = self.m.ROOT / 'bounded-tree'
        root.mkdir()
        for name in ('a', 'b'):
            (root / name).touch()
        with mock.patch.object(self.m, 'INVENTORY_LIMIT', 3):
            self.assertEqual(len(self.m.metadata_inventory(root)), 3)
            (root / 'c').touch()
            with self.assertRaisesRegex(self.m.Refusal, 'protected-inventory-bound'):
                self.m.metadata_inventory(root)
        self.assertEqual({p.name for p in root.iterdir()}, {'a', 'b', 'c'})
        self.assertGreater(self.m.INVENTORY_LIMIT, 286298)

    def test_large_saved_log_capture_replays_without_small_transaction_reader(self):
        payload = b'preserved log\n' * 100000
        (self.m.EVIDENCE / 'container.log').write_bytes(payload)
        self.m.CAPTURE.write_bytes(payload)
        with mock.patch.object(self.m, 'read_at', side_effect=AssertionError('small transaction reader')), \
             mock.patch.object(self.m, 'run_privileged_large', side_effect=AssertionError('Docker invoked')):
            self.m.capture_logs(False, execute=False)
        self.m.CAPTURE.write_bytes(payload + b'drift')
        with self.assertRaisesRegex(self.m.Refusal, 'retained-capture-bytes'):
            self.m.capture_logs(False, execute=False)


if __name__ == '__main__':
    unittest.main()

