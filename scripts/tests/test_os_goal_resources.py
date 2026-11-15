"""Offline resource policy: mocked planning and explicit accounting, no payloads."""
import copy
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
GIB, MIB = 1024 ** 3, 1024 ** 2
REPO = SOURCE.parents[1]


class ResourceTests(unittest.TestCase):
    def test_live_machine_guard_preserves_host_memory_and_disk_headroom(self):
        self.host(memory=4, host_free=16 * GIB, scratch_free=12 * GIB)
        self.assertIsNone(resources.check_machine_headroom(REPO))
        for available in (0, 3.99):
            with patch.object(resources, "_available_memory_gib", return_value=available), \
                    self.assertRaisesRegex(RuntimeError, "Machine headroom exhausted"):
                resources.check_machine_headroom(REPO)
        with patch.object(resources.shutil, "disk_usage", return_value=SimpleNamespace(free=11 * GIB)), \
                self.assertRaisesRegex(RuntimeError, "Machine headroom exhausted"):
            resources.check_machine_headroom(REPO)

    def host(self, cpus=range(8), memory=64, host_free=64 * GIB,
             scratch_free=32 * GIB, mounted=True, total_memory=64):
        def start(target, **kwargs):
            patcher = patch(target, **kwargs)
            result = patcher.start()
            self.addCleanup(patcher.stop)
            return result
        self.affinity = start("os.sched_getaffinity", return_value=set(cpus))
        self.set_affinity = start("os.sched_setaffinity", side_effect=AssertionError("affinity mutation"))
        self.meminfo = start("pathlib.Path.read_text", return_value=(
            "MemTotal: {} kB\nMemFree: 1 kB\nMemAvailable: {} kB\n"
            .format(int(total_memory * 1024 ** 2), int(memory * 1024 ** 2))))
        start("os.path.ismount", return_value=mounted)
        start("shutil.disk_usage", side_effect=lambda path: SimpleNamespace(
            free=scratch_free if Path(path) == resources.SCRATCH else host_free))

    def test_profiles_cap_host_and_keep_native_separate(self):
        self.host()
        for profile in ("aggressive", "balanced"):
            result = resources.resolve_resources(profile, repo=REPO)
            self.assertEqual((result["max_agents"], result["build_jobs"], result["memory_gib"]),
                             (6, 3, 4))
            self.assertEqual(result["host_memory_ceiling_bytes"], 4 * GIB)
            self.assertEqual(result["payload_memavailable_gib"], 26)
            self.assertEqual(result["host_max_jobs"], 3)
            self.assertEqual(result["source_owner_slots"], 6)
            self.assertEqual(result["cpu_affinity"], [0, 6, 7])
            self.assertEqual(result["host_cpu_affinity"], [0, 6, 7])
            self.assertEqual(result["observed_cpu_affinity"], list(range(8)))
            self.assertEqual(result["native"], {
                "cpu_affinity": [2, 3, 4, 5], "memory_gib": 12,
                "max_owners": 1, "separate_admission_required": True})
            self.assertIsNone(result["agent_memory_gib"])
            self.assertTrue(result["payload_admission_required"])
            self.assertEqual(json.loads(json.dumps(result, allow_nan=False)), result)
            self.assertIsNone(resources.check_resources(result))
        self.set_affinity.assert_not_called()

    def test_six_remote_slots_do_not_reserve_six_payload_slices(self):
        self.host(cpus=[7], memory=5)
        result = resources.resolve_resources()
        self.assertEqual((result["max_agents"], result["build_jobs"], result["memory_gib"]), (6, 1, 1))
        self.assertEqual(resources.resolve_resources(memory_gib=0.5)["max_agents"], 6)
        self.assertEqual(resources.resolve_resources(max_agents=2)["max_agents"], 2)

    def test_explicit_eleven_slots_keep_one_shared_host_pool_and_native_owner(self):
        self.host()
        for profile in ("aggressive", "balanced"):
            result = resources.resolve_resources(profile, max_agents=11)
            self.assertEqual((result["max_agents"], result["source_owner_slots"]), (11, 11))
            self.assertEqual((result["build_jobs"], result["memory_gib"], result["cpu_affinity"]),
                             (3, 4, [0, 6, 7]))
            self.assertEqual(result["max_depth"], 1)
            self.assertEqual(result["native"], {
                "cpu_affinity": [2, 3, 4, 5], "memory_gib": 12,
                "max_owners": 1, "separate_admission_required": True})
            self.assertIsNone(result["agent_memory_gib"])
            self.assertTrue(result["payload_admission_required"])
            self.assertIsNone(resources.check_resources(result))
            env = resources.resource_environment(result)
            self.assertEqual((env["MCKERNEL_OS_MAX_AGENTS"], env["MAKEFLAGS"],
                              env["MCKERNEL_OS_MEMORY_GIB"]), ("11", "-j3", "4"))
        self.host(cpus=[7], memory=5)
        small = resources.resolve_resources(max_agents=11)
        self.assertEqual((small["max_agents"], small["build_jobs"], small["memory_gib"]),
                         (11, 1, 1))
        self.set_affinity.assert_not_called()

    def test_explicit_pool_expansion_preserves_reservations_and_native_owner(self):
        for pool in (5, 8, 24):
            self.host(memory=18 + 4 + pool)
            result = resources.resolve_resources(memory_gib=pool, repo=REPO)
            self.assertEqual((result["memory_gib"], result["host_memory_ceiling_bytes"],
                              result["payload_memavailable_gib"]), (pool, pool * GIB, 22 + pool))
            self.assertEqual((result["build_jobs"], result["cpu_affinity"]), (3, [0, 6, 7]))
            self.assertEqual((result["non_host_reservation_gib"], result["memory_reserve_gib"]), (18, 4))
            self.assertEqual(result["native"], {
                "cpu_affinity": [2, 3, 4, 5], "memory_gib": 12,
                "max_owners": 1, "separate_admission_required": True})
            self.assertIsNone(result["agent_memory_gib"])
            self.assertIsNone(resources.check_resources(result))
            env = resources.resource_environment(result)
            self.assertEqual(env["MCKERNEL_OS_MEMORY_GIB"], str(pool))
            self.assertEqual(env["MCKERNEL_OS_HOST_MEMORY_CEILING_BYTES"], str(pool * GIB))
            instructions = resources.resource_instructions(result)
            self.assertIn("{} GiB TOTAL".format(pool), instructions)
            self.assertIn("{} GiB MemAvailable".format(22 + pool), instructions)
            self.assertIn("host_memory_ceiling_bytes", instructions)
            self.assertIn("does not change any command's enforced memory limit", instructions)
            self.assertEqual(resources.resolve_resources()["memory_gib"], 4)
            with patch.object(resources, "_available_memory_gib", return_value=22 + pool - 1 / GIB):
                with self.assertRaisesRegex(ValueError, "memory_gib exceeds"):
                    resources.resolve_resources(memory_gib=pool)
            changed = copy.deepcopy(result)
            changed["available_memory_gib"] -= 1 / GIB
            with self.assertRaisesRegex(RuntimeError, "Expanded HOST pool requires"):
                resources.check_resources(changed)
        self.set_affinity.assert_not_called()

    def test_dispatcher_selects_measured_cpus_jobs_and_next_server_slots(self):
        self.host()
        result = resources.resolve_resources(max_agents=32, build_jobs=4, memory_gib=16,
                                             host_cpu_affinity=[0, 1, 6, 7], host_max_jobs=4)
        self.assertEqual((result["max_agents"], result["source_owner_slots"]), (32, 32))
        self.assertEqual((result["build_jobs"], result["host_max_jobs"]), (4, 4))
        self.assertEqual((result["cpu_affinity"], result["host_cpu_affinity"]),
                         ([0, 1, 6, 7], [0, 1, 6, 7]))
        self.assertIsNone(resources.check_resources(result))
        env = resources.resource_environment(result)
        self.assertEqual((env["MCKERNEL_OS_MAX_AGENTS"], env["MAKEFLAGS"],
                          env["MCKERNEL_OS_HOST_MAX_JOBS"], env["MCKERNEL_OS_HOST_CPU_AFFINITY"]),
                         ("32", "-j4", "4", "0,1,6,7"))
        instructions = resources.resource_instructions(result)
        self.assertIn("actual loaded slot limit remains binding", instructions)
        self.assertIn("selected CPUs 0,1,6,7", instructions)
        self.assertIn("up to 4 aggregate payload jobs", instructions)
        self.assertIn("never clear native ownership", instructions)
        explicit_build = resources.resolve_resources(build_jobs=4)
        self.assertEqual((explicit_build["build_jobs"], explicit_build["host_max_jobs"]), (4, 4))
        for cpus in ([8], [0, 8], [0, 0], [True], [], "0,1"):
            with self.subTest(cpus=cpus), self.assertRaises(ValueError):
                resources.resolve_resources(host_cpu_affinity=cpus)
        changed = copy.deepcopy(result)
        changed["observed_cpu_affinity"] = [0, 6, 7]
        with self.assertRaisesRegex(ValueError, "outside the measured HOST selection"):
            resources.check_resources(changed)
        changed = copy.deepcopy(result)
        changed["build_jobs"] = 5
        with self.assertRaisesRegex(ValueError, "selected job ceiling"):
            resources.check_resources(changed)
        self.set_affinity.assert_not_called()

    def test_shared_work_pool_uses_physical_total_and_preserves_os_reserve(self):
        self.host(memory=24, total_memory=30.9196)
        result = resources.resolve_resources(work_memory_gib=28)
        self.assertEqual((result["work_memory_ceiling_bytes"], result["host_memory_ceiling_bytes"]),
                         (28 * GIB, 10 * GIB))
        self.assertEqual((result["memory_gib"], result["machine_reserve_gib"]), (10, 2))
        self.assertIsNone(result["payload_memavailable_gib"])
        self.assertIsNone(resources.check_resources(result))
        self.assertAlmostEqual(result["total_memory_gib"], 30.9196, places=5)
        env = resources.resource_environment(result)
        self.assertEqual((env["MCKERNEL_OS_WORK_MEMORY_GIB"], env["MCKERNEL_OS_MEMORY_GIB"],
                          env["MCKERNEL_OS_MACHINE_RESERVE_GIB"]), ("28", "10", "2"))
        self.assertEqual(env["MCKERNEL_OS_WORK_MEMORY_CEILING_BYTES"], str(28 * GIB))
        instructions = resources.resource_instructions(result)
        self.assertIn("28 GiB TOTAL shared work ceiling containing the preserved 18 GiB", instructions)
        self.assertIn("and the 10 GiB HOST ceiling", instructions)
        self.assertIn("not charged twice", instructions)
        self.assertIn("Run independent HOST compiles and checks in parallel", instructions)
        self.assertNotIn("one heavy build/guest at a time", instructions)
        with self.assertRaisesRegex(ValueError, "MemTotal minus the 2 GiB"):
            resources.resolve_resources(work_memory_gib=30)
        with self.assertRaisesRegex(ValueError, "memory_gib exceeds"):
            resources.resolve_resources(work_memory_gib=28, memory_gib=10.01)
        with self.assertRaisesRegex(ValueError, "preserved 18 GiB"):
            resources.resolve_resources(work_memory_gib=18)
        changed = copy.deepcopy(result)
        changed["available_memory_gib"] = 2 - 1 / GIB
        with self.assertRaisesRegex(RuntimeError, "2 GiB machine-free floor"):
            resources.check_resources(changed)
        self.set_affinity.assert_not_called()

    def test_explicit_machine_guard_reserve_keeps_two_gib_minimum(self):
        self.host(memory=2)
        self.assertIsNone(resources.check_machine_headroom(REPO, memory_reserve_gib=2))
        with self.assertRaisesRegex(RuntimeError, "Machine headroom exhausted"):
            resources.check_machine_headroom(REPO)
        for reserve in (0, 1.99, None, True, float("inf")):
            with self.subTest(reserve=reserve), self.assertRaises(ValueError):
                resources.check_machine_headroom(REPO, memory_reserve_gib=reserve)

    def test_invalid_or_overlarge_overrides_never_expand_beyond_explicit_pool(self):
        self.host(cpus=range(32))
        for profile in ("aggressive", "balanced"):
            for kwargs in ({"host_max_jobs": 3, "build_jobs": 4}, {"memory_gib": 42.01},
                           {"host_max_jobs": 4, "build_jobs": 5}):
                with self.assertRaises(ValueError):
                    resources.resolve_resources(profile, **kwargs)
        for name in ("max_agents", "build_jobs", "memory_gib", "host_max_jobs", "work_memory_gib"):
            for value in (0, -1, float("nan"), float("inf"), True, "2", []):
                with self.subTest(name=name, value=repr(value)[:20]):
                    with self.assertRaises(ValueError):
                        resources.resolve_resources(**{name: value})
        for name in ("max_agents", "build_jobs", "host_max_jobs"):
            with self.assertRaises(ValueError):
                resources.resolve_resources(**{name: 1.5})
        with self.assertRaises(ValueError):
            resources.resolve_resources("unknown")

    def test_native_only_affinity_never_becomes_host_or_unlimited_make(self):
        self.host(cpus=[2, 3, 4, 5])
        result = resources.resolve_resources()
        self.assertEqual((result["cpu_affinity"], result["build_jobs"]), ([], 0))
        with self.assertRaisesRegex(RuntimeError, "No campaign HOST CPU"):
            resources.check_resources(result)
        with self.assertRaises(ValueError):
            resources.resource_environment(result)
        self.set_affinity.assert_not_called()

    def test_unknown_or_insufficient_capacity_does_not_invent_headroom(self):
        self.host()
        self.affinity.side_effect = OSError("affinity unavailable")
        with self.assertRaises(OSError):
            resources.resolve_resources()
        self.affinity.side_effect = None
        self.affinity.return_value = set()
        with self.assertRaisesRegex(RuntimeError, "No CPUs"):
            resources.resolve_resources()
        self.affinity.return_value = {7}
        self.meminfo.return_value = "MemTotal: 9999999 kB\n"
        with self.assertRaisesRegex(RuntimeError, "MemAvailable"):
            resources.resolve_resources()
        self.host(memory=4)
        result = resources.resolve_resources()
        self.assertEqual(result["memory_gib"], 0)
        with self.assertRaisesRegex(RuntimeError, "host reserve"):
            resources.check_resources(result)

    def test_planning_floors_environment_and_no_payload_grant(self):
        self.host(host_free=16 * GIB, scratch_free=12 * GIB)
        result = resources.resolve_resources(repo=REPO)
        self.assertIsNone(resources.check_resources(result))
        with patch.dict(os.environ, {"MAKEFLAGS": "-j999", "UNRELATED": "keep"}, clear=True):
            before = dict(os.environ)
            env = resources.resource_environment(result)
            self.assertEqual(dict(os.environ), before)
            self.assertEqual((env["MAKEFLAGS"], env["CARGO_BUILD_JOBS"], env["MCKERNEL_OS_MEMORY_GIB"]),
                             ("-j3", "3", "4"))
            self.assertEqual(env["MCKERNEL_OS_MAX_AGENTS"], "6")
            self.assertEqual(env["MCKERNEL_OS_HOST_MEMORY_CEILING_BYTES"], str(4 * GIB))
            self.assertEqual(env["MCKERNEL_OS_HOST_CPU_AFFINITY"], "0,6,7")
            self.assertEqual(env["MCKERNEL_OS_HOST_MAX_JOBS"], "3")
        with self.assertRaisesRegex(ValueError, "explicit payload accounting"):
            resources.check_payload_admission(result, {}, now_utc_ns=1, now_mono_ns=1)
        self.host(host_free=16 * GIB - 1, scratch_free=12 * GIB - 1)
        result = resources.resolve_resources()
        result["host_disk"]["min_free_gib"] = 1
        result["scratch_disk"]["min_free_gib"] = 1
        with self.assertRaisesRegex(RuntimeError, "at least 16.*at least 12"):
            resources.check_resources(result)


class PayloadAdmissionTests(unittest.TestCase):
    def setUp(self):
        self.utc, self.mono = 9_000_000_000_000_000_000, 100_000_000_000
        self.snapshot = {
            "observed_utc_ns": self.utc - 1_000_000_000,
            "observed_mono_ns": self.mono - 1_000_000_000,
            "cpu_affinity": list(range(8)), "MemAvailable_bytes": 26 * GIB,
            "host_free_bytes": 17 * GIB, "scratch_free_bytes": 13 * GIB,
            "retained_charges_complete": True,
            "retained_charges": [
                {"owner": "original-publisher", "planning_bytes": 2 * GIB, "jobs": 1, "state": "UNKNOWN"},
                {"owner": "unjoined-reader", "planning_bytes": 256 * MIB, "jobs": 1, "state": "RETAINED"}],
            "controller_worker_overhead_bytes": 128 * MIB,
            "all_controller_worker_overhead_measured": True, "exclusive_scope_compatible": True}
        self.request = {"CPU": [7], "planning_bytes": 768 * MIB, "jobs": 1,
                        "host_floor_bytes": 17 * GIB, "scratch_floor_bytes": 13 * GIB,
                        "max_age_ns": 25_000_000_000}

    def check(self, snapshot=None, request=None, **clocks):
        return resources.check_payload_admission(
            self.snapshot if snapshot is None else snapshot,
            self.request if request is None else request,
            now_utc_ns=clocks.get("utc", self.utc), now_mono_ns=clocks.get("mono", self.mono))

    def test_retained_225_gib_jobs2_survives_logical_slot_release(self):
        before = copy.deepcopy((self.snapshot, self.request))
        result = self.check()
        self.assertEqual((result["retained_bytes"], result["retained_jobs"]), (2 * GIB + 256 * MIB, 2))
        self.assertEqual((result["accounted_total_bytes"], result["accounted_total_jobs"]),
                         (3 * GIB + 128 * MIB, 3))
        self.assertEqual(result["scope"], "HOST_resource_check_only")
        self.assertEqual(result["host_memory_ceiling_bytes"], 4 * GIB)
        self.assertEqual(result["required_memavailable_bytes"], 26 * GIB)
        self.assertEqual((result["host_cpu_affinity"], result["host_max_jobs"]), ([0, 6, 7], 3))
        with self.assertRaisesRegex(RuntimeError, "Retained charges"):
            self.check(request=dict(self.request, planning_bytes=2 * GIB))
        self.assertEqual((self.snapshot, self.request), before)

    def test_exact_total_equality_passes_one_byte_or_job_over_fails(self):
        exact = 4 * GIB - (2 * GIB + 256 * MIB) - 128 * MIB
        self.assertEqual(self.check(request=dict(self.request, planning_bytes=exact))[
            "accounted_total_bytes"], 4 * GIB)
        for request in (dict(self.request, planning_bytes=exact + 1), dict(self.request, jobs=2)):
            with self.assertRaisesRegex(RuntimeError, "4 GiB/max3"):
                self.check(request=request)

    def test_capacity_refusal_names_real_headroom_without_changing_request(self):
        before = copy.deepcopy((self.snapshot, self.request))
        maximum = 4 * GIB - (2 * GIB + 256 * MIB) - 128 * MIB
        with self.assertRaisesRegex(RuntimeError, "maximum_new_family_bytes=" + str(maximum)) as failure:
            self.check(request=dict(self.request, planning_bytes=2 * GIB))
        self.assertIn("maximum_new_jobs=1", str(failure.exception))
        self.assertEqual((self.snapshot, self.request), before)

    def test_explicit_five_gib_pool_fits_real_smp_total_without_shrinking_family(self):
        snapshot = copy.deepcopy(self.snapshot)
        snapshot.update({"MemAvailable_bytes": 27 * GIB,
                         "controller_worker_overhead_bytes": 1906847744})
        snapshot["retained_charges"][0]["planning_bytes"] = 256 * MIB
        snapshot["retained_charges"][1]["planning_bytes"] = 128 * MIB
        request = dict(self.request, planning_bytes=2 * GIB)
        before = copy.deepcopy((snapshot, request))
        with self.assertRaisesRegex(RuntimeError, "4 GiB/max3"):
            self.check(snapshot=snapshot, request=request)
        expanded = dict(request, host_memory_ceiling_bytes=5 * GIB)
        result = self.check(snapshot=snapshot, request=expanded)
        self.assertEqual((result["accounted_total_bytes"], result["accounted_total_jobs"]),
                         (4456984576, 3))
        self.assertEqual(result["new_family_bytes"], 2 * GIB)
        self.assertEqual(result["host_memory_ceiling_bytes"], 5 * GIB)
        self.assertEqual(result["required_memavailable_bytes"], 27 * GIB)
        self.assertEqual((snapshot, request), before)
        self.assertEqual(expanded, dict(request, host_memory_ceiling_bytes=5 * GIB))

    def test_shared_28_gib_pool_fits_real_smp_without_counting_resident_controls_twice(self):
        snapshot = copy.deepcopy(self.snapshot)
        snapshot.update({"MemTotal_bytes": int(30.9196 * GIB), "MemAvailable_bytes": 24 * GIB,
                         "controller_worker_overhead_bytes": 1906847744})
        snapshot["retained_charges"][0]["planning_bytes"] = 256 * MIB
        snapshot["retained_charges"][1]["planning_bytes"] = 128 * MIB
        request = dict(self.request, planning_bytes=2 * GIB,
                       work_memory_ceiling_bytes=28 * GIB, host_memory_ceiling_bytes=10 * GIB)
        before = copy.deepcopy((snapshot, request))
        result = self.check(snapshot=snapshot, request=request)
        required = 18 * GIB + 384 * MIB + 2 * GIB + 2 * GIB
        self.assertEqual(result["accounted_total_bytes"], 4456984576)
        self.assertEqual(result["measured_overhead_bytes"], 1906847744)
        self.assertEqual(result["required_memavailable_bytes"], required)
        self.assertEqual((result["work_memory_ceiling_bytes"], result["host_memory_ceiling_bytes"],
                          result["machine_reserve_gib"]), (28 * GIB, 10 * GIB, 2))
        self.assertEqual(result["accounted_work_total_bytes"], 18 * GIB + 4456984576)
        self.assertTrue(result["shared_work_pool"])
        self.check(snapshot=dict(snapshot, MemAvailable_bytes=required), request=request)
        with self.assertRaisesRegex(RuntimeError, "Shared work admission requires"):
            self.check(snapshot=dict(snapshot, MemAvailable_bytes=required - 1), request=request)
        with self.assertRaisesRegex(RuntimeError, "MemTotal minus the 2 GiB"):
            self.check(snapshot=snapshot, request=dict(request, work_memory_ceiling_bytes=30 * GIB))
        with self.assertRaisesRegex(ValueError, "exceeds shared work pool"):
            self.check(snapshot=snapshot, request=dict(request, host_memory_ceiling_bytes=11 * GIB))
        no_total = dict(snapshot)
        del no_total["MemTotal_bytes"]
        with self.assertRaisesRegex(ValueError, "MemTotal_bytes"):
            self.check(snapshot=no_total, request=request)
        no_host_ceiling = dict(request)
        del no_host_ceiling["host_memory_ceiling_bytes"]
        with self.assertRaisesRegex(ValueError, "host_memory_ceiling_bytes"):
            self.check(snapshot=snapshot, request=no_host_ceiling)
        self.assertEqual((snapshot, request), before)

    def test_shared_pool_only_credits_positive_measured_non_host_residency(self):
        snapshot = dict(self.snapshot, MemTotal_bytes=31 * GIB,
                        non_host_resident_bytes=12 * GIB)
        request = dict(self.request, work_memory_ceiling_bytes=28 * GIB,
                       host_memory_ceiling_bytes=10 * GIB)
        required = 6 * GIB + (2 * GIB + 256 * MIB) + 768 * MIB + 2 * GIB
        snapshot["MemAvailable_bytes"] = required
        result = self.check(snapshot=snapshot, request=request)
        self.assertEqual(result["required_memavailable_bytes"], required)
        self.assertEqual(result["non_host_resident_bytes"], 12 * GIB)
        no_measurement = dict(snapshot)
        del no_measurement["non_host_resident_bytes"]
        with self.assertRaisesRegex(RuntimeError, "Shared work admission requires"):
            self.check(snapshot=no_measurement, request=request)
        for resident in (None, True, -1, 12.0 * GIB, 18 * GIB + 1):
            with self.subTest(resident=resident), self.assertRaises(ValueError):
                self.check(snapshot=dict(snapshot, non_host_resident_bytes=resident), request=request)
        with self.assertRaisesRegex(RuntimeError, "exclusive ownership"):
            self.check(snapshot=dict(snapshot, exclusive_scope_compatible=False), request=request)
        with self.assertRaisesRegex(RuntimeError, "Fresh paired"):
            self.check(snapshot=snapshot, request=request,
                       utc=self.utc + 25_000_000_000, mono=self.mono + 25_000_000_000)

    def test_expanded_pool_counts_all_charges_and_preserves_three_job_ceiling(self):
        for pool in (5, 8, 24):
            snapshot = dict(self.snapshot, MemAvailable_bytes=(22 + pool) * GIB)
            exact = pool * GIB - (2 * GIB + 256 * MIB) - 128 * MIB
            request = dict(self.request, host_memory_ceiling_bytes=pool * GIB,
                           planning_bytes=exact)
            result = self.check(snapshot=snapshot, request=request)
            self.assertEqual(result["accounted_total_bytes"], pool * GIB)
            self.assertEqual(result["host_memory_ceiling_bytes"], pool * GIB)
            for oversized in (dict(request, planning_bytes=exact + 1), dict(request, jobs=2)):
                with self.assertRaisesRegex(RuntimeError, "{} GiB/max3".format(pool)):
                    self.check(snapshot=snapshot, request=oversized)
            with self.assertRaisesRegex(RuntimeError, "maximum_new_family_bytes=" + str(exact)):
                self.check(snapshot=snapshot, request=dict(request, planning_bytes=exact + 1))

    def test_expanded_ceiling_requires_real_fresh_headroom_and_numeric_selection(self):
        for pool in (5, 8, 24):
            request = dict(self.request, host_memory_ceiling_bytes=pool * GIB)
            snapshot = dict(self.snapshot, MemAvailable_bytes=(22 + pool) * GIB)
            self.check(snapshot=snapshot, request=request)
            with self.assertRaisesRegex(RuntimeError, "at least {} GiB MemAvailable".format(22 + pool)):
                self.check(snapshot=dict(snapshot, MemAvailable_bytes=(22 + pool) * GIB - 1),
                           request=request)
            with self.assertRaisesRegex(RuntimeError, "Fresh paired"):
                self.check(snapshot=snapshot, request=request,
                           utc=self.utc + 25_000_000_000, mono=self.mono + 25_000_000_000)
        for value in (None, True, False, 0, -1, 5.0 * GIB, "5368709120", float("inf")):
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.check(request=dict(self.request, host_memory_ceiling_bytes=value))

    def test_explicit_cpu_and_job_limits_require_measured_compatible_ownership(self):
        request = dict(self.request, CPU=[1], jobs=2,
                       host_cpu_affinity=[0, 1, 6, 7], host_max_jobs=4)
        before = copy.deepcopy((self.snapshot, request))
        result = self.check(request=request)
        self.assertEqual((result["accounted_total_jobs"], result["host_max_jobs"]), (4, 4))
        self.assertEqual((result["CPU"], result["host_cpu_affinity"]), ([1], [0, 1, 6, 7]))
        self.assertEqual(result["scope"], "HOST_resource_check_only")
        with self.assertRaisesRegex(RuntimeError, "max4 HOST jobs"):
            self.check(request=dict(request, jobs=3))
        with self.assertRaisesRegex(RuntimeError, "outside measured selected HOST"):
            self.check(request=dict(request, CPU=[2]))
        with self.assertRaisesRegex(RuntimeError, "outside measured process affinity"):
            self.check(request=dict(request, host_cpu_affinity=[0, 1, 6, 7, 8]))
        with self.assertRaisesRegex(RuntimeError, "exclusive ownership"):
            self.check(snapshot=dict(self.snapshot, exclusive_scope_compatible=False), request=request)
        # Selecting a measured native CPU is only a resource check, never a
        # release of the separate actual native owner or its admission gates.
        native_cpu_request = dict(request, CPU=[2], host_cpu_affinity=[2, 6, 7])
        with self.assertRaisesRegex(RuntimeError, "exclusive ownership"):
            self.check(snapshot=dict(self.snapshot, exclusive_scope_compatible=False),
                       request=native_cpu_request)
        for value in (None, True, False, 0, -1, 4.0, "4", float("inf")):
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.check(request=dict(request, host_max_jobs=value))
        for cpus in (None, [], [0, 0], [True], "0,1"):
            with self.subTest(cpus=cpus), self.assertRaises(ValueError):
                self.check(request=dict(request, host_cpu_affinity=cpus))
        self.assertEqual((self.snapshot, request), before)

    def test_smaller_explicit_pool_preserves_actual_reservations_without_default_floor(self):
        snapshot = dict(self.snapshot, retained_charges=[], MemAvailable_bytes=23 * GIB)
        request = dict(self.request, host_memory_ceiling_bytes=GIB)
        self.assertEqual(self.check(snapshot=snapshot, request=request)["required_memavailable_bytes"],
                         23 * GIB)
        with self.assertRaisesRegex(RuntimeError, "at least 26 GiB MemAvailable"):
            self.check(snapshot=snapshot)

    def test_missing_live_fields_never_default_to_zero(self):
        for field in self.snapshot:
            snapshot = copy.deepcopy(self.snapshot)
            del snapshot[field]
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.check(snapshot=snapshot)
        for field in self.request:
            request = dict(self.request)
            del request[field]
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.check(request=request)

    def test_incomplete_accounting_unknown_exclusivity_or_overhead_denies(self):
        for field in ("retained_charges_complete", "all_controller_worker_overhead_measured",
                      "exclusive_scope_compatible"):
            for value in (False, None, "UNKNOWN", 1):
                with self.subTest(field=field, value=value), self.assertRaises(RuntimeError):
                    self.check(snapshot=dict(self.snapshot, **{field: value}))
        for value in (0, None, False, 1.0):
            with self.assertRaises(ValueError):
                self.check(snapshot=dict(self.snapshot, controller_worker_overhead_bytes=value))
        self.assertEqual(self.check(snapshot=dict(self.snapshot, retained_charges=[]))["retained_bytes"], 0)
        for change in ({"state": "closed"}, {"planning_bytes": None}, {"jobs": False},
                       {"planning_bytes": 0}, {"jobs": 0}):
            snapshot = copy.deepcopy(self.snapshot)
            snapshot["retained_charges"][0].update(change)
            with self.assertRaises(ValueError):
                self.check(snapshot=snapshot)

    def test_same_root_multiple_families_are_all_counted_not_one_agent_slot(self):
        snapshot = copy.deepcopy(self.snapshot)
        for row in snapshot["retained_charges"]:
            row["owner"] = "same-root"
        result = self.check(snapshot=snapshot)
        self.assertEqual((result["retained_bytes"], result["retained_jobs"]),
                         (2 * GIB + 256 * MIB, 2))
        with self.assertRaises(RuntimeError):
            self.check(snapshot=snapshot, request=dict(self.request, planning_bytes=2 * GIB))

    def test_native_or_unmeasured_cpus_never_become_host_capacity(self):
        for cpus in ([2], [1], [7, 7], [True]):
            with self.subTest(cpus=cpus), self.assertRaises((ValueError, RuntimeError)):
                self.check(request=dict(self.request, CPU=cpus))
        with self.assertRaises(RuntimeError):
            self.check(snapshot=dict(self.snapshot, cpu_affinity=[0]))

    def test_paired_clocks_must_be_fresh_not_future_or_incoherent(self):
        self.check(utc=self.utc + 24_000_000_000, mono=self.mono + 24_000_000_000)
        for clocks in ({"utc": self.utc + 24_000_000_001, "mono": self.mono + 24_000_000_001},
                       {"utc": self.utc - 2_000_000_000}, {"mono": self.mono - 2_000_000_000},
                       {"utc": self.utc + 2_000_000_000}):
            with self.subTest(clocks=clocks), self.assertRaises(RuntimeError):
                self.check(**clocks)
        with self.assertRaises(ValueError):
            self.check(request=dict(self.request, max_age_ns=25_000_000_001))
        with self.assertRaises(ValueError):
            self.check(utc=float(self.utc))

    def test_26_gib_and_exact_packet_disk_floors_cannot_be_lowered(self):
        self.check()
        for field in ("MemAvailable_bytes", "host_free_bytes", "scratch_free_bytes"):
            snapshot = dict(self.snapshot)
            snapshot[field] -= 1
            with self.subTest(field=field), self.assertRaises(RuntimeError):
                self.check(snapshot=snapshot)
        for field, value in (("host_floor_bytes", 16 * GIB - 1), ("scratch_floor_bytes", 12 * GIB - 1)):
            with self.assertRaises(ValueError):
                self.check(request=dict(self.request, **{field: value}))


if __name__ == "__main__":
    unittest.main()
