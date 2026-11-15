"""Offline latewait fixtures: fake original Popen, real own pipes/files only.

Functional McKernel OS/Rust only; NO SECURITY TESTING. No subprocess creation,
signals, live process lookup, account/Docker/native operation or campaign writes.
"""
import ast
import datetime
import json
import os
from pathlib import Path
import pathlib
import re
import selectors
import signal
import subprocess
import sys
import tempfile
import traceback
import unittest
from unittest.mock import patch


CANDIDATE = Path(__file__).with_name("candidate_capture_root_once.py")
KEEPER = Path(__file__).with_name("qualified_keeper_fixture.py")


class OriginalPopen:
    pid = 1073741823

    def __init__(self, live=False):
        self.live = live
        self.returncode = None
        self.wait_calls = []

    def wait(self, timeout):
        self.wait_calls.append(timeout)
        if self.live:
            raise subprocess.TimeoutExpired("original-fixture", timeout)
        self.returncode = -15
        return self.returncode


class AmbiguousClose:
    def __init__(self, stream):
        self.stream = stream
        self.close_calls = 0

    @property
    def closed(self):
        return self.stream.closed

    def fileno(self):
        return self.stream.fileno()

    def close(self):
        self.close_calls += 1
        self.stream.close()
        raise OSError("close result ambiguous after actual original close")


class CaptureLatewaitFixtures(unittest.TestCase):
    def fixture(self, *, live=False, close_failure=False, persist_failure=False):
        temporary = tempfile.TemporaryDirectory(prefix="capture-latewait-fixture-")
        self.addCleanup(temporary.cleanup)
        out = Path(temporary.name)
        ns = dict(os=os, pathlib=pathlib, re=re, json=json, datetime=datetime,
                  selectors=selectors, subprocess=subprocess, signal=signal, sys=sys,
                  traceback=traceback, OUT=out, ACTIVE_CONTEXTS=[], DATA_CONTEXTS=[],
                  HELD_CONTAINERS=[], pending_calls={}, clients=[], RAW_ERRORS=[],
                  keeper_capture_errors=[], OUTER_RETENTION_ERRORS=[], OUTER_ORIGINAL_WAITS=[])
        names = {"now", "save", "record_raw", "write_exact", "finish_late_original_capture"}
        tree = ast.parse(CANDIDATE.read_text())
        selected = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in names]
        self.assertEqual({node.name for node in selected}, names)
        exec(compile(ast.Module(body=selected, type_ignores=[]), str(CANDIDATE), "exec"), ns)
        names = {"keeper_record", "preserve_original_pending_waits", "retain_outer_error",
                 "retain_original_pending_nonescaping", "entry_once_with_original_custody"}
        tree = ast.parse(KEEPER.read_text())
        selected = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in names]
        self.assertEqual({node.name for node in selected}, names)
        exec(compile(ast.Module(body=selected, type_ignores=[]), str(KEEPER), "exec"), ns)
        process = OriginalPopen(live=live)
        primary = TimeoutError("original supplier child deadline expired: Root-parent")
        row = dict(attempt_id=0, label="Root-parent", pid=process.pid, exit="UNKNOWN",
                   direct_wait_joined=False, streams_closed=False, input_FD_closed=False,
                   capture_FDs_closed=False, captures_fsynced=False, receipt_persisted=False,
                   lifecycle_UNKNOWN=True, resource_charge_retained=True,
                   stdout_limit_bytes=1024, stderr_limit_bytes=1024, stdout_bytes=0,
                   stderr_bytes=0, primary_error=type(primary).__name__ + ": " + str(primary), secondary_errors=[])
        context = dict(record=row, process=process, selector=selectors.DefaultSelector(),
                       capture_fds={}, pipe_streams={}, input_fd=os.open("/dev/null", os.O_RDONLY),
                       primary_raw=primary, primary_tb=None, secondary_raw=[])
        expected = {"stdout": b"late original stdout\n", "stderr": b"late original traceback bytes\n"}
        ambiguous = None
        for name, content in expected.items():
            read_fd, write_fd = os.pipe()
            os.write(write_fd, content)
            os.close(write_fd)
            stream = os.fdopen(read_fd, "rb", buffering=0)
            if name == "stdout" and close_failure:
                stream = ambiguous = AmbiguousClose(stream)
            os.set_blocking(stream.fileno(), False)
            context["pipe_streams"][name] = stream
            context["selector"].register(stream, selectors.EVENT_READ, name)
            context["capture_fds"][name] = os.open(out / ("Root-parent." + name),
                os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        ns["clients"].append(row)
        ns["ACTIVE_CONTEXTS"].append(context)
        ns["pending_calls"][0] = process
        final_save_calls = []
        actual_save = ns["save"]

        def save(name, value):
            if name == "CLIENTS.json" and row.get("late_original_capture_completed"):
                final_save_calls.append(name)
                if persist_failure:
                    raise OSError("final late capture receipt persistence failed")
            return actual_save(name, value)

        ns["save"] = save

        def cleanup_fixture_fds():
            for stream in context["pipe_streams"].values():
                if not stream.closed:
                    stream.close()
            if context["selector"].get_map() is not None:
                context["selector"].close()
            if context["input_fd"] is not None:
                os.close(context["input_fd"])
                context["input_fd"] = None
            for fd in context["capture_fds"].values():
                os.close(fd)
            context["capture_fds"].clear()

        self.addCleanup(cleanup_fixture_fds)
        return ns, row, context, process, primary, expected, ambiguous, final_save_calls

    def no_process_lookup(self):
        actual = Path.read_text

        def own_children(path, *args, **kwargs):
            if str(path).startswith("/proc/self/task/") and str(path).endswith("/children"):
                return ""  # Offline original-children observation; never reads live /proc.
            return actual(path, *args, **kwargs)

        return patch.object(Path, "read_text", own_children)

    def join_original_fixture(self, ns, process):
        ns["preserve_original_pending_waits"]()
        self.assertEqual(process.wait_calls, [30])

    def test_late_original_wait_finishes_real_capture_fds_and_propagates_initial_timeout(self):
        ns, row, context, process, primary, expected, _, saves = self.fixture()

        def main():
            try:
                raise primary
            except TimeoutError as error:
                context["primary_tb"] = error.__traceback__
                raise

        ns["main"] = main
        with self.no_process_lookup(), self.assertRaises(TimeoutError) as caught:
            try:
                ns["entry_once_with_original_custody"]()
            finally:
                for original in tuple(ns["ACTIVE_CONTEXTS"]):
                    self.assertTrue(ns["finish_late_original_capture"](original))
        self.assertIs(caught.exception, primary)
        self.assertIs(context["primary_raw"], primary)
        self.assertIsNotNone(context["primary_tb"])
        self.assertEqual(process.wait_calls, [30, 0])
        self.assertEqual(row["exit"], "UNKNOWN")
        self.assertFalse(row["direct_wait_joined"])
        self.assertTrue(row["late_original_direct_wait_joined"])
        self.assertEqual(row["late_original_exit"], -15)
        self.assertIn("TimeoutError", row["primary_error"])
        self.assertEqual(ns["ACTIVE_CONTEXTS"], [])
        self.assertEqual(ns["DATA_CONTEXTS"], [])
        self.assertEqual(ns["pending_calls"], {})
        self.assertEqual(saves, ["CLIENTS.json"])
        for name, content in expected.items():
            self.assertEqual((ns["OUT"] / ("Root-parent." + name)).read_bytes(), content)
        persisted = json.loads((ns["OUT"] / "CLIENTS.json").read_text())[0]
        self.assertTrue(persisted["late_original_capture_completed"])
        self.assertTrue(persisted["input_FD_closed"] and persisted["captures_fsynced"] and persisted["receipt_persisted"])

    def test_still_live_or_prior_ambiguous_close_keeps_original_custody_untouched(self):
        ns, row, context, process, _, _, _, saves = self.fixture(live=True)
        original_input = context["input_fd"]
        self.assertFalse(ns["finish_late_original_capture"](context))
        self.assertEqual(process.wait_calls, [])
        self.assertTrue(os.fstat(original_input))
        self.assertTrue(all(not stream.closed for stream in context["pipe_streams"].values()))
        self.assertEqual(ns["pending_calls"], {0: process})
        self.assertEqual(saves, [])
        # A timeout from a normal-close syscall is not the original deadline.
        context["primary_raw"] = TimeoutError("close syscall result uncertain")
        row.update(late_original_direct_wait_joined=True, late_original_exit=-15)
        process.returncode = -15
        self.assertFalse(ns["finish_late_original_capture"](context))
        self.assertNotIn("late_capture_completion_attempted", context)

    def test_close_or_receipt_failure_keeps_context_and_never_retries_ambiguous_fds(self):
        for failure in ("close", "persist"):
            with self.subTest(failure=failure):
                ns, row, context, process, primary, _, ambiguous, saves = self.fixture(
                    close_failure=failure == "close", persist_failure=failure == "persist")
                self.join_original_fixture(ns, process)
                with self.no_process_lookup():
                    self.assertFalse(ns["finish_late_original_capture"](context))
                    self.assertFalse(ns["finish_late_original_capture"](context))
                self.assertIs(context["primary_raw"], primary)
                self.assertTrue(context["late_capture_completion_attempted"])
                self.assertEqual(ns["ACTIVE_CONTEXTS"], [context])
                self.assertTrue(row["resource_charge_retained"] and row["lifecycle_UNKNOWN"])
                self.assertFalse(row["receipt_persisted"])
                self.assertEqual(len(context["secondary_raw"]), 1)
                if failure == "close":
                    self.assertEqual(ambiguous.close_calls, 1)
                    self.assertTrue(os.fstat(context["input_fd"]))
                    self.assertEqual(saves, [])
                else:
                    self.assertIsNone(context["input_fd"])
                    self.assertEqual(context["capture_fds"], {})
                    self.assertTrue(row["capture_FDs_closed"])
                    self.assertEqual(saves, ["CLIENTS.json"])


if __name__ == "__main__":
    unittest.main()
