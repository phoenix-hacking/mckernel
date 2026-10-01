"""Cheap packet tests; no Docker, root, build, or network."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).parents[2]
SOURCE = ROOT / 'docs/verification/evidence/native-exact-scratch15-build-execution-20261001.py'
spec = importlib.util.spec_from_file_location('scratch15_execution', SOURCE)
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
REAL_GIT_BLOB = m.git_blob

class Packet(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        out, evidence = root / 'out', root / 'evidence'; out.mkdir(); evidence.mkdir()
        for key, value in {'ORIGINAL': root/'original', 'LOG': root/'log', 'TERMINAL': root/'terminal', 'WRAPPER': root/'wrapper',
                           'CANDIDATE': root/'candidate', 'IHK': root/'ihk', 'OVERLAY': root/'overlay',
                           'OUTPUT': out, 'EVIDENCE': evidence, 'LEASE': root/'lease', 'DERIVED': root/'derived',
                           'EXPORTSET': str(root/'exportset')}.items(): setattr(m, key, value)
        m.CANDIDATE.mkdir(); m.IHK.mkdir(); result = m.IHK/'test/ihklib/whitebox/src/driver/mckernel/syscall.c'; result.parent.mkdir(parents=True); result.write_bytes(b'result'); m.OVERLAY.write_bytes(b'overlay')
        manifest = root/'manifest'; manifest.write_bytes(b'manifest'); m.MANIFEST_SHA256 = m.sha(manifest.read_bytes())
        m.LOG.write_bytes(b'fixture'); m.LOG_SHA256 = m.sha(m.LOG.read_bytes())
        m.TERMINAL.write_text(json.dumps({'returncode': 0, 'log': str(m.LOG), 'log_sha256': m.LOG_SHA256})); m.TERMINAL_SHA256 = m.sha(m.TERMINAL.read_bytes())
        m.WRAPPER.write_bytes(b'fixture'); m.WRAPPER_SHA256 = m.sha(m.WRAPPER.read_bytes())
        m.OVERLAY_SHA256 = m.sha(m.OVERLAY.read_bytes()); m.OVERLAY_RESULT_SHA256 = m.sha(result.read_bytes())
        m.IHK_RESULT = result
        self.request = {'input_manifest': str(manifest), 'input_manifest_sha256': m.MANIFEST_SHA256, 'release_required': True,
                        'operational_exclusion_path': '/home/holden/mckernel-work/scratch/native-exact-candidate-operational-exclusion-exportset-16.json',
                        'operational_exclusion_consumed': True, 'preparation_only': True, 'execution_released': False, 'executable': False,
                        'candidate_sha': m.CANDIDATE_SHA, 'ihk_overlay_base_sha': m.IHK_HEAD, 'ihk_overlay_sha256': m.OVERLAY_SHA256,
                        'ihk_overlay_result_blob_sha256': m.OVERLAY_RESULT_SHA256, 'source_root': str(m.CANDIDATE), 'ihk_overlay_path': str(m.OVERLAY),
                        'output_root': str(m.OUTPUT), 'evidence_root': str(m.EVIDENCE), 'lease_path': str(m.LEASE),
                        'owner_path': str(m.CANDIDATE/'scripts/native_rust_exact_build_container_owner.py'), 'owner_path_sha256': m.OWNER_SHA256,
                        'provenance_path': str(m.CANDIDATE/'scripts/native_rust_exact_build_offline.py'), 'provenance_path_sha256': m.DRIVER_SHA256,
                        'driver_path': str(m.CANDIDATE/'scripts/native_rust_exact_build_offline.py'), 'driver_path_sha256': m.DRIVER_SHA256}
        m.ORIGINAL.write_bytes(json.dumps(self.request, separators=(',', ':')).encode()); m.ORIGINAL_SHA256 = m.sha(m.ORIGINAL.read_bytes())
        m.IHK_RESULT = result
        m.git_blob = lambda commit: None
        m.git_run = lambda args, **kwargs: type('R', (), {'returncode': 0, 'stdout': ((m.IHK_HEAD if str(m.IHK / '.git') in str(args) else m.CANDIDATE_SHA) + '\n').encode() if 'rev-parse' in str(args) else b''})()

    def test_derive_changes_exactly_five_values(self):
        derived = m.derive(self.request)
        changed = {key for key in self.request if derived[key] != self.request[key]}
        self.assertEqual(changed, {'operational_exclusion_path', 'operational_exclusion_consumed',
                                   'preparation_only', 'execution_released', 'executable'})
        self.assertEqual(set(derived), set(self.request)); self.assertTrue(derived['release_required'])

    def test_validate_rejects_existing_destination_and_symlink(self):
        self.assertEqual(m.validate_inputs('a' * 40)['candidate_sha'], m.CANDIDATE_SHA)
        m.DERIVED.touch()
        with self.assertRaisesRegex(m.Refusal, 'destination-present'): m.validate_inputs('a' * 40)
        m.DERIVED.unlink(); m.OUTPUT.rmdir(); m.OUTPUT.symlink_to(m.EVIDENCE, target_is_directory=True)
        with self.assertRaisesRegex(m.Refusal, 'directory-binding'): m.validate_inputs('a' * 40)

    def test_publish_is_create_only_and_canonical(self):
        digest, canonical, size = m.publish(m.derive(self.request))
        self.assertEqual(m.sha(m.DERIVED.read_bytes()), digest); self.assertEqual(size, m.DERIVED.stat().st_size)
        self.assertNotEqual(digest, canonical)
        with self.assertRaises(FileExistsError): m.publish(m.derive(self.request))

    def test_wrapper_argv_binds_aggregate(self):
        self.assertEqual(m.wrapper_argv()[-2:], ['--launcher-aggregate-gib', '16.2158'])
        self.assertEqual(m.wrapper_argv()[5], str(m.DERIVED))

    def test_short_writes_are_completed_and_hashes_are_distinct(self):
        original = m.os.write
        def one_byte(fd, data):
            return original(fd, data[:1])
        with mock.patch.object(m.os, 'write', side_effect=one_byte):
            byte_hash, canonical_hash, _ = m.publish(m.derive(self.request))
        self.assertEqual(byte_hash, m.sha(m.DERIVED.read_bytes()))
        self.assertNotEqual(byte_hash, canonical_hash)

    def test_release_ref_and_blob_mismatch_fail_closed(self):
        good_packet = SOURCE.read_bytes()
        good_test = (ROOT / m.TEST_PATH).read_bytes()
        good_wrapper = m.WRAPPER.read_bytes()
        def response(stdout=b'', returncode=0):
            return type('R', (), {'returncode': returncode, 'stdout': stdout})()
        calls = iter((
            response((('0' * 40) + '\n').encode()),
        ))
        with mock.patch.object(m, 'git_run', side_effect=lambda *a, **k: next(calls)):
            with self.assertRaisesRegex(m.Refusal, 'release-ref-mismatch'):
                REAL_GIT_BLOB('a' * 40)
        calls = iter((
            response((('a' * 40) + '\n').encode()), response(),
            response(good_wrapper), response(good_packet + b'tamper'), response(good_test),
        ))
        with mock.patch.object(m, 'git_run', side_effect=lambda *a, **k: next(calls)):
            with self.assertRaisesRegex(m.Refusal, 'release-source-blob'):
                REAL_GIT_BLOB('a' * 40)

    def test_main_executes_once_only_after_successful_publish(self):
        order = []
        def published(_request):
            order.append('publish')
            return ('bytes', 'canonical', 1)
        def executed(program, argv):
            order.append(('exec', program, tuple(argv)))
            raise RuntimeError('exec-boundary')
        with mock.patch.object(m, 'validate_inputs', return_value=self.request), \
             mock.patch.object(m, 'publish', side_effect=published), \
             mock.patch.object(m.os, 'execv', side_effect=executed) as execv:
            with self.assertRaisesRegex(RuntimeError, 'exec-boundary'):
                m.main(['--release-commit', 'a' * 40, '--execute'])
        self.assertEqual(order[0], 'publish')
        self.assertEqual(order[1][0], 'exec')
        execv.assert_called_once()

    def test_admission_or_publication_failure_never_executes(self):
        for stage, error in (
            ('validate', m.Refusal('release-source-blob')),
            ('publish', OSError('parent-fsync-failure')),
        ):
            with self.subTest(stage=stage), \
                 mock.patch.object(m, 'validate_inputs',
                                   side_effect=error if stage == 'validate' else None,
                                   return_value=self.request), \
                 mock.patch.object(m, 'publish',
                                   side_effect=error if stage == 'publish' else None), \
                 mock.patch.object(m.os, 'execv') as execv:
                with self.assertRaises(type(error)):
                    m.main(['--release-commit', 'a' * 40, '--execute'])
                execv.assert_not_called()

    def test_parent_fsync_failure_retains_published_request(self):
        real_fsync = m.os.fsync
        calls = 0
        def fail_parent(fd):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise OSError('parent-fsync-failure')
            return real_fsync(fd)
        with mock.patch.object(m.os, 'fsync', side_effect=fail_parent):
            with self.assertRaisesRegex(OSError, 'parent-fsync-failure'):
                m.publish(m.derive(self.request))
        self.assertTrue(m.DERIVED.is_file())
        self.assertEqual(m.DERIVED.read_bytes(), m.payload(m.derive(self.request)))

    def test_packet_has_no_privileged_or_container_driver(self):
        text = SOURCE.read_text()
        self.assertNotIn('sudo', text); self.assertNotIn('docker', text.lower())
        self.assertIn("RELEASE_REF = 'refs/remotes/origin/codex/local-native-staging-repair'", text)
        self.assertIn("'rev-parse', '--verify', RELEASE_REF + '^{commit}'", text)
        self.assertIn("'/usr/bin/git'", text); self.assertIn("'PATH': '/usr/bin:/bin'", text)

if __name__ == '__main__': unittest.main()
