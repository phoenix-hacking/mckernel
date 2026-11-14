"""Offline HOST controller launch boundary; no subprocesses are started."""
import unittest
from unittest.mock import patch

from scripts.tests.test_os_goal_launcher import launcher


class ContinuousLaunchTests(unittest.TestCase):
    def test_continuous_mode_stops_at_original_m14_m15_acceptance(self):
        args = launcher.arguments(['--continuous'])
        self.assertTrue(args.stop_after_m14_m15)
        self.assertEqual(args.hours, 0)
        self.assertIsNone(args.credit_budget)

    def command(self, cpus, taskset='/usr/bin/taskset', continuous=True):
        args = launcher.arguments(['--continuous'] if continuous else [])
        with patch.object(launcher, 'agent_settings', return_value={}), \
                patch.object(launcher, 'launch_resources', return_value={}), \
                patch.object(launcher, 'resource_environment', return_value={}), \
                patch.object(launcher.os, 'sched_getaffinity', return_value=set(cpus)), \
                patch.object(launcher.shutil, 'which', return_value=taskset):
            return launcher.server_argv(args, launcher.REPO)

    def test_new_controller_and_descendants_are_bound_to_available_host_cpus(self):
        argv = self.command(range(8))
        self.assertEqual(argv[:3], ['/usr/bin/taskset', '--cpu-list', '0,6,7'])
        self.assertEqual(argv[3], 'codex')
        self.assertEqual(argv[-2:], ['app-server', '--stdio'])
        self.assertEqual(self.command([2, 3, 6])[:3],
                         ['/usr/bin/taskset', '--cpu-list', '6'])

    def test_native_only_affinity_and_missing_binding_tool_refuse_new_controller(self):
        for cpus, tool in (([2, 3, 4, 5], '/usr/bin/taskset'), ([0, 6, 7], None)):
            with self.subTest(cpus=cpus, tool=tool), self.assertRaises(RuntimeError):
                self.command(cpus, taskset=tool)

    def test_legacy_noncontinuous_launch_does_not_change_its_affinity(self):
        self.assertEqual(self.command([2, 3], continuous=False)[0], 'codex')
