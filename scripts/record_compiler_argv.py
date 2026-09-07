#!/usr/bin/env python3
"""Atomically record a compiler argv, then replace this process with it."""

import argparse
import json
import os
import tempfile
from pathlib import Path
from typing import Optional, Sequence


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args(argv)
    if args.command[:1] == ["--"]:
        args.command = args.command[1:]
    if not args.command or any(not item or "\x00" in item for item in args.command):
        parser.error("a non-empty compiler argv is required after --")
    return args


def write_argv(path: Path, command: Sequence[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = (json.dumps(command, ensure_ascii=True, separators=(",", ":")) + "\n").encode(
        "utf-8"
    )
    descriptor, temporary = tempfile.mkstemp(prefix=path.name + ".", dir=str(path.parent))
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temporary, 0o644)
        os.replace(temporary, path)
    except BaseException:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    write_argv(args.output, args.command)
    os.execvpe(args.command[0], args.command, os.environ.copy())
    raise AssertionError("os.execvpe returned")


if __name__ == "__main__":
    raise SystemExit(main())
