"""Disposable negative and positive protocol fixtures; no live observation."""
import copy
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest import mock

SOURCE = Path(__file__).resolve().parents[1] / 'native_exact_scratch22_image_retirement_reconcile.py'


def load():
    spec = importlib.util.spec_from_file_location('reconciliation_fixture', SOURCE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ReconcileTests(unittest.TestCase):
    def setUp(self):
        self.m = load()

    def process(self):
        return dict(schema='scratch21.proc.v1', uid=0, boot_id=self.m.BOOT,
                    challenge='fresh', caller=[42, '99'], publishers=[],
                    snapshots=[[[1, 0, '1'], [42, 1, '99']], [[1, 0, '1'], [42, 1, '99']]])

    def test_complete_two_snapshot_process_report(self):
        self.m.validate_process_report(self.process(), 'fresh', [42, '99'])

    def test_every_old_client_and_owner_rejected_in_either_snapshot(self):
        for pid in self.m.ABSENT:
            for which in range(2):
                report = self.process()
                report['snapshots'][which].append([pid, 1, '123'])
                with self.subTest(pid=pid, snapshot=which), self.assertRaises(self.m.Refusal):
                    self.m.validate_process_report(report, 'fresh', [42, '99'])

    def test_publisher_stale_boot_challenge_caller_and_incomplete_census_refuse(self):
        for key, value in [('publishers', [[4, '2', '/usr/bin/make']]), ('boot_id', 'old'),
                           ('challenge', 'old'), ('caller', [43, '99']), ('uid', True),
                           ('snapshots', [self.process()['snapshots'][0]])]:
            report = self.process(); report[key] = value
            with self.subTest(key=key), self.assertRaises(self.m.Refusal):
                self.m.validate_process_report(report, 'fresh', [42, '99'])
        report = self.process(); report['snapshots'][0].pop(0)
        with self.assertRaises(self.m.Refusal): self.m.validate_process_report(report, 'fresh', [42, '99'])

    def test_all_clients_transitive_descendants_across_snapshots_refuse(self):
        for pid in self.m.ABSENT:
            for which in (0, 1):
                report = self.process()
                report['snapshots'][which].append([999, pid, '12'])
                # The grandchild appears in the other snapshot, including a
                # parent whose own historical ancestor has already disappeared.
                report['snapshots'][1-which].append([1001, 999, '13'])
                with self.subTest(root=pid, snapshot=which), self.assertRaises(self.m.Refusal):
                    self.m.validate_process_report(report, 'fresh', [42, '99'])

    def test_bound_parsed_bytes_and_after_read_identity(self):
        m = self.m
        raw = b'{"expected":true}'
        row = dict(path='/frozen', sha256=m.core.sha(raw), size=len(raw), inode=10)
        with mock.patch.object(m.cleanup, 'observe_identity', return_value=row), \
             mock.patch.object(m.cleanup, 'read_bounded', return_value=raw):
            self.assertEqual(m.read_binding(row), {'expected': True})
        with mock.patch.object(m.cleanup, 'observe_identity', return_value=row), \
             mock.patch.object(m.cleanup, 'read_bounded', return_value=b'{"different_bytes":true}'), \
             self.assertRaises(m.Refusal):
            m.read_binding(row)
        with mock.patch.object(m.cleanup, 'observe_identity', side_effect=[row, dict(row, inode=11)]), \
             mock.patch.object(m.cleanup, 'read_bounded', return_value=raw), self.assertRaises(m.Refusal):
            m.read_binding(row)
        # The release consumer uses this same bound parser, not a second
        # independent read whose bytes could differ from the authenticated row.
        with mock.patch.object(m, 'read_binding', side_effect=m.Refusal('bound release bytes differ')), \
             self.assertRaises(m.Refusal):
            m.bind_release(Path('/frozen'), row['sha256'], consuming=True, binding=row)

    def test_scratch_uuid_device_and_root_identity_are_exact(self):
        m = self.m
        mount = dict(target=str(m.ROOT), source='/dev/loop36', fstype='ext4',
                     options='rw,nodev,nosuid', uuid=m.cleanup.UUID, **{'maj:min': '7:36'})
        root = dict(path=str(m.ROOT), device=1828, inode=55, mode='0o755', uid=1000, gid=1000)
        obs = dict(mount=mount, root=root)
        encode = lambda value: m.core.canonical(dict(filesystems=[value]))
        m.validate_mount_binding(encode(mount), root, obs)
        for key, value in [('uuid', 'other'), ('target', '/elsewhere'), ('fstype', 'tmpfs'),
                           ('options', 'rw,nodev'), ('maj:min', '7:37')]:
            changed = dict(mount); changed[key] = value
            with self.subTest(mount=key), self.assertRaises(m.Refusal):
                m.validate_mount_binding(encode(changed), root, obs)
        for key, value in [('device', 1829), ('inode', 56), ('uid', 0), ('mode', '0o777')]:
            with self.subTest(root=key), self.assertRaises(m.Refusal):
                m.validate_mount_binding(encode(mount), dict(root, **{key: value}), obs)
        # Even a release that blesses a different UUID/device must fail.
        wrong = dict(mount, uuid='other')
        with self.assertRaises(m.Refusal): m.validate_mount_binding(encode(wrong), root, dict(obs, mount=wrong))

    def test_mount_order_only_is_ignored(self):
        value = dict(Mounts=[dict(Destination='/a', RW=False, Source='/source'),
                             dict(Destination='/b', RW=True, Source='/out')], Config={'a': 1})
        other = copy.deepcopy(value); other['Mounts'].reverse()
        self.assertEqual(self.m.core.inspect_comparison(value), self.m.core.inspect_comparison(other))
        other['Mounts'][0]['RW'] = False
        self.assertNotEqual(self.m.core.inspect_comparison(value), self.m.core.inspect_comparison(other))
        for mounts in ([dict(Destination='/a'), dict(Destination='/a')], [dict(Destination='relative')], [{}]):
            with self.assertRaises(self.m.Refusal): self.m.core.inspect_comparison(dict(Mounts=mounts))

    def test_exact_container_census_and_competing_aliases(self):
        receipt = dict(container_name='name', owner_nonce='nonce')
        row = dict(ID=self.m.CONTAINER, Names='name', State='exited', Labels='mckernel.owner=nonce')
        encode = lambda rows: b''.join(self.m.core.canonical(r) for r in rows)
        self.m.validate_containers(encode([row]), receipt)
        for other in [dict(ID='a'*64, Names='other', State='running'),
                      dict(ID='a'*64, Names='name', State='exited'),
                      dict(ID='a'*64, Names='other', State='exited', Labels='mckernel.owner=nonce')]:
            with self.assertRaises(self.m.Refusal): self.m.validate_containers(encode([row, other]), receipt)
        with self.assertRaises(self.m.Refusal): self.m.validate_containers(encode([]), receipt)

    def test_missing_inputs_cannot_become_a_proof(self):
        with self.assertRaises(self.m.Refusal): self.m.validate_inputs({})
        with self.assertRaises(OSError): self.m.bind_release(Path('/nonexistent'), '0'*64)

    def release(self):
        return dict(schema=self.m.SCHEMA+'-release.v1', status='PASS_EXECUTION_RELEASE', execution_count=1,
                    fetched_source_verified=True, source_checkpoint='a'*40, author='author', files_sha256={},
                    nonce='b'*32, output=str(self.m.ROOT / ('scratch22-image-retirement-reconciliation-'+'b'*32)),
                    observation={}, source_review=dict(path='/source-review', sha256='c'*64),
                    execution_review=dict(path='/execution-review', sha256='d'*64))

    def test_independent_exact_reviews_and_fresh_nonce(self):
        m = self.m; release = self.release()
        def read(path, expected):
            if str(path) == '/release': return release
            return dict(decision='PASS_SOURCE' if str(path) == '/source-review' else 'PASS_EXECUTION_REVIEW',
                        reviewer='reviewer', implementation_ownership=False, files_sha256={},
                        source_checkpoint='a'*40, frozen_inputs_sha256=m.core.sha(m.core.canonical({})))
        with mock.patch.object(m.core, 'read_json', side_effect=read), \
             mock.patch.object(m, 'files_sha256', return_value={}), \
             mock.patch.object(m.os.path, 'lexists', return_value=False), \
             mock.patch.object(m.os, 'geteuid', return_value=0), \
             mock.patch.object(m.os, 'sched_getaffinity', return_value={0}):
            self.assertEqual(m.bind_release(Path('/release'), 'f'*64)[0], release)
            for key, value in [('status', 'PASS_SOURCE'), ('execution_count', True),
                               ('files_sha256', {'changed': '0'*64}), ('nonce', '../old'),
                               ('author', 'reviewer'), ('fetched_source_verified', False)]:
                old = release[key]; release[key] = value
                with self.subTest(key=key), self.assertRaises(m.Refusal): m.bind_release(Path('/release'), 'f'*64)
                release[key] = old
            with mock.patch.object(m.os.path, 'lexists', return_value=True), self.assertRaises(m.Refusal):
                m.bind_release(Path('/release'), 'f'*64)

    def test_observer_publishes_distinct_proof_and_retains_timeout_output(self):
        import os
        import subprocess
        from types import SimpleNamespace
        m = self.m
        for timeout in (False, True):
            with tempfile.TemporaryDirectory() as td:
                root = Path(td)
                m.ROOT = root
                output = root / 'fresh'
                lock = os.open(root / 'fake-lock', os.O_RDWR | os.O_CREAT, 0o600)
                item = dict(Mounts=[dict(Destination='/a', RW=False)])
                receipt = dict(container_name='name', owner_nonce='nonce')
                release = dict(observation=dict(container_inspect=item), nonce='a'*32)
                process = self.process()
                def run(argv, **kwargs):
                    if timeout and argv[0] == '/usr/bin/python3':
                        raise subprocess.TimeoutExpired(argv, 30, output=b'partial', stderr=b'diagnostic')
                    if 'inspect' in argv:
                        value = [item]
                    elif 'ps' in argv:
                        value = dict(ID=m.CONTAINER, Names='name', State='exited')
                    else:
                        value = process
                    return SimpleNamespace(stdout=m.core.canonical(value), stderr=b'', returncode=0)
                fields = ['0'] * 20; fields[19] = '99'
                with mock.patch.object(m.core, 'acquire_root_lock', return_value=lock), \
                     mock.patch.object(m.core, 'require_lock_holder'), \
                     mock.patch.object(m, 'validate_inputs', return_value=receipt), \
                     mock.patch.object(m.core, 'proc_stat', return_value=fields), \
                     mock.patch.object(m.core, 'process_code', return_value='frozen-census'), \
                     mock.patch.object(m, 'validate_mount_binding') as mounts, \
                     mock.patch.object(m, 'validate_process_report') as validate, \
                     mock.patch.object(m.subprocess, 'run', side_effect=run):
                    if timeout:
                        with self.assertRaises(m.Refusal): m.observe(release, output, {})
                        self.assertEqual((output / 'process.stdout').read_bytes(), b'partial')
                        self.assertEqual((output / 'process.stderr').read_bytes(), b'diagnostic')
                        self.assertFalse((output / 'recovery-proof.json').exists())
                        validate.assert_not_called()
                    else:
                        proof = m.observe(release, output, {})
                        self.assertTrue((output / 'recovery-proof.json').exists())
                        self.assertFalse(proof['original_guard_retirement_proven'])
                        self.assertTrue(proof['cleanup_separately_required'])
                        self.assertEqual(len(proof['captures']), 12)
                        self.assertEqual(mounts.call_count, 2)
                        validate.assert_called_once()
                self.assertFalse((output / 'guard-result.json').exists())

    def test_existing_root_lock_never_created_or_unlinked(self):
        import ast
        tree = ast.parse(SOURCE.read_text())
        names = [n.func.attr for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)]
        self.assertNotIn('unlink', names)
        self.assertNotIn('kill', names)
        self.assertNotIn('sole_sigkill', names)
        self.assertIn('acquire_root_lock', names)

    def test_bad_frozen_input_identity_refuses(self):
        row = dict(path='/frozen', sha256='a'*64)
        with mock.patch.object(self.m.cleanup, 'observe_identity', return_value=dict(row, sha256='b'*64)), \
             self.assertRaises(self.m.Refusal): self.m.read_binding(row)

    def test_incomplete_client_capture_cannot_prove_retirement(self):
        with tempfile.TemporaryDirectory() as td:
            self.m.ROOT = Path(td)
            root = self.m.ROOT / 'native-image-guard-942c927b-20261017-591fd260dfd144b584617b2298da1c8d'
            root.mkdir()
            with self.assertRaises(self.m.Refusal):
                self.m.validate_original_clients([], dict(guard_capture=str(root)))


if __name__ == '__main__':
    unittest.main()
