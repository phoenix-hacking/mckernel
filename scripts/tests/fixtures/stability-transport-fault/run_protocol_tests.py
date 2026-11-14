#!/usr/bin/env python3
"""Pinned-container-only controller infrastructure suite; no application credit.

Root supplies an independently retained pinned build of protocol_harness.c.
This helper runs only that ordinary fake-process harness, once per fresh case.
It stops at the first unexpected result and preserves every complete attempt.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import stat
import sys
import time

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]


def require(condition, message):
    if not condition:
        raise ValueError(message)


def read_bytes(path, limit):
    fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW)
    try:
        info = os.fstat(fd)
        require(stat.S_ISREG(info.st_mode) and info.st_size <= limit, "nonregular or oversized artifact: " + str(path))
        chunks, size = [], 0
        while True:
            data = os.read(fd, min(65536, limit + 1 - size))
            if not data:
                break
            size += len(data)
            require(size <= limit, "artifact grew beyond bound")
            chunks.append(data)
        after = os.fstat(fd)
        require((info.st_size, info.st_mtime_ns, info.st_ctime_ns) == (after.st_size, after.st_mtime_ns, after.st_ctime_ns), "artifact changed while reading")
        return b"".join(chunks)
    finally:
        os.close(fd)


def identity(path, limit=95 * 1024 * 1024 - 1):
    raw = read_bytes(path, limit)
    return {"path": str(path), "size": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def read_json(path):
    def pairs(items):
        value = {}
        for key, item in items:
            require(key not in value, "duplicate JSON key")
            value[key] = item
        return value
    return json.loads(read_bytes(path, 65536), object_pairs_hook=pairs,
                      parse_constant=lambda value: (_ for _ in ()).throw(ValueError("nonfinite JSON")))


def exact(actual, expected, label):
    require(type(actual) is type(expected) and actual == expected, label + " differs")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--harness", required=True, type=Path)
    parser.add_argument("--attempt-root", required=True, type=Path)
    parser.add_argument("--case", action="append", default=[])
    args = parser.parse_args()
    require(Path("/.dockerenv").is_file(), "run only inside the already-authorized pinned container wrapper")
    require(args.harness.is_absolute() and args.attempt_root.is_absolute(), "absolute paths required")
    manifest = read_json(HERE / "protocol-expectations.json")
    require(identity(HERE / "controller.c")["sha256"] == manifest["controller_sha256"], "frozen controller changed")
    cases = {row["name"]: row for row in manifest["cases"]}
    requested = args.case or list(cases)
    require(len(requested) == len(set(requested)) and all(name in cases for name in requested), "unknown/duplicate selected harness case")
    args.attempt_root.mkdir(mode=0o700)
    captured = args.attempt_root / "inputs"
    captured.mkdir(mode=0o700)
    inputs = []
    paths = [HERE / name for name in ("controller.c", "protocol_harness.c", "protocol-expectations.json", "run_protocol_tests.py")]
    supervisor_path = REPO / "scripts/application-tests/supervisor.py"
    paths += [supervisor_path, args.harness]
    for index, path in enumerate(paths):
        item = identity(path)
        copy = captured / (str(index) + "-" + path.name)
        shutil.copyfile(path, copy)
        require(identity(copy)["sha256"] == item["sha256"], "input changed during retention")
        item["retained"] = str(copy)
        inputs.append(item)
    invocation = {"schema_version": 1, "argv": sys.argv, "inputs": inputs,
                  "cases": requested, "case_timeout_seconds": 65, "cleanup_timeout_seconds": 15,
                  "suite_timeout_seconds": 150, "scope": "controller-protocol-infrastructure-only",
                  "isolation_authority": "external original pinned container wrapper; dockerenv alone is not resource/provenance evidence",
                  "application_acceptance": False, "transport_acceptance": False, "production_gate_credit": False}
    with (args.attempt_root / "invocation.json").open("x") as stream:
        json.dump(invocation, stream, indent=2); stream.write("\n")
    spec = importlib.util.spec_from_file_location("stability_protocol_supervisor", supervisor_path)
    require(spec is not None and spec.loader is not None, "supervisor import unavailable")
    supervisor = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = supervisor
    spec.loader.exec_module(supervisor)
    results = []
    started = time.monotonic()
    failure = None
    for name in requested:
        try:
            remaining = 150 - (time.monotonic() - started)
            require(remaining >= 65, "insufficient suite budget for another full bounded attempt")
            attempt = args.attempt_root / name
            attempt.mkdir(mode=0o700)
            report = supervisor.run_supervised([str(args.harness), name, str(attempt / "fixture")],
                cwd=str(attempt), env={"LANG": "C", "LC_ALL": "C", "TZ": "UTC", "PATH": "/usr/bin:/bin"},
                attempt_dir=str(attempt / "supervision"), timeout_seconds=65,
                cleanup_timeout_seconds=15, stdout_limit_bytes=65536, stderr_limit_bytes=65536)
            exact(report["status"], "COMPLETED", "supervisor collection")
            exact(report["raw_wait_status"], 0, "harness actual raw exit")
            exact(report["cleanup_complete"], True, "supervisor owned cleanup")
            exact(report["executable"]["sha256"], inputs[-1]["sha256"], "executed harness identity")
            exact(report["executable"]["size"], inputs[-1]["size"], "executed harness size")
            observed = read_json(attempt / "fixture/harness-result.json")
            peer = read_json(attempt / "fixture/peer-report.json")
            row = cases[name]
            expected = {**manifest["emergency_defaults" if row.get("emergency") else "normal_defaults"], **row}
            exact(observed["scope"], manifest["scope"], "harness scope")
            exact(observed["status"], "PASS", "harness assertions")
            exact(observed["case"], name, "case identity")
            for field in ("application_acceptance", "transport_acceptance"):
                exact(observed[field], False, field)
            for field in ("pre_input_accepted", "controller_failed", "emergency_attempted", "emergency_confirmed", "ack_count"):
                exact(observed[field], expected[field], field)
            exact(observed["controller_first_failure"], expected["first_failure"], "first failure")
            exact(observed["controller_first_failure_phase"], "POST_RET" if row.get("emergency") else "PRE_INPUT" if expected["controller_failed"] else "none", "first failing phase")
            require(type(observed["input_begin_ns"]) is int and (observed["input_begin_ns"] > 0) == expected["input_delivered"], "input release differs")
            require(type(observed["uart_rejections"]) is int and observed["uart_rejections"] >= expected["uart_rejections_min"], "invalid frame rejection missing")
            for field in ("launcher_raw_wait", "peer_raw_wait", "cleanup_complete"):
                exact(observed[field], manifest["common"][field], field)
            for output, field in (("fake.stdout.bin", "emergency_fake_stdout_hex" if row.get("emergency") else "normal_fake_stdout_hex"), ("fake.stderr.bin", "fake_stderr_hex")):
                exact(read_bytes(attempt / "fixture" / output, 65536), bytes.fromhex(manifest["common"][field]), "independent " + output)
            for field in ("requests_matched", "fake_child_live_before_response"):
                exact(peer[field], True, "peer " + field)
            exact(peer["emergency_ack_sent"], bool(row.get("emergency")) and name != "emergency-missing", "peer ACK witness")
            for field, actual in (("normal_elapsed_min_ns", "normal_capture_elapsed_ns"), ("emergency_elapsed_min_ns", "emergency_elapsed_ns")):
                if field in expected:
                    require(type(observed[actual]) is int and observed[actual] >= expected[field], "real monotonic lower bound differs")
            results.append({"case": name, "status": "PASS", "report": identity(attempt / "fixture/harness-result.json"), "peer": identity(attempt / "fixture/peer-report.json")})
            print("PROTOCOL_INFRASTRUCTURE_CASE " + name + " PASS", flush=True)
        except (ValueError, OSError, KeyError, TypeError) as error:
            failure = {"case": name, "error": str(error)}
            print("PROTOCOL_INFRASTRUCTURE_FIRST_FAILURE " + json.dumps(failure), flush=True)
            break
    result = {**invocation, "status": "FAIL" if failure else "PASS", "results": results, "first_failure": failure,
              "elapsed_seconds": time.monotonic() - started}
    with (args.attempt_root / "result.json").open("x") as stream:
        json.dump(result, stream, indent=2); stream.write("\n")
    return 1 if failure else 0


if __name__ == "__main__":
    raise SystemExit(main())
