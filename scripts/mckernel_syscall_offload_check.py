#!/usr/bin/env python3
"""Verify production ownership and composition of the syscall-offload tranche."""

import argparse
import hashlib
import json
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path


COMMIT_RE = re.compile(r"^[0-9a-fA-F]{40}$")
RUST_DEFINITIONS = (
    "send_syscall",
    "syscall_generic_forwarding",
    "syscall_offload_wait_reply",
    "syscall_request_publish_result",
)
C_IMPORTS = (
    "send_syscall",
    "syscall_generic_forwarding",
    "syscall_offload_wait_reply",
)
C_RETAINED_DEFINITIONS = (
    "do_syscall",
    "syscall_dispatch_context_bridge",
)
RUST_REQUIRED_IMPORTS = (
    "do_syscall",
    "check_sig_pending",
    "schedule",
    "ihk_mc_get_numa_node_by_distance",
    "syscall_dispatch_context_bridge",
)
UNDEFINED_TYPES = {"U", "u", "w", "v"}


def parse_nm(text):
    symbols = defaultdict(list)
    for line_no, line in enumerate(text.splitlines(), 1):
        parts = line.split()
        if not parts or (len(parts) == 1 and parts[0].endswith(":")):
            continue
        if len(parts) == 2:
            symbol_type, name = parts
        elif len(parts) >= 3:
            symbol_type, name = parts[-2:]
        else:
            raise ValueError("nm line {} is malformed".format(line_no))
        if len(symbol_type) != 1 or not symbol_type.isalpha():
            raise ValueError(
                "nm line {} has invalid symbol type {}".format(
                    line_no, symbol_type
                )
            )
        symbols[name].append(symbol_type)
    if not symbols:
        raise ValueError("nm reported no global symbols")
    return dict(symbols)


def _types(table, symbol):
    return table.get(symbol, [])


def _require_single_text_definition(table, symbol, artifact):
    types = _types(table, symbol)
    if types != ["T"]:
        raise ValueError(
            "{} must contain exactly one global text definition for {}; found {}".format(
                artifact, symbol, types or "none"
            )
        )


def _require_import(table, symbol, artifact):
    types = _types(table, symbol)
    if types != ["U"]:
        raise ValueError(
            "{} must contain exactly one undefined import for {}; found {}".format(
                artifact, symbol, types or "none"
            )
        )


def _reject_definition(table, symbol, artifact):
    defined = [kind for kind in _types(table, symbol) if kind not in UNDEFINED_TYPES]
    if defined:
        raise ValueError(
            "{} unexpectedly defines {} with symbol type(s) {}".format(
                artifact, symbol, defined
            )
        )


def check_contract(rust_symbols, c_symbols, image_symbols):
    for symbol in RUST_DEFINITIONS:
        _require_single_text_definition(rust_symbols, symbol, "mckernel_rust.o")
        _require_single_text_definition(image_symbols, symbol, "mckernel.img")
    for symbol in RUST_REQUIRED_IMPORTS:
        _require_import(rust_symbols, symbol, "mckernel_rust.o")
    for symbol in C_IMPORTS:
        _reject_definition(c_symbols, symbol, "syscall.c.o")
        _require_import(c_symbols, symbol, "syscall.c.o")
    for symbol in C_RETAINED_DEFINITIONS:
        _require_single_text_definition(c_symbols, symbol, "syscall.c.o")
        _require_single_text_definition(image_symbols, symbol, "mckernel.img")
    for symbol in RUST_DEFINITIONS + C_RETAINED_DEFINITIONS:
        if any(kind in UNDEFINED_TYPES for kind in _types(image_symbols, symbol)):
            raise ValueError("mckernel.img leaves {} unresolved".format(symbol))


def run_nm(nm, path, global_only=True):
    command = [nm]
    if global_only:
        command.append("-g")
    command.append(str(path))
    try:
        result = subprocess.run(
            command,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
    except subprocess.CalledProcessError as exc:
        raise ValueError(
            "nm failed for {}: {}".format(path, exc.stderr.strip())
        ) from exc
    return parse_nm(result.stdout)


def sha256_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _symbol_evidence(table, symbols):
    return {symbol: table.get(symbol, []) for symbol in symbols}


def build_report(build_dir, source_commit, nm="nm"):
    if not COMMIT_RE.match(source_commit):
        raise ValueError("source commit must be an exact 40-hex Git object name")
    source_commit = source_commit.lower()
    build_dir = build_dir.resolve()
    artifacts = {
        "rust_object": build_dir / "kernel/rust/mckernel_rust.o",
        "c_syscall_object": (
            build_dir / "kernel/CMakeFiles/mckernel.img.dir/syscall.c.o"
        ),
        "image": build_dir / "kernel/mckernel.img",
    }
    for name, path in artifacts.items():
        if not path.is_file():
            raise ValueError("missing production {}: {}".format(name, path))

    rust_symbols = run_nm(nm, artifacts["rust_object"])
    c_symbols = run_nm(nm, artifacts["c_syscall_object"], global_only=False)
    image_symbols = run_nm(nm, artifacts["image"])
    check_contract(rust_symbols, c_symbols, image_symbols)

    return {
        "schema": "mckernel-syscall-offload-composition-v1",
        "source_commit": source_commit,
        "result": "PASS",
        "contract": {
            "rust_definitions": list(RUST_DEFINITIONS),
            "rust_imports": list(RUST_REQUIRED_IMPORTS),
            "c_imports": list(C_IMPORTS),
            "c_retained_definitions": list(C_RETAINED_DEFINITIONS),
            "final_image": "one resolved global text definition for every named symbol",
        },
        "artifacts": {
            name: {"path": str(path), "sha256": sha256_file(path)}
            for name, path in artifacts.items()
        },
        "symbol_evidence": {
            "rust_object": _symbol_evidence(
                rust_symbols, RUST_DEFINITIONS + RUST_REQUIRED_IMPORTS
            ),
            "c_syscall_object": _symbol_evidence(
                c_symbols, C_IMPORTS + C_RETAINED_DEFINITIONS
            ),
            "image": _symbol_evidence(
                image_symbols, RUST_DEFINITIONS + C_RETAINED_DEFINITIONS
            ),
        },
    }


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build-dir", required=True, type=Path)
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--nm", default="nm")
    parser.add_argument("--output", type=Path)
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    try:
        report = build_report(args.build_dir, args.source_commit, nm=args.nm)
        rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(rendered, encoding="utf-8")
        print(rendered, end="")
    except (OSError, ValueError) as exc:
        print("error: {}".format(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
