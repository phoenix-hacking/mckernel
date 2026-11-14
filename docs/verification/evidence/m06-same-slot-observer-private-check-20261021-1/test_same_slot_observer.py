#!/usr/bin/env python3
"""Bounded ordinary trace-checker regressions; no backend, compiler, or guest.

Positive retained serial is real CLOSED evidence. Mutations are synthetic refusal
fixtures and never native acceptance. Local435/no-child evidence stays OPEN.
"""
import ast
import copy
import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parent
PREFIX = r"os=0 generation=1 pid=257"
SERIAL = (ROOT / "retained-serial.log").read_text()
EXPECTED = b"rc=-1 errno=95 eopnotsupp=1 child_created=0\n"

def load(filename, name):
    spec = importlib.util.spec_from_file_location(name, ROOT / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

ORIGINAL = load("native_diagnostic.original.py", "m06_original")
FIXED = load("native_diagnostic.py", "m06_fixed")

def changed_once(serial, old, new):
    assert serial.count(old) == 1, old
    return serial.replace(old, new, 1)

def delivered(delivery):
    return next(line for line in SERIAL.splitlines()
                if "application_syscall=delivered " in line and
                f" delivery={delivery} " in line)

def returned(delivery):
    return next(line for line in SERIAL.splitlines()
                if "application_syscall=returned " in line and
                f" delivery={delivery} " in line)

def route(delivery, launcher=1, guest=0):
    # Synthetic cross-slot witness, never relabelled as actual native evidence.
    return (f"mcctrl: application_syscall=return_route {PREFIX} worker=5 "
            f"delivery={delivery} launcher_cpu={launcher} guest_cpu={guest}")

def cross_slot():
    value = SERIAL
    for delivery in (8, 9, 11, 12):
        ret = returned(delivery)
        value = changed_once(value, ret, route(delivery) + "\n" + ret)
    return value

class SameSlotObserverRegression(unittest.TestCase):
    def test_original_failure_preserved(self):
        failure = json.loads((ROOT / "retained-failed-result.json").read_text())
        self.assertEqual(failure["status"], "FAIL")
        self.assertEqual(failure["failure"]["error"], "missing actual route/exit evidence")
        with self.assertRaisesRegex(ORIGINAL.DiagnosticError,
                                    "missing actual route/exit evidence"):
            ORIGINAL._check_syscall_trace(SERIAL, PREFIX)

    def test_genuine_retained_same_slot_trace(self):
        self.assertNotIn("application_syscall=return_route ", SERIAL)
        self.assertEqual(FIXED._check_syscall_trace(SERIAL, PREFIX), None)

    def test_app_oracle_and_other_evaluator_code_preserved(self):
        report = json.loads(next(line[len("ND_PAYLOAD "):] for line in
                                 SERIAL.splitlines() if line.startswith("ND_PAYLOAD ")))
        oracle = json.loads((ROOT / "retained-stage-manifest.json").read_text())["payload"]["oracle"]
        self.assertEqual(bytes.fromhex(oracle["stdout_hex"]), EXPECTED)
        self.assertEqual(bytes.fromhex(report["streams"]["stdout"]["hex"]), EXPECTED)
        self.assertEqual(oracle["stderr_hex"], "")
        self.assertEqual(report["streams"]["stderr"]["hex"], "")
        self.assertEqual(oracle["exit_code"], 0)
        self.assertEqual(report["raw_wait_status"], 0)
        for stream in report["streams"].values():
            self.assertTrue(stream["eof"])
            self.assertFalse(stream["truncated"])
            self.assertEqual(stream["discarded"], 0)
        # Only the one false global route-presence predicate changes. No payload,
        # route join, CPU, worker consistency, or terminal predicate is edited.
        original = ast.parse((ROOT / "native_diagnostic.original.py").read_text())
        fixed = ast.parse((ROOT / "native_diagnostic.py").read_text())
        def normalize(tree):
            for node in tree.body:
                if isinstance(node, ast.FunctionDef) and node.name == "_check_syscall_trace":
                    for child in ast.walk(node):
                        if isinstance(child, ast.BoolOp) and isinstance(child.op, ast.And):
                            child.values = [value for value in child.values
                                            if not (isinstance(value, ast.Name) and value.id == "routes")]
            return ast.dump(tree, include_attributes=False)
        self.assertEqual(normalize(original), normalize(fixed))

    def test_synthetic_valid_cross_slot(self):
        self.assertIsNone(FIXED._check_syscall_trace(cross_slot(), PREFIX))

    def test_refusal_vectors(self):
        begin, ret = delivered(8), returned(8)
        terminal = delivered(13)
        variants = {
            "malformed": (changed_once(SERIAL, begin, begin + " extra"), "malformed or foreign"),
            "foreign": (changed_once(SERIAL, begin, begin.replace("pid=257", "pid=258")), "malformed or foreign"),
            "missing return": (changed_once(SERIAL, ret + "\n", ""), "incomplete syscall correspondence"),
            "duplicate delivery": (changed_once(SERIAL, begin, begin + "\n" + begin), "duplicate syscall delivered"),
            "duplicate return": (changed_once(SERIAL, ret, ret + "\n" + ret), "duplicate syscall returned"),
            "orphan return": (changed_once(SERIAL, ret, ret.replace("delivery=8", "delivery=999")), "incomplete syscall correspondence"),
            "missing exit": (changed_once(SERIAL, terminal + "\n", ""), "missing actual route/exit evidence"),
            "second exit": (changed_once(SERIAL, terminal, terminal + "\n" + terminal.replace("delivery=13", "delivery=999")), "missing actual route/exit evidence"),
            "wrong guest CPU": (changed_once(SERIAL, begin, begin.replace("cpu=0", "cpu=1")), "unexpected guest CPU"),
            "return before delivery": (changed_once(changed_once(SERIAL, ret + "\n", ""), begin, ret + "\n" + begin), "syscall/terminal-exit ordering"),
            "return after terminal": (changed_once(changed_once(SERIAL, ret + "\n", ""), terminal, terminal + "\n" + ret), "syscall/terminal-exit ordering"),
            "non-group exit": (changed_once(SERIAL, begin, begin.replace("number=63", "number=60")), "unexpected non-group exit"),
            "route on terminal": (changed_once(SERIAL, terminal, terminal + "\n" + route(13)), "incomplete syscall correspondence"),
        }
        cross = cross_slot()
        variants.update({
            "missing one cross-slot route": (changed_once(cross, route(9) + "\n", ""), "missing/inconsistent worker route"),
            "wrong cross-slot launcher": (changed_once(cross, route(8), route(8, launcher=2)), "route identity/CPU mismatch"),
            "wrong cross-slot guest": (changed_once(cross, route(8), route(8, guest=1)), "route identity/CPU mismatch"),
            "cross-slot route after return": (changed_once(cross, route(8) + "\n" + ret, ret + "\n" + route(8)), "route identity/CPU mismatch"),
            "duplicate route": (changed_once(cross, route(8), route(8) + "\n" + route(8)), "duplicate syscall return_route"),
        })
        for name, (serial, message) in variants.items():
            with self.subTest(name=name):
                with self.assertRaisesRegex(FIXED.DiagnosticError, message):
                    FIXED._check_syscall_trace(serial, PREFIX)

if __name__ == "__main__":
    unittest.main(verbosity=2)
