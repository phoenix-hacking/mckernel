"""One case's transport join; every native/cycle acceptance decision is external."""
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sys


def _bound(name, path, pin):
    path = Path(path)
    if hashlib.sha256(path.read_bytes()).hexdigest() != pin:
        raise ValueError("frozen consumer source changed")
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def evaluate(serial):
    def need(ok, message):
        if not ok:
            raise ValueError(message)

    def pairs(items):
        obj = {}
        for name, value in items:
            need(name not in obj, "duplicate JSON key")
            obj[name] = value
        return obj

    need(type(serial) is str and len(serial.encode("utf-8")) <= 4 * 1024 * 1024,
         "bounded serial text")
    resource_decoder = _bound("cycle_resource_transport",
        "/home/holden/mckernel-work/scratch/native-resource-release-collector-20261017-1/transport-correction1/resource_capture.py",
        "e66e014f4b67854f05457770a42250fb5e0929e0da304bdbc2b7366b6bde9240")
    release = _bound("native_resource_release_capture",
        "/home/holden/mckernel/scripts/application-tests/native_resource_release_capture.py",
        "9c628074de9ae897e82f15c2f4438d2558c2a10fde6a0d5a288b8964eddfcc76")
    consumer = _bound("cycle_reference",
        "/home/holden/mckernel-work/host-preparation/native-second-stop-case-preparation-20261021-1/current053d-normalization-runtime-preparation-1/runtime-source-1/native_resource_reboot_sequence.py",
        "312bb2d53042f97a74a0e31cb97231d6e483e331dead825b19afddd17ab16d0c")
    diagnostic = _bound("cycle_unchanged_diagnostic",
        "/home/holden/mckernel/scripts/application-tests/native_diagnostic.py",
        "1b43934aacf63f21082448a99dd7237759387411200ced997aa2a16700505e5e")
    resource_stdout, resource_stderr, resource_status = resource_decoder.decode(serial)
    release.evaluate(resource_stdout, resource_stderr, resource_status)
    rows = []
    payloads = 0
    resource_finished = None
    reboot_seen = False
    for line in serial.splitlines(keepends=True):
        if line.startswith("ND_RESOURCE"):
            need(not reboot_seen, "resource capture precedes second boot capture")
        if line.startswith("ND_RESOURCE "):
            resource_finished = json.loads(line[len("ND_RESOURCE "):])["finished_ns"]
        if line.startswith("ND_PAYLOAD "):
            payloads += 1
            need(payloads == 1 and reboot_seen, "one payload follows complete cycle")
        if not line.startswith("ND_REBOOT"):
            continue
        reboot_seen = True
        need(payloads == 0 and line.endswith("\n") and len(line) <= 4097,
             "bounded ordered complete reboot record")
        wire = line[:-1]
        if wire.endswith("\r"):
            wire = wire[:-1]
        need("\r" not in wire and len(wire) <= 4095, "only terminal transport CR")
        prefix, raw = wire.split(" ", 1)
        value = json.loads(raw, object_pairs_hook=pairs,
                           parse_constant=lambda _: need(False, "nonfinite JSON"))
        need(type(value) is dict, "object required")
        rows.append((prefix, value))
    need(payloads == 1 and bool(rows) and rows[0][0] == "ND_REBOOT", "reboot header")
    header = rows.pop(0)[1]
    fields = {"argv", "result", "boot_attempted", "helper_result", "raw_wait_status",
              "fault", "timeout", "clean", "child_stage", "child_errno",
              "resource_finished_ns", "started_ns", "reaped_ns", "finished_ns"}
    need(set(header) == fields and header["argv"] == ["/bin/native-boot-second"], "header fields")
    for field in fields - {"argv"}:
        need(type(header[field]) is int and 0 <= header[field] < 2**64, "integer metadata")
    for field in ("result", "helper_result", "raw_wait_status", "fault", "timeout", "child_stage", "child_errno"):
        need(header[field] == 0, "second boot capture failure")
    need(header["boot_attempted"] == header["clean"] == 1 and
         header["resource_finished_ns"] == resource_finished and
         0 < resource_finished < header["started_ns"] <= header["reaped_ns"] <= header["finished_ns"],
         "sequence retirement/order")

    def body(name, size):
        out = bytearray()
        while len(out) < size:
            need(bool(rows), "missing chunk")
            prefix, value = rows.pop(0)
            need(prefix == "ND_REBOOT_CHUNK" and set(value) == {"name", "offset", "hex"}, "chunk fields")
            need(value["name"] == name and type(value["offset"]) is int and
                 value["offset"] == len(out) and type(value["hex"]) is str and
                 re.fullmatch(r"(?:[0-9a-f]{2}){1,512}", value["hex"]) is not None,
                 "ordered bounded chunk")
            raw = bytes.fromhex(value["hex"])
            need(len(raw) == min(512, size-len(out)), "exact chunk size")
            out.extend(raw)
        return bytes(out)

    streams = {}
    for name in ("stdout", "stderr"):
        need(bool(rows), "missing boot stream")
        prefix, value = rows.pop(0)
        need(prefix == "ND_REBOOT_STREAM" and set(value) ==
             {"name", "eof", "observed", "retained", "discarded", "limit", "eof_ns"}, "stream fields")
        need(value["name"] == name and value["eof"] is True, "complete boot stream")
        for key in ("observed", "retained", "discarded", "limit", "eof_ns"):
            need(type(value[key]) is int and 0 <= value[key] < 2**64, "integer stream metadata")
        need(value["observed"] == value["retained"] <= 1024 and value["discarded"] == 0 and
             value["limit"] == 1024 and header["started_ns"] <= value["eof_ns"] <= header["finished_ns"],
             "complete boot accounting")
        streams[name] = body(name, value["retained"])
    snapshots = {}
    for name in ("before", "after"):
        need(bool(rows), "missing kernel snapshot")
        prefix, value = rows.pop(0)
        need(prefix == "ND_REBOOT_LOG" and set(value) == {"name", "count", "errno", "limit"}, "snapshot fields")
        need(value["name"] == name and all(type(value[x]) is int for x in ("count", "errno", "limit")) and
             value["errno"] == 0 and value["limit"] == 262144 and 0 <= value["count"] < 262144,
             "complete bounded snapshot")
        snapshots[name] = body(name, value["count"])
        need(not diagnostic.BAD_MARKERS.search(snapshots[name].decode("latin1")), "kernel failure marker")
    need(not rows, "extra reboot records")
    marker = consumer.second_boot_status(snapshots["before"], snapshots["after"])
    result = consumer.evaluate(resource_stdout, resource_stderr, resource_status,
        streams["stdout"], streams["stderr"], header["raw_wait_status"], marker,
        resource_finished, header["started_ns"], header["finished_ns"])
    return dict(result, snapshot_sha256={k: hashlib.sha256(v).hexdigest() for k,v in snapshots.items()},
                snapshot_bytes={k: len(v) for k,v in snapshots.items()},
                second_boot_resources_retained=True, second_stop_verified=False)
