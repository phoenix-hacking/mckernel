"""Ordinary AF_UNIX bind checks and candidate-only preflight regressions."""
import importlib.util
import hashlib
import os
from pathlib import Path
import socket
import unittest
from unittest import mock

from scripts.tests import test_application_native_diagnostic as baseline

ND = baseline.ND
ROOT = Path(__file__).resolve().parents[2] / "scripts/application-tests"
FAILED_ATTEMPT = Path('/home/holden/mckernel-work/scratch/signal-mask-restore-current942-guest-20261017-1/attempt-6fb44f2a0cd64994af43c47bfc7476ab')
NEXT_ATTEMPT = Path('/home/holden/mckernel-work/scratch/ndmsk-2') / ('attempt-' + 'a' * 32)


class QmpPathAdmissionTests(unittest.TestCase):
    def setUp(self):
        self.fixture = baseline.NativeDiagnosticTests('runTest')
        self.fixture.setUp()
        self.addCleanup(self.fixture.tearDown)

    def endpoint(self, size, nonascii=False):
        # Count the complete actual endpoint, including parent and qmp.sock.
        root = self.fixture.root
        padding = size - len(os.fsencode(root)) - len(b'/qmp.sock') - 1
        self.assertGreaterEqual(padding, 2)
        name = ('é' + 'x' * (padding - 2)) if nonascii else 'x' * padding
        attempt = ND.prepare_attempt(self.fixture.manifest, root, name)
        endpoint = attempt / 'qmp.sock'
        self.assertEqual(len(os.fsencode(endpoint)), size)
        return attempt, endpoint

    def check_boundary(self, size, nonascii):
        attempt, endpoint = self.endpoint(size, nonascii)
        if nonascii:
            self.assertLess(len(str(endpoint)), len(os.fsencode(endpoint)))
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
            if size == 107:
                # Kernel admission is an independent oracle for the helper.
                sock.bind(str(endpoint))
                self.assertTrue(endpoint.exists())
            else:
                with self.assertRaises(OSError): sock.bind(str(endpoint))
                self.assertFalse(endpoint.exists())
        if endpoint.exists(): endpoint.unlink()
        for make in (ND.expected_qemu_argv, ND.build_command):
            if size == 107:
                value = make(self.fixture.manifest, attempt)
                argv = value if isinstance(value, list) else value['argv']
                self.assertIn('unix:' + str(endpoint) + ',server=on,wait=off', argv)
                self.assertEqual(argv[argv.index('-monitor') + 1], 'none')
                self.assertEqual(sum(arg.startswith('unix:') for arg in argv), 1)
            else:
                with self.assertRaisesRegex(ND.DiagnosticError, 'AF_UNIX 107-byte limit'):
                    make(self.fixture.manifest, attempt)

    def test_linux_bind_107_ascii_bytes_and_both_command_paths_admit(self):
        self.check_boundary(107, False)

    def test_linux_bind_108_ascii_bytes_and_both_command_paths_reject(self):
        self.check_boundary(108, False)

    def test_linux_bind_107_nonascii_bytes_and_both_command_paths_admit(self):
        self.check_boundary(107, True)

    def test_linux_bind_108_nonascii_bytes_and_both_command_paths_reject(self):
        self.check_boundary(108, True)

    def test_exact_failed_attempt_rejects_and_short_next_parent_admits(self):
        endpoint = FAILED_ATTEMPT / 'qmp.sock'
        self.assertGreater(len(os.fsencode(endpoint)), 107)
        with self.assertRaisesRegex(ND.DiagnosticError, 'AF_UNIX 107-byte limit'):
            ND.expected_qemu_argv(self.fixture.manifest, FAILED_ATTEMPT)
        self.assertLessEqual(len(os.fsencode(NEXT_ATTEMPT / 'qmp.sock')), 107)
        argv = ND.expected_qemu_argv(self.fixture.manifest, NEXT_ATTEMPT)
        self.assertIn('unix:' + str(NEXT_ATTEMPT / 'qmp.sock') + ',server=on,wait=off', argv)
        self.assertEqual(argv[argv.index('-monitor') + 1], 'none')
        # No attempt directory is reserved for this purely derived command.
        self.assertFalse(NEXT_ATTEMPT.exists())

    def test_owner_rejects_before_evidence_lock_or_container_side_effects(self):
        spec = importlib.util.spec_from_file_location('owner_candidate_fixture', ROOT / 'native_diagnostic_container_owner.py')
        owner = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(owner)
        self.assertEqual(Path(owner.__file__).resolve(), ROOT / 'native_diagnostic_container_owner.py')
        diagnostic_path = ROOT / 'native_diagnostic.py'
        self.assertEqual(owner.SOURCE_HASHES[str(diagnostic_path)],
                         hashlib.sha256(diagnostic_path.read_bytes()).hexdigest())
        # Construct the actual owner; only filesystem identity checks use fixtures.
        # The parent's length forces rejection independently of TMPDIR.
        parent = self.fixture.root / ('p' * 64)
        backend = mock.Mock()
        with mock.patch.object(owner, '_manifest_identity', return_value=('/fixture/manifest', 'c' * 64)), \
             mock.patch.object(owner, '_manifest_outside_writable_parent'):
            obj = owner.DiagnosticOwner(str(parent), manifest='/fixture/manifest',
                                        manifest_sha256='c' * 64, backend=backend, nonce='b' * 32)
        self.assertGreater(len(os.fsencode(obj.attempt / 'qmp.sock')), 107)
        with mock.patch.object(owner, 'private_parent', return_value={}), \
             mock.patch.object(owner, 'bound_manifest', return_value=(ND, self.fixture.manifest)), \
             mock.patch.object(owner, '_outer_identity') as identity, \
             mock.patch.object(obj, '_acquire') as acquire, \
             mock.patch.object(obj, '_queue_owner') as queue:
            with self.assertRaisesRegex(ND.DiagnosticError, 'AF_UNIX 107-byte limit'):
                obj.run()
            identity.assert_not_called()
            acquire.assert_not_called()
            queue.assert_not_called()
            self.assertEqual(obj.backend.mock_calls, [])
        self.assertFalse(obj.evidence.exists())
        self.assertFalse(obj.attempt.exists())

    def test_direct_run_rejects_before_process_or_qmp_factories(self):
        attempt, endpoint = self.endpoint(108)
        process, qmp = mock.Mock(), mock.Mock()
        with self.assertRaisesRegex(ND.DiagnosticError, 'AF_UNIX 107-byte limit'):
            ND.run_diagnostic(self.fixture.manifest, attempt, process, qmp)
        process.assert_not_called()
        qmp.assert_not_called()
        self.assertFalse(endpoint.exists())


if __name__ == '__main__':
    unittest.main()
