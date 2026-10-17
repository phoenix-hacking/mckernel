"""Offline tests only: no device, PID1, guest or native probe execution."""
import copy
import importlib.util
import json
import os
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "lifecycle_capture", ROOT / "scripts/application-tests/native_diagnostic_lifecycle_capture.py")
PARSER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PARSER)


def probe_records():
    rows = []
    for operation, request, result in (("open", 0, 4), ("status_before", 0x112a03, 3),
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
                                    status_before=3, status_after=0, os_destroyed=False,
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
        for before in (0, 1, 2, 4, 5, 6, 7):
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


if __name__ == "__main__":
    unittest.main(failfast=True)
