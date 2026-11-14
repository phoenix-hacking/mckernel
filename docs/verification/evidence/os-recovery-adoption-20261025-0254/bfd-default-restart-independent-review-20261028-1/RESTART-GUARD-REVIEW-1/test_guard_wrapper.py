"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Pure wrapper regression: static frozen sources are read, all live effects substituted.
"""
from pathlib import Path
import importlib.util
import sys
import unittest
from unittest.mock import patch

E = Path(__file__).resolve().parents[2]
D = E / 'restart-operation-guard-source-20261028-1'
sys.path.insert(0, str(D))
import guardian_guard as g
import test_guardian_guard as fixture


class PureWrapper(unittest.TestCase):
    def test_actual_guard_wrapper_with_only_effects_substituted(self):
        f = fixture.GuardTests()
        f.setUp()
        records = {
            g.CONTROL / 'armed-controller/journal.json': f.args[1],
            g.CONTROL / 'armed-controller/bridge-start.json': f.args[2],
            g.CAMPAIGN / 'state.json': f.args[3],
            g.CAMPAIGN / 'watcher.json': f.args[4],
        }
        original_text = Path.read_text
        original_exists = Path.exists
        stop_paths = {
            g.CONTROL / 'USER-STOP.json',
            g.CONTROL / 'armed-controller/USER-STOP.json',
            g.BASE / 'armed-controller/USER-STOP.json',
            g.BASE / 'new-guardian-binding-preparation-1/USER-STOP.json',
        }
        def text(path, *args, **kwargs):
            if str(path) == '/proc/sys/kernel/random/boot_id':
                return g.BOOT_ID
            return original_text(path, *args, **kwargs)
        def exists(path):
            return False if path in stop_paths else original_exists(path)
        with patch.object(g, 'read', side_effect=lambda path: records[path]), \
             patch.object(g, 'birth', side_effect=f.procs.get), \
             patch.object(g.time, 'time', return_value=f.args[6][0]), \
             patch.object(g.time, 'monotonic', return_value=f.args[6][1]), \
             patch.object(g.time, 'clock_gettime', return_value=f.args[6][2]), \
             patch.object(Path, 'read_text', text), \
             patch.object(Path, 'exists', exists):
            self.assertEqual(g.guard(), f.args[6])


if __name__ == '__main__':
    unittest.main(verbosity=2)
