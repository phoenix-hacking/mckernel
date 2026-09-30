#!/usr/bin/env python3
"""Unprivileged behavioral tests: temporary files and fake procfs only."""
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import signal
import stat
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock


SOURCE = Path(__file__).resolve().parents[2] / 'docs/verification/evidence/native-exact-candidate-live-reference-observer-76ae20b5-1.py'
spec = importlib.util.spec_from_file_location('observer_76ae20b5', SOURCE)
o = importlib.util.module_from_spec(spec)
spec.loader.exec_module(o)
WHO = (300, 301, '123')
MOUNT = {'device': '0:26', 'root': '/', 'mountpoint': '/dev/shm', 'filesystem': 'tmpfs',
         'mount_id': '24', 'parent_id': '1', 'options': 'rw', 'optional_fields': [],
         'source': 'tmpfs', 'super_options': ['rw']}


def baseline():
    roots = []
    for path, identity in zip(o.QUARANTINE, o.ROOT_IDS):
        root_id = identity + (0, 0, stat.S_IFDIR, 0o700)
        members = {root_id, (26, identity[1] + 1, 1000, 1000, stat.S_IFREG, 0o644)}
        roots.append({'path': str(path), 'device_number': identity[0], 'inode': identity[1],
                      'device': '0:26', 'uid': 0, 'gid': 0, 'mode': '0700',
                      'filesystem_root': '/' + path.name, 'tree_root_identity': list(root_id),
                      'tree_member_identities': [list(row) for row in sorted(members)],
                      'tree_inode_count': len(members), 'tree_membership_sha256': o.membership_digest(members),
                      'observer_mount': dict(MOUNT)})
    return {'schema': o.SCHEMA, 'status': 'PASS', 'scan_complete': True, 'boot_id': 'fake-boot',
            'observer_sha256': o.source_hash(), 'roots': roots, 'canonical_dev_shm': dict(MOUNT)}


def clean_record(who):
    return {'identity': who, 'successful': True, 'state': 'same', 'references': [],
            'denials': [], 'incomplete': [], 'expected_absences': []}


class ExactContractTests(unittest.TestCase):
    def test_exact_ordered_paths_and_identity(self):
        for pair in (o.ORIGINAL, o.QUARANTINE):
            self.assertEqual(o.parse_targets(['--target', str(pair[0]), '--target', str(pair[1])]), pair)
        with self.assertRaises(RuntimeError):
            o.parse_targets(['--target', str(o.ORIGINAL[0]), '--target', str(o.QUARANTINE[1])])
        info = SimpleNamespace(st_dev=26, st_ino=58679, st_uid=0, st_gid=0, st_mode=0o40700)
        o.check_target_identity(o.QUARANTINE[0], info, 0)
        for field, value in (('st_dev', 1831), ('st_ino', 1), ('st_uid', 1000), ('st_mode', 0o40755)):
            changed = copy.copy(info)
            setattr(changed, field, value)
            with self.subTest(field=field), self.assertRaises(RuntimeError):
                o.check_target_identity(o.QUARANTINE[0], changed, 0)

    def load(self, data):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'baseline.json'
            raw = json.dumps(data).encode()
            path.write_bytes(raw)
            return o.load_retained_baseline(path, hashlib.sha256(raw).hexdigest(), 'fake-boot')

    def test_baseline_authenticates_full_members_and_both_coordinates(self):
        data, targets, reference, inodes = self.load(baseline())
        self.assertEqual(len(inodes), 4)
        self.assertEqual({row['path'] for row in targets}, set(map(str, o.ORIGINAL + o.QUARANTINE)))
        self.assertEqual(reference, MOUNT)

    def test_baseline_rejects_bad_binding_or_member_set(self):
        changes = (
            lambda data: data.update(boot_id='different'),
            lambda data: data.update(status='FAIL'),
            lambda data: data.update(observer_sha256='0' * 64),
            lambda data: data['roots'][0].update(path=str(o.ORIGINAL[0])),
            lambda data: data['roots'][0].update(inode=999),
            lambda data: data['roots'][0].update(filesystem_root='/wrong'),
            lambda data: data['roots'][0].update(tree_inode_count=1),
            lambda data: data['roots'][0].update(tree_membership_sha256='0' * 64),
            lambda data: data['roots'][0]['tree_member_identities'].append(data['roots'][0]['tree_member_identities'][0]),
            lambda data: data['canonical_dev_shm'].update(device='0:1'),
        )
        for change in changes:
            data = baseline()
            change(data)
            with self.subTest(data=data), self.assertRaises(RuntimeError):
                self.load(data)

    def test_hash_mismatch_symlink_and_duplicate_json_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'baseline'
            path.write_text(json.dumps(baseline()))
            with self.assertRaisesRegex(RuntimeError, 'SHA256 mismatch'):
                o.load_retained_baseline(path, '0' * 64, 'fake-boot')
            link = Path(temp) / 'link'
            link.symlink_to(path)
            with self.assertRaises(OSError):
                o.load_retained_baseline(link, '0' * 64, 'fake-boot')
        with self.assertRaisesRegex(RuntimeError, 'duplicate JSON key'):
            o.exact_json('{"status":"PASS","status":"FAIL"}')

    def test_surviving_path_and_dangling_symlink_are_not_absent(self):
        with tempfile.TemporaryDirectory() as temp:
            missing = Path(temp) / 'missing'
            self.assertEqual(o.absence_failures((missing,)), [])
            missing.symlink_to(Path(temp) / 'nonexistent')
            self.assertEqual(o.absence_failures((missing,))[0]['kind'], 'surviving-or-replaced-path')


class FakeProcTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.proc = Path(self.temp.name)
        self.base = self.proc / '300/task/301'
        self.base.mkdir(parents=True)
        self.unrelated = self.proc / 'unrelated'
        self.unrelated.write_bytes(b'fixture')
        for name in ('cwd', 'root', 'exe'):
            (self.base / name).symlink_to(self.unrelated)
        for name in ('fd', 'map_files', 'ns'):
            (self.base / name).mkdir()
        (self.base / 'fd/3').symlink_to(self.unrelated)
        (self.base / 'map_files/1000-2000').symlink_to(self.unrelated)
        (self.base / 'ns/mnt').symlink_to('mnt:[123]')
        self.targets = baseline()['roots']

    def scan(self, **changes):
        args = dict(proc_root=self.proc, identity_reader=lambda pid, tid: WHO,
                    mount_reader=lambda pid, tid: [MOUNT])
        args.update(changes)
        return o.scan_identity(WHO, self.targets, MOUNT, {(26, 58680)}, 999, set(), **args)

    def test_clean_scan_covers_all_fields(self):
        record = self.scan()
        self.assertTrue(record['successful'])
        self.assertTrue(all(record['field_counts'][field] > 0 for field in
                            ('cwd', 'root', 'exe', 'fd', 'map_files', 'mountinfo', 'ns/mnt')))

    def test_retained_inode_reference_in_each_field_rejects(self):
        for label in ('cwd', 'root', 'exe', 'fd/3', 'map_files/1000-2000'):
            def reader(path):
                if path == self.base / label:
                    return SimpleNamespace(st_dev=26, st_ino=58680)
                return path.stat()
            with self.subTest(label=label):
                record = self.scan(stat_reader=reader)
                self.assertFalse(record['successful'])
                self.assertEqual(record['references'][0]['field'], label)

    def test_permissions_fail_closed(self):
        def denied(path):
            raise PermissionError('fake proc denial')
        record = self.scan(stat_reader=denied)
        self.assertFalse(record['successful'])
        self.assertTrue(record['denials'])

    def test_mount_alias_fails_closed(self):
        alias = dict(MOUNT, mount_id='25', mountpoint='/alias', root=self.targets[0]['filesystem_root'])
        record = self.scan(mount_reader=lambda pid, tid: [MOUNT, alias])
        self.assertFalse(record['successful'])
        self.assertEqual(record['references'][0]['field'], 'mount-violation')

    def test_pid_replacement_is_rejected(self):
        values = iter((WHO, (WHO[0], WHO[1], '456')))
        record = self.scan(identity_reader=lambda pid, tid: next(values))
        self.assertEqual(record['state'], 'reused')
        self.assertFalse(record['successful'])


class PostDeleteTests(unittest.TestCase):
    def round(self, **changes):
        args = dict(scanner=clean_record, snapshot=lambda: {WHO}, absence_reader=lambda: [])
        args.update(changes)
        return o.post_delete_round(1, 'a' * 64, [], MOUNT, {(26, 58680)}, **args)

    def test_clean_round_requires_every_identity(self):
        record = self.round()
        self.assertEqual(record['status'], 'PASS')
        self.assertEqual(record['censuses'], [[list(WHO)], [list(WHO)]])

    def test_exits_and_entry_churn_reject(self):
        snapshots = iter(({WHO}, set()))
        self.assertEqual(self.round(snapshot=lambda: next(snapshots))['status'], 'FAIL')
        def exited(who):
            return dict(clean_record(who), state='exited', successful=False)
        self.assertEqual(self.round(scanner=exited)['status'], 'FAIL')
        def entry_churn(who):
            return dict(clean_record(who), expected_absences=[{'reason': 'per-entry-procfs-absence'}])
        self.assertEqual(self.round(scanner=entry_churn)['status'], 'FAIL')

    def test_survivor_reference_denial_and_replacement_reject(self):
        self.assertEqual(self.round(absence_reader=lambda: [{'path': '/survivor'}])['status'], 'FAIL')
        for field in ('references', 'denials', 'incomplete'):
            def scanner(who):
                return dict(clean_record(who), **{field: [{'field': 'fixture'}]})
            with self.subTest(field=field):
                self.assertEqual(self.round(scanner=scanner)['status'], 'FAIL')
        self.assertEqual(self.round(scanner=lambda who: dict(clean_record(who), state='reused'))['status'], 'FAIL')

    def test_round_output_is_exclusive_and_fsynced(self):
        with tempfile.TemporaryDirectory() as temp:
            fd = os.open(temp, os.O_RDONLY | os.O_DIRECTORY)
            self.addCleanup(os.close, fd)
            record = self.round()
            with mock.patch.object(o.os, 'fsync', wraps=os.fsync) as sync:
                digest = o.publish_round(fd, 'post-delete-scan-1.json', record)
                self.assertEqual(sync.call_count, 2)
            raw = (Path(temp) / 'post-delete-scan-1.json').read_bytes()
            self.assertEqual(digest, hashlib.sha256(raw).hexdigest())
            self.assertEqual(json.loads(raw)['status'], 'PASS')
            with self.assertRaises(FileExistsError):
                o.publish_round(fd, 'post-delete-scan-1.json', record)
            self.assertEqual((Path(temp) / 'post-delete-scan-1.json').read_bytes(), raw)

    def test_signal_is_retained_as_failure_reason(self):
        with self.assertRaisesRegex(InterruptedError, 'signal 15'):
            o.interrupted(signal.SIGTERM, None)

    def run_three(self, directory, outcomes):
        data = baseline()
        fd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY)
        with mock.patch.object(o, 'load_retained_baseline', return_value=(data, [], MOUNT, {(26, 58680)})), \
                mock.patch.object(o, 'open_output_directory', return_value=fd), \
                mock.patch.object(o, 'starttime', return_value='123'), \
                mock.patch.object(o.Path, 'read_text', return_value='fake-boot'), \
                mock.patch.object(o, 'post_delete_round', side_effect=outcomes), \
                mock.patch.object(o, 'emit_progress'):
            return o.observe_post_delete('/unused/baseline', 'a' * 64, directory)

    def test_three_separate_durable_rounds_required(self):
        with tempfile.TemporaryDirectory() as temp:
            outcomes = [dict(self.round(), round=index) for index in range(1, 4)]
            result = self.run_three(temp, outcomes)
            self.assertEqual(result['status'], 'PASS')
            self.assertEqual(len(result['rounds']), 3)
            for index, row in enumerate(result['rounds'], 1):
                raw = (Path(temp) / ('post-delete-scan-%d.json' % index)).read_bytes()
                self.assertEqual(row['sha256'], hashlib.sha256(raw).hexdigest())
                self.assertEqual(json.loads(raw)['observer_starttime'], '123')

    def test_exception_persisted_and_later_rounds_not_started(self):
        with tempfile.TemporaryDirectory() as temp:
            result = self.run_three(temp, [PermissionError('fake denial')])
            self.assertEqual(result['status'], 'FAIL')
            files = list(Path(temp).iterdir())
            self.assertEqual([path.name for path in files], ['post-delete-scan-1.json'])
            self.assertIn('fake denial', json.loads(files[0].read_bytes())['failure'])

    def test_existing_round_rejects_before_any_scan_or_write(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'post-delete-scan-2.json'
            path.write_bytes(b'original evidence')
            with self.assertRaisesRegex(RuntimeError, 'already exists'):
                self.run_three(temp, [])
            self.assertEqual(path.read_bytes(), b'original evidence')


if __name__ == '__main__':
    unittest.main()
