#!/usr/bin/env python3
"""Send a UTF-8 instruction file to the configured McKernel GitHub mailbox.

Authentication uses the supported gh CLI. Exact, unedited comments by the
configured immutable user are durable deduplication evidence. A failed POST is
never retried automatically: rerun with the same file to scan and resume.
"""
import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys

from os_goal_mailbox_protocol import (PART_COMMAND, format_instruction_comments,
                                     parse_instruction_part)


DEFAULT_CONFIG = Path(__file__).resolve().with_name("os_goal_mailbox.json")


class SendError(RuntimeError):
    def __init__(self, message_id, reason, *, uncertain=False):
        self.message_id = message_id
        self.uncertain = uncertain
        super().__init__(reason)


def _gh_api(endpoint, *, method="GET", payload=None, timeout=10):
    """Use gh's own credentials, stdin JSON, no shell, and no credential output."""
    gh = shutil.which("gh")
    if gh is None:
        raise RuntimeError("Sending requires authenticated gh CLI")
    command = [gh, "api", "--method", method, endpoint]
    if payload is not None:
        command += ["--input", "-"]
    try:
        completed = subprocess.run(command,
            input=json.dumps(payload, ensure_ascii=True) if payload is not None else None,
            text=True, capture_output=True, timeout=timeout, check=False)
    except subprocess.TimeoutExpired:
        raise RuntimeError("GitHub API request timed out") from None
    if completed.returncode:
        raise RuntimeError("GitHub API " + method + " failed; check gh authentication/network")
    try:
        return json.loads(completed.stdout) if completed.stdout.strip() else None
    except (ValueError, TypeError):
        raise ValueError("GitHub API returned malformed JSON") from None


def _config(config):
    if not isinstance(config, dict):
        raise ValueError("Mailbox configuration must contain an object")
    remote, number = config.get("repo"), config.get("issue_number")
    user_id = config.get("authorized_user_id")
    login = config.get("authorized_user_login") or config.get("authorized_login")
    if (not isinstance(remote, str)
            or not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", remote)
            or type(number) is not int or number <= 0
            or type(user_id) is not int or user_id <= 0
            or not isinstance(login, str) or not re.fullmatch(r"[A-Za-z0-9-]+", login)):
        raise ValueError("Mailbox configuration requires one repository, PR, and numeric user identity")
    return remote, number, user_id, login


def _owner(comment, user_id, login):
    user = comment.get("user")
    return (isinstance(user, dict) and type(user.get("id")) is int
            and user["id"] == user_id and user.get("type") == "User"
            and isinstance(user.get("login"), str)
            and user["login"].casefold() == login.casefold())


def _unedited(comment):
    created = comment.get("created_at")
    if not isinstance(created, str) or created != comment.get("updated_at"):
        return False
    try:
        datetime.strptime(created, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError:
        return False
    return True


def _verified(comment, body, user_id, login):
    return (isinstance(comment, dict) and type(comment.get("id")) is int
            and comment["id"] > 0 and comment.get("body") == body
            and _owner(comment, user_id, login) and _unedited(comment))


def _validate_target(api, remote, number, user_id, login):
    user = api("user")
    if not isinstance(user, dict) or not _owner({"user": user}, user_id, login):
        raise ValueError("Authenticated GitHub user does not match the configured identity")
    pull = api(f"repos/{remote}/pulls/{number}")
    if not isinstance(pull, dict):
        raise ValueError("Configured mailbox PR could not be verified")
    author = pull.get("user") or {}
    base = pull.get("base") or {}
    repository = base.get("repo") if isinstance(base, dict) else None
    if (type(pull.get("number")) is not int or pull["number"] != number
            or not isinstance(author, dict) or type(author.get("id")) is not int
            or author["id"] != user_id or not isinstance(repository, dict)
            or not isinstance(repository.get("full_name"), str)
            or repository["full_name"].casefold() != remote.casefold()
            or pull.get("state") != "open" or pull.get("draft") is not True
            or pull.get("merged") is not False):
        raise ValueError("Configured mailbox must be the authorized user's open draft PR in the configured repository")


def _comments(api, remote, number):
    page = 1
    while True:
        rows = api(f"repos/{remote}/issues/{number}/comments?per_page=100&page={page}")
        if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
            raise ValueError("GitHub returned malformed mailbox comments")
        yield from rows
        if len(rows) < 100:
            return
        page += 1


def send_message(text, config, *, api=None):
    """Post missing exact parts sequentially, without retrying uncertain writes.

    ``api`` is an injectable gh-compatible helper for offline verification. The
    GitHub comment history supplies durable receipts; no sender state owner or
    second mailbox is introduced.
    """
    bodies = format_instruction_comments(text)
    message_id = hashlib.sha256(text.encode("utf-8")).hexdigest()
    remote, number, user_id, login = _config(config)
    api = _gh_api if api is None else api
    existing = {}
    multipart = parse_instruction_part(bodies[0].partition("\n")[0]) is not None
    try:
        _validate_target(api, remote, number, user_id, login)
        for comment in _comments(api, remote, number):
            if not _owner(comment, user_id, login) or not _unedited(comment):
                continue
            body = comment.get("body")
            if not isinstance(body, str):
                continue
            if not multipart:
                if _verified(comment, bodies[0], user_id, login):
                    existing.setdefault(1, comment["id"])
                continue
            command = body.partition("\n")[0]
            try:
                part = parse_instruction_part(command)
            except ValueError:
                if command.split()[:2] == [PART_COMMAND, message_id]:
                    raise SendError(message_id, "Malformed existing owner part conflicts with this message") from None
                continue
            if part is None or part["message_id"] != message_id:
                continue
            index = part["index"]
            if (part["total"] != len(bodies) or index > len(bodies)
                    or not _verified(comment, bodies[index - 1], user_id, login)):
                raise SendError(message_id, "Conflicting unedited owner part exists for this message")
            existing.setdefault(index, comment["id"])
    except SendError:
        raise
    except ValueError as error:
        raise SendError(message_id, str(error)) from None
    except Exception:
        raise SendError(message_id, "GitHub validation/history request failed; check gh authentication/network") from None

    posted = {}
    for index, body in enumerate(bodies, 1):
        if index in existing:
            continue
        try:
            comment = api(f"repos/{remote}/issues/{number}/comments", method="POST", payload={"body": body})
        except Exception:
            raise SendError(message_id, "GitHub POST outcome is unconfirmed; rerun the same file to scan before resuming",
                            uncertain=True) from None
        if not _verified(comment, body, user_id, login):
            raise SendError(message_id, "GitHub POST receipt is unconfirmed; rerun the same file to scan before resuming",
                            uncertain=True)
        posted[index] = comment["id"]
    return {"status": "sent", "message_id": message_id, "parts": len(bodies),
            "existing_parts": len(existing), "posted_parts": len(posted),
            "comment_ids": [existing.get(index, posted.get(index)) for index in range(1, len(bodies) + 1)]}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--message-file", type=Path, required=True, help="UTF-8 instruction file; all whitespace is retained")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG, help="Mailbox configuration (default: scripts/os_goal_mailbox.json)")
    args = parser.parse_args(argv)
    message_id = None
    try:
        text = args.message_file.read_bytes().decode("utf-8")
        message_id = hashlib.sha256(text.encode("utf-8")).hexdigest()
        config = json.loads(args.config.read_bytes().decode("utf-8"))
        result = send_message(text, config)
    except SendError as error:
        print(json.dumps({"status": "failed", "message_id": error.message_id,
                          "uncertain_post": error.uncertain, "reason": str(error)}), file=sys.stderr)
        return 1
    except (OSError, ValueError, TypeError) as error:
        print(json.dumps({"status": "failed", "message_id": message_id,
                          "uncertain_post": False, "reason": str(error)}), file=sys.stderr)
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
