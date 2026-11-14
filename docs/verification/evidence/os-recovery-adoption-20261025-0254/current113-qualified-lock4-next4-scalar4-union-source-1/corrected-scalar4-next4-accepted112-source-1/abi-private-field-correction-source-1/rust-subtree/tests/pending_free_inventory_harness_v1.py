#!/usr/bin/env python3
"""Finite-fixture source gate. Default mode is static; --execute is reviewed Layer-B work."""
import ast
import hashlib
import json
import os
import re
import signal
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
RS = ROOT / "kernel/rust/tests/pending_free_inventory_vectors_v1.rs"
C = ROOT / "kernel/rust/tests/pending_free_inventory_reference_v1.c"
MODEL = ROOT / "kernel/rust/tests/pending_free_inventory_v1.rs"
SELECTORS = (
    "empty", "capacity-zero", "capacity-exact", "capacity-exceeded", "count-mismatch",
    "count-overflow", "duplicate-id", "foreign-id", "null-link", "dangling-link",
    "one-sided-link", "malformed-sentinel", "foreign-cycle", "wrong-mode",
    "invalid-page-count", "page-count-overflow", "misaligned-extent", "foreign-extent",
    "overlapping-extent", "stale-generation", "concurrent-mutation", "valid-single", "valid-two",
)
FUTURE_COMPILE_C = ("/usr/bin/gcc", "-std=c11", "-Wall", "-Wextra", "-Werror", "-O2", str(C), "-o", "{output}/pending_free_inventory_reference_v1")
FUTURE_COMPILE_RUST = ("/home/holden/.rustup/toolchains/nightly-x86_64-unknown-linux-gnu/bin/rustc", "--edition=2021", "-C", "panic=abort", str(MODEL), "-o", "{output}/pending_free_inventory_v1")
FUTURE_RUN_C = ("{output}/pending_free_inventory_reference_v1", "{selector}")
FUTURE_RUN_RUST = ("{output}/pending_free_inventory_v1", "{selector}")
ACTIVE = {"command_id": None, "output": None, "pid": None, "started_ns": None}


class HarnessInterrupted(InterruptedError):
    """Outer supervisor owns teardown; this process only preserves its state."""


def durable_json(path, value):
    encoded = (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()
    fd = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        while encoded:
            written = os.write(fd, encoded)
            if written <= 0:
                raise OSError("short durable JSON write")
            encoded = encoded[written:]
        os.fsync(fd)
    finally:
        os.close(fd)


def durable_failure(output, error, interrupted=False):
    if output is None or not output.is_dir():
        return
    value = {"active_command_id": ACTIVE["command_id"], "active_pid": ACTIVE["pid"],
             "active_started_ns": ACTIVE["started_ns"], "error": type(error).__name__,
             "interrupted": interrupted, "message": str(error), "timestamp_ns": time.time_ns()}
    try:
        durable_json(output / "failure.json", value)
        encoded = (type(error).__name__ + ": " + str(error) + "\n").encode()
        fd = os.open(str(output / "failure.txt"), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        try:
            while encoded:
                written = os.write(fd, encoded)
                if written <= 0:
                    raise OSError("short durable failure write")
                encoded = encoded[written:]
            os.fsync(fd)
        finally:
            os.close(fd)
    except BaseException:
        # The original interruption remains authoritative; the outer supervisor retains streams.
        pass


def install_signal_handlers(output):
    def interrupted(signum, _frame):
        error = HarnessInterrupted("harness received " + signal.Signals(signum).name)
        durable_failure(output, error, interrupted=True)
        raise error
    signal.signal(signal.SIGTERM, interrupted)
    signal.signal(signal.SIGINT, interrupted)


def expected_statuses(text):
    rows = re.findall(r'Vector\s*\{\s*name:\s*"([^"]+)",\s*expected:\s*(-?\d+)\s*\}', text)
    return [(name, int(status)) for name, status in rows]


def future_argv(output, selector):
    fmt = {"output": str(output), "selector": selector}
    return (
        tuple(arg.format(**fmt) for arg in FUTURE_COMPILE_C),
        tuple(arg.format(**fmt) for arg in FUTURE_COMPILE_RUST),
        tuple(arg.format(**fmt) for arg in FUTURE_RUN_C),
        tuple(arg.format(**fmt) for arg in FUTURE_RUN_RUST),
    )


def static_check():
    ast.parse(Path(__file__).read_text())
    model, vectors, reference = MODEL.read_text(), RS.read_text(), C.read_text()
    expected = expected_statuses(vectors)
    assert tuple(name for name, _ in expected) == SELECTORS
    assert all(name in model and name in reference for name in SELECTORS)
    assert "fn main()" in model and "int main(" in reference
    for forbidden in ("impl Drop", "unsafe impl Send", "unsafe impl Sync", "kernel::", "crate::", "callback", "release"):
        assert forbidden not in model, forbidden
    assert "#undef MIX" in reference
    for command in FUTURE_COMPILE_C + FUTURE_COMPILE_RUST + FUTURE_RUN_C + FUTURE_RUN_RUST:
        assert isinstance(command, str) and command
    return expected


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run_retained(command, output, command_id):
    """Persist STARTING before fork; outer Layer-B supervisor remains process owner."""
    stdout_path = output / (command_id + ".stdout")
    stderr_path = output / (command_id + ".stderr")
    start_path = output / (command_id + ".start.json")
    terminal_path = output / (command_id + ".terminal.json")
    started_ns = time.time_ns()
    ACTIVE.update(command_id=command_id, output=output, pid=None, started_ns=started_ns)
    durable_json(start_path, {"argv": list(command), "command_id": command_id,
                              "started_ns": started_ns, "state": "STARTING"})
    process = None
    terminal = {"argv": list(command), "command_id": command_id,
                "started_ns": started_ns, "state": "UNOBSERVED"}
    try:
        with stdout_path.open("wb") as stdout, stderr_path.open("wb") as stderr:
            process = subprocess.Popen(command, stdin=subprocess.DEVNULL,
                                       stdout=stdout, stderr=stderr)
            ACTIVE["pid"] = process.pid
            durable_json(start_path, {"argv": list(command), "command_id": command_id,
                                      "pid": process.pid, "started_ns": started_ns,
                                      "state": "RUNNING"})
            returncode = process.wait()
        terminal.update({"ended_ns": time.time_ns(), "pid": process.pid,
                         "returncode": returncode, "state": "OBSERVED"})
        durable_json(terminal_path, terminal)
        ACTIVE.update(command_id=None, pid=None, started_ns=None)
        return returncode, stdout_path.read_text(), stderr_path.read_text()
    except BaseException as error:
        terminal.update({"ended_ns": time.time_ns(), "error": type(error).__name__ + ": " + str(error),
                         "pid": None if process is None else process.pid, "state": "UNOBSERVED"})
        try:
            durable_json(terminal_path, terminal)
        finally:
            durable_failure(output, error, interrupted=isinstance(error, HarnessInterrupted))
        raise


def execute_future(output):
    """Run the exact reviewed plan with persistent evidence; never owns child cleanup."""
    expected = static_check()
    output = Path(output)
    assert output.is_absolute() and output.parent.is_dir() and not output.exists()
    output.mkdir(mode=0o700)
    ACTIVE["output"] = output
    install_signal_handlers(output)
    durable_json(output / "execution-start.json", {"started_ns": time.time_ns(),
                "state": "STARTED", "supervisor_owns_cleanup": True})
    compile_c, compile_rust, _, _ = future_argv(output, SELECTORS[0])
    for command_id, command in (("compile-c", compile_c), ("compile-rust", compile_rust)):
        returncode, stdout, stderr = run_retained(command, output, command_id)
        assert returncode == 0 and stdout == "" and stderr == "", (command, returncode, stdout, stderr)
    binaries = {"c": output / "pending_free_inventory_reference_v1", "rust": output / "pending_free_inventory_v1"}
    executed = 0
    for index, (selector, status) in enumerate(expected):
        _, _, run_c, run_rust = future_argv(output, selector)
        expected_fields = (selector, str(status))
        for program, command in (("c", run_c), ("rust", run_rust)):
            command_id = "run-%02d-%s-%s" % (index, selector, program)
            returncode, stdout, stderr = run_retained(command, output, command_id)
            fields = tuple(stdout.strip().split("|"))
            assert returncode == 0 and stderr == "", (command, returncode, stdout, stderr)
            assert fields[:2] == expected_fields and len(fields) == 4 and fields[2] == fields[3], (command, fields)
            executed += 1
    result = {"binary_sha256": {name: sha256(path) for name, path in binaries.items()},
              "executed": executed, "programs": 2, "selectors": len(expected),
              "source_sha256": {str(path.relative_to(ROOT)): sha256(path) for path in (C, MODEL, RS)},
              "state_hashes": "equal", "status": "PASS_PENDING_FREE_INVENTORY"}
    durable_json(output / "result.json", result)
    print(f"PASS_PENDING_FREE_INVENTORY|executed={executed}|selectors={len(expected)}|programs=2|state_hashes=equal")


def main():
    if len(sys.argv) == 4 and sys.argv[1] == "--execute" and sys.argv[2] == "--output":
        output = Path(sys.argv[3])
        try:
            execute_future(output)
        except BaseException as error:
            durable_failure(output, error, interrupted=isinstance(error, HarnessInterrupted))
            raise
    elif not sys.argv[1:]:
        expected = static_check()
        print(f"PASS_SOURCE_INVENTORY_STRUCTURE|selectors={len(expected)}|future_executed=0|compile=disabled|runtime=disabled")
    else:
        raise SystemExit("usage: pending_free_inventory_harness_v1.py [--execute --output ABSENT]")


if __name__ == "__main__":
    main()
