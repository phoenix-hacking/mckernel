#!/usr/bin/env python3
"""Source-only, unexecuted tests; fresh reviewed profile/share required.
Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
No compilers, guests, production objects or native operations.
"""
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('prepare', HERE / 'prepare.py')
prepare = importlib.util.module_from_spec(spec)
spec.loader.exec_module(prepare)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def normalize(contract):
    value = json.loads(json.dumps(contract))
    for key in ('rust_witness', 'witness_only_entry_patch'):
        value['outputs'][key]['path'] = '<private-output>/' + Path(value['outputs'][key]['path']).name
    return value


class Reproducibility(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='perf-witness-provenance-')
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def test_two_generations_match_corrected_witness_and_contract(self):
        one, two = self.root / 'one', self.root / 'two'
        first = prepare.generate(one)
        second = prepare.generate(two)
        template = json.loads(prepare.TEMPLATE.read_text())
        self.assertEqual(digest(prepare.TEMPLATE), prepare.TEMPLATE_SHA)
        for filename, expected in (('f03_perf_entry_abi_witness.rs', prepare.EXPECTED_WITNESS),
                                   ('RUST-WITNESS-ONLY.PRIVATE.patch', prepare.EXPECTED_PATCH)):
            self.assertEqual((one / filename).read_bytes(), (two / filename).read_bytes())
            self.assertEqual(digest(one / filename), expected)
            self.assertEqual((one / filename).read_bytes(), (prepare.PREDECESSOR / filename).read_bytes())
        self.assertEqual(normalize(first), normalize(second))
        self.assertEqual(first, json.loads((one / 'TARGET-CONTRACT.json').read_text()))
        self.assertEqual(first['fields'], template['fields'])
        self.assertEqual(first['callbacks'], template['callbacks'])
        self.assertEqual(first['required_independent_checks'], template['required_independent_checks'])
        self.assertEqual(first['selection'], template['selection'])
        self.assertEqual(first['structure'], template['structure'])
        self.assertEqual(first['fields'][11]['rust_witness_expression'], '(super::super::IHK_MC_AP_NOWAIT) as CULong')
        self.assertEqual(len(first['fields']), 31)
        self.assertEqual(len(first['callbacks']), 13)
        self.assertEqual(first['outputs']['generator']['sha256'], digest(HERE / 'prepare.py'))
        self.assertEqual(first['outputs']['comparator']['sha256'], digest(HERE / 'compare_elf.py'))
        self.assertEqual(first['provenance']['corrected_contract']['sha256'], prepare.TEMPLATE_SHA)
        self.assertFalse(first['compiler_or_native_run'])
        self.assertIsNone(first['authority'])

    def test_wrong_template_and_comparator_hash_fail_before_output(self):
        bad = self.root / 'wrong'; bad.write_bytes(b'wrong')
        output = self.root / 'not-created'
        with mock.patch.object(prepare, 'TEMPLATE', bad):
            with self.assertRaisesRegex(ValueError, 'input hash mismatch'):
                prepare.generate(output)
        self.assertFalse(output.exists())
        with mock.patch.object(prepare, 'COMPARATOR', bad):
            with self.assertRaisesRegex(ValueError, 'input hash mismatch'):
                prepare.generate(output)
        self.assertFalse(output.exists())

    def test_wrong_bound_source_fails_before_output(self):
        bad = self.root / 'bad-source'; bad.write_bytes(b'wrong')
        source_map = dict(prepare.SOURCES)
        expected = next(iter(source_map.values()))
        source_map.pop(next(iter(source_map)))
        source_map[bad] = expected
        output = self.root / 'not-created'
        with mock.patch.object(prepare, 'SOURCES', source_map):
            with self.assertRaisesRegex(ValueError, 'input hash mismatch'):
                prepare.generate(output)
        self.assertFalse(output.exists())

    def test_existing_output_is_never_overwritten(self):
        output = self.root / 'existing'; output.mkdir()
        sentinel = output / 'TARGET-CONTRACT.json'; sentinel.write_bytes(b'preserve')
        with self.assertRaisesRegex(ValueError, 'new absolute directory'):
            prepare.generate(output)
        self.assertEqual(sentinel.read_bytes(), b'preserve')
        self.assertEqual(sorted(p.name for p in output.iterdir()), ['TARGET-CONTRACT.json'])

    def test_contract_callback_or_expression_drift_is_rejected(self):
        template = json.loads(prepare.TEMPLATE.read_text())
        source = next(iter(prepare.SOURCES)).read_bytes()
        template['fields'][11]['rust_witness_expression'] = 'wrong'
        with self.assertRaisesRegex(ValueError, 'scalar provenance mismatch'):
            prepare.make_witness(source, template)
        template = json.loads(prepare.TEMPLATE.read_text())
        template['callbacks'][3]['rust_binding_expression'] = 'Some(wrong)'
        with self.assertRaisesRegex(ValueError, 'callback provenance mismatch'):
            prepare.make_witness(source, template)


if __name__ == '__main__':
    unittest.main()
