"""Changed cfg/auth boundaries only; no host-profile, root or Docker execution.
Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
The temporary canonical layout is a fixture, never runtime release authority.
"""
from pathlib import Path
import copy
import hashlib
import importlib.util
import json
import os
import sys
import tempfile
import unittest
from unittest.mock import patch

D = Path(__file__).resolve().parent
sys.path.insert(0, '/home/holden/mckernel/scripts')


def load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class CanonicalAuth(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='canonical-auth-', dir=D)
        self.addCleanup(self.temp.cleanup)
        self.repo = Path(self.temp.name)
        cohort = json.loads((D / 'CANONICAL-RUNTIME-SOURCE-COHORT.json').read_text())
        for row in cohort['rows']:
            raw = Path(row['source']['path']).read_bytes()
            self.assertEqual(hashlib.sha256(raw).hexdigest(), row['source']['sha256'])
            target = self.repo / row['relative']
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(raw)
        self.m = load_module(self.repo / 'scripts/native_running_external_modules_owner.py',
                             'temporary_canonical_owner')
        self.hashes = cohort['source_sha256']
        self.request_path = self.repo / 'TEST_ONLY-request.json'
        self.request = dict(nonce='b' * 32, boot_id=self.m.BOOT,
                            terminal_policy='remove-owned-terminal',
                            driver=dict(path=str(self.repo / 'scripts/native_running_external_modules_offline.py'),
                                        sha256=self.hashes['scripts/native_running_external_modules_offline.py']))

    def saved(self, name, value):
        path = self.repo / name
        raw = self.m.canonical(value)
        with path.open('xb') as stream:
            stream.write(raw)
        os.chmod(path, 0o600)
        return dict(path=str(path), sha256=self.m.sha(raw))

    def release(self, request):
        request_ref = self.saved('TEST_ONLY-request.json', request)
        source_review = self.saved('TEST_ONLY-source-review.json', dict(
            decision='PASS_SOURCE', implementation_ownership=False,
            reviewer='TEST_ONLY_SOURCE_FIXTURE', source_sha256=self.hashes))
        release = dict(schema='mckernel.native-running-external-modules-host-output-release.v2',
                       status='PASS_EXECUTION_RELEASE', execution_count=1,
                       request=request_ref, nonce=request['nonce'], boot_id=self.m.BOOT,
                       fetched_source_verified=True, terminal_policy=request['terminal_policy'],
                       historical_observer=dict(path=str(self.m.HISTORICAL_OBSERVER),
                           sha256=self.m.HISTORICAL_OBSERVER_SHA,
                           prefix=list(self.m.HISTORICAL_PREFIX), timeout_seconds=30),
                       source_sha256=self.hashes, source_review=source_review,
                       author='TEST_ONLY_NO_RUNTIME_RELEASE')
        release['execution_review'] = self.saved('TEST_ONLY-execution-review.json', dict(
            decision='PASS_EXECUTION', implementation_ownership=False,
            reviewer='TEST_ONLY_EXECUTION_FIXTURE',
            reviewed_release_payload_sha256=self.m.sha(self.m.canonical(release))))
        return request_ref, self.saved('TEST_ONLY-release.json', release)

    def test_actual_sourceguard_accepts_canonical_complete_cohort(self):
        self.assertEqual(self.m.validate_runtime_source_bindings(self.hashes), self.hashes)

    def test_actual_sourceguard_refuses_isolated_entrypoint(self):
        with patch.object(self.m, '__file__', str(D / 'source/scripts/native_running_external_modules_owner.py')):
            with self.assertRaisesRegex(self.m.Refusal, 'executing owner differs from installed runtime source'):
                self.m.validate_runtime_source_bindings(self.hashes)

    def test_actual_sourceguard_refuses_incomplete_cohort(self):
        value = dict(self.hashes)
        value.pop('scripts/native_running_external_modules_offline.py')
        with self.assertRaisesRegex(self.m.Refusal, 'complete runtime source closure required'):
            self.m.validate_runtime_source_bindings(value)

    def test_actual_authenticate_accepts_canonical_role_hash_join(self):
        request_ref, release_ref = self.release(self.request)
        request, release = self.m.authenticate(Path(request_ref['path']), request_ref['sha256'],
                                               Path(release_ref['path']), release_ref['sha256'])
        self.assertEqual(request['driver']['path'], str(self.repo / 'scripts/native_running_external_modules_offline.py'))
        self.assertEqual(request['driver']['sha256'], release['source_sha256']['scripts/native_running_external_modules_offline.py'])

    def test_actual_authenticate_refuses_driver_role_hash_mismatch(self):
        request = copy.deepcopy(self.request)
        request['driver']['sha256'] = '0' * 64
        request_ref, release_ref = self.release(request)
        with self.assertRaisesRegex(self.m.Refusal, 'driver source release differs'):
            self.m.authenticate(Path(request_ref['path']), request_ref['sha256'],
                                Path(release_ref['path']), release_ref['sha256'])


if __name__ == '__main__':
    cfg = load_module(D / 'check_current68_opt_in.py', 'combined_cfg_fixture')
    suite = unittest.TestSuite([unittest.defaultTestLoader.loadTestsFromTestCase(cfg.OptInFlow),
                               unittest.defaultTestLoader.loadTestsFromTestCase(CanonicalAuth)])
    import subprocess
    def forbidden(*args, **kwargs):
        raise AssertionError('No subprocess permitted in cfg/auth fixtures')
    # Python3.8 uuid imports platform.system(), which otherwise spawns uname.
    # Supply only this import-time platform fact; auth/source checks remain real.
    with patch('platform.system', return_value='Linux'), patch.object(subprocess, 'run', forbidden), patch.object(subprocess, 'check_output', forbidden), patch.object(subprocess, 'Popen', forbidden):
        result = unittest.TextTestRunner(verbosity=2).run(suite)
    raise SystemExit(0 if result.wasSuccessful() else 1)
