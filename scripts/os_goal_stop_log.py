"""Durable, bounded stop diagnostics; this module never starts or retries work."""
import fcntl
import json
import os
from pathlib import Path
import re
import stat
from datetime import datetime, timezone
from uuid import uuid4


JOURNAL = "stop-events.jsonl"
LATEST = "latest-stop.json"
IDENTITIES = ("worker_pid", "worker_start", "server_pid", "server_start", "thread_id",
              "watcher_pid", "watcher_start")


def _text(value, limit=1024):
    if value is None:
        return None
    if not isinstance(value, (str, int, float, bool)):
        return None
    # Bound before regex processing; never serialize arbitrary error/state objects.
    value = str(value)[:limit * 4]
    value = re.sub(r"(?i)\b(bearer\s+)\S+", r"\1[REDACTED]", value)
    value = re.sub(r"\bsk-[A-Za-z0-9_-]+", "[REDACTED]", value)
    value = re.sub(r"(?i)\b((?:api[_-]?key|access[_-]?token|refresh[_-]?token|"
                   r"token|password|passwd|secret|authorization|cookie)\s*[:=]\s*)"
                   r"(?:\"[^\"]*\"|'[^']*'|[^\s,;]+)", r"\1[REDACTED]", value)
    value = re.sub(r"(https?://)[^/\s:@]+:[^/\s@]+@", r"\1[REDACTED]@", value)
    return value[:limit]


def _current(state, provenance):
    if (not isinstance(provenance, dict) or not isinstance(state.get("log_dir"), str)
            or not state["log_dir"]):
        return False
    if provenance.get("log_dir") != state["log_dir"]:
        return False
    return all(state.get(key) is None or provenance.get(key) is None
               or state[key] == provenance[key] for key in IDENTITIES)


def _error_fields(error):
    if error is None:
        return None
    if isinstance(error, BaseException):
        return {"code": type(error).__name__, "message": _text(str(error))}
    if isinstance(error, str):
        return {"code": None, "message": _text(error)}
    if not isinstance(error, dict):
        return {"code": None, "message": None, "unrecognized_type": type(error).__name__}
    inner = error.get("error")
    inner = inner if isinstance(inner, dict) else {}
    code = next((item for item in (error.get("codexErrorInfo"), error.get("code"),
                                  error.get("error_code"), inner.get("codexErrorInfo"),
                                  inner.get("code")) if item is not None), None)
    # Some protocol errors encode codexErrorInfo as a tagged object.
    if isinstance(code, dict):
        code = code.get("type") or code.get("code")
    message = error.get("message") or inner.get("message")
    return {"code": _text(code, 128), "message": _text(message)}


def _diagnostic(state, error):
    if error is not None:
        return _error_fields(error), "current_event", []
    retained = []
    for key in ("last_error", "last_failure"):
        value = state.get(key)
        if value is None:
            continue
        provenance = state.get("last_error_provenance") if key == "last_error" else value
        matches = _current(state, provenance)
        if key == "last_error":
            matches = matches and provenance.get("error") == value
        if matches:
            return _error_fields(value if key == "last_error" else value.get("error")), key, retained
        # Preserve attribution evidence without copying old error messages or prompts.
        retained.append({"field": key, "attribution": "other_or_unknown_invocation",
                         "log_dir": _text(provenance.get("log_dir"))
                         if isinstance(provenance, dict) else None})
    return None, "unavailable", retained


def _route(reason, error, goal_status):
    why = (reason or "").lower()
    code = (error or {}).get("code") or ""
    message = (error or {}).get("message") or ""
    if why.startswith("signal_") or why in {"user_requested", "user_stop", "paused"}:
        return "user_stop", "Respect the current user stop; resume only under current authorization.", "user"
    if code.lower() in {"cyberpolicy", "policyviolation", "contentpolicyviolation"}:
        return "policy_rejection", "Preserve the exact rejected request evidence; route through the supported review path. Do not replay or reassign the rejected request or infer missing scope.", "supported_review"
    if (why in {"quota_exhausted", "included_usage_guard", "credit_budget_exhausted",
                "budget_exhausted", "credit_balance_decreased"}
            or code.lower() in {"usagelimitexceeded", "quotaexceeded", "quotaexhausted"}):
        return "usage_limit", "Check fresh included allowance and original account controls before any further model work; no paid fallback.", "account_usage"
    if any(word in why for word in ("usage_unknown", "budget_unknown", "balance_unknown")):
        return "usage_unknown", "Repair the usage observation through its normal read-only path; retain the stop until actual allowance is known.", "account_usage"
    if ("auth" in why or code.lower() in {"unauthorized", "authenticationerror", "authenticationrequired", "401"}
            or re.search(r"\b(?:authentication required|not authenticated|invalid authentication|unauthorized)\b", message, re.I)):
        return "authentication", "Restore the supported account authentication path, then verify the current goal and controls; do not replay work while authentication is unresolved.", "account_authentication"
    if (code.lower() in {"permissionerror", "permissiondenied", "accessdenied", "forbidden", "eacces", "eperm", "403"}
            or re.search(r"\b(?:permission denied|access denied|operation not permitted)\b", message, re.I)):
        return "permission_denied", "Record the exact denied operation and scope; obtain the required access through its supported owner. Do not elevate, bypass or replay the denied operation.", "access_owner"
    if any(word in why for word in ("ownership", "current_free", "resource_hold", "source_hold", "sdk_binding")):
        return "binding_or_ownership", "Identify the exact missing binding or original owner and obtain the required scoped input; preserve UNKNOWN ownership and rejected-request restrictions.", "original_owner"
    if why in {"rpc_delivery_uncertain", "mutating_rpc_delivery_uncertain", "transport_uncertain"}:
        return "delivery_uncertain", "Reconcile the actual submitted operation and joins before retrying; never replay a possibly delivered mutation.", "operation_reconciliation"
    if why in {"work_window", "time_limit", "checkpoint"}:
        return "work_window", "Checkpoint and join work, then continue through the normal authorized controller path within the current work window.", "controller"
    if (why in {"launcher_error", "server_error", "turn_failed", "watchdog_recovery",
                "active_goal_did_not_continue", "rate_limit"}
            or re.search(r"timeout|connection|temporar|overload|rate.?limit|\b503\b", code + " " + message, re.I)):
        return "technical_failure", "Diagnose and fix the current launcher, transport or source failure; verify operation delivery and preserved controls before a bounded normal retry.", "repair_agent"
    if why == "requested_milestones_complete":
        return "requested_milestones_complete", "Verify original M14/M15 closure evidence and record the requested milestone result before stopping the authorized campaign.", "acceptance_review"
    if goal_status in {"complete", "completed"}:
        return "goal_completed", "Verify original M14/M15 acceptance evidence before reporting completion.", "acceptance_review"
    if goal_status == "blocked" or why in {"goal_blocked", "blocked", "source_binding_impasse"}:
        return "campaign_blocked", "Diagnose the exact blocker and continue authorized independent repair or engineering. A missing scope record alone does not establish a new policy rejection; preserve actual holds.", "campaign_agent"
    return "unknown", "Inspect current-invocation evidence and identify the cause before choosing a repair or retry; do not infer permission, completion or release from missing data.", "diagnosis_agent"


def _directory_fd(directory):
    # Traverse every component with O_NOFOLLOW, including ancestors of the target.
    path = Path(os.path.abspath(os.fspath(directory)))
    fd = os.open(path.anchor, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        for part in path.parts[1:]:
            next_fd = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd)
            fd = next_fd
        return fd
    except BaseException:
        os.close(fd)
        raise


def _open_regular(directory_fd, name, flags):
    fd = os.open(name, flags | os.O_NOFOLLOW | os.O_NONBLOCK, 0o600, dir_fd=directory_fd)
    info = os.fstat(fd)
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
        os.close(fd)
        raise ValueError("Stop log destination must be a regular, singly linked file: " + name)
    return fd


def _write_all(fd, payload):
    while payload:
        written = os.write(fd, payload)
        if not written:
            raise OSError("Short stop journal write")
        payload = payload[written:]


def write_stop_record(directory, state, *, event, exit_code=None, error=None, reason=None):
    """Append a private diagnostic and atomically refresh latest-stop.json.

    ``directory`` must already exist. Explicit ``error`` belongs to this event;
    saved errors require matching recorded invocation provenance. Records contain
    only bounded allowlisted fields, never raw state, goal prompts or requests.
    The journal is authoritative if a crash interrupts the latest-file refresh.
    """
    if not isinstance(state, dict):
        raise TypeError("state must be a dictionary")
    if not isinstance(event, str) or not event:
        raise ValueError("event must be a nonempty string")
    diagnostic, attribution, retained = _diagnostic(state, error)
    goal = state.get("goal") if isinstance(state.get("goal"), dict) else {}
    status = _text(goal.get("status"), 128)
    stop_reason = _text(reason if reason is not None else state.get("stop_reason"), 256)
    category, remedy, route = _route(stop_reason, diagnostic, status)
    log_dir = _text(state.get("log_dir"))
    record = {"schema_version": 1, "record_id": uuid4().hex,
              "recorded_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
              "event": _text(event, 128), "category": category,
              "invocation": _text(state.get("invocation"), 256) or (Path(log_dir).name if log_dir else None),
              "log_dir": log_dir, "identities": {key: _text(state.get(key), 256) for key in IDENTITIES},
              "turn_id": _text(state.get("turn_id"), 256), "phase": _text(state.get("phase"), 128),
              "goal_status": status, "exit_code": exit_code if exit_code is not None else state.get("exit_code"),
              "reason": stop_reason, "error": diagnostic, "error_attribution": attribution,
              "retained_diagnostics": retained, "remedy": remedy, "route": route,
              "request_scope": "not_inferred",
              "evidence": {key: _text(state.get(key)) for key in ("console_log", "recovery_handoff") if state.get(key)}}
    if not isinstance(record["exit_code"], (int, type(None))):
        record["exit_code"] = None
    failure = state.get("last_failure")
    if not record["turn_id"] and _current(state, failure):
        record["turn_id"] = _text(failure.get("id"), 256)
    active = state.get("active_turns")
    if (not record["turn_id"] and isinstance(active, dict)
            and isinstance(state.get("thread_id"), str)):
        record["turn_id"] = _text(active.get(state.get("thread_id")), 256)
    payload = (json.dumps(record, sort_keys=True, ensure_ascii=True) + "\n").encode("utf-8")
    directory_fd = _directory_fd(directory)
    lock_fd = None
    temporary = ".latest-stop-" + uuid4().hex + ".tmp"
    try:
        lock_fd = _open_regular(directory_fd, ".stop-log.lock", os.O_RDWR | os.O_CREAT)
        fcntl.flock(lock_fd, fcntl.LOCK_EX)
        try:
            info = os.stat(LATEST, dir_fd=directory_fd, follow_symlinks=False)
        except FileNotFoundError:
            pass
        else:
            if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
                raise ValueError("Unsafe latest stop destination")
        journal_fd = _open_regular(directory_fd, JOURNAL, os.O_WRONLY | os.O_APPEND | os.O_CREAT)
        try:
            _write_all(journal_fd, payload)
            os.fsync(journal_fd)
        finally:
            os.close(journal_fd)
        # Persist a newly created journal entry even if latest refresh fails.
        os.fsync(directory_fd)
        latest_fd = _open_regular(directory_fd, temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL)
        try:
            _write_all(latest_fd, payload)
            os.fsync(latest_fd)
        finally:
            os.close(latest_fd)
        os.replace(temporary, LATEST, src_dir_fd=directory_fd, dst_dir_fd=directory_fd)
        os.fsync(directory_fd)
    finally:
        if lock_fd is not None:
            os.close(lock_fd)
        try:
            os.unlink(temporary, dir_fd=directory_fd)
        except FileNotFoundError:
            pass
        os.close(directory_fd)
    return {"journal_path": str(Path(directory) / JOURNAL),
            "latest_path": str(Path(directory) / LATEST), "record": record}
