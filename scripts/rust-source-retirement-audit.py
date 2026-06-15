#!/usr/bin/env python3
"""Audit McKernel strict Rust source-retirement progress.

This gate tracks source retirement, not functional helper ownership.  It is
intended to run in two phases:

* Active campaign phase: fail on malformed tracker rows, untracked
  McKernel-owned C/header files, and already-retired rows that re-enter the
  strict Rust build graph, while reporting remaining tracked debt. Headers
  explicitly tracked as n/a are allowlisted compatibility or external
  boundaries and are not part of the executable-header debt count.
* Enforced/final phase: additionally fail when any scored C/header debt
  remains, when executable header logic remains, or when a strict Rust build
  compiles a non-allowlisted McKernel-owned C implementation object.
"""

import argparse
import json
import re
import sys
from collections import Counter, defaultdict, namedtuple
from pathlib import Path


DEFAULT_ROOTS = ("kernel", "arch/x86_64", "ihk", "executer", "tools", "lib")
SOURCE_SUFFIXES = {".c", ".h"}

SKIP_DIR_NAMES = {
    ".git",
    ".hg",
    ".svn",
    "__pycache__",
    "CMakeFiles",
    ".tmp_versions",
    "target",
}

EXTERNAL_PREFIXES = (
    "executer/user/lib/libdwarf/",
    "executer/user/lib/syscall_intercept/",
    "executer/user/lib/uti/contrib/",
)

TEST_PREFIXES = (
    "arch/x86_64/elfboot/test",
    "ihk/test/",
    "kernel/rust/tests/",
    "test/",
)

GENERATED_RE = re.compile(r"(^|/)(dwarf_names|.*generated.*)\.(c|h)$")
TRACKER_ROW_RE = re.compile(r"^\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|")
FUNCTION_MACRO_RE = re.compile(r"^\s*#\s*define\s+[A-Za-z_][A-Za-z0-9_]*\(")
INLINE_RE = re.compile(
    r"\b(static\s+(?:__always_inline\s+)?(?:inline|__inline__|__inline)\b|"
    r"extern\s+(?:inline|__inline__|__inline)\b)"
)
C_PATH_RE = re.compile(r"(?P<path>(?:/|\.\.?/)[^\s'\"\\]+\.c)\b")
OBJ_PATH_RE = re.compile(r"(?P<path>(?:/|\.\.?/)[^\s'\"\\;]+\.o)\b")
CMD_TARGET_RE = re.compile(r"^cmd_(?P<target>.+?)\s*:=", re.MULTILINE)


TrackerRow = namedtuple("TrackerRow", ("path", "category", "completion"))
BuildSource = namedtuple("BuildSource", ("path", "source"))


def relpath(path, repo):
    return path.resolve().relative_to(repo).as_posix()


def is_arm_path(rel):
    return rel.startswith("arch/arm64/") or "/arm64/" in rel


def is_skipped(rel):
    parts = set(rel.split("/"))
    if parts & SKIP_DIR_NAMES:
        return True
    if is_arm_path(rel):
        return True
    if any(rel.startswith(prefix) for prefix in EXTERNAL_PREFIXES):
        return True
    if any(rel.startswith(prefix) for prefix in TEST_PREFIXES):
        return True
    if GENERATED_RE.search(rel):
        return True
    return False


def parse_completion(value):
    text = value.strip()
    if text == "n/a":
        return None
    if not text.endswith("%"):
        raise ValueError("completion is neither percent nor n/a: {}".format(value))
    return float(text[:-1])


def parse_tracker(path):
    rows = {}
    errors = []
    with path.open("r", encoding="utf-8") as fh:
        for line_no, line in enumerate(fh, 1):
            match = TRACKER_ROW_RE.match(line)
            if not match:
                continue
            file_path, category, completion = (part.strip() for part in match.groups())
            if file_path in ("File", "---") or file_path.startswith("+"):
                continue
            if not (file_path.endswith(".c") or file_path.endswith(".h")):
                continue
            try:
                parsed = parse_completion(completion)
            except ValueError as exc:
                errors.append("{}:{}: {}".format(path, line_no, exc))
                continue
            if file_path in rows:
                errors.append("{}:{}: duplicate tracker row: {}".format(path, line_no, file_path))
                continue
            rows[file_path] = TrackerRow(file_path, category, parsed)
    return rows, errors


def iter_in_scope_sources(repo, roots):
    for root_name in roots:
        root = repo / root_name
        if not root.exists():
            continue
        paths = [root] if root.is_file() else root.rglob("*")
        for path in paths:
            if not path.is_file() or path.suffix not in SOURCE_SUFFIXES:
                continue
            try:
                rel = relpath(path, repo)
            except ValueError:
                continue
            if is_skipped(rel):
                continue
            yield rel


def executable_header_hits(path):
    hits = []
    try:
        lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    except OSError as exc:
        return [("read-error", 0, str(exc))]

    for line_no, line in enumerate(lines, 1):
        if INLINE_RE.search(line):
            hits.append(("inline", line_no, line.strip()))
        elif FUNCTION_MACRO_RE.search(line):
            hits.append(("macro", line_no, line.strip()))
    return hits


def load_compile_commands(build_dir):
    compile_commands = build_dir / "compile_commands.json"
    if not compile_commands.exists():
        return []
    try:
        data = json.loads(compile_commands.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError("{}: {}".format(compile_commands, exc))

    sources = []
    for entry in data:
        file_value = entry.get("file")
        if not file_value:
            continue
        sources.append(BuildSource(Path(file_value), str(compile_commands)))
    return sources


def load_kbuild_cmd_sources(build_dir):
    active_objects = active_kbuild_objects(build_dir)
    sources = []
    for cmd_file in build_dir.rglob("*.cmd"):
        try:
            text = cmd_file.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        target = kbuild_cmd_target(text, build_dir)
        if target is not None and active_objects and target not in active_objects:
            continue
        for match in C_PATH_RE.finditer(text):
            sources.append(BuildSource(Path(match.group("path")), str(cmd_file)))
    return sources


def kbuild_cmd_target(text, build_dir):
    match = CMD_TARGET_RE.search(text)
    if not match:
        return None
    return normalize_build_path(Path(match.group("target")), build_dir)


def normalize_build_path(path, build_dir):
    if path.is_absolute():
        return path.resolve()
    return (build_dir / path).resolve()


def active_kbuild_objects(build_dir):
    active = set()
    for cmd_file in build_dir.rglob("*.cmd"):
        try:
            text = cmd_file.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        if " -r -o " not in text or " := ld " not in text:
            continue
        for match in OBJ_PATH_RE.finditer(text):
            active.add(normalize_build_path(Path(match.group("path")), build_dir))
    return active


def load_cmake_make_sources(build_dir):
    sources = []
    for make_file in build_dir.rglob("build.make"):
        try:
            text = make_file.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for match in C_PATH_RE.finditer(text):
            sources.append(BuildSource(Path(match.group("path")), str(make_file)))
    return sources


def build_sources(build_dir):
    if not build_dir:
        return []
    sources = load_compile_commands(build_dir)
    sources.extend(load_cmake_make_sources(build_dir))
    sources.extend(load_kbuild_cmd_sources(build_dir))
    return sources


def row_state(row):
    if row.completion is None:
        return "allowlisted"
    if row.completion >= 100.0:
        return "retired"
    return "debt"


def category_progress(category_rows):
    progress = []
    total_scored = 0
    total_completion = 0.0

    for category, rows in sorted(category_rows.items()):
        scored = [row.completion for row in rows if row.completion is not None]
        zero = sum(1 for value in scored if value == 0.0)
        retired = sum(1 for value in scored if value >= 100.0)
        partial = len(scored) - zero - retired
        completion = None
        left = None
        if scored:
            completion = sum(scored) / len(scored)
            left = 100.0 - completion
            total_scored += len(scored)
            total_completion += sum(scored)
        progress.append({
            "category": category,
            "rows": len(rows),
            "scored": len(scored),
            "zero": zero,
            "partial": partial,
            "retired": retired,
            "allowlisted": len(rows) - len(scored),
            "completion": completion,
            "left": left,
        })

    overall_completion = None
    overall_left = None
    if total_scored:
        overall_completion = total_completion / total_scored
        overall_left = 100.0 - overall_completion

    return progress, overall_completion, overall_left


def format_percent(value):
    if value is None:
        return "n/a"
    return "{:.1f}%".format(value)


def print_category_progress(progress, overall_completion, overall_left):
    category_width = max([len("Category")] + [len(row["category"]) for row in progress])
    line = (
        "+-{cat}-+------+--------+------+---------+------+-----+------------+-------+"
        .format(cat="-" * category_width)
    )
    print("  category completion:")
    print("  " + line)
    print(
        "  | {cat:<{catw}} | Rows | Scored | 0.0% | Partial | 100% | n/a | Completion |  Left |"
        .format(cat="Category", catw=category_width)
    )
    print("  " + line)
    for row in progress:
        print(
            "  | {cat:<{catw}} | {rows:4d} | {scored:6d} | {zero:4d} | {partial:7d} |"
            " {retired:4d} | {allowlisted:3d} | {completion:>10} | {left:>5} |"
            .format(
                cat=row["category"],
                catw=category_width,
                rows=row["rows"],
                scored=row["scored"],
                zero=row["zero"],
                partial=row["partial"],
                retired=row["retired"],
                allowlisted=row["allowlisted"],
                completion=format_percent(row["completion"]),
                left=format_percent(row["left"]),
            )
        )
    print("  " + line)
    print("  overall scored completion: {}".format(format_percent(overall_completion)))
    print("  Total percentage points left: {}".format(format_percent(overall_left)))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=".", help="repository root")
    parser.add_argument("--tracker", default="rust-source-retirement.txt")
    parser.add_argument("--root", action="append", dest="roots", help="source root to scan")
    parser.add_argument("--build-dir", help="strict Rust build directory to inspect")
    parser.add_argument("--enforce-category", action="append", default=[], metavar="CATEGORY")
    parser.add_argument("--fail-on-unretired", action="store_true")
    parser.add_argument("--fail-on-executable-headers", action="store_true")
    parser.add_argument("--fail-on-compiled-c", action="store_true")
    parser.add_argument("--fail-on-retired-compiled-c", action="store_true")
    parser.add_argument("--json", action="store_true", help="print machine-readable summary")
    args = parser.parse_args()

    repo = Path(args.repo).resolve()
    tracker_path = Path(args.tracker)
    if not tracker_path.is_absolute():
        tracker_path = repo / tracker_path
    roots = args.roots if args.roots else list(DEFAULT_ROOTS)
    build_dir = Path(args.build_dir).resolve() if args.build_dir else None

    tracker, errors = parse_tracker(tracker_path)
    in_scope = sorted(set(iter_in_scope_sources(repo, roots)))
    scanned_set = set(in_scope)

    tracked_existing = {path for path in tracker if (repo / path).exists()}
    untracked = [path for path in in_scope if path not in tracker]
    stale = [path for path in tracker if not (repo / path).exists()]

    category_counts = defaultdict(Counter)
    category_rows = defaultdict(list)
    debt_rows = []
    allowlisted_rows = []
    for rel in sorted(scanned_set & set(tracker)):
        row = tracker[rel]
        state = row_state(row)
        category_counts[row.category][state] += 1
        category_rows[row.category].append(row)
        if state == "debt":
            debt_rows.append(row)
        elif state == "allowlisted":
            allowlisted_rows.append(row)

    header_hits = {}
    for rel in in_scope:
        if not rel.endswith(".h"):
            continue
        row = tracker.get(rel)
        if row is not None and row_state(row) == "allowlisted":
            continue
        hits = executable_header_hits(repo / rel)
        if hits:
            header_hits[rel] = hits

    compiled_c = []
    compiled_seen = set()
    for source in build_sources(build_dir):
        source_path = source.path
        if not source_path.is_absolute():
            source_path = (build_dir / source_path).resolve() if build_dir else source_path.resolve()
        if source_path.suffix != ".c":
            continue
        try:
            rel = relpath(source_path, repo)
        except ValueError:
            continue
        if is_skipped(rel):
            continue
        row = tracker.get(rel)
        if row is None or row_state(row) != "allowlisted":
            key = (rel, source.source)
            if key not in compiled_seen:
                compiled_seen.add(key)
                compiled_c.append(BuildSource(rel, source.source))

    enforced_categories = set(args.enforce_category)
    category_debt = [
        row for row in debt_rows if row.category in enforced_categories
    ]
    category_header_hits = {
        rel: hits for rel, hits in header_hits.items()
        if tracker.get(rel) and tracker[rel].category in enforced_categories
    }
    category_compiled_c = [
        item for item in compiled_c
        if tracker.get(item.path) and tracker[item.path].category in enforced_categories
    ]
    retired_compiled_c = [
        item for item in compiled_c
        if tracker.get(item.path) and row_state(tracker[item.path]) == "retired"
    ]
    progress, overall_completion, overall_left = category_progress(category_rows)

    if untracked:
        errors.append("untracked in-scope non-Rust files remain: {}".format(len(untracked)))
    if args.fail_on_unretired and debt_rows:
        errors.append("tracked source-retirement debt remains: {}".format(len(debt_rows)))
    if args.fail_on_executable_headers and header_hits:
        errors.append("headers with executable inline/macro logic remain: {}".format(len(header_hits)))
    if args.fail_on_compiled_c and compiled_c:
        errors.append("strict Rust build compiles non-allowlisted C sources: {}".format(len(compiled_c)))
    if args.fail_on_retired_compiled_c and retired_compiled_c:
        errors.append(
            "strict Rust build compiles retired source-retirement rows: {}".format(
                len(retired_compiled_c)
            )
        )
    if category_debt:
        errors.append(
            "source-retirement debt remains in enforced categories: {}".format(
                len(category_debt)
            )
        )
    if category_header_hits:
        errors.append(
            "executable headers remain in enforced categories: {}".format(
                len(category_header_hits)
            )
        )
    if category_compiled_c:
        errors.append(
            "compiled non-allowlisted C remains in enforced categories: {}".format(
                len(category_compiled_c)
            )
        )

    summary = {
        "tracked_files": len(tracker),
        "tracked_existing_files": len(tracked_existing),
        "in_scope_files": len(in_scope),
        "untracked_files": untracked[:50],
        "stale_tracker_rows": stale[:50],
        "debt_rows": len(debt_rows),
        "allowlisted_rows": len(allowlisted_rows),
        "headers_with_executable_logic": len(header_hits),
        "compiled_non_allowlisted_c": len(compiled_c),
        "compiled_retired_c": len(retired_compiled_c),
        "category_counts": {
            category: dict(counts) for category, counts in sorted(category_counts.items())
        },
        "category_progress": progress,
        "overall_scored_completion": overall_completion,
        "total_percentage_points_left": overall_left,
    }

    if args.json:
        print(json.dumps(summary, indent=2, sort_keys=True))
    else:
        print("Rust source-retirement audit")
        print("  tracker: {}".format(tracker_path))
        print("  in-scope C/header files: {}".format(len(in_scope)))
        print("  tracked existing files: {}".format(len(tracked_existing)))
        print("  tracked debt rows: {}".format(len(debt_rows)))
        print("  allowlisted rows: {}".format(len(allowlisted_rows)))
        print("  headers with executable inline/macro logic: {}".format(len(header_hits)))
        if build_dir:
            print("  compiled non-allowlisted C sources: {}".format(len(compiled_c)))
            print("  compiled retired C sources: {}".format(len(retired_compiled_c)))
        print_category_progress(progress, overall_completion, overall_left)
        if stale:
            print("  stale tracker rows: {}".format(len(stale)))
        if untracked:
            print("  untracked examples:")
            for rel in untracked[:20]:
                print("    {}".format(rel))
        if debt_rows:
            print("  debt examples:")
            for row in debt_rows[:20]:
                print("    {} [{}] {:.1f}%".format(row.path, row.category, row.completion))
        if header_hits:
            print("  executable header examples:")
            for rel, hits in list(sorted(header_hits.items()))[:20]:
                kind, line_no, line = hits[0]
                print("    {}:{} {} {}".format(rel, line_no, kind, line[:100]))
        if compiled_c:
            print("  compiled C examples:")
            for item in compiled_c[:20]:
                print("    {} ({})".format(item.path, item.source))
        if retired_compiled_c:
            print("  compiled retired C examples:")
            for item in retired_compiled_c[:20]:
                print("    {} ({})".format(item.path, item.source))
        print("  Total percentage points left: {}".format(format_percent(overall_left)))

    if errors:
        for error in errors:
            print("error: {}".format(error), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
