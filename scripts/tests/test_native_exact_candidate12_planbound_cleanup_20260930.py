"""Disposable filesystem tests; never access real candidate, Docker, or sudo."""
import copy
import contextlib
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import signal
import stat
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

PATH = Path(__file__).resolve().parents[2] / 'docs/verification/evidence/native-exact-candidate12-planbound-cleanup-20260930.py'
SPEC = importlib.util.spec_from_file_location('planbound_cleanup', PATH)
m = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(m)
REAL_GIT = m.git
REAL_COLLECT_CENSUS = m.collect_census


class Fixture(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='candidate12-test-')
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.root = self.base / 'candidate'
        self.evidence = self.root / 'docs/verification/evidence'
        self.evidence.mkdir(parents=True)
        self.source = {}
        self.rows = []
        for i in range(3):
            p = self.evidence / ('file-' + str(i))
            b = ('retained original ' + str(i) + '\n').encode()
            p.write_bytes(b)
            p.chmod(0o755 if i == 1 else 0o644)
            os.utime(p, ns=(1700000000000000000 + i, 1700000000000000000000 + i))
            s = p.stat()
            row = {'path': str(p), 'restore_git_path': str(p.relative_to(self.root)),
                   'blob': hashlib.sha1(b'blob ' + str(len(b)).encode() + b'\0' + b).hexdigest(),
                   **m.metadata(s), 'sha256': m.sha(b), 'allocated_bytes': s.st_blocks * 512}
            self.rows.append(row)
            self.source[row['restore_git_path']] = b
        self.protected = self.base / 'protected'
        self.protected.write_bytes(b'untouchable')
        self.protected.chmod(0o600)
        self.protected_dir = self.base / 'protected-dir'
        self.protected_dir.mkdir()
        s = self.protected.stat()
        protected = [{'path': str(self.protected), 'type': 'file', 'dev': s.st_dev,
                      'ino': s.st_ino, 'mode': stat.S_IMODE(s.st_mode), 'size': s.st_size,
                      'sha256': m.sha(self.protected.read_bytes())}]
        s = self.protected_dir.stat()
        protected.append({'path': str(self.protected_dir), 'type': 'directory',
                          'dev': s.st_dev, 'ino': s.st_ino, 'mode': stat.S_IMODE(s.st_mode)})
        s = self.root.stat()
        self.plan = {'candidate_commit': 'a' * 40, 'candidate_identity': f'{s.st_dev}:{s.st_ino}',
                     'candidate_root': str(self.root), 'nested_delta_preserved': True,
                     'preserved': [], 'protected_paths': [r['path'] for r in protected],
                     'safety_census': {'protected': protected},
                     'schema': 'mckernel.exact-git-source-audit.v1', 'status': 'AUDIT_PASS',
                     'targets': self.rows}
        self.plan_path = self.base / 'plan.json'
        self.seal()
        self.outputs = {k: str(self.base / (k + '.json')) for k in ('journal', 'receipt', 'status')}
        self.outputs['quarantine'] = str(self.root / '.planbound-cleanup-test')
        self.container_bindings = copy.deepcopy(m.CONTAINER_BINDINGS)
        for expected in self.container_bindings.values():
            for row in expected['Mounts']:
                source = row['Source']
                if m.inside(source, m.BINDING['root']):
                    source = str(self.root) + source[len(m.BINDING['root']):]
                elif m.inside(source, m.SCRATCH):
                    source = str(self.base) + source[len(m.SCRATCH):]
                elif m.inside(source, str(m.REPO)):
                    source = str(self.base / 'repo') + source[len(str(m.REPO)):]
                else:
                    source = str(self.base / 'nightly')
                row['Source'] = source
        for cid, obj in self.census()['inspect'].items():
            p = self.base / ('proof-' + cid + '.json')
            expected = self.container_bindings[cid]
            if expected['proof_kind'] == 'image_owner_receipt':
                obj = {'terminal_container_info': obj, 'container_id': cid,
                       'container_name': expected['Name'].lstrip('/'),
                       'owner_nonce': expected['owner_nonce']}
            p.write_text(json.dumps(obj))
            p.chmod(0o600)
            self.container_bindings[cid]['proof'] = {
                'path': str(p), **m.metadata(p.stat()), 'sha256': m.sha(p.read_bytes())}
        self.patches = [mock.patch.object(m, 'git', side_effect=self.git),
                        mock.patch.object(m, 'REPO', self.base),
                        mock.patch.object(m, 'SCRATCH', str(self.base)),
                        mock.patch.object(m, 'LEASES', [str(self.base / 'build-lease'), str(self.base / 'image-lease')]),
                        mock.patch.object(m, 'CONTAINER_BINDINGS', self.container_bindings),
                        mock.patch.object(m, 'collect_census', side_effect=lambda root: self.census())]
        for patch in self.patches:
            patch.start()
            self.addCleanup(patch.stop)

    def seal(self):
        self.plan_path.write_text(json.dumps(self.plan))
        self.plan_path.chmod(0o600)
        self.binding = {'path': str(self.plan_path), **m.metadata(self.plan_path.stat()),
                        'sha256': m.sha(self.plan_path.read_bytes()), 'root': str(self.root),
                        'identity': self.plan['candidate_identity'], 'commit': 'a' * 40,
                        'count': len(self.rows), 'bytes': sum(r['size'] for r in self.rows),
                        'allocated': sum(r['allocated_bytes'] for r in self.rows)}

    def git(self, repo, *args):
        if args == ('rev-parse', 'HEAD'):
            return b'a' * 40 + b'\n'
        if args[0] == 'ls-tree':
            row = next(r for r in self.rows if r['restore_git_path'] == args[-1])
            mode = '100755' if row['mode'] == 0o755 else '100644'
            return (mode + ' blob ' + row['blob'] + '\t' + row['restore_git_path']).encode() + b'\0'
        self.fail('unexpected Git edge')

    def committed(self, commit, path, row):
        self.assertEqual(commit, 'a' * 40)
        self.assertEqual(m.sha(self.source[path]), row['sha256'])

    def validate(self):
        with mock.patch.object(m, 'committed_file', side_effect=self.committed):
            return m.validate_plan(str(self.plan_path), self.binding)

    def transaction(self):
        journal = m.Journal(self.outputs['journal'])
        try:
            return m.transact(self.plan, self.outputs, journal)
        finally:
            journal.close()

    def events(self):
        return [json.loads(x) for x in Path(self.outputs['journal']).read_text().splitlines()]

    def assert_originals(self):
        for r in self.rows:
            with m.opened(r['path']) as fd:
                m.verify_fd(fd, r)

    def census(self):
        dev = self.root.stat().st_dev
        major_minor = str(os.major(dev)) + ':' + str(os.minor(dev))
        scratch = str(self.base)
        root_stat = self.root.stat()
        scratch_stat = self.base.stat()
        pid = os.getpid()
        witnesses = [
            {'pid': pid, 'fd': 100, 'dev': scratch_stat.st_dev, 'ino': scratch_stat.st_ino,
             'access': 'r', 'path': scratch},
            {'pid': pid, 'fd': 101, 'dev': root_stat.st_dev, 'ino': root_stat.st_ino,
             'access': 'r', 'path': str(self.root)},
        ]
        quarantine = self.root / '.planbound-cleanup-test'
        if quarantine.is_dir():
            qstat = quarantine.stat()
            witnesses.append({'pid': pid, 'fd': 102, 'dev': qstat.st_dev, 'ino': qstat.st_ino,
                              'access': 'r', 'path': str(quarantine)})
        for witness in witnesses:
            for fd_path in Path('/proc/self/fd').iterdir():
                try:
                    if os.path.realpath(fd_path) == witness['path']:
                        witness['fd'] = int(fd_path.name)
                        break
                except (OSError, ValueError):
                    pass
        # lsof 4.93.2 emits one ``p`` set followed by newline-framed ``f``
        # records, even when every descriptor belongs to the same process.
        lsof = f"p{pid}\0\n" + ''.join(
            f"f{w['fd']}\0a{w['access']}\0tDIR\0D{hex(w['dev'])}\0"
            f"i{w['ino']}\0n{w['path']}\0\n" for w in witnesses)
        objects = {}
        for cid, expected in self.container_bindings.items():
            objects[cid] = {'Id': cid, 'Name': expected['Name'],
                           'Mounts': copy.deepcopy(expected['Mounts']),
                           'State': copy.deepcopy(expected['State']),
                           'RestartCount': expected['RestartCount'],
                           'Config': {'Labels': {'mckernel.owner': expected['owner_nonce']}},
                           'HostConfig': {'RestartPolicy': {'Name': 'no', 'MaximumRetryCount': 0},
                                          'AutoRemove': False}}
        return {'lsof': {'returncode': 0, 'stdout': lsof, 'stderr': ''},
                'scratch_mount': scratch, 'witnesses': witnesses,
                'findmnt': {'returncode': 0, 'stdout': 'fixture', 'stderr': ''},
                'mountinfo': '1 0 ' + major_minor + ' / ' + str(self.base) + ' rw - ext4 /dev/test rw\n',
                'ids': sorted(objects), 'ids_after': sorted(objects), 'inspect': objects}

    def test_positive_validate_stage_delete_and_git_restoration(self):
        self.validate()
        m.output_paths(self.outputs, self.plan, str(self.base))
        result = self.transaction()
        self.assertEqual(result['status'], 'PASS')
        self.assertEqual(result['states'], ['deleted'] * 3)
        self.assertTrue(all(not Path(r['path']).exists() for r in self.rows))
        self.assertTrue(self.evidence.is_dir())
        self.assertEqual(self.protected.read_bytes(), b'untouchable')
        events = self.events()
        complete = next(i for i, e in enumerate(events) if e['event'] == 'staging-complete')
        self.assertTrue(all(e['event'] not in ('delete-intent', 'deleted') for e in events[:complete]))
        for row in result['restoration']:
            p = Path(row['path'])
            # Git edge provides retained bytes; restoration uses real exclusive writes.
            with m.directory(str(p.parent)) as parent:
                fd = os.open(p.name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                             row['mode'], dir_fd=parent)
                m.write_all(fd, self.source[row['restore_git_path']])
                os.fchmod(fd, row['mode'])
                os.utime(fd, ns=(row['mtime_ns'], row['mtime_ns']))
                os.fsync(fd)
                os.close(fd)
                os.fsync(parent)
            self.assertEqual(p.read_bytes(), self.source[row['restore_git_path']])
            self.assertEqual(stat.S_IMODE(p.stat().st_mode), row['mode'])
            self.assertEqual(p.stat().st_mtime_ns, row['mtime_ns'])

    def test_plan_hash_drift(self):
        self.plan_path.write_text(self.plan_path.read_text() + ' ')
        with self.assertRaises(m.Refusal): self.validate()

    def test_plan_path_drift(self):
        with self.assertRaises(m.Refusal): m.validate_plan(str(self.base / 'wrong'), self.binding)

    def test_plan_schema_status_and_duplicate_targets(self):
        for key, value in [('status', 'PASS'), ('schema', 'other'), ('preserved', [{}]),
                           ('nested_delta_preserved', False)]:
            with self.subTest(key=key):
                old = self.plan[key]
                self.plan[key] = value
                self.seal()
                with self.assertRaises(m.Refusal): self.validate()
                self.plan[key] = old
        self.rows.append(copy.deepcopy(self.rows[0]))
        self.seal()
        with self.assertRaises(m.Refusal): self.validate()

    def test_target_escape(self):
        self.rows[0]['path'] = str(self.protected)
        self.seal()
        with self.assertRaises(m.Refusal): self.validate()

    def test_metadata_drift(self):
        p = Path(self.rows[0]['path'])
        p.chmod(0o600)
        with self.assertRaises(m.Refusal): self.validate()

    def test_content_drift_same_size_mtime(self):
        row = self.rows[0]
        p = Path(row['path'])
        p.write_bytes(b'x' * row['size'])
        os.utime(p, ns=(row['mtime_ns'], row['mtime_ns']))
        with self.assertRaisesRegex(m.Refusal, 'content'): self.validate()

    def test_hardlink(self):
        os.link(self.rows[0]['path'], self.base / 'alias')
        with self.assertRaisesRegex(m.Refusal, 'type-link'): self.validate()

    def test_symlink(self):
        p = Path(self.rows[0]['path'])
        p.unlink()
        p.symlink_to(self.protected)
        with self.assertRaises(OSError): self.validate()

    def test_symlink_ancestor(self):
        moved = self.root / 'moved'
        self.evidence.rename(moved)
        self.evidence.symlink_to(moved, target_is_directory=True)
        with self.assertRaises(OSError): self.validate()

    def test_protected_file_drift(self):
        self.protected.write_bytes(b'replacement')
        with self.assertRaises(m.Refusal): self.validate()

    def test_protected_directory_drift(self):
        self.protected_dir.rename(self.base / 'saved-dir')
        self.protected_dir.mkdir()
        with self.assertRaisesRegex(m.Refusal, 'protected-directory'): self.validate()

    def test_root_and_head_drift(self):
        with mock.patch.object(m, 'git', return_value=b'b' * 40):
            with self.assertRaisesRegex(m.Refusal, 'root-head'): self.validate()
        self.plan['candidate_identity'] = '0:0'
        self.seal()
        with self.assertRaisesRegex(m.Refusal, 'root-identity'): self.validate()

    def test_census_positive_and_open_reference(self):
        c = self.census()
        m.check_census(c, str(self.root))
        c['lsof']['returncode'] = 0
        c['lsof']['stdout'] = 'PID FILE\n'
        with self.assertRaisesRegex(m.Refusal, 'lsof-fields'): m.check_census(c, str(self.root))

    def test_filesystem_census_rejects_rc1_plus_d_and_identity_alias(self):
        c = self.census()
        c['lsof'] = {'returncode': 1, 'stdout': '', 'stderr': ''}
        with self.assertRaisesRegex(m.Refusal, 'open-references-or-incomplete-census'):
            m.check_census(c, str(self.root))
        alias = self.base / 'root-alias'
        alias.symlink_to(self.root, target_is_directory=True)
        st = alias.resolve().stat()
        pid = os.getpid()
        c['lsof'] = {'returncode': 0, 'stdout':
                     f'p{pid}\0\nf9\0ar\0tDIR\0D{hex(st.st_dev)}\0i{st.st_ino}\0n{alias}\0\n',
                     'stderr': ''}
        with self.assertRaisesRegex(m.Refusal, 'lsof-path-alias'):
            m.check_census(c, str(self.root))

    def test_filesystem_census_accepts_outside_non_alias_identity(self):
        c = self.census()
        outside = self.base / 'outside'
        outside.mkdir()
        st = outside.stat()
        pid = os.getpid()
        c['lsof']['stdout'] += (
            f'f10\0ar\0tDIR\0D{hex(st.st_dev)}\0i{st.st_ino}\0n{outside}\0\n')
        m.check_census(c, str(self.root))

    def test_filesystem_census_rejects_strict_record_variants(self):
        c = self.census()
        outside = self.base / 'strict-outside'
        outside.mkdir()
        st = outside.stat()
        pid = os.getpid()
        good = (f'p{pid}\0\nf10\0ar\0tDIR\0D{hex(st.st_dev)}\0i{st.st_ino}\0n{outside}\0\n')
        variants = [
            good[:-1],  # missing final NUL terminator
            f'p{pid}\0\n',  # orphan PID record
            good.replace('tDIR', 'tunknown'),
            good.replace('ar\0', 'arrw-\0'),
        ]
        regular = self.base / 'strict-regular'
        regular.write_bytes(b'x')
        rs = regular.stat()
        variants.append(f'p{pid}\0f10\0ar\0tDIR\0D{hex(rs.st_dev)}\0i{rs.st_ino}\0n{regular}\0')
        alias = self.base / 'strict-alias'
        alias.mkdir()
        nested = alias / 'nested'
        nested.write_bytes(b'x')
        link = self.base / 'strict-link'
        link.symlink_to(alias, target_is_directory=True)
        ns = nested.stat()
        variants.append(f'p{pid}\0f10\0ar\0tREG\0D{hex(ns.st_dev)}\0i{ns.st_ino}\0n{link}/nested\0')
        for payload in variants:
            c['lsof'] = {'returncode': 0, 'stdout': payload, 'stderr': ''}
            with self.subTest(payload=payload), self.assertRaises(m.Refusal):
                m.check_census(c, str(self.root))

    def test_lsof_complete_census_rejects_separator_and_witness_substitutions(self):
        data = self.census()['lsof']['stdout']
        for label, payload in {
                'missing-record-newline': data[:-1],
                'appended-nul': data + '\0',
                'appended-newline': data + '\n',
                'orphan-process': data + 'p999999\0\n',
                'unknown-access': data.replace('ar\0', 'ax\0', 1),
                'unknown-type': data.replace('tDIR\0', 'tUNKNOWN\0', 1),
        }.items():
            c = self.census()
            c['lsof']['stdout'] = payload
            with self.subTest(label=label), self.assertRaises(m.Refusal):
                m.check_census(c, str(self.root))

        c = self.census()
        root_witness = next(w for w in c['witnesses'] if w['path'] == str(self.root))
        scratch_witness = next(w for w in c['witnesses'] if w['path'] == c['scratch_mount'])
        # A different PID/FD may not borrow the root pathname witness.
        c['lsof']['stdout'] += (
            f'p999999\0\nf9\0ar\0tDIR\0D{hex(root_witness["dev"])}\0'
            f'i{root_witness["ino"]}\0n{root_witness["path"]}\0\n')
        with self.assertRaisesRegex(m.Refusal, 'open-references-or-incomplete-census'):
            m.check_census(c, str(self.root))

        c = self.census()
        c['lsof']['stdout'] = c['lsof']['stdout'].replace(
            f'f{root_witness["fd"]}\0', f'f{scratch_witness["fd"]}\0', 1)
        with self.assertRaises(m.Refusal):
            m.check_census(c, str(self.root))

        c = self.census()
        second = dict(root_witness, fd=999)
        c['witnesses'].append(second)
        # Same pathname, distinct descriptor: both witnesses are required.
        with self.assertRaisesRegex(m.Refusal, 'open-references-or-incomplete-census'):
            m.check_census(c, str(self.root))
        c['lsof']['stdout'] += (
            f'f{second["fd"]}\0ar\0tDIR\0D{hex(second["dev"])}\0'
            f'i{second["ino"]}\0n{second["path"]}\0\n')
        m.check_census(c, str(self.root))

    @unittest.skipUnless(shutil.which('lsof'), 'lsof unavailable')
    def test_real_unprivileged_lsof_493_nul_newline_grammar(self):
        # This deliberately bypasses Docker/root census collection.  It binds
        # a genuine descriptor, captures lsof 4.93.2 output, and then mutates
        # the complete valid record rather than testing a hand-written fragment.
        with m.directory(str(self.base)) as scratch_fd, m.directory(str(self.root)) as root_fd:
            owned = m.pinned_references((scratch_fd, str(self.base)), (root_fd, str(self.root)))
            captured = m.run(['lsof', '-nP', '-w', '-F0pfaDint', '--', str(self.root)])
            self.assertEqual(captured['returncode'], 0, captured['stderr'])
            self.assertTrue(captured['stdout'].startswith(f'p{os.getpid()}\0\nf{root_fd}\0'))
            self.assertIn('\0\n', captured['stdout'])
            # The command scoped to root observes the root descriptor only;
            # scratch is deliberately not declared to this direct parser test.
            root_only = (owned[1],)
            m.check_lsof(captured, root_only, str(self.root), str(self.base))
            for label, payload in {
                    'extra-nul': captured['stdout'] + '\0',
                    'extra-newline': captured['stdout'] + '\n',
                    'orphan-process': captured['stdout'] + 'p999999\0\n',
                    'access': captured['stdout'].replace('ar\0', 'aw\0', 1),
                    'type': captured['stdout'].replace('tDIR\0', 'tREG\0', 1),
                    'path': captured['stdout'].replace(f'n{self.root}\0', f'n{self.base}\0', 1),
            }.items():
                bad = dict(captured, stdout=payload)
                with self.subTest(label=label), self.assertRaises(m.Refusal):
                    m.check_lsof(bad, root_only, str(self.root), str(self.base))

    def test_mount_descendant_and_alias(self):
        dev = self.root.stat().st_dev
        major_minor = str(os.major(dev)) + ':' + str(os.minor(dev))
        for mount in [('7:40', str(self.evidence)), (major_minor, str(self.base / 'alias'))]:
            c = self.census()
            c['mountinfo'] += '2 1 ' + mount[0] + ' / ' + mount[1] + ' rw - ext4 /dev/test rw\n'
            with self.subTest(mount=mount), self.assertRaises(m.Refusal):
                m.check_census(c, str(self.root))

    def test_container_all_retained_terminal_fields(self):
        values = {'Status': 'running', 'Pid': 1, 'ExitCode': 0, 'Running': True,
                  'Paused': True, 'Restarting': True, 'Dead': True, 'OOMKilled': True}
        for key, value in values.items():
            c = self.census()
            c['inspect'][m.CONTAINER]['State'][key] = value
            with self.subTest(key=key), self.assertRaises(m.Refusal):
                m.check_census(c, str(self.root))
        for key, value in [('AutoRemove', True), ('RestartPolicy', {'Name': 'always', 'MaximumRetryCount': 0})]:
            c = self.census()
            c['inspect'][m.CONTAINER]['HostConfig'][key] = value
            with self.subTest(key=key), self.assertRaises(m.Refusal): m.check_census(c, str(self.root))

    def test_other_container_full_mount_source_even_exited(self):
        for source in (str(self.root), str(self.base), str(self.evidence)):
            c = self.census()
            cid = 'f' * 64
            obj = copy.deepcopy(c['inspect'][m.CONTAINER])
            obj['Id'] = cid
            obj['Mounts'][0]['Source'] = source
            c['ids'].append(cid)
            c['ids_after'].append(cid)
            c['inspect'][cid] = obj
            with self.subTest(source=source), self.assertRaises(m.Refusal):
                m.check_census(c, str(self.root))

    def test_container_symlink_alias(self):
        alias = self.base / 'alias'
        alias.symlink_to(self.root, target_is_directory=True)
        c = self.census()
        c['inspect'][m.CONTAINER]['Mounts'][0]['Source'] = str(alias)
        with self.assertRaisesRegex(m.Refusal, 'unknown-alias'): m.check_census(c, str(self.root))

    def test_container_set_changes(self):
        c = self.census()
        c['ids_after'] = []
        with self.assertRaisesRegex(m.Refusal, 'set-changed'): m.check_census(c, str(self.root))

    def test_collision_does_not_overwrite(self):
        Path(self.outputs['receipt']).write_bytes(b'original')
        with self.assertRaises(m.Refusal): m.output_paths(self.outputs, self.plan, str(self.base))
        with self.assertRaises(FileExistsError): m.publish(self.outputs['receipt'], {})
        self.assertEqual(Path(self.outputs['receipt']).read_bytes(), b'original')

    def test_short_writes(self):
        original = os.write
        def short(fd, data): return original(fd, data[:3])
        with mock.patch.object(m.os, 'write', side_effect=short):
            result = self.transaction()
        self.assertEqual(result['status'], 'PASS')
        self.assertEqual(self.events()[-1]['event'], 'complete')

    def test_zero_write(self):
        with mock.patch.object(m.os, 'write', return_value=0):
            with self.assertRaisesRegex(m.Refusal, 'short-write-zero'):
                m.publish(self.outputs['receipt'], {'data': 1})
        self.assert_originals()

    def test_fsync_before_rename_preserves_originals(self):
        original = m.Journal.append
        def fail_intent(journal, row):
            if row['event'] == 'stage-intent':
                with mock.patch.object(m.os, 'fsync', side_effect=OSError('injected')):
                    return original(journal, row)
            return original(journal, row)
        with mock.patch.object(m.Journal, 'append', fail_intent):
            result = self.transaction()
        self.assertEqual(result['status'], 'FAIL')
        self.assertEqual(result['states'], ['original'] * 3)
        self.assert_originals()

    def test_fsync_after_rename_rolls_back(self):
        original = os.fsync
        failed = False
        def fail_after(fd):
            nonlocal failed
            if Path(self.outputs['quarantine'], '0').exists() and not failed:
                failed = True
                raise OSError('injected')
            return original(fd)
        with mock.patch.object(m.os, 'fsync', side_effect=fail_after):
            result = self.transaction()
        self.assertEqual(result['states'], ['restored', 'original', 'original'])
        self.assert_originals()

    def test_staging_failure_rolls_back_in_reverse(self):
        original = m.Journal.append
        def fail_third(journal, row):
            if row['event'] == 'stage-intent' and row['index'] == 2:
                raise OSError('injected')
            return original(journal, row)
        with mock.patch.object(m.Journal, 'append', fail_third): result = self.transaction()
        self.assertEqual(result['states'], ['restored', 'restored', 'original'])
        self.assertEqual([r['index'] for r in result['rollback'] if r.get('status') == 'restored'], [1, 0])
        self.assert_originals()

    def test_rename_source_replacement_detected_without_deletion(self):
        original = m.Journal.append
        saved = self.base / 'saved-original'
        def replace(journal, row):
            value = original(journal, row)
            if row['event'] == 'stage-intent' and row['index'] == 0:
                p = Path(self.rows[0]['path'])
                p.rename(saved)
                p.write_bytes(b'replaced')
            return value
        with mock.patch.object(m.Journal, 'append', replace): result = self.transaction()
        self.assertEqual(result['status'], 'FAIL')
        self.assertEqual(result['states'][0], 'stage-uncertain')
        self.assertEqual(saved.read_bytes(), self.source[self.rows[0]['restore_git_path']])
        self.assertEqual(Path(self.outputs['quarantine'], '0').read_bytes(), b'replaced')
        self.assertFalse(any(e['event'] == 'deleted' for e in self.events()))

    def test_stage_destination_collision_preserved(self):
        original = m.Journal.append
        def collide(journal, row):
            value = original(journal, row)
            if row['event'] == 'stage-intent' and row['index'] == 0:
                Path(self.outputs['quarantine'], '0').write_bytes(b'collision')
            return value
        with mock.patch.object(m.Journal, 'append', collide): result = self.transaction()
        self.assertEqual(result['states'], ['stage-uncertain', 'original', 'original'])
        self.assertEqual(Path(self.outputs['quarantine'], '0').read_bytes(), b'collision')
        self.assert_originals()

    def test_partial_delete_accurate_attempted_and_staged(self):
        original = m.Journal.append
        def fail_second(journal, row):
            if row['event'] == 'delete-intent' and row['index'] == 1:
                raise OSError('injected')
            return original(journal, row)
        with mock.patch.object(m.Journal, 'append', fail_second): result = self.transaction()
        self.assertEqual(result['status'], 'FAIL')
        self.assertEqual(result['phase'], 'deleting')
        self.assertEqual(result['attempted'], 1)
        self.assertEqual(result['states'], ['deleted', 'staged', 'staged'])
        self.assertFalse(Path(self.outputs['quarantine'], '0').exists())
        self.assertTrue(Path(self.outputs['quarantine'], '1').exists())
        self.assertEqual(len(result['restoration']), 3)

    def test_fsync_after_unlink_records_nondurable_deletion(self):
        original = os.fsync
        failed = False
        def fail_delete(fd):
            nonlocal failed
            q = Path(self.outputs['quarantine'])
            if q.exists() and (q / '1').exists() and not (q / '0').exists() and not failed:
                failed = True
                raise OSError('injected')
            return original(fd)
        with mock.patch.object(m.os, 'fsync', side_effect=fail_delete): result = self.transaction()
        self.assertEqual(result['states'], ['deleted-not-durable', 'staged', 'staged'])
        self.assertEqual(result['attempted'], 0)

    def test_missing_release_blocks_before_mutation(self):
        with self.assertRaisesRegex(m.Refusal, 'release-required'):
            m.execute(str(self.plan_path), None, None, self.outputs, [])
        self.assert_originals()
        self.assertFalse(Path(self.outputs['journal']).exists())

    def release_fixture(self):
        tool = self.base / m.TOOL_PATH
        tool.parent.mkdir(parents=True, exist_ok=True)
        tool.write_bytes(b'exact tool')
        path = self.base / 'docs/verification/release.json'
        release = {'schema': 'mckernel.candidate12-cleanup-release.v1', 'status': 'PASS',
                   'finalization': 'PASS', 'source_commit': 'a' * 40,
                   'tool_sha256': m.sha(tool.read_bytes()), 'tool_blob': 'c' * 40,
                   'plan': self.binding, 'command': ['python', 'tool', '--execute'],
                   'outputs': self.outputs, 'absent_leases': m.LEASES,
                   'dispatcher_exclusive': True, 'retained_containers': m.CONTAINER_BINDINGS}
        path.write_text(json.dumps(release))
        def git(repo, *args):
            if args[0] == 'merge-base': return b''
            if args[0] == 'show':
                return path.read_bytes() if args[1].endswith('release.json') else tool.read_bytes()
            if args[0] == 'rev-parse': return b'c' * 40 + b'\n'
            self.fail('unexpected release Git edge')
        return path, release, git

    def test_release_positive_and_wrong_bindings(self):
        path, release, git = self.release_fixture()
        with mock.patch.object(m, 'git', side_effect=git):
            m.validate_release(str(path), 'b' * 40, self.outputs,
                               release['command'], self.binding)
            for key, value in [('status', 'DRAFT'), ('finalization', 'FAIL'),
                               ('tool_sha256', '0' * 64), ('tool_blob', '0' * 40),
                               ('source_commit', 'b' * 40), ('command', []),
                               ('outputs', {}), ('plan', {}), ('absent_leases', []),
                               ('retained_containers', {}),
                               ('dispatcher_exclusive', False)]:
                changed = dict(release, **{key: value})
                path.write_text(json.dumps(changed))
                with self.subTest(key=key), self.assertRaises(m.Refusal):
                    m.validate_release(str(path), 'b' * 40, self.outputs,
                                       release['command'], self.binding)

    def test_release_not_fetched_or_not_committed(self):
        path, release, git = self.release_fixture()
        with mock.patch.object(m, 'git', side_effect=m.Refusal('not-fetched')):
            with self.assertRaises(m.Refusal):
                m.validate_release(str(path), 'b' * 40, self.outputs, release['command'], self.binding)
        def wrong(repo, *args):
            if args[0] == 'show' and args[1].endswith('release.json'): return b'{}'
            return git(repo, *args)
        with mock.patch.object(m, 'git', side_effect=wrong):
            with self.assertRaisesRegex(m.Refusal, 'not-committed'):
                m.validate_release(str(path), 'b' * 40, self.outputs, release['command'], self.binding)

    def test_actual_git_blob_and_mode(self):
        repo = self.base / 'git'
        repo.mkdir()
        with mock.patch.object(m, 'git', REAL_GIT), mock.patch.object(m, 'REPO', repo):
            m.git(repo, 'init', '-q')
            m.git(repo, 'config', 'user.email', 'fixture@example.invalid')
            m.git(repo, 'config', 'user.name', 'Fixture')
            for row in self.rows:
                p = repo / row['restore_git_path']
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_bytes(self.source[row['restore_git_path']])
                p.chmod(row['mode'])
            m.git(repo, 'add', '.')
            m.git(repo, 'commit', '-qm', 'fixture')
            commit = m.git(repo, 'rev-parse', 'HEAD').decode().strip()
            for row in self.rows:
                m.committed_file(commit, row['restore_git_path'], row)
            wrong = dict(self.rows[0], mode=0o755)
            with self.assertRaisesRegex(m.Refusal, 'identity-mode'):
                m.committed_file(commit, wrong['restore_git_path'], wrong)
            wrong = dict(self.rows[0], sha256='0' * 64)
            with self.assertRaisesRegex(m.Refusal, 'git-content'):
                m.committed_file(commit, wrong['restore_git_path'], wrong)

    def test_exact_tree_rejects_unlisted_regular(self):
        (self.evidence / 'unlisted').write_bytes(b'preserve')
        with self.assertRaisesRegex(m.Refusal, 'subtree-set'): self.validate()
        self.assert_originals()

    def test_exact_tree_rejects_extra_empty_directory(self):
        (self.evidence / 'unlisted-empty').mkdir()
        with self.assertRaisesRegex(m.Refusal, 'subtree-set'): self.validate()

    def test_exact_tree_rejects_unlisted_symlink_and_fifo(self):
        p = self.evidence / 'unlisted'
        p.symlink_to(self.protected)
        with self.assertRaisesRegex(m.Refusal, 'special-or-symlink'): self.validate()
        p.unlink()
        os.mkfifo(p)
        with self.assertRaisesRegex(m.Refusal, 'special-or-symlink'): self.validate()

    def test_exact_tree_allows_only_derived_nested_directories(self):
        row = self.rows[0]
        p = self.evidence / 'nested/deeper/file-0'
        p.parent.mkdir(parents=True)
        Path(row['path']).rename(p)
        row['path'] = str(p)
        old = row['restore_git_path']
        row['restore_git_path'] = str(p.relative_to(self.root))
        self.source[row['restore_git_path']] = self.source.pop(old)
        self.seal()
        self.validate()
        result = self.transaction()
        self.assertEqual(result['status'], 'PASS')
        self.assertTrue(p.parent.is_dir())

    def test_post_staging_original_tree_rejects_new_file(self):
        original = m.Journal.append
        def extra(journal, row):
            value = original(journal, row)
            if row['event'] == 'staging-complete':
                (self.evidence / 'new-unlisted').write_bytes(b'preserve')
            return value
        with mock.patch.object(m.Journal, 'append', extra): result = self.transaction()
        self.assertEqual(result['status'], 'FAIL')
        self.assertEqual(result['phase'], 'staged-admission')
        self.assertEqual(result['states'], ['staged'] * 3)
        self.assertFalse(any(e['event'] == 'delete-intent' for e in self.events()))

    def test_post_staging_quarantine_rejects_extra_file(self):
        original = m.Journal.append
        def extra(journal, row):
            value = original(journal, row)
            if row['event'] == 'staging-complete':
                Path(self.outputs['quarantine'], 'extra').write_bytes(b'preserve')
            return value
        with mock.patch.object(m.Journal, 'append', extra): result = self.transaction()
        self.assertEqual(result['error'], 'quarantine-set')
        self.assertEqual(result['states'], ['staged'] * 3)
        self.assertFalse(any(e['event'] == 'delete-intent' for e in self.events()))

    def execute_fixture(self, collector):
        with mock.patch.object(m, 'BINDING', self.binding), \
             mock.patch.object(m, 'MUTEX', str(self.base / 'mutex')), \
             mock.patch.object(m, 'validate_release', return_value={'absent_leases': m.LEASES}), \
             mock.patch.object(m, 'committed_file', side_effect=self.committed), \
             mock.patch.object(m, 'collect_census', side_effect=collector) as census:
            result = m.execute(str(self.plan_path), 'release-edge', 'b' * 40, self.outputs, [])
            return result, census.call_count

    def test_execute_collects_two_censuses_before_delete(self):
        result, calls = self.execute_fixture(lambda root: self.census())
        self.assertEqual(result['status'], 'PASS')
        self.assertEqual(calls, 3)
        events = [e['event'] for e in self.events()]
        self.assertLess(events.index('staging-complete'), events.index('post-staging-census'))
        self.assertLess(events.index('post-staging-census'), events.index('irreversible-delete-admitted'))
        self.assertLess(events.index('irreversible-delete-admitted'), events.index('delete-intent'))
        self.assertLess(max(i for i, name in enumerate(events) if name == 'deleted'), events.index('final-census'))

    def post_stage_drift(self, kind):
        calls = 0
        def collector(root):
            nonlocal calls
            calls += 1
            c = self.census()
            if calls == 2:
                if kind == 'process':
                    c['lsof'] = {'returncode': 0, 'stderr': '', 'stdout': 'p999999\0f4\0ar\0tREG\0D0x727\0i1\0nfile\0\n'}
                elif kind == 'container':
                    cid = 'f' * 64
                    c['inspect'][cid] = copy.deepcopy(c['inspect'][m.HOST_CONTAINER])
                    c['inspect'][cid]['Id'] = cid
                    c['ids'].append(cid)
                    c['ids_after'].append(cid)
                elif kind == 'lease':
                    Path(m.LEASES[0]).write_bytes(b'new owner')
                elif kind == 'protected':
                    self.protected.write_bytes(b'changed after staging')
            return c
        result, calls = self.execute_fixture(collector)
        self.assertEqual(calls, 2)
        self.assertEqual(result['status'], 'FAIL')
        self.assertEqual(result['phase'], 'staged-admission')
        self.assertEqual(result['states'], ['staged'] * 3)
        self.assertFalse(any(e['event'] in ('delete-intent', 'deleted') for e in self.events()))
        with m.directory(self.outputs['quarantine']) as fd:
            for i, row in enumerate(self.rows): m.verify_name(fd, str(i), row)

    def test_post_staging_process_blocks_without_deletion(self): self.post_stage_drift('process')

    def test_post_staging_container_blocks_without_deletion(self): self.post_stage_drift('container')

    def test_post_staging_lease_blocks_without_deletion(self): self.post_stage_drift('lease')

    def test_post_staging_protected_drift_blocks_without_deletion(self): self.post_stage_drift('protected')

    def test_narrow_self_directory_fd_admission(self):
        with m.directory(str(self.root)) as fd:
            owned = m.pinned_references((fd, str(self.root)))
            r = owned[0]
            c = self.census()
            data = (f"p{r['pid']}\0\nf{fd}\0ar\0tDIR\0D{hex(r['dev'])}\0i{r['ino']}\0n{self.root}\0\n")
            sw = next(w for w in c['witnesses'] if w['path'] == c['scratch_mount'])
            data += (f"f{sw['fd']}\0ar\0tDIR\0D{hex(sw['dev'])}\0"
                     f"i{sw['ino']}\0n{sw['path']}\0\n")
            c['lsof'] = {'returncode': 0, 'stdout': data, 'stderr': ''}
            m.check_census(c, str(self.root), owned)
            for old, new in [(f"p{r['pid']}", 'p999999'), (f'f{fd}', f'f{fd + 500}'),
                             ('ar', 'aw'), ('tDIR', 'tREG'),
                             (f"D{hex(r['dev'])}", 'D0x0'), (f"i{r['ino']}", 'i0'),
                             (f'n{self.root}', 'n/wrong')]:
                c['lsof']['stdout'] = data.replace(old, new)
                with self.subTest(field=old), self.assertRaises(m.Refusal):
                    m.check_census(c, str(self.root), owned)
            c['lsof']['stdout'] = data + data
            with self.assertRaisesRegex(m.Refusal, 'lsof-fields'):
                m.check_census(c, str(self.root), owned)

    def test_host_container_required_and_terminal(self):
        c = self.census()
        c['ids'].remove(m.HOST_CONTAINER)
        c['ids_after'].remove(m.HOST_CONTAINER)
        del c['inspect'][m.HOST_CONTAINER]
        with self.assertRaisesRegex(m.Refusal, 'retained-container-absent'): m.check_census(c, str(self.root))
        for key, value in [('ExitCode', 1), ('Pid', 9), ('Paused', True), ('OOMKilled', True)]:
            c = self.census()
            c['inspect'][m.HOST_CONTAINER]['State'][key] = value
            with self.subTest(key=key), self.assertRaises(m.Refusal): m.check_census(c, str(self.root))

    def test_exact_mount_bindings_for_both_containers(self):
        for cid in (m.CONTAINER, m.HOST_CONTAINER):
            for key, value in [('Source', str(self.base)), ('Destination', '/wrong'),
                               ('RW', True), ('Type', 'volume')]:
                c = self.census()
                c['inspect'][cid]['Mounts'][0][key] = (
                    not c['inspect'][cid]['Mounts'][0][key] if key == 'RW' else value)
                with self.subTest(cid=cid, key=key), self.assertRaises(m.Refusal):
                    m.check_census(c, str(self.root))
            c = self.census()
            c['inspect'][cid]['Mounts'].append(m.mount(str(self.protected_dir), '/extra'))
            with self.assertRaises(m.Refusal): m.check_census(c, str(self.root))

    def test_container_proof_hash_drift(self):
        proof = self.container_bindings[m.HOST_CONTAINER]['proof']
        Path(proof['path']).write_bytes(b'forged')
        with self.assertRaises(m.Refusal): m.check_census(self.census(), str(self.root))

    def test_forward_rename_post_syscall_interrupt_restores(self):
        rename = m.rename_noreplace
        done = False
        def interrupt(srcfd, src, dstfd, dst):
            nonlocal done
            rename(srcfd, src, dstfd, dst)
            if not done:
                done = True
                raise KeyboardInterrupt()
        with mock.patch.object(m, 'rename_noreplace', side_effect=interrupt): result = self.transaction()
        self.assertEqual(result['states'], ['restored', 'original', 'original'])
        self.assertEqual(result['error'], 'KeyboardInterrupt')
        self.assertTrue(result['interrupted'])
        self.assert_originals()
        reconciliation = next(e for e in self.events() if e['event'] == 'stage-reconciled')
        self.assertEqual(reconciliation['locations'], {'source': 'missing', 'quarantine': 'expected'})
        self.assertEqual(self.events()[2]['state'], 'stage-uncertain')

    def test_rollback_rename_post_syscall_interrupt_reconciles(self):
        rename = m.rename_noreplace
        journal_append = m.Journal.append
        def fail_stage(journal, row):
            if row['event'] == 'stage-intent' and row['index'] == 1:
                raise OSError('injected stage failure')
            return journal_append(journal, row)
        def interrupt_restore(srcfd, src, dstfd, dst):
            rename(srcfd, src, dstfd, dst)
            if dst == 'file-0': raise KeyboardInterrupt()
        with mock.patch.object(m.Journal, 'append', fail_stage), \
             mock.patch.object(m, 'rename_noreplace', side_effect=interrupt_restore):
            result = self.transaction()
        self.assertEqual(result['states'], ['restored', 'original', 'original'])
        self.assertTrue(result['interrupted'])
        self.assert_originals()
        record = next(e for e in self.events() if e['event'] == 'rollback-reconciled')
        self.assertEqual(record['state'], 'restored')
        self.assertEqual(record['error'], 'KeyboardInterrupt')
        self.assertEqual(record['locations'], {'source': 'expected', 'quarantine': 'missing'})
        intent = next(e for e in self.events() if e['event'] == 'rollback-intent')
        self.assertEqual(intent['state'], 'restore-uncertain')

    def test_post_syscall_wrong_source_is_uncertain_not_original(self):
        rename = m.rename_noreplace
        def interfere(srcfd, src, dstfd, dst):
            rename(srcfd, src, dstfd, dst)
            Path(self.rows[0]['path']).write_bytes(b'foreign replacement')
            raise KeyboardInterrupt()
        with mock.patch.object(m, 'rename_noreplace', side_effect=interfere): result = self.transaction()
        self.assertEqual(result['states'][0], 'stage-uncertain')
        self.assertTrue(result['interrupted'])
        self.assertEqual(Path(self.rows[0]['path']).read_bytes(), b'foreign replacement')
        self.assertEqual(Path(self.outputs['quarantine'], '0').read_bytes(), self.source[self.rows[0]['restore_git_path']])
        record = next(e for e in self.events() if e['event'] == 'stage-reconciled')
        self.assertEqual(record['locations'], {'source': 'wrong-or-unreadable', 'quarantine': 'expected'})

    def unwind_interruption(self, stage, close_target):
        close = os.close
        append = m.Journal.append
        armed = False
        fired = False
        calls = 0
        expected = {'staged': ['staged'] * 3,
                    'partial': ['deleted', 'staged', 'staged'],
                    'complete': ['deleted'] * 3}[stage]
        target = str(self.root) if close_target == 'root' else self.outputs['quarantine']

        def collector(root):
            nonlocal calls, armed
            calls += 1
            c = self.census()
            if stage == 'staged' and calls == 2:
                # A genuine post-staging admission failure starts unwinding;
                # then the real close syscall succeeds just before SIGINT.
                c['lsof']['stderr'] = 'fixture observer unavailable'
                armed = True
            return c

        def record(journal, row):
            nonlocal armed
            if stage == 'partial' and row.get('event') == 'delete-intent' and row['index'] == 1:
                armed = True
                raise OSError('fixture stop after first deletion')
            value = append(journal, row)
            if stage == 'complete' and row.get('event') == 'complete':
                armed = True
            return value

        def interrupted_close(fd):
            nonlocal fired
            # Examine the real descriptor, then perform the real close. No
            # filesystem mutation is mocked, including the successful syscall.
            hit = armed and not fired and os.readlink('/proc/self/fd/' + str(fd)) == target
            close(fd)
            if hit:
                fired = True
                raise KeyboardInterrupt()

        with mock.patch.object(m.os, 'close', side_effect=interrupted_close), \
             mock.patch.object(m.Journal, 'append', record):
            result, count = self.execute_fixture(collector)
        self.assertTrue(fired)
        self.assertEqual(count, 3 if stage == 'complete' else 2)
        self.assertEqual(result['status'], 'FAIL')
        self.assertEqual(result['states'], expected)
        self.assertNotEqual(result['phase'], 'preflight')
        self.assertEqual(result['error'], 'KeyboardInterrupt')
        self.assertTrue(result['interrupted'])
        self.assertTrue(result['escaped_after_transaction_entry'])
        receipt = json.loads(Path(self.outputs['receipt']).read_text())
        self.assertEqual(receipt, result)
        self.assertEqual(json.loads(Path(self.outputs['status']).read_text())['status'], 'FAIL')
        self.assertEqual(self.events()[-1]['event'], 'transaction-unwind-failure')
        self.assertFalse(any(e.get('phase') == 'preflight' for e in self.events()))
        for i, state in enumerate(expected):
            self.assertFalse(Path(self.rows[i]['path']).exists())
            q = Path(self.outputs['quarantine'], str(i))
            if state == 'deleted':
                self.assertFalse(q.exists())
            else:
                with m.opened(str(q)) as fd: m.verify_fd(fd, self.rows[i])

    def test_execute_staged_quarantine_close_interruption(self):
        self.unwind_interruption('staged', 'quarantine')

    def test_execute_staged_root_unwinding_interruption(self):
        self.unwind_interruption('staged', 'root')

    def test_execute_partial_delete_quarantine_close_interruption(self):
        self.unwind_interruption('partial', 'quarantine')

    def test_execute_partial_delete_root_unwinding_interruption(self):
        self.unwind_interruption('partial', 'root')

    def test_execute_complete_quarantine_close_interruption(self):
        self.unwind_interruption('complete', 'quarantine')

    def test_execute_complete_root_unwinding_interruption(self):
        self.unwind_interruption('complete', 'root')

    def test_execute_escaped_transaction_return_retains_shared_result(self):
        transact = m.transact
        def interrupted_return(plan, outputs, journal, progress):
            result = transact(plan, outputs, journal, progress)
            self.assertEqual(result['status'], 'PASS')
            raise KeyboardInterrupt()
        with mock.patch.object(m, 'transact', side_effect=interrupted_return):
            result, count = self.execute_fixture(lambda root: self.census())
        self.assertEqual(count, 3)
        self.assertEqual(result['states'], ['deleted'] * 3)
        self.assertEqual(result['phase'], 'complete')
        self.assertTrue(result['interrupted'])
        self.assertEqual(result['prior_status'], 'PASS')
        self.assertEqual(json.loads(Path(self.outputs['receipt']).read_text()), result)
        self.assertFalse(any(e.get('phase') == 'preflight' for e in self.events()))

    def test_execute_escape_before_transaction_initialization_is_uncertain(self):
        with mock.patch.object(m, 'transact', side_effect=KeyboardInterrupt()):
            result, count = self.execute_fixture(lambda root: self.census())
        self.assertEqual(count, 1)
        self.assertEqual(result['phase'], 'transaction-entered')
        self.assertEqual(result['states'], ['transaction-uncertain'] * 3)
        self.assertTrue(result['interrupted'])
        self.assert_originals()
        self.assertEqual(json.loads(Path(self.outputs['receipt']).read_text()), result)

    def test_exact_six_inventory_passes_unordered_mounts(self):
        self.assertEqual(len(self.container_bindings), 6)
        self.assertEqual({r['proof_kind'] for r in self.container_bindings.values()},
                         {'image_owner_receipt', 'docker_inspect'})
        c = self.census()
        for obj in c['inspect'].values(): obj['Mounts'].reverse()
        m.check_census(c, str(self.root))
        def collector(root):
            value = self.census()
            for obj in value['inspect'].values(): obj['Mounts'].reverse()
            return value
        result, count = self.execute_fixture(collector)
        self.assertEqual(result['status'], 'PASS')
        self.assertEqual(count, 3)
        self.assertEqual(result['states'], ['deleted'] * 3)

    def test_each_of_six_missing_is_rejected(self):
        for cid in self.container_bindings:
            c = self.census()
            del c['inspect'][cid]
            c['ids'].remove(cid)
            c['ids_after'].remove(cid)
            with self.subTest(cid=cid), self.assertRaisesRegex(m.Refusal, 'retained-container-absent'):
                m.check_census(c, str(self.root))

    def test_all_six_owner_nonce_and_restart_count_drift(self):
        for cid in self.container_bindings:
            for field, value in [('owner_nonce', 'unrecognized-owner'), ('RestartCount', 1),
                                 ('RestartCount', False)]:
                c = self.census()
                if field == 'owner_nonce':
                    c['inspect'][cid]['Config']['Labels']['mckernel.owner'] = value
                else:
                    c['inspect'][cid][field] = value
                with self.subTest(cid=cid, field=field, value=value), self.assertRaises(m.Refusal):
                    m.check_census(c, str(self.root))

    def test_all_six_full_state_and_full_mount_drift(self):
        for cid in self.container_bindings:
            for field in ('StartedAt', 'FinishedAt', 'Error'):
                c = self.census()
                c['inspect'][cid]['State'][field] = 'changed'
                with self.subTest(cid=cid, field=field), self.assertRaises(m.Refusal):
                    m.check_census(c, str(self.root))
            for field, value in [('Mode', 'rw'), ('Propagation', 'shared'), ('unexpected', True)]:
                c = self.census()
                c['inspect'][cid]['Mounts'][0][field] = value
                with self.subTest(cid=cid, field=field), self.assertRaises(m.Refusal):
                    m.check_census(c, str(self.root))
            c = self.census()
            c['inspect'][cid]['State']['unexpected'] = 'state'
            with self.assertRaises(m.Refusal): m.check_census(c, str(self.root))

    def test_seventh_candidate_intersection_rejected_unrelated_allowed(self):
        c = self.census()
        cid = 'e' * 64
        c['inspect'][cid] = copy.deepcopy(c['inspect'][m.CONTAINER])
        c['inspect'][cid]['Id'] = cid
        c['ids'].append(cid)
        c['ids_after'].append(cid)
        with self.assertRaisesRegex(m.Refusal, 'container-intersection'):
            m.check_census(c, str(self.root))
        c['inspect'][cid]['Mounts'] = [m.mount(str(self.protected_dir), '/unrelated')]
        m.check_census(c, str(self.root))

    def test_generic_proof_loader_rejects_kind_and_owner_mismatch(self):
        for cid, expected in self.container_bindings.items():
            original_kind = expected['proof_kind']
            expected['proof_kind'] = 'unsupported-kind'
            with self.subTest(cid=cid), self.assertRaisesRegex(m.Refusal, 'container-proof-kind'):
                m.validate_container_proofs()
            expected['proof_kind'] = original_kind
        cid = next(cid for cid, r in self.container_bindings.items()
                   if cid != m.CONTAINER and r['proof_kind'] == 'image_owner_receipt')
        expected = self.container_bindings[cid]
        p = Path(expected['proof']['path'])
        obj = json.loads(p.read_text())
        obj['owner_nonce'] = 'mismatched-top-level-owner'
        p.write_text(json.dumps(obj))
        expected['proof'].update(m.metadata(p.stat()), sha256=m.sha(p.read_bytes()))
        with self.assertRaisesRegex(m.Refusal, 'container-owner-proof'):
            m.validate_container_proofs()

    def test_all_six_proof_bytes_are_bound(self):
        for cid, expected in self.container_bindings.items():
            p = Path(expected['proof']['path'])
            data, stamp = p.read_bytes(), p.stat().st_mtime_ns
            p.write_bytes(b'x' * len(data))
            os.utime(p, ns=(stamp, stamp))
            with self.subTest(cid=cid), self.assertRaisesRegex(m.Refusal, 'file-content'):
                m.validate_container_proofs()
            p.write_bytes(data)
            os.utime(p, ns=(stamp, stamp))

    def test_collector_retains_only_owner_label_and_restart_count(self):
        c = self.census()
        def run(argv):
            result = {'argv': argv, 'returncode': 0, 'stdout': '', 'stderr': ''}
            if argv[2:5] == ['docker', 'ps', '-aq']:
                result['stdout'] = '\n'.join(c['ids']) + '\n'
            elif argv[2:4] == ['docker', 'inspect']:
                obj = copy.deepcopy(c['inspect'][argv[-1]])
                obj['Config']['Env'] = ['fixture-unrelated-env']
                obj['Config']['Labels']['unrelated'] = 'fixture-unrelated-label'
                result['stdout'] = json.dumps([obj])
            elif 'lsof' in argv:
                result['stdout'] = c['lsof']['stdout']
            elif argv[0] == 'findmnt':
                result['stdout'] = str(self.base) + '\n'
            else:
                self.fail('unexpected census command')
            return result
        with mock.patch.object(m, 'run', side_effect=run):
            collected = REAL_COLLECT_CENSUS(str(self.root))
        self.assertEqual(len(collected['inspect']), 6)
        for cid, obj in collected['inspect'].items():
            self.assertEqual(obj['Config'], {'Labels': {
                'mckernel.owner': self.container_bindings[cid]['owner_nonce']}})
            self.assertEqual(obj['RestartCount'], 0)
        self.assertNotIn('fixture-unrelated', json.dumps(collected))

    def test_final_current_census_rejects_changed_owner_preserving_deleted_states(self):
        calls = 0
        def collector(root):
            nonlocal calls
            calls += 1
            c = self.census()
            if calls == 3:
                c['inspect'][m.CONTAINER]['Config']['Labels']['mckernel.owner'] = 'changed'
            return c
        result, count = self.execute_fixture(collector)
        self.assertEqual(count, 3)
        self.assertEqual(result['status'], 'FAIL')
        self.assertEqual(result['phase'], 'deleting')
        self.assertEqual(result['states'], ['deleted'] * 3)
        self.assertEqual(result['error'], 'container-terminal-binding')
        self.assertTrue(any(e['event'] == 'final-census' for e in self.events()))
        self.assertEqual(json.loads(Path(self.outputs['receipt']).read_text()), result)

    def test_sixth_container_drift_blocks_initial_preflight(self):
        def collector(root):
            c = self.census()
            cid = next(k for k in c['ids'] if k not in (m.CONTAINER, m.HOST_CONTAINER))
            c['inspect'][cid]['RestartCount'] = 1
            return c
        result, count = self.execute_fixture(collector)
        self.assertEqual(count, 1)
        self.assertEqual(result['phase'], 'preflight')
        self.assertEqual(result['states'], ['original'] * 3)
        self.assertFalse(Path(self.outputs['quarantine']).exists())
        self.assert_originals()


class RecoveryFixture(Fixture):
    """A tiny, exact-shaped attempt-2 fixture; it never opens real scratch."""
    def recovery_census(self, root):
        c = self.census()
        seen = {w['fd'] for w in c['witnesses']}
        # Enumerate actual retained descriptors, independently of the helper's
        # declaration. A omitted duplicate/ancestor must fail the real parser.
        for entry in Path('/proc/self/fd').iterdir():
            try:
                fd = int(entry.name)
                path = os.readlink(entry)
                st = os.fstat(fd)
            except (OSError, ValueError):
                continue
            if fd not in seen and m.inside(path, root):
                self.assertTrue(stat.S_ISDIR(st.st_mode))
                c['lsof']['stdout'] += (f'f{fd}\0ar\0tDIR\0D{hex(st.st_dev)}\0'
                                       f'i{st.st_ino}\0n{path}\0\n')
        return c

    def stage_attempt(self):
        q = self.root / '.planbound-cleanup-20260930-2'
        q.mkdir(mode=0o700)
        for i, row in enumerate(self.rows):
            os.rename(row['path'], q / str(i))
        receipt = {'status': 'FAIL', 'phase': 'staged-admission',
                   'error': 'open-references-or-incomplete-census', 'interrupted': False,
                   'attempted': None, 'states': ['staged'] * len(self.rows),
                   'restoration': self.rows, 'quarantine': str(q)}
        journal_events = [
            {'event': 'admitted'}, {'event': 'census'}, {'event': 'transaction-entered'},
            {'event': 'quarantine-intent'}, {'event': 'quarantine-created'},
        ]
        for i, row in enumerate(self.rows):
            journal_events += [{'event': 'stage-intent', 'index': i, 'restore': row},
                               {'event': 'staged', 'index': i}]
        journal_events += [{'event': 'staging-complete'}, {'event': 'post-staging-census'},
                           {'event': 'failure', 'status': 'FAIL', 'phase': 'staged-admission',
                            'error': 'open-references-or-incomplete-census', 'attempted': None,
                            'states': ['staged'] * len(self.rows)}]
        old = {}
        for name, data in {
                'journal': ('\n'.join(json.dumps(x, sort_keys=True) for x in journal_events) + '\n').encode(),
                'receipt': json.dumps(receipt, sort_keys=True).encode(),
                'status': json.dumps({'status': 'FAIL', 'receipt': str(self.base / 'attempt-receipt'),
                                      'journal': str(self.base / 'attempt-journal')}, sort_keys=True).encode(),
        }.items():
            p = self.base / ('attempt-' + name)
            p.write_bytes(data); p.chmod(0o600)
            old[name] = {'path': str(p), **m.metadata(p.stat()), 'sha256': m.sha(data)}
        old['quarantine'] = {'path': str(q), 'dev': q.stat().st_dev, 'ino': q.stat().st_ino,
                             'mode': stat.S_IMODE(q.stat().st_mode), 'nlink': q.stat().st_nlink}
        outputs = {'journal': str(self.base / 'recovery-journal'),
                   'receipt': str(self.base / 'recovery-receipt'),
                   'status': str(self.base / 'recovery-status'), 'quarantine': str(q)}
        return old, outputs

    def recovery(self, mutate=None):
        attempt, outputs = self.stage_attempt()
        if mutate: mutate(attempt, outputs)
        with mock.patch.object(m, 'BINDING', self.binding), \
             mock.patch.object(m, 'ATTEMPT2', attempt), \
             mock.patch.object(m, 'committed_file', side_effect=self.committed), \
             mock.patch.object(m, 'collect_census', side_effect=self.recovery_census):
            m.recovery_output_paths(outputs, self.plan, str(self.base))
            opened = m.precreate_recovery_outputs(outputs)
            try:
                with m.terminal_latch():
                    result = m.recover_staged(self.plan, outputs, m.FDJournal(opened['journal'][1]))
                    try: m.write_precreated(opened['receipt'], result)
                    except m.Refusal: pass
                    try: m.write_precreated(opened['status'], {'status': result['status']})
                    except m.Refusal: pass
                    return result, outputs
            finally:
                m.close_recovery_outputs(opened)

    def execute_recovery(self, mutate_writer=None, latch_complete=False, cli=False):
        attempt, outputs = self.stage_attempt()
        release = {'absent_leases': m.LEASES, '_staged_manifest': {'targets': self.rows}}
        patches = [mock.patch.object(m, 'BINDING', self.binding),
                   mock.patch.object(m, 'ATTEMPT2', attempt),
                   mock.patch.object(m, 'MUTEX', str(self.base / 'recovery-mutex')),
                   mock.patch.object(m, 'validate_recovery_release', return_value=release),
                   mock.patch.object(m, 'validate_recovery_plan', return_value=self.plan),
                   mock.patch.object(m, 'validate_attempt2', return_value={}),
                   mock.patch.object(m, 'committed_file', side_effect=self.committed),
                   mock.patch.object(m, 'collect_census', side_effect=self.recovery_census)]
        if mutate_writer: patches.append(mock.patch.object(m, 'write_precreated', side_effect=mutate_writer))
        if latch_complete:
            original = m.FDJournal.append
            def latch(journal, event):
                value = original(journal, event)
                if event.get('event') == 'recovery-complete': m._terminal_latched = True
                return value
            patches.append(mock.patch.object(m.FDJournal, 'append', latch))
        with contextlib.ExitStack() as stack:
            for patch in patches: stack.enter_context(patch)
            if cli:
                argv = ['tool', '--recover-staged', '--plan', str(self.plan_path), '--release', 'release']
                for key, value in outputs.items(): argv += ['--' + key, value]
                with mock.patch.object(m, 'git', return_value=b'b' * 40 + b'\n'), \
                     mock.patch.object(sys, 'argv', argv):
                    m.cli_exit()
            return m.execute_recovery(str(self.plan_path), 'release', 'b' * 40, outputs,
                                      ['python', 'tool', '--recover-staged']), outputs

    def assert_durable_outcome(self, result, outputs, expected='PASS'):
        self.assertEqual(result['status'], expected)
        for key in ('receipt', 'status'):
            self.assertEqual(json.loads(Path(outputs[key]).read_text())['status'], expected)

    def cleanup_signal(self, signum):
        real = m.close_recovery_outputs
        fired = []
        def close(opened):
            real(opened)
            os.kill(os.getpid(), signum)
            fired.append(True)
        previous = {s: signal.getsignal(s) for s in (signal.SIGINT, signal.SIGTERM)}
        with mock.patch.object(m, 'close_recovery_outputs', side_effect=close):
            result, outputs = self.execute_recovery()
        self.assertTrue(fired)
        self.assert_durable_outcome(result, outputs)
        self.assertEqual({s: signal.getsignal(s) for s in previous}, previous)

    def test_execute_recovery_sigint_after_output_close_keeps_committed_result(self):
        self.cleanup_signal(signal.SIGINT)

    def test_execute_recovery_sigterm_after_output_close_keeps_committed_result(self):
        self.cleanup_signal(signal.SIGTERM)

    def test_execute_recovery_cleanup_exception_keeps_committed_result(self):
        real = m.close_recovery_outputs
        def close(opened):
            real(opened)
            raise OSError('fixture post-close error')
        with mock.patch.object(m, 'close_recovery_outputs', side_effect=close):
            result, outputs = self.execute_recovery()
        self.assert_durable_outcome(result, outputs)

    def test_execute_recovery_cleanup_signal_preserves_committed_fail(self):
        real = m.close_recovery_outputs
        def close(opened):
            real(opened)
            os.kill(os.getpid(), signal.SIGTERM)
        with mock.patch.object(m, 'close_recovery_outputs', side_effect=close):
            result, outputs = self.execute_recovery(latch_complete=True)
        self.assert_durable_outcome(result, outputs, 'FAIL')
        self.assertEqual(m.result_exit_code(result), 130)

    def test_execute_recovery_mutex_close_signal_and_exception_keep_outcome(self):
        real = os.close
        fired = []
        def close(fd):
            target = os.readlink('/proc/self/fd/' + str(fd))
            real(fd)
            if target == str(self.base / 'recovery-mutex') and m._terminal_committed:
                fired.append(True)
                os.kill(os.getpid(), signal.SIGINT)
                raise OSError('fixture post-mutex-close error')
        with mock.patch.object(m.os, 'close', side_effect=close):
            result, outputs = self.execute_recovery()
        self.assertTrue(fired)
        self.assert_durable_outcome(result, outputs)

    def test_close_outputs_attempts_every_descriptor_after_one_close_error(self):
        _, _, opened = self.publication_fixture()
        real = os.close
        observed = []
        expected = {entry[1] for entry in opened.values()}
        expected.update(item[0] for entry in opened.values() for item in entry[2]['chain'])
        def close(fd):
            real(fd); observed.append(fd)
            if len(observed) == 1: raise OSError('fixture post-close error')
        with mock.patch.object(m.os, 'close', side_effect=close):
            with self.assertRaises(OSError): m.close_recovery_outputs(opened)
        self.assertEqual(set(observed), expected)
        opened.clear()  # all descriptors closed; registered fixture cleanup is empty

    def test_isolated_cli_terminal_signals_through_cleanup_delivery_and_exit(self):
        # Each child runs the production main/execute/publication/cleanup/exit
        # stack against this suite's disposable three-file recovery fixture.
        code = r'''
import importlib.util, os, signal, sys
spec = importlib.util.spec_from_file_location('recovery_tests', sys.argv[1])
t = importlib.util.module_from_spec(spec); spec.loader.exec_module(t)
c = t.RecoveryFixture(); c.setUp()
print(str(c.base), flush=True)
signum = int(sys.argv[2]); phase = sys.argv[3]
m = t.m
if phase in ('outputs', 'fail'):
    real = m.close_recovery_outputs
    def close(outputs):
        real(outputs); os.kill(os.getpid(), signum)
    m.close_recovery_outputs = close
elif phase == 'mutex':
    real = os.close
    def close(fd):
        path = os.readlink('/proc/self/fd/' + str(fd))
        real(fd)
        if path == str(c.base / 'recovery-mutex') and m._terminal_committed:
            os.kill(os.getpid(), signum)
    m.os.close = close
else:
    class Delivery:
        def write(self, value):
            if phase in ('delivery', 'delivery-error') and m._terminal_committed:
                os.kill(os.getpid(), signum)
                if phase == 'delivery-error':
                    raise OSError('fixture status delivery failure')
            return sys.__stdout__.write(value)
        def flush(self):
            if phase == 'exit' and m._terminal_committed:
                os.kill(os.getpid(), signum)
                raise OSError('fixture stream flush failure')
            return sys.__stdout__.flush()
    sys.stdout = Delivery()
c.execute_recovery(latch_complete=(phase == 'fail'), cli=True)
raise AssertionError('CLI unexpectedly returned')
'''
        for signum in (signal.SIGINT, signal.SIGTERM):
            for phase in ('outputs', 'mutex', 'delivery', 'delivery-error', 'exit', 'fail'):
                with self.subTest(signum=signum, phase=phase):
                    completed = subprocess.run([sys.executable, '-B', '-c', code, __file__,
                                                str(int(signum)), phase], env={**os.environ, 'TMPDIR': str(self.base)},
                                               capture_output=True, text=True, timeout=15)
                    self.assertEqual(completed.returncode, 130 if phase == 'fail' else 0, completed.stderr)
                    child_root = Path(completed.stdout.splitlines()[0])
                    self.assertTrue(m.inside(str(child_root), str(self.base)))
                    expected = 'FAIL' if phase == 'fail' else 'PASS'
                    self.assert_durable_outcome({'status': expected},
                        {key: str(child_root / ('recovery-' + key)) for key in ('receipt', 'status')}, expected)

    def test_recovery_restores_exact_staged_tree(self):
        result, outputs = self.recovery()
        self.assertEqual(result['status'], 'PASS')
        self.assertEqual(result['states'], ['restored'] * 3)
        self.assert_originals()
        self.assertEqual(os.listdir(outputs['quarantine']), [])
        self.assertEqual(json.loads(Path(outputs['receipt']).read_text())['status'], 'PASS')

    def test_recovery_declares_all_actual_destination_descriptors(self):
        captured = []
        real = m.check_census
        def check(census, root, owned=()):
            actual = {}
            for path in Path('/proc/self/fd').iterdir():
                try:
                    name = os.readlink(path)
                    if m.inside(name, root):
                        fd = int(path.name); st = os.fstat(fd)
                        actual[fd] = (os.getpid(), name, st.st_dev, st.st_ino, 'r')
                except OSError:
                    pass
            declared = {w['fd']: (w['pid'], w['path'], w['dev'], w['ino'], w['access']) for w in owned}
            self.assertEqual(declared, actual)
            self.assertEqual(len([v for v in actual.values() if v[1] == root]), 2)
            self.assertGreaterEqual(len(actual), 6)
            captured.append(actual)
            return real(census, root, owned)
        with mock.patch.object(m, 'check_census', side_effect=check):
            result, _ = self.execute_recovery()
        self.assertEqual(result['status'], 'PASS')
        self.assertEqual(len(captured), 2)

    def test_recovery_census_rejects_omitted_retained_ancestor(self):
        real = m.recovery_references
        def omit(*args):
            refs = real(*args)
            return [w for w in refs if w['path'] != str(self.root / 'docs')]
        with mock.patch.object(m, 'recovery_references', side_effect=omit):
            result, _ = self.execute_recovery()
        self.assertEqual(result['status'], 'FAIL')
        self.assertEqual(result['error'], 'open-references-or-incomplete-census')
        self.assertEqual(result['states'], ['staged'] * 3)

    @unittest.skipUnless(shutil.which('lsof'), 'lsof unavailable')
    def test_validate_recovery_actual_unprivileged_lsof_all_pins(self):
        attempt, outputs = self.stage_attempt()
        def collector(root):
            with m.directory(str(self.base)):
                c = self.census()
                paths = {str(self.base)}
                for entry in Path('/proc/self/fd').iterdir():
                    try:
                        path = os.readlink(entry)
                        if m.inside(path, root): paths.add(path)
                    except OSError:
                        pass
                c['lsof'] = m.run(['lsof', '-nP', '-w', '-a', '-p', str(os.getpid()),
                                   '-F0pfaDint', '--', *sorted(paths)])
                return c
        with mock.patch.object(m, 'ATTEMPT2', attempt), \
             mock.patch.object(m, 'collect_census', side_effect=collector), m.terminal_latch():
            m.validate_live_staged_recovery(self.plan)
        self.assertFalse(Path(outputs['receipt']).exists())
        self.assertEqual(sorted(os.listdir(outputs['quarantine'])), ['0', '1', '2'])

    def publication_fixture(self):
        parent = self.base / 'output-space' / 'nested'
        parent.mkdir(parents=True)
        outputs = {k: str(parent / k) for k in ('journal', 'receipt', 'status')}
        opened = m.precreate_recovery_outputs(outputs)
        self.addCleanup(m.close_recovery_outputs, opened)
        return parent, outputs, opened

    def publish_fixture(self, opened, outputs):
        with m.terminal_latch():
            return m.publish_recovery_result(opened, {'status': 'PASS'}, outputs,
                                             m.FDJournal(opened['journal'][1]))

    def test_publication_parent_substitution_invalidates_displaced_pass(self):
        parent, outputs, opened = self.publication_fixture()
        displaced = parent.with_name('displaced')
        real = m.write_precreated
        def swap(entry, record, replace=False):
            real(entry, record, replace)
            if entry is opened['status']:
                parent.rename(displaced)
                parent.mkdir()
        with mock.patch.object(m, 'write_precreated', side_effect=swap):
            result = self.publish_fixture(opened, outputs)
        self.assertEqual(result['status'], 'FAIL')
        for key in ('receipt', 'status'):
            self.assertFalse(Path(outputs[key]).exists())
            self.assertEqual(json.loads((displaced / key).read_text())['status'], 'FAIL')

    def test_publication_ancestor_substitution_invalidates_displaced_pass(self):
        parent, outputs, opened = self.publication_fixture()
        ancestor = parent.parent
        displaced = ancestor.with_name('saved-space')
        real = m.write_precreated
        def swap(entry, record, replace=False):
            real(entry, record, replace)
            if entry is opened['receipt']:
                ancestor.rename(displaced)
                parent.mkdir(parents=True)
        with mock.patch.object(m, 'write_precreated', side_effect=swap):
            result = self.publish_fixture(opened, outputs)
        self.assertEqual(result['status'], 'FAIL')
        for key in ('receipt', 'status'):
            self.assertFalse(Path(outputs[key]).exists())
            self.assertEqual(json.loads((displaced / 'nested' / key).read_text())['status'], 'FAIL')

    def test_publication_output_name_substitution_invalidates_owned_pass(self):
        parent, outputs, opened = self.publication_fixture()
        real = m.write_precreated
        displaced = parent / 'saved-receipt'
        def swap(entry, record, replace=False):
            real(entry, record, replace)
            if entry is opened['status']:
                Path(outputs['receipt']).rename(displaced)
                Path(outputs['receipt']).write_bytes(b'foreign')
        with mock.patch.object(m, 'write_precreated', side_effect=swap):
            result = self.publish_fixture(opened, outputs)
        self.assertEqual(result['status'], 'FAIL')
        self.assertEqual(Path(outputs['receipt']).read_bytes(), b'foreign')
        self.assertEqual(json.loads(displaced.read_text())['status'], 'FAIL')
        self.assertEqual(json.loads(Path(outputs['status']).read_text())['status'], 'FAIL')

    def metadata_drift_after_pass(self, mutate):
        _, outputs, opened = self.publication_fixture()
        real = m.write_precreated
        def change(entry, record, replace=False):
            real(entry, record, replace)
            if entry is opened['status']:
                mutate(opened['receipt'][1])
                mutate(opened['status'][1])
        with mock.patch.object(m, 'write_precreated', side_effect=change):
            result = self.publish_fixture(opened, outputs)
        self.assert_durable_outcome(result, outputs, 'FAIL')
        self.assertNotIn('receipt_failure', result)
        self.assertNotIn('status_failure', result)

    def test_publication_chmod_after_pass_invalidates_both_owned_files(self):
        self.metadata_drift_after_pass(lambda fd: os.fchmod(fd, 0o644))

    def test_publication_group_change_after_pass_invalidates_both_owned_files(self):
        groups = [gid for gid in os.getgroups() if gid != os.getegid()]
        if not groups:
            self.skipTest('no alternate supplementary group for unprivileged fchown')
        self.metadata_drift_after_pass(lambda fd: os.fchown(fd, -1, groups[0]))

    def test_publication_late_real_signal_after_durable_pass_demotes_both(self):
        _, outputs, opened = self.publication_fixture()
        real = m.write_precreated
        def terminate(entry, record, replace=False):
            real(entry, record, replace)
            if entry is opened['status']:
                self.assertEqual(json.loads(Path(outputs['status']).read_text())['status'], 'PASS')
                os.kill(os.getpid(), signal.SIGTERM)
                self.assertIn(signal.SIGTERM, signal.sigpending())
        with mock.patch.object(m, 'write_precreated', side_effect=terminate):
            result = self.publish_fixture(opened, outputs)
        self.assertEqual(result['status'], 'FAIL')
        self.assertTrue(result['interrupted'])
        for key in ('receipt', 'status'):
            self.assertEqual(json.loads(Path(outputs[key]).read_text())['status'], 'FAIL')

    def test_publication_signal_at_committed_unmask_keeps_one_outcome(self):
        _, outputs, opened = self.publication_fixture()
        real = signal.pthread_sigmask
        fired = []
        def unmask(how, mask):
            if how == signal.SIG_SETMASK:
                self.assertTrue(m._terminal_committed)
                os.kill(os.getpid(), signal.SIGTERM)
                fired.append(True)
            return real(how, mask)
        with mock.patch.object(m.signal, 'pthread_sigmask', side_effect=unmask):
            result = self.publish_fixture(opened, outputs)
        self.assertTrue(fired)
        self.assertEqual(result['status'], 'PASS')
        self.assertFalse(m._terminal_latched)
        for key in ('receipt', 'status'):
            self.assertEqual(json.loads(Path(outputs[key]).read_text())['status'], result['status'])

    def test_recovery_collision_does_not_overwrite(self):
        def collision(attempt, outputs):
            Path(self.rows[1]['path']).write_bytes(b'foreign')
        result, outputs = self.recovery(collision)
        self.assertEqual(result['status'], 'FAIL')
        self.assertEqual(Path(self.rows[1]['path']).read_bytes(), b'foreign')
        self.assertNotEqual(result['states'][1], 'restored')

    def test_recovery_parent_namespace_drift_fails_before_rename(self):
        def drift(attempt, outputs):
            (self.evidence / 'foreign').write_bytes(b'x')
        result, _ = self.recovery(drift)
        self.assertEqual(result['status'], 'FAIL')
        self.assertEqual(result['error'], 'subtree-set')

    def test_recovery_root_swap_after_admission_never_redirects_restore(self):
        original = m.FDJournal.append
        moved = self.base / 'old-root'
        swapped = False
        def swap(journal, event):
            nonlocal swapped
            value = original(journal, event)
            if event.get('event') == 'recovery-admitted' and not swapped:
                swapped = True
                self.root.rename(moved)
                self.root.mkdir()
            return value
        with mock.patch.object(m.FDJournal, 'append', swap):
            result, outputs = self.recovery()
        self.assertTrue(swapped)
        self.assertEqual(result['status'], 'FAIL')
        self.assertTrue((moved / '.planbound-cleanup-20260930-2' / '0').exists())

    def test_recovery_evidence_swap_after_admission_never_redirects_restore(self):
        original = m.FDJournal.append
        moved = self.root / 'docs/verification/saved-evidence'; swapped = False
        def swap(journal, event):
            nonlocal swapped
            value = original(journal, event)
            if event.get('event') == 'recovery-admitted' and not swapped:
                swapped = True; self.evidence.rename(moved); self.evidence.mkdir()
            return value
        with mock.patch.object(m.FDJournal, 'append', swap): result, _ = self.recovery()
        self.assertTrue(swapped); self.assertEqual(result['status'], 'FAIL')
        self.assertTrue((Path(result['quarantine']) / '0').exists())
        self.assertFalse((self.evidence / 'file-0').exists())

    def test_recovery_displaced_restored_tree_reconciles_as_uncertain(self):
        real = m.FDJournal.append
        moved = self.evidence.with_name('displaced')
        def swap(journal, event):
            value = real(journal, event)
            if event.get('event') == 'restored' and not moved.exists():
                self.evidence.rename(moved)
                self.evidence.mkdir()
            return value
        with mock.patch.object(m.FDJournal, 'append', swap):
            result, _ = self.recovery()
        self.assertEqual(result['status'], 'FAIL')
        self.assertEqual(result['states'], ['restore-uncertain'] * 3)
        self.assertEqual(result['reconciliation'][2]['locations']['source'], 'expected')
        self.assertEqual(result['reconciliation'][2]['locations']['namespace'], 'replaced-or-unreadable')

    def test_recovery_one_reconcile_exception_does_not_omit_other_rows(self):
        real = m.reconcile_recovery_rename
        def unreadable(row, qfd, index, destinations, namespace_valid=True):
            if index == 0: raise OSError('fixture reconciliation read error')
            return real(row, qfd, index, destinations, namespace_valid)
        with mock.patch.object(m, 'rename_noreplace', side_effect=KeyboardInterrupt), \
             mock.patch.object(m, 'reconcile_recovery_rename', side_effect=unreadable):
            result, _ = self.recovery()
        self.assertEqual(result['status'], 'FAIL')
        self.assertEqual(result['states'], ['restore-uncertain', 'staged', 'staged'])
        self.assertEqual([entry['index'] for entry in result['reconciliation']], [0, 1, 2])

    def test_recovery_post_syscall_interrupt_reconciles_all_rows(self):
        old = m.rename_noreplace
        fired = False
        def interrupt(*args):
            nonlocal fired
            old(*args)
            if not fired:
                fired = True
                raise KeyboardInterrupt()
        with mock.patch.object(m, 'rename_noreplace', side_effect=interrupt):
            result, _ = self.recovery()
        self.assertTrue(fired)
        self.assertEqual(result['status'], 'FAIL')
        self.assertEqual(result['states'][2], 'restored')
        self.assertTrue(all('locations' in x for x in result['reconciliation']))

    def test_recovery_short_and_zero_write_fail_closed(self):
        original = os.write
        def short(fd, data): return original(fd, data[:2])
        with mock.patch.object(m.os, 'write', side_effect=short):
            result, _ = self.recovery()
        self.assertEqual(result['status'], 'PASS')

    def test_recovery_zero_journal_write_prevents_rename(self):
        with mock.patch.object(m.os, 'write', return_value=0):
            result, _ = self.recovery()
        self.assertEqual(result['status'], 'FAIL')
        self.assertTrue(all(state == 'staged' for state in result['states']))

    def test_recovery_release_binds_manifest_and_external_commit(self):
        attempt, outputs = self.stage_attempt()
        tool = self.base / m.TOOL_PATH; tool.parent.mkdir(parents=True, exist_ok=True)
        tool.write_bytes(b'exact recovery tool')
        test_path = 'scripts/tests/test_native_exact_candidate12_planbound_cleanup_20260930.py'
        test_file = self.base / test_path; test_file.parent.mkdir(parents=True, exist_ok=True)
        test_file.write_bytes(b'exact recovery tests')
        manifest_path = 'docs/verification/recovery-staged-manifest.json'
        manifest_file = self.base / manifest_path; manifest_file.parent.mkdir(parents=True, exist_ok=True)
        manifest = {'schema': 'mckernel.candidate12-cleanup-staged-manifest.v1', 'status': 'PASS',
                    'plan': self.binding, 'attempt2': attempt, 'quarantine': attempt['quarantine']['path'],
                    'targets': self.rows}
        manifest_file.write_bytes(json.dumps(manifest, sort_keys=True).encode())
        release_path = self.base / 'docs/verification/recovery-release.json'
        command = ['python', 'tool', '--recover-staged']
        release = {'schema': m.RECOVERY_SCHEMA, 'status': 'PASS', 'finalization': 'PASS',
                   'source_commit': 'a' * 40, 'tool_sha256': m.sha(tool.read_bytes()),
                   'tool_blob': 'c' * 40, 'test_path': test_path,
                   'test_sha256': m.sha(test_file.read_bytes()), 'test_blob': 'd' * 40, 'plan': self.binding,
                   'staged_manifest': {'path': manifest_path, 'sha256': m.sha(manifest_file.read_bytes()),
                                       'size': len(manifest_file.read_bytes())},
                   'command': command, 'outputs': outputs, 'quarantine': attempt['quarantine']['path'],
                   'absent_leases': m.LEASES, 'dispatcher_exclusive': True,
                   'retained_containers': m.CONTAINER_BINDINGS}
        release_path.write_bytes(json.dumps(release, sort_keys=True).encode())
        def git(repo, *args):
            if args[0] == 'merge-base': return b''
            if args[0] == 'rev-parse':
                return (b'd' * 40 if args[1].endswith(test_path) else b'c' * 40) + b'\n'
            if args[0] == 'show':
                name = args[1].split(':', 1)[1]
                return {'docs/verification/recovery-release.json': release_path.read_bytes(),
                        m.TOOL_PATH: tool.read_bytes(), test_path: test_file.read_bytes(),
                        manifest_path: manifest_file.read_bytes()}[name]
            self.fail('unexpected recovery git edge')
        with mock.patch.object(m, 'ATTEMPT2', attempt), mock.patch.object(m, 'git', side_effect=git):
            m.validate_recovery_release(str(release_path), 'b' * 40, outputs, command, self.binding)
            release['staged_manifest']['sha256'] = '0' * 64
            release_path.write_bytes(json.dumps(release, sort_keys=True).encode())
            with self.assertRaisesRegex(m.Refusal, 'recovery-manifest-content'):
                m.validate_recovery_release(str(release_path), 'b' * 40, outputs, command, self.binding)

    def test_recovery_journal_enospc_reconciles_each_row(self):
        original = m.FDJournal.append
        calls = 0
        def full(journal, record):
            nonlocal calls
            calls += 1
            if record.get('event') == 'restore-intent':
                raise OSError(28, 'ENOSPC')
            return original(journal, record)
        with mock.patch.object(m.FDJournal, 'append', full):
            result, _ = self.recovery()
        self.assertEqual(result['status'], 'FAIL')
        self.assertEqual(len(result['reconciliation']), 3)
        self.assertTrue(all(state == 'staged' for state in result['states']))

    def test_recovery_signal_during_final_scan_never_passes(self):
        original = m.recovery_evidence_shape
        calls = 0
        def signal_after(plan, destinations, staged=False):
            nonlocal calls
            value = original(plan, destinations, staged)
            calls += 1
            if calls >= 2 and not staged:
                m._terminal_latched = True
            return value
        with mock.patch.object(m, 'recovery_evidence_shape', side_effect=signal_after):
            result, _ = self.recovery()
        self.assertEqual(result['status'], 'FAIL')
        self.assertEqual(result['error'], 'terminal-signal-latched')

    def test_recovery_final_mutation_after_census_never_passes(self):
        original = m.FDJournal.append
        changed = False
        def mutate(journal, event):
            nonlocal changed
            value = original(journal, event)
            if event.get('event') == 'recovery-final-census' and not changed:
                changed = True
                Path(self.rows[0]['path']).write_bytes(b'changed final evidence')
            return value
        with mock.patch.object(m.FDJournal, 'append', mutate):
            result, _ = self.recovery()
        self.assertTrue(changed)
        self.assertEqual(result['status'], 'FAIL')
        self.assertEqual(result['error'], 'file-metadata')

    def test_recovery_publication_failures_demote_pass_and_status(self):
        real = m.write_precreated
        def receipt_full(entry, record, replace=False):
            if entry[1] == receipt_fd: raise OSError(28, 'ENOSPC')
            return real(entry, record, replace)
        receipt_fd = None
        # Learn the receipt fd in a first wrapper call without altering writes.
        def fail_receipt(entry, record, replace=False):
            nonlocal receipt_fd
            if receipt_fd is None and record.get('restore_commit'):
                receipt_fd = entry[1]; raise OSError(28, 'ENOSPC')
            return real(entry, record, replace)
        result, outputs = self.execute_recovery(fail_receipt)
        self.assertEqual(result['status'], 'FAIL')
        self.assertEqual(json.loads(Path(outputs['status']).read_text())['status'], 'FAIL')

    def test_recovery_signal_after_complete_demotes_public_status(self):
        result, outputs = self.execute_recovery(latch_complete=True)
        self.assertEqual(result['status'], 'FAIL')
        self.assertEqual(json.loads(Path(outputs['status']).read_text())['status'], 'FAIL')

    def test_cli_validate_recovery_is_read_only_mode(self):
        release = {'_staged_manifest': {'targets': self.rows}}
        with mock.patch.object(m, 'git', return_value=b'b' * 40 + b'\n'), \
             mock.patch.object(m, 'validate_recovery_release', return_value=release) as released, \
             mock.patch.object(m, 'validate_recovery_plan', return_value=self.plan), \
             mock.patch.object(m, 'validate_attempt2', return_value={}), \
             mock.patch.object(m, 'validate_live_staged_recovery') as live:
            self.assertEqual(m.main(['--validate-recovery', '--release', '/tmp/release.json']), 0)
        released.assert_called_once(); live.assert_called_once_with(self.plan)


if __name__ == '__main__':
    unittest.main()
