"""Offline tests only: no device, PID1, guest or native probe execution."""
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "lifecycle_capture", ROOT / "scripts/application-tests/native_diagnostic_lifecycle_capture.py")
PARSER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PARSER)


def probe_records():
    rows = []
    for operation, request, result in (("open", 0, 4), ("status_before", 0x112a03, 5),
                                       ("shutdown", 0x112a02, 0), ("status_after", 0x112a03, 0),
                                       ("close", 0, 0)):
        rows.append(dict(operation=operation, request=request, **{
            "return": result, "errno": 0, "linux_result": result}))
    rows.append(dict(result="PASS", transition_observed=True, resource_restoration_verified=False))
    return rows


def encode_probe(rows):
    return ("\n".join(json.dumps(r, separators=(",", ":")) for r in rows) + "\n").encode()


def stream(data):
    return dict(hex=data.hex(), eof=True, truncated=False, observed=len(data),
                retained=len(data), discarded=0, limit=1024, eof_ns=25)


def fixture(rows=None):
    return [dict(argv=["/bin/native-lifecycle-probe", "0"], helper_result=0, raw_wait_status=0,
                 fault=0, timeout=0, clean=1, child_stage=0, child_errno=0,
                 started_ns=10, reaped_ns=20, finished_ns=30),
            dict(name="stdout", capture=stream(encode_probe(rows or probe_records()))),
            dict(name="stderr", capture=stream(b"")),
            # Deliberately opaque: the lifecycle parser must never accept payloads.
            dict(opaque_payload_requires_independent_oracle=True)]


def wire(rows):
    return "\n".join(prefix + " " + json.dumps(row, separators=(",", ":"))
                     for prefix, row in zip(("ND_LIFECYCLE", "ND_LIFECYCLE_STREAM",
                                              "ND_LIFECYCLE_STREAM", "ND_PAYLOAD"), rows)) + "\n"


class LifecycleCaptureTests(unittest.TestCase):
    def reject(self, text):
        with self.assertRaises(PARSER.LifecycleCaptureError):
            PARSER.validate_lifecycle_capture(text)

    def test_transition_and_explicit_independent_payload_boundary(self):
        result = PARSER.validate_lifecycle_capture(wire(fixture()))
        self.assertEqual(result, dict(status="LIFECYCLE_DIAGNOSTIC_PASS", transition_observed=True,
                                    status_before=5, status_after=0, os_destroyed=False,
                                    resource_restoration_verified=False, payload_validation_required=True))

    def test_crlf_console_and_column_zero_prefix(self):
        serial = "kernel boot log\r\n" + wire(fixture()).replace("\n", "\r\n")
        self.assertTrue(PARSER.validate_lifecycle_capture(serial)["transition_observed"])
        self.reject("[prefix] " + wire(fixture()))

    def test_missing_duplicate_and_wrong_order_records(self):
        lines = wire(fixture()).splitlines(keepends=True)
        for index in range(4):
            with self.subTest(missing=index):
                self.reject("".join(lines[:index] + lines[index + 1:]))
            with self.subTest(duplicate=index):
                self.reject("".join(lines[:index] + [lines[index]] + lines[index:]))
        for order in ((1, 0, 2, 3), (0, 2, 1, 3), (3, 0, 1, 2)):
            self.reject("".join(lines[i] for i in order))
        self.reject("".join(lines).rstrip("\n"))

    def test_transport_unknown_keys_and_duplicate_json_keys(self):
        for index in range(3):
            rows = fixture()
            rows[index]["unknown"] = 1
            self.reject(wire(rows))
        rows = fixture()
        rows[1]["capture"]["unknown"] = 1
        self.reject(wire(rows))
        self.reject(wire(fixture()).replace('"helper_result":0', '"helper_result":0,"helper_result":0'))
        self.reject(wire(fixture()).replace('"retained":', '"eof":true,"retained":', 1))
        self.reject(wire(fixture()).replace("ND_LIFECYCLE ", "ND_LIFECYCLE_UNKNOWN ", 1))

    def test_helper_failure_fields_and_integer_types(self):
        original = fixture()
        for name in original[0]:
            if name == "argv":
                continue
            rows = copy.deepcopy(original)
            rows[0][name] = True
            with self.subTest(boolean=name):
                self.reject(wire(rows))
        for name in ("helper_result", "raw_wait_status", "fault", "timeout", "child_stage", "child_errno"):
            rows = fixture()
            rows[0][name] = 1
            self.reject(wire(rows))
        for key, value in (("clean", 0), ("raw_wait_status", 256), ("raw_wait_status", 9),
                           ("helper_result", -1), ("started_ns", 0), ("reaped_ns", 9),
                           ("finished_ns", 19), ("finished_ns", 1 << 64),
                           ("argv", ["/bin/native-lifecycle-probe", "/dev/mcos0"])):
            rows = fixture()
            rows[0][key] = value
            self.reject(wire(rows))

    def test_stream_accounting_eof_timestamps_and_types(self):
        mutations = (("hex", "zz"), ("hex", "AA"), ("hex", "0"),
                     ("hex", "00" * 1025), ("eof", False), ("eof", 1),
                     ("truncated", True), ("truncated", 0), ("observed", 999),
                     ("retained", 999), ("discarded", 1), ("limit", 4096),
                     ("eof_ns", 9), ("eof_ns", 31), ("eof_ns", 0))
        for index in (1, 2):
            for key, value in mutations:
                rows = fixture()
                rows[index]["capture"][key] = value
                with self.subTest(stream=index, key=key, value=value):
                    self.reject(wire(rows))
            for key in ("observed", "retained", "discarded", "limit", "eof_ns"):
                rows = fixture()
                rows[index]["capture"][key] = False
                self.reject(wire(rows))
        rows = fixture()
        rows[2]["capture"] = stream(b"error\n")
        self.reject(wire(rows))

    def test_probe_operation_results_and_transition_credit(self):
        for index in range(5):
            for key, value in (("request", 99), ("return", -1), ("errno", 5),
                               ("linux_result", -5), ("return", True),
                               ("errno", False), ("request", False),
                               ("linux_result", False), ("operation", "wrong"), ("unknown", 0)):
                rows = probe_records()
                rows[index][key] = value
                with self.subTest(index=index, key=key):
                    self.reject(wire(fixture(rows)))
        for before in (0, 1, 2, 3, 4, 6, 7):
            rows = probe_records()
            rows[1]["return"] = rows[1]["linux_result"] = before
            rows[5]["transition_observed"] = before != 0
            self.reject(wire(fixture(rows)))
        for key, value in (("result", "FAIL"), ("transition_observed", False),
                           ("transition_observed", 1), ("resource_restoration_verified", True),
                           ("resource_restoration_verified", 0), ("unknown", 0)):
            rows = probe_records()
            rows[5][key] = value
            self.reject(wire(fixture(rows)))

    def test_booted_three_is_not_running_ioctl_status(self):
        rows = probe_records()
        rows[1]["return"] = rows[1]["linux_result"] = 3
        self.reject(wire(fixture(rows)))

    def test_probe_missing_duplicate_truncated_and_non_json_bytes(self):
        original = probe_records()
        for index in range(6):
            rows = original[:index] + original[index + 1:]
            self.reject(wire(fixture(rows)))
            self.reject(wire(fixture(original[:index] + [original[index]] + original[index:])))
        valid = encode_probe(original)
        for data in (valid[:-1], valid.replace(b"\n", b"\r\n"), b"\xff\n", b"not JSON\n",
                     valid.replace(b'"request":0', b'"request":0,"request":0', 1),
                     valid.replace(b'"return":4', b'"return":NaN', 1)):
            rows = fixture()
            rows[1]["capture"] = stream(data)
            self.reject(wire(rows))

    def test_bounded_serial_and_transport_records(self):
        self.reject("x" * (PARSER.MAX_SERIAL_BYTES + 1))
        self.reject("\u00e9" * (PARSER.MAX_SERIAL_BYTES // 2 + 1))
        self.reject(wire(fixture()).replace("ND_LIFECYCLE ", "ND_LIFECYCLE " + " " * 4096, 1))
        self.reject(wire(fixture()).replace("ND_PAYLOAD ", "ND_PAYLOAD " + " " * 4096, 1))
        self.reject(None)
        self.reject("\ud800")
        self.reject(wire(fixture()).replace('"helper_result":0', '"helper_result":NaN'))

    def test_retained_actual_c_serializer_rejected_for_nonprobe_bytes(self):
        # Retained actual serializer stdout has synthetic binary stream bytes;
        # transport succeeds but it must never receive transition credit.
        source = Path(os.environ["LIFECYCLE_SERIALIZER_STDOUT"])
        serial = source.read_text()
        self.assertIn("ND_LIFECYCLE_STREAM", serial)
        self.reject(serial + "ND_PAYLOAD {}\n")


# Actual collector functions execute with injected captured bytes/timestamps;
# its renamed PID1 main, supervisor and all device operations remain uncalled.
CROSSBODY_HARNESS = r'''
#define main collector_pid1_main_never_called
#include "COLLECTOR_SOURCE"
#undef main
#include <assert.h>
int main(int argc, char **argv)
{
    struct result captured, payload;
    assert(argc == 2);
    memset(&captured, 0, sizeof captured);
    captured.clean = captured.out.eof = captured.err.eof = 1;
    captured.started = 10; captured.reaped = 20; captured.finished = 30;
    captured.out.eof_ns = captured.err.eof_ns = 25;
    FILE *input = fopen(argv[1], "rb");
    assert(input);
    size_t count = fread(captured.out.data, 1, STREAM_LIMIT, input);
    assert(!ferror(input) && count < STREAM_LIMIT && fgetc(input) == EOF);
    assert(fclose(input) == 0);
    captured.out.kept = captured.out.observed = count;
    /* Exact frozen serialization and write_all; no copied JSON producer. */
    assert(publish_lifecycle(STDOUT_FILENO, &captured, 0) == 0);
    memset(&payload, 0, sizeof payload);
    payload.clean = payload.out.eof = payload.err.eof = 1;
    payload.started = 1; payload.reaped = 2; payload.finished = 40;
    payload.out.eof_ns = payload.err.eof_ns = 3;
    /* Original ND_PAYLOAD schema/argv producer, not payload acceptance. */
    assert(publish(STDOUT_FILENO, &payload, 1) == 0);
    return 0;
}
'''


@unittest.skipUnless(os.environ.get("LIFECYCLE_CROSSBODY_EVIDENCE"),
                     "actual collector compile requires explicit bounded evidence directory")
class ActualBodyCrossBoundaryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out = Path(os.environ["LIFECYCLE_CROSSBODY_EVIDENCE"])
        cls.out.mkdir(mode=0o700, exist_ok=False)
        cls.env = {"PATH": "/usr/bin:/bin", "LANG": "C", "LC_ALL": "C"}
        for name in ("HOME", "TMPDIR"):
            private = Path(os.environ[name])
            private.relative_to(cls.out.parent.resolve(strict=True))
            if private.resolve(strict=True) != private or not private.is_dir():
                raise RuntimeError("private directory is not canonical")
            info = private.stat()
            if info.st_uid != os.getuid() or info.st_mode & 0o077:
                raise RuntimeError("private directory must be caller-owned and private")
            cls.env[name] = str(private)
        cls.sequence = 0
        source = ROOT / "scripts/application-tests/native_diagnostic_lifecycle_collector.c"
        expected = "36fa0d55a30f5e943de0b28c6f54e033cf84ff8cc83cdc54c59688e993c44383"
        if hashlib.sha256(source.read_bytes()).hexdigest() != expected:
            raise RuntimeError("frozen collector changed; stop for dispatcher")
        staged = cls.out / "collector.c"
        staged.write_bytes(source.read_bytes())
        probe = Path(os.environ["LIFECYCLE_ACTUAL_PROBE_STDOUT"])
        if hashlib.sha256(probe.read_bytes()).hexdigest() != "77cbf584af48c02267c6071dde26f780023b44bfbb00a520038ab971bd32bce5":
            raise RuntimeError("retained actual probe bytes changed; stop for dispatcher")
        cls.probe = cls.out / "actual-probe-running.stdout"
        cls.probe.write_bytes(probe.read_bytes())
        harness = cls.out / "harness.c"
        harness.write_text(CROSSBODY_HARNESS.replace("COLLECTOR_SOURCE", str(staged)))
        binary = cls.out / "harness"
        result = cls.capture(["/usr/bin/cc", "-std=c11", "-O2", "-Wall", "-Wextra",
                              "-Werror", str(harness), "-o", str(binary)])
        if result.returncode:
            raise RuntimeError("crossbody compile failed; retained evidence; stop for dispatcher")
        result = cls.capture([str(binary), str(cls.probe)])
        if result.returncode or result.stderr:
            raise RuntimeError("actual serializer failed; retained evidence; stop for dispatcher")
        cls.serial = result.stdout.decode("ascii")
        (cls.out / "actual-crossbody.serial").write_bytes(result.stdout)

    @classmethod
    def capture(cls, argv):
        cls.sequence += 1
        stem = cls.out / f"{cls.sequence:03d}"
        stem.with_suffix(".command.json").write_text(json.dumps({
            "argv": argv, "environment": cls.env,
        }, indent=2) + "\n")
        try:
            result = subprocess.run(argv, env=cls.env, stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE, timeout=20)
        except subprocess.TimeoutExpired as error:
            stem.with_suffix(".stdout").write_bytes(error.stdout or b"")
            stem.with_suffix(".stderr").write_bytes(error.stderr or b"")
            stem.with_suffix(".json").write_text(json.dumps({"timeout_seconds": 20}) + "\n")
            raise
        stem.with_suffix(".stdout").write_bytes(result.stdout)
        stem.with_suffix(".stderr").write_bytes(result.stderr)
        stem.with_suffix(".json").write_text(json.dumps({
            "argv": argv, "returncode": result.returncode,
            "stdout_sha256": hashlib.sha256(result.stdout).hexdigest(),
            "stderr_sha256": hashlib.sha256(result.stderr).hexdigest(),
        }, indent=2) + "\n")
        return result

    def test_actual_probe_bytes_through_actual_collector_serializer(self):
        lines = self.serial.splitlines(keepends=True)
        self.assertEqual([line.partition(" ")[0] for line in lines],
                         ["ND_LIFECYCLE", "ND_LIFECYCLE_STREAM", "ND_LIFECYCLE_STREAM", "ND_PAYLOAD"])
        for line in lines:
            self.assertLessEqual(len(line.encode("ascii")), 4096)
        captured = json.loads(lines[1].partition(" ")[2])["capture"]
        self.assertEqual(bytes.fromhex(captured["hex"]), self.probe.read_bytes())
        payload = json.loads(lines[-1].partition(" ")[2])
        self.assertEqual(set(payload), {"argv", "cwd", "env", "raw_wait_status", "started_ns",
                                       "reaped_ns", "finished_ns", "streams", "procfs_empty"})
        self.assertEqual(payload["argv"], ["/bin/mcexec", "-t", "1", "0", "app", "A", "", "B"])
        result = PARSER.validate_lifecycle_capture(self.serial)
        self.assertEqual(result["status_before"], 5)
        self.assertTrue(result["transition_observed"])
        self.assertFalse(result["resource_restoration_verified"])
        self.assertTrue(result["payload_validation_required"])
        (self.out / "positive-parser-result.json").write_text(json.dumps(result, indent=2) + "\n")

    def test_mutated_actual_serialized_operation_result_duplicate_order(self):
        lines = self.serial.splitlines(keepends=True)
        variants = {}
        for name in ("operation", "result", "booted"):
            record = json.loads(lines[1].partition(" ")[2])
            probe = [json.loads(line) for line in bytes.fromhex(record["capture"]["hex"]).splitlines()]
            if name == "operation":
                probe[2]["operation"] = "invalid_shutdown"
            elif name == "result":
                probe[3]["return"] = probe[3]["linux_result"] = 1
            else:
                probe[1]["return"] = probe[1]["linux_result"] = 3
            data = encode_probe(probe)
            record["capture"]["hex"] = data.hex()
            record["capture"]["observed"] = record["capture"]["retained"] = len(data)
            changed = list(lines)
            changed[1] = "ND_LIFECYCLE_STREAM " + json.dumps(record, separators=(",", ":")) + "\n"
            variants[name] = "".join(changed)
        variants["duplicate"] = "".join(lines[:2] + [lines[1]] + lines[2:])
        variants["order"] = "".join((lines[0], lines[2], lines[1], lines[3]))
        errors = {}
        for name, serial in variants.items():
            with self.subTest(mutation=name):
                self.assertTrue(serial.endswith(lines[-1]), "original ND_PAYLOAD must remain byte-identical")
                (self.out / ("negative-" + name + ".serial")).write_text(serial)
                with self.assertRaises(PARSER.LifecycleCaptureError) as caught:
                    PARSER.validate_lifecycle_capture(serial)
                errors[name] = str(caught.exception)
        (self.out / "negative-parser-results.json").write_text(json.dumps(errors, indent=2) + "\n")


if __name__ == "__main__":
    unittest.main(failfast=True)
