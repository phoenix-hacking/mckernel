#!/usr/bin/env python3
"""Finite-fixture source gate. Default mode is static; --execute is future Layer-B work."""
import ast
import re
import subprocess
import sys
import tempfile
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
# These are intentionally literal future commands. {output} is a disposable TemporaryDirectory.
FUTURE_COMPILE_C = ("/usr/bin/gcc", "-std=c11", "-Wall", "-Wextra", "-Werror", "-O2", str(C), "-o", "{output}/pending_free_inventory_reference_v1")
FUTURE_COMPILE_RUST = ("/home/holden/.cargo/bin/rustc", "--edition=2021", "-C", "panic=abort", str(MODEL), "-o", "{output}/pending_free_inventory_v1")
FUTURE_RUN_C = ("{output}/pending_free_inventory_reference_v1", "{selector}")
FUTURE_RUN_RUST = ("{output}/pending_free_inventory_v1", "{selector}")

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

def execute_future():
    """Released Layer-B caller may invoke this exact plan; it is never run by source admission."""
    expected = static_check()
    with tempfile.TemporaryDirectory(prefix="pending-free-inventory-") as output:
        compile_c, compile_rust, _, _ = future_argv(output, SELECTORS[0])
        for command in (compile_c, compile_rust):
            completed = subprocess.run(command, check=False, text=True, capture_output=True)
            assert completed.returncode == 0, (command, completed.stdout, completed.stderr)
        executed = 0
        for selector, status in expected:
            _, _, run_c, run_rust = future_argv(output, selector)
            expected_fields = (selector, str(status))
            for command in (run_c, run_rust):
                completed = subprocess.run(command, check=False, text=True, capture_output=True)
                fields = tuple(completed.stdout.strip().split("|"))
                assert completed.returncode == 0, (command, completed.stdout, completed.stderr)
                assert fields[:2] == expected_fields and len(fields) == 4 and fields[2] == fields[3], (command, fields)
                executed += 1
    print(f"PASS_PENDING_FREE_INVENTORY|executed={executed}|selectors={len(expected)}|programs=2|state_hashes=equal")

def main():
    if sys.argv[1:] == ["--execute"]:
        execute_future()
    elif not sys.argv[1:]:
        expected = static_check()
        print(f"PASS_SOURCE_INVENTORY_STRUCTURE|selectors={len(expected)}|future_executed=0|compile=disabled|runtime=disabled")
    else:
        raise SystemExit("usage: pending_free_inventory_harness_v1.py [--execute]")

if __name__ == "__main__":
    main()
