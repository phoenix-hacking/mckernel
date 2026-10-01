import copy
import hashlib
import importlib.util
import json
import math
import signal
from pathlib import Path
import stat
import subprocess
import tempfile
import time
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("native_diagnostic", ROOT / "scripts/application-tests/native_diagnostic.py")
ND = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ND)


def hostile_exception(base=Exception):
    """Metadata that must never run during cleanup or first-error reporting."""
    calls = []
    class HostileMeta(type):
        def __getattribute__(cls, name):
            if name == "__name__":
                calls.append("class-name")
                raise RuntimeError("class-name failure")
            return super().__getattribute__(name)
    class Hostile(base, metaclass=HostileMeta):
        def __getattribute__(self, name):
            if name in ("args", "__class__"):
                calls.append(name)
                raise RuntimeError("exception property failure")
            return super().__getattribute__(name)
        def __str__(self):
            calls.append("str")
            raise RuntimeError("exception str failure")
        def __repr__(self):
            calls.append("repr")
            raise RuntimeError("exception repr failure")
    return Hostile("original hostile failure"), calls


class Process:
    def __init__(self, stuck=False, never_reap=False):
        self.calls, self.stuck, self.never_reap = [], stuck, never_reap
        self.returncode = None
    def communicate(self, timeout):
        self.calls.append("communicate")
        return b"QEMU stdout is not payload", b"QEMU stderr is not payload"
    def terminate(self): self.calls.append("terminate")
    def kill(self): self.calls.append("kill")
    def wait(self, timeout):
        self.calls.append("wait")
        if self.never_reap or (self.stuck and "kill" not in self.calls):
            raise subprocess.TimeoutExpired("fake", timeout)
        self.returncode = 0
        return self.returncode
    def process_identity(self):
        return {"pid": 12345, "pgid": 12345, "sid": 12345, "starttime_ticks": 1}
    def qemu_evidence(self):
        if self.returncode is None:
            raise RuntimeError("QEMU process was not exactly reaped")
        return {"argv": ["/usr/libexec/qemu-kvm", "-qmp", "unix:test"],
                **self.process_identity(), "returncode": self.returncode}


class Qmp:
    def negotiate(self, timeout): pass
    def resume(self, timeout): pass
    def wait_shutdown(self, timeout): return {"status": "shutdown"}
    def terminate(self, timeout): pass
    def close(self, timeout): pass


class NativeDiagnosticTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.files = {}
        for name in (*ND.ARTIFACTS, *ND.MODULE_NAMES, "derived", "collector", "overlay_source"):
            path = self.root / name
            path.write_bytes(name.encode()); path.chmod(0o644)
            self.files[name] = path
        self.files["collector"].chmod(0o700)
        self.files["payload"].chmod(0o755)
        self.manifest_path = self.root / "manifest.json"
        self.raw = {"schema_version": 1, "kind": "native-diagnostic-manifest", "case_id": "pilot",
                    "artifacts": {name: self.ref(name) for name in ND.ARTIFACTS},
                    "modules": [self.ref(name) for name in ND.MODULE_NAMES],
                    "profile": {"memory_mib": 8192, "vcpus": 4, "numa_nodes": 2},
                    "payload": {"cwd": "/case/work", "argv": ["/bin/mcexec", "-t", "1", "0", "app", "A", "", "B"],
                                "env": {"PATH": "/usr/bin:/bin", "COKERNEL_PATH": "/apps"},
                                "oracle": {"stdout_hex": "4100420a", "stderr_hex": "", "exit_code": 37},
                                "stdout_limit_bytes": 1024, "stderr_limit_bytes": 1024}}
        refs = self.raw["artifacts"]
        staging = {"base_initramfs": refs["initramfs"], "derived_initramfs": self.ref("derived"),
                   "collector": self.ref("collector"), "overlay_source": self.ref("overlay_source")}
        all_refs = {**refs, "collector": staging["collector"], **dict(zip(ND.MODULE_NAMES, self.raw["modules"]))}
        final_map = {}
        for member, source in ND.FINAL_MEMBERS.items():
            ref = all_refs[source]
            final_map[member] = {"mode": stat.S_IFREG | 0o755 if member in ("init", "apps/app") else ref["mode"],
                                 "uid": 0, "gid": 0, "nlink": 1, "mtime": 0,
                                 "size": ref["size"], "sha256": ref["sha256"], "rdevmajor": 0, "rdevminor": 0}
        for member in ("apps", "case", "case/work"):
            final_map[member] = {"mode": stat.S_IFDIR | 0o755, "uid": 0, "gid": 0, "nlink": 2,
                                 "mtime": 0, "size": 0, "sha256": hashlib.sha256(b"").hexdigest(),
                                 "rdevmajor": 0, "rdevminor": 0}
        overlay = {"base_cpio_sha256": "a" * 64, "base_cpio_size": 1,
                   "base_sha256": staging["base_initramfs"]["sha256"],
                   "collector_sha256": staging["collector"]["sha256"], "final_map": final_map,
                   "output_identity": ND._identity(staging["derived_initramfs"]["path"]),
                   "output_sha256": staging["derived_initramfs"]["sha256"],
                   "overlay_sha256": "b" * 64, "payload_sha256": refs["payload"]["sha256"],
                   "mcexec_sha256": refs["mcexec"]["sha256"],
                   "size": staging["derived_initramfs"]["size"],
                   "sources": {name: {"path": ref["path"], "sha256": ref["sha256"],
                                         "identity": ND._identity(ref["path"])}
                               for name, ref in (("base", staging["base_initramfs"]),
                                                 ("collector", staging["collector"]),
                                                 ("payload", refs["payload"]),
                                                 ("mcexec", refs["mcexec"]))}}
        self.overlay = overlay
        overlay_path = self.root / "overlay_manifest.json"
        overlay_path.write_text(json.dumps(overlay)); overlay_path.chmod(0o644)
        self.files["overlay_manifest"] = overlay_path
        staging["overlay_manifest"] = self.ref("overlay_manifest")
        self.raw["staging"] = staging
        self.manifest_path.write_text(json.dumps(self.raw))
        self.manifest = ND.load_manifest(str(self.manifest_path))
        self.counter = 0

    def tearDown(self): self.tmp.cleanup()

    def ref(self, name):
        data = self.files[name].read_bytes()
        return {"path": str(self.files[name]), "size": len(data), "sha256": hashlib.sha256(data).hexdigest(),
                "mode": self.files[name].stat().st_mode}

    def report(self):
        report = {key: copy.deepcopy(self.manifest["payload"][key]) for key in ("argv", "env", "cwd")}
        report.update(raw_wait_status=37 << 8, started_ns=100, reaped_ns=200, finished_ns=300, procfs_empty=True, streams={})
        for name in ("stdout", "stderr"):
            data = self.manifest["payload"]["oracle"][name + "_hex"]
            report["streams"][name] = {"hex": data, "eof": True, "truncated": False,
                                       "observed": len(data) // 2, "retained": len(data) // 2,
                                       "discarded": 0, "limit": 1024, "eof_ns": 250}
        return report

    def serial(self, report=None):
        # Synthetic protocol fixture, never actual McKernel evidence.
        return "\n".join([
            "application SCHEDULE os=0 generation=1 pid=12 cpu=0",
            "application procfs published os=0 generation=1 pid=12 tid=12",
            "application_syscall=delivered os=0 generation=1 pid=12 worker=9 delivery=3 cpu=0 number=1",
            "application_syscall=return_route os=0 generation=1 pid=12 worker=9 delivery=3 launcher_cpu=1 guest_cpu=0",
            "application_syscall=returned os=0 generation=1 pid=12 worker=9 delivery=3 cpu=0 value=4",
            "application_syscall=delivered os=0 generation=1 pid=12 worker=9 delivery=4 cpu=0 number=231",
            "application procfs deleted os=0 generation=1 pid=12 tid=12",
            "application retirement os=0 generation=1 pid=12 token=2 errno=0",
            "application_process=release os=0 generation=1 pid=12 cleanup_errno=0",
            "ND_PAYLOAD " + json.dumps(self.report() if report is None else report), ""])

    def observation(self, report=None):
        return {"serial": self.serial(report), "debugcon": "guest log", "qmp": {"status": "shutdown"},
                "teardown": True, "started_at": 1, "finished_at": 2, "deadline": 3,
                "process_identity": {"pid": 12345, "pgid": 12345, "sid": 12345,
                                      "starttime_ticks": 1}}

    def attempt(self):
        self.counter += 1
        attempt = ND.prepare_attempt(self.manifest, self.root, "attempt-" + str(self.counter))
        (attempt / "serial.log").write_text(self.serial())
        (attempt / "debugcon.log").write_text("guest log")
        return attempt

    def exercise(self, attempt, process=None, qmp=None, timeout=1):
        return ND.exercise_lifecycle(self.manifest, attempt, lambda **kw: process or Process(), lambda **kw: qmp or Qmp(), timeout)

    def test_missing_factories_prevent_spawn_and_record_terminal(self):
        attempt = self.attempt(); factory = mock.Mock(side_effect=AssertionError("must not spawn"))
        with self.assertRaisesRegex(ND.DiagnosticError, "explicit diagnostic factories required"):
            ND.run_diagnostic(self.manifest, attempt, factory, None)
        factory.assert_not_called()
        result = json.loads((attempt / "result.json").read_text())
        self.assertEqual(result["status"], "BLOCKED")
        self.assertFalse(result["mckernel_application_executed"])
        self.assertTrue((attempt / "first-failure.jsonl").read_text())
        self.assertFalse((attempt / "root.img").exists())

    def test_staging_os_errors_are_terminal_without_factory_calls(self):
        for error in (FileNotFoundError("selected artifact disappeared"),
                      PermissionError("selected artifact unreadable"),
                      OSError("staging I/O failure")):
            with self.subTest(error=type(error).__name__):
                attempt = self.attempt()
                process_factory = mock.Mock(side_effect=AssertionError("must not spawn"))
                qmp_factory = mock.Mock(side_effect=AssertionError("must not spawn"))
                with mock.patch.object(ND, "build_command", side_effect=error):
                    with self.assertRaises(type(error)) as raised:
                        ND.run_diagnostic(self.manifest, attempt, process_factory, qmp_factory)
                self.assertEqual(str(raised.exception), str(error))
                process_factory.assert_not_called(); qmp_factory.assert_not_called()
                result = json.loads((attempt / "result.json").read_text())
                self.assertEqual(result["status"], "BLOCKED")
                self.assertEqual(result["failure"]["type"], type(error).__name__)
                journal = (attempt / "first-failure.jsonl").read_text().splitlines()
                self.assertEqual(len(journal), 1)
                self.assertEqual(json.loads(journal[0])["error"], str(error))

    def test_staging_publication_failure_does_not_mask_original_os_error(self):
        attempt = self.attempt()
        process_factory = mock.Mock(side_effect=AssertionError("must not spawn"))
        qmp_factory = mock.Mock(side_effect=AssertionError("must not spawn"))
        original = FileNotFoundError("selected artifact disappeared")
        with mock.patch.object(ND, "build_command", side_effect=original), \
             mock.patch.object(ND, "write_record", side_effect=OSError("journal unavailable")) as publish:
            with self.assertRaises(FileNotFoundError) as raised:
                ND.run_diagnostic(self.manifest, attempt, process_factory, qmp_factory)
        self.assertEqual(str(raised.exception), str(original))
        publish.assert_called_once()
        process_factory.assert_not_called(); qmp_factory.assert_not_called()

    def test_staging_does_not_normalize_base_exceptions(self):
        for error in (KeyboardInterrupt("stop"), SystemExit(37)):
            with self.subTest(error=type(error).__name__):
                attempt = self.attempt()
                with mock.patch.object(ND, "build_command", side_effect=error), \
                     mock.patch.object(ND, "write_record", wraps=ND.write_record) as publish:
                    with self.assertRaises(type(error)) as raised:
                        ND.run_diagnostic(self.manifest, attempt, mock.Mock(), mock.Mock())
                self.assertIs(raised.exception, error)
                publish.assert_called_once()
                self.assertEqual(json.loads((attempt / "result.json").read_text())["failure"]["type"],
                                 type(error).__name__)
                self.assertEqual(len((attempt / "first-failure.jsonl").read_text().splitlines()), 1)

    def test_retained_profile_and_payload_plan(self):
        plan = ND.build_command(self.manifest, self.attempt()); args = plan["argv"]
        self.assertEqual(args[:7], (ND.QEMU, "-machine", "q35", "-accel", "tcg,thread=multi", "-cpu", "max,la57=off"))
        for item in ("4,sockets=2,cores=2,threads=1", "-no-reboot", "-no-shutdown", "-nic", ND.APPEND): self.assertIn(item, args)
        self.assertEqual(args.count("-numa"), 2); self.assertNotIn("-drive", args)
        self.assertTrue(plan["runtime_ready"])
        self.assertEqual(args[args.index("-initrd") + 1], self.raw["staging"]["derived_initramfs"]["path"])
        for item in ("/apps/app", "/images/mckernel.img"): self.assertIn(item, plan["overlay"]["guest_destinations"])
        self.assertIn("insmod /modules/ihk-smp-x86_64.ko ihk_trampoline=524288", plan["overlay"]["init_sequence"])

    def test_explicit_small_profile_has_exact_two_cpu_six_gib_topology(self):
        value = copy.deepcopy(self.raw)
        value["profile"] = {"name": ND.PROFILE_SMALL, "memory_mib": 6144,
                             "vcpus": 2, "numa_nodes": 1}
        self.manifest_path.write_text(json.dumps(value))
        manifest = ND.load_manifest(str(self.manifest_path))
        args = ND.build_command(manifest, self.attempt())["argv"]
        self.assertEqual(args[args.index("-smp") + 1], "2,sockets=1,cores=2,threads=1")
        self.assertEqual(args[args.index("-m") + 1], "6144")
        self.assertEqual(args.count("-numa"), 1)
        self.assertIn("memory-backend-ram,size=6G,id=ram-node0", args)

    def test_profile_name_cannot_be_implicit_or_append_override(self):
        for profile in ({"name": ND.PROFILE_SMALL, "memory_mib": 6144, "vcpus": 2, "numa_nodes": 1,
                         "append": "console=ttyS0"},
                        {"name": ND.PROFILE_SMALL, "memory_mib": 8192, "vcpus": 2, "numa_nodes": 1},
                        {"name": "small", "memory_mib": 6144, "vcpus": 2, "numa_nodes": 1}):
            value = copy.deepcopy(self.raw); value["profile"] = profile
            self.manifest_path.write_text(json.dumps(value))
            with self.assertRaises(ND.DiagnosticError):
                ND.load_manifest(str(self.manifest_path))

    def test_payload_argv_accepts_core_memory_tail_and_retains_startup_prefix(self):
        self.raw["payload"]["argv"] = ["/bin/mcexec", "-t", "1", "0", "app", "memory"]
        self.manifest_path.write_text(json.dumps(self.raw))
        manifest = ND.load_manifest(str(self.manifest_path))
        self.assertEqual(manifest["payload"]["argv"][-1], "memory")

        self.raw["payload"]["argv"] = ["/bin/mcexec", "-t", "1", "0", "/apps/app"]
        self.manifest_path.write_text(json.dumps(self.raw))
        manifest = ND.load_manifest(str(self.manifest_path))
        self.assertEqual(manifest["payload"]["argv"][-1], "/apps/app")

    def test_payload_argv_rejects_empty_oversize_nul_nonstring_and_prefix_drift(self):
        cases = [
            ([], "non-empty"),
            (["/bin/mcexec", "-t", "1", "0", "app"] + ["x"] * ND.PAYLOAD_ARGC_MAX,
             "argc limit"),
            (["/bin/mcexec", "-t", "1", "0", "app", "x" * (ND.PAYLOAD_ARG_BYTES_MAX + 1)],
             "argument byte limit"),
            (["/bin/mcexec", "-t", "1", "0", "app", "bad\0arg"], "argv item"),
            (["/bin/mcexec", "-t", "1", "0", "app", True], "argv item"),
            (["/bin/mcexec", "-x", "1", "0", "app", "A"], "prefix"),
            (["/bin/mcexec", "-t", "1", "0", "apps/app"], "prefix/path"),
        ]
        for argv, message in cases:
            with self.subTest(argv=argv):
                value = copy.deepcopy(self.raw)
                value["payload"]["argv"] = argv
                self.manifest_path.write_text(json.dumps(value))
                with self.assertRaisesRegex(ND.DiagnosticError, message):
                    ND.load_manifest(str(self.manifest_path))

    def test_payload_argv_rejects_total_bytes_surrogate_and_list_subclass(self):
        total_bytes = ["/bin/mcexec", "-t", "1", "0", "app"] + ["x" * 256] * 9
        cases = [
            (total_bytes, "total byte limit"),
            (["/bin/mcexec", "-t", "1", "0", "app", "\ud800"], "UTF-8"),
        ]
        for argv, message in cases:
            with self.subTest(message=message):
                value = copy.deepcopy(self.raw)
                value["payload"]["argv"] = argv
                with self.assertRaisesRegex(ND.DiagnosticError, message):
                    ND._validate_manifest(value)

        class ListSubclass(list):
            pass

        value = copy.deepcopy(self.raw)
        value["payload"]["argv"] = ListSubclass(value["payload"]["argv"])
        with self.assertRaisesRegex(ND.DiagnosticError, "non-empty list"):
            ND._validate_manifest(value)

    def test_qemu_starts_only_after_qmp_negotiation(self):
        args = ND.build_command(self.manifest, self.attempt())["argv"]
        self.assertEqual(args.count("-S"), 1)
        self.assertNotIn("-S=off", args)
        self.assertLess(args.index("-S"), args.index("-kernel"))
        self.assertEqual(args[args.index("-smp") + 1], "4,sockets=2,cores=2,threads=1")
        self.assertEqual(args[args.index("-initrd") + 1], self.raw["staging"]["derived_initramfs"]["path"])

    def test_staging_refs_are_required_and_rechecked_before_factory(self):
        for key in ("base_initramfs", "derived_initramfs", "collector", "overlay_source", "overlay_manifest"):
            with self.subTest(key=key):
                value = copy.deepcopy(self.raw)
                del value["staging"][key]
                self.manifest_path.write_text(json.dumps(value))
                with self.assertRaises(ND.DiagnosticError): ND.load_manifest(str(self.manifest_path))
        self.manifest_path.write_text(json.dumps(self.raw))
        attempt = self.attempt(); factory = mock.Mock(side_effect=AssertionError("must not spawn"))
        self.files["collector"].write_bytes(b"drift")
        with self.assertRaises(ND.DiagnosticError): ND.run_diagnostic(self.manifest, attempt, factory, factory)
        factory.assert_not_called()
        self.assertEqual(json.loads((attempt / "result.json").read_text())["status"], "BLOCKED")

    def test_runtime_rechecks_kernel_and_overlay_manifest_bytes(self):
        for name in ("bzImage", "overlay_manifest"):
            with self.subTest(name=name):
                attempt = self.attempt(); factory = mock.Mock(side_effect=AssertionError("must not spawn"))
                original = self.files[name].read_bytes()
                self.files[name].write_bytes(original + b"drift")
                try:
                    with self.assertRaises(ND.DiagnosticError):
                        ND.run_diagnostic(self.manifest, attempt, factory, factory)
                    factory.assert_not_called()
                finally:
                    self.files[name].write_bytes(original)

    def test_base_cannot_be_used_as_derived(self):
        value = copy.deepcopy(self.raw)
        value["staging"]["derived_initramfs"] = value["staging"]["base_initramfs"]
        self.manifest_path.write_text(json.dumps(value))
        with self.assertRaisesRegex(ND.DiagnosticError, "derived initramfs must differ"):
            ND.load_manifest(str(self.manifest_path))

    def test_overlay_identity_and_final_map_must_join(self):
        for change in ("base", "collector", "payload", "derived", "member", "directory"):
            with self.subTest(change=change):
                overlay = copy.deepcopy(self.overlay)
                if change == "base": overlay["base_sha256"] = "0" * 64
                elif change == "collector": overlay["collector_sha256"] = "0" * 64
                elif change == "payload": overlay["payload_sha256"] = "0" * 64
                elif change == "derived": overlay["output_sha256"] = "0" * 64
                elif change == "member": overlay["final_map"]["modules/mcctrl.ko"]["sha256"] = "0" * 64
                else: del overlay["final_map"]["case/work"]
                self.files["overlay_manifest"].write_text(json.dumps(overlay))
                value = copy.deepcopy(self.raw)
                value["staging"]["overlay_manifest"] = self.ref("overlay_manifest")
                self.manifest_path.write_text(json.dumps(value))
                with self.assertRaises(ND.DiagnosticError): ND.load_manifest(str(self.manifest_path))

    def test_mcexec_overlay_hash_path_identity_and_membership_must_join(self):
        mutations = (
            ("top-level hash", lambda overlay: overlay.update(mcexec_sha256="0" * 64)),
            ("source hash", lambda overlay: overlay["sources"]["mcexec"].update(sha256="0" * 64)),
            ("source path", lambda overlay: overlay["sources"]["mcexec"].update(path=str(self.files["payload"]))),
            ("source identity", lambda overlay: overlay["sources"]["mcexec"]["identity"].update(st_ino=-1)),
            ("final membership", lambda overlay: overlay["final_map"].pop("bin/mcexec")),
        )
        for label, mutate in mutations:
            with self.subTest(change=label):
                overlay = copy.deepcopy(self.overlay)
                mutate(overlay)
                self.files["overlay_manifest"].write_text(json.dumps(overlay))
                value = copy.deepcopy(self.raw)
                value["staging"]["overlay_manifest"] = self.ref("overlay_manifest")
                self.manifest_path.write_text(json.dumps(value))
                with self.assertRaises(ND.DiagnosticError):
                    ND.load_manifest(str(self.manifest_path))

    def test_stale_output_rejected_before_factory(self):
        for name in ("qmp.sock", "qemu.stdout", "qemu.stderr", "qmp.transcript.json"):
            with self.subTest(name=name):
                attempt = self.attempt(); (attempt / name).touch()
                factory = mock.Mock(side_effect=AssertionError("must not spawn"))
                with self.assertRaises(ND.DiagnosticError):
                    ND.run_diagnostic(self.manifest, attempt, factory, factory)
                factory.assert_not_called()

    def test_ready_manifest_invokes_only_injected_factories(self):
        attempt = self.attempt()
        process, qmp = Process(), Qmp()
        pf, qf = mock.Mock(return_value=process), mock.Mock(return_value=qmp)
        result = ND.run_diagnostic(self.manifest, attempt, pf, qf, timeout=1)
        pf.assert_called_once(); qf.assert_called_once()
        self.assertEqual(result["status"], "PROTOCOL_PASS")
        self.assertFalse(result["application_acceptance"])
        self.assertFalse(result["mckernel_application_executed"])

    def test_expected_plan_rejects_valid_kernel_change_before_lifecycle(self):
        attempt = self.attempt()
        expected = ND.build_command(self.manifest, attempt)
        # Both references remain valid reviewed files; only the bound kernel
        # identity changes between the factory-binding and lifecycle checks.
        self.manifest["artifacts"]["bzImage"] = copy.deepcopy(self.manifest["artifacts"]["initramfs"])
        process_factory, qmp_factory = mock.Mock(), mock.Mock()
        lifecycle = mock.Mock(side_effect=AssertionError("must not enter lifecycle"))
        with mock.patch.object(ND, "exercise_lifecycle", lifecycle):
            with self.assertRaisesRegex(ND.DiagnosticError, "build plan changed"):
                ND.run_diagnostic(self.manifest, attempt, process_factory, qmp_factory,
                                  expected_plan=expected)
        process_factory.assert_not_called(); qmp_factory.assert_not_called(); lifecycle.assert_not_called()
        result = json.loads((attempt / "result.json").read_text())
        self.assertEqual(result["status"], "BLOCKED")

    def test_plan_owns_immutable_nested_inputs(self):
        plan = ND.build_command(self.manifest, self.attempt())
        for obj, key, value in ((plan, "runtime_ready", False),
                                (plan["payload"]["oracle"], "exit_code", 0),
                                (plan["staging"]["overlay_source"], "path", "/changed"),
                                (plan["argv"], 0, "/changed"),
                                (plan["manifest"]["modules"], 0, {})):
            with self.subTest(key=key), self.assertRaises(TypeError):
                obj[key] = value
        self.manifest["payload"]["oracle"]["exit_code"] = 0
        self.manifest["staging"]["overlay_source"]["path"] = "/changed"
        self.assertEqual(plan["payload"]["oracle"]["exit_code"], 37)
        self.assertEqual(plan["staging"]["overlay_source"]["path"], str(self.files["overlay_source"]))

    def test_expected_plan_rejects_nested_valid_drift_and_non_argv_inputs(self):
        for change in ("staging", "payload", "case"):
            with self.subTest(change=change):
                manifest = copy.deepcopy(self.manifest)
                attempt = self.attempt()
                expected = ND.build_command(manifest, attempt)
                if change == "staging":
                    manifest["staging"]["overlay_source"] = dict(manifest["staging"]["collector"])
                elif change == "payload":
                    manifest["payload"]["oracle"]["stdout_hex"] = "42"
                else:
                    manifest["case_id"] = "different-case"
                # The replacement independently validates. Rejection must be
                # the complete factory-plan join, not incidental bad input.
                ND.build_command(manifest, attempt)
                with mock.patch.object(ND, "exercise_lifecycle") as lifecycle:
                    with self.assertRaisesRegex(ND.DiagnosticError, "build plan changed"):
                        ND.run_diagnostic(manifest, attempt, mock.Mock(), mock.Mock(), expected_plan=expected)
                lifecycle.assert_not_called()

    def test_plan_comparison_is_strict_and_lifecycle_owns_its_snapshot(self):
        attempt = self.attempt()
        plan = ND.build_command(self.manifest, attempt)
        changed = ND._thaw(plan)
        changed["runtime_ready"] = 1
        self.assertFalse(ND._same_plan(plan, ND._freeze(changed)))
        def lifecycle(manifest, *args, **kwargs):
            self.manifest["payload"]["oracle"]["exit_code"] = 0
            self.assertEqual(manifest["payload"]["oracle"]["exit_code"], 37)
            self.assertEqual(kwargs["admitted_argv"], tuple(plan["argv"]))
            return {"status": "PROTOCOL_PASS"}
        with mock.patch.object(ND, "exercise_lifecycle", side_effect=lifecycle):
            ND.run_diagnostic(self.manifest, attempt, mock.Mock(), mock.Mock(), expected_plan=plan)

    def test_failure_reporting_never_formats_hostile_exception_or_arguments(self):
        class HostileArgument:
            def __str__(self): raise AssertionError("argument str called")
            def __repr__(self): raise AssertionError("argument repr called")
        class HostileError(RuntimeError):
            def __str__(self): raise AssertionError("exception str called")
            def __repr__(self): raise AssertionError("exception repr called")
        error = HostileError(HostileArgument())
        attempt = self.attempt()
        with mock.patch.object(ND, "build_command", side_effect=error):
            with self.assertRaises(HostileError) as raised:
                ND.run_diagnostic(self.manifest, attempt, mock.Mock(), mock.Mock())
        self.assertIs(raised.exception, error)
        result = json.loads((attempt / "result.json").read_text())
        self.assertEqual(result["failure"]["error"], "<exception argument omitted>")

    def test_total_failure_metadata_preserves_safe_types_and_ignores_all_hooks(self):
        self.assertEqual(ND._failure(OSError(5, "disk unavailable"), "cleanup"),
                         {"phase": "cleanup", "type": "OSError", "error": "5: disk unavailable"})
        error, calls = hostile_exception()
        self.assertEqual(ND._failure(error, "cleanup"),
                         {"phase": "cleanup", "type": "BaseException",
                          "error": "<exception metadata unavailable>"})
        self.assertEqual(calls, [])
        class HostileProperties(Exception):
            @property
            def args(self): raise AssertionError("args property called")
            @property
            def __class__(self): raise AssertionError("class property called")
        self.assertEqual(ND._failure(HostileProperties("safe message"), "cleanup"),
                         {"phase": "cleanup", "type": "HostileProperties", "error": "safe message"})
        self.assertEqual(ND._failure(object(), "cleanup")["error"], "<exception metadata unavailable>")

    def test_prepare_and_staging_hostile_errors_preserve_identity_and_evidence(self):
        for phase in ("prepare", "staging"):
            with self.subTest(phase=phase):
                original, calls = hostile_exception(BaseException)
                if phase == "prepare":
                    attempt = self.root / "prepare-hostile"
                    with mock.patch.object(Path, "touch", side_effect=original):
                        with self.assertRaises(BaseException) as raised:
                            ND.prepare_attempt(self.manifest, self.root, attempt.name)
                else:
                    attempt = self.attempt()
                    with mock.patch.object(ND, "build_command", side_effect=original):
                        with self.assertRaises(BaseException) as raised:
                            ND.run_diagnostic(self.manifest, attempt, mock.Mock(), mock.Mock())
                self.assertIs(raised.exception, original)
                self.assertEqual(calls, [])
                record = json.loads((attempt / "result.json").read_text())
                self.assertEqual(record["failure"], {"phase": phase, "type": "BaseException",
                                                     "error": "<exception metadata unavailable>"})
                self.assertEqual(len((attempt / "first-failure.jsonl").read_text().splitlines()), 1)

    def test_failure_publication_declines_ambient_timer_without_stealing_it(self):
        old_handler = signal.getsignal(signal.SIGALRM)
        handler = lambda *_args: None
        signal.signal(signal.SIGALRM, handler)
        signal.setitimer(signal.ITIMER_REAL, 30, 30)
        try:
            with mock.patch.object(ND, "write_record") as publisher, \
                 mock.patch.object(ND.signal, "setitimer", wraps=signal.setitimer) as timer:
                ND.record_failure(self.attempt(), RuntimeError("original"), "staging")
            publisher.assert_not_called()
            timer.assert_not_called()
            self.assertIs(signal.getsignal(signal.SIGALRM), handler)
            remaining, interval = signal.getitimer(signal.ITIMER_REAL)
            self.assertGreater(remaining, 0)
            self.assertEqual(interval, 30)
        finally:
            signal.setitimer(signal.ITIMER_REAL, 0)
            signal.signal(signal.SIGALRM, old_handler)

    def test_staging_writer_base_exception_preserves_original(self):
        for publish_error in (KeyboardInterrupt("writer stop"), SystemExit(2)):
            attempt = self.attempt()
            original = FileNotFoundError("original")
            with mock.patch.object(ND, "build_command", side_effect=original), \
                 mock.patch.object(ND, "write_record", side_effect=publish_error) as publish:
                with self.assertRaises(FileNotFoundError) as raised:
                    ND.run_diagnostic(self.manifest, attempt, mock.Mock(), mock.Mock())
            self.assertIs(raised.exception, original)
            publish.assert_called_once()

    def test_publication_restores_alarm_handler_when_arming_fails(self):
        old = signal.getsignal(signal.SIGALRM)
        with mock.patch.object(ND.signal, "setitimer", side_effect=OSError("timer unavailable")), \
             mock.patch.object(ND, "write_record") as publisher:
            ND.record_failure(self.attempt(), RuntimeError("original"), "staging")
        publisher.assert_not_called()
        self.assertIs(signal.getsignal(signal.SIGALRM), old)

    def test_publication_declines_worker_thread_without_calling_writer(self):
        with mock.patch.object(ND.threading, "current_thread", return_value=object()), \
             mock.patch.object(ND, "write_record") as publisher:
            ND.record_failure(self.attempt(), RuntimeError("original"), "staging")
        publisher.assert_not_called()

    def test_manifest_rejects_implicit_oracle_env_profile_and_types(self):
        variants = []
        for field in ("oracle", "stdout_limit_bytes"):
            value = copy.deepcopy(self.raw); del value["payload"][field]; variants.append(value)
        value = copy.deepcopy(self.raw); value["profile"]["append"] = "console=ttyS0"; variants.append(value)
        value = copy.deepcopy(self.raw); del value["payload"]["env"]["COKERNEL_PATH"]; variants.append(value)
        value = copy.deepcopy(self.raw); value["schema_version"] = True; variants.append(value)
        for value in variants:
            self.manifest_path.write_text(json.dumps(value))
            with self.assertRaises(ND.DiagnosticError): ND.load_manifest(str(self.manifest_path))

    def test_artifact_drift_duplicate_json_and_stale_attempt(self):
        self.files["mcexec"].write_bytes(b"wrong")
        with self.assertRaises(ND.DiagnosticError): ND.load_manifest(str(self.manifest_path))
        self.manifest_path.write_text('{"schema_version":1,"schema_version":1}')
        with self.assertRaises(ND.DiagnosticError): ND.load_manifest(str(self.manifest_path))
        attempt = self.attempt()
        with self.assertRaises(ND.DiagnosticError): ND.prepare_attempt(self.manifest, self.root, attempt.name)
        (attempt / "qmp.sock").touch()
        with self.assertRaises(ND.DiagnosticError): ND.build_command(self.manifest, attempt)

    def test_positive_fake_lifecycle_is_only_protocol_evidence(self):
        attempt = self.attempt(); process = Process(); result = self.exercise(attempt, process)
        self.assertEqual(result["status"], "PROTOCOL_PASS")
        self.assertFalse(result["mckernel_application_executed"])
        self.assertEqual(result["guest_report"]["raw_wait_status"], 37 << 8)
        self.assertIn("QEMU stdout", (attempt / "qemu.stdout").read_text())
        self.assertEqual(process.calls, ["terminate", "wait", "communicate"])

    def test_qemu_evidence_is_captured_before_host_timeout_and_retained(self):
        attempt = self.attempt()
        class Ordered(Process):
            def qemu_evidence(self):
                self.calls.append("qemu-evidence")
                return super().qemu_evidence()
            def communicate(self, timeout):
                self.calls.append("communicate")
                time.sleep(5)
        process = Ordered()
        with self.assertRaisesRegex(ND.DiagnosticError, "absolute deadline"):
            self.exercise(attempt, process, timeout=.05)
        self.assertLess(process.calls.index("qemu-evidence"), process.calls.index("communicate"))
        record = json.loads((attempt / "result.json").read_text())
        self.assertEqual(record["qemu_evidence"]["returncode"], 0)
        self.assertEqual(record["failure"]["phase"], "host-capture")

    def test_qemu_evidence_first_base_exception_is_rethrown_after_publication(self):
        first = KeyboardInterrupt("FIRST")
        class BrokenEvidence(Process):
            def qemu_evidence(self): raise first
        attempt = self.attempt(); process = BrokenEvidence()
        with self.assertRaises(KeyboardInterrupt) as raised:
            self.exercise(attempt, process)
        self.assertIs(raised.exception, first)
        self.assertIn("communicate", process.calls)
        record = json.loads((attempt / "result.json").read_text())
        self.assertEqual(record["failure"], {"phase": "qemu-evidence", "type": "KeyboardInterrupt", "error": "FIRST"})
        self.assertEqual(record["capture_errors"][0], record["failure"])

    def test_qemu_evidence_first_exception_beats_later_host_capture_failure(self):
        first = KeyboardInterrupt("FIRST")
        later = RuntimeError("LATER")
        class BrokenEvidence(Process):
            def qemu_evidence(self): raise first
            def communicate(self, timeout):
                self.calls.append("communicate")
                raise later
        attempt = self.attempt(); process = BrokenEvidence()
        with self.assertRaises(KeyboardInterrupt) as raised:
            self.exercise(attempt, process)
        self.assertIs(raised.exception, first)
        record = json.loads((attempt / "result.json").read_text())
        self.assertEqual(record["failure"]["error"], "FIRST")
        self.assertEqual([item["error"] for item in record["capture_errors"]], ["FIRST", "LATER"])

    def test_admitted_qemu_argv_is_exact_nonempty_and_not_reconstructed(self):
        admitted = ("/usr/libexec/qemu-kvm", "-qmp", "unix:test")
        for argv, message in (([], "QEMU evidence argv"),
                              (["/usr/libexec/qemu-kvm", "-qmp", "unix:other"], "admitted command mismatch")):
            with self.subTest(argv=argv):
                attempt = self.attempt()
                process = Process()
                process.qemu_evidence = lambda: {"argv": argv, **process.process_identity(), "returncode": 0}
                with self.assertRaisesRegex(ND.DiagnosticError, message):
                    ND.exercise_lifecycle(self.manifest, attempt, lambda **kw: process,
                                          lambda **kw: Qmp(), timeout=1, admitted_argv=admitted)
                record = json.loads((attempt / "result.json").read_text())
                self.assertEqual(record["failure"]["phase"], "qemu-evidence")
        attempt = self.attempt()
        process = Process()
        self.assertEqual(ND.exercise_lifecycle(self.manifest, attempt, lambda **kw: process,
                                               lambda **kw: Qmp(), timeout=1,
                                               admitted_argv=admitted)["status"], "PROTOCOL_PASS")

    def test_acquisition_failure_evidence_is_durable_without_fabricated_identity(self):
        attempt = self.attempt()
        failure = RuntimeError("post-Popen identity failure")
        carrier = RuntimeError("trusted acquisition carrier")
        carrier._mckernel_acquisition_original = failure
        carrier._mckernel_qemu_acquisition_evidence = {
            "argv": ["/usr/libexec/qemu-kvm", "-qmp", "unix:test"],
            "pid": 12345, "pgid": None, "sid": None, "starttime_ticks": None,
            "identity_complete": False, "reaped": True, "returncode": -signal.SIGKILL}
        with self.assertRaisesRegex(ND.DiagnosticError, "post-Popen identity failure"):
            ND.exercise_lifecycle(self.manifest, attempt,
                                  lambda **kw: (_ for _ in ()).throw(carrier), lambda **kw: Qmp())
        record = json.loads((attempt / "result.json").read_text())
        retained = record["qemu_acquisition_failure"]
        self.assertEqual(retained["failure"]["error"], "post-Popen identity failure")
        self.assertEqual(retained["evidence"]["pid"], 12345)
        self.assertIsNone(retained["evidence"]["pgid"])
        self.assertEqual(retained["evidence"]["returncode"], -signal.SIGKILL)
        attempt = self.attempt()
        carrier._mckernel_qemu_acquisition_evidence = dict(retained["evidence"], reaped=False,
                                                            returncode=None)
        with self.assertRaisesRegex(ND.DiagnosticError, "post-Popen identity failure"):
            ND.exercise_lifecycle(self.manifest, attempt,
                                  lambda **kw: (_ for _ in ()).throw(carrier), lambda **kw: Qmp())
        record = json.loads((attempt / "result.json").read_text())
        self.assertFalse(record["cleanup"]["reaped"])
        self.assertEqual(record["cleanup"]["errors"][-1]["phase"], "acquisition-retirement")

    def test_evaluate_rejects_malformed_missing_and_aliased_process_identity(self):
        base = self.observation()
        variants = []
        missing = dict(base); del missing["process_identity"]; variants.append(missing)
        malformed = dict(base); malformed["process_identity"] = {"pid": 1}; variants.append(malformed)
        aliased = dict(base); aliased["process_identity"] = {
            "pid": 1, "pgid": 2, "sid": 1, "starttime_ticks": 3}; variants.append(aliased)
        for observation in variants:
            with self.subTest(observation=observation):
                with self.assertRaises(ND.DiagnosticError):
                    ND.evaluate(self.manifest, observation)

    def test_evaluate_uses_retained_identity_after_reap_without_procfs(self):
        observation = self.observation()
        with mock.patch("pathlib.Path.read_bytes", side_effect=AssertionError("post-reap procfs read")):
            result = ND.evaluate(self.manifest, observation)
        self.assertEqual(result["observation"]["process_identity"]["starttime_ticks"], 1)

    def test_final_capture_includes_teardown_warnings(self):
        for log in ("serial", "debugcon"):
            for phase in ("terminate", "wait", "qmp-close"):
                with self.subTest(log=log, phase=phase):
                    attempt = self.attempt(); process = Process(); qmp = Qmp()
                    def warn(*args, **kwargs):
                        with (attempt / (log + ".log")).open("a") as stream:
                            stream.write("\nWARNING: teardown failure\n")
                        if phase == "wait":
                            process.returncode = 0
                        return 0
                    setattr(qmp if phase == "qmp-close" else process,
                            "close" if phase == "qmp-close" else phase, warn)
                    with self.assertRaisesRegex(ND.DiagnosticError, "kernel failure marker"):
                        self.exercise(attempt, process, qmp)
                    result = json.loads((attempt / "result.json").read_text())
                    self.assertEqual(result["status"], "FAIL")
                    self.assertTrue(result["cleanup"]["reaped"])

    def test_terminal_capture_is_bounded_after_teardown(self):
        attempt = self.attempt(); process = Process()
        def grow(timeout):
            (attempt / "debugcon.log").write_bytes(b"x" * (ND.MAX_JSON + 1))
            process.calls.append("wait")
            process.returncode = 0
            return 0
        process.wait = grow
        with self.assertRaisesRegex(ND.DiagnosticError, "capture limit"):
            self.exercise(attempt, process)
        self.assertIn("wait", process.calls)

    def test_complete_unique_syscall_correspondence(self):
        original = self.serial().splitlines()
        delivered, route, returned, terminal = original[2:6]
        variants = {
            "orphan returned": original[:5] + [returned.replace("delivery=3", "delivery=99")] + original[5:],
            "unreturned delivery": original[:5] + [delivered.replace("delivery=3", "delivery=99")] + original[5:],
            "duplicate delivered": original[:3] + [delivered] + original[3:],
            "duplicate returned": original[:5] + [returned] + original[5:],
            "duplicate route": original[:4] + [route] + original[4:],
            "missing return": original[:4] + original[5:],
            "missing route": original[:3] + original[4:],
            "non-group exit returned": [line.replace("number=1", "number=60") for line in original],
            "duplicate terminal": original[:6] + [terminal] + original[6:],
            "terminal with return": original[:6] + [returned.replace("delivery=3", "delivery=4")] + original[6:],
            "terminal with route": original[:5] + [route.replace("delivery=3", "delivery=4")] + original[5:],
            "malformed trace": original[:5] + [delivered + " extra"] + original[5:],
            "foreign PID": original[:5] + [delivered.replace("pid=12", "pid=13")] + original[5:],
            "route after return": original[:3] + [returned, route] + original[5:],
            "return before delivery": original[:2] + [returned, route, delivered] + original[5:],
            "second terminal ID": original[:6] + [terminal.replace("delivery=4", "delivery=5")] + original[6:],
            "missing worker route": original[:5] + [delivered.replace("delivery=3", "delivery=5"),
                returned.replace("delivery=3", "delivery=5")] + original[5:],
            "work after exit": original[:6] + [delivered.replace("delivery=3", "delivery=5"),
                route.replace("delivery=3", "delivery=5"), returned.replace("delivery=3", "delivery=5")] + original[6:],
        }
        for name, lines in variants.items():
            with self.subTest(name=name):
                observation = self.observation(); observation["serial"] = "\n".join(lines)
                with self.assertRaises(ND.DiagnosticError): ND.evaluate(self.manifest, observation)

    def test_trace_budget_exhaustion_still_requires_terminal_exit_delivery(self):
        """The observer retains exit_group after 64 ordinary samples."""
        lines = [
            "application SCHEDULE os=0 generation=1 pid=12 cpu=0",
            "application procfs published os=0 generation=1 pid=12 tid=12",
        ]
        for delivery in range(1, 65):
            lines.extend([
                "application_syscall=delivered os=0 generation=1 pid=12 "
                f"worker=9 delivery={delivery} cpu=0 number=1",
                "application_syscall=return_route os=0 generation=1 pid=12 "
                f"worker=9 delivery={delivery} launcher_cpu=1 guest_cpu=0",
                "application_syscall=returned os=0 generation=1 pid=12 "
                f"worker=9 delivery={delivery} cpu=0 value=4",
            ])
        lines.extend([
            "application_syscall=delivered os=0 generation=1 pid=12 "
            "worker=9 delivery=65 cpu=0 number=231",
            "application procfs deleted os=0 generation=1 pid=12 tid=12",
            "application retirement os=0 generation=1 pid=12 token=2 errno=0",
            "application_process=release os=0 generation=1 pid=12 cleanup_errno=0",
            "ND_PAYLOAD " + json.dumps(self.report()), "",
        ])
        observation = self.observation()
        observation["serial"] = "\n".join(lines)
        result = ND.evaluate(self.manifest, observation)
        self.assertEqual(result["status"], "PROTOCOL_PASS")

    def test_production_sampler_keeps_terminal_branch_after_budget_mutation(self):
        """The checked-in producer must preserve the source-bound terminal rule."""
        source_path = ROOT / "host-kernel" / "native-rust" / "mcctrl_process.rs"
        source = source_path.read_text(encoding="utf-8")
        branch = "let traced = number == 231 || self.trace();"
        self.assertIn("let number = image::word(&bytes, 40).map_err(errno)?;", source)
        self.assertIn(branch, source)
        mutated = source.replace(branch, "let traced = self.trace();", 1)
        self.assertNotIn(branch, mutated)
        self.assertNotEqual(source, mutated)

    def test_source_supported_launcher_slots_and_same_cpu_no_route(self):
        for cpu in ("-1", "0", "2", "3", "9999999999"):
            observation = self.observation()
            observation["serial"] = observation["serial"].replace("launcher_cpu=1", "launcher_cpu=" + cpu)
            with self.subTest(cpu=cpu), self.assertRaises(ND.DiagnosticError):
                ND.evaluate(self.manifest, observation)
        # A different worker occupying slot 0 legitimately omits return_route.
        lines = self.serial().splitlines()
        equal = [lines[2].replace("worker=9 delivery=3", "worker=8 delivery=2"),
                 lines[4].replace("worker=9 delivery=3", "worker=8 delivery=2")]
        observation = self.observation(); observation["serial"] = "\n".join(lines[:2] + equal + lines[2:])
        self.assertEqual(ND.evaluate(self.manifest, observation)["status"], "PROTOCOL_PASS")

    def test_qemu_output_alone_cannot_pass(self):
        attempt = self.attempt(); (attempt / "serial.log").write_text("")
        with self.assertRaisesRegex(ND.DiagnosticError, "guest payload report"): self.exercise(attempt)

    def test_wait_eof_accounting_timestamps_and_routes(self):
        variants = []
        for key, value in (("raw_wait_status", 9), ("raw_wait_status", True), ("raw_wait_status", 0), ("started_ns", 400), ("procfs_empty", False)):
            report = self.report(); report[key] = value; variants.append(self.observation(report))
        for key, value in (("eof", False), ("truncated", True), ("observed", 5), ("retained", True), ("discarded", 1), ("limit", 1025), ("eof_ns", 301), ("hex", "41")):
            report = self.report(); report["streams"]["stdout"][key] = value; variants.append(self.observation(report))
        for old, new in (("delivery=3 launcher", "delivery=99 launcher"), ("cleanup_errno=0", "cleanup_errno=1"), ("number=231", "number=0"), ("guest_cpu=0", "guest_cpu=1")):
            obs = self.observation(); obs["serial"] = obs["serial"].replace(old, new); variants.append(obs)
        for obs in variants:
            with self.subTest(obs=obs):
                with self.assertRaises(ND.DiagnosticError): ND.evaluate(self.manifest, obs)

    def test_all_original_failure_markers_reject(self):
        for marker in ("WARNING:", "soft lockup", "clear_host_pte failed", "Kernel panic", "Oops:", "BUG:", "rcu_preempt detected stalls", "hard LOCKUP", "continuing service error", "cleanup retained", "reap_retained", "strncpy_from_user:ioctl:", "FAIL", "ret: "):
            obs = self.observation(); obs["debugcon"] += "\n" + marker
            with self.assertRaises(ND.DiagnosticError): ND.evaluate(self.manifest, obs)

    def test_normal_boot_prose_and_success_status_fields_are_not_failure_markers(self):
        obs = self.observation()
        obs["debugcon"] += (
            "\ncmdline: panic=-1\n"
            "cmdline: panic = -1\n"
            "pci: report a bug to the vendor if this persists\n"
            "application result error=0\n"
        )
        self.assertEqual(ND.evaluate(self.manifest, obs)["status"], "PROTOCOL_PASS")

    def test_concrete_kernel_panics_reject_in_both_logs(self):
        for marker in ("panic: kernel mode PF", "PANIC: monitor_init() allocation failed.", "panic"):
            for log in ("serial", "debugcon"):
                with self.subTest(marker=marker, log=log):
                    obs = self.observation()
                    obs[log] += "\n" + marker
                    with self.assertRaisesRegex(ND.DiagnosticError, "kernel failure marker"):
                        ND.evaluate(self.manifest, obs)

    def test_actual_objdump_stderr_still_rejects_empty_stderr_oracle(self):
        report = self.report()
        payload = b"objdump /proc/self/exe: 2\nwarning: did not set LD_PRELOAD\n"
        self.assertEqual(len(payload), 58)
        report["streams"]["stderr"]["hex"] = payload.hex()
        report["streams"]["stderr"]["observed"] = 58
        report["streams"]["stderr"]["retained"] = 58
        with self.assertRaisesRegex(ND.DiagnosticError, "wrong payload bytes"):
            ND.evaluate(self.manifest, self.observation(report))

    def test_nonfinite_timeout_recorded(self):
        for timeout in (math.nan, math.inf, -1, 0, True):
            attempt = self.attempt()
            with self.assertRaisesRegex(ND.DiagnosticError, "finite deadline"): self.exercise(attempt, timeout=timeout)
            self.assertEqual(json.loads((attempt / "result.json").read_text())["status"], "FAIL")

    def test_qmp_deadline_and_errors_cannot_skip_kill_reap(self):
        class BrokenQmp(Qmp):
            def negotiate(self, timeout): time.sleep(1)
            def terminate(self, timeout): raise RuntimeError("quit broken")
            def close(self, timeout): raise RuntimeError("close broken")
        attempt = self.attempt(); process = Process(stuck=True); start = time.monotonic()
        with self.assertRaisesRegex(ND.DiagnosticError, "absolute deadline"): self.exercise(attempt, process, BrokenQmp(), timeout=0.02)
        self.assertLess(time.monotonic() - start, 0.5)
        self.assertEqual(process.calls, ["terminate", "wait", "kill", "wait", "communicate"])
        result = json.loads((attempt / "result.json").read_text())
        self.assertTrue(result["cleanup"]["reaped"])
        self.assertEqual(result["failure"]["type"], "TimeoutError")
        self.assertIn("quit broken", str(result["cleanup"]["errors"]))

    def test_each_blocking_qmp_or_communicate_step_is_bounded(self):
        for phase in ("negotiate", "resume", "wait_shutdown", "communicate"):
            attempt = self.attempt(); process = Process(); qmp = Qmp()
            def block(timeout): time.sleep(5 if phase == "communicate" else 1)
            setattr(process if phase == "communicate" else qmp, phase, block)
            with self.assertRaisesRegex(ND.DiagnosticError, "absolute deadline"):
                self.exercise(attempt, process, qmp, timeout=0.01)
            self.assertIn("wait", process.calls)
            self.assertEqual(len((attempt / "first-failure.jsonl").read_text().splitlines()), 1)

    def test_qmp_lookup_failures_never_skip_process_cleanup(self):
        for phase in ("negotiate", "resume", "wait_shutdown", "terminate", "close"):
            for failure in ("missing", "raises", "blocks"):
                with self.subTest(phase=phase, failure=failure):
                    class FaultyQmp(Qmp):
                        def __getattribute__(self, name):
                            if name == phase:
                                if failure == "missing": raise AttributeError(name)
                                if failure == "raises": raise RuntimeError("lookup failed")
                                time.sleep(5)
                            return super().__getattribute__(name)
                    attempt = self.attempt(); process = Process(stuck=True)
                    started = time.monotonic()
                    with self.assertRaises(ND.DiagnosticError):
                        self.exercise(attempt, process, FaultyQmp(), timeout=0.03)
                    self.assertLess(time.monotonic() - started, 1)
                    self.assertEqual(process.calls, ["terminate", "wait", "kill", "wait", "communicate"])
                    self.assertTrue(json.loads((attempt / "result.json").read_text())["cleanup"]["reaped"])

    def test_journal_cannot_delay_retirement(self):
        attempt = self.attempt(); process = Process(stuck=True)
        class BrokenQmp(Qmp):
            def negotiate(self, timeout): raise RuntimeError("first QMP failure")
            def terminate(self, timeout): raise RuntimeError("second QMP failure")
        original = ND._append_failure
        def check_retired(attempt, failure):
            self.assertEqual(process.calls, ["terminate", "wait", "kill", "wait", "communicate"])
            self.assertEqual(failure["error"], "first QMP failure")
            original(attempt, failure)
        with mock.patch.object(ND, "_append_failure", side_effect=check_retired):
            with self.assertRaisesRegex(ND.DiagnosticError, "first QMP failure"):
                self.exercise(attempt, process, BrokenQmp())
        self.assertEqual(len((attempt / "first-failure.jsonl").read_text().splitlines()), 1)

    def test_blocking_journal_is_bounded_after_reap(self):
        attempt = self.attempt(); process = Process()
        (attempt / "serial.log").write_text("missing report")
        def block(*args):
            self.assertIn("wait", process.calls)
            signal.pause()
        start = time.monotonic()
        with mock.patch.object(ND, "_append_failure", side_effect=block):
            with self.assertRaisesRegex(ND.DiagnosticError, "missing/duplicate"):
                self.exercise(attempt, process)
        self.assertLess(time.monotonic() - start, 3)

    def test_journal_write_failure_does_not_skip_reaping(self):
        attempt = self.attempt(); process = Process()
        (attempt / "serial.log").write_text("no guest report")
        with mock.patch.object(ND, "_append_failure", side_effect=OSError("disk failure")):
            with self.assertRaisesRegex(ND.DiagnosticError, "missing/duplicate"):
                self.exercise(attempt, process)
        self.assertIn("wait", process.calls)

    def test_lifecycle_abnormal_exit_rethrows_identity_after_retirement_and_evidence(self):
        for original in (KeyboardInterrupt("stop"), SystemExit(37)):
            with self.subTest(error=type(original).__name__):
                attempt = self.attempt(); process = Process(); qmp = Qmp()
                qmp.negotiate = mock.Mock(side_effect=original)
                with self.assertRaises(type(original)) as raised:
                    self.exercise(attempt, process, qmp)
                self.assertIs(raised.exception, original)
                self.assertIn("wait", process.calls)
                record = json.loads((attempt / "result.json").read_text())
                self.assertEqual(record["failure"]["type"], type(original).__name__)
                self.assertEqual(len((attempt / "first-failure.jsonl").read_text().splitlines()), 1)

    def test_lifecycle_writer_base_exception_cannot_replace_abnormal_exit(self):
        original = KeyboardInterrupt("first")
        process, qmp = Process(), Qmp()
        qmp.negotiate = mock.Mock(side_effect=original)
        with mock.patch.object(ND, "write_record", side_effect=SystemExit("second")) as publish:
            with self.assertRaises(KeyboardInterrupt) as raised:
                self.exercise(self.attempt(), process, qmp)
        self.assertIs(raised.exception, original)
        self.assertIn("wait", process.calls)
        publish.assert_called_once()

    def test_cleanup_abnormal_exit_rethrows_after_remaining_cleanup(self):
        attempt = self.attempt(); process = Process(); qmp = Qmp()
        original = SystemExit(37)
        qmp.terminate = mock.Mock(side_effect=original)
        with self.assertRaises(SystemExit) as raised:
            self.exercise(attempt, process, qmp)
        self.assertIs(raised.exception, original)
        self.assertIn("wait", process.calls)
        record = json.loads((attempt / "result.json").read_text())
        self.assertEqual(record["cleanup"]["errors"][0]["type"], "SystemExit")

    def test_qmp_cleanup_hostile_metadata_never_skips_retirement_or_first_error(self):
        for prior_failure in (False, True):
            with self.subTest(prior_failure=prior_failure):
                attempt = self.attempt(); process = Process(stuck=True); qmp = Qmp()
                original = RuntimeError("first negotiation failure")
                hostile, hooks = hostile_exception()
                if prior_failure:
                    qmp.negotiate = mock.Mock(side_effect=original)
                qmp.terminate = mock.Mock(side_effect=hostile)
                with self.assertRaises(ND.DiagnosticError) as raised:
                    self.exercise(attempt, process, qmp)
                self.assertIs(raised.exception.__cause__, original if prior_failure else hostile)
                self.assertEqual(hooks, [])
                self.assertEqual(process.calls, ["terminate", "wait", "kill", "wait", "communicate"])
                record = json.loads((attempt / "result.json").read_text())
                self.assertTrue(record["cleanup"]["reaped"])
                self.assertEqual(record["cleanup"]["errors"][0],
                                 {"phase": "qmp-quit", "type": "BaseException",
                                  "error": "<exception metadata unavailable>"})
                self.assertEqual(record["failure"]["error"],
                                 "first negotiation failure" if prior_failure else "teardown uncertain")
                self.assertEqual(len((attempt / "first-failure.jsonl").read_text().splitlines()), 1)

    def test_hostile_metadata_across_lifecycle_capture_evaluation_and_publication(self):
        for phase in ("lifecycle", "qmp-transcript", "host-capture", "evaluation", "publication"):
            with self.subTest(phase=phase):
                attempt = self.attempt(); process = Process(stuck=phase in ("lifecycle", "publication")); qmp = Qmp()
                hostile, hooks = hostile_exception(BaseException)
                original = RuntimeError("first negotiation failure")
                def raise_hostile(*args, **kwargs):
                    raise hostile
                evaluate = ND.evaluate
                publish = ND.write_record
                if phase == "lifecycle":
                    qmp.negotiate = raise_hostile
                    qmp.terminate = mock.Mock(side_effect=RuntimeError("later cleanup"))
                elif phase == "qmp-transcript":
                    class HostileSession(Qmp):
                        @property
                        def session(self): raise hostile
                    qmp = HostileSession()
                elif phase == "host-capture":
                    def communicate(timeout):
                        process.calls.append("communicate")
                        raise hostile
                    process.communicate = communicate
                elif phase == "evaluation":
                    evaluate = raise_hostile
                else:
                    qmp.negotiate = mock.Mock(side_effect=original)
                    publish = raise_hostile
                with mock.patch.object(ND, "evaluate", side_effect=evaluate), \
                     mock.patch.object(ND, "write_record", side_effect=publish) as publisher:
                    with self.assertRaises(BaseException) as raised:
                        self.exercise(attempt, process, qmp)
                self.assertEqual(hooks, [])
                expected_calls = ["terminate", "wait"]
                if process.stuck:
                    expected_calls.extend(["kill", "wait"])
                self.assertEqual(process.calls, expected_calls + ["communicate"])
                publisher.assert_called_once()
                if phase == "publication":
                    self.assertIs(raised.exception.__cause__, original)
                else:
                    self.assertIs(raised.exception, hostile)
                    record = json.loads((attempt / "result.json").read_text())
                    self.assertEqual(record["failure"]["type"], "BaseException")
                    self.assertEqual(len((attempt / "first-failure.jsonl").read_text().splitlines()), 1)

    def test_lifecycle_primary_error_remains_cause_when_writer_fails(self):
        original = RuntimeError("first QMP failure")
        process, qmp = Process(), Qmp()
        qmp.negotiate = mock.Mock(side_effect=original)
        with mock.patch.object(ND, "write_record", side_effect=SystemExit("writer stop")):
            with self.assertRaisesRegex(ND.DiagnosticError, "first QMP failure") as raised:
                self.exercise(self.attempt(), process, qmp)
        self.assertIs(raised.exception.__cause__, original)
        self.assertIn("wait", process.calls)

    def test_dangling_terminal_symlink_cannot_be_replaced(self):
        attempt = self.attempt(); target = attempt / "result.json"
        target.symlink_to(attempt / "absent")
        with self.assertRaises(ND.DiagnosticError): ND.write_record(attempt, {"status": "PASS"})
        self.assertTrue(target.is_symlink())

    def test_factory_and_communicate_errors_preserved(self):
        for phase in ("process", "qmp", "communicate"):
            attempt = self.attempt(); process = Process()
            def fail(**kwargs): raise RuntimeError(phase + " failure")
            if phase == "communicate": process.communicate = fail
            with self.assertRaisesRegex(ND.DiagnosticError, phase + " failure"):
                ND.exercise_lifecycle(self.manifest, attempt, fail if phase == "process" else lambda **kw: process,
                                      fail if phase == "qmp" else lambda **kw: Qmp())
            result = json.loads((attempt / "result.json").read_text())
            self.assertIn(phase, result["failure"]["error"])
            if phase != "process": self.assertIn("wait", process.calls)

    def test_unreaped_process_late_completion_capture_overflow(self):
        attempt = self.attempt()
        with self.assertRaisesRegex(ND.DiagnosticError, "teardown uncertain"): self.exercise(attempt, Process(never_reap=True))
        self.assertFalse(json.loads((attempt / "result.json").read_text())["cleanup"]["reaped"])
        obs = self.observation(); obs["finished_at"] = 3
        with self.assertRaisesRegex(ND.DiagnosticError, "late completion"): ND.evaluate(self.manifest, obs)
        attempt = self.attempt(); (attempt / "serial.log").write_bytes(b"x" * (ND.MAX_JSON + 1))
        with self.assertRaisesRegex(ND.DiagnosticError, "capture limit"): self.exercise(attempt)

    def test_terminal_record_cannot_be_replaced_or_raced(self):
        attempt = self.attempt(); ND.write_record(attempt, {"status": "FAIL"}, {"error": "original"})
        original = (attempt / "result.json").read_bytes()
        with self.assertRaises(ND.DiagnosticError): ND.write_record(attempt, {"status": "PASS"})
        self.assertEqual((attempt / "result.json").read_bytes(), original)
        attempt = self.attempt(); original_link = ND.os.link
        def race(source, dest, **kw):
            Path(dest).write_text("concurrent terminal")
            return original_link(source, dest, **kw)
        with mock.patch.object(ND.os, "link", race):
            with self.assertRaises(FileExistsError): ND.write_record(attempt, {"status": "PASS"})
        self.assertEqual((attempt / "result.json").read_text(), "concurrent terminal")


if __name__ == "__main__": unittest.main()
