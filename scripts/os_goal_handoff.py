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


DOCUMENTS = ("CURRENT.md", "HANDOFF.md", "RECOVERY-20261026.md", "GOAL.md",
             "START.md", "CONVERGENCE.md", "RUN-WINDOW-18H-20261025.md")


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
              "last_error", "last_failure", "credit_budget_error", "stop_errors", "exit_code",
              "startup_instruction_sha256", "transport_failure", "transport_uncertain",
              "last_usage_transport_error", "last_usage_read_retry", "server_close_errors")
    record = {key: state[key] for key in fields if key in state}
    record.update(schema_version=1, recorded_at=datetime.now(timezone.utc).isoformat(),
                  scope="Functional McKernel OS/apps and Rust/assembly migration only; no security testing.",
                  release_authorized=False, goal_status=goal.get("status"),
                  credit_accounting={key: credit[key] for key in
                                     ("id", "budget", "spent", "remaining") if key in credit},
                  remaining_seconds_observed=remaining_seconds,
                  source_documents=[str(Path(repo) / "docs/verification/os-milestones-20260914" / name)
                                    for name in DOCUMENTS])
    return record


def render(record):
    return ("# Campaign recovery handoff\n\n"
            "Functional McKernel OS/apps and Rust/assembly migration only; no security testing.\n\n"
            "This is a factual checkpoint, not resume or workload authority. Read the latest\n"
            "CURRENT.md and HANDOFF.md at the paths below before continuing. Preserve the\n"
            "same credit ledger and fixed deadline. A restart does not reset the allowance\n"
            "or extend the run window. Resolve uncertain submissions before resending.\n\n"
            "Document filenames and historical run windows do not supply new authorization.\n"
            "Use the current explicit invocation and its actual fixed window.\n\n"
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
