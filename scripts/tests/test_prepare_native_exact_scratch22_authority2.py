"""Disposable source-only regressions; no scratch, root, Docker, or compiler."""
import ast
import hashlib
import importlib.util
import inspect
import json
import os
import stat
from pathlib import Path
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location('scratch22', ROOT / 'scripts/prepare_native_exact_scratch22_authority2.py')
p = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(p)


class Scratch22Authority2(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.top = Path(self.temp.name)
        real_bound_json = p.bound_json
        def disposable_author(path, checksum):
            if str(path) == p.AUTHORITY_AUTHOR_RECORD:
                path = self.top / 'authority-author.json'
            return real_bound_json(path, checksum)
        patcher = mock.patch.object(p, 'bound_json', side_effect=disposable_author)
        patcher.start()
        self.addCleanup(patcher.stop)
        def no_git_process(source, *args, **kwargs):
            if args[:2] != ('hash-object', '--no-filters'):
                raise AssertionError('unexpected real Git request: ' + repr(args))
            raw = Path(args[-1]).read_bytes()
            # Frozen Git blob object format; no Git subprocess in this packet.
            return (hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest() + '\n').encode()
        git_patcher = mock.patch.object(p._IMPL, 'git', side_effect=no_git_process)
        git_patcher.start()
        self.addCleanup(git_patcher.stop)
        real_digest = p._IMPL.digest
        def retained_failure_digest(path):
            return p.RECOVERY_ORIGINAL_FAILURE_SHA256.get(str(path), None) or real_digest(path)
        digest_patcher = mock.patch.object(p._IMPL, 'digest', side_effect=retained_failure_digest)
        digest_patcher.start()
        self.addCleanup(digest_patcher.stop)
        self.actual_retirement_gate = p.validate_authority1_retirement
        retirement = mock.patch.object(p, 'validate_authority1_retirement')
        retirement.start()
        self.addCleanup(retirement.stop)

    def record(self, name, value):
        path = self.top / name
        raw = json.dumps(value, sort_keys=True).encode()
        path.write_bytes(raw)
        return {'path': str(path), 'sha256': hashlib.sha256(raw).hexdigest()}

    def identity(self, path):
        meta = path.stat()
        return dict(path=str(path), device=meta.st_dev, inode=meta.st_ino,
                    mode=oct(stat.S_IMODE(meta.st_mode)), uid=meta.st_uid, gid=meta.st_gid,
                    size=meta.st_size, nlink=meta.st_nlink,
                    sha256=hashlib.sha256(path.read_bytes()).hexdigest())

    def cleanup(self):
        cleanup_release = dict(schema='scratch21.cleanup-release.v1', status='PASS_EXECUTION_RELEASE',
                               author='cleanup-author',
                               source_review=dict(status='PASS', reviewer='reviewer', evidence_sha256='f' * 64),
                               execution_review=dict(status='PASS', reviewer='reviewer', evidence_sha256='e' * 64),
                               observation=dict(boot_id='boot', mount=dict(uuid=p.SCRATCH_UUID)))
        authority = self.record('cleanup-release.json', cleanup_release)
        archives = []
        for index in range(2):
            path = self.top / ('archive' + str(index))
            path.write_bytes(b'exclusion')
            archives.append(self.identity(path))
        plan = dict(schema='scratch21.terminal-cleanup.v1', root=str(p._IMPL.DEFAULT_SCRATCH),
                    filesystem_uuid=p.SCRATCH_UUID,
                    release_sha256=hashlib.sha256(p.canonical(cleanup_release)).hexdigest(),
                    records=[['original', Path(row['path']).name, row['sha256'], row['inode'], row['size']]
                             for row in archives])
        plan_path = self.top / 'plan.json'
        plan_path.write_bytes(p.canonical(plan) + b'\n')
        plan_identity = self.identity(plan_path)
        plan_sha = hashlib.sha256(p.canonical(plan)).hexdigest()
        previous = plan_sha
        journal = b''
        legal = [(event, index) for index in range(2) for event in
                 ('before_exchange', 'after_exchange', 'release', 'after_release')] + [('complete', 2)]
        for sequence, (event, index) in enumerate(legal):
            body = dict(event=event, index=index, sequence=sequence, plan_sha256=plan_sha,
                        previous=previous, plan_identity=[plan_identity['device'], plan_identity['inode']])
            previous = hashlib.sha256(p.canonical(body)).hexdigest()
            journal += p.canonical(dict(body, hash=previous)) + b'\n'
        journal_path = self.top / 'journal.jsonl'
        journal_path.write_bytes(journal)
        capture_path = self.top / 'capture'
        capture_path.write_bytes(b'original failure logs')
        result = dict(schema='scratch21.cleanup-result.v1', status='PASS_EXECUTED', terminal=True,
                      container_absent=True, container_id=p.SCRATCH21_CONTAINER,
                      filesystem_uuid=p.SCRATCH_UUID, boot_id='boot',
                      release_sha256=plan['release_sha256'], plan_sha256=plan_sha,
                      plan=plan_identity, journal=self.identity(journal_path),
                      capture=self.identity(capture_path), archives=archives)
        pointer = self.record('cleanup.json', result)
        postflight = self.record('cleanup-postflight.json',
                                dict(schema='scratch21.cleanup-postflight-review.v1', decision='PASS_CLEANUP',
                                     result_sha256=pointer['sha256'], release_sha256=result['release_sha256']))
        return pointer, authority, postflight

    def release(self):
        target, tree, baseline = 'a' * 40, 'b' * 40, 'c' * 40
        cleanup, cleanup_release, cleanup_postflight = self.cleanup()
        production = 'host-kernel/native-rust/ihk_smp_x86_64.rs'
        files = [dict(path='example', sha256=hashlib.sha256(b'source').hexdigest()),
                 dict(path=production, sha256=hashlib.sha256(self.repair_bytes(production, False)).hexdigest())]
        commands = ['native_rust_build_surface_audit.py', 'rocky_rust_staging.py --check',
                    'ihk_native_lifecycle_check.py', 'native_rust_unsafe_ffi_ledger.py check',
                    '-m unittest scripts.tests.test_native_rust_unsafe_ffi_ledger']
        checks = self.record('source-checks.json', dict(status='PASS_SOURCE_CHECKS_ONLY', files=files,
                             source_checks=[dict(command=command, exit_code=0) for command in commands]))
        review = self.record('source.json', dict(decision='PASS_SOURCE_AUTHORITY',
                             author_record=dict(checks, status='PASS_SOURCE_CHECKS_ONLY'),
                             files_sha256={row['path']: row['sha256'] for row in files}))
        authority_files = {rel: hashlib.sha256(('authority-' + rel).encode()).hexdigest()
                           for rel in p.AUTHORITY_FILES}
        authority_author = self.record('authority-author.json', dict(
            author='authority-author', status='NOT_RELEASED',
            checks=dict(status='PASS'), files_sha256=authority_files))
        authority_review = self.record('authority-review.json', dict(
            decision='PASS_SOURCE_AUTHORITY', reviewer='independent-authority-reviewer',
            implementation_ownership=False, files_sha256=authority_files,
            author_record=dict(path=p.AUTHORITY_AUTHOR_RECORD, sha256=authority_author['sha256'])))
        repair_review = self.record('repair-review.json', dict(
            decision='PASS_MINIMAL_SOURCE_REPAIR',
            reviewer='independent-repair-reviewer', implementation_author='repair-author',
            implementation_ownership=False, baseline_candidate=baseline, target=target, target_tree=tree,
            source_checks_baseline=checks, source_review_baseline=review,
            files_sha256_delta={rel: dict(baseline_sha256=hashlib.sha256(self.repair_bytes(rel, False)).hexdigest(),
                                         target_sha256=hashlib.sha256(self.repair_bytes(rel, True)).hexdigest())
                                for rel in p.REPAIR_FILES}))
        retirement = self.retirement_records()
        return dict(schema='scratch22-authority2-source-admission-v1', status='PASS',
                    attempt='scratch22-authority2', execution_released=False,
                    target=target, target_tree=tree, baseline=baseline,
                    source_base=p.SOURCE_BASE,
                    fetched_ref='refs/remotes/origin/reviewed',
                    exact_delta=[['M', rel, 'd' * 40] for rel in sorted(p.REPAIR_FILES)],
                    cleanup=cleanup, cleanup_release=cleanup_release, cleanup_postflight=cleanup_postflight,
                    source_checks=checks, source_review=review, authority_review=authority_review,
                    repair_review=repair_review, **retirement)

    def producer_dict(self, path, function, variable, namespace):
        """Extract only the actual producer's dict expression, never import it."""
        tree = ast.parse((ROOT / path).read_text())
        body = next(node for node in ast.walk(tree)
                    if isinstance(node, ast.FunctionDef) and node.name == function)
        if variable is None:
            expression = next(node.value for node in body.body if isinstance(node, ast.Return))
        else:
            expression = next(node.value for node in ast.walk(body) if isinstance(node, ast.Assign)
                              and any(isinstance(target, ast.Name) and target.id == variable for target in node.targets))
        self.assertIsInstance(expression, (ast.Call, ast.Dict))
        return eval(compile(ast.Expression(expression), str(path), 'eval'),
                    dict(namespace, __builtins__={}, dict=dict, str=str))

    def retirement_records(self):
        """Synthetic actual-shape fixtures; no actual retirement result is made."""
        profile = json.loads(p.RECOVERY_PROFILE.read_text())
        guard = profile['bound_guard']
        target = dict(pid=guard['pid'], starttime=guard['starttime'], parent=guard['parent_pid'],
                      boot_id=guard['boot_id'], uid=guard['uid'], gid=guard['gid'], threads=guard['threads'])
        authority = dict(schema='scratch22-authority1.quarantine-recovery-release.v1',
                         status='PASS_EXECUTION_RELEASE', source_checkpoint='9' * 40,
                         original_failure_sha256=p.RECOVERY_ORIGINAL_FAILURE_SHA256)
        authority_pointer = self.record('synthetic-recovery-release.json', authority)
        snapshot = dict(inputs={'synthetic': 'unchanged input hash map'},
                        captures={}, root_locks=[['FLOCK', 'ADVISORY', 'WRITE', '1001', '00:1b:4', '0', 'EOF']])
        ns = dict(PROFILE_SHA=p.RECOVERY_PROFILE_SHA256,
                  ORIGINAL_FAILURE_SHA256=p.RECOVERY_ORIGINAL_FAILURE_SHA256,
                  checksum=authority_pointer['sha256'], release=authority, target=target,
                  first=snapshot, second=snapshot, after=snapshot, requested=[],
                  signalled=dict(syscall=424, signal=9, returncode=0),
                  exited=dict(pidfd_exit_ready=True, events=[[8, 1]]),
                  canonical=lambda value: p.canonical(value) + b'\n',
                  sha=lambda raw: hashlib.sha256(raw).hexdigest())
        producer = 'scripts/native_exact_scratch22_authority1_quarantine_recovery.py'
        prepared = self.producer_dict(producer, 'execute', 'prepared', ns)
        prepared_path = self.top / 'synthetic-recovery-prepared.json'
        prepared_path.write_bytes(p.canonical(prepared) + b'\n')
        prepared_pointer = dict(path=str(prepared_path), sha256=hashlib.sha256(prepared_path.read_bytes()).hexdigest())
        ns['prepared'] = prepared
        complete = self.producer_dict(producer, 'execute', 'record', ns)
        result_pointer = self.record('synthetic-recovery-complete.json', complete)
        review_pointer = self.record('synthetic-recovery-review.json', dict(
            schema='scratch22-authority1.quarantine-recovery-postflight-review.v1',
            decision='PASS_PROCESS_RECOVERY_POSTFLIGHT', reviewer='independent-retirement-reviewer',
            implementation_ownership=False, result=result_pointer, release=authority_pointer,
            prepared=prepared_pointer, profile_sha256=p.RECOVERY_PROFILE_SHA256,
            source_checkpoint=authority['source_checkpoint']))

        directory = self.top / 'synthetic-cleanup'
        directory.mkdir()
        archives = []
        for index in range(2):
            path = directory / ('archive' + str(index))
            path.write_bytes(b'preserved exclusion')
            archives.append(self.identity(path))
        cleanup_release = dict(schema='scratch22-authority1.cleanup-release.v1', status='PASS_EXECUTION_RELEASE')
        cleanup_release_pointer = self.record('synthetic-cleanup-release.json', cleanup_release)
        plan = dict(schema='scratch22-authority1.terminal-cleanup.v1', root=str(p._IMPL.DEFAULT_SCRATCH),
                    filesystem_uuid=p.SCRATCH_UUID,
                    release_sha256=hashlib.sha256(p.canonical(cleanup_release)).hexdigest(),
                    records=[['original', Path(row['path']).name, row['sha256'], row['inode'], row['size']]
                             for row in archives])
        plan_path = directory / 'plan.json'
        plan_path.write_bytes(p.canonical(plan) + b'\n')
        plan_row = self.identity(plan_path)
        plan_sha = hashlib.sha256(p.canonical(plan)).hexdigest()
        previous = plan_sha
        journal = b''
        legal = [(event, index) for index in range(2) for event in
                 ('before_exchange', 'after_exchange', 'release', 'after_release')] + [('complete', 2)]
        for sequence, (event, index) in enumerate(legal):
            body = dict(event=event, index=index, sequence=sequence, plan_sha256=plan_sha,
                        previous=previous, plan_identity=[plan_row['device'], plan_row['inode']])
            previous = hashlib.sha256(p.canonical(body)).hexdigest()
            journal += p.canonical(dict(body, hash=previous)) + b'\n'
        journal_path = directory / 'journal.jsonl'
        journal_path.write_bytes(journal)
        capture_path = directory / 'capture'
        capture_path.write_bytes(b'synthetic retained container log')
        cleanup_ns = dict(CONTAINER=profile['retirement_proof']['container']['id'],
                          UUID=p.SCRATCH_UUID, BOOT_ID=target['boot_id'], RELEASE=cleanup_release,
                          plan=plan, PLAN=plan_path, JOURNAL=journal_path, CAPTURE=capture_path,
                          ROOT=directory, ARCHIVE_NAMES=[Path(row['path']).name for row in archives],
                          PUBLISHER_CONTRACT={'synthetic': 'publisher proof'},
                          canonical=p.canonical, observe_identity=self.identity,
                          digest=lambda raw: hashlib.sha256(raw).hexdigest(), status='PASS_EXECUTED')
        cleanup_result = self.producer_dict('scripts/native_exact_scratch22_authority1_terminal_cleanup.py',
                                            'terminal_result', None, cleanup_ns)
        cleanup_pointer = self.record('synthetic-cleanup-result.json', cleanup_result)
        cleanup_review = self.record('synthetic-cleanup-review.json', dict(
            schema='scratch22-authority1.cleanup-postflight-review.v1',
            decision='PASS_TERMINAL_CLEANUP_POSTFLIGHT', reviewer='independent-retirement-reviewer',
            implementation_ownership=False, result=cleanup_pointer, release=cleanup_release_pointer,
            plan={key: cleanup_result['plan'][key] for key in ('path', 'sha256')},
            journal={key: cleanup_result['journal'][key] for key in ('path', 'sha256')},
            capture={key: cleanup_result['capture'][key] for key in ('path', 'sha256')},
            release_canonical_sha256=cleanup_result['release_sha256'],
            container_absent=True, exclusions_absent=True, archives=archives))
        return dict(authority1_recovery=result_pointer, authority1_recovery_review=review_pointer,
                    authority1_cleanup=cleanup_pointer, authority1_cleanup_review=cleanup_review)

    def repair_bytes(self, rel, repaired):
        old, new = p.REPAIR_REPLACEMENTS[rel]
        return b'unchanged-prefix\n' + (new if repaired else old) + b'\nunchanged-suffix\n'

    def git_for_release(self, release, wrong_owner=False):
        def git(source, *args, **kwargs):
            if args[0] == 'rev-parse':
                return {release['fetched_ref']: release['target'],
                        release['target'] + '^{commit}': release['target'],
                        release['target'] + '^{tree}': release['target_tree'],
                        release['target'] + '^': release['baseline']}[args[-1]].encode() + b'\n'
            if args[0] == 'show':
                revision, rel = args[-1].split(':', 1)
                if rel in p.REPAIR_FILES:
                    return self.repair_bytes(rel, revision == release['target'])
                if args[-1].split(':', 1)[-1] in p.AUTHORITY_FILES:
                    return ('authority-' + args[-1].split(':', 1)[-1]).encode()
                if args[-1].endswith(':example'):
                    return b'source'
                return ("OPERATIONAL_EXCLUSION_PATH = %r\n" %
                        ('/wrong' if wrong_owner else p.ACTIVE_EXCLUSION)).encode()
            raise AssertionError(args)
        return git

    def test_closed_without_authority_and_execute_refused_first(self):
        with self.assertRaisesRegex(p.Refusal, 'forbids execute'):
            p.prepare(release_path='/missing', release_sha256='', execute=True)
        with self.assertRaisesRegex(p.Refusal, 'SHA-256 required'):
            p.prepare(release_path='/missing', release_sha256='')

    def test_release_accepts_exact_external_identity(self):
        release = self.release()
        bound = self.record('release.json', release)
        with mock.patch.object(p._IMPL, 'git', side_effect=self.git_for_release(release)), \
                mock.patch.object(p._IMPL, 'raw_delta') as delta:
            self.assertEqual(p.validate_release(ROOT, bound['path'], bound['sha256']), release)
            delta.assert_called_once_with(ROOT, old=release['baseline'], target=release['target'],
                                          expected=tuple(map(tuple, release['exact_delta'])))

    def test_scratch20_exclusion_mismatch_precedes_preparation(self):
        release = self.release()
        bound = self.record('release.json', release)
        with mock.patch.object(p._IMPL, 'git', side_effect=self.git_for_release(release, True)), \
                mock.patch.object(p._IMPL, 'raw_delta'), mock.patch.object(p._IMPL, 'prepare') as inherited:
            with self.assertRaisesRegex(p.Refusal, 'scratch20 family'):
                p.prepare(release_path=bound['path'], release_sha256=bound['sha256'])
            inherited.assert_not_called()

    def test_source_review_cannot_bind_different_authority(self):
        release = self.release()
        release['source_review'] = self.record('wrong.json', dict(decision='PASS_SOURCE_AUTHORITY', author_record={}))
        bound = self.record('release.json', release)
        with mock.patch.object(p._IMPL, 'git', side_effect=self.git_for_release(release)):
            with self.assertRaisesRegex(p.Refusal, 'minimal repair review immutable source baseline binding differs'):
                p.validate_release(ROOT, bound['path'], bound['sha256'])

    def test_unaccepted_cleanup_is_not_authority(self):
        release = self.release()
        release['cleanup'] = self.record('draft.json', dict(status='DRAFT', scope='scratch21-cleanup'))
        bound = self.record('release.json', release)
        with self.assertRaisesRegex(p.Refusal, 'accepted scratch21 terminal cleanup'):
            p.validate_release(ROOT, bound['path'], bound['sha256'])

    def test_authority_digest_drift_and_symlink_refused(self):
        bound = self.record('input.json', dict(status='PASS'))
        Path(bound['path']).write_bytes(b'{}')
        with self.assertRaisesRegex(p.Refusal, 'digest/race'):
            p.bound_json(bound['path'], bound['sha256'])
        alias = self.top / 'alias'
        alias.symlink_to(bound['path'])
        with self.assertRaisesRegex(p.Refusal, 'not regular'):
            p.bound_json(alias, bound['sha256'])

    def test_exact_fetched_ref_required(self):
        release = self.release()
        bound = self.record('release.json', release)
        original_git = self.git_for_release(release)
        def wrong_ref(source, *args, **kwargs):
            return b'f' * 40 + b'\n' if args[0] == 'rev-parse' else original_git(source, *args, **kwargs)
        with mock.patch.object(p._IMPL, 'git', side_effect=wrong_ref):
            with self.assertRaisesRegex(p.Refusal, 'released/fetched source identity'):
                p.validate_release(ROOT, bound['path'], bound['sha256'])

    def test_scratch19_frozen_default_leak_reproduced_and_prevented(self):
        release = self.release()
        signature = inspect.signature(p._IMPL.prepare)
        self.assertNotEqual(signature.parameters['target'].default, release['target'])
        self.assertNotEqual(signature.parameters['old'].default, release['baseline'])
        args = p.inherited_arguments(release, self.top, 6)
        for key in ('target', 'old', 'baseline', 'expected_delta'):
            self.assertIn(key, args)
        self.assertEqual(args['target'], release['target'])
        self.assertEqual(args['old'], release['baseline'])
        self.assertEqual(set(args), {key for key, param in signature.parameters.items()
                                    if param.default is not inspect.Parameter.empty})
        self.assertIs(args['execute'], False)
        self.assertEqual(args['exclusion'], p.ACTIVE_EXCLUSION)
        self.assertIn(self.top / 'mckernel-exact-candidate-scratch-21', args['additional_shared_roots'])

    def links(self, count):
        roots = [self.top / str(i) for i in range(count)]
        for root in roots:
            root.mkdir()
        (roots[0] / 'evidence').write_bytes(b'exact')
        (roots[0] / 'evidence').chmod(0o644)
        for root in roots[1:]:
            os.link(roots[0] / 'evidence', root / 'evidence')
        blob = hashlib.sha1(b'blob 5\0exact').hexdigest()
        return roots, [('evidence', '100644', blob)]

    def test_dynamic_census_accepts_different_complete_topologies(self):
        for count in (2, 7, 8, 9):
            with self.subTest(count=count), tempfile.TemporaryDirectory() as directory:
                before = self.top
                self.top = Path(directory)
                roots, shared = self.links(count)
                self.assertEqual(p.alias_census(roots, shared), count)
                self.top = before

    def test_unlisted_link_cannot_hide_missing_alias(self):
        roots, shared = self.links(6)
        os.link(roots[0] / 'evidence', self.top / 'unknown')
        with self.assertRaisesRegex(p.Refusal, 'incomplete authenticated alias'):
            p.alias_census(roots, shared)

    def test_replaced_alias_rejected_even_with_same_bytes_and_link_count(self):
        roots, shared = self.links(6)
        (roots[-1] / 'evidence').unlink()
        (roots[-1] / 'evidence').write_bytes(b'exact')
        os.link(roots[0] / 'evidence', self.top / 'replacement')
        with self.assertRaisesRegex(p.Refusal, 'incomplete authenticated alias'):
            p.alias_census(roots, shared)

    def test_changed_shared_bytes_and_duplicate_roots_refused(self):
        roots, shared = self.links(3)
        (roots[0] / 'evidence').write_bytes(b'wrong')
        with self.assertRaisesRegex(p.Refusal, 'unauthenticated alias bytes'):
            p.alias_census(roots, shared)
        with self.assertRaisesRegex(p.Refusal, 'duplicate/missing'):
            p.alias_census([roots[0], roots[0]], shared)

    def test_names_are_fresh_except_required_owner_slot(self):
        for key, value in p.NAMES.items():
            if key not in ('EXCLUSION_NAME', 'INTERMEDIATE_CANDIDATE_NAME', 'PREVIOUS_CANDIDATE_NAME'):
                self.assertIn('22', value)
                self.assertNotIn('21', value)
        self.assertEqual(p.NAMES['EXCLUSION_NAME'], 'native-exact-candidate-operational-exclusion-scratch18.json')

    def test_nested_symlink_is_not_an_authenticated_alias(self):
        roots, shared = self.links(2)
        (roots[0] / 'alias').symlink_to(roots[0], target_is_directory=True)
        (roots[1] / 'alias').symlink_to(roots[1], target_is_directory=True)
        with self.assertRaisesRegex(p.Refusal, 'noncanonical evidence alias'):
            p.alias_census(roots, [('alias/evidence', shared[0][1], shared[0][2])])

    def test_prepare_passes_only_explicit_nonexecuting_arguments(self):
        release = self.release()
        roots = tuple(self.top / name for name in p.ALIASES)
        for root in roots:
            root.mkdir()
        shared = []
        entries = []
        sizes = []
        for index in range(p._IMPL.EXPECTED_SHARED_FILES):
            rel = 'docs/verification/evidence/' + str(index)
            path = roots[0] / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.touch()
            entries.append(('100644', 'blob', 'd' * 40, rel))
            sizes.append(('100644 blob ' + 'd' * 40 + ' 1048577\t' + rel).encode())
        before = {name: getattr(p._IMPL, name) for name in
                  (*p.NAMES, 'TARGET', 'TARGET_TREE', 'BASELINE', 'SOURCE_BASE', 'FETCHED_REF', 'EXACT_DELTA')}
        try:
            with mock.patch.object(p, 'validate_release', return_value=release), \
                    mock.patch.object(p._IMPL, 'tree_entries', return_value=entries), \
                    mock.patch.object(p._IMPL, 'git', return_value=b'\0'.join(sizes) + b'\0'), \
                    mock.patch.object(p, 'alias_census', return_value=8) as census, \
                    mock.patch.object(p._IMPL, 'prepare', autospec=True,
                                      return_value={'status': 'PASS_VALIDATE_ONLY'}) as inherited:
                # autospec preserves the original signature for the default audit.
                with mock.patch.object(p.inspect, 'signature', return_value=inspect.signature(p._IMPL.prepare)):
                    result = p.prepare(release_path='/unused', release_sha256='a' * 64, scratch=self.top)
                self.assertEqual(len(census.call_args.args[1]), 486)
                self.assertEqual(census.call_args.args[0], roots)
                self.assertIs(inherited.call_args.kwargs['execute'], False)
                self.assertEqual(inherited.call_args.kwargs['target'], release['target'])
                self.assertEqual(result['authenticated_initial_links'], 8)
                self.assertEqual(result['expected_materialized_links'], 9)
        finally:
            for name, value in before.items():
                setattr(p._IMPL, name, value)

    def test_materialization_refuses_source_only_release_before_any_mutation(self):
        release = self.release()
        bound = self.record('release.json', release)
        with mock.patch.object(p._IMPL, 'prepare') as inherited:
            with self.assertRaisesRegex(p.Refusal, 'preparation execution release required'):
                p.prepare(release_path=bound['path'], release_sha256=bound['sha256'], materialize=True)
        inherited.assert_not_called()

    def test_materialization_calls_real_adapter_branch_and_request_boundary(self):
        release = self.release()
        roots = tuple(self.top / name for name in p.ALIASES)
        for root in roots:
            root.mkdir()
        entries, sizes = [], []
        for index in range(p._IMPL.EXPECTED_SHARED_FILES):
            rel = 'docs/verification/evidence/' + str(index)
            path = roots[0] / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.touch()
            entries.append(('100644', 'blob', 'd' * 40, rel))
            sizes.append(('100644 blob ' + 'd' * 40 + ' 1048577\t' + rel).encode())
        before = {name: getattr(p._IMPL, name) for name in
                  (*p.NAMES, 'TARGET', 'TARGET_TREE', 'BASELINE', 'SOURCE_BASE', 'FETCHED_REF', 'EXACT_DELTA')}
        try:
            with mock.patch.object(p, 'validate_release', return_value=release) as authority, \
                    mock.patch.object(p._IMPL, 'tree_entries', return_value=entries), \
                    mock.patch.object(p._IMPL, 'git', return_value=b'\0'.join(sizes) + b'\0'), \
                    mock.patch.object(p, 'alias_census', return_value=8), \
                    mock.patch.object(p, 'live_preparation_boundary') as live, \
                    mock.patch.object(p, 'validate_prepared_request') as request, \
                    mock.patch.object(p._IMPL, 'prepare', autospec=True,
                                      return_value={'status': 'PASS_PREPARE_ONLY', 'request': '/fresh/request'}) as inherited:
                result = p.prepare(release_path='/released', release_sha256='e' * 64,
                                   scratch=self.top, materialize=True)
                authority.assert_called_once_with(ROOT, '/released', 'e' * 64, materialize=True)
                live.assert_called_once_with(self.top, release)
                inherited.assert_called_once()
                self.assertIs(inherited.call_args.kwargs['execute'], True)
                self.assertEqual(inherited.call_args.kwargs['target'], release['target'])
                self.assertEqual(inherited.call_args.kwargs['expected_initial_links'], 8)
                self.assertEqual(inherited.call_args.kwargs['additional_shared_roots'], roots[3:])
                request.assert_called_once_with(self.top / p.NAMES['CANDIDATE_NAME'], '/fresh/request')
                self.assertEqual(result['canonical_owner_request_validation'], 'PASS')
                self.assertIs(result['execution_released'], False)
        finally:
            for name, value in before.items():
                setattr(p._IMPL, name, value)

    def test_cleanup_requires_complete_chain_and_retained_failure_bytes(self):
        release = self.release()
        p.validate_cleanup(release)
        result = json.loads(Path(release['cleanup']['path']).read_text())
        result['status'] = 'PASS_TERMINAL_REPLAY'
        release['cleanup'] = self.record('replay.json', result)
        release['cleanup_postflight'] = self.record('replay-review.json',
            dict(schema='scratch21.cleanup-postflight-review.v1', decision='PASS_CLEANUP',
                 result_sha256=release['cleanup']['sha256'], release_sha256=result['release_sha256']))
        p.validate_cleanup(release)
        journal = Path(result['journal']['path'])
        journal.write_bytes(b''.join(journal.read_bytes().splitlines(keepends=True)[:-1]))
        result['journal'] = self.identity(journal)
        release['cleanup'] = self.record('incomplete.json', result)
        with self.assertRaisesRegex(p.Refusal, 'journal not complete'):
            p.validate_cleanup(release)

    def test_cleanup_original_release_and_capture_drift_refused(self):
        release = self.release()
        result = json.loads(Path(release['cleanup']['path']).read_text())
        Path(result['capture']['path']).write_bytes(b'replaced')
        with self.assertRaisesRegex(p.Refusal, 'cleanup evidence drift'):
            p.validate_cleanup(release)

    def test_exact_preparation_review_binds_code_and_actual_evidence(self):
        release = self.release()
        paths = {'script_sha256': Path(p.__file__),
                 'tests_sha256': ROOT / 'scripts/tests/test_prepare_native_exact_scratch22_authority2.py',
                 'ancestor_sha256': p.ANCESTOR}
        release.update({key: hashlib.sha256(path.read_bytes()).hexdigest() for key, path in paths.items()})
        release.update(controller='9' * 40, author='author')
        expected = {key: release[key] for key in paths}
        expected.update({key + '_sha256': release[key]['sha256'] for key in
                         ('cleanup', 'cleanup_release', 'cleanup_postflight', 'source_checks', 'source_review', 'authority_review', 'repair_review',
                          'authority1_recovery', 'authority1_recovery_review', 'authority1_cleanup', 'authority1_cleanup_review')})
        review = dict(decision='PASS_PREPARATION_EXECUTION', reviewer='independent',
                      implementation_ownership=False, reviewed_inputs_sha256=expected,
                      target=release['target'], target_tree=release['target_tree'])
        release['preparation_review'] = self.record('prep-review.json', review)
        def git(source, *args, **kwargs):
            if args[0] == 'rev-parse':
                return release['controller'].encode() + b'\n'
            return (ROOT / args[-1].split(':', 1)[1]).read_bytes()
        with mock.patch.object(p._IMPL, 'git', side_effect=git):
            p.validate_preparation_release(ROOT, release)
            review['reviewer'] = 'author'
            release['preparation_review'] = self.record('same-author.json', review)
            with self.assertRaisesRegex(p.Refusal, 'independent exact preparation execution'):
                p.validate_preparation_release(ROOT, release)
            release['script_sha256'] = '0' * 64
            with self.assertRaisesRegex(p.Refusal, 'source hash drift'):
                p.validate_preparation_release(ROOT, release)

    def test_terminal_result_without_accepted_postflight_cannot_materialize(self):
        release = self.release()
        release['cleanup_postflight'] = self.record('draft-postflight.json',
            dict(schema='scratch21.cleanup-postflight-review.v1', decision='PENDING'))
        with self.assertRaisesRegex(p.Refusal, 'accepted exact cleanup postflight'):
            p.validate_cleanup(release)

    def test_eight_retained_aliases_preserve_old22_and_authority1_with_fresh_authority2_names(self):
        self.assertEqual(len(p.ALIASES), 8)
        self.assertIn('mckernel-exact-candidate-scratch-22', p.ALIASES)
        self.assertIn('mckernel-exact-candidate-scratch-22-authority1', p.ALIASES)
        for key, value in p.NAMES.items():
            if key not in ('EXCLUSION_NAME', 'INTERMEDIATE_CANDIDATE_NAME', 'PREVIOUS_CANDIDATE_NAME'):
                self.assertIn('scratch-22-authority2', value)

    def test_authority_review_is_additive_and_cannot_weaken_rs011(self):
        release = self.release()
        pointer = self.record('release.json', release)
        with mock.patch.object(p._IMPL, 'git', side_effect=self.git_for_release(release)), \
                mock.patch.object(p._IMPL, 'raw_delta'):
            p.validate_release(ROOT, pointer['path'], pointer['sha256'])
            release['source_checks'] = self.record('bad-rs011.json', dict(status='NOT_READY'))
            pointer = self.record('bad-release.json', release)
            with self.assertRaisesRegex(p.Refusal, 'minimal repair review immutable source baseline binding differs'):
                p.validate_release(ROOT, pointer['path'], pointer['sha256'])

    def test_authority_fixed_file_map_and_target_hash_are_enforced(self):
        release = self.release()
        with mock.patch.object(p._IMPL, 'git', side_effect=self.git_for_release(release)):
            p.validate_authority_review(ROOT, release)
        with mock.patch.object(p._IMPL, 'git', return_value=b'old observer bytes'):
            with self.assertRaisesRegex(p.Refusal, 'reviewed target blob mismatch'):
                p.validate_authority_review(ROOT, release)
        review = json.loads(Path(release['authority_review']['path']).read_text())
        review['files_sha256']['arbitrary-extra.py'] = 'e' * 64
        release['authority_review'] = self.record('extra-authority.json', review)
        with self.assertRaisesRegex(p.Refusal, 'fixed four-file review allowlist'):
            p.validate_authority_review(ROOT, release)

    def test_authority_review_cannot_be_pending_same_author_or_missing(self):
        release = self.release()
        review = json.loads(Path(release['authority_review']['path']).read_text())
        review['decision'] = 'PENDING'
        release['authority_review'] = self.record('pending-authority.json', review)
        with self.assertRaisesRegex(p.Refusal, 'independent authority1 source review'):
            p.validate_authority_review(ROOT, release)
        review.update(decision='PASS_SOURCE_AUTHORITY', reviewer='authority-author')
        release['authority_review'] = self.record('same-author.json', review)
        with self.assertRaisesRegex(p.Refusal, 'independent author/check/hash'):
            p.validate_authority_review(ROOT, release)
        author = json.loads((self.top / 'authority-author.json').read_text())
        author['checks'] = {}
        pointer = self.record('authority-author.json', author)
        review.update(reviewer='independent-authority-reviewer',
                      author_record=dict(path=p.AUTHORITY_AUTHOR_RECORD, sha256=pointer['sha256']))
        release['authority_review'] = self.record('missing-check-status.json', review)
        with self.assertRaisesRegex(p.Refusal, 'independent author/check/hash'):
            p.validate_authority_review(ROOT, release)
        release.pop('authority_review')
        with self.assertRaises(KeyError):
            p.validate_authority_review(ROOT, release)

    def test_original_safety_body_ast_is_preserved_without_old_module_mutation(self):
        original = ast.parse((ROOT / 'scripts/prepare_native_exact_scratch22.py').read_text())
        current = ast.parse(Path(p.__file__).read_text())
        functions = ('canonical', 'unique_object', 'bound_json', 'validate_cleanup',
                     'bound_identity', 'live_preparation_boundary',
                     'alias_census', 'inherited_arguments', 'validate_prepared_request')
        for name in functions:
            before = next(node for node in original.body if isinstance(node, ast.FunctionDef) and node.name == name)
            after = next(node for node in current.body if isinstance(node, ast.FunctionDef) and node.name == name)
            self.assertEqual(ast.dump(before), ast.dump(after), name)
        self.assertEqual(hashlib.sha256((ROOT / 'scripts/prepare_native_exact_scratch22.py').read_bytes()).hexdigest(),
                         '3c3dd179301ee9d16ecf8c9e918fee304ee76cb6a89bc2a987235c1f52ec6663')
        self.assertEqual(hashlib.sha256((ROOT / 'scripts/tests/test_prepare_native_exact_scratch22.py').read_bytes()).hexdigest(),
                         '71d1c0658fb67b65df761ce5b13f145ccb54a5f0ded64e0e06edf5fbcde1a97f')
        self.assertEqual(hashlib.sha256((ROOT / 'scripts/prepare_native_exact_scratch22_authority1.py').read_bytes()).hexdigest(),
                         '5e002228f09c2df3c712422d94f96f333bbc0df597335203de57350162723717')

    def test_missing_actual_accepted_retirement_records_block_preparation(self):
        release = self.release()
        review = json.loads(Path(release['authority1_recovery_review']['path']).read_text())
        review['decision'] = 'PENDING'
        release['authority1_recovery_review'] = self.record('pending-recovery-review.json', review)
        with mock.patch.object(p, 'validate_authority1_retirement', side_effect=self.actual_retirement_gate), \
                mock.patch.object(p._IMPL, 'git', side_effect=self.git_for_release(release)), \
                mock.patch.object(p._IMPL, 'raw_delta'), mock.patch.object(p._IMPL, 'prepare') as inherited:
            for materialize in (False, True):
                if materialize:
                    release.update(schema='scratch22-authority2.preparation-release.v1',
                                   status='PASS_PREPARATION_EXECUTION_RELEASE')
                pointer = self.record('release.json', release)
                with self.assertRaisesRegex(p.Refusal, 'independent accepted authority1 retirement review required'):
                    p.prepare(release_path=pointer['path'], release_sha256=pointer['sha256'], materialize=materialize)
        inherited.assert_not_called()

    def test_actual_producer_shapes_join_complete_recovery_and_terminal_cleanup(self):
        release = self.release()
        result = self.actual_retirement_gate(release)
        self.assertEqual(result['recovery']['status'], 'COMPLETE_PROCESS_RECOVERY')
        self.assertEqual(result['cleanup']['status'], 'PASS_EXECUTED')

    def test_recovery_sole_signal_exit_original_failure_and_review_hash_drift_refuse(self):
        release = self.release()
        original = json.loads(Path(release['authority1_recovery']['path']).read_text())
        for field, value, reason in (
                ('sole_signal', dict(syscall=424, signal=15, returncode=0), 'sole process-retirement'),
                ('exit_proof', dict(pidfd_exit_ready=False, events=[]), 'positive pidfd'),
                ('original_failure_sha256', {}, 'sole process-retirement'),
                ('status', 'PREPARED_PROCESS_RETIREMENT', 'actual complete recovery')):
            with self.subTest(field=field):
                altered = dict(original, **{field: value})
                pointer = self.record('altered-recovery.json', altered)
                review = json.loads(Path(release['authority1_recovery_review']['path']).read_text())
                review['result'] = pointer
                changed = dict(release, authority1_recovery=pointer,
                               authority1_recovery_review=self.record('altered-review.json', review))
                with self.assertRaisesRegex(p.Refusal, reason):
                    self.actual_retirement_gate(changed)

    def test_cleanup_postflight_and_complete_journal_required(self):
        release = self.release()
        review = json.loads(Path(release['authority1_cleanup_review']['path']).read_text())
        review['exclusions_absent'] = False
        release['authority1_cleanup_review'] = self.record('unclear-exclusion-review.json', review)
        with self.assertRaisesRegex(p.Refusal, 'accepted terminal cleanup binding differs'):
            self.actual_retirement_gate(release)
        review['exclusions_absent'] = True
        result = json.loads(Path(release['authority1_cleanup']['path']).read_text())
        journal = Path(result['journal']['path'])
        journal.write_bytes(b''.join(journal.read_bytes().splitlines(keepends=True)[:-1]))
        result['journal'] = self.identity(journal)
        review['journal'] = {key: result['journal'][key] for key in ('path', 'sha256')}
        pointer = self.record('incomplete-cleanup.json', result)
        review['result'] = pointer
        release.update(authority1_cleanup=pointer,
                       authority1_cleanup_review=self.record('incomplete-cleanup-review.json', review))
        with self.assertRaisesRegex(p.Refusal, 'actual cleanup journal incomplete'):
            self.actual_retirement_gate(release)

    def test_exact_two_file_repair_and_unaffected_rs011_hashes(self):
        release = self.release()
        with mock.patch.object(p._IMPL, 'git', side_effect=self.git_for_release(release)):
            p.validate_source_authority(ROOT, release)
        git = self.git_for_release(release)
        def unrelated(source, *args, **kwargs):
            if args[0] == 'show' and args[-1] == release['target'] + ':example':
                return b'unreviewed unrelated change'
            return git(source, *args, **kwargs)
        with mock.patch.object(p._IMPL, 'git', side_effect=unrelated):
            with self.assertRaisesRegex(p.Refusal, 'source authority target blob mismatch'):
                p.validate_source_authority(ROOT, release)
        release['exact_delta'].append(['M', 'kernel/rust/unreviewed.rs', 'e' * 40])
        with self.assertRaisesRegex(p.Refusal, 'only the two reviewed modifications'):
            p.validate_repair_review(ROOT, release)

    def test_repair_review_rejects_extra_edits_inside_selected_production_file(self):
        release = self.release()
        git = self.git_for_release(release)
        def modified(source, *args, **kwargs):
            result = git(source, *args, **kwargs)
            if args[0] == 'show' and args[-1] == release['target'] + ':host-kernel/native-rust/ihk_smp_x86_64.rs':
                return result + b'\nunrelated-production-token\n'
            return result
        with mock.patch.object(p._IMPL, 'git', side_effect=modified):
            with self.assertRaisesRegex(p.Refusal, 'exact bounded repair source differs'):
                p.validate_repair_review(ROOT, release)

    def test_canonical_owner_validation_and_nonexecutable_request(self):
        candidate = self.top / p.NAMES['CANDIDATE_NAME']
        request = dict(source_root=str(candidate), operational_exclusion_path=p.ACTIVE_EXCLUSION,
                       preparation_only=True, execution_released=False, executable=False,
                       release_required=True, operational_exclusion_consumed=False)
        bound = self.record('request.json', request)
        owner_module = mock.Mock()
        owner_module.BuildOwner.return_value.docker = None
        context = mock.MagicMock()
        context.__enter__.return_value = (None, None, owner_module)
        with mock.patch.object(p._IMPL, 'candidate_modules', return_value=context):
            p.validate_prepared_request(candidate, bound['path'])
        owner_module.BuildOwner.return_value.validate.assert_called_once_with()
        request['executable'] = True
        bound = self.record('request.json', request)
        with self.assertRaisesRegex(p.Refusal, 'executable or released'):
            p.validate_prepared_request(candidate, bound['path'])


if __name__ == '__main__':
    unittest.main()
