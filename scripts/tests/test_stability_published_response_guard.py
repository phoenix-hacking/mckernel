#!/usr/bin/env python3
"""Exercise the exact runner overlap guard with an explicit file-writing stub.

No QMP, physical memory, native code, guest or ownership acceptance occurs.
"""
import ast
import hashlib
import json
from pathlib import Path
import tempfile
import time
from types import SimpleNamespace
import unittest

RUNNER_SHA256 = '0946acc6005b12818f3721a3714d5dadab8b599dde51aaff49a798598377e9bc'
CAPTURE = Path(tempfile.mkdtemp(prefix='stability-published-response-guard-tests-'))
RUNNER = Path(__file__).resolve().parents[2] / 'scripts/tests/run_stability_published_guest.py'


class GuardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        raw = RUNNER.read_bytes()
        if hashlib.sha256(raw).hexdigest() != RUNNER_SHA256:
            raise ValueError('exact reviewed runner source required')
        (CAPTURE / 'runner.py').write_bytes(raw)
        (CAPTURE / 'test-source.py').write_bytes(Path(__file__).read_bytes())
        tree = ast.parse(raw)
        run = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'run']
        if len(run) != 1: raise ValueError('exact run definition required')
        functions = [n for n in run[0].body if isinstance(n, ast.FunctionDef) and n.name == 'guarded_dump']
        if len(functions) != 1: raise ValueError('exact guard definition required')
        cls.code = compile(ast.Module(body=functions, type_ignores=[]), str(CAPTURE / 'runner.py'), 'exec')

    def setUp(self):
        self.root = CAPTURE / self._testMethodName
        self.root.mkdir()
        self.calls = []
        self.record = {'physical_reads': []}
        def identity(path):
            data = path.read_bytes()
            return {'path': str(path), 'size': len(data), 'sha256': hashlib.sha256(data).hexdigest()}
        def save():
            (self.root / 'guard-journal.json').write_text(json.dumps(self.record, indent=2) + '\n')
        def backend(address, length, target):
            self.calls.append({'address': address, 'bytes': length, 'target': str(target)})
            data = bytes([0x5a]) * length
            target.write_bytes(data)
            return data
        self.namespace = dict(selected_span=(0x2000, 0x2028), original_read_phase=None,
            control=SimpleNamespace(release_possible=False), record=self.record, save=save,
            original_dump=backend, identity=identity, time=time)
        exec(self.code, self.namespace)
        self.guard = self.namespace['guarded_dump']
        self.target = self.root / 'stub-bytes.bin'

    def deny(self, address=0x2000, length=40, message=None):
        with self.assertRaises(AssertionError) as raised:
            self.guard(address, length, self.target)
        if message is not None: self.assertIn(message, str(raised.exception))
        self.assertEqual(self.calls, [])
        self.assertFalse(self.target.exists())
        row = self.record['physical_reads'][-1]
        self.assertEqual((row['address'], row['bytes']), (address, length))
        self.assertFalse(row['completed'])
        self.assertEqual(row['error_type'], 'AssertionError')
        self.assertGreaterEqual(row['end_ns'], row['begin_ns'])
        return row

    def test_disjoint_before_selection(self):
        self.namespace['selected_span'] = None
        self.assertEqual(self.guard(0x1000, 64, self.target), b'Z' * 64)
        row = self.record['physical_reads'][0]
        self.assertIsNone(row['selected_span']); self.assertFalse(row['original_overlap'])
        self.assertEqual(len(self.calls), 1)

    def test_disjoint_after_possible_release(self):
        self.namespace['control'].release_possible = True
        self.assertEqual(self.guard(0x3000, 64, self.target), b'Z' * 64)
        row = self.record['physical_reads'][0]
        self.assertTrue(row['release_possible']); self.assertFalse(row['original_overlap'])
        self.assertEqual(row['selected_span'], [0x2000, 0x2028])

    def test_exact_blocked_read(self):
        self.namespace['original_read_phase'] = 'BlockedRead'
        self.assertEqual(self.guard(0x2000, 40, self.target), b'Z' * 40)
        row = self.record['physical_reads'][0]
        self.assertTrue(row['original_overlap']); self.assertTrue(row['completed'])
        self.assertFalse(row['release_possible'])
        self.assertEqual(row['artifact']['sha256'], hashlib.sha256(b'Z' * 40).hexdigest())

    def test_exact_accepted_read(self):
        self.namespace['original_read_phase'] = 'AcceptedReturn'
        self.assertEqual(self.guard(0x2000, 40, self.target), b'Z' * 40)
        self.assertEqual(self.record['physical_reads'][0]['allowed_original_phase'], 'AcceptedReturn')

    def test_overlap_without_read_window(self):
        self.assertTrue(self.deny()['original_overlap'])

    def test_partial_overlap_inside_window(self):
        self.namespace['original_read_phase'] = 'BlockedRead'
        row = self.deny(0x1ff8, 16)
        self.assertTrue(row['original_overlap'])

    def test_subspan_inside_window(self):
        self.namespace['original_read_phase'] = 'AcceptedReturn'
        self.assertTrue(self.deny(0x2008, 8)['original_overlap'])

    def test_release_latch_overrides_stale_window(self):
        self.namespace['original_read_phase'] = 'AcceptedReturn'
        self.namespace['control'].release_possible = True
        self.assertTrue(self.deny(message='ownership may have transferred')['release_possible'])

    def test_final_or_emergency_overlap_after_release(self):
        self.namespace['control'].release_possible = True
        row = self.deny()
        self.assertIsNone(row['allowed_original_phase'])
        self.assertTrue(row['release_possible'])

    def test_no_controller_is_not_read_authority(self):
        self.namespace['original_read_phase'] = 'BlockedRead'
        self.namespace['control'] = None
        self.deny(message='ownership may have transferred')

    def test_physical_range_rejected_and_retained(self):
        self.deny(256 << 30, 40)

    def test_negative_address_rejected_and_retained(self):
        self.deny(-1, 40)

    def test_boolean_coordinate_rejected(self):
        row = self.deny(True, 40)
        self.assertIs(row['address'], True)

    def test_oversized_dump_rejected(self):
        self.deny(0x3000, (4 << 20) + 1)

    def test_attempt_cap_preserves_first_rejected_request(self):
        self.record['physical_reads'] = [{'prior_stub_entry': index} for index in range(1024)]
        row = self.deny(0x3000, 40, 'attempt limit')
        self.assertEqual(len(self.record['physical_reads']), 1025)
        self.assertEqual(row['selected_span'], [0x2000, 0x2028])

    def test_backend_failure_preserves_original_exception(self):
        def failure(address, length, target):
            self.calls.append({'address': address, 'bytes': length})
            target.write_bytes(b'partial')
            raise OSError(5, 'original backend failure')
        self.namespace['original_dump'] = failure
        with self.assertRaisesRegex(OSError, 'original backend failure'):
            self.guard(0x3000, 40, self.target)
        row = self.record['physical_reads'][-1]
        self.assertFalse(row['completed']); self.assertEqual(row['error_type'], 'OSError')
        self.assertIn('original backend failure', row['error'])
        self.assertEqual(self.target.read_bytes(), b'partial')
        self.assertEqual(len(self.calls), 1)

    def tearDown(self):
        (self.root / 'stub-calls.json').write_text(json.dumps(self.calls, indent=2) + '\n')


if __name__ == '__main__':
    print('RETAINED ' + str(CAPTURE), flush=True)
    unittest.main()
