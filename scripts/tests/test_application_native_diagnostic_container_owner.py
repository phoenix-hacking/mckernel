import copy
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import signal
import tempfile
import threading
import types
import unittest
from unittest import mock

SOURCE = Path(__file__).parents[1] / "application-tests/native_diagnostic_container_owner.py"
spec = importlib.util.spec_from_file_location("native_owner", SOURCE)
owner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(owner)
BOUND_MANIFEST = owner.bound_manifest
CID = "a" * 64
NONCE = "b" * 32
PINNED_QEMU_VERSION_STDOUT = (
    b"QEMU emulator version 10.1.0 (qemu-kvm-10.1.0-16.el10_2.5)\n"
    b"Copyright (c) 2003-2025 Fabrice Bellard and the QEMU Project developers\n"
)


def result(out=b"", code=0, err=b""):
    response = subprocess.CompletedProcess([], code, out, err)
    response.command_record = {"pid": os.getpid(), "pgid": os.getpid(),
                               "sid": os.getsid(os.getpid()), "proc_starttime": owner._proc_starttime(os.getpid()),
                               "reaped": True, "returncode": code}
    return response


def image():
    return {"Id": owner.IMAGE, "Architecture": "amd64", "Os": "linux",
            "Config": {"Env": ["PATH=/usr/bin:/bin"], "Labels": None, "Shell": ["/bin/bash"]},
            "RootFS": {"Type": "layers", "Layers": ["sha256:" + "c" * 64]}}


def container(obj):
    mounts = [(owner.REPO, True), (owner.SCRATCH, True), (str(obj.parent), False)]
    config = {"Hostname": CID[:12], "Domainname": "", "User": "1000:1000", "Image": owner.IMAGE,
              "WorkingDir": str(obj.parent), "Entrypoint": ["/usr/bin/python3"],
              "Cmd": ["-B", owner.SELF, "--inside", "--owner-sha256", obj.owner_sha,
                      "--attempt-parent", str(obj.parent), "--nonce", NONCE],
              "Labels": {"mckernel.native-diagnostic.owner": NONCE}, "Tty": False, "OpenStdin": False,
              "StdinOnce": False, "AttachStdin": False, "AttachStdout": True, "AttachStderr": True,
              "Env": ["PATH=/usr/bin:/bin", "HOME=/tmp", "TMPDIR=/tmp", "PYTHONDONTWRITEBYTECODE=1"]}
    host = {"NetworkMode": "none", "Privileged": False, "ReadonlyRootfs": True, "CapDrop": ["ALL"],
            "SecurityOpt": ["no-new-privileges"], "Memory": 12884901888, "MemorySwap": 12884901888,
            "NanoCpus": 4000000000, "CpusetCpus": "2-5", "PidsLimit": 512, "CgroupParent": "/mckernel-dev",
            "Init": True, "PidMode": "", "UTSMode": "", "UsernsMode": "", "IpcMode": "private", "Runtime": "runc",
            "AutoRemove": False, "PublishAllPorts": False, "RestartPolicy": {"Name": "no", "MaximumRetryCount": 0},
            "Tmpfs": {"/tmp": "rw,nodev,nosuid,size=256m"}, "ShmSize": 67108864, "OomScoreAdj": 0,
            "CgroupnsMode": "host", "LogConfig": {"Type": "json-file", "Config": {}},
            "Ulimits": [{"Hard": 0, "Name": "core", "Soft": 0}, {"Hard": 4096, "Name": "nofile", "Soft": 4096}],
            "MaskedPaths": ["/proc/kcore", "/proc/keys", "/proc/latency_stats", "/proc/timer_list", "/proc/scsi", "/sys/firmware"],
            "ReadonlyPaths": ["/proc/bus", "/proc/fs", "/proc/irq", "/proc/sys", "/proc/sysrq-trigger"],
            "Mounts": [{"Type": "bind", "Source": p, "Target": p, "ReadOnly": ro} for p, ro in mounts]}
    return {"Id": CID, "Name": "/" + obj.name, "Image": owner.IMAGE, "Config": config, "HostConfig": host,
            "Path": "/usr/bin/python3", "Args": config["Cmd"],
            "Mounts": [{"Type": "bind", "Source": p, "Destination": p, "RW": not ro, "Propagation": "rprivate"} for p, ro in mounts],
            "NetworkSettings": {"Networks": {"none": {}}, "Ports": {}},
            "State": {"Status": "created", "Running": False, "Paused": False, "Restarting": False,
                      "OOMKilled": False, "Dead": False, "Error": "", "ExitCode": 0}}


class Fake:
    def __init__(self):
        self.children = owner.CommandLedger()
        self.calls = []
        self.exists = False
        self.started = False
        self.change = lambda row: None
        self.image_change = lambda row: None
        self.start_failure = None
        self.cleanup_failure = False
        self.create_cid = CID
        self.lookup_cid = CID
        self.wait = b"0\n"
        self.start_code = 0
        self.stdout = None
        self.record_change = lambda row: None
        self.after_start = lambda row: None

    def call(self, argv, *, timeout):
        assert argv[:3] == ["/usr/bin/sudo", "-A", "/usr/bin/docker"]
        assert timeout > 0
        self.calls.append((argv, timeout))
        cmd = argv[3]
        if cmd == "ps":
            return result((self.lookup_cid + "\n").encode() if self.exists else b"")
        if cmd == "image":
            row = image()
            self.image_change(row)
            return result(json.dumps([row]).encode())
        if cmd == "create":
            self.exists = True
            return result((self.create_cid + "\n").encode())
        if cmd == "inspect":
            row = container(self.obj)
            self.change(row)
            if self.started:
                row["State"]["Status"] = "exited"
                self.after_start(row)
            return result(json.dumps([row]).encode())
        if cmd == "start":
            self.started = True
            if self.start_failure is not None:
                raise self.start_failure
            self.obj.attempt.mkdir(mode=0o700)
            process_identity = {"pid": 12345, "pgid": 12345, "sid": 12345,
                                "starttime_ticks": 77}
            qemu_evidence = {"argv": ["/usr/libexec/qemu-kvm", "-qmp", "unix:test"],
                             **process_identity, "returncode": 0}
            record = {"status": "PROTOCOL_PASS", "application_acceptance": False,
                      "mckernel_application_executed": False, "case_id": "x",
                      "cleanup": {"reaped": True, "errors": []}, "capture_errors": [],
                      "admitted_qemu_argv": qemu_evidence["argv"],
                      "qemu_evidence": qemu_evidence,
                      "observation": {"serial": "SERIAL", "debugcon": "DEBUG", "teardown": True,
                                      "process_identity": process_identity,
                                      "qemu_evidence": qemu_evidence}}
            self.record_change(record)
            (self.obj.attempt / "result.json").write_text(json.dumps(record))
            for name, data in {"serial.log": b"SERIAL", "debugcon.log": b"DEBUG", "qemu.stdout": b"",
                               "qemu.stderr": b"", "qmp.transcript.json": b"[]"}.items():
                (self.obj.attempt / name).write_bytes(data)
            out = self.stdout if self.stdout is not None else (owner._json({"attempt": self.obj.attempt.name,
                   "case_id": "x", "status": "PROTOCOL_PASS"}) + "\n").encode()
            return result(out, code=self.start_code)
        if cmd == "wait":
            return result(self.wait)
        if cmd == "rm":
            if self.cleanup_failure:
                return result(code=1)
            self.exists = False
        return result()


class OwnerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.parent = self.root / "attempts"
        self.parent.mkdir(mode=0o700)
        self.patch("SCRATCH", str(self.root))
        self.fake = Fake()
        self.obj = owner.DiagnosticOwner(str(self.parent), backend=self.fake, nonce=NONCE)
        self.fake.obj = self.obj
        self.elapsed = [0.0]
        self.obj.clock = lambda: self.elapsed[0]
        self.obj.sleep = lambda duration: self.elapsed.__setitem__(0, self.elapsed[0] + duration)
        manifest = {"case_id": "x"}
        self.diagnostic = types.SimpleNamespace(evaluate=lambda m, o: {
            "status": "PROTOCOL_PASS", "application_acceptance": False, "mckernel_application_executed": False,
            "case_id": "x", "observation": o},
            expected_qemu_argv=lambda manifest, attempt: ["/usr/libexec/qemu-kvm", "-qmp", "unix:test"])
        patch = mock.patch.object(owner, "bound_manifest", return_value=(self.diagnostic, manifest))
        self.bound = patch.start()
        self.addCleanup(patch.stop)
        image_path = self.root / "image.json"
        image_path.write_text(json.dumps([image()]))
        self.patch("IMAGE_RECORD", str(image_path))
        self.patch("IMAGE_RECORD_SHA256", owner._digest(image_path))
        cg = self.root / "cgroup"
        cg.write_text("512\n")
        self.patch("CGROUP", {str(cg): "512"})
        # The only host operation substituted is lock acquisition. Release
        # still closes a real temporary descriptor after verified absence.
        def acquire():
            self.obj.lock = os.open(str(self.root / "lock"), os.O_CREAT | os.O_RDWR, 0o600)
            info = os.fstat(self.obj.lock)
            self.obj.lock_identity = {"dev": info.st_dev, "ino": info.st_ino,
                                      "mode": owner.stat.S_IMODE(info.st_mode), "nlink": info.st_nlink,
                                      "uid": info.st_uid, "gid": info.st_gid}
        self.obj._acquire = acquire
        self.addCleanup(self.close_lock)

    def close_lock(self):
        if self.obj.lock is not None:
            os.close(self.obj.lock)
            self.obj.lock = None

    def patch(self, name, value):
        patch = mock.patch.object(owner, name, value)
        patch.start()
        self.addCleanup(patch.stop)

    def fails(self, pattern=None):
        with self.assertRaises(BaseException) as caught:
            self.obj.run()
        if pattern:
            self.assertIn(pattern, str(caught.exception))
        return caught.exception

    def test_positive_lifecycle_and_durable_evidence(self):
        self.assertEqual(self.obj.run()["status"], "PROTOCOL_PASS")
        self.assertFalse(self.fake.exists)
        self.assertIsNone(self.obj.lock)
        create = next(argv for argv, _ in self.fake.calls if argv[3] == "create")
        self.assertEqual(create[:3], owner.PREFIX)
        self.assertIn("--inside", create)
        self.assertIn("--network=none", create)
        self.assertIn("--cpuset-cpus=2-5", create)
        self.assertEqual([argv[3] for argv, _ in self.fake.calls if argv[3] in ("stop", "kill", "rm")], ["stop", "kill", "rm"])
        for name in ("inner-result.json", "capture-bindings.json", "state.json", "result.json", "serial.log"):
            self.assertTrue((self.obj.evidence / name).is_file(), name)
        self.assertNotIn(self.obj.parent, self.obj.evidence.parents)
        report = json.loads((self.obj.evidence / "result.json").read_text())
        self.assertTrue(report["absence_verified"])
        self.assertFalse(report["application_acceptance"])
        owner_record = json.loads((self.obj.evidence / "owner.json").read_text())
        self.assertEqual(owner_record["outer"]["pid"], os.getpid())
        self.assertEqual(owner_record["outer"]["pgid"], os.getpgid(os.getpid()))
        self.assertEqual(owner_record["outer"]["sid"], os.getsid(os.getpid()))
        self.assertIsInstance(owner_record["outer"]["proc_starttime"], int)
        self.assertEqual(set(owner_record["lock"]), {"dev", "ino", "mode", "nlink", "uid", "gid"})
        self.assertEqual(owner_record["lock"]["mode"], 0o600)
        self.assertEqual(owner_record["cgroup_profile"], {str(self.root / "cgroup"): "512"})

    def test_outer_rejects_qemu_evidence_argv_not_equal_to_admitted_plan(self):
        def mismatch(record):
            record["qemu_evidence"]["argv"] = ["/usr/libexec/qemu-kvm", "-qmp", "unix:wrong"]
            record["observation"]["qemu_evidence"] = record["qemu_evidence"]
        self.fake.record_change = mismatch
        self.fails("QEMU evidence/result join")
        self.assertTrue(self.obj.absent)
        self.assertIsNone(self.obj.lock)

    def test_owner_identity_rejects_malformed_proc_stat(self):
        path = self.root / "stat"
        path.write_bytes((str(os.getpid()) + " (owner) S " + " ".join(["1"] * 18) + " nope\n").encode())
        fd = os.open(path, os.O_RDONLY)
        with mock.patch.object(owner.os, "open", return_value=fd):
            with self.assertRaises(owner.OwnerError):
                owner._proc_starttime(os.getpid())

    def test_owner_record_is_not_written_until_after_retirement(self):
        seen = []
        original = self.obj._write_exclusive
        def writer(path, raw):
            if Path(path).name == "owner.json":
                seen.append((self.obj.absent, self.obj.lock))
            original(path, raw)
        self.obj._write_exclusive = writer
        self.obj.run()
        self.assertEqual(seen, [(True, None)])

    def test_preexisting_exact_owner_is_retired_before_unlock_and_report(self):
        self.fake.exists = True
        self.fails("preexisting owner")
        self.assertFalse(any(a[3] in ("create", "start") for a, _ in self.fake.calls))
        self.assertEqual([a[3] for a, _ in self.fake.calls if a[3] in ("stop", "kill", "rm")], ["stop", "kill", "rm"])
        self.assertFalse(self.fake.exists)
        self.assertTrue(self.obj.absent)
        self.assertIsNone(self.obj.lock)
        report = json.loads((self.obj.evidence / "result.json").read_text())
        self.assertEqual(report["status"], "FAIL")
        self.assertTrue(report["absence_verified"])
        self.assertFalse(report["lease_retained"])

    def test_preexisting_exact_owner_failed_cleanup_retains_lock_without_false_report(self):
        self.fake.exists = True
        self.fake.cleanup_failure = True
        self.fails("preexisting owner")
        self.assertTrue(self.fake.exists)
        self.assertFalse(self.obj.absent)
        self.assertIsNotNone(self.obj.lock)
        self.assertFalse((self.obj.evidence / "result.json").exists())

    def signal_at(self, command, signum):
        original = self.fake.call
        injected = []
        def call(argv, **kwargs):
            response = original(argv, **kwargs)
            if argv[3] == command and not injected:
                injected.append(True)
                signal.raise_signal(signum)
            return response
        self.fake.call = call
        release = self.obj._release
        def checked_release():
            self.assertFalse(self.fake.exists)
            self.assertTrue(self.obj.absent)
            release()
        self.obj._release = checked_release
        old = {sig: signal.getsignal(sig) for sig in owner.OWNER_SIGNALS}
        with self.assertRaises(owner.OwnerSignal) as caught:
            owner.execute_owner(self.obj)
        self.assertIs(caught.exception, self.obj.failure)
        self.assertTrue(injected)
        self.assertFalse(self.fake.exists)
        self.assertIsNone(self.obj.lock)
        self.assertEqual(self.obj.signal_number, signum)
        if command != "image":
            self.assertEqual([a[3] for a, _ in self.fake.calls if a[3] in ("stop", "kill", "rm")], ["stop", "kill", "rm"])
        self.assertEqual({sig: signal.getsignal(sig) for sig in owner.OWNER_SIGNALS}, old)

    def test_sigterm_before_create_verifies_absence(self):
        self.signal_at("image", signal.SIGTERM)

    def test_sigint_during_create_recovers_container(self):
        self.signal_at("create", signal.SIGINT)

    def test_sigterm_during_start_retires_container(self):
        self.signal_at("start", signal.SIGTERM)

    def test_sighup_during_inspect_retires_container(self):
        self.signal_at("inspect", signal.SIGHUP)

    def test_signal_during_cleanup_preserves_prior_failure(self):
        failure = TimeoutError("original")
        self.fake.start_failure = failure
        original_call = self.fake.call
        sent = []
        def call(argv, **kwargs):
            response = original_call(argv, **kwargs)
            if argv[3] == "stop" and not sent:
                sent.append(True)
                signal.raise_signal(signal.SIGINT)
            return response
        self.fake.call = call
        with self.assertRaises(TimeoutError) as caught:
            owner.execute_owner(self.obj)
        self.assertIs(caught.exception, failure)
        self.assertFalse(self.fake.exists)
        self.assertIsNone(self.obj.lock)
        self.assertTrue(self.obj.absent)

    def test_uncertain_removal_never_invokes_evidence_writer(self):
        self.fake.start_failure = TimeoutError("original")
        self.fake.cleanup_failure = True
        writer = mock.Mock(side_effect=AssertionError("writer entered before absence"))
        self.obj._write_exclusive = writer
        self.fails("original")
        writer.assert_not_called()
        self.assertTrue(self.fake.exists)
        self.assertIsNotNone(self.obj.lock)

    def test_signal_during_acquire_is_deferred_until_lock_owned(self):
        acquire = self.obj._acquire
        def signaled_acquire():
            acquire()
            signal.raise_signal(signal.SIGTERM)
        self.obj._acquire = signaled_acquire
        with self.assertRaises(owner.OwnerSignal):
            owner.execute_owner(self.obj)
        self.assertFalse(self.fake.exists)
        self.assertTrue(self.obj.absent)
        self.assertIsNone(self.obj.lock)
        self.assertFalse(any(a[3] == "create" for a, _ in self.fake.calls))

    def command_signal_window(self, phase):
        spawn, waitpid, killpg = owner.os.posix_spawn, owner.os.waitpid, owner.os.killpg
        children, reaps, kills = [], [], []
        injected = []
        def spawning(path, argv, env, **kwargs):
            self.assertEqual(kwargs["setpgroup"], 0)
            self.assertNotIn("setsid", kwargs)
            self.assertNotIn(signal.SIGTERM, kwargs["setsigmask"])
            self.assertIn(signal.SIGTERM, signal.pthread_sigmask(signal.SIG_BLOCK, []))
            pid = spawn(path, argv, env, **kwargs)
            children.append(pid)
            self.assertEqual(os.getpgid(pid), pid)
            self.assertNotEqual(os.getpgid(pid), os.getpgrp())
            if phase == "spawn":
                injected.append(True)
                signal.raise_signal(signal.SIGTERM)
            return pid
        def waiting(pid, flags):
            value = waitpid(pid, flags)
            if value[0]:
                reaps.append(value[0])
                if phase == "reap" and not injected:
                    injected.append(True)
                    signal.raise_signal(signal.SIGTERM)
            return value
        def killing(pid, number):
            kills.append(pid)
            return killpg(pid, number)
        original = self.fake.call
        def call(argv, **kwargs):
            response = original(argv, **kwargs)
            if argv[3] == "start":
                code = "import time; time.sleep(30)" if phase == "spawn" else "print('done')"
                owner.bounded_command(["/usr/bin/python3", "-c", code], 3)
            return response
        self.fake.call = call
        with mock.patch.object(owner.os, "posix_spawn", side_effect=spawning), \
             mock.patch.object(owner.os, "waitpid", side_effect=waiting), \
             mock.patch.object(owner.os, "killpg", side_effect=killing):
            with self.assertRaises(owner.OwnerSignal) as caught:
                owner.execute_owner(self.obj)
        self.assertIs(caught.exception, self.obj.failure)
        self.assertEqual(len(children), 1)
        self.assertEqual(reaps, children)
        self.assertEqual(kills, children if phase == "spawn" else [])
        self.assertTrue(injected)
        self.assertFalse(self.fake.exists)
        self.assertTrue(self.obj.absent)
        self.assertIsNone(self.obj.lock)

    def test_signal_inside_spawn_acquisition_retires_child_once(self):
        self.command_signal_window("spawn")

    def test_signal_after_waitpid_cannot_kill_reused_process_group(self):
        self.command_signal_window("reap")

    def test_create_publication_after_prior_quiet_window_requires_retirement(self):
        original = self.fake.call
        failure = TimeoutError("create reply lost")
        def call(argv, **kwargs):
            response = original(argv, **kwargs)
            if argv[3] == "create":
                self.fake.exists = False
                raise failure
            return response
        self.fake.call = call
        self.assertIs(self.fails(), failure)
        self.assertFalse(self.obj.absent)
        self.assertIsNotNone(self.obj.lock)
        # Multiple quiet windows cannot complete a request at the daemon.
        for _ in range(4):
            self.elapsed[0] += 3
            self.assertFalse(self.obj._cleanup())
            self.assertIsNotNone(self.obj.lock)
        self.fake.exists = True
        self.assertTrue(self.obj._cleanup())
        self.obj._release()
        self.obj._flush()
        self.assertFalse(self.fake.exists)
        self.assertIsNone(self.obj.lock)
        self.assertIs(self.obj.failure, failure)
        self.assertTrue(self.obj.create_completed)
        self.assertEqual([a[3] for a, _ in self.fake.calls if a[3] in ("stop", "kill", "rm")], ["stop", "kill", "rm"])

    def test_never_published_create_retains_lease_without_report(self):
        original = self.fake.call
        def call(argv, **kwargs):
            if argv[3] == "create":
                raise TimeoutError("request completion unknown")
            return original(argv, **kwargs)
        self.fake.call = call
        self.fails("request completion unknown")
        for elapsed in (2, 15, 60, 3600, 86400):
            self.elapsed[0] = elapsed
            self.assertFalse(self.obj._cleanup())
            self.assertFalse(self.obj.absent)
            self.assertIsNotNone(self.obj.lock)
            self.assertFalse(self.obj.create_completed)
            with self.assertRaises(owner.OwnerError):
                self.obj._release()
            self.assertFalse((self.obj.evidence / "result.json").exists())

    def test_cleanup_deadline_after_empty_lookup_cannot_publish_absence(self):
        self.obj._acquire()
        self.obj.absent = True  # A new cleanup must invalidate prior state.
        calls = []
        def lookup():
            self.assertFalse(self.obj.absent)
            calls.append(True)
            if len(calls) == 2:
                self.elapsed[0] = 16
            return None
        self.obj._lookup = lookup
        self.assertFalse(self.obj._cleanup())
        self.assertFalse(self.obj.absent)
        self.assertIsNotNone(self.obj.lock)
        with self.assertRaises(owner.OwnerError):
            self.obj._release()

    def test_cleanup_signal_after_empty_lookup_cannot_publish_absence(self):
        self.obj._acquire()
        self.obj.absent = True
        calls = []
        failure = owner.OwnerSignal("cleanup boundary")
        def lookup():
            self.assertFalse(self.obj.absent)
            calls.append(True)
            if len(calls) == 2:
                raise failure
            return None
        self.obj._lookup = lookup
        self.assertFalse(self.obj._cleanup())
        self.assertIs(self.obj.failure, failure)
        self.assertFalse(self.obj.absent)
        self.assertIsNotNone(self.obj.lock)
        with self.assertRaises(owner.OwnerError):
            self.obj._release()

    def test_pending_local_client_prevents_lookup_release_and_report(self):
        self.obj._acquire()
        child = owner.CommandChild()
        child.pid = 987654321
        self.fake.children.pending.add(child)
        failure = OSError("wait ownership unavailable")
        with mock.patch.object(owner.os, "killpg"), \
             mock.patch.object(owner.os, "waitpid", side_effect=failure):
            self.assertFalse(self.obj._cleanup())
        self.assertEqual(self.fake.calls, [])
        self.assertFalse(self.obj.absent)
        self.assertIn(child, self.fake.children.pending)
        self.assertIn("OSError", self.obj.secondary)
        with self.assertRaises(owner.OwnerError):
            self.obj._release()
        with mock.patch.object(owner.os, "killpg") as kill, \
             mock.patch.object(owner.os, "waitpid", return_value=(child.pid, 0)):
            self.assertTrue(self.obj._cleanup())
            self.fake.children.retire(child)
            # An unresolved child without a captured identity is never
            # signaled: fail closed against stale PID/process-group reuse.
            kill.assert_not_called()
        self.assertTrue(child.reaped)
        self.obj._release()
        self.assertIsNone(self.obj.lock)

    def blocking_writer(self, phase):
        original_call = self.fake.call
        failure = TimeoutError("original " + phase)
        if phase in ("create", "start"):
            def failing_call(argv, **kwargs):
                response = original_call(argv, **kwargs)
                if argv[3] == phase:
                    raise failure
                return response
            self.fake.call = failing_call
        else:
            self.fake.start_failure = failure
        entered, release = threading.Event(), threading.Event()
        write = self.obj._write_exclusive
        seen = []
        def blocked(path, raw):
            self.assertFalse(self.fake.exists)
            self.assertTrue(self.obj.absent)
            self.assertIsNone(self.obj.lock)
            if not seen:
                seen.append(True)
                entered.set()
                if not release.wait(3):
                    raise RuntimeError("test writer release timed out")
            write(path, raw)
        self.obj._write_exclusive = blocked
        caught = []
        def run():
            try:
                self.obj.run()
            except BaseException as exc:
                caught.append(exc)
        worker = threading.Thread(target=run)
        worker.start()
        try:
            self.assertTrue(entered.wait(3))
            self.assertFalse(self.fake.exists)
            self.assertTrue(self.obj.absent)
            self.assertIsNone(self.obj.lock)
            self.assertEqual([a[3] for a, _ in self.fake.calls if a[3] in ("stop", "kill", "rm")], ["stop", "kill", "rm"])
        finally:
            release.set()
            worker.join(3)
        self.assertFalse(worker.is_alive())
        self.assertEqual(len(caught), 1)
        self.assertIs(caught[0], failure)

    def test_blocked_writer_cannot_delay_create_failure_cleanup(self):
        self.blocking_writer("create")

    def test_blocked_writer_cannot_delay_start_failure_cleanup(self):
        self.blocking_writer("start")

    def test_blocked_writer_cannot_delay_cleanup_commands(self):
        self.blocking_writer("cleanup")

    def test_reentrant_writer_fails_only_after_retirement(self):
        failure = TimeoutError("original")
        self.fake.start_failure = failure
        def reenter(path, raw):
            self.assertFalse(self.fake.exists)
            self.assertIsNone(self.obj.lock)
            self.obj._flush()
        self.obj._write_exclusive = reenter
        self.assertIs(self.fails(), failure)
        self.assertFalse(self.fake.exists)

    def test_hostile_exception_hooks_never_run_before_retirement(self):
        calls = []
        class HostileMeta(type):
            def __getattribute__(cls, name):
                calls.append("metaclass")
                raise RuntimeError("metaclass hook")
        class Hostile(BaseException, metaclass=HostileMeta):
            def __repr__(self):
                calls.append("repr")
                threading.Event().wait(0.1)
                self.obj._cleanup()
                raise RuntimeError("repr hook")
            def __str__(self):
                calls.append("str")
                raise RuntimeError("str hook")
            @property
            def args(self):
                calls.append("args")
                raise RuntimeError("args hook")
            def __getattribute__(self, name):
                calls.append("attribute")
                raise RuntimeError("attribute hook")
        failure = Hostile()
        self.fake.start_failure = failure
        # unittest exception classification may consult __class__; keep the
        # original exception comparison outside assertion context helpers.
        try:
            self.obj.run()
        except BaseException as caught:
            self.assertIs(caught, failure)
        else:
            self.fail("hostile failure was lost")
        self.assertEqual(calls, [])
        self.assertFalse(self.fake.exists)
        self.assertIsNone(self.obj.lock)
        self.assertEqual([a[3] for a, _ in self.fake.calls if a[3] in ("stop", "kill", "rm")], ["stop", "kill", "rm"])

    def test_short_create_cid_fails_and_recovers_by_exact_identity(self):
        self.fake.create_cid = "abc"
        self.fails("full container ID")
        self.assertFalse(self.fake.exists)

    def test_short_lookup_id_rejects(self):
        self.fake.exists = True
        self.fake.lookup_cid = "abc"
        self.fails("full unique container ID")
        self.assertFalse(any(a[3] in ("create", "start", "rm") for a, _ in self.fake.calls))

    def test_changed_cid_retains_lease(self):
        original = self.fake.call
        def call(argv, **kwargs):
            response = original(argv, **kwargs)
            if argv[3] == "create":
                self.fake.lookup_cid = "d" * 64
            return response
        self.fake.call = call
        self.fails("container ID changed")
        self.assertIsNotNone(self.obj.lock)
        self.assertFalse(any(a[3] == "rm" for a, _ in self.fake.calls))

    def test_profile_drift_matrix(self):
        changes = [
            ("name", lambda r: r.update(Name="/other")),
            ("label", lambda r: r["Config"]["Labels"].update({"mckernel.native-diagnostic.owner": "other"})),
            ("image", lambda r: r.update(Image="sha256:" + "0" * 64)),
            ("config user", lambda r: r["Config"].update(User="0")),
            ("env", lambda r: r["Config"]["Env"].append("LD_PRELOAD=/evil")),
            ("cmd", lambda r: r["Config"].update(Cmd=["evil"])),
            ("entrypoint", lambda r: r.update(Path="/bin/sh")),
            ("unknown config", lambda r: r["Config"].update(Unexpected=True)),
            ("mount source", lambda r: r["Mounts"][0].update(Source="/")),
            ("mount readonly", lambda r: r["Mounts"][1].update(RW=True)),
            ("requested mount", lambda r: r["HostConfig"]["Mounts"][0].update(ReadOnly=False)),
            ("memory", lambda r: r["HostConfig"].update(Memory=1)),
            ("cpu", lambda r: r["HostConfig"].update(CpusetCpus="0-7")),
            ("pids", lambda r: r["HostConfig"].update(PidsLimit=513)),
            ("swap", lambda r: r["HostConfig"].update(MemorySwap=-1)),
            ("privileged", lambda r: r["HostConfig"].update(Privileged=True)),
            ("caps", lambda r: r["HostConfig"].update(CapAdd=["SYS_ADMIN"])),
            ("security", lambda r: r["HostConfig"].update(SecurityOpt=[])),
            ("devices", lambda r: r["HostConfig"].update(Devices=[{"PathOnHost": "/dev/kvm"}])),
            ("network", lambda r: r["HostConfig"].update(NetworkMode="host")),
            ("endpoint", lambda r: r["NetworkSettings"]["Networks"]["none"].update(IPAddress="1.2.3.4")),
            ("restart", lambda r: r["HostConfig"].update(RestartPolicy={"Name": "always", "MaximumRetryCount": 0})),
            ("unknown host", lambda r: r["HostConfig"].update(Unexpected=True)),
            ("bool resource", lambda r: r["HostConfig"].update(PidsLimit=True)),
        ]
        for name, change in changes:
            with self.subTest(name=name):
                row = container(self.obj)
                self.obj.container = CID
                change(row)
                with self.assertRaises((owner.OwnerError, TypeError, ValueError)):
                    self.obj._profile(row, image())

    def test_image_config_drift_before_create(self):
        self.fake.image_change = lambda r: r["Config"].update(User="root")
        self.fails("image Config/RootFS drift")
        self.assertFalse(any(a[3] == "create" for a, _ in self.fake.calls))

    def test_image_id_drift_before_create(self):
        self.fake.image_change = lambda r: r.update(Id="sha256:" + "0" * 64)
        self.fails("image Config/RootFS drift")

    def test_image_rootfs_drift_before_create(self):
        self.fake.image_change = lambda r: r["RootFS"].update(Layers=[])
        self.fails("image Config/RootFS drift")

    def test_cgroup_drift_before_docker(self):
        self.patch("CGROUP", {str(self.root / "cgroup"): "513"})
        self.fails("cgroup profile drift")
        self.assertEqual(self.fake.calls, [])

    def test_result_mismatch(self):
        self.fake.stdout = b"fake pass\n"
        self.fails("inner result mismatch")

    def test_inner_cleanup_rejects(self):
        self.fake.record_change = lambda r: r["cleanup"].update(reaped=False)
        self.fails("inner cleanup/result failure")

    def test_capture_errors_reject(self):
        self.fake.record_change = lambda r: r.update(capture_errors=["lost bytes"])
        self.fails("inner cleanup/result failure")

    def test_capture_join_rejects(self):
        self.fake.record_change = lambda r: r["observation"].update(serial="different")
        self.fails("capture observation join")

    def test_wait_nonzero(self):
        self.fake.wait = b"1\n"
        self.fails("container wait status")

    def test_start_nonzero(self):
        self.fake.start_code = 3
        self.fails("docker command failed: start")

    def test_oom_rejects_and_state_retained(self):
        self.fake.after_start = lambda r: r["State"].update(OOMKilled=True)
        self.fails("container state failed")
        self.assertTrue(json.loads((self.obj.evidence / "state.json").read_text())["OOMKilled"])

    def test_timeout_preserves_partial_output_and_cleans(self):
        failure = owner.CommandError("timeout", b"partial", b"diagnostic")
        self.fake.start_failure = failure
        self.assertIs(self.fails(), failure)
        self.assertFalse(self.fake.exists)
        self.assertTrue(any(p.read_bytes() == b"partial" for p in self.obj.evidence.glob("*-start.stdout")))

    def test_failure_writer_does_not_skip_cleanup_or_replace_original(self):
        failure = TimeoutError("original")
        self.fake.start_failure = failure
        original = self.obj._write_exclusive
        def writer(path, data):
            if self.fake.started:
                raise OSError("writer unavailable")
            return original(path, data)
        self.obj._write_exclusive = writer
        self.assertIs(self.fails(), failure)
        self.assertFalse(self.fake.exists)
        self.assertIsNone(self.obj.lock)

    def test_evidence_failure_alone_is_failure(self):
        original = self.obj._write_exclusive
        def writer(path, data):
            if Path(path).name == "inner-result.json":
                raise OSError("writer broken")
            original(path, data)
        self.obj._write_exclusive = writer
        self.fails("writer broken")
        self.assertFalse(self.fake.exists)

    def test_cleanup_failure_retains_lock_and_original_then_recovers(self):
        class Hostile(BaseException):
            def __str__(self):
                raise RuntimeError("hostile str")
            def __repr__(self):
                raise RuntimeError("hostile repr")
        failure = Hostile()
        self.fake.start_failure = failure
        self.fake.cleanup_failure = True
        self.assertIs(self.fails(), failure)
        self.assertIsNotNone(self.obj.lock)
        self.assertFalse(self.obj.absent)
        self.fake.cleanup_failure = False
        self.assertTrue(self.obj._cleanup())
        self.obj._release()
        self.assertIs(self.obj.failure, failure)

    def test_cleanup_timeout_budget_shared_by_commands(self):
        self.obj.evidence.mkdir()
        self.obj.container = CID
        self.fake.exists = True
        clock = [0]
        self.obj.clock = lambda: clock[0]
        original = self.fake.call
        def slow(argv, **kwargs):
            clock[0] += kwargs["timeout"]
            return original(argv, **kwargs)
        self.fake.call = slow
        self.assertFalse(self.obj._cleanup())
        self.assertLessEqual(clock[0], 15)

    def test_private_parent_and_fresh_paths(self):
        self.parent.chmod(0o755)
        self.fails("mode0700")
        self.parent.chmod(0o700)
        self.obj.attempt.mkdir()
        self.fails("inner attempt already exists")

    def test_existing_evidence_never_overwritten(self):
        self.obj.evidence.mkdir()
        protected = self.obj.evidence / "protected"
        protected.write_bytes(b"old")
        self.fails()
        self.assertEqual(protected.read_bytes(), b"old")

    def test_deadline_must_allow_inner_timeout_and_cleanup(self):
        for value in (True, 300, 315, float("inf"), float("nan")):
            with self.assertRaises(owner.OwnerError):
                self.obj.run(deadline=value)

    def test_exclusive_writer(self):
        path = self.root / "old"
        path.write_bytes(b"old")
        with self.assertRaises(FileExistsError):
            owner.write_exclusive(path, b"new")
        self.assertEqual(path.read_bytes(), b"old")

    def test_input_identity_ignores_read_atime_but_rejects_content_change(self):
        path = self.root / "regular"
        path.write_bytes(b"data")
        fields = ("st_dev", "st_ino", "st_mode", "st_nlink", "st_uid", "st_gid",
                  "st_size", "st_mtime_ns", "st_ctime_ns")
        info = path.stat()
        before = types.SimpleNamespace(**{key: getattr(info, key) for key in fields}, st_atime_ns=1)
        after = types.SimpleNamespace(**{key: getattr(info, key) for key in fields}, st_atime_ns=2)
        with mock.patch.object(owner.os, "fstat", side_effect=[before, after]):
            self.assertEqual(owner.regular(path), b"data")
        after.st_mtime_ns += 1
        with mock.patch.object(owner.os, "fstat", side_effect=[before, after]):
            with self.assertRaisesRegex(owner.OwnerError, "input changed"):
                owner.regular(path)

    def test_inside_checks_and_exact_execve(self):
        self.assertEqual(owner.QEMU_VERSION_STDOUT, PINNED_QEMU_VERSION_STDOUT)
        with mock.patch.object(owner, "_digest", side_effect=lambda p: owner.QEMU_SHA256 if p == owner.QEMU else self.obj.owner_sha), \
             mock.patch.object(owner, "bounded_command", return_value=result(PINNED_QEMU_VERSION_STDOUT)) as version, \
             mock.patch.object(owner.os, "execve") as execute:
            owner._inside(str(self.parent), NONCE, self.obj.owner_sha)
        self.bound.assert_called_once_with()
        version.assert_called_once_with([owner.QEMU, "--version"], 5)
        execute.assert_called_once_with("/usr/bin/python3", ["/usr/bin/python3", "-B", owner.RUNNER,
            "--manifest", owner.MANIFEST, "--attempt-parent", str(self.parent), "--attempt-name", "attempt-" + NONCE,
            "--timeout", "300"], {"PATH": "/usr/bin:/bin", "HOME": "/tmp", "TMPDIR": "/tmp", "PYTHONDONTWRITEBYTECODE": "1"})

    def test_inside_qemu_hash_rejects(self):
        with mock.patch.object(owner, "_digest", side_effect=lambda p: "0" * 64 if p == owner.QEMU else self.obj.owner_sha), \
             mock.patch.object(owner.os, "execve") as execute:
            with self.assertRaisesRegex(owner.OwnerError, "QEMU hash"):
                owner._inside(str(self.parent), NONCE, self.obj.owner_sha)
            execute.assert_not_called()

    def test_inside_qemu_version_rejects_any_exact_output_drift(self):
        suffix = b"QEMU emulator version 10.1.0 (qemu-kvm-10.1.0-16.el10_2.5)\n"
        copyright_line = b"Copyright (c) 2003-2025 Fabrice Bellard and the QEMU Project developers\n"
        invalid = (
            (b"QEMU emulator version 10.1.0\n" + copyright_line),
            (b"QEMU emulator version 10.1.0 (qemu-kvm-10.1.0-16.el10_2.4)\n" + copyright_line),
            (suffix + copyright_line + b"extra\n"),
            suffix,
            suffix + copyright_line.replace(b"developers", b"developer"),
        )
        for stdout in invalid:
            with self.subTest(stdout=stdout):
                with mock.patch.object(owner, "_digest", side_effect=lambda p: owner.QEMU_SHA256 if p == owner.QEMU else self.obj.owner_sha), \
                     mock.patch.object(owner, "bounded_command", return_value=result(stdout)), \
                     mock.patch.object(owner.os, "execve") as execute:
                    with self.assertRaisesRegex(owner.OwnerError, "QEMU version"):
                        owner._inside(str(self.parent), NONCE, self.obj.owner_sha)
                    execute.assert_not_called()

        with mock.patch.object(owner, "_digest", side_effect=lambda p: owner.QEMU_SHA256 if p == owner.QEMU else self.obj.owner_sha), \
             mock.patch.object(owner, "bounded_command", return_value=result(owner.QEMU_VERSION_STDOUT, err=b"warning\n")), \
             mock.patch.object(owner.os, "execve") as execute:
            with self.assertRaisesRegex(owner.OwnerError, "QEMU version"):
                owner._inside(str(self.parent), NONCE, self.obj.owner_sha)
            execute.assert_not_called()

    def test_inside_manifest_loader_failure_prevents_exec(self):
        self.bound.side_effect = owner.OwnerError("derived initramfs identity")
        with mock.patch.object(owner, "_digest", return_value=self.obj.owner_sha), mock.patch.object(owner.os, "execve") as execute:
            with self.assertRaisesRegex(owner.OwnerError, "derived initramfs"):
                owner._inside(str(self.parent), NONCE, self.obj.owner_sha)
            execute.assert_not_called()

    def test_docker_backend_rejects_non_sudo_prefix(self):
        with self.assertRaisesRegex(owner.OwnerError, "sudo Docker"):
            owner.DockerBackend().call(["/usr/bin/docker", "ps"], timeout=1)

    def test_outer_uid_rejection(self):
        with mock.patch.object(owner.os, "getuid", return_value=1000), mock.patch.object(owner.os, "geteuid", return_value=1000):
            with self.assertRaisesRegex(owner.OwnerError, "must be root"):
                owner.DockerBackend().call(owner.PREFIX + ["ps"], timeout=1)
            with self.assertRaisesRegex(owner.OwnerError, "root outer"):
                owner.main(["--attempt-parent", str(self.parent), "--nonce", NONCE, "--owner-sha256", self.obj.owner_sha])

    def test_root_docker_prefix_and_environment_are_exact(self):
        backend = owner.DockerBackend()
        with mock.patch.object(owner.os, "getuid", return_value=0), mock.patch.object(owner.os, "geteuid", return_value=0), \
             mock.patch.dict(owner.os.environ, {"SUDO_ASKPASS": "/reviewed/helper", "DOCKER_HOST": "evil"}, clear=True), \
             mock.patch.object(owner, "bounded_command", return_value=result()) as command:
            backend.call(owner.PREFIX + ["ps"], timeout=4)
        command.assert_called_once_with(["/usr/bin/sudo", "-A", "/usr/bin/docker", "ps"], 4,
            env={"PATH": "/usr/bin:/bin", "LANG": "C", "LC_ALL": "C", "SUDO_ASKPASS": "/reviewed/helper"},
            ledger=backend.children)

    def test_inner_parent_must_stay_uid1000_even_for_root_owner(self):
        with mock.patch.object(owner.os, "geteuid", return_value=0):
            owner.private_parent(str(self.parent))
        # No root chown or subprocess is needed to exercise rejection.
        with mock.patch.object(owner.os, "fstat", return_value=types.SimpleNamespace(
                st_uid=0, st_gid=0, st_mode=0o40700, st_dev=1, st_ino=2)):
            with self.assertRaisesRegex(owner.OwnerError, "uid/gid1000"):
                owner.private_parent(str(self.parent))

    def test_noncanonical_parent_rejected(self):
        with self.assertRaisesRegex(owner.OwnerError, "canonical"):
            owner.DiagnosticOwner(str(self.parent) + "/.", backend=self.fake)

    def test_unlock_failure_preserves_first_exception(self):
        failure = TimeoutError("original")
        self.fake.start_failure = failure
        self.obj._release = mock.Mock(side_effect=OSError("unlock failed"))
        self.assertIs(self.fails(), failure)

    def test_manifest_and_every_source_pin_before_loader(self):
        manifest = self.root / "manifest.json"
        manifest.write_bytes(b"{}")
        sources = {}
        for name in ("runner", "lifecycle", "backend", "qmp"):
            path = self.root / (name + ".py")
            path.write_bytes(name.encode())
            sources[str(path)] = owner._digest(path)
        self.patch("MANIFEST", str(manifest))
        self.patch("MANIFEST_SHA256", owner._digest(manifest))
        self.patch("SOURCE_HASHES", sources)
        module = types.SimpleNamespace(load_manifest=mock.Mock(return_value={"bound": True}))
        loader = types.SimpleNamespace(exec_module=mock.Mock())
        with mock.patch.object(owner.importlib.util, "spec_from_file_location", return_value=types.SimpleNamespace(loader=loader)), \
             mock.patch.object(owner.importlib.util, "module_from_spec", return_value=module):
            self.assertEqual(BOUND_MANIFEST(str(manifest))[1], {"bound": True})
            module.load_manifest.assert_called_once_with(str(manifest))
            for path in sources:
                original = Path(path).read_bytes()
                Path(path).write_bytes(b"drift")
                with self.subTest(source=path), self.assertRaisesRegex(owner.OwnerError, "source identity drift"):
                    BOUND_MANIFEST(str(manifest))
                Path(path).write_bytes(original)
            manifest.write_bytes(b"drift")
            with self.assertRaisesRegex(owner.OwnerError, "manifest identity drift"):
                BOUND_MANIFEST(str(manifest))
            self.assertEqual(module.load_manifest.call_count, 1)

    def test_bounded_local_command_and_overflow(self):
        response = owner.bounded_command(["/usr/bin/python3", "-c", "print('ok')"], 3)
        self.assertEqual(response.stdout, b"ok\n")
        with mock.patch.object(owner, "LIMIT", 32):
            with self.assertRaises(owner.CommandError) as caught:
                owner.bounded_command(["/usr/bin/python3", "-c", "print('x'*1000)"], 3)
            self.assertEqual(len(caught.exception.stdout), 33)

    def test_delayed_exact_reap_survives_bounded_command_failure(self):
        ledger = owner.CommandLedger()
        try:
            with mock.patch.object(owner.CommandChild, "wait", side_effect=owner.OwnerError("reap delayed")):
                with self.assertRaises(owner.CommandError):
                    owner.bounded_command(["/usr/bin/python3", "-c", "import time; time.sleep(30)"],
                                          0.05, ledger=ledger)
            self.assertEqual(len(ledger.pending), 1)
            child = next(iter(ledger.pending))
            self.assertFalse(child.reaped)
            self.assertEqual(len(ledger.errors), 1)
            with self.assertRaisesRegex(owner.OwnerError, "previous command child"):
                owner.bounded_command(["/usr/bin/true"], 1, ledger=ledger)
            ledger.retire_pending()
            self.assertTrue(child.reaped)
            self.assertEqual(ledger.pending, set())
            with mock.patch.object(owner.os, "killpg") as kill:
                ledger.retire(child)
                kill.assert_not_called()
        finally:
            ledger.retire_pending()

    def test_kill_and_wait_failures_remain_owned_and_preserved(self):
        ledger = owner.CommandLedger()
        kill_failure = PermissionError("kill failed")
        wait_failure = OSError("wait failed")
        try:
            with mock.patch.object(owner.os, "killpg", side_effect=kill_failure), \
                 mock.patch.object(owner.CommandChild, "wait", side_effect=wait_failure):
                with self.assertRaises(owner.CommandError):
                    owner.bounded_command(["/usr/bin/python3", "-c", "import time; time.sleep(30)"],
                                          0.05, ledger=ledger)
            self.assertEqual(len(ledger.pending), 1)
            child = next(iter(ledger.pending))
            self.assertFalse(child.reaped)
            self.assertEqual(ledger.errors, [wait_failure, kill_failure])
            ledger.retire_pending()
            self.assertTrue(child.reaped)
        finally:
            ledger.retire_pending()

    def test_child_signal_defaults_survive_ignored_cleanup_handlers(self):
        previous = {sig: signal.getsignal(sig) for sig in owner.OWNER_SIGNALS}
        try:
            for sig in owner.OWNER_SIGNALS:
                signal.signal(sig, signal.SIG_IGN)
            response = owner.bounded_command(["/usr/bin/python3", "-c",
                "import os,signal; os.kill(os.getpid(), signal.SIGTERM)"], 3)
            self.assertEqual(response.returncode, -signal.SIGTERM)
        finally:
            for sig, handler in previous.items():
                signal.signal(sig, handler)

    def test_command_record_success_and_nonzero_are_exact(self):
        for code in (0, 7):
            with self.subTest(code=code):
                response = owner.bounded_command(["/usr/bin/python3", "-c", "import sys; sys.exit(%d)" % code], 3,
                                                 ledger=owner.CommandLedger())
                record = response.command_record
                self.assertEqual(record["pid"], record["pgid"])
                self.assertGreater(record["pid"], 0)
                self.assertGreater(record["sid"], 0)
                self.assertGreater(record["proc_starttime"], 0)
                self.assertTrue(record["reaped"])
                self.assertEqual(record["returncode"], code)

    def test_command_record_timeout_is_reaped_after_kill(self):
        ledger = owner.CommandLedger()
        with self.assertRaises(owner.CommandError) as caught:
            owner.bounded_command(["/usr/bin/python3", "-c", "import time; time.sleep(30)"], .05, ledger=ledger)
        record = caught.exception.command_record
        self.assertEqual(record["pid"], record["pgid"])
        self.assertGreater(record["pid"], 0)
        self.assertGreater(record["sid"], 0)
        self.assertGreater(record["proc_starttime"], 0)
        self.assertTrue(record["reaped"])
        self.assertEqual(record["returncode"], -signal.SIGKILL)

    def test_identity_acquisition_retains_each_outer_command_field_before_failure(self):
        for failed_read, expected in (
                ("pgid", {"pid": 54321, "pgid": None, "sid": None,
                           "proc_starttime": None}),
                ("sid", {"pid": 54321, "pgid": 54321, "sid": None,
                          "proc_starttime": None}),
                ("starttime", {"pid": 54321, "pgid": 54321, "sid": 54321,
                                "proc_starttime": None}),
                ("validation", {"pid": 54321, "pgid": 99999, "sid": 54321,
                                 "proc_starttime": 9})):
            with self.subTest(failed_read=failed_read):
                child = owner.CommandChild()
                pgid = mock.Mock(return_value=54321)
                sid = mock.Mock(return_value=54321)
                start = mock.Mock(return_value=9)
                if failed_read == "pgid":
                    pgid.side_effect = owner.OwnerError("pgid read")
                elif failed_read == "sid":
                    sid.side_effect = owner.OwnerError("sid read")
                elif failed_read == "starttime":
                    start.side_effect = owner.OwnerError("starttime read")
                else:
                    pgid.return_value = 99999
                with mock.patch.object(owner.os, "posix_spawn", return_value=54321), \
                     mock.patch.object(owner.os, "getpgid", pgid), \
                     mock.patch.object(owner.os, "getsid", sid), \
                     mock.patch.object(owner, "_proc_starttime", start):
                    with self.assertRaises(owner.OwnerError):
                        child.acquire(["/bin/true"], {}, tuple(owner.OWNER_SIGNALS))
                record = child.record()
                self.assertEqual({key: record[key] for key in expected}, expected)
                self.assertIsNone(child.identity)
                with mock.patch.object(owner.os, "killpg") as kill:
                    with mock.patch.object(child, "wait", return_value=None):
                        with self.assertRaises(owner.OwnerError):
                            child.retire()
                    kill.assert_not_called()
                for stream in (child.stdout, child.stderr):
                    if stream is not None:
                        stream.close()

    def test_pre_spawn_failure_has_no_fabricated_identity(self):
        with self.assertRaises(owner.CommandError) as caught:
            owner.bounded_command(["/no/such/executable"], 1, ledger=owner.CommandLedger())
        self.assertEqual(caught.exception.command_record,
                         {"pid": None, "pgid": None, "sid": None,
                          "proc_starttime": None, "reaped": False, "returncode": None})

    def test_unresolved_reap_record_is_unreaped_and_ledger_owned(self):
        ledger = owner.CommandLedger()
        try:
            with mock.patch.object(owner.CommandChild, "wait", side_effect=owner.OwnerError("reap delayed")):
                with self.assertRaises(owner.CommandError) as caught:
                    owner.bounded_command(["/usr/bin/python3", "-c", "import time; time.sleep(30)"], .05,
                                          ledger=ledger)
            record = caught.exception.command_record
            self.assertFalse(record["reaped"])
            self.assertIsNone(record["returncode"])
            self.assertEqual(len(ledger.pending), 1)
        finally:
            ledger.retire_pending()

    def test_delayed_reap_appends_final_record_without_rewriting_initial(self):
        ledger = owner.CommandLedger()
        try:
            with mock.patch.object(owner.CommandChild, "wait", side_effect=owner.OwnerError("reap delayed")):
                with self.assertRaises(owner.CommandError) as caught:
                    owner.bounded_command(["/usr/bin/python3", "-c", "import time; time.sleep(30)"], .05,
                                          ledger=ledger)
            initial = dict(caught.exception.command_record)
            self.assertFalse(initial["reaped"])
            ledger.retire_pending()
            events = ledger.peek_final_reap_records()
            self.assertEqual(len(events), 1)
            self.assertEqual(events[0]["initial"], initial)
            self.assertTrue(events[0]["final"]["reaped"])
            self.assertEqual(caught.exception.command_record, initial)
            ledger.ack_final_reap_records(events)
        finally:
            ledger.retire_pending()

    def test_cleanup_retries_delayed_reap_publication_before_lease_release(self):
        initial = {"pid": 71, "pgid": 71, "sid": 71, "proc_starttime": 9,
                   "reaped": False, "returncode": None}
        final = dict(initial, reaped=True, returncode=-signal.SIGKILL)
        pair = {"initial": initial, "final": final}
        self.fake.children.final_reap_records.append(pair)
        self.obj._acquire()
        original_save = self.obj._save
        failed = []
        def save(name, value):
            if name.startswith("command-retirements-") and not failed:
                failed.append(name)
                raise MemoryError("reap evidence queue exhausted")
            return original_save(name, value)
        self.obj._save = save
        self.assertFalse(self.obj._cleanup())
        self.assertIsNotNone(self.obj.lock)
        self.assertEqual(self.fake.children.peek_final_reap_records(), (pair,))
        self.assertEqual(failed, ["command-retirements-001.json"])
        self.obj._save = original_save
        self.assertTrue(self.obj._cleanup())
        self.assertEqual(self.fake.children.peek_final_reap_records(), ())
        queued = [(path, raw) for path, raw in self.obj.pending_evidence
                  if path.name == "command-retirements-001.json"]
        self.assertEqual(len(queued), 1)
        self.assertEqual(json.loads(queued[0][1]), [pair])
        self.obj._release()
        self.assertIsNone(self.obj.lock)

    def test_final_signal_mask_restoration_carries_terminal_record(self):
        real = owner.signal.pthread_sigmask
        restores = []
        def mask(how, values):
            result = real(how, values)
            if how == signal.SIG_SETMASK:
                restores.append(True)
                if len(restores) == 3:
                    raise owner.OwnerSignal("final mask restoration")
            return result
        with mock.patch.object(owner.signal, "pthread_sigmask", side_effect=mask):
            with self.assertRaises(owner.OwnerSignal) as caught:
                owner.bounded_command(["/usr/bin/python3", "-c", "pass"], 3,
                                      ledger=owner.CommandLedger())
        record = caught.exception.command_record
        self.assertTrue(record["reaped"])
        self.assertEqual(record["returncode"], 0)

    def test_stream_close_finalizer_error_carries_terminal_command_record(self):
        original = owner.CommandChild.acquire
        class CloseFails:
            def __init__(self, stream): self.stream = stream
            def fileno(self): return self.stream.fileno()
            def close(self):
                self.stream.close()
                raise OSError("close finalizer failed")
        def acquire(child, *args):
            original(child, *args)
            child.stdout = CloseFails(child.stdout)
        with mock.patch.object(owner.CommandChild, "acquire", acquire):
            with self.assertRaises(owner.CommandError) as caught:
                owner.bounded_command(["/usr/bin/python3", "-c", "pass"], 3,
                                      ledger=owner.CommandLedger())
        record = caught.exception.command_record
        self.assertTrue(record["reaped"])
        self.assertEqual(record["returncode"], 0)

    def test_owner_signal_retains_exact_reap_record(self):
        ledger = owner.CommandLedger()
        original = owner.CommandChild.wait
        calls = [0]
        def interrupt_once(child, timeout):
            calls[0] += 1
            if calls[0] == 1:
                raise owner.OwnerSignal("cancelled")
            return original(child, timeout)
        with mock.patch.object(owner.CommandChild, "wait", interrupt_once):
            with self.assertRaises(owner.OwnerSignal) as caught:
                owner.bounded_command(["/usr/bin/python3", "-c", "pass"], 3,
                                      ledger=ledger)
        record = caught.exception.command_record
        self.assertEqual(record["pid"], record["pgid"])
        self.assertGreater(record["sid"], 0)
        self.assertGreater(record["proc_starttime"], 0)
        self.assertTrue(record["reaped"])
        self.assertEqual(record["returncode"], 0)

    def test_numbered_command_json_contains_identity_record(self):
        self.obj.run()
        # The injected backend has no process primitive, but the schema key is
        # always emitted for each numbered command.
        row = json.loads((self.obj.evidence / "001-ps.json").read_text())
        self.assertIn("command", row)
        self.assertEqual(row["command"]["pid"], row["command"]["pgid"])
        self.assertTrue(row["command"]["reaped"])


if __name__ == "__main__":
    unittest.main()
