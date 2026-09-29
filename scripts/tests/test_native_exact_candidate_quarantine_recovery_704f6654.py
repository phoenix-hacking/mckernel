#!/usr/bin/env python3
"""Source-only regression tests for the 704f quarantine continuation."""
import copy
import importlib.util
import json
import os
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
E = ROOT / 'docs/verification/evidence'
H = E / 'native-exact-candidate-quarantine-recover-704f6654-1.py'
B = E / 'native-exact-candidate-quarantine-recovery-release-basis-704f6654-1.json'
P = E / 'native-exact-candidate-quarantine-recovery-execution-704f6654-1.sh'


def load():
    spec = importlib.util.spec_from_file_location('recover704f', H)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = load()

    def test_draft_fails_before_side_effects_and_wrapper_is_inert(self):
        m = self.m
        with mock.patch.object(m, 'validate_authorities') as authorities:
            with self.assertRaisesRegex(m.Error, 'DRAFT_NOT_RELEASED'):
                m.main([])
            authorities.assert_not_called()
        result = subprocess.run(['/bin/bash', str(P)], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(b'DRAFT_NOT_RELEASED', result.stderr)

    def test_basis_has_all_finalization_sentinels_and_no_authority(self):
        m = self.m
        value = json.loads(B.read_text())
        m.validate_draft_basis(value)
        self.assertFalse(value['execution_authorized'])
        self.assertIn('independently review', ' '.join(value['mechanical_finalization']).lower())
        with self.assertRaisesRegex(m.Error, 'DRAFT_NOT_RELEASED'):
            m.draft_guard(value)

    def test_mechanical_source_finalization_still_has_no_execution_authority(self):
        m = self.m
        value = json.loads(B.read_text())
        value.update(status='PASS_ONE_SHOT_QUARANTINE_CONTINUATION',
                     observer_sha256='1' * 64, release_sha256='2' * 64,
                     packet_sha256='3' * 64, test_sha256='4' * 64)
        m.validate_final_basis(value)
        value['execution_authorized'] = True
        with self.assertRaises(m.Error): m.validate_final_basis(value)

    def test_authorities_are_fetched_and_exact(self):
        m = self.m
        packet = H.read_bytes()  # distinct fixture bytes; no live root access
        release = b'{"status":"PASS_ONE_SHOT_RETIRE","template":{"commit":"ef7b8ef8afa4ac458368f2d4ba26817846fbf8ee"}}'
        paths = {m.V2_PACKET: b'p', m.V2_RELEASE: release, m.INVENTORY: b'i', m.CAPSULE: b'c', m.SUCCESS: b's', m.HELPER: b'h'}
        hashes = {path: m.digest(data) for path, data in paths.items()}
        with mock.patch.object(m, 'V2_PACKET_SHA', hashes[m.V2_PACKET]), mock.patch.object(m, 'V2_RELEASE_SHA', hashes[m.V2_RELEASE]), \
             mock.patch.object(m, 'INVENTORY_SHA', hashes[m.INVENTORY]), mock.patch.object(m, 'CAPSULE_SHA', hashes[m.CAPSULE]), \
             mock.patch.object(m, 'SUCCESS_SHA', hashes[m.SUCCESS]), mock.patch.object(m, 'HELPER_SHA', hashes[m.HELPER]), \
             mock.patch.object(m, 'checked', side_effect=lambda path, wanted: paths[path]), \
             mock.patch.object(m, 'read_regular', side_effect=lambda path: paths[path]), \
             mock.patch.object(m, 'git_bytes', side_effect=[b'p', release]):
            self.assertEqual(m.validate_authorities()['status'], 'PASS_ONE_SHOT_RETIRE')

    def test_observer_rejects_mount_or_sticky_findings(self):
        m = self.m
        expected = [{}, {}]
        roots = [dict(path=str(q), device_number=d, inode=i, mode='0700', tree_member_identities=[[d, i]]) for _o, q, d, i in m.ROOTS]
        clean = dict(clean=True, target_references=[], permission_denials=[], tree_revalidation_failures=[], complete_mount_proofs=True, unresolved_churn=[], closure_nonconvergent=False, unscanned_final_identities=[])
        value = dict(schema='mckernel.read-only-live-reference-snapshot.v7', status='PASS', observer_sha256=m.OBSERVER_SHA_REQUIRED, complete_mount_proofs=True, roots=roots, rounds=[dict(clean, round=1), dict(clean, round=2)], target_references=[], permission_denials=[], tree_revalidation_failures=[], persistent_tree_revalidation_failures=[], unscanned_final_identities=[])
        m.validate_observer(value, expected)
        for key, bad in [('complete_mount_proofs', False), ('target_references', ['fd']), ('unscanned_final_identities', [[1, 2]])]:
            changed = copy.deepcopy(value); changed[key] = bad
            with self.assertRaises(m.Error): m.validate_observer(changed, expected)

    def test_docker_rejects_unknown_or_protected_mount(self):
        m = self.m
        ids = ['a' * 64, 'b' * 64, 'c' * 64, 'd' * 64]
        rows = [dict(Id=i, Mounts=[]) for i in ids]
        release = {'docker': {'terminal_containers': {row['Id']: row for row in rows}}}
        m.validate_docker(rows, release)
        changed = copy.deepcopy(rows); changed[0]['Mounts'] = [dict(Source=str(m.QUARANTINES[0]))]
        release = {'docker': {'terminal_containers': {row['Id']: row for row in changed}}}
        with self.assertRaises(m.Error): m.validate_docker(changed, release)

    def test_checked_delete_temp_tree_and_no_delete_before_proof(self):
        m = self.m
        log = []
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); (root / 'd').mkdir(); (root / 'd' / 'f').write_text('x')
            rows = {}
            for rel in ('d', 'd/f'):
                info = m.member_identity(os.lstat(str(root / rel)))
                rows[rel] = dict(info, sha256=m.digest((root / rel).read_bytes()) if info['kind'] == 'file' else None)
            fd = os.open(str(root), os.O_RDONLY | os.O_DIRECTORY)
            try:
                m.delete_dirfd(fd, rows, lambda phase, **kw: log.append((phase, kw)), 'r')
            finally:
                os.close(fd)
            self.assertEqual(os.listdir(str(root)), [])
            self.assertEqual([phase for phase, _kw in log], ['before-entry', 'before-entry', 'after-entry', 'after-entry'])
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); (root / 'extra').write_text('x'); fd = os.open(str(root), os.O_RDONLY | os.O_DIRECTORY)
            try:
                with self.assertRaisesRegex(m.Error, 'delete-before-proof'):
                    m.delete_dirfd(fd, {}, lambda *a, **k: None, 'r')
            finally: os.close(fd)
            self.assertTrue((root / 'extra').exists())

    def test_descriptor_cleanup_is_bounded_and_closes_real_temporary_fds(self):
        m = self.m
        one, two = os.pipe()
        m.close_descriptors([one, two, None])
        for fd in (one, two):
            with self.assertRaises(OSError): os.fstat(fd)

    def test_raw_history_fixture_detects_archive_or_live_mutation(self):
        m = self.m
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp); evidence = base / '.mckernel-retirement-evidence-704f6654-2'; evidence.mkdir(mode=0o700)
            tomb = base / 'native-exact-build-lease-704f6654-1.json'; tomb.write_bytes(b'tomb')
            # A malformed archive must be rejected before any deletion path exists.
            archive = base / 'bad.tar.gz'; import tarfile
            with tarfile.open(str(archive), 'w:gz') as stream: stream.add(str(tomb), arcname='wrong')
            with mock.patch.object(m, 'RAW_SHA', m.digest(archive.read_bytes())):
                with self.assertRaises(m.Error): m.validate_raw_history(archive, evidence, tomb)


if __name__ == '__main__':
    unittest.main()
