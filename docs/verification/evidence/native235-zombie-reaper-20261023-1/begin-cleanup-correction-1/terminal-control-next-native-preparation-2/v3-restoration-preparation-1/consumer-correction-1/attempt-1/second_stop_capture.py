"""Add only the second public-stop/release protocol to the frozen case oracle.

Source-only candidate. Offline protocol acceptance never proves native execution,
complete mapping/callback/ref/frame restoration or cycle quota.
"""
import hashlib
import importlib.util
import json
from pathlib import Path

CONSUMERS = {
    "workload": ("/home/holden/mckernel-work/host-preparation/p-m05-v3-matched-first-restoration-binding-20261023-1/sdk5-successor-1/consumer-correction-1/reboot_workload_capture.py", "beb97531b8828dfa9cb0fd51c4d0924824a61239a23f3e72813ae8eb7f4fd3e0"),
    "lifecycle": ("/home/holden/mckernel/scripts/application-tests/native_diagnostic_lifecycle_capture.py", "0585f78b80e603c010316418ce307794d59e1d92581b845ec6b2e74e22c8954b"),
    "transport": ("/home/holden/mckernel-work/scratch/native-resource-release-collector-20261017-1/transport-correction1/resource_capture.py", "e66e014f4b67854f05457770a42250fb5e0929e0da304bdbc2b7366b6bde9240"),
    "resource": ("/home/holden/mckernel/scripts/application-tests/native_resource_release_capture.py", "9c628074de9ae897e82f15c2f4438d2558c2a10fde6a0d5a288b8964eddfcc76"),
}
NAMES = {
    "ND_SECOND_LIFECYCLE": "ND_LIFECYCLE",
    "ND_SECOND_LIFECYCLE_STREAM": "ND_LIFECYCLE_STREAM",
    "ND_SECOND_RESOURCE": "ND_RESOURCE",
    "ND_SECOND_RESOURCE_STREAM": "ND_RESOURCE_STREAM",
    "ND_SECOND_RESOURCE_CHUNK": "ND_RESOURCE_CHUNK",
}
FAMILIES = ("ND_SECOND_LIFECYCLE", "ND_SECOND_RESOURCE")


def need(ok, reason):
    if not ok:
        raise ValueError(reason)


def bound(name):
    path, digest = CONSUMERS[name]
    need(hashlib.sha256(Path(path).read_bytes()).hexdigest() == digest,
         "frozen consumer changed: " + name)
    spec = importlib.util.spec_from_file_location("second_stop_" + name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def pairs(items):
    result = {}
    for key, value in items:
        need(key not in result, "duplicate JSON key")
        result[key] = value
    return result


def invalid_constant(_):
    raise ValueError("nonfinite JSON number")


def record(line):
    need(line.endswith("\n") and len(line.encode("utf-8")) <= 4096,
         "complete bounded second protocol record")
    wire = line[:-1]
    if wire.endswith("\r"):
        wire = wire[:-1]
    need("\r" not in wire, "one terminal CR only")
    prefix, separator, body = wire.partition(" ")
    need(bool(separator), "record separator")
    try:
        value = json.loads(body, object_pairs_hook=pairs,
                           parse_constant=invalid_constant)
    except (ValueError, RecursionError) as error:
        raise ValueError("invalid record JSON") from error
    need(type(value) is dict, "object record required")
    return prefix, value


def integer(value):
    need(type(value) is int and 0 < value < 2**64,
         "positive integer nanosecond timestamp")
    return value


def validate_second_protocol(serial, second_workload):
    """Exact new body; caller supplies independently validated second workload.

    This entry point is also used by the finite actual producer-body comparison.
    It cannot substitute for full evaluate's unchanged original obligations.
    """
    need(type(serial) is str and len(serial.encode("utf-8")) <= 4 * 1024 * 1024,
         "bounded serial text")
    lines = serial.splitlines(keepends=True)
    second = []
    for index, line in enumerate(lines):
        if any(family in line for family in FAMILIES):
            need(line.startswith(FAMILIES), "column-zero second records only")
            prefix, value = record(line)
            need(prefix in NAMES, "unknown second lifecycle/resource namespace")
            # Change only the validated column-zero prefix. Keep separator,
            # original JSON bytes, terminal CR and LF byte-for-byte.
            view_line = NAMES[prefix] + line[len(prefix):]
            second.append((index, prefix, value, view_line))
    lifecycle = [row for row in second if row[1].startswith("ND_SECOND_LIFECYCLE")]
    resource = [row for row in second if row[1].startswith("ND_SECOND_RESOURCE")]
    need(lifecycle and resource, "both second lifecycle and resource required")
    life_headers = [row for row in lifecycle if row[1] == "ND_SECOND_LIFECYCLE"]
    resource_headers = [row for row in resource if row[1] == "ND_SECOND_RESOURCE"]
    need(len(life_headers) == len(resource_headers) == 1, "unique second headers")
    payload = [(index, line) for index, line in enumerate(lines)
               if line.startswith("ND_PAYLOAD ")]
    workload = [index for index, line in enumerate(lines)
                if line.startswith("ND_SECOND_PAYLOAD ")]
    reboot = [index for index, line in enumerate(lines)
              if line.startswith("ND_REBOOT")]
    need(len(payload) == len(workload) == 1 and reboot,
         "original publication anchors required")
    final_index, final_line = payload[0]
    need(max(reboot) < workload[0] < lifecycle[0][0]
         and lifecycle[-1][0] < resource[0][0]
         and resource[-1][0] < final_index,
         "reboot/workload/second-stop/second-release/final publication order")
    life_view = "".join(row[3] for row in lifecycle) + final_line
    resource_view = "".join(row[3] for row in resource) + final_line
    life_result = bound("lifecycle").validate_lifecycle_capture(life_view)
    stdout, stderr, status = bound("transport").decode(resource_view)
    release_result = bound("resource").evaluate(stdout, stderr, status)
    life_header = life_headers[0][2]
    resource_header = resource_headers[0][2]
    _, final = record(final_line)
    finished = integer(second_workload["finished_ns"])
    ls, lr, lf = [integer(life_header[key]) for key in
                  ("started_ns", "reaped_ns", "finished_ns")]
    rs, rr, rf = [integer(resource_header[key]) for key in
                  ("started_ns", "reaped_ns", "finished_ns")]
    need(finished < ls <= lr <= lf < rs <= rr <= rf <= integer(final["finished_ns"]),
         "second workload/stop/release completion nanosecond order")
    return dict(second_stop_verified=True, second_public_release_verified=True,
                second_lifecycle_protocol=life_result,
                second_public_release_protocol=release_result,
                native_execution_verified=False,
                complete_restoration_verified=False, quota_credit=False)


def evaluate(manifest, observation):
    # Full original byte/audit/boot/workload/QMP/retirement checks run first,
    # on the unmodified complete observation, before the additive body.
    original = bound("workload").evaluate(manifest, observation)
    second = validate_second_protocol(observation["serial"], original["second_workload"])
    return dict(original, **second)
