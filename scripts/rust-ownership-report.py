#!/usr/bin/env python3
"""Report mechanical Rust ownership for the active McKernel migration scope.

The report is intentionally conservative: Rust files count as Rust-owned,
assembly and public/header surfaces are reported as boundaries, and C files are
counted as implementation debt unless they are explicitly classified as tests,
generated/external code, or compatibility/layout-check boundaries.
"""

import argparse
import fnmatch
import json
import sys
from collections import defaultdict, namedtuple
from pathlib import Path


DEFAULT_ROOTS = ("kernel", "arch/x86_64", "ihk", "executer", "tools", "lib")
SOURCE_SUFFIXES = {".c", ".h", ".S", ".rs"}

SKIP_DIRS = {
    ".git",
    ".svn",
    ".hg",
    "__pycache__",
    "CMakeFiles",
    ".tmp_versions",
    "target",
}

EXTERNAL_PATTERNS = (
    "executer/user/lib/libdwarf/**",
    "executer/user/lib/syscall_intercept/**",
    "executer/user/lib/uti/contrib/**",
    "scripts/checkpatch.pl",
)

TEST_PATTERNS = (
    "kernel/rust/tests/**",
    "ihk/test/**",
    "arch/x86_64/elfboot/test*",
)

GENERATED_PATTERNS = (
    "**/*generated*",
    "**/dwarf_names*.c",
    "**/dwarf_names*.h",
)

ABI_BOUNDARY_PATTERNS = (
    "kernel/rust/abi_checks.c",
    "ihk/linux/core/abi_checks.c",
    "kernel/include/**",
    "arch/x86_64/kernel/include/**",
    "ihk/include/**",
    "ihk/**/include/**",
    "executer/kernel/mcctrl/include/**",
)

COMPAT_SHIM_PATTERNS = (
    "arch/x86_64/kboot/**",
    "arch/x86_64/elfboot/**",
)


AREA_PATTERNS = (
    (
        "ABI/layout foundation",
        (
            "kernel/rust/abi*",
            "kernel/rust/abi_checks.c",
            "ihk/linux/core/abi_checks.c",
        ),
    ),
    (
        "Page allocator",
        (
            "lib/page_alloc.c",
            "kernel/rust/page_alloc.rs",
            "kernel/rust/page_helpers.rs",
        ),
    ),
    (
        "Shared primitives",
        (
            "lib/**",
            "kernel/rbtree.c",
            "kernel/llist.c",
            "kernel/plist.c",
            "kernel/waitq.c",
            "kernel/rust/rbtree.rs",
            "kernel/rust/llist.rs",
            "kernel/rust/plist.rs",
            "kernel/rust/waitq.rs",
            "kernel/rust/bitmap.rs",
            "kernel/rust/bitops.rs",
            "kernel/rust/string.rs",
            "kernel/rust/numparse.rs",
        ),
    ),
    (
        "x86_64 memory management",
        (
            "kernel/mem.c",
            "kernel/rust/mem_helpers.rs",
            "arch/x86_64/kernel/memory*",
            "arch/x86_64/kernel/include/arch-memory*",
            "kernel/rust/x86_memory_helpers.rs",
        ),
    ),
    (
        "Process/VM management",
        (
            "kernel/process*",
            "kernel/include/process*",
            "kernel/rust/process_helpers.rs",
        ),
    ),
    (
        "Syscall core",
        (
            "kernel/syscall.c",
            "arch/x86_64/kernel/syscall.c",
            "kernel/include/syscall.h",
            "kernel/rust/syscall_policy.rs",
            "kernel/rust/shmid_helpers.rs",
            "kernel/rust/rlimit_helpers.rs",
        ),
    ),
    (
        "Scheduler/timers/wait/futex",
        (
            "kernel/futex.c",
            "kernel/sched_helpers.c",
            "kernel/timer.c",
            "kernel/waitq.c",
            "kernel/plist.c",
            "kernel/rust/sched_helpers.rs",
            "kernel/rust/waitq.rs",
            "kernel/rust/plist.rs",
        ),
    ),
    (
        "procfs/sysfs/xpmem/file objects",
        (
            "kernel/procfs.c",
            "kernel/sysfs.c",
            "kernel/xpmem.c",
            "kernel/*obj.c",
            "kernel/pager.c",
            "kernel/hugefileobj.c",
            "kernel/rust/object_helpers.rs",
            "kernel/rust/xpmem_helpers.rs",
        ),
    ),
    (
        "host/IKC/mcctrl/IHK modules",
        (
            "ihk/**",
            "executer/kernel/mcctrl/**",
        ),
    ),
    (
        "User tools",
        (
            "executer/user/**",
            "tools/**",
        ),
    ),
    (
        "Rust build/link foundation",
        (
            "cmake/**",
            "CMakeLists.txt",
            "scripts/**",
        ),
    ),
)

DASHBOARD_ROWS = (
    "Rust build/link foundation",
    "ABI/layout foundation",
    "Shared primitives",
    "x86_64 memory management",
    "Page allocator",
    "Process/VM management",
    "Syscall core",
    "Scheduler/timers/wait/futex",
    "procfs/sysfs/xpmem/file objects",
    "host/IKC/mcctrl/IHK modules",
    "User tools",
    "Rocky runtime integration",
    "arm64",
)

DASHBOARD_FUNCTIONAL_PERCENT = {
    "Rust build/link foundation": "95",
    "ABI/layout foundation": "46",
    "Shared primitives": "84",
    "x86_64 memory management": "27",
    "Page allocator": "34",
    "Process/VM management": "68",
    "Syscall core": "66",
    "Scheduler/timers/wait/futex": "31",
    "procfs/sysfs/xpmem/file objects": "100",
    "host/IKC/mcctrl/IHK modules": "61",
    "User tools": "83",
    "Rocky runtime integration": "82",
    "arm64": "deferred",
}


FileRecord = namedtuple("FileRecord", ("path", "area", "kind", "loc", "reason"))


class AreaTotals:
    def __init__(self):
        self.rust_loc = 0
        self.c_impl_loc = 0
        self.header_loc = 0
        self.asm_loc = 0
        self.boundary_loc = 0
        self.test_loc = 0
        self.external_loc = 0
        self.generated_loc = 0
        self.files = 0
        self.c_files = []


def relpath(path, root):
    return path.relative_to(root).as_posix()


def matches(path, patterns):
    return any(fnmatch.fnmatch(path, pattern) for pattern in patterns)


def area_for(path):
    for area, patterns in AREA_PATTERNS:
        if matches(path, patterns):
            return area
    return "Other in-scope code"


def count_loc(path):
    try:
        with path.open("rb") as fh:
            return sum(1 for line in fh if line.strip())
    except OSError:
        return 0


def classify(path, suffix):
    if matches(path, EXTERNAL_PATTERNS):
        return "external", "third-party/external"
    if matches(path, TEST_PATTERNS):
        return "test", "test or smoke source"
    if matches(path, GENERATED_PATTERNS):
        return "generated", "generated source"
    if suffix == ".rs":
        return "rust", "Rust-owned implementation"
    if suffix == ".S":
        return "asm", "required architecture assembly"
    if matches(path, ABI_BOUNDARY_PATTERNS):
        return "boundary", "public ABI/header/layout boundary"
    if matches(path, COMPAT_SHIM_PATTERNS):
        return "boundary", "boot/loader compatibility boundary"
    if suffix == ".h":
        return "header", "C header surface; audit macros/inline logic"
    if suffix == ".c":
        return "c_impl", "C implementation debt"
    return "other", ""


def iter_source_files(repo, roots, include_arm64):
    for root_name in roots:
        root = repo / root_name
        if not root.exists():
            continue
        if root.is_file():
            paths = [root]
        else:
            paths = root.rglob("*")
        for path in paths:
            if not path.is_file():
                continue
            parts = set(path.parts)
            if parts & SKIP_DIRS:
                continue
            rel = relpath(path, repo)
            if not include_arm64 and (rel.startswith("arch/arm64/") or "/arm64/" in rel):
                continue
            if path.suffix in SOURCE_SUFFIXES:
                yield path


def build_report(repo, roots, include_arm64):
    areas = defaultdict(AreaTotals)
    records = []

    for path in sorted(iter_source_files(repo, roots, include_arm64), key=lambda p: relpath(p, repo)):
        rel = relpath(path, repo)
        loc = count_loc(path)
        area = area_for(rel)
        kind, reason = classify(rel, path.suffix)
        record = FileRecord(rel, area, kind, loc, reason)
        records.append(record)

        totals = areas[area]
        totals.files += 1
        if kind == "rust":
            totals.rust_loc += loc
        elif kind == "c_impl":
            totals.c_impl_loc += loc
            totals.c_files.append(record)
        elif kind == "header":
            totals.header_loc += loc
        elif kind == "asm":
            totals.asm_loc += loc
        elif kind == "boundary":
            totals.boundary_loc += loc
        elif kind == "test":
            totals.test_loc += loc
        elif kind == "external":
            totals.external_loc += loc
        elif kind == "generated":
            totals.generated_loc += loc

    total = AreaTotals()
    for totals in areas.values():
        total.rust_loc += totals.rust_loc
        total.c_impl_loc += totals.c_impl_loc
        total.header_loc += totals.header_loc
        total.asm_loc += totals.asm_loc
        total.boundary_loc += totals.boundary_loc
        total.test_loc += totals.test_loc
        total.external_loc += totals.external_loc
        total.generated_loc += totals.generated_loc
        total.files += totals.files
        total.c_files.extend(totals.c_files)

    return {
        "repo": str(repo),
        "include_arm64": include_arm64,
        "roots": list(roots),
        "areas": {name: totals for name, totals in sorted(areas.items())},
        "total": total,
        "records": records,
    }


def ownership_percent(totals):
    denom = totals.rust_loc + totals.c_impl_loc
    if denom == 0:
        return 100.0
    return totals.rust_loc * 100.0 / denom


def dashboard_row_errors(report):
    errors = []
    seen = set()
    for row in DASHBOARD_ROWS:
        if row in seen:
            errors.append("duplicate configured dashboard row: {}".format(row))
        seen.add(row)

    for area in report["areas"]:
        if area not in DASHBOARD_ROWS and area != "Other in-scope code":
            errors.append("report area is not represented in dashboard rows: {}".format(area))
    return errors


def dashboard_row_from_line(line):
    stripped = line.rstrip()
    if not stripped or stripped.startswith("-"):
        return None
    for row in sorted(DASHBOARD_ROWS, key=len, reverse=True):
        if not stripped.startswith(row):
            continue
        rest = stripped[len(row):]
        if not rest or not rest[0].isspace():
            continue
        return row
    return None


def check_dashboard_file(path):
    counts = defaultdict(int)
    try:
        with Path(path).open("r", encoding="utf-8") as fh:
            for line in fh:
                row = dashboard_row_from_line(line)
                if row:
                    counts[row] += 1
    except OSError as exc:
        return ["{}: {}".format(path, exc)]

    errors = []
    for row, count in sorted(counts.items()):
        if count > 1:
            errors.append("{}: duplicate dashboard row `{}` appears {} times".format(path, row, count))
    return errors


def print_dashboard_rows(report):
    print("## Dashboard Rows")
    print()
    print("| Area | Functional Rust % | Rust LOC | C debt LOC | Mechanical Rust % |")
    print("| --- | ---: | ---: | ---: | ---: |")
    for area in DASHBOARD_ROWS:
        totals = report["areas"].get(area)
        functional = DASHBOARD_FUNCTIONAL_PERCENT.get(area, "")
        if totals is None:
            print("| {} | {} | n/a | n/a | n/a |".format(area, functional))
            continue
        print(
            "| {} | {} | {} | {} | {:.1f}% |".format(
                area,
                functional,
                totals.rust_loc,
                totals.c_impl_loc,
                ownership_percent(totals),
            )
        )
    print()


def print_markdown(report, top):
    print("# McKernel Rust Ownership Report")
    print()
    scope = "including arm64" if report["include_arm64"] else "excluding arm64"
    print(f"Scope: `{scope}`")
    print(f"Roots: `{', '.join(report['roots'])}`")
    print()
    print("## Summary")
    total: AreaTotals = report["total"]
    print()
    print("| Metric | LOC |")
    print("| --- | ---: |")
    print(f"| Rust implementation | {total.rust_loc} |")
    print(f"| C implementation debt | {total.c_impl_loc} |")
    print(f"| C/header boundary | {total.header_loc + total.boundary_loc} |")
    print(f"| Required assembly | {total.asm_loc} |")
    print(f"| Tests/smokes | {total.test_loc} |")
    print(f"| External/generated | {total.external_loc + total.generated_loc} |")
    print(f"| Mechanical Rust ownership | {ownership_percent(total):.1f}% |")
    print()
    print(
        "Mechanical Rust ownership is `Rust implementation / "
        "(Rust implementation + C implementation debt)`. C/header boundaries, "
        "required assembly, tests, and external/vendor/generated code are "
        "reported but excluded from that denominator."
    )
    print()
    print_dashboard_rows(report)
    print("## Areas")
    print()
    print("| Area | Files | Rust LOC | C debt LOC | Boundary LOC | ASM LOC | Mechanical Rust % |")
    print("| --- | ---: | ---: | ---: | ---: | ---: | ---: |")
    for area, totals in report["areas"].items():
        boundary = totals.header_loc + totals.boundary_loc
        print(
            f"| {area} | {totals.files} | {totals.rust_loc} | "
            f"{totals.c_impl_loc} | {boundary} | {totals.asm_loc} | "
            f"{ownership_percent(totals):.1f}% |"
        )
    print()
    print("## Top C Implementation Debt")
    print()
    c_files = sorted(report["total"].c_files, key=lambda rec: rec.loc, reverse=True)
    if not c_files:
        print("No C implementation debt found.")
        return
    print("| LOC | Area | Path |")
    print("| ---: | --- | --- |")
    for record in c_files[:top]:
        print(f"| {record.loc} | {record.area} | `{record.path}` |")


def print_json(report):
    def totals_to_dict(totals):
        return {
            "files": totals.files,
            "rust_loc": totals.rust_loc,
            "c_impl_loc": totals.c_impl_loc,
            "header_loc": totals.header_loc,
            "boundary_loc": totals.boundary_loc,
            "asm_loc": totals.asm_loc,
            "test_loc": totals.test_loc,
            "external_loc": totals.external_loc,
            "generated_loc": totals.generated_loc,
            "mechanical_rust_percent": round(ownership_percent(totals), 2),
            "top_c_files": [
                {"path": rec.path, "loc": rec.loc, "area": rec.area}
                for rec in sorted(totals.c_files, key=lambda rec: rec.loc, reverse=True)[:20]
            ],
        }

    payload = {
        "repo": report["repo"],
        "include_arm64": report["include_arm64"],
        "roots": report["roots"],
        "total": totals_to_dict(report["total"]),
        "areas": {name: totals_to_dict(totals) for name, totals in report["areas"].items()},
        "dashboard_rows": [
            {
                "area": area,
                "functional_percent": DASHBOARD_FUNCTIONAL_PERCENT.get(area),
                "mechanical": totals_to_dict(report["areas"][area])
                if area in report["areas"]
                else None,
            }
            for area in DASHBOARD_ROWS
        ],
    }
    print(json.dumps(payload, indent=2, sort_keys=True))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=".", help="repository root")
    parser.add_argument(
        "--root",
        action="append",
        dest="roots",
        help="source root to scan; may be repeated",
    )
    parser.add_argument("--include-arm64", action="store_true", help="include arm64 sources")
    parser.add_argument(
        "--format",
        choices=("markdown", "json"),
        default="markdown",
        help="output format",
    )
    parser.add_argument("--top", type=int, default=25, help="number of top C-debt files")
    parser.add_argument(
        "--fail-on-c",
        action="store_true",
        help="exit nonzero if any C implementation debt remains",
    )
    parser.add_argument(
        "--fail-on-c-area",
        action="append",
        default=[],
        metavar="AREA",
        help="exit nonzero if the named dashboard/report area has C debt; may be repeated",
    )
    parser.add_argument(
        "--check-dashboard",
        action="append",
        default=[],
        metavar="PATH",
        help="check a dashboard text file for duplicate known rows; may be repeated",
    )
    args = parser.parse_args()

    repo = Path(args.repo).resolve()
    roots = args.roots if args.roots else list(DEFAULT_ROOTS)
    report = build_report(repo, roots, args.include_arm64)
    errors = dashboard_row_errors(report)
    for path in args.check_dashboard:
        errors.extend(check_dashboard_file(path))
    if errors:
        for error in errors:
            print("error: {}".format(error), file=sys.stderr)
        return 1

    if args.format == "json":
        print_json(report)
    else:
        print_markdown(report, args.top)

    failed = False
    if args.fail_on_c and report["total"].c_impl_loc:
        print(
            "error: C implementation debt remains: {}".format(
                report["total"].c_impl_loc
            ),
            file=sys.stderr,
        )
        failed = True
    for area in args.fail_on_c_area:
        if area not in report["areas"]:
            print("error: unknown or unscanned area `{}`".format(area), file=sys.stderr)
            failed = True
            continue
        debt = report["areas"][area].c_impl_loc
        if debt:
            print(
                "error: C implementation debt remains in `{}`: {}".format(area, debt),
                file=sys.stderr,
            )
            failed = True
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
