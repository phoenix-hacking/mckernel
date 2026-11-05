#!/usr/bin/env python3
"""Emit the eligible F03 adapter unit using genuine provider declarations.

This ordinary HOST compilation excludes the full kernel crate and its held
sources. Providers stay unresolved: this is reusable machine code, not a final
image, a native qualification, or C retirement.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import time

from scripts.tests.test_m14_f06_tail_codegen import definition, provider


ROOT = Path(__file__).resolve().parents[1]
RUST = ROOT / "kernel/rust"
ENTRIES = (
    "syscall_do_syscall2_bridge", "syscall_do_syscall3_bridge",
    "syscall_policy_do_syscall2_bridge", "syscall_policy_do_syscall3_bridge",
    "wait_host_wait4_bridge", "ptrace_detach_do_kill_bridge",
    "ptrace_detach_wakeup_bridge", "terminate_host",
    "do_setresuid", "do_setresgid",
)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prepare(directory):
    policy = (RUST / "syscall_policy.rs").read_text()
    lock = (RUST / "lock_helpers.rs").read_text()
    node = definition(lock, "McsRwlockNodeIrqsave", "struct")
    prefix = lock[:lock.index(node)].rstrip().splitlines()[-1]
    if prefix != "#[repr(C, align(64))]":
        raise ValueError("genuine lock-node representation changed")
    aliases = (
        "SyscallFindProcessFn", "SyscallProcessUnlockFn", "TerminateHostRefSetFn",
        "WaitThreadSideEffectFn", "SyscallDoKillThreadFn", "SyscallRequestCallFn",
        "SyscallGetcredFn",
    )
    declarations = []
    for name in aliases:
        matches = re.findall(r"(?m)^type " + name + r"\s*=[^;]+;", policy)
        if len(matches) != 1:
            raise ValueError("ambiguous genuine provider type: " + name)
        declarations.append(matches[0])
    signatures = [provider(policy, name) for name in (
        "syscall_generic_forwarding_body_result", "terminate_host_body_result",
        "syscall_refresh_cred_fields_body_result", "getcred")]
    cpu = (RUST / "x86_local.rs").read_text()
    cpu_signatures = set(re.findall(
        r'pub unsafe extern "C" fn ihk_mc_get_processor_id\([^{};]*\)[^{};]*', cpu))
    if len(cpu_signatures) != 1:
        raise ValueError("genuine CPU provider declarations differ")
    cpu_signature = cpu_signatures.pop().strip().replace(
        'pub unsafe extern "C" fn ', "pub fn ", 1) + ";"
    pieces = [
        "#![no_std]\n#![allow(dead_code,unused_imports)]",
        f'#[path="{RUST / "abi.rs"}"] mod abi;',
        "mod lock_helpers { use crate::abi::*;\n" + prefix + "\n" + node + "\n}",
        'mod cls { use crate::abi::*; unsafe extern "C" {\n'
        + provider((RUST / "cls.rs").read_text(), "get_this_cpu_local_var") + "\n}}",
        'mod x86_local { use crate::abi::*; unsafe extern "C" {\n'
        + cpu_signature + "\n}}",
        "mod syscall_policy { use crate::abi::*; use core::ffi::c_void;\n"
        + "\n".join(declarations) + '\nunsafe extern "C" {\n'
        + "\n".join(signatures) + "\n}}",
    ]
    modules = ("f03_forward_adapters", "f03_ptrace_adapters", "f03_host_cleanup",
               "f03_credential_refresh")
    for name in modules:
        pieces.append(f'#[path="{RUST / (name + ".rs")}"] mod {name};')
    source = directory / "f03_adapters.rs"
    source.write_text("\n".join(pieces) + "\n")
    inputs = ["abi", "lock_helpers", "cls", "x86_local", "syscall_policy", *modules]
    return source, {str((RUST / (name + ".rs")).relative_to(ROOT)):
                    digest(RUST / (name + ".rs")) for name in inputs}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rustc", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if 6 not in os.sched_getaffinity(0):
        raise ValueError("ordinary HOST CPU6 unavailable")
    directory = args.output.resolve()
    directory.mkdir(parents=True, exist_ok=False)
    source, inputs = prepare(directory)
    obj = directory / "f03_adapters.o"
    compiler = args.rustc.resolve(strict=True)
    command = [
        "/usr/bin/taskset", "-c", "6", "/usr/bin/prlimit",
        "--as=1073741824:1073741824", "--cpu=45:45",
        "--fsize=67108864:67108864", "--core=0:0", "--",
        "/usr/bin/time", "-v", "-o", str(directory / "time.txt"),
        str(compiler), "--edition=2021", "--crate-type=lib",
        "-C", "panic=abort", "-C", "opt-level=2", "-C", "code-model=large",
        "-C", "relocation-model=static", "-C", "no-redzone=yes",
        "-C", "no-vectorize-loops", "-C", "no-vectorize-slp",
        "-C", "target-feature=-sse,-sse2,-sse3,-ssse3,-sse4.1,-sse4.2,-avx,-avx2,-fma",
        "--emit=obj", "-o", str(obj), str(source),
    ]
    start = time.monotonic()
    result = subprocess.run(command, capture_output=True, timeout=60)
    (directory / "stdout.txt").write_bytes(result.stdout)
    (directory / "stderr.txt").write_bytes(result.stderr)
    receipt = {
        "scope": "M14_F03_ELIGIBLE_HOST_CODEGEN_ONLY", "command": command,
        "exit_code": result.returncode, "wall_seconds": time.monotonic() - start,
        "compiler": str(compiler), "compiler_sha256": digest(compiler),
        "compiler_version": subprocess.check_output([str(compiler), "--version"], text=True).strip(),
        "source_files_sha256": inputs, "unit_sha256": digest(source),
        "linked": False, "native_qualified": False, "c_retired": False,
    }
    if result.returncode == 0:
        symbols = subprocess.check_output(["nm", "--format=posix", "--print-size", str(obj)], text=True)
        (directory / "symbols.txt").write_text(symbols)
        definitions = {row[0]: int(row[3], 16) for line in symbols.splitlines()
                       if len(row := line.split()) >= 4 and row[1] == "T"}
        if any(definitions.get(name, 0) == 0 for name in ENTRIES):
            raise ValueError("required adapter body missing or compiler-elided")
        receipt.update(object_sha256=digest(obj), object_bytes=obj.stat().st_size,
                       definitions={name: definitions[name] for name in ENTRIES})
    (directory / "receipt.json").write_text(json.dumps(receipt, sort_keys=True, indent=2) + "\n")
    print(json.dumps(receipt, sort_keys=True))
    if result.returncode:
        raise SystemExit(result.returncode)


if __name__ == "__main__":
    main()
