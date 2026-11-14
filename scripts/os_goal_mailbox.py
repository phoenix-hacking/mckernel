"""A paginated GitHub mailbox for the existing same-Root instruction queue.

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
from os_goal_mailbox_protocol import parse_instruction_part, split_message
from os_goal_file_mailbox import read_revision, write_reply
from os_goal_mailbox_status import summarize_mailbox_state
from os_goal_stop_log import _text as _redacted_text


STATE_FILE = "mailbox-state.json"
MARKER = "<!-- mckernel-mailbox:{event_id} -->"
_COMMENT_PAGE_SIZE = 50
_COMMENTS_QUERY = """query($owner: String!, $name: String!, $number: Int!, $after: String) {
  repository(owner: $owner, name: $name) {
    pullRequest(number: $number) {
      comments(first: 50, after: $after) {
        nodes {
          id: fullDatabaseId body created_at: createdAt updated_at: updatedAt
          user: author { type: __typename login ... on User { id: databaseId } }
        }
        pageInfo { endCursor hasNextPage }
      }
    }
  }
}"""


def _read(path):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode):
            raise ValueError("Mailbox JSON must be a regular file")
        with os.fdopen(fd, "r", encoding="utf-8", closefd=False) as stream:
            value = json.load(stream)
        after = os.fstat(fd)
        if (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns) != (
                after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns):
            raise ValueError("Mailbox JSON changed while reading")
        if not isinstance(value, dict):
            raise ValueError("Mailbox JSON must contain an object")
        return value
    finally:
        os.close(fd)


def _save(path, value):
    temporary = path.with_name(path.name + "." + uuid4().hex + ".tmp")
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        with os.fdopen(fd, "w") as stream:
            json.dump(value, stream, sort_keys=True)
            stream.write("\n")
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


def _gh_api(endpoint, *, method="GET", payload=None, timeout=10, accept=None):
    """No shell, token discovery, credential output, or unbounded network wait."""
    gh = shutil.which("gh")
    if gh is None:
        raise RuntimeError("GitHub mailbox requires authenticated gh CLI")
    command = [gh, "api", "--method", method, endpoint]
    if accept is not None:
        if accept != "application/vnd.github.object+json":
            raise ValueError("Unsupported mailbox media type")
        command += ["--header", "Accept: " + accept]
    if payload is not None:
        command += ["--input", "-"]
    completed = subprocess.run(command, input=json.dumps(payload) if payload is not None else None,
                               text=True, capture_output=True, timeout=timeout, check=False)
    if completed.returncode:
        # gh stderr can include request details; retain only the exit class here.
        raise RuntimeError("GitHub mailbox API " + method + " failed (exit "
                           + str(completed.returncode) + "); check gh authentication/network")
    return json.loads(completed.stdout) if completed.stdout.strip() else None


def _safe(value, limit=None):
    if limit is None:
        limit = len(value) if isinstance(value, str) else 400
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
        self.file_enabled = bool(cfg.get("file_inbox_path"))

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
                    "notices": {}, "messages": {}, "multipart": {}, "pending_resumes": [], "failures": 0, "next_poll_at": 0}
        if (state.get("schema_version") != 1 or state.get("binding") != self.binding
                or type(state.get("last_seen_comment_id")) is not int
                or not isinstance(state.get("notices"), dict)
                or not isinstance(state.get("pending_resumes"), list)):
            raise ValueError("Mailbox state/config binding is invalid; retain for reconciliation")
        state.setdefault("messages", {})
        if not isinstance(state["messages"], dict):
            raise ValueError("Mailbox message receipts are invalid")
        if state.get("comment_cursor") is not None and not isinstance(state["comment_cursor"], str):
            raise ValueError("Mailbox comment cursor is invalid")
        state.setdefault("multipart", {})
        if not isinstance(state["multipart"], dict):
            raise ValueError("Mailbox multipart receipts are invalid")
        return state

    def _result(self, state, status, **fields):
        # Keep full history in durable state; order and compact the status view
        # independently of JSON key order and opaque file-revision identities.
        result = summarize_mailbox_state(state)
        result.update(status=status, issue_number=self.issue,
                      notice_event_id=state.get("active_notice_event_id"),
                      next_poll_at=state.get("next_poll_at", 0),
                      comment_scan_pending=bool(state.get("comment_scan_pending")), **fields)
        if state["pending_resumes"]:
            request = state["pending_resumes"][0]
            result.update(resume_request_id=request["request_id"], resume_comment_id=request["comment_id"],
                          resume_created_at=request["resume_created_at"])
        return result

    def _comment_pages(self, state):
        """Checkpointed connection cursors have no total history/page limit.

        The per-poll deadline limits work, not mailbox capacity. The caller
        commits each cursor only after every comment on that page is durable.
        """
        owner, name = self.remote.split("/", 1)
        cursor, deadline = state.get("comment_cursor"), time.monotonic() + 30
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return  # A subsequent scheduled poll continues the saved cursor.
            reply = _gh_api("graphql", method="POST", payload={"query": _COMMENTS_QUERY,
                "variables": {"owner": owner, "name": name, "number": self.issue, "after": cursor}},
                timeout=min(10, remaining))
            try:
                if not isinstance(reply, dict) or reply.get("errors"):
                    raise ValueError
                connection = reply["data"]["repository"]["pullRequest"]["comments"]
                rows, page_info = connection["nodes"], connection["pageInfo"]
                next_cursor, more = page_info["endCursor"], page_info["hasNextPage"]
            except (KeyError, TypeError, ValueError):
                raise ValueError("GitHub returned malformed mailbox comments") from None
            if (not isinstance(rows, list) or len(rows) > _COMMENT_PAGE_SIZE
                    or any(not isinstance(row, dict) for row in rows)
                    or type(more) is not bool
                    or (rows and (not isinstance(next_cursor, str) or not next_cursor or next_cursor == cursor))
                    or (not rows and more)):
                raise ValueError("GitHub returned malformed mailbox comments")
            for row in rows:
                # GraphQL BigInt preserves comment IDs that exceed signed Int32.
                if isinstance(row.get("id"), str) and re.fullmatch(r"[0-9]+", row["id"]):
                    row["id"] = int(row["id"])
            rows.sort(key=lambda row: row.get("id") if type(row.get("id")) is int else -1)
            yield rows, next_cursor if rows else cursor, more
            if not more:
                return
            cursor = next_cursor

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
        lines = ["M14/M15 is blocked.", ""]
        lines += [f"- **{key.replace('_', ' ')}:** {value}" for key, value in material.items() if value]
        if not any(material.values()):
            lines.append("- The campaign is blocked; the exact missing input still needs diagnosis.")
        return material, "\n".join(lines)

    @staticmethod
    def _utc(epoch=None):
        return datetime.fromtimestamp(time.time() if epoch is None else epoch, timezone.utc).isoformat().replace("+00:00", "Z")

    def _event(self, state, kind, key, body, **fields):
        event_id = _sha([self.binding, kind, key])
        if event_id not in state["notices"]:
            state["notices"][event_id] = {"event_id": event_id, "kind": kind, "body": body,
                "requested": False, "created_order": len(state["notices"]), "created_at": self._utc(),
                "publish_to_file": bool(self.config.get("file_reply_path")), **fields}
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
        lines = [f"📥 RECEIVED: [message #{comment_id}]({url})."]
        if request_id:
            raw = intent["instruction"].encode("utf-8")
            message.update(instruction_utf8_bytes=len(raw), instruction_sha256=hashlib.sha256(raw).hexdigest())
            lines += ["⏳ WAITING for controller acceptance."]
        else:
            message["not_queued_reason"] = reason or "No supported first-line command was supplied."
            lines += ["Not queued: " + message["not_queued_reason"]]
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
            if (message.get("source_kind") == "file"
                    and state.get("file_inbox", {}).get("request_id") == ident):
                state["file_inbox"].update(status="ACCEPTED", controller_accepted_at=receipt["delivered_at"])
            label = message.get("source_label") or f"message #{message['comment_id']}"
            url = message.get("source_url") or message["comment_url"]
            body = (f"✅ RECEIVED BY CONTROLLER: [{label}]({url}).\n"
                    "⏳ WAITING for the work result.")
            message["accepted_event_id"] = self._event(state, "accepted", ident, body,
                comment_id=message.get("comment_id"), source_key=message.get("source_key"),
                requires_event_id=message["received_event_id"])

    def _received_file(self, state, intent, request_id):
        revision = intent["file_revision"]
        source_key = "file:" + revision["commit_sha"]
        if source_key in state["messages"]:
            return state["messages"][source_key]
        label = self.config["file_inbox_path"] + " revision " + revision["commit_sha"][:10]
        raw = intent["instruction"].encode("utf-8")
        message = {"source_kind": "file", "source_key": source_key,
                   "source_label": label, "source_url": revision["source_url"],
                   "source_commit_sha": revision["commit_sha"], "source_blob_sha": revision["blob_sha"],
                   "received_at": intent["received_at"], "request_id": request_id,
                   "command_recognized": True, "delivery_status": "WAITING",
                   "instruction_utf8_bytes": len(raw), "instruction_sha256": hashlib.sha256(raw).hexdigest()}
        body = f"📥 RECEIVED: [{label}]({revision['source_url']}).\n⏳ WAITING for controller acceptance."
        message["received_event_id"] = self._event(state, "received", source_key, body, source_key=source_key)
        state["messages"][source_key] = message
        return message

    def _poll_file(self, state, now):
        if not self.file_enabled:
            return [], False
        binding = _sha([self.remote, self.config.get("file_inbox_branch"), self.config["file_inbox_path"], self.user_id])
        current = state.setdefault("file_inbox", {"binding": binding})
        if current.get("binding") != binding:
            raise ValueError("File mailbox binding changed; reconcile retained receipts first")
        current["last_poll_at"] = self._utc(now)
        try:
            revision = read_revision(self.config, api=_gh_api)
        except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
            current.update(status="ERROR", last_error=_safe(str(error)))
            self._event(state, "received", ["file-error", binding, current["last_error"]],
                        self.config["file_inbox_path"] + " was not queued: " + current["last_error"])
            _save(self.path, state)
            return [], False  # A file read failure must not disable PR comments.
        current.update(last_error=None, last_successful_poll_at=self._utc(now))
        if revision["status"] == "EMPTY":
            current.update(status="EMPTY", last_seen_commit=revision.get("commit_sha"),
                           source_url=revision.get("source_url"))
            _save(self.path, state)
            return [], False
        if revision["commit_sha"] == current.get("last_seen_commit"):
            if current.get("status") == "ERROR":
                retained = state["messages"].get("file:" + revision["commit_sha"], {})
                delivery = retained.get("delivery_status")
                current["status"] = {"ACCEPTED": "ACCEPTED", "WAITING": "QUEUED"}.get(delivery, "UNCHANGED")
            return [], False
        instruction = (f"Verified GitHub file instruction from {self.login} (user id {self.user_id}).\n"
                       f"Source: {revision['source_url']}\n"
                       f"Reply file: {self.config.get('file_reply_path', 'status.txt')} on "
                       f"{self.config['file_inbox_branch']}. Publish the work result or exact blocker there "
                       f"through the normal GitHub publisher.\n\n{revision['text']}")
        metadata = {key: value for key, value in revision.items() if key != "text"}
        state["enqueue_intent"] = {"source_kind": "file", "command": "/mckernel-instruct",
            "source_id": "github-file:" + _sha([binding, revision["commit_sha"]]),
            "instruction": instruction, "text_sha256": _sha(instruction),
            "file_revision": metadata, "received_at": self._utc(now)}
        _save(self.path, state)
        request_id = self._finish_enqueue(state)
        return [request_id], True

    def _publish_reply(self, state, now):
        candidates = [notice for notice in state["notices"].values()
                      if notice.get("publish_to_file") and not notice.get("superseded")]
        if not candidates:
            return
        notice = max(candidates, key=lambda n: n.get("created_order", 0))
        receipt = state.get("file_reply", {})
        if receipt.get("event_id") == notice["event_id"] and receipt.get("status") in {"POSTED", "OBSERVED", "PRESERVED"}:
            return
        if receipt.get("status") in {"ERROR", "PENDING"} and now < receipt.get("retry_after", 0):
            return
        # Save intent first. If a PUT outcome is lost, the next attempt reads
        # the remote blob before considering any new write.
        options = {}
        if notice.get("kind") == "accepted":
            # A controller may publish its result before the monitor sees the
            # acceptance receipt. Do not replace that newer result with WAITING.
            expected = (receipt.get("expected_blob_sha")
                        if receipt.get("event_id") == notice["event_id"]
                        else receipt.get("blob_sha") if receipt.get("status") in {"POSTED", "OBSERVED"} else None)
            options["expected_blob_sha"] = expected
        state["file_reply"] = {"event_id": notice["event_id"], "status": "PENDING",
                               "retry_after": now + self.poll_seconds, **options}
        _save(self.path, state)
        try:
            result = write_reply(self.config, notice["body"], api=_gh_api, **options)
        except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
            state["file_reply"].update(status="ERROR", last_error=_safe(str(error)))
        else:
            state["file_reply"].update(result, checked_at=self._utc(now))
            if result["status"] in {"POSTED", "OBSERVED"}:
                state["file_reply"]["published_at"] = self._utc(now)
        _save(self.path, state)

    @staticmethod
    def _notice_parts(notice):
        if "parts" in notice:
            return notice["parts"]
        chunks = split_message(notice["body"])
        if len(chunks) == 1:
            return [notice]  # Keep existing event IDs/receipts compatible.
        notice["parts"] = [{"event_id": _sha([notice["event_id"], "part", index]),
                            "body": body, "requested": False}
                           for index, body in enumerate(chunks, 1)]
        return notice["parts"]

    def _observe_notice(self, state, comment, now):
        body, ident = comment["body"], comment["id"]
        for notice in state["notices"].values():
            parts = self._notice_parts(notice)
            for part in parts:
                if MARKER.format(event_id=part["event_id"]) in body:
                    part.update(observed_comment_id=ident, observed_sent_at=comment.get("created_at"),
                                observed_at=self._utc(now))
            if "parts" in notice and all(part.get("observed_comment_id") for part in parts):
                notice.update(observed_comment_id=parts[-1]["observed_comment_id"],
                              observed_comment_ids=[part["observed_comment_id"] for part in parts],
                              observed_sent_at=parts[-1]["observed_sent_at"], observed_at=self._utc(now))

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
            parts = self._notice_parts(notice)
            for part in parts:
                if part.get("observed_comment_id"):
                    continue
                if part.get("last_dispatch_at") is not None and (
                        now < part["last_dispatch_at"] + max(600, self.poll_seconds)
                        or state.get("last_comments_read_at", 0) < part.get("retry_after_poll_at", 0)):
                    continue
                part.update(last_dispatch_at=now, retry_after_poll_at=now + max(600, self.poll_seconds))
                _save(self.path, state)
                try:
                    _gh_api(f"repos/{self.remote}/actions/workflows/{self.workflow}/dispatches", method="POST",
                            payload={"ref": self.workflow_ref, "inputs": {"event_id": part["event_id"], "body": part["body"]}}, timeout=10)
                except (OSError, ValueError, RuntimeError, subprocess.SubprocessError):
                    state["outbox_retry_poll_after"] = now + max(600, self.poll_seconds)
                    _save(self.path, state)
                    raise
                part.update(requested=True, requested_at=self._utc(now))
                notice["requested"] = all(p.get("requested") or p.get("observed_comment_id") for p in parts)
                if notice["requested"]:
                    notice["requested_at"] = self._utc(now)
                _save(self.path, state)
                return part["event_id"]  # One transport part per monitor tick.
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
        if intent.get("source_kind") == "file":
            self._received_file(state, intent, request_id)
            state["file_inbox"].update(status="QUEUED", last_seen_commit=intent["file_revision"]["commit_sha"],
                source_url=intent["file_revision"]["source_url"], request_id=request_id,
                blob_sha=intent["file_revision"]["blob_sha"], received_at=intent["received_at"])
        else:
            self._received(state, intent, request_id)
        if intent.get("multipart_id"):
            group = state["multipart"][intent["multipart_id"]]
            group["request_id"] = request_id
            group["completed_comment_id"] = intent["comment_id"]
            for prior in state["messages"].values():
                if (prior.get("multipart_id") == intent["multipart_id"]
                        and prior.get("delivery_status") == "ASSEMBLING"
                        and prior["comment_id"] != intent["comment_id"]):
                    prior.update(delivery_status="PART_OF_QUEUED", logical_request_id=request_id,
                                 completed_comment_id=intent["comment_id"])
        state["reply_epoch"] += 1
        if intent.get("source_kind") != "file":
            state["last_seen_comment_id"] = max(state["last_seen_comment_id"], intent["comment_id"])
        state.pop("enqueue_intent")
        _save(self.path, state)
        return request_id

    def _multipart_text(self, state, intent, part, text):
        """Keep authenticated parts durable; queue only the complete exact text."""
        groups = state.setdefault("multipart", {})
        group = groups.setdefault(part["message_id"], {"total": part["total"], "parts": {}})
        if group.get("failure_reason"):
            rejected = group.get("rejected_attempts", []) + [{
                "parts": group["parts"], "total": group["total"], "reason": group["failure_reason"]}]
            group = {"total": part["total"], "parts": {}, "rejected_attempts": rejected}
            groups[part["message_id"]] = group
        if group["total"] != part["total"]:
            raise ValueError("Conflicting multipart count; send a corrected new message.")
        key = str(part["index"])
        prior = group["parts"].get(key)
        if prior is not None and prior["text"] != text:
            raise ValueError("Conflicting multipart content; send a corrected new message.")
        if not text:
            raise ValueError("Multipart content is empty.")
        group["parts"].setdefault(key, {"text": text, "comment_id": intent["comment_id"],
            "comment_created_at": intent["comment_created_at"], "received_at": intent["received_at"]})
        if len(group["parts"]) == group["total"] and not group.get("request_id"):
            complete = "".join(group["parts"][str(index)]["text"] for index in range(1, group["total"] + 1))
            if not complete.strip() or hashlib.sha256(complete.encode("utf-8")).hexdigest() != part["message_id"]:
                group["failure_reason"] = "Multipart message digest does not match; resend every part as new comments."
                for receipt in state["messages"].values():
                    if (receipt.get("multipart_id") == part["message_id"]
                            and receipt.get("delivery_status") == "ASSEMBLING"):
                        receipt.update(delivery_status="REJECTED_ASSEMBLY", reason=group["failure_reason"])
                raise ValueError(group["failure_reason"])
            intent["multipart_id"] = part["message_id"]
            return complete
        # Part receipts remain local; send one receipt for the assembled message,
        # rather than an email for every transport fragment.
        state["messages"][str(intent["comment_id"])] = {
            "comment_id": intent["comment_id"], "multipart_id": part["message_id"],
            "part_index": part["index"], "part_count": part["total"],
            "source_created_at": intent["comment_created_at"], "received_at": intent["received_at"],
            "command_recognized": True,
            "delivery_status": "PART_OF_QUEUED" if group.get("request_id") else "ASSEMBLING",
            "logical_request_id": group.get("request_id")}
        return None

    def _consume_comment(self, state, comment, now):
        ident = comment.get("id")
        if type(ident) is not int or ident <= 0:
            return [], False
        user = comment.get("user") if isinstance(comment.get("user"), dict) else {}
        body = comment.get("body")
        if user.get("type") == "Bot" and user.get("login") == "github-actions[bot]" and isinstance(body, str):
            self._observe_notice(state, comment, now)
        if ident <= state["last_seen_comment_id"]:
            return [], False
        owner = (type(user.get("id")) is int and user["id"] == self.user_id
                 and user.get("type") == "User" and isinstance(user.get("login"), str)
                 and user["login"].casefold() == self.login.casefold())
        queued = []
        if owner:
            for notice in state["notices"].values():
                if notice.get("kind", "blocker") == "blocker":
                    notice["superseded"] = True
            first, separator, text = body.partition("\n") if isinstance(body, str) else ("", "", "")
            command = first.strip()
            intent = {"comment_id": ident, "command": command,
                      "comment_created_at": comment.get("created_at"), "received_at": self._utc(now)}
            unedited = (isinstance(comment.get("created_at"), str) and bool(comment["created_at"])
                        and comment["created_at"] == comment.get("updated_at"))
            reason = "No supported first-line command was supplied."
            if not unedited:
                reason = "Edited or unattributed comments are not executed; post a new comment."
            else:
                try:
                    part = parse_instruction_part(command)
                    if part is not None:
                        text = self._multipart_text(state, intent, part, text)
                        command = "/mckernel-instruct"
                        intent["command"] = command
                    if command == "/mckernel-resume" and not text.strip():
                        text = "Explicit manual continuation requested. Reconcile current controls and continue eligible work; genuine holds remain binding."
                    if command in {"/mckernel-instruct", "/mckernel-resume"} and text is not None and text.strip():
                        url = f"https://github.com/{self.remote}/pull/{self.issue}#issuecomment-{ident}"
                        instruction = (f"Verified GitHub mailbox instruction from {self.login} (user id {self.user_id}).\n"
                                       f"Source: {url}\nCommand: {command}\n\n{text}")
                        source_id = f"github:{self.remote}:{self.issue}:" + (
                            "multipart:" + intent["multipart_id"] if intent.get("multipart_id") else str(ident))
                        intent.update(source_id=source_id, instruction=instruction, text_sha256=_sha(instruction))
                        if command == "/mckernel-resume":
                            intent["resume_created_at"] = datetime.strptime(comment["created_at"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc).timestamp()
                        state["enqueue_intent"] = intent
                        _save(self.path, state)
                        queued.append(self._finish_enqueue(state))
                    elif command == "/mckernel-instruct" and text is not None:
                        reason = "The instruction body is empty; post a new comment with the direction below its first-line command."
                except ValueError as error:
                    # A bad source message does not prevent later valid messages.
                    # An already-durable enqueue intent is instead reconciled by
                    # the existing queue path; it must never be silently skipped.
                    if state.get("enqueue_intent"):
                        raise
                    reason = str(error)
                    state["rejected_comment"] = {"comment_id": ident, "reason": reason}
            if str(ident) not in state["messages"]:
                self._received(state, intent, reason=reason)
                state["reply_epoch"] += 1
        state["last_seen_comment_id"] = max(state["last_seen_comment_id"], ident)
        _save(self.path, state)
        return queued, owner

    def poll(self, context):
        """Read phone comments at the configured cadence; drain one receipt per tick."""
        with self._locked():
            state = self._state()
            now = time.time()
            due = now >= state.get("next_poll_at", 0)
            if due:
                state["last_poll_at"] = now
                _save(self.path, state)
            queued, replied = [], False
            try:
                if state.get("enqueue_intent"):
                    queued.append(self._finish_enqueue(state))
                    replied = True
                if due:
                    file_ids, file_reply = self._poll_file(state, now)
                    queued.extend(file_ids)
                    replied = replied or file_reply
                    for comments, cursor, more in self._comment_pages(state):
                        for comment in comments:
                            new_ids, owner_reply = self._consume_comment(state, comment, now)
                            queued.extend(new_ids)
                            replied = replied or owner_reply
                        state["comment_cursor"] = cursor
                        state["comment_scan_pending"] = more
                        if not more:
                            state["last_comments_read_at"] = now
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
                        "requested": False, "superseded": False, "created_order": len(state["notices"]), "created_at": self._utc(now),
                        "publish_to_file": bool(self.config.get("file_reply_path"))}
                self._inspect_deliveries(state)
                _save(self.path, state)
                self._publish_reply(state, now)
                dispatched = self._drain_outbox(state, now)
                if due:
                    state.update(failures=0, last_error=None, last_successful_poll_at=now)
                _save(self.path, state)
                return self._result(state, "POLLED" if due else "BACKOFF", queued_instruction_ids=queued, dispatched_event_id=dispatched)
            except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
                failures = min(int(state.get("failures", 0)) + 1, 5)
                state.update(failures=failures, last_error=_safe(str(error), 500))
                if due and state.get("next_poll_at", 0) <= now:
                    state["next_poll_at"] = now + min(max(900, self.poll_seconds), self.poll_seconds * 2 ** (failures - 1))
                _save(self.path, state)
                return self._result(state, "ERROR", reason=state["last_error"], queued_instruction_ids=queued)

    def ack_resume(self, request_id):
        """Guardian calls after durably recording its handling; no control changes."""
        with self._locked():
            state = self._state()
            state["pending_resumes"] = [item for item in state["pending_resumes"] if item["request_id"] != request_id]
            _save(self.path, state)

