"""Offline resource policy tests; no launcher, inference, build or guest runs."""

import importlib.util
import json
import os
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch


SOURCE = Path(__file__).resolve().parents[1] / "os_goal_resources.py"
SPEC = importlib.util.spec_from_file_location("os_goal_resources", SOURCE)
resources = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(resources)
GIB = 1024 ** 3
REPO = SOURCE.parents[1]


class ResourceTests(unittest.TestCase):
    def host(self, cpus=(2, 4, 6, 8, 10, 12, 14, 16), memory=64,
             host_free=64 * GIB, scratch_free=32 * GIB, mounted=True):
        """Mock OS observations, keeping the actual resolver and policy intact."""
        def disk_usage(path):
            self.assertIn(Path(path), (REPO, resources.SCRATCH))
            return SimpleNamespace(free=scratch_free if Path(path) == resources.SCRATCH else host_free)

        def start(target, **kwargs):
            patcher = patch(target, **kwargs)
            result = patcher.start()
            self.addCleanup(patcher.stop)
            return result

        self.affinity = start("os.sched_getaffinity", return_value=set(cpus))
        self.set_affinity = start("os.sched_setaffinity", side_effect=AssertionError("affinity mutation"))
        self.meminfo = start("pathlib.Path.read_text", return_value=(
            "MemTotal:       999999999 kB\nMemFree: 1 kB\n"
            "MemAvailable:   {} kB\nSwapFree: 999999999 kB\n".format(int(memory * 1024 ** 2))))
        self.mount = start("os.path.ismount", return_value=mounted)
        self.disk = start("shutil.disk_usage", side_effect=disk_usage)

    def test_aggressive_roomy_affinity_ceiling_and_json(self):
        self.host()
        result = resources.resolve_resources(repo=REPO)
        self.assertEqual((result["profile"], result["max_agents"], result["build_jobs"],
                          result["memory_gib"]), ("aggressive", 8, 8, 24))
        self.assertEqual(result["cpu_affinity"], [2, 4, 6, 8, 10, 12, 14, 16])
        self.assertEqual(result["cpu_count"], 8)
        self.assertEqual(result["available_memory_gib"], 64)
        self.assertEqual((result["memory_reserve_gib"], result["agent_memory_gib"]), (4, 2))
        self.assertEqual((result["max_depth"], result["heavy_jobs"]), (1, 1))
        self.assertEqual(json.loads(json.dumps(result, allow_nan=False)), result)
        self.assertIsNone(resources.check_resources(result))
        self.affinity.assert_called_once_with(0)
        self.set_affinity.assert_not_called()
        self.assertEqual(result["host_disk"], {"path": str(REPO), "free_gib": 64, "min_free_gib": 16})
        self.assertEqual(result["scratch_disk"], {"path": str(resources.SCRATCH), "mounted": True,
                                                   "free_gib": 32, "min_free_gib": 12})

    def test_defaults_follow_cpu_and_available_memory(self):
        for cpus, memory, expected in (([7], 64, (2, 1, 24)),
                                      ([2, 9], 64, (4, 2, 24)),
                                      ([2, 9], 12, (4, 2, 8)),
                                      ([2, 9], 11.5, (3, 2, 7.5)),
                                      ([2, 9], 7, (1, 2, 3)),
                                      (range(7), 64, (8, 7, 24)),
                                      (range(32), 10, (3, 32, 6)),
                                      (range(32), 64, (8, 32, 24)),
                                      ([7], 4.5, (1, 1, 0.5))):
            with self.subTest(cpus=cpus, memory=memory):
                self.host(cpus=cpus, memory=memory)
                result = resources.resolve_resources()
                self.assertEqual(tuple(result[k] for k in ("max_agents", "build_jobs", "memory_gib")), expected)
                self.assertIsNone(resources.check_resources(result))

    def test_balanced_caps_and_constrained_host(self):
        for cpus, memory, expected in ((range(32), 64, (3, 4, 12)),
                                      ([2, 9], 64, (2, 2, 12)),
                                      ([7], 7, (1, 1, 3))):
            with self.subTest(cpus=cpus):
                self.host(cpus=cpus, memory=memory)
                result = resources.resolve_resources("balanced")
                self.assertEqual(result["profile"], "balanced")
                self.assertEqual(tuple(result[k] for k in ("max_agents", "build_jobs", "memory_gib")), expected)

    def test_overrides_and_shared_memory_reduce_agent_capacity(self):
        self.host()
        result = resources.resolve_resources(max_agents=2, build_jobs=3, memory_gib=5.5)
        self.assertEqual((result["max_agents"], result["build_jobs"], result["memory_gib"]), (2, 3, 5.5))
        self.assertEqual(resources.resolve_resources(memory_gib=5.5)["max_agents"], 2)
        with self.assertRaisesRegex(ValueError, "max_agents"):
            resources.resolve_resources(max_agents=3, memory_gib=5.5)

    def test_explicit_agents_can_exceed_aggressive_default_with_capacity(self):
        self.host(cpus=range(32))
        self.assertEqual(resources.resolve_resources(max_agents=12)["max_agents"], 12)
        with self.assertRaisesRegex(ValueError, "max_agents"):
            resources.resolve_resources(max_agents=13)

    def test_extra_source_agents_do_not_expand_shared_execution_budget(self):
        self.host(cpus=[2, 9])
        result = resources.resolve_resources(max_agents=4)
        self.assertEqual(result["build_jobs"], 2)
        self.assertEqual(resources.resource_environment(result)["MAKEFLAGS"], "-j2")
        self.assertIn("aggregate 2-job/24-GiB", resources.resource_instructions(result))
        with self.assertRaisesRegex(ValueError, "max_agents"):
            resources.resolve_resources(max_agents=5)
        with self.assertRaisesRegex(ValueError, "build_jobs"):
            resources.resolve_resources(max_agents=4, build_jobs=3)
        with self.assertRaisesRegex(ValueError, "max_agents"):
            resources.resolve_resources(max_agents=4, memory_gib=7.5)
        self.assertEqual(resources.resolve_resources(build_jobs=1)["max_agents"], 4)

    def test_override_validation_and_capacity(self):
        self.host(cpus=[2, 7], memory=9)
        for name in ("max_agents", "build_jobs", "memory_gib"):
            for value in (0, -1, float("nan"), float("inf"), -float("inf"), True, "2", [], 10 ** 1000):
                with self.subTest(name=name, value=repr(value)[:30]):
                    with self.assertRaisesRegex(ValueError, name):
                        resources.resolve_resources(**{name: value})
        for name in ("max_agents", "build_jobs"):
            for value in (1.5, 3):
                with self.subTest(name=name, value=value):
                    with self.assertRaisesRegex(ValueError, name):
                        resources.resolve_resources(**{name: value})
        with self.assertRaisesRegex(ValueError, "memory_gib"):
            resources.resolve_resources(memory_gib=5.0001)
        result = resources.resolve_resources(max_agents=2.0, build_jobs=2.0, memory_gib=5)
        self.assertEqual((result["max_agents"], result["build_jobs"], result["memory_gib"]), (2, 2, 5))
        self.assertIsInstance(result["max_agents"], int)
        self.assertIsInstance(result["build_jobs"], int)
        with self.assertRaisesRegex(ValueError, "profile"):
            resources.resolve_resources("unknown")

    def test_profile_ceilings_apply_to_explicit_overrides(self):
        self.host(cpus=range(32))
        for profile, kwargs in (("balanced", {"max_agents": 4}),
                                ("balanced", {"build_jobs": 5}),
                                ("balanced", {"memory_gib": 12.01}),
                                ("aggressive", {"memory_gib": 24.01})):
            with self.subTest(profile=profile, kwargs=kwargs):
                with self.assertRaises(ValueError):
                    resources.resolve_resources(profile, **kwargs)

    def test_no_memory_headroom_reports_but_blocks_launch(self):
        for available in (0, 3, 4):
            with self.subTest(available=available):
                self.host(memory=available)
                result = resources.resolve_resources()
                self.assertEqual(result["max_agents"], 1)
                self.assertEqual(result["memory_gib"], 0)
                json.dumps(result, allow_nan=False)
                with self.assertRaisesRegex(RuntimeError, "host reserve"):
                    resources.check_resources(result)
                with self.assertRaisesRegex(ValueError, "memory_gib"):
                    resources.resolve_resources(memory_gib=0.5)

    def test_memavailable_is_required_not_total_free_or_swap(self):
        self.host()
        for content in ("MemTotal: 999999999 kB\nMemFree: 999999 kB\n",
                        "MemAvailable: invalid kB\n", "MemAvailable: -1 kB\n",
                        "MemAvailable: 123 GiB\n", "MemAvailable:\n"):
            with self.subTest(content=content):
                self.meminfo.return_value = content
                with self.assertRaisesRegex(RuntimeError, "MemAvailable"):
                    resources.resolve_resources()

    def test_measurement_errors_do_not_invent_capacity(self):
        self.host()
        self.affinity.side_effect = OSError("affinity unavailable")
        with self.assertRaisesRegex(OSError, "affinity"):
            resources.resolve_resources()
        self.affinity.side_effect = None
        self.affinity.return_value = set()
        with self.assertRaisesRegex(RuntimeError, "No CPUs"):
            resources.resolve_resources()
        self.affinity.return_value = {2}
        self.meminfo.side_effect = OSError("meminfo unavailable")
        with self.assertRaisesRegex(OSError, "meminfo"):
            resources.resolve_resources()
        self.meminfo.side_effect = None
        self.disk.side_effect = OSError("disk unavailable")
        with self.assertRaisesRegex(OSError, "disk"):
            resources.resolve_resources()

    def test_disk_floors_allow_equality_reject_one_byte_below(self):
        for host_free, scratch_free, passes in ((16 * GIB, 12 * GIB, True),
                                               (16 * GIB - 1, 12 * GIB, False),
                                               (16 * GIB, 12 * GIB - 1, False),
                                               (0, 0, False)):
            with self.subTest(host_free=host_free, scratch_free=scratch_free):
                self.host(host_free=host_free, scratch_free=scratch_free)
                result = resources.resolve_resources(repo=str(REPO))
                self.assertEqual(result["host_disk"]["free_gib"], host_free / GIB)
                self.assertEqual(result["scratch_disk"]["free_gib"], scratch_free / GIB)
                json.dumps(result, allow_nan=False)  # A low-space dry run still reports.
                if passes:
                    self.assertIsNone(resources.check_resources(result))
                else:
                    with self.assertRaisesRegex(RuntimeError, "requires at least"):
                        resources.check_resources(result)

    def test_scratch_is_measured_only_if_mounted(self):
        self.host(mounted=False, scratch_free=0)
        result = resources.resolve_resources(repo=REPO)
        self.assertFalse(result["scratch_disk"]["mounted"])
        self.assertIsNone(result["scratch_disk"]["free_gib"])
        self.disk.assert_called_once_with(REPO)
        self.mount.assert_called_once_with(resources.SCRATCH)
        self.assertIsNone(resources.check_resources(result))

    def test_packet_can_raise_but_cannot_lower_disk_floors(self):
        self.host(host_free=20 * GIB, scratch_free=14 * GIB)
        for key, floor in (("host_disk", 21), ("scratch_disk", 15)):
            with self.subTest(key=key):
                result = resources.resolve_resources()
                result[key]["min_free_gib"] = floor
                with self.assertRaisesRegex(RuntimeError, "at least " + str(floor)):
                    resources.check_resources(result)
        self.host(host_free=15 * GIB, scratch_free=11 * GIB)
        result = resources.resolve_resources()
        result["host_disk"]["min_free_gib"] = 1
        result["scratch_disk"]["min_free_gib"] = 1
        with self.assertRaisesRegex(RuntimeError, "at least 16.*at least 12"):
            resources.check_resources(result)

    def test_environment_is_only_overrides_and_never_mutates_process(self):
        self.host()
        with patch.dict(os.environ, {"MAKEFLAGS": "-j999", "CARGO_BUILD_JOBS": "999",
                                     "MCKERNEL_OS_MAX_AGENTS": "999", "UNRELATED": "keep"}, clear=True):
            before = dict(os.environ)
            result = resources.resolve_resources(max_agents=2, build_jobs=3, memory_gib=5.5)
            overrides = resources.resource_environment(result)
            self.assertEqual(dict(os.environ), before)
            self.assertEqual(overrides, {
                "MAKEFLAGS": "-j3", "CMAKE_BUILD_PARALLEL_LEVEL": "3", "CARGO_BUILD_JOBS": "3",
                "MCKERNEL_OS_RESOURCE_PROFILE": "aggressive", "MCKERNEL_OS_MAX_AGENTS": "2",
                "MCKERNEL_OS_BUILD_JOBS": "3", "MCKERNEL_OS_MEMORY_GIB": "5.5",
                "MCKERNEL_OS_MAX_DEPTH": "1", "MCKERNEL_OS_HEAVY_JOBS": "1"})
            self.assertEqual(dict(before, **overrides)["UNRELATED"], "keep")
            self.assertNotIn("UNRELATED", overrides)

    def test_instructions_share_budgets_and_preserve_reviewed_execution(self):
        self.host()
        text = resources.resource_instructions(resources.resolve_resources(build_jobs=6))
        for expected in ("profile aggressive", "8 child agents", "no recursive",
                         "one heavy build/guest at a time", "disjoint source", "light-test",
                         "aggregate 6-job/24-GiB", "divide jobs", "older coordinator caps only",
                         "CPUs 2-5", "12 GiB", "no network", "independent execution review",
                         "launcher's process tree", "does not forward these variables",
                         "automatically resize containers", "currently -j<=4",
                         "not an enforced cgroup limit", "Do not widen affinity",
                         "16/12 GiB", "greater measured packet"):
            self.assertIn(expected, text)


if __name__ == "__main__":
    unittest.main()
