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

    def test_draft_is_acyclic_and_exact(self):
        self.assertEqual(self.basis['status'], 'DRAFT_NOT_RELEASED')
        self.assertEqual(self.basis['source_checkpoint'], 'UNSET_REQUIRES_RECOVERY_TEMPLATE_CHECKPOINT')
        self.assertEqual(self.basis['template_helper']['sha256'], digest(HELPER))
        self.assertEqual(self.basis['template_packet']['sha256'], digest(PACKET))
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
        module = load_helper()
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / 'd').mkdir()
            (root / 'd' / 'f').write_bytes(b'bytes')
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

    def test_wrong_file_digest_stops_before_unlink(self):
        module = load_helper()
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw); path = root / 'f'; path.write_bytes(b'actual'); info = os.lstat(path)
            expected = {'f': {'type': 'file', 'mode': '0644', 'sha256': hashlib.sha256(b'wrong').hexdigest(),
                              'dev': info.st_dev, 'inode': info.st_ino}}
            fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY)
            try:
                with self.assertRaisesRegex(RuntimeError, 'content/identity'):
                    module.delete_verified(fd, expected, '', info.st_dev, MemoryJournal(), 'fixture')
            finally:
                os.close(fd)
            self.assertTrue(path.exists())

    def released_fixture(self, directory):
        release = json.loads(json.dumps(self.basis))
        release['status'] = 'PASS_ONE_SHOT_QUARANTINE_RECOVERY'
        release['source_checkpoint'] = '2' * 40
        data = (json.dumps(release, sort_keys=True, separators=(',', ':')) + '\n').encode()
        release_hash = hashlib.sha256(data).hexdigest()
        helper = HELPER.read_bytes().replace(
            b"RELEASE_SHA = 'UNSET-REQUIRES-INDEPENDENT-RECOVERY-RELEASE-SHA256'",
            ("RELEASE_SHA = '" + release_hash + "'").encode())
        helper_hash = hashlib.sha256(helper).hexdigest()
        packet, count = re.subn(
            rb'(?m)^FINAL_HELPER_SHA=__REPLACE_WITH_FINAL_RECOVERY_HELPER_SHA256__; RELEASE_SHA=__REPLACE_WITH_FINAL_RECOVERY_RELEASE_SHA256__$',
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
        revalidate = source.index('validate_old_lease()', absence)
        unlink = source.index('os.unlink(OLD_LEASE)', revalidate)
        terminal = source.index("journal.write('terminal-success'", unlink)
        self.assertLess(absence, revalidate)
        self.assertLess(revalidate, unlink)
        self.assertLess(unlink, terminal)


if __name__ == '__main__':
    unittest.main()
