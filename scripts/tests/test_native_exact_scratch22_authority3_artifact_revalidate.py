import hashlib
import json
from pathlib import Path
import tempfile
import types
import unittest
from unittest import mock

from scripts import native_exact_scratch22_authority3_artifact_revalidate as payload
from scripts import native_rust_exact_build_offline as original


class FinalCheckPayloadTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='retained-final-step-')
        self.addCleanup(self.tmp.cleanup)
        self.top = Path(self.tmp.name)
        self.source, self.output, self.prior, self.capture = (self.top/name for name in ('src', 'out', 'prior', 'capture'))
        for path in (self.source, self.output, self.prior, self.capture):
            path.mkdir()
        (self.source/'scripts').mkdir()
        checker = b'reviewed fixture overlay\n'
        (self.source/'scripts/ihk_native_lifecycle_check.py').write_bytes(checker)
        workflow = Path(__file__).resolve().parents[2]/original.WORKFLOW
        target = self.source/original.WORKFLOW
        target.parent.mkdir(parents=True)
        target.write_bytes(workflow.read_bytes())
        exports = {'NATIVE_SRPM': '/assets/kernel.src.rpm',
                   'NATIVE_SOURCE_ROOT': str(self.output/'source/linux-6.12.0-211.44.1.el10_2'),
                   'NATIVE_BASELINE_CONFIG': '/assets/kernel.config',
                   'NATIVE_BUILD_DIR': str(self.output/'build')}
        (self.prior/'phase.env').write_text(''.join(k+'='+v+'\n' for k,v in exports.items()))
        old = self.prior/'native-rust-build-evidence'
        old.mkdir()
        for name in payload.SEEDS:
            (old/name).write_bytes(name.encode())
        (old/'old-failure-must-not-copy').write_bytes(b'original fail')
        self.driver = types.SimpleNamespace(ENV=original.ENV, WORKFLOW=original.WORKFLOW,
            STEPS=original.STEPS, workflow_bodies=original.workflow_bodies, verify_artifacts=mock.Mock())
        self.runner = mock.Mock()
        def phase(script, cwd, env, log):
            (self.capture/'native-rust-build-evidence/commit.sha').write_text(payload.CANDIDATE+'\n')
            return 0
        self.runner.phase.side_effect = phase
        for name, value in [('SOURCE', self.source), ('OUTPUT', self.output),
                            ('CHECKER_SHA256', hashlib.sha256(checker).hexdigest())]:
            patch = mock.patch.object(payload, name, value)
            patch.start()
            self.addCleanup(patch.stop)

    def run_payload(self):
        return payload.run(prior=self.prior, capture=self.capture, driver=self.driver, runner=self.runner)

    def test_exact_original_final_body_only_and_two_seed_files(self):
        before = {str(p.relative_to(self.prior)): p.read_bytes() for p in self.prior.rglob('*') if p.is_file()}
        result = self.run_payload()
        self.assertEqual(result['status'], 'PASS_DIAGNOSTIC_FINAL_CHECKS')
        self.assertFalse(result['strict_fresh_build_pass'])
        script, cwd, env, log = self.runner.phase.call_args.args
        expected = original.workflow_bodies((self.source/original.WORKFLOW).read_text())[original.STEPS[4]]
        self.assertEqual(script.read_text(), expected)
        self.assertIn('kernelrelease)', expected)
        self.assertIn('assert_modinfo_binding', expected)
        self.assertIn('scripts/native_rust_kbuild_link_closure.py', expected)
        self.assertEqual(cwd, self.source)
        self.assertEqual(env['NATIVE_BUILD_DIR'], str(self.output/'build'))
        for key in ('RUNNER_TEMP', 'TMPDIR', 'TMP', 'TEMP'):
            self.assertEqual(env[key], str(self.capture))
        evidence = self.capture/'native-rust-build-evidence'
        self.assertEqual({p.name for p in evidence.iterdir()}, {*payload.SEEDS, 'commit.sha'})
        self.assertEqual(before, {str(p.relative_to(self.prior)): p.read_bytes() for p in self.prior.rglob('*') if p.is_file()})
        self.assertEqual(list(self.output.iterdir()), [])
        self.driver.verify_artifacts.assert_called_once_with(evidence)

    def test_failed_original_step_retained_and_never_verifies(self):
        self.runner.phase.side_effect = None
        self.runner.phase.return_value = 2
        with self.assertRaisesRegex(payload.RevalidationError, 'must remain read-only'):
            self.run_payload()
        record = json.loads((self.capture/'result.json').read_text())
        self.assertEqual((record['status'], record['exit_code']), ('FAIL', 2))
        self.driver.verify_artifacts.assert_not_called()

    def test_nonempty_capture_refused_without_writes(self):
        (self.capture/'preserved').write_bytes(b'old')
        with self.assertRaisesRegex(payload.RevalidationError, 'not fresh'):
            self.run_payload()
        self.assertEqual(list(self.capture.iterdir()), [self.capture/'preserved'])
        self.runner.phase.assert_not_called()

    def test_unknown_environment_or_wrong_original_path_refused(self):
        env = self.prior/'phase.env'
        initial = env.read_text()
        for raw in (initial+'PATH=/bad\n', initial.replace('/out/build', '/wrong/build')):
            env.write_text(raw)
            with self.assertRaises(payload.RevalidationError):
                self.run_payload()
            self.assertEqual(list(self.capture.iterdir()), [])

    def test_seed_symlink_and_overlapping_capture_refused(self):
        seed = self.prior/'native-rust-build-evidence'/payload.SEEDS[0]
        seed.unlink()
        seed.symlink_to(self.prior/'phase.env')
        with self.assertRaises(OSError):
            self.run_payload()
        self.runner.phase.assert_not_called()
        with self.assertRaisesRegex(payload.RevalidationError, 'overlap'):
            payload.run(prior=self.prior, capture=self.output, driver=self.driver, runner=self.runner)

    def test_overlay_mismatch_refused(self):
        (self.source/'scripts/ihk_native_lifecycle_check.py').write_bytes(b'wrong')
        with self.assertRaisesRegex(payload.RevalidationError, 'overlay differs'):
            self.run_payload()
        self.assertEqual(list(self.capture.iterdir()), [])


if __name__ == '__main__':
    unittest.main()
