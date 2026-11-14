"""Derived, readable M14/M15 status. Never an acceptance or execution authority."""
import argparse
from datetime import datetime, timedelta, timezone
import json
import math
import os
from pathlib import Path
import re
import tempfile
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from os_goal_guard_protocol import read_json
from os_goal_mailbox_status import read_mailbox_status, receipt_source_label
from os_goal_stop_log import _text as redact


MAX_BYTES = 200 * 1024


def _text(value):
    if value is None:
        return "UNKNOWN"
    if not isinstance(value, (str, int, float, bool)):
        return "UNKNOWN (unexpected metadata type)"
    text = str(value)
    if len(text) > 8192:
        raise ValueError("A status field exceeds 8192 characters; reconcile without truncation")
    return " ".join(re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", redact(text, 8192)).split())


def _percent(value):
    if type(value) not in (int, float) or not math.isfinite(value) or not 0 <= value <= 100:
        return "UNKNOWN"
    return f"{value:.2f}%"


def _time(value):
    if isinstance(value, datetime):
        result = value
    elif isinstance(value, str):
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    elif type(value) in (float, int):
        result = datetime.fromtimestamp(value, timezone.utc)
    else:
        raise ValueError("Missing or invalid timestamp")
    if result.tzinfo is None:
        raise ValueError("Timestamp has no timezone")
    return result.astimezone(timezone.utc)


def _utc(value):
    try:
        return _time(value).isoformat().replace("+00:00", "Z")
    except (ValueError, TypeError, OverflowError):
        return "UNKNOWN"


def _accepted(value):
    return "ACCEPTED" if value is True else "OPEN" if value is False else "UNKNOWN"


def _rows(ledger, key, missing):
    rows = ledger.get(key)
    if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
        missing.append(key + ": missing or malformed row list")
        return []
    for number, row in enumerate(rows, 1):
        for field in ("id", "percent_complete", "owner"):
            if field not in row:
                missing.append(f"{key} row {number}: missing {field}")
    return rows


def _runtime(lines, runtime, now, checker):
    lines += ["WORKSTATION AND AGENTS", ""]
    if runtime is None:
        lines += ["Workstation runtime: UNAVAILABLE.",
                  "No workstation snapshot was supplied. Live agents and active-turn counts are UNKNOWN, not zero.", ""]
        return
    state = runtime.get("state") if isinstance(runtime.get("state"), dict) else {}
    guard = runtime.get("guardian") if isinstance(runtime.get("guardian"), dict) else {}
    watch = runtime.get("watcher") if isinstance(runtime.get("watcher"), dict) else {}
    mailbox = runtime.get("mailbox") if isinstance(runtime.get("mailbox"), dict) else {}
    def verified(pid, birth):
        if checker is None or type(pid) is not int or not isinstance(birth, str) or not birth.isdigit():
            return False
        try:
            return checker(pid, birth) is True
        except (OSError, ValueError, TypeError):
            return False
    worker_live = verified(state.get("worker_pid"), state.get("worker_start"))
    watcher_live = verified(watch.get("watcher_pid"), watch.get("watcher_start")) and watch.get("worker_pid") == state.get("worker_pid")
    guardian_live = verified(guard.get("pid"), guard.get("start"))
    try:
        age = (now - _time(state.get("heartbeat_at"))).total_seconds()
        fresh = -5 <= age <= 120
    except (ValueError, TypeError, OverflowError):
        age, fresh = None, False
    current = worker_live and watcher_live and fresh and state.get("phase") in {"running", "waiting_for_input", "repair_review"}
    goal = state.get("goal") if isinstance(state.get("goal"), dict) else {}
    lines += ["Snapshot attribution: " + ("CURRENT: exact worker/watcher births verified and heartbeat <=120 seconds old."
              if current else "STALE OR UNVERIFIED: saved agent status does not establish live agents."),
              f"Worker exact birth verified: {worker_live}; watcher exact birth verified: {watcher_live}; guardian exact birth verified: {guardian_live}",
              "Controller phase: " + _text(state.get("phase")) + "; goal: " + _text(goal.get("status")),
              "State heartbeat UTC: " + _utc(state.get("heartbeat_at")) + "; state updated UTC: " + _utc(state.get("updated_at")),
              "State heartbeat age seconds: " + (f"{age:.1f}" if age is not None else "UNKNOWN"),
              "Guardian phase: " + _text(guard.get("phase")) + "; reason: " + _text(guard.get("reason")),
              "Watcher event: " + _text(watch.get("event")) + "; observation UTC: " + _utc(watch.get("at")),
              "Mailbox last attempt UTC: " + _utc(mailbox.get("last_poll_at")) + "; last successful poll UTC: " + _utc(mailbox.get("last_successful_poll_at")),
              "Mailbox next GET UTC: " + _utc(mailbox.get("next_poll_at")) + "; error: " + _text(mailbox.get("last_error"))]
    active = state.get("active_turns") if isinstance(state.get("active_turns"), dict) else None
    agents = state.get("agents") if isinstance(state.get("agents"), dict) else None
    lines += [f"Saved roster records: {len(agents) if agents is not None else 'UNKNOWN'}; saved active-turn records: {len(active) if active is not None else 'UNKNOWN'}.",
              "Fresh controller snapshot active-turn count: " + (str(len(active)) if current and active is not None else "UNKNOWN"),
              "Per-agent models, efforts and assignments are unavailable unless explicitly recorded; no defaults are inferred."]
    keys = sorted(set(agents or {}) | set(active or {}))
    if not keys:
        lines.append("Agent roster: " + ("no rows recorded in the current snapshot." if current else "UNAVAILABLE or historical empty snapshot; live count UNKNOWN."))
    for ident in keys:
        row = (agents or {}).get(ident)
        row = row if isinstance(row, dict) else {}
        observed = "ACTIVE TURN OBSERVED" if current and ident in (active or {}) else "SAVED / NOT VERIFIED LIVE"
        lines.append("AGENT " + _text(ident) + " | " + observed + " | label=" + _text(row.get("label") or row.get("name"))
                     + " | saved status=" + _text(row.get("status")) + " | turn=" + _text((active or {}).get(ident) or row.get("turn_id")))
        metadata = []
        if ident == state.get("thread_id"):
            metadata.append("controller role=Root (recorded primary thread)")
        elif row.get("child") is True:
            metadata.append("controller role=child (recorded)")
        if "last_event_at" in row:
            metadata.append("last event UTC=" + _utc(row["last_event_at"]))
        for key in ("quiet_seconds", "retired", "role", "child"):
            if key in row:
                metadata.append(key + "=" + _text(row[key]))
        if metadata:
            lines.append("  Recorded agent metadata: " + " | ".join(metadata))
    stop = runtime.get("latest_stop") if isinstance(runtime.get("latest_stop"), dict) else {}
    if stop:
        identities = stop.get("identities") if isinstance(stop.get("identities"), dict) else {}
        attributed = (bool(state.get("log_dir")) and stop.get("log_dir") == state["log_dir"]
                      and str(identities.get("worker_pid")) == str(state.get("worker_pid"))
                      and identities.get("worker_start") == state.get("worker_start"))
        error = stop.get("error") if isinstance(stop.get("error"), dict) else {}
        lines += ["Last stop diagnostic attribution: " + ("matches saved worker invocation" if attributed else "retained/unattributed; not asserted as the current blocker"),
                  "Recorded stop: " + _text(stop.get("category")) + " | " + _text(stop.get("reason")),
                  "Recorded error: " + _text(error.get("code")) + " | " + _text(error.get("message")),
                  "Recorded next action: " + _text(stop.get("remedy"))]
    messages = mailbox.get("messages") if isinstance(mailbox.get("messages"), dict) else None
    if messages is None:
        lines.append("Instruction receipt counts: UNAVAILABLE.")
    else:
        totals = mailbox.get("message_status_counts")
        if isinstance(totals, dict) and all(type(value) is int and value >= 0 for value in totals.values()):
            counts = {name: totals.get(name, 0) for name in ("WAITING", "ACCEPTED", "NOT_QUEUED")}
            counts.update({name: count for name, count in totals.items() if name not in counts and count})
            scope = "Instruction receipts: "
        else:
            counts = {name: sum(isinstance(v, dict) and v.get("delivery_status") == name for v in messages.values())
                      for name in ("WAITING", "ACCEPTED", "NOT_QUEUED")}
            scope = ("Recent instruction receipts: " if type(mailbox.get("message_count")) is int
                     and mailbox["message_count"] > len(messages) else "Instruction receipts: ")
        lines.append(scope + "; ".join(f"{name}={count}" for name, count in counts.items()) + ". Acceptance is not completed work.")
        total = mailbox.get("message_count", len(messages))
        lines.append(f"Recent instruction receipt metadata: {len(messages)} shown of {_text(total)} total.")
        for key, message in list(messages.items())[-5:]:
            if isinstance(message, dict):
                lines.append("Instruction " + _text(receipt_source_label(message, key))
                             + " | " + _text(message.get("delivery_status"))
                             + " | received UTC=" + _utc(message.get("received_at"))
                             + " | source=" + _text(message.get("source_url") or message.get("comment_url")))
    last = state.get("last_instruction") if isinstance(state.get("last_instruction"), dict) else {}
    lines += ["Last controller instruction: " + _text(last.get("id")) + " | " + _text(last.get("status"))
              + " | accepted timestamp=" + _utc(last.get("delivered_at")), ""]


def render_status_text(ledger, *, source_commit=None, runtime=None, generated_at=None,
                       identity_checker=None, ci=None, notes=None):
    if not isinstance(ledger, dict) or runtime is not None and not isinstance(runtime, dict):
        raise TypeError("Ledger/runtime must be objects")
    now = _time(generated_at) if generated_at is not None else datetime.now(timezone.utc)
    try:
        boise_zone = ZoneInfo("America/Boise")
        boise = now.astimezone(boise_zone).isoformat()
        stale_boise = (now + timedelta(minutes=15)).astimezone(boise_zone).isoformat()
    except ZoneInfoNotFoundError:
        boise = "UNAVAILABLE (America/Boise timezone data missing)"
        stale_boise = boise
    missing = []
    requirements, tasks = _rows(ledger, "requirements", missing), _rows(ledger, "tasks", missing)
    optional = _rows(ledger, "optional_or_deferred_decisions", missing)
    counted = [row for row in tasks if row.get("counted_in_requirement_rollup") is True]
    uncounted = [row for row in tasks if row.get("counted_in_requirement_rollup") is False]
    unclassified = len(tasks) - len(counted) - len(uncounted)
    lines = ["McKernel M14/M15 progress and agent status", "",
             "Generated UTC: " + now.isoformat().replace("+00:00", "Z"), "Generated America/Boise: " + boise,
             "Treat this snapshot as stale after UTC: " + _utc(now + timedelta(minutes=15)) + "; America/Boise: " + stale_boise
             + " (15 minutes after generation; check for a newer report).",
             "Ledger updated UTC: " + _utc(ledger.get("updated_at")), "Source commit: " + _text(source_commit),
             "Canonical ledger: docs/verification/m14-m15-closure-progress.json; human plan: CAMPAIGN.md.",
             "This is a derived view, not new acceptance or execution authority. Checklist percentages are not accepted milestones, engineering hours or converted LOC.",
             "Scope: " + _text(ledger.get("scope")), "", "MILESTONE SUMMARY", ""]
    summaries = ledger.get("summaries") if isinstance(ledger.get("summaries"), dict) else {}
    for milestone in ("M14", "M15"):
        summary = summaries.get(milestone)
        summary = summary if isinstance(summary, dict) else {}
        ids = summary.get("original_gate_ids") if isinstance(summary.get("original_gate_ids"), list) else []
        if not ids:
            missing.append(milestone + ": original gate IDs missing")
        files = [r for r in requirements if r.get("id") in ids and r.get("id", "").startswith(milestone + "-F")]
        integrations = [r for r in requirements if r.get("id") in ids and r.get("id", "").startswith(milestone + "-I")]
        file_count, integration_count = summary.get("original_file_gate_count"), summary.get("original_integration_gate_count")
        expected_files = {f"{milestone}-F{n:02d}" for n in range(1, file_count + 1)} if type(file_count) is int and 0 <= file_count <= 100 else None
        expected_integrations = {f"{milestone}-I{n:02d}" for n in range(1, integration_count + 1)} if type(integration_count) is int and 0 <= integration_count <= 100 else None
        ids_complete = (expected_files is not None and expected_integrations is not None and len(set(ids)) == len(ids)
                        and set(ids) == expected_files | expected_integrations)
        complete_files = (ids_complete and len(files) == file_count and {r["id"] for r in files} == expected_files
                          and all(type(r.get("accepted")) is bool for r in files))
        complete_integrations = (ids_complete and len(integrations) == integration_count and {r["id"] for r in integrations} == expected_integrations
                                 and all(type(r.get("accepted")) is bool for r in integrations))
        if not complete_files or not complete_integrations:
            missing.append(milestone + ": gate rows or binary acceptance metadata incomplete; accepted counts UNKNOWN")
        lines.append(milestone + ": checklist " + _percent(summary.get("checklist_percent_complete"))
                     + "; milestone " + _accepted(summary.get("milestone_accepted"))
                     + f"; accepted files {sum(r.get('accepted') is True for r in files) if complete_files else 'UNKNOWN'}/{_text(summary.get('original_file_gate_count'))}"
                     + f"; accepted integrations {sum(r.get('accepted') is True for r in integrations) if complete_integrations else 'UNKNOWN'}/{_text(summary.get('original_integration_gate_count'))}.")
    lines += [f"Rows: {len(requirements)} requirements (including original gates); {len(tasks)} tasks.",
              f"Counted evidence tasks: {len(counted)}; verified at 100%: {sum(r.get('percent_complete') == 100 for r in counted)}.",
              f"Uncounted definition/preparation/register/support tasks: {len(uncounted)}; unclassified counting metadata: {unclassified}.",
              "Uncounted rows remain visible and do not add checklist credit. A 100% task is verified only at its stated scope.", ""]
    _runtime(lines, runtime, now, identity_checker)
    if ci is not None:
        lines += ["REMOTE CI (provided evidence; separate from milestone acceptance and workstation activity)"]
        if isinstance(ci, dict):
            for key in ("source_commit", "run_id", "url", "status", "conclusion", "observed_at", "summary", "limitations"):
                if key in ci:
                    lines.append(key + ": " + _text(ci[key]))
        else:
            lines.append(_text(ci))
        lines.append("")
    if notes:
        lines += ["ATTRIBUTED NOTES"] + [_text(note) for note in (notes if isinstance(notes, list) else [notes])] + [""]
    dictionaries = {name: {} for name in ("OWNER", "DEPS", "ACTION", "SCOPE", "PROOF")}
    def alias(kind, value):
        if value in (None, "", []):
            return "none" if value == [] else "UNKNOWN"
        text = "; ".join(_text(v) for v in value) if isinstance(value, list) else _text(value)
        table = dictionaries[kind]
        if text not in table:
            table[text] = kind[0] + str(len(table) + 1)
        return table[text]
    seen = set()
    lines += ["ALL CANONICAL REQUIREMENTS AND ORIGINAL GATES", ""]
    for row in requirements:
        ident = _text(row.get("id"))
        if ident in seen:
            missing.append("Duplicate requirement ID: " + ident)
        seen.add(ident)
        lines += ["REQUIREMENT " + ident + " | checklist=" + _percent(row.get("percent_complete")) + " | acceptance=" + _accepted(row.get("accepted")),
                  "  " + _text(row.get("title")) + " | parent=" + _text(row.get("parent")) + " | target=" + _text(row.get("target")),
                  "  owner=" + alias("OWNER", row.get("owner")) + " | dependencies=" + alias("DEPS", row.get("dependencies"))]
        for action in row.get("remaining_actions", []):
            lines.append("  Remaining: " + _text(action))
    lines += ["", "ALL CANONICAL TASKS (COUNTED AND UNCOUNTED)", ""]
    task_seen = set()
    for row in tasks:
        ident = _text(row.get("id"))
        if ident in task_seen:
            missing.append("Duplicate task ID: " + ident)
        task_seen.add(ident)
        counted_label = "COUNTED" if row.get("counted_in_requirement_rollup") is True else "UNCOUNTED" if row.get("counted_in_requirement_rollup") is False else "COUNTING UNKNOWN"
        lines += ["TASK " + ident + " | " + _percent(row.get("percent_complete")) + " | " + counted_label + " | " + _text(row.get("status")),
                  "  " + _text(row.get("title")) + " | parent=" + _text(row.get("parent")),
                  "  owner=" + alias("OWNER", row.get("owner")) + " | dependencies=" + alias("DEPS", row.get("dependencies"))
                  + " | completion=" + alias("ACTION", row.get("done_when")) + " | scope=" + alias("SCOPE", row.get("scope_limit"))
                  + " | evidence=" + alias("PROOF", row.get("evidence"))]
        for key in ("done_when", "status", "counted_in_requirement_rollup"):
            if key not in row:
                missing.append(ident + ": missing " + key)
    lines += ["", "OPTIONAL / DEFERRED DECISIONS (NOT CHECKLIST CREDIT)", ""]
    for row in optional:
        lines += ["OPTIONAL " + _text(row.get("id")) + " | " + _percent(row.get("percent_complete")) + " | " + _text(row.get("state")),
                  "  owner=" + alias("OWNER", row.get("owner")) + " | required for closure=" + _text(row.get("required_for_closure")),
                  "  Condition: " + _text(row.get("done_when"))]
    for key, title in (("blocking_input_tasks", "ORIGINAL BLOCKING INPUTS"), ("execution_packet_gaps", "MISSING EXECUTION PACKETS")):
        values = ledger.get(key)
        lines += ["", title + f" ({len(values) if isinstance(values, list) else 'UNKNOWN'})"]
        if isinstance(values, list):
            lines += [_text(v) for v in values]
        else:
            missing.append(key + ": missing list")
    for key, title in (("registers", "CANONICAL REGISTERS"), ("dependency_aliases", "DEPENDENCY ALIASES")):
        lines += ["", title]
        values = ledger.get(key)
        if isinstance(values, dict):
            for name, value in values.items():
                lines.append(_text(name) + ": " + (", ".join(_text(v) for v in value) if isinstance(value, list) else _text(value)))
        else:
            missing.append(key + ": missing object")
    lines += ["", "LOOKUP DETAILS", "Aliases below preserve repeated canonical text without duplicating it across hundreds of rows."]
    for kind, table in dictionaries.items():
        lines += ["", kind]
        lines += [ident + ": " + value for value, ident in table.items()]
    lines += ["", "MISSING DATA / LIMITS"]
    lines += missing or ["No required row metadata gaps detected."]
    lines += ["Runtime identity checks establish controller snapshot attribution, not per-agent operating-system processes or completed engineering results.",
              "Detailed source/input packets and verification recipes remain in the canonical JSON; no command, prompt or credential fields are copied from runtime snapshots.",
              f"END: requirements={len(requirements)}; tasks={len(tasks)}; optional decisions={len(optional)}.", ""]
    result = "\n".join(lines)
    size = len(result.encode("utf-8"))
    if size > MAX_BYTES:
        raise ValueError(f"Complete status requires {size} bytes; exceeds {MAX_BYTES}-byte limit. No rows were truncated.")
    return result


def write_status_text(path, ledger, **kwargs):
    text = render_status_text(ledger, **kwargs)
    path = Path(path)
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    if path.is_symlink():
        raise ValueError("Refusing symlinked status destination")
    fd, temporary = tempfile.mkstemp(prefix=".status-", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        base = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            os.fsync(base)
        finally:
            os.close(base)
    finally:
        Path(temporary).unlink(missing_ok=True)
    return {"path": str(path), "bytes": len(text.encode("utf-8")),
            "row_counts": {key: len(ledger.get(key, [])) for key in ("requirements", "tasks", "optional_or_deferred_decisions")}}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ledger", type=Path, default=Path(__file__).resolve().parents[1] / "docs/verification/m14-m15-closure-progress.json")
    parser.add_argument("--runtime-directory", type=Path)
    parser.add_argument("--source-commit")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    runtime = None
    checker = None
    if args.runtime_directory:
        runtime = {}
        for key, name in (("state", "state.json"), ("guardian", "guardian.json"), ("watcher", "watcher.json"), ("mailbox", "mailbox-state.json"), ("latest_stop", "latest-stop.json")):
            try:
                reader = read_mailbox_status if name == "mailbox-state.json" else read_json
                runtime[key] = reader(args.runtime_directory / name)
            except FileNotFoundError:
                pass
        from os_goal_guard_protocol import process_start
        checker = lambda pid, birth: process_start(pid) == birth
    kwargs = {"source_commit": args.source_commit, "runtime": runtime, "identity_checker": checker}
    ledger = read_json(args.ledger)
    if args.output:
        print(json.dumps(write_status_text(args.output, ledger, **kwargs), sort_keys=True))
    else:
        print(render_status_text(ledger, **kwargs), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
