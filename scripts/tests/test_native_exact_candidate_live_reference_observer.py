#!/usr/bin/env python3
"""Pure unit coverage for live-reference observer procfs/mount semantics."""
import importlib.util
import unittest
from pathlib import Path


SOURCE = (Path(__file__).resolve().parents[2] / 'docs/verification/evidence/'
          'native-exact-candidate-live-reference-observer-68cf089a-1.py')
SPEC = importlib.util.spec_from_file_location('native_exact_observer', SOURCE)
OBSERVER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(OBSERVER)


def row(mount_id, device='0:26', root='/', mountpoint='/dev/shm', filesystem='tmpfs'):
    return {'mount_id': str(mount_id), 'device': device, 'root': root,
            'mountpoint': mountpoint, 'filesystem': filesystem}


TARGETS = [{'path': '/dev/shm/candidate', 'device': '0:26', 'filesystem_root': '/candidate'}]
REFERENCE = row(1)


class MountProofTests(unittest.TestCase):
    def test_positive_canonical_namespace(self):
        bad, canonical_id, complete = OBSERVER.mount_proof([row(9)], TARGETS, REFERENCE)
        self.assertEqual((bad, canonical_id, complete), ([], '9', True))

    def test_isolated_namespace_without_canonical_mount_is_safe(self):
        bad, canonical_id, complete = OBSERVER.mount_proof([], TARGETS, REFERENCE)
        self.assertEqual((bad, canonical_id, complete), ([], None, True))

    def test_ambiguous_canonical_mount_is_rejected(self):
        bad, canonical_id, complete = OBSERVER.mount_proof([row(9), row(10)], TARGETS, REFERENCE)
        self.assertIsNone(canonical_id)
        self.assertFalse(complete)
        self.assertEqual(bad[0]['kind'], 'ambiguous-canonical-dev-shm')

    def test_real_target_alias_is_rejected_without_canonical_mount(self):
        alias = row(11, root='/candidate', mountpoint='/private', filesystem='tmpfs')
        bad, _canonical_id, _complete = OBSERVER.mount_proof([alias], TARGETS, REFERENCE)
        self.assertEqual(bad[0]['kind'], 'tmpfs-target-alias-or-bind')

    def test_foreign_filesystem_mount_below_target_is_rejected(self):
        nested = row(12, device='8:1', root='/', mountpoint='/dev/shm/candidate/sub', filesystem='ext4')
        bad, _canonical_id, _complete = OBSERVER.mount_proof([nested], TARGETS, REFERENCE)
        self.assertEqual(bad[0]['kind'], 'mountpoint-on-or-below-target')

    def test_same_device_ancestor_view_is_rejected(self):
        ancestor = row(13, root='/', mountpoint='/private', filesystem='tmpfs')
        bad, _canonical_id, _complete = OBSERVER.mount_proof([ancestor], TARGETS, REFERENCE)
        self.assertEqual(bad[0]['kind'], 'tmpfs-target-alias-or-bind')


class ProcfsAbsenceTests(unittest.TestCase):
    def test_vanished_individual_entries_are_safe_but_mountinfo_is_not(self):
        self.assertTrue(OBSERVER.safe_proc_absence('fd/17'))
        self.assertTrue(OBSERVER.safe_proc_absence('map_files/1000-2000'))
        self.assertTrue(OBSERVER.safe_proc_absence('map_files'))
        self.assertFalse(OBSERVER.safe_proc_absence('mountinfo'))

    def test_post_scan_exit_cannot_complete_a_final_pass_streak(self):
        who = (41, 42, '99')
        current = {who}
        proofs = [{'identity': who, 'complete': True}]
        churn = []
        complete, clean = OBSERVER.finish_round(current, set(), [], [], churn, proofs)
        self.assertFalse(complete)
        self.assertFalse(clean)
        self.assertEqual(churn[0]['field'], 'end-of-round')
        self.assertEqual(OBSERVER.advance_streak(current, current, clean, 1), 0)

    def test_unchanged_fully_proven_round_advances_streak(self):
        who = (41, 42, '99')
        current = {who}
        complete, clean = OBSERVER.finish_round(
            current, current, [], [], [], [{'identity': who, 'complete': True}])
        self.assertTrue(complete)
        self.assertTrue(clean)
        self.assertEqual(OBSERVER.advance_streak(current, current, clean, 1), 2)

    def test_reference_denial_or_incomplete_proof_keeps_round_unclean(self):
        who = (41, 42, '99')
        current = {who}
        for refs, denials, complete in (([{'field': 'fd/7'}], [], True),
                                        ([], [{'field': 'fd'}], True),
                                        ([], [], False)):
            proof = [{'identity': who, 'complete': complete}]
            proof_complete, clean = OBSERVER.finish_round(
                current, current, refs, denials, [], proof)
            self.assertEqual(proof_complete, complete)
            self.assertFalse(clean)


if __name__ == '__main__':
    unittest.main()
