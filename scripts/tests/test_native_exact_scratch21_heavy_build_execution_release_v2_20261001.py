#!/usr/bin/env python3
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

PATH = Path(__file__).parents[2] / "docs/verification/evidence/native-exact-scratch21-heavy-build-execution-release-v2-20261001.py"
SPEC = importlib.util.spec_from_file_location("scratch21_release_v2", PATH)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class ReleaseTests(unittest.TestCase):
    def test_exact_derivation(self):
        prepared = json.loads(MODULE.PREP.read_text())
        derived, raw = MODULE.derive(prepared)
        self.assertEqual(MODULE.sha(raw), MODULE.DERIVED_SHA256)
        self.assertFalse(derived["preparation_only"])
        self.assertTrue(derived["execution_released"])
        self.assertTrue(derived["executable"])
        self.assertFalse(derived["release_required"])
        changed = {key for key in prepared if prepared[key] != derived[key]}
        self.assertEqual(changed, {"preparation_only", "execution_released", "executable", "release_required"})

    def test_wrong_prepared_flags_refuse(self):
        prepared = json.loads(MODULE.PREP.read_text())
        prepared["executable"] = True
        with self.assertRaises(MODULE.Refusal):
            MODULE.derive(prepared)

    def test_publish_is_exclusive(self):
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / "request.json"
            raw = b"{}\n"
            MODULE.publish(target, raw)
            with self.assertRaises(FileExistsError):
                MODULE.publish(target, raw)

    def test_execution_uses_outer_wrapper_and_root_lock(self):
        source = PATH.read_text()
        self.assertIn("acquire_development_lock()", source)
        self.assertIn("str(WRAPPER), str(EXECUTION)", source)
        self.assertNotIn("str(CANDIDATE / \"scripts/native_rust_exact_build_container_owner.py\")", source)
        self.assertIn("cleanup_separately_required", source)
        self.assertIn("terminal_container_retained", source)
        self.assertIn("pass_fds=(lockfd,)", source)
        self.assertNotIn("timeout=19920", source)
        self.assertIn("signal.SIGHUP, signal.SIGINT, signal.SIGTERM", source)

    def test_only_positive_current_terminal_proves_retirement(self):
        good = {"retired": True, "cleanup_separately_required": True,
                "terminal_container_retained": True,
                "terminal_container_info": {"State": {"Running": False}},
                "terminal_container_info_current": True}
        self.assertTrue(MODULE.retirement_proven(good))
        for key, value in (("retired", False), ("cleanup_separately_required", False),
                           ("terminal_container_retained", None),
                           ("terminal_container_info", None),
                           ("terminal_container_info_current", False),
                           ("client_retirement_unproven", True)):
            bad = dict(good)
            bad[key] = value
            self.assertFalse(MODULE.retirement_proven(bad), key)

    def test_uncertain_started_build_quarantines_before_unlock(self):
        source = PATH.read_text()
        finally_block = source.split("    finally:\n        if build_started", 1)[1]
        self.assertLess(finally_block.index("quarantine_root_lock"),
                        finally_block.index("fcntl.flock(lockfd, fcntl.LOCK_UN)"))
        self.assertIn("def quarantine_wait():\n    while True:", source)

    def test_malformed_terminal_behavior_enters_quarantine(self):
        validate = SimpleNamespace(returncode=0, stdout=b"PASS_COMPATIBILITY_ONLY", stderr=b"")
        census = SimpleNamespace(returncode=0, stdout=b'{"status":"PASS_READ_ONLY"}', stderr=b"")
        with mock.patch.object(MODULE, "bind_release"), \
             mock.patch.object(MODULE, "acquire_development_lock", return_value=91), \
             mock.patch.object(MODULE, "preflight", side_effect=[({}, b"{}\n"), ({}, b"{}\n")]), \
             mock.patch.object(MODULE.subprocess, "run", side_effect=[validate, census]), \
             mock.patch.object(MODULE, "publish"), \
             mock.patch.object(MODULE, "run_checked", return_value=1), \
             mock.patch.object(MODULE, "stable_regular", side_effect=[b"malformed", b""]), \
             mock.patch.object(MODULE, "quarantine_root_lock", side_effect=RuntimeError("quarantined")) as quarantine, \
             mock.patch.object(MODULE.signal, "getsignal", return_value=None), \
             mock.patch.object(MODULE.signal, "signal"), \
             mock.patch.object(MODULE.fcntl, "flock") as flock:
            with self.assertRaisesRegex(RuntimeError, "quarantined"):
                MODULE.execute("0" * 40)
        quarantine.assert_called_once_with(91, "build-started-without-positive-terminal-retirement")
        flock.assert_not_called()

    def test_quarantine_evidence_failure_still_waits(self):
        with mock.patch.object(MODULE.os.path, "lexists", return_value=False), \
             mock.patch.object(MODULE, "publish", side_effect=OSError("full")), \
             mock.patch.object(MODULE, "quarantine_wait", side_effect=RuntimeError("held")) as wait:
            with self.assertRaisesRegex(RuntimeError, "held"):
                MODULE.quarantine_root_lock(91, "uncertain")
        wait.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
