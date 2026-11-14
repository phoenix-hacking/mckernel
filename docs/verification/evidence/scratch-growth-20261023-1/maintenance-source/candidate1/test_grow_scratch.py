"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

Pure mocks: no root, loop, filesystem, Docker, guest or ownership mutation.
"""
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('growth', Path(__file__).with_name('grow_scratch.py'))
g = importlib.util.module_from_spec(spec)
spec.loader.exec_module(g)


class GrowthTests(unittest.TestCase):
    def run_case(self, fail_observation=None, fail_command=None, output='', last_device='/dev/loop36',
                 capacity_fail=None, changed_features=False):
        commands, observations, capacities = [], [], []
        def run(argv, timeout=20):
            commands.append(argv)
            if len(commands) == fail_command:
                raise g.Stop('mock command failure')
            return output if len(commands) == 3 else '', ''
        def observe(sizes):
            observations.append(sizes)
            if len(observations) == fail_observation:
                raise g.Stop('mock snapshot failure')
            return dict(device=last_device if len(observations) == 4 else '/dev/loop36', devnum=1828,
                        allocated=102264397824,
                        header={'Filesystem features': 'changed' if changed_features and len(observations) == 4 else 'unchanged'})
        def capacity(allocated):
            capacities.append(allocated)
            if len(capacities) == capacity_fail:
                raise g.Stop('mock capacity failure')
        try:
            g.execute_steps(run, observe, capacity)
            error = None
        except g.Stop as exc:
            error = exc
        return commands, observations, capacities, error

    def test_success_exact_order_and_geometry(self):
        commands, observations, capacities, error = self.run_case()
        self.assertIsNone(error)
        self.assertEqual(commands, [
            ['/usr/bin/truncate', '--size=152471339008', '--', str(g.BACKING)],
            ['/usr/sbin/losetup', '--set-capacity', '/dev/loop36'],
            ['/usr/sbin/resize2fs', '/dev/loop36', '37224448']])
        self.assertEqual(observations, [(g.OLD, g.OLD, 28835840), (g.TARGET, g.OLD, 28835840),
                                        (g.TARGET, g.TARGET, 28835840), (g.TARGET, g.TARGET, 37224448)])
        self.assertEqual(len(capacities), 2)

    def test_each_snapshot_failure_stops_successors(self):
        for observation in range(1, 5):
            with self.subTest(observation=observation):
                commands, _, _, error = self.run_case(fail_observation=observation)
                self.assertIsNotNone(error)
                self.assertEqual(len(commands), observation - 1)

    def test_each_command_failure_stops_successors(self):
        for command in range(1, 4):
            with self.subTest(command=command):
                commands, observations, _, error = self.run_case(fail_command=command)
                self.assertIsNotNone(error)
                self.assertEqual(len(commands), command)
                self.assertEqual(len(observations), command)

    def test_initial_capacity_failure_prevents_truncate(self):
        commands, _, _, error = self.run_case(capacity_fail=1)
        self.assertEqual(commands, [])
        self.assertIsNotNone(error)

    def test_final_capacity_failure_is_not_success(self):
        self.assertIsNotNone(self.run_case(capacity_fail=2)[3])

    def test_fallback_indication_fails(self):
        for output in ('falling back to old-style resize', 'fallback', 'ERROR', 'resize failed'):
            with self.subTest(output=output):
                commands, observations, _, error = self.run_case(output=output)
                self.assertEqual(len(commands), 3)
                self.assertEqual(len(observations), 3)
                self.assertIsNotNone(error)

    def test_final_loop_change_fails(self):
        self.assertIsNotNone(self.run_case(last_device='/dev/loop37')[3])

    def test_feature_change_fails(self):
        self.assertIsNotNone(self.run_case(changed_features=True)[3])

    def test_header_duplicate_refused(self):
        with self.assertRaises(g.Stop):
            g.parse_header('Block count: 1\nBlock count: 2\n')

    def test_bound_json_duplicates_refused(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'input.json'
            raw = b'{"status":1,"status":2}'
            path.write_bytes(raw)
            with self.assertRaises(g.Stop):
                g.load_bound(path, g.digest(raw))

    def test_host_budget_counts_entire_sparse_gap(self):
        from types import SimpleNamespace
        allocated = 102264397824
        needed = 16 * 2**30 + (g.TARGET - allocated) + 2**30
        def values(path):
            return SimpleNamespace(f_bavail=needed - 1 if path == g.BACKING.parent else 12 * 2**30, f_frsize=1)
        with patch.object(g.os, 'statvfs', side_effect=values):
            with self.assertRaises(g.Stop):
                g.capacity(allocated, 2**30, 0)
        with patch.object(g.os, 'statvfs', return_value=SimpleNamespace(f_bavail=needed, f_frsize=1)):
            g.capacity(allocated, 2**30, 0)

    def test_missing_budget_refused(self):
        with self.assertRaises(g.Stop):
            g.capacity(102264397824, 0, 0)

    def test_capture_timeout_retains_child_and_lock(self):
        class TimedOutChild:
            pid = 123456
            def wait(self, timeout):
                raise g.subprocess.TimeoutExpired('mock', timeout)
        with tempfile.TemporaryDirectory() as temporary:
            with patch.object(g.subprocess, 'Popen', return_value=TimedOutChild()) as launch:
                with patch.object(g, 'starttime', return_value='1234'):
                    with self.assertRaises(g.Stop):
                        g.Runner(Path(temporary), 41)(['/mock/command'])
            self.assertEqual(launch.call_args.kwargs['pass_fds'], (41,))
            self.assertTrue((Path(temporary) / '001.uncertain.json').exists())
            self.assertFalse((Path(temporary) / '001.terminal.json').exists())

    def test_capture_nonzero_is_failure(self):
        class FailedChild:
            pid = 123456
            def wait(self, timeout):
                return 1
        with tempfile.TemporaryDirectory() as temporary:
            with patch.object(g.subprocess, 'Popen', return_value=FailedChild()):
                with patch.object(g, 'starttime', return_value='1234'):
                    with self.assertRaises(g.Stop):
                        g.Runner(Path(temporary), 41)(['/mock/command'])
            self.assertTrue((Path(temporary) / '001.terminal.json').exists())


if __name__ == '__main__':
    unittest.main(verbosity=2)
