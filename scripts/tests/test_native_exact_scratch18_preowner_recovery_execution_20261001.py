"""Disposable source admission tests; no real observer or recovery execution."""
import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

SOURCE = Path(__file__).resolve().parents[2] / 'docs/verification/evidence/native-exact-scratch18-preowner-recovery-execution-20261001.py'
COMMIT = 'a' * 40


class Release(unittest.TestCase):
    def setUp(self):
        spec = importlib.util.spec_from_file_location('release', SOURCE)
        self.m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.m)
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.m.REPO = self.root / 'repo'
        self.m.REPO.mkdir()
        self.calls = []
        self.blobs = {}
        for path in (*self.m.DEPENDENCIES, self.m.PACKET, self.m.TEST):
            self.put(path, ('synthetic:' + path).encode())
        self.helper({'status': 'PASS_VALIDATE_ONLY', 'state': 0, 'terminal': False})
        self.m.REQUEST = self.record('request.json', b'{"x":1}\n')
        self.m.REQUEST['normalized_sha256'] = self.m.sha(b'{"x":1}')
        self.m.LOCKS = {key: self.record(key, key.encode()) for key in ('attempt', 'shared')}
        failure = {'request': {k: v for k, v in self.m.REQUEST.items() if k != 'device'},
                   'retained_locks': {key: {k: v for k, v in row.items() if k != 'device'}
                                      for key, row in self.m.LOCKS.items()}}
        # The production evidence has a fixed scratch device; emulate that
        # binding in failure dictionaries while the real file check uses tempfs.
        for row in (self.m.REQUEST, *self.m.LOCKS.values()):
            row['device'] = 1831
        self.put(self.m.FAILURE, json.dumps(failure).encode())
        self.m.DEPENDENCIES = {p: self.m.sha(self.blobs[p]) for p in self.m.DEPENDENCIES}
        original = self.m.read_regular
        def read(path, record=None):
            if record is not None:
                record = dict(record, device=os.stat(self.root).st_dev)
            return original(path, record)
        self.read_patch = mock.patch.object(self.m, 'read_regular', side_effect=read)
        self.read_patch.start()
        self.addCleanup(self.read_patch.stop)
        self.git_patch = mock.patch.object(self.m, 'git', side_effect=self.git)
        self.git_patch.start()
        self.addCleanup(self.git_patch.stop)

    def put(self, path, raw):
        target = self.m.REPO / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
        self.blobs[path] = raw

    def success(self):
        archive = self.m.ROOT / 'native-exact-scratch18-preowner-archives'
        return {'status': 'PASS', 'plan_sha256': 'a' * 64,
                'journal': str(archive / 'journal.jsonl'),
                'archives': [str(archive / 'attempt.archive'), str(archive / 'shared.archive')]}

    def helper(self, result, body=None):
        if body is None:
            body = 'return ' + repr(self.success())
        self.put(self.m.HELPER, ('calls = []\n'
                                'def recover(execute=False):\n'
                                '    calls.append(execute)\n'
                                '    if execute:\n'
                                '        ' + body + '\n'
                                '    return ' + repr(result) + '\n').encode())
        if self.m.HELPER in self.m.DEPENDENCIES:
            self.m.DEPENDENCIES = dict(self.m.DEPENDENCIES,
                                       **{self.m.HELPER: self.m.sha(self.blobs[self.m.HELPER])})

    def record(self, name, data):
        path = self.root / name
        path.write_bytes(data)
        path.chmod(0o600)
        st = path.stat()
        return {'path': str(path), 'sha256': self.m.sha(data), 'device': st.st_dev,
                'inode': st.st_ino, 'mode': '0600', 'uid': st.st_uid, 'gid': st.st_gid}

    def git(self, args):
        self.calls.append(args)
        if args[0] == 'rev-parse':
            return (COMMIT + '\n').encode()
        if args[0] == 'show':
            return self.blobs[args[1].split(':', 1)[1]]
        return b''

    def run_main(self, execute=False):
        with contextlib.redirect_stdout(io.StringIO()):
            return self.m.main(['--release-commit', COMMIT] + (['--execute'] if execute else []))

    def test_default_no_mutation_and_all_fetched_gates(self):
        before = {str(p): p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        with mock.patch.object(self.m.os, 'execv') as execute:
            self.assertEqual(self.run_main(), 0)
            execute.assert_not_called()
        self.assertEqual(before, {str(p): p.read_bytes() for p in self.root.rglob('*') if p.is_file()})
        for ancestor in self.m.ANCESTORS:
            self.assertIn(['merge-base', '--is-ancestor', ancestor, COMMIT], self.calls)
        self.assertIn(['cat-file', 'commit', COMMIT], self.calls)
        self.assertEqual(len([c for c in self.calls if c[0] == 'show']), 2 * len(self.blobs))

    def test_execute_bound_module_once_after_all_checks_without_path_exec(self):
        admitted = []
        original = self.m.admit
        def capture(commit):
            module, result = original(commit)
            self.assertEqual(module.calls, [False])
            self.assertEqual(len([c for c in self.calls if c[0] == 'rev-parse']), 2)
            admitted.append(module)
            # Replacing the pathname after validation must not replace the
            # authenticated code that is actually invoked.
            (self.m.REPO / self.m.HELPER).write_bytes(b'raise AssertionError("reopened path")')
            return module, result
        with mock.patch.object(self.m, 'admit', side_effect=capture), mock.patch.object(self.m.os, 'execv') as execute:
            self.assertEqual(self.run_main(True), 0)
            execute.assert_not_called()
        self.assertEqual(admitted[0].calls, [False, True])
        self.assertEqual(len([c for c in self.calls if c[0] == 'rev-parse']), 2)

    def test_execution_result_strict_and_single_invocation(self):
        success = self.success()
        for bad in (None, {}, dict(success, status='FAIL'), dict(success, extra=1),
                    dict(success, plan_sha256='A' * 64), dict(success, plan_sha256=3),
                    dict(success, journal='/other'), dict(success, archives=list(reversed(success['archives'])))):
            self.helper({'status': 'PASS_VALIDATE_ONLY', 'state': 0, 'terminal': False},
                        body='return ' + repr(bad))
            admitted = []
            original = self.m.admit
            def capture(commit):
                module, result = original(commit)
                admitted.append(module)
                return module, result
            with self.subTest(result=bad), mock.patch.object(self.m, 'admit', side_effect=capture), mock.patch.object(self.m.os, 'execv') as execute:
                self.assertEqual(self.run_main(True), 1)
                execute.assert_not_called()
            self.assertEqual(admitted[0].calls, [False, True])

    def test_mutation_exception_never_retries(self):
        for exception in ('ValueError', 'OSError', 'RuntimeError'):
            self.helper({'status': 'PASS_VALIDATE_ONLY', 'state': 0, 'terminal': False},
                        body='raise ' + exception + '("mutation failed")')
            admitted = []
            original = self.m.admit
            def capture(commit):
                module, result = original(commit)
                admitted.append(module)
                return module, result
            with self.subTest(exception=exception), mock.patch.object(self.m, 'admit', side_effect=capture), mock.patch.object(self.m.os, 'execv') as execute:
                if exception == 'RuntimeError':
                    with self.assertRaisesRegex(RuntimeError, 'mutation failed'):
                        self.run_main(True)
                else:
                    self.assertEqual(self.run_main(True), 1)
                execute.assert_not_called()
            self.assertEqual(admitted[0].calls, [False, True])

    def test_hash_mismatch_never_executes(self):
        (self.m.REPO / self.m.HELPER).write_bytes(b'raise AssertionError("must not import")')
        with mock.patch.object(self.m.os, 'execv') as execute:
            self.assertEqual(self.run_main(True), 1)
            execute.assert_not_called()

    def test_every_blob_binding(self):
        for path in self.blobs:
            with self.subTest(path=path):
                raw = self.blobs[path]
                self.blobs[path] = b'foreign blob'
                with self.assertRaisesRegex(self.m.Refusal, 'release-blob'):
                    self.m.sources(COMMIT)
                self.blobs[path] = raw

    def test_ref_fetched_and_each_ancestry_fail_closed(self):
        for command in ('rev-parse', 'cat-file', *self.m.ANCESTORS):
            def reject(args):
                if args[0] == command or (args[0] == 'merge-base' and args[2] == command):
                    raise self.m.Refusal('synthetic gate refusal')
                return self.git(args)
            with self.subTest(command=command), mock.patch.object(self.m, 'git', side_effect=reject), mock.patch.object(self.m.os, 'execv') as execute:
                self.assertEqual(self.run_main(True), 1)
                execute.assert_not_called()
        with mock.patch.object(self.m, 'git', return_value=b'b' * 40):
            with self.assertRaisesRegex(self.m.Refusal, 'release-ref-mismatch'):
                self.m.sources(COMMIT)

    def test_bad_commit_never_calls_git(self):
        for commit in ('HEAD', 'a' * 39, 'A' * 40, COMMIT + ':x'):
            with self.assertRaisesRegex(self.m.Refusal, 'release-commit'):
                self.m.sources(commit)
        self.assertFalse(self.calls)

    def test_lock_and_request_inode_and_mode_binding(self):
        for row in (self.m.REQUEST, *self.m.LOCKS.values()):
            for key, value in (('inode', -1), ('mode', '0644'), ('uid', -1), ('gid', -1), ('sha256', 'f' * 64)):
                old = row[key]
                row[key] = value
                with self.subTest(path=row['path'], key=key), self.assertRaises(self.m.Refusal):
                    self.m.admit(COMMIT)
                row[key] = old

    def test_replaced_inode_real_file_refuses(self):
        path = Path(self.m.REQUEST['path'])
        replacement = path.with_suffix('.replacement')
        replacement.write_bytes(path.read_bytes())
        replacement.chmod(0o600)
        replacement.replace(path)
        with self.assertRaisesRegex(self.m.Refusal, 'artifact-binding'):
            self.m.admit(COMMIT)

    def test_symlink_hardlink_and_parent_symlink_refuse(self):
        target = self.m.REPO / self.m.HELPER
        saved = target.with_suffix('.saved')
        target.rename(saved)
        target.symlink_to(saved)
        with self.assertRaises(OSError):
            self.m.sources(COMMIT)
        target.unlink()
        os.link(saved, target)
        with self.assertRaisesRegex(self.m.Refusal, 'artifact-shape'):
            self.m.sources(COMMIT)
        target.unlink()
        saved.rename(target)
        alias = self.root / 'alias'
        alias.symlink_to(self.m.REPO, target_is_directory=True)
        with self.assertRaises(OSError):
            self.m.read_regular(alias / self.m.HELPER)

    def test_state_terminal_and_malformed_results_refuse(self):
        for result in ({'status': 'PASS_VALIDATE_ONLY', 'state': 1, 'terminal': False},
                       {'status': 'PASS_VALIDATE_ONLY', 'state': 2, 'terminal': True},
                       {'status': 'PASS_VALIDATE_ONLY', 'state': 0, 'terminal': True},
                       {'status': 'PASS_VALIDATE_ONLY', 'state': False, 'terminal': False},
                       {'status': 'PASS'}, None):
            self.helper(result)
            with self.subTest(result=result), mock.patch.object(self.m.os, 'execv') as execute:
                self.assertEqual(self.run_main(True), 1)
                execute.assert_not_called()

    def test_post_census_ref_change_refuses(self):
        count = 0
        def changing(args):
            nonlocal count
            if args[0] == 'rev-parse':
                count += 1
                if count == 2:
                    return b'b' * 40
            return self.git(args)
        with mock.patch.object(self.m, 'git', side_effect=changing), mock.patch.object(self.m.os, 'execv') as execute:
            self.assertEqual(self.run_main(True), 1)
            execute.assert_not_called()

    def test_canonical_hash_refuses(self):
        self.m.REQUEST['normalized_sha256'] = 'f' * 64
        failure = json.loads(self.blobs[self.m.FAILURE])
        failure['request']['normalized_sha256'] = 'f' * 64
        self.put(self.m.FAILURE, json.dumps(failure).encode())
        self.m.DEPENDENCIES[self.m.FAILURE] = self.m.sha(self.blobs[self.m.FAILURE])
        with self.assertRaisesRegex(self.m.Refusal, 'request-canonical-binding'):
            self.m.admit(COMMIT)


if __name__ == '__main__':
    unittest.main()
