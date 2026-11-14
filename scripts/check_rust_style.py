#!/usr/bin/env python3
"""Check explicitly named, tracked McKernel runtime Rust files without writing them.

Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Use only after the coordinator grants the ordinary formatter slot. No traversal
of a crate's module children, automatic file discovery, compiler or cargo calls.
"""

import argparse
import difflib
from pathlib import Path
import re
import subprocess
import sys


SOURCE_ROOTS = (
    "kernel/rust",
    "host-kernel/native-rust",
    "executer/kernel/mcctrl/rust",
    "executer/user/rust",
    "tools/crash/rust",
    "tools/mcstat/rust",
)
EXCLUDED_PARTS = {"tests", "fixtures", "generated", "vendor", "third_party"}
GENERATED = re.compile(rb"@generated|auto[- ]generated|automatically generated", re.I)


def source_path(repo, name):
    relative = Path(name)
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError("use a repository-relative file path: " + name)
    relative = Path(*relative.parts)
    if relative.suffix != ".rs" or not any(
        relative.is_relative_to(root) for root in map(Path, SOURCE_ROOTS)
    ):
        raise ValueError("outside the canonical runtime Rust scope: " + name)
    if EXCLUDED_PARTS.intersection(relative.parts):
        raise ValueError("fixture/generated/vendor paths need their owner's workflow: " + name)
    path = repo / relative
    if not path.is_file() or any(part.is_symlink() for part in (path, *path.parents)):
        raise ValueError("source must be an existing regular file without symlink parents: " + name)
    tracked = subprocess.run(
        ["git", "-C", str(repo), "ls-files", "--error-unmatch", "--", relative.as_posix()],
        stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, check=False,
    )
    if tracked.returncode:
        raise ValueError("source must be tracked in this repository: " + name)
    data = path.read_bytes()
    if GENERATED.search(data[:4096]):
        raise ValueError("generated source needs its generator workflow: " + name)
    data.decode("utf-8")
    return relative.as_posix(), data


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--rustfmt", type=Path, required=True,
                        help="absolute path to the coordinator-selected Rust 1.92.0 formatter")
    parser.add_argument("--edition", required=True, choices=["2015", "2018", "2021", "2024"],
                        help="the selected target's existing edition; never infer an upgrade")
    parser.add_argument("files", nargs="+", help="explicit repository-relative .rs paths")
    args = parser.parse_args()
    try:
        repo = args.repo.resolve(strict=True)
        config = repo / "config" / "rustfmt.toml"
        if not config.is_file():
            raise ValueError("missing project configuration: " + str(config))
        if not args.rustfmt.is_absolute() or not args.rustfmt.is_file():
            raise ValueError("--rustfmt must name an existing absolute executable path")
        # Validate the full selection before invoking any formatter.
        selected = [source_path(repo, name) for name in dict.fromkeys(args.files)]
        version = subprocess.run([str(args.rustfmt), "--version"], capture_output=True,
                                 check=True, timeout=10)
        if version.stderr or not re.fullmatch(rb"rustfmt 1\.8\.0-stable[^\r\n]*\r?\n?", version.stdout):
            raise ValueError("expected rustfmt 1.8.0-stable from the pinned Rust 1.92.0 toolchain")
        print("Functional McKernel OS/apps and Rust/assembly migration only; no security testing.")
        print(version.stdout.decode().strip())
        different = False
        for name, original in selected:
            # Upstream Rust 1.92.0 rustfmt disables external module traversal for
            # stdin. Passing file paths would recursively visit child modules.
            result = subprocess.run(
                [str(args.rustfmt), "--edition", args.edition, "--emit", "stdout",
                 "--config-path", str(config)],
                input=original, capture_output=True, cwd=repo, timeout=60, check=False,
            )
            if result.returncode or result.stderr:
                # A zero exit plus an ignored unstable-option warning is not a pass.
                sys.stderr.write("formatter diagnostic for " + name + ":\n")
                sys.stderr.write(result.stderr.decode("utf-8", errors="replace"))
                return 2
            if result.stdout != original:
                different = True
                sys.stdout.writelines(difflib.unified_diff(
                    original.decode("utf-8").splitlines(keepends=True),
                    result.stdout.decode("utf-8").splitlines(keepends=True),
                    fromfile="a/" + name, tofile="b/" + name,
                ))
            else:
                print("PASS " + name)
        return int(different)
    except (OSError, ValueError, UnicodeError, subprocess.SubprocessError) as error:
        print("style check stopped: " + str(error), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
