#!/usr/bin/env python3
"""Independent offline oracle for storage-fault-v2 retained evidence."""
import hashlib
import itertools
import json
import os
import re
import signal
import stat
import struct
from pathlib import Path

HERE = Path(__file__).resolve().parent
SOURCE_SHA = "09a63a343fa8cc9f511a26693371f5ba4f55ac5ca56fcb47abdc44759830cf1f"
PREFIX = bytes.fromhex("41435251303030")
PREFIX_SHA = "793665677edfa8c879c38d37c8c5300c54ff78e980eae26a96913d7aab9d8d91"
REQUEST_SHA = "e81b38bbe6116bf1df2807fa968e12dccfd28fe8c3ad225c45f282b36cab6716"
SELECTED_SHA = "6b8761a9d2094147f02b9fe2a4c709246905a04c5122d68f6b9951162e01317d"
FIXTURE_SHA = "9ad70dd23d699e72ad805f59446aec371c4e80b955056b845af921b4ce51f725"
U64_MAX = (1 << 64) - 1
U32_MAX = (1 << 32) - 1
I64_MIN, I64_MAX = -(1 << 63), (1 << 63) - 1
LONG_MAX = (1 << 63) - 1
COMPLETE_EXECUTABLE_SEALS = 15
POSTFORK_STDOUT = b"DEVNULL\n"
POSTFORK_STDOUT_SHA = "3e6f38dc6dd02d445e4ff7679b89658b97bafabcf93840c3865e05924fab134f"
WITNESS_FD = 198
EXPECTED_DESIRED = {
    "role": 1, "request_profile": 1, "uid": 0, "gid": 0, "group": 0,
    "umask": 18, "argc": 2, "envc": 0, "stdin_mode": 0,
    "case_id_hex": "696e6672617374727563747572652e636f6c6c6563746f72",
    "source_selector_hex": "2f776f726b2f63617365732f737464696e2d6465766e756c6c2f696e707574732f66697874757265",
    "cwd_hex": "2f776f726b2f63617365732f737464696e2d6465766e756c6c2f637764",
    "stdin_selector_hex": "2f6465762f6e756c6c",
    "attempt_id_hex": "b9e7824e46f727250a6a80c8fcfc9359",
    "selected_inputs_sha256": SELECTED_SHA,
}
EXPECTED = {
    0: (0, "post-fork", "complete", "COMPLETED", "none", 0, 22),
    1: (256, "pre-fork", "complete", "PREPARATION_ERROR", "artifact-create", 28, 10),
    2: (256, "pre-fork", "complete", "COLLECTOR_ERROR", "artifact-write", 28, 17),
    3: (256, "post-fork", "complete", "COLLECTOR_ERROR", "artifact-fsync", 5, 22),
    4: (32000, "post-fork", "absent", None, None, 28, 17),
    5: (32000, "post-fork", "complete-undurable", "COMPLETED", "none", 0, 22),
    6: (32000, "pre-fork", "complete-undurable", "COLLECTOR_ERROR", "artifact-write", 28, 17),
}
COUNTS = [22, 10, 17, 22, 17, 22, 17]
REPORT_KEYS = {
    "schema_version", "kind", "collector_mode", "status", "first_failure",
    "first_failure_errno", "first_failure_monotonic_ns",
    "application_acceptance", "transport_acceptance", "backend_enabled",
    "pathname_execution", "loader_closure_verified", "native_payload",
    "collector_pid", "collector_uid", "collector_euid",
    "collector_interruption_signal", "request_valid", "desired",
    "configured_execution_mechanism", "child_created", "linux_child",
    "setup_ready_record", "setup_error_record", "setup_validated",
    "setup_words", "post_exec_backing_observed",
    "post_exec_observed_monotonic_ns", "post_exec_backing",
    "subsequent_proc_exe_link_sample", "preparation_start_ns",
    "preparation_deadline_ns", "process_start_ns", "process_deadline_ns",
    "completion_observed_ns", "cleanup_start_ns", "cleanup_deadline_ns",
    "cleanup_finished_ns", "cleanup_complete", "group_identity_pinned",
    "owned_records_omitted", "owned_children", "executable", "stdin",
    "devnull_identity", "artifacts", "streams",
}
REPORT_EXACT_INT_FIELDS = {
    "schema_version", "first_failure_errno", "first_failure_monotonic_ns",
    "collector_pid", "collector_uid", "collector_euid",
    "collector_interruption_signal", "owned_records_omitted",
    "post_exec_observed_monotonic_ns", "preparation_start_ns",
    "preparation_deadline_ns", "process_start_ns", "process_deadline_ns",
    "completion_observed_ns", "cleanup_start_ns", "cleanup_deadline_ns",
    "cleanup_finished_ns",
}
REPORT_EXACT_BOOL_FIELDS = {
    "application_acceptance", "transport_acceptance", "backend_enabled",
    "pathname_execution", "loader_closure_verified", "request_valid",
    "child_created", "setup_ready_record", "setup_error_record",
    "setup_validated", "post_exec_backing_observed", "cleanup_complete",
    "group_identity_pinned",
}
COMMON = {"schema_version", "nonce", "selector", "sequence", "kind", "phase",
          "monotonic_ns", "site", "object", "occurrence", "collector_pid",
          "collector_startticks", "source_sha256", "generated_sha256",
          "header_sha256", "elf_sha256"}
CREATE = {"dirfd", "dir_stat", "fd", "target_stat", "acquisition_id",
          "return", "errno_authoritative", "errno"}
WRITE_BEFORE = {"fd", "target_stat", "acquisition_id", "requested_bytes",
                "return", "errno_authoritative", "errno"}
WRITE_AFTER = WRITE_BEFORE | {"actual_bytes"}
IO = {"fd", "target_stat", "acquisition_id", "return",
      "errno_authoritative", "errno"}
BIND = {"acquisition_id", "old_fd", "old_stat", "new_fd", "new_stat"}
OBS = {"REAP": {"pid", "startticks", "raw_wait_status"},
       "SETUP": {"setup_words", "cwd_stat", "stdin_stat", "stdout_pipe_stat", "stderr_pipe_stat",
                 "executable_backing", "executable_seals", "leader_pid", "leader_startticks"},
       "EOF": {"closed_fd"},
       "CLEANUP_READY": {"waitid_return", "waitid_errno", "leader_reaped",
           "stdout_eof", "stderr_eof", "setup_eof"},
       "CLEANUP_FINAL": {"cleanup_start_ns", "cleanup_deadline_ns",
           "cleanup_finished_ns", "cleanup_complete", "group_pinned",
           "owned_count", "owned_records_omitted", "first_failure",
           "first_failure_errno"}}
OWNER_ERROR_KEYS = {"schema_version", "kind", "ordinal", "primary", "stage",
    "type", "message", "monotonic_ns", "packet_sequence", "packet_sha256"}
OWNER_ERROR_STAGES = {"receive", "pre-ack", "journal-packet", "release", "ack",
    "cleanup", "capture-fsync", "artifact-read", "owner-result-write",
    "journal-result", "directory-fsync"}
SUPERVISOR_KEYS = {"schema_version", "kind", "status", "owner_exit_code",
    "owner_signal", "started_ns", "finished_ns", "attempt_root",
    "supervisor_pid",
    "owner_result_present", "owner_result_sha256", "witness_present",
    "witness_sha256", "owner_errors_present", "owner_errors_sha256",
    "owner_stdout_sha256", "owner_stderr_sha256", "owner_identity",
    "owner_identity_observations", "owner_wait_observed",
    "owner_wait_deadline_ns", "cleanup_trigger_ns",
    "supervisor_cleanup_deadline_ns", "supervisor_deadline_ns",
    "supervisor_cleanup", "sigchld_default", "sentinel_wait_passed",
    "preflight_failure", "preflight_started_ns", "sentinel_wait_deadline_ns"}


def wait_fields(raw):
    if type(raw) is not int or raw < 0 or raw > 0xffff:
        raise ValueError("owner wait status")
    if os.WIFEXITED(raw):
        return True, os.WEXITSTATUS(raw), None
    if os.WIFSIGNALED(raw):
        number = os.WTERMSIG(raw)
        if number <= 0 or number >= signal.NSIG:
            raise ValueError("owner wait status")
        return True, None, number
    raise ValueError("owner wait status")

def pair(site, object_name, occurrence=1):
    return [("BEFORE", site, object_name, occurrence),
            ("AFTER", site, object_name, occurrence)]

def schedule_variants(selector):
    e, w1, w2 = pair("events-create", "events.jsonl"), \
        pair("request-write", "request.bin"), pair("request-write", "request.bin", 2)
    eb = [("BIND", "events-create", "events.jsonl", 1)]
    a, r = pair("request-sync", "request.bin"), pair("report-create", "report.json")
    rb = [("BIND", "report-create", "report.json", 1)]
    f, s = pair("report-flush", "report.json"), pair("report-sync", "report.json")
    base = {0:e+eb+w1+["O"]+a+r+rb+f+s, 1:e+r+rb+f+s,
            2:e+eb+w1+w2+a+r+rb+f+s, 3:e+eb+w1+["O"]+a+r+rb+f+s,
            4:e+eb+w1+["O"]+a+r, 5:e+eb+w1+["O"]+a+r+rb+f+s,
            6:e+eb+w1+w2+a+r+rb+f+s}[selector]
    ready = [("READY", "startup", "collector", 0)]
    if "O" not in base:
        return [ready + base]
    index = base.index("O")
    observations = [("REAP", "reap", "leader", 1),
        ("EOF", "pump", "stdout", 1), ("EOF", "pump", "stderr", 2),
        ("EOF", "pump", "setup", 3)]
    final = [("CLEANUP_READY", "cleanup", "owned-tree", 1),
             ("CLEANUP_FINAL", "cleanup", "owned-tree", 1),
             ("SETUP", "setup", "collector", 1)]
    return [ready + base[:index] + list(order) + final + base[index+1:]
            for order in itertools.permutations(observations)]

def phase_for(selector, site, kind):
    if kind == "READY" or site in ("events-create", "request-write"):
        return "pre-fork"
    if kind in OBS:
        return "post-fork"
    return "pre-fork" if selector in (1, 2, 6) else "post-fork"

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def decode_request_lists(raw):
    """Decode only the ACRQ list portion, preserving producer bytes exactly."""
    if len(raw) < 256 or raw[:8] != b"ACRQ0001":
        raise ValueError("request wire")
    total, argc, envc = struct.unpack_from("<III", raw, 16)[0], \
        struct.unpack_from("<I", raw, 52)[0], struct.unpack_from("<I", raw, 56)[0]
    if total != len(raw) or argc > 32 or envc > 32:
        raise ValueError("request wire")
    offset, values = 256, []
    for _ in range(4 + argc + envc):
        if offset + 4 > len(raw):
            raise ValueError("request strings")
        size = struct.unpack_from("<I", raw, offset)[0]; offset += 4
        if size == 0 or offset + size > len(raw):
            raise ValueError("request strings")
        value = raw[offset:offset + size]; offset += size
        if b"\0" in value:
            raise ValueError("request string")
        values.append(value)
    if offset != len(raw):
        raise ValueError("request trailing bytes")
    return (b"".join(value + b"\0" for value in values[4:4 + argc]),
            b"".join(value + b"\0" for value in values[4 + argc:]))

def strict(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("duplicate key")
            result[key] = value
        return result
    return json.loads(raw, object_pairs_hook=pairs,
                      parse_constant=lambda value: (_ for _ in ()).throw(
                          ValueError("nonfinite")))

def exact_equal(left, right):
    if type(left) is not type(right):
        return False
    if type(left) is dict:
        return set(left) == set(right) and all(
            exact_equal(left[key], right[key]) for key in left)
    if type(left) is list:
        return len(left) == len(right) and all(
            exact_equal(a, b) for a, b in zip(left, right))
    return left == right

def read(path, limit=1 << 20):
    path = Path(path)
    if not path.is_absolute() or path.resolve() != path:
        raise ValueError("canonical evidence path")
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or before.st_size > limit:
            raise ValueError("bounded regular evidence")
        chunks, remaining = [], before.st_size
        while remaining:
            chunk = os.read(fd, min(remaining, 65536))
            if not chunk:
                raise OSError("short evidence read")
            chunks.append(chunk)
            remaining -= len(chunk)
        after = os.fstat(fd)
        if (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) != \
           (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns):
            raise OSError("evidence changed during read")
        return b"".join(chunks)
    finally:
        os.close(fd)

def journal(path):
    raw = read(path, 1 << 20)
    if not raw.endswith(b"\n"):
        raise ValueError("journal terminal newline")
    rows = [strict(line) for line in raw.splitlines()]
    if not rows or any(set(row) != {"packet", "receipt_monotonic_ns"}
                       for row in rows):
        raise ValueError("journal envelope")
    if any(type(row["receipt_monotonic_ns"]) is not int or
           row["receipt_monotonic_ns"] <= 0 for row in rows):
        raise ValueError("journal receipt")
    return rows

def validate_owner_errors(raw, result=None):
    if raw == b"":
        rows = []
    else:
        if not raw.endswith(b"\n"):
            raise ValueError("owner error terminal newline")
        rows = [strict(line) for line in raw.splitlines()]
    previous_ns = 0
    for index, row in enumerate(rows):
        if type(row) is not dict or set(row) != OWNER_ERROR_KEYS or \
           type(row["schema_version"]) is not int or row["schema_version"] != 2 or \
           type(row["kind"]) is not str or row["kind"] != "OWNER_ERROR" or \
           type(row["ordinal"]) is not int or row["ordinal"] != index or \
           type(row["primary"]) is not bool or row["primary"] is not (index == 0) or \
           row["stage"] not in OWNER_ERROR_STAGES or \
           type(row["type"]) is not str or not row["type"] or \
           type(row["message"]) is not str or not row["message"] or \
           type(row["monotonic_ns"]) is not int or \
           row["monotonic_ns"] <= previous_ns:
            raise ValueError("owner error record")
        if row["message"].startswith("<empty-") and \
           row["message"] != "<empty-%s>" % row["type"]:
            raise ValueError("owner error message")
        sequence = row["packet_sequence"]
        digest = row["packet_sha256"]
        if sequence is not None and (type(sequence) is not int or sequence < 0):
            raise ValueError("owner error packet sequence")
        if digest is not None and (type(digest) is not str or
                re.fullmatch(r"[0-9a-f]{64}", digest) is None):
            raise ValueError("owner error packet hash")
        previous_ns = row["monotonic_ns"]
    if result is not None:
        cutoff = result.get("result_serialized_ns")
        if type(cutoff) is not int or cutoff <= 0:
            raise ValueError("owner result serialization")
        included = [row for row in rows if row["monotonic_ns"] <= cutoff]
        expected_primary = included[0] if included else None
        if not exact_equal(result.get("owner_failure"), expected_primary) or \
           not exact_equal(result.get("secondary_failures"), included[1:]):
            raise ValueError("owner error partition")
    return rows

def cleanup_phase(value, suffix=False):
    fixed = {"term-identity-1", "term-identity-2",
             "kill-identity-1", "kill-identity-2"}
    if value in fixed:
        return True
    match = re.fullmatch(r"owned-scan-(\d+)(?:-([12]))?", value) \
        if type(value) is str else None
    return match is not None and 0 <= int(match.group(1)) <= 2047 and \
        ((match.group(2) is not None) if suffix else (match.group(2) is None))

def validate_cleanup_unresolved(values):
    if type(values) is not list:
        raise ValueError("owner cleanup unresolved")
    for value in values:
        if type(value) is not dict or type(value.get("kind")) is not str:
            raise ValueError("owner cleanup unresolved")
        kind = value["kind"]
        if kind == "identity":
            if set(value) != {"kind", "phase", "observation", "pid", "ppid",
                    "startticks", "matched", "monotonic_ns"} or \
               not cleanup_phase(value["phase"], suffix=True) or \
               value["observation"] not in ("observed", "missing", "error") or \
               type(value["pid"]) is not int or value["pid"] <= 0 or \
               type(value["matched"]) is not bool or \
               type(value["monotonic_ns"]) is not int or value["monotonic_ns"] <= 0:
                raise ValueError("owner cleanup identity")
            if value["observation"] == "observed":
                if type(value["ppid"]) is not int or value["ppid"] <= 0 or \
                   type(value["startticks"]) is not int or value["startticks"] <= 0:
                    raise ValueError("owner cleanup identity")
            elif value["ppid"] is not None or value["startticks"] is not None or \
                    value["matched"] is not False:
                raise ValueError("owner cleanup identity")
        elif kind == "deadline":
            if set(value) != {"kind", "stage", "monotonic_ns", "deadline_ns"} or \
               value["stage"] not in ("direct-wait", "term-pre-signal",
                    "kill-pre-signal", "owned-scan") or any(
                    type(value[key]) is not int or value[key] <= 0
                    for key in ("monotonic_ns", "deadline_ns")) or \
               value["monotonic_ns"] < value["deadline_ns"]:
                raise ValueError("owner cleanup deadline")
        elif kind == "signal-error":
            if set(value) != {"kind", "stage", "pid", "startticks", "signal",
                    "errno", "monotonic_ns"} or value["stage"] not in ("term", "kill") or \
               type(value["signal"]) is not int or \
               value["signal"] != (15 if value["stage"] == "term" else 9) or any(
                    type(value[key]) is not int or value[key] <= 0 for key in
                    ("pid", "startticks", "errno", "monotonic_ns")):
                raise ValueError("owner cleanup signal error")
        elif kind == "wait-timeout":
            if set(value) != {"kind", "stage", "pid", "startticks",
                    "monotonic_ns", "deadline_ns"} or \
               value["stage"] not in ("direct", "term", "kill") or \
               type(value["pid"]) is not int or value["pid"] <= 0 or \
               (value["startticks"] is not None and (type(value["startticks"]) is not int or
                    value["startticks"] <= 0)) or any(type(value[key]) is not int or
                    value[key] <= 0 for key in ("monotonic_ns", "deadline_ns")) or \
               value["monotonic_ns"] < value["deadline_ns"]:
                raise ValueError("owner cleanup wait timeout")
        elif kind == "owned":
            if set(value) != {"kind", "phase", "pid", "ppid", "startticks",
                    "monotonic_ns"} or not cleanup_phase(value["phase"]) or any(
                    type(value[key]) is not int or value[key] <= 0 for key in
                    ("pid", "ppid", "startticks", "monotonic_ns")):
                raise ValueError("owner cleanup owned")
        else:
            raise ValueError("owner cleanup unresolved kind")
    return values

def validate_events(raw, selector, collector):
    if not raw.endswith(b"\n"):
        raise ValueError("events terminal newline")
    events = [strict(line) for line in raw.splitlines()]
    schemas = {
        "collector-start": {"monotonic_ns", "event", "pid"},
        "request-rejected": {"monotonic_ns", "event", "decoder_error"},
        "child-created": {"monotonic_ns", "event", "pid", "startticks"},
        "observed-sealed-exe": {"monotonic_ns", "event", "pid"},
        "leader-waitable": {"monotonic_ns", "event", "pid"},
        "owned-kill-attempt": {"monotonic_ns", "event", "pid", "startticks"},
        "adopted-child": {"monotonic_ns", "event", "pid", "startticks"},
        "actual-reap": {"monotonic_ns", "event", "pid", "raw_wait_status"},
        "owned-group-kill-attempt": {"monotonic_ns", "event", "pgid",
                                     "leader_startticks"},
        "direct-unreaped-child-kill-without-proc-identity": {
            "monotonic_ns", "event", "pid"},
        "collector-finish": {"monotonic_ns", "event", "first_failure"},
    }
    if not events or events[0] != {"monotonic_ns": events[0].get("monotonic_ns"),
            "event": "collector-start", "pid": collector["pid"]} or \
       events[-1].get("event") != "collector-finish":
        raise ValueError("events endpoints")
    stamps = []
    for event in events:
        name = event.get("event")
        if name not in schemas or set(event) != schemas[name] or \
           type(event["monotonic_ns"]) is not int or event["monotonic_ns"] <= 0:
            raise ValueError("events schema")
        stamps.append(event["monotonic_ns"])
    if stamps != sorted(stamps) or len(set(stamps)) != len(stamps):
        raise ValueError("events order")
    expected_failure = "artifact-write" if selector in (2, 6) else "none"
    if events[-1]["first_failure"] != expected_failure:
        raise ValueError("events failure snapshot")
    # collector.c has one closed lifecycle per selector.  Do not accept a
    # plausible-looking event merely because its schema is valid.
    expected_events = (["collector-start", "child-created",
        "observed-sealed-exe", "leader-waitable", "owned-group-kill-attempt",
        "actual-reap", "collector-finish"] if selector in (0, 3, 4, 5)
        else ["collector-start", "collector-finish"])
    if [event["event"] for event in events] != expected_events:
        raise ValueError("events lifecycle kinds")
    # Event fields are a typed wire contract, not merely JSON-shaped values.
    for event in events:
        name = event["event"]
        if name in ("collector-start", "child-created", "observed-sealed-exe",
                    "leader-waitable", "owned-kill-attempt", "adopted-child",
                    "direct-unreaped-child-kill-without-proc-identity") and \
                (type(event["pid"]) is not int or event["pid"] <= 0):
            raise ValueError("events scalar")
        if name in ("child-created", "owned-kill-attempt", "adopted-child") and \
                (type(event["startticks"]) is not int or event["startticks"] <= 0):
            raise ValueError("events scalar")
        if name == "owned-group-kill-attempt" and any(
                type(event[key]) is not int or event[key] <= 0
                for key in ("pgid", "leader_startticks")):
            raise ValueError("events scalar")
        if name == "request-rejected" and (type(event["decoder_error"]) is not str or
                                            not event["decoder_error"]):
            raise ValueError("events scalar")
        if name == "collector-finish" and (type(event["first_failure"]) is not str or
                                            event["first_failure"] not in
                                            ("none", "artifact-write")):
            raise ValueError("events scalar")
        if name == "actual-reap":
            if type(event["raw_wait_status"]) is not int:
                raise ValueError("events scalar")
            wait_fields(event["raw_wait_status"])
    children = [event for event in events if event["event"] == "child-created"]
    if selector in (0, 3, 4, 5):
        if len(children) != 1:
            raise ValueError("events child lifecycle")
        if any(event["event"] in ("observed-sealed-exe", "leader-waitable",
                                   "actual-reap") and event["monotonic_ns"] <=
               children[0]["monotonic_ns"] for event in events):
            raise ValueError("events child lifecycle")
        child = children[0]
        sealed = next(event for event in events if event["event"] ==
                      "observed-sealed-exe")
        leader = next(event for event in events if event["event"] ==
                      "leader-waitable")
        reap = next(event for event in events if event["event"] == "actual-reap")
        group = next(event for event in events if event["event"] ==
                     "owned-group-kill-attempt")
        if any(event["pid"] != child["pid"] for event in (sealed, leader, reap)) or \
           (reap["pid"] != child["pid"]) or \
           group["pgid"] != child["pid"] or \
           group["leader_startticks"] != child["startticks"]:
            raise ValueError("events child identity")
    return events

def validate_stat(value):
    if type(value) is not dict or set(value) != {"dev", "ino", "mode", "size"} or \
       any(type(value[key]) is not int for key in value):
        raise ValueError("witness stat")
    if any(not 0 <= value[key] <= U64_MAX for key in ("dev", "ino", "mode")) or \
       not I64_MIN <= value["size"] <= I64_MAX:
        raise ValueError("witness stat range")

def validate_report_stat(value):
    keys = {"device", "inode", "mode", "uid", "gid", "size", "nlink",
            "mtime_seconds", "mtime_nanoseconds", "ctime_seconds",
            "ctime_nanoseconds"}
    if type(value) is not dict or set(value) != keys or any(
            type(value[key]) is not int for key in keys):
        raise ValueError("report stat")
    bounds = {
        "device": (0, U64_MAX), "inode": (0, U64_MAX),
        "nlink": (0, U64_MAX), "mode": (0, (1 << 32) - 1),
        "uid": (0, (1 << 32) - 1), "gid": (0, (1 << 32) - 1),
        "size": (I64_MIN, I64_MAX),
        "mtime_seconds": (I64_MIN, I64_MAX),
        "ctime_seconds": (I64_MIN, I64_MAX),
        "mtime_nanoseconds": (0, 999999999),
        "ctime_nanoseconds": (0, 999999999)}
    if any(not low <= value[key] <= high
           for key, (low, high) in bounds.items()):
        raise ValueError("report stat range")

def validate_sink(value):
    if value is None:
        return
    keys = {"attempted_name", "created", "fd_available", "creation_errno",
            "fd_errno", "path", "limit_bytes", "seen_bytes", "stored_bytes",
            "truncated", "io_error", "sha256"}
    if type(value) is not dict or set(value) != keys or \
       type(value["attempted_name"]) is not str or \
       any(type(value[key]) is not bool for key in (
           "created", "fd_available", "truncated", "io_error")) or \
       any(type(value[key]) is not int or not 0 <= value[key] <= (1 << 64) - 1
           for key in ("limit_bytes", "seen_bytes", "stored_bytes")) or \
       any(type(value[key]) is not int or value[key] < 0 for key in (
           "creation_errno", "fd_errno", "limit_bytes", "seen_bytes",
           "stored_bytes")) or value["stored_bytes"] > value["seen_bytes"] or \
       value["stored_bytes"] > value["limit_bytes"]:
        raise ValueError("report sink")
    if value["created"] is not (value["path"] == value["attempted_name"]) or \
       (value["path"] is not None and type(value["path"]) is not str):
        raise ValueError("report sink path")
    # new_sink() records creation_errno only on an unsuccessful open; a
    # successfully-created sink has no creation or descriptor failure to
    # report, and its descriptor remains available for retain/json_sink.
    if value["created"] and (not value["fd_available"] or
                              value["creation_errno"] != 0 or
                              value["fd_errno"] != 0):
        raise ValueError("report sink creation")
    if not value["created"] and value["fd_available"]:
        raise ValueError("report sink creation")
    if value["fd_available"]:
        if type(value["sha256"]) is not str or len(value["sha256"]) != 64:
            raise ValueError("report sink hash")
    elif value["sha256"] is not None:
        raise ValueError("report sink hash")

def validate_report_source(value):
    keys = {"opened", "stable", "verified", "source_before", "source_after",
            "sealed_backing", "requested_memfd_flags", "seals", "artifact"}
    if type(value) is not dict or set(value) != keys or any(
            type(value[key]) is not bool for key in ("opened", "stable", "verified")) or \
       type(value["requested_memfd_flags"]) is not int or type(value["seals"]) is not int:
        raise ValueError("report source")
    for key in ("source_before", "source_after", "sealed_backing"):
        if value[key] is not None:
            validate_report_stat(value[key])
    validate_sink(value["artifact"])
    if value["requested_memfd_flags"] != 3:
        raise ValueError("report source flags")
    if value["opened"]:
        if any(value[key] is None for key in ("source_before", "source_after")):
            raise ValueError("report opened source")
    else:
        # json_source() emits an entirely empty source until seal_source (or
        # the unsealed DEVNULL path) has opened a source.
        if any(value[key] is not None for key in
               ("source_before", "source_after", "sealed_backing", "artifact")) or \
           value["stable"] or value["verified"] or \
           value["seals"] != 0:
            raise ValueError("report absent source")

def validate_report_scalars(report):
    """Reject JSON number coercions before applying lifecycle semantics."""
    if any(type(report[key]) is not int or report[key] < 0
           for key in REPORT_EXACT_INT_FIELDS):
        raise ValueError("report scalar types")
    if any(type(report[key]) is not bool for key in REPORT_EXACT_BOOL_FIELDS):
        raise ValueError("report scalar types")
    streams = report["streams"]
    if type(streams) is not dict or set(streams) != {
            "stdout_eof", "stderr_eof", "setup_eof"} or any(
            type(streams[key]) is not bool for key in streams):
        raise ValueError("report stream types")

def validate_report_proc_exe_sample(value):
    """Validate the exact optional sample emitted by collector.c."""
    if value is None:
        return
    keys = {"atomic_with_backing_stat", "observed_monotonic_ns", "bytes_hex"}
    if type(value) is not dict or set(value) != keys or \
       value["atomic_with_backing_stat"] is not False or \
       type(value["observed_monotonic_ns"]) is not int or \
       value["observed_monotonic_ns"] <= 0 or \
       type(value["bytes_hex"]) is not str or \
       re.fullmatch(r"(?:[0-9a-f]{2})*", value["bytes_hex"]) is None or \
       len(value["bytes_hex"]) // 2 > 254 or b"\x00" in bytes.fromhex(value["bytes_hex"]):
        raise ValueError("report proc exe sample")

def validate_report_process(value):
    keys = {"pid", "identity_observed", "ppid", "pgid_at_observation",
            "sid_at_observation", "startticks", "kill_sent", "reaped",
            "raw_wait_status", "wait"}
    if type(value) is not dict or set(value) != keys or any(
            type(value[key]) is not int for key in (
                "pid", "ppid", "pgid_at_observation", "sid_at_observation",
                "startticks")) or any(value[key] <= 0 for key in (
                "pid", "ppid", "pgid_at_observation", "sid_at_observation",
                "startticks")) or any(type(value[key]) is not bool for key in (
                "identity_observed", "kill_sent", "reaped")) or \
            value["identity_observed"] is not True:
        raise ValueError("report process")
    if value["reaped"]:
        wait = value["wait"]
        if type(value["raw_wait_status"]) is not int or type(wait) is not dict or \
           set(wait) != {"exited", "signaled", "exit_code", "signal", "core_dumped"} or \
           any(type(wait[key]) is not bool for key in (
               "exited", "signaled", "core_dumped")) or \
           (wait["exited"] and (type(wait["exit_code"]) is not int or
                                 wait["exit_code"] < 0 or
                                 wait["signaled"] or wait["signal"] is not None)) or \
           (wait["signaled"] and (wait["exit_code"] is not None or
                                   type(wait["signal"]) is not int or
                                   wait["signal"] <= 0 or wait["exited"])) or \
           (not wait["exited"] and not wait["signaled"] and
            (wait["exit_code"] is not None or wait["signal"] is not None)):
            raise ValueError("report wait")
        try:
            _waited, exit_code, signal_number = wait_fields(
                value["raw_wait_status"])
        except ValueError:
            raise ValueError("report wait")
        expected = {"exited": exit_code is not None,
                    "signaled": signal_number is not None,
                    "exit_code": exit_code, "signal": signal_number,
                    "core_dumped": bool(os.WCOREDUMP(value["raw_wait_status"]))
                        if signal_number is not None else False}
        if wait != expected:
            raise ValueError("report wait")
    elif value["raw_wait_status"] is not None or value["wait"] is not None:
        raise ValueError("report wait")

def validate_packet_schema(packet):
    kind, site = packet["kind"], packet["site"]
    if kind == "READY": extras = set()
    elif kind in ("BEFORE", "AFTER") and site in ("events-create", "report-create"):
        extras = CREATE
    elif kind == "BEFORE" and site == "request-write": extras = WRITE_BEFORE
    elif kind == "AFTER" and site == "request-write": extras = WRITE_AFTER
    elif kind in ("BEFORE", "AFTER") and site in (
            "request-sync", "report-flush", "report-sync"): extras = IO
    elif kind == "BIND": extras = BIND
    elif kind in OBS: extras = OBS[kind]
    else: raise ValueError("witness kind")
    if set(packet) != COMMON | extras:
        raise ValueError("witness exact fields")
    for name in ("target_stat", "dir_stat", "old_stat", "new_stat"):
        if name in packet and packet[name] is not None: validate_stat(packet[name])
    if kind == "BEFORE" and (packet["return"] is not None or
            packet["errno_authoritative"] is not False or packet["errno"] is not None):
        raise ValueError("before result")
    if kind == "AFTER":
        result = packet["return"]
        if type(result) is not int or packet["errno_authoritative"] is not (result < 0) or \
           (result < 0 and (type(packet["errno"]) is not int or packet["errno"] <= 0)) or \
           (result >= 0 and packet["errno"] is not None):
            raise ValueError("after result")

def validate_packet_order(packets, selector, nonce, hashes, expected_count):
    if len(packets) != expected_count or expected_count != COUNTS[selector]:
        raise ValueError("witness packet count")
    signatures = []
    for sequence, packet in enumerate(packets):
        kind, site = packet["kind"], packet["site"]
        validate_packet_schema(packet)
        for descriptor in ("dirfd", "fd", "old_fd", "new_fd", "closed_fd"):
            if descriptor in packet and packet[descriptor] is not None and \
                    (type(packet[descriptor]) is not int or
                     packet[descriptor] < 0):
                raise ValueError("witness descriptor")
            if descriptor in packet and packet[descriptor] == WITNESS_FD:
                raise ValueError("witness transport descriptor")
        if (type(packet.get("dirfd")) is int and 0 <= packet["dirfd"] < 3) or \
           (kind == "BIND" and type(packet["new_fd"]) is int and
            0 <= packet["new_fd"] < 3) or \
           (kind == "EOF" and type(packet["closed_fd"]) is int and
            0 <= packet["closed_fd"] < 3) or \
           (site in ("request-write", "request-sync", "report-flush", "report-sync") and
            type(packet.get("fd")) is int and 0 <= packet["fd"] < 3):
            raise ValueError("witness high descriptor")
        if "acquisition_id" in packet and type(packet["acquisition_id"]) is bool:
            raise ValueError("request acquisition")
        if type(packet["schema_version"]) is not int or type(packet["nonce"]) is not str or \
           type(packet["selector"]) is not int or type(packet["sequence"]) is not int or \
           type(packet["kind"]) is not str or packet["schema_version"] != 2 or \
           packet["nonce"] != nonce or \
           packet["selector"] != selector or packet["sequence"] != sequence:
            raise ValueError("witness identity")
        if type(packet["monotonic_ns"]) is not int or packet["monotonic_ns"] <= 0 or \
           type(packet["collector_pid"]) is not int or packet["collector_pid"] <= 0 or \
           type(packet["collector_startticks"]) is not int or packet["collector_startticks"] <= 0:
            raise ValueError("witness monotonic")
        if type(packet["occurrence"]) is not int or \
           (packet["kind"] != "READY" and packet["occurrence"] <= 0):
            raise ValueError("witness occurrence")
        if packet["source_sha256"] != SOURCE_SHA:
            raise ValueError("source hash")
        for key in ("generated_sha256", "header_sha256", "elf_sha256"):
            if packet[key] != hashes[key]:
                raise ValueError("generated hash")
        if packet["phase"] != phase_for(selector, packet["site"], packet["kind"]):
            raise ValueError("witness phase")
        if packet["kind"] == "REAP" and (type(packet["pid"]) is not int or
                type(packet["startticks"]) is not int or
                type(packet["raw_wait_status"]) is not int or
                packet["pid"] <= 0 or packet["startticks"] <= 0):
            raise ValueError("witness reap types")
        if packet["kind"] == "SETUP":
            if type(packet["setup_words"]) is not list or len(packet["setup_words"]) != 48 or \
               any(type(word) is not int or not 0 <= word <= (1 << 64) - 1
                   for word in packet["setup_words"]) or \
               type(packet["executable_seals"]) is not int or not 0 <= packet["executable_seals"] <= U32_MAX or \
               type(packet["leader_pid"]) is not int or not 0 < packet["leader_pid"] <= LONG_MAX or \
               type(packet["leader_startticks"]) is not int or not 0 < packet["leader_startticks"] <= U64_MAX:
                raise ValueError("witness setup types")
            for key in ("cwd_stat", "stdin_stat", "stdout_pipe_stat", "stderr_pipe_stat", "executable_backing"):
                validate_stat(packet[key])
        if packet["kind"] == "EOF" and (type(packet["closed_fd"]) is not int or
                packet["closed_fd"] < 0):
            raise ValueError("witness eof types")
        if packet["kind"] == "CLEANUP_READY" and (
                any(type(packet[key]) is not bool for key in
                    ("leader_reaped", "stdout_eof", "stderr_eof", "setup_eof")) or
                type(packet["waitid_return"]) is not int or
                type(packet["waitid_errno"]) is not int):
            raise ValueError("witness cleanup ready types")
        if packet["kind"] == "CLEANUP_FINAL" and (
                any(type(packet[key]) is not bool for key in
                    ("cleanup_complete", "group_pinned")) or
                any(type(packet[key]) is not int for key in
                    ("cleanup_start_ns", "cleanup_deadline_ns",
                     "cleanup_finished_ns", "owned_count",
                     "owned_records_omitted", "first_failure_errno"))):
            raise ValueError("witness cleanup final types")
        signatures.append((packet["kind"], packet["site"], packet["object"],
                           packet["occurrence"]))
    if signatures not in schedule_variants(selector):
        raise ValueError("witness schedule")
    if selector in (0, 3, 4, 5):
        reaps = [p for p in packets if p["kind"] == "REAP"]
        eofs = [p for p in packets if p["kind"] == "EOF"]
        finals = [p for p in packets if p["kind"] == "CLEANUP_FINAL"]
        if len(reaps) != 1 or wait_fields(reaps[0]["raw_wait_status"])[1:] != \
                (0, None) or \
           len(eofs) != 3 or len({p["closed_fd"] for p in eofs}) != 3 or \
           len(finals) != 1 or finals[0]["cleanup_deadline_ns"] != \
                finals[0]["cleanup_start_ns"] + 15_000_000_000:
            raise ValueError("postfork cleanup observations")

    request_identity, request_size, report_identity, report_id = None, 0, None, None
    creates, positive_ids, attempt_dir = {}, set(), None
    # Descriptor numbers remain occupied until the corresponding BIND closes
    # (relocates) them.  This is deliberately independent of acquisition IDs:
    # a forged record must not hide a numeric descriptor collision.
    live_fds = {}
    for packet in packets[1:]:
        kind, site = packet["kind"], packet["site"]
        if attempt_dir is not None:
            for stat_name in ("target_stat", "old_stat", "new_stat"):
                value = packet.get(stat_name)
                if value is not None and stat.S_ISREG(value["mode"]) and \
                        (value["dev"], value["ino"]) == attempt_dir[1:3]:
                    raise ValueError("directory inode collision")
        if kind == "EOF":
            # EOF closes a stream capability. Reject aliases of the persistent
            # attempt directory or any file capability still live now.
            if packet["closed_fd"] == (attempt_dir[0] if attempt_dir is not None else None) or \
                    packet["closed_fd"] in live_fds:
                raise ValueError("eof descriptor collision")
        elif kind == "BEFORE" and site in ("events-create", "report-create"):
            if packet["fd"] is not None or packet["target_stat"] is not None or \
               packet["acquisition_id"] is not None or type(packet["dirfd"]) is not int:
                raise ValueError("create before")
            validate_stat(packet["dir_stat"])
            if not stat.S_ISDIR(packet["dir_stat"]["mode"]):
                raise ValueError("witness directory type")
            identity = (packet["dirfd"], packet["dir_stat"]["dev"],
                        packet["dir_stat"]["ino"], packet["dir_stat"]["mode"])
            if attempt_dir is None:
                attempt_dir = identity
            elif identity != attempt_dir:
                raise ValueError("witness directory identity")
        elif kind == "AFTER" and site in ("events-create", "report-create"):
            if attempt_dir is None or \
               (packet["dirfd"], packet["dir_stat"]["dev"], packet["dir_stat"]["ino"],
                packet["dir_stat"]["mode"]) != attempt_dir:
                raise ValueError("witness directory identity")
            failed = (site == "events-create" and selector == 1) or \
                     (site == "report-create" and selector == 4)
            if failed:
                if (packet["return"], packet["errno"], packet["fd"],
                    packet["target_stat"], packet["acquisition_id"]) != \
                   (-1, 28, None, None, None): raise ValueError("create failure")
            else:
                if packet["return"] < 0 or packet["fd"] != packet["return"] or \
                   type(packet["acquisition_id"]) is not int or packet["acquisition_id"] <= 0:
                    raise ValueError("create success")
                validate_stat(packet["target_stat"])
                if not stat.S_ISREG(packet["target_stat"]["mode"]):
                    raise ValueError("witness target type")
                if packet["target_stat"]["size"] != 0 or \
                   packet["target_stat"]["mode"] & 0o170777 != 0o100600 or \
                   packet["acquisition_id"] in positive_ids:
                    raise ValueError("create acquisition")
                if packet["fd"] == attempt_dir[0] or packet["fd"] in live_fds:
                    raise ValueError("create descriptor collision")
                positive_ids.add(packet["acquisition_id"])
                creates[site] = packet
                live_fds[packet["fd"]] = (site, packet["acquisition_id"])
        elif kind == "BIND":
            create = creates.get(site)
            if (packet["old_fd"] >= 3 and packet["new_fd"] != packet["old_fd"]) or \
               (packet["old_fd"] < 3 and packet["new_fd"] < 3):
                raise ValueError("bind descriptor")
            if type(packet["acquisition_id"]) is not int or not create or packet["acquisition_id"] != create["acquisition_id"] or \
               packet["old_fd"] != create["fd"] or \
               live_fds.get(packet["old_fd"]) != (site, packet["acquisition_id"]) or \
               (packet["new_fd"] in live_fds and packet["new_fd"] != packet["old_fd"]):
                raise ValueError("bind acquisition")
            if not stat.S_ISREG(packet["old_stat"]["mode"]) or \
               not stat.S_ISREG(packet["new_stat"]["mode"]):
                raise ValueError("witness target type")
            for key in ("dev", "ino", "mode", "size"):
                if packet["old_stat"][key] != packet["new_stat"][key] or \
                   packet["old_stat"][key] != create["target_stat"][key]:
                    raise ValueError("bind identity")
            if site == "report-create":
                report_identity = (packet["new_fd"], packet["new_stat"]["dev"],
                    packet["new_stat"]["ino"], packet["new_stat"]["mode"])
                report_id = packet["acquisition_id"]
            if packet["new_fd"] == attempt_dir[0]:
                raise ValueError("directory descriptor collision")
            if packet["new_fd"] != packet["old_fd"]:
                del live_fds[packet["old_fd"]]
                live_fds[packet["new_fd"]] = (site, packet["acquisition_id"])
        elif site == "request-write":
            if type(packet["acquisition_id"]) is not int:
                raise ValueError("request acquisition")
            if type(packet["requested_bytes"]) is not int or \
               packet["requested_bytes"] <= 0 or \
               (kind == "AFTER" and
                (type(packet["actual_bytes"]) is not int or
                 packet["actual_bytes"] < 0)):
                raise ValueError("witness write types")
            stat_value = packet["target_stat"]
            if not stat.S_ISREG(stat_value["mode"]):
                raise ValueError("witness target type")
            identity = (packet["fd"], stat_value["dev"], stat_value["ino"], stat_value["mode"])
            if attempt_dir is not None and packet["fd"] == attempt_dir[0]:
                raise ValueError("directory descriptor collision")
            if packet["acquisition_id"] != 0 or (request_identity and identity != request_identity):
                raise ValueError("request acquisition")
            request_identity = identity
            prior = live_fds.get(packet["fd"])
            if prior is not None and prior != ("request-write", 0):
                raise ValueError("request descriptor collision")
            live_fds.setdefault(packet["fd"], ("request-write", 0))
            occurrence = packet["occurrence"]
            injected = selector in (2, 6)
            requested = 406 if occurrence == 1 else 399
            before_size = 0 if occurrence == 1 else 7
            if packet["requested_bytes"] != requested:
                raise ValueError("request bytes")
            if kind == "BEFORE" and stat_value["size"] != before_size:
                raise ValueError("request before size")
            if kind == "AFTER":
                result = 7 if injected and occurrence == 1 else -1 if occurrence == 2 else 406
                error = 28 if result < 0 else None
                if packet["return"] != result or packet["errno"] != error or \
                   packet["actual_bytes"] != max(result, 0) or \
                   stat_value["size"] != (7 if injected else 406):
                    raise ValueError("request write result")
                request_size = stat_value["size"]
        elif site == "request-sync":
            if type(packet["acquisition_id"]) is not int:
                raise ValueError("request sync result")
            if not stat.S_ISREG(packet["target_stat"]["mode"]):
                raise ValueError("witness target type")
            stat_value = packet["target_stat"]
            identity = (packet["fd"], stat_value["dev"], stat_value["ino"],
                        stat_value["mode"])
            if request_identity is None or identity != request_identity:
                raise ValueError("request sync identity")
            if live_fds.get(packet["fd"]) != ("request-write", 0):
                raise ValueError("request descriptor")
            expected_result = -1 if selector in (3, 6) else 0
            if packet["acquisition_id"] != 0 or packet["target_stat"]["size"] != request_size or \
               (kind == "AFTER" and (packet["return"] != expected_result or
                packet["errno"] != (5 if expected_result < 0 else None))):
                raise ValueError("request sync result")
        elif kind == "AFTER" and site == "report-flush" and packet["return"] != 0:
            raise ValueError("report flush result")
        elif kind == "AFTER" and site == "report-sync":
            expected_result = -1 if selector in (5, 6) else 0
            if packet["return"] != expected_result or \
               packet["errno"] != (5 if expected_result < 0 else None):
                raise ValueError("report sync result")
        if site in ("report-flush", "report-sync"):
            if type(packet["acquisition_id"]) is not int:
                raise ValueError("report acquisition")
            stat_value = packet["target_stat"]
            if not stat.S_ISREG(stat_value["mode"]):
                raise ValueError("witness target type")
            identity = (packet["fd"], stat_value["dev"], stat_value["ino"], stat_value["mode"])
            if identity != report_identity or packet["acquisition_id"] != report_id:
                raise ValueError("report acquisition")
            if live_fds.get(packet["fd"]) != ("report-create", report_id):
                raise ValueError("report descriptor")
    cleanup = [packet for packet in packets if packet["kind"] == "CLEANUP_FINAL"]
    if cleanup and (cleanup[0]["cleanup_complete"] is not True or
            not cleanup[0]["cleanup_start_ns"] < cleanup[0]["cleanup_finished_ns"] <
                cleanup[0]["cleanup_deadline_ns"] or cleanup[0]["group_pinned"] is not True or
            cleanup[0]["owned_count"] != 0 or cleanup[0]["owned_records_omitted"] != 0 or
            cleanup[0]["first_failure"] != "none" or cleanup[0]["first_failure_errno"] != 0):
        raise ValueError("collector cleanup result")
    ready = [packet for packet in packets if packet["kind"] == "CLEANUP_READY"]
    if ready and (ready[0]["waitid_return"], ready[0]["waitid_errno"],
            ready[0]["leader_reaped"], ready[0]["stdout_eof"],
            ready[0]["stderr_eof"], ready[0]["setup_eof"]) != \
            (-1, 10, True, True, True, True):
        raise ValueError("collector cleanup ready")

def validate_record(record, path, limit=1 << 20, shown_path=None):
    shown_path = path if shown_path is None else shown_path
    if type(record) is not dict or set(record) != {"path", "present", "size", "sha256"} or \
       record["path"] != str(shown_path) or type(record["present"]) is not bool:
        raise ValueError("evidence record")
    if not record["present"]:
        if record["size"] is not None or record["sha256"] is not None or \
           not is_absent_nofollow(path):
            raise ValueError("evidence absence")
        return None
    raw = read(Path(path), limit)
    if type(record["size"]) is not int or record["size"] != len(raw) or \
       record["sha256"] != sha(raw):
        raise ValueError("evidence hash")
    return raw

def is_absent_nofollow(path):
    try:
        os.lstat(path)
    except FileNotFoundError:
        return True
    return False

def validate_supervisor_observation(value):
    keys = {"observation", "pid", "ppid", "startticks", "monotonic_ns"}
    if type(value) is not dict or set(value) != keys or \
       value["observation"] not in ("observed", "missing", "error") or \
       type(value["pid"]) is not int or value["pid"] <= 0 or \
       type(value["monotonic_ns"]) is not int or value["monotonic_ns"] <= 0:
        raise ValueError("supervisor identity observation")
    if value["observation"] == "observed":
        if type(value["ppid"]) is not int or value["ppid"] <= 0 or \
           type(value["startticks"]) is not int or value["startticks"] <= 0:
            raise ValueError("supervisor identity observation")
    elif value["ppid"] is not None or value["startticks"] is not None:
        raise ValueError("supervisor identity observation")


def classify_supervisor_observations(pid, supervisor_pid, observations):
    """Independently recompute packet 11's spawned-owner classification."""
    observed = [item for item in observations
                if item["observation"] == "observed"]
    if len(observations) == 2 and len(observed) == 2 and \
       observed[0]["pid"] == observed[1]["pid"] == pid and \
       observed[0]["ppid"] == observed[1]["ppid"] == supervisor_pid and \
       observed[0]["startticks"] == observed[1]["startticks"]:
        return "MATCHED", observed[0]["startticks"]
    conflict = any(item["pid"] != pid or item["ppid"] != supervisor_pid
                   for item in observed)
    if len(observed) >= 2 and any(
            (item["pid"], item["ppid"], item["startticks"]) !=
            (observed[0]["pid"], observed[0]["ppid"],
             observed[0]["startticks"]) for item in observed[1:]):
        conflict = True
    return ("MISMATCH" if conflict else "UNOBSERVED"), None

def validate_supervisor_cleanup(cleanup, owner_identity, supervisor_pid,
                                original_wait_deadline_ns, trigger_ns,
                                deadline_ns, overall_deadline_ns, finished_ns,
                                preflight_stage=None, preflight_failure=None,
                                preflight_started_ns=None):
    if type(cleanup) is not dict or set(cleanup) != {"complete", "events", "unresolved"} or \
       type(cleanup["complete"]) is not bool or type(cleanup["events"]) is not list or \
       type(supervisor_pid) is not int or supervisor_pid <= 0 or \
       type(overall_deadline_ns) is not int or finished_ns > overall_deadline_ns:
        raise ValueError("supervisor cleanup")
    unresolved = cleanup["unresolved"]
    if type(unresolved) is not list:
        raise ValueError("supervisor cleanup unresolved")
    for value in unresolved:
        if type(value) is not dict:
            raise ValueError("supervisor cleanup unresolved")
        if value.get("kind") == "signal-error":
            if set(value) != {"kind", "stage", "pid", "startticks", "signal",
                    "errno", "monotonic_ns", "direct"} or \
               value["stage"] not in ("term", "kill") or \
               type(value["pid"]) is not int or value["pid"] <= 0 or \
               type(value["direct"]) is not bool or \
               type(value["signal"]) is not int or value["signal"] != \
                    (15 if value["stage"] == "term" else 9) or \
               type(value["errno"]) is not int or value["errno"] <= 0 or \
               type(value["monotonic_ns"]) is not int or value["monotonic_ns"] <= 0 or \
               (value["startticks"] is not None and
                (type(value["startticks"]) is not int or value["startticks"] <= 0)) or \
               (value["direct"] is False and value["startticks"] is None):
                raise ValueError("supervisor cleanup signal error")
            if value["direct"]:
                if preflight_stage == "sentinel-wait":
                    if type(value["startticks"]) is not int or value["startticks"] <= 0:
                        raise ValueError("supervisor sentinel authority")
                elif owner_identity.get("state") == "MATCHED":
                    if type(value["startticks"]) is not int or value["startticks"] <= 0 or \
                       value["startticks"] != owner_identity["startticks"] or \
                       value["pid"] != owner_identity["pid"]:
                        raise ValueError("supervisor direct signal identity")
                elif owner_identity.get("state") not in ("UNOBSERVED", "MISMATCH"):
                    raise ValueError("supervisor sentinel authority" if
                                     preflight_stage is not None else
                                     "supervisor direct signal authority")
        elif value.get("kind") == "deadline" and \
                value.get("stage") == "publication-finish":
            if set(value) != {"kind", "stage", "monotonic_ns",
                              "deadline_ns"} or any(
                    type(value[key]) is not int or value[key] <= 0
                    for key in ("monotonic_ns", "deadline_ns")) or \
                    value["monotonic_ns"] < value["deadline_ns"]:
                raise ValueError("supervisor publication finish deadline")
        else:
            validate_cleanup_unresolved([value])
    publication_finishes = [value for value in unresolved if
        value.get("kind") == "deadline" and
        value.get("stage") == "publication-finish"]
    if len(publication_finishes) > 1:
        raise ValueError("supervisor publication finish cardinality")
    direct_timeouts = [value for value in unresolved if
        value.get("kind") == "wait-timeout" and
        value.get("stage") == "direct"]
    if len(direct_timeouts) > 1:
        raise ValueError("supervisor direct wait timeout cardinality")
    if finished_ns > deadline_ns:
        if len(publication_finishes) != 1:
            raise ValueError("supervisor publication finish deadline")
    elif publication_finishes:
        raise ValueError("supervisor publication finish deadline")
    events = cleanup["events"]
    late_owner_start = preflight_failure == {
        "stage": "sentinel-wait", "type": "TimeoutError",
        "message": "owner start deadline", "errno": None} and \
        owner_identity == {"state": "NOT_SPAWNED", "pid": None,
                           "ppid": None, "startticks": None,
                           "spawn_error": None} and \
        type(preflight_started_ns) is int and preflight_started_ns > 0 and \
        type(original_wait_deadline_ns) is int and \
        original_wait_deadline_ns == preflight_started_ns + 5_000_000_000 and \
        original_wait_deadline_ns < trigger_ns
    for index, event in enumerate(events):
        event_ns = event.get("monotonic_ns") if type(event) is dict else None
        if type(event_ns) is not int or event_ns > min(deadline_ns, finished_ns):
            raise ValueError("supervisor cleanup event time")
        if event_ns >= trigger_ns:
            continue
        if not (late_owner_start and index == 0 and
                set(event) == {"kind", "pid", "startticks",
                               "raw_wait_status", "direct", "monotonic_ns"} and
                event["kind"] == "wait" and type(event["pid"]) is int and
                event["pid"] > 0 and event["startticks"] is None and
                type(event["raw_wait_status"]) is int and
                event["raw_wait_status"] == 73 << 8 and
                event["direct"] is True and
                preflight_started_ns <= event_ns <= original_wait_deadline_ns):
            raise ValueError("supervisor cleanup event time")
    if [event["monotonic_ns"] for event in events] != sorted(
            event["monotonic_ns"] for event in events):
        raise ValueError("supervisor cleanup event order")
    owner_pid = owner_identity.get("pid")
    known = {owner_pid: owner_identity["startticks"]} \
        if owner_identity.get("state") == "MATCHED" else {}
    def direct_birth_state(pid, before_ns, before_index=None):
        # Array order is authoritative for invalidation ties.  Positive birth
        # proof remains strictly earlier in time (the loop below skips ties),
        # while every retirement at an earlier array position revokes it.
        if before_index is None:
            before_index = len(events)
        birth = owner_identity["startticks"] if \
            owner_identity.get("state") == "MATCHED" and pid == owner_pid \
            else None
        authorized = birth is not None
        birth_contradicted = False
        retired_authority = False
        for index, event in enumerate(events):
            event_ns = event.get("monotonic_ns", before_ns)
            if event_ns > before_ns or \
               (event_ns == before_ns and index >= before_index):
                continue
            if event.get("kind") == "echild" or \
                    (event.get("kind") == "wait" and
                     event.get("pid") == pid):
                authorized = False
                retired_authority = True
                continue
            if event.get("kind") != "identity" or event.get("pid") != pid:
                continue
            if event.get("observation") == "observed" and \
                    (event.get("matched") is not True or
                     event.get("ppid") != supervisor_pid or
                     (birth is not None and
                      event.get("startticks") != birth)):
                authorized = False
                if birth is not None and event.get("startticks") != birth:
                    birth_contradicted = True
            if index == 0:
                continue
            first, second = events[index - 1:index + 1]
            if not retired_authority and not birth_contradicted and \
               first.get("kind") == second.get("kind") == "identity" and \
               first.get("matched") is second.get("matched") is True and \
               first.get("observation") == second.get("observation") == "observed" and \
               first.get("pid") == second.get("pid") == pid and \
               first.get("ppid") == second.get("ppid") == supervisor_pid and \
               first.get("startticks") == second.get("startticks") and \
               (first.get("phase"), second.get("phase")) in (
                   ("term-identity-1", "term-identity-2"),
                   ("kill-identity-1", "kill-identity-2")):
                if second.get("monotonic_ns") >= before_ns:
                    continue
                birth = second["startticks"]
                authorized = True
        return birth, authorized, birth is not None, retired_authority
    def established_birth(pid, before_ns):
        return direct_birth_state(pid, before_ns)[0]
    retired = set()
    retired_pids = set()
    direct_waits = []
    direct_wait_seen = False
    direct_signals = []
    # A failed-preflight sentinel has no summary owner identity.  Its direct
    # signal authority is therefore established only by two immediately
    # preceding matching positive observations, and must join a later wait.
    sentinel_signals = []
    echild_seen = False
    adopted_signals = []
    adopted_waits = []
    for index, event in enumerate(events):
        kind = event.get("kind")
        if echild_seen or (direct_wait_seen and kind == "signal" and
                event.get("direct_child") is True):
            raise ValueError("supervisor cleanup terminal order")
        if kind == "identity":
            keys = {"kind", "phase", "observation", "pid", "ppid",
                    "startticks", "matched", "monotonic_ns"}
            if set(event) != keys or type(event["matched"]) is not bool or \
               not cleanup_phase(event["phase"], suffix=True):
                raise ValueError("supervisor cleanup identity")
            validate_supervisor_observation({key: event[key] for key in
                ("observation", "pid", "ppid", "startticks", "monotonic_ns")})
            if event["observation"] != "observed" and event["matched"] is not False:
                raise ValueError("supervisor cleanup identity")
            if event["matched"] is True and index > 0:
                prior = events[index - 1]
                if prior.get("kind") == "identity" and prior.get("matched") is True and \
                   (prior.get("pid"), prior.get("ppid"), prior.get("startticks")) == \
                   (event["pid"], event["ppid"], event["startticks"]) and \
                   event["ppid"] == supervisor_pid and \
                   prior.get("phase", "").endswith("-1") and \
                   event.get("phase") == prior["phase"][:-1] + "2":
                    known[event["pid"]] = event["startticks"]
        elif kind == "signal":
            # Keep the supervisor signal schema distinct from owner cleanup.
            signal_keys = {"kind", "pid", "startticks", "signal", "monotonic_ns"}
            direct_signal = "direct_child" in event
            expected_keys = signal_keys | ({"direct_child"} if direct_signal else set())
            if set(event) != expected_keys or type(event["pid"]) is not int or event["pid"] <= 0 or \
               (direct_signal and event["direct_child"] is not True) or \
               type(event["signal"]) is not int or \
               event["signal"] not in (9, 15) or \
               (event["startticks"] is not None and
                (type(event["startticks"]) is not int or event["startticks"] <= 0)) or \
               (event["startticks"] is None and event["pid"] in known) or \
               (event["startticks"] is not None and
                known.get(event["pid"]) != event["startticks"] and
                not (direct_signal and owner_pid is None)):
                raise ValueError("supervisor cleanup signal")
            if direct_signal:
                birth, authorized, ever_established, retired_authority = \
                    direct_birth_state(event["pid"], event["monotonic_ns"], index)
                if retired_authority or \
                   (event["startticks"] is None and ever_established) or \
                   (event["startticks"] is not None and
                    (not authorized or event["startticks"] != birth)):
                    raise ValueError("supervisor sentinel authority" if
                                     owner_pid is None else
                                     "supervisor direct signal identity")
            if direct_signal and owner_pid is not None:
                if event["pid"] != owner_pid or \
                   (event["startticks"] is None and birth is not None):
                    raise ValueError("supervisor direct signal identity")
                if index < 2:
                    raise ValueError("supervisor direct signal identity")
                first, second = events[index - 2:index]
                stage = "term" if event["signal"] == 15 else "kill"
                phases = (stage + "-identity-1", stage + "-identity-2")
                if event["startticks"] is None:
                    if any(value.get("kind") != "identity" or
                           value.get("phase") != phases[pair_index] or
                           value.get("pid") != owner_pid or
                           value.get("observation") not in ("missing", "error") or
                           value.get("matched") is not False
                           for pair_index, value in enumerate((first, second))):
                        raise ValueError("supervisor direct signal identity")
                elif any(value.get("kind") != "identity" or
                         value.get("phase") != phases[pair_index] or
                         value.get("pid") != owner_pid or
                         value.get("ppid") != supervisor_pid or
                         value.get("matched") is not True or
                         value.get("startticks") != event["startticks"]
                         for pair_index, value in enumerate((first, second))):
                    raise ValueError("supervisor direct signal identity")
            if direct_signal and direct_wait_seen:
                raise ValueError("supervisor direct signal after wait")
            if not direct_signal and event["startticks"] is None:
                raise ValueError("supervisor cleanup signal identity")
            if not direct_signal and event["pid"] == owner_pid:
                raise ValueError("supervisor direct signal schema")
            if not direct_signal and index < 2:
                raise ValueError("supervisor cleanup signal identity")
            if not direct_signal:
                first, second = events[index - 2:index]
                first_phase = first.get("phase", "")
                if any(value.get("kind") != "identity" or
                       value.get("matched") is not True or
                       value.get("pid") != event["pid"] or
                       value.get("ppid") != supervisor_pid or
                       value.get("startticks") != event["startticks"]
                       for value in (first, second)) or \
                   not first_phase.startswith("owned-scan-") or \
                   not first_phase.endswith("-1") or \
                   second.get("phase") != first_phase[:-1] + "2":
                    raise ValueError("supervisor cleanup signal identity")
                identity = (event["pid"], event["startticks"])
                if identity in retired or event["pid"] in retired_pids:
                    raise ValueError("supervisor cleanup signal")
                adopted_signals.append((event["pid"], event["startticks"],
                                        event["signal"]))
            elif owner_pid is None:
                if preflight_stage != "sentinel-wait" or \
                   type(event["startticks"]) is not int or event["startticks"] <= 0 or \
                   index < 2:
                    raise ValueError("supervisor sentinel authority")
                first, second = events[index - 2:index]
                stage = "term" if event["signal"] == 15 else "kill"
                phases = (stage + "-identity-1", stage + "-identity-2")
                if any(value.get("kind") != "identity" or
                       value.get("phase") != phases[pair_index] or
                       value.get("observation") != "observed" or
                       value.get("matched") is not True or
                       value.get("pid") != event["pid"] or
                       value.get("ppid") != supervisor_pid or
                       value.get("startticks") != event["startticks"]
                       for pair_index, value in enumerate((first, second))):
                    raise ValueError("supervisor sentinel authority")
                sentinel = (event["pid"], event["startticks"])
                if sentinel in retired:
                    raise ValueError("supervisor cleanup signal")
                known[event["pid"]] = event["startticks"]
                direct_signals.append((event["pid"], event["startticks"]))
                sentinel_signals.append(sentinel)
        elif kind == "wait":
            if set(event) != {"kind", "pid", "startticks", "raw_wait_status",
                    "direct", "monotonic_ns"} or type(event["pid"]) is not int or \
               event["pid"] <= 0 or type(event["raw_wait_status"]) is not int or \
               type(event["direct"]) is not bool or \
               (event["startticks"] is not None and
                (type(event["startticks"]) is not int or event["startticks"] <= 0)):
                raise ValueError("supervisor cleanup wait")
            wait_fields(event["raw_wait_status"])
            if event["direct"]:
                birth, authorized, ever_established, retired_authority = \
                    direct_birth_state(event["pid"], event["monotonic_ns"], index)
                if event["pid"] in retired_pids or retired_authority or \
                   (event["startticks"] is None and ever_established) or \
                   (event["startticks"] is not None and
                    (not authorized or event["startticks"] != birth)):
                    raise ValueError("supervisor direct wait retired pid")
                if owner_pid is not None:
                    if event["pid"] != owner_pid:
                        raise ValueError("supervisor direct wait identity")
                if owner_pid is None:
                    sentinel = (event["pid"], event["startticks"])
                    if sentinel in retired:
                        raise ValueError("supervisor duplicate direct wait")
                    known[event["pid"]] = event["startticks"]
                direct_waits.append(event)
                if len(direct_waits) != 1:
                    raise ValueError("supervisor duplicate direct wait")
                # Direct retirement revokes the PID slot as well as its exact
                # birth identity; a later adopted observation cannot revive it.
                identity = (event["pid"], event["startticks"])
                retired.add(identity)
                retired_pids.add(event["pid"])
                direct_wait_seen = True
            else:
                if event["pid"] == owner_pid or \
                        (event["startticks"] is None and event["pid"] in known) or \
                        (event["startticks"] is not None and
                         known.get(event["pid"]) != event["startticks"]):
                    raise ValueError("supervisor cleanup adopted wait")
                identity = (event["pid"], event["startticks"])
                if identity in retired or event["pid"] in retired_pids:
                    raise ValueError("supervisor duplicate adopted wait")
                adopted_waits.append((event["pid"], event["startticks"],
                                      event["raw_wait_status"]))
                retired.add(identity)
                retired_pids.add(event["pid"])
        elif kind == "owned-scan":
            if set(event) != {"kind", "monotonic_ns", "pids"} or \
               type(event["pids"]) is not list:
                raise ValueError("supervisor owned scan")
            for identity in event["pids"]:
                if type(identity) is not dict or set(identity) != {
                        "pid", "ppid", "startticks"} or \
                   identity["ppid"] != supervisor_pid or any(
                       type(identity[key]) is not int or identity[key] <= 0
                       for key in identity):
                    raise ValueError("supervisor owned scan")
                known[identity["pid"]] = identity["startticks"]
        elif kind == "echild":
            if set(event) != {"kind", "monotonic_ns", "return", "errno"} or \
               type(event["return"]) is not int or event["return"] != -1 or \
               type(event["errno"]) is not int or event["errno"] != 10:
                raise ValueError("supervisor echild")
            echild_seen = True
        else:
            raise ValueError("supervisor cleanup event")
    if preflight_stage == "sentinel-wait":
        sentinel_pids = {event["pid"] for event in events if
            (event.get("kind") == "wait" and event.get("direct") is True) or
            (event.get("kind") == "signal" and
             event.get("direct_child") is True) or
            (event.get("kind") == "identity" and
             event.get("phase") in {"term-identity-1", "term-identity-2",
                                    "kill-identity-1", "kill-identity-2"})}
        sentinel_pids.update(item["pid"] for item in unresolved if
            (item.get("kind") == "signal-error" and
             item.get("direct") is True) or
            item.get("kind") == "wait-timeout")
        if len(sentinel_pids) > 1:
            raise ValueError("supervisor sentinel timeout identity")
    if cleanup["complete"]:
        if unresolved or len(events) < 3 or \
           events[-3].get("kind") != "owned-scan" or events[-3].get("pids") != [] or \
           events[-2].get("kind") != "owned-scan" or events[-2].get("pids") != [] or \
           events[-1].get("kind") != "echild":
            raise ValueError("supervisor cleanup terminal")
        if sum(event.get("kind") == "echild" for event in events) != 1:
            raise ValueError("supervisor cleanup terminal")
        if (owner_pid is not None or direct_signals) and (len(direct_waits) != 1 or
                (owner_pid is not None and direct_waits[0]["pid"] != owner_pid) or
                (direct_signals and (direct_waits[0]["pid"], direct_waits[0]["startticks"]) != direct_signals[0]) or
                (owner_pid is not None and direct_waits[0]["startticks"] !=
                 known.get(owner_pid))):
            raise ValueError("supervisor direct wait")
        if sentinel_signals and (len(direct_waits) != 1 or
                (direct_waits[0]["pid"], direct_waits[0]["startticks"]) !=
                sentinel_signals[-1]):
            raise ValueError("supervisor sentinel wait")
        signaled_ids = [(pid, ticks) for pid, ticks, _sig in adopted_signals]
        waited_ids = [(pid, ticks) for pid, ticks, _raw in adopted_waits]
        remaining_waits = waited_ids[:]
        for identity in signaled_ids:
            if identity not in remaining_waits:
                raise ValueError("supervisor adopted signal wait")
            remaining_waits.remove(identity)
    # A direct signal-error is an observation failure, not a signal event, but
    # it still needs the same birth proof and later direct-wait join.
    if preflight_stage is not None and preflight_stage != "sentinel-wait":
        if any(item.get("direct") is True for item in unresolved):
            raise ValueError("supervisor sentinel authority")
    for item in unresolved:
        if item.get("kind") != "signal-error":
            continue
        preceding = [event for event in events if
                     event["monotonic_ns"] < item["monotonic_ns"]]
        if len(preceding) < 2:
            raise ValueError("supervisor signal error authority")
        first, second = preceding[-2:]
        if item["direct"]:
            if any(event.get("kind") == "echild" or
                   (event.get("kind") == "wait" and
                    event.get("direct") is True)
                   for event in preceding):
                raise ValueError("supervisor direct signal error authority")
            expected_phases = (item["stage"] + "-identity-1",
                               item["stage"] + "-identity-2")
            birth, authorized, ever_established, retired_authority = \
                direct_birth_state(item["pid"], item["monotonic_ns"], len(events))
            if item["startticks"] is None:
                if preflight_stage is not None or item["pid"] != owner_pid or \
                   owner_identity.get("state") not in ("UNOBSERVED", "MISMATCH") or \
                   ever_established or retired_authority or \
                   any(value.get("kind") != "identity" or
                       value.get("phase") != expected_phases[index] or
                       value.get("pid") != item["pid"] or
                       value.get("observation") not in ("missing", "error") or
                       value.get("matched") is not False
                       for index, value in enumerate((first, second))):
                    raise ValueError("supervisor direct signal error authority")
            elif not authorized or item["startticks"] != birth or any(
                     value.get("kind") != "identity" or
                     value.get("phase") != expected_phases[index] or
                     value.get("observation") != "observed" or
                     value.get("matched") is not True or
                     value.get("pid") != item["pid"] or
                     value.get("startticks") != item["startticks"] or
                     value.get("ppid") != supervisor_pid
                     for index, value in enumerate((first, second))) or \
                    (preflight_stage is None and item["pid"] != owner_pid):
                raise ValueError("supervisor direct signal error authority")
            matching_waits = [wait for wait in direct_waits if
                              wait["monotonic_ns"] > item["monotonic_ns"] and
                              (wait["pid"], wait["startticks"]) ==
                              (item["pid"], item["startticks"])]
        else:
            first_phase = first.get("phase", "")
            adopted_retirement = any(
                (event.get("kind") == "echild" and
                 event.get("monotonic_ns", 0) <= item["monotonic_ns"]) or
                (event.get("kind") == "wait" and
                 event.get("pid") == item["pid"] and
                 event.get("monotonic_ns", 0) <= item["monotonic_ns"])
                for event in events)
            if item["pid"] == owner_pid or any(
                    event.get("kind") == "echild" or
                    (event.get("kind") == "wait" and
                     event.get("direct") is False and
                     (event.get("pid"), event.get("startticks")) ==
                     (item["pid"], item["startticks"]))
                    for event in preceding) or \
               any(value.get("kind") != "identity" or
                   value.get("observation") != "observed" or
                   value.get("matched") is not True or
                   value.get("pid") != item["pid"] or
                   value.get("ppid") != supervisor_pid or
                   value.get("startticks") != item["startticks"]
                    for value in (first, second)) or adopted_retirement or \
               not first_phase.startswith("owned-scan-") or \
               not first_phase.endswith("-1") or \
               second.get("phase") != first_phase[:-1] + "2":
                raise ValueError("supervisor adopted signal error authority")
            matching_waits = [wait for wait in events if
                wait.get("kind") == "wait" and wait.get("direct") is False and
                wait["monotonic_ns"] > item["monotonic_ns"] and
                (wait.get("pid"), wait.get("startticks")) ==
                (item["pid"], item["startticks"])]
            owned_phase = first_phase[:-2]
            matching_owned = [value for value in unresolved if
                value.get("kind") == "owned" and
                value.get("phase") == owned_phase and
                value.get("pid") == item["pid"] and
                value.get("ppid") == supervisor_pid and
                value.get("startticks") == item["startticks"] and
                value.get("monotonic_ns", item["monotonic_ns"]) <
                    item["monotonic_ns"]]
            matching_expirations = [value for value in unresolved if
                value.get("kind") == "deadline" and
                value.get("stage") == "owned-scan" and
                value.get("deadline_ns") == deadline_ns and
                value.get("monotonic_ns", 0) >= deadline_ns and
                value.get("monotonic_ns", 0) > item["monotonic_ns"]]
        matching_timeouts = [value for value in unresolved if
            value.get("kind") == "wait-timeout" and
            value.get("monotonic_ns", 0) > item["monotonic_ns"] and
            value.get("pid") == item["pid"] and
            value.get("startticks") == item["startticks"]]
        intervening_echild = any(event.get("kind") == "echild" and
            event.get("monotonic_ns", 0) > item["monotonic_ns"]
            for event in events)
        expiration_join = not item["direct"] and not cleanup["complete"] and \
            bool(matching_owned) and bool(matching_expirations) and \
            not intervening_echild
        if not matching_waits and not matching_timeouts and not expiration_join:
            raise ValueError("supervisor signal error join")
    if any(type(item.get("monotonic_ns")) is not int or
           not trigger_ns <= item["monotonic_ns"] <= finished_ns
           for item in unresolved):
        raise ValueError("supervisor cleanup unresolved time")
    for item in unresolved:
        if item["kind"] == "deadline":
            if item.get("stage") == "publication-finish":
                if cleanup["complete"] or item["deadline_ns"] != deadline_ns or \
                        item["monotonic_ns"] != finished_ns:
                    raise ValueError("supervisor publication finish deadline")
            elif item["deadline_ns"] != deadline_ns:
                raise ValueError("supervisor cleanup deadline")
        elif item["kind"] == "wait-timeout":
            if owner_pid is not None and item["pid"] != owner_pid:
                raise ValueError("supervisor direct wait timeout identity")
            if item["startticks"] != established_birth(
                    item["pid"], item["monotonic_ns"]):
                raise ValueError("supervisor direct wait timeout identity")
            prior_reap = any(event.get("kind") == "wait" and
                event.get("pid") == item["pid"] and
                event.get("monotonic_ns", 0) <= item["monotonic_ns"]
                for event in events)
            if prior_reap:
                raise ValueError("supervisor direct wait timeout retirement")
            if item["stage"] == "direct":
                if original_wait_deadline_ns is None or item["deadline_ns"] != \
                        min(original_wait_deadline_ns, deadline_ns):
                    raise ValueError("supervisor direct wait timeout deadline")
            elif item["stage"] in ("term", "kill"):
                expected_signal = 15 if item["stage"] == "term" else 9
                budget = 1_000_000_000 if item["stage"] == "term" else \
                    5_000_000_000
                attempts = [event for event in events
                    if event.get("kind") == "signal" and
                       event.get("direct_child") is True and
                       event.get("pid") == item["pid"] and
                       event.get("startticks") == item["startticks"] and
                       event.get("signal") == expected_signal and
                       event["monotonic_ns"] <= item["monotonic_ns"]]
                if not attempts or item["deadline_ns"] != min(
                        deadline_ns, attempts[-1]["monotonic_ns"] + budget):
                    raise ValueError("supervisor direct stage deadline")
    if cleanup["complete"] and finished_ns > deadline_ns:
        raise ValueError("supervisor cleanup complete deadline")
    if finished_ns > deadline_ns and not any(
            item.get("kind") in ("deadline", "wait-timeout") and
            item.get("deadline_ns") == deadline_ns and
            item.get("monotonic_ns", 0) >= deadline_ns for item in unresolved):
        raise ValueError("supervisor cleanup expiration evidence")
    # Cleanup failures are sticky: later empty scans/ECHILD cannot erase an
    # unresolved owner or adopted child.
    nonempty_scan = any(event.get("kind") == "owned-scan" and event.get("pids")
                        for event in events)
    if nonempty_scan and not cleanup["unresolved"]:
        raise ValueError("supervisor cleanup unresolved")
    if not cleanup["complete"] and not cleanup["unresolved"]:
        raise ValueError("supervisor cleanup unresolved")

def validate_supervisor_record(result, root=None):
    """Validate supervisor lifecycle joins without requiring a live evidence tree.

    ``root`` is optional; when supplied it is used only for the attempt-root
    binding and evidence hashes.  This deliberately covers failed preflight
    records, whose owner never existed.
    """
    if type(result) is not dict or set(result) != SUPERVISOR_KEYS or \
       type(result.get("schema_version")) is not int or \
       result.get("schema_version") != 1 or \
       result.get("kind") != "STORAGE_FAULT_V2_SUPERVISOR":
        raise ValueError("supervisor record")
    if root is not None and result["attempt_root"] != str(Path(root).resolve()):
        raise ValueError("supervisor attempt root")
    ints = ("supervisor_pid", "preflight_started_ns", "sentinel_wait_deadline_ns", "started_ns",
            "cleanup_trigger_ns", "supervisor_cleanup_deadline_ns",
            "supervisor_deadline_ns", "finished_ns")
    if any(type(result[key]) is not int or result[key] <= 0 for key in ints) or \
       result["sentinel_wait_deadline_ns"] != result["preflight_started_ns"] + 5_000_000_000 or \
       result["supervisor_cleanup_deadline_ns"] != result["cleanup_trigger_ns"] + 22_000_000_000 or \
       not result["preflight_started_ns"] <= result["started_ns"] <= \
           result["sentinel_wait_deadline_ns"] or \
       not result["cleanup_trigger_ns"] <= result["finished_ns"] <= \
           result["supervisor_deadline_ns"]:
        raise ValueError("supervisor deadlines")
    for key in ("owner_wait_observed", "sigchld_default", "sentinel_wait_passed",
                "owner_result_present", "witness_present", "owner_errors_present"):
        if type(result[key]) is not bool:
            raise ValueError("supervisor boolean fields")
    identity = result["owner_identity"]
    if type(identity) is not dict or set(identity) != {
            "state", "pid", "ppid", "startticks", "spawn_error"}:
        raise ValueError("supervisor owner identity")
    if identity["state"] == "MATCHED":
        if any(type(identity[key]) is not int or identity[key] <= 0
               for key in ("pid", "ppid", "startticks")) or \
           identity["spawn_error"] is not None:
            raise ValueError("supervisor owner identity")
    elif identity["state"] in ("MISMATCH", "UNOBSERVED"):
        if type(identity["pid"]) is not int or identity["pid"] <= 0 or \
           identity["ppid"] is not None or identity["startticks"] is not None or \
           identity["spawn_error"] is not None:
            raise ValueError("supervisor owner identity")
    elif identity["state"] == "SPAWN_FAILED":
        spawn_error = identity["spawn_error"]
        if any(identity[key] is not None for key in ("pid", "ppid", "startticks")) or \
           type(spawn_error) is not dict or \
           set(spawn_error) != {"type", "message", "errno"} or \
           type(spawn_error["type"]) is not str or not spawn_error["type"] or \
           type(spawn_error["message"]) is not str or not spawn_error["message"] or \
           (spawn_error["errno"] is not None and
            (type(spawn_error["errno"]) is not int or
             spawn_error["errno"] <= 0)):
            raise ValueError("supervisor owner identity")
    elif identity["state"] == "NOT_SPAWNED":
        # The preflight-state join below owns the exact absent-owner fields so
        # a malformed NOT_SPAWNED record retains that specific diagnostic.
        pass
    else:
        raise ValueError("supervisor owner identity")
    observations = result["owner_identity_observations"]
    if type(observations) is not list or len(observations) > 2:
        raise ValueError("supervisor owner observations")
    for observation in observations:
        validate_supervisor_observation(observation)
    if [item["monotonic_ns"] for item in observations] != sorted(
            item["monotonic_ns"] for item in observations) or any(
            not result["started_ns"] <= item["monotonic_ns"] <=
                result["cleanup_trigger_ns"] for item in observations):
        raise ValueError("supervisor owner observation chronology")
    observed = [item for item in observations if item["observation"] == "observed"]
    if identity["state"] == "MATCHED":
        if len(observations) != 2 or len(observed) != 2 or len({
                (item["pid"], item["ppid"], item["startticks"]) for item in observed}) != 1 or \
           any((item["pid"], item["ppid"], item["startticks"]) !=
               (identity["pid"], identity["ppid"], identity["startticks"])
               for item in observed):
            raise ValueError("supervisor owner observations")
    elif identity["state"] == "MISMATCH":
        # A single observed wrong-PPID record is a valid MISMATCH, but the
        # frozen result schema does not carry the supervisor PID separately.
        # The producer's classify_owner performs that comparison; here retain
        # the strongest independently representable check.
        if not observed:
            raise ValueError("supervisor owner observations")
    elif identity["state"] == "UNOBSERVED" and len(observed) >= 2 and len(observations) == 2 and \
            len({(item["pid"], item["ppid"], item["startticks"]) for item in observed}) == 1:
        raise ValueError("supervisor owner observations")
    failure = result["preflight_failure"]
    preflight = failure is not None
    late_owner_start_failure = False
    if preflight:
        if observations:
            raise ValueError("supervisor preflight state")
    elif identity["state"] == "SPAWN_FAILED":
        if observations:
            raise ValueError("supervisor owner observations")
    else:
        computed_state, computed_birth = classify_supervisor_observations(
            identity["pid"], result["supervisor_pid"], observations)
        if identity["state"] != computed_state or \
           (computed_state == "MATCHED" and
            (identity["ppid"] != result["supervisor_pid"] or
             identity["startticks"] != computed_birth)) or \
           (computed_state != "MATCHED" and
            (identity["ppid"] is not None or identity["startticks"] is not None)):
            raise ValueError("supervisor owner classification")
    if preflight:
        if set(failure) != {"stage", "type", "message", "errno"} or \
           failure["stage"] not in {"sigchld-default", "sentinel-fork", "sentinel-wait"} or \
           type(failure["type"]) is not str or not failure["type"] or \
           type(failure["message"]) is not str or not failure["message"] or \
           (failure["errno"] is not None and
            (type(failure["errno"]) is not int or failure["errno"] <= 0)):
            raise ValueError("supervisor preflight failure")
        if result["status"] != "OWNER_ERROR" or result["started_ns"] != \
                result["preflight_started_ns"] or identity != {
                    "state": "NOT_SPAWNED", "pid": None, "ppid": None,
                    "startticks": None, "spawn_error": None} or observations:
            raise ValueError("supervisor preflight state")
        if result["owner_wait_deadline_ns"] is not None or \
           result["owner_wait_observed"] is not False or \
           result["owner_exit_code"] is not None or result["owner_signal"] is not None:
            raise ValueError("supervisor absent owner")
        if result["supervisor_deadline_ns"] != result["preflight_started_ns"] + \
                33_000_000_000 or any(result[name + "_present"] or
                result[name + "_sha256"] is not None for name in
                ("owner_result", "witness", "owner_errors")) or \
           result["owner_stdout_sha256"] != sha(b"") or \
           result["owner_stderr_sha256"] != sha(b""):
            raise ValueError("supervisor absent evidence")
        if result["sigchld_default"] is not (failure["stage"] != "sigchld-default") or \
           result["sentinel_wait_passed"] is not False:
            raise ValueError("supervisor preflight flags")
        late_owner_start_failure = failure == {
            "stage": "sentinel-wait", "type": "TimeoutError",
            "message": "owner start deadline", "errno": None}
        if late_owner_start_failure and result["cleanup_trigger_ns"] <= \
                result["sentinel_wait_deadline_ns"]:
            raise ValueError("supervisor owner start deadline")
    else:
        # Validate the independent identity and clock joins before the
        # aggregate COMPLETE predicate.  A malformed owner identity or wait
        # deadline must report its specific contract violation, rather than
        # being hidden by the later completion-state check.
        terminal_error = identity["state"] in {"SPAWN_FAILED", "UNOBSERVED", "MISMATCH"}
        if terminal_error:
            if result["status"] != "OWNER_ERROR" or result["sigchld_default"] is not True or \
               result["sentinel_wait_passed"] is not True:
                raise ValueError("supervisor owner error state")
            if identity["state"] == "SPAWN_FAILED":
                if type(result["owner_wait_deadline_ns"]) is not int or \
                   result["owner_wait_deadline_ns"] <= 0 or \
                   result["owner_wait_deadline_ns"] != result["started_ns"] + 220_000_000_000 or result["owner_wait_observed"] is not False or \
                   result["owner_exit_code"] is not None or result["owner_signal"] is not None or \
                   any(identity[key] is not None for key in ("pid", "ppid", "startticks")) or \
                   type(identity["spawn_error"]) is not dict or set(identity["spawn_error"]) != {
                       "type", "message", "errno"}:
                    raise ValueError("supervisor owner identity")
            else:
                if type(identity["pid"]) is not int or identity["pid"] <= 0 or \
                   identity["ppid"] is not None or identity["startticks"] is not None or \
                   identity["spawn_error"] is not None:
                    raise ValueError("supervisor owner identity")
                if type(result["owner_wait_deadline_ns"]) is not int or \
                   result["owner_wait_deadline_ns"] != result["started_ns"] + 220_000_000_000:
                    raise ValueError("supervisor deadlines")
                if result["owner_wait_observed"]:
                    if (type(result["owner_exit_code"]) is not int or
                            result["owner_exit_code"] < 0) == \
                       (type(result["owner_signal"]) is not int or
                            result["owner_signal"] <= 0):
                        raise ValueError("supervisor owner wait")
                elif result["owner_exit_code"] is not None or result["owner_signal"] is not None:
                    raise ValueError("supervisor owner wait")
        elif type(identity["pid"]) is not int or type(identity["ppid"]) is not int or \
             type(identity["startticks"]) is not int:
            raise ValueError("supervisor owner identity")
        if terminal_error:
            # Cleanup is still authoritative for a post-preflight owner
            # failure; no owner wait is available to join.
            pass
        else:
            if type(result["owner_wait_deadline_ns"]) is not int or \
               result["owner_wait_deadline_ns"] <= 0 or \
               result["owner_wait_deadline_ns"] != result["started_ns"] + 220_000_000_000:
                raise ValueError("supervisor deadlines")
        if not terminal_error and (result["status"] not in ("COMPLETE", "OWNER_ERROR") or identity["state"] != "MATCHED" or \
           identity["spawn_error"] is not None or len(observations) != 2 or
           (result["owner_wait_observed"] and
            ((type(result["owner_exit_code"]) is not int or result["owner_exit_code"] < 0) ==
             (type(result["owner_signal"]) is not int or result["owner_signal"] <= 0))) or
           (not result["owner_wait_observed"] and
            (result["owner_exit_code"] is not None or result["owner_signal"] is not None or
             result["status"] != "OWNER_ERROR")) or
           (result["status"] == "COMPLETE" and (not result["owner_wait_observed"] or
            result["owner_exit_code"] != 0 or result["owner_signal"] is not None)) or
           result["sigchld_default"] is not True or \
           result["sentinel_wait_passed"] is not True):
            raise ValueError("supervisor complete state")
        if result["supervisor_deadline_ns"] != result["started_ns"] + \
                248_000_000_000:
            raise ValueError("supervisor complete deadline")
    cleanup = result["supervisor_cleanup"]
    if type(cleanup) is not dict or type(cleanup.get("complete")) is not bool:
        raise ValueError("supervisor cleanup record")
    if result["status"] == "COMPLETE" and cleanup["complete"] is not True:
        raise ValueError("supervisor cleanup incomplete")
    validate_supervisor_cleanup(cleanup, identity, result["supervisor_pid"],
        result["sentinel_wait_deadline_ns"] if preflight else
        result["owner_wait_deadline_ns"], result["cleanup_trigger_ns"],
        result["supervisor_cleanup_deadline_ns"],
        result["supervisor_deadline_ns"], result["finished_ns"],
        failure["stage"] if preflight else None,
        failure if preflight else None,
        result["preflight_started_ns"] if preflight else None)
    direct_waits = [event for event in cleanup["events"]
                    if event.get("kind") == "wait" and
                    event.get("direct") is True]
    direct_timeouts = [item for item in cleanup["unresolved"]
        if item.get("kind") == "wait-timeout" and
        item.get("stage") == "direct"]
    if late_owner_start_failure:
        if len(direct_waits) != 1 or direct_timeouts or \
                not cleanup["events"] or cleanup["events"][0] is not direct_waits[0]:
            raise ValueError("sentinel owner start wait")
        wait = direct_waits[0]
        if set(wait) != {"kind", "pid", "startticks", "raw_wait_status",
                        "direct", "monotonic_ns"} or \
           type(wait["pid"]) is not int or wait["pid"] <= 0 or \
           wait["startticks"] is not None or \
           type(wait["raw_wait_status"]) is not int or \
           wait["raw_wait_status"] != 73 << 8 or wait["direct"] is not True or \
           not result["preflight_started_ns"] <= wait["monotonic_ns"] <= \
               result["sentinel_wait_deadline_ns"] < result["cleanup_trigger_ns"]:
            raise ValueError("sentinel owner start wait")
    if direct_timeouts and direct_waits:
        timeout = direct_timeouts[0]
        waited = direct_waits[0]
        def has_later_direct_birth_pair():
            if timeout.get("startticks") is not None or \
                    type(waited.get("startticks")) is not int or \
                    waited["startticks"] <= 0:
                return False
            for pair_index in range(1, len(cleanup["events"])):
                first, second = cleanup["events"][pair_index - 1:pair_index + 1]
                if (first.get("phase"), second.get("phase")) not in (
                        ("term-identity-1", "term-identity-2"),
                        ("kill-identity-1", "kill-identity-2")):
                    continue
                if all(value.get("kind") == "identity" and
                       value.get("observation") == "observed" and
                       value.get("matched") is True and
                       value.get("pid") == timeout.get("pid") == waited.get("pid") and
                       value.get("ppid") == result["supervisor_pid"] and
                       value.get("startticks") == waited.get("startticks")
                       for value in (first, second)) and \
                   timeout["monotonic_ns"] < first["monotonic_ns"] <= \
                       second["monotonic_ns"] < waited["monotonic_ns"]:
                    return True
            return False
        later_established_birth = timeout.get("startticks") is None and \
            type(waited.get("startticks")) is int and \
            waited["startticks"] > 0 and has_later_direct_birth_pair()
        if timeout.get("pid") != waited.get("pid") or \
                (timeout.get("startticks") != waited.get("startticks") and
                 not later_established_birth):
            raise ValueError("supervisor direct timeout identity")
        if timeout["monotonic_ns"] >= waited["monotonic_ns"]:
            raise ValueError("supervisor direct timeout retirement")
    if result["status"] == "COMPLETE":
        if len(direct_waits) != 1 or direct_waits[0]["raw_wait_status"] != 0:
            raise ValueError("supervisor direct wait")
        if direct_waits[0]["monotonic_ns"] > result["owner_wait_deadline_ns"]:
            raise ValueError("supervisor owner wait deadline")
    if not preflight and identity["state"] != "SPAWN_FAILED":
        if result["owner_wait_observed"]:
            if len(direct_waits) != 1 or wait_fields(
                    direct_waits[0]["raw_wait_status"])[1:] != \
                    (result["owner_exit_code"], result["owner_signal"]):
                raise ValueError("supervisor owner wait")
        else:
            matching_direct_timeouts = [item for item in cleanup["unresolved"]
                if item.get("kind") == "wait-timeout" and
                item.get("stage") == "direct" and
                item.get("pid") == identity["pid"]]
            if direct_waits or len(matching_direct_timeouts) != 1:
                raise ValueError("supervisor owner wait timeout")
    elif not preflight and (direct_waits or direct_timeouts):
        raise ValueError("supervisor unexpected direct wait")
    if result["status"] == "COMPLETE" and cleanup["unresolved"]:
        raise ValueError("supervisor complete cleanup")
    if preflight:
        waits = [event for event in cleanup["events"]
                 if event.get("kind") == "wait" and event.get("direct") is True]
        if failure["stage"] == "sentinel-wait":
            if result["sentinel_wait_passed"] or (cleanup["complete"] and
                    len(waits) != 1) or len(waits) > 1:
                raise ValueError("sentinel wait closure")
            if not waits and len(direct_timeouts) != 1:
                raise ValueError("sentinel wait timeout")
        elif waits or direct_timeouts:
            raise ValueError("unexpected sentinel wait timeout")
    if root is not None:
        for name in ("owner_result", "witness", "owner_errors"):
            if result[name + "_present"]:
                digest = result[name + "_sha256"]
                if type(digest) is not str or sha(read(Path(root) /
                        {"owner_result": "owner-result.json", "witness": "witness.jsonl",
                         "owner_errors": "owner-errors.jsonl"}[name])) != digest:
                    raise ValueError("supervisor evidence hash")
    return result

def validate_supervisor(root):
    raw = read(root / "supervisor-result.json", 1 << 20)
    result = strict(raw)
    validate_supervisor_record(result, root)
    if type(result) is not dict or set(result) != SUPERVISOR_KEYS or \
       type(result["schema_version"]) is not int or result["schema_version"] != 1 or \
       type(result["kind"]) is not str or result["kind"] != \
            "STORAGE_FAULT_V2_SUPERVISOR" or result["status"] != "COMPLETE" or \
       result["attempt_root"] != str(root) or result["preflight_failure"] is not None or \
       result["sigchld_default"] is not True or result["sentinel_wait_passed"] is not True:
        raise ValueError("supervisor result")
    integer_fields = ("supervisor_pid", "preflight_started_ns", "sentinel_wait_deadline_ns",
        "started_ns", "owner_wait_deadline_ns", "cleanup_trigger_ns",
        "supervisor_cleanup_deadline_ns", "supervisor_deadline_ns", "finished_ns")
    if any(type(result[key]) is not int or result[key] <= 0 for key in integer_fields) or \
       result["sentinel_wait_deadline_ns"] != result["preflight_started_ns"] + 5000000000 or \
       not result["preflight_started_ns"] <= result["started_ns"] <= \
            result["sentinel_wait_deadline_ns"] or \
       result["owner_wait_deadline_ns"] != result["started_ns"] + 220000000000 or \
       result["supervisor_cleanup_deadline_ns"] != result["cleanup_trigger_ns"] + \
            22000000000 or result["supervisor_deadline_ns"] != \
            result["started_ns"] + 248000000000 or \
       not result["cleanup_trigger_ns"] <= result["finished_ns"] <= \
            result["supervisor_deadline_ns"]:
        raise ValueError("supervisor deadlines")
    identity = result["owner_identity"]
    observations = result["owner_identity_observations"]
    if type(identity) is not dict or set(identity) != {
            "state", "pid", "ppid", "startticks", "spawn_error"} or \
       identity["state"] != "MATCHED" or identity["spawn_error"] is not None or \
       any(type(identity[key]) is not int or identity[key] <= 0
           for key in ("pid", "ppid", "startticks")) or \
       type(observations) is not list or len(observations) != 2:
        raise ValueError("supervisor owner identity")
    for observation in observations:
        validate_supervisor_observation(observation)
    if any(observation["observation"] != "observed" or
           (observation["pid"], observation["ppid"], observation["startticks"]) !=
           (identity["pid"], identity["ppid"], identity["startticks"])
           for observation in observations):
        raise ValueError("supervisor owner identity")
    if result["owner_wait_observed"] is not True or \
       type(result["owner_exit_code"]) is not int or result["owner_exit_code"] != 0 or \
       result["owner_signal"] is not None:
        raise ValueError("supervisor owner wait")
    for name in ("owner_result", "witness", "owner_errors"):
        present = result[name + "_present"]
        digest = result[name + "_sha256"]
        if present is not True or type(digest) is not str or \
                re.fullmatch(r"[0-9a-f]{64}", digest) is None:
            raise ValueError("supervisor evidence record")
        actual = read(root / ({"owner_result": "owner-result.json",
            "witness": "witness.jsonl", "owner_errors": "owner-errors.jsonl"}[name]),
            1 << 20)
        if sha(actual) != digest:
            raise ValueError("supervisor evidence hash")
    for name in ("stdout", "stderr"):
        digest = result["owner_" + name + "_sha256"]
        if type(digest) is not str or re.fullmatch(r"[0-9a-f]{64}", digest) is None or \
           sha(read(root / ("owner-supervisor." + name + ".bin"), 1 << 20)) != digest:
            raise ValueError("supervisor capture hash")
    if read(root / "owner-errors.jsonl", 1 << 20) != b"":
        raise ValueError("supervisor owner errors")
    validate_supervisor_cleanup(result["supervisor_cleanup"], identity,
        result["supervisor_pid"], result["owner_wait_deadline_ns"],
        result["cleanup_trigger_ns"], result["supervisor_cleanup_deadline_ns"],
        result["supervisor_deadline_ns"], result["finished_ns"])
    if result["supervisor_cleanup"]["complete"] is not True:
        raise ValueError("supervisor cleanup incomplete")
    return result

def validate_owner(root, owner, selector, expected_wait):
    exact = {"schema_version", "kind", "nonce", "selector", "argv", "owner",
        "environment", "collector", "packet_count", "hashes", "inputs",
        "runtime_inputs", "captures", "artifacts", "owner_failure",
        "secondary_failures", "result_serialized_ns", "cleanup", "backend_enabled",
        "application_acceptance", "deadlines"}
    if type(owner) is not dict or set(owner) != exact or \
       type(owner["schema_version"]) is not int or owner["schema_version"] != 2 or \
       type(owner["kind"]) is not str or owner["kind"] != "OWNER_RESULT" or \
       type(owner["selector"]) is not int or owner["selector"] != selector or \
       type(owner["result_serialized_ns"]) is not int or owner["result_serialized_ns"] <= 0 or \
       type(owner["packet_count"]) is not int or owner["packet_count"] < 0 or \
       owner["backend_enabled"] is not False or \
       owner["application_acceptance"] is not False:
        raise ValueError("owner result")
    owner_errors = validate_owner_errors(read(root / "owner-errors.jsonl"), owner)
    owner_id = owner["owner"]
    if set(owner_id) != {"pid", "startticks"} or any(
            type(owner_id[key]) is not int or owner_id[key] <= 0 for key in owner_id):
        raise ValueError("owner identity")
    collector = owner["collector"]
    if set(collector) != {"pid", "identity_observed", "ppid", "startticks",
                         "reaped", "raw_wait_status"} or \
       collector["identity_observed"] is not True or collector["reaped"] is not True or \
       collector["ppid"] != owner_id["pid"] or collector["raw_wait_status"] != expected_wait or \
       type(collector["raw_wait_status"]) is not int or \
       any(type(collector[key]) is not int or collector[key] <= 0
           for key in ("pid", "ppid", "startticks")):
        raise ValueError("collector identity")
    hashes = owner["hashes"]
    if set(hashes) != {"source_sha256", "generated_sha256", "header_sha256", "elf_sha256"} or \
       hashes["source_sha256"] != SOURCE_SHA or any(type(value) is not str or
       re.fullmatch(r"[0-9a-f]{64}", value) is None for value in hashes.values()):
        raise ValueError("owner hashes")
    inputs = owner["inputs"]
    if set(inputs) != {"source", "generated_source", "header", "elf"}:
        raise ValueError("owner inputs")
    limits = {"source": 1 << 20, "generated_source": 1 << 20,
              "header": 1 << 20, "elf": 16 << 20}
    keys = {"source": "source_sha256", "generated_source": "generated_sha256",
            "header": "header_sha256", "elf": "elf_sha256"}
    for name in inputs:
        raw = validate_record(inputs[name], Path(inputs[name]["path"]), limits[name])
        if raw is None or sha(raw) != hashes[keys[name]]:
            raise ValueError("input binding")
    runtime = owner["runtime_inputs"]
    specs = {"request": ("request.bin", 406, REQUEST_SHA),
        "selected_inputs": ("selected-inputs.json", 76, SELECTED_SHA),
        "fixture": ("fixture", 27448, FIXTURE_SHA)}
    if type(runtime) is not dict or set(runtime) != set(specs):
        raise ValueError("runtime inputs")
    retained_root = (root / "retained-inputs").resolve()
    for name, (filename, size, digest) in specs.items():
        record = runtime[name]
        destination = retained_root / filename
        if type(record) is not dict or set(record) != {
                "source_path", "destination_path", "size", "sha256"} or \
           type(record["source_path"]) is not str or \
           record["destination_path"] != str(destination) or \
           type(record["size"]) is not int or record["size"] != size or \
           record["sha256"] != digest or \
           sha(read(destination, size)) != digest:
            raise ValueError("runtime input binding")
    if runtime["fixture"]["source_path"] != "/work/cases/stdin-devnull/inputs/fixture":
        raise ValueError("fixture source path")
    if type(owner["argv"]) is not list or not owner["argv"] or \
       any(type(value) is not str for value in owner["argv"]) or \
       owner["argv"] != [inputs["elf"]["path"],
            "--linux-sealed-infrastructure-v1",
            runtime["request"]["destination_path"],
            runtime["selected_inputs"]["destination_path"],
            str((root / "collection").resolve())]:
        raise ValueError("executed ELF path")
    expected_environment = {"LANG": "C", "LC_ALL": "C", "PATH": "/usr/bin:/bin",
        "M02_SF_NONCE": owner["nonce"], "M02_SF_SOURCE_SHA256": hashes["source_sha256"],
        "M02_SF_GENERATED_SHA256": hashes["generated_sha256"],
        "M02_SF_HEADER_SHA256": hashes["header_sha256"],
        "M02_SF_ELF_SHA256": hashes["elf_sha256"]}
    if owner["environment"] != expected_environment:
        raise ValueError("owner environment")
    captures = owner["captures"]
    if set(captures) != {"stdout", "stderr"}:
        raise ValueError("owner captures")
    for name in captures:
        raw = validate_record(captures[name], root / (name + ".bin"),
                              shown_path=name + ".bin")
        if raw != b"": raise ValueError("owner capture bytes")
    cleanup = owner["cleanup"]
    deadlines = owner["deadlines"]
    deadline_keys = {"owner_start_ns", "ready_deadline_ns",
        "release_send_start_ns", "collection_deadline_ns",
        "first_postfork_receipt_ns", "postfork_deadline_ns",
        "cleanup_trigger_ns", "cleanup_deadline_ns"}
    mandatory_deadlines = {"owner_start_ns", "ready_deadline_ns",
        "cleanup_trigger_ns", "cleanup_deadline_ns"}
    if type(deadlines) is not dict or set(deadlines) != deadline_keys or \
       any(type(deadlines[key]) is not int or deadlines[key] <= 0
           for key in mandatory_deadlines) or any(
           deadlines[key] is not None and (type(deadlines[key]) is not int or
           deadlines[key] <= 0) for key in deadline_keys - mandatory_deadlines) or \
       deadlines["ready_deadline_ns"] != deadlines["owner_start_ns"] + 10000000000 or \
       deadlines["cleanup_deadline_ns"] != deadlines["cleanup_trigger_ns"] + 22000000000:
        raise ValueError("owner deadlines")
    if deadlines["release_send_start_ns"] is None:
        if any(deadlines[key] is not None for key in ("collection_deadline_ns",
                "first_postfork_receipt_ns", "postfork_deadline_ns")):
            raise ValueError("owner release deadline")
    elif deadlines["collection_deadline_ns"] != \
            deadlines["release_send_start_ns"] + 180000000000:
        raise ValueError("owner release deadline")
    if deadlines["first_postfork_receipt_ns"] is None:
        if deadlines["postfork_deadline_ns"] is not None:
            raise ValueError("owner postfork deadline")
    elif deadlines["postfork_deadline_ns"] != min(
            deadlines["collection_deadline_ns"],
            deadlines["first_postfork_receipt_ns"] + 60000000000):
        raise ValueError("owner postfork deadline")
    if deadlines["first_postfork_receipt_ns"] is not None and \
       deadlines["release_send_start_ns"] is not None and \
       deadlines["first_postfork_receipt_ns"] <= deadlines["release_send_start_ns"]:
        raise ValueError("owner postfork receipt")
    validate_cleanup_unresolved(cleanup.get("unresolved") if
                                type(cleanup) is dict else None)
    if set(cleanup) != {"complete", "trigger_kind", "trigger_ns", "cleanup_start_ns",
            "cleanup_deadline_ns", "cleanup_finished_ns", "events", "adopted_reaps",
            "unresolved"} or cleanup["complete"] is not True or \
       cleanup["trigger_kind"] != "normal-eof" or \
       any(type(cleanup[key]) is not int or cleanup[key] <= 0 for key in (
           "trigger_ns", "cleanup_start_ns", "cleanup_deadline_ns",
           "cleanup_finished_ns")) or \
       cleanup["unresolved"] != [] or cleanup["cleanup_deadline_ns"] != \
            cleanup["trigger_ns"] + 22000000000 or not (
            cleanup["trigger_ns"] <= cleanup["cleanup_start_ns"] <=
            cleanup["cleanup_finished_ns"] <= cleanup["cleanup_deadline_ns"]):
        raise ValueError("owner cleanup")
    if cleanup["trigger_ns"] != deadlines["cleanup_trigger_ns"] or \
       cleanup["cleanup_deadline_ns"] != deadlines["cleanup_deadline_ns"] or \
       cleanup["cleanup_finished_ns"] > owner["result_serialized_ns"]:
        raise ValueError("owner cleanup deadline join")
    events = cleanup["events"]
    if len(events) < 4 or events[-3].get("kind") != "owned-scan" or \
       events[-3].get("pids") != [] or events[-2].get("kind") != "owned-scan" or \
       events[-2].get("pids") != [] or events[-1] != {
           "kind": "echild", "monotonic_ns": events[-1].get("monotonic_ns"),
           "return": -1, "errno": 10}:
        raise ValueError("owner cleanup terminal")
    timestamps = []
    known_births = {collector["pid"]: collector["startticks"]}
    signaled_adopted, waited_adopted = [], []
    retired_adopted = set()
    direct_wait_seen = False
    echild_seen = False
    adopted_wait_events = []
    for event_index, event in enumerate(events):
        kind = event.get("kind")
        if echild_seen:
            raise ValueError("owner cleanup terminal order")
        if kind == "identity":
            keys = {"kind", "phase", "observation", "pid", "ppid", "startticks",
                    "matched", "monotonic_ns"}
            if set(event) != keys or not cleanup_phase(event["phase"], suffix=True) or \
                    event["observation"] not in (
                    "observed", "missing", "error") or type(event["matched"]) is not bool or \
                    type(event["pid"]) is not int or event["pid"] <= 0:
                raise ValueError("owner identity event")
            if event["observation"] == "observed":
                if type(event["ppid"]) is not int or event["ppid"] <= 0 or \
                   type(event["startticks"]) is not int or event["startticks"] <= 0:
                    raise ValueError("owner identity event")
            elif event["ppid"] is not None or event["startticks"] is not None or \
                    event["matched"] is not False:
                raise ValueError("owner identity event")
            if event["observation"] == "observed" and event["matched"] is True and \
                    event_index > 0:
                previous = events[event_index - 1]
                if previous.get("kind") == "identity" and \
                   previous.get("observation") == "observed" and \
                   previous.get("matched") is True and \
                   (previous.get("pid"), previous.get("ppid"),
                    previous.get("startticks")) == \
                   (event["pid"], event["ppid"], event["startticks"]):
                    known_births[event["pid"]] = event["startticks"]
        elif kind == "signal":
            if set(event) != {"kind", "pid", "startticks", "signal", "monotonic_ns"} or \
               any(type(event[key]) is not int or event[key] <= 0 for key in
                   ("pid", "startticks", "monotonic_ns")) or \
               type(event["signal"]) is not int or event["signal"] not in (9, 15):
                raise ValueError("owner signal event")
            if event_index < 2:
                raise ValueError("owner signal identity")
            if event["pid"] == collector["pid"] and direct_wait_seen:
                raise ValueError("owner direct signal after wait")
            first, second = events[event_index - 2:event_index]
            expected_prefix = ("term-identity" if event["signal"] == 15 else
                               "kill-identity") if event["pid"] == collector["pid"] \
                else "owned-scan-"
            if event["pid"] == collector["pid"] and \
                    event["startticks"] != collector["startticks"]:
                raise ValueError("owner direct signal identity")
            if any(item.get("kind") != "identity" or
                   item.get("observation") != "observed" or
                   item.get("matched") is not True or item.get("pid") != event["pid"] or
                   item.get("ppid") != owner_id["pid"] or
                   item.get("startticks") != event["startticks"]
                   for item in (first, second)) or \
               (expected_prefix == "owned-scan-" and not (
                    re.fullmatch(r"owned-scan-(\d+)-1", first["phase"]) and
                    second["phase"] == first["phase"][:-1] + "2")) or \
               (expected_prefix != "owned-scan-" and
                    (first["phase"] != expected_prefix + "-1" or
                     second["phase"] != expected_prefix + "-2")):
                raise ValueError("owner signal identity")
            known_births[event["pid"]] = event["startticks"]
            if event["pid"] != collector["pid"]:
                if (event["pid"], event["startticks"]) in retired_adopted:
                    raise ValueError("owner signal after reap")
                if (event["pid"], event["startticks"]) in signaled_adopted:
                    raise ValueError("owner duplicate signal")
                signaled_adopted.append((event["pid"], event["startticks"]))
        elif kind == "wait":
            if set(event) != {"kind", "pid", "startticks", "raw_wait_status",
                              "direct", "monotonic_ns"} or type(event["direct"]) is not bool or \
               type(event["pid"]) is not int or event["pid"] <= 0 or \
               (event["startticks"] is not None and (type(event["startticks"]) is not int or
                    event["startticks"] <= 0)) or \
               type(event["raw_wait_status"]) is not int:
                raise ValueError("owner wait event")
            wait_fields(event["raw_wait_status"])
            if event["direct"] is False and (event["pid"] == collector["pid"] or
                    (event["startticks"] is None and
                    event["pid"] in known_births) or (event["startticks"] is not None and
                    known_births.get(event["pid"]) != event["startticks"])):
                raise ValueError("owner adopted wait identity")
            if event["direct"]:
                if event["pid"] != collector["pid"] or event["startticks"] != \
                        collector["startticks"] or direct_wait_seen:
                    raise ValueError("owner duplicate direct wait")
                direct_wait_seen = True
            else:
                identity = (event["pid"], event["startticks"])
                if identity in retired_adopted:
                    raise ValueError("owner duplicate adopted wait")
                # A null birth is admissible only when no matching birth was
                # ever established; known_births check above enforces that.
                waited_adopted.append(identity)
                adopted_wait_events.append(event)
                retired_adopted.add(identity)
        elif kind == "owned-scan":
            if set(event) != {"kind", "monotonic_ns", "pids"} or type(event["pids"]) is not list:
                raise ValueError("owner scan event")
            for identity in event["pids"]:
                if set(identity) != {"pid", "ppid", "startticks"} or \
                   identity["ppid"] != owner_id["pid"] or any(
                       type(identity[key]) is not int or identity[key] <= 0 for key in identity):
                    raise ValueError("owner scan identity")
                known_births[identity["pid"]] = identity["startticks"]
        elif kind == "echild":
            if set(event) != {"kind", "monotonic_ns", "return", "errno"} or \
               type(event["return"]) is not int or event["return"] != -1 or \
               type(event["errno"]) is not int or event["errno"] != 10:
                raise ValueError("owner echild event")
            echild_seen = True
        else:
            raise ValueError("owner cleanup event kind")
        if type(event["monotonic_ns"]) is not int or not (
                cleanup["cleanup_start_ns"] <= event["monotonic_ns"] <=
                cleanup["cleanup_deadline_ns"]):
            raise ValueError("owner cleanup event time")
        timestamps.append(event["monotonic_ns"])
    if timestamps != sorted(timestamps):
        raise ValueError("owner cleanup event order")
    remaining_waits = waited_adopted[:]
    for identity in signaled_adopted:
        if identity not in remaining_waits:
            raise ValueError("owner adopted signal wait")
        remaining_waits.remove(identity)
    if type(cleanup["adopted_reaps"]) is not list or \
            not exact_equal(cleanup["adopted_reaps"], adopted_wait_events):
        raise ValueError("owner adopted reap join")
    waits = [event for event in events if event.get("kind") == "wait" and
             event.get("direct") is True]
    if len(waits) != 1 or waits[0].get("pid") != collector["pid"] or \
       waits[0].get("startticks") != collector["startticks"] or \
       waits[0].get("raw_wait_status") != expected_wait:
        raise ValueError("owner direct wait")
    if owner["packet_count"] != COUNTS[selector]:
        raise ValueError("owner packet count")
    if owner_errors:
        raise ValueError("owner infrastructure errors")
    return hashes, collector

_MISSING_STATUS = object()

def validate(root, selector, supervisor_raw_wait_status=_MISSING_STATUS):
    if type(supervisor_raw_wait_status) is not int or \
       supervisor_raw_wait_status != 0:
        raise ValueError("supervisor raw wait status")
    if type(selector) is not int or selector not in EXPECTED:
        raise ValueError("selector")
    root = Path(root).resolve()
    expected_wait, phase, report_kind, status, failure, error, count = EXPECTED[selector]
    post = selector in (0, 3, 4, 5)
    supervisor = validate_supervisor(root)
    owner = strict(read(root / "owner-result.json"))
    if (owner.get("owner", {}).get("pid"), owner.get("owner", {}).get("startticks")) != \
            (supervisor["owner_identity"]["pid"],
             supervisor["owner_identity"]["startticks"]):
        raise ValueError("supervisor owner result identity")
    hashes, collector = validate_owner(root, owner, selector, expected_wait)
    nonce = owner.get("nonce")
    if type(nonce) is not str or len(nonce) != 32 or any(
            char not in "0123456789abcdef" for char in nonce):
        raise ValueError("nonce")
    rows = journal(root / "witness.jsonl")
    if not exact_equal(rows[-1]["packet"], owner):
        raise ValueError("owner publication")
    packets = [row["packet"] for row in rows[:-1]]
    validate_packet_order(packets, selector, nonce, hashes, count)
    deadlines = owner["deadlines"]
    packet_rows = rows[:-1]
    if not packet_rows or packet_rows[0]["packet"].get("kind") != "READY" or \
       packet_rows[0]["packet"].get("monotonic_ns", 0) < deadlines["owner_start_ns"] or \
       packet_rows[0]["receipt_monotonic_ns"] > deadlines["ready_deadline_ns"] or \
       deadlines["release_send_start_ns"] is None or \
       deadlines["release_send_start_ns"] < packet_rows[0]["receipt_monotonic_ns"]:
        raise ValueError("owner ready chronology")
    if any(type(row["packet"].get("monotonic_ns")) is not int or
           row["packet"]["monotonic_ns"] > row["receipt_monotonic_ns"]
           for row in packet_rows):
        raise ValueError("witness receipt chronology")
    first_postfork = next((row["receipt_monotonic_ns"] for row in packet_rows
        if row["packet"].get("phase") == "post-fork"), None)
    if first_postfork != deadlines["first_postfork_receipt_ns"]:
        raise ValueError("owner postfork receipt join")
    active_ceiling = deadlines["postfork_deadline_ns"] or \
        deadlines["collection_deadline_ns"]
    if any(row["receipt_monotonic_ns"] > active_ceiling for row in packet_rows[1:]) or \
       deadlines["cleanup_trigger_ns"] < packet_rows[-1]["receipt_monotonic_ns"] or \
       rows[-1]["receipt_monotonic_ns"] < owner["result_serialized_ns"]:
        raise ValueError("owner terminal chronology")
    if any(packet["collector_pid"] != collector["pid"] or
           packet["collector_startticks"] != collector["startticks"] for packet in packets):
        raise ValueError("collector packet identity")
    if any(rows[index]["receipt_monotonic_ns"] >= rows[index + 1]["receipt_monotonic_ns"]
           for index in range(len(rows) - 1)):
        raise ValueError("receipt order")
    collection = root / "collection"
    artifacts = owner["artifacts"]
    if set(artifacts) != {"events", "request", "report"}:
        raise ValueError("owner artifacts")
    artifact_bytes = {}
    for name, filename in (("events", "events.jsonl"), ("request", "request.bin"),
                           ("report", "report.json")):
        artifact_bytes[name] = validate_record(artifacts[name], collection / filename)
    if artifacts["events"]["present"] is (selector == 1) or \
       artifacts["request"]["present"] is (selector == 1) or \
       artifacts["report"]["present"] is (selector == 4):
        raise ValueError("artifact presence")
    events = None if selector == 1 else validate_events(
        artifact_bytes["events"], selector, collector)
    if selector in (0, 3, 4, 5):
        witness_reaps = [packet for packet in packets
                         if packet["kind"] == "REAP"]
        actual_reaps = [event for event in events
                        if event["event"] == "actual-reap"]
        if len(witness_reaps) != 1 or len(actual_reaps) != 1 or \
           (witness_reaps[0]["pid"], witness_reaps[0]["raw_wait_status"]) != \
           (actual_reaps[0]["pid"], actual_reaps[0]["raw_wait_status"]) or \
           wait_fields(witness_reaps[0]["raw_wait_status"])[1:] != (0, None) or \
           wait_fields(actual_reaps[0]["raw_wait_status"])[1:] != (0, None):
            raise ValueError("postfork reap join")
    report_path = collection / "report.json"
    retained_root = root / "retained-inputs"
    setup_raw = None
    if selector in (0, 3, 4, 5):
        setup_raw = read(collection / "setup.bin", 384)
        if len(setup_raw) != 384:
            raise ValueError("setup artifact shape")
        try:
            setup_values = list(struct.unpack("<48Q", setup_raw))
        except struct.error:
            raise ValueError("setup artifact shape")
        setup_packets = [packet for packet in packets if packet["kind"] == "SETUP"]
        if len(setup_packets) != 1:
            raise ValueError("setup witness count")
        setup = setup_packets[0]
        if setup["setup_words"] != setup_values or \
           (setup["leader_pid"], setup["leader_startticks"]) != \
                (witness_reaps[0]["pid"], witness_reaps[0]["startticks"]) or \
           setup_values[:5] != [827081537, 1, 1, 1, 0] or \
           setup_values[5:9] != [setup["leader_pid"], collector["pid"], setup["leader_pid"], setup["leader_pid"]] or \
           setup_values[9:16] != [0, 0, 0, 0, 1, 0, 0o22] or \
           not stat.S_ISDIR(setup["cwd_stat"]["mode"]) or \
           (setup["cwd_stat"]["dev"], setup["cwd_stat"]["ino"]) != \
                (setup_values[16], setup_values[17]) or \
           not stat.S_ISCHR(setup["stdin_stat"]["mode"]) or \
           [setup_values[18], setup_values[19], setup_values[20]] != \
                [setup["stdin_stat"][key] for key in ("mode", "dev", "ino")] or \
           any(not stat.S_ISFIFO(setup[key]["mode"]) for key in
               ("stdout_pipe_stat", "stderr_pipe_stat")) or \
           (setup["stdout_pipe_stat"]["dev"], setup["stdout_pipe_stat"]["ino"]) == \
                (setup["stderr_pipe_stat"]["dev"], setup["stderr_pipe_stat"]["ino"]) or \
           [setup_values[21], setup_values[22], setup_values[23]] != \
                [setup["stdout_pipe_stat"][key] for key in ("mode", "dev", "ino")] or \
           [setup_values[24], setup_values[25], setup_values[26]] != \
                [setup["stderr_pipe_stat"][key] for key in ("mode", "dev", "ino")] or \
           [setup_values[27], setup_values[28]] != \
                [setup["executable_backing"][key] for key in ("dev", "ino")] or \
           not stat.S_ISREG(setup["executable_backing"]["mode"]) or \
           stat.S_IMODE(setup["executable_backing"]["mode"]) != 0o500 or \
           setup["executable_backing"]["size"] != owner["runtime_inputs"]["fixture"]["size"] or \
           setup_values[29] != setup["executable_seals"] or \
           setup["executable_seals"] != COMPLETE_EXECUTABLE_SEALS or \
           setup_values[30:38] != [0, 0, 1, 1, 0, 0, 0, 1] or any(setup_values[38:]):
            raise ValueError("setup witness identity join")
        created = [event for event in events if event["event"] == "child-created"]
        groups = [event for event in events if event["event"] == "owned-group-kill-attempt"]
        if len(created) != 1 or len(groups) != 1 or \
           (created[0]["pid"], created[0]["startticks"]) != \
                (setup["leader_pid"], setup["leader_startticks"]) or \
           (groups[0]["pgid"], groups[0]["leader_startticks"]) != \
                (setup["leader_pid"], setup["leader_startticks"]):
            raise ValueError("setup event birth join")
    if report_kind == "absent":
        if not is_absent_nofollow(report_path):
            raise ValueError("fabricated report")
        # Report absence is a durability fault, not permission to skip the
        # reached-input and child/setup joins.
        if read(collection / "request.bin") != read(retained_root / "request.bin") or \
           read(collection / "selected-inputs.bin") != read(
               retained_root / "selected-inputs.json"):
            raise ValueError("absent report input binding")
        expected_argv, expected_env = decode_request_lists(
            read(collection / "request.bin"))
        if read(collection / "argv.nul") != expected_argv or \
           read(collection / "env.nul") != expected_env:
            raise ValueError("absent report list binding")
        if read(collection / "selected-inputs.bin") != read(retained_root / "selected-inputs.json") or \
           sha(read(collection / "selected-inputs.bin")) != SELECTED_SHA or \
           read(collection / "executable.verified.bin") != read(retained_root / "fixture") or \
           sha(read(collection / "executable.verified.bin")) != FIXTURE_SHA:
            raise ValueError("absent report reached artifact binding")
    else:
        report_raw = artifact_bytes["report"]
        report = strict(report_raw)
        if set(report) != REPORT_KEYS:
            raise ValueError("report fields")
        validate_report_scalars(report)
        if report["preparation_start_ns"] <= 0:
            raise ValueError("report deadlines")
        if report.get("schema_version") != 1 or \
           report.get("kind") != "linux-sealed-infrastructure-collection" or \
           report.get("collector_mode") != "linux-sealed-infrastructure-v1" or \
           report.get("status") != status or report.get("first_failure") != failure or \
           report.get("first_failure_errno") != error or \
           report.get("collector_pid") != collector["pid"] or \
           any(report.get(key) is not False for key in
               ("application_acceptance", "transport_acceptance", "backend_enabled")):
            raise ValueError("report result")
        if report["configured_execution_mechanism"] != \
                "execveat-AT_EMPTY_PATH-sealed-memfd" or \
           report["pathname_execution"] is not False or \
           report["loader_closure_verified"] is not False or \
           report["native_payload"] is not None or \
           report["collector_interruption_signal"] != 0 or \
           any(type(report[key]) is not int or report[key] < 0 for key in (
               "collector_uid", "collector_euid", "first_failure_monotonic_ns",
               "owned_records_omitted")) or type(report["owned_children"]) is not list:
            raise ValueError("report fixed fields")
        # The producer is root for every post-fork report; do not accept a
        # substituted identity merely because it remains non-negative.
        post = selector in (0, 3, 4, 5)
        if post and (report["collector_uid"] != 0 or report["collector_euid"] != 0):
            raise ValueError("report collector identity")
        for child in report["owned_children"]:
            validate_report_process(child)
        validate_report_proc_exe_sample(report["subsequent_proc_exe_link_sample"])
        desired = report["desired"]
        desired_keys = {"role", "request_profile", "uid", "gid", "group",
            "umask", "argc", "envc", "stdin_mode", "case_id_hex",
            "source_selector_hex", "cwd_hex", "stdin_selector_hex",
            "attempt_id_hex", "selected_inputs_sha256"}
        if report["request_valid"]:
            if type(desired) is not dict or set(desired) != desired_keys or \
               any(type(desired[key]) is not int for key in (
                   "role", "request_profile", "uid", "gid", "group", "umask",
                   "argc", "envc", "stdin_mode")) or any(
                   type(desired[key]) is not str for key in desired_keys - {
                       "role", "request_profile", "uid", "gid", "group", "umask",
                       "argc", "envc", "stdin_mode"}):
                raise ValueError("report desired")
            if desired != EXPECTED_DESIRED:
                raise ValueError("report desired binding")
        elif desired is not None:
            raise ValueError("report desired")
        if type(report["setup_words"]) is not list or \
           len(report["setup_words"]) != 48 or any(
               type(value) is not int or value < 0 for value in report["setup_words"]):
            raise ValueError("report setup words")
        validate_report_source(report["executable"])
        validate_report_source(report["stdin"])
        if post:
            backing = setup["executable_backing"]
            sealed = report["executable"]["sealed_backing"]
            observed = report["post_exec_backing"]
            if sealed is None or observed is None or any(
                    backing[key] != sealed[report_key] or
                    sealed[report_key] != observed[report_key]
                    for key, report_key in (("dev", "device"), ("ino", "inode"),
                                            ("mode", "mode"), ("size", "size"))):
                raise ValueError("report executable backing join")
        if report["devnull_identity"] is not None:
            validate_report_stat(report["devnull_identity"])
        if type(report["artifacts"]) is not list or len(report["artifacts"]) != 10:
            raise ValueError("report artifacts")
        for sink in report["artifacts"]:
            validate_sink(sink)
        names = ["request.bin", "selected-inputs.bin", "argv.nul", "env.nul",
            "events.jsonl", "executable.verified.bin", None, "stdout.bin",
            "stderr.bin", "setup.bin"]
        limits = [65537, 4194304, 65536, 65536, 65536, 1048576, None,
                  65536, 65536, 768]
        attempted = {4} if selector == 1 else {0, 4} if selector in (2, 6) \
            else {0, 1, 2, 3, 4, 5, 7, 8, 9}
        for index, sink in enumerate(report["artifacts"]):
            if index not in attempted:
                if sink is not None:
                    raise ValueError("report artifact position")
                continue
            if sink is None or sink["attempted_name"] != names[index] or \
               sink["limit_bytes"] != limits[index]:
                raise ValueError("report artifact position")
            # Every reached artifact is successfully opened except the
            # selector-1 events-create fault, which is checked verbatim below.
            if not sink["created"] and not (selector == 1 and index == 4):
                raise ValueError("report sink creation")
            if sink["created"]:
                raw = read(collection / names[index], limits[index])
                exceptional_request = selector in (2, 6) and index == 0
                if sink["path"] != names[index] or sink["fd_available"] is not True or \
                   sink["creation_errno"] != 0 or sink["fd_errno"] != 0 or \
                   sink["stored_bytes"] != len(raw) or sink["sha256"] != sha(raw) or \
                   (exceptional_request and sink["truncated"] is not False) or \
                   (exceptional_request and sink["io_error"] is not True) or \
                   (not exceptional_request and (sink["truncated"] is not False or
                                                  sink["io_error"] is not False or
                                                  sink["seen_bytes"] != len(raw))):
                    raise ValueError("report artifact binding")
        if post:
            setup_sink = report["artifacts"][9]
            setup_raw = read(collection / "setup.bin", 384)
            if setup_sink is None or setup_sink["limit_bytes"] != 768 or \
               len(setup_raw) != 384 or setup_sink["seen_bytes"] != 384 or \
               setup_sink["stored_bytes"] != 384 or setup_sink["sha256"] != sha(setup_raw):
                raise ValueError("report setup artifact")
            try:
                setup_values = list(struct.unpack("<48Q", setup_raw))
            except (struct.error, ValueError):
                raise ValueError("report setup artifact")
            if report["setup_words"] != setup_values or any(
                    type(value) is not int or not 0 <= value <= (1 << 64) - 1
                    for value in report["setup_words"]):
                raise ValueError("report setup semantics")
        if report["request_valid"]:
            selected_raw = read(collection / "selected-inputs.bin", 1 << 22)
            retained_selected = read(retained_root / "selected-inputs.json", 1 << 22)
            if selected_raw != retained_selected or sha(selected_raw) != SELECTED_SHA or \
               report["artifacts"][1]["sha256"] != SELECTED_SHA or \
               report["artifacts"][1]["seen_bytes"] != len(retained_selected) or \
               report["artifacts"][1]["stored_bytes"] != len(retained_selected):
                raise ValueError("selected inputs binding")
            argv_raw = read(collection / "argv.nul", 65536)
            env_raw = read(collection / "env.nul", 65536)
            expected_argv, expected_env = decode_request_lists(
                read(collection / "request.bin"))
            if argv_raw != expected_argv or env_raw != expected_env or \
               report["artifacts"][2]["sha256"] != sha(argv_raw) or \
               report["artifacts"][3]["sha256"] != sha(env_raw):
                raise ValueError("request list artifact binding")
        if selector == 1:
            events_sink = report["artifacts"][4]
            if events_sink is None or events_sink != {
                    "attempted_name": "events.jsonl", "created": False,
                    "fd_available": False, "creation_errno": 28, "fd_errno": 0,
                    "path": None, "limit_bytes": 65536, "seen_bytes": 0,
                    "stored_bytes": 0, "truncated": False, "io_error": False,
                    "sha256": None}:
                raise ValueError("report events create failure")
        if selector in (2, 6):
            request_sink = report["artifacts"][0]
            if request_sink is None or request_sink["attempted_name"] != "request.bin" or \
               request_sink["seen_bytes"] != 406 or request_sink["stored_bytes"] != 7 or \
               request_sink["truncated"] is not False or request_sink["io_error"] is not True or \
               request_sink["sha256"] != PREFIX_SHA:
                raise ValueError("report request sink")
            if request_sink["creation_errno"] != 0:
                raise ValueError("report request sink creation")
        elif selector in (0, 3, 4, 5):
            # Request creation and the complete raw write are reached before
            # every later selector-specific fault.
            request_sink = report["artifacts"][0]
            if request_sink is None or request_sink != {
                    "attempted_name": "request.bin", "created": True,
                    "fd_available": True, "creation_errno": 0, "fd_errno": 0,
                    "path": "request.bin", "limit_bytes": 65537,
                    "seen_bytes": 406, "stored_bytes": 406,
                    "truncated": False, "io_error": False,
                    "sha256": REQUEST_SHA}:
                raise ValueError("report request sink success")
        for sink in report["artifacts"]:
            if sink is not None and sink["created"] and sink["creation_errno"] != 0:
                raise ValueError("report sink creation")
        if selector not in (2, 6) and any(
                sink is not None and (sink["truncated"] or sink["io_error"])
                for sink in report["artifacts"]):
            raise ValueError("report sink io")
        report_io = [packet for packet in packets if packet.get("site") in (
            "report-flush", "report-sync")]
        if any((packet["kind"] == "BEFORE" and packet["site"] == "report-flush"
                and not 0 <= packet["target_stat"]["size"] <= len(report_raw)) or
               (not (packet["kind"] == "BEFORE" and
                     packet["site"] == "report-flush") and
                packet["target_stat"]["size"] != len(report_raw))
               for packet in report_io):
            raise ValueError("report witness size")
        if report.get("child_created") is not post or report.get("request_valid") is not (
                selector not in (1, 2, 6)) or report.get("cleanup_complete") is not post or \
           report.get("streams") != {"stdout_eof": post, "stderr_eof": post,
                                     "setup_eof": post}:
            raise ValueError("report lifecycle")
        if post:
            child = report.get("linux_child")
            validate_report_process(child)
            created = [event for event in events if event["event"] == "child-created"]
            if len(created) != 1 or (created[0]["pid"], created[0]["startticks"]) != \
                    (child["pid"], child["startticks"]):
                raise ValueError("report child cleanup")
            reap = next(packet for packet in packets if packet["kind"] == "REAP")
            final = next(packet for packet in packets if packet["kind"] == "CLEANUP_FINAL")
            if (child["pid"], child["startticks"], child["raw_wait_status"]) != \
                    (reap["pid"], reap["startticks"], reap["raw_wait_status"]) or \
               wait_fields(child["raw_wait_status"])[1:] != (0, None) or \
               child["wait"] != {
                    "exited": True, "signaled": False, "exit_code": 0,
                    "signal": None, "core_dumped": False} or \
               (report["cleanup_start_ns"], report["cleanup_deadline_ns"],
                report["cleanup_finished_ns"], report["cleanup_complete"],
                report["group_identity_pinned"], report["owned_records_omitted"]) != \
               (final["cleanup_start_ns"], final["cleanup_deadline_ns"],
                final["cleanup_finished_ns"], final["cleanup_complete"],
                final["group_pinned"], final["owned_records_omitted"]):
               raise ValueError("report child cleanup")
            group_events = [event for event in events if event["event"] == "owned-group-kill-attempt"]
            if len(group_events) != 1 or (group_events[0]["pgid"],
                    group_events[0]["leader_startticks"]) != (child["pid"], child["startticks"]):
                raise ValueError("report child birth join")
            if len(report["owned_children"]) != final["owned_count"] or \
               child["ppid"] != collector["pid"]:
                raise ValueError("report child cleanup")
            if child["kill_sent"] is not False:
                raise ValueError("report child cleanup")
            reaps = [event for event in events if event["event"] == "actual-reap"]
            if len(reaps) != 1 or (reaps[0]["pid"], reaps[0]["raw_wait_status"]) != \
                    (child["pid"], child["raw_wait_status"]):
                raise ValueError("report event reap")
            words = report["setup_words"]
            if report["setup_ready_record"] is not True or \
               report["setup_error_record"] is not False or \
               report["setup_validated"] is not True or words[:5] != \
                    [827081537, 1, 1, 1, 0] or \
               words[5:9] != [child["pid"], collector["pid"],
                              child["pid"], child["pid"]] or \
               words[9:15] != [0, 0, 0, 0, 1, 0] or words[15] != 0o22 or \
               words[18:21] != [report["devnull_identity"][key]
                                 for key in ("mode", "device", "inode")] or \
               words[21:27] != [setup["stdout_pipe_stat"][key] for key in ("mode", "dev", "ino")] + \
                              [setup["stderr_pipe_stat"][key] for key in ("mode", "dev", "ino")] or \
               words[27:30] != [report["post_exec_backing"][key]
                                 for key in ("device", "inode")] + [
                                     report["executable"]["seals"]] or \
               report["executable"]["seals"] != COMPLETE_EXECUTABLE_SEALS or \
               words[30:38] != [0, 0, 1, 1, 0, 0, 0, 1] or any(words[38:]):
                raise ValueError("report setup semantics")
            if report["post_exec_backing_observed"] is not True or not (
                    report["preparation_start_ns"] <= report["process_start_ns"] <=
                    report["post_exec_observed_monotonic_ns"] <=
                    report["completion_observed_ns"] <= report["cleanup_start_ns"] <=
                    report["cleanup_finished_ns"] <= events[-1]["monotonic_ns"]):
                raise ValueError("report lifecycle time")
            sample = report["subsequent_proc_exe_link_sample"]
            if sample is not None and not (
                    report["post_exec_observed_monotonic_ns"] <=
                    sample["observed_monotonic_ns"] <=
                    report["completion_observed_ns"]):
                raise ValueError("report proc exe sample")
            executable = report["executable"]
            for key in ("source_before", "source_after"):
                source_mode = executable[key]["mode"]
                if not stat.S_ISREG(source_mode) or not source_mode & 0o111 or \
                   source_mode & (stat.S_ISUID | stat.S_ISGID):
                    raise ValueError("report source mode")
            runtime_fixture_size = owner["runtime_inputs"]["fixture"]["size"]
            retained_executable = read(retained_root / "fixture")
            if executable["opened"] is not True or executable["stable"] is not True or \
               executable["verified"] is not True or \
               executable["source_before"] != executable["source_after"] or \
               executable["source_before"]["size"] != runtime_fixture_size or \
               executable["source_after"]["size"] != runtime_fixture_size or \
               executable["source_before"]["size"] != len(retained_executable) or \
               executable["source_after"]["size"] != len(retained_executable) or \
               executable["sealed_backing"] != report["post_exec_backing"] or \
               executable["artifact"] is None or \
               executable["artifact"]["sha256"] != FIXTURE_SHA or \
               executable["artifact"]["seen_bytes"] != 27448 or \
               executable["artifact"]["stored_bytes"] != 27448 or \
               executable["artifact"] != report["artifacts"][5] or \
               not stat.S_ISCHR(report["devnull_identity"]["mode"]):
                raise ValueError("report executable semantics")
        elif report.get("linux_child") is not None or report["owned_children"] or \
             report["subsequent_proc_exe_link_sample"] is not None or \
             report["process_start_ns"] != 0 or report["process_deadline_ns"] != 0 or \
             report["completion_observed_ns"] != 0 or report["group_identity_pinned"] is not False or \
             report["owned_records_omitted"] != 0 or any(report.get(key) != 0 for key in
                ("cleanup_start_ns", "cleanup_deadline_ns", "cleanup_finished_ns")):
            raise ValueError("report prefork cleanup")
        else:
            if any(report[key] is not False for key in ("setup_ready_record",
                    "setup_error_record", "setup_validated",
                    "post_exec_backing_observed")) or any(report["setup_words"]) or \
               report["post_exec_observed_monotonic_ns"] != 0 or \
               report["post_exec_backing"] is not None:
                raise ValueError("report prefork setup")
        if report["preparation_deadline_ns"] != report["preparation_start_ns"] + \
                120000000000 or (post and report["process_deadline_ns"] !=
                report["process_start_ns"] + 10000000000):
            raise ValueError("report deadlines")
        failure_ns = report["first_failure_monotonic_ns"]
        if (failure == "none") is not (failure_ns == 0):
            raise ValueError("report failure time")
        if failure != "none":
            finish_ns = events[-1]["monotonic_ns"] if events else None
            if failure_ns <= report["preparation_start_ns"] or \
               (selector == 3 and (failure_ns <= finish_ns or
                                   failure_ns <= report["cleanup_finished_ns"])) or \
               (selector in (2, 6) and failure_ns >= finish_ns):
                raise ValueError("report failure time")
        # collector.c exits before source preparation for these selectors.
        absent_source = {
            "opened": False, "stable": False, "verified": False,
            "source_before": None, "source_after": None,
            "sealed_backing": None, "requested_memfd_flags": 3,
            "seals": 0, "artifact": None}
        if selector in (1, 2, 6):
            if report["executable"] != absent_source or \
               report["stdin"] != absent_source or \
               report["devnull_identity"] is not None:
                raise ValueError("report prefork source state")
        else:
            # All fixtures request DEVNULL, so stdin is never a sealed source.
            if report["stdin"] != absent_source or \
               report["devnull_identity"] is None or not stat.S_ISCHR(
                   report["devnull_identity"]["mode"]):
                raise ValueError("report devnull source state")
    if post and (read(collection / "stdout.bin") != POSTFORK_STDOUT or
                 len(read(collection / "stdout.bin")) != 8 or
                 sha(read(collection / "stdout.bin")) != POSTFORK_STDOUT_SHA or
                 read(collection / "stderr.bin") != b""):
        raise ValueError("postfork output binding")
    if sha(read(retained_root / "request.bin")) != REQUEST_SHA or \
       sha(read(retained_root / "selected-inputs.json")) != SELECTED_SHA or \
       sha(read(retained_root / "fixture")) != FIXTURE_SHA:
        raise ValueError("retained input")
    if selector == 1:
        if not is_absent_nofollow(collection / "request.bin") or \
           not is_absent_nofollow(collection / "events.jsonl"):
            raise ValueError("prefork artifact absence")
        return True
    request = read(collection / "request.bin")
    if selector in (2, 6):
        if request != PREFIX or sha(request) != PREFIX_SHA:
            raise ValueError("request prefix")
    elif sha(request) != REQUEST_SHA:
        raise ValueError("request artifact")
    if selector in (5, 6):
        sync = [packet for packet in packets if packet.get("site") == "report-sync"]
        if len(sync) != 2 or sync[-1].get("return") != -1 or \
           sync[-1].get("errno") != 5:
            raise ValueError("report sync failure")
    return True
