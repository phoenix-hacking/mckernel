"""Focused authority1 adaptation checks reusing the reviewed scratch21 fault tests."""
import hashlib
import importlib.util
import os
from pathlib import Path
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / 'scripts/native_exact_scratch22_authority1_terminal_cleanup.py'
BASELINE_TESTS = ROOT / 'scripts/tests/test_native_exact_scratch21_terminal_cleanup.py'
BASELINE_TESTS_SHA = 'e1467625cfcc848c7834e23c6bff26a535b40115a0d85bb512f488bf8fcb7d90'


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


if hashlib.sha256(BASELINE_TESTS.read_bytes()).hexdigest() != BASELINE_TESTS_SHA:
    raise RuntimeError('reviewed scratch21 test baseline changed')
baseline = load(BASELINE_TESTS, 'authority1_reviewed_fault_fixture')
baseline.SOURCE = SOURCE
baseline_set_up = baseline.CleanupTests.setUp


def authority1_fixture(case):
    baseline_set_up(case)
    m = case.m
    # All identities here belong solely to the disposable fixture, never a live
    # container/request. The production module starts with every runtime ID None.
    m.CONTAINER = 'a' * 64
    m.CONTAINER_NAME = 'disposable-authority1'
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


baseline.CleanupTests.setUp = authority1_fixture


class Authority1CleanupTests(unittest.TestCase):
    def setUp(self):
        self.case = baseline.CleanupTests()
        self.case.setUp()
        self.addCleanup(self.case.doCleanups)
        self.m = self.case.m

    def test_fresh_namespace_and_no_runtime_identity_fallback(self):
        m = load(SOURCE, 'authority1_unconfigured')
        for key in ('CONTAINER', 'CONTAINER_NAME', 'OWNER_NONCE', 'OWNER_PID',
                    'OWNER_START', 'EXPECTED_EXIT', 'TERMINAL_SHA', 'TERMINAL_INODE',
                    'TERMINAL_SIZE', 'BOOT_ID', 'DEVICE', 'RELEASE'):
            self.assertIsNone(getattr(m, key), key)
        self.assertEqual(m.REQUEST.name, 'native-exact-build-request-scratch-22-authority1.execution.json')
        self.assertEqual(m.LEASE.name, 'native-exact-build-lease-scratch-22-authority1.json')
        for path in (m.CANDIDATE, m.OUTPUT, m.EVIDENCE, m.MUTEX, m.PLAN, m.JOURNAL, m.CAPTURE):
            self.assertIn('22-authority1', path.name)
        self.assertEqual(m.ATTEMPT.name, 'native-exact-candidate-operational-exclusion-scratch18.json')
        self.assertEqual(m.SHARED.name, 'mckernel-heavy-operation.lock')
        with mock.patch.object(m.os, 'open') as opened:
            with self.assertRaisesRegex(m.Refusal, 'release-not-configured'):
                m.recover()
        opened.assert_not_called()

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

    def test_reviewed_real_child_broken_stdout_and_writer_failure(self):
        self.case.test_actual_child_broken_pipe_and_writer_failure_cannot_release_lock()

    def test_reviewed_real_child_termination_before_mutation(self):
        self.case.test_actual_child_termination_is_deferred_before_first_mutation()

    def test_reviewed_real_child_termination_during_evidence(self):
        self.case.test_actual_child_termination_during_failed_quarantine_evidence_keeps_lock()


if __name__ == '__main__':
    unittest.main()
