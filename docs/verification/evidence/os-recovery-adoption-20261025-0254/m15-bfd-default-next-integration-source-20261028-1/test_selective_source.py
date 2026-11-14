"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing."""
from pathlib import Path
import hashlib
import importlib.util
import json
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('selective', HERE / 'check_selective_source.py')
s = importlib.util.module_from_spec(spec)
spec.loader.exec_module(s)
PLAN = json.loads((HERE / 'INTEGRATION.json').read_text())
BASE = Path(PLAN['canonical_preimage']['path']).read_bytes()


class SelectiveSource(unittest.TestCase):
    def test_real_current_source(self):
        self.assertEqual(s.check()['production_paths'], 4)

    def test_exact_accepted_result(self):
        self.assertEqual(s.transform(BASE, PLAN['sites']), (HERE / 'candidate/executer/user/CMakeLists.txt').read_bytes())

    def test_missing_site_rejected(self):
        for site in PLAN['sites']:
            with self.subTest(site=site['before']):
                altered = BASE.replace(site['before'].encode(), b'changed-selector', 1)
                with self.assertRaises(ValueError):
                    s.transform(altered, PLAN['sites'])

    def test_duplicate_site_rejected(self):
        for site in PLAN['sites']:
            with self.subTest(site=site['before']):
                with self.assertRaises(ValueError):
                    s.transform(BASE + b'\n' + site['before'].encode(), PLAN['sites'])

    def test_unrelated_current_bytes_preserved(self):
        marker = b'\n# unrelated downstream selector\n'
        self.assertEqual(s.transform(BASE + marker, PLAN['sites']), s.transform(BASE, PLAN['sites']) + marker)

    def test_same_size_byte_change_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            file = Path(tmp) / 'subject'
            file.write_bytes(b'abcd')
            pin = {'bytes': 4, 'sha256': hashlib.sha256(b'abce').hexdigest()}
            with self.assertRaises(ValueError):
                s.checked_bytes(file, pin)

    def test_size_change_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            file = Path(tmp) / 'subject'
            file.write_bytes(b'abcd')
            pin = {'bytes': 3, 'sha256': hashlib.sha256(b'abcd').hexdigest()}
            with self.assertRaises(ValueError):
                s.checked_bytes(file, pin)


if __name__ == '__main__':
    unittest.main(verbosity=2)
