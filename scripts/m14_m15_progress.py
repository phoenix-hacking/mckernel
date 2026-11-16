#!/usr/bin/env python3
"""Render every open original M14/M15 check; perform no campaign control."""

import argparse
from decimal import Decimal, ROUND_HALF_UP
from fractions import Fraction
import json
import math
import os
from pathlib import Path
import tempfile
from urllib.parse import quote


TRACKER = Path("docs/verification/m14-m15-closure-progress.json")
MARKDOWN = Path("docs/verification/M14-M15-OPEN-DELIVERABLES.md")
ENGINEERING = Path("docs/verification/m14-m15-engineering-progress.json")
ORIGINAL_COUNT = 156


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        _require(key not in result, "Duplicate JSON key: " + key)
        result[key] = value
    return result


def _read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"), object_pairs_hook=_pairs,
                      parse_constant=lambda value: (_ for _ in ()).throw(
                          ValueError("Nonfinite JSON value: " + value)))


def _percent(value):
    value = Fraction(value)
    number = Decimal(value.numerator) / Decimal(value.denominator)
    return float(number.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def _number(value):
    return type(value) in (int, float) and math.isfinite(value)


def parse_tracker(document, *, expected_count=ORIGINAL_COUNT):
    """Derive counts and original equal-child/equal-gate weights, read-only."""
    _require(isinstance(document, dict)
             and document.get("schema") == "mckernel-m14-m15-closure-progress-v1"
             and document.get("original_criteria_unchanged") is True,
             "Original closure tracker/criteria are missing or changed")
    maps = {}
    for name in ("tasks", "requirements"):
        rows = document.get(name)
        _require(isinstance(rows, list), "Missing " + name)
        ids = [row.get("id") if isinstance(row, dict) else None for row in rows]
        _require(all(isinstance(ident, str) and ident for ident in ids)
                 and len(ids) == len(set(ids)), "Duplicate or missing " + name + " IDs")
        maps[name] = dict(zip(ids, rows))
    tasks = {ident: row for ident, row in maps["tasks"].items()
             if row.get("counted_in_requirement_rollup") is True}
    _require(len(tasks) == expected_count, "Original counted-check denominator changed")
    for ident, row in tasks.items():
        _require(ident.startswith(("M14-", "M15-"))
                 and _number(row.get("percent_complete"))
                 and row["percent_complete"] in (0, 100)
                 and isinstance(row.get("done_when"), str) and row["done_when"].strip(),
                 "Original checks require binary completion and a condition: " + ident)
    requirements = maps["requirements"]
    declared_tasks = []
    child_map = {}
    for ident, row in requirements.items():
        _require(type(row.get("accepted")) is bool, "Nonbinary requirement acceptance: " + ident)
        task_ids, child_ids = row.get("task_ids", []), row.get("child_requirements", [])
        _require(isinstance(task_ids, list) and isinstance(child_ids, list),
                 "Original children must be explicit lists: " + ident)
        children = task_ids + child_ids
        _require(children and len(children) == len(set(children)),
                 "Missing or duplicate original children: " + ident)
        for child in children:
            child_row = tasks.get(child) or requirements.get(child)
            _require(child_row is not None and child_row.get("parent") == ident,
                     "Missing/reparented original child: " + str(child))
            if child in tasks:
                declared_tasks.append(child)
        child_map[ident] = children
    _require(len(declared_tasks) == len(tasks) and set(declared_tasks) == set(tasks),
             "Every counted check must belong to exactly one original parent")
    cache, visiting = {}, set()

    def rollup(ident):
        if ident in tasks:
            return Fraction(tasks[ident]["percent_complete"])
        _require(ident not in visiting, "Cycle in original requirement graph")
        if ident not in cache:
            visiting.add(ident)
            values = [rollup(child) for child in child_map[ident]]
            visiting.remove(ident)
            cache[ident] = (Fraction(100) if requirements[ident]["accepted"]
                            else sum(values, Fraction()) / len(values))
        return cache[ident]

    for ident in requirements:
        rollup(ident)
    summaries = document.get("summaries", {})
    milestones, root_ids = {}, []
    for milestone in ("M14", "M15"):
        summary = summaries.get(milestone, {})
        gates = summary.get("original_gate_ids")
        _require(isinstance(gates, list) and gates and len(gates) == len(set(gates))
                 and all(ident in requirements and requirements[ident].get("parent") is None
                         and ident.startswith(milestone + "-") for ident in gates)
                 and type(summary.get("milestone_accepted")) is bool,
                 "Missing original milestone gates/acceptance: " + milestone)
        root_ids.extend(gates)
        selected = [row for ident, row in tasks.items() if ident.startswith(milestone + "-")]
        closed = sum(row["percent_complete"] == 100 for row in selected)
        milestones[milestone] = {
            "total": len(selected), "accepted": closed, "open": len(selected) - closed,
            "checklist_percent": _percent(sum((rollup(ident) for ident in gates), Fraction()) / len(gates)),
            "accepted_gates": sum(requirements[ident]["accepted"] for ident in gates),
            "total_gates": len(gates), "accepted_milestone": summary["milestone_accepted"],
        }
    _require(len(root_ids) == len(set(root_ids))
             and set(root_ids) == {ident for ident, row in requirements.items()
                                  if row.get("parent") is None},
             "Original milestone weights omit or duplicate a gate")
    closed = sum(row["percent_complete"] == 100 for row in tasks.values())
    return {"tasks": tasks, "requirements": requirements,
            "parent_percent": {ident: _percent(value) for ident, value in cache.items()},
            "total": len(tasks), "accepted": closed, "open": len(tasks) - closed,
            "milestones": milestones, "tracker_updated_at": document.get("updated_at", "unknown")}


def _evidence(values):
    _require(isinstance(values, list) and all(isinstance(value, str) and value.strip()
                                            for value in values), "Evidence must be explicit references")
    return values


def parse_engineering(document, task_ids):
    """Optional engineering checkpoints/estimates can never change acceptance."""
    _require(isinstance(document, dict) and document.get("schema") ==
             "mckernel-m14-m15-engineering-progress-v1", "Invalid engineering sidecar schema")
    _require(set(document) <= {"schema", "note", "updated_at", "checks"}, "Unknown engineering sidecar field")
    checks = document.get("checks", {})
    _require(isinstance(checks, dict) and set(checks) <= set(task_ids),
             "Engineering metadata must name original counted check IDs")
    result = {}
    for ident, entry in checks.items():
        allowed = {"engineering_steps", "estimate_range", "rationale", "weight_rationale",
                   "latest_passing_evidence", "latest_passing_note", "next_increment",
                   "owner", "status", "updated_at"}
        _require(isinstance(entry, dict) and set(entry) <= allowed,
                 "Engineering metadata cannot override original acceptance: " + ident)
        steps = entry.get("engineering_steps", [])
        _require(isinstance(steps, list) and len(steps) <= 32, "Engineering steps must be finite")
        seen, total_weight, done_weight, done_count = set(), Fraction(), Fraction(), 0
        for step in steps:
            _require(isinstance(step, dict) and set(step) <=
                     {"id", "description", "done", "evidence", "weight"}, "Invalid engineering step")
            _require(isinstance(step.get("id"), str) and step["id"].strip()
                     and step["id"] not in seen and isinstance(step.get("description"), str)
                     and step["description"].strip() and type(step.get("done")) is bool,
                     "Steps require unique IDs, descriptions and explicit done flags")
            seen.add(step["id"])
            evidence = _evidence(step.get("evidence", []))
            _require(not step["done"] or evidence, "Completed engineering step has no evidence")
            weight = step.get("weight", 1)
            _require(_number(weight) and weight > 0, "Engineering weight must be positive and finite")
            if "weight" in step:
                _require(isinstance(entry.get("weight_rationale"), str)
                         and entry["weight_rationale"].strip(), "Explicit weights need a rationale")
            total_weight += Fraction(str(weight))
            if step["done"]:
                done_weight += Fraction(str(weight))
                done_count += 1
        estimate = entry.get("estimate_range")
        if estimate is not None:
            _require(isinstance(estimate, list) and len(estimate) == 2
                     and all(_number(value) for value in estimate)
                     and 0 <= estimate[0] <= estimate[1] <= 100
                     and isinstance(entry.get("rationale"), str) and entry["rationale"].strip()
                     and _evidence(entry.get("latest_passing_evidence", [])),
                     "Engineering estimates require a valid range, evidence and rationale")
        for name in ("rationale", "latest_passing_note", "next_increment", "owner", "status", "updated_at"):
            if name in entry:
                _require(isinstance(entry[name], str) and entry[name].strip(), "Empty " + name)
        if "latest_passing_evidence" in entry:
            _evidence(entry["latest_passing_evidence"])
        result[ident] = dict(entry,
            checkpoint_percent=_percent(100 * done_weight / total_weight) if steps else None,
            done_steps=done_count, total_steps=len(steps))
    return result


def load_progress(repo, *, engineering_path=None):
    """Return derived machine counts/open rows; never read runtime/account state."""
    repo = Path(repo)
    result = parse_tracker(_read_json(repo / TRACKER))
    sidecar = Path(engineering_path) if engineering_path is not None else repo / ENGINEERING
    engineering, warning = {}, None
    if sidecar.exists():
        try:
            engineering = parse_engineering(_read_json(sidecar), result["tasks"])
        except (OSError, ValueError, TypeError) as error:
            warning = "Engineering metadata unavailable; estimates are unknown: " + str(error)
    result["engineering_warning"] = warning
    result["engineering"] = engineering
    result["open_rows"] = [dict(row, parent_checklist_percent=result["parent_percent"][row["parent"]],
                                engineering=engineering.get(ident, {}))
                           for ident, row in sorted(result["tasks"].items())
                           if row["percent_complete"] == 0]
    return result


def _cell(value, limit=None):
    text = " ".join(str(value).split())
    if limit is not None and len(text) > limit:
        text = text[:limit - 1].rsplit(" ", 1)[0] + "…"
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("|", "\\|")


def _link(reference):
    if reference.startswith(("https://", "http://", "/")):
        target = reference
    else:
        target = os.path.relpath(reference, str(MARKDOWN.parent))
    label = Path(reference).name or reference
    return "[" + _cell(label) + "](" + quote(target, safe="/:#?=&%") + ")"


def _passing(row, progress):
    engineering = row["engineering"]
    refs = engineering.get("latest_passing_evidence", [])
    if refs:
        note = _cell(engineering.get("latest_passing_note", "Recorded passing partial scope"), 170)
        return note + " — " + ", ".join(_link(ref) for ref in refs)
    candidates = []
    parent = row["parent"]
    while parent:
        for order, sibling in enumerate(progress["tasks"].values()):
            refs = [ref for ref in sibling.get("evidence", [])
                    if isinstance(ref, str) and ref not in {"CAMPAIGN.md", "instructions/CAMPAIGN.md"}]
            if sibling.get("parent") == parent and sibling["percent_complete"] == 100 and refs:
                date = str(sibling.get("verified_at") or sibling.get("accepted_at") or "")
                candidates.append((date, order, sibling["id"], refs[-1]))
        if candidates:
            _, _, ident, reference = max(candidates)
            return "Scoped prerequisite `" + ident + "`: " + _link(reference)
        parent = progress["requirements"][parent].get("parent")
    return "No passing scope recorded for this check"


def _next_missing(row, progress):
    if row["id"].endswith("-ACCEPT"):
        parent = progress["requirements"][row["parent"]]
        missing = [ident for ident in parent.get("task_ids", []) if ident != row["id"]
                   and progress["tasks"][ident]["percent_complete"] != 100]
        missing += [ident for ident in parent.get("child_requirements", [])
                    if not progress["requirements"][ident]["accepted"]]
        return ("Close " + ", ".join("`" + ident + "`" for ident in missing)
                + "; then Root explicitly accepts the matching scope." if missing
                else "Root explicitly accepts the complete matching original evidence.")
    return _cell(row["engineering"].get("next_increment") or row["done_when"], 240)


def _engineering_text(entry):
    parts = []
    if entry.get("checkpoint_percent") is not None:
        if entry["checkpoint_percent"] == 100:
            parts.append("all {}/{} checkpoints done; original acceptance pending".format(
                entry["done_steps"], entry["total_steps"]))
        else:
            parts.append("{:g}% checkpoints ({}/{})".format(
                entry["checkpoint_percent"], entry["done_steps"], entry["total_steps"]))
    if entry.get("estimate_range") is not None:
        low, high = entry["estimate_range"]
        parts.append(("{:g}–<100% estimate".format(low) if low < 100 else
                      "estimate awaits original acceptance") if high == 100 else
                     "{:g}–{:g}% estimate".format(low, high))
    return "; ".join(parts) or "unknown"


def _runtime(repo, campaign_state=None, runtime_state=None):
    if runtime_state is None:
        path = Path(repo) / ".git/os-autopilot/state.json"
        try:
            runtime_state = _read_json(path) if path.exists() else {}
        except (OSError, ValueError):
            runtime_state = {}
    _require(isinstance(runtime_state, dict), "Runtime state must be an object")
    _require(campaign_state in {None, "STOPPED", "STOPPING", "RUNNING", "WAITING"},
             "Invalid explicit campaign state")
    active = bool(runtime_state.get("active_turns"))
    goal = runtime_state.get("goal") or {}
    stopped = (campaign_state in {"STOPPED", "STOPPING"}
               or runtime_state.get("stop_now") is True or bool(runtime_state.get("stop_reason"))
               or runtime_state.get("controller_dispatch_enabled") is False
               or runtime_state.get("phase") in {"stopped", "stopping", "owner_retained"}
               or goal.get("status") in {"paused", "complete", "usageLimited", "budgetLimited"})
    if stopped:
        state = "STOPPING" if active else "STOPPED"
    elif campaign_state is not None:
        state = campaign_state
    elif runtime_state.get("phase") == "running" and goal.get("status") == "active":
        state = "RUNNING"
    elif runtime_state:
        state = "WAITING"
    else:
        state = "STOPPED"
    work = runtime_state.get("active_work", [])
    _require(isinstance(work, list), "Runtime active_work must be an explicit list")
    mapped = {}
    for item in work:
        if isinstance(item, dict) and isinstance(item.get("original_check"), str):
            ident = item["original_check"]
            _require(ident not in mapped, "Duplicate runtime original-check assignment: " + ident)
            mapped[ident] = item
    return state, runtime_state.get("updated_at", "unknown"), mapped


def _row_state(row, campaign_state, work):
    if campaign_state == "STOPPED":
        return "stopped / open"
    if campaign_state == "STOPPING":
        return "stop requested / open"
    status = str(work.get("status") or row["engineering"].get("status") or "open").lower()
    if status in {"blocked", "waiting", "waiting_for_input"}:
        return "waiting / open"
    if campaign_state == "RUNNING" and status in {"active", "running", "working", "in_progress"}:
        return "working / open"
    if status in {"complete", "completed"}:
        return "increment complete / open"
    return "open"


def _markdown(progress, campaign_state, runtime_updated_at="unknown", active_work=None):
    active_work = active_work or {}
    lines = ["# M14/M15 remaining original deliverables", "",
             "One goal: a working OS, completed through the unchanged original M14/M15 checks.", "",
             "**Campaign: " + campaign_state + ".** " +
             ("Stopped by the current user; no new OS campaign or child dispatch is authorized."
              if campaign_state == "STOPPED" else
              "Stop requested; an existing turn is still recorded. No new campaign/child dispatch is authorized."
              if campaign_state == "STOPPING" else
              "Explicit campaign state supplied by the frontdoor; an open row is not proof of active work."), "",
             "**{accepted}/{total} original checks accepted; {open} open.**".format(**progress),
             "Tracker update: `" + _cell(progress["tracker_updated_at"]) + "`. "
             "[Original criteria, statuses and full evidence](m14-m15-closure-progress.json) remain the source of truth.", "",
             "Runtime state update: `" + _cell(runtime_updated_at) + "`. Only explicit original-ID assignments "
             "can label a row working; unrelated agent activity cannot.", "",
             "| Milestone | Accepted checks | Open checks | Original weighted checklist | Explicit milestone acceptance |",
             "| --- | ---: | ---: | ---: | --- |"]
    for name, summary in progress["milestones"].items():
        lines.append("| {} | {}/{} | {} | {:.2f}% | {} |".format(
            name, summary["accepted"], summary["total"], summary["open"],
            summary["checklist_percent"], "100% — accepted" if summary["accepted_milestone"] else "0% — open"))
    lines += ["", "Original check acceptance is binary: 0% or 100%. Parent checklist percentages use the declared "
              "immediate children; milestones give equal weight to their original file/integration gates. "
              "These are verified checklist metrics, not effort or engineering estimates.", "",
              "Engineering checkpoint percentages below count only explicitly defined, evidenced steps in the "
              "[optional sidecar](m14-m15-engineering-progress.json). They measure that small declared checklist, "
              "not the whole original condition, time spent, or acceptance. Estimates require evidence and a rationale; "
              "otherwise engineering progress is **unknown**. Agent activity, reviews and inventories earn no credit."]
    if progress["engineering_warning"]:
        lines += ["", _cell(progress["engineering_warning"])]
    for milestone in ("M14", "M15"):
        lines += ["", "## " + milestone + " — " + str(progress["milestones"][milestone]["open"]) + " open checks", "",
                  "Owner means the tracker-recorded responsible role, not a currently running worker. "
                  "Passing prerequisite/partial evidence does not satisfy the open row.", "",
                  "| Original ID / short name | State / recorded row update | Parent verified checklist | Own acceptance | Engineering only | Recorded owner | Latest recorded passing scope / next missing original proof |",
                  "| --- | --- | ---: | ---: | --- | --- | --- |"]
        for row in progress["open_rows"]:
            if not row["id"].startswith(milestone + "-"):
                continue
            title = row["title"].removeprefix("Qualify ").removesuffix(" on the matching admissible coherent image")
            work = active_work.get(row["id"], {})
            updated = work.get("updated_at") or row["engineering"].get("updated_at") or "unknown"
            cells = ["`" + row["id"] + "` — " + _cell(title, 95),
                     _row_state(row, campaign_state, work) + " / `" + _cell(updated) + "`",
                     "`" + row["parent"] + "` " + "{:g}%".format(row["parent_checklist_percent"]),
                     "0% — open", _engineering_text(row["engineering"]),
                     _cell(work.get("owner") or row["engineering"].get("owner") or row.get("owner", "unknown"), 105),
                     _passing(row, progress) + ". **Next:** " +
                     (_cell(work["next_action"], 240) if work.get("next_action") else _next_missing(row, progress))]
            lines.append("| " + " | ".join(cells) + " |")
    entries = [(row["id"], row["engineering"]) for row in progress["open_rows"] if row["engineering"]]
    if entries:
        lines += ["", "## Defined engineering checkpoints (separate from acceptance)"]
        for ident, entry in entries:
            lines += ["", "**`" + ident + "`: " + _engineering_text(entry) + ".**"]
            if entry.get("rationale"):
                lines += ["", _cell(entry["rationale"])]
            for step in entry.get("engineering_steps", []):
                evidence = "; ".join(_link(ref) for ref in step.get("evidence", []))
                lines += ["", "- [" + ("x" if step["done"] else " ") + "] `" + _cell(step["id"]) + "` "
                          + _cell(step["description"]) + ((" — " + evidence) if evidence else "")]
    lines += ["", "## Stop and resume", "", "```sh", "python3 -B scripts/m14_m15.py stop", "```", "",
              "This stops new campaign/child dispatch and requests active work to stop through the existing "
              "bounded shutdown. It preserves the saved goal, evidence, finite credit ledger and unresolved owners. "
              "A stop request or STOPPED label is not proof of Docker/native/workload cleanup or OS completion.", "",
              "Only an explicit later user start/resume restarts campaign dispatch. M14 final acceptance precedes "
              "M15 final acceptance. After both, checkpoint and stop the campaign; do not mark the larger working-OS "
              "goal complete without its remaining original requirements.", "",
              "Regenerate/print **every open row** with `python3 -B scripts/m14_m15.py status` "
              "(or `python3 -B scripts/m14_m15_progress.py status`). "
              "Each assignment must name an original ID, the concrete missing proof/next functional increment, "
              "and its expected result. Record a completed engineering step only with its actual evidence; "
              "original acceptance changes only through the canonical tracker.", ""]
    return "\n".join(lines)


def _write_changed(path, text):
    """Replace a changed report atomically; unchanged content keeps its mtime."""
    data = text.encode("utf-8")
    if path.exists() and path.read_bytes() == data:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, prefix="." + path.name + ".",
                                         delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        temporary = None
        fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def render_progress(repo, *, campaign_state=None, engineering_path=None, runtime_state=None):
    """Return full Markdown and update only its derived file if content changes."""
    repo = Path(repo)
    state, updated, work = _runtime(repo, campaign_state, runtime_state)
    text = _markdown(load_progress(repo, engineering_path=engineering_path), state, updated, work)
    _write_changed(repo / MARKDOWN, text)
    return text


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", nargs="?", choices=["status"], default="status")
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--campaign-state", choices=["STOPPED", "STOPPING", "RUNNING", "WAITING"])
    parser.add_argument("--engineering-file", type=Path)
    args = parser.parse_args(argv)
    print(render_progress(args.repo, campaign_state=args.campaign_state,
                          engineering_path=args.engineering_file), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
