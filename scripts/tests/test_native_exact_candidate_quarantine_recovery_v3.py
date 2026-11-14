#!/usr/bin/env python3
"""Pure, immutable-evidence and temporary-filesystem tests; never access live scratch."""
import copy
import hashlib
import importlib.util
import json
import os
import stat
import subprocess
import sys
import tarfile
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
E = ROOT / 'docs/verification/evidence'
H = E / 'native-exact-candidate-quarantine-recover-68cf089a-3.py'
B = E / 'native-exact-candidate-quarantine-recovery-release-basis-68cf089a-3.json'
P = E / 'native-exact-candidate-quarantine-recovery-execution-68cf089a-3.sh'


def load():
    spec = importlib.util.spec_from_file_location('recover2', H)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Log:
    def __init__(self):
        self.records = []
    def write(self, phase, fields):
        self.records.append(dict(phase=phase, **fields))


class Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = load()
        current_basis = json.loads(B.read_bytes())
        paths = (H, P, B, Path(__file__))
        if current_basis.get('status') == 'DRAFT_NOT_RELEASED':
            cls.templates = {path: path.read_bytes() for path in paths}
        else:
            # A finalized test run still executes only the non-executable template.
            # Read static committed blobs; never invoke the finalized packet.
            source = current_basis['source_checkpoint']
            cls.templates = {path: subprocess.check_output(
                ['/usr/bin/git', '--git-dir=' + str(ROOT / '.git'), '--work-tree=' + str(ROOT),
                 'show', source + ':' + str(path.relative_to(ROOT))])
                for path in paths}

    def finalization(self):
        m = self.m
        draft_bytes = self.templates[B]
        basis = json.loads(draft_bytes)
        basis.update(status='PASS_ONE_SHOT_QUARANTINE_RECOVERY3', execution_authorized=True,
                     source_checkpoint='1' * 40, template_basis_sha256=m.digest_bytes(draft_bytes))
        data = (json.dumps(basis, sort_keys=True) + '\n').encode()
        release_sha = m.digest_bytes(data)
        helper = self.templates[H].replace(("RELEASE_SHA = '" + m.RELEASE_SENTINEL + "'").encode(),
                                       ("RELEASE_SHA = '" + release_sha + "'").encode(), 1)
        helper_sha = m.digest_bytes(helper)
        packet = self.templates[P].replace(('RELEASE_SHA=' + m.RELEASE_SENTINEL).encode(),
                                       ('RELEASE_SHA=' + release_sha).encode(), 1)
        packet = packet.replace(('FINAL_HELPER_SHA=' + m.PACKET_HELPER_SENTINEL).encode(),
                                ('FINAL_HELPER_SHA=' + helper_sha).encode(), 1)
        return basis, data, helper, packet, self.templates[Path(__file__)], release_sha

    def test_draft_is_nonexecutable_before_mutation(self):
        self.m.validate_draft_basis(json.loads(self.templates[B]))
        with mock.patch.object(self.m, 'execute_released_recovery') as execute, \
             mock.patch.object(self.m, 'read_regular', return_value=self.templates[B]):
            with mock.patch.object(sys, 'argv', [str(H)]):
                with self.assertRaisesRegex(RuntimeError, 'non-executable'):
                    self.m.main()
            execute.assert_not_called()
        with tempfile.TemporaryDirectory() as temp:
            packet = Path(temp) / 'non-executable-template.sh'
            packet.write_bytes(self.templates[P])
            result = subprocess.run(['/bin/bash', str(packet)], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(b'draft-helper-pin', result.stderr)

    def test_acyclic_mechanical_finalization(self):
        args = self.finalization()
        self.m.validate_released_basis(*args)
        basis, data, helper, packet, tests, release_sha = args
        self.assertNotIn('final_helper_sha256', basis)
        self.assertNotIn('release_sha256', basis)
        self.assertEqual(self.m.normalize_helper(helper, release_sha), self.templates[H])
        self.assertEqual(self.m.normalize_packet(packet, release_sha, self.m.digest_bytes(helper)), self.templates[P])
        for index in (1, 2, 3, 4):
            changed = list(args)
            changed[index] += b' '
            with self.assertRaises(RuntimeError):
                self.m.validate_released_basis(*changed)

    def test_template_hashes_match_and_threat_includes_deletion(self):
        basis = json.loads(self.templates[B])
        for key, path in (('template_helper', H), ('template_packet', P), ('template_test', Path(__file__))):
            self.assertEqual(basis[key]['sha256'], self.m.digest_bytes(self.templates[path]))
        self.assertIn('observation AND deletion', basis['operational_threat_assumption'])
        self.assertIn('not machine proof or an atomic census', basis['operational_threat_assumption'])

    def test_source_validation_exact_blobs_allows_unrelated_dirty(self):
        m = self.m
        basis, data, helper, packet, test, release_sha = self.finalization()
        final = {H: helper, P: packet, B: data, Path(__file__): test}
        template = self.templates
        head = '2' * 40
        commands = []
        def git(*args):
            commands.append(args)
            if args[0] == 'rev-parse':
                return (head + '\n').encode()
            commit, path = args[1].split(':', 1)
            return (final if commit == head else template)[ROOT / path]
        with mock.patch.object(m, 'git_bytes', side_effect=git), mock.patch.object(m, 'read_regular', side_effect=lambda p: final[p]):
            self.assertEqual(m.validate_source(basis), head)
        self.assertFalse(any('status' in command for command in commands))
        self.assertEqual(sum(command[0] == 'show' for command in commands), 8)
        with mock.patch.object(m, 'git_bytes', return_value=b'bad\n'):
            with self.assertRaises(RuntimeError):
                m.validate_source(basis)

    def test_git_actual_argv_has_explicit_repository_pair(self):
        m = self.m
        with mock.patch.object(m.subprocess, 'check_output', return_value=b'fixture\n') as check:
            for query in (('rev-parse', '--verify', 'HEAD'), ('rev-parse', '--verify', '@{upstream}'),
                          ('rev-parse', '--verify', 'FETCH_HEAD'), ('show', '1' * 40 + ':input')):
                self.assertEqual(m.git_bytes(*query), b'fixture\n')
                argv = check.call_args.args[0]
                self.assertEqual(argv, ['/usr/bin/git', '--git-dir=/home/holden/mckernel/.git',
                                        '--work-tree=/home/holden/mckernel', *query])
                self.assertNotIn('-C', argv)
                self.assertFalse(any('safe.directory' in item for item in argv))
                self.assertEqual(check.call_args.kwargs['timeout'], 30)

    def test_recovery2_failure_archive_and_consumed_sources_bound(self):
        self.m.validate_recovery2_history()
        self.assertEqual(len(self.m.recovery2_retained_hashes()), 8)
        self.assertEqual(self.m.historical_bindings()['recovery2_record'],
                         'fbdffcf75f073f22434bbdf43e52281e7bb8a99a30d14c9b1783f057ee133e3b')

    def test_recovery3_fresh_outputs_preserve_observer_v2(self):
        m = self.m
        for path in (m.CLAIM, m.JOURNAL, m.PREFLIGHT, m.OBSERVER_OUT, m.OBSERVER_ERR, m.RELEASE, m.EVIDENCE):
            self.assertIn('recovery3', str(path))
            self.assertIn('68cf089a-3', str(path))
            self.assertNotIn(path, m.recovery2_retained_hashes())
        self.assertEqual(m.OBSERVER.name, 'native-exact-candidate-live-reference-observer-68cf089a-2.py')
        self.assertIn('recovery3-execution-release', str(m.EXECUTION_RELEASE))

    def test_recovery2_retained_state_requires_absent_claims_and_exact_bytes(self):
        m = self.m
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            evidence = root / 'evidence'
            evidence.mkdir(mode=0o700)
            data = {'log': b'unchanged'}
            for name, content in data.items():
                (evidence / name).write_bytes(content)
            hashes = {name: m.digest_bytes(content) for name, content in data.items()}
            claim, journal = root / 'absent-claim', root / 'absent-journal'
            with mock.patch.object(m, 'EVIDENCE2', evidence), mock.patch.object(m, 'CLAIM2', claim), \
                 mock.patch.object(m, 'JOURNAL2', journal), mock.patch.object(m, 'RECOVERY2_OUTPUT_HASHES', hashes), \
                 mock.patch.object(m, 'recovery2_retained_hashes', return_value={evidence / 'log': hashes['log']}):
                m.validate_recovery2_retained_state()
                claim.write_bytes(b'unexpected')
                with self.assertRaisesRegex(RuntimeError, 'claim/journal'):
                    m.validate_recovery2_retained_state()
                claim.unlink()
                (evidence / 'log').write_bytes(b'changed')
                with self.assertRaisesRegex(RuntimeError, 'evidence mismatch'):
                    m.validate_recovery2_retained_state()

    def test_separate_execution_release_required(self):
        m = self.m
        basis = self.finalization()[0]
        release = dict(status='PASS_ONE_SHOT_QUARANTINE_RECOVERY3_EXECUTION', runtime_acceptance=False,
                       one_shot=True, retry=False, rollback=False, source_checkpoint=basis['source_checkpoint'],
                       basis_sha256=m.RELEASE_SHA, helper_sha256=m.sha(H), packet_sha256=m.sha(P),
                       test_sha256=m.sha(Path(__file__)), operational_threat_assumption=m.THREAT)
        data = json.dumps(release).encode()
        with mock.patch.object(m, 'read_regular', return_value=data), mock.patch.object(m, 'git_bytes', return_value=data):
            self.assertEqual(m.validate_execution_release(basis, '2' * 40), m.digest_bytes(data))
        release['retry'] = True
        data = json.dumps(release).encode()
        with mock.patch.object(m, 'read_regular', return_value=data), mock.patch.object(m, 'git_bytes', return_value=data):
            with self.assertRaises(RuntimeError):
                m.validate_execution_release(basis, '2' * 40)

    def test_historical_records_archives_and_observer_bindings(self):
        m = self.m
        m.validate_historical_records(json.loads(m.ORIGINAL_RECORD.read_bytes()), json.loads(m.RECOVERY1_RECORD.read_bytes()))
        m.validate_historical_archives()
        m.validate_observer_source_record()
        historical = ((E / 'native-exact-candidate-quarantine-recover-68cf089a-1.py', m.HISTORICAL_HELPER_SHA),
                      (E / 'native-exact-candidate-quarantine-recovery-execution-68cf089a-1.sh', m.HISTORICAL_PACKET_SHA),
                      (ROOT / 'docs/verification/stability-native-exact-quarantine-recovery-execution-release-20260929-1.json', m.HISTORICAL_EXECUTION_RELEASE_SHA),
                      (ROOT / 'scripts/tests/test_native_exact_candidate_live_reference_observer_v2.py', m.OBSERVER_TEST_SHA))
        for path, sha in historical:
            self.assertEqual(m.sha(path), sha)

    def test_journal_prior_deletion_and_duplicate_key_rejected(self):
        m = self.m
        data = b'{"phase":"delete-entry"}\n'
        with self.assertRaises(RuntimeError):
            m.validate_journal_bytes(data, m.digest_bytes(data), ['delete-entry'], 'fixture')
        with self.assertRaises(RuntimeError):
            m.exact_json_bytes(b'{"phase":"x","phase":"y"}')

    def observer(self):
        m = self.m
        members = [{(device, inode)} for _o, _q, device, inode in m.ROOTS]
        roots = [dict(path=str(q), device_number=d, inode=i, mode='0700',
                      tree_member_identities=[list(x) for x in sorted(s)])
                 for (_o, q, d, i), s in zip(m.ROOTS, members)]
        row = dict(clean=True, complete_mount_proofs=True, target_references=[], permission_denials=[],
                   unscanned_final_identities=[], unresolved_churn=[], tree_revalidation_failures=[],
                   closure_nonconvergent=False)
        rounds = [dict(row, round=1, clean=False, closure_nonconvergent=True,
                       unscanned_final_identities=[[9, 9, 9]], unresolved_churn=['benign replacement']),
                  dict(row, round=2), dict(row, round=3)]
        return dict(schema='mckernel.read-only-live-reference-snapshot.v7', status='PASS', scan_complete=True,
                    observer_sha256=m.OBSERVER_SHA, roots=roots, rounds=rounds, failure=None,
                    tree_observation_transients=[], persistent_tree_revalidation_failures=[]), members

    def test_v7_accepts_early_benign_churn_and_two_clean(self):
        value, members = self.observer()
        self.m.validate_observer_result(value, members)

    def test_v7_rejects_sticky_any_round_or_top_level(self):
        original, members = self.observer()
        for key in ('target_references', 'permission_denials', 'tree_revalidation_failures'):
            for location in ('early', 'top'):
                with self.subTest(key=key, location=location):
                    value = copy.deepcopy(original)
                    (value['rounds'][0] if location == 'early' else value)[key] = ['unsafe']
                    with self.assertRaises(RuntimeError):
                        self.m.validate_observer_result(value, members)
        for position in (0, 1, 2):
            value = copy.deepcopy(original)
            value['rounds'][position]['complete_mount_proofs'] = False
            with self.assertRaises(RuntimeError):
                self.m.validate_observer_result(value, members)
        for key, bad in (('clean', False), ('unresolved_churn', ['x']), ('closure_nonconvergent', True)):
            value = copy.deepcopy(original)
            value['rounds'][-2][key] = bad
            with self.assertRaises(RuntimeError):
                self.m.validate_observer_result(value, members)
        value = copy.deepcopy(original)
        value['roots'][0]['tree_member_identities'].append([1, 2])
        with self.assertRaises(RuntimeError):
            self.m.validate_observer_result(value, members)

    def test_exact_inventory_archive_hash_schema_counts(self):
        m = self.m
        archive = E / 'stability-native-exact-complete-inventory-68cf089a-20260929-1.tar.gz'
        with tarfile.open(archive, 'r:gz') as stream:
            data = stream.extractfile('native-exact-complete-worktree-inventory-68cf089a-1.json').read()
        value = m.validate_inventory_bytes(data)
        with self.assertRaises(RuntimeError):
            m.validate_inventory_bytes(data + b' ')
        for change in ('count', 'schema', 'duplicate', 'outside'):
            bad = copy.deepcopy(value)
            if change == 'count':
                bad['worktree_inventory'].pop()
            elif change == 'schema':
                bad['schema_version'] = 9
            elif change == 'duplicate':
                bad['worktree_inventory'][1] = bad['worktree_inventory'][0]
            else:
                bad['worktree_inventory'][0]['path'] = 'elsewhere'
            changed = json.dumps(bad).encode()
            with self.assertRaises(RuntimeError):
                m.validate_inventory_bytes(changed, m.digest_bytes(changed))

    def test_descriptor_traversal_and_delete_temp_tree(self):
        m = self.m
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / 'quarantine'
            root.mkdir(mode=0o700)
            (root / 'd').mkdir()
            (root / 'd' / 'f').write_bytes(b'file')
            (root / 'link').symlink_to('d/f')
            orig = Path('/fixture/original')
            rows = []
            for rel in ('', 'd', 'd/f', 'link'):
                path = root / rel
                info = m.wanted_identity(os.lstat(path))
                digest = None if info['type'] == 'directory' else m.digest_bytes(
                    os.fsencode(os.readlink(path)) if info['type'] == 'symlink' else path.read_bytes())
                rows.append(dict(path=str(orig.relative_to('/')) + ('/' + rel if rel else ''),
                                 type=info['type'], mode=info['mode'], sha256=digest))
            info = os.lstat(root)
            # Synthetic roots bind the current unprivileged fixture owner.
            wanted = m.wanted_identity(info)
            with mock.patch.object(m, 'root_wanted', return_value=wanted):
                expected = m.reconstruct_inventory({'worktree_inventory': rows},
                                                    ((orig, root, info.st_dev, info.st_ino),))
            fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY)
            try:
                m.delete_verified(fd, {rel: row for (_root, rel), row in expected.items()},
                                  '', info.st_dev, Log(), str(root), wanted)
            finally:
                os.close(fd)
            self.assertEqual(list(root.iterdir()), [])

    def test_open_checked_rejects_directory_fd_swap(self):
        m = self.m
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'one').mkdir()
            (root / 'two').mkdir()
            wanted = m.wanted_identity(os.lstat(root / 'one'))
            fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY)
            def swapped(_name, flags, dir_fd):
                return os.open('two', flags, dir_fd=dir_fd)
            try:
                with self.assertRaisesRegex(RuntimeError, 'identity'):
                    m.open_checked(fd, 'one', wanted, swapped)
            finally:
                os.close(fd)

    def test_open_checked_rejects_name_swap_after_open(self):
        m = self.m
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'one').mkdir()
            (root / 'two').mkdir()
            wanted = m.wanted_identity(os.lstat(root / 'one'))
            fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY)
            def swapped(name, flags, dir_fd):
                child = os.open(name, flags, dir_fd=dir_fd)
                (root / 'one').rename(root / 'old')
                (root / 'two').rename(root / 'one')
                return child
            try:
                with self.assertRaisesRegex(RuntimeError, 'identity'):
                    m.open_checked(fd, 'one', wanted, swapped)
            finally:
                os.close(fd)

    def test_delete_rejects_wrong_open_root_identity(self):
        m = self.m
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            wanted = m.wanted_identity(os.lstat(root))
            wanted['inode'] += 1
            fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY)
            try:
                with self.assertRaises(RuntimeError):
                    m.delete_verified(fd, {}, '', wanted['dev'], Log(), str(root), wanted)
            finally:
                os.close(fd)

    def test_short_writes_complete_and_zero_fails(self):
        data, chunks = b'1234567', []
        def write(_fd, chunk):
            chunks.append(chunk[:2])
            return len(chunk[:2])
        self.m.full_write(1, data, write)
        self.assertEqual(b''.join(chunks), data)
        with self.assertRaises(RuntimeError):
            self.m.full_write(1, data, lambda _fd, _chunk: 0)

    def test_exclusive_files_reject_existing_and_symlink(self):
        m = self.m
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            m.write_exclusive(root / 'one', b'x')
            (root / 'link').symlink_to(root / 'absent')
            for path in (root / 'one', root / 'link'):
                with self.assertRaises(FileExistsError):
                    m.write_exclusive(path, b'y')
            self.assertFalse((root / 'absent').exists())

    def test_second_claim_creation_failure_has_terminal_journal(self):
        m = self.m
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            claim, journal = root / 'claim', root / 'journal'
            claim.write_bytes(b'permanent')
            snapshot = lambda: m.survivor_state((), root / 'absent', (claim,))
            with self.assertRaises(FileExistsError):
                m.with_claimed_journal(lambda _j: self.fail('must not run'), journal, claim, snapshot)
            rows = [json.loads(line) for line in journal.read_text().splitlines()]
            self.assertEqual([row['phase'] for row in rows], ['journal-created', 'terminal-failure'])
            self.assertFalse(rows[-1]['state']['old_lease']['present'])
            self.assertEqual(claim.read_bytes(), b'permanent')

    def test_terminal_failure_reports_lease_removed(self):
        m = self.m
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            lease = root / 'lease'
            lease.write_bytes(b'lease')
            def action(_journal):
                lease.unlink()
                raise RuntimeError('after lease removal')
            snapshot = lambda: m.survivor_state((), lease, ())
            with self.assertRaisesRegex(RuntimeError, 'after lease'):
                m.with_claimed_journal(action, root / 'journal', root / 'claim', snapshot)
            terminal = json.loads((root / 'journal').read_text().splitlines()[-1])
            self.assertFalse(terminal['state']['old_lease']['present'])

    def test_old_lease_binds_identity_digest_and_absence(self):
        m = self.m
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            lease = root / 'lease'
            lease.write_bytes(b'lease')
            info = os.lstat(lease)
            wanted = (info.st_dev, info.st_ino, stat.S_IMODE(info.st_mode), info.st_uid, info.st_gid)
            (root / 'protected').mkdir()
            with self.assertRaises(RuntimeError):
                m.remove_old_lease_after_absence(Log(), lease, (root / 'protected',), m.sha(lease), wanted)
            with self.assertRaises(RuntimeError):
                m.remove_old_lease_after_absence(Log(), lease, (), '0' * 64, wanted)
            m.remove_old_lease_after_absence(Log(), lease, (), m.sha(lease), wanted)
            self.assertFalse(lease.exists())

    def test_docker_ancestor_descendant_normalization(self):
        m = self.m
        for path in ('/dev/shm', str(m.C) + '/child', '/dev/shm/elsewhere/../' + m.QC.name, '/'):
            for key in ('Source', 'Destination'):
                mount = dict(Source='/unrelated/source', Destination='/unrelated/destination')
                mount[key] = path
                with self.assertRaises(RuntimeError):
                    m.evaluate_docker([dict(Mounts=[mount])])
        m.evaluate_docker([dict(Mounts=[dict(Source='/unrelated', Destination='/elsewhere')])])
        for malformed in ({}, [dict(Mounts=[dict(Source='relative', Destination='/other')])]):
            with self.assertRaises(RuntimeError):
                m.evaluate_docker(malformed)

    def test_process_filter_and_capacity(self):
        m = self.m
        clean = b'1 0 systemd /sbin/init\n2 1 python3 python3 unrelated.py\n'
        self.assertEqual(len(m.evaluate_processes(clean, set())), 2)
        for command in ('qemu-system-x86_64 /bin/qemu-system-x86_64', 'make make -j4',
                        'mcexec mcexec hello', 'python3 python3 ' + str(H),
                        'python3 python3 scripts/native_rust_exact_build_offline.py run',
                        'python3 python3 scripts/application-tests/native_diagnostic_container_owner.py run'):
            with self.assertRaises(RuntimeError):
                m.evaluate_processes(('3 1 ' + command + '\n').encode(), set())
        capacity = dict(host_free=16 << 30, scratch_free=12 << 30, tmpfs_free=4 << 30, mem_available=4 << 30)
        m.validate_capacity(capacity)
        for key in capacity:
            changed = dict(capacity)
            changed[key] -= 1
            with self.assertRaises(RuntimeError):
                m.validate_capacity(changed)

    def test_substantive_preflight_bindings_and_freshness(self):
        m = self.m
        basis = self.finalization()[0]
        proc = b'1 0 systemd /sbin/init\n'
        value = dict(schema='mckernel.recovery3-preflight.v2', boot_id='boot',
                     helper_sha256=m.sha(H), packet_sha256=m.sha(P), basis_sha256=m.RELEASE_SHA,
                     test_sha256=m.sha(Path(__file__)), source_checkpoint=basis['source_checkpoint'],
                     head='head', execution_release_sha256='exec', operational_threat_assumption=m.THREAT,
                     historical_bindings=m.historical_bindings(), monotonic=100, wall_time=time.time(),
                     roots=['bound'], old_state={'bound': True},
                     capacity=dict(host_free=16 << 30, scratch_free=12 << 30, tmpfs_free=4 << 30, mem_available=4 << 30),
                     process_allowed_ancestors=[1, 999999999], prepare_pid=999999999,
                     process_sha256=m.digest_bytes(proc), process_rows=m.evaluate_processes(proc, {1}))
        with mock.patch.object(m, 'root_observation', return_value=['bound']), \
             mock.patch.object(m, 'survivor_state', return_value={'bound': True}), \
             mock.patch.object(m, 'capacity'), mock.patch.object(m, 'ancestors', return_value={1, 2}):
            m.validate_preflight(value, basis, 'head', 'exec', proc, now=101, boot='boot')
            for key, bad in (('boot_id', 'other'), ('monotonic', -21), ('process_sha256', '0' * 64),
                             ('historical_bindings', {}), ('roots', []), ('old_state', {}),
                             ('helper_sha256', '0' * 64), ('operational_threat_assumption', 'weaker')):
                changed = dict(value)
                changed[key] = bad
                with self.assertRaises(RuntimeError, msg=key):
                    m.validate_preflight(changed, basis, 'head', 'exec', proc, now=101, boot='boot')

    def test_capture_fsync_on_command_failure(self):
        m = self.m
        with tempfile.TemporaryDirectory() as temp:
            def failed(argv, **kwargs):
                os.write(kwargs['stdout'], b'partial')
                os.write(kwargs['stderr'], b'failure')
                return subprocess.CompletedProcess(argv, 5)
            with mock.patch.object(m, 'EVIDENCE', Path(temp)):
                with self.assertRaises(RuntimeError):
                    m.capture_command(['/fixture'], 'fixture', run=failed)
                self.assertEqual((Path(temp) / 'fixture.stdout').read_bytes(), b'partial')
                self.assertEqual(json.loads((Path(temp) / 'fixture.result.json').read_bytes())['returncode'], 5)

    def test_packet_one_privilege_call_and_failure_capture(self):
        text = P.read_text()
        self.assertEqual(text.count('/usr/bin/sudo -A'), 1)
        self.assertNotIn('sudo -n', text)
        self.assertIn('/usr/bin/env -i', text)
        self.assertIn('/usr/bin/setsid --wait /usr/bin/timeout --signal=TERM --kill-after=10s 900s', text)
        self.assertLess(text.index('set +e'), text.index('/usr/bin/sudo -A'))
        self.assertLess(text.index('rc=$?'), text.index('--finish-packet'))
        self.assertNotIn('dirty-template', text)
        with tempfile.TemporaryDirectory() as temp, mock.patch.object(self.m, 'EVIDENCE', Path(temp)):
            (Path(temp) / 'recovery.stdout').write_bytes(b'partial')
            (Path(temp) / 'recovery.stderr').write_bytes(b'failure')
            with self.assertRaisesRegex(RuntimeError, 'rc=7'):
                self.m.finish_packet(7)
            self.assertEqual((Path(temp) / 'recovery.rc').read_bytes(), b'7\n')

    def test_timeout_retains_structured_capture(self):
        m = self.m
        with tempfile.TemporaryDirectory() as temp:
            def timed_out(argv, **kwargs):
                os.write(kwargs['stdout'], b'partial')
                raise subprocess.TimeoutExpired(argv, 30)
            with mock.patch.object(m, 'EVIDENCE', Path(temp)):
                with self.assertRaises(subprocess.TimeoutExpired):
                    m.capture_command(['/fixture'], 'timeout', run=timed_out)
            value = json.loads((Path(temp) / 'timeout.result.json').read_bytes())
            self.assertIsNone(value['returncode'])
            self.assertIn('TimeoutExpired', value['error'])
            self.assertEqual((Path(temp) / 'timeout.stdout').read_bytes(), b'partial')

    def test_signal_records_terminal_state(self):
        m = self.m
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            snapshot = lambda: m.survivor_state((), root / 'absent', ())
            def action(_journal):
                os.kill(os.getpid(), m.signal.SIGTERM)
            with self.assertRaisesRegex(RuntimeError, 'signal 15'):
                m.with_claimed_journal(action, root / 'journal', root / 'claim', snapshot)
            value = json.loads((root / 'journal').read_text().splitlines()[-1])
            self.assertEqual(value['phase'], 'terminal-failure')
            self.assertFalse(value['state']['old_lease']['present'])


if __name__ == '__main__':
    unittest.main()
