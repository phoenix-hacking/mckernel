import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock


SOURCE = Path(__file__).parents[1] / "application-tests/native_diagnostic_resource_observer.py"
spec = importlib.util.spec_from_file_location("native_resource_observer", SOURCE)
observer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(observer)
CID = "a" * 64
NONCE = "b" * 32
PID = 12345


def inspect_row(*, running=True, pid=PID):
    return {"Id": CID, "Name": "/mckernel-native-diagnostic-" + NONCE,
            "Image": observer.IMAGE, "HostConfig": {"CgroupParent": "/mckernel-dev"},
            "Config": {"Labels": {"mckernel.native-diagnostic.owner": NONCE}},
            "State": {"Running": running, "Status": "running" if running else "exited",
                      "Pid": pid if running else 0}}


class ObserverTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.proc = self.root / "proc"
        self.cgroup = self.root / "cgroup"
        (self.proc / str(PID)).mkdir(parents=True)
        self.output = self.root / "observation.json"
        self.patch("PROC_ROOT", str(self.proc))
        self.patch("CGROUP_ROOT", str(self.cgroup))
        self.stat(77)
        self.membership()
        self.metrics()
        self.now = [0.0]
        self.ticks = iter([1_000_000_000, 1_100_000_000])
        patch = mock.patch.object(observer.time, "monotonic_ns", side_effect=lambda: next(self.ticks))
        patch.start()
        self.addCleanup(patch.stop)

    def patch(self, name, value):
        patch = mock.patch.object(observer, name, value)
        patch.start()
        self.addCleanup(patch.stop)

    def stat(self, start):
        fields = ["S"] + ["0"] * 18 + [str(start)]
        (self.proc / str(PID) / "stat").write_text(
            str(PID) + " (name with ) spaces) " + " ".join(fields) + "\n")

    def membership(self, path="/mckernel-dev/docker/" + CID, *, duplicate=False,
                   controllers=("memory", "cpuacct,cpu", "pids")):
        lines = ["%d:%s:%s" % (n, names, path) for n, names in enumerate(controllers, 1)]
        if duplicate:
            lines.append("4:memory:" + path)
        (self.proc / str(PID) / "cgroup").write_text("\n".join(lines) + "\n")

    def metrics(self, *, memory_peak=1000, memory_current=900, cpu_ns=100, pids=2):
        path = self.cgroup / "memory/mckernel-dev/docker" / CID
        path.mkdir(parents=True, exist_ok=True)
        (path / "memory.max_usage_in_bytes").write_text(str(memory_peak) + "\n")
        (path / "memory.usage_in_bytes").write_text(str(memory_current) + "\n")
        path = self.cgroup / "cpuacct/mckernel-dev/docker" / CID
        path.mkdir(parents=True, exist_ok=True)
        (path / "cpuacct.usage").write_text(str(cpu_ns) + "\n")
        path = self.cgroup / "cpu/mckernel-dev/docker" / CID
        path.mkdir(parents=True, exist_ok=True)
        (path / "cpu.stat").write_text("nr_periods 10\nnr_throttled 2\nthrottled_time 100\n")
        path = self.cgroup / "pids/mckernel-dev/docker" / CID
        path.mkdir(parents=True, exist_ok=True)
        (path / "pids.current").write_text(str(pids) + "\n")
        (path / "pids.max").write_text("512\n")

    def observe(self, rows=None, *, on_sleep=None, timeout=3):
        if not (self.proc / str(PID) / "stat").exists():
            self.stat(77)
            self.membership()
        rows = iter(rows or [inspect_row(), inspect_row(), inspect_row(running=False)])

        def inspect_next(_):
            row = next(rows)
            if not row["State"]["Running"]:
                # Simulate procfs retirement accompanying the observed exit.
                (self.proc / str(PID) / "stat").unlink(missing_ok=True)
                (self.proc / str(PID) / "cgroup").unlink(missing_ok=True)
            return row

        def sleep(duration):
            self.now[0] += duration
            if on_sleep:
                on_sleep()

        with mock.patch.object(observer.subprocess, "Popen",
                               side_effect=AssertionError("offline test called Docker")):
            return observer.observe(
                CID, NONCE, str(self.output), timeout=timeout, interval=0.1,
                inspect_container=inspect_next, sleep=sleep,
                clock=lambda: self.now[0])

    def test_exact_owned_container_and_peakish_metrics(self):
        calls = [0]

        def advance():
            calls[0] += 1
            if calls[0] == 1:
                self.metrics(memory_peak=1200, memory_current=1100,
                             cpu_ns=200_000_100, pids=3)

        result = self.observe(on_sleep=advance)
        self.assertEqual(result["status"], "MEASURED")
        self.assertEqual(result["stop_reason"], "verified_container_exit")
        self.assertEqual(result["sample_count"], 2)
        self.assertEqual(result["proc_starttime"], 77)
        self.assertEqual(result["peaks"]["memory.memory.max_usage_in_bytes"], 1200)
        self.assertEqual(result["peaks"]["pids.pids.current"], 3)
        self.assertEqual(result["cpu_delta_ns"], 200_000_000)
        self.assertEqual(result["peak_sampled_cpu_millicores"], 2000)
        self.assertEqual(json.loads(self.output.read_text()), result)
        self.assertEqual(os.stat(self.output).st_mode & 0o777, 0o600)

    def test_optional_absence_is_explicit(self):
        self.membership(controllers=("memory", "cpuacct,cpu"))
        (self.cgroup / "cpu/mckernel-dev/docker" / CID / "cpu.stat").unlink()
        with self.assertRaisesRegex(observer.ObserverError, "incomplete cgroup resource sampling"):
            self.observe()
        self.assertFalse(self.output.exists())

    def test_incomplete_cpu_stat_is_rejected_fail_closed(self):
        path = self.cgroup / "cpu/mckernel-dev/docker" / CID / "cpu.stat"
        path.write_text("nr_periods 10\nnr_throttled 2\n")
        with self.assertRaisesRegex(observer.ObserverError, "incomplete cpu.stat"):
            self.observe()
        self.assertFalse(self.output.exists())

    def test_unlimited_pids_limit_is_valid_and_one_sample_has_no_cpu_rate(self):
        limit = self.cgroup / "pids/mckernel-dev/docker" / CID / "pids.max"
        limit.write_text("max\n")
        result = self.observe(rows=[inspect_row(), inspect_row(running=False)])
        self.assertEqual(result["status"], "MEASURED")
        self.assertEqual(result["samples"][0]["counters"]["pids.pids.max"], "max")
        self.assertIsNone(result["cpu_delta_ns"])
        self.assertIsNone(result["peak_sampled_cpu_millicores"])

    def test_identity_and_cgroup_ambiguity_refuse_without_output(self):
        cases = [
            lambda: self.membership(path="/mckernel-dev/docker/" + "c" * 64),
            lambda: self.membership(path="/mckernel-dev/docker/" + CID + "/child"),
            lambda: self.membership(duplicate=True),
            lambda: self.membership(path="/mckernel-dev/docker/../docker/" + CID),
        ]
        for change in cases:
            with self.subTest(change=change):
                self.membership()
                change()
                with self.assertRaises(observer.ObserverError):
                    self.observe()
                self.assertFalse(self.output.exists())

    def test_inspect_identity_and_pid_drift_refuse(self):
        for field, value in (("Id", "c" * 64), ("Name", "/wrong"),
                             ("Image", "sha256:" + "c" * 64)):
            with self.subTest(field=field):
                row = inspect_row()
                row[field] = value
                with self.assertRaises(observer.ObserverError):
                    self.observe(rows=[row])
                self.assertFalse(self.output.exists())
        row = inspect_row()
        row["Config"]["Labels"]["mckernel.native-diagnostic.owner"] = "c" * 32
        with self.assertRaises(observer.ObserverError):
            self.observe(rows=[row])
        row = inspect_row()
        row["HostConfig"]["CgroupParent"] = "/foreign"
        with self.assertRaises(observer.ObserverError):
            self.observe(rows=[row])
        row = inspect_row()
        row["State"]["Status"] = "exited"
        with self.assertRaises(observer.ObserverError):
            self.observe(rows=[row])
        with self.assertRaises(observer.ObserverError):
            self.observe(rows=[inspect_row(), inspect_row(pid=PID + 1)])

    def test_pid_reuse_and_counter_reversal_refuse(self):
        with self.assertRaisesRegex(observer.ObserverError, "identity drift"):
            self.observe(on_sleep=lambda: self.stat(78))
        self.stat(77)
        self.now[0] = 0.0
        self.ticks = iter([1_000_000_000, 1_100_000_000])
        with self.assertRaisesRegex(observer.ObserverError, "counter"):
            self.observe(on_sleep=lambda: self.metrics(cpu_ns=99))
        self.assertFalse(self.output.exists())
        self.now[0] = 0.0
        self.ticks = iter([1_000_000_000, 1_100_000_000])
        self.metrics(memory_peak=1000, cpu_ns=100)
        with self.assertRaisesRegex(observer.ObserverError, "memory peak counter"):
            self.observe(on_sleep=lambda: self.metrics(memory_peak=999, cpu_ns=200))
        self.assertFalse(self.output.exists())

    def test_malformed_oversized_and_symlinked_inputs_refuse(self):
        counter = self.cgroup / "memory/mckernel-dev/docker" / CID / "memory.usage_in_bytes"
        for value in ("max\n", "1" * 257):
            with self.subTest(value=value[:4]):
                counter.write_text(value)
                with self.assertRaises(observer.ObserverError):
                    self.observe()
                self.assertFalse(self.output.exists())
        counter.unlink()
        counter.symlink_to(self.root / "elsewhere")
        with self.assertRaises(OSError):
            self.observe()
        self.assertFalse(self.output.exists())

    def test_timeout_and_existing_output_refuse(self):
        with self.assertRaisesRegex(observer.ObserverError, "timeout"):
            self.observe(rows=[inspect_row()] * 100, timeout=0.15)
        self.assertFalse(self.output.exists())
        self.output.write_text("reserved")
        with self.assertRaisesRegex(observer.ObserverError, "already exists"):
            self.observe()
        self.assertEqual(self.output.read_text(), "reserved")

    def test_exit_before_proc_retirement_refuses_measurement(self):
        rows = iter([inspect_row(), inspect_row(running=False)])
        with mock.patch.object(observer.subprocess, "Popen",
                               side_effect=AssertionError("offline test called Docker")):
            with self.assertRaisesRegex(observer.ObserverError, "PID not retired"):
                observer.observe(CID, NONCE, str(self.output), timeout=3,
                                 interval=0.1, inspect_container=lambda _: next(rows),
                                 sleep=lambda _: None, clock=lambda: 0.0)
        self.assertFalse(self.output.exists())

    def test_invalid_inputs_refuse_before_inspect(self):
        for cid, nonce in (("a" * 12, NONCE), (CID, "bad"), ("A" * 64, NONCE)):
            with self.subTest(cid=cid, nonce=nonce):
                with self.assertRaises(observer.ObserverError):
                    observer.observe(cid, nonce, str(self.output),
                                     inspect_container=lambda _: self.fail("inspected"))

    def test_docker_inspect_client_is_read_only_and_output_bounded(self):
        real_popen = subprocess.Popen
        commands = []
        payload = json.dumps([inspect_row()])

        def valid_popen(argv, **kwargs):
            commands.append(argv)
            return real_popen([sys.executable, "-B", "-c",
                               "import sys; sys.stdout.write(sys.argv[1])", payload], **kwargs)

        with mock.patch.object(observer.subprocess, "Popen", side_effect=valid_popen):
            self.assertEqual(observer.inspect(CID), inspect_row())

        def fake_popen(argv, **kwargs):
            commands.append(argv)
            return real_popen([sys.executable, "-B", "-c",
                               "import sys; sys.stdout.write('x' * 65537)"], **kwargs)

        with mock.patch.object(observer.subprocess, "Popen", side_effect=fake_popen):
            with self.assertRaisesRegex(observer.ObserverError, "oversized Docker inspect"):
                observer.inspect(CID)
        self.assertEqual(commands, [(*observer.DOCKER, "inspect", "--type", "container", CID)] * 2)


if __name__ == "__main__":
    unittest.main()
