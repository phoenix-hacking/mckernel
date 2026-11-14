#!/usr/bin/env python3
"""Run selected M14 source/ABI/build regressions; a skip is not a pass.

This allowlist does not build a full kernel, initialize submodules, load modules,
install tools, or invoke native/resource controllers. It grants no file closure.
With no --module arguments, run the complete allowlist. Individual subprocesses
have test-owned timeouts; this runner does not impose a local total deadline.
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
    "scripts.tests.test_m14_util_thread",
    "scripts.tests.test_m14_rust_rebuild",
)
SOURCE_PATHS = (
    "kernel/rust/f06_signal_tail.rs", "kernel/rust/f06_rt_sigreturn_xrstor.rs",
    "scripts/derive_f06_signal_metadata.py",
    "kernel/syscall.c", "arch/x86_64/kernel/syscall.c",
    "kernel/rust/syscall_policy.rs", "kernel/rust/abi.rs", "kernel/rust/lib.rs",
    "kernel/rust/f03_forward_adapters.rs", "kernel/rust/f03_ptrace_adapters.rs",
    "kernel/rust/f03_host_cleanup.rs",
    "kernel/rust/f03_util_thread.rs", "kernel/rust/uti_data_providers.rs",
    "scripts/tests/fixtures/f03_util_thread_lifecycle.rs",
    "kernel/rust/f06_signal_ptrace_diagnostics.rs", "kernel/rust/f06_signal_trap_info.rs",
    "kernel/rust/x86_cpu_helpers.rs", "kernel/rust/native_signal.rs",
    "kernel/rust/cls.rs", "kernel/rust/debug.rs", "kernel/rust/lock_helpers.rs",
    "kernel/rust/mem_helpers.rs", "kernel/rust/sched_helpers.rs",
    "kernel/rust/string.rs", "kernel/rust/waitq.rs",
    "kernel/CMakeLists.txt", "cmake/NormalizeRustDepfile.cmake", "scripts/derive_f06_origin.py",
    "scripts/f06_origin_command_profile.json", "scripts/f06_origin_source_binding.json",
    "scripts/run_m14_focused_checks.py",
    "kernel/include/process.h", "kernel/include/syscall.h",
    "arch/x86_64/kernel/cpu.c", "arch/x86_64/kernel/include/registers.h",
    "lib/include/ihk/debug.h", "executer/user/mcexec.c",
    "executer/user/rust/mcexec_helpers.rs",
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


def source_fingerprints(paths):
    hashes, errors = {}, {}
    for name in paths:
        try:
            hashes[name] = hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
        except OSError as error:
            errors[name] = f"{type(error).__name__}: {error}"
    return hashes, errors


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json-output", type=Path, help="write the bounded result record")
    selection = parser.add_mutually_exclusive_group()
    selection.add_argument("--module", action="append", choices=MODULES,
                           help="run this allowlisted module; repeat to select several")
    selection.add_argument("--list", action="store_true",
                           help="list allowlisted modules without importing tests or probing tools")
    args = parser.parse_args(argv)
    if args.list:
        print("\n".join(MODULES))
        return 0
    modules = tuple(name for name in MODULES if args.module is None or name in args.module)
    full_allowlist = modules == MODULES
    sys.path.insert(0, str(ROOT))
    start = time.monotonic()
    result = unittest.TestResult()
    runner_errors = []
    try:
        suite = unittest.defaultTestLoader.loadTestsFromNames(modules)
        result = unittest.TextTestRunner(verbosity=2).run(suite)
    except Exception as error:
        runner_errors.append(f"{type(error).__name__}: {error}")
        print(f"M14 runner error: {runner_errors[-1]}", file=sys.stderr)
    # Retain the existing explicit inventory even for a subset. It is result
    # metadata, not a complete transitive dependency inventory or a reuse key.
    paths = sorted(set(SOURCE_PATHS) | {name.replace(".", "/") + ".py" for name in MODULES})
    hashes, fingerprint_errors = source_fingerprints(paths)
    accepted = result.wasSuccessful() and not result.skipped and not result.expectedFailures \
        and result.testsRun > 0 and not runner_errors and not fingerprint_errors
    record = {
        "schema_version": 2,
        "scope": "M14_FOCUSED_HOST_SOURCE_ABI_BUILD_ONLY",
        "selection_mode": "full" if full_allowlist else "subset",
        "full_allowlist_selected": full_allowlist,
        "requested_modules": list(modules) if args.module is not None else None,
        "unselected_modules": [name for name in MODULES if name not in modules],
        "source_base_commit": output(["git", "rev-parse", "HEAD"]),
        "source_files_sha256": hashes,
        "source_fingerprint_errors": fingerprint_errors,
        "runner_errors": runner_errors,
        "toolchain": {"rustc": version("RUSTC", "rustc"),
                      "cc": version("CC", "gcc"),
                      "cmake": version("CMAKE", "cmake"),
                      "python": sys.version.split()[0]},
        "modules": list(modules),
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
            "Only the selected modules ran; a subset does not establish a full-allowlist result.",
            "Source hashes are collected after testing from an explicit, incomplete dependency inventory; not a reuse key.",
            "Test-owned subprocess timeouts do not impose a local whole-suite deadline.",
        ],
    }
    if fingerprint_errors:
        print(f"M14 source fingerprint errors: {len(fingerprint_errors)}; see result record", file=sys.stderr)
    if args.json_output:
        try:
            args.json_output.parent.mkdir(parents=True, exist_ok=True)
            args.json_output.write_text(json.dumps(record, indent=2) + "\n")
        except OSError as error:
            accepted = False
            print(f"M14 result record could not be written: {error}", file=sys.stderr)
    label = "full allowlist" if full_allowlist else "subset"
    print(f"M14 focused {label}: {result.testsRun} checks, {len(result.failures)} failures, "
          f"{len(result.errors)} errors, {len(result.skipped)} skips; "
          f"focused result {'PASS' if accepted else 'FAIL'}")
    return 0 if accepted else 1


if __name__ == "__main__":
    raise SystemExit(main())
