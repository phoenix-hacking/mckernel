import hashlib
import json
from pathlib import Path
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
        self.repo, self.assets, self.output, self.evidence = [self.root / p for p in ('repo', 'assets', 'out', 'ev')]
        for path in (self.repo, self.assets, self.output):
            path.mkdir()
        files = {driver.WORKFLOW: WORKFLOW_TEXT, 'ihk/frozen.rs': 'immutable submodule source',
                 'host-kernel/fixture.rs': 'immutable source'}
        for name, text in files.items():
            path = self.repo / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text)
        self.rows = {name: driver.sha256(self.repo / name) for name in files}
        for name in (driver.ARCHIVE, driver.BASELINE, driver.SRPM, driver.DEBRAND):
            (self.assets / name).write_text('test bytes for ' + name)
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
        for name in (driver.STEPS[0], driver.STEPS[2], driver.STEPS[3]):
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
        validation = bodies[driver.STEPS[4]]
        self.assertIn('scripts/native_rust_kbuild_link_closure.py', validation)
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
                         (driver.STEPS[3], 'Different compilation step')]:
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
