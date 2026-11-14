"""Publish the allowlisted status snapshot to one fixed GitHub telemetry file.

No engine authority, new branch creation, source-code publication, credential
logging, or shell execution. The renderer owns public-data selection/redaction.
"""
from contextlib import contextmanager
import base64
import binascii
from datetime import datetime, timezone
import fcntl
import hashlib
import math
import os
from pathlib import Path
import re
import stat
import subprocess
import time
from urllib.parse import quote

from os_goal_mailbox import _gh_api, _read, _safe, _save


REPOSITORY = "phoenix-hacking/mckernel"
BRANCH = "codex/mckernel-control-mailbox"
PUBLIC_PATH = "status.txt"
MAX_BYTES = 200 * 1024
STATE_FILE = "status-publish.json"
COMMIT_MESSAGE = "Update generated McKernel status snapshot [skip ci]"
_CONTENTS = f"repos/{REPOSITORY}/contents/{PUBLIC_PATH}"
_GET = _CONTENTS + "?ref=" + quote(BRANCH, safe="")
_HEX40 = re.compile(r"[0-9a-f]{40}\Z")


def _digest(body):
    return hashlib.sha256(body).hexdigest()


def _blob_sha(body):
    return hashlib.sha1(b"blob " + str(len(body)).encode() + b"\0" + body).hexdigest()


def _utc(now):
    return datetime.fromtimestamp(now, timezone.utc).isoformat().replace("+00:00", "Z")


def _snapshot(value):
    if isinstance(value, Path):
        fd = os.open(value, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        try:
            info = os.fstat(fd)
            if not stat.S_ISREG(info.st_mode) or info.st_size > MAX_BYTES:
                raise ValueError("Public status must be a regular UTF-8 file of at most 200 KiB")
            body = os.read(fd, MAX_BYTES + 1)
            if len(body) != info.st_size:
                raise ValueError("Public status changed during read")
        finally:
            os.close(fd)
        body.decode("utf-8")
    elif isinstance(value, str):
        body = value.encode("utf-8")
    else:
        raise ValueError("Public status must be text or a local Path")
    if not body or len(body) > MAX_BYTES:
        raise ValueError("Public status must contain 1 to 200 KiB of UTF-8 text")
    return body


def _remote_file(value):
    if (not isinstance(value, dict) or value.get("type") != "file"
            or value.get("path") != PUBLIC_PATH or value.get("encoding") != "base64"
            or not isinstance(value.get("sha"), str) or not _HEX40.fullmatch(value["sha"])
            or not isinstance(value.get("content"), str)):
        raise ValueError("GitHub status response is not the existing fixed file")
    try:
        body = base64.b64decode("".join(value["content"].split()), validate=True)
    except (ValueError, binascii.Error) as error:
        raise ValueError("GitHub status content is not valid base64") from error
    if len(body) > MAX_BYTES or value.get("size") != len(body):
        raise ValueError("GitHub status content size differs or exceeds 200 KiB")
    body.decode("utf-8")
    if _blob_sha(body) != value["sha"]:
        raise ValueError("GitHub status blob SHA does not match its bytes")
    return body, value["sha"]


class StatusPublisher:
    def __init__(self, directory, *, interval_seconds=600):
        if (type(interval_seconds) not in (int, float) or not math.isfinite(interval_seconds)
                or interval_seconds < 600):
            raise ValueError("Status publication interval must be finite and at least 600 seconds")
        self.directory = Path(directory)
        self.interval = interval_seconds
        self.path = self.directory / STATE_FILE

    @contextmanager
    def _locked(self):
        self.directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        fd = os.open(self.directory / "status-publish.lock", os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            yield
        finally:
            os.close(fd)

    def _state(self):
        try:
            state = _read(self.path)
        except FileNotFoundError:
            return {"schema_version": 1, "repository": REPOSITORY, "branch": BRANCH,
                    "path": PUBLIC_PATH, "next_publish_at": 0, "failures": 0, "intent": None}
        if (type(state.get("schema_version")) is not int or state["schema_version"] != 1
                or (state.get("repository"), state.get("branch"), state.get("path"))
                != (REPOSITORY, BRANCH, PUBLIC_PATH)):
            raise ValueError("Status publication state has a different fixed destination")
        intent = state.get("intent")
        if intent is not None:
            if (not isinstance(intent, dict) or not isinstance(intent.get("body"), str)
                    or not isinstance(intent.get("base_sha"), str) or not _HEX40.fullmatch(intent["base_sha"])):
                raise ValueError("Status publication intent requires reconciliation")
            body = _snapshot(intent["body"])
            if _digest(body) != intent.get("expected_sha256"):
                raise ValueError("Status publication intent bytes/hash differ; retain without retry")
        return state

    def _result(self, state, status, desired_hash=None, **fields):
        return {"status": status, "repository": REPOSITORY, "branch": BRANCH, "path": PUBLIC_PATH,
                "url": f"https://github.com/{REPOSITORY}/blob/{BRANCH}/{PUBLIC_PATH}",
                "desired_sha256": desired_hash, "published_sha256": state.get("published_sha256"),
                "desired_current": desired_hash is not None and desired_hash == state.get("published_sha256"),
                "published_verified_at": state.get("published_verified_at"),
                "next_publish_at": state.get("next_publish_at", 0),
                "pending_expected_sha256": (state.get("intent") or {}).get("expected_sha256"),
                "last_error": state.get("last_error"), **fields}

    def _confirmed(self, state, body, blob_sha, now, commit=None):
        state.update(intent=None, published_sha256=_digest(body), published_blob_sha=blob_sha,
                     published_verified_at=_utc(now), failures=0, last_error=None)
        if commit is not None:
            state["published_commit_sha"] = commit
        else:
            state.pop("published_commit_sha", None)

    def publish(self, text_or_path=None):
        """At most one GET and one conditional PUT per due publication tick.

        An uncertain old intent is reconciled before a newer renderer timestamp.
        If GitHub still exposes the exact original base blob, repeating the same
        body with that current blob's CAS is safe. Any different intervening blob
        preserves UNKNOWN instead of overwriting another publication.
        """
        with self._locked():
            state = self._state()
            now = time.time()
            if now < state.get("next_publish_at", 0):
                return self._result(state, "BACKOFF")
            desired_hash = None
            try:
                desired = _snapshot(self.directory / PUBLIC_PATH if text_or_path is None else text_or_path)
                desired_hash = _digest(desired)
                state.update(last_attempt_at=_utc(now), next_publish_at=now + self.interval)
                _save(self.path, state)
                remote, remote_sha = _remote_file(_gh_api(_GET, timeout=10))
                state.update(last_checked_at=_utc(now), observed_remote_sha256=_digest(remote))
                prior = state.get("intent")
                target = desired
                if prior is not None:
                    previous = prior["body"].encode("utf-8")
                    if remote == previous:
                        self._confirmed(state, remote, remote_sha, now)
                        _save(self.path, state)
                    elif remote_sha == prior["base_sha"]:
                        target = previous  # Reconcile/retry exact old intent first.
                    else:
                        state.update(status="UNKNOWN", last_error="Remote status changed during an unresolved publication; retain intent for reconciliation")
                        _save(self.path, state)
                        return self._result(state, "UNKNOWN", desired_hash)
                if remote == target:
                    self._confirmed(state, remote, remote_sha, now)
                    state["status"] = "UNCHANGED"
                    _save(self.path, state)
                    return self._result(state, "UNCHANGED", desired_hash)
                intent = state.get("intent")
                if intent is None:
                    intent = {"body": target.decode("utf-8"), "expected_sha256": _digest(target),
                              "base_sha": remote_sha, "created_at": _utc(now), "attempts": 0}
                    state["intent"] = intent
                intent.update(status="sending", attempts=intent["attempts"] + 1, submitted_at=_utc(now))
                _save(self.path, state)  # Publish exact bytes/hash and CAS before mutation.
                response = _gh_api(_CONTENTS, method="PUT", payload={"message": COMMIT_MESSAGE,
                    "content": base64.b64encode(target).decode(), "branch": BRANCH, "sha": remote_sha}, timeout=10)
                content = response.get("content") if isinstance(response, dict) else None
                commit = response.get("commit") if isinstance(response, dict) else None
                if (not isinstance(content, dict) or content.get("path") != PUBLIC_PATH
                        or content.get("sha") != _blob_sha(target) or not isinstance(commit, dict)
                        or not isinstance(commit.get("sha"), str) or not _HEX40.fullmatch(commit["sha"])):
                    raise ValueError("GitHub PUT acknowledgement does not prove the intended status blob")
                self._confirmed(state, target, content["sha"], now, commit["sha"])
                state["status"] = "PUBLISHED"
                _save(self.path, state)
                return self._result(state, "PUBLISHED", desired_hash)
            except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
                failures = min(int(state.get("failures", 0)) + 1, 4)
                state.update(failures=failures, next_publish_at=now + min(3600, self.interval * 2 ** (failures - 1)),
                             last_error=_safe(str(error), 500),
                             status="UNKNOWN" if state.get("intent") else "ERROR")
                if state.get("intent"):
                    state["intent"]["status"] = "delivery_uncertain"
                _save(self.path, state)
                return self._result(state, state["status"], desired_hash)
