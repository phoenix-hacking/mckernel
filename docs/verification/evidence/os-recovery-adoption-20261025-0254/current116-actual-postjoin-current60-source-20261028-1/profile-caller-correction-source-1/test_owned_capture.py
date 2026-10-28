"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

SOURCE = Path(__file__).with_name('owned_capture.py')
spec = importlib.util.spec_from_file_location('profile_correction', SOURCE)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class CaptureTests(unittest.TestCase):
    def test_real_child_affinity_and_join(self):
        with tempfile.TemporaryDirectory() as directory:
            prefix = Path(directory) / 'capture'
            argv = [module.PYTHON, '-I', '-B', '-c',
                    'import os,time; print(sorted(os.sched_getaffinity(0)),flush=True); time.sleep(.05)']
            result = module.capture(argv, prefix, 5)
            self.assertEqual(result['actual_affinity'], [0])
            self.assertEqual(result['returncode'], 0)
            self.assertTrue(result['positive_direct_wait4_join'])
            self.assertTrue(result['streams_closed'])
            self.assertTrue(result['process_group_absent'])
            self.assertEqual(Path(str(prefix) + '.stdout').read_text(), '[0]\n')
            self.assertEqual(json.loads(Path(str(prefix) + '.STARTED.json').read_text())['birth'], result['birth'])
            with self.assertRaises(FileExistsError):
                module.capture(argv, prefix, 5)

    def test_failed_child_retains_return_and_error(self):
        with tempfile.TemporaryDirectory() as directory:
            prefix = Path(directory) / 'capture'
            argv = [module.PYTHON, '-I', '-B', '-c',
                    'import sys,time; time.sleep(.05); print("fixture-error",file=sys.stderr); sys.exit(7)']
            result = module.capture(argv, prefix, 5)
            self.assertEqual(result['returncode'], 7)
            self.assertTrue(result['positive_direct_wait4_join'])
            self.assertTrue(result['process_group_absent'])
            self.assertEqual(Path(str(prefix) + '.stderr').read_text(), 'fixture-error\n')


if __name__ == '__main__':
    unittest.main()
