#!/usr/bin/env python3
"""Pure and temporary-filesystem regressions for quarantine recovery."""

import hashlib
import importlib.util
import json
import os
import re
import stat
import tarfile
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = ROOT / 'docs/verification/evidence'
HELPER = EVIDENCE / 'native-exact-candidate-quarantine-recover-68cf089a-1.py'
PACKET = EVIDENCE / 'native-exact-candidate-quarantine-recovery-execution-68cf089a-1.sh'
BASIS = EVIDENCE / 'native-exact-candidate-quarantine-recovery-release-basis-68cf089a-1.json'


def load_helper():
    spec = importlib.util.spec_from_file_location('quarantine_recovery_fixture', HELPER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class MemoryJournal:
    def __init__(self):
        self.records = []

    def write(self, phase, fields):
        self.records.append((phase, fields))


class RecoveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_helper()
        cls.basis = json.loads(BASIS.read_text())

    def test_release_state_is_acyclic_and_exact(self):
        self.assertIn(self.basis['status'], ('DRAFT_NOT_RELEASED', 'PASS_ONE_SHOT_QUARANTINE_RECOVERY'))
        if self.basis['status'] == 'DRAFT_NOT_RELEASED':
            self.assertEqual(self.basis['source_checkpoint'], 'UNSET_REQUIRES_RECOVERY_TEMPLATE_CHECKPOINT')
            helper_template = HELPER.read_bytes()
            packet_template = PACKET.read_bytes()
        else:
            self.assertRegex(self.basis['source_checkpoint'], r'^[0-9a-f]{40}$')
            helper_source = HELPER.read_bytes()
            release_match = re.search(rb"(?m)^RELEASE_SHA = '([0-9a-f]{64})'$", helper_source)
            self.assertIsNotNone(release_match)
            helper_template = helper_source[:release_match.start(1)] + (
                b'UNSET-REQUIRES-INDEPENDENT-RECOVERY-RELEASE-SHA256') + helper_source[release_match.end(1):]
            packet_source = PACKET.read_bytes()
            pattern = re.compile(rb'(?m)^FINAL_HELPER_SHA=([0-9a-f]{64}); RELEASE_SHA=([0-9a-f]{64})$')
            packet_template, count = pattern.subn(
                b'FINAL_HELPER_SHA=__REPLACE_WITH_FINAL_RECOVERY_HELPER_SHA256__; '
                b'RELEASE_SHA=__REPLACE_WITH_FINAL_RECOVERY_RELEASE_SHA256__', packet_source)
            self.assertEqual(count, 1)
        self.assertEqual(self.basis['template_helper']['sha256'], hashlib.sha256(helper_template).hexdigest())
        self.assertEqual(self.basis['template_packet']['sha256'], hashlib.sha256(packet_template).hexdigest())
        for field in ('final_helper_sha256', 'final_packet_sha256', 'release_sha256'):
            self.assertNotIn(field, self.basis)

    def archived_old_journal(self):
        archive = EVIDENCE / 'stability-native-exact-cleanup-failure-raw-20260929-1.tar.gz'
        name = 'home/holden/mckernel-work/scratch/native-exact-candidate-delete-68cf089a-1.journal.jsonl'
        with tarfile.open(archive, 'r:gz') as source:
            return source.extractfile(name).read()

    def test_exact_archived_failure_journal_is_accepted(self):
        module = load_helper()
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / 'journal.jsonl'
            path.write_bytes(self.archived_old_journal())
            module.OLD_JOURNAL = path
            self.assertEqual(len(module.validate_failure_journal()), 9)

    def test_changed_failure_phase_is_rejected(self):
        module = load_helper()
        records = [json.loads(line) for line in self.archived_old_journal().splitlines()]
        records[7]['phase'] = 'delete-start'
        data = b''.join((json.dumps(value, sort_keys=True, separators=(',', ':')) + '\n').encode()
                        for value in records)
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / 'journal.jsonl'
            path.write_bytes(data)
            module.OLD_JOURNAL = path
            module.OLD_JOURNAL_SHA = hashlib.sha256(data).hexdigest()
            with self.assertRaisesRegex(RuntimeError, 'phase sequence'):
                module.validate_failure_journal()

    def test_raw_archive_contains_exact_old_lease(self):
        self.module.validate_raw_archive_lease()

    def test_inventory_is_mapped_to_quarantines_and_rebinds_inodes(self):
        module = load_helper()
        with tempfile.TemporaryDirectory() as raw:
            top = Path(raw)
            c, b, qc, qb = (top / name for name in ('c', 'b', 'qc', 'qb'))
            qc.mkdir(mode=0o700); qb.mkdir(mode=0o700)
            (qc / 'file').write_bytes(b'payload')
            (qb / 'link').symlink_to('target')
            (qc / 'file').chmod(0o644)
            dev = os.lstat(qc).st_dev
            rows = [
                {'path': str(c.relative_to('/')), 'type': 'directory', 'mode': '0755', 'sha256': None},
                {'path': str(c.relative_to('/')) + '/file', 'type': 'file', 'mode': '0644',
                 'sha256': hashlib.sha256(b'payload').hexdigest()},
                {'path': str(b.relative_to('/')), 'type': 'directory', 'mode': '0755', 'sha256': None},
                {'path': str(b.relative_to('/')) + '/link', 'type': 'symlink', 'mode': '0777',
                 'sha256': hashlib.sha256(b'target').hexdigest()}]
            inventory = top / 'inventory.json'
            inventory.write_text(json.dumps({'roots': [str(c), str(b)], 'worktree_inventory': rows}))
            module.C, module.B, module.QC, module.QB = c, b, qc, qb
            module.INVENTORY = inventory
            module.INVENTORY_SHA = digest(inventory)
            module.check_quarantine = lambda path, device, inode: None
            module.ROOTS = ((c, qc, dev, os.lstat(qc).st_ino, 2),
                            (b, qb, dev, os.lstat(qb).st_ino, 2))
            result = module.reconstruct_inventory()
            self.assertEqual(len(result), 2)
            self.assertEqual(result[(str(qc), 'file')]['inode'], os.lstat(qc / 'file').st_ino)
            self.assertEqual(result[(str(qb), 'link')]['sha256'], hashlib.sha256(b'target').hexdigest())

    def test_descriptor_delete_hash_checks_and_journals_each_entry(self):
        with tempfile.TemporaryDirectory() as raw:
            module = load_helper()
            root = Path(raw)
            (root / 'd').mkdir(mode=0o755)
            (root / 'd').chmod(0o755)
            (root / 'd' / 'f').write_bytes(b'bytes')
            (root / 'd' / 'f').chmod(0o644)
            file_info = os.lstat(root / 'd' / 'f')
            dir_info = os.lstat(root / 'd')
            expected = {
                'd': {'type': 'directory', 'mode': '0755', 'sha256': None,
                      'dev': dir_info.st_dev, 'inode': dir_info.st_ino},
                'd/f': {'type': 'file', 'mode': '0644', 'sha256': hashlib.sha256(b'bytes').hexdigest(),
                        'dev': file_info.st_dev, 'inode': file_info.st_ino}}
            journal = MemoryJournal()
            fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY)
            try:
                module.delete_verified(fd, expected, '', dir_info.st_dev, journal, 'fixture')
            finally:
                os.close(fd)
            self.assertEqual(os.listdir(root), [])
            self.assertEqual([phase for phase, _ in journal.records], ['delete-entry', 'delete-entry'])
            self.assertEqual([record['operation'] for _, record in journal.records], ['unlink', 'rmdir'])
            self.assertTrue(all(record['validated'] is True for _, record in journal.records))

    def test_wrong_file_digest_stops_before_unlink(self):
        module = load_helper()
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw); path = root / 'f'; path.write_bytes(b'actual'); path.chmod(0o644); info = os.lstat(path)
            expected = {'f': {'type': 'file', 'mode': '0644', 'sha256': hashlib.sha256(b'wrong').hexdigest(),
                              'dev': info.st_dev, 'inode': info.st_ino}}
            fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY)
            journal = MemoryJournal()
            try:
                with self.assertRaisesRegex(RuntimeError, 'content/identity'):
                    module.delete_verified(fd, expected, '', info.st_dev, journal, 'fixture')
            finally:
                os.close(fd)
            self.assertTrue(path.exists())
            self.assertEqual(journal.records, [])

    def test_old_lease_is_descriptor_verified_journaled_then_removed(self):
        module = load_helper()
        with tempfile.TemporaryDirectory() as raw:
            lease = Path(raw) / 'lease.json'
            helper_pid = 99999999
            data = (json.dumps({'schema': 'mckernel.native-exact-candidate-cleanup-lease.v1',
                                'pid': helper_pid,
                                'started_at_utc': '2026-09-29T05:32:34.727836Z'},
                               sort_keys=True, separators=(',', ':')) + '\n').encode()
            lease.write_bytes(data)
            lease.chmod(0o600)
            info = os.lstat(lease)
            module.OLD_LEASE = lease
            module.OLD_LEASE_ID = (info.st_dev, info.st_ino, 0o600, info.st_uid, info.st_gid)
            module.OLD_LEASE_SHA = hashlib.sha256(data).hexdigest()
            module.OLD_HELPER_PID = helper_pid
            journal = MemoryJournal()
            module.remove_old_lease(journal)
            self.assertFalse(lease.exists())
            self.assertEqual([phase for phase, _ in journal.records], ['old-lease-remove-before'])
            self.assertTrue(journal.records[0][1]['validated'])

    def released_fixture(self, directory):
        release = json.loads(json.dumps(self.basis))
        if release['status'] == 'DRAFT_NOT_RELEASED':
            release['status'] = 'PASS_ONE_SHOT_QUARANTINE_RECOVERY'
            release['source_checkpoint'] = '2' * 40
        data = (json.dumps(release, sort_keys=True, separators=(',', ':')) + '\n').encode()
        release_hash = hashlib.sha256(data).hexdigest()
        helper_source = HELPER.read_bytes()
        helper, count = re.subn(
            rb"(?m)^RELEASE_SHA = '(?:UNSET-REQUIRES-INDEPENDENT-RECOVERY-RELEASE-SHA256|[0-9a-f]{64})'$",
            ("RELEASE_SHA = '" + release_hash + "'").encode(), helper_source)
        self.assertEqual(count, 1)
        helper_hash = hashlib.sha256(helper).hexdigest()
        packet, count = re.subn(
            rb'(?m)^FINAL_HELPER_SHA=(?:__REPLACE_WITH_FINAL_RECOVERY_HELPER_SHA256__|[0-9a-f]{64}); RELEASE_SHA=(?:__REPLACE_WITH_FINAL_RECOVERY_RELEASE_SHA256__|[0-9a-f]{64})$',
            ('FINAL_HELPER_SHA=' + helper_hash + '; RELEASE_SHA=' + release_hash).encode(), PACKET.read_bytes())
        self.assertEqual(count, 1)
        paths = {name: directory / name for name in ('release', 'helper', 'packet')}
        paths['release'].write_bytes(data); paths['helper'].write_bytes(helper); paths['packet'].write_bytes(packet)
        module = load_helper(); module.RELEASE = paths['release']; module.RELEASE_SHA = release_hash
        module.PACKET = paths['packet']; module.__file__ = str(paths['helper'])
        return module, release

    def test_release_normalization_accepts_exact_final_join(self):
        with tempfile.TemporaryDirectory() as raw:
            module, release = self.released_fixture(Path(raw))
            self.assertEqual(module.validate_release(), release)

    def test_lease_removal_is_after_all_path_absence_checks(self):
        source = HELPER.read_text()
        absence = source.index('for path in (C, B, QC, QB):')
        remove = source.index('remove_old_lease(journal)', absence)
        unlink = source.index("os.unlink(OLD_LEASE.name, dir_fd=parentfd)")
        journal = source.index("journal.write('old-lease-remove-before'", source.index('def remove_old_lease'))
        terminal = source.index("journal.write('terminal-success'", unlink)
        self.assertLess(absence, remove)
        self.assertLess(journal, unlink)
        self.assertLess(unlink, terminal)


if __name__ == '__main__':
    unittest.main()
