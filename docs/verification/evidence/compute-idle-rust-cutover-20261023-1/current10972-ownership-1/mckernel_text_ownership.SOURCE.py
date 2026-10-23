#!/usr/bin/env python3
"""Measure linked x86_64 McKernel executable-text ownership by source language.

The metric is intentionally narrow: GNU ``nm``-sized T/t symbols in the final
guest ELF are attributed from each symbol start with ``addr2line``.  Rust and C
are the scored denominator; assembly and unknown sources are reported but are
not silently assigned to either language.
"""

import argparse
import hashlib
import json
import subprocess
from collections import Counter
from pathlib import Path


TEXT_TYPES = {"T", "t"}


def run_checked(argv):
    return subprocess.run(
        argv,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
    ).stdout


def parse_nm(text):
    symbols = []
    for line_no, line in enumerate(text.splitlines(), 1):
        parts = line.split(None, 3)
        if len(parts) != 4 or parts[2] not in TEXT_TYPES:
            continue
        try:
            size = int(parts[1], 16)
        except ValueError as exc:
            raise ValueError(f"nm line {line_no}: invalid hexadecimal size") from exc
        if size == 0:
            continue
        symbols.append({"address": parts[0], "size": size, "name": parts[3]})
    if not symbols:
        raise ValueError("nm reported no non-empty T/t symbols")
    return symbols


def source_path(location):
    if location in {"??:0", "??:?", "??"}:
        return "??"
    path, separator, _line = location.rpartition(":")
    return path if separator else location


def classify_source(path):
    lowered = path.lower()
    if lowered.endswith(".rs"):
        return "rust"
    if lowered.endswith(".c"):
        return "c"
    if lowered.endswith((".s", ".asm")):
        return "assembly"
    return "other"


def repo_relative_source(path, repo):
    if path == "??":
        return path
    source = Path(path)
    if source.is_absolute():
        try:
            return source.resolve().relative_to(repo.resolve()).as_posix()
        except ValueError:
            parts = source.parts
            repo_indices = [index for index, part in enumerate(parts) if part == repo.name]
            if repo_indices:
                candidate = Path(*parts[repo_indices[-1] + 1 :])
                if candidate.parts and candidate.parts[0] in {
                    "arch",
                    "executer",
                    "ihk",
                    "kernel",
                    "lib",
                    "scripts",
                    "tools",
                }:
                    return candidate.as_posix()
            return source.as_posix()
    return source.as_posix()


def attribute_symbols(image, symbols, addr2line, repo, batch_size=1000):
    locations = []
    for start in range(0, len(symbols), batch_size):
        batch = symbols[start : start + batch_size]
        output = run_checked(
            [addr2line, "-e", str(image), "-f", "-C"]
            + [symbol["address"] for symbol in batch]
        ).splitlines()
        if len(output) != 2 * len(batch):
            raise RuntimeError(
                "addr2line returned {} lines for {} symbols".format(
                    len(output), len(batch)
                )
            )
        locations.extend(output[1::2])

    attributed = []
    for symbol, location in zip(symbols, locations):
        source = repo_relative_source(source_path(location), repo)
        language = classify_source(source)
        attributed.append(
            {
                **symbol,
                "source": source,
                "language": language,
            }
        )
    return attributed


def summarize_attribution(attributed):
    """Count each address/size span once so aliases cannot inflate ownership."""
    raw_language_bytes = Counter()
    by_span = {}
    duplicate_spans = []
    for entry in attributed:
        raw_language_bytes[entry["language"]] += entry["size"]
        key = (int(entry["address"], 16), entry["size"])
        previous = by_span.get(key)
        if previous is None:
            by_span[key] = entry
            continue
        if (
            previous["language"] != entry["language"]
            or previous["source"] != entry["source"]
        ):
            raise ValueError(
                "aliased text span has conflicting source attribution: "
                f"{entry['address']}+{entry['size']}"
            )

    counts = Counter((int(entry["address"], 16), entry["size"]) for entry in attributed)
    for (address, size), count in sorted(counts.items()):
        if count > 1:
            duplicate_spans.append(
                {"address": f"{address:x}", "size": size, "symbols": count}
            )

    language_bytes = Counter()
    source_bytes = Counter()
    for entry in by_span.values():
        language_bytes[entry["language"]] += entry["size"]
        source_bytes[entry["source"]] += entry["size"]
    return language_bytes, raw_language_bytes, source_bytes, duplicate_spans


def sha256_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def git_commit(repo):
    try:
        return run_checked(["git", "-C", str(repo), "rev-parse", "HEAD"]).strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def build_report(image, repo, nm="nm", addr2line="addr2line"):
    nm_text = run_checked(
        [nm, "-S", "--defined-only", "--radix=x", str(image)]
    )
    symbols = parse_nm(nm_text)
    attributed = attribute_symbols(image, symbols, addr2line, repo)
    language_bytes, raw_language_bytes, source_bytes, overlaps = summarize_attribution(
        attributed
    )
    rust_bytes = language_bytes["rust"]
    c_bytes = language_bytes["c"]
    scored_bytes = rust_bytes + c_bytes
    if scored_bytes == 0:
        raise ValueError("no Rust or C executable-text bytes were attributed")

    return {
        "schema": "mckernel-symbol-source-attribution-v1",
        "metric_scope": "alias-deduplicated final guest ELF defined T/t symbol spans",
        "denominator": "Rust plus C bytes; assembly and other excluded",
        "method": "nm -S --defined-only --radix=x; symbol-start addr2line -f -C",
        "commit": git_commit(repo),
        "image": str(image),
        "image_sha256": sha256_file(image),
        "symbol_count": len(symbols),
        "unique_symbol_span_count": len(symbols) - sum(
            entry["symbols"] - 1 for entry in overlaps
        ),
        "language_bytes": {
            language: language_bytes[language]
            for language in ("rust", "c", "assembly", "other")
        },
        "raw_symbol_bytes_before_alias_deduplication": {
            language: raw_language_bytes[language]
            for language in ("rust", "c", "assembly", "other")
        },
        "scored_bytes": scored_bytes,
        "rust_percent": 100.0 * rust_bytes / scored_bytes,
        "duplicate_symbol_spans": overlaps,
        "source_bytes": [
            {"source": source, "bytes": size, "language": classify_source(source)}
            for source, size in sorted(
                source_bytes.items(), key=lambda item: (-item[1], item[0])
            )
        ],
    }


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", required=True, type=Path)
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--nm", default="nm")
    parser.add_argument("--addr2line", default="addr2line")
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def main():
    args = parse_args()
    image = args.image.resolve()
    repo = args.repo.resolve()
    report = build_report(image, repo, nm=args.nm, addr2line=args.addr2line)
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")


if __name__ == "__main__":
    main()
