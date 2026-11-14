#!/usr/bin/env python3
"""Run bounded M14 source/ABI/build regressions; a skip is not a pass.

This allowlist does not build a full kernel, initialize submodules, load modules,
install tools, or invoke native/resource controllers. It grants no file closure.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
MODULES = (
    "scripts.tests.test_m14_f06_tail_codegen",
    "scripts.tests.test_f03_forward_adapters",
    "scripts.tests.test_f06_signal_adapters",
    "scripts.tests.test_m14_syscall_selection",
    "scripts.tests.test_m14_build_origin",
    "scripts.tests.test_m14_f03_signal_context",
    "scripts.tests.test_m14_f03_wait_results",
    "scripts.tests.test_m14_f03_wait_c",
    "scripts.tests.test_m14_f03_sigaltstack_alias",
    "scripts.tests.test_m14_f06_xstate_extent",
    "scripts.tests.test_m14_f03_interrupt_context",
    "scripts.tests.test_m14_f03_ptrace_adapters",
    "scripts.tests.test_m14_f03_host_cleanup",
    "scripts.tests.test_m14_f03_perf_read_count",
    "scripts.tests.test_m14_f06_sigreturn_transaction",
    "scripts.tests.test_m14_f06_signal_xsave_cleanup",
    "scripts.tests.test_m14_f06_signal_restart",
    "scripts.tests.test_m14_rust_rebuild",
)
SOURCE_PATHS = (
    "kernel/rust/f06_signal_tail.rs", "kernel/rust/f06_rt_sigreturn_xrstor.rs",
    "scripts/derive_f06_signal_metadata.py",
    "kernel/syscall.c", "arch/x86_64/kernel/syscall.c",
    "kernel/rust/syscall_policy.rs", "kernel/rust/abi.rs", "kernel/rust/lib.rs",
    "kernel/rust/f03_forward_adapters.rs", "kernel/rust/f03_ptrace_adapters.rs",
    "kernel/rust/f03_host_cleanup.rs",
    "kernel/rust/f06_signal_ptrace_diagnostics.rs", "kernel/rust/f06_signal_trap_info.rs",
    "kernel/rust/x86_cpu_helpers.rs", "kernel/rust/native_signal.rs",
    "kernel/rust/cls.rs", "kernel/rust/debug.rs", "kernel/rust/lock_helpers.rs",
    "kernel/rust/mem_helpers.rs", "kernel/rust/sched_helpers.rs",
    "kernel/rust/string.rs", "kernel/rust/waitq.rs",
    "kernel/CMakeLists.txt", "cmake/NormalizeRustDepfile.cmake", "scripts/derive_f06_origin.py",
    "scripts/f06_origin_command_profile.json", "scripts/f06_origin_source_binding.json",
    "scripts/run_m14_focused_checks.py",
)


def output(command):
    try:
        result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=15)
        return result.stdout.strip() if result.returncode == 0 else None
    except (OSError, subprocess.TimeoutExpired):
        return None


def version(variable, fallback):
    executable = os.environ.get(variable) or shutil.which(fallback)
    value = output([executable, "--version"]) if executable else None
    return value.splitlines()[0] if value else None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json-output", type=Path, help="write the bounded result record")
    args = parser.parse_args()
    sys.path.insert(0, str(ROOT))
    start = time.monotonic()
    suite = unittest.defaultTestLoader.loadTestsFromNames(MODULES)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    accepted = result.wasSuccessful() and not result.skipped and not result.expectedFailures \
        and result.testsRun > 0
    paths = sorted(set(SOURCE_PATHS) | {name.replace(".", "/") + ".py" for name in MODULES})
    record = {
        "schema_version": 1,
        "scope": "M14_FOCUSED_HOST_SOURCE_ABI_BUILD_ONLY",
        "source_base_commit": output(["git", "rev-parse", "HEAD"]),
        "source_files_sha256": {
            name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in paths
        },
        "toolchain": {"rustc": version("RUSTC", "rustc"),
                      "cc": version("CC", "gcc"),
                      "cmake": version("CMAKE", "cmake"),
                      "python": sys.version.split()[0]},
        "modules": list(MODULES),
        "checks_run": result.testsRun,
        "failures": [test.id() for test, _ in result.failures],
        "errors": [test.id() for test, _ in result.errors],
        "skipped": [test.id() for test, _ in result.skipped],
        "expected_failures": [test.id() for test, _ in result.expectedFailures],
        "unexpected_successes": [test.id() for test in result.unexpectedSuccesses],
        "elapsed_seconds": round(time.monotonic() - start, 3),
        "passed_without_skips": accepted,
        "acceptance": {"establishes_file_closure": False,
                       "establishes_c_retirement": False,
                       "establishes_native_qualification": False},
        "limitations": [
            "Focused production-body fixtures and complete F06 module code generation; not a full kernel link.",
            "Complete F06 code generation leaves genuine provider declarations unresolved.",
            "GS, XSAVE and XRSTOR instructions are emitted but not executed or natively qualified.",
            "F03 ptrace adapters and F06 whole ownership remain opt-in pending matching image qualification.",
            "The separate C-ownership check does not establish final-image ownership or native acceptance.",
            "Perf group/descriptor concurrency and open-error ownership remain unqualified.",
            "No original native-host ownership, device or lifecycle action is performed.",
        ],
    }
    if args.json_output:
        args.json_output.parent.mkdir(parents=True, exist_ok=True)
        args.json_output.write_text(json.dumps(record, indent=2) + "\n")
    print(f"M14: {result.testsRun} checks, {len(result.failures)} failures, "
          f"{len(result.errors)} errors, {len(result.skipped)} skips; "
          f"focused result {'PASS' if accepted else 'FAIL'}")
    return 0 if accepted else 1


if __name__ == "__main__":
    raise SystemExit(main())
