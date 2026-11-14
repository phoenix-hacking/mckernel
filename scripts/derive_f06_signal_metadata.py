#!/usr/bin/env python3
"""Derive F06 signal diagnostics after the caller validates source/origin pins.

This is metadata generation only. It does not grant file or native acceptance.
All sites are taken from the retained complete C do_signal definition. Requiring
exact site counts prevents a new branch or changed allocation from disappearing.
"""
import hashlib
import json
from pathlib import Path
import re


def signal_body(source: str) -> tuple[str, int]:
    signature = "int\ndo_signal("
    if source.count(signature) != 1:
        raise ValueError("expected exactly one retained do_signal definition")
    start = source.index(signature)
    opening = source.index("{", start)
    depth, end = 1, opening + 1
    # Current pinned function has balanced braces in comments and string literals.
    # The source pin is validated by derive_f06_origin before calling this helper.
    while depth and end < len(source):
        depth += (source[end] == "{") - (source[end] == "}")
        end += 1
    if depth:
        raise ValueError("unclosed retained signal function")
    logical = 1
    for line in source[:start].splitlines():
        match = re.fullmatch(r"\s*#line\s+(\d+)\s*", line)
        logical = int(match.group(1)) if match else logical + 1
    return source[start:end], logical


def derive_signal_metadata(source: str, origin: str) -> dict[str, int]:
    if not re.fullmatch(r"/[A-Za-z0-9_./-]+", origin):
        raise ValueError("unsupported origin literal")
    body, first = signal_body(source)
    lines = body.splitlines()
    if any(re.match(r"\s*#\s*(?:line|\d)", line) for line in lines):
        raise ValueError("signal-body logical line overrides need independent review")

    def sites(needle: str, names: tuple[str, ...]) -> dict[str, int]:
        matches = [first + index for index, line in enumerate(lines) if needle in line]
        if len(matches) != len(names):
            raise ValueError(f"signal metadata site count changed for {needle!r}: {len(matches)}")
        return dict(zip(names, matches))

    result = sites("kfree_tracked(pending,", (
        "IGNORE_FREE_LINE", "LEGACY_XSAVE_OOM_PENDING_FREE_LINE",
        "LEGACY_XSAVE_COPY_PENDING_FREE_LINE", "LEGACY_FRAME_COPY_PENDING_FREE_LINE",
        "NATIVE_BAD_FRAME_PENDING_FREE_LINE", "HANDLER_PENDING_FREE_LINE",
        "DEFAULT_PENDING_FREE_LINE",
    ))
    result.update(sites("kfree_tracked(_kfpregs,", (
        "NATIVE_XSAVE_COPY_FREE_LINE", "LEGACY_XSAVE_COPY_FREE_LINE", "XSAVE_SUCCESS_FREE_LINE",
    )))
    result.update(sites("kfree_tracked(thread->ptrace_recvsig,", ("PTRACE_RECV_FREE_LINE",)))
    result.update(sites("kfree_tracked(thread->ptrace_sendsig,", ("PTRACE_SEND_FREE_LINE",)))
    result.update(sites("kmalloc_tracked(xsavesize + 64,", ("XSAVE_ALLOC_LINE",)))
    result.update(sites("kmalloc_tracked(sizeof(struct x86_user_context),", ("CORE_ALLOC_LINE",)))
    debug_sites = {
        'dkprintf("do_signal():': "ENTRY_LINE_FLAGS",
        'dkprintf("SIGSTOP():': "STOP_WAKE_LINE_FLAGS",
        'dkprintf("do_signal,SIGTRAP\\n': "TRAP_ENTER_LINE_FLAGS",
        'dkprintf("do_signal,SIGTRAP,sleeping': "TRAP_SLEEP_LINE_FLAGS",
        'dkprintf("SIGTRAP():': "TRAP_WAKE_LINE_FLAGS",
        'dkprintf("do_signal,default,terminate': "TERMINATE_LINE_FLAGS",
    }
    for needle, name in debug_sites.items():
        result.update(sites(needle, (name,)))
    if any(value <= 0 or value >= (1 << 24) for value in result.values()):
        raise ValueError("diagnostic line outside the original 24-bit representation")
    return {"F06_SIGNAL_" + name: value for name, value in result.items()}


def write_signal_metadata(source_path: Path, origin: str, output: Path) -> None:
    source = source_path.read_text()
    fields = derive_signal_metadata(source, origin)
    output.mkdir(parents=True, exist_ok=True)
    declarations = [
        "// Generated from the source validated by derive_f06_origin; no runtime authority.",
        f'const F06_SIGNAL_ORIGIN: &[u8] = b"{origin}\\0";',
    ]
    for name, value in sorted(fields.items()):
        kind = "u32" if name.endswith("FLAGS") else "i32"
        declarations.append(f"const {name}: {kind} = {value};")
    (output / "f06_signal_metadata.rs").write_text("\n".join(declarations) + "\n")
    (output / "f06_signal_metadata.json").write_text(json.dumps({
        "scope": "SOURCE_METADATA_ONLY_NO_RUNTIME_AUTHORITY",
        "source_sha256": hashlib.sha256(source_path.read_bytes()).hexdigest(),
        "origin": origin,
        "sites": fields,
    }, indent=2) + "\n")
