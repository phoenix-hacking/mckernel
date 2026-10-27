#!/usr/bin/env python3
"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

Source producer only. No subprocesses/compiler or workload authority.
Support precisely the adopted CURRENT110 SDK profile; reject profile drift.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re

PROFILE_SHA256 = "64242ef204a7696369462487e5ca17e63f24d1a9d4c9957e43778b643a2fa288"


def derive(profile_path, source_path):
    raw = profile_path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != PROFILE_SHA256:
        raise ValueError("unqualified SDK profile bytes; independent rebinding required")
    profile = json.loads(raw)
    commands = [row for row in profile["exact_commands"]
                if row["stage"] == "selected x86 syscall object"]
    if len(commands) != 1:
        raise ValueError("expected exactly one selected C command")
    command = commands[0]
    argv = command["argv"]
    if argv[0] != "/usr/bin/cc" or command["cwd"] != "/work/output/build/kernel":
        raise ValueError("unqualified compiler/context")
    if argv.count("-c") != 1 or argv.index("-c") != len(argv) - 2:
        raise ValueError("source token must be the one literal final -c operand")
    if any("prefix-map" in arg or arg.startswith("@") or "__FILE__" in arg
           or arg in ("-include", "-imacros") for arg in argv):
        raise ValueError("macro/prefix/source injection requires a new qualified profile")
    origin = argv[-1]
    if origin != "/src/arch/x86_64/kernel/syscall.c":
        raise ValueError("SDK selected source origin changed")
    if not re.fullmatch(r"/[A-Za-z0-9_./-]+", origin):
        raise ValueError("unsupported origin bytes; never normalize or shell-escape")
    source = source_path.read_text()
    if re.search(r'^\s*#\s*(?:line\s+)?\d+\s+"', source, re.M):
        raise ValueError("source filename line directive changes __FILE__")
    if re.search(r"^\s*#\s*(?:define|undef)\s+__FILE__\b", source, re.M):
        raise ValueError("source redefines __FILE__")
    return origin, command


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", type=Path, required=True)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    origin, command = derive(args.profile, args.source)
    args.output.mkdir(parents=True, exist_ok=True)
    # Simple pinned ASCII origin means JSON/C and CMake literals agree exactly.
    literal = json.dumps(origin)
    (args.output / "f06_rt_sigreturn_origin.h").write_text(
        "/* Functional OS only; no security testing. Generated; no C objects. */\n"
        "#ifndef MCKERNEL_F06_RT_SIGRETURN_ORIGIN\n"
        f"#define MCKERNEL_F06_RT_SIGRETURN_ORIGIN {literal}\n"
        "#else\n#error origin must come from the qualified generated header only\n#endif\n")
    (args.output / "f06_rt_sigreturn_origin.cmake").write_text(
        f"set(MCKERNEL_F06_RT_SIGRETURN_ORIGIN {literal})\n")
    (args.output / "rust-environment.json").write_text(json.dumps(
        {"MCKERNEL_F06_RT_SIGRETURN_ORIGIN": origin}, indent=2) + "\n")
    (args.output / "ORIGIN-BINDING.json").write_text(json.dumps({
        "scope": __doc__.splitlines()[0],
        "status": "GENERATED_SOURCE_ONLY_NO_COMPILER_RESULT",
        "profile_sha256": PROFILE_SHA256,
        "source_sha256": hashlib.sha256(args.source.read_bytes()).hexdigest(),
        "source_path": str(args.source),
        "command": command,
        "origin_utf8": origin,
        "origin_bytes_with_nul": list(origin.encode("ascii") + b"\0"),
        "prefix_mapping_flags": [],
        "new_C_runtime_objects": 0,
    }, indent=2) + "\n")


if __name__ == "__main__":
    main()
