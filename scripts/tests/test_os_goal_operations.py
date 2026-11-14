"""Harmless temporary HOST payloads; no workstation, native or held controls."""
import copy
import hashlib
import importlib.util
import os
from pathlib import Path
import json
import signal
import subprocess
import sys
import tempfile
import threading
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))
import os_goal_operations as operations
from os_goal_progress import load_ledger, condition_sha256

GIB, MIB = 1024 ** 3, 1024 ** 2


class TrackingBackend(operations.HostProcessBackend):
    def __init__(self):
        self.starts = 0
        self.handles = []

    def start(self, *args):
        self.starts += 1
        handle = super().start(*args)
        self.handles.append(handle)
        return handle


class OperationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.journal = self.root / "journal"
        self.backend = TrackingBackend()
        self.proofs = []
        self.external = []
        self.executable = str(Path(sys.executable).resolve())
        self.cpu = next(iter(set(os.sched_getaffinity(0)) & {0, 6, 7}), 0)

    def spec(self, ident="first", code="print('okay')"):
        result = {"schema_version": 1, "operation_id": ident, "original_id": "M15-F02-selection",
            "owner_id": "same-Root", "scope": "HOST",
            "inputs": [{"path": self.executable, "sha256": hashlib.sha256(Path(self.executable).read_bytes()).hexdigest()}],
            "argv": [self.executable, "-c", code], "environment": ["PYTHONUNBUFFERED=1", "LANG=C"],
            "ulimits": [{"Name": "core", "Soft": 0, "Hard": 0},
                        {"Name": "cpu", "Soft": 3, "Hard": 3},
                        {"Name": "fsize", "Soft": 16 * MIB, "Hard": 16 * MIB}],
            "cwd": str(self.root), "resources": {"CPU": [self.cpu], "planning_bytes": 256 * MIB,
                 "jobs": 1, "host_floor_bytes": 16 * GIB, "scratch_floor_bytes": 12 * GIB,
                 "max_age_ns": 25_000_000_000},
            "execution_timeout_s": 2, "cleanup_timeout_s": 1,
            "owned_process_group": True, "expected_exit_codes": [0]}
        return result

    def target(self):
        row = next(row for row in load_ledger(SCRIPTS.parent)["tasks"] if row["id"] == "M15-F02-selection")
        return {"original_check": row["id"], "condition_sha256": condition_sha256(row),
                "input_bindings": {"runtime": hashlib.sha256(Path(self.executable).read_bytes()).hexdigest()}}

    def provider(self, spec, *, phase, active_charges, deadline_mono_ns):
        self.proofs.append((phase, copy.deepcopy(active_charges)))
        utc, mono = time.time_ns(), time.monotonic_ns()
        return operations.FreshAdmission(spec.operation_id, spec.digest, phase, utc, mono,
            {gate: "actual-" + gate + "-record" for gate in operations.GATES},
            {"observed_utc_ns": utc, "observed_mono_ns": mono,
             "cpu_affinity": [self.cpu], "MemAvailable_bytes": 26 * GIB,
             "host_free_bytes": 20 * GIB, "scratch_free_bytes": 20 * GIB,
             "retained_charges_complete": True, "retained_charges": copy.deepcopy(self.external),
             "controller_worker_overhead_bytes": 128 * MIB,
             "all_controller_worker_overhead_measured": True, "exclusive_scope_compatible": True})

    def runner(self, provider=None, backend=None):
        return operations.OperationRunner(self.journal, self.provider if provider is None else provider,
                                           backend=self.backend if backend is None else backend)

    def test_every_missing_field_refuses_with_zero_effects(self):
        spec = self.spec()
        for field in operations.FIELDS:
            candidate = dict(spec)
            del candidate[field]
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.runner().run(candidate)
            self.assertFalse(self.journal.exists())
        self.assertEqual(self.proofs, [])
        self.assertEqual(self.backend.starts, 0)

    def test_unknown_original_or_mismatched_closure_refuses_before_effects(self):
        candidates = []
        unknown = self.spec()
        unknown["original_id"] = "invented-original"
        candidates.append(unknown)
        mismatch = self.spec()
        mismatch["closure_target"] = self.target()
        mismatch["closure_target"]["original_check"] = "M15-F03"
        candidates.append(mismatch)
        condition = self.spec()
        condition["closure_target"] = self.target()
        condition["closure_target"]["condition_sha256"] = "f" * 64
        candidates.append(condition)
        unbound = self.spec()
        unbound["closure_target"] = self.target()
        unbound["closure_target"]["input_bindings"] = {"source": "b" * 64}
        candidates.append(unbound)
        for candidate in candidates:
            with self.assertRaises(ValueError):
                self.runner().run(candidate)
            self.assertFalse(self.journal.exists())

    def test_profile_maps_are_exact_unique_and_order_independent(self):
        spec = self.spec()
        reordered = copy.deepcopy(spec)
        reordered["environment"].reverse()
        reordered["ulimits"].reverse()
        self.assertEqual(operations.OperationSpec.parse(spec).digest, operations.OperationSpec.parse(reordered).digest)
        self.assertTrue(operations.profiles_match(spec["environment"], reordered["environment"],
                                                spec["ulimits"], reordered["ulimits"]))
        changed_argv = copy.deepcopy(spec)
        changed_argv["argv"][1:] = reversed(changed_argv["argv"][1:])
        self.assertNotEqual(operations.OperationSpec.parse(spec).digest, operations.OperationSpec.parse(changed_argv).digest)
        for env in (["A=1", "A=1"], ["missing"], ["=empty"], ["A=1", "A=2"]):
            with self.subTest(env=env), self.assertRaises(ValueError):
                operations.environment_map(env)
        for change in ("extra", "changed", "missing"):
            actual = list(spec["environment"])
            if change == "extra":
                actual.append("EXTRA=1")
            elif change == "changed":
                actual[0] += "changed"
            else:
                actual.pop()
            self.assertFalse(operations.profiles_match(spec["environment"], actual, spec["ulimits"], spec["ulimits"]))
        with self.assertRaises(ValueError):
            operations.ulimit_map(spec["ulimits"] + [spec["ulimits"][0]])
        changed = copy.deepcopy(spec["ulimits"])
        changed[1]["Hard"] += 1
        self.assertFalse(operations.profiles_match([], [], spec["ulimits"], changed))

    def test_complete_spec_still_requires_fresh_callback_not_supplied_flags(self):
        with self.assertRaisesRegex(ValueError, "Trusted fresh"):
            operations.OperationRunner(self.journal, backend=self.backend).run(self.spec())
        for index, value in enumerate((True, {"account": True, "source": True, "permission": True, "ownership": True})):
            with self.assertRaisesRegex(ValueError, "FreshAdmission"):
                self.runner(provider=lambda *args, **kwargs: value).run(self.spec("invalid" + str(index)))
        self.assertEqual(self.backend.starts, 0)

    def test_exact_input_change_during_admission_never_starts(self):
        source = self.root / "source.txt"
        source.write_text("before")
        spec = self.spec()
        spec["inputs"].append({"path": str(source), "sha256": hashlib.sha256(source.read_bytes()).hexdigest()})
        def changed(*args, **kwargs):
            proof = self.provider(*args, **kwargs)
            source.write_text("after")
            return proof
        with self.assertRaisesRegex(ValueError, "input changed"):
            self.runner(provider=changed).run(spec)
        self.assertEqual(self.backend.starts, 0)
        self.assertEqual(self.runner().status()[0]["payload_state"], "NOT_STARTED")

    def test_actual_compile_failure_closes_own_custody_and_emits_only_failure(self):
        source = self.root / "broken.py"
        source.write_text("this is invalid python !\n")
        spec = self.spec()
        spec["argv"] = [self.executable, "-m", "py_compile", str(source)]
        spec["inputs"].append({"path": str(source), "sha256": hashlib.sha256(source.read_bytes()).hexdigest()})
        spec["closure_target"] = self.target()
        self.external = [{"owner": "old-native-adjacent-HOST-hold", "planning_bytes": 256 * MIB,
                          "jobs": 1, "state": "UNKNOWN"}]
        result = self.runner().run(spec)
        self.assertEqual((result["payload_state"], result["custody_state"], result["reservation"]),
                         ("FAIL", "CLOSED", "RELEASED"))
        self.assertEqual(self.external[0]["state"], "UNKNOWN")
        self.assertIn(b"SyntaxError", Path(result["captures"]["stderr"]["path"]).read_bytes())
        self.assertEqual(result["ordinary_failure"]["kind"], "ordinary_failure")
        self.assertIn("SyntaxError", result["ordinary_failure"]["defect"])
        self.assertEqual(result["ordinary_failure"]["diagnostic"]["stream"], "stderr")
        self.assertNotIn("qualification", result)
        self.assertEqual(self.runner().status()[0]["closure_proof"]["basis"], "original_wait_subreaper_echild_captures_closed")
        for identity in (result["owner_process"], result["original_process"]):
            self.assertIsInstance(identity["pid"], int)
            self.assertTrue(identity["start_ticks"].isdigit())
            self.assertTrue(identity["boot_id"])
        self.assertGreater(result["execution_deadline_utc_ns"], result["started_utc_ns"])

    def test_reaped_leader_never_reauthorizes_numeric_group_signals(self):
        handle = {"process": SimpleNamespace(returncode=0, pid=123), "pgid": 123, "identity": {}}
        backend = operations.HostProcessBackend()
        with patch.object(backend, "group_closed", return_value=False), patch("os.killpg") as signal_group:
            with self.assertRaisesRegex(ValueError, "unreaped"):
                backend.cleanup(handle, time.monotonic_ns() + 100_000_000)
        signal_group.assert_not_called()

    def test_post_spawn_descriptor_failure_cannot_be_positive_no_start(self):
        runner = self.runner()
        real_close, real_popen = operations.os.close, operations.subprocess.Popen
        state = {"proof_fd": None, "failed": False}
        def spawn(*args, **kwargs):
            process = real_popen(*args, **kwargs)
            state["proof_fd"] = kwargs["pass_fds"][0]
            return process
        def close(fd):
            if fd == state["proof_fd"] and not state["failed"]:
                state["failed"] = True
                raise OSError("post-spawn proof close failed")
            return real_close(fd)
        with patch.object(operations.subprocess, "Popen", side_effect=spawn), patch.object(
                operations.os, "close", side_effect=close):
            result = runner.run(self.spec(code="import time; time.sleep(.4)"))
        self.assertTrue(state["failed"])
        self.assertEqual(result["payload_state"], "UNKNOWN")
        self.assertEqual(result["custody_state"], "HELD_UNKNOWN")
        self.assertEqual(result["reservation"], "HELD")
        self.assertNotIn("closure_proof", result)
        self.assertIn("Post-start descriptor", result["primary_error"]["message"])
        self.assertEqual(self.backend.starts, 1)
        self.assertIsNotNone(self.backend.handles[0]["process"].returncode)

    def test_stale_resource_bookend_after_durable_start_intent_does_not_start(self):
        runner = self.runner()
        save = runner._save
        def age_resources(row):
            if row["phase"] == "STARTING":
                for key in ("observed_utc_ns", "observed_mono_ns"):
                    row["admissions"][0]["resources"][key] -= 26_000_000_000
            save(row)
        with patch.object(runner, "_save", side_effect=age_resources):
            result = runner.run(self.spec())
        self.assertEqual((result["payload_state"], result["custody_state"]), ("NOT_STARTED", "CLOSED"))
        self.assertEqual(self.backend.starts, 0)

    def test_timeout_preserves_partial_output_and_original_bounded_cleanup(self):
        spec = self.spec(code="import time; print('partial', flush=True); time.sleep(10)")
        spec["execution_timeout_s"] = 0.2
        started = time.monotonic()
        result = self.runner().run(spec)
        self.assertLess(time.monotonic() - started, 1.5)
        self.assertEqual((result["payload_state"], result["custody_state"], result["reservation"]),
                         ("UNKNOWN", "CLOSED", "RELEASED"))
        self.assertEqual([phase for phase, charges in self.proofs], ["execute", "cleanup"])
        self.assertEqual(self.proofs[1][1][0]["owner"], "operation:first")
        self.assertEqual(result["admissions"][1]["resources"]["accounted_total_jobs"], 1)
        self.assertEqual(Path(result["captures"]["stdout"]["path"]).read_text(), "partial\n")

    def test_detached_child_is_joined_before_positive_family_closure(self):
        child = "import os,time; os.setsid(); time.sleep(.25); print('late descendant', flush=True)"
        code = "import subprocess,sys; subprocess.Popen([sys.executable,'-c'," + repr(child) + "]); print('parent',flush=True)"
        started = time.monotonic()
        result = self.runner().run(self.spec(code=code))
        self.assertGreater(time.monotonic() - started, .25)
        self.assertEqual((result["payload_state"], result["custody_state"], result["reservation"]),
                         ("PASS", "CLOSED", "RELEASED"))
        self.assertEqual(result["family_closure"]["waitpid_terminal"], "ECHILD")
        self.assertEqual(result["family_closure"]["reaped_children"], 2)
        self.assertIn("late descendant", Path(result["captures"]["stdout"]["path"]).read_text())

    def test_detached_child_beyond_budget_keeps_hold_and_exact_test_cleanup(self):
        identity_path = self.root / "detached-child.json"
        child = ("import json,os,pathlib,time; os.setsid(); pid=os.getpid(); "
                 "start=pathlib.Path('/proc/'+str(pid)+'/stat').read_text().rpartition(') ')[2].split()[19]; "
                 "pathlib.Path(" + repr(str(identity_path)) + ").write_text(json.dumps({'pid':pid,'start_ticks':start})); "
                 "time.sleep(5)")
        code = "import subprocess,sys; subprocess.Popen([sys.executable,'-c'," + repr(child) + "])"
        spec = self.spec(code=code)
        spec["execution_timeout_s"], spec["cleanup_timeout_s"] = .2, .4
        result = None
        try:
            result = self.runner().run(spec)
            self.assertEqual((result["payload_state"], result["custody_state"], result["reservation"]),
                             ("UNKNOWN", "HELD_UNKNOWN", "HELD"))
            self.assertNotIn("family_closure", result)
        finally:
            # Only this test's exact privately recorded child is eligible. The
            # production runner does not rediscover, signal or adopt that PID.
            identity = json.loads(identity_path.read_text())
            pidfd = os.pidfd_open(identity["pid"])
            try:
                current = operations._process_identity(identity["pid"])
                self.assertEqual(current["start_ticks"], identity["start_ticks"])
                signal.pidfd_send_signal(pidfd, signal.SIGKILL)
            finally:
                os.close(pidfd)
            for _ in range(100):
                try:
                    state = Path('/proc/' + str(identity['pid']) + '/stat').read_text().rpartition(') ')[2].split()[0]
                except FileNotFoundError:
                    break
                if state == "Z":
                    break
                threading.Event().wait(.01)
            else:
                self.fail("Exact harmless detached child did not terminate")

    def test_ambiguous_start_restart_and_duplicate_never_replay(self):
        class Ambiguous(TrackingBackend):
            def start(inner, *args):
                inner.starts += 1
                raise RuntimeError("lost launch acknowledgement")
        backend = Ambiguous()
        result = self.runner(backend=backend).run(self.spec())
        self.assertEqual((result["payload_state"], result["custody_state"], result["reservation"]),
                         ("UNKNOWN", "HELD_UNKNOWN", "HELD"))
        restarted = self.runner(backend=backend)
        self.assertEqual(restarted.reconcile()[0]["reservation"], "HELD")
        with self.assertRaisesRegex(ValueError, "replay"):
            restarted.run(self.spec())
        self.assertEqual(backend.starts, 1)

    def test_journal_failure_before_start_never_launches(self):
        runner = self.runner()
        with patch.object(runner, "_save", side_effect=OSError("fsync refused")):
            with self.assertRaisesRegex(OSError, "fsync refused"):
                runner.run(self.spec())
        self.assertEqual(self.backend.starts, 0)

    def test_final_journal_failure_keeps_durable_charge_and_no_replay(self):
        runner = self.runner()
        save = runner._save
        def fail_final(row):
            if row["phase"] == "FINISHED":
                raise OSError("terminal journal unavailable")
            save(row)
        with patch.object(runner, "_save", side_effect=fail_final):
            with self.assertRaisesRegex(OSError, "terminal journal"):
                runner.run(self.spec())
        self.assertEqual(runner.status()[0]["reservation"], "ACTIVE")
        self.assertEqual(runner.reconcile()[0]["reservation"], "HELD")
        with self.assertRaisesRegex(ValueError, "replay"):
            runner.run(self.spec())
        self.assertEqual(self.backend.starts, 1)

    def test_cleanup_journal_failure_does_not_signal_or_release(self):
        runner = self.runner()
        save = runner._save
        def fail_cleanup(row):
            if row["phase"] == "CLEANING":
                raise OSError("cleanup admission could not be persisted")
            save(row)
        spec = self.spec(code="import time; time.sleep(.4)")
        spec["execution_timeout_s"] = .1
        with patch.object(runner, "_save", side_effect=fail_cleanup), patch.object(
                self.backend, "cleanup", wraps=self.backend.cleanup) as cleanup:
            result = runner.run(spec)
        cleanup.assert_not_called()
        self.assertEqual(result["reservation"], "HELD")
        self.assertEqual(result["primary_error"]["type"], "TimeoutExpired")
        self.backend.handles[0]["process"].wait(timeout=2)

    def test_duplicate_completed_id_also_never_starts_again(self):
        self.runner().run(self.spec())
        with self.assertRaisesRegex(ValueError, "replay"):
            self.runner().run(self.spec(code="print('different')"))
        self.assertEqual(self.backend.starts, 1)

    def test_final_slot_reservation_race_counts_all_active_operations(self):
        self.external = [{"owner": "old-family", "planning_bytes": 256 * MIB, "jobs": 2, "state": "UNKNOWN"}]
        started = threading.Event()
        class Notify(TrackingBackend):
            def start(inner, *args):
                result = super().start(*args)
                started.set()
                return result
        backend = Notify()
        outcomes = []
        def first():
            try:
                outcomes.append(self.runner(backend=backend).run(self.spec(code="import time; time.sleep(.6)")))
            except BaseException as error:
                outcomes.append(error)
        thread = threading.Thread(target=first)
        thread.start()
        self.assertTrue(started.wait(2))
        with self.assertRaisesRegex(RuntimeError, "4 GiB/max3"):
            self.runner(backend=backend).run(self.spec("second"))
        self.assertEqual(len(self.runner().status()), 2)
        thread.join(3)
        self.assertFalse(thread.is_alive())
        self.assertIsInstance(outcomes[0], dict)
        self.assertEqual(backend.starts, 1)

    def test_slow_admission_does_not_hold_unrelated_finalization_lock(self):
        first_started, first_finished, second_validating = (threading.Event() for _ in range(3))
        results = {}
        class Notify(TrackingBackend):
            def start(inner, spec, *args):
                handle = super().start(spec, *args)
                if spec.operation_id == "first":
                    first_started.set()
                return handle
        backend = Notify()
        def provider(spec, **kwargs):
            if spec.operation_id == "second" and kwargs["phase"] == "execute":
                second_validating.set()
                if not first_finished.wait(2):
                    raise TimeoutError("Other completed operation could not finalize")
            return self.provider(spec, **kwargs)
        def execute(ident, code):
            try:
                results[ident] = self.runner(provider=provider, backend=backend).run(self.spec(ident, code))
            except BaseException as error:
                results[ident] = error
            finally:
                if ident == "first":
                    first_finished.set()
        first = threading.Thread(target=execute, args=("first", "import time; time.sleep(.35)"))
        first.start()
        self.assertTrue(first_started.wait(2))
        second = threading.Thread(target=execute, args=("second", "print('second')"))
        second.start()
        self.assertTrue(second_validating.wait(2))
        first.join(2)
        second.join(2)
        self.assertFalse(first.is_alive())
        self.assertFalse(second.is_alive())
        for ident in ("first", "second"):
            self.assertIsInstance(results[ident], dict, str(results[ident]))
            self.assertEqual((results[ident]["payload_state"], results[ident]["custody_state"]), ("PASS", "CLOSED"))

    def test_denied_cleanup_is_finite_and_retains_own_family(self):
        def deny(spec, **kwargs):
            if kwargs["phase"] == "cleanup":
                raise PermissionError("original cleanup permission denied")
            return self.provider(spec, **kwargs)
        spec = self.spec(code="import time; time.sleep(.4)")
        spec["execution_timeout_s"] = .1
        started = time.monotonic()
        result = self.runner(provider=deny).run(spec)
        self.assertLess(time.monotonic() - started, .4)
        self.assertEqual((result["payload_state"], result["custody_state"], result["reservation"]),
                         ("UNKNOWN", "HELD_UNKNOWN", "HELD"))
        self.assertIn("permission denied", result["cleanup_errors"][0]["message"])
        self.assertEqual(result["primary_error"]["type"], "TimeoutExpired")
        # Test alone joins its harmless original child after the runner refused
        # cleanup. This does not change the durable HELD state or replay it.
        self.backend.handles[0]["process"].wait(timeout=2)
        self.assertEqual(self.runner().reconcile()[0]["reservation"], "HELD")

    def test_capture_error_preserves_primary_failure_and_hold(self):
        runner = self.runner()
        with patch.object(self.backend, "close_captures", side_effect=OSError("capture close failed")):
            result = runner.run(self.spec(code="raise SystemExit(7)"))
        self.assertEqual(result["payload_state"], "FAIL")
        self.assertEqual(result["custody_state"], "HELD_UNKNOWN")
        self.assertEqual(result["primary_error"]["stage"], "payload_exit")
        self.assertIn("capture close failed", result["cleanup_errors"][0]["message"])
        for stream in self.backend.handles[0]["streams"]:
            stream.close()

    def test_cleanup_callback_timeout_respects_original_budget(self):
        def blocked(spec, **kwargs):
            if kwargs["phase"] == "cleanup":
                time.sleep(.4)
            return self.provider(spec, **kwargs)
        spec = self.spec(code="import time; time.sleep(.4)")
        spec["execution_timeout_s"], spec["cleanup_timeout_s"] = .1, .1
        started = time.monotonic()
        with self.assertRaises(operations.OperationJournalError) as failure:
            self.runner(provider=blocked).run(spec)
        result = failure.exception.record
        self.assertLess(time.monotonic() - started, .4)
        self.assertEqual(result["reservation"], "HELD")
        self.backend.handles[0]["process"].wait(timeout=2)
        for stream in self.backend.handles[0]["streams"]:
            stream.close()

    def test_pending_admission_worker_blocks_new_ids_and_retains_charge(self):
        release = threading.Event()
        def blocked(spec, **kwargs):
            release.wait(1)
            return self.provider(spec, **kwargs)
        runner = self.runner(provider=blocked)
        spec = self.spec()
        spec["resources"]["max_age_ns"] = 50_000_000
        with self.assertRaisesRegex(TimeoutError, "worker retained"):
            runner.run(spec)
        row = runner.status()[0]
        self.assertEqual((row["reservation"], row["payload_state"]), ("HELD", "NOT_STARTED"))
        self.assertEqual(row["pending_worker"]["state"], "HELD_UNKNOWN")
        self.assertEqual(runner._charges([row])[0]["planning_bytes"], spec["resources"]["planning_bytes"])
        with self.assertRaisesRegex(ValueError, "pending worker"):
            self.runner(provider=blocked).run(self.spec("second"))
        self.assertEqual(self.backend.starts, 0)
        release.set()
        runner.workers["first"].join(timeout=2)

    def test_transaction_lock_deadline_is_finite(self):
        runner = self.runner()
        acquired, release = threading.Event(), threading.Event()
        def hold():
            with runner._lock(".transactions.lock"):
                acquired.set()
                release.wait(2)
        thread = threading.Thread(target=hold)
        thread.start()
        self.assertTrue(acquired.wait(1))
        started = time.monotonic()
        try:
            with self.assertRaisesRegex(TimeoutError, "lock deadline"):
                with runner._lock(".transactions.lock", deadline=time.monotonic_ns() + 50_000_000):
                    self.fail("entered contended lock")
            self.assertLess(time.monotonic() - started, .2)
        finally:
            release.set()
            thread.join(2)

    def test_journal_double_failure_retains_primary_in_exception_record(self):
        runner = self.runner()
        save = runner._save
        def fail_cleanup_and_final(row):
            if row["phase"] in {"CLEANING", "HELD"}:
                raise OSError("journal remains unavailable")
            save(row)
        spec = self.spec(code="import time; time.sleep(.4)")
        spec["execution_timeout_s"] = .1
        with patch.object(runner, "_save", side_effect=fail_cleanup_and_final):
            with self.assertRaises(operations.OperationJournalError) as failure:
                runner.run(spec)
        result = failure.exception.record
        self.assertEqual(result["primary_error"]["type"], "TimeoutExpired")
        self.assertGreaterEqual(len(result["journal_errors"]), 2)
        self.assertEqual(result["reservation"], "HELD")
        self.backend.handles[0]["process"].wait(timeout=2)
        for stream in self.backend.handles[0]["streams"]:
            stream.close()

    def test_repeated_failure_digest_ignores_attempt_and_output_changes(self):
        target = self.target()
        first = self.spec("first", "print('attempt 1'); raise SystemExit(1)")
        second = self.spec("second", "print('attempt 2'); raise SystemExit(1)")
        first["closure_target"] = second["closure_target"] = target
        left, right = self.runner().run(first), self.runner().run(second)
        self.assertNotEqual(left["captures"]["stdout"]["sha256"], right["captures"]["stdout"]["sha256"])
        self.assertEqual(left["ordinary_failure"]["diagnostic_sha256"], right["ordinary_failure"]["diagnostic_sha256"])


if __name__ == "__main__":
    unittest.main()
