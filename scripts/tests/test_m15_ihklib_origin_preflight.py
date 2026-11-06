"""Pure source-location checks; no compiler, library body or device is executed."""
from pathlib import Path
import hashlib
import importlib.util
import os
import re
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(os.environ.get('M15_REPO', Path(__file__).resolve().parents[2]))
WHOLE70 = ROOT / 'ihk/linux/user/rust/whole70'
PRODUCER = Path(os.environ.get('M15_ORIGIN_PREFLIGHT_PRODUCER',
                              WHOLE70 / 'build_whole70_qualified.py'))
STALE = Path(__file__).resolve().parent / 'fixtures/m15_origin_witness_stale.c'
STALE_SHA = 'ba54b173d3e2efec723e8e6b6dec505a97070e1944b8fd03dd1a12a7a9e565c6'
WITNESS = 'diagnostic_origins.selected_target_C_witness.c'


class M15IhklibOriginPreflightTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Importing the producer does not run its main/build entrypoint.
        spec = importlib.util.spec_from_file_location('m15_origin_producer', PRODUCER)
        cls.producer = importlib.util.module_from_spec(spec)
        with patch.object(sys, 'path', [str(WHOLE70)] + sys.path):
            spec.loader.exec_module(cls.producer)
        cls.original = (WHOLE70.parent.parent / 'ihklib.c').read_bytes()
        cls.current = (WHOLE70 / 'abi' / WITNESS).read_bytes()

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix='m15-origin-source-')
        self.addCleanup(self.directory.cleanup)
        self.source = Path(self.directory.name) / 'user/rust/whole70'
        (self.source / 'abi').mkdir(parents=True)
        self.c = self.source.parent.parent / 'ihklib.c'
        self.witness = self.source / 'abi' / WITNESS
        self.c.write_bytes(self.original)
        self.witness.write_bytes(self.current)

    def validate(self):
        return self.producer.validate_diagnostic_origins(self.source)

    def test_current_nineteen_physical_macro_sites(self):
        receipt = self.validate()
        self.assertEqual(receipt['original_C_sha256'], hashlib.sha256(self.original).hexdigest())
        self.assertEqual(receipt['witness_sha256'], hashlib.sha256(self.current).hexdigest())
        self.assertEqual(len(receipt['rows']), 19)
        self.assertEqual([row['origin'] for row in receipt['rows']], list(range(19)))
        for row in receipt['rows']:
            offset = row['line_macro_byte_offset']
            self.assertEqual(self.original[offset:offset + 8], b'__LINE__')
            self.assertEqual(row['line'], self.original[:offset].count(b'\n') + 1)
            self.assertEqual(row['logical_file'], '/src/ihk/linux/user/ihklib.c')

    def test_retained_old_witness_rejects_all_nineteen(self):
        stale = STALE.read_bytes()
        self.assertEqual(hashlib.sha256(stale).hexdigest(), STALE_SHA)
        self.witness.write_bytes(stale)
        with self.assertRaisesRegex(ValueError, r'source-line mismatch \(19\)') as failure:
            self.validate()
        self.assertEqual(re.findall(r'origin([0-9]+): expected', str(failure.exception)),
                         [str(i) for i in range(19)])

    def test_stale_main_stops_before_output_and_any_compiler(self):
        self.witness.write_bytes(STALE.read_bytes())
        output = Path(self.directory.name) / 'must-not-be-created'
        argv = ['producer', '--cc', '/must-not-execute/cc', '--rustc', '/must-not-execute/rustc',
                '--source-dir', str(self.source), '--include-dir', str(self.source),
                '--out-dir', str(output)]
        with patch.object(sys, 'argv', argv), patch.object(self.producer.subprocess, 'run') as run:
            with self.assertRaisesRegex(ValueError, r'source-line mismatch \(19\)'):
                self.producer.main()
            run.assert_not_called()
        self.assertFalse(output.exists())

    def test_missing_or_ambiguous_selected_sites(self):
        text = self.original.decode()
        literal = re.search(r'"%s:%d: ihk_reserve_cpu failed with %d\\n"\s*,\s*'
                            r'__FILE__\s*,\s*__LINE__\s*,\s*ret\b', text).group(0)
        self.assertEqual(text.count(literal), 1)
        for label, changed, error in (
            ('missing-operation', text.replace(literal, literal.replace('ihk_reserve_cpu', 'other')),
             'one diagnostic operation site'),
            ('duplicate-operation', text.replace(literal, literal + '); printf(' + literal),
             'one diagnostic operation site'),
            ('missing-function', text.replace('int _ihk_reserve_cpu_str(', 'int renamed_reserve_cpu_str('),
             'one diagnostic function definition'),
            ('duplicate-function', text + '\nint _ihk_reserve_cpu_str(void) {\n}\n',
             'one diagnostic function definition'),
        ):
            with self.subTest(label=label):
                self.c.write_text(changed)
                with self.assertRaisesRegex(ValueError, error):
                    self.validate()

    def test_unsupported_c_line_controls(self):
        for control in ('#line 700 "other"', '# 700 "other"', '#/**/line 700 "other"',
                        '#li\\\nne 700 "other"', '/* prefix */ #line 700 "other"',
                        '#\\\n 700 "other"'):
            with self.subTest(control=control):
                self.c.write_bytes(control.encode() + b'\n' + self.original)
                with self.assertRaisesRegex(ValueError, 'unsupported C source #line'):
                    self.validate()

    def test_wrong_missing_duplicate_or_unsupported_witness_rows(self):
        text = self.current.decode()
        first = re.search(r'^#line [^\n]+\nstatic const struct origin origin0[^\n]+\n',
                          text, re.MULTILINE).group(0)
        for label, changed in (
            ('wrong-id', text.replace('origin0 =', 'origin00 =', 1)),
            ('wrong-operation', text.replace('"ihk_reserve_cpu"', '"other"', 1)),
            ('wrong-logical-path', text.replace('/src/ihk/linux/user/ihklib.c', '/other', 1)),
            ('missing-row', text.replace(first, '', 1)),
            ('duplicate-row', text.replace(first, first + first, 1)),
            ('extra-control', text + '\n#line 7 "extra"\n'),
            ('unsupported-control', text + '\n# 7 "extra"\n'),
            ('comment-control', text + '\n#/**/line 7 "extra"\n'),
            ('spliced-control', text + '\n#li\\\nne 7 "extra"\n'),
            ('wrong-main-reset', text.replace('#line 1 "metadata-witness-main"',
                                             '#line 2 "metadata-witness-main"')),
        ):
            with self.subTest(label=label):
                self.witness.write_text(changed)
                with self.assertRaises(ValueError):
                    self.validate()


if __name__ == '__main__':
    unittest.main()
