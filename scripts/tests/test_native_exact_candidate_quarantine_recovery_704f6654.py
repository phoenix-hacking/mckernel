#!/usr/bin/env python3
"""Source-only regression tests for the 704f quarantine continuation."""
import copy
import importlib.util
import json
import os
import signal
import stat
import subprocess
import tempfile
import types
from contextlib import ExitStack
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

    def observer_fixture(self, expected, boot='boot', launched=(1, 1)):
        m = self.m
        roots = []
        for (_original, q, d, i), members in zip(m.ROOTS, expected):
            identities = {_id for _id in [m._observer_identity(d, i, 0, 0, 'directory', 0o700)]}
            identities.update(m._observer_identity(item['device'], item['inode'], item['uid'], item['gid'], item['kind'], item['mode']) for item in members.values())
            identities = [list(item) for item in sorted(identities)]
            roots.append(dict(path=str(q), device_number=d, inode=i, mode='0700', device='%d:%d' % (os.major(d), os.minor(d)), uid=0, gid=0,
                              filesystem_root='/', observer_mount={}, tree_root_identity=list(m._observer_identity(d, i, 0, 0, 'directory', 0o700)),
                              tree_member_identities=identities, tree_inode_count=len(identities), tree_membership_sha256=m._observer_membership_digest(identities)))
        clean = dict(clean=True, target_references=[], permission_denials=[], tree_revalidation_failures=[], complete_mount_proofs=True,
                     unresolved_churn=[], closure_nonconvergent=False, unscanned_final_identities=[], closure_passes=1,
                     task_identities=0, rescanned_identities=0, identities=[], field_counts={}, mount_proofs=[])
        return dict(schema='mckernel.read-only-live-reference-snapshot.v7', status='PASS', observer_sha256=m.OBSERVER_SHA,
                    scan_complete=True, failure=None, boot_id=boot, started_at_utc='start', ended_at_utc='end', observer_pid=launched[0],
                    observer_starttime=str(launched[1]), tasks_scanned=0, allowed_self_scan_fds=[], roots=roots, rounds=[dict(clean, round=1), dict(clean, round=2)],
                    target_references=[], permission_denials=[], tree_revalidation_failures=[], persistent_tree_revalidation_failures=[], unscanned_final_identities=[])

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
            m.draft_guard()

    def finalized(self):
        m = self.m
        templates = {name: path.read_bytes() for name, path in m.source_paths().items()}
        finals = dict(templates)
        finals['packet'] = m.final_packet_bytes(templates['packet'])
        finals['wrapper'] = m.final_wrapper_bytes(templates['wrapper'])
        pins = {name: m.digest(data) for name, data in finals.items()}
        finals['basis'] = m.final_basis_bytes(templates['basis'], pins)
        pins['basis'] = m.digest(finals['basis'])
        paths = m.source_paths()
        allowed = [str(path.relative_to(m.REPO)) for path in (m.PACKET, m.WRAPPER, m.BASIS, m.EXECUTION_RELEASE)]
        release = dict(schema='mckernel.quarantine-continuation-execution-release.v2', status='PASS',
                       execution_authorized=True, one_shot=True, retry=False, rollback=False,
                       authenticated_sources=pins, runtime={}, docker=self.docker_fixture()[1]['docker'],
                       finalization=dict(template_commit='a' * 40,
                                         template_hashes={name: m.digest(data) for name, data in templates.items()},
                                         allowed_changed_paths=allowed))
        local = {paths[name]: data for name, data in finals.items()}
        local[m.EXECUTION_RELEASE] = json.dumps(release).encode()
        fetched = dict(local)
        def git(*args):
            if args[0] == 'rev-parse': return b'b' * 40 + b'\n'
            if args[0] == 'merge-base': return b''
            if args[0] == 'diff': return ('\0'.join(allowed) + '\0').encode()
            if args[0] == 'show':
                commit, rel = args[1].split(':', 1)
                if commit == 'b' * 40: return fetched[m.REPO / rel]
                return templates[next(name for name, path in paths.items() if path == m.REPO / rel)]
            raise AssertionError(args)
        final_module = types.ModuleType('final704f')
        exec(compile(finals['packet'], str(H), 'exec'), final_module.__dict__)
        return final_module, release, local, fetched, git, templates, finals

    def test_real_finalized_main_and_wrapper_syntax(self):
        m, release, local, fetched, git, templates, finals = self.finalized()
        self.assertFalse(m.SOURCE_TEMPLATE_ONLY)
        with mock.patch.object(m, 'git_bytes', side_effect=git), \
             mock.patch.object(m, 'read_regular', side_effect=lambda path: local[path]), \
             mock.patch.object(m, 'execute_final', return_value=0) as execute:
            self.assertEqual(m.main(['--release', str(m.EXECUTION_RELEASE)]), 0)
            execute.assert_called_once_with(release)
        result = subprocess.run(['/bin/bash', '-n'], input=finals['wrapper'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(b'exec /usr/bin/sudo -A /usr/bin/python3 -E -s -B ', finals['wrapper'])
        basis = json.loads(finals['basis'])
        self.assertFalse(basis['execution_authorized'])
        self.assertNotIn('release_sha256', basis)
        self.assertNotIn('basis_sha256', basis)

    def test_real_finalization_substitution_matrix(self):
        for target in ('packet', 'wrapper', 'basis', 'observer', 'test'):
            for location in ('local', 'fetched', 'template'):
                with self.subTest(target=target, location=location):
                    m, release, local, fetched, git, templates, finals = self.finalized()
                    path = m.source_paths()[target]
                    if location == 'local': local[path] += b' '
                    elif location == 'fetched': fetched[path] += b' '
                    else: templates[target] += b' '
                    with self.assertRaises(m.Error):
                        m.admit_execution_release(str(m.EXECUTION_RELEASE), git, lambda p: local[p])
        for defect in ('nonancestor', 'diff', 'upstream', 'canonical', 'schema', 'release-local'):
            with self.subTest(defect=defect):
                m, release, local, fetched, git, templates, finals = self.finalized()
                def broken(*args):
                    if defect == 'nonancestor' and args[0] == 'merge-base':
                        raise subprocess.CalledProcessError(1, args)
                    if defect == 'diff' and args[0] == 'diff': return b'unknown\0'
                    if defect == 'upstream' and args == ('rev-parse', '@{upstream}'): return b'c' * 40
                    return git(*args)
                if defect == 'schema':
                    del release['schema']
                    fetched[m.EXECUTION_RELEASE] = local[m.EXECUTION_RELEASE] = json.dumps(release).encode()
                if defect == 'release-local': local[m.EXECUTION_RELEASE] += b' '
                path = str(m.EXECUTION_RELEASE) + ('/../bad' if defect == 'canonical' else '')
                with self.assertRaises((m.Error, subprocess.CalledProcessError)):
                    m.admit_execution_release(path, broken, lambda p: local[p])

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
        value = self.observer_fixture(expected)
        m.validate_observer(value, expected)
        for key, bad in [('target_references', ['fd']), ('unscanned_final_identities', [[1, 2]])]:
            changed = copy.deepcopy(value); changed[key] = bad
            with self.assertRaises(m.Error): m.validate_observer(changed, expected)
        changed = copy.deepcopy(value); changed['rounds'][-1]['complete_mount_proofs'] = False
        with self.assertRaises(m.Error): m.validate_observer(changed, expected)

    def test_observer_uses_unique_hardlink_identities(self):
        m = self.m
        member = dict(device=26, inode=9, uid=0, gid=0, mode=0o600, kind='file', size=1, sha256='a' * 64)
        expected = [dict(a=member, b=member), {}]
        value = self.observer_fixture(expected, boot='b')
        m.validate_observer(value, expected)
        with self.assertRaisesRegex(m.Error, 'boot mismatch'):
            m.validate_observer(value, expected, admitted_boot='other')
        with self.assertRaisesRegex(m.Error, 'launched identity'):
            m.validate_observer(value, expected, launched=(2, 1))

    def test_sealed_observer_gets_real_fd_and_timeout_captures_status(self):
        m = self.m
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp); source = base / 'observer.py'; source.write_text('import json; print(json.dumps({"sealed": True}))\n')
            fd = os.open(str(source), os.O_RDONLY | os.O_NOFOLLOW)
            prior = m.OUTPUT; m.OUTPUT = base / 'output'; m.OUTPUT.mkdir()
            try:
                self.assertEqual(m.run_sealed_observer(fd, (), timeout=2)[0], {'sealed': True})
                self.assertTrue((m.OUTPUT / 'observer.status.json').exists())
            finally:
                m.OUTPUT = prior; os.close(fd)
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp); source = base / 'slow.py'; source.write_text('import time; time.sleep(10)\n')
            fd = os.open(str(source), os.O_RDONLY | os.O_NOFOLLOW)
            prior = m.OUTPUT; m.OUTPUT = base / 'output'; m.OUTPUT.mkdir()
            try:
                with self.assertRaisesRegex(m.Error, 'timed out'):
                    m.run_sealed_observer(fd, (), timeout=.01)
                self.assertTrue((m.OUTPUT / 'observer.status.json').exists())
            finally:
                m.OUTPUT = prior; os.close(fd)

    def docker_fixture(self):
        m = self.m
        ids = [format(number, '064x') for number in range(17)]
        rows = [dict(Id=i, Mounts=[], State={'Status': 'exited', 'Running': False, 'Pid': 0,
                     'OOMKilled': False, 'Paused': False, 'Restarting': False, 'Dead': False, 'ExitCode': 0},
                     RestartCount=0, HostConfig={'RestartPolicy': {'Name': 'no', 'MaximumRetryCount': 0}},
                     Config={'Env': ['TOKEN=synthetic-private-env-' + str(number)],
                             'Labels': {'private': 'synthetic-private-label'}})
                for number, i in enumerate(ids)]
        for row in rows[:4]:
            row['Mounts'] = [dict(Type='bind', Source=str(m.ORIGINALS[0]), Destination='/candidate',
                                  Mode='ro', RW=False, Propagation='rprivate')]
        exceptions = {row['Id']: copy.deepcopy(row['Mounts']) for row in rows[:4]}
        release = {'docker': {'authenticated_current_record_sha256':
                              {row['Id']: m.docker_record_sha256(row) for row in rows},
                              'terminal_candidate_mount_exceptions': exceptions}}
        return rows, release

    def test_docker_full_census_rejects_unknown_protected_or_omitted(self):
        m = self.m
        rows, release = self.docker_fixture()
        m.validate_docker(rows, release)
        changed = copy.deepcopy(rows); changed[0]['Mounts'] = [dict(Source=str(m.QUARANTINES[0]))]
        with self.assertRaises(m.Error): m.validate_docker(changed, release)
        with self.assertRaises(m.Error): m.validate_docker(rows[:-1], release)
        changed = copy.deepcopy(rows); changed[0]['State']['Running'] = True
        with self.assertRaises(m.Error):
            m.validate_docker(changed, release)

    def test_docker_secrets_bound_by_hash_but_never_persisted(self):
        m = self.m
        rows, release = self.docker_fixture()
        m.validate_docker(rows, release)
        summary = m.docker_safe_summary(rows)
        encoded_release = json.dumps(release).encode()
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'docker.before.json'
            m.exclusive_json(path, summary)
            evidence = path.read_bytes()
        for data in (encoded_release, evidence):
            self.assertNotIn(b'synthetic-private', data)
            self.assertNotIn(b'"Config"', data)
            self.assertNotIn(b'"Env"', data)
            self.assertNotIn(b'"Labels"', data)
        self.assertEqual(summary['schema'], 'mckernel.docker-census-safe-summary.v1')
        self.assertEqual(len(summary['records']), 17)
        self.assertEqual([row['id'] for row in summary['records']], sorted(row['Id'] for row in rows))
        for row in summary['records']:
            self.assertEqual(set(row), {'id', 'record_sha256', 'protected_mounts', 'terminal_state',
                                        'restart_count', 'restart_policy'})
            self.assertEqual(row['restart_policy'], {'Name': 'no', 'MaximumRetryCount': 0})
        self.assertEqual(summary['records'][0]['protected_mounts'], rows[0]['Mounts'])
        self.assertEqual(summary['records'][0]['terminal_state']['Pid'], 0)
        changed = copy.deepcopy(rows)
        changed[0]['Config']['Env'] = ['TOKEN=synthetic-private-replaced']
        self.assertNotEqual(m.docker_record_sha256(changed[0]), m.docker_record_sha256(rows[0]))
        with self.assertRaisesRegex(m.Error, 'authenticated record'):
            m.validate_docker(changed, release)
        # Fields outside the explicit audit projection stay private, including
        # unexpected additions within otherwise permitted inspect structures.
        changed = copy.deepcopy(rows)
        changed[0]['State']['Error'] = 'synthetic-private-state-error'
        changed[0]['HostConfig']['RestartPolicy']['Private'] = 'synthetic-private-policy'
        changed[0]['Mounts'][0]['Private'] = 'synthetic-private-mount'
        self.assertNotIn('synthetic-private', json.dumps(m.docker_safe_summary(changed)))
        # Only Mounts ordering is normalized; other array ordering binds.
        ordered = copy.deepcopy(rows[0])
        ordered['Mounts'].append(dict(Source='/unprotected', Destination='/other'))
        reverse = copy.deepcopy(ordered); reverse['Mounts'].reverse()
        self.assertEqual(m.docker_record_sha256(ordered), m.docker_record_sha256(reverse))
        ordered['Config']['Env'] = ['first', 'second']
        reverse = copy.deepcopy(ordered); reverse['Config']['Env'].reverse()
        self.assertNotEqual(m.docker_record_sha256(ordered), m.docker_record_sha256(reverse))

    def test_docker_hash_census_and_terminal_exception_gates(self):
        m = self.m
        for defect in ('omitted', 'duplicate', 'unknown-mount', 'fewer-exceptions', 'outside-exception',
                       'OOMKilled', 'Restarting', 'Paused', 'Dead', 'restart-count', 'restart-policy'):
            with self.subTest(defect=defect):
                rows, release = self.docker_fixture()
                exceptions = release['docker']['terminal_candidate_mount_exceptions']
                if defect == 'omitted': rows.pop()
                elif defect == 'duplicate': rows[-1] = copy.deepcopy(rows[-2])
                elif defect == 'unknown-mount':
                    rows[-1]['Mounts'] = [dict(Source=str(m.QUARANTINES[0]), Destination='/unknown')]
                elif defect == 'fewer-exceptions': exceptions.pop(next(iter(exceptions)))
                elif defect == 'outside-exception': exceptions['f' * 64] = exceptions.pop(next(iter(exceptions)))
                elif defect == 'restart-count': rows[0]['RestartCount'] = 1
                elif defect == 'restart-policy': rows[0]['HostConfig']['RestartPolicy']['Name'] = 'always'
                else: rows[0]['State'][defect] = True
                # Bind the changed complete objects so these checks exercise
                # census/terminal/mount invariants beyond mere hash rejection.
                release['docker']['authenticated_current_record_sha256'] = {
                    row['Id']: m.docker_record_sha256(row) for row in rows}
                with self.assertRaises(m.Error): m.validate_docker(rows, release)

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

    def test_conflict_permission_pid_reuse_and_boot_fail_closed(self):
        m = self.m
        with tempfile.TemporaryDirectory() as temp, mock.patch.object(m.os, 'getpid', return_value=100):
            proc = Path(temp); row = proc / '7'; row.mkdir(); (row / 'stat').write_text('7 (x) ' + ' '.join(['S'] + ['0'] * 19) + '\n')
            child = proc / '100'; child.mkdir()
            (child / 'stat').write_bytes(self.census_stat(100, 0, 11))
            (row / 'cmdline').write_bytes(b'qemu-system-aarch64\0')
            boot = proc / 'boot'; boot.write_text('boot\n')
            with self.assertRaisesRegex(m.Error, 'conflicting'):
                m.validate_conflicts(proc, boot)
            with mock.patch.object(m, '_proc_cmdline_stable', side_effect=PermissionError('no')):
                with self.assertRaises(PermissionError):
                    m.validate_conflicts(proc, boot)
            with self.assertRaisesRegex(m.Error, 'boot binding changed'):
                m.validate_conflicts(proc, boot, admitted_boot='other')

    def test_direct_sudo_parent_is_exact_live_exception_only(self):
        m = self.m

        def stat_line(pid, ppid, start):
            fields = ['S', str(ppid), str(pid), str(pid)] + ['0'] * 15 + [str(start)] + ['0'] * 2
            return ('%d (sudo) %s\n' % (pid, ' '.join(fields))).encode()

        def fixture(temp, child=100, parent=200, child_ppid=None, parent_start=22,
                    child_start=11, exe='/usr/bin/sudo', argv=None, uid='0 0 0 0', gid='0 0 0 0',
                    unreadable=None):
            child_ppid = parent if child_ppid is None else child_ppid
            child_dir = temp / str(child); parent_dir = temp / str(parent)
            child_dir.mkdir(); parent_dir.mkdir()
            (child_dir / 'stat').write_bytes(stat_line(child, child_ppid, child_start))
            (parent_dir / 'stat').write_bytes(stat_line(parent, 1, parent_start))
            expected = [b'/usr/bin/sudo', b'-A', b'/usr/bin/python3', b'-E', b'-s', b'-B',
                        os.fsencode(str(m.PACKET)), b'--release', os.fsencode(str(m.EXECUTION_RELEASE))]
            (parent_dir / 'cmdline').write_bytes(b'\0'.join(expected if argv is None else argv) + b'\0')
            (parent_dir / 'status').write_text('Uid:\t%s\nGid:\t%s\n' % (uid, gid))
            os.symlink(exe, parent_dir / 'exe')
            if unreadable == 'parent-stat': (parent_dir / 'stat').unlink()
            if unreadable == 'parent-cmdline': (parent_dir / 'cmdline').unlink()
            if unreadable == 'parent-status': (parent_dir / 'status').unlink()
            if unreadable == 'child-stat': (child_dir / 'stat').unlink()
            return temp / 'boot'

        with tempfile.TemporaryDirectory() as directory:
            temp = Path(directory); boot = temp / 'boot'; boot.write_text('boot\n')
            with mock.patch.object(m, 'PACKET', temp / 'packet.py'), mock.patch.object(m, 'EXECUTION_RELEASE', temp / 'release.json'), \
                 mock.patch.object(m.os, 'getpid', return_value=100):
                for defect in ('exact', 'wrong-exe', 'wrong-argv', 'wrong-uid', 'wrong-ppid', 'pid-reuse',
                               'unreadable'):
                    with self.subTest(defect=defect):
                        for path in temp.iterdir():
                            if path.name != 'boot':
                                if path.is_dir():
                                    for item in path.iterdir(): item.unlink()
                                    path.rmdir()
                                else: path.unlink()
                        kwargs = {}
                        if defect == 'wrong-exe': kwargs['exe'] = '/usr/bin/python3'
                        if defect == 'wrong-argv': kwargs['argv'] = [b'/usr/bin/sudo', b'-A', b'/usr/bin/python3']
                        if defect == 'wrong-uid': kwargs['uid'] = '1000 0 0 0'
                        if defect == 'wrong-ppid': kwargs['child_ppid'] = 201
                        if defect == 'unreadable': kwargs['unreadable'] = 'parent-cmdline'
                        fixture(temp, **kwargs)
                        if defect == 'exact':
                            self.assertEqual(m._direct_sudo_parent(temp), {
                                'parent': {'pid': 200, 'ppid': 1, 'starttime': 22},
                                'child': {'pid': 100, 'ppid': 200, 'starttime': 11}})
                        elif defect in ('wrong-exe', 'wrong-argv', 'wrong-uid'):
                            self.assertIsNone(m._direct_sudo_parent(temp))
                        elif defect == 'wrong-ppid':
                            with self.assertRaises(m.Error): m._direct_sudo_parent(temp)
                        elif defect == 'pid-reuse':
                            parent_stat = temp / '200' / 'stat'
                            original = parent_stat.read_bytes()
                            changed = original.replace(b'22', b'33', 1)
                            reads = [original, changed]
                            real_read_text = Path.read_text
                            def changing_read_text(path, *args, **kwargs):
                                if path == parent_stat:
                                    return reads.pop(0).decode()
                                return real_read_text(path, *args, **kwargs)
                            with mock.patch.object(Path, 'read_text', autospec=True,
                                                   side_effect=changing_read_text):
                                with self.assertRaises(m.Error): m._direct_sudo_parent(temp)
                        else:
                            with self.assertRaises(m.Error): m._direct_sudo_parent(temp)

    @staticmethod
    def census_stat(pid, ppid, start):
        fields = ['S', str(ppid), str(pid), str(pid)] + ['0'] * 15 + [str(start)]
        return ('%d (name with ) parentheses) %s\n' % (pid, ' '.join(fields))).encode()

    def census_fixture(self, proc):
        m = self.m
        for pid, ppid, start in ((100, 200, 11), (200, 1, 22), (300, 1, 33), (400, 1, 44)):
            row = proc / str(pid); row.mkdir()
            (row / 'stat').write_bytes(self.census_stat(pid, ppid, start))
            (row / 'cmdline').write_bytes(b'ordinary\0')
        argv = [b'/usr/bin/sudo', b'-A', b'/usr/bin/python3', b'-E', b'-s', b'-B',
                os.fsencode(str(m.PACKET)), b'--release', os.fsencode(str(m.EXECUTION_RELEASE))]
        (proc / '200' / 'cmdline').write_bytes(b'\0'.join(argv) + b'\0')
        (proc / '200' / 'status').write_text('Name:\tsudo\nUid:\t0 0 0 0\nGid:\t0 0 0 0\nvoluntary_ctxt_switches:\t1\n')
        os.symlink('/usr/bin/sudo', proc / '200' / 'exe')
        (proc / '300' / 'cmdline').write_bytes(b'qemu-system-x86_64\0')
        boot = proc / 'boot'; boot.write_text('boot\n')
        return boot, [{'pid': 300, 'starttime': 33}]

    def test_census_exact_sudo_and_identity_bound_launcher(self):
        m = self.m
        with tempfile.TemporaryDirectory() as directory, mock.patch.object(m.os, 'getpid', return_value=100):
            proc = Path(directory); boot, allowed = self.census_fixture(proc)
            self.assertEqual(m.validate_conflicts(proc, boot, allowed=allowed), 'boot')
            # A same-basename process elsewhere must still be rejected.
            (proc / '400' / 'cmdline').write_bytes((proc / '200' / 'cmdline').read_bytes())
            with self.assertRaisesRegex(m.Error, 'conflicting'):
                m.validate_conflicts(proc, boot, allowed=allowed)

    def test_census_sudo_exact_fields_and_unreadable_fail_closed(self):
        m = self.m
        defects = ('exe', 'argv', 'trailing-empty', 'missing-nul', 'uid', 'gid', 'ppid',
                   'missing-uid', 'duplicate-gid', 'malformed-uid', 'stat', 'cmdline', 'status',
                   'exe-unreadable', 'child-stat')
        for defect in defects:
            with self.subTest(defect=defect), tempfile.TemporaryDirectory() as directory, \
                    mock.patch.object(m.os, 'getpid', return_value=100):
                proc = Path(directory); boot, allowed = self.census_fixture(proc)
                parent = proc / '200'
                if defect == 'exe':
                    (parent / 'exe').unlink(); os.symlink('/usr/bin/other', parent / 'exe')
                elif defect in ('argv', 'trailing-empty', 'missing-nul'):
                    data = (parent / 'cmdline').read_bytes()
                    data = data.replace(b'-A\0', b'-n\0') if defect == 'argv' else data + b'\0' if defect == 'trailing-empty' else data[:-1]
                    (parent / 'cmdline').write_bytes(data)
                elif defect in ('uid', 'gid', 'missing-uid', 'duplicate-gid', 'malformed-uid'):
                    data = (parent / 'status').read_text()
                    if defect in ('uid', 'gid'):
                        key = defect.capitalize(); data = data.replace(key + ':\t0', key + ':\t1')
                    elif defect == 'missing-uid': data = data.replace('Uid:\t0 0 0 0\n', '')
                    elif defect == 'duplicate-gid': data += 'Gid:\t0 0 0 0\n'
                    else: data = data.replace('Uid:\t0', 'Uid:\tbad')
                    (parent / 'status').write_text(data)
                elif defect == 'ppid':
                    (proc / '100' / 'stat').write_bytes(self.census_stat(100, 0, 11))
                elif defect == 'exe-unreadable': (parent / 'exe').unlink()
                elif defect == 'child-stat': (proc / '100' / 'stat').unlink()
                else: (parent / defect).unlink()
                with self.assertRaises(m.Error):
                    m.validate_conflicts(proc, boot, allowed=allowed)

    def test_census_ignores_volatile_status_but_rejects_credential_churn(self):
        m = self.m
        for credentials_change in (False, True):
            with self.subTest(credentials_change=credentials_change), tempfile.TemporaryDirectory() as directory, \
                    mock.patch.object(m.os, 'getpid', return_value=100):
                proc = Path(directory); boot, allowed = self.census_fixture(proc)
                real_read = Path.read_text; reads = [0]
                def changing_status(path, *args, **kwargs):
                    data = real_read(path, *args, **kwargs)
                    if path == proc / '200' / 'status':
                        reads[0] += 1
                        data = data.replace('switches:\t1', 'switches:\t%d' % reads[0])
                        if credentials_change and reads[0] > 1: data = data.replace('Uid:\t0', 'Uid:\t1')
                    return data
                with mock.patch.object(Path, 'read_text', autospec=True, side_effect=changing_status):
                    if credentials_change:
                        with self.assertRaises(m.Error): m.validate_conflicts(proc, boot, allowed=allowed)
                    else:
                        self.assertEqual(m.validate_conflicts(proc, boot, allowed=allowed), 'boot')
                        self.assertGreaterEqual(reads[0], 6)

    def test_census_post_admission_churn_rejected_at_skip_and_completion(self):
        m = self.m
        for target in ('sudo', 'launcher'):
            for timing in ('before-skip', 'after-skip'):
                for defect in ('reuse', 'disappear', 'reparent', 'child-reuse', 'exe', 'argv', 'uid', 'gid') if target == 'sudo' else ('reuse', 'disappear'):
                    with self.subTest(target=target, timing=timing, defect=defect), \
                            tempfile.TemporaryDirectory() as directory, mock.patch.object(m.os, 'getpid', return_value=100):
                        proc = Path(directory); boot, allowed = self.census_fixture(proc)
                        victim = 200 if target == 'sudo' else 300
                        def mutate():
                            row = proc / str(victim)
                            if defect == 'reuse':
                                (row / 'stat').write_bytes(self.census_stat(victim, 1, 999))
                            elif defect == 'disappear':
                                for member in row.iterdir(): member.unlink()
                                row.rmdir()
                            elif defect == 'reparent': (proc / '100' / 'stat').write_bytes(self.census_stat(100, 400, 11))
                            elif defect == 'child-reuse': (proc / '100' / 'stat').write_bytes(self.census_stat(100, 200, 999))
                            elif defect == 'exe':
                                (row / 'exe').unlink(); os.symlink('/usr/bin/other', row / 'exe')
                            elif defect == 'argv':
                                (row / 'cmdline').write_bytes((row / 'cmdline').read_bytes() + b'\0')
                            else:
                                key = defect.capitalize()
                                (row / 'status').write_text((row / 'status').read_text().replace(key + ':\t0', key + ':\t1'))
                        real_iterdir = Path.iterdir
                        def census_rows(path):
                            if path != proc:
                                yield from real_iterdir(path); return
                            # Mutation happens only after the admission snapshot.
                            if timing == 'before-skip': mutate()
                            yield proc / str(victim)
                            if timing == 'after-skip': mutate()
                            for pid in (100, 200, 300, 400):
                                if pid != victim: yield proc / str(pid)
                        with mock.patch.object(Path, 'iterdir', autospec=True, side_effect=census_rows):
                            with self.assertRaises(m.Error):
                                m.validate_conflicts(proc, boot, allowed=allowed)

    def test_census_bare_pid_allowance_is_rejected(self):
        m = self.m
        with tempfile.TemporaryDirectory() as directory, mock.patch.object(m.os, 'getpid', return_value=100):
            proc = Path(directory); boot, _allowed = self.census_fixture(proc)
            for allowed in ([300], [{'pid': True, 'starttime': 33}],
                            [{'pid': 300, 'starttime': 33}, {'pid': 300, 'starttime': 33}]):
                with self.subTest(allowed=allowed), self.assertRaisesRegex(m.Error, 'identity schema'):
                    m.validate_conflicts(proc, boot, allowed=allowed)

    def test_runtime_admission_preserves_launcher_identity_through_census(self):
        m = self.m
        for defect in ('exact', 'reuse', 'disappear'):
            with self.subTest(defect=defect), tempfile.TemporaryDirectory() as directory, \
                    mock.patch.object(m.os, 'getpid', return_value=100):
                proc = Path(directory); boot, launchers = self.census_fixture(proc)
                runtime = {'boot_id': 'boot', 'launcher_identities': launchers,
                    'conflict_basenames': ['qemu-system-x86_64', 'qemu-system-aarch64', 'qemu-kvm', 'mcexec',
                        'native_rust_exact_build_container_owner.py', 'native_exact_candidate_retire.py',
                        'native_exact_candidate_quarantine_recover.py', 'native-exact-candidate-retirement-704f6654-1.py',
                        'native-exact-candidate-retirement-704f6654-2.py', 'native-exact-candidate-quarantine-recover-704f6654-1.py',
                        'native-exact-candidate-quarantine-recovery-execution-704f6654-1.sh'],
                    'heavy_lease_paths': [str(m.TOMBSTONE)],
                    'immutable_tombstone': {'path': str(m.TOMBSTONE), 'immutable': True, 'device': 1831, 'inode': 31474,
                        'sha256': '482bdf30e7320693c338832695932fdf1be261ed081de225e4cbdaf7e4c2c123'}}
                real_identity = m._proc_identity_pid
                def admitted_then_changed(pid, proc):
                    value = real_identity(pid, proc)
                    if defect == 'reuse':
                        (proc / str(pid) / 'stat').write_bytes(self.census_stat(pid, 1, 999))
                    elif defect == 'disappear':
                        for member in (proc / str(pid)).iterdir(): member.unlink()
                        (proc / str(pid)).rmdir()
                    return value
                observed = (1831, 31474, None, None, None, None, None, runtime['immutable_tombstone']['sha256'])
                with mock.patch.object(m, '_proc_identity_pid', side_effect=admitted_then_changed), \
                        mock.patch.object(m, 'tombstone_fd', return_value=(98765, observed)) as tombstone, \
                        mock.patch.object(m, 'revalidate_tombstone'), mock.patch.object(m.os, 'close'):
                    if defect == 'exact':
                        self.assertEqual(m.validate_runtime_admission(runtime, proc, boot), 'boot')
                    else:
                        with self.assertRaises(m.Error): m.validate_runtime_admission(runtime, proc, boot)
                        tombstone.assert_not_called()

    def test_descriptor_cleanup_is_bounded_and_closes_real_temporary_fds(self):
        m = self.m
        one, two = os.pipe()
        m.close_descriptors([one, two, None])
        for fd in (one, two):
            with self.assertRaises(OSError): os.fstat(fd)

    def test_full_write_short_and_delete_detects_same_size_and_symlink_replacement(self):
        m = self.m
        chunks = []
        m.full_write(7, b'abcdef', write=lambda _fd, data: chunks.append(data[:2]) or min(2, len(data)))
        self.assertEqual(b''.join(chunks), b'abcdef')
        with self.assertRaisesRegex(m.Error, 'short'):
            m.full_write(7, b'x', write=lambda _fd, _data: 0)
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); path = root / 'f'; path.write_bytes(b'one')
            info = m.member_identity(os.lstat(str(path)))
            wanted = dict(info, sha256=m.digest(b'one'))
            path.write_bytes(b'two')
            fd = os.open(str(root), os.O_RDONLY | os.O_DIRECTORY)
            try:
                with self.assertRaisesRegex(m.Error, 'hash'):
                    m._verify_delete_entry(fd, 'f', wanted, 'f')
            finally:
                os.close(fd)

    def test_survivor_ledger_observes_identity_and_failure_is_not_swallowed(self):
        m = self.m
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp); claim = base / 'claim'; claim.write_text('x')
            with mock.patch.object(m, 'CLAIM', claim), mock.patch.object(m, 'JOURNAL', base / 'journal'), \
                 mock.patch.object(m, 'OUTPUT', base / 'output'), mock.patch.object(m, 'ORIGINALS', (base / 'o1', base / 'o2')), \
                 mock.patch.object(m, 'QUARANTINES', (base / 'q1', base / 'q2')):
                ledger = m.survivor_ledger()
            self.assertTrue(ledger['claim']['present'])
            self.assertIn('inode', ledger['claim'])

    def test_delete_rejects_symlink_and_child_replacement(self):
        m = self.m
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); (root / 'd').mkdir(); (root / 'd' / 'f').write_text('x'); os.symlink('f', str(root / 'link'))
            symlink = m.member_identity(os.lstat(str(root / 'link')))
            wanted_link = dict(symlink, target='f', sha256=m.digest(b'f'))
            os.unlink(str(root / 'link')); os.symlink('d/f', str(root / 'link'))
            fd = os.open(str(root), os.O_RDONLY | os.O_DIRECTORY)
            try:
                with self.assertRaisesRegex(m.Error, 'identity changed|symlink target'):
                    m._verify_delete_entry(fd, 'link', wanted_link, 'link')
            finally:
                os.close(fd)

    def test_actual_observer_producer_schema(self):
        m = self.m
        spec = importlib.util.spec_from_file_location('observer704f', m.OBSERVER)
        observer = importlib.util.module_from_spec(spec); spec.loader.exec_module(observer)
        expected = [{}, {}]
        rows = []
        for _o, q, d, i in m.ROOTS:
            info = types.SimpleNamespace(st_dev=d, st_ino=i, st_uid=0, st_gid=0, st_mode=stat.S_IFDIR | 0o700)
            rows.append((info, {tuple(observer.node_identity(info))}, 900 + len(rows), []))
        closure = dict(records=[], final_live=set(), closure_passes=1, denials=[], references=[],
                       replacements=[], missing_final=set(), nonconvergent=False, incomplete=False, clean=True)
        with mock.patch.object(observer, 'open_tree', side_effect=rows), \
             mock.patch.object(observer, 'mount_rows', return_value=[]), \
             mock.patch.object(observer, 'coordinate', return_value=('0:26', '/', {})), \
             mock.patch.object(observer, 'canonical', return_value={}), \
             mock.patch.object(observer, 'closure_round', return_value=closure), \
             mock.patch.object(observer, 'revalidate_tree', return_value=None), \
             mock.patch.object(observer, 'emit_progress'), \
             mock.patch.object(observer, 'source_hash', return_value=m.OBSERVER_SHA), \
             mock.patch.object(observer, 'starttime', return_value='12345'), \
             mock.patch.object(observer.Path, 'read_text', return_value='boot'), \
             mock.patch.object(observer.os, 'close'):
            value = json.loads(json.dumps(observer.observe(m.QUARANTINES)))
        m.validate_observer(value, expected, admitted_boot='boot', launched=(os.getpid(), 12345))
        for start in (12345, '+12345', '12345 ', '1.2', ''):
            changed = copy.deepcopy(value); changed['observer_starttime'] = start
            with self.assertRaises(m.Error):
                m.validate_observer(changed, expected, admitted_boot='boot', launched=(os.getpid(), 12345))
        for field in ('uid', 'gid', 'device', 'tree_root_identity', 'tree_membership_sha256'):
            changed = copy.deepcopy(value); changed['roots'][0][field] = 'bad'
            with self.assertRaises(m.Error): m.validate_observer(changed, expected)

    def test_capture_attempts_fsync_close_and_parent_after_write_failure(self):
        m = self.m
        calls = []
        with mock.patch.object(m, 'exclusive_fd', return_value=77), \
             mock.patch.object(m, 'full_write', side_effect=OSError('write-fault')), \
             mock.patch.object(m.os, 'fsync', side_effect=lambda fd: calls.append('fsync') or (_ for _ in ()).throw(OSError('fsync-fault'))), \
             mock.patch.object(m.os, 'close', side_effect=lambda fd: calls.append('close') or (_ for _ in ()).throw(OSError('close-fault'))), \
             mock.patch.object(m, 'fsync_dir', side_effect=lambda path: calls.append('parent') or (_ for _ in ()).throw(OSError('parent-fault'))):
            with self.assertRaises(m.Error) as raised:
                m.exclusive_bytes(Path('/unused'), b'x')
        self.assertEqual(calls, ['fsync', 'close', 'parent'])
        text = json.dumps(m.error_record(raised.exception))
        for word in ('write-fault', 'fsync-fault', 'close-fault', 'parent-fault'):
            self.assertIn(word, text)

    def test_terminal_faults_keep_primary_and_all_cleanup_errors(self):
        m = self.m
        docker_rows, _release = self.docker_fixture()
        for faults in ({'primary'}, {'close'}, {'journal'}, {'status'}, {'primary', 'close', 'journal', 'status'}):
            with self.subTest(faults=faults), tempfile.TemporaryDirectory() as temp, ExitStack() as stack:
                base = Path(temp); tomb = base / 'tomb'; tomb.write_bytes(b'kept')
                fd = os.open(str(tomb), os.O_RDONLY)
                for key, value in dict(SOURCE_TEMPLATE_ONLY=False, SCRATCH=base, CLAIM=base / 'claim',
                                       JOURNAL=base / 'journal', OUTPUT=base / 'output', ROOTS=(),
                                       ORIGINALS=(), QUARANTINES=()).items():
                    stack.enter_context(mock.patch.object(m, key, value))
                for name in ('validate_authorities', 'validate_raw_history', 'validate_capacity',
                             'revalidate_tombstone', 'reopen_tombstone', 'validate_docker'):
                    stack.enter_context(mock.patch.object(m, name))
                stack.enter_context(mock.patch.object(m, 'validate_runtime_admission', return_value='boot'))
                stack.enter_context(mock.patch.object(m, 'tombstone_fd', return_value=(fd, ())))
                stack.enter_context(mock.patch.object(m, 'validate_quarantines', return_value=[]))
                stack.enter_context(mock.patch.object(m, 'docker_census', return_value=docker_rows))
                stack.enter_context(mock.patch.object(m, 'seal_and_run_observer',
                                                     side_effect=RuntimeError('primary-fault') if 'primary' in faults else None))
                close, append, write = m.os.close, m.append_journal, m.exclusive_json
                def closing(target):
                    close(target)
                    if target == fd and 'close' in faults: raise OSError('close-fault')
                def journal(target, phase, **fields):
                    append(target, phase, **fields)
                    if phase.startswith('terminal-') and 'journal' in faults: raise OSError('journal-fault')
                def output(path, value):
                    if path.name == 'terminal.json' and 'status' in faults: raise OSError('status-fault')
                    write(path, value)
                stack.enter_context(mock.patch.object(m.os, 'close', side_effect=closing))
                stack.enter_context(mock.patch.object(m, 'append_journal', side_effect=journal))
                stack.enter_context(mock.patch.object(m, 'exclusive_json', side_effect=output))
                with self.assertRaises(BaseException) as caught:
                    m.execute_final({'runtime': {}})
                record = json.loads((base / 'output' / 'terminal-failure.json').read_text())
                combined = json.dumps(record) + str(caught.exception)
                for word in faults: self.assertIn(word + '-fault', combined)
                self.assertEqual(record['status'], 'FAIL_RETAINED')
                self.assertTrue((base / 'claim').exists())
                self.assertTrue((base / 'native-exact-candidate-quarantine-recovery-704f6654-1.survivors.json').exists())
                before = json.loads((base / 'output' / 'docker.before.json').read_text())
                self.assertEqual(before['schema'], 'mckernel.docker-census-safe-summary.v1')
                for path in (base / 'output').glob('*.json'):
                    self.assertNotIn(b'synthetic-private', path.read_bytes())

    def assert_failure_tree(self, error, *messages):
        encoded = json.dumps(self.m.error_record(error))
        for message in messages:
            self.assertIn(message, encoded)

    def test_file_hash_and_child_cleanup_failures_are_both_serialized(self):
        m = self.m
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); file = root / 'file'; file.write_bytes(b'changed')
            wanted = dict(m.member_identity(os.lstat(str(file))), sha256=m.digest(b'old'))
            parent = os.open(str(root), os.O_RDONLY | os.O_DIRECTORY)
            close = os.close
            def closing(fd):
                close(fd)
                raise OSError('file-close-fault')
            try:
                with mock.patch.object(m.os, 'close', side_effect=closing):
                    with self.assertRaises(m.Error) as caught:
                        m._verify_delete_entry(parent, 'file', wanted, 'file')
                self.assert_failure_tree(caught.exception, 'delete file hash changed', 'file-close-fault')
                self.assertTrue(file.exists())
            finally: close(parent)
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); child = root / 'child'; child.mkdir(); (child / 'unlisted').write_bytes(b'x')
            expected = {'child': m.member_identity(os.lstat(str(child)))}
            parent = os.open(str(root), os.O_RDONLY | os.O_DIRECTORY)
            try:
                with mock.patch.object(m.os, 'close', side_effect=closing):
                    with self.assertRaises(m.Error) as caught:
                        m.delete_dirfd(parent, expected, lambda *a, **k: None, 'fixture')
                self.assert_failure_tree(caught.exception, 'delete-before-proof membership', 'file-close-fault')
                self.assertTrue((child / 'unlisted').exists())
            finally: close(parent)

    def test_regular_read_fsync_exclusive_and_tombstone_cleanup_failures(self):
        m = self.m
        scenarios = (
            ('read', lambda: m.read_regular(Path('/unused')), 'read-fault'),
            ('fsync', lambda: m.fsync_dir(Path('/unused')), 'fsync-fault'),
            ('exclusive', lambda: m.exclusive_fd(Path('/unused')), 'parent-fault'),
            ('reopen', lambda: m.reopen_tombstone(('wanted',)), 'tombstone-fault'),
            ('tombstone-open', lambda: m.tombstone_fd(Path('/unused')), 'fstat-fault'),
        )
        for name, action, primary in scenarios:
            with self.subTest(name=name), ExitStack() as stack:
                stack.enter_context(mock.patch.object(m.os, 'open', return_value=71))
                stack.enter_context(mock.patch.object(m.os, 'close', side_effect=OSError('close-fault')))
                if name == 'read':
                    stack.enter_context(mock.patch.object(m.os, 'fstat',
                        return_value=types.SimpleNamespace(st_mode=stat.S_IFREG | 0o600, st_nlink=1)))
                    stack.enter_context(mock.patch.object(m.os, 'read', side_effect=OSError(primary)))
                elif name == 'fsync':
                    stack.enter_context(mock.patch.object(m.os, 'fsync', side_effect=OSError(primary)))
                elif name == 'exclusive':
                    stack.enter_context(mock.patch.object(m, 'fsync_dir', side_effect=OSError(primary)))
                elif name == 'reopen':
                    stack.enter_context(mock.patch.object(m, 'tombstone_fd', return_value=(71, ('wanted',))))
                    stack.enter_context(mock.patch.object(m, 'revalidate_tombstone', side_effect=OSError(primary)))
                else:
                    stack.enter_context(mock.patch.object(m.os, 'fstat', side_effect=OSError(primary)))
                with self.assertRaises(m.Error) as caught: action()
                self.assert_failure_tree(caught.exception, primary, 'close-fault')

    def test_observer_seal_read_and_runner_cleanup_failures(self):
        m = self.m
        for stage in ('write', 'read', 'runner'):
            with self.subTest(stage=stage), tempfile.TemporaryDirectory() as temp, ExitStack() as stack:
                base = Path(temp); source = b'fixture'
                (base / 'observer.sealed.py').write_bytes(source)
                stack.enter_context(mock.patch.object(m, 'OUTPUT', base))
                stack.enter_context(mock.patch.object(m, 'checked', return_value=source))
                stack.enter_context(mock.patch.object(m, 'OBSERVER_SHA', m.digest(source)))
                close = os.close
                def closing(fd):
                    close(fd)
                    raise OSError('observer-close-fault')
                stack.enter_context(mock.patch.object(m.os, 'close', side_effect=closing))
                if stage == 'write':
                    # Exercise the same exclusive_bytes scope used by sealing.
                    stack.enter_context(mock.patch.object(m, 'exclusive_fd',
                        side_effect=lambda p: os.open(str(p), os.O_WRONLY)))
                    stack.enter_context(mock.patch.object(m, 'full_write', side_effect=OSError('write-fault')))
                    stack.enter_context(mock.patch.object(m, 'fsync_dir'))
                else:
                    stack.enter_context(mock.patch.object(m, 'exclusive_bytes'))
                    if stage == 'read':
                        stack.enter_context(mock.patch.object(m.os, 'read', side_effect=OSError('read-fault')))
                    else:
                        stack.enter_context(mock.patch.object(m, 'run_sealed_observer',
                                                            side_effect=RuntimeError('runner-fault')))
                with self.assertRaises(m.Error) as caught: m.seal_and_run_observer([], 'boot')
                self.assert_failure_tree(caught.exception, stage + '-fault', 'observer-close-fault')

    def test_terminal_latch_has_two_saturating_slots(self):
        m = self.m
        latch = m.TerminalSignalLatch()
        first = None
        for index in range(latch.COUNT_LIMIT + 20):
            for sig in (signal.SIGTERM, signal.SIGINT):
                latch.record(sig)
            if index == 0:
                first = latch.rows[signal.SIGTERM][0]
        self.assertEqual(len(latch.rows), 2)
        for event, count, overflow in latch.rows.values():
            self.assertIsInstance(event, m.Interrupted)
            self.assertEqual(count, latch.COUNT_LIMIT)
            self.assertTrue(overflow)
        self.assertIs(latch.rows[signal.SIGTERM][0], first)
        mask = signal.pthread_sigmask(signal.SIG_BLOCK, {signal.SIGTERM, signal.SIGINT})
        try: snapshot = latch.detach()
        finally: signal.pthread_sigmask(signal.SIG_SETMASK, mask)
        self.assertEqual(len(snapshot), 2)
        self.assertEqual(len(latch.rows), 2)
        self.assertTrue(all(row == [None, 0, False] for row in latch.rows.values()))

    def test_term_during_terminal_journal_and_ledgers_is_durably_latched(self):
        m = self.m
        for trigger in ('journal', 'terminal', 'survivors', 'blocked-ledger', 'continuous-storm'):
            with self.subTest(trigger=trigger), tempfile.TemporaryDirectory() as temp, ExitStack() as stack:
                base = Path(temp); tomb = base / 'tomb'; tomb.write_bytes(b'kept')
                fd = os.open(str(tomb), os.O_RDONLY)
                for key, value in dict(SOURCE_TEMPLATE_ONLY=False, SCRATCH=base, CLAIM=base / 'claim',
                                       JOURNAL=base / 'journal', OUTPUT=base / 'output', ROOTS=(),
                                       ORIGINALS=(), QUARANTINES=()).items():
                    stack.enter_context(mock.patch.object(m, key, value))
                for name in ('validate_authorities', 'validate_raw_history', 'validate_capacity',
                             'revalidate_tombstone', 'reopen_tombstone', 'validate_docker'):
                    stack.enter_context(mock.patch.object(m, name))
                stack.enter_context(mock.patch.object(m, 'validate_runtime_admission', return_value='boot'))
                stack.enter_context(mock.patch.object(m, 'tombstone_fd', return_value=(fd, ())))
                stack.enter_context(mock.patch.object(m, 'validate_quarantines', return_value=[]))
                stack.enter_context(mock.patch.object(m, 'docker_census', return_value=[]))
                stack.enter_context(mock.patch.object(m, 'seal_and_run_observer',
                    side_effect=RuntimeError('primary-fault') if trigger in ('survivors', 'blocked-ledger') else None))
                append, write = m.append_journal, m.exclusive_json
                prior_handlers = {sig: signal.getsignal(sig) for sig in (signal.SIGTERM, signal.SIGINT)}
                prior_mask = signal.pthread_sigmask(signal.SIG_BLOCK, [])
                sent = []
                def terminate():
                    self.assertNotEqual(signal.getsignal(signal.SIGTERM), prior_handlers[signal.SIGTERM])
                    sent.append(True)
                    os.kill(os.getpid(), signal.SIGTERM)
                def journal(target, phase, **fields):
                    if trigger == 'journal' and phase == 'terminal-success':
                        terminate()
                    if trigger == 'continuous-storm' and phase == 'terminal-success':
                        # Deliver beyond the counter cap with no per-event
                        # allocation, then emulate continuous pending arrivals
                        # at every bounded terminal reconciliation attempt.
                        for _ in range(m.TerminalSignalLatch.COUNT_LIMIT + 3):
                            signal.getsignal(signal.SIGTERM)(signal.SIGTERM, None)
                        sent.append(True)
                    append(target, phase, **fields)
                def output(path, value):
                    fire = ((trigger == 'terminal' and path.name == 'terminal.json') or
                            (trigger == 'survivors' and path.name.endswith('.survivors.json')) or
                            (trigger == 'blocked-ledger' and path.name.endswith('.terminal-signal-0.json')))
                    if fire: terminate()
                    write(path, value)
                stack.enter_context(mock.patch.object(m, 'append_journal', side_effect=journal))
                stack.enter_context(mock.patch.object(m, 'exclusive_json', side_effect=output))
                snapshots = []
                if trigger == 'continuous-storm':
                    stack.enter_context(mock.patch.object(m.signal, 'sigpending',
                                                         return_value={signal.SIGTERM, signal.SIGINT}))
                    stack.enter_context(mock.patch.object(m.signal, 'sigtimedwait',
                        side_effect=lambda values, timeout: types.SimpleNamespace(si_signo=next(iter(values)))))
                    detach = m.TerminalSignalLatch.detach
                    def detached(latch):
                        self.assertTrue({signal.SIGTERM, signal.SIGINT}.issubset(
                            signal.pthread_sigmask(signal.SIG_BLOCK, [])))
                        snapshot = detach(latch)
                        self.assertEqual(len(snapshot), 2)
                        self.assertTrue(all(0 <= row[1] <= latch.COUNT_LIMIT for row in snapshot.values()))
                        snapshots.append(snapshot)
                        return snapshot
                    stack.enter_context(mock.patch.object(m.TerminalSignalLatch, 'detach', detached))
                try:
                    with self.assertRaises(m.Interrupted) as caught:
                        m.execute_final({'runtime': {}})
                    self.assertTrue(sent)
                    self.assert_failure_tree(caught.exception, 'signal 15')
                    records = list((base / 'output').glob('*terminal-signal-*.json'))
                    self.assertTrue(records)
                    latest = json.loads(sorted(records)[-1].read_text())
                    self.assertEqual(latest['status'], 'FAIL_RETAINED')
                    self.assertIn('signal 15', json.dumps(latest))
                    if trigger == 'continuous-storm':
                        self.assertIn('mask retained', str(caught.exception))
                        self.assertEqual(len(records), 8)
                        self.assertLessEqual(len(snapshots), 16)
                        self.assertTrue({signal.SIGTERM, signal.SIGINT}.issubset(
                            signal.pthread_sigmask(signal.SIG_BLOCK, [])))
                        recorded = (base / 'output' / 'terminal.json').read_text()
                        self.assertIn(r'\"count\":65535', recorded)
                        self.assertIn(r'\"overflow\":true', recorded)
                    else:
                        for sig, handler in prior_handlers.items():
                            self.assertEqual(signal.getsignal(sig), handler)
                        self.assertEqual(signal.pthread_sigmask(signal.SIG_BLOCK, []), prior_mask)
                finally:
                    for sig, handler in prior_handlers.items(): signal.signal(sig, handler)
                    signal.pthread_sigmask(signal.SIG_SETMASK, prior_mask)

    def test_delete_root_replacement_and_interrupted_partial_deletion(self):
        m = self.m
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); (root / 'a').write_bytes(b'a'); (root / 'b').write_bytes(b'b')
            expected = {name: dict(m.member_identity(os.lstat(str(root / name))), sha256=m.digest(name.encode()))
                        for name in ('a', 'b')}
            fd = os.open(str(root), os.O_RDONLY | os.O_DIRECTORY)
            def journal(phase, **row):
                if phase == 'after-entry': raise KeyboardInterrupt()
            try:
                with self.assertRaises(KeyboardInterrupt): m.delete_dirfd(fd, expected, journal, 'temp')
            finally: os.close(fd)
            self.assertFalse((root / 'a').exists()); self.assertTrue((root / 'b').exists())
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / 'q'; root.mkdir(); os.chmod(str(root), 0o700)
            info = os.lstat(str(root))
            # Test root name/descriptor replacement with current user ownership.
            original = m._same_member
            def same(info, wanted):
                wanted = dict(wanted, uid=os.getuid(), gid=os.getgid())
                return original(info, wanted)
            def replace(phase, **row):
                if phase == 'before-root':
                    root.rename(root.parent / 'old'); root.mkdir()
            with mock.patch.object(m, '_same_member', side_effect=same):
                with self.assertRaises(m.Error):
                    m.remove_quarantine(root, info.st_dev, info.st_ino, {}, replace)
            self.assertTrue(root.exists()); self.assertTrue((root.parent / 'old').exists())

    def test_observer_failure_status_write_still_has_failure_capture(self):
        m = self.m
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp); source = base / 'observer'; source.write_text('import sys; print("kept"); sys.exit(7)\n')
            fd = os.open(str(source), os.O_RDONLY)
            original = m.exclusive_json
            def write(path, value):
                if path.name == 'observer.status.json': raise OSError('status-fault')
                original(path, value)
            try:
                with mock.patch.object(m, 'OUTPUT', base), mock.patch.object(m, 'exclusive_json', side_effect=write):
                    with self.assertRaises(m.Error) as caught: m.run_sealed_observer(fd, (), timeout=2)
                self.assertIn('status-fault', str(caught.exception))
                self.assertEqual((base / 'observer.stdout').read_bytes(), b'kept\n')
                result = json.loads((base / 'observer.failure.json').read_text())
                self.assertEqual(result['survivors'], [])
            finally: os.close(fd)

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
