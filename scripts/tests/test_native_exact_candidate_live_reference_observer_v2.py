#!/usr/bin/env python3
"""Synthetic regression coverage for v2 closure semantics only."""
import importlib.util
import os
import shutil
import tempfile
import unittest
from pathlib import Path


SOURCE = (Path(__file__).resolve().parents[2] / 'docs/verification/evidence/'
          'native-exact-candidate-live-reference-observer-68cf089a-2.py')
SPEC = importlib.util.spec_from_file_location('native_exact_observer_v2', SOURCE)
OBSERVER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(OBSERVER)


def row(mount_id, device='0:26', root='/', mountpoint='/dev/shm', filesystem='tmpfs'):
    return {'mount_id': str(mount_id), 'device': device, 'root': root,
            'mountpoint': mountpoint, 'filesystem': filesystem}


TARGETS = [{'path': '/dev/shm/candidate', 'device': '0:26', 'filesystem_root': '/candidate'}]
REFERENCE = row(1)


def success(who):
    return {'identity': who, 'successful': True, 'state': 'same', 'references': [], 'denials': [],
            'incomplete': [], 'expected_absences': [], 'mount_proof': None,
            'field_counts': {key: 0 for key in ('cwd', 'root', 'exe', 'fd', 'map_files', 'mountinfo', 'ns/mnt')}}


class ClosureTests(unittest.TestCase):
    def closure(self, snapshots, scanner):
        values = iter(snapshots)
        return OBSERVER.closure_round(scanner, lambda: next(values))

    def test_stable_clean_round_and_two_round_streak(self):
        who = (41, 42, '99')
        result = self.closure([{who}, {who}], success)
        self.assertTrue(result['clean'])
        self.assertEqual(result['closure_passes'], 1)
        self.assertEqual(OBSERVER.advance_streak(result['clean'], 1), 2)

    def test_exit_only_closure_is_clean(self):
        exited, live = (1, 1, '10'), (2, 2, '20')
        def scanner(who):
            record = success(who)
            if who == exited:
                record.update({'successful': False, 'state': 'exited'})
            return record
        result = self.closure([{exited, live}, {live}, {live}], scanner)
        self.assertTrue(result['clean'])
        self.assertEqual(result['final_live'], {live})
        self.assertEqual(result['successful'], {live})

    def test_unseen_final_appearance_rejects_when_closure_bound_exhausted(self):
        original = (1, 1, '10')
        appearances = [(2, 2, str(n)) for n in range(1, OBSERVER.MAX_CLOSURE_PASSES + 2)]
        snapshots = [{original}]
        snapshots.extend([{original, *appearances[:n]} for n in range(1, OBSERVER.MAX_CLOSURE_PASSES + 1)])
        result = self.closure(snapshots, success)
        self.assertFalse(result['clean'])
        self.assertTrue(result['nonconvergent'])
        self.assertTrue(result['missing_final'])

    def test_reused_identity_rejects_until_replacement_is_scanned_in_later_round(self):
        old, replacement = (7, 7, '100'), (7, 7, '200')
        def replaced(who):
            if who == old:
                record = success(who)
                record.update({'successful': False, 'state': 'reused'})
                return record
            return success(who)
        first = self.closure([{old}, {replacement}, {replacement}], replaced)
        self.assertFalse(first['clean'])
        self.assertEqual(first['successful'], {replacement})
        second = self.closure([{replacement}, {replacement}], success)
        self.assertTrue(second['clean'])

    def test_reference_denial_and_incomplete_each_reset_clean(self):
        who = (41, 42, '99')
        for field in ('references', 'denials', 'incomplete'):
            def scanner(identity, field=field):
                record = success(identity)
                record[field] = [{'identity': identity, 'field': field}]
                return record
            result = self.closure([{who}, {who}], scanner)
            self.assertFalse(result['clean'], field)
            self.assertEqual(OBSERVER.advance_streak(result['clean'], 1), 0)

    def test_bounded_nonconvergence(self):
        who = (1, 1, '1')
        snapshots = [{who}] + [{who, (2, 2, str(n))} for n in range(OBSERVER.MAX_CLOSURE_PASSES)]
        result = self.closure(snapshots, success)
        self.assertFalse(result['clean'])
        self.assertEqual(result['closure_passes'], OBSERVER.MAX_CLOSURE_PASSES)
        self.assertTrue(result['nonconvergent'])


class MountProofTests(unittest.TestCase):
    def test_canonical_and_isolated_namespaces_are_complete(self):
        self.assertEqual(OBSERVER.mount_proof([row(9)], TARGETS, REFERENCE), ([], '9', True))
        self.assertEqual(OBSERVER.mount_proof([], TARGETS, REFERENCE), ([], None, True))

    def test_alias_ambiguous_and_nested_mounts_reject(self):
        alias = row(11, root='/candidate', mountpoint='/private', filesystem='tmpfs')
        nested = row(12, device='8:1', root='/', mountpoint='/dev/shm/candidate/sub', filesystem='ext4')
        ambiguous = [row(9), row(10)]
        self.assertEqual(OBSERVER.mount_proof([alias], TARGETS, REFERENCE)[0][0]['kind'],
                         'tmpfs-target-alias-or-bind')
        self.assertEqual(OBSERVER.mount_proof([nested], TARGETS, REFERENCE)[0][0]['kind'],
                         'mountpoint-on-or-below-target')
        self.assertEqual(OBSERVER.mount_proof(ambiguous, TARGETS, REFERENCE)[0][0]['kind'],
                         'ambiguous-canonical-dev-shm')

    def test_procfs_entry_absence_policy_is_retained(self):
        self.assertTrue(OBSERVER.safe_proc_absence('fd/17'))
        self.assertTrue(OBSERVER.safe_proc_absence('map_files/1000-2000'))
        self.assertFalse(OBSERVER.safe_proc_absence('mountinfo'))


class ScanIdentityProductionPathTests(unittest.TestCase):
    """Exercise scan_identity against a tiny injected procfs-shaped tree."""
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.proc_root = self.root / 'proc'
        self.who = (41, 42, '99')
        self.base = self.proc_root / '41' / 'task' / '42'
        self.base.mkdir(parents=True)
        self.other = self.root / 'other'
        self.other.write_text('other', encoding='ascii')
        self.target = self.root / 'target'
        self.target.write_text('target', encoding='ascii')
        for field in ('cwd', 'root', 'exe'):
            os.symlink(self.other, self.base / field)
        (self.base / 'fd').mkdir()
        (self.base / 'map_files').mkdir()
        (self.base / 'ns').mkdir()
        os.symlink('mnt:[1]', self.base / 'ns' / 'mnt')
        self.target_ids = {(self.target.stat().st_dev, self.target.stat().st_ino)}

    def tearDown(self):
        self.temp.cleanup()

    def scan(self, **kwargs):
        arguments = {'proc_root': self.proc_root, 'identity_reader': lambda _pid, _tid: self.who,
                     'mount_reader': lambda _pid, _tid: [row(9)],
                     'link_reader': os.readlink}
        arguments.update(kwargs)
        return OBSERVER.scan_identity(self.who, TARGETS, REFERENCE, self.target_ids, 900, set(), **arguments)

    def test_stable_scan_succeeds_and_allowed_absences_do_not_make_it_incomplete(self):
        self.assertTrue(self.scan()['successful'])
        (self.base / 'exe').unlink()
        shutil.rmtree(self.base / 'fd')
        shutil.rmtree(self.base / 'map_files')
        result = self.scan()
        self.assertTrue(result['successful'])
        self.assertFalse(result['incomplete'])
        self.assertEqual({item['field'] for item in result['expected_absences']},
                         {'exe', 'fd', 'map_files'})

    def test_exit_and_reuse_during_a_missing_required_field_are_distinguished(self):
        (self.base / 'cwd').unlink()
        calls = {'count': 0}
        def exited(_pid, _tid):
            calls['count'] += 1
            return self.who if calls['count'] == 1 else None
        exit_result = self.scan(identity_reader=exited)
        self.assertEqual(exit_result['state'], 'exited')
        self.assertFalse(exit_result['incomplete'])
        replacement = (41, 42, '100')
        calls['count'] = 0
        def reused(_pid, _tid):
            calls['count'] += 1
            return self.who if calls['count'] == 1 else replacement
        reuse_result = self.scan(identity_reader=reused)
        self.assertEqual(reuse_result['state'], 'reused')
        self.assertFalse(reuse_result['successful'])

    def test_inode_hit_survives_readlink_loss(self):
        os.symlink(self.target, self.base / 'fd' / '7')
        def lost_link(path):
            if path.name == '7':
                raise FileNotFoundError('vanished after stat')
            return os.readlink(path)
        result = self.scan(link_reader=lost_link)
        self.assertFalse(result['successful'])
        self.assertEqual(result['references'][0]['field'], 'fd/7')
        self.assertIsNone(result['references'][0]['link'])
        self.assertIn('link_diagnostic_failure', result['references'][0])

    def test_mount_violation_denial_and_required_missing_each_reject(self):
        alias = row(11, root='/candidate', mountpoint='/private', filesystem='tmpfs')
        self.assertTrue(self.scan(mount_reader=lambda _pid, _tid: [alias])['references'])
        def denied(path):
            if path.name == 'cwd':
                raise PermissionError('synthetic denial')
            return Path.stat(path)
        self.assertTrue(self.scan(stat_reader=denied)['denials'])
        (self.base / 'root').unlink()
        incomplete = self.scan()
        self.assertTrue(incomplete['incomplete'])
        self.assertFalse(incomplete['successful'])


class TreeRevalidationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name) / 'tree'
        self.root.mkdir()
        (self.root / 'child').mkdir()
        (self.root / 'child' / 'one').write_text('one', encoding='ascii')

    def tearDown(self):
        self.temp.cleanup()

    def test_root_and_child_replacement_are_detected(self):
        root_baseline = OBSERVER.tree_baseline(self.root)
        moved = self.root.with_name('tree-old')
        os.rename(self.root, moved)
        self.root.mkdir()
        self.assertEqual(OBSERVER.revalidate_tree(root_baseline)['kind'], 'tree-root-identity-changed')
        shutil.rmtree(self.root)
        os.rename(moved, self.root)
        child_baseline = OBSERVER.tree_baseline(self.root)
        child = self.root / 'child'
        os.rename(child, self.root / 'child-old')
        child.mkdir()
        self.assertEqual(OBSERVER.revalidate_tree(child_baseline)['kind'], 'tree-membership-changed')

    def test_child_open_race_is_retried_after_fstat_identity_check(self):
        changed = {'value': False}
        def opener(path, flags, **kwargs):
            if path == 'child' and not changed['value']:
                changed['value'] = True
                os.rename(self.root / 'child', self.root / 'child-raced')
                (self.root / 'child').mkdir()
            return os.open(path, flags, **kwargs)
        _info, _members, fd, transients = OBSERVER.open_tree(self.root, opener)
        os.close(fd)
        self.assertTrue(changed['value'])
        self.assertEqual(transients[0]['resolution'], 'retry')

    def test_membership_addition_and_removal_are_detected(self):
        baseline = OBSERVER.tree_baseline(self.root)
        added = self.root / 'added'
        added.write_text('new', encoding='ascii')
        self.assertEqual(OBSERVER.revalidate_tree(baseline)['kind'], 'tree-membership-changed')
        added.unlink()
        removable = self.root / 'removable'
        removable.write_text('remove', encoding='ascii')
        removal_baseline = OBSERVER.tree_baseline(self.root)
        removable.unlink()
        self.assertEqual(OBSERVER.revalidate_tree(removal_baseline)['kind'], 'tree-membership-changed')


if __name__ == '__main__':
    unittest.main()
