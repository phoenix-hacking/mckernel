#!/usr/bin/env python3
"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Proposed focused CMake producer-fragment configure checks. No compiler or build.
This does not configure the complete McKernel project or qualify its SDK graph.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parent
CANDIDATE_SHA = "a2451f574cf87b4ea5467303bc42684b72e63f7e3d352639998af682a25d1c2f"
PREIMAGE_SHA = "507e1f058f8bc559f4d8b47eb5646d64aa7a20653bce89ad578a5af452ab7faa"
PAIRS = {
    "f03_io_diagnostic_callbacks_candidate": "MCKERNEL_RUST_F03_IO_DIAGNOSTICS",
    "f03_mincore_candidate": "MCKERNEL_RUST_F03_MINCORE",
    "f03_move_pages_candidate": "MCKERNEL_RUST_F03_MOVE_PAGES",
    "f03_sched_bridges_candidate": "MCKERNEL_RUST_F03_SCHED_BRIDGES",
    "f03_signal_process_bridges_candidate": "MCKERNEL_RUST_F03_SIGNAL_PROCESS_BRIDGES",
    "f03_dispatch_context_candidate": "MCKERNEL_RUST_F03_DISPATCH_CONTEXT",
    "f03_leaf_callbacks_candidate": "MCKERNEL_RUST_F03_LEAF_CALLBACKS",
}

def checked(path, expected):
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != expected:
        raise ValueError("bound source changed: " + str(path))
    return raw.decode()

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    candidate = checked(ROOT / "candidate/kernel/CMakeLists.txt", CANDIDATE_SHA)
    preimage = checked(ROOT / "canonical-preimage.CMakeLists.txt", PREIMAGE_SHA)
    delta_cfg = '\t\tlist(APPEND RUST_KERNEL_CFG "--cfg" "f03_dispatch_context_candidate")\n\t\tlist(APPEND RUST_KERNEL_CFG "--cfg" "f03_leaf_callbacks_candidate")\n'
    cfg = '\t\t# Pair the existing F03 Rust providers with syscall.c source selectors below.\n\t\tlist(APPEND RUST_KERNEL_CFG\n\t\t\t"--cfg" "f03_io_diagnostic_callbacks_candidate"\n\t\t\t"--cfg" "f03_mincore_candidate")\n\t\tlist(APPEND RUST_KERNEL_CFG "--cfg" "f03_move_pages_candidate")\n\t\tlist(APPEND RUST_KERNEL_CFG "--cfg" "f03_sched_bridges_candidate")\n\t\tlist(APPEND RUST_KERNEL_CFG "--cfg" "f03_signal_process_bridges_candidate")\n\t\tlist(APPEND RUST_KERNEL_CFG "--cfg" "f03_dispatch_context_candidate")\n\t\tlist(APPEND RUST_KERNEL_CFG "--cfg" "f03_leaf_callbacks_candidate")\n'
    removed = candidate.replace(delta_cfg, "", 1).replace(
        ";MCKERNEL_RUST_F03_DISPATCH_CONTEXT", "", 1).replace(";MCKERNEL_RUST_F03_LEAF_CALLBACKS", "", 1)
    if removed != preimage:
        raise ValueError("change exceeds the paired cfg/definition delta")
    if "f03_move_pages_copy_error_candidate" in candidate:
        raise ValueError("copy-error semantic correction must remain default OFF")
    # These exact guards are retained in the real producer. The harness covers
    # the successful Rust-selection path; compiler discovery/version validation
    # is outside this fragment and remains unchanged in the full source.
    rust_guard = 'if (ENABLE_RUST_KERNEL AND "${ARCH}" STREQUAL "x86_64")'
    c_guard = "if (RUST_KERNEL_ENABLED)"
    if candidate.count(rust_guard) != 1 or c_guard not in candidate:
        raise ValueError("real producer guard changed")
    setter = re.search(
        r'set_source_files_properties\("\$\{CMAKE_CURRENT_SOURCE_DIR\}/syscall\.c"\s*'
        r'PROPERTIES COMPILE_DEFINITIONS\s*"[^"\n]+"\)', candidate)
    if setter is None:
        raise ValueError("syscall.c exact source definition setter absent")
    if candidate.count(cfg) != 1:
        raise ValueError("paired Rust cfg producer not unique")
    # LANGUAGES NONE and only these extracted data/selection statements ensure
    # the check creates no compiler detection target or compilation job.
    harness = (
        "cmake_minimum_required(VERSION 3.11)\n"
        "project(f03_current230_dispatch_leaf_paired_producer_selection LANGUAGES NONE)\n"
        "set(RUST_KERNEL_ENABLED OFF)\n" + rust_guard + "\n"
        "set(RUST_KERNEL_CFG)\n" + cfg + "set(RUST_KERNEL_ENABLED ON)\nendif()\n"
        + c_guard + "\n" + setter.group(0) + "\nendif()\n"
        'get_source_file_property(_cdefs "${CMAKE_CURRENT_SOURCE_DIR}/syscall.c" COMPILE_DEFINITIONS)\n'
        'file(WRITE "${CMAKE_CURRENT_BINARY_DIR}/selection.txt" "rust=${RUST_KERNEL_ENABLED}\ncfg=${RUST_KERNEL_CFG}\ncdefs=${_cdefs}\n")\n'
    )
    args.output.mkdir(mode=0o700, parents=False, exist_ok=False)
    source = args.output / "producer-fragment"
    source.mkdir(mode=0o700)
    (source / "CMakeLists.txt").write_text(harness)
    cases = [("rust_x86", "x86_64", "ON", True),
             ("fallback_x86", "x86_64", "OFF", False),
             ("non_x86", "arm64", "ON", False)]
    results = []
    for name, arch, rust, expected in cases:
        build = args.output / name
        command = ["/usr/bin/cmake", "-S", str(source), "-B", str(build),
                   "-DARCH=" + arch, "-DENABLE_RUST_KERNEL=" + rust]
        result = subprocess.run(command, stdin=subprocess.DEVNULL, capture_output=True,
                                env={"PATH": "/usr/bin:/bin", "LANG": "C", "LC_ALL": "C"},
                                timeout=10, check=False)
        (args.output / (name + ".stdout")).write_bytes(result.stdout)
        (args.output / (name + ".stderr")).write_bytes(result.stderr)
        if result.returncode:
            raise RuntimeError("first unexpected configure result: " + name)
        raw = (build / "selection.txt").read_text()
        values = dict(line.split("=", 1) for line in raw.splitlines())
        flags = values["cfg"].split(";")
        defs = values["cdefs"].split(";")
        for rust_cfg, c_define in PAIRS.items():
            if (flags.count(rust_cfg) != int(expected)
                    or defs.count(c_define) != int(expected)):
                raise ValueError(name + ": unpaired source selection")
        if expected and flags.count("--cfg") != 7:
            raise ValueError("unexpected Rust cfg vector")
        if "f03_move_pages_copy_error_candidate" in flags:
            raise ValueError("copy-error semantic correction enabled by producer")
        if not expected and values["rust"] != "OFF":
            raise ValueError("fallback unexpectedly enabled Rust")
        if list(build.rglob("CMakeCCompiler.cmake")) or list(build.rglob("CMakeASMCompiler.cmake")):
            raise ValueError("compiler detection outside intended check")
        results.append(dict(name=name, argv=command, returncode=result.returncode,
                            selected=expected, observed=values))
    report = dict(scope=__doc__.splitlines()[0],
                  status="PASS_THREE_CURRENT230_DISPATCH_LEAF_PAIRED_PRODUCER_CONFIGURES",
                  cases=results, source_delta_exact=True, compiler_invoked=False,
                  whole_project_configure=False, SDK_build=False, native=False,
                  retirement_credit=0,
                  limits="Extracted real producer guards/statements only; full root compiler discovery, default graph/link and matching native proof remain open.")
    (args.output / "RESULT.json").write_text(json.dumps(report, indent=2) + "\n")
    print(report["status"])

if __name__ == "__main__":
    main()
