"""Cheap packet tests; no Docker, root, build, or network."""
import importlib.util
import contextlib
import io
import json
from pathlib import Path
import tempfile
import types
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / 'docs/verification/evidence/native-exact-scratch17-build-execution-20261001.py'
def load_packet():
    spec = importlib.util.spec_from_file_location('scratch17_execution', SOURCE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ProductionArtifacts(unittest.TestCase):
    """Real prepared inputs; no filesystem, hash, or Git HEAD substitution."""
    def test_production_constants_bind_prepared_request(self):
        m = load_packet()
        request_path = Path('/home/holden/mckernel-work/scratch/native-exact-delta-request-50b08432-scratch-17.json')
        self.assertEqual(m.ORIGINAL, request_path)
        self.assertEqual(m.sha(request_path.read_bytes()), '852f7d8f652079828cd30377de30d7d810e7747e8e0703a1efb65ae09cedb852')
        self.assertEqual(m.ORIGINAL_SHA256, m.sha(request_path.read_bytes()))
        request = json.loads(request_path.read_bytes())
        production_exportset = '/home/holden/mckernel-work/scratch/native-exact-candidate-operational-exclusion-scratch17.json'
        self.assertEqual(request['operational_exclusion_path'], production_exportset)
        self.assertEqual(m.EXPORTSET, production_exportset)
        self.assertFalse(request['operational_exclusion_consumed'])
        self.assertTrue(request['preparation_only'])
        self.assertFalse(request['execution_released'])
        self.assertFalse(request['executable'])
        manifest_hash = 'cbdfac7bc5b9e3c03e112335d12eeca3420835f630c134c269fbf7ca7f0a92bc'
        self.assertEqual(request['input_manifest_sha256'], manifest_hash)
        self.assertEqual(m.MANIFEST_SHA256, manifest_hash)
        self.assertEqual(m.sha(Path(request['input_manifest']).read_bytes()), manifest_hash)
        scratch = Path('/home/holden/mckernel-work/scratch')
        self.assertEqual(m.LOG, scratch / 'native-exact-candidate-delta-preparation-50b08432-scratch-17.log')
        self.assertEqual(m.TERMINAL, scratch / 'native-exact-candidate-delta-preparation-50b08432-scratch-17-terminal.json')
        self.assertEqual(m.sha(m.LOG.read_bytes()), m.LOG_SHA256)
        self.assertEqual(m.sha(m.TERMINAL.read_bytes()), m.TERMINAL_SHA256)
        for name, key in (('CANDIDATE', 'source_root'), ('OVERLAY', 'ihk_overlay_path'),
                          ('OUTPUT', 'output_root'), ('EVIDENCE', 'evidence_root'),
                          ('LEASE', 'lease_path')):
            self.assertEqual(str(getattr(m, name)), request[key])
        for key, expected in (('owner_path', m.OWNER_SHA256),
                              ('provenance_path', m.DRIVER_SHA256),
                              ('driver_path', m.DRIVER_SHA256)):
            actual = m.sha(Path(request[key]).read_bytes())
            if key == 'owner_path' and actual != expected:
                # The immutable prepared request predates the owner rebind;
                # admission must reject it until preparation is rerun.
                self.assertEqual(actual, 'a8c4c9fc61fab312e3a6e48e93b417453ec12e6543d6adbb7038933f92e79155')
            else:
                self.assertEqual(actual, expected)
        self.assertEqual(m.WRAPPER, ROOT / m.RELEASE_PATH)
        self.assertEqual(m.WRAPPER_SHA256,
                         '578d34e8fa96a08a0729edb9ff58ffa9d66837bbf30eed8cb75fa9da9f7f26b1')
        self.assertNotEqual(m.sha(m.WRAPPER.read_bytes()), m.WRAPPER_SHA256)
        self.assertEqual(m.IHK, m.CANDIDATE / 'ihk')
        self.assertEqual(m.DERIVED, scratch / 'native-exact-build-request-50b08432-scratch-17-execution.json')
        self.assertFalse(m.lexists(m.DERIVED))

    def test_actual_artifact_admission_validate_only(self):
        m = load_packet()
        output = io.StringIO()
        # The release cannot contain these bytes until the coordinator commits
        # and fetches them. This is the sole substituted production boundary.
        with mock.patch.object(m, 'git_blob') as release, contextlib.redirect_stdout(output):
            rc = m.main(['--release-commit', 'a' * 40])
        self.assertEqual(rc, 2)
        release.assert_not_called()
        report = json.loads(output.getvalue())
        self.assertEqual(report['status'], 'TERMINAL_NON_RELEASABLE')
        request = json.loads(m.ORIGINAL.read_bytes())
        derived = m.derive(request)
        self.assertEqual({key for key in request if request[key] != derived[key]},
                         {'preparation_only', 'execution_released', 'executable'})
        self.assertEqual(set(request), set(derived))
        self.assertFalse(derived['operational_exclusion_consumed'])
        self.assertEqual(derived['operational_exclusion_path'], m.EXPORTSET)
        self.assertEqual(len(report['successor_requirements']), 4)
        self.assertFalse(m.lexists(m.DERIVED))

    def test_terminal_execution_never_validates_publishes_or_executes(self):
        m = load_packet()
        before = m.ORIGINAL.read_bytes()
        with mock.patch.object(m, 'validate_inputs') as validate, \
             mock.patch.object(m, 'publish') as publish, \
             mock.patch.object(m.os, 'execv') as execute, contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(m.main(['--release-commit', 'a' * 40, '--execute']), 2)
        validate.assert_not_called(); publish.assert_not_called(); execute.assert_not_called()
        self.assertEqual(m.ORIGINAL.read_bytes(), before)


class Packet(unittest.TestCase):
    """Synthetic fault injection, isolated from production artifact admission."""
    def setUp(self):
        global m, REAL_GIT_BLOB
        m = load_packet()
        # Exercise historical publication mechanics only in synthetic fixtures;
        # the production packet is irreversibly non-releasable in source.
        m.TERMINAL_NON_RELEASABLE = False
        self.downstream = mock.patch.object(m, 'validate_downstream', return_value={})
        self.downstream.start(); self.addCleanup(self.downstream.stop)
        REAL_GIT_BLOB = m.git_blob
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        out, evidence = root / 'out', root / 'evidence'; out.mkdir(); evidence.mkdir()
        for key, value in {'ORIGINAL': root/'original', 'LOG': root/'log', 'TERMINAL': root/'terminal', 'WRAPPER': root/'wrapper',
                           'CANDIDATE': root/'candidate', 'IHK': root/'ihk', 'OVERLAY': root/'overlay',
                           'OUTPUT': out, 'EVIDENCE': evidence, 'LEASE': root/'lease', 'DERIVED': root/'derived',
                           'EXPORTSET': str(root/'exportset')}.items(): setattr(m, key, value)
        m.CANDIDATE.mkdir(); m.IHK.mkdir(); result = m.IHK/'test/ihklib/whitebox/src/driver/mckernel/syscall.c'; result.parent.mkdir(parents=True); result.write_bytes(b'result'); m.OVERLAY.write_bytes(b'overlay')
        owner = m.CANDIDATE/'scripts/native_rust_exact_build_container_owner.py'; owner.parent.mkdir(parents=True); owner.write_bytes(b'owner')
        driver = m.CANDIDATE/'scripts/native_rust_exact_build_offline.py'; driver.write_bytes(b'driver')
        m.OWNER_SHA256 = m.sha(owner.read_bytes()); m.DRIVER_SHA256 = m.sha(driver.read_bytes())
        manifest = root/'manifest'; manifest.write_bytes(b'manifest'); m.MANIFEST_SHA256 = m.sha(manifest.read_bytes())
        m.LOG.write_bytes(b'fixture'); m.LOG_SHA256 = m.sha(m.LOG.read_bytes())
        receipt = root/'receipt'; receipt.write_bytes(b'receipt'); m.RECEIPT_SHA256 = m.sha(receipt.read_bytes())
        m.TERMINAL.write_text(json.dumps({'returncode': 0, 'log': str(m.LOG), 'log_sha256': m.LOG_SHA256})); m.TERMINAL_SHA256 = m.sha(m.TERMINAL.read_bytes())
        m.WRAPPER.write_bytes(b'fixture'); m.WRAPPER_SHA256 = m.sha(m.WRAPPER.read_bytes())
        m.OVERLAY_SHA256 = m.sha(m.OVERLAY.read_bytes()); m.OVERLAY_RESULT_SHA256 = m.sha(result.read_bytes())
        m.IHK_RESULT = result
        self.request = {'input_manifest': str(manifest), 'input_manifest_sha256': m.MANIFEST_SHA256, 'release_required': True,
                        'operational_exclusion_path': m.EXPORTSET,
                        'operational_exclusion_consumed': False, 'preparation_only': True, 'execution_released': False, 'executable': False,
                        'candidate_sha': m.CANDIDATE_SHA, 'ihk_overlay_base_sha': m.IHK_HEAD, 'ihk_overlay_sha256': m.OVERLAY_SHA256,
                        'image_receipt': str(receipt), 'image_receipt_sha256': m.RECEIPT_SHA256,
                        'limits': dict(m.EXPECTED_LIMITS), 'launcher_aggregate_memory_gib': '16.2158',
                        'timeout': 19800, 'host_floor': 16 * 2 ** 30, 'scratch_floor': 12 * 2 ** 30,
                        'host_measure_root': '/', 'scratch_measure_root': '/home/holden/mckernel-work/scratch',
                        'memory_allocation_roots': [str(m.CANDIDATE), str(m.CANDIDATE.parent / (m.CANDIDATE.name + '-metadata-backup'))],
                        'ihk_overlay_result_blob_sha256': m.OVERLAY_RESULT_SHA256, 'source_root': str(m.CANDIDATE), 'ihk_overlay_path': str(m.OVERLAY),
                        'output_root': str(m.OUTPUT), 'evidence_root': str(m.EVIDENCE), 'lease_path': str(m.LEASE),
                        'owner_path': str(m.CANDIDATE/'scripts/native_rust_exact_build_container_owner.py'), 'owner_path_sha256': m.OWNER_SHA256,
                        'provenance_path': str(m.CANDIDATE/'scripts/native_rust_exact_build_offline.py'), 'provenance_path_sha256': m.DRIVER_SHA256,
                        'driver_path': str(m.CANDIDATE/'scripts/native_rust_exact_build_offline.py'), 'driver_path_sha256': m.DRIVER_SHA256}
        m.ORIGINAL.write_bytes(json.dumps(self.request, separators=(',', ':')).encode()); m.ORIGINAL_SHA256 = m.sha(m.ORIGINAL.read_bytes())
        m.IHK_RESULT = result
        m.git_blob = lambda commit: None
        m.git_run = lambda args, **kwargs: type('R', (), {'returncode': 0, 'stdout': ((m.IHK_HEAD if str(m.IHK / '.git') in str(args) else m.CANDIDATE_SHA) + '\n').encode() if 'rev-parse' in str(args) else b''})()

    def test_derive_changes_exactly_three_values(self):
        derived = m.derive(self.request)
        changed = {key for key in self.request if derived[key] != self.request[key]}
        self.assertEqual(changed, {'preparation_only', 'execution_released', 'executable'})
        self.assertEqual(set(derived), set(self.request)); self.assertTrue(derived['release_required'])

    def test_validate_rejects_existing_destination_and_symlink(self):
        self.assertEqual(m.validate_inputs('a' * 40)['candidate_sha'], m.CANDIDATE_SHA)
        m.DERIVED.touch()
        with self.assertRaisesRegex(m.Refusal, 'destination-present'): m.validate_inputs('a' * 40)
        m.DERIVED.unlink(); m.OUTPUT.rmdir(); m.OUTPUT.symlink_to(m.EVIDENCE, target_is_directory=True)
        with self.assertRaisesRegex(m.Refusal, 'directory-binding'): m.validate_inputs('a' * 40)

    def test_validate_rejects_current_source_hash_mutation(self):
        m.WRAPPER.write_bytes(b'tampered-wrapper')
        with self.assertRaisesRegex(m.Refusal, 'artifact-binding'):
            m.validate_inputs('a' * 40)

    def test_validate_rejects_candidate_head_mutation(self):
        real = m.git_run
        def wrong_head(args, **kwargs):
            result = real(args, **kwargs)
            if 'rev-parse' in args and str(m.CANDIDATE / '.git') in str(args):
                result.stdout = b'0' * 40 + b'\n'
            return result
        with mock.patch.object(m, 'git_run', side_effect=wrong_head):
            with self.assertRaisesRegex(m.Refusal, 'candidate-head'):
                m.validate_inputs('a' * 40)

    def test_validate_rejects_resource_reconciliation_mutation(self):
        request = dict(self.request, limits=dict(m.EXPECTED_LIMITS, PidsLimit=513))
        m.ORIGINAL.write_bytes(json.dumps(request, separators=(',', ':')).encode())
        m.ORIGINAL_SHA256 = m.sha(m.ORIGINAL.read_bytes())
        with self.assertRaisesRegex(m.Refusal, 'resource-limits-binding'):
            m.validate_inputs('a' * 40)

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

    def test_zero_write_retains_partial_request_and_never_executes(self):
        real_write = m.os.write
        calls = 0
        def partial_then_zero(fd, data):
            nonlocal calls
            calls += 1
            return real_write(fd, data[:7]) if calls == 1 else 0
        with mock.patch.object(m.os, 'write', side_effect=partial_then_zero), \
             mock.patch.object(m.os, 'execv') as execv:
            with self.assertRaisesRegex(m.Refusal, 'short-publish'):
                m.main(['--release-commit', 'a' * 40, '--execute'])
        execv.assert_not_called()
        self.assertEqual(m.DERIVED.read_bytes(), m.payload(m.derive(self.request))[:7])
        with self.assertRaisesRegex(m.Refusal, 'destination-present'):
            m.validate_inputs('a' * 40)

    def test_file_fsync_failure_retains_request_and_never_executes(self):
        with mock.patch.object(m.os, 'fsync', side_effect=OSError('file-fsync-failure')), \
             mock.patch.object(m.os, 'execv') as execv:
            with self.assertRaisesRegex(OSError, 'file-fsync-failure'):
                m.main(['--release-commit', 'a' * 40, '--execute'])
        execv.assert_not_called()
        self.assertEqual(m.DERIVED.read_bytes(), m.payload(m.derive(self.request)))
        with self.assertRaisesRegex(m.Refusal, 'destination-present'):
            m.validate_inputs('a' * 40)

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
             mock.patch.object(m, 'validate_downstream', side_effect=lambda r: order.append('downstream')), \
             mock.patch.object(m, 'publish', side_effect=published), \
             mock.patch.object(m.os, 'execv', side_effect=executed) as execv:
            with self.assertRaisesRegex(RuntimeError, 'exec-boundary'):
                m.main(['--release-commit', 'a' * 40, '--execute'])
        self.assertEqual(order[:2], ['downstream', 'publish'])
        self.assertEqual(order[2][0], 'exec')
        execv.assert_called_once()

    def test_real_wrapper_admission_precedes_derived_publication(self):
        wrapper_spec = importlib.util.spec_from_file_location(
            'scratch17_wrapper', ROOT/'scripts/native_rust_exact_disk_build_wrapper.py')
        w = importlib.util.module_from_spec(wrapper_spec)
        wrapper_spec.loader.exec_module(w)
        active = Path(self.tmp.name)/'scratch17-exclusion'
        w.OPERATIONAL_EXCLUSION_PATH = str(active)
        request = dict(self.request, operational_exclusion_path=str(active),
                       operational_exclusion_consumed=False,
                       memory_allocation_roots=[str(m.CANDIDATE)],
                       limits=dict(w.EXPECTED_LIMITS),
                       host_floor=16 * 2**30, scratch_floor=12 * 2**30)
        measurement = {
            'memory_allocation_memory_backed_bytes': 0,
            'memory_allocation_roots': [{'filesystem': 'ext4', 'memory_effect_bytes': 0,
                                         'allocated_bytes': 1}],
            'memory_allocation_total_bytes': 1, 'memory_allocation_tmpfs_bytes': 0,
            'candidate_memory_effect': {'classification': 'none', 'bytes': 0},
            'aggregate_memory_required': w.EXPECTED_LIMITS['Memory']}
        class Signals:
            def __enter__(self): return self
            def __exit__(self, *args): return False
        class Build:
            def __init__(self, req, signals=None): self.measurement = measurement
            def validate(self): return None
            def run(self):
                return {'status': 'PASS', 'retired': True,
                        'cleanup_separately_required': False,
                        'terminal_container_info': None,
                        'terminal_container_info_current': True}
        module = types.SimpleNamespace(LIMITS=dict(w.EXPECTED_LIMITS),
                                       provenance=types.SimpleNamespace(ENV={}),
                                       CliSignals=Signals, BuildOwner=Build)
        with mock.patch.object(w, 'HEAVY_ENTRY_CONTRACT_RELEASED', True), \
             mock.patch.object(w, 'SHARED_HEAVY_LOCK_PATH', str(active.parent / 'shared.lock')), \
             mock.patch.object(w, '_dispatcher_reconcile', return_value={}), \
             mock.patch.object(w, '_load_owner', return_value=module):
            result = w.run_request(request)
        self.assertEqual(result['status'], 'PASS')
        self.assertFalse(active.exists())
        self.assertFalse(m.lexists(m.DERIVED))

    def test_downstream_failure_is_before_publication(self):
        with mock.patch.object(m, 'validate_inputs', return_value=self.request), \
             mock.patch.object(m, 'validate_downstream', side_effect=ValueError('downstream incompatibility')), \
             mock.patch.object(m, 'publish') as publish, mock.patch.object(m.os, 'execv') as execute:
            with self.assertRaisesRegex(ValueError, 'downstream incompatibility'):
                m.main(['--release-commit', 'a' * 40, '--execute'])
        publish.assert_not_called(); execute.assert_not_called()

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
