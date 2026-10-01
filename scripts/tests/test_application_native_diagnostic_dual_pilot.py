"""Offline safety regressions for the two-guest pilot; never invoke Docker."""

import copy
from contextlib import ExitStack
import importlib.util
import json
import os
from pathlib import Path
import signal
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch


SOURCE = Path(__file__).resolve().parents[1] / "application-tests/native_diagnostic_dual_pilot.py"
SPEC = importlib.util.spec_from_file_location("native_diagnostic_dual_pilot", SOURCE)
pilot = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(pilot)


class FinishedClient:
    returncode = 0

    def poll(self):
        return 0

    def wait(self, timeout=None):
        return 0


class DualPilotTests(unittest.TestCase):
    @staticmethod
    def created_row(cid, name, nonce, cpus, parent, manifest, runtime_runner=None, runtime_dir=None):
        command = ["-B", str(runtime_runner or pilot.RUNNER), "--manifest", str(manifest),
                   "--attempt-parent", str(parent), "--attempt-name", "attempt",
                   "--timeout", "300"]
        mounts = [(pilot.REPO, False), (pilot.SCRATCH, False), (parent, True)]
        if runtime_dir is not None:
            mounts.append((runtime_dir, False))
        return {
            "Id": cid, "Name": "/" + name, "Image": pilot.IMAGE,
            "Path": "/usr/bin/python3", "Args": command,
            "Config": {
                "Labels": {"mckernel.dual-pilot.owner": nonce}, "User": "1000:1000",
                "WorkingDir": str(parent), "Entrypoint": ["/usr/bin/python3"],
                "Cmd": command,
                "Env": ["HOME=/tmp", "TMPDIR=/tmp", "PYTHONDONTWRITEBYTECODE=1"],
            },
            "HostConfig": {
                "NanoCpus": 2_000_000_000, "CpusetCpus": ",".join(map(str, cpus)),
                "Memory": pilot.CONTAINER_MEMORY, "MemorySwap": pilot.CONTAINER_MEMORY,
                "PidsLimit": 256, "NetworkMode": "none", "Privileged": False,
                "ReadonlyRootfs": True, "CapDrop": ["ALL"],
                "SecurityOpt": ["no-new-privileges"],
                "LogConfig": {"Type": "local", "Config": {"max-size": "5m", "max-file": "2"}},
                "Tmpfs": {"/tmp": "rw,nodev,nosuid,size=256m"},
                "Ulimits": [{"Name": "core", "Soft": 0, "Hard": 0},
                            {"Name": "fsize", "Soft": 104857600, "Hard": 104857600}],
                "RestartPolicy": {"Name": "no", "MaximumRetryCount": 0},
                "PidMode": "", "IpcMode": "private", "UsernsMode": "",
                "Mounts": [{"Type": "bind", "Source": str(source), "Target": str(source),
                            "ReadOnly": not writable} for source, writable in mounts],
            },
            "Mounts": [{"Type": "bind", "Source": str(source), "Destination": str(source),
                        "RW": writable} for source, writable in mounts],
            "NetworkSettings": {"Networks": {"none": {}}, "Ports": {}},
            "State": {"Status": "created", "Running": False},
        }

    def fake_pair(self, *, intervals=None, mutate_manifest=False, mutate_runner=False,
                  bad_result=None, on_start=None):
        """Run real outer control flow against local files and fake Docker clients."""
        intervals = intervals or (
            ("2026-10-01T00:00:00.000000000Z", "2026-10-01T00:00:03.000000000Z"),
            ("2026-10-01T00:00:01.000000000Z", "2026-10-01T00:00:04.000000000Z"),
        )
        with tempfile.TemporaryDirectory(prefix="offline-dual-pilot-") as directory:
            root = Path(directory)
            manifests = [root / "case-a.json", root / "case-b.json"]
            for index, path in enumerate(manifests):
                path.write_text(json.dumps({"case_id": "case-" + str(index), "revision": 1}))
            runner = root / "runner.py"
            runner.write_text("# admitted runner\n")
            runtime_dir = root / "runtime-source"
            runtime_dir.mkdir()
            runtime_runner = runtime_dir / "runner.py"
            runtime_runner.write_bytes(runner.read_bytes())
            sealed_manifests = []
            for index, path in enumerate(manifests):
                sealed = runtime_dir / ("manifest-%d.json" % index)
                sealed.write_bytes(path.read_bytes())
                sealed_manifests.append(sealed)
            lock_path = root / "local.lock"
            lock_path.touch()
            nonce = "f" * 32
            cids = ("a" * 64, "b" * 64)
            created = {}
            inspections = {cid: 0 for cid in cids}
            handlers = {signal.SIGINT: signal.default_int_handler,
                        signal.SIGTERM: signal.SIG_DFL, signal.SIGHUP: signal.SIG_DFL}
            started = 0

            def fake_lock():
                fd = os.open(lock_path, os.O_RDONLY)
                pilot.fcntl.flock(fd, pilot.fcntl.LOCK_EX)
                return fd

            def fake_docker(*args, **kwargs):
                if args[:2] == ("image", "inspect"):
                    image = {"Id": pilot.IMAGE, "Architecture": "amd64", "Os": "linux",
                             "Config": {"Env": [], "Labels": {}}}
                    return SimpleNamespace(stdout=json.dumps([image]).encode(), returncode=0)
                if args[0] == "create":
                    name = next(value.split("=", 1)[1] for value in args if value.startswith("--name="))
                    index = int(name.rsplit("-", 1)[1])
                    parent = Path(next(value.split("=", 1)[1] for value in args
                                       if value.startswith("--workdir=")))
                    selected_manifest = Path(args[args.index("--manifest") + 1])
                    created[cids[index]] = (name, parent, selected_manifest, index,
                                            Path(args[args.index("-B") + 1]))
                    return SimpleNamespace(stdout=(cids[index] + "\n").encode(), returncode=0)
                if args[0] == "logs":
                    return SimpleNamespace(stdout=b"offline diagnostic log\n", returncode=0)
                self.fail("unexpected Docker call in offline test: " + repr(args))

            def fake_inspect(cid):
                name, parent, manifest, index, selected_runner = created[cid]
                row = self.created_row(cid, name, nonce, pilot.SLOTS[index], parent,
                                       manifest, selected_runner, runtime_dir)
                inspections[cid] += 1
                if inspections[cid] > 1:
                    row["State"] = {"Status": "exited", "Running": False, "ExitCode": 0,
                                    "OOMKilled": False, "StartedAt": intervals[index][0],
                                    "FinishedAt": intervals[index][1], "Error": ""}
                return row

            def fake_start(argv, **kwargs):
                nonlocal started
                cid = argv[-1]
                index = created[cid][3]
                self.assertEqual(kwargs["stdout"], pilot.subprocess.DEVNULL)
                self.assertEqual(kwargs["stderr"], pilot.subprocess.DEVNULL)
                parent = created[cid][1]
                attempt = parent / "attempt"
                attempt.mkdir()
                record = {"schema_version": 1, "kind": "native-diagnostic-result",
                          "case_id": "case-" + str(index), "status": "PROTOCOL_PASS",
                          "application_acceptance": False, "mckernel_application_executed": False,
                          "cleanup": {"reaped": True, "errors": []}, "capture_errors": []}
                if index == 0 and bad_result == "capture":
                    record["capture_errors"] = [{"phase": "host-capture", "error": "failed"}]
                if index == 0 and bad_result == "executed":
                    record["mckernel_application_executed"] = True
                (attempt / "result.json").write_text(json.dumps(record))
                started += 1
                if started == 1:
                    if mutate_manifest:
                        manifests[0].write_text(json.dumps({"case_id": "case-0", "revision": 2}))
                    if mutate_runner:
                        runner.write_text("# changed runner\n")
                    if on_start is not None:
                        on_start(handlers)
                return FinishedClient()

            def set_handler(number, handler):
                previous = handlers[number]
                handlers[number] = handler
                return previous

            with ExitStack() as stack:
                stack.enter_context(patch.object(pilot, "SCRATCH", root))
                stack.enter_context(patch.object(pilot, "RUNNER", runner))
                stack.enter_context(patch.object(pilot, "SOURCE_FILES", (runner,)))
                stack.enter_context(patch.object(pilot, "prepare_source_snapshot",
                                                return_value=(runtime_dir,
                                                              {str(path): pilot.sha(path)
                                                               for path in runtime_dir.iterdir()},
                                                              sealed_manifests)))
                stack.enter_context(patch.object(pilot, "uuid", SimpleNamespace(uuid4=lambda: SimpleNamespace(hex=nonce))))
                stack.enter_context(patch.object(pilot, "load_manifest", side_effect=lambda path: {
                    "case_id": "case-" + str(manifests.index(Path(path)))}))
                stack.enter_context(patch.object(pilot, "admit", return_value={"offline": True}))
                stack.enter_context(patch.object(pilot, "acquire_lock", side_effect=fake_lock))
                stack.enter_context(patch.object(pilot, "docker", side_effect=fake_docker))
                stack.enter_context(patch.object(pilot, "inspect_one", side_effect=fake_inspect))
                stack.enter_context(patch.object(pilot.subprocess, "Popen", side_effect=fake_start))
                cleanup = stack.enter_context(patch.object(pilot, "cleanup"))
                stack.enter_context(patch.object(pilot.signal, "getsignal", side_effect=handlers.get))
                stack.enter_context(patch.object(pilot.signal, "signal", side_effect=set_handler))
                stack.enter_context(patch.dict(pilot.os.environ, {
                    "SUDO_ASKPASS": "/offline/askpass", "MCKERNEL_OS_SUDO_CREDENTIAL": "offline"}))
                try:
                    outcome = pilot.run_guests(manifests)
                except BaseException as exc:
                    outcome = exc
                published = list(root.glob("dual-guest-*/summary.json"))
                return outcome, cleanup.call_count, bool(published)

    def test_create_has_disjoint_cpu_and_memory_caps(self):
        a = pilot.create_args("guest-a", "a" * 32, pilot.SLOTS[0], Path("/tmp/guest-a"), Path("/tmp/a.json"))
        b = pilot.create_args("guest-b", "a" * 32, pilot.SLOTS[1], Path("/tmp/guest-b"), Path("/tmp/b.json"))
        self.assertIn("--cpuset-cpus=2,3", a)
        self.assertIn("--cpuset-cpus=4,5", b)
        for args in (a, b):
            for expected in ("--cpus=2", "--memory=7g", "--memory-swap=7g", "--pids-limit=256",
                             "--read-only", "--network=none", "--cap-drop=ALL",
                             "--log-driver=local", "--log-opt=max-size=5m", "--log-opt=max-file=2"):
                self.assertIn(expected, args)
            self.assertIn(pilot.IMAGE, args)

    def test_capacity_refuses_overcommit_and_low_disk(self):
        with patch.object(pilot.os, "sched_getaffinity", return_value={0, 2, 3, 4, 5, 6, 7}), \
             patch.object(pilot, "mem_available", return_value=17 * pilot.GIB), \
             patch.object(pilot.shutil, "disk_usage", return_value=SimpleNamespace(free=40 * pilot.GIB)):
            with self.assertRaisesRegex(pilot.PilotError, "reserve"):
                pilot.admit(2)
            self.assertEqual(pilot.admit(1)["cpusets"], ["2,3", "4,5"])
        with patch.object(pilot.os, "sched_getaffinity", return_value={0, 2, 3, 4, 5, 6, 7}), \
             patch.object(pilot, "mem_available", return_value=30 * pilot.GIB), \
             patch.object(pilot.shutil, "disk_usage", return_value=SimpleNamespace(free=11 * pilot.GIB)):
            with self.assertRaisesRegex(pilot.PilotError, "free-space"):
                pilot.admit(2)

    def test_owner_lookup_requires_matching_name_and_label(self):
        cid = "a" * 64
        def matched(*args, **kwargs):
            return SimpleNamespace(stdout=(cid + "\n").encode())
        with patch.object(pilot, "docker", side_effect=matched):
            self.assertEqual(pilot.lookup("owned", "b" * 32), cid)
        responses = [SimpleNamespace(stdout=(cid + "\n").encode()), SimpleNamespace(stdout=b"")]
        with patch.object(pilot, "docker", side_effect=responses):
            with self.assertRaisesRegex(pilot.PilotError, "mismatch"):
                pilot.lookup("owned", "b" * 32)

    def test_owned_census_finds_renamed_guest_and_refuses_foreign_reserved_name(self):
        cid, nonce = "a" * 64, "b" * 32
        responses = [SimpleNamespace(stdout=(cid + "\n").encode()),
                     SimpleNamespace(stdout=b""), SimpleNamespace(stdout=b"")]
        row = {"Id": cid, "Name": "/renamed", "Config": {"Labels": {
            "mckernel.dual-pilot.owner": nonce}}}
        with patch.object(pilot, "docker", side_effect=responses), \
             patch.object(pilot, "inspect_one", return_value=row):
            self.assertEqual(pilot.owned_census(["guest-0", "guest-1"], nonce), [cid])
        responses = [SimpleNamespace(stdout=b""), SimpleNamespace(stdout=(cid + "\n").encode())]
        with patch.object(pilot, "docker", side_effect=responses):
            with self.assertRaisesRegex(pilot.PilotError, "reserved name"):
                pilot.owned_census(["guest-0"], nonce)

    def test_cleanup_requires_two_empty_censuses_after_removal(self):
        cid = "a" * 64
        with patch.object(pilot, "owned_census", side_effect=[[cid], [], []]) as census, \
             patch.object(pilot, "docker", return_value=SimpleNamespace(returncode=0)) as docker, \
             patch.object(pilot.time, "sleep"):
            pilot.cleanup(["guest-0", "guest-1"], "b" * 32)
        self.assertEqual(census.call_count, 3)
        self.assertEqual([call.args[0] for call in docker.call_args_list], ["stop", "rm"])

    def test_cleanup_retries_malformed_census(self):
        malformed = json.JSONDecodeError("bad", "{", 0)
        with patch.object(pilot, "owned_census", side_effect=[malformed, [], []]) as census, \
             patch.object(pilot.time, "sleep"):
            pilot.cleanup(["guest-0", "guest-1"], "b" * 32)
        self.assertEqual(census.call_count, 3)

    def test_created_profile_rejects_exact_mount_and_identity_drift(self):
        cid, nonce, parent, manifest = "a" * 64, "b" * 32, Path("/tmp/guest"), Path("/tmp/a.json")
        row = self.created_row(cid, "guest", nonce, (2, 3), parent, manifest)
        pilot.verify_created(row, cid, "guest", (2, 3), parent, nonce, manifest)
        for label, change in (
            ("memory", lambda value: value["HostConfig"].__setitem__("MemorySwap", pilot.CONTAINER_MEMORY + 1)),
            ("wrong bind source", lambda value: value["Mounts"][2].__setitem__("Source", "/tmp/other")),
            ("extra writable bind", lambda value: value["Mounts"].append(
                {"Type": "bind", "Source": "/tmp/other", "Destination": "/other", "RW": True})),
            ("missing no-new-privileges", lambda value: value["HostConfig"].__setitem__("SecurityOpt", [])),
            ("host PID namespace", lambda value: value["HostConfig"].__setitem__("PidMode", "host")),
            ("host IPC namespace", lambda value: value["HostConfig"].__setitem__("IpcMode", "host")),
            ("added capability", lambda value: value["HostConfig"].__setitem__("CapAdd", ["SYS_ADMIN"])),
            ("wrong user", lambda value: value["Config"].__setitem__("User", "0:0")),
            ("wrong command", lambda value: value["Config"].__setitem__("Cmd", ["-c", "pass"])),
            ("wrong label", lambda value: value["Config"]["Labels"].__setitem__(
                "mckernel.dual-pilot.owner", "c" * 32)),
        ):
            with self.subTest(label=label):
                changed = copy.deepcopy(row)
                change(changed)
                with self.assertRaises(pilot.PilotError):
                    pilot.verify_created(changed, cid, "guest", (2, 3), parent, nonce, manifest)

    def test_execution_requires_two_guests(self):
        with patch.dict(pilot.os.environ, {"SUDO_ASKPASS": "/offline/askpass",
                                                "MCKERNEL_OS_SUDO_CREDENTIAL": "offline"}):
            with self.assertRaisesRegex(pilot.PilotError, "two manifests required"):
                pilot.run_guests([Path("/tmp/one-manifest.json")])

    def test_overlap_requires_positive_measured_interval(self):
        def state(start, finish):
            return {"StartedAt": "2026-10-01T00:00:%02dZ" % start,
                    "FinishedAt": "2026-10-01T00:00:%02dZ" % finish}

        self.assertEqual(pilot.overlap_seconds([state(0, 3), state(1, 4)]), 2.0)
        for pair in ([state(0, 1), state(1, 3)], [state(0, 1), state(2, 3)]):
            with self.subTest(pair=pair), self.assertRaises(pilot.PilotError):
                pilot.overlap_seconds(pair)

    def test_pair_pass_requires_actual_overlap(self):
        passing, cleanup_count, published = self.fake_pair()
        self.assertIsInstance(passing, dict, passing)
        self.assertEqual(passing["status"], "DIAGNOSTIC_PASS")
        self.assertGreaterEqual(passing["observed_overlap_seconds"], 1.0)
        self.assertEqual(cleanup_count, 1)
        self.assertTrue(published)
        disjoint = (
            ("2026-10-01T00:00:00.000000000Z", "2026-10-01T00:00:01.000000000Z"),
            ("2026-10-01T00:00:02.000000000Z", "2026-10-01T00:00:03.000000000Z"),
        )
        outcome, cleanup_count, published = self.fake_pair(intervals=disjoint)
        self.assertIsInstance(outcome, pilot.PilotError, outcome)
        self.assertRegex(str(outcome), "overlap")
        self.assertEqual(cleanup_count, 1)
        self.assertFalse(published)

    def test_pair_pass_rejects_inconsistent_inner_result(self):
        for bad_result in ("capture", "executed"):
            with self.subTest(bad_result=bad_result):
                outcome, cleanup_count, published = self.fake_pair(bad_result=bad_result)
                self.assertIsInstance(outcome, pilot.PilotError, outcome)
                self.assertRegex(str(outcome), "inner|capture|result")
                self.assertEqual(cleanup_count, 1)
                self.assertFalse(published)

    def test_pair_pass_rejects_manifest_hash_drift(self):
        outcome, cleanup_count, published = self.fake_pair(mutate_manifest=True)
        self.assertIsInstance(outcome, pilot.PilotError, outcome)
        self.assertRegex(str(outcome), "input/source changed")
        self.assertEqual(cleanup_count, 1)
        self.assertFalse(published)

    def test_pair_pass_rejects_runner_source_hash_drift(self):
        outcome, cleanup_count, published = self.fake_pair(mutate_runner=True)
        self.assertIsInstance(outcome, pilot.PilotError, outcome)
        self.assertRegex(str(outcome), "input/source changed")
        self.assertEqual(cleanup_count, 1)
        self.assertFalse(published)

    def test_term_and_hup_interrupt_pair_and_cleanup(self):
        for number in (signal.SIGTERM, signal.SIGHUP):
            with self.subTest(signal=number):
                armed = []

                def interrupt(handlers):
                    handler = handlers[number]
                    if callable(handler):
                        armed.append(True)
                        handler(number, None)

                outcome, cleanup_count, published = self.fake_pair(on_start=interrupt)
                self.assertTrue(armed, "termination handler must be armed before guest start")
                self.assertIsInstance(outcome, BaseException, outcome)
                self.assertEqual(cleanup_count, 1)
                self.assertFalse(published)


if __name__ == "__main__":
    unittest.main()
