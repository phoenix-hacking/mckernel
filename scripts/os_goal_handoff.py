"""Durable functional McKernel recovery context; no security testing.

This records facts and source pointers. It never authorizes a resume, signals a
process, clears ownership, or changes the coordinator's Markdown documents.
"""

from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
import tempfile
from uuid import uuid4


DOCUMENTS = ("CAMPAIGN.md",)


def _invocation_attribution(state, provenance):
    """Attribute diagnostics only by recorded invocation identity, never error text."""
    current_log = state.get("log_dir")
    if (not isinstance(provenance, dict) or not isinstance(current_log, str)
            or not current_log or not isinstance(provenance.get("log_dir"), str)
            or not provenance["log_dir"]):
        return "unknown"
    if provenance["log_dir"] != current_log:
        return "other_invocation"
    for key in ("worker_pid", "worker_start"):
        if (state.get(key) is not None and provenance.get(key) is not None
                and state[key] != provenance[key]):
            return "other_invocation"
    return "current"


def context_record(repo, state, remaining_seconds=None):
    """Build bounded data from a saved worker snapshot, without live actions."""
    if not isinstance(state, dict):
        raise ValueError("Recovery context requires a worker snapshot")
    if remaining_seconds is not None and (
            isinstance(remaining_seconds, bool) or not isinstance(remaining_seconds, (int, float))
            or not math.isfinite(remaining_seconds) or remaining_seconds < 0):
        raise ValueError("Remaining work-window time must be finite and nonnegative")
    goal, credit = state.get("goal") or {}, state.get("credit_budget") or {}
    if not isinstance(goal, dict) or not isinstance(credit, dict):
        raise ValueError("Invalid saved goal or credit record")
    fields = ("thread_id", "updated_at", "phase", "stop_reason", "worker_pid",
              "worker_start", "server_pid", "server_start", "log_dir", "console_log",
              "last_instruction", "resume_instruction", "capture_progress", "cleanup_verified",
              "last_error", "last_error_provenance", "last_failure", "credit_budget_error", "stop_errors", "exit_code",
              "startup_instruction_sha256", "transport_failure", "transport_uncertain",
              "last_usage_transport_error", "last_usage_read_retry", "server_close_errors")
    fields += ("stop_journal", "latest_stop", "last_stop_record_id", "stop_decision", "blocked_repair_reviews",
               "waiting_reason")
    record = {key: state[key] for key in fields if key in state}
    current = {key: state[key] for key in
               ("thread_id", "log_dir", "worker_pid", "worker_start", "server_pid",
                "server_start", "phase", "stop_reason", "exit_code") if key in state}
    current["goal_status"] = goal.get("status")
    retained = {}
    for key in ("last_error", "last_failure"):
        if key not in state or state[key] is None:
            continue
        value = state[key]
        provenance = state.get("last_error_provenance") if key == "last_error" else value
        attribution = _invocation_attribution(state, provenance)
        if key == "last_error" and (not isinstance(provenance, dict)
                or "error" not in provenance or provenance["error"] != value):
            attribution = "unknown"
        if attribution == "current":
            current[key] = value
        else:
            retained[key] = {"value": value, "provenance": provenance,
                             "attribution": attribution}
    record.update(schema_version=2, recorded_at=datetime.now(timezone.utc).isoformat(),
                  current_invocation=current, retained_diagnostics=retained,
                  raw_worker_snapshot=dict(state),
                  scope="Functional McKernel OS/apps and Rust/assembly migration only; no security testing.",
                  release_authorized=False, goal_status=goal.get("status"),
                  credit_accounting={key: credit[key] for key in
                                     ("id", "budget", "spent", "remaining") if key in credit},
                  remaining_seconds_observed=remaining_seconds,
                  source_documents=[str(Path(repo) / name) for name in DOCUMENTS])
    return record


def render(record):
    current = record["current_invocation"]
    summary = ("Current invocation: goal=" + str(current.get("goal_status"))
               + "; phase=" + str(current.get("phase"))
               + "; stop_reason=" + str(current.get("stop_reason"))
               + "; exit_code=" + str(current.get("exit_code")) + ".\n\n")
    return ("# Campaign recovery handoff\n\n"
            "Functional McKernel OS/apps and Rust/assembly migration only; no security testing.\n\n"
            "This is a factual checkpoint, not resume or workload authority. Read CAMPAIGN.md\n"
            "as the sole active plan, status and handoff at the source_documents path below.\n"
            "Preserve the selected allowance, ledger and any actually configured deadlines;\n"
            "a restart resets none of them. No time limit is implied when none is configured.\n"
            "Resolve uncertain submissions before resending. Historical documents, diagnostics\n"
            "and run windows supply no new authorization.\n\n"
            + summary +
            "Only current_invocation diagnostics are attributed to this invocation.\n"
            "retained_diagnostics distinguishes other-invocation and unknown provenance.\n"
            "Original diagnostic fields and raw_worker_snapshot remain unchanged evidence;\n"
            "they do not replace the current goal/stop/exit result.\n\n"
            "Local worker/server retirement does not prove native jobs or cleanup owners\n"
            "have retired. Reconcile their live identities and retained transactions; do\n"
            "not remove containers, unlink locks, replay used grants or redo successful\n"
            "build prefixes merely because a model process restarted. An unconfirmed\n"
            "checkpoint may omit the interrupted turn's unsaved conclusions. Reuse the\n"
            "retained logs and source changes to establish the actual next operation.\n\n"
            "```json\n" + json.dumps(record, indent=2, sort_keys=True) + "\n```\n")


def _write_exclusive(path, text):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as output:
        output.write(text)
        output.flush()
        os.fsync(output.fileno())


def _sync_directory(path):
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def write_recovery_handoff(repo, directory, state, *, remaining_seconds=None):
    """Retain an immutable snapshot, then atomically publish RECOVERY.md."""
    record = context_record(repo, state, remaining_seconds)
    raw = json.dumps(record, indent=2, sort_keys=True) + "\n"
    if len(raw.encode()) > 256 * 1024:
        raise ValueError("Recovery context exceeds the bounded snapshot size")
    directory = Path(directory)
    archive = directory / "recovery"
    archive.mkdir(mode=0o700, parents=True, exist_ok=True)
    name = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ") + "-" + uuid4().hex[:8]
    _write_exclusive(archive / (name + ".json"), raw)
    markdown = render(record)
    _write_exclusive(archive / (name + ".md"), markdown)
    _sync_directory(archive)
    fd, temporary = tempfile.mkstemp(prefix=".recovery-", dir=directory)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as output:
            output.write(markdown)
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary, directory / "RECOVERY.md")
        _sync_directory(directory)
    finally:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
    return directory / "RECOVERY.md"

