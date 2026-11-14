"""Read-only evidence for overnight monitoring readiness, never start authority."""
from datetime import datetime, timezone
import hashlib
import math
import os
from pathlib import Path
import re
import stat
import time

from os_goal_guard_protocol import lease_free, process_start, read_json
from os_goal_stop_log import _text as redact


GUARDIAN_MAX_AGE = 90
RECEIPT_MAX_AGE = 900
POLL_DEADLINE_GRACE = 30
MAX_STATUS_BYTES = 200 * 1024
HEX64 = re.compile(r"[0-9a-f]{64}\Z")


def _epoch(value):
    try:
        if type(value) in (int, float):
            result = float(value)
        elif isinstance(value, str):
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                return None
            result = parsed.timestamp()
        else:
            return None
        return result if math.isfinite(result) and result > 0 else None
    except (ValueError, TypeError, OverflowError):
        return None


def _utc(value):
    try:
        return datetime.fromtimestamp(value, timezone.utc).isoformat().replace("+00:00", "Z") if value else None
    except (ValueError, TypeError, OverflowError, OSError):
        return None


def _fresh(value, now, limit):
    return value is not None and -5 <= now - value <= limit


def _hash(value):
    return value if isinstance(value, str) and HEX64.fullmatch(value) else None


def _oneof(value, choices):
    return isinstance(value, str) and value in choices


def _status_hash(path):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        before = os.fstat(fd)
        if (not stat.S_ISREG(before.st_mode) or before.st_uid != os.getuid()
                or not 0 < before.st_size <= MAX_STATUS_BYTES):
            raise ValueError("Status text is not an owned bounded regular file")
        body = os.read(fd, MAX_STATUS_BYTES + 1)
        after = os.fstat(fd)
        if (len(body) != before.st_size or
                (before.st_size, before.st_mtime_ns, before.st_ctime_ns) !=
                (after.st_size, after.st_mtime_ns, after.st_ctime_ns)):
            raise ValueError("Status text changed during readiness observation")
        body.decode("utf-8")
        return hashlib.sha256(body).hexdigest()
    finally:
        os.close(fd)


def evaluate_readiness(directory, *, now=None, identity_checker=None):
    """Evaluate local receipts without polling, writing, signalling or launching.

    A healthy held/paused campaign can have monitoring ready. File timestamps
    alone never establish a successful poll or remote publication. Old receipts
    must be refreshed by the current guardian while respecting normal cadence.
    """
    directory = Path(directory)
    observed = _epoch(time.time() if now is None else now)
    if observed is None:
        raise ValueError("Readiness observation time must be a finite timestamp")
    issues = {}
    def load(name):
        try:
            return read_json(directory / name)
        except FileNotFoundError:
            issues[name] = "missing"
        except (OSError, ValueError, TypeError, OverflowError):
            issues[name] = "unreadable or malformed"
        return {}
    def identity(pid, birth):
        if type(pid) is not int or pid <= 0 or not isinstance(birth, str) or not birth.isdigit():
            return False
        try:
            return ((identity_checker(pid, birth) if identity_checker else process_start(pid) == birth) is True)
        except (OSError, ValueError, TypeError):
            return False
    guard, mailbox, text, published, state, watcher = (
        load(name) for name in ("guardian.json", "mailbox-state.json", "status-text-state.json",
                               "status-publish.json", "state.json", "watcher.json"))
    stages = {name: {"ready": False, "missing": []} for name in ("guardian", "mailbox", "publication")}
    gs, ms, ps = (stages[name] for name in ("guardian", "mailbox", "publication"))
    started = _epoch(guard.get("started_at"))
    heartbeat = _epoch(guard.get("heartbeat_at"))
    live_guard = identity(guard.get("pid"), guard.get("start"))
    try:
        held = not lease_free(directory, "guardian.lock")
    except (OSError, ValueError, TypeError):
        held = False
    if not live_guard:
        gs["missing"].append("Current guardian process birth is unverified.")
    if not held:
        gs["missing"].append("Current guardian lease is unverified.")
    if started is None or started > observed + 5:
        gs["missing"].append("Current guardian started_at is missing or invalid.")
    if not _fresh(heartbeat, observed, GUARDIAN_MAX_AGE) or started is not None and heartbeat is not None and heartbeat < started:
        gs["missing"].append("Guardian heartbeat is stale, missing or predates this guardian.")
    gs.update(started_at=_utc(started), heartbeat_at=_utc(heartbeat),
              heartbeat_age_seconds=observed - heartbeat if heartbeat else None,
              identity_verified=live_guard, lease_verified=held)

    polled = _epoch(mailbox.get("last_successful_poll_at"))
    next_poll = _epoch(mailbox.get("next_poll_at"))
    if started is None or polled is None or polled < started:
        ms["missing"].append("A successful mailbox poll from this guardian instance is not yet proven.")
    if not _fresh(polled, observed, RECEIPT_MAX_AGE):
        ms["missing"].append("Successful mailbox poll is stale or unavailable.")
    if next_poll is None:
        ms["missing"].append("Next mailbox poll deadline is unavailable.")
    elif observed > next_poll + POLL_DEADLINE_GRACE:
        ms["missing"].append("The mailbox poll deadline is overdue.")
    if mailbox.get("last_error") not in (None, "") or mailbox.get("failures", 0) != 0:
        ms["missing"].append("Mailbox has an unresolved poll or delivery error.")
    ms.update(last_successful_poll_at=_utc(polled), next_poll_at=_utc(next_poll),
              successful_poll_age_seconds=observed - polled if polled else None)

    verified = _epoch(published.get("published_verified_at"))
    generated = _epoch(text.get("generated_at"))
    if started is None or verified is None or verified < started:
        ps["missing"].append("Verified status publication from this guardian instance is not yet proven.")
    if not _fresh(verified, observed, RECEIPT_MAX_AGE):
        ps["missing"].append("Verified remote status publication is stale or unavailable.")
    if started is None or generated is None or generated < started or not _fresh(generated, observed, RECEIPT_MAX_AGE):
        ps["missing"].append("The rendered status snapshot is stale or not from this guardian instance.")
    if not _oneof(published.get("status"), {"PUBLISHED", "UNCHANGED"}):
        ps["missing"].append("A successful PUBLISHED or UNCHANGED publication receipt is unavailable.")
    if not _oneof(text.get("status"), {"PUBLISHED", "UNCHANGED", "BACKOFF"}):
        ps["missing"].append("The current report has not completed remote publication; GENERATED alone is insufficient.")
    if published.get("intent") is not None or published.get("last_error") not in (None, ""):
        ps["missing"].append("Status publication has an unresolved intent or error.")
    if (published.get("repository"), published.get("branch"), published.get("path")) != (
            "phoenix-hacking/mckernel", "codex/mckernel-control-mailbox", "status.txt"):
        ps["missing"].append("The remote publication destination is unverified.")
    try:
        actual = _status_hash(directory / "status.txt")
    except (OSError, ValueError, TypeError):
        actual = None
        issues["status.txt"] = "missing, changed or malformed"
    remote = _hash(published.get("published_sha256"))
    outcome = text.get("publication") if isinstance(text.get("publication"), dict) else {}
    desired = _hash(outcome.get("desired_sha256"))
    if actual is None or remote is None or actual != remote:
        ps["missing"].append("Current local status bytes do not match the verified published SHA-256.")
    if _oneof(text.get("status"), {"PUBLISHED", "UNCHANGED"}):
        if (desired != actual or outcome.get("desired_current") is not True
                or _hash(outcome.get("published_sha256")) != remote
                or not _oneof(outcome.get("status"), {"PUBLISHED", "UNCHANGED"})):
            ps["missing"].append("The current rendered desired hash lacks a matching successful publication receipt.")
    elif desired is not None and desired != actual:
        ps["missing"].append("The retained desired hash differs from the actual status bytes.")
    ps.update(published_verified_at=_utc(verified), generated_at=_utc(generated),
              publication_age_seconds=observed - verified if verified else None,
              actual_sha256=actual, published_sha256=remote)

    # Reject a guardian replacement observed during this multi-file read.
    latest = load("guardian.json")
    keys = ("pid", "start", "run_id", "started_at")
    if any(latest.get(key) != guard.get(key) for key in keys) or not identity(guard.get("pid"), guard.get("start")):
        gs["missing"].append("Guardian changed or exited during readiness observation.")
    for stage in stages.values():
        stage["ready"] = not stage["missing"]

    worker_live = identity(state.get("worker_pid"), state.get("worker_start"))
    watcher_live = identity(watcher.get("watcher_pid"), watcher.get("watcher_start"))
    engine_live = bool(worker_live and watcher_live and watcher.get("worker_pid") == state.get("worker_pid")
                       and isinstance(guard.get("run_id"), str)
                       and state.get("guardian_run_id") == guard["run_id"] == watcher.get("guardian_run_id"))
    state_heartbeat = _epoch(state.get("heartbeat_at"))
    current_engine = engine_live and _fresh(state_heartbeat, observed, 120)
    goal = state.get("goal") if isinstance(state.get("goal"), dict) else {}
    goal_status = goal.get("status") if _oneof(goal.get("status"), {"active", "blocked", "paused", "complete", "usageLimited", "budgetLimited"}) else "unknown"
    phase = state.get("phase") if _oneof(state.get("phase"), {"running", "waiting_for_input", "repair_review", "stopped", "starting", "ready", "stopping"}) else "unknown"
    reason = state.get("stop_reason") or guard.get("reason")
    work = {"engine_live": engine_live, "snapshot_current": current_engine,
            "reported_goal_status": goal_status, "reported_phase": phase,
            "state": goal_status.upper() if current_engine else "UNVERIFIED" if state else "UNAVAILABLE",
            "reason": redact(reason, 400) if isinstance(reason, str) else None,
            "active_turn_count": len(state["active_turns"]) if current_engine and isinstance(state.get("active_turns"), dict) else None}
    return {"schema_version": 1, "observed_at": _utc(observed),
            "monitoring_ready": all(stage["ready"] for stage in stages.values()),
            "stages": stages, "missing_stages": [name for name, stage in stages.items() if not stage["ready"]],
            "next_due": {"mailbox_poll_at": _utc(next_poll), "mailbox_poll_epoch": next_poll,
                         "status_refresh_at": _utc(_epoch(text.get("next_refresh_at"))),
                         "publication_at": _utc(_epoch(published.get("next_publish_at")))},
            "work_state": work, "data_issues": issues,
            "limits": "Local monitoring evidence only; no email delivery, engineering acceptance, or permission to start or resume work is established."}
