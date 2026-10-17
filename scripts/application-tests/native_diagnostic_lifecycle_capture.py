"""Bounded offline lifecycle evidence oracle; never grants payload acceptance.

Call the unchanged native_diagnostic.evaluate separately for payload, kernel,
QMP and owner checks. This module proves only the captured diagnostic transition;
the retained OS and its resources have not been destroyed or restored.
"""
import json
import re

MAX_SERIAL_BYTES = 4 * 1024 * 1024
MAX_RECORD_BYTES = 4096
STREAM_LIMIT = 1024
U64_MAX = (1 << 64) - 1


class LifecycleCaptureError(ValueError):
    pass


def _need(ok, message):
    if not ok:
        raise LifecycleCaptureError(message)


def _keys(value, names):
    _need(type(value) is dict and set(value) == set(names), "unexpected object keys")


def _pairs(pairs):
    obj = {}
    for key, value in pairs:
        _need(key not in obj, "duplicate JSON key")
        obj[key] = value
    return obj


def _json(text):
    try:
        return json.loads(text, object_pairs_hook=_pairs,
                          parse_constant=lambda _: (_ for _ in ()).throw(
                              LifecycleCaptureError("nonfinite JSON number")))
    except (ValueError, RecursionError) as exc:
        raise LifecycleCaptureError("invalid JSON: " + str(exc)) from exc


def _integer(value, low=0, high=U64_MAX):
    _need(type(value) is int and low <= value <= high, "invalid integer")


def _stream(value, metadata):
    _keys(value, ("hex", "eof", "truncated", "observed", "retained",
                  "discarded", "limit", "eof_ns"))
    _need(type(value["hex"]) is str and
          re.fullmatch(r"(?:[0-9a-f]{2})*", value["hex"]) is not None,
          "invalid stream hex")
    _need(len(value["hex"]) <= 2 * STREAM_LIMIT, "oversize stream")
    data = bytes.fromhex(value["hex"])
    _need(value["eof"] is True and value["truncated"] is False, "incomplete stream")
    for field in ("observed", "retained", "discarded", "limit", "eof_ns"):
        _integer(value[field])
    _need(value["limit"] == STREAM_LIMIT and value["discarded"] == 0 and
          value["observed"] == value["retained"] == len(data), "stream accounting")
    _need(metadata["started_ns"] <= value["eof_ns"] <= metadata["finished_ns"],
          "stream EOF timestamp")
    return data


def _probe(stdout):
    try:
        text = stdout.decode("ascii")
    except UnicodeDecodeError as exc:
        raise LifecycleCaptureError("non-ASCII probe output") from exc
    # The frozen probe emits LF, not terminal-normalized CRLF, into its pipe.
    _need("\r" not in text, "unexpected probe carriage return")
    lines = text.split("\n")
    _need(len(lines) == 7 and lines[-1] == "", "missing/extra/truncated probe records")
    operations = (("open", 0, None), ("status_before", 0x112a03, 3),
                  ("shutdown", 0x112a02, 0), ("status_after", 0x112a03, 0),
                  ("close", 0, 0))
    for line, (operation, request, result) in zip(lines[:5], operations):
        record = _json(line)
        _keys(record, ("operation", "request", "return", "errno", "linux_result"))
        _need(record["operation"] == operation, "probe operation order")
        _integer(record["request"])
        _integer(record["return"], -(1 << 31), (1 << 31) - 1)
        _integer(record["errno"], 0, (1 << 31) - 1)
        _integer(record["linux_result"], -(1 << 31), (1 << 31) - 1)
        _need(record["request"] == request and record["errno"] == 0 and
              record["return"] == record["linux_result"], "probe request/result/errno")
        _need(record["return"] >= 0 if result is None else record["return"] == result,
              "probe did not observe Running -> shutdown -> NotBooted")
    result = _json(lines[5])
    _keys(result, ("result", "transition_observed", "resource_restoration_verified"))
    _need(result["result"] == "PASS" and result["transition_observed"] is True and
          result["resource_restoration_verified"] is False, "probe transition summary")


def validate_lifecycle_capture(serial):
    """Return lifecycle-only evidence or raise LifecycleCaptureError.

    Exactly one opaque ND_PAYLOAD must follow metadata/stdout/stderr. Its schema
    and oracle remain the responsibility of native_diagnostic.evaluate. No
    caller-supplied payload success flag can grant lifecycle credit here.
    """
    _need(type(serial) is str, "serial must be text")
    _need(len(serial) <= MAX_SERIAL_BYTES, "oversize serial")
    try:
        _need(len(serial.encode("utf-8")) <= MAX_SERIAL_BYTES, "oversize serial bytes")
    except UnicodeEncodeError as exc:
        raise LifecycleCaptureError("invalid serial encoding") from exc
    records = []
    for line in serial.splitlines(keepends=True):
        if not line.startswith(("ND_LIFECYCLE", "ND_PAYLOAD")):
            continue
        _need(line.endswith("\n"), "unterminated transport record")
        # Like native_diagnostic.evaluate, prefixes must start at column zero;
        # serial console CRLF is accepted, arbitrary console prefixes are not.
        bare = line[:-2] if line.endswith("\r\n") else line[:-1]
        _need(len(bare.encode("utf-8")) + 1 <= MAX_RECORD_BYTES, "oversize record")
        prefix, separator, body = bare.partition(" ")
        _need(separator and prefix in ("ND_LIFECYCLE", "ND_LIFECYCLE_STREAM", "ND_PAYLOAD"),
              "unknown transport record")
        records.append((prefix, body))
        _need(len(records) <= 4, "duplicate transport records")
    _need([p for p, _ in records] == ["ND_LIFECYCLE", "ND_LIFECYCLE_STREAM",
                                          "ND_LIFECYCLE_STREAM", "ND_PAYLOAD"],
          "missing/duplicate/out-of-order transport records")
    metadata = _json(records[0][1])
    _keys(metadata, ("argv", "helper_result", "raw_wait_status", "fault", "timeout",
                     "clean", "child_stage", "child_errno", "started_ns", "reaped_ns", "finished_ns"))
    _need(metadata["argv"] == ["/bin/native-lifecycle-probe", "0"], "probe argv")
    for key in metadata:
        if key != "argv":
            _integer(metadata[key])
    _need(all(metadata[k] == 0 for k in ("helper_result", "raw_wait_status", "fault",
                                        "timeout", "child_stage", "child_errno")) and
          metadata["clean"] == 1, "helper failure or incomplete retirement")
    _need(0 < metadata["started_ns"] <= metadata["reaped_ns"] <= metadata["finished_ns"],
          "helper timestamp ordering")
    streams = {}
    for expected, (_, body) in zip(("stdout", "stderr"), records[1:3]):
        record = _json(body)
        _keys(record, ("name", "capture"))
        _need(record["name"] == expected, "stream order/name")
        streams[expected] = _stream(record["capture"], metadata)
    _need(streams["stderr"] == b"", "unexpected probe stderr")
    _probe(streams["stdout"])
    return {"status": "LIFECYCLE_DIAGNOSTIC_PASS", "transition_observed": True,
            "status_before": 3, "status_after": 0,
            "resource_restoration_verified": False, "os_destroyed": False,
            "payload_validation_required": True}
