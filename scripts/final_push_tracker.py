#!/usr/bin/env python3
"""Validate and recalculate the evidence-weighted final-push tracker."""

from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import sys
from collections import Counter, OrderedDict
from dataclasses import asdict, dataclass
from pathlib import Path


TOTAL_POINTS = 10_000
BEGIN_MARKER = "BEGIN AUTO-GENERATED TRACKER"
END_MARKER = "END AUTO-GENERATED TRACKER"
VALID_STATUSES = {"PASS", "TODO", "IN_PROGRESS", "BLOCKED"}
NO_EVIDENCE = {"", "-", "none", "n/a", "na", "tbd", "todo"}


class TrackerError(RuntimeError):
    """Raised when the tracker is structurally invalid."""


@dataclass(frozen=True)
class Workstream:
    ident: str
    name: str
    points: int


@dataclass(frozen=True)
class Gate:
    ident: str
    workstream: str
    points: int
    status: str
    evidence: str
    deliverable: str
    owner: str


def parse_tracker(text: str) -> tuple[OrderedDict[str, Workstream], list[Gate], list[str]]:
    workstreams: OrderedDict[str, Workstream] = OrderedDict()
    gates: list[Gate] = []
    source_records: list[str] = []
    gate_ids: set[str] = set()

    for line_number, raw_line in enumerate(text.splitlines(), start=1):
        line = raw_line.strip()
        if line.startswith("WORKSTREAM|"):
            fields = line.split("|")
            if len(fields) != 4:
                raise TrackerError(
                    f"line {line_number}: WORKSTREAM requires exactly 4 fields"
                )
            _, ident, name, points_text = fields
            if not ident or ident in workstreams:
                raise TrackerError(
                    f"line {line_number}: missing or duplicate workstream {ident!r}"
                )
            try:
                points = int(points_text)
            except ValueError as exc:
                raise TrackerError(
                    f"line {line_number}: invalid workstream points {points_text!r}"
                ) from exc
            if points <= 0:
                raise TrackerError(
                    f"line {line_number}: workstream points must be positive"
                )
            workstreams[ident] = Workstream(ident, name, points)
            source_records.append(line)
        elif line.startswith("GATE|"):
            fields = line.split("|")
            if len(fields) != 8:
                raise TrackerError(
                    f"line {line_number}: GATE requires exactly 8 fields; "
                    "the evidence and deliverable fields may not contain a pipe"
                )
            _, ident, workstream, points_text, status, evidence, deliverable, owner = fields
            if not ident or ident in gate_ids:
                raise TrackerError(
                    f"line {line_number}: missing or duplicate gate {ident!r}"
                )
            gate_ids.add(ident)
            if workstream not in workstreams:
                raise TrackerError(
                    f"line {line_number}: gate {ident} references unknown workstream "
                    f"{workstream!r}"
                )
            try:
                points = int(points_text)
            except ValueError as exc:
                raise TrackerError(
                    f"line {line_number}: gate {ident} has invalid points {points_text!r}"
                ) from exc
            if points <= 0:
                raise TrackerError(
                    f"line {line_number}: gate {ident} points must be positive"
                )
            if status not in VALID_STATUSES:
                raise TrackerError(
                    f"line {line_number}: gate {ident} has invalid status {status!r}"
                )
            if status == "PASS" and evidence.strip().lower() in NO_EVIDENCE:
                raise TrackerError(
                    f"line {line_number}: PASS gate {ident} requires concrete evidence"
                )
            if not deliverable.strip():
                raise TrackerError(
                    f"line {line_number}: gate {ident} requires a deliverable"
                )
            if not owner.strip():
                raise TrackerError(
                    f"line {line_number}: gate {ident} requires an owner role"
                )
            gates.append(
                Gate(
                    ident=ident,
                    workstream=workstream,
                    points=points,
                    status=status,
                    evidence=evidence.strip(),
                    deliverable=deliverable.strip(),
                    owner=owner.strip(),
                )
            )
            source_records.append(line)

    if not workstreams:
        raise TrackerError("no WORKSTREAM records found")
    if not gates:
        raise TrackerError("no GATE records found")

    declared_total = sum(item.points for item in workstreams.values())
    if declared_total != TOTAL_POINTS:
        raise TrackerError(
            f"declared workstream total is {declared_total}, expected {TOTAL_POINTS}"
        )

    gate_points_by_workstream = Counter()
    for gate in gates:
        gate_points_by_workstream[gate.workstream] += gate.points
    for ident, workstream in workstreams.items():
        actual = gate_points_by_workstream[ident]
        if actual != workstream.points:
            raise TrackerError(
                f"workstream {ident} gate total is {actual}, declared {workstream.points}"
            )

    return workstreams, gates, source_records


def summary_data(
    workstreams: OrderedDict[str, Workstream],
    gates: list[Gate],
    source_records: list[str],
) -> dict[str, object]:
    earned_total = sum(gate.points for gate in gates if gate.status == "PASS")
    digest = hashlib.sha256(("\n".join(source_records) + "\n").encode()).hexdigest()
    status_counts = Counter(gate.status for gate in gates)
    rows = []
    for ident, workstream in workstreams.items():
        selected = [gate for gate in gates if gate.workstream == ident]
        earned = sum(gate.points for gate in selected if gate.status == "PASS")
        rows.append(
            {
                "id": ident,
                "name": workstream.name,
                "earned_points": earned,
                "total_points": workstream.points,
                "percent": round(earned * 100 / workstream.points, 2),
                "passed_gates": sum(gate.status == "PASS" for gate in selected),
                "total_gates": len(selected),
            }
        )
    return {
        "schema_version": 1,
        "earned_points": earned_total,
        "total_points": TOTAL_POINTS,
        "percent": round(earned_total * 100 / TOTAL_POINTS, 2),
        "status_counts": {status: status_counts.get(status, 0) for status in sorted(VALID_STATUSES)},
        "gate_count": len(gates),
        "input_sha256": digest,
        "workstreams": rows,
        "gates": [asdict(gate) for gate in gates],
    }


def render_summary(data: dict[str, object]) -> str:
    rows = data["workstreams"]
    assert isinstance(rows, list)
    counts = data["status_counts"]
    assert isinstance(counts, dict)
    lines = [
        BEGIN_MARKER,
        f"OVERALL COMPLETION: {data['percent']:.2f}% "
        f"({data['earned_points']} / {data['total_points']} evidence points)",
        f"TRACKED GATES: {data['gate_count']} total; "
        f"{counts['PASS']} PASS; {counts['IN_PROGRESS']} IN_PROGRESS; "
        f"{counts['BLOCKED']} BLOCKED; {counts['TODO']} TODO",
        f"TRACKER INPUT SHA256: {data['input_sha256']}",
        "",
        "WORKSTREAM SUMMARY:",
    ]
    for row in rows:
        assert isinstance(row, dict)
        lines.append(
            f"- {row['id']} {row['name']}: {row['percent']:.2f}% "
            f"({row['earned_points']} / {row['total_points']} points; "
            f"{row['passed_gates']} / {row['total_gates']} gates PASS)"
        )
    lines.append(END_MARKER)
    return "\n".join(lines)


def replace_summary(text: str, rendered: str) -> str:
    if text.count(BEGIN_MARKER) != 1 or text.count(END_MARKER) != 1:
        raise TrackerError("tracker must contain exactly one generated-summary marker pair")
    begin = text.index(BEGIN_MARKER)
    end = text.index(END_MARKER, begin) + len(END_MARKER)
    return text[:begin] + rendered + text[end:]


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--file", type=Path, default=Path("final-push.txt"), help="tracker path"
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--check", action="store_true", help="fail when the generated summary is stale"
    )
    mode.add_argument(
        "--update", action="store_true", help="rewrite the generated summary in place"
    )
    parser.add_argument("--json", type=Path, help="write the full computed state as JSON")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    try:
        original = args.file.read_text(encoding="utf-8")
        workstreams, gates, source_records = parse_tracker(original)
        data = summary_data(workstreams, gates, source_records)
        rendered = render_summary(data)
        updated = replace_summary(original, rendered)
    except (OSError, TrackerError) as exc:
        print(f"final-push tracker error: {exc}", file=sys.stderr)
        return 2

    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    if args.update:
        if updated != original:
            args.file.write_text(updated, encoding="utf-8")
            print(
                f"updated {args.file}: {data['percent']:.2f}% "
                f"({data['earned_points']}/{data['total_points']})"
            )
        else:
            print(
                f"already current: {data['percent']:.2f}% "
                f"({data['earned_points']}/{data['total_points']})"
            )
        return 0

    if updated != original:
        print("final-push.txt generated summary is stale", file=sys.stderr)
        diff = difflib.unified_diff(
            original.splitlines(),
            updated.splitlines(),
            fromfile=str(args.file),
            tofile=f"{args.file} (recalculated)",
            lineterm="",
        )
        for line in diff:
            print(line, file=sys.stderr)
        print(
            f"run: {Path(sys.argv[0])} --file {args.file} --update",
            file=sys.stderr,
        )
        return 1

    print(
        f"final-push tracker valid: {data['percent']:.2f}% "
        f"({data['earned_points']}/{data['total_points']}; "
        f"{data['gate_count']} gates; sha256:{data['input_sha256']})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
