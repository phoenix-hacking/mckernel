"""Cheap source-only identity checks for the scratch19 successor helper."""
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
PATH = ROOT / 'docs/verification/evidence/native-exact-candidate-delta-preparation-scratch19-20261001.py'
spec = importlib.util.spec_from_file_location('scratch19', PATH)
p = importlib.util.module_from_spec(spec)
spec.loader.exec_module(p)

class Scratch19Identity(unittest.TestCase):
    def test_fetched_target_and_exact_delta(self):
        self.assertEqual(p._IMPL.git(ROOT, 'rev-parse', p.TARGET).decode().strip(), p.TARGET)
        self.assertEqual(p._IMPL.git(ROOT, 'rev-parse', p.TARGET + '^{tree}').decode().strip(), p.TARGET_TREE)
        self.assertEqual(p._IMPL.git(ROOT, 'rev-parse', p.TARGET + '^').decode().strip(), p.BASELINE)
        self.assertEqual(tuple((s, path, p._IMPL.git(ROOT, 'rev-parse', p.TARGET + ':' + path).decode().strip())
                              for s, path in p._IMPL.raw_delta(ROOT, p.BASELINE, p.TARGET, None)), p.EXACT_DELTA)

    def test_fresh_names_and_execution_forbidden(self):
        for value in (p.CANDIDATE_NAME, p.MANIFEST_NAME, p.REQUEST_NAME, p.LOG_NAME,
                      p.TERMINAL_NAME, p.LEASE_NAME, p.EXCLUSION_NAME):
            self.assertIn('scratch-19' if 'scratch19' not in value else 'scratch19', value)
            self.assertNotIn('scratch-18', value)
        with self.assertRaisesRegex(p.Refusal, 'execute is forbidden'):
            p.prepare(execute=True)

    def test_cli_execution_is_fail_closed_and_predecessors_are_bound(self):
        with self.assertRaisesRegex(SystemExit, 'forbids --execute'):
            p.main(['--execute'])
        intermediate = Path('/home/holden/mckernel-work/scratch') / p.INTERMEDIATE_CANDIDATE_NAME
        previous = Path('/home/holden/mckernel-work/scratch') / p.PREVIOUS_CANDIDATE_NAME
        self.assertTrue(intermediate.is_dir())
        self.assertTrue(previous.is_dir())
        self.assertEqual(p._IMPL.git(intermediate, 'rev-parse', 'HEAD').decode().strip(),
                         'ddb8d7d58a9de7063663a27397b9fb9613a6325c')
        self.assertEqual(p._IMPL.git(previous, 'rev-parse', 'HEAD').decode().strip(),
                         '89ab5c555aac9177a789efc67ddc775dacb25d6d')

if __name__ == '__main__':
    unittest.main()
