#!/usr/bin/env python3
"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

Source producer only. No subprocesses/compiler or workload authority.
Support precisely the private CURRENT113 arch-command profile; reject profile drift.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re

PROFILE_SHA256 = "f9f51aa43d4a572b08f26fae7340f16998044590c9c684489ed0cf4d15e17d6f"


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
    if hashlib.sha256(source_path.read_bytes()).hexdigest() != profile["composed_arch_source_sha256"]:
        raise ValueError("exact proposed architecture source bytes required")
    source = source_path.read_text()
    if re.search(r'^\s*#\s*(?:line\s+)?\d+\s+"', source, re.M):
        raise ValueError("source filename line directive changes __FILE__")
    if re.search(r"^\s*#\s*(?:define|undef)\s+__FILE__\b", source, re.M):
        raise ValueError("source redefines __FILE__")
    return origin, command



def derive_clone_cpuid(profile_path, source_path, origin):
    """One exact existing body/two descriptors; no CPP or general macro evaluator."""
    p=json.loads(profile_path.read_bytes());source=source_path.read_text();contract=p['clone_cpuid_origin_reference']
    # Canonical historical DEBUG_PRINT_SC block is inactive in this pinned command.
    # Recognize that one literal block; never generally evaluate C preprocessor input.
    block='#ifdef DEBUG_PRINT_SC\n#undef DDEBUG_DEFAULT\n#define DDEBUG_DEFAULT DDEBUG_PRINT\n#endif'
    if source.count(block)!=1:raise ValueError('historical debug selector block changed')
    command=next(r for r in p['exact_commands'] if r['stage']=='selected x86 syscall object')
    if any('DEBUG_PRINT_SC' in arg for arg in command['argv']):raise ValueError('debug selector command override')
    checked=source.replace(block,'',1)
    if re.search(r'^\s*#\s*(?:define|undef)\s+DEBUG_PRINT_SC\b',checked,re.M):raise ValueError('debug selector source override')
    if re.search(r'^\s*#\s*(?:define|undef)\s+(?:__LINE__|dkprintf|DDEBUG_DEFAULT|DDEBUG_NONE)\b',checked,re.M):
        raise ValueError('clone descriptor macro override unsupported')
    header=source_path.parents[3]/'lib/include/ihk/debug.h'
    if hashlib.sha256(header.read_bytes()).hexdigest()!=contract['debug_header_sha256']:
        raise ValueError('genuine defining Ddebug header changed')
    text=header.read_text()
    if '#define DDEBUG_NONE  0x0' not in text or '#define DDEBUG_DEFAULT DDEBUG_NONE' not in text:
        raise ValueError('unqualified initial debug flags')
    signature='int obtain_clone_cpuid(cpu_set_t *cpu_set, int use_last) {'
    if source.count(signature)!=1:raise ValueError('one exact C fallback body required')
    start=source.index(signature);depth=0;end=None
    for i in range(source.index('{',start),len(source)):
        if source[i]=='{':depth+=1
        elif source[i]=='}':
            depth-=1
            if depth==0:end=i+1;break
    body=source[start:end]+'\n'
    if hashlib.sha256(body.encode()).hexdigest()!=contract['original_body_sha256']:
        raise ValueError('qualified full body changed')
    before=source[:start].splitlines();logical=1
    for line in before:
        match=re.fullmatch(r'\s*#line\s+(\d+)\s*',line)
        logical=int(match.group(1)) if match else logical+1
    slots=[]
    for offset,line in enumerate(body.splitlines()):
        if 'dkprintf(' in line:
            slots.append(dict(file_utf8=origin,function_utf8='obtain_clone_cpuid',fmt=None,line=logical+offset,flags=0,line_flags=(logical+offset)&0xffffff,bytes=32,alignment=8))
    if slots!=contract['retained_C_metadata']:raise ValueError('genuine retained C descriptor identity changed')
    return slots


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", type=Path, required=True)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    origin, command = derive(args.profile, args.source)
    clone_slots = derive_clone_cpuid(args.profile, args.source, origin)
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
    metadata_path = args.output / "f06_clone_cpuid_metadata.rs"
    metadata_path.write_text(
        "// Functional OS only; no security testing. Generated from exact C origin/body/retained descriptors.\n"
        f"const F06_CLONE_CPU_SAMPLE_LINE_FLAGS: u32 = {clone_slots[0]['line_flags']};\n"
        f"const F06_CLONE_CPU_CHOICE_LINE_FLAGS: u32 = {clone_slots[1]['line_flags']};\n")
    with (args.output / "f06_rt_sigreturn_origin.cmake").open("a") as stream:
        stream.write(f"set(MCKERNEL_F06_CLONE_CPUID_METADATA_RS {json.dumps(str(metadata_path))})\n")
    (args.output / "rust-environment.json").write_text(json.dumps(
        {"MCKERNEL_F06_RT_SIGRETURN_ORIGIN": origin,
         "MCKERNEL_F06_CLONE_CPUID_METADATA_RS": str(metadata_path)}, indent=2) + "\n")
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
        "clone_cpuid_debug_slots": clone_slots,
        "compiled_Rust_metadata_qualification": None,
    }, indent=2) + "\n")


if __name__ == "__main__":
    main()
