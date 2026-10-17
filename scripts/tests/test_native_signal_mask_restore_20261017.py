"""Cheap preparation checks; synthetic protocol records are never guest evidence.

Run: python3 -B -m unittest discover -s scripts/tests \
    -p test_native_signal_mask_restore_20261017.py -v
No native compiler, process payload, container, privilege or network is used.
"""
import copy
import hashlib
import importlib.util
import itertools
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "scripts/application-tests"
EXPECTED = b"handled=1 observed_blocked=1 restored=1\n"
SPEC = importlib.util.spec_from_file_location("mask_restore_diagnostic", APP / "native_diagnostic.py")
ND = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ND)


def fixture():
    """Minimal evaluate-only input; no artifact admission or execution claim."""
    payload = {
        "argv": ["/bin/mcexec", "-t", "1", "0", "app", "A", "", "B"],
        "cwd": "/case/work", "env": {"PATH": "/usr/bin:/bin", "COKERNEL_PATH": "/apps"},
        "oracle": {"stdout_hex": EXPECTED.hex(), "stderr_hex": "", "exit_code": 0},
        "stdout_limit_bytes": 1024, "stderr_limit_bytes": 1024,
    }
    report = {key: copy.deepcopy(payload[key]) for key in ("argv", "cwd", "env")}
    report.update(raw_wait_status=0, started_ns=100, reaped_ns=200,
                  finished_ns=300, procfs_empty=True, streams={})
    for name, data in (("stdout", EXPECTED), ("stderr", b"")):
        report["streams"][name] = {
            "hex": data.hex(), "eof": True, "truncated": False,
            "observed": len(data), "retained": len(data), "discarded": 0,
            "limit": 1024, "eof_ns": 250,
        }
    serial = [
        "application SCHEDULE os=0 generation=1 pid=12 cpu=0",
        "application procfs published os=0 generation=1 pid=12 tid=12",
        "application_syscall=delivered os=0 generation=1 pid=12 worker=9 delivery=3 cpu=0 number=1",
        "application_syscall=return_route os=0 generation=1 pid=12 worker=9 delivery=3 launcher_cpu=1 guest_cpu=0",
        "application_syscall=returned os=0 generation=1 pid=12 worker=9 delivery=3 cpu=0 value=40",
        "application_syscall=delivered os=0 generation=1 pid=12 worker=9 delivery=4 cpu=0 number=231",
        "application procfs deleted os=0 generation=1 pid=12 tid=12",
        "application retirement os=0 generation=1 pid=12 token=2 errno=0",
        "application_process=release os=0 generation=1 pid=12 cleanup_errno=0",
    ]
    observation = {
        "debugcon": "", "qmp": {"status": "shutdown"}, "teardown": True,
        "started_at": 1, "finished_at": 2, "deadline": 3,
        "process_identity": {"pid": 12345, "pgid": 12345, "sid": 12345, "starttime_ticks": 1},
    }
    return {"case_id": "signal.mask-restore", "payload": payload}, report, serial, observation


def observe(report, serial, observation):
    return dict(observation, serial="\n".join(serial + ["ND_PAYLOAD " + json.dumps(report), ""]))


class MaskRestorePreparation(unittest.TestCase):
    def test_frozen_inputs_and_exact_bytes(self):
        hashes = {
            "cases/signal/signal.mask-restore.c": "c5c7803f9d9592151d1c3508d832cd1c26aafca3ac55c420c209b1bc1c740a57",
            "oracles/signal.mask-restore.json": "9f7f1d39a26e9016331e1ad2032062d84feb72c23540064fe1994dd00dc56759",
        }
        for name, digest in hashes.items():
            self.assertEqual(hashlib.sha256((APP / name).read_bytes()).hexdigest(), digest)
        oracle = json.loads((APP / "oracles/signal.mask-restore.json").read_text())
        self.assertEqual(("\n".join(oracle["stdout"]["lines"]) + "\n").encode(), EXPECTED)
        self.assertEqual(oracle["stderr"], {"kind": "exact-bytes", "hex": ""})
        self.assertEqual(oracle["wait_status"], {"kind": "exited", "code": 0})

    def test_independent_posix_set_rule_and_scope_counterexample(self):
        # Specification model only: no implementation or runtime claim.
        # Without SA_NODEFER, entry mask is baseline | sa_mask | {delivered}.
        for bits in itertools.product((False, True), repeat=3):
            baseline = {s for s, blocked in zip(("USR1", "USR2", "TERM"), bits) if blocked}
            entry = baseline | {"USR2"} | {"USR1"}
            self.assertTrue({"USR1", "USR2"} <= entry)
            restored = entry - (entry - baseline)
            self.assertEqual(restored, baseline)
        # The frozen payload checks only two signals: it cannot certify an
        # arbitrary caller mask or detect a faulty restoration of SIGTERM.
        baseline, faulty_after = {"TERM"}, set()
        self.assertTrue(all((s in baseline) == (s in faulty_after) for s in ("USR1", "USR2")))
        self.assertNotEqual(baseline, faulty_after)

    def test_collector_protocol_accepts_only_as_nonacceptance(self):
        manifest, report, serial, observation = fixture()
        result = ND.evaluate(manifest, observe(report, serial, observation))
        self.assertEqual(result["status"], "PROTOCOL_PASS")
        self.assertFalse(result["application_acceptance"])
        self.assertFalse(result["mckernel_application_executed"])

    def test_rejects_altered_streams_status_or_retirement(self):
        variants = (
            ("missing newline", lambda r: r["streams"]["stdout"].update(hex=EXPECTED[:-1].hex(), observed=len(EXPECTED)-1, retained=len(EXPECTED)-1)),
            ("stderr", lambda r: r["streams"]["stderr"].update(hex="78", observed=1, retained=1)),
            ("nonzero exit", lambda r: r.update(raw_wait_status=256)),
            ("signaled", lambda r: r.update(raw_wait_status=11)),
            ("procfs remains", lambda r: r.update(procfs_empty=False)),
            ("no EOF", lambda r: r["streams"]["stdout"].update(eof=False)),
            ("truncation", lambda r: r["streams"]["stdout"].update(truncated=True)),
            ("wrong launch argv", lambda r: r["argv"].pop()),
        )
        for name, change in variants:
            with self.subTest(name=name):
                manifest, report, serial, observation = fixture()
                change(report)
                with self.assertRaises(ND.DiagnosticError):
                    ND.evaluate(manifest, observe(report, serial, observation))

    def test_rejects_missing_route_or_shutdown_or_teardown(self):
        for missing in ("return_route", "application retirement", "application_process=release", "procfs deleted"):
            with self.subTest(missing=missing):
                manifest, report, serial, observation = fixture()
                serial = [line for line in serial if missing not in line]
                with self.assertRaises(ND.DiagnosticError):
                    ND.evaluate(manifest, observe(report, serial, observation))
        for field, value in (("qmp", {"status": "running"}), ("teardown", False)):
            manifest, report, serial, observation = fixture()
            observation[field] = value
            with self.assertRaises(ND.DiagnosticError):
                ND.evaluate(manifest, observe(report, serial, observation))


if __name__ == "__main__":
    unittest.main()
