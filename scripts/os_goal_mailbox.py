"""A bounded GitHub PR-comment mailbox for the existing same-Root instruction queue.

Network access uses supported ``gh api`` authentication without reading or logging
credentials. Replies are plain instructions, never shell commands. This module
never activates a goal, starts a controller, clears a hold, or claims email delivery.
"""
from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import time
from uuid import uuid4

from run_os_goal import queue_instruction
from os_goal_instruction_limits import MAX_INSTRUCTION_BYTES, validate_instruction
from os_goal_stop_log import _text as _redacted_text


STATE_FILE = "mailbox-state.json"
MARKER = "<!-- mckernel-mailbox:{event_id} -->"
_MAX_STATE_JSON = 8 * 1024 * 1024
# Keep ordinary polls at 100 comments/page; retry smaller pages only if needed.
_MAX_API_JSON = 32 * 1024 * 1024
_COMMENTS_PER_PAGE = 100
_MAX_COMMENTS = 1000


class MailboxStateLimitError(ValueError):
    """A larger state must never replace the last durable mailbox record."""


class MailboxResponseLimitError(ValueError):
    """The same comments may need smaller pages within the existing deadline."""


def _read(path):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_size > _MAX_STATE_JSON:
            raise ValueError("Mailbox JSON must be a bounded regular file")
        raw = os.read(fd, _MAX_STATE_JSON + 1)
        value = json.loads(raw)
        if not isinstance(value, dict):
            raise ValueError("Mailbox JSON must contain an object")
        return value
    finally:
        os.close(fd)


def _save(path, value):
    payload = (json.dumps(value, sort_keys=True) + "\n").encode("utf-8")
    if len(payload) > _MAX_STATE_JSON:
        raise MailboxStateLimitError(
            f"Mailbox state requires {len(payload)} bytes; maximum {_MAX_STATE_JSON}. "
            "Prior state and receipts are preserved; reconcile before adding more records.")
    temporary = path.with_name(path.name + "." + uuid4().hex + ".tmp")
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        parent = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(parent)
        finally:
            os.close(parent)
    finally:
        temporary.unlink(missing_ok=True)


def _gh_api(endpoint, *, method="GET", payload=None, timeout=10):
    """No shell, token discovery, credential output, or unbounded network wait."""
    gh = shutil.which("gh")
    if gh is None:
        raise RuntimeError("GitHub mailbox requires authenticated gh CLI")
    command = [gh, "api", "--method", method, endpoint]
    if payload is not None:
        command += ["--input", "-"]
    completed = subprocess.run(command, input=json.dumps(payload) if payload is not None else None,
                               text=True, capture_output=True, timeout=timeout, check=False)
    if completed.returncode:
        # gh stderr can include request details; retain only the exit class here.
        raise RuntimeError("GitHub mailbox API " + method + " failed (exit "
                           + str(completed.returncode) + "); check gh authentication/network")
    if len(completed.stdout.encode("utf-8")) > _MAX_API_JSON:
        raise MailboxResponseLimitError("GitHub mailbox response exceeded the bounded limit")
    return json.loads(completed.stdout) if completed.stdout.strip() else None


def _safe(value, limit=400):
    return " ".join((_redacted_text(value, limit) or "").split()).replace("@", "@\u200b")


def _sha(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                    allow_nan=False).encode()).hexdigest()


class Mailbox:
    def __init__(self, repo, directory, config):
        self.repo, self.directory = Path(repo), Path(directory)
        self.config = _read(Path(config)) if isinstance(config, (str, Path)) else dict(config)
        cfg = self.config
        self.remote = cfg.get("repo")
        if not isinstance(self.remote, str) or not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", self.remote):
            raise ValueError("Mailbox requires one explicit GitHub repository")
        self.issue = cfg.get("issue_number")
        self.user_id = cfg.get("authorized_user_id")
        self.login = cfg.get("authorized_user_login") or cfg.get("authorized_login")
        if (type(self.issue) is not int or self.issue <= 0 or type(self.user_id) is not int
                or self.user_id <= 0 or not isinstance(self.login, str)
                or not re.fullmatch(r"[A-Za-z0-9-]+", self.login)):
            raise ValueError("Mailbox requires a PR number and verified numeric user identity")
        self.workflow = cfg.get("workflow_file", "mckernel-mailbox-notify.yml")
        self.workflow_ref = cfg.get("workflow_ref", "development")
        if (not isinstance(self.workflow, str) or not re.fullmatch(r"[A-Za-z0-9_.-]+\.ya?ml", self.workflow)
                or not isinstance(self.workflow_ref, str) or not self.workflow_ref.strip()):
            raise ValueError("Mailbox workflow/ref is invalid")
        self.poll_seconds = cfg.get("poll_seconds", 600)
        if type(self.poll_seconds) not in (int, float) or not 30 <= self.poll_seconds <= 3600:
            raise ValueError("Mailbox poll_seconds must be between 30 and 3600")
        self.binding = _sha([self.remote, self.issue, self.user_id])
        self.path = self.directory / STATE_FILE
        self._comments_per_page = _COMMENTS_PER_PAGE

    @contextmanager
    def _locked(self):
        self.directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        fd = os.open(self.directory / "mailbox.lock", os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX)
            yield
        finally:
            os.close(fd)

    def _state(self):
        try:
            state = _read(self.path)
        except FileNotFoundError:
            baseline = self.config.get("after_comment_id", 0)
            if type(baseline) is not int or baseline < 0:
                raise ValueError("Invalid mailbox comment baseline")
            return {"schema_version": 1, "binding": self.binding,
                    "last_seen_comment_id": baseline, "reply_epoch": 0,
                    "notices": {}, "messages": {}, "pending_resumes": [], "failures": 0, "next_poll_at": 0}
        if (state.get("schema_version") != 1 or state.get("binding") != self.binding
                or type(state.get("last_seen_comment_id")) is not int
                or not isinstance(state.get("notices"), dict)
                or not isinstance(state.get("pending_resumes"), list)):
            raise ValueError("Mailbox state/config binding is invalid; retain for reconciliation")
        state.setdefault("messages", {})
        if not isinstance(state["messages"], dict):
            raise ValueError("Mailbox message receipts are invalid")
        return state

    def _result(self, state, status, **fields):
        event_id = state.get("active_notice_event_id")
        notice = state["notices"].get(event_id, {})
        result = {"status": status, "issue_number": self.issue, "notice_event_id": event_id,
                  "notice_requested": bool(notice.get("requested")),
                  "observed_notice": bool(notice.get("observed_comment_id")),
                  "next_poll_at": state.get("next_poll_at", 0),
                  "messages": state["messages"],
                  "outbox_pending": sum(not n.get("observed_comment_id") and not n.get("superseded") for n in state["notices"].values()), **fields}
        if state["pending_resumes"]:
            request = state["pending_resumes"][0]
            result.update(resume_request_id=request["request_id"], resume_comment_id=request["comment_id"],
                          resume_created_at=request["resume_created_at"])
        return result

    def _comments(self):
        comments, page, deadline = [], 1, time.monotonic() + 30
        while len(comments) < _MAX_COMMENTS:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise RuntimeError("GitHub mailbox pagination exceeded poll time budget")
            per_page = self._comments_per_page
            try:
                rows = _gh_api(f"repos/{self.remote}/issues/{self.issue}/comments?per_page={per_page}&page={page}",
                               timeout=min(10, remaining))
            except MailboxResponseLimitError:
                if per_page == 1:
                    raise
                self._comments_per_page = max(1, per_page // 2)
                # Page numbering changes with page size. Restart collection,
                # retaining both the deadline and the last durable cursor.
                comments, page = [], 1
                continue
            if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
                raise ValueError("GitHub returned malformed mailbox comments")
            if len(rows) > per_page or len(comments) + len(rows) > _MAX_COMMENTS:
                raise RuntimeError("GitHub mailbox exceeds bounded pagination; reconcile before polling")
            comments.extend(rows)
            if len(rows) < per_page:
                return sorted(comments, key=lambda row: row.get("id") if type(row.get("id")) is int else -1)
            page += 1
        raise RuntimeError("GitHub mailbox exceeds bounded pagination; reconcile before polling")

    def _capacity_error(self, error, now, queued):
        # Only unpublished memory is discarded. Any durable enqueue intent,
        # cursor and receipt remain intact for the next idempotent poll.
        retained = self._state()
        retained.update(last_error=_safe(str(error), 500),
                        failures=min(int(retained.get("failures", 0)) + 1, 5),
                        next_poll_at=now + max(600, self.poll_seconds))
        try:
            _save(self.path, retained)
        except MailboxStateLimitError:
            pass  # No room for error metadata: preserve exact prior bytes.
        return self._result(retained, "ERROR", reason=_safe(str(error), 500),
                            queued_instruction_ids=queued)

    @staticmethod
    def _current_stop(stop, state, context, mode):
        """Do not turn retained diagnostics into the current blocker's cause."""
        identities = stop.get("identities") if isinstance(stop.get("identities"), dict) else {}
        current_log, recorded_log = state.get("log_dir"), stop.get("log_dir")
        if isinstance(current_log, str) and current_log and isinstance(recorded_log, str) and recorded_log:
            if current_log != recorded_log:
                return False
            same_thread = (isinstance(state.get("thread_id"), str) and bool(state["thread_id"])
                           and identities.get("thread_id") == state["thread_id"])
            same_worker = (type(state.get("worker_pid")) is int and state["worker_pid"] > 0
                           and str(identities.get("worker_pid")) == str(state["worker_pid"])
                           and isinstance(state.get("worker_start"), str) and bool(state["worker_start"])
                           and identities.get("worker_start") == state["worker_start"])
            if same_thread or same_worker:
                return True
        # Guardian-owned holds without an engine identity still have an actual
        # current reason. A conflicting recorded invocation above remains vetoed.
        reason = context.get("reason")
        return (mode == "HELD" and isinstance(reason, str) and bool(reason)
                and stop.get("event") == "guardian_held" and stop.get("reason") == reason)

    def _blocker(self, context):
        if not isinstance(context, dict):
            raise ValueError("Mailbox poll requires a context object")
        mode = context.get("status") or context.get("mode") or context.get("phase")
        mode = mode.upper() if isinstance(mode, str) else None
        if mode in {"ACTIVE", "RUNNING", "COMPLETE", "COMPLETED"}:
            return None
        state = next((context[key] for key in ("engine_state", "state")
                      if isinstance(context.get(key), dict)), context)
        if "latest_stop" in context or "stop_record" in context:
            supplied = context.get("latest_stop") if "latest_stop" in context else context.get("stop_record")
            stop = supplied if isinstance(supplied, dict) else {}
        else:
            try:
                stop = _read(self.directory / "latest-stop.json")
            except FileNotFoundError:
                stop = {}
        if not self._current_stop(stop, state, context, mode):
            stop = {}
        goal = state.get("goal") if isinstance(state.get("goal"), dict) else {}
        goal_status = context.get("goal_status") or goal.get("status") or stop.get("goal_status")
        fresh_reason = context.get("stop_reason") or context.get("reason") or state.get("stop_reason")
        if (mode == "SUPERVISED" and goal_status == "active"
                and state.get("phase") == "running" and not fresh_reason):
            return None
        reason = fresh_reason or stop.get("reason")
        if mode not in {"HELD", "WAITING", "BLOCKED", "STOPPING", "STOPPED", "FAILED"} and goal_status != "blocked" and not fresh_reason:
            return None
        error = stop.get("error") if isinstance(stop.get("error"), dict) else {}
        material = {"category": _safe(context.get("category") or stop.get("category")),
                    "reason": _safe(reason), "error_code": _safe(error.get("code")),
                    "error_message": _safe(error.get("message")),
                    "missing_input": _safe(context.get("missing_input")),
                    "next_action": _safe(context.get("next_action") or stop.get("remedy")),
                    "route": _safe(context.get("route") or stop.get("route"))}
        lines = ["## 📤 SENT — computer → phone", "", "### ⏳ WAITING FOR YOUR REPLY", "",
                 "Original M14/M15 acceptance is unfinished. Current blocker:"]
        lines += [f"- **{key.replace('_', ' ')}:** {value}" for key, value in material.items() if value]
        if not any(material.values()):
            lines.append("- The campaign is blocked; the exact missing input still needs diagnosis.")
        lines += ["", "Reply in this PR with `/mckernel-instruct` on the first line and your instruction below it,",
                  "or `/mckernel-resume` for explicit manual continuation. Existing service, permission,",
                  "usage, source and native/resource holds remain binding. GitHub notification requested;",
                  "email delivery depends on your GitHub notification settings."]
        body = "\n".join(lines).encode("utf-8")[:6000].decode("utf-8", errors="ignore")
        return material, body

    @staticmethod
    def _utc(epoch=None):
        return datetime.fromtimestamp(time.time() if epoch is None else epoch, timezone.utc).isoformat().replace("+00:00", "Z")

    def _event(self, state, kind, key, body, **fields):
        event_id = _sha([self.binding, kind, key])
        if event_id not in state["notices"]:
            state["notices"][event_id] = {"event_id": event_id, "kind": kind, "body": body,
                "requested": False, "created_order": len(state["notices"]), "created_at": self._utc(), **fields}
        return event_id

    def _received(self, state, intent, request_id=None, reason=None):
        comment_id = intent["comment_id"]
        key = str(comment_id)
        if key in state["messages"]:
            return state["messages"][key]
        url = f"https://github.com/{self.remote}/pull/{self.issue}#issuecomment-{comment_id}"
        message = {"comment_id": comment_id, "comment_url": url, "request_id": request_id,
                   "source_created_at": intent.get("comment_created_at"),
                   "received_at": intent.get("received_at"),
                   "command_recognized": intent.get("command") in {"/mckernel-instruct", "/mckernel-resume"},
                   "delivery_status": "WAITING" if request_id else "NOT_QUEUED"}
        lines = ["## 📥 RECEIVED — phone → computer", "",
                 f"- Your message: [comment #{comment_id}]({url})",
                 "- 📤 GitHub sent timestamp: " + (message["source_created_at"] or "unavailable in preserved record"),
                 "- 📥 Computer received timestamp: " + (message["received_at"] or "unavailable in preserved record")]
        if request_id:
            raw = intent["instruction"].encode("utf-8")
            message.update(instruction_utf8_bytes=len(raw),
                           instruction_sha256=hashlib.sha256(raw).hexdigest())
            lines += [f"- Queued instruction: `{request_id}`", "", "**⏳ WAITING for controller acceptance.**",
                      f"Instruction: {len(raw)} UTF-8 bytes including mailbox provenance; maximum {MAX_INSTRUCTION_BYTES}.",
                      f"Instruction SHA-256: `{message['instruction_sha256']}`.",
                      "The instruction is saved once. Queueing does not prove controller acceptance or completed work."]
        else:
            message["not_queued_reason"] = reason or "No supported first-line command was supplied."
            lines += ["", "**⏳ WAITING for a new valid instruction — NOT QUEUED.**",
                      message["not_queued_reason"],
                      "Put `/mckernel-instruct` or `/mckernel-resume` on the first line of a new comment; put your instruction below it."]
        message["received_event_id"] = self._event(state, "received", comment_id, "\n".join(lines), comment_id=comment_id)
        state["messages"][key] = message
        return message

    def _inspect_deliveries(self, state):
        for message in state["messages"].values():
            ident = message.get("request_id")
            if message.get("delivery_status") != "WAITING" or not isinstance(ident, str):
                continue
            if not re.fullmatch(r"source-[0-9a-f]{64}", ident):
                continue
            try:
                receipt = _read(self.directory / "instructions/delivered" / (ident + ".json"))
            except (OSError, ValueError):
                continue  # Missing, unreadable or ambiguous delivery remains WAITING.
            if (receipt.get("id") != ident or receipt.get("status") != "accepted_by_server"
                    or not all(isinstance(receipt.get(k), str) and receipt[k].strip()
                               for k in ("thread_id", "turn_id", "delivered_at"))):
                continue
            try:
                accepted = datetime.fromisoformat(receipt["delivered_at"].replace("Z", "+00:00"))
                if accepted.tzinfo is None:
                    continue
            except ValueError:
                continue
            message.update(delivery_status="ACCEPTED", controller_accepted_at=receipt["delivered_at"],
                           controller_thread_id=receipt["thread_id"], controller_turn_id=receipt["turn_id"])
            body = "\n".join(["## ✅ RECEIVED BY CONTROLLER — instruction accepted", "",
                f"- Your message: [comment #{message['comment_id']}]({message['comment_url']})",
                "- 📤 GitHub sent timestamp: " + (message["source_created_at"] or "unavailable in preserved record"),
                "- 📥 Computer received timestamp: " + (message["received_at"] or "unavailable in preserved record"),
                f"- Queued instruction: `{ident}`",
                "- ✅ Controller accepted timestamp: " + receipt["delivered_at"],
                f"- Controller thread / turn: `{_safe(receipt['thread_id'])}` / `{_safe(receipt['turn_id'])}`", "",
                "Controller acceptance is confirmed. **⏳ WAITING for the work result**; this does not claim completed work or release a genuine hold."])
            message["accepted_event_id"] = self._event(state, "accepted", ident, body,
                comment_id=message["comment_id"], requires_event_id=message["received_event_id"])

    def _drain_outbox(self, state, now):
        if state.get("last_comments_read_at", 0) < state.get("outbox_retry_poll_after", 0):
            return None
        priorities = {"received": 0, "accepted": 1, "blocker": 2}
        notices = sorted(state["notices"].values(), key=lambda n: (priorities.get(n.get("kind", "blocker"), 2), n.get("created_order", 0)))
        for notice in notices:
            if notice.get("observed_comment_id") or notice.get("superseded"):
                continue
            prerequisite = notice.get("requires_event_id")
            if prerequisite and not state["notices"].get(prerequisite, {}).get("observed_comment_id"):
                continue
            if notice.get("last_dispatch_at") is not None and (
                    now < notice["last_dispatch_at"] + max(600, self.poll_seconds)
                    or state.get("last_comments_read_at", 0) < notice.get("retry_after_poll_at", 0)):
                continue
            notice.update(last_dispatch_at=now, retry_after_poll_at=now + max(600, self.poll_seconds))
            _save(self.path, state)
            try:
                _gh_api(f"repos/{self.remote}/actions/workflows/{self.workflow}/dispatches", method="POST",
                        payload={"ref": self.workflow_ref, "inputs": {"event_id": notice["event_id"], "body": notice["body"]}}, timeout=10)
            except (OSError, ValueError, RuntimeError, subprocess.SubprocessError):
                state["outbox_retry_poll_after"] = now + max(600, self.poll_seconds)
                _save(self.path, state)
                raise
            notice.update(requested=True, requested_at=self._utc(now))
            _save(self.path, state)
            return notice["event_id"]  # At most one bounded POST per monitor tick.
        return None

    def _finish_enqueue(self, state):
        intent = state["enqueue_intent"]
        if _sha(intent["instruction"]) != intent["text_sha256"]:
            raise ValueError("Mailbox enqueue intent changed; reconcile without replay")
        if intent["command"] == "/mckernel-resume" and type(intent.get("resume_created_at")) not in (int, float):
            raise ValueError("Manual resume lacks its original GitHub timestamp; reconcile without replay")
        request_id = queue_instruction(self.directory, intent["instruction"], source_id=intent["source_id"])
        if intent["command"] == "/mckernel-resume" and not any(
                item["request_id"] == request_id for item in state["pending_resumes"]):
            state["pending_resumes"].append({"request_id": request_id, "comment_id": intent["comment_id"],
                                             "resume_created_at": intent["resume_created_at"]})
        self._received(state, intent, request_id)
        state["reply_epoch"] += 1
        state["last_seen_comment_id"] = max(state["last_seen_comment_id"], intent["comment_id"])
        state.pop("enqueue_intent")
        _save(self.path, state)
        return request_id

    def poll(self, context):
        """Read phone comments at the configured cadence; drain one receipt per tick."""
        with self._locked():
            state = self._state()
            now = time.time()
            due = now >= state.get("next_poll_at", 0)
            queued, replied = [], False
            try:
                if due:
                    state["last_poll_at"] = now
                    _save(self.path, state)
                if state.get("enqueue_intent"):
                    queued.append(self._finish_enqueue(state))
                    replied = True
                if due:
                    comments = self._comments()
                    state["last_comments_read_at"] = now
                    for comment in comments:
                        ident = comment.get("id")
                        if type(ident) is not int or ident <= 0:
                            continue
                        user = comment.get("user") if isinstance(comment.get("user"), dict) else {}
                        body = comment.get("body")
                        if user.get("type") == "Bot" and user.get("login") == "github-actions[bot]" and isinstance(body, str):
                            for event_id, notice in state["notices"].items():
                                if MARKER.format(event_id=event_id) in body:
                                    notice.update(observed_comment_id=ident, observed_sent_at=comment.get("created_at"),
                                                  observed_at=self._utc(now))
                        if ident <= state["last_seen_comment_id"]:
                            continue
                        owner = (type(user.get("id")) is int and user["id"] == self.user_id
                                 and user.get("type") == "User" and isinstance(user.get("login"), str)
                                 and user["login"].casefold() == self.login.casefold())
                        if owner:
                            for notice in state["notices"].values():
                                if notice.get("kind", "blocker") == "blocker":
                                    notice["superseded"] = True
                            lines = body.splitlines() if isinstance(body, str) else []
                            command = lines[0].strip() if lines else ""
                            intent = {"comment_id": ident, "command": command,
                                      "comment_created_at": comment.get("created_at"), "received_at": self._utc(now)}
                            unedited = (isinstance(comment.get("created_at"), str) and bool(comment["created_at"])
                                        and comment["created_at"] == comment.get("updated_at"))
                            text = "\n".join(lines[1:]).strip()
                            if command == "/mckernel-resume" and not text:
                                text = "Explicit manual continuation requested. Reconcile current controls and continue eligible work; genuine holds remain binding."
                            reason = "No supported first-line command was supplied."
                            if not unedited:
                                reason = "Edited or unattributed comments are not executed; post a new comment."
                            elif command in {"/mckernel-instruct", "/mckernel-resume"} and text:
                                url = f"https://github.com/{self.remote}/pull/{self.issue}#issuecomment-{ident}"
                                instruction = (f"Verified GitHub mailbox instruction from {self.login} (user id {self.user_id}).\n"
                                               f"Source: {url}\nCommand: {command}\n\n{text}")
                                try:
                                    validate_instruction(instruction)
                                except ValueError as error:
                                    reason = str(error) + " Mailbox provenance is included; post a shorter new comment."
                                    state["rejected_comment"] = {"comment_id": ident, "reason": reason}
                                else:
                                    intent.update(source_id=f"github:{self.remote}:{self.issue}:{ident}",
                                                  instruction=instruction, text_sha256=_sha(instruction))
                                    if command == "/mckernel-resume":
                                        intent["resume_created_at"] = datetime.strptime(comment["created_at"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc).timestamp()
                                    state["enqueue_intent"] = intent
                                    _save(self.path, state)
                                    queued.append(self._finish_enqueue(state))
                            elif command == "/mckernel-instruct":
                                reason = "The instruction body is empty; post a new comment with the direction below its first-line command."
                            if str(ident) not in state["messages"]:
                                self._received(state, intent, reason=reason)
                                state["reply_epoch"] += 1
                            replied = True
                        state["last_seen_comment_id"] = ident
                        _save(self.path, state)
                    state["next_poll_at"] = now + self.poll_seconds
                    _save(self.path, state)
                # Local health can change between comment polls. Never drain an
                # obsolete blocker merely because a ten-minute GET is not due.
                blocker = self._blocker(context)
                event_id = _sha([self.binding, blocker[0], state["reply_epoch"]]) if blocker is not None else None
                for old_id, old in state["notices"].items():
                    if old.get("kind", "blocker") == "blocker":
                        old["superseded"] = old_id != event_id
                state["active_notice_event_id"] = event_id if event_id in state["notices"] else None
                if due and blocker is not None and not replied and event_id not in state["notices"]:
                    state["active_notice_event_id"] = event_id
                    state["notices"][event_id] = {"event_id": event_id, "kind": "blocker", "body": blocker[1],
                        "requested": False, "superseded": False, "created_order": len(state["notices"]), "created_at": self._utc(now)}
                self._inspect_deliveries(state)
                _save(self.path, state)
                dispatched = self._drain_outbox(state, now)
                if due:
                    state.update(failures=0, last_error=None, last_successful_poll_at=now)
                _save(self.path, state)
                return self._result(state, "POLLED" if due else "BACKOFF", queued_instruction_ids=queued, dispatched_event_id=dispatched)
            except MailboxStateLimitError as error:
                return self._capacity_error(error, now, queued)
            except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
                failures = min(int(state.get("failures", 0)) + 1, 5)
                state.update(failures=failures, last_error=_safe(str(error), 500))
                if due and state.get("next_poll_at", 0) <= now:
                    state["next_poll_at"] = now + min(max(900, self.poll_seconds), self.poll_seconds * 2 ** (failures - 1))
                try:
                    _save(self.path, state)
                except MailboxStateLimitError as capacity_error:
                    return self._capacity_error(capacity_error, now, queued)
                return self._result(state, "ERROR", reason=state["last_error"], queued_instruction_ids=queued)

    def ack_resume(self, request_id):
        """Guardian calls after durably recording its handling; no control changes."""
        with self._locked():
            state = self._state()
            state["pending_resumes"] = [item for item in state["pending_resumes"] if item["request_id"] != request_id]
            _save(self.path, state)

