import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import native_rust_exact_build_offline as driver

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW_TEXT = (ROOT / driver.WORKFLOW).read_text()


class FakeRunner:
    def __init__(self, repo, files, candidate):
        self.repo, self.files, self.candidate = repo, files, candidate
        self.phases = []
        self.environments = []
        self.fail_phase = None
        self.dirty = False
        self.head = candidate
        self.submodule = driver.EXPECTED_IHK_HEAD
        self.gitlinks = {'ihk': driver.EXPECTED_IHK_HEAD,
                         'vendor/unconsumed': 'd' * 40}
        self.create_artifacts = True
        self.corrupt = None
        self.objects = {p: hashlib.sha1(b'blob ' + str(len(text.encode())).encode() +
                                      b'\0' + text.encode()).hexdigest()
                        for p, text in files.items()}

    def bytes(self, argv, cwd):
        if argv[:2] != ['/usr/bin/git', '-c'] or '-C' not in argv:
            raise AssertionError('unexpected identity command ' + repr(argv))
        c = argv.index('-C')
        root, args = Path(argv[c + 1]), argv[c + 2:]
        if args == ['rev-parse', 'HEAD']:
            return ((self.head if root == self.repo else self.submodule) + '\n').encode('ascii')
        if args == ['ls-files', '--others', '--exclude-standard', '-z']:
            return b'mutated\0' if self.dirty else b''
        if args == ['ls-files', '-z']:
            files = [p for p in self.files if not p.startswith('ihk/')]
            if root != self.repo:
                files = [p[4:] for p in self.files if p.startswith('ihk/')]
            else:
                files.extend(self.gitlinks)
            return ('\0'.join(files) + '\0').encode('utf-8')
        if args in (['ls-files', '-s', '-z'], ['ls-tree', '-r', '-z', '--full-tree', 'HEAD']):
            tree = args[0] == 'ls-tree'
            rows = [(p if root == self.repo else p[4:], '100644', self.objects[p])
                    for p in self.files if p.startswith('ihk/') != (root == self.repo)]
            if root == self.repo:
                rows += [(p, '160000', oid) for p, oid in self.gitlinks.items()]
            return ''.join(('%s %s %s\t%s\0' % (mode, 'commit' if mode == '160000' else 'blob', oid, p)
                            if tree else '%s %s 0\t%s\0' % (mode, oid, p))
                           for p, mode, oid in rows).encode('utf-8')
        raise AssertionError('unexpected git command ' + repr(argv))

    def phase(self, script, cwd, env, log):
        self.phases.append(script.read_text())
        self.environments.append(dict(env))
        with log.open('a') as stream:
            stream.write('phase %d executed\n' % len(self.phases))
        if self.fail_phase == len(self.phases):
            return 37
        if len(self.phases) == 5 and self.create_artifacts:
            root = Path(env['RUNNER_TEMP']) / 'native-rust-build-evidence'
            root.mkdir()
            for name in driver.ARTIFACTS:
                if name != 'SHA256SUMS':
                    (root / name).write_text('nonempty observed artifact: ' + name)
            (root / 'SHA256SUMS').write_text(''.join(
                driver.sha256(p) + '  ' + p.name + '\n' for p in sorted(root.iterdir())))
            if self.corrupt:
                self.corrupt(root)
        return 0


class DriverTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        # This fixture models the historical pristine-only contract.  The
        # production pinned IHK identity additionally requires the exact
        # reviewed working-tree overlay, exercised by focused tests below.
        self.ihk_pin = mock.patch.object(driver, 'EXPECTED_IHK_HEAD', 'f' * 40)
        self.ihk_pin.start()
        self.repo, self.assets, self.output, self.evidence = [self.root / p for p in ('repo', 'assets', 'out', 'ev')]
        for path in (self.repo, self.assets, self.output):
            path.mkdir()
        files = {driver.WORKFLOW: WORKFLOW_TEXT, 'ihk/frozen.rs': 'immutable submodule source',
                 'host-kernel/fixture.rs': 'immutable source'}
        for name, text in files.items():
            path = self.repo / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text)
            path.chmod(0o644)
        self.rows = {name: driver.sha256(self.repo / name) for name in files}
        for name in (driver.ARCHIVE, driver.BASELINE, driver.SRPM, driver.DEBRAND):
            (self.assets / name).write_text('test bytes for ' + name)
            (self.assets / name).chmod(0o644)
        asset_hashes = {p.name: driver.sha256(p) for p in self.assets.iterdir()}
        # Substitute small frozen fixture archive identities, not hash behavior.
        self.pins = mock.patch.dict(driver.ASSET_HASHES,
                                    {n: asset_hashes[n] for n in driver.ASSET_HASHES}, clear=True)
        self.pins.start()
        self.candidate = 'a' * 40
        self.manifest = self.root / 'manifest.json'
        self.data = {'candidate_sha': self.candidate, 'repository_files': self.rows,
                     'schema': driver.INPUT_SCHEMA, 'ihk_sha': driver.EXPECTED_IHK_HEAD,
                     'gitlinks': dict(self.runner.gitlinks) if hasattr(self, 'runner') else {
                         'ihk': driver.EXPECTED_IHK_HEAD, 'vendor/unconsumed': 'd' * 40},
                     'assets': asset_hashes, 'driver_sha256': driver.sha256(Path(driver.__file__))}
        self.save_manifest()
        self.runner = FakeRunner(self.repo, files, self.candidate)

    def tearDown(self):
        self.pins.stop()
        self.ihk_pin.stop()
        self.temp.cleanup()

    def save_manifest(self):
        self.manifest.write_text(json.dumps(self.data))

    def execute(self):
        return driver.run(self.repo, self.candidate, self.assets, self.output,
                          self.evidence, self.manifest, runner=self.runner)

    def test_positive_all_five_phases_and_inventory(self):
        result = self.execute()
        self.assertEqual(result['status'], 'PASS', result)
        self.assertEqual(len(self.runner.phases), 5)
        self.assertEqual([r['exit_code'] for r in result['commands']], [0] * 5)
        self.assertIn('native-rust-build-evidence/bzImage', result['inventory'])
        self.assertFalse(json.loads((self.evidence / 'local-provenance.json').read_text())['github_run'])
        for env in self.runner.environments:
            for key in ('RUNNER_TEMP', 'TMPDIR', 'TMP', 'TEMP'):
                self.assertEqual(env[key], str(self.evidence))
            self.assertEqual(env['SOURCE_PARENT'], str(self.output / 'source'))
            self.assertEqual(env['BUILD_DIR'], str(self.output / 'build'))
        self.assertEqual(self.runner.phases,
                         list(driver.workflow_bodies(WORKFLOW_TEXT).values()))

    def test_ihk_overlay_rejects_missing_wrong_and_extra_changes(self):
        """The pinned IHK may have exactly one reviewed unstaged diff."""
        pinned = '3114d9e7101ad52030eb3effa849a5c108972a1f'
        repo = self.root / 'overlay-repo'
        ihk = repo / 'ihk'
        repo.mkdir()
        subprocess.run(['/usr/bin/git', '-C', str(repo), 'init', '-q'], check=True)
        subprocess.run(['/usr/bin/git', '-C', str(repo), 'config', 'user.name', 'test'], check=True)
        subprocess.run(['/usr/bin/git', '-C', str(repo), 'config', 'user.email', 'test@example'], check=True)
        source_ihk = ROOT / 'ihk'
        subprocess.run(['/usr/bin/git', 'clone', '-q', str(source_ihk), str(ihk)], check=True)
        subprocess.run(['/usr/bin/git', '-C', str(ihk), 'checkout', '-q', pinned], check=True)
        asset = repo / driver.IHK_OVERLAY_ASSET
        asset.parent.mkdir(parents=True)
        shutil.copy2(ROOT / driver.IHK_OVERLAY_ASSET, asset)
        subprocess.run(['/usr/bin/git', '-C', str(repo), 'add', str(asset.relative_to(repo))], check=True)
        subprocess.run(['/usr/bin/git', '-C', str(repo), 'update-index', '--add', '--cacheinfo',
                        '160000,' + pinned + ',ihk'], check=True)
        subprocess.run(['/usr/bin/git', '-C', str(repo), 'commit', '-qm', 'overlay fixture'], check=True)

        def git(root, *args):
            return subprocess.check_output(['/usr/bin/git', '-C', str(root), *args])

        driver.verify_ihk_overlay(repo, git, applied=False)
        target = ihk / driver.IHK_OVERLAY_PATH
        result = git(ihk, 'show', '21a0d1eb1705c3ee597aed41358ba4c0a92d5f8c:' + driver.IHK_OVERLAY_PATH)
        target.write_bytes(result)
        driver.verify_ihk_overlay(repo, git, applied=True)
        target.chmod(0o600)
        with self.assertRaisesRegex(driver.BuildError, 'permission|mode'):
            driver.source_inventory(repo, git, allow_ihk_overlay=True)
        target.chmod(0o644)
        target.write_bytes(b'wrong overlay bytes')
        with self.assertRaisesRegex(driver.BuildError, 'applied bytes differ'):
            driver.verify_ihk_overlay(repo, git, applied=True)
        target.write_bytes(result)
        (ihk / 'untracked-extra').write_bytes(b'extra')
        with self.assertRaisesRegex(driver.BuildError, 'unexpected changes'):
            driver.verify_ihk_overlay(repo, git, applied=True)

    def test_temporary_root_rejects_invalid_paths(self):
        build = self.root / 'build'
        build.mkdir()
        regular = build / 'ordinary-file'
        regular.write_text('not a directory')
        link = build / 'link'
        link.symlink_to(build, target_is_directory=True)
        outside = self.root / 'outside'
        outside.mkdir()
        for path in (Path('relative'), build / '..' / 'outside', outside,
                     build / 'missing', regular, link, link / 'child'):
            with self.subTest(path=str(path)):
                with self.assertRaises(driver.BuildError):
                    driver.temporary_environment(path, build)
        for mode in (0o555, 0o666, 0o000):
            with self.subTest(mode=oct(mode)):
                build.chmod(mode)
                try:
                    with self.assertRaisesRegex(driver.BuildError, 'writable/searchable'):
                        driver.temporary_environment(build, build)
                finally:
                    build.chmod(0o700)
        with mock.patch.object(driver.os, 'access', return_value=False):
            with self.assertRaisesRegex(driver.BuildError, 'writable/searchable'):
                driver.temporary_environment(build, build)
        child = build / 'child'
        child.mkdir()
        self.assertEqual(driver.temporary_environment(child, build),
                         {k: str(child) for k in ('RUNNER_TEMP', 'TMPDIR', 'TMP', 'TEMP')})

    def test_run_rejects_symlinked_evidence_ancestor_before_creation(self):
        link = self.root / 'evidence-link'
        link.symlink_to(self.output, target_is_directory=True)
        self.evidence = link / 'build'
        with self.assertRaisesRegex(driver.BuildError, 'real directory'):
            self.execute()
        self.assertFalse((self.output / 'build').exists())
        self.assertEqual(self.runner.phases, [])

    def test_fresh_python_tempfile_compiles_and_executes_in_bound_root(self):
        compiler = shutil.which('cc', path=driver.ENV['PATH'])
        if compiler is None:
            self.skipTest('host C compiler unavailable')
        self.evidence.mkdir()
        env = dict(driver.ENV, **driver.temporary_environment(self.evidence, self.evidence))
        # The coordinator process has already cached a different temp directory.
        self.assertNotEqual(Path(tempfile.gettempdir()), self.evidence)
        probe = '''import os
from pathlib import Path
import subprocess
import tempfile
root = Path(os.environ['RUNNER_TEMP'])
assert Path(tempfile.gettempdir()) == root
with tempfile.TemporaryDirectory() as name:
    directory = Path(name)
    assert directory.parent == root
    source = directory / 'registry.c'
    binary = directory / 'registry-tests'
    source.write_text('#include <stdio.h>\\nint main(void) { puts("registry-temp-ok"); return 0; }\\n')
    subprocess.run([COMPILER, str(source), '-o', str(binary)], check=True)
    result = subprocess.run([str(binary)], stdout=subprocess.PIPE, check=True)
    assert result.stdout == b'registry-temp-ok\\n'
    print(result.stdout.decode('ascii'), end='')
assert not directory.exists()
'''.replace('COMPILER', repr(compiler))
        validation = driver.workflow_bodies(WORKFLOW_TEXT)[driver.STEPS[4]]
        environment_start = validation.index('isolated_environment=(')
        environment_end = validation.index(' TEMP="$TEMP")\n', environment_start)
        environment_end += len(' TEMP="$TEMP")\n')
        environment = validation[environment_start:environment_end]
        script = self.root / 'registry-temp-phase.sh'
        # Cross the real phase-4 env -i boundary rather than invoking Python
        # directly with the outer runner environment.
        script.write_text(
            environment +
            '"${kbuild_environment[@]}" /usr/bin/python3 -E -s <<\'PY\'\n' +
            probe + 'PY\n')
        log = self.root / 'registry-temp-phase.log'
        self.assertEqual(driver.Runner().phase(script, self.repo, env, log), 0,
                         log.read_text())
        self.assertEqual(log.read_bytes(), b'registry-temp-ok\n')
        self.assertEqual(list(self.evidence.iterdir()), [])

    def test_postcheck_temp_environment_anchor_is_unique_and_fail_closed(self):
        original = 'kbuild_environment=("${isolated_environment[@]}" PATH=/usr/bin:/bin)'
        for mutated in (
                WORKFLOW_TEXT.replace(original, original + '\n          ' + original, 1),
                WORKFLOW_TEXT.replace(original, 'kbuild_environment=("${isolated_environment[@]}")', 1)):
            with self.assertRaisesRegex(
                    driver.BuildError, 'postcheck environment adaptation anchor changed'):
                driver.workflow_bodies(mutated)

    def test_runner_temp_alone_does_not_select_python_tempfile_root(self):
        self.evidence.mkdir()
        default = self.root / 'default-temp'
        default.mkdir()
        env = dict(driver.ENV, RUNNER_TEMP=str(self.evidence), TMPDIR=str(default))
        probe = ('import os, tempfile; from pathlib import Path; '
                 'assert Path(tempfile.gettempdir()) != Path(os.environ["RUNNER_TEMP"]); '
                 'print(tempfile.gettempdir())')
        result = subprocess.run(['/usr/bin/python3', '-E', '-s', '-c', probe],
                                env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), os.fsencode(default))

    def test_phase_execution_denial_remains_failure(self):
        self.evidence.mkdir()
        env = dict(driver.ENV, **driver.temporary_environment(self.evidence, self.evidence))
        script = self.root / 'denied-execution.sh'
        # Model the EACCES exec failure from a noexec mount with file permissions;
        # this needs no mount privilege and is not evidence of mount policy.
        script.write_text("""/usr/bin/python3 -E -s <<'PY'
from pathlib import Path
import subprocess
import tempfile
with tempfile.TemporaryDirectory() as name:
    binary = Path(name) / 'registry-tests'
    binary.write_text('#!/bin/sh\\nexit 0\\n')
    binary.chmod(0o644)
    subprocess.run([str(binary)], check=True)
PY
""")
        log = self.root / 'denied-execution.log'
        self.assertNotEqual(driver.Runner().phase(script, self.repo, env, log), 0)
        self.assertIn(b'PermissionError: [Errno 13] Permission denied', log.read_bytes())
        self.assertEqual(list(self.evidence.iterdir()), [])

    def test_successful_commands_without_artifacts_fail(self):
        self.runner.create_artifacts = False
        result = self.execute()
        self.assertEqual(result['status'], 'FAIL')
        self.assertEqual(result['phase'], 'artifact-verification')

    def test_each_phase_failure_preserves_partial_log_and_status(self):
        for phase in range(1, 6):
            with self.subTest(phase=phase):
                self.evidence = self.root / ('failure-' + str(phase))
                self.runner.phases = []
                self.runner.fail_phase = phase
                result = self.execute()
                self.assertEqual(result['status'], 'FAIL')
                self.assertEqual(result['commands'][-1]['exit_code'], 37)
                self.assertEqual(len(result['commands']), phase)
                self.assertTrue((self.evidence / 'driver.log').stat().st_size)

    def test_artifact_checksum_mutation_fails(self):
        self.runner.corrupt = lambda root: (root / 'bzImage').write_text('mutated')
        self.assertEqual(self.execute()['status'], 'FAIL')

    def test_empty_artifact_fails(self):
        self.runner.corrupt = lambda root: (root / 'mcctrl.ko').write_text('')
        self.assertEqual(self.execute()['status'], 'FAIL')

    def test_missing_validator_result_fails(self):
        self.runner.corrupt = lambda root: (root / 'kbuild-link-closure.json').unlink()
        self.assertEqual(self.execute()['status'], 'FAIL')

    def test_input_mutation_and_incomplete_inventory_reject(self):
        for name in ('repo', 'asset', 'manifest', 'driver', 'gitlink'):
            with self.subTest(name=name):
                original = json.loads(json.dumps(self.data))
                self.evidence = self.root / ('reject-' + name)
                if name == 'repo':
                    self.data['repository_files']['host-kernel/fixture.rs'] = '0' * 64
                elif name == 'asset':
                    self.data['assets'][driver.ARCHIVE] = '0' * 64
                elif name == 'manifest':
                    self.data['repository_files'].pop('host-kernel/fixture.rs')
                else:
                    if name == 'driver':
                        self.data['driver_sha256'] = '0' * 64
                    else:
                        self.data['gitlinks']['vendor/unconsumed'] = 'f' * 40
                self.save_manifest()
                result = self.execute()
                self.assertEqual(result['status'], 'FAIL')
                self.assertEqual(result['commands'], [])
                self.data = original

    def test_head_submodule_and_dirty_mutations(self):
        for key, value in [('head', 'b' * 40), ('submodule', 'c' * 40), ('dirty', True)]:
            self.evidence = self.root / ('reject-' + key)
            old = getattr(self.runner, key)
            setattr(self.runner, key, value)
            self.assertEqual(self.execute()['status'], 'FAIL')
            setattr(self.runner, key, old)

    def test_schema_and_ihk_manifest_fields_are_required(self):
        for key in ('schema', 'ihk_sha'):
            for value in (None, 'forged'):
                with self.subTest(key=key, value=value):
                    data = dict(self.data)
                    if value is None:
                        data.pop(key)
                    else:
                        data[key] = value
                    with self.assertRaisesRegex(driver.BuildError, 'schema or IHK'):
                        driver.verify_inputs(self.repo, self.candidate, self.assets,
                                             data, self.runner)

    def test_forged_manifest_cannot_bless_changed_tracked_bytes(self):
        for relative in ('host-kernel/fixture.rs', 'ihk/frozen.rs'):
            with self.subTest(relative=relative):
                path = self.repo / relative
                original = path.read_bytes()
                path.write_bytes(b'forged source')
                data = dict(self.data, repository_files=dict(self.rows))
                data['repository_files'][relative] = driver.sha256(path)
                with self.assertRaisesRegex(driver.BuildError, 'Git blob bytes differ'):
                    driver.verify_inputs(self.repo, self.candidate, self.assets,
                                         data, self.runner)
                path.write_bytes(original)

    def test_repository_symlink_is_bound_as_link_text(self):
        link = self.repo / 'link'
        link.symlink_to('missing-but-tracked')
        rows = {'link': hashlib.sha256(b'missing-but-tracked').hexdigest()}
        driver.bound_files(self.repo, rows, links=True)
        with self.assertRaises(driver.BuildError):
            driver.bound_files(self.repo, rows)

    def test_source_build_config_and_validation_bodies_preserved(self):
        bodies = driver.workflow_bodies(WORKFLOW_TEXT)
        # Compare literal original bodies, not lists of validator keywords.
        for name in (driver.STEPS[0], driver.STEPS[3]):
            raw = WORKFLOW_TEXT.split('      - name: ' + name + '\n', 1)[1]
            raw = raw.split('        run: |\n', 1)[1].split('\n      - name:', 1)[0]
            raw = '\n'.join(line[10:] if line else '' for line in raw.splitlines()).rstrip() + '\n'
            self.assertEqual(bodies[name], raw)
        acquisition = bodies[driver.STEPS[1]]
        original_suffix = WORKFLOW_TEXT.split('          archive="$SOURCE_ASSETS/', 1)[1]
        original_suffix = original_suffix.split('\n      - name:', 1)[0]
        suffix = 'archive="$SOURCE_ASSETS/' + '\n'.join(
            line[10:] if i else line for i, line in enumerate(original_suffix.splitlines())).rstrip() + '\n'
        self.assertTrue(acquisition.endswith(suffix))
        phase2 = bodies[driver.STEPS[2]]
        self.assertEqual(phase2.count('cd "$BUILD_DIR"'), 1)
        self.assertEqual(phase2.count('merge_config.sh'), 1)
        self.assertIn('(\n  cd "$BUILD_DIR"\n', phase2)
        self.assertIn('\n)\n"${kbuild_environment[@]}" /usr/bin/make', phase2)
        self.assertNotIn('cd "$GITHUB_WORKSPACE"', phase2)
        validation = bodies[driver.STEPS[4]]
        self.assertIn('scripts/native_rust_kbuild_link_closure.py', validation)
        self.assertIn(
            'RUNNER_TEMP="$RUNNER_TEMP" TMPDIR="$TMPDIR" TMP="$TMP" TEMP="$TEMP")',
            validation)
        self.assertNotIn('github_run_id =', validation)
        # All artifact validators after the provenance block survive byte-exact.
        suffix = WORKFLOW_TEXT.split('          # Preserve the exact binaries', 1)[1]
        suffix = suffix.split('\n      - name:', 1)[0]
        suffix = '# Preserve the exact binaries' + '\n'.join(
            line[10:] if i else line for i, line in enumerate(suffix.splitlines())).rstrip() + '\n'
        self.assertTrue(validation.endswith(suffix))
        for index, body in enumerate(bodies.values()):
            script = self.root / ('syntax-%d.sh' % index)
            script.write_text(body)
            result = subprocess.run(['/usr/bin/bash', '-n', str(script)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_adaptation_anchor_drift_rejects(self):
        for old, new in [('archive="$SOURCE_ASSETS/', 'archive="$DIFFERENT/'),
                         ('# Preserve the exact binaries', '# changed marker'),
                         (driver.STEPS[3], 'Different compilation step'),
                         ('merge_config.sh', 'merge_config_changed.sh')]:
            with self.assertRaises(driver.BuildError):
                driver.workflow_bodies(WORKFLOW_TEXT.replace(old, new))

    def test_real_phase_runner_streams_failure_bytes_and_exit(self):
        script = self.root / 'ordinary-local-regression.sh'
        script.write_text("printf 'partial-output\\n'; printf 'failure-output\\n' >&2; exit 37\n")
        log = self.root / 'ordinary-local-regression.log'
        result = driver.Runner().phase(script, self.repo, dict(driver.ENV), log)
        self.assertEqual(result, 37)
        self.assertEqual(log.read_bytes(), b'partial-output\nfailure-output\n')


if __name__ == '__main__':
    unittest.main()
