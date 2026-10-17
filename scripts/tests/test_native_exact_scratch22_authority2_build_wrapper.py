#!/usr/bin/env python3
"""Disposable tests: no Docker, sudo, compiler, network or real preparation."""
from contextlib import ExitStack
import ast
import importlib.util
import json
import os
import fcntl
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest import mock

PATH = Path(__file__).parents[1] / 'native_exact_scratch22_authority2_build_wrapper.py'
SPEC = importlib.util.spec_from_file_location('scratch22-authority2_build_wrapper', PATH)
M = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(M)


class Quarantined(BaseException):
    pass


def retired():
    # Preserve the existing reviewed owner receipt contract verbatim.
    return dict(status='PASS', retired=True, cleanup_separately_required=True,
                terminal_container_retained=True, terminal_container_info_current=True,
                terminal_container_info={'State': {'Running': False, 'Pid': 0}})


class WrapperTests(unittest.TestCase):
    def preparation_fixture(self, stack):
        temp = Path(stack.enter_context(tempfile.TemporaryDirectory()))
        source = temp / 'source'
        source.mkdir()
        scratch = temp / 'scratch'
        scratch.mkdir()
        stack.enter_context(mock.patch.object(M, 'REPO', source))
        stack.enter_context(mock.patch.object(M, 'ROOT', scratch))
        for key in ('CANDIDATE', 'PREP', 'MANIFEST', 'EXECUTION', 'OUTPUT', 'EVIDENCE',
                    'LEASE', 'EXCLUSION', 'SHARED', 'STDOUT', 'STDERR', 'TERMINAL',
                    'QUARANTINE', 'PREP_TERMINAL', 'PREP_LOG'):
            stack.enter_context(mock.patch.object(M, key, scratch / getattr(M, key).name))
        M.CANDIDATE.mkdir()
        M.OUTPUT.mkdir()
        M.EVIDENCE.mkdir()
        stack.enter_context(mock.patch.object(M, 'WRAPPER', M.CANDIDATE / 'scripts/native_rust_exact_disk_build_wrapper.py'))
        def write(path, raw):
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)
            return dict(path=str(path), sha256=M.sha(raw))
        source_hashes = {}
        for key, rel in {'script_sha256': M.ADAPTER,
                         'tests_sha256': 'scripts/tests/test_prepare_native_exact_scratch22_authority2.py',
                         'ancestor_sha256': M.ANCESTOR}.items():
            source_hashes[key] = write(source / rel, b'fixed helper bytes')['sha256']
        preparation = dict(schema='scratch22-authority2.preparation-release.v1',
                           status='PASS_PREPARATION_EXECUTION_RELEASE', attempt='scratch22-authority2',
                           execution_released=False, controller='c' * 40,
                           target='a' * 40, target_tree='b' * 40, author='preparation-author',
                           **source_hashes)
        for key in ('cleanup', 'cleanup_release', 'cleanup_postflight', 'source_checks', 'source_review',
                    'authority_review'):
            preparation[key] = dict(path='/exact-prerequisite/' + key, sha256='d' * 64)
        reviewed = dict(source_hashes, **{key + '_sha256': preparation[key]['sha256'] for key in
                         ('cleanup', 'cleanup_release', 'cleanup_postflight', 'source_checks', 'source_review',
                          'authority_review')})
        prep_review = dict(decision='PASS_PREPARATION_EXECUTION', reviewer='independent-reviewer',
                           implementation_ownership=False, reviewed_inputs_sha256=reviewed,
                           target=preparation['target'], target_tree=preparation['target_tree'])
        preparation['preparation_review'] = write(temp / 'preparation-review.json', M.canonical(prep_review))
        release = dict(preparation_release=write(temp / 'preparation-release.json', M.canonical(preparation)),
                       candidate_sha=preparation['target'], candidate_tree=preparation['target_tree'],
                       image_id='sha256:' + 'e' * 64, launcher_aggregate_memory_gib='16.2158',
                       artifacts={}, live_binding={})
        def artifact(key, path, raw):
            release['artifacts'][key] = dict(write(path, raw), identity=M.identity(path.stat()))
        artifact('manifest', M.MANIFEST, b'canonical manifest bound by real validator')
        artifact('owner', M.CANDIDATE / 'scripts/native_rust_exact_build_container_owner.py', b'exact owner')
        artifact('driver', M.CANDIDATE / 'scripts/native_rust_exact_build_offline.py', b'exact driver')
        artifact('disk_wrapper', M.WRAPPER, b'exact wrapper')
        prepared = dict(M.FLAGS, candidate_sha=preparation['target'], image_id=release['image_id'],
                        source_root=str(M.CANDIDATE), input_manifest=str(M.MANIFEST),
                        input_manifest_sha256=release['artifacts']['manifest']['sha256'],
                        output_root=str(M.OUTPUT), evidence_root=str(M.EVIDENCE), lease_path=str(M.LEASE),
                        operational_exclusion_path=str(M.EXCLUSION), operational_exclusion_consumed=False,
                        limits=M.LIMITS, timeout=19800, host_floor=16 * 2**30, scratch_floor=12 * 2**30,
                        launcher_aggregate_memory_gib='16.2158')
        for key in ('owner', 'driver'):
            prepared[key + '_path'] = release['artifacts'][key]['path']
            prepared[key + '_path_sha256'] = release['artifacts'][key]['sha256']
        artifact('prepared_request', M.PREP, M.canonical(prepared))
        artifact('preparation_log', M.PREP_LOG, b'complete original preparation log\n')
        terminal = dict(phase='complete', returncode=0, exception=None, preparation_only=True,
                        log=str(M.PREP_LOG), log_sha256=release['artifacts']['preparation_log']['sha256'])
        artifact('preparation_terminal', M.PREP_TERMINAL, M.canonical(terminal))
        for key, path in (('candidate', M.CANDIDATE), ('output', M.OUTPUT), ('evidence', M.EVIDENCE)):
            release['live_binding'][key] = M.identity(path.stat())
        derived = dict(prepared, preparation_only=False, executable=True, execution_released=True, release_required=False)
        release['derived_request_sha256'] = M.sha(M.canonical(derived))
        adapter = mock.Mock()
        stack.enter_context(mock.patch.object(M, 'adapter_module', return_value=adapter))
        def git(args, cwd=None):
            if args[0] == 'show':
                return b'fixed helper bytes'
            return ((preparation['target_tree'] if args[-1] == 'HEAD^{tree}' else preparation['target']) + '\n').encode()
        stack.enter_context(mock.patch.object(M, 'git', side_effect=git))
        return SimpleNamespace(**locals())

    def test_real_preparation_terminal_fields_and_canonical_validator_are_consumed(self):
        with ExitStack() as stack:
            fixture = self.preparation_fixture(stack)
            derived, raw = M.preflight(fixture.release)
            self.assertEqual(derived, fixture.derived)
            self.assertEqual(raw, M.canonical(fixture.derived))
            fixture.adapter.validate_cleanup.assert_called_once_with(fixture.preparation)
            fixture.adapter.validate_source_authority.assert_called_once_with(M.REPO, fixture.preparation)
            fixture.adapter.validate_authority_review.assert_called_once_with(M.REPO, fixture.preparation)
            fixture.adapter.validate_prepared_request.assert_called_once_with(M.CANDIDATE, M.PREP)

    def test_original_scratch22_execution_release_refuses_new_attempt(self):
        release = dict(schema='scratch22.build-execution-release.v1',
                       status='PASS_EXECUTION_RELEASE', attempt='scratch22', execution_count=1)
        with mock.patch.object(M, 'bound_json', return_value=release), self.assertRaises(M.Refusal):
            M.bind_release('/missing', '0' * 64, '0' * 40)

    def test_original_scratch22_preparation_release_refuses_new_attempt(self):
        with ExitStack() as stack:
            fixture = self.preparation_fixture(stack)
            old = dict(fixture.preparation, schema='scratch22.preparation-release.v1', attempt='scratch22')
            fixture.release['preparation_release'] = fixture.write(
                fixture.temp / 'original-attempt-release.json', M.canonical(old))
            with self.assertRaisesRegex(M.Refusal, 'actual scratch22-authority2 preparation'):
                M.preflight(fixture.release)
            fixture.adapter.validate_cleanup.assert_not_called()

    def test_all_fresh_materialization_and_capture_paths_use_authority2(self):
        for name in ('CANDIDATE', 'PREP', 'MANIFEST', 'EXECUTION', 'OUTPUT', 'EVIDENCE',
                     'LEASE', 'STDOUT', 'STDERR', 'TERMINAL', 'QUARANTINE', 'PREP_TERMINAL', 'PREP_LOG'):
            self.assertIn('scratch-22-authority2', str(getattr(M, name)), name)
        self.assertEqual(M.ADAPTER, 'scripts/prepare_native_exact_scratch22_authority2.py')
        self.assertEqual(M.SELF, 'scripts/native_exact_scratch22_authority2_build_wrapper.py')
        self.assertEqual(M.TEST, 'scripts/tests/test_native_exact_scratch22_authority2_build_wrapper.py')

    def test_additional_authority_is_mandatory_and_not_substituted_for_rs011(self):
        with ExitStack() as stack:
            fixture = self.preparation_fixture(stack)
            fixture.adapter.validate_authority_review.side_effect = M.Refusal('authority mismatch')
            with self.assertRaisesRegex(M.Refusal, 'authority mismatch'):
                M.preflight(fixture.release)
            fixture.adapter.validate_cleanup.assert_called_once_with(fixture.preparation)
            fixture.adapter.validate_source_authority.assert_called_once_with(M.REPO, fixture.preparation)
            fixture.adapter.validate_prepared_request.assert_not_called()

    def test_preparation_review_must_bind_new_authority_review_digest(self):
        with ExitStack() as stack:
            fixture = self.preparation_fixture(stack)
            fixture.prep_review['reviewed_inputs_sha256'].pop('authority_review_sha256')
            pointer = fixture.write(fixture.temp / 'unbound-preparation-review.json', M.canonical(fixture.prep_review))
            preparation = dict(fixture.preparation, preparation_review=pointer)
            fixture.release['preparation_release'] = fixture.write(
                fixture.temp / 'unbound-preparation-release.json', M.canonical(preparation))
            with self.assertRaisesRegex(M.Refusal, 'preparation execution review mismatch'):
                M.preflight(fixture.release)

    def test_reviewed_lock_and_execution_bodies_are_mechanically_preserved(self):
        original_path = PATH.with_name('native_exact_scratch22_build_wrapper.py')
        original = original_path.read_text()
        normalized = original.replace('scratch-22', 'scratch-22-authority2').replace('scratch22', 'scratch22-authority2')
        normalized = normalized.replace(
            'def publish(path, raw, expected_sha256=None):',
            'def publish(path, raw, expected_sha256=None, *, maximum=MAX_CAPTURE):\n'
            '    if maximum not in (MAX_CAPTURE, MAX_LARGE_CAPTURE) or len(raw) > maximum:\n'
            '        raise Refusal(\'publication exceeds finite capture bound\')')
        normalized = normalized.replace('stable_regular(path, expected_sha256 or sha(raw))',
                                        'stable_regular(path, expected_sha256 or sha(raw), maximum=maximum)')
        normalized = normalized.replace('def execute(path, checksum, commit):',
                                        'def execute(path, checksum, commit):\n    require_released_adapter()')
        normalized = normalized.replace('stdout, stderr = stable_regular(STDOUT), stable_regular(STDERR)',
                                        'stdout, stderr = stable_large_capture(STDOUT), stable_regular(STDERR)')
        normalized = normalized.replace('publish(TERMINAL, canonical(terminal))',
                                        'publish(TERMINAL, canonical(terminal), maximum=MAX_LARGE_CAPTURE)')
        normalized = normalized.replace('sha(stable_regular(TERMINAL))', 'sha(stable_large_capture(TERMINAL))')
        old = {node.name: node for node in ast.parse(normalized).body if isinstance(node, ast.FunctionDef)}
        new = {node.name: node for node in ast.parse(PATH.read_text()).body if isinstance(node, ast.FunctionDef)}
        for name in ('acquire_development_lock', 'derive', 'publish', 'run_checked',
                     'retirement_proven', 'quarantine_wait', 'quarantine_root_lock', 'execute'):
            self.assertEqual(ast.dump(old[name]), ast.dump(new[name]), name)

    def test_actual_terminal_failure_and_artifact_identity_drift_refuse(self):
        for failure in ('terminal', 'inode', 'consumed', 'occupied', 'output'):
            with self.subTest(failure=failure), ExitStack() as stack:
                fixture = self.preparation_fixture(stack)
                if failure == 'terminal':
                    fixture.artifact('preparation_terminal', M.PREP_TERMINAL,
                                     M.canonical(dict(fixture.terminal, returncode=2)))
                elif failure == 'inode':
                    fixture.release['artifacts']['manifest']['identity']['inode'] += 1
                elif failure == 'consumed':
                    fixture.artifact('prepared_request', M.PREP,
                                     M.canonical(dict(fixture.prepared, operational_exclusion_consumed=0)))
                elif failure == 'occupied':
                    M.EXECUTION.write_bytes(b'consumed request')
                else:
                    (M.OUTPUT / 'old-output').write_bytes(b'not fresh')
                with self.assertRaises(M.Refusal):
                    M.preflight(fixture.release)

    def test_only_four_release_flags_change(self):
        prepared = dict(M.FLAGS, operational_exclusion_consumed=False, preserved=['exact', 7])
        expected = dict(prepared, preparation_only=False, executable=True,
                        execution_released=True, release_required=False)
        derived, raw = M.derive(prepared, M.sha(M.canonical(expected)))
        self.assertEqual(derived, expected)
        self.assertEqual({k for k in prepared if prepared[k] != derived[k]}, set(M.FLAGS))
        self.assertEqual(raw, M.canonical(expected))

    def test_prepared_flags_and_exact_derived_digest_refuse(self):
        for key in M.FLAGS:
            prepared = dict(M.FLAGS)
            prepared[key] = not prepared[key]
            with self.assertRaises(M.Refusal):
                M.derive(prepared, '0' * 64)
        with self.assertRaises(M.Refusal):
            M.derive(dict(M.FLAGS), '0' * 64)

    def test_strict_duplicate_and_nonfinite_json_refuse(self):
        for raw in (b'{"x":1,"x":2}', b'{"x":NaN}'):
            with self.assertRaises(M.Refusal):
                M.strict(raw)

    def test_exclusive_publication_and_hash_binding(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'request'
            M.publish(path, b'{}\n')
            self.assertEqual(M.stable_regular(path), b'{}\n')
            with self.assertRaises(FileExistsError):
                M.publish(path, b'changed')
            with self.assertRaises(M.Refusal):
                M.stable_regular(path, '0' * 64)

    def test_symlink_and_unexplained_hardlink_refuse(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'authority'
            path.write_bytes(b'{}')
            alias = path.with_name('symlink')
            alias.symlink_to(path)
            with self.assertRaises(M.Refusal):
                M.stable_regular(alias)
            alias.unlink()
            os.link(path, alias)
            with self.assertRaises(M.Refusal):
                M.stable_regular(path)

    def test_read_only_default_has_no_authority(self):
        with mock.patch.object(M, 'execute') as execute, mock.patch('builtins.print'):
            self.assertEqual(M.main(['--release', '/missing', '--release-sha256', '0' * 64,
                                     '--release-commit', '0' * 40]), 1)
        execute.assert_not_called()

    def test_stale_release_cannot_transfer_authority(self):
        for release in ({}, {'schema': 'scratch21.build-execution-release.v1'},
                        dict(schema='scratch22-authority2.build-execution-release.v1',
                             status='PROPOSED', attempt='scratch22-authority2', execution_count=1)):
            with mock.patch.object(M, 'bound_json', return_value=release), \
                    self.assertRaises(M.Refusal):
                M.bind_release('/missing', '0' * 64, '0' * 40)

    def build_release_fixture(self, stack):
        repo = Path(stack.enter_context(tempfile.TemporaryDirectory()))
        stack.enter_context(mock.patch.object(M, 'REPO', repo))
        hashes = {}
        for rel in (M.SELF, M.TEST, M.ADAPTER, M.ANCESTOR):
            path = repo / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(('bound bytes ' + rel).encode())
            hashes[rel] = M.sha(path.read_bytes())
        release = dict(schema='scratch22-authority2.build-execution-release.v1', status='PASS_EXECUTION_RELEASE',
                       attempt='scratch22-authority2', execution_count=1, author='implementation-author',
                       fetched_ref='refs/remotes/origin/exact-test-ref', source_sha256=hashes)
        review = dict(decision='PASS_EXECUTION', implementation_ownership=False,
                      reviewer='independent-reviewer', reviewed_release_payload_sha256=M.sha(M.canonical(release)))
        review_path = repo / 'review.json'
        review_path.write_bytes(M.canonical(review))
        release['execution_review'] = dict(path=str(review_path), sha256=M.sha(review_path.read_bytes()))
        release_path = repo / 'release.json'
        release_path.write_bytes(M.canonical(release))
        commit = 'f' * 40
        def git(args, cwd=None):
            if args[0] == 'rev-parse':
                return (commit + '\n').encode()
            return (repo / args[-1].split(':', 1)[1]).read_bytes()
        git_mock = stack.enter_context(mock.patch.object(M, 'git', side_effect=git))
        return SimpleNamespace(**locals())

    def test_exact_fetched_code_and_independent_review_bind_release(self):
        with ExitStack() as stack:
            fixture = self.build_release_fixture(stack)
            self.assertEqual(M.bind_release(fixture.release_path,
                             M.sha(fixture.release_path.read_bytes()), fixture.commit), fixture.release)

    def test_same_author_implementation_owner_or_changed_payload_refuse(self):
        for failure in ('same-author', 'owner', 'payload', 'source'):
            with self.subTest(failure=failure), ExitStack() as stack:
                fixture = self.build_release_fixture(stack)
                if failure == 'same-author':
                    fixture.review['reviewer'] = fixture.release['author']
                elif failure == 'owner':
                    fixture.review['implementation_ownership'] = True
                elif failure == 'payload':
                    fixture.review['reviewed_release_payload_sha256'] = '0' * 64
                else:
                    fixture.release['source_sha256'][M.SELF] = '0' * 64
                fixture.review_path.write_bytes(M.canonical(fixture.review))
                fixture.release['execution_review']['sha256'] = M.sha(fixture.review_path.read_bytes())
                fixture.release_path.write_bytes(M.canonical(fixture.release))
                with self.assertRaises(M.Refusal):
                    M.bind_release(fixture.release_path, M.sha(fixture.release_path.read_bytes()), fixture.commit)

    def test_positive_current_retirement_contract(self):
        self.assertTrue(M.retirement_proven(retired()))
        for key, value in (('retired', False), ('cleanup_separately_required', False),
                           ('terminal_container_retained', False),
                           ('terminal_container_info_current', False),
                           ('terminal_container_info', None), ('client_retirement_unproven', True)):
            bad = dict(retired(), **{key: value})
            self.assertFalse(M.retirement_proven(bad), key)

    def runtime(self, stack):
        release = dict(launcher_aggregate_memory_gib='16.2158', derived_request_sha256='a' * 64,
                       artifacts={'prepared_request': {'sha256': 'b' * 64}})
        stack.enter_context(mock.patch.object(M, 'bind_release', return_value=release))
        stack.enter_context(mock.patch.object(M, 'require_released_adapter'))
        acquire = stack.enter_context(mock.patch.object(M, 'acquire_development_lock', return_value=91))
        preflight = stack.enter_context(mock.patch.object(M, 'preflight', return_value=({}, b'{}\n')))
        checked = [SimpleNamespace(returncode=0, stdout=b'{"status":"PASS_COMPATIBILITY_ONLY"}'),
                   SimpleNamespace(returncode=0, stdout=b'{"status":"PASS_READ_ONLY"}')]
        subprocess = stack.enter_context(mock.patch.object(M.subprocess, 'run', side_effect=checked))
        run = stack.enter_context(mock.patch.object(M, 'run_checked', return_value=0))
        read = stack.enter_context(mock.patch.object(M, 'stable_regular',
                                                     side_effect=[M.canonical(retired()), b'', b'terminal']))
        publish = stack.enter_context(mock.patch.object(M, 'publish'))
        quarantine = stack.enter_context(mock.patch.object(M, 'quarantine_root_lock', side_effect=Quarantined))
        stack.enter_context(mock.patch.object(M.signal, 'getsignal', return_value=signal.SIG_DFL))
        handlers = stack.enter_context(mock.patch.object(M.signal, 'signal'))
        masks = stack.enter_context(mock.patch.object(M.signal, 'pthread_sigmask', return_value=set()))
        flock = stack.enter_context(mock.patch.object(M.fcntl, 'flock'))
        close = stack.enter_context(mock.patch.object(M.os, 'close'))
        stack.enter_context(mock.patch.object(M.os.path, 'lexists',
                                             side_effect=lambda p: p in (M.EXCLUSION, M.SHARED)))
        return SimpleNamespace(**locals())

    def invoke(self):
        return M.execute(Path('/release'), 'c' * 64, 'd' * 40)

    def test_success_holds_lock_until_terminal_and_retained_exclusions(self):
        with ExitStack() as stack:
            runtime = self.runtime(stack)
            result = self.invoke()
            self.assertEqual(result['status'], 'PASS_EXECUTED')
            runtime.quarantine.assert_not_called()
            runtime.flock.assert_called_once_with(91, M.fcntl.LOCK_UN)
            runtime.close.assert_called_once_with(91)
            command, lockfd = runtime.run.call_args.args
            self.assertEqual(lockfd, 91)
            self.assertIn(str(M.WRAPPER), command)
            self.assertIn(str(M.EXECUTION), command)
            self.assertEqual(runtime.preflight.call_count, 2)
            self.assertEqual(runtime.publish.call_count, 2)
            self.assertEqual(runtime.handlers.call_count, 2 * len(M.DEFERRED_SIGNALS))

    def test_malformed_stdout_or_failed_capture_always_quarantines(self):
        for failure in (b'malformed', OSError('stdout read failed')):
            with self.subTest(failure=str(failure)), ExitStack() as stack:
                runtime = self.runtime(stack)
                runtime.read.side_effect = [failure, b'']
                with self.assertRaises(Quarantined):
                    self.invoke()
                runtime.quarantine.assert_called_once_with(91, 'build-started-without-positive-terminal-retirement')
                runtime.flock.assert_not_called()
                runtime.close.assert_not_called()

    def test_failed_start_or_terminal_publication_quarantines(self):
        for failure in ('start', 'terminal', 'fsync'):
            with self.subTest(failure=failure), ExitStack() as stack:
                runtime = self.runtime(stack)
                if failure == 'start':
                    runtime.run.side_effect = OSError('start failed')
                elif failure == 'terminal':
                    runtime.publish.side_effect = [None, OSError('evidence full')]
                else:
                    runtime.run.side_effect = OSError('capture fsync failed')
                with self.assertRaises(Quarantined):
                    self.invoke()
                runtime.quarantine.assert_called_once()
                runtime.flock.assert_not_called()

    def test_explicit_uncertain_retirement_quarantines(self):
        with ExitStack() as stack:
            runtime = self.runtime(stack)
            runtime.read.side_effect = [M.canonical(dict(retired(), client_retirement_unproven=True)), b'']
            with self.assertRaises(Quarantined):
                self.invoke()
            runtime.flock.assert_not_called()

    def test_failed_build_with_positive_retirement_unlocks(self):
        with ExitStack() as stack:
            runtime = self.runtime(stack)
            runtime.run.return_value = 1
            with self.assertRaisesRegex(M.Refusal, 'failed after positive retirement'):
                self.invoke()
            runtime.quarantine.assert_not_called()
            runtime.flock.assert_called_once()

    def test_preflight_failure_unlocks_and_restores_signals(self):
        with ExitStack() as stack:
            runtime = self.runtime(stack)
            runtime.preflight.side_effect = M.Refusal('drift')
            with self.assertRaisesRegex(M.Refusal, 'drift'):
                self.invoke()
            runtime.run.assert_not_called()
            runtime.quarantine.assert_not_called()
            runtime.flock.assert_called_once()
            self.assertEqual(runtime.handlers.call_count, 2 * len(M.DEFERRED_SIGNALS))

    def test_acquisition_failure_restores_installed_signal_handlers(self):
        with ExitStack() as stack:
            runtime = self.runtime(stack)
            runtime.acquire.side_effect = M.Refusal('lock busy')
            with self.assertRaisesRegex(M.Refusal, 'lock busy'):
                self.invoke()
            self.assertEqual(runtime.handlers.call_count, 2 * len(M.DEFERRED_SIGNALS))
            runtime.flock.assert_not_called()
            runtime.close.assert_not_called()

    def test_signal_before_publication_does_not_start_build(self):
        with ExitStack() as stack:
            runtime = self.runtime(stack)
            checked = iter(('PASS_COMPATIBILITY_ONLY', 'PASS_READ_ONLY'))
            def validate(*_args, **_kwargs):
                runtime.handlers.call_args_list[0].args[1](signal.SIGHUP, None)
                return SimpleNamespace(returncode=0, stdout=M.canonical(dict(status=next(checked))))
            # Invoke the installed callback during the first validation call.
            runtime.subprocess.side_effect = lambda *_args, **_kwargs: validate()
            with self.assertRaises(M.Refusal):
                self.invoke()
            runtime.run.assert_not_called()
            runtime.publish.assert_not_called()
            runtime.flock.assert_called_once()

    def test_signal_during_publication_retains_request_without_starting(self):
        with ExitStack() as stack:
            runtime = self.runtime(stack)
            runtime.publish.side_effect = lambda *_args: runtime.handlers.call_args_list[1].args[1](signal.SIGINT, None)
            with self.assertRaisesRegex(M.Refusal, 'during request publication'):
                self.invoke()
            runtime.run.assert_not_called()
            runtime.publish.assert_called_once()
            runtime.quarantine.assert_not_called()
            runtime.flock.assert_called_once()

    def test_quarantine_evidence_failure_cannot_release_lock(self):
        with mock.patch.object(M.os, 'fstat', side_effect=OSError('descriptor evidence failure')), \
                mock.patch.object(M, 'quarantine_wait', side_effect=Quarantined) as wait:
            with self.assertRaises(Quarantined):
                M.quarantine_root_lock(91, 'uncertain')
        wait.assert_called_once_with()

    def test_run_checked_passes_root_descriptor_without_timeout(self):
        with tempfile.TemporaryDirectory() as temp, \
                mock.patch.object(M, 'STDOUT', Path(temp) / 'stdout'), \
                mock.patch.object(M, 'STDERR', Path(temp) / 'stderr'), \
                mock.patch.object(M.subprocess, 'run', return_value=SimpleNamespace(returncode=0)) as run:
            self.assertEqual(M.run_checked(['fake-unprivileged-command'], 91), 0)
        self.assertEqual(run.call_args.kwargs['pass_fds'], (91,))
        self.assertNotIn('timeout', run.call_args.kwargs)

    def test_stdout_open_failure_does_not_leak_successful_capture_descriptor(self):
        with mock.patch.object(M.os, 'open', side_effect=[51, OSError('stderr exists')]), \
                mock.patch.object(M.os, 'close') as close, \
                mock.patch.object(M.subprocess, 'run') as run:
            with self.assertRaises(OSError):
                M.run_checked(['fake'], 91)
        close.assert_called_once_with(51)
        run.assert_not_called()

    def test_fresh_namespace_and_frozen_runtime_profile(self):
        for name in ('CANDIDATE', 'PREP', 'MANIFEST', 'EXECUTION', 'OUTPUT', 'EVIDENCE',
                     'LEASE', 'STDOUT', 'STDERR', 'TERMINAL', 'QUARANTINE'):
            self.assertNotIn('scratch-21', str(getattr(M, name)))
            self.assertNotIn('scratch21', str(getattr(M, name)))
        self.assertEqual(M.LIMITS, dict(NanoCpus=4000000000, CpusetCpus='2-5',
                                      Memory=12884901888, MemorySwap=12884901888,
                                      PidsLimit=512, NetworkMode='none'))
        self.assertEqual(M.EXCLUSION.name, 'native-exact-candidate-operational-exclusion-scratch18.json')

    def test_signal_installation_is_atomic_and_build_inherits_original_mask(self):
        with ExitStack() as stack:
            runtime = self.runtime(stack)
            events = []
            runtime.masks.side_effect = lambda how, mask: events.append(('mask', how, tuple(mask))) or {signal.SIGUSR1}
            runtime.handlers.side_effect = lambda signum, handler: events.append(('handler', signum))
            runtime.acquire.side_effect = lambda _release: events.append(('lock',)) or 91
            runtime.run.side_effect = lambda *_args: events.append(('run',)) or 0
            self.invoke()
            self.assertEqual(events[0], ('mask', signal.SIG_BLOCK, M.DEFERRED_SIGNALS))
            self.assertEqual([row[1] for row in events[1:5]], list(M.DEFERRED_SIGNALS))
            self.assertEqual(events[5], ('mask', signal.SIG_SETMASK, (signal.SIGUSR1,)))
            self.assertEqual(events[6], ('lock',))
            self.assertIn(('run',), events)
            self.assertEqual(events[-1], ('mask', signal.SIG_SETMASK, (signal.SIGUSR1,)))

    def test_actual_quarantine_holds_disposable_flock_across_ordinary_termination(self):
        # Real child, real flock, actual execute -> quarantine path. Only producer
        # admission/build are mocked; no Docker, sudo or production lock is used.
        program = r'''
import importlib.util, os, signal, sys
from pathlib import Path
from types import SimpleNamespace
spec = importlib.util.spec_from_file_location('disposable_scratch22-authority2', sys.argv[1])
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
root = Path(sys.argv[2])
broken = sys.argv[3] == 'broken'
m.LOCK = root / 'root.lock'
m.EXECUTION = root / 'request.json'
m.QUARANTINE = root / 'quarantine.json'
release = dict(launcher_aggregate_memory_gib='16.2158', derived_request_sha256='a' * 64,
               artifacts={'prepared_request': {'sha256': 'b' * 64}},
               live_binding={'root_lock': m.identity(m.LOCK.stat())})
m.bind_release = lambda *_args: release
m.require_released_adapter = lambda: None
m.preflight = lambda _release: ({}, b'{}\n')
statuses = iter(('PASS_COMPATIBILITY_ONLY', 'PASS_READ_ONLY'))
m.subprocess.run = lambda *_args, **_kwargs: SimpleNamespace(
    returncode=0, stdout=m.canonical({'status': next(statuses)}))
def publish(path, raw, *_args):
    if path == m.EXECUTION:
        path.write_bytes(raw)
        return
    # At the actual evidence/prewait boundary, record readiness out of band.
    (root / 'ready').write_bytes(m.canonical(dict(
        blocked_signals=sorted(int(s) for s in signal.pthread_sigmask(signal.SIG_BLOCK, [])),
        all_handlers_callable=all(callable(signal.getsignal(s)) for s in m.DEFERRED_SIGNALS))))
    raise OSError('simulated unavailable quarantine evidence')
m.publish = publish
def uncertain(*_args):
    if broken:
        # stdout really is a pipe with no reader; this raises BrokenPipeError.
        os.write(1, b'broken output\n')
        raise AssertionError('broken output was unexpectedly writable')
    raise OSError('simulated uncertain started build')
m.run_checked = uncertain
original_sleep = m.time.sleep
calls = []
def interrupted_wait(seconds):
    if not calls:
        calls.append(True)
        (root / 'wait-failure').write_bytes(b'preserved')
        raise BrokenPipeError('simulated diagnostic/wait exception')
    return original_sleep(seconds)
m.time.sleep = interrupted_wait
m.execute(root / 'release.json', 'c' * 64, 'd' * 40)
raise AssertionError('quarantine escaped')
'''
        cases = [(signum, False) for signum in M.DEFERRED_SIGNALS]
        cases.append((None, True))
        for signum, broken in cases:
            with self.subTest(signal=signum, broken_output=broken), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                lock = root / 'root.lock'
                lock.write_bytes(b'disposable root lock')
                stdout_fd = None
                if broken:
                    reader, stdout_fd = os.pipe()
                    os.close(reader)
                child = subprocess.Popen([sys.executable, '-B', '-c', program,
                                          str(PATH), str(root), 'broken' if broken else 'ordinary'],
                                         cwd=str(root), stdin=subprocess.DEVNULL,
                                         stdout=stdout_fd if broken else subprocess.DEVNULL,
                                         stderr=subprocess.DEVNULL, close_fds=True,
                                         start_new_session=True,
                                         env=dict(PATH='/usr/bin:/bin', LANG='C', LC_ALL='C'))
                if stdout_fd is not None:
                    os.close(stdout_fd)
                contender = os.open(str(lock), os.O_RDONLY)
                try:
                    deadline = time.monotonic() + 5
                    while not (root / 'wait-failure').exists() and time.monotonic() < deadline:
                        if child.poll() is not None:
                            self.fail('disposable quarantine exited before readiness: ' + str(child.returncode))
                        time.sleep(0.005)
                    self.assertTrue((root / 'wait-failure').exists(), 'quarantine readiness timeout')
                    ready = json.loads((root / 'ready').read_bytes())
                    self.assertTrue(ready['all_handlers_callable'])
                    self.assertFalse(set(ready['blocked_signals']) & set(M.DEFERRED_SIGNALS),
                                     'ordinary signals must reach deferral handlers, not remain pending')
                    signals = M.DEFERRED_SIGNALS if broken else (signum,)
                    for requested in signals:
                        child.send_signal(requested)
                        with self.assertRaises(subprocess.TimeoutExpired):
                            child.wait(timeout=0.05)
                        with self.assertRaises(BlockingIOError):
                            fcntl.flock(contender, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    self.assertTrue((root / 'request.json').exists())
                    self.assertFalse((root / 'quarantine.json').exists(), 'failed evidence must not be fabricated')
                finally:
                    # Only this exact owned disposable child is killed/reaped.
                    # SIGKILL releases its live flock; no persistence is claimed.
                    if child.poll() is None:
                        child.kill()
                    child.wait(timeout=5)
                    fcntl.flock(contender, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    os.close(contender)

    def test_unreleased_adapter_refuses_before_release_read_or_lock(self):
        self.assertIs(M.ADAPTER_RELEASED, False)
        self.assertIsNone(M.ADAPTER_SHA256)
        with mock.patch.object(M, 'bind_release') as bind, \
                mock.patch.object(M, 'acquire_development_lock') as acquire:
            with self.assertRaisesRegex(M.Refusal, 'NOT_RELEASED'):
                self.invoke()
        bind.assert_not_called()
        acquire.assert_not_called()

    def test_large_canonical_positive_retirement_is_parsed_and_retained(self):
        reader, publisher = M.stable_regular, M.publish
        for status, code in (('PASS', 0), ('FAIL', 1)):
            with self.subTest(status=status), tempfile.TemporaryDirectory() as temp, ExitStack() as stack:
                root = Path(temp)
                stack.enter_context(mock.patch.object(M, 'STDOUT', root / 'stdout'))
                stack.enter_context(mock.patch.object(M, 'STDERR', root / 'stderr'))
                stack.enter_context(mock.patch.object(M, 'TERMINAL', root / 'terminal.json'))
                result = dict(retired(), status=status, padding='x' * (17 << 20))
                M.STDOUT.write_bytes(M.canonical(result))
                M.STDERR.write_bytes(b'')
                self.assertGreater(M.STDOUT.stat().st_size, M.MAX_CAPTURE)
                runtime = self.runtime(stack)
                runtime.run.return_value = code
                runtime.read.side_effect = reader
                def publish(path, raw, expected=None, **kwargs):
                    if path == M.TERMINAL:
                        return publisher(path, raw, expected, **kwargs)
                runtime.publish.side_effect = publish
                if code:
                    with self.assertRaisesRegex(M.Refusal, 'failed after positive retirement'):
                        self.invoke()
                else:
                    checked = self.invoke()
                    self.assertEqual(checked['status'], 'PASS_EXECUTED')
                    self.assertTrue(M.retirement_proven(checked['wrapper_result']))
                self.assertGreater(M.TERMINAL.stat().st_size, M.MAX_CAPTURE)
                terminal = M.strict(M.stable_large_capture(M.TERMINAL))
                self.assertEqual(terminal['wrapper_result'], result)
                runtime.quarantine.assert_not_called()
                runtime.flock.assert_called_once_with(91, M.fcntl.LOCK_UN)

    def test_over_128_mib_capture_quarantines_started_owner(self):
        reader = M.stable_regular
        with tempfile.TemporaryDirectory() as temp, ExitStack() as stack:
            root = Path(temp)
            stack.enter_context(mock.patch.object(M, 'STDOUT', root / 'stdout'))
            stack.enter_context(mock.patch.object(M, 'STDERR', root / 'stderr'))
            with M.STDOUT.open('wb') as stream:
                stream.truncate(M.MAX_LARGE_CAPTURE + 1)
            M.STDERR.write_bytes(b'')
            runtime = self.runtime(stack)
            runtime.read.side_effect = reader
            with self.assertRaises(Quarantined):
                self.invoke()
            runtime.quarantine.assert_called_once()
            runtime.flock.assert_not_called()

    def test_over_128_mib_capture_refuses_before_allocating_or_reading(self):
        self.assertEqual(M.MAX_LARGE_CAPTURE, 128 << 20)
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'oversize'
            with path.open('wb') as stream:
                stream.truncate(M.MAX_LARGE_CAPTURE + 1)
            with mock.patch.object(M.os, 'read') as read, self.assertRaises(M.Refusal):
                M.stable_large_capture(path)
            read.assert_not_called()

    def test_authority_and_default_publication_limits_remain_16_mib(self):
        self.assertEqual(M.MAX_CAPTURE, 16 << 20)
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'oversize-small'
            with path.open('wb') as stream:
                stream.truncate(M.MAX_CAPTURE + 1)
            with self.assertRaises(M.Refusal):
                M.stable_regular(path)
            with self.assertRaises(M.Refusal):
                M.publish(Path(temp) / 'default-publication', b'x' * (M.MAX_CAPTURE + 1))
            self.assertFalse((Path(temp) / 'default-publication').exists())


if __name__ == '__main__':
    unittest.main()
