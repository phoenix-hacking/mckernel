#!/usr/bin/env python3
"""Start/resume the McKernel milestone goal through the local Codex app server.

No model calls for --dry-run, --status, --check or --check-sudo. A normal invocation starts
paid/account-metered work. Runtime state stays in the repository's Git directory.
"""

import argparse
import codecs
from decimal import Decimal, InvalidOperation
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import selectors
import shlex
import shutil
import signal
import stat
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from uuid import uuid4

from os_goal_output import LiveOutput
from os_goal_resources import (check_resources, resolve_resources,
                               resource_environment, resource_instructions)
from os_goal_windows import window_capability
from os_goal_instructions import reconcile_instructions
from os_goal_credits import (CreditBudget, available_balance, amount, billing_policy,
                             credit_budget_argument)
from os_goal_transport import (READ_ONLY_RPC_METHODS, classify_rpc_failure, classify_service_failure,
                               classify_usage_failure)
from os_goal_stop_log import write_stop_record
from os_goal_repair import (repair_instruction, blocked_repair_key,
                            blocked_repair_instruction)
from os_goal_custody import (retention_required, guard_owner_close,
                             make_retention_record, retention_error)


REPO = Path(__file__).resolve().parents[1]
SUDO_HELPER = REPO / "scripts/os_goal_sudo_askpass.py"
SUDO_CREDENTIAL = Path.home() / ".local/state/mckernel-os-goal/sudo-password"
PLAN_REL = "docs/verification/os-milestones-20260914"
CAPTURE_PROGRESS_CAPABILITY = 1
SAME_OWNER_CONTROL_CAPABILITY = 1
# Older launchers validate this existing envelope before steering. The reserved,
# non-registration shape makes them refuse a control command before any turn RPC.
SAME_OWNER_CONTROL_LEGACY_BARRIER = {"control_only": "resume_same_owner", "capability_version": 1}
DEFAULT_DISPATCHER_MODEL = "gpt-6.1-sol"
DEFAULT_DISPATCHER_EFFORT = "max"
# User preference, 2026-10-30: Sol/max first; capable fallbacks before economy
# models, with max reasoning preferred. This orders routing choices; advertised
# capability is not proof of current capacity, entitlement, or service clearance.
DISPATCHER_MODEL_PREFERENCE = (
    "gpt-6.1-sol", "gpt-6-astra", "gpt-6.1-terra", "gpt-6-sol", "gpt-6-luna",
)
DISPATCHER_EFFORT_PREFERENCE = ("max", "ultra", "xhigh", "high")
DEFAULT_WORKER_MODEL = "gpt-6.1-sol"
MINIMUM_WORKER_EFFORT = "max"
AUDIT_MODEL = "gpt-6.1-sol"
REVIEW_MODEL = "gpt-6.1-sol"
OBJECTIVE = (
    "Complete the McKernel OS functionality, stability, native production and "
    "Rust/assembly acceptance objective in " + PLAN_REL + "/README.md. "
    "First read " + PLAN_REL + "/GOAL.md, START.md and CURRENT.md. "
    "Automatically dispatch bounded cheap subagents using that plan; continue "
    "through all dependency-ready milestones, preserving exact evidence and "
    "verified Git checkpoints. Complete only when all 130 production gates, "
    "seven language gates and required application/configuration coverage meet "
    "their original acceptance contracts, including external qualification. "
    "A work-window checkpoint is not whole-OS completion."
)
TERMINAL_CODES = {"complete": 0, "paused": 10, "blocked": 20,
                  "usageLimited": 21, "budgetLimited": 22}
LIMIT_ERRORS = {"usageLimitExceeded", "sessionBudgetExceeded"}
# The user selected continuous work through the full included allowance.
# Prepaid credits require --credit-budget; API-key billing is never enabled.
INCLUDED_USAGE_STOP_PERCENT = 100
CREDIT_NOTIFICATION_MAX_AGE_SECONDS = 15
USER_INPUT_METHOD = "item/tool/requestUserInput"
ENGINEERING_SCOPE = (
    "Functional McKernel OS/apps and Rust/assembly migration only; no security testing. "
    "Scope each task to an original M14/M15 provider/ABI, coherent image/module, "
    "or functional/lifecycle requirement. Do not undertake vulnerability scanning, "
    "exploit development, penetration testing, red teaming or credential collection. "
    "Preserve legitimate kernel behavior tests and their original acceptance criteria. "
    "Include this scope and any rejected-task exclusions in every delegated task. "
    "On a cyberPolicy rejection, stop the affected task and preserve its request, "
    "worker/turn identity and service notice. Use supported account resolution or "
    "Codex /feedback for a suspected false positive. Do not retry, rephrase or "
    "reassign the rejected task, switch accounts/models, or clear service records. "
    "A new conversation or local history cleanup does not clear a service hold. "
)
AUTONOMY_REPLY = (
    "Automatic launcher response applying the user's standing instruction; "
    "no new human answer was provided. Continue the authorized OS milestone "
    "work autonomously without asking questions. Choose reasonable implementation "
    "defaults and record assumptions. If a missing fact, credential or external "
    "resource cannot be inferred, record that task's blocker and continue other "
    "ready work. Do not fabricate facts, select an external-action approval, "
    "weaken acceptance criteria, or repeat this question. This automatic answer "
    "does not authorize security testing, replay of a rejected task or clearance "
    "of a service/account hold."
)


def unattended_input(params):
    """Return the existing delegation instruction, never an invented user choice."""
    answers = {}
    for question in params["questions"]:
        ident = question["id"]
        if not isinstance(ident, str) or not ident or ident in answers:
            raise ValueError("Invalid/duplicate unattended question ID")
        # An instruction must not be supplied as if it were a password/token.
        answers[ident] = {"answers": [] if question.get("isSecret") else [AUTONOMY_REPLY]}
    return {"answers": answers}


def runtime_environment():
    """Pass credential paths to sudo, never the password in argv or environment."""
    return dict(os.environ, GIT_TERMINAL_PROMPT="0", GCM_INTERACTIVE="Never",
                SUDO_ASKPASS=str(SUDO_HELPER), MCKERNEL_OS_SUDO_CREDENTIAL=str(SUDO_CREDENTIAL))


class RecoverableFailure(RuntimeError):
    """A transport/process failure that the watcher may retry."""


def utc():
    return datetime.now(timezone.utc).isoformat()


def m14_m15_closed(repo):
    """Require original binary acceptance, never checklist percentages alone."""
    path = Path(repo) / "docs/verification/m14-m15-closure-progress.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if data.get("original_criteria_unchanged") is not True:
            return False
        requirements = data["requirements"]
        if not isinstance(requirements, list):
            return False
        for milestone, files, integrations in (("M14", 6, 3), ("M15", 8, 4)):
            expected = ({f"{milestone}-F{n:02d}" for n in range(1, files + 1)} |
                        {f"{milestone}-I{n:02d}" for n in range(1, integrations + 1)})
            summary = data["summaries"][milestone]
            gate_ids = summary.get("original_gate_ids", [])
            if (summary.get("milestone_accepted") is not True or
                    not isinstance(gate_ids, list) or len(gate_ids) != len(expected)
                    or set(gate_ids) != expected):
                return False
            rows = [row for row in requirements if row.get("id") in expected]
            if (len(rows) != len(expected) or {row["id"] for row in rows} != expected
                    or any(row.get("accepted") is not True for row in rows)):
                return False
        return True
    except (OSError, ValueError, TypeError, KeyError, AttributeError):
        return False


def _read_instruction_bytes(path, description, *, private=False):
    """Read a stable regular file in chunks, without imposing a payload quota."""
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode):
            raise ValueError(description + " must be a regular file")
        if private and (before.st_uid != os.getuid() or before.st_nlink != 1):
            raise ValueError(description + " must be an owner-controlled single-link file")
        chunks, size = [], 0
        # Read at most the observed file plus one byte: concurrent growth is a
        # changed input, while a complete immutable instruction has no size cap.
        while size <= before.st_size:
            chunk = os.read(fd, min(65536, before.st_size + 1 - size))
            if not chunk:
                break
            chunks.append(chunk)
            size += len(chunk)
        after = os.fstat(fd)
        if (size != before.st_size or
                (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns,
                 before.st_ctime_ns, before.st_uid, before.st_nlink) !=
                (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns,
                 after.st_ctime_ns, after.st_uid, after.st_nlink)):
            raise ValueError(description + " changed during read")
        return b"".join(chunks)
    finally:
        os.close(fd)


def _read_private_json(path):
    raw = _read_instruction_bytes(path, "Instruction JSON", private=True)
    value = json.loads(raw.decode("utf-8"))
    if not isinstance(value, dict):
        raise ValueError("Instruction JSON must contain an object")
    return value


def _validate_instruction(instruction):
    if not isinstance(instruction, str):
        raise ValueError("Instruction must be UTF-8 text")
    try:
        instruction.encode("utf-8")
    except UnicodeEncodeError as error:
        raise ValueError("Instruction must be valid UTF-8 text") from error
    if not instruction.strip():
        raise ValueError("Instruction must be nonempty UTF-8 text")
    return instruction


def read_startup_instruction(path):
    """Load an explicit invocation note before thread/resume can start work."""
    raw = _read_instruction_bytes(path, "Startup instruction")
    try:
        note = raw.decode("utf-8")
    except UnicodeDecodeError as error:
        raise ValueError("Startup instruction must be valid UTF-8 text") from error
    if not note.strip() or "\0" in note:
        raise ValueError("Startup instruction must be nonempty UTF-8 text without NUL")
    return note


def say(message):
    print("[os-goal] " + message, flush=True)


def is_policy_stop(state):
    error = state.get("last_error")
    return (state.get("stop_reason") in {"turn_failed", "server_error"}
            and isinstance(error, dict) and error.get("codexErrorInfo") == "cyberPolicy")


def failure_location(state):
    """Keep failure identity separate from later sibling interruption events."""
    failure = state.get("last_failure")
    if (isinstance(failure, dict) and isinstance(failure.get("log_dir"), str)
            and failure.get("log_dir") == state.get("log_dir")
            and failure.get("error") == state.get("last_error")):
        return failure
    # Older state has no dedicated failure record. A unique failed worker is
    # stronger evidence than last_turn, which shutdown may have overwritten.
    agents = state.get("agents")
    failed = [{"thread_id": ident, "id": agent.get("turn_id")}
              for ident, agent in (agents.items() if isinstance(agents, dict) else ())
              if isinstance(agent, dict) and agent.get("status") == "failed"
              and agent.get("turn_id")]
    if len(failed) == 1:
        return failed[0]
    last = state.get("last_turn")
    if isinstance(last, dict) and last.get("status") in (None, "failed"):
        return last
    return {}


def restart_advice(state):
    if is_policy_stop(state):
        failed = failure_location(state)
        return ("service-side cyberPolicy stop; automatic retry is disabled. "
                "Local history cleanup or a fresh session does not clear this hold. "
                "Resolve the recorded account/security requirement before resuming. "
                "Report a suspected false positive with Codex /feedback; "
                "thread=" + str(failed.get("thread_id") or state.get("thread_id", "unknown"))
                + "; turn=" + str(failed.get("id", "unknown"))
                + ". Saved work is preserved; service-side checks remain active for any explicit manual resume.")
    return "run the same command to resume unfinished work."


def atomic_json(path, value):
    """Same-directory replace and fsync keep the last complete cursor on a crash."""
    with tempfile.NamedTemporaryFile(mode="w", dir=str(path.parent),
                                     prefix=path.name + ".", delete=False) as stream:
        temporary = Path(stream.name)
        json.dump(value, stream, indent=2)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(str(temporary), str(path))
    directory = os.open(str(path.parent), os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)


def validate_capture_progress_directory(value):
    """Validate one explicitly named future directory; never discover paths."""
    if not isinstance(value, (str, Path)) or len(str(value).encode('utf-8')) > 4096:
        raise ValueError('capture progress directory must be a bounded explicit path')
    path = Path(value)
    if (not path.is_absolute() or '..' in path.parts or os.path.lexists(path)
            or not path.parent.is_dir()
            or any(p.is_symlink() for p in (path, *path.parents))):
        raise ValueError('capture progress directory must be fresh, absolute and nonsymlink')
    return path


def queue_instruction(directory, instruction, capture_progress_directory=None, *, source_id=None,
                      resume_same_owner=False):
    """Queue an owner's instruction without touching the running server lease."""
    if not (directory / "state.json").is_file():
        raise RuntimeError("No saved OS campaign exists; start the runner first.")
    _validate_instruction(instruction)
    item = {"submitted_at": utc(), "text": instruction}
    if resume_same_owner:
        if source_id is None or capture_progress_directory is not None:
            raise ValueError("Same-owner resume requires an explicit source ID and no capture registration")
        item["control"] = {"kind": "resume_same_owner", "schema_version": 1}
        item["capture_progress"] = dict(SAME_OWNER_CONTROL_LEGACY_BARRIER)
    if capture_progress_directory is not None:
        path = validate_capture_progress_directory(capture_progress_directory)
        state = json.loads((directory / 'state.json').read_text())
        if (type(state.get('capture_progress_capability')) is not int
                or state['capture_progress_capability'] != CAPTURE_PROGRESS_CAPABILITY):
            raise ValueError('resident launcher does not advertise compatible capture progress capability')
        if (state.get('phase') != 'running' or not isinstance(state.get('thread_id'), str)
                or not state['thread_id'] or type(state.get('worker_pid')) is not int
                or state['worker_pid'] <= 0 or not isinstance(state.get('log_dir'), str)
                or not state['log_dir']):
            raise ValueError('capture registration requires an identified running campaign')
        item['capture_progress'] = dict(directory=str(path), capability_version=CAPTURE_PROGRESS_CAPABILITY,
            expected_thread_id=state['thread_id'], expected_worker_pid=state['worker_pid'],
            expected_log_dir=state['log_dir'])
    inbox = directory / "instructions" / "pending"
    inbox.mkdir(mode=0o700, parents=True, exist_ok=True)
    ident = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ") + "-" + uuid4().hex
    if source_id is not None:
        if not isinstance(source_id, str) or not 0 < len(source_id) <= 512 or capture_progress_directory is not None:
            raise ValueError("Source-bound instructions require a bounded source ID and no capture registration")
        digest = hashlib.sha256(source_id.encode()).hexdigest()
        ident = "source-" + digest
        item.update(source_id=source_id, text_sha256=hashlib.sha256(instruction.encode()).hexdigest())
        item["id"] = ident
        sources = directory / "instructions" / "sources"
        sources.mkdir(mode=0o700, parents=True, exist_ok=True)
        lock = os.open(sources / "queue.lock", os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
        try:
            fcntl.flock(lock, fcntl.LOCK_EX)
            registry = sources / (digest + ".json")
            try:
                prior = _read_private_json(registry)
            except FileNotFoundError:
                prior = None
            if prior:
                prior_item = prior.get("item", {})
                if (prior_item.get("text_sha256") != item["text_sha256"]
                        or prior_item.get("source_id") != source_id
                        or bool(prior_item.get("control")) != resume_same_owner
                        or resume_same_owner and (prior_item.get("control") or {}).get("kind") != "resume_same_owner"):
                    raise ValueError("Source instruction content changed; refusing replay")
                if prior.get("status") == "queued" or any((directory / "instructions" / phase / (ident + ".json")).exists()
                        for phase in ("pending", "sending", "delivered", "refused")):
                    return ident
                item = prior_item  # Recover the original durable publication intent.
            if resume_same_owner and prior is None:
                # Only the first publication binds a source. A repeated source
                # returns its original command, even after the goal changes.
                item["control"] = same_owner_resume_binding(directory)
            atomic_json(registry, {"status": "intent", "item": item})
            atomic_json(inbox / (ident + ".json"), item)
            atomic_json(registry, {"status": "queued", "item": item})
            return ident
        finally:
            os.close(lock)
    item["id"] = ident
    atomic_json(inbox / (ident + ".json"), item)
    return ident


def queue_same_owner_resume(directory, instruction, *, source_id):
    """Queue one explicit control command; never create a server or admit work."""
    return queue_instruction(directory, instruction, source_id=source_id,
                             resume_same_owner=True)


def progress_report(directory, repo):
    """Show canonical practical check states and the live heartbeat; never infer credit."""
    state_path = directory / "state.json"
    state = json.loads(state_path.read_text()) if state_path.is_file() else {}
    goal = state.get("goal") or {}
    active = state.get("active_turns") or {}
    primary = state.get("thread_id")
    children = len(active) - int(primary in active)
    agents = ((state.get("settings") or {}).get("resources") or {}).get("max_agents", "?")
    phase = state.get("phase", "not_started")
    activity = ("recorded active child agents" if phase == "running"
                else "historical child turns (runner inactive)")
    lines = ["Runner: {} | goal: {} | {}: {}/{}".format(
        phase, goal.get("status", "none"), activity, children, agents),
        "Last heartbeat: {}".format(state.get("heartbeat_at", "none")),
        "State last updated: {}".format(state.get("updated_at", "none"))]
    for progress in state.get('capture_progress', []):
        lines.append('Capture progress (nonterminal; no clearance): ' + json.dumps(progress, sort_keys=True))
    control = directory / "instructions"
    pending = list((control / "pending").glob("*.json"))
    uncertain = list((control / "sending").glob("*.json"))
    lines.append("Instructions: {} pending, {} delivery-uncertain".format(len(pending), len(uncertain)))
    last_instruction = state.get("last_instruction") or {}
    if last_instruction:
        lines.append("Last instruction: {} ({})".format(
            last_instruction.get("id", "?"), last_instruction.get("status", "?")))
    lines = ["Campaign log: " + str(repo / "CAMPAIGN.md"), ""] + lines
    return "\n".join(lines)


class Lease:
    def __init__(self, path):
        self.file = path.open("a+")
        try:
            fcntl.flock(self.file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            self.file.close()
            raise RuntimeError("Another OS launcher holds the repository lease.")

    def close(self):
        self.file.close()


def _account_value_sha256(value):
    """Private content binding; never publish account values in diagnostics."""
    return hashlib.sha256(json.dumps(value, sort_keys=True,
                                     separators=(",", ":")).encode("utf-8")).hexdigest()


def accepted_account_observation(state, ledger, owner, now_utc_ns, now_mono_ns,
                                 max_age_seconds=25):
    """Validate one durable current-owner observation; perform no I/O or refresh.

    ``owner`` must be obtained independently by the invoking current-owner
    consumer.  A receipt is evidence of an observation, never execution authority.
    The newest received observation wins, including a newer rejection/pending
    observation; this deliberately never falls back to an older success.
    """
    def require(value, message):
        if not value:
            raise ValueError(message)

    def finite_primary(limits):
        require(isinstance(limits, dict), "account limits missing")
        primary = limits.get("primary")
        require(isinstance(primary, dict), "account primary missing")
        used = primary.get("usedPercent")
        require(isinstance(used, (int, float)) and not isinstance(used, bool)
                and math.isfinite(used) and 0 <= used <= 100,
                "account primary unknown")
        require(primary.get("windowDurationMins") == 10080,
                "account primary window unsupported")

    require(isinstance(state, dict) and isinstance(ledger, dict)
            and isinstance(owner, dict), "account snapshot shape")
    require(isinstance(max_age_seconds, (int, float))
            and not isinstance(max_age_seconds, bool)
            and math.isfinite(max_age_seconds) and 0 < max_age_seconds <= 25,
            "account observation age bound")
    require(type(now_utc_ns) is int and type(now_mono_ns) is int,
            "account observation clock shape")
    candidates = [state.get(name) for name in
                  ("last_account_observation", "last_account_notification",
                   "successful_account_read") if state.get(name) is not None]
    require(bool(candidates), "no durable account observation")
    for item in candidates:
        require(isinstance(item, dict) and item.get("schema_version") == 1,
                "account observation shape")
        require(type(item.get("received_mono_ns")) is int
                and type(item.get("sequence")) is int,
                "account observation ordering missing")
    newest = max(candidates, key=lambda item: (item["received_mono_ns"],
                                              item["sequence"]))
    require(newest.get("status") == "ACCEPTED",
            "newest account observation not accepted")
    require(newest.get("owner") == owner, "account observation owner mismatch")
    required = ("boot_id", "log_dir", "thread_id", "worker_pid", "worker_start",
                "server_pid", "server_start", "credit_run_id", "credit_budget",
                "credit_ledger_path")
    require(all(owner.get(key) is not None for key in required),
            "account observation owner incomplete")
    require(state.get("phase") == "running" and not state.get("stop_reason")
            and not state.get("credit_budget_error"), "account owner not running")
    require(state.get("auth_mode") == "chatgpt", "account authentication unknown")
    for key in ("log_dir", "thread_id", "worker_pid", "server_pid",
                "worker_start", "server_start", "repo", "guardian_run_id"):
        require(state.get(key) == owner.get(key), "account current owner mismatch")
    goal = state.get("goal")
    require(isinstance(goal, dict) and goal.get("status") == "active"
            and isinstance(goal.get("objective"), str) and bool(goal["objective"])
            and _account_value_sha256(goal["objective"])
                == owner.get("goal_objective_sha256")
            and goal.get("threadId", owner["thread_id"]) == owner["thread_id"],
            "account saved goal mismatch or stopped")
    for key in ("worker_pid", "server_pid"):
        require(type(owner.get(key)) is int and owner[key] > 0,
                "account owner pid invalid")
    for key in ("worker_start", "server_start"):
        require(isinstance(owner.get(key), str) and owner[key].isascii()
                and owner[key].isdigit(), "account owner birth invalid")
    transport = state.get("transport_failure") or {}
    require(not (newest.get("source") == "read"
                 and transport.get("method") == "account/rateLimits/read"
                 and transport.get("channel_unusable")),
            "failed transport requires original notification-only fallback")
    require(newest.get("server_pid") == owner["server_pid"],
            "account response server mismatch")
    source = newest.get("source")
    require((source == "read" and newest.get("method") == "account/rateLimits/read"
             and type(newest.get("request_id")) is int)
            or (source == "notification"
                and newest.get("method") == "account/rateLimits/updated"
                and newest.get("request_id") is None),
            "account observation source mismatch")
    require(type(newest.get("received_utc_ns")) is int,
            "account observation UTC missing")
    for now, received in ((now_utc_ns, newest["received_utc_ns"]),
                          (now_mono_ns, newest["received_mono_ns"])):
        require(0 <= now - received < max_age_seconds * 1000000000,
                "account observation stale")
    limits = state.get("last_rate_limits")
    finite_primary(limits)
    require(_account_value_sha256(limits) == newest.get("rate_limits_sha256"),
            "account observation limits mismatch")
    require(state.get("credit_budget") == ledger,
            "account durable credit snapshot mismatch")
    require(_account_value_sha256(ledger) == newest.get("credit_record_sha256"),
            "account observation credit mismatch")
    require(type(ledger.get("schema_version")) is int
            and ledger.get("schema_version") in (1, 2)
            and ledger.get("id") == owner["credit_run_id"]
            and amount(ledger.get("budget"), positive=True)
                == amount(owner["credit_budget"], positive=True),
            "account original credit identity mismatch")
    initial = amount(ledger.get("initial_balance"))
    minimum = amount(ledger.get("minimum_balance"))
    last = amount(ledger.get("last_balance"))
    spent = amount(ledger.get("spent"))
    remaining = amount(ledger.get("remaining"))
    budget = amount(ledger.get("budget"), positive=True)
    require(minimum <= initial and minimum <= last
            and spent >= initial - minimum
            and remaining == max(Decimal(0), budget - spent)
            and (ledger["schema_version"] != 1
                 or (last <= initial and spent == initial - minimum)),
            "account retained credit accounting inconsistent")
    require(last == available_balance(limits),
            "account observation credit balance mismatch")
    require(remaining > 0, "account credit exhausted or unknown")
    require(newest.get("state_limits_and_credit_persisted") is True,
            "account observation persistence unconfirmed")
    return dict(newest)


TECHNICAL_CONTROL_STOPS = frozenset({"watchdog_recovery", "guardian_recovery",
                                     "active_goal_did_not_continue"})
_CONTROL_HOLD_FLAGS = ("service_hold", "policy_hold", "auth_hold", "billing_hold",
                       "budget_hold", "permission_hold", "account_hold",
                       "accounting_unknown", "budget_unknown", "auth_unknown",
                       "credit_budget_unknown", "included_usage_unknown",
                       "user_pause", "user_paused", "pause_requested")


def _same_owner_control_blocker(state, current_receipt=None, *, allow_technical=False):
    """Account/service stops block control; scoped execution holds stay intact."""
    reason = state.get("stop_reason")
    if reason is not None and not (allow_technical and reason in TECHNICAL_CONTROL_STOPS):
        return "stop_reason"
    if state.get("credit_budget_error") is not None:
        return "credit_budget_error"
    for key in _CONTROL_HOLD_FLAGS:
        if key in state and state[key] is not False:
            return key
    for key in ("transport_uncertain", "pending_request"):
        if key in state and state[key] is not None and state[key] is not False:
            return key
    if is_policy_stop(state):
        return "policy_stop"
    from os_goal_guard_protocol import recovery_blocker
    projection = {key: state.get(key) for key in
                  ("log_dir", "last_error", "last_error_provenance", "last_failure")}
    failure = recovery_blocker(projection, explicit_user=True)
    if failure:
        return failure
    for key in ("resume_instruction", "last_instruction"):
        receipt = state.get(key)
        own = (isinstance(current_receipt, dict) and isinstance(receipt, dict)
               and current_receipt.get("control_kind") == "resume_same_owner"
               and isinstance(current_receipt.get("id"), str)
               and current_receipt["id"].startswith("source-")
               and receipt == current_receipt)
        if (receipt and not own
                and (not isinstance(receipt, dict) or receipt.get("status") in
                     {"sending", "delivery_uncertain", "control_archive_failed_before_activation"})):
            return "instruction_delivery_unreconciled"
    return None


def _paused_retained_control(state):
    """Authenticate a technically paused continuous owner, without releasing it."""
    row = state.get("owner_retention")
    return (state.get("continuous") is True and state.get("phase") == "owner_retained"
            and isinstance(row, dict) and row.get("custody") == "UNKNOWN"
            and row.get("release_authorized") is False
            and row.get("automatic_resume") is False
            and all(row.get(key) == state.get(key) and state.get(key) is not None
                    for key in ("worker_pid", "worker_start", "server_pid", "server_start",
                                "thread_id", "log_dir")))


def control_context_eligible(state, *, current_receipt=None):
    """Permit factual reads/typed control, never execution or hold release.

    Runtime callers include their actual stop/checkpoint flags in ``state``.
    Only the named technical retained checkpoint can be acknowledged by a new,
    exactly bound user command. User, time-window and account stops stay closed.
    """
    if not isinstance(state, dict):
        return False
    reason = state.get("stop_reason")
    technical = (isinstance(reason, str) and reason in TECHNICAL_CONTROL_STOPS)
    if technical:
        if (not _paused_retained_control(state)
                or (state.get("goal") or {}).get("status") not in {"paused", "blocked"}
                or type(state.get("stop_now")) is not bool
                or type(state.get("checkpoint_requested")) is not bool):
            return False
    elif state.get("stop_now") or state.get("checkpoint_requested"):
        return False
    return (type(state.get("same_owner_control_capability")) is int
            and state["same_owner_control_capability"] == SAME_OWNER_CONTROL_CAPABILITY
            and not _same_owner_control_blocker(state, current_receipt,
                                                allow_technical=technical))


def _account_control_owner(state, directory, repo):
    """Independently join the saved owner to its existing live processes."""
    from os_goal_guard_protocol import process_start
    if state.get("repo") != str(repo):
        raise ValueError("account control repository mismatch")
    for role in ("worker", "server"):
        pid, birth = state.get(role + "_pid"), state.get(role + "_start")
        if (type(pid) is not int or pid <= 0 or not isinstance(birth, str)
                or not birth.isascii() or not birth.isdigit() or process_start(pid) != birth):
            raise ValueError("account control original process mismatch")
    ledger = state.get("credit_budget")
    if not isinstance(ledger, dict):
        raise ValueError("account control retained ledger missing")
    identifier = ledger.get("id")
    if (not isinstance(identifier, str) or len(identifier) != 32
            or any(c not in "0123456789abcdef" for c in identifier)):
        raise ValueError("account control original credit identity missing")
    return {"boot_id": Path("/proc/sys/kernel/random/boot_id").read_text().strip(),
            "repo": str(repo), "guardian_run_id": state.get("guardian_run_id"),
            "log_dir": state.get("log_dir"), "thread_id": state.get("thread_id"),
            "goal_objective_sha256": _account_value_sha256((state.get("goal") or {}).get("objective")),
            "worker_pid": state["worker_pid"], "worker_start": state["worker_start"],
            "server_pid": state["server_pid"], "server_start": state["server_start"],
            "credit_run_id": identifier,
            "credit_budget": str(amount(ledger.get("budget"), positive=True)),
            "credit_ledger_path": str(Path(directory) / "credit-runs" / (identifier + ".json"))}


def observed_account_control(state, ledger, owner, now_utc_ns, now_mono_ns,
                             max_age_seconds=25, *, current_receipt=None):
    """Validate factual account control evidence independently of goal activity.

    This separate opt-in receipt has NO execution or hold-release authority.
    The original ACCEPTED helper and its active-goal contract remain unchanged.
    """
    def require(value, message):
        if not value:
            raise ValueError(message)

    require(isinstance(state, dict) and isinstance(ledger, dict) and isinstance(owner, dict),
            "account control snapshot shape")
    require(type(state.get("same_owner_control_capability")) is int
            and state["same_owner_control_capability"] == SAME_OWNER_CONTROL_CAPABILITY,
            "account control capability unavailable")
    require(isinstance(max_age_seconds, (int, float)) and not isinstance(max_age_seconds, bool)
            and math.isfinite(max_age_seconds) and 0 < max_age_seconds <= 25,
            "account control observation age bound")
    require(type(now_utc_ns) is int and type(now_mono_ns) is int,
            "account control clock shape")
    observed = state.get("last_account_control_observation")
    require(isinstance(observed, dict) and observed.get("schema_version") == 1
            and observed.get("status") == "OBSERVED"
            and observed.get("context") == "same_owner_control"
            and observed.get("execution_authorized") is False,
            "account control observation unavailable")
    candidates = [state.get(name) for name in ("last_account_observation",
                  "last_account_notification", "successful_account_read")
                  if state.get(name) is not None]
    require(bool(candidates), "account control receive evidence missing")
    for received in candidates + [observed]:
        require(isinstance(received, dict) and received.get("schema_version") == 1
                and type(received.get("received_mono_ns")) is int
                and type(received.get("sequence")) is int,
                "account control receive ordering missing")
    newest = max(candidates, key=lambda item: (item["received_mono_ns"], item["sequence"]))
    technical = (isinstance(state.get("stop_reason"), str)
                 and state["stop_reason"] in TECHNICAL_CONTROL_STOPS
                 and control_context_eligible(state, current_receipt=current_receipt))
    require((newest.get("status") in {"PENDING", "ACCEPTED"}
             or technical and newest.get("status") == "REJECTED")
            and not newest.get("response_error"), "newest account control receive rejected")
    for key in ("received_mono_ns", "received_utc_ns", "sequence", "source", "method",
                "request_id", "server_pid", "rate_limits_sha256"):
        require(observed.get(key) == newest.get(key), "newest account control observation differs")
    require(observed.get("owner") == owner, "account control observation owner mismatch")
    required = ("boot_id", "repo", "log_dir", "thread_id", "worker_pid", "worker_start",
                "server_pid", "server_start", "credit_run_id", "credit_budget", "credit_ledger_path")
    require(all(owner.get(key) is not None for key in required), "account control owner incomplete")
    for key in ("boot_id", "repo", "log_dir", "thread_id"):
        require(isinstance(owner.get(key), str) and bool(owner[key]), "account control owner identity missing")
    for key in ("worker_pid", "server_pid"):
        require(type(owner.get(key)) is int and owner[key] > 0, "account control owner pid invalid")
    for key in ("worker_start", "server_start"):
        require(isinstance(owner.get(key), str) and owner[key].isascii() and owner[key].isdigit(),
                "account control owner birth invalid")
    require((state.get("phase") in {"ready", "running", "waiting_for_input", "repair_review"}
             or _paused_retained_control(state))
            and control_context_eligible(state, current_receipt=current_receipt),
            "account control owner stopped or held")
    require(state.get("auth_mode") == "chatgpt", "account control authentication unknown")
    for key in ("log_dir", "thread_id", "worker_pid", "worker_start", "server_pid",
                "server_start", "repo", "guardian_run_id"):
        require(state.get(key) == owner.get(key), "account control current owner mismatch")
    goal = state.get("goal")
    require(isinstance(goal, dict) and goal.get("status") in {"active", "blocked", "paused"}
            and isinstance(goal.get("objective"), str) and bool(goal["objective"])
            and _account_value_sha256(goal["objective"]) == owner.get("goal_objective_sha256")
            and goal.get("threadId", owner["thread_id"]) == owner["thread_id"],
            "account control saved goal mismatch or terminal")
    source = observed.get("source")
    require(observed.get("server_pid") == owner["server_pid"]
            and ((source == "read" and observed.get("method") == "account/rateLimits/read"
                  and type(observed.get("request_id")) is int)
                 or (source == "notification" and observed.get("method") == "account/rateLimits/updated"
                     and observed.get("request_id") is None)), "account control receive source mismatch")
    require(type(observed.get("received_utc_ns")) is int, "account control UTC missing")
    for now, received in ((now_utc_ns, observed["received_utc_ns"]),
                          (now_mono_ns, observed["received_mono_ns"])):
        require(0 <= now - received < max_age_seconds * 1000000000,
                "account control observation stale")
    limits = state.get("last_rate_limits")
    require(isinstance(limits, dict) and isinstance(limits.get("primary"), dict),
            "account control limits missing")
    primary = limits["primary"]
    used = primary.get("usedPercent")
    require(isinstance(used, (int, float)) and not isinstance(used, bool) and math.isfinite(used)
            and 0 <= used <= 100 and primary.get("windowDurationMins") == 10080,
            "account control primary unknown")
    require(_account_value_sha256(limits) == observed.get("rate_limits_sha256"),
            "account control limits mismatch")
    require(state.get("credit_budget") == ledger
            and _account_value_sha256(ledger) == observed.get("credit_record_sha256"),
            "account control durable credit mismatch")
    require(type(ledger.get("schema_version")) is int and ledger["schema_version"] in (1, 2)
            and ledger.get("id") == owner["credit_run_id"]
            and amount(ledger.get("budget"), positive=True) == amount(owner["credit_budget"], positive=True),
            "account control original credit identity mismatch")
    initial, minimum, last, spent, remaining, budget = (
        amount(ledger.get(key), positive=(key == "budget")) for key in
        ("initial_balance", "minimum_balance", "last_balance", "spent", "remaining", "budget"))
    require(minimum <= initial and minimum <= last and spent >= initial - minimum
            and remaining == max(Decimal(0), budget - spent)
            and (ledger["schema_version"] != 1 or (last <= initial and spent == initial - minimum)),
            "account control retained credit accounting inconsistent")
    require(last == available_balance(limits) and remaining > 0,
            "account control credit exhausted or unknown")
    require(observed.get("state_limits_and_credit_persisted") is True,
            "account control persistence unconfirmed")
    return dict(observed)


def same_owner_resume_binding(directory):
    """Bind explicit user control to a fresh observation of the original owner."""
    from os_goal_guard_protocol import read_json
    state = read_json(Path(directory) / "state.json")
    if (type(state.get("same_owner_control_capability")) is not int
            or state["same_owner_control_capability"] != SAME_OWNER_CONTROL_CAPABILITY):
        raise ValueError("Resident controller does not advertise same-owner control capability v1; no resume command queued")
    current = state.get("goal") or {}
    technical = (isinstance(state.get("stop_reason"), str)
                 and state["stop_reason"] in TECHNICAL_CONTROL_STOPS)
    if (not control_context_eligible(state)
            or not (current.get("status") == "blocked" or
             current.get("status") == "paused" and _paused_retained_control(state))
            or current.get("objective") != OBJECTIVE
            or state.get("active_turns")
            or type(state.get("primary_stop_generation")) is not int
            or state["primary_stop_generation"] < 0):
        raise ValueError("Same-owner resume requires the exact idle blocked campaign")
    owner = _account_control_owner(state, directory, Path(state["repo"]))
    ledger = read_json(owner["credit_ledger_path"])
    observed_account_control(state, ledger, owner, time.time_ns(), time.monotonic_ns())
    binding = {"kind": "resume_same_owner", "schema_version": 1,
               "expected_owner": owner, "goal_sha256": _account_value_sha256(current),
               "primary_stop_generation": state["primary_stop_generation"],
               "execution_admission": False, "hold_release": False}
    if technical:
        binding["technical_checkpoint"] = {key: state[key] for key in
            ("stop_reason", "stop_now", "checkpoint_requested")}
    return binding


class RPC:
    """JSON-lines transport; waiting and goal observation consume no model tokens."""
    def __init__(self, argv, log_dir, on_event):
        self.on_event = on_event
        self.next_id = 0
        self.responses = {}
        self.pending_methods = {}
        self.response_contexts = {}
        self.account_receive_sequence = 0
        self.last_account_read_completion = None
        self.last_account_notification = None
        self.buffer = b""
        self.events = (log_dir / "protocol.jsonl").open("a", buffering=1)
        self.stderr = (log_dir / "server.stderr.log").open("ab")
        self.stderr_reader = (log_dir / "server.stderr.log").open("rb")
        self.stderr_decoder = codecs.getincrementaldecoder("utf-8")("replace")
        self.proc = subprocess.Popen(argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                     stderr=self.stderr, bufsize=0, start_new_session=True,
                                     env=runtime_environment())
        os.set_blocking(self.proc.stdin.fileno(), False)
        self.selector = selectors.DefaultSelector()
        self.selector.register(self.proc.stdout, selectors.EVENT_READ)

    def send(self, value, *, deadline=None):
        # A raw pipe may accept only part of a large JSON line. Never replay the
        # whole request after a partial send; call/delivery owns uncertainty.
        if getattr(self, "_send_failure", None) is not None:
            raise self._send_failure
        if deadline is None:
            deadline = getattr(self, "_call_deadline", None)
        if deadline is None:
            deadline = time.monotonic() + 45.0
        view = memoryview((json.dumps(value) + "\n").encode("utf-8"))
        fd = self.proc.stdin.fileno()
        try:
            with selectors.DefaultSelector() as writable:
                writable.register(fd, selectors.EVENT_WRITE)
                while view:
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        raise RecoverableFailure("App-server request timed out while sending")
                    if not writable.select(min(1.0, remaining)):
                        continue
                    try:
                        written = os.write(fd, view)
                    except (BlockingIOError, InterruptedError):
                        continue
                    if written <= 0:
                        raise BrokenPipeError("App-server stdin stopped accepting request bytes")
                    view = view[written:]
        except (RecoverableFailure, BrokenPipeError, ConnectionResetError) as error:
            # Appending another line could complete a malformed or uncertain
            # request. Retain this failure and prohibit further channel writes.
            error.rpc_send_incomplete = True
            self._send_failure = error
            raise

    def pump(self, timeout=1.0):
        self.pump_stderr()
        if b"\n" not in self.buffer:
            if not self.selector.select(timeout):
                return
            chunk = os.read(self.proc.stdout.fileno(), 65536)
            if not chunk:
                raise RecoverableFailure("Codex app server disconnected; see retained stderr.")
            self.buffer += chunk
        while b"\n" in self.buffer:
            line, self.buffer = self.buffer.split(b"\n", 1)
            message = json.loads(line)
            # Time the decoded receive, not the eventual return from call():
            # a newer notification may be consumed before a read is returned.
            self.account_receive_sequence += 1
            received_utc_ns = time.time_ns()
            received_mono_ns = time.monotonic_ns()
            if "method" not in message:
                ident = message["id"]
                if self.pending_methods.get(ident) == "account/rateLimits/read":
                    result = message.get("result")
                    limits = result.get("rateLimits") if isinstance(result, dict) else None
                    self.response_contexts[ident] = {
                        "schema_version": 1, "source": "read",
                        "method": "account/rateLimits/read", "request_id": ident,
                        "received_at": datetime.fromtimestamp(
                            received_utc_ns / 1000000000, timezone.utc).isoformat(),
                        "received_utc_ns": received_utc_ns,
                        "received_mono_ns": received_mono_ns,
                        "sequence": self.account_receive_sequence,
                        "server_pid": self.proc.pid,
                        "rate_limits_sha256": _account_value_sha256(limits),
                        "response_error": "error" in message,
                    }
                self.responses[ident] = message
                continue
            if message.get("method") == "account/rateLimits/updated":
                limits = (message.get("params") or {}).get("rateLimits")
                self.last_account_notification = {
                    "schema_version": 1, "source": "notification",
                    "method": "account/rateLimits/updated", "request_id": None,
                    "received_at": datetime.fromtimestamp(
                        received_utc_ns / 1000000000, timezone.utc).isoformat(),
                    "received_utc_ns": received_utc_ns,
                    "received_mono_ns": received_mono_ns,
                    "sequence": self.account_receive_sequence,
                    "server_pid": self.proc.pid,
                    "rate_limits_sha256": _account_value_sha256(limits),
                }
            self.events.write(json.dumps({"at": utc(), "event": message}) + "\n")
            if "id" in message:
                if message["method"] == USER_INPUT_METHOD:
                    self.send({"id": message["id"], "result": unattended_input(message["params"])})
                else:
                    # Full permissions are selected before execution. Unknown
                    # interactive protocols still require facts/authority we lack.
                    self.send({"id": message["id"], "error": {
                        "code": -32000, "message": "Unattended launcher cannot answer this protocol; checkpoint and stop."}})
            self.on_event(message)

    def pump_stderr(self, final=False):
        # Read the retained file, so stderr cannot fill a pipe and deadlock Codex.
        remaining = max(0, os.fstat(self.stderr_reader.fileno()).st_size - self.stderr_reader.tell()) if final else 65536
        while remaining:
            chunk = self.stderr_reader.read(min(remaining, 65536))
            if not chunk:
                break
            remaining -= len(chunk)
            value = self.stderr_decoder.decode(chunk)
            if value:
                self.on_event({"method": "launcher/serverStderr", "params": {"delta": value}})
        if final:
            value = self.stderr_decoder.decode(b"", final=True)
            if value:
                self.on_event({"method": "launcher/serverStderr", "params": {"delta": value}})

    def call(self, method, params, timeout=45.0):
        deadline = time.monotonic() + timeout
        previous_deadline = getattr(self, "_call_deadline", None)
        if previous_deadline is not None:
            deadline = min(deadline, previous_deadline)
        if method == "account/rateLimits/read":
            self.last_account_read_completion = None
        self.next_id += 1
        ident = self.next_id
        self.pending_methods[ident] = method
        self.events.write(json.dumps({"at": utc(), "request": method, "id": ident}) + "\n")
        self._call_deadline = deadline
        try:
            self.send({"id": ident, "method": method, "params": params}, deadline=deadline)
            while ident not in self.responses:
                if time.monotonic() >= deadline:
                    raise RecoverableFailure("App-server request timed out: " + method)
                self.pump(min(1.0, max(0.0, deadline - time.monotonic())))
        except (RecoverableFailure, BrokenPipeError, ConnectionResetError) as error:
            self.pending_methods.pop(ident, None)
            self.response_contexts.pop(ident, None)
            if not hasattr(error, "rpc_method"):
                error.rpc_method = method
                error.rpc_mutating = method not in READ_ONLY_RPC_METHODS
            if (isinstance(error, RecoverableFailure) and
                    str(error) == "App-server request timed out while sending"):
                error.args = ("App-server request timed out: " + error.rpc_method,)
            raise
        finally:
            self._call_deadline = previous_deadline
        response = self.responses.pop(ident)
        self.pending_methods.pop(ident, None)
        completion = self.response_contexts.pop(ident, None)
        if method == "account/rateLimits/read":
            self.last_account_read_completion = completion
        if "error" in response:
            raise RuntimeError(method + ": " + json.dumps(response["error"]))
        return response["result"]

    def close(self):
        guard_owner_close(getattr(self, "owner_custody_retained", False))
        # Only this launcher's server process; never kill a host-wide process name.
        self.close_errors = []
        if self.proc.stdin:
            try:
                self.proc.stdin.close()
            except OSError as error:
                self.close_errors.append("stdin.close: " + str(error))
        try:
            self.proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.proc.kill()
                self.proc.wait(timeout=5)
        self.selector.close()
        self.proc.stdout.close()
        self.pump_stderr(final=True)
        self.stderr_reader.close()
        self.events.close()
        self.stderr.close()


def launch_resources(args, repo):
    """Cache configuration/planning only; actual jobs need fresh admission."""
    if not hasattr(args, "resources"):
        args.resources = resolve_resources(args.profile, args.max_agents,
                                           args.build_jobs, args.memory_gib, repo)
    return args.resources


def policy_hashes(repo):
    entrypoint = repo / "CAMPAIGN.md"
    return ({"CAMPAIGN.md": hashlib.sha256(entrypoint.read_bytes()).hexdigest()}
            if entrypoint.is_file() else {})


def agent_settings(args, repo):
    return {"enabled": True,
            "max_concurrent_threads_per_session": launch_resources(args, repo)["max_agents"],
            "max_depth": 1, "default_subagent_model": DEFAULT_WORKER_MODEL,
            "default_subagent_reasoning_effort": MINIMUM_WORKER_EFFORT}


def dispatcher_candidates(catalog, unavailable=()):
    """Return advertised max-first dispatcher pairs; perform no inference/retry.

    Accept the app-server model/list rows, a model-keyed mapping, or the retained
    controller catalog's models/efforts rows. Callers still enforce exact capacity
    classification, account holds, cooldown, ownership and finite run limits.
    """
    if isinstance(catalog, dict):
        rows = catalog.get("models", catalog.get("data", catalog))
        rows = rows.values() if isinstance(rows, dict) else rows
    else:
        rows = catalog
    offered = {}
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get("model"), str):
            raise ValueError("Dispatcher catalog requires named model rows")
        name = row["model"]
        raw = row.get("supportedReasoningEfforts", row.get("efforts", []))
        efforts = {item.get("reasoningEffort") if isinstance(item, dict) else item
                   for item in raw}
        efforts &= set(DISPATCHER_EFFORT_PREFERENCE)
        if name in offered and offered[name] != efforts:
            raise ValueError("Conflicting dispatcher model catalog rows: " + name)
        offered[name] = efforts
    excluded = set(unavailable)
    result = []
    # Prefer max-capable choices across the ranked models before lowering the
    # dispatcher effort. A failed model is excluded as a whole, never retried at
    # a different effort to reinterpret a service rejection.
    for maximum in (True, False):
        for name in DISPATCHER_MODEL_PREFERENCE:
            efforts = offered.get(name, set())
            if name in excluded or not efforts or ("max" in efforts) != maximum:
                continue
            effort = next(value for value in DISPATCHER_EFFORT_PREFERENCE if value in efforts)
            result.append({"model": name, "effort": effort})
    return result


def model_routing(args):
    """One source for model admission, dispatcher guidance and preview output."""
    return {
        "dispatcher": {"model": args.model, "effort": args.effort},
        "default_worker": {"model": DEFAULT_WORKER_MODEL, "effort": MINIMUM_WORKER_EFFORT},
        "complex_worker": {"model": DEFAULT_WORKER_MODEL, "effort": MINIMUM_WORKER_EFFORT},
        "auditor": {"model": AUDIT_MODEL, "effort": MINIMUM_WORKER_EFFORT},
        "reviewer": {"model": REVIEW_MODEL, "effort": MINIMUM_WORKER_EFFORT},
    }


def server_argv(args, repo):
    settings = {
        "model": args.model,
        "model_reasoning_effort": args.effort,
        "features.goals": True,
        "approval_policy": "never",
        # The user explicitly authorized full access for the standalone launcher.
        # This is local to this process; global config/project trust are unchanged.
        "sandbox_mode": "danger-full-access",
    }
    settings.update(("agents." + key, value) for key, value in agent_settings(args, repo).items())
    settings.update(("shell_environment_policy.set." + key, value)
                    for key, value in resource_environment(launch_resources(args, repo)).items())
    argv = [args.codex, "--strict-config", "-C", str(repo)]
    for key, value in settings.items():
        argv.extend(["-c", key + "=" + json.dumps(value)])
    argv += ["app-server", "--stdio"]
    if getattr(args, "continuous", False):
        affinity = sorted(set(os.sched_getaffinity(0)) & {0, 6, 7})
        taskset = shutil.which("taskset")
        if not affinity or taskset is None:
            raise RuntimeError("Continuous HOST controller needs taskset and CPUs 0,6,7 admission")
        # Bind the NEW controller and descendants. Native execution requires
        # its own separately admitted explicit CPU profile.
        argv = [taskset, "--cpu-list", ",".join(map(str, affinity))] + argv
    return argv


def preflight(rpc, args, repo):
    rpc.call("initialize", {"clientInfo": {"name": "mckernel-os-goal", "version": "1.0"},
                            "capabilities": {"experimentalApi": True}})
    rpc.send({"method": "initialized", "params": {}})
    config = rpc.call("config/read", {"cwd": str(repo), "includeLayers": False})["config"]
    agents = config.get("agents") or {}
    expected = agent_settings(args, repo)
    if (config.get("model") != args.model or config.get("model_reasoning_effort") != args.effort
            or not (config.get("features") or {}).get("goals")
            or config.get("approval_policy") != "never"
            or any(agents.get(key) != value for key, value in expected.items())):
        raise RuntimeError("Effective Codex settings differ from the requested dispatch limits.")
    build_env = (config.get("shell_environment_policy") or {}).get("set") or {}
    if any(build_env.get(key) != value
           for key, value in resource_environment(launch_resources(args, repo)).items()):
        raise RuntimeError("Effective build environment differs from the requested resource profile.")
    models, catalog_rows, cursor = {}, [], None
    while True:
        page = rpc.call("model/list", {"includeHidden": True, "limit": 100, "cursor": cursor})
        catalog_rows.extend(page["data"])
        models.update((row["model"], row) for row in page["data"])
        cursor = page.get("nextCursor")
        if not cursor:
            break
    choices = dispatcher_candidates(catalog_rows)
    requested_dispatcher = {"model": args.model, "effort": args.effort}
    available = {r["reasoningEffort"] for r in
                 models.get(args.model, {}).get("supportedReasoningEfforts", [])}
    if args.effort not in available:
        if args.dispatcher_pinned:
            raise RuntimeError("Pinned dispatcher model/effort not advertised: " +
                               args.model + "/" + args.effort)
        if not choices:
            raise RuntimeError("No eligible dispatcher model/effort advertised")
        args.model, args.effort = choices[0]["model"], choices[0]["effort"]
    for selection in model_routing(args).values():
        model, effort = selection["model"], selection["effort"]
        if effort not in {r["reasoningEffort"] for r in models.get(model, {}).get("supportedReasoningEfforts", [])}:
            raise RuntimeError("Required model/effort not advertised: " + model + "/" + effort)
    # Deliberately do not serialize the full personal config or authentication data.
    return {"model": args.model, "effort": args.effort, "agents": expected,
            "model_routing": model_routing(args),
            "requested_dispatcher": requested_dispatcher,
            "dispatcher_selection": "pinned" if args.dispatcher_pinned else "advertised_preference",
            # Strict config above checks the server defaults. Thread start/resume
            # passes the selected pair explicitly and verifies its own readback.
            "server_defaults": {"model": config["model"],
                                "effort": config["model_reasoning_effort"]},
            "dispatcher_preference": choices,
            "included_usage_stop_percent": INCLUDED_USAGE_STOP_PERCENT,
            "billing": billing_policy(args),
            "resources": launch_resources(args, repo), "policy_sha256": policy_hashes(repo),
            "agent_windows": window_capability(args.agent_windows),
            "goals": True, "approval_policy": "never", "sandbox_mode": "danger-full-access",
            "scope": "Configuration and advertised models only; quota and inference untested."}


def temporary_usage_read_failure(error):
    """Classify only observed failures of the read-only usage endpoint."""
    return isinstance(error, RuntimeError) and classify_usage_failure(str(error)) is not None


class Campaign:
    def __init__(self, args, repo, directory, rpc_factory=RPC):
        self.args, self.repo, self.directory = args, repo, directory
        self.state_path = directory / "state.json"
        self.state = json.loads(self.state_path.read_text()) if self.state_path.exists() else {
            "schema_version": 1, "repo": str(repo), "thread_id": None, "created_at": utc()}
        if self.state.get("schema_version") != 1 or self.state.get("repo") != str(repo):
            raise RuntimeError("State belongs to a different repository or unsupported schema.")
        self.prior_policy_failure = (dict(failure_location(self.state))
                                     if is_policy_stop(self.state) else None)
        self.log_dir = directory / "runs" / (datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid4().hex[:8])
        self.log_dir.mkdir(parents=True, mode=0o700)
        self.rpc_factory, self.rpc = rpc_factory, None
        self.active = {}
        self.capacity_children = {}
        self.child_capacity_failures = []
        self.goal = None
        self.primary_stop_generation = (self.state.get("primary_stop_generation", 0)
                                       if getattr(args, "same_owner_control", False) else 0)
        if type(self.primary_stop_generation) is not int or self.primary_stop_generation < 0:
            raise ValueError("Invalid saved primary stop generation")
        self.stop_reason = None
        self.stop_now = False
        self.checkpoint_requested = False
        self.credit_guard = (CreditBudget(directory, args.credit_run_id, args.credit_budget,
                                          atomic_json, recovered=args.recovered)
                             if getattr(args, "credit_budget", None) is not None else None)
        # Memory-only: never inherit usage freshness from a preceding worker/server.
        self.state.pop("credit_timeout_shutdown_pause", None)
        self.state.pop("credit_timeout_startup", None)
        self.state.pop("transport_shutdown_pause", None)
        self.state.pop("transport_startup", None)
        self.state.pop("transport_failure", None)
        for key in ("successful_account_read", "last_account_observation",
                    "last_account_notification", "last_account_control_observation"):
            self.state.pop(key, None)
        self.state.pop("same_owner_control_capability", None)
        self.last_credit_notification = None
        self.last_activity = time.monotonic()
        self.stopping = False
        self.controlled = False
        self.native_owner_control = None
        self.native_owner_control_failed = False
        self.retained_for_stop = False
        self.retention_errors = []
        self.output = LiveOutput(self.log_dir, quiet=args.quiet, agent_windows=args.agent_windows)
        self.output.primary = self.state.get("thread_id")
        # Saved hints belong to the preceding launcher instance, never this monitor.
        previous = {key: self.state[key] for key in
                    ('capture_progress_registration', 'capture_progress') if key in self.state}
        if previous:
            atomic_json(self.log_dir / 'prior-capture-progress.json', dict(
                classification='historical_inactive_instance_hints', recorded_at=utc(),
                previous_thread_id=self.state.get('thread_id'),
                previous_worker_pid=self.state.get('worker_pid'),
                previous_log_dir=self.state.get('log_dir'), hints=previous))
        self.state.pop('capture_progress_registration', None)
        self.state['capture_progress'] = []
        # Explicit future-capture registration; no path discovery or data execution.
        self.capture_progress_directory = getattr(args, 'capture_progress_directory', None)
        self.capture_progress_accepted = {}
        self.capture_progress_notices = set()
        if self.capture_progress_directory is not None:
            path = validate_capture_progress_directory(self.capture_progress_directory)
            self.state['capture_progress_registration'] = dict(
                directory=str(path), registered_at=utc(), terminal=False,
                direct_child_joined=False, release_authorized=False)

    def poll_native_owner_control(self):
        """Service this owning controller only; replies never grant native RAM."""
        if not self.controlled or self.native_owner_control_failed:
            return
        try:
            import native_current_owner
            if self.native_owner_control is None:
                self.native_owner_control = native_current_owner.CurrentOwnerServer.__new__(native_current_owner.CurrentOwnerServer)
                self.native_owner_control.__init__(self)
                self.save(native_current_owner=dict(path=self.native_owner_control.path,
                    pid=os.getpid(), birth=self.native_owner_control.start,
                    source_sha256=native_current_owner.LOADED_SOURCE_SHA256,
                    scope="controller_account_data_only_not_native_admission"))
            self.native_owner_control.poll()
        except Exception as error:
            # Close every own data-channel handle BEFORE a possibly failing
            # receipt. Neither cleanup nor receipt loss changes native custody.
            self.native_owner_control_failed = True
            secondary = []
            primary_interrupt = getattr(error, "interrupt", None)
            if self.native_owner_control is not None:
                try:self.native_owner_control.close()
                except BaseException as close_error:secondary.append(close_error)
            # Select any real interruption BEFORE fallible diagnostics. The
            # close wrapper retains nested KeyboardInterrupt/SystemExit too.
            for close_error in secondary:
                interrupt = (close_error if isinstance(close_error, (KeyboardInterrupt, SystemExit))
                             else getattr(close_error, "interrupt", None))
                if primary_interrupt is None and interrupt is not None:
                    primary_interrupt = interrupt
            try:
                self.save(native_current_owner_error=str(error),
                          native_current_owner_close_errors=[str(x) for x in secondary])
            except BaseException as receipt_error:
                receipt_error.native_primary_error = error
                receipt_error.native_close_errors = secondary
                if primary_interrupt is not None:
                    primary_interrupt.native_secondary_errors = secondary + [receipt_error]
                    raise primary_interrupt from error
                raise
            if primary_interrupt is not None:
                primary_interrupt.native_secondary_errors = secondary
                raise primary_interrupt from error
            for close_error in secondary:
                interrupt = (close_error if isinstance(close_error, (KeyboardInterrupt, SystemExit))
                             else getattr(close_error, "interrupt", None))
                if interrupt is not None:
                    interrupt.native_primary_error = error
                    raise interrupt

    def poll_capture_progress(self):
        """Read two registered hints only; never dispatch, signal or grant clearance."""
        if self.capture_progress_directory is None:
            return
        rows = []
        for event in ('CHILD_JOIN_PENDING', 'QUARANTINE_MARKER_OBSERVED'):
            path = self.capture_progress_directory / ('progress-' + event.lower() + '.json')
            key = str(path)
            row = self.capture_progress_accepted.get(key)
            if row is None:
                row = dict(path=key, observation='awaiting_file', terminal=False,
                           direct_child_joined=False, release_authorized=False)
                fd = None
                try:
                    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
                    info = os.fstat(fd)
                    if not (stat.S_ISREG(info.st_mode) and info.st_uid == os.getuid()
                            and info.st_nlink == 1 and info.st_size <= 8192):
                        raise ValueError('unexpected progress file shape')
                    data = json.loads(os.read(fd, 8193))
                    if not (isinstance(data, dict) and data.get('schema') == 'capture-progress.v1'
                            and data.get('event') == event
                            and data.get('capture_directory') == str(self.capture_progress_directory)
                            and data.get('terminal') is False
                            and data.get('direct_child_joined') is False
                            and data.get('release_authorized') is False
                            and type(data.get('pid')) is int and data['pid'] > 0
                            and isinstance(data.get('proc_start_ticks'), str)
                            and 0 < len(data['proc_start_ticks']) <= 32
                            and data['proc_start_ticks'].isascii() and data['proc_start_ticks'].isdigit()):
                        raise ValueError('unexpected progress record')
                    row.update(observation=event, pid=data['pid'],
                               proc_start_ticks=data['proc_start_ticks'])
                    self.capture_progress_accepted[key] = row
                except FileNotFoundError:
                    pass
                except OSError:
                    row['observation'] = 'unreadable_file'
                except (ValueError, UnicodeError, RecursionError):
                    row['observation'] = 'invalid_file'
                finally:
                    if fd is not None:
                        os.close(fd)
            rows.append(row)
            notice = (key, row['observation'])
            # At most four notices per fixed file, including failed-read diagnostics.
            if notice not in self.capture_progress_notices:
                self.capture_progress_notices.add(notice)
                self.output.notice('CAPTURE_PROGRESS nonterminal; ' + json.dumps(row, sort_keys=True))
        self.state['capture_progress'] = rows

    def save(self, **fields):
        self.state.update(fields)
        self.state['capture_progress_capability'] = CAPTURE_PROGRESS_CAPABILITY
        if getattr(self.args, "same_owner_control", False):
            self.state.update(same_owner_control_capability=SAME_OWNER_CONTROL_CAPABILITY,
                              primary_stop_generation=self.primary_stop_generation,
                              checkpoint_requested=self.checkpoint_requested,
                              stop_now=self.stop_now,
                              continuous=getattr(self.args, "continuous", False))
        self.state.update(updated_at=utc(), log_dir=str(self.log_dir), active_turns=self.active,
                          agents=self.output.snapshot(), console_log=str(self.log_dir / "console.log"),
                          agent_event_count=self.output.agent_event_count)
        atomic_json(self.state_path, self.state)

    def record_stop_diagnostic(self, event, *, error=None, reason=None, exit_code=None, snapshot=None):
        """Keep failure history across restarts without changing recovery authority."""
        state = dict(self.state if snapshot is None else snapshot)
        state.setdefault("log_dir", str(self.log_dir))
        state.setdefault("worker_pid", os.getpid())
        try:
            result = write_stop_record(self.directory, state, event=event, error=error,
                                       reason=reason, exit_code=exit_code)
            self.save(stop_journal=result["journal_path"], latest_stop=result["latest_path"],
                      last_stop_record_id=result["record"]["record_id"])
        except (OSError, ValueError, TypeError) as error:
            # The existing console remains a fallback; logging failure is never
            # permission to reset a goal or repeat an uncertain operation.
            self.output.notice("Stop journal write failed (" + type(error).__name__
                               + "); retain console and state diagnostics.")

    def remember_started_turn(self, thread_id, turn):
        ident = turn.get("id")
        if not isinstance(ident, str) or not ident:
            raise ValueError("Started turn response has no turn identity")
        completed = self.state.get("last_turn") or {}
        terminal = {"completed", "failed", "interrupted"}
        # A completion can be pumped before the start response. Never resurrect
        # that turn; otherwise block a second start while notifications catch up.
        if (turn.get("status") not in terminal and
                not (completed.get("thread_id") == thread_id and completed.get("id") == ident
                     and completed.get("status") in terminal)):
            self.active[thread_id] = ident
        self.last_activity = time.monotonic()
        return ident

    def review_blocked_goal(self):
        """One same-Root diagnosis, then monitored waiting for changed input.

        This never sets a blocked goal active. Actual hard stops are handled by
        the normal run loop before this method. An uncertain turn/start is not
        resubmitted, including after supervisor recovery.
        """
        if self.active:
            return
        view = dict(self.state, active_turns=dict(self.active), goal=self.goal,
                    stop_reason=self.stop_reason, stop_now=self.stop_now,
                    checkpoint_requested=self.checkpoint_requested)
        key = blocked_repair_key(self.goal, view)
        reviews = self.state.get("blocked_repair_reviews", {})
        if not isinstance(reviews, dict):
            raise ValueError("Invalid saved repair review receipts")
        if not key or key in reviews:
            if self.state.get("phase") != "waiting_for_input":
                self.save(phase="waiting_for_input", waiting_reason="blocked_goal_requires_changed_input")
                self.record_stop_diagnostic("blocked_wait", reason="goal_blocked")
                self.output.notice("Blocked task retained; waiting for changed input or a queued instruction.")
            return
        self.refresh_credit_budget()
        if self.stop_reason or self.stop_now:
            return
        # A read can deliver a newer stop or an active turn. Revalidate before
        # sending, and persist the receipt before the mutating RPC.
        self.remember_goal(self.rpc.call("thread/goal/get", {"threadId": self.state["thread_id"]})["goal"])
        view.update(self.state, active_turns=dict(self.active), goal=self.goal,
                    stop_reason=self.stop_reason, stop_now=self.stop_now,
                    checkpoint_requested=self.checkpoint_requested)
        if blocked_repair_key(self.goal, view) != key:
            return
        message = blocked_repair_instruction(self.goal, view)
        receipt = {"key": key, "status": "sending", "submitted_at": utc(),
                   "thread_id": self.state["thread_id"], "log_dir": str(self.log_dir)}
        generation = self.primary_stop_generation
        reviews = dict(reviews, **{key: receipt})
        self.save(blocked_repair_reviews=reviews, phase="repair_review")
        self.record_stop_diagnostic("blocked_repair_review", reason="goal_blocked")
        if (self.stop_reason or self.stop_now or self.checkpoint_requested or self.active
                or self.primary_stop_generation != generation or not self.goal
                or self.goal.get("status") != "blocked"):
            self.save(blocked_repair_reviews=dict(reviews, **{
                key: dict(receipt, status="cancelled_before_submission")}))
            return
        try:
            started = self.rpc.call("turn/start", {"threadId": self.state["thread_id"],
                "input": [{"type": "text", "text": message}]})
            turn = started["turn"]
            turn_id = self.remember_started_turn(self.state["thread_id"], turn)
            receipt = dict(receipt, status="accepted_by_server", turn_id=turn_id)
            self.save(blocked_repair_reviews=dict(reviews, **{key: receipt}))
        except Exception as error:
            receipt = dict(receipt, status="delivery_uncertain", error_type=type(error).__name__)
            self.stop_reason, self.stop_now = "rpc_delivery_uncertain", True
            self.save(blocked_repair_reviews=dict(reviews, **{key: receipt}),
                      transport_uncertain={"at": utc(), "method": "turn/start",
                          "reason": "repair_review_delivery_uncertain"})
            self.record_stop_diagnostic("repair_review_delivery_uncertain", error=error,
                                        reason=self.stop_reason)

    def register_instruction_capture_progress(self, item, receipt):
        """Durably acknowledge visibility registration before this instruction steers."""
        if 'capture_progress' not in item:
            return ''
        data = item['capture_progress']
        if (not isinstance(data, dict) or set(data) != {
                'directory', 'capability_version', 'expected_thread_id', 'expected_worker_pid', 'expected_log_dir'}
                or type(data.get('capability_version')) is not int
                or data['capability_version'] != CAPTURE_PROGRESS_CAPABILITY
                or type(self.state.get('capture_progress_capability')) is not int
                or self.state['capture_progress_capability'] != CAPTURE_PROGRESS_CAPABILITY
                or data.get('expected_thread_id') != self.state.get('thread_id')
                or type(data.get('expected_worker_pid')) is not int
                or data['expected_worker_pid'] != os.getpid()
                or data['expected_worker_pid'] != self.state.get('worker_pid')
                or data.get('expected_log_dir') != str(self.log_dir)):
            raise ValueError('capture registration refused: current thread or launcher instance differs')
        path = validate_capture_progress_directory(data['directory'])
        if path == self.capture_progress_directory:
            raise ValueError('capture registration refused: directory already registered')
        registration = dict(directory=str(path), capability_version=CAPTURE_PROGRESS_CAPABILITY,
            registered_at=utc(), instruction_id=item['id'],
            thread_id=self.state['thread_id'], worker_pid=os.getpid(), log_dir=str(self.log_dir),
            terminal=False, direct_child_joined=False, release_authorized=False)
        receipt['previous_capture_progress_registration'] = self.state.get('capture_progress_registration')
        receipt['previous_capture_progress'] = self.state.get('capture_progress', [])
        receipt['capture_progress_registration'] = registration
        # A failed save prevents steering. It never authorizes a capture or clears a lock.
        prior = {key: self.state[key] for key in ('capture_progress_registration', 'capture_progress')
                 if key in self.state}
        try:
            self.save(capture_progress_registration=registration, capture_progress=[])
        except OSError:
            # save updates memory before writing; restore it before recording refusal.
            for key in ('capture_progress_registration', 'capture_progress'):
                if key in prior:
                    self.state[key] = prior[key]
                else:
                    self.state.pop(key, None)
            raise
        self.capture_progress_directory = path
        self.capture_progress_accepted = {}
        self.capture_progress_notices = set()
        self.output.notice('Registered capture progress (nonterminal; no execution or release authority): '
                           + json.dumps(registration, sort_keys=True))
        return ('\nLauncher visibility acknowledgment: ' + json.dumps(registration, sort_keys=True)
                + '\nThis registers progress only. Existing execution, ownership and terminal checks still apply.')

    def finish_control_instruction(self, sending, receipt, *, refused=False):
        """Archive a claimed control command durably, without requeueing it."""
        destination = self.directory / "instructions" / ("refused" if refused else "delivered")
        destination.mkdir(mode=0o700, parents=True, exist_ok=True)
        if refused:
            os.link(sending, destination / sending.name, follow_symlinks=False)
            path = destination / (sending.stem + ".receipt.json")
        else:
            path = destination / sending.name
        atomic_json(path, receipt)
        self.save(last_instruction=receipt)
        sending.unlink()
        (sending.parent / (sending.stem + ".control-intent.json")).unlink(missing_ok=True)
        for directory in (sending.parent, destination):
            fd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
            try:
                os.fsync(fd)
            finally:
                os.close(fd)

    def deliver_same_owner_resume(self, item, receipt, sending):
        """Apply an explicit bound control on this RPC; never grant job resources."""
        from os_goal_guard_protocol import read_json
        attempted = False
        read_failed = False
        control = item.get("control")
        technical = control.get("technical_checkpoint") if isinstance(control, dict) else None
        receipt.update(control_kind="resume_same_owner", execution_admission=False, hold_release=False)

        def stop_flags():
            return {"stop_reason": self.stop_reason, "stop_now": self.stop_now,
                    "checkpoint_requested": self.checkpoint_requested}

        def runtime_view():
            return dict(self.state, goal=self.goal, **stop_flags())

        def stops_changed():
            expected = technical or {"stop_reason": None, "stop_now": False,
                                     "checkpoint_requested": False}
            return stop_flags() != expected

        def confirm_stopped_goal():
            self.pause()
            if self.goal and (self.goal.get("objective") != OBJECTIVE or
                    self.goal.get("status") not in {"paused", "blocked", "complete",
                                                   "usageLimited", "budgetLimited"}):
                raise ValueError("Compensating pause did not confirm a stopped goal")

        def read(method, params):
            nonlocal read_failed
            try:
                return self.rpc.call(method, params)
            except Exception:
                read_failed = True
                raise

        def ready():
            if (not getattr(self.args, "same_owner_control", False)
                    or self.state.get("same_owner_control_capability") != SAME_OWNER_CONTROL_CAPABILITY
                    or not self.controlled or self.active or stops_changed()
                    or self.primary_stop_generation != control["primary_stop_generation"]
                    or self.state.get("primary_stop_generation") != self.primary_stop_generation
                    or not self.goal or not (self.goal.get("status") == "blocked" or
                        self.goal.get("status") == "paused"
                        and getattr(self.args, "continuous", False)
                        and _paused_retained_control(self.state))
                    or self.goal.get("objective") != OBJECTIVE
                    or _account_value_sha256(self.goal) != control["goal_sha256"]
                    or not control_context_eligible(runtime_view(), current_receipt=receipt)
                    or technical is not None and any(self.state.get(key) != value
                                                     for key, value in technical.items())
                    or (self.state.get("transport_failure") or {}).get("channel_unusable")):
                raise ValueError("Same-owner resume context changed, stopped or unavailable")
            owner = _account_control_owner(self.state, self.directory, self.repo)
            if (owner != control["expected_owner"] or self.rpc.proc.pid != owner["server_pid"]
                    or os.getpid() != owner["worker_pid"] or self.credit_guard is None
                    or self.credit_guard.identifier != owner["credit_run_id"]
                    or self.credit_guard.budget != amount(owner["credit_budget"], positive=True)
                    or str(self.credit_guard.path) != owner["credit_ledger_path"]):
                raise ValueError("Same-owner resume original owner or credit run changed")
            return owner

        try:
            required = {"kind", "schema_version", "expected_owner", "goal_sha256",
                        "primary_stop_generation", "execution_admission", "hold_release"}
            if technical is not None:
                required.add("technical_checkpoint")
            if (not isinstance(control, dict) or set(control) != required
                    or control.get("kind") != "resume_same_owner" or control.get("schema_version") != 1
                    or control.get("execution_admission") is not False or control.get("hold_release") is not False
                    or type(control.get("primary_stop_generation")) is not int
                    or not isinstance(item.get("source_id"), str) or not 0 < len(item["source_id"]) <= 512
                    or item.get("capture_progress") != SAME_OWNER_CONTROL_LEGACY_BARRIER):
                raise ValueError("Invalid source-bound same-owner control command")
            if technical is not None and (not isinstance(technical, dict)
                    or set(technical) != {"stop_reason", "stop_now", "checkpoint_requested"}
                    or technical.get("stop_reason") not in TECHNICAL_CONTROL_STOPS
                    or type(technical.get("stop_now")) is not bool
                    or type(technical.get("checkpoint_requested")) is not bool):
                raise ValueError("Invalid bound technical checkpoint")
            digest = hashlib.sha256(item["source_id"].encode()).hexdigest()
            source = read_json(self.directory / "instructions" / "sources" / (digest + ".json"))
            if (item.get("id") != "source-" + digest or sending.name != item["id"] + ".json"
                    or source.get("status") != "queued" or source.get("item") != item
                    or item.get("text_sha256") != hashlib.sha256(item["text"].encode()).hexdigest()):
                raise ValueError("Same-owner control source binding differs")
            self.current_control_receipt = receipt
            ready()
            # Flush the claimed original before any control RPC. A crash leaves
            # sending evidence, which the existing queue guard never replays.
            for directory in (sending.parent, self.directory / "instructions" / "pending"):
                fd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
                try:
                    os.fsync(fd)
                finally:
                    os.close(fd)
            account = read("account/read", {"refreshToken": False}).get("account") or {}
            if account.get("type") != "chatgpt":
                self.save(auth_mode=account.get("type"))
                self.stop_reason, self.stop_now = "chatgpt_auth_changed", True
                raise ValueError("Same-owner control authentication unavailable")
            self.refresh_credit_budget(control_only=True)
            ready()
            page = read("thread/turns/list", {"threadId": self.state["thread_id"],
                        "limit": 1, "sortDirection": "desc", "itemsView": "notLoaded"})
            if any(turn.get("status") == "inProgress" for turn in page["data"]):
                raise ValueError("Same-owner control found an existing active turn")
            generation = self.primary_stop_generation
            current = read("thread/goal/get", {"threadId": self.state["thread_id"]})["goal"]
            ready()  # Read-time pause/stop notifications beat a stale read response.
            if not current or _account_value_sha256(current) != control["goal_sha256"]:
                raise ValueError("Same-owner control exact saved goal changed")
            self.remember_goal(current)
            owner = ready()
            observed_account_control(self.state, read_json(self.credit_guard.path), owner,
                                     time.time_ns(), time.monotonic_ns(), current_receipt=receipt)
            receipt.update(status="sending", source_id=item["source_id"],
                           goal_before_sha256=control["goal_sha256"], owner=owner,
                           primary_stop_generation=generation, method="thread/goal/set")
            atomic_json(sending.parent / (sending.stem + ".control-intent.json"), receipt)
            self.save(last_instruction=receipt)
            ready()
            observed_account_control(self.state, read_json(self.credit_guard.path), owner,
                                     time.time_ns(), time.monotonic_ns(), current_receipt=receipt)
            attempted = True
            result = self.rpc.call("thread/goal/set", {"threadId": owner["thread_id"], "status": "active"})["goal"]
            if (stops_changed()
                    or _same_owner_control_blocker(self.state, receipt, allow_technical=technical is not None)
                    or self.primary_stop_generation != generation or not self.goal
                    or self.goal.get("status") in {"complete", "usageLimited", "budgetLimited"}):
                # The normal protocol has no CAS. A later stop wins even when
                # it arrives inside activation; compensate on the SAME RPC.
                confirm_stopped_goal()
                receipt.update(status="cancelled_after_stop", delivered_at=utc())
            else:
                if (not result or result.get("status") != "active" or result.get("objective") != OBJECTIVE
                        or result.get("threadId", owner["thread_id"]) != owner["thread_id"]):
                    raise ValueError("Same-owner activation response differs")
                self.remember_goal(result)
                receipt.update(status="accepted_by_server", delivered_at=utc(),
                               goal_after_sha256=_account_value_sha256(result))
                if technical is not None:
                    # Acknowledge only the checkpoint explicitly bound by this
                    # user command. Signals cannot be overwritten mid-clear.
                    mask = signal.pthread_sigmask(signal.SIG_BLOCK,
                        {signal.SIGINT, signal.SIGTERM, signal.SIGHUP, signal.SIGUSR1})
                    try:
                        if stops_changed() or self.primary_stop_generation != generation:
                            raise ValueError("Technical checkpoint changed before acknowledgement")
                        receipt["acknowledged_checkpoint"] = dict(technical)
                        self.stop_reason, self.stop_now, self.checkpoint_requested = None, False, False
                        self.save(stop_reason=None, last_instruction=receipt,
                                  acknowledged_technical_checkpoint={
                                      "instruction_id": item["id"], "checkpoint": dict(technical),
                                      "primary_stop_generation": generation, "at": utc()})
                    finally:
                        signal.pthread_sigmask(signal.SIG_SETMASK, mask)
                    if (self.stop_reason or self.stop_now or self.checkpoint_requested
                            or self.primary_stop_generation != generation):
                        confirm_stopped_goal()
                        receipt.update(status="cancelled_after_stop")
                        self.save(stop_reason=self.stop_reason)
            self.finish_control_instruction(sending, receipt)
        except Exception as error:
            if attempted:
                receipt.update(status="delivery_uncertain", error_type=type(error).__name__)
                self.stop_reason = self.stop_reason or "rpc_delivery_uncertain"
                self.stop_now = True
                self.save(last_instruction=receipt, stop_reason=self.stop_reason, transport_uncertain={"at": utc(),
                          "method": "thread/goal/set", "reason": "same_owner_control_delivery_uncertain"})
                self.output.notice("Same-owner control outcome uncertain; original intent retained at " + str(sending))
                return
            if read_failed:
                self.stop_reason = self.stop_reason or "account_control_unknown"
                self.stop_now = True
            receipt.update(status="same_owner_resume_refused", error=str(error), refused_at=utc())
            if self.stop_reason is not None:
                self.save(stop_reason=self.stop_reason)
            try:
                self.finish_control_instruction(sending, receipt, refused=True)
            except OSError as archive_error:
                receipt.update(status="control_archive_failed_before_activation", error_type=type(archive_error).__name__)
                self.save(last_instruction=receipt)
        finally:
            if getattr(self, "current_control_receipt", None) is receipt:
                del self.current_control_receipt

    def deliver_instruction(self, *, control_only=False):
        """Steer one active coordinator turn; retain uncertain deliveries for audit."""
        ident = self.state.get("thread_id")
        waiting = (getattr(self.args, "repair_agent_failures", False) and self.goal
                   and self.goal.get("status") == "blocked" and not self.active)
        control_waiting = (getattr(self.args, "same_owner_control", False) and self.goal
                           and (self.goal.get("status") == "blocked" or
                                self.goal.get("status") == "paused" and
                                getattr(self.args, "continuous", False) and
                                _paused_retained_control(self.state)) and not self.active)
        eligible_control = (control_only and control_waiting and not self.active
            and control_context_eligible(dict(self.state, goal=self.goal, stop_reason=self.stop_reason,
                stop_now=self.stop_now, checkpoint_requested=self.checkpoint_requested)))
        if (not ident or not self.controlled or
                (self.checkpoint_requested or self.stop_reason or self.stop_now) and not eligible_control
                or not self.goal or self.goal.get("status") not in {"active", "blocked", "paused"}
                or ident not in self.active and not waiting and not control_waiting):
            return
        control = self.directory / "instructions"
        sending_dir = control / "sending"
        if any(sending_dir.glob("*.json")):
            return  # An uncertain earlier delivery must be resolved before newer ones.
        pending = sorted(
            (control / "pending").glob("*.json"),
            key=lambda path: (datetime.fromisoformat(_read_private_json(path)["submitted_at"]),
                              path.name))
        if not pending:
            return
        if (control_only or control_waiting and not waiting and ident not in self.active) \
                and json.loads(pending[0].read_text()).get("control") is None:
            return
        sending_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
        source = pending[0]
        sending = sending_dir / source.name
        os.replace(source, sending)
        item = _read_private_json(sending)
        _validate_instruction(item.get("text"))
        receipt = {"id": item["id"], "thread_id": ident,
                   "turn_id": self.active.get(ident), "submitted_at": item["submitted_at"]}
        if item.get("control") is not None:
            self.deliver_same_owner_resume(item, receipt, sending)
            return
        try:
            progress_ack = self.register_instruction_capture_progress(item, receipt)
        except ValueError as error:
            # No RPC was attempted: archive this exact rejected item without
            # blocking a later ordinary control instruction or replaying this one.
            receipt.update(status='registration_refused_before_steer', error=str(error))
            refused = control / 'refused'
            try:
                refused.mkdir(mode=0o700, parents=True, exist_ok=True)
                archived = refused / source.name
                receipt_path = refused / (source.stem + '.receipt.json')
                if receipt_path.exists():
                    raise FileExistsError('refusal receipt already exists')
                os.link(sending, archived, follow_symlinks=False)
                atomic_json(receipt_path, receipt)  # fsync also publishes the original link.
                sending.unlink()
            except OSError as archive_error:
                receipt.update(status='registration_archive_failed_before_steer',
                               error=str(archive_error))
                self.save(last_instruction=receipt)
                self.output.notice('Registration refusal archival failed before steering; inspect ' + str(sending))
                return
            self.save(last_instruction=receipt)
            self.output.notice('Capture registration refused before steering; original and receipt at ' + str(refused))
            return
        except OSError as error:
            receipt.update(status='registration_persistence_failed_before_steer', error=str(error))
            self.save(last_instruction=receipt)
            self.output.notice('Capture registration persistence failed before steering; retained instruction at ' + str(sending))
            return  # No RPC attempted; retain uncertain persistence evidence without replay.
        try:
            message = "Live user instruction " + item["id"] + ":\n" + item["text"] + progress_ack
            if waiting:
                if (self.stop_reason or self.stop_now or self.checkpoint_requested or self.active
                        or not self.goal or self.goal.get("status") != "blocked"):
                    os.replace(sending, source)
                    return
                started = self.rpc.call("turn/start", {"threadId": ident,
                    "input": [{"type": "text", "text": message}]})
                receipt["turn_id"] = self.remember_started_turn(ident, started["turn"])
            else:
                self.rpc.call("turn/steer", {"threadId": ident,
                              "expectedTurnId": receipt["turn_id"], "input": [{"type": "text",
                              "text": message}]})
            receipt.update(status="accepted_by_server", delivered_at=utc())
            delivered = control / "delivered"
            delivered.mkdir(mode=0o700, parents=True, exist_ok=True)
            atomic_json(delivered / source.name, receipt)
            sending.unlink()
            self.save(last_instruction=receipt)
            self.output.notice("Delivered live instruction " + item["id"] + " to the coordinator.")
        except Exception as error:
            # A timeout may mean the server accepted the steer. Never silently
            # retry a potentially non-idempotent user instruction.
            receipt.update(status="delivery_uncertain", error=str(error))
            fields = {"last_instruction": receipt, "transport_uncertain": {"at": utc(),
                      "method": "turn/start" if waiting else "turn/steer", "error": str(error),
                      "reason": "instruction_delivery_uncertain"}}
            failure = self.transport_error_record(error)
            if failure is not None:
                fields["transport_failure"] = failure
            self.save(**fields)
            self.stop_reason = self.stop_reason or "rpc_delivery_uncertain"
            self.stop_now = True
            self.output.notice("Instruction delivery uncertain; inspect " + str(sending))

    def on_signal(self, signum, frame):
        self.state.pop("credit_timeout_shutdown_pause", None)
        self.state.pop("credit_timeout_startup", None)
        self.state.pop("transport_shutdown_pause", None)
        self.state.pop("transport_startup", None)
        if (self.stop_reason or "").startswith("signal_"):
            self.stop_now = True
        # Signals retain stop authority even if a retryable error arrived first.
        self.stop_reason = "signal_" + str(signum)

    def on_watchdog(self, signum, frame):
        from os_goal_guard_protocol import checkpoint_request
        request = checkpoint_request(self.directory, self.state)
        if request is not None:
            if not self.stop_reason and not self.stop_now:
                self.save(guardian_checkpoint_request=request)
                self.stop_reason = "guardian_recovery"
            return
        from watch_os_goal import watchdog_requested
        if not watchdog_requested(self.directory, os.getpid()):
            self.on_signal(signum, frame)
            return
        if not self.stop_reason and not self.stop_now:
            self.stop_reason = "watchdog_recovery"

    def remember_goal(self, goal):
        self.goal = goal
        fields = {"goal": goal}
        if (isinstance(goal, dict) and goal.get("status") == "active"
                and self.state.get("phase") in {"waiting_for_input", "repair_review"}
                and not self.stop_reason and not self.stop_now and not self.checkpoint_requested):
            fields.update(phase="running", waiting_reason=None)
        self.save(**fields)

    def remember_child_provenance(self, data):
        """Only an observed direct-child activity in the current root turn qualifies."""
        root = self.state.get("thread_id")
        item = data.get("item") or {}
        child, path = item.get("agentThreadId"), item.get("agentPath")
        if (not root or data.get("threadId") != root or
                not self.active.get(root) or data.get("turnId") != self.active[root] or
                item.get("type") != "subAgentActivity" or
                item.get("kind") not in {"started", "interacted"} or
                not isinstance(child, str) or not 0 < len(child) <= 128 or child == root or
                not isinstance(path, str) or not path.startswith("/root/") or
                len(path.split("/")) != 3 or path.split("/")[-1] in {"", ".", ".."}):
            return
        # No provenance is restored from last run's renderer/state snapshots.
        if child in self.capacity_children or len(self.capacity_children) < 64:
            self.capacity_children[child] = root

    def record_child_capacity(self, error, reason, thread_id, turn_id):
        """Record a scoped capacity failure; never retry or call RPC from events."""
        root = self.state.get("thread_id")
        if (not isinstance(error, dict) or error.get("codexErrorInfo") != "serverOverloaded" or
                not isinstance(thread_id, str) or thread_id == root or
                self.capacity_children.get(thread_id) != root or
                not isinstance(turn_id, str) or not 0 < len(turn_id) <= 128):
            return False
        rows = self.child_capacity_failures
        prior = next((row for row in rows if row["thread_id"] == thread_id and
                      row["turn_id"] == turn_id), None)
        if self.active.get(thread_id) != turn_id and prior is None:
            return False
        healthy = (self.controlled and self.goal and self.goal.get("status") == "active"
                   and root in self.active and not self.stopping)
        held = (self.stop_reason or self.stop_now or self.checkpoint_requested or
                self.state.get("last_error") is not None or
                self.state.get("last_failure") is not None or
                (self.goal and self.goal.get("status") in TERMINAL_CODES))
        if not healthy and not held:
            return False
        # A late child event must not replace a fatal error, policy hold or user stop.
        # Original error bytes remain in RPC's existing protocol log.
        if prior is None:
            row = {"thread_id": thread_id, "turn_id": turn_id,
                   "codexErrorInfo": "serverOverloaded", "reason": reason,
                   "message": str(error.get("message", ""))[:2048],
                   "recorded_at": utc(), "retry_not_before_unix": time.time() + 60,
                   "automatic_retry": False, "events": [reason]}
            rows.append(row)
            del rows[:-16]
            self.output.notice("Child capacity unavailable: " + thread_id + "/" + turn_id +
                               "; preserve work; coordinator may follow up after backoff.")
        elif reason not in prior["events"]:
            prior["events"].append(reason)
        self.save(child_capacity_failures=list(rows))
        return True

    def record_failure(self, error, reason, will_retry=False, *, thread_id=None, turn_id=None):
        transient = classify_service_failure(error)
        prior_stop = self.stop_reason
        preserve = bool(prior_stop and (prior_stop not in {
            "server_error", "turn_failed", "rate_limit"} or transient is not None))
        self.state.pop("credit_timeout_shutdown_pause", None)
        self.state.pop("credit_timeout_startup", None)
        self.state.pop("transport_shutdown_pause", None)
        self.state.pop("transport_startup", None)
        failure = {"thread_id": thread_id, "id": turn_id, "error": error,
                   "reason": reason, "log_dir": str(self.log_dir), "recorded_at": utc(),
                   "worker_pid": os.getpid(), "worker_start": self.state.get("worker_start")}
        fields = {"last_failure": failure}
        if not preserve or "last_error" not in self.state:
            fields.update(last_error=error, last_error_provenance={
                key: failure[key] for key in
                ("error", "log_dir", "worker_pid", "worker_start", "recorded_at")})
        self.save(**fields)
        self.record_stop_diagnostic("service_failure", error=error, reason=reason)
        if preserve:
            # A late server error must not turn a requested stop into recovery.
            return
        info = (error or {}).get("codexErrorInfo")
        if isinstance(info, str) and info in LIMIT_ERRORS:
            self.stop_reason, self.stop_now = "quota_exhausted", True
        elif self.stop_reason != "quota_exhausted" and not will_retry:
            self.stop_reason = "rate_limit" if info == "rateLimitExceeded" else reason
            self.stop_now = True
            if (transient is not None and reason in {"server_error", "turn_failed", "rate_limit"}
                    and not self.state.get("transport_uncertain")
                    and not any(self.state.get(key) for key in
                                ("service_hold", "policy_hold", "auth_hold", "billing_hold"))):
                failure = {"schema_version": 1, "worker_pid": os.getpid(),
                    "worker_start": self.state.get("worker_start"),
                    "thread_id": self.state.get("thread_id"), "class": "service_transient",
                    "error": json.dumps(error, sort_keys=True, separators=(",", ":")),
                    "error_type": "ServiceTransient", "service_error": error,
                    "method": None, "mutating": False, "channel_unusable": False}
                self.save(transport_failure=failure)
                expected = (getattr(self.args, "recovery_goal_sha256", None) or
                            getattr(self.args, "credit_timeout_goal_sha256", None))
                active = getattr(self.args, "recovery_require_active", False)
                if not self.controlled and (expected or active):
                    from watch_os_goal import process_start
                    self.save(transport_startup={"schema_version": 1, "worker_pid": os.getpid(),
                        "worker_start": self.state.get("worker_start"), "watcher_pid": os.getppid(),
                        "watcher_start": process_start(os.getppid()), "thread_id": self.state.get("thread_id"),
                        "before_inference": True, "expected_goal_sha256": expected,
                        "require_active": active, "class": "service_transient",
                        "error": failure["error"], "method": None})

    def publish_account_control_observation(self, context):
        """Publish opt-in control evidence without granting execution ACCEPTED."""
        if not getattr(self.args, "same_owner_control", False):
            return
        observed = dict(context, context="same_owner_control", execution_authorized=False,
                        status="REJECTED")
        try:
            from os_goal_guard_protocol import read_json
            current_receipt = getattr(self, "current_control_receipt", None)
            view = dict(self.state, goal=self.goal, stop_reason=self.stop_reason,
                        stop_now=self.stop_now, checkpoint_requested=self.checkpoint_requested)
            if (not control_context_eligible(view, current_receipt=current_receipt)
                    or self.credit_guard is None or self.rpc.proc.pid != self.state.get("server_pid")
                    or os.getpid() != self.state.get("worker_pid")):
                raise ValueError("account control original owner stopped or unavailable")
            saved = read_json(self.state_path)
            owner = _account_control_owner(saved, self.directory, self.repo)
            if (owner["credit_run_id"] != self.credit_guard.identifier
                    or amount(owner["credit_budget"]) != self.credit_guard.budget
                    or owner["credit_ledger_path"] != str(self.credit_guard.path)):
                raise ValueError("account control original ledger mismatch")
            ledger = read_json(self.credit_guard.path)
            observed.update(status="OBSERVED", owner=owner,
                            credit_record_sha256=_account_value_sha256(ledger),
                            state_limits_and_credit_persisted=True)
            observed_account_control(dict(saved, last_account_control_observation=observed),
                                     ledger, owner, time.time_ns(), time.monotonic_ns(),
                                     current_receipt=current_receipt)
        except (OSError, ValueError, TypeError, AttributeError, KeyError, InvalidOperation) as error:
            observed.update(status="REJECTED", reason=str(error))
        self.save(last_account_control_observation=observed)

    def record_rate_limits(self, limits, *, notification=False,
                           read_completion=None):
        context = None
        if self.rpc is not None:
            if notification:
                context = getattr(self.rpc, "last_account_notification", None)
            elif read_completion is getattr(self.rpc, "last_account_read_completion", None):
                context = read_completion
        previous = self.state.get("last_account_observation")
        previous_control = self.state.get("last_account_control_observation")
        previous_limits = self.state.get("last_rate_limits")
        order = lambda item: (item["received_mono_ns"], item["sequence"])
        late_read = (context is not None and previous is not None
                     and order(context) < order(previous))
        if context is not None:
            if context.get("rate_limits_sha256") != _account_value_sha256(limits):
                raise ValueError("account receive payload mismatch")
            context = dict(context, status="PENDING")
            if not late_read:
                fields = {"last_account_observation": context}
                if notification:
                    fields["last_account_notification"] = context
                if getattr(self.args, "same_owner_control", False):
                    fields["last_account_control_observation"] = dict(
                        context, context="same_owner_control", execution_authorized=False)
                self.save(**fields)
        # Original accounting, including the original durable ledger and all
        # real holds.  Even a late read remains conservatively accounted.
        self._record_rate_limits_accounting(limits, notification=notification)
        if context is None:
            return
        if late_read:
            # pump() can consume a newer notification before call() returns an
            # older read.  Restore its actual limits, never its freshness clock.
            # Re-observe through the SAME conservative cumulative ledger: an
            # upward snapshot never refunds allowance or clears any real hold.
            if _account_value_sha256(previous_limits) != previous.get("rate_limits_sha256"):
                raise ValueError("newer account observation payload mismatch")
            self.save(last_rate_limits=previous_limits)
            context = dict(previous, status="PENDING")
            if not self.stop_reason and not self.stop_now and (
                    previous.get("status") == "ACCEPTED" or (
                        getattr(self.args, "same_owner_control", False)
                        and (previous.get("status") == "PENDING" or
                             previous.get("status") == "REJECTED"
                             and control_context_eligible(dict(self.state, goal=self.goal,
                                 stop_reason=self.stop_reason, stop_now=self.stop_now,
                                 checkpoint_requested=self.checkpoint_requested)))
                        and isinstance(previous_control, dict)
                        and previous_control.get("status") == "OBSERVED"
                        and order(previous_control) == order(previous))):
                self._record_rate_limits_accounting(previous_limits, notification=False)
            else:
                rejected = dict(context, status="REJECTED")
                fields = {"last_account_observation": rejected}
                if context.get("source") == "notification":
                    fields["last_account_notification"] = rejected
                self.save(**fields)
                self.publish_account_control_observation(rejected)
                return
        newest = self.state.get("last_account_observation")
        if newest is None or order(newest) != order(context):
            return
        publish_notification = context.get("source") == "notification"
        if self.stop_reason or self.stop_now or self.credit_guard is None \
                or self.state.get("credit_budget_error"):
            rejected = dict(context, status="REJECTED")
            fields = {"last_account_observation": rejected}
            if publish_notification:
                fields["last_account_notification"] = rejected
            self.save(**fields)
            self.publish_account_control_observation(rejected)
            return
        self.publish_account_control_observation(context)
        # Starting/paused/blocked workers still use the original accounting.
        # Only the actual running saved-goal owner can publish this new receipt.
        if self.state.get("phase") != "running" \
                or (self.state.get("goal") or {}).get("status") != "active":
            return
        saved = json.loads(self.state_path.read_text())
        ledger = json.loads(self.credit_guard.path.read_text())
        if saved.get("last_rate_limits") != self.state.get("last_rate_limits") \
                or saved.get("credit_budget") != ledger:
            raise ValueError("account durable publication mismatch")
        def birth(pid):
            raw = Path("/proc/%d/stat" % pid).read_text()
            return raw.rsplit(")", 1)[1].split()[19]
        worker_pid = os.getpid()
        server_pid = self.rpc.proc.pid
        owner = {
            "boot_id": Path("/proc/sys/kernel/random/boot_id").read_text().strip(),
            "repo": str(self.repo), "guardian_run_id": self.state.get("guardian_run_id"),
            "log_dir": str(self.log_dir), "thread_id": self.state.get("thread_id"),
            "goal_objective_sha256": _account_value_sha256(
                (self.state.get("goal") or {}).get("objective")),
            "worker_pid": worker_pid, "worker_start": birth(worker_pid),
            "server_pid": server_pid, "server_start": birth(server_pid),
            "credit_run_id": self.credit_guard.identifier,
            "credit_budget": str(self.credit_guard.budget),
            "credit_ledger_path": str(self.credit_guard.path),
        }
        accepted = dict(context, status="ACCEPTED", owner=owner,
                        credit_record_sha256=_account_value_sha256(ledger),
                        state_limits_and_credit_persisted=True)
        trial = dict(saved, last_account_observation=accepted)
        if publish_notification:
            trial["last_account_notification"] = accepted
        else:
            trial["successful_account_read"] = accepted
        accepted_account_observation(trial, ledger, owner,
                                     time.time_ns(), time.monotonic_ns())
        fields = {"last_account_observation": accepted}
        if publish_notification:
            fields["last_account_notification"] = accepted
        else:
            fields["successful_account_read"] = accepted
        self.save(**fields)

    def _record_rate_limits_accounting(self, limits, *, notification=False):
        if notification:
            self.last_credit_notification = None
        previous = self.state.get("last_rate_limits") or {}
        self.save(last_rate_limits=limits)
        if self.stop_reason and not control_context_eligible(dict(
                self.state, goal=self.goal, stop_reason=self.stop_reason,
                stop_now=self.stop_now, checkpoint_requested=self.checkpoint_requested),
                current_receipt=getattr(self, "current_control_receipt", None)):
            return
        primary = (limits or {}).get("primary") or {}
        used = primary.get("usedPercent")
        if (not isinstance(used, (int, float)) or isinstance(used, bool) or
                not math.isfinite(used) or not 0 <= used <= 100):
            self.stop_reason, self.stop_now = "included_usage_unknown", True
        elif self.credit_guard is not None:
            try:
                record, exhausted = self.credit_guard.observe(limits)
                self.save(credit_budget=record, credit_budget_error=None)
                if exhausted:
                    self.stop_reason, self.stop_now = "credit_budget_exhausted", True
                elif notification:
                    # observe() persisted the existing run/budget before freshness is granted.
                    self.last_credit_notification = (self.rpc, time.monotonic())
            except (OSError, ValueError, TypeError, InvalidOperation) as error:
                self.save(credit_budget_error=str(error))
                self.stop_reason, self.stop_now = "credit_budget_unknown", True
        elif used >= INCLUDED_USAGE_STOP_PERCENT:
            # Use the full included allowance; service, billing and auth stops still win.
            self.stop_reason, self.stop_now = "included_usage_guard", True
        else:
            old_balance = (previous.get("credits") or {}).get("balance")
            new_balance = ((limits or {}).get("credits") or {}).get("balance")
            if old_balance is not None and new_balance is not None:
                try:
                    if Decimal(str(new_balance)) < Decimal(str(old_balance)):
                        self.stop_reason, self.stop_now = "credit_balance_decreased", True
                except InvalidOperation:
                    self.stop_reason, self.stop_now = "credit_balance_unknown", True
        if self.stop_reason:
            self.output.notice("Usage/billing stop: " + self.stop_reason)

    def refresh_credit_budget(self, *, control_only=False):
        """Poll without inference; only freshly persisted notifications cover transport failure."""
        def may_read():
            return ((not self.stop_reason and not self.stop_now)
                    or control_only and control_context_eligible(dict(
                        self.state, goal=self.goal, stop_reason=self.stop_reason,
                        stop_now=self.stop_now, checkpoint_requested=self.checkpoint_requested),
                        current_receipt=getattr(self, "current_control_receipt", None)))

        for attempt in range(3):
            if not may_read():
                return
            try:
                try:
                    result = self.rpc.call("account/rateLimits/read", {}, timeout=10)
                except (RecoverableFailure, BrokenPipeError, ConnectionResetError) as error:
                    label = ("broken_pipe" if isinstance(error, BrokenPipeError) else
                             "connection_reset" if isinstance(error, ConnectionResetError) else
                             "disconnected" if str(error) ==
                             "Codex app server disconnected; see retained stderr." else None)
                    if (label is None or getattr(error, "rpc_mutating", False)
                            or getattr(error, "rpc_method", "account/rateLimits/read") !=
                            "account/rateLimits/read"):
                        raise
                    failure = self.transport_error_record(error)
                    failure.update(method="account/rateLimits/read", mutating=False, channel_unusable=True)
                    self.save(transport_failure=failure)
                    self.save(last_usage_transport_error={"at": utc(), "error": str(error),
                              "error_type": type(error).__name__, "method": "account/rateLimits/read"})
                    raise RecoverableFailure("Local account/rateLimits/read transport: " + label) from error
                prior = self.state.get("transport_failure") or {}
                if prior.get("method") == "account/rateLimits/read" and prior.get("channel_unusable"):
                    self.save(transport_failure=None)
                self.record_rate_limits(
                    result.get("rateLimits"), read_completion=getattr(
                        self.rpc, "last_account_read_completion", None))
                return
            except Exception as error:
                completion = getattr(self.rpc, "last_account_read_completion", None)
                if isinstance(completion, dict) and completion.get("response_error"):
                    previous = self.state.get("last_account_observation")
                    order = lambda item: (item["received_mono_ns"], item["sequence"])
                    if previous is None or order(completion) >= order(previous):
                        self.save(last_account_observation=dict(completion, status="REJECTED"))
                if getattr(error, "rpc_mutating", False):
                    self.save(transport_uncertain={"at": utc(), "method": error.rpc_method,
                              "error": str(error), "reason": "nested_mutating_rpc_delivery_uncertain"})
                    self.stop_reason = self.stop_reason or "rpc_delivery_uncertain"
                    self.stop_now = True
                    return
                if not may_read():
                    self.save(last_usage_read_error_after_stop={"at": utc(), "error": str(error)})
                    return
                failure = (classify_usage_failure(str(error))
                           if isinstance(error, RuntimeError) else None)
                observed = self.last_credit_notification
                age = time.monotonic() - observed[1] if observed is not None else None
                if (failure is not None
                        and self.credit_guard is not None and observed is not None
                        and observed[0] is self.rpc and age is not None
                        and 0 <= age <= CREDIT_NOTIFICATION_MAX_AGE_SECONDS
                        and may_read()
                        and self.state.get("credit_budget_error") is None):
                    self.save(last_usage_read_notification_fallback={
                        "at": utc(), "age_seconds": age, "error": str(error),
                        "failure_class": failure, "source": "same_worker_server_validated_persisted_notification"})
                    self.output.notice("Usage read transport failed; current validated notification "
                                       "already persisted the unchanged credit guard.")
                    return
                if (attempt < 2 and may_read()
                        and temporary_usage_read_failure(error)):
                    self.save(last_usage_read_retry={"at": utc(), "attempt": attempt + 1,
                                                    "error": str(error)})
                    self.output.notice("Usage reporting temporarily unavailable; retrying read-only balance check "
                                       + str(attempt + 1) + "/2.")
                    time.sleep(attempt + 1)
                    continue
                expected = getattr(self.args, "credit_timeout_goal_sha256", None)
                if (failure is not None
                        and self.credit_guard is not None and expected
                        and not self.controlled and not self.stop_reason
                        and not self.stop_now and self.state.get("phase") == "starting"
                        and self.state.get("auth_mode") == "chatgpt"
                        and (self.state.get("goal") or {}).get("status") == "paused"
                        and hashlib.sha256(json.dumps(self.state["goal"], sort_keys=True,
                            separators=(",", ":")).encode()).hexdigest() == expected):
                    from watch_os_goal import process_start
                    self.save(credit_timeout_startup={"schema_version": 1,
                        "worker_pid": os.getpid(), "worker_start": self.state.get("worker_start"),
                        "watcher_pid": os.getppid(), "watcher_start": process_start(os.getppid()),
                        "thread_id": self.state.get("thread_id"), "before_inference": True,
                        "account_validated": True, "expected_goal_sha256": expected,
                        "phase_at_failure": "starting"})
                generic_expected = getattr(self.args, "recovery_goal_sha256", None)
                require_active = getattr(self.args, "recovery_require_active", False)
                if (failure is not None and self.credit_guard is not None and not self.controlled
                        and not self.stop_reason and not self.stop_now
                        and self.state.get("phase") == "starting"
                        and (generic_expected or require_active)):
                    from watch_os_goal import process_start
                    self.save(transport_startup={"schema_version": 1, "worker_pid": os.getpid(),
                        "worker_start": self.state.get("worker_start"), "watcher_pid": os.getppid(),
                        "watcher_start": process_start(os.getppid()), "thread_id": self.state.get("thread_id"),
                        "before_inference": True, "expected_goal_sha256": generic_expected,
                        "require_active": require_active, "class": failure,
                        "error": str(error), "method": "account/rateLimits/read"})
                self.save(credit_budget_error=str(error))
                self.stop_reason = ("credit_budget_unknown" if control_only
                    and self.stop_reason in TECHNICAL_CONTROL_STOPS else
                    self.stop_reason or "credit_budget_unknown")
                self.stop_now = True
                return

    def event(self, message):
        method, data = message.get("method"), message.get("params", {})
        self.output.event(message)
        thread = data.get("threadId")
        primary = thread == self.state.get("thread_id")
        if primary and method in {"thread/goal/updated", "thread/goal/cleared"}:
            self.state.pop("credit_timeout_shutdown_pause", None)
            self.state.pop("credit_timeout_startup", None)
            self.state.pop("transport_shutdown_pause", None)
            self.state.pop("transport_startup", None)
        if method in {"item/started", "item/completed"}:
            self.remember_child_provenance(data)
        if "id" in message:
            if method == USER_INPUT_METHOD:
                self.save(last_automatic_input={"thread_id": thread, "request_id": message["id"],
                          "question_ids": [q["id"] for q in data["questions"]],
                          "policy": "standing_autonomy_instruction; no new human answer"})
                return
            self.save(pending_request={"method": method, "params": data})
            self.stop_reason, self.stop_now = "needs_user_input", True
        elif method == "thread/goal/updated" and primary:
            if data["goal"]["status"] in {"paused", "blocked"}:
                self.primary_stop_generation += 1
            self.remember_goal(data["goal"])
        elif method == "thread/goal/cleared" and primary:
            self.goal = None
            self.stop_reason, self.stop_now = "goal_cleared", True
        elif method == "turn/started":
            self.active[thread] = data["turn"]["id"]
            self.last_activity = time.monotonic()
            self.save()
        elif method == "turn/completed":
            isolated = (data["turn"]["status"] == "failed" and
                        self.record_child_capacity(data["turn"].get("error"), "turn_failed",
                                                   thread, data["turn"]["id"]))
            if self.active.get(thread) == data["turn"]["id"]:
                self.active.pop(thread, None)
            self.last_activity = time.monotonic()
            self.save(last_turn={"thread_id": thread, "id": data["turn"]["id"],
                                 "status": data["turn"]["status"]})
            if data["turn"]["status"] == "failed" and not isolated:
                self.record_failure(data["turn"].get("error"), "turn_failed",
                                    thread_id=thread, turn_id=data["turn"]["id"])
        elif method == "error":
            turn = data.get("turnId")
            if not self.record_child_capacity(data["error"], "server_error", thread, turn):
                self.record_failure(data["error"], "server_error", data.get("willRetry", False),
                                    thread_id=thread, turn_id=turn or self.active.get(thread))
        elif method == "account/rateLimits/updated":
            self.record_rate_limits(data.get("rateLimits"), notification=True)
        elif method == "account/updated" and data.get("authMode") not in (None, "chatgpt"):
            self.stop_reason, self.stop_now = "chatgpt_auth_changed", True
        elif method == "item/agentMessage/delta" and primary:
            # Preserve the existing dispatcher-only transcript for older consumers.
            excerpt = data.get("delta", "")
            with (self.log_dir / "dispatcher.txt").open("a") as stream:
                stream.write(excerpt)

    def instructions(self):
        """One human-readable campaign entrypoint; runtime guards stay separate."""
        prefix = (("Current user instruction for this invocation, loaded before session activation:\n"
                   + self.args.startup_instruction + "\nEnd current invocation instruction.\n")
                  if getattr(self.args, "startup_instruction", None) else "")
        usage = (
            "This invocation uses up to " + self.args.credit_budget +
            " existing prepaid credits under its explicit guard. Never change "
            "its budget/run identifier, buy credits, use API-key billing, or bypass a real hold. "
            if getattr(self.args, "credit_budget", None) is not None else
            "Included weekly usage only; stop at 100% or an earlier actual hold, unknown "
            "usage or inherited cutoff. No prepaid/API fallback and no new allowance at reset. "
        )
        window = ("This invocation has a finite work window. " if self.args.hours else
                  "This invocation has no time limit beyond its actual usage and inherited controls. ")
        repair = repair_instruction() if getattr(self.args, "repair_agent_failures", False) else ""
        milestones = ("This invocation targets original M14 and M15 acceptance only. "
                      "Prepare independent eligible work in parallel, accept M14 before M15, "
                      "and checkpoint when BOTH original milestones are accepted. Do not "
                      "mark the larger saved whole-system goal complete at that point. "
                      if getattr(self.args, "stop_after_m14_m15", False) else "")
        return (
            prefix + repair + milestones + ENGINEERING_SCOPE +
            "Read CAMPAIGN.md as the SOLE human-readable plan, status and handoff. Do not read "
            "legacy narrative logs or follow their reading lists. This replaces the old reading "
            "order in the retained goal identity and archived conversation. On fresh/recovered "
            "sessions use this same one-file entrypoint. Current source, build definitions, "
            "artifacts and necessary live machine controls still require exact validation; "
            "they are not additional narrative context. Reconcile source changes, live "
            "identities, leases and any in-flight outcome before execution. "
            "Adopt this sole policy hash: " + json.dumps(policy_hashes(self.repo), sort_keys=True) + ". "
            + usage + window +
            "An explicit user pause remains authoritative; never auto-resume it or replace it "
            "with an older continuous-run instruction. A normal checkpoint alone is not a pause. "
            "Keep original M14 FINAL acceptance before M15 FINAL acceptance, then complete-system "
            "delivery with existing Rocky/Linux support, as specified in CAMPAIGN.md. Prepare "
            "eligible independent M14 and M15 source, tests and focused reviews in parallel; "
            "retain every genuine operation-specific source, account, ownership and resource hold. "
            "Keep four accepted M14 files and the accepted M15 file closed at their exact scope. "
            "No source/typecheck/mock result alone retires C or accepts an image. "
            "Dispatcher model/effort and separate worker routing: "
            + json.dumps(model_routing(self.args), sort_keys=True) + ". "
            "The user requires GPT-6.1 Sol/max for the dispatcher; do not silently downgrade it. "
            "Use authorized danger-full-access and approval never; confirm actual permissions "
            "once for every recovered/new thread. Full access is not Unix root. Use existing "
            "sudo -A/askpass only within actual execution admission; never read or log the "
            "credential, call its helper directly, or expose it in commands/environment. "
            + resource_instructions(launch_resources(self.args, self.repo)) + " " +
            "Cached resource settings are planning only; every actual job requires fresh aggregate "
            "admission including original retained charges, measured overhead and current floors. "
            "Preserve service/account/source holds, rejected-request exclusions, failed evidence, "
            "historical ledger, native owners, scratch21 and UNKNOWN reservations. Do not replay "
            "an old nonce or infer native retirement from model/process recovery. Do not edit "
            "launcher-owned state, clear this goal, reset budgets or arm competing controllers. "
            "Use followup_task for actual deliverables, including completed/idle owners; verify "
            "a new turn once. Keep disjoint private writers and one compositor. Feed ready "
            "eligible bodies to the existing ordinary compiler queue independently of native "
            "setup; reuse matching SDKs, objects and accepted checks. Root/native work retains "
            "its reviewed operation-specific execution, ownership and resource release. "
            "Carry each failure family: one failed candidate and one bounded correction, then "
            "focused escalation. No repeated unchanged failures, broad audits, inventories or "
            "new control frameworks without a concrete blocking defect. "
            "Update only CAMPAIGN.md for human status: real implementation/build/link/native/C "
            "retirement delta, one blocker/owner and one next action. Keep required raw machine "
            "evidence separate without expanding narrative context. Push coherent checkpoints "
            "through the existing wrapper and verify fetched commits/blobs. Preserve dirty work. "
            "On a user checkpoint/break request stop new dispatch, finish only bounded in-flight "
            "work, retain UNKNOWN owners, checkpoint, pause through the normal goal tool and return."
        )

    def recovery_goal_allowed(self, goal):
        """Validate live saved context before resume or fresh-session activation."""
        expected = getattr(self.args, "recovery_goal_sha256", None)
        active = getattr(self.args, "recovery_require_active", False)
        if not expected and not active:
            return True
        valid = (isinstance(goal, dict) and goal.get("objective") == OBJECTIVE
                 and goal.get("threadId", self.state.get("thread_id") or
                              (self.state.get("previous_session") or {}).get("thread_id")) ==
                 (self.state.get("thread_id") or (self.state.get("previous_session") or {}).get("thread_id")))
        if expected:
            valid = valid and goal.get("status") == "paused" and hashlib.sha256(json.dumps(
                goal, sort_keys=True, separators=(",", ":")).encode()).hexdigest() == expected
        if active:
            valid = valid and goal.get("status") == "active"
        if not valid:
            self.remember_goal(goal)
            self.stop_reason, self.stop_now = "startup_goal_stopped", True
        return bool(valid)

    def prepare_fresh_goal(self):
        """Read only predecessor metadata, pause active continuations, retain allowance."""
        previous = self.state.get("previous_session")
        if not previous or self.state.get("thread_id"):
            return True
        from os_goal_sessions import validate_prepared_fresh_session
        validate_prepared_fresh_session(self.directory, self.repo, self.state, expected_objective=OBJECTIVE)
        if not isinstance(previous, dict) or not isinstance(previous.get("thread_id"), str):
            raise RuntimeError("Fresh session has no valid predecessor identity")
        ident = previous["thread_id"]
        goal = self.rpc.call("thread/goal/get", {"threadId": ident})["goal"]

        def validate(value):
            if (not isinstance(value, dict) or value.get("objective") != OBJECTIVE
                    or value.get("status") not in {"active", "paused", "blocked", "complete",
                                                   "usageLimited", "budgetLimited"}):
                raise RuntimeError("Archived thread goal is missing, changed, or unsupported; no new thread was started")

        validate(goal)
        if self.args.recovered and not (getattr(self.args, "recovery_goal_sha256", None)
                                        or getattr(self.args, "recovery_require_active", False)):
            raise RuntimeError("Automatic fresh recovery lacks live predecessor goal provenance")
        if not self.recovery_goal_allowed(goal):
            return False
        if goal["status"] in {"complete", "usageLimited", "budgetLimited"}:
            self.remember_goal(goal)
            return False
        if goal["status"] == "active":
            goal = self.rpc.call("thread/goal/set", {"threadId": ident, "status": "paused"})["goal"]
            validate(goal)
            if goal["status"] != "paused":
                raise RuntimeError("Previous goal did not pause; no new thread was started")
        page = self.rpc.call("thread/turns/list", {
            "threadId": ident, "limit": 1, "sortDirection": "desc", "itemsView": "notLoaded"})
        if any(turn.get("status") == "inProgress" for turn in page["data"]):
            raise RuntimeError("Previous conversation still has an active turn; no new thread was started")
        # Goal pausing stops future continuations. Observe turn retirement and
        # then refresh usage so the new allowance includes the final old turn.
        goal = self.rpc.call("thread/goal/get", {"threadId": ident})["goal"]
        validate(goal)
        if goal["status"] in {"complete", "usageLimited", "budgetLimited"}:
            self.remember_goal(goal)
            return False
        if goal["status"] == "active":
            raise RuntimeError("Previous goal became active again; no new thread was started")
        budget, used = goal.get("tokenBudget"), goal.get("tokensUsed")
        if budget is not None and (type(budget) is not int or budget <= 0
                or type(used) is not int or used < 0):
            raise RuntimeError("Previous goal has an invalid token allowance; no new thread was started")
        remaining = None if budget is None else max(0, budget - used)
        saved = self.state.get("fresh_token_budget")
        if saved is not None and (type(saved) is not int or saved < 0):
            raise RuntimeError("Saved fresh token allowance is invalid")
        caps = [value for value in (remaining, saved, self.args.token_budget) if value is not None]
        allowance = min(caps) if caps else None
        # Retain this before thread/start so a crash before goal/set cannot
        # silently replace the bounded remainder with the original CLI budget.
        self.save(fresh_token_budget=allowance)
        if allowance == 0:
            self.stop_reason, self.stop_now = "budget_exhausted", True
            self.remember_goal(goal)
            return False
        return True

    def manual_resume_instruction(self, note):
        previous = (self.state.get("last_instruction") or {}).get("id", "not recorded")
        failure = self.prior_policy_failure
        exclusion = ("\nPreserved policy rejection: thread=" +
                     str(failure.get("thread_id") or self.state.get("thread_id", "unknown")) +
                     "; turn=" + str(failure.get("id", "unknown")) + ". "
                     "That task remains excluded from replay or reassignment. A scope "
                     "statement is not service/account clearance.\n" if failure is not None else "")
        return (
            "EXPLICIT USER RESUME — new manual launcher invocation " + self.log_dir.name + ".\n"
            "The user has invoked the launcher NOW to resume unfinished functional OS and "
            "Rust/assembly development. This is a NEW resume instruction: it supersedes "
            "earlier user stop/pause requests and PAUSED handoff banners from preceding "
            "invocations. Do not answer that the earlier pause is still in force or wait "
            "for another resume instruction. Begin the next authorized engineering task.\n"
            "Preserved prior instruction reference: " + previous + ".\n"
            "A new stop received during or after this invocation remains authoritative. "
            "Preserve signal, quota and selected included/credit budget, billing, ownership/resource and service "
            "controls; do not replay rejected work or expired execution releases. "
            "The launcher's automatic recovery does not issue this manual authorization.\n"
            + ENGINEERING_SCOPE + exclusion +
            (("Current invocation scope and execution instructions:\n" + note) if note else "")
        )

    def begin(self):
        # Admission failures belong to this worker, never the preceding retry.
        if self.state.get("transport_uncertain"):
            raise RuntimeError("Mutating RPC delivery is uncertain; reconcile before recovery")
        if (getattr(self.args, "credit_timeout_goal_sha256", None)
                or getattr(self.args, "recovery_goal_sha256", None)
                or getattr(self.args, "recovery_require_active", False)) and not (
                    self.state.get("thread_id") or (self.state.get("previous_session") or {}).get("thread_id")):
            raise RuntimeError("Automatic recovery lost its saved thread identity")
        if (self.state.get("last_instruction") or {}).get("status") == "delivery_uncertain":
            raise RuntimeError("Instruction delivery is uncertain; reconcile before recovery")
        if (self.state.get("resume_instruction") or {}).get("status") in {"sending", "delivery_uncertain"}:
            raise RuntimeError("Resume instruction delivery is uncertain; reconcile its saved turn before resuming")
        note = getattr(self.args, "startup_instruction", None)
        from watch_os_goal import process_start
        self.save(worker_pid=os.getpid(), worker_start=process_start(os.getpid()),
                  server_pid=None, server_start=None, retryable=False,
                  guardian_run_id=getattr(self.args, "guardian_run_id", None),
                  startup_instruction_sha256=hashlib.sha256(note.encode()).hexdigest() if note else None)
        check_resources(launch_resources(self.args, self.repo))
        self.rpc = self.rpc_factory(server_argv(self.args, self.repo), self.log_dir, self.event)
        if retention_required(self.args, self.rpc):
            self.rpc.owner_custody_retained = True
        proc = getattr(self.rpc, "proc", None)
        birth = None
        if proc:
            from watch_os_goal import process_start
            birth = process_start(proc.pid)
        self.save(worker_pid=os.getpid(), server_pid=proc.pid if proc else None,
                  server_start=birth, retryable=False)
        settings = preflight(self.rpc, self.args, self.repo)
        self.save(phase="starting", settings=settings, stop_reason=None)
        account = self.rpc.call("account/read", {"refreshToken": False}).get("account") or {}
        if account.get("type") != "chatgpt":
            self.stop_reason, self.stop_now = "chatgpt_auth_required", True
            self.save(auth_mode=account.get("type"))
            return
        self.save(auth_mode="chatgpt")
        if self.credit_guard is not None:
            self.refresh_credit_budget()
        else:
            self.record_rate_limits(self.rpc.call("account/rateLimits/read", {}).get("rateLimits"))
        if self.stop_reason:
            return
        bindings = getattr(self.args, "supersede_instructions", [])
        if bindings:
            # Only the launcher holding run.lock changes its own instruction
            # lifecycle. Never deliver an explicitly superseded historical hold
            # as a new user message after the campaign starts.
            receipts = reconcile_instructions(
                self.directory, bindings, hashlib.sha256(note.encode()).hexdigest(), execute=True)
            self.save(instruction_reconciliation=receipts)
        if not self.prepare_fresh_goal():
            return
        params = {"cwd": str(self.repo), "model": self.args.model, "approvalPolicy": "never",
                  "sandbox": "danger-full-access",
                  "config": {"model_reasoning_effort": self.args.effort},
                  "developerInstructions": self.instructions()}
        previous_id = self.state.get("thread_id")
        goal = None
        if previous_id:
            # Reading a stored goal does not resume a thread or start inference.
            # Validate ownership before a resume can trigger automatic goal work.
            goal = self.rpc.call("thread/goal/get", {"threadId": previous_id})["goal"]
            if goal and goal["objective"] != OBJECTIVE:
                raise RuntimeError("Stored thread has a different objective; it was not resumed or replaced.")
            if not self.recovery_goal_allowed(goal):
                return
            expected = getattr(self.args, "credit_timeout_goal_sha256", None)
            if expected and hashlib.sha256(json.dumps(
                    goal, sort_keys=True, separators=(",", ":")).encode()).hexdigest() != expected:
                self.remember_goal(goal)
                self.stop_reason, self.stop_now = "startup_goal_stopped", True
                return
            if not goal and self.state.get("goal"):
                raise RuntimeError("The saved goal was cleared outside this launcher; inspect state before starting a new campaign.")
            self.controlled = True
            if goal and (goal["status"] == "complete" or
                         goal["status"] == "usageLimited" and self.args.recovered or
                         goal["status"] == "budgetLimited" and (self.args.recovered or self.args.token_budget is None)):
                self.remember_goal(goal)
                return
            params.update(threadId=previous_id, excludeTurns=True)
            result = self.rpc.call("thread/resume", params)
        else:
            params.update(ephemeral=False, allowProviderModelFallback=False)
            result = self.rpc.call("thread/start", params)
        ident = result["thread"]["id"]
        if previous_id and ident != previous_id:
            raise RuntimeError("Resume returned a different thread; refusing to replace the cursor.")
        self.save(thread_id=ident, phase="ready")
        self.output.primary = ident
        self.controlled = True
        if result["model"] != self.args.model or result.get("reasoningEffort") != self.args.effort:
            raise RuntimeError("Thread model/effort differs from the selected dispatcher.")
        if result.get("sandbox", {}).get("type") != "dangerFullAccess" or result.get("approvalPolicy") != "never":
            raise RuntimeError("Thread permissions differ from this authorized OS-development session.")
        self.save(effective_permissions={"sandbox": result.get("sandbox"),
                  "profile": result.get("activePermissionProfile"),
                  "approval_policy": result.get("approvalPolicy")})
        goal = self.rpc.call("thread/goal/get", {"threadId": ident})["goal"]
        if goal and goal["objective"] != OBJECTIVE:
            raise RuntimeError("Stored thread has a different objective; it was not replaced.")
        if not self.recovery_goal_allowed(goal):
            return
        expected = getattr(self.args, "credit_timeout_goal_sha256", None)
        if expected and hashlib.sha256(json.dumps(
                goal, sort_keys=True, separators=(",", ":")).encode()).hexdigest() != expected:
            self.remember_goal(goal)
            self.stop_reason, self.stop_now = "startup_goal_stopped", True
            return
        if goal and (goal["status"] == "complete" or
                     goal["status"] == "usageLimited" and self.args.recovered):
            self.remember_goal(goal)
            return
        if goal and goal["status"] == "budgetLimited" and (self.args.recovered or self.args.token_budget is None):
            self.remember_goal(goal)
            return
        if self.stop_reason:
            self.remember_goal(goal)
            return
        if goal and goal["status"] == "blocked" and self.args.recovered:
            # Recovery is not a new manual authorization. In repair mode the
            # run loop can diagnose once while preserving this blocked goal.
            self.remember_goal(goal)
            self.save(phase="waiting_for_input" if getattr(self.args, "repair_agent_failures", False) else "ready")
            return
        if previous_id and goal and goal["status"] in {"paused", "blocked"} and not self.args.recovered:
            # A fresh explicit --run is a CURRENT user instruction. Seeding it
            # once before activation fixes stale user-role history without a
            # second dispatcher or an automatic turn/start continuation loop.
            stop_generation = self.primary_stop_generation
            resume_goal = dict(goal)
            page = self.rpc.call("thread/turns/list", {
                "threadId": ident, "limit": 1, "sortDirection": "desc", "itemsView": "notLoaded"})
            if any(turn.get("status") == "inProgress" for turn in page["data"]):
                raise RuntimeError("A saved turn is still active; reconcile it before a fresh resume instruction")
            if self.stop_reason or self.stop_now:
                return
            if self.primary_stop_generation != stop_generation:
                self.stop_reason, self.stop_now = "startup_goal_stopped", True
                return
            message = self.manual_resume_instruction(note)
            message_path = self.log_dir / "manual-resume-instruction.txt"
            message_path.write_text(message)
            receipt = {"sha256": hashlib.sha256(note.encode()).hexdigest() if note else None,
                       "message_sha256": hashlib.sha256(message.encode()).hexdigest(),
                       "message_path": str(message_path), "invocation": self.log_dir.name,
                       "status": "sending"}
            self.save(resume_instruction=receipt)
            try:
                started = self.rpc.call("turn/start", {
                    "threadId": ident, "input": [{"type": "text", "text": message}]})
            except Exception as error:
                self.save(resume_instruction=dict(receipt, status="delivery_uncertain"))
                raise RuntimeError("Resume instruction delivery uncertain; reconcile the saved turn before retry") from error
            self.save(resume_instruction=dict(receipt, status="accepted_by_server", turn_id=started["turn"]["id"]))
            if self.stop_reason or self.stop_now:
                return
            # turn/start pumps asynchronous goal, signal and allowance events.
            # Never activate from the pre-message paused snapshot after a new
            # stop, terminal state, cleared goal or changed objective.
            goal = self.rpc.call("thread/goal/get", {"threadId": ident})["goal"]
            if self.stop_reason or self.stop_now:
                return
            if not goal or goal["objective"] != OBJECTIVE:
                raise RuntimeError("Saved goal changed during resume instruction; it was not recreated or replaced")
            if (self.primary_stop_generation != stop_generation or
                    goal["status"] in {"paused", "blocked"} and
                    (goal["status"], goal.get("updatedAt")) !=
                    (resume_goal["status"], resume_goal.get("updatedAt"))):
                self.remember_goal(goal)
                if goal["status"] == "blocked" and getattr(self.args, "repair_agent_failures", False):
                    self.save(phase="waiting_for_input")
                    return
                self.stop_reason, self.stop_now = "startup_goal_stopped", True
                return
            if (goal["status"] in {"complete", "usageLimited"} or
                    goal["status"] == "budgetLimited" and (self.args.recovered or self.args.token_budget is None)):
                self.remember_goal(goal)
                return
        update = {"threadId": ident, "status": "active"}
        if not goal:
            update["objective"] = OBJECTIVE
        requested_budget = self.args.token_budget
        if "fresh_token_budget" in self.state:
            allowance = self.state["fresh_token_budget"]
            if not goal:
                requested_budget = allowance
            elif self.args.recovered:
                requested_budget = None
            elif allowance is not None and requested_budget is not None:
                requested_budget = min(allowance, requested_budget)
        elif self.args.recovered and goal:
            requested_budget = None
        if requested_budget is not None:
            update["tokenBudget"] = requested_budget
        if not goal or goal["status"] != "active" or requested_budget is not None:
            # The server continues idle turns. An explicit startup message may
            # already own the first turn; activation must not start a second one.
            goal = self.rpc.call("thread/goal/set", update)["goal"]
        self.remember_goal(goal)
        self.save(phase="running")
        self.output.notice("Thread " + ident + "; " + self.args.model + "/" + self.args.effort
                           + "; resources=" + json.dumps(launch_resources(self.args, self.repo), sort_keys=True))

    def transport_error_record(self, error):
        """Keep typed transport provenance and the actual RPC delivery boundary."""
        label = ("broken_pipe" if isinstance(error, BrokenPipeError) else
                 "connection_reset" if isinstance(error, ConnectionResetError) else
                 classify_rpc_failure(str(error)) if isinstance(error, RecoverableFailure) else None)
        method = getattr(error, "rpc_method", None)
        if isinstance(error, RecoverableFailure) and str(error).startswith(
                "App-server request timed out: "):
            method = method or str(error)[len("App-server request timed out: "):]
            label = "rpc_timeout"
        if label is None:
            return None
        return {"schema_version": 1, "worker_pid": os.getpid(),
                "worker_start": self.state.get("worker_start"),
                "thread_id": self.state.get("thread_id"), "class": label,
                "error": str(error), "error_type": type(error).__name__, "method": method,
                "channel_unusable": bool(getattr(error, "rpc_send_incomplete", False) or
                                         label in {"disconnected", "broken_pipe", "connection_reset"}),
                "mutating": bool(getattr(error, "rpc_mutating", False) or
                                 method is not None and method not in READ_ONLY_RPC_METHODS)}

    def pause(self):
        ident = self.state.get("thread_id")
        if not ident or not self.controlled:
            return
        current = self.rpc.call("thread/goal/get", {"threadId": ident})["goal"]
        if current and current["objective"] != OBJECTIVE:
            self.controlled = False
            raise RuntimeError("Goal objective changed externally; launcher will not alter it.")
        receipt = None
        transport_receipt = None
        paused_active = bool(current and current["status"] == "active")
        if paused_active:
            before = dict(current)
            generation = self.primary_stop_generation
            current = self.rpc.call("thread/goal/set", {"threadId": ident, "status": "paused"})["goal"]
            if (self.stopping and not self.checkpoint_requested
                    and self.stop_reason == "credit_budget_unknown" and self.stop_now
                    and classify_usage_failure(self.state.get("credit_budget_error")) is not None
                    and current and current.get("status") == "paused"
                    and current.get("objective") == OBJECTIVE
                    and self.primary_stop_generation <= generation + 1
                    and not any(self.state.get(key) for key in
                                ("service_hold", "policy_hold", "auth_hold", "billing_hold"))):
                receipt = {"schema_version": 1, "worker_pid": os.getpid(),
                           "worker_start": self.state.get("worker_start"), "thread_id": ident,
                           "stop_reason": self.stop_reason,
                           "credit_budget_error": self.state["credit_budget_error"],
                           "pause_method": "thread/goal/set", "pause_confirmed": True,
                           "goal_before": before, "goal_after": current,
                           "goal_after_sha256": hashlib.sha256(json.dumps(
                               current, sort_keys=True, separators=(",", ":")).encode()).hexdigest()}
            failure = self.state.get("transport_failure") or {}
            if (self.stopping and not self.checkpoint_requested
                    and self.stop_reason in {"launcher_error", "active_goal_did_not_continue",
                                             "server_error", "turn_failed", "rate_limit"}
                    and failure.get("mutating") is False and failure.get("worker_pid") == os.getpid()
                    and failure.get("worker_start") == self.state.get("worker_start")
                    and failure.get("thread_id") == ident and current
                    and current.get("status") == "paused" and current.get("objective") == OBJECTIVE
                    and self.primary_stop_generation <= generation + 1
                    and not self.state.get("transport_uncertain")
                    and not any(self.state.get(key) for key in
                                ("service_hold", "policy_hold", "auth_hold", "billing_hold"))):
                transport_receipt = {"schema_version": 1, "worker_pid": os.getpid(),
                    "worker_start": self.state.get("worker_start"), "thread_id": ident,
                    "stop_reason": self.stop_reason, "transport_error": failure.get("error"),
                    "transport_class": failure.get("class"), "transport_method": failure.get("method"),
                    "pause_method": "thread/goal/set", "pause_confirmed": True,
                    "goal_before": before, "goal_after": current,
                    "goal_after_sha256": hashlib.sha256(json.dumps(
                        current, sort_keys=True, separators=(",", ":")).encode()).hexdigest()}
        self.goal = current
        fields = {"goal": current}
        if receipt is not None:
            fields["credit_timeout_shutdown_pause"] = receipt
        if transport_receipt is not None:
            fields["transport_shutdown_pause"] = transport_receipt
        self.save(**fields)
        return bool(paused_active and current and current["status"] == "paused")

    def request_checkpoint(self, reason=None):
        if reason is not None and (self.stop_reason or self.stop_now):
            return False
        paused_active = self.pause()
        if reason is not None:
            # The pause-time read may observe a newer terminal goal or stop.
            # Commit milestone checkpointing only after pausing an active goal.
            if not paused_active or self.stop_reason or self.stop_now:
                return False
            self.stop_reason = reason
        self.checkpoint_requested = True
        if retention_required(self.args, self.rpc):
            self.save(checkpoint_requested=True, checkpoint_reason=self.stop_reason,
                      checkpoint_cleanup_verified=False)
            return True
        ident = self.state["thread_id"]
        turn = self.active.get(ident)
        if turn:
            self.rpc.call("turn/steer", {"threadId": ident, "expectedTurnId": turn,
                "input": [{"type": "text", "text":
                    "The launcher is checkpointing following a signal, accepted milestone completion, "
                    "or an explicitly configured time limit; recorded reason "
                    + str(self.stop_reason or "work_window") + ". Stop new task dispatch. "
                    "Finish bounded active operations, join/close child agents, preserve "
                    "original evidence and active process identities, update CAMPAIGN.md "
                    "as the sole active plan, status and handoff with next tasks, commit/push "
                    "and verify the checkpoint, then return. "
                    "The launcher has paused future goal continuations. Do not mark the OS "
                    "complete or resume it during shutdown. A subsequent launcher "
                    "invocation authorizes continuation; this pause is not permanent."}]})
        self.output.notice("Checkpoint requested; waiting for bounded active work to finish.")
        return True

    def stop(self):
        if not self.rpc or self.stopping or not self.controlled:
            return
        self.stopping = True
        failure = self.state.get("transport_failure") or {}
        if (failure.get("channel_unusable") is True and failure.get("worker_pid") == os.getpid()
                and failure.get("worker_start") == self.state.get("worker_start")
                and failure.get("thread_id") == self.state.get("thread_id")):
            self.save(stop_errors=["Known unavailable app-server channel; no shutdown RPCs attempted"],
                      cleanup_verified=False)
            return
        errors = []
        try:
            self.pause()
        except Exception as error:
            errors.append(str(error))
            if getattr(error, "rpc_mutating", False):
                self.save(transport_uncertain={"at": utc(), "method": error.rpc_method,
                          "error": str(error), "reason": "shutdown_pause_delivery_uncertain"})
        if not self.controlled:
            self.save(stop_errors=errors, cleanup_verified=False)
            return
        # Include loaded descendants even if this client did not receive their events.
        try:
            for ident in self.rpc.call("thread/loaded/list", {})["data"]:
                page = self.rpc.call("thread/turns/list", {
                    "threadId": ident, "limit": 1, "sortDirection": "desc", "itemsView": "notLoaded"})
                for turn in page["data"]:
                    if turn["status"] == "inProgress":
                        self.active[ident] = turn["id"]
        except Exception as error:
            errors.append(str(error))
        for ident, turn in list(self.active.items()):
            try:
                self.rpc.call("turn/interrupt", {"threadId": ident, "turnId": turn}, timeout=10)
            except Exception as error:
                errors.append(str(error))
        self.save(stop_errors=errors, cleanup_verified=False)
        # Runtime cleanup is an OS evidence contract. Interruption/EOF is never
        # recorded as proof that a guest, container or retained owner was cleaned.

    def retention_failure(self, stage, error):
        """Bound diagnostics even if a multiday monitor repeatedly loses I/O."""
        row = retention_error(stage, error)
        if not self.retention_errors or self.retention_errors[-1] != row:
            self.retention_errors.append(row)
            del self.retention_errors[:-16]

    def retain_owner(self, reason):
        """Latch custody before any fallible pause, publication or monitoring."""
        self.retained_for_stop = True
        if self.rpc is not None:
            self.rpc.owner_custody_retained = True
        if not hasattr(self, "retention_errors"):
            self.retention_errors = []
        if not hasattr(self, "retained_rpc"):
            self.retained_rpc = self.rpc
            self.retained_resume_id = (self.state.get("last_instruction") or {}).get("id")
        if not getattr(self, "retention_pause_attempted", False):
            self.retention_pause_attempted = True
            try:
                self.pause()
            except (Exception, KeyboardInterrupt, SystemExit) as error:
                self.retention_failure("pause", error)
                if getattr(error, "rpc_mutating", False):
                    self.state["transport_uncertain"] = {"at": utc(),
                        "method": getattr(error, "rpc_method", "thread/goal/set"),
                        "reason": "owner_retention_pause_delivery_uncertain"}
                self.stop_reason = self.stop_reason or "owner_pause_unknown"
                self.stop_now = True
        if not isinstance(self.state.get("owner_retention"), dict):
            from os_goal_guard_protocol import process_start
            self.state["owner_retention"] = make_retention_record(
                self.state, watcher_pid=os.getppid(), watcher_start=process_start(os.getppid()),
                reason=reason, errors=self.retention_errors)
        self.state.update(phase="owner_retained", controller_dispatch_enabled=False,
                          stop_reason=self.stop_reason,
                          owner_retention_errors=list(self.retention_errors))
        try:
            self.save()
        except (Exception, KeyboardInterrupt, SystemExit) as error:
            self.retention_failure("save", error)
            if isinstance(error, (KeyboardInterrupt, SystemExit)):
                self.stop_reason = self.stop_reason or "owner_monitor_interrupted"
                self.stop_now = True

    def retained_resume_ready(self):
        receipt = self.state.get("last_instruction") or {}
        return (getattr(self.args, "continuous", False) and self.rpc is self.retained_rpc
                and not self.stop_reason and not self.stop_now and not self.checkpoint_requested
                and set(self.active) <= {self.state.get("thread_id")}
                and self.goal and self.goal.get("status") == "active"
                and self.goal.get("objective") == OBJECTIVE
                and receipt.get("id") != self.retained_resume_id
                and receipt.get("status") == "accepted_by_server"
                and receipt.get("control_kind") == "resume_same_owner"
                and receipt.get("primary_stop_generation") == self.primary_stop_generation
                and not _same_owner_control_blocker(self.state)
                and receipt.get("owner") == _account_control_owner(self.state, self.directory, self.repo))

    def wait_retained_owner(self, reason):
        """Keep original channels alive; only explicit typed control can resume.

        Pausing a goal prevents future continuations. Existing turns/children may
        still run: neither a heartbeat nor this loop proves their quiescence.
        """
        self.retain_owner(reason)
        next_refresh = time.monotonic()
        while True:
            try:
                if self.retained_resume_ready():
                    self.retained_for_stop = False
                    self.retention_pause_attempted = False
                    self.retained_resume_id = (self.state.get("last_instruction") or {}).get("id")
                    self.save(phase="running", controller_dispatch_enabled=True)
                    return True
                # No native-control polling, repairs, turn starts or ordinary
                # instructions in custody retention. Typed control has its own
                # fresh account/identity/stop checks and grants no job resources.
                view = dict(self.state, goal=self.goal, stop_reason=self.stop_reason,
                            stop_now=self.stop_now, checkpoint_requested=self.checkpoint_requested)
                if control_context_eligible(view):
                    self.deliver_instruction(control_only=True)
                self.rpc.pump(timeout=1)
                now = time.monotonic()
                if now >= next_refresh:
                    if control_context_eligible(view):
                        self.refresh_credit_budget(control_only=True)
                    self.save(phase="owner_retained", heartbeat_at=utc(),
                              owner_retention_errors=list(self.retention_errors))
                    self.output.flush()
                    next_refresh = now + max(5, self.args.heartbeat_seconds)
            except (Exception, KeyboardInterrupt, SystemExit) as error:
                self.retention_failure("monitor", error)
                if isinstance(error, (KeyboardInterrupt, SystemExit)):
                    self.stop_reason = self.stop_reason or "owner_monitor_interrupted"
                    self.stop_now = True
                # A broken stream/save never closes or replaces the owner.
                # Bounded backoff prevents a disconnected server hot loop.
                try:
                    time.sleep(min(30, max(1, self.args.heartbeat_seconds)))
                except (KeyboardInterrupt, SystemExit) as interrupt:
                    self.retention_failure("monitor_backoff", interrupt)
                    self.stop_reason = self.stop_reason or "owner_monitor_interrupted"
                    self.stop_now = True

    def run(self):
        begin = True
        while True:
            try:
                code = self._run_until_stop(begin=begin)
            except (Exception, KeyboardInterrupt, SystemExit) as error:
                if not retention_required(self.args, self.rpc):
                    raise
                self.retention_failure("work_loop", error)
                self.stop_reason = self.stop_reason or "launcher_error"
                self.stop_now = True
                self.retain_owner(self.stop_reason)
                code = 1
            if not retention_required(self.args, self.rpc):
                return code
            self.wait_retained_owner(self.stop_reason or (self.goal or {}).get("status"))
            begin = False  # Resume the SAME Campaign/RPC; never call begin again.

    def _run_until_stop(self, *, begin=True):
        started = time.monotonic()
        deadline = started + self.args.hours * 3600 if self.args.hours else float("inf")
        checkpoint_at = max(started, deadline - min(self.args.grace_seconds, self.args.hours * 1800))
        stop_deadline = None
        refresh_interval = 5 if self.credit_guard is not None else 30
        next_refresh = started + refresh_interval
        next_heartbeat = started
        next_acceptance_check = started
        acceptance_turn = None
        code = 1
        try:
            self.output.notice("Starting launcher; worker_pid=" + str(os.getpid())
                               + "; live log: " + str(self.log_dir / "console.log"))
            if begin:
                self.begin()
            while True:
                now = time.monotonic()
                status = self.goal["status"] if self.goal else None
                blocked_wait = (status == "blocked" and
                                (getattr(self.args, "repair_agent_failures", False)
                                 or getattr(self.args, "same_owner_control", False))
                                and not self.stop_reason and not self.stop_now
                                and not self.checkpoint_requested)
                current_turn = (self.state.get("last_turn") or {}).get("id")
                if self.stop_now:
                    code = 21 if self.stop_reason in {"quota_exhausted", "included_usage_guard",
                                                      "included_usage_unknown", "credit_balance_decreased",
                                                      "credit_balance_unknown", "chatgpt_auth_required",
                                                      "chatgpt_auth_changed", "credit_budget_exhausted",
                                                      "credit_budget_unknown"} else 23
                    break
                if (status in TERMINAL_CODES and not self.checkpoint_requested
                        and not blocked_wait and not self.stop_reason):
                    code = TERMINAL_CODES[status]
                    break
                if (getattr(self.args, "stop_after_m14_m15", False) and status == "active"
                        and not self.stop_reason and not self.stop_now and not self.checkpoint_requested
                        and (now >= next_acceptance_check or current_turn != acceptance_turn)):
                    next_acceptance_check, acceptance_turn = now + 30, current_turn
                    if m14_m15_closed(self.repo):
                        if not self.request_checkpoint("requested_milestones_complete"):
                            continue
                        stop_deadline = min(deadline, now + self.args.grace_seconds)
                        blocked_wait = False
                if blocked_wait:
                    if getattr(self.args, "repair_agent_failures", False):
                        self.review_blocked_goal()
                    elif self.state.get("phase") != "waiting_for_input":
                        self.save(phase="waiting_for_input", waiting_reason="explicit_same_owner_control_required")
                    if self.stop_now:
                        continue
                if not self.checkpoint_requested and (self.stop_reason or now >= checkpoint_at):
                    self.stop_reason = self.stop_reason or "work_window"
                    self.request_checkpoint()
                    stop_deadline = min(deadline, now + self.args.grace_seconds)
                if self.checkpoint_requested and (retention_required(self.args, self.rpc)
                                                  or not self.active or now >= stop_deadline):
                    code = 10
                    break
                if not self.active and now - self.last_activity > 120 and not blocked_wait:
                    self.stop_reason = "active_goal_did_not_continue"
                    self.save(retryable=True, transport_failure={"schema_version": 1,
                        "worker_pid": os.getpid(), "worker_start": self.state.get("worker_start"),
                        "thread_id": self.state.get("thread_id"), "class": "continuation_stall",
                        "error": "active_goal_did_not_continue", "error_type": "ContinuationStall",
                        "method": None, "mutating": False})
                    code = 24
                    break
                self.poll_native_owner_control()
                self.deliver_instruction()
                self.rpc.pump(timeout=1)
                self.output.flush()
                now = time.monotonic()
                if now >= next_heartbeat:
                    self.poll_capture_progress()
                    self.output.heartbeat(self.goal, self.active, now - started,
                                          os.getpid(), self.state.get("server_pid"))
                    self.save(heartbeat_at=utc(), uptime_seconds=round(now - started, 1))
                    next_heartbeat = now + self.args.heartbeat_seconds
                if now >= next_refresh:
                    if self.credit_guard is not None:
                        self.refresh_credit_budget()
                        if self.stop_now:
                            continue
                    self.remember_goal(self.rpc.call("thread/goal/get", {"threadId": self.state["thread_id"]})["goal"])
                    next_refresh = now + refresh_interval
        except Exception as error:
            failure = self.transport_error_record(error)
            prior_stop = self.stop_reason
            self.stop_reason = self.stop_reason or "launcher_error"
            retryable = failure is not None and not failure["mutating"]
            error_fields = {}
            if not prior_stop or "last_error" not in self.state:
                error_fields = {"last_error": str(error), "last_error_provenance": {
                    "error": str(error), "log_dir": str(self.log_dir),
                    "worker_pid": os.getpid(), "worker_start": self.state.get("worker_start"),
                    "recorded_at": utc()}}
            self.save(retryable=retryable, transport_failure=failure, **error_fields)
            if failure is not None and failure["mutating"]:
                self.save(transport_uncertain={"at": utc(), "method": failure["method"],
                          "error": str(error), "reason": "mutating_rpc_delivery_uncertain"})
                self.stop_reason, self.stop_now = prior_stop or "rpc_delivery_uncertain", True
            if (retryable and not prior_stop and not self.controlled
                    and (getattr(self.args, "recovery_goal_sha256", None)
                         or getattr(self.args, "recovery_require_active", False)
                         or getattr(self.args, "credit_timeout_goal_sha256", None))
                    and not any(self.state.get(key) for key in
                                ("service_hold", "policy_hold", "auth_hold", "billing_hold"))):
                from watch_os_goal import process_start
                self.save(transport_startup={"schema_version": 1, "worker_pid": os.getpid(),
                    "worker_start": self.state.get("worker_start"), "watcher_pid": os.getppid(),
                    "watcher_start": process_start(os.getppid()), "thread_id": self.state.get("thread_id"),
                    "before_inference": True, "expected_goal_sha256": getattr(
                        self.args, "recovery_goal_sha256", None) or getattr(
                        self.args, "credit_timeout_goal_sha256", None),
                    "require_active": getattr(self.args, "recovery_require_active", False),
                    "class": failure["class"], "error": failure["error"], "method": failure["method"]})
            self.output.notice(str(error))
        finally:
            if retention_required(self.args, self.rpc):
                self.retain_owner(self.stop_reason or (self.goal or {}).get("status") or "owner_unknown")
            else:
                # Preserve an already propagating interruption and any interruption
                # acquired while closing the data channel across ALL later cleanup.
                native_primary = sys.exc_info()[1]
                native_close_interrupt = (native_primary if isinstance(native_primary, (KeyboardInterrupt, SystemExit))
                                          else getattr(native_primary, "interrupt", None))
                native_close_errors = []
                if self.native_owner_control is not None:
                    try:self.native_owner_control.close()
                    except BaseException as native_error:
                        native_close_errors.append(native_error)
                        if native_close_interrupt is None:
                            native_close_interrupt = (native_error if isinstance(native_error, (KeyboardInterrupt, SystemExit))
                                                      else getattr(native_error, "interrupt", None))
                # Retain exception objects before formatting or persistence.
                self.native_owner_control_cleanup_errors = native_close_errors
                try:
                    self.state["native_current_owner_close_errors"] = [str(x) for x in native_close_errors]
                    # Capture the actual reason/goal before shutdown may pause it. Keep
                    # the original diagnostic identity; old failures are not relabelled.
                    stop_snapshot = dict(self.state, goal=dict(self.goal) if self.goal else None,
                                         stop_reason=self.stop_reason, phase="stopping",
                                         active_turns=dict(self.active))
                    try:
                        self.stop()
                    finally:
                        try:
                            close_errors = []
                            try:
                                if self.rpc:
                                    self.rpc.close()
                            except Exception as error:
                                close_errors.append(str(error))
                            known = getattr(self.rpc, "close_errors", None)
                            if isinstance(known, list):
                                close_errors = known + close_errors
                            self.save(phase="stopped", stop_reason=self.stop_reason, exit_code=code,
                                      server_close_errors=close_errors, cleanup_verified=False,
                                      stop_decision={"goal_status": (stop_snapshot.get("goal") or {}).get("status"),
                                          "log_dir": str(self.log_dir), "worker_pid": self.state.get("worker_pid"),
                                          "worker_start": self.state.get("worker_start"), "reason": self.stop_reason})
                            if self.stop_reason == "guardian_recovery" and self.state.get("guardian_checkpoint_request"):
                                request = self.state["guardian_checkpoint_request"]
                                self.save(guardian_checkpoint={"run_id": request["run_id"], "request_id": request["request_id"],
                                          "worker_pid": os.getpid(), "worker_start": self.state.get("worker_start")})
                            self.record_stop_diagnostic("worker_stopped", reason=self.stop_reason,
                                                        exit_code=code, snapshot=stop_snapshot)
                            self.output.notice("Stopped: goal reports " + str((self.goal or {}).get("status", "unknown"))
                                               + "; " + (self.stop_reason or "goal status") + ".")
                            self.output.notice("State: " + str(self.state_path) + "; " + restart_advice(self.state))
                        finally:
                            self.output.close()
                except BaseException as native_cleanup_error:
                    native_close_errors.append(native_cleanup_error)
                    if native_close_interrupt is None:
                        native_close_interrupt = (native_cleanup_error if isinstance(native_cleanup_error, (KeyboardInterrupt, SystemExit))
                                                  else getattr(native_cleanup_error, "interrupt", None))
                    raise
                finally:
                    if native_close_interrupt is not None:
                        native_close_interrupt.native_primary_error = native_primary
                        native_close_interrupt.native_secondary_errors = list(native_close_errors)
                        raise native_close_interrupt
        return code


def arguments(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="Print launch settings; no server, thread or model call")
    mode.add_argument("--check", action="store_true", help="Inspect local Codex settings/models; no thread or inference")
    mode.add_argument("--check-sudo", action="store_true", help="Verify private askpass authentication with sudo id -u; no inference")
    mode.add_argument("--status", action="store_true", help="Read the last saved launcher snapshot; no server")
    mode.add_argument("--progress", action="store_true", help="Show live runner activity and the last engineering dashboard; no server")
    mode.add_argument("--instruct", metavar="TEXT", help="Send a live instruction to the coordinator; queues through checkpoints")
    mode.add_argument("--resume-same-owner", metavar="TEXT",
                      help="Queue explicit source-bound resume control for an opted-in idle blocked owner; grants no jobs or hold releases")
    parser.add_argument("--instruction-source-id", help="Stable user-source identity for an instruction or explicit same-owner resume")
    parser.add_argument("--same-owner-control", action="store_true",
                        help="Opt in to factual control observations and explicit typed same-owner resume; never auto-activate")
    parser.add_argument("--retain-owner-on-stop", action="store_true",
                        help="Keep the original server and channels on stop; never infer child closure")
    parser.add_argument("--continuous", action="store_true",
                        help="Opt in to owner retention, guarded control and eligible repairs; preserves finite budgets and work windows")
    parser.add_argument('--capture-progress-directory', type=Path,
                        help='Explicit fresh capture directory; with --instruct register it before steering, otherwise at startup')
    parser.add_argument("--hours", type=float, default=0, help="Optional work window in hours; 0 means no time limit (default: 0)")
    parser.add_argument("--repair-agent-failures", action="store_true",
                        help="Delegate eligible engineering repairs; diagnose a blocked goal once and retain monitored waiting")
    parser.add_argument("--stop-after-m14-m15", action="store_true",
                        help="Checkpoint after BOTH original M14 and M15 file/integration acceptances; preserve the larger saved goal")
    parser.add_argument("--grace-seconds", type=float, default=600, help="Reserve up to this many seconds for a checkpoint")
    parser.add_argument("--model",
                        choices=list(dict.fromkeys((DEFAULT_DISPATCHER_MODEL,) + DISPATCHER_MODEL_PREFERENCE)),
                        help="Pin dispatcher model; default preference: " + DEFAULT_DISPATCHER_MODEL)
    parser.add_argument("--effort",
                        choices=list(DISPATCHER_EFFORT_PREFERENCE),
                        help="Pin dispatcher reasoning; max preferred by default, workers retain separate effort levels")
    parser.add_argument("--profile", choices=["aggressive", "balanced"], default="aggressive",
                        help="Dedicated-machine parallelism (default) or historical balanced limits")
    parser.add_argument("--max-agents", type=int, help="Coordination slots; default six canonical owners, subject to admission")
    parser.add_argument("--build-jobs", type=int, help="Aggregate HOST light-job ceiling, at most 3 on CPUs 0,6,7")
    parser.add_argument("--memory-gib", type=float, help="HOST aggregate ceiling, at most 4 GiB including retained charges and overhead")
    parser.add_argument("--agent-windows", choices=["auto", "on", "off"], default="auto",
                        help="Separate live desktop window per child (default: auto when a desktop is available); logs always retained")
    parser.add_argument("--fresh-session", action="store_true",
                        help="Explicitly start a fresh conversation from Markdown; archive the previous state")
    parser.add_argument("--fresh-on-recovery", action="store_true",
                        help="Use fresh Markdown-guided conversations after classified recoverable crashes")
    parser.add_argument("--fresh-recovery-proof", type=Path, help=argparse.SUPPRESS)
    parser.add_argument("--token-budget", type=int, help="Explicit total goal budget; omitted preserves the current budget")
    parser.add_argument("--credit-budget", type=credit_budget_argument, metavar="CREDITS",
                        help="Explicitly allow existing prepaid credits up to an observed account-balance budget; in-flight charges may settle later")
    parser.add_argument("--credit-run-id", help=argparse.SUPPRESS)
    parser.add_argument("--codex", default="codex", help="Path to the local Codex executable")
    parser.add_argument("--startup-instruction-file", type=Path,
                        help="Explicit invocation instructions loaded before resuming the saved thread")
    parser.add_argument("--startup-instruction-sha256",
                        help="Pin the invocation instructions across preflight and watcher recoveries")
    parser.add_argument("--supersede-instruction", action="append", default=[], metavar="ID:SHA256",
                        help="Archive an exact historical queued instruction before this explicit resume")
    parser.add_argument("--max-restarts", type=int, default=-1, help="Automatic recoveries; -1 means unlimited, 0 disables (default: -1)")
    parser.add_argument("--restart-delay", type=float, default=5, help="Initial recovery backoff in seconds (default: 5)")
    parser.add_argument("--watchdog-seconds", type=float, default=180, help="Recover a runner with no state heartbeat; 0 disables")
    parser.add_argument("--heartbeat-seconds", type=float, default=15, help="Print liveness and agent activity every N seconds (default: 15)")
    parser.add_argument("--stall-seconds", type=float, default=0, help="Opt-in agent-silence watchdog; 0 (default) preserves healthy silent builds/soaks")
    parser.add_argument("--quiet", action="store_true", help="Hide live agent output; keep heartbeats and console.log")
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--supervisor", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--guardian-run-id", help=argparse.SUPPRESS)
    parser.add_argument("--guardian-recovery-proof", type=Path, help=argparse.SUPPRESS)
    parser.add_argument("--recovered", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--credit-timeout-goal-sha256", help=argparse.SUPPRESS)
    parser.add_argument("--recovery-goal-sha256", help=argparse.SUPPRESS)
    parser.add_argument("--recovery-require-active", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--allow-dispatcher-fallback", action="store_true",
                        help="Explicitly allow advertised model fallback for unpinned defaults; otherwise Sol/max stays pinned")
    args = parser.parse_args(argv)
    if args.continuous:
        args.same_owner_control = args.retain_owner_on_stop = args.repair_agent_failures = True
    if args.instruction_source_id is not None and (not 0 < len(args.instruction_source_id) <= 512
            or args.instruct is None and args.resume_same_owner is None):
        parser.error("instruction-source-id requires an instruction or explicit same-owner resume and at most 512 characters")
    if args.resume_same_owner is not None and (args.instruction_source_id is None
            or args.capture_progress_directory is not None):
        parser.error("same-owner resume requires instruction-source-id and no capture registration")
    if args.guardian_run_id and (len(args.guardian_run_id) != 32 or any(c not in "0123456789abcdef" for c in args.guardian_run_id)):
        parser.error("Guardian run identity must be a 32-character hex nonce")
    if args.guardian_recovery_proof and (not args.guardian_run_id or not args.supervisor or args.worker or args.fresh_session):
        parser.error("Guardian recovery needs its supervised first-launch proof and saved cursor")
    args.dispatcher_pinned = (args.model is not None or args.effort is not None
                              or not args.allow_dispatcher_fallback)
    if args.model is None:
        args.model = DEFAULT_DISPATCHER_MODEL
    if args.effort is None:
        args.effort = DEFAULT_DISPATCHER_EFFORT
    if args.credit_run_id is not None and (args.credit_budget is None or
            len(args.credit_run_id) != 32 or any(c not in "0123456789abcdef" for c in args.credit_run_id)):
        parser.error("credit-run-id requires a credit budget and a 32-character lowercase hex identifier")
    if args.worker and args.credit_budget is not None and args.credit_run_id is None:
        parser.error("Credit-funded workers require the watcher's persistent credit-run-id")
    if ((args.recovery_goal_sha256 or args.recovery_require_active) and
            (not args.worker or not args.recovered or
             bool(args.recovery_goal_sha256) and args.recovery_require_active)):
        parser.error("Generic recovery needs a supervised worker and one live-goal guard")
    if args.recovery_goal_sha256 and (len(args.recovery_goal_sha256) != 64 or
            any(c not in "0123456789abcdef" for c in args.recovery_goal_sha256)):
        parser.error("Generic recovery requires an exact goal digest")
    if args.credit_timeout_goal_sha256 and (args.recovery_goal_sha256 or args.recovery_require_active):
        parser.error("Choose one recovery goal provenance mode")
    if args.credit_timeout_goal_sha256 and (not args.worker or not args.recovered
            or len(args.credit_timeout_goal_sha256) != 64
            or any(c not in "0123456789abcdef" for c in args.credit_timeout_goal_sha256)):
        parser.error("Credit-timeout recovery requires a supervised worker and exact goal digest")
    if args.fresh_recovery_proof and not (args.worker and args.recovered and args.fresh_on_recovery):
        parser.error("Fresh recovery requires the supervised recovered worker and a watcher proof")
    args.startup_instruction = (read_startup_instruction(args.startup_instruction_file)
                                if args.startup_instruction_file else None)
    if args.startup_instruction_sha256 is not None:
        if (args.startup_instruction is None or
                hashlib.sha256(args.startup_instruction.encode()).hexdigest() != args.startup_instruction_sha256):
            parser.error("Startup instruction digest differs; reconcile the changed instruction before resuming")
    args.supersede_instructions = []
    for binding in args.supersede_instruction:
        ident, separator, digest = binding.partition(":")
        if (not separator or not args.startup_instruction_sha256 or len(digest) != 64 or
                any(c not in "0123456789abcdef" for c in digest)):
            parser.error("Supersession requires ID:SHA256 and a hash-pinned startup instruction")
        args.supersede_instructions.append({"id": ident, "sha256": digest})
    if any(value is not None and value <= 0 for value in (args.max_agents, args.build_jobs)):
        parser.error("max-agents and build-jobs must be positive")
    if args.memory_gib is not None and (not math.isfinite(args.memory_gib) or args.memory_gib <= 0):
        parser.error("memory-gib must be finite and positive")
    if not math.isfinite(args.hours) or args.hours < 0 or not math.isfinite(args.grace_seconds) or args.grace_seconds < 0:
        parser.error("hours and grace-seconds must be finite and non-negative")
    if args.token_budget is not None and args.token_budget <= 0:
        parser.error("token-budget must be positive")
    if not math.isfinite(args.heartbeat_seconds) or args.heartbeat_seconds <= 0:
        parser.error("heartbeat-seconds must be finite and positive")
    if not math.isfinite(args.stall_seconds) or args.stall_seconds < 0:
        parser.error("stall-seconds must be finite and non-negative")
    if args.stall_seconds and args.stall_seconds <= args.heartbeat_seconds:
        parser.error("stall-seconds must exceed heartbeat-seconds, or be 0 to disable recovery")
    if (args.max_restarts < -1
            or not math.isfinite(args.restart_delay) or args.restart_delay < 0
            or not math.isfinite(args.watchdog_seconds) or args.watchdog_seconds < 0):
        parser.error("restart count must be -1 (unlimited) or non-negative; recovery timing must be finite and non-negative")
    return args


def main(argv=None):
    args = arguments(argv)
    os.umask(0o077)
    git_dir = subprocess.check_output(["git", "-C", str(REPO), "rev-parse", "--git-common-dir"], text=True).strip()
    directory = (REPO / git_dir).resolve() / "os-autopilot"
    if args.status:
        state = directory / "state.json"
        current = json.loads(state.read_text()) if state.exists() else {"phase": "not_started", "state_path": str(state)}
        watch = directory / "watcher.json"
        if watch.exists():
            current["watcher"] = json.loads(watch.read_text())
            saved_watch = current["watcher"]
            if (saved_watch.get("worker_pid") == current.get("worker_pid")
                    and saved_watch.get("event") in {"worker_exited", "watcher_stopped"}):
                # SIGKILL prevents the worker from replacing its last running snapshot.
                current["last_worker_phase"] = current.get("phase")
                current["phase"] = "stopped"
                current["last_recorded_active_turns"] = current.get("active_turns", {})
                current["active_turns"] = {}
        latest_stop = directory / "latest-stop.json"
        if latest_stop.is_file() and not latest_stop.is_symlink():
            try:
                current["latest_stop_diagnostic"] = json.loads(latest_stop.read_text())
                current["stop_journal"] = str(directory / "stop-events.jsonl")
            except (OSError, ValueError):
                current["stop_diagnostic_read_error"] = "Latest stop diagnostic is unreadable; inspect journal/console."
        print(json.dumps(current, indent=2))
        return 0
    if args.progress:
        print(progress_report(directory, REPO))
        return 0
    if args.instruct is not None:
        ident = queue_instruction(directory, args.instruct, args.capture_progress_directory,
                                  source_id=args.instruction_source_id)
        print("Queued instruction " + ident + "; it will reach the next active coordinator turn.")
        return 0
    if args.resume_same_owner is not None:
        ident = queue_same_owner_resume(directory, args.resume_same_owner,
                                        source_id=args.instruction_source_id)
        print("Queued explicit same-owner control " + ident + "; this admits no jobs and releases no holds.")
        return 0
    if args.dry_run:
        print(json.dumps({"command": shlex.join(server_argv(args, REPO)), "hours": args.hours,
                          "checkpoint_reserve_seconds": args.grace_seconds, "state_directory": str(directory),
                          "objective": OBJECTIVE, "model_calls": 0,
                          "sudo_helper": str(SUDO_HELPER), "sudo_credential_configured": SUDO_CREDENTIAL.is_file(),
                          "supervised": not args.worker, "max_restarts": args.max_restarts,
                          "watchdog_seconds": args.watchdog_seconds,
                          "heartbeat_seconds": args.heartbeat_seconds, "live_output": not args.quiet,
                          "stall_seconds": args.stall_seconds,
                          "repair_agent_failures": args.repair_agent_failures,
                          "same_owner_control": args.same_owner_control,
                          "stop_after_m14_m15": args.stop_after_m14_m15,
                          "stop_journal": str(directory / "stop-events.jsonl"),
                          "resources": launch_resources(args, REPO), "policy_sha256": policy_hashes(REPO),
                          "model_routing": model_routing(args),
                          "included_usage_stop_percent": INCLUDED_USAGE_STOP_PERCENT,
                          "billing": billing_policy(args),
                          "supersede_instructions": args.supersede_instructions,
                          "agent_windows": window_capability(args.agent_windows),
                          "startup_instruction_sha256": (hashlib.sha256(args.startup_instruction.encode()).hexdigest()
                                                         if args.startup_instruction else None),
                          "permissions": "User-authorized danger-full-access, approval_policy=never; no clarification prompts. Global config unchanged."}, indent=2))
        return 0
    if args.check_sudo:
        result = subprocess.run(["sudo", "-A", "-k", "--", "/usr/bin/id", "-u"],
                                env=runtime_environment(), stdin=subprocess.DEVNULL,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=30)
        if result.returncode != 0 or result.stdout.strip() != "0":
            raise RuntimeError("Unattended sudo check failed: " + result.stderr.strip())
        print(json.dumps({"status": "PASS_UNATTENDED_SUDO", "effective_uid": 0,
                          "scope": "Authentication and id -u only; no agent or OS payload started."}))
        return 0
    if not shutil.which(args.codex):
        raise RuntimeError("Codex executable not found. Install/sign in to the local CLI first.")
    if args.check:
        if args.supersede_instructions:
            reconcile_instructions(directory, args.supersede_instructions,
                                   args.startup_instruction_sha256, execute=False)
        with tempfile.TemporaryDirectory(prefix="mckernel-goal-check-") as temporary:
            rpc = RPC(server_argv(args, REPO), Path(temporary), lambda event: None)
            try:
                report = preflight(rpc, args, REPO)
                if args.credit_budget is not None:
                    account = rpc.call("account/read", {"refreshToken": False}).get("account") or {}
                    if account.get("type") != "chatgpt":
                        raise RuntimeError("Prepaid credits require ChatGPT account authentication")
                    limits = rpc.call("account/rateLimits/read", {}).get("rateLimits")
                    report["billing"]["available_prepaid_credits"] = str(available_balance(limits))
                print(json.dumps(report, indent=2))
            finally:
                rpc.close()
        return 0
    if not args.worker:
        if not args.supervisor:
            from start_os_overnight import launch_legacy
            return launch_legacy(list(sys.argv[1:] if argv is None else argv))
        check_resources(launch_resources(args, REPO))
        from watch_os_goal import supervise
        forwarded = list(sys.argv[1:] if argv is None else argv)
        if args.credit_budget is not None and args.credit_run_id is None:
            args.credit_run_id = uuid4().hex
            forwarded.extend(["--credit-run-id", args.credit_run_id])
        return supervise(args, REPO, directory, forwarded, Lease, atomic_json)
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    lease = Lease(directory / "run.lock")
    try:
        if args.fresh_session or args.fresh_recovery_proof:
            saved = json.loads((directory / "state.json").read_text()) if (directory / "state.json").exists() else {}
            if saved.get("transport_uncertain") or (saved.get("resume_instruction") or {}).get(
                    "status") in {"sending", "delivery_uncertain"}:
                raise RuntimeError("Uncertain RPC delivery cannot be cleared by session archival")
            if args.fresh_recovery_proof and not (args.recovery_goal_sha256 or args.recovery_require_active):
                raise RuntimeError("Fresh automatic recovery needs live predecessor goal provenance")
            from os_goal_sessions import prepare_fresh_session
            previous = prepare_fresh_session(
                directory, REPO, atomic_json,
                recovery=bool(args.fresh_recovery_proof),
                recovery_proof=args.fresh_recovery_proof,
                expected_objective=OBJECTIVE)
            say("Fresh conversation prepared from Markdown; previous state preserved at "
                + str(previous.get("previous_session", {}).get("state_path", "session-archives")))
        campaign = Campaign(args, REPO, directory)
        for signum in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
            signal.signal(signum, campaign.on_signal)
        signal.signal(signal.SIGUSR1, campaign.on_watchdog)
        return campaign.run()
    finally:
        lease.close()


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as failure:
        say(str(failure))
        sys.exit(1)


