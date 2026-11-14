"""Compact mailbox telemetry; full durable history has no application size cap.

These derived snapshots carry no instruction text or execution authority. Only
mailbox-state.json uses this reader; bounded ownership/recovery receipts keep
their existing reader and validation.
"""
from datetime import datetime, timezone
import json
import math
import os
import stat


_RECENT = 100
_STATUSES = ("WAITING", "ACCEPTED", "NOT_QUEUED", "ASSEMBLING", "PART_OF_QUEUED", "REJECTED_ASSEMBLY")
_RECEIPT_FIELDS = {
    "source_kind", "source_key", "source_label", "source_url", "source_commit_sha", "source_blob_sha",
    "comment_id", "comment_url", "request_id", "source_created_at", "received_at", "command_recognized",
    "delivery_status", "instruction_utf8_bytes", "instruction_sha256", "not_queued_reason",
    "received_event_id", "accepted_event_id", "controller_accepted_at", "controller_thread_id",
    "controller_turn_id", "multipart_id", "logical_request_id", "completed_comment_id", "reason",
}
_NOTICE_FIELDS = {
    "event_id", "kind", "requested", "created_order", "created_at", "source_key", "comment_id",
    "observed_comment_id", "observed_sent_at", "observed_at", "superseded", "publish_to_file",
    "last_dispatch_at", "retry_after_poll_at", "requires_event_id",
}
_FILE_FIELDS = {
    "status", "path", "branch", "commit_sha", "blob_sha", "source_url", "byte_size", "request_id",
    "received_at", "controller_accepted_at", "event_id", "retry_after", "last_error", "published_at", "checked_at",
    "sha", "content_sha", "commit_url", "url",
}


def _compact(value):
    if isinstance(value, str):
        return value if len(value) <= 2048 else value[:2047] + "…"
    if value is None or isinstance(value, bool) or type(value) is int:
        return value
    if type(value) is float and math.isfinite(value):
        return value
    return None


def _metadata(value, fields):
    if not isinstance(value, dict):
        return {}
    return {key: _compact(value[key]) for key in sorted(fields & value.keys())}


def _timestamp(value):
    if type(value) in (int, float) and math.isfinite(value):
        return value
    if isinstance(value, str):
        try:
            when = datetime.fromisoformat(value.replace("Z", "+00:00"))
            if when.tzinfo is not None:
                return when.astimezone(timezone.utc).timestamp()
        except (ValueError, OverflowError, OSError):
            pass
    return float("-inf")


def _recent(rows, timestamp):
    if not isinstance(rows, dict) or any(not isinstance(key, str) for key in rows):
        raise ValueError("Mailbox telemetry collections must have opaque string keys")
    return sorted(rows.items(), key=lambda row: (
        _timestamp(row[1].get(timestamp)) if isinstance(row[1], dict) else float("-inf"), row[0]))[-_RECENT:]


def receipt_source_label(message, key):
    """File revisions have opaque source identities, never invented comment IDs."""
    if message.get("source_kind") == "file":
        return message.get("source_label") or message.get("source_key") or "GitHub file"
    if type(message.get("comment_id")) is int and message["comment_id"] > 0:
        return "message #" + str(message["comment_id"])
    return message.get("source_label") or message.get("source_key") or key


def summarize_mailbox_state(state):
    """Return recent receipt metadata and accurate totals without body/history data."""
    if not isinstance(state, dict):
        raise ValueError("Mailbox state must contain an object")
    messages, notices = state.get("messages", {}), state.get("notices", {})
    recent_messages = _recent(messages, "received_at")
    recent_notices = _recent(notices, "created_at")
    counts = {name: 0 for name in _STATUSES}
    for message in messages.values():
        status = message.get("delivery_status") if isinstance(message, dict) else None
        status = status if status in _STATUSES else "UNKNOWN"
        counts[status] = counts.get(status, 0) + 1
    summary = _metadata(state, {
        "schema_version", "last_poll_at", "last_successful_poll_at", "next_poll_at", "last_error",
        "comment_scan_pending", "last_comments_read_at", "active_notice_event_id", "failures",
    })
    summary.update(messages={key: _metadata(value, _RECEIPT_FIELDS) for key, value in recent_messages},
                   message_count=len(messages), message_status_counts=counts,
                   notices={key: _metadata(value, _NOTICE_FIELDS) for key, value in recent_notices},
                   notice_count=len(notices), outbox_pending=sum(
                       isinstance(value, dict) and not value.get("observed_comment_id") and not value.get("superseded")
                       for value in notices.values()))
    event = state.get("active_notice_event_id")
    active = notices.get(event, {}) if isinstance(event, str) else {}
    active = active if isinstance(active, dict) else {}
    summary.update(notice_requested=bool(active.get("requested")),
                   observed_notice=bool(active.get("observed_comment_id")),
                   observed_comment_id=_compact(active.get("observed_comment_id")))
    for key in ("file_inbox", "file_reply"):
        if key in state:
            summary[key] = _metadata(state[key], _FILE_FIELDS)
    pending = state.get("pending_resumes", [])
    if not isinstance(pending, list):
        raise ValueError("Mailbox pending resumes must be a list")
    summary.update(pending_resume_count=len(pending), pending_resumes=[_metadata(value, {
        "request_id", "comment_id", "source_kind", "source_key", "source_url", "resume_created_at",
    }) for value in pending[:_RECENT]])
    return summary


def read_mailbox_status(path):
    """Read complete owned mailbox history safely, then expose compact telemetry."""
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or before.st_uid != os.getuid():
            raise ValueError("Expected owned regular mailbox state")
        chunks, size = [], 0
        while size <= before.st_size:
            chunk = os.read(fd, min(65536, before.st_size + 1 - size))
            if not chunk:
                break
            chunks.append(chunk)
            size += len(chunk)
        after = os.fstat(fd)
        if (size != before.st_size or
                (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns, before.st_ctime_ns, before.st_uid) !=
                (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns, after.st_uid)):
            raise ValueError("Mailbox state changed while reading")
        state = json.loads(b"".join(chunks).decode("utf-8"))
        return summarize_mailbox_state(state)
    finally:
        os.close(fd)
