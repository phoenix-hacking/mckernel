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
    def host(self, cpus=range(8), memory=64, host_free=64 * GIB,
             scratch_free=32 * GIB, mounted=True):
        def start(target, **kwargs):
            patcher = patch(target, **kwargs)
            result = patcher.start()
            self.addCleanup(patcher.stop)
            return result
        self.affinity = start("os.sched_getaffinity", return_value=set(cpus))
        self.set_affinity = start("os.sched_setaffinity", side_effect=AssertionError("affinity mutation"))
        self.meminfo = start("pathlib.Path.read_text", return_value=(
            "MemTotal: 999999999 kB\nMemFree: 1 kB\nMemAvailable: {} kB\n"
            .format(int(memory * 1024 ** 2))))
        start("os.path.ismount", return_value=mounted)
        start("shutil.disk_usage", side_effect=lambda path: SimpleNamespace(
            free=scratch_free if Path(path) == resources.SCRATCH else host_free))

    def test_profiles_cap_host_and_keep_native_separate(self):
        self.host()
        for profile in ("aggressive", "balanced"):
            result = resources.resolve_resources(profile, repo=REPO)
            self.assertEqual((result["max_agents"], result["build_jobs"], result["memory_gib"]),
                             (6, 3, 4))
            self.assertEqual(result["cpu_affinity"], [0, 6, 7])
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

    def test_invalid_or_overlarge_overrides_never_expand_pool(self):
        self.host(cpus=range(32))
        for profile in ("aggressive", "balanced"):
            for kwargs in ({"max_agents": 7}, {"build_jobs": 4}, {"memory_gib": 4.01}):
                with self.assertRaises(ValueError):
                    resources.resolve_resources(profile, **kwargs)
        for name in ("max_agents", "build_jobs", "memory_gib"):
            for value in (0, -1, float("nan"), float("inf"), True, "2", [], 10 ** 1000):
                with self.subTest(name=name, value=repr(value)[:20]):
                    with self.assertRaises(ValueError):
                        resources.resolve_resources(**{name: value})
        for name in ("max_agents", "build_jobs"):
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
