#!/usr/bin/env python3
"""Validate and render the manual SC1 engineering snapshot (stdlib only).

The default command updates only STABLE-CORE.md. --check and --stdout never
write. Neither the report nor this helper authorizes campaign execution.
"""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
from collections import deque
from datetime import date
from pathlib import Path, PurePosixPath, PureWindowsPath
from urllib.parse import quote


REPO_ROOT = Path(__file__).resolve().parents[1]
INPUT_RELATIVE = Path("docs/verification/os-milestones-20260914/stable-core.json")
TASKS_RELATIVE = INPUT_RELATIVE.with_name("tasks.json")
OUTPUT_RELATIVE = Path("STABLE-CORE.md")
DEFAULT_INPUT = REPO_ROOT / INPUT_RELATIVE
STATUSES = (
    "verified", "baseline", "implemented", "partial", "blocked", "unmeasured", "planned"
)
STATUS_LEGEND = {
    "verified": "Scoped completed behavior supported by the cited evidence.",
    "baseline": "Passing historical exact artifacts; current-source replay is still required.",
    "implemented": "Source exists; this does not establish accepted runtime behavior.",
    "partial": "Some of the behavior is supported; the stated remainder is open.",
    "blocked": "The next check awaits the recorded blocker or dependency.",
    "unmeasured": "No accepted measurement for this scope; this does not mean code is absent.",
    "planned": "An observable substep is specified; no completed result is claimed.",
}
MILESTONE_STATUSES = ("NOT YET DEMONSTRATED", "STABLE ON DECLARED PROFILE")


class TrackerError(ValueError):
    """An invalid tracker or unsafe reporting path."""


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise TrackerError(f"duplicate JSON key: {key!r}")
        result[key] = value
    return result


def load_tracker(path=DEFAULT_INPUT):
    """Read JSON, rejecting duplicate object keys; perform no writes."""
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"),
                          object_pairs_hook=_unique_object)
    except (OSError, UnicodeError, ValueError) as exc:
        raise TrackerError(f"cannot load {path}: {exc}") from exc


def _object(value, label):
    if not isinstance(value, dict):
        raise TrackerError(f"{label} must be an object")
    return value


def _string(value, label, allow_empty=False):
    if not isinstance(value, str) or (not allow_empty and not value.strip()):
        raise TrackerError(f"{label} must be a {'nonempty ' if not allow_empty else ''}string")
    return value


def _list(value, label, nonempty=False):
    if not isinstance(value, list) or (nonempty and not value):
        raise TrackerError(f"{label} must be a {'nonempty ' if nonempty else ''}list")
    return value


def _strings(value, label, nonempty=False):
    for index, entry in enumerate(_list(value, label, nonempty)):
        _string(entry, f"{label}[{index}]")
    return value


def _relative_file(value, label):
    _string(value, label)
    path = PurePosixPath(value)
    if (path.is_absolute() or PureWindowsPath(value).drive or "\\" in value
            or ".." in path.parts or value != path.as_posix()
            or value in (".", "") or re.search(r"[\x00-\x1f\x7f]", value)
            or re.match(r"^[A-Za-z][A-Za-z0-9+.-]*:", value)):
        raise TrackerError(f"{label} must be a repo-relative file path without traversal")
    return path


def _in_repo_file(root, relative, label):
    """Resolve symlinks before checking containment and file existence."""
    try:
        resolved = (root / relative).resolve()
        resolved.relative_to(root)
        if not resolved.is_file():
            raise TrackerError(f"{label} is not a real in-repo file: {relative}")
    except (OSError, RuntimeError, ValueError) as exc:
        raise TrackerError(f"{label} must resolve to a real in-repo file: {relative}: {exc}") from exc
    return resolved


def validate(doc, root=None):
    """Raise TrackerError on invalid data; do not mutate it.

    Without root this checks the schema, references and dependency graph.
    Passing a repository root additionally checks every reference's resolved
    file and each area's original task IDs in the canonical tasks.json.
    The CLI always supplies a root.
    """
    _object(doc, "tracker")
    if type(doc.get("schema_version")) is not int or doc["schema_version"] != 1:
        raise TrackerError("schema_version must be integer 1")
    if doc.get("milestone") != "SC1":
        raise TrackerError("milestone must be SC1")
    for field in ("title", "as_of", "source_revision", "status"):
        _string(doc.get(field), field)
    if not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", doc["as_of"]):
        raise TrackerError("as_of must be YYYY-MM-DD")
    try:
        date.fromisoformat(doc["as_of"])
    except ValueError as exc:
        raise TrackerError("as_of must be a valid calendar date") from exc
    if not re.fullmatch(r"[0-9a-fA-F]{40}", doc["source_revision"]):
        raise TrackerError("source_revision must be a full 40-character hexadecimal SHA")
    if doc["status"] not in MILESTONE_STATUSES:
        raise TrackerError(f"unsupported milestone status: {doc['status']!r}")
    for field in ("profile", "definition", "scope_notes"):
        _strings(doc.get(field), field, nonempty=True)
    for index, exclusion in enumerate(_list(doc.get("exclusions"), "exclusions")):
        label = f"exclusions[{index}]"
        _object(exclusion, label)
        for field in ("name", "route", "reason"):
            _string(exclusion.get(field), f"{label}.{field}")

    references = _object(doc.get("references"), "references")
    for key, path in references.items():
        _string(key, "reference key")
        _relative_file(path, f"references.{key}")

    areas = {}
    for index, area in enumerate(_list(doc.get("areas"), "areas", nonempty=True)):
        label = f"areas[{index}]"
        _object(area, label)
        for field in ("id", "title", "kind", "owner"):
            _string(area.get(field), f"{label}.{field}")
        if area["id"] in areas:
            raise TrackerError(f"duplicate area ID: {area['id']}")
        if area["kind"] not in ("core", "enabler"):
            raise TrackerError(f"{label}.kind must be core or enabler")
        _strings(area.get("task_refs"), f"{label}.task_refs", nonempty=True)
        areas[area["id"]] = area

    items = {}
    for index, item in enumerate(_list(doc.get("items"), "items", nonempty=True)):
        label = f"items[{index}]"
        _object(item, label)
        for field in ("id", "area", "title", "status", "next_check"):
            _string(item.get(field), f"{label}.{field}")
        if item["id"] in items:
            raise TrackerError(f"duplicate item ID: {item['id']}")
        if item["area"] not in areas:
            raise TrackerError(f"{label}: unknown area {item['area']!r}")
        if item["status"] not in STATUSES:
            raise TrackerError(f"{label}: unsupported status {item['status']!r}")
        if "required" in item and type(item["required"]) is not bool:
            raise TrackerError(f"{label}.required must be boolean")
        needs_result = item["status"] not in ("unmeasured", "planned")
        _string(item.get("result"), f"{label}.result", allow_empty=not needs_result)
        _strings(item.get("depends_on"), f"{label}.depends_on")
        _strings(item.get("evidence"), f"{label}.evidence", nonempty=needs_result)
        for key in item["evidence"]:
            if key not in references:
                raise TrackerError(f"{label}: unknown evidence reference {key!r}")
        # Assignment and original contracts belong to the area, not individual agents.
        if "owner" in item or "task_refs" in item:
            raise TrackerError(f"{label}: owner and task_refs must inherit from the area")
        items[item["id"]] = item

    dependents = {ident: [] for ident in items}
    indegree = {}
    for ident, item in items.items():
        deps = set(item["depends_on"])
        indegree[ident] = len(deps)
        for dep in deps:
            if dep == ident:
                raise TrackerError(f"item {ident}: self dependency")
            if dep not in items:
                raise TrackerError(f"item {ident}: unknown dependency {dep!r}")
            dependents[dep].append(ident)
    ready = deque(ident for ident, degree in indegree.items() if degree == 0)
    visited = 0
    while ready:
        ident = ready.popleft()
        visited += 1
        for dependent in dependents[ident]:
            indegree[dependent] -= 1
            if indegree[dependent] == 0:
                ready.append(dependent)
    if visited != len(items):
        raise TrackerError("dependency cycle involving: " + ", ".join(
            ident for ident, degree in indegree.items() if degree))

    priority = _strings(doc.get("priority"), "priority")
    if len(set(priority)) != len(priority):
        raise TrackerError("duplicate priority item ID")
    for ident in priority:
        if ident not in items:
            raise TrackerError(f"unknown priority item ID: {ident}")

    if doc["status"] == "STABLE ON DECLARED PROFILE":
        required = [item for item in items.values() if item.get("required", True)]
        if not required or any(item["status"] != "verified" for item in required):
            raise TrackerError("STABLE ON DECLARED PROFILE requires every required item verified "
                               "and at least one required item")

    if root is not None:
        root = Path(root).resolve()
        for key, path in references.items():
            _in_repo_file(root, path, f"references.{key}")
        tasks_path = _in_repo_file(root, TASKS_RELATIVE, "tasks.json")
        tasks_doc = _object(load_tracker(tasks_path), "tasks.json")
        task_ids = set()
        for index, task in enumerate(_list(tasks_doc.get("tasks"), "tasks.json.tasks")):
            task = _object(task, f"tasks.json.tasks[{index}]")
            ident = _string(task.get("id"), f"tasks.json.tasks[{index}].id")
            if ident in task_ids:
                raise TrackerError(f"duplicate original task ID: {ident}")
            task_ids.add(ident)
        for area in areas.values():
            for ident in area["task_refs"]:
                if ident not in task_ids:
                    raise TrackerError(f"area {area['id']}: unknown original task ID {ident!r}")


def summarize(doc):
    """Return independent status counts by area, kind and total; no scoring."""
    validate(doc)

    def counts():
        return dict.fromkeys(STATUSES, 0)

    result = {
        "total": counts(),
        "by_kind": {kind: counts() for kind in ("core", "enabler")},
        "by_area": {area["id"]: counts() for area in doc["areas"]},
    }
    kinds = {area["id"]: area["kind"] for area in doc["areas"]}
    for item in doc["items"]:
        status, area = item["status"], item["area"]
        result["total"][status] += 1
        result["by_area"][area][status] += 1
        result["by_kind"][kinds[area]][status] += 1
    return result


def _md(value):
    value = html.escape(value, quote=False)
    for char in ("\\", "`", "*", "_", "[", "]", "|"):
        value = value.replace(char, "\\" + char)
    return "<br>".join(value.splitlines())


def _link(label, path):
    return f"[{_md(label)}]({quote(str(path), safe='/.-_')})"


def _table(lines, headings, rows):
    lines.append("| " + " | ".join(headings) + " |")
    lines.append("| " + " | ".join("---" for _ in headings) + " |")
    lines.extend("| " + " | ".join(row) + " |" for row in rows)
    lines.append("")


def render(doc):
    """Return deterministic Markdown for the supplied snapshot, with a final newline."""
    summary = summarize(doc)
    items = {item["id"]: item for item in doc["items"]}
    lines = [
        f"# {_md(doc['title'])}", "",
        f"Milestone: {doc['milestone']} — {doc['status']}", "",
        "## Snapshot provenance", "",
        f"As of: {doc['as_of']}. Source revision: `{doc['source_revision']}`.", "",
        "Input: " + _link(str(INPUT_RELATIVE), INPUT_RELATIVE) + ".", "",
        "Manual snapshot, not live telemetry. Counts describe only the declared substeps "
        "and cited evidence; they do not verify the current checkout or promote the milestone.", "",
        "Campaign state is not inferred from this snapshot; this helper does not start/resume "
        "or change it. Owner labels are responsibility roles, not live runtime status.", "",
        "## Practical progress counts", "",
        "Every row is one observable substep. Statuses are counted separately; historical "
        "baselines remain separate from verified behavior. There is no weighted score or "
        "overall stability percentage. Counts include required and optional rows.", "",
    ]
    count_rows = []
    for kind in ("core", "enabler"):
        counts = summary["by_kind"][kind]
        count_rows.append([kind, str(sum(counts.values()))] + [str(counts[s]) for s in STATUSES])
    _table(lines, ["Kind", "Substeps", *STATUSES], count_rows)
    _table(lines, ["Area", "Kind", "Substeps", *STATUSES], [
        [_md(area["id"] + " — " + area["title"]), area["kind"],
         str(sum(summary["by_area"][area["id"]].values()))]
        + [str(summary["by_area"][area["id"]][s]) for s in STATUSES]
        for area in doc["areas"]
    ])
    lines.extend(["## Status legend", ""])
    lines.extend(f"- {status}: {STATUS_LEGEND[status]}" for status in STATUSES)
    lines.extend(["", "## Declared profile", ""])
    lines.extend(f"- {_md(entry)}" for entry in doc["profile"])
    lines.extend(["", "## Finish definition", ""])
    lines.extend(f"- {_md(entry)}" for entry in doc["definition"])
    lines.extend(["", "STABLE ON DECLARED PROFILE is a manual declaration allowed only when "
                  "every required row is verified and the declared scope is valid. "
                  "Omitted required flags mean required; optional rows are marked below.", "",
                  "## Scope notes", ""])
    lines.extend(f"- {_md(entry)}" for entry in doc["scope_notes"])
    lines.extend(["", "## Priority queue", ""])
    if not doc["priority"]:
        lines.extend(["No priority substeps declared.", ""])
    for index, ident in enumerate(doc["priority"], 1):
        item = items[ident]
        open_deps = [dep for dep in item["depends_on"] if items[dep]["status"] != "verified"]
        blockers = "; ".join(f"{dep} ({items[dep]['status']}): {items[dep]['result'] or 'No result recorded.'}"
                             for dep in open_deps)
        if item["status"] == "blocked":
            blockers = item["result"] + ("; " + blockers if blockers else "")
        lines.extend([
            f"### {index}. {_md(ident)} — {_md(item['title'])}", "",
            f"State: {item['status']}. Required: {'yes' if item.get('required', True) else 'no'}.", "",
            f"Result: {_md(item['result']) if item['result'].strip() else 'No result recorded.'}", "",
            f"Blockers / unmet dependencies: {_md(blockers) if blockers else 'None recorded.'}", "",
            f"Next check: {_md(item['next_check'])}", "",
            "Dependencies: " + (", ".join(f"{_md(dep)} ({items[dep]['status']})"
                                          for dep in item["depends_on"]) or "None."), "",
        ])
    for area in doc["areas"]:
        lines.extend([
            f"## {_md(area['id'])} — {_md(area['title'])}", "",
            f"Kind: {area['kind']}. Owner role: {_md(area['owner'])}.", "",
            "Original contracts (inherited by every substep): "
            + ", ".join(_link(ident, TASKS_RELATIVE) for ident in area["task_refs"]) + ".", "",
        ])
        rows = []
        for item in doc["items"]:
            if item["area"] != area["id"]:
                continue
            evidence = ", ".join(_link(key, doc["references"][key]) for key in item["evidence"])
            deps = ", ".join(f"{_md(dep)} ({items[dep]['status']})" for dep in item["depends_on"])
            rows.append([
                _md(item["id"]) + (" (optional)" if not item.get("required", True) else ""),
                _md(item["title"]), item["status"],
                _md(item["result"]) if item["result"].strip() else "No result recorded.",
                _md(item["next_check"]), deps or "None", evidence or "None recorded",
            ])
        _table(lines, ["ID", "Behavior", "State", "Exact result", "Next check", "Dependencies", "Evidence"], rows)
    lines.extend(["## Explicit exclusions", ""])
    if doc["exclusions"]:
        _table(lines, ["Excluded behavior", "Route / later obligation", "Reason"], [
            [_md(exclusion[field]) for field in ("name", "route", "reason")]
            for exclusion in doc["exclusions"]
        ])
    else:
        lines.extend(["No exclusions declared.", ""])
    lines.extend([
        "## Updating this report", "",
        "Edit only " + _link(str(INPUT_RELATIVE), INPUT_RELATIVE)
        + " for tracker updates; do not edit this generated Markdown by hand. "
        "Record the snapshot date, full source revision, exact scoped results, evidence "
        "and next observable checks. Keep original gates and acceptance contracts unchanged.", "",
        "From the repository root:", "",
        "```sh", "python3 -B scripts/stable_core_tracker.py",
        "python3 -B scripts/stable_core_tracker.py --check", "```", "",
        "The default command updates only STABLE-CORE.md. --check validates and compares "
        "without writing; --stdout validates and prints without writing. "
        "The helper never auto-promotes the milestone or resumes the campaign.", "",
    ])
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=REPO_ROOT, help="repository root")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true", help="validate and compare without writing")
    mode.add_argument("--stdout", action="store_true", help="validate and print without writing")
    args = parser.parse_args(argv)
    try:
        root = args.root.resolve()
        input_path = _in_repo_file(root, INPUT_RELATIVE, "tracker input")
        doc = load_tracker(input_path)
        validate(doc, root=root)
        rendered = render(doc)
        if args.stdout:
            sys.stdout.write(rendered)
            return 0
        output = root / OUTPUT_RELATIVE
        # Never follow a generated-output symlink, even to another repository file.
        if output.is_symlink():
            raise TrackerError("STABLE-CORE.md must not be a symlink")
        if args.check:
            if not output.is_file() or output.read_bytes() != rendered.encode("utf-8"):
                print("STABLE-CORE.md is stale or missing; run python3 -B "
                      "scripts/stable_core_tracker.py to regenerate.", file=sys.stderr)
                return 1
        else:
            output.write_bytes(rendered.encode("utf-8"))
        return 0
    except (TrackerError, OSError, UnicodeError, RuntimeError) as exc:
        print(f"stable-core tracker: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
