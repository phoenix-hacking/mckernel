#!/usr/bin/env python3
"""Root-owned isolated infrastructure only. No compilation or catalog execution.

Use an external pinned container and independent whole-driver watchdog. All
attempts, including the first failed assertion, remain under the fresh root.
The request encoder below uses the literal published wire offsets and does not
import the C decoder or collector. Expected streams/waits are separate literals.
"""
import argparse
import errno
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import signal
import stat
import struct
import sys
import time
import traceback


CASES = (
    "literal", "empty-env", "stdin-devnull", "pressure", "signal-term",
    "exit143", "stdout-over", "stderr-over", "pipe-holder", "escaped-holder",
    "timeout", "interrupt-collector", "replace-source", "bad-executable-hash",
    "bad-stdin-hash", "bad-manifest-hash", "role-two", "unknown-mode",
    "malformed-request", "request-fifo", "executable-symlink", "stdin-fifo",
    "missing-executable", "script-executable", "existing-attempt",
)
EXPECTED_FAILURES = {
    "bad-executable-hash": ("source-size-or-sha256", errno.EBADMSG),
    "bad-stdin-hash": ("source-size-or-sha256", errno.EBADMSG),
    "bad-manifest-hash": ("manifest-sha256", errno.EBADMSG),
    "role-two": ("unsupported-role-or-profile", errno.EOPNOTSUPP),
    "unknown-mode": ("unsupported-collector-mode", errno.EOPNOTSUPP),
    "malformed-request": ("request-decode", errno.EINVAL),
    "request-fifo": ("input-not-regular", errno.EINVAL),
    "executable-symlink": ("source-open", errno.ELOOP),
    "stdin-fifo": ("source-not-regular", errno.EINVAL),
    "missing-executable": ("source-open", errno.ENOENT),
    "script-executable": ("unsupported-executable-format", errno.ENOEXEC),
    "builder-identity": ("root-infrastructure-identity-required", errno.EPERM),
    "stdout-over": ("stream-bound", errno.EFBIG),
    "stderr-over": ("stream-bound", errno.EFBIG),
    "pipe-holder": ("surviving-owned-descendant", errno.ECHILD),
    "escaped-holder": ("surviving-owned-descendant", errno.ECHILD),
    "timeout": ("process-deadline", errno.ETIMEDOUT),
    "interrupt-collector": ("collector-interrupted", errno.EINTR),
}


def identity(path):
    raw = path.read_bytes()
    return {"path": str(path), "size_bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def save(path, value):
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())


def plain_file(path, maximum):
    if not path.is_absolute() or path.resolve(strict=True) != path or path.is_symlink():
        raise ValueError("input must be an absolute canonical nonsymlink file")
    info = path.stat()
    if not stat.S_ISREG(info.st_mode) or info.st_size > maximum:
        raise ValueError("input file type or size")
    return path.read_bytes()


def request_wire(executable, cwd, stdin, args, environment, manifest, executable_bytes,
                 stdin_bytes, attempt_id, role=1):
    """Independent literal ACRQ0001 LE encoding; no normalization or inheritance."""
    header = bytearray(256)
    header[0:8] = b"ACRQ0001"
    values = {8: 1, 12: 256, 20: 0, 24: role, 28: 1, 32: 0, 36: 0, 40: 1,
              44: 0, 48: 18, 52: len(args), 56: len(environment),
              60: int(stdin is not None), 64: 1, 68: 1, 72: 10000, 76: 15000,
              80: 65536, 84: 65536}
    for offset, value in values.items():
        struct.pack_into("<I", header, offset, value)
    struct.pack_into("<Q", header, 88, len(executable_bytes))
    struct.pack_into("<Q", header, 96, len(stdin_bytes) if stdin is not None else 0)
    header[104:136] = hashlib.sha256(manifest).digest()
    header[136:168] = hashlib.sha256(executable_bytes).digest()
    header[168:200] = hashlib.sha256(stdin_bytes).digest() if stdin is not None else bytes(32)
    header[200:216] = attempt_id
    strings = [b"infrastructure.collector", os.fsencode(executable), os.fsencode(cwd),
               os.fsencode(stdin) if stdin is not None else b"/dev/null", *args, *environment]
    body = b"".join(struct.pack("<I", len(value)) + value for value in strings)
    struct.pack_into("<I", header, 16, len(header) + len(body))
    return bytes(header) + body


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def artifact(case, item):
    check(type(item) is dict and type(item.get("path")) is str, "artifact object")
    check(item.get("created") is True and item.get("fd_available") is True and
          item.get("creation_errno") == 0 and item.get("fd_errno") == 0, "actual owned artifact creation/fd")
    name = item["path"]
    check(name not in ("", ".", "..") and "/" not in name, "artifact leaf")
    path = case / "collection" / name
    raw = plain_file(path, 5 * 1024 * 1024)
    check(type(item.get("stored_bytes")) is int and item["stored_bytes"] == len(raw), "actual stored artifact length")
    check(item.get("sha256") == hashlib.sha256(raw).hexdigest(), "independent artifact digest")
    check(type(item.get("seen_bytes")) is int and item["seen_bytes"] >= len(raw), "actual artifact counters")
    return raw


def outer_ok(report, case, expected_exit):
    check(report.get("status") == "COMPLETED" and report.get("cleanup_complete") is True, "outer collection and cleanup")
    raw = report.get("raw_wait_status")
    check(type(raw) is int and os.WIFEXITED(raw) and os.WEXITSTATUS(raw) == expected_exit, "outer actual raw exit")
    check((case / "outer" / "stdout.bin").read_bytes() == b"", "outer literal empty stdout")
    expected_stderr = b"fresh attempt creation failed\n" if expected_exit == 125 else b""
    check((case / "outer" / "stderr.bin").read_bytes() == expected_stderr, "outer literal stderr")
    for name in ("stdout", "stderr"):
        stream = report["streams"][name]
        check(stream.get("eof") is True and stream.get("discarded_observed_bytes") == 0, "outer complete stream")


def run_case(supervisor, collector, binary, fixture_bytes, root, name, builder=False):
    case = root / name
    case.mkdir(mode=0o755)
    inputs = case / "inputs"; inputs.mkdir(mode=0o755)
    cwd = case / "cwd"; cwd.mkdir(mode=0o755)
    executable = inputs / "fixture"
    executable.write_bytes(fixture_bytes); executable.chmod(0o755)
    manifest_bytes = b'{"kind":"opaque-infrastructure-input-bytes","application_acceptance":false}\n'
    manifest = inputs / "selected-inputs.json"; manifest.write_bytes(manifest_bytes)
    stdin_bytes = bytes((0, 1, 0xa5, 10, 255, 0))
    stdin = inputs / "stdin.bin"; stdin.write_bytes(stdin_bytes)
    mode = name if name in CASES[:13] else "stdin-devnull"
    args = [b"literal-app", mode.encode()]
    environment = []
    stdin_selected = None
    if name == "literal":
        args += [b"", b"A=B"]
        environment = [b"ONLY=A=B", b"EMPTY=", b"EXPECTED_CWD=" + os.fsencode(cwd)]
        stdin_selected = stdin
    if name in ("bad-stdin-hash", "stdin-fifo"):
        stdin_selected = stdin
    if name == "replace-source":
        args.append(os.fsencode(executable))
    if name == "script-executable":
        fixture_bytes = b"#!/bin/sh\nexit 0\n"
        executable.write_bytes(fixture_bytes)
    attempt_id = hashlib.sha256(name.encode()).digest()[:16]
    wire = bytearray(request_wire(executable, cwd, stdin_selected, args, environment,
                                  manifest_bytes, fixture_bytes, stdin_bytes, attempt_id,
                                  role=2 if name == "role-two" else 1))
    if name == "bad-executable-hash": wire[136] ^= 1
    if name == "bad-stdin-hash": wire[168] ^= 1
    if name == "bad-manifest-hash": wire[104] ^= 1
    if name == "malformed-request": wire[216] = 1
    request_path = inputs / "request.bin"
    request_path.write_bytes(wire)
    (case / "expected-request.bin").write_bytes(wire)
    if name == "request-fifo":
        request_path.unlink(); os.mkfifo(request_path, 0o600)
    if name == "executable-symlink":
        actual = inputs / "fixture-real"; executable.rename(actual); executable.symlink_to(actual.name)
    if name == "stdin-fifo":
        stdin.unlink(); os.mkfifo(stdin, 0o600)
    if name == "missing-executable": executable.unlink()
    attempt = case / "collection"
    if name == "existing-attempt":
        attempt.mkdir(); (attempt / "original.txt").write_bytes(b"ORIGINAL\n")
    argv = [str(collector), "--unknown" if name == "unknown-mode" else "--linux-sealed-infrastructure-v1",
            str(request_path), str(manifest), str(attempt)]
    expected_stdout = {"literal": b"LITERAL_OK\n", "empty-env": b"EMPTY_ENV\n", "stdin-devnull": b"DEVNULL\n",
                       "pressure": b"O" * 65536, "stdout-over": b"X" * 65536,
                       "replace-source": b"SEALED_SOURCE_UNCHANGED\n"}.get(name, b"")
    expected_stderr = {"literal": b"LITERAL_ERR\n", "pressure": b"E" * 65536,
                       "stderr-over": b"Y" * 65536}.get(name, b"")
    (case / "expected-stdout.bin").write_bytes(expected_stdout)
    (case / "expected-stderr.bin").write_bytes(expected_stderr)
    parent_environment = {"COLLECTOR_PARENT_ONLY": "must-not-reach-subject"}
    save(case / "invocation.json", {"argv": argv, "cwd": str(case), "env": parent_environment, "outer_timeout_seconds": 40,
                                    "outer_cleanup_seconds": 15, "builder_only": builder,
                                    "fixture_binary_input": identity(binary)})
    started = time.monotonic()
    result = supervisor.run_supervised(argv, cwd=str(case), env=parent_environment, attempt_dir=case / "outer",
                                      timeout_seconds=40, cleanup_timeout_seconds=15,
                                      stdout_limit_bytes=65536, stderr_limit_bytes=65536)
    save(case / "outer-returned.json", result)
    save(case / "collection-observed.json", {"elapsed_seconds": time.monotonic() - started})
    if name == "existing-attempt":
        outer_ok(result, case, 125)
        check(sorted(p.name for p in attempt.iterdir()) == ["original.txt"] and
              (attempt / "original.txt").read_bytes() == b"ORIGINAL\n", "preexisting attempt preserved")
        return {"case": name, "status": "PASS_INFRASTRUCTURE_ONLY"}
    report = json.loads(plain_file(attempt / "report.json", 1024 * 1024))
    check(report.get("schema_version") == 1 and report.get("kind") == "linux-sealed-infrastructure-collection", "actual report schema")
    for key in ("application_acceptance", "transport_acceptance", "backend_enabled", "pathname_execution", "loader_closure_verified"):
        check(report.get(key) is False, "no acceptance or unsupported semantics")
    check(report.get("native_payload") is None, "no invented native identity")
    actual_names = []
    for entry in report["artifacts"]:
        if entry is not None: artifact(case, entry)
        if entry is not None: actual_names.append(entry["path"])
    check(len(actual_names) == len(set(actual_names)), "no duplicate artifact identity")
    # Join copied evidence to independent authored bytes, including failed-input
    # captures; a self-consistent reported digest alone cannot satisfy this gate.
    expected_copies = {
        "request.bin": b"" if name == "request-fifo" else bytes(wire),
        "selected-inputs.bin": manifest_bytes,
        "executable.verified.bin": b"" if name in ("executable-symlink", "missing-executable") else fixture_bytes,
        "stdin.verified.bin": b"" if name == "stdin-fifo" else stdin_bytes,
    }
    for leaf, expected_bytes in expected_copies.items():
        if leaf in actual_names:
            check((attempt / leaf).read_bytes() == expected_bytes, "independent authored input capture: " + leaf)
    blocked = {"role-two", "unknown-mode", "malformed-request", "script-executable"}
    prep_errors = {"bad-executable-hash", "bad-stdin-hash", "bad-manifest-hash", "request-fifo",
                   "executable-symlink", "stdin-fifo", "missing-executable"}
    expected_status = ("BLOCKED" if builder or name in blocked else "PREPARATION_ERROR" if name in prep_errors else
                       "OUTPUT_LIMIT" if name in ("stdout-over", "stderr-over") else
                       "ORPHANED_DESCENDANTS" if name in ("pipe-holder", "escaped-holder") else
                       "TIMED_OUT" if name == "timeout" else "INTERRUPTED" if name == "interrupt-collector" else "COMPLETED")
    check(report.get("status") == expected_status, "independent expected collection status: " + expected_status)
    if name in EXPECTED_FAILURES:
        reason, error = EXPECTED_FAILURES[name]
        check(report.get("first_failure") == reason and type(report.get("first_failure_errno")) is int and
              report["first_failure_errno"] == error, "specific intended failure gate")
    outer_ok(result, case, 2 if expected_status == "BLOCKED" else 0 if expected_status == "COMPLETED" else 1)
    if builder or name in blocked or name in prep_errors:
        check(report.get("child_created") is False and report.get("linux_child") is None, "negative input did not launch")
        if builder:
            check(report.get("first_failure") == "root-infrastructure-identity-required", "actual builder identity blocked")
        return {"case": name, "status": "PASS_INFRASTRUCTURE_ONLY", "observed_status": expected_status}
    check(report.get("child_created") is True and report.get("setup_validated") is True, "actual child and checked setup")
    expected_names = {"request.bin", "selected-inputs.bin", "argv.nul", "env.nul", "events.jsonl", "executable.verified.bin",
                      "stdout.bin", "stderr.bin", "setup.bin"}
    if stdin_selected is not None: expected_names.add("stdin.verified.bin")
    check(set(actual_names) == expected_names, "complete exact runtime artifact inventory")
    check(report.get("cleanup_complete") is True and report.get("owned_records_omitted") == 0, "bounded owned cleanup complete")
    child = report["linux_child"]; raw = child["raw_wait_status"]
    check(child.get("identity_observed") is True and child.get("reaped") is True and type(raw) is int, "actual identified raw child wait")
    check(child["wait"]["exited"] is os.WIFEXITED(raw) and child["wait"]["signaled"] is os.WIFSIGNALED(raw), "raw wait decoder agreement")
    if name == "signal-term": check(os.WIFSIGNALED(raw) and os.WTERMSIG(raw) == signal.SIGTERM, "genuine SIGTERM")
    elif name in ("timeout", "interrupt-collector"):
        check(os.WIFSIGNALED(raw) and os.WTERMSIG(raw) == signal.SIGKILL, "actual owned cleanup SIGKILL")
    elif name not in ("stdout-over", "stderr-over"):
        expected_exit = 37 if name == "literal" else 143 if name == "exit143" else 0
        check(os.WIFEXITED(raw) and os.WEXITSTATUS(raw) == expected_exit, "independent expected child exit")
    check((attempt / "stdout.bin").read_bytes() == expected_stdout, "literal independent stdout")
    check((attempt / "stderr.bin").read_bytes() == expected_stderr, "literal independent stderr")
    check((attempt / "argv.nul").read_bytes() == b"".join(value + b"\0" for value in args), "literal argument record")
    check((attempt / "env.nul").read_bytes() == b"".join(value + b"\0" for value in environment), "literal complete environment")
    check((attempt / "executable.verified.bin").read_bytes() == fixture_bytes, "actual retained executable bytes")
    if stdin_selected is not None: check((attempt / "stdin.verified.bin").read_bytes() == stdin_bytes, "actual retained stdin bytes")
    for key in ("stdout_eof", "stderr_eof", "setup_eof"): check(report["streams"].get(key) is True, "actual pipe EOF")
    check(report["process_deadline_ns"] - report["process_start_ns"] == 10_000_000_000, "independent exact ten-second process allowance")
    check(report["cleanup_deadline_ns"] - report["cleanup_start_ns"] == 15_000_000_000 and
          report["cleanup_finished_ns"] < report["cleanup_deadline_ns"], "actual bounded cleanup observation")
    if expected_status == "COMPLETED":
        check(report["process_start_ns"] <= report["completion_observed_ns"] < report["process_deadline_ns"], "on-time observed completion")
        check(report["first_failure"] == "none", "no hidden first failure")
    if name in ("stdout-over", "stderr-over"):
        selected = "stdout.bin" if name == "stdout-over" else "stderr.bin"
        entry = next(item for item in report["artifacts"] if item and item["path"] == selected)
        check(entry["truncated"] is True and entry["seen_bytes"] == 65537 and entry["stored_bytes"] == 65536, "explicit one-byte stream loss")
    if name in ("pipe-holder", "escaped-holder"):
        check(len(report["owned_children"]) == 1, "actual one synthetic adopted child")
        adopted = report["owned_children"][0]
        check(adopted["identity_observed"] is True and adopted["reaped"] is True and
              os.WIFSIGNALED(adopted["raw_wait_status"]) and os.WTERMSIG(adopted["raw_wait_status"]) == signal.SIGKILL,
              "actual adopted child reap")
        if name == "escaped-holder": check(adopted["sid_at_observation"] == adopted["pid"], "actual escaped child session")
    if name == "interrupt-collector":
        check(report["collector_interruption_signal"] == signal.SIGTERM and report["first_failure_errno"] == errno.EINTR,
              "actual signal recorded separately from interruption errno")
    if name == "replace-source": check(executable.read_bytes() == b"changed\n", "temporary source mutation occurred after sealing")
    return {"case": name, "status": "PASS_INFRASTRUCTURE_ONLY", "observed_status": expected_status, "actual_raw_wait_status": raw}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--collector", type=Path, required=True)
    parser.add_argument("--fixture", type=Path, required=True)
    parser.add_argument("--supervisor", type=Path, required=True)
    parser.add_argument("--attempt-root", type=Path, required=True)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--root-infrastructure", action="store_true")
    group.add_argument("--builder-only", action="store_true")
    args = parser.parse_args()
    if args.root_infrastructure and (os.getuid() != 0 or os.geteuid() != 0):
        parser.error("root profile requires actual isolated root; builder must use --builder-only")
    if args.builder_only and (os.getuid() == 0 or os.geteuid() == 0):
        parser.error("builder negative requires an actual nonroot UID/EUID")
    fixture = plain_file(args.fixture, 1024 * 1024)
    plain_file(args.collector, 4 * 1024 * 1024)
    plain_file(args.supervisor, 1024 * 1024)
    root = args.attempt_root
    if not root.is_absolute() or root.parent.resolve(strict=True) != root.parent or root.name in ("", ".", ".."):
        parser.error("attempt root must have an absolute canonical existing parent")
    root.mkdir(mode=0o755)
    record = {"schema_version": 1, "kind": "actual-linux-sealed-collector-infrastructure-tests",
              "status": "FAIL", "application_acceptance": False, "backend_enabled": False,
              "uid": os.getuid(), "euid": os.geteuid(), "cases": [],
              "inputs": [identity(p) for p in (args.collector, args.fixture, args.supervisor, Path(__file__).resolve())]}
    save(root / "frozen-inputs.json", record["inputs"])
    spec = importlib.util.spec_from_file_location("actual_linux_collector_outer_supervisor", args.supervisor)
    supervisor = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(supervisor)
    names = ("builder-identity",) if args.builder_only else CASES
    try:
        for name in names:
            result = run_case(supervisor, args.collector, args.fixture, fixture, root, name, builder=args.builder_only)
            record["cases"].append(result)
            save(root / name / "assertions.json", result)
            print("PASS", name, flush=True)
        for item in record["inputs"]:
            check(identity(Path(item["path"])) == item, "driver/collector/fixture/supervisor source drift")
        record["status"] = "PASS_INFRASTRUCTURE_ONLY"
    except BaseException as error:
        record["failure"] = {"type": type(error).__name__, "message": str(error), "traceback": traceback.format_exc()}
        (root / "first-failure.txt").write_text(record["failure"]["traceback"], encoding="utf-8")
        print("FAIL", name, str(error), file=sys.stderr, flush=True)
    finally:
        save(root / "result.json", record)
        print("RETAINED", root, flush=True)
    return 0 if record["status"] == "PASS_INFRASTRUCTURE_ONLY" else 1


if __name__ == "__main__":
    raise SystemExit(main())
